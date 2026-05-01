"""
tests/test_cedenar_cvm_cot.py — CAL-10b.2 (literalidad CREG 174 art. 25)
=======================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Verifica el helper que extrae el componente Cvm,i,j puro del CSV mensual
Cedenar para alimentar la liquidacion CREG 174/2021 art. 25 sobre la
energia permutada (Excedentes Tipo 1 en jerga industria).

Historico: en CAL-10b inicial el helper devolvia Cvm + COT (interpretacion
conservadora). Tras revision del texto oficial CREG 174/2021 art. 25
(WebSearch gestornormativo.creg.gov.co) se corrige a Cvm puro:
"el comercializador cobra al AGPE el componente Cvm,i,j de la Resolucion
CREG 119 de 2007", sin mencion al COT (CREG 101 028/2023).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from data.cedenar_tariff import (
    INSTITUTION_PROFILE,
    TariffProfile,
    _lookup_cvm,
    cvm_per_agent_hourly,
    load_monthly_tariffs,
)


def test_lookup_cvm_real_value_oficial_NT2_2025_04():
    """2025-04 oficial NT2 cedenar: Cvm = 174.69 COP/kWh (PDF Cedenar)."""
    df = load_monthly_tariffs()
    profile = TariffProfile("oficial", 2, "cedenar")
    result = _lookup_cvm(df, "2025-04", profile)
    assert result == pytest.approx(174.69, rel=1e-4)


def test_lookup_cvm_no_incluye_cot():
    """Verifica explicitamente que _lookup_cvm NO suma COT.

    CREG 174/2021 art. 25 cita literalmente "el componente Cvm,i,j de
    CREG 119/2007"; el COT (CREG 101 028/2023) no se incluye.
    """
    df = load_monthly_tariffs()
    profile = TariffProfile("oficial", 2, "cedenar")
    cvm = _lookup_cvm(df, "2026-04", profile)
    # Si erroneamente incluyera COT, estaria cerca de 215.14 (176.41+38.73).
    assert cvm == pytest.approx(176.41, rel=1e-4)
    assert cvm < 200, "El helper esta sumando COT por error"


def test_cvm_per_agent_hourly_shape():
    """Devuelve matriz (N, T) con tipo float."""
    agents = ["Udenar", "Mariana"]
    idx = pd.date_range("2025-07-01", "2025-07-04", freq="1h",
                        inclusive="left", tz="America/Bogota")
    arr = cvm_per_agent_hourly(agents, idx)
    assert arr.shape == (2, 72)
    assert arr.dtype == np.float64


def test_cvm_constante_dentro_de_un_mes():
    """Todas las horas del mismo mes comparten el mismo valor Cvm."""
    agents = ["Udenar"]
    idx = pd.date_range("2025-07-01", "2025-08-01", freq="1h",
                        inclusive="left", tz="America/Bogota")
    arr = cvm_per_agent_hourly(agents, idx)
    assert np.allclose(arr[0, :], arr[0, 0])


def test_cvm_per_agent_hourly_lookup_NT2():
    """Oficial y comercial NT2 comparten Cvm,i,j (CREG 119: depende de NT,
    no de categoria) en abril 2026 = 176.41 COP/kWh."""
    agents = ["Udenar", "Mariana"]   # oficial NT2 vs comercial NT2
    idx = pd.date_range("2026-04-01", "2026-04-02", freq="1h",
                        inclusive="left", tz="America/Bogota")
    arr = cvm_per_agent_hourly(agents, idx)
    expected = 176.41
    assert arr[0, 0] == pytest.approx(expected, abs=0.05)
    assert arr[1, 0] == pytest.approx(expected, abs=0.05)
