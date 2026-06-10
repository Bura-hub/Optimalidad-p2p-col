"""
test_smoke_fixtures_extremos.py — S5 de la campaña de smokes (ADR-0038).

Casos de borde del worker P2P (`core/ems_p2p._run_hour_worker`): el solver
no debe lanzar excepciones y la contabilidad debe ser válida en:
  1×1 · solo vendedores (I=0) · solo compradores (J=0) · G_net≈0
  (gatilla NaN-guard o mercado nulo) · D≫G · J=1,I=20.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core.ems_p2p import _run_hour_worker, SolverParams, HourlyResult

PGS, PGB = 1250.0, 114.0
SV = SolverParams(t_span=(0.0, 0.005), n_points=150, parallel=False)


def _worker(G_klim_k, D_k, seller_ids, buyer_ids):
    N = len(G_klim_k)
    a = np.full(N, 0.1)
    b = np.full(N, 50.0)
    lam = np.full(N, 100.0)
    theta = np.full(N, 0.5)
    etha = np.full(N, 0.1)
    args = (0, np.asarray(G_klim_k, float), np.asarray(D_k, float),
            np.asarray(G_klim_k, float),
            list(seller_ids), list(buyer_ids),
            a, b, lam, theta, etha, PGS, PGB,
            SV.tau, SV.tau_buyers, SV.t_span, SV.n_points,
            SV.stackelberg_iters, SV.stackelberg_tol, SV.stackelberg_max,
            SV.ode_method, SV.buyer_competition)
    return _run_hour_worker(args)


def _assert_contable(res: HourlyResult, G_klim_k, D_k):
    """Contabilidad válida si hubo mercado."""
    if res.P_star is None:
        return
    assert np.all(np.isfinite(res.P_star))
    assert np.all(res.P_star >= -1e-12)
    assert np.all(res.pi_star >= PGB - 1e-6)
    assert np.all(res.pi_star <= PGS + 1e-6)
    G_net = np.array([G_klim_k[j] - D_k[j] for j in res.seller_ids])
    D_net = np.array([D_k[i] - G_klim_k[i] for i in res.buyer_ids])
    short = min(float(np.sum(G_net)), float(np.sum(D_net)))
    assert float(np.sum(res.P_star)) <= short + 1e-6


def test_mercado_1x1():
    G = [5.0, 0.0]; D = [1.0, 3.0]
    res = _worker(G, D, [0], [1])
    _assert_contable(res, G, D)
    assert res.P_star is not None


def test_solo_vendedores():
    G = [5.0, 4.0]; D = [1.0, 1.0]
    res = _worker(G, D, [0, 1], [])
    assert res.P_star is None          # sin compradores → sin mercado


def test_solo_compradores():
    G = [0.0, 0.0]; D = [2.0, 3.0]
    res = _worker(G, D, [], [0, 1])
    assert res.P_star is None


def test_gnet_minusculo():
    """G_net=1e-8: simplex<1e-10 → mercado nulo o NaN-guard, sin excepción."""
    G = [1.0 + 1e-8, 0.0]; D = [1.0, 2.0]
    res = _worker(G, D, [0], [1])
    _assert_contable(res, G, D)
    if res.P_star is not None:
        assert float(np.sum(res.P_star)) <= 1e-6


def test_deficit_enorme():
    G = [10.0, 0.0, 0.0]; D = [2.0, 500.0, 800.0]
    res = _worker(G, D, [0], [1, 2])
    _assert_contable(res, G, D)


def test_j1_i20():
    N = 21
    G = [50.0] + [0.0] * 20
    D = [5.0] + [3.0] * 20
    res = _worker(G, D, [0], list(range(1, N)))
    _assert_contable(res, G, D)
    assert res.P_star is not None
    assert res.P_star.shape == (1, 20)
