"""
scenario_c1_creg174.py
----------------------
Escenario C1: Autogeneración individual a pequeña escala
Resolución CREG 174 de 2021

Mecanismo:
  - Créditos de energía 1:1 entre horas de inyección y consumo
  - Excedentes netos liquidados a precio de bolsa (Pbolsa)
  - Cada prosumidor actúa independientemente (sin comunidad)

El ingreso neto del agente n en el período evaluado es:
    Ingreso_n = Σ_k [crédito(k) + excedente(k) * pi_bolsa(k)]
    Ahorro_n  = Σ_k credito(k) * pi_gs   (energía que no compró a la red)

Referencia regulatoria:
    CREG 174 de 2021 - Artículo 5 (pequeña escala <= 1 MW)
    Tarifa de red: pi_gs (precio regulado al usuario)
"""

import numpy as np


def run_c1_creg174(
    D: np.ndarray,           # (N, T) demanda base [kWh]
    G: np.ndarray,           # (N, T) generación bruta [kWh]
    pi_gs: float,            # precio de venta red al usuario $/kWh (precio regulado)
    pi_bolsa: np.ndarray,    # (T,) precio de bolsa horario $/kWh
    agent_ids: list,         # índices de agentes autogeneradores
) -> dict:
    """
    Simula el esquema CREG 174 para cada autogenerador individualmente.

    Lógica créditos 1:1:
        - Si G[n,k] <= D[n,k]: crédito = G[n,k] (autoconsumo total)
        - Si G[n,k] >  D[n,k]: crédito = D[n,k], excedente = G[n,k] - D[n,k]

    El excedente se liquida a precio de bolsa.

    Retorna dict con métricas por agente y agregadas.
    """
    T = D.shape[1]
    results = {}

    total_savings   = 0.0
    total_surplus_revenue = 0.0
    total_grid_cost = 0.0

    for n in agent_ids:
        savings_n  = 0.0
        surplus_n  = 0.0
        grid_cost_n = 0.0

        for k in range(T):
            gen  = max(0.0, G[n, k])
            dem  = max(0.0, D[n, k])

            if gen <= dem:
                # Autoconsumo parcial: crédito por toda la generación
                credit = gen
                deficit = dem - gen
                grid_cost_n += deficit * pi_gs
            else:
                # Autoconsumo total + excedente
                credit  = dem
                surplus = gen - dem
                surplus_n += surplus * pi_bolsa[k]

            savings_n += credit * pi_gs   # ahorro por no comprar ese kWh

        results[n] = {
            "savings":         savings_n,
            "surplus_revenue": surplus_n,
            "grid_cost":       grid_cost_n,
            "net_benefit":     savings_n + surplus_n - grid_cost_n,
        }

        total_savings         += savings_n
        total_surplus_revenue += surplus_n
        total_grid_cost       += grid_cost_n

    results["aggregate"] = {
        "total_savings":         total_savings,
        "total_surplus_revenue": total_surplus_revenue,
        "total_grid_cost":       total_grid_cost,
        "total_net_benefit":     total_savings + total_surplus_revenue - total_grid_cost,
    }

    return results


def net_economic_gain_c1(results: dict, agent_ids: list) -> np.ndarray:
    """Extrae ganancia económica neta por agente como vector."""
    return np.array([results[n]["net_benefit"] for n in agent_ids])
