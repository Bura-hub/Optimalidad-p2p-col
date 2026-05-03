"""
tests/test_cal19_iters_real.py — CAL-19 Convergencia Stackelberg empirica
==========================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 2.1

Valida que `stackelberg_iters=2` (default) produce un bienestar
indistinguible (< 1 %) del producido con `stackelberg_iters=10`
sobre datos MTE reales. Test de regresion que previene drift en
los parametros del bucle Stackelberg.

Optimizado para CI: usa un subset de 48 h (sub-subset del audit
oficial de 168 h) y solo dos puntos del barrido (`iters in {2, 10}`).

Referencia: docs/adr/0019-cal19-stackelberg-convergencia-empirica.md
            analysis/stackelberg_convergence_real.py (audit completo).
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Windows: stdout UTF-8 para que la barra de progreso del EMS no rompa.
if sys.platform == "win32" and not isinstance(
    sys.stdout, io.TextIOWrapper
):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                   encoding="utf-8", errors="replace")

# Tolerancia 1 % alineada con la regla del plan radiant-sleeping-eagle:
#   |welfare(iters=2) - welfare(iters=10)| / |welfare(iters=10)| < 1%.
TOL_WELFARE_PCT = 1.0
# Tolerancia 0.5 % para kwh_p2p_total (mas estricto: el volumen P2P es
# invariante a partir de la primera pasada del juego).
TOL_KWH_PCT = 0.5

# Subset 48 h (jue-vie ago 2025): horizonte minimo viable que cubre
# 1 dia laboral + 1 dia activo P2P. ~30 s por iter en CI.
T_START = "2025-08-07"
T_END = "2025-08-09"
ITERS_LIST = [2, 10]


@pytest.fixture(scope="module")
def mte_subset():
    """Carga el subset una vez para los dos puntos del barrido."""
    from data.xm_data_loader import MTEDataLoader, slice_horizon, AGENTS
    mte_root = os.environ.get("MTE_ROOT",
                              str(ROOT / "MedicionesMTE_v3"))
    if not Path(mte_root).is_dir():
        pytest.skip(f"MTE_ROOT no disponible: {mte_root}")
    loader = MTEDataLoader(root_path=mte_root)
    D_full, G_full, idx = loader.load(verbose=False)
    D, G, idx_sub = slice_horizon(D_full, G_full, idx, T_START, T_END)
    if D.shape[1] < 24:
        pytest.skip(f"Subset {T_START}..{T_END} demasiado corto: {D.shape}")
    return D, G, idx_sub, list(AGENTS)


def _run_iters(iters: int, D, G, agent_names: list[str]) -> dict:
    """Helper: corre EMS con iters dado y devuelve metricas agregadas."""
    from analysis.stackelberg_convergence_real import (
        run_one_iters, _build_agents_real, _build_grid,
    )
    from data.cedenar_tariff import community_effective_pi_gs

    N = D.shape[0]
    pi_gs_eff = community_effective_pi_gs(
        agent_names, T_START, T_END, weights=D.mean(axis=1),
    )
    agents = _build_agents_real(N, agent_names)
    grid = _build_grid(pi_gs_eff, pi_gb=280.0)
    return run_one_iters(iters, D, G, agents, grid)


def test_iters_2_vs_10_welfare_within_1pct(mte_subset):
    """|welfare(iters=2) − welfare(iters=10)| / |welfare(10)| < 1 %."""
    D, G, _idx, agent_names = mte_subset
    r2 = _run_iters(2, D, G, agent_names)
    r10 = _run_iters(10, D, G, agent_names)

    delta_pct = (
        abs(r2["welfare_total"] - r10["welfare_total"])
        / max(abs(r10["welfare_total"]), 1e-9) * 100
    )
    assert delta_pct < TOL_WELFARE_PCT, (
        f"|welfare(iters=2) − welfare(iters=10)| / |welfare(10)| "
        f"= {delta_pct:.4f} % >= {TOL_WELFARE_PCT} %\n"
        f"  iters=2:  welfare={r2['welfare_total']:.1f}\n"
        f"  iters=10: welfare={r10['welfare_total']:.1f}"
    )


def test_iters_2_vs_10_kwh_p2p_within_05pct(mte_subset):
    """`kwh_p2p_total` es practicamente invariante a partir de iters=1."""
    D, G, _idx, agent_names = mte_subset
    r2 = _run_iters(2, D, G, agent_names)
    r10 = _run_iters(10, D, G, agent_names)
    delta_pct = (
        abs(r2["kwh_p2p_total"] - r10["kwh_p2p_total"])
        / max(abs(r10["kwh_p2p_total"]), 1e-9) * 100
    )
    assert delta_pct < TOL_KWH_PCT, (
        f"kwh_p2p_total difiere {delta_pct:.4f} % >= {TOL_KWH_PCT} %"
    )


def test_iters_2_is_faster_than_iters_10(mte_subset):
    """Sustento del speedup: iters=2 debe ser sustancialmente mas rapido."""
    D, G, _idx, agent_names = mte_subset
    r2 = _run_iters(2, D, G, agent_names)
    r10 = _run_iters(10, D, G, agent_names)
    # iters=2 debe ser al menos 1.3x mas rapido (margen tolerante para CI ruidoso)
    speedup = r10["elapsed_s"] / max(r2["elapsed_s"], 1e-3)
    assert speedup >= 1.3, (
        f"speedup iters=2 vs iters=10: {speedup:.2f}x < 1.3x esperado.\n"
        f"  iters=2:  elapsed={r2['elapsed_s']} s\n"
        f"  iters=10: elapsed={r10['elapsed_s']} s"
    )


def test_norm_residual_below_tol_with_iters_2(mte_subset):
    """Con iters=2, la norma residual mediana debe estar bajo `stackelberg_tol`."""
    D, G, _idx, agent_names = mte_subset
    r2 = _run_iters(2, D, G, agent_names)
    # stackelberg_tol = 1e-3; mediana real esperada ~1e-4 segun audit.
    assert r2["norm_rel_median"] < 1e-3 + 1e-9, (
        f"norm_rel mediana = {r2['norm_rel_median']:.2e} >= 1e-3"
    )
