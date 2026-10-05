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

Añadido el 2026-09-30 (Tarea B1b), también al final, de modo que las 818
filas anteriores salen iguales byte a byte:

12. La atribución de P2P − C4 a los dos supuestos de liquidación (`atr__*`,
    CANON §14.21), de `atribucion_supuestos_2026-09-30/atribucion_13casos.csv`
    (grupo `e1/S`): por caso, los dos órdenes de la identidad (texto: C4 → C1
    → P2P; inverso: C4 → v01 → P2P), Shapley, la interacción, sus partes de
    P2P − C4, la parte transada de la inyección, si C1 es la esquina exacta
    de «solo el supuesto 1» y el grupo (s1, s2 u «orden»); los resúmenes de
    los tres grupos; la inyección de E0; y el reparto por orden del kWh de
    ASC de abril (Cv + Θ). Compuertas: P2P, C1, C4 y P2P colectivo = Resumen;
    el orden del texto = (C1 − C4, P2P − C1); los dos órdenes y Shapley
    cierran; la tabla de CANON §14.21 a tres decimales; los tres grupos de
    §14.21; la energía de E0 = almacén; Cv + Θ = kwh__ASC__P2P_C4.

Añadido el 2026-10-02 (C2 como PPA), también al final, de modo que las 1 051
filas anteriores salen iguales byte a byte:

13. El C2 de la propuesta como PPA de todo el excedente (CANON §14.22), de
    `c2_ppa_2026-10-02/c2_ppa_13casos.csv` (grupo `e1/P`): por caso, el valor
    de la comunidad con el PPA a la media de XM (`com__<caso>__C2ppa`), sus
    brechas con C1, C4, P2P, P2P colectivo y C3 (`com__<caso>__C2ppa_<X>`),
    los precios de equilibrio (`ppa__<caso>__PPeq_<X>`), k*, el excedente, la
    parte que en C1 es crédito, el Gini del PPA, del mercado y de C4
    (`gini__<caso>__*`) y las instituciones con el PPA por encima de C1, C4 y
    P2P; la media, el mínimo y el máximo de la serie de XM; el rango de k*; los
    pares institución-caso con la convención de «25 de 64»; y el orden de E0
    con C2 como PPA (`mec__E0__orden_C2ppa`, el de la Fig. 2). Las claves
    `com__<caso>__C2` existentes no cambian: siguen siendo la columna `C2` de
    la hoja `Resumen` (el contrato interno de CAL-52). Compuertas: B^X de la
    comunidad = Resumen; B^C2 = A + PP·S; brechas, PP* y signos coherentes
    fila a fila; las tres tablas de CANON §14.22 a sus decimales.

Añadido el 2026-10-02 (P2P comunitario), también al final, de modo que las
1 343 filas anteriores salen iguales byte a byte:

14. El P2P comunitario (CANON §14.23), la propuesta regulatoria que en el
    artículo en español y en la tesis de entrega reemplaza al mercado por el
    colectivo como mecanismo, de `p2p_comunitario_2026-10-02/
    p2p_comunitario_13casos.csv` (grupo `e1/PC`): por caso, el valor de la
    comunidad (`com__<caso>__P2Pcom`), C4 sin la regla del 10 %
    (`com__<caso>__C4sin10`), P2Pcom − C4 en MCOP y en % de C4, su
    descomposición (`pcom__<caso>__sin10` e `__intercambio`), las brechas con
    C1, P2P, P2P colectivo, C2 como PPA, C5 y C3 (`com__<caso>__P2Pcom_<X>`),
    el caso del art. 20 sin el 10 % y la CINAC, las potencias residual y
    bruta máximas por frontera, el Gini (`gini__<caso>__P2Pcom`) y las dos
    sensibilidades (PDE por importación y caso 1 para todos); y los globales:
    rangos, suma, casos y pares por encima de cada mecanismo, el Gini frente
    a C4 y a P2P, la parte de quitar el 10 % en los casos del caso 1 y el
    orden de E0 con el P2P comunitario (`mec__E0__orden_P2Pcom`, el de la
    Fig. 2 en español). Ninguna clave existente cambia de significado: las
    `*P2Pcol*` siguen siendo el mercado por el colectivo (la vía legal de
    hoy). Compuertas (4): la comunidad = hoja Resumen y PPA, brechas y signos,
    CINAC y suma = los atributos del bloque 8 (a 1e-3 kW: el CSV redondea la planta de UCC a 4 decimales) y caso del art. 20 = el de la
    CINAC; las tres descomposiciones cierran y la comunidad es la suma; las
    tres tablas y el texto de CANON §14.23; ninguna sensibilidad cambia el
    signo frente a C4 y el orden de E0 no tiene empates.

Añadido el 2026-10-02 (los dos órdenes del P2P comunitario), también al
final, de modo que las 1 714 filas anteriores salen iguales byte a byte:

15. P2Pcom − C4 por los dos órdenes y Shapley (CANON §14.23; regla de cita
    como en §14.21: los dos órdenes o Shapley, nunca uno solo). Directo:
    `pcom__<caso>__sin10` e `__intercambio` (ya existentes). Inverso: primero
    el intercambio exento con la regla del 10 % vigente, el P2P comunitario
    con el residual en el caso 2 (`com__<caso>__P2Pcom_caso2`, y sus brechas
    con C4, P2P y C1): `pcom__<caso>__inv_sin10` e `__inv_intercambio`.
    Shapley: `pcom__<caso>__sh_sin10` e `__sh_intercambio`; la interacción, la
    parte de quitar la regla en % por los tres y la clase del caso
    (`pcom__<caso>__orden_clase`). Globales `pcom__orden__*`: los casos en que
    quitar la regla pone la mayor parte por los dos órdenes, en que depende
    del orden y en que todo es intercambio, con sus rangos; las partes por el
    inverso y por Shapley en los casos del caso 1 (`pcom__inv_sin10_share_*`,
    `pcom__sh_sin10_share_*`, `pcom__sh_sin10_{min,max}`), las sumas de los
    13 casos por cada orden y la interacción. Compuertas (2): las identidades
    cierran, en el caso 2 los dos órdenes coinciden al peso y P2Pcom caso 2
    cae en [v01_igual_min, v01_igual_max] de e1/S; la cuarta tabla y el texto
    de CANON §14.23.

Añadido el 2026-10-02 (los derivados del P2P colectivo), también al final, de
modo que las 1 918 filas anteriores salen iguales byte a byte:

16. Las mediciones de la tesis que se hicieron con el viejo mercado por el
    colectivo, rehechas para el P2P colectivo (el P2P comunitario de §14.23,
    renombrado por el autor; sus claves conservan el prefijo `P2Pcom`/`pcom`) y
    para C2 como PPA (CANON §14.24), de `p2p_colectivo_derivados_2026-10-02/`
    (grupo `e1/PD`): mes a mes (`pcom__mes__*`, `ppa__mes__*`, por institución
    `*__mes_inst__*` y por tercil `pcom__tercil*__*`), el barrido de σ
    (`pcom__sigma__*`), el COT (`pcom__cot__*`, `ppa__cot__*`), el comercializador
    único (`pcom__comA__*`, `pcom__comB__*`, `ppa__com*__*`), el retiro de un
    miembro (`pcom__retiro__*`, `ppa__retiro__*`), el factor de coincidencia
    (`pcom__coinc__*`), el precio de la justicia y su clase (`pcom__pof__*`), las
    11 fronteras (`pcom__11f__*`), el umbral (`*__umbral_E4_7P1*`) y el techo
    (`pcom__techo__*`). Compuertas (3): los meses suman el horizonte del P2P
    colectivo y de C2 de los bloques 13 y 14 y la hoja Resumen, y el mercado
    queda sobre C4, C1 y C5 en 116, 116 y 117 meses; las tablas 1, 4, 6 y 7 de
    CANON §14.24 a sus decimales y el precio de la justicia desde la hoja
    Resumen; las claves cuadran con las tablas 2, 3 y 5.

Añadido el 2026-10-02 (el GSA con C2 como PPA y el P2P colectivo), también al
final, de modo que las 2 210 filas anteriores salen iguales byte a byte:

17. La P(inversión) de las siete brechas nuevas de comunidad en la caja del
    GSA del 2026-10-02 (CANON §13.9; grupos `gsa2/`, entrega
    `entrega_gsa_directo_c2_p2pcol_2026-10-03/`): P2P colectivo (`P2Pcom`)
    − C4, − C1, − P2P y − C2 como PPA, y C2 como PPA (`C2ppa`) − C1, − C4 y
    − P2P, con su intervalo al 95 % y su valor en el punto base, por caso
    (`gsa__<caso>__<sufijo>__p|lo|hi|base`, con sufijos `P2Pcom_C4`,
    `P2Pcom_C1`, `P2Pcom_P2P`, `C2ppa_C1`, `C2ppa_C4`, `C2ppa_P2P` y
    `P2Pcom_C2ppa`, que no chocan con los del GSA del 27), y los casos sin
    inversión de cada una (`gsa__n_casos_sin_inversion_<sufijo>`). Las claves
    del GSA del 27 no cambian. Compuertas (3): las cinco brechas del 27 salen
    al bit en la entrega nueva (y la P es la de sus claves); las dos tablas y
    los intervalos de CANON §13.9.3; P2Pcom − C4 sin inversión en los 12.

Añadido el 2026-10-04 (el corte y el fondo, C-282), también al final, de modo
que las 2 553 filas anteriores salen iguales byte a byte:

18. El corte hx y el fondo del P2P colectivo (CANON §14.25), de
    `corte_fondo_2026-10-04/corte_fondo_13casos.csv` (grupo `e1/CF`): por
    caso, la energía transada en el mercado P2P y su ahorro del intercambio
    antes y desde la hora del corte hx del vendedor, con sus partes y el ahorro
    por kWh (`corte__<caso>__*`); el exceso a la bolsa en C1, el mercado P2P,
    el P2P colectivo y C4, con sus diferencias (`exc__<caso>__*`); el residual
    que entra al fondo del P2P colectivo, el que el reparto igual redistribuye,
    el que se acredita a quien todavía importa y el crédito que pierde quien
    cede (`fondo__<caso>__*`); los globales (`corte__casos_con_corte*`,
    `corte__ancho_*`, `fondo__casos_*`) y N1 por institución. Ninguna clave
    existente cambia. Compuertas (3): las sumas, `com__<caso>__banda`,
    `e0__ancho_efectivo` y `atr__<caso>__transado_pct`; las dos tablas de
    CANON §14.25; el P2P colectivo manda más a la bolsa solo en N1.

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
BASE_GSA2 = SALIDAS / "entrega_gsa_directo_c2_p2pcol_2026-10-03"   # grupos gsa2/ (§13.9)
SALIDA =SALIDAS / "cifras_articulo_2026-09-30"

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
# 2026-10-02: las siete brechas nuevas del GSA con C2 como PPA y el P2P
# colectivo (grupos `gsa2/`, CANON §13.9) -> sufijo de la clave, rótulo de la
# tabla de CANON §13.9.3 y rótulo de la definición. Los sufijos no chocan con
# los de BRECHAS: las claves del GSA del 27 siguen iguales.
BRECHAS_GSA2 = {
    "P2Pcom_menos_C4": ("P2Pcom_C4", "P2Pcom − C4", "P2P colectivo (P2Pcom) − C4"),
    "P2Pcom_menos_C1": ("P2Pcom_C1", "P2Pcom − C1", "P2P colectivo (P2Pcom) − C1"),
    "P2Pcom_menos_P2P": ("P2Pcom_P2P", "P2Pcom − P2P", "P2P colectivo (P2Pcom) − P2P"),
    "C2ppa_menos_C1": ("C2ppa_C1", "C2ppa − C1", "C2 como PPA (C2ppa) − C1"),
    "C2ppa_menos_C4": ("C2ppa_C4", "C2ppa − C4", "C2 como PPA (C2ppa) − C4"),
    "C2ppa_menos_P2P": ("C2ppa_P2P", "C2ppa − P2P", "C2 como PPA (C2ppa) − P2P"),
    "P2Pcom_menos_C2ppa": ("P2Pcom_C2ppa", "P2Pcom − C2ppa", "P2P colectivo (P2Pcom) − C2 como PPA (C2ppa)"),
}
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
    if grupo.startswith("gsa2/"):
        return BASE_GSA2
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


# ── 12. La atribución a los dos supuestos (B1, hallazgo I-1; añadido el 2026-09-30) ──
F_ATR = "atribucion_supuestos_2026-09-30/atribucion_13casos.csv"
GRUPOS_ATR = {"s1": ["E1", "E2", "E3", "P1", "N1"], "s2": ["E4", "E5", "P2", "I1"],
              "orden": ["E0", "K1", "CV2", "SINU"]}
EXACTA_ATR = {"E0", "K1", "CV2", "SINU"}


def atribucion(R: pd.DataFrame, tar: dict) -> None:
    """Los dos órdenes de la identidad, Shapley y la interacción por caso, la
    clasificación en tres grupos y el reparto del kWh de ASC (CANON §14.21)."""
    A = pd.read_csv(lee(F_ATR, "e1/S")).set_index("caso")
    exige(list(A.index) == CASOS, f"atribucion: casos {list(A.index)}")
    num = ["P2P", "C1", "C4", "P2P_colectivo", "v01", "texto_s1", "texto_s2", "inverso_s1", "inverso_s2",
           "shapley_s1", "shapley_s2", "interaccion", "inyeccion_kwh", "transado_kwh", "transado_sobre_inyeccion"]
    finito(A[num].to_numpy(), "atribucion")
    for c in CASOS:
        a, r = A.loc[c], R.loc[c]
        tol = max(2.0, 1e-7 * abs(r["P2P"]))
        for mec in ["P2P", "C1", "C4", "P2P_colectivo"]:
            exige(abs(a[mec] - r[mec]) <= tol, f"atribucion {c} {mec}: {a[mec] - r[mec]:.2f} COP frente a Resumen")
        tot = r["P2P"] - r["C4"]
        exige(abs(a.texto_s1 - (r["C1"] - r["C4"])) <= tol and abs(a.texto_s2 - (r["P2P"] - r["C1"])) <= tol,
              f"atribucion {c}: el orden del texto no es (C1 − C4, P2P − C1) de Resumen")
        exige(abs(a.inverso_s2 - (a.v01 - a.C4)) <= 1e-3 and abs(a.inverso_s1 - (a.P2P - a.v01)) <= 1e-3,
              f"atribucion {c}: el orden inverso no es (v01 − C4, P2P − v01)")
        for k1, k2 in [("texto_s1", "texto_s2"), ("inverso_s1", "inverso_s2"), ("shapley_s1", "shapley_s2")]:
            exige(abs(a[k1] + a[k2] - tot) <= tol, f"atribucion {c}: {k1} + {k2} no cierra P2P − C4")
        exige(abs(a.shapley_s1 - 0.5 * (a.texto_s1 + a.inverso_s1)) <= 1e-3
              and abs(a.interaccion - (a.inverso_s1 - a.texto_s1)) <= 1e-3, f"atribucion {c}: Shapley o interacción")
        exige(int(a.c1_esquina_exacta) == int(c in EXACTA_ATR), f"atribucion {c}: c1_esquina_exacta {a.c1_esquina_exacta}")
    ok("atribución (e1/S): P2P, C1, C4 y P2P colectivo = Resumen; orden del texto = (C1 − C4, P2P − C1); los dos órdenes "
       "y Shapley cierran P2P − C4; Shapley = media de los órdenes; C1 esquina exacta solo en E0, K1, CV2 y SINU")
    # la tabla de CANON §14.21 a tres decimales
    t = tablas(seccion("### 14.21 ·"))
    exige(len(t) == 1 and list(t[0].index) == CASOS, "CANON §14.21: se esperaba una tabla de los 13 casos")
    t = t[0]
    COLS = {"P2P − C4": "P2P_menos_C4", "Texto: s1 = C1 − C4": "texto_s1", "Texto: s2 = P2P − C1": "texto_s2",
            "Inverso: s2 = v01 − C4": "inverso_s2", "Inverso: s1 = P2P − v01": "inverso_s1",
            "Shapley s1": "shapley_s1", "Shapley s2": "shapley_s2", "Interacción": "interaccion"}
    for c in CASOS:
        for col, k in COLS.items():
            exige(abs(A.loc[c, k] / M - num_es(t.loc[c, col])) <= 0.0005 + 1e-9,
                  f"CANON §14.21 {c} {col}: {A.loc[c, k] / M:.6f} no redondea a {t.loc[c, col]}")
        exige(round(100 * A.loc[c, "transado_sobre_inyeccion"]) == int(num_es(t.loc[c, "Transado / inyección (%)"])),
              f"CANON §14.21 {c}: transado sobre inyección")
        exige((t.loc[c, "C1 exacta"] == "sí") == (c in EXACTA_ATR), f"CANON §14.21 {c}: C1 exacta")
    ok("la tabla de CANON §14.21 a tres decimales en los 13 casos")
    # E0: energía contra el almacén y las cifras ya emitidas
    ag = almacen("E0", "agentes")
    iny = float(ag.sobrante.astype("float64").sum())
    tr = next(f["valor"] for f in FILAS if f["clave"] == "e0__energia_transada")
    exige(abs(A.loc["E0", "inyeccion_kwh"] - iny) <= 1e-3 and abs(A.loc["E0", "transado_kwh"] - tr) <= 1e-3,
          "atribucion E0: inyección o energía transada distintas del almacén")
    ok("atribución: inyección y energía transada de E0 = almacén de E0 (≤ 1e-3 kWh)")
    FA = F_ATR
    SEC = "§14.21"
    pon("e0__inyeccion_kwh", iny, "kWh", en(iny, 2), "inyección de la comunidad en E0 (sobrante tras el autoconsumo)",
        F_ALM.format("E0", "agentes") + ", suma de sobrante; = " + FA + ", inyeccion_kwh", SEC)
    DEFS = {
        "texto_s1": ("supuesto 1 por el orden del texto (C4 → C1 → P2P): C1 − C4", "texto_s1"),
        "texto_s2": ("supuesto 2 por el orden del texto: P2P − C1", "texto_s2"),
        "inverso_s1": ("supuesto 1 por el orden inverso (C4 → v01 → P2P): P2P − v01", "inverso_s1"),
        "inverso_s2": ("supuesto 2 por el orden inverso: v01 − C4 (v01: intercambio exento, residual al colectivo)", "inverso_s2"),
        "shapley_s1": ("supuesto 1 por Shapley, media de los dos órdenes", "shapley_s1"),
        "shapley_s2": ("supuesto 2 por Shapley, media de los dos órdenes", "shapley_s2"),
        "interaccion": ("interacción de los dos supuestos: (P2P − v01) − (C1 − C4); negativa = sustitutos", "interaccion"),
    }
    grupo = {}
    for c in CASOS:
        a = A.loc[c]
        tot = a.P2P_menos_C4
        for k, (d, col) in DEFS.items():
            pon(f"atr__{c}__{k}", a[col] / M, "MCOP", en(a[col] / M, 2), f"{d}, caso {c}", f"{FA}, {col}", SEC)
        for k in ["texto_s1", "texto_s2", "inverso_s1", "inverso_s2", "shapley_s1", "shapley_s2"]:
            v = 100 * a[k] / tot
            pon(f"atr__{c}__{k}_pct", v, "%", en_int(round(v), " %"),
                f"{DEFS[k][0]}, como parte de P2P − C4, caso {c}", f"{FA}, {k} / P2P_menos_C4", SEC)
        v = 100 * a.transado_sobre_inyeccion
        pon(f"atr__{c}__transado_pct", v, "%", en_int(round(v), " %"),
            f"energía transada dentro como parte de la inyección de la comunidad, caso {c}",
            f"{FA}, transado_kwh / inyeccion_kwh", SEC)
        pon(f"atr__{c}__c1_esquina_exacta", int(a.c1_esquina_exacta), "indicador", en_int(int(a.c1_esquina_exacta)),
            f"1 si C1 es exactamente la esquina «solo el supuesto 1» (con el intercambio pagando la deducción del caso 2 ningún par ganaría), caso {c}",
            f"{FA}, c1_esquina_exacta", SEC)
        s1 = a.texto_s1 / tot > 0.5 and a.inverso_s1 / tot > 0.5
        s2 = a.texto_s2 / tot > 0.5 and a.inverso_s2 / tot > 0.5
        exige(not (s1 and s2), f"atribucion {c}: los dos supuestos mayoritarios a la vez")
        grupo[c] = "s1" if s1 else ("s2" if s2 else "orden")
        pon(f"atr__{c}__grupo", grupo[c], "grupo", grupo[c],
            f"supuesto que explica más de la mitad de P2P − C4 por los dos órdenes (s1, s2), u «orden» si depende del orden, caso {c}",
            f"{FA}, texto_s* e inverso_s* sobre P2P_menos_C4", SEC)
    obtenidos = {g: [c for c in CASOS if grupo[c] == g] for g in GRUPOS_ATR}
    exige(obtenidos == GRUPOS_ATR, f"atribucion: grupos {obtenidos}, CANON §14.21 dice {GRUPOS_ATR}")
    ok("atribución: los tres grupos de CANON §14.21 (s1: E1, E2, E3, P1, N1; s2: E4, E5, P2, I1; orden: E0, K1, CV2, SINU)")
    for g, cs in GRUPOS_ATR.items():
        pon(f"atr__grupo_{g}__casos", ", ".join(cs), "casos", ", ".join(cs),
            f"casos del grupo «{g}» de la atribución a los supuestos", f"{FA}; regla de atr__<caso>__grupo", SEC)
        pon(f"atr__grupo_{g}__n", len(cs), "casos", en_int(len(cs)), f"número de casos del grupo «{g}»",
            f"{FA}; regla de atr__<caso>__grupo", SEC)
        tp = [100 * A.loc[c, "transado_sobre_inyeccion"] for c in cs]
        pon(f"atr__grupo_{g}__transado_pct_min", min(tp), "%", en_int(round(min(tp)), " %"),
            f"menor parte transada de la inyección en el grupo «{g}»", f"{FA}, transado_sobre_inyeccion", SEC)
        pon(f"atr__grupo_{g}__transado_pct_max", max(tp), "%", en_int(round(max(tp)), " %"),
            f"mayor parte transada de la inyección en el grupo «{g}»", f"{FA}, transado_sobre_inyeccion", SEC)
    for k in ["texto_s1", "inverso_s1"]:
        vs = [100 * A.loc[c, k] / A.loc[c, "P2P_menos_C4"] for c in GRUPOS_ATR["s1"]]
        for f, x in [("min", min(vs)), ("max", max(vs))]:
            pon(f"atr__grupo_s1__{k}_pct_{f}", x, "%", en_int(round(x), " %"),
                f"{'menor' if f == 'min' else 'mayor'} parte de P2P − C4 del {DEFS[k][0]} en el grupo «s1»",
                f"{FA}, {k} / P2P_menos_C4", SEC)
    solo = [100 * min(A.loc[c, "texto_s1"], A.loc[c, "inverso_s2"]) / A.loc[c, "P2P_menos_C4"] for c in GRUPOS_ATR["orden"]]
    solo_max = [100 * max(A.loc[c, "texto_s1"], A.loc[c, "inverso_s2"]) / A.loc[c, "P2P_menos_C4"] for c in GRUPOS_ATR["orden"]]
    pon("atr__grupo_orden__un_supuesto_pct_min", min(solo), "%", en_int(round(min(solo)), " %"),
        "en el grupo «orden», la menor parte de P2P − C4 que deja un supuesto solo (C1 − C4 o v01 − C4)",
        f"{FA}, mín(texto_s1, inverso_s2) / P2P_menos_C4", SEC)
    pon("atr__grupo_orden__un_supuesto_pct_max", max(solo_max), "%", en_int(round(max(solo_max)), " %"),
        "en el grupo «orden», la mayor parte de P2P − C4 que deja un supuesto solo (C1 − C4 o v01 − C4)",
        f"{FA}, máx(texto_s1, inverso_s2) / P2P_menos_C4", SEC)
    # el kWh de ASC a ASC en abril: Cv + Θ sobre C4, por orden
    T, com = tar["T"], tar["com"]
    r = T.loc[(com["ASC"][0], MES_REP)]
    p2p_c4 = next(f["valor"] for f in FILAS if f["clave"] == f"kwh__ASC__{MES_REP}__P2P_C4")
    exige(abs(r.Cv + r.Theta - p2p_c4) <= 1e-9, "kWh de ASC: Cv + Θ distinto de kwh__ASC__P2P_C4")
    for k, v, d in [("texto_s1", r.Theta, "cargos de red Θ: supuesto 1 por el orden del texto"),
                    ("texto_s2", r.Cv, "Cv: supuesto 2 por el orden del texto"),
                    ("inverso_s1", 0.0, "supuesto 1 por el orden inverso (el kWh transado se libra de los cargos por el supuesto 2)"),
                    ("inverso_s2", r.Cv + r.Theta, "Cv + Θ: supuesto 2 por el orden inverso"),
                    ("shapley_s1", 0.5 * r.Theta, "supuesto 1 por Shapley: Θ / 2"),
                    ("shapley_s2", r.Cv + 0.5 * r.Theta, "supuesto 2 por Shapley: Cv + Θ / 2")]:
        pon(f"kwh__ASC__{MES_REP}__{k}", v, "COP/kWh", en(v, 2),
            f"reparto de lo que un kWh vendido dentro de ASC gana sobre C4 (Cv + Θ): {d}; {MES_REP}",
            F_ALM.format("E0", "agentes") + " y " + F_ALM.format("P2", "agentes") + ", techo y piso (como kwh__ASC__*)", SEC)
    ok("kWh de ASC en abril: Cv + Θ = kwh__ASC__P2P_C4, repartido por los dos órdenes y por Shapley")


# ── 13. El C2 de la propuesta como PPA (punto P; añadido el 2026-10-02) ─────
F_PPA = "c2_ppa_2026-10-02/c2_ppa_13casos.csv"
# mecanismo del CSV del PPA -> sufijo de la clave y de la hoja Resumen
MECS_PPA = {"C1": "C1", "C4": "C4", "P2P": "P2P", "P2P_colectivo": "P2Pcol", "C3": "C3"}
ROT_PPA = {"C1": "C1", "C4": "C4", "P2P": "P2P", "P2P_colectivo": "P2P colectivo", "C3": "C3"}


def ppa(R: pd.DataFrame) -> None:
    """El C2 de la propuesta como PPA de todo el excedente por institución
    (CANON §14.22), con el PP a la media de la serie de XM."""
    T = pd.read_csv(lee(F_PPA, "e1/P"), keep_default_na=False, na_values=[""])
    exige(len(T) == 77, f"c2_ppa: {len(T)} filas, no 77")
    es_com = T.institucion == "comunidad"
    C = T[es_com].set_index("caso")
    I = T[~es_com]
    exige(list(C.index) == CASOS, f"c2_ppa: casos {list(C.index)}")
    exige(len(I) == 64, f"c2_ppa: {len(I)} pares institución-caso, no 64")
    exige(set(T.comercializador.fillna("")) <= {"", "A", "B"}, "c2_ppa: comercializador sin anonimizar")
    pp = {}
    for v in ["media", "minimo", "maximo"]:
        col = T[f"PP_{v}_COP_kWh"]
        if v == "media":
            col = col[T.excedente_kwh > 0]       # sin excedente, la media simple (igual)
        exige(float(col.max() - col.min()) <= 1e-6, f"c2_ppa: PP {v} no es único")
        pp[v] = float(col.iloc[0])
    exige(pp["minimo"] < pp["media"] < pp["maximo"], "c2_ppa: PP fuera de orden")
    # compuertas fila a fila
    for x in MECS_PPA:
        tol = np.maximum(0.05, 1e-9 * C[f"B_{x}_COP"].abs())
        dif = (C[f"B_{x}_COP"] - R.loc[CASOS, x].to_numpy()).abs()
        exige(bool((dif <= tol).all()), f"c2_ppa: la comunidad con {x} no es la hoja Resumen ({dif.max():.3f} COP)")
        b = T.B_C2_media_COP - T[f"B_{x}_COP"]
        exige(float((b - T[f"brecha_C2_media_menos_{x}_COP"]).abs().max()) <= 1e-3, f"c2_ppa: brecha con {x}")
        s = T[f"signo_C2_media_menos_{x}"]
        exige(bool(((s == 1) == (b > 1.0)).all() and ((s == -1) == (b < -1.0)).all()), f"c2_ppa: signo con {x}")
        r = T[T.excedente_kwh > 0]
        exige(float((r.A_autoconsumo_COP + r[f"PPeq_{x}_COP_kWh"] * r.excedente_kwh - r[f"B_{x}_COP"]).abs().max())
              <= 0.5, f"c2_ppa: PP* de {x} no reproduce B^{x}")
    exige(float((T.A_autoconsumo_COP + pp["media"] * T.excedente_kwh - T.B_C2_media_COP).abs().max()) <= 0.5,
          "c2_ppa: B^C2 no es A + PP·S")
    gcols = ["gini_C2_media", "gini_P2P", "gini_C4"]
    finito(C[gcols].to_numpy(), "c2_ppa: Gini")
    exige(bool(((C[gcols] >= 0) & (C[gcols] <= 1)).all().all()), "c2_ppa: Gini fuera de [0, 1]")
    ok("C2 como PPA (e1/P): B^X de la comunidad = hoja Resumen (C1, C4, P2P, P2P colectivo, C3); B^C2 = A + PP·S con "
       "PP la media de XM; brechas, PP* y signos coherentes fila a fila; 64 pares institución-caso")
    # las tres tablas de CANON §14.22, a sus decimales
    t = tablas(seccion("### 14.22 ·"))
    exige(len(t) == 3, f"CANON §14.22: {len(t)} tablas, no 3")
    t1, t2, t3 = t

    def igual(v, celda, d, qué):
        exige(abs(v - num_es(celda)) <= 0.5 * 10 ** -d + 1e-9, f"CANON §14.22 {qué}: {v:.6f} no redondea a {celda}")

    for c in CASOS:
        r = C.loc[c]
        igual(r.excedente_kwh, t1.loc[c, "S (kWh)"], 2, f"{c} S")
        for x, col in [("C1", "PP* frente a C1"), ("C4", "frente a C4"), ("P2P", "frente a P2P"),
                       ("P2P_colectivo", "frente a P2P colectivo"), ("C3", "frente a C3")]:
            igual(r[f"PPeq_{x}_COP_kWh"], t1.loc[c, col], 2, f"{c} {col}")
        igual(100 * r.fraccion_credito_C1, t1.loc[c, "Crédito en C1 (%)"], 1, f"{c} crédito")
        igual(r.B_C2_media_COP / M, t2.loc[c, "C2"], 3, f"{c} C2")
        for x in MECS_PPA:
            igual(r[f"brecha_C2_media_menos_{x}_COP"] / M, t2.loc[c, f"C2 − {ROT_PPA[x]}"], 3, f"{c} C2 − {x}")
        igual(r.k_estrella, t2.loc[c, "k*"], 3, f"{c} k*")
        for k, col in [("gini_C2_media", "Gini PPA"), ("gini_P2P", "Gini P2P"), ("gini_C4", "Gini C4"),
                       ("gini_C1", "Gini C1")]:
            igual(r[k], t3.loc[c, col], 3, f"{c} {col}")
        i_ = I[I.caso == c]
        exige(len(i_) == int(t3.loc[c, "Instituciones"]), f"CANON §14.22 {c}: instituciones")
        for x in ["C1", "C4", "P2P"]:
            exige(int((i_[f"signo_C2_media_menos_{x}"] == 1).sum()) == int(t3.loc[c, f"PPA > {x}"]),
                  f"CANON §14.22 {c}: instituciones con el PPA sobre {x}")
    for x in ["C1", "C4", "P2P"]:
        exige(int((I[f"signo_C2_media_menos_{x}"] == 1).sum()) == int(t3.loc["Total", f"PPA > {x}"]),
              f"CANON §14.22: pares con el PPA sobre {x}")
    exige(int(t3.loc["Total", "Instituciones"]) == len(I), "CANON §14.22: total de pares")
    ok("las tres tablas de CANON §14.22 (PP*, valor y brechas, Gini y pares) a sus decimales en los 13 casos")

    SEC = "§14.22"
    FC = F_PPA + ", fila comunidad, "
    for c in CASOS:
        r = C.loc[c]
        v = r.B_C2_media_COP / M
        pon(f"com__{c}__C2ppa", v, "MCOP", en(v, 2),
            f"beneficio neto de la comunidad con C2 como PPA de todo el excedente por institución, PP = media de XM, caso {c}",
            FC + "B_C2_media_COP", SEC)
        for x, suf in MECS_PPA.items():
            v = r[f"brecha_C2_media_menos_{x}_COP"] / M
            pon(f"com__{c}__C2ppa_{suf}", v, "MCOP", en(v, 2),
                f"C2 como PPA (media de XM) − {ROT_PPA[x]} de la comunidad, caso {c}",
                FC + f"brecha_C2_media_menos_{x}_COP", SEC)
        for x, suf in MECS_PPA.items():
            v = r[f"PPeq_{x}_COP_kWh"]
            pon(f"ppa__{c}__PPeq_{suf}", v, "COP/kWh", en(v, 2),
                f"precio pactado con el que el PPA iguala a {ROT_PPA[x]} en la comunidad, caso {c}",
                FC + f"PPeq_{x}_COP_kWh", SEC)
        pon(f"ppa__{c}__k_estrella", r.k_estrella, "factor", en(r.k_estrella, 2),
            f"factor de la bolsa con el que vender todo el excedente a la bolsa (C3) iguala al PPA a la media de XM, caso {c}",
            FC + "k_estrella", SEC)
        pon(f"ppa__{c}__excedente_kwh", r.excedente_kwh, "kWh", en(r.excedente_kwh, 2),
            f"excedente horario de la comunidad, Σ max(G − D, 0), caso {c}", FC + "excedente_kwh", SEC)
        v = 100 * r.fraccion_credito_C1
        pon(f"ppa__{c}__credito_C1_pct", v, "%", en(v, 1, " %"),
            f"parte del excedente que en C1 es crédito (tipo 1), caso {c}", FC + "fraccion_credito_C1", SEC)
        for k, nom in [("gini_C2_media", "C2ppa"), ("gini_P2P", "P2P"), ("gini_C4", "C4")]:
            pon(f"gini__{c}__{nom}", r[k], "índice", en(r[k], 3),
                f"Gini del beneficio por institución (C-214), {'C2 como PPA a la media de XM' if nom == 'C2ppa' else nom}, caso {c}",
                FC + k + ("" if nom == "C2ppa" else " (= hoja PoF_Fairness)"), SEC)
        i_ = I[I.caso == c]
        pon(f"ppa__{c}__n_inst", len(i_), "instituciones", en_int(len(i_)), f"instituciones del caso {c}",
            F_PPA + ", filas de institución", SEC)
        for x in ["C1", "C4", "P2P"]:
            n = int((i_[f"signo_C2_media_menos_{x}"] == 1).sum())
            pon(f"ppa__{c}__inst_sobre_{x}", n, "instituciones", en_int(n),
                f"instituciones con el PPA a la media de XM por encima de {x}, caso {c}",
                F_PPA + f", filas de institución, signo_C2_media_menos_{x} = 1", SEC)
    FX = F_PPA + ", columna "
    for v, k, d in [("media", "PP_media", "media horaria"), ("minimo", "PP_min", "mínimo"), ("maximo", "PP_max", "máximo")]:
        pon(f"ppa__{k}", pp[v], "COP/kWh", en(pp[v], 2),
            f"{d} de la serie de XM de contratos del mercado no regulado en el horizonte (PP de referencia del PPA)",
            FX + f"PP_{v}_COP_kWh", SEC)
    ks = C.k_estrella
    pon("ppa__k_estrella_min", float(ks.min()), "factor", en(ks.min(), 2), f"menor k* de la comunidad ({ks.idxmin()})",
        FC + "k_estrella", SEC)
    pon("ppa__k_estrella_max", float(ks.max()), "factor", en(ks.max(), 2), f"mayor k* de la comunidad ({ks.idxmax()})",
        FC + "k_estrella", SEC)
    PI = F_PPA + ", filas de institución, "
    pon("ppa__pares__n", len(I), "pares", en_int(len(I)),
        "pares institución-caso (12 casos × 5 y SINU × 4, sin Udenar; convención de «25 de 64 bajo C4»)",
        PI + "conteo", SEC)
    for x, suf in MECS_PPA.items():
        n = int((I[f"signo_C2_media_menos_{x}"] == 1).sum())
        pon(f"ppa__pares__sobre_{suf}", n, "pares de 64", en_int(n),
            f"pares institución-caso con el PPA a la media de XM por encima de {ROT_PPA[x]}",
            PI + f"signo_C2_media_menos_{x} = 1", SEC)
    n_emp = int((I.signo_C2_media_menos_C1 == 0).sum())
    pon("ppa__pares__empates_C1", n_emp, "pares de 64", en_int(n_emp),
        "pares con el PPA igual a C1 a menos de 1 COP (las instituciones de K1 sin excedente)",
        PI + "signo_C2_media_menos_C1 = 0", SEC)
    for x in ["C1", "P2P"]:
        s = I[I[f"signo_C2_media_menos_{x}"] == 1]
        lista = "; ".join(s.caso + " " + s.institucion)
        pon(f"ppa__pares__sobre_{x}__lista", lista, "pares", lista,
            f"pares institución-caso con el PPA a la media de XM por encima de {x}", PI + f"signo_C2_media_menos_{x} = 1",
            SEC)
    for nom, cond in [("sobre_C1_y_C4", (C.signo_C2_media_menos_C1 == 1) & (C.signo_C2_media_menos_C4 == 1)),
                      ("sobre_P2P", C.signo_C2_media_menos_P2P == 1)]:
        lista = ", ".join(C.index[cond])
        exige(bool(lista), f"c2_ppa: ningún caso {nom}")
        pon(f"ppa__casos_{nom}", lista, "casos", lista,
            f"casos con la comunidad mejor con el PPA a la media de XM que con {' y con '.join(nom[6:].split('_y_'))}",
            FC + "signo_C2_media_menos_*", SEC)
    for x in ["P2P", "C4"]:
        n = int((C.gini_C2_media < C[f"gini_{x}"]).sum())
        pon(f"gini__casos_C2ppa_menor_que_{x}", n, "casos", en_int(n),
            f"casos en que el Gini del PPA a la media de XM es menor que el de {x}", FC + f"gini_C2_media y gini_{x}", SEC)
    # el orden de E0 con C2 como PPA (Fig. 2): los siete de la hoja Resumen, con el PPA en lugar de C2
    b = {m: R.loc["E0", m] for m in ["P2P", "P2P_colectivo", "C1", "C3", "C4", "C5"]}
    b["C2"] = C.loc["E0", "B_C2_media_COP"]
    rot = {"P2P_colectivo": "P2P colectivo"}
    orden = " > ".join(rot.get(m, m) for m in sorted(b, key=lambda m: -b[m]))
    exige(orden == "P2P > C1 > C4 > P2P colectivo > C5 > C2 > C3", f"orden de E0 con el PPA: {orden}")
    exige(min(abs(b[m] - b[n]) for m in b for n in b if m != n) > 1.0, "orden de E0 con el PPA: empate")
    pon("mec__E0__orden_C2ppa", orden, "orden", orden,
        "orden de los mecanismos en E0 por beneficio neto, con C2 como PPA a la media de XM",
        F_RES.format("E0") + " y " + FC + "B_C2_media_COP", SEC)
    ok("C2 como PPA: orden de E0 con el PPA en lugar de C2: " + orden)


# ── 14. El P2P comunitario (punto PC; añadido el 2026-10-02) ───────────────
F_PC = "p2p_comunitario_2026-10-02/p2p_comunitario_13casos.csv"
# mecanismo del CSV del P2P comunitario -> sufijo de la clave y rótulo
MECS_PC = {"C1": ("C1", "C1"), "C4": ("C4", "C4"), "P2P": ("P2P", "P2P (con sus dos supuestos)"),
           "P2P_colectivo": ("P2Pcol", "P2P por el colectivo (la vía legal de hoy)"),
           "C2ppa": ("C2ppa", "C2 como PPA a la media de XM"), "C5": ("C5", "C5"), "C3": ("C3", "C3")}


def valor_de(clave: str):
    """Valor de una clave ya emitida en esta corrida (falla si no está)."""
    f = [x for x in FILAS if x["clave"] == clave]
    exige(len(f) == 1, f"falta la clave {clave} para contrastar")
    return f[0]["valor"]


def es_txt(v: float, dec: int) -> str:
    """Forma española del canon: coma decimal, espacio de millares, signo «−»."""
    s = en(v, dec).replace(",", " ").replace(".", ",")
    return s.replace("-", "−")


def p2p_comunitario(R: pd.DataFrame) -> None:
    """El P2P comunitario (CANON §14.23): intercambio interno exento de cargos y
    fuera del fondo, y el residual al autogenerador colectivo con el PDE igual,
    en el caso del art. 20 que da la CINAC sin la regla del 10 %."""
    T = pd.read_csv(lee(F_PC, "e1/PC"), keep_default_na=False, na_values=[""])
    exige(len(T) == 77, f"p2p_comunitario: {len(T)} filas, no 77")
    es_com = T.institucion == "comunidad"
    C = T[es_com].set_index("caso")
    I = T[~es_com]
    exige(list(C.index) == CASOS, f"p2p_comunitario: casos {list(C.index)}")
    exige(len(I) == 64, f"p2p_comunitario: {len(I)} pares institución-caso, no 64")
    exige(set(T.comercializador.fillna("")) <= {"", "A", "B"}, "p2p_comunitario: comercializador sin anonimizar")
    num = [c for c in T.columns if c not in ("caso", "institucion", "comercializador")
           and not c.startswith("gini_") and not c.startswith("pot_") and c != "cap_planta_kw"]
    finito(T[num].to_numpy(), "p2p_comunitario: columnas numéricas")
    gcols = [c for c in T.columns if c.startswith("gini_")]
    finito(C[gcols].to_numpy(), "p2p_comunitario: Gini")
    exige(bool(((C[gcols] >= 0) & (C[gcols] <= 1)).all().all()), "p2p_comunitario: Gini fuera de [0, 1]")
    finito(C[["pot_residual_max_kw", "pot_excedente_max_kw"]].to_numpy(), "p2p_comunitario: potencias")

    # (a) los mecanismos de la comunidad son los de la hoja Resumen y del PPA
    P = pd.read_csv(lee(F_PPA, "e1/P"), keep_default_na=False, na_values=[""])
    Pc = P[P.institucion == "comunidad"].set_index("caso")
    for x in MECS_PC:
        ref = (Pc.loc[CASOS, "B_C2_media_COP"] if x == "C2ppa" else R.loc[CASOS, x]).to_numpy(dtype=float)
        dif = (C[f"B_{x}_COP"].to_numpy(dtype=float) - ref)
        exige(bool((np.abs(dif) <= np.maximum(0.05, 1e-9 * np.abs(ref))).all()),
              f"p2p_comunitario: la comunidad con {x} no es la de la hoja Resumen o del PPA ({np.abs(dif).max():.3f} COP)")
        b = T.P2Pcom_COP - T[f"B_{x}_COP"]
        exige(float((b - T[f"brecha_P2Pcom_menos_{x}_COP"]).abs().max()) <= 1e-3, f"p2p_comunitario: brecha con {x}")
        s = T[f"signo_P2Pcom_menos_{x}"]
        exige(bool(((s == 1) == (b > 1.0)).all() and ((s == -1) == (b < -1.0)).all()), f"p2p_comunitario: signo con {x}")
    for c in CASOS:
        exige(abs(C.loc[c, "suma_cap_kw"] - valor_de(f"caso__{c}__cap_suma_kW")) <= 1e-3, f"{c}: suma de plantas")
        exige(abs(C.loc[c, "cinac_kw"] - valor_de(f"caso__{c}__capu_kW")) <= 1e-3, f"{c}: CINAC ≠ capu_kW")
        caso = 1 if (C.loc[c, "cinac_kw"] <= 100 and C.loc[c, "suma_cap_kw"] <= 1000) else 2
        exige(int(C.loc[c, "caso_art20"]) == caso, f"{c}: caso del art. 20 sin el 10 % no es el de la CINAC")
        exige(bool((I[I.caso == c].caso_art20 == caso).all()), f"{c}: las instituciones no comparten el caso")
    ok("P2P comunitario (e1/PC): C1, C4, P2P, P2P colectivo, C5 y C3 de la comunidad = hoja Resumen y C2 = el PPA "
       "(e1/P); brechas y signos coherentes fila a fila; suma de plantas y CINAC = caso__*__cap_suma_kW y capu_kW; "
       "caso del art. 20 = el de la CINAC (≤ 100 kW y ≤ 1 MW)")

    # (b) las descomposiciones cierran; la comunidad es la suma de sus instituciones
    for pre, a, b_ in [("", "C4_sin10_COP", "C4_COP"), ("imp_", "C4_sin10_imp_COP", "C4_imp_COP"),
                       ("c1todos_", "C4_sin10_c1todos_COP", "C4_COP")]:
        tot = "P2Pcom_menos_C4_COP" if pre == "" else f"{pre}P2Pcom_menos_C4_COP"
        exige(float((T[f"{pre}dec_sin10_COP"] + T[f"{pre}dec_intercambio_COP"] - T[tot]).abs().max()) <= 1e-3,
              f"p2p_comunitario: la descomposición {pre or 'base'} no cierra")
        exige(float((T[a] - T[b_] - T[f"{pre}dec_sin10_COP"]).abs().max()) <= 1e-3,
              f"p2p_comunitario: «quitar el 10 %» {pre or 'base'} no es C4 sin 10 % − C4")
    exige(float((C.P2Pcom_menos_C4_COP - C.brecha_P2Pcom_menos_C4_COP).abs().max()) <= 1.0,
          "p2p_comunitario: P2Pcom − C4 de la descomposición y de la brecha difieren en más de 1 COP")
    for c in ["E4", "E5", "P2"]:
        exige(int(C.loc[c, "caso_art20"]) == 2 and abs(C.loc[c, "dec_sin10_COP"]) <= 1e-6,
              f"{c}: en el caso 2 quitar el 10 % no vale cero")
    for col in ["P2Pcom_COP", "C4_sin10_COP", "P2Pcom_imp_COP", "P2Pcom_c1todos_COP"]:
        sumas = I.groupby("caso")[col].sum().reindex(CASOS)
        exige(float((sumas - C[col]).abs().max()) <= 1e-3, f"p2p_comunitario: la comunidad no es la suma en {col}")
    ok("P2P comunitario: las tres descomposiciones P2Pcom − C4 = (C4 sin 10 % − C4) + intercambio cierran (base, "
       "PDE por importación y caso 1 para todos); en E4, E5 y P2 quitar el 10 % vale cero; la comunidad es la suma")

    # (c) las tres tablas de CANON §14.23 a sus decimales
    t = tablas(seccion("### 14.23 ·"))
    exige(len(t) == 4, f"CANON §14.23: {len(t)} tablas, no 4 (la cuarta, los dos órdenes, va en p2p_comunitario_ordenes)")
    t1, t2, t3 = t[:3]

    def igual(v, celda, d, qué):
        exige(abs(v - num_es(celda)) <= 0.5 * 10 ** -d + 1e-9, f"CANON §14.23 {qué}: {v:.6f} no redondea a {celda}")

    for c in CASOS:
        r = C.loc[c]
        for col, k in [("Suma de plantas", "suma_cap_kw"), ("CINAC", "cinac_kw"),
                       ("Residual máx. por frontera", "pot_residual_max_kw"),
                       ("Excedente máx. por frontera", "pot_excedente_max_kw")]:
            igual(r[k], t1.loc[c, col], 2, f"{c} {col}")
        exige(int(r.caso_art20) == int(t1.loc[c, "Caso del art. 20"]), f"CANON §14.23 {c}: caso del art. 20")
        for col, k in [("C4", "B_C4_COP"), ("C4 sin 10 %", "C4_sin10_COP"), ("P2P comunitario", "P2Pcom_COP"),
                       ("P2P (con supuestos)", "B_P2P_COP"), ("P2Pcom − C4", "P2Pcom_menos_C4_COP"),
                       ("Quitar el 10 %", "dec_sin10_COP"), ("Intercambio exento", "dec_intercambio_COP"),
                       ("P2Pcom − C1", "brecha_P2Pcom_menos_C1_COP"),
                       ("P2Pcom − C2 (PPA)", "brecha_P2Pcom_menos_C2ppa_COP"),
                       ("P2Pcom − P2P", "brecha_P2Pcom_menos_P2P_COP")]:
            igual(r[k] / M, t2.loc[c, col], 3, f"{c} {col}")
        for col, k in [("Gini P2Pcom", "gini_P2Pcom"), ("Gini C4", "gini_C4"), ("Gini P2P", "gini_P2P")]:
            igual(r[k], t2.loc[c, col], 3, f"{c} {col}")
        for col, k in [("Imp.: P2Pcom − C4", "imp_P2Pcom_menos_C4_COP"), ("Imp.: quitar el 10 %", "imp_dec_sin10_COP"),
                       ("Imp.: intercambio", "imp_dec_intercambio_COP"),
                       ("Imp.: P2Pcom − P2P", "imp_P2Pcom_menos_P2P_COP"),
                       ("Caso 1 para todos: P2Pcom − C4", "c1todos_P2Pcom_menos_C4_COP"),
                       ("Quitar el 10 %", "c1todos_dec_sin10_COP"), ("Intercambio", "c1todos_dec_intercambio_COP")]:
            igual(r[k] / M, t3.loc[c, col], 3, f"{c} {col}")

    # los resúmenes que el texto de §14.23 escribe
    g = C.brecha_P2Pcom_menos_C4_COP / M
    pct = 100 * C.brecha_P2Pcom_menos_C4_COP / C.B_C4_COP
    g1 = C.brecha_P2Pcom_menos_C1_COP / M
    caso1 = [c for c in CASOS if int(C.loc[c, "caso_art20"]) == 1]
    sh = 100 * C.loc[caso1, "dec_sin10_COP"] / C.loc[caso1, "P2Pcom_menos_C4_COP"]
    suma_pcom = float(g.sum())
    suma_p2p = float((R.loc[CASOS, "P2P"] - R.loc[CASOS, "C4"]).sum() / M)
    sobre = {x: int((I[f"signo_P2Pcom_menos_{x}"] == 1).sum()) for x in MECS_PC}
    frases = [
        f"de {es_txt(g.min(), 2)} ({g.idxmin()}) a {es_txt(g.max(), 2)} MCOP ({g.idxmax()}), entre el "
        f"{es_txt(pct.min(), 1)} y el {es_txt(pct.max(), 1)} % de C4; en los 13 suma {es_txt(suma_pcom, 2)} MCOP, "
        f"frente a {es_txt(suma_p2p, 2)} del mercado P2P",
        f"Supera también a C1 en los 13 (de {es_txt(g1.min(), 2)} a {es_txt(g1.max(), 2)} MCOP)",
        f"entre el {int(round(float(sh.min())))} % ({sh.idxmin()}) y el {int(round(float(sh.max())))} % ({sh.idxmax()}) de P2Pcom − C4",
        f"por encima de C4 en {sobre['C4']} de {len(I)}",
        f"y de C1 en {sobre['C1']}.",
        f"menor que el de C4 en {int((C.gini_P2Pcom < C.gini_C4).sum())} casos",
        f"es menor que el del mercado en {int((C.gini_P2Pcom < C.gini_P2P).sum())} ",
    ]
    sec = seccion("### 14.23 ·")
    for f_ in frases:
        exige(f_ in sec, f"CANON §14.23 no escribe «{f_}»")
    ok("las tres tablas de CANON §14.23 (clasificación y potencias, la comunidad, las sensibilidades) a sus decimales "
       "en los 13 casos, y los rangos, la suma, la parte de quitar el 10 %, los pares y el Gini de su texto")

    SEC = "§14.23"
    FC = F_PC + ", fila comunidad, "
    for c in CASOS:
        r = C.loc[c]
        for k, col, dfn in [
                ("P2Pcom", "P2Pcom_COP", "beneficio neto de la comunidad con el P2P comunitario (propuesta regulatoria: "
                 "intercambio exento, residual al colectivo sin la regla del 10 %, PDE igual)"),
                ("C4sin10", "C4_sin10_COP", "beneficio neto de la comunidad con C4 sin la regla del 10 % (caso del art. 20 "
                 "que da la CINAC, sin intercambio, PDE igual)")]:
            pon(f"com__{c}__{k}", r[col] / M, "MCOP", en(r[col] / M, 2), f"{dfn}, caso {c}", FC + col, SEC)
        v = r.brecha_P2Pcom_menos_C4_COP / M
        pon(f"com__{c}__P2Pcom_C4", v, "MCOP", en(v, 2), f"P2P comunitario − C4 de la comunidad, caso {c}",
            FC + "brecha_P2Pcom_menos_C4_COP", SEC)
        v = 100 * r.brecha_P2Pcom_menos_C4_COP / r.B_C4_COP
        pon(f"com__{c}__P2Pcom_C4_pct", v, "%", en(v, 2, " %"), f"(P2P comunitario − C4) sobre C4, caso {c}",
            FC + "brecha_P2Pcom_menos_C4_COP / B_C4_COP", SEC)
        for k, col, dfn in [("sin10", "dec_sin10_COP", "lo que vale quitar la regla del 10 % (C4 sin 10 % − C4)"),
                            ("intercambio", "dec_intercambio_COP",
                             "lo que vale el intercambio exento (P2P comunitario − C4 sin 10 %)")]:
            pon(f"pcom__{c}__{k}", r[col] / M, "MCOP", en(r[col] / M, 2),
                f"{dfn}, término de P2P comunitario − C4, PDE igual, caso {c}", FC + col, SEC)
        for x, (suf, rot) in MECS_PC.items():
            if x == "C4":
                continue
            v = r[f"brecha_P2Pcom_menos_{x}_COP"] / M
            pon(f"com__{c}__P2Pcom_{suf}", v, "MCOP", en(v, 2), f"P2P comunitario − {rot} de la comunidad, caso {c}",
                FC + f"brecha_P2Pcom_menos_{x}_COP", SEC)
        pon(f"pcom__{c}__caso_art20", int(r.caso_art20), "caso", en_int(int(r.caso_art20)),
            f"caso del art. 20 de la CREG 101 072 del P2P comunitario, sin la regla del 10 %: 1 si la CINAC ≤ 100 kW y la "
            f"suma ≤ 1 MW (no es caso__{c}__caso_art20, que aplica la regla del 10 %), caso {c}", FC + "caso_art20", SEC)
        pon(f"pcom__{c}__cinac_kW", r.cinac_kw, "kW", en(r.cinac_kw, 2),
            f"capacidad instalada por usuario del art. 18 (CINAC = suma de las plantas / fronteras), caso {c}",
            FC + "cinac_kw (= caso__*__capu_kW)", SEC)
        for k, col, dfn in [("pot_residual_max_kW", "pot_residual_max_kw",
                             "potencia residual horaria máxima por frontera, máx_h max(s − v, 0); informativa"),
                            ("pot_excedente_max_kW", "pot_excedente_max_kw",
                             "potencia del excedente bruto horario máxima por frontera, máx_h s; informativa")]:
            pon(f"pcom__{c}__{k}", r[col], "kW", en(r[col], 2), f"{dfn}, caso {c}", FC + col, SEC)
        pon(f"gini__{c}__P2Pcom", r.gini_P2Pcom, "índice", en(r.gini_P2Pcom, 3),
            f"Gini del beneficio por institución (C-214), P2P comunitario, caso {c}", FC + "gini_P2Pcom", SEC)
        for k, col, dfn in [
                ("imp_P2Pcom_C4", "imp_P2Pcom_menos_C4_COP",
                 "sensibilidad del PDE por importación (P2P comunitario por importación residual, C4 por importación, H-100): "
                 "P2P comunitario − C4"),
                ("imp_sin10", "imp_dec_sin10_COP", "sensibilidad del PDE por importación: quitar la regla del 10 %"),
                ("imp_intercambio", "imp_dec_intercambio_COP", "sensibilidad del PDE por importación: el intercambio exento"),
                ("imp_P2Pcom_P2P", "imp_P2Pcom_menos_P2P_COP", "sensibilidad del PDE por importación: P2P comunitario − P2P"),
                ("c1todos_P2Pcom_C4", "c1todos_P2Pcom_menos_C4_COP",
                 "sensibilidad «caso 1 para todos» (κ·Cv en los 13 casos; segunda reforma, sin base vigente): "
                 "P2P comunitario − C4"),
                ("c1todos_sin10", "c1todos_dec_sin10_COP", "sensibilidad «caso 1 para todos»: quitar la regla del 10 %"),
                ("c1todos_intercambio", "c1todos_dec_intercambio_COP",
                 "sensibilidad «caso 1 para todos»: el intercambio exento")]:
            pon(f"pcom__{c}__{k}", r[col] / M, "MCOP", en(r[col] / M, 2), f"{dfn}, caso {c}", FC + col, SEC)

    # globales
    FX = F_PC + ", filas comunidad, "
    pon("pcom__P2Pcom_C4_min", float(g.min()), "MCOP", en(g.min(), 2),
        f"menor P2P comunitario − C4 de la comunidad en los 13 casos ({g.idxmin()})", FX + "brecha_P2Pcom_menos_C4_COP", SEC)
    pon("pcom__P2Pcom_C4_min_caso", g.idxmin(), "caso", g.idxmin(), "caso con el menor P2P comunitario − C4 (MCOP)",
        FX + "brecha_P2Pcom_menos_C4_COP", SEC)
    pon("pcom__P2Pcom_C4_max", float(g.max()), "MCOP", en(g.max(), 2),
        f"mayor P2P comunitario − C4 de la comunidad en los 13 casos ({g.idxmax()})", FX + "brecha_P2Pcom_menos_C4_COP", SEC)
    pon("pcom__P2Pcom_C4_max_caso", g.idxmax(), "caso", g.idxmax(), "caso con el mayor P2P comunitario − C4 (MCOP)",
        FX + "brecha_P2Pcom_menos_C4_COP", SEC)
    pon("pcom__P2Pcom_C4_pct_min", float(pct.min()), "%", en(pct.min(), 1, " %"),
        f"menor (P2P comunitario − C4) / C4 en los 13 casos ({pct.idxmin()}), a un decimal como en CANON §14.23",
        FX + "brecha_P2Pcom_menos_C4_COP / B_C4_COP", SEC)
    pon("pcom__P2Pcom_C4_pct_min_caso", pct.idxmin(), "caso", pct.idxmin(),
        "caso con el menor (P2P comunitario − C4) / C4", FX + "brecha_P2Pcom_menos_C4_COP / B_C4_COP", SEC)
    pon("pcom__P2Pcom_C4_pct_max", float(pct.max()), "%", en(pct.max(), 1, " %"),
        f"mayor (P2P comunitario − C4) / C4 en los 13 casos ({pct.idxmax()}), a un decimal como en CANON §14.23",
        FX + "brecha_P2Pcom_menos_C4_COP / B_C4_COP", SEC)
    pon("pcom__P2Pcom_C4_pct_max_caso", pct.idxmax(), "caso", pct.idxmax(),
        "caso con el mayor (P2P comunitario − C4) / C4", FX + "brecha_P2Pcom_menos_C4_COP / B_C4_COP", SEC)
    pon("pcom__P2Pcom_C4_suma", suma_pcom, "MCOP", en(suma_pcom, 2),
        "suma de P2P comunitario − C4 de la comunidad en los 13 casos", FX + "brecha_P2Pcom_menos_C4_COP, suma", SEC)
    pon("pcom__P2P_C4_suma", suma_p2p, "MCOP", en(suma_p2p, 2),
        "suma de P2P − C4 (mercado con sus dos supuestos) de la comunidad en los 13 casos, para comparar con "
        "pcom__P2Pcom_C4_suma", F_RES.format("<caso>") + ", P2P − C4, suma", SEC)
    pon("pcom__P2Pcom_C1_min", float(g1.min()), "MCOP", en(g1.min(), 2),
        f"menor P2P comunitario − C1 de la comunidad en los 13 casos ({g1.idxmin()})", FX + "brecha_P2Pcom_menos_C1_COP", SEC)
    pon("pcom__P2Pcom_C1_max", float(g1.max()), "MCOP", en(g1.max(), 2),
        f"mayor P2P comunitario − C1 de la comunidad en los 13 casos ({g1.idxmax()})", FX + "brecha_P2Pcom_menos_C1_COP", SEC)
    for nom, lista in [("caso1", caso1), ("caso2", [c for c in CASOS if c not in caso1])]:
        pon(f"pcom__casos_{nom}", ", ".join(lista), "casos", ", ".join(lista),
            f"casos con el P2P comunitario en el caso {nom[-1]} del art. 20 (CINAC, sin la regla del 10 %)", FX + "caso_art20", SEC)
        pon(f"pcom__n_casos_{nom}", len(lista), "casos", en_int(len(lista)),
            f"número de casos con el P2P comunitario en el caso {nom[-1]} del art. 20", FX + "caso_art20", SEC)
    for x, (suf, rot) in MECS_PC.items():
        s = C[f"signo_P2Pcom_menos_{x}"]
        n = int((s == 1).sum())
        pon(f"pcom__casos_sobre_{suf}", n, "casos de 13", en_int(n),
            f"casos con la comunidad mejor con el P2P comunitario que con {rot} (por más de 1 COP)",
            FX + f"signo_P2Pcom_menos_{x} = 1", SEC)
        if n < len(CASOS):
            for nom, cond in [("sobre", s == 1), ("bajo", s == -1), ("empate", s == 0)]:
                lista = ", ".join(C.index[cond])
                if lista:
                    pon(f"pcom__casos_{nom}_{suf}__lista", lista, "casos", lista,
                        f"casos con el P2P comunitario {'por encima de' if nom == 'sobre' else 'por debajo de' if nom == 'bajo' else 'empatado (a menos de 1 COP) con'} {rot}",
                        FX + f"signo_P2Pcom_menos_{x}", SEC)
    PI = F_PC + ", filas de institución, "
    pon("pcom__pares__n", len(I), "pares", en_int(len(I)),
        "pares institución-caso (12 casos × 5 y SINU × 4, sin Udenar; convención de «25 de 64 bajo C4»)",
        PI + "conteo", SEC)
    for x, (suf, rot) in MECS_PC.items():
        pon(f"pcom__pares__sobre_{suf}", sobre[x], "pares de 64", en_int(sobre[x]),
            f"pares institución-caso con el P2P comunitario por encima de {rot}", PI + f"signo_P2Pcom_menos_{x} = 1", SEC)
    for x, suf in [("C4", "C4"), ("C1", "C1"), ("P2P", "P2P")]:
        b = I[I[f"signo_P2Pcom_menos_{x}"] == -1]
        pon(f"pcom__pares__bajo_{suf}", len(b), "pares de 64", en_int(len(b)),
            f"pares institución-caso con el P2P comunitario por debajo de {MECS_PC[x][1]}",
            PI + f"signo_P2Pcom_menos_{x} = −1", SEC)
    b = I[I.signo_P2Pcom_menos_C4 == -1]
    lista = "; ".join(b.caso + " " + b.institucion)
    pon("pcom__pares__bajo_C4__lista", lista, "pares", lista,
        "pares institución-caso con el P2P comunitario por debajo de C4", PI + "signo_P2Pcom_menos_C4 = −1", SEC)
    n_emp = int((I.signo_P2Pcom_menos_P2P == 0).sum())
    pon("pcom__pares__empates_P2P", n_emp, "pares de 64", en_int(n_emp),
        "pares con el P2P comunitario igual a P2P a menos de 1 COP", PI + "signo_P2Pcom_menos_P2P = 0", SEC)
    for x in ["C4", "P2P"]:
        for nom, cond in [("menor", C.gini_P2Pcom < C[f"gini_{x}"]), ("mayor", C.gini_P2Pcom > C[f"gini_{x}"]),
                          ("igual", C.gini_P2Pcom == C[f"gini_{x}"])]:
            n = int(cond.sum())
            pon(f"gini__casos_P2Pcom_{nom}_que_{x}", n, "casos", en_int(n),
                f"casos en que el Gini del P2P comunitario es {nom} que el de {x}", FX + f"gini_P2Pcom y gini_{x}", SEC)
            if 0 < n < len(CASOS):
                lista = ", ".join(C.index[cond])
                pon(f"gini__casos_P2Pcom_{nom}_que_{x}__lista", lista, "casos", lista,
                    f"casos en que el Gini del P2P comunitario es {nom} que el de {x}", FX + f"gini_P2Pcom y gini_{x}", SEC)
    for k, f_, d in [("min", sh.min, sh.idxmin), ("max", sh.max, sh.idxmax)]:
        pon(f"pcom__sin10_share_{k}", float(f_()), "%", en_int(int(round(float(f_()))), " %"),
            f"{'menor' if k == 'min' else 'mayor'} parte de quitar la regla del 10 % en P2P comunitario − C4, en los casos "
            f"del caso 1 ({d()}); en entero, como share_*", FX + "dec_sin10_COP / P2Pcom_menos_C4_COP, caso_art20 = 1", SEC)
        pon(f"pcom__sin10_share_{k}_caso", d(), "caso", d(),
            f"caso con la {'menor' if k == 'min' else 'mayor'} parte de quitar la regla del 10 % en P2P comunitario − C4",
            FX + "dec_sin10_COP / P2Pcom_menos_C4_COP, caso_art20 = 1", SEC)
    dimp = (C.imp_P2Pcom_menos_C4_COP - C.brecha_P2Pcom_menos_C4_COP) / M
    k_ = dimp.abs().idxmax()
    pon("pcom__imp_cambio_max", float(dimp[k_]), "MCOP", en(dimp[k_], 2),
        f"mayor cambio (en valor absoluto) de P2P comunitario − C4 al pasar al PDE por importación en los dos ({k_})",
        FX + "imp_P2Pcom_menos_C4_COP − brecha_P2Pcom_menos_C4_COP", SEC)
    pon("pcom__imp_cambio_max_caso", k_, "caso", k_, "caso con el mayor cambio de P2P comunitario − C4 con el PDE por "
        "importación", FX + "imp_P2Pcom_menos_C4_COP − brecha_P2Pcom_menos_C4_COP", SEC)
    exige(bool((np.sign(C.imp_P2Pcom_menos_C4_COP) == np.sign(C.brecha_P2Pcom_menos_C4_COP)).all()
               and (np.sign(C.c1todos_P2Pcom_menos_C4_COP) == np.sign(C.brecha_P2Pcom_menos_C4_COP)).all()),
          "p2p_comunitario: alguna sensibilidad cambia el signo de P2Pcom − C4")

    # el orden de E0 con el P2P comunitario en lugar del colectivo y C2 como PPA (Fig. 2 en español)
    b = {m: R.loc["E0", m] for m in ["P2P", "C1", "C3", "C4", "C5"]}
    b["C2"] = Pc.loc["E0", "B_C2_media_COP"]
    b["P2P comunitario"] = C.loc["E0", "P2Pcom_COP"]
    orden = " > ".join(sorted(b, key=lambda m: -b[m]))
    exige(orden == "P2P > P2P comunitario > C1 > C4 > C5 > C2 > C3", f"orden de E0 con el P2P comunitario: {orden}")
    exige(min(abs(b[m] - b[n]) for m in b for n in b if m != n) > 1.0, "orden de E0 con el P2P comunitario: empate")
    pon("mec__E0__orden_P2Pcom", orden, "orden", orden,
        "orden de los mecanismos en E0 por beneficio neto, con el P2P comunitario en lugar del mercado por el colectivo "
        "y C2 como PPA a la media de XM (Fig. 2 en español)",
        F_RES.format("E0") + "; " + F_PPA + ", B_C2_media_COP; " + FC + "P2Pcom_COP", SEC)
    ok("P2P comunitario: ninguna sensibilidad cambia el signo de P2Pcom − C4; orden de E0 sin empates: " + orden)


# ── 15. El P2P comunitario por los dos órdenes y Shapley (añadido el 2026-10-02) ──
CLASES_PC = {"sin10_domina": "quitar la regla, por los dos", "intercambio_domina": "intercambio, por los dos",
             "depende_orden": "depende del orden", "solo_intercambio": "solo intercambio"}
CLASES_PC_EN = {"sin10_domina": "removing the rule, both orders", "intercambio_domina": "exchange, both orders",
                "depende_orden": "order-dependent", "solo_intercambio": "exchange only"}
ROT_CLASES_PC = {"sin10_domina": "quitar la regla del 10 % pone la mayor parte por los dos órdenes",
                 "intercambio_domina": "el intercambio exento pone la mayor parte por los dos órdenes",
                 "depende_orden": "la reforma que pone la mayor parte depende del orden",
                 "solo_intercambio": "toda la ventaja es el intercambio exento (caso 2: quitar la regla no vale nada)"}


def clase_pc(sin10: float, inter: float, sin10_inv: float, inter_inv: float) -> str:
    """La misma regla que `clasifica_ordenes` de p2p_comunitario.py (en COP, empate a 1 COP)."""
    if abs(sin10) <= 1.0 and abs(sin10_inv) <= 1.0:
        return "solo_intercambio"
    d, i = sin10 > inter, sin10_inv > inter_inv
    return "sin10_domina" if (d and i) else "intercambio_domina" if (not d and not i) else "depende_orden"


def p2p_comunitario_ordenes(R: pd.DataFrame) -> None:
    """P2Pcom − C4 por los dos órdenes (directo: quitar la regla del 10 % primero;
    inverso: el intercambio exento primero, con el residual en el caso 2) y por
    Shapley (CANON §14.23, regla de cita como en §14.21)."""
    T = pd.read_csv(lee(F_PC, "e1/PC"), keep_default_na=False, na_values=[""])
    C = T[T.institucion == "comunidad"].set_index("caso")
    nuevas = ["P2Pcom_caso2_COP", "inv_dec_intercambio_COP", "inv_dec_sin10_COP", "sh_dec_sin10_COP",
              "sh_dec_intercambio_COP", "interaccion_ordenes_COP"]
    exige(all(k in T.columns for k in nuevas), "p2p_comunitario: faltan las columnas de los dos órdenes")
    finito(T[nuevas].to_numpy(), "p2p_comunitario: columnas de los dos órdenes")

    # (a) identidades, caso 2 y la cota de v01 con reparto igual (e1/S)
    de = max(float((T.dec_sin10_COP + T.dec_intercambio_COP - T.P2Pcom_menos_C4_COP).abs().max()),
             float((T.inv_dec_sin10_COP + T.inv_dec_intercambio_COP - T.P2Pcom_menos_C4_COP).abs().max()),
             float((T.sh_dec_sin10_COP + T.sh_dec_intercambio_COP - T.P2Pcom_menos_C4_COP).abs().max()),
             float((T.inv_dec_intercambio_COP - (T.P2Pcom_caso2_COP - T.C4_COP)).abs().max()),
             float((T.inv_dec_sin10_COP - (T.P2Pcom_COP - T.P2Pcom_caso2_COP)).abs().max()),
             float((T.sh_dec_sin10_COP - (T.dec_sin10_COP + T.inv_dec_sin10_COP) / 2).abs().max()),
             float((T.interaccion_ordenes_COP - (T.inv_dec_sin10_COP - T.dec_sin10_COP)).abs().max()))
    exige(de <= 1e-3, f"p2p_comunitario: las identidades de los dos órdenes no cierran ({de:.2e} COP)")
    caso2 = [c for c in CASOS if int(C.loc[c, "caso_art20"]) == 2]
    exige(caso2 == ["E4", "E5", "P2"], f"p2p_comunitario: caso 2 en {caso2}")
    for c in caso2:
        r = C.loc[c]
        exige(r.P2Pcom_caso2_COP == r.P2Pcom_COP and r.inv_dec_sin10_COP == 0.0 and r.dec_sin10_COP == 0.0,
              f"{c}: en el caso 2 los dos órdenes no coinciden al peso")
    A = pd.read_csv(lee(F_ATR, "e1/S")).set_index("caso")
    for c in CASOS:
        x, lo, hi = C.loc[c, "P2Pcom_caso2_COP"], A.loc[c, "v01_igual_min"], A.loc[c, "v01_igual_max"]
        exige(lo - 1.0 <= x <= hi + 1.0, f"{c}: P2Pcom caso 2 fuera de [v01_igual_min, v01_igual_max]")
    for col in nuevas:
        sumas = T[T.institucion != "comunidad"].groupby("caso")[col].sum().reindex(CASOS)
        exige(float((sumas - C[col]).abs().max()) <= 1e-3, f"p2p_comunitario: la comunidad no es la suma en {col}")
    ok("P2P comunitario por los dos órdenes: las identidades directa, inversa y de Shapley cierran fila a fila "
       f"(≤ {de:.1e} COP); en E4, E5 y P2 los dos órdenes coinciden al peso; P2Pcom caso 2 de la comunidad cae en "
       "[v01_igual_min, v01_igual_max] de e1/S en los 13 casos; la comunidad es la suma en las columnas nuevas")

    # (b) la cuarta tabla de CANON §14.23 y el texto
    t4 = tablas(seccion("### 14.23 ·"))[3]

    def igual(v, celda, d, qué):
        exige(abs(v - num_es(celda)) <= 0.5 * 10 ** -d + 1e-9, f"CANON §14.23 {qué}: {v:.6f} no redondea a {celda}")

    clase = {}
    for c in CASOS:
        r = C.loc[c]
        tot = r.P2Pcom_menos_C4_COP
        clase[c] = clase_pc(r.dec_sin10_COP, r.dec_intercambio_COP, r.inv_dec_sin10_COP, r.inv_dec_intercambio_COP)
        exige(int(t4.loc[c, "Caso del art. 20"]) == int(r.caso_art20), f"CANON §14.23 {c}: caso del art. 20 (tabla 4)")
        for col, k in [("P2Pcom − C4", "P2Pcom_menos_C4_COP"), ("P2Pcom caso 2", "P2Pcom_caso2_COP"),
                       ("Directo: quitar el 10 %", "dec_sin10_COP"), ("Directo: intercambio", "dec_intercambio_COP"),
                       ("Inverso: intercambio", "inv_dec_intercambio_COP"), ("Inverso: quitar el 10 %", "inv_dec_sin10_COP"),
                       ("Shapley: quitar el 10 %", "sh_dec_sin10_COP"), ("Shapley: intercambio", "sh_dec_intercambio_COP"),
                       ("Interacción", "interaccion_ordenes_COP")]:
            igual(r[k] / M, t4.loc[c, col], 3, f"{c} {col}")
        for col, k in [("Quitar el 10 %, directo (%)", "dec_sin10_COP"), ("Quitar el 10 %, inverso (%)", "inv_dec_sin10_COP"),
                       ("Quitar el 10 %, Shapley (%)", "sh_dec_sin10_COP")]:
            igual(100 * r[k] / tot, t4.loc[c, col], 0, f"{c} {col}")
        exige(t4.loc[c, "Clase"] == CLASES_PC[clase[c]], f"CANON §14.23 {c}: clase {t4.loc[c, 'Clase']!r}")
    caso1 = [c for c in CASOS if c not in caso2]
    pct = {k: 100 * C.loc[caso1, k] / C.loc[caso1, "P2Pcom_menos_C4_COP"]
           for k in ["dec_sin10_COP", "inv_dec_sin10_COP", "sh_dec_sin10_COP"]}
    grupos = {k: [c for c in CASOS if clase[c] == k] for k in CLASES_PC}
    dom, dep = grupos["sin10_domina"], grupos["depende_orden"]
    # cada reforma por sí sola, en los casos que dependen del orden: quitar la regla primero (directo) e
    # intercambio primero (inverso)
    solo = pd.concat([pct["dec_sin10_COP"][dep], 100 - pct["inv_dec_sin10_COP"][dep]])
    S = {k: float(C[k].sum() / M) for k in ["P2Pcom_menos_C4_COP", "dec_sin10_COP", "inv_dec_sin10_COP", "sh_dec_sin10_COP",
                                             "dec_intercambio_COP", "inv_dec_intercambio_COP", "sh_dec_intercambio_COP"]}
    it = C.loc[caso1, "interaccion_ordenes_COP"] / M
    exige(bool((it < 0).all()) and bool((C.loc[caso2, "interaccion_ordenes_COP"] == 0).all()),
          "p2p_comunitario: la interacción no es negativa en el caso 1 y nula en el caso 2")
    ent = lambda v: int(round(float(v)))  # noqa: E731
    p = {k: pct[k] for k in pct}
    frases = [
        f"por el orden directo, entre el {ent(p['dec_sin10_COP'].min())} % ({p['dec_sin10_COP'].idxmin()}) y el "
        f"{ent(p['dec_sin10_COP'].max())} % ({p['dec_sin10_COP'].idxmax()}) de P2Pcom − C4; por el inverso, entre el "
        f"{ent(p['inv_dec_sin10_COP'].min())} % ({p['inv_dec_sin10_COP'].idxmin()}) y el {ent(p['inv_dec_sin10_COP'].max())} % "
        f"({p['inv_dec_sin10_COP'].idxmax()}); por Shapley, entre el {ent(p['sh_dec_sin10_COP'].min())} % "
        f"({p['sh_dec_sin10_COP'].idxmin()}) y el {ent(p['sh_dec_sin10_COP'].max())} % ({p['sh_dec_sin10_COP'].idxmax()})",
        f"por los dos órdenes** en {', '.join(dom[:-1])} y {dom[-1]}, del {ent(p['dec_sin10_COP'][dom].min())} al "
        f"{ent(p['dec_sin10_COP'][dom].max())} % por el directo y del {ent(p['inv_dec_sin10_COP'][dom].min())} al "
        f"{ent(p['inv_dec_sin10_COP'][dom].max())} % por el inverso",
        f"**depende del orden** en {', '.join(dep[:-1])} y {dep[-1]}",
        f"deja entre el {ent(solo.min())} y el {ent(solo.max())} % de la ventaja",
        f"**todo es intercambio** en {', '.join(caso2[:-1])} y {caso2[-1]}",
        f"de los {es_txt(S['P2Pcom_menos_C4_COP'], 2)} MCOP quitar la regla pone {es_txt(S['dec_sin10_COP'], 2)} por el orden "
        f"directo, {es_txt(S['inv_dec_sin10_COP'], 2)} por el inverso y {es_txt(S['sh_dec_sin10_COP'], 2)} por Shapley, y el "
        f"intercambio exento {es_txt(S['dec_intercambio_COP'], 2)}, {es_txt(S['inv_dec_intercambio_COP'], 2)} y "
        f"{es_txt(S['sh_dec_intercambio_COP'], 2)}",
        f"(de {es_txt(it.max(), 2)} en {it.idxmax()} a {es_txt(it.min(), 2)} MCOP en {it.idxmin()})",
        f"se cita con la del inverso ({ent(p['inv_dec_sin10_COP'].min())} a {ent(p['inv_dec_sin10_COP'].max())} %) o con la de "
        f"Shapley ({ent(p['sh_dec_sin10_COP'].min())} a {ent(p['sh_dec_sin10_COP'].max())} %)",
    ]
    exige(not grupos["intercambio_domina"], "p2p_comunitario: hay casos con el intercambio dominando por los dos órdenes")
    sec = seccion("### 14.23 ·")
    for f_ in frases:
        exige(f_ in sec, f"CANON §14.23 no escribe «{f_}»")
    ok("P2P comunitario por los dos órdenes: la cuarta tabla de CANON §14.23 a sus decimales y con su clase en los 13 "
       "casos; los rangos de la parte de quitar la regla por los dos órdenes y Shapley, los tres grupos, las sumas y la "
       "interacción de su texto")

    # (c) las claves
    SEC = "§14.23"
    FC = F_PC + ", fila comunidad, "
    for c in CASOS:
        r = C.loc[c]
        tot = r.P2Pcom_menos_C4_COP
        for k, col, dfn in [
                ("inv_sin10", "inv_dec_sin10_COP", "orden inverso: lo que vale quitar la regla del 10 % después del "
                 "intercambio exento (P2P comunitario − P2P comunitario en el caso 2)"),
                ("inv_intercambio", "inv_dec_intercambio_COP", "orden inverso: lo que vale el intercambio exento con la "
                 "regla del 10 % vigente (P2P comunitario en el caso 2 − C4)"),
                ("sh_sin10", "sh_dec_sin10_COP", "Shapley (media de los dos órdenes): quitar la regla del 10 %"),
                ("sh_intercambio", "sh_dec_intercambio_COP", "Shapley (media de los dos órdenes): el intercambio exento"),
                ("interaccion", "interaccion_ordenes_COP", "interacción de las dos reformas: quitar la regla por el orden "
                 "inverso menos por el directo")]:
            pon(f"pcom__{c}__{k}", r[col] / M, "MCOP", en(r[col] / M, 2),
                f"{dfn}, término de P2P comunitario − C4, PDE igual, caso {c}", FC + col, SEC)
        for k, col, dfn in [("sin10_pct_dir", "dec_sin10_COP", "orden directo"),
                            ("sin10_pct_inv", "inv_dec_sin10_COP", "orden inverso"),
                            ("sin10_pct_sh", "sh_dec_sin10_COP", "Shapley")]:
            v = 100 * r[col] / tot
            pon(f"pcom__{c}__{k}", v, "%", en_int(ent(v), " %"),
                f"parte de quitar la regla del 10 % en P2P comunitario − C4 por el {dfn}, en entero, caso {c}",
                FC + f"{col} / P2Pcom_menos_C4_COP", SEC)
        pon(f"pcom__{c}__orden_clase", CLASES_PC[clase[c]], "clase", CLASES_PC_EN[clase[c]],
            f"clase del caso con los dos órdenes ({ROT_CLASES_PC[clase[c]]}), caso {c}",
            FC + "dec_* e inv_dec_*", SEC)
        pon(f"com__{c}__P2Pcom_caso2", r.P2Pcom_caso2_COP / M, "MCOP", en(r.P2Pcom_caso2_COP / M, 2),
            f"beneficio neto de la comunidad con el P2P comunitario y el residual en el caso 2 (κ·Cv + Θ, la regla del "
            f"10 % vigente, PDE igual; orden inverso), caso {c}", FC + "P2Pcom_caso2_COP", SEC)
        for x, suf, rot in [("C4", "C4", "C4 de la hoja Resumen (= pcom__<caso>__inv_intercambio a 1 COP, que usa el C4 vuelto a liquidar)"), ("P2P", "P2P", "P2P (con sus dos supuestos)"),
                            ("C1", "C1", "C1")]:
            v = (r.P2Pcom_caso2_COP - r[f"B_{x}_COP"]) / M
            pon(f"com__{c}__P2Pcom_caso2_{suf}", v, "MCOP", en(v, 2),
                f"P2P comunitario en el caso 2 − {rot} de la comunidad, caso {c}", FC + f"P2Pcom_caso2_COP − B_{x}_COP", SEC)
        exige(abs(valor_de(f"com__{c}__P2Pcom_caso2_C4") - valor_de(f"pcom__{c}__inv_intercambio")) <= 1e-6,
              f"{c}: P2Pcom caso 2 − C4 ≠ intercambio del orden inverso")

    FX = F_PC + ", filas comunidad, "
    for k, (rot_c, lista) in {"sin10_domina": (ROT_CLASES_PC["sin10_domina"], grupos["sin10_domina"]),
                              "depende": (ROT_CLASES_PC["depende_orden"], grupos["depende_orden"]),
                              "solo_intercambio": (ROT_CLASES_PC["solo_intercambio"], grupos["solo_intercambio"]),
                              "intercambio_domina": (ROT_CLASES_PC["intercambio_domina"],
                                                     grupos["intercambio_domina"])}.items():
        pon(f"pcom__orden__n_casos_{k}", len(lista), "casos de 13", en_int(len(lista)),
            f"número de casos en que {rot_c}", FX + "dec_* e inv_dec_*", SEC)
        if lista:
            pon(f"pcom__orden__casos_{k}", ", ".join(lista), "casos", ", ".join(lista), f"casos en que {rot_c}",
                FX + "dec_* e inv_dec_*", SEC)
    for k, col, rot in [("dir", "dec_sin10_COP", "orden directo"), ("inv", "inv_dec_sin10_COP", "orden inverso"),
                        ("sh", "sh_dec_sin10_COP", "Shapley")]:
        s = pct[col]
        for m_, f_, d in [("min", s.min, s.idxmin), ("max", s.max, s.idxmax)]:
            if k == "dir":           # pcom__sin10_share_* ya existe (orden directo); aquí van el inverso y Shapley
                continue
            pon(f"pcom__{k}_sin10_share_{m_}", float(f_()), "%", en_int(ent(f_()), " %"),
                f"{'menor' if m_ == 'min' else 'mayor'} parte de quitar la regla del 10 % en P2P comunitario − C4 por el "
                f"{rot}, en los casos del caso 1 ({d()}); en entero", FX + f"{col} / P2Pcom_menos_C4_COP, caso_art20 = 1", SEC)
            pon(f"pcom__{k}_sin10_share_{m_}_caso", d(), "caso", d(),
                f"caso con la {'menor' if m_ == 'min' else 'mayor'} parte de quitar la regla del 10 % por el {rot}",
                FX + f"{col} / P2Pcom_menos_C4_COP, caso_art20 = 1", SEC)
        if k == "sh":
            v = C.loc[caso1, col] / M
            for m_, f_, d in [("min", v.min, v.idxmin), ("max", v.max, v.idxmax)]:
                pon(f"pcom__sh_sin10_{m_}", float(f_()), "MCOP", en(f_(), 2),
                    f"{'menor' if m_ == 'min' else 'mayor'} parte de quitar la regla del 10 % por Shapley en los casos del "
                    f"caso 1 ({d()})", FX + f"{col}, caso_art20 = 1", SEC)
                pon(f"pcom__sh_sin10_{m_}_caso", d(), "caso", d(),
                    f"caso con la {'menor' if m_ == 'min' else 'mayor'} parte de quitar la regla del 10 % por Shapley (MCOP)",
                    FX + f"{col}, caso_art20 = 1", SEC)
    for k, serie, rot in [("sin10_domina__dir", p["dec_sin10_COP"][dom], "por el orden directo, en los casos en que quitar "
                           "la regla pone la mayor parte por los dos órdenes"),
                          ("sin10_domina__inv", p["inv_dec_sin10_COP"][dom], "por el orden inverso, en los casos en que "
                           "quitar la regla pone la mayor parte por los dos órdenes"),
                          ("depende__solo", solo, "de cualquiera de las dos reformas por sí sola (la que va primero), en "
                           "los casos que dependen del orden")]:
            for m_, v in [("min", float(serie.min())), ("max", float(serie.max()))]:
                pon(f"pcom__orden__{k}_share_{m_}", v, "%", en_int(ent(v), " %"),
                    f"{'menor' if m_ == 'min' else 'mayor'} parte de P2P comunitario − C4 {rot}; en entero",
                    FX + "dec_sin10_COP, inv_dec_sin10_COP / P2Pcom_menos_C4_COP", SEC)
    for k, col, rot in [("sin10_suma", "dec_sin10_COP", "quitar la regla del 10 %, orden directo"),
                        ("intercambio_suma", "dec_intercambio_COP", "el intercambio exento, orden directo"),
                        ("inv_sin10_suma", "inv_dec_sin10_COP", "quitar la regla del 10 %, orden inverso"),
                        ("inv_intercambio_suma", "inv_dec_intercambio_COP", "el intercambio exento, orden inverso"),
                        ("sh_sin10_suma", "sh_dec_sin10_COP", "quitar la regla del 10 %, Shapley"),
                        ("sh_intercambio_suma", "sh_dec_intercambio_COP", "el intercambio exento, Shapley")]:
        v = S[col]
        pon(f"pcom__{k}", v, "MCOP", en(v, 2),
            f"suma en los 13 casos de lo que pone {rot} en P2P comunitario − C4 (de pcom__P2Pcom_C4_suma)",
            FX + f"{col}, suma", SEC)
    for m_, f_, d in [("min", it.min, it.idxmin), ("max", it.max, it.idxmax)]:
        pon(f"pcom__interaccion_{m_}", float(f_()), "MCOP", en(f_(), 2),
            f"{'más negativa' if m_ == 'min' else 'menos negativa'} interacción de las dos reformas en los casos del caso 1 "
            f"({d()}); nula en el caso 2", FX + "interaccion_ordenes_COP, caso_art20 = 1", SEC)
        pon(f"pcom__interaccion_{m_}_caso", d(), "caso", d(),
            f"caso con la {'más negativa' if m_ == 'min' else 'menos negativa'} interacción de las dos reformas",
            FX + "interaccion_ordenes_COP, caso_art20 = 1", SEC)


# ── 16. Las mediciones rehechas para el P2P colectivo y C2 (punto PD; añadido el 2026-10-02) ──
F_PD = "p2p_colectivo_derivados_2026-10-02/{}"
ESC_PD = {"P2Pcol": "P2P colectivo", "C2ppa": "C2 (PPA)", "P2P": "el mercado P2P"}


def p2p_colectivo_derivados(R: pd.DataFrame) -> None:
    """Mes a mes, σ, COT, comercializador único, retiro de un miembro, factor de
    coincidencia, precio de la justicia, umbral, 11 fronteras y techo, rehechos
    para el P2P colectivo (el P2P comunitario de §14.23, renombrado) y para C2
    como PPA (CANON §14.24)."""
    SEC = "§14.24"
    T = {k: pd.read_csv(lee(F_PD.format(k), "e1/PD"), keep_default_na=False, na_values=[""])
         for k in ["mensual_13casos.csv", "sigma_13casos.csv", "cot_13casos.csv", "comercializador_13casos.csv",
                   "retiro_comunidad.csv", "retiro_quienes_quedan.csv", "coincidencia_13casos.csv", "otros_13casos.csv"]}
    for k, X in T.items():
        num = X.select_dtypes(include=[np.number])
        exige(not X.to_csv().lower().count("cedenar"), f"{k}: nombra a un comercializador")
        exige(bool(np.isfinite(num.to_numpy(dtype=float)[~np.isnan(num.to_numpy(dtype=float))]).all()), f"{k}: no finito")
    me = T["mensual_13casos.csv"]
    com = me[me.institucion == "comunidad"]
    ins = me[me.institucion != "comunidad"]
    exige(len(com) == 117 and len(ins) == 576, f"mes a mes: {len(com)} meses-caso y {len(ins)} institución-mes")

    # (a) los meses suman el horizonte de la comunidad (claves de los bloques 13 y 14) y el mercado es el del canon
    for c in CASOS:
        x = com[com.caso == c]
        exige(len(x) == 9, f"{c}: {len(x)} meses")
        exige(abs(x.P2Pcol_COP.sum() / M - valor_de(f"com__{c}__P2Pcom")) <= 1e-6, f"{c}: los meses del P2P colectivo")
        exige(abs(x.C2ppa_COP.sum() / M - valor_de(f"com__{c}__C2ppa")) <= 1e-6, f"{c}: los meses de C2")
        for m_ in ["P2P", "C1", "C4", "C5"]:
            exige(abs(x[f"B_{m_}_COP"].sum() - R.loc[c, m_]) <= max(2.0, 2e-7 * abs(R.loc[c, "P2P"])),
                  f"{c}: los meses de {m_} no suman la hoja Resumen")
    sob = {(q, x): int((com[f"signo_{q}_menos_{x}"] == 1).sum()) for q, x in
           [("P2P", "C4"), ("P2P", "C1"), ("P2P", "C5"), ("P2Pcol", "C4"), ("P2Pcol", "C1"), ("P2Pcol", "C5"),
            ("P2Pcol", "P2P"), ("C2ppa", "C4"), ("C2ppa", "C1"), ("C2ppa", "C5")]}
    exige((sob[("P2P", "C4")], sob[("P2P", "C1")], sob[("P2P", "C5")]) == (116, 116, 117),
          f"mes a mes: el mercado sobre C4, C1 y C5 en {sob}")
    ok("P2P colectivo derivado (e1/PD): los 117 meses-caso suman, por caso, el P2P colectivo y C2 de los bloques 13 y 14 "
       "(≤ 1e-6 MCOP) y P2P, C1, C4 y C5 la hoja Resumen; el mercado queda sobre C4 en 116, sobre C1 en 116 y sobre C5 en "
       "117 meses (CANON §12 y §14.9)")

    # (b) las tablas de CANON §14.24
    tb = tablas(seccion("### 14.24 ·"))
    exige(len(tb) == 7, f"CANON §14.24: {len(tb)} tablas, no 7")
    t1, t2, t3, t4, t5, t6, t7 = tb
    rot = {"P2P": "P2P", "P2Pcol": "P2P colectivo", "C2ppa": "C2"}
    for (q, x), n in sob.items():
        exige(int(num_es(t1.loc[f"{rot[q]} − {x}", "Meses con la brecha positiva (de 117)"])) == n,
              f"CANON §14.24, tabla 1: {q} − {x}")

    def igual(v, celda, d, qué):
        exige(abs(v - num_es(celda)) <= 0.5 * 10 ** -d + 1e-9, f"CANON §14.24 {qué}: {v:.6f} no redondea a {celda}")

    ct = T["cot_13casos.csv"]
    ctc = ct[ct.institucion == "comunidad"].set_index("caso")
    for c in CASOS:
        for col, k in [("ΔP2P colectivo", "d_P2Pcol_COP"), ("ΔC4", "d_C4_COP"), ("ΔC1", "d_C1_COP"),
                       ("P2P colectivo − C4", "P2Pcol_menos_C4_COP"), ("P2P colectivo − C1", "P2Pcol_menos_C1_COP"),
                       ("C2 − C4", "C2ppa_menos_C4_COP"), ("C2 − C1", "C2ppa_menos_C1_COP")]:
            igual(ctc.loc[c, k] / M, t4.loc[c, col], 3, f"tabla 4, {c} {col}")
    co = T["coincidencia_13casos.csv"].set_index("caso")
    ot = T["otros_13casos.csv"].set_index("caso")
    for c in CASOS:
        igual(co.loc[c, "coincidencia_P2Pcol"], t7.loc[c, "Coincidencia, P2P colectivo"], 3, f"tabla 7, {c}")
        igual(100 * ot.loc[c, "pof_P2Pcol"], t7.loc[c, "Precio de la justicia del P2P colectivo (%)"], 1, f"tabla 7, {c}")
        igual(ot.loc[c, "once_fronteras_P2Pcol_menos_P2P_COP"] / M, t7.loc[c, "11 fronteras: P2P colectivo − P2P"], 3,
              f"tabla 7, {c}")
        cl = {"domina": "P2P colectivo domina"}.get(ot.loc[c, "clase_P2Pcol"], ot.loc[c, "clase_P2Pcol"])
        exige(cl == t7.loc[c, "Clase"], f"CANON §14.24, tabla 7: clase de {c}")
    rq = T["retiro_quienes_quedan.csv"]
    exige(int(num_es(t6.loc["Todas", "Se mueve menos con el P2P colectivo"])) == int((rq.mas_estable == "P2Pcol").sum()),
          "CANON §14.24, tabla 6: pares más estables")
    # el precio de la justicia del mercado y del P2P colectivo, desde la hoja Resumen y el bloque 14
    for c in CASOS:
        w4 = R.loc[c, "C4"]
        exige(abs(ot.loc[c, "pof_P2P"] - (R.loc[c, "P2P"] - w4) / R.loc[c, "P2P"]) <= 1e-6, f"{c}: precio de la justicia")
        wx = valor_de(f"com__{c}__P2Pcom") * M
        exige(abs(ot.loc[c, "pof_P2Pcol"] - (wx - w4) / wx) <= 1e-6, f"{c}: precio de la justicia del P2P colectivo")
    ok("P2P colectivo derivado: las tablas 1, 4, 6 y 7 de CANON §14.24 a sus decimales (meses, COT, retiro, "
       "coincidencia, precio de la justicia y 11 fronteras); el precio de la justicia del mercado y del P2P colectivo "
       "= (W − W_C4) / W con la hoja Resumen y el bloque 14")

    FM = F_PD.format("mensual_13casos.csv") + ", filas comunidad, "
    # ── mes a mes
    pon("pcom__mes__n", len(com), "meses-caso", en_int(len(com)), "meses-caso de la comunidad (13 casos × 9 meses)",
        FM.rstrip(", "), SEC)
    for (q, x), n in sob.items():
        pre = {"P2P": "pcom__mes__mercado", "P2Pcol": "pcom__mes", "C2ppa": "ppa__mes"}[q]
        pon(f"{pre}__sobre_{x}", n, "meses", en_int(n), f"meses-caso (de 117) con {ESC_PD[q]} por encima de {x} "
            "(empate a 1 COP no cuenta)", FM + f"signo_{q}_menos_{x}", SEC)
    emp = int((com.signo_P2Pcol_menos_P2P == 0).sum())
    pon("pcom__mes__empates_P2P", emp, "meses", en_int(emp), "meses-caso con el P2P colectivo empatado con el mercado "
        "(a 1 COP)", FM + "signo_P2Pcol_menos_P2P", SEC)
    neg = com[com.signo_P2Pcol_menos_C1 < 0]
    lst = "; ".join(f"{a} {b}" for a, b in zip(neg.caso, neg.mes))
    pon("pcom__mes__bajo_C1__lista", lst, "lista", lst, "meses-caso con el P2P colectivo por debajo de C1",
        FM + "signo_P2Pcol_menos_C1", SEC)
    for (a, b), v in zip(zip(neg.caso, neg.mes), neg.P2Pcol_menos_C1_COP):
        pon(f"pcom__mes__bajo_C1__{a}_{b}", float(v), "COP", en(v, 0), f"P2P colectivo − C1 de la comunidad en {a}, {b}",
            FM + "P2Pcol_menos_C1_COP", SEC)
    k_ = com.P2Pcol_menos_C4_COP.idxmin()
    pon("pcom__mes__min_C4", float(com.loc[k_, "P2Pcol_menos_C4_COP"]), "COP", en(com.loc[k_, "P2Pcol_menos_C4_COP"], 0),
        f"menor P2P colectivo − C4 de la comunidad en un mes ({com.loc[k_, 'caso']}, {com.loc[k_, 'mes']})",
        FM + "P2Pcol_menos_C4_COP", SEC)
    pon("pcom__mes__min_C4_caso", f"{com.loc[k_, 'caso']} {com.loc[k_, 'mes']}", "caso y mes",
        f"{com.loc[k_, 'caso']} {com.loc[k_, 'mes']}", "mes-caso con el menor P2P colectivo − C4", FM + "P2Pcol_menos_C4_COP", SEC)
    for x in ["C4", "C1"]:
        cs_ = ", ".join(c for c in CASOS if (com[(com.caso == c)][f"signo_C2ppa_menos_{x}"] == 1).any())
        pon(f"ppa__mes__sobre_{x}__casos", cs_, "lista", cs_, f"casos con algún mes en que C2 supera a {x}",
            FM + f"signo_C2ppa_menos_{x}", SEC)
    FI = F_PD.format("mensual_13casos.csv") + ", filas de institución, "
    pon("pcom__mes_inst__n", len(ins), "pares institución-mes", en_int(len(ins)), "pares institución-mes (64 × 9)",
        FI.rstrip(", "), SEC)
    for q, x in [("P2Pcol", "C4"), ("P2Pcol", "C1"), ("P2P", "C4"), ("P2P", "C1"), ("C2ppa", "C4"), ("C2ppa", "C1")]:
        pre = {"P2P": "pcom__mes_inst__mercado", "P2Pcol": "pcom__mes_inst", "C2ppa": "ppa__mes_inst"}[q]
        n = int((ins[f"signo_{q}_menos_{x}"] == 1).sum())
        pon(f"{pre}__sobre_{x}", n, "pares", en_int(n), f"pares institución-mes (de 576) con {ESC_PD[q]} por encima de {x}",
            FI + f"signo_{q}_menos_{x}", SEC)
    for t, tn in [("t_generacion", "generacion"), ("t_bolsa", "bolsa"), ("t_demanda", "demanda")]:
        for lv in ["bajo", "medio", "alto"]:
            x = com[com[t] == lv]
            exige(len(x) == 39, f"tercil {tn} {lv}: {len(x)} meses")
            for pre, col, quien in [("pcom__tercil", "P2Pcol_menos_C4_COP", "el P2P colectivo"),
                                    ("pcom__tercil_mercado", "P2P_menos_C4_COP", "el mercado")]:
                v = float(x[col].mean() / M)
                pon(f"{pre}__{tn}__{lv}", v, "MCOP", en(v, 2), f"ventaja media por mes de {quien} sobre C4, tercil {lv} "
                    f"de {tn} (39 meses de los 13 casos)", FM + f"{col}, {t}", SEC)
            igual(float(x.P2Pcol_menos_C4_COP.mean() / M), t2.loc[lv, f"P2P colectivo − C4, por {tn.replace('generacion', 'generación')}"],
                  2, f"tabla 2, {tn} {lv}")

    # ── σ
    FS = F_PD.format("sigma_13casos.csv") + ", "
    sg = T["sigma_13casos.csv"]
    cc = ["C1", "C4", "C5", "C3", "C2ppa"]
    sgc = sg[sg.institucion == "comunidad"]
    n_com = int(sum(sgc[f"cambia_P2Pcol_menos_{x}"].sum() for x in cc))
    pon("pcom__sigma__brechas_comunidad_cambian", n_com, "brechas", en_int(n_com), "brechas de la comunidad del P2P "
        "colectivo frente a C1, C2, C3, C4 y C5 que cambian de signo con σ = 0, 0,5 o 1 (39 corridas)",
        FS + "filas comunidad, cambia_P2Pcol_menos_*", SEC)
    rel = 100 * (sgc.P2Pcol_COP / sgc.P2Pcol_base_COP - 1)
    for m_, v in [("min", float(rel.min())), ("max", float(rel.max()))]:
        pon(f"pcom__sigma__cambio_pct_{m_}", v, "%", en(v, 2, " %"), f"{'menor' if m_ == 'min' else 'mayor'} cambio del "
            "P2P colectivo de la comunidad con σ frente al canon (39 corridas)", FS + "P2Pcol_COP / P2Pcol_base_COP", SEC)
    for s_, k in [(0.0, "0"), (0.5, "05"), (1.0, "1")]:
        x = sg[(sg.sigma == s_) & (sg.institucion != "comunidad")]
        cam = [f"{r.caso} {r.institucion} − {('C2' if y == 'C2ppa' else y)}" for _, r in x.iterrows() for y in cc
               if r[f"cambia_P2Pcol_menos_{y}"]]
        pon(f"pcom__sigma__{k}__pares_cambian", len(cam), "pares", en_int(len(cam)),
            f"pares institución-brecha del P2P colectivo (frente a C1, C2, C3, C4 y C5) que cambian de signo con σ = "
            f"{es_txt(s_, 1)}", FS + "filas de institución, cambia_P2Pcol_menos_*", SEC)
        igual(len(cam), t3.loc[es_txt(s_, 1), "Pares institución-brecha que cambian (de 64 × 5)"], 0, f"tabla 3, σ {s_}")
        pon(f"pcom__sigma__{k}__pares_cambian__lista", "; ".join(cam), "lista", "; ".join(cam),
            f"los pares que cambian con σ = {es_txt(s_, 1)}", FS + "filas de institución", SEC)

    # ── COT
    FC_ = F_PD.format("cot_13casos.csv") + ", filas comunidad, "
    for c in CASOS:
        for k, col, dfn in [("dP2Pcol", "d_P2Pcol_COP", "cambio del P2P colectivo"),
                            ("P2Pcol_C4", "P2Pcol_menos_C4_COP", "P2P colectivo − C4"),
                            ("P2Pcol_C1", "P2Pcol_menos_C1_COP", "P2P colectivo − C1")]:
            v = float(ctc.loc[c, col] / M)
            pon(f"pcom__cot__{c}__{k}", v, "MCOP", en(v, 3), f"{dfn} con el COT en la deducción, caso {c}", FC_ + col, SEC)
    k_ = ctc.d_P2Pcol_COP.idxmin()
    pon("pcom__cot__baja_max", float(ctc.loc[k_, "d_P2Pcol_COP"] / M), "MCOP", en(ctc.loc[k_, "d_P2Pcol_COP"] / M, 2),
        f"mayor baja del P2P colectivo con el COT ({k_})", FC_ + "d_P2Pcol_COP", SEC)
    pon("pcom__cot__baja_max_caso", k_, "caso", k_, "caso con la mayor baja del P2P colectivo con el COT", FC_ + "d_P2Pcol_COP", SEC)
    v = float(100 * ctc.loc[k_, "d_P2Pcol_COP"] / (ctc.loc[k_, "P2Pcol_cot_COP"] - ctc.loc[k_, "d_P2Pcol_COP"]))
    pon("pcom__cot__baja_max_pct", v, "%", en(v, 2, " %"), "mayor baja del P2P colectivo con el COT, en % de su valor",
        FC_ + "d_P2Pcol_COP / P2Pcol_base_COP", SEC)
    cti = ct[ct.institucion != "comunidad"]
    for pre, q, xs in [("pcom", "P2Pcol", ["C1", "C4", "C5", "C3", "C2ppa", "P2P"]), ("ppa", "C2ppa", ["C1", "C4"])]:
        n1 = int(sum(ctc[f"cambia_{q}_menos_{x}"].sum() for x in xs))
        n2 = int(sum(cti[f"cambia_{q}_menos_{x}"].sum() for x in xs))
        pon(f"{pre}__cot__brechas_comunidad_cambian", n1, "brechas", en_int(n1), f"brechas de la comunidad de "
            f"{ESC_PD[q]} que cambian de signo con el COT", FC_ + f"cambia_{q}_menos_*", SEC)
        pon(f"{pre}__cot__pares_cambian", n2, "pares", en_int(n2), f"pares institución-caso de {ESC_PD[q]} que cambian "
            "de signo con el COT", F_PD.format("cot_13casos.csv") + ", filas de institución", SEC)
    cam = [f"{r.caso} {r.institucion} − {x}" for _, r in cti.iterrows() for x in ["C1", "C4"] if r[f"cambia_C2ppa_menos_{x}"]]
    pon("ppa__cot__pares_cambian__lista", "; ".join(cam), "lista", "; ".join(cam), "pares de C2 que cambian con el COT",
        F_PD.format("cot_13casos.csv") + ", filas de institución", SEC)

    # ── comercializador único
    cm = T["comercializador_13casos.csv"]
    cmc = cm[cm.institucion == "comunidad"]
    cmi = cm[cm.institucion != "comunidad"]
    FK = F_PD.format("comercializador_13casos.csv") + ", "
    for v_ in ["A", "B"]:
        x = cmc[cmc.variante == v_].set_index("caso")
        for c in CASOS:
            for k, col in [("P2Pcol_C4", "P2Pcol_menos_C4_COP"), ("P2Pcol_C1", "P2Pcol_menos_C1_COP"),
                           ("C2ppa_C4", "C2ppa_menos_C4_COP")]:
                pre = "ppa" if k.startswith("C2") else "pcom"
                kk = k.replace("C2ppa_", "") if pre == "ppa" else k
                val = float(x.loc[c, col] / M)
                pon(f"{pre}__com{v_}__{c}__{kk}", val, "MCOP", en(val, 3), f"{ESC_PD['C2ppa' if pre == 'ppa' else 'P2Pcol']} − "
                    f"{col.split('_menos_')[1][:2]} de la comunidad con las cinco en el comercializador {v_}, caso {c}",
                    FK + f"variante {v_}, filas comunidad, {col}", SEC)
                igual(val, t5.loc[c, f"{v_}: C2 − C4" if pre == "ppa" else (f"{v_}: P2P colectivo − C1" if k.endswith("C1")
                      else f"{v_}: − C4")], 3, f"tabla 5, {v_} {c} {k}")
        xi = cmi[cmi.variante == v_]
        for pre, q in [("pcom", "P2Pcol"), ("ppa", "C2ppa")]:
            cam = [f"{r.caso} {r.institucion} − {y}" for _, r in xi.iterrows() for y in ["C1", "C4", "C5"]
                   if r[f"cambia_{q}_menos_{y}"]]
            pon(f"{pre}__com{v_}__pares_cambian", len(cam), "pares", en_int(len(cam)), f"pares institución-caso de "
                f"{ESC_PD[q]} (frente a C1, C4 y C5) que cambian de signo con las cinco en {v_}",
                FK + f"variante {v_}, filas de institución", SEC)
            pon(f"{pre}__com{v_}__pares_cambian__lista", "; ".join(cam) or "ninguno", "lista", "; ".join(cam) or "ninguno",
                f"los pares de {ESC_PD[q]} que cambian con las cinco en {v_}", FK + f"variante {v_}", SEC)
        err = float(x[["P2P_flujos_canon_menos_contrafactico_COP",
                       "col_viejo_flujos_canon_menos_contrafactico_COP"]].abs().to_numpy().max() / M)
        pon(f"pcom__com{v_}__flujos_fijos_err", err, "MCOP", en(err, 3), f"lo que la aproximación de los flujos fijos "
            f"deja el mercado y el viejo colectivo de la comunidad del contrafáctico re-simulado, con las cinco en {v_} "
            "(como mucho, 13 casos)", FK + "P2P_flujos_canon_menos_contrafactico_COP, col_viejo_…", SEC)
    for pre, q in [("pcom", "P2Pcol"), ("ppa", "C2ppa")]:
        cam = [f"{r.caso} ({r.variante}) − {y}" for _, r in cmc.iterrows() for y in ["C1", "C4", "C5"]
               if r[f"cambia_{q}_menos_{y}"]]
        pon(f"{pre}__com__brechas_comunidad_cambian", len(cam), "brechas", en_int(len(cam)), f"brechas de la comunidad "
            f"de {ESC_PD[q]} (frente a C1, C4 y C5) que cambian de signo con un solo comercializador (A o B)",
            FK + "filas comunidad", SEC)
        pon(f"{pre}__com__brechas_comunidad_cambian__lista", "; ".join(cam) or "ninguna", "lista", "; ".join(cam) or "ninguna",
            f"las brechas de la comunidad de {ESC_PD[q]} que cambian con un solo comercializador", FK + "filas comunidad", SEC)

    # ── retiro de un miembro
    rc = T["retiro_comunidad.csv"]
    FR = F_PD.format("retiro_comunidad.csv") + ", "
    FQ = F_PD.format("retiro_quienes_quedan.csv") + ", "
    pon("pcom__retiro__n", len(rc), "comunidades", en_int(len(rc)), "comunidades de cuatro (cada retiro en 11 casos)",
        FR.rstrip(", "), SEC)
    for pre, q in [("pcom", "P2Pcol"), ("ppa", "C2ppa")]:
        for y in ["C4", "C1", "C5"]:
            x = rc[rc[f"cambia_{q}_menos_{y}"] == 1]
            pon(f"{pre}__retiro__cambia_{y}", len(x), "comunidades", en_int(len(x)), f"comunidades de cuatro (de 54) con "
                f"{ESC_PD[q]} − {y} de signo distinto del de la comunidad completa", FR + f"cambia_{q}_menos_{y}", SEC)
            lst = "; ".join(f"{a} sin {b}" for a, b in zip(x.caso, x.retirada)) or "ninguna"
            pon(f"{pre}__retiro__cambia_{y}__lista", lst, "lista", lst, f"las comunidades de cuatro en que cambia "
                f"{ESC_PD[q]} − {y}", FR + f"cambia_{q}_menos_{y}", SEC)
    k_ = rc.P2Pcol_menos_C4_COP.idxmin()
    pon("pcom__retiro__min_C4", float(rc.loc[k_, "P2Pcol_menos_C4_COP"]), "COP", en(rc.loc[k_, "P2Pcol_menos_C4_COP"], 0),
        f"menor P2P colectivo − C4 en las 54 comunidades ({rc.loc[k_, 'caso']} sin {rc.loc[k_, 'retirada']})",
        FR + "P2Pcol_menos_C4_COP", SEC)
    pon("pcom__retiro__min_C4_caso", f"{rc.loc[k_, 'caso']} sin {rc.loc[k_, 'retirada']}", "comunidad",
        f"{rc.loc[k_, 'caso']} sin {rc.loc[k_, 'retirada']}", "comunidad con el menor P2P colectivo − C4",
        FR + "P2Pcol_menos_C4_COP", SEC)
    for k, v, u, fmt, dfn in [
            ("caso1", int((rc.caso_art20_P2Pcol == 1).sum()), "comunidades", None, "comunidades de cuatro en el caso 1 del "
             "art. 20 del P2P colectivo"),
            ("cal_energia_pct", float(100 * ((rc.energia_aprox_kwh - rc.energia_canon_kwh).abs() / rc.energia_canon_kwh).max()),
             "%", 2, "calibración: mayor diferencia de la energía del lado corto con la del canon de cuatro"),
            ("cal_com_max", float(rc.P2P_aprox_menos_canon_COP.abs().max() / M), "MCOP", 2, "calibración: mayor error de "
             "la aproximación en el mercado de la comunidad de cuatro"),
            ("cal_col_max", float(rc.col_viejo_aprox_menos_canon_COP.abs().max() / M), "MCOP", 2, "calibración: mayor "
             "error de la aproximación en el viejo colectivo de la comunidad de cuatro")]:
        pon(f"pcom__retiro__{k}", v, u, en_int(v) if fmt is None else en(v, fmt, " %" if u == "%" else ""), dfn,
            FR + "caso_art20_P2Pcol, energia_*, *_aprox_menos_canon_COP", SEC)
    rq = T["retiro_quienes_quedan.csv"]
    err = (rq.P2P_sin_aprox_menos_canon_COP).abs()
    acu = int((rq.mas_estable_mercado_aprox == rq.mas_estable_mercado_canon).sum())
    for k, v, u, fmt, dfn in [
            ("pares", len(rq), "pares", None, "pares (retirada, institución que se queda)"),
            ("estables", int((rq.mas_estable == "P2Pcol").sum()), "pares", None, "pares en que el beneficio de quien se "
             "queda se mueve menos con el P2P colectivo que con C4"),
            ("mediana_P2Pcol_miles", float(rq.perdida_P2Pcol_COP.abs().median() / 1e3), "miles de COP", 0,
             "mediana de la pérdida absoluta de quien se queda con el P2P colectivo"),
            ("mediana_P2Pcol_pct", float(100 * rq.perdida_rel_P2Pcol.abs().median()), "%", 2, "mediana de la pérdida "
             "absoluta relativa al beneficio propio, con el P2P colectivo"),
            ("mediana_C4_miles", float(rq.perdida_C4_COP.abs().median() / 1e3), "miles de COP", 0,
             "mediana de la pérdida absoluta de quien se queda con C4 (§14.13)"),
            ("pierde", int((rq.perdida_P2Pcol_COP > 0).sum()), "pares", None, "pares en que quien se queda pierde con el "
             "P2P colectivo"),
            ("gana", int((rq.perdida_P2Pcol_COP < 0).sum()), "pares", None, "pares en que quien se queda gana con el P2P "
             "colectivo"),
            ("pares_cambia_C4", int(rq.cambia_P2Pcol_menos_C4.sum()), "pares", None, "pares con P2P colectivo − C4 de quien "
             "se queda de signo distinto del de la comunidad completa"),
            ("cal_inst_mediana", float(err.median()), "COP", 0, "calibración: error mediano de la aproximación en el "
             "mercado por institución"),
            ("cal_inst_max", float(err.max()), "COP", 0, "calibración: mayor error de la aproximación en el mercado por "
             "institución"),
            ("cal_acuerdo", acu, "pares", None, "calibración: pares en que la clase «se mueve menos» del mercado aproximado "
             "coincide con la del canon (de 216)")]:
        pon(f"pcom__retiro__{k}", v, u, en_int(v) if fmt is None else en(v, fmt, " %" if u == "%" else ""), dfn,
            FQ + "perdida_*, mas_estable*", SEC)
    for ret, g in rq.groupby("retirada", sort=False):
        n = int((g.mas_estable == "P2Pcol").sum())
        pon(f"pcom__retiro__{ret}__estables", n, "pares", en_int(n), f"sale {ret}: pares en que quien se queda se mueve "
            f"menos con el P2P colectivo (de {len(g)})", FQ + "mas_estable", SEC)

    # ── coincidencia, precio de la justicia, 11 fronteras, umbral y techo
    FO = F_PD.format("coincidencia_13casos.csv") + ", "
    for c in CASOS:
        v = float(co.loc[c, "coincidencia_P2Pcol"])
        pon(f"pcom__coinc__{c}", v, "fracción", en(v, 3), f"factor de coincidencia del P2P colectivo (D20), caso {c}",
            FO + "coincidencia_P2Pcol", SEC)
    for m_, f_ in [("min", co.coincidencia_P2Pcol.idxmin()), ("max", co.coincidencia_P2Pcol.idxmax())]:
        pon(f"pcom__coinc__{m_}_caso", f_, "caso", f_, f"caso con el {'menor' if m_ == 'min' else 'mayor'} factor de "
            "coincidencia del P2P colectivo", FO + "coincidencia_P2Pcol", SEC)
    d_ = co.coincidencia_P2Pcol - co.coincidencia_P2P
    for k, sel, dfn in [("igual_P2P", d_.abs() <= 1e-6, "igual al del mercado (a 1e-6)"),
                        ("menor_P2P", d_ < -1e-6, "menor que el del mercado"), ("mayor_P2P", d_ > 1e-6, "mayor que el del mercado")]:
        lst = ", ".join(c for c in CASOS if sel[c])
        pon(f"pcom__coinc__{k}__lista", lst, "lista", lst, f"casos con el factor de coincidencia del P2P colectivo {dfn}",
            FO + "coincidencia_P2Pcol − coincidencia_P2P", SEC)
    n = int((co.coincidencia_P2Pcol > co.coincidencia_C4).sum())
    pon("pcom__coinc__sobre_C4", n, "casos", en_int(n), "casos con el factor de coincidencia del P2P colectivo por encima "
        "del de C4", FO + "coincidencia_P2Pcol, coincidencia_C4", SEC)
    FT = F_PD.format("otros_13casos.csv") + ", "
    for c in CASOS:
        v = float(100 * ot.loc[c, "pof_P2Pcol"])
        pon(f"pcom__pof__{c}", v, "%", en(v, 1, " %"), f"precio de la justicia del P2P colectivo frente a C4, (W − W_C4) / W "
            f"(Bertsimas, C-208), caso {c}", FT + "pof_P2Pcol", SEC)
        cl = {"domina": "P2P colectivo domina"}.get(ot.loc[c, "clase_P2Pcol"], ot.loc[c, "clase_P2Pcol"])
        cl_en = {"P2P colectivo domina": "collective P2P dominates", "intercambio": "trade-off"}[cl]
        pon(f"pcom__pof__{c}__clase", cl, "clase", cl_en, f"clase del P2P colectivo frente a C4 (§14.6), caso {c}",
            FT + "clase_P2Pcol", SEC)
        v = float(ot.loc[c, "once_fronteras_P2Pcol_menos_P2P_COP"] / M)
        pon(f"pcom__11f__{c}__P2Pcol_P2P", v, "MCOP", en(v, 3), f"con 11 fronteras (el caso 1 para todos), P2P colectivo − "
            f"P2P, caso {c}", FT + "once_fronteras_P2Pcol_menos_P2P_COP", SEC)
    dom = [c for c in CASOS if ot.loc[c, "clase_P2Pcol"] == "domina"]
    pon("pcom__pof__n_domina", len(dom), "casos", en_int(len(dom)), "casos en que el P2P colectivo domina a C4 (más "
        "beneficio y menos desigualdad)", FT + "clase_P2Pcol", SEC)
    lst = ", ".join(c for c in CASOS if c not in dom)
    pon("pcom__pof__intercambio__lista", lst, "lista", lst, "casos con intercambio entre equidad y eficiencia del P2P "
        "colectivo frente a C4", FT + "clase_P2Pcol", SEC)
    for k, col, dfn in [("pcom__umbral_E4_7P1", "umbral_E4_menos_7P1_P2Pcol_COP", "P2P colectivo"),
                        ("pcom__umbral_E4_7P1_c1todos", "umbral_E4_menos_7P1_P2Pcol_c1todos_COP",
                         "P2P colectivo con el caso 1 para todos"),
                        ("ppa__umbral_E4_7P1", "umbral_E4_menos_7P1_C2ppa_COP", "C2 (PPA)")]:
        v = float(ot.loc["E4", col] / M)
        pon(k, v, "MCOP", en(v, 2), f"E4 − 7 × P1 con el {dfn} (§14.11)", FT + col, SEC)
    pon("pcom__techo__horas", int(ot.loc["E0", "techo_horas"]), "horas", en_int(int(ot.loc["E0", "techo_horas"])),
        "horas con la bolsa sobre el precio de escasez ponderado; en ninguna hay excedente (§14.16)", FT + "techo_horas", SEC)
    exige(float(ot.techo_cambio_P2Pcol_COP.abs().max()) == 0.0 and float(ot.techo_excedente_kwh.abs().max()) == 0.0,
          "techo: el P2P colectivo cambia")
    pon("pcom__techo__cambio", 0.0, "MCOP", en(0.0, 2), "cambio del P2P colectivo y de C2 con el techo literal del Anexo 4: "
        "cero exacto", FT + "techo_cambio_P2Pcol_COP, techo_cambio_C2ppa_COP", SEC)
    ok("P2P colectivo derivado: las claves de los meses, σ, COT, comercializador único, retiro, coincidencia, precio de la "
       "justicia, 11 fronteras, umbral y techo cuadran con las tablas 2, 3 y 5 de CANON §14.24")


# ── 17. El GSA con C2 como PPA y el P2P colectivo (§13.9) ───────────────────
def gsa_c2_p2pcol() -> None:
    """P(inversión) de las siete brechas nuevas de comunidad (P2P colectivo,
    `P2Pcom`, y C2 como PPA, `C2ppa`) en la caja del GSA del 2026-10-02, con
    su intervalo al 95 % y su valor en el punto base. Compuertas: las cinco
    brechas del GSA del 27 de septiembre salen al bit en la entrega nueva; las
    dos tablas y los intervalos de CANON §13.9.3; P2Pcom − C4 sin inversión en
    los 12 casos."""
    sub = "SALIDAS_SERVIDOR/gsa_directo_c2_p2pcol_2026-10-03"
    ent = "entrega_gsa_directo_c2_p2pcol_2026-10-03/" + sub
    pb = pd.read_csv(lee(f"{sub}/base/punto_base.csv", "gsa2/base")).set_index("caso")
    # a) lo común con el GSA del 27 de septiembre, al bit
    cols = ["base", "p_inversion", "p_inf", "p_sup", "minimo", "maximo", "n_filas"]
    nuevos = {}
    for c in CASOS_GSA:
        v2 = pd.read_csv(lee(f"{sub}/{c}/inversion_{c}.csv", f"gsa2/{c}")).set_index("salida")
        v9 = pd.read_csv(lee(f"SALIDAS_SERVIDOR/gsa_directo/{c}/inversion_{c}.csv", f"gsa/{c}")).set_index("salida")
        comunes = [s for s in v9.index if s in v2.index]
        exige(len(comunes) == len(v9), f"{c}: la entrega nueva no trae todas las filas de la del 27")
        exige(bool((v9.loc[comunes, cols].to_numpy(float) == v2.loc[comunes, cols].to_numpy(float)).all()),
              f"{c}: inversion_{c}.csv difiere de la del 27 en las brechas comunes")
        for b in BRECHAS:
            exige(v2.loc[b, "p_inversion"] * 100 == next(f["valor"] for f in FILAS if f["clave"] == f"gsa__{c}__{BRECHAS[b][0]}__p"),
                  f"{c} {b}: la clave del 27 no es la P de la entrega nueva")
        nuevos[c] = v2
    ok("las cinco brechas del GSA del 27 de septiembre, al bit en la entrega del 2026-10-02 (base, P, intervalo, mínimo, "
       "máximo y filas, también por institución) en los 12 casos")
    # b) CANON §13.9.3
    s = seccion("#### 13.9.3 ·")
    tp, tb = tablas(s)
    exige(list(tp.index) == CASOS_GSA and list(tb.index) == CASOS_GSA + ["CV2"], "CANON §13.9.3: casos de las tablas")
    ic = {}
    for m in re.finditer(r"^- (\w+): (.+)\.$", s, re.M):
        for rot, lo, hi in re.findall(r"([^,;]+?), \[([−\d,]+); ([−\d,]+)\]", m.group(2)):
            ic[(m.group(1), rot.strip())] = (num_es(lo), num_es(hi))
    sin_inv = {b: 0 for b in BRECHAS_GSA2}
    for c in CASOS_GSA:
        v = nuevos[c]
        n = int(num_es(tp.loc[c, "n"]))
        for b, (suf, rot, rot_def) in BRECHAS_GSA2.items():
            f = v.loc[b]
            finito([f.p_inversion, f.p_inf, f.p_sup, f.base], f"inversion_{c} {b}")
            exige(int(f.n_filas) == 2 * n, f"{c} {b}: {f.n_filas} filas, CANON §13.9.3 da n = {n}")
            exige(abs(f.base - pb.loc[c, b]) <= 1e-6, f"{c} {b}: la base de inversion no es la de punto_base")
            exige(f.p_inf <= f.p_inversion <= f.p_sup, f"{c} {b}: P fuera de su intervalo")
            p, lo, hi = 100 * f.p_inversion, 100 * f.p_inf, 100 * f.p_sup
            esp = num_es(tp.loc[c, rot])
            exige(abs(p - esp) <= 0.005 + 1e-9, f"{c} {b}: P = {p:.4f} %, CANON §13.9.3 da {esp}")
            if esp == 0:
                exige(lo == 0 and hi == 0 and (c, rot) not in ic, f"{c} {b}: P nula con intervalo no nulo")
                sin_inv[b] += 1
            else:
                elo, ehi = ic[(c, rot)]
                exige(abs(lo - elo) <= 0.005 + 1e-9 and abs(hi - ehi) <= 0.005 + 1e-9,
                      f"{c} {b}: intervalo [{lo:.4f}, {hi:.4f}], CANON §13.9.3 da [{elo}, {ehi}]")
            eb = num_es(tb.loc[c, rot])
            exige(abs(f.base / M - eb) <= 0.005 + 1e-9, f"{c} {b}: base {f.base / M:.4f} MCOP, CANON §13.9.3 da {eb}")
            nota = (" (base nula hasta el redondeo: no se cita, CANON §13.9.8)"
                    if abs(f.base) < 1.0 else "")
            FG = f"{ent}/{c}/inversion_{c}.csv, fila {b}, columna "
            pon(f"gsa__{c}__{suf}__p", p, "%", en(p, 2, " %"),
                f"P(inversión) de {rot_def} en la caja del GSA del 2026-10-02, caso {c}{nota}", FG + "p_inversion", "§13.9")
            pon(f"gsa__{c}__{suf}__lo", lo, "%", en(lo, 2, " %"),
                f"cota inferior al 95 % de P(inversión) de {rot_def}, caso {c}{nota}", FG + "p_inf", "§13.9")
            pon(f"gsa__{c}__{suf}__hi", hi, "%", en(hi, 2, " %"),
                f"cota superior al 95 % de P(inversión) de {rot_def}, caso {c}{nota}", FG + "p_sup", "§13.9")
            pon(f"gsa__{c}__{suf}__base", f.base / M, "MCOP", en(f.base / M, 2),
                f"{rot_def} en el punto base del GSA del 2026-10-02, caso {c}", f"{ent}/base/punto_base.csv, columna " + b,
                "§13.9")
    exige(len(ic) == sum(12 - k for k in sin_inv.values()),
          f"CANON §13.9.3: {len(ic)} intervalos leídos, se esperaban {sum(12 - k for k in sin_inv.values())}")
    ok(f"la tabla de P(inversión) de las siete brechas nuevas, sus {len(ic)} intervalos y la tabla del punto base de "
       "CANON §13.9.3 en los 12 casos")
    for b, (suf, rot, rot_def) in BRECHAS_GSA2.items():
        pon(f"gsa__n_casos_sin_inversion_{suf}", sin_inv[b], "casos de 12", en_int(sin_inv[b]),
            f"casos del GSA del 2026-10-02 con P(inversión) de {rot_def} igual a cero",
            f"{ent}/<caso>/inversion_<caso>.csv, columna p_inversion, conteo", "§13.9")
    exige(sin_inv["P2Pcom_menos_C4"] == 12, f"P2Pcom − C4: P(inversión) nula en {sin_inv['P2Pcom_menos_C4']} casos, no en 12")
    ok("P2P colectivo (P2Pcom) − C4 sin inversión en los 12 casos (CANON §13.9.3)")


# ── 18. El corte hx y el fondo del P2P colectivo (C-282; añadido el 2026-10-04) ──
F_CF = "corte_fondo_2026-10-04/corte_fondo_13casos.csv"


def corte_fondo() -> None:
    """El corte hx (energía y ahorro del intercambio del mercado P2P antes y tras
    la hora del corte, y el ahorro por kWh) y el fondo del P2P colectivo
    (residual redistribuido a quien todavía importa y exceso a la bolsa en C1,
    el mercado P2P, el P2P colectivo y C4), de `corte_fondo_2026-10-04/`
    (grupo `e1/CF`, CANON §14.25). Compuertas: lo antes y lo tras suman lo
    total y el ahorro total es `com__<caso>__banda`, al peso; el ancho de E0 es
    `e0__ancho_efectivo` y la energía transada sobre la inyección,
    `atr__<caso>__transado_pct`; el neto del fondo es la diferencia de exceso;
    las dos tablas de CANON §14.25 a sus decimales; el P2P colectivo manda más
    a la bolsa que el mercado solo en N1."""
    SEC = "§14.25"
    X = pd.read_csv(lee(F_CF, "e1/CF"))
    exige(len(X) == 77 and not X.to_csv().lower().count("cedenar"), f"{F_CF}: {len(X)} filas o comercializador nombrado")
    num = X.drop(columns=["caso", "institucion", "ancho_COP_kWh", "ancho_antes_COP_kWh", "ancho_tras_COP_kWh"])
    finito(num.to_numpy(dtype=float), F_CF)
    C = X[X.institucion == "comunidad"].set_index("caso")
    exige(list(C.index) == CASOS, f"{F_CF}: casos de la comunidad")
    FC = F_CF + ", fila comunidad, "
    # (a) las sumas, la banda de §14.8 y las claves previas
    for c in CASOS:
        r = C.loc[c]
        exige(abs(r.vendido_antes_kwh + r.vendido_tras_kwh - r.vendido_kwh) <= 1e-5
              and abs(r.vendido_kwh - r.comprado_kwh) <= 1e-5, f"{c}: energía antes + tras ≠ total")
        exige(abs(r.banda_antes_COP + r.banda_tras_COP - r.banda_COP) <= 1e-5, f"{c}: ahorro antes + tras ≠ total")
        exige(abs(r.banda_COP / M - valor_de(f"com__{c}__banda")) <= 1e-6,
              f"{c}: ahorro del intercambio {r.banda_COP / M:.6f} ≠ com__{c}__banda {valor_de(f'com__{c}__banda'):.6f}")
        exige(abs(100 * r.vendido_kwh / r.inyeccion_kwh - valor_de(f"atr__{c}__transado_pct")) <= 1e-4,
              f"{c}: energía transada / inyección ≠ atr__{c}__transado_pct")
        exige(abs(r.exceso_P2P_menos_P2Pcol_kwh - r.fondo_neto_kwh) <= 1e-5
              and abs(r.fondo_ganado_kwh - r.fondo_perdido_kwh - r.fondo_neto_kwh) <= 1e-5
              and abs(r.exceso_C1_menos_P2P_kwh - (r.exceso_C1_kwh - r.exceso_P2P_kwh)) <= 1e-5,
              f"{c}: el neto del fondo no es la diferencia de exceso")
        ins = X[(X.caso == c) & (X.institucion != "comunidad")]
        for k in ["vendido_tras_kwh", "banda_tras_COP", "exceso_P2Pcol_kwh", "fondo_ganado_kwh"]:
            exige(abs(float(ins[k].sum()) - float(r[k])) <= 1e-4, f"{c}: la comunidad no es la suma de sus instituciones en {k}")
    exige(abs(C.loc["E0", "ancho_COP_kWh"] - valor_de("e0__ancho_efectivo")) <= 1e-6, "E0: ancho ≠ e0__ancho_efectivo")
    ok("corte y fondo (e1/CF): lo antes y lo tras el corte suman lo total; el ahorro del intercambio total es "
       "com__<caso>__banda (≤ 1 COP) y la energía transada sobre la inyección, atr__<caso>__transado_pct; el ancho de E0 "
       "es e0__ancho_efectivo; neto del fondo = ganado − perdido = exceso del mercado − exceso del P2P colectivo; la "
       "comunidad es la suma de sus instituciones, en los 13 casos")
    # (b) las dos tablas de CANON §14.25
    tb = tablas(seccion("### 14.25 ·"))
    exige(len(tb) == 2, f"CANON §14.25: {len(tb)} tablas, no 2")
    t1, t2 = tb
    exige(list(t1.index) == CASOS and list(t2.index) == CASOS, "CANON §14.25: casos de las tablas")

    def igual(v, celda, d, qué):
        if celda == "—":
            exige(not np.isfinite(v), f"CANON §14.25 {qué}: «—» con valor {v}")
            return
        exige(abs(v - num_es(celda)) <= 0.5 * 10 ** -d + 1e-9, f"CANON §14.25 {qué}: {v:.6f} no redondea a {celda}")

    for c in CASOS:
        r = C.loc[c]
        for col, v, d in [("Transado (kWh)", r.vendido_kwh, 1), ("Tras el corte (kWh)", r.vendido_tras_kwh, 1),
                          ("Tras el corte (%)", 100 * r.vendido_tras_kwh / r.vendido_kwh, 1),
                          ("Ahorro antes (MCOP)", r.banda_antes_COP / M, 3), ("Ahorro tras (MCOP)", r.banda_tras_COP / M, 3),
                          ("Ahorro tras (%)", 100 * r.banda_tras_COP / r.banda_COP, 1),
                          ("COP/kWh antes", r.ancho_antes_COP_kWh, 2), ("COP/kWh tras", r.ancho_tras_COP_kWh, 2),
                          ("COP/kWh total", r.ancho_COP_kWh, 2)]:
            igual(v, t1.loc[c, col], d, f"tabla 1, {c} {col}")
        for col, v, d in [("C1", r.exceso_C1_kwh, 1), ("Mercado P2P", r.exceso_P2P_kwh, 1),
                          ("P2P colectivo", r.exceso_P2Pcol_kwh, 1), ("C4", r.exceso_C4_kwh, 1),
                          ("C1 − mercado", r.exceso_C1_menos_P2P_kwh, 1),
                          ("Mercado − P2P colectivo", r.exceso_P2P_menos_P2Pcol_kwh, 1),
                          ("Residual al fondo", r.residual_iny_kwh, 1), ("Redistribuido", r.fondo_recibido_kwh, 1),
                          ("Ganado", r.fondo_ganado_kwh, 1), ("Perdido", r.fondo_perdido_kwh, 1)]:
            igual(v, t2.loc[c, col], d, f"tabla 2, {c} {col}")
    ok("las dos tablas de CANON §14.25 (el corte en el mercado P2P; el exceso a la bolsa y el fondo) a sus decimales en "
       "los 13 casos")
    # (c) las claves por caso
    con_corte = [c for c in CASOS if C.loc[c, "vendido_tras_kwh"] > 0]
    for c in CASOS:
        r = C.loc[c]
        pc_e = 100 * r.vendido_tras_kwh / r.vendido_kwh
        pc_b = 100 * r.banda_tras_COP / r.banda_COP
        for k, v, u, t, dfn, col in [
                ("energia_kwh", r.vendido_kwh, "kWh", en(r.vendido_kwh, 2), "energía transada en el mercado P2P",
                 "vendido_kwh"),
                ("energia_antes_kwh", r.vendido_antes_kwh, "kWh", en(r.vendido_antes_kwh, 2),
                 "energía transada en el mercado P2P antes de la hora del corte hx de su vendedor (piso = permuta)",
                 "vendido_antes_kwh"),
                ("energia_tras_kwh", r.vendido_tras_kwh, "kWh", en(r.vendido_tras_kwh, 2),
                 "energía transada en el mercado P2P desde la hora del corte hx de su vendedor (piso = bolsa)",
                 "vendido_tras_kwh"),
                ("energia_tras_pct", pc_e, "%", en(pc_e, 2, " %"),
                 "parte de la energía transada que es posterior al corte hx de su vendedor", "vendido_tras_kwh / vendido_kwh"),
                ("ahorro_antes", r.banda_antes_COP / M, "MCOP", en(r.banda_antes_COP / M, 2),
                 "ahorro del intercambio (banda de §14.8) de lo transado antes del corte hx", "banda_antes_COP"),
                ("ahorro_tras", r.banda_tras_COP / M, "MCOP", en(r.banda_tras_COP / M, 2),
                 "ahorro del intercambio (banda de §14.8) de lo transado desde el corte hx", "banda_tras_COP"),
                ("ahorro_tras_pct", pc_b, "%", en(pc_b, 2, " %"),
                 "parte del ahorro del intercambio que viene de lo transado desde el corte hx", "banda_tras_COP / banda_COP"),
                ("ancho", r.ancho_COP_kWh, "COP/kWh", en(r.ancho_COP_kWh, 2),
                 "ahorro del intercambio por kWh transado (ancho efectivo; = banda media techo − piso ponderada por energía)",
                 "ancho_COP_kWh"),
                ("ancho_antes", r.ancho_antes_COP_kWh, "COP/kWh", en(r.ancho_antes_COP_kWh, 2),
                 "ahorro del intercambio por kWh transado antes del corte hx (banda media ponderada por energía)",
                 "ancho_antes_COP_kWh")]:
            pon(f"corte__{c}__{k}", float(v), u, t, f"{dfn}, caso {c}", FC + col, SEC)
        if c in con_corte:
            pon(f"corte__{c}__ancho_tras", float(r.ancho_tras_COP_kWh), "COP/kWh", en(r.ancho_tras_COP_kWh, 2),
                f"ahorro del intercambio por kWh transado desde el corte hx (banda media CU − bolsa ponderada por energía), "
                f"caso {c}", FC + "ancho_tras_COP_kWh", SEC)
        for k, col, dfn in [("C1_kwh", "exceso_C1_kwh", "exceso a la bolsa en C1 (inyección bruta por miembro, Anexo 4)"),
                            ("P2P_kwh", "exceso_P2P_kwh", "exceso a la bolsa en el mercado P2P (residual por miembro)"),
                            ("P2Pcom_kwh", "exceso_P2Pcol_kwh",
                             "exceso a la bolsa en el P2P colectivo (P2Pcom: residual al fondo, reparto igual)"),
                            ("C4_kwh", "exceso_C4_kwh", "exceso a la bolsa en C4 (inyección bruta al fondo, reparto igual)"),
                            ("C1_menos_P2P_kwh", "exceso_C1_menos_P2P_kwh",
                             "exceso de C1 menos el del mercado P2P: lo que vender dentro saca de la bolsa"),
                            ("P2P_menos_P2Pcom_kwh", "exceso_P2P_menos_P2Pcol_kwh",
                             "exceso del mercado P2P menos el del P2P colectivo (P2Pcom): lo que el fondo saca de la bolsa "
                             "(negativo: lo manda)")]:
            pon(f"exc__{c}__{k}", float(C.loc[c, col]), "kWh", en(C.loc[c, col], 2), f"{dfn}, caso {c}", FC + col, SEC)
        for k, col, dfn in [("residual_kwh", "residual_iny_kwh", "residual de la comunidad que entra al fondo del P2P "
                             "colectivo, Σ max(s − v, 0)"),
                            ("redistribuido_kwh", "fondo_recibido_kwh", "residual que el reparto igual del fondo lleva de "
                             "un miembro a otro, Σ por miembro y mes de max(asignado − propio, 0)"),
                            ("ganado_kwh", "fondo_ganado_kwh", "residual que el fondo lleva a miembros que todavía importan "
                             "y se acredita (crédito ganado por quien recibe, frente al mercado P2P)"),
                            ("perdido_kwh", "fondo_perdido_kwh", "crédito que pierde quien cede su residual al fondo "
                             "(frente al mercado P2P); ganado − perdido = exc__<caso>__P2P_menos_P2Pcom_kwh")]:
            pon(f"fondo__{c}__{k}", float(C.loc[c, col]), "kWh", en(C.loc[c, col], 2), f"{dfn}, caso {c}", FC + col, SEC)
    # (d) los globales
    pon("corte__casos_con_corte", len(con_corte), "casos de 13", en_int(len(con_corte)),
        "casos con energía transada desde el corte hx (algún miembro agota su crédito)", F_CF + ", filas comunidad", SEC)
    pon("corte__casos_con_corte__lista", ", ".join(con_corte), "casos", ", ".join(con_corte),
        "casos con energía transada desde el corte hx", F_CF + ", filas comunidad, vendido_tras_kwh > 0", SEC)
    at = C.loc[con_corte, "ancho_tras_COP_kWh"]
    aa = C.loc[con_corte, "ancho_antes_COP_kWh"]
    for k, v, cc, dfn in [("ancho_tras_min", at.min(), at.idxmin(), "menor ahorro por kWh transado desde el corte"),
                          ("ancho_tras_max", at.max(), at.idxmax(), "mayor ahorro por kWh transado desde el corte"),
                          ("ancho_antes_min", aa.min(), aa.idxmin(), "menor ahorro por kWh transado antes del corte"),
                          ("ancho_antes_max", aa.max(), aa.idxmax(), "mayor ahorro por kWh transado antes del corte")]:
        pon(f"corte__{k}", float(v), "COP/kWh", en(v, 2), f"{dfn}, en los casos con corte ({cc})",
            F_CF + ", filas comunidad", SEC)
    menos = [c for c in CASOS if C.loc[c, "exceso_P2P_menos_P2Pcol_kwh"] > 1e-6]
    mas = [c for c in CASOS if C.loc[c, "exceso_P2P_menos_P2Pcol_kwh"] < -1e-6]
    for k, lst, dfn in [("menos_bolsa", menos, "el P2P colectivo manda menos energía a la bolsa que el mercado P2P"),
                        ("mas_bolsa", mas, "el P2P colectivo manda más energía a la bolsa que el mercado P2P")]:
        pon(f"fondo__casos_{k}", len(lst), "casos de 13", en_int(len(lst)), f"casos en que {dfn}",
            F_CF + ", filas comunidad, exceso_P2P_menos_P2Pcol_kwh", SEC)
        pon(f"fondo__casos_{k}__lista", ", ".join(lst), "casos", ", ".join(lst), f"casos en que {dfn}",
            F_CF + ", filas comunidad, exceso_P2P_menos_P2Pcol_kwh", SEC)
    exige(mas == ["N1"], f"el P2P colectivo manda más a la bolsa en {mas}, no solo en N1 (CANON §14.23 y §14.25)")
    # N1 por institución: por qué el fondo manda más a la bolsa
    n1 = X[(X.caso == "N1") & (X.institucion != "comunidad")].set_index("institucion")
    FN = F_CF + ", fila N1, institución "
    for a, r in n1.iterrows():
        for k, col, dfn in [("P2P_kwh", "exceso_P2P_kwh", "exceso a la bolsa en el mercado P2P"),
                            ("P2Pcom_kwh", "exceso_P2Pcol_kwh", "exceso a la bolsa en el P2P colectivo (P2Pcom)")]:
            pon(f"exc__N1__{a}__{k}", float(r[col]), "kWh", en(r[col], 2), f"{dfn}, N1, {a}", FN + f"{a}, {col}", SEC)
        for k, col, dfn in [("recibido_kwh", "fondo_recibido_kwh", "residual que el reparto igual le lleva de otros"),
                            ("cedido_kwh", "fondo_cedido_kwh", "residual propio que el reparto igual lleva a otros")]:
            pon(f"fondo__N1__{a}__{k}", float(r[col]), "kWh", en(r[col], 2), f"{dfn}, N1, {a}", FN + f"{a}, {col}", SEC)
    ok(f"corte y fondo: {len(con_corte)} casos con energía tras el corte ({', '.join(con_corte)}); el P2P colectivo manda "
       f"menos a la bolsa que el mercado en {', '.join(menos)} y más solo en N1 (corrección de CANON §14.23)")


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
    n30 = len(FILAS)
    exige(n30 == 818, f"los bloques del 29 y del 30 (A1) dan {n30} cifras, no 818")
    print("[cifras_articulo] 12. la atribución a los dos supuestos (B1, añadido el 2026-09-30)")
    atribucion(R, tar)
    n_b1 = len(FILAS)
    exige(n_b1 == 1051, f"los bloques hasta la atribución dan {n_b1} cifras, no 1051")
    print("[cifras_articulo] 13. el C2 de la propuesta como PPA (añadido el 2026-10-02)")
    ppa(R)
    n_p = len(FILAS)
    exige(n_p == 1343, f"los bloques hasta el PPA dan {n_p} cifras, no 1343")
    print("[cifras_articulo] 14. el P2P comunitario (añadido el 2026-10-02)")
    p2p_comunitario(R)
    n_pc = len(FILAS)
    exige(n_pc == 1714, f"los bloques hasta el P2P comunitario dan {n_pc} cifras, no 1714")
    print("[cifras_articulo] 15. el P2P comunitario por los dos órdenes y Shapley (añadido el 2026-10-02)")
    p2p_comunitario_ordenes(R)
    n_ord = len(FILAS)
    exige(n_ord == 1918, f"los bloques hasta los dos órdenes dan {n_ord} cifras, no 1918")
    print("[cifras_articulo] 16. las mediciones rehechas para el P2P colectivo y C2 (añadido el 2026-10-02)")
    p2p_colectivo_derivados(R)
    n_pd = len(FILAS)
    exige(n_pd == 2210, f"los bloques hasta los derivados del P2P colectivo dan {n_pd} cifras, no 2210")
    print("[cifras_articulo] 17. el GSA con C2 como PPA y el P2P colectivo (añadido el 2026-10-02)")
    gsa_c2_p2pcol()
    n_g2 = len(FILAS)
    exige(n_g2 == 2553, f"los bloques hasta el GSA con C2 y el P2P colectivo dan {n_g2} cifras, no 2553")
    print("[cifras_articulo] 18. el corte hx y el fondo del P2P colectivo (añadido el 2026-10-04)")
    corte_fondo()
    print(f"[cifras_articulo] {len(FILAS) - n29} cifras nuevas desde el 29; {n_b1 - n30} de la atribución; "
          f"{n_p - n_b1} del PPA; {n_pc - n_p} del P2P comunitario; {n_ord - n_pc} de sus dos órdenes; "
          f"{n_pd - n_ord} de los derivados del P2P colectivo; {n_g2 - n_pd} del GSA con C2 y el P2P colectivo; "
          f"{len(FILAS) - n_g2} del corte y el fondo")
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
        fh.write("CANON.md leído como texto (compuertas y constantes de §1, §4, §6, §9, §10.1, §13.1, §13.2, §13.3, §13.9, §14.3, §14.7, "
                 "§14.8, §14.10, §14.11, §14.16, §14.18, §14.21, §14.22, §14.23, §14.24, §14.25); "
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
