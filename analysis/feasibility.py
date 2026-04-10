"""
feasibility.py  — Análisis de factibilidad (Actividad 4.2 de la tesis)
-----------------------------------------------------------------------
Brayan S. Lopez-Mendez · Udenar 2026

Dos análisis:

  FA-1: Condición de deserción del mercado P2P
        Un prosumidor abandona el P2P cuando:
          precio_p2p < precio_bolsa  (vender fuera es más rentable)
        Se computa la fracción de horas donde se cumple la condición.

  FA-2: Riesgo regulatorio del escenario C4 (CREG 101 072/2025)
        La CREG 101 072 impone:
          - Regla 10%: un agente no puede suministrar >10% de la demanda
          - Límite 100 kW por instalación de autogeneración colectiva
        Se verifica si la comunidad MTE cumple estas restricciones
        y qué pasa si cambia la composición (nueva institución, más PV).
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FeasibilityReport:
    """Reporte completo de factibilidad."""
    # FA-1: Deserción
    desertion_hours_by_agent:  dict = field(default_factory=dict)
    desertion_pct_by_agent:    dict = field(default_factory=dict)
    avg_p2p_price_by_hour:     np.ndarray = field(default_factory=lambda: np.array([]))
    condition_never_met:       bool = True
    critical_pgb_threshold:    Optional[float] = None

    # FA-2: Riesgo regulatorio C4
    rule_10pct_satisfied:      bool  = True
    rule_10pct_violations:     dict  = field(default_factory=dict)
    rule_100kw_satisfied:      bool  = True
    rule_100kw_violations:     list  = field(default_factory=list)
    max_supply_share_by_agent: dict  = field(default_factory=dict)
    max_capacity_by_agent:     dict  = field(default_factory=dict)
    robustness_score:          float = 1.0   # 1=máxima robustez, 0=ninguna


def analyze_desertion(
    p2p_results: list,
    pi_bolsa: np.ndarray,
    agent_names: list,
    prosumer_ids: list,
    verbose: bool = True,
) -> FeasibilityReport:
    """
    FA-1: Para cada hora con mercado P2P activo, verifica si el precio
    p2p es mayor que el precio de bolsa (condición de no-deserción).

    Condición de permanencia: pi_p2p(k) >= pi_bolsa(k)
    Si se viola: el vendedor prefiere exportar directamente a la red.
    """
    T = len(p2p_results)
    report = FeasibilityReport()

    # Precio promedio P2P por hora
    avg_price = np.full(T, np.nan)
    for r in p2p_results:
        if r.pi_star is not None and r.P_star is not None:
            total = float(np.sum(r.P_star))
            if total > 1e-6:
                w = np.sum(r.P_star, axis=0) / total
                avg_price[r.k] = float(np.dot(w, r.pi_star))

    report.avg_p2p_price_by_hour = avg_price

    # Horas activas donde precio P2P < precio bolsa
    active_mask = ~np.isnan(avg_price)
    if not active_mask.any():
        report.condition_never_met = True
        if verbose:
            print("  FA-1: Sin horas de mercado activo — deserción no aplica.")
        return report

    n_active = active_mask.sum()
    desertion_mask = active_mask & (avg_price < pi_bolsa[:T])
    n_desertion = desertion_mask.sum()
    report.condition_never_met = (n_desertion == 0)

    if verbose:
        print(f"\n  FA-1: Condición de deserción")
        print(f"    Horas mercado activo: {n_active}/{T}")
        print(f"    Horas con pi_p2p < pi_bolsa: {n_desertion} "
              f"({n_desertion/max(n_active,1)*100:.1f}%)")
        if n_desertion == 0:
            print(f"    → El P2P NUNCA es menos rentable que vender a bolsa.")
            print(f"    → Condición de permanencia SIEMPRE satisfecha.")
        else:
            print(f"    → En {n_desertion} horas un vendedor preferiría la bolsa.")

    # Precio mínimo de bolsa que provocaría deserción en ≥50% de las horas activas
    if not report.condition_never_met:
        active_prices = avg_price[active_mask]
        # El umbral es la mediana de los precios P2P en horas activas
        report.critical_pgb_threshold = float(np.median(active_prices))
        if verbose:
            med = report.critical_pgb_threshold
            print(f"    → Deserción masiva si pi_bolsa > {med:.0f} COP/kWh "
                  f"(mediana precio P2P)")
    else:
        # Umbral mínimo: si bolsa sube por encima del máximo precio P2P
        active_prices = avg_price[active_mask]
        report.critical_pgb_threshold = float(np.max(active_prices))
        if verbose:
            print(f"    → Deserción posible solo si pi_bolsa > "
                  f"{report.critical_pgb_threshold:.0f} COP/kWh")

    return report


def analyze_creg_101072_compliance(
    D: np.ndarray,
    G: np.ndarray,
    agent_names: list,
    prosumer_ids: list,
    capacity_limit_kw: float = 100.0,
    share_limit: float = 0.10,
    verbose: bool = True,
) -> FeasibilityReport:
    """
    FA-2: Verifica si la comunidad MTE cumple las restricciones de la
    CREG 101 072/2025 para autogeneración colectiva (C4).

    Restricciones:
      1. Regla del 10%: ningún prosumidor puede suministrar más del 10%
         de la demanda total de la comunidad.
      2. Límite de 100 kW: la capacidad instalada de cada instalación
         de autogeneración no puede superar 100 kW (pequeña escala).
    """
    report = FeasibilityReport()
    N = D.shape[0]
    T = D.shape[1]

    D_total_per_hour = D.sum(axis=0)              # demanda comunitaria (T,)
    D_total_mean     = float(D_total_per_hour.mean())

    if verbose:
        print(f"\n  FA-2: Cumplimiento CREG 101 072/2025")
        print(f"    Demanda media comunidad: {D_total_mean:.1f} kW")
        print(f"    Restricción 1: participación ≤ {share_limit*100:.0f}% de D_total")
        print(f"    Restricción 2: capacidad instalada ≤ {capacity_limit_kw:.0f} kW")

    # Regla 10%
    violations_10pct = {}
    max_share = {}
    for n in prosumer_ids:
        name = agent_names[n] if n < len(agent_names) else f"A{n+1}"
        g_n  = float(G[n].mean())
        share = g_n / max(D_total_mean, 1e-6)
        max_share[name] = round(share * 100, 2)
        if share > share_limit:
            violations_10pct[name] = round(share * 100, 2)

    report.max_supply_share_by_agent = max_share
    report.rule_10pct_satisfied = len(violations_10pct) == 0
    report.rule_10pct_violations = violations_10pct

    # Límite 100 kW
    violations_100kw = []
    cap_by_agent = {}
    for n in prosumer_ids:
        name   = agent_names[n] if n < len(agent_names) else f"A{n+1}"
        g_max  = float(G[n].max())
        cap_by_agent[name] = round(g_max, 1)
        if g_max > capacity_limit_kw:
            violations_100kw.append(name)

    report.max_capacity_by_agent  = cap_by_agent
    report.rule_100kw_satisfied   = len(violations_100kw) == 0
    report.rule_100kw_violations  = violations_100kw

    # Score de robustez: fracción de restricciones cumplidas
    n_rules = 2 * len(prosumer_ids)
    n_ok    = (n_rules
               - len(violations_10pct)
               - len(violations_100kw))
    report.robustness_score = n_ok / max(n_rules, 1)

    if verbose:
        print(f"\n    Restricción 1 — Participación por agente:")
        for name, pct in max_share.items():
            status = "✗ VIOLA" if name in violations_10pct else "✓"
            print(f"      {name:<12}: {pct:>6.2f}%  {status}")

        print(f"\n    Restricción 2 — Capacidad máxima [kW]:")
        for name, cap in cap_by_agent.items():
            status = "✗ VIOLA" if name in violations_100kw else "✓"
            print(f"      {name:<12}: {cap:>7.1f} kW  {status}")

        r1 = "CUMPLE" if report.rule_10pct_satisfied else f"VIOLA ({len(violations_10pct)} agentes)"
        r2 = "CUMPLE" if report.rule_100kw_satisfied else f"VIOLA ({len(violations_100kw)} agentes)"
        print(f"\n    Regla 10%:     {r1}")
        print(f"    Límite 100 kW: {r2}")
        print(f"    Score robustez: {report.robustness_score:.2f}")

    return report


def analyze_new_agent_impact(
    D: np.ndarray,
    G: np.ndarray,
    agent_names: list,
    new_agent_d: float,
    new_agent_g: float,
    new_agent_name: str = "NuevaNodo",
    verbose: bool = True,
) -> dict:
    """
    Simula el impacto de añadir un nuevo agente a la comunidad C4.
    Calcula si las restricciones de la CREG 101 072 siguen cumpliéndose.
    """
    N, T = D.shape
    D_new  = np.vstack([D, np.full((1, T), new_agent_d)])
    G_new  = np.vstack([G, np.full((1, T), new_agent_g)])
    names_new = agent_names + [new_agent_name]
    ids_new   = list(range(N + 1))

    report_orig = analyze_creg_101072_compliance(
        D, G, agent_names, list(range(N)), verbose=False)
    report_new  = analyze_creg_101072_compliance(
        D_new, G_new, names_new, ids_new, verbose=False)

    result = {
        "original_compliant": (report_orig.rule_10pct_satisfied
                                and report_orig.rule_100kw_satisfied),
        "new_compliant":       (report_new.rule_10pct_satisfied
                                and report_new.rule_100kw_satisfied),
        "new_violations_10pct": report_new.rule_10pct_violations,
        "new_violations_100kw": report_new.rule_100kw_violations,
        "share_change": {
            name: (report_new.max_supply_share_by_agent.get(name, 0)
                   - report_orig.max_supply_share_by_agent.get(name, 0))
            for name in agent_names
        },
    }

    if verbose:
        status = "✓ SIGUE CUMPLIENDO" if result["new_compliant"] else "✗ VIOLA RESTRICCIONES"
        print(f"\n  Impacto de añadir {new_agent_name} ({new_agent_g:.1f} kW PV):")
        print(f"  {status}")
        if not result["new_compliant"]:
            print(f"  Violaciones 10%: {result['new_violations_10pct']}")
            print(f"  Violaciones 100kW: {result['new_violations_100kw']}")

    return result
