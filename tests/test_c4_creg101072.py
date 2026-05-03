"""
tests/test_c4_creg101072.py — CAL-15: C4 Tipo 1 / Tipo 2 + Cvm
===============================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Verifica la implementación CAL-15 de ``run_c4_creg101072``:

  1. component_c='auto' descuenta proporcionalmente al CU (≈ 13.85 %).
  2. component_c=float aplica descuento fijo en permuta Tipo 1.
  3. component_c=0.0 reproduce valoración legacy (sin descuento).
  4. Tipo 2 se valora a pi_bolsa[k] horario, no al promedio.
  5. Conservación de energía: inyeccion_total = permuta_t1 + excedente_t2.
  6. Ejemplo del usuario: descalce horario produce venta+compra simultánea.
  7. mode='pde_only' legacy emite DeprecationWarning y omite Tipo 2.
  8. validate_pde rechaza ponderadores que no suman 1.

Referencia: docs/adr/0015-cal15-c4-creg101072-tipo-1-2-cvm.md
"""

from __future__ import annotations

import warnings

import numpy as np
import pytest

from scenarios.scenario_c4_creg101072 import (
    run_c4_creg101072, compute_pde_weights, validate_pde,
)
from data.xm_prices import C_FRACTION


PI_GS = 800.0
PI_BOLSA = 200.0


def _bolsa_horaria(T: int, base: float = PI_BOLSA, var: float = 0.0):
    """Serie horaria con variabilidad opcional para distinguir media vs horaria."""
    if var <= 0:
        return np.full(T, base)
    rng = np.random.default_rng(42)
    return base + var * rng.standard_normal(T)


# ─── 1. Descuento Cvm en permuta Tipo 1 ──────────────────────────────────────

def test_c4_component_c_auto_proportional():
    """component_c='auto' descuenta C_FRACTION × pi_gs en permuta Tipo 1."""
    # 2 agentes con descalce: A genera mucho, B demanda mucho → permuta T1.
    D = np.zeros((2, 24)); D[1, :] = 2.0
    G = np.zeros((2, 24)); G[0, 8:18] = 4.0     # surplus solar A
    pde = np.array([0.5, 0.5])
    pi_bolsa = _bolsa_horaria(24)

    res_auto = run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde,
                                   component_c="auto")
    res_zero = run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde,
                                   component_c=0.0)

    # Permuta Tipo 1 a (pi_gs - pi_gs * C_FRACTION) bajo auto, a pi_gs bajo zero.
    pde_auto = res_auto["aggregate"]["total_pde_credits"]
    pde_zero = res_zero["aggregate"]["total_pde_credits"]
    assert pde_auto < pde_zero
    # El cociente debe ser aproximadamente (1 - C_FRACTION).
    ratio = pde_auto / pde_zero
    assert ratio == pytest.approx(1.0 - C_FRACTION, rel=1e-6)


def test_c4_component_c_fixed_value():
    """component_c=float aplica descuento fijo en permuta Tipo 1."""
    D = np.zeros((2, 24)); D[1, :] = 2.0
    G = np.zeros((2, 24)); G[0, 8:18] = 4.0
    pde = np.array([0.5, 0.5])
    pi_bolsa = _bolsa_horaria(24)

    C_FIXED = 90.0
    res = run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde,
                              component_c=C_FIXED)
    res_zero = run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde,
                                   component_c=0.0)

    # Si pde_zero usa pi_gs, pde_fixed usa (pi_gs - C_FIXED).
    ratio = res["aggregate"]["total_pde_credits"] / res_zero["aggregate"]["total_pde_credits"]
    assert ratio == pytest.approx(1.0 - C_FIXED / PI_GS, rel=1e-6)


def test_c4_component_c_zero_legacy_compat():
    """component_c=0.0 reproduce valoración pi_gs completo en permuta."""
    D = np.zeros((2, 24)); D[1, :] = 2.0
    G = np.zeros((2, 24)); G[0, 8:18] = 4.0
    pde = np.array([0.5, 0.5])
    pi_bolsa = _bolsa_horaria(24)

    res = run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde,
                              component_c=0.0)

    # Verificar suma: total_pde_credits = sum_h permuta_t1[n,h] * pi_gs (sin descuento).
    permuta = res["hourly"]["permuta_t1"]
    expected = float(permuta.sum() * PI_GS)
    assert res["aggregate"]["total_pde_credits"] == pytest.approx(expected, rel=1e-9)


# ─── 2. Tipo 2 a pi_bolsa horario ────────────────────────────────────────────

def test_c4_tipo2_uses_hourly_bolsa_not_mean():
    """Tipo 2 se valora a pi_bolsa[k], no al promedio (importante con var > 0)."""
    # Caso: solo agente 0 produce; nadie demanda → todo es Tipo 2.
    D = np.zeros((2, 24))
    G = np.zeros((2, 24)); G[0, 12] = 10.0       # surplus en hora 12 únicamente
    pde = np.array([0.5, 0.5])

    pi_bolsa = _bolsa_horaria(24, base=200.0)
    pi_bolsa[12] = 50.0                          # hora 12 mucho más barata
    pi_bolsa[10] = 800.0                         # hora 10 cara (pero sin surplus)

    res = run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde,
                              component_c=0.0)

    # surplus de 10 kWh en hora 12 → revenue = 10 × 50 (no 10 × promedio).
    expected = 10.0 * 50.0
    assert res["aggregate"]["total_surplus_revenue"] == pytest.approx(expected, rel=1e-9)


# ─── 3. Conservación ─────────────────────────────────────────────────────────

def test_c4_conservacion_inyeccion_total():
    """sum_n (permuta_t1 + excedente_t2)[k] = inyeccion_total[k] para toda hora k."""
    rng = np.random.default_rng(7)
    D = rng.uniform(0.0, 3.0, (4, 24))
    G = rng.uniform(0.0, 3.0, (4, 24))
    pde = compute_pde_weights(np.array([1.0, 2.0, 3.0, 4.0]))
    pi_bolsa = _bolsa_horaria(24, var=30.0)

    res = run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde,
                              component_c="auto")

    iny = res["hourly"]["inyeccion_total"]                 # (T,)
    permuta = res["hourly"]["permuta_t1"].sum(axis=0)       # (T,)
    tipo2   = res["hourly"]["excedente_t2"].sum(axis=0)     # (T,)

    np.testing.assert_allclose(permuta + tipo2, iny, atol=1e-9)


def test_c4_conservacion_demanda_individual():
    """deficit_ind[n,k] = permuta_t1[n,k] + grid_buy[n,k] (cada agente)."""
    rng = np.random.default_rng(11)
    D = rng.uniform(0.0, 3.0, (3, 12))
    G = rng.uniform(0.0, 3.0, (3, 12))
    pde = np.array([0.4, 0.3, 0.3])
    pi_bolsa = _bolsa_horaria(12)

    res = run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde,
                              component_c="auto")

    permuta = res["hourly"]["permuta_t1"]
    grid    = res["hourly"]["grid_buy"]
    deficit = np.maximum(D - G, 0.0)

    np.testing.assert_allclose(permuta + grid, deficit, atol=1e-9)


# ─── 4. Ejemplo del usuario: descalce horario ────────────────────────────────

def test_c4_ejemplo_descalce_horario():
    """
    Caso narrativa del usuario: A genera 10 kWh sin demanda, B demanda 10 kWh
    sin generar. PDE 50/50. La comunidad SIMULTÁNEAMENTE vende excedente A a
    pi_bolsa y compra déficit B a pi_gs — la "inefficiencia AGRC" cuantificada.
    """
    # Una sola hora.
    D = np.array([[0.0], [10.0]])
    G = np.array([[10.0], [0.0]])
    pde = np.array([0.5, 0.5])
    pi_bolsa = np.array([100.0])

    res = run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde,
                              component_c=0.0)

    # Inyección comunitaria = 10 (solo A inyecta).
    assert res["hourly"]["inyeccion_total"][0] == pytest.approx(10.0)

    # Crédito A = 5 (B no demanda los suyos), excedente A = 5 → vendido a 100.
    # Crédito B = 5 (compensa parte de su deficit), permuta B = 5 → ahorra a pi_gs.
    # Déficit residual B = 5 → pagado a pi_gs (no produce ahorro).
    a, b = 0, 1

    # A: solo Tipo 2 (no tiene demanda propia).
    assert res["hourly"]["excedente_t2"][a, 0] == pytest.approx(5.0)
    assert res["hourly"]["permuta_t1"][a, 0] == pytest.approx(0.0)

    # B: todo su crédito es Tipo 1 (compensa parte del deficit), resto es grid.
    assert res["hourly"]["permuta_t1"][b, 0] == pytest.approx(5.0)
    assert res["hourly"]["excedente_t2"][b, 0] == pytest.approx(0.0)
    assert res["hourly"]["grid_buy"][b, 0] == pytest.approx(5.0)

    # Beneficios netos: A = 5 × pi_bolsa, B = 5 × pi_gs (permuta sin descuento).
    assert res["per_agent"][a]["net_benefit"] == pytest.approx(5.0 * 100.0)
    assert res["per_agent"][b]["net_benefit"] == pytest.approx(5.0 * PI_GS)


# ─── 5. Modo legacy con DeprecationWarning ───────────────────────────────────

def test_c4_legacy_pde_only_emits_deprecation():
    """mode='pde_only' es legacy; emite DeprecationWarning y omite Tipo 2."""
    D = np.zeros((2, 24))
    G = np.zeros((2, 24)); G[0, 12] = 10.0
    pde = np.array([0.5, 0.5])
    pi_bolsa = _bolsa_horaria(24)

    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        res = run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde,
                                  mode="pde_only")

    deprecation = [w for w in ws if issubclass(w.category, DeprecationWarning)]
    assert len(deprecation) >= 1
    assert "CAL-15" in str(deprecation[0].message)

    # En modo pde_only legacy no hay venta a bolsa.
    assert res["aggregate"]["total_surplus_revenue"] == 0.0


# ─── 6. Validaciones ─────────────────────────────────────────────────────────

def test_c4_validate_pde_rejects_invalid():
    """PDE que no suma 1 lanza ValueError."""
    D = np.zeros((2, 1))
    G = np.zeros((2, 1))
    pde_invalido = np.array([0.4, 0.4])          # suma 0.8
    pi_bolsa = np.array([100.0])

    with pytest.raises(ValueError, match="PDE invál"):
        run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde_invalido)


def test_c4_capacity_limit_raises():
    """Capacidad agregada > 100 kW lanza ValueError (régimen simplificado)."""
    D = np.zeros((2, 1))
    G = np.zeros((2, 1))
    pde = np.array([0.5, 0.5])
    pi_bolsa = np.array([100.0])
    cap_alta = np.array([60.0, 60.0])            # 120 kW > 100

    with pytest.raises(ValueError, match="excede límite"):
        run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde, capacity=cap_alta)


# ─── 7. Slicing en feasibility (regression CAL-9.1 + CAL-15) ─────────────────

def test_c4_acepta_component_c_matriz_NT():
    """component_c con shape (N, T) se aplica per-agente y per-hora."""
    D = np.zeros((2, 24)); D[1, :] = 2.0
    G = np.zeros((2, 24)); G[0, 8:18] = 4.0
    pde = np.array([0.5, 0.5])
    pi_bolsa = _bolsa_horaria(24)

    pi_C_matrix = np.zeros((2, 24)); pi_C_matrix[1, :] = 100.0   # solo B descuenta

    res = run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde,
                              component_c=pi_C_matrix)

    # Como solo B (que recibe permuta) tiene C != 0, el descuento se aplica.
    res_zero = run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde,
                                   component_c=0.0)
    assert res["aggregate"]["total_pde_credits"] < res_zero["aggregate"]["total_pde_credits"]


def test_c4_validate_pde_helper_directo():
    """validate_pde directo: positivos y suma 1."""
    assert validate_pde(np.array([0.5, 0.5]))
    assert validate_pde(np.array([0.25, 0.25, 0.25, 0.25]))
    assert not validate_pde(np.array([0.4, 0.4]))
    assert not validate_pde(np.array([1.5, -0.5]))     # uno negativo
