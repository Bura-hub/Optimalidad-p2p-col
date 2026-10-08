"""
gen_resumen_grafico_en.py — Resumen gráfico (graphical abstract) del artículo
para IEEE Latin America Transactions, en inglés.
===============================================================================
Actividad 4.2 de la propuesta (difusión del resultado regulatorio). Requisitos
de la revista (página de envíos, consultada el 2026-10-08): PNG a color, mínimo
531 × 1328 px (alto × ancho), mínimo 400 ppp, como mucho 5 MB, un resumen
visual de la contribución principal que evite gráficas de desempeño, tablas y
texto. Por eso es un esquema, sin cifras de resultados: solo los hechos del
caso de estudio (cinco instituciones, 6 144 horas medidas) que ya están en el
resumen del artículo.

Salida: Documentos/articulo_latam/v2_es/resumen_grafico/graphical_abstract_en.png
(13,28 × 5,31 pulgadas a 400 ppp, es decir, 5312 × 2124 px) y su PDF.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle, FancyArrowPatch, Circle

RAIZ = Path(__file__).resolve().parents[4]
SALIDA = RAIZ / "Documentos" / "articulo_latam" / "v2_es" / "resumen_grafico"

W, H = 13.28, 5.31
DPI = 400

AZUL_T = "#0B3C5D"       # franja del título
TXT = "#1F1F1F"
SUAVE = "#5A5A5A"
GRIS_F = "#F2F2F2"
C1 = "#0072B2"           # autogeneración individual
C4 = "#009E73"           # autogeneración colectiva y fondo común
C4_F = "#E6F4EF"
P2P = "#D55E00"          # mercado P2P
P2P_F = "#FDEBDD"
PCOL = "#E69F00"         # intercambio del P2P colectivo
PCOL_F = "#FDF3DC"
PANEL = "#7FA7C7"        # paneles solares
C1_F = "#EAF2F9"
C4_PF = "#EBF6F1"
REJILLA = "#6E6E6E"

plt.rcParams.update({"font.family": "Arial", "font.size": 10})


def caja(ax, x, y, w, h, fc, ec, lw=1.2, ls="-", r=0.08, z=1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, lw=lw, ls=ls, zorder=z))


def flecha(ax, a, b, color=TXT, lw=1.3, ls="-", estilo="-|>", ms=9, z=4, cs="arc3,rad=0"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=estilo, mutation_scale=ms, color=color,
                                 lw=lw, ls=ls, zorder=z, connectionstyle=cs,
                                 shrinkA=0, shrinkB=0))


def edificio(ax, x, y, w=0.46, h=0.42, color="#8C8C8C"):
    """Un edificio con techo solar y un medidor: (x, y) es la esquina inferior izquierda."""
    ax.add_patch(Rectangle((x, y), w, h, fc="#FFFFFF", ec=color, lw=1.1, zorder=3))
    # ventanas
    for i in range(3):
        for j in range(2):
            ax.add_patch(Rectangle((x + 0.06 + i * 0.13, y + 0.08 + j * 0.15), 0.08, 0.09,
                                   fc="#D9E2EC", ec="none", zorder=4))
    # panel solar inclinado sobre el techo
    ax.add_patch(Polygon([(x + 0.02, y + h + 0.02), (x + w - 0.02, y + h + 0.02),
                          (x + w - 0.08, y + h + 0.15), (x + 0.08, y + h + 0.15)],
                         closed=True, fc=PANEL, ec="#3D5A73", lw=0.8, zorder=4))
    for k in range(1, 4):
        xa = x + 0.02 + k * (w - 0.04) / 4
        xb = x + 0.08 + k * (w - 0.16) / 4
        ax.plot([xa, xb], [y + h + 0.02, y + h + 0.15], color="#3D5A73", lw=0.5, zorder=5)


def casita(ax, cx, y, color, s=0.26):
    """Miembro estilizado: casa con techo, centrada en cx."""
    ax.add_patch(Rectangle((cx - s / 2, y), s, s * 0.75, fc="#FFFFFF", ec=color, lw=1.2, zorder=4))
    ax.add_patch(Polygon([(cx - s / 2 - 0.03, y + s * 0.75), (cx + s / 2 + 0.03, y + s * 0.75),
                          (cx, y + s * 1.25)], closed=True, fc=PANEL, ec="#3D5A73", lw=0.8, zorder=4))


def red(ax, cx, y, color="#6E6E6E"):
    """Torre de la red de distribución, base centrada en (cx, y)."""
    pts = [(cx - 0.13, y), (cx - 0.03, y + 0.42), (cx + 0.03, y + 0.42), (cx + 0.13, y)]
    ax.add_patch(Polygon(pts, closed=False, fill=False, ec=color, lw=1.2, zorder=4))
    for yy, dx in ((y + 0.30, 0.15), (y + 0.40, 0.11)):
        ax.plot([cx - dx, cx + dx], [yy, yy], color=color, lw=1.2, zorder=4)
    ax.plot([cx - 0.09, cx + 0.06], [y + 0.12, y + 0.24], color=color, lw=0.7, zorder=4)
    ax.plot([cx + 0.09, cx - 0.06], [y + 0.12, y + 0.24], color=color, lw=0.7, zorder=4)


def numero(ax, x, y, n, color):
    ax.add_patch(Circle((x, y), 0.105, fc=color, ec="none", zorder=6))
    ax.text(x, y - 0.004, str(n), ha="center", va="center", color="white", fontsize=8.5,
            fontweight="bold", zorder=7)


def encabezado(ax, x, y, w, texto, color):
    ax.add_patch(Rectangle((x, y), w, 0.30, fc=color, ec="none", zorder=2))
    ax.text(x + w / 2, y + 0.15, texto, ha="center", va="center", color="white",
            fontsize=10.5, fontweight="bold", zorder=3)


def main() -> None:
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # ---------------- franja del título
    ax.add_patch(Rectangle((0, H - 0.78), W, 0.78, fc=AZUL_T, ec="none", zorder=1))
    ax.text(W / 2, H - 0.29, "Peer-to-Peer Energy Markets for Colombian Energy Communities:",
            ha="center", va="center", color="white", fontsize=15, fontweight="bold")
    ax.text(W / 2, H - 0.59, "Network Charges, Settlement Rules, and a Collective Alternative",
            ha="center", va="center", color="white", fontsize=15, fontweight="bold")

    y0, y1 = 1.12, H - 0.98          # zona de los tres bloques
    # ---------------- bloque 1: la comunidad medida
    x1, w1 = 0.22, 3.30
    caja(ax, x1, y0, w1, y1 - y0, "#FFFFFF", "#9AA9B8", lw=1.0)
    encabezado(ax, x1, y1 - 0.30, w1, "MEASURED COMMUNITY", "#4A6A86")
    nombres = ["Udenar", "Unicesmag", "Unimar", "UCC", "HUDN"]
    xs = [x1 + w1 / 2 - 0.33 + (i - 2) * 0.62 for i in range(5)]
    yb = y0 + 1.35
    ax.plot([x1 + 0.15, x1 + w1 - 0.12], [yb + 0.95, yb + 0.95], color="#6E6E6E", lw=1.4, zorder=2)
    red(ax, x1 + w1 - 0.27, yb + 0.95)
    for xx, nom in zip(xs, nombres):
        edificio(ax, xx, yb)
        flecha(ax, (xx + 0.23, yb + 0.60), (xx + 0.23, yb + 0.93), color=REJILLA, lw=0.9,
               estilo="<|-|>", ms=6, z=2)
        ax.text(xx + 0.23, yb - 0.13, nom, ha="center", va="center", fontsize=8.6, color=TXT)
    ax.text(x1 + w1 / 2, y0 + 0.90, "5 institutions in Pasto, Colombia", ha="center",
            va="center", fontsize=11, fontweight="bold", color=TXT)
    ax.text(x1 + w1 / 2, y0 + 0.58, "Solar plants and bidirectional meters", ha="center",
            va="center", fontsize=9.8, color=SUAVE)
    ax.text(x1 + w1 / 2, y0 + 0.30, "6,144 metered hours (2025)", ha="center", va="center",
            fontsize=9.8, color=SUAVE)

    # flecha entre bloques
    flecha(ax, (x1 + w1 + 0.06, (y0 + y1) / 2), (x1 + w1 + 0.42, (y0 + y1) / 2),
           color="#9AA9B8", lw=3.2, ms=20)

    # ---------------- bloque 2: cómo se liquida la energía
    x2, w2 = 4.00, 5.40
    caja(ax, x2, y0, w2, y1 - y0, "#FFFFFF", "#9AA9B8", lw=1.0)
    encabezado(ax, x2, y1 - 0.30, w2, "SETTLEMENT RULES COMPARED", "#4A6A86")
    sub_w = (w2 - 0.40) / 3
    titulos = [("Individual\nself-generation (C1)", C1), ("Collective\nself-generation (C4)", C4),
               ("P2P market", P2P)]
    for k, (tit, col) in enumerate(titulos):
        sx = x2 + 0.10 + k * (sub_w + 0.10)
        caja(ax, sx, y0 + 0.12, sub_w, y1 - y0 - 0.56, (C1_F, C4_PF, P2P_F)[k], col, lw=1.3)
        ax.text(sx + sub_w / 2, y1 - 0.62, tit, ha="center", va="center", fontsize=9.6,
                fontweight="bold", color=col, linespacing=1.15)
        cxs = [sx + sub_w * f for f in (0.22, 0.50, 0.78)]
        ym = y0 + 1.05
        if k == 0:          # cada miembro con la red, por su cuenta
            red(ax, sx + sub_w / 2, ym - 0.22)
            for cx in cxs:
                casita(ax, cx, ym + 0.62, col)
                flecha(ax, (cx, ym + 0.58), (sx + sub_w / 2 + (cx - (sx + sub_w / 2)) * 0.30, ym + 0.24),
                       color=SUAVE, lw=1.0, ls=(0, (3, 2)), estilo="<|-|>", ms=7)
            ax.text(sx + sub_w / 2, y0 + 0.50, "each member\nwith the grid", ha="center",
                    va="center", fontsize=8.6, color=SUAVE, linespacing=1.15)
        elif k == 1:        # fondo común repartido
            for cx in cxs:
                casita(ax, cx, ym + 0.62, col)
                flecha(ax, (cx, ym + 0.60), (cx, ym + 0.27), color=TXT, lw=1.0, ms=7)
            caja(ax, sx + 0.18, ym - 0.06, sub_w - 0.36, 0.33, "#FFFFFF", C4, lw=1.1, ls=(0, (4, 2)))
            ax.text(sx + sub_w / 2, ym + 0.105, "common fund", ha="center", va="center",
                    fontsize=8.6, color=C4, fontweight="bold")
            ax.text(sx + sub_w / 2, y0 + 0.50, "surplus pooled\nand shared", ha="center",
                    va="center", fontsize=8.6, color=SUAVE, linespacing=1.15)
        else:               # mercado P2P con sus dos supuestos
            for cx in cxs:
                casita(ax, cx, ym + 0.62, col)
            flecha(ax, (cxs[0] + 0.12, ym + 0.74), (cxs[1] - 0.12, ym + 0.74), color=col,
                   lw=1.3, estilo="<|-|>", ms=8)
            flecha(ax, (cxs[1] + 0.12, ym + 0.74), (cxs[2] - 0.12, ym + 0.74), color=col,
                   lw=1.3, estilo="<|-|>", ms=8)
            ax.text(sx + sub_w / 2, ym + 0.40, "members trade\neach hour", ha="center",
                    va="center", fontsize=8.6, color=col, linespacing=1.15)
            numero(ax, sx + 0.22, ym - 0.02, 1, P2P)
            ax.text(sx + 0.38, ym - 0.02, "untraded energy\nsettled per member", ha="left",
                    va="center", fontsize=8.5, color=TXT, linespacing=1.1)
            numero(ax, sx + 0.22, ym - 0.40, 2, P2P)
            ax.text(sx + 0.38, ym - 0.40, "trade pays no\nnetwork charges", ha="left",
                    va="center", fontsize=8.5, color=TXT, linespacing=1.1)
            ax.text(sx + sub_w / 2, y0 + 0.36, "not contemplated\nby current regulation",
                    ha="center", va="center", fontsize=8.5, color=P2P, style="italic",
                    linespacing=1.1)

    flecha(ax, (x2 + w2 + 0.06, (y0 + y1) / 2), (x2 + w2 + 0.42, (y0 + y1) / 2),
           color="#9AA9B8", lw=3.2, ms=20)

    # ---------------- bloque 3: la regla propuesta
    x3, w3 = 9.88, 3.18
    caja(ax, x3, y0, w3, y1 - y0, "#FFFFFF", C4, lw=1.6)
    encabezado(ax, x3, y1 - 0.30, w3, "PROPOSED: COLLECTIVE P2P", C4)
    cxs = [x3 + w3 * f for f in (0.22, 0.50, 0.78)]
    yt = y1 - 0.95
    for cx in cxs:
        casita(ax, cx, yt, PCOL)
    for a, b in ((0, 1), (1, 2)):
        flecha(ax, (cxs[a] + 0.12, yt + 0.12), (cxs[b] - 0.12, yt + 0.12), color=PCOL,
               lw=1.3, estilo="<|-|>", ms=8)
    caja(ax, x3 + 0.30, yt - 0.62, w3 - 0.60, 0.36, PCOL_F, PCOL, lw=1.2)
    ax.text(x3 + w3 / 2, yt - 0.44, "charge-free internal trade", ha="center", va="center",
            fontsize=9.2, fontweight="bold", color="#8A5A00")
    flecha(ax, (x3 + w3 / 2, yt - 0.64), (x3 + w3 / 2, yt - 0.98), color=TXT, lw=1.1, ms=8)
    ax.text(x3 + w3 / 2 + 0.08, yt - 0.81, "only the residual", ha="left", va="center",
            fontsize=8.4, color=SUAVE)
    caja(ax, x3 + 0.30, yt - 1.38, w3 - 0.60, 0.38, C4_F, C4, lw=1.2, ls=(0, (4, 2)))
    ax.text(x3 + w3 / 2, yt - 1.19, "common fund, shared", ha="center", va="center",
            fontsize=9.2, fontweight="bold", color=C4)
    ax.text(x3 + w3 / 2, y0 + 0.68, "inside collective self-generation,\nwithout the 10% share rule",
            ha="center", va="center", fontsize=8.8, color=SUAVE, linespacing=1.15)
    caja(ax, x3 + 0.32, y0 + 0.10, w3 - 0.64, 0.32, C4, C4, lw=0, r=0.16, z=3)
    ax.text(x3 + w3 / 2, y0 + 0.26, "Beats C4 in all five cases studied", ha="center",
            va="center", fontsize=9.6, fontweight="bold", color="white", zorder=4)

    # ---------------- franja inferior: el hallazgo y lo que pide a la regulación
    ax.add_patch(Rectangle((0, 0), W, 0.92, fc="#EEF3F7", ec="none", zorder=1))
    ax.text(0.30, 0.70, "KEY FINDING", ha="left", va="center", fontsize=8.6,
            fontweight="bold", color="#4A6A86")
    ax.text(0.30, 0.36, "The market's value comes from how energy\nis settled, not from the price.",
            ha="left", va="center", fontsize=12, fontweight="bold", color=AZUL_T,
            linespacing=1.2)
    ax.plot([6.55, 6.55], [0.14, 0.78], color="#B8C6D3", lw=1.0, zorder=2)
    ax.text(6.85, 0.70, "REGULATION SHOULD DEFINE", ha="left", va="center", fontsize=8.6,
            fontweight="bold", color="#4A6A86")
    numero(ax, 6.97, 0.44, 1, AZUL_T)
    ax.text(7.13, 0.44, "which charges traded energy pays", ha="left", va="center",
            fontsize=10.4, color=TXT)
    numero(ax, 6.97, 0.18, 2, AZUL_T)
    ax.text(7.13, 0.18, "how the energy each member does not trade is settled", ha="left",
            va="center", fontsize=10.4, color=TXT)

    SALIDA.mkdir(parents=True, exist_ok=True)
    png = SALIDA / "graphical_abstract_en.png"
    fig.savefig(png, dpi=DPI, facecolor="white")
    fig.savefig(SALIDA / "graphical_abstract_en.pdf", facecolor="white")
    plt.close(fig)
    from PIL import Image
    # PNG en color sin canal alfa, con los 400 ppp en la cabecera
    Image.open(png).convert("RGB").save(png, dpi=(DPI, DPI))
    im = Image.open(png)
    assert im.mode == "RGB", im.mode
    alto, ancho = im.size[1], im.size[0]
    tam = png.stat().st_size / 1e6
    assert alto >= 531 and ancho >= 1328, (alto, ancho)
    assert tam <= 5.0, tam
    dpi = im.info.get("dpi", (0, 0))[0]
    assert dpi >= 399, dpi
    print(f"ok {png} {ancho}x{alto} px, {dpi:.0f} ppp, {tam:.2f} MB")


if __name__ == "__main__":
    main()
