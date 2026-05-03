"""
tests/test_ruflo_snapshot_run.py — A4 Snapshot wrapper
========================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Tests del wrapper que captura metricas de outputs/resultados_comparacion.xlsx
y las almacena en Ruflo namespace 'runs'. Usa fixtures con xlsx
sintetico para no depender de un run real.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.ruflo_snapshot_run import (
    extract_run_metrics, build_snapshot_text, get_active_cals, _gini,
)


def _build_fake_xlsx(tmp_path: Path) -> Path:
    """Construye un xlsx con la estructura mínima de resultados_comparacion."""
    p = tmp_path / "fake.xlsx"
    with pd.ExcelWriter(p, engine="openpyxl") as w:
        pd.DataFrame({
            "Escenario": ["P2P", "C1", "C2", "C3", "C4"],
            "Ganancia_neta_COP": [50e6, 49e6, 48e6, 47e6, 50e6],
            "SC": [0.18, 0.17, 0.17, 0.17, 0.17],
            "SS": [0.98, 0.92, 0.92, 0.92, 0.92],
            "IE": [0.36, 0.01, 0.02, 0.04, 0.06],
        }).to_excel(w, sheet_name="Resumen", index=False)

        pd.DataFrame({
            "Agente": ["A1", "A2", "A3", "A4", "A5"],
            "P2P": [10e6, 11e6, 12e6, 9e6, 8e6],
            "C1": [9e6, 11e6, 12e6, 9e6, 8e6],
            "C2": [9e6, 11e6, 11e6, 9e6, 8e6],
            "C3": [8e6, 11e6, 11e6, 9e6, 8e6],
            "C4": [10e6, 11e6, 12e6, 9e6, 8e6],
        }).to_excel(w, sheet_name="Por_agente", index=False)

        T = 100
        rng = np.random.default_rng(0)
        kwh = np.zeros(T)
        kwh[10:50] = rng.uniform(0.5, 5.0, 40)
        pd.DataFrame({
            "Hora": np.arange(1, T + 1),
            "kWh_P2P": kwh,
            "SC": rng.uniform(0.1, 0.3, T),
            "SS": rng.uniform(0.7, 0.9, T),
            "IE": rng.uniform(-0.1, 0.4, T),
            "PS_%": rng.uniform(0, 100, T),
            "PSR_%": rng.uniform(0, 100, T),
            "Wj": rng.uniform(0, 1000, T),
            "Wi": rng.uniform(0, 1000, T),
        }).to_excel(w, sheet_name="P2P_horario", index=False)
    return p


# ─── A — extract_run_metrics ────────────────────────────────────────────────


def test_extract_devuelve_net_benefit_por_escenario(tmp_path):
    xlsx = _build_fake_xlsx(tmp_path)
    metrics = extract_run_metrics(xlsx)
    for esc in ("P2P", "C1", "C2", "C3", "C4"):
        assert f"net_benefit_{esc}" in metrics
    assert metrics["net_benefit_P2P"] == pytest.approx(50e6)


def test_extract_devuelve_indices_SC_SS_IE(tmp_path):
    xlsx = _build_fake_xlsx(tmp_path)
    metrics = extract_run_metrics(xlsx)
    assert metrics["IE_P2P"] == pytest.approx(0.36)
    assert metrics["SC_P2P"] == pytest.approx(0.18)


def test_extract_devuelve_kwh_p2p_total_y_horas(tmp_path):
    xlsx = _build_fake_xlsx(tmp_path)
    metrics = extract_run_metrics(xlsx)
    assert metrics["horas_total"] == 100
    assert metrics["horas_p2p_activas"] == 40
    assert metrics["kWh_P2P_total"] > 0


def test_extract_devuelve_gini_por_escenario(tmp_path):
    xlsx = _build_fake_xlsx(tmp_path)
    metrics = extract_run_metrics(xlsx)
    for esc in ("P2P", "C1", "C2", "C3", "C4"):
        assert f"gini_{esc}" in metrics
        assert 0.0 <= metrics[f"gini_{esc}"] <= 1.0


# ─── B — build_snapshot_text ────────────────────────────────────────────────


def test_snapshot_text_incluye_cals_y_rpe():
    metrics = {
        "net_benefit_P2P": 100,
        "net_benefit_C1":   90,
        "net_benefit_C4":   95,
        "IE_P2P": 0.3,
        "kWh_P2P_total": 100,
    }
    txt = build_snapshot_text(metrics, [1, 2, 3], "2026-05-02 12:00",
                                tag="test")
    assert "tag=test" in txt
    assert "CALs activos" in txt
    assert "RPE_P2P_vs_C1" in txt
    assert "RPE_P2P_vs_C4" in txt
    assert "actividad" in txt


def test_snapshot_text_no_revienta_sin_cals():
    txt = build_snapshot_text({"net_benefit_P2P": 1.0}, [], "2026-05-02 00:00")
    assert "Snapshot run 2026-05-02 00:00" in txt


# ─── C — get_active_cals lee README ─────────────────────────────────────────


def test_get_active_cals_repo_real():
    cals = get_active_cals()
    # Hay al menos 20 CALs Accepted al cierre de Sprint 4.
    assert len(cals) >= 20
    assert min(cals) == 1


# ─── D — script CLI smoke ───────────────────────────────────────────────────


def test_script_dry_run_xlsx_no_existe(tmp_path):
    """Script con --xlsx ausente debe fallar limpio (exit 1)."""
    res = subprocess.run(
        [sys.executable,
         str(ROOT / "scripts" / "ruflo_snapshot_run.py"),
         "--xlsx", str(tmp_path / "no_existe.xlsx"),
         "--dry-run"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert res.returncode == 1


def test_script_dry_run_con_xlsx_sintetico(tmp_path):
    xlsx = _build_fake_xlsx(tmp_path)
    res = subprocess.run(
        [sys.executable,
         str(ROOT / "scripts" / "ruflo_snapshot_run.py"),
         "--xlsx", str(xlsx),
         "--tag", "test",
         "--dry-run"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert res.returncode == 0
    assert "Snapshot key: run-test" in res.stdout
