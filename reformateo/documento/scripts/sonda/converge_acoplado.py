"""
¿Converge el sistema acoplado, y a un precio interior?

El autor necesita precios negociados, es decir un equilibrio dentro de la
banda y no en sus esquinas. Antes de cambiar nada en producción hay que
responder dos preguntas, y en este orden:

  1. ¿El sistema acoplado **llega a un estado estacionario** dentro del
     horizonte de integración del modelo base? Un precio interior que
     todavía se mueve no es un acuerdo, es una foto a medio camino.
  2. Si converge, ¿a cuánto, y cuánto cuesta?

Se mide sobre una sola hora del caso base, con los parámetros del MATLAB, y
se mira **la cola de la trayectoria**: cuánto se mueve el precio en el
último décimo del horizonte comparado con el recorrido total.

Uso:
    python converge_acoplado.py --hora 14
    python converge_acoplado.py --hora 22 --horizonte 0.05
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))

from core.coupled_ode_convergence import solve_coupled_for_hour  # noqa: E402
from core.ems_p2p import AgentParams, GridParams  # noqa: E402
from core.market_prep import classify_agents, compute_generation_limit  # noqa: E402
from data.base_case_data import (get_agent_params,  # noqa: E402
                                 get_demand_profiles,
                                 get_generation_profiles)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hora", type=int, default=14)
    ap.add_argument("--horizonte", type=float, nargs="*",
                    default=[0.01, 0.05, 0.2])
    ap.add_argument("--puntos", type=int, default=500)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    p = get_agent_params()
    ag = AgentParams(**p)
    gr = GridParams()
    G, D = get_generation_profiles(), get_demand_profiles()
    gs, gb = gr.pi_gs, gr.pi_gb
    k = args.hora

    g_klim = compute_generation_limit(G[:, k], ag.a, ag.b, ag.c, gs)
    _, sids, bids = classify_agents(g_klim, D[:, k])
    J, I = len(sids), len(bids)
    G_net = np.array([g_klim[j] - D[j, k] for j in sids])
    D_net = np.array([D[i, k] - g_klim[i] for i in bids])

    print(f"¿Converge el acoplado? · caso base, hora {k} · "
          f"{J} vendedores, {I} compradores")
    print(f"  banda [{gb:.0f}, {gs:.0f}] · punto medio {(gs+gb)/2:.0f}")
    print("=" * 78)
    print(f"  {'horizonte':>10s} {'seg':>6s}  {'precios finales':<34s} "
          f"{'cola/recorrido':>14s} {'interior':>9s}")

    for t_fin in args.horizonte:
        t0 = time.time()
        tr = solve_coupled_for_hour(
            G_net_j=G_net, D_net_i=D_net,
            a_j=ag.a[sids], b_j=ag.b[sids],
            lam_j=ag.lam[sids], theta_j=ag.theta[sids],
            G_klim_i=g_klim[bids], lam_i=ag.lam[bids],
            theta_i=ag.theta[bids], etha_i=ag.etha[bids],
            pi_gs=gs, pi_gb=gb, tau_sellers=0.001, tau_buyers=0.01,
            t_span=(0.0, t_fin), n_points=args.puntos)
        dur = time.time() - t0

        pi = np.clip(tr.pi_star, gb, gs)
        traj = tr.pi_t                       # (I, n_t)
        n = traj.shape[1]
        cola = int(max(1, n // 10))
        # Cuánto se mueve el precio en el último décimo, frente a todo su
        # recorrido: si la razón tiende a cero, ha llegado a un estacionario.
        mov_cola = float(np.max(np.abs(traj[:, -1] - traj[:, -cola])))
        recorrido = float(np.max(np.abs(traj.max(axis=1) - traj.min(axis=1))))
        razon = mov_cola / recorrido if recorrido > 1e-12 else 0.0
        dentro = sum(1 for x in pi
                     if abs(x - gb) > 1e-6 and abs(x - gs) > 1e-6)
        fila = " ".join(f"{x:8.2f}" for x in pi)
        print(f"  {t_fin:10.3f} {dur:6.1f}  {fila:<34s} "
              f"{razon:13.1%} {dentro:d} de {len(pi):d}")

    print("\n  La columna «cola/recorrido» es cuánto se mueve el precio en el")
    print("  último décimo del horizonte frente a todo su recorrido. Cerca de")
    print("  cero significa que llegó a un estacionario; alta, que sigue en")
    print("  movimiento y el valor final no es un equilibrio.")


if __name__ == "__main__":
    main()
