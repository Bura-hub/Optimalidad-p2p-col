"""
tests/test_pi_gs_temporal.py — CAL-9: tarifa pi_gs temporal (N, T)
==================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Verifica que el contrato matriz (N, T) introducido en CAL-9:

  1. ``as_pi_gs_array`` produce las shapes esperadas para escalar,
     vector (N,) y matriz (N, T).
  2. C1, C3 y C4 con matriz constante en t reproducen exactamente el
     resultado del mismo escalar / vector (compatibilidad CAL-8).
  3. C1 con matriz mes a mes produce un beneficio neto distinto y
     consistente con la integral mes a mes.

No requiere datos MTE; usa perfiles sintéticos compactos.
"""

from __future__ import annotations

import numpy as np
import pytest

from scenarios._pi_gs import as_pi_gs_array, as_pi_gs_vector
from scenarios.scenario_c1_creg174    import run_c1_creg174
from scenarios.scenario_c3_spot       import run_c3_spot
from scenarios.scenario_c4_creg101072 import run_c4_creg101072, compute_pde_weights


N, T = 4, 48           # 2 días sintéticos × 24 h
PI_GS = 800.0          # COP/kWh
PI_BOLSA = 250.0


@pytest.fixture
def synthetic_data():
    """Dos prosumidores con surplus, dos consumidores con déficit."""
    rng = np.random.default_rng(42)
    G = np.zeros((N, T))
    D = np.zeros((N, T))
    for k in range(T):
        h = k % 24
        # Curva solar simple
        gen = max(0.0, 5.0 * np.sin((h - 6) * np.pi / 12))
        G[0, k] = gen * 1.5
        G[1, k] = gen * 1.2
        G[2, k] = gen * 0.3
        G[3, k] = gen * 0.1
        # Demanda con perfil diurno
        dem = 1.5 + 0.8 * np.sin((h - 8) * np.pi / 14)
        D[:, k] = dem + rng.normal(0, 0.05, N)
        D[:, k] = np.maximum(D[:, k], 0.5)
    pi_bolsa = np.full(T, PI_BOLSA)
    pde = compute_pde_weights(G.mean(axis=1))
    return D, G, pi_bolsa, pde


# ─── 1. Shapes del helper ─────────────────────────────────────────────────────

def test_as_pi_gs_array_scalar():
    arr = as_pi_gs_array(800.0, 5, 24)
    assert arr.shape == (5, 24)
    assert np.allclose(arr, 800.0)


def test_as_pi_gs_array_vector_N():
    v = np.array([700, 800, 900, 1000, 1100], dtype=float)
    arr = as_pi_gs_array(v, 5, 24)
    assert arr.shape == (5, 24)
    # Constante en tiempo
    assert np.allclose(arr[:, 0], v)
    assert np.allclose(arr[:, -1], v)


def test_as_pi_gs_array_matrix_NT():
    M = np.tile(np.array([700, 800, 900, 1000, 1100])[:, None], (1, 24)).astype(float)
    arr = as_pi_gs_array(M, 5, 24)
    assert arr.shape == (5, 24)
    assert np.allclose(arr, M)


def test_as_pi_gs_array_invalid_shape():
    with pytest.raises(ValueError):
        as_pi_gs_array(np.zeros((3, 4)), 5, 24)


def test_as_pi_gs_vector_collapses_matrix():
    """Backward compat: as_pi_gs_vector acepta (N, T) y colapsa al promedio."""
    M = np.array([[700, 800], [900, 1000]], dtype=float)
    v = as_pi_gs_vector(M, 2)
    assert v.shape == (2,)
    assert np.allclose(v, [750.0, 950.0])


# ─── 2. Equivalencia escalar ↔ matriz constante ───────────────────────────────

def test_c1_scalar_vs_constant_matrix(synthetic_data):
    """C1 con escalar y con matriz constante en (N, T) debe dar el mismo
    beneficio neto agregado."""
    D, G, pi_bolsa, _ = synthetic_data
    agent_ids = list(range(N))
    month_labels = np.array([1] * 24 + [2] * 24, dtype=int)

    res_scalar = run_c1_creg174(D, G, PI_GS, pi_bolsa, agent_ids, month_labels)
    pi_gs_M = np.full((N, T), PI_GS)
    res_matrix = run_c1_creg174(D, G, pi_gs_M, pi_bolsa, agent_ids, month_labels)

    nb_s = res_scalar["aggregate"]["total_net_benefit"]
    nb_m = res_matrix["aggregate"]["total_net_benefit"]
    assert nb_s == pytest.approx(nb_m, rel=1e-9)


def test_c3_scalar_vs_constant_matrix(synthetic_data):
    D, G, pi_bolsa, _ = synthetic_data
    pros = list(range(N))

    r1 = run_c3_spot(D, G, PI_GS, pi_bolsa, pros, [])
    pi_gs_M = np.full((N, T), PI_GS)
    r2 = run_c3_spot(D, G, pi_gs_M, pi_bolsa, pros, [])

    assert r1["aggregate"]["total_net_benefit"] == pytest.approx(
        r2["aggregate"]["total_net_benefit"], rel=1e-9
    )


def test_c4_scalar_vs_constant_matrix(synthetic_data):
    D, G, pi_bolsa, pde = synthetic_data

    r1 = run_c4_creg101072(D, G, PI_GS, pi_bolsa, pde)
    pi_gs_M = np.full((N, T), PI_GS)
    r2 = run_c4_creg101072(D, G, pi_gs_M, pi_bolsa, pde)

    assert r1["aggregate"]["total_net_benefit"] == pytest.approx(
        r2["aggregate"]["total_net_benefit"], rel=1e-9
    )


# ─── 3. Matriz mes a mes produce delta esperado ──────────────────────────────

def test_c1_matrix_per_month_differs_from_scalar(synthetic_data):
    """Tarifa que cambia entre dos meses produce un beneficio distinto al
    promedio escalar, y el promedio horario-ponderado del beneficio per-mes
    coincide con el cálculo a partir del promedio temporal."""
    D, G, pi_bolsa, _ = synthetic_data
    agent_ids = list(range(N))
    month_labels = np.array([1] * 24 + [2] * 24, dtype=int)

    pi_low, pi_high = 700.0, 900.0
    pi_gs_M = np.zeros((N, T))
    pi_gs_M[:, :24] = pi_low
    pi_gs_M[:, 24:] = pi_high

    res_temporal = run_c1_creg174(D, G, pi_gs_M, pi_bolsa, agent_ids, month_labels)

    pi_avg = (pi_low + pi_high) / 2.0
    res_scalar = run_c1_creg174(D, G, pi_avg, pi_bolsa, agent_ids, month_labels)

    # Deben diferir: la tarifa temporal pondera cada mes con su CU real.
    nb_t = res_temporal["aggregate"]["total_net_benefit"]
    nb_s = res_scalar["aggregate"]["total_net_benefit"]
    assert nb_t != pytest.approx(nb_s, rel=1e-9)

    # Reproducción por suma de períodos: correr cada mes por separado y sumar
    # debe dar exactamente lo mismo que el run mes a mes con month_labels.
    res_m1 = run_c1_creg174(
        D[:, :24], G[:, :24], pi_low, pi_bolsa[:24], agent_ids, None,
    )
    res_m2 = run_c1_creg174(
        D[:, 24:], G[:, 24:], pi_high, pi_bolsa[24:], agent_ids, None,
    )
    nb_split = (res_m1["aggregate"]["total_net_benefit"]
                + res_m2["aggregate"]["total_net_benefit"])
    assert nb_t == pytest.approx(nb_split, rel=1e-9)


def test_c4_matrix_per_month_differs_from_scalar(synthetic_data):
    """C4 con tarifa que cambia mes a mes da un net_benefit distinto del
    obtenido con el promedio escalar."""
    D, G, pi_bolsa, pde = synthetic_data
    pi_low, pi_high = 700.0, 900.0
    pi_gs_M = np.zeros((N, T))
    pi_gs_M[:, :24] = pi_low
    pi_gs_M[:, 24:] = pi_high

    r_t = run_c4_creg101072(D, G, pi_gs_M, pi_bolsa, pde)
    pi_avg = (pi_low + pi_high) / 2.0
    r_s = run_c4_creg101072(D, G, pi_avg, pi_bolsa, pde)

    assert r_t["aggregate"]["total_net_benefit"] != pytest.approx(
        r_s["aggregate"]["total_net_benefit"], rel=1e-9
    )
