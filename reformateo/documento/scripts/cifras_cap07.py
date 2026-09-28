"""
cifras_cap07.py — Las cifras derivadas que cita el capítulo 7 de la tesis
(Comparación de desempeño) y que `CANON.md` no escribe tal cual (C-230).
===============================================================================
Decisión del controlador, ronda 2 del capítulo 7 (2026-09-28): toda cifra del
capítulo que no esté escrita tal cual en `Documentos/canon_2026-09/CANON.md`
sale de este guion. No simula nada: solo lee artefactos que tienen huella en
`Documentos/canon_2026-09/HUELLAS.csv`, y antes de leer cada uno comprueba su
tamaño y su `sha256` contra esa huella.

Qué calcula:

1. La comunidad (hoja `Resumen` de los 13 casos): las brechas entre
   mecanismos, sus porcentajes, el orden de los mecanismos, C1 − C4 como parte
   de P2P − C4, el máximo y el mínimo de P2P − C3, y las identidades P2P = C2 y
   C4 = C4 mensual.
2. Las horas con vendedores y compradores a la vez (tabla `horas` del almacén,
   régimen no nulo), contrastadas con 6 144 − «sin ids» de CANON §4.
3. El factor de coincidencia de los 13 casos (hoja `Coincidencia`).
4. El Gini de los siete mecanismos en E0 y, en los 13 casos, en cuántos el
   mercado reparte con menos desigualdad que C1, C3, C4 y C5 (hoja
   `PoF_Fairness`).
5. Las brechas por institución P2P − C1, P2P − C4 y P2P − C5 de los 64 pares
   (`compara_matriz_reposo.csv`), con la comprobación de P2P − C4 contra
   `optimalidad_D72/resumen_13casos.csv`, los recuentos de pares negativos, los
   extremos, y los meses por institución de E0.
6. La liquidación por institución de E0 (`figuras_foro/foro_d1_liquidacion_m1.csv`),
   contrastada con el bloque «EN UNA FRASE» del registro de liquidación, el
   mecanismo «mejor» de cada mes del registro, y el reparto del excedente
   (`foro_e3_reparto_m1.csv`).
7. Las reglas de reparto del colectivo: las de E0 (hoja `Contrafacticos`) y,
   en los 13 casos, las cuatro reglas frente al mercado
   (`spread_estatico_2026-09-27/spread_13casos.csv`), con E4 frente al mercado
   y frente al mercado por la vía del colectivo, y el efecto del COT en E4
   (`contrafactico_techo_cot_2026-09-28/brechas_13casos.csv`).
8. Los subperíodos por tercil de demanda (`subperiodos_2026-09-27/meses_condicion.csv`),
   con la comprobación de la tabla de meses de CANON §14.9.
9. Los recuentos de signos frágiles de la caja del GSA
   (`gsa_directo/<caso>/inversion_<caso>.csv`).

Falla en voz alta: ningún `except` que trague, ningún NaN rellenado; una
huella que no cuadra, una cifra no finita, una clave repetida o una compuerta
que no cierra es un error.

Escribe en SALIDAS_SERVIDOR/cifras_cap07_2026-09-28/:

    cifras.csv        clave, valor, unidad, definicion, fuente
    procedencia.txt   commit, estado del árbol, versiones, orden y huellas leídas

    PYTHONUNBUFFERED=1 python -u reformateo/documento/scripts/cifras_cap07.py

Actividades 3.2 y 3.3.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import math
import platform
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
HUELLAS = RAIZ / "Documentos" / "canon_2026-09" / "HUELLAS.csv"
SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
BASE_MATRIZ = SALIDAS / "entrega_matriz_reposo_2026-09-19"
BASE_GSA = SALIDAS / "entrega_gsa_directo_completo_2026-09-27"
SALIDA = SALIDAS / "cifras_cap07_2026-09-28"

CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU"]
CASOS_GSA = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
             "SINU"]
INST = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
MECS = ["P2P", "P2P_colectivo", "C1", "C2", "C3", "C4", "C5"]
MEJOR = {"P2P", "C1", "C2", "C3", "C4", "C5"}
# CANON §4, tabla de horas por régimen, columna «sin ids» (compuerta del punto 2)
SIN_IDS = {"E0": 5018, "E1": 4390, "E2": 4522, "E3": 4748, "E4": 4959,
           "E5": 5224, "P1": 4959, "P2": 5018, "K1": 5554, "I1": 4362,
           "N1": 5001, "CV2": 5018, "SINU": 5542}
# CANON §14.9, tabla de meses (compuerta del punto 8), en MCOP
MESES_1492 = {("generacion", "bajo"): (0.31, 1.12), ("generacion", "medio"): (0.40, 1.27),
              ("generacion", "alto"): (0.44, 1.35), ("bolsa", "bajo"): (0.45, 1.41),
              ("bolsa", "medio"): (0.35, 1.23), ("bolsa", "alto"): (0.33, 1.11)}

FILAS: list[dict] = []
LEIDOS: list[tuple[str, str]] = []


class CifraError(RuntimeError):
    pass


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise CifraError(msg)


def pon(clave: str, valor, unidad: str, definicion: str, fuente: str) -> None:
    """Añade una cifra. Falla si no es finita o si la clave ya existe."""
    exige(not any(f["clave"] == clave for f in FILAS), f"clave repetida: {clave}")
    if isinstance(valor, (bool, np.bool_)):
        valor = int(valor)
    if isinstance(valor, (int, float, np.integer, np.floating)):
        exige(math.isfinite(float(valor)), f"{clave}: valor no finito {valor!r}")
        valor = int(valor) if isinstance(valor, (int, np.integer)) else float(valor)
    else:
        exige(isinstance(valor, str) and bool(valor), f"{clave}: valor vacío")
    FILAS.append(dict(clave=clave, valor=valor, unidad=unidad,
                      definicion=definicion, fuente=fuente))


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True,
                       text=True, check=True)
    return r.stdout.rstrip("\n")


# ── Huellas ─────────────────────────────────────────────────────────────────
_H = pd.read_csv(HUELLAS)
exige(list(_H.columns) == ["grupo", "ruta", "bytes", "sha256"],
      f"cabecera inesperada en {HUELLAS}")


def _base(grupo: str) -> Path:
    if grupo.startswith("gsa/"):
        return BASE_GSA
    if grupo.startswith("e1/"):
        return SALIDAS
    return BASE_MATRIZ


def lee(ruta: str, grupo: str | None = None) -> Path:
    """Devuelve la ruta del artefacto tras comprobar su huella; falla si no la tiene."""
    f = _H[_H.ruta == ruta]
    if grupo is not None:
        f = f[f.grupo == grupo]
    exige(len(f) == 1, f"{ruta}: {len(f)} filas en HUELLAS.csv (se esperaba 1)")
    fila = f.iloc[0]
    p = _base(fila.grupo) / ruta
    exige(p.is_file(), f"no existe {p}")
    datos = p.read_bytes()
    exige(len(datos) == int(fila.bytes), f"{ruta}: {len(datos)} bytes, huella {fila.bytes}")
    exige(hashlib.sha256(datos).hexdigest() == fila.sha256, f"{ruta}: sha256 distinto de la huella")
    if (fila.grupo, ruta) not in LEIDOS:
        LEIDOS.append((fila.grupo, ruta))
    return p


def libro(caso: str) -> Path:
    return lee(f"SALIDAS_SERVIDOR/matriz_reposo/{caso}/outputs/resultados_comparacion.xlsx")


def hoja(caso: str, nombre: str) -> pd.DataFrame:
    return pd.read_excel(libro(caso), sheet_name=nombre)


def finito(s: pd.Series, qué: str) -> pd.Series:
    exige(bool(np.isfinite(s.to_numpy(dtype=float)).all()), f"{qué}: valores no finitos")
    return s


F_RES = "hoja Resumen de M19/<caso>/outputs/resultados_comparacion.xlsx"


# ── 1. La comunidad ─────────────────────────────────────────────────────────
def comunidad() -> pd.DataFrame:
    R = {}
    for c in CASOS:
        r = hoja(c, "Resumen").set_index("Escenario")["Ganancia_neta_COP"]
        finito(r, f"Resumen {c}")
        exige(abs(r["C4_mensual"] - r["C4"]) == 0.0, f"{c}: C4 mensual distinto de C4")
        exige(abs(r["P2P"] - r["C2"]) <= 1e-6, f"{c}: P2P distinto de C2 en el agregado")
        R[c] = r
    R = pd.DataFrame(R).T
    M = 1e6
    for c in CASOS:
        r = R.loc[c]
        for nom, v in [("P2P_menos_C1", r.P2P - r.C1), ("P2P_menos_C3", r.P2P - r.C3),
                       ("P2P_menos_C4", r.P2P - r.C4), ("P2P_menos_C5", r.P2P - r.C5),
                       ("colectivo_menos_C1", r.P2P_colectivo - r.C1),
                       ("colectivo_menos_C4", r.P2P_colectivo - r.C4),
                       ("C1_menos_C4", r.C1 - r.C4)]:
            pon(f"comunidad__{c}__{nom}", v / M, "MCOP", f"{nom} de la comunidad", F_RES + ", resta")
        pon(f"comunidad__{c}__P2P_menos_C1_pct_C1", 100 * (r.P2P - r.C1) / r.C1, "%",
            "P2P − C1 sobre C1", F_RES + ", cociente")
        pon(f"comunidad__{c}__P2P_menos_C4_pct_C4", 100 * (r.P2P - r.C4) / r.C4, "%",
            "P2P − C4 sobre C4", F_RES + ", cociente")
        pon(f"comunidad__{c}__colectivo_menos_C4_pct_C4", 100 * (r.P2P_colectivo - r.C4) / r.C4, "%",
            "P2P colectivo − C4 sobre C4", F_RES + ", cociente")
        if r.C1 > r.C4:
            pon(f"comunidad__{c}__C1_menos_C4_pct_P2P_menos_C4", 100 * (r.C1 - r.C4) / (r.P2P - r.C4),
                "%", "(C1 − C4) / (P2P − C4), donde C1 supera a C4", F_RES + ", cociente")
    # el orden de los mecanismos (sin C2 ni C4 mensual)
    O = R.drop(columns=["C2", "C4_mensual"])
    orden = {c: list(O.loc[c].sort_values(ascending=False).index) for c in CASOS}
    pon("orden__casos_P2P_primero", sum(o[0] == "P2P" for o in orden.values()), "casos",
        "casos en que el mercado deja más que cualquier otro mecanismo", F_RES + ", orden")
    pon("orden__casos_C3_ultimo", sum(o[-1] == "C3" for o in orden.values()), "casos",
        "casos en que C3 deja menos que cualquier otro mecanismo", F_RES + ", orden")
    pon("orden__casos_C1_segundo", sum(o[1] == "C1" for o in orden.values()), "casos",
        "casos en que C1 queda segundo", F_RES + ", orden")
    pon("orden__casos_C4_segundo", ", ".join(c for c, o in orden.items() if o[1] == "C4"), "casos",
        "casos en que C4 queda segundo", F_RES + ", orden")
    pon("orden__casos_C5_sobre_C4", ", ".join(c for c in CASOS if R.loc[c, "C5"] > R.loc[c, "C4"]),
        "casos", "casos en que C5 deja más que C4", F_RES + ", orden")
    d3 = (R.P2P - R.C3) / M
    pon("comunidad__P2P_menos_C3_min", float(d3.min()), "MCOP", f"mínimo de P2P − C3 ({d3.idxmin()})", F_RES)
    pon("comunidad__P2P_menos_C3_max", float(d3.max()), "MCOP", f"máximo de P2P − C3 ({d3.idxmax()})", F_RES)
    pc = (R.P2P_colectivo - R.C1)
    pon("comunidad__colectivo_sobre_C1_casos", ", ".join(c for c in CASOS if pc[c] > 0), "casos",
        "casos con el mercado por la vía del colectivo por encima de C1", F_RES)
    pon("comunidad__P2_sobre_E0_energia", 32144.14 / 4592.02, "veces",
        "energía transada de P2 sobre la de E0 (CANON §4)", "CANON §4, cociente")
    pon("comunidad__P2_sobre_E0_banda", 10.659 / 0.296, "veces",
        "banda de P2 sobre la de E0 (CANON §14.8)", "CANON §14.8, cociente")
    pon("comunidad__E0_SS_C2", float(hoja("E0", "Resumen").set_index("Escenario").loc["C2", "SS"]),
        "fracción", "autosuficiencia que reporta el modelo para C2 en E0", F_RES + " (E0), columna SS")
    return R


# ── 2. Horas con vendedores y compradores ───────────────────────────────────
def horas() -> None:
    for c in CASOS:
        h = pd.read_parquet(lee(f"SALIDAS_SERVIDOR/matriz_reposo/{c}/almacen/m1/horas/parte_0000.parquet"))
        exige(len(h) == 6144, f"{c}: la tabla horas no tiene 6 144 filas")
        n = int(h["regimen"].notna().sum())
        exige(n == 6144 - SIN_IDS[c], f"{c}: {n} horas con régimen frente a {6144 - SIN_IDS[c]} de CANON §4")
        pon(f"horas_con_ambos_lados__{c}", n, "h",
            "horas con vendedores y compradores a la vez (régimen no nulo; = 6 144 − «sin ids» de CANON §4)",
            f"almacén {c}, tabla horas, columna regimen")


# ── 3. Factor de coincidencia ───────────────────────────────────────────────
def coincidencia() -> None:
    V = {}
    for c in CASOS:
        k = hoja(c, "Coincidencia").set_index("escenario")["valor"]
        exige(bool(np.isnan(k["C3"])), f"{c}: C3 debería no tener factor")
        exige(k["P2P"] == k["C2"], f"{c}: coincidencia de P2P distinta de C2")
        exige(k["C4"] == k["C4_mensual"], f"{c}: coincidencia de C4 distinta del alias")
        exige(k["C1"] == 0.0 and k["C5"] == 1.0, f"{c}: C1 o C5 fuera de construcción")
        for m in ["C1", "C4", "P2P_colectivo", "P2P", "C5"]:
            pon(f"coincidencia__{c}__{m}", float(k[m]), "fracción",
                f"factor de coincidencia de {m} (D20)", f"hoja Coincidencia de M19/{c}")
        V[c] = k
    V = pd.DataFrame(V).T
    fuera = V[["C1", "C4", "P2P_colectivo"]].max(axis=1)
    pon("coincidencia__casos_P2P_max_sin_C5", int((V.P2P >= fuera).sum()), "casos",
        "casos en que el mercado tiene el factor más alto fuera de C5", "hoja Coincidencia de los 13 casos")


# ── 4. Gini ─────────────────────────────────────────────────────────────────
def gini() -> None:
    G = {}
    for c in CASOS:
        g = hoja(c, "PoF_Fairness").set_index("escenario")["gini"]
        finito(g, f"PoF_Fairness {c}")
        exige(g["C4"] == g["C4_mensual"], f"{c}: Gini de C4 distinto del alias")
        G[c] = g
    G = pd.DataFrame(G).T
    for m in MECS:
        pon(f"gini__E0__{m}", float(G.loc["E0", m]), "índice", f"Gini del beneficio por institución, {m}, E0",
            "hoja PoF_Fairness de M19/E0")
    for m in ["C1", "C3", "C4", "C5"]:
        pon(f"gini__casos_P2P_menor_que_{m}", int((G.P2P < G[m]).sum()), "casos",
            f"casos en que el Gini del mercado es menor que el de {m}", "hoja PoF_Fairness de los 13 casos")


# ── 5. Por institución ──────────────────────────────────────────────────────
def instituciones() -> None:
    d = pd.read_csv(lee("compara_matriz_reposo.csv"), comment="#")
    d = d[d.institucion != "comunidad"].copy()
    exige(len(d) == 64, f"compara: {len(d)} pares, se esperaban 64")
    r = pd.read_csv(lee("optimalidad_D72/resumen_13casos.csv"))
    ri = r[r.agente != "Comunidad"].rename(columns={"agente": "institucion"})
    m = d.merge(ri[["caso", "institucion", "delta_COP", "meses_P2P", "meses"]], on=["caso", "institucion"])
    exige(len(m) == 64, "el cruce compara-D72 no da 64 pares")
    dif = float((m.delta_COP - m.P2P_menos_C4_nueva).abs().max())
    exige(dif <= 1.0, f"P2P − C4 por institución: compara y D72 difieren {dif} COP")
    pon("institucion__P2P_menos_C4_dif_max_compara_D72", dif, "COP",
        "diferencia máxima entre compara y D72 en P2P − C4 por institución", "compara_matriz_reposo.csv y resumen_13casos.csv")
    F = "compara_matriz_reposo.csv, filas por institución, columna {}"
    for col, nom in [("P2P_menos_C1_nueva", "C1"), ("P2P_menos_C4_nueva", "C4"), ("P2P_menos_C5_nueva", "C5")]:
        finito(m[col], col)
        neg = m[m[col] < 0]
        pon(f"institucion__P2P_menos_{nom}__negativos", len(neg), "pares de 64",
            f"pares institución-caso con P2P − {nom} negativo", F.format(col))
        imin, imax = m[col].idxmin(), m[col].idxmax()
        pon(f"institucion__P2P_menos_{nom}__min", float(m.loc[imin, col]), "COP",
            f"mínimo de P2P − {nom} por institución ({m.loc[imin, 'caso']} {m.loc[imin, 'institucion']})", F.format(col))
        pon(f"institucion__P2P_menos_{nom}__max", float(m.loc[imax, col]), "COP",
            f"máximo de P2P − {nom} por institución ({m.loc[imax, 'caso']} {m.loc[imax, 'institucion']})", F.format(col))
        if nom != "C4":
            pon(f"institucion__P2P_menos_{nom}__lista_negativos",
                "; ".join(f"{a.caso} {a.institucion} {getattr(a, col):.0f}" for a in neg.itertuples())
                or "ninguno",
                "COP", f"pares con P2P − {nom} negativo", F.format(col))
    for a in m.itertuples():
        pon(f"institucion__{a.caso}__{a.institucion}__P2P_menos_C4", float(a.delta_COP), "COP",
            "P2P − C4 de la institución en el horizonte", "optimalidad_D72/resumen_13casos.csv, delta_COP")
    neg = m[m.P2P_menos_C4_nueva < 0].groupby("caso").size().reindex(CASOS, fill_value=0)
    n_inst = m.groupby("caso").size().reindex(CASOS)
    pon("institucion__casos_mayoria_bajo_C4", ", ".join(c for c in CASOS if neg[c] > n_inst[c] / 2),
        "casos", "casos con la mayoría de las instituciones bajo C4", "resumen_13casos.csv, conteo")
    pon("institucion__casos_ninguna_bajo_C4", ", ".join(c for c in CASOS if neg[c] == 0),
        "casos", "casos sin ninguna institución bajo C4", "resumen_13casos.csv, conteo")
    e0 = m[m.caso == "E0"]
    pon("institucion__E0__suma_cuatro_bajo_C4", float(e0[e0.delta_COP < 0].delta_COP.sum()), "COP",
        "suma de P2P − C4 de las cuatro instituciones de E0 bajo C4", "resumen_13casos.csv, suma")
    for a in e0.itertuples():
        exige(a.meses == 9, "E0: una institución sin nueve meses")
        pon(f"meses_P2P_sobre_C4__E0__{a.institucion}", int(a.meses_P2P), "meses de 9",
            "meses en que el mercado le deja a la institución más que C4", "resumen_13casos.csv, meses_P2P")


# ── 6. La liquidación de E0 ─────────────────────────────────────────────────
def liquidacion() -> None:
    f = pd.read_csv(lee("SALIDAS_SERVIDOR/matriz_reposo/figuras_foro/foro_d1_liquidacion_m1.csv"),
                    encoding="utf-8-sig").set_index("agente")
    exige(list(f.index) == INST, "foro_d1: instituciones fuera de orden")
    finito(f.stack(), "foro_d1")
    exige(np.allclose(f.dv / f.kdv, f.dentro_vende) and np.allclose(f.dc / f.kdc, f.dentro_compra),
          "foro_d1: los precios de dentro no son los cocientes")
    exige(abs(f.kdv.sum() - 4592.02) < 0.01 and abs(f.kdc.sum() - 4592.02) < 0.02,
          "foro_d1: la energía de dentro no suma la de CANON §4")
    log = lee("modelo_base/logs/matriz_reposo_liquidacion_E0_2026-09-19_1734.log").read_text(encoding="utf-8")
    num = lambda s: float(s.replace(",", "."))
    for i in INST:
        mp = re.search(rf"A {i} la red le paga el excedente a ([\d,]+) COP/kWh; dentro de la comunidad lo vende a ([\d,]+)\.", log)
        mc = re.search(rf"A {i} la red le cobra la energía a ([\d,]+) COP/kWh; dentro de la comunidad la compra a ([\d,]+)\.", log)
        exige(mp is not None and mc is not None, f"registro: sin la frase de {i}")
        for reg, col in [(mp.group(1), "red_paga"), (mp.group(2), "dentro_vende"),
                         (mc.group(1), "red_cobra"), (mc.group(2), "dentro_compra")]:
            exige(abs(num(reg) - f.loc[i, col]) <= 0.051, f"{i}: {col} del CSV no reproduce el registro")
        for col, u, dfn in [("kdv", "kWh", "energía vendida dentro"), ("dentro_vende", "COP/kWh", "precio medio de venta dentro"),
                            ("red_paga", "COP/kWh", "precio medio al que la red le paga el excedente"),
                            ("kdc", "kWh", "energía comprada dentro"), ("dentro_compra", "COP/kWh", "precio medio de compra dentro"),
                            ("red_cobra", "COP/kWh", "precio medio al que la red le cobra la energía")]:
            pon(f"liquidacion__E0__{i}__{col}", float(f.loc[i, col]), u, f"{dfn}, E0, horizonte",
                "figuras_foro/foro_d1_liquidacion_m1.csv (reproduce el registro de liquidación de E0)")
    pon("liquidacion__E0__Udenar_parte_vendida", 100 * f.loc["Udenar", "kdv"] / f.kdv.sum(), "%",
        "parte de la energía transada que vende Udenar", "foro_d1_liquidacion_m1.csv, kdv / suma")
    # el mecanismo «mejor» de cada mes
    tramo = log.split("Y LO QUE LE DEJAR", 1)
    exige(len(tramo) == 2, "registro: sin la tabla de mecanismos")
    cuenta: dict[str, dict[str, int]] = {i: {} for i in INST}
    for linea in tramo[1].splitlines():
        t = linea.split()
        if len(t) >= 3 and re.fullmatch(r"\d{4}-\d{2}", t[0]) and t[1] in INST and t[-1] in MEJOR:
            cuenta[t[1]][t[-1]] = cuenta[t[1]].get(t[-1], 0) + 1
    for i in INST:
        exige(sum(cuenta[i].values()) == 9, f"registro: {i} no tiene nueve meses en la tabla de mecanismos")
        pon(f"liquidacion__E0__{i}__mejor", "; ".join(f"{k} {v}" for k, v in sorted(cuenta[i].items())),
            "meses de 9", "mecanismo que más le deja cada mes (entre P2P, C1, C2, C3, C4 y C5)",
            "registro matriz_reposo_liquidacion_E0, columna «mejor», conteo")
    e3 = pd.read_csv(lee("SALIDAS_SERVIDOR/matriz_reposo/figuras_foro/foro_e3_reparto_m1.csv"),
                     encoding="utf-8-sig").set_index("reparto")
    pon("reparto__E0__mercado_vendedores_pct", float(e3.loc["mercado", "vendedores_pct"]), "%",
        "parte del excedente del mercado en los vendedores, E0", "figuras_foro/foro_e3_reparto_m1.csv")
    pon("reparto__E0__excedente", float(e3.loc["mercado", "excedente_COP"]), "COP",
        "excedente del mercado en E0", "figuras_foro/foro_e3_reparto_m1.csv")


# ── 7. Reglas de reparto ────────────────────────────────────────────────────
def reglas(R: pd.DataFrame) -> None:
    ct = hoja("E0", "Contrafacticos").set_index("contrafactico")["total_COP"]
    for k in ["C4_regla_consumo", "C4_regla_aporte", "C4_regla_generacion", "P2P_colectivo_11_fronteras"]:
        pon(f"reglas__E0__{k}", float(ct[k]) / 1e6, "MCOP", f"{k} en E0",
            "hoja Contrafacticos de M19/E0 (coincide con la carpeta, trampa 5 de CANON §10.0)")
    pon("reglas__E0__P2P_colectivo_11_fronteras_menos_P2P", float(ct["P2P_colectivo_11_fronteras"] - R.loc["E0", "P2P"]) / 1e6,
        "MCOP", "mercado por la vía del colectivo con 11 fronteras menos el mercado, E0",
        "hoja Contrafacticos y hoja Resumen de M19/E0, resta")
    s = pd.read_csv(lee("spread_estatico_2026-09-27/spread_13casos.csv")).set_index("caso")
    exige(sorted(s.index) == sorted(CASOS) and s.index.is_unique, "spread_13casos: faltan casos o hay repetidos")
    s = s.loc[CASOS]
    reglas_col = {"consumo": "C4_regla_consumo_COP", "aporte": "C4_regla_aporte_COP",
                  "generacion": "C4_regla_generacion_COP", "importacion": "C4_importacion_COP"}
    for c in CASOS:
        exige(abs(s.loc[c, "P2P_COP"] - R.loc[c, "P2P"]) <= 0.5, f"{c}: P2P del spread distinto de Resumen")
        exige(abs(s.loc[c, "C4_COP"] - R.loc[c, "C4"]) <= 0.5, f"{c}: C4 del spread distinto de Resumen")
        exige(abs(s.loc[c, "P2P_colectivo_COP"] - R.loc[c, "P2P_colectivo"]) <= 0.5, f"{c}: colectivo distinto")
    e4 = hoja("E4", "Contrafacticos").set_index("contrafactico")["total_COP"]
    exige(abs(e4["C4_regla_consumo"] - s.loc["E4", "C4_regla_consumo_COP"]) <= 0.5,
          "E4: la regla por consumo de la hoja no coincide con spread_13casos")
    dif = pd.DataFrame({k: s[v] - s.P2P_COP for k, v in reglas_col.items()})
    sup = dif[dif.max(axis=1) > 0]
    pon("reglas__casos_alguna_regla_sobre_P2P", ", ".join(sup.index), "casos",
        "casos en que alguna regla del colectivo deja más que el mercado", "spread_13casos.csv, resta")
    resto = dif.drop(index=sup.index)
    pon("reglas__resto__mas_cerca_del_P2P", float(resto.max(axis=1).max()) / 1e6, "MCOP",
        f"regla más cercana al mercado fuera de esos casos ({resto.max(axis=1).idxmax()}, "
        f"{resto.loc[resto.max(axis=1).idxmax()].idxmax()})", "spread_13casos.csv, resta")
    for k in reglas_col:
        pon(f"reglas__E4__{k}_menos_P2P", float(dif.loc["E4", k]) / 1e6, "MCOP",
            f"colectivo de E4 con la regla por {k} menos el mercado", "spread_13casos.csv, resta")
        pon(f"reglas__E4__{k}_menos_P2P_pct", 100 * float(dif.loc["E4", k]) / s.loc["E4", "P2P_COP"], "%",
            f"la misma diferencia sobre el beneficio del mercado de E4", "spread_13casos.csv, cociente")
    for k in ["consumo", "importacion"]:
        pon(f"reglas__E4__{k}_menos_colectivo", float(s.loc["E4", reglas_col[k]] - s.loc["E4", "P2P_colectivo_COP"]) / 1e6,
            "MCOP", f"colectivo de E4 con la regla por {k} menos el mercado por la vía del colectivo",
            "spread_13casos.csv, resta")
    b = pd.read_csv(lee("contrafactico_techo_cot_2026-09-28/brechas_13casos.csv"))
    fila = b[(b.caso == "E4") & (b.variante == "cot")]
    exige(len(fila) == 1, "brechas COT: sin la fila E4 cot")
    pon("reglas__E4__cot_d_P2P_menos_C4", float(fila.d_P2P_menos_C4_COP.iloc[0]), "COP",
        "cambio de P2P − C4 en E4 con el COT en la deducción", "contrafactico_techo_cot_2026-09-28/brechas_13casos.csv")


# ── 8. Subperíodos por demanda ──────────────────────────────────────────────
def subperiodos() -> None:
    m = pd.read_csv(lee("subperiodos_2026-09-27/meses_condicion.csv"))
    exige(len(m) == 117, f"meses_condicion: {len(m)} meses")
    finito(m.P2P_menos_C4, "P2P_menos_C4 por mes")
    for (cond, nivel), (e1, e4) in MESES_1492.items():
        g = m[m[f"t_{cond}"] == nivel]
        exige(len(g) == 39, f"{cond} {nivel}: {len(g)} meses")
        exige(abs(round(g.P2P_menos_C1.mean() / 1e6, 2) - e1) < 1e-9 and abs(round(g.P2P_menos_C4.mean() / 1e6, 2) - e4) < 1e-9,
              f"{cond} {nivel}: no reproduce CANON §14.9")
    for nivel in ["bajo", "medio", "alto"]:
        g = m[m.t_demanda == nivel]
        exige(len(g) == 39, f"demanda {nivel}: {len(g)} meses")
        pon(f"subperiodos__demanda_{nivel}__P2P_menos_C4", float(g.P2P_menos_C4.mean()) / 1e6, "MCOP",
            f"P2P − C4 medio por mes en el tercil {nivel} de demanda", "meses_condicion.csv, media")
        pon(f"subperiodos__demanda_{nivel}__P2P_menos_C1", float(g.P2P_menos_C1.mean()) / 1e6, "MCOP",
            f"P2P − C1 medio por mes en el tercil {nivel} de demanda", "meses_condicion.csv, media")
    pon("subperiodos__meses_bajo_C4_por_demanda", int((m.P2P_menos_C4 < 0).sum()), "meses",
        "meses con el mercado bajo C4", "meses_condicion.csv")


# ── 9. Signos frágiles de la caja ───────────────────────────────────────────
def fragiles() -> None:
    filas = []
    for c in CASOS_GSA:
        v = pd.read_csv(lee(f"SALIDAS_SERVIDOR/gsa_directo/{c}/inversion_{c}.csv"))
        v["caso"] = c
        filas.append(v)
    v = pd.concat(filas)
    finito(v.p_inversion, "p_inversion")
    inst = v[v.salida.str.contains("__")].copy()
    inst[["brecha", "institucion"]] = inst.salida.str.split("__", expand=True)
    for br in ["P2P_menos_C1", "P2P_menos_C4", "P2P_menos_C5"]:
        g = inst[inst.brecha == br]
        mayor = g[g.p_inversion > 0.5]
        medio = g[(g.p_inversion > 0.25) & (g.p_inversion <= 0.5)]
        pon(f"fragiles__{br}__p_mayor_50", len(mayor), "pares",
            f"pares institución-caso con P(inversión) de {br} de más del 50 %", "gsa_directo/<caso>/inversion_<caso>.csv")
        pon(f"fragiles__{br}__p_25_a_50", len(medio), "pares",
            f"pares con P(inversión) de {br} entre el 25 y el 50 %", "gsa_directo/<caso>/inversion_<caso>.csv")
        pon(f"fragiles__{br}__lista_mayor_25",
            "; ".join(f"{a.caso} {a.institucion} {100 * a.p_inversion:.2f}" for a in g[g.p_inversion > 0.25].itertuples()),
            "%", f"pares con P(inversión) de {br} de más del 25 %", "gsa_directo/<caso>/inversion_<caso>.csv")
    # CESMAG en N1 frente a C4 con el barrido de σ (CANON §14.4; ronda 3, R2)
    base_n1 = None
    for etiqueta, sigma in [("0", "0"), ("05", "0,5"), ("1", "1")]:
        c = pd.read_csv(lee(f"entrega_barrido_sigma_2026-09-27/compara_sigma{etiqueta}.csv", "e1/B1"), comment="#")
        f = c[(c.caso == "N1") & (c.institucion == "Cesmag")]
        exige(len(f) == 1, f"compara_sigma{etiqueta}: sin la fila N1 Cesmag")
        vieja = float(f.P2P_menos_C4_vieja.iloc[0])
        exige(abs(vieja - 3669.5485) < 0.01, f"compara_sigma{etiqueta}: la base de N1 Cesmag no es la del canon (+3 669,5)")
        base_n1 = vieja
        pon(f"fragiles__N1__Cesmag__P2P_menos_C4__sigma_{etiqueta}", float(f.P2P_menos_C4_nueva.iloc[0]), "COP",
            f"P2P − C4 de CESMAG en N1 con σ = {sigma}",
            f"entrega_barrido_sigma_2026-09-27/compara_sigma{etiqueta}.csv, P2P_menos_C4_nueva")
    pon("fragiles__N1__Cesmag__P2P_menos_C4__base", base_n1, "COP", "P2P − C4 de CESMAG en N1 en el canon",
        "compara_sigma*.csv, P2P_menos_C4_vieja (= CANON §8)")
    com = v[~v.salida.str.contains("__")]
    may = com[com.p_inversion > 0.5]
    pon("fragiles__comunidad__p_mayor_50", len(may), "brechas",
        "brechas de comunidad con P(inversión) de más del 50 %", "gsa_directo/<caso>/inversion_<caso>.csv")
    pon("fragiles__comunidad__lista_mayor_50",
        "; ".join(f"{a.caso} {a.salida} {100 * a.p_inversion:.2f}" for a in may.itertuples()),
        "%", "brechas de comunidad con P(inversión) de más del 50 %", "gsa_directo/<caso>/inversion_<caso>.csv")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    print("[cifras7] 1. comunidad")
    R = comunidad()
    print("[cifras7] 2. horas con los dos lados")
    horas()
    print("[cifras7] 3. coincidencia")
    coincidencia()
    print("[cifras7] 4. Gini")
    gini()
    print("[cifras7] 5. instituciones")
    instituciones()
    print("[cifras7] 6. liquidación de E0")
    liquidacion()
    print("[cifras7] 7. reglas de reparto")
    reglas(R)
    print("[cifras7] 8. subperíodos")
    subperiodos()
    print("[cifras7] 9. signos frágiles")
    fragiles()
    out = pd.DataFrame(FILAS, columns=["clave", "valor", "unidad", "definicion", "fuente"])
    out.to_csv(SALIDA / "cifras.csv", index=False, encoding="utf-8")
    sucio = git("status", "--short", "--", "reformateo/documento/scripts/cifras_cap07.py")
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8") as fh:
        fh.write("cifras_cap07.py: cifras derivadas del capítulo 7 (C-230)\n")
        fh.write(f"fecha: {_dt.datetime.now().isoformat(timespec='seconds')}\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n" + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + Path(sys.argv[0]).as_posix() + "\n")
        fh.write(f"huellas: {HUELLAS.relative_to(RAIZ).as_posix()}; {len(LEIDOS)} artefactos leídos, todos con la huella comprobada:\n")
        for g, r in LEIDOS:
            fh.write(f"  {g}  {r}\n")
        fh.write(f"cifras: {len(out)}\n")
    print(f"[cifras7] {len(out)} cifras de {len(LEIDOS)} artefactos en {SALIDA / 'cifras.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
