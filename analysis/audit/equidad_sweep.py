"""
analysis/audit/equidad_sweep.py
--------------------------------
Eje 1 del audit de calibracion: barrido alpha_n x theta para fortalecer
la ventaja de equidad del mercado P2P frente a C1/C4.

El script ejecuta un grid 4x4 (16 configuraciones) sobre el perfil diario
promedio MTE (T=24h) e informa IE, Gini, PoF y welfare por configuracion.

Trazabilidad: Act 4.2, anexo defensivo del paper.

Metodologia de override:
  AgentParams.alpha y AgentParams.theta son arrays de longitud N inyectados
  directamente al construir el objeto; no se modifica ningun archivo del repo.
  Para datos reales (--data daily), alpha=0 es el default de produccion porque
  la demanda MTE es un insumo fijo observado (sin DR activo). El sweep mueve
  alpha fuera de ese default para cuantificar el efecto sobre equidad.
"""

import argparse
import datetime
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")

# Forzar UTF-8 en Windows para evitar errores de codificacion
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path

import numpy as np
import pandas as pd

# --- inserta la raiz del repo en el path para imports absolutos ---------------
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams
from scenarios.comparison_engine import run_comparison
from data.base_case_data import GRID_PARAMS_REAL, PGB_COP
from data.xm_prices import get_pi_bolsa
from data.cedenar_tariff import (
    effective_pi_gs_per_agent,
    g_plus_commercialization_per_agent_hourly,
    cu_components_per_agent_hourly,
    mem_costs_per_agent_hourly,
)
from data.xm_data_loader import MTEDataLoader, daily_profiles

# --- Grids de barrido ---------------------------------------------------------
ALPHA_GRID = [0.10, 0.15, 0.20, 0.25]  # fraccion de demanda flexible
THETA_GRID = [0.25, 0.50, 0.75, 1.00]  # coeficiente cuadratico de costo

# Nombres de agentes MTE
AGENT_NAMES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]


def _load_daily_data() -> dict:
    """Carga el perfil diario promedio MTE (T=24h) y parametros fijos."""
    mte_root = os.environ.get(
        "MTE_ROOT",
        str(_REPO_ROOT / "MedicionesMTE_v3"),
    )
    loader = MTEDataLoader(mte_root)
    D_full, G_full, index_full = loader.load(verbose=False)

    N = D_full.shape[0]
    agent_names = AGENT_NAMES[:N]

    D, G = daily_profiles(D_full, G_full, index_full)
    T = 24

    # pi_gs vector (N,) promedio del horizonte (perfil diario sin mes-a-mes)
    pi_gs_per_agent = effective_pi_gs_per_agent(
        agent_names,
        index_full[0],
        index_full[-1] + pd.Timedelta(hours=1),
    )
    pi_gb = PGB_COP

    xm_csv = _REPO_ROOT / "data" / "xm_precios_bolsa.csv"
    pi_bolsa = get_pi_bolsa(
        T,
        csv_path=str(xm_csv) if xm_csv.exists() else None,
        scenario="2025_normal",
    )

    # CAL-13: rango negociable G+Cvm+COT como promedio del horizonte
    pi_G_full = g_plus_commercialization_per_agent_hourly(agent_names, index_full)
    pi_G_arg = pi_G_full.mean(axis=1)  # (N,)

    # CAL-16: descomposicion regulatoria del ahorro en C2
    cu_comps_full = cu_components_per_agent_hourly(agent_names, index_full)
    mem_full = mem_costs_per_agent_hourly(agent_names, index_full)
    cu_comps = {k: np.nanmean(v, axis=1) for k, v in cu_comps_full.items()}
    mem_arg = np.nanmean(mem_full, axis=1)

    # pi_ppa default f=0.5 (CAL-21)
    g_mean = float(np.nanmean(cu_comps["G"]))
    cvm_mean = float(np.nanmean(cu_comps["Cvm"]))
    cot_mean = float(np.nanmean(cu_comps["COT"]))
    mem_mean = float(np.nanmean(mem_arg))
    pi_upper = g_mean + cvm_mean + 1.0 * cot_mean - mem_mean
    pi_ppa = pi_gb + 0.5 * (pi_upper - pi_gb)

    from scenarios.scenario_c4_creg101072 import compute_pde_weights
    pde = compute_pde_weights(np.maximum(G_full.mean(axis=1), 0))
    cap = np.maximum(G_full.mean(axis=1), 0)

    return dict(
        D=D, G=G, N=N, T=T,
        agent_names=agent_names,
        pi_gs_arg=pi_gs_per_agent,
        pi_gb=pi_gb,
        pi_bolsa=pi_bolsa,
        pde=pde, cap=cap,
        pi_ppa=pi_ppa, pi_G_arg=pi_G_arg,
        g_arg=cu_comps["G"], cvm_arg=cu_comps["Cvm"],
        cot_arg=cu_comps["COT"], mem_arg=mem_arg,
        prosumer_ids=list(range(N)), consumer_ids=[],
    )


def _load_synthetic_data() -> dict:
    """Carga datos sinteticos de validacion (24h, 6 agentes)."""
    from data.base_case_data import (
        get_generation_profiles, get_demand_profiles,
        get_agent_params, get_pde_weights, GRID_PARAMS, PGS, PGB,
    )
    from data.xm_prices import get_pi_bolsa as _gp

    G = get_generation_profiles()
    D = get_demand_profiles()
    p = get_agent_params()
    N, T = D.shape

    pi_bolsa = np.full(T, PGB)
    pi_G_arg = float(np.mean(pi_bolsa)) * 1.5
    pi_ppa = PGB + 0.5 * (pi_G_arg - PGB)

    return dict(
        D=D, G=G, N=N, T=T,
        agent_names=[f"A{i+1}" for i in range(N)],
        pi_gs_arg=GRID_PARAMS["pi_gs"],
        pi_gb=PGB,
        pi_bolsa=pi_bolsa,
        pde=get_pde_weights(),
        cap=np.array([3., 4., 3., 2., 0., 0.]),
        pi_ppa=pi_ppa, pi_G_arg=pi_G_arg,
        g_arg=None, cvm_arg=None, cot_arg=None, mem_arg=None,
        prosumer_ids=[0, 1, 2, 3], consumer_ids=[4, 5],
    )


def run_one_config(data: dict, alpha_uniform: float,
                   theta_uniform: float) -> dict:
    """
    Ejecuta un run P2P + comparacion con alpha_n y theta uniformes.

    Retorna dict con IE_p2p, IE_C1, IE_C4, gini_p2p, welfare_p2p,
    welfare_C1, welfare_C4, pof, alpha, theta, compute_time.
    """
    N = data["N"]

    agents = AgentParams(
        N=N,
        a=np.zeros(N),
        b=np.zeros(N),
        c=np.full(N, 1.2) if data["g_arg"] is not None else np.zeros(N),
        lam=np.full(N, 100.0),
        theta=np.full(N, theta_uniform),
        etha=np.full(N, 0.1),
        alpha=np.full(N, alpha_uniform),
    )
    grid = GridParams(
        pi_gs=(float(np.mean(data["pi_gs_arg"]))
               if isinstance(data["pi_gs_arg"], np.ndarray)
               else float(data["pi_gs_arg"])),
        pi_gb=float(data["pi_gb"]),
    )
    solver = SolverParams(
        tau=0.001, t_span=(0.0, 0.005),
        n_points=150, stackelberg_iters=2, parallel=False,
    )

    ems = EMSP2P(agents, grid, solver)
    D_run = data["D"].copy()
    G_run = data["G"].copy()
    p2p_results, G_klim, D_star = ems.run(D_run, G_run)

    if np.any(agents.alpha > 1e-9):
        D_run = D_star

    cr = run_comparison(
        D=D_run, G_klim=G_klim, G_raw=G_run,
        p2p_results=p2p_results,
        pi_gs=data["pi_gs_arg"],
        pi_gb=float(data["pi_gb"]),
        pi_bolsa=data["pi_bolsa"],
        prosumer_ids=data["prosumer_ids"],
        consumer_ids=data["consumer_ids"],
        pde=data["pde"],
        pi_ppa=data["pi_ppa"],
        capacity=data["cap"],
        month_labels=None,
        component_c="auto",
        pi_G=data["pi_G_arg"],
        g_component=data["g_arg"],
        cvm_component=data["cvm_arg"],
        cot_component=data["cot_arg"],
        mem_costs=data["mem_arg"],
        cot_alpha=1.0,
    )

    pof_val = cr.fairness.pof if cr.fairness is not None else float("nan")
    return {
        "IE_p2p":      cr.equity_index.get("P2P", float("nan")),
        "IE_C1":       cr.equity_index.get("C1",  float("nan")),
        "IE_C4":       cr.equity_index.get("C4",  float("nan")),
        "gini_p2p":    cr.gini.get("P2P",  float("nan")),
        "gini_C1":     cr.gini.get("C1",   float("nan")),
        "welfare_p2p": cr.net_benefit.get("P2P", float("nan")),
        "welfare_C1":  cr.net_benefit.get("C1",  float("nan")),
        "welfare_C4":  cr.net_benefit.get("C4",  float("nan")),
        "pof":         pof_val,
    }


def main() -> None:
    """Punto de entrada: barrido 4x4 alpha x theta sobre perfil diario."""
    if sys.platform == "win32":
        import multiprocessing
        multiprocessing.freeze_support()

    ap = argparse.ArgumentParser(
        description="Barrido alpha x theta para auditoria de equidad P2P")
    ap.add_argument(
        "--data",
        choices=["synthetic", "daily"],
        default="daily",
        help="Fuente de datos: 'daily' = perfil MTE, 'synthetic' = modelo base",
    )
    ap.add_argument(
        "--output-dir", default=None,
        help="Directorio de salida (default: outputs/audit_<fecha>/equidad/)",
    )
    args = ap.parse_args()

    fecha = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    outdir = Path(args.output_dir or
                  (_REPO_ROOT / "outputs" / f"audit_{fecha}" / "equidad"))
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"[B1] Cargando datos ({args.data})...")
    if args.data == "daily":
        data = _load_daily_data()
    else:
        data = _load_synthetic_data()
    print(f"[B1] N={data['N']}  T={data['T']}h  agentes={data['agent_names']}")

    rows = []
    t_global = time.monotonic()
    for alpha in ALPHA_GRID:
        for theta in THETA_GRID:
            print(f"[B1] alpha={alpha:.2f}  theta={theta:.2f} ...", flush=True)
            t0 = time.monotonic()
            try:
                res = run_one_config(data, alpha, theta)
            except Exception as exc:  # noqa: BLE001
                print(f"     ERROR: {exc}")
                res = {k: float("nan") for k in [
                    "IE_p2p", "IE_C1", "IE_C4", "gini_p2p", "gini_C1",
                    "welfare_p2p", "welfare_C1", "welfare_C4", "pof",
                ]}
            res["alpha"] = alpha
            res["theta"] = theta
            res["compute_time"] = round(time.monotonic() - t0, 2)
            rows.append(res)
            print(f"     IE_p2p={res['IE_p2p']:+.4f}  IE_C1={res['IE_C1']:+.4f}"
                  f"  gini_p2p={res['gini_p2p']:.4f}"
                  f"  W_p2p={res['welfare_p2p']:,.0f}"
                  f"  [{res['compute_time']:.1f}s]")

    t_total = time.monotonic() - t_global
    df = pd.DataFrame(rows)
    cols_order = ["alpha", "theta", "IE_p2p", "IE_C1", "IE_C4",
                  "gini_p2p", "gini_C1", "welfare_p2p", "welfare_C1",
                  "welfare_C4", "pof", "compute_time"]
    df = df[cols_order]
    csv_path = outdir / "equidad_sweep.csv"
    df.to_csv(csv_path, index=False)

    print(f"\n[B1] Resultados completos ({len(df)} configuraciones):")
    print(df.to_string(index=False))

    top3 = df.nlargest(3, "IE_p2p")
    top3_path = outdir / "equidad_top3.csv"
    top3.to_csv(top3_path, index=False)

    print(f"\n[B1] Top-3 por IE_p2p (mayor equidad P2P):")
    print(top3[["alpha", "theta", "IE_p2p", "IE_C1", "gini_p2p",
                "welfare_p2p", "welfare_C1"]].to_string(index=False))

    print(f"\n[B1] Tiempo total: {t_total:.1f}s")
    print(f"[B1] Resultados en: {outdir}")


if __name__ == "__main__":
    main()
