"""
sensitivity.py  — Análisis de sensibilidad (Objetivo 4 de la tesis)
--------------------------------------------------------------------
Brayan S. Lopez-Mendez · Udenar 2026

Implementa dos barridos paramétricos:

  SA-1: Variación del precio de bolsa PGB (200 → 500 COP/kWh)
        Representa: año normal, sequía severa, El Niño extremo, escasez
        Pregunta: ¿cuándo C3 supera a C1? ¿cuándo el P2P sigue siendo óptimo?

  SA-2: Variación de cobertura PV (11% → 100%)
        Representa: escalar los sistemas solares de las instituciones
        Pregunta: ¿qué cobertura mínima hace que P2P domine claramente?

Cada barrido corre la simulación completa y recopila:
  - Ganancia neta por escenario
  - IE (equidad) del P2P
  - PoF (Price of Fairness) P2P vs C4
  - Horas de mercado activo
"""

import time
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SensitivityResult:
    """Resultado de un punto del barrido paramétrico."""
    param_name:  str
    param_value: float
    net_benefit: dict = field(default_factory=dict)   # por escenario
    net_per_agent: dict = field(default_factory=dict) # P2P y C4 por agente
    ie_p2p:      float = 0.0
    rpe:         float = 0.0
    ss_p2p:      float = 0.0
    sc_p2p:      float = 0.0
    market_hours: int  = 0
    kwh_p2p:     float = 0.0


def run_sensitivity_pgb(
    D: np.ndarray,
    G: np.ndarray,
    G_klim: np.ndarray,
    agents,
    grid_base,
    solver,
    p2p_results_base: list,
    pi_gb_range: Optional[np.ndarray] = None,
    pde: Optional[np.ndarray] = None,
    prosumer_ids: Optional[list] = None,
    verbose: bool = True,
) -> list:
    """
    SA-1: Varía PGB entre pi_gb_range y recalcula los escenarios C1-C4.
    El mercado P2P (p2p_results_base) se mantiene fijo — su despacho no
    cambia con el precio de bolsa, solo cambia la valoración monetaria.

    pi_gb_range: array de precios PGB a evaluar (COP/kWh)
                 default: [200, 250, 300, 350, 400, 450, 500]
    """
    import sys; sys.path.insert(0, '..')
    from scenarios import run_comparison

    if pi_gb_range is None:
        pi_gb_range = np.array([200, 250, 280, 300, 350, 400, 450, 500])
    if prosumer_ids is None:
        prosumer_ids = list(range(D.shape[0]))

    T  = D.shape[1]
    N  = D.shape[0]
    results = []

    if verbose:
        print(f"\n  SA-1: Sensibilidad PGB  ({len(pi_gb_range)} puntos)")
        print(f"  {'PGB':>6}  {'P2P':>10}  {'C1':>10}  {'C3':>10}  "
              f"{'C4':>10}  {'IE':>6}  {'PoF':>6}")
        print("  " + "─"*68)

    for pgb in pi_gb_range:
        pi_bolsa = np.full(T, pgb)
        pde_v    = pde if pde is not None else np.ones(N)/N

        cr = run_comparison(
            D=D, G_klim=G_klim, G_raw=G,
            p2p_results=p2p_results_base,
            pi_gs=grid_base.pi_gs, pi_gb=pgb,
            pi_bolsa=pi_bolsa,
            prosumer_ids=prosumer_ids, consumer_ids=[],
            pde=pde_v, pi_ppa=pgb + 0.5*(grid_base.pi_gs - pgb),
            capacity=np.maximum(G.mean(axis=1), 0),
        )

        active = [r for r in p2p_results_base
                  if r.P_star is not None and np.sum(r.P_star) > 1e-4]
        kwh = sum(float(np.sum(r.P_star)) for r in active)

        sr = SensitivityResult(
            param_name="PGB_COP_kWh", param_value=float(pgb),
            net_benefit={e: cr.net_benefit.get(e, 0) for e in ["P2P","C1","C2","C3","C4"]},
            net_per_agent={
                "P2P": cr.net_benefit_per_agent["P2P"].tolist(),
                "C1":  cr.net_benefit_per_agent["C1"].tolist(),
                "C4":  cr.net_benefit_per_agent["C4"].tolist(),
            },
            ie_p2p=cr.equity_index.get("P2P", 0),
            rpe=cr.rpe or 0,
            ss_p2p=cr.self_sufficiency.get("P2P", 0),
            sc_p2p=cr.self_consumption.get("P2P", 0),
            market_hours=len(active),
            kwh_p2p=kwh,
        )
        results.append(sr)

        if verbose:
            nb = sr.net_benefit
            print(f"  {pgb:>6.0f}  {nb['P2P']:>10,.0f}  {nb['C1']:>10,.0f}  "
                  f"{nb['C3']:>10,.0f}  {nb['C4']:>10,.0f}  "
                  f"{sr.ie_p2p:>6.3f}  {sr.rpe:>6.3f}")

    return results


def run_sensitivity_pv(
    D: np.ndarray,
    G_base: np.ndarray,
    agents,
    grid,
    solver,
    pv_factors: Optional[np.ndarray] = None,
    pde: Optional[np.ndarray] = None,
    prosumer_ids: Optional[list] = None,
    verbose: bool = True,
) -> list:
    """
    SA-2: Escala la generación G multiplicando por pv_factors.
    Simula qué pasaría si las instituciones instalan más capacidad solar.

    pv_factors: factores de escala sobre G_base (1.0 = actual)
                [1.0, 2.0, 3.0, 4.5, 9.1] → coberturas [11%,22%,33%,50%,100%]
    """
    import sys; sys.path.insert(0, '..')
    from core.ems_p2p import EMSP2P
    from core.market_prep import compute_generation_limit
    from scenarios import run_comparison

    if pv_factors is None:
        # Factores para coberturas: 11%, 20%, 33%, 50%, 75%, 100%
        baseline_cov = float(G_base.mean() / max(D.mean(), 1e-6))
        targets = [0.11, 0.20, 0.33, 0.50, 0.75, 1.00]
        pv_factors = np.array([t / max(baseline_cov, 0.01) for t in targets])
        pv_factors = pv_factors[pv_factors >= 0.99]  # no reducir

    if prosumer_ids is None:
        prosumer_ids = list(range(D.shape[0]))

    T, N = D.shape[1], D.shape[0]
    results = []

    if verbose:
        print(f"\n  SA-2: Sensibilidad cobertura PV  ({len(pv_factors)} puntos)")
        print(f"  {'Factor':>7}  {'Cob%':>6}  {'P2P':>10}  {'C4':>10}  "
              f"{'IE':>6}  {'Horas':>6}  {'kWh':>7}")
        print("  " + "─"*62)

    ems = EMSP2P(agents, grid, solver)

    for factor in pv_factors:
        G_scaled = G_base * factor
        G_klim_s = np.zeros((N, T))
        for k in range(T):
            G_klim_s[:, k] = compute_generation_limit(
                G_scaled[:, k], agents.a, agents.b, agents.c, grid.pi_gs)

        p2p_res, _, _d = ems.run(D, G_scaled)

        cov = G_scaled.sum() / max(D.sum(), 1)
        pde_v = pde if pde is not None else np.ones(N)/N
        pi_bolsa = np.full(T, grid.pi_gb)

        cr = run_comparison(
            D=D, G_klim=G_klim_s, G_raw=G_scaled,
            p2p_results=p2p_res,
            pi_gs=grid.pi_gs, pi_gb=grid.pi_gb,
            pi_bolsa=pi_bolsa,
            prosumer_ids=prosumer_ids, consumer_ids=[],
            pde=pde_v, pi_ppa=grid.pi_gb + 0.5*(grid.pi_gs - grid.pi_gb),
            capacity=np.maximum(G_scaled.mean(axis=1), 0),
        )

        active = [r for r in p2p_res
                  if r.P_star is not None and np.sum(r.P_star) > 1e-4]
        kwh = sum(float(np.sum(r.P_star)) for r in active)

        sr = SensitivityResult(
            param_name="PV_factor", param_value=float(factor),
            net_benefit={e: cr.net_benefit.get(e, 0) for e in ["P2P","C1","C2","C3","C4"]},
            net_per_agent={
                "P2P": cr.net_benefit_per_agent["P2P"].tolist(),
                "C4":  cr.net_benefit_per_agent["C4"].tolist(),
            },
            ie_p2p=cr.equity_index.get("P2P", 0),
            rpe=cr.rpe or 0,
            ss_p2p=cr.self_sufficiency.get("P2P", 0),
            sc_p2p=cr.self_consumption.get("P2P", 0),
            market_hours=len(active),
            kwh_p2p=kwh,
        )
        results.append(sr)

        if verbose:
            nb = sr.net_benefit
            print(f"  {factor:>7.2f}  {cov*100:>5.0f}%  "
                  f"{nb['P2P']:>10,.0f}  {nb['C4']:>10,.0f}  "
                  f"{sr.ie_p2p:>6.3f}  {len(active):>6}  {kwh:>7.1f}")

    return results


def run_sensitivity_ppa(
    D: np.ndarray,
    G_klim: np.ndarray,
    G_raw: np.ndarray,
    pi_gs: float,
    pi_gb: float,
    pi_bolsa: np.ndarray,
    p2p_results: list,
    prosumer_ids: list,
    consumer_ids: list,
    pde: Optional[np.ndarray] = None,
    capacity: Optional[np.ndarray] = None,
    ppa_factors: Optional[list] = None,
    verbose: bool = True,
) -> list:
    """
    SA-3 — §3.8: Sensibilidad al precio del contrato bilateral (pi_ppa).

    Varía pi_ppa como fracción del rango [pi_gb, pi_gs]:
        pi_ppa(f) = pi_gb + f × (pi_gs - pi_gb),  f ∈ [0, 1]

    f = 0 → pi_ppa = pi_gb  (todo el beneficio al comprador)
    f = 1 → pi_ppa = pi_gs  (todo el beneficio al vendedor/generador)
    f = 0.5 → punto medio (default actual)

    No re-ejecuta el EMS P2P — los despachos P2P son fijos.
    Solo re-evalúa C2 en cada punto; los demás escenarios (C1, C3, C4, P2P)
    son independientes de pi_ppa y sirven como referencia constante.

    Retorna lista de dicts con:
        ppa_factor, pi_ppa, net_benefit (por escenario),
        net_per_agent_c2, surplus_gen_c2, saving_cons_c2
    """
    from scenarios import run_comparison

    if ppa_factors is None:
        ppa_factors = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5,
                       0.6, 0.7, 0.8, 0.9, 1.0]

    N = D.shape[0]
    results = []

    if verbose:
        spread = pi_gs - pi_gb
        print(f"\n  SA-3: Sensibilidad PPA  (pi_gb={pi_gb:.0f} → pi_gs={pi_gs:.0f} "
              f"COP/kWh, Δ={spread:.0f})")
        print(f"  {'Factor':>7}  {'pi_ppa':>7}  {'C2 total':>10}  "
              f"{'P2P total':>10}  {'C1 total':>10}  {'C4 total':>10}  "
              f"{'C2>P2P':>7}")
        print("  " + "─"*72)

    for f in ppa_factors:
        pi_ppa = pi_gb + f * (pi_gs - pi_gb)

        cr = run_comparison(
            D=D, G_klim=G_klim, G_raw=G_raw,
            p2p_results=p2p_results,
            pi_gs=pi_gs, pi_gb=pi_gb,
            pi_bolsa=pi_bolsa,
            prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
            pde=pde, pi_ppa=pi_ppa,
            capacity=capacity,
        )

        nb = {e: cr.net_benefit.get(e, 0.0) for e in ["P2P", "C1", "C2", "C3", "C4"]}
        c2_per = cr.net_benefit_per_agent["C2"].tolist()

        # Desglose de C2: re-cálculo directo para obtener saving_cons y surplus_gen
        from scenarios.scenario_c2_bilateral import run_c2_bilateral
        c2_raw = run_c2_bilateral(D, G_klim, pi_gs, pi_gb, pi_ppa,
                                   prosumer_ids, consumer_ids)
        agg = c2_raw["aggregate"]

        row = {
            "ppa_factor":       round(f, 2),
            "pi_ppa":           round(pi_ppa, 2),
            "net_benefit":      nb,
            "net_per_agent_c2": c2_per,
            "surplus_gen_c2":   agg["total_savings_gen"],
            "saving_cons_c2":   agg["total_savings_cons"],
            "c2_beats_p2p":     nb["C2"] > nb["P2P"],
        }
        results.append(row)

        if verbose:
            beats = "SI" if row["c2_beats_p2p"] else "no"
            print(f"  {f:>7.2f}  {pi_ppa:>7.0f}  {nb['C2']:>10,.0f}  "
                  f"{nb['P2P']:>10,.0f}  {nb['C1']:>10,.0f}  {nb['C4']:>10,.0f}  "
                  f"{beats:>7}")

    if verbose:
        # Precio óptimo para C2 (max net_benefit)
        best = max(results, key=lambda r: r["net_benefit"]["C2"])
        print(f"\n  Precio óptimo C2: {best['pi_ppa']:.0f} COP/kWh "
              f"(factor={best['ppa_factor']:.2f})  →  {best['net_benefit']['C2']:,.0f} COP")
        never_beats = not any(r["c2_beats_p2p"] for r in results)
        if never_beats:
            print(f"  C2 nunca supera P2P en el rango evaluado.")
        else:
            cross = next(r for r in results if r["c2_beats_p2p"])
            print(f"  C2 supera P2P a partir de pi_ppa ≥ {cross['pi_ppa']:.0f} COP/kWh "
                  f"(factor={cross['ppa_factor']:.2f})")

    return results


def find_dominance_threshold(sa_pgb: list, sa_pv: list) -> dict:
    """
    Identifica los umbrales donde P2P deja de dominar (cruces de rentabilidad).

    Para cada alternativa X ∈ {C1, C4}:
      - Si P2P siempre supera X: reporta "siempre_mejor"
      - Si P2P siempre pierde vs X: reporta "nunca_mejor"
      - Si hay cruce: reporta el pi_gb donde P2P deja de ser mejor (interpolado)

    Retorna dict con hallazgos para el documento de la tesis.
    """
    findings = {}

    pgb_vals = [r.param_value for r in sa_pgb]
    p2p_gt_c4 = [r.net_benefit["P2P"] > r.net_benefit["C4"] for r in sa_pgb]
    p2p_gt_c1 = [r.net_benefit["P2P"] > r.net_benefit["C1"] for r in sa_pgb]

    # Umbral vs C4: buscar cruce descendente (P2P deja de > C4)
    thr_c4 = _find_descending_threshold(sa_pgb, "C4")
    findings["p2p_always_beats_c4"] = all(p2p_gt_c4)
    findings["pgb_threshold_vs_C4"] = thr_c4 if thr_c4 else ("siempre_mejor" if all(p2p_gt_c4) else "nunca_mejor")

    # Umbral vs C1: buscar cruce descendente (P2P deja de > C1)
    thr_c1 = _find_descending_threshold(sa_pgb, "C1")
    findings["p2p_always_beats_c1"] = all(p2p_gt_c1)
    findings["pgb_threshold_vs_C1"] = thr_c1 if thr_c1 else ("siempre_mejor" if all(p2p_gt_c1) else "nunca_mejor")

    # SA-2: cobertura mínima donde P2P > C4
    if sa_pv:
        pv_coverage = [r.param_value for r in sa_pv]
        pv_p2p_gt_c4 = [r.net_benefit["P2P"] > r.net_benefit["C4"] for r in sa_pv]
        thr_pv = next((pv_coverage[i] for i, v in enumerate(pv_p2p_gt_c4) if v), None)
        findings["pv_threshold_vs_C4"] = thr_pv
        # horas de mercado en cada punto
        findings["market_hours_by_pv"] = {
            r.param_value: r.market_hours for r in sa_pv}

    return findings


def _find_descending_threshold(sa_pgb: list, alt: str) -> Optional[float]:
    """
    Encuentra el pi_gb donde P2P deja de superar la alternativa `alt`
    (cruce descendente: P2P > alt → P2P < alt, al aumentar pi_gb).
    Retorna None si no hay cruce en el rango del barrido.
    """
    pgb_vals = [r.param_value for r in sa_pgb]
    for i in range(len(sa_pgb) - 1):
        delta_i   = sa_pgb[i].net_benefit.get("P2P", 0) - sa_pgb[i].net_benefit.get(alt, 0)
        delta_ip1 = sa_pgb[i+1].net_benefit.get("P2P", 0) - sa_pgb[i+1].net_benefit.get(alt, 0)
        if delta_i > 0 and delta_ip1 <= 0:
            # Interpolación lineal en el cruce
            frac = delta_i / (delta_i - delta_ip1 + 1e-12)
            return float(pgb_vals[i] + frac * (pgb_vals[i+1] - pgb_vals[i]))
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SA-3 (precio al usuario π_gs) — Actividad 4.1 de la propuesta de tesis
# ─────────────────────────────────────────────────────────────────────────────

def run_sensitivity_pgs(
    D:           np.ndarray,
    G:           np.ndarray,
    agents,
    grid_base,
    solver,
    pde:          Optional[np.ndarray] = None,
    prosumer_ids: Optional[list]       = None,
    consumer_ids: Optional[list]       = None,
    pi_gs_range:  Optional[np.ndarray] = None,
    verbose: bool = True,
) -> list:
    """
    SA-3: Varía π_gs (precio al usuario / tarifa retail) y re-ejecuta el EMS completo.

    Motivación (propuesta §VI.D, Actividad 4.1):
      "Sensibilidad relativa: cómo las ganancias netas se afectan ante cambios
       en parámetros operativos: precios de bolsa, irradiancia y variaciones
       regulatorias."

    π_gs es el precio que los usuarios pagan a la red por cada kWh.
    Si π_gs sube → el ahorro por autoconsumo y P2P crece → P2P más atractivo.
    Si π_gs baja → la ventaja del P2P se reduce.

    A diferencia de SA-1 (PGB fijo), SA-3 re-ejecuta el EMS P2P porque G_klim
    depende de π_gs (Algoritmo 1: la restricción de generación usa pi_gs en la
    ecuación cuadrática de costo).

    pi_gs_range: array de precios π_gs a evaluar [COP/kWh o adimensional]
                 default: 7 puntos entre 0.5×π_gs_base y 2.0×π_gs_base
    """
    from core.ems_p2p       import EMSP2P, GridParams
    from core.market_prep   import compute_generation_limit
    from scenarios          import run_comparison

    if prosumer_ids is None:
        prosumer_ids = list(range(D.shape[0]))
    if consumer_ids is None:
        consumer_ids = []

    pi_gs_base = grid_base.pi_gs
    pi_gb      = grid_base.pi_gb

    if pi_gs_range is None:
        pi_gs_range = np.round(
            np.linspace(0.5 * pi_gs_base, 2.0 * pi_gs_base, 7), 0
        )

    N, T  = D.shape
    results = []

    if verbose:
        print(f"\n  SA-3: Sensibilidad π_gs  (π_gs_base={pi_gs_base:.0f}, "
              f"π_gb={pi_gb:.0f})  — {len(pi_gs_range)} puntos")
        print(f"  {'π_gs':>7}  {'Ratio':>6}  {'P2P':>10}  {'C1':>10}  "
              f"{'C4':>10}  {'IE':>6}  {'PoF':>6}  {'Gini-P2P':>9}")
        print("  " + "─"*75)

    ems = EMSP2P(agents, grid_base, solver)

    for pgs in pi_gs_range:
        # Re-calcular G_klim con el nuevo π_gs (depende de la condición de costo)
        G_klim_new = np.zeros((N, T))
        for k in range(T):
            G_klim_new[:, k] = compute_generation_limit(
                G[:, k], agents.a, agents.b, agents.c, float(pgs))

        # Re-ejecutar EMS P2P con π_gs nuevo (afecta G_klim y funciones de bienestar)
        grid_new = GridParams(pi_gs=float(pgs), pi_gb=pi_gb)
        ems_new  = EMSP2P(agents, grid_new, solver)
        p2p_res, G_klim_new, D_star = ems_new.run(D, G)

        pde_v    = pde if pde is not None else np.ones(N) / N
        pi_bolsa = np.full(T, pi_gb)   # precio bolsa fijo en este barrido

        cr = run_comparison(
            D=D_star, G_klim=G_klim_new, G_raw=G,
            p2p_results=p2p_res,
            pi_gs=float(pgs), pi_gb=pi_gb,
            pi_bolsa=pi_bolsa,
            prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
            pde=pde_v,
            pi_ppa=pi_gb + 0.5 * (float(pgs) - pi_gb),
            capacity=np.maximum(G.mean(axis=1), 0),
        )

        active    = [r for r in p2p_res
                     if r.P_star is not None and np.sum(r.P_star) > 1e-4]
        kwh       = sum(float(np.sum(r.P_star)) for r in active)
        gini_p2p  = cr.gini.get("P2P", 0.0)

        sr = SensitivityResult(
            param_name="pi_gs",
            param_value=float(pgs),
            net_benefit={e: cr.net_benefit.get(e, 0) for e in ["P2P","C1","C2","C3","C4"]},
            net_per_agent={
                "P2P": cr.net_benefit_per_agent["P2P"].tolist(),
                "C1":  cr.net_benefit_per_agent["C1"].tolist(),
                "C4":  cr.net_benefit_per_agent["C4"].tolist(),
            },
            ie_p2p=cr.equity_index.get("P2P", 0),
            rpe=cr.rpe or 0,
            ss_p2p=cr.self_sufficiency.get("P2P", 0),
            sc_p2p=cr.self_consumption.get("P2P", 0),
            market_hours=len(active),
            kwh_p2p=kwh,
        )
        results.append(sr)

        if verbose:
            nb    = sr.net_benefit
            ratio = float(pgs) / pi_gs_base
            print(f"  {pgs:>7.0f}  {ratio:>6.2f}  {nb['P2P']:>10,.0f}  "
                  f"{nb['C1']:>10,.0f}  {nb['C4']:>10,.0f}  "
                  f"{sr.ie_p2p:>6.3f}  {sr.rpe:>6.3f}  {gini_p2p:>9.4f}")

    if verbose:
        # Resumen: tendencia de la ventaja P2P al variar π_gs
        deltas = [r.net_benefit["P2P"] - r.net_benefit["C4"] for r in results]
        increasing = all(deltas[i] <= deltas[i+1] for i in range(len(deltas)-1))
        sign = "↑ creciente" if increasing else "no monótona"
        print(f"\n  Tendencia ventaja P2P-C4 vs π_gs: {sign}")
        best = max(results, key=lambda r: r.net_benefit["P2P"] - r.net_benefit["C4"])
        print(f"  Mayor ventaja P2P vs C4 en π_gs = {best.param_value:.0f}  "
              f"(Δ = {best.net_benefit['P2P']-best.net_benefit['C4']:+,.0f})")

    return results
