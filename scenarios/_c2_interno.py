"""
El contrato bilateral interno: el mismo mercado con precio fijo (CAL-52).

QUE MODELA. Los miembros de la comunidad intercambian la misma energia que
intercambiarian en el mercado entre pares, pero **a un precio pactado de
antemano** en vez de a uno formado por el juego. Es un contrato de suministro
a largo plazo entre vecinos: lo que un PPA hace, que es fijar el precio y
quitar la incertidumbre.

POR QUE ES LA COMPARACION QUE LE FALTABA A LA TESIS. Aisla **exactamente** lo
que aporta el mecanismo dinamico. Mismos flujos, misma comunidad, misma
energia: lo unico que cambia es como se forma el precio.

  · Si el contrato a precio fijo da lo mismo que el juego, entonces la
    dinamica de replicador y la relajacion lagrangiana **no estan aportando
    nada**, y eso hay que saberlo antes de que lo pregunte un jurado.
  · Si da menos, ahi esta el valor del mecanismo, y se puede cuantificar.

EL PRECIO, y no tiene parametros libres. Cada pareja contrata en **el punto
medio de su propia banda**:

    pi_ji = ( techo_i + piso_j ) / 2

Es decir, a mitad de camino entre lo que el comprador pagaria a la red y lo
que la red le pagaria al vendedor. Reparte la banda **a la mitad**, de modo
que el ahorro del comprador y la prima del vendedor son iguales por
construccion.

De ahi una propiedad que lo vuelve un patron util: **su indice de equidad es
cero exacto**. Es el reparto perfectamente equitativo, y el mercado entre
pares se mide contra el.

Y POR LA IDENTIDAD DE H-33, el excedente total **no cambia**: el ancho de la
banda por la energia es el mismo se pacte el precio que se pacte. Lo que
cambia es el reparto. De modo que esta comparacion mide **si el mecanismo
reparte mejor o peor que una regla fija**, que es justo la pregunta que el
modelo base plantea con su indice de equidad.

LA PAREJA QUE NO FIRMA. Nada garantiza que el techo del comprador este por
encima del piso del vendedor: son dos agentes distintos con dos tarifas
distintas. Cuando el piso queda por encima del techo **la banda esta invertida**
y no hay precio que deje a los dos mejor que yendo a la red; el punto medio
caeria fuera de las dos cotas. Ese contrato no se firma, y la energia se trata
como la que el mercado no coloca: va a bolsa.

Medido sobre el horizonte (H-64): la banda se invierte en el 0,036 % de las
parejas-hora de la primera frontera y en el 1,900 % de la segunda, pero **en
ninguna pareja con papeles compatibles**, es decir en ninguna que pudiera
transar. Hoy no muerde. La guarda esta porque manana, con otra frontera u otra
tarifa, si podria.

QUE NO MODELA, y conviene decirlo. No es la venta a un tercero del articulo 23
numeral 2 literal a; eso es otra alternativa del mismo articulo, con su propio
precio de mercado, y quedo medida y registrada en H-63 sin adoptarse.
"""
from __future__ import annotations

import numpy as np


def contrato_interno(flujos_por_hora, techo, piso, N: int,
                     dt: float = 1.0) -> dict:
    """Liquida los mismos flujos a precio pactado, no negociado.

    Parameters
    ----------
    flujos_por_hora : iterable de (k, sids, bids, P)
        Lo que el mercado entre pares asigno en cada hora. Se reutiliza a
        proposito: la pregunta es que aporta la FORMACION del precio, no el
        reparto de la energia, que por D-7 es el lado corto y no depende del
        precio.
    techo : (N, T) lo que cada comprador paga a la red.
    piso  : (N, T) lo que la red le paga a cada vendedor.
    N : numero de agentes.
    dt : duracion del paso en horas (CAL-46).

    Returns
    -------
    dict con el ingreso del vendedor, el ahorro del comprador, el precio medio
    ponderado y el excedente, todo por agente y agregado.
    """
    techo = np.asarray(techo, dtype=float)
    piso = np.asarray(piso, dtype=float)
    T = techo.shape[1]
    ingreso = np.zeros(N)        # prima del vendedor sobre SU piso
    ahorro = np.zeros(N)         # ahorro del comprador contra SU techo
    energia = np.zeros(N)
    # La energia que el mercado asigno a una pareja que NO firma. El motor la
    # cuenta como colocada; para el contrato no lo esta, y hay que devolverla
    # al residual o se perderia de la contabilidad.
    sin_firmar = np.zeros((N, T))
    # C-165: el excedente del contrato a la hora que lo genera, repartido
    # entre las dos partes de cada intercambio.
    neto_horario = np.zeros((N, T))
    val, kwh, parejas_rotas = 0.0, 0.0, 0

    for k, sids, bids, P in flujos_por_hora:
        P = np.asarray(P, dtype=float)
        if P.size == 0:
            continue
        for a, j in enumerate(sids):
            for b, i in enumerate(bids):
                e = float(P[a, b])
                if e <= 0.0:
                    continue
                te = float(techo[i, k])
                pi_ = float(piso[j, k])
                if te < pi_:
                    # Banda invertida: no hay precio que deje a los dos
                    # mejor que la red. Nadie firma eso.
                    sin_firmar[j, k] += e
                    parejas_rotas += 1
                    continue
                # El punto medio de la banda de ESA pareja. Sin parametros.
                precio = 0.5 * (te + pi_)
                ingreso[j] += (precio - pi_) * e
                ahorro[i] += (te - precio) * e
                neto_horario[j, k] += (precio - pi_) * e
                neto_horario[i, k] += (te - precio) * e
                energia[j] += e
                val += precio * e
                kwh += e

    if dt != 1.0:
        ingreso *= dt
        ahorro *= dt
        energia *= dt
        sin_firmar *= dt
        neto_horario *= dt
        val *= dt
        kwh *= dt

    total = float(np.sum(ingreso) + np.sum(ahorro))
    return dict(
        ingreso_vendedor=ingreso,
        ahorro_comprador=ahorro,
        energia_vendida=energia,
        excedente=total,
        kwh=float(kwh),
        sin_firmar=sin_firmar,
        neto_horario=neto_horario,
        parejas_sin_firmar=int(parejas_rotas),
        precio_medio=(float(val / kwh) if kwh > 1e-12 else float("nan")),
        # Cero exacto por construccion: el punto medio reparte la banda a la
        # mitad. Se calcula igualmente para que la compuerta lo compruebe en
        # vez de darlo por supuesto.
        equidad=((float(np.sum(ahorro)) - float(np.sum(ingreso))) / total
                 if abs(total) > 1e-12 else float("nan")),
    )
