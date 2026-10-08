"""M-A2X: la forma cerrada frente a la dinamica con PRECIOS EXTREMOS (DX).

Actividades 1.1 y 4.1.

QUE MIDE. La validacion ampliada (M-A2, `medicion_ampliada.py`, CANON §14.33)
contrasto la forma cerrada con la dinamica acelerada solo con los precios del
punto base. Aqui, lo mismo en horas construidas con precios extremos, para ver
si el acuerdo (o el desacuerdo) depende del nivel de los precios. Tres
familias de precio, cada una con las otras cuatro entradas del GSA en 1:

    bolsa4       f_bolsa = 4: el extremo superior de la caja del GSA
                 (`comun.SOPORTES`), la bolsa cruda por 4 y el techo PES de la
                 101 066 despues (`aplica_bolsa`);
    tarifa_baja  f_tarifa = 0,5, la tarifa a la mitad de §14.32, SALVO en E4,
                 E5 y P2, donde con 0,5 el piso del vendedor es negativo en
                 cientos de horas-vendedor y el evaluador no las evalua
                 (§14.32, tabla 2): alli 0,6, la tarifa mas baja evaluable
                 (el umbral 0,5906 redondeado hacia arriba a la centesima). Se
                 dice en el rotulo de cada corrida (`precios`);
    tarifa2      f_tarifa = 2, el doble de la de §14.32.

EL CRITERIO NO CAMBIA: el mismo de M-A y M-A2 (ADR 0060), aplicado por el
mismo `veredicto.py` sin cambios (95 % de las horas dentro en teq 80 y 160,
1 % de E y 0,5 COP/kWh por la aceleracion, cinco como minimo). LA MISMA
DINAMICA: el brazo V3a acelerado de M-A2 (k = 1 000, mu = 1, los mismos
cortes hasta teq 160, precios desde el presupuesto sigma, piso del vendedor
marginal) y el mismo tope por corrida (10 800 s, EXTREMA_TOPE_S). Cada familia
de precio es su propia FAMILIA del veredicto («V3a acelerada (bolsa4)», ...),
de modo que la tabla y la lectura salen separadas por factor de precio.

LAS HORAS. No hay almacen de la matriz con los precios cambiados: las elige
`selecciona_extrema.py`, que corre el motor del evaluador del GSA con los
factores (`aplica_factores`, las 6 144 h), agrupa las horas por el regimen que
el motor les da, muestrea con semilla y COMPRUEBA cada hora con el arnes (la
misma hora cargada con `paso_a_paso.carga(factor_bolsa, factor_tarifa)`):
mismo regimen, mismo piso del juego y misma energia. Deja un
`horas_<caso>__<familia>.json` por caso y familia, con la clave
`<caso>__<familia>`, que es lo que lee `specs`.

LA MUESTRA: los regimenes con mas horas de la matriz (interiores, un
comprador, topados y compradores cortos; EXTREMA_REGIMENES), hasta
EXTREMA_HORAS (10) horas por regimen y familia, repartidas por turno entre los
trece casos, y el plan por rondas: en cada ronda, una hora de cada regimen en
cada familia. Si la noche se corta, todos los grupos quedan con un numero
parecido de horas.

SIN PARADA POR FUTILIDAD POR DEFECTO. En M-A2 la parada servia para decidir el
rotulo antes. Aqui el rotulo ya esta decidido en los siete regimenes (regla
declarada, §14.33) y lo que se mide es la fraccion dentro y si la energia
coincide, separadas por precio: con 10 horas por grupo el limite es
floor(0,05·10) = 0 y la parada dejaria cada grupo en una o dos horas.
EXTREMA_FUTILIDAD=1 la activa con la regla de M-A2.

RETOMAR otra noche: `corre_mediciones.py --desde <k>` con otra `--salida`
(el lanzador lo hace con RETOMA=<k>, accion `dinamica_extrema`).
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import medicion_ampliada as MA

MEDICION = "M-A2X"
QUE_DECIDE = ("la forma cerrada frente a la dinamica con precios extremos "
              "(bolsa x4, tarifa x0,5 o 0,6 y x2), por regimen y familia de "
              "precio")

FAMILIAS = ("bolsa4", "tarifa_baja", "tarifa2")
TARIFA_BAJA = 0.5
# §14.32, tabla 2: con f_tarifa = 0,5 el piso del vendedor es negativo en E4
# (994 horas-vendedor), E5 (617) y P2 (270); la mas baja evaluable es 0,6.
TARIFA_BAJA_MINIMA = 0.6
CASOS_TARIFA_MINIMA = ("E4", "E5", "P2")
REGIMENES = ("interiores", "un_comprador", "topados", "compradores_cortos")
CASOS = MA.CASOS
K = MA.K
MU = MA.MU
CORTES = MA.CORTES[K]
ACELERADA = MA.ACELERADA
UMBRAL = MA.UMBRAL


def precios_de(familia: str, caso: str) -> dict:
    """Los factores de precio de una familia en un caso."""
    if familia == "bolsa4":
        return {"f_bolsa": 4.0, "f_tarifa": 1.0}
    if familia == "tarifa_baja":
        f = TARIFA_BAJA_MINIMA if caso in CASOS_TARIFA_MINIMA else TARIFA_BAJA
        return {"f_bolsa": 1.0, "f_tarifa": f}
    if familia == "tarifa2":
        return {"f_bolsa": 1.0, "f_tarifa": 2.0}
    raise ValueError(f"familia de precio {familia!r}; use {FAMILIAS}")


def punto_gsa(familia: str, caso: str):
    """El punto de las seis entradas del GSA de la familia en el caso."""
    import numpy as np
    from gsa_directo import comun
    x = comun.PUNTO_BASE.copy()
    p = precios_de(familia, caso)
    x[comun.NOMBRES.index("f_bolsa")] = p["f_bolsa"]
    x[comun.NOMBRES.index("f_tarifa")] = p["f_tarifa"]
    return np.asarray(x, dtype=float)


def clave_horas(caso: str, familia: str) -> str:
    """La clave del caso en el `horas_*.json` de la seleccion."""
    if familia not in FAMILIAS:
        raise ValueError(f"familia de precio {familia!r}; use {FAMILIAS}")
    return f"{caso}__{familia}"


def familia_veredicto(familia: str) -> str:
    return f"{ACELERADA} ({familia})"


def _lista(variable: str, defecto, validos) -> tuple:
    texto = os.environ.get(variable, "")
    v = tuple(x for x in texto.replace(",", " ").split() if x) or tuple(defecto)
    malos = [x for x in v if x not in validos]
    if malos:
        raise ValueError(f"{variable}: {malos} no valen; use {tuple(validos)}")
    return v


def familias() -> tuple:
    return _lista("EXTREMA_FAMILIAS", FAMILIAS, FAMILIAS)


def regimenes() -> tuple:
    return _lista("EXTREMA_REGIMENES", REGIMENES, MA.REGIMENES)


def n_max() -> int:
    n = int(os.environ.get("EXTREMA_HORAS", "10"))
    if n < 5:
        raise ValueError(f"EXTREMA_HORAS={n}: hacen falta al menos 5 horas "
                         f"por regimen (el minimo del criterio)")
    return n


def tope() -> float:
    t = float(os.environ.get("EXTREMA_TOPE_S", "10800"))
    if not (t > 0 and math.isfinite(t)):
        raise ValueError(f"EXTREMA_TOPE_S={t!r}")
    return t


def con_futilidad() -> bool:
    return os.environ.get("EXTREMA_FUTILIDAD", "0") == "1"


def horas_del_regimen(horas, familia, regimen, cuantas) -> list:
    """Las horas de ese regimen y familia, por turno entre los casos, como
    `medicion_ampliada.horas_del_regimen`. [(caso, fecha)]."""
    por_caso = {c: (horas.get(clave_horas(c, familia), {}) or {})
                for c in CASOS}
    return MA.horas_del_regimen(por_caso, regimen, cuantas)


def _spec(caso, fecha, regimen, familia, ronda, n_plan) -> dict:
    return dict(medicion=MEDICION, familia=familia_veredicto(familia),
                familia_precio=familia, precios=precios_de(familia, caso),
                caso=caso, fecha=fecha, grupo=regimen,
                etq=f"V3a k{K:g} {familia}", var=dict(mu_ent=MU, k_lento=K),
                cortes=list(CORTES), tope=tope(), nivel="sigma",
                piso_juego="marginal", ronda=ronda, n_plan_grupo=n_plan)


def specs(horas) -> list:
    cuantas = n_max()
    fams, regs = familias(), regimenes()
    grupos = {(f, r): horas_del_regimen(horas, f, r, cuantas)
              for f in fams for r in regs}
    fuera = []
    rondas = max((len(v) for v in grupos.values()), default=0)
    for j in range(rondas):
        for f in fams:
            for r in regs:
                lista = grupos[(f, r)]
                if j < len(lista):
                    caso, fecha = lista[j]
                    fuera.append(_spec(caso, fecha, r, f, j, len(lista)))
    return fuera


# ── La parada por futilidad, solo con EXTREMA_FUTILIDAD=1 ─────────────────
_PREVIOS = None


def previos() -> list:
    """Los resultados de noches anteriores (EXTREMA_PREVIOS, JSON separados
    por comas), para que la parada cuente lo ya hecho."""
    global _PREVIOS
    if _PREVIOS is None:
        _PREVIOS = []
        for p in (os.environ.get("EXTREMA_PREVIOS", "") or "").split(","):
            p = p.strip()
            if p:
                _PREVIOS.extend(json.loads(Path(p).read_text(encoding="utf-8")))
    return _PREVIOS


def omite(spec, resultados):
    """Con EXTREMA_FUTILIDAD=1, la regla de M-A2 por regimen y familia de
    precio; sin ella (el defecto), nunca omite."""
    if not con_futilidad():
        return None
    r, fam = spec.get("grupo"), spec.get("familia")
    n_plan = int(spec.get("n_plan_grupo", 0) or 0)
    if not n_plan:
        return None
    fuera = 0
    for res in list(previos()) + list(resultados):
        sp = res.get("spec", {})
        if sp.get("grupo") != r or sp.get("familia") != fam:
            continue
        if MA.hora_fuera(res):
            fuera += 1
    lim = MA.limite_fuera(n_plan, UMBRAL)
    if fuera > lim:
        return (f"parada por futilidad: {fuera} horas de {r} ({fam}) en "
                f"contra, mas de las {lim} que admiten {n_plan} para el 95 %")
    return None
