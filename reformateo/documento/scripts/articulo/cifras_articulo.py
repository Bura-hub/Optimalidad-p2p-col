"""
cifras_articulo.py — La tabla de cifras con huella de la que sale toda cifra
del artículo para IEEE Latin America Transactions (canon 2026-09).
===============================================================================
Tarea 1 del plan `docs/superpowers/plans/2026-09-29-articulo-latam.md` (spec
`docs/superpowers/specs/2026-09-28-articulo-latam-design.md`, §4). No simula
nada: solo lee artefactos que tienen huella en
`Documentos/canon_2026-09/HUELLAS.csv`, y antes de leer cada uno comprueba su
tamaño y su `sha256` contra esa huella. Lo que el canon escribe tal cual y no
está en ningún fichero con huella se lee del texto de `CANON.md`, con la
sección anotada, y se contrasta con un fichero con huella donde lo hay.

Qué lee:

1. La hoja `Resumen` de los 13 libros de la matriz del 19 de septiembre
   (grupos `outputs/<caso>`): el beneficio de P2P, P2P colectivo, C1, C4 y C5 y
   sus brechas. Compuertas: la tabla de CANON §6 a dos decimales, P2P = C2 y
   C4 = C4 mensual, y la identidad P2P − C4 = (P2P − C1) + (C1 − C4) al peso.
2. `cifras_cap07_2026-09-28/cifras.csv` (grupo `e1/R`): los porcentajes de las
   brechas, la parte de C1 − C4 en P2P − C4, el colectivo frente a C4, E4 con
   las reglas del art. 19, los pares bajo C4 y CESMAG en N1. Compuerta: cada
   brecha de cap. 7 coincide con la recalculada de `Resumen`.
3. `descomposicion_p2p_2026-09-27/descomposicion_13casos.csv` (grupo `e1/C5`):
   la banda y la reclasificación de la comunidad. Compuertas: la fila
   `comunidad` es la suma de los agentes, banda + reclasificación = P2P − C1 de
   `Resumen` dentro del float32 (≤ 1 COP por caso) y la tabla de CANON §14.8 a
   tres decimales.
4. `gsa_directo/<caso>/inversion_<caso>.csv` y `base/punto_base.csv` del GSA
   directo completo (grupos `gsa/`): P(inversión) de las cinco brechas de
   comunidad con su intervalo al 95 % y su valor en el punto base. Compuerta:
   las dos tablas y los intervalos de CANON §13.3.
5. Las constantes publicables: la validación dinámica (CANON §9, texto,
   contrastada con `m_a_regimenes.json`, grupo `e1/V`), el horizonte
   (`cifras_datos_2026-09-28`, grupo `e1/D`), las horas cuantales y con mercado
   (tabla `horas` de los 13 almacenes, contrastadas con CANON §10.1), la parte
   del vendedor de E0 (`compara_matriz_reposo.csv`, contra CANON §4), el techo
   del ponderado y el COT (`contrafactico_techo_cot_2026-09-28`, grupo `e1/T`,
   contra CANON §14.16) y el umbral de deserción de E4
   (`infactibilidad_desercion_2026-09-27`, grupo `e1/C7`, contra CANON §14.10).
6. Los resúmenes: `share_*` (C1 − C4 como parte de P2P − C4 donde C1 > C4),
   `col_pct_*` (colectivo − C4 sobre C4) y el recuento del GSA sin inversiones.

Añadido el 2026-09-30 (Tarea A1 de `docs/superpowers/plans/2026-09-30-articulo-es-revision.md`),
siempre al final de la tabla, de modo que las 482 filas del 29 salen iguales
byte a byte:

7. El valor de un kWh (`kwh__*`), de las tablas `agentes` de los almacenes de
   E0 y P2 (grupos `almacen/<caso>`): el techo es el CU de cada institución y
   hora; el piso de E0, que nadie agota el crédito, es la permuta del numeral 1
   (CU − Cv); el de P2, con todas las plantas en el numeral 2 y sin crédito
   agotado, la del numeral 2 (CU − Cv − Θ), que es también la del caso 2 del
   colectivo. Por mes (abril de 2025, el mes de los ejemplos), rango de los
   nueve meses y media ponderada por horas. Compuertas: la tarifa constante en
   cada institución y mes; dos comercializadores; las medias, el rango del CU y
   las diferencias contra `cifras_datos_2026-09-28` (§14.17); C1 de E0 = el
   autoconsumo a la tarifa más el crédito a la permuta del numeral 1, y C4 =
   el autoconsumo más la parte 1/n del fondo a la permuta del numeral 2, al
   peso, donde nadie agota su parte (E0, P2, K1, CV2 y SINU); y los anchos de
   par del almacén de flujos de E0 contra los de las tarifas.
8. Los atributos de los 13 casos (`caso__*`): capacidad por planta, suma y
   por usuario (`contrafacticos_art18_2026-09-27/capacidad_por_usuario.csv`,
   e1/A1, contra `cifras_datos`), factores de generación y demanda (almacén
   contra la opción de CANON §1), numeral de cada planta (por la regla de los
   100 kW, contrastado con el piso del almacén), pares que agotan el crédito
   (almacén contra `cifras_datos`), participación mínima del reparto igual y
   caso del art. 20 del colectivo (contra `contrafacticos_13casos.csv`).
9. Los siete mecanismos: C2 y C3 de la hoja `Resumen` en los 13 casos, contra
   CANON §6; C4 mensual no se emite (regla 4).
10. El diseño del GSA: evaluaciones por caso (M = 14 n) y soportes de los seis
    factores, de los `.meta.json` y las muestras (gsa/<caso>), contra CANON
    §13.1, §13.2 y §14.10; la cota de una proporción nula por la regla del tres.
11. Otras cifras que las respuestas a las notas del autor marcan como
    derivadas: el ancho efectivo de E0 (§14.3), las horas sin mercado y de
    saturación de E0 (§4), el umbral de 100 kW (`umbral_100kw.csv`, e1/C8,
    §14.11), la bolsa media topada y P2 frente a E0 (§14.18).

Formato de `texto_en` (la forma exacta en que el valor aparece en el artículo):
punto decimal, coma de millares a partir de 1 000, signo menos ASCII (`-`) y
ningún `-0.00`. MCOP a dos decimales; porcentajes a dos decimales con « %»,
salvo `share_*`, que va en entero; P(inversión) del GSA en % a dos decimales;
conteos en entero; la parte del vendedor a tres decimales, como la cita el
canon.

Falla en voz alta: ningún `except` que trague, ningún NaN rellenado; una
huella que no cuadra, una cifra no finita, una clave repetida o una compuerta
que no cierra es un error (`raise SystemExit` con el mensaje).

Escribe en SALIDAS_SERVIDOR/cifras_articulo_2026-09-30/ (la del 29 queda como
estaba):

    cifras.csv        clave, valor, unidad, texto_en, definicion, fuente, seccion_canon
    procedencia.txt   commit, estado del árbol, versiones, orden y huellas leídas

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/cifras_articulo.py

`cifras.csv` y `procedencia.txt` salen idénticos byte a byte entre corridas
con el mismo HEAD y el mismo estado del guion (desde el 2026-09-30,
`procedencia.txt` no lleva fecha: la hora de la corrida solo se imprime en la
consola).

Actividades 3.3 y 4.2.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import platform
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# La consola de Windows (cp1252) no codifica «≤», «−» ni «Θ»: al redirigir la
# salida el guion moría con UnicodeEncodeError. Se fija UTF-8.
for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[4]
HUELLAS = RAIZ / "Documentos" / "canon_2026-09" / "HUELLAS.csv"
CANON_MD = RAIZ / "Documentos" / "canon_2026-09" / "CANON.md"
SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
BASE_MATRIZ = SALIDAS / "entrega_matriz_reposo_2026-09-19"
BASE_GSA = SALIDAS / "entrega_gsa_directo_completo_2026-09-27"
SALIDA = SALIDAS / "cifras_articulo_2026-09-30"

CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU"]
CASOS_GSA = ["E0", "E2", "E4", "E1", "E3", "E5", "P1", "P2", "K1", "I1", "N1",
             "SINU"]
# brecha del GSA -> sufijo de la clave y rótulo de CANON §13.3
BRECHAS = {"P2P_menos_C1": ("P2P_C1", "P2P − C1"),
           "P2P_menos_C4": ("P2P_C4", "P2P − C4"),
           "P2Pcol_menos_C1": ("P2Pcol_C1", "P2P colectivo − C1"),
           "C4_menos_C1": ("C4_C1", "C4 − C1"),
           "P2P_menos_C5": ("P2P_C5", "P2P − C5")}
# mecanismo de la hoja Resumen -> sufijo de la clave y columna de CANON §6
MECS = {"P2P": ("P2P", "P2P"), "P2P_colectivo": ("P2Pcol", "P2P colectivo"),
        "C1": ("C1", "C1"), "C4": ("C4", "C4"), "C5": ("C5", "C5")}
REGIMENES_MERCADO = {"interiores", "topados", "excluidos", "suma_no_cabe",
                     "compradores_cortos", "un_comprador", "cuantal", "mixto"}
M = 1e6
# Claves de cifras_cap07 cuyo valor es texto (listas de casos, de pares o de
# mecanismos): no se leen como número. Cualquier otra clave no numérica, o que
# falte una de estas, falla en voz alta en main() (minor diferido de la Tarea 1).
CLAVES_TEXTO_CAP07 = frozenset({
    "orden__casos_C4_segundo", "orden__casos_C5_sobre_C4",
    "comunidad__colectivo_sobre_C1_casos",
    "institucion__P2P_menos_C1__lista_negativos", "institucion__P2P_menos_C5__lista_negativos",
    "institucion__casos_mayoria_bajo_C4", "institucion__casos_ninguna_bajo_C4",
    "liquidacion__E0__Udenar__mejor", "liquidacion__E0__Mariana__mejor",
    "liquidacion__E0__UCC__mejor", "liquidacion__E0__HUDN__mejor", "liquidacion__E0__Cesmag__mejor",
    "reglas__casos_alguna_regla_sobre_P2P",
    "fragiles__P2P_menos_C1__lista_mayor_25", "fragiles__P2P_menos_C4__lista_mayor_25",
    "fragiles__P2P_menos_C5__lista_mayor_25", "fragiles__comunidad__lista_mayor_50",
})

FILAS: list[dict] = []
LEIDOS: list[tuple[str, str]] = []
COMPUERTAS: list[str] = []


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[cifras_articulo] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    COMPUERTAS.append(msg)
    print(f"[cifras_articulo]   OK  {msg}")


# ── Formato en inglés ───────────────────────────────────────────────────────
def en(v: float, dec: int, sufijo: str = "") -> str:
    """Número con punto decimal, coma de millares y signo menos ASCII; sin -0."""
    s = f"{float(v):,.{dec}f}"
    if s.lstrip("-").strip("0.,") == "":
        s = s.lstrip("-")
    return s + sufijo


def en_int(v: int, sufijo: str = "") -> str:
    return f"{int(v):,d}" + sufijo


def pon(clave: str, valor, unidad: str, texto_en: str, definicion: str,
        fuente: str, seccion: str) -> None:
    """Añade una cifra. Falla si no es finita, si la clave ya existe o si
    `texto_en` o `seccion_canon` vienen vacíos o mal formados."""
    exige(not any(f["clave"] == clave for f in FILAS), f"clave repetida: {clave}")
    if isinstance(valor, (bool, np.bool_)):
        valor = int(valor)
    if isinstance(valor, (int, float, np.integer, np.floating)):
        exige(math.isfinite(float(valor)), f"{clave}: valor no finito {valor!r}")
        valor = int(valor) if isinstance(valor, (int, np.integer)) else float(valor)
    else:
        exige(isinstance(valor, str) and bool(valor), f"{clave}: valor vacío")
    exige(isinstance(texto_en, str) and bool(texto_en), f"{clave}: texto_en vacío")
    exige(not re.search(r"\d,\d{1,2}(?!\d)", texto_en), f"{clave}: texto_en con coma decimal {texto_en!r}")
    exige(re.fullmatch(r"§\d+(\.\d+)?", seccion) is not None, f"{clave}: sección mal formada {seccion!r}")
    FILAS.append(dict(clave=clave, valor=valor, unidad=unidad, texto_en=texto_en,
                      definicion=definicion, fuente=fuente, seccion_canon=seccion))


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


def finito(s, qué: str):
    exige(bool(np.isfinite(np.asarray(s, dtype=float)).all()), f"{qué}: valores no finitos")
    return s


# ── CANON.md: secciones y tablas escritas ───────────────────────────────────
_CANON = CANON_MD.read_text(encoding="utf-8")


def seccion(prefijo: str) -> str:
    """Texto de la sección cuyo encabezado empieza por `prefijo` (p. ej.
    «## 6 ·» o «### 13.3 ·»), hasta el siguiente encabezado de nivel igual o
    menor, o hasta la primera subsección."""
    lineas = _CANON.splitlines()
    ini = [i for i, l in enumerate(lineas) if l.startswith(prefijo)]
    exige(len(ini) == 1, f"CANON.md: {len(ini)} encabezados «{prefijo}»")
    i0 = ini[0]
    fin = next((j for j in range(i0 + 1, len(lineas)) if lineas[j].startswith("#")), len(lineas))
    return "\n".join(lineas[i0:fin])


def num_es(s: str) -> float:
    """Número escrito en español en el canon: «−1,72», «2 048», «**56,25**», «39 %»."""
    t = s.replace("*", "").replace("%", "").replace("−", "-")
    t = re.sub(r"[\s  ]", "", t).replace(",", ".")
    exige(re.fullmatch(r"-?\d+(\.\d+)?", t) is not None, f"CANON.md: número ilegible {s!r}")
    return float(t)


def tablas(texto: str) -> list[pd.DataFrame]:
    """Las tablas Markdown de un texto, como DataFrames de cadenas indexados por
    la primera columna."""
    out, bloque = [], []
    for l in texto.splitlines() + [""]:
        if l.startswith("|"):
            bloque.append(l)
        elif bloque:
            celdas = [[c.strip() for c in f.strip().strip("|").split("|")] for f in bloque]
            cab, filas = celdas[0], celdas[2:]
            out.append(pd.DataFrame(filas, columns=cab).set_index(cab[0]))
            bloque = []
    return out


def texto_canon(sec: str, patron: str) -> re.Match:
    m = re.search(patron, seccion(sec), re.S)
    exige(m is not None, f"CANON.md {sec}: no se encuentra /{patron}/")
    return m


# ── 1. La hoja Resumen de los 13 casos ──────────────────────────────────────
F_RES = "entrega_matriz_reposo_2026-09-19/SALIDAS_SERVIDOR/matriz_reposo/{}/outputs/resultados_comparacion.xlsx, hoja Resumen, Ganancia_neta_COP"


def resumen() -> pd.DataFrame:
    R = {}
    for c in CASOS:
        p = lee(f"SALIDAS_SERVIDOR/matriz_reposo/{c}/outputs/resultados_comparacion.xlsx")
        r = pd.read_excel(p, sheet_name="Resumen").set_index("Escenario")["Ganancia_neta_COP"]
        finito(r, f"Resumen {c}")
        exige(r["C4_mensual"] == r["C4"], f"{c}: C4 mensual distinto de C4")
        exige(abs(r["P2P"] - r["C2"]) <= 1e-6, f"{c}: P2P distinto de C2 en el agregado")
        R[c] = r
    R = pd.DataFrame(R).T
    ok("P2P = C2 (≤ 1e-6 COP) y C4 = C4 mensual (exacto) en los 13 casos")
    # compuerta: la tabla de CANON §6 a dos decimales
    t6 = tablas(seccion("## 6 ·"))
    exige(len(t6) == 1, "CANON §6: se esperaba una tabla")
    t6 = t6[0]
    exige(list(t6.index) == CASOS, f"CANON §6: casos {list(t6.index)}")
    for c in CASOS:
        for mec, (_, col) in MECS.items():
            v, esp = R.loc[c, mec] / M, num_es(t6.loc[c, col])
            exige(abs(v - esp) <= 0.005 + 1e-9, f"{c} {mec}: {v:.6f} MCOP no redondea a {esp} de CANON §6")
    ok("la tabla de CANON §6 (P2P, P2P colectivo, C1, C4, C5) a dos decimales en los 13 casos")
    return R


def comunidad(R: pd.DataFrame, c7: dict, D: pd.DataFrame) -> None:
    for c in CASOS:
        r = R.loc[c]
        fr = F_RES.format(c)
        for mec, (suf, _) in MECS.items():
            pon(f"com__{c}__{suf}", r[mec] / M, "MCOP", en(r[mec] / M, 2),
                f"beneficio neto de la comunidad con {mec}, caso {c}", fr, "§6")
        p2p_c1, c1_c4, p2p_c4 = r.P2P - r.C1, r.C1 - r.C4, r.P2P - r.C4
        col_c4 = r.P2P_colectivo - r.C4
        # identidad al peso (float64 del libro)
        exige(abs(p2p_c4 - (p2p_c1 + c1_c4)) <= 1e-6,
              f"{c}: P2P − C4 ≠ (P2P − C1) + (C1 − C4): {p2p_c4 - (p2p_c1 + c1_c4)} COP")
        # las brechas de cap. 7 son las de Resumen
        for k7, v in [("P2P_menos_C1", p2p_c1), ("C1_menos_C4", c1_c4), ("P2P_menos_C4", p2p_c4),
                      ("colectivo_menos_C4", col_c4)]:
            exige(abs(c7[f"comunidad__{c}__{k7}"] - v / M) <= 1e-9,
                  f"{c}: {k7} de cifras_cap07 distinto del recalculado de Resumen")
        pon(f"com__{c}__P2P_C1", p2p_c1 / M, "MCOP", en(p2p_c1 / M, 2),
            f"P2P − C1 de la comunidad, caso {c}", fr + ", resta", "§14.8")
        pon(f"com__{c}__C1_C4", c1_c4 / M, "MCOP", en(c1_c4 / M, 2),
            f"C1 − C4 de la comunidad, caso {c}", fr + ", resta", "§6")
        pon(f"com__{c}__P2P_C4", p2p_c4 / M, "MCOP", en(p2p_c4 / M, 2),
            f"P2P − C4 de la comunidad, caso {c}", fr + ", resta", "§6")
        pon(f"com__{c}__P2Pcol_C4", col_c4 / M, "MCOP", en(col_c4 / M, 2),
            f"P2P colectivo − C4 de la comunidad, caso {c}", fr + ", resta", "§6")
        F7 = "cifras_cap07_2026-09-28/cifras.csv, clave "
        for k7, suf, dfn in [("P2P_menos_C1_pct_C1", "P2P_C1_pct", "P2P − C1 sobre C1"),
                             ("P2P_menos_C4_pct_C4", "P2P_C4_pct", "P2P − C4 sobre C4"),
                             ("colectivo_menos_C4_pct_C4", "P2Pcol_C4_pct", "P2P colectivo − C4 sobre C4")]:
            v = c7[f"comunidad__{c}__{k7}"]
            pon(f"com__{c}__{suf}", v, "%", en(v, 2, " %"), f"{dfn}, caso {c}",
                F7 + f"comunidad__{c}__{k7}", "§14.18")
        k = f"comunidad__{c}__C1_menos_C4_pct_P2P_menos_C4"
        exige((k in c7) == (r.C1 > r.C4), f"{c}: la parte de C1 − C4 no está donde C1 > C4")
        if r.C1 > r.C4:
            v = c7[k]
            exige(abs(v - 100 * c1_c4 / p2p_c4) <= 1e-9, f"{c}: parte de C1 − C4 distinta de la recalculada")
            pon(f"com__{c}__C1C4_share", v, "%", en_int(round(v), " %"),
                f"(C1 − C4) / (P2P − C4), caso {c} (C1 > C4)", F7 + k, "§14.18")
        d = D.loc[c]
        for col, suf, dfn in [("banda", "banda", "banda (prima del vendedor sobre su piso más ahorro del comprador bajo su techo)"),
                              ("reclasificacion", "reclas", "reclasificación (P2P − C1 − banda)")]:
            pon(f"com__{c}__{suf}", d[col] / M, "MCOP", en(d[col] / M, 2), f"{dfn} de la comunidad, caso {c}",
                "descomposicion_p2p_2026-09-27/descomposicion_13casos.csv, fila comunidad, columna " + col, "§14.8")
    ok("P2P − C4 = (P2P − C1) + (C1 − C4) al peso (≤ 1e-6 COP) en los 13 casos")
    ok("las brechas y porcentajes de cifras_cap07 reproducen la hoja Resumen (≤ 1e-9 MCOP)")


# ── 2. La descomposición de §14.8 ───────────────────────────────────────────
def descomposicion(R: pd.DataFrame) -> pd.DataFrame:
    d = pd.read_csv(lee("descomposicion_p2p_2026-09-27/descomposicion_13casos.csv", "e1/C5"))
    num = ["P2P", "C1", "banda_vendedor", "banda_comprador", "banda", "reclasificacion", "P2P_menos_C1"]
    finito(d[num].to_numpy(), "descomposicion_13casos")
    com = d[d.agente == "comunidad"].set_index("caso")
    exige(sorted(com.index) == sorted(CASOS) and com.index.is_unique, "descomposicion: filas comunidad")
    ag = d[d.agente != "comunidad"].groupby("caso")[num].sum()
    for c in CASOS:
        dif = float((ag.loc[c, num] - com.loc[c, num]).abs().max())
        exige(dif <= 1.0, f"{c}: la fila comunidad difiere de la suma de agentes en {dif} COP")
        s = com.loc[c, "banda"] + com.loc[c, "reclasificacion"]
        exige(abs(s - com.loc[c, "P2P_menos_C1"]) <= 1.0,
              f"{c}: banda + reclasificación = {s}, P2P − C1 del almacén = {com.loc[c, 'P2P_menos_C1']}")
        # El almacén va en float32: P2P y C1 de la comunidad reproducen Resumen a
        # unos pocos COP (hasta 5,1 en C1 de N1), no a 1 COP; la tolerancia es la
        # relativa del float32 acumulado, 1e-7 del beneficio del mercado.
        tol = max(1.0, 1e-7 * abs(R.loc[c, "P2P"]))
        res = R.loc[c, "P2P"] - R.loc[c, "C1"]
        for x, y, q in [(com.loc[c, "P2P"], R.loc[c, "P2P"], "P2P"), (com.loc[c, "C1"], R.loc[c, "C1"], "C1"),
                        (s, res, "banda + reclasificación frente a P2P − C1")]:
            exige(abs(x - y) <= tol, f"{c}: {q} del almacén {x} frente a Resumen {y} (tolerancia {tol:.1f} COP)")
    ok("descomposición: comunidad = suma de agentes (≤ 1 COP), banda + reclasificación = P2P − C1 del almacén "
       "(≤ 1 COP), y P2P, C1 y banda + reclasificación = Resumen dentro del float32 (≤ 1e-7 del beneficio)")
    t = tablas(seccion("### 14.8 ·"))
    exige(len(t) == 1, "CANON §14.8: se esperaba una tabla")
    t = t[0]
    exige(list(t.index) == CASOS, "CANON §14.8: casos")
    for c in CASOS:
        for col, cc in [("P2P − C1 (MCOP)", None), ("Banda (MCOP)", "banda"),
                        ("Reclasificación (MCOP)", "reclasificacion")]:
            v = (R.loc[c, "P2P"] - R.loc[c, "C1"]) / M if cc is None else com.loc[c, cc] / M
            esp = num_es(t.loc[c, col])
            exige(abs(v - esp) <= 0.0005 + 1e-9, f"{c} {col}: {v:.6f} no redondea a {esp} de CANON §14.8")
        frac = 100 * com.loc[c, "reclasificacion"] / (R.loc[c, "P2P"] - R.loc[c, "C1"])
        esp = num_es(t.loc[c, "Reclasificación / (P2P − C1)"])
        exige(abs(frac - esp) <= 0.5 + 1e-9, f"{c}: reclasificación / (P2P − C1) {frac:.3f} % frente a {esp} %")
    ok("la tabla de CANON §14.8 a tres decimales (y el cociente en entero) en los 13 casos")
    return com


# ── 3. Resúmenes de la comunidad ────────────────────────────────────────────
def resumenes(R: pd.DataFrame, c7: dict) -> None:
    F7 = "cifras_cap07_2026-09-28/cifras.csv, claves comunidad__<caso>__"
    sh = {c: c7[f"comunidad__{c}__C1_menos_C4_pct_P2P_menos_C4"] for c in CASOS
          if R.loc[c, "C1"] > R.loc[c, "C4"]}
    exige(len(sh) == 10, f"casos con C1 > C4: {len(sh)}, se esperaban 10")
    atipico = min(sh, key=sh.get)
    exige(atipico == "P2" and round(sh["P2"]) == 4, f"el caso atípico es {atipico} ({sh[atipico]:.2f} %), no P2 con 4 %")
    resto = {c: v for c, v in sh.items() if c != atipico}
    mn, mx = min(resto.values()), max(resto.values())
    exige((round(mn), round(mx)) == (79, 96), f"share en [{mn:.2f}, {mx:.2f}], no [79, 96]")
    n = sum(79 <= round(v) <= 96 for v in sh.values())
    exige(n == 9, f"share en [79, 96] en {n} casos, no en 9 de 10")
    ok("share: 9 de 10 casos con C1 > C4 en [79, 96] % y P2 con 4 % (redondeo entero)")
    casos_share = ", ".join(sh)
    pon("share_casos_C1_sobre_C4", len(sh), "casos", en_int(len(sh)),
        f"casos con C1 > C4 ({casos_share})", F7 + "C1_menos_C4_pct_P2P_menos_C4, conteo", "§14.18")
    pon("share_min", mn, "%", en_int(round(mn), " %"),
        f"mínimo de (C1 − C4) / (P2P − C4) en los casos con C1 > C4 salvo P2 ({min(resto, key=resto.get)})",
        F7 + "C1_menos_C4_pct_P2P_menos_C4, mínimo", "§14.18")
    pon("share_max", mx, "%", en_int(round(mx), " %"),
        f"máximo de (C1 − C4) / (P2P − C4) en los casos con C1 > C4 ({max(resto, key=resto.get)})",
        F7 + "C1_menos_C4_pct_P2P_menos_C4, máximo", "§14.18")
    pon("share_n", n, "casos de 10", en_int(n),
        "casos con C1 > C4 en que (C1 − C4) / (P2P − C4) redondea a un entero entre share_min y share_max",
        F7 + "C1_menos_C4_pct_P2P_menos_C4, conteo", "§14.18")
    pon("share_P2", sh["P2"], "%", en_int(round(sh["P2"]), " %"),
        "(C1 − C4) / (P2P − C4) en P2, el caso atípico", F7 + "C1_menos_C4_pct_P2P_menos_C4 (P2)", "§14.18")
    col = {c: c7[f"comunidad__{c}__colectivo_menos_C4_pct_C4"] for c in CASOS}
    cmn, cmx = min(col, key=col.get), max(col, key=col.get)
    exige((round(col[cmn], 2), round(col[cmx], 2)) == (-0.96, 1.69),
          f"col_pct en [{col[cmn]:.4f}, {col[cmx]:.4f}], no [−0,96; +1,69]")
    ok(f"col_pct en [−0,96; +1,69] % ({cmn} y {cmx}) con el redondeo a dos decimales")
    pon("col_pct_min", col[cmn], "%", en(col[cmn], 2, " %"),
        f"mínimo de (P2P colectivo − C4) / C4 en los 13 casos ({cmn})",
        F7 + "colectivo_menos_C4_pct_C4, mínimo", "§14.18")
    pon("col_pct_max", col[cmx], "%", en(col[cmx], 2, " %"),
        f"máximo de (P2P colectivo − C4) / C4 en los 13 casos ({cmx})",
        F7 + "colectivo_menos_C4_pct_C4, máximo", "§14.18")
    sobre = [c for c in CASOS if R.loc[c, "P2P_colectivo"] > R.loc[c, "C4"]]
    m = texto_canon("### 14.7 ·", r"el\s+colectivo\s+queda\s+por\s+encima\s+de\s+C4\s+solo\s+en\s+([^.]+)\.")
    canon_sobre = [x.strip() for x in re.split(r",|\sy\s", m.group(1)) if x.strip()]
    exige(sorted(sobre) == sorted(canon_sobre), f"colectivo sobre C4 en {sobre}, CANON §14.7 dice {canon_sobre}")
    ok(f"colectivo sobre C4 en {', '.join(sobre)}, como CANON §14.7")
    pon("col_casos_sobre_C4", ", ".join(sobre), "casos", ", ".join(sobre),
        "casos en que el mercado por la vía del colectivo deja más que C4", F_RES.format("<caso>") + ", resta",
        "§14.7")
    pon("col_n_sobre_C4", len(sobre), "casos de 13", en_int(len(sobre)),
        "número de casos en que el mercado por la vía del colectivo deja más que C4",
        F_RES.format("<caso>") + ", resta", "§14.7")


# ── 4. El GSA directo (§13.3) ───────────────────────────────────────────────
def gsa() -> None:
    pb = pd.read_csv(lee("SALIDAS_SERVIDOR/gsa_directo/base/punto_base.csv", "gsa/base")).set_index("caso")
    s = seccion("### 13.3 ·")
    tp, tb = tablas(s)
    exige(list(tp.index) == CASOS_GSA and list(tb.index) == CASOS_GSA, "CANON §13.3: casos de las tablas")
    ic = {}
    for m in re.finditer(r"^- (\w+): (.+)\.$", s, re.M):
        for rot, lo, hi in re.findall(r"([^,;]+?), \[([−\d,]+); ([−\d,]+)\]", m.group(2)):
            ic[(m.group(1), rot.strip())] = (num_es(lo), num_es(hi))
    exige(len(ic) == 12, f"CANON §13.3: {len(ic)} intervalos leídos, se esperaban 12")
    sin_inv = {b: 0 for b in BRECHAS}
    for c in CASOS_GSA:
        v = pd.read_csv(lee(f"SALIDAS_SERVIDOR/gsa_directo/{c}/inversion_{c}.csv", f"gsa/{c}")).set_index("salida")
        n = int(num_es(tp.loc[c, "n"]))
        for b, (suf, rot) in BRECHAS.items():
            f = v.loc[b]
            finito([f.p_inversion, f.p_inf, f.p_sup, f.base], f"inversion_{c} {b}")
            exige(int(f.n_filas) == 2 * n, f"{c} {b}: {f.n_filas} filas, CANON §13.3 da n = {n}")
            exige(abs(f.base - pb.loc[c, b]) <= 1e-6, f"{c} {b}: la base de inversion no es la de punto_base")
            exige(f.p_inf <= f.p_inversion <= f.p_sup, f"{c} {b}: P fuera de su intervalo")
            p, lo, hi = 100 * f.p_inversion, 100 * f.p_inf, 100 * f.p_sup
            esp = num_es(tp.loc[c, rot])
            exige(abs(p - esp) <= 0.005 + 1e-9, f"{c} {b}: P = {p:.4f} %, CANON §13.3 da {esp}")
            if esp == 0:
                exige(lo == 0 and hi == 0 and (c, rot) not in ic, f"{c} {b}: P nula con intervalo no nulo")
                sin_inv[b] += 1
            else:
                elo, ehi = ic[(c, rot)]
                exige(abs(lo - elo) <= 0.005 + 1e-9 and abs(hi - ehi) <= 0.005 + 1e-9,
                      f"{c} {b}: intervalo [{lo:.4f}, {hi:.4f}], CANON §13.3 da [{elo}, {ehi}]")
            eb = num_es(tb.loc[c, rot])
            exige(abs(f.base / M - eb) <= 0.005 + 1e-9, f"{c} {b}: base {f.base / M:.4f} MCOP, CANON §13.3 da {eb}")
            FG = f"entrega_gsa_directo_completo_2026-09-27/SALIDAS_SERVIDOR/gsa_directo/{c}/inversion_{c}.csv, fila {b}, columna "
            pon(f"gsa__{c}__{suf}__p", p, "%", en(p, 2, " %"), f"P(inversión) de {rot} en la caja del GSA, caso {c}",
                FG + "p_inversion", "§13.3")
            pon(f"gsa__{c}__{suf}__lo", lo, "%", en(lo, 2, " %"), f"cota inferior al 95 % de P(inversión) de {rot}, caso {c}",
                FG + "p_inf", "§13.3")
            pon(f"gsa__{c}__{suf}__hi", hi, "%", en(hi, 2, " %"), f"cota superior al 95 % de P(inversión) de {rot}, caso {c}",
                FG + "p_sup", "§13.3")
            pon(f"gsa__{c}__{suf}__base", f.base / M, "MCOP", en(f.base / M, 2), f"{rot} en el punto base del GSA, caso {c}",
                "entrega_gsa_directo_completo_2026-09-27/SALIDAS_SERVIDOR/gsa_directo/base/punto_base.csv, columna " + b,
                "§13.3")
        pon(f"gsa__{c}__n", n, "muestras base", en_int(n), f"n_base del Sobol, caso {c} (n_filas / 2)",
            f"inversion_{c}.csv, columna n_filas", "§13.3")
    ok("la tabla de P(inversión), sus 12 intervalos y la tabla del punto base de CANON §13.3 en los 12 casos")
    pon("gsa__n_casos", len(CASOS_GSA), "casos", en_int(len(CASOS_GSA)), "casos del Sobol (sin CV2)",
        "gsa_directo/<caso>/inversion_<caso>.csv", "§13.3")
    for b in ["P2P_menos_C4", "P2P_menos_C1"]:
        suf = BRECHAS[b][0]
        exige(sin_inv[b] == 12, f"{b}: P(inversión) nula en {sin_inv[b]} casos, no en 12")
        pon(f"gsa__n_casos_sin_inversion_{suf}", sin_inv[b], "casos de 12", en_int(sin_inv[b]),
            f"casos del Sobol con P(inversión) de {BRECHAS[b][1]} igual a cero",
            "gsa_directo/<caso>/inversion_<caso>.csv, columna p_inversion, conteo", "§13.3")
    ok("P2P − C1 y P2P − C4 sin inversión en los 12 casos")


# ── 5. E4 y las constantes publicables ──────────────────────────────────────
def e4(c7: dict) -> None:
    F7 = "cifras_cap07_2026-09-28/cifras.csv, clave "
    for k in ["consumo", "importacion"]:
        v, vp = c7[f"reglas__E4__{k}_menos_P2P"], c7[f"reglas__E4__{k}_menos_P2P_pct"]
        pon(f"e4__{k}_menos_P2P", v, "MCOP", en(v, 2),
            f"C4 de E4 con la regla mensual del art. 19 por {k} menos el mercado", F7 + f"reglas__E4__{k}_menos_P2P",
            "§14.18")
        pon(f"e4__{k}_menos_P2P_pct", vp, "%", en(vp, 2, " %"),
            f"la misma diferencia sobre el beneficio del mercado de E4", F7 + f"reglas__E4__{k}_menos_P2P_pct", "§14.18")
    m = texto_canon("### 14.18 ·", r"superan\s+al\s+mercado\s+por\s+\*\*([\d,]+)\s+y\s+([\d,]+)\s+MCOP\*\*\s+\(([\d,]+)\s+y\s+([\d,]+)\s+%\)")
    esp = [num_es(x) for x in m.groups()]
    got = [c7["reglas__E4__consumo_menos_P2P"], c7["reglas__E4__importacion_menos_P2P"],
           c7["reglas__E4__consumo_menos_P2P_pct"], c7["reglas__E4__importacion_menos_P2P_pct"]]
    exige(all(abs(g - e) <= 0.005 + 1e-9 for g, e in zip(got, esp)), f"E4 reglas {got} frente a CANON §14.18 {esp}")
    ok("E4: consumo e importación sobre el mercado, 0,36 y 0,18 MCOP (0,18 y 0,09 %), como CANON §14.18")


def constantes(c7: dict) -> None:
    # validación dinámica: CANON §9 (texto), contrastada con m_a_regimenes.json
    m = texto_canon("## 9 ·", r"de\s+(\d+)\s+horas\s+muestreadas,\s+la\s+dinámica\s+integró\s+(\d+)\s+hasta\s+el\s+final\s+y\s+en\s+(\d+)\s+llegó\s+a\s+la\s+forma\s+cerrada")
    muestreadas, integradas, confirmadas = (int(x) for x in m.groups())
    reg = json.loads(lee("entrega_validacion_2026-09-19/SALIDAS_SERVIDOR/validacion_reposo/m_a_regimenes.json",
                         "e1/V").read_text(encoding="utf-8"))
    h = {(r["spec"]["caso"], r["spec"]["fecha"]) for r in reg}
    h160 = {(r["spec"]["caso"], r["spec"]["fecha"]) for r in reg if (r.get("teq_alcanzado") or 0) >= 160}
    exige((len(h), len(h160)) == (muestreadas, integradas) and {c for c, _ in h} == {"E0"},
          f"m_a_regimenes.json: {len(h)} horas y {len(h160)} integradas, CANON §9 dice {muestreadas} y {integradas}")
    ok(f"validación: {muestreadas} horas de E0 muestreadas y {integradas} integradas, como CANON §9")
    FV = "CANON.md §9 (texto); el total de horas integradas se contrasta con m_a_regimenes.json (e1/V, teq ≥ 160)"
    pon("validacion__confirmadas", confirmadas, "h", en_int(confirmadas),
        "horas de E0 en que la dinámica integrada hasta el final llegó a la forma cerrada", "CANON.md §9 (texto)", "§9")
    pon("validacion__integradas", integradas, "h", en_int(integradas),
        "horas de E0 que la dinámica integró hasta el final", FV, "§9")
    pon("validacion__muestreadas", muestreadas, "h", en_int(muestreadas),
        "horas de E0 muestreadas en la validación dinámica", FV, "§9")
    # horizonte
    d = pd.read_csv(lee("cifras_datos_2026-09-28/cifras.csv", "e1/D"), dtype={"valor": str})
    hz = float(d.set_index("clave").loc["horizonte_horas", "valor"])
    exige(hz == 6144.0, f"horizonte {hz} h")
    pon("horas_total", int(hz), "h", en_int(hz), "horizonte de la corrida (256 días desde el 2025-04-04)",
        "cifras_datos_2026-09-28/cifras.csv, clave horizonte_horas", "§14.17")
    # horas cuantales y con mercado: almacenes, contra CANON §10.1
    cu, me = 0, 0
    for c in CASOS:
        hh = pd.read_parquet(lee(f"SALIDAS_SERVIDOR/matriz_reposo/{c}/almacen/m1/horas/parte_0000.parquet"))
        exige(len(hh) == 6144, f"{c}: la tabla horas no tiene 6 144 filas")
        cu += int((hh.regimen == "cuantal").sum())
        me += int(hh.regimen.isin(REGIMENES_MERCADO).sum())
    m = texto_canon("### 10.1 ·", r"(\d+)\s+horas\s+de\s+las\s+(\d{1,3}(?:[   ]\d{3})*)\s+con\s+mercado")
    exige((cu, me) == (int(m.group(1)), int(num_es(m.group(2)))), f"horas cuantales {cu} de {me}, CANON §10.1 dice {m.groups()}")
    ok(f"horas cuantales {cu} de {me} con mercado en los 13 almacenes, como CANON §10.1")
    FA = "almacen/m1/horas/parte_0000.parquet de los 13 casos (matriz del 19), columna regimen"
    pon("horas_cuantales", cu, "h", en_int(cu), "horas resueltas en la rama cuantal (D71), suma de los 13 casos",
        FA + " = «cuantal»", "§10.1")
    pon("horas_mercado", me, "h", en_int(me), "horas con mercado, suma de los 13 casos",
        FA + " en los regímenes con mercado", "§10.1")
    # parte del vendedor de E0 (almacén), contra CANON §4
    cm = pd.read_csv(lee("compara_matriz_reposo.csv", "comparacion"), comment="#")
    f = cm[(cm.caso == "E0") & (cm.institucion == "comunidad")]
    exige(len(f) == 1, "compara: sin la fila E0 comunidad")
    pv = float(f.parte_vendedor_nueva.iloc[0])
    t4 = tablas(seccion("## 4 ·"))[0]
    exige(abs(pv - num_es(t4.loc["E0", "Parte del vendedor"])) <= 0.0005 + 1e-9, f"parte del vendedor de E0 {pv}")
    ok("parte del vendedor de E0 (almacén) = 0,542, como CANON §4")
    pon("parte_vendedor_E0", pv, "fracción", en(pv, 3),
        "parte del vendedor de E0: prima sobre el piso del juego / (prima + ahorro del comprador), del almacén",
        "compara_matriz_reposo.csv (matriz del 19), fila E0 comunidad, columna parte_vendedor_nueva", "§4")
    # techo del ponderado y COT (e1/T), contra CANON §14.16
    ha = pd.read_csv(lee("contrafactico_techo_cot_2026-09-28/horas_afectadas.csv", "e1/T"))
    finito(ha[["horas_bolsa_sobre_PrecEscaPon", "excedente_fisico_PrecEscaPon_kWh"]].to_numpy(), "horas_afectadas")
    th = {c: int(g.horas_bolsa_sobre_PrecEscaPon.sum()) for c, g in ha.groupby("caso")}
    exige(set(th.values()) == {38} and len(th) == 13, f"horas sobre el ponderado por caso: {th}")
    exige(float(ha.excedente_fisico_PrecEscaPon_kWh.abs().sum()) == 0.0, "exportación en las horas sobre el ponderado")
    texto_canon("### 14.16 ·", r"supera\s+el\s+ponderado\s+en\s+\*\*38\s+horas")
    ok("techo: 38 horas sobre el ponderado en los 13 casos, sin exportación, como CANON §14.16")
    pon("techo_horas", 38, "h", en_int(38), "horas del horizonte con la bolsa del modelo por encima del precio de escasez ponderado",
        "contrafactico_techo_cot_2026-09-28/horas_afectadas.csv, suma de horas_bolsa_sobre_PrecEscaPon (igual en los 13)",
        "§14.16")
    pon("techo_exportacion_kWh", 0.0, "kWh", en(0.0, 0), "energía exportada por la comunidad en esas horas, en los 13 casos",
        "contrafactico_techo_cot_2026-09-28/horas_afectadas.csv, excedente_fisico_PrecEscaPon_kWh", "§14.16")
    mc = pd.read_csv(lee("contrafactico_techo_cot_2026-09-28/mecanismos_13casos.csv", "e1/T"))
    cot = mc[mc.variante == "cot"]
    exige(len(cot) == 13, f"mecanismos_13casos: {len(cot)} filas cot")
    pct = {m_: float(cot[f"d_{m_}_pct"].abs().max()) for m_ in ["P2P", "P2P_colectivo", "C1", "C2", "C3", "C4", "C5"]}
    finito(list(pct.values()), "d_pct del COT")
    mec_max = max(pct, key=pct.get)
    exige(mec_max == "C4" and round(pct["C4"], 2) == 0.49, f"COT: mayor cambio {pct}")
    ok("COT: el mayor cambio es de C4, 0,49 %, como CANON §14.16")
    pon("cot_max_pct", pct["C4"], "%", en(pct["C4"], 2, " %"),
        "mayor baja relativa de un mecanismo con el COT en la deducción (C4), sobre los 13 casos",
        "contrafactico_techo_cot_2026-09-28/mecanismos_13casos.csv, variante cot, máximo de |d_<mecanismo>_pct|", "§14.16")
    # pares bajo C4 y CESMAG en N1 (cap. 7)
    F7 = "cifras_cap07_2026-09-28/cifras.csv, clave "
    n_pares = sum(1 for k in c7 if re.fullmatch(r"institucion__\w+__\w+__P2P_menos_C4", k))
    neg = int(c7["institucion__P2P_menos_C4__negativos"])
    exige((neg, n_pares) == (25, 64), f"pares bajo C4: {neg} de {n_pares}")
    ok("pares institución-caso bajo C4: 25 de 64, como CANON §14.18")
    pon("pares_bajo_C4", neg, "pares", en_int(neg), "pares institución-caso con P2P − C4 negativo",
        F7 + "institucion__P2P_menos_C4__negativos", "§14.18")
    pon("pares_total", n_pares, "pares", en_int(n_pares), "pares institución-caso de los 13 casos",
        F7 + "institucion__<caso>__<institución>__P2P_menos_C4, conteo", "§14.18")
    cb = c7["fragiles__N1__Cesmag__P2P_menos_C4__base"]
    exige(abs(cb - 3669.5485) < 0.01, f"CESMAG en N1: {cb}")
    pon("cesmag_N1_fragil", cb, "COP", en(cb, 1), "P2P − C4 de CESMAG en N1 en el canon (signo frágil)",
        F7 + "fragiles__N1__Cesmag__P2P_menos_C4__base", "§14.18")
    for s, t in [("0", "0"), ("05", "0.5"), ("1", "1")]:
        v = c7[f"fragiles__N1__Cesmag__P2P_menos_C4__sigma_{s}"]
        exige(v < 0, f"CESMAG en N1 con σ = {t}: no cambia de signo")
        pon(f"cesmag_N1_fragil__sigma_{s}", v, "COP", en(v, 0), f"P2P − C4 de CESMAG en N1 con σ = {t}",
            F7 + f"fragiles__N1__Cesmag__P2P_menos_C4__sigma_{s}", "§14.18")
    vn = pd.read_csv(lee("SALIDAS_SERVIDOR/gsa_directo/N1/inversion_N1.csv", "gsa/N1")).set_index("salida")
    pn = 100 * float(vn.loc["P2P_menos_C4__Cesmag", "p_inversion"])
    pon("cesmag_N1_fragil__p_gsa", pn, "%", en(pn, 2, " %"), "P(inversión) de P2P − C4 de CESMAG en N1 en la caja del GSA",
        "entrega_gsa_directo_completo_2026-09-27/SALIDAS_SERVIDOR/gsa_directo/N1/inversion_N1.csv, fila P2P_menos_C4__Cesmag",
        "§13.5")
    # deserción en E4: el umbral de unas dos veces la bolsa (e1/C7), contra CANON §14.10
    ds = pd.read_csv(lee("infactibilidad_desercion_2026-09-27/desercion_c1_por_fbolsa.csv", "e1/C7"))
    e = ds[ds.caso == "E4"].copy()
    finito(e.p_desercion, "deserción E4")
    e["lo"] = e.tramo.str.extract(r"\(([\d.]+),")[0].astype(float)
    e["hi"] = e.tramo.str.extract(r", ([\d.]+)\]")[0].astype(float)
    pmax = e.groupby("lo").p_desercion.max().sort_index()
    umbral = float(pmax[pmax > 0.05].index.min())
    exige(umbral == 2.0 and float(pmax[pmax.index < umbral].max()) < 0.01,
          f"E4: el primer tramo con deserción de más del 5 % empieza en {umbral}; bajo él, {pmax[pmax.index < umbral].max()}")
    m = texto_canon("### 14.10 ·", r"con\s+f_bolsa\s+entre\s+2\s+y\s+3,\s+HUDN\s+en\s+el\s+([\d,]+)\s+%\s+de\s+los\s+puntos\s+y\s+Cesmag\s+en\s+el\s+([\d,]+)\s+%;\s+entre\s+3\s+y\s+4,\s+en\s+el\s+([\d,]+)\s+%\s+y\s+el\s+([\d,]+)\s+%")
    esp = [num_es(x) for x in m.groups()]
    val = {}
    for inst, lo in [("HUDN", 2.0), ("Cesmag", 2.0), ("HUDN", 3.0), ("Cesmag", 3.0)]:
        f = e[(e.institucion == inst) & (e.lo == lo)]
        exige(len(f) == 1, f"deserción E4 {inst} {lo}")
        val[(inst, lo)] = 100 * float(f.p_desercion.iloc[0])
    got = [val[("HUDN", 2.0)], val[("Cesmag", 2.0)], val[("HUDN", 3.0)], val[("Cesmag", 3.0)]]
    exige(all(abs(g - x) <= 0.05 + 1e-9 for g, x in zip(got, esp)), f"deserción E4 {got} frente a CANON §14.10 {esp}")
    ok("deserción en E4: umbral en f_bolsa = 2 y los cuatro porcentajes de CANON §14.10")
    FD = "infactibilidad_desercion_2026-09-27/desercion_c1_por_fbolsa.csv"
    pon("desercion_E4_umbral", umbral, "× bolsa de 2025", en(umbral, 0),
        "límite inferior del primer tramo de f_bolsa con deserción hacia C1 de más del 5 % en E4 (solo E4, H-103)",
        FD + ", filas E4, tramo", "§14.10")
    for (inst, lo), v in val.items():
        tr = "2_3" if lo == 2.0 else "3_4"
        pon(f"desercion_E4__{inst}__{tr}", v, "%", en(v, 2, " %"),
            f"deserción hacia C1 de {inst} en E4 con f_bolsa en ({lo:g}, {lo + 1:g}]", FD, "§14.10")


# ════════════════════════════════════════════════════════════════════════════
# Añadido el 2026-09-30 (Tarea A1). Todo lo de abajo emite claves nuevas al
# final de la tabla; nada de lo de arriba cambia.
# ════════════════════════════════════════════════════════════════════════════
MES_REP = "2025-04"          # el mes de los ejemplos de las respuestas a las notas
F_DAT = "cifras_datos_2026-09-28/cifras.csv, clave "
PREF_ALM = "SALIDAS_SERVIDOR/matriz_reposo/{}/almacen/m1/{}/"
F_ALM = "entrega_matriz_reposo_2026-09-19/SALIDAS_SERVIDOR/matriz_reposo/{}/almacen/m1/{}"
UMBRAL_NUMERAL_KW = 100.0    # art. 25 de la CREG 174: numeral 1 hasta 100 kW
UMBRAL_PARTICIPACION = 10.0  # art. 20 de la CREG 101 072: caso 1 si toda participación < 10 %
FACTORES = ["f_cv", "f_bolsa", "f_tarifa", "f_peaje", "e_G", "e_D"]


def en_factor(v: float) -> str:
    """Factor de escala: entero, 1/k o hasta dos decimales sin ceros de sobra."""
    if abs(v - round(v)) < 1e-6:
        return en_int(round(v))
    if v < 1 and abs(1 / v - round(1 / v)) < 1e-4:
        return f"1/{round(1 / v)}"
    return f"{v:.2f}".rstrip("0").rstrip(".")


def almacen(c: str, tabla: str) -> pd.DataFrame:
    """La tabla `tabla` del almacén del caso `c`: todas sus partes, cada una con
    su huella comprobada; las partes en disco tienen que ser las de HUELLAS.csv."""
    pref = PREF_ALM.format(c, tabla)
    rutas = sorted(r for r in _H[_H.grupo == f"almacen/{c}"].ruta if r.startswith(pref))
    exige(len(rutas) >= 1, f"{c}: sin partes de «{tabla}» en HUELLAS.csv")
    en_disco = sorted(p.name for p in (BASE_MATRIZ / pref).glob("*.parquet"))
    exige(en_disco == [r.rsplit("/", 1)[1] for r in rutas],
          f"{c} {tabla}: partes en disco {en_disco} distintas de las de HUELLAS.csv")
    return pd.concat([pd.read_parquet(lee(r, f"almacen/{c}")) for r in rutas], ignore_index=True)


def datos_d() -> dict:
    d = pd.read_csv(lee("cifras_datos_2026-09-28/cifras.csv", "e1/D"), dtype={"valor": str})
    exige(d.clave.is_unique, "cifras_datos: claves repetidas")
    return dict(zip(d.clave, d.valor))


def dnum(dat: dict, k: str) -> float:
    exige(k in dat, f"cifras_datos: falta la clave {k}")
    v = float(dat[k])
    exige(math.isfinite(v), f"cifras_datos: {k} no finito")
    return v


# ── 7. El valor de un kWh ───────────────────────────────────────────────────
def tarifas_kwh(R: pd.DataFrame, D: pd.DataFrame, dat: dict) -> dict:
    """Tarifa por institución y mes (CU, Cv, Θ y las dos permutas) de los
    almacenes de E0 y P2, sus compuertas y las claves `kwh__*`. Devuelve la
    tabla mensual por institución y el comercializador de cada una."""
    AG = {}
    for c in ["E0", "P2"]:
        a = almacen(c, "agentes")
        exige(len(a) == 6144 * 5 and a.agente.nunique() == 5, f"{c}: agentes {len(a)} filas")
        finito(a[["techo", "piso", "autoconsumo", "sobrante", "faltante"]].to_numpy(), f"agentes {c}")
        n = a.groupby(["agente", "mes"])[["techo", "piso"]].nunique()
        exige(bool((n == 1).all().all()), f"{c}: techo o piso no constantes dentro de un mes")
        AG[c] = a
    m0 = AG["E0"].groupby(["agente", "mes"])[["techo", "piso"]].first().astype(float)
    m2 = AG["P2"].groupby(["agente", "mes"])[["techo", "piso"]].first().astype(float)
    exige(m0.index.equals(m2.index) and bool((m0.techo == m2.techo).all()), "E0 y P2 con techos distintos")
    T = pd.DataFrame({"CU": m0.techo, "C1": m0.piso, "C4": m2.piso})
    T["Cv"] = T.CU - T.C1
    T["Theta"] = T.C1 - T.C4
    exige(bool(((T.Cv > 0) & (T.Theta > 0)).all()), "Cv o Θ no positivos")
    ok("tarifa: techo y piso constantes en cada institución y mes en E0 y P2, mismos techos, Cv > 0 y Θ > 0")
    # horas de cada mes (pesos de la media)
    h0 = AG["E0"]
    horas = h0[h0.agente == h0.agente.iloc[0]].groupby("mes").size()
    exige(int(horas.sum()) == 6144 and len(horas) == 9, f"horas por mes {horas.to_dict()}")
    # dos comercializadores: instituciones con la misma serie mensual de CU
    grupos: dict = {}
    for ag, fila in T.CU.unstack("mes").iterrows():
        grupos.setdefault(tuple(np.round(fila.to_numpy(), 6)), []).append(ag)
    exige(len(grupos) == 2, f"{len(grupos)} series de CU distintas, no 2")
    VARS = ["CU", "Cv", "Theta", "C1", "C4"]
    COMP = {"CU": "CU_aplicado", "Cv": "Cvm", "Theta": "Theta"}
    com, media, mens = {}, {}, {}
    for insts in grupos.values():
        s = T.loc[insts[0], VARS]
        for ag in insts[1:]:
            exige(bool((T.loc[ag, VARS] - s).abs().max().max() <= 1e-9), f"{ag}: tarifa distinta de {insts[0]}")
        mu = s.mul(horas, axis=0).sum() / horas.sum()
        nombre = [n for n in ["ASC", "CEDENAR"] if abs(mu.CU - dnum(dat, f"tarifa_media__{n}__CU_aplicado")) <= 0.005 + 2e-4]
        exige(len(nombre) == 1, f"el CU medio {mu.CU:.4f} de {insts} no identifica un comercializador")
        n = nombre[0]
        exige(n not in com, f"dos grupos con el CU medio de {n}")
        com[n], media[n], mens[n] = sorted(insts), mu, s
        for v, k in COMP.items():
            esp = dnum(dat, f"tarifa_media__{n}__{k}")
            exige(abs(mu[v] - esp) <= 0.005 + 2e-4, f"{n}: media de {v} {mu[v]:.4f}, cifras_datos {esp}")
        for f, k in [("min", "cu_min"), ("max", "cu_max")]:
            esp = dnum(dat, f"{k}__{n}")
            exige(abs(getattr(s.CU, f)() - esp) <= 0.005 + 2e-4, f"{n}: CU {f} {getattr(s.CU, f)():.4f}, cifras_datos {esp}")
    exige(com.get("CEDENAR") == ["Cesmag"], f"CEDENAR = {com.get('CEDENAR')}, no solo Cesmag")
    for k, v in [("cu_cedenar_menos_asc", media["CEDENAR"].CU - media["ASC"].CU),
                 ("theta_cedenar_menos_asc", media["CEDENAR"].Theta - media["ASC"].Theta),
                 ("cv_razon_cedenar_asc", media["CEDENAR"].Cv / media["ASC"].Cv)]:
        exige(abs(v - dnum(dat, k)) <= 0.005 + 2e-4, f"{k}: {v:.4f}, cifras_datos {dnum(dat, k)}")
    ok("tarifa: dos comercializadores (CEDENAR solo Cesmag); medias ponderadas de CU, Cv y Θ, CU mínimo y máximo y "
       "las diferencias y la razón entre los dos, como cifras_datos (§14.17) a dos decimales")

    # compuertas de liquidación: C1 y C4 al peso donde nadie agota su crédito ni su parte
    for c in ["E0", "P2", "K1", "CV2", "SINU"]:
        a = AG[c] if c in AG else almacen(c, "agentes")
        a = a.astype({k: "float64" for k in ["autoconsumo", "sobrante", "faltante", "techo"]})
        e = almacen(c, "escenarios")
        finito(e.valor.to_numpy(), f"escenarios {c}")
        ev = e.astype({"valor": "float64"}).groupby(["escenario", "agente"]).valor.sum().unstack(0)
        nm = a.agente.nunique()
        kap = 2.0 if c == "CV2" else 1.0
        a["auto"] = a.autoconsumo * a.techo
        m = a.groupby(["agente", "mes"]).agg(auto=("auto", "sum"), s=("sobrante", "sum"), d=("faltante", "sum"))
        t = T.loc[m.index]
        num2 = c == "P2"
        m["perm_planta"] = t.CU - kap * t.Cv - (t.Theta if num2 else 0.0)
        m["perm_caso2"] = t.CU - kap * t.Cv - t.Theta
        fondo = m.groupby("mes").s.sum()
        m["parte"] = m.index.get_level_values("mes").map(fondo) / nm
        exige(bool((m.s <= m.d).all()) and bool((m.parte <= m.d).all()), f"{c}: alguien agota su crédito o su parte")
        c1 = (m.auto + m.s * m.perm_planta).groupby("agente").sum()
        c4 = (m.auto + m.parte * m.perm_caso2).groupby("agente").sum()
        for mec, calc in [("C1", c1), ("C4", c4)]:
            dif = (ev[mec] - calc).abs()
            tol = np.maximum(1.0, 1e-8 * ev[mec].abs())
            exige(bool((dif <= tol).all()), f"{c} {mec}: el almacén difiere de la cuenta en {dif.max():.3f} COP")
            exige(abs(ev[mec].sum() - R.loc[c, mec]) <= max(1.0, 1e-7 * abs(R.loc[c, "P2P"])),
                  f"{c} {mec}: el almacén no suma la hoja Resumen")
    ok("liquidación al peso (≤ 1 COP o 1e-8 por institución) en E0, P2, K1, CV2 y SINU: C1 = autoconsumo × CU + "
       "crédito × permuta del numeral de la planta, y C4 = autoconsumo × CU + (fondo / n) × permuta del caso 2 "
       "(CU − κ·Cv − Θ); el almacén suma la hoja Resumen")

    # anchos de par del almacén de flujos de E0
    fl = pd.read_parquet(lee(PREF_ALM.format("E0", "flujos") + "parte_0000.parquet", "almacen/E0"))
    fl = fl.astype({k: "float64" for k in ["kwh", "ahorro_comprador", "prima_vendedor", "techo_comprador", "piso_vendedor"]})
    finito(fl[["kwh", "ahorro_comprador", "prima_vendedor"]].to_numpy(), "flujos E0")
    fl["ancho"] = (fl.ahorro_comprador + fl.prima_vendedor) / fl.kwh
    tc = T.CU.reindex(pd.MultiIndex.from_arrays([fl.comprador, fl.mes])).to_numpy()
    pv = T.C1.reindex(pd.MultiIndex.from_arrays([fl.vendedor, fl.mes])).to_numpy()
    exige(float(np.abs(fl.ancho - (tc - pv)).max()) <= 1e-3, "flujos E0: el ancho de par no es CU del comprador − permuta del vendedor")
    energia, banda = float(fl.kwh.sum()), float((fl.ahorro_comprador + fl.prima_vendedor).sum())
    exige(abs(banda - D.loc["E0", "banda"]) <= 1.0, f"flujos E0: banda {banda:.2f}, descomposición {D.loc['E0', 'banda']:.2f}")
    t4 = tablas(seccion("## 4 ·"))[0]
    exige(abs(energia - num_es(t4.loc["E0", "Energía transada (kWh)"])) <= 0.005 + 1e-6, f"energía de E0 {energia}")
    ancho = banda / energia
    m = texto_canon("### 14.3 ·", r"ancho\s+efectivo,\s+el\s+excedente\s+del\s+mercado\s+por\s+kWh\s+transado,\s+de\s+([\d,]+)\s+a")
    exige(abs(ancho - num_es(m.group(1))) <= 0.005 + 1e-9, f"ancho efectivo de E0 {ancho:.4f}, CANON §14.3 {m.group(1)}")
    rep = fl[fl.mes == MES_REP]
    ok("flujos de E0: ancho de par = CU del comprador − permuta del vendedor (≤ 1e-3), banda = descomposición "
       "(≤ 1 COP), energía = CANON §4 y ancho efectivo = CANON §14.3")

    # claves
    FA = F_ALM.format("E0", "agentes")
    FUENTE = {"CU": FA + ", columna techo",
              "Cv": FA + ", techo − piso",
              "Theta": FA + ", piso, menos " + F_ALM.format("P2", "agentes") + ", piso",
              "C1": FA + ", piso (nadie agota el crédito en E0)",
              "C4": F_ALM.format("P2", "agentes") + ", piso (numeral 2, nadie agota el crédito en P2)"}
    DEF = {"CU": "costo unitario, techo del comprador y valor de un kWh vendido dentro para la comunidad (P2P con los dos supuestos)",
           "Cv": "componente de comercialización Cv que el art. 25 descuenta de la permuta; ahorro del intercambio por kWh entre dos miembros del mismo comercializador",
           "Theta": "cargos de red y de sistema Θ (T + D + PR + R), que descuenta el numeral 2 o el caso 2",
           "C1": "valor de un kWh acreditado en C1 con el numeral 1: permuta CU − Cv",
           "C4": "valor de un kWh acreditado en C4 (caso 2 del colectivo) o con el numeral 2: permuta CU − Cv − Θ"}
    for n in ["ASC", "CEDENAR"]:
        s, mu, insts = mens[n], media[n], ", ".join(com[n])
        r = s.loc[MES_REP]
        for v in VARS:
            pon(f"kwh__{n}__{MES_REP}__{v}", r[v], "COP/kWh", en(r[v], 2),
                f"{DEF[v]}; {n} ({insts}), {MES_REP}", FUENTE[v], "§14.17")
        if len(com[n]) >= 2:     # solo hay par dentro de ASC; Cesmag es el único cliente de CEDENAR
            pon(f"kwh__{n}__{MES_REP}__P2P_C4", r.CU - r.C4, "COP/kWh", en(r.CU - r.C4, 2),
                f"lo que un kWh vendido dentro entre dos miembros de {n} gana sobre C4: Cv + Θ (cargos evitados más ahorro del intercambio); {MES_REP}",
                FUENTE["CU"] + " menos " + FUENTE["C4"], "§14.17")
        for v in VARS:
            for f in ["min", "max"]:
                x = getattr(s[v], f)()
                mes = getattr(s[v], "idx" + f)()
                pon(f"kwh__{n}__{v}__{f}", x, "COP/kWh", en(x, 2),
                    f"{'mínimo' if f == 'min' else 'máximo'} mensual del horizonte ({mes}): {DEF[v]}; {n}",
                    FUENTE[v] + ", nueve meses", "§14.17")
            pon(f"kwh__{n}__{v}__media", mu[v], "COP/kWh", en(mu[v], 2),
                f"media del horizonte ponderada por horas: {DEF[v]}; {n}",
                FUENTE[v] + ", media de las 6 144 horas", "§14.17")
    A, C = mens["ASC"].loc[MES_REP], mens["CEDENAR"].loc[MES_REP]
    for clave, v, dfn in [
            ("kwh__" + MES_REP + "__ancho_CEDENAR_compra_ASC", C.CU - A.C1,
             "ahorro del intercambio por kWh cuando Cesmag (CEDENAR) compra a un miembro de ASC: Cv_ASC + (CU_CEDENAR − CU_ASC)"),
            ("kwh__" + MES_REP + "__ancho_CEDENAR_vende_ASC", A.CU - C.C1,
             "ahorro del intercambio por kWh cuando Cesmag (CEDENAR) vende a un miembro de ASC: Cv_CEDENAR + (CU_ASC − CU_CEDENAR)")]:
        obs = rep[(rep.comprador == "Cesmag") if "compra" in clave else (rep.vendedor == "Cesmag")].ancho
        exige(len(obs) > 0 and float((obs - v).abs().max()) <= 1e-3, f"{clave}: el almacén de flujos no lo reproduce")
        pon(clave, v, "COP/kWh", en(v, 2), dfn + f", {MES_REP}",
            F_ALM.format("E0", "agentes") + ", techo y piso; contrastado con " + F_ALM.format("E0", "flujos"), "§14.17")
    ok(f"flujos de E0 en {MES_REP}: los anchos de Cesmag comprador y vendedor reproducen los de la tarifa")
    sig = 2.0 / 3.0
    pon("kwh__" + MES_REP + "__juguete_prima", sig * A.Cv, "COP/kWh", en(sig * A.Cv, 2),
        "ejemplo de juguete del presupuesto (5.6): σ = 2/3 (tres compradores) por la banda Cv de ASC; lo que el vendedor cobra sobre su piso",
        FUENTE["Cv"] + ", por 2/3", "§14.20")
    pon("kwh__" + MES_REP + "__juguete_precio", A.C1 + sig * A.Cv, "COP/kWh", en(A.C1 + sig * A.Cv, 2),
        "ejemplo de juguete del presupuesto (5.6): piso del juego (permuta del numeral 1 de ASC) más σ = 2/3 de la banda Cv",
        FUENTE["C1"] + " más 2/3 de Cv", "§14.20")
    bm = dnum(dat, "bolsa_media_topada")
    pon("bolsa_media_topada", bm, "COP/kWh", en(bm, 2), "media de la bolsa del horizonte con el techo PES",
        F_DAT + "bolsa_media_topada", "§14.17")
    ra = media["ASC"].C1 / bm
    exige(round(ra, 1) == 3.8, f"permuta del numeral 1 de ASC sobre la bolsa media {ra:.3f}")
    pon("kwh__ASC__C1_sobre_bolsa", ra, "veces", en(ra, 1),
        "permuta media del numeral 1 de ASC sobre la bolsa media topada del horizonte",
        "kwh__ASC__C1__media / bolsa_media_topada", "§14.20")
    pon("e0__energia_transada", energia, "kWh", en(energia, 2), "energía transada en el mercado en E0",
        F_ALM.format("E0", "flujos") + ", suma de kwh", "§4")
    pon("e0__ancho_efectivo", ancho, "COP/kWh", en(ancho, 2),
        "ancho efectivo de E0: banda (ahorro del intercambio) por kWh transado",
        F_ALM.format("E0", "flujos") + ", (ahorro_comprador + prima_vendedor) / kwh", "§14.3")
    return {"T": T, "com": com}


# ── 8. Los atributos de los 13 casos ────────────────────────────────────────
def atributos(R: pd.DataFrame, dat: dict, tar: dict) -> None:
    T = tar["T"]
    cap_base = num_es(texto_canon("### 14.11 ·", r"P1\s+\(demanda\s+÷\s+7,\s+plantas\s+de\s+([\d,]+)\s+kW\)").group(1))
    exige(cap_base == 17.55, f"capacidad de E0 {cap_base}")
    cu = pd.read_csv(lee("contrafacticos_art18_2026-09-27/capacidad_por_usuario.csv", "e1/A1")).set_index("caso")
    exige(sorted(cu.index) == sorted(CASOS), "capacidad_por_usuario: casos")
    cf = pd.read_csv(lee("contrafacticos_art18_2026-09-27/contrafacticos_13casos.csv", "e1/A1"))
    t1 = [t for t in tablas(seccion("## 1 ·")) if t.index.name == "Caso"]
    exige(len(t1) == 1 and list(t1[0].index) == CASOS, "CANON §1: tabla de opciones")
    opc = {c: t1[0].loc[c, "Opción"].strip("`") for c in CASOS}
    a0 = almacen("E0", "agentes")
    orden = list(dict.fromkeys(a0.agente))
    g0 = a0.astype({"generacion": "float64"}).groupby("agente").generacion.sum()
    d0 = a0.astype({"demanda": "float64"}).groupby("agente").demanda.sum()
    A = {}
    for c in CASOS:
        a = a0 if c == "E0" else almacen(c, "agentes")
        finito(a[["generacion", "demanda", "sobrante", "faltante", "piso", "techo"]].to_numpy(), f"agentes {c}")
        ags = list(dict.fromkeys(a.agente))
        exige(len(a) == 6144 * len(ags), f"{c}: {len(a)} filas de agentes")
        a = a.astype({k: "float64" for k in ["generacion", "demanda", "sobrante", "faltante", "piso", "techo"]})
        g, d = a.groupby("agente").generacion.sum(), a.groupby("agente").demanda.sum()
        fg, fd = (g / g0.reindex(g.index)), (d / d0.reindex(d.index))
        # la opción de CANON §1
        o = opc[c]
        esp_g = {k: 1.0 for k in ags}
        esp_d = 1.0
        neto = []
        kap = 1.0
        if o == "(ninguna)":
            pass
        else:
            for m in re.finditer(r"--([\w-]+)(?:\s+([^\s-][^\s]*))?", o):
                k, v = m.group(1), m.group(2)
                if k == "factor-generacion":
                    esp_g = {x: float(v) for x in ags}
                elif k == "factor-demanda":
                    num, _, den = v.partition("/")
                    esp_d = float(num) / float(den or 1)
                elif k == "escala-agente":
                    exige(v.endswith(":neto_cero"), f"{c}: opción {o}")
                    neto = [v.split(":")[0]]
                elif k == "neto-cero":
                    neto = list(ags)
                elif k == "factor-cv":
                    kap = float(v)
                elif k == "excluir-agente":
                    exige(v not in ags and sorted(ags + [v]) == sorted(orden), f"{c}: excluye {v}, agentes {ags}")
                else:
                    exige(False, f"{c}: opción desconocida {k} en CANON §1")
        for x in ags:
            if x in neto:
                exige(abs(g[x] / d[x] - 1) <= 1e-5, f"{c} {x}: generación {g[x]:.3f} y demanda {d[x]:.3f} no se igualan (neto cero)")
            else:
                exige(abs(fg[x] / esp_g[x] - 1) <= 1e-5, f"{c} {x}: factor de generación {fg[x]:.6f}, opción {o}")
        exige(bool(((fd / esp_d - 1).abs() <= 1e-5).all()), f"{c}: factor de demanda {fd.to_dict()}, opción {o}")
        cap = cap_base * fg
        # capacidad: capacidad_por_usuario.csv (e1/A1) y cifras_datos
        lista = [float(x) for x in str(cu.loc[c, "cap_kw"]).split(";")]
        exige(len(lista) == len(ags), f"{c}: {len(lista)} capacidades")
        for x, v in zip(ags, lista):
            exige(abs(v - cap[x]) <= 1e-3, f"{c} {x}: capacidad {v} (A1) frente a {cap[x]:.4f} (almacén)")
            exige(abs(v - dnum(dat, f"capacidad_kW__{c}__{x}")) <= 0.005 + 1e-6, f"{c} {x}: capacidad frente a cifras_datos")
        suma, capu = float(cu.loc[c, "suma_kw"]), float(cu.loc[c, "capu_N_kw"])
        exige(abs(suma - sum(lista)) <= 1e-3 and abs(capu - suma / len(ags)) <= 1e-5, f"{c}: suma {suma} o capacidad por usuario {capu}")
        exige(abs(suma - dnum(dat, f"capacidad_suma_kW__{c}")) <= 0.005 + 1e-6, f"{c}: suma frente a cifras_datos")
        exige(suma < 1000.0, f"{c}: la suma {suma} kW llega a 1 MW")
        # numeral por planta: regla de los 100 kW, contrastada con el piso de la primera hora de cada mes
        numeral = {x: (2 if v > UMBRAL_NUMERAL_KW else 1) for x, v in zip(ags, lista)}
        p1 = a.groupby(["agente", "mes"]).piso.first()
        t = T.loc[p1.index]
        for x in ags:
            perm = (t.CU - kap * t.Cv - (t.Theta if numeral[x] == 2 else 0.0)).loc[x]
            exige(float((p1.loc[x] - perm).abs().max()) <= 1e-3,
                  f"{c} {x}: el piso del almacén no es la permuta del numeral {numeral[x]} (κ = {kap:g})")
        # pares que agotan el crédito
        pm = a.groupby(["agente", "mes"])[["sobrante", "faltante"]].sum()
        agotan, total = int((pm.sobrante > pm.faltante).sum()), len(pm)
        exige(agotan == int(dnum(dat, f"pares_agotan_credito__{c}")) and total == int(dnum(dat, f"pares_total__{c}")),
              f"{c}: {agotan} de {total} pares agotan el crédito, cifras_datos dice otra cosa")
        # participación del reparto igual y caso del art. 20
        part = 100.0 / len(ags)
        caso = 1 if (part < UMBRAL_PARTICIPACION and capu <= UMBRAL_NUMERAL_KW) else 2
        otros = cf[(cf.caso == c) & ~cf.contrafactico.str.contains("11_fronteras")]
        exige(len(otros) == 3 and bool((otros.caso_art20 == 2).all()), f"{c}: los contrafácticos de 5 fronteras no están en el caso 2")
        exige(caso == 2, f"{c}: caso {caso} del art. 20")
        A[c] = dict(cap_min=min(lista), cap_max=max(lista), suma=suma, capu=capu, fg_min=float(fg.min()), fg_max=float(fg.max()),
                    fd=float(fd.iloc[0]), num_min=min(numeral.values()), num_max=max(numeral.values()),
                    n_num2=sum(v == 2 for v in numeral.values()), num2=[x for x in ags if numeral[x] == 2],
                    n=len(ags), part=part, caso=caso, agotan=agotan, total=total)
    ok("casos: factores de generación y demanda del almacén como la opción de CANON §1 (neto cero donde se pide; ≤ 1e-5)")
    ok("casos: capacidad por planta, suma y por usuario de capacidad_por_usuario.csv (e1/A1) = almacén (17,55 kW por el "
       "factor, CANON §14.11) = cifras_datos; ninguna suma llega a 1 MW")
    ok("casos: el numeral de cada planta por la regla de los 100 kW coincide con el piso del almacén en la primera hora de "
       "cada mes (permuta del numeral 1 o 2, con κ = 2 en CV2), en las 64 plantas")
    ok("casos: pares que agotan el crédito recalculados del almacén = cifras_datos; participación 1/n ≥ 20 % y caso 2 del "
       "art. 20 en los 13, como los contrafácticos de cinco fronteras de contrafacticos_13casos.csv")
    FC = "contrafacticos_art18_2026-09-27/capacidad_por_usuario.csv, "
    for c in CASOS:
        x = A[c]
        FAc = F_ALM.format(c, "agentes")
        for k, v, u, t, dfn, f, s in [
                ("cap_min_kW", x["cap_min"], "kW", en(x["cap_min"], 2), "menor capacidad por planta", FC + "cap_kw, mínimo", "§14.17"),
                ("cap_max_kW", x["cap_max"], "kW", en(x["cap_max"], 2), "mayor capacidad por planta", FC + "cap_kw, máximo", "§14.17"),
                ("cap_suma_kW", x["suma"], "kW", en(x["suma"], 2), "suma de las capacidades de las plantas", FC + "suma_kw", "§14.17"),
                ("capu_kW", x["capu"], "kW", en(x["capu"], 2), "capacidad por usuario del colectivo (art. 18: suma entre fronteras)",
                 FC + "capu_N_kw", "§14.2"),
                ("f_gen_min", x["fg_min"], "factor", en_factor(x["fg_min"]), "menor factor de generación frente a E0",
                 FAc + ", generación sobre la de E0", "§1"),
                ("f_gen_max", x["fg_max"], "factor", en_factor(x["fg_max"]), "mayor factor de generación frente a E0",
                 FAc + ", generación sobre la de E0", "§1"),
                ("f_dem", x["fd"], "factor", en_factor(x["fd"]), "factor de demanda frente a E0 (el mismo en todas)",
                 FAc + ", demanda sobre la de E0", "§1"),
                ("numeral_min", x["num_min"], "numeral", en_int(x["num_min"]), "menor numeral del art. 25 de las plantas",
                 FC + "cap_kw, regla de los 100 kW; contrastado con el piso de " + FAc, "§14.11"),
                ("numeral_max", x["num_max"], "numeral", en_int(x["num_max"]), "mayor numeral del art. 25 de las plantas",
                 FC + "cap_kw, regla de los 100 kW; contrastado con el piso de " + FAc, "§14.11"),
                ("n_plantas_numeral2", x["n_num2"], "plantas", en_int(x["n_num2"]), "plantas en el numeral 2 (más de 100 kW)",
                 FC + "cap_kw, regla de los 100 kW", "§14.11"),
                ("n_miembros", x["n"], "miembros", en_int(x["n"]), "miembros de la comunidad", FAc + ", agentes", "§1"),
                ("part_min_pct", x["part"], "%", en_int(round(x["part"]), " %"),
                 "participación de cada miembro en el reparto igual del art. 19 (1/n); el art. 20 exige menos del 10 % para el caso 1",
                 FAc + ", 1 / número de agentes; contrastado con la liquidación de C4 (bloque 7)", "§14.2"),
                ("caso_art20", x["caso"], "caso", en_int(x["caso"]), "caso del art. 20 del colectivo (C4 y mercado por el colectivo)",
                 "regla del art. 20 sobre part_min_pct y capu_kW; contrafacticos_13casos.csv (e1/A1)", "§14.2"),
                ("pares_agotan", x["agotan"], "pares", en_int(x["agotan"]), "pares institución-mes que agotan el crédito (inyección del mes mayor que su importación)",
                 FAc + ", sobrante y faltante por mes; = " + F_DAT + f"pares_agotan_credito__{c}", "§14.17"),
                ("pares_total", x["total"], "pares", en_int(x["total"]), "pares institución-mes", FAc + f"; = {F_DAT}pares_total__{c}", "§14.17"),
                ("agota_credito", int(x["agotan"] > 0), "indicador",en_int(int(x["agotan"] > 0)), "1 si algún miembro agota el crédito en algún mes",
                 FAc + ", pares_agotan > 0", "§14.17")]:
            pon(f"caso__{c}__{k}", v, u, t, f"{dfn}, caso {c}", f, s)
        if 0 < x["n_num2"] < x["n"]:
            pon(f"caso__{c}__plantas_numeral2", ", ".join(x["num2"]), "instituciones", ", ".join(x["num2"]),
                f"instituciones con la planta en el numeral 2, caso {c}", FC + "cap_kw, regla de los 100 kW", "§14.11")
    todas2 = [c for c in CASOS if A[c]["num_min"] == 2]
    alguna2 = [c for c in CASOS if A[c]["num_min"] == 1 and A[c]["num_max"] == 2]
    agot = [c for c in CASOS if A[c]["agotan"] > 0]
    sin = [c for c in CASOS if A[c]["agotan"] == 0]
    exige(todas2 == ["E4", "E5", "P2"] and alguna2 == ["I1", "N1"], f"numeral 2: todas {todas2}, alguna {alguna2}")
    exige(sin == ["E0", "P2", "K1", "CV2", "SINU"], f"casos sin crédito agotado {sin}")
    ok("casos: numeral 2 en todas las plantas de E4, E5 y P2 y solo en la UCC de I1 y N1; crédito sin agotar en E0, P2, K1, CV2 y SINU")
    FT = "atributos de los 13 casos (claves caso__<caso>__*)"
    for k, v, u, t, dfn, s in [
            ("casos_numeral2_todas", ", ".join(todas2), "casos", ", ".join(todas2), "casos con todas las plantas en el numeral 2", "§14.11"),
            ("casos_numeral2_alguna", ", ".join(alguna2), "casos", ", ".join(alguna2), "casos con plantas en los dos numerales", "§14.11"),
            ("casos_agotan_credito", ", ".join(agot), "casos", ", ".join(agot), "casos en que algún miembro agota el crédito", "§14.17"),
            ("casos_sin_agotar_credito", ", ".join(sin), "casos", ", ".join(sin), "casos en que ningún miembro agota el crédito", "§14.17"),
            ("n_casos_sin_agotar_credito", len(sin), "casos", en_int(len(sin)), "casos en que ningún miembro agota el crédito", "§14.17"),
            ("cap_min_13", min(A[c]["cap_min"] for c in CASOS), "kW", en(min(A[c]["cap_min"] for c in CASOS), 2),
             "menor capacidad por planta en los 13 casos", "§14.17"),
            ("cap_max_13", max(A[c]["cap_max"] for c in CASOS), "kW", en(max(A[c]["cap_max"] for c in CASOS), 2),
             "mayor capacidad por planta en los 13 casos", "§14.17"),
            ("cap_suma_max_13", max(A[c]["suma"] for c in CASOS), "kW", en(max(A[c]["suma"] for c in CASOS), 2),
             "mayor suma de capacidades en los 13 casos (" + max(CASOS, key=lambda c: A[c]["suma"]) + ")", "§14.17"),
            ("part_min_13", min(A[c]["part"] for c in CASOS), "%", en_int(round(min(A[c]["part"] for c in CASOS)), " %"),
             "menor participación de un miembro en el reparto igual, en los 13 casos (toda participación pasa del 10 %)", "§14.2"),
            ("n_casos_caso2", sum(A[c]["caso"] == 2 for c in CASOS), "casos", en_int(sum(A[c]["caso"] == 2 for c in CASOS)),
             "casos con el colectivo en el caso 2 del art. 20", "§14.2")]:
        pon(f"casos__{k}", v, u, t, dfn, FT, s)


# ── 9. Los siete mecanismos ─────────────────────────────────────────────────
def mecanismos(R: pd.DataFrame) -> None:
    t6 = tablas(seccion("## 6 ·"))[0]
    for c in CASOS:
        for mec in ["C2", "C3"]:
            v = R.loc[c, mec] / M
            exige(abs(v - num_es(t6.loc[c, mec])) <= 0.005 + 1e-9, f"{c} {mec}: {v:.6f} no redondea a CANON §6")
            pon(f"com__{c}__{mec}", v, "MCOP", en(v, 2), f"beneficio neto de la comunidad con {mec}, caso {c}",
                F_RES.format(c), "§6")
    ok("C2 y C3 de la hoja Resumen como CANON §6 a dos decimales en los 13 casos")
    mecs = [m for m in R.columns if m != "C4_mensual"]
    exige(sorted(mecs) == sorted(["P2P", "P2P_colectivo", "C1", "C2", "C3", "C4", "C5"]), f"mecanismos {mecs}")
    exige(not any("C4_mensual" in f["clave"] or "C4m" in f["clave"] for f in FILAS), "una clave emite C4 mensual")
    r = R.loc["E0", [m for m in mecs if m != "C2"]].sort_values(ascending=False)
    rot = {"P2P": "P2P = C2", "P2P_colectivo": "P2P colectivo"}
    orden = " > ".join(rot.get(m, m) for m in r.index)
    exige(orden == "P2P = C2 > C1 > C4 > P2P colectivo > C5 > C3", f"orden de E0: {orden}")
    ok("siete mecanismos (C4 mensual es alias de C4 y no se emite); orden de E0: " + orden)
    pon("mec__n", len(mecs), "mecanismos", en_int(len(mecs)), "mecanismos liquidados en cada corrida (sin C4 mensual, alias de C4)",
        F_RES.format("<caso>") + ", filas", "§6")
    pon("mec__n_resultados", len(mecs) * len(CASOS), "resultados", en_int(len(mecs) * len(CASOS)),
        "resultados de comunidad: 13 casos por siete mecanismos", F_RES.format("<caso>") + ", filas", "§6")
    pon("mec__E0__orden", orden, "orden", orden, "orden de los mecanismos en E0 por beneficio neto", F_RES.format("E0"), "§6")


# ── 10. El diseño del GSA ───────────────────────────────────────────────────
def gsa_diseno() -> None:
    s1 = seccion("### 13.1 ·")
    t = [x for x in tablas(s1) if x.index.name == "Caso"]
    exige(len(t) == 1, "CANON §13.1: tabla de n_base")
    t = t[0]
    tab = {}
    for grupo, fila in t.iterrows():
        for c in [x.strip() for x in grupo.split(",")]:
            tab[c] = (int(num_es(fila["n_base"])), int(num_es(fila["Evaluaciones (14 × n)"])))
    exige(sorted(tab) == sorted(CASOS_GSA), f"CANON §13.1: casos {sorted(tab)}")
    t2 = [x for x in tablas(seccion("### 13.2 ·")) if x.index.name == "Entrada"][0]
    sop_canon = {}
    for f in FACTORES:
        m = re.fullmatch(r"\[([\d,]+); ([\d,]+)\]", t2.loc[f"`{f}`", "Soporte"])
        exige(m is not None, f"CANON §13.2: soporte de {f}")
        sop_canon[f] = (num_es(m.group(1)), num_es(m.group(2)))
    n_por = {f["clave"].split("__")[1]: f["valor"] for f in FILAS if re.fullmatch(r"gsa__\w+__n", f["clave"])}
    total, soportes = 0, None
    for c in CASOS_GSA:
        n = int(n_por[c])
        base = f"SALIDAS_SERVIDOR/gsa_directo/{c}/muestras_{c}_n{n}_s42"
        meta = json.loads(lee(base + ".meta.json", f"gsa/{c}").read_text(encoding="utf-8"))
        exige(meta["caso"] == c and int(meta["n_base"]) == n and meta["entradas"] == FACTORES, f"{c}: meta.json")
        B, Mm = int(meta["B"]), int(meta["M"])
        exige(B == 2 * len(FACTORES) + 2 and Mm == B * n and bool(meta["segundo_orden"]), f"{c}: B = {B}, M = {Mm}")
        mu = pd.read_csv(lee(base + ".csv", f"gsa/{c}"), usecols=["idx", "motivo"], dtype={"motivo": str})
        exige(len(mu) == Mm and mu.idx.is_unique, f"{c}: {len(mu)} filas en la muestra, M = {Mm}")
        exige(bool(mu.motivo.isna().all()), f"{c}: {int(mu.motivo.notna().sum())} evaluaciones con motivo (fallidas)")
        exige(tab[c] == (n, Mm), f"{c}: n = {n}, M = {Mm}, CANON §13.1 dice {tab[c]}")
        sop = {f: tuple(float(x) for x in s) for f, s in zip(meta["entradas"], meta["soportes"])}
        exige(soportes is None or sop == soportes, f"{c}: soportes distintos de los de {CASOS_GSA[0]}")
        soportes = sop
        total += Mm
        pon(f"gsa__{c}__evals", Mm, "corridas", en_int(Mm),
            f"evaluaciones del modelo (corridas completas de las 6 144 h con los siete mecanismos), 14 × n, caso {c}",
            f"entrega_gsa_directo_completo_2026-09-27/{base}.meta.json, M; = filas de {base.rsplit('/', 1)[1]}.csv", "§13.1")
    exige(soportes == sop_canon, f"soportes {soportes}, CANON §13.2 {sop_canon}")
    m = texto_canon("### 14.10 ·", r"Lee\s+las\s+(\d{1,3}(?:[\s  ]\d{3})*)\s+evaluaciones")
    exige(total == int(num_es(m.group(1))), f"evaluaciones totales {total}, CANON §14.10 {m.group(1)}")
    ok(f"GSA: M = 14 n = filas de la muestra, sin evaluaciones fallidas, en los 12 casos (CANON §13.1); {total} en total "
       "(CANON §14.10); los seis soportes iguales en los 12 .meta.json y en CANON §13.2")
    FM = "gsa_directo/<caso>/muestras_<caso>_n<n>_s42.meta.json"
    pon("gsa__B", 14, "evaluaciones por punto base", en_int(14), "evaluaciones por punto base con segundo orden: 2 × 6 + 2",
        FM + ", B", "§13.1")
    pon("gsa__evals_total", total, "corridas", en_int(total), "evaluaciones del GSA en los 12 casos", FM + ", suma de M", "§14.10")
    pon("gsa__n_factores", len(FACTORES), "factores", en_int(len(FACTORES)), "factores (entradas) de la caja", FM + ", entradas", "§13.2")
    for n_ in [2048, 512]:
        cs = [c for c in CASOS_GSA if int(n_por[c]) == n_]
        pon(f"gsa__n_casos_n{n_}", len(cs), "casos", en_int(len(cs)), f"casos del Sobol con n = {n_} ({', '.join(cs)})",
            FM + ", n_base", "§13.1")
        cota = 100 * 3 / (2 * n_)
        pon(f"gsa__cota_cero_n{n_}", cota, "%", en(cota, 2, " %"),
            f"cota superior aproximada al 95 % de una P(inversión) nula en las 2n = {2 * n_} filas A y B, por la regla del tres (3 / 2n); "
            "cuenta de libro que trata las filas como independientes, no cifra del canon",
            f"3 / (2 × {n_})", "§13.2")
    for f in FACTORES:
        lo, hi = soportes[f]
        for lado, v in [("lo", lo), ("hi", hi)]:
            pon(f"gsa__factor__{f}__{lado}", v, "factor", f"{v:.2f}".rstrip("0").rstrip("."),
                f"{'límite inferior' if lado == 'lo' else 'límite superior'} del soporte uniforme de {f}", FM + ", soportes", "§13.2")


# ── 11. Otras cifras derivadas ──────────────────────────────────────────────
def otras(R: pd.DataFrame, D: pd.DataFrame, c7: dict) -> None:
    h = pd.read_parquet(lee(PREF_ALM.format("E0", "horas") + "parte_0000.parquet", "almacen/E0"))
    sin = int((h.motivo == "sin mercado esa hora").sum())
    con = int(h.regimen.isin(REGIMENES_MERCADO).sum())
    sat = int((h.regimen == "suma_no_cabe").sum())
    exige(sin + con == 6144, f"E0: {sin} horas sin mercado y {con} con mercado")
    t = tablas(seccion("## 4 ·"))[2]
    exige(sin == int(num_es(t.loc["E0", "sin ids"])) and sat == int(num_es(t.loc["E0", "suma_no_cabe"])),
          f"E0: {sin} sin mercado y {sat} de saturación, CANON §4 dice otra cosa")
    ok(f"E0: {sin} horas sin mercado, {con} con mercado y {sat} de saturación (suma_no_cabe), como CANON §4")
    FH = F_ALM.format("E0", "horas")
    pon("e0__horas_sin_mercado", sin, "h", en_int(sin), "horas de E0 sin vendedores o sin compradores", FH + ", motivo", "§4")
    pon("e0__horas_con_mercado", con, "h", en_int(con), "horas de E0 con mercado", FH + ", regimen", "§4")
    pon("e0__horas_saturacion", sat, "h", en_int(sat), "horas de E0 resueltas por la regla de saturación declarada (suma_no_cabe)",
        FH + ", regimen = suma_no_cabe", "§4")
    u = pd.read_csv(lee("umbral_100kw_2026-09-27/umbral_100kw.csv", "e1/C8")).set_index("mecanismo")
    m = texto_canon("### 14.11 ·", r"\|\s*P2P\s*\|[^\n]*\(([−\d,]+)\s*%\)\s*\|\n\|\s*C1\s*\|[^\n]*\(([−\d,]+)\s*%\)")
    for mec, esp in [("P2P", num_es(m.group(1))), ("C1", num_es(m.group(2)))]:
        f = u.loc[mec]
        exige(abs(f.E4 - R.loc["E4", mec]) <= 1e-3 and abs(f.P1_por_7 - 7 * R.loc["P1", mec]) <= 1e-3,
              f"umbral {mec}: E4 o 7 × P1 distintos de Resumen")
        exige(abs(float(f.efecto_pct) - esp) <= 0.05 + 1e-9, f"umbral {mec}: {f.efecto_pct:.3f} %, CANON §14.11 {esp}")
        pon(f"umbral100__{mec}_pct", float(f.efecto_pct), "%", en(float(f.efecto_pct), 2, " %"),
            f"efecto del umbral de 100 kW sobre {mec}: (E4 − 7 × P1) / (7 × P1)",
            "umbral_100kw_2026-09-27/umbral_100kw.csv, columna efecto_pct", "§14.11")
    ok("umbral de 100 kW: E4 y 7 × P1 de umbral_100kw.csv = Resumen, y −14,2 % (P2P) y −14,9 % (C1) como CANON §14.11")
    t4 = tablas(seccion("## 4 ·"))[0]
    re_e = num_es(t4.loc["P2", "Energía transada (kWh)"]) / num_es(t4.loc["E0", "Energía transada (kWh)"])
    re_b = D.loc["P2", "banda"] / D.loc["E0", "banda"]
    ve, vb = c7["comunidad__P2_sobre_E0_energia"], c7["comunidad__P2_sobre_E0_banda"]
    # cifras_cap07 hizo los cocientes sobre las cifras redondeadas del canon (36,01); aquí se
    # recalcula la banda al peso de la descomposición (36,05) y se exige el mismo entero.
    exige(abs(ve - re_e) <= 1e-3 and round(vb) == round(re_b) == 36 and round(re_e) == 7,
          f"P2 sobre E0: {ve}, {vb} (cifras_cap07) frente a {re_e}, {re_b}")
    ok("P2 sobre E0: energía 7 veces (CANON §4) y banda 36 veces (descomposición al peso), el mismo entero que cifras_cap07")
    pon("p2_sobre_e0__energia", re_e, "veces", en_int(round(re_e)), "energía transada de P2 sobre la de E0",
        "CANON §4, tabla de los trece casos, cociente; = cifras_cap07 comunidad__P2_sobre_E0_energia", "§4")
    pon("p2_sobre_e0__banda", re_b, "veces", en_int(round(re_b)), "banda (ahorro del intercambio) de P2 sobre la de E0",
        "descomposicion_p2p_2026-09-27/descomposicion_13casos.csv, fila comunidad, columna banda, cociente", "§14.8")


def main() -> int:
    c7p = lee("cifras_cap07_2026-09-28/cifras.csv", "e1/R")
    c7d = pd.read_csv(c7p, dtype={"valor": str})
    exige(c7d.clave.is_unique, "cifras_cap07: claves repetidas")
    c7 = {}
    de_texto = set()
    for k, v in zip(c7d.clave, c7d.valor):
        if k in CLAVES_TEXTO_CAP07:
            de_texto.add(k)             # listas y rótulos; no se usan como número
            continue
        try:
            c7[k] = float(v)
        except (TypeError, ValueError):
            raise SystemExit(f"[cifras_articulo] COMPUERTA FALLIDA: cifras_cap07: la clave {k} tiene "
                             f"valor no numérico {v!r} y no está en CLAVES_TEXTO_CAP07") from None
        exige(math.isfinite(c7[k]), f"cifras_cap07: la clave {k} tiene valor no finito {v!r}")
    exige(de_texto == CLAVES_TEXTO_CAP07,
          f"cifras_cap07: faltan claves de texto esperadas {sorted(CLAVES_TEXTO_CAP07 - de_texto)}")
    print("[cifras_articulo] 1. hoja Resumen de los 13 casos")
    R = resumen()
    print("[cifras_articulo] 2. descomposición (§14.8)")
    D = descomposicion(R)
    print("[cifras_articulo] 3. la comunidad caso a caso")
    comunidad(R, c7, D)
    print("[cifras_articulo] 4. resúmenes")
    resumenes(R, c7)
    print("[cifras_articulo] 5. GSA directo (§13.3)")
    gsa()
    print("[cifras_articulo] 6. E4 y constantes publicables")
    e4(c7)
    constantes(c7)
    n29 = len(FILAS)
    exige(n29 == 482, f"el bloque del 29 da {n29} cifras, no 482")
    print("[cifras_articulo] 7. el valor de un kWh (añadido el 2026-09-30)")
    dat = datos_d()
    tar = tarifas_kwh(R, D, dat)
    print("[cifras_articulo] 8. atributos de los 13 casos")
    atributos(R, dat, tar)
    print("[cifras_articulo] 9. los siete mecanismos")
    mecanismos(R)
    print("[cifras_articulo] 10. diseño del GSA")
    gsa_diseno()
    print("[cifras_articulo] 11. otras cifras derivadas")
    otras(R, D, c7)
    print(f"[cifras_articulo] {len(FILAS) - n29} cifras nuevas")
    SALIDA.mkdir(parents=True, exist_ok=True)
    out = pd.DataFrame(FILAS, columns=["clave", "valor", "unidad", "texto_en", "definicion", "fuente", "seccion_canon"])
    exige(out.clave.is_unique, "claves repetidas en la salida")
    out.to_csv(SALIDA / "cifras.csv", index=False, encoding="utf-8", lineterminator="\n")
    guion = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    sucio = git("status", "--short", "--untracked-files=all", "--", guion)
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("cifras_articulo.py: tabla de cifras del artículo IEEE LatAm (canon 2026-09)\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n" + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + guion + "\n")
        fh.write("CANON.md leído como texto (compuertas y constantes de §1, §4, §6, §9, §10.1, §13.1, §13.2, §13.3, §14.3, §14.7, "
                 "§14.8, §14.10, §14.11, §14.16, §14.18); "
                 f"sha256 {hashlib.sha256(CANON_MD.read_bytes()).hexdigest()}\n")
        fh.write(f"huellas: {HUELLAS.relative_to(RAIZ).as_posix()}; {len(LEIDOS)} artefactos leídos, todos con la huella comprobada:\n")
        for g, r in LEIDOS:
            fh.write(f"  {g}  {r}\n")
        fh.write(f"compuertas: {len(COMPUERTAS)}, todas OK:\n")
        for cpt in COMPUERTAS:
            fh.write(f"  OK  {cpt}\n")
        fh.write(f"cifras: {len(out)}\n")
    print(f"[cifras_articulo] corrida del {_dt.datetime.now().isoformat(timespec='seconds')} (la fecha no va a procedencia.txt)")
    print(f"[cifras_articulo] {len(out)} cifras de {len(LEIDOS)} artefactos y {len(COMPUERTAS)} compuertas en {SALIDA / 'cifras.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
