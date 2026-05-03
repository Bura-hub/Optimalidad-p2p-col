"""
tests/test_cal17_xm_audit.py — CAL-17 Auditoria pydataxm vs PB_PROM oficial
============================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 2.1

Verifica el invariante de tolerancia entre el cache pydataxm y el PB_PROM
oficial XM, y la sincronia entre `XM_MONTHLY_REAL` y los valores oficiales
declarados en el script de auditoria.

Referencia: docs/adr/0017-cal17-pydataxm-vs-ptb-audit.md
            docs/superpowers/specs/2026-05-02-cal17-pydataxm-vs-ptb-audit.md
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "audit_pydataxm_full_horizon.py"

# Tolerancia 15 %: limite mayor al 10 % del audit ejecutivo, en linea con el
# test pre-existente de regresion CAL-14 (test_creg101066_ceiling.py).
TOLERANCE_REGRESSION_PCT = 15.0
SIGNED_BIAS_LIMIT_PCT = 5.0


# ─── Grupo A — Script reproducible ──────────────────────────────────────────

def test_audit_script_exists():
    """El script de auditoria existe en la ruta documentada."""
    assert SCRIPT.exists(), f"Falta {SCRIPT}"


def test_audit_script_runs_and_produces_csv(tmp_path):
    """El script termina sin errores Python y produce el CSV reportado."""
    out_csv = tmp_path / "audit.csv"
    res = subprocess.run(
        [sys.executable, str(SCRIPT),
         "--tolerance", "0.15",
         "--output", str(out_csv)],
        cwd=str(ROOT),
        capture_output=True, text=True, timeout=120,
    )
    # El script termina con 0 si todos los meses pasan tolerancia 15 %.
    # Si algun mes excede 15 %, devuelve 1 — no es un crash.
    assert res.returncode in (0, 1), (
        f"Script crash. stdout=\n{res.stdout}\nstderr=\n{res.stderr}")
    assert out_csv.exists(), "El CSV de salida no se genero"

    df = pd.read_csv(out_csv)
    assert {"mes", "cache_mean", "oficial",
            "delta_pct", "fuera_tolerancia"} <= set(df.columns)
    assert len(df) == 7, f"Se esperan 7 meses, hay {len(df)}"


# ─── Grupo B — Invariantes numericos ────────────────────────────────────────

def _run_audit_dataframe() -> pd.DataFrame:
    """Helper: invoca la funcion de auditoria y devuelve el DataFrame."""
    sys.path.insert(0, str(ROOT))
    from scripts.audit_pydataxm_full_horizon import (
        cargar_cache, auditar_mensual,
    )
    serie = cargar_cache(apply_ceiling=False)
    return auditar_mensual(serie, tolerance_pct=0.15)


def test_cache_within_15pct_of_official_per_month():
    """Cada mes del horizonte debe estar dentro de tolerancia 15 % del PB_PROM oficial."""
    df = _run_audit_dataframe()
    out_of_tol = df[df["delta_pct"] > TOLERANCE_REGRESSION_PCT]
    assert out_of_tol.empty, (
        f"Meses fuera de tolerancia {TOLERANCE_REGRESSION_PCT} %:\n"
        f"{out_of_tol[['mes','cache_mean','oficial','delta_pct']].to_string(index=False)}"
    )


def test_signed_mean_delta_under_5pct():
    """El sesgo medio firmado del cache vs oficial debe ser pequeno (< 5 %)."""
    df = _run_audit_dataframe()
    bias_signed = (df["cache_mean"].sum() - df["oficial"].sum()) / df["oficial"].sum() * 100
    assert abs(bias_signed) < SIGNED_BIAS_LIMIT_PCT, (
        f"Sesgo medio firmado {bias_signed:+.2f} % fuera de [-{SIGNED_BIAS_LIMIT_PCT},"
        f" {SIGNED_BIAS_LIMIT_PCT}] %"
    )


# ─── Grupo C — Sincronia XM_MONTHLY_REAL <-> PB_OFFICIAL_PROM_MES ────────────

def test_xm_monthly_real_matches_audit_official():
    """`XM_MONTHLY_REAL` queda sincronizado con `PB_OFFICIAL_PROM_MES` del script."""
    sys.path.insert(0, str(ROOT))
    from data.xm_prices import XM_MONTHLY_REAL
    from scripts.audit_pydataxm_full_horizon import PB_OFFICIAL_PROM_MES

    for mes, (oficial, _fuente) in PB_OFFICIAL_PROM_MES.items():
        assert mes in XM_MONTHLY_REAL, (
            f"XM_MONTHLY_REAL no contiene mes {mes!r}")
        diff = abs(XM_MONTHLY_REAL[mes] - oficial)
        assert diff < 0.5, (
            f"{mes}: XM_MONTHLY_REAL={XM_MONTHLY_REAL[mes]} difiere del "
            f"oficial {oficial} en {diff:.2f} COP/kWh — desincronizado"
        )


def test_dec_2025_y_ene_2026_no_son_estimados():
    """Regresion: dic-2025 y ene-2026 ya no deben usar valores placeholder."""
    sys.path.insert(0, str(ROOT))
    from data.xm_prices import XM_MONTHLY_REAL

    # Antes de CAL-17 estos valores eran estimados (200, 220).
    # CAL-17 los actualizo a oficiales (278.83, 213.00).
    assert XM_MONTHLY_REAL["2025-12"] == pytest.approx(278.83, abs=0.5), (
        "dic-2025 sigue como estimado; CAL-17 requiere 278.83")
    assert XM_MONTHLY_REAL["2026-01"] == pytest.approx(213.00, abs=0.5), (
        "ene-2026 sigue como estimado; CAL-17 requiere 213.00")


# ─── Grupo D — Sprint 1.1b: extension cache abr-2025 + alineacion MTE ───────

def test_xm_monthly_real_incluye_abr_may_jun_2025():
    """Sprint 1.1b: XM_MONTHLY_REAL debe incluir abr/may/jun 2025."""
    sys.path.insert(0, str(ROOT))
    from data.xm_prices import XM_MONTHLY_REAL
    for mes in ["2025-04", "2025-05", "2025-06"]:
        assert mes in XM_MONTHLY_REAL, (
            f"XM_MONTHLY_REAL no contiene {mes!r} — Sprint 1.1b "
            f"extendio el cache pero el dict quedo desactualizado")


def test_cache_xm_cubre_horizonte_mte_completo():
    """Sprint 1.1b: el cache XM debe cubrir abr-2025 a ene-2026 (>=7272h)."""
    sys.path.insert(0, str(ROOT))
    cache_path = ROOT / "data" / "precios_bolsa_xm_api.csv"
    df = pd.read_csv(cache_path)
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    assert df["Fecha"].min() <= pd.Timestamp("2025-04-04"), (
        f"Cache empieza en {df['Fecha'].min()}, esperado <= 2025-04-04")
    assert df["Fecha"].max() >= pd.Timestamp("2026-01-31"), (
        f"Cache termina en {df['Fecha'].max()}, esperado >= 2026-01-31")
    assert len(df) >= 7272, (
        f"Cache tiene {len(df)} filas, esperado >= 7272 (303 dias)")


def test_get_pi_bolsa_alineacion_por_fecha():
    """Sprint 1.1b: get_pi_bolsa con t_start='2025-04-04' devuelve valores
    de abr-2025, no de jul-2025 (default antiguo)."""
    sys.path.insert(0, str(ROOT))
    from data.xm_prices import get_pi_bolsa
    pi_abr = get_pi_bolsa(
        T=24, t_start="2025-04-04", t_end="2025-04-05",
        use_api=True, apply_ceiling=False,
    )
    pi_jul = get_pi_bolsa(
        T=24, t_start="2025-07-01", t_end="2025-07-02",
        use_api=True, apply_ceiling=False,
    )
    # Las medias deben diferir notablemente: abr ~107 vs jul ~138 COP/kWh.
    assert abs(pi_abr.mean() - pi_jul.mean()) > 10.0, (
        f"pi_bolsa abr-2025 ({pi_abr.mean():.1f}) y jul-2025 "
        f"({pi_jul.mean():.1f}) deberian diferir >10 COP/kWh; "
        f"probable bug de alineacion."
    )
