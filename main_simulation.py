"""
main_simulation.py  — Tesis Brayan López, Udenar 2026

Implementa el EMS completo de Chacón et al. (2025):
  Algoritmo 1: G_klim + DR program (D* = D cuando alpha=0 para datos reales)
  Algoritmos 2-3: RD + Stackelberg (vendedores y compradores)

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

# Windows: forzar UTF-8 en stdout para soportar caracteres Unicode (█, etc.)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

from core.ems_p2p  import EMSP2P, AgentParams, GridParams, SolverParams
from scenarios     import (run_comparison, print_comparison_report,
                           print_flow_breakdown, print_welfare_decomposition)
from data.base_case_data import (
    get_generation_profiles, get_demand_profiles,
    get_agent_params, get_pde_weights,
    GRID_PARAMS, GRID_PARAMS_REAL, PGS, PGB, PGS_COP, PGB_COP,
)
from data.xm_prices import get_pi_bolsa, get_b_for_real_data


def main(use_real_data=False, full_horizon=False, run_analysis=False,
         single_day: str = None):
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

        if single_day:
            from data.xm_data_loader import slice_horizon
            day_start = single_day
            day_end   = (pd.Timestamp(single_day) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            D, G, idx_day = slice_horizon(D_full, G_full, index_full,
                                          day_start, day_end)
            T = D.shape[1]
            month_labels = None   # período único para C1
            dow = pd.Timestamp(single_day).day_name()
            print(f"\n    Modo: DÍA ESPECÍFICO  {single_day} ({dow})  N={N}  T={T}h")
        elif full_horizon:
            D, G = D_full, G_full
            T    = D.shape[1]
            # Etiquetas de período de facturación (YYYYMM) para C1 (CREG 174)
            month_labels = np.array([ts.year * 100 + ts.month
                                     for ts in index_full], dtype=int)
            print(f"\n    Modo: COMPLETO  N={N}  T={T}h ({T//24} días)")
            n_periods = len(set(month_labels))
            print(f"    Períodos de facturación C1: {n_periods} meses")
        else:
            D, G = daily_profiles(D_full, G_full, index_full)
            T    = 24
            month_labels = None   # perfil promedio → un único período
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
        month_labels = None   # período único (24h sintéticas)
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
    p2p_results, G_klim, D_star = ems.run(D, G)

    # Reportar impacto del DR (solo si hay flexibilidad activa)
    dr_active = np.any(agents.alpha > 1e-9)
    if dr_active:
        from core.dr_program import dr_impact_report
        dr_rep = dr_impact_report(D, D_star, G_klim, agent_names)
        print(f"    DR activo: {dr_rep['shift_total_kwh']:.3f} kWh desplazados "
              f"({dr_rep['shift_pct']:.2f}% demanda)  "
              f"SC: {dr_rep['sc_before']:.3f}→{dr_rep['sc_after']:.3f}  "
              f"SS: {dr_rep['ss_before']:.3f}→{dr_rep['ss_after']:.3f}")
        # Usar D_star para los escenarios comparativos
        D = D_star
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
        month_labels=month_labels,
    )

    # ── 4. Reporte ───────────────────────────────────────────────────────
    print("\n[4/5] Reporte:")
    print_comparison_report(cr)

    print_flow_breakdown(cr, currency=currency)

    # Nota: en la propuesta de tesis, el escenario "Individual" = C1 (CREG 174),
    # y los escenarios "C1"→"C3" de la propuesta corresponden a C2→C4 del código.
    # Los encabezados ya reflejan esto: "C1 Individual", "C4 Colectivo", etc.
    esc = ["P2P", "C1", "C2", "C3", "C4"]
    esc_labels = {
        "P2P": "P2P", "C1": "C1-Indiv", "C2": "C2-Bilat",
        "C3": "C3-Spot", "C4": "C4-Colect",
    }
    print(f"\n  Ganancia neta por agente ({currency}/período):")
    print(f"  {'Institución':<12}" + "".join(f"{esc_labels[e]:>14}" for e in esc))
    print("  " + "─"*82)
    for n in range(N):
        name = agent_names[n] if n < len(agent_names) else f"A{n+1}"
        print(f"  {name:<12}" +
              "".join(f"{cr.net_benefit_per_agent[e][n]:>14,.0f}" for e in esc))

    print(f"\n  Gini por escenario (0=equitativo, 1=concentrado):")
    print(f"  " + "  ".join(f"{esc_labels[e]}: {cr.gini.get(e, 0):.4f}" for e in esc))

    print(f"\n  Ventaja P2P vs C4 (Colectivo CREG 101 072):")
    for n in range(N):
        name  = agent_names[n] if n < len(agent_names) else f"A{n+1}"
        delta = (cr.net_benefit_per_agent["P2P"][n]
                 - cr.net_benefit_per_agent["C4"][n])
        print(f"    {name:<12}: {'+'if delta>=0 else ''}{delta:>12,.0f} {currency}  "
              f"({'P2P mejor' if delta > 0 else 'C4 mejor'})")

    # ── 4b. Reporte mensual (solo modo --full con datos reales) ─────────────
    monthly_data = []
    if use_real_data and full_horizon and month_labels is not None:
        print("\n  Reporte mensual (horizonte completo)...")
        from analysis.monthly_report import compute_monthly_metrics, print_monthly_table
        monthly_data = compute_monthly_metrics(
            D=D, G_klim=G_klim, G_raw=G,
            p2p_results=p2p_results,
            pi_gs=grid_params["pi_gs"],
            pi_gb=grid_params["pi_gb"],
            pi_bolsa=pi_bolsa,
            prosumer_ids=prosumer_ids,
            consumer_ids=consumer_ids,
            month_labels=month_labels,
            pde=pde,
            capacity=cap,
        )
        print_monthly_table(monthly_data, currency=currency)

    # ── 5. Exportar base ─────────────────────────────────────────────────
    print("\n[5/5] Exportando resultados y gráficas...")
    base_dir  = os.path.dirname(os.path.abspath(__file__))

    # Series diarias (solo modo --full con datos reales, T ≥ 48h)
    daily_series = None
    if use_real_data and full_horizon and D.shape[1] >= 48:
        import datetime as _dt
        print("    Calculando series diarias para bootstrap estadístico...")
        daily_series = _compute_daily_series(
            D=D, G_klim=G_klim, p2p_results=p2p_results,
            pi_gs=grid_params["pi_gs"], pi_gb=grid_params["pi_gb"],
            pi_bolsa=pi_bolsa, pde=pde, cap=cap,
            prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
        )
        os.makedirs(os.path.join(base_dir, "outputs"), exist_ok=True)
        ts_str = _dt.datetime.now().strftime("%Y%m%d_%H%M")
        csv_path = os.path.join(base_dir, "outputs", f"daily_series_{ts_str}.csv")
        daily_series.to_csv(csv_path)
        print(f"    Series diarias ({len(daily_series)} días) → {csv_path}")

    excel_path = _export_base(cr, p2p_results, G_klim, D, base_dir, currency,
                               daily_series=daily_series)
    print(f"    Excel → {excel_path}")

    from analysis.p2p_breakdown import export_p2p_hourly, print_p2p_sample
    flows_rows, summary_rows = export_p2p_hourly(
        p2p_results=p2p_results,
        agent_names=agent_names,
        pi_gs=grid_params["pi_gs"],
        pi_gb=grid_params["pi_gb"],
        out_dir=base_dir,
        prefix="p2p_breakdown",
        verbose=True,
    )
    print_p2p_sample(flows_rows, summary_rows, n_hours=2)

    from visualization.plots import (generate_all_plots, plot_monthly_comparison,
                                     plot_flow_breakdown, plot_c1_vs_c4)
    plots_dir = os.path.join(base_dir, "graficas")
    generate_all_plots(D=D, G=G, G_klim=G_klim, p2p_results=p2p_results,
                       cr=cr, agent_names=agent_names,
                       out_dir=plots_dir, currency=currency)

    p = plot_flow_breakdown(cr, out_dir=plots_dir, currency=currency)
    if p:
        print(f"    ✓ Fig 13 — Desglose de flujos por componente")

    if monthly_data:
        p = plot_monthly_comparison(monthly_data, out_dir=plots_dir, currency=currency)
        if p:
            print(f"    ✓ Fig 12 — Comparación mensual")

    p = plot_c1_vs_c4(
        cr=cr, agent_names=agent_names,
        D=D, G_klim=G_klim, pi_bolsa=pi_bolsa,
        pde=pde, pi_gs=grid_params["pi_gs"],
        out_dir=plots_dir, currency=currency,
    )
    if p:
        print(f"    ✓ Fig 15 — Comparación directa C1 vs C4")

    # ── 6. Análisis de sensibilidad y factibilidad (--analysis) ──────────
    sa_pgb, sa_pv, sa_ppa = [], [], []
    fa_des, fa_creg_rep, fa_ir = None, None, None

    if run_analysis:
        print("\n" + "="*65)
        print("  ANÁLISIS DE SENSIBILIDAD Y FACTIBILIDAD")
        print("="*65)

        from analysis.sensitivity import (
            run_sensitivity_pgb, run_sensitivity_pv,
            run_sensitivity_ppa, run_sensitivity_pgs,
            find_dominance_threshold)
        from analysis.feasibility import (
            analyze_desertion, analyze_desertion_individual_rationality,
            analyze_creg_101072_compliance)
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

        # SA-3: variación precio al usuario π_gs (Actividad 4.1 propuesta)
        print(f"\n  SA-3: Ejecutando barrido de precio al usuario (π_gs)...")
        sa_pgs = run_sensitivity_pgs(
            D=D, G=G, agents=agents, grid_base=grid, solver=solver,
            pde=pde, prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
            verbose=True,
        )

        # Umbrales de dominancia
        thresholds = find_dominance_threshold(sa_pgb, sa_pv)
        print(f"\n  Umbrales de dominancia P2P:")
        print(f"    P2P siempre > C4: {thresholds.get('p2p_always_beats_c4')}")
        t_c4 = thresholds.get("pgb_threshold_vs_C4")
        t_c1 = thresholds.get("pgb_threshold_vs_C1")
        if isinstance(t_c4, float):
            print(f"    PGB umbral P2P = C4: {t_c4:.0f} COP/kWh")
        else:
            print(f"    PGB umbral P2P = C4: {t_c4}")
        if isinstance(t_c1, float):
            print(f"    PGB umbral P2P = C1: {t_c1:.0f} COP/kWh  ← deserción posible aquí")
        else:
            print(f"    PGB umbral P2P = C1: {t_c1}")
        if thresholds.get("pv_threshold_vs_C4"):
            print(f"    Factor PV umbral vs C4: {thresholds['pv_threshold_vs_C4']:.2f}x")

        # FA-1: deserción horaria (precio P2P vs precio bolsa)
        fa_des = analyze_desertion(
            p2p_results=p2p_results, pi_bolsa=pi_bolsa,
            agent_names=agent_names, prosumer_ids=prosumer_ids, verbose=True,
        )

        # FA-1b: Condición de Racionalidad Individual por agente (§3.14)
        # Pasamos los beneficios reales del caso nominal (XM variable) para
        # que la evaluación base use precios correctos, no el SA-1 constante.
        pi_gb_nom = grid_params["pi_gb"]
        fa_ir = analyze_desertion_individual_rationality(
            sa_pgb_results=sa_pgb,
            agent_names=agent_names,
            pi_gb_nominal=pi_gb_nom,
            base_net_p2p=cr.net_benefit_per_agent.get("P2P"),
            base_net_c1=cr.net_benefit_per_agent.get("C1"),
            base_net_c4=cr.net_benefit_per_agent.get("C4"),
            verbose=True,
        )

        # §3.6: Análisis de fuente y calibración de precios
        from data.xm_prices import price_source_analysis
        price_source_analysis(
            pi_bolsa=pi_bolsa,
            pi_gs=grid_params["pi_gs"],
            verbose=True,
        )

        # SA-3: sensibilidad precio bilateral PPA (§3.8)
        print(f"\n  SA-3: Sensibilidad al precio PPA (pi_ppa)...")
        sa_ppa = run_sensitivity_ppa(
            D=D, G_klim=G_klim, G_raw=G,
            pi_gs=grid_params["pi_gs"], pi_gb=grid_params["pi_gb"],
            pi_bolsa=pi_bolsa,
            p2p_results=p2p_results,
            prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
            pde=pde,
            capacity=cap if 'cap' in dir() else None,
            verbose=True,
        )

        # §3.12: Desglose P2P hora a hora (exportado en bloque 5, muestra ampliada)
        print(f"\n  §3.12 Desglose P2P hora a hora (muestra ampliada):")
        print_p2p_sample(flows_rows, summary_rows, n_hours=5)

        # FA-2: cumplimiento CREG 101 072
        fa_creg_rep = analyze_creg_101072_compliance(
            D=D, G=G, agent_names=agent_names,
            prosumer_ids=prosumer_ids, verbose=True,
        )

        # FA-3: Robustez — retiro de participante
        # FA-4: Robustez — escalamiento de instalación
        from analysis.feasibility import (analyze_withdrawal_risk,
                                          analyze_scaling_risk)
        print(f"\n  FA-3/FA-4: Robustez regulatoria C4...")
        cap_arr = np.array([float(G[n].max()) for n in range(D.shape[0])])
        wr_report = analyze_withdrawal_risk(
            D=D, G=G, G_klim=G_klim,
            pi_gs=grid_params["pi_gs"],
            pi_gb=grid_params["pi_gb"],
            pi_bolsa=pi_bolsa,
            pde=pde,
            prosumer_ids=prosumer_ids,
            agent_names=agent_names,
            net_benefit_p2p=cr.net_benefit_per_agent["P2P"],
            net_benefit_c4_full=cr.net_benefit_per_agent["C4"],
            capacity=cap_arr,
            verbose=True,
        )
        sc_risk = analyze_scaling_risk(
            G=G, prosumer_ids=prosumer_ids, agent_names=agent_names,
            D=D, verbose=True,
        )

        # ── Convergencia RD + Stackelberg (Objetivo 2 / Validación) ──────
        print(f"\n  Convergencia RD+Stackelberg (horas representativas)...")
        from visualization.plots import plot_convergence
        conv_data = ems.run_convergence(
            D=D, G=G, G_klim=G_klim,
            p2p_results=p2p_results,
            n_iters_conv=8,
            max_hours=2,
        )
        if conv_data:
            conv_paths = plot_convergence(
                conv_list=conv_data,
                agent_names=agent_names,
                out_dir=plots_dir,
                currency=currency,
            )
            for p in conv_paths:
                print(f"    ✓ {os.path.basename(p)}")
        else:
            print("    (sin horas activas para análisis de convergencia)")

        # Activity 4.2: Análisis cualitativo de optimalidad P2P vs C4
        print(f"\n  Activity 4.2: Análisis de optimalidad P2P vs C4 hora a hora...")
        from analysis.optimality import analyze_hourly_dominance, print_optimality_report
        from visualization.plots import plot_optimality
        opt_summary = analyze_hourly_dominance(
            D=D, G_klim=G_klim,
            p2p_results=p2p_results,
            pde=pde,
            pi_gs=grid_params["pi_gs"],
            pi_gb=grid_params["pi_gb"],
            pi_bolsa=pi_bolsa,
            prosumer_ids=prosumer_ids,
            consumer_ids=consumer_ids,
        )
        print_optimality_report(opt_summary, agent_names=agent_names, currency=currency)
        p = plot_optimality(opt_summary, out_dir=plots_dir, currency=currency)
        if p:
            print(f"    ✓ Fig 14 — Análisis de optimalidad P2P vs C4")

        # Actividad 4.3: Análisis de sub-períodos (laborable/finde × jul/ene)
        print(f"\n  Actividad 4.3: Análisis de sub-períodos...")
        from analysis.subperiod import (run_subperiod_analysis,
                                        print_subperiod_table, plot_subperiod)
        sp_results = run_subperiod_analysis(
            D=D, G=G,
            agents=agents, grid=grid, solver=solver,
            pde=pde, prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
            pi_gs=grid_params["pi_gs"], capacity=cap,
            agent_names=agent_names, currency=currency, verbose=True,
        )
        print_subperiod_table(sp_results, currency=currency)
        p = plot_subperiod(sp_results, out_dir=plots_dir, currency=currency)
        if p:
            print(f"    ✓ Fig 16 — Análisis de sub-períodos")

        # Fig 17 — Robustez C4
        from visualization.plots import plot_robustness_c4
        p17 = plot_robustness_c4(wr_report, agent_names,
                                  out_dir=plots_dir, currency=currency)
        if p17:
            print(f"    ✓ Fig 17 — Robustez regulatoria C4")

        # Gráficas 7-9
        generate_sensitivity_plots(
            sa_pgb=sa_pgb, sa_pv=sa_pv,
            findings=thresholds,
            fa_desertion=fa_des, fa_creg=fa_creg_rep,
            p2p_results=p2p_results, pi_bolsa=pi_bolsa,
            D=D, agent_names=agent_names,
            out_dir=plots_dir, currency=currency,
            sa_ppa=sa_ppa,
            pi_gb=grid_params["pi_gb"],
            pi_gs=grid_params["pi_gs"],
            sa_pgs=sa_pgs,
        )

        # Exportar análisis a Excel
        _export_analysis(sa_pgb, sa_pv, fa_des, fa_creg_rep,
                          thresholds, base_dir, agent_names, fa_ir=fa_ir,
                          wr_report=wr_report, sc_risk=sc_risk)

    # ── Reporte de avances para asesores ─────────────────────────────────
    _generate_progress_report(
        cr=cr, p2p_results=p2p_results, G_klim=G_klim, D=D, G=G,
        agent_names=agent_names, currency=currency,
        use_real_data=use_real_data, full_horizon=full_horizon,
        sa_pgb=sa_pgb, sa_pv=sa_pv,
        fa_des=fa_des, fa_creg=fa_creg_rep, fa_ir=fa_ir,
        base_dir=base_dir,
    )

    t_total = time.time() - t_total_start
    print(f"\n✓ Completado en {t_total:.1f}s.")
    return cr, p2p_results


# ── Exportar Excel base ───────────────────────────────────────────────────────

def _export_base(cr, p2p_results, G_klim, D, base_dir, currency, daily_series=None):
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
            "RPE_P2P_vs_C4":         cr.rpe,
            "Spread_C4_kWh":         float(np.sum(cr.static_spread_24h))
                                      if cr.static_spread_24h is not None else 0,
            # Act 3.3 — Bienestar de optimización (u.o.)
            "W_sellers_total_uo":    cr.W_sellers_total,
            "W_buyers_total_uo":     cr.W_buyers_total,
            "W_total_uo":            cr.W_sellers_total + cr.W_buyers_total,
            "Nota_W":                "u.o.=unidades optimizacion; no son COP",
        }]).to_excel(w, sheet_name="Metricas_extra", index=False)
        if daily_series is not None and not daily_series.empty:
            daily_series.to_excel(w, sheet_name="Series_diarias", index=True)
    return path


# ── Series diarias para bootstrap estadístico ─────────────────────────────────

def _compute_daily_series(
    D, G_klim, p2p_results,
    pi_gs, pi_gb, pi_bolsa, pde, cap, prosumer_ids, consumer_ids,
):
    """
    Agrega beneficio neto comunitario por día para P2P y C4.
    Llama solo a las funciones de liquidación (NO re-corre el EMS).

    Retorna DataFrame(n_days, 2) con columnas ['nb_p2p', 'nb_c4'] en COP/día.
    Actividad 4.2 — soporte para bootstrap por bloques.
    """
    from scenarios.comparison_engine import _p2p_monetary_benefit
    from scenarios.scenario_c4_creg101072 import run_c4_creg101072

    T      = D.shape[1]
    N      = D.shape[0]
    n_days = T // 24

    rows = []
    for d in range(n_days):
        sl = slice(d * 24, (d + 1) * 24)
        D_d = D[:, sl]
        G_d = G_klim[:, sl]

        nb_p2p = _p2p_monetary_benefit(
            p2p_results[d * 24 : (d + 1) * 24],
            D_d, G_d, pi_gs, pi_gb, prosumer_ids,
        ).sum()

        c4 = run_c4_creg101072(
            D_d, G_d, pi_gs, pi_bolsa[sl], pde, cap, mode="pde_only"
        )
        nb_c4 = sum(c4["per_agent"][n]["net_benefit"] for n in range(N))

        rows.append({"dia": d, "nb_p2p": float(nb_p2p), "nb_c4": float(nb_c4)})

    return pd.DataFrame(rows).set_index("dia")


# ── Exportar análisis de sensibilidad a Excel ─────────────────────────────────

def _export_analysis(sa_pgb, sa_pv, fa_des, fa_creg, thresholds, base_dir, agent_names,
                     fa_ir=None, wr_report=None, sc_risk=None):
    path = os.path.join(base_dir, "resultados_analisis.xlsx")
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        if sa_pgb:
            rows = []
            for r in sa_pgb:
                row = {"PGB_COP_kWh": r.param_value,
                       "IE_P2P": r.ie_p2p, "RPE": r.rpe,
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

        # §3.14 — Racionalidad Individual
        if fa_ir:
            rows_ir = []
            for name in agent_names:
                rows_ir.append({
                    "Agente":         name,
                    "B_P2P_COP":      fa_ir.benefit_p2p.get(name, 0),
                    "B_C4_COP":       fa_ir.benefit_c4.get(name, 0),
                    "Delta_n_COP":    fa_ir.surplus_vs_c4.get(name, 0),
                    "Delta_n_rel":    fa_ir.surplus_rel.get(name, 0),
                    "pi_gb_critico":  fa_ir.critical_pgb.get(name, 0),
                    "Estado":         ("estable" if name in fa_ir.stable_agents
                                       else "en_riesgo"),
                })
            pd.DataFrame(rows_ir).to_excel(
                w, sheet_name="FA_DesercionIR", index=False)

            # Tabla de sensibilidad Δ_n(pi_gb)
            rows_sens = []
            for pgb_v, row_d in sorted(fa_ir.pgb_vs_surplus.items()):
                row = {"pi_gb": pgb_v}
                for name in agent_names:
                    row[f"delta_{name}"] = row_d.get(name, 0)
                row["delta_total"] = sum(row_d.values())
                rows_sens.append(row)
            pd.DataFrame(rows_sens).to_excel(
                w, sheet_name="DesercionIR_Sensibilidad", index=False)

        # FA-3: Robustez — retiro de participante
        if wr_report is not None and wr_report.by_agent:
            rows_wr = []
            for name, d in wr_report.by_agent.items():
                rows_wr.append({
                    "Agente_retirado":      name,
                    "AGRC_restante_cumple": d["compliant"],
                    "B_C4_full_COP":        d["B_C4_full"],
                    "B_C4_remaining_COP":   d["B_C4_remaining"],
                    "B_fallback_COP":       d["B_fallback"],
                    "B_P2P_remaining_COP":  d["B_P2P_remaining"],
                    "loss_C4_COP":          d["loss_C4"],
                    "flexibility_premium_COP": d["flexibility_premium"],
                    "reglas_violadas":      ",".join(d["violated_rules"]) or "—",
                })
            pd.DataFrame(rows_wr).to_excel(
                w, sheet_name="FA3_Robustez_Retiro", index=False)

        # FA-4: Robustez — escalamiento
        if sc_risk is not None:
            rows_sc = []
            for name, d in sc_risk.items():
                rows_sc.append({
                    "Agente":         name,
                    "G_mean_kW":      d["g_mean_kw"],
                    "G_max_kW":       d["g_max_kw"],
                    "Share_actual_%": d["share_pct"],
                    "2x_cumple":      d["2x_ok"],
                    "3x_cumple":      d["3x_ok"],
                    "Escala_max_ok":  d["max_ok_scale"],
                })
            pd.DataFrame(rows_sc).to_excel(
                w, sheet_name="FA4_Robustez_Escala", index=False)

    print(f"    Excel análisis → {path}")
    return path


# ── Reporte de avances para asesores (Markdown) ───────────────────────────────

def _generate_progress_report(cr, p2p_results, G_klim, D, G,
                               agent_names, currency, use_real_data,
                               full_horizon, sa_pgb, sa_pv,
                               fa_des, fa_creg, base_dir, fa_ir=None):
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

    rpe = cr.rpe or 0
    spread = float(np.sum(cr.static_spread_24h)) if cr.static_spread_24h is not None else 0
    lines += [
        "",
        f"**RPE (P2P vs C4):** {rpe:.4f}",
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
        f"| RPE      | {rpe:.4f} | Rendimiento relativo P2P vs C4 (RPE ≠ PoF Bertsimas 2011) |",
        "",
    ]

    # Sensibilidad si disponible
    if sa_pgb:
        lines += [
            "## 5. Análisis de sensibilidad",
            "",
            "### SA-1: Variación precio de bolsa PGB",
            "",
            f"| PGB (COP/kWh) | P2P ({currency}) | C4 ({currency}) | IE P2P | RPE |",
            "|---------------|---------|---------|--------|-----|",
        ]
        for r in sa_pgb:
            lines.append(
                f"| {r.param_value:.0f} | {r.net_benefit['P2P']:,.0f} | "
                f"{r.net_benefit['C4']:,.0f} | {r.ie_p2p:.3f} | {r.rpe:.3f} |")

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

    # §3.14 — Racionalidad Individual
    if fa_ir:
        lines += [
            "",
            "### FA-1b: Deserción — Condición de Racionalidad Individual (§3.14)",
            "",
            "**Definición formal (Restricción IR):**",
            "Agente n permanece en P2P sii `B_n^P2P(π) ≥ max(B_n^C1, B_n^C4)(π)`",
            "",
            "Donde `Δ_n = B_n^P2P − max(B_n^C1, B_n^C4)` (>0 → agente prefiere P2P). ",
            "Umbral crítico `π_gb^*_n`: precio de bolsa donde el agente es indiferente.",
            "",
            f"| Agente | B_P2P ({currency}) | B_alt ({currency}) | Δ_n ({currency}) | Δ_n/B_alt | π_gb^*_n | Estado |",
            "|--------|---------|---------|---------|----------|---------|--------|",
        ]
        for name in agent_names:
            b_p2p = fa_ir.benefit_p2p.get(name, 0)
            b_c4  = fa_ir.benefit_c4.get(name, 0)
            delta = fa_ir.surplus_vs_c4.get(name, 0)
            rel   = fa_ir.surplus_rel.get(name, 0)
            thr   = fa_ir.critical_pgb.get(name, 0)
            estado = "estable" if name in fa_ir.stable_agents else "en riesgo"
            pgb_arr = sorted(fa_ir.pgb_vs_surplus.keys())
            thr_str = f">rango" if pgb_arr and thr > max(pgb_arr) * 1.05 else f"{thr:.0f}"
            sign = "+" if delta >= 0 else ""
            lines.append(
                f"| {name} | {b_p2p:,.0f} | {b_c4:,.0f} | "
                f"{sign}{delta:,.0f} | {rel:+.1%} | {thr_str} | {estado} |")

        comm_thr = fa_ir.community_critical_pgb
        agg_thr  = fa_ir.community_agg_critical_pgb
        pgb_arr  = sorted(fa_ir.pgb_vs_surplus.keys())
        comm_str = (f"{comm_thr:.0f}" if pgb_arr and comm_thr < max(pgb_arr) * 1.05
                    else f">rango (>{max(pgb_arr) if pgb_arr else '?'})")
        agg_str  = (f"{agg_thr:.0f}" if pgb_arr and agg_thr < max(pgb_arr) * 1.05
                    else f">rango (>{max(pgb_arr) if pgb_arr else '?'})")
        lines += [
            "",
            f"**Agentes estables ({len(fa_ir.stable_agents)}/{len(agent_names)}):** "
            f"{', '.join(fa_ir.stable_agents) or 'ninguno'}",
            f"**Umbral comunitario (mediana individual):** {comm_str} COP/kWh",
            f"**Umbral agregado P2P < max(C1,C4):** {agg_str} COP/kWh",
            "",
            "**Tabla Δ_n(pi_gb) — sensibilidad a precio de bolsa:**",
            "",
        ]
        # Header de la tabla sensibilidad
        hdr = "| pi_gb |" + "".join(f" {n} |" for n in agent_names) + " Σ Δ |"
        sep = "|-------|" + "".join("--------|" for _ in agent_names) + "--------|"
        lines += [hdr, sep]
        for pgb_v in sorted(fa_ir.pgb_vs_surplus.keys()):
            row_d = fa_ir.pgb_vs_surplus[pgb_v]
            total = sum(row_d.values())
            sign_t = "+" if total >= 0 else ""
            row = f"| {pgb_v:.0f} |"
            for name in agent_names:
                d = row_d.get(name, 0)
                sign_d = "+" if d >= 0 else ""
                row += f" {sign_d}{d:,.0f} |"
            row += f" {sign_t}{total:,.0f} |"
            lines.append(row)

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
    # CRÍTICO en Windows: freeze_support evita que ProcessPoolExecutor
    # re-ejecute este script en cada worker (produce banner duplicado).
    import multiprocessing
    multiprocessing.freeze_support()

    ap = argparse.ArgumentParser(
        description="Simulación P2P — Tesis Brayan López, Udenar 2026")
    ap.add_argument("--data", choices=["synthetic", "real"], default="synthetic")
    ap.add_argument("--full", action="store_true",
                    help="Horizonte completo 5160h")
    ap.add_argument("--analysis", action="store_true",
                    help="Análisis de sensibilidad y factibilidad")
    ap.add_argument("--day", type=str, default=None,
                    help="Día específico YYYY-MM-DD (implica --data real, 24h)")
    ap.add_argument("--gsa", action="store_true",
                    help="Ejecutar análisis de sensibilidad global Sobol/Saltelli")
    ap.add_argument("--n-base", type=int, default=64, metavar="N",
                    help="Tamaño base muestra Saltelli (default 64 → 1024 eval.)")
    args = ap.parse_args()

    if args.gsa:
        from analysis.global_sensitivity import (
            run_sobol_analysis, compute_indices, save_results)
        import multiprocessing
        multiprocessing.freeze_support()
        if args.n_base >= 256:
            ans = input(
                f"--n-base={args.n_base} genera "
                f"{args.n_base*(2*7+2)} evaluaciones (~5 h). "
                "Confirmar [s/N]: "
            )
            if ans.strip().lower() != "s":
                print("Cancelado.")
                sys.exit(0)
        Y_dict   = run_sobol_analysis(n_base=args.n_base, seed=42, parallel=True)
        idx_dict = compute_indices(Y_dict)
        out_path = save_results(idx_dict, Y_dict=Y_dict)
        print(f"\nGSA completado. Resultados en: {out_path}")
    elif args.day:
        main(use_real_data=True, full_horizon=False, run_analysis=args.analysis,
             single_day=args.day)
    else:
        main(use_real_data=(args.data == "real"),
             full_horizon=args.full,
             run_analysis=args.analysis)
