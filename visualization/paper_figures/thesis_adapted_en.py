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
from typing import Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from visualization.ieee_style import (
    apply_ieee_style, save_ieee, COLORS, COLORS_AGENT,
    WIDTH_SINGLE_IN, WIDTH_DOUBLE_IN,
)


def fig_paper_per_agent_benefit(scenarios_data: dict, agents: list,
                                 out_path: Path) -> Path:
    """Grouped bar chart: net benefit per agent per scenario (P2P, C1, C2).

    Visualiza TABLA II del paper (Per-agent net benefit). Sustenta el
    claim "P2P dominates regulated baseline (C1) for 5/5 agents;
    4/5 also prefer P2P over C2 PPA. UCC is the only outlier".

    Redesign 2026-05-05 (Brayan paper review): adopta el patrón visual de
    fig_paper_c1_vs_c4_detailed para consistencia inter-figura:
      - Title bold con case-study tag inline.
      - Aggregate subtitle italic gris (totales por mecanismo + winners).
      - Numeros DENTRO de cada barra (white bold) — sin overlap.
      - Winner box arriba de cada cluster: "+ΔkCOP (mech)" colored.
      - axvspan en outlier (UCC: C2 wins) — paralelo al highlight de C4.
      - Footer narrativo gris explicando el outlier.
      - Custom legend con 4 patches (P2P, C1, C2, highlight zone).

    Trazabilidad: Reunion 01/05 — paper IEEE WEEF.
    """
    apply_ieee_style()
    N = len(agents)
    scenario_keys = list(scenarios_data.keys())  # P2P, C1, C2 (renamed)
    nb_per_agent = {k: scenarios_data[k][1] / 1e3 for k in scenario_keys}

    def _color_for(key: str) -> str:
        if key.startswith("P2P"):
            return COLORS["P2P"]
        if key.startswith("C1"):
            return COLORS["C1"]
        if key.startswith("C2 (CREG 101") or key.startswith("C4"):
            return COLORS["C4"]
        return "#888888"

    short_label = {}
    for key in scenario_keys:
        short_label[key] = ("P2P" if key.startswith("P2P")
                            else "C1 (CREG 174)" if key.startswith("C1")
                            else "C2 (CREG 101 072)")

    # Identificacion P2P / C1 / C2
    p2p_key = next(k for k in scenario_keys if k.startswith("P2P"))
    c1_key  = next(k for k in scenario_keys if k.startswith("C1"))
    c2_key  = next(k for k in scenario_keys
                    if k.startswith("C2") or k.startswith("C4"))

    p2p_arr = np.asarray(nb_per_agent[p2p_key], dtype=float)
    c1_arr  = np.asarray(nb_per_agent[c1_key],  dtype=float)
    c2_arr  = np.asarray(nb_per_agent[c2_key],  dtype=float)
    nb_matrix = np.vstack([p2p_arr, c1_arr, c2_arr])  # (3, N)
    nb_max = float(np.max(nb_matrix))

    # Winner argmax sobre los 3 mecanismos
    winner_idx = np.argmax(nb_matrix, axis=0)
    winner_short_map = {0: "P2P", 1: "C1", 2: "C2"}
    color_short_map = {0: COLORS["P2P"], 1: COLORS["C1"], 2: COLORS["C4"]}

    n_p2p_wins = int(np.sum(winner_idx == 0))
    n_c1_wins  = int(np.sum(winner_idx == 1))
    n_c2_wins  = int(np.sum(winner_idx == 2))

    # Aggregate totals
    p2p_total = float(p2p_arr.sum())
    c1_total  = float(c1_arr.sum())
    c2_total  = float(c2_arr.sum())
    totals = {"P2P": p2p_total, "C1": c1_total, "C2": c2_total}
    agg_winner = max(totals, key=totals.get)
    sorted_totals = sorted(totals.values(), reverse=True)
    agg_delta = sorted_totals[0] - sorted_totals[1]
    agg_pct = (agg_delta / sorted_totals[1]) * 100.0

    x = np.arange(N)
    width = 0.26  # 3 bars per cluster

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 2.9))

    # Identifica P2P star (mayor gap P2P-C1, indicador de fuerte beneficio)
    p2p_minus_c1 = p2p_arr - c1_arr
    star_n = int(np.argmax(p2p_minus_c1))
    star_gap = float(p2p_minus_c1[star_n])
    star_pct = 100.0 * star_gap / float(c1_arr[star_n])

    # Highlight axvspan: outliers (C1/C2 wins) + P2P star
    for n in range(N):
        if winner_idx[n] != 0:  # outlier (C1 o C2 wins) — pink
            ax.axvspan(n - 0.45, n + 0.45,
                       alpha=0.10, color=color_short_map[winner_idx[n]],
                       zorder=0)
        elif n == star_n:  # P2P star — sombreado azul sutil
            ax.axvspan(n - 0.45, n + 0.45,
                       alpha=0.08, color=COLORS["P2P"],
                       zorder=0)

    # Bars con edgecolor negro consistente
    bars_p2p = ax.bar(x - width, p2p_arr, width,
                       color=COLORS["P2P"], edgecolor="black",
                       linewidth=0.6, zorder=3,
                       label="P2P (Stackelberg + RD)")
    bars_c1 = ax.bar(x, c1_arr, width,
                      color=COLORS["C1"], edgecolor="black",
                      linewidth=0.6, zorder=3,
                      label="C1 (CREG 174)")
    bars_c2 = ax.bar(x + width, c2_arr, width,
                      color=COLORS["C4"], edgecolor="black",
                      linewidth=0.6, zorder=3,
                      label="C2 (CREG 101 072)")

    # Valores DENTRO de cada barra (white bold, va=top)
    for bar_set in (bars_p2p, bars_c1, bars_c2):
        for bar in bar_set:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h - 30,
                    f"{h:.0f}",
                    ha="center", va="top", fontsize=5.5,
                    fontweight="bold", color="white", zorder=4)

    # Winner box arriba de cada cluster: "+ΔkCOP (mech)"
    y_top = nb_max
    for n in range(N):
        top = float(np.max(nb_matrix[:, n]))
        # Delta vs second-best
        sorted_vals = np.sort(nb_matrix[:, n])[::-1]
        delta = float(sorted_vals[0] - sorted_vals[1])
        winner_short = winner_short_map[winner_idx[n]]
        winner_color = color_short_map[winner_idx[n]]
        # ★ prefix en outlier (no-P2P winner)
        prefix = r"$\bigstar$ " if winner_idx[n] != 0 else ""
        ax.text(n, top + y_top * 0.04,
                f"{prefix}+{delta:.0f}k",
                ha="center", va="bottom", fontsize=6, fontweight="bold",
                color=winner_color,
                bbox=dict(facecolor="white", edgecolor=winner_color,
                          boxstyle="round,pad=0.18", linewidth=0.5,
                          alpha=0.95), zorder=5)

    ax.axhline(0.0, color="black", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(agents, fontsize=7)
    ax.set_ylabel("Net benefit (kCOP)", fontsize=7.5)
    ax.tick_params(axis="y", labelsize=6.5)
    ax.yaxis.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.set_ylim(top=y_top * 1.18)

    # Title reducido (case-study tag movido al caption del paper)
    ax.set_title(
        "Per-agent net benefit by mechanism",
        fontsize=8.5, fontweight="bold", pad=4,
    )

    outlier_n = None
    for n in range(N):
        if winner_idx[n] != 0:
            outlier_n = n
            break

    # Custom legend con 3 patches (sin highlight zones; van al caption)
    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor=COLORS["P2P"], edgecolor="black", linewidth=0.5,
              label="P2P"),
        Patch(facecolor=COLORS["C1"], edgecolor="black", linewidth=0.5,
              label="C1 (CREG 174)"),
        Patch(facecolor=COLORS["C4"], edgecolor="black", linewidth=0.5,
              label="C2 (CREG 101 072)"),
    ]
    ax.legend(
        handles=handles,
        loc="upper center", bbox_to_anchor=(0.5, -0.16),
        ncol=3, fontsize=6, frameon=False,
        columnspacing=0.8, handletextpad=0.4,
    )
    fig.subplots_adjust(top=0.90, bottom=0.18, left=0.13, right=0.98)

    df = pd.DataFrame({"agent": agents,
                       **{k: nb_per_agent[k] for k in scenario_keys}})
    df.to_csv(str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path), also_pdf=True))


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
    total_kwh = float(kwh.sum())
    n_days = T // 24
    grid = kwh[: n_days * 24].reshape(n_days, 24)

    # Localizar peak (day, hour) y valor
    peak_idx = np.unravel_index(np.argmax(grid), grid.shape)
    peak_day = int(peak_idx[0]) + 1   # 1-indexed dia del mes
    peak_hour = int(peak_idx[1])
    peak_value = float(grid[peak_idx])

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 2.7))
    vmax = max(float(np.percentile(grid, 99)), 1e-6)
    im = ax.pcolormesh(np.arange(25), np.arange(n_days + 1), grid,
                       cmap="viridis", shading="flat", vmin=0, vmax=vmax)
    ax.set_xlabel("Hour of day", fontsize=7.5)
    ax.set_ylabel("Day of August 2025", fontsize=7.5)
    ax.set_xticks(np.arange(0, 25, 6))
    ax.tick_params(axis="both", labelsize=6.5)

    # (c) Y-axis calendario explicito: D1, D6, D11, D16, D21, D26, D31
    day_ticks = np.array([0, 5, 10, 15, 20, 25, n_days - 1])
    day_ticks = day_ticks[day_ticks < n_days]
    ax.set_yticks(day_ticks + 0.5)
    ax.set_yticklabels([f"D{int(t) + 1}" for t in day_ticks])
    ax.invert_yaxis()

    # (d) Anotar peak con circulo blanco + texto compacto
    ax.scatter(peak_hour + 0.5, peak_day - 0.5,
               s=70, facecolors="none", edgecolors="white",
               linewidth=1.0, zorder=5)
    label_x = peak_hour + 0.5 - 3
    ax.annotate(
        f"Peak D{peak_day} {peak_hour:02d}h",
        xy=(peak_hour + 0.5, peak_day - 0.5),
        xytext=(label_x, peak_day - 0.5),
        textcoords="data",
        fontsize=5.5, fontstyle="italic", color="white",
        ha="right", va="center",
        bbox=dict(boxstyle="round,pad=0.18", facecolor="#222222",
                  edgecolor="white", lw=0.4, alpha=0.85),
        arrowprops=dict(arrowstyle="->", color="white", lw=0.5),
        zorder=6,
    )

    cbar = fig.colorbar(im, ax=ax, label="kWh/h",
                        fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=6)
    cbar.set_label("kWh/h", fontsize=7)

    # Weekend markers: Aug 1, 2025 = Friday (weekday idx 4, where Mon=0)
    # Strip in the left margin (data x in [-0.55, -0.15]) for sat/sun rows
    WEEKDAY_AUG1 = 4
    n_weekend = 0
    kwh_weekend = 0.0
    kwh_weekday = 0.0
    n_weekday = 0
    for d in range(1, n_days + 1):
        widx = (WEEKDAY_AUG1 + d - 1) % 7  # 0=Mon, 5=Sat, 6=Sun
        if widx in (5, 6):
            n_weekend += 1
            kwh_weekend += float(grid[d - 1].sum())
            ax.fill_betweenx(
                [d - 1, d], -0.55, -0.15,
                facecolor="#7A7A7A", alpha=0.55, edgecolor="none",
                clip_on=False, zorder=2,
            )
            ax.text(-0.35, d - 0.5, "Sa" if widx == 5 else "Su",
                    ha="center", va="center", fontsize=5.0,
                    color="white", fontweight="bold",
                    clip_on=False, zorder=3)
        else:
            n_weekday += 1
            kwh_weekday += float(grid[d - 1].sum())
    avg_weekend = kwh_weekend / max(n_weekend, 1)
    avg_weekday = kwh_weekday / max(n_weekday, 1)
    ratio_wd_we = avg_weekday / max(avg_weekend, 1e-3)

    # Star marker on y-axis at peak_day position (audit pattern)
    ax.text(-0.85, peak_day - 0.5, r"$\bigstar$",
            ha="right", va="center", fontsize=11,
            color="#C0651B", fontweight="bold",
            clip_on=False, zorder=10)

    # Title reducido (case-study tag movido al caption del paper)
    ax.set_title("P2P market activity by day $\\times$ hour",
                  fontsize=10, fontweight="bold", pad=22)

    # Key message itálica naranja bold con dualidad solar+weekday
    key_msg = ("P2P trading is solar- and weekday-driven: weekends (gray strip) "
               rf"trade {ratio_wd_we:.1f}$\times$ less than workdays")
    ax.text(0.5, 1.02, key_msg,
            transform=ax.transAxes, ha="center", va="bottom",
            fontsize=8.5, fontstyle="italic", fontweight="bold",
            color="#C0651B")

    # Footer azul itálica con KPIs cuantitativos
    footer_kpi = (
        rf"{n_active}/{T} h active ({pct_active:.1f}%) $\cdot$ "
        rf"{total_kwh:.0f} kWh traded $\cdot$ "
        rf"peak D{peak_day}, {peak_hour:02d}h ({peak_value:.1f} kWh/h) $\cdot$ "
        rf"avg {avg_weekday:.1f} (Mon-Fri) vs {avg_weekend:.1f} kWh/day (Sat-Sun)"
    )
    fig.text(0.5, 0.015, footer_kpi, ha="center", va="bottom",
             fontsize=7.5, fontstyle="italic", color="#1F4F8A")

    fig.tight_layout(rect=(0, 0.04, 1, 0.97))

    pd.DataFrame({"hour": np.arange(T), "kwh_p2p": kwh}).to_csv(
        str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path)))


def fig_paper_hourly_prices(p2p_results, out_path: Path,
                             agents: Optional[list] = None,
                             pi_gs: Optional[float] = None,
                             pi_gb: float = 234.0) -> Path:
    """Distribution of P2P clearing prices by hour of day, **per-buyer split**.

    Adaptacion en ingles de fig3 panel B. Revela heterogeneidad de precios
    entre agentes buyer (Cesmag suele clavarse al floor por baja PV;
    Mariana/UCC/HUDN suben mas en horas pico).

    Parameters
    ----------
    agents : lista de nombres de agentes (matching el orden de los ids).
             Si None, se etiquetan como "A0, A1, ..." genericos.
    pi_gs  : admissible upper bound (CEDENAR median); si None, infiere
             como max(P90)*1.05 para escala visual.
    pi_gb  : admissible lower bound (XM bolsa floor con techo PES); 234.
    """
    apply_ieee_style()
    T = len(p2p_results)
    if T == 0:
        raise ValueError("p2p_results vacio")

    # Determinar N (max buyer_id + 1 sobre todas las horas)
    N_max = 0
    for r in p2p_results:
        if r.buyer_ids:
            N_max = max(N_max, max(r.buyer_ids) + 1)
    N = N_max if N_max > 0 else 1
    if agents is None or len(agents) < N:
        agents = [f"A{n}" for n in range(N)]

    # pi_per_agent[(N, T)]: precio del agente n en hora k (NaN si no buyer)
    pi_per_agent = np.full((N, T), np.nan)
    active_market_hours = set()  # horas con mercado P2P activo
    for r in p2p_results:
        if r.pi_star is not None and r.buyer_ids and r.P_star is not None:
            if float(np.sum(r.P_star)) > 1e-6:
                active_market_hours.add(r.k)
            for i, bid in enumerate(r.buyer_ids):
                if 0 <= bid < N:
                    pi_per_agent[bid, r.k] = float(r.pi_star[i])

    n_days = T // 24
    h_day = np.arange(24)
    # Reshape a (N, n_days, 24) para agregar por hora-of-day
    grid_per_agent = pi_per_agent[:, : n_days * 24].reshape(N, n_days, 24)
    med_per_agent = np.nanmedian(grid_per_agent, axis=1)   # (N, 24)
    # Conteo de horas-buyer por agente, RELATIVO a horas activas (no a 744)
    buyer_hours = np.sum(~np.isnan(pi_per_agent), axis=1)  # (N,)
    n_active = max(len(active_market_hours), 1)

    # Tambien calcular la community avg (para comparacion en CSV)
    avg_price = np.full(T, np.nan)
    for r in p2p_results:
        if r.pi_star is not None and r.P_star is not None:
            total = float(np.sum(r.P_star))
            if total > 1e-6:
                w = np.sum(r.P_star, axis=0) / total
                avg_price[r.k] = float(np.dot(w, r.pi_star))
    grid_avg = avg_price[: n_days * 24].reshape(n_days, 24)
    med_avg = np.nanmedian(grid_avg, axis=0)

    # Identificar peaks de la community avg para el subtitle
    active_mask = ~np.isnan(med_avg)
    active_hours = h_day[active_mask]
    morning_peak = evening_peak = (None, None)
    if active_hours.size > 0:
        evening_hours = active_hours[active_hours >= 16]
        if evening_hours.size > 0:
            evening_peak = (
                int(evening_hours[np.argmax(med_avg[evening_hours])]),
                float(med_avg[evening_hours[np.argmax(med_avg[evening_hours])]])
            )

    if pi_gs is None:
        max_obs = float(np.nanmax(pi_per_agent))
        pi_gs = max_obs * 1.05 if np.isfinite(max_obs) else 1000.0

    # Layout 2x1 vertical (single-column IEEE): panel (a) arriba, (b) abajo
    fig, axes = plt.subplots(2, 1, figsize=(WIDTH_SINGLE_IN, 4.4),
                              sharex=True)

    # Definicion de los dos grupos
    PANEL_A_BUYERS = ["Cesmag", "Mariana", "HUDN"]
    PANEL_B_BUYERS = ["UCC", "Udenar"]
    LINESTYLES_BUYER = ["-", "--", "-."]
    MARKERS_BUYER    = ["D", "s", "^"]

    def _draw_panel(ax, buyer_names, panel_label, panel_subtitle):
        # PV inactive bands
        ax.axvspan(-0.5, 5.5, color="#cccccc", alpha=0.22, zorder=0)
        ax.axvspan(17.5, 23.5, color="#cccccc", alpha=0.22, zorder=0)

        # Filter to agents present + with data
        active = [name for name in buyer_names
                  if name in agents and buyer_hours[agents.index(name)] > 0]
        n_panel = len(active)
        x_jitter = 0.25 if n_panel > 1 else 0.0
        x_step = (2 * x_jitter / (n_panel - 1)) if n_panel > 1 else 0.0
        plotted = []

        for k, name in enumerate(active):
            n = agents.index(name)
            color  = COLORS_AGENT[n % len(COLORS_AGENT)]
            ls     = LINESTYLES_BUYER[k % len(LINESTYLES_BUYER)]
            marker = MARKERS_BUYER[k % len(MARKERS_BUYER)]
            share = 100.0 * buyer_hours[n] / n_active
            x_offset = (k - (n_panel - 1) / 2.0) * x_step
            x_jit = h_day + x_offset
            ax.plot(x_jit, med_per_agent[n], marker=marker,
                    color=color, linewidth=1.0, markersize=2.8,
                    linestyle=ls, alpha=0.85,
                    markeredgecolor="white", markeredgewidth=0.4,
                    label=rf"{name} ({share:.0f}%)",
                    zorder=3 + k)
            plotted.append(n)

        # Cotas admisibles
        ax.axhline(pi_gb, color="gray", linestyle="--", linewidth=0.7, zorder=2)
        ax.axhline(pi_gs, color="gray", linestyle="--", linewidth=0.7, zorder=2)

        ax.set_xticks(np.arange(0, 24, 6))
        ax.set_xlim(-0.5, 23.5)
        ax.tick_params(labelsize=6.0)
        ax.set_title(rf"{panel_label} {panel_subtitle}",
                     fontsize=7.5, fontweight="bold", pad=2)
        ax.legend(loc="upper right", fontsize=5.5, framealpha=0.9,
                  frameon=False, ncol=1, handlelength=1.2,
                  handletextpad=0.4)
        ax.set_ylabel(r"$\pi^*_n$ (COP/kWh)", fontsize=7)
        return plotted

    plotted_a = _draw_panel(axes[0], PANEL_A_BUYERS,
                              "(a)", "Representative")
    # Cotas labels SOLO panel (a)
    x_lab = 23.0
    band = pi_gs - pi_gb
    axes[0].text(x_lab, pi_gs - 0.04 * band,
                 rf"$\pi_{{gs}}={pi_gs:.0f}$",
                 fontsize=5.5, color="#444444", va="top", ha="right",
                 fontstyle="italic",
                 bbox=dict(boxstyle="round,pad=0.12",
                           facecolor="white", edgecolor="#aaaaaa",
                           lw=0.3, alpha=0.9))
    axes[0].text(x_lab, pi_gb + 0.06 * band,
                 rf"$\pi_{{gb}}={pi_gb:.0f}$",
                 fontsize=5.5, color="#444444", va="bottom", ha="right",
                 fontstyle="italic",
                 bbox=dict(boxstyle="round,pad=0.12",
                           facecolor="white", edgecolor="#aaaaaa",
                           lw=0.3, alpha=0.9))

    plotted_b = _draw_panel(axes[1], PANEL_B_BUYERS,
                              "(b)", "Mixed/sparse")
    axes[1].set_xlabel("Hour of day", fontsize=7)

    # Suptitle compacto
    fig.suptitle("Per-buyer cleared price by hour",
                 fontsize=8.5, fontweight="bold", y=0.99)

    fig.subplots_adjust(top=0.93, bottom=0.10, left=0.16, right=0.97,
                         hspace=0.32)

    # CSV: una columna por TODOS los agentes con datos + community avg
    df_data = {"hour_of_day": h_day, "community_median_COP_kWh": med_avg}
    for n in range(N):
        if buyer_hours[n] > 0:
            df_data[f"median_{agents[n]}"] = med_per_agent[n]
    pd.DataFrame(df_data).to_csv(str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path)))


# ── Fig paper: hourly KPIs (SC / SS / IE) ────────────────────────────────────

def fig_paper_metrics_hourly(p2p_results, D, G_klim, out_path: Path) -> Path:
    """Hourly community KPIs (SC, SS, IE) aggregated by hour-of-day.

    Reading 2026-05-04 (paper review):
      - Filter to ACTIVE hours only (drop 552/744 h with KPI=0 that pollute
        the figure with vertical streaks).
      - Aggregate by hour-of-day (0-23) — median + IQR shaded band.
      - Y-axis [0, 1] (drop unused negative space).
      - Audit-style suptitle (case study), italic orange key message,
        italic blue footer KPI.

    SC = Self-Consumption (PV retained locally / generated)
    SS = Self-Sufficiency  (demand met locally / total demand)
    IE = Index of Equity   (seller-buyer balance, Chacon)
    """
    apply_ieee_style()
    T = len(p2p_results)
    SC = np.clip(np.array([r.SC for r in p2p_results]), -1.0, 1.0)
    SS = np.clip(np.array([r.SS for r in p2p_results]), -1.0, 1.0)
    IE = np.clip(np.array([r.IE for r in p2p_results]), -1.0, 1.0)

    # Active mask: hours where market actually traded
    active = np.array([
        (r.P_star is not None and float(np.sum(r.P_star)) > 1e-4)
        for r in p2p_results
    ])
    n_active = int(active.sum())
    pct_active = 100.0 * n_active / max(T, 1)

    hours = np.arange(T)
    hod = hours % 24  # 0..23

    def _agg(metric):
        med = np.full(24, np.nan)
        p25 = np.full(24, np.nan)
        p75 = np.full(24, np.nan)
        for h in range(24):
            mask = active & (hod == h)
            if mask.any():
                vals = metric[mask]
                med[h] = float(np.nanmedian(vals))
                p25[h] = float(np.nanpercentile(vals, 25))
                p75[h] = float(np.nanpercentile(vals, 75))
        return med, p25, p75

    SC_med, SC_p25, SC_p75 = _agg(SC)
    SS_med, SS_p25, SS_p75 = _agg(SS)
    IE_med, IE_p25, IE_p75 = _agg(IE)

    SC_avg = float(np.nanmean(SC[active])) if n_active > 0 else 0.0
    SS_avg = float(np.nanmean(SS[active])) if n_active > 0 else 0.0
    IE_avg = float(np.nanmean(IE[active])) if n_active > 0 else 0.0

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 2.7))
    h_axis = np.arange(24)

    # Inactive (no-PV) bands gris claro: 18h-06h
    ax.axvspan(-0.5, 5.5, color="#cccccc", alpha=0.20, zorder=0)
    ax.axvspan(17.5, 23.5, color="#cccccc", alpha=0.20, zorder=0)

    series_def = [
        (SC_med, SC_p25, SC_p75, COLORS["P2P"],
         f"SC: {SC_avg*100:.0f}%"),
        (SS_med, SS_p25, SS_p75, COLORS["C1"],
         f"SS: {SS_avg*100:.0f}%"),
        (IE_med, IE_p25, IE_p75, COLORS["C4"],
         f"IE: +{IE_avg:.2f}"),
    ]
    for med, p25, p75, color, label in series_def:
        ax.fill_between(h_axis, p25, p75, color=color, alpha=0.18, zorder=1)
        ax.plot(h_axis, med, color=color, linewidth=1.2, marker='o',
                markersize=2.6, label=label,
                markeredgecolor="white", markeredgewidth=0.3, zorder=2)

    ax.set_ylim(0.0, 1.05)
    ax.set_xlim(-0.5, 23.5)
    ax.set_xticks(np.arange(0, 25, 6))
    ax.set_xlabel("Hour of day", fontsize=7.5)
    ax.set_ylabel("Index (p.u.)", fontsize=7.5)
    ax.tick_params(labelsize=6.5)

    # Anotación ★ sobre el valle SS (sin caja para ahorrar espacio)
    valley_h = int(np.nanargmin(SS_med))
    valley_v = float(SS_med[valley_h])
    ax.scatter([valley_h], [valley_v], s=40,
               facecolors="none", edgecolors="#C0651B",
               linewidth=1.0, zorder=5)

    ax.set_title("Hourly community KPIs by hour of day",
                 fontsize=8.5, fontweight="bold", pad=4)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18),
              ncol=3, fontsize=6.5, frameon=False,
              columnspacing=0.8, handletextpad=0.4)

    fig.subplots_adjust(top=0.91, bottom=0.20, left=0.13, right=0.98)

    df_out = pd.DataFrame({
        "hour_of_day": h_axis,
        "SC_median": SC_med, "SC_p25": SC_p25, "SC_p75": SC_p75,
        "SS_median": SS_med, "SS_p25": SS_p25, "SS_p75": SS_p75,
        "IE_median": IE_med, "IE_p25": IE_p25, "IE_p75": IE_p75,
    })
    df_out.to_csv(str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path), also_pdf=True))


# ── Fig paper: per-agent role classification heatmap ─────────────────────────

def fig_paper_classification(p2p_results, agents: list, out_path: Path) -> Path:
    """Per-agent role heatmap: seller / buyer / neutral by hour.

    Mejoras (revision 2026-05-04):
      - Suptitle con identificador del case study (MTE 744 h, phi=1.5).
      - Subtitle italic con insight clave (roles dinamicos, ciclo diurno).
      - Yticklabels enriquecidos con % horas como Buyer por agente.
      - Color Seller cambiado a dorado (#E8A33D) — evita colision con C1
        green usado en otras figuras.
      - Marcadores de semana (lineas verticales blancas cada 168 h).
      - Eje secundario superior con dia del mes (1..31).
      - Legend con anotacion "(none in this case study)" si neutral=0.

    Trazabilidad: Reunion 01/05 — paper IEEE WEEF.
    """
    import matplotlib.patches as mpatches
    import matplotlib.colors as mcolors

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

    # Conteos por agente (para enriquecer ytick labels)
    pct_buyer = np.zeros(N)
    pct_seller = np.zeros(N)
    pct_neutral = np.zeros(N)
    for n in range(N):
        pct_buyer[n]   = (roles[n] == -1.0).sum() / T * 100
        pct_seller[n]  = (roles[n] ==  1.0).sum() / T * 100
        pct_neutral[n] = (roles[n] ==  0.0).sum() / T * 100
    total_neutral_hours = int((roles == 0.0).sum())

    # Colores: seller dorado (PV surplus / sun), buyer azul (demand),
    # neutral gris claro. Evita usar el verde C1 para Seller.
    SELLER_COLOR = "#E8A33D"
    BUYER_COLOR  = "#378ADD"
    NEUTRAL_COLOR = "#E8E8E8"
    cmap = mcolors.ListedColormap([BUYER_COLOR, NEUTRAL_COLOR, SELLER_COLOR])
    norm = mcolors.BoundaryNorm([-1.5, -0.5, 0.5, 1.5], cmap.N)

    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 2.9))
    ax.pcolormesh(np.arange(T + 1), np.arange(N + 1), roles,
                  cmap=cmap, norm=norm, shading="flat", zorder=1)

    # Y-ticks: solo nombre (% buyer va al caption)
    ax.set_yticks(np.arange(N) + 0.5)
    ax.set_yticklabels(agents, fontsize=6.5)

    ax.set_xlim(0, T)
    ax.set_ylim(0, N)
    ax.invert_yaxis()

    # Bottom axis: ticks cada 5 dias, solo numero de dia (compacto)
    n_days = T // 24
    hour_ticks = np.arange(0, n_days + 1, 5) * 24
    hour_ticks = hour_ticks[hour_ticks <= T]
    day_labels = [
        f"D{int(h/24) + 1 if h < T else n_days}" for h in hour_ticks
    ]
    ax.set_xticks(hour_ticks)
    ax.set_xticklabels(day_labels, fontsize=6.5)
    ax.set_xticks(np.arange(0, T + 1, 24), minor=True)
    ax.tick_params(axis="x", which="minor", length=1.5, color="#999999")
    ax.set_xlabel("Day of horizon", fontsize=7.5, labelpad=2)

    # Sin twiny, sin annotation diurnal — el caption del paper lo describe
    ax.set_title(
        "Per-agent role classification by hour",
        fontsize=8.5, fontweight="bold", pad=4,
    )
    # (a) Subtitle italic naranja con metricas concretas
    avg_seller_pct = float(pct_seller.mean())

    # Legend compacta: 2 entries (Seller/Buyer); Neutral va al caption
    neutral_label = (
        "Neutral (none)" if total_neutral_hours == 0 else "Neutral"
    )
    patches = [
        mpatches.Patch(facecolor=SELLER_COLOR, label="Seller"),
        mpatches.Patch(facecolor=BUYER_COLOR,  label="Buyer"),
    ]
    if total_neutral_hours > 0:
        patches.append(
            mpatches.Patch(facecolor=NEUTRAL_COLOR,
                           edgecolor="#999999", linewidth=0.4,
                           label=neutral_label)
        )
    ax.legend(handles=patches, loc="upper center",
              bbox_to_anchor=(0.5, -0.20),
              ncol=len(patches), fontsize=6.5, frameon=False,
              columnspacing=0.8, handletextpad=0.4)

    fig.subplots_adjust(top=0.91, bottom=0.20, left=0.13, right=0.98)

    rows = {"hour": np.arange(T)}
    for n, name in enumerate(agents):
        rows[f"role_{name}"] = roles[n]
    pd.DataFrame(rows).to_csv(str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path), also_pdf=True))


# ── Fig paper: weekly welfare evolution per scenario ─────────────────────────

def fig_paper_subperiod(scenarios_data: dict, agents: list,
                         p2p_results, G_klim, out_path: Path) -> Path:
    """Weekly net-benefit evolution for P2P, C1, C2 over 744-hour horizon.

    Adapts fig16 to English + IEEE double-col. Weeks are 168-hour bins.

    Hybrid weekly attribution (refinement 2026-05-05):
      - P2P: ACTUAL hourly clearing summed per week (no attribution; we
        have hourly data from p2p_results). Baseline autoconsumption is
        added proportionally to weekly PV availability.
      - C1, C2: PV-weighted attribution of total benefit (settle monthly
        in reality, no real weekly settlement exists).

    This is more honest than uniform PV-attribution: P2P advantage shape
    reflects real hourly clearing, not just PV proxy.

    Redesign 2026-05-04 + 2026-05-05 (Brayan paper review):
      - Audit-style: case-study suptitle, italic orange key message,
        italic blue footer KPI, ★ on peak week.
      - fill_between P2P↔C1 (light blue alpha) — visualizes persistent
        advantage that drives the paper claim.
      - Holiday markers on W1 (Aug 7 Boyacá) and W3 (Aug 18 Asunción).

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

    def _weekly_attrib(per_agent_arr: np.ndarray) -> np.ndarray:
        """Weekly via PV-weighted attribution (for C1/C2 monthly settlement)."""
        total = float(np.asarray(per_agent_arr, dtype=float).sum())
        return total * weights / 1e3  # kCOP

    # Compute REAL hourly P2P revenue (when p2p_results is real, not stubs)
    has_real_p2p = any(
        r is not None and getattr(r, "pi_star", None) is not None
        for r in p2p_results
    )
    p2p_weekly_real_kCOP = None
    if has_real_p2p:
        rev_per_hour_COP = np.zeros(T)
        for k, r in enumerate(p2p_results):
            if r is None or r.pi_star is None or r.P_star is None:
                continue
            kwh_per_buyer = np.sum(r.P_star, axis=0)  # (I,)
            rev_per_hour_COP[k] = float(np.dot(kwh_per_buyer, r.pi_star))
        p2p_weekly_revenue_kCOP = np.array([
            rev_per_hour_COP[w*week_size:(w+1)*week_size].sum() / 1e3
            for w in range(n_weeks)
        ])

    scenario_colors = {"P2P": COLORS["P2P"], "C1": COLORS["C1"], "C4": COLORS["C4"]}

    # Compute weekly series first (needed for fill_between)
    weekly_by_tag: dict[str, np.ndarray] = {}
    csv_rows: dict[str, np.ndarray] = {"week": np.array(week_labels)}
    label_by_tag: dict[str, str] = {}
    for key, (total, per_agent) in scenarios_data.items():
        if "P2P" in key:
            tag = "P2P"
        elif "C1" in key:
            tag = "C1"
        else:
            tag = "C4"
        # P2P: si tenemos hourly real, descomponer:
        #   weekly = (total - sum_revenue_real) * weights + revenue_real_per_week
        # baseline (autoconsumo + reventa grid) atribuido por PV;
        # P2P clearing surplus es real per-week (no atribuido).
        if tag == "P2P" and has_real_p2p:
            total_kCOP = float(np.asarray(per_agent, dtype=float).sum()) / 1e3
            real_revenue_total_kCOP = float(p2p_weekly_revenue_kCOP.sum())
            baseline_kCOP = total_kCOP - real_revenue_total_kCOP
            weekly = baseline_kCOP * weights + p2p_weekly_revenue_kCOP
        else:
            weekly = _weekly_attrib(per_agent)
        weekly_by_tag[tag] = weekly
        label_by_tag[tag] = key
        csv_rows[key] = weekly

    x = np.arange(n_weeks)
    # Single-column IEEE: figsize 3.5x2.7, ratio 1.30:1 (paper la incluye
    # con \includegraphics[width=0.48\textwidth] = ~3.4" rendered).
    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 2.7))

    # Sombreado Δ P2P-C1 (P2P advantage zone) — la tesis del paper
    if "P2P" in weekly_by_tag and "C1" in weekly_by_tag:
        ax.fill_between(x, weekly_by_tag["C1"], weekly_by_tag["P2P"],
                        color=COLORS["P2P"], alpha=0.13, zorder=1,
                        label=r"P2P advantage")

    # Lineas con orden C1, C2, P2P para que P2P quede arriba en la leyenda
    for tag in ("C1", "C4", "P2P"):
        if tag not in weekly_by_tag:
            continue
        # Etiqueta compacta para legend single-col (P2P / C1 / C2)
        short = {"P2P": "P2P", "C1": "C1 (CREG 174)", "C4": "C2 (CREG 101 072)"}[tag]
        ax.plot(x, weekly_by_tag[tag], "o-",
                color=scenario_colors[tag],
                linewidth=1.3, markersize=3.6,
                markeredgecolor="white", markeredgewidth=0.4,
                label=short, zorder=3)

    # ★ peak P2P
    peak_w = 0; peak_v = 0.0
    if "P2P" in weekly_by_tag:
        peak_w = int(np.argmax(weekly_by_tag["P2P"]))
        peak_v = float(weekly_by_tag["P2P"][peak_w])
        ax.plot([peak_w], [peak_v], marker="*", markersize=10,
                color=COLORS["P2P"], markeredgecolor="black",
                markeredgewidth=0.6, zorder=5, linestyle="none")

    # Compute y-range con padding mas alto arriba (legend externa va abajo)
    all_vals = np.concatenate(list(weekly_by_tag.values()))
    y_min = float(all_vals.min())
    y_max = float(all_vals.max())
    y_range = y_max - y_min
    ax.set_ylim(y_min - 0.06 * y_range, y_max + 0.10 * y_range)

    # Holiday markers en W1 (Aug 7 Boyaca) y W3 (Aug 18 Asuncion)
    holiday_weeks = {0: "Aug 7", 2: "Aug 18"}
    for w_idx, hday in holiday_weeks.items():
        if w_idx < n_weeks and "P2P" in weekly_by_tag:
            v = float(weekly_by_tag["P2P"][w_idx])
            ax.annotate("H",
                        xy=(w_idx, v),
                        xytext=(w_idx, v + 0.07 * y_range),
                        fontsize=5.5, color="#666666", fontweight="bold",
                        ha="center", va="center",
                        bbox=dict(boxstyle="circle,pad=0.10",
                                  facecolor="white", edgecolor="#888888",
                                  lw=0.4, alpha=0.92))

    ax.set_xticks(x)
    ax.set_xticklabels(week_labels, fontsize=7)
    ax.set_xlim(-0.55, n_weeks - 0.45)
    ax.set_ylabel("Net benefit per week (kCOP)", fontsize=7.5)
    ax.tick_params(axis="y", labelsize=7)
    ax.grid(True, alpha=0.25, linestyle=":", linewidth=0.5)

    # Legend ncol=2 abajo, sin tomar mucho espacio
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13),
              ncol=2, fontsize=6.5, framealpha=0.95,
              columnspacing=1.0, handletextpad=0.4,
              borderpad=0.3)

    # Suptitle compacto (sin key_msg ni footer azul — paper caption los explica)
    fig.suptitle("Weekly net benefit evolution",
                 fontsize=8.5, fontweight="bold", color="#222222",
                 y=0.985)

    fig.subplots_adjust(left=0.16, right=0.97, top=0.91, bottom=0.27)

    pd.DataFrame(csv_rows).to_csv(str(out_path) + ".csv", index=False)
    return Path(save_ieee(fig, str(out_path), also_pdf=True))


# ── Fig paper: C1 vs C4 per-agent bar chart ──────────────────────────────────

def fig_paper_c1_vs_c4_detailed(scenarios_data: dict, agents: list,
                                  out_path: Path) -> Path:
    """Grouped bar chart: C1 (CREG 174) vs C2 (CREG 101 072) per agent.

    Aisla la pregunta del Arc B del paper: ¿cual de las dos regulaciones
    existentes conviene mas, agente por agente? P2P queda fuera por diseño
    (ver `project_paper_c1_vs_c4_role.md`).

    Mejoras (revision 2026-05-04):
      - Suptitle con identificador del case study (consistencia visual).
      - Caja de agregado: C1 total / C2 total / winner aggregate.
      - Etiquetas de winner mas grandes (fontsize 7.5 bold) con caja.
      - Estilo: solid colors + edgecolor negro (consistente con audit).
      - Anotacion narrativa: por que cada uno gana segun cobertura PV.

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

    # Agregado (suma per-agent)
    c1_total = float(c1_arr.sum())
    c4_total = float(c4_arr.sum())
    agg_winner = "C1" if c1_total > c4_total else "C2"
    agg_delta = abs(c1_total - c4_total)
    agg_pct = (agg_delta / min(c1_total, c4_total)) * 100

    # Conteo de winners individuales
    n_c1_wins = int((c1_arr > c4_arr).sum())
    n_c2_wins = int((c4_arr > c1_arr).sum())

    x = np.arange(N)
    width = 0.38
    # Single-column IEEE: 3.5x2.9, ratio compacto.
    fig, ax = plt.subplots(figsize=(WIDTH_SINGLE_IN, 2.9))

    # Highlighting de los agentes donde C2 gana (paralelo al rectangulo
    # rojo del calibration_robustness y a los axvspan del chacon).
    for n in range(N):
        if c4_arr[n] > c1_arr[n]:
            ax.axvspan(
                n - 0.45, n + 0.45,
                alpha=0.10, color=COLORS["C4"], zorder=0,
            )

    bars_c1 = ax.bar(
        x - width / 2, c1_arr, width, label="C1 (CREG 174)",
        color=COLORS["C1"], edgecolor="black", linewidth=0.6, zorder=3,
    )
    bars_c2 = ax.bar(
        x + width / 2, c4_arr, width, label="C2 (CREG 101 072)",
        color=COLORS["C4"], edgecolor="black", linewidth=0.6, zorder=3,
    )

    # Valor numerico DENTRO de cada barra (white bold, vertical)
    for bar_set in (bars_c1, bars_c2):
        for bar in bar_set:
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2, h - 50,
                f"{h:.0f}",
                ha="center", va="top", fontsize=5.5, fontweight="bold",
                color="white",
            )

    # Etiquetas de winner sobre cada par (compactas)
    y_top = max(c1_arr.max(), c4_arr.max())
    for n in range(N):
        top = max(c1_arr[n], c4_arr[n])
        delta = abs(c1_arr[n] - c4_arr[n])
        winner = "C1" if c1_arr[n] >= c4_arr[n] else "C2"
        winner_color = COLORS["C1"] if winner == "C1" else COLORS["C4"]
        ax.text(
            n, top + y_top * 0.03,
            f"+{delta:.0f}k",
            ha="center", va="bottom", fontsize=6, fontweight="bold",
            color=winner_color,
            bbox=dict(facecolor="white", edgecolor=winner_color,
                       boxstyle="round,pad=0.18", linewidth=0.5, alpha=0.95),
        )

    ax.axhline(0.0, color="black", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(agents, fontsize=7)
    ax.set_ylabel("Net benefit (kCOP)", fontsize=7.5)
    ax.tick_params(axis="y", labelsize=6.5)
    ax.yaxis.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.set_ylim(top=y_top * 1.18)

    ax.set_title(
        "C1 (CREG 174) vs C2 (CREG 101 072) per agent",
        fontsize=8.5, fontweight="bold", pad=4,
    )

    # Legenda al pie con 2 entradas (highlight zone va al caption)
    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor=COLORS["C1"], edgecolor="black", linewidth=0.5,
               label="C1 (CREG 174)"),
        Patch(facecolor=COLORS["C4"], edgecolor="black", linewidth=0.5,
               label="C2 (CREG 101 072)"),
    ]
    ax.legend(
        handles=handles,
        loc="upper center", bbox_to_anchor=(0.5, -0.16),
        ncol=2, fontsize=6.5, frameon=False,
        columnspacing=0.8, handletextpad=0.4,
    )
    fig.subplots_adjust(top=0.91, bottom=0.18, left=0.13, right=0.98)

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

        # Hora real del case study (Aug 2025 + h0512 → Aug 22, 08:00)
        day_of_month = cd.hour // 24 + 1
        hour_of_day  = cd.hour % 24

        # IEEE single-column: 3 paneles apilados verticalmente (3x1).
        fig = plt.figure(figsize=(WIDTH_SINGLE_IN, 6.2))
        gs = fig.add_gridspec(
            3, 1, hspace=0.65,
            height_ratios=[1.0, 1.0, 1.0],
        )

        # Discrete welfare arrays (always computed, used in legacy CSV fallback)
        iters    = np.arange(1, n_iters + 1)
        Wj_arr   = np.array([w[0] for w in cd.welfare_iters])
        Wi_arr   = np.array([w[1] for w in cd.welfare_iters])
        W_total  = Wj_arr + Wi_arr
        has_coupled = (cd.coupled_t is not None and cd.coupled_W_t is not None)

        # ── (a) Aggregate welfare evolution — coupled-ODE continuous trajectory ─
        # Matching Chacon Fig 10a/11a: continuous welfare W(t) over Time (s).
        # If coupled-ODE data not available (older runs), fallback to discrete
        # Stackelberg-iteration view.
        ax_w = fig.add_subplot(gs[0, 0])  # Panel (a): top row (full width)
        if has_coupled:
            t_s = cd.coupled_t
            ax_w.plot(t_s, cd.coupled_Wj_t, "-", color=COLORS["C4"], lw=1.0,
                      label=r"$W_j$")
            ax_w.plot(t_s, cd.coupled_Wi_t, "-", color="#378ADD", lw=1.0,
                      label=r"$W_i$")
            ax_w.plot(t_s, cd.coupled_W_t,  "-", color=COLORS["P2P"], lw=1.4,
                      label=r"$W$")
            # Linea horizontal en cero como referencia visual del bienestar
            ax_w.axhline(0.0, color="#bbbbbb", lw=0.6, ls="-", alpha=0.7,
                         zorder=1)
            ax_w.axhline(cd.coupled_W_t[-1], color=COLORS["P2P"],
                         lw=0.5, ls=":", alpha=0.6)

            # Convergence marker
            W_final = float(cd.coupled_W_t[-1])
            delta_W_total = float(np.abs(cd.coupled_W_t[-1]
                                         - cd.coupled_W_t[0]))
            t_conv = float(t_s[-1])
            if delta_W_total > 1e-6:
                threshold = 0.01 * delta_W_total
                conv_mask = np.abs(cd.coupled_W_t - W_final) < threshold
                idx_conv = (np.argmax(conv_mask)
                            if conv_mask.any() else len(t_s) - 1)
                t_conv = float(t_s[idx_conv])
                ax_w.axvline(t_conv, color="#333333", lw=0.9, ls="--",
                             alpha=0.85, zorder=4)

            # Caja compacta con converged time (deltas van al caption)
            info_text = (
                rf"Converged $t \approx {t_conv*1000:.1f}$ ms"
                "\n"
                rf"$W_\infty={W_final:.0f}$ COP"
            )
            ax_w.text(0.99, 0.04, info_text,
                      transform=ax_w.transAxes, ha="right", va="bottom",
                      fontsize=5.5, color="#1a1a1a",
                      bbox=dict(boxstyle="round,pad=0.20",
                                facecolor="white",
                                edgecolor="#555555", lw=0.5, alpha=0.96))

            ax_w.set_xlabel(r"Time $t$ (s)", fontsize=7)
            ax_w.set_ylabel("Welfare (COP)", fontsize=7)
            ax_w.tick_params(labelsize=6)
            ax_w.set_title("(a) Aggregate welfare evolution",
                            fontsize=7.5, pad=2)
            ax_w.set_xlim(t_s[0], t_s[-1])
            ax_w.legend(loc="center right",
                        bbox_to_anchor=(0.99, 0.55),
                        ncol=3, fontsize=5.5, frameon=True,
                        framealpha=0.92, edgecolor="#888888",
                        handlelength=1.2, handletextpad=0.4,
                        columnspacing=0.8)
        else:
            ax_w.plot(iters, Wj_arr, "o--", color=COLORS["C4"], lw=1.0,
                      markersize=2.6, label=r"$W_j$")
            ax_w.plot(iters, Wi_arr, "s--", color="#378ADD", lw=1.0,
                      markersize=2.6, label=r"$W_i$")
            ax_w.plot(iters, W_total, "D-", color=COLORS["P2P"], lw=1.4,
                      markersize=3.0, label=r"$W$")
            ax_w.axhline(W_total[-1], color=COLORS["P2P"], lw=0.5, ls=":",
                         alpha=0.6)
            ax_w.set_xlabel("Stackelberg iteration", fontsize=7)
            ax_w.set_ylabel("Welfare (COP)", fontsize=7)
            ax_w.tick_params(labelsize=6)
            ax_w.set_title(
                f"(a) Welfare conv. k={cd.hour} ({regime})",
                fontsize=7.5, pad=2,
            )
            ax_w.set_xticks(iters)
            ax_w.legend(loc="best", fontsize=5.5, frameon=False, ncol=3,
                         handlelength=1.2, handletextpad=0.4)

        # ── (b) Buyer price trajectories pi_i(t) — last RD loop ──────────────
        ax_pi = fig.add_subplot(gs[1, 0])  # Panel (b): middle row
        # Panel (b): prefer coupled trajectory when available
        if has_coupled:
            t_pi  = cd.coupled_t
            pi_xy = cd.coupled_pi_t
        else:
            t_pi  = cd.t_buyers
            pi_xy = cd.pi_traj

        if pi_xy.size > 0 and t_pi.size > 0:
            for i in range(I):
                bid = cd.buyer_ids[i]
                bname = agents[bid] if bid < len(agents) else f"B{bid}"
                ax_pi.plot(t_pi, pi_xy[i, :],
                           color=COLORS_AGENT[i % len(COLORS_AGENT)],
                           lw=1.0, label=rf"$\pi_{{{bname}}}$")
            from core.replicator_buyers import PGB as _PGB_DEF
            from core.replicator_buyers import PGS as _PGS_DEF
            pgb_eff = float(cd.pi_gb) if cd.pi_gb is not None else _PGB_DEF
            pgs_eff = float(cd.pi_gs) if cd.pi_gs is not None else _PGS_DEF
            ax_pi.axhline(pgs_eff, color="#888888", lw=0.5, ls="--", alpha=0.7)
            ax_pi.axhline(pgb_eff, color="#888888", lw=0.5, ls="--", alpha=0.7)
            # Labels compactos sin caja (espacio reducido)
            x_label = t_pi[0] + 0.97 * (t_pi[-1] - t_pi[0])
            band = max(1.0, pgs_eff - pgb_eff)
            ax_pi.text(
                x_label, pgs_eff - 0.04 * band,
                rf"$\pi_{{gs}}={pgs_eff:.0f}$",
                fontsize=5.5, color="#444444", va="top", ha="right",
                fontstyle="italic",
            )
            ax_pi.text(
                x_label, pgb_eff + 0.06 * band,
                rf"$\pi_{{gb}}={pgb_eff:.0f}$",
                fontsize=5.5, color="#444444", va="bottom", ha="right",
                fontstyle="italic",
            )
            ax_pi.set_xlabel(r"Time $t$ (s)", fontsize=7)
            ax_pi.set_ylabel(r"$\pi_i(t)$ (COP/kWh)", fontsize=7)
            ax_pi.tick_params(labelsize=6)
            ax_pi.set_title(r"(b) Buyer prices $\pi_i(t)$",
                             fontsize=7.5, pad=2)
            ax_pi.legend(loc="best", fontsize=5.5, frameon=False,
                         ncol=min(I, 3), handlelength=1.2,
                         handletextpad=0.4)
        else:
            ax_pi.text(0.5, 0.5, "no trajectory captured",
                       ha="center", va="center", transform=ax_pi.transAxes,
                       fontsize=6, color="#888888")

        # ── (c) Power exchange dynamics P_{ji}(t) ────────────────────────────
        ax_p = fig.add_subplot(gs[2, 0])  # Panel (c): bottom row
        if has_coupled:
            t_P  = cd.coupled_t
            P_xy = cd.coupled_P_t
        else:
            t_P  = cd.t_sellers
            P_xy = cd.P_traj

        # Codificacion compacta: SELLER -> color, BUYER -> linestyle
        BUYER_LINESTYLES = ["-", "--", ":", "-."]
        if P_xy.size > 0 and t_P.size > 0:
            seller_handles = []
            for j in range(J):
                sid = cd.seller_ids[j]
                sname = agents[sid] if sid < len(agents) else f"S{sid}"
                color_j = COLORS_AGENT[j % len(COLORS_AGENT)]
                for i in range(I):
                    style_i = BUYER_LINESTYLES[i % len(BUYER_LINESTYLES)]
                    ax_p.plot(t_P, P_xy[j, i, :],
                              color=color_j, lw=1.0, linestyle=style_i)
                seller_handles.append(
                    plt.Line2D([0], [0], color=color_j, lw=1.2,
                                label=sname)
                )
            buyer_handles = []
            for i in range(I):
                bid = cd.buyer_ids[i]
                bname = agents[bid] if bid < len(agents) else f"B{bid}"
                style_i = BUYER_LINESTYLES[i % len(BUYER_LINESTYLES)]
                buyer_handles.append(
                    plt.Line2D([0], [0], color="#444444", lw=1.2,
                                linestyle=style_i,
                                label=rf"$\to${bname}")
                )
            ax_p.set_xlabel(r"Time $t$ (s)", fontsize=7)
            ax_p.set_ylabel(r"$P_{ji}(t)$ (kW)", fontsize=7)
            ax_p.tick_params(labelsize=6)
            ax_p.set_title(r"(c) Power flows $P_{ji}(t)$",
                            fontsize=7.5, pad=2)
            leg_handles = seller_handles + buyer_handles
            ax_p.legend(handles=leg_handles, loc="upper center",
                         bbox_to_anchor=(0.5, -0.32),
                         ncol=J + I, fontsize=5.0, frameon=False,
                         columnspacing=0.6, handlelength=1.2,
                         handletextpad=0.3)
        else:
            ax_p.text(0.5, 0.5, "no trajectory captured",
                       ha="center", va="center", transform=ax_p.transAxes,
                       fontsize=6, color="#888888")

        # Final equilibrium scalars — usados en el subtitle naranja
        if has_coupled:
            P_final  = cd.coupled_P_t[:, :, -1]
            pi_final = cd.coupled_pi_t[:, -1]
        else:
            P_final  = cd.P_star_iters[-1]
            pi_final = cd.pi_star_iters[-1]

        # Suptitle compacto (sin sub_metric — al caption del paper)
        regime_label = "surplus" if regime == "surplus" else "deficit"
        day_label  = f"{day_of_month:02d} Aug"
        clock_label = f"{hour_of_day:02d}:00"
        fig.suptitle(
            f"P2P convergence k={cd.hour} ({day_label} {clock_label})",
            fontsize=8.5, fontweight="bold", y=0.99,
        )

        fig.subplots_adjust(top=0.95, bottom=0.06, left=0.16, right=0.97,
                             hspace=0.65)

        # Per-hour CSV — usar coupled-ODE traj cuando esté disponible
        path_no_ext = f"{out_path_prefix}_h{cd.hour:04d}"
        if has_coupled:
            csv_df = pd.DataFrame({
                "t_seconds": cd.coupled_t,
                "W_j":       cd.coupled_Wj_t,
                "W_i":       cd.coupled_Wi_t,
                "W_total":   cd.coupled_W_t,
            })
        else:
            csv_df = pd.DataFrame({
                "iteration": iters,
                "W_j":       Wj_arr,
                "W_i":       Wi_arr,
                "W_total":   W_total,
            })
        csv_df.to_csv(path_no_ext + ".csv", index=False)
        saved.append(Path(save_ieee(fig, path_no_ext, also_pdf=True)))

    return saved


# ── Fig paper: Price of Fairness analysis (Bertsimas et al. 2011) ────────────

def fig_paper_price_of_fairness(scenarios_data: dict, agents: list,
                                 out_path: Path) -> Path:
    """Three-panel paper-spec PoF analysis for P2P / C1 / C2.

    Adapts plot_fig20_price_of_fairness (visualization/plots.py:2075) to
    English + IEEE double-column. Computes Gini per scenario and the
    Price of Fairness PoF = (W_eff - W_fair) / |W_eff| using the formal
    definition of Bertsimas, Farias & Trichakis (2011, Op. Res. 59:1).

    Panels:
      (a) Total welfare per scenario (kCOP) — efficient (max W) bar
          highlighted with thick black edge + "eff" label.
      (b) Gini index per scenario (lower = fairer) — equitable (min Gini)
          bar highlighted with thick black edge + "fair" label.
      (c) Per-agent sacrifice PoF_n — outlier (Cesmag) highlighted with
          axvspan + ★ marker, paralelo al patron de per_agent_benefit.

    Redesign 2026-05-05 (Brayan paper review):
      - Audit-style: case-study title peso normal, orange key msg italic,
        blue footer italic, in-bar "eff"/"fair" labels with bbox.
      - Cesmag outlier explicitamente marcado en panel (c) — el agente
        que paga 68% del sacrificio comunitario (vs 1-2% otros).
      - Footer conecta con per_agent_benefit: mismo Cesmag = "P2P star".

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

    # Indices de eff/fair scenarios para highlight
    eff_idx = keys.index(fr.eff_scenario) if fr.eff_scenario in keys else None
    fair_idx = (keys.index(fr.fair_scenario)
                if fr.fair_scenario in keys else None)

    # Single-column IEEE: gridspec 2x2 — (a) y (b) lado a lado en row 1,
    # (c) full-width en row 2 (mas espacio para etiquetas rotadas).
    fig = plt.figure(figsize=(WIDTH_SINGLE_IN, 4.6))
    gs = fig.add_gridspec(2, 2, hspace=0.55, wspace=0.42,
                           height_ratios=[1.0, 1.1])
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, :])
    axes = [ax_a, ax_b, ax_c]

    # ── (a) Total welfare per scenario ───────────────────────────────────────
    ax = axes[0]
    x = np.arange(len(keys))
    edge_widths_a = [1.2 if i == eff_idx else 0.5 for i in range(len(keys))]
    bars = ax.bar(x, totals_kcop,
                  color=[_color_for(k) for k in keys],
                  alpha=0.92,
                  edgecolor=["black" if i == eff_idx else "white"
                              for i in range(len(keys))],
                  linewidth=edge_widths_a)
    for b, v in zip(bars, totals_kcop):
        ax.text(b.get_x() + b.get_width() / 2,
                b.get_height() + max(totals_kcop) * 0.02,
                f"{v:.0f}", ha="center", va="bottom",
                fontsize=5.5, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.12", facecolor="white",
                          edgecolor="#888", lw=0.3, alpha=0.85))
    if eff_idx is not None:
        ax.text(eff_idx, totals_kcop[eff_idx] * 0.5, "eff",
                ha="center", va="center",
                fontsize=6.5, fontweight="bold",
                color=_color_for(keys[eff_idx]),
                bbox=dict(boxstyle="round,pad=0.15",
                          facecolor="white",
                          edgecolor=_color_for(keys[eff_idx]),
                          lw=0.5, alpha=0.92))
    ax.set_xticks(x)
    short_keys = [k.split(" ")[0] for k in keys]  # P2P, C1, C2
    ax.set_xticklabels(short_keys, fontsize=6.5)
    ax.set_ylabel("Welfare (kCOP)", fontsize=7)
    ax.tick_params(axis="y", labelsize=6)
    ax.set_title("(a) Total welfare", fontsize=7.5, pad=2)
    ax.set_ylim(0, max(totals_kcop) * 1.15)
    ax.yaxis.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)

    # ── (b) Gini index per scenario ──────────────────────────────────────────
    ax = axes[1]
    gini_vals = np.array([gini[k] for k in keys])
    edge_widths_b = [1.2 if i == fair_idx else 0.5 for i in range(len(keys))]
    bars = ax.bar(x, gini_vals,
                  color=[_color_for(k) for k in keys],
                  alpha=0.92,
                  edgecolor=["black" if i == fair_idx else "white"
                              for i in range(len(keys))],
                  linewidth=edge_widths_b)
    for b, v in zip(bars, gini_vals):
        ax.text(b.get_x() + b.get_width() / 2,
                b.get_height() + max(gini_vals) * 0.02,
                f"{v:.3f}", ha="center", va="bottom",
                fontsize=5.5, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.12", facecolor="white",
                          edgecolor="#888", lw=0.3, alpha=0.85))
    if fair_idx is not None:
        ax.text(fair_idx, gini_vals[fair_idx] * 0.5, "fair",
                ha="center", va="center",
                fontsize=6.5, fontweight="bold",
                color=_color_for(keys[fair_idx]),
                bbox=dict(boxstyle="round,pad=0.15",
                          facecolor="white",
                          edgecolor=_color_for(keys[fair_idx]),
                          lw=0.5, alpha=0.92))
    ax.set_xticks(x)
    ax.set_xticklabels(short_keys, fontsize=6.5)
    ax.set_ylabel("Gini", fontsize=7)
    ax.tick_params(axis="y", labelsize=6)
    ax.set_title("(b) Inequity", fontsize=7.5, pad=2)
    ax.set_ylim(0, max(gini_vals) * 1.18)
    ax.yaxis.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)

    # ── (c) Per-agent sacrifice PoF_n ────────────────────────────────────────
    ax = axes[2]
    pof_n = np.asarray(fr.pof_per_agent, dtype=float)
    cesmag_share_pct = 0.0
    outlier_n = None
    if pof_n.size == len(agents) and pof_n.size > 0:
        # Identifica outlier (max sacrifice)
        outlier_n = int(np.argmax(pof_n))
        outlier_val = float(pof_n[outlier_n])
        total_loss = float(pof_n.sum())
        cesmag_share_pct = 100.0 * outlier_val / total_loss if total_loss > 0 else 0.0

        xa = np.arange(len(agents))

        # axvspan amber-neutral en outlier — distinto de C2 pink
        # (este highlight es por sacrificio, no por preferencia C2)
        OUTLIER_AMBER = "#F4A340"
        ax.axvspan(outlier_n - 0.45, outlier_n + 0.45,
                   alpha=0.18, color=OUTLIER_AMBER, zorder=0)

        ax.bar(xa, pof_n, color="#7F77DD", alpha=0.92,
               edgecolor="black", linewidth=0.5, zorder=3)
        for n, v in enumerate(pof_n):
            is_outlier = (n == outlier_n)
            star = r"$\bigstar$ " if is_outlier else ""
            color_v = "#C0651B" if is_outlier else "#222222"
            edge = "#C0651B" if is_outlier else "#888"
            ax.text(n, v + max(pof_n) * 0.02,
                    f"{star}{v:.2f}",
                    ha="center", va="bottom",
                    fontsize=5.5, fontweight="bold", color=color_v,
                    bbox=dict(boxstyle="round,pad=0.12",
                              facecolor="white",
                              edgecolor=edge, lw=0.4, alpha=0.9))
        ax.set_xticks(xa)
        ax.set_xticklabels(agents, rotation=20, ha="right", fontsize=6.5)
        ax.set_ylabel(r"$\mathrm{PoF}_n$", fontsize=7)
        ax.tick_params(axis="y", labelsize=6)
        eff_short = fr.eff_scenario.split(" ")[0]
        fair_short = fr.fair_scenario.split(" ")[0]
        ax.set_title(rf"(c) Per-agent sacrifice ({eff_short} $\to$ {fair_short})",
                     fontsize=7.5, pad=2)
        ax.set_ylim(0, max(pof_n) * 1.20)
        ax.yaxis.grid(True, alpha=0.3, linewidth=0.5)
        ax.set_axisbelow(True)
    else:
        ax.text(0.5, 0.5, "PoF n/a (eff = fair)", ha="center", va="center",
                transform=ax.transAxes, fontsize=6, color="#888888")
        ax.set_axis_off()

    fig.suptitle(
        "Price of Fairness",
        fontsize=8.5, y=0.99, fontweight="bold",
    )

    fig.subplots_adjust(top=0.93, bottom=0.10, left=0.13, right=0.97,
                         hspace=0.55, wspace=0.42)

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
