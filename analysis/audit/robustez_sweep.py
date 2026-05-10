"""
analysis/audit/robustez_sweep.py
---------------------------------
Eje 2 del audit: coordinate descent sobre alpha_n per-agente para
maximizar la cobertura de Racionalidad Individual (IR coverage).

IR coverage = porcentaje de agentes con Delta_n >= 0, donde
  Delta_n = B_n^P2P - max(B_n^C1, B_n^C4)

Trazabilidad: Act 4.2, anexo defensivo del paper.
"""

import argparse
import datetime
import io
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Forzar UTF-8 en stdout (Windows) para soportar barras de progreso Unicode
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")

from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams
from scenarios import run_comparison
from data.xm_prices import get_pi_bolsa, get_b_for_real_data
from data.cedenar_tariff import (
    effective_pi_gs_per_agent,
    g_plus_commercialization_per_agent_hourly,
    cu_components_per_agent_hourly,
    mem_costs_per_agent_hourly,
    community_effective_pi_gs,
    pi_gs_per_agent_hourly,
)
from data.base_case_data import GRID_PARAMS_REAL, PGB_COP

# Valores de alpha a explorar por agente (fraccion de demanda flexible)
# Limite reglamentario CREG: [0, 0.25]
ALPHA_VALUES = [0.0, 0.10, 0.20, 0.25]

AGENT_NAMES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
N = 5


def load_daily_data() -> dict:
    """Carga perfiles diarios promedio MTE y parametros de precios."""
    from data.xm_data_loader import MTEDataLoader, daily_profiles

    mte_root = os.environ.get(
        "MTE_ROOT",
        str(Path(__file__).resolve().parents[2] / "MedicionesMTE_v3"),
    )
    loader = MTEDataLoader(mte_root)
    D_full, G_full, index_full = loader.load(verbose=False)
    D, G = daily_profiles(D_full, G_full, index_full)
    T = 24

    from scenarios.scenario_c4_creg101072 import compute_pde_weights
    cap = np.maximum(G_full.mean(axis=1), 0)
    pde = compute_pde_weights(cap)

    t_start = index_full[0]
    t_end   = index_full[-1] + pd.Timedelta(hours=1)
    demand_weights = D_full.mean(axis=1)
    pi_gs_eff      = community_effective_pi_gs(AGENT_NAMES, t_start, t_end,
                                                weights=demand_weights)
    pi_gs_per_agent = effective_pi_gs_per_agent(AGENT_NAMES, t_start, t_end)

    xm_csv = Path(__file__).resolve().parents[2] / "data" / "xm_precios_bolsa.csv"
    pi_bolsa = get_pi_bolsa(T, csv_path=str(xm_csv) if xm_csv.exists() else None,
                             scenario="2025_normal")

    b_cal = get_b_for_real_data(N, AGENT_NAMES)

    # CAL-13/CAL-16: componentes tarifarios
    pi_G_full = g_plus_commercialization_per_agent_hourly(AGENT_NAMES, index_full)
    pi_G_arg  = pi_G_full.mean(axis=1)
    cu_comps_full = cu_components_per_agent_hourly(AGENT_NAMES, index_full)
    mem_full      = mem_costs_per_agent_hourly(AGENT_NAMES, index_full)
    cu_comps = {k: np.nanmean(v, axis=1) for k, v in cu_comps_full.items()}
    mem_arg  = np.nanmean(mem_full, axis=1)
    g_arg, cvm_arg, cot_arg = cu_comps["G"], cu_comps["Cvm"], cu_comps["COT"]
    pi_upper = float(np.nanmean(g_arg + cvm_arg + cot_arg - mem_arg))
    pi_ppa   = float(PGB_COP) + 0.5 * (pi_upper - float(PGB_COP))

    return dict(
        D=D, G=G, T=T, N=N, cap=cap, pde=pde, b_cal=b_cal,
        pi_gs_arg=pi_gs_per_agent,
        pi_gb=float(PGB_COP), pi_bolsa=pi_bolsa,
        pi_G_arg=pi_G_arg, g_arg=g_arg, cvm_arg=cvm_arg,
        cot_arg=cot_arg, mem_arg=mem_arg, pi_ppa=pi_ppa,
    )


def run_with_alpha(alpha_vec: np.ndarray, data: dict) -> Dict:
    """Ejecuta EMS + comparacion con el vector alpha dado.

    Retorna: delta_n (N,), ir_coverage_pct, welfare_p2p.
    """
    D, G = data["D"], data["G"]

    agents = AgentParams(
        N=N, a=np.zeros(N), b=data["b_cal"],
        c=np.zeros(N),  # CAL-32 (apendice 2026-05-06b): c=0 PV puro
        lam=np.full(N, 100.0), theta=np.full(N, 0.5), etha=np.full(N, 0.1),
        alpha=alpha_vec.copy(),
    )
    solver = SolverParams(tau=0.001, t_span=(0.0, 0.005),
                          n_points=150, stackelberg_iters=2, parallel=True)
    grid = GridParams(pi_gs=GRID_PARAMS_REAL["pi_gs"], pi_gb=data["pi_gb"])
    ems  = EMSP2P(agents, grid, solver)
    p2p_results, G_klim, D_star = ems.run(D, G)

    D_comp = D_star if np.any(alpha_vec > 1e-9) else D

    cr = run_comparison(
        D=D_comp, G_klim=G_klim, G_raw=G,
        p2p_results=p2p_results,
        pi_gs=data["pi_gs_arg"], pi_gb=data["pi_gb"],
        pi_bolsa=data["pi_bolsa"],
        prosumer_ids=list(range(N)), consumer_ids=[],
        pde=data["pde"], pi_ppa=data["pi_ppa"],
        capacity=data["cap"], month_labels=None, component_c="auto",
        pi_G=data["pi_G_arg"],
        g_component=data["g_arg"], cvm_component=data["cvm_arg"],
        cot_component=data["cot_arg"], mem_costs=data["mem_arg"],
    )

    nb_p2p = cr.net_benefit_per_agent.get("P2P", np.zeros(N))
    nb_c1  = cr.net_benefit_per_agent.get("C1", np.zeros(N))
    nb_c4  = cr.net_benefit_per_agent.get("C4", np.zeros(N))
    delta_n = nb_p2p - np.maximum(nb_c1, nb_c4)
    ir_coverage = float(np.mean(delta_n >= 0)) * 100.0

    return dict(
        delta_n=delta_n,
        ir_coverage_pct=ir_coverage,
        welfare_p2p=cr.net_benefit.get("P2P", 0.0),
        min_delta_n=float(np.min(delta_n)),
        alpha=alpha_vec.copy(),
    )


def coordinate_descent(
    initial_alpha: np.ndarray,
    data: dict,
    max_passes: int = 2,
) -> Tuple[List[dict], dict]:
    """Coordinate descent sobre alpha_n per-agente para maximizar IR coverage.

    En cada pasada prueba ALPHA_VALUES para cada agente y mantiene la que
    maximiza min(delta_n). Para si una pasada completa no mejora.
    """
    trajectory: List[dict] = []
    current_alpha = initial_alpha.copy()

    baseline = run_with_alpha(current_alpha, data)
    trajectory.append({"pass": 0, "agent": "baseline", "alpha_chosen": -1,
                        "min_delta_n": baseline["min_delta_n"],
                        "ir_coverage_pct": baseline["ir_coverage_pct"]})
    print(f"[B2] Baseline  IR={baseline['ir_coverage_pct']:.0f}%  "
          f"min_delta={baseline['min_delta_n']:+,.0f} COP")

    best_result = baseline

    for pass_idx in range(1, max_passes + 1):
        improved = False
        for n in range(N):
            best_alpha_n = current_alpha[n]
            best_min_delta = best_result["min_delta_n"]

            for a_val in ALPHA_VALUES:
                if abs(a_val - current_alpha[n]) < 1e-9:
                    continue
                trial_alpha = current_alpha.copy()
                trial_alpha[n] = a_val
                t0 = time.time()
                res = run_with_alpha(trial_alpha, data)
                elapsed = time.time() - t0
                print(f"  [P{pass_idx} A{n}={AGENT_NAMES[n]}] "
                      f"alpha={a_val:.2f}  "
                      f"IR={res['ir_coverage_pct']:.0f}%  "
                      f"min_d={res['min_delta_n']:+,.0f}  "
                      f"({elapsed:.1f}s)")
                if res["min_delta_n"] > best_min_delta:
                    best_min_delta = res["min_delta_n"]
                    best_alpha_n = a_val
                    best_result = res

            if abs(best_alpha_n - current_alpha[n]) > 1e-9:
                current_alpha[n] = best_alpha_n
                improved = True

            trajectory.append({
                "pass": pass_idx, "agent": AGENT_NAMES[n],
                "alpha_chosen": float(current_alpha[n]),
                "min_delta_n": best_result["min_delta_n"],
                "ir_coverage_pct": best_result["ir_coverage_pct"],
            })

        print(f"[B2] Pasada {pass_idx} completa  "
              f"IR={best_result['ir_coverage_pct']:.0f}%  "
              f"min_delta={best_result['min_delta_n']:+,.0f}  "
              f"alpha={current_alpha}")
        if not improved:
            print(f"[B2] Convergencia en pasada {pass_idx} (sin mejora).")
            break

    return trajectory, best_result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Coordinate descent sobre alpha_n para IR universal (Act 4.2)"
    )
    parser.add_argument("--max-passes", type=int, default=2)
    args = parser.parse_args()

    import multiprocessing
    multiprocessing.freeze_support()

    print("\n[B2] robustez_sweep.py — Eje 2 audit IR universal")
    print(f"     ALPHA_VALUES = {ALPHA_VALUES}")
    print(f"     max_passes   = {args.max_passes}")

    t_total = time.time()
    data = load_daily_data()
    print(f"[B2] Datos cargados: N={N}  T={data['T']}h")

    initial_alpha = np.array([0.20, 0.20, 0.20, 0.20, 0.10])

    fecha   = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    outdir  = Path(__file__).resolve().parents[2] / "outputs" / f"audit_{fecha}" / "robustez"
    outdir.mkdir(parents=True, exist_ok=True)

    trajectory, optimal = coordinate_descent(initial_alpha, data,
                                             max_passes=args.max_passes)

    pd.DataFrame(trajectory).to_csv(outdir / "robustez_trajectory.csv", index=False)
    pd.DataFrame([{
        "alpha_inicial": list(initial_alpha),
        "alpha_optima":  list(optimal["alpha"]),
        "ir_coverage_pct": optimal["ir_coverage_pct"],
        "min_delta_n":     optimal["min_delta_n"],
        "welfare_p2p":     optimal["welfare_p2p"],
        **{f"delta_{AGENT_NAMES[n]}": float(optimal["delta_n"][n])
           for n in range(N)},
    }]).to_csv(outdir / "robustez_optimal.csv", index=False)

    elapsed_total = time.time() - t_total
    print(f"\n[B2] Tiempo total: {elapsed_total:.1f}s")
    print(f"[B2] alpha inicial: {initial_alpha}")
    print(f"[B2] alpha optima:  {optimal['alpha']}")
    print(f"[B2] IR coverage:   {optimal['ir_coverage_pct']:.0f}%")
    print(f"[B2] min delta_n:   {optimal['min_delta_n']:+,.0f} COP")
    for n in range(N):
        print(f"     {AGENT_NAMES[n]:<10}: delta={float(optimal['delta_n'][n]):+,.0f} COP")
    print(f"[B2] Resultados en: {outdir}")


if __name__ == "__main__":
    main()
