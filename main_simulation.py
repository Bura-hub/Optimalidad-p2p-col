"""
main_simulation.py  — Tesis Brayan López, Udenar 2026
Sin programa DR. D es insumo fijo (datos reales de la comunidad MTE).

Modos:
  python main_simulation.py                              # datos sintéticos (24h)
  python main_simulation.py --data real                  # datos MTE, perfil diario (24h)
  python main_simulation.py --data real --full           # datos MTE, 5160h completas
  python main_simulation.py --data real --analysis       # + sensibilidad y factibilidad
  python main_simulation.py --data real --analysis --full  # todo, horizonte completo
"""
import sys, os, time, argparse, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

from core.ems_p2p  import EMSP2P, AgentParams, GridParams, SolverParams
from scenarios     import run_comparison, print_comparison_report
from data.base_case_data import (
    get_generation_profiles, get_demand_profiles,
    get_agent_params, get_pde_weights,
    GRID_PARAMS, GRID_PARAMS_REAL, PGS, PGB, PGS_COP, PGB_COP,
)
from data.xm_prices import get_pi_bolsa, get_b_for_real_data


def main(use_real_data=False, full_horizon=False, run_analysis=False):
    t_total_start = time.time()
    print("\n" + "█"*65)
    print("  TESIS: Validación Regulatoria de Mercados P2P en Colombia")
    print("  Brayan S. Lopez-Mendez — Udenar, 2026  [SIN DR]")
    print("█"*65)

    # ── 1. Cargar datos ──────────────────────────────────────────────────
    if use_real_data:
        from data.xm_data_loader import (
            MTEDataLoader, validate_load, print_validation_report,
            daily_profiles,
        )
        mte_root = os.environ.get(
            "MTE_ROOT",
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "MedicionesMTE"),
        )
        print(f"\n[1/5] Cargando datos empíricos MTE...")
        loader = MTEDataLoader(mte_root)
        D_full, G_full, index_full = loader.load(verbose=True)
        print_validation_report(validate_load(D_full, G_full, index_full))

        from scenarios.scenario_c4_creg101072 import compute_pde_weights
        pde = compute_pde_weights(np.maximum(G_full.mean(axis=1), 0))
        cap = np.maximum(G_full.mean(axis=1), 0)
        N   = D_full.shape[0]

        agent_names = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"][:N]
        grid_params = GRID_PARAMS_REAL
        currency    = "COP"

        # Parámetro b calibrado por institución (Actividad 1.2)
        b_cal = get_b_for_real_data(N, agent_names)

        if full_horizon:
            D, G = D_full, G_full
            T    = D.shape[1]
            print(f"\n    Modo: COMPLETO  N={N}  T={T}h ({T//24} días)")
        else:
            D, G = daily_profiles(D_full, G_full, index_full)
            T    = 24
            print(f"\n    Modo: PERFIL DIARIO PROMEDIO  N={N}  T=24h")
            print(f"    Basado en {D_full.shape[1]} horas reales")
            print(f"    Para horizonte completo: --full")

        # Precios de bolsa: real si hay CSV, sintético si no
        xm_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "data", "xm_precios_bolsa.csv")
        pi_bolsa = get_pi_bolsa(T, csv_path=xm_csv if os.path.exists(xm_csv) else None,
                                 scenario="2025_normal")
        print(f"    PGS={PGS_COP} COP/kWh · PGB={pi_bolsa.mean():.0f} COP/kWh (promedio)")
        print(f"    b calibrado: {b_cal.round(0)}")

        prosumer_ids = list(range(N))
        consumer_ids = []

    else:
        print("\n[1/5] Datos sintéticos de validación (modelo base Sofía)...")
        G, D  = get_generation_profiles(), get_demand_profiles()
        p     = get_agent_params()
        pde   = get_pde_weights()
        T     = 24
        N, _  = D.shape
        grid_params  = GRID_PARAMS
        currency     = "$"
        agent_names  = [f"A{i+1}" for i in range(N)]
        b_cal        = np.array(p["b"])
        pi_bolsa     = np.full(T, PGB)
        prosumer_ids = [0, 1, 2, 3]
        consumer_ids = [4, 5]
        cap          = np.array([3., 4., 3., 2., 0., 0.])
        print(f"    N={N}  T={T}h  |  PGS={PGS} · PGB={PGB} (modelo base)")

    # ── 2. EMS P2P ───────────────────────────────────────────────────────
    print("\n[2/5] EMS P2P (RD + Stackelberg)...")
    t0   = time.time()
    grid = GridParams(**grid_params)

    agents = AgentParams(
        N=N, a=np.zeros(N) if use_real_data else np.array(p["a"]),
        b=b_cal if use_real_data else np.array(p["b"]),
        c=np.full(N, 1.2) if use_real_data else np.array(p["c"]),
        lam=np.full(N, 100.0), theta=np.full(N, 0.5), etha=np.full(N, 0.1),
    ) if use_real_data else AgentParams(**p)

    solver = SolverParams(tau=0.001, t_span=(0.0, 0.005),
                          n_points=150, stackelberg_iters=2, parallel=True)
    ems    = EMSP2P(agents, grid, solver)
    p2p_results, G_klim = ems.run(D, G)
    t_p2p = time.time() - t0

    active = [r for r in p2p_results
              if r.P_star is not None and np.sum(r.P_star) > 1e-4]
    kwh    = sum(float(np.sum(r.P_star)) for r in active)
    print(f"    {t_p2p:.1f}s | horas mercado: {len(active)}/{T} | {kwh:.2f} kWh P2P")

    # ── 3. Escenarios C1–C4 ──────────────────────────────────────────────
    print("\n[3/5] Escenarios regulatorios C1–C4...")
    cr = run_comparison(
        D=D, G_klim=G_klim, G_raw=G,
        p2p_results=p2p_results,
        pi_gs=grid_params["pi_gs"], pi_gb=grid_params["pi_gb"],
        pi_bolsa=pi_bolsa,
        prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
        pde=pde, pi_ppa=grid_params["pi_gb"] + 0.5*(grid_params["pi_gs"]-grid_params["pi_gb"]),
        capacity=cap,
    )

    # ── 4. Reporte ───────────────────────────────────────────────────────
    print("\n[4/5] Reporte:")
    print_comparison_report(cr)

    esc = ["P2P", "C1", "C2", "C3", "C4"]
    print(f"\n  Ganancia neta por agente ({currency}/período):")
    print(f"  {'Institución':<12}" + "".join(f"{'  '+e:>14}" for e in esc))
    print("  " + "─"*82)
    for n in range(N):
        name = agent_names[n] if n < len(agent_names) else f"A{n+1}"
        print(f"  {name:<12}" +
              "".join(f"{cr.net_benefit_per_agent[e][n]:>14,.0f}" for e in esc))

    print(f"\n  Ventaja P2P vs C4:")
    for n in range(N):
        name  = agent_names[n] if n < len(agent_names) else f"A{n+1}"
        delta = (cr.net_benefit_per_agent["P2P"][n]
                 - cr.net_benefit_per_agent["C4"][n])
        print(f"    {name:<12}: {'+'if delta>=0 else ''}{delta:>12,.0f} {currency}  "
              f"({'P2P mejor' if delta > 0 else 'C4 mejor'})")

    # ── 5. Exportar base ─────────────────────────────────────────────────
    print("\n[5/5] Exportando resultados y gráficas...")
    base_dir  = os.path.dirname(os.path.abspath(__file__))
    excel_path = _export_base(cr, p2p_results, G_klim, D, base_dir, currency)
    print(f"    Excel → {excel_path}")

    from visualization.plots import generate_all_plots
    plots_dir = os.path.join(base_dir, "graficas")
    generate_all_plots(D=D, G=G, G_klim=G_klim, p2p_results=p2p_results,
                       cr=cr, agent_names=agent_names,
                       out_dir=plots_dir, currency=currency)

    # ── 6. Análisis de sensibilidad y factibilidad (--analysis) ──────────
    sa_pgb, sa_pv, fa_des, fa_creg_rep = [], [], None, None

    if run_analysis:
        print("\n" + "="*65)
        print("  ANÁLISIS DE SENSIBILIDAD Y FACTIBILIDAD")
        print("="*65)

        from analysis.sensitivity import (
            run_sensitivity_pgb, run_sensitivity_pv, find_dominance_threshold)
        from analysis.feasibility import (
            analyze_desertion, analyze_creg_101072_compliance)
        from visualization.plots import generate_sensitivity_plots

        # SA-1: variación PGB
        pgb_range = np.array([200, 250, 280, 300, 350, 400, 450, 500])
        sa_pgb = run_sensitivity_pgb(
            D=D, G=G, G_klim=G_klim, agents=agents, grid_base=grid,
            solver=solver, p2p_results_base=p2p_results,
            pi_gb_range=pgb_range, pde=pde,
            prosumer_ids=prosumer_ids, verbose=True,
        )

        # SA-2: variación cobertura PV
        print(f"\n  SA-2: Ejecutando barrido de cobertura PV...")
        base_cov = float(G.mean() / max(D.mean(), 1e-6))
        targets  = [0.11, 0.20, 0.33, 0.50, 0.75, 1.00]
        pv_factors = np.unique(np.clip(
            [t / max(base_cov, 0.01) for t in targets], 1.0, 10.0))
        sa_pv = run_sensitivity_pv(
            D=D, G_base=G, agents=agents, grid=grid, solver=solver,
            pv_factors=pv_factors, pde=pde,
            prosumer_ids=prosumer_ids, verbose=True,
        )

        # Umbrales de dominancia
        thresholds = find_dominance_threshold(sa_pgb, sa_pv)
        print(f"\n  Umbrales de dominancia P2P:")
        print(f"    P2P > C4 para todo PGB testado: {thresholds.get('p2p_always_beats_c4')}")
        if thresholds.get("pgb_threshold_vs_C4"):
            print(f"    PGB umbral vs C4: {thresholds['pgb_threshold_vs_C4']:.0f} COP/kWh")
        if thresholds.get("pv_threshold_vs_C4"):
            print(f"    Factor PV umbral vs C4: {thresholds['pv_threshold_vs_C4']:.2f}x")

        # FA-1: deserción
        fa_des = analyze_desertion(
            p2p_results=p2p_results, pi_bolsa=pi_bolsa,
            agent_names=agent_names, prosumer_ids=prosumer_ids, verbose=True,
        )

        # FA-2: cumplimiento CREG 101 072
        fa_creg_rep = analyze_creg_101072_compliance(
            D=D, G=G, agent_names=agent_names,
            prosumer_ids=prosumer_ids, verbose=True,
        )

        # Gráficas 7-9
        generate_sensitivity_plots(
            sa_pgb=sa_pgb, sa_pv=sa_pv,
            fa_desertion=fa_des, fa_creg=fa_creg_rep,
            p2p_results=p2p_results, pi_bolsa=pi_bolsa,
            D=D, agent_names=agent_names,
            out_dir=plots_dir, currency=currency,
        )

        # Exportar análisis a Excel
        _export_analysis(sa_pgb, sa_pv, fa_des, fa_creg_rep,
                          thresholds, base_dir, agent_names)

    # ── Reporte de avances para asesores ─────────────────────────────────
    _generate_progress_report(
        cr=cr, p2p_results=p2p_results, G_klim=G_klim, D=D, G=G,
        agent_names=agent_names, currency=currency,
        use_real_data=use_real_data, full_horizon=full_horizon,
        sa_pgb=sa_pgb, sa_pv=sa_pv,
        fa_des=fa_des, fa_creg=fa_creg_rep,
        base_dir=base_dir,
    )

    t_total = time.time() - t_total_start
    print(f"\n✓ Completado en {t_total:.1f}s.")
    return cr, p2p_results


# ── Exportar Excel base ───────────────────────────────────────────────────────

def _export_base(cr, p2p_results, G_klim, D, base_dir, currency):
    path = os.path.join(base_dir, "resultados_comparacion.xlsx")
    esc  = ["P2P", "C1", "C2", "C3", "C4"]
    N, T = G_klim.shape
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        pd.DataFrame({
            "Escenario": esc,
            f"Ganancia_neta_{currency}": [cr.net_benefit[e] for e in esc],
            "SC": [cr.self_consumption.get(e, 0) for e in esc],
            "SS": [cr.self_sufficiency.get(e, 0) for e in esc],
            "IE": [cr.equity_index.get(e, 0) for e in esc],
        }).to_excel(w, sheet_name="Resumen", index=False)
        pd.DataFrame([{"Agente": f"A{n+1}",
                        **{e: cr.net_benefit_per_agent[e][n] for e in esc}}
                       for n in range(cr.n_agents)]
                     ).to_excel(w, sheet_name="Por_agente", index=False)
        pd.DataFrame([{
            "Hora": r.k+1,
            "kWh_P2P": float(np.sum(r.P_star)) if r.P_star is not None else 0,
            "SC": r.SC, "SS": r.SS, "IE": r.IE,
            "PS_%": r.PS, "PSR_%": r.PSR,
            "Wj": r.Wj_total, "Wi": r.Wi_total,
        } for r in p2p_results]).to_excel(w, sheet_name="P2P_horario", index=False)
        pd.DataFrame([{
            "PoF_P2P_vs_C4": cr.price_of_fairness,
            "Spread_C4_kWh": float(np.sum(cr.static_spread_24h))
                              if cr.static_spread_24h is not None else 0,
        }]).to_excel(w, sheet_name="Metricas_extra", index=False)
    return path


# ── Exportar análisis de sensibilidad a Excel ─────────────────────────────────

def _export_analysis(sa_pgb, sa_pv, fa_des, fa_creg, thresholds, base_dir, agent_names):
    path = os.path.join(base_dir, "resultados_analisis.xlsx")
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        if sa_pgb:
            rows = []
            for r in sa_pgb:
                row = {"PGB_COP_kWh": r.param_value,
                       "IE_P2P": r.ie_p2p, "PoF": r.pof,
                       "Horas_mercado": r.market_hours, "kWh_P2P": r.kwh_p2p}
                row.update({f"Net_{e}": r.net_benefit[e]
                             for e in ["P2P","C1","C2","C3","C4"]})
                rows.append(row)
            pd.DataFrame(rows).to_excel(w, sheet_name="SA1_PGB", index=False)

        if sa_pv:
            rows = []
            for r in sa_pv:
                row = {"PV_factor": r.param_value,
                       "Cobertura_pct": r.param_value * 0.113 * 100,
                       "IE_P2P": r.ie_p2p, "SS_P2P": r.ss_p2p,
                       "Horas_mercado": r.market_hours, "kWh_P2P": r.kwh_p2p}
                row.update({f"Net_{e}": r.net_benefit[e]
                             for e in ["P2P","C1","C4"]})
                rows.append(row)
            pd.DataFrame(rows).to_excel(w, sheet_name="SA2_PV", index=False)

        if fa_creg:
            rows = []
            for name in agent_names:
                rows.append({
                    "Agente": name,
                    "Participacion_pct": fa_creg.max_supply_share_by_agent.get(name, 0),
                    "Cumple_10pct": name not in fa_creg.rule_10pct_violations,
                    "Capacidad_max_kW": fa_creg.max_capacity_by_agent.get(name, 0),
                    "Cumple_100kW": name not in fa_creg.rule_100kw_violations,
                })
            rows.append({"Agente": "COMUNIDAD",
                          "Robustez_C4": fa_creg.robustness_score})
            pd.DataFrame(rows).to_excel(w, sheet_name="FA_CREG101072", index=False)

        pd.DataFrame([thresholds]).to_excel(w, sheet_name="Umbrales", index=False)
    print(f"    Excel análisis → {path}")
    return path


# ── Reporte de avances para asesores (Markdown) ───────────────────────────────

def _generate_progress_report(cr, p2p_results, G_klim, D, G,
                               agent_names, currency, use_real_data,
                               full_horizon, sa_pgb, sa_pv,
                               fa_des, fa_creg, base_dir):
    """
    Genera un reporte Markdown con los resultados actuales para presentar
    a los asesores Andrés Pantoja y Germán Obando.
    """
    from datetime import datetime
    now   = datetime.now().strftime("%Y-%m-%d %H:%M")
    N, T  = G_klim.shape
    esc   = ["P2P", "C1", "C2", "C3", "C4"]

    active = [r for r in p2p_results
              if r.P_star is not None and np.sum(r.P_star) > 1e-4]
    kwh_p2p = sum(float(np.sum(r.P_star)) for r in active)

    data_mode = ("Empíricos MTE — " + ("5160h completas" if full_horizon
                  else "perfil diario promedio (24h)")) if use_real_data else "Sintéticos (validación)"

    lines = [
        "# Reporte de Avances — Tesis P2P Colombia",
        "",
        f"**Autor:** Brayan S. Lopez-Mendez | **Fecha:** {now}",
        f"**Asesores:** Andrés Pantoja · Germán Obando | **Udenar, 2026**",
        "",
        "---",
        "",
        "## 1. Estado del modelo",
        "",
        f"| Parámetro | Valor |",
        f"|-----------|-------|",
        f"| Datos | {data_mode} |",
        f"| Agentes | {N} instituciones Pasto (MTE) |",
        f"| Horizonte | {T}h ({T//24} días) |",
        f"| Horas con mercado P2P | {len(active)}/{T} ({len(active)/T*100:.1f}%) |",
        f"| Energía P2P total | {kwh_p2p:.1f} kWh/período |",
        f"| Precios | PGS={PGS_COP if use_real_data else PGS} · PGB={PGB_COP if use_real_data else PGB} {currency}/kWh |",
        "",
        "## 2. Datos empíricos MTE",
        "",
        "| Institución | D̄ (kW) | Ḡ (kW) | Cobertura PV |",
        "|-------------|---------|---------|-------------|",
    ]

    for n in range(N):
        name = agent_names[n]
        d_m  = float(D[n].mean())
        g_m  = float(G[n].mean())
        cov  = g_m / max(d_m, 1e-6) * 100
        lines.append(f"| {name} | {d_m:.1f} | {g_m:.1f} | {cov:.0f}% |")

    d_tot = float(D.sum())
    g_tot = float(G.sum())
    lines += [
        f"| **Comunidad** | **{D.mean(axis=1).sum():.1f}** | **{G.mean(axis=1).sum():.1f}** | **{g_tot/max(d_tot,1)*100:.1f}%** |",
        "",
        "## 3. Resultados comparación regulatoria",
        "",
        f"| Escenario | Ganancia neta ({currency}) | SC | SS | IE |",
        "|-----------|--------------------------|-----|-----|-----|",
    ]

    esc_labels = {
        "P2P": "P2P (Stackelberg + RD)",
        "C1": "C1 CREG 174/2021",
        "C2": "C2 Bilateral PPA",
        "C3": "C3 Mercado spot",
        "C4": "C4 CREG 101 072 ★",
    }
    for e in esc:
        nb = cr.net_benefit.get(e, 0)
        sc = cr.self_consumption.get(e, 0)
        ss = cr.self_sufficiency.get(e, 0)
        ie = cr.equity_index.get(e, 0)
        lines.append(f"| {esc_labels[e]} | {nb:,.0f} | {sc:.3f} | {ss:.3f} | {ie:.4f} |")

    pof = cr.price_of_fairness or 0
    spread = float(np.sum(cr.static_spread_24h)) if cr.static_spread_24h is not None else 0
    lines += [
        "",
        f"**Price of Fairness (P2P vs C4):** {pof:.4f}",
        f"**Spread ineficiencia estática C4:** {spread:.3f} kWh/período",
        "",
        "### 3.1 Ventaja P2P vs C4 por institución",
        "",
        f"| Institución | P2P ({currency}) | C4 ({currency}) | Ventaja P2P ({currency}) |",
        "|-------------|---------|---------|-----------------|",
    ]

    for n in range(N):
        name  = agent_names[n]
        p2p_n = cr.net_benefit_per_agent["P2P"][n]
        c4_n  = cr.net_benefit_per_agent["C4"][n]
        delta = p2p_n - c4_n
        sign  = "+" if delta >= 0 else ""
        win   = "✓ P2P mejor" if delta > 0 else "✗ C4 mejor"
        lines.append(f"| {name} | {p2p_n:,.0f} | {c4_n:,.0f} | {sign}{delta:,.0f} {win} |")

    lines += [
        "",
        "### 3.2 Nota sobre C1 = C3",
        "",
        "Con el perfil diario promedio de datos MTE, C1 (CREG 174) y C3 (Mercado spot)",
        "producen resultados idénticos. Esto es **correcto matemáticamente**: cuando la",
        "cobertura PV es 11% y G < D en el 100% de las horas, ningún nodo tiene excedente",
        "para vender a bolsa, por lo que el mecanismo de liquidación es irrelevante.",
        "La diferencia entre C1 y C3 aparecerá con precios de bolsa XM horarios reales",
        "y en días con baja demanda institucional (fines de semana, festivos).",
        "",
        "## 4. Métricas del mercado P2P",
        "",
        "| Métrica | Valor | Interpretación |",
        "|---------|-------|----------------|",
    ]

    sc_p2p = cr.self_consumption.get("P2P", 0)
    ss_p2p = cr.self_sufficiency.get("P2P", 0)
    ie_p2p = cr.equity_index.get("P2P", 0)
    ie_c4  = cr.equity_index.get("C4", 0)
    lines += [
        f"| SC (P2P) | {sc_p2p:.3f} | Fracción demanda cubierta internamente |",
        f"| SS (P2P) | {ss_p2p:.3f} | Fracción generación usada en comunidad |",
        f"| IE (P2P) | {ie_p2p:.4f} | Distribución beneficio (0=equitativo) |",
        f"| IE (C4)  | {ie_c4:.4f} | Referencia regulatoria vigente |",
        f"| PoF      | {pof:.4f} | Pérdida eficiencia por equidad P2P vs C4 |",
        "",
    ]

    # Sensibilidad si disponible
    if sa_pgb:
        lines += [
            "## 5. Análisis de sensibilidad",
            "",
            "### SA-1: Variación precio de bolsa PGB",
            "",
            f"| PGB (COP/kWh) | P2P ({currency}) | C4 ({currency}) | IE P2P | PoF |",
            "|---------------|---------|---------|--------|-----|",
        ]
        for r in sa_pgb:
            lines.append(
                f"| {r.param_value:.0f} | {r.net_benefit['P2P']:,.0f} | "
                f"{r.net_benefit['C4']:,.0f} | {r.ie_p2p:.3f} | {r.pof:.3f} |")

    if sa_pv:
        lines += [
            "",
            "### SA-2: Variación cobertura PV",
            "",
            f"| Factor PV | Cobertura (%) | P2P ({currency}) | C4 ({currency}) | Horas mercado | kWh P2P |",
            "|-----------|--------------|---------|---------|--------------|---------|",
        ]
        for r in sa_pv:
            cov = r.param_value * 0.113 * 100
            lines.append(
                f"| {r.param_value:.2f}x | {cov:.0f}% | "
                f"{r.net_benefit['P2P']:,.0f} | {r.net_benefit['C4']:,.0f} | "
                f"{r.market_hours} | {r.kwh_p2p:.1f} |")

    # Factibilidad si disponible
    if fa_des and fa_creg:
        lines += [
            "",
            "## 6. Análisis de factibilidad",
            "",
            "### FA-1: Condición de deserción del P2P",
            "",
            f"- Precio P2P nunca menor que bolsa: **{'Sí' if fa_des.condition_never_met else 'No'}**",
            f"- Umbral crítico precio bolsa: **{fa_des.critical_pgb_threshold:.0f} COP/kWh**",
            "",
            "### FA-2: Cumplimiento CREG 101 072/2025",
            "",
            f"| Institución | Participación (%) | Cumple 10% | Cap. max (kW) | Cumple 100kW |",
            "|-------------|------------------|-----------|--------------|-------------|",
        ]
        for name in agent_names:
            sh  = fa_creg.max_supply_share_by_agent.get(name, 0)
            cap = fa_creg.max_capacity_by_agent.get(name, 0)
            c10 = "✓" if name not in fa_creg.rule_10pct_violations else "✗"
            c100= "✓" if name not in fa_creg.rule_100kw_violations  else "✗"
            lines.append(f"| {name} | {sh:.2f}% | {c10} | {cap:.1f} | {c100} |")
        lines += [
            "",
            f"**Score de robustez C4:** {fa_creg.robustness_score:.2f} (1=máxima robustez)",
        ]

    lines += [
        "",
        "---",
        "",
        "## 7. Pendiente",
        "",
        "- [ ] Correr horizonte completo 5160h: `python main_simulation.py --data real --full --analysis`",
        "- [ ] Descargar serie horaria XM Jul 2025-Ene 2026 → `data/xm_precios_bolsa.csv`",
        "- [ ] Verificar LCOE real de inversores instalados en cada institución",
        "- [ ] Análisis sub-período: laborables vs fines de semana, julio vs enero",
        "",
        "---",
        f"*Generado automáticamente por main_simulation.py · {now}*",
    ]

    path = os.path.join(base_dir, "REPORTE_AVANCES.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"    Reporte asesores → {path}")
    return path


# ── Punto de entrada ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Simulación P2P — Tesis Brayan López, Udenar 2026")
    ap.add_argument("--data", choices=["synthetic", "real"], default="synthetic")
    ap.add_argument("--full", action="store_true",
                    help="Horizonte completo 5160h")
    ap.add_argument("--analysis", action="store_true",
                    help="Análisis de sensibilidad y factibilidad")
    args = ap.parse_args()
    main(use_real_data=(args.data == "real"),
         full_horizon=args.full,
         run_analysis=args.analysis)
