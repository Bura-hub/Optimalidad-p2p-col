"""
test_cli_flags.py — Validación de combinaciones de flags CLI (CAL-39).

Antes, las combinaciones inválidas se ignoraban en silencio (--gsa
descartaba --full/--analysis/--include-c5/--paper-meters; --day pisaba
--full) y el prompt input() del GSA con n>=256 reventaba bajo nohup.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "main_simulation.py")


def _run(*flags):
    return subprocess.run([sys.executable, MAIN, *flags],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=ROOT, timeout=60)


def test_gsa_incompatible_con_full():
    res = _run("--gsa", "--full")
    assert res.returncode != 0
    assert "incompatible" in (res.stderr or "")


def test_gsa_incompatible_con_include_c5():
    res = _run("--gsa", "--include-c5")
    assert res.returncode != 0


def test_gsa_incompatible_con_paper_meters():
    res = _run("--gsa", "--paper-meters")
    assert res.returncode != 0


def test_day_y_full_exclusivos():
    res = _run("--day", "2025-08-06", "--full")
    assert res.returncode != 0
    assert "exclusivos" in (res.stderr or "")


def test_help_no_revienta():
    res = _run("--help")
    assert res.returncode == 0
    assert "--include-c5" in res.stdout
