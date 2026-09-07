"""
Cuánto del resultado de la banda estrecha es el arranque y cuánto el mercado.

El bloque comprador arranca en `techo · I/(I+1)`, con I el número de
compradores de la hora. Viene del modelo base, donde el piso valía 114 y el
techo 1.250, de modo que ese punto siempre caía holgadamente dentro de la
banda. Con el piso de permuta la banda se estrecha a unos 175 COP/kWh y ese
arranque **nace por debajo del piso** en las horas de pocos compradores: el
código lo recorta al piso, y allí el peso que mueve la dinámica vale cero,
así que el precio queda congelado.

Esta sonda mide el tamaño del artefacto. Corre la misma hora dos veces:

    tal cual   el arranque del modelo base, `techo · I/(I+1)`
    interior   el mismo reparto pero **dentro de la banda**,
               `piso + (techo − piso) · I/(I+1)`, que recupera al modelo
               base cuando el piso es despreciable frente al techo

No toca el núcleo. Usa el parámetro de condición inicial que el propio
solucionador ya admite y que la corrida de producción no emplea.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

from core.ems_p2p import AgentParams, SolverParams  # noqa: E402
from core.market_prep import classify_agents, compute_generation_limit  # noqa: E402
from core.replicator_buyers import solve_buyers  # noqa: E402
from core.replicator_sellers import solve_sellers  # noqa: E402
from data.xm_prices import get_b_for_real_data  # noqa: E402

from banda_precios import piso_permuta, techo_mensual  # noqa: E402


def una_hora(G_klim_k, D_k, sids, bids, ag, sv, gs, gb, interior: bool):
    """Un lazo de Stackelberg con la condición inicial elegida."""
    J, I = len(sids), len(bids)
    if J == 0 or I == 0:
        return None

    a_j, b_j = ag.a[sids], ag.b[sids]
    etha_i = ag.etha[bids]
    G_net_j = np.array([G_klim_k[j] - D_k[j] for j in sids])
    D_net_i = np.array([D_k[i] - G_klim_k[i] for i in bids])

    P = (np.tile(D_net_i / J, (J, 1)) if np.sum(G_net_j) >= np.sum(D_net_i)
         else np.tile(G_net_j / I, (I, 1)).T)
    P = np.clip(P, 1e-10, None)

    # La condición inicial, que es lo único que distingue las dos corridas
    ci = (gb + (gs - gb) * I / (I + 1)) if interior else (gs * I / (I + 1))
    pi0 = np.full(I, ci)

    pi_i = np.full(I, gb)
    for _ in range(sv.stackelberg_iters):
        P = solve_sellers(pi_i, G_net_j, D_net_i, a_j, b_j, tau=sv.tau,
                          t_span=sv.t_span, n_points=sv.n_points,
                          method=sv.ode_method)
        pi_i = solve_buyers(P, a_j, b_j, etha_i, pi_gs=gs, pi_gb=gb,
                            tau=sv.tau_buyers, t_span=sv.t_span,
                            n_points=sv.n_points, pi0=pi0)
        pi_i = np.clip(pi_i, gb, gs)
    return P, pi_i, ci


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mes", default="2025-09")
    ap.add_argument("--cobertura", default="m3", choices=["m1", "m3"])
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import os
    from data.preprocessing import PAPER_METER_DEMAND_CONFIG
    from data.xm_data_loader import MTEDataLoader, slice_horizon

    cfg = PAPER_METER_DEMAND_CONFIG if args.cobertura == "m3" else None
    loader = MTEDataLoader(os.environ.get("MTE_ROOT",
                                          str(RAIZ / "MedicionesMTE_v3")),
                           demand_config=cfg)
    D_full, G_full, idx_full = loader.load(verbose=False)
    ini = pd.Timestamp(args.mes + "-01")
    fin = ini + pd.offsets.MonthBegin(1)
    D, G, _ = slice_horizon(D_full, G_full, idx_full,
                            ini.strftime("%Y-%m-%d"), fin.strftime("%Y-%m-%d"))
    N, T = D.shape
    nombres = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"][:N]

    ag = AgentParams(N=N, a=np.zeros(N), b=get_b_for_real_data(N, nombres),
                     c=np.zeros(N), lam=np.full(N, 100.0),
                     theta=np.full(N, 0.5), etha=np.full(N, 0.1))
    sv = SolverParams(tau=0.001, t_span=(0.0, 0.005), n_points=150,
                      stackelberg_iters=2, parallel=False)

    gs, gb = techo_mensual(args.mes), piso_permuta(args.mes)
    print(f"El arranque de la banda estrecha · {args.mes} · "
          f"{args.cobertura.upper()}")
    print(f"  techo {gs:.2f} · piso {gb:.2f} · ancho {gs - gb:.2f}")
    print("=" * 74)

    res = {}
    for interior in (False, True):
        filas = []
        for k in range(T):
            g_klim = compute_generation_limit(G[:, k], ag.a, ag.b, ag.c, gs)
            _, sids, bids = classify_agents(g_klim, D[:, k])
            r = una_hora(g_klim, D[:, k], sids, bids, ag, sv, gs, gb, interior)
            if r is None:
                continue
            P, pi, ci = r
            for a, i in enumerate(bids):
                for b, j in enumerate(sids):
                    q = float(P[b, a])
                    if q <= 1e-9:
                        continue
                    filas.append({"hora": k, "kWh": q, "precio": float(pi[a]),
                                  "prima": (float(pi[a]) - gb) * q,
                                  "ahorro": (gs - float(pi[a])) * q,
                                  "arranque_bajo_piso": ci <= gb})
        res["interior" if interior else "tal cual"] = pd.DataFrame(filas)

    for nombre, f in res.items():
        pv, ac = f.prima.sum(), f.ahorro.sum()
        piso = (f.precio - gb).abs() < 1e-6
        print(f"\n  {nombre:9s} {len(f):5d} flujos · {f.kWh.sum():9.1f} kWh · "
              f"precio mediano {f.precio.median():7.2f}")
        print(f"  {'':9s} en el piso {100*piso.mean():5.1f} % · "
              f"excedente {pv+ac:11,.0f} COP · reparto "
              f"{100*pv/(pv+ac) if pv+ac else 0:4.1f} vendedor / "
              f"{100*ac/(pv+ac) if pv+ac else 0:4.1f} comprador")
        if nombre == "tal cual":
            print(f"  {'':9s} flujos cuyo arranque nace bajo el piso: "
                  f"{100*f.arranque_bajo_piso.mean():.1f} %")

    a, b = res["tal cual"], res["interior"]
    ea = a.prima.sum() + a.ahorro.sum()
    eb = b.prima.sum() + b.ahorro.sum()
    print(f"\n  El artefacto vale: excedente {ea:,.0f} -> {eb:,.0f} COP "
          f"({100*(eb-ea)/ea:+.1f} %)")
    print(f"  y la tajada del vendedor pasa de "
          f"{100*a.prima.sum()/ea:.1f} % a {100*b.prima.sum()/eb:.1f} %")


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
