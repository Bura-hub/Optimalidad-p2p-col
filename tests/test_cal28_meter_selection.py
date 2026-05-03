"""
tests/test_cal28_meter_selection.py — CAL-28 selección medidor puntual
=========================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 4.1 + 4.2

Verifica:
  1. data/paper_meter_config.csv tiene 5 instituciones + columnas requeridas.
  2. _read_meter_csvs localiza tz-aware y resamplea a horario.
  3. cargar_mte_paper produce D, G, idx con shapes correctos.
  4. Cobertura G/D resultante > 50% (vs ~19% con M1 totalizador).
  5. --no-paper-meters revierte al M1 totalizador (status quo tesis).

Referencia: docs/adr/0028-cal28-paper-medidor-puntual.md
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CONFIG_CSV = ROOT / "data" / "paper_meter_config.csv"


# ─── A — Configuración CSV ────────────────────────────────────────────────


def test_config_csv_existe():
    assert CONFIG_CSV.exists(), f"Falta {CONFIG_CSV}"


def test_config_csv_tiene_5_instituciones():
    df = pd.read_csv(CONFIG_CSV)
    insts = set(df["institucion"])
    assert insts == {"Udenar", "Mariana", "UCC", "HUDN", "Cesmag"}


def test_config_csv_columnas_requeridas():
    df = pd.read_csv(CONFIG_CSV)
    required = {"institucion", "carpeta", "medidor_nombre",
                "factor_escala", "nota"}
    assert required <= set(df.columns)


def test_mariana_tiene_factor_escala_no_uno():
    """Mariana se documenta con factor 0.3 (M3 vacío, M1 escalado)."""
    df = pd.read_csv(CONFIG_CSV).set_index("institucion")
    factor = float(df.loc["Mariana", "factor_escala"])
    assert factor == pytest.approx(0.3)


# ─── B — _read_meter_csvs ──────────────────────────────────────────────────


def test_read_meter_csvs_localiza_tz_y_resamplea():
    """La serie devuelta debe ser horaria, tz-aware, no vacía."""
    from scripts.run_paper_iter import _read_meter_csvs

    mte_root = Path(os.environ.get("MTE_ROOT",
                                     str(ROOT / "MedicionesMTE_v3")))
    if not mte_root.is_dir():
        pytest.skip("MedicionesMTE_v3 no disponible")

    meter_dir = (mte_root / "UCC" / "electricMeter"
                  / "Medidor 3 - UCC - electricMeter")
    if not meter_dir.is_dir():
        pytest.skip(f"Sin medidor UCC M3 en {meter_dir}")

    s = _read_meter_csvs(meter_dir)
    assert str(s.index.tz) == "America/Bogota", (
        f"Serie no localizada: tz={s.index.tz}"
    )
    # Frecuencia horaria: dos puntos consecutivos a 1h de distancia
    delta = s.dropna().index.to_series().diff().dropna().min()
    assert delta == pd.Timedelta("1h")
    assert s.dropna().mean() > 0.5  # demanda real, no ruido


# ─── C — cargar_mte_paper ──────────────────────────────────────────────────


def test_cargar_mte_paper_shapes_correctos():
    from scripts.run_paper_iter import cargar_mte_paper

    mte_root = Path(os.environ.get("MTE_ROOT",
                                     str(ROOT / "MedicionesMTE_v3")))
    if not mte_root.is_dir():
        pytest.skip("MedicionesMTE_v3 no disponible")

    D, G, idx, agents = cargar_mte_paper("2025-08-01", "2025-09-01")
    assert D.shape == (5, len(idx))
    assert G.shape == (5, len(idx))
    assert len(agents) == 5
    assert agents == ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]


def test_cargar_mte_paper_cobertura_alta():
    """G/D agregada debe ser >50% (vs ~19% con M1 totalizador)."""
    from scripts.run_paper_iter import cargar_mte_paper

    mte_root = Path(os.environ.get("MTE_ROOT",
                                     str(ROOT / "MedicionesMTE_v3")))
    if not mte_root.is_dir():
        pytest.skip("MedicionesMTE_v3 no disponible")

    D, G, _idx, _agents = cargar_mte_paper("2025-08-01", "2025-09-01")
    cobertura = float(G.sum()) / max(float(D.sum()), 1e-9)
    assert cobertura > 0.5, (
        f"CAL-28 esperaba cobertura >50%, obtuvo {cobertura*100:.1f}%"
    )
    assert cobertura < 2.0, (
        f"Cobertura {cobertura*100:.1f}% sospechosa (>200%); "
        f"verifica timezone y reindex"
    )


def test_cargar_mte_paper_d_no_negativa():
    """Demandas siempre >=0 tras clip."""
    from scripts.run_paper_iter import cargar_mte_paper

    mte_root = Path(os.environ.get("MTE_ROOT",
                                     str(ROOT / "MedicionesMTE_v3")))
    if not mte_root.is_dir():
        pytest.skip("MedicionesMTE_v3 no disponible")

    D, _G, _idx, _agents = cargar_mte_paper("2025-08-01", "2025-09-01")
    assert (D >= 0).all()


# ─── D — Smoke CLI ──────────────────────────────────────────────────────────


def test_no_paper_meters_revierte_a_totalizador(tmp_path):
    """--no-paper-meters debe usar M1 totalizador (cobertura ~19%)."""
    mte_root = ROOT / "MedicionesMTE_v3"
    if not mte_root.is_dir():
        pytest.skip("MedicionesMTE_v3 no disponible")

    out_dir = tmp_path / "paper"
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_paper_iter.py"),
         "--month", "2025-08", "--tag", "no_cal28",
         "--out-dir", str(out_dir),
         "--no-paper-meters"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
        timeout=180,
    )
    assert res.returncode == 0
    assert "DESACTIVADO" in res.stdout
    # Cobertura con M1 debería estar en torno a 19-25%.
    # No es estricto, solo verificar que no usa CAL-28.
    assert "Cargando medidores puntuales" not in res.stdout
