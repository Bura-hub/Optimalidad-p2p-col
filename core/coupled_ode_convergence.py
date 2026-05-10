"""
coupled_ode_convergence.py
---------------------------
Solver acoplado tipo ``JoinFinal.m:join()`` que integra simultaneamente la
dinamica de vendedores (P_ji + multiplicadores Lagrangianos λ/β filtrados)
y compradores (π_i + filtros γ) como UN solo sistema de EDOs continuo
sobre [0, 0.01] s, usando ``scipy.integrate.solve_ivp(method='LSODA')``
(analogo a ``ode15s`` de MATLAB que usa Chacon en JoinFinal.m linea 139).

Diseñado UNICAMENTE para generar ``fig_paper_convergence`` — la metodologia
de produccion (``EMSP2P.run()`` + ``run_convergence``) usa el solver
alternante (sellers RD → buyers RD → repeat) por eficiencia. Ambos
convergen al mismo equilibrio Nash; verificable con ``equilibrium_match``.

Factores de escala (matching JoinFinal.m:160-161)
-------------------------------------------------
* En ``_rhs()`` se aplican los factores ``0.08`` al bloque de buyers
  (d_pi_all, d_gamma, d_y_filt) y ``10`` al bloque de sellers
  (dP, Glam, Gbet, d_lam_filt, d_bet_filt). Esto preserva la
  separacion temporal Stackelberg del modelo base: sellers ~125x mas
  rapidos que buyers, lo que hace que en t_span=[0, 0.01]s ambos
  alcancen el equilibrio dentro de la ventana visible y la trayectoria
  P_ji(t) muestre el transitorio (Chacon Fig 3a). Sin estos factores
  los buyers convergen en ~1ms pero los sellers apenas se mueven.
* Los factores no afectan el equilibrio (zeros del RHS son invariantes
  bajo escalado positivo); solo afectan la velocidad del transitorio.
* La inicializacion ``pi_all_0 = pi_gs*I/(I+1)`` matchea JoinFinal.m
  linea 103.

Trazabilidad: Plan 2026-05-04 — alineacion fig_paper_convergence con
JoinFinal.m. Referencias:
  - JoinFinal.m:139 (single ode15s call)
  - JoinFinal.m:146-166 (join function — RHS acoplado)
  - core/replicator_sellers.py:_sellers_ode
  - core/replicator_buyers.py:solve_buyers (Euler loop body)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from scipy.integrate import solve_ivp

from core.replicator_sellers import VEL_GRAD, BGRANDE, VEL_RD
from core.replicator_buyers import VEL_WI, VEL_GPC, PGB, PGS


@dataclass
class CoupledTrajectory:
    """Resultado del solver coupled-ODE para una hora.

    Atributos
    ---------
    t        : (n_t,) tiempo en segundos sobre [t_span[0], t_span[1]]
    pi_t     : (I, n_t) trayectoria precios reales (sin virtual player)
    P_t      : (J, I, n_t) trayectoria potencias por par (j, i)
    Wj_t     : (n_t,) welfare agregado de vendedores W_j(t) en cada t
    Wi_t     : (n_t,) welfare agregado de compradores W_i(t) en cada t
    W_t      : (n_t,) welfare total = Wj_t + Wi_t
    pi_star  : (I,) precios en steady-state (t = t_span[1])
    P_star   : (J, I) potencias en steady-state
    success  : bool, indica si el ODE termino sin error
    message  : descripcion del status del solver
    """
    t:        np.ndarray
    pi_t:     np.ndarray
    P_t:      np.ndarray
    Wj_t:     np.ndarray
    Wi_t:     np.ndarray
    W_t:      np.ndarray
    pi_star:  np.ndarray
    P_star:   np.ndarray
    success:  bool = True
    message:  str  = ""


def solve_coupled_for_hour(
    G_net_j:     np.ndarray,
    D_net_i:     np.ndarray,
    a_j:         np.ndarray,
    b_j:         np.ndarray,
    lam_j:       np.ndarray,
    theta_j:     np.ndarray,
    G_klim_i:    np.ndarray,
    lam_i:       np.ndarray,
    theta_i:     np.ndarray,
    etha_i:      np.ndarray,
    pi_gs:       float = PGS,
    pi_gb:       float = PGB,
    tau_sellers: float = 0.001,
    tau_buyers:  float = 0.01,
    t_span:      Tuple[float, float] = (0.0, 0.01),
    n_points:    int   = 500,
    method:      str   = "LSODA",
    rtol:        float = 1e-6,
    atol:        float = 1e-9,
) -> CoupledTrajectory:
    """Integra el sistema acoplado [buyer_state ; seller_state] en una sola
    llamada ``solve_ivp``, replicando estructuralmente JoinFinal.m:join().

    Parametros
    ----------
    G_net_j  : (J,) excedente neto del seller j (kW)
    D_net_i  : (I,) deficit neto del buyer i (kW)
    a_j, b_j : (J,) coeficientes costo cuadratico H_j = a_j*P^2 + b_j*P
    lam_j    : (J,) preferencia self-consumption seller (eq 7 Chacon)
    theta_j  : (J,) curvatura utilidad seller (eq 7)
    G_klim_i : (I,) generacion limite buyer (eq 14, U_i)
    lam_i    : (I,) preferencia self-consumption buyer
    theta_i  : (I,) curvatura utilidad buyer
    etha_i   : (I,) factor competencia (β_i en eq 14)
    pi_gs    : COP/kWh, precio venta a la red (limite superior π)
    pi_gb    : COP/kWh, precio compra a la red (limite inferior π)
    tau_sellers : tau filtro Lagrange (matching JoinFinal.m linea 132)
    tau_buyers  : tau3 filtro buyer (matching JoinFinal.m linea 133)
    t_span      : intervalo integracion (matching JoinFinal.m linea 128)
    n_points    : puntos t_eval (matching JoinFinal.m linea 129 = 500)
    method      : solver scipy (LSODA = stiff-aware ~ ode15s)

    Estado X (concatenado, dim total = J*I + 4*J + 3*I + 1)
    --------------------------------------------------------
    [0           : I+1                ]  pi_all (I real prices + virtual player p)
    [I+1         : I+1+J              ]  gamma  (auxiliar buyer)
    [I+1+J       : I+1+2J             ]  y_filt (filtro buyer en gamma)
    [I+1+2J      : I+1+2J+J*I         ]  P_ji (potencias, flat row-major)
    [I+1+2J+J*I  : I+1+3J+J*I         ]  lam_ub (Lagrange seller, capacity)
    [I+1+3J+J*I  : I+1+3J+J*I+I       ]  bet_ub (Lagrange seller, demand)
    [I+1+3J+J*I+I: I+1+4J+J*I+I       ]  lam_filt (filtro lam_ub)
    [I+1+4J+J*I+I: I+1+4J+J*I+2I      ]  bet_filt (filtro bet_ub)
    """
    G_net_j  = np.asarray(G_net_j,  dtype=float)
    D_net_i  = np.asarray(D_net_i,  dtype=float)
    a_j      = np.asarray(a_j,      dtype=float)
    b_j      = np.asarray(b_j,      dtype=float)
    lam_j    = np.asarray(lam_j,    dtype=float)
    theta_j  = np.asarray(theta_j,  dtype=float)
    G_klim_i = np.asarray(G_klim_i, dtype=float)
    lam_i    = np.asarray(lam_i,    dtype=float)
    theta_i  = np.asarray(theta_i,  dtype=float)
    etha_i   = np.asarray(etha_i,   dtype=float)

    J = len(G_net_j)
    I = len(D_net_i)
    sum_G = float(np.sum(G_net_j))
    sum_D = float(np.sum(D_net_i))
    simplex = min(sum_G, sum_D)

    # Caso degenerado: sin mercado P2P
    if simplex < 1e-10 or J == 0 or I == 0:
        t = np.linspace(t_span[0], t_span[1], n_points)
        return CoupledTrajectory(
            t=t,
            pi_t=np.full((I, n_points), pi_gb),
            P_t=np.zeros((J, I, n_points)),
            Wj_t=np.zeros(n_points),
            Wi_t=np.zeros(n_points),
            W_t=np.zeros(n_points),
            pi_star=np.full(I, pi_gb),
            P_star=np.zeros((J, I)),
            success=True,
            message="No P2P market (simplex < 1e-10)",
        )

    # ── Indices del estado ────────────────────────────────────
    n_pi_all = I + 1
    idx0_gamma    = n_pi_all
    idx0_yfilt    = idx0_gamma + J
    idx0_P        = idx0_yfilt + J
    idx0_lam      = idx0_P + J*I
    idx0_bet      = idx0_lam + J
    idx0_lamfilt  = idx0_bet + I
    idx0_betfilt  = idx0_lamfilt + J
    n_total       = idx0_betfilt + I

    # ── Condiciones iniciales (matching JoinFinal.m) ──────────
    simple = pi_gs * I
    pi_all_0 = np.full(n_pi_all, simple / n_pi_all)
    gamma_0  = 0.1 * np.ones(J)
    y_filt_0 = np.ones(J)

    if sum_G >= sum_D:
        P0 = np.tile(D_net_i / J, (J, 1))
    else:
        P0 = np.tile(G_net_j / I, (I, 1)).T
    P0 = np.clip(P0, 1e-10, None)

    lam_ub_0   = 0.1 * np.ones(J)
    bet_ub_0   = 0.1 * np.ones(I)
    lam_filt_0 = np.zeros(J)
    bet_filt_0 = np.zeros(I)

    X0 = np.concatenate([
        pi_all_0, gamma_0, y_filt_0,
        P0.ravel(), lam_ub_0, bet_ub_0, lam_filt_0, bet_filt_0,
    ])
    assert X0.shape[0] == n_total, "state-vector dim mismatch"

    etha_s = float(np.mean(etha_i))

    def _rhs(t: float, X: np.ndarray) -> np.ndarray:
        pi_all   = X[:n_pi_all]
        gamma    = X[idx0_gamma:idx0_yfilt]
        y_filt   = X[idx0_yfilt:idx0_P]
        P        = X[idx0_P:idx0_lam].reshape(J, I)
        lam_ub   = X[idx0_lam:idx0_bet]
        bet_ub   = X[idx0_bet:idx0_lamfilt]
        lam_filt = X[idx0_lamfilt:idx0_betfilt]
        bet_filt = X[idx0_betfilt:]

        pi_real = pi_all[:I]
        pi_p    = pi_all[I]

        sumP_i = P.sum(axis=0)   # (I,) suma sobre j
        sumP_j = P.sum(axis=1)   # (J,) suma sobre i

        # ── BUYER DYNAMICS (replicating solve_buyers loop body) ──
        pagos = -pi_gb * sumP_i / (pi_real + 1.0)
        trestris = (y_filt[:, None] * P).sum(axis=0)
        compe = etha_s * sumP_i
        dwi_real = pagos - compe + trestris
        dwi_all = np.append(dwi_real, simple - pi_p)

        pi_hat = (pi_gs - pi_all) * (-pi_gb + pi_all)
        pi_hat = np.clip(pi_hat, 1e-12, None)
        sum_ph = float(np.sum(pi_hat))
        F_bar_buyers = float(np.dot(pi_hat, dwi_all)) / sum_ph if sum_ph > 1e-14 else 0.0
        d_pi_all = pi_hat * VEL_WI * (dwi_all - F_bar_buyers)
        # Projeccion en frontera (matching solve_buyers:118 que clipea pi
        # despues de cada Euler step). Sin esto, la barrera pi_hat ~0 deja
        # pi_i flotando dentro pero no hace cumplir pi_gb estricto en la
        # presencia de ruido numerico. La proyeccion garantiza que el
        # equilibrio del solver coupled coincida con el alternante en pi_i.
        at_low_real  = (pi_all[:I] <= pi_gb + 1e-9) & (d_pi_all[:I] < 0)
        at_high_real = (pi_all[:I] >= pi_gs - 1e-9) & (d_pi_all[:I] > 0)
        d_pi_all[:I] = np.where(at_low_real | at_high_real, 0.0, d_pi_all[:I])

        re = (P * pi_real[None, :]).sum(axis=1)
        Hj_buyer = a_j * sumP_j**2 + b_j * sumP_j
        raw_gamma = VEL_GPC * gamma * (Hj_buyer - re) + 1000.0
        d_gamma = raw_gamma
        d_y_filt = (raw_gamma - y_filt) / tau_buyers

        # ── SELLER DYNAMICS (replicating _sellers_ode) ──
        H = 2.0 * a_j * sumP_j + b_j
        F = (pi_real[None, :] - H[:, None]
             - lam_filt[:, None] - bet_filt[None, :] + BGRANDE)
        F_bar_sellers = float(np.sum(P * F)) / simplex
        dP = P * VEL_RD * (F - F_bar_sellers)

        Glam = VEL_GRAD * lam_ub * (sumP_j - G_net_j) + 1000.0
        Gbet = VEL_GRAD * bet_ub * (sumP_i - D_net_i) + 1000.0
        d_lam_filt = (Glam - lam_filt) / tau_sellers
        d_bet_filt = (Gbet - bet_filt) / tau_sellers

        # Factores de escala matching JoinFinal.m:160-161:
        #   WI = 0.08 * Replicator_buyers   → 0.08 sobre bloque buyers
        #   WJ = 10   * Replicator_sellers  → 10   sobre bloque sellers
        # Equilibrio invariante (cero del RHS). Recupera transitorio
        # visible de P_ji(t) en t_span=[0, 0.01]s.
        return np.concatenate([
            0.08 * d_pi_all,    # I+1   (buyer pi)
            0.08 * d_gamma,     # J     (buyer auxiliar)
            0.08 * d_y_filt,    # J     (buyer filtro)
            10.0 * dP.ravel(),  # J*I   (seller P_ji)
            10.0 * Glam,        # J     (seller capacity multiplier)
            10.0 * Gbet,        # I     (seller demand multiplier)
            10.0 * d_lam_filt,  # J     (seller lam filtro)
            10.0 * d_bet_filt,  # I     (seller bet filtro)
        ])

    # ── Integracion ──────────────────────────────────────────
    t_eval = np.linspace(t_span[0], t_span[1], n_points)
    sol = solve_ivp(
        _rhs, t_span, X0, method=method,
        t_eval=t_eval, rtol=rtol, atol=atol,
    )

    n_t = sol.y.shape[1]
    pi_t_real = np.clip(sol.y[:I, :], pi_gb, pi_gs)
    P_t = np.clip(
        sol.y[idx0_P:idx0_lam, :].reshape(J, I, n_t),
        0.0, None,
    )

    pi_star = pi_t_real[:, -1]
    P_star  = P_t[:, :, -1]

    # ── Welfare a lo largo de la trayectoria ─────────────────
    Wj_t, Wi_t = _compute_welfare_trajectory(
        P_t=P_t, pi_t=pi_t_real,
        a_j=a_j, b_j=b_j, lam_j=lam_j, theta_j=theta_j, G_net_j=G_net_j,
        G_klim_i=G_klim_i, lam_i=lam_i, theta_i=theta_i, etha_i=etha_i,
    )
    W_t = Wj_t + Wi_t

    return CoupledTrajectory(
        t=sol.t,
        pi_t=pi_t_real,
        P_t=P_t,
        Wj_t=Wj_t,
        Wi_t=Wi_t,
        W_t=W_t,
        pi_star=pi_star,
        P_star=P_star,
        success=bool(sol.success),
        message=str(sol.message),
    )


def _compute_welfare_trajectory(
    P_t:      np.ndarray,   # (J, I, n_t)
    pi_t:     np.ndarray,   # (I, n_t)
    a_j:      np.ndarray,
    b_j:      np.ndarray,
    lam_j:    np.ndarray,
    theta_j:  np.ndarray,
    G_net_j:  np.ndarray,
    G_klim_i: np.ndarray,
    lam_i:    np.ndarray,
    theta_i:  np.ndarray,
    etha_i:   np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Welfare W_j(t), W_i(t) en cada paso t usando ``seller_welfare`` y
    ``buyer_welfare`` (formulas Chacon eqs 6, 14)."""
    from core.replicator_sellers import seller_welfare
    from core.replicator_buyers  import buyer_welfare

    J, I, n_t = P_t.shape
    Wj_t = np.zeros(n_t)
    Wi_t = np.zeros(n_t)
    for k in range(n_t):
        P_k  = P_t[:, :, k]
        pi_k = pi_t[:, k]
        Wj_t[k] = seller_welfare(P_k, G_net_j, a_j, b_j, lam_j, theta_j, pi_k)
        Wi_t[k] = buyer_welfare(pi_k, P_k, G_klim_i, lam_i, theta_i, etha_i)
    return Wj_t, Wi_t


def equilibrium_match(
    coupled:   CoupledTrajectory,
    pi_alt:    np.ndarray,    # (I,) pi_star del solver alternante
    P_alt:     np.ndarray,    # (J, I) P_star del solver alternante
    pi_tol:    float = 1.0,   # COP/kWh
    P_tol:     float = 0.01,  # kW
) -> dict:
    """Compara steady-state coupled vs alternating. Retorna dict con
    diff_pi_max, diff_P_max, y flag ``match``.

    Uso esperado: validar que el solver coupled converge al mismo
    equilibrio Nash que el solver alternante (sanity check pre-PR).
    """
    diff_pi = np.abs(coupled.pi_star - pi_alt)
    diff_P  = np.abs(coupled.P_star  - P_alt)
    return {
        "diff_pi_max":   float(diff_pi.max()),
        "diff_P_max":    float(diff_P.max()),
        "diff_pi_mean":  float(diff_pi.mean()),
        "diff_P_mean":   float(diff_P.mean()),
        "match_pi":      bool(diff_pi.max() < pi_tol),
        "match_P":       bool(diff_P.max()  < P_tol),
        "match":         bool(diff_pi.max() < pi_tol and diff_P.max() < P_tol),
    }
