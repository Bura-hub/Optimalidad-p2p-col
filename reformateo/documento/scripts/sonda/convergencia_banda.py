"""
¿Le da tiempo al precio a moverse cuando la banda se estrecha?

El peso que gobierna la dinámica del precio es
`(techo − precio)·(precio − piso)`, cuyo máximo es el cuadrado de la mitad
del ancho. Al pasar del piso de hoy al de permuta la banda se estrecha 3,5
veces, de modo que **el peso cae 12,4 veces** y la dinámica se vuelve otro
tanto más lenta. Con el mismo presupuesto de integración el precio recorre
una fracción de lo que recorría, y eso podría confundirse con que el
mercado decidió quedarse donde está.

La prueba: la misma hora con presupuestos crecientes. Si el reparto no se
mueve, el presupuesto basta y las velocidades heredadas del modelo base
sirven para este régimen. Si se mueve, hay un segundo defecto y queda
cifrado.

Solo puede cambiar **el reparto**. El excedente total es el ancho de la
banda por la energía transada y no depende del precio, de modo que ninguna
de estas variantes puede moverlo.

Se corre siempre con la condición inicial corregida de H-32, porque medir
la convergencia con el arranque roto no diría nada.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

from core.ems_p2p import AgentParams, SolverParams  # noqa: E402
from core.market_prep import classify_agents, compute_generation_limit  # noqa: E402
from data.xm_prices import get_b_for_real_data  # noqa: E402

from arranque_banda import una_hora  # noqa: E402
from banda_precios import piso_permuta, techo_mensual  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mes", default="2025-09")
    ap.add_argument("--cobertura", default="m3", choices=["m1", "m3"])
    ap.add_argument("--banda", default="permuta",
                    choices=["permuta", "canon"],
                    help="permuta = la banda estrecha de CAL-47; "
                         "canon = las cotas con que se produjo el canon, "
                         "para saber si el defecto toca a lo ya publicado")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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

    if args.banda == "permuta":
        gs, gb = techo_mensual(args.mes), piso_permuta(args.mes)
    else:
        # Las cotas con que se produjo el canon: el escalar comunitario
        # ponderado por demanda y la constante heredada.
        from data.base_case_data import GRID_PARAMS_REAL
        from data.cedenar_tariff import community_effective_pi_gs
        gs = community_effective_pi_gs(
            nombres, idx_full[0], idx_full[-1] + pd.Timedelta(hours=1),
            weights=D_full.mean(axis=1))
        gb = float(GRID_PARAMS_REAL["pi_gb"])

    print(f"Convergencia con la banda «{args.banda}» · {args.mes} · "
          f"{args.cobertura.upper()}")
    print(f"  techo {gs:.2f} · piso {gb:.2f} · ancho {gs - gb:.2f}")
    print("=" * 78)

    # Cuatro presupuestos. Los tres primeros alargan el horizonte a paso
    # constante, es decir preguntan si da tiempo. El cuarto afina el paso a
    # horizonte constante, es decir pregunta si el paso es bastante fino.
    variantes = [
        ("producción", 0.005, 150, 2),
        ("horizonte ×2", 0.010, 300, 2),
        ("horizonte ×4", 0.020, 600, 2),
        ("paso ×4", 0.005, 600, 2),
        ("Stackelberg ×4", 0.005, 150, 8),
    ]

    print(f"  {'variante':16s} {'t_span':>8s} {'pasos':>6s} {'iter':>5s} "
          f"{'flujos':>7s} {'kWh':>9s} {'excedente':>12s} "
          f"{'en piso':>8s} {'vendedor':>9s}")

    for nombre, t_fin, n_pts, st in variantes:
        sv = SolverParams(tau=0.001, t_span=(0.0, t_fin), n_points=n_pts,
                          stackelberg_iters=st, parallel=False)
        filas = []
        for k in range(T):
            g_klim = compute_generation_limit(G[:, k], ag.a, ag.b, ag.c, gs)
            _, sids, bids = classify_agents(g_klim, D[:, k])
            r = una_hora(g_klim, D[:, k], sids, bids, ag, sv, gs, gb,
                         interior=True)
            if r is None:
                continue
            P, pi, _ = r
            for a, i in enumerate(bids):
                for b, j in enumerate(sids):
                    q = float(P[b, a])
                    if q > 1e-9:
                        filas.append({"kWh": q, "precio": float(pi[a])})
        f = pd.DataFrame(filas)
        prima = ((f.precio - gb) * f.kWh).sum()
        exc = (gs - gb) * f.kWh.sum()
        piso = ((f.precio - gb).abs() < 1e-6).mean()
        print(f"  {nombre:16s} {t_fin:8.3f} {n_pts:6d} {st:5d} "
              f"{len(f):7d} {f.kWh.sum():9.2f} {exc:12,.0f} "
              f"{100*piso:7.1f} % {100*prima/exc:8.1f} %")

    print("\n  Si la columna del vendedor no se mueve, el presupuesto basta y")
    print("  las velocidades heredadas sirven para este régimen.")


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
