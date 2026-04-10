"""
main_simulation.py  — Tesis Brayan López, Udenar 2026
Sin programa DR. D es insumo fijo.

Modos de ejecución:
  python main_simulation.py                        # datos sintéticos (24h)
  python main_simulation.py --data real            # datos MTE, perfil promedio (24h)
  python main_simulation.py --data real --full     # datos MTE, 5160h completas
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
    GRID_PARAMS, PGS, PGB,
)


def main(use_real_data=False, full_horizon=False):
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

        if full_horizon:
            # Modo completo: 5160 horas — tarda ~20 min
            D, G = D_full, G_full
            T    = D.shape[1]
            pi_bolsa = np.full(T, PGB)
            print(f"\n    Modo: COMPLETO  N={N}  T={T}h ({T//24} días)")
        else:
            # Modo rápido (por defecto): perfil diario promedio 24h
            # Representa el comportamiento típico de la comunidad
            D, G = daily_profiles(D_full, G_full, index_full)
            T    = 24
            pi_bolsa = np.full(T, PGB)
            print(f"\n    Modo: PERFIL DIARIO PROMEDIO  N={N}  T=24h")
            print(f"    (basado en {D_full.shape[1]} horas reales)")
            print(f"    Para horizonte completo: --data real --full")

        prosumer_ids = list(range(N))
        consumer_ids = []

    else:
        print("\n[1/5] Datos sintéticos de validación...")
        G, D  = get_generation_profiles(), get_demand_profiles()
        p     = get_agent_params()
        pde   = get_pde_weights()
        pi_bolsa = np.full(24, PGB)
        N, T  = D.shape
        prosumer_ids = [0, 1, 2, 3]
        consumer_ids = [4, 5]
        cap   = np.array([3., 4., 3., 2., 0., 0.])
        print(f"    N={N}  T={T}h  |  demanda D fija, sin DR")

    # ── 2. EMS P2P ───────────────────────────────────────────────────────
    print("\n[2/5] EMS P2P (RD + Stackelberg)...")
    print(f"    Horas a procesar: {T}  —  estimado: ~{T*1.1:.0f}s")
    t0   = time.time()
    grid = GridParams(**GRID_PARAMS)

    if use_real_data:
        agents = AgentParams(
            N=N, a=np.zeros(N), b=np.full(N, 194.76), c=np.full(N, 1.2),
            lam=np.full(N, 100.0), theta=np.full(N, 0.5), etha=np.full(N, 0.1),
        )
    else:
        agents = AgentParams(**p)

    solver = SolverParams(tau=0.001, t_span=(0.0, 0.005),
                          n_points=150, stackelberg_iters=2, parallel=True)
    ems    = EMSP2P(agents, grid, solver)
    p2p_results, G_klim = ems.run(D, G)
    t_p2p  = time.time() - t0

    active = [r for r in p2p_results
              if r.P_star is not None and np.sum(r.P_star) > 1e-4]
    kwh    = sum(float(np.sum(r.P_star)) for r in active)
    print(f"    {t_p2p:.1f}s | horas mercado: {len(active)}/{T} | {kwh:.2f} kWh P2P")

    # ── 3. Escenarios C1–C4 ──────────────────────────────────────────────
    print("\n[3/5] Escenarios C1–C4...")
    cr = run_comparison(
        D=D, G_klim=G_klim, G_raw=G,
        p2p_results=p2p_results,
        pi_gs=PGS, pi_gb=PGB, pi_bolsa=pi_bolsa,
        prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
        pde=pde, pi_ppa=PGB + 0.5*(PGS - PGB), capacity=cap,
    )

    # ── 4. Reporte ───────────────────────────────────────────────────────
    print("\n[4/5] Reporte:")
    print_comparison_report(cr)

    print("\n  Ganancia neta por agente ($):")
    esc = ["P2P", "C1", "C2", "C3", "C4"]
    print(f"  {'Agente':<12}" + "".join(f"{'  '+e:>14}" for e in esc))
    print("  " + "─"*76)
    for n in range(N):
        role = "pros" if n in prosumer_ids else "cons"
        print(f"  A{n+1} ({role})" + "".join(
            f"{cr.net_benefit_per_agent[e][n]:>14,.0f}" for e in esc))

    # ── 5. Exportar ──────────────────────────────────────────────────────
    print("\n[5/5] Exportando resultados...")
    path = _export(cr, p2p_results, G_klim, D)
    print(f"    → {path}")
    print("\n✓ Completado.")
    return cr, p2p_results


def _export(cr, p2p_results, G_klim, D):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "resultados_comparacion.xlsx")
    esc  = ["P2P", "C1", "C2", "C3", "C4"]
    N, T = G_klim.shape

    with pd.ExcelWriter(path, engine="openpyxl") as w:
        pd.DataFrame({
            "Escenario":       esc,
            "Ganancia_neta_$": [cr.net_benefit[e] for e in esc],
            "SC":  [cr.self_consumption.get(e, 0) for e in esc],
            "SS":  [cr.self_sufficiency.get(e, 0) for e in esc],
            "IE":  [cr.equity_index.get(e, 0) for e in esc],
        }).to_excel(w, sheet_name="Resumen", index=False)

        pd.DataFrame([{"Agente": f"A{n+1}",
                       **{e: cr.net_benefit_per_agent[e][n] for e in esc}}
                      for n in range(cr.n_agents)]
                     ).to_excel(w, sheet_name="Por_agente", index=False)

        pd.DataFrame([{
            "Hora":    r.k + 1,
            "kWh_P2P": float(np.sum(r.P_star)) if r.P_star is not None else 0,
            "SC": r.SC, "SS": r.SS, "IE": r.IE,
            "PS_%": r.PS, "PSR_%": r.PSR,
            "Wj": r.Wj_total, "Wi": r.Wi_total,
            "Vendedores":  str([s+1 for s in r.seller_ids]),
            "Compradores": str([b+1 for b in r.buyer_ids]),
        } for r in p2p_results]).to_excel(w, sheet_name="P2P_horario", index=False)

        pd.DataFrame([{"Hora": k+1,
                       **{f"Gklim_A{n+1}": G_klim[n, k] for n in range(N)},
                       **{f"D_A{n+1}": D[n, k] for n in range(N)}}
                      for k in range(T)]).to_excel(w, sheet_name="Glim_y_D", index=False)

        pd.DataFrame([{
            "PoF_P2P_vs_C4": cr.price_of_fairness,
            "Spread_C4_kWh": float(np.sum(cr.static_spread_24h))
                              if cr.static_spread_24h is not None else 0,
            "pi_ppa": cr.pi_ppa,
        }]).to_excel(w, sheet_name="Metricas_extra", index=False)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", choices=["synthetic", "real"], default="synthetic")
    ap.add_argument("--full", action="store_true",
                    help="Usar horizonte completo 5160h (tarda ~20 min)")
    args = ap.parse_args()
    main(use_real_data=(args.data == "real"),
         full_horizon=args.full)