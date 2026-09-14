"""
El factor de coincidencia (D20): cuanto de lo que cada mecanismo acredita
como si sustituyera importacion coincidio en la hora con la importacion
contra la que se acredita (opcion C), y la simultaneidad de los picos de
importacion de la comunidad (opcion B). Decision del autor del 2026-09-13;
ver docs/superpowers/specs/2026-09-13-factor-coincidencia-opciones.md.

Opcion C. Para cada miembro y mes, la energia ACREDITADA es la que la
liquidacion valora contra una importacion, con el corte del Anexo 4; la
COINCIDENTE es la parte que cayo en la misma hora que esa importacion,
topada por lo acreditado:

    coincidente = min( suma_k min(asignada_k, importada_k), acreditada )

Por la desigualdad del minimo el factor cae entre cero y uno. Con demanda
fija la fisica es la misma en todos los mecanismos: lo que cambia es la
regla con que cada uno acredita.

  C1   se acredita su propia inyeccion contra su importacion del mes. Una
       frontera no inyecta e importa en la misma hora: factor cero, todo el
       credito de la permuta lo respalda la red.
  C4   su porcentaje por la inyeccion horaria del colectivo, que es el
       perfil que el motor supone para la asignacion (C-178).
  P2P  lo transado dentro coincide por construccion (D-7); el residual se
       acredita por el articulo 25, con factor cero como en C1.
  C2   como el P2P, pero lo que la pareja no firma vuelve al residual. Solo
       se calcula con el contrato interno.
  C5   el contrato despachado cada hora es el minimo horario (art. 19 de la
       CREG 101 099): factor uno.
  C3   no acredita nada contra importacion: no aplica (NaN).
  P2P_colectivo  la liquidacion regulatoria es la del colectivo con el
       porcentaje que sale del mercado: el mismo calculo que C4.

Opcion B. El pico de la importacion neta de la comunidad entre la suma de
los picos de importacion de cada miembro. Es de la comunidad, no del
mecanismo, y se mueve con la matriz de escalado.

El factor es una razon de energias, de modo que no depende de la duracion
del paso.

Actividad 3.2.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from core.opciones_externas import reparto_anexo4


def _meses(month_labels, T: int) -> list:
    """[(mes, indices)] de cada periodo de facturacion."""
    et = (np.zeros(T, dtype=int) if month_labels is None
          else np.asarray(month_labels))
    return [(int(m), np.flatnonzero(et == m)) for m in np.unique(et)]


def _cuenta_mes(asignada: np.ndarray, importada: np.ndarray) -> tuple:
    """(coincidente, acreditada) de un mes, topando miembro a miembro."""
    credito = reparto_anexo4(asignada, importada)[0]
    acred_n = credito.sum(axis=1)
    coinc_n = np.minimum(asignada, importada).sum(axis=1)
    return float(np.minimum(coinc_n, acred_n).sum()), float(acred_n.sum())


def _razon(pares: list) -> float:
    coinc = sum(p[0] for p in pares)
    acred = sum(p[1] for p in pares)
    return coinc / acred if acred > 1e-12 else float("nan")


def coincidencia_por_mecanismo(D, G, p2p_results,
                               month_labels=None,
                               pde: Optional[np.ndarray] = None,
                               pde_colectivo: Optional[dict] = None,
                               sin_firmar: Optional[np.ndarray] = None,
                               sin_firmar_comprador: Optional[np.ndarray] = None,
                               include_c5: bool = False) -> dict:
    """{escenario: factor} de la opcion C. Ver el docstring del modulo.

    D, G : (N, T) demanda y generacion; la limitada, como la liquidacion.
    p2p_results : HourlyResult alineados con las columnas por `r.k`.
    pde : (N,) porcentaje del colectivo; None es igual para todos.
    pde_colectivo : {mes: (N,)} del mercado por la via del colectivo.
    sin_firmar, sin_firmar_comprador : (N, T) lo que el contrato interno no
        firma, en las unidades de P_star (kW del paso). None si no hay
        contrato interno; entonces no se calcula C2.
    """
    from scenarios.scenario_p2p_colectivo import _flujos

    D = np.asarray(D, dtype=float)
    G = np.asarray(G, dtype=float)
    N, T = D.shape
    meses = _meses(month_labels, T)
    exc = np.maximum(np.maximum(G, 0.0) - np.maximum(D, 0.0), 0.0)
    imp = np.maximum(np.maximum(D, 0.0) - np.maximum(G, 0.0), 0.0)
    S = exc.sum(axis=0)
    out: dict = {}

    out["C1"] = _razon([_cuenta_mes(exc[:, i], imp[:, i]) for _, i in meses])

    p = (np.full(N, 1.0 / N) if pde is None
         else np.asarray(pde, dtype=float))
    out["C4"] = _razon([_cuenta_mes(p[:, None] * S[None, i], imp[:, i])
                        for _, i in meses])

    comprado, vendido = _flujos(p2p_results, N, T)

    def _mercado(comprado, vendido):
        iny_r = np.maximum(exc - vendido, 0.0)
        ret_r = np.maximum(imp - comprado, 0.0)
        pares = [_cuenta_mes(iny_r[:, i], ret_r[:, i]) for _, i in meses]
        dentro = float(comprado.sum())
        pares.append((dentro, dentro))       # lo transado coincide (D-7)
        return _razon(pares)

    out["P2P"] = _mercado(comprado, vendido)
    if sin_firmar is not None:
        out["C2"] = _mercado(
            np.maximum(comprado - np.asarray(sin_firmar_comprador, float), 0.0),
            np.maximum(vendido - np.asarray(sin_firmar, float), 0.0))
    out["C3"] = float("nan")
    if include_c5:
        q = float(np.minimum(S, imp.sum(axis=0)).sum())
        out["C5"] = 1.0 if q > 1e-12 else float("nan")
    if pde_colectivo is not None:
        out["P2P_colectivo"] = _razon([
            _cuenta_mes(np.asarray(pde_colectivo[m], dtype=float)[:, None]
                        * S[None, i], imp[:, i])
            for m, i in meses])
    return out


def simultaneidad_picos(D, G) -> float:
    """Pico de la importacion neta de la comunidad entre la suma de picos."""
    neto = np.maximum(np.asarray(D, float), 0.0) - np.maximum(
        np.asarray(G, float), 0.0)
    pico_ind = float(np.maximum(neto, 0.0).max(axis=1).sum())
    pico_com = max(float(neto.sum(axis=0).max()), 0.0)
    return pico_com / pico_ind if pico_ind > 1e-12 else float("nan")
