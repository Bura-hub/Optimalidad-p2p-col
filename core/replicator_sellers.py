"""
replicator_sellers.py  (v2 — fiel al código de Sofía)
------------------------------------------------------
Implementa exactamente la dinámica de ReplicadorWjSol2 de JoinFinal.m /
Generadoresfiltro.m.

Diferencias clave respecto a versión anterior:
  1. Fitness F_Pji = R_i - H_j - lam_filt_j - bet_filt_i + BGRANDE
     donde H_j = 2*a_j*sum(P_j) + b_j  (costo MARGINAL, no derivada Lagrangiana)
     y R_i = pi_i  (precio del comprador, no función logarítmica)
  2. Filtro de paso bajo sobre los multiplicadores (no sobre P directamente)
  3. Dinámicas crudas de multiplicadores:
       Glam_j = VelGrad * lam_j * (sum_i P_ji - G_j) + 1000
       Gbet_i = VelGrad * bet_i * (sum_j P_ji - D_i) + 1000
  4. Constantes: VEL_GRAD=1e6, BGRANDE=1e6, VEL_RD=0.1  (JoinFinal.m)
"""

import numpy as np
from scipy.integrate import solve_ivp

VEL_GRAD = 1e6
BGRANDE  = 1e6
VEL_RD   = 0.1


def _sellers_ode(t, y, a, b, pi_i, simplex, J, I, D_net_i, G_net_j, tau):
    """
    Estado: [P_ji(J*I), lam_ub(J), bet_ub(I), lam_filt(J), bet_filt(I)]
    Fiel a ReplicadorWjSol2 con filtro (Generadoresfiltro.m / JoinFinal.m).
    """
    n_P = J * I
    P_flat   = y[:n_P]
    lam_ub   = y[n_P           : n_P + J]
    bet_ub   = y[n_P + J       : n_P + J + I]
    lam_filt = y[n_P + J + I   : n_P + 2*J + I]
    bet_filt = y[n_P + 2*J + I : n_P + 2*J + 2*I]

    P = P_flat.reshape(J, I)

    # Costo marginal H_j = 2*a_j*sum_i(P_ji) + b_j
    H = np.array([2.0 * a[j] * np.sum(P[j, :]) + b[j] for j in range(J)])

    # Fitness F_Pji (usa multiplicadores FILTRADOS)
    F = np.array([[pi_i[i] - H[j] - lam_filt[j] - bet_filt[i] + BGRANDE
                   for i in range(I)]
                  for j in range(J)])  # (J, I)

    # Fitness promedio
    F_bar = np.sum(P * F) / simplex if simplex > 1e-12 else 0.0

    # RD para potencias
    dP = P * VEL_RD * (F - F_bar)

    # Dinámicas crudas de multiplicadores
    Glam = np.array([VEL_GRAD * lam_ub[j] * (np.sum(P[j, :]) - G_net_j[j]) + 1000.0
                     for j in range(J)])
    Gbet = np.array([VEL_GRAD * bet_ub[i] * (np.sum(P[:, i]) - D_net_i[i]) + 1000.0
                     for i in range(I)])

    # Filtros de paso bajo
    d_lam_filt = (Glam - lam_filt) / tau
    d_bet_filt = (Gbet - bet_filt) / tau

    return np.concatenate([dP.ravel(), Glam, Gbet, d_lam_filt, d_bet_filt])


def solve_sellers(
    pi_i:        np.ndarray,
    G_net_j:     np.ndarray,
    D_net_i:     np.ndarray,
    a_j:         np.ndarray,
    b_j:         np.ndarray,
    tau:         float = 0.001,
    t_span:      tuple = (0.0, 0.01),
    n_points:    int   = 500,
    rng_seed:    int   = 42,
    return_traj: bool  = False,
    method:      str   = "LSODA",
):
    """
    Retorna P_star (J, I).
    Si return_traj=True, retorna (P_star, t_arr, P_traj) donde
      t_arr  : (n_points,)  eje de tiempo de integración
      P_traj : (J, I, n_points)  trayectoria de potencias

    method : solver ODE de scipy.integrate.solve_ivp. Default "LSODA"
        (Adams/BDF con detección automática de stiffness, análogo a ode15s
        de MATLAB en JoinFinal.m:139). Alternativas: "Radau", "BDF", "RK45".
        VelGrad=1e6 hace el sistema stiff en los multiplicadores λ/β; los
        solvers stiff-aware aceptan pasos mayores sin perder precisión.
    """
    J = len(G_net_j)
    I = len(D_net_i)
    sum_G = float(np.sum(G_net_j))
    sum_D = float(np.sum(D_net_i))
    simplex = min(sum_G, sum_D)

    if simplex < 1e-10:
        if return_traj:
            t_arr = np.linspace(t_span[0], t_span[1], n_points)
            return np.zeros((J, I)), t_arr, np.zeros((J, I, n_points))
        return np.zeros((J, I))

    # CI de P — idénticas a JoinFinal.m
    if sum_G >= sum_D:
        P0 = np.tile(D_net_i / J, (J, 1))
    else:
        P0 = np.tile(G_net_j / I, (I, 1)).T

    P0 = np.clip(P0, 1e-10, None)
    lam0 = 0.1 * np.ones(J)
    bet0 = 0.1 * np.ones(I)

    y0 = np.concatenate([P0.ravel(), lam0, bet0, np.zeros(J), np.zeros(I)])

    # t_eval sólo necesario si se requiere la trayectoria completa.
    # En modo producción (return_traj=False) solo se usa sol.y[:, -1], y el
    # solver adaptativo converge al mismo punto final sin interpolar 500 puntos.
    t_eval = np.linspace(t_span[0], t_span[1], n_points) if return_traj else None

    sol = solve_ivp(
        _sellers_ode, t_span, y0,
        args=(a_j, b_j, pi_i, simplex, J, I, D_net_i, G_net_j, tau),
        t_eval=t_eval, method=method,
        rtol=1e-6, atol=1e-9,
    )
    P_star = np.clip(sol.y[:J*I, -1].reshape(J, I), 0.0, None)

    if return_traj:
        n_actual = sol.y.shape[1]
        P_traj = np.clip(sol.y[:J*I, :], 0.0, None).reshape(J, I, n_actual)
        return P_star, sol.t, P_traj

    return P_star


def seller_welfare(P, G_j, a_j, b_j, lam_j, theta_j, pi_i) -> float:
    """W_j total (fiel a Welfarejgen de ConArtLatin.m).

    G_j[j] = excedente neto del vendedor j: G_klim[j] - D[j].
    Revenue: -sum_i P_ji/log(1+pi_i)  (alineado con Welfarei de compradores).
    """
    total = 0.0
    log_pi = np.log1p(np.asarray(pi_i, dtype=float))
    log_pi = np.where(log_pi < 1e-12, 1e-12, log_pi)   # evitar div/0
    for j in range(len(a_j)):
        sumP = float(np.sum(P[j, :]))
        revenue = -float(np.sum(P[j, :] / log_pi))
        total += (lam_j[j] * G_j[j] - theta_j[j] * G_j[j]**2
                  + revenue
                  - a_j[j] * sumP**2 - b_j[j] * sumP)
    return total
