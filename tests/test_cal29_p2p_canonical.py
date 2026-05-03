"""
tests/test_cal29_p2p_canonical.py — CAL-29 fórmula canónica P2P (paper)
=========================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 4.1 + 4.2

Verifica los invariantes del fix CAL-29 al `_p2p_decomposed` del script
paper:

  1. Autoconsumo P2P == C1 == C2 (offset común post-fix Bug 2).
  2. Autoconsumo se cuenta en TODAS las horas, no solo las activas.
  3. La descomposición incluye residual surplus (Bug 1 fix).
  4. Replicación del invariante H1 del audit (delta ≈ pi_bolsa × surplus).

Referencia: docs/adr/0029-cal29-p2p-revenue-canonica.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_autoconsumo_p2p_cuenta_horas_sin_mercado():
    """Bug 2 fix: con todos los P_star=0, autoconsumo total = sum_t min(G,D)*pi_gs."""
    from scripts.run_paper_iter import _p2p_decomposed
    from core.ems_p2p import HourlyResult

    N, T = 3, 24
    rng = np.random.default_rng(42)
    D = rng.uniform(1, 5, (N, T))
    G_klim = rng.uniform(0, 4, (N, T))
    pi_gs = np.full((N, T), 900.0)
    pi_bolsa = np.full(T, 200.0)

    # Resultados sin trades en TODAS las horas
    results = []
    for k in range(T):
        results.append(HourlyResult(
            k=k, P_star=np.zeros((1, 1)), pi_star=np.array([100.0]),
            seller_ids=[0], buyer_ids=[1],
        ))
    auto, _mercado = _p2p_decomposed(
        results, D, G_klim, pi_gs, 200.0, list(range(N)),
        pi_bolsa=pi_bolsa,
    )
    # Autoconsumo esperado (analítico): sum_t min(G,D) * pi_gs
    auto_expected = np.array([
        float(np.sum(np.minimum(G_klim[n], D[n]) * pi_gs[n]))
        for n in range(N)
    ])
    np.testing.assert_allclose(auto, auto_expected, rtol=1e-6,
                                 err_msg="Bug 2 fix: autoconsumo debe contar todas las horas")


def test_residual_surplus_se_incluye_en_mercado():
    """Bug 1 fix: residual surplus contribuye con pi_bolsa × residual."""
    from scripts.run_paper_iter import _p2p_decomposed
    from core.ems_p2p import HourlyResult

    N, T = 2, 4
    # Agente 0 tiene surplus 5 kWh/hr; agente 1 tiene deficit.
    G_klim = np.array([[5.0, 5.0, 5.0, 5.0],
                        [0.0, 0.0, 0.0, 0.0]])
    D = np.array([[0.0, 0.0, 0.0, 0.0],
                   [3.0, 3.0, 3.0, 3.0]])
    pi_gs = np.full((N, T), 800.0)
    pi_bolsa = np.full(T, 250.0)
    pi_gb = 250.0

    # Trade P2P: agente 0 vende 2 kWh a agente 1 cada hora a pi_star=400.
    # Residual surplus = 5 - 2 = 3 kWh/hr × 4 horas = 12 kWh totales.
    results = []
    for k in range(T):
        results.append(HourlyResult(
            k=k,
            P_star=np.array([[2.0]]),  # seller 0 -> buyer 1, 2 kWh
            pi_star=np.array([400.0]),
            seller_ids=[0], buyer_ids=[1],
        ))
    _auto, mercado = _p2p_decomposed(
        results, D, G_klim, pi_gs, pi_gb, [0, 1],
        pi_bolsa=pi_bolsa,
    )

    # Vendedor 0:
    #   trade revenue completo: 4 horas × 2 kWh × 400 = 3200
    #   residual: 4 horas × 3 kWh × 250 = 3000
    #   total mercado_0 = 6200
    expected_seller_mercado = 4 * 2 * 400 + 4 * 3 * 250
    assert mercado[0] == pytest.approx(expected_seller_mercado, rel=1e-6)

    # Comprador 1:
    #   savings = 4 horas × 2 kWh × (800 - 400) = 3200
    expected_buyer_mercado = 4 * 2 * (800 - 400)
    assert mercado[1] == pytest.approx(expected_buyer_mercado, rel=1e-6)


def test_canonica_simetria_con_c1_autoconsumo_paper():
    """Tras correr el script paper, autoconsumo P2P == C1 == C2 (offset común)."""
    out_dir = ROOT / "outputs" / "paper"
    xlsx = out_dir / "resultados_paper_test_decomp.xlsx"
    if not xlsx.exists():
        pytest.skip("Test de Sprint 6.4 no generó xlsx; correr ese primero")
    df = pd.read_excel(xlsx, sheet_name="Resumen")
    auto_p2p = df.loc[df["Escenario"].str.contains("P2P"),
                        "Ahorro_autoconsumo_COP"].iloc[0]
    auto_c1 = df.loc[df["Escenario"].str.contains("CREG 174"),
                        "Ahorro_autoconsumo_COP"].iloc[0]
    auto_c2 = df.loc[df["Escenario"].str.contains("101 072"),
                        "Ahorro_autoconsumo_COP"].iloc[0]
    assert auto_p2p == pytest.approx(auto_c1, rel=1e-3), (
        f"CAL-29: P2P autoconsumo {auto_p2p:.0f} != C1 autoconsumo {auto_c1:.0f}"
    )
    assert auto_c1 == pytest.approx(auto_c2, rel=1e-6)


def test_pi_bolsa_default_a_pi_gb_si_no_se_pasa():
    """Si pi_bolsa=None, _p2p_decomposed usa pi_gb escalar como fallback."""
    from scripts.run_paper_iter import _p2p_decomposed
    from core.ems_p2p import HourlyResult

    N, T = 1, 2
    G_klim = np.array([[3.0, 3.0]])
    D = np.array([[0.0, 0.0]])  # surplus puro
    pi_gs = np.full((N, T), 700.0)
    pi_gb = 300.0

    results = [
        HourlyResult(k=k, P_star=np.zeros((0, 0)),
                      pi_star=np.array([]),
                      seller_ids=[], buyer_ids=[])
        for k in range(T)
    ]
    # Sin pi_bolsa: usa pi_gb=300 como aproximación
    _auto, mercado = _p2p_decomposed(
        results, D, G_klim, pi_gs, pi_gb, [0],
    )
    # Residual = 6 kWh × 300 COP/kWh = 1800
    assert mercado[0] == pytest.approx(2 * 3 * 300, rel=1e-6)
