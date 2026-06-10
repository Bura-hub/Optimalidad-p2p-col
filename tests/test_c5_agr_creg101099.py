"""CAL-37 — C5 AGR (CREG 101 099/2026) + fix C2 a bolsa horaria (ADR-0037).

Fixture de mano (ver plan 2026-06-09-cal37): N=3, T=2;
tasa no-regulada = g300+cvm170+cot40−mem10 = 500; pi_gs=800; pi_bolsa=[150,200].
h0: surplus a0=4; déficits a1=2, a2=1 → E_comp=3, residual=1→(150−10)=140.
h1: surplus a2=2; déficits a0=1, a1=2 → E_comp=2, residual=0.
Autoconsumo: a0=1×800, a2=1×800. Total invariante = 1600+5×500+140 = 4240.
"""
import numpy as np
import pytest

from scenarios.scenario_c5_agr_creg101099 import run_c5_agr_creg101099


def _fx():
    G  = np.array([[5.0, 0.0], [0.0, 0.0], [0.0, 3.0]])
    D  = np.array([[1.0, 1.0], [2.0, 2.0], [1.0, 1.0]])
    pi_gs = np.full((3, 2), 800.0)
    kw = dict(pi_bolsa=np.array([150.0, 200.0]),
              g_component=np.full((3, 2), 300.0),
              cvm_component=np.full((3, 2), 170.0),
              cot_component=np.full((3, 2), 40.0),
              mem_costs=np.full((3, 2), 10.0))
    return D, G, pi_gs, kw


def test_doble_limite_y_residual():
    D, G, pi_gs, kw = _fx()
    r = run_c5_agr_creg101099(D, G, pi_gs, **kw)
    assert r["hourly"]["e_comp"].tolist() == [3.0, 2.0]
    # residual h0 = 1 kWh a (150-10)=140; h1 = 0
    assert r["aggregate"]["total_residual_bolsa"] == pytest.approx(140.0)


def test_total_invariante_a_f_split():
    D, G, pi_gs, kw = _fx()
    for f in (0.0, 0.5, 1.0):
        r = run_c5_agr_creg101099(D, G, pi_gs, f_split=f, **kw)
        assert r["aggregate"]["total_net_benefit"] == pytest.approx(4240.0)


def test_split_per_agente_f05():
    D, G, pi_gs, kw = _fx()
    r = run_c5_agr_creg101099(D, G, pi_gs, f_split=0.5, **kw)
    pa = r["per_agent"]
    # a0: auto 800 + residual 140 + gen 3×250 + rec (2/3)×250
    assert pa[0]["net_benefit"] == pytest.approx(800 + 140 + 750 + (2 / 3) * 250)
    assert pa[1]["net_benefit"] == pytest.approx(2 * 250 + (4 / 3) * 250)
    assert pa[2]["net_benefit"] == pytest.approx(800 + 500 + 250)


def test_lbc_solo_diagnostico():
    D, G, pi_gs, kw = _fx()
    base = run_c5_agr_creg101099(D, G, pi_gs, **kw)
    # PES=180: h1 (bolsa 200) dispara; h0 (150) no.
    r = run_c5_agr_creg101099(D, G, pi_gs,
                              pi_escasez=np.array([180.0, 180.0]), **kw)
    assert r["regulatory"]["lbc_active_hours"] == 1
    assert r["regulatory"]["lbc_afecta_beneficio"] is False
    assert r["aggregate"]["total_net_benefit"] == pytest.approx(
        base["aggregate"]["total_net_benefit"])


def test_c2_excedente_a_bolsa_horaria_retrocompatible():
    from scenarios.scenario_c2_bilateral import run_c2_bilateral
    D = np.array([[1.0, 1.0], [1.0, 1.0]])
    G = np.array([[3.0, 3.0], [0.0, 0.0]])
    pi_gs = np.full((2, 2), 800.0)
    base = dict(pi_gb=280.0, pi_ppa=400.0, prosumer_ids=[0], consumer_ids=[],
                pi_G=500.0)
    old = run_c2_bilateral(D, G, pi_gs, **base)
    new = run_c2_bilateral(D, G, pi_gs, pi_bolsa=np.array([100.0, 200.0]),
                           **base)
    # surplus = 2 kWh/h. Sin pi_bolsa: 4×280=1120. Con: 2×100+2×200=600.
    assert old["aggregate"]["total_grid_revenue"] == pytest.approx(1120.0)
    assert new["aggregate"]["total_grid_revenue"] == pytest.approx(600.0)
