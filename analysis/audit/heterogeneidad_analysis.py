"""
analysis/audit/heterogeneidad_analysis.py — Eje 3 del audit.
Cuantifica la ventaja del P2P por captura de heterogeneidad horaria
frente a C4 (PDE estatico).  Delta_k = B_P2P(k) - B_C4(k) [COP].
GDR_k = kWh_P2P / min(G_net, D_net). Spread C4 = 1 004.4 kWh (notas
modelo tesis §3, lineas 55-63).  Trazabilidad: Act 4.2.
"""

from __future__ import annotations

import datetime
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# Windows: forzar UTF-8 en stdout para barras de progreso del EMS
if sys.platform == "win32":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# --- path setup so the script se puede correr directamente ---------------------
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams
from data.base_case_data import (
    get_agent_params, get_generation_profiles, get_demand_profiles,
    get_pde_weights, GRID_PARAMS, PGS, PGB,
)
from scenarios.scenario_c4_creg101072 import compute_pde_weights
from analysis.optimality import analyze_hourly_dominance, OptimalitySummary


def _run_p2p_synthetic() -> tuple[np.ndarray, np.ndarray, list, list, list]:
    """EMS P2P caso sintetico 24h -> (D, G_klim, p2p_results, pros_ids, cons_ids)."""
    G = get_generation_profiles()
    D = get_demand_profiles()
    p = get_agent_params()
    N = D.shape[0]

    agents = AgentParams(**p)
    grid   = GridParams(**GRID_PARAMS)
    solver = SolverParams(
        tau=0.001, t_span=(0.0, 0.005),
        n_points=150, stackelberg_iters=2, parallel=True,
    )
    ems = EMSP2P(agents, grid, solver)
    p2p_results, G_klim, _ = ems.run(D, G)

    prosumer_ids = [0, 1, 2, 3]
    consumer_ids = [4, 5]
    return D, G_klim, p2p_results, prosumer_ids, consumer_ids


def _build_pi_bolsa(T: int) -> np.ndarray:
    """Vector de precio bolsa constante al PGB del caso sintetico."""
    return np.full(T, float(PGB))


def _build_pde(G: np.ndarray) -> np.ndarray:
    cap = np.maximum(G.mean(axis=1), 0.0)
    return compute_pde_weights(cap)


def run_heterogeneidad_audit(outdir: Path) -> OptimalitySummary:
    """Ejecuta el analisis hora a hora y guarda los CSV de resultado."""
    print("[B3] Corriendo EMS P2P sobre perfil sintetico 24h ...")
    t0 = time.monotonic()

    D, G_klim, p2p_results, prosumer_ids, consumer_ids = _run_p2p_synthetic()
    T = D.shape[1]
    pi_bolsa = _build_pi_bolsa(T)
    pde      = _build_pde(G_klim)

    elapsed_ems = time.monotonic() - t0
    active_hrs  = sum(
        1 for r in p2p_results
        if r.P_star is not None and float(np.sum(r.P_star)) > 1e-6
    )
    print(f"[B3] EMS listo en {elapsed_ems:.1f}s | horas activas: {active_hrs}/{T}")

    print("[B3] Calculando dominancia horaria P2P vs C4 ...")
    summary = analyze_hourly_dominance(
        D=D,
        G_klim=G_klim,
        p2p_results=p2p_results,
        pde=pde,
        pi_gs=float(PGS),
        pi_gb=float(PGB),
        pi_bolsa=pi_bolsa,
        prosumer_ids=prosumer_ids,
        consumer_ids=consumer_ids,
        threshold_cop=None,   # umbral adaptativo (5 % beneficio medio)
    )

    rows = [
        {
            "hour":           h.k,
            "kwh_p2p":        h.kwh_p2p,
            "B_p2p_COP":      h.B_p2p,
            "B_c4_COP":       h.B_c4,
            "delta_COP":      h.delta,
            "GDR":            h.gdr,
            "classification": h.category,
            "active":         h.active,
        }
        for h in summary.hourly_data
    ]
    hourly_df = pd.DataFrame(rows)
    hourly_df.to_csv(outdir / "heterogeneidad_horaria.csv", index=False)

    s = summary
    summary_row = {
        "n_hours":          s.T_total,
        "P2P_dom_count":    s.n_p2p_dom,
        "C4_dom_count":     s.n_c4_dom,
        "neutral_count":    s.n_neutral,
        "inactive_count":   s.n_inactive,
        "active_count":     s.n_active,
        "total_delta_COP":  s.delta_total,
        "delta_mean_COP_h": s.delta_mean,
        "GDR_overall":      s.gdr_mean,
        "GDR_min":          s.gdr_min,
        "GDR_max":          s.gdr_max,
        "kwh_p2p_total":    s.kwh_p2p_total,
        "B_p2p_total_COP":  s.B_p2p_total,
        "B_c4_total_COP":   s.B_c4_total,
        "threshold_cop":    s.threshold_cop,
        "elapsed_ems_s":    round(elapsed_ems, 2),
    }
    pd.DataFrame([summary_row]).to_csv(outdir / "heterogeneidad_summary.csv", index=False)

    top5 = (hourly_df
            .sort_values("delta_COP", ascending=False)
            .head(5)
            [["hour", "kwh_p2p", "delta_COP", "GDR", "classification"]])
    top5.to_csv(outdir / "heterogeneidad_top5.csv", index=False)

    return summary


def _print_results(summary: OptimalitySummary) -> None:
    s = summary
    print("\n" + "=" * 60)
    print("  [B3] HETEROGENEIDAD HORARIA — P2P vs C4")
    print("=" * 60)
    print(f"  Horas totales     : {s.T_total}")
    print(f"  Horas activas P2P : {s.n_active}")
    print(f"  Umbral neutral    : {s.threshold_cop:,.0f} COP")
    print()
    print(f"  Clasificacion (horas activas):")
    print(f"    P2P_dom  : {s.n_p2p_dom}")
    print(f"    C4_dom   : {s.n_c4_dom}")
    print(f"    neutral  : {s.n_neutral}")
    print(f"    inactive : {s.n_inactive}")
    print()
    print(f"  GDR medio         : {s.gdr_mean:.4f}")
    print(f"  GDR rango         : [{s.gdr_min:.4f}, {s.gdr_max:.4f}]")
    print(f"  Delta total (COP) : {s.delta_total:,.0f}")
    print(f"  kWh P2P total     : {s.kwh_p2p_total:.3f}")
    print("=" * 60)

    top5 = sorted(summary.hourly_data, key=lambda h: h.delta, reverse=True)[:5]
    print("\n  Top-5 horas P2P_dom (mayor delta):")
    print(f"  {'hora':>4}  {'kWh_P2P':>9}  {'delta_COP':>12}  {'GDR':>6}  clase")
    for h in top5:
        print(f"  {h.k:>4}  {h.kwh_p2p:>9.4f}  {h.delta:>12,.0f}  "
              f"{h.gdr:>6.4f}  {h.category}")


def main() -> None:
    fecha  = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    outdir = Path(_ROOT / "outputs" / f"audit_{fecha}" / "heterogeneidad")
    outdir.mkdir(parents=True, exist_ok=True)

    t_start = time.monotonic()
    summary = run_heterogeneidad_audit(outdir)
    elapsed = time.monotonic() - t_start

    _print_results(summary)
    print(f"\n[B3] Archivos escritos en: {outdir}")
    print(f"[B3] Tiempo total: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
