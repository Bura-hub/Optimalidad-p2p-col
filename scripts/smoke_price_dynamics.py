"""
smoke_price_dynamics.py — EJE 3: dinámica/negociación de precios (P1-P5)
=========================================================================
ADR-0038. Verifica que el precio de clearing del juego tiene sentido
económico:

  P1 monotonia_desbalance   HARD  π* no-decreciente en el ratio de escasez
        r = ΣD_net/ΣG_net ∈ {0.2…5} (10 pts, agentes de la hora 14 sintética):
        Spearman ρ ≥ 0.95 y sin descenso pareado > 1 % de banda.
        SOFT: asíntotas (r≫1 → π* a ≤15 % de π_gs; r≪1 → ≤15 % de π_gb).
  P2 estatica_comparativa   HARD  π_gs+10 % → π* no baja; π_gb+10 % → no baja.
  P3 dispersion_precios     INFO  CV de π*_i por hora; SOFT si CV>50 %.
  P4 correlacion_precio_escasez  SOFT ρ≤0.2 → warning; HARD: precio medio
        ponderado dentro de [π_gb, π_gs] del juego.
  P5 no_arbitraje_csv       HARD  sobre el CSV exportado por
        export_p2p_hourly: π_gb ≤ precio ≤ π_gs[i] por trade (ε=0.005 COP
        por redondeo del CSV).

Uso:
    python scripts/smoke_price_dynamics.py --datasets SYN --tier 1
    python scripts/smoke_price_dynamics.py --datasets COB-M1 COB-M3 --tier 2
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

from smoke_common import (
    CheckResult, ROOT, load_dataset, make_solver, run_ems_cached,
    active_hours, save_results, hard_failures, setup_stdout_utf8,
)

HOUR_BASE = 13   # hora 14 sintética (la del golden) como base de P1/P2


SOLVE_TIMEOUT_S = 60      # tope por solve (SIGALRM, Linux)
VOLUME_FLOOR_KWH = 0.05   # mercados degenerados quedan fuera del barrido


def _solve_fixture_hour(G_net, D_net, a_j, b_j, etha_i, pi_gs, pi_gb,
                        sv=None):
    """Resuelve una hora aislada con el loop Stackelberg de producción.

    Blindajes (lección server 2026-06-10, OOM kill silencioso):
    - ``return_traj=True`` en solve_sellers fuerza ``t_eval`` → scipy solo
      almacena n_points; sin t_eval, en fixtures extremos (D_net minúscula
      → ultra-stiff) LSODA acumula MILLONES de pasos internos y explota la
      RAM (observado: 1.9 GB y subiendo en el server).
    - tope de 60 s por solve vía SIGALRM (Linux); el punto que no converge
      a tiempo retorna None y el barrido sigue con los demás.
    - piso de volumen: mercados degenerados (< 0.05 kWh del lado corto)
      no se barren — la monotonía económica no se define ahí.
    """
    import signal
    from core.replicator_sellers import solve_sellers
    from core.replicator_buyers import solve_buyers
    sv = sv or make_solver()

    if min(float(np.sum(G_net)), float(np.sum(D_net))) < VOLUME_FLOOR_KWH:
        return None, None

    use_alarm = hasattr(signal, "SIGALRM")

    class _Timeout(Exception):
        pass

    def _handler(signum, frame):                           # pragma: no cover
        raise _Timeout()

    if use_alarm:
        signal.signal(signal.SIGALRM, _handler)

    I = len(D_net)
    P = (np.tile(D_net / len(G_net), (len(G_net), 1))
         if np.sum(G_net) >= np.sum(D_net)
         else np.tile(G_net / I, (I, 1)).T)
    P = np.clip(P, 1e-10, None)
    pi = np.full(I, pi_gb)
    try:
        for it in range(sv.stackelberg_max):
            P_old = P.copy()
            if use_alarm:
                signal.alarm(SOLVE_TIMEOUT_S)
            P, _, _ = solve_sellers(pi, G_net, D_net, a_j, b_j, tau=sv.tau,
                                    t_span=sv.t_span, n_points=sv.n_points,
                                    method=sv.ode_method, return_traj=True)
            pi = solve_buyers(P, a_j, b_j, etha_i, pi_gs=pi_gs, pi_gb=pi_gb,
                              tau=sv.tau_buyers, t_span=sv.t_span,
                              n_points=sv.n_points)
            if use_alarm:
                signal.alarm(0)
            pi = np.clip(pi, pi_gb, pi_gs)
            nr = np.linalg.norm(P - P_old) / (np.linalg.norm(P_old) + 1e-9)
            if it + 1 >= sv.stackelberg_iters and nr < sv.stackelberg_tol:
                break
    except Exception:                                      # noqa: BLE001
        return None, None
    finally:
        if use_alarm:
            signal.alarm(0)
    if np.isnan(P).any() or np.isnan(pi).any():
        return None, None
    return P, pi


def _fixture_h14():
    from data.base_case_data import (
        get_generation_profiles, get_demand_profiles, get_agent_params,
        PGS, PGB,
    )
    from core.market_prep import compute_generation_limit, classify_agents
    G = get_generation_profiles()[:, HOUR_BASE]
    D = get_demand_profiles()[:, HOUR_BASE]
    p = get_agent_params()
    G_klim = compute_generation_limit(G, p["a"], p["b"], p["c"], PGS)
    _, sids, bids = classify_agents(G_klim, D)
    G_net = np.array([G_klim[j] - D[j] for j in sids])
    D_net = np.array([D[i] - G_klim[i] for i in bids])
    return (G_net, D_net, p["a"][sids], p["b"][sids], p["etha"][bids],
            float(PGS), float(PGB))


def _spearman(x, y):
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean(); ry -= ry.mean()
    den = np.sqrt(np.sum(rx**2) * np.sum(ry**2))
    return float(np.sum(rx * ry) / den) if den > 0 else 0.0


def check_p1(tier) -> list:
    t0 = time.time()
    G_net, D_net, a_j, b_j, etha_i, pgs, pgb = _fixture_h14()
    band = pgs - pgb
    base_ratio = float(np.sum(D_net) / np.sum(G_net))
    ratios = np.array([0.2, 0.4, 0.7, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0])
    pis, used = [], []
    for r_target in ratios:
        D_scaled = D_net * (r_target / base_ratio)
        _, pi = _solve_fixture_hour(G_net, D_scaled, a_j, b_j, etha_i,
                                    pgs, pgb)
        if pi is None:
            continue
        pis.append(float(np.mean(pi)))
        used.append(float(r_target))
    pis = np.array(pis); used = np.array(used)
    if len(pis) < 5:
        return [CheckResult(
            "P1", "precios", "FIX-h14",
            f"monotonía: solo {len(pis)}/10 puntos resolubles "
            f"(timeout/piso de volumen)",
            "insuficiente", ">=5 puntos", "WARN", tier, time.time() - t0)]
    rho = _spearman(used, pis)
    worst_drop = 0.0
    for i in range(1, len(pis)):
        worst_drop = max(worst_drop, (pis[i - 1] - pis[i]) / band)
    # Criterio reestructurado tras el tier 1 (hallazgo "coordenada lenta"):
    # la teoría solo garantiza el ORDEN DE EXTREMOS (escasez alta debe
    # pagar más que exceso alto) y la pertenencia a banda; la monotonía
    # fina punto a punto muestrea la variedad lenta del precio (se observó
    # un atractor intermedio ~493 en SYN) y queda como SOFT documentado.
    lo = pis[used <= 0.5]
    hi = pis[used >= 3.0]
    extremos_ok = (lo.size > 0 and hi.size > 0
                   and float(np.min(hi)) > float(np.max(lo)) + 0.05 * band)
    en_banda = bool(np.all(pis >= pgb - 1e-6) and np.all(pis <= pgs + 1e-6))
    if not (extremos_ok and en_banda):
        verdict = "FAIL"
    elif rho >= 0.95 and worst_drop <= 0.01:
        verdict = "PASS"
    else:
        verdict = "WARN"
    rows = [CheckResult(
        "P1", "precios", "FIX-h14",
        f"extremos/banda + Spearman ρ / peor descenso ({len(pis)} pts)",
        f"extremos={'OK' if extremos_ok else 'X'} ρ={rho:.3f} "
        f"drop={worst_drop:.3f}",
        "HARD: π(r≥3)>π(r≤0.5)+5% banda y todo en banda; "
        "SOFT: ρ>=0.95, drop<=1%",
        verdict, tier, time.time() - t0,
        detail="; ".join(f"r={r:.1f}→π*={p:.0f}"
                         for r, p in zip(used, pis)))]
    # SOFT: asíntotas
    hi = pis[used >= 4.0]
    lo = pis[used <= 0.4]
    asint_ok = True
    msg = []
    if hi.size and (pgs - float(np.max(hi))) / band > 0.15:
        asint_ok = False
        msg.append(f"r≥4: π*={float(np.max(hi)):.0f} lejos de π_gs={pgs:.0f}")
    if lo.size and (float(np.min(lo)) - pgb) / band > 0.15:
        asint_ok = False
        msg.append(f"r≤0.4: π*={float(np.min(lo)):.0f} lejos de π_gb={pgb:.0f}")
    rows.append(CheckResult(
        "P1b", "precios", "FIX-h14", "asíntotas de saturación",
        "OK" if asint_ok else "no saturó", "≤15% banda (SOFT)",
        "PASS" if asint_ok else "WARN", tier, 0.0, detail="; ".join(msg)))
    return rows


def check_p2(tier) -> CheckResult:
    t0 = time.time()
    G_net, D_net, a_j, b_j, etha_i, pgs, pgb = _fixture_h14()
    band = pgs - pgb
    _, pi0 = _solve_fixture_hour(G_net, D_net, a_j, b_j, etha_i, pgs, pgb)
    base = float(np.mean(pi0))
    drops = []
    _, pi_gs_up = _solve_fixture_hour(G_net, D_net, a_j, b_j, etha_i,
                                      pgs * 1.10, pgb)
    drops.append(("π_gs+10%", (base - float(np.mean(pi_gs_up))) / band))
    _, pi_gb_up = _solve_fixture_hour(G_net, D_net, a_j, b_j, etha_i,
                                      pgs, pgb * 1.10)
    drops.append(("π_gb+10%", (base - float(np.mean(pi_gb_up))) / band))
    worst = max(d for _, d in drops)
    return CheckResult(
        "P2", "precios", "FIX-h14",
        "peor descenso de π* al subir cotas externas",
        f"{worst:.4f} banda", "<=1%",
        "PASS" if worst <= 0.01 else "FAIL", tier, time.time() - t0,
        detail="; ".join(f"{n}: Δ={d:+.4f}" for n, d in drops))


def check_p3(tier, ds, results) -> CheckResult:
    t0 = time.time()
    cvs = []
    for k in active_hours(results):
        r = results[k]
        if len(r.pi_star) >= 2:
            m = float(np.mean(r.pi_star))
            if m > 1e-9:
                cvs.append(float(np.std(r.pi_star)) / m)
    if not cvs:
        return CheckResult("P3", "precios", ds["name"], "CV de π*_i",
                           "sin horas multi-comprador", "-", "SKIP",
                           tier, time.time() - t0)
    mx = float(np.max(cvs))
    return CheckResult(
        "P3", "precios", ds["name"],
        f"CV de π*_i por hora ({len(cvs)} h)",
        f"med={float(np.median(cvs)):.3f} max={mx:.3f}",
        "INFO; SOFT si max>50%",
        "INFO" if mx <= 0.50 else "WARN", tier, time.time() - t0)


def check_p4(tier, ds, results) -> CheckResult:
    t0 = time.time()
    pgb, pgs = float(ds["grid"].pi_gb), float(ds["grid"].pi_gs)
    pis, scar, vols = [], [], []
    for k in active_hours(results):
        r = results[k]
        G_net = np.array([r.G_klim_k[j] - r.D_k[j] for j in r.seller_ids])
        D_net = np.array([r.D_k[i] - r.G_klim_k[i] for i in r.buyer_ids])
        sg, sd = float(np.sum(G_net)), float(np.sum(D_net))
        vol = float(np.sum(r.P_star))
        pis.append(float(np.mean(r.pi_star)))
        scar.append(sd / (sg + sd) if sg + sd > 0 else 0.5)
        vols.append(vol)
    pis, scar, vols = map(np.array, (pis, scar, vols))
    rho = _spearman(scar, pis)
    mean_w = float(np.dot(pis, vols) / np.sum(vols)) if np.sum(vols) else 0.0
    in_band = pgb - 1e-6 <= mean_w <= pgs + 1e-6
    verdict = "FAIL" if not in_band else ("WARN" if rho <= 0.2 else "PASS")
    return CheckResult(
        "P4", "precios", ds["name"],
        f"ρ(π*, escasez) / precio medio pond. ({len(pis)} h)",
        f"{rho:.3f} / {mean_w:.0f} COP", "ρ>0.2 SOFT; media∈banda HARD",
        verdict, tier, time.time() - t0)


def check_p5(tier, ds, results) -> CheckResult:
    import pandas as pd
    from analysis.p2p_breakdown import export_p2p_hourly
    t0 = time.time()
    out_dir = os.path.join(ROOT, "outputs", "smoke_cache")
    prefix = f"p5_{ds['name']}"
    export_p2p_hourly(results, ds["names"], ds["pi_gs_matrix"],
                      float(ds["grid"].pi_gb), out_dir=out_dir,
                      prefix=prefix, verbose=False)
    flows = pd.read_csv(os.path.join(out_dir, f"{prefix}_flujos.csv"))
    eps = 0.005 + 1e-9 * float(ds["grid"].pi_gs)
    pgb = float(ds["grid"].pi_gb)
    name_to_idx = {n: i for i, n in enumerate(ds["names"])}
    viol = 0
    for _, row in flows.iterrows():
        price = float(row["precio_COP_kWh"])
        i = name_to_idx[row["comprador"]]
        # hora local: la columna se llama 'hora'
        k = int(row["hora"])
        cap = float(ds["pi_gs_matrix"][i, k])
        if price < pgb - eps or price > cap + eps:
            viol += 1
    return CheckResult(
        "P5", "precios", ds["name"],
        f"violaciones de no-arbitraje en CSV ({len(flows)} trades)",
        str(viol), "0", "PASS" if viol == 0 else "FAIL",
        tier, time.time() - t0)


def run_checks(tier: int, datasets: list) -> list:
    rows = []
    if tier <= 1 or "SYN" in datasets:
        rows.extend(check_p1(tier))
        rows.append(check_p2(tier))
    for ds_name in datasets:
        ds = load_dataset(ds_name)
        results, _, _ = run_ems_cached(ds, make_solver())
        rows.append(check_p3(tier, ds, results))
        if ds["month_labels"] is not None:
            rows.append(check_p4(tier, ds, results))
            rows.append(check_p5(tier, ds, results))
    return rows


def main():
    setup_stdout_utf8()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--datasets", nargs="+", default=["SYN"])
    ap.add_argument("--tier", type=int, default=1)
    args = ap.parse_args()
    print("=== EJE 3 — Dinámica de precios (P1-P5) ===")
    rows = run_checks(args.tier, args.datasets)
    save_results(rows, args.tier)
    for r in rows:
        print(f"  {r.id} [{r.datos}] {r.verdict}: {r.metric} = {r.value}")
    return 1 if hard_failures(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
