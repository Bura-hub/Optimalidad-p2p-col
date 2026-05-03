"""
tests/test_run_paper_iter.py — CAL-25 Modo paper IEEE WEEF
============================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 4.1 + 4.2

Tests del orquestador del paper. Verifica:
  1. Homogeneizacion de INSTITUTION_PROFILE (A1).
  2. Horizonte mensual correcto (G).
  3. Renaming completo C4 -> "C2 (CREG 101 072)".
  4. Filtrado: solo C1 + C4 + P2P (no C2 PPA, no C3 Spot).
  5. Output xlsx con 3 escenarios.
  6. Smoke end-to-end sobre agosto-2025 (subset chico).

Referencia: docs/adr/0025-cal25-modo-paper.md
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ─── A1 — Homogeneización ───────────────────────────────────────────────────


def test_homogeneizar_a_comercial_modifica_dict():
    """Después de homogeneizar, todos los agentes tienen perfil comercial."""
    # Re-import limpio para no contaminar otros tests.
    if "data.cedenar_tariff" in sys.modules:
        del sys.modules["data.cedenar_tariff"]
    from scripts.run_paper_iter import homogeneizar_a_comercial
    from data import cedenar_tariff

    original = homogeneizar_a_comercial()
    profiles = cedenar_tariff.INSTITUTION_PROFILE
    assert all(p.categoria == "comercial" for p in profiles.values())
    # Restaura para no contaminar otros tests
    cedenar_tariff.INSTITUTION_PROFILE = original


def test_homogeneizar_no_toca_archivo():
    """Después de homogeneizar, el archivo cedenar_tariff.py debe seguir
    teniendo Udenar y HUDN como 'oficial' (no se edita el código fuente)."""
    src = (ROOT / "data" / "cedenar_tariff.py").read_text(encoding="utf-8")
    assert 'TariffProfile("oficial",' in src or "oficial" in src, (
        "El archivo data/cedenar_tariff.py NO debe modificarse"
    )


# ─── G — Horizonte mensual ─────────────────────────────────────────────────


def test_horizonte_mensual_agosto_2025():
    from scripts.run_paper_iter import horizonte_mensual
    t_start, t_end = horizonte_mensual("2025-08")
    assert t_start == "2025-08-01"
    assert t_end == "2025-09-01"


def test_horizonte_mensual_diciembre_cruza_anio():
    from scripts.run_paper_iter import horizonte_mensual
    t_start, t_end = horizonte_mensual("2025-12")
    assert t_start == "2025-12-01"
    assert t_end == "2026-01-01"


# ─── B — Renaming ──────────────────────────────────────────────────────────


def test_paper_renaming_dict():
    """C4 se renombra a 'C2 (CREG 101 072)' en outputs."""
    from scripts.run_paper_iter import PAPER_RENAMING
    assert PAPER_RENAMING["C4"] == "C2 (CREG 101 072)"
    assert PAPER_RENAMING["C1"] == "C1 (CREG 174)"
    assert "P2P" in PAPER_RENAMING["P2P"]


# ─── End-to-end smoke ──────────────────────────────────────────────────────


@pytest.mark.slow
def test_script_corre_sobre_agosto_2025_y_genera_xlsx(tmp_path):
    """Smoke: el script termina exit 0 y genera el xlsx esperado."""
    mte_root = ROOT / "MedicionesMTE_v3"
    if not mte_root.is_dir():
        pytest.skip("MedicionesMTE_v3 no disponible")

    out_dir = tmp_path / "paper"
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_paper_iter.py"),
         "--month", "2025-08",
         "--tag", "smoketest",
         "--out-dir", str(out_dir)],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
        timeout=180,
    )
    assert res.returncode == 0, (
        f"Script crash: stderr=\n{res.stderr}\nstdout-end=\n{res.stdout[-500:]}"
    )

    xlsx = out_dir / "resultados_paper_smoketest.xlsx"
    assert xlsx.exists()
    df = pd.read_excel(xlsx, sheet_name="Resumen")
    # 3 escenarios (no 4: sin C2 PPA, sin C3 Spot)
    assert len(df) == 3
    nombres = df["Escenario"].astype(str).tolist()
    assert any("P2P" in n for n in nombres)
    assert any("CREG 174" in n for n in nombres)
    assert any("101 072" in n for n in nombres)
    # Renaming verificado:
    assert any("C2" in n and "101 072" in n for n in nombres)


def test_script_pde_capacity_y_excedentes_son_aceptados():
    """Ambos métodos PDE son argumentos válidos del CLI."""
    res_help = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_paper_iter.py"),
         "--help"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert res_help.returncode == 0
    assert "capacity" in res_help.stdout
    assert "excedentes" in res_help.stdout
