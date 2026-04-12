"""
dr_program.py  — Programa de Respuesta a la Demanda (DR)
---------------------------------------------------------
Implementa los pasos 15-22 del Algoritmo 1 del modelo base de Chacón et al. (2025).

Referencia: §III-A "Deployment of the DR Program" y ecuaciones (2)-(5):

  U_k = ln(1 + Σ_{n∈N} D_k^n)                              (utilidad comunitaria)

  W_k = U_k - π_k × (Σ_{n∈N} D_k^n - Σ_{n∈N} G_{k_lim}^n) (bienestar neto)

  max  Σ_{k∈T} W_k                                           (problema DR, ec. 5)
  {Dv_k^n}

  sujeto a:
    D_k^n = D_k^{0n} + Dv_k^n                               (demanda total, ec. 2)
    0 ≤ Dv_k^n                                               (no negativo si flexible)
    |Dv_k^n| ≤ α_n × D_k^{0n}                               (límite de flexibilidad)
    Σ_{k∈T} Dv_k^n = 0   ∀n                                 (conservación)

Uso:
    from core.dr_program import run_dr_program

    D_star = run_dr_program(D0, G_klim, pi_k, alpha)
    # D_star es (N, T) — demanda óptima post-DR

    Si alpha es todo ceros (datos reales sin flexibilidad):
        D_star == D0  (sin cambio, comportamiento por defecto)

Implementación:
    Se resuelve con SLSQP (Sequential Least Squares Programming) de scipy,
    que es el método descrito en el artículo base (paso 21 del Algoritmo 1).
"""

from __future__ import annotations
import numpy as np
from typing import Optional

try:
    from scipy.optimize import minimize, LinearConstraint, Bounds
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


# ─────────────────────────────────────────────────────────────────────────────
# Función principal
# ─────────────────────────────────────────────────────────────────────────────

def run_dr_program(
    D0:     np.ndarray,          # (N, T)  demanda base (medida)
    G_klim: np.ndarray,          # (N, T)  límites de generación pre-calculados
    pi_k:   np.ndarray,          # (T,)    señal de precio del P2PMO [$/kWh]
    alpha:  np.ndarray,          # (N,)    fracción de demanda flexible [0, 1]
    verbose: bool = False,
) -> np.ndarray:
    """
    Calcula la demanda óptima D_k^{n*} maximizando Σ_k W_k.

    Para alpha=0 (o todos ceros): retorna D0 sin modificar.
    Para alpha>0: desplaza hasta α_n × D0_kn en cada periodo.

    Returns
    -------
    D_star : (N, T)  demanda óptima tras el programa DR
    """
    N, T = D0.shape
    alpha = np.asarray(alpha, dtype=float)

    # Caso trivial: sin flexibilidad → D_star = D0
    if np.all(alpha < 1e-9):
        return D0.copy()

    if not _HAS_SCIPY:
        raise ImportError(
            "scipy no está instalado. Instalar con: pip install scipy\n"
            "Sin scipy el programa DR no puede ejecutarse."
        )

    # ── Construcción del problema de optimización ────────────────────────────
    # Variables de decisión: x = Dv (N×T), aplanado por filas.
    # x[n*T + k] = Dv_k^n

    # Bounds: -alpha_n * D0_kn ≤ x_nk ≤ alpha_n * D0_kn
    lb = np.zeros(N * T)
    ub = np.zeros(N * T)
    for n in range(N):
        for k in range(T):
            slack = alpha[n] * max(float(D0[n, k]), 0.0)
            lb[n * T + k] = -slack
            ub[n * T + k] =  slack

    bounds = Bounds(lb, ub)

    # Restricciones de igualdad: Σ_k Dv_k^n = 0  para cada n
    # A_eq (N, N*T): A_eq[n, n*T:n*T+T] = 1
    A_eq = np.zeros((N, N * T))
    for n in range(N):
        A_eq[n, n * T : n * T + T] = 1.0
    b_eq = np.zeros(N)
    lin_constraint = LinearConstraint(A_eq, lb=b_eq, ub=b_eq)

    # ── Función objetivo (negativa para minimización) ─────────────────────────
    pi_arr = np.asarray(pi_k, dtype=float)  # (T,)

    def _neg_welfare(x: np.ndarray) -> float:
        Dv = x.reshape(N, T)
        D  = D0 + Dv                          # (N, T) demanda total
        D_sum = np.sum(D, axis=0)              # (T,)  Σ_n D_k^n
        G_sum = np.sum(G_klim, axis=0)         # (T,)  Σ_n G_klim_k^n

        # W_k = ln(1 + D_sum_k) - π_k × (D_sum_k - G_sum_k)
        W = np.log1p(np.maximum(D_sum, 0.0)) - pi_arr * (D_sum - G_sum)
        return -float(np.sum(W))

    def _grad(x: np.ndarray) -> np.ndarray:
        Dv = x.reshape(N, T)
        D  = D0 + Dv
        D_sum = np.maximum(np.sum(D, axis=0), 0.0)   # (T,)

        # ∂W_k/∂Dv_kn = 1/(1 + D_sum_k) - π_k   (igual para todos n)
        dW_dDsum = 1.0 / (1.0 + D_sum) - pi_arr      # (T,)

        # Gradiente negativo (minimizamos -W)
        grad = np.zeros(N * T)
        for n in range(N):
            grad[n * T : n * T + T] = -dW_dDsum
        return grad

    # ── Punto inicial: sin desplazamiento ────────────────────────────────────
    x0 = np.zeros(N * T)

    # ── Optimización SLSQP ───────────────────────────────────────────────────
    result = minimize(
        _neg_welfare, x0,
        jac=_grad,
        method="SLSQP",
        bounds=bounds,
        constraints=[{"type": "eq",
                      "fun":  lambda x: A_eq @ x,
                      "jac":  lambda x: A_eq}],
        options={"ftol": 1e-9, "maxiter": 500, "disp": False},
    )

    if verbose:
        status = "OK" if result.success else f"WARN: {result.message}"
        W_base = -_neg_welfare(x0)
        W_opt  = -result.fun
        print(f"    DR [{status}]  W_base={W_base:.4f}  W_opt={W_opt:.4f}  "
              f"ΔW={W_opt - W_base:+.4f}  iters={result.nit}")

    Dv_star = result.x.reshape(N, T)
    D_star  = np.maximum(D0 + Dv_star, 0.0)   # demanda siempre ≥ 0
    return D_star


# ─────────────────────────────────────────────────────────────────────────────
# Señal de precio sugerida para el P2PMO
# ─────────────────────────────────────────────────────────────────────────────

def compute_price_signal(
    D0:     np.ndarray,     # (N, T)
    G_klim: np.ndarray,     # (N, T)
    pi_gs:  float,
    pi_gb:  float,
) -> np.ndarray:
    """
    Señal de precio π_k para el programa DR (fijada por el P2PMO).

    Heurística basada en balance comunitario:
      - Si ΣG_k > ΣD_k (surplus):  π_k = π_gb  (precio compra red)
      - Si ΣG_k < ΣD_k (déficit):  π_k = π_gs  (precio venta red)
      - Interpolación lineal en la zona de transición.

    Esta señal incentiva desplazar demanda hacia horas de surplus solar.
    """
    D_sum = np.sum(D0, axis=0)       # (T,)
    G_sum = np.sum(G_klim, axis=0)   # (T,)
    ratio = np.where(D_sum > 1e-9, G_sum / D_sum, 0.0)   # GDR comunitario

    # Interpolación: ratio=0 → pi_gs,  ratio≥1 → pi_gb
    ratio_clipped = np.clip(ratio, 0.0, 1.0)
    pi_k = pi_gs + ratio_clipped * (pi_gb - pi_gs)
    return pi_k


# ─────────────────────────────────────────────────────────────────────────────
# Reporte de impacto del DR
# ─────────────────────────────────────────────────────────────────────────────

def dr_impact_report(
    D0:     np.ndarray,
    D_star: np.ndarray,
    G_klim: np.ndarray,
    agent_names: Optional[list] = None,
) -> dict:
    """
    Calcula métricas de impacto del programa DR.

    Retorna dict con:
      shift_total_kwh : kWh totales desplazados (|Dv|)
      shift_pct       : fracción de demanda modificada (%)
      sc_before       : SC sin DR
      sc_after        : SC con DR
      ss_before       : SS sin DR
      ss_after        : SS con DR
      per_agent       : dict por agente
    """
    N, T = D0.shape
    Dv = D_star - D0

    shift_total = float(np.sum(np.abs(Dv)))
    shift_pct   = shift_total / max(float(np.sum(D0)), 1e-9) * 100.0

    def _sc(D, G):
        used  = float(np.sum(np.minimum(np.maximum(G, 0), np.maximum(D, 0))))
        total = float(np.sum(np.maximum(D, 0)))
        return used / total if total > 1e-9 else 0.0

    def _ss(D, G):
        used = float(np.sum(np.minimum(np.maximum(G, 0), np.maximum(D, 0))))
        gen  = float(np.sum(np.maximum(G, 0)))
        return used / gen if gen > 1e-9 else 0.0

    per_agent = {}
    for n in range(N):
        name = agent_names[n] if agent_names and n < len(agent_names) else f"A{n+1}"
        per_agent[name] = {
            "shift_kwh": float(np.sum(np.abs(Dv[n, :]))),
            "D_mean_before": float(np.mean(D0[n, :])),
            "D_mean_after":  float(np.mean(D_star[n, :])),
        }

    return {
        "shift_total_kwh": shift_total,
        "shift_pct":       shift_pct,
        "sc_before":       _sc(D0,     G_klim),
        "sc_after":        _sc(D_star, G_klim),
        "ss_before":       _ss(D0,     G_klim),
        "ss_after":        _ss(D_star, G_klim),
        "per_agent":       per_agent,
    }
