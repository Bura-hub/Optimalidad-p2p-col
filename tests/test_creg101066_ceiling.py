"""
tests/test_creg101066_ceiling.py — CAL-14: Techo CREG 101 066/2024 PES
=======================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 3.x

Verifica el cargador de la tabla mensual PEI/PE/PES y la aplicacion del
techo regulatorio al precio de bolsa horario.

Referencia: docs/superpowers/specs/2026-05-01-cal14-creg101066-pes-ceiling.md
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from data.xm_prices import (
    load_creg_ceiling,
    apply_creg101066_ceiling,
    get_pi_bolsa,
)


# ─── Grupo A — load_creg_ceiling ──────────────────────────────────────────────

def test_load_csv_returns_series_indexed_by_month():
    """load_creg_ceiling devuelve serie pandas con index Period[M]."""
    s = load_creg_ceiling("2025-07-01", "2026-02-01", level="PES")
    assert isinstance(s, pd.Series)
    assert len(s) == 7
    # Valor exacto del Excel XM para sep-2025
    assert s.loc[pd.Period("2025-09", freq="M")] == pytest.approx(893.85)
    assert s.loc[pd.Period("2025-07", freq="M")] == pytest.approx(865.22)
    assert s.loc[pd.Period("2026-01", freq="M")] == pytest.approx(830.34)


def test_load_csv_supports_pei_pe_pes_levels():
    """Los tres niveles PEI/PE/PES son seleccionables."""
    s_pes = load_creg_ceiling("2025-07-01", "2026-02-01", level="PES")
    s_pe  = load_creg_ceiling("2025-07-01", "2026-02-01", level="PE")
    s_pei = load_creg_ceiling("2025-07-01", "2026-02-01", level="PEI")
    # Orden canonico: PEI < PE < PES en cualquier mes
    assert (s_pei < s_pe).all()
    assert (s_pe  < s_pes).all()


def test_load_csv_raises_when_file_missing(tmp_path):
    """Falla explicita cuando el CSV no existe (no caer en silencio)."""
    fake_path = tmp_path / "no_existe.csv"
    with pytest.raises(FileNotFoundError, match="Falta"):
        load_creg_ceiling("2025-07-01", "2026-02-01",
                          level="PES", csv_path=str(fake_path))


def test_load_csv_raises_on_invalid_level():
    """level fuera de {PEI, PE, PES} lanza ValueError."""
    with pytest.raises(ValueError, match="level debe ser"):
        load_creg_ceiling("2025-07-01", "2026-02-01", level="WRONG")


def test_load_csv_handles_empty_cell_with_interpolation(tmp_path):
    """Mes con celda vacia se interpola linealmente entre adyacentes."""
    csv = tmp_path / "test_ceiling.csv"
    csv.write_text(
        "mes,pei_cop_kwh,pe_cop_kwh,pes_cop_kwh,fuente,nota\n"
        "2025-07,350.0,700.0,800.0,test,jul\n"
        "2025-08,,,,test,gap\n"
        "2025-09,360.0,720.0,820.0,test,sep\n"
    )
    s = load_creg_ceiling("2025-07-01", "2025-10-01",
                          level="PES", csv_path=str(csv))
    # Interpolacion lineal: ago deberia ser (800 + 820) / 2 = 810
    assert s.loc[pd.Period("2025-08", freq="M")] == pytest.approx(810.0)


# ─── Grupo B — apply_creg101066_ceiling ──────────────────────────────────────

def test_ceiling_caps_values_above_PES():
    """Valores > PES del mes se recortan a PES exacto."""
    # 24 horas del 2025-07-01 (PES jul = 865.22)
    pi = np.array([100.0, 1500.0, 200.0, 2000.0] + [100.0] * 20)
    capped = apply_creg101066_ceiling(pi, "2025-07-01", level="PES")
    assert capped.max() == pytest.approx(865.22)
    # Valores no afectados quedan iguales
    assert capped[0] == 100.0
    assert capped[2] == 200.0


def test_ceiling_does_not_modify_values_below_PES():
    """Si todos los valores estan bajo PES, la serie no se modifica."""
    pi = np.array([100.0, 200.0, 300.0, 400.0] + [500.0] * 20)
    capped = apply_creg101066_ceiling(pi, "2025-07-01", level="PES")
    assert np.allclose(capped, pi)
