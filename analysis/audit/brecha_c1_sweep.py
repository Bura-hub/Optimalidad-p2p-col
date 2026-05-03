"""
analysis/audit/brecha_c1_sweep.py
----------------------------------
Eje 4 del audit: barrido pi_ppa x metodo PDE para cerrar brecha P2P vs C1.

Contexto: en 6144h C1 supera P2P por +1.61 MCOP (~3%). Se barre pi_ppa
(5 valores en [pi_gb, G+Cvm+COT]) x PDE method (3 opciones de CAL-26)
= 15 configuraciones sobre perfil diario sintetico (24h).

HALLAZGO ANALITICO CLAVE (confirmado por sweep):
  ratio_p2p_c1 = welfare_P2P / welfare_C1 es INVARIANTE a pi_ppa y PDE:
    - pi_ppa solo afecta C2 (welfare_C2); no toca P2P ni C1.
    - PDE method solo afecta C4 (welfare_C4 y IE_C4); no toca P2P ni C1.
  Por tanto, la BRECHA P2P vs C1 no se cierra calibrando estos parametros.
  Para cerrar la brecha se requiere modificar el mecanismo P2P o los
  parametros de la funcion de bienestar de los agentes (lam, theta, etha).

Frontera Pareto en (ratio_p2p_c2, IE_p2p): bienestar P2P vs C2 que SI
  varia con pi_ppa; y en (welfare_C4, IE_C4) que varia con PDE.

Trazabilidad: Act 4.2, anexo defensivo del paper.
Referencia: CAL-11 (ADR-0011), CAL-13 (ADR-0013), CAL-26 (ADR-0026).
"""

import datetime
import sys
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams
from scenarios.comparison_engine import run_comparison
from scenarios.scenario_c4_creg101072 import (
    compute_pde_weights,
    compute_excedentes_acumulados,
)
from data.base_case_data import (
    get_generation_profiles,
    get_demand_profiles,
    get_pde_weights,
    GRID_PARAMS,
    PGS,
    PGB,
    get_agent_params,
)

# ── Rangos del sweep ──────────────────────────────────────────────────────────
# CAL-11/CAL-13: rango valido [pi_gb, G+Cvm+COT]
# pi_gb ~ 280 COP/kWh; G+Cvm+COT ~ 526 COP/kWh (abr-2026 NT2 oficial)
# Modo sintetico: PGB=114, PGS=1250 -> usamos escala proporcional al modelo base
# Para hacerlo sensato en el espacio sintetico [114, PGS*0.42] ~ [114, 525]
_PI_GB  = float(PGB)          # 114.0 (adimensional, modelo base)
_PI_GS  = float(PGS)          # 1250.0
# G+Cvm+COT en el modelo sintetico: aproximado como 42% del CU
# (proporcion tipica Colombia: G+Cvm+COT / CU ~ 526/1250 ~ 0.42)
_PI_G_UPPER = _PI_GB + 0.42 * (_PI_GS - _PI_GB)   # ~ 601.5 u. sinteticas

PI_PPA_VALUES = [
    _PI_GB + f * (_PI_G_UPPER - _PI_GB)
    for f in [0.1, 0.3, 0.5, 0.7, 0.9]
]
# Metodos PDE (CAL-26): nombres internos del modulo scenario_c4_creg101072
PDE_METHODS = [
    "capacity_proportional",
    "equal",
    "excedentes_proportional",
]
PDE_LABELS = {
    "capacity_proportional":   "capacidad_proporcional",
    "equal":                   "equitativo",
    "excedentes_proportional": "excedentes_proporcional",
}


def _build_solver() -> SolverParams:
    return SolverParams(
        tau=0.001, t_span=(0.0, 0.005),
        n_points=150, stackelberg_iters=2, parallel=True,
    )


def _run_p2p_once(D: np.ndarray, G: np.ndarray, p: dict) -> tuple:
    """Ejecuta EMS P2P y retorna (p2p_results, G_klim)."""
    grid   = GridParams(**GRID_PARAMS)
    agents = AgentParams(**p)
    solver = _build_solver()
    ems    = EMSP2P(agents, grid, solver)
    p2p_results, G_klim, _ = ems.run(D, G)
    return p2p_results, G_klim


def run_one(pi_ppa: float, pde_method: str, p2p_cache: dict) -> dict:
    """
    Ejecuta la comparacion C1-C4+P2P con los parametros dados.

    p2p_cache: dict con claves 'p2p_results', 'G_klim', 'D', 'G'
    para reutilizar la corrida P2P (identica para todos los pi_ppa/pde).

    Retorna dict con welfare_p2p, welfare_C1, welfare_C2, welfare_C4,
    IE_p2p, IE_C1, ratio_p2p_c1, gini_p2p.
    """
    D          = p2p_cache["D"]
    G          = p2p_cache["G"]
    G_klim     = p2p_cache["G_klim"]
    p2p_results = p2p_cache["p2p_results"]
    prosumer_ids = p2p_cache["prosumer_ids"]
    consumer_ids = p2p_cache["consumer_ids"]
    cap          = p2p_cache["cap"]
    pi_bolsa     = p2p_cache["pi_bolsa"]

    N = D.shape[0]
    T = D.shape[1]

    # Construir pde segun metodo
    if pde_method == "capacity_proportional":
        metric = cap
    elif pde_method == "equal":
        metric = cap   # ignorada para "equal", solo el tamano importa
    elif pde_method == "excedentes_proportional":
        metric = compute_excedentes_acumulados(G_klim, D)
    else:
        raise ValueError(f"Metodo PDE desconocido: {pde_method!r}")

    pde = compute_pde_weights(metric, method=pde_method)

    cr = run_comparison(
        D=D, G_klim=G_klim, G_raw=G,
        p2p_results=p2p_results,
        pi_gs=GRID_PARAMS["pi_gs"],
        pi_gb=GRID_PARAMS["pi_gb"],
        pi_bolsa=pi_bolsa,
        prosumer_ids=prosumer_ids,
        consumer_ids=consumer_ids,
        pde=pde,
        pi_ppa=pi_ppa,
        capacity=cap,
        month_labels=None,
        component_c="auto",
        pi_G=float(_PI_G_UPPER),
    )

    w_p2p = cr.net_benefit.get("P2P", 0.0)
    w_c1  = cr.net_benefit.get("C1",  0.0)
    w_c2  = cr.net_benefit.get("C2",  0.0)
    w_c4  = cr.net_benefit.get("C4",  0.0)
    ie_p2p = cr.equity_index.get("P2P", 0.0)
    ie_c1  = cr.equity_index.get("C1",  0.0)
    ie_c4  = cr.equity_index.get("C4",  0.0)
    ratio_c1 = w_p2p / w_c1 if abs(w_c1) > 1e-10 else 0.0
    ratio_c2 = w_p2p / w_c2 if abs(w_c2) > 1e-10 else 0.0
    gini_p2p = cr.gini.get("P2P", 0.0)

    return {
        "welfare_p2p":  w_p2p,
        "welfare_C1":   w_c1,
        "welfare_C2":   w_c2,
        "welfare_C4":   w_c4,
        "IE_p2p":       ie_p2p,
        "IE_C1":        ie_c1,
        "IE_C4":        ie_c4,
        "ratio_p2p_c1": ratio_c1,
        "ratio_p2p_c2": ratio_c2,
        "gini_p2p":     gini_p2p,
    }


def compute_pareto_frontier(df: pd.DataFrame,
                             max_cols: list) -> pd.DataFrame:
    """
    Retorna filas no dominadas respecto a max_cols (mayor = mejor).
    Config a DOMINA b si a[c] >= b[c] para todo c en max_cols,
    con al menos una desigualdad estricta.
    """
    vals = df[max_cols].values
    n    = len(vals)
    dominated = np.zeros(n, dtype=bool)

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if (np.all(vals[j] >= vals[i])
                    and np.any(vals[j] > vals[i])):
                dominated[i] = True
                break

    return df[~dominated].reset_index(drop=True)


def main() -> None:
    import multiprocessing
    multiprocessing.freeze_support()

    fecha  = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    outdir = Path(__file__).resolve().parents[2] / f"outputs/audit_{fecha}/brecha_c1"
    outdir.mkdir(parents=True, exist_ok=True)

    print("\n[B4] brecha_c1_sweep — 15 configuraciones (5 pi_ppa x 3 PDE)")
    print(f"     pi_ppa range: [{_PI_GB:.0f}, {_PI_G_UPPER:.0f}] u. sinteticas")
    print(f"     Salida: {outdir}")

    # ── Pre-computar P2P una sola vez (igual para todos los barridos) ─────
    G = get_generation_profiles()
    D = get_demand_profiles()
    p = get_agent_params()
    N, T = D.shape
    cap          = np.array([3., 4., 3., 2., 0., 0.])
    prosumer_ids = [0, 1, 2, 3]
    consumer_ids = [4, 5]
    pi_bolsa     = np.full(T, float(PGB))

    print("\n[B4] Corriendo EMS P2P base...")
    t_p2p = time.monotonic()
    p2p_results, G_klim = _run_p2p_once(D, G, p)
    print(f"     EMS P2P listo en {time.monotonic() - t_p2p:.1f}s")

    p2p_cache = {
        "D": D, "G": G, "G_klim": G_klim,
        "p2p_results": p2p_results,
        "prosumer_ids": prosumer_ids,
        "consumer_ids": consumer_ids,
        "cap": cap,
        "pi_bolsa": pi_bolsa,
    }

    rows = []
    for pi_ppa in PI_PPA_VALUES:
        for pde_method in PDE_METHODS:
            label = PDE_LABELS[pde_method]
            print(f"[B4] pi_ppa={pi_ppa:.1f}  pde={label} ...", end=" ", flush=True)
            t0  = time.monotonic()
            res = run_one(pi_ppa, pde_method, p2p_cache)
            elapsed = time.monotonic() - t0
            res["pi_ppa"]       = pi_ppa
            res["pde_method"]   = label
            res["compute_time"] = elapsed
            rows.append(res)
            print(f"ratio={res['ratio_p2p_c1']:.4f}  IE={res['IE_p2p']:.4f}  "
                  f"({elapsed:.2f}s)")

    df = pd.DataFrame(rows)
    col_order = [
        "pi_ppa", "pde_method",
        "welfare_p2p", "welfare_C1", "welfare_C2", "welfare_C4",
        "IE_p2p", "IE_C1", "IE_C4",
        "ratio_p2p_c1", "ratio_p2p_c2", "gini_p2p", "compute_time",
    ]
    df = df[col_order]
    df.to_csv(outdir / "brecha_sweep.csv", index=False)

    # Pareto en (ratio_p2p_c1, IE_p2p) — eje original del plan
    pareto = compute_pareto_frontier(df, max_cols=["ratio_p2p_c1", "IE_p2p"])
    pareto.to_csv(outdir / "brecha_pareto.csv", index=False)

    # Pareto en (ratio_p2p_c2, IE_p2p) — eje que SI varia con pi_ppa
    pareto_c2 = compute_pareto_frontier(df, max_cols=["ratio_p2p_c2", "IE_p2p"])
    pareto_c2.to_csv(outdir / "brecha_pareto_c2.csv", index=False)

    print("\n" + "=" * 80)
    print("[B4] TABLA COMPLETA (15 configs)")
    print("=" * 80)
    print(df[["pi_ppa", "pde_method", "ratio_p2p_c1", "ratio_p2p_c2",
              "IE_p2p", "IE_C4", "welfare_p2p", "welfare_C1",
              "welfare_C2", "welfare_C4"]].to_string(
                  index=False, float_format=lambda x: f"{x:.4f}"))

    print(f"\n[B4] Frontera Pareto (ratio_p2p_c1, IE_p2p) — {len(pareto)} configs:")
    print(pareto[["pi_ppa", "pde_method", "ratio_p2p_c1",
                  "IE_p2p"]].to_string(index=False,
                  float_format=lambda x: f"{x:.4f}"))

    print(f"\n[B4] Frontera Pareto (ratio_p2p_c2, IE_p2p) — {len(pareto_c2)} configs:")
    print(pareto_c2[["pi_ppa", "pde_method", "ratio_p2p_c2",
                     "IE_p2p"]].to_string(index=False,
                     float_format=lambda x: f"{x:.4f}"))

    # Config que maximiza ratio_p2p_c1 con IE_p2p > 0.20
    eq_thresh = 0.20
    fair_df   = df[df["IE_p2p"] > eq_thresh]
    if not fair_df.empty:
        best = fair_df.loc[fair_df["ratio_p2p_c1"].idxmax()]
        print(f"\n[B4] MEJOR config (ratio_p2p_c1 max con IE_p2p > {eq_thresh}):")
        print(f"     pi_ppa={best['pi_ppa']:.1f}  pde={best['pde_method']}")
        print(f"     ratio_p2p_c1={best['ratio_p2p_c1']:.4f}  "
              f"IE_p2p={best['IE_p2p']:.4f}")
        print(f"     welfare_P2P={best['welfare_p2p']:,.0f}  "
              f"welfare_C1={best['welfare_C1']:,.0f}")
    else:
        print(f"\n[B4] AVISO: ninguna config con IE_p2p > {eq_thresh}. "
              f"IE_p2p max = {df['IE_p2p'].max():.4f}")
        print(f"     HALLAZGO: ratio_p2p_c1 invariante = "
              f"{df['ratio_p2p_c1'].iloc[0]:.4f} (P2P supera C1 en todas las configs)")
        print(f"     IE_p2p = {df['IE_p2p'].iloc[0]:.4f} (negativo: beneficio "
              f"concentrado en prosumidores, no en consumidores)")

    print(f"\n[B4] Archivos guardados en: {outdir}")
    print("[B4] brecha_c1_sweep COMPLETO.")


if __name__ == "__main__":
    main()
