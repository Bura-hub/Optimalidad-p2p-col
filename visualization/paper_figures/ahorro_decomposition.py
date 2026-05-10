"""
visualization/paper_figures/ahorro_decomposition.py
Figura paper IEEE WEEF: descomposicion bienestar agregado — ahorro comun
de autoconsumo (offset identico para todos) + revenue por venta de
excedentes (diferenciador entre escenarios P2P, C1, C4).

Fuente primaria: el xlsx mas reciente bajo outputs/paper/resultados_paper_*.xlsx
(case study activo). Si quieres apuntar a un tag concreto, exporta la
variable de entorno PAPER_XLSX_TAG (por ejemplo "cal29_phi15" o
"cal29_canonical").

Fallback: graficas/fig13_desglose_flujos.csv

Trazabilidad: Decision asesores Pantoja + Obando, Reunion 01/05
Act 4.2 (paper IEEE WEEF).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from visualization.ieee_style import (
    apply_ieee_style, save_ieee, COLORS,
    WIDTH_SINGLE_IN,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PAPER_DIR = REPO_ROOT / "outputs" / "paper"


def _resolve_xlsx_path() -> Path:
    """Devuelve el xlsx del case study activo.

    Si PAPER_XLSX_TAG esta definida, usa
    `resultados_paper_<tag>.xlsx`. Si no, prefiere `cal29_phi15` (el case
    study actual) y, como fallback, el `cal29_canonical` historico.
    """
    tag = os.environ.get("PAPER_XLSX_TAG")
    if tag:
        return PAPER_DIR / f"resultados_paper_{tag}.xlsx"
    preferred = PAPER_DIR / "resultados_paper_cal29_phi15.xlsx"
    if preferred.exists():
        return preferred
    return PAPER_DIR / "resultados_paper_cal29_canonical.xlsx"


XLSX_PATH = _resolve_xlsx_path()
CSV_PATH  = REPO_ROOT / "graficas" / "fig13_desglose_flujos.csv"

# Escenarios de interes (sin C2/C3 segun decision reunion).
# Orden por performance: P2P (best), C4 (mid), C1 (worst).
SCENARIOS = ["P2P", "C4", "C1"]

# Etiquetas eje X (renombrado del paper: C4 -> C2)
X_LABELS = {
    "P2P": "P2P\n(Stackelberg+RD)",
    "C1":  "C1\n(CREG 174)",
    "C4":  "C2\n(CREG 101 072)",
}


def _load_from_xlsx() -> pd.DataFrame:
    """
    Lee Ahorro_autoconsumo_COP y Venta_excedentes_COP del xlsx canonico.
    El paper-mode exporta C4 con la etiqueta 'C2 (CREG 101 072)'.
    Retorna DataFrame con columnas [scenario, autoconsumption, revenue].
    """
    df = pd.read_excel(XLSX_PATH, sheet_name="Resumen", engine="openpyxl")
    required = {"Ahorro_autoconsumo_COP", "Venta_excedentes_COP"}
    if not required.issubset(df.columns):
        raise KeyError(f"Columnas faltantes en xlsx: {required - set(df.columns)}")

    # Mapear etiquetas del paper a claves internas
    label_map = {
        "P2P (Stackelberg + RD)": "P2P",
        "C1 (CREG 174)":          "C1",
        "C2 (CREG 101 072)":      "C4",   # en paper-mode C4 se exporta como C2
    }
    records = []
    for _, row in df.iterrows():
        key = label_map.get(str(row["Escenario"]).strip())
        if key in SCENARIOS:
            records.append({
                "scenario":       key,
                "autoconsumption": float(row["Ahorro_autoconsumo_COP"]),
                "revenue":         float(row["Venta_excedentes_COP"]),
            })
    result = pd.DataFrame(records)
    if len(result) < len(SCENARIOS):
        raise ValueError(
            f"Solo se encontraron {len(result)}/{len(SCENARIOS)} escenarios en xlsx"
        )
    return result


def _load_from_csv() -> pd.DataFrame:
    """
    Fallback: lee fig13_desglose_flujos.csv.
    Autoconsumo = absoluto_Autoconsumo.
    Revenue = suma de las demas columnas absolutas (varia por escenario).
    """
    df = pd.read_csv(CSV_PATH)
    records = []
    esc_map = {"P2P": "P2P", "C1": "C1", "C4": "C4"}
    for _, row in df.iterrows():
        key = esc_map.get(str(row["escenario"]).strip())
        if key is None:
            continue
        auto = float(row.get("absoluto_Autoconsumo", 0))
        # Revenue = todo excepto Autoconsumo
        revenue_cols = [c for c in df.columns
                        if c.startswith("absoluto_") and "Autoconsumo" not in c]
        rev = float(sum(row[c] for c in revenue_cols
                        if pd.notna(row[c]) and float(row[c]) > 0))
        records.append({"scenario": key, "autoconsumption": auto, "revenue": rev})
    return pd.DataFrame(records)


def _load_data() -> tuple[float, dict[str, float], str]:
    """
    Retorna (common_autoconsumption_COP, {scenario: revenue_COP}, source_label).
    Si los valores de autoconsumo difieren entre escenarios, usa el promedio.
    """
    source = "xlsx"
    try:
        df = _load_from_xlsx()
    except Exception as exc:
        print(f"[B3] xlsx no disponible ({exc}), usando fig13_desglose_flujos.csv")
        df = _load_from_csv()
        source = "fig13_desglose_flujos.csv"

    auto_vals = df.set_index("scenario")["autoconsumption"]
    dispersion = float(auto_vals.std())
    common_auto = float(auto_vals.mean())
    if dispersion > 1.0:
        print(f"[B3] Dispersion en autoconsumo: std={dispersion:.2f} COP "
              f"(se usa promedio={common_auto:.2f})")
    else:
        print(f"[B3] Autoconsumo identico entre escenarios: {common_auto:.2f} COP "
              f"(dispersion={dispersion:.4f} COP)")

    revenue = {row["scenario"]: float(row["revenue"])
               for _, row in df.iterrows()}
    return common_auto, revenue, source, dispersion


def build_figure(
    common_auto: float,
    revenue: dict[str, float],
    source_label: str,
) -> plt.Figure:
    """Construye la figura de barras apiladas con UN SOLO panel.

    Layout (revision 2026-05-04, post broken-axis):
      - Panel unico, eje y continuo de 0 a ~6.1 M COP.
      - Barras: gris (baseline) + color (revenue) apiladas en orden P2P,
        C2, C1 (mejor a peor).
      - Linea horizontal punteada naranja al tope del baseline (4.125 M)
        cruzando los 3 bars — marca visual del separador.
      - Tick especial en el eje y a 4.125 M en color naranja bold +
        etiqueta "(baseline)" — sustituye el tick generico de 4.0 M.
      - Anotaciones: Total encima, revenue dentro de la barra coloreada,
        Δ vs C1 dentro de la barra al borde inferior.
      - Caja "Identical baseline" en zona gris (debajo de la linea de
        separacion).
    """
    apply_ieee_style()

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 3.2))

    x = np.arange(len(SCENARIOS))
    base_color = "#cccccc"
    rev_vals = [revenue[s] for s in SCENARIOS]
    bar_colors = [COLORS[s] for s in SCENARIOS]

    # ── Stack bars (baseline + revenue) ─────────────────────────────────
    ax.bar(
        x, [common_auto] * len(SCENARIOS),
        color=base_color, edgecolor="black", linewidth=0.4, zorder=3,
    )
    ax.bar(
        x, rev_vals, bottom=[common_auto] * len(SCENARIOS),
        color=bar_colors, edgecolor="black", linewidth=0.4, zorder=3,
    )

    # ── Escala custom: [0, baseline] comprimida, [baseline, ymax] expandida.
    # Bottom 30% del eje visual muestra [0, 4.125 M]; top 70% muestra el
    # rango de revenue [4.125 M, ymax]. Asi el baseline aparece "pequeño"
    # pero los numeros son reales y continuos (sin broken-axis).
    y_max = common_auto + max(rev_vals) + 0.30e6
    SPLIT = 0.30  # fraccion de altura visual dedicada al baseline

    def _forward(y):
        y = np.asarray(y, dtype=float)
        out = np.empty_like(y)
        mask = y <= common_auto
        out[mask] = SPLIT * (y[mask] / common_auto)
        out[~mask] = SPLIT + (1.0 - SPLIT) * (
            (y[~mask] - common_auto) / (y_max - common_auto)
        )
        return out

    def _inverse(s):
        s = np.asarray(s, dtype=float)
        out = np.empty_like(s)
        mask = s <= SPLIT
        out[mask] = common_auto * (s[mask] / SPLIT)
        out[~mask] = common_auto + (s[~mask] - SPLIT) / (1.0 - SPLIT) * (
            y_max - common_auto
        )
        return out

    ax.set_yscale("function", functions=(_forward, _inverse))
    ax.set_ylim(0, y_max)

    # ── Linea horizontal punteada al tope del baseline ──────────────────
    BASELINE_COLOR = "#cc6600"
    ax.axhline(
        common_auto, color=BASELINE_COLOR, linestyle="--",
        linewidth=1.2, alpha=0.85, zorder=4,
    )

    # Custom yticks: el baseline en naranja, los demas en orden natural.
    yticks = [0.0, 1e6, 2e6, 3e6, common_auto, 5e6, 6e6]
    ax.set_yticks(yticks)
    yticklabels = []
    for y in yticks:
        if abs(y - common_auto) < 1:
            yticklabels.append(f"{y / 1e6:.3f} M\n(baseline)")
        else:
            yticklabels.append(f"{y / 1e6:.1f} M")
    ax.set_yticklabels(yticklabels)

    for tick_lbl, y in zip(ax.get_yticklabels(), yticks):
        if abs(y - common_auto) < 1:
            tick_lbl.set_color(BASELINE_COLOR)
            tick_lbl.set_fontweight("bold")
            tick_lbl.set_fontsize(6.0)

    ax.yaxis.grid(True, alpha=0.35, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)

    # ── Anotaciones: Total + Revenue + Δ vs C1 ──────────────────────────
    rev_c1 = float(revenue["C1"])
    for i, s in enumerate(SCENARIOS):
        total = common_auto + revenue[s]
        rev_s = revenue[s]
        # Total (encima de la barra, bold negro)
        ax.text(
            i, total + 0.04e6,
            f"{total / 1e6:.2f}M",
            ha="center", va="bottom",
            fontsize=6, fontweight="bold", color="black",
        )
        # Revenue dentro de la barra coloreada (centro, blanco bold)
        rev_mid = common_auto + rev_s / 2
        ax.text(
            i, rev_mid,
            f"{rev_s / 1e6:.3f}M",
            ha="center", va="center",
            fontsize=6, fontweight="bold", color="white",
        )
        # Delta vs C1 — compacto, sin caja (mas espacio)
        delta_y = common_auto + 0.12e6
        if s != "C1":
            delta = rev_s - rev_c1
            delta_pct = (delta / rev_c1) * 100
            ax.text(
                i, delta_y,
                f"$\\Delta$+{delta / 1e6:.3f}M\n(+{delta_pct:.1f}%)",
                ha="center", va="bottom",
                fontsize=5.5, fontweight="bold",
                color="#003060",
                bbox=dict(facecolor="white", edgecolor="#003060",
                           boxstyle="round,pad=0.12", linewidth=0.4,
                           alpha=0.95),
            )

    # ── Etiquetas eje x y ──────────────────────────────────────────────
    ax.set_xticks(x)
    ax.set_xticklabels([X_LABELS[s] for s in SCENARIOS],
                        fontsize=6.5, ha="center")
    ax.set_ylabel("Welfare [COP]", fontsize=7.5)
    ax.tick_params(axis="y", labelsize=6.0)

    # ── Suptitle compacto (case study tag movido al caption del paper) ─
    fig.suptitle(
        "Welfare decomposition",
        fontsize=8.5, fontweight="bold", color="#222222", y=0.99,
    )

    # ── Leyenda al pie compacta ────────────────────────────────────────
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_handles = [
        Patch(facecolor=base_color, edgecolor="black", linewidth=0.4,
               label="Baseline (autoconsumption)"),
        Patch(facecolor=COLORS["P2P"], edgecolor="black", linewidth=0.4,
               label="Surplus revenue"),
        Line2D([0], [0], color=BASELINE_COLOR, linestyle="--",
                linewidth=1.0,
                label=f"Baseline {common_auto / 1e6:.2f}M"),
    ]
    fig.legend(handles=legend_handles, loc="lower center",
                bbox_to_anchor=(0.5, 0.005), ncol=3, fontsize=5.5,
                frameon=False, columnspacing=1.2, handletextpad=0.4)

    # Ajuste explicito de margenes
    fig.subplots_adjust(
        top=0.90, bottom=0.16, left=0.18, right=0.97,
    )
    return fig


def main() -> None:
    common_auto, revenue, source_label, dispersion = _load_data()

    print(f"[B3] Fuente de datos: {source_label}")
    print(f"[B3] Autoconsumption comun: {common_auto:,.2f} COP "
          f"(dispersion std={dispersion:.4f} COP)")
    for s in SCENARIOS:
        print(f"[B3]   Revenue {s}: {revenue[s]:,.2f} COP")
        print(f"[B3]   Total   {s}: {common_auto + revenue[s]:,.2f} COP")

    fig = build_figure(common_auto, revenue, source_label)

    out = REPO_ROOT / "outputs" / "paper" / "fig_paper_ahorro_decomposition"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_ieee(fig, str(out), dpi=300, also_pdf=True)

    # CSV sibling
    pd.DataFrame({
        "scenario":              SCENARIOS,
        "autoconsumption_COP":   [common_auto] * len(SCENARIOS),
        "revenue_surplus_COP":   [revenue[s] for s in SCENARIOS],
        "total_welfare_COP":     [common_auto + revenue[s] for s in SCENARIOS],
        "source":                [source_label] * len(SCENARIOS),
    }).to_csv(str(out) + ".csv", index=False)

    png_size = (out.with_suffix(".png")).stat().st_size // 1024
    print(f"[B3] Saved {out}.png  ({png_size} kB) / .pdf / .csv")


if __name__ == "__main__":
    main()
