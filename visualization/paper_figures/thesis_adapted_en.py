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


# ── Fig paper: hourly KPIs (SC / SS / IE) ────────────────────────────────────

def fig_paper_metrics_hourly(p2p_results, D, G_klim, out_path: Path) -> Path:
    """Hourly community KPIs (SC, SS, IE) over 744-hour horizon.

    Adapts fig4 from visualization/plots.py to English + IEEE single-col.
    Rolling-mean 24 h smoothing overlaid as thicker line.
    Trazabilidad: Reunion 01/05 — paper IEEE WEEF.
    """
    apply_ieee_style()
    hours = np.array([r.k for r in p2p_results])
    SC = np.array([r.SC for r in p2p_results])
    SS = np.array([r.SS for r in p2p_results])
    IE = np.array([r.IE for r in p2p_results])

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 3.2))
    _win = 24

    def _add_series(data, color, label):
        ax.plot(hours, data, color=color, alpha=0.30, linewidth=0.6)
        smooth = pd.Series(data).rolling(_win, center=True, min_periods=1).mean().values
        ax.plot(hours, smooth, color=color, linewidth=1.6, label=label)

    _add_series(SC, COLORS["P2P"], "SC")
    _add_series(SS, COLORS["C1"],  "SS")
    _add_series(IE, COLORS["C4"],  "IE")

    ax.axhline(0.0, color="black", linewidth=0.5, linestyle="--")
    ax.set_ylim(-1.05, 1.05)
    ax.set_xlabel("Hour of horizon")
    ax.set_ylabel("Index (p.u.)")
    ax.set_title("Hourly community KPIs (August 2025)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18),
              ncol=3, fontsize=7, frameon=False)
    fig.tight_layout()

    pd.DataFrame({"hour": hours, "SC": SC, "SS": SS, "IE": IE}).to_csv(
        str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path), also_pdf=True))


# ── Fig paper: per-agent role classification heatmap ─────────────────────────

def fig_paper_classification(p2p_results, agents: list, out_path: Path) -> Path:
    """Per-agent role heatmap: seller / buyer / neutral by hour.

    Adapts fig2 from visualization/plots.py to English + IEEE double-col.
    Uses pcolormesh for clean raster rendering at 300 dpi.
    Trazabilidad: Reunion 01/05 — paper IEEE WEEF.
    """
    import matplotlib.patches as mpatches
    apply_ieee_style()
    T = len(p2p_results)
    N = len(agents)
    roles = np.zeros((N, T), dtype=float)
    for r in p2p_results:
        for j in r.seller_ids:
            if 0 <= j < N:
                roles[j, r.k] = 1.0
        for i in r.buyer_ids:
            if 0 <= i < N:
                roles[i, r.k] = -1.0

    import matplotlib.colors as mcolors
    cmap = mcolors.ListedColormap(["#378ADD", "#E8E8E8", COLORS["C1"]])
    norm = mcolors.BoundaryNorm([-1.5, -0.5, 0.5, 1.5], cmap.N)

    fig, ax = plt.subplots(figsize=(WIDTH_DOUBLE_IN, 2.2))
    ax.pcolormesh(np.arange(T + 1), np.arange(N + 1), roles,
                  cmap=cmap, norm=norm, shading="flat")

    ax.set_yticks(np.arange(N) + 0.5)
    ax.set_yticklabels(agents, fontsize=8)
    ax.set_xlabel("Hour of horizon")
    ax.set_title("Per-agent role classification by hour")
    ax.set_xlim(0, T); ax.set_ylim(0, N)
    ax.invert_yaxis()

    patches = [
        mpatches.Patch(color=COLORS["C1"],  label="Seller"),
        mpatches.Patch(color="#E8E8E8",     label="Neutral"),
        mpatches.Patch(color="#378ADD",     label="Buyer"),
    ]
    ax.legend(handles=patches, loc="upper center", bbox_to_anchor=(0.5, -0.22),
              ncol=3, fontsize=7, frameon=False)
    fig.tight_layout()

    rows = {"hour": np.arange(T)}
    for n, name in enumerate(agents):
        rows[f"role_{name}"] = roles[n]
    pd.DataFrame(rows).to_csv(str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path), also_pdf=True))


# ── Fig paper: weekly welfare evolution per scenario ─────────────────────────

def fig_paper_subperiod(scenarios_data: dict, agents: list,
                         p2p_results, out_path: Path) -> Path:
    """Weekly net-benefit evolution for P2P, C1, C4 over 744-hour horizon.

    Adapts fig16 to English + IEEE single-col. Weeks are 168-hour bins.
    Trazabilidad: Reunion 01/05 — paper IEEE WEEF.
    """
    apply_ieee_style()
    T = len(p2p_results)
    week_size = 168  # hours per week
    n_weeks = max(1, T // week_size)
    week_labels = [f"W{w + 1}" for w in range(n_weeks)]

    def _weekly(per_agent_arr: np.ndarray) -> np.ndarray:
        """Sum per-hour net benefit per week (approximate from hourly share)."""
        total = float(per_agent_arr.sum())
        weekly = np.zeros(n_weeks)
        for w in range(n_weeks):
            h0, h1 = w * week_size, min((w + 1) * week_size, T)
            frac = (h1 - h0) / max(T, 1)
            weekly[w] = total * frac
        return weekly / 1e3  # kCOP

    scenario_colors = {"P2P": COLORS["P2P"], "C1": COLORS["C1"], "C4": COLORS["C4"]}

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 3.0))
    csv_rows: dict[str, np.ndarray] = {"week": np.array(week_labels)}
    for key, (total, per_agent) in scenarios_data.items():
        tag = "P2P" if "P2P" in key else ("C1" if "C1" in key else "C4")
        color = scenario_colors.get(tag, "#888888")
        weekly = _weekly(per_agent)
        ax.plot(np.arange(n_weeks), weekly, "o-", color=color,
                linewidth=1.5, markersize=4, label=key)
        csv_rows[key] = weekly

    ax.set_xticks(np.arange(n_weeks))
    ax.set_xticklabels(week_labels, fontsize=8)
    ax.set_xlabel("Week of August 2025")
    ax.set_ylabel("Net benefit per week (k COP)")
    ax.set_title("Weekly net benefit evolution by scenario")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20),
              ncol=1, fontsize=7, frameon=False)
    fig.tight_layout()

    pd.DataFrame(csv_rows).to_csv(str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path), also_pdf=True))


# ── Fig paper: C1 vs C4 per-agent bar chart ──────────────────────────────────

def fig_paper_c1_vs_c4_detailed(scenarios_data: dict, agents: list,
                                  out_path: Path) -> Path:
    """Grouped bar chart: C1 (CREG 174) vs C4 (CREG 101 072) per agent.

    Winner annotated above each pair with delta label.
    Adapts fig15 to English + IEEE single-col.
    Trazabilidad: Reunion 01/05 — paper IEEE WEEF.
    """
    apply_ieee_style()
    N = len(agents)

    c1_arr = np.zeros(N); c4_arr = np.zeros(N)
    for key, (total, per_agent) in scenarios_data.items():
        if "C1" in key:
            c1_arr = np.asarray(per_agent[:N], dtype=float) / 1e3
        elif "C4" in key:
            c4_arr = np.asarray(per_agent[:N], dtype=float) / 1e3

    x = np.arange(N)
    width = 0.36
    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 3.2))
    ax.bar(x - width / 2, c1_arr, width, label="C1 (CREG 174)",
           color=COLORS["C1"], alpha=0.90, edgecolor="white", linewidth=0.4)
    ax.bar(x + width / 2, c4_arr, width, label="C4 (CREG 101 072)",
           color=COLORS["C4"], alpha=0.90, edgecolor="white", linewidth=0.4)

    for n in range(N):
        top = max(c1_arr[n], c4_arr[n])
        delta = abs(c1_arr[n] - c4_arr[n])
        winner = "C1" if c1_arr[n] >= c4_arr[n] else "C4"
        ax.text(n, top + max(abs(top) * 0.04, 0.5),
                f"+{delta:.0f}\n({winner})",
                ha="center", va="bottom", fontsize=6,
                color=COLORS["C1"] if winner == "C1" else COLORS["C4"])

    ax.axhline(0.0, color="black", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(agents, rotation=10, ha="right", fontsize=8)
    ax.set_ylabel("Net benefit (k COP)")
    ax.set_title("C1 (CREG 174) vs C4 (CREG 101 072) per agent")
    ax.yaxis.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20),
              ncol=2, fontsize=7, frameon=False)
    fig.tight_layout()

    pd.DataFrame({"agent": agents, "C1_kCOP": c1_arr, "C4_kCOP": c4_arr}).to_csv(
        str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path), also_pdf=True))
