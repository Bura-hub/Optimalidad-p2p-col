"""
Las opciones de fuera: lo que cada parte obtiene si NO negocia (CAL-47).

La banda dentro de la cual un intercambio entre pares conviene a las dos
partes no es un rango escogido: son las dos opciones de fuera.

  techo_i(k)  lo que el comprador i paga a la red por ese kWh
  piso_j(k)   lo que la red le paga al vendedor j por inyectarlo

El techo es el costo unitario de la institucion en ese mes.

**El piso NO es unico ni constante**, y ese es el punto de este modulo. El
articulo 25 de la Resolucion CREG 174 clasifica al cierre del mes: el
excedente acumulado hasta igualar la importacion del MES ENTERO es credito,
y vale la tarifa menos lo que el comercializador cobra sobre la permuta; lo
que la supera se paga a la bolsa de cada hora desde el corte hx (Anexo 4 de
la Resolucion CREG 101 072, regla transitoria vigente). Lo que se cobra sobre
la permuta depende del tamano de la planta: solo el componente de
comercializar hasta 100 kW, y T+D+Cv+PR+R entre 100 kW y 1 MW.

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


# Umbrales de tamano del articulo 25 de la Resolucion CREG 174 y del limite
# de la autogeneracion a pequena escala (Resolucion UPME 281 de 2015).
LIMITE_NUMERAL_1_KW = 100.0
LIMITE_AGPE_KW = 1000.0


def reparto_anexo4(iny: np.ndarray, ret: np.ndarray,
                   etiqueta_mes: Optional[np.ndarray] = None):
    """Parte la inyeccion en credito y exceso con la regla del Anexo 4.

    Anexo 4 de la Resolucion CREG 101 072 de 2025: hx es la hora en que la
    inyeccion acumulada desde la primera hora del mes iguala o sobrepasa la
    importacion TOTAL del mes. La inyeccion de esa hora se parte; desde ahi
    todo es exceso (C-175, C-177).

    Recibe las series que se le den: brutas en la autogeneracion individual,
    residuales en el mercado entre pares y en el contrato interno (lectura
    comercial, decision D3).

    Parameters
    ----------
    iny, ret : (N, T) inyeccion e importacion, no negativas.
    etiqueta_mes : (T,) etiqueta del periodo de facturacion; None es un solo
        periodo.

    Returns
    -------
    credito, exceso : (N, T), con ``iny == credito + exceso``.
    en_permuta : (N, T) booleana, False desde la hora del corte hasta el fin
        del mes, incluidas las horas sin inyeccion. Es lo que necesita el piso.
    """
    iny = np.asarray(iny, dtype=float)
    ret = np.asarray(ret, dtype=float)
    N, T = iny.shape
    exceso = np.zeros((N, T))
    en_permuta = np.ones((N, T), dtype=bool)
    etiquetas = (np.zeros(T, dtype=int) if etiqueta_mes is None
                 else np.asarray(etiqueta_mes))
    for mes in np.unique(etiquetas):
        idx = np.flatnonzero(etiquetas == mes)
        for n in range(N):
            acum = np.cumsum(iny[n, idx])
            cupo = float(ret[n, idx].sum())
            cruza = acum > cupo
            if cruza.any():
                k = int(np.argmax(cruza))
                exceso[n, idx[k]] = min(iny[n, idx[k]], acum[k] - cupo)
                exceso[n, idx[k + 1:]] = iny[n, idx[k + 1:]]
                en_permuta[n, idx[k:]] = False
    return iny - exceso, exceso, en_permuta


def tramo_permuta(G: np.ndarray, D: np.ndarray, etiqueta_mes: np.ndarray,
                  iny: Optional[np.ndarray] = None,
                  ret: Optional[np.ndarray] = None) -> np.ndarray:
    """Matriz booleana (N, T): ¿esta el agente n todavia en permuta en k?

    Envoltorio de `reparto_anexo4`. Sin `iny` ni `ret` usa el excedente y el
    deficit brutos de G y D; con ellos, las series que se le pasen.
    """
    if iny is None:
        iny = np.maximum(G - D, 0.0)
    if ret is None:
        ret = np.maximum(D - G, 0.0)
    return reparto_anexo4(iny, ret, etiqueta_mes)[2]


def residual_proporcional(G: np.ndarray, D: np.ndarray):
    """Inyeccion e importacion que quedan tras colocar el lado corto dentro.

    Por D-7 lo transado en cada hora es el minimo entre oferta y demanda netas
    y no depende del precio. Se reparte entre vendedores en proporcion a su
    excedente y entre compradores en proporcion a su deficit. El agregado es
    exacto; el reparto es una aproximacion del que da la partida (H-53).
    """
    exc = np.maximum(G - D, 0.0)
    dfc = np.maximum(D - G, 0.0)
    oferta, demanda = exc.sum(axis=0), dfc.sum(axis=0)
    corto = np.minimum(oferta, demanda)
    with np.errstate(invalid="ignore", divide="ignore"):
        fv = np.where(oferta > 1e-9, corto / oferta, 0.0)
        fc = np.where(demanda > 1e-9, corto / demanda, 0.0)
    return exc * (1.0 - fv)[None, :], dfc * (1.0 - fc)[None, :]


def deduccion_art25(cvm: np.ndarray, tolls: Optional[np.ndarray],
                    capacidad_kw: Optional[np.ndarray]) -> np.ndarray:
    """Lo que el comercializador cobra por cada kWh permutado, (N, T).

    Articulo 25 de la Resolucion CREG 174: hasta 100 kW, el componente de
    comercializar Cv; entre 100 kW y 1 MW, el agregado T+D+Cv+PR+R. Por
    encima de 1 MW la planta deja de ser autogeneracion a pequena escala.
    Con `capacidad_kw` None se aplica el numeral 1 a todos.

    Los peajes de las filas del numeral 2 tienen que ser finitos: un NaN (mes
    ausente de la tabla) se rechaza con error en vez de aceptar un relleno,
    que liquidaria el numeral 2 con un valor que no es el publicado.
    """
    cvm = np.asarray(cvm, dtype=float)
    if capacidad_kw is None:
        return cvm.copy()
    cap = np.asarray(capacidad_kw, dtype=float).reshape(-1)
    if (cap > LIMITE_AGPE_KW).any():
        raise ValueError(
            f"capacidad {cap.max():.1f} kW por encima de {LIMITE_AGPE_KW:.0f} kW: "
            "ya no es AGPE y el articulo 25 no aplica")
    grande = cap > LIMITE_NUMERAL_1_KW
    out = cvm.copy()
    if grande.any():
        if tolls is None:
            raise ValueError(
                "hay plantas de mas de 100 kW y no se pasaron los peajes "
                "T+D+PR+R que cobra el numeral 2 del articulo 25")
        t = np.broadcast_to(np.asarray(tolls, dtype=float), cvm.shape)
        malos = ~np.isfinite(t[grande, :])
        if malos.any():
            raise ValueError(
                f"los peajes T+D+PR+R tienen {int(malos.sum())} valores no "
                "finitos en las plantas de mas de 100 kW; el numeral 2 del "
                "articulo 25 no se liquida con un relleno (revisar la tabla "
                "de tarifas del mes)")
        out[grande, :] = cvm[grande, :] + t[grande, :]
    return out


def precio_permuta_por_periodo(pi_gs_v: np.ndarray, deduccion: np.ndarray,
                               etiqueta_mes: Optional[np.ndarray] = None
                               ) -> np.ndarray:
    """Valor (N, T) de un kWh de credito: tarifa media del periodo menos la
    deduccion media del periodo, igual que liquida C1."""
    pi_gs_v = np.asarray(pi_gs_v, dtype=float)
    deduccion = np.asarray(deduccion, dtype=float)
    N, T = pi_gs_v.shape
    out = np.empty((N, T))
    etiquetas = (np.zeros(T, dtype=int) if etiqueta_mes is None
                 else np.asarray(etiqueta_mes))
    for mes in np.unique(etiquetas):
        idx = np.flatnonzero(etiquetas == mes)
        for n in range(N):
            out[n, idx] = (float(pi_gs_v[n, idx].mean())
                           - float(deduccion[n, idx].mean()))
    return out


def piso_residual(G, D, cu, deduccion, bolsa, etiqueta_mes):
    """Piso de cada vendedor: permuta antes de su corte hx calculado sobre las
    residuales, bolsa de la hora desde hx (spec 4.3). Devuelve (piso, en_permuta).

    Supuesto declarado: fijar el piso exige los totales del mes, que en la
    realidad solo se conocen al cierre; es una liquidacion sobre datos medidos.
    """
    iny_r, ret_r = residual_proporcional(G, D)
    en_permuta = tramo_permuta(G, D, etiqueta_mes, iny=iny_r, ret=ret_r)
    return piso_por_vendedor(cu, deduccion, bolsa, en_permuta), en_permuta


def piso_por_vendedor(cu: np.ndarray, deduccion: np.ndarray, bolsa: np.ndarray,
                      en_permuta: np.ndarray) -> np.ndarray:
    """Matriz (N, T) con la opcion de fuera de cada vendedor en cada hora.

    En permuta vale la tarifa menos lo que el comercializador cobra sobre lo
    permutado (`deduccion_art25`); fuera de permuta, la bolsa de esa hora.
    """
    return np.where(en_permuta, cu - deduccion, bolsa[None, :])


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
