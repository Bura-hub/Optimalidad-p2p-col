"""
Calibración: correr EMS P2P sobre 168 h (1 semana real MTE) y extrapolar
tiempo esperado del --full (6144 h).

Replica la configuración de main_simulation.py cuando se invoca con
--data real --full, pero truncando a las primeras 168 horas.
"""
import sys, os, time, warnings
warnings.filterwarnings("ignore")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np

from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams
from data.xm_data_loader import MTEDataLoader
from data.base_case_data import get_pde_weights, GRID_PARAMS_REAL, PGS, PGB
from data.xm_prices import get_b_for_real_data


def main():
    import multiprocessing
    multiprocessing.freeze_support()

    mte_root = os.environ.get("MTE_ROOT", os.path.join(ROOT, "MedicionesMTE_v3"))
    print(f"[1/3] Cargando datos MTE desde {mte_root}...")
    loader = MTEDataLoader(mte_root)
    D_full, G_full, index_full = loader.load(verbose=False)

    HORAS = 168   # 1 semana
    D = D_full[:, :HORAS]
    G = G_full[:, :HORAS]
    N = D.shape[0]

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

    print(f"[2/3] Corriendo EMS sobre {HORAS} h reales MTE...")
    print(f"    SolverParams: n_points={solver.n_points}, "
          f"ode_method={solver.ode_method}, parallel={solver.parallel}")

    ems = EMSP2P(agents, grid, solver)
    t0 = time.time()
    results, G_klim, D_star = ems.run(D, G)
    dt = time.time() - t0

    active = [r for r in results
              if r.P_star is not None and np.sum(r.P_star) > 1e-4]
    P_tot = sum(float(np.sum(r.P_star)) for r in active)

    print(f"\n[3/3] Resultados calibración ({HORAS} h):")
    print(f"    Tiempo EMS:           {dt:.1f} s  ({dt/60:.2f} min)")
    print(f"    Tiempo por hora:      {dt/HORAS:.3f} s/h")
    print(f"    Horas con mercado:    {len(active)}/{HORAS}  "
          f"({100*len(active)/HORAS:.1f}%)")
    print(f"    kWh P2P transados:    {P_tot:.2f}")

    # Extrapolación al full (6144 h)
    FULL = 6144
    t_full = dt * FULL / HORAS
    print(f"\nEXTRAPOLACIÓN AL --full ({FULL} h):")
    print(f"    Tiempo EMS esperado:  {t_full:.0f} s  "
          f"({t_full/60:.1f} min  ≈  {t_full/3600:.2f} h)")
    print(f"    + overhead fijo       ~60 s (carga datos, excel, figuras)")
    print(f"    + --analysis          ~900-1800 s (sensibilidad + factibilidad)")
    t_total_lo = t_full + 60 + 900
    t_total_hi = t_full + 60 + 1800
    print(f"    TOTAL --full:         {t_total_lo/3600:.2f} - "
          f"{t_total_hi/3600:.2f} horas")


if __name__ == "__main__":
    main()
