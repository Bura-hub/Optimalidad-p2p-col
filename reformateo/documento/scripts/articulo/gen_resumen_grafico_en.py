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


def main_r1():
    """Resumen gráfico de la revisión r1 (2026-11-21, comentario 9 del revisor C):
    menos texto y el resultado en cifras. La cascada de E0, de la autogeneración
    colectiva al mercado P2P, con los cargos evitados y el ahorro del
    intercambio, y la regla P2P colectiva. Cifras de
    SALIDAS_SERVIDOR/cifras_articulo_2026-09-30/cifras.csv (e1/L) y la conversión
    a dólares de SALIDAS_SERVIDOR/articulo_r1_2026-11-21/cifras.csv (e1/AR1,
    CANON §14.40). Salida: graphical_abstract_r1.png y .pdf."""
    import csv
    import hashlib

    def cifras(rel, grupo, ruta):
        p = RAIZ / "SALIDAS_SERVIDOR" / rel
        with open(RAIZ / "Documentos" / "canon_2026-09" / "HUELLAS.csv", encoding="utf-8", newline="") as fh:
            h = [f for f in csv.DictReader(fh) if f["grupo"] == grupo and f["ruta"] == ruta]
        assert len(h) == 1 and hashlib.sha256(p.read_bytes()).hexdigest() == h[0]["sha256"], f"huella de {rel}"
        with open(p, encoding="utf-8", newline="") as fh:
            return {f["clave"]: f["valor"] for f in csv.DictReader(fh)}

    L = cifras("cifras_articulo_2026-09-30/cifras.csv", "e1/L", "cifras_articulo_2026-09-30/cifras.csv")
    R = cifras("articulo_r1_2026-11-21/cifras.csv", "e1/AR1", "articulo_r1_2026-11-21/cifras.csv")
    c4, evit, ahorro, p2p = (float(L[k]) for k in ("com__E0__C4", "com__E0__C1_C4", "com__E0__banda", "com__E0__P2P"))
    pcol_c4 = float(L["com__E0__P2Pcom_C4"])
    sin10 = float(L["com__E0__C4sin10"]) - c4
    usd = float(R["usd__com__E0__P2P_C4"])
    assert abs(c4 + evit + ahorro - p2p) < 1e-4, "la cascada de E0 no cierra"
    pct = 100 * evit / (p2p - c4)
    assert round(pct) == 85 and round(usd) == 500 and f"{sin10:.2f}" == "1.66"

    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    # franja de cabecera: el resultado en una línea
    ax.add_patch(Rectangle((0, H - 0.95), W, 0.95, fc=AZUL_T, ec="none", zorder=1))
    ax.text(W / 2, H - 0.475, f"P2P market with two settlement assumptions: +{p2p - c4:.2f} MCOP (USD {usd:.0f}) "
            "over collective self-generation", ha="center", va="center", fontsize=15.5, fontweight="bold",
            color="white")
    # izquierda: la comunidad medida
    for i in range(5):
        edificio(ax, 0.45 + i * 0.52, 2.55, w=0.42, h=0.40)
    ax.text(1.70, 2.05, "5 institutions", ha="center", va="center", fontsize=13, fontweight="bold", color=TXT)
    ax.text(1.70, 1.68, "6,144 metered hours (2025)", ha="center", va="center", fontsize=11.5, color=SUAVE)
    # centro: la cascada de E0 (MCOP)
    x0, y0, alto = 3.9, 1.35, 2.75
    base = c4 - 0.55
    esc = alto / (p2p - base + 0.25)
    yb = lambda v: y0 + (v - base) * esc
    ancho, paso = 0.95, 1.45
    barras = [
        (0, base, c4, "#9A9A9A", f"{c4:.2f}", "Collective\nself-generation"),
        (1, c4, c4 + evit, C1, f"+{evit:.2f}", f"Avoided charges\n({pct:.0f} %)"),
        (2, c4 + evit, p2p, PCOL, f"+{ahorro:.2f}", "Trade"),
        (3, base, p2p, P2P, f"{p2p:.2f}", "P2P market"),
    ]
    for i, lo, hi, col, num, rot in barras:
        ax.add_patch(Rectangle((x0 + i * paso, yb(lo)), ancho, yb(hi) - yb(lo), fc=col, ec="#333333", lw=1.0, zorder=3))
        ax.text(x0 + i * paso + ancho / 2, yb(hi) + 0.10, num, ha="center", va="bottom", fontsize=14,
                fontweight="bold", color=TXT)
        ax.text(x0 + i * paso + ancho / 2, y0 - 0.12, rot, ha="center", va="top", fontsize=11.5, color=TXT,
                linespacing=1.1)
    ax.plot([x0 - 0.15, x0 + 3 * paso + ancho + 0.15], [y0, y0], color="#333333", lw=1.0, zorder=4)
    ax.plot([x0 + ancho, x0 + 3 * paso], [yb(c4), yb(c4)], color="#777777", lw=1.0, ls=(0, (4, 2)), zorder=2)
    ax.text(x0 - 0.22, y0 + alto / 2, "Net benefit (million COP)", ha="center", va="center", rotation=90, fontsize=11,
            color=SUAVE)
    # derecha: la regla propuesta
    xr = 10.35
    caja(ax, xr - 0.15, 1.15, 2.85, 2.95, C4_PF, C4, lw=1.4, r=0.10, z=1)
    ax.text(xr + 1.275, 3.72, "Collective P2P rule", ha="center", va="center", fontsize=13.5, fontweight="bold",
            color=C4)
    ax.text(xr + 1.275, 3.05, f"+{pcol_c4:.2f} MCOP", ha="center", va="center", fontsize=19, fontweight="bold",
            color=TXT)
    # Ronda 2 de la revisión (exactitud, N3): la cifra es un solo orden de la
    # atribución, quitar la regla primero y sin intercambio, y así se rotula.
    ax.text(xr + 1.275, 2.35, f"{sin10:.2f} of them from dropping\nthe 10 % share rule,\nwith no trading",
            ha="center", va="center",
            fontsize=11.5, color=TXT, linespacing=1.15)
    ax.text(xr + 1.275, 1.55, "over collective self-generation", ha="center", va="center", fontsize=10.5,
            color=SUAVE)
    flecha(ax, (x0 + 3 * paso + ancho + 0.35, 2.65), (xr - 0.25, 2.65), color="#8A9BAA", lw=2.2, ms=16)
    # pie: el hallazgo
    ax.add_patch(Rectangle((0, 0), W, 0.62, fc="#EEF3F7", ec="none", zorder=1))
    ax.text(W / 2, 0.31, "The value comes from how energy is settled, not from the price.", ha="center",
            va="center", fontsize=13.5, fontweight="bold", color=AZUL_T)

    SALIDA.mkdir(parents=True, exist_ok=True)
    png = SALIDA / "graphical_abstract_r1.png"
    fig.savefig(png, dpi=DPI, facecolor="white")
    fig.savefig(SALIDA / "graphical_abstract_r1.pdf", facecolor="white")
    palabras = sum(len(t.get_text().split()) for t in ax.texts)
    plt.close(fig)
    from PIL import Image
    Image.open(png).convert("RGB").save(png, dpi=(DPI, DPI))
    im = Image.open(png)
    alto_px, ancho_px = im.size[1], im.size[0]
    tam = png.stat().st_size / 1e6
    assert im.mode == "RGB" and alto_px >= 531 and ancho_px >= 1328 and abs(ancho_px / alto_px - 2.5) < 0.01
    assert tam <= 5.0 and im.info.get("dpi", (0, 0))[0] >= 300
    print(f"ok {png} {ancho_px}x{alto_px} px, {im.info['dpi'][0]:.0f} ppp, {tam:.2f} MB, {palabras} palabras")


def main_r2():
    """Resumen gráfico principal de la revisión (ronda 1, 2026-11-21): sin gráfica
    de barras ni eje, como pide la página de envíos de la revista. Una franja
    única representa la ventaja del mercado P2P sobre la autogeneración colectiva
    en la comunidad medida, 2,01 MCOP, partida en proporción en los cargos
    evitados (1,71) y el ahorro del intercambio (0,30). MCOP se define en la
    cabecera. La cascada de `main_r1` queda como alternativa. Cifras de
    SALIDAS_SERVIDOR/cifras_articulo_2026-09-30/cifras.csv (e1/L) y la conversión
    a dólares de SALIDAS_SERVIDOR/articulo_r1_2026-11-21/cifras.csv (e1/AR1,
    CANON §14.40). Salida: graphical_abstract_r2.png y .pdf."""
    import csv
    import hashlib

    def cifras(rel, grupo, ruta):
        p = RAIZ / "SALIDAS_SERVIDOR" / rel
        with open(RAIZ / "Documentos" / "canon_2026-09" / "HUELLAS.csv", encoding="utf-8", newline="") as fh:
            h = [f for f in csv.DictReader(fh) if f["grupo"] == grupo and f["ruta"] == ruta]
        assert len(h) == 1 and hashlib.sha256(p.read_bytes()).hexdigest() == h[0]["sha256"], f"huella de {rel}"
        with open(p, encoding="utf-8", newline="") as fh:
            return {f["clave"]: f["valor"] for f in csv.DictReader(fh)}

    L = cifras("cifras_articulo_2026-09-30/cifras.csv", "e1/L", "cifras_articulo_2026-09-30/cifras.csv")
    R = cifras("articulo_r1_2026-11-21/cifras.csv", "e1/AR1", "articulo_r1_2026-11-21/cifras.csv")
    c4, evit, ahorro, p2p = (float(L[k]) for k in ("com__E0__C4", "com__E0__C1_C4", "com__E0__banda", "com__E0__P2P"))
    pcol_c4 = float(L["com__E0__P2Pcom_C4"])
    sin10 = float(L["com__E0__C4sin10"]) - c4
    usd = float(R["usd__com__E0__P2P_C4"])
    total = p2p - c4
    assert abs(evit + ahorro - total) < 1e-4, "las dos partes no suman la ventaja de E0"
    pct = 100 * evit / total
    assert round(pct) == 85 and round(usd) == 500 and f"{sin10:.2f}" == "1.66" and f"{total:.2f}" == "2.01"

    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    # cabecera: el resultado en una línea, con MCOP definido
    ax.add_patch(Rectangle((0, H - 0.95), W, 0.95, fc=AZUL_T, ec="none", zorder=1))
    ax.text(W / 2, H - 0.475, f"P2P market with two settlement assumptions: +{total:.2f} million Colombian pesos "
            f"(MCOP), USD {usd:.0f}", ha="center", va="center", fontsize=15.5, fontweight="bold", color="white")
    # izquierda: la comunidad medida
    for i in range(5):
        edificio(ax, 0.42 + i * 0.56, 2.72, w=0.46, h=0.42)
    ax.text(1.77, 2.28, "5 institutions", ha="center", va="center", fontsize=14, fontweight="bold", color=TXT)
    ax.text(1.77, 1.90, "6,144 metered hours (2025)", ha="center", va="center", fontsize=12, color=SUAVE)
    # centro: una franja única, partida en proporción
    x0, x1, y0, alto = 3.75, 9.55, 2.25, 0.95
    xm = x0 + (x1 - x0) * evit / total
    ax.text((x0 + x1) / 2, y0 + alto + 0.42, "Advantage over collective self-generation", ha="center", va="center",
            fontsize=14, fontweight="bold", color=TXT)
    ax.add_patch(Rectangle((x0, y0), xm - x0, alto, fc=C1, ec="#333333", lw=1.0, zorder=3))
    ax.add_patch(Rectangle((xm, y0), x1 - xm, alto, fc=PCOL, ec="#333333", lw=1.0, zorder=3))
    ax.text((x0 + xm) / 2, y0 + alto / 2, f"{evit:.2f} MCOP", ha="center", va="center", fontsize=19,
            fontweight="bold", color="white", zorder=4)
    ax.text((xm + x1) / 2, y0 + alto / 2, f"{ahorro:.2f}", ha="center", va="center", fontsize=17, fontweight="bold",
            color=TXT, zorder=4)
    ax.text((x0 + xm) / 2, y0 - 0.33, f"Avoided charges ({pct:.0f} %)", ha="center", va="center", fontsize=13.5,
            color=TXT)
    ax.text((xm + x1) / 2, y0 - 0.33, f"Trade ({100 - pct:.0f} %)", ha="center", va="center", fontsize=13.5,
            color=TXT)
    # derecha: la regla propuesta
    xr = 10.35
    caja(ax, xr - 0.15, 1.30, 2.85, 2.75, C4_PF, C4, lw=1.4, r=0.10, z=1)
    ax.text(xr + 1.275, 3.68, "Collective P2P rule", ha="center", va="center", fontsize=13.5, fontweight="bold",
            color=C4)
    ax.text(xr + 1.275, 3.08, f"+{pcol_c4:.2f} MCOP", ha="center", va="center", fontsize=19, fontweight="bold",
            color=TXT)
    ax.text(xr + 1.275, 2.66, "over collective self-generation", ha="center", va="center", fontsize=11,
            color=SUAVE)
    # Ronda 2 de la revisión (exactitud, N3): la cifra es un solo orden de la
    # atribución, quitar la regla primero y sin intercambio, y así se rotula.
    ax.text(xr + 1.275, 1.90, f"{sin10:.2f} of them from dropping\nthe 10 % share rule,\nwith no trading",
            ha="center", va="center",
            fontsize=12, color=TXT, linespacing=1.15)
    flecha(ax, (x1 + 0.12, y0 + alto / 2), (xr - 0.25, y0 + alto / 2), color="#8A9BAA", lw=2.2, ms=16)
    # pie: el hallazgo
    ax.add_patch(Rectangle((0, 0), W, 0.72, fc="#EEF3F7", ec="none", zorder=1))
    ax.text(W / 2, 0.36, "The value comes from how energy is settled, not from the price.", ha="center",
            va="center", fontsize=14.5, fontweight="bold", color=AZUL_T)

    SALIDA.mkdir(parents=True, exist_ok=True)
    png = SALIDA / "graphical_abstract_r2.png"
    fig.savefig(png, dpi=DPI, facecolor="white")
    fig.savefig(SALIDA / "graphical_abstract_r2.pdf", facecolor="white")
    palabras = sum(len(t.get_text().split()) for t in ax.texts)
    plt.close(fig)
    from PIL import Image
    Image.open(png).convert("RGB").save(png, dpi=(DPI, DPI))
    im = Image.open(png)
    alto_px, ancho_px = im.size[1], im.size[0]
    tam = png.stat().st_size / 1e6
    assert im.mode == "RGB" and alto_px >= 531 and ancho_px >= 1328 and abs(ancho_px / alto_px - 2.5) < 0.01
    assert tam <= 5.0 and im.info.get("dpi", (0, 0))[0] >= 300
    print(f"ok {png} {ancho_px}x{alto_px} px, {im.info['dpi'][0]:.0f} ppp, {tam:.2f} MB, {palabras} palabras")


SALIDA_R4 = RAIZ / "Documentos" / "articulo_latam" / "v2_es" / "revision_r1" / "resumen_grafico" / "v5"


def main_r4():
    """Resumen gráfico híbrido de la revisión r1, versión v3 (2026-11-21,
    comentario C-9; decisiones en revision_r1/resumen_grafico/decisiones_fijas.txt
    y tratamiento de la ronda 1 en ronda1_tratamiento.md). La base es el
    original (modo por defecto): las cuatro partes, sus colores y su título,
    con menos texto, íconos y letra más grandes, y el «Key finding» del pie
    cambiado por una franja única de E0. La franja da P2P − C4 con los dos
    supuestos (2,01 MCOP, USD 500), partida en 1,71 de cargos evitados y 0,30
    de ahorro del intercambio, en la familia naranja del mercado P2P, y dice que
    sin los supuestos el mercado queda por debajo de C4 en los cinco casos.
    Cifras de SALIDAS_SERVIDOR/cifras_articulo_2026-09-30/cifras.csv (e1/L) y de
    SALIDAS_SERVIDOR/articulo_r1_2026-11-21/cifras.csv (e1/AR1, CANON §14.40),
    con su huella, y el mercado sin los supuestos con un solo comercializador
    (art. 10 de la CREG 101 072) de
    SALIDAS_SERVIDOR/articulo_r1_resuelta_2026-11-21/cifras.csv (e1/AR2,
    CANON §14.41, punto 4). Salida en SALIDA_R4 (v5/): graphical_abstract_r4.png,
    .pdf y graphical_abstract_r4_gris.png. La v1 a la v4 (v1/ a v4/) las
    dibujaron versiones anteriores de esta función; la v3 añadió la ronda 2 (la
    comunidad en el rótulo de la franja, MCOP a 11 pt y las diagonales más
    cortas), la v4 cambió la línea de debajo de la cifra por el rango con el
    mercado resuelto y la v5 la cambia por «without them, no gain over C4 with
    one retailer». No usa ni cambia lo que dibujan main, main_r1 y main_r2."""
    import csv
    import hashlib

    def cifras(rel, grupo, ruta):
        p = RAIZ / "SALIDAS_SERVIDOR" / rel
        with open(RAIZ / "Documentos" / "canon_2026-09" / "HUELLAS.csv", encoding="utf-8", newline="") as fh:
            h = [f for f in csv.DictReader(fh) if f["grupo"] == grupo and f["ruta"] == ruta]
        assert len(h) == 1 and hashlib.sha256(p.read_bytes()).hexdigest() == h[0]["sha256"], f"huella de {rel}"
        with open(p, encoding="utf-8", newline="") as fh:
            return {f["clave"]: f["valor"] for f in csv.DictReader(fh)}

    L = cifras("cifras_articulo_2026-09-30/cifras.csv", "e1/L", "cifras_articulo_2026-09-30/cifras.csv")
    R = cifras("articulo_r1_2026-11-21/cifras.csv", "e1/AR1", "articulo_r1_2026-11-21/cifras.csv")
    total = float(L["com__E0__P2P_C4"])
    evit = float(L["com__E0__C1_C4"])
    ahorro = float(L["com__E0__banda"])
    usd = float(R["usd__com__E0__P2P_C4"])
    trm = float(R["trm__media_horizonte"])
    horas = int(float(L["horas_total"]))
    casos = ("E0", "E3", "E4", "I1", "SINU")
    pcom = {c: float(L[f"com__{c}__P2Pcom_C4"]) for c in casos}    # P2P colectivo (la alternativa) − C4
    # mercado sin los supuestos − C4 en E0 con un solo comercializador, A o B
    # (art. 10 de la CREG 101 072; CANON §14.41, punto 4)
    R2 = cifras("articulo_r1_resuelta_2026-11-21/cifras.csv", "e1/AR2", "articulo_r1_resuelta_2026-11-21/cifras.csv")
    un_com = {k: float(R2[f"m10__E0__un_comercializador_{k}"]) for k in ("A", "B")}
    exacto = float(R2["m10__E0__exacto"])
    # compuertas: la franja cierra, las cifras impresas son las del canon
    assert abs(evit + ahorro - total) < 1e-4, "las dos partes no suman la ventaja de E0"
    assert abs(float(L["com__E0__P2P"]) - float(L["com__E0__C4"]) - total) < 1e-9
    assert abs(total * 1e6 / trm - usd) < 1e-6, "USD 500 no sale de la TRM media"
    pct = 100 * evit / total
    assert round(pct) == round(float(L["com__E0__C1C4_share"])) == 85
    assert f"{total:.2f}" == "2.01" and f"{evit:.2f}" == "1.71" and f"{ahorro:.2f}" == "0.30"
    assert round(usd) == 500 and f"{trm:.2f}" == "4019.25" and horas == 6144
    assert all(v > 0 for v in pcom.values()), "el P2P colectivo no supera a C4 en los cinco casos"
    # «no gain over C4 with one retailer»: cero con cualquiera de los dos
    # (A da −7·10⁻¹⁵ MCOP, redondeo de coma flotante) y la igualdad es exacta
    assert all(abs(v) < 1e-9 for v in un_com.values()), un_com
    assert exacto == 1.0, exacto

    VERDE_O = "#00785A"   # verde de C4 oscurecido: texto blanco legible en la insignia
    P2P_CL = "#F19E55"    # naranja claro de la familia del P2P (validador dataviz: pasa)
    MIN_PT = 10.0

    fig = plt.figure(figsize=(W, H), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    rend = fig.canvas.get_renderer()

    def ancho(t):
        """Ancho en pulgadas (unidades del eje) de un texto ya dibujado."""
        return t.get_window_extent(rend).width / fig.dpi

    def torre(cx, y, s=1.0, color="#6E6E6E"):
        pts = [(cx - 0.13 * s, y), (cx - 0.03 * s, y + 0.42 * s), (cx + 0.03 * s, y + 0.42 * s),
               (cx + 0.13 * s, y)]
        ax.add_patch(Polygon(pts, closed=False, fill=False, ec=color, lw=1.5, zorder=4))
        for yy, dx in ((y + 0.30 * s, 0.15 * s), (y + 0.40 * s, 0.11 * s)):
            ax.plot([cx - dx, cx + dx], [yy, yy], color=color, lw=1.5, zorder=4)
        ax.plot([cx - 0.09 * s, cx + 0.06 * s], [y + 0.12 * s, y + 0.24 * s], color=color, lw=0.9, zorder=4)
        ax.plot([cx + 0.09 * s, cx - 0.06 * s], [y + 0.12 * s, y + 0.24 * s], color=color, lw=0.9, zorder=4)

    def casa(cx, y, color, s=0.28):
        ax.add_patch(Rectangle((cx - s / 2, y), s, s * 0.75, fc="#FFFFFF", ec=color, lw=1.8, zorder=4))
        ax.add_patch(Polygon([(cx - s / 2 - 0.035, y + s * 0.75), (cx + s / 2 + 0.035, y + s * 0.75),
                              (cx, y + s * 1.25)], closed=True, fc=PANEL, ec="#3D5A73", lw=1.0, zorder=4))

    def edif(x, y, w=0.50, h=0.44):
        ax.add_patch(Rectangle((x, y), w, h, fc="#FFFFFF", ec="#8C8C8C", lw=1.4, zorder=3))
        for i in range(3):
            for j in range(2):
                ax.add_patch(Rectangle((x + 0.065 + i * 0.135, y + 0.08 + j * 0.17), 0.09, 0.10,
                                       fc="#D9E2EC", ec="none", zorder=4))
        ax.add_patch(Polygon([(x + 0.02, y + h + 0.02), (x + w - 0.02, y + h + 0.02),
                              (x + w - 0.085, y + h + 0.16), (x + 0.085, y + h + 0.16)],
                             closed=True, fc=PANEL, ec="#3D5A73", lw=1.0, zorder=4))
        for k in range(1, 4):
            xa_ = x + 0.02 + k * (w - 0.04) / 4
            xb_ = x + 0.085 + k * (w - 0.17) / 4
            ax.plot([xa_, xb_], [y + h + 0.02, y + h + 0.16], color="#3D5A73", lw=0.6, zorder=5)

    def num(x, y, n, color=AZUL_T, r=0.14, fs=11.5):
        ax.add_patch(Circle((x, y), r, fc=color, ec="none", zorder=6))
        ax.text(x, y - 0.005, str(n), ha="center", va="center", color="white", fontsize=fs,
                fontweight="bold", zorder=7)

    def cabecera(x, y, w, texto, color, h=0.34):
        ax.add_patch(Rectangle((x, y), w, h, fc=color, ec="none", zorder=2))
        ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", color="white",
                fontsize=12.5, fontweight="bold", zorder=3)

    # ---------------- franja del título (la del original, 0,06 in más baja)
    ax.add_patch(Rectangle((0, H - 0.72), W, 0.72, fc=AZUL_T, ec="none", zorder=1))
    ax.text(W / 2, H - 0.215, "Peer-to-Peer Energy Markets for Colombian Energy Communities:",
            ha="center", va="center", color="white", fontsize=15, fontweight="bold")
    ax.text(W / 2, H - 0.505, "Network Charges, Settlement Rules, and a Collective Alternative",
            ha="center", va="center", color="white", fontsize=15, fontweight="bold")

    hp = 1.70                        # alto del pie
    y0, y1 = hp + 0.14, H - 0.82     # zona de los tres bloques
    ym = (y0 + y1) / 2
    hc = 0.34                        # alto de las cabeceras
    # retícula horizontal, la misma arriba y en el pie
    x1, w1 = 0.22, 3.25
    x2, w2 = 3.93, 5.24
    x3, w3 = 9.63, 3.43

    # ---------------- bloque 1: la comunidad medida
    caja(ax, x1, y0, w1, y1 - y0, "#FFFFFF", "#9AA9B8", lw=1.0)
    cabecera(x1, y1 - hc, w1, "MEASURED COMMUNITY", "#4A6A86", hc)
    nombres = ["Udenar", "Unicesmag", "Unimar", "UCC", "HUDN"]
    paso_e, we = 0.655, 0.50
    xe0 = x1 + (w1 - (4 * paso_e + we)) / 2
    yb = 2.86
    yl = yb + 0.44 + 0.16 + 0.26     # línea de la red
    ax.plot([x1 + 0.14, x1 + w1 - 0.12], [yl, yl], color="#6E6E6E", lw=1.8, zorder=2)
    torre(x1 + w1 - 0.30, yl, s=0.80)
    for i, nom in enumerate(nombres):
        xx = xe0 + i * paso_e
        edif(xx, yb, we, 0.44)
        flecha(ax, (xx + we / 2, yb + 0.63), (xx + we / 2, yl - 0.02), color=REJILLA, lw=1.1,
               estilo="<|-|>", ms=7, z=2)
        ax.text(xx + we / 2, yb - 0.17, nom, ha="center", va="center", fontsize=10, color=TXT)
    ax.text(x1 + w1 / 2, 2.34, "Pasto, Colombia", ha="center", va="center", fontsize=13,
            fontweight="bold", color=TXT)
    ax.text(x1 + w1 / 2, 2.05, f"{horas:,} metered hours (Apr–Dec 2025)", ha="center", va="center",
            fontsize=12, color=SUAVE)

    flecha(ax, (x1 + w1 + 0.06, ym), (x1 + w1 + 0.40, ym), color="#9AA9B8", lw=3.4, ms=21)

    # ---------------- bloque 2: los mecanismos comparados
    caja(ax, x2, y0, w2, y1 - y0, "#FFFFFF", "#9AA9B8", lw=1.0)
    cabecera(x2, y1 - hc, w2, "SETTLEMENT RULES COMPARED", "#4A6A86", hc)
    sub_w = (w2 - 0.40) / 3
    sb0, sb1 = y0 + 0.08, y1 - hc - 0.08   # alto de las subcajas
    mecs = [("C1", "Individual\nself-generation", C1, C1_F),
            ("C4", "Collective\nself-generation", C4, C4_PF),
            ("P2P", "Peer-to-peer\nmarket", P2P, P2P_F)]
    yc = 2.92                        # base de las casas
    yt = 2.40                        # base de las torres de C1 y P2P (alineadas)
    for k, (cod, nom, col, fondo) in enumerate(mecs):
        sx = x2 + 0.10 + k * (sub_w + 0.10)
        caja(ax, sx, sb0, sub_w, sb1 - sb0, fondo, col, lw=1.6)
        cxm = sx + sub_w / 2
        ax.text(cxm, sb1 - 0.21, cod, ha="center", va="center", fontsize=17, fontweight="bold",
                color=col)
        ax.text(cxm, sb1 - 0.57, nom, ha="center", va="center", fontsize=11, color=TXT,
                linespacing=1.1)
        cxs = [sx + sub_w * f for f in (0.16, 0.50, 0.84)]
        for cx in cxs:
            casa(cx, yc, col)
        if k in (0, 2):              # cada miembro con la red
            torre(cxm, yt, s=0.85)
            # flechas solo en las diagonales: la vertical central era tan
            # corta que se leía como un reloj de arena (ronda 1, diseño B3);
            # la casa del centro queda unida a la torre por un trazo sin puntas
            for cx in (cxs[0], cxs[2]):
                # ronda 2 (diseño D2): la punta sale 0,05 in más abajo, sin tocar la
                # casa, y llega a la cruceta de la torre para que siga siendo diagonal
                flecha(ax, (cx, yc - 0.08), (cxm + (cx - cxm) * 0.24, yt + 0.27), color=SUAVE, lw=1.6,
                       ls=(0, (3, 2)), estilo="<|-|>", ms=9)
            ax.plot([cxm, cxm], [yc - 0.03, yt + 0.37], color=SUAVE, lw=1.6, ls=(0, (2, 1.5)), zorder=3)
        if k == 1:                   # el excedente va al fondo común
            for cx in cxs:
                flecha(ax, (cx, yc - 0.03), (cx, 2.68), color=TXT, lw=1.2, ms=8)
            caja(ax, sx + 0.14, 2.30, sub_w - 0.28, 0.36, C4_F, C4, lw=1.4, ls=(0, (4, 2)))
            ax.text(cxm, 2.48, "common fund", ha="center", va="center", fontsize=11.5,
                    fontweight="bold", color=TXT)
        if k == 2:                   # el intercambio entre miembros
            for a, b in ((0, 1), (1, 2)):
                flecha(ax, (cxs[a] + 0.15, yc + 0.11), (cxs[b] - 0.15, yc + 0.11), color=col, lw=1.8,
                       estilo="<|-|>", ms=9)
            ax.text(cxm, 2.15, "not in current\nregulation", ha="center", va="center", fontsize=11.5,
                    style="italic", color=TXT, linespacing=1.1)

    flecha(ax, (x2 + w2 + 0.06, ym), (x2 + w2 + 0.40, ym), color="#9AA9B8", lw=3.4, ms=21)

    # ---------------- bloque 3: el P2P colectivo, la alternativa del título
    caja(ax, x3, y0, w3, y1 - y0, "#FFFFFF", C4, lw=1.8)
    cabecera(x3, y1 - hc, w3, "ALTERNATIVE: COLLECTIVE P2P", C4, hc)
    xc3 = x3 + w3 / 2
    cxs = [x3 + w3 * f for f in (0.22, 0.50, 0.78)]
    yh = 3.72
    for cx in cxs:
        casa(cx, yh, PCOL)
    for a, b in ((0, 1), (1, 2)):
        flecha(ax, (cxs[a] + 0.16, yh + 0.11), (cxs[b] - 0.16, yh + 0.11), color=PCOL, lw=1.8,
               estilo="<|-|>", ms=10)
    t1 = ax.text(xc3, 3.45, "charge-free trade", ha="center", va="center", fontsize=12.5,
                 fontweight="bold", color="#8A5A00")
    num(xc3 - ancho(t1) / 2 - 0.24, 3.45, 1)
    flecha(ax, (xc3, 3.31), (xc3, 3.12), color=TXT, lw=1.4, ms=10)
    ax.text(xc3 + 0.10, 3.215, "residual", ha="left", va="center", fontsize=12, color=TXT)
    caja(ax, x3 + 0.30, 2.62, w3 - 0.60, 0.48, C4_F, C4, lw=1.4, ls=(0, (4, 2)))
    ax.text(xc3, 2.965, "common fund", ha="center", va="center", fontsize=12.5, fontweight="bold",
            color=TXT)
    t2 = ax.text(xc3, 2.745, "no 10% share rule", ha="center", va="center", fontsize=12,
                 fontweight="bold", color=TXT)
    num(xc3 - ancho(t2) / 2 - 0.24, 2.86, 2)
    caja(ax, x3 + 0.22, 1.94, w3 - 0.44, 0.58, VERDE_O, VERDE_O, lw=0, r=0.12, z=3)
    ax.text(xc3, 2.335, f"Above C4 in all {len(pcom)} cases studied", ha="center", va="center",
            fontsize=13, fontweight="bold", color="white", zorder=4)
    ax.text(xc3, 2.11, "partly by paying fewer charges", ha="center", va="center",
            fontsize=12, fontweight="semibold", color="white", zorder=4)

    # ---------------- pie: la franja de E0 y lo que la regulación tendría que definir
    ax.add_patch(Rectangle((0, 0), W, hp, fc="#EEF3F7", ec="none", zorder=1))
    xa, xb = x1, x2 + w2             # la franja va bajo los dos primeros paneles
    # ronda 2 (cifras, B-2): el rótulo dice de qué comunidad es la cifra
    tr = ax.text(xa, 1.51, "P2P MARKET OVER C4, MEASURED COMMUNITY, WITH TWO SETTLEMENT ASSUMPTIONS",
                 ha="left", va="center", fontsize=12.5, fontweight="bold", color="#4A6A86")
    assert xa + ancho(tr) <= xb, "el rótulo de la franja no cabe sobre la barra"
    t = ax.text(xa, 1.19, f"+{total:.2f} MCOP", ha="left", va="center", fontsize=20, fontweight="bold",
                color=AZUL_T)
    ax.text(xa + ancho(t) + 0.14, 1.19, f"(USD {usd:.0f})", ha="left", va="center", fontsize=15,
            fontweight="bold", color=AZUL_T)
    ax.text(xa, 0.91, "without them, no gain over C4 with one retailer",
            ha="left", va="center",
            fontsize=12, color=TXT)
    ax.text(xb, 0.91, "MCOP: million Colombian pesos", ha="right", va="center", fontsize=11,
            color=TXT)
    # la franja: una barra segmentada alta, sin ejes; anchos en proporción y
    # fondo entre los dos bloques (skill dataviz, «Segmented bar»)
    ys, hs, hueco = 0.40, 0.36, 0.03
    xm = xa + (xb - xa) * evit / total
    for (u, v, col) in ((xa, xm - hueco / 2, P2P), (xm + hueco / 2, xb, P2P_CL)):
        ax.add_patch(FancyBboxPatch((u, ys), v - u, hs, boxstyle="round,pad=0,rounding_size=0.04",
                                    fc=col, ec="none", zorder=3))
    ax.text(xa + 0.14, ys + hs / 2, f"{evit:.2f}", ha="left", va="center", fontsize=16,
            fontweight="bold", color="white", zorder=4)
    ax.text(xm + hueco / 2 + 0.14, ys + hs / 2, f"{ahorro:.2f}", ha="left", va="center", fontsize=16,
            fontweight="bold", color=TXT, zorder=4)
    ax.text(xa, 0.20, f"Avoided charges {pct:.0f}%", ha="left", va="center", fontsize=12, color=TXT)
    ax.text(xb, 0.20, f"Trade saving {100 - pct:.0f}%", ha="right", va="center", fontsize=12,
            color=TXT)
    # las dos definiciones, en el orden del artículo, bajo el panel de la alternativa
    ax.plot([9.40, 9.40], [0.16, 1.56], color="#B8C6D3", lw=1.2, zorder=2)
    ax.text(x3, 1.51, "REGULATION SHOULD DEFINE", ha="left", va="center", fontsize=12.5,
            fontweight="bold", color="#4A6A86")
    num(x3 + 0.14, 1.07, 1)
    ax.text(x3 + 0.37, 1.07, "charges on traded energy", ha="left", va="center", fontsize=15, color=TXT)
    num(x3 + 0.14, 0.58, 2)
    ax.text(x3 + 0.37, 0.58, "settlement of untraded energy", ha="left", va="center", fontsize=15,
            color=TXT)

    menor = min(t.get_fontsize() for t in ax.texts)
    assert menor >= MIN_PT, menor
    fig.canvas.draw()
    for t in ax.texts:               # ningún texto se sale del lienzo
        bb = t.get_window_extent(rend)
        assert bb.x0 >= 0 and bb.x1 <= W * fig.dpi and bb.y0 >= 0 and bb.y1 <= H * fig.dpi, t.get_text()
    palabras = sum(len(t.get_text().split()) for t in ax.texts)
    titulo = sum(len(t.get_text().split()) for t in ax.texts[:2])

    SALIDA_R4.mkdir(parents=True, exist_ok=True)
    png = SALIDA_R4 / "graphical_abstract_r4.png"
    fig.savefig(png, dpi=DPI, facecolor="white")
    fig.savefig(SALIDA_R4 / "graphical_abstract_r4.pdf", facecolor="white")
    plt.close(fig)
    from PIL import Image
    Image.open(png).convert("RGB").save(png, dpi=(DPI, DPI))
    gris = SALIDA_R4 / "graphical_abstract_r4_gris.png"
    Image.open(png).convert("L").save(gris, dpi=(DPI, DPI))
    im = Image.open(png)
    alto_px, ancho_px = im.size[1], im.size[0]
    tam = png.stat().st_size / 1e6
    assert im.mode == "RGB" and alto_px >= 531 and ancho_px >= 1328 and abs(ancho_px / alto_px - 2.5) < 0.01
    assert tam <= 5.0 and im.info.get("dpi", (0, 0))[0] >= 300
    print(f"ok {png} {ancho_px}x{alto_px} px, {im.info['dpi'][0]:.0f} ppp, {tam:.2f} MB, "
          f"{palabras} palabras ({titulo} del título), letra mínima {menor} pt")


if __name__ == "__main__":
    import sys
    if "--r4" in sys.argv[1:]:
        main_r4()
    elif "--r2" in sys.argv[1:]:
        main_r2()
    elif "--r1" in sys.argv[1:]:
        main_r1()
    else:
        main()
