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

from visualization.ieee_style import apply_ieee_style, save_ieee, COLORS

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

# Escenarios de interes (sin C2/C3 segun decision reunion)
SCENARIOS = ["P2P", "C1", "C4"]

# Etiquetas eje X
X_LABELS = {
    "P2P": "P2P\n(Stackelberg+RD)",
    "C1":  "C1\n(CREG 174)",
    "C4":  "C4\n(CREG 101 072)",
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
    """Construye la figura de barras apiladas."""
    apply_ieee_style()

    fig, ax = plt.subplots(figsize=(3.5, 3.5))

    x = np.arange(len(SCENARIOS))
    base_color = "#cccccc"

    # Stack inferior — autoconsumo comun (identico para los 3)
    auto_bars = ax.bar(
        x, [common_auto] * len(SCENARIOS),
        color=base_color,
        label="Common autoconsumption savings",
        zorder=3,
    )

    # Stack superior — revenue diferenciador
    rev_vals = [revenue[s] for s in SCENARIOS]
    rev_bars = ax.bar(
        x, rev_vals,
        bottom=[common_auto] * len(SCENARIOS),
        color=[COLORS[s] for s in SCENARIOS],
        label="Revenue from surplus sales",
        zorder=3,
    )

    # Anotacion del offset comun (centrada en el stack inferior)
    mid_auto = common_auto / 2
    ax.text(
        len(SCENARIOS) - 0.5, mid_auto,
        "common baseline\n(offset)",
        ha="right", va="center",
        fontsize=7, color="#555555",
        style="italic",
    )

    # Anotaciones sobre cada stack superior (valor revenue exacto)
    max_total = common_auto + max(rev_vals)
    for i, s in enumerate(SCENARIOS):
        total = common_auto + revenue[s]
        ax.text(
            i, total + 0.015 * max_total,
            f"{revenue[s] / 1e6:.3f} M",
            ha="center", va="bottom",
            fontsize=7.5, fontweight="bold",
            color=COLORS[s],
        )

    # Ejes
    ax.set_xticks(x)
    ax.set_xticklabels([X_LABELS[s] for s in SCENARIOS], fontsize=8)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v / 1e6:.1f} M")
    )
    ax.set_ylabel("Welfare [COP]", fontsize=9)
    ax.set_title(
        "Welfare decomposition\n(common offset + scenario-specific revenue)",
        fontsize=9,
    )

    # Leyenda DEBAJO del eje x para no tapar las etiquetas de totales
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18),
              ncol=2, fontsize=7, framealpha=0.9, frameon=False)

    # Grilla horizontal solo
    ax.yaxis.grid(True, alpha=0.35, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)

    fig.tight_layout(pad=0.8)
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
