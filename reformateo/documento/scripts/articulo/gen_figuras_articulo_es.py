"""
gen_figuras_articulo_es.py — Figuras de la versión en español del artículo
para IEEE Latin America Transactions (Documentos/articulo_latam/v2_es/).
===============================================================================
Tarea A2 de la revisión del artículo en español
(`docs/superpowers/plans/2026-09-30-articulo-es-revision.md`), que responde a
las notas 14, 18 y 56 del autor (`v2_es/revision/anotaciones_autor.md`) con
las piezas F1, F2 y F4 de `respuestas_anotaciones.md` y los tres nombres
aprobados el 2026-09-30: «cargos evitados» (C1 − C4), «ahorro del
intercambio» (la banda) y «efecto sobre el crédito» (la reclasificación).

No simula nada. Su única entrada numérica es
`SALIDAS_SERVIDOR/cifras_articulo_2026-09-30/cifras.csv`, leída con su huella
e1/L por el generador inglés (`gen_figuras_articulo.py`, que se importa sin
modificarlo), salvo la figura de la hora, que sale del almacén de E0 con
huella a través del generador de la tesis (`gen_tesis_figuras.py`, función
`c5_banda_hora`, importado sin modificarlo y con sus compuertas).

Figuras (en `Documentos/articulo_latam/v2_es/figuras/`, con .pdf, .png a
600 ppp, .csv y .fuente.txt):

  fig1_comunidad     dos paneles, sin cifras: (a) lo que las reglas permiten,
                     C1 y C4; (b) lo que el mercado supone, el intercambio
                     interno con el pago interno y los supuestos 1 y 2, con el
                     residual fuera del colectivo (corrige la figura anterior,
                     que dibujaba el mercado dentro del colectivo). Página.
  fig2_cascada_E0    dos paneles con el mismo eje: (a) el beneficio neto de la
                     comunidad en E0 con los siete mecanismos; (b) la cascada
                     de C4 al mercado con los tres nombres aprobados y la línea
                     del P2P comunitario (desde el 2026-10-02 reemplaza al
                     mercado por el colectivo como mecanismo, CANON §14.23).
                     Página.
  fig_hora_E0        una hora de E0 en el eje de precios (pieza F2): la figura
                     de la tesis más el volumen transado como lado corto y la
                     energía disponible de cada comprador. Página.
  fig3_trece_casos   variante española propia desde el 2026-10-02: las barras
                     de la figura inglesa con los nombres nuevos en la leyenda
                     y el rombo del P2P comunitario − C4 en lugar del colectivo
                     − C4 (CANON §14.23). Columna.
  Nombre (2026-10-02, decisión del autor): el P2P comunitario se rotula «P2P
  colectivo» en las Figs. 2 y 3 (CANON §14.23, nota de nombre); las claves
  `*P2Pcom*`, las columnas de los CSV y el texto de `mec__E0__orden_P2Pcom`
  conservan su nombre. La columna «Vía legal (colectivo) − C1» de la Fig. 4 se
  queda hasta que llegue la sensibilidad global con el P2P colectivo.
  fig4_gsa_inversion la figura inglesa traducida, sin cambios de contenido; la
                     columna del colectivo se rotula «Vía legal (colectivo)
                     − C1» (2026-10-02). Columna.

Compuertas (fallan en voz alta con SystemExit):
  1. huella e1/L de cifras.csv (la del generador inglés) y coherencia de
     texto_en con valor en cada clave usada;
  2. Fig. 2: los siete mecanismos siguen el orden de `mec__E0__orden_P2Pcom`
     (desde el 2026-10-02, C2 es el PPA de todo el excedente, CANON §14.22, y
     el P2P comunitario, §14.23, ocupa el lugar del colectivo; los dos cuadran
     con sus brechas al peso), la cascada cierra al peso y sus cinco pasos son
     los de la Fig. 2 inglesa;
  3. Fig. 4: sus datos son, byte a byte en el CSV, los de la figura inglesa;
     Fig. 3 (variante española, 2026-10-02): sus tres series de barras son,
     al peso, las de la figura inglesa y el rombo es com__*__P2Pcom − com__*__C4
     al peso;
  4. figura de la hora: sus datos son los de la Figura 5.1 de la tesis
     (`Documentos/FinalTesisV2/figuras/c5_banda_hora.csv`); los pisos y el
     techo son las claves `kwh__*__2025-04__*` de cifras.csv; el volumen es la
     suma de lo vendido y de lo comprado, y es el lado corto;
  5. cada PDF mide la caja pedida y cada PNG su ancho a 600 ppp; letra ≥ 7 pt
     en todo texto visible; nada se sale del lienzo; ninguna palabra inglesa;
     las instituciones se rotulan Udenar, Unicesmag, Unimar, UCC y HUDN (C-267,
     2026-10-04: acrónimos de más de cuatro letras con mayúscula inicial y
     siglas en mayúsculas, como en el texto);
  6. todo número impreso en el PDF (pypdf) es uno de los que la figura
     escribe desde sus claves (o una marca de eje o de norma declarada), y los
     de las claves están en cifras.csv.

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/gen_figuras_articulo_es.py

Actividades 3.3 y 4.2.
"""
from __future__ import annotations

import hashlib
import io
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

for _s in (sys.stdout, sys.stderr):          # consola cp1252 de Windows
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[3]
SCRIPTS = RAIZ / "reformateo" / "documento" / "scripts"
sys.path.insert(0, str(SCRIPTS / "tesis_entrega"))
sys.path.insert(0, str(AQUI))

import matplotlib                                          # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                            # noqa: E402
from matplotlib.lines import Line2D                        # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch  # noqa: E402

import gen_figuras_entrega as T                            # noqa: E402  (captura y traductor)
import herramientas_articulo as H                          # noqa: E402  (lector de cifras en español)

A = T.A                                                    # gen_figuras_articulo (inglés, sin modificar)
G = T.G                                                    # gen_tesis_figuras (tesis, sin modificar)
E = A.E
GUION = "reformateo/documento/scripts/articulo/gen_figuras_articulo_es.py"
DIR_SAL = RAIZ / "Documentos" / "articulo_latam" / "v2_es" / "figuras"
DIR_EN = RAIZ / "Documentos" / "articulo_latam" / "v2" / "figuras"
CSV_HORA_TESIS = RAIZ / "Documentos" / "FinalTesisV2" / "figuras" / "c5_banda_hora.csv"
CIFRAS = RAIZ / "SALIDAS_SERVIDOR" / A.RUTA_CIFRAS
ANCHO_COL, ANCHO_PAG = T.ANCHO_COL, T.ANCHO_PAG
# 2026-10-02: IEEE pide al menos 8 pt al tamaño impreso (9 a 10 recomendados);
# el mínimo sube de 7 a 8 pt y lo comprueba guardar() en cada figura.
LETRA_MIN, DPI = 8.0, 600
FS, FS_TIT = 8.0, 9.0
PESO = A.PESO
INST = ["Udenar", "Unicesmag", "Unimar", "UCC", "HUDN"]  # mismo orden en los paneles (C-267)
VENDEN = {"Udenar", "Unicesmag"}                           # papeles de la hora de ejemplo

C_ENERGIA = "#222222"
C_LIQ = "#6E6E6E"
C_PAGO = "#8A5A00"

# Números estructurales impresos que no son cifras del canon: normas, artículos,
# numerales, supuestos y marcas de eje. pypdf une a veces dos marcas contiguas
# con un espacio, que el lector español toma por separador de millares.
MARCAS = {
    # 10: umbral normativo del art. 20 de la CREG 101 072 (regla del 10 %), no cifra del canon
    "fig1_comunidad": {"174", "25", "101072", "101", "072", "18", "21", "19", "1", "2", "10"},
    "fig1_mercados": {"174", "25", "101072", "101", "072", "18", "21", "19", "1", "2", "10"},
    "fig2_cascada_E0": {"1", "2", "7"},
    "fig_hora_E0": {"620", "640", "660", "680", "700", "720", "740", "14", "2025", "16", "00", "0"},
    "fig3_trece_casos": {"0", "10", "20", "30", "40", "50", "2"},
    "fig4_gsa_inversion": {"0", "20", "40", "60", "80", "100", "80100", "95", "2 048", "2048", "2 048"},  # n = 2 048 (gsa__<c>__n)
    "fig4_gsa_inversion_tesis": {"0", "20", "40", "60", "80", "100", "80100", "95", "2 048", "2048", "2 048"},  # n = 2 048 (gsa__<c>__n)
}
RES: list[dict] = []
IMPRESOS: dict[str, set[str]] = {}                          # números que cada figura escribe


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[gen_figuras_articulo_es] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    print(f"[gen_figuras_articulo_es]   OK  {msg}")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def es(t: str) -> str:
    """texto_en → español: coma decimal, espacio de millares y signo menos."""
    s = T.num_es(t)
    return "−" + s[1:] if s.startswith("-") else s


def TX(clave: str, dest: str, *, signo: bool = False) -> str:
    """Texto impreso de una clave en español; se anota como número esperado."""
    s = es(A.T(clave, dest))
    if signo and not s.startswith("−"):
        s = "+" + s
    IMPRESOS.setdefault(dest, set()).add(s.lstrip("+−").replace(" %", ""))
    return s


def V(clave: str, dest: str) -> float:
    return A.V(clave, dest)


def rc_articulo() -> None:
    plt.close("all")
    plt.rcdefaults()
    E.aplicar_rc()
    plt.rcParams.update(A.RC_ARTICULO)
    plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})
    # 2026-10-02: tamaños por defecto a 8 pt (IEEE), también en marcas y leyendas
    plt.rcParams.update({"font.size": FS, "xtick.labelsize": FS, "ytick.labelsize": FS,
                         "axes.labelsize": FS, "legend.fontsize": FS, "axes.titlesize": FS_TIT})


# ── Guardado y medidas ──────────────────────────────────────────────────────
def guardar(fig, nombre: str, datos: pd.DataFrame, caja: str, procedencia: list[str]) -> None:
    ancho = ANCHO_COL if caja == "col" else ANCHO_PAG
    w, h = fig.get_size_inches()
    exige(abs(w - ancho) < 1e-6, f"{nombre}: la figura mide {w:.5f} in, la caja es {ancho:.5f}")
    letra = T.letra_minima(fig, nombre)
    exige(letra >= LETRA_MIN - 1e-9,
          f"{nombre}: letra de {letra:.2f} pt, por debajo de los {LETRA_MIN} pt de IEEE")
    T.dentro_del_lienzo(fig, nombre)
    for t in T._textos_visibles(fig):
        m = T.VETADAS.search(t.get_text())
        exige(m is None, f"{nombre}: queda inglés: «{t.get_text()}»")
        for viejo in ("Cesmag", "CESMAG", "Mariana"):           # C-267
            exige(viejo not in t.get_text(), f"{nombre}: rotula «{viejo}» en «{t.get_text()}» (Unicesmag o Unimar)")
    DIR_SAL.mkdir(parents=True, exist_ok=True)
    base = DIR_SAL / nombre
    with plt.rc_context({"savefig.bbox": "standard", "savefig.pad_inches": 0.0}):
        fig.savefig(base.with_suffix(".pdf"))
        fig.savefig(base.with_suffix(".png"), dpi=DPI)
    plt.close(fig)
    datos.to_csv(base.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    claves = sorted(A.USADAS.get(nombre, set()))
    base.with_suffix(".fuente.txt").write_text(
        f"Figura: {nombre} (versión en español del artículo, Documentos/articulo_latam/v2_es)\n"
        f"Guion: {GUION}\n"
        f"Caja: {'columna' if caja == 'col' else 'página'}, {w:.5f} × {h:.5f} in; "
        f"letra mínima medida {letra:.2f} pt; PNG a {DPI} ppp\n"
        f"Tabla de cifras: SALIDAS_SERVIDOR/{A.RUTA_CIFRAS} (HUELLAS.csv, grupo e1/L; sha256 {A.SHA})\n"
        f"Claves usadas ({len(claves)}):\n" + "".join(f"  - {k}\n" for k in claves)
        + "Procedencia y compuertas:\n" + "".join(f"  - {p}\n" for p in procedencia),
        encoding="utf-8")
    RES.append(dict(nombre=nombre, ancho=w, alto=h, letra=letra, caja=caja))
    print(f"  escrito {nombre}.pdf / .png / .csv / .fuente.txt ({w:.3f} × {h:.3f} in, "
          f"letra mínima {letra:.2f} pt)")


# ── Fig. 1: lo que las reglas permiten frente a lo que el mercado supone ────
def _caja(ax, x0, y0, w, h, lineas, *, fc="white", ec="#333333", ls="-", lw=0.8, r=0.05):
    """Caja redondeada con líneas de texto centradas; `lineas` = [(texto, peso)]."""
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, ls=ls, lw=lw, zorder=2))
    paso = 1.18 * FS / 72
    yc = y0 + h / 2 + (len(lineas) - 1) * paso / 2
    for i, (t, peso) in enumerate(lineas):
        ax.text(x0 + w / 2, yc - i * paso, t, ha="center", va="center", fontsize=FS,
                fontweight=peso, color=E.COLOR_TEXTO, zorder=3)


def _flecha(ax, a, b, *, ls="-", color=C_ENERGIA, estilo="-|>", lw=0.8):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=estilo, mutation_scale=6, lw=lw, ls=ls,
                                 color=color, zorder=4, shrinkA=0, shrinkB=0))


def _miembros(ax, x0, ancho, y0, alto, papeles: bool = False) -> list[float]:
    g = 0.08
    w = (ancho - 4 * g) / 5
    centros = []
    for k, n in enumerate(INST):
        x = x0 + k * (w + g)
        lineas = [(n, "bold")]
        if papeles:
            lineas.append(("vende" if n in VENDEN else "compra", "normal"))
        _caja(ax, x, y0, w, alto, lineas, r=0.04)
        centros.append(x + w / 2)
    return centros


def fig1() -> None:
    # 2026-10-02 (auditoría del autor): cuadrícula de 2 × 2 con letra de 8 pt
    # (IEEE: al menos 8 pt). (a) C1 y (b) C4, lo que las reglas permiten; (c) el
    # mercado P2P con sus dos supuestos y (d) el P2P colectivo, la regla propuesta
    # dentro de C4. Correcciones: la energía asignada se liquida contra la
    # importación por el art. 21 (no el 25); el caso 2 de C4 se debe a la regla
    # del 10 %; la flecha del fondo al comercializador lleva rótulo; «que la
    # regulación vigente no contempla».
    nombre = "fig1_comunidad"
    W, Hh = ANCHO_PAG, 4.62
    fig = plt.figure(figsize=(W, Hh))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, Hh)
    ax.axis("off")
    suave = E.COLOR_TEXTO_SUAVE
    ret = "Comercializador de cada miembro"         # 2026-10-01: sin nombres
    L = 1.18 * FS / 72                              # alto de una línea de texto
    alto = lambda n: n * L + 0.09                   # alto de una caja de n líneas
    xa, wa = 0.05, 3.42                             # columna izquierda
    xb, wb = 3.67, 3.42                             # columna derecha
    pas = 0.42                                      # pasillo del fondo a la derecha

    def titulo(x, y, t):
        ax.text(x, y, t, ha="left", va="top", fontsize=FS_TIT, fontweight="bold",
                color=E.COLOR_TEXTO)
        return y - 0.22

    def flechas_dobles(cs, y0, y1):
        for cx in cs:
            _flecha(ax, (cx, y0), (cx, y1), ls="--", color=C_LIQ, estilo="<|-|>")

    def rotulo(x, y, t):
        ax.text(x, y, t, ha="center", va="center", fontsize=FS, color=suave,
                bbox=dict(boxstyle="square,pad=0.05", fc="white", ec="none"), zorder=5)

    # ── (a) C1 ──────────────────────────────────────────────────────────────
    y = titulo(xa, Hh - 0.04, "(a) C1: autogeneración individual (CREG 174, art. 25)")
    h = alto(3)
    _caja(ax, xa, y - h, wa, h, [(ret, "normal"),
                                 ("importación, crédito y exceso de cada miembro,", "normal"),
                                 ("con la deducción del numeral de su planta", "normal")],
          fc="#F2F2F2")
    y_ret_a = y - h
    y_m = y_ret_a - 0.24 - 0.25
    cs = _miembros(ax, xa, wa, y_m, 0.25)
    flechas_dobles(cs, y_m + 0.25, y_ret_a)
    fin_a = y_m

    # ── (b) C4 ──────────────────────────────────────────────────────────────
    y = fin_a - 0.20
    ax.plot([xa, xa + wa], [y + 0.10, y + 0.10], color="#CCCCCC", lw=0.6)
    y = titulo(xa, y, "(b) C4: autogeneración colectiva (CREG 101 072)")
    h = alto(4)
    _caja(ax, xa, y - h, wa, h, [(ret, "normal"),
                                 ("la energía asignada a cada miembro, contra", "normal"),
                                 ("su importación (art. 21)", "normal"),
                                 ("caso 2 por la regla del 10 %: Cv más cargos de red", "bold")],
          fc="#F2F2F2")
    y_ret_b = y - h
    y_m = y_ret_b - 0.26 - 0.25
    cs = _miembros(ax, xa, wa - pas, y_m, 0.25)
    flechas_dobles(cs, y_m + 0.25, y_ret_b)
    rotulo((cs[1] + cs[2]) / 2, y_ret_b - 0.13, "importación")
    h = alto(3)
    y_f = y_m - 0.16 - h
    for cx in cs:
        _flecha(ax, (cx, y_m), (cx, y_f + h), color=C_ENERGIA)
    _caja(ax, xa, y_f, wa, h, [("Fondo común: la inyección de los cinco miembros,", "normal"),
                               ("repartida con el porcentaje del art. 19 (aquí, igual)", "normal"),
                               ("sin pagos entre miembros", "normal")],
          fc="#EAF6F1", ec=A.C_COL, ls=(0, (4, 2)))
    xp = xa + wa - pas / 2
    _flecha(ax, (xp, y_f + h), (xp, y_ret_b), ls="--", color=C_LIQ)
    ax.text(xp + 0.02, (y_f + h + y_ret_b) / 2, "asignada", rotation=90, ha="center",
            va="center", fontsize=FS, color=suave,
            bbox=dict(boxstyle="square,pad=0.03", fc="white", ec="none"), zorder=5)
    fin_izq = y_f

    # separador de columnas
    ax.plot([3.58, 3.58], [0.05, Hh - 0.04], color="#BBBBBB", lw=0.6)

    # ── (c) mercado P2P ─────────────────────────────────────────────────────
    y = titulo(xb, Hh - 0.04, "(c) Mercado P2P con los dos supuestos")
    ax.text(xb, y + 0.02, "La regulación vigente no los contempla", ha="left", va="top",
            fontsize=FS, style="italic", color=E.COLOR_TEXTO)
    y -= 0.19
    h = alto(3)
    _caja(ax, xb, y - h, wb, h, [(ret, "normal"),
                                 ("Supuesto 1: residual por miembro,", "bold"),
                                 ("fuera de C4, con el numeral de su planta", "normal")],
          fc="#F2F2F2")
    y_ret_c = y - h
    y_m = y_ret_c - 0.22 - 0.36
    cs = _miembros(ax, xb, wb, y_m, 0.36, papeles=True)
    flechas_dobles(cs, y_m + 0.36, y_ret_c)
    rotulo((cs[1] + cs[2]) / 2, y_ret_c - 0.11, "residual")
    h = alto(3)
    y_x = y_m - 0.26 - h
    _caja(ax, xb, y_x, wb, h, [("Intercambio interno, cada hora, a precio uniforme", "normal"),
                               ("con tope en la tarifa de cada comprador", "normal"),
                               ("Supuesto 2: no paga cargos de red ni Cv", "bold")],
          fc="#FFF4E0", ec=A.C_P2PC1)
    d = 0.07
    for n, cx in zip(INST, cs):
        if n in VENDEN:   # energía hacia el intercambio; pago de vuelta al vendedor
            _flecha(ax, (cx - d, y_m), (cx - d, y_x + h), color=C_ENERGIA)
            _flecha(ax, (cx + d, y_x + h), (cx + d, y_m), ls=":", color=C_PAGO, lw=1.0)
        else:             # energía hacia el comprador; su pago hacia el intercambio
            _flecha(ax, (cx - d, y_x + h), (cx - d, y_m), color=C_ENERGIA)
            _flecha(ax, (cx + d, y_m), (cx + d, y_x + h), ls=":", color=C_PAGO, lw=1.0)
    fin_c = y_x

    # ── (d) P2P colectivo ──────────────────────────────────────────────────
    y = fin_c - 0.20
    ax.plot([xb, xb + wb], [y + 0.10, y + 0.10], color="#CCCCCC", lw=0.6)
    y = titulo(xb, y, "(d) P2P colectivo: la regla propuesta, dentro de C4")
    h = alto(3)
    _caja(ax, xb, y - h, wb, h, [(ret, "normal"),
                                 ("la energía asignada, contra la importación residual", "normal"),
                                 ("caso 1, sin la regla del 10 %: solo Cv", "bold")],
          fc="#F2F2F2")
    y_ret_d = y - h
    y_m = y_ret_d - 0.26 - 0.25
    cs = _miembros(ax, xb, wb - pas, y_m, 0.25)
    flechas_dobles(cs, y_m + 0.25, y_ret_d)
    rotulo((cs[1] + cs[2]) / 2, y_ret_d - 0.13, "importación residual")
    h_x = alto(1)
    y_x = y_m - 0.14 - h_x
    for n, cx in zip(INST, cs):     # mismos papeles de la hora de ejemplo que en (c)
        if n in VENDEN:
            _flecha(ax, (cx - d, y_m), (cx - d, y_x + h_x), color=C_ENERGIA)
            _flecha(ax, (cx + d, y_x + h_x), (cx + d, y_m), ls=":", color=C_PAGO, lw=1.0)
        else:
            _flecha(ax, (cx - d, y_x + h_x), (cx - d, y_m), color=C_ENERGIA)
            _flecha(ax, (cx + d, y_m), (cx + d, y_x + h_x), ls=":", color=C_PAGO, lw=1.0)
    _caja(ax, xb, y_x, wb - pas, h_x, [("Intercambio interno sin cargos", "bold")],
          fc="#FFF4E0", ec=A.C_P2PC1)
    h_f = alto(2)
    y_f = y_x - 0.18 - h_f
    xm = xb + (wb - pas) / 2
    _flecha(ax, (xm, y_x), (xm, y_f + h_f), color=C_ENERGIA)
    rotulo(xm + 0.42, y_x - 0.09, "residual")
    _caja(ax, xb, y_f, wb, h_f, [("Fondo común: solo el residual, lo que nadie", "normal"),
                                 ("compró dentro, repartido igual (art. 19)", "normal")],
          fc="#EAF6F1", ec=A.C_COL, ls=(0, (4, 2)))
    xp = xb + wb - pas / 2
    _flecha(ax, (xp, y_f + h_f), (xp, y_ret_d), ls="--", color=C_LIQ)
    ax.text(xp + 0.02, (y_f + h_f + y_ret_d) / 2, "asignada", rotation=90, ha="center",
            va="center", fontsize=FS, color=suave,
            bbox=dict(boxstyle="square,pad=0.03", fc="white", ec="none"), zorder=5)
    fin_der = y_f

    # ── Leyenda, al pie de la columna izquierda, que es la más corta ────────
    exige(fin_der > 0.04, f"{nombre}: la columna derecha no cabe ({fin_der:.2f} in)")
    yl = fin_izq - 0.28
    for k, (ls, col, txt, lw) in enumerate([("-", C_ENERGIA, "energía", 1.0),
                                             ("--", C_LIQ, "liquidación con el comercializador", 1.0),
                                             (":", C_PAGO, "pago interno, del comprador al vendedor",
                                              1.2)]):
        yk = yl - k * 0.20
        ax.plot([xa + 0.05, xa + 0.40], [yk, yk], ls=ls, color=col, lw=lw)
        ax.text(xa + 0.48, yk, txt, ha="left", va="center", fontsize=FS, color=E.COLOR_TEXTO)
    exige(yl - 0.40 > 0.0, f"{nombre}: la leyenda no cabe ({yl - 0.40:.2f} in)")

    datos = pd.DataFrame({
        "panel": ["a", "a", "b", "b", "b", "c", "c", "c", "d", "d", "d", "d",
                  "leyenda", "leyenda", "leyenda"],
        "elemento": ["C1: comercializador de cada miembro", "C1: miembros",
                     "C4: comercializador de cada miembro, caso 2",
                     "C4: miembros, liquidados contra su importación", "C4: fondo común",
                     "mercado: comercializador de cada miembro (supuesto 1)",
                     "mercado: miembros (vende o compra en la hora)",
                     "mercado: intercambio interno (supuesto 2)",
                     "P2P colectivo: comercializador de cada miembro, caso 1",
                     "P2P colectivo: miembros", "P2P colectivo: intercambio interno sin cargos",
                     "P2P colectivo: fondo común del residual",
                     "energía", "liquidación con el comercializador", "pago interno"],
        "nota": ["art. 25 de la CREG 174; numeral de la planta", "; ".join(INST),
                 "art. 21 de la CREG 101 072; caso 2 del art. 20 por la regla del 10 %",
                 "flecha doble hacia el comercializador (importación)",
                 "art. 19; porcentaje igual; el reparto sube por el pasillo («asignada»)",
                 "residual por miembro, fuera de C4, con el numeral de su planta",
                 "; ".join(INST), "precio uniforme con tope en la tarifa; sin cargos",
                 "energía asignada contra la importación residual; caso 1 sin la regla del 10 %",
                 "; ".join(INST), "intercambio sin cargos (CANON sec. 14.23)",
                 "solo el residual, repartido igual (art. 19)",
                 "trazo continuo", "trazo discontinuo", "trazo punteado"]})
    guardar(fig, nombre, datos, "pag", [
        "esquema sin cifras del canon: solo números de norma, artículo, numeral, caso y supuesto",
        "2026-10-02 (auditoría del autor): cuadrícula de 2 × 2 a 8 pt (IEEE); (d) P2P colectivo, "
        "la regla propuesta (CANON sec. 14.23); art. 21 para la energía asignada; caso 2 de C4 por "
        "la regla del 10 %; flecha «asignada»; «la regulación vigente no los contempla»",
        "papeles de la hora de ejemplo del panel (c): venden Udenar y Unicesmag y compran Unimar, "
        "UCC y HUDN, como en la hora de fig_hora_E0; cambian de hora en hora"])


def fig1_col() -> None:
    # 2026-10-03 (recorte a 9 páginas, decisión del autor): la Fig. 1 del
    # artículo pasa a una columna con lo fundamental, los paneles (c) y (d) de
    # fig1_comunidad: (a) el mercado P2P con sus dos supuestos y (b) el P2P
    # colectivo. C1 y C4 quedan en el texto y en las Tablas I y II; la tesis
    # conserva la cuadrícula de 2 × 2 (fig1_comunidad).
    nombre = "fig1_mercados"
    W, Hh = ANCHO_COL, ALTO_FIG1_COL
    fig = plt.figure(figsize=(W, Hh))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, Hh)
    ax.axis("off")
    suave = E.COLOR_TEXTO_SUAVE
    ret = "Comercializador de cada miembro"
    L = 1.18 * FS / 72
    alto = lambda n: n * L + 0.09
    xb, wb = 0.03, W - 0.06
    pas = 0.42
    d = 0.07

    def titulo(x, y, t):
        ax.text(x, y, t, ha="left", va="top", fontsize=FS_TIT, fontweight="bold",
                color=E.COLOR_TEXTO)
        return y - 0.22

    def flechas_dobles(cs, y0, y1):
        for cx in cs:
            _flecha(ax, (cx, y0), (cx, y1), ls="--", color=C_LIQ, estilo="<|-|>")

    def rotulo(x, y, t):
        ax.text(x, y, t, ha="center", va="center", fontsize=FS, color=suave,
                bbox=dict(boxstyle="square,pad=0.05", fc="white", ec="none"), zorder=5)

    def papeles(cs, y_m, y_x, h):
        for n, cx in zip(INST, cs):
            if n in VENDEN:
                _flecha(ax, (cx - d, y_m), (cx - d, y_x + h), color=C_ENERGIA)
                _flecha(ax, (cx + d, y_x + h), (cx + d, y_m), ls=":", color=C_PAGO, lw=1.0)
            else:
                _flecha(ax, (cx - d, y_x + h), (cx - d, y_m), color=C_ENERGIA)
                _flecha(ax, (cx + d, y_m), (cx + d, y_x + h), ls=":", color=C_PAGO, lw=1.0)

    # ── (a) mercado P2P ─────────────────────────────────────────────────────
    y = titulo(xb, Hh - 0.04, "(a) Mercado P2P con los dos supuestos")
    ax.text(xb, y + 0.02, "La regulación vigente no los contempla", ha="left", va="top",
            fontsize=FS, style="italic", color=E.COLOR_TEXTO)
    y -= 0.19
    h = alto(3)
    _caja(ax, xb, y - h, wb, h, [(ret, "normal"),
                                 ("Supuesto 1: residual por miembro,", "bold"),
                                 ("fuera de C4, con el numeral de su planta", "normal")],
          fc="#F2F2F2")
    y_ret = y - h
    y_m = y_ret - 0.18 - 0.36
    cs = _miembros(ax, xb, wb, y_m, 0.36, papeles=True)
    flechas_dobles(cs, y_m + 0.36, y_ret)
    rotulo((cs[1] + cs[2]) / 2, y_ret - 0.11, "residual")
    h = alto(3)
    y_x = y_m - 0.20 - h
    _caja(ax, xb, y_x, wb, h, [("Intercambio interno, cada hora, a precio uniforme", "normal"),
                               ("con tope en la tarifa de cada comprador", "normal"),
                               ("Supuesto 2: no paga cargos de red ni Cv", "bold")],
          fc="#FFF4E0", ec=A.C_P2PC1)
    papeles(cs, y_m, y_x, h)

    # ── (b) P2P colectivo ──────────────────────────────────────────────────
    y = y_x - 0.16
    ax.plot([xb, xb + wb], [y + 0.10, y + 0.10], color="#CCCCCC", lw=0.6)
    y = titulo(xb, y, "(b) P2P colectivo: la regla propuesta, en C4")
    h = alto(3)
    _caja(ax, xb, y - h, wb, h, [(ret, "normal"),
                                 ("la energía asignada, contra la importación residual", "normal"),
                                 ("caso 1, sin la regla del 10 %: solo Cv", "bold")],
          fc="#F2F2F2")
    y_ret = y - h
    y_m = y_ret - 0.20 - 0.25
    cs = _miembros(ax, xb, wb - pas, y_m, 0.25)
    flechas_dobles(cs, y_m + 0.25, y_ret)
    rotulo((cs[1] + cs[2]) / 2, y_ret - 0.13, "importación residual")
    h_x = alto(1)
    y_x = y_m - 0.14 - h_x
    papeles(cs, y_m, y_x, h_x)
    _caja(ax, xb, y_x, wb - pas, h_x, [("Intercambio interno sin cargos", "bold")],
          fc="#FFF4E0", ec=A.C_P2PC1)
    h_f = alto(2)
    y_f = y_x - 0.15 - h_f
    xm = xb + (wb - pas) / 2
    _flecha(ax, (xm, y_x), (xm, y_f + h_f), color=C_ENERGIA)
    rotulo(xm + 0.42, y_x - 0.09, "residual")
    _caja(ax, xb, y_f, wb, h_f, [("Fondo común: solo el residual, lo que nadie", "normal"),
                                 ("compró dentro, repartido igual (art. 19)", "normal")],
          fc="#EAF6F1", ec=A.C_COL, ls=(0, (4, 2)))
    xp = xb + wb - pas / 2
    _flecha(ax, (xp, y_f + h_f), (xp, y_ret), ls="--", color=C_LIQ)
    ax.text(xp + 0.02, (y_f + h_f + y_ret) / 2, "asignada", rotation=90, ha="center",
            va="center", fontsize=FS, color=suave,
            bbox=dict(boxstyle="square,pad=0.03", fc="white", ec="none"), zorder=5)

    # ── Leyenda ─────────────────────────────────────────────────────────────
    yl = y_f - 0.18
    for k, (ls, col, txt, lw) in enumerate([("-", C_ENERGIA, "energía", 1.0),
                                             ("--", C_LIQ, "liquidación con el comercializador", 1.0),
                                             (":", C_PAGO, "pago interno, del comprador al vendedor",
                                              1.2)]):
        yk = yl - k * 0.16
        ax.plot([xb + 0.05, xb + 0.40], [yk, yk], ls=ls, color=col, lw=lw)
        ax.text(xb + 0.48, yk, txt, ha="left", va="center", fontsize=FS, color=E.COLOR_TEXTO)
    sobra = yl - 2 * 0.16 - 0.10
    print(f"  {nombre}: sobran {sobra:.3f} in abajo")
    exige(0.0 < sobra < 0.06, f"{nombre}: ajusta ALTO_FIG1_COL (sobran {sobra:.3f} in)")

    datos = pd.DataFrame({
        "panel": ["a", "a", "a", "b", "b", "b", "b", "leyenda", "leyenda", "leyenda"],
        "elemento": ["mercado: comercializador de cada miembro (supuesto 1)",
                     "mercado: miembros (vende o compra en la hora)",
                     "mercado: intercambio interno (supuesto 2)",
                     "P2P colectivo: comercializador de cada miembro, caso 1",
                     "P2P colectivo: miembros", "P2P colectivo: intercambio interno sin cargos",
                     "P2P colectivo: fondo común del residual",
                     "energía", "liquidación con el comercializador", "pago interno"],
        "nota": ["residual por miembro, fuera de C4, con el numeral de su planta",
                 "; ".join(INST), "precio uniforme con tope en la tarifa; sin cargos de red ni Cv",
                 "energía asignada contra la importación residual; caso 1 sin la regla del 10 %",
                 "; ".join(INST), "intercambio sin cargos (CANON sec. 14.23)",
                 "solo el residual, repartido igual (art. 19)",
                 "trazo continuo", "trazo discontinuo", "trazo punteado"]})
    guardar(fig, nombre, datos, "col", [
        "esquema sin cifras del canon: solo números de norma, artículo, caso y supuesto",
        "2026-10-03 (recorte a 9 páginas): los paneles (c) y (d) de fig1_comunidad a una "
        "columna; C1 y C4 quedan en el texto y en las Tablas I y II",
        "papeles de la hora de ejemplo: venden Udenar y Unicesmag y compran Unimar, UCC y HUDN, "
        "como en la hora de fig_hora_E0; cambian de hora en hora"])


ALTO_FIG1_COL = 4.96     # se ajusta con la compuerta de fig1_col (lo que sobra abajo)


# ── Fig. 2: los siete mecanismos y la cascada de E0 ─────────────────────────
MECANISMOS = [  # (clave, rótulo, color, rayado)
    ("P2P", "P2P", A.C_TOTAL_P2P, None),
    # Desde el 2026-10-02, por decisión del autor, el P2P comunitario (CANON
    # §14.23; claves *P2Pcom*) reemplaza como mecanismo al mercado por el
    # colectivo, que queda como la vía legal de hoy (esquina v(0,0) de §14.21).
    # Desde el 2026-10-02 (más tarde), por decisión del autor, se rotula «P2P
    # colectivo» (CANON §14.23, nota de nombre); las claves conservan P2Pcom.
    ("P2Pcom", "P2P\ncolectivo", A.C_COL, None),
    ("C1", "C1", "#999999", None),
    ("C4", "C4", A.C_TOTAL_REF, None),
    ("C5", "C5\n(referencia,\nno elegible)", "white", "////"),
    # C2 es, desde el 2026-10-02, el de la propuesta medido como PPA de todo el
    # excedente por institución, a la media de XM (CANON §14.22; claves *C2ppa);
    # antes era el contrato interno de CAL-52, igual a P2P en el agregado.
    ("C2ppa", "C2 (venta a\nun tercero,\nPPA)", A.OI["purpura"], None),
    # C3: contrafáctico declarado (tesis §6.5 y Tabla 6.x: «contrafáctico declarado,
    # no un régimen elegible»); el artículo usa un único calificativo, «contrafáctico»
    # (ronda 1 de A3, M-12)
    ("C3", "C3\n(contrafáctico)", "white", "\\\\\\\\"),
]
# (el texto de la clave mec__E0__orden_P2Pcom conserva «P2P comunitario»: las
# claves no cambian; en la figura se rotula «P2P colectivo»)
# 2026-10-02 (indicación del asesor, decisión del autor): C2, C3 y C5 se
# reportan en un párrafo breve, sin foco en figuras; el panel (a) dibuja solo
# los cuatro mecanismos centrales. Las compuertas siguen sobre los siete.
PANEL_A = [m for m in MECANISMOS if m[0] in ("P2P", "P2Pcom", "C1", "C4")]
ORDEN_CANON = {"P2P": "P2P", "C2ppa": "C2", "C1": "C1", "C4": "C4", "P2Pcom": "P2P comunitario",
               "C5": "C5", "C3": "C3"}


def _corte(ax) -> None:
    """Corte visible del eje vertical: la línea del eje se interrumpe (tramo en
    blanco) entre dos barras oblicuas."""
    kw = dict(transform=ax.transAxes, clip_on=False)
    ax.plot([0, 0], [0.03, 0.06], color="white", lw=3.0, zorder=10, solid_capstyle="butt", **kw)
    ax.plot([-0.03, 0.03], [0.008, 0.048], color="#222222", lw=1.0, zorder=11, **kw)
    ax.plot([-0.03, 0.03], [0.042, 0.082], color="#222222", lw=1.0, zorder=11, **kw)


def fig2() -> None:
    nombre = d = "fig2_cascada_E0"
    c = "E0"
    b = {m: V(f"com__{c}__{m}", d) for m, *_ in MECANISMOS}
    exige(int(V("mec__n", d)) == len(MECANISMOS), "mec__n no es 7")
    # C2 como PPA (CANON §14.22): su valor cuadra con sus brechas al peso
    for m in ["P2P", "C1", "C4", "C3"]:
        exige(abs(b["C2ppa"] - b[m] - V(f"com__{c}__C2ppa_{m}", d)) <= PESO,
              f"E0: com__E0__C2ppa − {m} no es com__E0__C2ppa_{m}")
    # P2P comunitario (CANON §14.23): su valor cuadra con sus brechas al peso
    for m in ["P2P", "C1", "C4", "C5", "C2ppa", "C3"]:
        exige(abs(b["P2Pcom"] - b[m] - V(f"com__{c}__P2Pcom_{m}", d)) <= PESO,
              f"E0: com__E0__P2Pcom − {m} no es com__E0__P2Pcom_{m}")
    orden = sorted(MECANISMOS, key=lambda m: -round(b[m[0]], 6))
    esperado = A.T("mec__E0__orden_P2Pcom", d)
    exige(" > ".join(ORDEN_CANON[m[0]] for m in orden) == esperado,
          f"el orden de los mecanismos no es el de mec__E0__orden_P2Pcom ({esperado})")
    exige([m[0] for m in orden] == [m[0] for m in MECANISMOS], "MECANISMOS no está ordenado")
    ok(f"E0: siete mecanismos en el orden de mec__E0__orden_P2Pcom ({esperado}); el P2P comunitario y C2 "
       "(PPA a la media de XM) cuadran con sus brechas al peso")

    c4, c1_c4 = b["C4"], V(f"com__{c}__C1_C4", d)
    banda, reclas = V(f"com__{c}__banda", d), V(f"com__{c}__reclas", d)
    p2p, pcom, c1 = b["P2P"], b["P2Pcom"], b["C1"]
    exige(abs(c4 + c1_c4 + banda + reclas - p2p) <= PESO, "cascada de E0: no cierra al peso")
    exige(abs(c4 + c1_c4 - c1) <= PESO, "cascada de E0: C4 + cargos evitados no es C1")
    niveles = [c4, c4 + c1_c4, c4 + c1_c4 + banda, c4 + c1_c4 + banda + reclas]
    ok("cascada de E0: C4 + cargos evitados + ahorro del intercambio + efecto sobre el crédito "
       "= P2P al peso")

    fig, (axa, axb) = plt.subplots(1, 2, sharey=True, figsize=(ANCHO_PAG, 2.30),
                                   gridspec_kw=dict(width_ratios=[4, 5]))
    piso, techo = A.eje_truncado([b[m[0]] for m in PANEL_A] + niveles, sobre=0.5)

    # (a) los cuatro mecanismos centrales (C2, C3 y C5 van en el texto)
    for i, (m, rot, colr, rayado) in enumerate(PANEL_A):
        axa.bar(i, b[m] - piso, bottom=piso, width=0.64, color=colr, hatch=rayado,
                edgecolor="#333333" if rayado is None else "#777777", lw=0.5, zorder=3)
        axa.text(i, b[m] + 0.06, TX(f"com__{c}__{m}", d), ha="center", va="bottom",
                 fontsize=FS, color=E.COLOR_TEXTO, zorder=5)
    axa.set_xticks(range(len(PANEL_A)), [m[1] for m in PANEL_A])
    axa.set_xlim(-0.55, len(PANEL_A) - 0.45)
    axa.set_title("(a) El mercado, el P2P colectivo, C1 y C4", fontsize=FS_TIT, loc="left", pad=4)

    # (b) la cascada con los tres nombres
    pasos = [
        ("C4", piso, c4 - piso, A.C_TOTAL_REF, TX(f"com__{c}__C4", d)),
        ("+ cargos\nevitados", c4, c1_c4, A.C_C1C4,
         TX(f"com__{c}__C1_C4", d, signo=True)),
        ("+ ahorro del\nintercambio", niveles[1], banda, A.C_P2PC1,
         TX(f"com__{c}__banda", d, signo=True)),
        ("+ efecto\nsobre el\ncrédito", niveles[2], reclas, A.C_RECLAS,
         TX(f"com__{c}__reclas", d, signo=True)),
        ("P2P", piso, p2p - piso, A.C_TOTAL_P2P, TX(f"com__{c}__P2P", d)),
    ]
    for i, (_, y0, h, colr, txt) in enumerate(pasos):
        axb.bar(i, h, bottom=y0, width=0.62, color=colr, edgecolor="#333333", lw=0.5, zorder=3)
        cima = y0 + max(h, 0)
        axb.text(i, cima + 0.06, txt, ha="center", va="bottom", fontsize=FS,
                 color=E.COLOR_TEXTO, zorder=5)
    for i, nv in enumerate(niveles):
        axb.plot([i + 0.31, i + 0.69], [nv, nv], color="#555555", lw=0.6, ls=(0, (2, 1.5)),
                 zorder=2)
    # C1 a la izquierda de la barra de los cargos evitados, a su altura (no sobre +1,71)
    axb.text(0.64, c1, f"C1: {TX(f'com__{c}__C1', d)}", ha="right", va="center",
             fontsize=FS, color=E.COLOR_TEXTO_SUAVE)
    # 2026-10-02 (decisión del autor): la línea de referencia es el nivel de C4,
    # la base de la ventaja que la cascada descompone; el P2P colectivo ya está
    # en el panel (a) y su línea aquí sobraba.
    axb.axhline(c4, color="#777777", lw=0.8, ls=(0, (4, 2)), zorder=1)
    axb.text(3.0, c4 + 0.05, "nivel de C4", ha="center", va="bottom",   # hueco sin barras
             fontsize=FS, color=E.COLOR_TEXTO_SUAVE, zorder=5)
    axb.set_xticks(range(len(pasos)), [p[0] for p in pasos])
    axb.set_xlim(-0.55, len(pasos) - 0.45)
    axb.set_title("(b) De C4 al mercado P2P", fontsize=FS_TIT, loc="left", pad=4)

    axa.set_ylim(piso, techo)
    # marcas enteras por encima del piso: el piso lleva la marca de corte, no cifra
    axa.set_yticks([float(t) for t in np.arange(np.floor(piso) + 1, techo)])
    for ax in (axa, axb):
        E.aplicar_estilo_ejes(ax, ylabel="Beneficio neto (MCOP)" if ax is axa else "")  # C-281: 1,95 in
        ax.grid(axis="x", visible=False)
        ax.tick_params(axis="x", labelsize=FS, length=0)
        ax.tick_params(axis="y", labelsize=FS)
        _corte(ax)
        ax.yaxis.set_major_formatter(T._FormatoEs(useOffset=False))
    axb.tick_params(axis="y", labelleft=False)
    fig.tight_layout(pad=0.3, w_pad=0.6)
    for yt in axa.get_yticks():                          # marcas del eje, no cifras
        if piso <= yt <= techo:
            MARCAS[d].update({f"{yt:.1f}".replace(".", ","), f"{yt:g}"})

    # Los datos de la cascada son los de la Fig. 2 inglesa (misma tabla con huella).
    en = pd.read_csv(DIR_EN / "fig2_cascada_E0.csv", encoding="utf-8-sig")
    casc = pd.DataFrame({
        "paso": ["C4", "C1_menos_C4", "banda", "reclasificacion", "P2P"],
        "base_MCOP": [0.0, c4, niveles[1], niveles[2], 0.0],
        "altura_MCOP": [c4, c1_c4, banda, reclas, p2p],
        "nivel_final_MCOP": [c4, niveles[1], niveles[2], niveles[3], p2p]})
    # la Fig. 2 inglesa conserva la línea del colectivo; se comparan los cinco pasos
    exige(list(en.paso) == list(casc.paso) + ["P2P_colectivo"], f"pasos de la Fig. 2 inglesa: {list(en.paso)}")
    try:
        pd.testing.assert_frame_equal(casc, en[casc.columns.tolist()].iloc[:5], check_dtype=False,
                                      rtol=1e-12, atol=1e-12)
    except AssertionError as e:
        raise SystemExit(f"[gen_figuras_articulo_es] COMPUERTA FALLIDA: la cascada no es la de "
                         f"la Fig. 2 inglesa: {e}")
    ok("cascada: mismos datos que Documentos/articulo_latam/v2/figuras/fig2_cascada_E0.csv "
       "(los cinco pasos; la línea es el P2P comunitario y no el colectivo de la inglesa)")
    casc = pd.concat([casc, pd.DataFrame({"paso": ["C4_referencia"], "base_MCOP": [0.0],
                                          "altura_MCOP": [c4], "nivel_final_MCOP": [c4]})],
                     ignore_index=True)
    nombres_casc = {"C4": "C4", "C1_menos_C4": "cargos evitados (C1 − C4)",
                    "banda": "ahorro del intercambio (banda)",
                    "reclasificacion": "efecto sobre el crédito (reclasificación)",
                    "P2P": "P2P", "C4_referencia": "nivel de C4 (línea de referencia)"}
    datos = pd.concat([
        pd.DataFrame({"panel": "a", "rotulo": [m[1].replace("\n", " ") for m in PANEL_A],
                      "clave": [f"com__E0__{m[0]}" for m in PANEL_A],
                      "beneficio_MCOP": [b[m[0]] for m in PANEL_A]}),
        pd.DataFrame({"panel": "b", "rotulo": [nombres_casc[p] for p in casc.paso],
                      "clave": ["com__E0__C4", "com__E0__C1_C4", "com__E0__banda",
                                "com__E0__reclas", "com__E0__P2P", "com__E0__C4"],
                      "base_MCOP": casc.base_MCOP, "altura_MCOP": casc.altura_MCOP,
                      "nivel_final_MCOP": casc.nivel_final_MCOP}),
    ], ignore_index=True)
    guardar(fig, nombre, datos, "pag", [
        f"eje vertical común a los dos paneles, desde {piso} MCOP (marcado con un corte)",
        "compuertas: mec__n = 7; orden de las barras = mec__E0__orden_P2Pcom; el P2P comunitario y "
        "C2 como PPA cuadran con sus brechas al peso (sin C4 mensual, alias de C4, regla 4); la "
        "cascada cierra al peso y sus cinco pasos son los de la Fig. 2 inglesa",
        "P2P comunitario (2026-10-02, decisión del autor): reemplaza como mecanismo al mercado por "
        "el colectivo, en la barra del panel (a) y en la línea discontinua del panel (b) (CANON sec. "
        "14.23, clave com__E0__P2Pcom: intercambio interno exento de cargos y residual al "
        "autogenerador colectivo sin la regla del 10 %, caso 1 en E0); el colectivo, la vía legal "
        "de hoy (com__E0__P2Pcol, 44,48), ya no se dibuja; como la línea queda casi a la altura "
        "de P2P, el rótulo de los cargos evitados va dentro de su barra, en blanco",
        "nombre (2026-10-02, decisión del autor): el P2P comunitario se rotula «P2P colectivo» en la "
        "barra, en la línea y en el CSV (CANON sec. 14.23, nota de nombre); la clave com__E0__P2Pcom y el "
        "identificador del paso P2P_comunitario conservan su nombre, y el texto de mec__E0__orden_P2Pcom "
        "dice «P2P comunitario»",
        "panel (a) con cuatro barras (2026-10-02, indicación del asesor): P2P, P2P colectivo, C1 y C4; "
        "C2, C3 y C5 se reportan en el texto y siguen en las compuertas de los siete mecanismos",
        "C5 rayado: referencia no elegible; C2 (2026-10-02) es el de la propuesta medido como PPA "
        "de todo el excedente por institución a la media de XM (CANON sec. 14.22, clave "
        "com__E0__C2ppa), no el contrato interno de CAL-52 (igual a P2P en el agregado)",
        "nombres aprobados el 2026-09-30: cargos evitados = C1 − C4, ahorro del intercambio = "
        "banda, efecto sobre el crédito = reclasificación (0,00 en E0: nadie agota su crédito); "
        "ronda B (2026-09-30), I-1: los rótulos ya no atan cada barra a un supuesto, porque esa "
        "atribución depende del orden (CANON sec. 14.21); la cascada sigue el orden de la "
        "identidad (6), que pasa por C1; alto de 2,75 a 2,30 in (ronda B y su re-revisión)"])


# ── Fig. 2, variante en evaluación: dos cascadas, E0 y E3 (2026-10-02) ──────
# Propuesta del asesor (E3 muestra los tres términos activos) y del autor: E0, la
# comunidad medida, junto a E3; cada cascada de C4 al mercado P2P, con la
# línea de referencia en C4 y una barra final del P2P colectivo. Colores
# Okabe-Ito bien distintos entre sí; C4 es la única barra neutra.
C2_C4 = "#9E9E9E"            # C4, la base (único gris)
C2_EVIT = A.OI["azul"]       # cargos evitados
C2_AHORRO = A.OI["naranja"]  # ahorro del intercambio
C2_CRED = "#CC79A7"          # efecto sobre el crédito (púrpura rojizo de Okabe-Ito)
C2_P2P = "#D55E00"           # mercado P2P (bermellón)
C2_PCOL = A.OI["verde"]      # P2P colectivo


def _cascada(ax, c: str, d: str, titulo: str) -> list[dict]:
    c4, evit = V(f"com__{c}__C4", d), V(f"com__{c}__C1_C4", d)
    ahorro, cred = V(f"com__{c}__banda", d), V(f"com__{c}__reclas", d)
    p2p, pcol, c1 = V(f"com__{c}__P2P", d), V(f"com__{c}__P2Pcom", d), V(f"com__{c}__C1", d)
    # banda y reclasificación vienen en float32 (como en la Fig. 3): tolerancia 2e-7 de P2P
    exige(abs(c4 + evit + ahorro + cred - p2p) <= PESO + 2e-7 * abs(p2p),
          f"cascada de {c}: no cierra")
    exige(abs(c4 + evit - c1) <= PESO, f"cascada de {c}: C4 + cargos evitados no es C1")
    niveles = [c4, c4 + evit, c4 + evit + ahorro, c4 + evit + ahorro + cred]
    # eje propio: el piso deja ver la barra de C4 (un cuarto del recorrido bajo C4) y
    # cae en un múltiplo del paso de las marcas; la marca del piso no se rotula (corte)
    paso = 0.5 if c == "E0" else 10.0
    alto_max = max(c1, p2p, pcol, *niveles)
    piso = float(np.floor((c4 - 0.25 * (alto_max - c4)) / paso) * paso)
    techo = alto_max + 0.12 * (alto_max - piso)
    pasos = [
        ("C4", piso, c4 - piso, C2_C4, TX(f"com__{c}__C4", d)),
        ("+ cargos\nevitados", c4, evit, C2_EVIT, TX(f"com__{c}__C1_C4", d, signo=True)),
        ("+ ahorro del\nintercambio", niveles[1], ahorro, C2_AHORRO, TX(f"com__{c}__banda", d, signo=True)),
        ("+ efecto\nsobre el\ncrédito", niveles[2], cred, C2_CRED, TX(f"com__{c}__reclas", d, signo=True)),
        ("P2P", piso, p2p - piso, C2_P2P, TX(f"com__{c}__P2P", d)),
        ("P2P\ncolectivo", piso, pcol - piso, C2_PCOL, TX(f"com__{c}__P2Pcom", d)),
    ]
    sube = (techo - piso) * 0.015
    for i, (_, y0, h, colr, txt) in enumerate(pasos):
        ax.bar(i, h, bottom=y0, width=0.62, color=colr, edgecolor="#333333", lw=0.5, zorder=3)
        ax.text(i, y0 + max(h, 0) + sube, txt, ha="center", va="bottom", fontsize=FS,
                color=E.COLOR_TEXTO, zorder=5)
    for i, nv in enumerate(niveles):
        ax.plot([i + 0.31, i + 0.69], [nv, nv], color="#555555", lw=0.6, ls=(0, (2, 1.5)), zorder=2)
    ax.text(0.64, c1, f"C1: {TX(f'com__{c}__C1', d)}", ha="right", va="center", fontsize=FS,
            color=E.COLOR_TEXTO_SUAVE)
    ax.axhline(c4, color="#777777", lw=0.8, ls=(0, (4, 2)), zorder=1)
    ax.text(3.0, c4 + sube, "nivel de C4", ha="center", va="bottom", fontsize=FS,
            color=E.COLOR_TEXTO_SUAVE, zorder=5)
    ax.set_xticks(range(len(pasos)), [p[0] for p in pasos])
    ax.set_xlim(-0.55, len(pasos) - 0.45)
    ax.set_ylim(piso, techo)
    ax.set_yticks([float(t) for t in np.arange(piso + paso, techo, paso)])
    ax.set_title(titulo, fontsize=FS_TIT, loc="left", pad=4)
    return [dict(caso=c, paso=p[0].replace("\n", " "), base_MCOP=p[1], altura_MCOP=p[2])
            for p in pasos]


def fig2_dos() -> None:
    nombre = d = "fig2_cascadas_E0_E3"
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(ANCHO_PAG, 1.95))
    filas = _cascada(axa, "E0", d, "(a) E0: la comunidad medida")
    filas += _cascada(axb, "E3", d, "(b) E3: la mayor escala bajo 100 kW")
    for ax in (axa, axb):
        E.aplicar_estilo_ejes(ax, ylabel="Beneficio neto (MCOP)" if ax is axa else "")  # C-281: 1,95 in
        ax.grid(axis="x", visible=False)
        ax.tick_params(axis="x", labelsize=FS, length=0)
        ax.tick_params(axis="y", labelsize=FS)
        _corte(ax)
        ax.yaxis.set_major_formatter(T._FormatoEs(useOffset=False))
    fig.tight_layout(pad=0.3, w_pad=1.0)
    MARCAS.setdefault(d, set())
    for ax in (axa, axb):
        lo, hi = ax.get_ylim()
        for yt in ax.get_yticks():
            if lo <= yt <= hi:
                MARCAS[d].update({f"{yt:.1f}".replace(".", ","), f"{yt:g}", f"{yt:.0f}"})
    MARCAS[d].update({"100", "1", "2", "3"})          # «100 kW» del título; renglones del eje
    guardar(fig, nombre, pd.DataFrame(filas), "pag", [
        "variante en evaluación (2026-10-02): dos cascadas, E0 (comunidad medida) y E3 (los tres "
        "términos activos), de C4 al mercado P2P, con la barra del P2P colectivo y la línea de "
        "referencia en C4; cada panel con su eje; colores Okabe-Ito distintos; letra de 8 pt",
        "compuertas: cada cascada cierra al peso (C4 + cargos evitados + ahorro del intercambio + "
        "efecto sobre el crédito = P2P) y C4 + cargos evitados = C1"])


# ── Una hora de E0 en el eje de precios (pieza F2) ──────────────────────────
def fig_hora() -> None:
    nombre = d = "fig_hora_E0"
    T._rc("G")
    T._CAPTURA.clear()
    T.PLT_G.tam = (ANCHO_PAG, 2.85)
    try:
        G.c5_banda_hora()          # con sus compuertas contra el almacén con huella
    finally:
        T.PLT_G.tam = None
    exige(bool(T._CAPTURA), "la función de la tesis no llegó a guardar")
    fig, datos, proc = T._CAPTURA["fig"], T._CAPTURA["datos"], T._CAPTURA["procedencia"]
    # 2026-10-02: el generador de la tesis rotula las marcas a 7,5 pt; aquí, 8 pt (IEEE)
    for a in fig.axes:
        a.tick_params(labelsize=FS)
    T.datos_iguales(datos, CSV_HORA_TESIS, nombre)
    ok("hora: mismos datos que Documentos/FinalTesisV2/figuras/c5_banda_hora.csv")

    # Pisos y techo: las claves del valor de un kWh en abril de 2025.
    exige(set(datos.hora) == {"2025-04-14 16:00:00"}, "la hora de ejemplo ya no es de abril de 2025")
    v = datos.set_index("institucion")
    for inst, clave in [("Udenar", "kwh__ASC__2025-04__C1"), ("Cesmag", "kwh__CEDENAR__2025-04__C1")]:
        exige(abs(float(v.loc[inst, "piso_COP_kWh"]) - V(clave, d)) <= 0.01,
              f"piso de {inst} ≠ {clave}")
    for inst in ["Mariana", "UCC", "HUDN"]:
        exige(abs(float(v.loc[inst, "techo_COP_kWh"]) - V("kwh__ASC__2025-04__CU", d)) <= 0.01,
              f"techo de {inst} ≠ kwh__ASC__2025-04__CU")
    pj = float(datos.piso_juego_COP_kWh.iloc[0])
    exige(abs(pj - V("kwh__ASC__2025-04__C1", d)) <= 0.01, "el piso del juego no es la permuta de ASC")
    ok("hora: pisos, techo y piso del juego = claves kwh__*__2025-04__* de cifras.csv")

    # Energía disponible de cada agente y volumen = lado corto (almacén con huella).
    ag, rastro_ag = G.almacen("E0", "agentes")
    h_, rastro_h = G.almacen("E0", "horas")
    x = ag[ag.fecha.astype(str) == "2025-04-14 16:00:00"].set_index("agente")
    hh = h_[h_.fecha.astype(str) == "2025-04-14 16:00:00"].iloc[0]
    vend = datos[datos.papel == "vendedor"].institucion.tolist()
    comp = datos[datos.papel == "comprador"].institucion.tolist()
    oferta = float(x.loc[vend, "sobrante"].sum())
    demanda = float(x.loc[comp, "faltante"].sum())
    vendido = float(datos[datos.papel == "vendedor"].kWh.sum())
    comprado = float(datos[datos.papel == "comprador"].kWh.sum())
    volumen = float(hh.volumen)
    exige(abs(vendido - volumen) <= 1e-4 and abs(comprado - volumen) <= 1e-4,
          "volumen ≠ lo vendido ≠ lo comprado")
    exige(abs(volumen - min(oferta, demanda)) <= 1e-4, "el volumen no es el lado corto")
    exige(oferta < demanda, "en esta hora el lado corto ya no es la oferta")
    ok(f"hora: volumen {volumen:.4f} kWh = lo vendido = lo comprado = min(oferta {oferta:.4f}, "
       f"demanda {demanda:.4f})")

    ax = fig.axes[0]
    fmt = lambda z: G.num(z, 2)                          # coma decimal, como la tesis
    fila = {lab.get_text(): yt for yt, lab in zip(ax.get_yticks(), ax.get_yticklabels())}
    exige(all(i in fila for i in comp), f"no se hallaron las filas de los compradores {list(fila)}")
    n_rec = 0
    for t in ax.texts:
        m = re.fullmatch(r"recibe (\S+) kWh", t.get_text())
        if m:
            inst = [i for i in comp if abs(fila[i] - t.get_position()[1]) < 1e-9]
            exige(len(inst) == 1, f"«{t.get_text()}» no está en la fila de un comprador")
            exige(m.group(1) == fmt(float(v.loc[inst[0], "kWh"])), f"«{t.get_text()}»: no es su energía")
            t.set_text(f"recibe {m.group(1)} de {fmt(float(x.loc[inst[0], 'faltante']))} kWh")
            n_rec += 1
    exige(n_rec == len(comp), "no se rotuló la energía de cada comprador")
    lo = ax.get_xlim()[0]
    y_c = [fila[i] for i in comp]
    ax.text(lo + 3, float(np.mean(y_c)),
            f"volumen transado: el lado corto\noferta {fmt(oferta)} kWh; demanda {fmt(demanda)} kWh"
            f"\n(sumas sin redondear)\nse transan {fmt(volumen)} kWh",
            ha="left", va="center", fontsize=FS, color=E.COLOR_TEXTO, linespacing=1.2,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#BBBBBB", lw=0.6))
    # Un solo nombre para el precio que paga cada comprador (en esta hora, el
    # uniforme: ningún techo lo corta) y glosa de los rótulos propios del modelo.
    exige(bool((datos[datos.papel == "comprador"].precio_liquidado_COP_kWh
                == datos.precio_uniforme_COP_kWh.iloc[0]).all()),
          "hora: algún comprador no paga el precio uniforme (tope en su tarifa)")
    glosas = {"precio liquidado": "precio uniforme",
              "precio del reposo": "precio de cada comprador en el reposo del juego",
              "renta inframarginal": "renta inframarginal: piso del juego − piso de Unicesmag",
              "Cesmag": "Unicesmag", "Mariana": "Unimar"}
    hechos = set()
    for t in fig.findobj(matplotlib.text.Text):
        if t.get_text() in glosas:
            hechos.add(t.get_text())
            t.set_text(glosas[t.get_text()])
    exige(hechos >= set(glosas) - {"Cesmag", "Mariana"}, f"hora: rótulos sin renombrar {set(glosas) - hechos}")
    T.renombra_instituciones(fig)          # C-267: «Unicesmag» y «Unimar» en todo rótulo
    ax.text(lo + 1, -0.95, "Caso E0, 14 de abril de 2025, 16:00", ha="left", va="bottom",
            fontsize=8.2, color=E.COLOR_TEXTO, fontweight="bold")
    T.menos_tipografico(fig)
    fig.tight_layout()

    textos = [t.get_text() for t in T._textos_visibles(fig)]
    for s in textos:
        for n in re.findall(r"\d+,\d+", s):
            IMPRESOS.setdefault(d, set()).add(n)
    for z in [pj, float(datos.precio_uniforme_COP_kWh.iloc[0]), oferta, demanda, volumen,
              *datos.kWh, *x.loc[comp, "faltante"]]:
        IMPRESOS[d].discard(fmt(z))
    exige(not IMPRESOS[d], f"hora: números impresos que no salen de los datos: {IMPRESOS[d]}")
    for z in [pj, float(datos.precio_uniforme_COP_kWh.iloc[0]), oferta, demanda, volumen,
              *datos.kWh, *x.loc[comp, "faltante"]]:
        IMPRESOS[d].add(fmt(z))

    salida = datos.copy()
    salida["institucion"] = salida.institucion.replace({"Cesmag": "Unicesmag", "Mariana": "Unimar"})
    salida["disponible_kWh"] = [float(x.loc[i, "sobrante" if p == "vendedor" else "faltante"])
                                for i, p in zip(datos.institucion, datos.papel)]
    salida["oferta_kWh"], salida["demanda_kWh"], salida["volumen_kWh"] = oferta, demanda, volumen
    guardar(fig, nombre, salida, "pag", [
        "reutiliza sin modificar reformateo/documento/scripts/gen_tesis_figuras.py, función "
        "c5_banda_hora() (Figura 5.1 de la tesis; la misma de Documentos/Tesis_entrega/figuras/"
        "banda_hora), con sus compuertas; se añaden el cuadro del volumen como lado corto y la "
        "energía que pedía cada comprador («recibe x de y kWh»), que la figura de la tesis no rotula",
        *proc, *rastro_ag, *rastro_h,
        "pisos (695,68 y 619,93) y techo (734,30) = kwh__ASC__2025-04__C1, "
        "kwh__CEDENAR__2025-04__C1 y kwh__ASC__2025-04__CU; piso del juego = la permuta de ASC",
        "el precio uniforme y las energías de la hora (vende, recibe, oferta, demanda, volumen) "
        "salen del almacén de E0 con huella y NO están en cifras.csv: si el texto las cita, hay "
        "que registrarlas antes"])


# ── Fig. 3: los trece casos, con el P2P comunitario (variante española) ─────
LEY_FIG3 = {  # serie -> rótulo de la leyenda
    "C1_C4": "cargos evitados (C1 − C4)",
    "C1_C4_neg": "C1 − C4 < 0 (C4 supera a C1)",
    "P2P_C1": "ahorro del intercambio + efecto\nsobre el crédito (P2P − C1)",
    "P2P_C4": "P2P − C4",
    "P2Pcom_C4": "P2P colectivo − C4",          # antes «P2P comunitario» (nombre del 2026-10-02)
}


def fig3() -> None:
    """Variante española propia (2026-10-02): la de la figura inglesa
    (`gen_figuras_articulo.fig3`, sin modificar), con los nombres aprobados y el
    rombo del P2P comunitario − C4 (CANON §14.23, claves com__<caso>__P2Pcom_C4)
    en lugar del mercado por el colectivo − C4, que deja de ser mecanismo."""
    nombre = d = "fig3_trece_casos"
    casos = A.CASOS
    c1c4 = np.array([V(f"com__{c}__C1_C4", d) for c in casos])
    p2pc1 = np.array([V(f"com__{c}__P2P_C1", d) for c in casos])
    p2pc4 = np.array([V(f"com__{c}__P2P_C4", d) for c in casos])
    pcomc4 = np.array([V(f"com__{c}__P2Pcom_C4", d) for c in casos])
    exige(np.all(np.abs(c1c4 + p2pc1 - p2pc4) <= PESO), "fig3: las partes no suman P2P − C4")
    exige(np.all(p2pc1 > 0), "fig3: P2P − C1 no es positivo en todos los casos")
    for c, v in zip(casos, pcomc4):
        exige(abs(v - (V(f"com__{c}__P2Pcom", d) - V(f"com__{c}__C4", d))) <= PESO,
              f"fig3 {c}: com__{c}__P2Pcom_C4 no es P2P comunitario − C4 al peso")
    exige(np.all(pcomc4 > 0), "fig3: P2P comunitario − C4 no es positivo en los 13 casos")
    # las tres series compartidas son, al peso, las de la Fig. 3 inglesa
    en = pd.read_csv(DIR_EN / f"{nombre}.csv", encoding="utf-8-sig")
    exige(list(en.caso) == list(casos), "fig3: casos de la figura inglesa")
    for col, v in [("C1_menos_C4_MCOP", c1c4), ("P2P_menos_C1_MCOP", p2pc1), ("P2P_menos_C4_MCOP", p2pc4)]:
        exige(np.all(np.abs(en[col].to_numpy() - v) <= 1e-12), f"fig3: {col} no es el de la figura inglesa")
    ok("fig3: C1 − C4 + P2P − C1 = P2P − C4 al peso y las tres series = las de la Fig. 3 inglesa; "
       "P2P comunitario − C4 = com__*__P2Pcom − com__*__C4 al peso, positivo en los 13 casos")

    fig, ax = plt.subplots(figsize=(ANCHO_COL, 3.45))   # 3,05 -> 3,45 in con letra de 8 pt
    x = np.arange(len(casos))
    w = 0.66
    pos_c1c4 = np.clip(c1c4, 0, None)
    neg_c1c4 = np.clip(c1c4, None, 0)
    lumas = {n: A.luma(col) for n, col in [("C1 − C4", A.C_C1C4), ("C1 − C4 < 0", A.C_C1C4_NEG),
                                            ("P2P − C1", A.C_P2PC1)]}
    orden_l = sorted(lumas.values())
    exige(min(b - a for a, b in zip(orden_l, orden_l[1:])) >= 0.15, f"fig3: rellenos poco distintos en gris {lumas}")
    h = {}
    h["C1_C4"] = ax.bar(x, pos_c1c4, width=w, color=A.C_C1C4, edgecolor="#333333", lw=0.4, zorder=3)
    h["C1_C4_neg"] = ax.bar(x, neg_c1c4, width=w, color=A.C_C1C4_NEG, edgecolor="#333333", lw=0.4, zorder=3)
    h["P2P_C1"] = ax.bar(x, p2pc1, bottom=pos_c1c4, width=w, color=A.C_P2PC1, edgecolor="#333333", lw=0.4,
                         zorder=3)
    h["P2P_C4"] = ax.scatter(x, p2pc4, marker="_", s=70, lw=1.4, color="#000000", zorder=5)
    h["P2Pcom_C4"] = ax.scatter(x, pcomc4, marker="D", s=13, color=A.C_COL, edgecolor="#000000", lw=0.5,
                                zorder=6)
    ax.axhline(0, color="#333333", lw=0.7, zorder=4)
    ax.set_xticks(x, casos)
    ax.tick_params(axis="x", labelsize=FS)
    ax.tick_params(axis="y", labelsize=FS)
    ax.set_xlim(-0.6, len(casos) - 0.4)
    ax.set_ylim(neg_c1c4.min() - 1.5, max((pos_c1c4 + p2pc1).max(), pcomc4.max()) * 1.08)
    E.aplicar_estilo_ejes(ax, xlabel="Caso", ylabel="Diferencia con C4 (MCOP)")
    ax.grid(axis="x", visible=False)
    ax.yaxis.set_major_formatter(T._FormatoEs(useOffset=False))
    # leyenda bajo el eje, en dos columnas (como la traducción anterior)
    orden = ["C1_C4", "P2P_C1", "C1_C4_neg", "P2P_C4", "P2Pcom_C4"]
    fig.legend([h[k] for k in orden], [LEY_FIG3[k] for k in orden], loc="lower center",
               bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False, fontsize=FS,
               handlelength=1.3, columnspacing=0.8, labelspacing=0.35, handletextpad=0.4)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    alto_ley = fig.legends[0].get_window_extent(r).height / fig.bbox.height
    fig.tight_layout(pad=0.3, rect=[0, alto_ley + 0.04, 1, 1])
    fig.canvas.draw()
    exige(fig.legends[0].get_window_extent(r).y1 < ax.get_tightbbox(r).y0 - 1, "fig3: la leyenda pisa el eje")
    T.menos_tipografico(fig)
    lo, hi = ax.get_ylim()
    for yt in ax.get_yticks():                               # marcas del eje, no cifras
        if lo <= yt <= hi:
            MARCAS[d].update({f"{yt:g}".replace("-", ""), f"{yt:.1f}".replace(".", ",")})
    IMPRESOS[d] = set()                                      # ninguna cifra impresa salvo las marcas

    datos = pd.DataFrame({"caso": casos, "C1_menos_C4_MCOP": c1c4, "P2P_menos_C1_MCOP": p2pc1,
                          "P2P_menos_C4_MCOP": p2pc4, "P2Pcom_menos_C4_MCOP": pcomc4})
    guardar(fig, nombre, datos, "col", [
        "variante española propia (2026-10-02); la figura inglesa (gen_figuras_articulo.py, fig3) y "
        "su CSV no se tocan",
        "barras apiladas con signo: cargos evitados C1 − C4 (azul; azul claro si es negativo, E4, E5 "
        "e I1) y ahorro del intercambio + efecto sobre el crédito P2P − C1 (naranja) sobre cero; "
        "raya negra = P2P − C4; rombo verde = P2P colectivo − C4",
        "nombre (2026-10-02, decisión del autor): el P2P comunitario se rotula «P2P colectivo» en la "
        "leyenda (CANON sec. 14.23, nota de nombre); la columna P2Pcom_menos_C4_MCOP y las claves "
        "conservan su nombre",
        "P2P comunitario (CANON sec. 14.23, claves com__<caso>__P2Pcom_C4): reemplaza como "
        "mecanismo al mercado por el colectivo, que era el rombo de la figura anterior "
        "(com__<caso>__P2Pcol_C4, la vía legal de hoy, ya no se dibuja); en E3 el rombo (40,38) "
        "queda sobre la barra (35,85), y el eje sube hasta él",
        "compuertas: las tres series compartidas son, al peso, las de "
        "Documentos/articulo_latam/v2/figuras/fig3_trece_casos.csv; P2P comunitario − C4 = "
        "com__*__P2Pcom − com__*__C4 al peso; rellenos distintos en gris; la leyenda no pisa el eje"])


# ── Figs. 3 y 4: las inglesas traducidas, con los nombres nuevos ────────────
TRAD_NUEVOS = {
    "C1 − C4 (case-2 charges)": "cargos evitados (C1 − C4)",
    "C1 − C4 < 0 (C4 leads C1)": "C1 − C4 < 0 (C4 supera a C1)",
    "P2P − C1 (band + reclass.)": "ahorro del intercambio + efecto\nsobre el crédito (P2P − C1)",
    "P2P via collective − C4": "P2P por el colectivo − C4",
    # Fig. 4: desde el 2026-10-02 el P2P comunitario reemplaza al colectivo como
    # mecanismo y no está en el GSA; la columna se conserva y se rotula como lo
    # que es, la vía legal de hoy (los datos no cambian)
    "P2P coll.\n− C1": "Vía legal\n(colectivo)\n− C1",
}


# ── Fig. 4: P(inversión) del GSA con el P2P colectivo (CANON §13.9) ────────
# 2026-10-02: corrida del GSA con C2 como PPA y P2P colectivo (bloque 11 del
# verificador; claves gsa__<caso>__<brecha>__p|lo|hi). El artículo dibuja sus
# cinco casos y las brechas de los mecanismos centrales, sin C2 ni C5
# (indicación del asesor); la tesis, los 12 casos con C2 y C5.
BRECHAS_ART = [("P2P_C1", "P2P\n− C1"), ("P2P_C4", "P2P\n− C4"),
               ("P2Pcom_C1", "P2P col.\n− C1"), ("P2Pcom_C4", "P2P col.\n− C4"),
               ("C4_C1", "C1\n− C4")]
BRECHAS_TES = BRECHAS_ART + [("C2ppa_C1", "C2\n− C1"), ("C2ppa_C4", "C2\n− C4"),
                             ("P2P_C5", "P2P\n− C5")]
CASOS_ART = ["E0", "E3", "E4", "I1", "SINU"]
CASOS_TES = ["E0", "E2", "E4", "E1", "E3", "E5", "P1", "P2", "K1", "I1", "N1", "SINU"]


def _mapa_gsa(nombre: str, casos: list, brechas: list, caja: str, alto: float) -> None:
    from matplotlib.colors import LinearSegmentedColormap
    d = nombre
    P = np.zeros((len(casos), len(brechas)))
    filas = []
    for i, c in enumerate(casos):
        for j, (b, _) in enumerate(brechas):
            p, lo, hi = (V(f"gsa__{c}__{b}__{s}", d) for s in ["p", "lo", "hi"])
            exige(lo <= p <= hi, f"GSA {c} {b}: P fuera de su intervalo")
            exige(p != 0 or (lo == 0 and hi == 0), f"GSA {c} {b}: P nula con intervalo no nulo")
            P[i, j] = p
            filas.append(dict(caso=c, brecha=b, p_pct=p, lo_pct=lo, hi_pct=hi,
                              n_base=V(f"gsa__{c}__n", d)))
        for b, k, s in [("P2P_C1", "P2P_C1", 1), ("P2P_C4", "P2P_C4", 1), ("C4_C1", "C1_C4", -1),
                        ("P2Pcom_C4", "P2Pcom_C4", 1)]:
            exige(abs(V(f"gsa__{c}__{b}__base", d) - s * V(f"com__{c}__{k}", d)) <= PESO,
                  f"GSA {c} {b}: el punto base no es el de la matriz (¿signo?)")
    ok(f"{nombre}: {len(casos)} casos × {len(brechas)} brechas; lo ≤ p ≤ hi; punto base = matriz")

    ancho = ANCHO_COL if caja == "col" else ANCHO_PAG
    cmap = LinearSegmentedColormap.from_list("azul_oi", ["#FFFFFF", "#9CCBE8", A.OI["azul"], "#003B5C"])
    fig = plt.figure(figsize=(ancho, alto))
    izq, abajo = 0.62 / ancho, 0.62 / alto        # margen izquierdo y pie, en pulgadas
    ax = fig.add_axes([izq, abajo + 0.08 / alto, 1 - izq - 0.04, 1 - abajo - 0.58 / alto])
    cax = fig.add_axes([izq, abajo - 0.20 / alto, 1 - izq - 0.04, 0.07 / alto])
    im = ax.imshow(P, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    for i, c in enumerate(casos):
        for j, (b, _) in enumerate(brechas):
            p = P[i, j]
            if p == 0:
                ax.text(j, i, "0", ha="center", va="center", fontsize=FS, color="#8A8A8A")
                continue
            colt = "white" if p > 55 else E.COLOR_TEXTO
            pt = TX(f"gsa__{c}__{b}__p", d).replace(" %", "")
            lo = TX(f"gsa__{c}__{b}__lo", d).replace(" %", "")
            hi = TX(f"gsa__{c}__{b}__hi", d).replace(" %", "")
            ax.text(j, i - 0.17, pt, ha="center", va="center", fontsize=FS, color=colt,
                    fontweight="bold")
            ax.text(j, i + 0.22, f"{lo}–{hi}", ha="center", va="center", fontsize=FS, color=colt)
    ax.set_xticks(range(len(brechas)), [r for _, r in brechas], fontsize=FS)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(casos)), [f"{c} ({TX(f'gsa__{c}__n', d)})" for c in casos],
                  fontsize=FS)
    ax.set_xticks(np.arange(-0.5, len(brechas)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(casos)), minor=True)
    ax.grid(which="minor", color="#D0D0D0", lw=0.5)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="both", length=0)
    for s in ax.spines.values():
        s.set_linewidth(0.6)
        s.set_color("#888888")
    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    cb.set_label("Probabilidad de inversión en la caja (%);\ndebajo de cada valor, su intervalo al 95 %",
                 fontsize=FS, labelpad=1.5)
    cb.ax.tick_params(labelsize=FS, length=2)
    cb.outline.set_linewidth(0.5)
    guardar(fig, nombre, pd.DataFrame(filas), caja, [
        "corrida del GSA con C2 como PPA y P2P colectivo (CANON sec. 13.9, bloque 11 del verificador); "
        "claves gsa__<caso>__<brecha>__p|lo|hi y gsa__<caso>__n de cifras.csv",
        "celda con «0»: ninguna inversión en la muestra; debajo de cada valor no nulo, su intervalo al "
        "95 % (sin «%»; la unidad está en la barra); la brecha de clave C4_C1 se rotula «C1 − C4», "
        "porque P(inversión) no depende del sentido de la resta",
        "letra de 8 pt (IEEE)"])


def fig4() -> None:
    _mapa_gsa("fig4_gsa_inversion", CASOS_ART, BRECHAS_ART, "col", 2.50)


def fig4_tesis() -> None:
    _mapa_gsa("fig4_gsa_inversion_tesis", CASOS_TES, BRECHAS_TES, "pag", 5.20)


def desde_ingles(func: str, nombre: str, alto: float | None) -> None:
    T._rc("A")
    T._CAPTURA.clear()
    getattr(A, func)()
    exige(bool(T._CAPTURA), f"{nombre}: el generador inglés no llegó a guardar")
    fig, datos = T._CAPTURA["fig"], T._CAPTURA["datos"]
    T.datos_iguales(datos, DIR_EN / f"{nombre}.csv", nombre)
    T.traduce_figura(fig)
    if func == "fig4":
        # «Vía legal (colectivo) − C1» ocupa tres líneas: el mapa baja un poco
        # para que la cabecera quepa en el lienzo (solo composición)
        ax = fig.axes[0]
        p = ax.get_position()
        ax.set_position([p.x0, p.y0, p.width, p.height - 0.03])
        # Ronda B (2026-09-30), C-1: la figura baja de 4,30 a 3,55 in de alto
        # para dejar sitio al bloque inglés. Se conservan en pulgadas el margen
        # inferior, la barra de color y el margen de la cabecera; solo se
        # acortan las filas del mapa (solo composición, los datos no cambian).
        h0 = fig.get_size_inches()[1]
        h1 = 3.55
        posiciones = []
        for k, a in enumerate(fig.axes):
            q = a.get_position()
            y0_in, alto_in = q.y0 * h0, q.height * h0
            if k == 0:                                 # el mapa: pierde lo que baja la figura
                alto_in -= h0 - h1
            posiciones.append((a, [q.x0, y0_in / h1, q.width, alto_in / h1]))
        fig.set_size_inches(ANCHO_COL, h1)
        for a, pos in posiciones:
            a.set_position(pos)
    csv = (DIR_EN / f"{nombre}.csv").read_text(encoding="utf-8-sig")
    guardar(fig, nombre, datos, "col", [
        f"generador inglés reutilizado sin modificar: gen_figuras_articulo.py, función {func}() "
        f"(nota del generador: {T._CAPTURA['nota']})",
        "textos traducidos con el diccionario cerrado TRAD de gen_figuras_entrega.py"
        + (", con los nombres aprobados el 2026-09-30 en la leyenda (cargos evitados; ahorro "
           "del intercambio + efecto sobre el crédito); leyenda bajo el eje" if func == "fig3" else
           "; sin cambios de contenido; la columna P2Pcol − C1 se rotula «Vía legal (colectivo) − C1» "
           "(2026-10-02: el P2P comunitario, que no está en el GSA, reemplaza al colectivo como "
           "mecanismo; los datos no cambian)"),
        "compuerta: los datos son los de Documentos/articulo_latam/v2/figuras/"
        f"{nombre}.csv (sha256 del CSV inglés {hashlib.sha256(csv.encode('utf-8')).hexdigest()[:16]}…)"])
    exige(sha(DIR_SAL / f"{nombre}.csv") == sha(DIR_EN / f"{nombre}.csv"),
          f"{nombre}: el CSV no es, byte a byte, el de la figura inglesa")
    ok(f"{nombre}: CSV idéntico byte a byte al de la figura inglesa")


# ── Comprobaciones de las salidas ───────────────────────────────────────────
def comprueba() -> None:
    from PIL import Image
    from pypdf import PdfReader
    fuentes = H.lee_fuentes_es([str(CIFRAS)])
    for r in RES:
        n = r["nombre"]
        pdf = DIR_SAL / f"{n}.pdf"
        caja = PdfReader(pdf).pages[0].mediabox
        w, h = float(caja.width) / 72, float(caja.height) / 72
        exige(abs(w - r["ancho"]) < 0.01 and abs(h - r["alto"]) < 0.01, f"{n}.pdf mide {w:.4f} × {h:.4f}")
        with Image.open(DIR_SAL / f"{n}.png") as im:
            px = im.size
        exige(abs(px[0] - r["ancho"] * DPI) <= 1, f"{n}.png: {px[0]} px de ancho")
        texto = H._canoniza_menos(PdfReader(pdf).pages[0].extract_text())
        exige("Cesmag" not in texto, f"{n}: el PDF rotula «Cesmag»")
        exige(not re.search(r"\bASC\b|CEDENAR", texto, re.IGNORECASE),
              f"{n}: el PDF nombra a un comercializador")
        malos = []
        for x in H.extrae_numeros_es(texto):
            forma = x.entero + ("," + x.decimales if x.decimales else "")
            if forma in MARCAS[n] and not x.signo:
                continue
            # pypdf une marcas de eje contiguas con espacios («620 640 660»)
            partes = re.split(r"[\s  ]+", x.texto.strip())
            if len(partes) > 1 and not x.signo and all(p in MARCAS[n] for p in partes):
                continue
            if x.punto:
                malos.append(f"{x.texto} (punto decimal)")
            elif n in IMPRESOS and forma not in IMPRESOS[n]:
                malos.append(f"{x.texto} (no lo escribe ninguna clave de la figura)")
            elif n != "fig_hora_E0" and not fuentes.presente(x):
                malos.append(f"{x.texto} (no está en cifras.csv)")
        exige(not malos, f"{n}: números impresos no justificados: {malos}")
        print(f"  {n:<20} {r['caja']:<4} {w:.5f} × {h:.3f} in  PNG {px[0]} × {px[1]} px  "
              f"letra mínima {r['letra']:.2f} pt")
    ok("cajas de los PDF, PNG a 600 ppp, letra ≥ 8 pt, Unicesmag y Unimar y números impresos justificados")
    t1 = PdfReader(DIR_SAL / "fig1_comunidad.pdf").pages[0].extract_text()
    exige("Unicesmag" in t1 and "Unimar" in t1, "fig1_comunidad: no rotula «Unicesmag» y «Unimar»")


def main() -> int:
    IMPRESOS["fig1_comunidad"] = set()                   # Fig. 1: ninguna cifra
    IMPRESOS["fig1_mercados"] = set()
    T.TRAD.update(TRAD_NUEVOS)                           # solo en este proceso
    A.compuertas_comunidad()
    exige(sha(CIFRAS) == A.SHA, "cifras.csv no tiene la huella e1/L")
    exige(A.RUTA_CIFRAS == "cifras_articulo_2026-09-30/cifras.csv",
          f"el generador inglés lee {A.RUTA_CIFRAS}, no la tabla del 30")
    rc_articulo()
    fig1()                                               # 2 × 2, para la tesis
    rc_articulo()
    fig1_col()        # Fig. 1 del artículo desde el 2026-10-03 (una columna)
    rc_articulo()
    fig2()
    rc_articulo()
    fig2_dos()        # Fig. 2 vigente desde el 2026-10-03 (dos cascadas, E0 y E3); fig2() queda por sus compuertas
    fig_hora()
    rc_articulo()
    fig3()                                               # variante española (P2P comunitario)
    rc_articulo()
    fig4()
    rc_articulo()
    fig4_tesis()
    comprueba()
    print("[gen_figuras_articulo_es] FIGURAS EN ESPAÑOL ESCRITAS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
