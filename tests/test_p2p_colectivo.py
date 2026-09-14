"""El mercado entre pares liquidado por la via del colectivo (spec 4.10, verif. 7)."""
import warnings
from types import SimpleNamespace

import numpy as np
import pytest

from scenarios.scenario_c1_creg174 import run_c1_creg174
from scenarios.scenario_c4_creg101072 import pde_por_regla, run_c4_creg101072
from scenarios.scenario_p2p_colectivo import (pde_mensual_desde_mercado,
                                              run_p2p_colectivo)

warnings.filterwarnings("ignore")


def _horas(T, tratos=()):
    out = [SimpleNamespace(k=k, P_star=None, pi_star=None, seller_ids=[],
                           buyer_ids=[]) for k in range(T)]
    for k, sids, bids, P, pi in tratos:
        out[k] = SimpleNamespace(k=k, P_star=np.asarray(P, float),
                                 pi_star=np.asarray(pi, float),
                                 seller_ids=sids, buyer_ids=bids)
    return out


def test_sin_intercambios_es_el_colectivo_que_reparte_por_aporte():
    rng = np.random.default_rng(4)
    D = rng.uniform(0, 3, (3, 48))
    G = rng.uniform(0, 4, (3, 48))
    pi_gs = np.full((3, 48), 800.0)
    pb = rng.uniform(80, 400, 48)
    mes = np.repeat([1, 2], 24)
    r = run_p2p_colectivo(_horas(48), D, G, pi_gs, pb, month_labels=mes,
                          component_c=40.0, caso=1)
    c4 = run_c4_creg101072(D, G, pi_gs, pb, np.full(3, 1 / 3),
                           component_c=40.0, mode="monthly_hx",
                           month_labels=mes, caso=1,
                           pde_mensual=pde_por_regla("aporte", G, D, mes))
    assert r["aggregate"]["total_net_benefit"] == pytest.approx(
        c4["aggregate"]["total_net_benefit"], rel=1e-12)


def _caso_sin_cupo_agotado():
    D = np.array([[1.0, 10, 10, 10], [3, 3, 3, 3]])
    G = np.array([[5.0, 0, 0, 0], [0, 0, 0, 0]])
    horas = _horas(4, [(0, [0], [1], [[3.0]], [500.0])])
    return D, G, horas, np.full((2, 4), 800.0), np.full(4, 150.0)


def test_el_porcentaje_es_la_energia_que_termina_siendo_de_cada_uno():
    D, G, horas, _, _ = _caso_sin_cupo_agotado()
    pm = pde_mensual_desde_mercado(horas, D, G)
    # El 0 exporta 1 sin colocar; el 1 compra 3 dentro. Fondo 4.
    np.testing.assert_allclose(pm[0], [0.25, 0.75])


@pytest.mark.parametrize("caso, esperado", [(1, 0.0), (2, -4 * 300.0)])
def test_misma_tarifa_y_sin_cupo_agotado_no_crea_valor(caso, esperado):
    D, G, horas, pi_gs, pb = _caso_sin_cupo_agotado()
    r = run_p2p_colectivo(horas, D, G, pi_gs, pb, component_c=40.0,
                          tolls=np.full((2, 4), 300.0), caso=caso)
    c1 = run_c1_creg174(D, G, pi_gs, pb, [0, 1], None, component_c=40.0)
    ganancia = (r["aggregate"]["total_net_benefit"]
                - c1["aggregate"]["total_net_benefit"])
    assert ganancia == pytest.approx(esperado, abs=1e-9)
    assert r["pagos_internos"].sum() == pytest.approx(0.0, abs=1e-12)
