"""
scenario_c2_bilateral.py
------------------------
Escenario C2: Contratos bilaterales (Power Purchase Agreement — PPA)
Mecanismo: precio fijo pactado a largo plazo entre generador y consumidor.

El generador vende su excedente a un precio fijo pi_ppa negociado
al inicio del contrato (no varía hora a hora). El consumidor paga
ese precio fijo independientemente del precio de bolsa.

Ventaja: elimina volatilidad del precio de bolsa.
Desventaja: puede implicar costos de oportunidad si pi_bolsa sube mucho.

Se modela como: cada prosumidor con excedente firma un contrato con
uno o más consumidores a un precio pi_ppa = promedio(pi_gb, pi_gs) * factor.
"""

from typing import Union

import numpy as np

from ._pi_gs import as_pi_gs_vector


def run_c2_bilateral(
    D: np.ndarray,             # (N, T) demanda [kWh]
    G: np.ndarray,             # (N, T) generación bruta [kWh]
    pi_gs: Union[float, np.ndarray],  # escalar o (N,) — CAL-8
    pi_gb: float,              # precio de compra red al usuario $/kWh
    pi_ppa: float,             # precio PPA pactado $/kWh
    prosumer_ids: list,        # índices de agentes con generación
    consumer_ids: list,        # índices de consumidores puros
) -> dict:
    """
    Lógica:
      1. Cada prosumidor autoconsume primero
      2. El excedente se vende a precio pi_ppa a los consumidores del contrato
      3. Los consumidores compran a pi_ppa hasta cubrir su demanda;
         el déficit restante va a la red a pi_gs
      4. Si queda excedente del prosumidor, va a red a pi_gb

    Reparto del excedente: proporcional a la demanda de cada consumidor.

    Filosofía A (WEEF min 22-26): net_benefit = savings + revenues.
    No se resta grid_cost residual; ese costo se incurriría igual sin PPA.
    """
    N, T = D.shape
    pi_gs_v = as_pi_gs_vector(pi_gs, N)

    savings_gen  = np.zeros(N)    # ahorro autoconsumo + ingreso PPA
    savings_cons = np.zeros(N)    # ahorro por comprar a pi_ppa < pi_gs
    grid_cost    = np.zeros(N)    # costo energía aún comprada a red
    grid_revenue = np.zeros(N)    # ingresos por venta excedente a red

    for k in range(T):
        # Excedentes netos de prosumidores
        gen_surplus = np.maximum(G[:, k] - D[:, k], 0.0)
        # Déficit de todos los agentes (antes de contrato)
        deficits    = np.maximum(D[:, k] - G[:, k], 0.0)

        total_surplus = float(np.sum(gen_surplus[prosumer_ids]))
        total_deficit_cons = float(np.sum(deficits[consumer_ids]))

        # Autoconsumo: ahorro de cada prosumidor (a su pi_gs[n])
        for n in prosumer_ids:
            autoconsumo = min(G[n, k], D[n, k])
            savings_gen[n] += autoconsumo * pi_gs_v[n]

        # Distribución del excedente a consumidores (proporcional a demanda)
        dem_cons = np.array([D[i, k] for i in consumer_ids])
        total_dem_cons = float(np.sum(dem_cons))

        if total_dem_cons > 0 and total_surplus > 0:
            share = dem_cons / total_dem_cons
            ppa_delivered = np.minimum(share * total_surplus, dem_cons)

            for idx, i in enumerate(consumer_ids):
                # Ahorro del consumidor: habría pagado pi_gs[i], paga pi_ppa
                savings_cons[i] += ppa_delivered[idx] * (pi_gs_v[i] - pi_ppa)
                # Déficit residual → red a la tarifa del consumidor
                residual = max(0.0, deficits[i] - ppa_delivered[idx])
                grid_cost[i] += residual * pi_gs_v[i]

            # Ingresos PPA del prosumidor
            for n in prosumer_ids:
                frac = gen_surplus[n] / total_surplus if total_surplus > 0 else 0.0
                ppa_sold = frac * float(np.sum(ppa_delivered))
                savings_gen[n] += ppa_sold * pi_ppa
                # Excedente que no se vendió por PPA → red
                ppa_unsold = gen_surplus[n] - ppa_sold * gen_surplus[n] / max(gen_surplus[n], 1e-9)
                grid_revenue[n] += max(0.0, gen_surplus[n] - ppa_sold) * pi_gb
        else:
            # Sin PPA posible: todo va a red
            for n in prosumer_ids:
                grid_revenue[n] += gen_surplus[n] * pi_gb
            for i in consumer_ids:
                grid_cost[i] += deficits[i] * pi_gs_v[i]

    net_benefit = savings_gen + savings_cons + grid_revenue

    results_per_agent = {
        n: {
            "savings_autoconsumo": float(savings_gen[n]),
            "savings_ppa":         float(savings_cons[n]),
            "grid_revenue":        float(grid_revenue[n]),
            "grid_cost":           float(grid_cost[n]),
            "net_benefit":         float(net_benefit[n]),
            "pi_ppa":              pi_ppa,
        }
        for n in range(N)
    }

    return {
        "per_agent": results_per_agent,
        "aggregate": {
            "total_net_benefit":     float(np.sum(net_benefit)),
            "total_savings_gen":     float(np.sum(savings_gen)),
            "total_savings_cons":    float(np.sum(savings_cons)),
            "total_grid_revenue":    float(np.sum(grid_revenue)),
            "total_grid_cost":       float(np.sum(grid_cost)),
        },
        "params": {"pi_ppa": pi_ppa,
                    "pi_gs": pi_gs_v.tolist() if pi_gs_v.size > 1 else float(pi_gs_v[0]),
                    "pi_gb": pi_gb},
    }


def ppa_price_range(pi_gb: float, pi_gs: float,
                    factors: list = None) -> list:
    """
    Genera un rango de precios PPA para análisis de sensibilidad.
    Por defecto: 25%, 50%, 75% del rango [pi_gb, pi_gs].
    """
    if factors is None:
        factors = [0.25, 0.50, 0.75]
    return [pi_gb + f * (pi_gs - pi_gb) for f in factors]
