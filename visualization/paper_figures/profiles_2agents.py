"""
visualization/paper_figures/profiles_2agents.py
Figura paper IEEE WEEF: perfiles 1 semana real de Hospital (HUDN) + Udenar.

Fuente de datos (post-redesign 2026-05-05): MTE Aug 2025 raw vía
cargar_mte_paper("2025-08-01", "2025-09-01") — los MISMOS datos que el
case study (consistencia inter-figura).

Aug 1 2025 fue viernes. Se elige la semana Mon-Sun Aug 11-17 (no Aug 4-10)
para evitar el feriado de Batalla de Boyaca (jueves 7-Aug 2025, demanda
academica residual de jueves a domingo). Aug 11-17 es la primera semana
del mes sin feriados nacionales (Aug 18 ya es lunes festivo trasladado
por Asuncion 15-Aug).
Esa semana se extrae directamente del horizonte 744h sin sintetizar.

Trazabilidad: Reunion 01/05 con asesores Pantoja + Obando.
Caso de estudio: phi=1.5 (UPME 2030), week Aug 11-17, 2025 (real, hourly).
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from visualization.ieee_style import (
    apply_ieee_style,
    save_ieee,
    COLORS_AGENT,
    set_column_width,
    WIDTH_SINGLE_IN,
)

OUT_DIR = ROOT / "outputs" / "paper"

WEEK_META = "Real week: Monday 2025-08-11 to Sunday 2025-08-17 (MTE 744h, phi=1.5)"


def _load_real_week() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Carga datos reales Aug 2025 via cargar_mte_paper, extrae Mon-Sun Aug 11-17.

    Returns (D_hudn, G_hudn, D_udenar, G_udenar) cada uno con 168 valores.
    Aplica homogeneizacion CAL-25/A1 + factor phi=1.5 (UPME 2030 case study)
    para consistencia exacta con el resto de figuras del paper.

    Se elige Aug 11-17 (no Aug 4-10) para evitar el feriado de Batalla de
    Boyaca (jueves 7 de agosto), que produce demanda academica residual
    desde el jueves hasta el domingo en el caso de Udenar.
    """
    from scripts.run_paper_iter import (
        cargar_mte_paper, homogeneizar_a_comercial,
    )
    print("[B2] CAL-25/A1: homogeneizando perfiles institucionales...")
    homogeneizar_a_comercial()
    print("[B2] Cargando MTE Aug 2025 (744h)...")
    D, G, idx, agents = cargar_mte_paper("2025-08-01", "2025-09-01")
    # Case study: phi=1.5 PV scaling (UPME 2030)
    G = G * 1.5

    # Aug 1 2025 = Friday. Mon Aug 4 = day 4 (h72), Mon Aug 11 = day 11 (h240).
    # Se elige Aug 11-17 (h240-h407) por estar libre de feriados nacionales:
    # Aug 7 (Batalla de Boyaca, jueves) ya paso; Aug 18 (Asuncion trasladado)
    # cae el lunes siguiente. Mon Aug 11 to Sun Aug 17 = h240 a h407 (168 h).
    week_start = 240
    week_end = week_start + 168

    udenar_i = agents.index("Udenar")
    hudn_i = agents.index("HUDN")
    print(f"[B2] Extrayendo semana Mon Aug 11 - Sun Aug 17 (h{week_start}-h{week_end-1})")
    print(f"        agentes: Udenar idx={udenar_i}, HUDN idx={hudn_i}")
    return (
        D[hudn_i,   week_start:week_end],
        G[hudn_i,   week_start:week_end],
        D[udenar_i, week_start:week_end],
        G[udenar_i, week_start:week_end],
    )


def _xtick_labels() -> tuple[np.ndarray, list[str]]:
    """Ticks al inicio de cada dia con nombre corto Mon..Sun (Aug 11-17)."""
    days = ["Mon\n11", "Tue\n12", "Wed\n13", "Thu\n14", "Fri\n15", "Sat\n16", "Sun\n17"]
    ticks = np.arange(7) * 24
    return ticks, days


def main() -> None:
    apply_ieee_style()

    D_hudn, G_hudn, D_udenar, G_udenar = _load_real_week()

    hours = np.arange(168)
    xticks, xlabels = _xtick_labels()

    color_D = COLORS_AGENT[3]   # violeta
    color_G = COLORS_AGENT[0]   # azul

    # Single-column IEEE: figsize 3.5x4.0, ratio compacto para 2 paneles
    # apilados verticalmente.
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True,
                                     figsize=(WIDTH_SINGLE_IN, 4.0),
                                     gridspec_kw={"hspace": 0.28})

    # Y-axis comun para comparacion directa de magnitudes
    y_max_common = max(float(D_hudn.max()), float(D_udenar.max()),
                       float(G_hudn.max()), float(G_udenar.max())) * 1.20

    # Weekend strips
    for ax in (ax1, ax2):
        ax.axvspan(120, 168, alpha=0.10, color="#7A7A7A", zorder=0)
        ax.axvline(120, color="#7A7A7A", linestyle=":", linewidth=0.6,
                   alpha=0.6, zorder=1)

    # Panel A — Hospital (HUDN)
    ax1.plot(hours, D_hudn, label="Demand", color=color_D, linewidth=1.0,
             zorder=3)
    ax1.plot(hours, G_hudn, label="PV gen.", color=color_G,
             linestyle="--", linewidth=0.9, zorder=3)
    ax1.set_title("(a) HUDN — Hospital (24/7)",
                  fontsize=7.5, fontweight="normal", pad=2)
    ax1.set_ylabel("Power [kW]", fontsize=7)
    ax1.set_ylim(0, y_max_common)
    ax1.legend(loc="upper left", framealpha=0.92, fontsize=5.5, ncol=2,
               handlelength=1.2, handletextpad=0.4, columnspacing=0.8)
    ax1.tick_params(labelsize=6)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))
    ax1.grid(True, alpha=0.25, linestyle=":", zorder=1)

    # Panel B — Udenar
    ax2.plot(hours, D_udenar, label="Demand", color=color_D, linewidth=1.0,
             zorder=3)
    ax2.plot(hours, G_udenar, label="PV gen.", color=color_G,
             linestyle="--", linewidth=0.9, zorder=3)
    ax2.set_title("(b) Udenar — University (weekday)",
                  fontsize=7.5, fontweight="normal", pad=2)
    ax2.set_ylabel("Power [kW]", fontsize=7)
    ax2.set_ylim(0, y_max_common)
    ax2.legend(loc="upper left", framealpha=0.92, fontsize=5.5, ncol=2,
               handlelength=1.2, handletextpad=0.4, columnspacing=0.8)
    ax2.tick_params(labelsize=6)
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))
    ax2.grid(True, alpha=0.25, linestyle=":", zorder=1)

    # "Sat/Sun" header arriba del strip
    for ax in (ax1, ax2):
        ax.text(144, y_max_common * 0.95, "Sa/Su",
                ha="center", va="top",
                fontsize=5.5, color="#666666",
                fontweight="bold", fontstyle="italic")

    ax2.set_xticks(xticks)
    ax2.set_xticklabels(xlabels, fontsize=5.5)
    ax2.set_xlim(0, 167)

    fig.suptitle(
        "One-week demand vs PV generation",
        fontsize=8.5, y=0.99, fontweight="bold",
    )

    fig.subplots_adjust(top=0.93, bottom=0.10, left=0.13, right=0.97,
                         hspace=0.30)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "fig_paper_profiles_2agents"
    save_ieee(fig, str(out), dpi=300, also_pdf=True)

    # CSV sibling
    pd.DataFrame({
        "hour":        hours,
        "D_HUDN_kW":   D_hudn,
        "G_HUDN_kW":   G_hudn,
        "D_Udenar_kW": D_udenar,
        "G_Udenar_kW": G_udenar,
    }).to_csv(str(out) + ".csv", index=False, float_format="%.4f")

    # Metadata en el CSV como comentario al inicio
    csv_path = str(out) + ".csv"
    original = Path(csv_path).read_text(encoding="utf-8")
    header = (f"# {WEEK_META}\n"
              "# Source: cargar_mte_paper('2025-08-01','2025-09-01') h240-h407\n"
              "# Same MTE data as case study; phi=1.5 PV scaling applied\n")
    Path(csv_path).write_text(header + original, encoding="utf-8")

    print(f"[B2] saved {out}.png")
    print(f"[B2] saved {out}.pdf")
    print(f"[B2] saved {out}.csv")


if __name__ == "__main__":
    main()
