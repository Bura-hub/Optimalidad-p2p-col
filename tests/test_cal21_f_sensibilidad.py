"""
tests/test_cal21_f_sensibilidad.py — CAL-21 Sensibilidad de `f` en C2
======================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 3.1-3.3

Verifica las tres hipotesis sustanciales del default `f = 0.5`:

  H1. `total_net_benefit C2` es INVARIANTE en `f` (teorema §3.8).
  H2. `Gini(net_benefit)` NO es invariante (justifica SA-3).
  H3. `f = 0.5` es la cota egalitaria.

Ademas verifica que con `consumer_ids = []` (configuracion MTE real),
`f` es inerte — consistente con CAL-20.

Referencia: docs/adr/0021-cal21-c2-f-split-sensibilidad.md
            scripts/study_f_split.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scenarios.scenario_c2_bilateral import run_c2_bilateral


def _build_synthetic_setup(N: int = 5, T: int = 24):
    """Setup deterministico que activa el flujo PPA."""
    g_pattern = np.zeros(T)
    g_pattern[6:18] = np.array([0.3, 0.6, 0.9, 1.0, 1.0, 1.0,
                                 1.0, 1.0, 0.9, 0.7, 0.5, 0.2])
    d_pattern = np.full(T, 0.5)
    d_pattern[8:20] = 1.0
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


def _gini(values: np.ndarray) -> float:
    v = np.asarray(values, dtype=float).flatten()
    if v.size == 0 or np.all(v == 0):
        return 0.0
    if np.any(v < 0):
        v = v - v.min()
    v = np.sort(v)
    n = v.size
    cum = np.cumsum(v)
    return float((2 * np.sum(np.arange(1, n + 1) * v) - (n + 1) * cum[-1])
                  / (n * cum[-1]))


def _run_c2_with_f(f: float, prosumer_ids, consumer_ids,
                    D, G, pi_gs, g_comp, cvm, cot, mem):
    pi_gb = 280.0
    g_mean = float(np.nanmean(g_comp))
    cvm_mean = float(np.nanmean(cvm))
    cot_mean = float(np.nanmean(cot))
    mem_mean = float(np.nanmean(mem))
    pi_upper = g_mean + cvm_mean + 1.0 * cot_mean - mem_mean
    pi_ppa = pi_gb + f * (pi_upper - pi_gb)
    return run_c2_bilateral(
        D=D, G=G,
        pi_gs=pi_gs, pi_gb=pi_gb, pi_ppa=pi_ppa,
        prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
        g_component=g_comp, cvm_component=cvm,
        cot_component=cot, mem_costs=mem, cot_alpha=1.0,
    )


# ── H1: invarianza del agregado ─────────────────────────────────────────────


def test_total_net_benefit_invariante_en_f():
    """H1: total_net_benefit es invariante en f (Δ < 1e-9 % entre f=0 y f=1)."""
    D, G, pi_gs, g_comp, cvm, cot, mem = _build_synthetic_setup()
    pros, cons = [0, 1, 4], [2, 3]

    nb = []
    for f in [0.0, 0.25, 0.5, 0.75, 1.0]:
        r = _run_c2_with_f(f, pros, cons, D, G, pi_gs, g_comp, cvm, cot, mem)
        nb.append(r["aggregate"]["total_net_benefit"])
    spread = max(nb) - min(nb)
    rel = spread / max(abs(np.mean(nb)), 1e-9)
    assert rel < 1e-9, (
        f"total_net_benefit NO invariante en f: spread={spread:.3e}, "
        f"rel={rel:.3e}, valores={nb}"
    )


# ── H2: Gini monotono creciente en f ─────────────────────────────────────────


def test_gini_monotono_creciente_en_f():
    """H2: Gini sube monotonicamente con f (split mas favorable a prosumer)."""
    D, G, pi_gs, g_comp, cvm, cot, mem = _build_synthetic_setup()
    pros, cons = [0, 1, 4], [2, 3]

    ginis = []
    for f in [0.0, 0.25, 0.5, 0.75, 1.0]:
        r = _run_c2_with_f(f, pros, cons, D, G, pi_gs, g_comp, cvm, cot, mem)
        nb_per = np.array([r["per_agent"][n]["net_benefit"] for n in range(5)])
        ginis.append(_gini(nb_per))
    diffs = np.diff(ginis)
    assert (diffs >= -1e-9).all(), (
        f"Gini no monotono creciente: ginis={ginis}, diffs={diffs}"
    )
    # rango notable: al menos 0.01 entre f=0 y f=1
    assert (ginis[-1] - ginis[0]) > 0.01, (
        f"Gini casi invariante: rango={ginis[-1]-ginis[0]:.4f}; "
        f"esperado > 0.01. Eso falsificaria H2."
    )


# ── H3: simetria egalitaria en f=0.5 ─────────────────────────────────────────


def test_f_05_egalitaria():
    """H3: nb_consumer_mean(0.5) es la mediana del rango [f=0, f=1]."""
    D, G, pi_gs, g_comp, cvm, cot, mem = _build_synthetic_setup()
    pros, cons = [0, 1, 4], [2, 3]

    means = {}
    for f in [0.0, 0.5, 1.0]:
        r = _run_c2_with_f(f, pros, cons, D, G, pi_gs, g_comp, cvm, cot, mem)
        means[f] = np.mean([r["per_agent"][n]["net_benefit"] for n in cons])
    mid = (means[0.0] + means[1.0]) / 2.0
    err = abs(means[0.5] - mid) / max(abs(mid), 1e-9)
    assert err < 1e-9, (
        f"nb_consumer_mean(f=0.5) no es la mediana de [f=0, f=1]: "
        f"means={means}, mediana={mid:.2f}, error rel={err:.3e}"
    )


# ── Inercia con consumer_ids vacio (config MTE real) ────────────────────────


def test_f_inerte_si_consumer_ids_vacio():
    """Cuando consumer_ids=[], f es inerte (consistente con CAL-20)."""
    D, G, pi_gs, g_comp, cvm, cot, mem = _build_synthetic_setup()
    pros = list(range(5))
    cons = []  # MTE real

    r0 = _run_c2_with_f(0.0, pros, cons, D, G, pi_gs, g_comp, cvm, cot, mem)
    r1 = _run_c2_with_f(1.0, pros, cons, D, G, pi_gs, g_comp, cvm, cot, mem)
    assert r0["aggregate"]["total_net_benefit"] == pytest.approx(
        r1["aggregate"]["total_net_benefit"], abs=1e-6
    )
