"""
scenario_c4_creg101072.py
-------------------------
Escenario C4: Autogeneración Colectiva (AGRC)
Resolución CREG 101 072 de 2025 + Decreto 2236 de 2023

Este es el escenario más relevante para la tesis:
representa la alternativa regulatoria vigente contra la cual
se compara el mercado P2P dinámico.

Mecanismo - Porcentaje de Distribución de Excedentes (PDE):
  - Los excedentes de generación de la comunidad se distribuyen
    administrativamente entre los miembros según ponderadores PDE_n
  - La distribución es ESTÁTICA: no responde a preferencias individuales
    ni a condiciones de oferta/demanda en tiempo real
  - Restricciones regulatorias clave:
      * Capacidad total <= 100 kW (régimen simplificado)
      * Ningún participante puede tener más del 10% de la capacidad
        instalada de otro sin activar restricciones de composición
      * Precio de liquidación de excedentes: precio de bolsa horario

Fórmula de distribución:
    excedente_comunitario(k) = max(0, Σ_n G_n(k) - Σ_n D_n(k))
    crédito_n(k) = PDE_n * excedente_comunitario(k)

Referencia regulatoria:
    Decreto 2236 de 2023 - Marco AGRC
    Resolución CREG 101 072 de 2025 - Condiciones regulatorias
    Resolución CREG 101 066 de 2024 - Techos tarifarios
"""

import numpy as np
from typing import Optional


def validate_pde(
    pde: np.ndarray,
    tol: float = 1e-6,
) -> bool:
    """Verifica que los PDE sumen 1 y sean no negativos."""
    return bool(np.all(pde >= 0) and abs(np.sum(pde) - 1.0) < tol)


def compute_pde_weights(
    capacity: np.ndarray,    # (N,) capacidad instalada kW de cada agente
    method: str = "capacity_proportional",
) -> np.ndarray:
    """
    Calcula los ponderadores PDE.

    Métodos disponibles:
        'capacity_proportional' : PDE_n = cap_n / sum(cap)  (más común)
        'equal'                 : PDE_n = 1/N

    En la práctica, la CREG 101 072 permite ponderadores acordados
    entre miembros, con estas opciones como referencia.
    """
    if method == "capacity_proportional":
        total = float(np.sum(capacity))
        if total < 1e-10:
            return np.ones(len(capacity)) / len(capacity)
        return capacity / total
    elif method == "equal":
        N = len(capacity)
        return np.ones(N) / N
    else:
        raise ValueError(f"Método PDE desconocido: {method}")


def run_c4_creg101072(
    D: np.ndarray,              # (N, T) demanda [kWh]
    G: np.ndarray,              # (N, T) generación bruta [kWh]
    pi_gs: float,               # precio regulado de venta red al usuario $/kWh
    pi_bolsa: np.ndarray,       # (T,) precio de bolsa $/kWh
    pde: np.ndarray,            # (N,) Porcentaje de Distribución de Excedentes
    capacity: Optional[np.ndarray] = None,  # (N,) kW instalados (para validación)
    max_capacity_kw: float = 100.0,         # límite régimen simplificado
) -> dict:
    """
    Simula el esquema AGRC (CREG 101 072) con distribución PDE.

    Lógica:
      1. Cada agente autoconsume su propia generación hasta cubrir demanda
      2. El excedente comunitario se redistribuye via PDE
      3. Déficit residual se compra a la red a pi_gs
      4. Excedente neto tras redistribución se liquida a pi_bolsa

    Este mecanismo es ESTÁTICO: el PDE no varía según condiciones de mercado.
    """
    N, T = D.shape

    if not validate_pde(pde):
        raise ValueError(f"PDE inválido: debe sumar 1.0, suma={np.sum(pde):.4f}")

    # Verificar restricción de capacidad
    if capacity is not None:
        total_cap = float(np.sum(capacity))
        if total_cap > max_capacity_kw:
            raise ValueError(
                f"Capacidad total {total_cap:.1f} kW excede límite de "
                f"{max_capacity_kw} kW para régimen simplificado"
            )

    # Resultados por agente
    savings       = np.zeros(N)     # ahorro por autoconsumo propio
    credits_pde   = np.zeros(N)     # créditos recibidos vía PDE
    grid_cost     = np.zeros(N)     # costo de compras a la red
    surplus_sell  = np.zeros(N)     # ingresos por venta excedentes a bolsa

    # Seguimiento horario
    hourly_community_surplus = np.zeros(T)
    hourly_distribution      = np.zeros((N, T))

    for k in range(T):
        total_gen = float(np.sum(np.maximum(G[:, k], 0)))
        total_dem = float(np.sum(np.maximum(D[:, k], 0)))

        # Paso 1: Autoconsumo individual
        autoconsumo_k = np.minimum(np.maximum(G[:, k], 0), np.maximum(D[:, k], 0))
        deficit_k     = np.maximum(D[:, k] - G[:, k], 0.0)
        surplus_ind_k = np.maximum(G[:, k] - D[:, k], 0.0)

        # Paso 2: Excedente comunitario
        community_surplus = max(0.0, total_gen - total_dem)
        hourly_community_surplus[k] = community_surplus

        # Paso 3: Distribución PDE del excedente comunitario
        credits_k = pde * community_surplus
        hourly_distribution[:, k] = credits_k

        # Paso 4: Déficit residual tras créditos PDE
        deficit_after_pde = np.maximum(deficit_k - credits_k, 0.0)

        # Paso 5: Contabilización
        for n in range(N):
            # Ahorro por autoconsumo propio
            savings[n] += autoconsumo_k[n] * pi_gs

            # Créditos PDE (valorizados a precio de usuario)
            credits_received = min(credits_k[n], deficit_k[n])
            credits_pde[n]  += credits_received * pi_gs

            # Costo de energía que aún falta comprar a la red
            grid_cost[n] += deficit_after_pde[n] * pi_gs

        # Excedente neto comunitario que va a bolsa (si hay)
        # Se distribuye también via PDE
        net_surplus = max(0.0, total_gen - total_dem)
        if net_surplus > 0:
            for n in range(N):
                # Solo si el agente tiene generación propia excedente
                own_surplus = max(0.0, surplus_ind_k[n])
                surplus_sell[n] += own_surplus * pi_bolsa[k]

    # Ganancia = ahorro por autoconsumo + créditos PDE + ingresos excedentes.
    # No se resta grid_cost: esa energía la compraría la comunidad igual sin
    # tener el sistema solar — no es una pérdida del mecanismo AGRC.
    net_benefit = savings + credits_pde + surplus_sell

    results_per_agent = {}
    for n in range(N):
        results_per_agent[n] = {
            "savings":         float(savings[n]),
            "pde_credits":     float(credits_pde[n]),
            "surplus_revenue": float(surplus_sell[n]),
            "grid_cost":       float(grid_cost[n]),
            "net_benefit":     float(net_benefit[n]),
            "pde_weight":      float(pde[n]),
        }

    results = {
        "per_agent":   results_per_agent,
        "aggregate": {
            "total_savings":         float(np.sum(savings)),
            "total_pde_credits":     float(np.sum(credits_pde)),
            "total_surplus_revenue": float(np.sum(surplus_sell)),
            "total_grid_cost":       float(np.sum(grid_cost)),
            "total_net_benefit":     float(np.sum(net_benefit)),
        },
        "hourly": {
            "community_surplus":    hourly_community_surplus,
            "pde_distribution":     hourly_distribution,
        },
        "regulatory": {
            "pde_weights":          pde,
            "static_mechanism":     True,   # flag: no responde a mercado
        },
    }

    return results


def regulatory_risk_c4(
    agent_capacities: np.ndarray,   # (N,) kW
    max_total_kw: float = 100.0,
) -> dict:
    """
    Evalúa riesgos regulatorios del esquema C4:
      - Violación del límite de 100 kW
      - Violación de la regla del 10% de participación
    
    Este análisis es parte del Objetivo 4 de la tesis.
    """
    N = len(agent_capacities)
    total_cap = float(np.sum(agent_capacities))
    max_share = float(np.max(agent_capacities)) / total_cap if total_cap > 0 else 0.0

    risks = {
        "capacity_exceeded":      total_cap > max_total_kw,
        "total_capacity_kw":      total_cap,
        "max_single_share":       max_share,
        "concentration_risk":     max_share > 0.10,   # regla del 10%
        "n_agents":               N,
        "min_agents_for_stability": int(np.ceil(1 / 0.10)) if max_share > 0 else N,
    }
    return risks


def static_spread_c4_vs_p2p(
    D: np.ndarray,
    G: np.ndarray,
    pde: np.ndarray,
) -> np.ndarray:
    """
    Calcula el 'spread de ineficiencia estática' por hora:
    cuánta energía podría reasignarse dinámicamente pero el
    mecanismo PDE no puede capturar.

    Retorna array (T,) con el spread horario [kWh].
    """
    N, T = D.shape
    spread = np.zeros(T)

    for k in range(T):
        total_gen = float(np.sum(np.maximum(G[:, k], 0)))
        total_dem = float(np.sum(np.maximum(D[:, k], 0)))

        # Agentes con déficit y agentes con superávit
        deficit_agents  = np.sum(np.maximum(D[:, k] - G[:, k], 0))
        surplus_agents  = np.sum(np.maximum(G[:, k] - D[:, k], 0))

        # Desequilibrio que PDE no puede redistribuir eficientemente
        # porque aplica el mismo porcentaje a todos sin importar necesidad
        if deficit_agents > 0 and surplus_agents > 0:
            # Lo que PDE asigna a quien no lo necesita
            pde_to_surplus_agents = float(
                np.dot(pde, np.maximum(G[:, k] - D[:, k], 0))
            )
            spread[k] = pde_to_surplus_agents

    return spread
