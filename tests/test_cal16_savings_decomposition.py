"""
tests/test_cal16_savings_decomposition.py
=========================================
CAL-16 (2026-05-02) — Descomposición regulatoria del ahorro en C2.

Valida que el cálculo de savings_cons en `run_c2_bilateral` se descompone
en sus componentes regulatorios exactos:

    savings = E_PPA × [(G − π_ppa) + Cvm + α·COT − MEM]

con
  - G   negociable bajo Ley 143/1994 art. 41
  - Cvm ahorrado al 100 % por sustitución del comercializador minorista
        por representante MEM (CREG 086/1996 + CREG 156/2012)
  - α·COT cota de margen tributario (CREG 101-028/2023; default α=1.0)
  - MEM = FAZNI + 0.04·G + π_rep
        (Ley 1715/2014 art. 19 + Ley 1117/2006 + Ley 2099/2021 art. 45)

Ref: ADR-0016; spec docs/superpowers/specs/2026-05-02-cal16-c2-savings-decomposition.md
"""

import numpy as np
import pandas as pd
import pytest
from pathlib import Path


AGENTS_NT2 = ["Cesmag", "HUDN", "Mariana", "UCC", "Udenar"]


def _idx_abr_2026() -> pd.DatetimeIndex:
    """Índice horario para abril 2026, hora local Bogotá."""
    return pd.date_range(
        "2026-04-01", "2026-04-30 23:00", freq="h",
        tz="America/Bogota",
    )


# ── Task 2: tolls_per_agent_hourly ─────────────────────────────────────────


def test_tolls_per_agent_hourly_devuelve_NT_y_suma_correcta():
    """T+D+PR+Rm para abr-2026 NT2 oficial = 55.95+165.37+21.09+30.64=273.05."""
    from data.cedenar_tariff import tolls_per_agent_hourly
    idx = _idx_abr_2026()
    tolls = tolls_per_agent_hourly(AGENTS_NT2, idx)
    assert tolls.shape == (5, len(idx))
    # Cesmag (comercial NT2): T+D+PR+R varía vs oficial pero usa mismo CSV;
    # Udenar (oficial NT2 abr-2026): 55.95 + 165.37 + 21.09 + 30.64 ≈ 273.05
    udenar_idx = AGENTS_NT2.index("Udenar")
    assert np.isclose(tolls[udenar_idx, 0], 273.05, atol=0.5), (
        f"Udenar T+D+PR+R = {tolls[udenar_idx, 0]:.2f}, esperado ≈ 273.05"
    )


# ── Task 3: cu_components_per_agent_hourly ─────────────────────────────────


def test_cu_components_per_agent_hourly_reconcilia_cu_oficial():
    """Para usuarios 'oficial' (Udenar, HUDN), la suma de los 7
    componentes debe igualar CU_aplicado.

    Para 'comercial', CU_aplicado incluye la contribución 20 %
    (Ley 142/1994 art. 131), por lo que la reconciliación pura
    sólo aplica a la categoría oficial.
    """
    from data.cedenar_tariff import cu_components_per_agent_hourly
    idx = _idx_abr_2026()
    comps = cu_components_per_agent_hourly(AGENTS_NT2, idx)
    # claves esperadas
    for k in ("G", "T", "D", "Cvm", "PR", "R", "COT", "CU"):
        assert k in comps, f"falta clave '{k}'"
        assert comps[k].shape == (5, len(idx)), (
            f"{k} shape {comps[k].shape} != (5, {len(idx)})"
        )
    # reconciliación: G + T + D + Cvm + PR + R + COT == CU (solo oficial)
    suma = (comps["G"] + comps["T"] + comps["D"] + comps["Cvm"]
            + comps["PR"] + comps["R"] + comps["COT"])
    oficial_idx = [AGENTS_NT2.index(a) for a in ("Udenar", "HUDN")]
    assert np.allclose(
        suma[oficial_idx], comps["CU"][oficial_idx], atol=0.5,
        equal_nan=True,
    ), (
        f"Suma componentes != CU oficial: max|delta| = "
        f"{np.nanmax(np.abs(suma[oficial_idx] - comps['CU'][oficial_idx])):.2f}"
    )
    # Para 'comercial', CU_aplicado debe ser 1.20 × suma (contrib 20%)
    comercial_idx = [AGENTS_NT2.index(a) for a in ("Cesmag", "Mariana", "UCC")]
    ratio = comps["CU"][comercial_idx] / suma[comercial_idx]
    assert np.allclose(ratio, 1.20, atol=0.005, equal_nan=True), (
        f"CU_comercial / suma_componentes != 1.20: media = "
        f"{np.nanmean(ratio):.4f}"
    )


# ── Task 4: mem_costs_per_agent_hourly ─────────────────────────────────────


def test_mem_costs_per_agent_hourly_fazni_y_4pct_y_rep():
    """MEM_costs = FAZNI + 0.04·G + π_rep
    abr-2026 NT2 oficial: G = 310.96 -> 4 % = 12.4384
    1.90 + 12.4384 + 2.00 ≈ 16.34 COP/kWh
    """
    from data.cedenar_tariff import mem_costs_per_agent_hourly
    idx = _idx_abr_2026()
    mem = mem_costs_per_agent_hourly(AGENTS_NT2, idx)
    assert mem.shape == (5, len(idx))
    udenar_idx = AGENTS_NT2.index("Udenar")
    expected = 1.90 + 0.04 * 310.96 + 2.00
    assert np.isclose(mem[udenar_idx, 0], expected, atol=0.05), (
        f"Udenar MEM = {mem[udenar_idx, 0]:.3f}, esperado ≈ {expected:.3f}"
    )
    # Para Cesmag (comercial NT2 abr-2026: G = 310.96 mismo valor que oficial)
    cesmag_idx = AGENTS_NT2.index("Cesmag")
    assert np.isclose(mem[cesmag_idx, 0], expected, atol=0.05)


# ── Task 5: refactor run_c2_bilateral descompuesto ─────────────────────────


def test_run_c2_savings_descompuesto_es_suma_componentes():
    """savings_ppa = savings_G + savings_Cvm + α·savings_COT − mem_costs.

    Diseño manual: 1 prosumidor genera 10 kWh durante horas 0..11
    (12 h), 1 consumidor demanda 5 kWh/h. El consumidor recibe
    5 kWh PPA cada hora durante 12 h = 60 kWh.

      G = 310, Cvm = 176, COT = 39, MEM = 16, π_ppa = 350, α = 1.0
      savings_G    = 60 × (310 − 350) = -2400
      savings_Cvm  = 60 × 176 = 10560
      savings_COT  = 1.0 × 60 × 39 = 2340
      mem_costs    = 60 × 16 = 960
      savings_ppa  = -2400 + 10560 + 2340 − 960 = 9540
    """
    from scenarios.scenario_c2_bilateral import run_c2_bilateral
    N, T = 2, 24
    D = np.ones((N, T)) * 5.0
    G = np.zeros((N, T))
    G[0, :12] = 10.0
    pi_gs = np.full((N, T), 800.0)
    g     = np.full((N, T), 310.0)
    cvm   = np.full((N, T), 176.0)
    cot   = np.full((N, T), 39.0)
    mem   = np.full((N, T), 16.0)
    res = run_c2_bilateral(
        D=D, G=G, pi_gs=pi_gs, pi_gb=200.0, pi_ppa=350.0,
        prosumer_ids=[0], consumer_ids=[1],
        g_component=g, cvm_component=cvm, cot_component=cot,
        mem_costs=mem, cot_alpha=1.0,
    )
    per = res["per_agent"][1]
    assert np.isclose(per["savings_G"],   -2400.0, atol=1.0), per
    assert np.isclose(per["savings_Cvm"],  10560.0, atol=1.0), per
    assert np.isclose(per["savings_COT"],   2340.0, atol=1.0), per
    assert np.isclose(per["mem_costs"],      960.0, atol=1.0), per
    assert np.isclose(per["savings_ppa"],   9540.0, atol=1.0), per


def test_run_c2_compat_pi_G_legacy_no_descompone():
    """Modo legacy CAL-13: pasar solo pi_G (sin g/cvm/cot/mem) preserva
    comportamiento anterior; savings_G es la suma agregada y los
    demás componentes son 0.
    """
    from scenarios.scenario_c2_bilateral import run_c2_bilateral
    N, T = 2, 24
    D = np.ones((N, T)) * 5.0
    G = np.zeros((N, T))
    G[0, :12] = 10.0
    pi_gs = np.full((N, T), 800.0)
    pi_G  = np.full((N, T), 526.0)  # G+Cvm+COT agregado CAL-13
    res = run_c2_bilateral(
        D=D, G=G, pi_gs=pi_gs, pi_gb=200.0, pi_ppa=350.0,
        prosumer_ids=[0], consumer_ids=[1],
        pi_G=pi_G,
    )
    per = res["per_agent"][1]
    # Modo CAL-13: savings_ppa = ppa × (526 − 350) × 60 h = 60 × 176 = 10560
    assert np.isclose(per["savings_ppa"], 10560.0, atol=1.0), per
    # En modo CAL-13, Cvm/COT/MEM están en cero
    assert per["savings_Cvm"] == 0.0
    assert per["savings_COT"] == 0.0
    assert per["mem_costs"] == 0.0


# ── Task 6: comparison_engine acepta nuevos parámetros ─────────────────────


def test_run_comparison_acepta_parametros_descompuestos():
    """run_comparison expone los 5 parámetros nuevos (g/cvm/cot/mem/alpha)."""
    from scenarios.comparison_engine import run_comparison
    import inspect
    sig = inspect.signature(run_comparison)
    expected = ("g_component", "cvm_component", "cot_component",
                "mem_costs", "cot_alpha")
    for p in expected:
        assert p in sig.parameters, (
            f"falta parametro '{p}' en run_comparison; firma actual: "
            f"{list(sig.parameters)}"
        )
