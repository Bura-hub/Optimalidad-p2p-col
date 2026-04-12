"""
settlement.py  (v3 — SS unificada)
------------------------------------
Liquidación residual y métricas de desempeño.

CORRECCIÓN v3 — Métrica SS unificada (punto 3 de "qué sigue"):
  Versión anterior: SS_P2P = sum(P_star) / G_total
    Solo contaba energía intercambiada en mercado, ignoraba autoconsumo.
  
  Versión nueva: SS = (autoconsumo_local + intercambio_P2P) / G_total
    Alineada con la definición de C1–C4, permite comparación equitativa.
    
  SS_P2P_total(k) = [sum_n min(G_klim_n, D_n) + sum(P_star)] / sum(G_klim)
"""

import numpy as np


def residual_settlement(
    P_star:     np.ndarray,
    G_net_j:    np.ndarray,
    D_net_i:    np.ndarray,
    G_klim_k:   np.ndarray,
    D_star_k:   np.ndarray,
    pi_gs:      float,
    pi_gb:      float,
    seller_ids: list,
    buyer_ids:  list,
) -> dict:
    J, I = P_star.shape
    P_ext = np.array([max(0.0, G_net_j[j] - float(np.sum(P_star[j, :])))
                      for j in range(J)])
    P_int = np.array([max(0.0, D_net_i[i] - float(np.sum(P_star[:, i])))
                      for i in range(I)])
    return {
        "P_int":               P_int,
        "P_ext":               P_ext,
        "cost_grid_purchases": float(np.sum(P_int)) * pi_gs,
        "revenue_grid_sales":  float(np.sum(P_ext)) * pi_gb,
    }


def self_consumption_index(P_star, D_k, G_klim_k=None) -> float:
    """
    SC = (autoconsumo_local + intercambio_P2P) / D_total
    Si G_klim_k se provee, incluye el autoconsumo local de cada nodo.
    """
    p2p_energy = float(np.sum(P_star))
    if G_klim_k is not None:
        N = len(G_klim_k)
        D_arr = D_k if hasattr(D_k, '__len__') else np.array([D_k])
        G_arr = G_klim_k
        autoconsumo = float(np.sum(np.minimum(
            np.maximum(G_arr, 0), np.maximum(D_arr, 0))))
        numerator = autoconsumo + p2p_energy
    else:
        numerator = p2p_energy
    denom = float(np.sum(np.maximum(D_k, 0)))
    return numerator / denom if denom > 1e-10 else 0.0


def self_sufficiency_index(P_star, G_klim_k, D_k=None) -> float:
    """
    SS = (autoconsumo_local + intercambio_P2P) / G_total
    Incluye autoconsumo para ser comparable con C1–C4 (punto 3).
    """
    p2p_energy = float(np.sum(P_star))
    G_arr = np.maximum(G_klim_k, 0)

    if D_k is not None:
        D_arr = np.maximum(D_k if hasattr(D_k,'__len__') else np.array([D_k]), 0)
        autoconsumo = float(np.sum(np.minimum(G_arr, D_arr)))
        numerator   = autoconsumo + p2p_energy
    else:
        numerator = p2p_energy

    denom = float(np.sum(G_arr))
    return numerator / denom if denom > 1e-10 else 0.0


def compute_savings(P_star, pi_star, pi_gs, pi_gb):
    I = len(pi_star); J = P_star.shape[0]
    S_i  = np.array([(pi_gs - pi_star[i]) * float(np.sum(P_star[:, i]))
                     for i in range(I)])
    SR_j = np.array([float(np.sum((pi_star - pi_gb) * P_star[j, :]))
                     for j in range(J)])
    return S_i, SR_j


def equity_index(S_i, SR_j) -> float:
    num   = float(np.sum(S_i) - np.sum(SR_j))
    denom = float(np.sum(S_i) + np.sum(SR_j))
    return num / denom if abs(denom) > 1e-12 else 0.0


def welfare_distribution(S_i, SR_j) -> dict:
    total = float(np.sum(S_i) + np.sum(SR_j))
    if total < 1e-12:
        return {"PS": 50.0, "PSR": 50.0}
    return {"PS":  100.0 * float(np.sum(S_i))  / total,
            "PSR": 100.0 * float(np.sum(SR_j)) / total}


def gini_index(values: np.ndarray) -> float:
    """
    Coeficiente de Gini sobre beneficios netos por agente.

    Mide la desigualdad en la distribución del beneficio económico
    entre los N agentes de la comunidad energética.

    Rango: [0, 1]
      0 → distribución perfectamente igualitaria (todos ganan lo mismo)
      1 → máxima desigualdad (un agente captura todo el beneficio)

    Referencia: propuesta de tesis §VI.C, Nivel 2 — Equidad.
    Se evalúa sobre valores absolutos para capturar dispersión incluyendo
    agentes con beneficio cero (consumidores puros sin PV).

    Parámetro
    ---------
    values : (N,)  beneficio neto por agente [$/período]
    """
    v = np.abs(np.asarray(values, dtype=float))
    v = np.sort(v)
    n = len(v)
    if n == 0 or np.sum(v) < 1e-12:
        return 0.0
    # Fórmula: G = (2 Σ i·v_i) / (n Σ v_i) − (n+1)/n
    idx  = np.arange(1, n + 1)
    gini = (2.0 * np.dot(idx, v)) / (n * np.sum(v)) - (n + 1.0) / n
    return float(np.clip(gini, 0.0, 1.0))
