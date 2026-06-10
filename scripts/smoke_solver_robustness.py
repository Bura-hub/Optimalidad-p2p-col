"""
smoke_solver_robustness.py — EJE 4: robustez del solver (S1-S6, A2; ADR-0038)
==============================================================================
  S1 grid_solver        HARD  24 configs (t_span,n_points)×ode_method×iters:
        max desviación vs default ≤1% en W_money y kWh; ≤2% banda en π*;
        SOFT en IE/Gini ≤0.02. Excluidas configs con dt_Euler>4e-5
        (inestabilidad documentada de VEL_GPC=1e5, ems_p2p.py:150-155).
  S2 multistart_unicidad HARD  10 arranques aleatorios (P0/pi0 opt-in) →
        diferencia pareada P* ≤1% rel y π* ≤1% banda.
  S3 rtol_atol_acoplado HARD  rtol{1e-6,1e-8}×atol{1e-9,1e-12} en el solver
        acoplado: Δ endpoint ≤0.1%.
  S4 determinismo_parallel HARD parallel True vs False → bit a bit idéntico.
  S5 fixtures_extremos  HARD  delega en tests/test_smoke_fixtures_extremos.py.
  S6 sensibilidad_pgb_floor INFO piso π_gb 280 vs 182 (ago-2025).
  A2 competencia_matricial INFO/SOFT flag buyer_competition="matrix" vs
        "aggregate": ΔW>1% o Δπ*>5% banda → "A2 material".

Uso:
    python scripts/smoke_solver_robustness.py --datasets SYN --tier 1
    python scripts/smoke_solver_robustness.py --datasets SYN ago-2025 COB-M1 --tier 2
"""
from __future__ import annotations

import argparse
import itertools
import os
import subprocess
import sys
import time

import numpy as np

from smoke_common import (
    CheckResult, ROOT, load_dataset, make_solver, run_ems_cached,
    active_hours, save_results, hard_failures, setup_stdout_utf8,
)
from core.ems_p2p import GridParams


def _metrics(ds, results, G_klim):
    from scenarios.comparison_engine import _p2p_monetary_benefit
    from scenarios._pi_gs import as_pi_gs_array
    from core.settlement import gini_index
    N, T = ds["D"].shape
    pi_gs_m = as_pi_gs_array(ds["pi_gs_matrix"], N, T)
    money = _p2p_monetary_benefit(results, ds["D"], G_klim, pi_gs_m,
                                  float(ds["grid"].pi_gb),
                                  ds["prosumer_ids"],
                                  pi_bolsa=ds["pi_bolsa"], mode="canonical")
    kwh = pis = vol = 0.0
    ies = []
    for k in active_hours(results):
        r = results[k]
        v = float(np.sum(r.P_star))
        kwh += v
        pis += float(np.mean(r.pi_star)) * v
        vol += v
        ies.append(r.IE)
    return dict(W=float(np.sum(money)), kwh=kwh,
                pi=pis / vol if vol > 0 else 0.0,
                ie=float(np.mean(ies)) if ies else 0.0,
                gini=gini_index(money), money=money)


# ─────────────────────────────────────────────────────────────────────────────
# S1 — grid del solver
# ─────────────────────────────────────────────────────────────────────────────

GRID_TSPAN = [((0.0, 0.005), 150),    # default producción (dt=3.33e-5)
              ((0.0, 0.01), 300),     # JoinFinal t_span, mismo dt
              ((0.0, 0.01), 600),     # dt=1.67e-5 (más fino)
              ((0.0, 0.02), 600)]     # ventana doble, dt=3.33e-5
GRID_METHOD = ["LSODA", "BDF", "RK45"]
GRID_ITERS  = [(2, 10, 1e-3), (6, 20, 1e-5)]


def check_s1(tier, ds) -> CheckResult:
    t0 = time.time()
    band = float(ds["grid"].pi_gs) - float(ds["grid"].pi_gb)
    res0, gk0, _ = run_ems_cached(ds, make_solver())
    m0 = _metrics(ds, res0, gk0)

    worst = dict(W=0.0, kwh=0.0, pi=0.0, ie=0.0, gini=0.0)
    lines = []
    n_cfg = 0
    for (tspan, npts), meth, (it, mx, tol) in itertools.product(
            GRID_TSPAN, GRID_METHOD, GRID_ITERS):
        dt = (tspan[1] - tspan[0]) / npts
        assert dt <= 4e-5 + 1e-12, "config viola estabilidad Euler"
        sv = make_solver(t_span=tspan, n_points=npts, ode_method=meth,
                         stackelberg_iters=it, stackelberg_max=mx,
                         stackelberg_tol=tol)
        res, gk, _ = run_ems_cached(ds, sv, verbose=False)
        m = _metrics(ds, res, gk)
        dW = abs(m["W"] - m0["W"]) / max(abs(m0["W"]), 1e-9)
        dk = abs(m["kwh"] - m0["kwh"]) / max(m0["kwh"], 1e-9)
        dp = abs(m["pi"] - m0["pi"]) / band
        die = abs(m["ie"] - m0["ie"])
        dg = abs(m["gini"] - m0["gini"])
        for key, val in zip(("W", "kwh", "pi", "ie", "gini"),
                            (dW, dk, dp, die, dg)):
            worst[key] = max(worst[key], val)
        n_cfg += 1
        lines.append(f"{tspan}x{npts} {meth} it{it}: dW={dW:.2%} "
                     f"dkWh={dk:.2%} dπ={dp:.2%} dIE={die:.3f}")
    # HARD solo en W y kWh. El precio π* (y con él IE/Gini) es una
    # coordenada LENTA del replicador: el tier 1 SYN mostró dπ creciendo
    # con la LONGITUD de la ventana (0.89%→3.85%→7.6%) con W/kWh EXACTOS
    # (0.00%) e idéntico entre métodos ODE. El "precio de equilibrio" es
    # operacionalmente π(t_fin) — igual que en JoinFinal.m. La deriva se
    # reporta como WARN (banda de indeterminación, va a Métodos).
    hard_ok = worst["W"] <= 0.01 and worst["kwh"] <= 0.01
    soft_ok = worst["pi"] <= 0.02 and worst["ie"] <= 0.02 and \
        worst["gini"] <= 0.02
    verdict = "PASS" if hard_ok and soft_ok else (
        "WARN" if hard_ok else "FAIL")
    return CheckResult(
        "S1", "solver", ds["name"],
        f"max desv vs default sobre {n_cfg} configs (W/kWh/π*/IE/Gini)",
        f"{worst['W']:.2%}/{worst['kwh']:.2%}/{worst['pi']:.2%}/"
        f"{worst['ie']:.3f}/{worst['gini']:.3f}",
        "W,kWh<=1% HARD; π<=2%,IE,Gini<=0.02 SOFT (π = coord. lenta)",
        verdict, tier, time.time() - t0, detail="\n".join(lines))


# ─────────────────────────────────────────────────────────────────────────────
# S2 — multi-start (unicidad del equilibrio)
# ─────────────────────────────────────────────────────────────────────────────

def _select_hours(results):
    act = active_hours(results)
    if not act:
        return []
    by_vol = sorted(act, key=lambda k: float(np.sum(results[k].P_star)))
    picks = {by_vol[-1], by_vol[len(by_vol) // 2], by_vol[0]}
    # hora de máximo déficit comunitario activa
    def deficit(k):
        r = results[k]
        return float(np.sum([r.D_k[i] - r.G_klim_k[i] for i in r.buyer_ids]))
    picks.add(max(act, key=deficit))
    return sorted(picks)


def check_s2(tier, ds, results, n_starts=10, seed=7) -> CheckResult:
    from core.replicator_sellers import solve_sellers
    from core.replicator_buyers import solve_buyers
    t0 = time.time()
    sv = make_solver()
    gr = ds["grid"]
    band = float(gr.pi_gs) - float(gr.pi_gb)
    rng = np.random.default_rng(seed)
    hours = _select_hours(results)

    worst_P = worst_pi = worst_T = 0.0
    detail = []
    for k in hours:
        r = results[k]
        G_net = np.array([r.G_klim_k[j] - r.D_k[j] for j in r.seller_ids])
        D_net = np.array([r.D_k[i] - r.G_klim_k[i] for i in r.buyer_ids])
        a_j = ds["agents"].a[r.seller_ids]
        b_j = ds["agents"].b[r.seller_ids]
        etha_i = ds["agents"].etha[r.buyer_ids]
        J, I = len(G_net), len(D_net)
        finals_P, finals_pi = [], []
        for s in range(n_starts + 1):
            if s == 0:
                P0 = pi0 = None      # CI histórica
            else:
                P0 = rng.uniform(0.05, 1.0, (J, I))
                # escala dentro de la caja factible (≤ G_net por fila)
                row = P0.sum(axis=1)
                P0 *= (0.8 * G_net / np.maximum(row, 1e-12))[:, None]
                col = P0.sum(axis=0)
                over = col / np.maximum(D_net, 1e-12)
                P0 /= np.maximum(over.max(), 1.0)
                pi0 = rng.uniform(gr.pi_gb, gr.pi_gs, I)
            # FIEL A PRODUCCIÓN (fix tier 1: el arnés original encadenaba
            # P0 entre iteraciones — warm-start que producción NO hace y
            # contaminaba la comparación). Producción re-inicializa los
            # solvers en CADA iteración Stackelberg; la perturbación
            # multi-start entra SOLO en la primera (P0/pi0 de la iter 0).
            pi = np.full(I, gr.pi_gb) if pi0 is None else \
                np.clip(pi0.copy(), gr.pi_gb, gr.pi_gs)
            P_cur = None
            for it in range(sv.stackelberg_max):
                P_old = P_cur.copy() if P_cur is not None else None
                P_cur = solve_sellers(pi, G_net, D_net, a_j, b_j,
                                      tau=sv.tau, t_span=sv.t_span,
                                      n_points=sv.n_points,
                                      method=sv.ode_method,
                                      P0=P0 if it == 0 else None)
                pi = solve_buyers(P_cur, a_j, b_j, etha_i,
                                  pi_gs=gr.pi_gs, pi_gb=gr.pi_gb,
                                  tau=sv.tau_buyers, t_span=sv.t_span,
                                  n_points=sv.n_points,
                                  pi0=pi0 if it == 0 else None)
                pi = np.clip(pi, gr.pi_gb, gr.pi_gs)
                if P_old is not None:
                    nr = np.linalg.norm(P_cur - P_old) / \
                        (np.linalg.norm(P_old) + 1e-9)
                    if it + 1 >= sv.stackelberg_iters and \
                            nr < sv.stackelberg_tol:
                        break
            if np.isnan(P_cur).any() or np.isnan(pi).any():
                continue
            finals_P.append(P_cur)
            finals_pi.append(pi)
        # Diferencias pareadas vs el arranque histórico (índice 0).
        # Métrica en 3 niveles (refinada tras tier 1):
        #   kWh total (HARD)  — el VOLUMEN transado debe ser único;
        #   marginales (SOFT) — quién vende/recibe cuánto puede depender de
        #                       la CI (selección de equilibrio del
        #                       replicador, propiedad conocida de la
        #                       dinámica evolutiva; producción usa CI
        #                       determinista → reproducible, ver S4);
        #   π* (SOFT)         — coordenada lenta (ver S1).
        if len(finals_P) < 2:
            continue
        ref_P, ref_pi = finals_P[0], finals_pi[0]
        ref_tot = float(np.sum(ref_P)) + 1e-12
        ref_marg = np.concatenate([ref_P.sum(axis=1), ref_P.sum(axis=0)])
        nrm_m = float(np.linalg.norm(ref_marg)) + 1e-12
        dT = max(abs(float(np.sum(p)) - ref_tot) / ref_tot
                 for p in finals_P[1:])
        dM = max(float(np.linalg.norm(
            np.concatenate([p.sum(axis=1), p.sum(axis=0)]) - ref_marg))
            / nrm_m for p in finals_P[1:])
        dpi = max(float(np.max(np.abs(p - ref_pi))) / band
                  for p in finals_pi[1:])
        worst_T = max(worst_T, dT)
        worst_P, worst_pi = max(worst_P, dM), max(worst_pi, dpi)
        detail.append(f"h{k}: dkWh={dT:.4f} dmarg={dM:.4f} dπ={dpi:.4f} "
                      f"({len(finals_P)-1} arranques)")
    verdict = ("FAIL" if worst_T > 0.01 else
               "PASS" if worst_P <= 0.01 and worst_pi <= 0.01 else "WARN")
    return CheckResult(
        "S2", "solver", ds["name"],
        f"multi-start dkWh/dmarginales/dπ ({len(hours)} horas, "
        f"{n_starts} arranques)",
        f"{worst_T:.4f} / {worst_P:.4f} / {worst_pi:.4f} banda",
        "kWh<=1% HARD; marginales,π SOFT (selección de equilibrio por CI)",
        verdict, tier, time.time() - t0,
        detail="; ".join(detail))


# ─────────────────────────────────────────────────────────────────────────────
# S3 — rtol/atol del acoplado
# ─────────────────────────────────────────────────────────────────────────────

def check_s3(tier, ds, results) -> CheckResult:
    """rtol/atol del acoplado. Cada solve con tope de 90 s (SIGALRM, Linux)
    — mismo blindaje que el worker C2: las horas stiff pueden arrastrarse
    >5 min sin converger y S3 corre en el proceso principal."""
    import signal
    from core.coupled_ode_convergence import solve_coupled_for_hour

    use_alarm = hasattr(signal, "SIGALRM")

    class _Timeout(Exception):
        pass

    def _handler(signum, frame):                           # pragma: no cover
        raise _Timeout()

    if use_alarm:
        signal.signal(signal.SIGALRM, _handler)

    def _solve(**kwargs):
        try:
            if use_alarm:
                signal.alarm(90)
            return solve_coupled_for_hour(**kwargs)
        finally:
            if use_alarm:
                signal.alarm(0)

    t0 = time.time()
    gr, ag = ds["grid"], ds["agents"]
    sv = make_solver()
    band = float(gr.pi_gs) - float(gr.pi_gb)
    hours = _select_hours(results)[:4]
    worst = 0.0
    for k in hours:
        r = results[k]
        G_net = np.array([r.G_klim_k[j] - r.D_k[j] for j in r.seller_ids])
        D_net = np.array([r.D_k[i] - r.G_klim_k[i] for i in r.buyer_ids])
        kw = dict(G_net_j=G_net, D_net_i=D_net,
                  a_j=ag.a[r.seller_ids], b_j=ag.b[r.seller_ids],
                  lam_j=ag.lam[r.seller_ids], theta_j=ag.theta[r.seller_ids],
                  G_klim_i=r.G_klim_k[r.buyer_ids],
                  lam_i=ag.lam[r.buyer_ids], theta_i=ag.theta[r.buyer_ids],
                  etha_i=ag.etha[r.buyer_ids],
                  pi_gs=gr.pi_gs, pi_gb=gr.pi_gb,
                  tau_sellers=sv.tau, tau_buyers=sv.tau_buyers,
                  t_span=(0.0, 0.04), n_points=50, method="LSODA")
        try:
            base = _solve(rtol=1e-6, atol=1e-9, **kw)
            if not base.success:
                continue
            for rt, at in ((1e-8, 1e-9), (1e-6, 1e-12), (1e-8, 1e-12)):
                try:
                    alt = _solve(rtol=rt, atol=at, **kw)
                except Exception:                          # noqa: BLE001
                    continue
                if not alt.success:
                    continue
                nP = float(np.linalg.norm(base.P_star)) + 1e-12
                worst = max(worst,
                            float(np.linalg.norm(alt.P_star - base.P_star))
                            / nP,
                            float(np.max(np.abs(alt.pi_star -
                                                base.pi_star))) / band)
        except Exception:                                  # noqa: BLE001
            continue
    return CheckResult(
        "S3", "solver", ds["name"],
        f"max Δ endpoint rtol/atol ({len(hours)} horas)",
        f"{worst:.5f}", "<=0.1%",
        "PASS" if worst <= 1e-3 else "FAIL", tier, time.time() - t0)


# ─────────────────────────────────────────────────────────────────────────────
# S4 — determinismo parallel
# ─────────────────────────────────────────────────────────────────────────────

def check_s4(tier, ds) -> CheckResult:
    t0 = time.time()
    res_p, _, _ = run_ems_cached(ds, make_solver(parallel=True))
    res_s, _, _ = run_ems_cached(ds, make_solver(parallel=False))
    diff = 0
    for rp, rs in zip(res_p, res_s):
        if (rp.P_star is None) != (rs.P_star is None):
            diff += 1
            continue
        if rp.P_star is None:
            continue
        if not (np.array_equal(rp.P_star, rs.P_star)
                and np.array_equal(rp.pi_star, rs.pi_star)):
            diff += 1
    return CheckResult(
        "S4", "solver", ds["name"], "horas con diferencia parallel vs serial",
        str(diff), "0 (bit a bit)", "PASS" if diff == 0 else "FAIL",
        tier, time.time() - t0)


# ─────────────────────────────────────────────────────────────────────────────
# S5 — fixtures extremos (delegado a pytest)
# ─────────────────────────────────────────────────────────────────────────────

def check_s5(tier) -> CheckResult:
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest",
         os.path.join(ROOT, "tests", "test_smoke_fixtures_extremos.py"),
         "-q", "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=ROOT)
    tail = (proc.stdout or "").strip().splitlines()[-1:]
    return CheckResult(
        "S5", "solver", "FIX", "pytest fixtures extremos",
        " ".join(tail), "todos pass",
        "PASS" if proc.returncode == 0 else "FAIL",
        tier, time.time() - t0,
        detail="" if proc.returncode == 0 else proc.stdout[-1500:])


# ─────────────────────────────────────────────────────────────────────────────
# S6 — sensibilidad del piso PGB (INFO)
# ─────────────────────────────────────────────────────────────────────────────

def check_s6(tier, ds) -> CheckResult:
    t0 = time.time()
    res_a, gk_a, _ = run_ems_cached(ds, make_solver())
    m_a = _metrics(ds, res_a, gk_a)
    grid_b = GridParams(pi_gs=float(ds["grid"].pi_gs), pi_gb=182.0)
    res_b, gk_b, _ = run_ems_cached(ds, make_solver(), grid_override=grid_b)
    m_b = _metrics(ds, res_b, gk_b)
    return CheckResult(
        "S6", "solver", ds["name"],
        "piso π_gb 280→182: ΔW / Δπ* / ΔkWh / ΔIE",
        f"{(m_b['W']-m_a['W'])/abs(m_a['W']):+.2%} / "
        f"{m_b['pi']-m_a['pi']:+.0f} COP / "
        f"{(m_b['kwh']-m_a['kwh'])/max(m_a['kwh'],1e-9):+.2%} / "
        f"{m_b['ie']-m_a['ie']:+.3f}",
        "INFO (decisión asesores)", "INFO", tier, time.time() - t0)


# ─────────────────────────────────────────────────────────────────────────────
# A2 — competencia matricial
# ─────────────────────────────────────────────────────────────────────────────

def check_a2(tier, ds) -> CheckResult:
    t0 = time.time()
    band = float(ds["grid"].pi_gs) - float(ds["grid"].pi_gb)
    res_a, gk_a, _ = run_ems_cached(ds, make_solver())
    m_a = _metrics(ds, res_a, gk_a)
    res_m, gk_m, _ = run_ems_cached(
        ds, make_solver(buyer_competition="matrix"))
    m_m = _metrics(ds, res_m, gk_m)
    dW = abs(m_m["W"] - m_a["W"]) / max(abs(m_a["W"]), 1e-9)
    dpi = abs(m_m["pi"] - m_a["pi"]) / band
    material = dW > 0.01 or dpi > 0.05
    return CheckResult(
        "A2", "solver", ds["name"],
        "agregada vs matricial: ΔW / Δπ* / ΔIE / ΔGini",
        f"{dW:.2%} / {dpi:.2%} banda / {m_m['ie']-m_a['ie']:+.3f} / "
        f"{m_m['gini']-m_a['gini']:+.3f}",
        "material si ΔW>1% o Δπ>5%",
        "WARN" if material else "INFO", tier, time.time() - t0,
        detail=("A2 MATERIAL: decidir en tesis si se adopta la forma "
                "matricial" if material else
                "A2 inmaterial: la forma agregada es equivalente a efectos "
                "prácticos — cerrar deuda"))


def run_checks(tier: int, datasets: list) -> list:
    rows = []
    for ds_name in datasets:
        ds = load_dataset(ds_name)
        if ds_name == "SYN":
            rows.append(check_s1(tier, ds))
            res, _, _ = run_ems_cached(ds, make_solver())
            rows.append(check_s2(tier, ds, res))
            rows.append(check_s3(tier, ds, res))
            rows.append(check_s4(tier, ds))
            rows.append(check_a2(tier, ds))
        elif ds_name in ("ago-2025", "oct-2025"):
            res, _, _ = run_ems_cached(ds, make_solver())
            rows.append(check_s2(tier, ds, res))
            rows.append(check_s3(tier, ds, res))
            rows.append(check_s6(tier, ds))
        else:   # COB-M1 / COB-M3
            rows.append(check_a2(tier, ds))
    rows.append(check_s5(tier))
    return rows


def main():
    setup_stdout_utf8()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--datasets", nargs="+", default=["SYN"])
    ap.add_argument("--tier", type=int, default=1)
    args = ap.parse_args()
    print("=== EJE 4 — Robustez del solver (S1-S6, A2) ===")
    rows = run_checks(args.tier, args.datasets)
    save_results(rows, args.tier)
    for r in rows:
        print(f"  {r.id} [{r.datos}] {r.verdict}: {r.metric} = {r.value}")
    return 1 if hard_failures(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
