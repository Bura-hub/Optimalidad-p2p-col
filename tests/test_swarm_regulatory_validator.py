"""
tests/test_swarm_regulatory_validator.py — CAL-24 Swarm validador
=====================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0 + 4.1 + 4.2

Tests del modo `local` del validador. El modo `swarm` requiere MCP
y no se cubre con tests deterministicos.

Referencia: scripts/swarm_regulatory_validator.py
            docs/adr/0024-cal24-swarm-validador-regulatorio.md
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.swarm_regulatory_validator import (
    AgentVerdict, Check,
    validate_creg_174, validate_creg_101072, validate_creg_101066,
    aggregate_verdict, run_all_local,
)


# ─── A — agentes individuales sobre repo real ──────────────────────────────


def test_agente_creg174_pasa_sobre_repo_real():
    v = validate_creg_174()
    assert v.agent == "CREG174Validator"
    assert v.verdict in ("PASS", "PARCIAL"), (
        f"Esperado PASS/PARCIAL para C1, obtuvo {v.verdict}: {v.checks}"
    )


def test_agente_creg101072_pasa_sobre_repo_real():
    v = validate_creg_101072()
    assert v.verdict == "PASS", (
        f"Esperado PASS para C4, obtuvo {v.verdict}: {v.checks}"
    )


def test_agente_creg101066_pasa_sobre_repo_real():
    v = validate_creg_101066()
    assert v.verdict == "PASS"


# ─── B — aggregate_verdict ──────────────────────────────────────────────────


def test_aggregate_pass_si_todos_pass():
    vs = [AgentVerdict("a", "f", "C", [Check("x", True)]),
           AgentVerdict("b", "f", "C", [Check("x", True)])]
    assert aggregate_verdict(vs) == "PASS"


def test_aggregate_fail_si_algun_fail():
    vs = [
        AgentVerdict("a", "f", "C", [Check("x", True)] * 5),
        AgentVerdict("b", "f", "C",
                      [Check(f"x{i}", False) for i in range(5)]),
    ]
    assert aggregate_verdict(vs) == "FAIL"


def test_aggregate_parcial_si_mix():
    vs = [
        AgentVerdict("a", "f", "C", [Check("x", True)] * 5),
        AgentVerdict("b", "f", "C",
                      [Check("x", True)] * 4 + [Check("y", False)]),
    ]
    assert aggregate_verdict(vs) == "PARCIAL"


# ─── C — AgentVerdict.verdict ───────────────────────────────────────────────


def test_verdict_pass_con_todos_passed():
    v = AgentVerdict("a", "f", "C",
                      [Check("x", True), Check("y", True)])
    assert v.verdict == "PASS"


def test_verdict_fail_con_menos_70pct():
    v = AgentVerdict("a", "f", "C",
                      [Check("x", True)] +
                      [Check(f"y{i}", False) for i in range(3)])
    assert v.verdict == "FAIL"


def test_verdict_parcial_con_70_99pct():
    v = AgentVerdict("a", "f", "C",
                      [Check(f"y{i}", True) for i in range(7)] +
                      [Check(f"z{i}", False) for i in range(3)])
    assert v.verdict == "PARCIAL"


# ─── D — script CLI smoke ───────────────────────────────────────────────────


def test_script_local_corre_sobre_repo_real():
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "swarm_regulatory_validator.py"),
         "--mode", "local"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
    )
    assert res.returncode == 0
    assert "Veredicto agregado" in res.stdout


def test_script_json_only_emite_json_valido():
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "swarm_regulatory_validator.py"),
         "--mode", "local", "--json-only"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert "verdicts" in data
    assert "aggregate" in data
    assert len(data["verdicts"]) == 3


def test_swarm_mode_graceful_degradation():
    """--mode swarm NO debe crashear; cae a local con warning."""
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "swarm_regulatory_validator.py"),
         "--mode", "swarm"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
    )
    assert res.returncode in (0, 1)  # 0 si PASS, 1 si PARCIAL/FAIL
    assert "graceful degradation" in res.stdout or "modo local" in res.stdout
