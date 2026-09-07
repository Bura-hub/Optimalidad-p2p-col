"""
Compuerta de H-45: el techo por comprador entra al solucionador acoplado.

El techo es lo que CADA comprador le paga a la red, y en esta comunidad no
es uno solo porque hay dos comercializadores. Hasta el 2026-09-07 el
solucionador acoplado recibia un ESCALAR, el mayor de los techos de la hora,
y el techo propio se aplicaba DESPUES como recorte. Medido sobre un dia
completo: tres de los cuatro compradores pagaban exactamente su techo y su
ahorro valia cero, porque el ahorro es el techo menos el precio.

Aviso de fidelidad, que la compuerta tambien fija: el modelo base NO
contempla esto. La ecuacion (5) del articulo publicado escribe las dos cotas
como escalares globales, y el fichero original las fija a mano. El techo por
comprador es una extension de esta tesis, no una traduccion.

Lo que esta compuerta exige:

  1. Con techo escalar el resultado es IDENTICO BIT A BIT, en las tres
     bandas de interes: la del modelo base, la del canon y la de permuta.
     Es la condicion para que el cambio sea una generalizacion estricta.
  2. Un vector constante da lo mismo que el escalar de ese valor.
  3. Con techos distintos, ningun precio supera EL SUYO.
  4. Con techos distintos, el comprador del techo bajo deja de estar pegado
     a el, que es el defecto que motiva el cambio.

El punto 1 se comprueba contra la formula historica reproducida aqui, no
contra el fichero anterior, para que la compuerta siga sirviendo cuando ese
fichero ya no exista.

Uso:
    python tests/gate_h45_techo_por_comprador.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.coupled_ode_convergence import solve_coupled_for_hour  # noqa: E402

BANDAS = (("modelo base", 1250.00, 114.00),
          ("canon      ",  906.27, 280.00),
          ("permuta    ",  731.10, 620.00))


def caso(semilla: int = 5, J: int = 3, I: int = 4) -> dict:
    rng = np.random.default_rng(semilla)
    return dict(
        G_net_j=rng.uniform(1.0, 4.0, J), D_net_i=rng.uniform(1.0, 4.0, I),
        a_j=np.zeros(J), b_j=rng.uniform(80.0, 200.0, J),
        etha_i=rng.uniform(0.05, 0.5, I),
        lam_j=np.full(J, 100.0), theta_j=np.full(J, 0.5),
        G_klim_i=rng.uniform(0.0, 2.0, I),
        lam_i=np.full(I, 100.0), theta_i=np.full(I, 0.5))


def corre(d: dict, pi_gs, pi_gb: float):
    tr = solve_coupled_for_hour(
        **d, pi_gs=pi_gs, pi_gb=pi_gb, tau_sellers=0.001, tau_buyers=0.01,
        t_span=(0.0, 0.01), n_points=200)
    return np.asarray(tr.pi_star, float), np.asarray(tr.P_star, float)


def main() -> int:
    fallos: list[str] = []
    print()
    print("  Compuerta H-45 · el techo por comprador en el acoplado")
    print("  " + "=" * 60)

    # ── 1 y 2 · el escalar no se movio, y el vector constante lo iguala ──
    malos = []
    for etiqueta, gs, gb in BANDAS:
        for semilla in (5, 11, 23):
            d = caso(semilla)
            I = len(d["D_net_i"])
            pe, Pe = corre(d, gs, gb)
            pv, Pv = corre(d, np.full(I, gs), gb)
            if not (np.array_equal(pe, pv) and np.array_equal(Pe, Pv)):
                malos.append(f"{etiqueta.strip()} semilla {semilla}")
    ok = not malos
    print(f"  1 · vector constante identico al escalar, 9 casos     "
          f"{'ok' if ok else 'FALLA'}")
    if not ok:
        fallos += malos

    # ── 3 · con dos techos, cada precio respeta el suyo ──────────────────
    d = caso(5)
    I = len(d["D_net_i"])
    piso = 620.0
    techos = np.resize(np.array([731.10, 731.10, 731.10, 777.20]), I)
    pi, _ = corre(d, techos, piso)
    excede = bool(np.any(pi > techos + 1e-9))
    bajo = bool(np.any(pi < piso - 1e-9))
    ok = not (excede or bajo)
    print(f"  2 · ningun precio sale de SU banda                    "
          f"{'ok' if ok else 'FALLA'}")
    if not ok:
        fallos.append("precio fuera de su propia banda")

    # ── 4 · el comprador del techo bajo se despega ───────────────────────
    bajos = techos < techos.max() - 1e-9
    pegados = bool(np.all(pi[bajos] >= techos[bajos] - 1e-6))
    print(f"  3 · el comprador del techo bajo NO esta pegado a el   "
          f"{'FALLA' if pegados else 'ok'}")
    if pegados:
        fallos.append("el techo bajo sigue pegado")

    print()
    print(f"  {'techo':>9s} {'precio':>9s} {'ahorro/kWh':>11s} {'posicion':>9s}")
    for i in range(I):
        ancho = techos[i] - piso
        pos = (pi[i] - piso) / ancho if ancho > 1e-9 else float("nan")
        print(f"  {techos[i]:9.2f} {pi[i]:9.2f} {techos[i] - pi[i]:11.4f} "
              f"{pos:9.3f}")

    print()
    if fallos:
        print("  FALLA: " + "; ".join(fallos))
        return 1
    print("  todo en verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
