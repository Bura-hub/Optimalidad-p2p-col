"""
Shapley de dos factores sobre las cuatro esquinas del factorial.

Actividad 3.3. Revision r1 del articulo (AE-5): «Shapley values should then be
recalculated using the resulting economic outcomes». Regla de cita de CANON
§14.21: los dos ordenes o Shapley, nunca un termino a solas.

  v00 ninguno, v10 solo el 1, v01 solo el 2, v11 los dos.

Desde v00 (el factorial completo):
  orden «el 1 primero»: s1 = v10 − v00, s2 = v11 − v10
  orden «el 2 primero»: s2 = v01 − v00, s1 = v11 − v01
  Shapley: la media de los dos; interaccion = (v11 − v01) − (v10 − v00).

Desde C4, como el articulo (l. 549 de `r3_final/articulo_es.tex`): el valor de
Shapley de cada supuesto desde v00 menos la mitad de lo que v00 queda por
debajo de C4, de modo que los dos suman v11 − C4.
"""
from __future__ import annotations


def shapley_dos(v00, v10, v01, v11) -> dict:
    """Los dos ordenes, Shapley y la interaccion. Admite escalares o arrays."""
    s1_primero = v10 - v00
    s2_despues = v11 - v10
    s2_primero = v01 - v00
    s1_despues = v11 - v01
    return dict(
        total=v11 - v00,
        orden1_s1=s1_primero, orden1_s2=s2_despues,
        orden2_s1=s1_despues, orden2_s2=s2_primero,
        shapley_s1=0.5 * (s1_primero + s1_despues),
        shapley_s2=0.5 * (s2_primero + s2_despues),
        interaccion=s1_despues - s1_primero,
    )


def desde_c4(sh: dict, v00, c4) -> dict:
    """Shapley medido desde C4 (regla del articulo)."""
    medio = 0.5 * (c4 - v00)
    return dict(shapley_s1=sh["shapley_s1"] - medio,
                shapley_s2=sh["shapley_s2"] - medio,
                total=sh["total"] - (c4 - v00))
