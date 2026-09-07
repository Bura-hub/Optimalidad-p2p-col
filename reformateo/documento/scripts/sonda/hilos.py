"""
Un hilo por proceso, y hay que fijarlo ANTES de importar numpy.

Las bibliotecas de algebra lineal abren por defecto tantos hilos como
nucleos vean. Cuando el trabajo se reparte en tantos PROCESOS como nucleos,
eso multiplica: en el servidor de 32 nucleos serian 32 procesos por 32 hilos
peleando por 32 nucleos, y el tiempo se va en esperas entre hilos que no
tienen nada que calcular.

Aqui no aportan nada aunque no estorbaran. El sistema que el solucionador
integra tiene del orden de treinta y siete estados: las operaciones son
demasiado pequenas para que repartirlas entre hilos compense.

Las variables solo surten efecto si se fijan antes de que numpy cargue su
biblioteca, de modo que este modulo se importa en la PRIMERA linea de cada
sonda, antes que ningun otro import. Si ya vienen puestas desde fuera se
respetan, para que el lanzador pueda decidir otra cosa.
"""
from __future__ import annotations

import os

VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)


def uno_por_proceso() -> None:
    """Fija un hilo por proceso, sin pisar lo que venga del entorno."""
    for v in VARIABLES:
        os.environ.setdefault(v, "1")


uno_por_proceso()
