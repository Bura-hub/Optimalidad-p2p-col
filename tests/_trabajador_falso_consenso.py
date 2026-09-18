"""Un trabajador y una medicion falsos para las pruebas del pool de
`corre_mediciones.py` (tarea 4d, `tests/test_arnes_consenso.py`).

No es una prueba: pytest no lo recoge, porque no empieza por `test_`. Vive en
un modulo propio y ligero porque los procesos del pool lo importan para
deshacer el pickle de `trabaja`, y el modulo de las pruebas trae el arnes.

`trabaja` muere con `os._exit(1)` en la especificacion que lo pide, que es
lo que ve el pool cuando el sistema mata a un trabajador por falta de memoria:
un proceso que termina de golpe, sin excepcion ni resultado.
"""
import os
import time

MEDICION = "M-X"
QUE_DECIDE = "nada: prueba del pool de corre_mediciones.py"

# El plan de `specs`: lo fija cada prueba en el proceso principal.
PLAN = []


def trabaja(spec):
    """Una corrida falsa: muere si la especificacion lo pide y, si no,
    devuelve un registro de «sin mercado» con la forma de `trabajo`.

    `muere`: muere siempre. `muere_una_vez`: la ruta de una marca; muere si la
    marca no esta (y la deja), de modo que a la segunda corre bien."""
    if spec.get("muere"):
        os._exit(1)
    marca = spec.get("muere_una_vez")
    if marca and not os.path.exists(marca):
        with open(marca, "w", encoding="ascii") as f:
            f.write("murio")
        os._exit(1)
    time.sleep(float(spec.get("duerme", 0.0)))
    return dict(spec=spec, msg="sin mercado", filas=[], avisos=[], cerrada={},
                veredicto={}, seg=0.0)


def specs(horas):
    return [dict(sp) for sp in PLAN]


def plan(mueren, n, duerme=0.05, una_vez=None):
    """n especificaciones; mueren siempre las de los indices de `mueren`, y
    una sola vez las de `una_vez` ({indice: ruta de su marca})."""
    una_vez = una_vez or {}
    return [dict(medicion=MEDICION, caso="X", fecha=f"h{i}", etq="prueba",
                 grupo="g", muere=(i in mueren), duerme=duerme,
                 muere_una_vez=una_vez.get(i))
            for i in range(n)]
