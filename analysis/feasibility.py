"""
feasibility.py  — Análisis de factibilidad (Actividad 4.2 de la tesis)
-----------------------------------------------------------------------
Brayan S. Lopez-Mendez · Udenar 2026

Cuatro análisis:

  FA-1: Condición de deserción del mercado P2P (§3.14)
        Restricción de Racionalidad Individual (IR):
          Agente n permanece en P2P sólo si B_n^P2P ≥ B_n^{mejor_alt}
        Se define formalmente y se calcula el umbral crítico pi_gb^*_n
        para cada agente (precio de bolsa que hace al agente indiferente).

  FA-1b: Análisis de racionalidad individual con barrido de pi_gb
        Usando los resultados del SA-1, se determina:
          - ¿Qué agentes actualmente tienen incentivo a quedarse en P2P?
          - ¿A qué precio de bolsa cada agente preferiría salirse?
          - ¿Cuál es el umbral comunitario (pi_gb donde la mayoría deserta)?

  FA-1c: Sensibilidad de deserción al precio al usuario pi_gs (§3.14.4)
        Análisis analítico de primer orden:
          B_n^C1(pi_gs) = autoconsumo_n × pi_gs + excedente_n × pi_bolsa (exacto)
          B_n^C4(pi_gs) ≈ autoconsumo_n × pi_gs              (PDE≈0, exacto)
          B_n^P2P(pi_gs) ≈ B_nom_n × (pi_gs / pi_gs_nom)    (aproximado)
        Resultado teórico: dΔ_n/dπ_gs > 0 → P2P más atractivo a pi_gs alto.
        Umbral pi_gs^*_n: precio retail donde el agente sería indiferente.

  FA-2: Riesgo regulatorio del escenario C4 (CREG 101 072/2025)
        La CREG 101 072 impone:
          - Regla 10%: un agente no puede suministrar >10% de la demanda
          - Límite 100 kW por instalación de autogeneración colectiva
        Se verifica si la comunidad MTE cumple estas restricciones
        y qué pasa si cambia la composición (nueva institución, más PV).

  FA-3: Robustez regulatoria — retiro de participante (propuesta §VII.C)
        Para cada prosumidor n, simula su retiro de la comunidad:
          - ¿La comunidad restante sigue cumpliendo CREG 101 072?
          - Si no: B_C4 cae al régimen individual (sin créditos PDE)
          - Cuantifica la pérdida COP por fragilidad regulatoria de C4
          - Compara con P2P, que no tiene restricciones de composición

  FA-4: Robustez regulatoria — escalamiento de instalación (propuesta §VII.C)
        Para cada prosumidor n, simula escalar su generación (2×, 3×):
          - ¿Cuándo se viola la regla 100 kW o el 10% de participación?
          - Escala máxima sin violar ninguna restricción CREG 101 072
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FeasibilityReport:
    """Reporte completo de factibilidad."""
    # FA-1: Deserción (versión horaria — precio P2P vs precio bolsa)
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


@dataclass
class IndividualRationalityReport:
    """
    §3.14 Condición formal de deserción — Restricción IR por agente.

    Definición matemática:
        Agente n participa en P2P sii  B_n^P2P(π) ≥ B_n^{alt}(π)

    donde:
        B_n^P2P = ahorro_autoconsumo + prima_vendedor (o ahorro_comprador)
        B_n^C4  = ahorro_autoconsumo + créditos_PDE + excedente_bolsa
        π       = (pi_gs, pi_gb, pi_p2p)

    Condición de deserción del agente n:
        Δ_n(pi_gb) = B_n^P2P(pi_gb) - B_n^C4(pi_gb) < 0

    Umbral crítico pi_gb^*_n:
        pi_gb^*_n = sup{ pi_gb : B_n^P2P(pi_gb) ≥ B_n^C4(pi_gb) }

    Deserción comunitaria: cuando la mayoría de agentes tiene Δ_n < 0
    """
    # Beneficio a pi_gb nominal por agente
    benefit_p2p:    dict = field(default_factory=dict)   # nombre → B_n^P2P
    benefit_c4:     dict = field(default_factory=dict)   # nombre → B_n^C4
    surplus_vs_c4:  dict = field(default_factory=dict)   # Δ_n = B_n^P2P − B_n^C4
    surplus_rel:    dict = field(default_factory=dict)   # Δ_n / B_n^C4 (relativo)

    # Clasificación
    stable_agents:  list = field(default_factory=list)   # Δ_n > 0 → prefieren P2P
    risk_agents:    list = field(default_factory=list)   # Δ_n ≤ 0 → prefieren salirse

    # Umbrales críticos por agente (interpolados del barrido PGB)
    critical_pgb:   dict = field(default_factory=dict)   # nombre → pi_gb^*_n

    # Umbral comunitario: pi_gb donde ≥ 50% de agentes desertan
    community_critical_pgb: float = 0.0
    # pi_gb donde P2P deja de ser óptimo a nivel comunidad (B^P2P < B^C4 agregado)
    community_agg_critical_pgb: float = 0.0

    # Tabla de sensibilidad: pgb → {agente: Δ_n(pgb)}
    pgb_vs_surplus: dict = field(default_factory=dict)

    # Resumen textual para el reporte
    summary_lines:  list = field(default_factory=list)


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


def analyze_desertion_individual_rationality(
    sa_pgb_results: list,
    agent_names: list,
    pi_gb_nominal: float,
    base_net_p2p: Optional[np.ndarray] = None,    # caso nominal real (no SA-1)
    base_net_c1: Optional[np.ndarray] = None,     # caso nominal real C1
    base_net_c4: Optional[np.ndarray] = None,     # caso nominal real C4
    verbose: bool = True,
) -> IndividualRationalityReport:
    """
    Sec.3.14 — Condición formal de deserción: Restricción de Racionalidad Individual.

    Utiliza los resultados del barrido SA-1 (que ya almacena B_n^P2P y B_n^C4/C1
    por agente a cada valor de pi_gb) para:

      1. Identificar qué agentes actualmente tienen incentivo a quedarse en P2P
         (Delta_n = B_n^P2P − B_n^best_alt > 0 al pi_gb nominal).
         Si se pasan base_net_p2p/c1/c4, usa los valores REALES del caso nominal
         (precios XM variables), no los del SA-1 (pi_bolsa constante). Esto es
         importante porque el SA-1 a pi_gb=280 constante difiere del caso nominal
         donde pi_bolsa_solar ~ 100 COP/kWh.

      2. Para cada agente n, encontrar el umbral crítico pi_gb^*_n:
         el pi_gb donde Delta_n cambia de signo (interpolando entre puntos del barrido)

      3. Calcular el umbral comunitario: pi_gb donde la mayoría deserta

    Parámetros
    ----------
    sa_pgb_results : lista de SensitivityResult con campo net_per_agent
    agent_names    : nombres de los agentes (misma indexación)
    pi_gb_nominal  : precio de bolsa base (COP/kWh)
    """
    report = IndividualRationalityReport()
    if not sa_pgb_results:
        return report

    N = len(agent_names)

    # ── 1. Beneficio a pi_gb_nominal ─────────────────────────────────────
    pgb_vals = [r.param_value for r in sa_pgb_results]
    closest_idx = int(np.argmin(np.abs(np.array(pgb_vals) - pi_gb_nominal)))
    base_res = sa_pgb_results[closest_idx]

    has_c1 = "C1" in (base_res.net_per_agent or {}) or (base_net_c1 is not None)

    for n, name in enumerate(agent_names):
        # Preferir datos reales (caso nominal variable) sobre SA-1 (constante)
        if base_net_p2p is not None:
            b_p2p = float(base_net_p2p[n])
        else:
            b_p2p = float(base_res.net_per_agent["P2P"][n])

        if base_net_c4 is not None:
            b_c4 = float(base_net_c4[n])
        else:
            b_c4 = float(base_res.net_per_agent["C4"][n])

        if base_net_c1 is not None:
            b_c1 = float(base_net_c1[n])
        elif "C1" in (base_res.net_per_agent or {}):
            b_c1 = float(base_res.net_per_agent["C1"][n])
        else:
            b_c1 = b_c4  # sin C1 disponible → usar C4 como único benchmark

        b_alt = max(b_c4, b_c1)
        delta = b_p2p - b_alt
        report.benefit_p2p[name]   = b_p2p
        report.benefit_c4[name]    = b_alt
        report.surplus_vs_c4[name] = delta
        report.surplus_rel[name]   = delta / abs(b_alt) if abs(b_alt) > 1e-10 else 0.0
        if delta > 0:
            report.stable_agents.append(name)
        else:
            report.risk_agents.append(name)

    # ── 2. Umbral crítico pi_gb^*_n por agente ───────────────────────────
    # Para cada agente, Δ_n(pgb) = B_n^P2P(pgb) − max(B_n^C1, B_n^C4)(pgb)
    # Buscar el cruce de signo (o extrapolar si no cruza dentro del rango)

    pgb_arr = np.array(pgb_vals)
    delta_by_agent = {name: np.zeros(len(pgb_vals)) for name in agent_names}

    for i, r in enumerate(sa_pgb_results):
        pgb_surplus_row = {}
        has_c1_i = "C1" in r.net_per_agent
        for n, name in enumerate(agent_names):
            b_p2p = float(r.net_per_agent["P2P"][n])
            b_c4  = float(r.net_per_agent["C4"][n])
            b_c1  = float(r.net_per_agent["C1"][n]) if has_c1_i else b_c4
            b_alt = max(b_c4, b_c1)
            delta_by_agent[name][i] = b_p2p - b_alt
            pgb_surplus_row[name] = b_p2p - b_alt
        report.pgb_vs_surplus[float(r.param_value)] = pgb_surplus_row

    for name in agent_names:
        deltas = delta_by_agent[name]
        threshold = None
        for i in range(len(pgb_arr) - 1):
            if deltas[i] >= 0 and deltas[i + 1] < 0:
                frac = deltas[i] / (deltas[i] - deltas[i + 1])
                threshold = float(pgb_arr[i] + frac * (pgb_arr[i + 1] - pgb_arr[i]))
                break
        if threshold is None:
            if deltas[-1] >= 0:
                threshold = float(pgb_arr[-1]) * 1.1
            else:
                threshold = float(pgb_arr[0]) * 0.9
        report.critical_pgb[name] = round(threshold, 1)

    # ── 3. Umbral comunitario ────────────────────────────────────────────
    thresholds_per_agent = [report.critical_pgb[n] for n in agent_names]
    if thresholds_per_agent:
        report.community_critical_pgb = float(np.median(thresholds_per_agent))
    else:
        report.community_critical_pgb = float(pgb_arr[-1]) * 1.1

    # Umbral agregado: cruce de P2P_total vs mejor_alternativa_total
    for i, r in enumerate(sa_pgb_results):
        b_p2p_tot = r.net_benefit.get("P2P", 0)
        b_c4_tot  = r.net_benefit.get("C4", 0)
        b_c1_tot  = r.net_benefit.get("C1", b_c4_tot)
        b_alt_tot = max(b_c4_tot, b_c1_tot)
        delta_agg = b_p2p_tot - b_alt_tot
        if i > 0:
            prev_p2p  = sa_pgb_results[i-1].net_benefit.get("P2P", 0)
            prev_c4   = sa_pgb_results[i-1].net_benefit.get("C4", 0)
            prev_c1   = sa_pgb_results[i-1].net_benefit.get("C1", prev_c4)
            prev_alt  = max(prev_c4, prev_c1)
            prev_delta = prev_p2p - prev_alt
            if prev_delta >= 0 and delta_agg < 0:
                frac = prev_delta / (prev_delta - delta_agg + 1e-12)
                report.community_agg_critical_pgb = float(
                    pgb_vals[i-1] + frac * (pgb_vals[i] - pgb_vals[i-1]))
                break
    if report.community_agg_critical_pgb == 0.0:
        report.community_agg_critical_pgb = float(pgb_arr[-1]) * 1.1

    # ── 4. Verbose ───────────────────────────────────────────────────────
    alt_label = "max(C1,C4)" if has_c1 else "C4"
    lines = []
    lines.append(f"\n  Sec.3.14 Desercion -- Condicion de Racionalidad Individual (IR)")
    lines.append(f"  " + "-"*63)
    lines.append(f"  Definicion formal:")
    lines.append(f"    Agente n permanece en P2P sii  B_n^P2P(pi) >= B_n^{{{alt_label}}}(pi)")
    lines.append(f"    Delta_n = B_n^P2P - B_n^{alt_label}  (>0 -> P2P preferido)")
    lines.append(f"    pi_gb^*_n = pi_gb donde Delta_n = 0  (punto de indiferencia)")
    lines.append(f"")
    lines.append(f"  A pi_gb ~= {pi_gb_nominal:.0f} COP/kWh (alt={alt_label}):")
    lines.append(f"  {'Agente':<12} {'B_P2P':>10} {'B_alt':>10} {'Delta_n':>10}"
                 f"  {'Dn/B_alt':>9}  {'pi_gb*':>9}  {'Estado'}")
    lines.append(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10}"
                 f"  {'-'*9}  {'-'*9}  {'-'*15}")

    for name in agent_names:
        b_p2p = report.benefit_p2p[name]
        b_alt = report.benefit_c4[name]
        delta = report.surplus_vs_c4[name]
        rel   = report.surplus_rel[name]
        thr   = report.critical_pgb[name]
        estado = "OK estable" if name in report.stable_agents else "!! en riesgo"
        thr_str = f">rango" if thr > pgb_arr[-1] * 1.05 else f"{thr:.0f}"
        lines.append(f"  {name:<12} {b_p2p:>10,.0f} {b_alt:>10,.0f} {delta:>+10,.0f}"
                     f"  {rel:>+8.1%}  {thr_str:>9}  {estado}")

    lines.append(f"")
    lines.append(f"  Agentes estables (P2P > {alt_label}): {len(report.stable_agents)}/{N} "
                 f"({', '.join(report.stable_agents) or 'ninguno'})")
    lines.append(f"  Agentes en riesgo (P2P <= {alt_label}): {len(report.risk_agents)}/{N} "
                 f"({', '.join(report.risk_agents) or 'ninguno'})")
    lines.append(f"")
    thr_agg_str = (f"{report.community_agg_critical_pgb:.0f}"
                   if report.community_agg_critical_pgb < pgb_arr[-1] * 1.05
                   else f">rango (>{pgb_arr[-1]:.0f})")
    lines.append(f"  Umbral comunitario (mediana individual): "
                 f"{report.community_critical_pgb:.0f} COP/kWh")
    lines.append(f"  Umbral agregado P2P < {alt_label}:      {thr_agg_str} COP/kWh")
    lines.append(f"")
    lines.append(f"  Tabla sensibilidad Delta_n(pi_gb):")
    header = "  " + f"{'pi_gb':>6}" + "".join(f"  {n:>9}" for n in agent_names) + f"  {'Sum-D':>9}"
    lines.append(header)
    lines.append("  " + "-" * (6 + 11 * (N + 1)))
    for r in sa_pgb_results:
        pgb_v = r.param_value
        row_deltas = report.pgb_vs_surplus.get(pgb_v, {})
        total_delta = sum(row_deltas.values())
        row_str = f"  {pgb_v:>6.0f}"
        for name in agent_names:
            d = row_deltas.get(name, 0)
            row_str += f"  {d:>+9,.0f}"
        row_str += f"  {total_delta:>+9,.0f}"
        lines.append(row_str)

    report.summary_lines = lines

    if verbose:
        for line in lines:
            print(line)

    return report


def analyze_desertion_sensitivity_pgs(
    D: np.ndarray,
    G_klim: np.ndarray,
    pi_gs_nominal: float,
    pi_bolsa: np.ndarray,
    agent_names: list,
    prosumer_ids: list,
    base_net_p2p: np.ndarray,
    base_net_c4: np.ndarray,
    base_net_c1: Optional[np.ndarray] = None,
    pgs_multipliers: Optional[list] = None,
    verbose: bool = True,
) -> dict:
    """
    FA-1c — §3.14.4: Sensibilidad de la condición IR al precio retail pi_gs.

    Metodología (analítica de primer orden):
      - C1_n(pi_gs) = autoconsumo_n × pi_gs + excedente_n × mean(pi_bolsa)
        (exacto: el crédito escala con pi_gs, el excedente no)
      - C4_n(pi_gs) ≈ autoconsumo_n × pi_gs
        (exacto para esta comunidad: excedente comunitario neto = 0)
      - P2P_n(pi_gs) ≈ base_net_p2p[n] × (pi_gs / pi_gs_nominal)
        (aproximado: pi_star fijado por Stackelberg en función de pi_gb;
         todos los términos escalan proporcional a pi_gs)

    Resultado teórico: dΔ_n/dπ_gs = (escala P2P - escala mejor_alt) × ... ≥ 0
    → a mayor pi_gs, el P2P es relativamente más atractivo (compradores ahorran
      más en cada kWh que compran a pi_star < pi_gs).

    Retorna:
        {
          "pgs_values": [...],
          "delta_by_agent": {nombre: [Δ_n(pgs_1), Δ_n(pgs_2), ...]},
          "stable_at_pgs": {nombre: [bool, bool, ...]},
          "critical_pgs": {nombre: float},   # pi_gs donde Δ_n = 0 (None si >rango)
          "summary_lines": [...]
        }
    """
    if pgs_multipliers is None:
        pgs_multipliers = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0]

    pi_bolsa_mean = float(np.mean(pi_bolsa))
    pgs_values = [pi_gs_nominal * m for m in pgs_multipliers]

    # Pre-calcular autoconsumo y excedente individuales (usando D y G_klim)
    autoconsumo = np.array([
        float(np.sum(np.minimum(np.maximum(G_klim[n], 0), np.maximum(D[n], 0))))
        for n in range(D.shape[0])
    ])
    excedente = np.array([
        float(np.sum(np.maximum(G_klim[n] - D[n], 0)))
        for n in range(D.shape[0])
    ])

    result = {
        "pgs_values": pgs_values,
        "delta_by_agent": {name: [] for name in agent_names},
        "stable_at_pgs": {name: [] for name in agent_names},
        "critical_pgs": {},
        "summary_lines": [],
    }

    table = []
    for pgs in pgs_values:
        row = {"pgs": pgs}
        for n, name in enumerate(prosumer_ids if prosumer_ids else range(D.shape[0])):
            idx = n  # index into agent_names and benefit arrays
            # C1: exacto
            b_c1 = autoconsumo[name] * pgs + excedente[name] * pi_bolsa_mean
            if base_net_c1 is not None:
                # Re-escalar usando proporción: C1 sin surplus = autoconsumo × pi_gs
                b_c1_nom = float(base_net_c1[name])
                auto_nom  = autoconsumo[name] * pi_gs_nominal
                surplus_nom = float(base_net_c1[name]) - auto_nom
                b_c1 = autoconsumo[name] * pgs + surplus_nom
            # C4: exacto (PDE≈0)
            b_c4 = float(base_net_c4[name]) * (pgs / pi_gs_nominal)
            # P2P: proporcional (aproximación)
            b_p2p = float(base_net_p2p[name]) * (pgs / pi_gs_nominal)
            b_alt = max(b_c1, b_c4)
            delta = b_p2p - b_alt
            result["delta_by_agent"][agent_names[idx]].append(delta)
            result["stable_at_pgs"][agent_names[idx]].append(delta > 0)
            row[agent_names[idx]] = delta
        table.append(row)

    # Umbral crítico pi_gs^*_n (interpolación)
    for name in agent_names:
        deltas = result["delta_by_agent"][name]
        threshold = None
        for i in range(len(pgs_values) - 1):
            if deltas[i] < 0 and deltas[i + 1] >= 0:
                frac = -deltas[i] / (deltas[i + 1] - deltas[i] + 1e-12)
                threshold = pgs_values[i] + frac * (pgs_values[i + 1] - pgs_values[i])
                break
        result["critical_pgs"][name] = round(threshold, 1) if threshold else None

    # Verbose / summary lines
    lines = []
    lines.append("\n  FA-1c — §3.14.4: Sensibilidad IR al precio al usuario (pi_gs)")
    lines.append("  " + "-"*60)
    lines.append(f"  Base: pi_gs_nom = {pi_gs_nominal:.0f} COP/kWh")
    lines.append(f"  C1/C4: calculados analíticamente (autoconsumo × pi_gs)")
    lines.append(f"  P2P: escala proporcional a pi_gs (aprox. Stackelberg)")
    lines.append(f"  Interpretación: Δ_n > 0 → agente prefiere P2P")
    lines.append(f"")
    header = f"  {'pi_gs':>7}" + "".join(f"  {n:>9}" for n in agent_names)
    lines.append(header)
    lines.append("  " + "-" * (7 + 11 * len(agent_names)))
    for row in table:
        pgs = row["pgs"]
        mark = " ←nom" if abs(pgs - pi_gs_nominal) < 1 else ""
        row_str = f"  {pgs:>7.0f}"
        for name in agent_names:
            d = row.get(name, 0)
            row_str += f"  {d:>+9,.0f}"
        row_str += mark
        lines.append(row_str)

    lines.append(f"")
    lines.append(f"  Umbrales pi_gs^*_n (indiferencia):")
    for name in agent_names:
        thr = result["critical_pgs"][name]
        if thr is None:
            s = f"    {name:<12}: P2P estable en todo el rango evaluado"
        else:
            s = f"    {name:<12}: pi_gs^* ≈ {thr:.0f} COP/kWh"
        lines.append(s)

    lines.append(f"")
    lines.append(f"  Conclusión teórica:")
    lines.append(f"  dΔ_n/dπ_gs ≈ (escala_P2P − escala_C1/C4) > 0 para compradores P2P")
    lines.append(f"  → mayor CU fortalece el incentivo a quedarse en P2P.")

    result["summary_lines"] = lines
    if verbose:
        for line in lines:
            print(line)

    return result


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


# ─────────────────────────────────────────────────────────────────────────────
# FA-3 / FA-4: Robustez regulatoria (propuesta §VII.C)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class WithdrawalRiskReport:
    """
    FA-3: Impacto del retiro de cada prosumidor sobre el régimen C4.

    by_agent[nombre] = {
        'compliant'          : bool   — ¿la comunidad restante sigue en AGRC?
        'B_C4_full'          : float  — beneficio C4 de la comunidad completa (COP)
        'B_C4_remaining'     : float  — beneficio C4 de la comunidad sin n (COP)
        'B_fallback'         : float  — beneficio sin AGRC (régimen individual, COP)
        'B_P2P_remaining'    : float  — estimación P2P sin n (conservadora, COP)
        'loss_C4'            : float  — pérdida por fragilidad = B_C4_remaining - B_fallback
        'flexibility_premium': float  — B_P2P_remaining - B_fallback
        'violated_rules'     : list   — ['10pct'] | ['100kw'] | []
    }
    community_at_risk          : bool  — algún retiro invalida el AGRC
    n_risky_withdrawals        : int   — cuántos retiros causan no-cumplimiento
    flexibility_premium_total  : float — Σ premios sobre retiros que invalidan AGRC
    scaling_risk               : dict  — FA-4: nombre → {'max_ok_scale', '2x_ok', '3x_ok'}
    """
    by_agent:                  dict  = field(default_factory=dict)
    community_at_risk:         bool  = False
    n_risky_withdrawals:       int   = 0
    flexibility_premium_total: float = 0.0
    scaling_risk:              dict  = field(default_factory=dict)


def analyze_withdrawal_risk(
    D:                  np.ndarray,
    G:                  np.ndarray,
    G_klim:             np.ndarray,
    pi_gs:              float,
    pi_gb:              float,
    pi_bolsa:           np.ndarray,
    pde:                np.ndarray,
    prosumer_ids:       list,
    agent_names:        list,
    net_benefit_p2p:    np.ndarray,
    net_benefit_c4_full: np.ndarray,
    capacity:           Optional[np.ndarray] = None,
    capacity_limit_kw:  float = 100.0,
    share_limit:        float = 0.10,
    verbose:            bool  = True,
) -> "WithdrawalRiskReport":
    """
    FA-3: Para cada prosumidor n, simula su retiro de la comunidad.

    Si la comunidad restante viola CREG 101 072:
      → B_fallback = régimen individual (autoconsumo + excedente a bolsa; sin PDE)
    Si la comunidad restante sigue cumpliendo:
      → B_fallback = B_C4_remaining (sin penalización)

    Flexibility premium P2P = B_P2P_remaining - B_fallback
      (cuantifica qué tanto más gana P2P que el fallback de C4 cuando alguien se va)
    """
    from scenarios.scenario_c4_creg101072 import (
        run_c4_creg101072, compute_pde_weights,
    )
    from scenarios.scenario_c3_spot import run_c3_spot

    N, T = D.shape
    report = WithdrawalRiskReport()

    B_C4_full = float(np.sum(net_benefit_c4_full))

    if verbose:
        print("\n  FA-3: Robustez regulatoria — retiro de participante")
        print(f"    Escenario: retiro de cada prosumidor → impacto sobre AGRC C4")
        print(f"    Beneficio C4 comunidad completa: {B_C4_full:,.0f} COP")
        print(f"    {'Agente':<12} {'Cumple?':>8} {'B_C4_rest':>12} {'B_fallback':>12} "
              f"{'B_P2P_rest':>12} {'FP (COP)':>12} {'Reglas violadas'}")
        print(f"    {'─'*80}")

    risky = 0
    fp_total = 0.0

    for n in prosumer_ids:
        name = agent_names[n] if n < len(agent_names) else f"A{n+1}"

        # Máscara de agentes restantes
        mask = [m for m in range(N) if m != n]
        D_r    = D[mask, :]
        G_r    = G_klim[mask, :]        # generación limitada
        G_raw_r = G[mask, :]

        # PDE para la comunidad restante (proporcional a capacidad)
        if capacity is not None:
            cap_r = capacity[mask]
        else:
            cap_r = np.maximum(G_raw_r.mean(axis=1), 0.0)
        pde_r = compute_pde_weights(cap_r)

        # IDs de prosumidores en la comunidad restante
        new_ids_map  = {old: new for new, old in enumerate(mask)}
        pros_r  = [new_ids_map[m] for m in prosumer_ids if m != n]
        cons_r  = []  # MTE: todos son prosumidores

        # Beneficio C4 comunidad restante
        c4_r = run_c4_creg101072(
            D_r, G_raw_r, pi_gs, pi_bolsa, pde_r,
            capacity=cap_r,
        )
        B_C4_remaining = float(c4_r["aggregate"]["total_net_benefit"])

        # Verificar cumplimiento CREG 101 072 para la comunidad restante
        names_r = [agent_names[m] for m in mask]
        rep_r   = analyze_creg_101072_compliance(
            D_r, G_raw_r, names_r, pros_r,
            capacity_limit_kw=capacity_limit_kw,
            share_limit=share_limit,
            verbose=False,
        )
        compliant = rep_r.rule_10pct_satisfied and rep_r.rule_100kw_satisfied

        violated = []
        if not rep_r.rule_10pct_satisfied:
            violated.append("10%")
        if not rep_r.rule_100kw_satisfied:
            violated.append("100kW")

        # Fallback: si AGRC inválido → régimen individual (C3-like, sin PDE)
        if compliant:
            B_fallback = B_C4_remaining
        else:
            c3_r = run_c3_spot(D_r, G_raw_r, pi_gs, pi_bolsa, pros_r, cons_r)
            B_fallback = float(c3_r["aggregate"]["total_net_benefit"])

        # P2P restante (estimación conservadora: excluye net_benefit del agente retirado)
        B_P2P_remaining = float(np.sum(net_benefit_p2p[mask]))

        loss_C4           = B_C4_remaining - B_fallback
        flexibility_premium = B_P2P_remaining - B_fallback

        report.by_agent[name] = {
            "compliant":           compliant,
            "B_C4_full":           B_C4_full,
            "B_C4_remaining":      B_C4_remaining,
            "B_fallback":          B_fallback,
            "B_P2P_remaining":     B_P2P_remaining,
            "loss_C4":             loss_C4,
            "flexibility_premium": flexibility_premium,
            "violated_rules":      violated,
        }

        if not compliant:
            risky      += 1
            fp_total   += flexibility_premium

        if verbose:
            tag = "✗ VIOLA" if not compliant else "✓"
            viol_str = ",".join(violated) if violated else "—"
            print(f"    {name:<12} {tag:>8} {B_C4_remaining:>12,.0f} "
                  f"{B_fallback:>12,.0f} {B_P2P_remaining:>12,.0f} "
                  f"{flexibility_premium:>12,.0f}  {viol_str}")

    report.community_at_risk         = risky > 0
    report.n_risky_withdrawals       = risky
    report.flexibility_premium_total = fp_total

    if verbose:
        print(f"    {'─'*80}")
        status = "⚠ SÍ" if report.community_at_risk else "✓ NO"
        print(f"    Comunidad en riesgo: {status}  "
              f"({risky}/{len(prosumer_ids)} retiros invalidan AGRC)")
        if risky > 0:
            print(f"    Prima de flexibilidad P2P total: {fp_total:,.0f} COP")
            print(f"    → P2P mantiene operatividad donde C4 perdería el régimen AGRC")

    return report


def analyze_scaling_risk(
    G:              np.ndarray,
    prosumer_ids:   list,
    agent_names:    list,
    D:              np.ndarray,
    capacity_limit_kw: float = 100.0,
    share_limit:    float = 0.10,
    scales:         list  = None,
    verbose:        bool  = True,
) -> dict:
    """
    FA-4: Para cada prosumidor n, evalúa hasta qué escala puede crecer
    su generación sin violar las restricciones de CREG 101 072.

    Restricciones verificadas:
      - Regla 10%:   G_n_scaled.mean() / D_total.mean() ≤ share_limit
      - Límite 100 kW: G_n_scaled.max() ≤ capacity_limit_kw

    Retorna dict: nombre → {'max_ok_scale': float, '2x_ok': bool, '3x_ok': bool}
    """
    if scales is None:
        scales = [1.5, 2.0, 2.5, 3.0]

    N, T      = G.shape
    D_total   = float(D.sum(axis=0).mean())
    result    = {}

    if verbose:
        print("\n  FA-4: Robustez regulatoria — escalamiento de instalación")
        print(f"    D_total media: {D_total:.1f} kW  |  límite 100 kW  |  share ≤ {share_limit*100:.0f}%")
        print(f"    {'Agente':<12} {'G_actual':>10} {'share%':>8}  "
              + "  ".join(f"{s}×" for s in scales))
        print(f"    {'─'*60}")

    for n in prosumer_ids:
        name    = agent_names[n] if n < len(agent_names) else f"A{n+1}"
        g_mean  = float(G[n].mean())
        g_max   = float(G[n].max())
        share0  = g_mean / max(D_total, 1e-6)

        scale_ok = {}
        max_ok   = 1.0
        for s in scales:
            g_mean_s = g_mean * s
            g_max_s  = g_max  * s
            ok_share = (g_mean_s / max(D_total, 1e-6)) <= share_limit
            ok_100kw = g_max_s <= capacity_limit_kw
            ok = ok_share and ok_100kw
            scale_ok[s] = ok
            if ok:
                max_ok = s

        result[name] = {
            "g_mean_kw":     round(g_mean, 2),
            "g_max_kw":      round(g_max, 2),
            "share_pct":     round(share0 * 100, 2),
            "max_ok_scale":  max_ok,
            "2x_ok":         scale_ok.get(2.0, False),
            "3x_ok":         scale_ok.get(3.0, False),
            "scale_detail":  scale_ok,
        }

        if verbose:
            flags = "  ".join("✓" if scale_ok[s] else "✗" for s in scales)
            print(f"    {name:<12} {g_mean:>10.2f} {share0*100:>8.1f}%  {flags}  "
                  f"→ max ok: {max_ok}×")

    return result


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
