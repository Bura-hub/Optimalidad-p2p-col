"""La autogeneracion remota con la mecanica de la CREG 101 099 (spec 4.7, verif. 5).

Fixture de tests/test_c5_agr_creg101099.py: N=3, T=2, tasa 500, tarifa 800,
bolsa [150, 200], MEM 10. h0: el 0 inyecta 4; importan el 1 (2) y el 2 (1):
contrato 3, sobrante 1. h1: el 2 inyecta 2; importan el 0 (1) y el 1 (2):
contrato 2. Total sin devolucion del CERE = 4240.
"""
import numpy as np
import pytest

from scenarios.scenario_c5_agr_creg101099 import run_c5_agr_creg101099


def _fx():
    G = np.array([[5.0, 0.0], [0.0, 0.0], [0.0, 3.0]])
    D = np.array([[1.0, 1.0], [2.0, 2.0], [1.0, 1.0]])
    kw = dict(pi_bolsa=np.array([150.0, 200.0]),
              g_component=np.full((3, 2), 300.0),
              cvm_component=np.full((3, 2), 170.0),
              cot_component=np.full((3, 2), 40.0),
              mem_costs=np.full((3, 2), 10.0))
    return D, G, np.full((3, 2), 800.0), kw


def test_contrato_despachado_es_el_minimo_horario():
    D, G, pi_gs, kw = _fx()
    r = run_c5_agr_creg101099(D, G, pi_gs, pi_contrato=300.0, **kw)
    assert r["hourly"]["contrato"].tolist() == [3.0, 2.0]
    assert r["aggregate"]["kwh_contrato"] == pytest.approx(5.0)


def test_la_energia_se_conserva():
    D, G, pi_gs, kw = _fx()
    r = run_c5_agr_creg101099(D, G, pi_gs, pi_contrato=300.0, **kw)
    for n in range(3):
        pa = r["per_agent"][n]
        assert (pa["E_auto"] + pa["E_contrato"] + pa["E_sobrante"]
                == pytest.approx(float(G[n].sum())))


@pytest.mark.parametrize("pc", [0.0, 300.0, 500.0])
def test_el_precio_del_contrato_reparte_y_no_crea(pc):
    D, G, pi_gs, kw = _fx()
    r = run_c5_agr_creg101099(D, G, pi_gs, pi_contrato=pc, **kw)
    assert r["aggregate"]["total_net_benefit"] == pytest.approx(4240.0)


def test_reparto_con_precio_de_contrato():
    D, G, pi_gs, kw = _fx()
    r = run_c5_agr_creg101099(D, G, pi_gs, pi_contrato=300.0, **kw)
    pa = r["per_agent"]
    assert pa[0]["net_benefit"] == pytest.approx(800 + 900 + (2 / 3) * 200 + 140)
    assert pa[1]["net_benefit"] == pytest.approx((2 + 4 / 3) * 200)
    assert pa[2]["net_benefit"] == pytest.approx(800 + 600 + 200)


def test_devolucion_del_cere_con_porcentaje_fijo():
    D, G, pi_gs, kw = _fx()
    sin = run_c5_agr_creg101099(D, G, pi_gs, pi_contrato=300.0, **kw)
    con = run_c5_agr_creg101099(D, G, pi_gs, pi_contrato=300.0, cere=50.0,
                                **kw)
    assert sin["regulatory"]["cere_omitido"] is True
    assert con["regulatory"]["cere_omitido"] is False
    # Porcentaje igual (1/3). h0: 4/3 cada una, tope su deficit -> 4/3 y 1.
    # h1: 2/3 cada una -> 2/3 y 2/3. Total 11/3 kWh a 50.
    assert con["aggregate"]["total_devolucion_cere"] == pytest.approx(50 * 11 / 3)
