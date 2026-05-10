"""
scripts/run_heterogeneidad_paper.py
Heterogeneidad horaria del paper IEEE WEEF — case study (744 h MTE, phi=1.5).

Reemplaza el bench sintetico Chacon 24 h por una corrida sobre el experimento
real del paper: agosto 2025 (744 h hourly), demanda M3 (CAL-28), generacion
escalada por phi=1.5 (UPME 2030, CAL-29). Despues agrega los 744 valores
horarios por "hora del dia" (0..23) para producir un perfil diario equivalente
al formato del CSV sintetico.

Agregaciones por hora-del-dia:
- delta_COP, kwh_p2p, B_p2p_COP, B_c4_COP : SUM sobre los ~31 dias.
- GDR : MEAN sobre instancias activas (NaN si no hay activa esa hora).
- classification : voto mayoritario; "inactive" si nunca fue activa.
- active : True si hubo P2P activo en al menos 1 dia para esa hora.

Trazabilidad: Act 4.2 paper IEEE WEEF · CAL-29 (phi=1.5).
"""
from __future__ import annotations

import datetime
import sys
import time
from pathlib import Path

# Forzar UTF-8 en stdout (Windows charmap rompe con flechas y simbolos)
if sys.platform == "win32":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
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
from scenarios.scenario_c4_creg101072 import compute_pde_weights
from analysis.optimality import analyze_hourly_dominance


PHI_PAPER = 1.50
THETA_FIXED = 0.5
ALPHA_FIXED = 0.0


def _run_p2p_paper(D: np.ndarray, G: np.ndarray, params: dict
                    ) -> tuple[np.ndarray, list]:
    """Run P2P sobre el case study con phi=1.5. Retorna (G_klim, p2p_results)."""
    N = D.shape[0]
    G_scaled = G * PHI_PAPER

    agent_params = AgentParams(
        N=N,
        a=np.zeros(N),
        b=params["b_cal"],
        c=np.zeros(N),  # CAL-32 (apendice 2026-05-06b): c=0 PV puro
        lam=np.full(N, 100.0),
        theta=np.full(N, THETA_FIXED),
        etha=np.full(N, 0.1),
        alpha=np.full(N, ALPHA_FIXED),  # sin DR (paper)
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
    return G_klim, p2p_results, G_scaled, pi_gs_eff, pi_gb


def _aggregate_hourly(summary, idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Agrega los T HourlyOptimality por hora-del-dia (0..23).

    Devuelve DataFrame con columnas en el formato que consume
    `fig_audit_heterogeneidad_horaria`.
    """
    rows = []
    for h in summary.hourly_data:
        rows.append({
            "k": h.k,
            "hour_of_day": idx[h.k].hour,
            "kwh_p2p": h.kwh_p2p,
            "B_p2p_COP": h.B_p2p,
            "B_c4_COP": h.B_c4,
            "delta_COP": h.delta,
            "GDR": h.gdr,
            "classification": h.category,
            "active": bool(h.active),
        })
    df_full = pd.DataFrame(rows)

    out = []
    for hod in range(24):
        sub = df_full[df_full["hour_of_day"] == hod]
        active = sub[sub["active"]]
        n_total = len(sub)
        n_active = len(active)

        # Sumas (totales del mes en esa hora-del-dia)
        kwh_p2p_sum = float(active["kwh_p2p"].sum())
        b_p2p_sum = float(sub["B_p2p_COP"].sum())
        b_c4_sum = float(sub["B_c4_COP"].sum())
        delta_sum = float(sub["delta_COP"].sum())

        # GDR promedio sobre instancias activas
        if n_active > 0:
            gdr_mean = float(active["GDR"].mean())
        else:
            gdr_mean = 0.0

        # Clasificacion: mayoritaria entre instancias activas (sino "inactive")
        if n_active == 0:
            classification = "inactive"
            is_active = False
        else:
            counts = active["classification"].value_counts()
            classification = str(counts.idxmax())
            is_active = True

        out.append({
            "hour": hod,
            "kwh_p2p": kwh_p2p_sum,
            "B_p2p_COP": b_p2p_sum,
            "B_c4_COP": b_c4_sum,
            "delta_COP": delta_sum,
            "GDR": gdr_mean,
            "classification": classification,
            "active": is_active,
            "n_active_days": n_active,
            "n_total_days": n_total,
        })
    return pd.DataFrame(out)


def main() -> None:
    if sys.platform == "win32":
        import multiprocessing
        multiprocessing.freeze_support()

    print("[B3-paper] Heterogeneidad sobre case study (744 h, phi=1.5)")
    t_start, t_end = horizonte_mensual("2025-08")
    print(f"[B3-paper] Horizonte: [{t_start} .. {t_end})")

    print("[B3-paper] Cargando MTE...")
    D, G, idx, agents = cargar_mte_paper(t_start, t_end)
    print(f"[B3-paper] D.shape={D.shape}  G.shape={G.shape}")

    print("[B3-paper] Setup parametros...")
    params = setup_parametros(D, G, idx, agents)

    print(f"[B3-paper] Run P2P phi={PHI_PAPER}...")
    t0 = time.monotonic()
    G_klim, p2p_results, G_scaled, pi_gs_eff, pi_gb = _run_p2p_paper(
        D, G, params,
    )
    elapsed_ems = time.monotonic() - t0
    active_hrs = sum(
        1 for r in p2p_results
        if r.P_star is not None and float(np.sum(r.P_star)) > 1e-6
    )
    print(f"[B3-paper] EMS listo en {elapsed_ems:.1f}s | "
          f"horas activas: {active_hrs}/{D.shape[1]}")

    print("[B3-paper] Analizando dominancia P2P vs C4 hora a hora...")
    pde = compute_pde_weights(np.maximum(G_scaled.mean(axis=1), 0.0))
    summary = analyze_hourly_dominance(
        D=D,
        G_klim=G_klim,
        p2p_results=p2p_results,
        pde=pde,
        pi_gs=pi_gs_eff,
        pi_gb=pi_gb,
        pi_bolsa=params["pi_bolsa"],
        prosumer_ids=list(range(D.shape[0])),
        consumer_ids=[],
        threshold_cop=None,
    )

    print("[B3-paper] Agregando por hora-del-dia...")
    df_24h = _aggregate_hourly(summary, idx)

    # Output dir
    fecha = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    outdir = _REPO / "outputs" / f"audit_{fecha}" / "heterogeneidad"
    outdir.mkdir(parents=True, exist_ok=True)

    csv_main = outdir / "heterogeneidad_horaria.csv"
    df_24h.to_csv(csv_main, index=False)
    print(f"[B3-paper] CSV escrito: {csv_main}")

    # Summary file
    summary_row = {
        "horizon_h": D.shape[1],
        "phi": PHI_PAPER,
        "alpha": ALPHA_FIXED,
        "theta": THETA_FIXED,
        "active_hours_of_horizon": active_hrs,
        "active_hours_of_day": int(df_24h["active"].sum()),
        "delta_total_COP": float(df_24h["delta_COP"].sum()),
        "kwh_p2p_total": float(df_24h["kwh_p2p"].sum()),
        "GDR_mean_active": float(df_24h.loc[df_24h["active"], "GDR"].mean()),
        "elapsed_ems_s": round(elapsed_ems, 2),
    }
    pd.DataFrame([summary_row]).to_csv(
        outdir / "heterogeneidad_summary.csv", index=False,
    )

    # Top-5 horas-del-dia
    top5 = (df_24h
            .sort_values("delta_COP", ascending=False)
            .head(5)
            [["hour", "n_active_days", "kwh_p2p", "delta_COP",
              "GDR", "classification"]])
    top5.to_csv(outdir / "heterogeneidad_top5.csv", index=False)

    print("\n[B3-paper] Resumen por hora-del-dia (top-5 delta):")
    print(top5.to_string(index=False))
    print(f"\n[B3-paper] Total delta: {summary_row['delta_total_COP']:>14,.0f} COP")
    print(f"[B3-paper] Total kWh P2P: {summary_row['kwh_p2p_total']:>14,.1f} kWh")
    print(f"[B3-paper] GDR mean (active): {summary_row['GDR_mean_active']:.4f}")


if __name__ == "__main__":
    main()
