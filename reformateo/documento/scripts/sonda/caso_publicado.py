"""
El caso publicado del modelo base, reproducido con sus propios datos.

Hasta hoy el caso del modelo base NO era reproducible: el codigo en MATLAB
carga un libro de calculo que no esta en el repositorio, y los perfiles del
proyecto son una reconstruccion sintetica hecha a mano.

La version arbitrada del modelo, publicada en *IEEE Latin America
Transactions* 23(8) en agosto de 2025, **trae sus datos de entrada
completos** en dos tablas, de modo que el caso se puede armar exactamente y
enfrentar contra lo que el articulo afirma de el.

QUE SE PUEDE COMPROBAR, Y QUE NO
--------------------------------
El resultado del mercado depende de la generacion, la demanda, los
coeficientes de costo, las dos cotas y el factor de competencia. De esos, el
articulo publica los cuatro primeros y declara el quinto en 1. Las cotas no
las da en numeros, y se toman las del modelo base, 114 y 1250.

Los factores de preferencia lambda y theta **no afectan al resultado**,
porque la utilidad de autoconsumo no depende de lo transado; solo desplazan
el nivel del bienestar que se reporta. Por eso su ausencia no impide la
comprobacion.

Uso:
    python caso_publicado.py
    python caso_publicado.py --beta6 100
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

# ── Tabla II · parametros de costo ───────────────────────────────────────
# El articulo advierte que los factores c son constantes y no entran en la
# optimizacion. El agente 6 es consumidor puro y no tiene generacion.
A_PUB = np.array([0.089, 0.110, 0.069, 0.000, 0.000, 0.000])
B_PUB = np.array([52.0, 58.0, 40.0, 37.0, 32.0, 0.0])
C_PUB = np.zeros(6)

# ── Tabla III · demanda y generacion (kWh) ───────────────────────────────
D_PUB = {13: np.array([1.24, 0.46, 0.12, 3.17, 0.06, 1.03]),
         19: np.array([3.34, 0.68, 0.25, 1.06, 0.07, 0.66])}
G_PUB = {13: np.array([2.00, 2.60, 0.89, 0.30, 0.61, 0.00]),
         19: np.array([2.00, 1.58, 0.49, 0.48, 0.96, 0.00])}

# Cotas del modelo base. El articulo arbitrado no las da en numeros.
PI_GB, PI_GS = 114.0, 1250.0

# Lo que el articulo afirma de cada escenario, para enfrentarlo
AFIRMA = {
    13: ["vendedores 1, 2, 3 y 5; compradores 4 y 6",
         "toda la demanda de la comunidad se suple dentro de ella",
         "los generadores 1, 3 y 5 se despachan a su maxima capacidad",
         "el generador 2, el mas costoso, queda con exceso de capacidad",
         "el comprador 4, el de mayor demanda, paga el precio mas alto",
         "la recompensa de cada vendedor supera sus costos"],
    19: ["vendedores 2, 3 y 5; compradores 1, 4 y 6",
         "todos los vendedores se despachan en su totalidad",
         "el comprador 1 cubre toda su demanda dentro de la comunidad",
         "los compradores 4 y 6 NO la cubren y recurren a la red",
         "la recompensa de cada vendedor supera sus costos"],
}


def _n(x, dec=3):
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


COMPETENCIA = "aggregate"   # lo cambia main() segun el argumento


def resuelve(t: int, beta: np.ndarray):
    D, G = D_PUB[t], G_PUB[t]
    g = compute_generation_limit(G, A_PUB, B_PUB, C_PUB,
                                 np.full(6, PI_GS))
    # la clasificacion del articulo se hace sobre la razon entre generacion y
    # demanda tal como se publican, antes del limite economico
    gdr = np.divide(G, D, out=np.zeros(6), where=D > 0)
    _, sids, bids = classify_agents(g, D)
    G_net = np.array([g[j] - D[j] for j in sids])
    D_net = np.array([D[i] - g[i] for i in bids])
    tr = solve_coupled_for_hour(
        G_net_j=G_net, D_net_i=D_net, a_j=A_PUB[sids], b_j=B_PUB[sids],
        lam_j=np.full(len(sids), 100.0), theta_j=np.full(len(sids), 0.5),
        G_klim_i=g[bids], lam_i=np.full(len(bids), 100.0),
        theta_i=np.full(len(bids), 0.5), etha_i=beta[bids],
        pi_gs=PI_GS, pi_gb=PI_GB, tau_sellers=0.001, tau_buyers=0.01,
        t_span=(0.0, 0.05), n_points=500,
        buyer_competition=COMPETENCIA)
    P = np.asarray(tr.P_star, float)
    pi = np.clip(np.asarray(tr.pi_star, float), PI_GB, PI_GS)
    return dict(t=t, D=D, G=G, g=g, gdr=gdr, sids=sids, bids=bids,
                G_net=G_net, D_net=D_net, P=P, pi=pi)


def informa(r, beta) -> list:
    t, sids, bids, P, pi = r["t"], r["sids"], r["bids"], r["P"], r["pi"]
    print(f"\n{'='*72}\n  ESCENARIO t = {t}:00\n{'='*72}")
    print(f"  {'agente':>8s} {'D':>7s} {'G':>7s} {'G/D':>7s} "
          f"{'G lim':>7s} {'papel':>10s} {'neto':>8s}")
    for n in range(6):
        papel = ("vende" if n in sids else "compra" if n in bids else "-")
        neto = (r["g"][n] - r["D"][n])
        print(f"  {n+1:>8d} {r['D'][n]:7.2f} {r['G'][n]:7.2f} "
              f"{r['gdr'][n]:7.2f} {r['g'][n]:7.3f} {papel:>10s} {neto:8.3f}")

    print(f"\n  Flujos (kWh) y precios (unidades)")
    print(f"  {'':>10s}" + "".join(f"{'c'+str(i+1):>9s}" for i in bids)
          + f"{'total':>9s}{'tiene':>9s}")
    for m, j in enumerate(sids):
        print(f"  {'v'+str(j+1):>10s}"
              + "".join(f"{P[m, q]:9.3f}" for q in range(len(bids)))
              + f"{P[m].sum():9.3f}{r['G_net'][m]:9.3f}")
    print(f"  {'total':>10s}"
          + "".join(f"{P[:, q].sum():9.3f}" for q in range(len(bids)))
          + f"{P.sum():9.3f}")
    print(f"  {'necesita':>10s}"
          + "".join(f"{r['D_net'][q]:9.3f}" for q in range(len(bids))))
    print(f"  {'precio':>10s}"
          + "".join(f"{pi[q]:9.2f}" for q in range(len(bids))))

    # ── contraste con lo que el articulo afirma ──────────────────────────
    print(f"\n  Contraste con lo que afirma el articulo")
    ver = []
    if t == 13:
        ver.append(("vendedores 1, 2, 3 y 5; compradores 4 y 6",
                    sorted(sids) == [0, 1, 2, 4] and sorted(bids) == [3, 5]))
        ver.append(("toda la demanda de la comunidad se suple dentro",
                    bool(np.all(P.sum(axis=0) >= r["D_net"] - 1e-6))))
        holg = {j: r["G_net"][m] - P[m].sum() for m, j in enumerate(sids)}
        ver.append(("los generadores 1, 3 y 5 se despachan al maximo",
                    all(abs(holg.get(j, 1)) < 1e-3 for j in (0, 2, 4))))
        ver.append(("el generador 2 queda con exceso de capacidad",
                    holg.get(1, 0.0) > 1e-3))
        i4 = list(bids).index(3) if 3 in bids else None
        i6 = list(bids).index(5) if 5 in bids else None
        ver.append(("el comprador 4 paga el precio mas alto",
                    i4 is not None and i6 is not None and pi[i4] > pi[i6]))
    else:
        ver.append(("vendedores 2, 3 y 5; compradores 1, 4 y 6",
                    sorted(sids) == [1, 2, 4] and sorted(bids) == [0, 3, 5]))
        ver.append(("todos los vendedores se despachan en su totalidad",
                    bool(np.all(np.abs(P.sum(axis=1) - r["G_net"]) < 1e-3))))
        if 0 in bids:
            q = list(bids).index(0)
            ver.append(("el comprador 1 cubre toda su demanda dentro",
                        abs(P[:, q].sum() - r["D_net"][q]) < 1e-3))
        for ag in (3, 5):
            if ag in bids:
                q = list(bids).index(ag)
                ver.append((f"el comprador {ag+1} NO la cubre",
                            P[:, q].sum() < r["D_net"][q] - 1e-3))
    # recompensa contra costos, comun a los dos escenarios
    ok_rec = True
    for m, j in enumerate(sids):
        rec = float(np.sum(pi * P[m]))
        cos = A_PUB[j] * P[m].sum()**2 + B_PUB[j] * P[m].sum()
        ok_rec &= rec >= cos - 1e-9
    ver.append(("la recompensa de cada vendedor supera sus costos", ok_rec))

    for texto, ok in ver:
        print(f"    [{'si' if ok else 'NO':>2s}] {texto}")
    return ver


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--competencia", default="aggregate",
                    choices=("aggregate", "matlab", "matrix"),
                    help="forma del termino de competencia; «matrix» es la "
                         "ecuacion (11) publicada")
    ap.add_argument("--beta6", type=float, default=None,
                    help="factor de competencia del agente 6 (el articulo "
                         "lo sube de 1 a 100 y mide el efecto)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    global COMPETENCIA
    COMPETENCIA = args.competencia

    print("El caso publicado del modelo base, con sus propios datos")
    print("IEEE Latin America Transactions 23(8), agosto de 2025, tablas II y III")
    print(f"cotas {PI_GB:.0f} y {PI_GS:.0f} · factor de competencia 1 en todos")
    print(f"termino de competencia: «{COMPETENCIA}»")

    beta = np.ones(6)
    todos = []
    for t in (13, 19):
        todos += informa(resuelve(t, beta), beta)

    if args.beta6 is not None:
        print(f"\n{'='*72}\n  SENSIBILIDAD · el agente 6 pasa de 1 a "
              f"{args.beta6:.0f}\n{'='*72}")
        r1 = resuelve(19, beta)
        b2 = beta.copy(); b2[5] = args.beta6
        r2 = resuelve(19, b2)
        q1 = list(r1["bids"]).index(5); q2 = list(r2["bids"]).index(5)
        d = r2["pi"][q2] - r1["pi"][q1]
        print(f"  precio del agente 6: {r1['pi'][q1]:.2f} -> "
              f"{r2['pi'][q2]:.2f}   sube {_n(d, 2)}")
        print(f"  el articulo publica una subida de 25,22")
        e6a = float(r1["P"][:, q1].sum()); e6b = float(r2["P"][:, q2].sum())
        print(f"  energia del agente 6: {_n(e6a)} -> {_n(e6b)} kWh")

    n_ok = sum(1 for _, ok in todos if ok)
    print(f"\n{'='*72}")
    print(f"  {n_ok} de {len(todos)} afirmaciones del articulo se reproducen")


if __name__ == "__main__":
    main()
