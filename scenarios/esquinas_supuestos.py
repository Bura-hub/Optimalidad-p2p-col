"""
La liquidacion de las cuatro esquinas del factorial de los dos supuestos.

Actividad 3.3. Revision r1 del articulo (envio 11297), comentario AE-5 del
editor asociado: las cuatro combinaciones de los dos supuestos de liquidacion
evaluadas en un mismo marco. Diseno en
`Documentos/articulo_latam/v2_es/revision_r1/diseno_mediciones_completas.md`,
seccion 1; las definiciones son las de CANON §14.21.

Son las mismas formulas que `reformateo/documento/scripts/articulo/
atribucion_supuestos.py` (`art25`, `colectivo` y `esquinas`) aplicaba a los
flujos FIJOS del canon, traidas al paquete para liquidar cada esquina sobre
SUS PROPIOS flujos (los de `main_simulation.py --esquina`). La aritmetica no
cambia. Ningun escenario existente se toca y nada de esto corre por defecto.

  p2p      los dos: auto + CU·q + art25(sr, dr, ded1)
  solo1    solo el 1: auto + CU·q − ded4·q + art25(sr, dr, ded1)
  solo2    solo el 2: auto + CU·q + colectivo(sr, dr, ded4, PDE de sr)
  ninguno  ninguno: auto + colectivo(s, d, ded4, PDE de q + sr)

con ded1 la deduccion del numeral de la planta (art. 25 de la CREG 174), ded4
la del caso 2 del art. 20 de la CREG 101 072 (kappa·Cv + Theta), del
COMPRADOR, y el PDE propio de cada mes (art. 19). `pagos` (N, T), opcional,
son los pagos internos netos (cobrado menos pagado): suman cero en cada hora y
solo cambian el reparto por institucion.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from core.opciones_externas import precio_permuta_por_periodo, reparto_anexo4
from scenarios.scenario_c4_creg101072 import compute_pde_weights

ESQUINAS = ("p2p", "solo1", "solo2", "ninguno")


def _exceso_valor(ex: np.ndarray, pb: np.ndarray) -> np.ndarray:
    pb = np.asarray(pb, dtype=float).reshape(-1)
    hay = ex > 0
    if (hay & ~np.isfinite(pb)[None, :]).any():
        raise ValueError("hay exceso en horas sin bolsa conocida")
    return np.where(hay, ex * np.where(np.isfinite(pb), pb, 0.0)[None, :], 0.0)


def art25(iny, ret, CU, ded, mes, pb):
    """Art. 25 y Anexo 4 por miembro (como C1). Devuelve (valor, exceso)."""
    cr, ex, _ = reparto_anexo4(iny, ret, mes)
    pr = precio_permuta_por_periodo(CU, ded, mes)
    return cr * pr + _exceso_valor(ex, pb), ex


def pesos_mes(x: np.ndarray, mes: np.ndarray) -> dict:
    """{mes: (N,)} el PDE propio: la parte de cada miembro en el total de `x`."""
    x = np.asarray(x, dtype=float)
    mes = np.asarray(mes)
    return {m: compute_pde_weights(x[:, mes == m].sum(axis=1),
                                   method="excedentes_proportional")
            for m in np.unique(mes)}


def colectivo(iny, ret, CU, ded, mes, pb, pesos: dict):
    """Colectivo mensual: el fondo de la hora con el perfil horario de la
    comunidad, la parte de cada miembro contra su importacion con el Anexo 4.
    Devuelve (valor, exceso)."""
    iny = np.asarray(iny, dtype=float)
    N, T = iny.shape
    mes = np.asarray(mes)
    pb = np.asarray(pb, dtype=float).reshape(-1)
    val, exs = np.zeros((N, T)), np.zeros((N, T))
    for m in np.unique(mes):
        h = np.flatnonzero(mes == m)
        w = np.asarray(pesos[m], dtype=float)
        if abs(w.sum() - 1.0) > 1e-9 or (w < 0).any():
            raise ValueError(f"pesos del mes {m} no suman 1")
        asign = w[:, None] * iny[:, h].sum(axis=0)[None, :]
        cr, ex, _ = reparto_anexo4(asign, ret[:, h])
        pr = CU[:, h].mean(axis=1) - ded[:, h].mean(axis=1)
        val[:, h] = cr * pr[:, None] + _exceso_valor(ex, pb[h])
        exs[:, h] = ex
    return val, exs


def liquida_esquina(esquina: str, G, D, v, q, CU, ded1, ded4, mes, pb,
                    pagos: Optional[np.ndarray] = None):
    """(valor (N, T) en COP, exceso (N, T) en kWh) de la esquina, sobre los
    flujos (v vendido, q comprado, (N, T)) de esa misma esquina."""
    if esquina not in ESQUINAS:
        raise ValueError(f"esquina {esquina!r}; se esperaba una de {ESQUINAS}")
    G, D, v, q, CU = (np.asarray(x, dtype=float) for x in (G, D, v, q, CU))
    ded1 = np.asarray(ded1, dtype=float)
    ded4 = np.asarray(ded4, dtype=float)
    s, d = np.maximum(G - D, 0.0), np.maximum(D - G, 0.0)
    if (v > s + 1e-6).any() or (q > d + 1e-6).any():
        raise ValueError("se vende mas que el sobrante o se compra mas que el "
                         "faltante")
    sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
    auto = np.minimum(G, D) * CU
    if esquina == "p2p":
        r, ex = art25(sr, dr, CU, ded1, mes, pb)
        val = auto + CU * q + r
    elif esquina == "solo1":
        r, ex = art25(sr, dr, CU, ded1, mes, pb)
        val = auto + CU * q - ded4 * q + r
    elif esquina == "solo2":
        r, ex = colectivo(sr, dr, CU, ded4, mes, pb, pesos_mes(sr, mes))
        val = auto + CU * q + r
    else:
        r, ex = colectivo(s, d, CU, ded4, mes, pb, pesos_mes(q + sr, mes))
        val = auto + r
    if pagos is not None:
        val = val + np.asarray(pagos, dtype=float)
    if not np.isfinite(val).all():
        raise ValueError("liquidacion de la esquina no finita")
    return val, ex


def c1(G, D, CU, ded1, mes, pb):
    """C1 con las mismas funciones (sin mercado), para las compuertas."""
    G, D, CU = (np.asarray(x, dtype=float) for x in (G, D, CU))
    s, d = np.maximum(G - D, 0.0), np.maximum(D - G, 0.0)
    r, ex = art25(s, d, CU, ded1, mes, pb)
    return np.minimum(G, D) * CU + r, ex
