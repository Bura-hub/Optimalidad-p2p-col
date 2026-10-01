"""
gen_figuras_entrega.py — Figuras del documento de tesis en formato MaIE
(Acuerdo 021 de 2020): artículo IEEE a dos columnas, en español.
===============================================================================
Tarea 1 del plan `docs/superpowers/plans/2026-09-29-tesis-entrega.md`.

No dibuja nada nuevo ni simula nada: REUTILIZA, sin modificarlos, los dos
generadores que ya dibujan estas figuras desde el canon 2026-09 con huella:

  * `reformateo/documento/scripts/gen_tesis_figuras.py` (figuras c4_ a c8_ de
    `Documentos/FinalTesisV2/tesis.md`, en español, a 6,5 in). Se importa el
    módulo y, para cada figura, se sustituye en su espacio de nombres
    (monkeypatch, solo en este proceso):
      - `plt` por un apoderado que fija el `figsize` de la caja IEEE
        (columna de 3,48692 in o página de 7,13989 in) al crear la figura, de
        modo que el `tight_layout` del generador ya trabaja en la caja final;
      - `guardar` por una captura que devuelve la figura, sus datos y su
        procedencia a este guion en lugar de escribirlos.
    Las compuertas del generador (huellas de HUELLAS.csv y cifras contra
    cifras.csv de cada capítulo) corren igual que en la tesis.
  * `reformateo/documento/scripts/articulo/gen_figuras_articulo.py` (figuras
    del artículo v2, en inglés, ya a 3,48692 in). Se sustituye `guardar` por
    la captura y se traducen al español todos sus textos con un diccionario
    cerrado: el número del texto en inglés (`texto_en`, punto decimal y coma
    de millares) pasa a coma decimal y espacio de millares, y cualquier
    palabra inglesa que quede detiene el guion. Sus compuertas
    (`compuertas_comunidad`, huella e1/L de `cifras.csv`, coherencia de
    `texto_en`) corren antes de dibujar.

Compuertas de este guion (fallan en voz alta con SystemExit):
  1. la figura mide exactamente la caja pedida (in) y su PDF también (pypdf);
  2. letra mínima medida ≥ 7 pt en todo texto visible;
  3. ningún texto, rótulo ni leyenda se sale del lienzo;
  4. los datos dibujados (el CSV que devuelve el generador) son idénticos a
     los de la figura fuente ya publicada (`Documentos/FinalTesisV2/figuras/`
     o `Documentos/articulo_latam/v2/figuras/`), que salieron de las mismas
     tablas con huella;
  5. en las figuras traducidas, ninguna palabra inglesa de la lista vetada.

Salida: `Documentos/Tesis_entrega/figuras/<nombre>.{pdf,png,csv,fuente.txt}`
(PDF vectorial con fuentes TrueType incrustadas; PNG a 600 ppp).

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/tesis_entrega/gen_figuras_entrega.py
    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/tesis_entrega/gen_figuras_entrega.py banda_hora retiro

Actividades de la propuesta: 1.0, 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.3, 4.1 y 4.2
(una figura por lo menos para cada objetivo).
"""
from __future__ import annotations

import argparse
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
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "articulo"))

import matplotlib                                              # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                # noqa: E402
from matplotlib.text import Text                               # noqa: E402
from matplotlib.ticker import FixedFormatter, FuncFormatter, ScalarFormatter  # noqa: E402

import gen_tesis_figuras as G                                  # noqa: E402
import gen_figuras_articulo as A                               # noqa: E402  (lee cifras.csv con su huella)

GUION = "reformateo/documento/scripts/tesis_entrega/gen_figuras_entrega.py"
DIR_SAL = RAIZ / "Documentos" / "Tesis_entrega" / "figuras"
DIR_FUENTE_G = RAIZ / "Documentos" / "FinalTesisV2" / "figuras"
DIR_FUENTE_A = RAIZ / "Documentos" / "articulo_latam" / "v2" / "figuras"

ANCHO_COL = 252.0 / 72.27        # 3,48692 in: \columnwidth de IEEEtran (10 pt)
ANCHO_PAG = 516.0 / 72.27        # 7,13989 in: \textwidth
LETRA_MIN = 7.0                  # pt a tamaño de impresión
DPI_PNG = 600
NBSP = " "                  # separador de millares, como gen_tesis_figuras.num

# Tipografía del cuerpo IEEE (Times, 10 pt): las figuras de la tesis ya usan
# Times New Roman; aquí se bajan los tamaños por defecto a la caja IEEE. Los
# tamaños explícitos de cada generador (7,4 a 9,5 pt) se respetan.
RC_ENTREGA = {
    "font.size": 8.0,
    "axes.labelsize": 8.0,
    "axes.titlesize": 8.0,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[gen_figuras_entrega] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    print(f"[gen_figuras_entrega]   OK  {msg}")


# ── Apoderado de pyplot: fija el tamaño de la figura que crea el generador ──
class _PltCaja:
    def __init__(self, real):
        self._real = real
        self.tam: tuple[float, float] | None = None

    def __getattr__(self, nombre):
        return getattr(self._real, nombre)

    def subplots(self, *a, **k):
        if self.tam is not None:
            k["figsize"] = self.tam
        return self._real.subplots(*a, **k)

    def figure(self, *a, **k):
        if self.tam is not None:
            k["figsize"] = self.tam
        return self._real.figure(*a, **k)


PLT_G = _PltCaja(plt)
G.plt = PLT_G

# ── Captura de lo que el generador iba a guardar ────────────────────────────
_CAPTURA: dict = {}


def _captura_g(fig, nombre, datos, procedencia):
    _CAPTURA.update(fig=fig, nombre=nombre, datos=datos, procedencia=list(procedencia))
    return None


def _captura_a(fig, nombre, datos, nota):
    _CAPTURA.update(fig=fig, nombre=nombre, datos=datos, nota=nota)
    return None


G.guardar = _captura_g
A.guardar = _captura_a


# ── Número y texto en español ───────────────────────────────────────────────
_NUM_EN = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?!\w)")


def num_es(s: str) -> str:
    """'2.01' -> '2,01'; '1,024' -> '1 024'; '0.4–3.3' -> '0,4–3,3'. Solo toca
    números sueltos (no «P2P», «C1» ni «E0»)."""
    def f(m):
        ent = m.group(1).replace(",", NBSP)
        return ent + ("," + m.group(2) if m.group(2) else "")
    return _NUM_EN.sub(f, s)


class _FormatoEs(ScalarFormatter):
    """El formateador lineal de matplotlib con coma decimal."""
    def __call__(self, x, pos=None):
        return num_es(super().__call__(x, pos))


# Diccionario cerrado de las figuras del artículo v2 (texto completo).
TRAD = {
    # Fig. 1 (comunidad)
    "XM wholesale market\n(hourly spot price)": "Mercado mayorista (XM)\n(precio de bolsa horario)",
    "Retailers\nASC Ingeniería · CEDENAR": "Comercializadores\nASC Ingeniería · CEDENAR",
    "excess at\nspot price": "exceso a\nprecio de bolsa",
    "Distribution network: CEDENAR (network operator)":
        "Red de distribución: CEDENAR (operador de red)",
    "settlement per meter\n(Art. 25; Annex 4)": "liquidación por medidor\n(art. 25; anexo 4)",
    "import / surplus": "importación / excedente",
    "energy": "energía",
    "settlement": "liquidación",
    "Collective self-generation (CREG 101 072, Arts. 18–21)":
        "Autogeneración colectiva (CREG 101 072, arts. 18–21)",
    "Cesmag": "CESMAG",
    "PV + meter": "FV+medidor",
    "P2P market: hourly price, all pairs (no specific rule)":
        "Mercado P2P: precio horario, todos los pares (sin norma)",
    # Fig. 2 (cascada de E0)
    "+Band": "+Banda",
    "+Reclass.": "+Reclasif.",
    "Community net benefit (MCOP)": "Beneficio neto de la comunidad (MCOP)",
    # Fig. 3 (trece casos)
    "C1 − C4 (case-2 charges)": "C1 − C4 (cargos del caso 2)",
    "C1 − C4 < 0 (C4 leads C1)": "C1 − C4 < 0 (C4 supera a C1)",
    "P2P − C1 (band + reclass.)": "P2P − C1 (banda + reclasif.)",
    "P2P via collective − C4": "P2P por el colectivo − C4",
    "Case": "Caso",
    "Difference with C4 (MCOP)": "Diferencia con C4 (MCOP)",
    # Fig. 4 (GSA)
    "P2P coll.\n− C1": "P2P col.\n− C1",
    "Case (n)": "Caso (n)",
    "P(sign inversion) in the GSA box (%); 95 % interval below":
        "P(inversión de signo) en la caja del GSA (%); debajo, intervalo al 95 %",
}
# Prefijos con número detrás (el número pasa por num_es).
PREFIJOS = [("P2P via collective: ", "P2P por el colectivo: ")]
VETADAS = re.compile(
    r"\b(via|case|band|reclass|collective|coll|settlement|energy|meter|market|retailers?"
    r"|surplus|import|leads|charges|difference|benefit|interval|inversion|sign|below"
    r"|wholesale|spot|network|distribution|operator|annex|pairs|rule|excess|price"
    r"|community|hourly|self-generation|PV)\b", re.I)


def traduce(s: str) -> str:
    if s in TRAD:
        s = TRAD[s]
    else:
        for a, b in PREFIJOS:
            if s.startswith(a):
                s = b + s[len(a):]
    return num_es(s)


def traduce_figura(fig) -> None:
    """Traduce todo texto de la figura: textos sueltos, rótulos de ejes y de la
    barra de color, leyendas y los rótulos fijos de las marcas; los ejes
    lineales pasan a coma decimal."""
    for ax in fig.axes:
        for eje in (ax.xaxis, ax.yaxis):
            f = eje.get_major_formatter()
            if isinstance(f, FixedFormatter):
                eje.set_major_formatter(FixedFormatter([traduce(s) for s in f.seq]))
            elif type(f) is ScalarFormatter:
                eje.set_major_formatter(_FormatoEs(useOffset=False))
            elif isinstance(f, FuncFormatter):
                # set_xticks(x, rótulos) deja un FuncFormatter sobre la lista
                eje.set_major_formatter(FuncFormatter(lambda v, p, f=f: traduce(f(v, p))))
    for t in fig.findobj(Text):
        s = t.get_text()
        if s.strip():
            t.set_text(traduce(s))
    fig.canvas.draw()
    for t in _textos_visibles(fig):
        m = VETADAS.search(t.get_text())
        exige(m is None, f"queda inglés en la figura: «{t.get_text()}» ({m.group(0) if m else ''})")


# ── Medidas ─────────────────────────────────────────────────────────────────
def _textos_visibles(fig) -> list[Text]:
    """Textos que se dibujan: los de cada eje (rótulos, marcas visibles,
    textos, leyenda) y los de la figura."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    fuera = []
    for ax in fig.axes:
        for eje in (ax.xaxis, ax.yaxis):
            for t in eje.get_ticklabels(which="both"):
                if t.get_visible() and t.get_text().strip():
                    fuera.append(t)
            if eje.label.get_visible() and eje.label.get_text().strip():
                fuera.append(eje.label)
        fuera += [t for t in ax.texts if t.get_visible() and t.get_text().strip()]
        fuera += [c for c in ax.get_children() if isinstance(c, Text) and c not in fuera
                  and c.get_visible() and c.get_text().strip()]
        ley = ax.get_legend()
        if ley is not None:
            fuera += [t for t in ley.get_texts() if t.get_text().strip()]
    for ley in fig.legends:
        fuera += [t for t in ley.get_texts() if t.get_text().strip()]
    fuera += [t for t in fig.texts if t.get_visible() and t.get_text().strip()]
    for t in fuera:
        t.get_window_extent(r)
    return fuera


def letra_minima(fig, nombre: str) -> float:
    ts = _textos_visibles(fig)
    exige(bool(ts), f"{nombre}: sin textos")
    m = min(t.get_fontsize() for t in ts)
    exige(m >= LETRA_MIN - 1e-9, f"{nombre}: letra de {m:.2f} pt, por debajo de {LETRA_MIN} pt")
    return m


def dentro_del_lienzo(fig, nombre: str) -> None:
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    caja = fig.bbox
    tol = 1.0                                      # px a los 100 ppp del lienzo
    cajas = [(f"eje {i}", ax.get_tightbbox(r)) for i, ax in enumerate(fig.axes)]
    cajas += [(f"leyenda de figura {i}", l.get_window_extent(r)) for i, l in enumerate(fig.legends)]
    cajas += [(f"«{t.get_text()[:30]}»", t.get_window_extent(r)) for t in fig.texts
              if t.get_visible() and t.get_text().strip()]
    for que, b in cajas:
        if b is None:
            continue
        exige(b.x0 >= caja.x0 - tol and b.x1 <= caja.x1 + tol and b.y0 >= caja.y0 - tol
              and b.y1 <= caja.y1 + tol,
              f"{nombre}: {que} se sale del lienzo ({b.x0:.1f}, {b.y0:.1f}, {b.x1:.1f}, "
              f"{b.y1:.1f}) frente a ({caja.x0:.1f}, {caja.y0:.1f}, {caja.x1:.1f}, {caja.y1:.1f})")


def sin_remision_a_capitulos(fig, nombre: str) -> None:
    """El documento de entrega no tiene capítulos: ningún texto de la figura
    remite a «capítulo N» de la tesis extensa (ronda 1)."""
    for t in _textos_visibles(fig):
        exige(re.search(r"cap[ií]tulo\s*\d", t.get_text(), re.I) is None,
              f"{nombre}: remite a un capítulo de la tesis extensa: «{t.get_text()}»")


def datos_iguales(datos: pd.DataFrame, fuente_csv: Path, nombre: str) -> None:
    """Los datos que dibuja la figura de entrega son los de la figura fuente."""
    exige(fuente_csv.is_file(), f"{nombre}: no está la figura fuente {fuente_csv}")
    nuevo = pd.read_csv(io.StringIO(datos.to_csv(index=False)))
    viejo = pd.read_csv(fuente_csv, encoding="utf-8-sig")
    exige(list(nuevo.columns) == list(viejo.columns),
          f"{nombre}: columnas distintas de {fuente_csv.name}")
    exige(len(nuevo) == len(viejo), f"{nombre}: {len(nuevo)} filas frente a {len(viejo)}")
    try:
        pd.testing.assert_frame_equal(nuevo, viejo, check_dtype=False, rtol=1e-12, atol=1e-12)
    except AssertionError as e:
        raise SystemExit(f"[gen_figuras_entrega] COMPUERTA FALLIDA: {nombre}: los datos no son "
                         f"los de {fuente_csv.relative_to(RAIZ).as_posix()}: {e}")


# ── Ajustes de composición en la caja IEEE (no tocan datos) ─────────────────
def _leyenda_abajo(ax, ncol: int, y: float, **kw) -> None:
    ley = ax.get_legend()
    exige(ley is not None, "se esperaba una leyenda en el eje")
    h = list(ley.legend_handles)
    l_ = [t.get_text() for t in ley.get_texts()]
    ax.legend(h, l_, loc="upper center", bbox_to_anchor=(0.5, y), ncol=ncol,
              frameon=False, **kw)


def ajuste_sigma(fig) -> None:
    ax = fig.axes[0]
    _leyenda_abajo(ax, 2, -0.16, handletextpad=0.3, columnspacing=1.0)
    fig.tight_layout(pad=0.3)


def ajuste_retiro(fig) -> None:
    """La leyenda de c8_retiro va a la derecha del eje cuadrado; en la columna
    no cabe y pasa a la figura, debajo, en tres columnas."""
    ax = fig.axes[0]
    ley = ax.get_legend()
    exige(ley is not None, "retiro: se esperaba una leyenda en el eje")
    h = list(ley.legend_handles)
    l_ = [t.get_text() for t in ley.get_texts()]
    ley.remove()
    fig.legend(h, l_, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=3, frameon=False,
               handletextpad=0.2, columnspacing=0.9, fontsize=7.5)
    # Los dos rótulos de las regiones, a 7,5 pt; el de abajo, alineado a la
    # derecha dentro del eje (centrado en 2 000 se salía por la derecha).
    for t in ax.texts:
        t.set_fontsize(7.5)
        if t.get_text().startswith("se mueve menos con el mercado"):
            # Ronda 1: por debajo del marcador más bajo (0,55), sin pisarlo.
            t.set_position((1.5e4, 0.13))
            t.set_horizontalalignment("right")
            t.set_verticalalignment("bottom")
    # Con aspect «equal», tight_layout no respeta la franja de la leyenda: el
    # eje cuadrado se coloca a mano (2,34 in de lado) y se comprueba que la
    # leyenda quede por debajo de los rótulos.
    fig.subplots_adjust(left=0.19, right=0.86, bottom=0.27, top=0.98)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    exige(fig.legends[0].get_window_extent(r).y1 < ax.get_tightbbox(r).y0 - 2,
          "retiro: la leyenda pisa los rótulos del eje")


def ajuste_perfiles(fig) -> None:
    """En c4_perfiles_e0 el hueco entre las marcas y «Hora del día» crece al
    bajar el alto: los ejes se alargan hacia abajo hasta 4 px del rótulo."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    exige(fig._supxlabel is not None, "perfiles: se esperaba supxlabel")
    tope = fig._supxlabel.get_window_extent(r).y1
    fondo = min(ax.get_tightbbox(r).y0 for ax in fig.axes)
    delta = (fondo - tope - 4.0) / fig.bbox.height
    exige(delta > 0, "perfiles: no hay hueco que cerrar")
    for ax in fig.axes:
        p = ax.get_position()
        ax.set_position([p.x0, p.y0 - delta, p.width, p.height + delta])


def menos_tipografico(fig) -> None:
    """Las cifras negativas de gen_tesis_figuras.num llevan el guion ASCII; en
    la caja IEEE se imprime el signo menos (U+2212)."""
    for t in fig.findobj(Text):
        s = t.get_text()
        if re.match(r"^-\d", s):
            t.set_text("−" + s[1:])


def ajuste_subir_letra(fig) -> None:
    """Las cifras de las celdas de c7_brechas_institucion van a 6,6 pt en la
    tesis (caja de 6,5 in); en la página IEEE (7,14 in) caben a 7 pt."""
    for t in fig.findobj(Text):
        if t.get_text().strip() and t.get_fontsize() < LETRA_MIN:
            t.set_fontsize(LETRA_MIN)


def ajuste_brechas(fig) -> None:
    """c7_brechas_institucion: letra de celda a 7 pt y la leyenda sin la
    remisión al capítulo 8 de la tesis extensa, que el documento de entrega no
    tiene (ronda 1)."""
    ajuste_subir_letra(fig)
    n = 0
    for ley in fig.legends:
        for t in ley.get_texts():
            s = t.get_text()
            if "caja del capítulo 8" in s:
                t.set_text(s.replace("caja del capítulo 8", "caja de la sensibilidad global"))
                n += 1
    exige(n == 1, f"brechas: se esperaba un rótulo con «caja del capítulo 8» ({n})")


def ajuste_desercion(fig) -> None:
    """c8_infactibilidad_desercion: «CESMAG, E2» se separa del final de su
    línea punteada (ronda 1)."""
    ts = [t for ax in fig.axes for t in ax.texts if t.get_text() == "CESMAG, E2"]
    exige(len(ts) == 1, f"desercion: se esperaba un rótulo «CESMAG, E2» ({len(ts)})")
    x, y = ts[0].get_position()
    ts[0].set_position((x + 0.12, y))


def ajuste_corte_hx(fig) -> None:
    """c6_corte_hx: la flecha del «exceso» apunta dentro del área del exceso
    (entre la importación del mes y la inyección acumulada, cerca del final
    del mes), con punta (ronda 1). Posición derivada de los datos dibujados."""
    from matplotlib.text import Annotation
    ax = fig.axes[0]
    an = [t for t in ax.texts if isinstance(t, Annotation) and t.get_text().startswith("exceso:")]
    exige(len(an) == 1, f"corte_hx: se esperaba una anotación del exceso ({len(an)})")
    d = _CAPTURA["datos"]
    imp = float(d.importacion_mes_kWh.iloc[0])
    ultimo = ax.get_xlim()[1] - 0.2
    t_dias = np.arange(len(d)) / 24.0 + 1.0
    x = ultimo - 2.0
    acum_x = float(np.interp(x, t_dias, d.inyeccion_acumulada_kWh.to_numpy(float)))
    exige(acum_x > imp, "corte_hx: el punto elegido no está en el exceso")
    an[0].xy = (x, imp + 0.5 * (acum_x - imp))
    an[0].arrow_patch.set_arrowstyle("-|>", head_length=0.35, head_width=0.18)


def ajuste_retight(fig) -> None:
    fig.tight_layout(pad=0.3)


# ── Catálogo: 12 figuras, al menos una por objetivo ─────────────────────────
# origen: ("G", función de gen_tesis_figuras) o ("A", función de gen_figuras_articulo)
FIGURAS = [
    dict(nombre="comunidad", origen=("A", "fig1"), fuente="fig1_comunidad", caja="col",
         seccion="III", objetivo="1 (actividad 1.0)"),
    dict(nombre="perfiles_e0", origen=("G", "c4_perfiles_e0"), caja="pag", alto=2.35,
         ajuste=ajuste_perfiles, seccion="III", objetivo="1 (actividades 1.2) y 3 (actividad 3.1)"),
    dict(nombre="banda_hora", origen=("G", "c5_banda_hora"), caja="pag", alto=2.85,
         seccion="IV", objetivo="1 (actividad 1.1)"),
    dict(nombre="barrido_sigma", origen=("G", "c5_barrido_sigma"), caja="col", alto=3.35,
         ajuste=ajuste_sigma, seccion="VII", objetivo="4 (actividad 4.1)"),
    dict(nombre="corte_hx", origen=("G", "c6_corte_hx"), caja="pag", alto=2.45,
         ajuste=ajuste_corte_hx, seccion="V", objetivo="2 (actividad 2.1)"),
    dict(nombre="cascada_e0", origen=("A", "fig2"), fuente="fig2_cascada_E0", caja="col",
         ajuste=ajuste_retight, seccion="VI", objetivo="3 (actividad 3.3)"),
    dict(nombre="trece_casos", origen=("A", "fig3"), fuente="fig3_trece_casos", caja="col",
         ajuste=ajuste_retight, seccion="VI", objetivo="3 (actividades 3.2 y 3.3)"),
    dict(nombre="optimalidad_mensual", origen=("G", "c7_optimalidad_mensual"), caja="pag",
         alto=3.1, seccion="VI", objetivo="2 (actividad 2.2) y 4 (actividad 4.2)"),
    dict(nombre="brechas_institucion", origen=("G", "c7_brechas_institucion"), caja="pag",
         alto=3.9, ajuste=ajuste_brechas, seccion="VI", objetivo="3 (actividad 3.3)"),
    dict(nombre="gsa_inversion", origen=("A", "fig4"), fuente="fig4_gsa_inversion", caja="col",
         seccion="VII", objetivo="4 (actividad 4.1)"),
    dict(nombre="desercion", origen=("G", "c8_infactibilidad_desercion"), caja="pag", alto=4.4,
         ajuste=ajuste_desercion, seccion="VII", objetivo="4 (actividad 4.1)"),
    dict(nombre="retiro", origen=("G", "c8_retiro"), caja="col", alto=3.3, ajuste=ajuste_retiro,
         seccion="VII", objetivo="4 (actividad 4.1)"),
]


def _rc(origen: str) -> None:
    plt.close("all")
    plt.rcdefaults()
    if origen == "G":
        G._estilo_tesis()
        plt.rcParams.update(RC_ENTREGA)
    else:
        A.E.aplicar_rc()
        plt.rcParams.update(A.RC_ARTICULO)
        plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})


def genera(spec: dict) -> dict:
    nombre = spec["nombre"]
    tipo, func = spec["origen"]
    ancho = ANCHO_COL if spec["caja"] == "col" else ANCHO_PAG
    print(f"[gen_figuras_entrega] {nombre} ← {tipo}.{func} ({spec['caja']}, {ancho:.5f} in)")
    _rc(tipo)
    _CAPTURA.clear()
    if tipo == "G":
        PLT_G.tam = (ancho, spec["alto"])
        try:
            getattr(G, func)()
        finally:
            PLT_G.tam = None
        fuente_csv = DIR_FUENTE_G / f"{func}.csv"
    else:
        getattr(A, func)()
        fuente_csv = DIR_FUENTE_A / f"{spec['fuente']}.csv"
    exige(bool(_CAPTURA), f"{nombre}: el generador no llegó a guardar")
    fig, datos = _CAPTURA["fig"], _CAPTURA["datos"]
    w, h = fig.get_size_inches()
    exige(abs(w - ancho) < 1e-6, f"{nombre}: la figura mide {w:.5f} in, la caja es {ancho:.5f}")
    if tipo == "A":
        traduce_figura(fig)
    if spec.get("ajuste"):
        spec["ajuste"](fig)
    if tipo == "G":
        menos_tipografico(fig)
    letra = letra_minima(fig, nombre)
    dentro_del_lienzo(fig, nombre)
    sin_remision_a_capitulos(fig, nombre)
    datos_iguales(datos, fuente_csv, nombre)

    DIR_SAL.mkdir(parents=True, exist_ok=True)
    base = DIR_SAL / nombre
    with plt.rc_context({"savefig.bbox": "standard", "savefig.pad_inches": 0.0}):
        fig.savefig(base.with_suffix(".pdf"))
        fig.savefig(base.with_suffix(".png"), dpi=DPI_PNG)
    plt.close(fig)
    datos.to_csv(base.with_suffix(".csv"), index=False, encoding="utf-8-sig")

    if tipo == "G":
        proc = _CAPTURA["procedencia"]
        gen = f"reformateo/documento/scripts/gen_tesis_figuras.py, función {func}()"
    else:
        claves = sorted(A.USADAS.get(_CAPTURA["nombre"], set()))
        proc = [f"SALIDAS_SERVIDOR/{A.RUTA_CIFRAS} (HUELLAS.csv, grupo e1/L; sha256 {A.SHA})",
                f"claves usadas ({len(claves)}): " + ", ".join(claves),
                "nota del generador: " + _CAPTURA["nota"],
                "textos traducidos al español con el diccionario cerrado TRAD de este guion; "
                "números de texto_en con coma decimal y espacio de millares"]
        gen = f"reformateo/documento/scripts/articulo/gen_figuras_articulo.py, función {func}()"
    (base.with_suffix(".fuente.txt")).write_text(
        f"Figura: {nombre} (documento de tesis, Documentos/Tesis_entrega)\n"
        f"Guion: {GUION}\n"
        f"Generador reutilizado sin modificar: {gen}\n"
        f"Caja: {'columna' if spec['caja'] == 'col' else 'página'}, {w:.5f} × {h:.5f} in; "
        f"letra mínima medida {letra:.2f} pt\n"
        f"Sección del documento: {spec['seccion']}; objetivo de la propuesta: {spec['objetivo']}\n"
        f"Compuerta de datos: el CSV es idéntico al de "
        f"{fuente_csv.relative_to(RAIZ).as_posix()}\n"
        "Procedencia (la del generador):\n" + "".join(f"  - {p}\n" for p in proc),
        encoding="utf-8")
    print(f"  escrito {nombre}.pdf / .png / .csv / .fuente.txt ({w:.3f} × {h:.3f} in, "
          f"letra mínima {letra:.2f} pt)")
    return dict(nombre=nombre, ancho=w, alto=h, letra=letra, caja=spec["caja"])


def comprueba_pdf(res: list[dict]) -> None:
    from pypdf import PdfReader
    for r in res:
        caja = PdfReader(DIR_SAL / f"{r['nombre']}.pdf").pages[0].mediabox
        w, h = float(caja.width) / 72, float(caja.height) / 72
        exige(abs(w - r["ancho"]) < 0.01 and abs(h - r["alto"]) < 0.01,
              f"{r['nombre']}.pdf mide {w:.4f} × {h:.4f} in")
        for suf in (".png", ".csv", ".fuente.txt"):
            exige((DIR_SAL / f"{r['nombre']}{suf}").is_file(), f"falta {r['nombre']}{suf}")
    ok(f"{len(res)} PDF con la caja exacta y sus PNG, CSV y fuente")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Figuras del documento de tesis (formato MaIE)")
    ap.add_argument("nombres", nargs="*", help="figuras a generar (todas si se omite)")
    a = ap.parse_args(argv)
    por_nombre = {s["nombre"]: s for s in FIGURAS}
    nombres = a.nombres or list(por_nombre)
    malos = [n for n in nombres if n not in por_nombre]
    exige(not malos, f"figuras desconocidas: {malos}")
    A.compuertas_comunidad()
    res = [genera(por_nombre[n]) for n in nombres]
    comprueba_pdf(res)
    for r in res:
        print(f"  {r['nombre']:<22} {r['caja']}  {r['ancho']:.5f} × {r['alto']:.3f} in  "
              f"letra mínima {r['letra']:.2f} pt")
    ok(f"letra ≥ {LETRA_MIN} pt, todo dentro del lienzo y datos iguales a la figura fuente")
    print("[gen_figuras_entrega] FIGURAS DE ENTREGA ESCRITAS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
