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

- ``as_pi_gs_vector(pi_gs, N)``    → array (N,)      (compatibilidad CAL-8)
- ``as_pi_gs_array(pi_gs, N, T)``  → array (N, T)    (CAL-9, canónico)
- ``as_component_c_array(c, pi_gs_arr, N, T)`` → array (N, T)  (CAL-10)

Uso interno en escenarios:

    from ._pi_gs import as_pi_gs_array, as_component_c_array

    def run_cN_*(D, G, pi_gs, ..., component_c="auto"):
        N, T = D.shape
        pi_gs = as_pi_gs_array(pi_gs, N, T)
        pi_C  = as_component_c_array(component_c, pi_gs, N, T)
        # a partir de aquí usar pi_gs[n, t] o (pi_gs[n, t] - pi_C[n, t])

Compatibilidad: ambos helpers de pi_gs aceptan las mismas formas de
entrada; el broadcast de escalar / (N,) / (T,) → (N, T) es idempotente.
"""

from __future__ import annotations

from typing import Union

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


def as_component_c_array(
    component_c: Union[float, str, np.ndarray, None],
    pi_gs_arr: np.ndarray,
    N: int,
    T: int,
) -> np.ndarray:
    """
    Normaliza el componente C de Comercialización a matriz (N, T) en COP/kWh.

    Bajo Res. CREG 174/2021 art. 25 (renumeración CAL-31) el
    comercializador sigue cobrando el
    componente C aunque el AGPE permute energía. CAL-10 modela este efecto
    valorando la permuta a (pi_gs - pi_C) en lugar de pi_gs completo.

    Modos aceptados
    ---------------
    "auto" (default canónico CAL-10):
        pi_C = pi_gs * C_FRACTION   con C_FRACTION ≈ 90/650 ≈ 0.1385
        proporcional al CU (escala con tarifas Cedenar reales).

    None o 0.0:
        Retorna matriz de ceros → comportamiento legacy pre-CAL-10
        (sin descuento, valoración a pi_gs completo).

    float:
        Constante uniforme en COP/kWh. Útil para tests con C fijo
        (p.ej. component_c=90.0 reproduce el supuesto literal de
        CU_COMPONENTS_2025["C"]).

    np.ndarray (N,):
        Per-agente, constante en tiempo. Útil si distintas instituciones
        tienen márgenes de Comercialización diferentes.

    np.ndarray (T,):
        Constante entre agentes, varía en tiempo.

    np.ndarray (N, T):
        Matriz completa as-is (con validación de shape).

    Parámetros
    ----------
    component_c : str | float | np.ndarray | None
        Especificación del componente C; ver modos arriba.
    pi_gs_arr : np.ndarray (N, T)
        Matriz de pi_gs ya normalizada por as_pi_gs_array. Necesaria para
        el modo "auto".
    N, T : int
        Dimensiones esperadas (N agentes, T horas).

    Retorna
    -------
    np.ndarray (N, T)
        Matriz de pi_C en COP/kWh, lista para restar a pi_gs.
    """
    if pi_gs_arr.shape != (N, T):
        raise ValueError(
            f"pi_gs_arr shape {pi_gs_arr.shape} != ({N}, {T}); "
            f"normaliza con as_pi_gs_array antes de pasar a as_component_c_array."
        )

    if component_c is None:
        return np.zeros((N, T), dtype=float)

    if isinstance(component_c, str):
        if component_c == "auto":
            # Import perezoso para evitar import circular en tests aislados.
            from data.xm_prices import C_FRACTION
            return pi_gs_arr * float(C_FRACTION)
        raise ValueError(
            f"component_c='{component_c}' no soportado. "
            f"Cadenas válidas: 'auto'."
        )

    arr = np.atleast_1d(np.asarray(component_c, dtype=float))
    if arr.size == 1:
        return np.full((N, T), float(arr.flat[0]))
    if arr.shape == (N,):
        return np.broadcast_to(arr[:, None], (N, T)).astype(float, copy=True)
    if arr.shape == (T,) and N != T:
        return np.broadcast_to(arr[None, :], (N, T)).astype(float, copy=True)
    if arr.shape == (N, T):
        out = arr.astype(float, copy=True)
        # CAL-10b: si el helper Cedenar marcó celdas con NaN (mes ausente
        # del CSV o Cvm/COT NaN), rellenamos con la aproximación proporcional
        # CAL-10 — pi_gs[n, k] * C_FRACTION — para no romper la corrida.
        nan_mask = np.isnan(out)
        if nan_mask.any():
            from data.xm_prices import C_FRACTION
            out[nan_mask] = pi_gs_arr[nan_mask] * float(C_FRACTION)
        return out
    if N == T and arr.shape == (N,):
        return np.broadcast_to(arr[:, None], (N, T)).astype(float, copy=True)
    raise ValueError(
        f"component_c shape {arr.shape} no es compatible con (N={N}, T={T}). "
        f"Acepta 'auto', None, float, (N,), (T,) o (N, T)."
    )
