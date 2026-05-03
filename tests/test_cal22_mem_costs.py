"""
tests/test_cal22_mem_costs.py — CAL-22 Validación de mem_costs_no_regulado.csv
==============================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 3.1-3.3

Verifica:
  1. Schema del CSV (columnas, tipos, sin NaN).
  2. Cobertura completa abr-2025 a abr-2026 (13 meses).
  3. Rangos de los componentes (FAZNI, contrib, comisión).
  4. Coherencia: el helper `mem_costs_per_agent_hourly` produce
     valores en rango razonable (~10-20 COP/kWh).

Referencia: docs/adr/0022-cal22-mem-costs-validacion.md
            data/mem_costs_audit.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CSV_PATH = ROOT / "data" / "mem_costs_no_regulado.csv"

REQUIRED_COLS = {
    "mes", "fazni_cop_kwh", "contrib_4pct_de",
    "comision_representante_cop_kwh", "fuente",
}

EXPECTED_MONTHS = [
    f"2025-{m:02d}" for m in range(4, 13)
] + [f"2026-{m:02d}" for m in range(1, 5)]

# Bandas razonables (CAL-22): si UPME / ASOCODIS publican valores fuera de
# estas, hay que actualizar el CSV y este test.
FAZNI_MIN, FAZNI_MAX = 1.0, 3.0
COMISION_MIN, COMISION_MAX = 0.5, 5.0


# ─── Grupo A — Schema ───────────────────────────────────────────────────────


def test_csv_existe():
    assert CSV_PATH.exists(), f"Falta {CSV_PATH}"


def test_csv_tiene_columnas_requeridas():
    df = pd.read_csv(CSV_PATH)
    missing = REQUIRED_COLS - set(df.columns)
    assert not missing, f"Faltan columnas: {missing}"


def test_csv_tiene_13_filas():
    df = pd.read_csv(CSV_PATH)
    assert len(df) == 13, (
        f"Esperan 13 filas (abr-2025 a abr-2026), hay {len(df)}"
    )


def test_csv_no_tiene_nan_en_columnas_clave():
    df = pd.read_csv(CSV_PATH)
    for col in ["fazni_cop_kwh", "comision_representante_cop_kwh",
                "contrib_4pct_de"]:
        n_nan = df[col].isna().sum()
        assert n_nan == 0, f"{col} tiene {n_nan} NaN"


# ─── Grupo B — Cobertura horizonte ─────────────────────────────────────────


def test_meses_cubren_horizonte():
    df = pd.read_csv(CSV_PATH)
    meses = df["mes"].astype(str).tolist()
    for m in EXPECTED_MONTHS:
        assert m in meses, f"Falta mes {m} en CSV"


def test_no_hay_meses_duplicados():
    df = pd.read_csv(CSV_PATH)
    assert df["mes"].duplicated().sum() == 0


# ─── Grupo C — Rangos de los componentes ────────────────────────────────────


def test_fazni_en_rango_razonable():
    df = pd.read_csv(CSV_PATH)
    fazni = df["fazni_cop_kwh"].astype(float)
    assert (fazni >= FAZNI_MIN).all() and (fazni <= FAZNI_MAX).all(), (
        f"FAZNI fuera de rango [{FAZNI_MIN}, {FAZNI_MAX}]: "
        f"{fazni.tolist()}"
    )


def test_comision_representante_en_rango_razonable():
    df = pd.read_csv(CSV_PATH)
    com = df["comision_representante_cop_kwh"].astype(float)
    assert (com >= COMISION_MIN).all() and (com <= COMISION_MAX).all(), (
        f"Comisión fuera de rango [{COMISION_MIN}, {COMISION_MAX}]: "
        f"{com.tolist()}"
    )


def test_contrib_4pct_es_literal_Gm_o_numerico():
    df = pd.read_csv(CSV_PATH)
    contrib = df["contrib_4pct_de"].astype(str)
    valid = contrib.isin(["Gm", "0.04*Gm", "G_mensual"]) | (
        contrib.str.contains(r"^[0-9.]+$", regex=True)
    )
    assert valid.all(), (
        f"contrib_4pct_de debe ser 'Gm' o numerico, valores: "
        f"{contrib.unique().tolist()}"
    )


# ─── Grupo D — Trazabilidad fuente ──────────────────────────────────────────


def test_columna_fuente_menciona_leyes_clave():
    df = pd.read_csv(CSV_PATH)
    # Cada fila debe mencionar al menos una de las leyes/resoluciones
    # documentadas en el ADR.
    fuente = df["fuente"].astype(str)
    keywords = ["Ley 1715", "Ley 1117", "Ley 2099", "CREG 156"]
    for idx, txt in enumerate(fuente):
        hit = any(kw in txt for kw in keywords)
        assert hit, (
            f"Fila {idx} ({df['mes'].iloc[idx]}) no cita ninguna de "
            f"{keywords}: {txt!r}"
        )


# ─── Grupo E — Coherencia con el helper ─────────────────────────────────────


def test_helper_produce_valores_en_rango_razonable():
    """`mem_costs_per_agent_hourly` debe entregar 10-25 COP/kWh sobre datos reales."""
    from data.cedenar_tariff import mem_costs_per_agent_hourly
    idx = pd.date_range("2025-08-01", "2025-08-08", freq="1h",
                         inclusive="left")
    agents = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
    M = mem_costs_per_agent_hourly(agents, idx)
    assert M.shape == (5, len(idx))
    assert np.isfinite(M).all()
    # FAZNI 1.9 + 0.04*~300 + 2.0 ~= 15.9 COP/kWh; banda generosa [5, 30].
    assert M.mean() > 5.0 and M.mean() < 30.0, (
        f"MEM helper mean={M.mean():.2f} COP/kWh fuera de [5, 30]"
    )
