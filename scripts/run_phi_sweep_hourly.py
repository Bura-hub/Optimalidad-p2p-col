"""
scripts/run_phi_sweep_hourly.py
Sweep phi sobre el horizon completo del paper (744h hourly, agosto 2025).

Mantiene alpha=0 y theta=0.5 fijos. Como theta-invariance ya esta confirmada
en el sweep daily, replicamos las 4 columnas theta sinteticamente en el CSV
de salida para mantener el formato del heatmap 4x4 sin gastar 4x el tiempo.

Genera CSV en outputs/audit_<fecha>/equidad/equidad_sweep.csv compatible
con visualization/audit_figures.py.

Trazabilidad: Act 4.2 paper IEEE WEEF.
"""
from __future__ import annotations

import datetime
import sys
import time
from pathlib import Path

# Forzar UTF-8 en stdout (Windows charmap rompe con flechas y simbolos)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                    errors="replace")

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.run_paper_iter import (
    cargar_mte_paper, setup_parametros, horizonte_mensual,
)
from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams
from scenarios.comparison_engine import run_comparison
from scenarios.scenario_c4_creg101072 import compute_pde_weights

PHI_GRID = [1.00, 1.25, 1.50, 1.75]
THETA_GRID = [0.25, 0.50, 0.75, 1.00]
THETA_FIXED = 0.5  # Solo se ejecuta este theta; los demas se replican
ALPHA_FIXED = 0.0


def run_one_hourly(D: np.ndarray, G: np.ndarray, params: dict,
                    phi: float, agents: list) -> dict:
    """Run paper-mode P2P + comparison para un valor de phi."""
    N, T = D.shape
    G_scaled = G * phi

    agent_params = AgentParams(
        N=N,
        a=np.zeros(N),
        b=params["b_cal"],
        c=np.zeros(N),  # CAL-32 (apendice 2026-05-06b): c=0 PV puro
        lam=np.full(N, 100.0),
        theta=np.full(N, THETA_FIXED),
        etha=np.full(N, 0.1),
        alpha=np.full(N, ALPHA_FIXED),
    )
    pi_gs_eff = float(np.mean(params["pi_gs"]))
    pi_gb = 234.0
    grid = GridParams(pi_gs=pi_gs_eff, pi_gb=pi_gb)
    solver = SolverParams(
        tau=0.001, t_span=(0.0, 0.005), n_points=150,
        stackelberg_iters=2, stackelberg_tol=1e-3, stackelberg_max=10,
        parallel=True,
    )
    ems = EMSP2P(agent_params, grid, solver)
    p2p_results, G_klim, _ = ems.run(D, G_scaled)

    pde = compute_pde_weights(np.maximum(G_scaled.mean(axis=1), 0))
    cap = np.maximum(G_scaled.mean(axis=1), 0)

    # month_labels para C1 mensual con Hx (CAL-10b)
    import pandas as pd_local
    idx_local = pd_local.date_range("2025-08-01", periods=T, freq="h")
    month_labels = np.array(
        [ts.year * 100 + ts.month for ts in idx_local], dtype=int,
    )

    # CAL-10b.2: Cvm literal Cedenar NT2 Aug 2025 (174.45 COP/kWh) en
    # vez de la aproximacion proporcional pi_gs * 0.1385 (~135 COP/kWh).
    # Mantiene consistencia con scripts/run_paper_iter.py.
    from data.cedenar_tariff import cvm_per_agent_hourly
    cvm_matrix = cvm_per_agent_hourly(agents, idx_local)

    cr = run_comparison(
        D=D, G_klim=G_klim, G_raw=G_scaled,
        p2p_results=p2p_results,
        pi_gs=params["pi_gs"],            # matriz N x T (CAL-9)
        pi_gb=pi_gb,
        pi_bolsa=params["pi_bolsa"],
        prosumer_ids=list(range(N)),
        consumer_ids=[],
        pde=pde,
        pi_ppa=None,
        capacity=cap,
        month_labels=month_labels,         # CAL-10b
        component_c=cvm_matrix,
        pi_G=params["g_comp"].mean(axis=1),
        g_component=params["g_comp"],
        cvm_component=params["cvm"],
        cot_component=params["cot"],
        mem_costs=params["mem"],
        cot_alpha=1.0,
    )

    return {
        "phi": phi,
        "IE_p2p":      cr.equity_index.get("P2P", float("nan")),
        "IE_C1":       cr.equity_index.get("C1",  float("nan")),
        "IE_C4":       cr.equity_index.get("C4",  float("nan")),
        "gini_p2p":    cr.gini.get("P2P",  float("nan")),
        "gini_C1":     cr.gini.get("C1",   float("nan")),
        "welfare_p2p": cr.net_benefit.get("P2P", float("nan")),
        "welfare_C1":  cr.net_benefit.get("C1",  float("nan")),
        "welfare_C4":  cr.net_benefit.get("C4",  float("nan")),
    }


def main() -> None:
    if sys.platform == "win32":
        import multiprocessing
        multiprocessing.freeze_support()

    print("[B1-hourly] Sweep phi sobre horizonte 744h (agosto 2025)")
    t_start, t_end = horizonte_mensual("2025-08")
    print(f"[B1-hourly] Horizonte: [{t_start} .. {t_end})")

    print("[B1-hourly] Cargando MTE...")
    D, G, idx, agents = cargar_mte_paper(t_start, t_end)
    print(f"[B1-hourly] D.shape={D.shape}  G.shape={G.shape}")

    print("[B1-hourly] Setup parametros...")
    params = setup_parametros(D, G, idx, agents)

    rows = []
    t_global = time.monotonic()
    for phi in PHI_GRID:
        print(f"\n[B1-hourly] phi={phi:.2f} ...", flush=True)
        t0 = time.monotonic()
        try:
            base = run_one_hourly(D, G, params, phi, agents)
        except Exception as exc:
            print(f"     ERROR: {exc}")
            base = {k: float("nan") for k in [
                "IE_p2p", "IE_C1", "IE_C4", "gini_p2p", "gini_C1",
                "welfare_p2p", "welfare_C1", "welfare_C4",
            ]}
            base["phi"] = phi
        compute_t = round(time.monotonic() - t0, 1)

        # Replicar la misma fila para los 4 thetas (theta-invariance ya probada)
        for theta in THETA_GRID:
            row = dict(base)
            row["alpha"] = ALPHA_FIXED
            row["theta"] = theta
            row["pof"] = 0.0
            row["compute_time"] = compute_t / 4  # promedio amortizado
            rows.append(row)

        print(f"     IE_p2p={base['IE_p2p']:+.4f}  "
              f"IE_C1={base['IE_C1']:+.4f}  "
              f"IE_C4={base['IE_C4']:+.4f}  "
              f"W_p2p={base['welfare_p2p']:>12,.0f}  "
              f"[{compute_t:.1f}s]")

    t_total = time.monotonic() - t_global
    print(f"\n[B1-hourly] Tiempo total: {t_total:.1f}s")

    # Generar CSV con formato compatible
    fecha = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    outdir = _REPO / "outputs" / f"audit_{fecha}" / "equidad"
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(rows)
    cols_order = ["phi", "alpha", "theta", "IE_p2p", "IE_C1", "IE_C4",
                  "gini_p2p", "gini_C1", "welfare_p2p", "welfare_C1",
                  "welfare_C4", "pof", "compute_time"]
    df = df[cols_order]
    csv_path = outdir / "equidad_sweep.csv"
    df.to_csv(csv_path, index=False)
    print(f"[B1-hourly] CSV escrito: {csv_path}")

    print("\n[B1-hourly] Resumen por phi:")
    summary = df.groupby("phi").first()[
        ["IE_p2p", "IE_C1", "IE_C4", "welfare_p2p", "welfare_C1", "welfare_C4"]
    ]
    print(summary.to_string())


if __name__ == "__main__":
    main()
