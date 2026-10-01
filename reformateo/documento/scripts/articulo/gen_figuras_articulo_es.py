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
                     del mercado por el colectivo. Página.
  fig_hora_E0        una hora de E0 en el eje de precios (pieza F2): la figura
                     de la tesis más el volumen transado como lado corto y la
                     energía disponible de cada comprador. Página.
  fig3_trece_casos   la figura inglesa traducida, con los nombres nuevos en la
                     leyenda. Columna.
  fig4_gsa_inversion la figura inglesa traducida, sin cambios de contenido.
                     Columna.

Compuertas (fallan en voz alta con SystemExit):
  1. huella e1/L de cifras.csv (la del generador inglés) y coherencia de
     texto_en con valor en cada clave usada;
  2. Fig. 2: los siete mecanismos siguen el orden de `mec__E0__orden`, C2 es
     P2P al peso, la cascada cierra al peso y sus datos son los de la Fig. 2
     inglesa;
  3. Figs. 3 y 4: sus datos son, byte a byte en el CSV, los de la figura
     inglesa;
  4. figura de la hora: sus datos son los de la Figura 5.1 de la tesis
     (`Documentos/FinalTesisV2/figuras/c5_banda_hora.csv`); los pisos y el
     techo son las claves `kwh__*__2025-04__*` de cifras.csv; el volumen es la
     suma de lo vendido y de lo comprado, y es el lado corto;
  5. cada PDF mide la caja pedida y cada PNG su ancho a 600 ppp; letra ≥ 7 pt
     en todo texto visible; nada se sale del lienzo; ninguna palabra inglesa;
     la institución se rotula «CESMAG»;
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
LETRA_MIN, DPI = 7.0, 600
FS, FS_TIT = 7.0, 8.0
PESO = A.PESO
INST = ["Udenar", "CESMAG", "Mariana", "UCC", "HUDN"]     # mismo orden en los paneles
VENDEN = {"Udenar", "CESMAG"}                              # papeles de la hora de ejemplo

C_ENERGIA = "#222222"
C_LIQ = "#6E6E6E"
C_PAGO = "#8A5A00"

# Números estructurales impresos que no son cifras del canon: normas, artículos,
# numerales, supuestos y marcas de eje. pypdf une a veces dos marcas contiguas
# con un espacio, que el lector español toma por separador de millares.
MARCAS = {
    "fig1_comunidad": {"174", "25", "101072", "101", "072", "18", "21", "19", "1", "2"},
    "fig2_cascada_E0": {"1", "2", "7"},
    "fig_hora_E0": {"620", "640", "660", "680", "700", "720", "740", "14", "2025", "16", "00", "0"},
    "fig3_trece_casos": {"0", "10", "20", "30", "40", "50", "2"},
    "fig4_gsa_inversion": {"0", "20", "40", "60", "80", "100", "80100", "95"},
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


# ── Guardado y medidas ──────────────────────────────────────────────────────
def guardar(fig, nombre: str, datos: pd.DataFrame, caja: str, procedencia: list[str]) -> None:
    ancho = ANCHO_COL if caja == "col" else ANCHO_PAG
    w, h = fig.get_size_inches()
    exige(abs(w - ancho) < 1e-6, f"{nombre}: la figura mide {w:.5f} in, la caja es {ancho:.5f}")
    letra = T.letra_minima(fig, nombre)
    T.dentro_del_lienzo(fig, nombre)
    for t in T._textos_visibles(fig):
        m = T.VETADAS.search(t.get_text())
        exige(m is None, f"{nombre}: queda inglés: «{t.get_text()}»")
        exige("Cesmag" not in t.get_text(), f"{nombre}: rotula «Cesmag», no «CESMAG»")
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
    nombre = "fig1_comunidad"
    W, Hh = ANCHO_PAG, 3.40
    fig = plt.figure(figsize=(W, Hh))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, Hh)
    ax.axis("off")
    suave = E.COLOR_TEXTO_SUAVE
    ret = "Comercializador de cada miembro (ASC Ingeniería o CEDENAR)"

    # ── (a) Lo que las reglas permiten ──
    xa, wa = 0.06, 3.40
    ax.text(xa, Hh - 0.05, "(a) Lo que las reglas permiten", ha="left", va="top",
            fontsize=FS_TIT, fontweight="bold", color=E.COLOR_TEXTO)
    # C1
    ax.text(xa, 3.10, "C1: autogeneración individual (CREG 174, art. 25)", ha="left", va="top",
            fontsize=FS, style="italic", color=E.COLOR_TEXTO)
    _caja(ax, xa, 2.56, wa, 0.34, [(ret, "normal"),
                                   ("crédito y exceso de cada miembro, con el numeral de su planta",
                                    "normal")], fc="#F2F2F2")
    cs = _miembros(ax, xa, wa, 2.08, 0.24)
    for cx in cs:
        _flecha(ax, (cx, 2.32), (cx, 2.56), ls="--", color=C_LIQ, estilo="<|-|>")
    ax.plot([xa, xa + wa], [1.98, 1.98], color="#CCCCCC", lw=0.6)
    # C4
    ax.text(xa, 1.93, "C4: autogeneración colectiva (CREG 101 072, arts. 18–21)", ha="left",
            va="top", fontsize=FS, style="italic", color=E.COLOR_TEXTO)
    _caja(ax, xa, 1.32, wa, 0.44, [(ret, "normal"),
                                   ("cada parte, contra la importación de su miembro (art. 25)",
                                    "normal"),
                                   ("caso 2 para todos: Cv más cargos de red", "bold")], fc="#F2F2F2")
    _caja(ax, xa, 0.76, wa, 0.36, [("Fondo común: la inyección de los cinco miembros", "normal"),
                                   ("repartida con el porcentaje del art. 19 (aquí, igual)", "normal"),
                                   ("sin pagos entre miembros", "normal")],
          fc="#EAF6F1", ec=A.C_COL, ls=(0, (4, 2)))
    cs = _miembros(ax, xa, wa, 0.38, 0.24)
    for cx in cs:
        _flecha(ax, (cx, 0.62), (cx, 0.76), color=C_ENERGIA)
        _flecha(ax, (cx, 1.12), (cx, 1.32), ls="--", color=C_LIQ)

    # separador de paneles
    ax.plot([3.57, 3.57], [0.34, Hh - 0.05], color="#BBBBBB", lw=0.6)

    # ── (b) Lo que el mercado supone ──
    xb, wb = 3.68, 3.40
    ax.text(xb, Hh - 0.05, "(b) Lo que el mercado supone", ha="left", va="top",
            fontsize=FS_TIT, fontweight="bold", color=E.COLOR_TEXTO)
    ax.text(xb, 3.10, "Mercado P2P con los dos supuestos (ninguna regla los prevé)", ha="left",
            va="top", fontsize=FS, style="italic", color=E.COLOR_TEXTO)
    _caja(ax, xb, 2.44, wb, 0.46, [(ret, "normal"),
                                   ("Supuesto 1: residual por miembro", "bold"),
                                   ("fuera del colectivo, con el numeral de su planta", "normal")],
          fc="#F2F2F2")
    cs = _miembros(ax, xb, wb, 1.78, 0.32, papeles=True)
    for cx in cs:
        _flecha(ax, (cx, 2.10), (cx, 2.44), ls="--", color=C_LIQ, estilo="<|-|>")
    ax.text((cs[1] + cs[2]) / 2, 2.27, "residual", ha="center", va="center", fontsize=FS,
            color=suave)
    _caja(ax, xb, 0.58, wb, 0.58, [("Intercambio interno, cada hora: precio uniforme", "normal"),
                                   ("con tope en la tarifa de cada comprador", "normal"),
                                   ("Supuesto 2: el intercambio no paga cargos", "bold"),
                                   ("ni Cv ni cargos de red, aunque usa la red de CEDENAR", "normal")],
          fc="#FFF4E0", ec=A.C_P2PC1)
    d = 0.07
    for n, cx in zip(INST, cs):
        if n in VENDEN:   # energía hacia el intercambio; pago de vuelta al vendedor
            _flecha(ax, (cx - d, 1.78), (cx - d, 1.16), color=C_ENERGIA)
            _flecha(ax, (cx + d, 1.16), (cx + d, 1.78), ls=":", color=C_PAGO, lw=1.0)
        else:             # energía hacia el comprador; su pago hacia el intercambio
            _flecha(ax, (cx - d, 1.16), (cx - d, 1.78), color=C_ENERGIA)
            _flecha(ax, (cx + d, 1.78), (cx + d, 1.16), ls=":", color=C_PAGO, lw=1.0)

    # ── Leyenda de trazos, a todo lo ancho ──
    yl = 0.15
    muestras = [(0.9, "-", C_ENERGIA, "energía", 1.0),
                (2.3, "--", C_LIQ, "liquidación con el comercializador", 1.0),
                (4.6, ":", C_PAGO, "pago interno, del comprador al vendedor", 1.2)]
    for x, ls, col, txt, lw in muestras:
        ax.plot([x, x + 0.3], [yl, yl], ls=ls, color=col, lw=lw)
        ax.text(x + 0.36, yl, txt, ha="left", va="center", fontsize=FS, color=E.COLOR_TEXTO)

    datos = pd.DataFrame({
        "panel": ["a", "a", "a", "a", "b", "b", "b", "leyenda", "leyenda", "leyenda"],
        "elemento": ["C1: comercializador de cada miembro", "C1: miembros", "C4: fondo común",
                     "C4: comercializador de cada miembro, caso 2",
                     "mercado: comercializador de cada miembro (supuesto 1)",
                     "mercado: miembros (vende o compra en la hora)",
                     "mercado: intercambio interno (supuesto 2)",
                     "energía", "liquidación con el comercializador", "pago interno"],
        "nota": ["art. 25 de la CREG 174; numeral de la planta", "; ".join(INST),
                 "arts. 18-21 y 19 de la CREG 101 072; porcentaje igual",
                 "caso 2 del art. 20: Cv más cargos de red",
                 "residual por miembro, fuera del colectivo, con el numeral de su planta",
                 "; ".join(INST), "precio uniforme con tope en la tarifa; sin cargos",
                 "trazo continuo", "trazo discontinuo", "trazo punteado"]})
    guardar(fig, nombre, datos, "pag", [
        "esquema sin cifras del canon: solo números de norma, artículo, numeral, caso y supuesto",
        "corrige la figura del 2026-09-29, que dibujaba el mercado P2P dentro del colectivo "
        "(notas 14 y 18 del autor): el residual del mercado se liquida por miembro, fuera del "
        "colectivo (supuesto 1), y el intercambio interno no paga cargos (supuesto 2)",
        "papeles de la hora de ejemplo del panel (b): venden Udenar y CESMAG y compran Mariana, "
        "UCC y HUDN, como en la hora de fig_hora_E0; cambian de hora en hora"])


# ── Fig. 2: los siete mecanismos y la cascada de E0 ─────────────────────────
MECANISMOS = [  # (clave, rótulo, color, rayado)
    ("P2P", "P2P", A.C_TOTAL_P2P, None),
    ("C2", "C2\n(igual a P2P\nen el agregado)", A.C_TOTAL_P2P, None),
    ("C1", "C1", "#999999", None),
    ("C4", "C4", A.C_TOTAL_REF, None),
    ("P2Pcol", "P2P por el\ncolectivo", A.C_COL, None),
    ("C5", "C5\n(referencia,\nno elegible)", "white", "////"),
    # C3: contrafáctico declarado (tesis §6.5 y Tabla 6.x: «contrafáctico declarado,
    # no un régimen elegible»); el artículo usa un único calificativo, «contrafáctico»
    # (ronda 1 de A3, M-12)
    ("C3", "C3\n(contrafáctico)", "white", "\\\\\\\\"),
]
ORDEN_CANON = {"P2P": "P2P", "C2": "C2", "C1": "C1", "C4": "C4", "P2Pcol": "P2P colectivo",
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
    exige(abs(b["C2"] - b["P2P"]) <= PESO, "C2 no es P2P en el agregado de E0 (regla 5)")
    orden = sorted(MECANISMOS, key=lambda m: -round(b[m[0]], 6))   # al peso: C2 = P2P
    esperado = A.T("mec__E0__orden", d)
    exige(" > ".join(ORDEN_CANON[m[0]] for m in orden).replace("P2P > C2", "P2P = C2")
          == esperado, f"el orden de los mecanismos no es el de mec__E0__orden ({esperado})")
    exige([m[0] for m in orden] == [m[0] for m in MECANISMOS], "MECANISMOS no está ordenado")
    ok(f"E0: siete mecanismos en el orden de mec__E0__orden ({esperado}); C2 = P2P al peso")

    c4, c1_c4 = b["C4"], V(f"com__{c}__C1_C4", d)
    banda, reclas = V(f"com__{c}__banda", d), V(f"com__{c}__reclas", d)
    p2p, col, c1 = b["P2P"], b["P2Pcol"], b["C1"]
    exige(abs(c4 + c1_c4 + banda + reclas - p2p) <= PESO, "cascada de E0: no cierra al peso")
    exige(abs(c4 + c1_c4 - c1) <= PESO, "cascada de E0: C4 + cargos evitados no es C1")
    niveles = [c4, c4 + c1_c4, c4 + c1_c4 + banda, c4 + c1_c4 + banda + reclas]
    ok("cascada de E0: C4 + cargos evitados + ahorro del intercambio + efecto sobre el crédito "
       "= P2P al peso")

    fig, (axa, axb) = plt.subplots(1, 2, sharey=True, figsize=(ANCHO_PAG, 2.75),
                                   gridspec_kw=dict(width_ratios=[7, 5]))
    piso, techo = A.eje_truncado(list(b.values()) + niveles, sobre=0.5)

    # (a) los siete mecanismos
    for i, (m, rot, colr, rayado) in enumerate(MECANISMOS):
        axa.bar(i, b[m] - piso, bottom=piso, width=0.64, color=colr, hatch=rayado,
                edgecolor="#333333" if rayado is None else "#777777", lw=0.5, zorder=3)
        axa.text(i, b[m] + 0.06, TX(f"com__{c}__{m}", d), ha="center", va="bottom",
                 fontsize=FS, color=E.COLOR_TEXTO, zorder=5)
    axa.set_xticks(range(len(MECANISMOS)), [m[1] for m in MECANISMOS])
    axa.set_xlim(-0.55, len(MECANISMOS) - 0.45)
    axa.set_title("(a) Los siete mecanismos", fontsize=FS_TIT, loc="left", pad=4)

    # (b) la cascada con los tres nombres
    pasos = [
        ("C4", piso, c4 - piso, A.C_TOTAL_REF, TX(f"com__{c}__C4", d)),
        ("+ cargos\nevitados\n(supuesto 1)", c4, c1_c4, A.C_C1C4,
         TX(f"com__{c}__C1_C4", d, signo=True)),
        ("+ ahorro del\nintercambio\n(supuesto 2)", niveles[1], banda, A.C_P2PC1,
         TX(f"com__{c}__banda", d, signo=True)),
        ("+ efecto\nsobre el\ncrédito\n(supuesto 1)", niveles[2], reclas, A.C_RECLAS,
         TX(f"com__{c}__reclas", d, signo=True)),
        ("P2P", piso, p2p - piso, A.C_TOTAL_P2P, TX(f"com__{c}__P2P", d)),
    ]
    for i, (_, y0, h, colr, txt) in enumerate(pasos):
        axb.bar(i, h, bottom=y0, width=0.62, color=colr, edgecolor="#333333", lw=0.5, zorder=3)
        axb.text(i, y0 + max(h, 0) + 0.06, txt, ha="center", va="bottom", fontsize=FS,
                 color=E.COLOR_TEXTO, zorder=5)
    for i, nv in enumerate(niveles):
        axb.plot([i + 0.31, i + 0.69], [nv, nv], color="#555555", lw=0.6, ls=(0, (2, 1.5)),
                 zorder=2)
    # C1 a la izquierda de la barra de los cargos evitados, a su altura (no sobre +1,71)
    axb.text(0.64, c1, f"C1: {TX(f'com__{c}__C1', d)}", ha="right", va="center",
             fontsize=FS, color=E.COLOR_TEXTO_SUAVE)
    axb.axhline(col, color=A.C_COL, lw=1.1, ls="--", zorder=4)
    axb.text(2.4, col - 0.1, f"P2P por el colectivo: {TX(f'com__{c}__P2Pcol', d)}",
             ha="center", va="top", fontsize=FS, color=E.COLOR_TEXTO,
             bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9), zorder=6)
    axb.set_xticks(range(len(pasos)), [p[0] for p in pasos])
    axb.set_xlim(-0.55, len(pasos) - 0.45)
    axb.set_title("(b) De C4 al mercado P2P", fontsize=FS_TIT, loc="left", pad=4)

    axa.set_ylim(piso, techo)
    # marcas enteras por encima del piso: el piso lleva la marca de corte, no cifra
    axa.set_yticks([float(t) for t in np.arange(np.floor(piso) + 1, techo)])
    for ax in (axa, axb):
        E.aplicar_estilo_ejes(ax, ylabel="Beneficio neto de la comunidad (MCOP)" if ax is axa else "")
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
        "paso": ["C4", "C1_menos_C4", "banda", "reclasificacion", "P2P", "P2P_colectivo"],
        "base_MCOP": [0.0, c4, niveles[1], niveles[2], 0.0, 0.0],
        "altura_MCOP": [c4, c1_c4, banda, reclas, p2p, col],
        "nivel_final_MCOP": [c4, niveles[1], niveles[2], niveles[3], p2p, col]})
    try:
        pd.testing.assert_frame_equal(casc, en[casc.columns.tolist()], check_dtype=False,
                                      rtol=1e-12, atol=1e-12)
    except AssertionError as e:
        raise SystemExit(f"[gen_figuras_articulo_es] COMPUERTA FALLIDA: la cascada no es la de "
                         f"la Fig. 2 inglesa: {e}")
    ok("cascada: mismos datos que Documentos/articulo_latam/v2/figuras/fig2_cascada_E0.csv")
    nombres_casc = {"C4": "C4", "C1_menos_C4": "cargos evitados (C1 − C4; supuesto 1)",
                    "banda": "ahorro del intercambio (banda; supuesto 2)",
                    "reclasificacion": "efecto sobre el crédito (reclasificación; supuesto 1)",
                    "P2P": "P2P", "P2P_colectivo": "P2P por el colectivo"}
    datos = pd.concat([
        pd.DataFrame({"panel": "a", "rotulo": [m[1].replace("\n", " ") for m in MECANISMOS],
                      "clave": [f"com__E0__{m[0]}" for m in MECANISMOS],
                      "beneficio_MCOP": [b[m[0]] for m in MECANISMOS]}),
        pd.DataFrame({"panel": "b", "rotulo": [nombres_casc[p] for p in casc.paso],
                      "clave": ["com__E0__C4", "com__E0__C1_C4", "com__E0__banda",
                                "com__E0__reclas", "com__E0__P2P", "com__E0__P2Pcol"],
                      "base_MCOP": casc.base_MCOP, "altura_MCOP": casc.altura_MCOP,
                      "nivel_final_MCOP": casc.nivel_final_MCOP}),
    ], ignore_index=True)
    guardar(fig, nombre, datos, "pag", [
        f"eje vertical común a los dos paneles, desde {piso} MCOP (marcado con un corte)",
        "compuertas: mec__n = 7; orden de las barras = mec__E0__orden; C2 = P2P al peso "
        "(regla 5 de CLAUDE.md; sin C4 mensual, alias de C4, regla 4); la cascada cierra al peso "
        "y sus datos son los de la Fig. 2 inglesa",
        "C5 rayado: referencia no elegible; C2 rotulado igual a P2P en el agregado",
        "nombres aprobados el 2026-09-30: cargos evitados = C1 − C4, ahorro del intercambio = "
        "banda, efecto sobre el crédito = reclasificación (0,00 en E0: nadie agota su crédito); "
        "los dos que dependen del residual por miembro se atan al supuesto 1 y la banda al 2"])


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
            ha="left", va="center", fontsize=7.5, color=E.COLOR_TEXTO, linespacing=1.2,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#BBBBBB", lw=0.6))
    # Un solo nombre para el precio que paga cada comprador (en esta hora, el
    # uniforme: ningún techo lo corta) y glosa de los rótulos propios del modelo.
    exige(bool((datos[datos.papel == "comprador"].precio_liquidado_COP_kWh
                == datos.precio_uniforme_COP_kWh.iloc[0]).all()),
          "hora: algún comprador no paga el precio uniforme (tope en su tarifa)")
    glosas = {"precio liquidado": "precio uniforme",
              "precio del reposo": "precio de cada comprador en el reposo del juego",
              "renta inframarginal": "renta inframarginal: piso del juego − piso de CESMAG",
              "Cesmag": "CESMAG"}
    hechos = set()
    for t in fig.findobj(matplotlib.text.Text):
        if t.get_text() in glosas:
            hechos.add(t.get_text())
            t.set_text(glosas[t.get_text()])
    exige(hechos >= set(glosas) - {"Cesmag"}, f"hora: rótulos sin renombrar {set(glosas) - hechos}")
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
    salida["institucion"] = salida.institucion.replace({"Cesmag": "CESMAG"})
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


# ── Figs. 3 y 4: las inglesas traducidas, con los nombres nuevos ────────────
TRAD_NUEVOS = {
    "C1 − C4 (case-2 charges)": "cargos evitados (C1 − C4)",
    "C1 − C4 < 0 (C4 leads C1)": "C1 − C4 < 0 (C4 supera a C1)",
    "P2P − C1 (band + reclass.)": "ahorro del intercambio + efecto\nsobre el crédito (P2P − C1)",
    "P2P via collective − C4": "P2P por el colectivo − C4",
    "P2P coll.\n− C1": "P2P por el\ncolectivo\n− C1",                  # Fig. 4, sin abreviar
}


def desde_ingles(func: str, nombre: str, alto: float | None) -> None:
    T._rc("A")
    T._CAPTURA.clear()
    getattr(A, func)()
    exige(bool(T._CAPTURA), f"{nombre}: el generador inglés no llegó a guardar")
    fig, datos = T._CAPTURA["fig"], T._CAPTURA["datos"]
    T.datos_iguales(datos, DIR_EN / f"{nombre}.csv", nombre)
    T.traduce_figura(fig)
    if func == "fig3":
        ax = fig.axes[0]
        ley = ax.get_legend()
        h = list(ley.legend_handles)
        l_ = [t.get_text() for t in ley.get_texts()]
        ley.remove()
        fig.set_size_inches(ANCHO_COL, alto)
        # la leyenda pasa debajo del eje, en dos columnas; el eje recupera la altura
        ax.set_ylim(ax.get_ylim()[0], max(p.get_y() + p.get_height() for p in ax.patches) * 1.08)
        orden = [0, 2, 1, 3, 4]
        fig.legend([h[i] for i in orden], [l_[i] for i in orden], loc="lower center",
                   bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False, fontsize=FS,
                   handlelength=1.3, columnspacing=0.8, labelspacing=0.35, handletextpad=0.4)
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        alto_ley = fig.legends[0].get_window_extent(r).height / fig.bbox.height
        fig.tight_layout(pad=0.3, rect=[0, alto_ley + 0.01, 1, 1])
        fig.canvas.draw()
        exige(fig.legends[0].get_window_extent(r).y1 < ax.get_tightbbox(r).y0 - 1,
              "fig3: la leyenda pisa el eje")
    if func == "fig4":
        # «P2P por el colectivo» sin abreviar ocupa tres líneas: el mapa baja un
        # poco para que la cabecera quepa en el lienzo (solo composición)
        ax = fig.axes[0]
        p = ax.get_position()
        ax.set_position([p.x0, p.y0, p.width, p.height - 0.03])
    csv = (DIR_EN / f"{nombre}.csv").read_text(encoding="utf-8-sig")
    guardar(fig, nombre, datos, "col", [
        f"generador inglés reutilizado sin modificar: gen_figuras_articulo.py, función {func}() "
        f"(nota del generador: {T._CAPTURA['nota']})",
        "textos traducidos con el diccionario cerrado TRAD de gen_figuras_entrega.py"
        + (", con los nombres aprobados el 2026-09-30 en la leyenda (cargos evitados; ahorro "
           "del intercambio + efecto sobre el crédito); leyenda bajo el eje" if func == "fig3" else
           "; sin cambios de contenido"),
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
    ok("cajas de los PDF, PNG a 600 ppp, letra ≥ 7 pt, CESMAG y números impresos justificados")
    t1 = PdfReader(DIR_SAL / "fig1_comunidad.pdf").pages[0].extract_text()
    exige("CESMAG" in t1, "fig1_comunidad: no rotula «CESMAG»")


def main() -> int:
    IMPRESOS["fig1_comunidad"] = set()                   # Fig. 1: ninguna cifra
    T.TRAD.update(TRAD_NUEVOS)                           # solo en este proceso
    A.compuertas_comunidad()
    exige(sha(CIFRAS) == A.SHA, "cifras.csv no tiene la huella e1/L")
    exige(A.RUTA_CIFRAS == "cifras_articulo_2026-09-30/cifras.csv",
          f"el generador inglés lee {A.RUTA_CIFRAS}, no la tabla del 30")
    rc_articulo()
    fig1()
    rc_articulo()
    fig2()
    fig_hora()
    desde_ingles("fig3", "fig3_trece_casos", 3.05)
    desde_ingles("fig4", "fig4_gsa_inversion", None)
    comprueba()
    print("[gen_figuras_articulo_es] FIGURAS EN ESPAÑOL ESCRITAS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
