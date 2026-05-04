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
    SC = np.clip(np.array([r.SC for r in p2p_results]), -1.0, 1.0)
    SS = np.clip(np.array([r.SS for r in p2p_results]), -1.0, 1.0)
    IE = np.clip(np.array([r.IE for r in p2p_results]), -1.0, 1.0)

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

    fig, ax = plt.subplots(figsize=(WIDTH_DOUBLE_IN, 2.8))
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
    ax.legend(handles=patches, loc="upper center", bbox_to_anchor=(0.5, -0.32),
              ncol=3, fontsize=7, frameon=False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))

    rows = {"hour": np.arange(T)}
    for n, name in enumerate(agents):
        rows[f"role_{name}"] = roles[n]
    pd.DataFrame(rows).to_csv(str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path), also_pdf=True))


# ── Fig paper: weekly welfare evolution per scenario ─────────────────────────

def fig_paper_subperiod(scenarios_data: dict, agents: list,
                         p2p_results, G_klim, out_path: Path) -> Path:
    """Weekly net-benefit evolution for P2P, C1, C4 over 744-hour horizon.

    Adapts fig16 to English + IEEE single-col. Weeks are 168-hour bins.
    Per-week welfare is approximated by weighting the scenario total
    proportionally to weekly community PV availability (sum of G_klim over
    agents). Honest under the constraint that C1 and C4 settle monthly:
    no true weekly attribution exists for those, so PV availability is the
    most defensible proxy for activity intensity.
    Trazabilidad: Reunion 01/05 — paper IEEE WEEF.
    """
    apply_ieee_style()
    T = len(p2p_results)
    week_size = 168  # hours per week
    n_weeks = max(1, T // week_size)
    week_labels = [f"W{w + 1}" for w in range(n_weeks)]

    G_arr = np.asarray(G_klim, dtype=float)
    if G_arr.ndim == 2:
        G_total_h = G_arr.sum(axis=0) if G_arr.shape[0] < G_arr.shape[1] else G_arr.sum(axis=1)
    else:
        G_total_h = G_arr
    if G_total_h.shape[0] < T:
        pad = np.zeros(T - G_total_h.shape[0])
        G_total_h = np.concatenate([G_total_h, pad])
    elif G_total_h.shape[0] > T:
        G_total_h = G_total_h[:T]

    pv_per_week = np.array([
        float(G_total_h[w * week_size: min((w + 1) * week_size, T)].sum())
        for w in range(n_weeks)
    ])
    pv_total = float(pv_per_week.sum())
    if pv_total > 1e-9:
        weights = pv_per_week / pv_total
    else:
        weights = np.full(n_weeks, 1.0 / n_weeks)

    def _weekly(per_agent_arr: np.ndarray) -> np.ndarray:
        total = float(np.asarray(per_agent_arr, dtype=float).sum())
        return total * weights / 1e3  # kCOP

    scenario_colors = {"P2P": COLORS["P2P"], "C1": COLORS["C1"], "C4": COLORS["C4"]}

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 3.0))
    csv_rows: dict[str, np.ndarray] = {"week": np.array(week_labels)}
    for key, (total, per_agent) in scenarios_data.items():
        if "P2P" in key:
            tag = "P2P"
        elif "C1" in key:
            tag = "C1"
        else:
            tag = "C4"
        color = scenario_colors.get(tag, "#888888")
        weekly = _weekly(per_agent)
        ax.plot(np.arange(n_weeks), weekly, "o-", color=color,
                linewidth=1.5, markersize=4, label=key)
        csv_rows[key] = weekly

    ax.set_xticks(np.arange(n_weeks))
    ax.set_xticklabels(week_labels, fontsize=8)
    ax.set_xlabel("Week of August 2025 (PV-weighted attribution)")
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
        if "P2P" in key:
            continue
        if "C1" in key:
            c1_arr = np.asarray(per_agent[:N], dtype=float) / 1e3
        elif "C4" in key or "101 072" in key:
            c4_arr = np.asarray(per_agent[:N], dtype=float) / 1e3

    x = np.arange(N)
    width = 0.36
    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 3.2))
    ax.bar(x - width / 2, c1_arr, width, label="C1 (CREG 174)",
           color=COLORS["C1"], alpha=0.90, edgecolor="white", linewidth=0.4)
    ax.bar(x + width / 2, c4_arr, width, label="C2 (CREG 101 072)",
           color=COLORS["C4"], alpha=0.90, edgecolor="white", linewidth=0.4)

    for n in range(N):
        top = max(c1_arr[n], c4_arr[n])
        delta = abs(c1_arr[n] - c4_arr[n])
        winner = "C1" if c1_arr[n] >= c4_arr[n] else "C2"
        ax.text(n, top + max(abs(top) * 0.04, 0.5),
                f"+{delta:.0f}\n({winner})",
                ha="center", va="bottom", fontsize=6,
                color=COLORS["C1"] if winner == "C1" else COLORS["C4"])

    ax.axhline(0.0, color="black", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(agents, rotation=10, ha="right", fontsize=8)
    ax.set_ylabel("Net benefit (k COP)")
    ax.set_title("C1 (CREG 174) vs C2 (CREG 101 072) per agent", pad=8)
    ax.yaxis.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)
    y_top = max(c1_arr.max(), c4_arr.max())
    ax.set_ylim(top=y_top * 1.18)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20),
              ncol=2, fontsize=7, frameon=False)
    fig.tight_layout()

    pd.DataFrame({"agent": agents, "C1_kCOP": c1_arr, "C4_kCOP": c4_arr}).to_csv(
        str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path), also_pdf=True))


# ── Fig paper: RD + Stackelberg convergence (Game-theoretic certificate) ─────

def fig_paper_convergence(conv_data: list, agents: list,
                           out_path_prefix: Path) -> list:
    """RD + Stackelberg convergence trajectories for representative hours.

    Adapts plot_convergence (visualization/plots.py:1228) to English + IEEE
    double-column. One figure per representative hour with three stacked
    panels:
      (a) Aggregate welfare W_j, W_i, W=W_j+W_i per outer Stackelberg iter.
      (b) Buyer price dynamics pi_i(t) — last replicator-dynamics inner loop.
      (c) Power exchange dynamics P_{ji}(t) for all active seller-buyer pairs.

    Provides the visual certificate that the equilibrium reported in
    Tables I-III is the actual fixed point of the algorithm, addressing the
    referee question on solution quality and convergence.

    Parameters
    ----------
    conv_data : list[ConvergenceData] from `EMSP2P.run_convergence(...)`.
    agents    : list of agent names indexed as in the EMS.
    out_path_prefix : path WITHOUT extension; the function appends
        `_h{HH:04d}` per hour and `.png/.pdf` via save_ieee.

    Returns
    -------
    list[Path]: paths of generated PNG files (one per hour).
    """
    apply_ieee_style()
    saved: list[Path] = []

    for cd in conv_data:
        J = len(cd.seller_ids)
        I = len(cd.buyer_ids)
        n_iters = len(cd.welfare_iters)
        if n_iters == 0 or J == 0 or I == 0:
            continue

        regime = ("surplus"
                  if float(np.sum(cd.G_net_j)) >= float(np.sum(cd.D_net_i))
                  else "deficit")

        fig = plt.figure(figsize=(WIDTH_DOUBLE_IN, 6.4))
        gs = fig.add_gridspec(3, 1, hspace=0.55, height_ratios=[1.0, 1.0, 1.1])

        # ── (a) Aggregate welfare per outer Stackelberg iteration ────────────
        ax_w = fig.add_subplot(gs[0, 0])
        iters = np.arange(1, n_iters + 1)
        Wj_arr = np.array([w[0] for w in cd.welfare_iters])
        Wi_arr = np.array([w[1] for w in cd.welfare_iters])
        W_total = Wj_arr + Wi_arr

        ax_w.plot(iters, Wj_arr, "o--", color=COLORS["C4"], lw=1.4,
                  markersize=4, label=r"$W_j$ (sellers)")
        ax_w.plot(iters, Wi_arr, "s--", color="#378ADD", lw=1.4,
                  markersize=4, label=r"$W_i$ (buyers)")
        ax_w.plot(iters, W_total, "D-", color=COLORS["P2P"], lw=1.8,
                  markersize=5, label=r"$W=W_j+W_i$")
        ax_w.axhline(W_total[-1], color=COLORS["P2P"], lw=0.5, ls=":", alpha=0.6)
        ax_w.set_xlabel("Stackelberg iteration")
        ax_w.set_ylabel("Welfare (COP)")
        ax_w.set_title(f"(a) Aggregate welfare convergence — hour k={cd.hour} ({regime})")
        ax_w.set_xticks(iters)
        ax_w.legend(loc="best", fontsize=7, frameon=False, ncol=3)

        # ── (b) Buyer price trajectories pi_i(t) — last RD loop ──────────────
        ax_pi = fig.add_subplot(gs[1, 0])
        if cd.pi_traj.size > 0 and cd.t_buyers.size > 0:
            for i in range(I):
                bid = cd.buyer_ids[i]
                bname = agents[bid] if bid < len(agents) else f"B{bid}"
                ax_pi.plot(cd.t_buyers, cd.pi_traj[i, :],
                           color=COLORS_AGENT[i % len(COLORS_AGENT)],
                           lw=1.2, label=rf"$\pi_{{{bname}}}$")
            ax_pi.set_xlabel(r"Integration time $t$")
            ax_pi.set_ylabel(r"$\pi_i(t)$ (COP/kWh)")
            ax_pi.set_title(r"(b) Buyer price replicator dynamics — last iteration")
            ax_pi.legend(loc="best", fontsize=7, frameon=False,
                         ncol=min(I, 3))
        else:
            ax_pi.text(0.5, 0.5, "no trajectory captured",
                       ha="center", va="center", transform=ax_pi.transAxes,
                       fontsize=8, color="#888888")

        # ── (c) Power exchange dynamics P_{ji}(t) ────────────────────────────
        ax_p = fig.add_subplot(gs[2, 0])
        pair_count = 0
        if cd.P_traj.size > 0 and cd.t_sellers.size > 0:
            for j in range(J):
                sid = cd.seller_ids[j]
                sname = agents[sid] if sid < len(agents) else f"S{sid}"
                for i in range(I):
                    bid = cd.buyer_ids[i]
                    bname = agents[bid] if bid < len(agents) else f"B{bid}"
                    color = COLORS_AGENT[pair_count % len(COLORS_AGENT)]
                    ax_p.plot(cd.t_sellers, cd.P_traj[j, i, :],
                              color=color, lw=1.1,
                              label=rf"$P_{{{sname}\rightarrow {bname}}}$")
                    pair_count += 1
            ax_p.set_xlabel(r"Integration time $t$")
            ax_p.set_ylabel(r"$P_{ji}(t)$ (kW)")
            ax_p.set_title(r"(c) Power exchange replicator dynamics — last iteration")
            ax_p.legend(loc="upper center", bbox_to_anchor=(0.5, -0.30),
                         ncol=min(pair_count, 4), fontsize=6, frameon=False)
        else:
            ax_p.text(0.5, 0.5, "no trajectory captured",
                       ha="center", va="center", transform=ax_p.transAxes,
                       fontsize=8, color="#888888")

        # Final-iteration scalars annotated inside subplot (a) top-right corner,
        # so the box never collides with the panel-(c) bottom legend.
        P_final = cd.P_star_iters[-1]
        pi_final = cd.pi_star_iters[-1]
        info = (
            rf"Final (it.\,{n_iters}): "
            rf"$\sum P_{{ji}}={float(np.sum(P_final)):.2f}$ kW, "
            rf"$\pi_i\in[{float(pi_final.min()):.0f},{float(pi_final.max()):.0f}]$ COP/kWh"
        )
        ax_w.text(0.99, 0.96, info, fontsize=6.5,
                  family="monospace", ha="right", va="top",
                  transform=ax_w.transAxes,
                  bbox=dict(boxstyle="round,pad=0.25", fc="#fffbe6",
                            ec="#cccccc", lw=0.5, alpha=0.9))

        fig.tight_layout(rect=(0, 0.04, 1, 1))

        # Per-hour CSV with welfare-iteration trace
        df = pd.DataFrame({
            "iteration": iters,
            "W_j": Wj_arr,
            "W_i": Wi_arr,
            "W_total": W_total,
        })
        path_no_ext = f"{out_path_prefix}_h{cd.hour:04d}"
        df.to_csv(path_no_ext + ".csv", index=False)
        saved.append(Path(save_ieee(fig, path_no_ext, also_pdf=True)))

    return saved


# ── Fig paper: Price of Fairness analysis (Bertsimas et al. 2011) ────────────

def fig_paper_price_of_fairness(scenarios_data: dict, agents: list,
                                 out_path: Path) -> Path:
    """Three-panel paper-spec PoF analysis for P2P / C1 / C4.

    Adapts plot_fig20_price_of_fairness (visualization/plots.py:2075) to
    English + IEEE double-column. Computes Gini per scenario and the
    Price of Fairness PoF = (W_eff - W_fair) / |W_eff| using the formal
    definition of Bertsimas, Farias & Trichakis (2011, Op. Res. 59:1).

    Panels:
      (a) Total welfare per scenario (kCOP), with the efficient and
          equitable scenarios annotated.
      (b) Gini index per scenario (lower = more equitable), sorted
          ascending; the equitable scenario is highlighted.
      (c) Per-agent sacrifice PoF_n = max(0, (B_n^eff - B_n^fair) /
          |B_n^eff|): the local efficiency cost imposed on each agent
          by switching from the efficient to the equitable allocation.

    Trazabilidad: Reunion 01/05 — paper IEEE WEEF, fairness narrative.
    """
    from analysis.fairness import compute_pof
    from core.settlement import gini_index

    apply_ieee_style()

    # 1) Compute net benefits and Gini per scenario from scenarios_data
    nb: dict[str, np.ndarray] = {}
    gini: dict[str, float] = {}
    for key, (total, per_agent) in scenarios_data.items():
        arr = np.asarray(per_agent, dtype=float)
        nb[key] = arr
        gini[key] = float(gini_index(arr))

    fr = compute_pof(nb, gini)

    keys = list(scenarios_data.keys())
    totals_kcop = np.array([float(nb[k].sum()) / 1e3 for k in keys])

    def _color_for(key: str) -> str:
        if key.startswith("P2P"):
            return COLORS["P2P"]
        if key.startswith("C1"):
            return COLORS["C1"]
        return COLORS["C4"]

    fig, axes = plt.subplots(1, 3, figsize=(WIDTH_DOUBLE_IN, 3.0),
                              gridspec_kw={"width_ratios": [1.0, 1.0, 1.4]})

    # ── (a) Total welfare per scenario ───────────────────────────────────────
    ax = axes[0]
    x = np.arange(len(keys))
    bars = ax.bar(x, totals_kcop,
                  color=[_color_for(k) for k in keys],
                  alpha=0.88, edgecolor="white", linewidth=0.4)
    for b, v in zip(bars, totals_kcop):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                f"{v:.0f}", ha="center", va="bottom",
                fontsize=7, fontweight="bold")
    ax.set_xticks(x)
    short_keys = [k.split(" ")[0] for k in keys]  # P2P, C1, C2
    ax.set_xticklabels(short_keys, fontsize=8)
    ax.set_ylabel("Total welfare (k COP)")
    ax.set_title(f"(a) Welfare\nPoF = {fr.pof:.4f}")
    ax.yaxis.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)
    if fr.eff_scenario in keys:
        ax.text(keys.index(fr.eff_scenario), 0.02,
                "eff", ha="center", va="bottom",
                fontsize=6.5, color="white", fontweight="bold",
                transform=ax.get_xaxis_transform())
    if fr.fair_scenario in keys and fr.fair_scenario != fr.eff_scenario:
        ax.text(keys.index(fr.fair_scenario), 0.02,
                "fair", ha="center", va="bottom",
                fontsize=6.5, color="white", fontweight="bold",
                transform=ax.get_xaxis_transform())

    # ── (b) Gini index per scenario ──────────────────────────────────────────
    ax = axes[1]
    gini_vals = np.array([gini[k] for k in keys])
    bars = ax.bar(x, gini_vals,
                  color=[_color_for(k) for k in keys],
                  alpha=0.88, edgecolor="white", linewidth=0.4)
    for b, v in zip(bars, gini_vals):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                f"{v:.3f}", ha="center", va="bottom",
                fontsize=7, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(short_keys, fontsize=8)
    ax.set_ylabel("Gini coefficient")
    ax.set_title("(b) Inequity (lower = fairer)")
    ax.yaxis.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)

    # ── (c) Per-agent sacrifice PoF_n ────────────────────────────────────────
    ax = axes[2]
    pof_n = np.asarray(fr.pof_per_agent, dtype=float)
    if pof_n.size == len(agents) and pof_n.size > 0:
        xa = np.arange(len(agents))
        ax.bar(xa, pof_n, color="#7F77DD", alpha=0.88,
               edgecolor="white", linewidth=0.4)
        for n, v in enumerate(pof_n):
            ax.text(n, v, f"{v:.2f}", ha="center", va="bottom",
                    fontsize=7)
        ax.set_xticks(xa)
        ax.set_xticklabels(agents, rotation=15, ha="right", fontsize=7)
        ax.set_ylabel(r"$\mathrm{PoF}_n$ (relative sacrifice)")
        title_txt = (f"(c) Per-agent sacrifice\n"
                     f"{fr.eff_scenario.split(' ')[0]} $\\to$ "
                     f"{fr.fair_scenario.split(' ')[0]}")
        ax.set_title(title_txt)
        ax.yaxis.grid(True, alpha=0.3, linewidth=0.5)
        ax.set_axisbelow(True)
    else:
        ax.text(0.5, 0.5, "PoF n/a (eff = fair)", ha="center", va="center",
                transform=ax.transAxes, fontsize=8, color="#888888")
        ax.set_axis_off()

    fig.suptitle("Price of Fairness — Bertsimas, Farias & Trichakis (2011)",
                 fontsize=9, fontweight="bold", y=1.02)
    fig.tight_layout()

    # Sibling CSV with key numbers
    rows = {
        "scenario":         np.array(keys),
        "total_welfare_COP": np.array([float(nb[k].sum()) for k in keys]),
        "gini":              np.array([gini[k] for k in keys]),
    }
    pd.DataFrame(rows).to_csv(str(out_path) + ".csv", index=False)
    if pof_n.size == len(agents):
        pd.DataFrame({"agent": agents, "pof_n": pof_n}).to_csv(
            str(out_path) + "_per_agent.csv", index=False)

    return Path(save_ieee(fig, str(out_path), also_pdf=True))


# ── Fig paper: Welfare flow breakdown per scenario ───────────────────────────

def fig_paper_flow_breakdown(scenarios_data: dict, decomposition: dict,
                              out_path: Path) -> Path:
    """Stacked bar paper-spec flow breakdown for P2P / C1 / C4.

    Adapts plot_flow_breakdown (visualization/plots.py:1003) to English +
    IEEE single-column. Decomposes total welfare per scenario into:
      - Common autoconsumption savings (offset, identical across
        scenarios under CAL-25 homogenization).
      - Surplus revenue (the differentiating component: P2P clearing,
        C1 monthly settlement, C4 PDE + spot residual).

    The figure makes visible *why* the three scenarios produce different
    totals despite sharing the same autoconsumption baseline. Uses
    `decomposition` produced by run_paper_iter.py:construir_resumen,
    which already encodes the renamed paper keys.

    Trazabilidad: Reunion 01/05 — paper IEEE WEEF, monthly vs hourly
    settlement framing (Section II.B).
    """
    apply_ieee_style()

    keys = list(scenarios_data.keys())
    short_keys = [k.split(" ")[0] for k in keys]

    auto_kcop = np.zeros(len(keys))
    rev_kcop = np.zeros(len(keys))
    for i, k in enumerate(keys):
        entry = decomposition.get(k) if isinstance(decomposition, dict) else None
        if isinstance(entry, (tuple, list)) and len(entry) >= 2:
            auto_kcop[i] = float(entry[0]) / 1e3
            rev_kcop[i] = float(entry[1]) / 1e3
        elif isinstance(entry, dict):
            auto_kcop[i] = float(entry.get("autoconsumo_total", 0.0)) / 1e3
            rev_kcop[i] = float(entry.get("mercado_total", 0.0)) / 1e3

    def _color_for(key: str) -> str:
        if key.startswith("P2P"):
            return COLORS["P2P"]
        if key.startswith("C1"):
            return COLORS["C1"]
        return COLORS["C4"]

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 3.4))
    x = np.arange(len(keys))
    base_color = "#cccccc"

    bars_auto = ax.bar(x, auto_kcop, color=base_color,
                       label="Common autoconsumption",
                       edgecolor="white", linewidth=0.4, zorder=3)
    bars_rev = ax.bar(x, rev_kcop, bottom=auto_kcop,
                      color=[_color_for(k) for k in keys],
                      alpha=0.88, label="Scenario-specific surplus revenue",
                      edgecolor="white", linewidth=0.4, zorder=3)

    totals = auto_kcop + rev_kcop
    for i, (a, r, t) in enumerate(zip(auto_kcop, rev_kcop, totals)):
        ax.text(i, t + 0.015 * max(totals.max(), 1.0),
                f"{t:.0f}", ha="center", va="bottom",
                fontsize=7, fontweight="bold", color=_color_for(keys[i]))
        if a > 0:
            ax.text(i, a / 2, f"{a:.0f}",
                    ha="center", va="center", fontsize=6.5, color="#444444")
        if r > 0:
            ax.text(i, a + r / 2, f"{r:.0f}",
                    ha="center", va="center", fontsize=6.5, color="white",
                    fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(short_keys, fontsize=8)
    ax.set_ylabel("Welfare (k COP)")
    ax.set_title("Welfare decomposition: common offset + surplus revenue")
    ax.yaxis.grid(True, alpha=0.35, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18),
              ncol=1, fontsize=7, frameon=False)
    fig.tight_layout()

    pd.DataFrame({
        "scenario": keys,
        "common_autoconsumption_kCOP": auto_kcop,
        "surplus_revenue_kCOP": rev_kcop,
        "total_kCOP": totals,
    }).to_csv(str(out_path) + ".csv", index=False)

    return Path(save_ieee(fig, str(out_path), also_pdf=True))
