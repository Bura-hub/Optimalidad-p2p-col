"""
sweep_pgb_pv.py  — Barrido bivariado PGB × PV (Actividad 4.1)
-------------------------------------------------------------
Ejecuta el barrido 2D y persiste el resultado a parquet. La gráfica fig18 lee
ese parquet para construirse sin re-ejecutar las simulaciones.

Uso:
    python scripts/sweep_pgb_pv.py --grid 20 --workers 6
    python scripts/sweep_pgb_pv.py --grid 12 --workers 4 --base sintetico
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from multiprocessing import freeze_support
from pathlib import Path

import numpy as np

# Windows: forzar UTF-8 en stdout/stderr para soportar caracteres Unicode
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _load_synthetic_inputs():
    """Devuelve D, G, agents, grid, solver, prosumer_ids, pde para el caso sintético base."""
    from core.ems_p2p              import AgentParams, GridParams, SolverParams
    from data.base_case_data       import (
        get_generation_profiles, get_demand_profiles,
        get_agent_params, get_pde_weights, GRID_PARAMS,
    )

    G    = get_generation_profiles()
    D    = get_demand_profiles()
    p    = get_agent_params()
    pde  = get_pde_weights()

    agents = AgentParams(**p)
    grid   = GridParams(**GRID_PARAMS)
    solver = SolverParams(tau=0.001, t_span=(0.0, 0.005),
                          n_points=150, stackelberg_iters=2, parallel=False)

    prosumer_ids = [0, 1, 2, 3]
    return D, G, agents, grid, solver, prosumer_ids, pde


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=int, default=20,
                        help="Tamaño de la grilla NxN (default 20).")
    parser.add_argument("--workers", type=int, default=1,
                        help="Workers para ProcessPoolExecutor (default 1=serial).")
    parser.add_argument("--base", choices=["sintetico"], default="sintetico",
                        help="Caso base: sintético del modelo Sofía (única opción soportada hoy).")
    parser.add_argument("--out", type=str,
                        default="outputs/sensitivity_2d_pgb_pv.parquet")
    parser.add_argument("--pgb-min", type=float, default=200.0)
    parser.add_argument("--pgb-max", type=float, default=500.0)
    parser.add_argument("--pv-min", type=float, default=1.0)
    parser.add_argument("--pv-max", type=float, default=9.1)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))

    from analysis.sensitivity_2d import sweep_pgb_pv, to_parquet

    D, G, agents, grid, solver, prosumer_ids, pde = _load_synthetic_inputs()

    pgb_grid = np.linspace(args.pgb_min, args.pgb_max, args.grid)
    pv_grid  = np.linspace(args.pv_min,  args.pv_max,  args.grid)

    print(f"\n  Barrido 2D PGB×PV  base={args.base}  grid={args.grid}x{args.grid}  "
          f"workers={args.workers}")
    print(f"  PGB ∈ [{args.pgb_min:.0f}, {args.pgb_max:.0f}] COP/kWh")
    print(f"  PV  ∈ [{args.pv_min:.2f}, {args.pv_max:.2f}] (factor sobre G base)")

    result = sweep_pgb_pv(
        D=D, G_base=G, agents=agents, grid=grid, solver=solver,
        pgb_grid=pgb_grid, pv_grid=pv_grid, pde=pde,
        prosumer_ids=prosumer_ids, n_workers=args.workers,
        verbose=True,
    )

    out_path = repo_root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    to_parquet(result, str(out_path))

    print(f"\n  ✓ Resultado → {out_path}")
    print(f"  RPE rango: [{result.z_rpe.min():.3f}, {result.z_rpe.max():.3f}]")
    print(f"  Ganancia P2P rango: "
          f"[{result.z_p2p.min():,.0f}, {result.z_p2p.max():,.0f}]")
    return 0


if __name__ == "__main__":
    freeze_support()
    sys.exit(main())
