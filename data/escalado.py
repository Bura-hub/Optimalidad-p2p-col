"""
El escalado controlado de la comunidad (decisiones D10 a D12, spec 4.11).

Sustituye a la segunda frontera: en vez de cambiar de medidor, se multiplica
la generacion, la demanda, o la generacion de una sola institucion, justo
despues de cargar las series. Todo lo demas (tarifa, cotas, porcentajes,
casos regulatorios, capacidad instalada) se rearma sobre las series escaladas.

«neto_cero» es el factor que iguala la generacion de la institucion a su
consumo sobre el horizonte cargado: es como se dimensiona una planta para
cubrir el consumo anual.

Actividad 4.1.
"""
from __future__ import annotations

from typing import Optional, Union

import numpy as np


def lee_factor(texto: str) -> float:
    """«7», «0.5» o «1/7»."""
    texto = str(texto).strip()
    if "/" in texto:
        a, b = texto.split("/", 1)
        return float(a) / float(b)
    return float(texto)


def lee_escala_agente(texto: Optional[str]) -> dict:
    """«UCC:neto_cero,Udenar:2» -> {"UCC": "neto_cero", "Udenar": 2.0}."""
    out: dict = {}
    for par in (texto or "").split(","):
        if not par.strip():
            continue
        nombre, valor = par.split(":", 1)
        valor = valor.strip()
        out[nombre.strip()] = ("neto_cero" if valor == "neto_cero"
                               else lee_factor(valor))
    return out


def _neto_cero(D_n: np.ndarray, G_n: np.ndarray) -> float:
    g = float(np.maximum(G_n, 0.0).sum())
    if g <= 0.0:
        raise ValueError("una institucion sin generacion no tiene neto cero")
    return float(np.maximum(D_n, 0.0).sum()) / g


def escala_comunidad(D: np.ndarray, G: np.ndarray, nombres,
                     factor_generacion: float = 1.0,
                     factor_demanda: float = 1.0,
                     generacion_por_agente: Optional[
                         dict[str, Union[float, str]]] = None,
                     neto_cero: bool = False):
    """Devuelve (D, G, factores_g) escalados; factores_g es (N,).

    El factor por institucion sustituye al uniforme para esa institucion. Un
    nombre que no este entre los miembros detiene todo en voz alta.
    """
    D = np.asarray(D, dtype=float) * float(factor_demanda)
    G = np.asarray(G, dtype=float)
    N = G.shape[0]
    f = np.full(N, float(factor_generacion))
    if neto_cero:
        f = np.array([_neto_cero(D[n], G[n]) for n in range(N)])
    for nombre, valor in (generacion_por_agente or {}).items():
        if nombre not in nombres:
            raise ValueError(f"{nombre} no esta entre {list(nombres)}")
        n = list(nombres).index(nombre)
        f[n] = (_neto_cero(D[n], G[n]) if valor == "neto_cero"
                else float(valor))
    return D, G * f[:, None], f
