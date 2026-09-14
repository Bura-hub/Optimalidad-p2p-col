"""C3 descuenta los costos del mercado mayorista a lo que vende (D28).

Caso: el 0 inyecta 4 en h0 y el 1 inyecta 2 en h1; bolsa 150 y 200.
"""
import numpy as np
import pytest

from scenarios.scenario_c3_spot import run_c3_spot


def _fx():
    G = np.array([[5.0, 0.0], [0.0, 3.0]])
    D = np.array([[1.0, 1.0], [2.0, 1.0]])
    return D, G, np.full((2, 2), 800.0), np.array([150.0, 200.0])


def test_sin_costos_es_el_de_antes_al_bit():
    D, G, pgs, pb = _fx()
    a = run_c3_spot(D, G, pgs, pb, [0, 1], [])
    b = run_c3_spot(D, G, pgs, pb, [0, 1], [], mem_costs=None)
    assert a["aggregate"]["total_net_benefit"] == b["aggregate"]["total_net_benefit"]
    assert (a["neto_horario"] == b["neto_horario"]).all()


def test_descuenta_los_costos_del_excedente():
    D, G, pgs, pb = _fx()
    a = run_c3_spot(D, G, pgs, pb, [0, 1], [])
    b = run_c3_spot(D, G, pgs, pb, [0, 1], [], mem_costs=10.0)
    # 6 kWh de excedente por 10 (COP/kWh)
    assert (a["aggregate"]["total_net_benefit"]
            - b["aggregate"]["total_net_benefit"]) == pytest.approx(60.0)
    assert b["neto_horario"].sum() == pytest.approx(
        b["aggregate"]["total_net_benefit"])


def test_bolsa_bajo_los_costos_no_paga_negativo():
    D, G, pgs, _ = _fx()
    b = run_c3_spot(D, G, pgs, np.array([5.0, 5.0]), [0, 1], [],
                    mem_costs=10.0)
    assert b["aggregate"]["total_revenues"] == pytest.approx(0.0)


def test_la_matriz_horaria_suma_el_total_de_cada_agente_con_costos_y_paso():
    D, G, pgs, pb = _fx()
    mem = np.array([[5.0, 20.0], [12.0, 3.0]])
    b = run_c3_spot(D, G, pgs, pb, [0, 1], [], dt=0.5, mem_costs=mem)
    por_agente = np.array([b["per_agent"][n]["net_benefit"] for n in range(2)])
    assert np.allclose(b["neto_horario"].sum(axis=1), por_agente, rtol=1e-12)
