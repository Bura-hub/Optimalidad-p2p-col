"""
tests/test_creg101066_ceiling.py — CAL-14: Techo CREG 101 066/2024 PES
=======================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 3.x

Verifica el cargador de la tabla mensual PEI/PE/PES y la aplicacion del
techo regulatorio al precio de bolsa horario.

Referencia: especificacion de diseno interna (CAL-14, techo PES CREG 101 066).
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


def test_ceiling_uses_correct_month_for_each_hour():
    """Cada hora se compara con el techo del mes al que pertenece."""
    # 31 dias de jul (24*31 = 744 h) + 24 horas de ago.
    # Todas las horas con valor 1000 — superan ambos techos.
    T = 24 * 31 + 24
    pi = np.full(T, 1000.0)
    capped = apply_creg101066_ceiling(pi, "2025-07-01", level="PES")
    # Hora 0 (jul-01 00:00) debe topar a PES jul = 865.22
    assert capped[0] == pytest.approx(865.22)
    # Hora 743 (jul-31 23:00) sigue en jul
    assert capped[743] == pytest.approx(865.22)
    # Hora 744 (ago-01 00:00) debe topar a PES ago = 898.02
    assert capped[744] == pytest.approx(898.02)
    # Ultima hora (ago-01 23:00) tambien ago
    assert capped[-1] == pytest.approx(898.02)


def test_ceiling_skips_hours_before_effective_date():
    """Horas anteriores a effective_date no se recortan."""
    import tempfile
    csv_content = (
        "mes,pei_cop_kwh,pe_cop_kwh,pes_cop_kwh,fuente,nota\n"
        "2024-11,300.0,600.0,800.0,test,nov-2024\n"
        "2024-12,310.0,610.0,810.0,test,dic-2024\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        tmp_csv = f.name
    pi = np.full(24, 5000.0)
    capped = apply_creg101066_ceiling(pi, "2024-11-01", level="PES",
                                       effective_date="2024-12-01",
                                       csv_path=tmp_csv)
    # Sin recorte (effective_date no se ha alcanzado)
    assert np.allclose(capped, pi)


def test_ceiling_returns_diagnostics_when_requested():
    """return_diagnostics=True devuelve tupla con metricas correctas."""
    # 48 horas en jul-2025: 5 horas > PES jul (865.22), resto bajo
    pi = np.array([100.0] * 5 + [1500.0] * 5 + [100.0] * 38)
    result = apply_creg101066_ceiling(pi, "2025-07-01", level="PES",
                                       return_diagnostics=True)
    assert isinstance(result, tuple)
    capped, diag = result
    assert diag["hours_capped"] == 5
    assert diag["fraction"] == pytest.approx(5 / 48)
    assert diag["delta_cop_total"] == pytest.approx((1500.0 - 865.22) * 5)
    assert "2025-07" in diag["by_month"]
    assert diag["by_month"]["2025-07"]["hours_capped"] == 5


# ─── Grupo C — Integracion en get_pi_bolsa ───────────────────────────────────

def test_get_pi_bolsa_applies_ceiling_by_default():
    """get_pi_bolsa(apply_ceiling=True) topa la serie a max(PES) del horizonte."""
    pi = get_pi_bolsa(T=5160, t_start="2025-07-01",
                      use_api=True, apply_ceiling=True)
    # max(PES) jul-ene = 898.02 (ago-2025)
    assert pi.max() <= 898.02 + 1e-6


def test_get_pi_bolsa_respects_disable_flag():
    """apply_ceiling=False entrega la serie sin recortar (puede exceder PES)."""
    pi_capped = get_pi_bolsa(T=5160, t_start="2025-07-01",
                              use_api=True, apply_ceiling=True)
    pi_raw    = get_pi_bolsa(T=5160, t_start="2025-07-01",
                              use_api=True, apply_ceiling=False)
    # raw debe tener al menos un valor > PES (cache real tiene picos > 1000)
    assert pi_raw.max() > pi_capped.max()


# ─── Grupo D — Validacion contra PB oficial XM (regresion) ───────────────────

PB_OFFICIAL_PROM_MES = {
    # Valores oficiales (PRECIO_BOLSA_PROM_MES o PPB del informe XM)
    "2025-07": 138.36,
    "2025-08": 251.50,
    "2025-09": 292.65,
    "2025-10": 176.90,
    "2025-11": 234.87,
    "2025-12": 278.83,
    "2026-01": 213.00,
}


def test_capped_monthly_means_match_official_within_tolerance():
    """
    Media mensual de la serie con techo PES dentro del +/-15% del
    PRECIO_BOLSA_PROM_MES oficial XM, EXCEPTO ene-2026 (gap conocido,
    follow-up CAL-17: pydataxm devuelve datos provisionales para ese mes).

    Tolerancia +/-15%: el oficial XM es promedio ponderado por demanda
    horaria, mientras la serie del cache se promedia aritmeticamente. La
    diferencia tipica esta en 3-7%, pero nov-2025 muestra ~12% y se
    acepta como margen estructural de la metrica.
    """
    pi = get_pi_bolsa(T=5160, t_start="2025-07-01",
                      use_api=True, apply_ceiling=True)
    idx = pd.date_range("2025-07-01", periods=5160, freq="1h")
    serie = pd.Series(pi, index=idx)

    out_of_tolerance = []
    for mes_str, oficial in PB_OFFICIAL_PROM_MES.items():
        mask = serie.index.to_period("M") == pd.Period(mes_str, freq="M")
        media = serie[mask].mean()
        delta_pct = abs(media - oficial) / oficial * 100
        if delta_pct > 15.0 and mes_str != "2026-01":
            out_of_tolerance.append(
                f"{mes_str}: capped={media:.1f} oficial={oficial:.1f} "
                f"delta={delta_pct:.1f}%"
            )
    assert not out_of_tolerance, (
        "Meses fuera de la tolerancia +/-15% (excluyendo ene-2026 follow-up "
        f"CAL-17):\n" + "\n".join(out_of_tolerance)
    )
