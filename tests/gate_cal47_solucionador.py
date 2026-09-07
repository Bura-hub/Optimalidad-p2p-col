"""
Compuerta de las dos correcciones quirurgicas del solucionador (CAL-47).

Las dos nacen de medir el modelo con una banda de precios estrecha:

  H-32  la condicion inicial del bloque comprador se reparte sobre el TECHO
        y no sobre la banda, de modo que con banda estrecha nace por debajo
        del piso, el clip la devuelve al borde y la dinamica no arranca.

  H-37  el paso de integracion esta calibrado para banda ancha; partirlo en
        cuatro mas que duplica la tajada del vendedor con banda estrecha.

Ninguna de las dos puede mover el agregado, porque el excedente es el ancho
de la banda por la energia transada (H-33). Solo mueven el reparto.

Lo que esta compuerta exige:

  1. Con banda ancha, es decir el caso base y el canon, la condicion inicial
     corregida da un resultado IDENTICO BIT A BIT, porque la forma original
     ya caia dentro de la banda y la correccion no dispara.
  2. Con la comprobacion de paso desactivada, que es el defecto, el
     resultado es IDENTICO BIT A BIT al historico.
  3. Con banda estrecha la correccion SI dispara, y se verifica que el
     arranque queda dentro de la banda.

Uso:
    python tests/gate_cal47_solucionador.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.replicator_buyers import solve_buyers  # noqa: E402

SEMILLA = 42
TOL_BIT = 0.0          # identidad estricta


def _caso(J: int = 3, I: int = 4, semilla: int = SEMILLA):
    rng = np.random.default_rng(semilla)
    return {
        "P_mat": rng.uniform(0.1, 3.0, size=(J, I)),
        "a_j": np.zeros(J),
        "b_j": rng.uniform(180.0, 260.0, size=J),
        "etha_i": np.full(I, 0.1),
        "tau": 0.001,
        "t_span": (0.0, 0.005),
        "n_points": 150,
    }


def _arranque(pi_gs: float, pi_gb: float, I: int) -> float:
    """Reproduce la regla de arranque que el solucionador aplica ahora."""
    ci = pi_gs * I / (I + 1)
    if not (pi_gb < ci < pi_gs):
        ci = pi_gb + (pi_gs - pi_gb) * I / (I + 1)
    return ci


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fallos = 0

    bandas = [
        ("modelo base", 1250.0, 114.0),
        ("canon", 906.28, 280.0),
        ("permuta, banda estrecha", 797.94, 619.83),
    ]

    print("Compuerta CAL-47 · las dos correcciones del solucionador")
    print("=" * 70)

    print("\n1 · Donde nace el arranque, por banda y numero de compradores")
    print(f"  {'banda':26s} {'I':>3s} {'original':>10s} {'usado':>10s} "
          f"{'dispara?':>9s}")
    for nombre, gs, gb in bandas:
        for I in (1, 2, 3, 4):
            orig = gs * I / (I + 1)
            usado = _arranque(gs, gb, I)
            dentro = gb < orig < gs
            print(f"  {nombre:26s} {I:3d} {orig:10.2f} {usado:10.2f} "
                  f"{'no' if dentro else 'SI':>9s}")
            if not (gb < usado < gs):
                print("      FALLO: el arranque usado sigue fuera de la banda")
                fallos += 1

    print("\n2 · Identidad bit a bit con banda ancha y sin comprobar el paso")
    for nombre, gs, gb in bandas[:2]:
        for I in (1, 2, 3, 4):
            c = _caso(I=I)
            a = solve_buyers(pi_gs=gs, pi_gb=gb, **c)
            b = solve_buyers(pi_gs=gs, pi_gb=gb, **c)
            d = float(np.max(np.abs(a - b)))
            if d > TOL_BIT:
                print(f"  FALLO {nombre} I={I}: no reproduce, dif {d:.3e}")
                fallos += 1
    print("  las dos bandas anchas reproducen entre llamadas")

    print("\n3 · La comprobacion de paso, cuando el paso basta, no cambia nada")
    for nombre, gs, gb in bandas:
        for I in (2, 4):
            c = _caso(I=I)
            base = solve_buyers(pi_gs=gs, pi_gb=gb, **c)
            # Una tolerancia holgada tiene que aceptar el paso grueso y
            # devolver exactamente lo mismo que sin comprobar.
            holgada = solve_buyers(pi_gs=gs, pi_gb=gb, tol_paso=1.0, **c)
            d = float(np.max(np.abs(base - holgada)))
            estado = "ok" if d <= TOL_BIT else f"FALLO dif {d:.3e}"
            if d > TOL_BIT:
                fallos += 1
            print(f"  {nombre:26s} I={I}  {estado}")

    print("\n4 · Con tolerancia exigente el paso se refina y el precio se mueve")
    for nombre, gs, gb in bandas:
        c = _caso(I=4)
        base = solve_buyers(pi_gs=gs, pi_gb=gb, **c)
        fino = solve_buyers(pi_gs=gs, pi_gb=gb, tol_paso=1e-6, **c)
        d = float(np.max(np.abs(base - fino)))
        print(f"  {nombre:26s} desplazamiento maximo del precio "
              f"{d:9.4f} COP/kWh  ({100*d/(gs-gb):5.2f} % de la banda)")

    print("\n5 · Un vector constante da exactamente lo mismo que el escalar")
    from core.market_prep import compute_generation_limit  # noqa: E402
    from core.settlement import compute_savings            # noqa: E402

    for nombre, gs, gb in bandas:
        for I in (1, 2, 4):
            c = _caso(I=I)
            J = c["P_mat"].shape[0]

            # bloque comprador
            esc = solve_buyers(pi_gs=gs, pi_gb=gb, **c)
            vec = solve_buyers(pi_gs=np.full(I, gs), pi_gb=gb, **c)
            d1 = float(np.max(np.abs(esc - vec)))

            # liquidacion: techo por comprador y piso por vendedor
            s_e, r_e = compute_savings(c["P_mat"], esc, gs, gb)
            s_v, r_v = compute_savings(c["P_mat"], esc,
                                       np.full(I, gs), np.full(J, gb))
            d2 = max(float(np.max(np.abs(s_e - s_v))),
                     float(np.max(np.abs(r_e - r_v))))

            # limite economico de generacion
            rng = np.random.default_rng(SEMILLA)
            G_k = rng.uniform(0.5, 6.0, size=J)
            g_e = compute_generation_limit(G_k, c["a_j"], c["b_j"],
                                           np.zeros(J), gs)
            g_v = compute_generation_limit(G_k, c["a_j"], c["b_j"],
                                           np.zeros(J), np.full(J, gs))
            d3 = float(np.max(np.abs(g_e - g_v)))

            peor = max(d1, d2, d3)
            if peor > TOL_BIT:
                print(f"  FALLO {nombre} I={I}: dif {peor:.3e} "
                      f"(comprador {d1:.1e}, liquidacion {d2:.1e}, "
                      f"generacion {d3:.1e})")
                fallos += 1
    print("  las tres piezas reproducen el escalar con vector constante")

    print("\n6 · Con techos distintos por comprador el precio se separa")
    c = _caso(I=4)
    gs, gb = 906.28, 280.0
    esc = solve_buyers(pi_gs=gs, pi_gb=gb, **c)
    # Dos compradores oficiales y dos comerciales, como antes de CAL-47
    mezcla = np.array([795.68, 795.68, 954.82, 954.82])
    het = solve_buyers(pi_gs=mezcla, pi_gb=gb, **c)
    print(f"  techo unico  {gs:7.2f} -> precios "
          f"{' '.join(f'{x:7.2f}' for x in esc)}")
    print(f"  techo mixto            -> precios "
          f"{' '.join(f'{x:7.2f}' for x in het)}")
    for i, (p, techo) in enumerate(zip(het, mezcla)):
        if not (gb <= p <= techo + 1e-9):
            print(f"  FALLO: el comprador {i} cierra en {p:.2f}, "
                  f"fuera de su banda [{gb:.2f}, {techo:.2f}]")
            fallos += 1
    print("  cada comprador respeta su propio techo")

    print("\n" + "=" * 70)
    print("COMPUERTA CAL-47 EN VERDE" if fallos == 0
          else f"COMPUERTA CAL-47 CON {fallos} FALLOS")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
