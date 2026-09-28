"""
cifras_cap08.py — Las cifras derivadas que cita el capítulo 8 de la tesis
(Sensibilidad y robustez) y que `CANON.md` no escribe tal cual (C-231).
===============================================================================
Decisión del controlador, ronda 2 del capítulo 8 (2026-09-28): toda cifra del
capítulo que no esté escrita tal cual en `Documentos/canon_2026-09/CANON.md`
sale de este guion. No simula nada: solo lee artefactos del GSA directo que
tienen huella en `Documentos/canon_2026-09/HUELLAS.csv` (grupos `gsa/`, bloque
9 del verificador), y antes de leer cada uno comprueba su tamaño y su `sha256`.

Qué calcula:

1. El coeficiente de variación de cada mecanismo en la caja del GSA, en los 12
   casos del Sobol, **recalculado** de las filas A y B de las muestras como hace
   el bloque 9 (desviación típica poblacional sobre el valor absoluto de la
   media). Compuertas: E0 y E2 reproducen el CV de CANON §13.5 (y las
   constantes del bloque 9) a 5e-7; el de los 12 casos, redondeado a dos
   decimales, es el que imprime `INFORME_<caso>.md`; C2 = P2P.
   Recuentos: casos con el CV del mercado menor que el de C1, C4, C3 y C5.
2. La bolsa de 2024 (`base/deterministas.csv`): energía transada y horas sin
   ganancia en la variante `base` y en `bolsa_2024`; los casos en que la
   energía no cambia; los pares institución-caso con P2P − C1 negativo con la
   bolsa de 2024 y su mínimo. Compuertas: la variante `base` da la energía y
   las horas sin ganancia de CANON §4; P2P − C5 con la bolsa de 2024 da la
   tabla de CANON §13.6.
3. El índice de segundo orden de E4 que cita el capítulo (parte del vendedor,
   f_cv × f_bolsa, `s2_E4.csv`), con la compuerta de que es el único par de
   E4 con |S2| > 0,02, como dice `INFORME_E4.md`.
4. La entrada dominante de cada brecha de comunidad (`indices_<caso>.csv`,
   n = n_base), con la compuerta contra la tabla de CANON §13.4; la segunda
   entrada y si la dominante se separa de ella (ST1 − ST2 > conf1 + conf2),
   con la compuerta de que las no separadas son las cinco de la revisión (M2);
   y los casos en que manda cada entrada, contando solo las separadas.
5. La entrada dominante de cada nivel (P2P, P2P colectivo, C1, C3, C4 y C5) y
   los casos en que manda cada una (M3 de la revisión).
6. La cercanía a la infactibilidad y la deserción hacia C1 por tramo de
   f_bolsa (`infactibilidad_desercion_2026-09-27/`, grupo `e1/C7`), con las
   compuertas de CANON §14.10 (Tabla 8.10, los seis pares de más del 5 % y E4
   por tramo); las horas sin ganancia de E0, SINU, E1 y N1, que no dependen de
   la bolsa, y su correlación con f_cv y f_bolsa en E0 y SINU; la deserción
   por tramo de N1 Udenar, E3 y E2 Cesmag, E5 Cesmag y HUDN y P1 HUDN (M1).

Ronda 3 (2026-09-28): la cabecera de las 12 muestras se compara con la lista
«columnas» de su `.meta.json`, se exige n = n_base de forma explícita y la
comprobación del Gini se hace en los 12 casos (m12). `procedencia.txt` lleva
la fecha de la corrida y no sale igual byte a byte; `cifras.csv` sí.

**El Gini en la caja del GSA no se calcula.** Las muestras traen, por
institución, solo las brechas P2P − C1, P2P − C4 y P2P − C5, no el beneficio
de cada institución con cada mecanismo (D75), de modo que el Gini del
beneficio por institución de cada mecanismo no se puede obtener de ellas sin
volver a evaluar el modelo. El guion lo comprueba sobre la cabecera y lo deja
escrito en `procedencia.txt`.

Falla en voz alta: ningún `except` que trague, ningún NaN rellenado; una
huella que no cuadra, una cifra no finita, una clave repetida o una compuerta
que no cierra es un error.

Escribe en SALIDAS_SERVIDOR/cifras_cap08_2026-09-28/:

    cifras.csv        clave, valor, unidad, definicion, fuente
    procedencia.txt   commit, estado del árbol, versiones, orden y huellas leídas

    PYTHONUNBUFFERED=1 python -u reformateo/documento/scripts/cifras_cap08.py

Actividades 4.1 y 4.2.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
HUELLAS = RAIZ / "Documentos" / "canon_2026-09" / "HUELLAS.csv"
SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
BASE_GSA = SALIDAS / "entrega_gsa_directo_completo_2026-09-27"
SALIDA = SALIDAS / "cifras_cap08_2026-09-28"

CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU"]
CASOS_GSA = ["E0", "E2", "E4", "E1", "E3", "E5", "P1", "P2", "K1", "I1", "N1",
             "SINU"]
INST = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
MECS_CV = ["P2P", "P2P_colectivo", "C1", "C3", "C4", "C5", "C2"]
BRECHAS = ["P2P_menos_C1", "P2P_menos_C4", "P2Pcol_menos_C1", "C4_menos_C1",
           "P2P_menos_C5"]
B = 14                              # filas por bloque de Saltelli (2 x 6 + 2)

# CANON §13.5 (y GSA_CV del bloque 9): CV de E0 y E2 recalculado de A y B
CV_CANON = {
    "E0": {"P2P": 0.064590, "P2P_colectivo": 0.066511, "C1": 0.064852,
           "C3": 0.063807, "C4": 0.066554, "C5": 0.060959, "C2": 0.064590},
    "E2": {"P2P": 0.064909, "P2P_colectivo": 0.077749, "C1": 0.066246,
           "C3": 0.121444, "C4": 0.078639, "C5": 0.104709, "C2": 0.064909},
}
# CANON §4: energía transada (kWh, dos decimales) y horas «sin_ganancia»
ENERGIA_CANON = {"E0": 4592.02, "E1": 16601.93, "E2": 17271.61, "E3": 15089.50,
                 "E4": 12804.59, "E5": 9272.82, "P1": 1829.23, "P2": 32144.14,
                 "K1": 3718.53, "I1": 17555.84, "N1": 6074.29, "CV2": 4592.02,
                 "SINU": 917.63}
SIN_GANANCIA_CANON = {c: 0 for c in CASOS} | {"E4": 2, "E5": 1, "P1": 2}
# CANON §13.6: P2P − C5 con la bolsa de 2024 (MCOP, dos decimales)
P2P_C5_2024 = {"E0": 1.73, "E2": 17.65, "E4": -9.90, "E1": 12.68, "E3": 21.58,
               "E5": -9.31, "P1": 3.39, "P2": 9.15, "K1": 1.22, "I1": 1.53,
               "N1": 5.34, "CV2": 1.65, "SINU": 0.32}
# CANON §13.4: entrada de mayor ST de cada brecha de comunidad y su ST
DOMINANTE_CANON = {
    "E0": [("f_cv", 0.976), ("f_cv", 0.370), ("f_peaje", 0.531), ("f_peaje", 0.497), ("f_tarifa", 0.529)],
    "E2": [("f_bolsa", 0.692), ("f_peaje", 0.794), ("f_peaje", 0.811), ("f_peaje", 0.818), ("f_bolsa", 0.831)],
    "E4": [("f_bolsa", 0.905), ("f_bolsa", 0.365), ("f_bolsa", 0.886), ("f_bolsa", 0.896), ("f_bolsa", 0.829)],
    "E1": [("f_cv", 0.520), ("f_peaje", 0.594), ("f_peaje", 0.736), ("f_peaje", 0.635), ("f_bolsa", 0.793)],
    "E3": [("f_bolsa", 0.901), ("f_peaje", 0.924), ("f_peaje", 0.733), ("f_peaje", 0.706), ("f_bolsa", 0.849)],
    "E5": [("f_bolsa", 0.599), ("e_D", 0.360), ("f_bolsa", 0.726), ("f_bolsa", 0.801), ("f_bolsa", 0.838)],
    "P1": [("f_bolsa", 0.901), ("f_peaje", 0.902), ("f_peaje", 0.806), ("f_peaje", 0.717), ("f_bolsa", 0.852)],
    "P2": [("f_cv", 0.423), ("f_cv", 0.632), ("f_cv", 0.995), ("f_cv", 0.989), ("f_tarifa", 0.613)],
    "K1": [("f_cv", 0.944), ("f_cv", 0.508), ("f_peaje", 0.485), ("f_peaje", 0.660), ("f_tarifa", 0.930)],
    "I1": [("f_bolsa", 0.676), ("f_cv", 0.620), ("f_bolsa", 0.586), ("f_bolsa", 0.531), ("f_bolsa", 0.791)],
    "N1": [("f_cv", 0.678), ("f_bolsa", 0.481), ("f_peaje", 0.927), ("f_peaje", 0.478), ("f_bolsa", 0.871)],
    "SINU": [("f_cv", 0.823), ("e_G", 0.485), ("e_G", 0.511), ("e_G", 0.515), ("e_G", 0.391)],
}

# Revisión del capítulo 8 (M2): las cinco celdas de la Tabla 8.5 cuya dominante no
# se separa de la segunda entrada (ST1 − ST2 ≤ conf1 + conf2)
NO_SEPARADAS_REVISION = {("E1", "P2P_menos_C1"), ("P2", "P2P_menos_C1"), ("K1", "P2Pcol_menos_C1"),
                         ("N1", "P2P_menos_C4"), ("N1", "C4_menos_C1")}
NIVELES = ["P2P", "P2P_colectivo", "C1", "C3", "C4", "C5"]
TRAMOS = ["075_1", "1_15", "15_2", "2_3", "3_4"]
# CANON §14.10: energía media con f_bolsa entre 3 y 4 (% del punto base) y horas
# sin ganancia medias con f_bolsa entre 0,75 y 1 y entre 3 y 4
CERCANIA_CANON = {"E5": (72.9, 0.4, 210.4), "P1": (82.6, 2.5, 159.4), "E4": (83.2, 0.6, 157.0)}
# CANON §14.10: los seis pares con deserción hacia C1 de más del 5 % y E4 por tramo
DESERCION_CANON = {("E4", "HUDN"): 38.6, ("E4", "Cesmag"): 35.2, ("E5", "Cesmag"): 21.4,
                   ("E4", "Mariana"): 17.0, ("E5", "HUDN"): 5.6, ("P1", "HUDN"): 5.5}
DESERCION_E4_CANON = {("HUDN", "2_3"): 27.2, ("Cesmag", "2_3"): 33.0,
                      ("HUDN", "3_4"): 98.2, ("Cesmag", "3_4"): 81.3}

FILAS: list[dict] = []
LEIDOS: list[tuple[str, str]] = []
NOTAS: list[str] = []


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


def lee(ruta: str, prefijo: str = "gsa/") -> Path:
    """Devuelve la ruta del artefacto tras comprobar su huella (grupos gsa/ o e1/)."""
    f = _H[(_H.ruta == ruta) & (_H.grupo.str.startswith(prefijo))]
    exige(len(f) == 1, f"{ruta}: {len(f)} filas {prefijo} en HUELLAS.csv (se esperaba 1)")
    fila = f.iloc[0]
    p = (BASE_GSA if prefijo == "gsa/" else SALIDAS) / ruta
    exige(p.is_file(), f"no existe {p}")
    datos = p.read_bytes()
    exige(len(datos) == int(fila.bytes), f"{ruta}: {len(datos)} bytes, huella {fila.bytes}")
    exige(hashlib.sha256(datos).hexdigest() == fila.sha256, f"{ruta}: sha256 distinto de la huella")
    if (fila.grupo, ruta) not in LEIDOS:
        LEIDOS.append((fila.grupo, ruta))
    return p


def ruta_gsa(caso: str, nombre: str) -> str:
    return f"SALIDAS_SERVIDOR/gsa_directo/{caso}/{nombre}"


def finito(a, qué: str):
    exige(bool(np.isfinite(np.asarray(a, dtype=float)).all()), f"{qué}: valores no finitos")
    return a


def muestras(caso: str) -> tuple[pd.DataFrame, int]:
    meta = json.loads(lee(ruta_gsa(caso, f"muestras_{caso}_n{n_base(caso)}_s42.meta.json")).read_text(encoding="utf-8"))
    n = int(meta["n_base"])
    exige(n == n_base(caso), f"{caso}: n_base {n} en el .meta.json, se esperaba {n_base(caso)}")
    exige(int(meta["B"]) == B and int(meta["semilla"]) == 42, f"{caso}: .meta.json con B o semilla inesperados")
    df = pd.read_csv(lee(ruta_gsa(caso, f"muestras_{caso}_n{n}_s42.csv")))
    exige(list(df.columns) == list(meta["columnas"]),
          f"{caso}: la cabecera de la muestra no es la lista «columnas» del .meta.json")
    exige(len(df) == B * n, f"{caso}: {len(df)} filas, se esperaban {B * n}")
    exige(bool(df["motivo"].isna().all()), f"{caso}: hay evaluaciones con motivo de fallo")
    exige(sorted(df["idx"].tolist()) == list(range(B * n)), f"{caso}: índices incompletos o repetidos")
    return df, n


def n_base(caso: str) -> int:
    return 2048 if caso in ("E0", "E2", "E4") else 512


# ── 0. ¿Traen las muestras el beneficio por institución de cada mecanismo? ──
def comprueba_gini(caso: str, cols: list[str]) -> None:
    """La cabecera completa (igual a la del .meta.json) no tiene niveles por institución."""
    por_inst = [c for c in cols if any(c.endswith("__" + i) or ("_" + i) in c or c == i for i in INST)]
    esperadas = [f"{b}__{i}" for i in INST for b in ["P2P_menos_C1", "P2P_menos_C4", "P2P_menos_C5"]]
    if caso == "SINU":
        esperadas = [e for e in esperadas if not e.endswith("__Udenar")]
    exige(sorted(por_inst) == sorted(esperadas),
          f"{caso}: columnas por institución inesperadas: {sorted(set(por_inst) ^ set(esperadas))}")
    niveles = [m for m in ["P2P", "P2P_colectivo", "C1", "C2", "C3", "C4", "C5"] if m in cols]
    exige(len(niveles) == 7, f"{caso}: faltan niveles de comunidad en la cabecera")
    if NOTAS:
        return
    NOTAS.append("Gini en la caja del GSA: NO CALCULADO. Las muestras traen por "
                 "institución solo P2P_menos_C1, P2P_menos_C4 y P2P_menos_C5 "
                 "(D75), no el beneficio de cada institución con cada mecanismo; "
                 "el Gini del beneficio por institución exige esos niveles.")


# ── 1. El coeficiente de variación en la caja ───────────────────────────────
def cv() -> None:
    V = {}
    for c in CASOS_GSA:
        df, n = muestras(c)
        comprueba_gini(c, list(df.columns))
        if c in ("E0", "SINU"):
            # M1 de la revisión: las horas sin ganancia de E0 y SINU frente a f_cv y f_bolsa
            for e in ["f_cv", "f_bolsa"]:
                r = float(np.corrcoef(df[e].to_numpy(float), df["n_sin_ganancia"].to_numpy(float))[0, 1])
                pon(f"sin_ganancia__{c}__corr_{e}", r, "coef.",
                    f"correlación de Pearson entre las horas sin ganancia y {e} en todas las filas de la muestra de {c}",
                    f"gsa_directo/{c}/muestras_{c}_n{n}_s42.csv, n_sin_ganancia")
        ab = (df["idx"] % B == 0) | (df["idx"] % B == B - 1)
        exige(int(ab.sum()) == 2 * n, f"{c}: {int(ab.sum())} filas A y B, se esperaban {2 * n}")
        txt = lee(ruta_gsa(c, f"INFORME_{c}.md")).read_text(encoding="utf-8")
        V[c] = {}
        for m in MECS_CV:
            y = finito(df.loc[ab, m].to_numpy(dtype=float), f"{c} {m}")
            v = float(np.std(y) / abs(np.mean(y)))
            V[c][m] = v
            exige(f"| {m} | {100 * v:.2f} % |" in txt, f"{c}: el informe no imprime el CV {100 * v:.2f} % de {m}")
            if c in CV_CANON:
                exige(abs(v - CV_CANON[c][m]) <= 5e-7, f"{c} {m}: CV {v:.6f} frente a CANON §13.5 {CV_CANON[c][m]:.6f}")
            if m != "C2":
                pon(f"cv__{c}__{m}", 100 * v, "%", f"coeficiente de variación de {m} en la caja del GSA (filas A y B)",
                    f"gsa_directo/{c}/muestras_{c}_n{n}_s42.csv, std/|media| de las filas A y B")
        exige(abs(V[c]["C2"] - V[c]["P2P"]) <= 1e-9, f"{c}: CV de C2 distinto del de P2P")
    for otro in ["C1", "C4", "C3", "C5"]:
        menor = [c for c in CASOS_GSA if V[c]["P2P"] < V[c][otro]]
        empate2 = [c for c in CASOS_GSA if round(100 * V[c]["P2P"], 2) == round(100 * V[c][otro], 2)]
        pon(f"cv__casos_P2P_menor_{otro}", len(menor), "casos",
            f"casos con el CV del mercado menor que el de {otro} (sin redondear)", "cv__<caso>__*")
        pon(f"cv__lista_P2P_menor_{otro}", "; ".join(menor) or "ninguno", "casos",
            f"casos con el CV del mercado menor que el de {otro}", "cv__<caso>__*")
        pon(f"cv__lista_empate_2dec_P2P_{otro}", "; ".join(empate2) or "ninguno", "casos",
            f"casos con el CV del mercado igual al de {otro} con dos decimales", "cv__<caso>__*")


# ── 2. La bolsa de 2024 ─────────────────────────────────────────────────────
def bolsa_2024() -> None:
    d = pd.read_csv(lee("SALIDAS_SERVIDOR/gsa_directo/base/deterministas.csv"))
    exige(len(d) == 13 * 4 and set(d.variante) == {"base", "mu_0.5", "mu_2", "bolsa_2024"},
          "deterministas.csv: filas o variantes inesperadas")
    exige(bool(d["motivo"].isna().all()), "deterministas.csv: evaluaciones con motivo de fallo")
    sin_cambio = []
    negativos = []
    for c in CASOS:
        b = d[(d.caso == c) & (d.variante == "base")]
        y = d[(d.caso == c) & (d.variante == "bolsa_2024")]
        exige(len(b) == 1 and len(y) == 1, f"{c}: sin variante base o bolsa_2024")
        b, y = b.iloc[0], y.iloc[0]
        eb, ey = float(b.energia), float(y.energia)
        finito([eb, ey, b.n_sin_ganancia, y.n_sin_ganancia, y.P2P_menos_C5], f"{c} deterministas")
        exige(abs(eb - ENERGIA_CANON[c]) < 0.006, f"{c}: energía base {eb:.2f} frente a CANON §4 {ENERGIA_CANON[c]}")
        exige(int(b.n_sin_ganancia) == SIN_GANANCIA_CANON[c], f"{c}: horas sin ganancia base distintas de CANON §4")
        exige(abs(round(float(y.P2P_menos_C5) / 1e6, 2) - P2P_C5_2024[c]) < 1e-9,
              f"{c}: P2P − C5 con la bolsa de 2024 no reproduce CANON §13.6")
        F = "gsa_directo/base/deterministas.csv"
        pon(f"det2024__{c}__energia_base", eb, "kWh", "energía transada, variante base", F + ", energia")
        pon(f"det2024__{c}__energia", ey, "kWh", "energía transada con la bolsa de 2024", F + ", energia")
        pon(f"det2024__{c}__n_sin_ganancia_base", int(b.n_sin_ganancia), "h", "horas sin ganancia, variante base", F + ", n_sin_ganancia")
        pon(f"det2024__{c}__n_sin_ganancia", int(y.n_sin_ganancia), "h", "horas sin ganancia con la bolsa de 2024", F + ", n_sin_ganancia")
        if ey == eb:
            sin_cambio.append(c)
        for i in INST:
            if c == "SINU" and i == "Udenar":
                exige(pd.isna(y[f"P2P_menos_C1__{i}"]), "SINU: Udenar con valor")
                continue
            v = float(y[f"P2P_menos_C1__{i}"])
            finito([v], f"{c} {i}")
            if v < 0:
                negativos.append((c, i, v))
    pon("det2024__casos_energia_sin_cambio", "; ".join(sin_cambio), "casos",
        "casos con la misma energía transada con la bolsa de 2024 que en la base", "deterministas.csv")
    exige(len(negativos) > 0, "ningún par con P2P − C1 negativo con la bolsa de 2024")
    pon("det2024__P2P_menos_C1__negativos", "; ".join(f"{c} {i}" for c, i, _ in negativos), "pares",
        "pares institución-caso con P2P − C1 < 0 con la bolsa de 2024", "deterministas.csv, P2P_menos_C1__<institución>")
    pon("det2024__P2P_menos_C1__n_negativos", len(negativos), "pares",
        "número de esos pares", "deterministas.csv")
    casos = []
    for c, _, _ in negativos:
        if c not in casos:
            casos.append(c)
    pon("det2024__P2P_menos_C1__casos", "; ".join(casos), "casos",
        "casos con al menos una institución con P2P − C1 < 0 con la bolsa de 2024", "deterministas.csv")
    c, i, v = min(negativos, key=lambda t: t[2])
    pon("det2024__P2P_menos_C1__min", v, "COP", "P2P − C1 más negativo con la bolsa de 2024", "deterministas.csv")
    pon("det2024__P2P_menos_C1__min_par", f"{c} {i}", "par", "par del mínimo", "deterministas.csv")


# ── 3. El índice de segundo orden de E4 ─────────────────────────────────────
def segundo_orden() -> None:
    s2 = pd.read_csv(lee(ruta_gsa("E4", "s2_E4.csv")))
    finito(s2.S2, "s2_E4")
    grandes = s2[s2.S2.abs() > 0.02]
    exige(len(grandes) == 1, f"E4: {len(grandes)} pares con |S2| > 0,02 (el informe dice uno)")
    g = grandes.iloc[0]
    exige((g.salida, g.entrada_i, g.entrada_k) == ("parte_vendedor", "f_cv", "f_bolsa"),
          f"E4: el par con |S2| > 0,02 es {g.salida} {g.entrada_i} × {g.entrada_k}")
    txt = lee(ruta_gsa("E4", "INFORME_E4.md")).read_text(encoding="utf-8")
    exige(f"| parte_vendedor | f_cv × f_bolsa | {g.S2:.3f} | {g.S2_conf:.3f} |" in txt,
          "E4: el informe no imprime ese S2")
    pon("s2__E4__parte_vendedor__f_cv__f_bolsa", float(g.S2), "índice",
        "S2 de la parte del vendedor, f_cv × f_bolsa, en E4 (n = 2 048)", "gsa_directo/E4/s2_E4.csv, S2")
    pon("s2__E4__parte_vendedor__f_cv__f_bolsa__semiancho", float(g.S2_conf), "índice",
        "su semiancho al 95 %", "gsa_directo/E4/s2_E4.csv, S2_conf")
    pon("s2__E4__n_mayor_002", len(grandes), "pares", "pares salida-entradas con |S2| > 0,02 en E4", "s2_E4.csv")


# ── 4. La entrada dominante de cada brecha ──────────────────────────────────
def dominantes() -> None:
    por = {}
    no_sep = []
    for c in CASOS_GSA:
        ind = pd.read_csv(lee(ruta_gsa(c, f"indices_{c}.csv")))
        ind = ind[ind.n == n_base(c)]
        for k, br in enumerate(BRECHAS):
            g = ind[ind.salida == br]
            exige(len(g) == 6, f"{c} {br}: {len(g)} entradas a n = n_base")
            finito(g.ST, f"{c} {br} ST")
            top = g.loc[g.ST.idxmax()]
            e, st = DOMINANTE_CANON[c][k]
            exige(top.entrada == e and abs(round(float(top.ST), 3) - st) < 1e-9,
                  f"{c} {br}: dominante {top.entrada} {top.ST:.3f} frente a CANON §13.4 {e} {st}")
            pon(f"dominante__{c}__{br}", f"{top.entrada} {float(top.ST):.3f} (±{float(top.ST_conf):.3f})", "ST",
                f"entrada de mayor ST de {br} en {c}", f"gsa_directo/{c}/indices_{c}.csv, n = n_base")
            # M2 de la revisión: ¿se separa la dominante de la segunda? (ST1 − ST2 > conf1 + conf2)
            seg = g.drop(index=top.name).sort_values("ST").iloc[-1]
            separada = float(top.ST) - float(seg.ST) > float(top.ST_conf) + float(seg.ST_conf)
            pon(f"dominante__{c}__{br}__segunda", f"{seg.entrada} {float(seg.ST):.3f} (±{float(seg.ST_conf):.3f})", "ST",
                f"segunda entrada de {br} en {c}", f"gsa_directo/{c}/indices_{c}.csv, n = n_base")
            if separada:
                por.setdefault((br, top.entrada), []).append(c)
            else:
                no_sep.append((c, br, top.entrada, seg.entrada))
    exige({(c, br) for c, br, _, _ in no_sep} == NO_SEPARADAS_REVISION,
          f"celdas no separadas distintas de las de la revisión: {no_sep}")
    pon("dominante__no_separadas__n", len(no_sep), "celdas",
        "celdas de la Tabla 8.5 cuya dominante no se separa de la segunda (ST1 − ST2 ≤ conf1 + conf2)", "indices_<caso>.csv")
    pon("dominante__no_separadas__lista", "; ".join(f"{c} {br} {a} ~ {b}" for c, br, a, b in no_sep), "celdas",
        "esas celdas, con la dominante y la segunda", "indices_<caso>.csv")
    for (br, e), casos in sorted(por.items()):
        pon(f"dominante__{br}__{e}__casos", "; ".join(casos), "casos",
            f"casos en que {e} es la entrada de mayor ST de {br} y se separa de la segunda", "indices_<caso>.csv")


# ── 5. La entrada dominante de los niveles (M3 de la revisión) ──────────────
def niveles() -> None:
    por = {}
    for c in CASOS_GSA:
        ind = pd.read_csv(lee(ruta_gsa(c, f"indices_{c}.csv")))
        ind = ind[ind.n == n_base(c)]
        for m in NIVELES:
            g = ind[ind.salida == m]
            exige(len(g) == 6, f"{c} {m}: {len(g)} entradas a n = n_base")
            finito(g.ST, f"{c} {m} ST")
            top = g.loc[g.ST.idxmax()]
            pon(f"nivel__{c}__{m}", f"{top.entrada} {float(top.ST):.3f} (±{float(top.ST_conf):.3f})", "ST",
                f"entrada de mayor ST del nivel {m} en {c}", f"gsa_directo/{c}/indices_{c}.csv, n = n_base")
            por.setdefault((m, top.entrada), []).append((c, float(top.ST)))
    for (m, e), lst in sorted(por.items()):
        pon(f"nivel__{m}__{e}__casos", "; ".join(c for c, _ in lst), "casos",
            f"casos en que {e} es la entrada de mayor ST del nivel {m}", "indices_<caso>.csv")
        pon(f"nivel__{m}__{e}__ST_min", min(s for _, s in lst), "ST", "menor ST dominante de esos casos", "indices_<caso>.csv")
        pon(f"nivel__{m}__{e}__ST_max", max(s for _, s in lst), "ST", "mayor ST dominante de esos casos", "indices_<caso>.csv")


# ── 6. Cercanía y deserción por tramo de la bolsa (M1 de la revisión) ───────
def cercania_desercion() -> None:
    F_C = "infactibilidad_desercion_2026-09-27/cercania_por_fbolsa.csv"
    F_D = "infactibilidad_desercion_2026-09-27/desercion_c1_por_fbolsa.csv"
    F_T = "infactibilidad_desercion_2026-09-27/desercion_c1.csv"
    ce = pd.read_csv(lee(F_C, "e1/"))
    de = pd.read_csv(lee(F_D, "e1/"))
    dt = pd.read_csv(lee(F_T, "e1/"))
    finito(ce[["energia_rel_media", "energia_rel_min", "sin_ganancia_media", "sin_ganancia_max"]].to_numpy(), "cercanía")
    finito(de.p_desercion, "deserción por tramo")
    finito(dt.p_desercion, "deserción total")
    tr = {t: TRAMOS[i] for i, t in enumerate(sorted(ce.tramo.unique(), key=lambda s: float(s.split(",")[0][1:])))}
    exige(len(tr) == 5, f"tramos inesperados: {list(tr)}")
    # compuertas: la Tabla 8.10 (CANON §14.10)
    for c, (en, sg1, sg4) in CERCANIA_CANON.items():
        a = ce[(ce.caso == c) & (ce.tramo.map(tr) == "3_4")].iloc[0]
        b = ce[(ce.caso == c) & (ce.tramo.map(tr) == "075_1")].iloc[0]
        igual = lambda x, y: abs(round(float(x), 1) - y) < 1e-9
        exige(igual(100 * a.energia_rel_media, en) and igual(b.sin_ganancia_media, sg1)
              and igual(a.sin_ganancia_media, sg4), f"{c}: la cercanía no reproduce CANON §14.10")
    # compuertas: los seis pares de más del 5 % y E4 por tramo (CANON §14.10)
    for (c, i), p in DESERCION_CANON.items():
        f = dt[(dt.caso == c) & (dt.institucion == i)]
        exige(len(f) == 1 and abs(round(100 * float(f.p_desercion.iloc[0]), 1) - p) < 1e-9,
              f"{c} {i}: deserción total ≠ CANON §14.10")
    for (i, t), p in DESERCION_E4_CANON.items():
        f = de[(de.caso == "E4") & (de.institucion == i) & (de.tramo.map(tr) == t)]
        exige(len(f) == 1 and abs(round(100 * float(f.p_desercion.iloc[0]), 1) - p) < 1e-9,
              f"E4 {i} {t}: ≠ CANON §14.10")
    exige(set(dt[dt.p_desercion > 0.05].apply(lambda r: (r.caso, r.institucion), axis=1)) == set(DESERCION_CANON),
          "los pares de más del 5 % no son los seis de CANON §14.10")
    # las cifras nuevas
    for c in ["E0", "SINU", "E1", "N1"]:
        g = ce[ce.caso == c]
        pon(f"cercania__{c}__sin_ganancia_media_min", float(g.sin_ganancia_media.min()), "h",
            f"menor media de horas sin ganancia por evaluación entre los tramos de f_bolsa en {c}", F_C)
        pon(f"cercania__{c}__sin_ganancia_media_max", float(g.sin_ganancia_media.max()), "h",
            f"mayor media de horas sin ganancia por evaluación entre los tramos de f_bolsa en {c}", F_C)
        pon(f"cercania__{c}__sin_ganancia_max", int(g.sin_ganancia_max.max()), "h",
            f"máximo de horas sin ganancia en una evaluación de {c}", F_C)
        pon(f"cercania__{c}__energia_rel_min", 100 * float(g.energia_rel_min.min()), "% del punto base",
            f"menor energía transada de una evaluación de {c}, como porcentaje del punto base", F_C)
        pon(f"cercania__{c}__energia_rel_media_min", 100 * float(g.energia_rel_media.min()), "% del punto base",
            f"menor energía media de un tramo de f_bolsa en {c}", F_C)
        pon(f"cercania__{c}__energia_rel_media_max", 100 * float(g.energia_rel_media.max()), "% del punto base",
            f"mayor energía media de un tramo de f_bolsa en {c}", F_C)
    peor = ce.loc[ce.energia_rel_media.idxmin()]
    pon("cercania__energia_rel_media_min", 100 * float(peor.energia_rel_media), "% del punto base",
        "menor energía media de un tramo de f_bolsa en los 12 casos", F_C)
    pon("cercania__energia_rel_media_min__donde", f"{peor.caso} {tr[peor.tramo]}", "caso y tramo", "dónde", F_C)
    for (c, i) in [("N1", "Udenar"), ("E3", "Cesmag"), ("E2", "Cesmag"), ("E5", "Cesmag"), ("E5", "HUDN"),
                   ("P1", "HUDN")]:
        f = dt[(dt.caso == c) & (dt.institucion == i)]
        exige(len(f) == 1, f"{c} {i}: sin fila en desercion_c1.csv")
        pon(f"desercion__{c}__{i}__total", 100 * float(f.p_desercion.iloc[0]), "%",
            f"probabilidad de deserción hacia C1 de {i} en {c}, todas las filas de la muestra", F_T)
        for t_orig, t in tr.items():
            f = de[(de.caso == c) & (de.institucion == i) & (de.tramo == t_orig)]
            exige(len(f) == 1, f"{c} {i} {t}: {len(f)} filas en {F_D}")
            pon(f"desercion__{c}__{i}__{t}", 100 * float(f.p_desercion.iloc[0]), "%",
                f"deserción de {i} en {c} con f_bolsa en el tramo {t_orig}", F_D)


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    print("[cifras8] 1. coeficiente de variación (y comprobación del Gini)")
    cv()
    print("[cifras8] 2. bolsa de 2024")
    bolsa_2024()
    print("[cifras8] 3. segundo orden de E4")
    segundo_orden()
    print("[cifras8] 4. entradas dominantes")
    dominantes()
    print("[cifras8] 5. entradas dominantes de los niveles")
    niveles()
    print("[cifras8] 6. cercanía y deserción por tramo")
    cercania_desercion()
    out = pd.DataFrame(FILAS, columns=["clave", "valor", "unidad", "definicion", "fuente"])
    out.to_csv(SALIDA / "cifras.csv", index=False, encoding="utf-8")
    sucio = git("status", "--short", "--", "reformateo/documento/scripts/cifras_cap08.py")
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8") as fh:
        fh.write("cifras_cap08.py: cifras derivadas del capítulo 8 (C-231)\n")
        fh.write(f"fecha: {_dt.datetime.now().isoformat(timespec='seconds')}\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n" + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + Path(sys.argv[0]).as_posix() + "\n")
        fh.write(f"huellas: {HUELLAS.relative_to(RAIZ).as_posix()}; {len(LEIDOS)} artefactos leídos, todos con la huella comprobada:\n")
        for g, r in LEIDOS:
            fh.write(f"  {g}  {r}\n")
        for n in NOTAS:
            fh.write(n + "\n")
        fh.write(f"cifras: {len(out)}\n")
    print(f"[cifras8] {len(out)} cifras de {len(LEIDOS)} artefactos en {SALIDA / 'cifras.csv'}")
    for n in NOTAS:
        print("[cifras8] " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
