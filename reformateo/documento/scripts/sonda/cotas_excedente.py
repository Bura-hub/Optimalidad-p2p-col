"""
El excedente no tiene solo un techo: tambien tiene un piso.

`eficiencia.py` mide contra el mejor reparto posible, y en las horas de un
solo vendedor el mercado se queda en el 54 %. Ese numero, solo, se lee mal.
Le falta la otra cota.

El mejor reparto es el de un planificador que puede **dejar sin nada** a los
compradores de techo bajo y darselo todo al de techo alto. Ningun mecanismo
que atienda a todos va a igualarlo, y el del proyecto atiende a todos por
construccion: la dinamica del replicador reparte. De modo que la pregunta
util no es cuanto le falta al mercado para el dictador, sino **donde cae
entre el mejor y el peor reparto** del mismo volumen, que es la misma forma
en que el proyecto lee el precio acordado dentro de su banda.

Esta sonda calcula las dos cotas por hora. Es barata: dos programas lineales
y ningun integrador, de modo que corre en segundos sobre las mismas horas
que la sonda cara, y sus resultados se cruzan por el numero de hora.

Uso:
    python cotas_excedente.py --cobertura m1 --muestra 30
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

from eficiencia import optimo_centralizado  # noqa: E402


def peor_reparto(G_net, D_net, techo_i, piso_j, volumen):
    """El reparto de menor excedente que aun mueve el mismo volumen.

    Es la otra cota: un planificador que emparejara al reves. Se fija el
    volumen con una igualdad para comparar peras con peras, porque de otro
    modo el minimo trivial es no transar nada.
    """
    J, I = len(G_net), len(D_net)
    val = np.array([[techo_i[i] - piso_j[j] for i in range(I)]
                    for j in range(J)]).ravel()
    A, b = [], []
    for j in range(J):
        fila = np.zeros(J * I); fila[j * I:(j + 1) * I] = 1.0
        A.append(fila); b.append(G_net[j])
    for i in range(I):
        fila = np.zeros(J * I); fila[i::I] = 1.0
        A.append(fila); b.append(D_net[i])
    r = linprog(val, A_ub=np.array(A), b_ub=np.array(b),
                A_eq=np.ones((1, J * I)), b_eq=[volumen],
                bounds=[(0, None)] * (J * I), method="highs")
    return float(r.fun) if r.success else None


def reparto_ciego(G_net, D_net):
    """Reparto proporcional, sin mirar precios ni bandas.

    Es la referencia que de verdad decide si el juego aporta algo: mueve
    exactamente el mismo volumen que el optimo, el lado corto, y reparte a
    prorrata. Un mecanismo que no lo supere no esta emparejando, esta
    repartiendo.
    """
    J, I = len(G_net), len(D_net)
    sg, sd = float(np.sum(G_net)), float(np.sum(D_net))
    if sg >= sd:                       # sobra oferta: cada comprador se llena
        return np.outer(G_net / sg, D_net)
    return np.outer(G_net, D_net / sd)  # falta oferta: cada vendedor se vacia


def prepara(dat, k):
    """Los datos de una hora, sin resolver el juego."""
    from core.market_prep import classify_agents, compute_generation_limit

    D, G = dat["D"], dat["G"]
    N = D.shape[0]
    if dat.get("modo") == "base":
        from data.base_case_data import get_agent_params
        p = get_agent_params()
        a, b, c = p["a"].copy(), p["b"].copy(), p["c"].copy()
    else:
        from data.xm_prices import get_b_for_real_data
        a = np.zeros(N); c = np.zeros(N)
        b = get_b_for_real_data(N, dat["nombres"])

    g = compute_generation_limit(G[:, k], a, b, c, dat["techo"][:, k])
    _, sids, bids = classify_agents(g, D[:, k])
    if not sids or not bids:
        return None
    return (np.array([g[j] - D[j, k] for j in sids]),
            np.array([D[i, k] - g[i] for i in bids]),
            dat["techo"][bids, k], dat["piso"][sids, k])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=30)
    ap.add_argument("--cobertura", default="m1", choices=["m1", "m3"])
    ap.add_argument("--base", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    from paso_a_paso import carga, carga_base
    dat = carga_base() if args.base else carga(args.cobertura)
    D, G = dat["D"], dat["G"]
    vende = (np.maximum(G - D, 0.0) > 1e-9).any(axis=0)
    compra = (np.maximum(D - G, 0.0) > 1e-9).any(axis=0)
    cand = np.flatnonzero(vende & compra)
    # la misma semilla y el mismo tamaño que la sonda cara, para que las
    # dos hablen de las mismas horas
    rng = np.random.default_rng(42)
    sel = np.sort(rng.choice(cand, size=min(args.muestra, len(cand)),
                             replace=False))

    etiqueta = "caso base de Chacón" if args.base else args.cobertura.upper()
    print(f"Las dos cotas del excedente · {etiqueta} · {len(sel)} horas")
    print("  el mejor reparto puede dejar compradores sin nada; el peor "
          "mueve lo mismo y vale menos")
    print("=" * 78)
    print(f"  {'hora':>6s} {'J':>2s} {'I':>2s} {'mejor COP':>11s} "
          f"{'peor COP':>10s} {'ancho %':>9s} {'ciego':>9s}")

    from eficiencia import excedente
    filas = []
    for k in sel:
        pre = prepara(dat, int(k))
        if pre is None:
            continue
        G_net, D_net, techo_i, piso_j = pre
        cen = optimo_centralizado(G_net, D_net, techo_i, piso_j)
        if cen is None or cen["excedente"] <= 1e-9:
            continue
        peor = peor_reparto(G_net, D_net, techo_i, piso_j, cen["volumen"])
        if peor is None:
            continue
        ancho = 100.0 * (cen["excedente"] - peor) / cen["excedente"]
        ciego = 100.0 * excedente(reparto_ciego(G_net, D_net),
                                  techo_i, piso_j) / cen["excedente"]
        filas.append(dict(k=int(k), J=len(G_net), I=len(D_net),
                          mejor=cen["excedente"], peor=peor,
                          volumen=cen["volumen"], ancho_pct=ancho,
                          ef_ciego=ciego))
        print(f"  {k:6d} {len(G_net):2d} {len(D_net):2d} "
              f"{cen['excedente']:11.1f} {peor:10.1f} "
              f"{ancho:8.1f} % {ciego:7.1f} %")

    if not filas:
        print("  ninguna hora con excedente alcanzable")
        return
    an = np.array([f["ancho_pct"] for f in filas])
    ci = np.array([f["ef_ciego"] for f in filas])
    print("\n  " + "-" * 74)
    print(f"  el peor reparto vale entre el {100 - an.max():.1f} % y el "
          f"{100 - an.min():.1f} % del mejor")
    print(f"  margen que el emparejamiento puede decidir: media "
          f"{an.mean():.1f} % · mediana {np.median(an):.1f} %")
    print(f"  horas sin margen alguno: {int((an < 1e-9).sum())} de {len(filas)}")
    print(f"  el reparto ciego captura: media {ci.mean():.1f} % · mediana "
          f"{np.median(ci):.1f} % · mínimo {ci.min():.1f} %")

    import pandas as pd
    sal = Path(__file__).parent / "salidas"
    sal.mkdir(exist_ok=True)
    suf = "base" if args.base else args.cobertura
    pd.DataFrame(filas).to_csv(sal / f"cotas_{suf}.csv", index=False)
    print(f"\n  detalle en salidas/cotas_{suf}.csv")


if __name__ == "__main__":
    main()
