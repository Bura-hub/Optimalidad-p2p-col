"""El factor de coincidencia (D20): la opcion C por mecanismo y la B.

Caso a mano, un mes y dos horas. h0: el 0 inyecta 2 y el 1 importa 2.
h1: el 0 importa 2. C1 acredita al 0 sus 2 contra su propia importacion de
h1: nada coincide. El colectivo con reparto igual asigna 1 y 1 en h0; solo
el 1 importa en h0: coincide 1 de 2. El mercado transa los 2 en h0: todo
coincide.
"""
import warnings

import numpy as np
import pytest

from analysis.coincidencia import (coincidencia_por_mecanismo,
                                   simultaneidad_picos)
from core.ems_p2p import HourlyResult

warnings.filterwarnings("ignore")


def _caso():
    G = np.array([[3.0, 0.0], [0.0, 0.0]])
    D = np.array([[1.0, 2.0], [2.0, 0.0]])
    res = [HourlyResult(k=0, P_star=np.array([[2.0]]),
                        pi_star=np.array([600.0]),
                        seller_ids=[0], buyer_ids=[1]),
           HourlyResult(k=1)]
    return D, G, res


def test_caso_a_mano():
    D, G, res = _caso()
    fc = coincidencia_por_mecanismo(
        D, G, res, pde_colectivo={0: np.array([0.0, 1.0])},
        include_c5=True)
    assert fc["C1"] == pytest.approx(0.0)
    assert fc["C4"] == pytest.approx(0.5)
    assert fc["P2P"] == pytest.approx(1.0)
    assert fc["C5"] == pytest.approx(1.0)
    assert fc["P2P_colectivo"] == pytest.approx(1.0)
    assert np.isnan(fc["C3"])
    assert "C2" not in fc          # sin contrato interno no se calcula


def test_lo_que_no_se_firma_vuelve_al_residual():
    D, G, res = _caso()
    fc = coincidencia_por_mecanismo(
        D, G, res, sin_firmar=np.array([[2.0, 0.0], [0.0, 0.0]]),
        sin_firmar_comprador=np.array([[0.0, 0.0], [2.0, 0.0]]))
    assert fc["C2"] == pytest.approx(0.0)


def test_simultaneidad_a_mano():
    D, G, _ = _caso()
    # Picos individuales 2 y 2; el neto de la comunidad es 0 y 2.
    assert simultaneidad_picos(D, G) == pytest.approx(0.5)


def test_entre_cero_y_uno_y_c1_cero():
    rng = np.random.default_rng(3)
    N, T = 4, 96
    D = rng.uniform(0, 3, (N, T))
    G = rng.uniform(0, 4, (N, T))
    res = []
    for k in range(T):
        exc = np.maximum(G[:, k] - D[:, k], 0)
        dfc = np.maximum(D[:, k] - G[:, k], 0)
        s, b = list(np.flatnonzero(exc > 0)), list(np.flatnonzero(dfc > 0))
        if s and b:
            corto = min(exc[s].sum(), dfc[b].sum())
            P = np.outer(exc[s] / exc[s].sum(), dfc[b] / dfc[b].sum()) * corto
            res.append(HourlyResult(k=k, P_star=P,
                                    pi_star=np.full(len(b), 600.0),
                                    seller_ids=s, buyer_ids=b))
        else:
            res.append(HourlyResult(k=k))
    fc = coincidencia_por_mecanismo(
        D, G, res, month_labels=np.repeat([202507, 202508], 48),
        include_c5=True)
    for esc, v in fc.items():
        if not np.isnan(v):
            assert -1e-12 <= v <= 1 + 1e-12, esc
    assert fc["C1"] == pytest.approx(0.0)
    assert fc["C5"] == pytest.approx(1.0)
    assert 0.0 <= simultaneidad_picos(D, G) <= 1.0


def test_run_comparison_lo_trae():
    from scenarios.comparison_engine import run_comparison
    rng = np.random.default_rng(12)
    N, T = 3, 96
    D = rng.uniform(0, 3, (N, T))
    G = rng.uniform(0, 4, (N, T))
    res = []
    for k in range(T):
        exc = np.maximum(G[:, k] - D[:, k], 0)
        dfc = np.maximum(D[:, k] - G[:, k], 0)
        s, b = list(np.flatnonzero(exc > 0)), list(np.flatnonzero(dfc > 0))
        if s and b:
            corto = min(exc[s].sum(), dfc[b].sum())
            P = np.outer(exc[s] / exc[s].sum(), dfc[b] / dfc[b].sum()) * corto
            res.append(HourlyResult(k=k, P_star=P,
                                    pi_star=np.full(len(b), 600.0),
                                    seller_ids=s, buyer_ids=b))
        else:
            res.append(HourlyResult(k=k))
    cr = run_comparison(
        D=D, G_klim=G, G_raw=G, p2p_results=res,
        pi_gs=np.full((N, T), 800.0), pi_gb=150.0,
        pi_bolsa=rng.uniform(80, 400, T), prosumer_ids=list(range(N)),
        consumer_ids=[], month_labels=np.repeat([202507, 202508], 48),
        pde=np.full(N, 1 / N), capacity=np.full(N, 17.55),
        component_c=40.0, tolls=np.full((N, T), 300.0))
    for esc in ("P2P", "C1", "C4", "P2P_colectivo"):
        assert 0.0 <= cr.coincidencia[esc] <= 1.0, esc
    assert 0.0 <= cr.simultaneidad <= 1.0
    assert "P2P_colectivo" in cr.equity_index
    assert -1.0 <= cr.equity_index["P2P_colectivo"] <= 1.0
