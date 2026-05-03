"""
visualization/audit_figures.py
Figuras del audit de calibracion para el paper IEEE WEEF.

Trazabilidad: Act 4.2 (paper IEEE WEEF, anexo defensivo).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from visualization.ieee_style import (
    apply_ieee_style,
    save_ieee,
    WIDTH_SINGLE_IN,
    WIDTH_DOUBLE_IN,
    COLORS,
    COLORS_AGENT,
)

# ── helpers ──────────────────────────────────────────────────────────────────

_SOLAR_HOURS = set(range(10, 16))  # 10-15 h inclusive


def _solar_bar_colors(hours: pd.Index) -> list:
    return [COLORS["P2P"] if h in _SOLAR_HOURS else "#AAAAAA" for h in hours]


# ── Figura 1 ──────────────────────────────────────────────────────────────────

def fig_audit_heterogeneidad_horaria(csv_path: Path, out_path: Path) -> Path:
    """
    2 paneles verticales (7" double-column IEEE).
    Panel A: delta_COP por hora. Panel B: GDR por hora.
    """
    df = pd.read_csv(csv_path)
    hours = df["hour"].astype(int)

    fig, axes = plt.subplots(2, 1, figsize=(WIDTH_DOUBLE_IN, 4.5), sharex=True)

    # Panel A — delta_COP
    ax = axes[0]
    colors = _solar_bar_colors(hours)
    ax.bar(hours, df["delta_COP"] / 1000, color=colors, width=0.8)
    ax.set_ylabel("Welfare advantage (kCOP)")
    ax.set_title("(A) Hourly P2P welfare advantage over C4")
    from matplotlib.patches import Patch
    legend_patches = [
        Patch(color=COLORS["P2P"], label="Solar peak (10-15 h)"),
        Patch(color="#AAAAAA", label="Off-peak"),
    ]
    ax.legend(handles=legend_patches, loc="upper left")

    # Panel B — GDR
    ax2 = axes[1]
    ax2.plot(hours, df["GDR"], color=COLORS["P2P"], marker="o", linewidth=1.2)
    ax2.axhline(1.0, color="gray", linestyle="--", linewidth=0.8, label="GDR = 1.0")
    ax2.set_ylabel("GDR")
    ax2.set_xlabel("Hour of day")
    ax2.set_title("(B) Gain-to-default ratio by hour")
    ax2.set_xticks(range(0, 24, 2))
    ax2.legend(loc="lower right")
    ax2.set_ylim(0.85, 1.05)

    fig.tight_layout()

    # sibling CSV (source is already the CSV; copy path reference to out_dir)
    sibling_csv = Path(str(out_path).replace(".png", "").replace(
        str(out_path.parent), str(out_path.parent)
    )
    )
    df.to_csv(str(out_path.parent / (out_path.stem + ".csv")), index=False)

    return Path(save_ieee(fig, str(out_path)))


# ── Figura 2 ──────────────────────────────────────────────────────────────────

_CHACON_DATA = {
    "labels": [
        "P2P this paper\n(6144 h real)",
        "C1 this paper\n(6144 h real)",
        "Chacon RD\n(2025, Table VII)",
        "Chacon PI centralized\n(2025, Table VII)",
    ],
    "IE": [0.3677, -0.0115, 0.0149, -0.8913],
}


def fig_audit_chacon_comparison(out_path: Path) -> Path:
    """
    Horizontal bar chart single-column (3.5" IEEE).
    Compara IE de este paper con Chacon et al. 2025, Tabla VII.
    """
    labels = _CHACON_DATA["labels"]
    ie_vals = _CHACON_DATA["IE"]

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 2.8))

    colors = COLORS_AGENT[: len(labels)]
    bars = ax.barh(labels, ie_vals, color=colors, height=0.55)

    ax.axvline(0.0, color="black", linewidth=0.8)
    ax.axvspan(-0.05, 0.05, alpha=0.12, color="green", label="Near-equitable [-0.05, 0.05]")

    ax.set_xlabel("Index of Equity (IE)")
    ax.set_xlim(-1.05, 0.55)
    ax.set_title("Index of Equity: this paper\nvs Chacon et al. (2025, Table VII)")
    ax.legend(loc="lower right", fontsize=7)

    for bar, val in zip(bars, ie_vals):
        offset = 0.03 if val >= 0 else -0.03
        ha = "left" if val >= 0 else "right"
        ax.text(val + offset, bar.get_y() + bar.get_height() / 2,
                f"{val:+.4f}", va="center", ha=ha, fontsize=7)

    fig.tight_layout()

    # sibling CSV
    pd.DataFrame({"label": labels, "IE": ie_vals}).to_csv(
        str(out_path.parent / (out_path.stem + ".csv")), index=False
    )

    return Path(save_ieee(fig, str(out_path)))


# ── Figura 3 ──────────────────────────────────────────────────────────────────

def fig_audit_calibration_robustness(csv_path: Path, out_path: Path) -> Path:
    """
    Heatmap 4x4 single-column (3.5" IEEE).
    Eje x: theta; eje y: alpha; color: IE_p2p.
    """
    df = pd.read_csv(csv_path)

    alphas = sorted(df["alpha"].unique())
    thetas = sorted(df["theta"].unique())

    matrix = np.zeros((len(alphas), len(thetas)))
    for i, a in enumerate(alphas):
        for j, t in enumerate(thetas):
            row = df[(df["alpha"] == a) & (df["theta"] == t)]
            matrix[i, j] = float(row["IE_p2p"].iloc[0]) if len(row) else np.nan

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 2.8))

    im = ax.imshow(matrix, aspect="auto", cmap="viridis", vmin=-0.5, vmax=0.5,
                   origin="lower")
    plt.colorbar(im, ax=ax, label="IE (P2P)", fraction=0.046, pad=0.04)

    ax.set_xticks(range(len(thetas)))
    ax.set_xticklabels([f"{t:.2f}" for t in thetas])
    ax.set_yticks(range(len(alphas)))
    ax.set_yticklabels([f"{a:.2f}" for a in alphas])
    ax.set_xlabel("theta")
    ax.set_ylabel("alpha")
    ax.set_title("Equity sweep: invariance over\nregulatory parameter ranges")

    for i in range(len(alphas)):
        for j in range(len(thetas)):
            val = matrix[i, j]
            ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                    fontsize=6, color="white" if abs(val) > 0.25 else "black")

    fig.tight_layout()

    df.to_csv(str(out_path.parent / (out_path.stem + ".csv")), index=False)

    return Path(save_ieee(fig, str(out_path)))


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    apply_ieee_style()

    audit_dirs = sorted(Path("outputs").glob("audit_*"))
    if not audit_dirs:
        raise SystemExit("[B5] ERROR: No audit outputs found in outputs/audit_*")

    # Buscar el directorio mas reciente con heterogeneidad_horaria.csv
    het_csv: Path | None = None
    for d in reversed(audit_dirs):
        candidate = d / "heterogeneidad" / "heterogeneidad_horaria.csv"
        if candidate.exists():
            het_csv = candidate
            break
    if het_csv is None:
        raise SystemExit("[B5] ERROR: heterogeneidad_horaria.csv not found in any audit dir")

    # Buscar equidad_sweep.csv
    eq_csv: Path | None = None
    for d in reversed(audit_dirs):
        candidate = d / "equidad" / "equidad_sweep.csv"
        if candidate.exists():
            eq_csv = candidate
            break
    if eq_csv is None:
        raise SystemExit("[B5] ERROR: equidad_sweep.csv not found in any audit dir")

    out_dir = Path("graficas")
    out_dir.mkdir(exist_ok=True)

    p1 = fig_audit_heterogeneidad_horaria(
        het_csv,
        out_dir / "fig_audit_heterogeneidad_horaria",
    )
    p2 = fig_audit_chacon_comparison(out_dir / "fig_audit_chacon_comparison")
    p3 = fig_audit_calibration_robustness(
        eq_csv,
        out_dir / "fig_audit_calibration_robustness",
    )

    for p in (p1, p2, p3):
        size_kb = Path(p).stat().st_size // 1024
        pdf = Path(str(p).replace(".png", ".pdf"))
        size_pdf_kb = pdf.stat().st_size // 1024 if pdf.exists() else 0
        print(f"  {Path(p).name}: PNG {size_kb} kB | PDF {size_pdf_kb} kB")

    print("[B5] 3 audit figures generated in graficas/")


if __name__ == "__main__":
    main()
