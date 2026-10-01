"""
gen_figuras_articulo.py — Figuras, tablas `.tex` y resumen gráfico del artículo
para IEEE Latin America Transactions (canon 2026-09).
===============================================================================
Tarea 3 del plan `docs/superpowers/plans/2026-09-29-articulo-latam.md` (spec
`docs/superpowers/specs/2026-09-28-articulo-latam-design.md`, §3 y §4). No
simula nada y tiene UNA sola entrada numérica:
`SALIDAS_SERVIDOR/cifras_articulo_2026-09-30/cifras.csv` (Tarea 1; desde el
2026-09-30 la tabla ampliada de la revisión del artículo en español, cuyas 482
cifras antiguas son idénticas a las del 29), cuya huella
(tamaño y sha256, grupo `e1/L` de `Documentos/canon_2026-09/HUELLAS.csv`) se
comprueba antes de leerla. Dibuja con la columna `valor` y escribe todo número
impreso (rótulos, tablas) con la columna `texto_en`.

Salidas:

    Documentos/articulo_latam/v2/figuras/
        fig1_comunidad        esquema de la comunidad (sin cifras)
        fig2_cascada_E0       cascada de E0: C4 → +(C1 − C4) → +banda → +reclasificación → P2P
        fig3_trece_casos      P2P − C4 = (C1 − C4) + (P2P − C1) en los 13 casos, con P2P colectivo − C4
        fig4_gsa_inversion    P(inversión) del GSA: 12 casos × 5 brechas, con su intervalo al 95 %
      cada una en .pdf (vectorial, caja exacta) y .png (600 dpi), con .csv, .mat y .fuente.txt
    Documentos/articulo_latam/v2/manuscrito/tablas/
        tabla1_mecanismos.tex     texto normativo, sin cifras del canon
        tabla2_trece_casos.tex    brechas de comunidad de los 13 casos (texto_en)
    Documentos/articulo_latam/v2/resumen_grafico/graphical_abstract.png
        1328 × 531 px a 300 dpi, ≤ 5 MB

Compuertas (fallan en voz alta con `SystemExit`):
  * huella de `cifras.csv`;
  * `texto_en` es el redondeo de `valor` en cada cifra usada;
  * por caso, al peso (1 COP = 1e-6 MCOP): P2P − C1, C1 − C4, P2P − C4 y
    P2P colectivo − C4 son las restas de los beneficios en ese sentido (un signo
    invertido falla) y P2P − C4 = (P2P − C1) + (C1 − C4); P2P − C1 = banda +
    reclasificación dentro del float32 del almacén (1e-7 del beneficio del
    mercado, la tolerancia de `cifras_articulo.py`); el porcentaje sobre C4 es
    la división;
  * C1 − C4 es negativo exactamente en E4, E5 e I1;
  * la cascada de E0 cierra al peso: C4 + (C1 − C4) + banda + reclasificación = P2P;
  * GSA: 12 casos sin CV2, lo ≤ p ≤ hi, P nula ⇒ intervalo nulo, y el punto
    base de P2P − C1, P2P − C4 y C4 − C1 es el de la matriz (el de C4 − C1, con
    el signo contrario al de C1 − C4);
  * las dimensiones de cada PDF (pypdf) son las de la caja y el PNG del resumen
    mide 1328 × 531 y pesa 5 MB o menos.

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/gen_figuras_articulo.py

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
import scipy.io as sio

for _s in (sys.stdout, sys.stderr):          # consola cp1252 de Windows
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ / "Documentos" / "articulo_latam" / "estilo"))
import estilo_latam as E  # noqa: E402  (hereda el estilo de la tesis y fija la caja)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

HUELLAS = RAIZ / "Documentos" / "canon_2026-09" / "HUELLAS.csv"
RUTA_CIFRAS = "cifras_articulo_2026-09-30/cifras.csv"
CIFRAS = RAIZ / "SALIDAS_SERVIDOR" / RUTA_CIFRAS
V2 = RAIZ / "Documentos" / "articulo_latam" / "v2"
DIR_FIG = V2 / "figuras"
DIR_TAB = V2 / "manuscrito" / "tablas"
DIR_GA = V2 / "resumen_grafico"
GUION = "reformateo/documento/scripts/articulo/gen_figuras_articulo.py"

CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU"]
CASOS_GSA = [c for c in CASOS if c != "CV2"]
INST = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
# La brecha del GSA con clave C4_C1 se rotula «C1 − C4», como en la Fig. 3 y la
# Tabla II: P(inversión) no depende del sentido de la resta (decisión del
# controlador, ronda 1). El punto base se compara con el signo de la clave.
BRECHAS_GSA = [("P2P_C1", "P2P\n− C1"), ("P2P_C4", "P2P\n− C4"),
               ("P2Pcol_C1", "P2P coll.\n− C1"), ("C4_C1", "C1\n− C4"),
               ("P2P_C5", "P2P\n− C5")]
LETRA_MIN = 7.0      # pt a tamaño de impresión, figuras del artículo
LETRA_MIN_GA = 6.5   # pt, resumen gráfico (4.43 × 1.77 in)
LETRAS: dict[str, float] = {}
PESO = 1e-6          # 1 COP en MCOP
DPI = 600            # spec §4: PNG a 600 dpi

# Okabe-Ito
OI = {"negro": "#000000", "naranja": "#E69F00", "celeste": "#56B4E9",
      "verde": "#009E73", "amarillo": "#F0E442", "azul": "#0072B2",
      "bermellon": "#D55E00", "purpura": "#CC79A7"}
# Azul oscuro frente a naranja claro: se distinguen también en gris
# (luminancia ~0.34 frente a ~0.64); el bermellón quedaba a ~0.51 del azul.
C_C1C4 = OI["azul"]          # C1 − C4, en todas las figuras
# C1 − C4 negativo (E4, E5 e I1) en la Fig. 3: azul claro en lugar del rayado,
# que casi no se veía en E5 y dejaba artefactos en los visores de Poppler (M-19
# de revision_final.md). Luma ~0.82, frente a ~0.34 del azul y ~0.64 del naranja.
C_C1C4_NEG = "#BCD8EE"
C_P2PC1 = OI["naranja"]      # P2P − C1 (banda), en todas las figuras
C_RECLAS = OI["amarillo"]    # reclasificación
C_COL = OI["verde"]          # P2P por la vía del colectivo
C_TOTAL_REF = "#BBBBBB"      # C4 (nivel de referencia)
C_TOTAL_P2P = "#555555"      # P2P (nivel)

# La spec pide Times en las figuras; el módulo base declara DejaVu Sans. Se
# amplía aquí, sin modificar el módulo de estilo.
RC_ARTICULO = {
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "STIXGeneral"],
    "mathtext.fontset": "stix",
    "axes.unicode_minus": True,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[gen_figuras_articulo] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    print(f"[gen_figuras_articulo]   OK  {msg}")


# ── Lectura de la tabla de cifras, con su huella ────────────────────────────
def _lee_cifras() -> tuple[pd.DataFrame, str]:
    h = pd.read_csv(HUELLAS)
    f = h[(h.grupo == "e1/L") & (h.ruta == RUTA_CIFRAS)]
    exige(len(f) == 1, f"{RUTA_CIFRAS}: {len(f)} filas e1/L en HUELLAS.csv (se esperaba 1)")
    datos = CIFRAS.read_bytes()
    sha = hashlib.sha256(datos).hexdigest()
    exige(len(datos) == int(f.iloc[0].bytes), f"cifras.csv: {len(datos)} bytes, huella {f.iloc[0].bytes}")
    exige(sha == f.iloc[0].sha256, "cifras.csv: sha256 distinto de la huella e1/L")
    d = pd.read_csv(io.BytesIO(datos), dtype=str, keep_default_na=False, encoding="utf-8")
    exige(list(d.columns) == ["clave", "valor", "unidad", "texto_en", "definicion", "fuente",
                              "seccion_canon"], "cifras.csv: cabecera inesperada")
    exige(d.clave.is_unique, "cifras.csv: claves repetidas")
    ok(f"huella de cifras.csv (e1/L, {len(datos)} bytes, sha256 {sha[:16]}…), {len(d)} filas")
    return d.set_index("clave"), sha


TAB, SHA = _lee_cifras()
USADAS: dict[str, set[str]] = {}


def _usa(clave: str, dest: str | None) -> pd.Series:
    exige(clave in TAB.index, f"falta la clave {clave} en cifras.csv")
    if dest:
        USADAS.setdefault(dest, set()).add(clave)
    return TAB.loc[clave]


def V(clave: str, dest: str | None = None) -> float:
    """Valor numérico, finito y con su texto_en coherente."""
    f = _usa(clave, dest)
    v = float(f.valor)
    exige(np.isfinite(v), f"{clave}: valor no finito")
    _coherente(clave, v, f.texto_en)
    return v


def T(clave: str, dest: str | None = None) -> str:
    """Texto en inglés tal como se imprime (texto_en)."""
    f = _usa(clave, dest)
    if re.fullmatch(r"-?[\d.,]+(?: %)?", f.texto_en):
        _coherente(clave, float(f.valor), f.texto_en)
    return f.texto_en


def _coherente(clave: str, v: float, t: str) -> None:
    """texto_en es el redondeo de valor a los decimales que muestra."""
    m = re.fullmatch(r"(-?[\d,]+)(?:\.(\d+))?( %)?", t)
    exige(m is not None, f"{clave}: texto_en no numérico {t!r}")
    dec = len(m.group(2) or "")
    tv = float(t.replace(",", "").replace(" %", ""))
    exige(abs(tv - v) <= 0.5 * 10 ** (-dec) + 1e-9,
          f"{clave}: texto_en {t!r} no es el redondeo de {v}")


def sin_pct(t: str) -> str:
    return t[:-2] if t.endswith(" %") else t


def luma(color: str) -> float:
    """Luma Rec. 601 de un color hexadecimal (0 negro, 1 blanco)."""
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b


def menos_fig(t: str) -> str:
    """Signo menos tipográfico para las figuras."""
    return "−" + t[1:] if t.startswith("-") else t


def menos_tex(t: str) -> str:
    """Signo menos de LaTeX para las tablas (el chequeo de cifras lo normaliza)."""
    t = t.replace("%", r"\%")
    return "$-$" + t[1:] if t.startswith("-") else t


# ── Compuertas de las cifras de comunidad ───────────────────────────────────
def compuertas_comunidad() -> None:
    negativos = []
    for c in CASOS:
        b = {m: V(f"com__{c}__{m}") for m in ["P2P", "P2Pcol", "C1", "C4"]}
        p2p_c1, c1_c4 = V(f"com__{c}__P2P_C1"), V(f"com__{c}__C1_C4")
        p2p_c4, col_c4 = V(f"com__{c}__P2P_C4"), V(f"com__{c}__P2Pcol_C4")
        banda, reclas = V(f"com__{c}__banda"), V(f"com__{c}__reclas")
        exige(abs(p2p_c1 - (b["P2P"] - b["C1"])) <= PESO, f"{c}: P2P − C1 no es P2P menos C1")
        exige(abs(c1_c4 - (b["C1"] - b["C4"])) <= PESO, f"{c}: C1 − C4 no es C1 menos C4 (¿signo invertido?)")
        exige(abs(p2p_c4 - (b["P2P"] - b["C4"])) <= PESO, f"{c}: P2P − C4 no es P2P menos C4")
        exige(abs(col_c4 - (b["P2Pcol"] - b["C4"])) <= PESO, f"{c}: P2P colectivo − C4 no es la resta")
        exige(abs(p2p_c4 - (p2p_c1 + c1_c4)) <= PESO, f"{c}: P2P − C4 ≠ (P2P − C1) + (C1 − C4) al peso")
        # banda y reclasificación salen del almacén, en float32: cierran contra P2P − C1
        # de Resumen dentro de 1e-7 del beneficio del mercado (la tolerancia de
        # cifras_articulo.py; hasta 6,2 COP en N1), no al peso.
        exige(abs(p2p_c1 - (banda + reclas)) <= 1e-7 * b["P2P"],
              f"{c}: P2P − C1 ≠ banda + reclasificación dentro del float32")
        pct = V(f"com__{c}__P2Pcol_C4_pct")
        exige(abs(pct - 100 * col_c4 / b["C4"]) <= 1e-6, f"{c}: P2P colectivo − C4 en % de C4 no es la división")
        if c1_c4 < 0:
            negativos.append(c)
    exige(negativos == ["E4", "E5", "I1"], f"C1 − C4 negativo en {negativos}, se esperaba E4, E5 e I1")
    ok("13 casos: restas en su sentido y P2P − C4 = (P2P − C1) + (C1 − C4) al peso; P2P − C1 = "
       "banda + reclasificación dentro del float32 (1e-7 de P2P); % de C4; C1 − C4 < 0 solo en E4, E5 e I1")


def eje_truncado(valores: list[float], *, sobre: float, bajo: float = 0.3) -> tuple[float, float]:
    """Límites de un eje que no empieza en cero, derivados de los datos: el piso es
    el medio MCOP entero por debajo del menor valor menos `bajo`, y el techo, el
    mayor más `sobre` (sitio para los rótulos). Falla si algún valor queda fuera."""
    lo, hi = min(valores), max(valores)
    piso = np.floor(2 * (lo - bajo)) / 2
    techo = hi + sobre
    exige(all(piso < v < techo for v in valores), f"eje truncado [{piso}, {techo}] no contiene {valores}")
    return float(piso), float(techo)


# ── Guardado con rastro ─────────────────────────────────────────────────────
def _guardar_mat(df: pd.DataFrame, ruta: Path) -> None:
    """Una variable por columna del CSV (mismo formato que estilo.guardar(mat=True))."""
    salida = {}
    for col in df.columns:
        k = re.sub(r"[^A-Za-z0-9_]", "_", str(col))
        if not k or not k[0].isalpha():
            k = "v_" + k
        k = k[:31]
        exige(k not in salida, f"columna repetida al sanear para MATLAB: {k}")
        s = df[col]
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            salida[k] = s.to_numpy(dtype=float)
        else:
            salida[k] = np.array(s.astype(str).tolist(), dtype=object)
    sio.savemat(ruta, salida, do_compression=True)


def _fuente(ruta: Path, nombre: str, dest: str, nota: str) -> None:
    claves = sorted(USADAS.get(dest, set()))
    ruta.write_text(
        f"Figura o tabla: {nombre}\n"
        f"Guion: {GUION}\n"
        f"Artefacto leído (única entrada numérica):\n"
        f"  - SALIDAS_SERVIDOR/{RUTA_CIFRAS}  (HUELLAS.csv, grupo e1/L; sha256 {SHA})\n"
        f"Claves usadas ({len(claves)}):\n" + "".join(f"  - {k}\n" for k in claves)
        + f"Nota: {nota}\n", encoding="utf-8")


def letra_minima(fig, nombre: str, minimo: float) -> float:
    """Menor tamaño de letra (pt) de todo texto visible de la figura, rótulos de
    ejes y de la barra de color incluidos; falla si baja de `minimo`."""
    fig.canvas.draw()
    tams = [t.get_fontsize() for t in fig.findobj(matplotlib.text.Text)
            if t.get_visible() and t.get_text().strip()]
    exige(bool(tams), f"{nombre}: sin textos")
    m = min(tams)
    exige(m >= minimo - 1e-9, f"{nombre}: letra de {m} pt, por debajo de {minimo} pt")
    LETRAS[nombre] = m
    return m


def guardar(fig, nombre: str, datos: pd.DataFrame, nota: str) -> None:
    letra_minima(fig, nombre, LETRA_MIN)
    DIR_FIG.mkdir(parents=True, exist_ok=True)
    base = DIR_FIG / nombre
    fig.savefig(base.with_suffix(".pdf"))
    fig.savefig(base.with_suffix(".png"), dpi=DPI)
    plt.close(fig)
    datos.to_csv(base.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    _guardar_mat(datos, base.with_suffix(".mat"))
    _fuente(base.with_suffix(".fuente.txt"), nombre, nombre, nota)
    print(f"  escrito {nombre}.pdf / .png / .csv / .mat / .fuente.txt")


# ── Fig. 1: la comunidad ────────────────────────────────────────────────────
def _caja(ax, x0, y0, w, h, texto, *, fc="white", ec="#333333", ls="-", lw=0.8,
          fs=7.0, peso="normal", r=1.2, z=2):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, ls=ls, lw=lw, zorder=z))
    if texto:
        ax.text(x0 + w / 2, y0 + h / 2, texto, ha="center", va="center", fontsize=fs,
                fontweight=peso, color=E.COLOR_TEXTO, zorder=z + 1, linespacing=1.15)


def _flecha(ax, a, b, *, ls="-", color="#333333", lw=0.9, estilo="<|-|>", rad=0.0, z=3):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=estilo, mutation_scale=6, lw=lw,
                                 ls=ls, color=color, zorder=z,
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0))


def fig1() -> None:
    nombre = "fig1_comunidad"
    W, H = E.ANCHO_COL, 2.85
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ytop = 100 * H / W                      # ~86.0 unidades (misma escala en x e y)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, ytop)
    ax.axis("off")
    fs, suave = 7.0, E.COLOR_TEXTO_SUAVE

    # Fila superior: bolsa y comercializadores
    ysup = ytop - 14
    _caja(ax, 1, ysup, 37, 12, "XM wholesale market\n(hourly spot price)", fc="#F2F2F2", fs=fs)
    _caja(ax, 57, ysup, 42, 12, "Retailers\nASC Ingeniería · CEDENAR", fc="#F2F2F2", fs=fs)
    _flecha(ax, (38, ysup + 6), (57, ysup + 6), ls="--", color=suave)
    ax.text(47.5, ysup + 4.4, "excess at\nspot price", ha="center", va="top", fontsize=fs,
            color=suave, linespacing=1.05)

    # Red de distribución
    yred = ysup - 18
    _caja(ax, 1, yred, 83, 9, "Distribution network: CEDENAR (network operator)", fc="#E8F1F8",
          ec=OI["azul"], fs=fs)

    # El colectivo (límite discontinuo)
    ycol_top = yred - 12
    _caja(ax, 1, 1.5, 88, ycol_top - 1.5, "", fc="none", ec=C_COL, ls=(0, (4, 2)), lw=1.0, r=2.5, z=1)

    # Liquidación por medidor: del comercializador al colectivo, por la derecha
    xs = 86.5
    _flecha(ax, (xs, ysup), (xs, ycol_top), ls="--", color=suave, estilo="-|>")
    ax.text(94.3, (ysup + ycol_top) / 2, "settlement per meter\n(Art. 25; Annex 4)",
            rotation=90, ha="center", va="center", fontsize=fs, color=suave, linespacing=1.05)

    # Energía medida entre la comunidad y la red
    xe = 55
    _flecha(ax, (xe, ycol_top), (xe, yred), color="#333333")
    ax.text(xe + 2, (ycol_top + yred) / 2, "import / surplus", ha="left", va="center",
            fontsize=fs, color=suave)

    # Leyenda de trazos
    yl = (ycol_top + yred) / 2
    ax.plot([3, 9], [yl, yl], color="#333333", lw=0.9)
    ax.text(10, yl, "energy", ha="left", va="center", fontsize=fs, color=suave)
    ax.plot([23, 29], [yl, yl], color=suave, lw=0.9, ls="--")
    ax.text(30, yl, "settlement", ha="left", va="center", fontsize=fs, color=suave)

    ax.text(3, ycol_top - 1.8, "Collective self-generation (CREG 101 072, Arts. 18–21)",
            ha="left", va="top", fontsize=fs, color=E.COLOR_TEXTO, style="italic")

    # Las cinco instituciones
    w, g, x0, yb, hb = 15.6, 1.6, 3.0, 17, 12.5
    centros = []
    for k, n in enumerate(INST):
        x = x0 + k * (w + g)
        _caja(ax, x, yb, w, hb, "", fc="white", ec="#333333")
        ax.text(x + w / 2, yb + hb * 0.68, n, ha="center", va="center", fontsize=fs,
                fontweight="bold", color=E.COLOR_TEXTO, zorder=4)
        ax.text(x + w / 2, yb + hb * 0.28, "PV + meter", ha="center", va="center", fontsize=fs,
                color=suave, zorder=4)
        centros.append(x + w / 2)
    # El mercado entre pares: un nodo común con todas las instituciones (todos los pares)
    xm0, xm1, ym0, ym1 = 12, 78, 4, 10.5
    _caja(ax, xm0, ym0, xm1 - xm0, ym1 - ym0, "P2P market: hourly price, all pairs (no specific rule)",
          fc="#FFF4E0", ec=C_P2PC1, fs=fs, r=1.5)
    for cx in centros:
        destino = (min(max(cx, xm0 + 3), xm1 - 3), ym1)
        _flecha(ax, (cx, yb), destino, ls=":", color="#8A5A00", lw=0.9, estilo="<|-|>")

    datos = pd.DataFrame({"elemento": ["institucion"] * 5 + ["red", "bolsa", "comercializadores",
                                                              "colectivo", "mercado P2P"],
                          "nombre": INST + ["CEDENAR (network operator)", "XM spot market",
                                            "ASC Ingenieria; CEDENAR",
                                            "CREG 101 072, Arts. 18-21",
                                            "P2P market, all pairs"]})
    guardar(fig, nombre, datos, "esquema sin cifras del canon; los nombres de las instituciones son "
            "los de INST (cifras_cap07.py) y los comercializadores los de la tesis, sección 4.7; "
            "el mercado P2P es un nodo común (todos los pares), no una cadena de vecinos")


# ── Fig. 2: cascada de E0 ───────────────────────────────────────────────────
def fig2() -> None:
    nombre, c = "fig2_cascada_E0", "E0"
    d = nombre
    c4, c1_c4 = V(f"com__{c}__C4", d), V(f"com__{c}__C1_C4", d)
    banda, reclas = V(f"com__{c}__banda", d), V(f"com__{c}__reclas", d)
    p2p, col, c1 = V(f"com__{c}__P2P", d), V(f"com__{c}__P2Pcol", d), V(f"com__{c}__C1", d)
    exige(abs(c4 + c1_c4 + banda + reclas - p2p) <= PESO, "cascada de E0: no cierra al peso")
    exige(abs(c4 + c1_c4 - c1) <= PESO, "cascada de E0: C4 + (C1 − C4) no es C1")
    ok("cascada de E0: C4 + (C1 − C4) + banda + reclasificación = P2P al peso")

    fig, ax = E.figura(alto=2.25)
    niveles = [c4, c4 + c1_c4, c4 + c1_c4 + banda, c4 + c1_c4 + banda + reclas]
    piso, techo = eje_truncado([c4, col, *niveles, p2p], sobre=0.45)
    pasos = [
        ("C4", piso, c4 - piso, C_TOTAL_REF, T(f"com__{c}__C4", d)),
        ("+(C1 − C4)", c4, c1_c4, C_C1C4, "+" + T(f"com__{c}__C1_C4", d)),
        ("+Band", niveles[1], banda, C_P2PC1, "+" + T(f"com__{c}__banda", d)),
        ("+Reclass.", niveles[2], reclas, C_RECLAS, "+" + T(f"com__{c}__reclas", d)),
        ("P2P", piso, p2p - piso, C_TOTAL_P2P, T(f"com__{c}__P2P", d)),
    ]
    x = np.arange(len(pasos))
    for i, (rot, y0, h, col_, txt) in enumerate(pasos):
        ax.bar(i, h, bottom=y0, width=0.62, color=col_, edgecolor="#333333", lw=0.5, zorder=3)
        ax.text(i, y0 + max(h, 0) + 0.06, txt, ha="center", va="bottom", fontsize=7.0,
                color=E.COLOR_TEXTO, zorder=5)
    # conectores entre escalones
    for i, nv in enumerate(niveles):
        ax.plot([i + 0.31, i + 0.69], [nv, nv], color="#555555", lw=0.6, ls=(0, (2, 1.5)), zorder=2)
    ax.text(1, c1 + 0.36, f"C1: {T(f'com__{c}__C1', d)}", ha="center", va="bottom", fontsize=7.0,
            color=E.COLOR_TEXTO_SUAVE)
    # vía legal: el mercado liquidado por el colectivo
    ax.axhline(col, color=C_COL, lw=1.1, ls="--", zorder=4)
    ax.text(2.5, col + 0.12, f"P2P via collective: {T(f'com__{c}__P2Pcol', d)}",
            ha="center", va="bottom", fontsize=7.0, color=E.COLOR_TEXTO,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9), zorder=6)
    ax.set_xticks(x, [p[0] for p in pasos])
    ax.set_ylim(piso, techo)
    ax.set_xlim(-0.55, len(pasos) - 0.45)
    E.aplicar_estilo_ejes(ax, ylabel="Community net benefit (MCOP)")
    ax.grid(axis="x", visible=False)
    # el eje no empieza en cero: marca de corte
    kw = dict(transform=ax.transAxes, color="#333333", clip_on=False, lw=0.7)
    ax.plot([-0.02, 0.02], [0.015, 0.045], **kw)
    ax.plot([-0.02, 0.02], [0.045, 0.075], **kw)
    fig.tight_layout(pad=0.3)

    datos = pd.DataFrame({
        "paso": ["C4", "C1_menos_C4", "banda", "reclasificacion", "P2P", "P2P_colectivo"],
        "base_MCOP": [0.0, c4, niveles[1], niveles[2], 0.0, 0.0],
        "altura_MCOP": [c4, c1_c4, banda, reclas, p2p, col],
        "nivel_final_MCOP": [c4, niveles[1], niveles[2], niveles[3], p2p, col],
        "texto_en": [T(f"com__{c}__C4"), T(f"com__{c}__C1_C4"), T(f"com__{c}__banda"),
                     T(f"com__{c}__reclas"), T(f"com__{c}__P2P"), T(f"com__{c}__P2Pcol")]})
    guardar(fig, nombre, datos, f"eje vertical desde {piso} MCOP (marcado con un corte); la "
            "cascada cierra al peso contra P2P (compuerta del guion)")


# ── Fig. 3: los 13 casos ────────────────────────────────────────────────────
def fig3() -> None:
    nombre = d = "fig3_trece_casos"
    c1c4 = np.array([V(f"com__{c}__C1_C4", d) for c in CASOS])
    p2pc1 = np.array([V(f"com__{c}__P2P_C1", d) for c in CASOS])
    p2pc4 = np.array([V(f"com__{c}__P2P_C4", d) for c in CASOS])
    colc4 = np.array([V(f"com__{c}__P2Pcol_C4", d) for c in CASOS])
    exige(np.all(np.abs(c1c4 + p2pc1 - p2pc4) <= PESO), "fig3: las partes no suman P2P − C4")
    exige(np.all(p2pc1 > 0), "fig3: P2P − C1 no es positivo en todos los casos")

    fig, ax = E.figura(alto=2.45)
    x = np.arange(len(CASOS))
    w = 0.66
    # apilado con signo: lo positivo sobre cero, lo negativo bajo cero
    pos_c1c4 = np.clip(c1c4, 0, None)
    neg_c1c4 = np.clip(c1c4, None, 0)
    ax.bar(x, pos_c1c4, width=w, color=C_C1C4, edgecolor="#333333", lw=0.4, zorder=3,
           label="C1 − C4 (case-2 charges)")
    # los tres rellenos se distinguen también en gris (luma Rec. 601)
    lumas = {n: luma(c) for n, c in [("C1 − C4", C_C1C4), ("C1 − C4 < 0", C_C1C4_NEG),
                                      ("P2P − C1", C_P2PC1)]}
    orden = sorted(lumas.values())
    exige(min(b - a for a, b in zip(orden, orden[1:])) >= 0.15,
          f"fig3: rellenos poco distintos en gris {lumas}")
    ax.bar(x, neg_c1c4, width=w, color=C_C1C4_NEG, edgecolor="#333333", lw=0.4, zorder=3,
           label="C1 − C4 < 0 (C4 leads C1)")
    ax.bar(x, p2pc1, bottom=pos_c1c4, width=w, color=C_P2PC1, edgecolor="#333333", lw=0.4,
           zorder=3, label="P2P − C1 (band + reclass.)")
    ax.scatter(x, p2pc4, marker="_", s=70, lw=1.4, color="#000000", zorder=5, label="P2P − C4")
    ax.scatter(x, colc4, marker="D", s=13, color=C_COL, edgecolor="#000000", lw=0.5, zorder=6,
               label="P2P via collective − C4")
    ax.axhline(0, color="#333333", lw=0.7, zorder=4)
    ax.set_xticks(x, CASOS)
    ax.tick_params(axis="x", labelsize=7.0)
    ax.set_xlim(-0.6, len(CASOS) - 0.4)
    ymin = min(neg_c1c4.min(), colc4.min())
    ax.set_ylim(ymin - 1.5, max(pos_c1c4 + p2pc1) * 1.42)
    E.aplicar_estilo_ejes(ax, xlabel="Case", ylabel="Difference with C4 (MCOP)")
    ax.grid(axis="x", visible=False)
    h, l = ax.get_legend_handles_labels()
    orden_ley = ["C1 − C4 (case-2 charges)", "C1 − C4 < 0 (C4 leads C1)", "P2P − C1 (band + reclass.)",
                 "P2P − C4", "P2P via collective − C4"]
    exige(sorted(l) == sorted(orden_ley), f"fig3: leyenda inesperada {l}")
    ax.legend([h[l.index(e)] for e in orden_ley], orden_ley, loc="upper right", ncol=2, fontsize=7.0, handlelength=1.3, columnspacing=0.8,
              borderpad=0.3, labelspacing=0.25, handletextpad=0.4)
    fig.tight_layout(pad=0.3)

    datos = pd.DataFrame({"caso": CASOS, "C1_menos_C4_MCOP": c1c4, "P2P_menos_C1_MCOP": p2pc1,
                          "P2P_menos_C4_MCOP": p2pc4, "P2Pcol_menos_C4_MCOP": colc4})
    guardar(fig, nombre, datos, "barras apiladas con signo: C1 − C4 (azul; azul claro, sin "
            "rayado, si es negativo, E4, E5 e I1) y P2P − C1 (naranja) sobre cero; raya negra = "
            "P2P − C4; rombo verde = P2P colectivo − C4")


# ── Fig. 4: P(inversión) del GSA ────────────────────────────────────────────
def fig4() -> None:
    nombre = d = "fig4_gsa_inversion"
    P = np.zeros((len(CASOS_GSA), len(BRECHAS_GSA)))
    filas = []
    for i, c in enumerate(CASOS_GSA):
        for j, (b, _) in enumerate(BRECHAS_GSA):
            p, lo, hi = (V(f"gsa__{c}__{b}__{s}", d) for s in ["p", "lo", "hi"])
            exige(lo <= p <= hi, f"GSA {c} {b}: P fuera de su intervalo")
            exige(p != 0 or (lo == 0 and hi == 0), f"GSA {c} {b}: P nula con intervalo no nulo")
            P[i, j] = p
            filas.append(dict(caso=c, brecha=b, p_pct=p, lo_pct=lo, hi_pct=hi,
                              n_base=V(f"gsa__{c}__n", d)))
        # el punto base del GSA es el de la matriz, con el signo de cada brecha
        for b, k, s in [("P2P_C1", "P2P_C1", 1), ("P2P_C4", "P2P_C4", 1), ("C4_C1", "C1_C4", -1)]:
            exige(abs(V(f"gsa__{c}__{b}__base") - s * V(f"com__{c}__{k}")) <= PESO,
                  f"GSA {c} {b}: el punto base no es el de la matriz (¿signo?)")
    exige("gsa__CV2__P2P_C1__p" not in TAB.index, "el GSA no debería tener CV2")
    exige(int(V("gsa__n_casos")) == len(CASOS_GSA), "gsa__n_casos no es 12")
    ok("GSA: 12 casos, lo ≤ p ≤ hi, P nula ⇒ intervalo nulo, punto base = matriz con su signo")

    cmap = LinearSegmentedColormap.from_list("azul_oi", ["#FFFFFF", "#9CCBE8", OI["azul"], "#003B5C"])
    fig = plt.figure(figsize=(E.ANCHO_COL, 4.3))
    ax = fig.add_axes([0.155, 0.13, 0.81, 0.79])
    cax = fig.add_axes([0.155, 0.068, 0.81, 0.017])
    im = ax.imshow(P, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    for i, c in enumerate(CASOS_GSA):
        for j, (b, _) in enumerate(BRECHAS_GSA):
            p = P[i, j]
            if p == 0:
                ax.text(j, i, "0", ha="center", va="center", fontsize=7.0, color="#8A8A8A")
                continue
            colt = "white" if p > 55 else E.COLOR_TEXTO
            lo, hi = T(f"gsa__{c}__{b}__lo", d), T(f"gsa__{c}__{b}__hi", d)
            # sin «%» en la celda: la unidad va en la barra de color
            ax.text(j, i - 0.19, sin_pct(T(f"gsa__{c}__{b}__p", d)), ha="center", va="center",
                    fontsize=7.0, color=colt, fontweight="bold")
            ax.text(j, i + 0.22, f"{sin_pct(lo)}–{sin_pct(hi)}", ha="center", va="center",
                    fontsize=7.0, color=colt)
    ax.set_xticks(range(len(BRECHAS_GSA)), [r for _, r in BRECHAS_GSA], fontsize=7.0)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(CASOS_GSA)),
                  [f"{c} ({T(f'gsa__{c}__n', d)})" for c in CASOS_GSA], fontsize=7.0)
    ax.text(-0.02, 1.0, "Case (n)", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7.0, color=E.COLOR_TEXTO)
    ax.set_xticks(np.arange(-0.5, len(BRECHAS_GSA)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(CASOS_GSA)), minor=True)
    ax.grid(which="minor", color="#D0D0D0", lw=0.5)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="both", length=0)
    for s in ax.spines.values():
        s.set_linewidth(0.6)
        s.set_color("#888888")
    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    cb.set_label("P(sign inversion) in the GSA box (%); 95 % interval below",
                 fontsize=7.0, labelpad=1.5)
    cb.ax.tick_params(labelsize=7.0, length=2)
    cb.outline.set_linewidth(0.5)

    guardar(fig, nombre, pd.DataFrame(filas),
            "celdas en blanco con «0»: ninguna inversión en la muestra; debajo de cada valor no "
            "nulo, su intervalo al 95 % (sin «%»; la unidad está en la barra); n = muestras base del "
            "Sobol (texto_en); CV2 no está en el GSA; la brecha de clave C4_C1 se rotula «C1 − C4», "
            "como en la Fig. 3 y la Tabla II, porque P(inversión) no depende del sentido de la resta")


# ── Tablas .tex ─────────────────────────────────────────────────────────────
TABLA1 = r"""% Tabla I del articulo IEEE LatAm (canon 2026-09). Generada por
% reformateo/documento/scripts/articulo/gen_figuras_articulo.py. Texto normativo
% (tesis, secciones 3.2, 3.4, 3.5 y 6.2 a 6.9); sin cifras del canon.
% Solo usa el paquete array de la plantilla (columnas p{}).
\begin{table*}[!t]
% Pie reescrito en la Tarea 5 (2026-09-29); titulo corto y nota bajo la tabla
% en la correccion final (M-16 de revision_final.md).
\caption{Settlement Mechanisms Compared}
\label{tab:mecanismos}
\centering
\footnotesize
\renewcommand{\arraystretch}{1.15}
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{0.1\textwidth}>{\raggedright\arraybackslash}p{0.185\textwidth}>{\raggedright\arraybackslash}p{0.195\textwidth}>{\raggedright\arraybackslash}p{0.185\textwidth}>{\raggedright\arraybackslash}p{0.13\textwidth}>{\raggedright\arraybackslash}p{0.12\textwidth}@{}}
\hline
Mechanism & Rule & What is settled & Price of surplus or internal energy & Charges paid on credited energy & Eligible \\
\hline
P2P market & No specific rule; residual per member under CREG 174 Art.~25 and Annex~4 & Hourly internal trades; each member's residual injection and import with its own retailer & Uniform hourly price capped at the buyer's tariff; residual: credit up to monthly import, excess at hourly spot price & Trades: none (assumed); residual: plant's numeral & Not provided for \\
P2P via collective & C4 rules plus a civil contract among members (two-level route) & C4 with a monthly percentage set by the market's flows; internal payments at market prices & As C4; internal payments sum to zero & Case~2 on all credited energy, reassigned included & Yes, with an Art.~19 reporting agreement \\
C1 individual self-generation & CREG 174 Arts.~23 and~25; Annex~4 & Each member's gross injection and import with its own retailer, monthly with an hourly cut-off & Credit at the swap price (tariff minus deduction) up to monthly import; excess at hourly spot price & Plant's numeral: Cv up to 100~kW; Cv plus network charges above 100~kW up to 1~MW & Yes \\ % cifra-ok: umbrales normativos del art. 25 de la CREG 174 (100 kW y 1 MW)
C2 internal fixed-price contract & No specific rule (CREG 174 Art.~23 lit.~a allows sales only to generators or retailers) & The P2P trades at a price fixed in advance; unsigned energy as in C1 & Midpoint of each pair's band; unsigned residual as in C1 & Signed: none (assumed); residual: plant's numeral & Not provided for \\
C3 wholesale exposure & Declared counterfactual; spot cap of CREG 101~066 & All hourly surplus sold to the spot market & Hourly spot price minus wholesale-market costs & No swap; wholesale-market costs & No \\
C4 collective self-generation & CREG 101~072 Arts.~18--21 (case~2 of Art.~20); CREG 174 Art.~25 & Monthly pooled surplus split by the Art.~19 percentage (equal, the Art.~9 default here), each share against the member's own import & Credit up to monthly import; excess at hourly spot price from the cut-off hour & Case~2 for every member: Cv plus network charges & Yes, if single retailer (Art.~10) \\
C5 remote self-generation & CREG 101~099 Arts.~4 and 15--22 & Generation sold to the wholesale market; consumption served by a registered contract, hourly & Contract price shares the avoided purchase; leftover at spot price minus market costs & No swap; network charges on consumption & No, reference only (Art.~4 lits.~iii, v, vi; Art.~17 lit.~ii) \\
\hline
\end{tabular}
\par\smallskip
{\footnotesize\raggedright Five mechanisms end in the credit of CREG 174, Art.~25, and differ in who receives it and what the retailer deducts. Cv: commercialization component; network charges: transmission, distribution, losses and restrictions.\par}
\end{table*}
"""


def tabla1() -> None:
    DIR_TAB.mkdir(parents=True, exist_ok=True)
    (DIR_TAB / "tabla1_mecanismos.tex").write_text(TABLA1, encoding="utf-8")
    print("  escrito tabla1_mecanismos.tex")


def tabla2() -> None:
    d = "tabla2_trece_casos"
    filas = []
    for c in CASOS:
        cols = [T(f"com__{c}__P2P_C1", d), T(f"com__{c}__C1_C4", d), T(f"com__{c}__P2P_C4", d),
                T(f"com__{c}__P2Pcol_C4", d), sin_pct(T(f"com__{c}__P2Pcol_C4_pct", d))]
        filas.append(f"{c} & " + " & ".join(menos_tex(t) for t in cols) + r" \\")
    tex = "\n".join([
        "% Tabla II del articulo IEEE LatAm (canon 2026-09). Generada por",
        f"% {GUION} desde SALIDAS_SERVIDOR/{RUTA_CIFRAS}",
        f"% (sha256 {SHA}); cada numero es el texto_en de su clave.",
        r"\begin{table}[!t]",
        "% Pie reescrito en la Tarea 7 (2026-09-29); titulo corto, nota bajo la tabla",
        "% y «to rounding» en la correccion final (M-7 y M-16 de revision_final.md).",
        r"\caption{Community Net-Benefit Gaps in the 13 Cases (MCOP)}",
        r"\label{tab:casos}",
        r"\centering",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{6pt}",
        r"\begin{tabular}{@{}lrrrrr@{}}",
        r"\hline",
        r" & P2P & C1 & P2P & \multicolumn{2}{c@{}}{P2P via coll.\ $-$ C4} \\",
        r"\cline{5-6}",
        r"Case & $-$ C1 & $-$ C4 & $-$ C4 & MCOP & \% of C4 \\",
        r"\hline",
        *filas,
        r"\hline",
        r"\end{tabular}",
        r"\par\smallskip",
        r"{\footnotesize\raggedright The last column is in \% of C4. The first three",
        r"columns add up, to rounding, as P2P~$-$~C4~=~(P2P~$-$~C1)~+~(C1~$-$~C4)",
        r"under the two settlement assumptions; the last two settle the market",
        r"through the collective, without them.\par}",
        r"\end{table}",
        ""])
    DIR_TAB.mkdir(parents=True, exist_ok=True)
    (DIR_TAB / "tabla2_trece_casos.tex").write_text(tex, encoding="utf-8")
    _fuente(DIR_TAB / "tabla2_trece_casos.fuente.txt", d, d,
            "sin columna de cobertura (no hay cifra con huella; decisión del controlador)")
    print("  escrito tabla2_trece_casos.tex / .fuente.txt")


# ── Resumen gráfico ─────────────────────────────────────────────────────────
def resumen_grafico() -> Path:
    d, c = "graphical_abstract", "E0"
    c4, c1_c4 = V(f"com__{c}__C4", d), V(f"com__{c}__C1_C4", d)
    p2p_c1, p2p, col = V(f"com__{c}__P2P_C1", d), V(f"com__{c}__P2P", d), V(f"com__{c}__P2Pcol", d)
    exige(abs(c4 + c1_c4 + p2p_c1 - p2p) <= PESO, "resumen gráfico: la cascada no cierra")
    for k in ["share_min", "share_max", "share_n", "share_casos_C1_sobre_C4", "col_pct_min",
              "col_pct_max"]:
        V(k, d)

    ancho_px, alto_px, dpi = 1328, 531, 300
    fs = 6.5
    fig = plt.figure(figsize=(ancho_px / dpi, alto_px / dpi), dpi=dpi)
    fig.text(0.5, 0.955, "Where does P2P value come from under Colombian rules?",
             ha="center", va="top", fontsize=8.6, fontweight="bold", color=E.COLOR_TEXTO)
    # el eje deja abajo una franja a todo lo ancho para la recomendación
    ax = fig.add_axes([0.095, 0.25, 0.37, 0.57])
    piso, techo = eje_truncado([c4, col, c4 + c1_c4, p2p], sobre=0.55, bajo=0.8)
    pasos = [("C4", piso, c4 - piso, C_TOTAL_REF, T(f"com__{c}__C4", d)),
             ("+(C1−C4)", c4, c1_c4, C_C1C4, "+" + T(f"com__{c}__C1_C4", d)),
             ("+(P2P−C1)", c4 + c1_c4, p2p_c1, C_P2PC1, "+" + T(f"com__{c}__P2P_C1", d)),
             ("P2P", piso, p2p - piso, C_TOTAL_P2P, T(f"com__{c}__P2P", d))]
    for i, (rot, y0, h, col_, txt) in enumerate(pasos):
        ax.bar(i, h, bottom=y0, width=0.6, color=col_, edgecolor="#333333", lw=0.4, zorder=3)
        ax.text(i, y0 + h + 0.07, txt, ha="center", va="bottom", fontsize=fs, color=E.COLOR_TEXTO)
    ax.axhline(col, color=C_COL, lw=1.0, ls="--", zorder=4)
    # rótulo de la vía legal bajo la línea, entre la barra de C4 y la de P2P (hueco sin barras)
    ax.text(1.5, col - 0.08, f"legal route\n(via collective): {T(f'com__{c}__P2Pcol', d)}",
            ha="center", va="top", fontsize=fs, color=E.COLOR_TEXTO, linespacing=1.05, zorder=6)
    ax.set_xticks(range(len(pasos)), [p[0] for p in pasos], fontsize=fs)
    ax.set_ylim(piso, techo)
    ax.set_xlim(-0.5, len(pasos) - 0.5)
    ax.tick_params(axis="y", labelsize=fs, length=2)
    ax.tick_params(axis="x", length=0)
    ax.set_ylabel("Net benefit, case E0 (MCOP)", fontsize=fs, labelpad=1.5)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#DDDDDD", lw=0.4, zorder=0)
    kw = dict(transform=ax.transAxes, color="#333333", clip_on=False, lw=0.5)
    ax.plot([-0.025, 0.025], [0.02, 0.06], **kw)
    ax.plot([-0.025, 0.025], [0.06, 0.10], **kw)

    # Corrección final (I-2 de revision_final.md): la ventaja del mercado se ata a
    # sus dos supuestos de liquidación, y la recomendación va completa, con el
    # término del artículo («internal trade»).
    rango = f"{sin_pct(T('share_min', d))}–{T('share_max', d)}"
    bloques = [
        (["Metered community: 5 institutions, Pasto, Colombia"], "normal", "normal"),
        ([f"• C1 − C4 is {rango} of P2P − C4 in {T('share_n', d)} of the",
          f"   {T('share_casos_C1_sobre_C4', d)} cases with C1 > C4: case-2 charges avoided",
          "   only by settling each member's residual",
          "   outside the collective (no rule provides it)"], "bold", "normal"),
        (["• P2P − C1, the band, assumes that internal",
          "   trade pays no charges (no rule provides it)"], "bold", "normal"),
        (["• Via the legal route (the collective):",
          f"   {menos_fig(T('col_pct_min', d))} to +{T('col_pct_max', d)} of C4"], "bold", "normal"),
    ]
    paso = 1.22 * fs / (alto_px / dpi * 72)          # interlineado en fracción de la figura
    y = 0.83
    for lineas, peso, estilo in bloques:
        for t in lineas:
            fig.text(0.51, y, t, ha="left", va="top", fontsize=fs, color=E.COLOR_TEXTO,
                     fontweight=peso, style=estilo)
            y -= paso
        y -= 0.45 * paso
    columna = list(fig.texts[1:])                    # sin el título
    rec = fig.text(0.5, 0.075, "The rules should state which charges internal trade pays "
                   "and whether it requires a collective.", ha="center", va="center",
                   fontsize=fs, color=E.COLOR_TEXTO, style="italic", fontweight="bold")
    letra_minima(fig, "graphical_abstract", LETRA_MIN_GA)
    # todo texto cabe en la figura; la columna no pisa el eje ni la recomendación
    fig.canvas.draw()
    caja, r = fig.bbox, rec.get_window_extent()
    eje = ax.get_tightbbox()
    for t in fig.texts:
        b = t.get_window_extent()
        exige(b.x0 >= caja.x0 and b.x1 <= caja.x1 and b.y0 >= caja.y0 and b.y1 <= caja.y1,
              f"resumen gráfico: «{t.get_text()}» se sale de la figura")
    for t in columna:
        b = t.get_window_extent()
        exige(b.y0 > r.y1 + 3, f"resumen gráfico: «{t.get_text()}» pisa la recomendación")
        exige(b.x0 > eje.x1 + 3, f"resumen gráfico: «{t.get_text()}» pisa el eje")
    exige(r.y1 < eje.y0 - 1, "resumen gráfico: la recomendación pisa el eje")

    DIR_GA.mkdir(parents=True, exist_ok=True)
    ruta = DIR_GA / "graphical_abstract.png"
    fig.savefig(ruta, dpi=dpi)
    plt.close(fig)
    _fuente(DIR_GA / "graphical_abstract.fuente.txt", d, d, "resumen gráfico de 1328 × 531 px a 300 dpi")
    print("  escrito graphical_abstract.png / .fuente.txt")
    return ruta


# ── Comprobaciones de las salidas ───────────────────────────────────────────
def comprueba_salidas(ga: Path) -> None:
    from PIL import Image
    from pypdf import PdfReader

    esperados = {"fig1_comunidad": E.ANCHO_COL, "fig2_cascada_E0": E.ANCHO_COL,
                 "fig3_trece_casos": E.ANCHO_COL, "fig4_gsa_inversion": E.ANCHO_COL}
    for n, ancho in esperados.items():
        for suf in [".pdf", ".png", ".csv", ".mat", ".fuente.txt"]:
            exige((DIR_FIG / (n + suf)).is_file(), f"falta {n}{suf}")
        caja = PdfReader(DIR_FIG / f"{n}.pdf").pages[0].mediabox
        w, h = float(caja.width) / 72, float(caja.height) / 72
        exige(abs(w - ancho) < 0.01, f"{n}.pdf mide {w:.4f} in de ancho, la caja es {ancho:.5f}")
        with Image.open(DIR_FIG / f"{n}.png") as im:
            px = im.size
        exige(abs(px[0] - ancho * DPI) <= 1, f"{n}.png: {px[0]} px, se esperaban {ancho * DPI:.0f}")
        print(f"  {n}.pdf {w:.5f} × {h:.5f} in (caja {ancho:.5f}); .png {px[0]} × {px[1]} px")
    for t in ["tabla1_mecanismos.tex", "tabla2_trece_casos.tex"]:
        exige((DIR_TAB / t).is_file(), f"falta {t}")
    with Image.open(ga) as im:
        px, dpi = im.size, im.info.get("dpi")
    peso = ga.stat().st_size
    exige(px == (1328, 531), f"graphical_abstract.png mide {px}, se esperaba (1328, 531)")
    exige(peso <= 5 * 1024 * 1024, f"graphical_abstract.png pesa {peso} B, más de 5 MB")
    exige(dpi is not None and round(dpi[0]) == 300, f"graphical_abstract.png: dpi {dpi}")
    print(f"  graphical_abstract.png {px[0]} × {px[1]} px, {round(dpi[0])} dpi, {peso / 1024:.1f} KiB")
    ok("ficheros, cajas de los PDF, PNG a 600 dpi y resumen gráfico de 1328 × 531 px ≤ 5 MB")
    for n, m in LETRAS.items():
        print(f"  letra mínima {n}: {m:.1f} pt")
    ok(f"letra ≥ {LETRA_MIN} pt en las figuras y ≥ {LETRA_MIN_GA} pt en el resumen gráfico")


def main() -> None:
    E.aplicar_rc()
    plt.rcParams.update(RC_ARTICULO)
    compuertas_comunidad()
    fig1()
    fig2()
    fig3()
    fig4()
    tabla1()
    tabla2()
    ga = resumen_grafico()
    comprueba_salidas(ga)
    print("[gen_figuras_articulo] FIGURAS Y TABLAS DEL ARTICULO ESCRITAS")


if __name__ == "__main__":
    main()
