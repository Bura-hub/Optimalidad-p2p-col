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
