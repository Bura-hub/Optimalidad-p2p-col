"""La capacidad por usuario del art. 18 de la CREG 101 072 decide el caso del
art. 20 (C-206, 2026-09-27).

El art. 18 define la capacidad instalada por usuario del autogenerador
colectivo para fines comerciales como la suma de las capacidades instaladas
dividida entre el numero de usuarios (fronteras), contando tambien las que
solo consumen. Hasta C-206 el motor comparaba la planta mayor con los 100 kW
(y la hoja FA_CREG101072, el pico de generacion), que es la lectura por
planta del art. 25 num. 2 de la CREG 174, otro criterio.

Actividad 2.2.
"""
import warnings

import numpy as np
import pytest

from scenarios.scenario_c4_creg101072 import (
    capacidad_por_usuario_art18, resolve_caso_art20, regulatory_risk_c4,
)

E4_PLANTA_KW = 122.9          # 17,55 kWp x 7, redondeado como en el brief


def test_e4_con_11_fronteras_es_caso_1():
    cap = np.full(5, E4_PLANTA_KW)
    capu = capacidad_por_usuario_art18(cap, 11)
    assert capu == pytest.approx(5 * E4_PLANTA_KW / 11)
    assert capu == pytest.approx(55.86, abs=0.01)
    assert resolve_caso_art20(np.full(11, 1 / 11), cap, n_fronteras=11) == 1


def test_e4_con_5_fronteras_es_caso_2():
    cap = np.full(5, E4_PLANTA_KW)
    assert capacidad_por_usuario_art18(cap, 5) == pytest.approx(E4_PLANTA_KW)
    # Con cinco fronteras el reparto ya lo manda al caso 2; la capacidad
    # tambien, por si sola, con un reparto hipotetico por debajo del 10 %.
    assert resolve_caso_art20(np.full(5, 0.2), cap) == 2
    assert resolve_caso_art20(np.full(11, 1 / 11), cap, n_fronteras=5) == 2


@pytest.mark.parametrize("cap_kw", [0.0, 17.55, 50.0, 122.9, 199.0])
def test_comunidad_real_reparto_20_por_ciento_siempre_caso_2(cap_kw):
    assert resolve_caso_art20(np.full(5, 0.2), np.full(5, cap_kw)) == 2
    assert resolve_caso_art20(np.full(5, 0.2)) == 2


def test_frontera_de_solo_consumo_cuenta_en_el_denominador():
    # Dos plantas de 150 kW y una frontera que solo consume.
    con_consumo = np.array([150.0, 150.0, 0.0])
    assert capacidad_por_usuario_art18(con_consumo, 3) == pytest.approx(100.0)
    assert capacidad_por_usuario_art18(np.array([150.0, 150.0]), 3) == \
        pytest.approx(100.0)
    # Sin ella la media seria 150 kW.
    assert capacidad_por_usuario_art18(np.array([150.0, 150.0]), 2) == \
        pytest.approx(150.0)
    # Por defecto, resolve_caso_art20 cuenta una frontera por porcentaje,
    # incluidas las de solo consumo (reparto hipotetico < 10 %).
    pde = np.full(12, 1 / 12)
    cap = np.zeros(12); cap[:2] = 600.0             # 1200 / 12 = 100 kW
    assert resolve_caso_art20(pde, cap) == 1
    cap[:2] = 606.0                                  # 1212 / 12 = 101 kW
    assert resolve_caso_art20(pde, cap) == 2


@pytest.mark.parametrize("malo", [np.nan, np.inf, -np.inf])
def test_capacidad_no_finita_falla_en_voz_alta(malo):
    with pytest.raises(ValueError, match="no finita"):
        capacidad_por_usuario_art18(np.array([10.0, malo]), 11)
    with pytest.raises(ValueError, match="no finita"):
        resolve_caso_art20(np.full(11, 1 / 11), np.array([10.0, malo]),
                           n_fronteras=11)


def test_capacidad_negativa_falla():
    with pytest.raises(ValueError, match="negativa"):
        capacidad_por_usuario_art18(np.array([10.0, -1.0]), 11)


def test_menos_fronteras_que_plantas_falla():
    with pytest.raises(ValueError, match="fronteras"):
        capacidad_por_usuario_art18(np.full(5, 10.0), 4)
    with pytest.raises(ValueError, match="fronteras"):
        capacidad_por_usuario_art18(np.full(5, 10.0), 0)
    with pytest.raises(ValueError, match="entero"):
        capacidad_por_usuario_art18(np.full(5, 10.0), 5.5)
    # Por defecto el denominador es len(pde): cinco porcentajes para seis
    # plantas no cuadran (porcentajes bajo el 10 % para llegar a la prueba
    # de capacidad; aqui solo interesa el denominador).
    with pytest.raises(ValueError, match="fronteras"):
        resolve_caso_art20(np.full(5, 0.05), np.full(6, 10.0))


def test_regulatory_risk_c4_usa_la_capacidad_por_usuario():
    r = regulatory_risk_c4(np.full(5, 17.55))
    assert r["capacidad_por_usuario_kw"] == pytest.approx(17.55)
    assert r["capacity_exceeded"] is False
    # Antes comparaba la SUMA (150 kW > 100): ahora la media, 30 kW.
    r = regulatory_risk_c4(np.full(5, 30.0))
    assert r["capacity_exceeded"] is False
    r = regulatory_risk_c4(np.full(5, 122.9))
    assert r["capacity_exceeded"] is True


# ── FA-2 y FA-4 (analysis/feasibility.py) ───────────────────────────────────
def _comunidad(cap_kw, pico_kw):
    T = 48
    D = np.full((5, T), 50.0)
    G = np.zeros((5, T)); G[:, 12] = pico_kw
    return D, G, np.full(5, cap_kw)


def test_fa2_usa_la_capacidad_instalada_y_no_el_pico():
    from analysis.feasibility import analyze_creg_101072_compliance
    nombres = ["A", "B", "C", "D", "E"]
    # Pico de generacion de 150 kW con placa de 90: la condicion ii mira la
    # placa (90 kW por usuario), no el pico.
    D, G, cap = _comunidad(90.0, 150.0)
    rep = analyze_creg_101072_compliance(D, G, nombres, list(range(5)),
                                         verbose=False, capacity=cap)
    assert rep.capacidad_por_usuario_kw == pytest.approx(90.0)
    assert rep.rule_100kw_satisfied is True
    assert rep.rule_100kw_violations == []
    assert rep.max_capacity_by_agent["A"] == pytest.approx(90.0)
    assert rep.caso_art20 == 2                      # por el reparto del 20 %
    # Con 11 fronteras (seis de solo consumo) y placas de 122,9 kW: 55,9 kW.
    D, G, cap = _comunidad(E4_PLANTA_KW, 100.0)
    rep = analyze_creg_101072_compliance(D, G, nombres, list(range(5)),
                                         verbose=False, capacity=cap,
                                         n_fronteras=11)
    assert rep.capacidad_por_usuario_kw == pytest.approx(55.86, abs=0.01)
    assert rep.rule_100kw_satisfied is True
    # Con cinco fronteras la supera, y la superan todos los usuarios.
    rep = analyze_creg_101072_compliance(D, G, nombres, list(range(5)),
                                         verbose=False, capacity=cap)
    assert rep.rule_100kw_satisfied is False
    assert rep.rule_100kw_violations == nombres


def test_fa2_sin_capacidad_avisa():
    from analysis.feasibility import analyze_creg_101072_compliance
    D, G, _ = _comunidad(90.0, 150.0)
    with pytest.warns(UserWarning, match="C-206"):
        rep = analyze_creg_101072_compliance(D, G, list("ABCDE"),
                                             list(range(5)), verbose=False)
    assert rep.capacidad_por_usuario_kw == pytest.approx(150.0)


def test_fa2_capacidad_de_otra_forma_falla():
    from analysis.feasibility import analyze_creg_101072_compliance
    D, G, _ = _comunidad(90.0, 150.0)
    with pytest.raises(ValueError, match="capacity"):
        analyze_creg_101072_compliance(D, G, list("ABCDE"), list(range(5)),
                                       verbose=False, capacity=np.ones(4))


def test_fa4_escala_con_el_art18():
    from analysis.feasibility import analyze_scaling_risk
    D, G, cap = _comunidad(50.0, 999.0)
    with warnings.catch_warnings():
        warnings.simplefilter("error")          # con capacity, sin aviso
        r = analyze_scaling_risk(G, list(range(5)), list("ABCDE"), D,
                                 verbose=False, capacity=cap)
    # Suma 250, U = 5: la planta de A tendria que crecer a 300 kW (x6) para
    # que la media llegue a 100: (250 + 5 x 50) / 5 = 100.
    assert r["A"]["factor_limite_100kw"] == pytest.approx(6.0)
    assert r["A"]["3x_ok"] is True
    assert r["A"]["cap_kw"] == pytest.approx(50.0)
