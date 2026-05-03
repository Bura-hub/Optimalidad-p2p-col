"""
tests/test_cal20_cot_alpha.py — CAL-20 Sensibilidad cot_alpha en C2
======================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 3.1-3.3

Verifica:
  1. Linealidad de `net_benefit C2` en `cot_alpha`.
  2. `cot_alpha` es inerte cuando `consumer_ids = []` (configuracion
     MTE real).
  3. `savings_COT` es proporcional a `cot_alpha`.

Referencia: docs/adr/0020-cal20-cot-alpha-sensibilidad.md
            scripts/study_cot_alpha.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scenarios.scenario_c2_bilateral import run_c2_bilateral

# ── Fixture sintetica reusable ──────────────────────────────────────────────


def _build_synthetic_setup(N: int = 5, T: int = 24, seed: int = 0):
    """Genera D, G, pi_gs, g_comp, cvm, cot, mem deterministicos.

    Calibrado para activar el flujo PPA: prosumers (0, 1, 4) tienen
    G > D durante el pico solar; consumers (2, 3) tienen D pura.
    """
    # Patron diurno: noche 0, manana subida, mediodia pico, tarde bajada.
    g_pattern = np.zeros(T)
    g_pattern[6:18] = np.array([0.3, 0.6, 0.9, 1.0, 1.0, 1.0,
                                 1.0, 1.0, 0.9, 0.7, 0.5, 0.2])
    d_pattern = np.full(T, 0.5)
    d_pattern[8:20] = 1.0  # carga diurna estable

    # Prosumers (0, 1, 4): G grande, D pequena -> mucho surplus diurno.
    # Consumers (2, 3): G nula, D normal.
    g_base = np.array([10.0, 8.0, 0.0, 0.0, 7.0])
    d_base = np.array([3.0, 2.5, 5.0, 7.0, 2.0])
    D = np.outer(d_base, d_pattern)
    G = np.outer(g_base, g_pattern)

    pi_gs = np.full((N, T), 900.0)
    g_comp = np.full((N, T), 300.0)
    cvm = np.full((N, T), 175.0)
    cot = np.full((N, T), 40.0)
    mem = np.full((N, T), 16.0)
    return D, G, pi_gs, g_comp, cvm, cot, mem


def _run_c2(alpha: float, prosumer_ids, consumer_ids,
             D, G, pi_gs, g_comp, cvm, cot, mem):
    return run_c2_bilateral(
        D=D, G=G,
        pi_gs=pi_gs, pi_gb=280.0, pi_ppa=300.0,
        prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
        g_component=g_comp,
        cvm_component=cvm,
        cot_component=cot,
        mem_costs=mem,
        cot_alpha=alpha,
    )


# ── Grupo A — Linealidad ────────────────────────────────────────────────────


def test_linealidad_net_benefit_en_cot_alpha():
    """net_benefit(alpha=2) - net_benefit(alpha=0) = 2*(net_benefit(1) - net_benefit(0))."""
    D, G, pi_gs, g_comp, cvm, cot, mem = _build_synthetic_setup()
    prosumers = [0, 1, 4]
    consumers = [2, 3]

    nb0 = _run_c2(0.0, prosumers, consumers, D, G, pi_gs, g_comp, cvm, cot, mem
                   )["aggregate"]["total_net_benefit"]
    nb1 = _run_c2(1.0, prosumers, consumers, D, G, pi_gs, g_comp, cvm, cot, mem
                   )["aggregate"]["total_net_benefit"]
    nb2 = _run_c2(2.0, prosumers, consumers, D, G, pi_gs, g_comp, cvm, cot, mem
                   )["aggregate"]["total_net_benefit"]

    expected_at_2 = nb0 + 2.0 * (nb1 - nb0)
    rel_err = abs(nb2 - expected_at_2) / max(abs(expected_at_2), 1e-9)
    assert rel_err < 1e-9, (
        f"net_benefit no es lineal en cot_alpha. "
        f"nb(0)={nb0:.2f} nb(1)={nb1:.2f} nb(2)={nb2:.2f} "
        f"esperado nb(2)={expected_at_2:.2f}, error rel={rel_err:.2e}"
    )


def test_savings_cot_proporcional_a_cot_alpha():
    """savings_COT(alpha) / cot_alpha es constante (excepto alpha=0)."""
    D, G, pi_gs, g_comp, cvm, cot, mem = _build_synthetic_setup()
    prosumers = [0, 1, 4]
    consumers = [2, 3]

    s05 = _run_c2(0.5, prosumers, consumers, D, G, pi_gs, g_comp, cvm, cot, mem
                   )["aggregate"]["total_savings_COT"]
    s10 = _run_c2(1.0, prosumers, consumers, D, G, pi_gs, g_comp, cvm, cot, mem
                   )["aggregate"]["total_savings_COT"]
    s20 = _run_c2(2.0, prosumers, consumers, D, G, pi_gs, g_comp, cvm, cot, mem
                   )["aggregate"]["total_savings_COT"]

    assert s10 > 0, "savings_COT debe ser > 0 con consumer_ids != []"
    rel = lambda a, b: abs(a - b) / max(abs(b), 1e-9)
    assert rel(s05 * 2.0, s10) < 1e-9, "ratio s(0.5)*2 != s(1.0)"
    assert rel(s20 / 2.0, s10) < 1e-9, "ratio s(2.0)/2 != s(1.0)"


def test_savings_cot_cero_en_alpha_cero():
    """`cot_alpha=0` produce `savings_COT=0` exacto."""
    D, G, pi_gs, g_comp, cvm, cot, mem = _build_synthetic_setup()
    res = _run_c2(0.0, [0, 1, 4], [2, 3],
                   D, G, pi_gs, g_comp, cvm, cot, mem)
    assert res["aggregate"]["total_savings_COT"] == 0.0


# ── Grupo B — Inercia en configuracion MTE real (consumer_ids = []) ─────────


def test_cot_alpha_inerte_si_consumer_ids_vacio():
    """cot_alpha no afecta net_benefit cuando consumer_ids=[] (MTE real)."""
    D, G, pi_gs, g_comp, cvm, cot, mem = _build_synthetic_setup()
    prosumers = list(range(5))
    consumers = []  # MTE real: todos prosumidores

    nb0 = _run_c2(0.0, prosumers, consumers,
                   D, G, pi_gs, g_comp, cvm, cot, mem
                   )["aggregate"]["total_net_benefit"]
    nb1 = _run_c2(1.0, prosumers, consumers,
                   D, G, pi_gs, g_comp, cvm, cot, mem
                   )["aggregate"]["total_net_benefit"]
    nb2 = _run_c2(2.0, prosumers, consumers,
                   D, G, pi_gs, g_comp, cvm, cot, mem
                   )["aggregate"]["total_net_benefit"]

    assert nb0 == pytest.approx(nb1, abs=1e-6)
    assert nb1 == pytest.approx(nb2, abs=1e-6)


# ── Grupo C — Default 1.0 ─────────────────────────────────────────────────────


def test_default_cot_alpha_es_1_0():
    """`run_c2_bilateral` usa `cot_alpha=1.0` cuando no se pasa explicitamente."""
    import inspect
    sig = inspect.signature(run_c2_bilateral)
    assert sig.parameters["cot_alpha"].default == 1.0
