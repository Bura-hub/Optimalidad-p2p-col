"""
Compuerta de H-46: el peso del jugador virtual es una opcion, y esta apagada.

En el fichero original el peso con que cada estrategia entra en la aptitud
media se arma en dos piezas: producto de barrera para los compradores
reales, y **su propio precio** para el jugador virtual. Esta traduccion le
aplica la barrera tambien a el.

La opcion existe para poder medir la diferencia antes de decidir. Como una
opcion que nadie ejerce se rompe sin que se note, hace falta una compuerta.

Lo que exige:

  1. El defecto es "barrera", y produce EXACTAMENTE lo mismo que antes de
     que la opcion existiera, es decir que omitir el parametro y pasarlo
     explicitamente coinciden bit a bit.
  2. La forma "precio" es alcanzable y da un resultado DISTINTO, de modo que
     elegir sirve de algo.
  3. Un valor desconocido se rechaza en vez de caer en silencio en el
     defecto, que es como una opcion deja de existir sin avisar.
  4. El volumen NO cambia entre las dos formas. Es lo esperable por H-33 y
     D-7, y si algun dia deja de cumplirse, eso es un hallazgo.

Uso:
    python tests/gate_h46_peso_virtual.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.coupled_ode_convergence import solve_coupled_for_hour  # noqa: E402

SEMILLAS = (5, 11, 23)


def caso(semilla: int = 5, J: int = 3, I: int = 4) -> dict:
    rng = np.random.default_rng(semilla)
    return dict(
        G_net_j=rng.uniform(1.0, 4.0, J), D_net_i=rng.uniform(1.0, 4.0, I),
        a_j=np.zeros(J), b_j=rng.uniform(80.0, 200.0, J),
        etha_i=rng.uniform(0.05, 0.5, I),
        lam_j=np.full(J, 100.0), theta_j=np.full(J, 0.5),
        G_klim_i=rng.uniform(0.0, 2.0, I),
        lam_i=np.full(I, 100.0), theta_i=np.full(I, 0.5))


def corre(d: dict, **kw):
    tr = solve_coupled_for_hour(
        **d, pi_gs=906.27, pi_gb=280.0, tau_sellers=0.001, tau_buyers=0.01,
        t_span=(0.0, 0.005), n_points=150, **kw)
    return np.asarray(tr.pi_star, float), np.asarray(tr.P_star, float)


def main() -> int:
    fallos: list[str] = []
    print()
    print("  Compuerta H-46 · el peso del jugador virtual")
    print("  " + "=" * 58)

    # ── 1 · el defecto no se movio ──────────────────────────────────────
    malos = [s for s in SEMILLAS
             if not all(np.array_equal(a, b) for a, b in
                        zip(corre(caso(s)), corre(caso(s),
                                                  peso_virtual="barrera")))]
    print(f"  1 · el defecto es «barrera», bit a bit          "
          f"{'ok' if not malos else 'FALLA'}")
    fallos += [f"defecto semilla {s}" for s in malos]

    # ── 2 · la otra forma es alcanzable y distinta ──────────────────────
    distingue, volumen_igual = 0, []
    for s in SEMILLAS:
        pb, Pb = corre(caso(s), peso_virtual="barrera")
        pp, Pp = corre(caso(s), peso_virtual="precio")
        if not np.array_equal(pb, pp):
            distingue += 1
        volumen_igual.append(abs(float(Pb.sum()) - float(Pp.sum())))
    print(f"  2 · «precio» da un resultado distinto           "
          f"{distingue} de {len(SEMILLAS)}"
          f"{'   ok' if distingue == len(SEMILLAS) else '   FALLA'}")
    if distingue != len(SEMILLAS):
        fallos.append("la opcion no cambia nada")

    # ── 3 · un valor desconocido se rechaza ─────────────────────────────
    try:
        corre(caso(5), peso_virtual="loquesea")
        rechaza = False
    except ValueError:
        rechaza = True
    print(f"  3 · rechaza un valor desconocido                "
          f"{'ok' if rechaza else 'FALLA'}")
    if not rechaza:
        fallos.append("acepta un valor desconocido en silencio")

    # ── 4 · el volumen no se mueve ──────────────────────────────────────
    peor = max(volumen_igual)
    ok = peor < 1e-9
    print(f"  4 · el volumen no cambia entre las dos formas   "
          f"max|dif| {peor:.2e} kWh   {'ok' if ok else 'FALLA'}")
    if not ok:
        fallos.append(f"el volumen se mueve {peor:.3e} kWh")

    print()
    print(f"  {'semilla':>8s} {'barrera':>34s} {'precio':>34s}")
    for s in SEMILLAS:
        pb, _ = corre(caso(s), peso_virtual="barrera")
        pp, _ = corre(caso(s), peso_virtual="precio")
        print(f"  {s:>8d} {str(np.round(pb, 1)):>34s} "
              f"{str(np.round(pp, 1)):>34s}")

    print()
    if fallos:
        print("  FALLA: " + "; ".join(fallos))
        return 1
    print("  todo en verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
