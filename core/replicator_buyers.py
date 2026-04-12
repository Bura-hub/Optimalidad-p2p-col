"""
replicator_buyers.py  (v3)
--------------------------
Fiel a ReplicadorWiSol2 de JoinFinal.m con integración numérica estable.

El problema del comprador en JoinFinal.m usa escalas muy diferentes
(VelWi=0.1, VelGPC=1e5) que generan sistemas stiff. Se usa Euler
explícito con paso fijo pequeño como en el solver ode15s de MATLAB,
que maneja bien sistemas stiff.
"""

import numpy as np

VEL_WI  = 0.1
VEL_GPC = 1e5
PGB     = 114.0
PGS     = 1250.0


def solve_buyers(
    P_mat:       np.ndarray,   # (J, I)
    a_j:         np.ndarray,
    b_j:         np.ndarray,
    etha_i:      np.ndarray,   # (I,)
    pi_gs:       float = PGS,
    pi_gb:       float = PGB,
    tau:         float = 0.001,
    t_span:      tuple = (0.0, 0.01),
    n_points:    int   = 500,
    return_traj: bool  = False,
):
    """
    Resuelve la dinámica de compradores con Euler implícito
    (equivalente a ode15s de MATLAB para sistemas stiff).
    Retorna pi_star (I,).
    Si return_traj=True, retorna (pi_star, t_arr, pi_traj) donde
      t_arr   : (n_points,)  eje de tiempo
      pi_traj : (I, n_points)  trayectoria de precios de compradores reales
    """
    J, I  = P_mat.shape
    simple = pi_gs * I

    # ---- Condiciones iniciales (JoinFinal.m) ----
    pi_all   = np.full(I + 1, simple / (I + 1))   # incluye jugador virtual
    gamma    = 0.1 * np.ones(J)
    y_filt   = np.ones(J)

    dt = (t_span[1] - t_span[0]) / n_points
    etha_s = float(np.mean(etha_i))
    t0 = t_span[0]

    if return_traj:
        pi_history = np.zeros((I, n_points))
        t_arr      = np.zeros(n_points)

    for step in range(n_points):
        pi_real = pi_all[:I]
        pi_p    = pi_all[I]

        # Suma de potencias recibidas por cada comprador
        sum_Pji = np.array([float(np.sum(P_mat[:, i])) for i in range(I)])

        # pagos = -Pgb * sum_Pji / (pi_i + 1)
        pagos = -pi_gb * sum_Pji / (pi_real + 1.0)

        # trestris = sum_j(y_filt_j * P_ji)  ← señal de costo filtrada
        trestris = np.array([float(np.dot(y_filt, P_mat[:, i])) for i in range(I)])

        # competencia: -etha * sum_Pji
        compe = etha_s * sum_Pji

        # fitness compradores reales
        dwi = pagos - compe + trestris

        # jugador virtual
        dwi_all = np.append(dwi, 1.0 * (simple - pi_p))

        # pi_hat = (Pgs - pi) * (-Pgb + pi)
        pi_hat = (pi_gs - pi_all) * (-pi_gb + pi_all)
        pi_hat = np.clip(pi_hat, 1e-12, None)

        # fitness promedio
        sum_ph = float(np.sum(pi_hat))
        F_bar  = float(np.dot(pi_hat, dwi_all)) / sum_ph if sum_ph > 1e-14 else 0.0

        # dpi
        d_pi = pi_hat * VEL_WI * (dwi_all - F_bar)
        pi_all = pi_all + dt * d_pi
        pi_all = np.clip(pi_all, pi_gb, pi_gs)

        # ingresos y costos por generador
        re = np.array([float(np.dot(pi_all[:I], P_mat[j, :])) for j in range(J)])
        Hj = np.array([a_j[j] * float(np.sum(P_mat[j, :]))**2
                       + b_j[j] * float(np.sum(P_mat[j, :])) for j in range(J)])

        # dinámica gamma
        raw_gamma = VEL_GPC * gamma * (Hj - re) + 1000.0
        gamma = gamma + dt * raw_gamma
        gamma = np.clip(gamma, 0.0, 1e8)

        # filtro
        d_filt = (raw_gamma - y_filt) / tau
        y_filt = y_filt + dt * d_filt

        if return_traj:
            pi_history[:, step] = np.clip(pi_all[:I], pi_gb, pi_gs)
            t_arr[step] = t0 + (step + 1) * dt

    pi_star = np.clip(pi_all[:I], pi_gb, pi_gs)

    if return_traj:
        return pi_star, t_arr, pi_history

    return pi_star


def buyer_welfare(pi_i, P_mat, G_klim_i, lam_i, theta_i, etha_i) -> float:
    """
    W_i total (fiel a Welfarei de Bienestar6p.py):
    Wi = lam*Gi - theta*Gi^2 + sum_j(P_ji)/log(|pi_i|+1) - etha*compe
    """
    I = len(pi_i)
    J = P_mat.shape[0]
    matriz = np.ones((I, I)) - np.eye(I)
    compe = [sum(matriz[i][k] * pi_i[k] * float(np.sum(P_mat[:, k]))
                 for k in range(I))
             for i in range(I)]
    Wi = [
        lam_i[i] * G_klim_i[i] - theta_i[i] * G_klim_i[i]**2
        + float(np.sum(P_mat[:, i])) / (np.log(abs(pi_i[i]) + 1) + 1e-12)
        - compe[i] * etha_i[i]
        for i in range(I)
    ]
    return sum(Wi)
