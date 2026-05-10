"""
visualization/ieee_style.py
Estilo IEEE WEEF para figuras del paper.

Reemplaza dpi=150 por dpi=300, ajusta fonts a 9-11 pt, expone helpers
de save_ieee y set_column_width.

Trazabilidad: Act 4.2 (paper IEEE WEEF).
"""
import matplotlib.pyplot as plt

WIDTH_SINGLE_IN = 3.5
WIDTH_DOUBLE_IN = 7.0
DEFAULT_DPI = 300

# Paleta replicada de visualization/plots.py:28-31
COLORS = {
    "P2P": "#534AB7",
    "C1":  "#1D9E75",
    "C2":  "#BA7517",
    "C3":  "#D85A30",
    "C4":  "#D4537E",
}
COLORS_AGENT = ["#378ADD", "#1D9E75", "#D85A30", "#7F77DD", "#BA7517", "#D4537E"]


def apply_ieee_style() -> None:
    """Actualiza rcParams a estandar IEEE WEEF."""
    plt.rcParams.update({
        "font.family":       "DejaVu Sans",
        "font.size":         9,
        "axes.titlesize":    11,
        "axes.labelsize":    10,
        "xtick.labelsize":   9,
        "ytick.labelsize":   9,
        "legend.fontsize":   8,
        "figure.titlesize":  12,
        "figure.facecolor":  "white",
        "axes.facecolor":    "white",
        "axes.grid":         True,
        "grid.alpha":        0.3,
        "grid.linewidth":    0.5,
        "lines.linewidth":   1.0,
        "lines.markersize":  4,
        "savefig.dpi":       DEFAULT_DPI,
        "savefig.facecolor": "white",
        "savefig.edgecolor": "none",
        "savefig.bbox":      "tight",
        "pdf.fonttype":      42,  # TrueType for vector PDF
    })


def save_ieee(fig, path: str, dpi: int = DEFAULT_DPI, also_pdf: bool = True) -> str:
    """Guarda PNG 300dpi + PDF vectorial opcional."""
    png_path = path if path.endswith(".png") else path + ".png"
    fig.savefig(png_path, dpi=dpi, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    if also_pdf:
        pdf_path = png_path[:-4] + ".pdf"
        fig.savefig(pdf_path, format="pdf", bbox_inches="tight",
                    facecolor="white", edgecolor="none")
    plt.close(fig)
    return png_path


def set_column_width(fig, mode: str = "single") -> None:
    """mode: 'single' (3.5 in) o 'double' (7.0 in). Mantiene alto."""
    width = WIDTH_SINGLE_IN if mode == "single" else WIDTH_DOUBLE_IN
    _, h = fig.get_size_inches()
    fig.set_size_inches(width, h)
