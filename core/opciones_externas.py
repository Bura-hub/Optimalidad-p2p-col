"""
Las opciones de fuera: lo que cada parte obtiene si NO negocia (CAL-47).

La banda dentro de la cual un intercambio entre pares conviene a las dos
partes no es un rango escogido: son las dos opciones de fuera.

  techo_i(k)  lo que el comprador i paga a la red por ese kWh
  piso_j(k)   lo que la red le paga al vendedor j por inyectarlo

El techo es el costo unitario de la institucion en ese mes.

**El piso NO es unico ni constante**, y ese es el punto de este modulo. La
Resolucion CREG 174 liquida el excedente en dos tramos: mientras la
inyeccion acumulada del mes no supere el retiro acumulado, el excedente
cierra una permuta y vale la tarifa menos el componente de comercializacion;
a partir del cruce se vende al mercado mayorista. De modo que el piso
**depende del agente y de su estado dentro del mes**.

Medido sobre el horizonte, el reparto entre tramos separa a las dos
fronteras y lo hace en direcciones opuestas:

    frontera principal   69,0 % permuta   31,0 % a bolsa
    frontera secundaria  10,9 % permuta   89,1 % a bolsa

Un piso escalar, por tanto, se equivoca en las dos y en sentidos contrarios.

Consecuencia economica, y es la que ordena el capitulo de precios. Para un
kWh de excedente que casa con un kWh de deficit, el pago neto de la
comunidad a la red es:

    sin mercado, en permuta   CU - (CU - C) = C
    sin mercado, en bolsa     CU - bolsa
    con mercado               0

es decir, **el mercado ahorra exactamente el ancho de la banda**, que es el
cargo de comercializar en el primer regimen y mucho mas en el segundo.
"""
from __future__ import annotations

from typing import Optional

import numpy as np


def tramo_permuta(G: np.ndarray, D: np.ndarray,
                  etiqueta_mes: np.ndarray) -> np.ndarray:
    """Matriz booleana (N, T): ¿está el agente n todavía en permuta en k?

    Replica la mecánica de los artículos 22 y 23 de la Resolución CREG 174
    tal como la implementa el escenario individual: dentro de cada mes se
    acumulan inyección y retiro hora a hora, y **en cuanto la inyección
    acumulada supera al retiro acumulado, el agente pasa a mercado
    mayorista para el resto del mes**.

    Parameters
    ----------
    G, D : (N, T) generación y demanda en kW.
    etiqueta_mes : (T,) etiqueta de mes por hora, p. ej. "2025-04".
    """
    N, T = D.shape
    excedente = np.maximum(G - D, 0.0)
    deficit = np.maximum(D - G, 0.0)
    en_permuta = np.ones((N, T), dtype=bool)

    for mes in np.unique(etiqueta_mes):
        sel = etiqueta_mes == mes
        for n in range(N):
            inyecta = np.cumsum(excedente[n, sel])
            retira = np.cumsum(deficit[n, sel])
            cruza = inyecta > retira
            if cruza.any():
                k = int(np.argmax(cruza))
                idx = np.flatnonzero(sel)
                en_permuta[n, idx[k:]] = False
    return en_permuta


def piso_por_vendedor(cu: np.ndarray, cvm: np.ndarray, bolsa: np.ndarray,
                      en_permuta: np.ndarray) -> np.ndarray:
    """Matriz (N, T) con la opción de fuera de cada vendedor en cada hora.

    En permuta vale ``cu - cvm``, es decir la tarifa menos el componente de
    comercialización, porque el kWh inyectado descuenta un kWh consumido y
    sobre esa permuta el comercializador sí factura su cargo. Fuera de
    permuta vale el precio de bolsa de esa hora.
    """
    return np.where(en_permuta, cu - cvm, bolsa[None, :])


def piso_comunitario(piso_nk: np.ndarray, G: np.ndarray,
                     D: np.ndarray) -> np.ndarray:
    """Vector (T,) con un solo piso por hora, para la dinámica del juego.

    El juego forma **un** precio de mercado, de modo que necesita una sola
    cota inferior por hora. Se toma la media de las opciones de fuera de los
    vendedores activos, **ponderada por el excedente que cada uno aporta**,
    que es la agregación que conserva el excedente total de la hora.

    Es una aproximación y hay que declararla: cada vendedor conserva su
    propio piso en la liquidación, de modo que la prima que se le reconoce
    se mide contra su alternativa y no contra la media.

    Las horas sin vendedor activo devuelven la media simple de los pisos, un
    valor que no se usa porque esas horas no abren mercado.
    """
    excedente = np.maximum(G - D, 0.0)
    peso = excedente.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        agregado = (piso_nk * excedente).sum(axis=0) / peso
    sin_oferta = ~np.isfinite(agregado)
    agregado[sin_oferta] = piso_nk[:, sin_oferta].mean(axis=0)
    return agregado


def banda_vacia(techo: np.ndarray, piso: np.ndarray) -> np.ndarray:
    """Vector (T,) booleano: horas en que ninguna transacción conviene.

    Ocurre cuando la opción de fuera del vendedor iguala o supera lo que el
    comprador paga a la red. Entonces el vendedor prefiere inyectar y el
    comprador prefiere importar, y **el mercado no debe abrir esa hora**.
    """
    return piso >= techo


def resumen(en_permuta: np.ndarray, G: np.ndarray,
            D: np.ndarray, nombres: Optional[list] = None) -> dict:
    """Reparto del excedente entre los dos tramos, por agente y comunidad."""
    excedente = np.maximum(G - D, 0.0)
    N = excedente.shape[0]
    nombres = nombres or [f"A{n + 1}" for n in range(N)]
    out = {}
    for n in range(N):
        tot = float(excedente[n].sum())
        perm = float(excedente[n][en_permuta[n]].sum())
        out[nombres[n]] = (perm / tot if tot else 0.0, tot)
    tot = float(excedente.sum())
    perm = float(excedente[en_permuta].sum())
    out["_comunidad"] = (perm / tot if tot else 0.0, tot)
    return out
