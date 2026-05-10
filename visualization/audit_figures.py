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
    Single panel SINGLE-column IEEE (3.5" wide; rendered at
    \\includegraphics[width=0.48\\textwidth] in paper_weef.md).

    Panel: delta_COP por hora-del-dia (suma sobre el horizonte) +
    eje secundario con % de dias activos.

    Fuente de datos: case study del paper — MTE 744 h hourly (agosto 2025),
    phi=1.5, alpha=0. Datos agregados por hora-del-dia desde
    `scripts/run_heterogeneidad_paper.py`.

    Layout (revision 2026-05-09b — single-column fix):
      - figsize=(WIDTH_SINGLE_IN, 2.7) ratio ~1.30:1, optimo IEEE 1-col.
      - Eje X cada 4 h (0,4,8,12,16,20) para no apretar 12 etiquetas.
      - Anotacion top-3 fontsize 6 con offset vertical compacto.
      - Legend de 2 entradas en una linea (sin "Off-peak bars" — auto-evidente).
    """
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D

    df = pd.read_csv(csv_path)
    hours = df["hour"].astype(int)
    has_n_total = "n_total_days" in df.columns

    # Mayor altura (3.4 vs 2.7) para que respiren textos y annotations
    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 3.4))

    SOLAR_LO, SOLAR_HI = 6.5, 17.5

    # ── Panel unico — delta_COP ──────────────────────────────────────────
    ax.axvspan(SOLAR_LO, SOLAR_HI, alpha=0.14, color=COLORS["P2P"],
               zorder=0, label="_nolegend_")
    colors = ["#AAAAAA"] * len(hours)
    for i, h in enumerate(hours):
        if SOLAR_LO < h < SOLAR_HI:
            colors[i] = COLORS["P2P"]
    ax.bar(hours, df["delta_COP"] / 1000, color=colors, width=0.82,
            edgecolor="black", linewidth=0.3, zorder=3)
    ax.axhline(0.0, color="black", linewidth=0.5, zorder=2)

    ax.set_ylabel("Welfare advantage (kCOP)", fontsize=8.5)
    ax.set_xlabel("Hour of day", fontsize=8.5, fontweight="bold")
    ax.set_xticks(range(0, 24, 4))
    ax.tick_params(axis="both", labelsize=7.5)

    # Headroom para que las anotaciones no toquen la leyenda externa
    y_max = float((df["delta_COP"] / 1000).max())
    if y_max > 0:
        ax.set_ylim(top=y_max * 1.25)

    # Anotacion del top-3 horas con mayor delta
    if (df["delta_COP"] > 0).any():
        top_hours = df.nlargest(3, "delta_COP")[["hour", "delta_COP"]]
        for _, row in top_hours.iterrows():
            h_ = int(row["hour"])
            d_ = float(row["delta_COP"]) / 1000
            ax.annotate(f"+{d_:.1f}", xy=(h_, d_), xytext=(0, 2),
                         textcoords="offset points",
                         ha="center", va="bottom", fontsize=7,
                         fontweight="bold", color="#003060",
                         bbox=dict(facecolor="white", edgecolor="none",
                                    boxstyle="round,pad=0.12", alpha=0.85))

    # ── Eje secundario: dias activos / 31 (heterogeneidad real) ───────────
    if "n_active_days" in df.columns and "n_total_days" in df.columns:
        n_total = float(df["n_total_days"].iloc[0])
        active_pct = (df["n_active_days"] / n_total) * 100.0  # %
        active_mask = df["active"].astype(bool)

        ax_r = ax.twinx()
        ax_r.plot(
            hours[active_mask], active_pct[active_mask],
            "D--", color="#cc6600", linewidth=1.0, markersize=4.0,
            markerfacecolor="#cc6600", markeredgecolor="white",
            markeredgewidth=0.4, zorder=5,
        )
        ax_r.set_ylim(0, 105)
        ax_r.set_yticks([0, 50, 100])
        ax_r.set_yticklabels(["0%", "50%", "100%"])
        ax_r.set_ylabel("Days active (%)", fontsize=8, color="#cc6600")
        ax_r.tick_params(axis="y", labelcolor="#cc6600", labelsize=7.5)
        for spine in ("top",):
            ax_r.spines[spine].set_visible(False)
        ax_r.spines["right"].set_color("#cc6600")

    # ── Legend externa horizontal compacta (2 entradas) ───────────────────
    legend_handles = [
        Patch(facecolor=COLORS["P2P"], edgecolor="black", linewidth=0.3,
               label="Solar window (7-17 h)"),
        Line2D([0], [0], marker="D", color="#cc6600", linestyle="--",
                markerfacecolor="#cc6600", markeredgecolor="white",
                markersize=4.0, linewidth=1.0,
                label="Days active % (right axis)"),
    ]
    fig.legend(handles=legend_handles, loc="upper center",
                bbox_to_anchor=(0.5, 0.96), ncol=2, fontsize=7.5,
                frameon=True, framealpha=0.95,
                handletextpad=0.4, columnspacing=1.0)

    # Suptitle compacto
    fig.suptitle("P2P welfare advantage over C2 by hour-of-day",
                 fontsize=9.5, fontweight="bold", color="#222222",
                 y=1.005)

    fig.subplots_adjust(top=0.84, bottom=0.13, left=0.16, right=0.86)

    df.to_csv(str(out_path.parent / (out_path.stem + ".csv")), index=False)

    return Path(save_ieee(fig, str(out_path)))


# ── Figura 2 ──────────────────────────────────────────────────────────────────

_CHACON_DATA = {
    # Case study del paper IEEE WEEF: 744 h hourly (agosto 2025), phi=1.5,
    # alpha=0. IE_p2p y IE_C1 vienen del run via run_phi_sweep_hourly.py;
    # los valores de Chacon vienen de Chacon et al. 2025, Table VII.
    "labels": [
        "P2P this paper\n(RD on MTE, 744 h, $\\varphi$=1.5)",
        "C1 this paper\n(CREG 174, 744 h, $\\varphi$=1.5)",
        "Chacon RD\n(synthetic 6-agent, Table VII)",
        "Centralized planner\n(Chacon PI, Table VII)",
    ],
    "IE": [0.6650, -0.0282, 0.0149, -0.8913],
    # Indices de las dos entradas RD (para conectar con anotacion)
    "rd_indices": (0, 2),  # P2P this paper, Chacon RD
}


def fig_audit_chacon_comparison(out_path: Path) -> Path:
    """
    Horizontal bar chart single-column (3.5" IEEE).
    Compara IE de este paper con Chacon et al. 2025, Tabla VII.

    Diseño visual (A+D, 2026-05-04):
      - Barras pequeñas (|IE| ≤ 0.05) llevan edge color enfático para que
        sean visibles cerca del cero.
      - Lugar del axvspan verde: dos lineas punteadas en ±0.05 (umbral
        near-equitable) que NO tapan las barras pequeñas.
      - Anotaciones de valor con offset adaptativo por magnitud.
    """
    labels = _CHACON_DATA["labels"]
    ie_vals = _CHACON_DATA["IE"]

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 3.8))

    colors = COLORS_AGENT[: len(labels)]
    # Bars con edge color enfático cuando |IE| es chico (sino la barra
    # es practicamente invisible)
    edge_widths = [1.4 if abs(v) <= 0.05 else 0.4 for v in ie_vals]
    bars = ax.barh(labels, ie_vals, color=colors, height=0.55,
                    edgecolor="black", linewidth=edge_widths)

    # Regiones de fondo (tenues) para indicar interpretacion del signo
    ax.axvspan(-1.05, -0.05, alpha=0.10, color="#e07b00", zorder=0,
               label="Seller-favoring zone (IE < $-$0.05)")
    ax.axvspan(0.05, 0.85, alpha=0.10, color="#0070c0", zorder=0,
               label="Buyer-favoring zone (IE > $+$0.05)")
    # Umbral balanced ±0.05 (Chacon's "near-equitable" threshold)
    for thr in (-0.05, 0.05):
        ax.axvline(thr, color="#2a8a2a", linewidth=0.8,
                    linestyle=(0, (3, 2)), alpha=0.7)
    ax.plot([], [], color="#2a8a2a", linewidth=0.8,
             linestyle=(0, (3, 2)),
             label="Balanced threshold ($\\pm$0.05)")
    # Eje cero solido (precio P2P en midpoint del rango admisible)
    ax.axvline(0.0, color="black", linewidth=0.8)

    ax.set_xlabel("Seller-buyer balance index (IE)\n"
                  "IE = ($\\pi_{gs}+\\pi_{gb}-2\\pi^*$) / ($\\pi_{gs}-\\pi_{gb}$)",
                  fontsize=7)
    ax.set_xlim(-1.05, 0.85)
    ax.set_title("Seller-buyer balance index:\n"
                 "this paper vs Chacon et al. (2025, Table~VII)",
                 fontsize=8, fontweight="bold", pad=22)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.40),
              fontsize=6.5, frameon=False, ncol=1)

    # Anotaciones: barras chicas afuera (espacio claro junto al cero),
    # barras grandes DENTRO de la barra (texto blanco bold) en el
    # extremo final cercano al valor.
    for bar, val in zip(bars, ie_vals):
        if abs(val) <= 0.05:
            x_text = 0.07
            ha = "left"
            color_t = "black"
            weight = "bold"
        elif val >= 0:
            # interior de la barra positiva, cerca del extremo derecho
            x_text = val - 0.03
            ha = "right"
            color_t = "white"
            weight = "bold"
        else:
            # interior de la barra negativa, junto al cero
            x_text = -0.03
            ha = "right"
            color_t = "white"
            weight = "bold"
        ax.text(x_text, bar.get_y() + bar.get_height() / 2,
                f"{val:+.4f}", va="center", ha=ha, fontsize=7,
                fontweight=weight, color=color_t)

    # Marcador ▲ en yticklabels para entradas RD (mismo algoritmo, distinta
    # comunidad). Una nota debajo del titulo explica el simbolo.
    rd_p2p, rd_chacon = _CHACON_DATA["rd_indices"]
    yticklabels_new = []
    for i, lab in enumerate(labels):
        prefix = "▲ " if i in (rd_p2p, rd_chacon) else ""
        yticklabels_new.append(prefix + lab)
    ax.set_yticklabels(yticklabels_new)

    # Nota explicativa del simbolo ▲ — DEBAJO del titulo (entre titulo y bars)
    ax.text(
        0.5, 1.005,
        "▲ Same Replicator Dynamics algorithm, different community",
        transform=ax.transAxes, ha="center", va="bottom",
        fontsize=6.8, fontstyle="italic", color="#cc6600",
        fontweight="bold",
    )

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
    On-paper: eje x = theta; eje y = phi; color = IE_p2p (alpha=0).
    Legacy:   eje x = theta; eje y = alpha; color = IE_p2p (off-paper).
    """
    df = pd.read_csv(csv_path)

    # Detect axis: phi-mode si phi tiene mas de un valor unico
    is_phi_mode = ("phi" in df.columns and df["phi"].nunique() > 1)

    if is_phi_mode:
        y_key, y_label = "phi", "$\\varphi$ (PV coverage factor)"
        title = ("$\\theta$-invariance of seller-buyer balance index\n"
                 "across PV coverage ($\\alpha=0$)")
    else:
        y_key, y_label = "alpha", "alpha (DR fraction, off-paper)"
        title = ("Seller-buyer balance index: invariance\n"
                 "over regulatory parameter ranges")

    y_vals = sorted(df[y_key].unique())
    thetas = sorted(df["theta"].unique())

    matrix = np.zeros((len(y_vals), len(thetas)))
    for i, y in enumerate(y_vals):
        for j, t in enumerate(thetas):
            row = df[(df[y_key] == y) & (df["theta"] == t)]
            matrix[i, j] = float(row["IE_p2p"].iloc[0]) if len(row) else np.nan

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 2.8))

    # Escala de color adaptativa: si todos los IE son positivos y cercanos
    # entre si, usar rango TIGHT (max contraste visual entre celdas);
    # si no, simetrico [-0.5, 0.5]
    finite_vals = matrix[np.isfinite(matrix)]
    if finite_vals.size > 0 and finite_vals.min() > 0.0:
        # Tightening: padding +-0.005 en lugar de +-0.05 para amplificar
        # las pequeñas diferencias entre filas
        v_lo = max(0.0, finite_vals.min() - 0.005)
        v_hi = finite_vals.max() + 0.005
    else:
        v_lo, v_hi = -0.5, 0.5

    im = ax.imshow(matrix, aspect="auto", cmap="viridis",
                   vmin=v_lo, vmax=v_hi, origin="lower")
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Seller-buyer balance index (IE)", fontsize=7)
    cbar.ax.tick_params(labelsize=6)

    ax.set_xticks(range(len(thetas)))
    ax.set_xticklabels([f"{t:.2f}" for t in thetas])
    ax.set_yticks(range(len(y_vals)))
    # Marcar el case study (phi=1.5 si está presente) con asterisco en el ytick
    yticklabels = []
    for v in y_vals:
        if is_phi_mode and abs(v - 1.5) < 1e-6:
            yticklabels.append(f"★ {v:.2f}")
        else:
            yticklabels.append(f"{v:.2f}")
    ax.set_yticklabels(yticklabels)
    ax.set_xlabel("$\\theta$ (utility curvature)", fontsize=8)
    ax.set_ylabel(y_label, fontsize=8)
    ax.set_title(title, fontsize=8, fontweight="bold", pad=22)

    # Texto: blanco si fondo es oscuro (mitad inferior del rango), negro si claro
    mid = (v_lo + v_hi) / 2
    for i in range(len(y_vals)):
        for j in range(len(thetas)):
            val = matrix[i, j]
            text_color = "white" if val < mid else "black"
            ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                    fontsize=6, color=text_color,
                    fontweight="bold" if (is_phi_mode and abs(y_vals[i] - 1.5) < 1e-6) else "normal")

    # Resaltar la fila del case study (phi=1.5) con un rectangulo rojo
    if is_phi_mode:
        for i, v in enumerate(y_vals):
            if abs(v - 1.5) < 1e-6:
                from matplotlib.patches import Rectangle
                rect = Rectangle((-0.5, i - 0.5), len(thetas), 1.0,
                                  fill=False, edgecolor="#d62728",
                                  linewidth=1.4, zorder=5)
                ax.add_patch(rect)
                break

    # Anotacion: theta-invariance (las 4 columnas son identicas en cada fila)
    if is_phi_mode and finite_vals.size > 0:
        per_row_spread = matrix.max(axis=1) - matrix.min(axis=1)
        if float(per_row_spread.max()) < 1e-3:
            # Texto subtitulado entre titulo y heatmap
            ax.text(
                0.42, 1.02,
                "$\\theta$-invariant: all 4 columns identical",
                transform=ax.transAxes, ha="center", va="bottom",
                fontsize=7, fontweight="bold", fontstyle="italic",
                color="#d62728",
                zorder=7,
            )

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

    out_dir = Path("outputs") / "paper"
    out_dir.mkdir(parents=True, exist_ok=True)

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

    print("[audit] 3 audit figures generated in outputs/paper/")


if __name__ == "__main__":
    main()
