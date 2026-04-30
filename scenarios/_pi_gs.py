"""
scenarios/_pi_gs.py
-------------------
Helper privado para normalizar `pi_gs` a las formas que consumen los
escenarios C1-C4 y los módulos de análisis.

Permite que los escenarios acepten indistintamente:

    pi_gs : float                   caso uniforme (sintético, sensibilidad)
    pi_gs : np.ndarray (N,)         calibración Cedenar per-agente (CAL-8)
    pi_gs : np.ndarray (N, T)       calibración Cedenar mes a mes (CAL-9)
    pi_gs : np.ndarray (T,)         tarifa horaria comunitaria (uso interno)

Funciones públicas:

- ``as_pi_gs_vector(pi_gs, N)``  → array (N,)        (compatibilidad CAL-8)
- ``as_pi_gs_array(pi_gs, N, T)`` → array (N, T)     (CAL-9, contrato canónico)

Uso interno en escenarios:

    from ._pi_gs import as_pi_gs_array

    def run_cN_*(D, G, pi_gs, ...):
        N, T = D.shape
        pi_gs = as_pi_gs_array(pi_gs, N, T)
        # a partir de aquí usar pi_gs[n, t] o pi_gs[n, hours].mean()

Compatibilidad: ambos helpers aceptan las mismas formas de entrada; el
broadcast de escalar / (N,) / (T,) → (N, T) es idempotente.
"""

from __future__ import annotations

import numpy as np


def as_pi_gs_vector(pi_gs, N: int) -> np.ndarray:
    """
    Normaliza pi_gs a array (N,) sin importar si entró como escalar,
    vector (N,) o matriz (N, T).

    - float / 0-d ndarray  → np.full(N, valor)
    - ndarray (N,)         → copia float
    - ndarray (N, T)       → promedio sobre el eje temporal
    - cualquier otra forma → ValueError

    Mantenido para compatibilidad CAL-8 con módulos que aún consumen
    pi_gs como vector escalar por agente. El nuevo contrato canónico es
    ``as_pi_gs_array``.
    """
    arr = np.atleast_1d(np.asarray(pi_gs, dtype=float))
    if arr.size == 1:
        return np.full(N, float(arr.flat[0]))
    if arr.shape == (N,):
        return arr.astype(float, copy=False)
    if arr.ndim == 2 and arr.shape[0] == N:
        # CAL-9: matriz (N, T) → colapsar al promedio temporal por agente.
        return arr.mean(axis=1).astype(float, copy=False)
    raise ValueError(
        f"pi_gs shape {arr.shape} != (N={N},) — debe ser float, "
        f"array (N,) o matriz (N, T)."
    )


def as_pi_gs_array(pi_gs, N: int, T: int) -> np.ndarray:
    """
    Normaliza pi_gs a matriz (N, T) sin importar la forma de entrada.

    - float / 0-d ndarray  → np.full((N, T), valor)
    - ndarray (N,)         → broadcast a (N, T)  (constante en tiempo)
    - ndarray (T,)         → broadcast a (N, T)  (constante entre agentes)
    - ndarray (N, T)       → as-is con validación de shape
    - cualquier otra forma → ValueError

    Contrato canónico CAL-9: los escenarios C1-C4 consumen tarifas
    temporales mes a mes. Se devuelve siempre una copia escribible para
    evitar que llamadores modifiquen el broadcast subyacente.
    """
    arr = np.atleast_1d(np.asarray(pi_gs, dtype=float))
    if arr.size == 1:
        return np.full((N, T), float(arr.flat[0]))
    if arr.shape == (N,):
        return np.broadcast_to(arr[:, None], (N, T)).astype(float, copy=True)
    if arr.shape == (T,) and N != T:
        return np.broadcast_to(arr[None, :], (N, T)).astype(float, copy=True)
    if arr.shape == (N, T):
        return arr.astype(float, copy=False)
    # Caso degenerado N == T: priorizar interpretación per-agente.
    if N == T and arr.shape == (N,):
        return np.broadcast_to(arr[:, None], (N, T)).astype(float, copy=True)
    raise ValueError(
        f"pi_gs shape {arr.shape} no es compatible con (N={N}, T={T}). "
        f"Acepta float, (N,), (T,) o (N, T)."
    )
