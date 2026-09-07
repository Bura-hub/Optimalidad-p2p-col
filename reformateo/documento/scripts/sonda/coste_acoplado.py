"""
Que fraccion del mercado converge a cada horizonte pagable.

El primer intento midio con parada adaptativa, doblando el horizonte hasta
converger, y resulto inviable: sobre 36 horas reales las diez primeras
resolvieron en 16 segundos, las diez siguientes en 499, las diez siguientes
en 1.432, y las seis ultimas no acabaron en 3.500. El coste no esta
repartido, esta concentrado en unas pocas horas rebeldes.

De modo que la pregunta util no es cuanto cuesta converger sino **que
horizonte se puede pagar y que fraccion converge ahi**. Esta sonda integra
el sistema acoplado a horizontes fijos y, para cada uno, reporta:

  - que fraccion de las horas llega a un estacionario
  - cuanto cuesta
  - cuantos precios quedan DENTRO de la banda, que es lo que motiva el
    cambio, frente a los que da el lazo alternado de produccion

Uso:
    python coste_acoplado.py --muestra 24
    python coste_acoplado.py --muestra 24 --horizontes 0.01 0.05 0.1
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))

TOL_COLA = 0.01     # 1 % de movimiento en la cola se acepta como estacionario


def _prepara(G_k, D_k, a, b, c, gs):
    from core.market_prep import classify_agents, compute_generation_limit
    g_klim = compute_generation_limit(G_k, a, b, c, gs)
    _, sids, bids = classify_agents(g_klim, D_k)
    return g_klim, sids, bids


def _alternado(args):
    """La via de produccion, para tener la referencia de cada hora."""
    import numpy as np
    from core.replicator_buyers import solve_buyers
    from core.replicator_sellers import solve_sellers
    (k, G_k, D_k, a, b, c, lam, theta, etha, gs, gb) = args
    g_klim, sids, bids = _prepara(G_k, D_k, a, b, c, gs)
    J, I = len(sids), len(bids)
    if J == 0 or I == 0:
        return None
    G_net = np.array([g_klim[j] - D_k[j] for j in sids])
    D_net = np.array([D_k[i] - g_klim[i] for i in bids])
    a_j, b_j = a[sids], b[sids]
    P = (np.tile(D_net / J, (J, 1)) if np.sum(G_net) >= np.sum(D_net)
         else np.tile(G_net / I, (I, 1)).T)
    P = np.clip(P, 1e-10, None)
    pi = np.full(I, gb)
    for _ in range(2):
        P = solve_sellers(pi, G_net, D_net, a_j, b_j, tau=0.001,
                          t_span=(0.0, 0.005), n_points=150, method="LSODA")
        pi = np.clip(solve_buyers(P, a_j, b_j, etha[bids], pi_gs=gs,
                                  pi_gb=gb, tau=0.01, t_span=(0.0, 0.005),
                                  n_points=150), gb, gs)
    dentro = int(sum(1 for x in pi
                     if abs(x - gb) > 1e-6 and abs(x - gs) > 1e-6))
    return {"hora": k, "I": I, "J": J, "dentro_alt": dentro}


def _acoplado(args):
    """La via del modelo base, a un horizonte fijo."""
    import numpy as np
    from core.coupled_ode_convergence import solve_coupled_for_hour
    (k, G_k, D_k, a, b, c, lam, theta, etha, gs, gb, t_fin) = args
    g_klim, sids, bids = _prepara(G_k, D_k, a, b, c, gs)
    J, I = len(sids), len(bids)
    if J == 0 or I == 0:
        return None
    G_net = np.array([g_klim[j] - D_k[j] for j in sids])
    D_net = np.array([D_k[i] - g_klim[i] for i in bids])

    t0 = time.time()
    try:
        tr = solve_coupled_for_hour(
            G_net_j=G_net, D_net_i=D_net, a_j=a[sids], b_j=b[sids],
            lam_j=lam[sids], theta_j=theta[sids],
            G_klim_i=g_klim[bids], lam_i=lam[bids],
            theta_i=theta[bids], etha_i=etha[bids],
            pi_gs=gs, pi_gb=gb, tau_sellers=0.001, tau_buyers=0.01,
            t_span=(0.0, t_fin), n_points=500)
    except Exception as exc:
        return {"hora": k, "I": I, "horizonte": t_fin, "converge": False,
                "segundos": time.time() - t0, "razon_cola": np.nan,
                "dentro_aco": 0, "fallo": str(exc)[:40]}

    traj = tr.pi_t
    n = traj.shape[1]
    exito = bool(getattr(tr, "success", True))
    cola = int(max(1, n // 10))
    mov = float(np.max(np.abs(traj[:, -1] - traj[:, -cola])))
    rec = float(np.max(np.abs(traj.max(axis=1) - traj.min(axis=1))))
    razon = mov / rec if rec > 1e-12 else 0.0
    pi = np.clip(tr.pi_star, gb, gs)
    return {
        "hora": k, "I": I, "horizonte": t_fin,
        "exito": exito,
        "converge": bool(razon <= TOL_COLA),
        "segundos": time.time() - t0, "razon_cola": razon,
        "dentro_aco": int(sum(1 for x in pi
                              if abs(x - gb) > 1e-6 and abs(x - gs) > 1e-6)),
        "fallo": "",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=24)
    ap.add_argument("--cobertura", default="m1", choices=["m1", "m3"])
    ap.add_argument("--procesos", type=int, default=6)
    ap.add_argument("--horizontes", type=float, nargs="*",
                    default=[0.01, 0.05, 0.1])
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    from data.base_case_data import GRID_PARAMS_REAL
    from data.cedenar_tariff import community_effective_pi_gs
    from data.preprocessing import PAPER_METER_DEMAND_CONFIG
    from data.xm_data_loader import MTEDataLoader
    from data.xm_prices import get_b_for_real_data

    cfg = PAPER_METER_DEMAND_CONFIG if args.cobertura == "m3" else None
    loader = MTEDataLoader(os.environ.get("MTE_ROOT",
                                          str(RAIZ / "MedicionesMTE_v3")),
                           demand_config=cfg)
    D, G, idx = loader.load(verbose=False)
    N = D.shape[0]
    nombres = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"][:N]
    a = np.zeros(N); c = np.zeros(N)
    b = get_b_for_real_data(N, nombres)
    lam = np.full(N, 100.0); theta = np.full(N, 0.5); etha = np.full(N, 0.1)
    gs = community_effective_pi_gs(nombres, idx[0],
                                   idx[-1] + pd.Timedelta(hours=1),
                                   weights=D.mean(axis=1))
    gb = float(GRID_PARAMS_REAL["pi_gb"])

    vende = (np.maximum(G - D, 0.0) > 1e-9).any(axis=0)
    compra = (np.maximum(D - G, 0.0) > 1e-9).any(axis=0)
    cand = np.flatnonzero(vende & compra)
    rng = np.random.default_rng(42)
    sel = np.sort(rng.choice(cand, size=min(args.muestra, len(cand)),
                             replace=False))

    print(f"Coste por horizonte · {args.cobertura.upper()} · {len(sel)} horas "
          f"de {len(cand)} con mercado posible", flush=True)
    print(f"  banda [{gb:.2f}, {gs:.2f}] · estacionario = cola por debajo "
          f"del {100*TOL_COLA:.0f} %", flush=True)
    print("=" * 78, flush=True)

    base = [(int(k), G[:, k].copy(), D[:, k].copy(), a, b, c,
             lam, theta, etha, gs, gb) for k in sel]

    with ProcessPoolExecutor(max_workers=args.procesos) as ex:
        alt = [r for r in ex.map(_alternado, base) if r]
    d_alt = pd.DataFrame(alt).set_index("hora")
    tot_precios = int(d_alt.I.sum())
    print(f"\n  Referencia, el lazo alternado de producción:")
    print(f"    {int(d_alt.dentro_alt.sum())} de {tot_precios} precios dentro "
          f"de la banda ({100*d_alt.dentro_alt.sum()/tot_precios:.1f} %)",
          flush=True)

    print(f"\n  {'horizonte':>10s} {'converge':>10s} {'seg/hora med':>13s} "
          f"{'seg/hora max':>13s} {'precios dentro':>16s} "
          f"{'corrida 11 proc':>16s}", flush=True)

    filas = []
    for t_fin in args.horizontes:
        trabajos = [tuple(list(x) + [t_fin]) for x in base]
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=args.procesos) as ex:
            res = [r for r in ex.map(_acoplado, trabajos) if r]
        d = pd.DataFrame(res)
        horas_totales = len(cand) * d.segundos.mean() / 3600.0
        if "exito" in d:
            print(f"    integrador con exito en {100*d.exito.mean():.1f} % "
                  f"de las horas", flush=True)
            dd = d[d.exito]
            if len(dd) and len(dd) < len(d):
                print(f"    solo con las exitosas: dentro "
                      f"{100*dd.dentro_aco.sum()/max(1,int(dd.I.sum())):.1f} %",
                      flush=True)
        print(f"  {t_fin:10.3f} {100*d.converge.mean():9.1f} % "
              f"{d.segundos.median():13.1f} {d.segundos.max():13.1f} "
              f"{100*d.dentro_aco.sum()/tot_precios:15.1f} % "
              f"{horas_totales/11:15.1f} h", flush=True)
        d["muro_s"] = time.time() - t0
        filas.append(d)

    sal = Path(__file__).parent / "salidas"
    sal.mkdir(exist_ok=True)
    pd.concat(filas).to_csv(
        sal / f"coste_acoplado_{args.cobertura}.csv", index=False)
    print(f"\n  detalle en salidas/coste_acoplado_{args.cobertura}.csv")


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
