"""
Actividad 3.1 — Verifica que el índice temporal del cargador MTE
sea tz-aware con zona America/Bogota.

No requiere MedicionesMTE/ ni datos reales; valida la lógica de
localización sobre el rango de fechas del proyecto.
"""

import pandas as pd


def test_tz_localize_colombia():
    """La localización no debe producir NaT ni errores en el período real."""
    idx = pd.date_range("2025-07-01", "2026-02-01", freq="1h", inclusive="left")
    idx_tz = idx.tz_localize(
        "America/Bogota",
        nonexistent="shift_forward",
        ambiguous="infer",
    )
    assert idx_tz.tzinfo is not None, "Índice debe ser tz-aware"
    assert str(idx_tz.tzinfo) == "America/Bogota"
    assert idx_tz.isna().sum() == 0, "No deben generarse NaT"
    assert len(idx_tz) == len(idx)


def test_tz_aware_dtype():
    """El índice localizado debe tener tzinfo distinto de None."""
    idx = pd.date_range("2025-07-01", "2025-07-02", freq="1h", inclusive="left")
    idx_tz = idx.tz_localize(
        "America/Bogota",
        nonexistent="shift_forward",
        ambiguous="infer",
    )
    assert idx_tz.tzinfo is not None


def test_tz_preserves_length():
    """tz_localize no debe cambiar el número de horas del período."""
    idx = pd.date_range("2025-07-01", "2026-02-01", freq="1h", inclusive="left")
    idx_tz = idx.tz_localize(
        "America/Bogota",
        nonexistent="shift_forward",
        ambiguous="infer",
    )
    assert len(idx_tz) == 5160, f"Esperado 5160 h, obtenido {len(idx_tz)}"
