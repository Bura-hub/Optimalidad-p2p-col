"""
comparison_engine.py  (v2 — sin DR)
------------------------------------
Motor de comparación cuantitativa del Objetivo 3 de la tesis.

La demanda D es un insumo fijo (datos reales de la comunidad).
Todos los escenarios C1–C4 y el P2P operan sobre los mismos
perfiles D y G_klim, garantizando comparación equitativa.

Dos niveles de métricas (propuesta tesis):
  Nivel 1 — Monetario: ganancias económicas netas
  Nivel 2 — Bienestar: IE, Price of Fairness, SC, SS, autosuficiencia
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from .scenario_c1_creg174    import run_c1_creg174
from .scenario_c2_bilateral  import run_c2_bilateral
from .scenario_c3_spot       import run_c3_spot
from .scenario_c4_creg101072 import (
    run_c4_creg101072, compute_pde_weights, static_spread_c4_vs_p2p,
)


@dataclass
class ComparisonResult:
    net_benefit:           dict  = field(default_factory=dict)
    net_benefit_per_agent: dict  = field(default_factory=dict)
    equity_index:          dict  = field(default_factory=dict)
    self_sufficiency:      dict  = field(default_factory=dict)
    self_consumption:      dict  = field(default_factory=dict)
    price_of_fairness:     Optional[float]      = None
    static_spread_24h:     Optional[np.ndarray] = None
    hours:     int   = 24
    n_agents:  int   = 6
    pi_ppa:    float = 0.0
    pde:       Optional[np.ndarray] = None


def run_comparison(
    D:            np.ndarray,       # (N, T) demanda real FIJA
    G_klim:       np.ndarray,       # (N, T) límite de generación (pre-calc.)
    G_raw:        np.ndarray,       # (N, T) generación bruta original
    p2p_results:  list,
    pi_gs:        float,
    pi_gb:        float,
    pi_bolsa:     np.ndarray,       # (T,) precio de bolsa horario
    prosumer_ids: list,
    consumer_ids: list,
    pde:          Optional[np.ndarray] = None,
    pi_ppa:       Optional[float]      = None,
    capacity:     Optional[np.ndarray] = None,
) -> ComparisonResult:
    """
    Todos los escenarios operan sobre D (real, fijo) y G_klim.
    """
    N, T = D.shape
    cr   = ComparisonResult(hours=T, n_agents=N)

    # Valores por defecto
    if pde is None:
        cap = np.maximum(np.mean(G_raw, axis=1), 0)
        pde = compute_pde_weights(cap)
    cr.pde = pde

    if pi_ppa is None:
        pi_ppa = pi_gb + 0.5 * (pi_gs - pi_gb)
    cr.pi_ppa = pi_ppa

    # ── C1 ──────────────────────────────────────────────────────────────
    c1 = run_c1_creg174(D, G_klim, pi_gs, pi_bolsa, prosumer_ids)
    c1_net = np.array([c1[n]["net_benefit"] if n in c1 else 0.0
                       for n in range(N)])
    cr.net_benefit["C1"]           = float(np.sum(c1_net))
    cr.net_benefit_per_agent["C1"] = c1_net

    # ── C2 ──────────────────────────────────────────────────────────────
    c2 = run_c2_bilateral(D, G_klim, pi_gs, pi_gb, pi_ppa,
                           prosumer_ids, consumer_ids)
    c2_net = np.array([c2["per_agent"][n]["net_benefit"] for n in range(N)])
    cr.net_benefit["C2"]           = float(np.sum(c2_net))
    cr.net_benefit_per_agent["C2"] = c2_net

    # ── C3 ──────────────────────────────────────────────────────────────
    c3 = run_c3_spot(D, G_klim, pi_gs, pi_bolsa, prosumer_ids, consumer_ids)
    c3_net = np.array([c3["per_agent"][n]["net_benefit"] for n in range(N)])
    cr.net_benefit["C3"]           = float(np.sum(c3_net))
    cr.net_benefit_per_agent["C3"] = c3_net

    # ── C4 ──────────────────────────────────────────────────────────────
    c4 = run_c4_creg101072(D, G_klim, pi_gs, pi_bolsa, pde, capacity)
    c4_net = np.array([c4["per_agent"][n]["net_benefit"] for n in range(N)])
    cr.net_benefit["C4"]           = float(np.sum(c4_net))
    cr.net_benefit_per_agent["C4"] = c4_net

    # ── P2P ─────────────────────────────────────────────────────────────
    p2p_net = _p2p_monetary_benefit(
        p2p_results, D, G_klim, pi_gs, pi_gb, prosumer_ids)
    cr.net_benefit["P2P"]           = float(np.sum(p2p_net))
    cr.net_benefit_per_agent["P2P"] = p2p_net

    # ── SC / SS ─────────────────────────────────────────────────────────
    # PUNTO 3 — SS unificada: misma definición para todos los escenarios.
    #
    # Definición única (comparable entre P2P y C1-C4):
    #   SC = (autoconsumo_local + energía_P2P_recibida) / D_total
    #   SS = (autoconsumo_local + energía_P2P_recibida) / G_total
    #
    # Para C1–C4: no hay mercado P2P → energía_P2P = 0
    #   SC_C1 = sum(min(G,D)) / sum(D)
    #   SS_C1 = sum(min(G,D)) / sum(G)
    #
    # Para P2P: se suma el autoconsumo local más lo intercambiado en mercado
    #   SC_P2P = (sum_k [autoconsumo_k + P2P_k]) / D_total
    #   SS_P2P = (sum_k [autoconsumo_k + P2P_k]) / G_total
    #
    # Esto corrige la paradoja SS_P2P < SS_C1 que aparecía porque la versión
    # anterior solo contaba energía del mercado, ignorando el autoconsumo local.

    sc_base = _sc_index_static(G_klim, D)
    ss_base = _ss_index_static(G_klim, D)
    for esc in ["C1", "C2", "C3", "C4"]:
        cr.self_consumption[esc] = sc_base
        cr.self_sufficiency[esc] = ss_base

    # Para P2P: SC/SS unificados incluyendo autoconsumo + mercado
    active = [r for r in p2p_results
              if r.P_star is not None and np.sum(r.P_star) > 1e-6]

    # Calcular SS/SC P2P sobre el período completo (no solo horas activas)
    T_total   = len(p2p_results)
    D_total   = float(np.sum(np.maximum(D, 0)))
    G_total   = float(np.sum(np.maximum(G_klim, 0)))

    energia_util_total = 0.0   # autoconsumo local + intercambio P2P
    for k, r in enumerate(p2p_results):
        # Autoconsumo local en esta hora (todos los nodos, independiente de si hay mercado)
        autoconsumo_k = float(np.sum(np.minimum(
            np.maximum(G_klim[:, k], 0),
            np.maximum(D[:, k], 0)
        )))
        # Energía adicional cubierta por el mercado P2P esta hora
        p2p_k = float(np.sum(r.P_star)) if r.P_star is not None else 0.0
        energia_util_total += autoconsumo_k + p2p_k

    cr.self_consumption["P2P"] = energia_util_total / D_total if D_total > 1e-10 else 0.0
    cr.self_sufficiency["P2P"] = energia_util_total / G_total if G_total > 1e-10 else 0.0

    # ── Equidad (IE) ─────────────────────────────────────────────────────
    cr.equity_index["P2P"] = np.mean([r.IE for r in active]) if active else 0.0
    for esc, net in [("C1", c1_net), ("C2", c2_net),
                     ("C3", c3_net), ("C4", c4_net)]:
        s_gen  = float(np.sum(net[prosumer_ids]))
        s_cons = float(np.sum(net[consumer_ids]))
        total  = abs(s_gen) + abs(s_cons)
        cr.equity_index[esc] = (s_cons - s_gen) / total if total > 1e-10 else 0.0

    # ── Price of Fairness (P2P vs C4) ────────────────────────────────────
    w_eff  = cr.net_benefit["P2P"]
    w_fair = cr.net_benefit["C4"]
    cr.price_of_fairness = ((w_eff - w_fair) / abs(w_eff)
                            if abs(w_eff) > 1e-10 else 0.0)

    # ── Spread de ineficiencia estática C4 ───────────────────────────────
    cr.static_spread_24h = static_spread_c4_vs_p2p(D, G_klim, pde)

    return cr


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _p2p_monetary_benefit(results, D, G_klim, pi_gs, pi_gb,
                           prosumer_ids) -> np.ndarray:
    """
    Convierte resultados P2P a flujos monetarios netos por agente.

    Vendedor:   ingreso_P2P  - baseline_venta_red
    Comprador:  ahorro_P2P   - costo_residual_red
    Todos los prosumidores: + ahorro por autoconsumo propio
    """
    N = D.shape[0]
    net = np.zeros(N)

    for r in results:
        if r.P_star is None:
            continue

        # Vendedores: ganaron más que vendiendo a la red
        for idx_j, j in enumerate(r.seller_ids):
            if r.pi_star is not None:
                income = float(np.dot(r.pi_star, r.P_star[idx_j, :]))
            else:
                income = float(np.sum(r.P_star[idx_j, :])) * pi_gb
            baseline = float(np.sum(r.P_star[idx_j, :])) * pi_gb
            net[j] += income - baseline

        # Compradores: pagaron menos que comprando toda a la red
        for idx_i, i in enumerate(r.buyer_ids):
            received = float(np.sum(r.P_star[:, idx_i]))
            if r.pi_star is not None:
                paid = r.pi_star[idx_i] * received
            else:
                paid = received * pi_gs
            net[i] += received * pi_gs - paid   # ahorro positivo

            # Costo del déficit residual
            if r.P_int is not None:
                net[i] -= r.P_int[idx_i] * pi_gs

    # Autoconsumo propio de prosumidores (igual en todos los escenarios,
    # pero lo incluimos para comparación completa)
    for n in prosumer_ids:
        T = D.shape[1]
        for k in range(T):
            auto = min(G_klim[n, k], D[n, k])
            net[n] += auto * pi_gs

    return net


def _sc_index_static(G_klim, D) -> float:
    """SC de autoconsumo individual sin mercado: min(G,D) / sum(D)."""
    used  = float(np.sum(np.minimum(
        np.maximum(G_klim, 0), np.maximum(D, 0))))
    total = float(np.sum(np.maximum(D, 0)))
    return used / total if total > 1e-10 else 0.0


def _ss_index_static(G_klim, D) -> float:
    """SS de autoconsumo individual sin mercado: min(G,D) / sum(G)."""
    used = float(np.sum(np.minimum(
        np.maximum(G_klim, 0), np.maximum(D, 0))))
    gen  = float(np.sum(np.maximum(G_klim, 0)))
    return used / gen if gen > 1e-10 else 0.0


def print_comparison_report(cr: ComparisonResult) -> None:
    scenarios = ["P2P", "C1", "C2", "C3", "C4"]
    labels = {
        "P2P": "P2P (Stackelberg + RD)",
        "C1":  "C1  CREG 174/2021",
        "C2":  f"C2  Bilateral PPA (${cr.pi_ppa:.0f}/kWh)",
        "C3":  "C3  Mercado spot",
        "C4":  "C4  CREG 101 072 (AGRC)",
    }
    print("\n" + "="*68)
    print("  COMPARACIÓN REGULATORIA  —  GANANCIA ECONÓMICA NETA")
    print("="*68)
    print(f"  {'Escenario':<32} {'Gan. neta':>12}  {'SC':>6}  {'SS':>6}  {'IE':>8}")
    print("-"*68)
    for esc in scenarios:
        nb = cr.net_benefit.get(esc, 0.0)
        sc = cr.self_consumption.get(esc, 0.0)
        ss = cr.self_sufficiency.get(esc, 0.0)
        ie = cr.equity_index.get(esc, 0.0)
        print(f"  {labels[esc]:<32} ${nb:>11,.0f}  {sc:>6.3f}  "
              f"{ss:>6.3f}  {ie:>8.4f}")
    print("="*68)
    print(f"  Price of Fairness (P2P vs C4):  {cr.price_of_fairness:.4f}")
    if cr.static_spread_24h is not None:
        print(f"  Spread inef. estática C4 total: "
              f"{np.sum(cr.static_spread_24h):.3f} kWh")
    print("="*68)
