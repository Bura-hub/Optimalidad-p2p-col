"""
tests/test_cal26_pde_excedentes.py — CAL-26 PDE excedentes_proportional
=========================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 4.1 + 4.2 + 3.1-3.3

Verifica:
  1. Helper compute_excedentes_acumulados produce (N,) correcto.
  2. compute_pde_weights con method='excedentes_proportional' suma 1.
  3. Fallback 1/N si total = 0.
  4. Default sigue siendo 'capacity_proportional' (CAL-15 intacto).
  5. Método desconocido lanza ValueError.

Referencia: docs/adr/0026-cal26-pde-excedentes-proportional.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scenarios.scenario_c4_creg101072 import (
    compute_pde_weights,
    compute_excedentes_acumulados,
)


# ─── A — compute_excedentes_acumulados ──────────────────────────────────────


def test_excedentes_acumulados_basico():
    """Calculo aritmetico correcto sobre matrices D y G."""
    G = np.array([[3.0, 0.0, 5.0], [0.0, 2.0, 0.0]])  # N=2, T=3
    D = np.array([[2.0, 1.0, 0.0], [1.0, 1.0, 1.0]])
    exc = compute_excedentes_acumulados(G, D)
    # Agente 0: max(3-2,0)+max(0-1,0)+max(5-0,0) = 1 + 0 + 5 = 6
    # Agente 1: max(0-1,0)+max(2-1,0)+max(0-1,0) = 0 + 1 + 0 = 1
    assert np.allclose(exc, [6.0, 1.0])


def test_excedentes_acumulados_no_negativo():
    """Excedentes nunca son negativos."""
    G = np.zeros((3, 5))
    D = np.full((3, 5), 10.0)  # toda demanda, nada de generación
    exc = compute_excedentes_acumulados(G, D)
    assert np.all(exc == 0.0)
    assert np.all(exc >= 0.0)


def test_excedentes_acumulados_shape_check():
    G = np.ones((3, 4))
    D = np.ones((3, 5))   # shape distinto
    with pytest.raises(ValueError, match="shape"):
        compute_excedentes_acumulados(G, D)


# ─── B — compute_pde_weights con method='excedentes_proportional' ──────────


def test_pde_excedentes_proportional_suma_uno():
    metric = np.array([100.0, 200.0, 300.0, 400.0])
    pde = compute_pde_weights(metric, method="excedentes_proportional")
    assert pde.sum() == pytest.approx(1.0)
    # Cada PDE_n proporcional al excedente
    assert np.allclose(pde, metric / metric.sum())


def test_pde_excedentes_no_negatividad():
    metric = np.array([0.0, 50.0, 100.0])
    pde = compute_pde_weights(metric, method="excedentes_proportional")
    assert (pde >= 0).all()
    assert pde[0] == 0.0  # agente sin excedente


def test_pde_excedentes_fallback_si_todos_cero():
    """Si nadie generó excedente, fallback 1/N uniforme."""
    metric = np.zeros(5)
    pde = compute_pde_weights(metric, method="excedentes_proportional")
    assert np.allclose(pde, 0.2)
    assert pde.sum() == pytest.approx(1.0)


# ─── C — Default y compatibilidad ──────────────────────────────────────────


def test_default_sigue_siendo_capacity_proportional():
    """CAL-15 no se rompe: default sin cambios."""
    capacity = np.array([3.0, 5.0, 2.0])
    pde_default = compute_pde_weights(capacity)  # sin method
    pde_explicit = compute_pde_weights(capacity, method="capacity_proportional")
    assert np.allclose(pde_default, pde_explicit)
    assert np.allclose(pde_default, capacity / capacity.sum())


def test_equal_method_no_se_rompe():
    """Método 'equal' sigue produciendo 1/N."""
    metric = np.array([100.0, 50.0, 25.0, 12.5])
    pde = compute_pde_weights(metric, method="equal")
    assert np.allclose(pde, 0.25)


def test_metodo_desconocido_lanza_error():
    with pytest.raises(ValueError, match="(?i)Método PDE desconocido"):
        compute_pde_weights(np.array([1.0, 2.0]), method="random_split")


# ─── D — Integración con run_c4_creg101072 ─────────────────────────────────


def test_pde_excedentes_da_pde_valido_para_c4():
    """PDE excedentes pasa la validación validate_pde."""
    from scenarios.scenario_c4_creg101072 import validate_pde

    G = np.array([[10.0, 0.0, 5.0], [0.0, 8.0, 0.0]])
    D = np.array([[3.0, 1.0, 1.0], [2.0, 6.0, 0.0]])
    exc = compute_excedentes_acumulados(G, D)
    pde = compute_pde_weights(exc, method="excedentes_proportional")
    assert validate_pde(pde), f"PDE no válido: suma={pde.sum()}"


def test_paper_iter_acepta_pde_excedentes():
    """run_paper_iter.py acepta --pde excedentes (smoke parser)."""
    import subprocess
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_paper_iter.py"),
         "--help"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert res.returncode == 0
    assert "excedentes" in res.stdout
