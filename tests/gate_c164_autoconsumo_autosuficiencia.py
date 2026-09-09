"""
Compuerta de C-164: el autoconsumo y la autosuficiencia dicen lo que son.

EL DEFECTO. Los dos indices llevaban el nombre del otro, y no en un sitio sino
en tres: el modulo de liquidacion, el motor de comparacion y el campo por hora
del resultado. La capa de lectura del documento lo venia **parcheando al abrir
el libro**, de modo que el texto salia bien y el codigo seguia mal.

LA CONVENCION, que es la estandar de la literatura de fotovoltaica en
edificios:

    autoconsumo      = energia aprovechada en sitio / GENERACION total
                       (que fraccion de lo que genero se aprovecha)
    autosuficiencia  = energia aprovechada en sitio / DEMANDA total
                       (que fraccion de lo que consumo cubro sin la red)

POR QUE SE PUEDE COMPROBAR POR FISICA, y por eso se detecto. Con una cobertura
solar baja —el 20 % en la primera frontera— la fraccion de demanda cubierta con
generacion propia **no puede ser alta**, mientras que la fraccion de generacion
aprovechada si. Un caso con generacion escasa separa los dos sin ambiguedad, y
uno con generacion abundante los separa al reves.

QUE PRUEBA:

  1. Con generacion ESCASA, el autoconsumo es alto y la autosuficiencia baja.
  2. Con generacion ABUNDANTE, al reves.
  3. Los dos son fracciones en el intervalo cerrado de cero a uno.
  4. La identidad que los liga: autoconsumo x generacion = autosuficiencia x
     demanda, porque el numerador de los dos es la misma energia.
  5. El motor por hora y el motor de comparacion coinciden en el criterio.

Uso:
    python tests/gate_c164_autoconsumo_autosuficiencia.py
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402

TOL = 1e-9


def main() -> int:
    from core.settlement import self_consumption_index, self_sufficiency_index
    from scenarios.comparison_engine import _sc_index_static, _ss_index_static

    rng = np.random.default_rng(3)
    N, T = 5, 240
    D = rng.uniform(4.0, 12.0, (N, T))
    fallos = []

    # ── 1 · generacion escasa: mucho autoconsumo, poca autosuficiencia ────
    G_poca = D * rng.uniform(0.10, 0.25, (N, T))
    sc_p = _sc_index_static(G_poca, D)
    ss_p = _ss_index_static(G_poca, D)
    ok1 = sc_p > 0.90 and ss_p < 0.30
    print(f"  1 · con generación escasa   autoconsumo {sc_p:.4f}, "
          f"autosuficiencia {ss_p:.4f}   {'ok' if ok1 else 'FALLA'}")
    if not ok1:
        fallos.append("con generación escasa los dos índices están cruzados")

    # ── 2 · generacion abundante: al reves ────────────────────────────────
    G_mucha = D * rng.uniform(3.0, 6.0, (N, T))
    sc_m = _sc_index_static(G_mucha, D)
    ss_m = _ss_index_static(G_mucha, D)
    ok2 = sc_m < 0.35 and ss_m > 0.90
    print(f"  2 · con generación abundante   autoconsumo {sc_m:.4f}, "
          f"autosuficiencia {ss_m:.4f}   {'ok' if ok2 else 'FALLA'}")
    if not ok2:
        fallos.append("con generación abundante los dos índices están cruzados")

    # ── 3 · los dos son fracciones ────────────────────────────────────────
    todos = [sc_p, ss_p, sc_m, ss_m]
    ok3 = all(-TOL <= v <= 1.0 + TOL for v in todos)
    print(f"  3 · los dos viven en [0; 1]   "
          f"mínimo {min(todos):.4f}, máximo {max(todos):.4f}   "
          f"{'ok' if ok3 else 'FALLA'}")
    if not ok3:
        fallos.append("algún índice se sale del intervalo")

    # ── 4 · la identidad que los liga ─────────────────────────────────────
    peor = 0.0
    for G in (G_poca, G_mucha):
        sc, ss = _sc_index_static(G, D), _ss_index_static(G, D)
        peor = max(peor, abs(sc * float(np.sum(G)) - ss * float(np.sum(D))))
    ok4 = peor <= 1e-6 * float(np.sum(D))
    print(f"  4 · autoconsumo × generación = autosuficiencia × demanda   "
          f"dif {peor:.3e}   {'ok' if ok4 else 'FALLA'}")
    if not ok4:
        fallos.append("la identidad entre los dos índices no se cumple")

    # ── 5 · el motor por hora usa el mismo criterio ───────────────────────
    #
    # Sin mercado (reparto nulo) los indices por hora deben reducirse a los
    # estaticos de esa hora. Si uno de los dos modulos volviera a cruzarlos,
    # esta comprobacion lo separa.
    k = 7
    P0 = np.zeros((2, 2))
    sc_h = self_consumption_index(P0, G_poca[:, k], D[:, k])
    ss_h = self_sufficiency_index(P0, D[:, k], G_poca[:, k])
    sc_e = _sc_index_static(G_poca[:, k:k + 1], D[:, k:k + 1])
    ss_e = _ss_index_static(G_poca[:, k:k + 1], D[:, k:k + 1])
    d5 = max(abs(sc_h - sc_e), abs(ss_h - ss_e))
    ok5 = d5 <= 1e-9
    print(f"  5 · liquidación y comparación coinciden sin mercado   "
          f"dif {d5:.3e}   {'ok' if ok5 else 'FALLA'}")
    if not ok5:
        fallos.append("los dos módulos no usan el mismo criterio")

    print()
    if fallos:
        for x in fallos:
            print(f"  FALLA: {x}")
        return 1
    print("  C-164 EN VERDE. El autoconsumo se mide contra la generación y la")
    print("  autosuficiencia contra la demanda, en los dos módulos, y la capa")
    print("  de lectura del documento ya no necesita parchear nada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
