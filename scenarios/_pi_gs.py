"""
scenarios/_pi_gs.py
-------------------
Helper privado para normalizar `pi_gs` a vector (N,).

Permite que los escenarios C1-C4 acepten indistintamente
`pi_gs : float` (caso uniforme: sintético, sensibilidad) o
`pi_gs : np.ndarray (N,)` (calibración real Cedenar per-agente, CAL-8).

Uso interno:

    from ._pi_gs import as_pi_gs_vector

    def run_cN_*(D, G, pi_gs, ...):
        N = D.shape[0]
        pi_gs = as_pi_gs_vector(pi_gs, N)
        # a partir de aquí usar pi_gs[n] dentro de bucles per-agente
"""

from __future__ import annotations

import numpy as np


def as_pi_gs_vector(pi_gs, N: int) -> np.ndarray:
    """
    Normaliza pi_gs a array (N,) sin importar si entró como escalar o vector.

    - float / 0-d ndarray  → np.full(N, valor)
    - ndarray (N,)         → copia float
    - cualquier otra forma → ValueError
    """
    arr = np.atleast_1d(np.asarray(pi_gs, dtype=float))
    if arr.size == 1:
        return np.full(N, float(arr.flat[0]))
    if arr.shape != (N,):
        raise ValueError(
            f"pi_gs shape {arr.shape} != (N={N},) — debe ser float "
            f"o array de N agentes."
        )
    return arr.astype(float, copy=False)
