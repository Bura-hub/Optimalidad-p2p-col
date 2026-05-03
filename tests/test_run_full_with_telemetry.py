"""
tests/test_run_full_with_telemetry.py — D3 telemetría wrapper
==============================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Tests del parser de stdout que emite JSONL. Usa fixtures con líneas
sintéticas para cubrir todos los patrones.

Referencia: scripts/run_full_with_telemetry.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.run_full_with_telemetry import parse_line, replay_log


TS = "2026-05-02T20:00:00"


# ─── A — patrones individuales ──────────────────────────────────────────────


def test_phase_start():
    ev = parse_line("[1/5] Cargando datos empíricos MTE...", TS)
    assert ev == {"ts": TS, "event": "phase_start",
                  "phase": 1,
                  "label": "Cargando datos empíricos MTE"}


def test_ceiling_applied():
    ev = parse_line(
        "  [creg-101-066] Techo PES aplicado: 12 horas recortadas "
        "(0.2% del horizonte), delta = 3,676 COP/kWh acumulado",
        TS,
    )
    assert ev["event"] == "ceiling_applied"
    assert ev["level"] == "PES"
    assert ev["hours_capped"] == 12
    assert ev["fraction_pct"] == 0.2
    assert ev["delta_cop_kwh_total"] == 3676


def test_cal16_decomposition():
    ev = parse_line(
        "    [CAL-16] C2 descompuesto: savings = G + Cvm + α·COT − MEM | "
        "G≈300.0 Cvm≈175.0 α·COT≈40.0 (α=1.0) MEM≈16.0 → pi_upper≈499.0 COP/kWh.",
        TS,
    )
    assert ev["event"] == "cal16_decomposition"
    assert ev["g_mean"] == 300.0
    assert ev["pi_upper"] == 499.0


def test_monthly_metric():
    ev = parse_line(
        "  Abr 2025       5,367,656     5,490,651     5,036,248     5,319,582    "
        "0.3162    68.0    32.0     682.43",
        TS,
    )
    assert ev["event"] == "monthly_metric"
    assert ev["mes"] == "Abr 2025"
    assert ev["P2P"] == 5367656
    assert ev["IE_P2P"] == pytest.approx(0.3162)
    assert ev["kWh_P2P"] == pytest.approx(682.43)


def test_p2p_summary():
    ev = parse_line(
        "    73.6s | horas mercado: 1031/6144 | 3659.31 kWh P2P", TS,
    )
    assert ev["event"] == "p2p_summary"
    assert ev["horas_activas"] == 1031
    assert ev["horas_total"] == 6144
    assert ev["kwh_p2p_total"] == pytest.approx(3659.31)


def test_completion():
    ev = parse_line("✓ Completado en 225.3s.", TS)
    assert ev["event"] == "completion"
    assert ev["elapsed_s"] == pytest.approx(225.3)


def test_traceback_se_marca_como_error():
    ev = parse_line("Traceback (most recent call last):", TS)
    assert ev["event"] == "error"


def test_linea_irrelevante_devuelve_none():
    assert parse_line("texto cualquiera sin patron", TS) is None


# ─── B — replay_log sobre fixture sintética ────────────────────────────────


def test_replay_log_sobre_fixture(tmp_path):
    log = tmp_path / "fake.log"
    log.write_text(
        "[1/5] Cargando datos empíricos MTE...\n"
        "  [creg-101-066] Techo PES aplicado: 12 horas recortadas "
        "(0.2% del horizonte), delta = 3,676 COP/kWh acumulado\n"
        "[2/5] EMS P2P (RD + Stackelberg)...\n"
        "    horas mercado: 1031/6144 | 3659.31 kWh P2P\n"
        "  Abr 2025       5,367,656     5,490,651     5,036,248     5,319,582"
        "    0.3162    68.0    32.0     682.43\n"
        "✓ Completado en 225.3s.\n",
        encoding="utf-8",
    )
    out = tmp_path / "telemetry.jsonl"
    code = replay_log(log, out)
    assert code == 0
    events = [json.loads(ln) for ln in out.read_text(encoding="utf-8").splitlines()]
    types = [e["event"] for e in events]
    assert "phase_start" in types
    assert "ceiling_applied" in types
    assert "p2p_summary" in types
    assert "monthly_metric" in types
    assert "completion" in types


# ─── C — script CLI smoke ───────────────────────────────────────────────────


def test_script_dry_run_sobre_log_real_existente():
    """Smoke: parsea un log real del repo si existe."""
    log_dir = ROOT / "outputs"
    candidatos = sorted(log_dir.glob("run_*.log"))
    if not candidatos:
        pytest.skip("Sin logs reales para smoke")
    log = candidatos[-1]  # mas reciente

    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_full_with_telemetry.py"),
         "--dry-run", str(log), "--tag", "smoke-test"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert res.returncode == 0
    assert "Eventos" in res.stdout
