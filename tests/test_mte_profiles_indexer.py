"""
tests/test_mte_profiles_indexer.py — A3 KG MTE indexer
========================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Tests del indexer de perfiles MTE. Verifica el pipeline en modo
dry-run (sin tocar Ruflo) y la composicion del texto semantico.

Referencia: scripts/ruflo_index_mte_profiles.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.ruflo_index_mte_profiles import (
    calcular_perfil, perfil_a_texto_semantico, INVERTER_INFO,
)


def _profile_stub(categoria="oficial", nivel_tension=2,
                   propiedad="cedenar"):
    class _P:
        pass
    p = _P()
    p.categoria = categoria
    p.nivel_tension = nivel_tension
    p.propiedad = propiedad
    return p


# ─── A — calcular_perfil ────────────────────────────────────────────────────


def test_perfil_basico_correcto():
    """Perfil aritmetico correcto sobre matrices D y G dadas."""
    D = np.array([[10.0, 8.0, 6.0]])  # T=3
    G = np.array([[3.0, 0.0, 5.0]])
    profile = _profile_stub()
    p = calcular_perfil("Udenar", 0, D, G, profile, "2025-04-04",
                         "2025-12-16")
    assert p["name"] == "Udenar"
    assert p["categoria"] == "oficial"
    assert p["D_total_kWh"] == pytest.approx(24.0)
    assert p["G_total_kWh"] == pytest.approx(8.0)
    assert p["cobertura_PV_total"] == pytest.approx(8.0 / 24.0, abs=1e-4)
    assert p["horas_con_G_pos"] == 2  # 3.0 y 5.0 son > 0


def test_perfil_inverter_info_correcto():
    """Cesmag debe mapearse a su inversor real."""
    D = np.ones((1, 5))
    G = np.ones((1, 5))
    profile = _profile_stub("comercial")
    p = calcular_perfil("Cesmag", 0, D, G, profile,
                         "2025-04-04", "2025-12-16")
    inv, meter, mode = INVERTER_INFO["Cesmag"]
    assert p["inverter"] == inv
    assert p["meter"] == meter
    assert p["metering_mode"] == mode


# ─── B — perfil_a_texto_semantico ───────────────────────────────────────────


def test_texto_semantico_contiene_clave_principal():
    """El texto debe mencionar nombre, NT, inversor, cobertura PV."""
    p = {
        "name": "Udenar", "categoria": "oficial", "nivel_tension": 2,
        "propiedad": "cedenar", "inverter": "Fronius",
        "meter": "M1", "metering_mode": "NET METER",
        "D_mean_kW": 7.2, "D_max_kW": 33.0, "D_total_kWh": 44310.0,
        "G_mean_kW": 2.15, "G_max_kW": 13.9, "G_total_kWh": 13219.0,
        "cobertura_PV_total": 0.298, "horas_con_G_pos": 3232,
        "horas_total": 6144,
        "horizonte": "2025-04-04 a 2025-12-16",
    }
    txt = perfil_a_texto_semantico(p)
    assert "Udenar" in txt
    assert "NT2" in txt
    assert "Fronius" in txt
    assert "29.8%" in txt
    assert "Actividad" in txt


# ─── C — script CLI smoke ───────────────────────────────────────────────────


def test_script_dry_run_corre_sobre_repo_real():
    """Smoke: --dry-run no toca Ruflo y reporta los 5 perfiles."""
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ruflo_index_mte_profiles.py"),
         "--dry-run"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
    )
    assert res.returncode == 0
    out = res.stdout
    assert "Udenar" in out
    assert "Cesmag" in out
    assert "dry-run" in out
