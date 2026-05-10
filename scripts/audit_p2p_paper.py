"""
scripts/audit_p2p_paper.py — Sprint 6.6-A Fase B (auditoría P2P decomposition)
=================================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 4.1 + 4.2

Diagnostica la asimetría entre las fórmulas net_benefit de P2P, C1 y C2.

Imprime, por escenario y por agente:
  - Energía: E_auto, E_surplus_total, E_surplus_traded, E_surplus_residual,
            E_deficit
  - Monetario: R_auto, R_traded, R_residual, R_total_canonical,
              R_engine, delta
  - Reconciliación: el delta debe ser ~ pi_bolsa_mean × E_surplus_total
                    (evidencia de H1: residual surplus + base trade revenue
                     omitidos en _p2p_monetary_benefit).

Uso:
  python scripts/audit_p2p_paper.py
  python scripts/audit_p2p_paper.py --month 2025-08 --iters-sweep

Referencia: Documentos/audit_p2p_decomposition.md
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _wrap_stdout_utf8():
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                       encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer,
                                       encoding="utf-8", errors="replace")


def compute_p2p_energy_breakdown(p2p_results, D, G_klim, prosumer_ids):
    """Devuelve dicts con energía por agente: auto, traded_sold, traded_bought,
    surplus_total, residual, deficit."""
    N, T = D.shape
    e_auto = np.zeros(N)
    e_traded_sold = np.zeros(N)
    e_traded_bought = np.zeros(N)
    e_surplus_total = np.zeros(N)
    e_deficit = np.zeros(N)

    for n in prosumer_ids:
        for k in range(T):
            G_nk = max(G_klim[n, k], 0.0)
            D_nk = max(D[n, k], 0.0)
            e_auto[n] += min(G_nk, D_nk)
            e_surplus_total[n] += max(G_nk - D_nk, 0.0)
            e_deficit[n] += max(D_nk - G_nk, 0.0)

    for k_local, r in enumerate(p2p_results):
        if r.P_star is None:
            continue
        if np.isnan(r.P_star).any():
            continue
        for idx_j, j in enumerate(r.seller_ids or []):
            e_traded_sold[j] += float(np.sum(r.P_star[idx_j, :]))
        for idx_i, i in enumerate(r.buyer_ids or []):
            e_traded_bought[i] += float(np.sum(r.P_star[:, idx_i]))

    e_residual = np.maximum(e_surplus_total - e_traded_sold, 0.0)
    return {
        "E_auto": e_auto,
        "E_traded_sold": e_traded_sold,
        "E_traded_bought": e_traded_bought,
        "E_surplus_total": e_surplus_total,
        "E_residual": e_residual,
        "E_deficit": e_deficit,
    }


def compute_p2p_monetary_breakdown(p2p_results, D, G_klim, pi_gs_v, pi_gb,
                                     pi_bolsa, prosumer_ids):
    """Devuelve breakdown monetario por agente con la fórmula CANÓNICA y la
    del engine, más el delta (debe ser ~ pi_bolsa × surplus_total)."""
    N, T = D.shape
    R_auto = np.zeros(N)
    R_trade_full_seller = np.zeros(N)   # pi_star * P_sold (revenue completo)
    R_trade_premium_seller = np.zeros(N) # (pi_star - pi_gb) * P_sold (engine)
    R_buyer_savings = np.zeros(N)        # (pi_gs - pi_star) * P_bought
    R_buyer_paid = np.zeros(N)           # pi_star * P_bought (gasto comprador)

    for n in prosumer_ids:
        for k in range(T):
            G_nk = max(G_klim[n, k], 0.0)
            D_nk = max(D[n, k], 0.0)
            R_auto[n] += min(G_nk, D_nk) * float(pi_gs_v[n, k])

    for k_local, r in enumerate(p2p_results):
        if r.P_star is None or r.pi_star is None:
            continue
        if np.isnan(r.P_star).any() or np.isnan(r.pi_star).any():
            continue
        sids = r.seller_ids or []
        bids = r.buyer_ids or []
        pi_st = np.asarray(r.pi_star, dtype=float)
        P = np.asarray(r.P_star, dtype=float)
        for idx_j, j in enumerate(sids):
            sold = float(P[idx_j, :].sum())
            if sold > 1e-12:
                income = float(np.dot(pi_st, P[idx_j, :]))
                R_trade_full_seller[j] += income
                R_trade_premium_seller[j] += income - sold * pi_gb
        for idx_i, i in enumerate(bids):
            bought = float(P[:, idx_i].sum())
            if bought > 1e-12:
                pi_buy = float(pi_st[idx_i])
                pi_gs_ki = float(pi_gs_v[i, k_local])
                R_buyer_paid[i] += pi_buy * bought
                R_buyer_savings[i] += (pi_gs_ki - pi_buy) * bought

    # Residual surplus se asume vendido a pi_bolsa[k] (counterfactual de
    # comparison_engine implícito). Aproximación: pi_bolsa medio ponderado
    # por surplus residual horario (no tenemos breakdown horario del residual
    # por agente, así que usamos pi_bolsa promedio como proxy).
    energy = compute_p2p_energy_breakdown(p2p_results, D, G_klim, prosumer_ids)
    pi_bolsa_mean = float(np.nanmean(pi_bolsa))
    R_residual = energy["E_residual"] * pi_bolsa_mean

    # Net benefit canónico: ahorro_total - costo_post_solar (relativo a "sin solar").
    # Por agente (ya neto):
    #   net_canonico[n] = R_auto + R_trade_full_seller + R_residual
    #                     + R_buyer_savings    (compradores)
    # Donde R_buyer_savings = (pi_gs - pi_star) * P_bought.
    # NOTA: aquí NO sumamos R_auto + R_buyer_savings dos veces. Para un agente
    # que es comprador y prosumidor, R_auto es su autoconsumo propio, y
    # R_buyer_savings es el ahorro al comprar P2P en lugar de a la red.
    net_canonical = (R_auto + R_trade_full_seller + R_residual
                     + R_buyer_savings)
    net_engine = (R_auto + R_trade_premium_seller + R_buyer_savings)
    delta = net_canonical - net_engine

    return {
        "R_auto": R_auto,
        "R_trade_full_seller": R_trade_full_seller,
        "R_trade_premium_seller": R_trade_premium_seller,
        "R_buyer_savings": R_buyer_savings,
        "R_residual": R_residual,
        "net_canonical": net_canonical,
        "net_engine": net_engine,
        "delta": delta,
        "pi_bolsa_mean": pi_bolsa_mean,
    }


def imprimir_tabla(agents, energy, money, c1_per_agent, c4_per_agent,
                    prosumer_ids):
    """Imprime tabla compacta de auditoría (energía + monetario)."""
    print()
    print("=" * 90)
    print(" AUDITORÍA P2P decomposition — agosto 2025 (post-CAL-25..28)")
    print("=" * 90)

    print()
    print(" Energía por agente [kWh]")
    print(f" {'Agente':>10}  {'E_auto':>10}  {'E_surplus':>10}  "
          f"{'E_traded':>10}  {'E_residual':>11}  {'E_deficit':>10}")
    print(" " + "─" * 75)
    tot_E_auto = 0.0
    tot_E_surplus = 0.0
    tot_E_traded = 0.0
    tot_E_residual = 0.0
    tot_E_deficit = 0.0
    for n in prosumer_ids:
        print(f" {agents[n]:>10}  {energy['E_auto'][n]:>10.1f}  "
              f"{energy['E_surplus_total'][n]:>10.1f}  "
              f"{energy['E_traded_sold'][n]:>10.1f}  "
              f"{energy['E_residual'][n]:>11.1f}  "
              f"{energy['E_deficit'][n]:>10.1f}")
        tot_E_auto += energy['E_auto'][n]
        tot_E_surplus += energy['E_surplus_total'][n]
        tot_E_traded += energy['E_traded_sold'][n]
        tot_E_residual += energy['E_residual'][n]
        tot_E_deficit += energy['E_deficit'][n]
    print(" " + "─" * 75)
    print(f" {'TOTAL':>10}  {tot_E_auto:>10.1f}  {tot_E_surplus:>10.1f}  "
          f"{tot_E_traded:>10.1f}  {tot_E_residual:>11.1f}  "
          f"{tot_E_deficit:>10.1f}")

    print()
    print(" Monetario P2P [COP]")
    print(f" {'Agente':>10}  {'R_auto':>11}  {'R_trade_full':>12}  "
          f"{'R_residual':>12}  {'R_buyer_sav':>12}  {'NET_canon':>12}  "
          f"{'NET_engine':>12}  {'delta':>11}")
    print(" " + "─" * 105)
    tot_canon = 0.0
    tot_engine = 0.0
    tot_delta = 0.0
    for n in prosumer_ids:
        print(f" {agents[n]:>10}  {money['R_auto'][n]:>11,.0f}  "
              f"{money['R_trade_full_seller'][n]:>12,.0f}  "
              f"{money['R_residual'][n]:>12,.0f}  "
              f"{money['R_buyer_savings'][n]:>12,.0f}  "
              f"{money['net_canonical'][n]:>12,.0f}  "
              f"{money['net_engine'][n]:>12,.0f}  "
              f"{money['delta'][n]:>11,.0f}")
        tot_canon += money['net_canonical'][n]
        tot_engine += money['net_engine'][n]
        tot_delta += money['delta'][n]
    print(" " + "─" * 105)
    print(f" {'TOTAL':>10}  {money['R_auto'].sum():>11,.0f}  "
          f"{money['R_trade_full_seller'].sum():>12,.0f}  "
          f"{money['R_residual'].sum():>12,.0f}  "
          f"{money['R_buyer_savings'].sum():>12,.0f}  "
          f"{tot_canon:>12,.0f}  {tot_engine:>12,.0f}  {tot_delta:>11,.0f}")

    pi_bolsa_mean = money['pi_bolsa_mean']
    delta_predicted = pi_bolsa_mean * tot_E_surplus
    print()
    print(f" Verificación H1: delta total = {tot_delta:,.0f} COP")
    print(f"                  predicción ≈ pi_bolsa_mean × E_surplus_total = "
          f"{pi_bolsa_mean:.1f} × {tot_E_surplus:.1f} = {delta_predicted:,.0f}")
    if abs(tot_delta - delta_predicted) / max(abs(delta_predicted), 1.0) < 0.05:
        print(f"                  → MATCH (<5%): H1 confirmada empíricamente.")
    else:
        print(f"                  → diferencia >{5}%; revisar estimador residual.")

    # Comparación con C1/C2
    print()
    print(" Comparación NET por escenario [COP]")
    c1_total = sum(c1_per_agent[n]["net_benefit"] for n in c1_per_agent
                    if isinstance(n, int))
    c4_total = sum(c4_per_agent[n]["net_benefit"] for n in c4_per_agent
                    if isinstance(n, int))
    print(f"  P2P engine    : {tot_engine:>14,.0f} COP")
    print(f"  P2P canónico  : {tot_canon:>14,.0f} COP "
          f"(+{tot_delta:,.0f} vs engine)")
    print(f"  C1 (CREG 174) : {c1_total:>14,.0f} COP")
    print(f"  C2 (CREG 101 072): {c4_total:>14,.0f} COP")
    if tot_canon > c1_total:
        print(f"  → P2P canónico GANA contra C1 por {tot_canon - c1_total:,.0f} COP "
              f"({(tot_canon/c1_total - 1)*100:.1f}%)")
    else:
        print(f"  → P2P canónico PIERDE contra C1 por {c1_total - tot_canon:,.0f} COP "
              f"({(1 - tot_canon/c1_total)*100:.1f}%)")


def sanity_check_b(agents, b_cal, D):
    """Imprime ratio b/D.mean por agente para detectar miscalibración (H4)."""
    print()
    print(" Sanity check b vs D.mean (H4)")
    print(f" {'Agente':>10}  {'b_cal':>8}  {'D.mean':>8}  {'b/D.mean':>10}")
    print(" " + "─" * 45)
    for n, name in enumerate(agents):
        d_mean = float(D[n].mean())
        ratio = b_cal[n] / max(d_mean, 1e-6)
        flag = " ⚠" if (ratio < 0.5 or ratio > 5.0) else ""
        print(f" {name:>10}  {b_cal[n]:>8.2f}  {d_mean:>8.2f}  "
              f"{ratio:>10.2f}{flag}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--month", default="2025-08")
    ap.add_argument("--iters-sweep", action="store_true",
                    help="Barrer iters ∈ {2, 5, 10} para H3.")
    args = ap.parse_args()

    from scripts.run_paper_iter import (
        homogeneizar_a_comercial, horizonte_mensual, cargar_mte_paper,
        setup_parametros, correr_p2p, correr_c1, correr_c4,
    )
    from scenarios.scenario_c4_creg101072 import compute_pde_weights
    from scenarios._pi_gs import as_pi_gs_array

    print()
    print("=" * 78)
    print(f" AUDIT-P2P (Sprint 6.6-A Fase B)  mes={args.month}")
    print("=" * 78)

    homogeneizar_a_comercial()
    t_start, t_end = horizonte_mensual(args.month)
    D, G, idx, agents = cargar_mte_paper(t_start, t_end)
    p = setup_parametros(D, G, idx, agents)
    pi_gs_eff = float(np.nanmean(p["pi_gs"]))
    pi_gb = float(np.nanmean(p["pi_bolsa"]))
    prosumer_ids = list(range(D.shape[0]))

    print(f"\n  pi_gs_eff = {pi_gs_eff:.1f}, pi_gb = {pi_gb:.1f}")
    print(f"  D.shape = {D.shape}, agents = {agents}")

    sanity_check_b(agents, p["b_cal"], D)

    print(f"\n  Corriendo P2P + C1 + C4...")
    p2p_results, G_klim = correr_p2p(D, G, agents, p["b_cal"], pi_gs_eff, pi_gb)
    c1_per_agent = correr_c1(D, G_klim, p["pi_gs"], p["pi_bolsa"],
                              prosumer_ids, idx)
    capacity = np.maximum(G.mean(axis=1), 0)
    pde = compute_pde_weights(capacity, method="capacity_proportional")
    c4_result = correr_c4(D, G_klim, p["pi_gs"], p["pi_bolsa"],
                            pde, capacity, component_c="auto")

    pi_gs_v = as_pi_gs_array(p["pi_gs"], D.shape[0], D.shape[1])
    energy = compute_p2p_energy_breakdown(p2p_results, D, G_klim, prosumer_ids)
    money = compute_p2p_monetary_breakdown(
        p2p_results, D, G_klim, pi_gs_v, pi_gb, p["pi_bolsa"], prosumer_ids,
    )
    imprimir_tabla(agents, energy, money, c1_per_agent,
                    c4_result["per_agent"], prosumer_ids)

    if args.iters_sweep:
        print()
        print(" Sprint 6.6-A H3: convergencia iters")
        print(f" {'iters':>7}  {'NET_engine':>14}  {'NET_canon':>14}  {'horas activas':>13}")
        print(" " + "─" * 60)
        from core.ems_p2p import (EMSP2P, AgentParams, GridParams,
                                    SolverParams)
        N = D.shape[0]
        results_by_iter = {}
        for it in [2, 5, 10]:
            ap_pars = AgentParams(
                N=N, a=np.zeros(N), b=p["b_cal"], c=np.zeros(N),  # CAL-32 (2026-05-06b)
                lam=np.full(N, 100.0), theta=np.full(N, 0.5),
                etha=np.full(N, 0.1), alpha=np.zeros(N),
            )
            grid = GridParams(pi_gs=pi_gs_eff, pi_gb=pi_gb)
            solver = SolverParams(
                tau=0.001, t_span=(0.0, 0.005), n_points=150,
                stackelberg_iters=it, stackelberg_tol=1e-3,
                stackelberg_max=20, parallel=True,
            )
            ems = EMSP2P(ap_pars, grid, solver)
            p2p_it, G_klim_it, _ = ems.run(D, G)
            mny = compute_p2p_monetary_breakdown(
                p2p_it, D, G_klim_it, pi_gs_v, pi_gb, p["pi_bolsa"],
                prosumer_ids,
            )
            active = sum(1 for r in p2p_it
                          if r.P_star is not None and np.sum(r.P_star) > 1e-4)
            results_by_iter[it] = mny
            print(f" {it:>7}  {mny['net_engine'].sum():>14,.0f}  "
                  f"{mny['net_canonical'].sum():>14,.0f}  {active:>13}")

        # Comparar iters=2 vs iters=10
        if 2 in results_by_iter and 10 in results_by_iter:
            ne2 = results_by_iter[2]['net_engine'].sum()
            ne10 = results_by_iter[10]['net_engine'].sum()
            rel = abs(ne10 - ne2) / max(abs(ne2), 1.0)
            print(f"\n  |net(iters=10) - net(iters=2)| / |net(iters=2)| = {rel*100:.2f}%")
            if rel > 0.01:
                print(f"  → H3 CONFIRMADA: iters=2 no converge en este caso. "
                      f"Considerar default >=5 para paper.")
            else:
                print(f"  → H3 RECHAZADA: iters=2 converge bien (<1%).")

    return 0


if __name__ == "__main__":
    _wrap_stdout_utf8()
    sys.exit(main())
