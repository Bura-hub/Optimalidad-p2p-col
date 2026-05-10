"""
analysis/stackelberg_convergence_real.py — CAL-19 Convergencia Stackelberg
============================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 2.1

Sustento empirico del default `stackelberg_iters=2` (CAL-1) sobre datos
MTE reales (no sintetico). Reemplaza el barrido sintetico de
`tests/calibration_study.py::calibrate_stackelberg_iters` con uno que
opera sobre la serie horaria reconstruida de las 5 instituciones MTE.

Modos:
  --quick : subset de 168 h (1 semana, ago-2025, alta actividad P2P).
            Barre iters in {1,2,3,5,8,10}. ~3-5 min total.
  --full  : horizonte completo 6144 h MTE (abr-2025 a dic-2025).
            Solo iters={2,10} para validar |delta net_benefit| < 1 %.
            ~10-15 min total.

Salidas:
  graficas/convergencia_stackelberg.csv  — tabla iters vs metricas
  graficas/convergencia_stackelberg.png  — curva de convergencia
  graficas/convergencia_stackelberg.mat  — para reproducibilidad MATLAB

Referencia: docs/adr/0019-cal19-stackelberg-convergencia-empirica.md
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Windows: forzar stdout a UTF-8 para que la barra de progreso del EMS
# no rompa con caracteres unicode (heredado de main_simulation.py).
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                   encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer,
                                   encoding="utf-8", errors="replace")


def _load_mte_subset(t_start: str, t_end: str):
    """Carga MTE completo y devuelve subset [t_start, t_end). Sin DR."""
    import os
    from data.xm_data_loader import MTEDataLoader, slice_horizon, AGENTS
    mte_root = os.environ.get("MTE_ROOT",
                              str(ROOT / "MedicionesMTE_v3"))
    loader = MTEDataLoader(root_path=mte_root)
    D_full, G_full, index_full = loader.load(verbose=False)
    D, G, idx = slice_horizon(D_full, G_full, index_full, t_start, t_end)
    return D, G, idx, list(AGENTS)


def _build_solver(iters: int):
    """Configura SolverParams con stackelberg_iters dado, todo demas default."""
    from core.ems_p2p import SolverParams
    return SolverParams(
        tau=0.001, t_span=(0.0, 0.005), n_points=150,
        stackelberg_iters=iters,
        stackelberg_tol=1e-3, stackelberg_max=max(iters, 10),
        parallel=True,
    )


def _build_agents_real(N: int, agent_names: list[str]):
    """AgentParams para datos reales (b calibrado, alpha=0 sin DR)."""
    from core.ems_p2p import AgentParams
    from data.xm_prices import get_b_for_real_data
    b = get_b_for_real_data(N, agent_names)
    return AgentParams(
        N=N,
        a=np.zeros(N), b=b, c=np.zeros(N),  # CAL-32 (2026-05-06b): c=0 PV puro
        lam=np.full(N, 100.0),
        theta=np.full(N, 0.5),
        etha=np.full(N, 0.1),
        alpha=np.zeros(N),  # sin DR para aislar el efecto del juego
    )


def _build_grid(pi_gs_eff: float, pi_gb: float):
    from core.ems_p2p import GridParams
    return GridParams(pi_gs=pi_gs_eff, pi_gb=pi_gb)


def run_one_iters(iters: int, D, G, agents, grid):
    """Corre un EMS completo con `stackelberg_iters=iters`. Devuelve metricas."""
    from core.ems_p2p import EMSP2P
    sv = _build_solver(iters)
    ems = EMSP2P(agents, grid, sv)

    t0 = time.time()
    p2p_results, _G_klim, _D_star = ems.run(D, G)
    elapsed = time.time() - t0

    # Resumen agregado
    active = [r for r in p2p_results
              if r.P_star is not None and np.sum(r.P_star) > 1e-4]
    kwh_p2p = sum(float(np.sum(r.P_star)) for r in active)
    welfare_total = sum(
        float((r.Wj_total or 0.0) + (r.Wi_total or 0.0))
        for r in p2p_results
    )
    # Convergencia real: iteraciones efectivas usadas y norma residual
    iters_used = [r.iters_used for r in active
                   if r.iters_used is not None]
    norms = [r.norm_rel_final for r in active
              if r.norm_rel_final is not None]
    return {
        "iters": iters,
        "elapsed_s": round(elapsed, 1),
        "horas_activas": len(active),
        "kwh_p2p_total": round(kwh_p2p, 3),
        "welfare_total": round(welfare_total, 1),
        "iters_used_median": float(np.median(iters_used)) if iters_used else 0.0,
        "iters_used_max": float(np.max(iters_used)) if iters_used else 0.0,
        "norm_rel_median": float(np.median(norms)) if norms else 0.0,
    }


def barrido_iters(D, G, iters_list: list[int],
                   pi_gs_eff: float, pi_gb: float,
                   agent_names: list[str]) -> pd.DataFrame:
    """Barrido stackelberg_iters in iters_list. Devuelve DataFrame ordenado."""
    N = D.shape[0]
    agents = _build_agents_real(N, agent_names)
    grid = _build_grid(pi_gs_eff, pi_gb)
    rows = []
    for it in iters_list:
        print(f"  [cal-19] iters={it}...")
        r = run_one_iters(it, D, G, agents, grid)
        print(f"    elapsed={r['elapsed_s']} s, kwh={r['kwh_p2p_total']:.2f}, "
              f"welfare={r['welfare_total']:.0f}, "
              f"iters_used median={r['iters_used_median']:.1f}, "
              f"norm_rel median={r['norm_rel_median']:.1e}")
        rows.append(r)
    df = pd.DataFrame(rows).set_index("iters").sort_index()

    # Convergencia relativa vs el iters maximo del barrido
    iter_ref = df.index.max()
    ref = df.loc[iter_ref]
    df["delta_kwh_pct"] = (
        (df["kwh_p2p_total"] - ref["kwh_p2p_total"]).abs()
        / max(ref["kwh_p2p_total"], 1e-9) * 100
    )
    df["delta_welfare_pct"] = (
        (df["welfare_total"] - ref["welfare_total"]).abs()
        / max(abs(ref["welfare_total"]), 1e-9) * 100
    )
    return df


def _save_outputs(df: pd.DataFrame, out_dir: Path, modo: str) -> None:
    """Guarda CSV, MAT y PNG con la curva de convergencia."""
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"convergencia_stackelberg_{modo}.csv"
    df.to_csv(csv_path)
    print(f"  [cal-19] CSV  -> {csv_path}")

    try:
        from scipy.io import savemat
        savemat(str(out_dir / f"convergencia_stackelberg_{modo}.mat"),
                {"iters": df.index.to_numpy(dtype=float),
                 "kwh_p2p_total": df["kwh_p2p_total"].to_numpy(),
                 "welfare_total": df["welfare_total"].to_numpy(),
                 "delta_kwh_pct": df["delta_kwh_pct"].to_numpy(),
                 "delta_welfare_pct": df["delta_welfare_pct"].to_numpy()})
    except Exception as e:
        print(f"  [cal-19] MAT skipped ({e})")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharex=True)

        ax = axes[0]
        ax.plot(df.index, df["welfare_total"] / 1e3,
                "o-", color="tab:blue")
        ax.set_xlabel("stackelberg_iters")
        ax.set_ylabel("Bienestar total comunitario [k$]")
        ax.set_title("Convergencia del bienestar")
        ax.grid(alpha=0.3)

        ax = axes[1]
        ax.semilogy(df.index, df["delta_welfare_pct"].clip(lower=1e-4),
                    "o-", color="tab:red", label="|Delta welfare| / ref")
        ax.semilogy(df.index, df["delta_kwh_pct"].clip(lower=1e-4),
                    "s--", color="tab:green", label="|Delta kWh_P2P| / ref")
        ax.axhline(1.0, color="gray", lw=0.8, ls=":", label="1 %")
        ax.set_xlabel("stackelberg_iters")
        ax.set_ylabel("Error relativo vs iters_ref [%]")
        ax.set_title("Convergencia (escala log)")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=0.3, which="both")

        fig.suptitle(f"CAL-19 — convergencia Stackelberg (modo {modo})")
        fig.tight_layout()
        png_path = out_dir / f"convergencia_stackelberg_{modo}.png"
        fig.savefig(png_path, dpi=130, bbox_inches="tight")
        plt.close(fig)
        print(f"  [cal-19] PNG  -> {png_path}")
    except Exception as e:
        print(f"  [cal-19] PNG skipped ({e})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true",
                    help="Subset 168 h ago-2025 (default; rapido).")
    ap.add_argument("--full", action="store_true",
                    help="Horizonte completo MTE 6144 h (lento, validacion).")
    ap.add_argument("--t-start", default=None,
                    help="Fecha inicio override (YYYY-MM-DD).")
    ap.add_argument("--t-end", default=None,
                    help="Fecha fin override (YYYY-MM-DD).")
    ap.add_argument("--iters", default=None,
                    help="Lista de iters separada por comas (override).")
    ap.add_argument("--out-dir", default=str(ROOT / "graficas"))
    args = ap.parse_args()

    if args.full:
        modo = "full"
        t_start = args.t_start or "2025-04-04"
        t_end = args.t_end or "2025-12-16"
        iters_list = [2, 10] if args.iters is None else [
            int(x) for x in args.iters.split(",")
        ]
    else:
        modo = "quick"
        t_start = args.t_start or "2025-08-04"
        t_end = args.t_end or "2025-08-11"
        iters_list = [1, 2, 3, 5, 8, 10] if args.iters is None else [
            int(x) for x in args.iters.split(",")
        ]

    print(f"  [cal-19] modo={modo}, [{t_start} .. {t_end})")
    print(f"  [cal-19] iters a barrer: {iters_list}")

    D, G, idx, agent_names = _load_mte_subset(t_start, t_end)
    print(f"  [cal-19] D={D.shape}, G={G.shape}, T={len(idx)} h")

    # Tarifa promedio del subperiodo (CAL-9): comunitaria efectiva.
    from data.cedenar_tariff import community_effective_pi_gs
    pi_gs_eff = community_effective_pi_gs(
        agent_names, t_start=t_start, t_end=t_end,
        weights=D.mean(axis=1),
    )
    pi_gb = float(np.mean([280.0]))  # baseline conservador (PGB_COP de CAL-6)
    print(f"  [cal-19] pi_gs efectivo comunitario: {pi_gs_eff:.1f} COP/kWh")

    df = barrido_iters(D, G, iters_list, pi_gs_eff, pi_gb, agent_names)
    print()
    print(df.to_string())

    out_dir = Path(args.out_dir)
    _save_outputs(df, out_dir, modo)
    print()
    print("  [cal-19] hecho.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
