"""
La capacidad instalada de cada planta, que decide el numeral del articulo 25.

Las cinco plantas del MTE son identicas: 17,55 kWp cada una, 87,75 kWp en
total (Informe 4 del MTE, p. 4; H-67 registra las otras dos cifras que
circulan y por que se descartan). Hasta el 2026-09-13 el orquestador pasaba
la generacion media como aproximacion de la capacidad; con el escalado de la
generacion (spec 4.11) la capacidad es la placa por el factor de cada una.

Actividad 2.2.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

KWP_POR_PLANTA = 17.55


def capacidad_instalada(nombres, factores: Optional[np.ndarray] = None
                        ) -> np.ndarray:
    """Vector (N,) en kW: la placa de cada planta por su factor de generacion."""
    f = (np.ones(len(nombres)) if factores is None
         else np.asarray(factores, dtype=float).reshape(-1))
    if f.size != len(nombres):
        raise ValueError(f"{f.size} factores para {len(nombres)} plantas")
    return KWP_POR_PLANTA * f
