"""Tarea R y D72 (Act 4.2): el análisis de optimalidad, con el beneficio
liquidado, mes a mes y sin mezclar conjuntos de horas.

1. Conjuntos. En el canon 2026-09-19, E4 imprimía «P2P superior» con B_P2P
   24,9 millones de COP por debajo de B_C4: los totales sumaban las 6 144
   horas y la diferencia, y con ella el veredicto, solo las activas. Aquí se
   reproduce el mismo cuadro con tres horas sintéticas.
2. El mensual (D72): P2P − C4 de cada mes, por institución y en la
   comunidad, quién domina cada mes y el total del horizonte.
3. La liquidación: el análisis falla si su total no es el liquidado, y el
   beneficio horario es exactamente el de `run_comparison`.
"""
from types import SimpleNamespace

import numpy as np
import pytest

from analysis.optimality import (COMUNIDAD, analyze_hourly_dominance,
                                 analyze_monthly_dominance,
                                 exporta_optimalidad,
                                 print_optimality_report)


def _res(activa):
    if activa:
        return SimpleNamespace(P_star=np.array([[2.0]]),
                               pi_star=np.array([500.0]),
                               seller_ids=[0], buyer_ids=[1])
    return SimpleNamespace(P_star=None, pi_star=None,
                           seller_ids=[0], buyer_ids=[1])


def _caso_e4_sintetico(**kw):
    """Una hora con mercado donde gana el P2P (+240) y dos sin mercado donde
    gana el colectivo (−450 cada una), que en el horizonte pesan más."""
    D = np.array([[1.0, 1.0, 1.0], [2.0, 2.0, 2.0]])
    G = np.array([[3.0, 2.0, 2.0], [0.0, 0.0, 0.0]])
    p2p = np.array([[1240.0, 700.0, 700.0],
                    [500.0, 200.0, 200.0]])       # 1 740 | 900 | 900
    c4 = np.array([[1000.0, 1000.0, 1000.0],
                   [500.0, 350.0, 350.0]])        # 1 500 | 1 350 | 1 350
    if "referencia_liquidacion" not in kw:
        kw["sin_referencia"] = True
    return analyze_hourly_dominance(
        p2p_horario=p2p, c4_horario=c4,
        p2p_results=[_res(True), _res(False), _res(False)],
        D=D, G_klim=G, month_labels=np.array([202504, 202504, 202505]),
        agent_names=["Udenar", "Mariana"], **kw)


# ── 1. Conjuntos de horas ─────────────────────────────────────────────────────

def test_totales_y_diferencia_del_mismo_conjunto():
    s = _caso_e4_sintetico()
    assert s.B_p2p_total == pytest.approx(3540.0)
    assert s.B_c4_total == pytest.approx(4200.0)
    assert s.delta_horizonte == pytest.approx(-660.0)
    assert s.B_p2p_activas == pytest.approx(1740.0)
    assert s.B_c4_activas == pytest.approx(1500.0)
    assert s.delta_total == pytest.approx(240.0)          # solo activas
    assert s.delta_inactivas == pytest.approx(-900.0)
    # El cuadro de E4: activas a favor del P2P, horizonte no.
    assert s.delta_total > 0 > s.delta_horizonte
    assert s.n_active == 1 and s.n_p2p_dom == 1 and s.n_inactive == 2


def test_el_veredicto_del_horizonte_sale_de_su_diferencia(capsys):
    print_optimality_report(_caso_e4_sintetico())
    out = capsys.readouterr().out
    # El mes va primero y la hora después.
    assert out.index("1. Mes a mes") < out.index("2. Horizonte") \
        < out.index("3. Hora a hora (DESCRIPTIVO)")
    horizonte = out[out.index("2. Horizonte"):out.index("3. Hora a hora")]
    assert "3,540" in horizonte and "4,200" in horizonte
    assert "-660" in horizonte and "C4 superior" in horizonte
    assert "P2P superior" not in horizonte
    hora = out[out.index("3. Hora a hora"):]
    assert "DESCRIPTIVA (D72)" in hora
    assert "Delta en horas con mercado" in hora and "240" in hora
    assert "Delta en horas sin mercado (2 h)" in hora and "-900" in hora
    assert "veredictos contrarios" in hora


def test_beneficio_no_finito_falla_en_voz_alta():
    D = np.ones((2, 1))
    with pytest.raises(ValueError, match="no finito"):
        analyze_hourly_dominance(
            p2p_horario=np.array([[np.nan], [1.0]]),
            c4_horario=np.ones((2, 1)), p2p_results=[_res(False)],
            D=D, G_klim=D)


def test_sin_beneficio_liquidado_no_hay_analisis():
    D = np.ones((2, 1))
    with pytest.raises(ValueError, match="obligatorio"):
        analyze_hourly_dominance(p2p_horario=None, c4_horario=np.ones((2, 1)),
                                 p2p_results=[_res(False)], D=D, G_klim=D)


def test_empate_dentro_de_un_peso():
    s = _caso_e4_sintetico()
    from analysis.optimality import _veredicto
    assert _veredicto(0.0) == "empate" and _veredicto(0.9) == "empate"
    assert _veredicto(1.5) == "P2P superior"
    assert _veredicto(-1.5) == "C4 superior"
    assert s.mensual.cuenta(COMUNIDAD) == {"P2P": 0, "C4": 2, "empate": 0}


# ── 2. El mensual (D72) ───────────────────────────────────────────────────────

def test_mensual_por_institucion_y_comunidad():
    # Dos meses; Udenar gana abril y pierde mayo, Mariana al revés, y un
    # empate exacto de Mariana en junio.
    p2p = np.array([[10.0, 20.0, 5.0, 5.0, 3.0],
                    [1.0, 1.0, 50.0, 0.0, 4.0]])
    c4 = np.array([[8.0, 12.0, 9.0, 9.0, 3.0],
                   [2.0, 2.0, 30.0, 10.0, 4.0]])
    mes = np.array([202504, 202504, 202505, 202505, 202506])
    mm = analyze_monthly_dominance(p2p, c4, mes, ["Udenar", "Mariana"])
    assert mm.meses == ["2025-04", "2025-05", "2025-06"]
    assert mm.agentes == ["Udenar", "Mariana", COMUNIDAD]
    np.testing.assert_allclose(mm.delta[0], [10.0, -8.0, 0.0])
    np.testing.assert_allclose(mm.delta[1], [-2.0, 10.0, 0.0])
    np.testing.assert_allclose(mm.delta[2], [8.0, 2.0, 0.0])
    assert list(mm.domina[0]) == ["P2P", "C4", "empate"]
    assert mm.cuenta("Mariana") == {"P2P": 1, "C4": 1, "empate": 1}
    assert mm.cuenta(COMUNIDAD) == {"P2P": 2, "C4": 0, "empate": 1}
    assert mm.total("Udenar") == pytest.approx((43.0, 41.0, 2.0))
    assert mm.total(COMUNIDAD)[2] == pytest.approx(10.0)
    # El horizonte de cada agente es la suma de sus meses y la comunidad la
    # suma de los agentes.
    r = mm.resumen().set_index("agente")
    assert r.loc[COMUNIDAD, "delta_COP"] == pytest.approx(
        r.loc["Udenar", "delta_COP"] + r.loc["Mariana", "delta_COP"])
    assert r.loc[COMUNIDAD, "veredicto_horizonte"] == "P2P superior"
    t = mm.tabla()
    assert len(t) == 3 * 3
    assert t["delta_COP"].sum() == pytest.approx(2 * 10.0)


def test_mensual_sin_calendario_es_un_solo_periodo():
    mm = analyze_monthly_dominance(np.ones((2, 4)), np.zeros((2, 4)))
    assert mm.meses == ["horizonte"] and mm.agentes[:2] == ["A1", "A2"]
    assert mm.total(COMUNIDAD) == pytest.approx((8.0, 0.0, 8.0))


def test_el_mensual_suma_lo_mismo_que_el_horario(tmp_path):
    s = _caso_e4_sintetico()
    assert s.mensual.total(COMUNIDAD) == pytest.approx(
        (s.B_p2p_total, s.B_c4_total, s.delta_horizonte))
    assert [h.mes for h in s.hourly_data] == ["2025-04", "2025-04", "2025-05"]
    rutas = exporta_optimalidad(s, str(tmp_path))
    assert [p.split("optimalidad_")[-1] for p in rutas] == [
        "mensual.csv", "resumen.csv", "horaria.csv"]


def test_mensual_rechaza_formas_distintas():
    with pytest.raises(ValueError, match="mismo horizonte"):
        analyze_monthly_dominance(np.ones((2, 4)), np.ones((2, 3)))
    with pytest.raises(ValueError, match="etiquetas"):
        analyze_monthly_dominance(np.ones((2, 4)), np.ones((2, 4)), [1, 2])


# ── 3. La liquidación ─────────────────────────────────────────────────────────

def test_falla_si_el_horario_no_cuadra_con_la_liquidacion():
    s = _caso_e4_sintetico(referencia_liquidacion={"P2P": 3540.0,
                                                   "C4": 4200.0})
    assert s.B_p2p_total == pytest.approx(3540.0)
    with pytest.raises(ValueError, match="no es el de la liquidacion"):
        _caso_e4_sintetico(referencia_liquidacion={"P2P": 3542.0})
    with pytest.raises(ValueError, match="no es finita"):
        _caso_e4_sintetico(referencia_liquidacion={"P2P": float("nan"),
                                                   "C4": 4200.0})


def test_la_referencia_no_se_omite_en_silencio(capsys):
    """M-1: sin referencia hay que pedirlo, y se avisa; con referencia,
    P2P y C4 son obligatorios y el reparto por agente se comprueba."""
    with pytest.raises(ValueError, match="falta referencia_liquidacion"):
        _caso_e4_sintetico(referencia_liquidacion=None)
    with pytest.raises(ValueError, match="no trae 'C4'"):
        _caso_e4_sintetico(referencia_liquidacion={"P2P": 3540.0})
    with pytest.raises(ValueError, match="no trae 'C4'"):
        _caso_e4_sintetico(referencia_liquidacion={"P2P": 3540.0,
                                                   "C4": None})
    ok = {"P2P": 3540.0, "C4": 4200.0,
          "P2P_por_agente": [2640.0, 900.0], "C4_por_agente": [3000.0, 1200.0]}
    _caso_e4_sintetico(referencia_liquidacion=ok)
    malo = dict(ok, P2P_por_agente=[2540.0, 1000.0])   # mismo total
    with pytest.raises(ValueError, match="del agente 0"):
        _caso_e4_sintetico(referencia_liquidacion=malo)
    capsys.readouterr()
    _caso_e4_sintetico()
    assert "SIN comprobar contra la liquidacion" in capsys.readouterr().out


def test_el_modo_premium_ya_no_existe():
    """C-202: el camino viejo del beneficio se retiró también del motor."""
    from scenarios.comparison_engine import _p2p_monetary_benefit
    D = np.ones((1, 2))
    with pytest.raises(TypeError):
        _p2p_monetary_benefit(_horas(2, []), D, D, 800.0, 200.0, [0],
                              mode="premium")


def _horas(T, tratos):
    from core.ems_p2p import HourlyResult
    out = [HourlyResult(k=k) for k in range(T)]
    for k, P, pi in tratos:
        out[k] = HourlyResult(k=k, P_star=np.asarray(P, dtype=float),
                              pi_star=np.asarray(pi, dtype=float),
                              seller_ids=[0], buyer_ids=[1, 2])
    return out


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_el_horario_es_el_de_la_liquidacion_del_motor():
    """Con `run_comparison` de verdad: el total del análisis es el P2P y el
    C4 liquidados, al peso. Si el beneficio horario deja de ser el del motor
    (o el motor deja de anotar en la hora lo que liquida), esto falla."""
    from scenarios.comparison_engine import run_comparison
    rng = np.random.default_rng(7)
    N, T = 3, 48
    D = rng.uniform(1.0, 4.0, (N, T))
    G = np.zeros((N, T))
    G[0] = rng.uniform(0.0, 9.0, T)
    mes = np.array([202504] * 24 + [202505] * 24)
    tratos = []
    for k in range(T):
        sobra = max(G[0, k] - D[0, k], 0.0)
        if sobra > 0.5:
            q = min(sobra, D[1, k] + D[2, k]) / 2.0
            tratos.append((k, [[q, q]], [600.0, 650.0]))
    res = _horas(T, tratos)
    cr = run_comparison(D, G, G, res, pi_gs=np.full((N, T), 800.0),
                        pi_gb=200.0, pi_bolsa=rng.uniform(100, 300, T),
                        prosumer_ids=[0], consumer_ids=[1, 2],
                        month_labels=mes)
    s = analyze_hourly_dominance(
        p2p_horario=cr.neto_horario["P2P"], c4_horario=cr.neto_horario["C4"],
        p2p_results=res, D=D, G_klim=G, month_labels=mes,
        referencia_liquidacion={"P2P": cr.net_benefit["P2P"],
                                "C4": cr.net_benefit["C4"]})
    assert s.B_p2p_total == pytest.approx(cr.net_benefit["P2P"], abs=1e-6)
    assert s.B_c4_total == pytest.approx(cr.net_benefit["C4"], abs=1e-6)
    assert s.mensual.total(COMUNIDAD)[2] == pytest.approx(
        cr.net_benefit["P2P"] - cr.net_benefit["C4"], abs=1e-6)
    assert s.n_active == len(tratos) > 0
