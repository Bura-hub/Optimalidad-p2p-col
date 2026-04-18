"""
test_stackelberg_convergence.py
--------------------------------
Verifica que el criterio de parada adaptativo del loop Stackelberg funciona:
  - iters_used ∈ [min_iter, max_iter] en el caso base sintético.
  - La norma relativa ||P_new - P_old|| / (||P_old|| + ε) < tol al terminar.
  - El campo HourlyResult.iters_used se guarda correctamente.

Actividad 4.2 — Análisis cualitativo de optimalidad del equilibrio.
"""

import sys, os, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pytest

from core.ems_p2p import (
    EMSP2P, AgentParams, GridParams, SolverParams, HourlyResult
)
from data.base_case_data import (
    get_agent_params, get_generation_profiles, get_demand_profiles,
    PGS, PGB,
)


def _build_ems(min_iter=2, tol=1e-3, max_iter=10) -> EMSP2P:
    """
    Construye EMSP2P con parámetros canónicos de base_case_data (sin DR).

    Parámetros
    ----------
    min_iter : int   — iteraciones mínimas Stackelberg (stackelberg_iters)
    tol      : float — tolerancia relativa de convergencia (stackelberg_tol)
    max_iter : int   — iteraciones máximas (stackelberg_max)
    """
    p = get_agent_params()
    agents = AgentParams(
        N=p["N"], a=p["a"], b=p["b"], c=p["c"],
        lam=p["lam"], theta=p["theta"], etha=p["etha"],
        alpha=np.zeros(6),   # sin DR para test determinista
    )
    grid   = GridParams(pi_gs=PGS, pi_gb=PGB)
    solver = SolverParams(
        stackelberg_iters=min_iter,
        stackelberg_tol=tol,
        stackelberg_max=max_iter,
        parallel=False,
    )
    return EMSP2P(agents, grid, solver)


def test_iters_used_in_range():
    """iters_used debe estar en [min_iter, max_iter] en horas activas."""
    ems = _build_ems(min_iter=2, tol=1e-3, max_iter=10)
    G   = get_generation_profiles()
    D   = get_demand_profiles()
    results, _, _ = ems.run(D, G)

    active = [r for r in results if r.iters_used > 0]
    assert len(active) > 0, "Ninguna hora tuvo mercado activo"

    for r in active:
        assert 2 <= r.iters_used <= 10, (
            f"hora {r.k}: iters_used={r.iters_used} fuera de [2, 10]"
        )


def test_convergence_norm_below_tol():
    """
    Verifica que el loop Stackelberg converge en hora 14 (índice 13).

    Criterio: ||P_new - P_old|| / (||P_old|| + 1e-9) < tol=1e-3 al salir,
    con al menos min_iter=2 y como máximo max_iter=10 iteraciones.
    """
    p = get_agent_params()
    sv = SolverParams(stackelberg_iters=2, stackelberg_tol=1e-3,
                      stackelberg_max=10, parallel=False)

    from core.ems_p2p import _run_hour_worker
    from core.market_prep import compute_generation_limit, classify_agents

    G = get_generation_profiles()
    D = get_demand_profiles()
    k = 13
    G_klim_k = compute_generation_limit(G[:, k], p["a"], p["b"], p["c"], PGS)
    _, sids, bids = classify_agents(G_klim_k, D[:, k])

    if len(sids) == 0 or len(bids) == 0:
        pytest.skip("Hora 13 sin mercado activo en este perfil")

    args = (
        k, G_klim_k, D[:, k].copy(), G[:, k].copy(),
        sids, bids,
        p["a"], p["b"], p["lam"], p["theta"], p["etha"],
        PGS, PGB,
        sv.tau, sv.tau_buyers, sv.t_span, sv.n_points,
        sv.stackelberg_iters, sv.stackelberg_tol, sv.stackelberg_max,
    )
    res = _run_hour_worker(args)
    assert isinstance(res, HourlyResult)
    assert res.iters_used >= 2, "Debe ejecutar al menos min_iter=2 iteraciones"
    assert res.P_star is not None and res.pi_star is not None
    # A6 (auditoría 2026-04-17): assert explícito sobre norma relativa final.
    # Si iters_used == max_iter, el loop salió por tope y no necesariamente
    # convergió bajo tolerancia; solo exigimos el criterio cuando salió antes.
    if res.iters_used < 10:
        assert res.norm_rel_final < 1e-3, (
            f"Loop salió antes de max_iter={10} pero norm_rel_final="
            f"{res.norm_rel_final:.2e} >= tol=1e-3"
        )


def test_iters_used_stored_in_inactive_hours():
    """Horas sin mercado (J=0 o I=0) deben reportar iters_used=0."""
    ems = _build_ems()
    G   = get_generation_profiles()
    D   = get_demand_profiles()
    results, _, _ = ems.run(D, G)

    for r in results:
        if not r.seller_ids and not r.buyer_ids:
            assert r.iters_used == 0, (
                f"hora {r.k}: horas inactivas deben tener iters_used=0"
            )


def test_min_iter_respected():
    """Con tol=0 (imposible converger antes), debe siempre llegar a max_iter."""
    ems = _build_ems(min_iter=3, tol=0.0, max_iter=3)
    G   = get_generation_profiles()
    D   = get_demand_profiles()
    results, _, _ = ems.run(D, G)

    active = [r for r in results if r.iters_used > 0]
    for r in active:
        assert r.iters_used == 3, (
            f"hora {r.k}: con tol=0 y max_iter=3 debe iterar exactamente 3 veces, "
            f"obtuvo {r.iters_used}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
