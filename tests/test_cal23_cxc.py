"""
tests/test_cal23_cxc.py — CAL-23 CXC opt-in en C2 (PPA bilateral)
==================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 3.1-3.3

Verifica:
  1. Default sin pasar `cxc_component` no afecta el flujo C2 (compat).
  2. Schema y cobertura del CSV `data/cxc_costs.csv`.
  3. Helper `cxc_per_agent_hourly` produce matriz (N, T) en rango.
  4. Linealidad de `savings_CXC` en `cxc_alpha`.
  5. Inercia con `consumer_ids = []` (config MTE real).

Referencia: docs/adr/0023-cal23-c2-cxc-cargo-confiabilidad.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scenarios.scenario_c2_bilateral import run_c2_bilateral
from scenarios._c2_cxc import (
    load_cxc_monthly,
    cxc_per_agent_hourly,
    CSV_DEFAULT_PATH,
)


# ─── Grupo A — Schema y cobertura del CSV ───────────────────────────────────


def test_csv_existe():
    assert CSV_DEFAULT_PATH.exists()


def test_csv_schema_y_cobertura():
    df = load_cxc_monthly()
    assert "cxc_cop_kwh" in df.columns
    assert len(df) == 13
    expected = [f"2025-{m:02d}" for m in range(4, 13)] + \
                [f"2026-{m:02d}" for m in range(1, 5)]
    for m in expected:
        assert m in df.index, f"Falta mes {m}"


def test_csv_valores_en_rango():
    df = load_cxc_monthly()
    cxc = df["cxc_cop_kwh"].astype(float)
    # Banda ASOCODIS 2024: [5, 15] COP/kWh + margen.
    assert (cxc >= 3.0).all() and (cxc <= 20.0).all(), (
        f"CXC fuera de banda [3, 20]: {cxc.tolist()}"
    )


# ─── Grupo B — Helper cxc_per_agent_hourly ──────────────────────────────────


def test_helper_produce_matriz_correcta():
    idx = pd.date_range("2025-08-01", "2025-08-08",
                         freq="1h", inclusive="left")
    agents = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
    M = cxc_per_agent_hourly(agents, idx)
    assert M.shape == (5, len(idx))
    assert np.isfinite(M).all()
    assert (M > 0).all()


# ─── Grupo C — Compatibilidad: default no rompe C2 ──────────────────────────


def _build_synthetic(N=5, T=24):
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
    cxc = np.full((N, T), 10.0)
    return D, G, pi_gs, g_comp, cvm, cot, mem, cxc


def test_default_sin_cxc_no_cambia_resultado():
    """Sin pasar cxc_component, savings_CXC=0 y el resto del modelo intacto."""
    D, G, pi_gs, g_comp, cvm, cot, mem, _cxc = _build_synthetic()
    res = run_c2_bilateral(
        D=D, G=G, pi_gs=pi_gs, pi_gb=280.0, pi_ppa=400.0,
        prosumer_ids=[0, 1, 4], consumer_ids=[2, 3],
        g_component=g_comp, cvm_component=cvm,
        cot_component=cot, mem_costs=mem, cot_alpha=1.0,
    )
    assert res["aggregate"]["total_savings_CXC"] == 0.0


def test_cxc_component_pero_alpha_cero_es_inerte():
    """Pasar cxc_component pero cxc_alpha=0 mantiene savings_CXC=0."""
    D, G, pi_gs, g_comp, cvm, cot, mem, cxc = _build_synthetic()
    res = run_c2_bilateral(
        D=D, G=G, pi_gs=pi_gs, pi_gb=280.0, pi_ppa=400.0,
        prosumer_ids=[0, 1, 4], consumer_ids=[2, 3],
        g_component=g_comp, cvm_component=cvm,
        cot_component=cot, mem_costs=mem, cot_alpha=1.0,
        cxc_component=cxc, cxc_alpha=0.0,
    )
    assert res["aggregate"]["total_savings_CXC"] == 0.0


# ─── Grupo D — Linealidad e invariantes ─────────────────────────────────────


def test_savings_cxc_lineal_en_cxc_alpha():
    """savings_CXC(alpha) escala linealmente con cxc_alpha."""
    D, G, pi_gs, g_comp, cvm, cot, mem, cxc = _build_synthetic()

    def run_alpha(a):
        return run_c2_bilateral(
            D=D, G=G, pi_gs=pi_gs, pi_gb=280.0, pi_ppa=400.0,
            prosumer_ids=[0, 1, 4], consumer_ids=[2, 3],
            g_component=g_comp, cvm_component=cvm,
            cot_component=cot, mem_costs=mem, cot_alpha=1.0,
            cxc_component=cxc, cxc_alpha=a,
        )["aggregate"]["total_savings_CXC"]

    s05 = run_alpha(0.5)
    s10 = run_alpha(1.0)
    s20 = run_alpha(2.0)
    assert s10 > 0, "savings_CXC debe ser > 0 con consumer_ids != []"
    rel = lambda a, b: abs(a - b) / max(abs(b), 1e-9)
    assert rel(s05 * 2.0, s10) < 1e-9
    assert rel(s20 / 2.0, s10) < 1e-9


def test_cxc_alpha_inerte_si_consumer_ids_vacio():
    """Como cot_alpha (CAL-20): inerte si consumer_ids=[]."""
    D, G, pi_gs, g_comp, cvm, cot, mem, cxc = _build_synthetic()
    pros = list(range(5))
    cons = []  # MTE real

    def run_alpha(a):
        return run_c2_bilateral(
            D=D, G=G, pi_gs=pi_gs, pi_gb=280.0, pi_ppa=400.0,
            prosumer_ids=pros, consumer_ids=cons,
            g_component=g_comp, cvm_component=cvm,
            cot_component=cot, mem_costs=mem, cot_alpha=1.0,
            cxc_component=cxc, cxc_alpha=a,
        )["aggregate"]["total_net_benefit"]

    nb0 = run_alpha(0.0)
    nb1 = run_alpha(1.0)
    nb2 = run_alpha(2.0)
    assert nb0 == pytest.approx(nb1, abs=1e-6)
    assert nb1 == pytest.approx(nb2, abs=1e-6)


def test_default_cxc_alpha_es_0_0():
    """run_c2_bilateral usa cxc_alpha=0.0 cuando no se pasa explicitamente."""
    import inspect
    sig = inspect.signature(run_c2_bilateral)
    assert sig.parameters["cxc_alpha"].default == 0.0
