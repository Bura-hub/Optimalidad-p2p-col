"""M-G repetida con el tope que le falto: el caso de la autora (CA).

Actividad 1.1.

QUE ES. La tesis dice que la integracion del caso de la autora (el de seis
agentes de Chacon et al., sus dos horas publicadas, 22:00 y 14:00) con la
dinamica regularizada termino sin lectura. Fue M-G (`medicion_chacon.py`), la
noche del 18 de septiembre de 2026 (`validacion_reposo_m_g_2026-09-18_1411.log`
de la entrega de intentos, hoy en `_cuarentena/2026-10-05/`): ocho corridas,
dos horas x dos formas del jugador virtual x dos aceleraciones (k = 1 y
k = 100), con un tope de 3 600 s cada una. Seis se cortaron por el tope y dos
(las de las 14:00 con k = 100) se cortaron al arrancar por un valor no finito.
En ninguna el estado final estaba quieto, de modo que no se leyo contra la
tabla.

LO QUE DICE AQUEL REGISTRO, corrida por corrida, y por que esta repeticion es
la que es:

  - 22:00, barrera, k = 100: en teq 40 (2 266 s) estaba en la forma cerrada
    (|dp| = 2,2e-3 COP/kWh, |dq| = 4,3e-7 kWh) con |dq/dt| = 1,2e-3, apenas
    sobre el 1e-3 de la quietud; el tope la corto entre teq 40 y 80. Con un
    tope suficiente llega a teq 160: cada duplicacion de teq costo ~3 veces la
    anterior (769 s en teq 20, 2 266 en teq 40), de modo que teq 160 cae hacia
    los 20 000 s. Se repite con tope AUTORA_TOPE_S (defecto 25 200 s).
  - 22:00, barrera, k = 1 000 (NUEVA): el brazo de M-A2. En local, el
    2026-10-07, llego a teq 20 en 210 s con los precios a 1 COP/kWh de la
    forma cerrada (833,65 x 3; 1 249,04; 1 250); unas nueve veces mas barata
    que k = 100. En teq 80 (1 459 s en local) estaba en la forma cerrada
    (|dp| = 1,5e-3, |dq| = 2,6e-6) pero con |dq/dt| = 9,3e-3: el reparto
    vibra sobre el reposo, y la quietud puede no cumplirse. Si es asi, el
    juicio lo dice y no se relaja; la lectura la daria el brazo k = 100.
  - k = 1, las cuatro: NO SE REPITEN. Sus cortes terminan en teq 40 por
    diseno y la quietud se lee entre teq 20 y 40; en 3 600 s llegaron a teq 2
    (22:00) y a teq 1 (14:00), y el costo crece ~3,7 veces por duplicacion
    (418 s en teq 1, 1 543 en teq 2, barrera de las 22:00): teq 40 pediria del
    orden de 4e5 s. No cabe en ninguna noche.
  - 22:00, precio (la forma del fichero original): k = 100 llego a teq 5 en
    1 798 s con |dq/dt| = 1,2e3, oscilando; k = 1 000, en local, no paso de
    teq 2 en 400 s. Se repiten las dos con el tope, pero lo esperable es que
    no lleguen a teq 160: el obstaculo es la rigidez, no el tope.
  - 14:00, las dos formas: con k = 100 el integrador dio un valor no finito
    entre teq 0 y 2 (828 y 1 294 s); en local, con k = 1 000, LSODA se detuvo
    a los 122 s por «repeated convergence failures», y con k = 10 no paso de
    teq 2 en 400 s. Con k = 1 llego a teq 1 en 3 600 s. Se repiten con
    k = 1 000 y k = 100 para dejarlo medido con el codigo de hoy, pero lo
    esperable es que no haya lectura: la dinamica acelerada de esa hora no se
    integra con las tolerancias del motor (rtol = atol = 1e-6, H-51, que no
    se aflojan) y sin acelerar no cabe.

EL CRITERIO ES EL DE M-G, SIN CAMBIOS: las mismas especificaciones de
`medicion_chacon.py` (la configuracion del codigo de la autora, competencia
`matlab` y oferta a partes iguales, mu = 1, arranque de precios c136, las dos
referencias), el mismo rotulo `M-G`, de modo que `veredicto.py` aplica el
juicio propio de M-G (`medicion_chacon.veredicto`: contra la tabla, con el
brazo que llego mas lejos ESTANDO QUIETO en teq 80 y 160). Lo unico que
cambia es el tope, el brazo k = 1 000 (sus cortes, los de M-A2, hasta teq 160)
y que no se corren los brazos k = 1.

EL ORDEN, para que quepa con pocos procesos (AUTORA_PROCESOS, 4 por defecto):
primero las dos de barrera de las 22:00, que son las que dan lectura; despues
las cuatro de las 14:00, que mueren pronto; al final las dos de precio de las
22:00, que ocupan su proceso hasta el tope.
"""
from __future__ import annotations

import math
import os

import medicion_chacon as MG

MEDICION = MG.MEDICION            # "M-G": veredicto.py aplica su juicio
QUE_DECIDE = MG.QUE_DECIDE + " (repetida con el tope suficiente, CA)"
CORTES = {100.0: list(MG.CORTES[100.0]),
          1000.0: [0, 2e-3, 5e-3, 1e-2, 2e-2, 4e-2, 8e-2, 0.16]}
ORDEN = (("22", MG.BARRERA, 1000.0), ("22", MG.BARRERA, 100.0),
         ("14", MG.BARRERA, 1000.0), ("14", MG.PRECIO, 1000.0),
         ("14", MG.BARRERA, 100.0), ("14", MG.PRECIO, 100.0),
         ("22", MG.PRECIO, 1000.0), ("22", MG.PRECIO, 100.0))
TOPE = 25200.0


def tope() -> float:
    t = float(os.environ.get("AUTORA_TOPE_S", str(TOPE)))
    if not (t > 0 and math.isfinite(t)):
        raise ValueError(f"AUTORA_TOPE_S={t!r}")
    return t


def specs(horas=None) -> list:
    variantes = dict(MG.VARIANTES)
    fuera = []
    for hora, familia, k in ORDEN:
        var = dict(mu_ent=MG.MU, k_lento=k)
        var.update(variantes[familia])
        cortes = CORTES[k]
        if abs(cortes[-1] * k - 160.0) > 1e-9:
            raise AssertionError(f"los cortes de k = {k:g} no llegan a teq 160")
        fuera.append(dict(
            medicion=MEDICION, familia=familia, caso="CHACON", fecha=hora,
            grupo="chacon", etq=f"{familia} k{k:g}", var=var, cortes=cortes,
            tope=tope(), nivel="c136", piso_juego="marginal",
            cerrada=dict(MG.REFERENCIAS["cerrada"]),
            referencias={n: dict(v) for n, v in MG.REFERENCIAS.items()}))
    return fuera
