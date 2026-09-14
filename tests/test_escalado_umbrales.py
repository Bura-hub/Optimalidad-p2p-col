"""Escalado de la comunidad y umbrales de tamano (spec 4.11, verificacion 8 y 9)."""
import numpy as np
import pytest

from data.capacidad_instalada import KWP_POR_PLANTA, capacidad_instalada
from data.escalado import escala_comunidad, lee_factor

NOMBRES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]


def _serie():
    rng = np.random.default_rng(3)
    return rng.uniform(1, 5, (5, 48)), rng.uniform(0, 3, (5, 48))


def test_capacidad_por_planta():
    np.testing.assert_allclose(capacidad_instalada(NOMBRES), 17.55)
    np.testing.assert_allclose(capacidad_instalada(NOMBRES, np.full(5, 7.0)),
                               122.85)


def test_lee_factor():
    assert lee_factor("7") == 7.0
    assert lee_factor("1/7") == pytest.approx(1 / 7)


def test_lee_escala_agente():
    from data.escalado import lee_escala_agente
    assert lee_escala_agente("UCC:neto_cero, Udenar:1/2") == {
        "UCC": "neto_cero", "Udenar": 0.5}
    assert lee_escala_agente(None) == {}


def test_escalado_uniforme():
    D, G = _serie()
    D2, G2, f = escala_comunidad(D, G, NOMBRES, factor_generacion=3.0,
                                 factor_demanda=0.5)
    np.testing.assert_allclose(G2, 3.0 * G)
    np.testing.assert_allclose(D2, 0.5 * D)
    np.testing.assert_allclose(f, 3.0)


def test_un_solo_inversor_a_neto_cero():
    D, G = _serie()
    D2, G2, f = escala_comunidad(D, G, NOMBRES,
                                 generacion_por_agente={"UCC": "neto_cero"})
    assert G2[2].sum() == pytest.approx(D[2].sum())
    np.testing.assert_allclose(np.delete(G2, 2, 0), np.delete(G, 2, 0))
    assert f[2] == pytest.approx(D[2].sum() / G[2].sum())


def test_todas_a_neto_cero():
    D, G = _serie()
    _, G2, _ = escala_comunidad(D, G, NOMBRES, neto_cero=True)
    np.testing.assert_allclose(G2.sum(axis=1), D.sum(axis=1))


def test_nombre_desconocido_detiene():
    D, G = _serie()
    with pytest.raises(ValueError, match="Nadie"):
        escala_comunidad(D, G, NOMBRES, generacion_por_agente={"Nadie": 2.0})


@pytest.mark.parametrize("escenario", ["C1", "C3", "C4"])
def test_homogeneidad_sin_umbrales(escenario):
    # Verificacion 8: G y D por el mismo factor, sin cruzar ningun umbral,
    # dan el factor por la base en los escenarios regulados.
    import warnings
    from scenarios.scenario_c1_creg174 import run_c1_creg174
    from scenarios.scenario_c3_spot import run_c3_spot
    from scenarios.scenario_c4_creg101072 import run_c4_creg101072
    D, G = _serie()
    pi_gs = np.full((5, 48), 800.0)
    pb = np.linspace(100, 300, 48)
    mes = np.array([1] * 24 + [2] * 24)
    ids = list(range(5))

    def total(D_, G_):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if escenario == "C1":
                r = run_c1_creg174(D_, G_, pi_gs, pb, ids, mes,
                                   component_c=40.0)
            elif escenario == "C3":
                r = run_c3_spot(D_, G_, pi_gs, pb, ids, [])
            else:
                r = run_c4_creg101072(D_, G_, pi_gs, pb, np.full(5, 0.2),
                                      component_c=40.0, mode="monthly_hx",
                                      month_labels=mes)
        return r["aggregate"]["total_net_benefit"]

    assert total(3 * D, 3 * G) == pytest.approx(3 * total(D, G), rel=1e-12)
