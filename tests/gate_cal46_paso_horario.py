# -*- coding: utf-8 -*-
"""Compuerta de CAL-46: el camino horario tiene que dar exactamente lo mismo.

La sonda de quince minutos exige hacer explicito el factor de duracion del
paso, y ese factor toca la liquidacion, los cinco escenarios y la serie de
bolsa. La condicion que el registro de la decision impone es que **con paso
horario el resultado no se mueva ni un bit**. Si esta compuerta no pasa, la
sonda no sigue.

No compara contra el canon en disco: compara la corrida de hoy contra la
corrida del mismo codigo antes del cambio. Se usa asi:

    git stash                                   # vuelve a HEAD
    python tests/gate_cal46_paso_horario.py --escribe antes.json
    git stash pop                               # vuelve al arbol de trabajo
    python tests/gate_cal46_paso_horario.py --compara antes.json

La huella recoge todo numero que la comparacion produce, con `repr` de
precision completa, de modo que una diferencia en el ultimo bit se ve.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams  # noqa: E402
from core.settlement import residual_settlement, compute_savings  # noqa: E402
from data.base_case_data import (  # noqa: E402
    get_demand_profiles, get_generation_profiles)
from data.xm_prices import apply_creg101066_ceiling  # noqa: E402
from scenarios import run_comparison  # noqa: E402


def _plano(obj, prefijo="", salida=None):
    """Aplana cualquier estructura a {ruta: repr del numero}."""
    salida = {} if salida is None else salida
    if isinstance(obj, dict):
        for k in sorted(obj, key=str):
            _plano(obj[k], f"{prefijo}.{k}", salida)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _plano(v, f"{prefijo}[{i}]", salida)
    elif isinstance(obj, np.ndarray):
        for i, v in enumerate(obj.reshape(-1)):
            salida[f"{prefijo}[{i}]"] = repr(float(v))
    elif isinstance(obj, (int, float, np.integer, np.floating)):
        salida[prefijo] = repr(float(obj))
    elif isinstance(obj, (bool, np.bool_)):
        salida[prefijo] = repr(bool(obj))
    return salida


def huella() -> dict:
    """Corre el caso sintetico entero y devuelve su huella numerica."""
    D = np.asarray(get_demand_profiles(), float)
    G = np.asarray(get_generation_profiles(), float)
    N, T = D.shape

    rng = np.random.default_rng(20260905)
    pi_bolsa = 180.0 + 40.0 * rng.random(T)
    pi_gs = np.full((N, T), 797.0)
    pi_gb = 182.0

    agentes = AgentParams(
        N=N, alpha=np.zeros(N), a=np.full(N, 0.01), b=np.full(N, 225.0),
        c=np.zeros(N), lam=np.full(N, 100.0), theta=np.full(N, 0.5),
        etha=np.full(N, 0.1),
    )
    red = GridParams(pi_gs=797.0, pi_gb=pi_gb)
    solver = SolverParams(tau=0.001, t_span=(0.0, 0.005), n_points=150,
                          stackelberg_iters=2, parallel=False)
    p2p, G_klim, _ = EMSP2P(agentes, red, solver).run(D, G)

    prosumidores = [n for n in range(N) if G[n].sum() > 0]
    consumidores = [n for n in range(N) if n not in prosumidores]
    pde = np.full(N, 1.0 / N)
    # Dos meses para que la reliquidacion mensual de C4 tambien entre.
    meses = np.array([202507 if k < T // 2 else 202508 for k in range(T)])

    cr = run_comparison(
        D=D, G_klim=G_klim, G_raw=G, p2p_results=p2p,
        pi_gs=pi_gs, pi_gb=pi_gb, pi_bolsa=pi_bolsa,
        prosumer_ids=prosumidores, consumer_ids=consumidores,
        pde=pde, pi_ppa=400.0, capacity=np.full(N, 50.0),
        month_labels=meses, tolls=120.0,
        g_component=300.0, cvm_component=60.0, cot_component=20.0,
        mem_costs=10.0, include_c5=True,
        pi_escasez=np.full(T, 900.0),
    )

    h = {}
    for campo in ("net_benefit", "net_benefit_per_agent", "equity_index",
                  "gini", "self_sufficiency", "self_consumption",
                  "flow_breakdown", "rpe", "ps_p2p", "psr_p2p",
                  "W_sellers_total", "W_buyers_total", "static_spread_24h"):
        _plano(getattr(cr, campo), f"cr.{campo}", h)
    if cr.fairness is not None:
        _plano(cr.fairness.__dict__, "cr.fairness", h)

    # Liquidacion residual y ahorros, llamados a pelo.
    r0 = p2p[0]
    if r0.P_star is not None and r0.seller_ids and r0.buyer_ids:
        liq = residual_settlement(
            r0.P_star, G_klim[r0.seller_ids, 0], D[r0.buyer_ids, 0],
            G_klim[:, 0], D[:, 0], 797.0, pi_gb,
            r0.seller_ids, r0.buyer_ids,
        )
        _plano(liq, "liquidacion", h)
        _plano(compute_savings(r0.P_star, r0.pi_star, 797.0, pi_gb),
               "ahorros", h)

    # Techo de escasez sobre la serie horaria.
    techo, diag = apply_creg101066_ceiling(
        pi_bolsa, "2025-07-01", return_diagnostics=True)
    _plano(techo, "techo.serie", h)
    _plano({k: v for k, v in diag.items() if k != "by_month"}, "techo.diag", h)

    # Huella del propio motor, hora a hora.
    for k, r in enumerate(p2p):
        for campo in ("SC", "SS", "IE", "PS", "PSR", "Wj_total", "Wi_total",
                      "iters_used", "norm_rel_final"):
            _plano(getattr(r, campo), f"p2p[{k}].{campo}", h)
        if r.P_star is not None:
            _plano(r.P_star, f"p2p[{k}].P_star", h)
            _plano(r.pi_star, f"p2p[{k}].pi_star", h)

    return h


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--escribe")
    ap.add_argument("--compara")
    args = ap.parse_args()

    h = huella()
    print(f"huella con {len(h)} numeros")

    if args.escribe:
        Path(args.escribe).write_text(
            json.dumps(h, indent=0, sort_keys=True), encoding="utf-8")
        print(f"escrita en {args.escribe}")
        return 0

    if args.compara:
        antes = json.loads(Path(args.compara).read_text(encoding="utf-8"))
        faltan = sorted(set(antes) - set(h))
        sobran = sorted(set(h) - set(antes))
        distintas = sorted(k for k in set(antes) & set(h) if antes[k] != h[k])
        if faltan or sobran or distintas:
            print(f"\nCOMPUERTA CAL-46 FALLA")
            for etiqueta, xs in (("solo antes", faltan), ("solo ahora", sobran),
                                 ("distintas", distintas)):
                if xs:
                    print(f"  {etiqueta}: {len(xs)}")
                    for k in xs[:12]:
                        print(f"    {k}: {antes.get(k)} -> {h.get(k)}")
            return 1
        print(f"\nCAMINO HORARIO IDENTICO ({len(h)} numeros, bit a bit)")
        return 0

    print("nada que hacer: use --escribe o --compara")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
