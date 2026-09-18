"""Los dos casos publicados de Chacon et al. (2025), para la medicion M-G.

QUE ES. Las Tablas II (14:00) y IV (22:00) del documento extenso, con la
clasificacion de `Documentos/copy/JoinFinal.m` (lineas 50 a 59): un agente es
comprador si Glim/Dopt <= 1, con deficit Dopt - Glim, y vendedor si >= 1, con
excedente Glim - Dopt. La banda es escalar (114 a 1 250 (COP/kWh), aunque en
el modelo base es adimensional) y los costos son los de `JoinFinal.m`, los
mismos que `data/base_case_data.py`.

DE DONDE VIENE. De `scratchpad/revision_chacon/literal.py`, la traduccion
literal que se uso en la sonda del consenso; aqui solo esta la parte de los
casos publicados, sin el integrador literal, que no hace falta.

POR QUE ESTA AQUI Y NO SE IMPORTA. Los literales de las 22:00 estan tambien en
`tests/test_reposo_mercado.py` (`GLIM_22`, `DOPT_22`, `B_CHACON`), que es una
prueba y no una biblioteca; los de las 14:00 no estan en ninguna otra parte del
arbol. `tests/test_arnes_consenso.py` comprueba que los de aqui coinciden con
los de alli, de modo que una copia que se desvie se ve.

SIN DATOS REALES: solo literales publicados.
"""
import sys

import numpy as np

SCALE = 6.0865
A_ALL = SCALE * np.array([4 * 0.089, 0.069, 0, 0, 0, 0])
B_ALL = SCALE * np.array([3.93 * 52, 32, 47, 37, 0, 0])

# Tabla II (14:00) y Tabla IV (22:00) del documento extenso
CASO14 = dict(Glim=np.array([2.844, 3.738, 0.539, 0.624, 0.0, 0.0]),
              Dopt=np.array([1.183, 0.516, 0.56, 3.467, 0.259, 0.114]))
CASO22 = dict(Glim=np.array([2.844, 0.770, 0.0, 1.760, 0.0, 0.0]),
              Dopt=np.array([3.421, 1.295, 0.534, 0.379, 0.262, 0.208]))


def prepara(Glim, Dopt, etha_all=None, Pgs=1250.0, Pgb=114.0,
            a_all=A_ALL, b_all=B_ALL):
    """Quien compra, quien vende, y con que cantidades y costos.

    La clasificacion es la de `JoinFinal.m` al pie de la letra, y el resultado
    no se cambia. Pero un agente con Glim = Dopt = 0 da 0/0 = NaN, que no es ni
    <= 1 ni >= 1: queda fuera de los dos lados sin que nadie lo diga. Eso era un
    fallo mudo (menor 4 de la revision de 4c): ahora se AVISA por la salida de
    errores, con el agente y el motivo, y se devuelve en `sin_papel`. Por la
    salida de errores y no con `warnings`, porque el lanzador corre Python con
    `-W ignore` y un aviso de `warnings` no llegaria al registro. En las dos
    horas publicadas no ocurre.
    """
    Glim = np.asarray(Glim, float)
    Dopt = np.asarray(Dopt, float)
    etha_all = np.full(6, 0.1) if etha_all is None else np.asarray(etha_all, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = Glim / Dopt
    cb = r <= 1
    cs = r >= 1
    sin_papel = []
    for k in np.where(~(cb | cs))[0]:
        motivo = (f"Glim = {Glim[k]:g} y Dopt = {Dopt[k]:g}: el cociente "
                  f"Glim/Dopt es {r[k]!r}, que no es ni <= 1 (comprador) ni "
                  f">= 1 (vendedor)")
        sin_papel.append(dict(agente=f"ag{k + 1}", indice=int(k),
                              motivo=motivo))
        print(f"  AVISO caso_publicado_chacon: el agente ag{k + 1} queda FUERA "
              f"del mercado ({motivo}); asi lo clasifica JoinFinal.m y no se "
              f"cambia", file=sys.stderr, flush=True)
    return dict(
        compradores=np.where(cb)[0], vendedores=np.where(cs)[0],
        Di=Dopt[cb] - Glim[cb], Gj=Glim[cs] - Dopt[cs],
        etha=etha_all[cb], a=np.asarray(a_all, float)[cs],
        b=np.asarray(b_all, float)[cs], Pgs=Pgs, Pgb=Pgb,
        sin_papel=sin_papel)
