"""
tests/test_cedenar_cvm_cot.py — CAL-10b
========================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Verifica el helper que extrae Cvm + COT real del CSV mensual Cedenar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from data.cedenar_tariff import (
    INSTITUTION_PROFILE,
    TariffProfile,
    _lookup_cvm_plus_cot,
    cvm_plus_cot_per_agent_hourly,
    load_monthly_tariffs,
)


def test_lookup_cvm_plus_cot_real_value_oficial_NT2_2025_04():
    """2025-04 oficial NT2 cedenar: Cvm=174.69, COT=40.27 → C=214.96 COP/kWh."""
    df = load_monthly_tariffs()
    profile = TariffProfile("oficial", 2, "cedenar")
    result = _lookup_cvm_plus_cot(df, "2025-04", profile)
    assert result == pytest.approx(214.96, rel=1e-4)


def test_cvm_plus_cot_per_agent_hourly_shape():
    """Devuelve matriz (N, T) con tipo float."""
    agents = ["Udenar", "Mariana"]
    idx = pd.date_range("2025-07-01", "2025-07-04", freq="1h",
                        inclusive="left", tz="America/Bogota")
    arr = cvm_plus_cot_per_agent_hourly(agents, idx)
    assert arr.shape == (2, 72)
    assert arr.dtype == np.float64


def test_cvm_plus_cot_constante_dentro_de_un_mes():
    """Todas las horas del mismo mes comparten el mismo valor C."""
    agents = ["Udenar"]
    idx = pd.date_range("2025-07-01", "2025-08-01", freq="1h",
                        inclusive="left", tz="America/Bogota")
    arr = cvm_plus_cot_per_agent_hourly(agents, idx)
    # Todas las horas de julio deben ser iguales.
    assert np.allclose(arr[0, :], arr[0, 0])


def test_cvm_plus_cot_per_agent_hourly_lookup_distinto_por_categoria():
    """Oficial y comercial NT2 pueden tener Cvm idéntico pero verificamos lookup."""
    agents = ["Udenar", "Mariana"]   # oficial NT2 vs comercial NT2
    idx = pd.date_range("2026-04-01", "2026-04-02", freq="1h",
                        inclusive="left", tz="America/Bogota")
    arr = cvm_plus_cot_per_agent_hourly(agents, idx)
    # Ambos NT2: Cvm + COT_NT2 ≈ 215.14 COP/kWh en 2026-04 (PDF tarifa_2026-04.pdf).
    expected = 215.14
    assert arr[0, 0] == pytest.approx(expected, abs=0.05)
    assert arr[1, 0] == pytest.approx(expected, abs=0.05)
