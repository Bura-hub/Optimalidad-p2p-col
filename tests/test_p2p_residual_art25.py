"""El residual del mercado entre pares se liquida por el articulo 25 (D2, D3).

Verificacion 3 de la especificacion: con volumen transado nulo, el mercado
liquida exactamente como la autogeneracion individual. Verificacion 6: la
brecha entre los dos es el ancho de la banda real por la energia transada.
"""
from types import SimpleNamespace

import numpy as np
import pytest

from scenarios.comparison_engine import _p2p_monetary_benefit
from scenarios.scenario_c1_creg174 import run_c1_creg174


def _horas(T, trato=None):
    out = [SimpleNamespace(k=k, P_star=None, pi_star=None,
                           seller_ids=[], buyer_ids=[]) for k in range(T)]
    if trato:
        for k, sids, bids, P, pi in trato:
            out[k] = SimpleNamespace(k=k, P_star=np.asarray(P, dtype=float),
                                     pi_star=np.asarray(pi, dtype=float),
                                     seller_ids=sids, buyer_ids=bids)
    return out


def test_sin_intercambios_el_mercado_liquida_como_c1():
    rng = np.random.default_rng(5)
    N, T = 3, 48
    D = rng.uniform(0, 4, (N, T))
    G = rng.uniform(0, 6, (N, T))
    mes = np.array([1] * 24 + [2] * 24)
    pi_gs = np.full((N, T), 800.0)
    pb = rng.uniform(80, 400, T)
    ded = np.full((N, T), 40.0)
    p2p = _p2p_monetary_benefit(_horas(T), D, G, pi_gs, 150.0, [0, 1, 2],
                                pi_bolsa=pb, month_labels=mes, deduccion=ded)
    c1 = run_c1_creg174(D, G, pi_gs, pb, [0, 1, 2], mes, component_c=40.0)
    for n in range(N):
        assert p2p[n] == pytest.approx(c1[n]["net_benefit"], rel=1e-12)


def test_sin_intercambios_con_numeral_2_el_residual_liquida_como_c1():
    # Revision final: con una planta de mas de 100 kW el residual del mercado
    # se deduce con el numeral 2 (Cv + T+D+PR+R), igual que C1.
    from core.opciones_externas import deduccion_art25
    rng = np.random.default_rng(11)
    N, T = 3, 48
    D = rng.uniform(0, 4, (N, T))
    G = rng.uniform(0, 6, (N, T))
    mes = np.array([1] * 24 + [2] * 24)
    pi_gs = np.full((N, T), 800.0)
    pb = rng.uniform(80, 400, T)
    cap = np.array([122.85, 17.55, 17.55])
    tolls = np.full((N, T), 250.0)
    ded = deduccion_art25(np.full((N, T), 40.0), tolls, cap)
    p2p = _p2p_monetary_benefit(_horas(T), D, G, pi_gs, 150.0, [0, 1, 2],
                                pi_bolsa=pb, month_labels=mes, deduccion=ded)
    c1 = run_c1_creg174(D, G, pi_gs, pb, [0, 1, 2], mes, component_c=40.0,
                        capacidad_kw=cap, tolls=tolls)
    for n in range(N):
        assert p2p[n] == pytest.approx(c1[n]["net_benefit"], rel=1e-12)
    # Y el numeral 2 muerde: con el numeral 1 la planta grande ganaria mas.
    c1_n1 = run_c1_creg174(D, G, pi_gs, pb, [0, 1, 2], mes, component_c=40.0)
    assert p2p[0] < c1_n1[0]["net_benefit"]
    assert p2p[1] == pytest.approx(c1_n1[1]["net_benefit"], rel=1e-12)


def test_brecha_es_el_ancho_real_por_la_energia():
    # Vendedor 0 (tarifa 780, Cv 40) vende 3 kWh al comprador 1 (tarifa 800)
    # a 500. Nadie supera su cupo. Brecha = 3 x (800 - (780 - 40)) = 180.
    D = np.array([[1.0, 10.0, 10.0, 10.0], [3.0, 3.0, 3.0, 3.0]])
    G = np.array([[5.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]])
    pi_gs = np.array([[780.0] * 4, [800.0] * 4])
    pb = np.full(4, 150.0)
    ded = np.full((2, 4), 40.0)
    horas = _horas(4, [(0, [0], [1], [[3.0]], [500.0])])
    p2p = _p2p_monetary_benefit(horas, D, G, pi_gs, 150.0, [0, 1],
                                pi_bolsa=pb, month_labels=None, deduccion=ded)
    c1 = run_c1_creg174(D, G, pi_gs, pb, [0, 1], None, component_c=40.0)
    brecha = p2p.sum() - c1["aggregate"]["total_net_benefit"]
    assert brecha == pytest.approx(180.0, abs=1e-9)


def test_lo_que_supera_el_cupo_va_a_la_bolsa_de_su_hora():
    # Un solo agente que no importa nada: todo su residual es exceso.
    D = np.array([[1.0, 0.0, 0.0]])
    G = np.array([[5.0, 2.0, 0.0]])
    pi_gs = np.full((1, 3), 800.0)
    pb = np.array([100.0, 300.0, 999.0])
    p2p = _p2p_monetary_benefit(_horas(3), D, G, pi_gs, 150.0, [0],
                                pi_bolsa=pb, deduccion=np.full((1, 3), 40.0))
    # autoconsumo 1 x 800 + exceso 4 x 100 + 2 x 300
    assert p2p[0] == pytest.approx(800.0 + 400.0 + 600.0)


def test_sin_deduccion_conserva_el_residual_a_bolsa():
    D = np.array([[1.0, 5.0]])
    G = np.array([[3.0, 0.0]])
    pi_gs = np.full((1, 2), 800.0)
    pb = np.array([100.0, 100.0])
    viejo = _p2p_monetary_benefit(_horas(2), D, G, pi_gs, 150.0, [0],
                                  pi_bolsa=pb)
    assert viejo[0] == pytest.approx(800.0 + 2.0 * 100.0)


def _comparacion(piso_vendedor):
    import warnings
    from core.ems_p2p import HourlyResult
    from scenarios.comparison_engine import run_comparison
    D = np.array([[1.0, 10, 10, 10], [3, 3, 3, 3]])
    G = np.array([[5.0, 0, 0, 0], [0, 0, 0, 0]])
    pi_gs = np.array([[780.0] * 4, [800.0] * 4])
    res = [HourlyResult(k=k) for k in range(4)]
    res[0] = HourlyResult(k=0, P_star=np.array([[3.0]]),
                          pi_star=np.array([500.0]),
                          seller_ids=[0], buyer_ids=[1])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return run_comparison(
            D=D, G_klim=G, G_raw=G, p2p_results=res, pi_gs=pi_gs, pi_gb=150.0,
            pi_bolsa=np.full(4, 150.0), prosumer_ids=[0, 1], consumer_ids=[],
            pde=np.full(2, 0.5), piso_agente=np.full((2, 4), piso_vendedor),
            component_c=40.0)


def test_contrato_firmado_da_el_total_del_mercado():
    # H-33 y H-78: mismos flujos, el precio se cancela en el total.
    cr = _comparacion(740.0)
    assert cr.net_benefit["C2"] == pytest.approx(cr.net_benefit["P2P"])
    assert cr.net_benefit["P2P"] == pytest.approx(3920.0)


def test_contrato_sin_firmar_vuelve_a_la_autogeneracion_individual():
    # Piso 810 por encima del techo 800: la pareja no firma. Los 3 kWh vuelven
    # al residual del vendedor, que los permuta, y el comprador los importa.
    cr = _comparacion(810.0)
    assert cr.contrato_c2["parejas_sin_firmar"] == 1
    assert cr.net_benefit["C2"] == pytest.approx(cr.net_benefit["C1"])


def test_contrato_ignora_horas_nan_igual_que_el_mercado():
    # Fix ronda 1: una hora con NaN Y banda invertida (piso 810 > techo 800)
    # antes dejaba sin_firmar en NaN y lo propagaba via _residual_art25 a
    # todo el horizonte del agente. Con la guarda, esa hora no aporta nada,
    # igual que si el mercado no hubiera corrido esa hora.
    import warnings
    from core.ems_p2p import HourlyResult
    from scenarios.comparison_engine import run_comparison
    D = np.array([[1.0, 10, 10, 10], [3, 3, 3, 3]])
    G = np.array([[5.0, 0, 0, 0], [0, 0, 0, 0]])
    pi_gs = np.array([[780.0] * 4, [800.0] * 4])

    def _correr(p_star_hora0):
        res = [HourlyResult(k=k) for k in range(4)]
        if p_star_hora0 is not None:
            res[0] = HourlyResult(k=0, P_star=p_star_hora0,
                                  pi_star=np.array([500.0]),
                                  seller_ids=[0], buyer_ids=[1])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return run_comparison(
                D=D, G_klim=G, G_raw=G, p2p_results=res, pi_gs=pi_gs,
                pi_gb=150.0, pi_bolsa=np.full(4, 150.0),
                prosumer_ids=[0, 1], consumer_ids=[], pde=np.full(2, 0.5),
                piso_agente=np.full((2, 4), 810.0), component_c=40.0)

    cr_nan     = _correr(np.array([[np.nan]]))
    cr_sin_esa = _correr(None)
    assert np.isfinite(cr_nan.net_benefit["C2"])
    assert cr_nan.net_benefit["C2"] == pytest.approx(
        cr_sin_esa.net_benefit["C2"])
