"""
optimality.py  — Análisis cualitativo de optimalidad del mercado P2P
----------------------------------------------------------------------
Brayan S. Lopez-Mendez · Udenar 2026

Activity 4.2: Clasificación hora a hora de la dominancia del mecanismo P2P
frente al escenario AGRC (C4), con métricas de eficiencia del mercado.

Para cada hora k del horizonte se calcula:
  - B_P2P_k  : beneficio P2P (autoconsumo + prima vendedor + ahorro comprador)
  - B_C4_k   : beneficio C4 (autoconsumo + créditos PDE valorizados)
  - Delta_k  = B_P2P_k - B_C4_k        (ventaja diferencial)
  - GDR_k    : Global Dispatch Ratio = Σ P_ji / min(ΣG_net_j, ΣD_net_i)
                → eficiencia de clearing del mercado (1 = óptimo, 0 = inactivo)

Clasificación de cada hora:
  "P2P_dom"   : Delta_k > umbral_pos (P2P claramente superior)
  "C4_dom"    : Delta_k < umbral_neg (C4 claramente superior)
  "neutral"   : |Delta_k| ≤ umbral (resultados equivalentes)
  "inactive"  : no hubo mercado P2P activo (P_star == None o ≈ 0)

Exporta:
  HourlyOptimality  — resultado por hora
  OptimalitySummary — estadísticas agregadas

Nota: B_C4_k se calcula de forma liviana (sin run_c4_creg101072 completo)
usando la misma lógica de autoconsumo + crédito PDE.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ── Clases de resultados ────────────────────────────────────────────────────

@dataclass
class HourlyOptimality:
    k:            int
    B_p2p:        float    # beneficio P2P en la hora k  [COP]
    B_c4:         float    # beneficio C4 en la hora k   [COP]
    delta:        float    # B_p2p - B_c4                [COP]
    gdr:          float    # Global Dispatch Ratio  ∈ [0,1]
    category:     str      # "P2P_dom" | "C4_dom" | "neutral" | "inactive"
    kwh_p2p:      float    # kWh transados en P2P
    active:       bool     # True si hubo mercado activo


@dataclass
class OptimalitySummary:
    # Conteos de horas por categoría
    n_p2p_dom:      int   = 0
    n_c4_dom:       int   = 0
    n_neutral:      int   = 0
    n_inactive:     int   = 0
    n_active:       int   = 0
    T_total:        int   = 0

    # Estadísticas de delta (solo horas activas)
    delta_mean:     float = 0.0
    delta_std:      float = 0.0
    delta_total:    float = 0.0    # acumulado P2P - C4 en COP totales
    delta_pct:      float = 0.0    # % horas donde P2P > C4

    # Estadísticas GDR (solo horas activas)
    gdr_mean:       float = 0.0
    gdr_std:        float = 0.0
    gdr_min:        float = 0.0
    gdr_max:        float = 0.0

    # Beneficios totales acumulados
    B_p2p_total:    float = 0.0
    B_c4_total:     float = 0.0
    kwh_p2p_total:  float = 0.0

    # Umbrales usados
    threshold_cop:  float = 0.0
    hourly_data:    list  = field(default_factory=list)   # list[HourlyOptimality]


# ── Función principal ────────────────────────────────────────────────────────

def analyze_hourly_dominance(
    D:            np.ndarray,        # (N, T) demanda [kWh]
    G_klim:       np.ndarray,        # (N, T) generación limitada [kWh]
    p2p_results:  list,              # lista de HourlyResult, len = T
    pde:          np.ndarray,        # (N,) ponderadores PDE
    pi_gs:        float,             # precio usuario [COP/kWh]
    pi_gb:        float,             # precio compra bolsa [COP/kWh] — referencia P2P
    pi_bolsa:     np.ndarray,        # (T,) precio bolsa horario [COP/kWh]
    prosumer_ids: list,
    consumer_ids: list,
    threshold_cop: Optional[float] = None,  # umbral |Delta| en COP para clasificar como "neutral"
) -> OptimalitySummary:
    """
    Clasifica cada hora según dominancia P2P vs C4 y calcula GDR.

    Parameters
    ----------
    threshold_cop : float, optional
        Umbral en COP por debajo del cual se considera empate (neutral).
        Si None, se usa el 5% del beneficio P2P promedio por hora activa.

    Returns
    -------
    OptimalitySummary con lista completa de HourlyOptimality.
    """
    N, T = D.shape
    hourly = []

    for k, res in enumerate(p2p_results):
        D_k     = np.maximum(D[:, k], 0.0)
        G_k     = np.maximum(G_klim[:, k], 0.0)
        pb_k    = float(pi_bolsa[k])

        # ── Beneficio C4 en la hora k (sin re-simular run_c4) ────────────
        auto_k     = np.minimum(G_k, D_k)                     # autoconsumo individual
        surplus_k  = np.maximum(G_k - D_k, 0.0)               # excedentes individuales
        deficit_k  = np.maximum(D_k - G_k, 0.0)               # déficits individuales

        G_total_k  = float(np.sum(G_k))
        D_total_k  = float(np.sum(D_k))
        comm_surp  = max(0.0, G_total_k - D_total_k)           # excedente comunitario

        credits_k  = pde * comm_surp                           # distribución PDE
        credits_eff = np.minimum(credits_k, deficit_k)         # crédito efectivo (hasta cubrir déficit)

        # Ingreso por excedente propio a bolsa
        surplus_income_k = surplus_k * pb_k

        B_c4_k = (float(np.sum(auto_k)) * pi_gs
                  + float(np.sum(credits_eff)) * pi_gs
                  + float(np.sum(surplus_income_k)))

        # ── Beneficio P2P en la hora k ────────────────────────────────────
        active = (res.P_star is not None and float(np.sum(res.P_star)) > 1e-6)

        if not active:
            # Sin mercado: solo autoconsumo propio (igual en ambos escenarios)
            B_p2p_k  = float(np.sum(auto_k)) * pi_gs + float(np.sum(surplus_k)) * pb_k
            kwh_p2p  = 0.0
            gdr      = 0.0
        else:
            P_star = res.P_star      # (J, I) o (J, I) matrix

            # Autoconsumo propio: vendedores antes de vender + compradores propios
            B_auto = float(np.sum(auto_k)) * pi_gs

            # Prima vendedor: ingresos P2P - ingresos al precio de referencia (pi_gb)
            kwh_sold_j = np.sum(P_star, axis=1)   # (J,)
            if res.pi_star is not None:
                income_j = np.array([
                    float(np.dot(res.pi_star, P_star[idx_j, :]))
                    for idx_j in range(len(res.seller_ids))
                ])
            else:
                income_j = kwh_sold_j * pi_gb
            prima_seller = float(np.sum(income_j - kwh_sold_j * pi_gb))

            # Ahorro comprador: precio red (pi_gs) - precio P2P pagado
            kwh_recv_i = np.sum(P_star, axis=0)   # (I,)
            if res.pi_star is not None:
                paid_i = res.pi_star * kwh_recv_i
            else:
                paid_i = kwh_recv_i * pi_gs
            ahorro_buyer = float(np.sum(kwh_recv_i * pi_gs - paid_i))

            # Excedente no vendido: al precio bolsa
            kwh_p2p  = float(np.sum(P_star))
            surplus_sold_p2p = np.maximum(
                np.array([G_klim[j, k] for j in res.seller_ids]) - kwh_sold_j, 0.0
            )
            surplus_bolsa = float(np.sum(surplus_sold_p2p)) * pb_k

            B_p2p_k = B_auto + prima_seller + ahorro_buyer + surplus_bolsa

            # ── GDR: eficiencia de clearing ───────────────────────────────
            G_net_j = np.array([
                max(float(G_klim[j, k]) - float(D[j, k]), 0.0)
                for j in res.seller_ids
            ])
            D_net_i = np.array([
                max(float(D[i, k]) - float(G_klim[i, k]), 0.0)
                for i in res.buyer_ids
            ])
            potential = min(float(np.sum(G_net_j)), float(np.sum(D_net_i)))
            gdr = (kwh_p2p / potential) if potential > 1e-9 else 0.0
            gdr = float(np.clip(gdr, 0.0, 1.0))

        delta_k = B_p2p_k - B_c4_k

        hourly.append(HourlyOptimality(
            k=k,
            B_p2p=B_p2p_k,
            B_c4=B_c4_k,
            delta=delta_k,
            gdr=gdr,
            category="inactive",   # se asigna después
            kwh_p2p=kwh_p2p if active else 0.0,
            active=active,
        ))

    # ── Umbral adaptativo ────────────────────────────────────────────────────
    active_hrs = [h for h in hourly if h.active]
    if threshold_cop is None:
        if active_hrs:
            avg_b = np.mean([abs(h.B_p2p) for h in active_hrs])
            threshold_cop = max(avg_b * 0.05, 1.0)   # 5% del beneficio medio, mínimo 1 COP
        else:
            threshold_cop = 1.0

    # ── Clasificación ─────────────────────────────────────────────────────────
    for h in hourly:
        if not h.active:
            h.category = "inactive"
        elif h.delta > threshold_cop:
            h.category = "P2P_dom"
        elif h.delta < -threshold_cop:
            h.category = "C4_dom"
        else:
            h.category = "neutral"

    # ── Resumen agregado ──────────────────────────────────────────────────────
    cats = [h.category for h in hourly]
    deltas_active = [h.delta for h in hourly if h.active]
    gdrs_active   = [h.gdr   for h in hourly if h.active]

    summary = OptimalitySummary(
        n_p2p_dom  = cats.count("P2P_dom"),
        n_c4_dom   = cats.count("C4_dom"),
        n_neutral  = cats.count("neutral"),
        n_inactive = cats.count("inactive"),
        n_active   = len(active_hrs),
        T_total    = len(hourly),
        delta_mean   = float(np.mean(deltas_active))  if deltas_active else 0.0,
        delta_std    = float(np.std(deltas_active))   if deltas_active else 0.0,
        delta_total  = float(np.sum(deltas_active))   if deltas_active else 0.0,
        delta_pct    = (cats.count("P2P_dom") / max(len(active_hrs), 1)) * 100.0,
        gdr_mean     = float(np.mean(gdrs_active))    if gdrs_active else 0.0,
        gdr_std      = float(np.std(gdrs_active))     if gdrs_active else 0.0,
        gdr_min      = float(np.min(gdrs_active))     if gdrs_active else 0.0,
        gdr_max      = float(np.max(gdrs_active))     if gdrs_active else 0.0,
        B_p2p_total  = float(np.sum([h.B_p2p for h in hourly])),
        B_c4_total   = float(np.sum([h.B_c4  for h in hourly])),
        kwh_p2p_total= float(np.sum([h.kwh_p2p for h in hourly])),
        threshold_cop= threshold_cop,
        hourly_data  = hourly,
    )
    return summary


# ── Impresión consola ──────────────────────────────────────────────────────────

def print_optimality_report(
    summary: OptimalitySummary,
    agent_names: Optional[list] = None,
    currency: str = "COP",
) -> None:
    """Imprime resumen del análisis de optimalidad en consola."""
    s = summary
    T = s.T_total
    A = max(s.n_active, 1)

    print("\n" + "="*60)
    print("  ANÁLISIS DE OPTIMALIDAD — P2P vs C4 hora a hora")
    print("="*60)
    print(f"  Horizonte total  : {T} horas")
    print(f"  Horas activas P2P: {s.n_active} ({100*s.n_active/T:.1f}%)")
    print(f"  Umbral neutral   : ±{s.threshold_cop:,.0f} {currency}")
    print()
    print("  Clasificación de horas activas:")
    print(f"    P2P dominante : {s.n_p2p_dom:>5} h  ({100*s.n_p2p_dom/A:5.1f}%)")
    print(f"    C4  dominante : {s.n_c4_dom:>5} h  ({100*s.n_c4_dom/A:5.1f}%)")
    print(f"    Neutral       : {s.n_neutral:>5} h  ({100*s.n_neutral/A:5.1f}%)")
    print(f"    Inactivas     : {s.n_inactive:>5} h")
    print()
    print("  Delta = B_P2P - B_C4 (horas activas):")
    print(f"    Media  : {s.delta_mean:>12,.0f} {currency}/h")
    print(f"    Std    : {s.delta_std:>12,.0f} {currency}/h")
    print(f"    Total  : {s.delta_total:>12,.0f} {currency}")
    print()
    print("  GDR — Global Dispatch Ratio (eficiencia clearing):")
    print(f"    Media  : {s.gdr_mean:>6.3f}")
    print(f"    Mínimo : {s.gdr_min:>6.3f}   Máximo: {s.gdr_max:.3f}")
    print()
    print("  Beneficios acumulados totales:")
    print(f"    B_P2P : {s.B_p2p_total:>14,.0f} {currency}")
    print(f"    B_C4  : {s.B_c4_total:>14,.0f} {currency}")
    print(f"    Delta : {s.delta_total:>14,.0f} {currency}  "
          f"({'P2P superior' if s.delta_total > 0 else 'C4 superior'})")
    print("="*60)
