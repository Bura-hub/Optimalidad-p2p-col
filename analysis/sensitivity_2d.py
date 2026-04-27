"""
sensitivity_2d.py  — Análisis de sensibilidad bivariado (Actividad 4.1)
-----------------------------------------------------------------------
Brayan S. Lopez-Mendez · Udenar 2026

Barrido conjunto en la grilla {PGB × PV factor} para producir el mapa de
ganancia neta P2P. Complementa los barridos univariados SA-1 (PGB) y SA-2 (PV)
de `analysis/sensitivity.py`.

Estrategia computacional
~~~~~~~~~~~~~~~~~~~~~~~~
- Variar la cobertura PV requiere re-ejecutar el mercado P2P (despacho cambia).
- Variar PGB con G y el despacho fijos solo afecta la valoración monetaria.
  Por lo tanto, para cada PV se computa el P2P UNA vez y luego se barre PGB
  con `run_comparison` (cheap, ms).

Costo aproximado (perfil sintético 24 h, grid 20×20):
  - 20 sims EMS × ~3 s = ~60 s sequential, ~12 s con 6 workers
  - 400 evaluaciones run_comparison ~ 5–10 s
  TOTAL: ~30–60 s en una máquina moderna.
"""

from __future__ import annotations

import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class Sweep2DResult:
    pgb_grid:        np.ndarray  # (Npgb,)
    pv_grid:         np.ndarray  # (Npv,)
    pv_coverage:     np.ndarray  # (Npv,) cobertura efectiva G_total/D_total
    z_p2p:           np.ndarray  # (Npv, Npgb) ganancia neta P2P
    z_c4:            np.ndarray  # (Npv, Npgb) ganancia neta C4
    z_rpe:           np.ndarray  # (Npv, Npgb) (P2P - C4) / |P2P|
    z_ie_p2p:        np.ndarray  # (Npv, Npgb) índice de equidad P2P
    z_kwh_p2p:       np.ndarray  # (Npv, Npgb) energía intercambiada P2P (kWh)


def _run_one_pv(args):
    """
    Worker para un solo factor PV: ejecuta el EMS y barre PGB en serie.
    """
    (factor, D, G_base, agents_dict, grid_dict, solver_dict, pgb_grid, pde, prosumer_ids) = args
    from core.ems_p2p     import EMSP2P, AgentParams, GridParams, SolverParams
    from core.market_prep import compute_generation_limit
    from scenarios        import run_comparison

    agents = AgentParams(**agents_dict)
    grid   = GridParams(**grid_dict)
    solver = SolverParams(**solver_dict)

    T, N = D.shape[1], D.shape[0]
    G_scaled = G_base * factor
    G_klim_s = np.zeros((N, T))
    for k in range(T):
        G_klim_s[:, k] = compute_generation_limit(
            G_scaled[:, k], agents.a, agents.b, agents.c, grid.pi_gs)

    ems = EMSP2P(agents, grid, solver)
    p2p_res, _, _d = ems.run(D, G_scaled)

    coverage = float(G_scaled.sum() / max(D.sum(), 1e-9))

    row_p2p = np.zeros(len(pgb_grid))
    row_c4  = np.zeros(len(pgb_grid))
    row_rpe = np.zeros(len(pgb_grid))
    row_ie  = np.zeros(len(pgb_grid))
    row_kwh = np.zeros(len(pgb_grid))

    pde_v = pde if pde is not None else np.ones(N) / N
    capacity = np.maximum(G_scaled.mean(axis=1), 0)

    for j, pgb in enumerate(pgb_grid):
        pi_bolsa = np.full(T, pgb)
        cr = run_comparison(
            D=D, G_klim=G_klim_s, G_raw=G_scaled,
            p2p_results=p2p_res,
            pi_gs=grid.pi_gs, pi_gb=float(pgb),
            pi_bolsa=pi_bolsa,
            prosumer_ids=prosumer_ids, consumer_ids=[],
            pde=pde_v,
            pi_ppa=float(pgb) + 0.5 * (grid.pi_gs - float(pgb)),
            capacity=capacity,
        )
        row_p2p[j] = cr.net_benefit.get("P2P", 0.0)
        row_c4[j]  = cr.net_benefit.get("C4", 0.0)
        row_rpe[j] = cr.rpe or 0.0
        row_ie[j]  = cr.equity_index.get("P2P", 0.0)

        active = [r for r in p2p_res
                  if r.P_star is not None and np.sum(r.P_star) > 1e-4]
        row_kwh[j] = float(sum(np.sum(r.P_star) for r in active))

    return factor, coverage, row_p2p, row_c4, row_rpe, row_ie, row_kwh


def sweep_pgb_pv(
    D: np.ndarray,
    G_base: np.ndarray,
    agents,
    grid,
    solver,
    pgb_grid: Optional[np.ndarray] = None,
    pv_grid: Optional[np.ndarray]  = None,
    pde: Optional[np.ndarray]      = None,
    prosumer_ids: Optional[list]   = None,
    n_workers: int = 1,
    verbose: bool = True,
) -> Sweep2DResult:
    """
    Barrido bivariado PGB × PV.

    Parámetros
    ----------
    D, G_base : matrices (N, T)
    agents, grid, solver : dataclasses de core.ems_p2p
    pgb_grid : array de precios de bolsa (COP/kWh). Default 20 puntos en [200, 500].
    pv_grid  : array de factores PV. Default 20 puntos logspace en [1.0, 9.1] (≈11%–100% cobertura).
    n_workers : workers para ProcessPoolExecutor (1 = serial).
    """
    if pgb_grid is None:
        pgb_grid = np.linspace(200.0, 500.0, 20)
    if pv_grid is None:
        pv_grid = np.linspace(1.0, 9.1, 20)
    if prosumer_ids is None:
        prosumer_ids = list(range(D.shape[0]))
    pgb_grid = np.asarray(pgb_grid, dtype=float)
    pv_grid  = np.asarray(pv_grid,  dtype=float)
    Npv, Npgb = len(pv_grid), len(pgb_grid)

    if verbose:
        print(f"\n  Sensibilidad 2D PGB×PV: {Npv} factores PV × {Npgb} valores PGB "
              f"= {Npv*Npgb} puntos. Workers={n_workers}.")

    import dataclasses
    def _to_dict(obj):
        return {f.name: getattr(obj, f.name) for f in dataclasses.fields(obj)}
    agents_dict = _to_dict(agents)
    grid_dict   = _to_dict(grid)
    solver_dict = _to_dict(solver)

    args_list = [
        (float(f), D, G_base, agents_dict, grid_dict, solver_dict,
         pgb_grid, pde, prosumer_ids)
        for f in pv_grid
    ]

    z_p2p = np.zeros((Npv, Npgb))
    z_c4  = np.zeros((Npv, Npgb))
    z_rpe = np.zeros((Npv, Npgb))
    z_ie  = np.zeros((Npv, Npgb))
    z_kwh = np.zeros((Npv, Npgb))
    cov   = np.zeros(Npv)

    factor_to_idx = {float(f): i for i, f in enumerate(pv_grid)}

    if n_workers <= 1:
        for args in args_list:
            f, c, rp, rc, rr, ri, rk = _run_one_pv(args)
            i = factor_to_idx[f]
            cov[i] = c
            z_p2p[i] = rp; z_c4[i] = rc; z_rpe[i] = rr
            z_ie[i]  = ri; z_kwh[i] = rk
            if verbose:
                print(f"    PV factor {f:.2f}  cob={c*100:.0f}%  RPE@PGB_med={rr[Npgb//2]:.3f}")
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as ex:
            futures = [ex.submit(_run_one_pv, a) for a in args_list]
            for fut in as_completed(futures):
                f, c, rp, rc, rr, ri, rk = fut.result()
                i = factor_to_idx[f]
                cov[i] = c
                z_p2p[i] = rp; z_c4[i] = rc; z_rpe[i] = rr
                z_ie[i]  = ri; z_kwh[i] = rk
                if verbose:
                    print(f"    [done] PV factor {f:.2f}  cob={c*100:.0f}%")

    return Sweep2DResult(
        pgb_grid=pgb_grid, pv_grid=pv_grid, pv_coverage=cov,
        z_p2p=z_p2p, z_c4=z_c4, z_rpe=z_rpe, z_ie_p2p=z_ie, z_kwh_p2p=z_kwh,
    )


def to_parquet(result: Sweep2DResult, out_path: str) -> str:
    """Persiste el resultado en formato largo en un archivo parquet."""
    rows = []
    for i, (pv_f, cov) in enumerate(zip(result.pv_grid, result.pv_coverage)):
        for j, pgb in enumerate(result.pgb_grid):
            rows.append({
                "pv_factor":   float(pv_f),
                "pv_coverage": float(cov),
                "pgb":         float(pgb),
                "ganancia_p2p": float(result.z_p2p[i, j]),
                "ganancia_c4":  float(result.z_c4[i, j]),
                "rpe":          float(result.z_rpe[i, j]),
                "ie_p2p":       float(result.z_ie_p2p[i, j]),
                "kwh_p2p":      float(result.z_kwh_p2p[i, j]),
            })
    df = pd.DataFrame(rows)
    df.to_parquet(out_path, index=False)
    return out_path


def from_parquet(path: str) -> Sweep2DResult:
    """Reconstruye un Sweep2DResult desde el parquet largo."""
    df = pd.read_parquet(path)
    pv_factors = np.array(sorted(df["pv_factor"].unique()))
    pgb_vals   = np.array(sorted(df["pgb"].unique()))
    Npv, Npgb  = len(pv_factors), len(pgb_vals)
    z_p2p = np.zeros((Npv, Npgb)); z_c4 = np.zeros((Npv, Npgb))
    z_rpe = np.zeros((Npv, Npgb)); z_ie = np.zeros((Npv, Npgb))
    z_kwh = np.zeros((Npv, Npgb)); cov  = np.zeros(Npv)
    for i, pv_f in enumerate(pv_factors):
        sub_pv = df[df["pv_factor"] == pv_f]
        cov[i] = float(sub_pv["pv_coverage"].iloc[0])
        for j, pgb in enumerate(pgb_vals):
            row = sub_pv[sub_pv["pgb"] == pgb].iloc[0]
            z_p2p[i, j] = row["ganancia_p2p"]
            z_c4[i, j]  = row["ganancia_c4"]
            z_rpe[i, j] = row["rpe"]
            z_ie[i, j]  = row["ie_p2p"]
            z_kwh[i, j] = row["kwh_p2p"]
    return Sweep2DResult(
        pgb_grid=pgb_vals, pv_grid=pv_factors, pv_coverage=cov,
        z_p2p=z_p2p, z_c4=z_c4, z_rpe=z_rpe, z_ie_p2p=z_ie, z_kwh_p2p=z_kwh,
    )
