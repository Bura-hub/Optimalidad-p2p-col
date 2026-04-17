"""
generate_reference_h14.py
--------------------------
Genera el caso canónico de referencia para el golden test (F2.1 de la Fase 2).

Usa el enfoque de optimización estática de Bienestar6p.py (Chacón et al., 2025)
con los parámetros del modelo base de JoinFinal.m:
  theta=0.5, lamda=100, etha=0.1, Pgs=1250, Pgb=114

Datos: perfil sintético de data/base_case_data.py, hora t=14 (índice 13).

Salida: Documentos/copy/reference_h14.json

Ejecutar UNA SOLA VEZ para generar la referencia:
    python Documentos/copy/generate_reference_h14.py

NOTA DE FIDELIDAD: las funciones de bienestar son las de Bienestar6p.py (Sofía
Chacón et al., 2025). La formulación del vendedor usa -P_ji/log(1+pi_i), mientras
que el EMS Python usa fitness lineal pi_i - H_j. Ambas convergen al mismo mercado
Nash cuando las condiciones de primer orden coinciden (ver notas_modelo_tesis.md §6).
El golden test verifica equivalencia en métricas de vaciado de mercado (clearing).
"""

import sys, os, json, warnings
warnings.filterwarnings("ignore")

# Agregar raíz del proyecto al path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np
from scipy.optimize import minimize

from core.market_prep   import compute_generation_limit, classify_agents
from data.base_case_data import (
    get_generation_profiles, get_demand_profiles, get_agent_params,
    PGS, PGB,
)

# ── Parámetros JoinFinal.m (Tabla I canónica) ───────────────────────────────
HOUR_IDX = 13   # hora 14 en 1-indexed (pico solar)
PGS_REF  = PGS  # 1250 adimensional
PGB_REF  = PGB  # 114  adimensional


# ── Funciones de bienestar (Bienestar6p.py — Chacón et al. 2025) ─────────────

def welfare_sellers(x, Gj, a_j, b_j, theta_j, lamda_j, pii, J, I, consumer, generator):
    """
    Bienestar agregado de vendedores — formulación log-precio de Bienestar6p.py.

    W_j = λ_j·G_j - θ_j·G_j² - Σ_i P_ji/log(1+|π_i|) - a_j·(ΣP_ji)² - b_j·ΣP_ji

    Retorna -ΣW_j (negativo para minimización con scipy.optimize).
    x es el vector aplanado P_ij de tamaño J×I.
    """
    Pij = x.reshape((J, I))
    Wj = [
        lamda_j[j] * Gj[j]
        - theta_j[j] * Gj[j]**2
        - sum(Pij[j][i] / (np.log(1.0 + abs(pii[i])) + 1e-12) for i in consumer)
        - a_j[j] * (sum(Pij[j][i] for i in consumer)**2)
        - b_j[j] * sum(Pij[j][i] for i in consumer)
        for j in generator
    ]
    return -sum(Wj)


def welfare_buyers(x, Pij_mat, J, I, consumer, generator, etha_i, lamda_i, Gi, theta_i):
    """
    Bienestar agregado de compradores — formulación log-precio de Bienestar6p.py.

    W_i = λ_i·G_i - θ_i·G_i² + (Σ_j P_ji)/log(|π_i|+1) - η_i·compe_i
    donde compe_i = Σ_{k≠i} π_k · (Σ_j P_jk) es la presión competitiva.

    x es el vector de precios π_i de tamaño I.
    Retorna -ΣW_i (negativo para minimización con scipy.optimize).
    """
    pii = x
    mat = np.ones((I, I))
    np.fill_diagonal(mat, 0)
    compe = [
        sum(mat[i][k] * pii[k] * sum(Pij_mat[j][i] for j in generator)
            for k in consumer)
        for i in consumer
    ]
    Wi = [
        lamda_i[i] * Gi[i]
        - theta_i[i] * Gi[i]**2
        + sum(Pij_mat[j][i] for j in generator) / (np.log(abs(pii[i]) + 1.0) + 1e-12)
        - compe[i] * etha_i[i]
        for i in consumer
    ]
    return -sum(Wi)


def _solve_sellers(pii, Gj, Di, a_j, b_j, theta_j, lamda_j, J, I, Pgs, Pgb):
    """
    Optimiza la asignación P_ij de vendedores dado el vector de precios pii.

    Usa trust-constr (scipy) con restricciones:
      - P_ji >= 0  (bounds)
      - Σ_i P_ji <= Gj[j]  para cada vendedor (límite de oferta)
      - Σ_j P_ji <= Di[i]  para cada comprador (límite de demanda)
      - Cierre: si ΣGj <= ΣDi → toda la oferta se coloca (eq. total);
                si ΣDi <  ΣGj → toda la demanda se cubre (eq. por comprador)

    Retorna (P_ij: ndarray J×I, W_total: float).
    """
    consumer  = range(I)
    generator = range(J)
    sli0   = np.zeros(J * I)
    bounds = [(0.0, 1000.0 * Gj[j]) for _ in consumer for j in generator]

    # Restricciones de oferta (Gj[j] límite) y demanda (Di[i] límite)
    sum_Di = sum(Di)
    sum_Gj = sum(Gj)

    cons = []
    # suma de P_ji <= Gj[j] para cada vendedor j
    for j in generator:
        def _ub_gen(x, _j=j):
            Pij = x.reshape((J, I))
            return Gj[_j] - sum(Pij[_j][i] for i in consumer)
        cons.append({"type": "ineq", "fun": _ub_gen})

    # suma de P_ji <= Di[i] para cada comprador i (si demanda > oferta)
    for i in consumer:
        def _ub_dem(x, _i=i):
            Pij = x.reshape((J, I))
            return Di[_i] - sum(Pij[j][_i] for j in generator)
        cons.append({"type": "ineq", "fun": _ub_dem})

    # restricción de cierre de mercado
    if sum_Di >= sum_Gj:
        # toda la generación debe colocarse
        def _close(x):
            Pij = x.reshape((J, I))
            return np.sum(Pij) - sum_Gj
        cons.append({"type": "eq", "fun": _close})
    else:
        # toda la demanda debe cubrirse
        for i in consumer:
            def _close_i(x, _i=i):
                Pij = x.reshape((J, I))
                return sum(Pij[j][_i] for j in generator) - Di[_i]
            cons.append({"type": "eq", "fun": _close_i})

    sol = minimize(
        welfare_sellers, sli0, method="trust-constr",
        bounds=bounds, constraints=cons,
        args=(Gj, a_j, b_j, theta_j, lamda_j, pii, J, I, consumer, generator),
        options={"maxiter": 500, "gtol": 1e-8},
    )
    return sol.x.reshape((J, I)), -sol.fun


def _solve_buyers(Pij_mat, Gi, etha_i, lamda_i, theta_i, J, I, Pgs, Pgb, a_j, b_j):
    """
    Optimiza el vector de precios pii de compradores dada la asignación P_ij.

    Usa SLSQP (scipy) con bounds [Pgb, Pgs] y restricciones de rentabilidad
    del vendedor: ingresos_j >= costos_j para cada j (una restricción por vendedor).

    Retorna (pii: ndarray I, W_total: float), con pii clipeado a [Pgb, Pgs].
    """
    consumer  = range(I)
    generator = range(J)
    pii0   = np.full(I, Pgb)
    bounds = [(Pgb, Pgs) for _ in consumer]

    # Restricción de rentabilidad del vendedor (costos <= ingresos)
    def _vendor_profit(x, _j=0):
        pii = x
        cost = a_j[_j] * (sum(Pij_mat[_j][i] for i in consumer)**2) \
               + b_j[_j] * sum(Pij_mat[_j][i] for i in consumer)
        rev  = sum(pii[i] * Pij_mat[_j][i] for i in consumer)
        return rev - cost

    cons = [{"type": "ineq", "fun": _vendor_profit, "args": ()}]
    # Solo aplicamos la restricción al vendedor 0 (representativo)
    # para no sobre-restringir (Bienestar6p.py usa un constraint por vendedor)
    for j_idx in range(J):
        def _vp(x, _j=j_idx):
            pii = x
            cost = a_j[_j] * (sum(Pij_mat[_j][i] for i in consumer)**2) \
                   + b_j[_j] * sum(Pij_mat[_j][i] for i in consumer)
            rev  = sum(pii[i] * Pij_mat[_j][i] for i in consumer)
            return rev - cost
        cons.append({"type": "ineq", "fun": _vp})

    sol = minimize(
        welfare_buyers, pii0, method="SLSQP",
        bounds=bounds, constraints=cons,
        args=(Pij_mat, J, I, consumer, generator, etha_i, lamda_i, Gi, theta_i),
        tol=1e-8,
        options={"maxiter": 500},
    )
    return np.clip(sol.x, Pgb, Pgs), -sol.fun


def generate(out_path: str = None, verbose: bool = True) -> dict:
    """
    Genera el oráculo de referencia SLSQP para hora t=14 (índice 13).

    Ejecuta el loop Stackelberg estático (≤10 iter.) alternando _solve_sellers
    y _solve_buyers con los parámetros canónicos de JoinFinal.m. Guarda el
    resultado en out_path (o Documentos/copy/reference_h14.json por defecto).

    Parámetros
    ----------
    out_path : str, opcional — ruta de salida del JSON
    verbose  : bool — imprime progreso por iteración

    Retorna dict con P_ij, pi_i, P_total, pi_mean, W_total y métricas auxiliares.
    """
    # ── Datos canónicos ───────────────────────────────────────────────────────
    G    = get_generation_profiles()
    D    = get_demand_profiles()
    p    = get_agent_params()
    k    = HOUR_IDX

    G_klim = compute_generation_limit(G[:, k], p["a"], p["b"], p["c"], PGS_REF)
    _, sids, bids = classify_agents(G_klim, D[:, k])

    if len(sids) == 0 or len(bids) == 0:
        raise RuntimeError(f"Hora {k+1} no tiene vendedores y/o compradores — "
                           "elige otra hora para el golden test.")

    J = len(sids); I = len(bids)
    consumer  = range(I)
    generator = range(J)

    Gj     = np.array([G_klim[j] - D[j, k] for j in sids])
    Di     = np.array([D[i, k] - G_klim[i] for i in bids])
    Gi     = G_klim[bids]

    a_j    = p["a"][sids];   b_j    = p["b"][sids]
    theta_j = p["theta"][sids]; lamda_j = p["lam"][sids]
    theta_i = p["theta"][bids]; lamda_i = p["lam"][bids]
    etha_i  = p["etha"][bids]

    pii   = np.full(I, PGB_REF)
    Pij   = (np.tile(Di / J, (J, 1)) if np.sum(Gj) >= np.sum(Di)
             else np.tile(Gj / I, (I, 1)).T)
    Pij   = np.clip(Pij, 1e-10, None)

    if verbose:
        print(f"Hora {k+1} | J={J} vendedores: {[s+1 for s in sids]}, I={I} compradores: {[b+1 for b in bids]}")
        print(f"  Gj={Gj.round(4)}, Di={Di.round(4)}")
        print(f"  PGS={PGS_REF}, PGB={PGB_REF}")

    W_prev = -np.inf
    for it in range(10):
        Pij_new, Wj = _solve_sellers(pii, Gj, Di, a_j, b_j, theta_j, lamda_j, J, I, PGS_REF, PGB_REF)
        pii_new, Wi = _solve_buyers(Pij_new, Gi, etha_i, lamda_i, theta_i, J, I, PGS_REF, PGB_REF, a_j, b_j)
        W_total = Wj + Wi
        if verbose:
            print(f"  Iter {it+1:2d}: W={W_total:.4f}  pi_mean={pii_new.mean():.2f}  "
                  f"P_total={Pij_new.sum():.4f}")
        Pij   = Pij_new
        pii   = np.clip(pii_new, PGB_REF, PGS_REF)
        if W_total >= W_prev and it >= 2:
            break
        W_prev = W_total

    # ── Validar restricciones ──────────────────────────────────────────────
    supply_err  = [abs(Pij[j, :].sum() - Gj[j]) for j in generator]
    demand_err  = [abs(Pij[:, i].sum() - Di[i]) for i in consumer]
    if verbose:
        print(f"\n  Error suministro: max={max(supply_err):.6f} kW")
        print(f"  Error demanda:    max={max(demand_err):.6f} kW")
        print(f"  pi_i = {pii.round(2)}")
        print(f"  P_ij (J×I):")
        print(Pij.round(4))

    # ── Serializar ────────────────────────────────────────────────────────
    ref = {
        "hour_idx": k,
        "pgs": PGS_REF,
        "pgb": PGB_REF,
        "seller_ids": [int(s) for s in sids],
        "buyer_ids":  [int(b) for b in bids],
        "G_net_j":    Gj.tolist(),
        "D_net_i":    Di.tolist(),
        "P_ij":       Pij.tolist(),       # J × I
        "pi_i":       pii.tolist(),       # I
        "P_total":    float(Pij.sum()),
        "pi_mean":    float(pii.mean()),
        "W_total":    float(W_total),
        "supply_sum": float(Pij.sum(axis=1).sum()),
        "demand_sum": float(Pij.sum(axis=0).sum()),
    }

    if out_path is None:
        out_path = os.path.join(os.path.dirname(__file__), "reference_h14.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ref, f, indent=2)
    print(f"\nReferencia guardada en: {out_path}")
    return ref


if __name__ == "__main__":
    generate(verbose=True)
