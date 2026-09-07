"""
¿El precio se negocia o se pega a las cotas? Las dos vías, enfrentadas.

El MATLAB de Chacón integra **todo el sistema junto**, precios y cantidades
a la vez, con `ode15s` sobre un estado combinado. La traducción de
producción, en cambio, **alterna**: resuelve las cantidades dadas las cotas,
luego los precios dadas las cantidades, y repite. La alternancia es una
aproximación nuestra, no está en el modelo base.

Esta sonda corre las dos vías sobre el mismo caso y mira **dónde cae el
precio**: en una cota o dentro de la banda.

Se corre primero sobre el caso base de Chacón, que es donde la comparación
es limpia porque no hay ninguna decisión nuestra de por medio.

Uso:
    python alternado_vs_acoplado.py
    python alternado_vs_acoplado.py --horas 24
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))

from core.coupled_ode_convergence import solve_coupled_for_hour  # noqa: E402
from core.ems_p2p import AgentParams, GridParams, SolverParams  # noqa: E402
from core.market_prep import classify_agents, compute_generation_limit  # noqa: E402
from core.replicator_buyers import solve_buyers  # noqa: E402
from core.replicator_sellers import solve_sellers  # noqa: E402
from data.base_case_data import (get_agent_params,  # noqa: E402
                                 get_demand_profiles,
                                 get_generation_profiles)


def _donde(pi, gb, gs, tol=1e-6) -> str:
    if abs(pi - gb) < tol:
        return "piso"
    if abs(pi - gs) < tol:
        return "techo"
    return "dentro"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horas", type=int, default=24)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    p = get_agent_params()
    ag = AgentParams(**p)
    gr = GridParams()
    G = get_generation_profiles()
    D = get_demand_profiles()
    gs, gb = gr.pi_gs, gr.pi_gb
    medio = 0.5 * (gs + gb)

    # Los parametros del MATLAB, no los de produccion con dato real:
    # t_span [0, 0.01] y 500 puntos, tau 0.001 y tau3 0.01.
    sv = SolverParams(tau=0.001, tau_buyers=0.01, t_span=(0.0, 0.01),
                      n_points=500, stackelberg_iters=2, parallel=False)

    print("El precio del acuerdo: alternado frente a acoplado")
    print(f"  caso base de Chacón · banda [{gb:.0f}, {gs:.0f}] · "
          f"punto medio {medio:.0f}")
    print("=" * 76)
    print(f"  {'h':>3s} {'J':>2s} {'I':>2s}  {'alternado':>34s}  "
          f"{'acoplado':>34s}")

    cuenta = {"alternado": [0, 0, 0], "acoplado": [0, 0, 0]}
    clases = ["piso", "techo", "dentro"]

    for k in range(min(args.horas, D.shape[1])):
        g_klim = compute_generation_limit(G[:, k], ag.a, ag.b, ag.c, gs)
        _, sids, bids = classify_agents(g_klim, D[:, k])
        J, I = len(sids), len(bids)
        if J == 0 or I == 0:
            continue

        G_net = np.array([g_klim[j] - D[j, k] for j in sids])
        D_net = np.array([D[i, k] - g_klim[i] for i in bids])
        a_j, b_j = ag.a[sids], ag.b[sids]

        # ── vía de producción: alternancia ────────────────────────────
        P = (np.tile(D_net / J, (J, 1)) if np.sum(G_net) >= np.sum(D_net)
             else np.tile(G_net / I, (I, 1)).T)
        P = np.clip(P, 1e-10, None)
        pi_alt = np.full(I, gb)
        for _ in range(sv.stackelberg_iters):
            P = solve_sellers(pi_alt, G_net, D_net, a_j, b_j, tau=sv.tau,
                              t_span=sv.t_span, n_points=sv.n_points,
                              method=sv.ode_method)
            pi_alt = solve_buyers(P, a_j, b_j, ag.etha[bids],
                                  pi_gs=gs, pi_gb=gb, tau=sv.tau_buyers,
                                  t_span=sv.t_span, n_points=sv.n_points)
            pi_alt = np.clip(pi_alt, gb, gs)

        # ── vía del modelo base: un solo sistema acoplado ─────────────
        tr = solve_coupled_for_hour(
            G_net_j=G_net, D_net_i=D_net, a_j=a_j, b_j=b_j,
            lam_j=ag.lam[sids], theta_j=ag.theta[sids],
            G_klim_i=g_klim[bids], lam_i=ag.lam[bids],
            theta_i=ag.theta[bids], etha_i=ag.etha[bids],
            pi_gs=gs, pi_gb=gb, tau_sellers=sv.tau,
            tau_buyers=sv.tau_buyers, t_span=sv.t_span,
            n_points=sv.n_points)
        pi_aco = np.clip(tr.pi_star, gb, gs)

        for nombre, pi in (("alternado", pi_alt), ("acoplado", pi_aco)):
            for x in pi:
                cuenta[nombre][clases.index(_donde(x, gb, gs))] += 1

        if k < 12:
            f_alt = " ".join(f"{x:8.2f}" for x in pi_alt)
            f_aco = " ".join(f"{x:8.2f}" for x in pi_aco)
            print(f"  {k:3d} {J:2d} {I:2d}  {f_alt:>34s}  {f_aco:>34s}")

    print("\n  Dónde cae el precio, sobre todas las horas")
    print(f"  {'vía':12s} {'en el piso':>12s} {'en el techo':>12s} "
          f"{'DENTRO':>10s}")
    for nombre in ("alternado", "acoplado"):
        piso, techo, dentro = cuenta[nombre]
        tot = piso + techo + dentro
        print(f"  {nombre:12s} {100*piso/tot:11.1f} % {100*techo/tot:11.1f} % "
              f"{100*dentro/tot:9.1f} %")

    print("\n  El MATLAB de Chacón integra el sistema ACOPLADO con ode15s;")
    print("  la alternancia es una aproximación de la traducción.")


if __name__ == "__main__":
    main()
