"""
visualization/paper_figures/thesis_adapted_en.py
Figuras adicionales para el paper IEEE WEEF, en INGLES y con estilo IEEE.

Adapta funciones equivalentes de visualization/plots.py (que estan en
espanol y para la tesis) al contexto del paper (1 mes, 3 escenarios
P2P/C1/C4, comercial homogeneo). Lee directamente de los datos en
memoria proporcionados por scripts/run_paper_iter.py durante --all-figures.

Trazabilidad: Reunion 01/05 Pantoja + Obando, complemento visual.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from visualization.ieee_style import (
    apply_ieee_style, save_ieee, COLORS, COLORS_AGENT,
    WIDTH_SINGLE_IN, WIDTH_DOUBLE_IN,
)


def fig_paper_per_agent_benefit(scenarios_data: dict, agents: list,
                                 out_path: Path) -> Path:
    """Grouped bar chart: net benefit per agent per scenario.

    Visualiza TABLA II del paper (Per-agent net benefit). Sustenta el
    claim "three of five institutions individually prefer P2P".
    """
    apply_ieee_style()
    N = len(agents)
    scenario_keys = list(scenarios_data.keys())  # P2P, C1, C4 (renamed)
    nb_per_agent = {k: scenarios_data[k][1] / 1e3 for k in scenario_keys}

    fig, ax = plt.subplots(figsize=(WIDTH_DOUBLE_IN, 3.0))
    x = np.arange(N)
    n_scen = len(scenario_keys)
    width = 0.78 / n_scen

    def _color_for(key: str) -> str:
        if key.startswith("P2P"):
            return COLORS["P2P"]
        if key.startswith("C1"):
            return COLORS["C1"]
        if key.startswith("C2 (CREG 101"):
            return COLORS["C4"]
        if key.startswith("C4"):
            return COLORS["C4"]
        return "#888888"

    for j, key in enumerate(scenario_keys):
        offset = (j - (n_scen - 1) / 2.0) * width
        short = "P2P" if key.startswith("P2P") else \
                "C1 (CREG 174)" if key.startswith("C1") else \
                "C2 (CREG 101 072)"
        ax.bar(x + offset, nb_per_agent[key], width, label=short,
               color=_color_for(key), alpha=0.92, edgecolor="white",
               linewidth=0.4)

    # Highlight the agent that wins under P2P vs C1
    p2p_arr = nb_per_agent[scenario_keys[0]]
    c1_arr  = nb_per_agent[scenario_keys[1]]
    for n in range(N):
        if p2p_arr[n] > c1_arr[n]:
            ax.text(n, max(p2p_arr[n], c1_arr[n]) * 1.04, "P2P",
                    ha="center", fontsize=7, color=COLORS["P2P"],
                    fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(agents, rotation=10, ha="right")
    ax.set_ylabel("Net benefit (k COP)")
    ax.set_title("Per-agent net benefit by mechanism (August 2025)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20),
              ncol=3, fontsize=7, framealpha=0.9, frameon=False)
    ax.yaxis.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()

    df = pd.DataFrame({"agent": agents,
                       **{k: nb_per_agent[k] for k in scenario_keys}})
    df.to_csv(str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path)))


def fig_paper_market_activity(p2p_results, out_path: Path) -> Path:
    """Heatmap day x hour of P2P market activity (kWh traded).

    Adaptacion en ingles de fig3_mercado_p2p (panel A heatmap).
    Sustenta el claim "P2P market is active in 221 of 744 hours".
    """
    apply_ieee_style()
    T = len(p2p_results)
    kwh = np.array([float(np.sum(r.P_star)) if r.P_star is not None else 0.0
                    for r in p2p_results])
    n_active = int(np.sum(kwh > 1e-4))
    pct_active = 100.0 * n_active / max(T, 1)
    n_days = T // 24
    grid = kwh[: n_days * 24].reshape(n_days, 24)

    fig, ax = plt.subplots(figsize=(WIDTH_DOUBLE_IN, 3.4))
    vmax = max(float(np.percentile(grid, 99)), 1e-6)
    im = ax.pcolormesh(np.arange(25), np.arange(n_days + 1), grid,
                       cmap="viridis", shading="flat", vmin=0, vmax=vmax)
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Day of horizon")
    ax.set_xticks(np.arange(0, 25, 3))
    ax.set_title(f"P2P market activity: {n_active}/{T} hours active "
                 f"({pct_active:.1f}%), total {kwh.sum():.0f} kWh traded")
    ax.invert_yaxis()
    cbar = fig.colorbar(im, ax=ax, label="kWh traded per hour",
                        fraction=0.040, pad=0.03)
    cbar.ax.tick_params(labelsize=8)
    fig.tight_layout()

    pd.DataFrame({"hour": np.arange(T), "kwh_p2p": kwh}).to_csv(
        str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path)))


def fig_paper_hourly_prices(p2p_results, out_path: Path) -> Path:
    """Distribution of P2P clearing prices by hour of day (P10 / median / P90).

    Adaptacion en ingles de fig3 panel B.  Sustenta el claim que en
    horas pico el precio peer-cleared esta sustancialmente sobre el
    spot floor (~234 COP/kWh).
    """
    apply_ieee_style()
    T = len(p2p_results)
    avg_price = np.full(T, np.nan)
    for r in p2p_results:
        if r.pi_star is not None and r.P_star is not None:
            total = float(np.sum(r.P_star))
            if total > 1e-6:
                w = np.sum(r.P_star, axis=0) / total
                avg_price[r.k] = float(np.dot(w, r.pi_star))

    n_days = T // 24
    grid = avg_price[: n_days * 24].reshape(n_days, 24)
    h_day = np.arange(24)
    med = np.nanmedian(grid, axis=0)
    p10 = np.nanpercentile(grid, 10, axis=0)
    p90 = np.nanpercentile(grid, 90, axis=0)

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 3.0))
    ax.fill_between(h_day, p10, p90, color=COLORS["P2P"], alpha=0.22,
                    label="P10--P90 range")
    ax.plot(h_day, med, "o-", color=COLORS["P2P"], linewidth=1.5,
            markersize=4, label="Median")
    ax.axhline(234.0, color="gray", linestyle="--", linewidth=0.8,
               label="Spot floor (234 COP/kWh)")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel(r"$\pi^*$ (COP/kWh)")
    ax.set_xticks(np.arange(0, 24, 3))
    ax.set_title("P2P cleared price by hour of day")
    ax.legend(loc="lower center", fontsize=7, framealpha=0.9, frameon=False,
              bbox_to_anchor=(0.5, -0.32), ncol=3)
    fig.tight_layout()

    df = pd.DataFrame({"hour_of_day": h_day, "median_COP_kWh": med,
                       "P10_COP_kWh": p10, "P90_COP_kWh": p90})
    df.to_csv(str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path)))
