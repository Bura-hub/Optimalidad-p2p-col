"""
smoke_settlement.py — EJE 1: reparto de beneficio P2P (R1-R6, ADR-0038)
========================================================================
Verifica las identidades contables del settlement P2P (CAL-29/30/35):

  R1 identidad_cal35        HARD  err rel ≤ 1e-9 (recomputación independiente
                                  por agente vs `_p2p_monetary_benefit`)
  R2 banda_precios          HARD  0 violaciones de banda y de techo per-cápita
  R3 conservacion_short_side HARD atol 1e-6 kWh (P_ext/P_int recomputados +
                                  short-side + balances)
  R4 demand_clearing        SOFT 2% / HARD 5% (= tolerancia del golden)
  R5 metricas_sanas         HARD  IE∈[−1,1], Gini∈[0,1], PS+PSR=100, sin NaN
  R6 dominancia_p2p_vs_c3   SOFT  neto P2P ≥ neto C3 por agente vendedor

Uso standalone:
    python scripts/smoke_settlement.py --datasets SYN [COB-M1 COB-M3] --tier N
"""
from __future__ import annotations

import argparse
import sys
import time

import numpy as np

from smoke_common import (
    CheckResult, ROOT, load_dataset, make_solver, run_ems_cached,
    active_hours, save_results, hard_failures, setup_stdout_utf8,
)
from core.settlement import gini_index
from scenarios.comparison_engine import (
    _p2p_monetary_benefit, _effective_buyer_prices,
)
from scenarios._pi_gs import as_pi_gs_array


def _recompute_net_independent(results, D, G_klim, pi_gs_matrix, pi_bolsa,
                               prosumer_ids):
    """Recomputación INDEPENDIENTE (vectorizada, orden de suma distinto)
    del beneficio canónico CAL-30/35 por agente, desde HourlyResults."""
    N, T = D.shape
    net = np.zeros(N)
    P_sold = np.zeros((N, T))
    for k, r in enumerate(results):
        if r.P_star is None or np.isnan(r.P_star).any():
            continue
        caps = pi_gs_matrix[r.buyer_ids, k]
        pi_eff = np.minimum(np.asarray(r.pi_star, dtype=float), caps)
        recv = r.P_star.sum(axis=0)                      # (I,)
        sold = r.P_star.sum(axis=1)                      # (J,)
        for idx_j, j in enumerate(r.seller_ids):
            net[j] += float(np.dot(pi_eff, r.P_star[idx_j, :]))
            P_sold[j, k] = sold[idx_j]
        for idx_i, i in enumerate(r.buyer_ids):
            net[i] += float((pi_gs_matrix[i, k] - pi_eff[idx_i]) * recv[idx_i])
    auto = np.minimum(np.maximum(G_klim, 0.0), np.maximum(D, 0.0))
    surplus = np.maximum(np.maximum(G_klim, 0.0) - np.maximum(D, 0.0), 0.0)
    residual = np.maximum(surplus - P_sold, 0.0)
    for n in prosumer_ids:
        net[n] += float(np.dot(auto[n], pi_gs_matrix[n]))
        net[n] += float(np.dot(residual[n], pi_bolsa))
    return net


def run_checks(tier: int, datasets: list) -> list:
    rows = []
    sv = make_solver()
    for ds_name in datasets:
        ds = load_dataset(ds_name)
        D, G = ds["D"], ds["G"]
        N, T = D.shape
        pi_gs_m = as_pi_gs_array(ds["pi_gs_matrix"], N, T)
        pi_gb = float(ds["grid"].pi_gb)
        pi_gs_game = float(ds["grid"].pi_gs)
        results, G_klim, _ = run_ems_cached(ds, sv)
        act = active_hours(results)
        print(f"  [{ds_name}] T={T}h, horas activas={len(act)}")

        # ── R1: identidad CAL-35 / recomputación independiente ───────────
        t0 = time.time()
        engine = _p2p_monetary_benefit(
            results, D, G_klim, pi_gs_m, pi_gb,
            ds["prosumer_ids"], pi_bolsa=ds["pi_bolsa"], mode="canonical")
        indep = _recompute_net_independent(
            results, D, G_klim, pi_gs_m, ds["pi_bolsa"], ds["prosumer_ids"])
        denom = np.maximum(np.abs(engine), 1.0)
        err_r1 = float(np.max(np.abs(engine - indep) / denom))
        # identidad por trade: vendedor+comprador = pi_gs[i,k]·P (exacta)
        max_tr = 0.0
        n_trades = 0
        for k in act:
            r = results[k]
            caps = pi_gs_m[r.buyer_ids, k]
            pi_eff = np.minimum(np.asarray(r.pi_star, dtype=float), caps)
            for idx_i in range(len(r.buyer_ids)):
                P_col = r.P_star[:, idx_i]
                mask = P_col > 1e-12
                n_trades += int(mask.sum())
                lhs = pi_eff[idx_i] * P_col[mask] + \
                    (caps[idx_i] - pi_eff[idx_i]) * P_col[mask]
                rhs = caps[idx_i] * P_col[mask]
                if mask.any():
                    max_tr = max(max_tr, float(np.max(
                        np.abs(lhs - rhs) / np.maximum(np.abs(rhs), 1e-12))))
        v1 = max(err_r1, max_tr)
        rows.append(CheckResult(
            "R1", "reparto", ds_name,
            "max err rel (motor vs indep; identidad/trade)",
            f"{v1:.2e} ({n_trades} trades)", "<=1e-9",
            "PASS" if v1 <= 1e-9 else "FAIL", tier, time.time() - t0))

        # ── R2: banda del juego + techo per-cápita CAL-35 ─────────────────
        t0 = time.time()
        viol_band = viol_cap = 0
        for k in act:
            r = results[k]
            tol_b = 1e-9 * pi_gs_game
            if np.any(r.pi_star < pi_gb - tol_b) or \
               np.any(r.pi_star > pi_gs_game + tol_b):
                viol_band += 1
            caps = pi_gs_m[r.buyer_ids, k]
            pi_eff = _effective_buyer_prices(r.pi_star, r.buyer_ids,
                                             pi_gs_m, k)
            if np.any(pi_eff > caps + 1e-9 * pi_gs_game):
                viol_cap += 1
        rows.append(CheckResult(
            "R2", "reparto", ds_name, "violaciones banda / techo",
            f"{viol_band} / {viol_cap}", "0 / 0",
            "PASS" if viol_band == 0 and viol_cap == 0 else "FAIL",
            tier, time.time() - t0))

        # ── R3: conservación / short-side / P_ext-P_int ───────────────────
        t0 = time.time()
        max_err_pe = max_err_pi = max_ss = 0.0
        for k in act:
            r = results[k]
            G_net = np.array([r.G_klim_k[j] - r.D_k[j] for j in r.seller_ids])
            D_net = np.array([r.D_k[i] - r.G_klim_k[i] for i in r.buyer_ids])
            sold = r.P_star.sum(axis=1)
            recv = r.P_star.sum(axis=0)
            pe = np.maximum(0.0, G_net - sold)
            pi_ = np.maximum(0.0, D_net - recv)
            if r.P_ext is not None:
                max_err_pe = max(max_err_pe,
                                 float(np.max(np.abs(pe - r.P_ext))))
            if r.P_int is not None:
                max_err_pi = max(max_err_pi,
                                 float(np.max(np.abs(pi_ - r.P_int))))
            short = min(float(np.sum(G_net)), float(np.sum(D_net)))
            max_ss = max(max_ss, float(np.sum(r.P_star)) - short)
        worst = max(max_err_pe, max_err_pi, max_ss)
        rows.append(CheckResult(
            "R3", "reparto", ds_name,
            "max err P_ext/P_int/short-side [kWh]",
            f"{worst:.2e}", "<=1e-6",
            "PASS" if worst <= 1e-6 else "FAIL", tier, time.time() - t0))

        # ── R4: demand clearing ───────────────────────────────────────────
        t0 = time.time()
        worst_rel = 0.0
        for k in act:
            r = results[k]
            D_net = np.array([r.D_k[i] - r.G_klim_k[i] for i in r.buyer_ids])
            recv = r.P_star.sum(axis=0)
            # solo compradores cuyo lado corto los puede atender
            G_tot = float(np.sum([r.G_klim_k[j] - r.D_k[j]
                                  for j in r.seller_ids]))
            if G_tot + 1e-9 < float(np.sum(D_net)):
                continue   # oferta insuficiente: el clearing total no aplica
            mask = D_net > 1e-6
            if mask.any():
                rel = np.abs(recv[mask] - D_net[mask]) / D_net[mask]
                worst_rel = max(worst_rel, float(np.max(rel)))
        verdict = ("PASS" if worst_rel <= 0.02 else
                   "WARN" if worst_rel <= 0.05 else "FAIL")
        rows.append(CheckResult(
            "R4", "reparto", ds_name, "max err rel clearing (oferta≥demanda)",
            f"{worst_rel:.4f}", "SOFT 2% / HARD 5%", verdict,
            tier, time.time() - t0))

        # ── R5: métricas sanas ────────────────────────────────────────────
        t0 = time.time()
        bad = []
        for k in act:
            r = results[k]
            if not (-1.0 - 1e-9 <= r.IE <= 1.0 + 1e-9):
                bad.append(f"IE h{k}={r.IE}")
            if not (abs(r.PS + r.PSR - 100.0) <= 1e-6 or
                    (r.PS == 50.0 and r.PSR == 50.0)):
                bad.append(f"PS+PSR h{k}={r.PS + r.PSR}")
            for v in (r.SC, r.SS, r.IE, r.Wj_total, r.Wi_total):
                if not np.isfinite(v):
                    bad.append(f"no-finito h{k}")
                    break
        g = gini_index(engine)
        if not (0.0 <= g <= 1.0):
            bad.append(f"Gini={g}")
        rows.append(CheckResult(
            "R5", "reparto", ds_name, "anomalías IE/Gini/PS+PSR/finitud",
            str(len(bad)), "0", "PASS" if not bad else "FAIL",
            tier, time.time() - t0,
            detail="; ".join(bad[:10])))

        # ── R6: dominancia P2P >= C3 por agente (solo datasets reales) ────
        if ds["month_labels"] is not None:
            t0 = time.time()
            from scenarios.scenario_c3_spot import run_c3_spot
            c3 = run_c3_spot(D, G_klim, pi_gs_m, ds["pi_bolsa"],
                             ds["prosumer_ids"], ds["consumer_ids"])
            c3_net = np.array([c3["per_agent"][n]["net_benefit"]
                               for n in range(N)])
            viol = [(ds["names"][n], float(engine[n] - c3_net[n]))
                    for n in range(N) if engine[n] < c3_net[n] - 1e-6]
            rel = max((abs(d) / max(abs(c3_net[i]), 1.0)
                       for i, (_, d) in enumerate(viol)), default=0.0)
            verdict = ("PASS" if not viol else
                       "INFO" if rel < 0.01 else "WARN")
            rows.append(CheckResult(
                "R6", "reparto", ds_name, "agentes con P2P < C3",
                f"{len(viol)}", "0 (SOFT)", verdict, tier,
                time.time() - t0,
                detail=", ".join(f"{n}: {d:,.0f} COP" for n, d in viol)))
    return rows


def main():
    setup_stdout_utf8()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--datasets", nargs="+", default=["SYN"])
    ap.add_argument("--tier", type=int, default=1)
    args = ap.parse_args()
    print("=== EJE 1 — Reparto de beneficio (R1-R6) ===")
    rows = run_checks(args.tier, args.datasets)
    save_results(rows, args.tier)
    for r in rows:
        print(f"  {r.id} [{r.datos}] {r.verdict}: {r.metric} = {r.value}")
    return 1 if hard_failures(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
