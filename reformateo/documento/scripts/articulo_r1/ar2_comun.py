"""
ar2_comun.py — Piezas comunes de las mediciones completas de AE-5 y AE-4
(revisión r1 del artículo, envío 11297; CANON §14.41)
===============================================================================
Actividades 2.2 y 3.3. Las corridas son las 81 del servidor del 2026-11-21
(`modelo_base/run_servidor.sh revision_r1_resuelta`, commits 57fbb55 y abf83ab,
el mismo núcleo): las cuatro esquinas del factorial de los dos supuestos en los
13 casos (`SALIDAS_SERVIDOR/matriz_esquina_<esquina>/<caso>/`) y las tres
variantes del corte del piso (`SALIDAS_SERVIDOR/matriz_corte_<variante>/<caso>/`).
Diseño en `Documentos/articulo_latam/v2_es/revision_r1/diseno_mediciones_completas.md`.

Estos guiones NO simulan: leen los almacenes y los libros de esas corridas (su
sha256 queda en la procedencia; las huellas se registran después en el canon,
grupos `r1m/`) y el canon con huella, y liquidan con las funciones del proyecto
(`scenarios/esquinas_supuestos.py`, `core/opciones_externas.reparto_anexo4`,
`core/corte_secuencial.liquida_fifo`). Escriben en
`SALIDAS_SERVIDOR/articulo_r1_resuelta_2026-11-21/`.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

import ar1_comun as A1

SALIDA = A1.SALIDAS / "articulo_r1_resuelta_2026-11-21"
A1.SALIDA = SALIDA                      # Medicion escribe aquí, no en la de §14.40
AS, CP, Medicion, CASOS, M = A1.AS, A1.CP, A1.Medicion, A1.CASOS, A1.M
RAIZ = A1.RAIZ
ESQUINAS = ("p2p", "solo1", "solo2", "ninguno")
CORTES = ("iterado", "secuencial_pronostico", "secuencial_saldo")
CON_CORTE = ["E1", "E2", "E3", "E4", "E5", "P1", "I1", "N1"]
CONTROLES = ["E0", "P2", "K1", "CV2", "SINU"]
CASOS_CORTE = {"iterado": CON_CORTE, "secuencial_saldo": CON_CORTE,
               "secuencial_pronostico": CON_CORTE + CONTROLES}
NUCLEO = {"57fbb55", "abf83ab", "e1a0e40"}   # el mismo núcleo; e1a0e40 (retome de B1 y B2) añade la opción del punto fijo de solo1 y --max-iter-corte, apagadas


def dir_corrida(tipo: str, valor: str, caso: str) -> Path:
    return A1.SALIDAS / f"matriz_{tipo}_{valor}" / caso


def _lee_partes(med: Medicion, d: Path, tabla: str) -> pd.DataFrame:
    partes = sorted((d / "almacen" / "m1" / tabla).glob("parte_*.parquet"))
    if not partes:
        return pd.DataFrame()
    for p in partes:
        med.insumo(p.relative_to(RAIZ).as_posix())
    return pd.concat([pd.read_parquet(p) for p in partes], ignore_index=True)


def carga_corrida(med: Medicion, d: Path, c: str, base: dict) -> dict:
    """Las matrices (N, T) de una corrida nueva, en el orden y con las tarifas
    de la carga canónica `base` (`AS.carga`). Comprueba que la demanda, la
    generación, la tarifa y el calendario son los del canon."""
    a = _lee_partes(med, d, "agentes")
    fl = _lee_partes(med, d, "flujos")
    ags, N = base["ags"], base["N"]
    med.exige(list(dict.fromkeys(a.agente)) == ags and len(a) == 6144 * N, f"{d}: agentes distintos del canon")

    def piv(col):
        return a.pivot(index="agente", columns="hora", values=col).loc[ags].to_numpy(dtype=float)

    G, D, v, q, CU, piso = (piv(k) for k in ["generacion", "demanda", "vende_p2p", "compra_p2p", "techo", "piso"])
    for nom, x, y in (("generacion", G, base["G"]), ("demanda", D, base["D"]), ("techo", CU, base["CU"])):
        med.exige(np.array_equal(x, y), f"{d}: {nom} distinta de la del canon")
    if len(fl):
        fl = fl.astype({"kwh": "float64", "precio": "float64"})
        fv = fl.groupby(["vendedor", "hora"]).kwh.sum().unstack(fill_value=0.0).reindex(
            index=ags, columns=range(6144), fill_value=0.0).to_numpy()
        fq = fl.groupby(["comprador", "hora"]).kwh.sum().unstack(fill_value=0.0).reindex(
            index=ags, columns=range(6144), fill_value=0.0).to_numpy()
        med.exige(float(np.abs(fv - v).max()) <= 1e-3 and float(np.abs(fq - q).max()) <= 1e-3,
                  f"{d}: vende/compra distintos de los flujos")
        cob = (fl.kwh * fl.precio).groupby(fl.vendedor).sum().reindex(ags, fill_value=0.0)
        pag = (fl.kwh * fl.precio).groupby(fl.comprador).sum().reindex(ags, fill_value=0.0)
        pagos = (cob - pag).to_numpy()
    else:
        med.exige(float(np.abs(v).sum() + np.abs(q).sum()) == 0.0, f"{d}: transa sin flujos")
        pagos = np.zeros(N)
    med.exige(float(np.abs(v.sum(0) - q.sum(0)).max()) <= 1e-3, f"{d}: vendido distinto de comprado")
    med.exige(bool((v <= base["s"] + 1e-4).all() and (q <= base["d"] + 1e-4).all()),
              f"{d}: vende más que el sobrante o compra más que el faltante")
    libro = d / "outputs" / "resultados_comparacion.xlsx"
    med.insumo(libro.relative_to(RAIZ).as_posix())
    res = pd.read_excel(libro, "Resumen").set_index("Escenario")["Ganancia_neta_COP"]
    pa = pd.read_excel(libro, "Por_agente")
    dg = pd.read_excel(libro, "Diagnostico", keep_default_na=False)
    med.exige(str(dg.git_hash.iloc[0]) in NUCLEO, f"{d}: commit {dg.git_hash.iloc[0]}")
    cargo = None
    f_c = d / "almacen" / "cargo_comprador.npy"
    if f_c.is_file():
        med.insumo(f_c.relative_to(RAIZ).as_posix())
        cargo = np.load(f_c)
    return dict(G=G, D=D, v=v, q=q, CU=CU, piso=piso, pagos=pagos, res=res, pa=pa,
                orden=str(dg.comando.iloc[0]), commit=str(dg.git_hash.iloc[0]), cargo=cargo)


def bases():
    TT = AS.tarifas()
    cap = AS.capacidades()
    DAT = {c: AS.carga(c, TT, cap) for c in CASOS}
    idx, _ = CP.horizonte()
    pb = CP.bolsa(idx)
    return DAT, pb


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

# El retome de B1 y B2 (2026-11-21, commit e1a0e40): solo1 con el punto fijo
# de su corte y el iterado del corte con los dos estados del ciclo. Si la
# corrida principal entra en ciclo, el otro estado está en <caso>_ciclo.
RETOME_ESQ = A1.SALIDAS / "matriz_esquina_solo1_iterado"
RETOME_COR = A1.SALIDAS / "matriz_corte_iterado_b2"


def estados(base: Path, caso: str) -> list:
    """Las carpetas de los estados de una corrida del retome: la principal y,
    si cicló, la del otro estado."""
    out = [base / caso]
    if (base / f"{caso}_ciclo").is_dir():
        out.append(base / f"{caso}_ciclo")
    return out
