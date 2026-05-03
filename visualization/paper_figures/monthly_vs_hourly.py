"""
visualization/paper_figures/monthly_vs_hourly.py
Figura paper IEEE WEEF: schematic conceptual liquidacion mensual vs horaria.

Trazabilidad: Reunion 01/05 con asesores Pantoja + Obando.
Act 4.2 (paper IEEE WEEF).
"""
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from visualization.ieee_style import apply_ieee_style, save_ieee, COLORS, set_column_width

AVG_BOLSA = 234          # COP/kWh — precio promedio bolsa mes referencia
TOTAL_SURPLUS_KWH = 100  # kWh acumulado al final del mes (Panel A)


def _build_panel_a(ax: plt.Axes) -> None:
    """Panel A: liquidacion mensual — surplus acumulado y liquidacion al cierre."""
    days = np.arange(1, 31)
    cumulative = days * (TOTAL_SURPLUS_KWH / 30)

    ax.fill_between(days, 0, cumulative,
                    color=COLORS["C1"], alpha=0.25,
                    label="Accumulated surplus")
    ax.plot(days, cumulative, color=COLORS["C1"], linewidth=1.5)

    # Barra de liquidacion mensual al dia 30
    ax.bar(30, TOTAL_SURPLUS_KWH, width=1.6,
           color=COLORS["C1"], alpha=0.9,
           label=f"Monthly liquidation\n({TOTAL_SURPLUS_KWH} kWh × {AVG_BOLSA} COP/kWh)")

    # Linea de precio promedio (escala secundaria ficticia — se muestra como referencia)
    ax.axhline(y=TOTAL_SURPLUS_KWH, color="gray", linestyle="--",
               linewidth=0.9, label=f"End-of-month total = {TOTAL_SURPLUS_KWH} kWh")

    ax.annotate(f"avg(π_bolsa)\n≈{AVG_BOLSA} COP/kWh",
                xy=(30, TOTAL_SURPLUS_KWH), xytext=(18, 88),
                fontsize=7,
                arrowprops=dict(arrowstyle="->", color="gray", lw=0.8),
                color="gray")

    ax.set_xlim(0.5, 31)
    ax.set_ylim(0, 115)
    ax.set_xlabel("Day of month")
    ax.set_ylabel("Cumulative surplus [kWh]")
    ax.set_title("Regulated (C1, C4): monthly settlement", fontsize=10)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(5))
    ax.legend(loc="upper left", fontsize=7, framealpha=0.8)


def _build_panel_b(ax: plt.Axes) -> None:
    """Panel B: liquidacion horaria P2P — precios peer-cleared hora a hora."""
    hours = np.arange(24)
    pi_h = np.array([
        180, 175, 175, 180, 200, 250, 350, 450,
        500, 530, 540, 530, 510, 500, 460, 400,
        340, 300, 280, 260, 240, 220, 210, 200,
    ], dtype=float)
    avg_pi = pi_h.mean()  # ~316 COP/kWh

    bars = ax.bar(hours, pi_h, color=COLORS["P2P"], alpha=0.85,
                  label=r"$\pi^*_i(k)$ peer-cleared price")

    # Resaltar pico solar (h 10-14)
    for h in range(10, 15):
        bars[h].set_alpha(1.0)
        bars[h].set_edgecolor("white")
        bars[h].set_linewidth(0.5)

    ax.axhline(y=AVG_BOLSA, color="gray", linestyle="--", linewidth=0.9,
               label=f"Spot floor ≈{AVG_BOLSA} COP/kWh")
    ax.axhline(y=avg_pi, color=COLORS["P2P"], linestyle=":",
               linewidth=1.0, alpha=0.8,
               label=f"Daily avg ≈{avg_pi:.0f} COP/kWh")

    ax.annotate(f"Solar peak\n(h 10-14)",
                xy=(12, 540), xytext=(15, 520),
                fontsize=7,
                arrowprops=dict(arrowstyle="->", color="dimgray", lw=0.8),
                color="dimgray")

    ax.set_xlim(-0.7, 23.7)
    ax.set_ylim(0, 610)
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Price [COP/kWh]")
    ax.set_title("P2P: hourly settlement", fontsize=10)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(4))
    ax.legend(loc="upper right", fontsize=7, framealpha=0.8)


def main() -> None:
    apply_ieee_style()

    fig, (axA, axB) = plt.subplots(1, 2)
    set_column_width(fig, "double")
    fig.set_size_inches(7.0, 3.2)

    _build_panel_a(axA)
    _build_panel_b(axB)

    fig.suptitle(
        "Settlement granularity: regulated (monthly) vs P2P (hourly)",
        y=1.03, fontsize=11,
    )
    fig.tight_layout()

    out = Path("C:/Users/burav/Documentos/MaIE - UDENAR/Proyectos/SistemaBL/outputs/paper/fig_paper_monthly_vs_hourly")
    save_ieee(fig, str(out), dpi=300, also_pdf=True)
    print(f"[B4] saved {out}.png")
    print(f"[B4] saved {out}.pdf")


if __name__ == "__main__":
    main()
