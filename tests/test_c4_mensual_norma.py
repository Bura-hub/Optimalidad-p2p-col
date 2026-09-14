"""El colectivo mensual conforme a la norma (spec 4.6, verificacion 4)."""
import warnings

import numpy as np
import pytest

from scenarios.scenario_c4_creg101072 import (
    pde_por_regla, resolve_caso_art20, run_c4_creg101072,
)

warnings.filterwarnings("ignore")


def _c4(D, G, pb, pde, **kw):
    return run_c4_creg101072(D, G, np.full(D.shape, 800.0), pb, pde,
                             component_c=40.0, mode="monthly_hx", **kw)


def test_exceso_a_bolsa_de_su_hora_no_a_la_media():
    D = np.zeros((2, 3))
    G = np.array([[0.0, 10.0, 0.0], [0.0, 0.0, 0.0]])
    pb = np.array([200.0, 50.0, 800.0])
    r = _c4(D, G, pb, np.array([0.5, 0.5]))
    # 10 kWh de exceso en la hora 1, a 50; con la media del mes serian 3500.
    assert r["aggregate"]["total_surplus_revenue"] == pytest.approx(500.0)


def test_desglose_horario_suma_el_total_por_agente():
    rng = np.random.default_rng(2)
    D = rng.uniform(0, 3, (4, 96))
    G = rng.uniform(0, 5, (4, 96))
    pb = rng.uniform(80, 400, 96)
    mes = np.repeat([1, 2], 48)
    r = _c4(D, G, pb, np.full(4, 0.25), month_labels=mes)
    tot = np.array([r["per_agent"][n]["net_benefit"] for n in range(4)])
    np.testing.assert_allclose(r["neto_horario"].sum(axis=1), tot, rtol=1e-12)


def test_credito_es_el_minimo_entre_asignacion_y_deficit_del_mes():
    D = np.array([[0.0, 0.0], [2.0, 2.0]])
    G = np.array([[6.0, 6.0], [0.0, 0.0]])
    r = _c4(D, G, np.full(2, 100.0), np.array([0.5, 0.5]))
    # Fondo 12; cada uno recibe 6. El 0 no importa (todo exceso), el 1 importa
    # 4 (4 credito, 2 exceso).
    assert r["aggregate"]["total_E_excedente_t2"] == pytest.approx(8.0)


def test_porcentaje_distinto_cada_mes():
    D = np.array([[0.0] * 4, [9.0] * 4])
    G = np.array([[4.0] * 4, [0.0] * 4])
    mes = np.array([1, 1, 2, 2])
    pm = {1: np.array([0.0, 1.0]), 2: np.array([1.0, 0.0])}
    r = _c4(D, G, np.full(4, 100.0), np.array([0.5, 0.5]),
            month_labels=mes, pde_mensual=pm)
    # Mes 1: todo al 1, que lo permuta (8 kWh a 760). Mes 2: todo al 0, que no
    # importa: 8 kWh a bolsa.
    assert r["per_agent"][1]["pde_credits"] == pytest.approx(8 * 760.0)
    assert r["per_agent"][0]["surplus_revenue"] == pytest.approx(8 * 100.0)


def test_el_caso_cambia_de_10_a_11_fronteras_iguales():
    assert resolve_caso_art20(np.full(10, 0.1)) == 2
    assert resolve_caso_art20(np.full(11, 1 / 11)) == 1


def test_reglas_de_porcentaje():
    D = np.array([[1.0, 3.0], [3.0, 1.0]])
    G = np.array([[4.0, 0.0], [0.0, 0.0]])
    mes = np.array([1, 2])
    for regla in ("igual", "consumo", "aporte", "generacion"):
        pm = pde_por_regla(regla, G, D, mes)
        for v in pm.values():
            assert v.sum() == pytest.approx(1.0)
    np.testing.assert_allclose(pde_por_regla("consumo", G, D, mes)[1],
                               [0.25, 0.75])
    np.testing.assert_allclose(pde_por_regla("aporte", G, D, mes)[1], [1, 0])
    # Mes sin excedente: el aporte cae al reparto igual.
    np.testing.assert_allclose(pde_por_regla("aporte", G, D, mes)[2],
                               [0.5, 0.5])


def _cr(capacidad):
    from core.ems_p2p import HourlyResult
    from scenarios.comparison_engine import run_comparison
    rng = np.random.default_rng(8)
    D = rng.uniform(0, 3, (5, 48))
    G = rng.uniform(0, 4, (5, 48))
    return run_comparison(
        D=D, G_klim=G, G_raw=G,
        p2p_results=[HourlyResult(k=k) for k in range(48)],
        pi_gs=np.full((5, 48), 800.0), pi_gb=150.0,
        pi_bolsa=np.full(48, 150.0), prosumer_ids=list(range(5)),
        consumer_ids=[], capacity=capacidad, component_c=40.0,
        tolls=np.full((5, 48), 300.0), month_labels=np.repeat([1, 2], 24))


def test_c4_es_el_mensual_y_el_alias_coincide():
    cr = _cr(np.full(5, 17.55))
    assert cr.net_benefit["C4"] == cr.net_benefit["C4_mensual"]
    np.testing.assert_allclose(cr.pde, 0.2)
    np.testing.assert_allclose(cr.neto_horario["C4"].sum(axis=1),
                               cr.net_benefit_per_agent["C4"], rtol=1e-12)


def test_contrafactico_de_11_fronteras_respeta_la_capacidad():
    chica = _cr(np.full(5, 17.55)).contrafacticos
    grande = _cr(np.full(5, 122.85)).contrafacticos
    assert chica["C4_11_fronteras"]["caso_art20"] == 1
    assert grande["C4_11_fronteras"]["caso_art20"] == 2
    # Revision final (I-4): y el mercado por la via del colectivo en el
    # mismo caso favorable, que tambien sigue la capacidad.
    assert chica["P2P_colectivo_11_fronteras"]["caso_art20"] == 1
    assert grande["P2P_colectivo_11_fronteras"]["caso_art20"] == 2
    assert set(chica) == {"C4_11_fronteras", "C4_regla_consumo",
                          "C4_regla_aporte", "C4_regla_generacion",
                          "P2P_colectivo_11_fronteras"}


def test_suma_de_mas_de_un_megavatio_detiene():
    # Verificacion 9: 5 x 210 kW = 1.050 kW; el colectivo caeria en el caso 3
    # del art. 20, que el motor no modela.
    with pytest.raises(ValueError, match="AGPE"):
        _cr(np.full(5, 210.0))


def test_las_graficas_no_dibujan_el_alias_dos_veces():
    # Fix round 1 (C-178): visualization/plots.py contrastaba "C4" horario
    # contra "C4_mensual"; ahora son el mismo objeto y las figuras deben
    # detectarlo para no repetir la barra.
    from visualization.plots import _c4_es_alias
    cr = _cr(np.full(5, 17.55))
    assert _c4_es_alias(cr) is True
    esc = [e for e in ["P2P", "C1", "C2", "C3", "C4", "C4_mensual"]
           if e in cr.net_benefit_per_agent
           and not (e == "C4_mensual" and _c4_es_alias(cr))]
    assert "C4" in esc
    assert "C4_mensual" not in esc
