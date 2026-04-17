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
from core.settlement import gini_index, compute_net_benefit


@dataclass
class ComparisonResult:
    net_benefit:           dict  = field(default_factory=dict)
    net_benefit_per_agent: dict  = field(default_factory=dict)
    equity_index:          dict  = field(default_factory=dict)
    gini:                  dict  = field(default_factory=dict)   # Índice de Gini por escenario
    self_sufficiency:      dict  = field(default_factory=dict)
    self_consumption:      dict  = field(default_factory=dict)
    rpe:                   Optional[float]      = None
    # RPE = (W_P2P - W_C4) / |W_P2P|: rendimiento relativo frente al escenario
    # colectivo regulatorio (C4). Positivo = P2P supera a C4; negativo = al revés.
    # RPE ≠ PoF de Bertsimas (2011), que requiere resolver un problema de equidad
    # con restricción Gini. Ver notas_modelo_tesis.md §6.
    static_spread_24h:     Optional[np.ndarray] = None
    hours:     int   = 24
    n_agents:  int   = 6
    pi_ppa:    float = 0.0
    pde:       Optional[np.ndarray] = None
    # Distribución del excedente P2P (solo aplica al escenario P2P)
    # PS  = (Σ S_i)  / (Σ S_i + Σ SR_j) × 100  → fracción capturada por compradores
    # PSR = (Σ SR_j) / (Σ S_i + Σ SR_j) × 100  → fracción capturada por vendedores
    # Ref: Tabla VII modelo base Sofía Chacón (2025)
    ps_p2p:    float = 50.0   # % excedente P2P hacia compradores
    psr_p2p:   float = 50.0   # % excedente P2P hacia vendedores
    # Desglose de flujos por componente (Activity 3.2 — Nivel 1)
    # {escenario: {componente: COP_total}}
    flow_breakdown: dict = field(default_factory=dict)
    # ── Descomposición del bienestar P2P (Act 3.3) ──────────────────────
    # Nivel 1: beneficio monetario directo (COP)  → net_benefit["P2P"]
    # Nivel 2: bienestar de optimización (u.o.)   → W_sellers + W_buyers
    #
    # W_j = lam_j×G_j - theta_j×G_j² - Σ_i P_ji/log(1+π_i) - a_j×ΣP² - b_j×ΣP
    # W_i = lam_i×G_i - theta_i×G_i² + Σ_j P_ji/log(|π_i|+1) - etha_i×compe
    #
    # Nota: W_j y W_i están en unidades de optimización (u.o.): son los valores
    # de las funciones objetivo que guían la dinámica de replicador, e incluyen
    # utilidad de autoconsumo (preferencias λ, θ) y aversión al riesgo (η).
    # NO son directamente comparables en COP, pero cuantifican los beneficios
    # intangibles del mecanismo P2P más allá de los flujos de caja.
    W_sellers_total: float = 0.0   # Σ_k W_j(k) sobre todas las horas activas
    W_buyers_total:  float = 0.0   # Σ_k W_i(k) sobre todas las horas activas


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
    month_labels: Optional[np.ndarray] = None,  # (T,) etiqueta de período (YYYYMM)
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

    # Todos los escenarios usan Filosofía A: net_benefit = savings + revenues.
    # No se resta la factura residual a la red (validado por asesor Pantoja,
    # Documentos/conversacion_WEEF.txt min 22-26).

    # ── C1 ──────────────────────────────────────────────────────────────
    # month_labels habilita el balance mensual real de CREG 174 (permutación).
    # Si None (perfil 24h o sintético), todo el horizonte es un único período.
    c1 = run_c1_creg174(D, G_klim, pi_gs, pi_bolsa, prosumer_ids,
                        month_labels=month_labels)
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
    c4 = run_c4_creg101072(D, G_klim, pi_gs, pi_bolsa, pde, capacity,
                            mode="pde_only")
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
    #
    # P2P: fórmula del mercado hora a hora (settlement.py)
    #   IE = (ΣS_i − ΣSR_j) / (ΣS_i + ΣSR_j)
    #   S_i  = (pi_gs − pi_star) × P_comprado  ← ahorro comprador
    #   SR_j = (pi_star − pi_gb) × P_vendido   ← prima vendedor
    #   IE = +1 → compradores capturan todo el excedente del mercado
    #   IE = −1 → vendedores/generadores capturan todo
    #   IE =  0 → reparto exactamente igual
    #
    # C1–C4: cuando toda la comunidad son prosumidores (consumer_ids=[]),
    #   la fórmula prosumidor/consumidor colapsa siempre a −1.0 (artefacto).
    #   Fix: clasificar agentes por COBERTURA PV (ratio G/D promedio):
    #     "alta cobertura" = G/D por encima de la mediana → rol vendedor natural
    #     "baja cobertura" = G/D por debajo de la mediana → rol comprador natural
    #   IE = (beneficio_baja_cobertura − beneficio_alta_cobertura) / total
    #   IE = +1 → mecanismo redistribuye hacia quienes menos generan (equitativo)
    #   IE = −1 → mecanismo concentra beneficios en el mayor generador
    #   IE =  0 → distribución proporcional a capacidad instalada

    cr.equity_index["P2P"] = np.mean([r.IE for r in active]) if active else 0.0

    # ── PS / PSR agregados (distribución del excedente P2P) ──────────────
    # Ponderado por kWh transados en cada hora activa:
    #   PS_agg  = Σ_k (PS_k  × kWh_k) / Σ_k kWh_k
    #   PSR_agg = Σ_k (PSR_k × kWh_k) / Σ_k kWh_k
    # Esto es equivalente a calcular (Σ S_i) / (Σ S_i + Σ SR_j) global.
    if active:
        kwh_arr = np.array([float(np.sum(r.P_star)) for r in active])
        ps_arr  = np.array([r.PS  for r in active])
        psr_arr = np.array([r.PSR for r in active])
        total_kwh = float(np.sum(kwh_arr))
        if total_kwh > 1e-9:
            cr.ps_p2p  = float(np.dot(ps_arr,  kwh_arr) / total_kwh)
            cr.psr_p2p = float(np.dot(psr_arr, kwh_arr) / total_kwh)
        else:
            cr.ps_p2p = cr.psr_p2p = 50.0
    else:
        cr.ps_p2p = cr.psr_p2p = 50.0

    if len(consumer_ids) > 0:
        # Comunidad mixta (prosumidores + consumidores puros): fórmula original
        for esc, net in [("C1", c1_net), ("C2", c2_net),
                         ("C3", c3_net), ("C4", c4_net)]:
            s_gen  = float(np.sum(net[prosumer_ids]))
            s_cons = float(np.sum(net[consumer_ids]))
            total  = abs(s_gen) + abs(s_cons)
            cr.equity_index[esc] = (s_cons - s_gen) / total if total > 1e-10 else 0.0
    else:
        # Comunidad 100% prosumidores: clasificar por cobertura PV (G/D ratio)
        g_mean = np.mean(G_raw, axis=1)                       # (N,)
        d_mean = np.mean(D,     axis=1)                       # (N,)
        gd_ratio = g_mean / np.maximum(d_mean, 1e-9)         # cobertura individual
        gd_median = np.median(gd_ratio)
        high_cov = [n for n in prosumer_ids if gd_ratio[n] >= gd_median]  # vendedores natos
        low_cov  = [n for n in prosumer_ids if gd_ratio[n] <  gd_median]  # compradores natos

        for esc, net in [("C1", c1_net), ("C2", c2_net),
                         ("C3", c3_net), ("C4", c4_net)]:
            s_alta = float(np.sum(net[high_cov])) if high_cov else 0.0
            s_baja = float(np.sum(net[low_cov]))  if low_cov  else 0.0
            total  = abs(s_alta) + abs(s_baja)
            cr.equity_index[esc] = (s_baja - s_alta) / total if total > 1e-10 else 0.0

    # ── Gini (Índice de desigualdad, propuesta §VI.C Nivel 2) ───────────────
    # Se calcula sobre beneficios netos por agente para todos los escenarios.
    # Gini=0: todos los agentes ganan lo mismo; Gini=1: máxima concentración.
    for esc, net in [("P2P", p2p_net), ("C1", c1_net),
                     ("C2", c2_net), ("C3", c3_net), ("C4", c4_net)]:
        cr.gini[esc] = gini_index(net)

    # ── Desglose de flujos por componente (Activity 3.2 — Nivel 1) ──────────
    #
    # Para cada escenario, el beneficio neto se descompone en sus fuentes:
    #   Autoconsumo : energía solar consumida en sitio  → valorada a pi_gs
    #   Permutación : energía inyectada que compensa retiros del período (C1)
    #   Excedente   : energía neta exportada            → valorada a pi_bolsa
    #   Prima vend. : ganancia P2P del vendedor sobre pi_gb  (solo P2P)
    #   Ahorro comp.: ahorro del comprador respecto a pi_gs  (solo P2P)
    #   Créditos PDE: distribución administrativa de excedentes (C4)
    #
    # Autoconsumo es IDÉNTICO en todos los escenarios (no depende del mecanismo).
    # Lo que varía es el valor asignado a la energía que pasa por la red.

    # Autoconsumo total (prosumidores) — igual en todos los escenarios
    auto_kwh = float(np.sum(np.minimum(
        np.maximum(G_klim[prosumer_ids, :], 0),
        np.maximum(D[prosumer_ids, :], 0),
    )))
    auto_cop = auto_kwh * pi_gs

    # C1 breakdown
    c1_savings_total = c1["aggregate"]["total_savings"]      # auto + permutación
    c1_permutacion   = max(0.0, c1_savings_total - auto_cop) # solo permutación
    c1_excedente     = c1["aggregate"]["total_surplus_revenue"]

    # C3 breakdown
    c3_auto_total    = c3["aggregate"]["total_savings"]
    c3_excedente     = c3["aggregate"]["total_revenues"]

    # C4 breakdown
    c4_auto_total    = c4["aggregate"]["total_savings"]
    c4_pde_credits   = c4["aggregate"]["total_pde_credits"]
    c4_excedente     = c4["aggregate"]["total_surplus_revenue"]

    # P2P breakdown: prima vendedor + ahorro comprador + autoconsumo propio
    p2p_prima, p2p_ahorro = _p2p_flow_breakdown(p2p_results, pi_gs, pi_gb)

    cr.flow_breakdown = {
        "P2P": {
            "Autoconsumo":      auto_cop,
            "Prima vendedor":   p2p_prima,
            "Ahorro comprador": p2p_ahorro,
        },
        "C1": {
            "Autoconsumo":    auto_cop,
            "Permutación":    c1_permutacion,
            "Excedente neto": c1_excedente,
        },
        "C3": {
            "Autoconsumo":     c3_auto_total,
            "Excedente bolsa": c3_excedente,
        },
        "C4": {
            "Autoconsumo":   c4_auto_total,
            "Créditos PDE":  c4_pde_credits,
            "Excedente bolsa": c4_excedente,
        },
    }

    # ── Act 3.3: Bienestar de optimización (Nivel 2 — u.o.) ─────────────
    # Acumula los valores W_j y W_i calculados por el motor P2P hora a hora.
    # Estos incluyen utilidad de autoconsumo (λ, θ) y aversión al riesgo (η),
    # que no están capturados en el beneficio monetario de Nivel 1.
    cr.W_sellers_total = float(sum(
        r.Wj_total for r in p2p_results if r.P_star is not None))
    cr.W_buyers_total = float(sum(
        r.Wi_total for r in p2p_results if r.P_star is not None))

    # ── RPE: Rendimiento Relativo P2P vs C4 ──────────────────────────────
    w_eff  = cr.net_benefit["P2P"]
    w_fair = cr.net_benefit["C4"]
    # TODO (Opción B): implementar PoF de Bertsimas 2011 [15] — requiere resolver
    # el mismo problema bajo criterio equitativo con restricción Gini ≤ umbral.
    cr.rpe = ((w_eff - w_fair) / abs(w_eff)
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

    Filosofía A (WEEF min 22-26): net_benefit = savings + revenues.
    No se resta el costo residual de compra a la red.

    Vendedor:    (π_star − π_gb) × P_vendido   (prima sobre venta a bolsa)
    Comprador:   (π_gs  − π_star) × P_comprado (ahorro vs comprar a la red)
    Autoconsumo: min(G, D) × π_gs              (todos los prosumidores)

    Parámetros
    ----------
    results : list[HourlyResult]
    D, G_klim : ndarray (N, T)
    pi_gs, pi_gb : float — precio al usuario y precio de bolsa (COP/kWh)
    prosumer_ids : list[int] — índices de agentes con generación propia
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

        # Compradores: ahorro por pagar pi_star < pi_gs en vez de comprar todo a la red
        for idx_i, i in enumerate(r.buyer_ids):
            received = float(np.sum(r.P_star[:, idx_i]))
            if r.pi_star is not None:
                paid = r.pi_star[idx_i] * received
            else:
                paid = received * pi_gs
            net[i] += received * pi_gs - paid   # ahorro = (pi_gs - pi_star) × kWh_P2P
            # No se resta el déficit residual: esa energía la comprará a la red
            # igual que sin solar — no es una pérdida del mecanismo P2P.

    # Autoconsumo propio de prosumidores (igual en todos los escenarios,
    # pero lo incluimos para comparación completa)
    for n in prosumer_ids:
        T = D.shape[1]
        for k in range(T):
            auto = min(G_klim[n, k], D[n, k])
            net[n] += auto * pi_gs

    return net


def _p2p_flow_breakdown(results, pi_gs: float, pi_gb: float) -> tuple:
    """
    Descompone el beneficio P2P en prima de vendedor y ahorro de comprador.

      prima_vendedor  : Σ_k Σ_j max(0, ingreso_j - baseline_j)
      ahorro_comprador: Σ_k Σ_i max(0, pi_gs×P_comprado - pagado)

    El autoconsumo propio se contabiliza por separado (igual en todos los
    escenarios, independiente del mecanismo de mercado).

    Parámetros
    ----------
    results : list[HourlyResult]
    pi_gs   : float — tarifa al usuario (COP/kWh)
    pi_gb   : float — precio de bolsa, baseline de venta (COP/kWh)

    Retorna
    -------
    (prima_vendedor, ahorro_comprador) : (float, float) en COP
    """
    prima  = 0.0
    ahorro = 0.0
    for r in results:
        if r.P_star is None:
            continue
        for idx_j, j in enumerate(r.seller_ids):
            if r.pi_star is not None:
                income = float(np.dot(r.pi_star, r.P_star[idx_j, :]))
            else:
                income = float(np.sum(r.P_star[idx_j, :])) * pi_gb
            baseline = float(np.sum(r.P_star[idx_j, :])) * pi_gb
            prima += max(0.0, income - baseline)
        for idx_i, i in enumerate(r.buyer_ids):
            received = float(np.sum(r.P_star[:, idx_i]))
            paid     = (r.pi_star[idx_i] * received if r.pi_star is not None
                        else received * pi_gs)
            ahorro  += max(0.0, received * pi_gs - paid)
    return prima, ahorro


def print_welfare_decomposition(cr: "ComparisonResult") -> None:
    """
    Act 3.3 — Descomposición formal del bienestar P2P.

    Nivel 1 — Beneficio monetario directo (COP):
        Comparable directamente con C1–C4 (que son puramente financieros).
        Fuentes: autoconsumo, prima vendedor, ahorro comprador.

    Nivel 2 — Bienestar de optimización (u.o.) + métricas sociales:
        W_j y W_i guían la dinámica de replicador e incluyen utilidad de
        autoconsumo (λ, θ) y aversión al riesgo (η). No son COP, pero
        cuantifican el valor intangible del mecanismo dinámico.
        Métricas sociales: IE, Gini, SC, SS, PoF.

    Referencia: propuesta tesis §VI.C Act 3.3, §VII.C Niveles 1 y 2.
    """
    W = 70
    print("\n" + "=" * W)
    print("  Act 3.3 — DESCOMPOSICIÓN DEL BIENESTAR P2P")
    print("  (distingue beneficio monetario de intangibles del mecanismo dinámico)")
    print("=" * W)

    # ── Nivel 1: monetario ────────────────────────────────────────────────
    print("\n  NIVEL 1 — Beneficio monetario directo (COP)")
    print(f"  {'(comparable con C1–C4 que son puramente financieros)'}")
    print(f"  {'-' * 60}")
    bd = cr.flow_breakdown.get("P2P", {})
    if bd:
        total_mon = sum(bd.values())
        for comp, val in bd.items():
            pct = val / total_mon * 100 if total_mon > 1e-6 else 0.0
            print(f"    {comp:<26} {val:>14,.0f} COP  ({pct:5.1f}%)")
        print(f"    {'─' * 52}")
        print(f"    {'TOTAL monetario (Nivel 1)':<26} {total_mon:>14,.0f} COP  (100.0%)")
    else:
        print(f"    (no disponible — ejecutar con datos reales)")

    # ── Nivel 2: intangibles del mecanismo ───────────────────────────────
    print(f"\n  NIVEL 2 — Bienestar de optimización P2P (unidades de optimización)")
    print(f"  {'(incluye: utilidad de autoconsumo λ/θ, aversión al riesgo η)'}")
    print(f"  {'-' * 60}")
    W_total = cr.W_sellers_total + cr.W_buyers_total
    print(f"    {'Bienestar vendedores  Σ W_j':<34} {cr.W_sellers_total:>12.4f} u.o.")
    print(f"    {'Bienestar compradores Σ W_i':<34} {cr.W_buyers_total:>12.4f} u.o.")
    print(f"    {'─' * 52}")
    print(f"    {'Total W_opt (Wj + Wi)':<34} {W_total:>12.4f} u.o.")
    print(f"\n    Nota: u.o. = unidades de optimización. Los valores W guían la")
    print(f"    dinámica de replicador; no son COP pero reflejan la preferencia")
    print(f"    de los agentes más allá del flujo de caja directo.")

    # ── Métricas sociales (componente intangible observable) ─────────────
    print(f"\n  NIVEL 2 — Métricas sociales del mecanismo P2P")
    print(f"  {'-' * 60}")
    ie   = cr.equity_index.get("P2P",   0.0)
    ie4  = cr.equity_index.get("C4",    0.0)
    gini = cr.gini.get("P2P",           0.0)
    gini4 = cr.gini.get("C4",           0.0)
    sc   = cr.self_consumption.get("P2P", 0.0)
    ss   = cr.self_sufficiency.get("P2P", 0.0)
    rpe  = cr.rpe or 0.0
    print(f"    IE  P2P = {ie:+.4f}   vs   IE  C4 = {ie4:+.4f}  "
          f"  Δ = {ie - ie4:+.4f}")
    print(f"    Gini P2P = {gini:.4f}   vs   Gini C4 = {gini4:.4f}  "
          f"  Δ = {gini - gini4:+.4f}")
    print(f"    SC  P2P = {sc:.4f}    SS  P2P = {ss:.4f}")
    print(f"    RPE (P2P vs C4): {rpe:.4f}  [Rendimiento relativo vs C4; RPE > 0: P2P supera C4]")

    print("=" * W)


def print_flow_breakdown(cr: "ComparisonResult", currency: str = "COP") -> None:
    """
    Imprime el desglose de flujos por componente para cada escenario.
    Activity 3.2 — Nivel 1: flujos de caja netos por fuente de valor.
    """
    if not cr.flow_breakdown:
        return

    print("\n" + "="*68)
    print("  DESGLOSE DE FLUJOS POR COMPONENTE  (Activity 3.2 — Nivel 1)")
    print("  (muestra cómo se genera el beneficio neto en cada escenario)")
    print("="*68)

    esc_order = ["P2P", "C1", "C3", "C4"]
    labels = {
        "P2P": "P2P (Stackelberg + RD)",
        "C1":  "C1  CREG 174 — AGPE",
        "C3":  "C3  Mercado spot",
        "C4":  "C4  CREG 101 072 — AGRC",
    }
    col_w = 16

    for esc in esc_order:
        bd = cr.flow_breakdown.get(esc)
        if not bd:
            continue
        total = sum(bd.values())
        print(f"\n  {labels[esc]}")
        print(f"  {'Componente':<24} {'COP':>{col_w}} {'%':>7}")
        print(f"  {'-'*50}")
        for comp, val in bd.items():
            pct = val / total * 100 if total > 1e-6 else 0.0
            print(f"  {comp:<24} {val:>{col_w},.0f} {pct:>7.1f}%")
        print(f"  {'TOTAL':<24} {total:>{col_w},.0f} {'100.0%':>7}")

    print("="*68)
    # Nota interpretativa
    auto_p2p = cr.flow_breakdown.get("P2P", {}).get("Autoconsumo", 0)
    auto_c1  = cr.flow_breakdown.get("C1",  {}).get("Autoconsumo", 0)
    if auto_p2p > 0 and abs(auto_p2p - auto_c1) < 1.0:
        print("  Nota: el autoconsumo es idéntico en todos los escenarios —")
        print(f"        lo que varía es el valor asignado a los excedentes.")
    print("="*68)

    # ── Act 3.3: descomposición formal del bienestar ─────────────────────
    print_welfare_decomposition(cr)


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
        "C1":  "C1  Individual CREG 174/2021",
        "C2":  f"C2  Bilateral PPA (${cr.pi_ppa:.0f}/kWh)",
        "C3":  "C3  Spot (bolsa mayorista)",
        "C4":  "C4  Colectivo CREG 101 072",
    }
    print("\n" + "="*80)
    print("  COMPARACIÓN REGULATORIA  —  BENEFICIO ECONÓMICO DEL SISTEMA SOLAR")
    print("  (ahorro en factura + ingresos; no incluye compras residuales a red)")
    print("="*80)
    print(f"  {'Escenario':<32} {'Beneficio':>12}  {'SC':>6}  {'SS':>6}  "
          f"{'IE':>8}  {'Gini':>6}")
    print(f"  {'':32} {'COP/período':>12}  {'[0-1]':>6}  {'[0-1]':>6}  "
          f"{'[-1,+1]':>8}  {'[0-1]':>6}")
    print("-"*80)
    for esc in scenarios:
        nb   = cr.net_benefit.get(esc, 0.0)
        sc   = cr.self_consumption.get(esc, 0.0)
        ss   = cr.self_sufficiency.get(esc, 0.0)
        ie   = cr.equity_index.get(esc, 0.0)
        gini = cr.gini.get(esc, 0.0)
        print(f"  {labels[esc]:<32} ${nb:>11,.0f}  {sc:>6.3f}  "
              f"{ss:>6.3f}  {ie:>8.4f}  {gini:>6.4f}")
    print("="*80)
    print(f"  RPE (P2P vs C4):  {cr.rpe:.4f}")
    if cr.static_spread_24h is not None:
        print(f"  Spread inef. estática C4 total: "
              f"{np.sum(cr.static_spread_24h):.3f} kWh")
    print("-"*68)
    print(f"  Distribución del excedente P2P (ref. Tabla VII Sofía Chacón):")
    print(f"    PS  (compradores):  {cr.ps_p2p:6.2f}%  "
          f"← fracción del surplus P2P capturada por compradores")
    print(f"    PSR (vendedores):   {cr.psr_p2p:6.2f}%  "
          f"← fracción del surplus P2P capturada por vendedores")
    psr_gap = abs(cr.ps_p2p - cr.psr_p2p)
    dominant = "compradores" if cr.ps_p2p > cr.psr_p2p else "vendedores"
    print(f"    → Asimetría: {psr_gap:.2f} pp a favor de {dominant}  "
          f"(IE={cr.equity_index.get('P2P', 0):.4f})")
    print("="*68)
