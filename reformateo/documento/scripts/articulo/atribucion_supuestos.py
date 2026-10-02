"""
atribucion_supuestos.py — ¿Depende del orden la atribución de la ventaja del
mercado P2P sobre C4 a cada uno de los dos supuestos de liquidación?
===============================================================================
Tarea B1 de la revisión del artículo en español (2026-09-30), hallazgo I-1 de
`Documentos/articulo_latam/v2_es/revision/revision_independiente.md`. No simula
el mercado ni el GSA: lee artefactos con huella en
`Documentos/canon_2026-09/HUELLAS.csv` (comprueba tamaño y `sha256` de cada uno
antes de leerlo) y vuelve a liquidar, con las funciones de liquidación del
propio proyecto (`core.opciones_externas.reparto_anexo4` y
`precio_permuta_por_periodo`), los flujos del mercado tal como quedaron en el
almacén de cada caso, con otras reglas de liquidación.

Los dos supuestos del mercado P2P (artículo, III-D):

  (1) el residual de cada miembro se liquida por miembro, fuera del colectivo,
      con el art. 25 y el numeral de su planta;
  (2) el intercambio interno no paga cargos.

Resultado principal (I): los dos órdenes de la identidad.

  orden del texto    C4 -> C1 -> P2P:   s1 = C1 − C4,  s2 = P2P − C1
  orden inverso      C4 -> v01 -> P2P:  s2 = v01 − C4, s1 = P2P − v01
  Shapley (media de los dos órdenes) e interacción = (P2P − v01) − (C1 − C4)

C1 es la esquina «solo el supuesto 1» (cada miembro liquida por el art. 25 y
nadie transa) y v01 la de «solo el supuesto 2» (definida abajo). C1 es exacta
donde, pagando el intercambio la deducción del caso 2, ningún par transado
gana (compuerta: E0, K1, CV2 y SINU); en los demás es la de un miembro que no
transa, y una esquina con mercado valdría entre máx(C1, v10) y P2P.

Resultado auxiliar (II): con los flujos del mercado FIJOS (los kWh que cada
miembro vendió y compró en cada hora, del almacén), las cuatro esquinas del
cuadro 2 × 2 son:

  v(0,0)  ninguno: el mercado por el colectivo (P2P_colectivo, canónico).
          Todo pasa por el fondo común con el porcentaje rho del mercado
          (compra interna más exportación no colocada) y la deducción del
          caso 2 del art. 20.
  v(1,1)  los dos: el mercado P2P (canónico).
  v(0,1)  solo el (2): el intercambio no paga cargos (el comprador ahorra su
          CU), pero el residual va al colectivo, caso 2, con el reparto que da
          a cada miembro su propia exportación no colocada (la parte de rho que
          no es compra), contra su importación residual.
  v(1,0)  solo el (1): el residual por miembro como en el P2P, pero cada kWh
          intercambiado paga la deducción del caso 2 del comprador
          (kappa·Cv + Theta), la misma que paga en v(0,0).

Con ellas (columnas `fijos_*`): P2P − C4 = (P2P_colectivo − C4) + (v01 −
P2P_colectivo) + (P2P − v01), y la interacción (P2P − v01) − (v10 −
P2P_colectivo) es cero donde nadie agota el cupo (compuerta). v(1,0) obliga a
transar aunque no convenga, por eso queda bajo C1 donde transar con cargos no
paga: es un cuadro contable, no de comportamiento.

Sensibilidades: v(0,1) con el reparto igual del art. 9 (como C4) en lugar del
propio (acotado con la bolsa en 0 y en su máximo donde falta la bolsa), y
v(1,0) con el intercambio pagando solo Theta (cargos de red).

El precio de bolsa no está en ningún artefacto como serie: se reconstruye de
dos fuentes con huella. (a) La columna `piso` de la tabla `agentes` de los 13
almacenes: desde el corte hx del residual el piso del vendedor es la bolsa de
la hora, de modo que donde el piso difiere de la permuta del numeral de la
planta, es la bolsa (exacta, float32). (b) Donde (a) no llega y algún
mecanismo canónico liquida exceso, se despeja de la tabla `escenarios`:
bolsa = (valor de la comunidad en la hora − autoconsumo − crédito) / exceso,
con la observación de mayor exceso. Compuertas: (a) idéntica entre casos; (a)
y (b) coinciden donde se solapan; toda hora con exceso en una esquina tiene
bolsa conocida (si no, falla).

Falla en voz alta: ningún `except` que trague, ningún NaN rellenado.

Escribe en SALIDAS_SERVIDOR/atribucion_supuestos_2026-09-30/:

    atribucion_13casos.csv   esquinas, brechas y atribuciones por caso (COP)
    bolsa_reconstruida.csv   hora, bolsa y fuente
    procedencia.txt          commit, versiones, huellas leídas y compuertas, sin
                             fecha: con el mismo HEAD y el mismo guion, las tres
                             salen iguales byte a byte entre corridas

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/atribucion_supuestos.py

Sin registrar en HUELLAS.csv (pendiente de decisión del autor).

Actividades 3.3 y 4.2.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import math
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
from core.opciones_externas import reparto_anexo4, precio_permuta_por_periodo  # noqa: E402
from scenarios.scenario_c4_creg101072 import compute_pde_weights  # noqa: E402

HUELLAS = RAIZ / "Documentos" / "canon_2026-09" / "HUELLAS.csv"
SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
BASE_MATRIZ = SALIDAS / "entrega_matriz_reposo_2026-09-19"
SALIDA = SALIDAS / "atribucion_supuestos_2026-09-30"
PREF_ALM = "SALIDAS_SERVIDOR/matriz_reposo/{}/almacen/m1/{}/"
CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1", "CV2", "SINU"]
SIN_AGOTAR = ["E0", "P2", "K1", "CV2", "SINU"]     # CANON §14.8: nadie agota el cupo
M = 1e6

LEIDOS: list[tuple[str, str]] = []
COMPUERTAS: list[str] = []


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[atribucion] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    COMPUERTAS.append(msg)
    print(f"[atribucion]   OK  {msg}")


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


_H = pd.read_csv(HUELLAS)
exige(list(_H.columns) == ["grupo", "ruta", "bytes", "sha256"], f"cabecera inesperada en {HUELLAS}")


def _base(grupo: str) -> Path:
    return SALIDAS if grupo.startswith("e1/") else BASE_MATRIZ


def lee(ruta: str, grupo: str) -> Path:
    f = _H[(_H.ruta == ruta) & (_H.grupo == grupo)]
    exige(len(f) == 1, f"{ruta}: {len(f)} filas en HUELLAS.csv (se esperaba 1)")
    fila = f.iloc[0]
    p = _base(grupo) / ruta
    exige(p.is_file(), f"no existe {p}")
    datos = p.read_bytes()
    exige(len(datos) == int(fila.bytes), f"{ruta}: {len(datos)} bytes, huella {fila.bytes}")
    exige(hashlib.sha256(datos).hexdigest() == fila.sha256, f"{ruta}: sha256 distinto de la huella")
    if (grupo, ruta) not in LEIDOS:
        LEIDOS.append((grupo, ruta))
    return p


def almacen(c: str, tabla: str) -> pd.DataFrame:
    pref = PREF_ALM.format(c, tabla)
    rutas = sorted(r for r in _H[_H.grupo == f"almacen/{c}"].ruta if r.startswith(pref))
    exige(len(rutas) >= 1, f"{c}: sin partes de «{tabla}» en HUELLAS.csv")
    en_disco = sorted(p.name for p in (BASE_MATRIZ / pref).glob("*.parquet"))
    exige(en_disco == [r.rsplit("/", 1)[1] for r in rutas], f"{c} {tabla}: partes en disco distintas de HUELLAS.csv")
    return pd.concat([pd.read_parquet(lee(r, f"almacen/{c}")) for r in rutas], ignore_index=True)


def finito(x, qué: str):
    exige(bool(np.isfinite(np.asarray(x, dtype=float)).all()), f"{qué}: valores no finitos")
    return x


# ── Liquidaciones (las mismas reglas que el motor) ──────────────────────────
def valor_exceso(ex: np.ndarray, pb: np.ndarray, qué: str) -> np.ndarray:
    """Exceso a la bolsa de su hora; falla si una hora con exceso no tiene bolsa."""
    hay = ex > 0
    falta = hay & ~np.isfinite(pb)[None, :]
    exige(not falta.any(), f"{qué}: {int(falta.sum())} horas con exceso sin bolsa conocida "
          f"({float(ex[falta].sum()):.3f} kWh)")
    return np.where(hay, ex * np.where(np.isfinite(pb), pb, 0.0)[None, :], 0.0)


def art25(iny, ret, CU, ded, mes, pb, qué):
    """Art. 25 y Anexo 4 por miembro (como `_residual_art25` y C1)."""
    cr, ex, _ = reparto_anexo4(iny, ret, mes)
    pr = precio_permuta_por_periodo(CU, ded, mes)
    return cr * pr + valor_exceso(ex, pb, qué), ex


def colectivo(iny, ret, CU, ded, mes, pb, pesos, qué):
    """Colectivo mensual (como `_run_c4_monthly_hx`): el fondo del mes con el
    perfil horario del colectivo, la parte de cada miembro contra su
    importación con el Anexo 4."""
    N, T = iny.shape
    val, exs = np.zeros((N, T)), np.zeros((N, T))
    for m in np.unique(mes):
        h = np.flatnonzero(mes == m)
        w = np.asarray(pesos[m], dtype=float)
        exige(abs(w.sum() - 1.0) <= 1e-9 and (w >= 0).all(), f"{qué}: pesos del mes {m} no suman 1")
        asign = w[:, None] * iny[:, h].sum(axis=0)[None, :]
        cr, ex, _ = reparto_anexo4(asign, ret[:, h])
        pr = CU[:, h].mean(axis=1) - ded[:, h].mean(axis=1)
        val[:, h] = cr * pr[:, None] + valor_exceso(ex, pb[h], qué)
        exs[:, h] = ex
    return val, exs


# ── Datos de cada caso ──────────────────────────────────────────────────────
def tarifas() -> pd.DataFrame:
    """CU, Cv y Theta por institución y mes, como cifras_articulo.py §7: Cv =
    techo − piso de E0 (numeral 1, nadie agota); Theta = piso E0 − piso P2."""
    t = {}
    for c in ["E0", "P2"]:
        a = almacen(c, "agentes")
        n = a.groupby(["agente", "mes"])[["techo", "piso"]].nunique()
        exige(bool((n == 1).all().all()), f"{c}: techo o piso no constantes en un mes")
        t[c] = a.groupby(["agente", "mes"])[["techo", "piso"]].first().astype(float)
    exige(t["E0"].index.equals(t["P2"].index) and bool((t["E0"].techo == t["P2"].techo).all()), "E0 y P2: techos distintos")
    T = pd.DataFrame({"CU": t["E0"].techo, "Cv": t["E0"].techo - t["E0"].piso, "Th": t["E0"].piso - t["P2"].piso})
    exige(bool(((T.Cv > 0) & (T.Th > 0)).all()), "Cv o Theta no positivos")
    ok("tarifas: techo y piso constantes por institución y mes en E0 y P2; Cv > 0 y Theta > 0")
    return T


def capacidades() -> pd.Series:
    p = lee("contrafacticos_art18_2026-09-27/capacidad_por_usuario.csv", "e1/A1")
    c = pd.read_csv(p).set_index("caso")
    exige(sorted(c.index) == sorted(CASOS), "capacidad_por_usuario: casos distintos")
    return c.cap_kw


def resumen(c: str) -> pd.Series:
    p = lee(f"SALIDAS_SERVIDOR/matriz_reposo/{c}/outputs/resultados_comparacion.xlsx", f"outputs/{c}")
    r = pd.read_excel(p, sheet_name="Resumen").set_index("Escenario")["Ganancia_neta_COP"]
    finito(r, f"Resumen {c}")
    return r


def carga(c: str, TT: pd.DataFrame, cap: pd.Series) -> dict:
    a = almacen(c, "agentes")
    e = almacen(c, "escenarios")
    fl = almacen(c, "flujos")
    ags = list(dict.fromkeys(a.agente))
    N = len(ags)
    horas = np.sort(a.hora.unique())
    exige(len(horas) == 6144 and len(a) == 6144 * N, f"{c}: {len(a)} filas de agentes")
    exige(bool((horas == np.arange(6144)).all()), f"{c}: horas no consecutivas")
    finito(a[["demanda", "generacion", "autoconsumo", "sobrante", "faltante", "vende_p2p", "compra_p2p",
              "techo", "piso"]].to_numpy(dtype=float), f"agentes {c}")

    def piv(col):
        return a.pivot(index="agente", columns="hora", values=col).loc[ags].to_numpy(dtype=float)

    G, D, au, s, d, v, q, CU, piso = (piv(k) for k in ["generacion", "demanda", "autoconsumo", "sobrante",
                                                         "faltante", "vende_p2p", "compra_p2p", "techo", "piso"])
    exige(float(np.abs(au - np.minimum(G, D)).max()) <= 1e-3 and float(np.abs(s - np.maximum(G - D, 0)).max()) <= 1e-3
          and float(np.abs(d - np.maximum(D - G, 0)).max()) <= 1e-3, f"{c}: autoconsumo, sobrante o faltante no cuadran con G y D")
    mes_s = a[a.agente == ags[0]].sort_values("hora").mes.to_numpy()
    meses = sorted(set(mes_s))
    mes = np.array([meses.index(m) for m in mes_s])
    # flujos: lo vendido y comprado por agente y hora es lo del almacén de flujos
    fl = fl.astype({"kwh": "float64"})
    fv = fl.groupby(["vendedor", "hora"]).kwh.sum().unstack(fill_value=0.0).reindex(index=ags, columns=horas, fill_value=0.0).to_numpy()
    fq = fl.groupby(["comprador", "hora"]).kwh.sum().unstack(fill_value=0.0).reindex(index=ags, columns=horas, fill_value=0.0).to_numpy()
    exige(float(np.abs(fv - v).max()) <= 1e-3 and float(np.abs(fq - q).max()) <= 1e-3, f"{c}: vende_p2p/compra_p2p distintos del almacén de flujos")
    exige(float(np.abs(v.sum(0) - q.sum(0)).max()) <= 1e-3, f"{c}: lo vendido no es lo comprado en alguna hora")
    exige(bool((v <= s + 1e-4).all()) and bool((q <= d + 1e-4).all()), f"{c}: se vende más que el sobrante o se compra más que el faltante")
    kap = 2.0 if c == "CV2" else 1.0
    capk = np.array([float(x) for x in cap[c].split(";")])
    exige(len(capk) == N, f"{c}: {len(capk)} capacidades para {N} agentes")
    Cv = TT.Cv.unstack("mes").loc[ags, list(mes_s)].to_numpy()
    Th = TT.Th.unstack("mes").loc[ags, list(mes_s)].to_numpy()
    exige(float(np.abs(TT.CU.unstack("mes").loc[ags, list(mes_s)].to_numpy() - CU).max()) <= 1e-3, f"{c}: CU distinto del de E0")
    ded1 = kap * Cv + np.where(capk[:, None] > 100.0, Th, 0.0)        # numeral de la planta (art. 25)
    ded4 = kap * Cv + Th                                               # caso 2 del art. 20 (todos los casos)
    ev = e.astype({"valor": "float64"})
    por_agente = ev.groupby(["escenario", "agente"]).valor.sum().unstack(0).loc[ags]
    por_hora = ev.pivot_table(index="hora", columns="escenario", values="valor", aggfunc="sum").reindex(horas)
    return dict(c=c, ags=ags, N=N, G=G, D=D, au=au, s=s, d=d, v=v, q=q, CU=CU, piso=piso, mes=mes,
                kap=kap, capk=capk, Cv=Cv, Th=Th, ded1=ded1, ded4=ded4, por_agente=por_agente, por_hora=por_hora)


def pesos(x: np.ndarray, mes: np.ndarray) -> dict:
    return {m: compute_pde_weights(x[:, mes == m].sum(axis=1), method="excedentes_proportional") for m in np.unique(mes)}


def esquinas(L: dict, pb: np.ndarray) -> dict:
    """Las seis liquidaciones de la comunidad (COP) y la energía en exceso de cada una."""
    s, d, v, q, CU, mes, N = L["s"], L["d"], L["v"], L["q"], L["CU"], L["mes"], L["N"]
    ded1, ded4, c = L["ded1"], L["ded4"], L["c"]
    sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
    auto = L["au"] * CU
    igual = {m: np.full(N, 1.0 / N) for m in np.unique(mes)}
    c1, ex1 = art25(s, d, CU, ded1, mes, pb, f"{c} C1")
    c4, ex4 = colectivo(s, d, CU, ded4, mes, pb, igual, f"{c} C4")
    rp, exr = art25(sr, dr, CU, ded1, mes, pb, f"{c} residual del P2P")
    pc, exc = colectivo(s, d, CU, ded4, mes, pb, pesos(q + sr, mes), f"{c} P2P colectivo")
    co, exo = colectivo(sr, dr, CU, ded4, mes, pb, pesos(sr, mes), f"{c} v01 (residual propio al colectivo)")
    # Sensibilidad con el reparto igual: puede dejar exceso en horas sin bolsa
    # reconstruida. No se rellena: se acota con la bolsa en 0 y en su máximo
    # observado en esas horas, y se publican las dos cotas.
    pbf = pb[np.isfinite(pb)]
    pb_lo = np.where(np.isfinite(pb), pb, 0.0) if pbf.size else pb
    pb_hi = np.where(np.isfinite(pb), pb, float(pbf.max()) if pbf.size else np.nan)
    ce_lo, exe = colectivo(sr, dr, CU, ded4, mes, pb_lo, igual, f"{c} v01 igual (cota inferior)")
    ce_hi, _ = colectivo(sr, dr, CU, ded4, mes, pb_hi, igual, f"{c} v01 igual (cota superior)")
    ahorro = CU * q                                     # el comprador ahorra su CU (supuesto 2)
    out = dict(
        C1=auto + c1, C4=auto + c4, P2P=auto + ahorro + rp, P2P_colectivo=auto + pc,
        v01=auto + ahorro + co, v01_igual_min=auto + ahorro + ce_lo, v01_igual_max=auto + ahorro + ce_hi,
        v10=auto + ahorro - ded4 * q + rp, v10_theta=auto + ahorro - L["Th"] * q + rp)
    exc_kwh = dict(C1=ex1, C4=ex4, P2P=exr, P2P_colectivo=exc, v01=exo, v01_igual=exe, v10=exr, v10_theta=exr)
    return out, exc_kwh


# ── La bolsa reconstruida ───────────────────────────────────────────────────
def bolsa(DAT: dict) -> tuple[np.ndarray, pd.DataFrame]:
    # (a) el piso desde el corte hx del residual
    obs = []
    for c, L in DAT.items():
        perm = precio_permuta_por_periodo(L["CU"], L["ded1"], L["mes"])
        m = np.abs(L["piso"] - perm) > 1e-2
        k = np.nonzero(m)[1]
        obs.append(pd.DataFrame({"hora": k, "pb": L["piso"][m], "caso": c}))
    P = pd.concat(obs, ignore_index=True)
    rng = P.groupby("hora").pb.agg(lambda x: x.max() - x.min())
    exige(float(rng.max()) <= 1e-3, f"bolsa del piso distinta entre casos en una misma hora ({rng.max():.4f})")
    pa = P.groupby("hora").pb.first()
    exige(bool((pa > 0).all()), "bolsa del piso no positiva")
    ok(f"bolsa (a): el piso desde hx da {len(pa)} horas, idéntico entre los 13 casos (rango ≤ 1e-3)")
    # (b) despejada de la tabla escenarios, con exceso y bolsa 0
    cero = np.zeros(6144)
    obs = []
    for c, L in DAT.items():
        out, exk = esquinas(L, cero)
        for mec in ["C1", "C4", "P2P", "P2P_colectivo"]:
            ex = exk[mec].sum(axis=0)
            m = ex > 1e-4
            pbk = (L["por_hora"][mec].to_numpy() - out[mec].sum(axis=0))[m] / ex[m]
            obs.append(pd.DataFrame({"hora": np.flatnonzero(m), "pb": pbk, "ex": ex[m], "fuente": f"{c}/{mec}"}))
    O = pd.concat(obs, ignore_index=True)
    finito(O.pb, "bolsa despejada")
    grande = O[O.ex >= 0.01]
    comun = grande[grande.hora.isin(pa.index)]
    dif = (comun.pb - pa.reindex(comun.hora).to_numpy()).abs()
    exige(float(dif.max()) <= 0.25, f"bolsa despejada y bolsa del piso difieren en {dif.max():.3f} COP/kWh")
    ok(f"bolsa (b) despejada de escenarios coincide con (a) en {comun.hora.nunique()} horas comunes "
       f"(diferencia máxima {dif.max():.3f} COP/kWh con exceso ≥ 0,01 kWh)")
    pb_b = O.loc[O.groupby("hora").ex.idxmax()].set_index("hora")
    solo_b = pb_b[~pb_b.index.isin(pa.index)]
    pb = np.full(6144, np.nan)
    pb[pa.index.to_numpy()] = pa.to_numpy()
    pb[solo_b.index.to_numpy()] = solo_b.pb.to_numpy()
    exige(bool((pb[np.isfinite(pb)] > 0).all()), "bolsa no positiva")
    tabla = pd.concat([pd.DataFrame({"hora": pa.index, "bolsa": pa.to_numpy(), "fuente": "piso"}),
                       pd.DataFrame({"hora": solo_b.index, "bolsa": solo_b.pb.to_numpy(),
                                     "fuente": "escenarios:" + solo_b.fuente})]).sort_values("hora")
    ok(f"bolsa: {len(pa)} horas del piso y {len(solo_b)} despejadas de escenarios; {int(np.isfinite(pb).sum())} de 6144")
    return pb, tabla


def main() -> int:
    TT = tarifas()
    cap = capacidades()
    print("[atribucion] 1. almacenes de los 13 casos")
    DAT = {c: carga(c, TT, cap) for c in CASOS}
    ok("flujos: vende_p2p y compra_p2p del almacén = almacén de flujos (≤ 1e-3 kWh) y lo vendido = lo comprado por hora, en los 13 casos")
    print("[atribucion] 2. la bolsa")
    pb, tabla_pb = bolsa(DAT)
    print("[atribucion] 3. esquinas y reproducción")
    filas = []
    for c, L in DAT.items():
        R = resumen(c)
        out, exk = esquinas(L, pb)
        tol = max(1.0, 1e-7 * abs(R["P2P"]))
        for mec in ["C1", "C4", "P2P", "P2P_colectivo"]:
            alm = float(L["por_agente"][mec].sum())
            exige(abs(alm - R[mec]) <= tol, f"{c} {mec}: el almacén no suma la hoja Resumen ({alm - R[mec]:.2f})")
            dif = float(out[mec].sum()) - R[mec]
            exige(abs(dif) <= tol, f"{c} {mec}: la reliquidación difiere de Resumen en {dif:.2f} COP")
        for mec in ["C1", "C4"]:
            dif = np.abs(out[mec].sum(axis=1) - L["por_agente"][mec].to_numpy())
            exige(float(dif.max()) <= 1.0, f"{c} {mec}: por institución difiere en {dif.max():.3f} COP")
        # exceso valorado con bolsa despejada (fuente b): cota del error
        solo_b = tabla_pb[tabla_pb.fuente != "piso"].hora.to_numpy()
        f = dict(caso=c)
        for k, x in out.items():
            f[k] = float(x.sum())
        for k in ["v01", "C4", "P2P_colectivo", "P2P", "C1"]:
            f[f"exceso_kwh__{k}"] = float(exk[k].sum())
            f[f"exceso_kwh_bolsa_b__{k}"] = float(exk[k][:, solo_b].sum())
        f["inyeccion_kwh"] = float(L["s"].sum())
        f["transado_kwh"] = float(L["q"].sum())
        f["importacion_kwh"] = float(L["d"].sum())
        filas.append(f)
    ok("reliquidación: C1, C4, P2P y P2P colectivo de la comunidad = hoja Resumen (≤ máx(1 COP, 1e-7·P2P)) y C1 y C4 "
       "por institución = almacén (≤ 1 COP), en los 13 casos")
    A = pd.DataFrame(filas).set_index("caso")
    A["P2P_menos_C4"] = A.P2P - A.C4
    # (I) Los dos órdenes con las esquinas de un solo supuesto C1 (solo el 1:
    # cada miembro liquida su inyección por el art. 25; el texto) y v01 (solo
    # el 2: intercambio exento, residual al colectivo; el revisor).
    A["texto_s1"] = A.C1 - A.C4                    # orden C4 -> C1 -> P2P
    A["texto_s2"] = A.P2P - A.C1
    A["inverso_s2"] = A.v01 - A.C4                 # orden C4 -> v01 -> P2P
    A["inverso_s1"] = A.P2P - A.v01
    A["shapley_s1"] = 0.5 * (A.texto_s1 + A.inverso_s1)
    A["shapley_s2"] = 0.5 * (A.texto_s2 + A.inverso_s2)
    A["interaccion"] = A.inverso_s1 - A.texto_s1   # s1 con s2 menos s1 sin s2 (< 0: sustitutos)
    # (II) El cuadro 2 x 2 mecánico, con el mercado y sus flujos fijos en las
    # cuatro esquinas: v00 = P2P colectivo, v10 = el intercambio paga la
    # deducción del caso 2 aunque no le convenga.
    A["mercado_sin_supuestos"] = A.P2P_colectivo - A.C4
    A["fijos_s1_con_s2"] = A.P2P - A.v01
    A["fijos_s1_sin_s2"] = A.v10 - A.P2P_colectivo
    A["fijos_s2_con_s1"] = A.P2P - A.v10
    A["fijos_s2_sin_s1"] = A.v01 - A.P2P_colectivo
    A["fijos_interaccion"] = A.fijos_s1_con_s2 - A.fijos_s1_sin_s2
    A["fijos_v10_menos_C1"] = A.v10 - A.C1
    A["fijos_s2_con_s1_solo_theta"] = A.P2P - A.v10_theta
    # sensibilidad: el residual al colectivo con el reparto igual (art. 9)
    A["inverso_s1_reparto_igual_min"] = A.P2P - A.v01_igual_max
    A["inverso_s1_reparto_igual_max"] = A.P2P - A.v01_igual_min
    ancho = (A.v01_igual_max - A.v01_igual_min).abs()
    exige(float(ancho.max()) <= 0.05 * M, f"la cota del reparto igual es ancha: {ancho.max():.0f} COP")
    ok(f"sensibilidad del reparto igual acotada: ancho máximo de la cota {ancho.max():.0f} COP "
       f"(exceso en horas sin bolsa en {', '.join(A.index[ancho > 0]) or 'ningún caso'})")
    A["transado_sobre_inyeccion"] = A.transado_kwh / A.inyeccion_kwh
    for k in ["texto_s1", "texto_s2", "inverso_s1", "inverso_s2", "shapley_s1", "shapley_s2", "mercado_sin_supuestos"]:
        A[f"parte__{k}"] = A[k] / A.P2P_menos_C4
    # ¿Es C1 la esquina exacta de «solo el supuesto 1»? Lo es si, pagando el
    # intercambio la deducción del caso 2, ningún par transado gana: el techo
    # del comprador menos esa deducción no supera el piso del vendedor.
    gan = {}
    for c, L in DAT.items():
        fl = almacen(c, "flujos").astype({"techo_comprador": "float64", "piso_vendedor": "float64"})
        ags = L["ags"]
        iag = fl.comprador.map({a: i for i, a in enumerate(ags)}).to_numpy()
        ded_i = L["ded4"][iag, fl.hora.to_numpy()]
        g = fl.techo_comprador.to_numpy() - ded_i - fl.piso_vendedor.to_numpy()
        finito(g, f"{c} ganancia del intercambio con cargos")
        gan[c] = float(g.max())
    A["ganancia_max_intercambio_con_cargos"] = pd.Series(gan)
    exactos = [c for c in CASOS if gan[c] < 0]
    exige(set(["E0", "K1", "CV2", "SINU"]) <= set(exactos),
          f"en E0, K1, CV2 o SINU algún par ganaría transando con cargos: {gan}")
    ok(f"pagando el intercambio la deducción del caso 2, ningún par transado gana en {', '.join(exactos)}: "
       "allí C1 es exactamente la esquina «solo el supuesto 1» (nadie transaría)")
    A["c1_esquina_exacta"] = [int(c in exactos) for c in A.index]
    # compuertas de las identidades
    tol = 1e-6 * float(A.P2P.abs().max())
    for k1, k2 in [("texto_s1", "texto_s2"), ("inverso_s1", "inverso_s2"), ("shapley_s1", "shapley_s2")]:
        cierre = (A[k1] + A[k2] - A.P2P_menos_C4).abs()
        exige(float(cierre.max()) <= tol, f"{k1} + {k2} no cierra: {cierre.max():.3f}")
    cierre = (A.mercado_sin_supuestos + A.fijos_s1_con_s2 + A.fijos_s2_sin_s1 - A.P2P_menos_C4).abs()
    exige(float(cierre.max()) <= tol, "el cuadro con flujos fijos no cierra")
    ok("identidades: los dos órdenes y Shapley suman P2P − C4; el cuadro con flujos fijos suma P2P − C4 "
       "con el mercado sin supuestos")
    inter0 = A.loc[SIN_AGOTAR, "fijos_interaccion"].abs()
    exige(float(inter0.max()) <= 2.0, f"interacción con flujos fijos no nula donde nadie agota el cupo: {inter0.max():.2f} COP")
    ok(f"con los flujos fijos y nadie agotando el cupo (E0, P2, K1, CV2, SINU) la interacción es cero (≤ {inter0.max():.2f} COP)")
    s2 = (A.fijos_s2_con_s1 - pd.Series({c: float((DAT[c]["ded4"] * DAT[c]["q"]).sum()) for c in CASOS})).abs()
    exige(float(s2.max()) <= 1e-6, "fijos_s2_con_s1 no es la deducción del caso 2 sobre lo transado")
    ok("con los flujos fijos, s2 dado s1 = Σ (kappa·Cv + Theta) del comprador × kWh transados, exacto")
    # contra el canon: C1 − C4 y P2P − C1 de la hoja Resumen (cifras_articulo los cita)
    for c in CASOS:
        R = resumen(c)
        exige(abs(A.loc[c, "texto_s1"] - (R["C1"] - R["C4"])) <= max(2.0, 2e-7 * abs(R["P2P"])), f"{c}: C1 − C4 distinto de Resumen")
    ok("C1 − C4 reliquidado = el de la hoja Resumen en los 13 casos")
    # salida
    SALIDA.mkdir(parents=True, exist_ok=True)
    A.reset_index().to_csv(SALIDA / "atribucion_13casos.csv", index=False, encoding="utf-8", lineterminator="\n",
                           float_format="%.6f")
    tabla_pb.to_csv(SALIDA / "bolsa_reconstruida.csv", index=False, encoding="utf-8", lineterminator="\n",
                    float_format="%.6f")
    guion = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    sucio = git("status", "--short", "--untracked-files=all", "--", guion)
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("atribucion_supuestos.py: atribución de P2P − C4 a los dos supuestos (hallazgo I-1, tarea B1)\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n" + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + guion + "\n")
        fh.write("NO registrado en HUELLAS.csv\n")
        fh.write(f"huellas: {HUELLAS.relative_to(RAIZ).as_posix()}; {len(LEIDOS)} artefactos leídos, todos con la huella comprobada:\n")
        for g, r in LEIDOS:
            fh.write(f"  {g}  {r}\n")
        fh.write(f"compuertas: {len(COMPUERTAS)}, todas OK:\n")
        for cpt in COMPUERTAS:
            fh.write(f"  OK  {cpt}\n")
        fh.write(f"filas: {len(A)}\n")
        fh.write("sin fecha: la hora de la corrida solo se imprime en la consola\n")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    cols = ["P2P_menos_C4", "texto_s1", "texto_s2", "inverso_s2", "inverso_s1", "shapley_s1", "shapley_s2",
            "interaccion", "mercado_sin_supuestos", "fijos_s1_sin_s2", "fijos_interaccion", "fijos_v10_menos_C1"]
    print((A[cols] / M).round(3))
    print(A[["transado_kwh", "inyeccion_kwh", "transado_sobre_inyeccion", "parte__texto_s1", "parte__inverso_s1",
             "parte__shapley_s1", "ganancia_max_intercambio_con_cargos", "c1_esquina_exacta"]].round(3))
    print((A[["inverso_s1", "inverso_s1_reparto_igual_min", "inverso_s1_reparto_igual_max",
              "fijos_s2_con_s1", "fijos_s2_con_s1_solo_theta"]] / M).round(3))
    print(f"[atribucion] corrida del {_dt.datetime.now().isoformat(timespec='seconds')}")
    print(f"[atribucion] {len(LEIDOS)} artefactos, {len(COMPUERTAS)} compuertas; salida en {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
