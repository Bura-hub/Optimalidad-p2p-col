"""
Compuerta de C-146: el techo por agente llega AL JUEGO, no solo a la liquidación.

Hasta el 2026-09-07 la asimetría era esta: la liquidación recibía la matriz
del costo unitario por agente y hora, y el juego recibía un único escalar
comunitario. Como el ahorro de un comprador es su techo menos el precio, y
el precio se resolvía contra un techo ajeno, los compradores del techo más
bajo salían con ahorro exactamente cero. Medido: 109 de 200 horas de la
frontera principal tenían al menos uno.

Lo que esta compuerta exige:

  1. Sin la matriz, el resultado es IDENTICO BIT A BIT al histórico. Es la
     condición para que el cambio sea una generalización estricta y para que
     el caso sintético y el modelo base no se muevan.
  2. Una matriz constante con el valor del escalar da exactamente lo mismo
     que el escalar.
  3. Con techos distintos por agente, el precio de cada comprador respeta EL
     SUYO y no el mayor de la hora.
  4. Con techos distintos, ningún comprador queda pegado a su techo con
     ahorro nulo, que es el defecto que motiva el cambio. Se exige SOBRE LA
     VIA ACOPLADA, y esa precisión importa: la alternada deja el precio
     pegado a una cota por razones ajenas a esto, que son las de H-38. La
     corrida canónica va por la alternada, de modo que **no hereda esta
     propiedad**, y así hay que declararlo.
  5. La matriz se valida: una forma que no corresponde al problema se
     rechaza en vez de deformarse en silencio.

Uso:
    python tests/gate_c146_techo_en_el_juego.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.ems_p2p import AgentParams, EMSP2P, GridParams, SolverParams  # noqa: E402
from core.settlement import compute_savings  # noqa: E402

N, T = 5, 6
ESCALAR = 906.27
PISO = 280.0


def caso(semilla: int = 3):
    """Un caso pequeño con vendedores y compradores en todas las horas."""
    rng = np.random.default_rng(semilla)
    D = rng.uniform(1.0, 5.0, (N, T))
    G = np.zeros((N, T))
    G[:2, :] = rng.uniform(4.0, 9.0, (2, T))      # dos con excedente claro
    G[2:, :] = rng.uniform(0.0, 0.6, (N - 2, T))
    return D, G


def corre(D, G, techo_agente=None, pi_gs=ESCALAR, metodo="alternado"):
    """Resuelve el caso. `metodo` importa y no es un detalle.

    La vía ALTERNADA deja el precio pegado a una cota en la mayoría de los
    casos, y eso es H-38, no un defecto de C-146. De modo que la propiedad
    de que ningún comprador quede con ahorro nulo solo se puede exigir sobre
    la vía ACOPLADA, que es donde se midió sobre 400 horas.
    """
    agents = AgentParams(N=N, a=np.zeros(N),
                         b=np.full(N, 150.0), c=np.zeros(N),
                         lam=np.full(N, 100.0), theta=np.full(N, 0.5),
                         etha=np.full(N, 0.1))
    grid = GridParams(pi_gs=pi_gs, pi_gb=PISO, pi_gs_agente=techo_agente)
    solver = SolverParams(tau=0.001, t_span=(0.0, 0.005), n_points=120,
                          stackelberg_iters=2, parallel=False,
                          metodo=metodo, t_span_acoplado=0.02)
    res, G_klim, D_star = EMSP2P(agents, grid, solver).run(D, G)
    P = np.array([r.P_star if r.P_star is not None else np.zeros((1, 1))
                  for r in res], dtype=object)
    pi = [None if r.pi_star is None else np.asarray(r.pi_star, float)
          for r in res]
    return res, pi, G_klim


def main() -> int:
    fallos: list[str] = []
    D, G = caso()
    print()
    print("  Compuerta C-146 · el techo por agente en el juego")
    print("  " + "=" * 58)

    # ── 1 y 2 · sin matriz, y con matriz constante ──────────────────────
    r0, pi0, gk0 = corre(D, G)
    r1, pi1, gk1 = corre(D, G, np.full((N, T), ESCALAR))
    ok = np.array_equal(gk0, gk1) and all(
        (a is None and b is None) or np.array_equal(a, b)
        for a, b in zip(pi0, pi1))
    if ok:
        for x, y in zip(r0, r1):
            if (x.P_star is None) != (y.P_star is None):
                ok = False; break
            if x.P_star is not None and not np.array_equal(x.P_star, y.P_star):
                ok = False; break
    print(f"  1 · matriz constante identica al escalar             "
          f"{'ok' if ok else 'FALLA'}")
    if not ok:
        fallos.append("la matriz constante no reproduce el escalar")

    # ── 3 y 4 · con techos distintos ────────────────────────────────────
    techos = np.tile(np.array([731.1, 731.1, 731.1, 777.2, 777.2])[:, None],
                     (1, T))
    r2, pi2, gk2 = corre(D, G, techos, metodo="acoplado")

    excede, pegados, horas = 0, 0, 0
    for k, r in enumerate(r2):
        if r.P_star is None or not r.buyer_ids:
            continue
        horas += 1
        ti = techos[r.buyer_ids, k]
        p = np.asarray(r.pi_star, float)
        excede += int(np.sum(p > ti + 1e-9))
        S_i, _ = compute_savings(r.P_star, p, ti, PISO)
        comprado = r.P_star.sum(axis=0)
        pegados += int(np.sum((comprado > 1e-9) & (S_i <= 1e-6)))

    print(f"  2 · ningun precio supera SU techo, en {horas} horas        "
          f"{'ok' if excede == 0 else 'FALLA'}")
    if excede:
        fallos.append(f"{excede} precios por encima de su techo")

    print(f"  3 · ningun comprador con ahorro nulo                 "
          f"{'ok' if pegados == 0 else 'FALLA'}  ({pegados})")
    if pegados:
        fallos.append(f"{pegados} compradores con ahorro nulo")

    # ── 5 · una forma que no corresponde se rechaza ─────────────────────
    try:
        corre(D, G, np.full((N + 1, T), ESCALAR))
        rechaza = False
    except ValueError:
        rechaza = True
    print(f"  4 · rechaza una matriz de forma equivocada           "
          f"{'ok' if rechaza else 'FALLA'}")
    if not rechaza:
        fallos.append("acepta una matriz de forma equivocada")

    print()
    if fallos:
        print("  FALLA: " + "; ".join(fallos))
        return 1
    print("  todo en verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
