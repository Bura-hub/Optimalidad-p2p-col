"""
run_s8_pde_sensitivity.py — Sensibilidad S8: PDE uniforme vs proxy en C4.

Actividad 2.2 / 4.1 · Pregunta 6 de la auditoría (Capa 2.6, Informe 4 BPIN).

Contexto: el Informe 4 (Fajardo, 2026-05-27, p. 4) confirma placas FV
idénticas (17.55 kWp × 5 = 87.75 kWp). Con capacidad de placa idéntica,
el PDE "proporcional a capacidad" de la CREG 101 072 art. 19 es UNIFORME
(1/5 = 0.2). El default actual de `run_comparison` usa como proxy la
generación media observada (`compute_pde_weights(mean(G_raw))`,
`comparison_engine.py:162-164`), que difiere del uniforme en la medida en
que los rendimientos reales difieren (sombras, clipeo Udenar, M1×0.3
Mariana en M3).

Este script corre el escenario C4 dos veces — PDE proxy vs PDE uniforme —
replicando EXACTAMENTE la preparación de datos de `main_simulation.py`
en modo `--data real --full` (pi_gs matriz CAL-9, Cvm literal CAL-10b.2,
bolsa horaria con techo PES CAL-14, G_klim del Algoritmo 1), SIN correr
el juego P2P (C4 no lo necesita; G_klim es forma cerrada).

NO toca el paper (`run_paper_iter.py` no usa este script ni el default).

Uso (local, ~1-2 min; el costo es la carga de CSVs):
  python scripts/run_s8_pde_sensitivity.py                 # M1 totalizador
  python scripts/run_s8_pde_sensitivity.py --paper-meters  # M3 sub-medidores

Salida: tabla per-agente + agregado + Gini, y CSV en
  outputs/s8_pde_sensitivity_<M1|M3>.csv
"""
import sys, os, argparse, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")

import numpy as np
import pandas as pd

from core.market_prep import compute_generation_limit
from core.settlement import gini_index
from data.base_case_data import GRID_PARAMS_REAL
from data.xm_prices import get_pi_bolsa, get_b_for_real_data
from data.cedenar_tariff import (
    community_effective_pi_gs, cvm_per_agent_hourly, pi_gs_per_agent_hourly,
)
from data.xm_data_loader import MTEDataLoader
from scenarios.scenario_c4_creg101072 import (
    run_c4_creg101072, compute_pde_weights,
)

AGENT_NAMES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_inputs(paper_meters: bool):
    """Replica la preparación de main_simulation.py (--data real --full)."""
    mte_root = os.environ.get("MTE_ROOT",
                              os.path.join(ROOT, "MedicionesMTE_v3"))
    demand_cfg = None
    if paper_meters:
        from data.preprocessing import PAPER_METER_DEMAND_CONFIG
        demand_cfg = PAPER_METER_DEMAND_CONFIG
    loader = MTEDataLoader(mte_root, demand_config=demand_cfg)
    D, G, index_full = loader.load(verbose=False)
    N, T = D.shape
    names = AGENT_NAMES[:N]

    # pi_gs matriz (N, T) mes a mes — CAL-9
    pi_gs_v = pi_gs_per_agent_hourly(names, index_full)

    # Bolsa horaria alineada por fecha (CAL-17) con techo PES (CAL-14)
    xm_csv = os.path.join(ROOT, "data", "xm_precios_bolsa.csv")
    pi_bolsa = get_pi_bolsa(
        T,
        t_start=index_full[0].strftime("%Y-%m-%d"),
        t_end=(index_full[-1] + pd.Timedelta(hours=1)).strftime("%Y-%m-%d"),
        csv_path=xm_csv if os.path.exists(xm_csv) else None,
        scenario="2025_normal",
    )

    # Cvm literal — CAL-10b.2
    component_c = cvm_per_agent_hourly(names, index_full)

    # G_klim — Algoritmo 1 pasos 1-14, mismos parámetros que main
    # (a=0, c=0 CAL-32; b calibrado Act 1.2; pi_gs escalar comunitario).
    t0 = index_full[0]
    t1 = index_full[-1] + pd.Timedelta(hours=1)
    pi_gs_eff = community_effective_pi_gs(names, t0, t1,
                                          weights=D.mean(axis=1))
    b_cal = get_b_for_real_data(N, names)
    a = np.zeros(N); c = np.zeros(N)
    G_klim = np.zeros((N, T))
    for k in range(T):
        G_klim[:, k] = compute_generation_limit(G[:, k], a, b_cal, c,
                                                pi_gs_eff)

    cap = np.maximum(G.mean(axis=1), 0)   # mismo `cap` que main:90
    return D, G, G_klim, pi_gs_v, pi_bolsa, component_c, cap, names


def _run_c4(D, G_klim, pi_gs_v, pi_bolsa, pde, cap, component_c):
    r = run_c4_creg101072(D, G_klim, pi_gs_v, pi_bolsa, pde, cap,
                          component_c=component_c)
    N = D.shape[0]
    per = np.array([r["per_agent"][n]["net_benefit"] for n in range(N)])
    return r, per


def main():
    ap = argparse.ArgumentParser(description="Sensibilidad S8 PDE de C4")
    ap.add_argument("--paper-meters", action="store_true",
                    help="Escenario M3 sub-medidores (CAL-36)")
    args = ap.parse_args()
    tag = "M3" if args.paper_meters else "M1"

    print(f"\n=== S8 — Sensibilidad PDE de C4 (uniforme vs proxy) · {tag} ===")
    D, G, G_klim, pi_gs_v, pi_bolsa, component_c, cap, names = \
        _load_inputs(args.paper_meters)
    N, T = D.shape
    print(f"    N={N}  T={T}h  cobertura PV={G.sum()/D.sum():.3f}")

    # Variante A — proxy actual (default de run_comparison): gen. media
    pde_proxy = compute_pde_weights(cap)                 # capacity_proportional
    # Variante B — uniforme (placas idénticas 17.55 kWp, Informe 4 p. 4)
    pde_unif = compute_pde_weights(np.zeros(N), method="equal")

    rA, perA = _run_c4(D, G_klim, pi_gs_v, pi_bolsa, pde_proxy, cap,
                       component_c)
    rB, perB = _run_c4(D, G_klim, pi_gs_v, pi_bolsa, pde_unif, cap,
                       component_c)

    print(f"\n    PDE proxy (gen. media): "
          + "  ".join(f"{names[n]}={pde_proxy[n]:.3f}" for n in range(N)))
    print(f"    PDE uniforme          : "
          + "  ".join(f"{names[n]}={pde_unif[n]:.3f}" for n in range(N)))

    print(f"\n    {'Institución':<10} {'C4 proxy':>14} {'C4 uniforme':>14} "
          f"{'Δ (COP)':>13} {'Δ%':>7}")
    print("    " + "-" * 64)
    rows = []
    for n in range(N):
        d = perB[n] - perA[n]
        dp = 100.0 * d / perA[n] if abs(perA[n]) > 1e-9 else float("nan")
        print(f"    {names[n]:<10} {perA[n]:>14,.0f} {perB[n]:>14,.0f} "
              f"{d:>13,.0f} {dp:>6.2f}%")
        rows.append({"agente": names[n], "pde_proxy": pde_proxy[n],
                     "pde_uniforme": pde_unif[n],
                     "c4_proxy_cop": perA[n], "c4_uniforme_cop": perB[n],
                     "delta_cop": d, "delta_pct": dp})

    totA, totB = perA.sum(), perB.sum()
    giniA, giniB = gini_index(perA), gini_index(perB)
    print("    " + "-" * 64)
    print(f"    {'TOTAL':<10} {totA:>14,.0f} {totB:>14,.0f} "
          f"{totB - totA:>13,.0f} {100*(totB-totA)/totA:>6.3f}%")
    print(f"    Gini per-agente: proxy={giniA:.4f}  uniforme={giniB:.4f}")

    out = os.path.join(ROOT, "outputs", f"s8_pde_sensitivity_{tag}.csv")
    df = pd.DataFrame(rows)
    df.loc[len(df)] = {"agente": "TOTAL", "pde_proxy": 1.0,
                       "pde_uniforme": 1.0, "c4_proxy_cop": totA,
                       "c4_uniforme_cop": totB, "delta_cop": totB - totA,
                       "delta_pct": 100*(totB-totA)/totA}
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"\n    CSV → {out}")
    print(f"    Lectura: el agregado apenas se mueve (la permuta Tipo 1 y el "
          f"residual Tipo 2\n    redistribuyen el MISMO pool de excedentes); "
          f"el efecto es per-agente.")


if __name__ == "__main__":
    main()
