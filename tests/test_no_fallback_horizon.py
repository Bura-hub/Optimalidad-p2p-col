"""
tests/test_no_fallback_horizon.py — CAL-18 fail-fast Cedenar
================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 2.1

Verifica que `data/cedenar_tariff.py` opera en modo fail-fast por
defecto (sin fallback silencioso) y que la cobertura actual permite
correr la simulacion sin fallback explicito.

Referencia: ADR-0018 (CAL-18, tarifa Cedenar fail-fast).
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import pytest

from data import cedenar_tariff as ct
from data.cedenar_tariff import (
    DEFAULT_PI_GS_FALLBACK,
    LEGACY_PI_GS_DIAGNOSTIC_FALLBACK,
    INSTITUTION_PROFILE,
    TariffProfile,
    _lookup_pi_gs,
    effective_pi_gs,
    effective_pi_gs_per_agent,
    pi_gs_per_agent_hourly,
    load_monthly_tariffs,
)


# ─── Grupo A — Constantes ───────────────────────────────────────────────────

def test_default_fallback_is_none():
    """CAL-18 invariante: el default es fail-fast (None)."""
    assert DEFAULT_PI_GS_FALLBACK is None, (
        "DEFAULT_PI_GS_FALLBACK debe ser None tras CAL-18 (ADR-0018). "
        f"Valor actual: {DEFAULT_PI_GS_FALLBACK!r}"
    )


def test_legacy_diagnostic_fallback_preserved():
    """CLI/diagnostico conserva el escalar 650 COP/kWh."""
    assert LEGACY_PI_GS_DIAGNOSTIC_FALLBACK == 650.0


# ─── Grupo B — _lookup_pi_gs ────────────────────────────────────────────────

def _df_y_perfil():
    df = load_monthly_tariffs()
    prof = INSTITUTION_PROFILE["Udenar"]
    return df, prof


def test_lookup_raises_when_month_missing_default():
    """Mes fuera de cobertura sin fallback explicito → KeyError."""
    df, prof = _df_y_perfil()
    with pytest.raises(KeyError, match=r"CAL-18|ADR-0018"):
        _lookup_pi_gs(df, "2024-01", prof)  # mes fuera del CSV


def test_lookup_uses_fallback_when_explicit():
    """Con fallback=600 explicito, retorna 600 + warning."""
    df, prof = _df_y_perfil()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        v = _lookup_pi_gs(df, "2024-01", prof, fallback=600.0)
    assert v == pytest.approx(600.0)
    msg_warns = [str(w.message) for w in caught
                 if "[cedenar_tariff]" in str(w.message)]
    assert msg_warns, "Se esperaba un warning explicito de fallback"


def test_lookup_in_covered_month_returns_real_value():
    """Mes en cobertura: lookup no toca fallback."""
    df, prof = _df_y_perfil()
    v = _lookup_pi_gs(df, "2025-08", prof)  # cubierto
    assert v > 0 and v < 5000  # sanity


def test_keyerror_mentions_adr_0018():
    """El mensaje del KeyError debe citar ADR-0018 para trazabilidad."""
    df, prof = _df_y_perfil()
    with pytest.raises(KeyError) as ei:
        _lookup_pi_gs(df, "2024-01", prof)
    assert "ADR-0018" in str(ei.value) or "CAL-18" in str(ei.value)


# ─── Grupo C — effective_pi_gs (escalar por horizonte) ──────────────────────

def test_effective_pi_gs_full_horizon_works():
    """Horizonte real --full (abr-2025 a dic-2025) sin fallback explicito."""
    prof = INSTITUTION_PROFILE["Udenar"]
    v = effective_pi_gs("2025-04-04", "2025-12-16", prof)
    assert 200 < v < 2000  # sanity COP/kWh


def test_effective_pi_gs_outside_horizon_raises():
    """Mes fuera de cobertura levanta KeyError con default fail-fast."""
    prof = INSTITUTION_PROFILE["Udenar"]
    with pytest.raises(KeyError, match=r"CAL-18|ADR-0018"):
        effective_pi_gs("2024-11-01", "2025-01-01", prof)


# ─── Grupo D — pi_gs_per_agent_hourly ───────────────────────────────────────

def test_pi_gs_per_agent_hourly_full_horizon_works():
    """Matriz (N, T) sobre horizonte real sin fallback explicito."""
    idx = pd.date_range("2025-04-04", "2025-12-16",
                        freq="1h", inclusive="left")
    agents = list(INSTITUTION_PROFILE.keys())
    M = pi_gs_per_agent_hourly(agents, idx)
    assert M.shape == (len(agents), len(idx))
    assert np.isfinite(M).all(), "No debe haber NaN si cobertura 100 %"
    assert (M > 0).all() and (M < 5000).all()


def test_pi_gs_per_agent_hourly_unknown_agent_raises():
    """Agente sin perfil → KeyError con default fail-fast."""
    idx = pd.date_range("2025-08-01", "2025-08-02",
                        freq="1h", inclusive="left")
    with pytest.raises(KeyError, match=r"CAL-18|ADR-0018"):
        pi_gs_per_agent_hourly(["NoExiste"], idx)
