"""
settlement.py  (v2)
-------------------
Liquidación residual y métricas de desempeño.
Fiel al cálculo de Pext / Pint de Bienestar6p.py (líneas 405-406)
y a las métricas SS, SC, IE definidas en el modelo base.
"""

import numpy as np


def residual_settlement(
    P_star:     np.ndarray,   # (J, I)
    G_net_j:    np.ndarray,   # (J,)
    D_net_i:    np.ndarray,   # (I,)
    G_klim_k:   np.ndarray,   # (N,) toda la comunidad
    D_star_k:   np.ndarray,   # (N,) toda la comunidad
    pi_gs:      float,
    pi_gb:      float,
    seller_ids: list,
    buyer_ids:  list,
) -> dict:
    """
    Pext_j = G_j - sum_i P_ji   (excedente vendido a la red)
    Pint_i = D_i - sum_j P_ji   (déficit comprado a la red)

    Fiel a dffinal['Pext'] y dffinal['Pint'] en Bienestar6p.py.
    """
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


def self_consumption_index(P_star, D_total) -> float:
    denom = float(np.sum(D_total))
    return float(np.sum(P_star)) / denom if denom > 1e-10 else 0.0


def self_sufficiency_index(P_star, G_total) -> float:
    denom = float(np.sum(G_total))
    return float(np.sum(P_star)) / denom if denom > 1e-10 else 0.0


def compute_savings(P_star, pi_star, pi_gs, pi_gb):
    """
    S_i  = (pi_gs - pi_i) * sum_j P_ji   ahorro comprador
    SR_j = sum_i (pi_i - pi_gb) * P_ji   recompensa extra vendedor
    """
    I = len(pi_star)
    J = P_star.shape[0]
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
