"""
visualization/paper_figures/monthly_vs_hourly.py
Settlement granularity contrast: regulated (monthly) vs P2P (hourly).
Uses REAL case study data (MTE 744 h, phi=1.5, August 2025) — no synthetic.

Trazabilidad: Reunion 01/05 con asesores Pantoja + Obando.
Act 4.2 (paper IEEE WEEF). Redesign 2026-05-04 — Brayan paper review:
  - Real cumulative kWh from p2p_results en panel (a).
  - Real median pi*(k) per hour-of-day en panel (b).
  - C4 -> C2 (CREG 101 072) renaming.
  - Audit-style cosmetics: case-study suptitle, italic orange key message,
    italic blue footer KPI, panel labels (a)/(b), pi_gb/pi_gs annotations.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from visualization.ieee_style import (
    apply_ieee_style, save_ieee, COLORS, set_column_width,
    WIDTH_SINGLE_IN,
)


def _load_real_data():
    """Run case study pipeline (MTE 744h, phi=1.5, Aug 2025)."""
    from scripts.run_paper_iter import (
        homogeneizar_a_comercial, cargar_mte_paper,
        setup_parametros, correr_p2p,
    )
    homogeneizar_a_comercial()
    D, G, idx, agents = cargar_mte_paper("2025-08-01", "2025-09-01")
    G = G * 1.5  # phi case study
    p = setup_parametros(D, G, idx, agents)
    pi_gs_eff = float(np.median(p["pi_gs"]))
    pi_gb = 234.0  # XM floor (CREG 101 066 PES techo aplicado)
    p2p_results, _, _ = correr_p2p(D, G, agents, p["b_cal"], pi_gs_eff, pi_gb)
    return p2p_results, pi_gs_eff, pi_gb


def _build_panel_a(ax: plt.Axes, kwh_per_hour: np.ndarray,
                    pi_gb: float) -> tuple[float, float]:
    """Panel A: liquidacion mensual a precio regulado (pi_gb = bolsa floor)."""
    n_days = len(kwh_per_hour) // 24
    days = np.arange(1, n_days + 1)
    daily_kwh = kwh_per_hour[: n_days * 24].reshape(n_days, 24).sum(axis=1)
    cumulative = np.cumsum(daily_kwh)
    total_kwh = float(cumulative[-1])
    monthly_revenue_kCOP = total_kwh * pi_gb / 1000.0

    ax.fill_between(days, 0, cumulative,
                    color=COLORS["C1"], alpha=0.25,
                    label=f"kWh acc. -> {total_kwh:.0f}")
    ax.plot(days, cumulative, color=COLORS["C1"], linewidth=1.2)

    # Liquidation bar
    ax.bar(n_days + 0.6, total_kwh, width=2.4, color="#0E5F47", alpha=0.95,
           edgecolor="black", linewidth=0.7, zorder=4,
           label=f"Liquidation\n{monthly_revenue_kCOP:.0f} kCOP")
    ax.text(n_days + 0.6, total_kwh * 0.50, "LIQUID.",
            ha="center", va="center", rotation=90,
            fontsize=5.5, fontweight="bold", color="white", zorder=5)

    ax.axhline(y=total_kwh, color="gray", linestyle="--",
               linewidth=0.6, alpha=0.6)

    ax.set_xlim(0.5, n_days + 2.5)
    ax.set_ylim(0, total_kwh * 1.18)
    ax.set_ylabel("Cum. kWh", fontsize=7)
    ax.tick_params(labelsize=6)
    ax.set_title(rf"(a) Regulated (C1,C2): monthly $\pi_{{gb}}$={pi_gb:.0f}",
                 fontsize=7.5, pad=2)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(10))
    ax.legend(loc="upper left", fontsize=5.5, framealpha=0.95,
              handlelength=1.2, handletextpad=0.4)
    return total_kwh, monthly_revenue_kCOP


def _build_panel_b(ax: plt.Axes, pi_med_per_hod: np.ndarray,
                    pi_gb: float, pi_gs: float) -> tuple[int, float, float]:
    """Panel B: P2P hourly clearing — real median pi*(k) per hour-of-day."""
    hours = np.arange(24)
    valid = ~np.isnan(pi_med_per_hod)
    avg_pi = float(np.nanmean(pi_med_per_hod))

    ax.bar(hours[valid], pi_med_per_hod[valid], color=COLORS["P2P"],
           alpha=0.82, edgecolor="white", linewidth=0.3,
           label=r"$\pi^*_i(k)$")

    peak_h = int(hours[valid][np.nanargmax(pi_med_per_hod[valid])])
    peak_v = float(np.nanmax(pi_med_per_hod))
    ax.bar([peak_h], [peak_v], color=COLORS["P2P"],
           alpha=1.0, edgecolor="#C0651B", linewidth=1.0, zorder=3)

    ax.axhline(y=pi_gb, color="gray", linestyle="--", linewidth=0.7,
               label=rf"$\pi_{{gb}}\approx${pi_gb:.0f}")

    # Peak marker compacto (texto al caption del paper)
    ax.scatter([peak_h], [peak_v * 1.03], marker=(5, 1, 0),
               s=24, color="#C0651B", zorder=5)

    ax.set_xlim(-0.7, 23.7)
    ax.set_ylim(0, peak_v * 1.20)
    ax.set_xlabel("Hour of day", fontsize=7)
    ax.set_ylabel("Price [COP/kWh]", fontsize=7)
    ax.tick_params(labelsize=6)
    ax.set_title(rf"(b) P2P: hourly, peak h{peak_h:02d}={peak_v:.0f} "
                 rf"({peak_v / pi_gb:.1f}$\times$)",
                 fontsize=7.5, pad=2)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(6))
    ax.legend(loc="upper right", fontsize=5.5, framealpha=0.95,
              handlelength=1.2, handletextpad=0.4)
    return peak_h, peak_v, avg_pi


def main() -> None:
    apply_ieee_style()
    print("[B4] cargando datos reales del case study...")
    p2p_results, pi_gs, pi_gb = _load_real_data()

    # Panel A: kWh por hora -> cumulative diario
    kwh_per_hour = np.array([
        float(np.sum(r.P_star)) if r.P_star is not None else 0.0
        for r in p2p_results
    ])

    # Panel B: median pi*_i(k) por hour-of-day (volume-weighted across agents)
    pi_per_hod = [[] for _ in range(24)]
    for r in p2p_results:
        if r.pi_star is None or r.P_star is None:
            continue
        total_p = float(np.sum(r.P_star))
        if total_p > 1e-6:
            hod = r.k % 24
            w = np.sum(r.P_star, axis=0) / total_p  # peso por buyer
            pi_clear_hour = float(np.dot(w, r.pi_star))
            pi_per_hod[hod].append(pi_clear_hour)

    pi_med_per_hod = np.array([
        float(np.median(pi_per_hod[h])) if pi_per_hod[h] else np.nan
        for h in range(24)
    ])

    # Single-column IEEE: layout 2x1 vertical (stack)
    fig, (axA, axB) = plt.subplots(2, 1, figsize=(WIDTH_SINGLE_IN, 4.4))
    # Panel A usa pi_gb (floor regulado, lo que paga XM bajo CREG 174)
    total_kwh, monthly_kCOP = _build_panel_a(axA, kwh_per_hour, pi_gb)
    peak_h, peak_v, _ = _build_panel_b(axB, pi_med_per_hod, pi_gb, pi_gs)
    axA.set_xlabel("Day of August 2025", fontsize=7)

    # P2P revenue REAL: sum_k sum_i (kwh_per_buyer[i] * pi_star[i]) — volume-weighted
    p2p_revenue_total_COP = 0.0
    for r in p2p_results:
        if r.pi_star is not None and r.P_star is not None:
            kwh_per_buyer = np.sum(r.P_star, axis=0)  # (I,)
            p2p_revenue_total_COP += float(np.dot(kwh_per_buyer, r.pi_star))
    p2p_revenue_kCOP = p2p_revenue_total_COP / 1000.0
    # Volume-weighted avg = revenue/kwh (precio efectivo del mercado P2P)
    avg_pi = p2p_revenue_total_COP / total_kwh if total_kwh > 0 else 0.0
    gain_pct = 100.0 * (p2p_revenue_kCOP - monthly_kCOP) / monthly_kCOP if monthly_kCOP > 0 else 0

    # Suptitle compacto (case-study tag movido al caption del paper)
    fig.suptitle(
        "Settlement granularity: monthly vs hourly",
        fontsize=8.5, y=0.99, fontweight="bold",
    )

    ratio = peak_v / pi_gb if pi_gb > 0 else 0

    fig.subplots_adjust(top=0.93, bottom=0.10, left=0.16, right=0.97,
                         hspace=0.42)

    out = ROOT / "outputs" / "paper" / "fig_paper_monthly_vs_hourly"
    save_ieee(fig, str(out), dpi=300, also_pdf=True)
    print(f"[B4] saved {out}.png")
    print(f"[B4] saved {out}.pdf")
    print(f"[B4] total_kwh={total_kwh:.0f}, monthly_kCOP={monthly_kCOP:.0f}, "
          f"peak h{peak_h:02d}={peak_v:.0f}, avg_pi={avg_pi:.0f}, ratio={ratio:.2f}")


if __name__ == "__main__":
    main()
