"""
La forma del termino de competencia, medida sobre los datos reales.

La forma publicada, la ecuacion (11) del articulo arbitrado, es la unica que
reproduce los resultados del propio articulo. Pero en el caso publicado sus
precios cayeron pegados a las cotas, que es justo el defecto que la via
acoplada venia a corregir. Antes de adoptarla hay que medir si eso pasa
tambien con los datos del proyecto, o si era cosa de aquel caso.

Se comparan las dos formas sobre las mismas horas, y se mira:

  - donde cae cada precio DENTRO de su banda, en tanto por ciento;
  - cuantos precios quedan pegados a una cota, con el uno por ciento de
    la banda como criterio;
  - cuanto del ahorro alcanzable se captura, que es la medida propia;
  - el volumen, que no deberia moverse;
  - como se reparte el excedente entre quien vende y quien compra.

Uso:
    python competencia_real.py --cobertura m1 --muestra 20
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

from core.coupled_ode_convergence import solve_coupled_for_hour  # noqa: E402
from core.market_prep import classify_agents, compute_generation_limit  # noqa: E402
from eficiencia import excedente, optimo_centralizado  # noqa: E402

PEGADO = 0.01     # a menos del uno por ciento de la banda se cuenta pegado


def una_hora(dat, k, forma):
    from data.xm_prices import get_b_for_real_data

    D, G = dat["D"], dat["G"]
    N = D.shape[0]
    a = np.zeros(N); c = np.zeros(N)
    b = get_b_for_real_data(N, dat["nombres"])
    lam = np.full(N, 100.0); theta = np.full(N, 0.5); etha = np.full(N, 0.1)

    g = compute_generation_limit(G[:, k], a, b, c, dat["techo"][:, k])
    _, sids, bids = classify_agents(g, D[:, k])
    if not sids or not bids:
        return None
    G_net = np.array([g[j] - D[j, k] for j in sids])
    D_net = np.array([D[i, k] - g[i] for i in bids])
    techo_i = dat["techo"][bids, k]
    piso_j = dat["piso"][sids, k]
    piso_h = float(np.min(piso_j)); gs_esc = float(np.max(techo_i))
    if gs_esc - piso_h < 1e-9:
        return None

    tr = solve_coupled_for_hour(
        G_net_j=G_net, D_net_i=D_net, a_j=a[sids], b_j=b[sids],
        lam_j=lam[sids], theta_j=theta[sids], G_klim_i=g[bids],
        lam_i=lam[bids], theta_i=theta[bids], etha_i=etha[bids],
        pi_gs=gs_esc, pi_gb=piso_h, tau_sellers=0.001, tau_buyers=0.01,
        t_span=(0.0, 0.05), n_points=500, buyer_competition=forma)
    P = np.asarray(tr.P_star, float)
    pi = np.clip(np.asarray(tr.pi_star, float), piso_h, techo_i)

    # posicion del precio dentro de la banda de SU comprador
    pos = (pi - piso_h) / np.maximum(techo_i - piso_h, 1e-12)
    pegados = int(np.sum((pos <= PEGADO) | (pos >= 1.0 - PEGADO)))

    cen = optimo_centralizado(G_net, D_net, techo_i, piso_j)
    ef = (100.0 * excedente(P, techo_i, piso_j) / cen["excedente"]
          if cen and cen["excedente"] > 1e-9 else np.nan)

    # reparto entre quien vende y quien compra
    prima = float(sum((pi[q] - piso_j[m]) * P[m, q]
                      for m in range(len(sids)) for q in range(len(bids))))
    ahorro = float(sum((techo_i[q] - pi[q]) * P[m, q]
                       for m in range(len(sids)) for q in range(len(bids))))
    tot = prima + ahorro
    return dict(k=int(k), J=len(sids), I=len(bids), forma=forma,
                pos_media=100.0 * float(np.mean(pos)),
                pos_min=100.0 * float(np.min(pos)),
                pos_max=100.0 * float(np.max(pos)),
                pegados=pegados, n_precios=len(pi),
                eficiencia=ef, volumen=float(P.sum()),
                tajada_vendedor=100.0 * prima / tot if tot > 1e-9 else np.nan)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=20)
    ap.add_argument("--cobertura", default="m1", choices=["m1", "m3"])
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    from paso_a_paso import carga
    dat = carga(args.cobertura)
    D, G = dat["D"], dat["G"]
    vende = (np.maximum(G - D, 0.0) > 1e-9).any(axis=0)
    compra = (np.maximum(D - G, 0.0) > 1e-9).any(axis=0)
    cand = np.flatnonzero(vende & compra)
    # misma semilla que la sonda de eficiencia, para hablar de las mismas horas
    rng = np.random.default_rng(42)
    sel = np.sort(rng.choice(cand, size=min(args.muestra, len(cand)),
                             replace=False))

    print(f"La forma del término de competencia · {args.cobertura.upper()} · "
          f"{len(sel)} horas", flush=True)
    print("  «posición» es dónde cae el precio dentro de su banda: "
          "0 % es el piso y 100 % el techo", flush=True)
    print("=" * 78, flush=True)
    print(f"  {'hora':>6s} {'forma':>10s} {'pos media':>10s} "
          f"{'pegados':>9s} {'eficiencia':>11s} {'volumen':>9s} "
          f"{'vendedor':>9s}", flush=True)

    import pandas as pd
    sal = Path(__file__).parent / "salidas"; sal.mkdir(exist_ok=True)
    filas = []
    for k in sel:
        for forma in ("aggregate", "matrix"):
            r = una_hora(dat, int(k), forma)
            if r is None:
                continue
            filas.append(r)
            print(f"  {r['k']:6d} {forma:>10s} {r['pos_media']:9.1f} % "
                  f"{r['pegados']:4d}/{r['n_precios']:<4d} "
                  f"{r['eficiencia']:10.1f} % {r['volumen']:9.3f} "
                  f"{r['tajada_vendedor']:8.1f} %", flush=True)
            pd.DataFrame(filas).to_csv(
                sal / f"competencia_{args.cobertura}.csv", index=False)

    if not filas:
        print("  ninguna hora resuelta"); return
    d = pd.DataFrame(filas)
    print("\n  " + "-" * 74)
    for forma in ("aggregate", "matrix"):
        s = d[d.forma == forma]
        if s.empty:
            continue
        peg = 100.0 * s["pegados"].sum() / s["n_precios"].sum()
        print(f"  {forma:>10s}: posición media {s['pos_media'].mean():5.1f} % · "
              f"precios pegados a una cota {peg:5.1f} % · "
              f"eficiencia {s['eficiencia'].mean():5.1f} % · "
              f"tajada del vendedor {s['tajada_vendedor'].mean():5.1f} %")
    va = d[d.forma == "aggregate"].set_index("k")["volumen"]
    vm = d[d.forma == "matrix"].set_index("k")["volumen"]
    comun = va.index.intersection(vm.index)
    print(f"\n  el volumen no se mueve: máxima diferencia "
          f"{float((va[comun] - vm[comun]).abs().max()):.2e} kWh")
    print(f"  detalle en salidas/competencia_{args.cobertura}.csv")


if __name__ == "__main__":
    main()
