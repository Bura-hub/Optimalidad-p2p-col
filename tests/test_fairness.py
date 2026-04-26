"""
test_fairness.py
----------------
Verifica el módulo analysis/fairness.py (Price of Fairness, Bertsimas 2011).

Actividad 3.3 — Descomposición del bienestar y comparación monetaria.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pytest

from analysis.fairness import compute_pof, fairness_curve, FairnessResult


# Datos sintéticos: 5 escenarios, 3 agentes
_PER_AGENT = {
    "P2P": np.array([100.0, 120.0, 80.0]),   # total=300, más eficiente
    "C1":  np.array([ 90.0, 110.0, 90.0]),   # total=290
    "C4":  np.array([ 98.0, 100.0, 102.0]),  # total=300, más equitativo (Gini≈0)
}
_GINI = {
    "P2P": 0.10,   # alguna concentración
    "C1":  0.05,
    "C4":  0.01,   # casi perfectamente equitativo
}


def test_pof_bounded():
    """PoF ∈ [0, 1] para datos sintéticos razonables."""
    fr = compute_pof(_PER_AGENT, _GINI)
    assert isinstance(fr, FairnessResult)
    assert 0.0 <= fr.pof <= 1.0, f"PoF={fr.pof} fuera de [0, 1]"


def test_pof_efficient_scenario_correct():
    """El escenario eficiente es el de mayor beneficio total."""
    fr = compute_pof(_PER_AGENT, _GINI)
    totals = {k: float(np.sum(v)) for k, v in _PER_AGENT.items()}
    assert fr.eff_scenario == max(totals, key=totals.get), (
        f"eff_scenario esperado={max(totals, key=totals.get)}, obtuvo={fr.eff_scenario}"
    )


def test_pof_zero_when_same_distribution():
    """PoF = 0 cuando el escenario más eficiente es también el más equitativo."""
    per_agent = {
        "A": np.array([100.0, 100.0, 100.0]),   # más eficiente Y más equitativo
        "B": np.array([ 80.0, 100.0, 120.0]),   # menos eficiente, menos equitativo
    }
    gini = {"A": 0.0, "B": 0.2}
    fr = compute_pof(per_agent, gini)
    assert fr.pof == pytest.approx(0.0, abs=1e-9), (
        f"PoF debería ser 0 cuando eficiente=equitativo, obtuvo {fr.pof}"
    )


def test_pof_per_agent_non_negative():
    """pof_per_agent[n] ≥ 0 para todo agente."""
    fr = compute_pof(_PER_AGENT, _GINI)
    assert np.all(fr.pof_per_agent >= -1e-12), (
        f"pof_per_agent tiene negativos: {fr.pof_per_agent}"
    )


def test_gini_ranking_ascending():
    """gini_ranking está ordenado por Gini ascendente."""
    fr = compute_pof(_PER_AGENT, _GINI)
    ginis = [g for _, g, _ in fr.gini_ranking]
    assert ginis == sorted(ginis), f"gini_ranking no está en orden ascendente: {ginis}"


def test_fairness_curve_length():
    """fairness_curve retorna una fila por escenario."""
    curve = fairness_curve(_PER_AGENT, _GINI)
    assert len(curve) == len(_PER_AGENT), (
        f"Se esperaban {len(_PER_AGENT)} filas, se obtuvieron {len(curve)}"
    )


def test_pof_empty_inputs():
    """compute_pof no falla con dicts vacíos."""
    fr = compute_pof({}, {})
    assert fr.pof == 0.0
    assert fr.eff_scenario == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
