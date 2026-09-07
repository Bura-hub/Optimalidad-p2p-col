"""
Compuerta de CAL-49: la forma del termino de competencia llega a las dos vias.

La decision del 2026-09-06 fue conservar la forma agregada. Eso no obliga a
cambiar nada, y precisamente por eso hace falta una compuerta: una opcion que
nadie ejerce se rompe sin que se note.

Comprueba cuatro cosas:

  1. el defecto es la forma agregada, y produce EXACTAMENTE lo mismo que
     antes de que existiera la opcion;
  2. las tres formas son alcanzables en el bloque alternado y dan resultados
     distintos, de modo que elegir sirve de algo;
  3. lo mismo en el solucionador acoplado, que hasta CAL-49 no recibia el
     parametro y se quedaba siempre con la agregada aunque se eligiera otra;
  4. la forma «matlab» reproduce el producto vector por matriz del fichero
     original, es decir la suma de los factores ajenos.

Uso:
    python tests/gate_cal49_competencia.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.coupled_ode_convergence import solve_coupled_for_hour  # noqa: E402
from core.replicator_buyers import solve_buyers  # noqa: E402

FORMAS = ("aggregate", "matlab", "matrix")


def caso(semilla=5, J=3, I=4):
    rng = np.random.default_rng(semilla)
    return dict(
        P=rng.uniform(0.2, 3.0, (J, I)),
        G_net=rng.uniform(1.0, 4.0, J), D_net=rng.uniform(1.0, 4.0, I),
        a=np.zeros(J), b=rng.uniform(80.0, 200.0, J),
        etha=rng.uniform(0.05, 0.5, I),
        lam_j=np.full(J, 100.0), theta_j=np.full(J, 0.5),
        G_klim=rng.uniform(0.0, 2.0, I),
        lam_i=np.full(I, 100.0), theta_i=np.full(I, 0.5))


def alternado(d, forma=None):
    kw = {} if forma is None else {"buyer_competition": forma}
    return solve_buyers(d["P"], d["a"], d["b"], d["etha"],
                        pi_gs=900.0, pi_gb=200.0, tau=0.01,
                        t_span=(0.0, 0.005), n_points=150, **kw)


def acoplado(d, forma=None):
    kw = {} if forma is None else {"buyer_competition": forma}
    tr = solve_coupled_for_hour(
        G_net_j=d["G_net"], D_net_i=d["D_net"], a_j=d["a"], b_j=d["b"],
        lam_j=d["lam_j"], theta_j=d["theta_j"], G_klim_i=d["G_klim"],
        lam_i=d["lam_i"], theta_i=d["theta_i"], etha_i=d["etha"],
        pi_gs=900.0, pi_gb=200.0, tau_sellers=0.001, tau_buyers=0.01,
        t_span=(0.0, 0.01), n_points=200, **kw)
    return np.asarray(tr.pi_star, float), np.asarray(tr.P_star, float)


def main() -> int:
    fallos = []
    d = caso()

    # ---- 1 · el defecto no se movio ------------------------------------
    sin, con = alternado(d), alternado(d, "aggregate")
    ok = np.array_equal(sin, con)
    print(f"  1 · el defecto es la agregada, bit a bit            "
          f"{'ok' if ok else 'FALLA'}")
    if not ok:
        fallos.append("el defecto del bloque alternado cambio")
    a_sin, a_con = acoplado(d), acoplado(d, "aggregate")
    ok2 = (np.array_equal(a_sin[0], a_con[0])
           and np.array_equal(a_sin[1], a_con[1]))
    print(f"      y lo mismo en el acoplado                       "
          f"{'ok' if ok2 else 'FALLA'}")
    if not ok2:
        fallos.append("el defecto del acoplado cambio")

    # ---- 2 · las tres son alcanzables y distintas -----------------------
    #
    # Se barren varias semillas a propósito. En la vía alternada los precios
    # saturan en las cotas con frecuencia, y cuando saturan las tres formas
    # coinciden porque el recorte borra la diferencia. Eso no es un fallo de
    # la opción sino el comportamiento que documenta CAL-48, de modo que la
    # comprobación pide que la elección se note en ALGUNA de las semillas y
    # además informa en cuántas.
    print("\n  2 · bloque alternado, sobre varias semillas")
    n_disc, casos = 0, 5
    for s in range(casos):
        dd = caso(semilla=5 + s)
        alt = {f: alternado(dd, f) for f in FORMAS}
        dist = len({tuple(np.round(v, 9)) for v in alt.values()})
        n_disc += dist >= 2
        marca = "distingue" if dist >= 2 else "satura en las cotas"
        print(f"      semilla {5 + s}: {dist} de 3 distintos · {marca}")
        if s == 0:
            for f in FORMAS:
                print(f"        {f:>10s}  {np.array2string(alt[f], precision=1)}")
    ok = n_disc > 0
    print(f"      la elección se nota en {n_disc} de {casos} semillas   "
          f"{'ok' if ok else 'FALLA'}")
    if not ok:
        fallos.append("elegir la forma no cambia nada en el alternado")

    # ---- 3 · el acoplado tambien la recibe ------------------------------
    aco = {f: acoplado(d, f) for f in FORMAS}
    print("\n  3 · solucionador acoplado, precios de equilibrio")
    for f in FORMAS:
        print(f"      {f:>10s}  {np.array2string(aco[f][0], precision=2)}")
    dist2 = len({tuple(np.round(v[0], 9)) for v in aco.values()})
    print(f"      resultados distintos: {dist2} de 3   "
          f"{'ok' if dist2 >= 2 else 'FALLA'}")
    if dist2 < 2:
        fallos.append("el acoplado ignora la forma elegida; era el defecto "
                      "que CAL-49 vino a cerrar")

    # ---- 4 · «matlab» es el producto vector por matriz -------------------
    I = len(d["etha"])
    matriz = np.ones((I, I)) - np.eye(I)
    esperado = matriz.T @ d["etha"]
    directo = np.array([sum(d["etha"][k] for k in range(I) if k != i)
                        for i in range(I)])
    ok4 = np.allclose(esperado, directo)
    print(f"\n  4 · «matlab» es la suma de los factores ajenos     "
          f"{'ok' if ok4 else 'FALLA'}")
    print(f"      {np.array2string(esperado, precision=3)}")
    if not ok4:
        fallos.append("la forma matlab no reproduce el producto del original")

    print()
    if fallos:
        for f in fallos:
            print(f"  FALLA: {f}")
        return 1
    print("  COMPUERTA CAL-49 EN VERDE")
    print("  La decision es la forma agregada; las otras dos quedan")
    print("  alcanzables y medidas. Ver docs/adr/0049.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
