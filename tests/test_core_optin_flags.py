"""
test_core_optin_flags.py — No-regresión de los flags opt-in ADR-0038.

Actividad 3.2 · Campaña de smokes del núcleo P2P (plan 2026-06-10).

Garantiza que los parámetros nuevos del core (CAL/ADR-0038):
  - ``buyer_competition`` ("aggregate" default | "matrix") en solve_buyers
    y su plumbing vía SolverParams,
  - ``pi0`` (solve_buyers) y ``P0`` (solve_sellers) para multi-start,
son ESTRICTAMENTE opt-in: con defaults el resultado es bit a bit idéntico
al comportamiento histórico. El gate del paper depende de esto.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core.replicator_buyers import solve_buyers
from core.replicator_sellers import solve_sellers
from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams
from data.base_case_data import (
    get_generation_profiles, get_demand_profiles, get_agent_params,
    PGS, PGB,
)

HOUR = 13   # hora 14 (1-indexada en JoinFinal.m) — la del golden test


def _hour_fixture():
    """Fixture determinista de la hora 14 sintética (mismo caso del golden)."""
    G = get_generation_profiles()[:, HOUR]
    D = get_demand_profiles()[:, HOUR]
    p = get_agent_params()
    a, b = np.array(p["a"]), np.array(p["b"])
    etha = np.array(p["etha"])
    surplus_ids = [n for n in range(len(G)) if G[n] > D[n]]
    deficit_ids = [n for n in range(len(G)) if G[n] < D[n]]
    G_net = np.array([G[j] - D[j] for j in surplus_ids])
    D_net = np.array([D[i] - G[i] for i in deficit_ids])
    a_j, b_j = a[surplus_ids], b[surplus_ids]
    etha_i = etha[deficit_ids]
    return G_net, D_net, a_j, b_j, etha_i


def _default_P0(G_net, D_net):
    """Réplica de la CI histórica de JoinFinal.m en solve_sellers."""
    J, I = len(G_net), len(D_net)
    if float(np.sum(G_net)) >= float(np.sum(D_net)):
        P0 = np.tile(D_net / J, (J, 1))
    else:
        P0 = np.tile(G_net / I, (I, 1)).T
    return np.clip(P0, 1e-10, None)


def test_solve_sellers_default_bit_identical():
    G_net, D_net, a_j, b_j, _ = _hour_fixture()
    kw = dict(t_span=(0.0, 0.005), n_points=150)
    pi_i = np.full(len(D_net), float(PGB))
    ref = solve_sellers(pi_i, G_net, D_net, a_j, b_j, **kw)
    new = solve_sellers(pi_i, G_net, D_net, a_j, b_j, P0=None, **kw)
    assert np.array_equal(ref, new), "P0=None debe ser bit a bit el default"


def test_solve_sellers_P0_explicit_ci_historica():
    """Pasar EXPLÍCITAMENTE la CI histórica reproduce el default bit a bit."""
    G_net, D_net, a_j, b_j, _ = _hour_fixture()
    kw = dict(t_span=(0.0, 0.005), n_points=150)
    pi_i = np.full(len(D_net), float(PGB))
    ref = solve_sellers(pi_i, G_net, D_net, a_j, b_j, **kw)
    new = solve_sellers(pi_i, G_net, D_net, a_j, b_j,
                        P0=_default_P0(G_net, D_net), **kw)
    assert np.array_equal(ref, new)


def test_solve_sellers_P0_shape_invalida():
    G_net, D_net, a_j, b_j, _ = _hour_fixture()
    pi_i = np.full(len(D_net), float(PGB))
    with pytest.raises(ValueError, match="P0"):
        solve_sellers(pi_i, G_net, D_net, a_j, b_j,
                      P0=np.ones((1, 1)), t_span=(0.0, 0.005), n_points=150)


def test_solve_buyers_default_bit_identical():
    G_net, D_net, a_j, b_j, etha_i = _hour_fixture()
    P_mat = _default_P0(G_net, D_net)
    kw = dict(pi_gs=float(PGS), pi_gb=float(PGB),
              t_span=(0.0, 0.005), n_points=150)
    ref = solve_buyers(P_mat, a_j, b_j, etha_i, **kw)
    agg = solve_buyers(P_mat, a_j, b_j, etha_i,
                       buyer_competition="aggregate", pi0=None, **kw)
    assert np.array_equal(ref, agg), \
        "buyer_competition='aggregate' + pi0=None debe ser bit a bit el default"


def test_solve_buyers_pi0_explicit_ci_historica():
    G_net, D_net, a_j, b_j, etha_i = _hour_fixture()
    P_mat = _default_P0(G_net, D_net)
    I = len(D_net)
    simple = float(PGS) * I
    pi0 = np.full(I + 1, simple / (I + 1))      # CI histórica exacta
    kw = dict(pi_gs=float(PGS), pi_gb=float(PGB),
              t_span=(0.0, 0.005), n_points=150)
    ref = solve_buyers(P_mat, a_j, b_j, etha_i, **kw)
    new = solve_buyers(P_mat, a_j, b_j, etha_i, pi0=pi0, **kw)
    assert np.array_equal(ref, new)


def test_solve_buyers_matrix_plumbed():
    """El flag 'matrix' cambia la dinámica (sanidad: está cableado de verdad)."""
    G_net, D_net, a_j, b_j, etha_i = _hour_fixture()
    P_mat = _default_P0(G_net, D_net)
    kw = dict(pi_gs=float(PGS), pi_gb=float(PGB),
              t_span=(0.0, 0.005), n_points=150)
    agg = solve_buyers(P_mat, a_j, b_j, etha_i, **kw)
    mat = solve_buyers(P_mat, a_j, b_j, etha_i,
                       buyer_competition="matrix", **kw)
    assert mat.shape == agg.shape
    assert np.all(mat >= float(PGB) - 1e-9) and np.all(mat <= float(PGS) + 1e-9)
    assert not np.array_equal(agg, mat), \
        "matrix debería alterar la dinámica en la hora 14 (equilibrio interior)"


def test_solve_buyers_flag_invalido():
    G_net, D_net, a_j, b_j, etha_i = _hour_fixture()
    P_mat = _default_P0(G_net, D_net)
    with pytest.raises(ValueError, match="buyer_competition"):
        solve_buyers(P_mat, a_j, b_j, etha_i, buyer_competition="otra")


def test_ems_plumbing_default_bit_identical():
    """run_single_hour con SolverParams default == buyer_competition explícito."""
    G = get_generation_profiles()
    D = get_demand_profiles()
    p = get_agent_params()
    agents = AgentParams(**p)
    grid = GridParams(pi_gs=float(PGS), pi_gb=float(PGB))
    sv_def = SolverParams(parallel=False)
    sv_agg = SolverParams(parallel=False, buyer_competition="aggregate")

    r_def = EMSP2P(agents, grid, sv_def).run_single_hour(HOUR, D, G)
    r_agg = EMSP2P(agents, grid, sv_agg).run_single_hour(HOUR, D, G)

    assert (r_def.P_star is None) == (r_agg.P_star is None)
    if r_def.P_star is not None:
        assert np.array_equal(r_def.P_star, r_agg.P_star)
        assert np.array_equal(r_def.pi_star, r_agg.pi_star)
        assert r_def.iters_used == r_agg.iters_used
