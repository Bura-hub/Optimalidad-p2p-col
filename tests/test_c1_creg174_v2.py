"""
tests/test_c1_creg174_v2.py — CAL-10: Excedentes Tipo 1 / Tipo 2 + componente C
==============================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Verifica la implementación CAL-10 de ``run_c1_creg174``:

  1. component_c="auto" descuenta proporcionalmente al CU (≈ 13.85 %).
  2. component_c=float aplica el descuento fijo.
  3. component_c=0.0 reproduce la valoración legacy a pi_gs completo.
  4. Hora Hx se identifica correctamente cuando inyección_acum cruza retiro_acum.
  5. Sin cruce (deficit ≥ surplus) todo el surplus es Tipo 1.
  6. Cruce desde t=0 (surplus desde la primera hora) clasifica correctamente.

Referencia: docs/adrs/CAL-10-creg174-tipo-1-2-componente-c.md
"""

from __future__ import annotations

import numpy as np
import pytest

from scenarios.scenario_c1_creg174 import run_c1_creg174
from data.xm_prices import C_FRACTION


PI_GS = 800.0
PI_BOLSA = 200.0


# ─── 1. Descuento del componente C ───────────────────────────────────────────

def test_c1_component_c_auto_proportional():
    """component_c='auto' descuenta C_FRACTION × pi_gs en la permuta Tipo 1."""
    # 1 agente, 24 h con surplus moderado → permuta sin cruce.
    D = np.full((1, 24), 1.0)            # demanda constante
    G = np.zeros((1, 24))
    G[0, 8:18] = 1.5                      # surplus solar moderado
    pi_bolsa = np.full(24, PI_BOLSA)

    res_auto = run_c1_creg174(D, G, PI_GS, pi_bolsa, [0],
                               component_c="auto")
    res_zero = run_c1_creg174(D, G, PI_GS, pi_bolsa, [0],
                               component_c=0.0)

    # Bajo "auto", la permuta vale (pi_gs - pi_gs * C_FRACTION) en lugar de pi_gs.
    # El autoconsumo sigue valorado a pi_gs completo.
    e_auto = res_auto[0]["E_auto"]
    e_t1   = res_auto[0]["E_permuted_t1"]

    expected_savings_auto = e_auto * PI_GS + e_t1 * PI_GS * (1 - C_FRACTION)
    expected_savings_zero = (e_auto + e_t1) * PI_GS

    assert res_auto[0]["savings"] == pytest.approx(expected_savings_auto, rel=1e-9)
    assert res_zero[0]["savings"] == pytest.approx(expected_savings_zero, rel=1e-9)
    assert res_auto[0]["savings"] < res_zero[0]["savings"]


def test_c1_component_c_fixed_value():
    """component_c=float aplica un descuento fijo en COP/kWh."""
    D = np.full((1, 24), 1.0)
    G = np.zeros((1, 24))
    G[0, 8:18] = 1.5
    pi_bolsa = np.full(24, PI_BOLSA)

    C_FIXED = 90.0
    res = run_c1_creg174(D, G, PI_GS, pi_bolsa, [0], component_c=C_FIXED)

    e_auto = res[0]["E_auto"]
    e_t1   = res[0]["E_permuted_t1"]
    expected = e_auto * PI_GS + e_t1 * (PI_GS - C_FIXED)
    assert res[0]["savings"] == pytest.approx(expected, rel=1e-9)


def test_c1_component_c_zero_legacy_compat():
    """component_c=0.0 → savings = (auto + permuted_t1) × pi_gs (sin C)."""
    D = np.full((1, 24), 1.0)
    G = np.zeros((1, 24))
    G[0, 8:18] = 1.5
    pi_bolsa = np.full(24, PI_BOLSA)

    res = run_c1_creg174(D, G, PI_GS, pi_bolsa, [0], component_c=0.0)
    e_auto = res[0]["E_auto"]
    e_t1   = res[0]["E_permuted_t1"]
    assert res[0]["savings"] == pytest.approx((e_auto + e_t1) * PI_GS, rel=1e-9)


# ─── 2. Lógica de hora Hx ────────────────────────────────────────────────────

def test_c1_hx_basic_crossing():
    """Cruce intramensual: surplus dominante en horas finales tras déficit
    inicial. Hx debe ubicarse en el momento del cruce y separar Tipo 1/Tipo 2."""
    # Día 24h: 0-9 deficit, 10-23 surplus.
    D = np.zeros((1, 24))
    G = np.zeros((1, 24))
    D[0, 0:10]  = 2.0   # 10 h × 2 kWh = 20 kWh deficit
    G[0, 10:24] = 4.0   # 14 h × 4 kWh = 56 kWh surplus  → cruza retiro
    pi_bolsa = np.full(24, PI_BOLSA)

    res = run_c1_creg174(D, G, PI_GS, pi_bolsa, [0], component_c=0.0)

    # E_surplus = 56, E_deficit = 20.
    # Tipo 1 esperado = 20 kWh (cierra la permuta), Tipo 2 = 36 kWh.
    assert res[0]["E_permuted_t1"] == pytest.approx(20.0, abs=1e-9)
    assert res[0]["E_tipo2"]       == pytest.approx(36.0, abs=1e-9)
    # Hx debe estar entre 10 y 23 (cuando cumulative iny pasa los 20 kWh).
    hx_period = res[0]["hx_history"][0]
    assert hx_period is not None
    assert 10 <= hx_period <= 23

    # Revenue = 36 kWh × pi_bolsa = 36 × 200
    assert res[0]["surplus_revenue"] == pytest.approx(36.0 * PI_BOLSA, rel=1e-9)


def test_c1_hx_no_crossing():
    """deficit > surplus en todo el mes → no hay Hx, todo es Tipo 1."""
    D = np.full((1, 24), 3.0)            # 72 kWh demanda total
    G = np.zeros((1, 24))
    G[0, 10:14] = 2.0                     # 4 h × 2 = 8 kWh surplus máximo
    # Pero el surplus efectivo es G - min(G,D) = (2-2)=0 en horas con D=3 ≥ G=2.
    # Re-construyamos con surplus real:
    D = np.full((1, 24), 1.0)
    G = np.zeros((1, 24))
    G[0, 10:14] = 1.5                     # surplus = 0.5 kWh × 4 = 2 kWh
    pi_bolsa = np.full(24, PI_BOLSA)

    res = run_c1_creg174(D, G, PI_GS, pi_bolsa, [0], component_c=0.0)

    # Surplus total ≈ 2 kWh; deficit total ≈ 22 kWh. No cruza.
    assert res[0]["hx_history"][0] is None
    assert res[0]["E_tipo2"] == pytest.approx(0.0, abs=1e-9)
    assert res[0]["surplus_revenue"] == pytest.approx(0.0, abs=1e-9)
    # Tipo 1 == E_surplus
    expected_t1 = float(np.sum(np.maximum(G[0] - D[0], 0)))
    assert res[0]["E_permuted_t1"] == pytest.approx(expected_t1, rel=1e-9)


def test_c1_hx_at_first_hour():
    """Surplus desde t=0 sin retiros previos → Hx=0, casi todo es Tipo 2."""
    D = np.full((1, 24), 0.5)             # demanda baja
    G = np.zeros((1, 24))
    G[0, 0:24] = 5.0                       # surplus inmediato y sostenido
    pi_bolsa = np.full(24, PI_BOLSA)

    res = run_c1_creg174(D, G, PI_GS, pi_bolsa, [0], component_c=0.0)

    # En la primera hora: surplus_h[0] = 4.5, deficit_h[0] = 0
    # iny_acum = 4.5 > ret_acum = 0 → cruza en hora 0.
    # cruce = 4.5; surplus_t2[0] = min(4.5, 4.5) = 4.5; surplus_t1[0] = 0.
    assert res[0]["hx_history"][0] == 0
    # Como deficit es 0 todo el mes, todo el surplus es Tipo 2.
    assert res[0]["E_permuted_t1"] == pytest.approx(0.0, abs=1e-9)
    e_surplus_total = float(np.sum(np.maximum(G[0] - D[0], 0)))
    assert res[0]["E_tipo2"] == pytest.approx(e_surplus_total, rel=1e-9)


# ─── 3. Multi-mes y multi-agente ─────────────────────────────────────────────

def test_c1_hx_per_month_independent():
    """En multi-mes, cada mes recalcula su propia Hx independiente."""
    # 48 h = 2 meses. Mes 1: cruza. Mes 2: no cruza.
    D = np.zeros((1, 48))
    G = np.zeros((1, 48))
    # Mes 1 (h 0-23): cruza
    D[0, 0:10]  = 2.0
    G[0, 10:24] = 4.0
    # Mes 2 (h 24-47): solo deficit
    D[0, 24:48] = 2.0
    pi_bolsa = np.full(48, PI_BOLSA)
    month_labels = np.array([1] * 24 + [2] * 24)

    res = run_c1_creg174(D, G, PI_GS, pi_bolsa, [0], month_labels,
                          component_c=0.0)

    hx_list = res[0]["hx_history"]
    assert len(hx_list) == 2
    # Mes 1 cruza
    assert hx_list[0] is not None
    # Mes 2 no cruza
    assert hx_list[1] is None


def test_c1_aggregate_consistency():
    """Suma de E_auto + E_permuted_t1 + E_tipo2 == suma de generación bruta
    cuando G ≥ 0 (conservación de energía)."""
    D = np.full((2, 48), 1.0)
    G = np.zeros((2, 48))
    G[0, 8:18]  = 2.0
    G[0, 32:42] = 1.5
    G[1, 10:14] = 3.0
    pi_bolsa = np.full(48, PI_BOLSA)
    month_labels = np.array([1] * 24 + [2] * 24)

    res = run_c1_creg174(D, G, PI_GS, pi_bolsa, [0, 1], month_labels)

    for n in [0, 1]:
        e_total = res[n]["E_auto"] + res[n]["E_permuted_t1"] + res[n]["E_tipo2"]
        e_gen   = float(np.sum(np.maximum(G[n], 0)))
        assert e_total == pytest.approx(e_gen, rel=1e-9), (
            f"Agente {n}: auto+t1+t2 = {e_total} ≠ gen total = {e_gen}"
        )


# ─── 4. CAL-10b: matriz con NaN (fallback proporcional) ──────────────────────

def test_as_component_c_array_rellena_nan_con_proporcional():
    """Si component_c es matriz con NaN, se rellenan con pi_gs * C_FRACTION."""
    from scenarios._pi_gs import as_component_c_array, as_pi_gs_array
    from data.xm_prices import C_FRACTION

    N, T = 2, 4
    pi_gs = as_pi_gs_array(800.0, N, T)         # matriz constante 800
    c_in = np.array([
        [200.0, np.nan, 200.0, np.nan],
        [np.nan, 210.0, np.nan, 210.0],
    ])
    c_out = as_component_c_array(c_in, pi_gs, N, T)

    # Celdas con dato real intactas.
    assert c_out[0, 0] == 200.0
    assert c_out[0, 2] == 200.0
    assert c_out[1, 1] == 210.0
    assert c_out[1, 3] == 210.0
    # Celdas NaN reemplazadas por 800 * C_FRACTION.
    expected_fallback = 800.0 * float(C_FRACTION)
    assert c_out[0, 1] == pytest.approx(expected_fallback, rel=1e-9)
    assert c_out[0, 3] == pytest.approx(expected_fallback, rel=1e-9)
    assert c_out[1, 0] == pytest.approx(expected_fallback, rel=1e-9)
    assert c_out[1, 2] == pytest.approx(expected_fallback, rel=1e-9)


# ─── 5. CAL-10b: integración C real CSV vs aproximación proporcional ─────────

def test_c1_real_csv_C_mayor_que_proporcional():
    """
    Con C real ≈ 22-27 % del CU (vs C_FRACTION ≈ 13.85 %), la permuta Tipo 1
    se descuenta más → savings_m baja → C1 cae respecto a 'auto'.
    Requiere CSV Cedenar real (data/tarifas_cedenar_mensual.csv).
    """
    import pandas as pd
    from data.cedenar_tariff import cvm_per_agent_hourly

    N = 1
    idx = pd.date_range("2025-07-01", "2025-08-01", freq="1h",
                        inclusive="left", tz="America/Bogota")
    T = len(idx)
    D = np.full((N, T), 1.0)
    G = np.zeros((N, T))
    # Surplus solar moderado: 8 h/día con G > D durante 31 días.
    for d in range(31):
        G[0, d * 24 + 8 : d * 24 + 16] = 1.5
    pi_bolsa = np.full(T, 250.0)

    pi_gs_real = 797.0   # ~oficial NT2 Cedenar

    # 1) Modo auto (CAL-10): C = pi_gs * 0.1385 ≈ 110 COP/kWh.
    res_auto = run_c1_creg174(D, G, pi_gs_real, pi_bolsa, [0],
                               component_c="auto")

    # 2) Modo CSV (CAL-10b.2 literal CREG 174 art. 25): Cvm puro ≈ 174 COP/kWh.
    c_csv = cvm_per_agent_hourly(["Udenar"], idx)
    res_csv = run_c1_creg174(D, G, pi_gs_real, pi_bolsa, [0],
                              component_c=c_csv)

    nb_auto = res_auto[0]["net_benefit"]
    nb_csv  = res_csv[0]["net_benefit"]
    assert nb_csv < nb_auto, (
        f"Esperado nb_csv ({nb_csv:.0f}) < nb_auto ({nb_auto:.0f}); "
        f"el dato real Cedenar debería descontar más que la aprox. 13.85 %."
    )
