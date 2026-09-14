"""
El mercado entre pares liquidado por la via del colectivo (D8, H-76).

QUE MIDE. Cuanto del valor del mercado entre pares sobrevive si se lleva a la
practica por la unica via legal disponible hoy: la arquitectura de dos niveles
del asesor regulatorio y del asesor academico. En el primer nivel la comunidad
es un autogenerador colectivo que liquida con la Resolucion CREG 101 072; en
el segundo, el mercado decide hora a hora quien recibe que energia y a que
precio, y el dinero se ajusta entre los miembros por contrato.

COMO SE LIQUIDA.
  1. El porcentaje de cada miembro en cada mes es la energia que termina
     siendo suya dentro del fondo comun: la comprada dentro mas la exportada
     sin colocar, sobre el total exportado por la comunidad. Suma cien por
     construccion y se puede reportar cada mes (articulo 19).
  2. La liquidacion regulatoria es la del colectivo mensual con ese
     porcentaje, contra la importacion que registra el MEDIDOR de cada
     miembro, con lo que el articulo 20 cobre sobre lo permutado.
  3. El ajuste por contrato son los pagos internos del mercado, al precio de
     cada intercambio con el techo del comprador (CAL-35). Suman cero: no
     cambian el total, reparten.

LO QUE SE ESPERA, y la corrida debe confirmarlo o desmentirlo: con la misma
tarifa y sin cupos agotados, reasignar creditos no crea valor; con cinco
fronteras el caso caro lo deja por debajo de la autogeneracion individual.

Actividad 2.2.
"""
from __future__ import annotations

from typing import Optional, Union

import numpy as np

from ._pi_gs import as_pi_gs_array
from .scenario_c4_creg101072 import compute_pde_weights, run_c4_creg101072


def _flujos(p2p_results, N, T):
    """Comprado y vendido (N, T) por agente y hora, con la hora de r.k."""
    comprado = np.zeros((N, T))
    vendido = np.zeros((N, T))
    for r in p2p_results:
        if r.P_star is None or not r.seller_ids:
            continue
        P = np.asarray(r.P_star, dtype=float)
        if np.isnan(P).any():
            continue
        for a, j in enumerate(r.seller_ids):
            vendido[j, r.k] += float(P[a, :].sum())
        for b, i in enumerate(r.buyer_ids):
            comprado[i, r.k] += float(P[:, b].sum())
    return comprado, vendido


def pde_mensual_desde_mercado(p2p_results, D, G,
                              month_labels: Optional[np.ndarray] = None
                              ) -> dict:
    """{mes: (N,)} con la energia que termina siendo de cada miembro."""
    D = np.asarray(D, dtype=float)
    G = np.asarray(G, dtype=float)
    N, T = D.shape
    comprado, vendido = _flujos(p2p_results, N, T)
    surplus = np.maximum(np.maximum(G, 0.0) - np.maximum(D, 0.0), 0.0)
    propio = comprado + np.maximum(surplus - vendido, 0.0)
    etiquetas = (np.zeros(T, dtype=int) if month_labels is None
                 else np.asarray(month_labels))
    out = {}
    for mes in np.unique(etiquetas):
        idx = np.flatnonzero(etiquetas == mes)
        out[int(mes)] = compute_pde_weights(propio[:, idx].sum(axis=1),
                                            method="excedentes_proportional")
    return out


def run_p2p_colectivo(p2p_results, D, G, pi_gs, pi_bolsa,
                      month_labels: Optional[np.ndarray] = None,
                      component_c: Union[str, float, np.ndarray] = "auto",
                      tolls: Union[float, np.ndarray, None] = None,
                      capacity: Optional[np.ndarray] = None,
                      caso: Union[int, str] = "auto",
                      dt: float = 1.0) -> dict:
    """Liquida el mercado por la via del colectivo. Ver el docstring del modulo."""
    D = np.asarray(D, dtype=float)
    G = np.asarray(G, dtype=float)
    N, T = D.shape
    pi_gs_v = as_pi_gs_array(pi_gs, N, T)
    pm = pde_mensual_desde_mercado(p2p_results, D, G, month_labels)
    c4 = run_c4_creg101072(D, G, pi_gs_v, pi_bolsa, np.full(N, 1.0 / N),
                           capacity, component_c=component_c, tolls=tolls,
                           mode="monthly_hx", month_labels=month_labels,
                           caso=caso, pde_mensual=pm, dt=dt)
    pagos = np.zeros(N)
    pagos_h = np.zeros((N, T))
    for r in p2p_results:
        if r.P_star is None or r.pi_star is None or not r.seller_ids:
            continue
        P = np.asarray(r.P_star, dtype=float)
        pi = np.asarray(r.pi_star, dtype=float)
        if np.isnan(P).any() or np.isnan(pi).any():
            continue
        for b, i in enumerate(r.buyer_ids):
            precio = min(float(pi[b]), float(pi_gs_v[i, r.k]))
            for a, j in enumerate(r.seller_ids):
                dinero = precio * float(P[a, b]) * dt
                pagos[j] += dinero
                pagos[i] -= dinero
                pagos_h[j, r.k] += dinero
                pagos_h[i, r.k] -= dinero
    neto = np.array([c4["per_agent"][n]["net_benefit"] for n in range(N)]) + pagos
    return {
        "per_agent": {n: {"net_benefit": float(neto[n]),
                          "colectivo": float(neto[n] - pagos[n]),
                          "pagos_internos": float(pagos[n])}
                      for n in range(N)},
        "neto_horario": c4["neto_horario"] + pagos_h,
        "aggregate": {"total_net_benefit": float(neto.sum())},
        "pagos_internos": pagos,
        "pde_por_mes": pm,
        "caso_art20": int(c4["caso_art20"]),
    }
