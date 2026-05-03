"""
tests/test_run_paper_decomposition.py — Sprint 6.4 separar ahorro vs venta
=============================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 4.1 + 4.2

Verifica:
  1. _p2p_decomposed devuelve (autoconsumo, mercado) coherentes.
  2. C1 y C2 tienen autoconsumo idéntico (mismo offset físico).
  3. Resumen del paper incluye 3 columnas: Ahorro/Venta/Total.
  4. Smoke: el script genera figura barras apiladas.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_p2p_decomposed_no_negativo():
    """Mock de p2p_results: autoconsumo y mercado nunca negativos."""
    from scripts.run_paper_iter import _p2p_decomposed
    from core.ems_p2p import HourlyResult

    N, T = 3, 24
    rng = np.random.default_rng(0)
    D = rng.uniform(1, 5, (N, T))
    G_klim = rng.uniform(0, 4, (N, T))
    pi_gs = np.full((N, T), 900.0)

    # Resultados horarios mock: sin mercado (P_star=0)
    results = []
    for k in range(T):
        results.append(HourlyResult(
            k=k, P_star=np.zeros((1, 1)), pi_star=np.array([100.0]),
            seller_ids=[0], buyer_ids=[1],
        ))
    auto, mercado = _p2p_decomposed(results, D, G_klim, pi_gs, 200.0,
                                      list(range(N)))
    assert (auto >= 0).all()
    # mercado puede ser 0 si no hay flujos P2P
    assert auto.sum() > 0  # debe haber autoconsumo


def test_resumen_tiene_3_columnas_decomposition():
    """El xlsx Resumen tiene Ahorro_autoconsumo_COP, Venta_excedentes_COP, Total_COP."""
    import os, subprocess
    mte_root = ROOT / "MedicionesMTE_v3"
    if not mte_root.is_dir():
        pytest.skip("MedicionesMTE_v3 no disponible")
    out_dir = ROOT / "outputs" / "paper"

    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_paper_iter.py"),
         "--month", "2025-08", "--tag", "test_decomp"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
        timeout=180,
    )
    assert res.returncode == 0
    xlsx = out_dir / "resultados_paper_test_decomp.xlsx"
    assert xlsx.exists()
    df = pd.read_excel(xlsx, sheet_name="Resumen")
    required = {"Ahorro_autoconsumo_COP", "Venta_excedentes_COP", "Total_COP"}
    assert required <= set(df.columns)
    # Total = ahorro + venta (con tolerancia de redondeo)
    for _, row in df.iterrows():
        suma = row["Ahorro_autoconsumo_COP"] + row["Venta_excedentes_COP"]
        assert abs(suma - row["Total_COP"]) < 100.0


def test_c1_y_c2_tienen_autoconsumo_identico():
    """Hipótesis del asesor (líneas 414-462): autoconsumo es offset común."""
    out_dir = ROOT / "outputs" / "paper"
    xlsx = out_dir / "resultados_paper_test_decomp.xlsx"
    if not xlsx.exists():
        pytest.skip("Test anterior no generó xlsx")
    df = pd.read_excel(xlsx, sheet_name="Resumen")
    c1 = df.loc[df["Escenario"].str.contains("CREG 174"),
                "Ahorro_autoconsumo_COP"].iloc[0]
    c2 = df.loc[df["Escenario"].str.contains("101 072"),
                "Ahorro_autoconsumo_COP"].iloc[0]
    assert c1 == pytest.approx(c2, rel=1e-6), (
        f"C1 autoconsumo {c1:.0f} != C2 autoconsumo {c2:.0f}"
    )


def test_figura_barras_apiladas_existe():
    """fig_offset_vs_diferencial_<tag>.png se genera junto al xlsx."""
    fig = (ROOT / "outputs" / "paper"
            / "fig_offset_vs_diferencial_test_decomp.png")
    if not fig.exists():
        pytest.skip("Test anterior no se ejecutó")
    assert fig.stat().st_size > 1000  # PNG razonable
