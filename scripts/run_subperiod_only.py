"""
Ejecuta solo la Actividad 4.3 (análisis de subperiodos) sobre el horizonte
completo 6144 h MTE. Usado después de que main_simulation.py --full crashó
en subperiod.py por el bug np.full(24, pgb) ya corregido.

Los resultados principales del --full (stages 1-5 excepto Actividad 4.3)
ya fueron guardados en resultados_comparacion.xlsx y p2p_breakdown.xlsx.
Este script llena el hueco que faltaba sin volver a correr las 22 pasadas
de EMS + sensibilidad.
"""
import sys, os, time, warnings
warnings.filterwarnings("ignore")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np

from core.ems_p2p import AgentParams, GridParams, SolverParams
from data.xm_data_loader import MTEDataLoader
from data.base_case_data import get_pde_weights, GRID_PARAMS_REAL, PGS, PGB
from data.xm_prices import get_b_for_real_data
from analysis.subperiod import (
    run_subperiod_analysis, print_subperiod_table, plot_subperiod,
)
from scenarios.scenario_c4_creg101072 import compute_pde_weights


def main():
    import multiprocessing
    multiprocessing.freeze_support()

    mte_root = os.environ.get("MTE_ROOT", os.path.join(ROOT, "MedicionesMTE_v3"))
    print(f"[1/3] Cargando datos MTE (6144 h)...")
    loader = MTEDataLoader(mte_root)
    D, G, idx = loader.load(verbose=False)
    N, T = D.shape
    print(f"    Shape D,G = ({N}, {T})")

    agent_names = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"][:N]
    b_cal = get_b_for_real_data(N, agent_names)

    agents = AgentParams(
        N=N,
        a=np.zeros(N),
        b=b_cal,
        c=np.full(N, 1.2),
        lam=np.full(N, 100.0),
        theta=np.full(N, 0.5),
        etha=np.full(N, 0.1),
        alpha=np.zeros(N),
    )
    grid   = GridParams(**GRID_PARAMS_REAL)
    solver = SolverParams(stackelberg_iters=2, parallel=True)

    pde = compute_pde_weights(np.maximum(G.mean(axis=1), 0))
    cap = np.maximum(G.mean(axis=1), 0)

    # IDs (heurística igual a main_simulation.py cuando use_real_data=True)
    prosumer_ids = [n for n in range(N) if cap[n] > 1e-6]
    consumer_ids = [n for n in range(N) if cap[n] <= 1e-6]
    if not prosumer_ids:
        prosumer_ids = list(range(N))
    if not consumer_ids:
        consumer_ids = [n for n in range(N) if n not in prosumer_ids]

    print(f"    prosumer_ids={prosumer_ids}, consumer_ids={consumer_ids}")
    print(f"\n[2/3] Corriendo subperiod_analysis sobre 6144 h (4 subperíodos SP1-SP4)...")
    t0 = time.time()
    sp_results = run_subperiod_analysis(
        D=D, G=G,
        agents=agents, grid=grid, solver=solver,
        pde=pde, prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
        pi_gs=GRID_PARAMS_REAL["pi_gs"], capacity=cap,
        agent_names=agent_names, currency="COP", verbose=True,
    )
    dt = time.time() - t0
    print(f"\n[3/3] Hecho en {dt:.1f}s ({dt/60:.1f} min)")

    print_subperiod_table(sp_results, currency="COP")

    plots_dir = os.path.join(ROOT, "graficas")
    os.makedirs(plots_dir, exist_ok=True)
    p = plot_subperiod(sp_results, out_dir=plots_dir, currency="COP")
    if p:
        print(f"    ✓ Fig 16 — Análisis de sub-períodos guardada")


if __name__ == "__main__":
    main()
