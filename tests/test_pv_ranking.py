"""
tests/test_pv_ranking.py — Sprint 6.5 ranking PV con cruces
==============================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 4.1

Verifica:
  1. ranking_table_pv produce columnas factor/NB_*/rank_*/star_*.
  2. Detecta cambios de ranking respecto al baseline (★).
  3. plot_pv_ranking genera PNG razonable.
  4. Acepta dicts y SensitivityResult indistintamente.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_ranking_table_pv_smoke_factor_unico():
    """Factor único: ranks 1..N consistentes y sin asteriscos."""
    from analysis.sensitivity import ranking_table_pv

    results = [
        {"param_value": 1.0,
         "net_benefit": {"P2P": 1e6, "C1": 2e6, "C2": 1.5e6}},
    ]
    df = ranking_table_pv(results)
    assert "factor" in df.columns
    assert int(df.loc[0, "rank_C1"]) == 1
    assert int(df.loc[0, "rank_C2"]) == 2
    assert int(df.loc[0, "rank_P2P"]) == 3
    for s in ["P2P", "C1", "C2"]:
        assert df.loc[0, f"star_{s}"] == ""


def test_ranking_table_pv_detecta_cruce():
    """Si el orden cambia entre factores, ★ marca el cambio respecto al baseline."""
    from analysis.sensitivity import ranking_table_pv

    results = [
        {"param_value": 1.0, "net_benefit": {"P2P": 1e6, "C1": 2e6}},
        {"param_value": 3.0, "net_benefit": {"P2P": 5e6, "C1": 2e6}},
    ]
    df = ranking_table_pv(results, baseline_factor=1.0)
    base = df[df["factor"] == 1.0].iloc[0]
    high = df[df["factor"] == 3.0].iloc[0]
    assert base["star_C1"] == ""
    assert base["star_P2P"] == ""
    # En factor 3.0 el ranking cambió: ambos con ★
    assert high["star_C1"] == "★"
    assert high["star_P2P"] == "★"


def test_ranking_table_pv_acepta_sensitivity_result():
    """Acepta SensitivityResult (de run_sensitivity_pv) sin convertir."""
    from analysis.sensitivity import SensitivityResult, ranking_table_pv

    sr1 = SensitivityResult(
        param_name="PV_factor", param_value=1.0,
        net_benefit={"P2P": 1e6, "C1": 2e6},
    )
    sr2 = SensitivityResult(
        param_name="PV_factor", param_value=2.0,
        net_benefit={"P2P": 4e6, "C1": 2e6},
    )
    df = ranking_table_pv([sr1, sr2])
    assert len(df) == 2
    assert int(df.loc[df["factor"] == 1.0, "rank_C1"].iloc[0]) == 1
    assert int(df.loc[df["factor"] == 2.0, "rank_P2P"].iloc[0]) == 1


def test_plot_pv_ranking_genera_png(tmp_path):
    """Smoke: figura PNG con tamaño no trivial."""
    from analysis.sensitivity import ranking_table_pv, plot_pv_ranking

    results = [
        {"param_value": 1.0, "net_benefit": {"P2P": 1e6, "C1": 2e6}},
        {"param_value": 2.0, "net_benefit": {"P2P": 4e6, "C1": 2e6}},
    ]
    df = ranking_table_pv(results)
    out = tmp_path / "fig_pv_ranking.png"
    plot_pv_ranking(df, ["P2P", "C1"], out)
    assert out.exists()
    assert out.stat().st_size > 1000


def test_ranking_table_pv_subset_escenarios():
    """Si scenarios se pasa explícito, ignora claves extra del dict."""
    from analysis.sensitivity import ranking_table_pv

    results = [
        {"param_value": 1.0,
         "net_benefit": {"P2P": 1e6, "C1": 2e6, "C2": 5e5, "C3": 0}},
    ]
    df = ranking_table_pv(results, scenarios=["P2P", "C1"])
    assert "NB_P2P" in df.columns
    assert "NB_C1" in df.columns
    assert "NB_C2" not in df.columns
    assert "NB_C3" not in df.columns
