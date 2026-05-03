"""
tests/test_cal27_c4_monthly.py — CAL-27 C4-mensual con Hx
============================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 4.1 + 4.2 + 3.1-3.3

Verifica:
  1. mode='monthly_hx' es aceptado por run_c4_creg101072.
  2. Sin month_labels, todo es un único período (similar a perfil diario).
  3. Con month_labels, cada mes se liquida separadamente.
  4. Hipótesis CAL-27: total_net_benefit(monthly_hx) >= total_net_benefit(creg174_inheritance).
  5. Default sigue 'creg174_inheritance' (CAL-15 intacto).

Referencia: docs/adr/0027-cal27-c4-mensual-hx.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scenarios.scenario_c4_creg101072 import (
    run_c4_creg101072,
    compute_pde_weights,
)


def _build_setup(N=4, T=24*7):
    """Setup deterministico con surplus diurno y deficit nocturno."""
    rng = np.random.default_rng(0)
    g_pat = np.zeros(T)
    # Surplus solar entre horas 7-17 cada día (T=24*7 ⇒ 7 días)
    for d in range(T // 24):
        g_pat[d*24+7:d*24+17] = np.array([0.4, 0.7, 1.0, 1.2, 1.3, 1.2,
                                            1.1, 1.0, 0.8, 0.4])
    d_pat = np.full(T, 0.5)
    d_pat[8:20] = 1.0  # carga diurna estable

    g_base = np.array([8.0, 6.0, 0.0, 5.0])[:N]
    d_base = np.array([2.0, 3.0, 5.0, 2.5])[:N]
    G = np.outer(g_base, g_pat)
    D = np.outer(d_base, d_pat)
    pi_gs = np.full((N, T), 900.0)
    pi_bolsa = np.full(T, 200.0)
    capacity = g_base.copy()
    pde = compute_pde_weights(capacity, method="capacity_proportional")
    return D, G, pi_gs, pi_bolsa, pde, capacity


# ─── A — Aceptación del modo nuevo ──────────────────────────────────────────


def test_monthly_hx_mode_es_aceptado():
    D, G, pi_gs, pi_bolsa, pde, cap = _build_setup()
    res = run_c4_creg101072(
        D=D, G=G, pi_gs=pi_gs, pi_bolsa=pi_bolsa,
        pde=pde, capacity=cap,
        mode="monthly_hx",
        component_c="auto",
    )
    assert "per_agent" in res
    assert "aggregate" in res
    assert res["params"]["mode"] == "monthly_hx"


def test_monthly_hx_sin_labels_es_periodo_unico():
    """Sin month_labels, n_periods == 1."""
    D, G, pi_gs, pi_bolsa, pde, cap = _build_setup()
    res = run_c4_creg101072(
        D=D, G=G, pi_gs=pi_gs, pi_bolsa=pi_bolsa,
        pde=pde, capacity=cap,
        mode="monthly_hx",
    )
    assert res["params"]["n_periods"] == 1


def test_monthly_hx_con_labels_dos_periodos():
    """Con 2 month_labels distintos, n_periods == 2."""
    D, G, pi_gs, pi_bolsa, pde, cap = _build_setup(N=4, T=24*14)
    # 7 días en mes 1, 7 días en mes 2
    labels = np.array([1] * (24*7) + [2] * (24*7), dtype=int)
    res = run_c4_creg101072(
        D=D, G=G, pi_gs=pi_gs, pi_bolsa=pi_bolsa,
        pde=pde, capacity=cap,
        mode="monthly_hx",
        month_labels=labels,
    )
    assert res["params"]["n_periods"] == 2


# ─── B — Hipótesis CAL-27: monthly_hx >= creg174_inheritance ───────────────


def test_hipotesis_monthly_hx_no_peor_que_creg174_inheritance():
    """
    En la hipótesis CAL-27, ``total_net_benefit(monthly_hx)`` debe ser
    >= ``total_net_benefit(creg174_inheritance)``. La diferencia
    típica es 0-5%.
    """
    D, G, pi_gs, pi_bolsa, pde, cap = _build_setup()

    res_inh = run_c4_creg101072(
        D=D, G=G, pi_gs=pi_gs, pi_bolsa=pi_bolsa,
        pde=pde, capacity=cap,
        mode="creg174_inheritance",
    )
    res_mhx = run_c4_creg101072(
        D=D, G=G, pi_gs=pi_gs, pi_bolsa=pi_bolsa,
        pde=pde, capacity=cap,
        mode="monthly_hx",
    )

    inh_total = res_inh["aggregate"]["total_net_benefit"]
    mhx_total = res_mhx["aggregate"]["total_net_benefit"]
    # Tolerancia 1%: monthly_hx no debe ser sustancialmente peor.
    # En la hipótesis es >=; permitimos eps numérico.
    assert mhx_total >= inh_total - abs(inh_total) * 0.01, (
        f"CAL-27 hipótesis violada: monthly_hx={mhx_total:.0f} < "
        f"creg174_inheritance={inh_total:.0f}"
    )


# ─── C — Default sin cambios ─────────────────────────────────────────────


def test_default_sigue_creg174_inheritance():
    """run_c4_creg101072 sin mode usa creg174_inheritance (CAL-15)."""
    D, G, pi_gs, pi_bolsa, pde, cap = _build_setup()
    res_default = run_c4_creg101072(
        D=D, G=G, pi_gs=pi_gs, pi_bolsa=pi_bolsa,
        pde=pde, capacity=cap,
    )
    res_explicit = run_c4_creg101072(
        D=D, G=G, pi_gs=pi_gs, pi_bolsa=pi_bolsa,
        pde=pde, capacity=cap,
        mode="creg174_inheritance",
    )
    assert (res_default["aggregate"]["total_net_benefit"]
            == pytest.approx(
                res_explicit["aggregate"]["total_net_benefit"]))


# ─── D — Estructura del output ──────────────────────────────────────────────


def test_monthly_hx_per_agent_keys_compatibles_con_creg174():
    """per_agent debe tener las mismas claves que creg174_inheritance."""
    D, G, pi_gs, pi_bolsa, pde, cap = _build_setup()
    res_mhx = run_c4_creg101072(
        D=D, G=G, pi_gs=pi_gs, pi_bolsa=pi_bolsa,
        pde=pde, capacity=cap,
        mode="monthly_hx",
    )
    expected_keys = {"savings", "pde_credits", "surplus_revenue",
                      "grid_cost", "net_benefit", "pde_weight"}
    for n, agent_data in res_mhx["per_agent"].items():
        assert expected_keys <= set(agent_data.keys()), (
            f"Agente {n} faltan claves: "
            f"{expected_keys - set(agent_data.keys())}"
        )
