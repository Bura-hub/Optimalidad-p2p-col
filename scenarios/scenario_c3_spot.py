"""
scenario_c3_spot.py
-------------------
Escenario C3: Exposición al mercado mayorista (precio de bolsa horario).

Mecanismo: el prosumidor vende sus excedentes directamente al mercado
mayorista al precio de bolsa horario (pi_bolsa[k]).

Característica: asume el riesgo total de volatilidad de precios.
  - Si pi_bolsa[k] > pi_gb base: mayor ingreso
  - Si pi_bolsa[k] < pi_gb base: menor ingreso (ej. horas de sobreoferta)
  - Fenómenos como El Niño pueden llevar pi_bolsa al precio de escasez

Referencia colombiana:
  - Precio de bolsa XM (horario)
  - Precio de escasez CREG 101 066 de 2024 (techo tarifario)
"""

import numpy as np


def run_c3_spot(
    D: np.ndarray,           # (N, T) demanda [kWh]
    G: np.ndarray,           # (N, T) generación bruta [kWh]
    pi_gs: float,            # precio de venta red al usuario $/kWh
    pi_bolsa: np.ndarray,    # (T,) precio de bolsa horario $/kWh
    prosumer_ids: list,
    consumer_ids: list,
) -> dict:
    """
    Lógica:
      1. Autoconsumo: ahorro a pi_gs
      2. Excedente vendido al mercado al precio de bolsa horario
      3. Déficit comprado a la red a pi_gs
    """
    N, T = D.shape

    savings   = np.zeros(N)   # ahorro por autoconsumo
    revenues  = np.zeros(N)   # ingresos por venta a bolsa
    grid_cost = np.zeros(N)   # compras a red

    hourly_exposure = np.zeros(T)  # exposición horaria a precio spot

    for k in range(T):
        for n in prosumer_ids:
            gen  = max(0.0, G[n, k])
            dem  = max(0.0, D[n, k])
            auto = min(gen, dem)
            savings[n]  += auto * pi_gs
            surplus = gen - auto
            revenues[n] += surplus * pi_bolsa[k]
            deficit = max(0.0, dem - gen)
            grid_cost[n] += deficit * pi_gs

        for i in consumer_ids:
            grid_cost[i] += max(0.0, D[i, k]) * pi_gs

        # Exposición total comunitaria al precio spot esta hora
        total_surplus = sum(max(0.0, G[n, k] - D[n, k]) for n in prosumer_ids)
        hourly_exposure[k] = total_surplus * pi_bolsa[k]

    # Ganancia = ahorro por autoconsumo + ingresos por excedentes vendidos.
    # No se resta grid_cost: la comunidad seguiría comprando esa energía
    # aunque no tuviera solar — no es una pérdida del mecanismo.
    net_benefit = savings + revenues

    results_per_agent = {
        n: {
            "savings":     float(savings[n]),
            "revenues":    float(revenues[n]),
            "grid_cost":   float(grid_cost[n]),
            "net_benefit": float(net_benefit[n]),
        }
        for n in range(N)
    }

    # Métricas de riesgo
    volatility = float(np.std(pi_bolsa))
    cvar_95    = _cvar(revenues[prosumer_ids], alpha=0.05)

    return {
        "per_agent": results_per_agent,
        "aggregate": {
            "total_net_benefit":  float(np.sum(net_benefit)),
            "total_savings":      float(np.sum(savings)),
            "total_revenues":     float(np.sum(revenues)),
            "total_grid_cost":    float(np.sum(grid_cost)),
        },
        "risk": {
            "price_volatility_std": volatility,
            "cvar_95_revenues":     cvar_95,
            "hourly_exposure":      hourly_exposure,
            "max_exposure_hour":    int(np.argmax(hourly_exposure)),
        },
    }


def _cvar(values: np.ndarray, alpha: float = 0.05) -> float:
    """Conditional Value at Risk (CVaR) al nivel alpha."""
    if len(values) == 0:
        return 0.0
    sorted_v = np.sort(values)
    cutoff   = max(1, int(np.floor(alpha * len(sorted_v))))
    return float(np.mean(sorted_v[:cutoff]))


def spot_sensitivity_analysis(
    D: np.ndarray,
    G: np.ndarray,
    pi_gs: float,
    pi_bolsa_base: np.ndarray,
    prosumer_ids: list,
    consumer_ids: list,
    multipliers: list = None,
) -> dict:
    """
    Análisis de sensibilidad del escenario C3 ante variaciones de pi_bolsa.
    Útil para modelar: años normales, sequías (El Niño), techos CREG 101 066.

    multipliers: lista de factores sobre pi_bolsa_base (ej. [0.5, 1.0, 1.5, 2.0])
    """
    if multipliers is None:
        multipliers = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

    results = {}
    for m in multipliers:
        pi_bolsa_m = np.clip(pi_bolsa_base * m, 0, pi_gs)
        res = run_c3_spot(D, G, pi_gs, pi_bolsa_m, prosumer_ids, consumer_ids)
        results[m] = {
            "total_net_benefit": res["aggregate"]["total_net_benefit"],
            "total_revenues":    res["aggregate"]["total_revenues"],
            "price_volatility":  res["risk"]["price_volatility_std"],
        }

    return results
