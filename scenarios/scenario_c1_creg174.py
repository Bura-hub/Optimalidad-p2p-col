"""
scenario_c1_creg174.py
----------------------
Escenario C1: Autogeneración a Pequeña Escala (AGPE)
Resolución CREG 174 de 2021 — balance por período de facturación

Mecanismo (alineado con arts. 22-23 CREG 174 y Decreto 2469/2014):
  1. Autoconsumo directo hora a hora  → valor = pi_gs  (no se compra a la red)
  2. Energía inyectada vs energía retirada se PERMUTAN dentro del período
     de facturación (mes) → cada kWh permutado vale pi_gs (reemplaza compra)
  3. Excedente NETO del período = max(0, Σ inyectado − Σ retirado)
     → remunerado a precio de bolsa promedio ponderado del período

Diferencia estructural con C3:
  C1 (este módulo):  liquidación en el período de facturación (mes).
     La energía permutada se valora a pi_gs, no a bolsa.
     Solo el excedente neto del período llega a bolsa.
  C3 (scenario_c3_spot): liquidación hora a hora.
     Cada kWh excedente de cada hora → bolsa(h).
     El agente asume volatilidad spot completa.

Cuando pi_bolsa < pi_gs (caso habitual en Colombia), C1 es más favorable
porque más energía se valora a pi_gs (vía permutación) en vez de bolsa.

Parámetros
----------
month_labels : array (T,) de enteros con etiqueta del período de facturación
               (p.ej. año×100+mes: 202507, 202508, …).
               Si None, todo el horizonte se trata como un único período
               (equivalente al modo perfil-diario de 24 h).

Referencia regulatoria:
    CREG 174 de 2021 - Artículo 5 (pequeña escala ≤ 1 MW)
    Decreto MinEnergía 2469 de 2014 - art. 2.2.3.2.4.1
"""

from __future__ import annotations

import numpy as np
from collections import defaultdict
from typing import Optional, Union

from ._pi_gs import as_pi_gs_vector


def run_c1_creg174(
    D:            np.ndarray,                # (N, T) demanda base [kWh]
    G:            np.ndarray,                # (N, T) generación bruta [kWh]
    pi_gs:        Union[float, np.ndarray],  # escalar o (N,) — CAL-8
    pi_bolsa:     np.ndarray,               # (T,) precio de bolsa horario $/kWh
    agent_ids:    list,                      # índices de agentes autogeneradores
    month_labels: Optional[np.ndarray] = None,  # (T,) etiqueta de período (ej. YYYYMM)
) -> dict:
    """
    Simula el esquema CREG 174 con balance por período de facturación.

    Para cada agente n y cada período de facturación m:

        G_total_m  = Σ_{k∈m} max(G[n,k], 0)
        D_total_m  = Σ_{k∈m} max(D[n,k], 0)
        auto_m     = Σ_{k∈m} min(G[n,k], D[n,k])          ← autoconsumo directo
        surplus_h  = Σ_{k∈m} max(G[n,k]-D[n,k], 0)        ← inyectado a la red
        deficit_h  = Σ_{k∈m} max(D[n,k]-G[n,k], 0)        ← retirado de la red

        E_permuted_m    = min(surplus_h, deficit_h)
        E_net_surplus_m = max(0, surplus_h - deficit_h)

        savings_m  = (auto_m + E_permuted_m) × pi_gs
                   = min(G_total_m, D_total_m) × pi_gs
        revenue_m  = E_net_surplus_m × π̄_bolsa_m
                     donde π̄_bolsa_m es el promedio ponderado de bolsa
                     en las horas de excedente del período

        net_benefit_n = Σ_m (savings_m + revenue_m)
    """
    N, T = D.shape
    pi_gs_v = as_pi_gs_vector(pi_gs, N)

    # ── Construir índice de períodos ─────────────────────────────────────────
    if month_labels is None:
        # Período único (modo perfil diario 24h o sintético)
        period_hours: dict[int, list[int]] = {0: list(range(T))}
    else:
        period_hours = defaultdict(list)
        for k, m in enumerate(month_labels):
            period_hours[int(m)].append(k)

    results: dict = {}
    total_savings         = 0.0
    total_surplus_revenue = 0.0
    total_grid_cost       = 0.0

    for n in agent_ids:
        savings_n  = 0.0
        surplus_n  = 0.0
        grid_cost_n = 0.0

        for _m, hours in period_hours.items():
            # ── Vectores del período ─────────────────────────────────────
            G_h = np.maximum(G[n, hours], 0.0)  # generación  (≥0)
            D_h = np.maximum(D[n, hours], 0.0)  # demanda     (≥0)
            pb_h = pi_bolsa[hours]               # precios bolsa del período

            # ── Flujos horarios ──────────────────────────────────────────
            auto_h     = np.minimum(G_h, D_h)   # autoconsumo directo (kWh)
            surplus_h  = G_h - auto_h            # inyectado a la red  (≥0)
            deficit_h  = D_h - auto_h            # retirado de la red  (≥0)

            # ── Totales del período ──────────────────────────────────────
            E_auto    = float(np.sum(auto_h))
            E_surplus = float(np.sum(surplus_h))
            E_deficit = float(np.sum(deficit_h))

            # ── Permutación y excedente neto ─────────────────────────────
            E_permuted    = min(E_surplus, E_deficit)
            E_net_surplus = max(0.0, E_surplus - E_deficit)

            # ── Valoración ───────────────────────────────────────────────
            # Autoconsumo + permutación → valorados a pi_gs[n] del agente
            savings_m = (E_auto + E_permuted) * pi_gs_v[n]

            # Excedente neto → bolsa promedio ponderado por excedente horario
            if E_net_surplus > 1e-9 and E_surplus > 1e-9:
                pi_bolsa_avg = float(np.dot(surplus_h, pb_h) / E_surplus)
            else:
                pi_bolsa_avg = float(np.mean(pb_h))

            revenue_m   = E_net_surplus * pi_bolsa_avg

            # Costo residual de red (energía que aún compra: déficit > surplus)
            grid_cost_m = max(0.0, E_deficit - E_surplus) * pi_gs_v[n]

            savings_n   += savings_m
            surplus_n   += revenue_m
            grid_cost_n += grid_cost_m

        results[n] = {
            "savings":         savings_n,
            "surplus_revenue": surplus_n,
            "grid_cost":       grid_cost_n,
            "net_benefit":     savings_n + surplus_n,
        }

        total_savings         += savings_n
        total_surplus_revenue += surplus_n
        total_grid_cost       += grid_cost_n

    results["aggregate"] = {
        "total_savings":         total_savings,
        "total_surplus_revenue": total_surplus_revenue,
        "total_grid_cost":       total_grid_cost,
        "total_net_benefit":     total_savings + total_surplus_revenue,
    }

    return results


def net_economic_gain_c1(results: dict, agent_ids: list) -> np.ndarray:
    """Extrae ganancia económica neta por agente como vector."""
    return np.array([results[n]["net_benefit"] for n in agent_ids])
