"""
tests/test_check_scenario_duplication.py — F1 detector duplicación
====================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Tests del detector de duplicación entre escenarios. Usa fixtures con
funciones controladas para verificar que el detector flagea código
casi-idéntico y NO flagea funciones distintas.

Referencia: scripts/check_scenario_duplication.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.check_scenario_duplication import (
    extract_functions, normalize_ast, similarity, pairwise_compare,
)


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


# ─── A — extract_functions ──────────────────────────────────────────────────


def test_extract_skips_short_functions(tmp_path):
    """Funciones < 10 líneas se ignoran."""
    p = tmp_path / "x.py"
    _write(p, "def short():\n    return 1\n\n"
              "def long_one():\n" + "\n".join([f"    x{i} = {i}"
                                                 for i in range(15)]) + "\n")
    funcs = extract_functions(p)
    names = [f[0] for f in funcs]
    assert "short" not in names
    assert "long_one" in names


def test_extract_strips_docstrings(tmp_path):
    """Docstrings no afectan la normalización."""
    p1 = tmp_path / "x.py"
    p2 = tmp_path / "y.py"
    body = "\n".join([f"    a{i} = {i}" for i in range(15)])
    _write(p1, f'def foo():\n    """docstring 1"""\n{body}\n')
    _write(p2, f'def foo():\n    """docstring TOTALMENTE distinto"""\n{body}\n')
    f1 = extract_functions(p1)[0]
    f2 = extract_functions(p2)[0]
    assert similarity(f1[1], f2[1]) > 0.99


# ─── B — similarity behavior ────────────────────────────────────────────────


def test_similarity_idempotente():
    code = "def f():\n    return 1"
    assert similarity(code, code) == 1.0


def test_similarity_distinto_es_baja():
    a = "def f():\n    return 1"
    b = "def g():\n    print('hello world')"
    assert similarity(a, b) < 0.95


# ─── C — pairwise_compare detecta clones ────────────────────────────────────


def test_pairwise_detecta_funciones_casi_identicas(tmp_path):
    """Dos funciones que solo difieren en nombres de variable → flag."""
    body_a = "\n".join([
        "    pi_gs_v = pi_gs",
        "    revenues = 0",
        "    for k in range(T):",
        "        for n in prosumer_ids:",
        "            gen = max(0.0, G[n, k])",
        "            dem = max(0.0, D[n, k])",
        "            auto = min(gen, dem)",
        "            revenues += auto * pi_gs_v[n, k]",
        "            surplus = gen - auto",
        "            revenues += surplus * pi_bolsa[k]",
        "    return revenues",
    ])
    body_b = body_a.replace("pi_gs_v", "tariff").replace("revenues", "income")
    p1 = tmp_path / "scenario_c3_spot.py"
    p2 = tmp_path / "scenario_c5_clone.py"
    _write(p1, f"def run_c3_spot(D, G, pi_gs, pi_bolsa, prosumer_ids, T):\n{body_a}\n")
    _write(p2, f"def run_c5_clone(D, G, pi_gs, pi_bolsa, prosumer_ids, T):\n{body_b}\n")

    funcs = []
    for p in [p1, p2]:
        for name, code, lineno in extract_functions(p):
            funcs.append((p.relative_to(tmp_path), name, code, lineno))
    pairs = pairwise_compare(funcs, threshold=0.85)
    assert len(pairs) >= 1
    assert pairs[0]["similarity"] > 0.85


def test_pairwise_no_flagea_funciones_estructuralmente_distintas(tmp_path):
    """Funciones con estructura claramente distinta (loop vs llamadas)
    no aparecen al threshold default."""
    body_a = "\n".join([f"    x{i} = {i} * 2" for i in range(15)])
    body_b = (
        "    if x > 0:\n"
        "        result = []\n"
        "        for i in range(10):\n"
        "            if i % 2 == 0:\n"
        "                result.append(i)\n"
        "            else:\n"
        "                result.append(-i)\n"
        "        return sum(result)\n"
        "    else:\n"
        "        return -1\n"
    )
    p1 = tmp_path / "a.py"
    p2 = tmp_path / "b.py"
    _write(p1, f"def f_a(x):\n{body_a}\n    return 0\n")
    _write(p2, f"def f_b(x):\n{body_b}")
    funcs = []
    for p in [p1, p2]:
        for name, code, lineno in extract_functions(p):
            funcs.append((p.relative_to(tmp_path), name, code, lineno))
    pairs = pairwise_compare(funcs, threshold=0.85)
    assert pairs == [], (
        f"falso positivo: estructura distinta no deberia exceder 0.85: "
        f"{pairs}"
    )


# ─── D — script CLI smoke ───────────────────────────────────────────────────


def test_script_corre_sobre_repo_real():
    """Smoke: el detector corre sobre scenarios/ del repo real."""
    res = subprocess.run(
        [sys.executable, "scripts/check_scenario_duplication.py",
         "--threshold", "0.85"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
    )
    assert res.returncode == 0
    assert "F1" in res.stdout


def test_strict_mode_propaga_exit_code(tmp_path):
    """strict=True con clones detectados → exit 1."""
    body = "\n".join([f"    x{i} = {i}" for i in range(15)])
    p1 = tmp_path / "scenarios" / "scenario_c1.py"
    p2 = tmp_path / "scenarios" / "scenario_c2.py"
    _write(p1, f"def run_c1(D):\n{body}\n    return 0\n")
    _write(p2, f"def run_c2(D):\n{body}\n    return 0\n")

    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_scenario_duplication.py"),
         "--root", str(tmp_path),
         "--pattern", "scenarios/scenario_c*.py",
         "--threshold", "0.85", "--strict"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert res.returncode == 1
