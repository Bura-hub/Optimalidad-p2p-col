"""M-A2: la validacion AMPLIADA del reposo, estratificada por regimen y caso.

Actividades 1.1 y 4.2.

QUE DECIDE. Lo mismo que M-A (`medicion_regimenes.py`): si cada regimen se
publica en la tesis como «el reposo al que la dinamica llega» o como «regla
declarada». La validacion del 2026-09-19 no pudo decidirlo en ninguno (CANON
§9 y §14.5): la muestra era de E0 solo, con 41 horas, y 72 de las 106
corridas se cortaron por su tope de 3 600 (s) antes de teq 160, de modo que
ningun regimen junto horas juzgadas suficientes.

EL CRITERIO NO CAMBIA. El mismo de M-A, fijado de antemano (ADR 0060, fable
§6 y §11) y aplicado por el mismo `veredicto.py`: una hora esta dentro si en
teq 80 y en teq 160 max|q - q_cerrada| <= 1 % de E y max|p - p_cerrada| <=
0,5 (COP/kWh) (la tolerancia floja de la familia acelerada; la estricta,
1e-3·E y 0,05, en el brazo sin acelerar); un regimen queda como «reposo
verificado» con el 95 % o mas de TODAS sus horas dentro y cinco como minimo.
Una hora sin ninguna corrida en teq 160 sigue en el denominador y cuenta como
«no llega». La misma dinamica: mu = 1 (D49), precios desde el presupuesto
sigma (D50), piso del vendedor marginal (D63), el arnes acelerado con el
`rtol = atol = 1e-6` del motor (H-51; el arnes no lo baja).

LO QUE CAMBIA, y por que (diseno del 2026-10-06, informe_servidor.md):

  1. LA MUESTRA. Siete regimenes del nucleo con mercado (sin «mixto», que la
     matriz del 19 no tiene) y hasta N_MAX horas por regimen (40 por defecto,
     AMPLIACION_HORAS), repartidas por turno entre los trece casos: la hora
     j de cada caso antes que la j+1 de ninguno. Las horas salen de
     `selecciona_horas.py` sobre los almacenes de la matriz canonica del 19
     de septiembre, comprobadas una a una (regimen y piso del juego).
  2. UN SOLO BRAZO ACELERADO, k = 1 000. En M-A del 19, k = 100 llego a teq
     160 en 11 de 43 corridas y cuesta diez veces mas por unidad de teq;
     k = 1 000 llego en 19 de 43. La familia «V3a acelerada» juntaba las dos aceleraciones y
     una hora se juzgaba con las que llegaban: con una, se juzga con esa. La
     tolerancia es la misma (la floja, por la aceleracion).
  3. EL TOPE POR CORRIDA, 10 800 (s) (AMPLIACION_TOPE_S). En los regimenes
     rigidos k = 1 000 llega a teq 80 hacia los 2 100 a 2 600 (s) y de teq
     80 a teq 160 tarda 2,8 veces mas (mediana medida el 19): unos 6 000 a
     7 300 (s). Con 3 600, esas horas «no llegan» por presupuesto y no por la
     dinamica.
  4. EL ORDEN DE PRIORIDAD, por rondas: en cada ronda, una hora de cada
     regimen, primero los que menos horas juzgadas tuvieron el 19 (cuantal 0,
     compradores cortos 0, excluidos 0, un comprador 3, suma que no cabe 3,
     interiores 5, topados 7). Si la noche se corta, todos los regimenes
     quedan con un numero parecido de horas y los peor cubiertos, con alguna
     mas.
  5. LA PARADA POR FUTILIDAD (`omite`). Cuando un regimen acumula mas horas
     fuera (o sin llegar, o fallidas) que floor(0,05·N_plan), ya no puede
     llegar al 95 % ni con todas las que faltan dentro: su rotulo es «regla
     declarada» y esta decidido. Sus horas pendientes no se someten (quedan
     «OMITIDAS» en el JSON, fuera de todo denominador) y el tiempo pasa a los
     demas. El rotulo es el mismo que daria la muestra entera; solo el
     porcentaje se calcula sobre las horas hechas, y la lectura lo dice.
  6. EL BRAZO SIN ACELERAR (k = 1, tolerancia estricta), opcional:
     AMPLIACION_SIN_ACELERAR=1 lo anade AL FINAL del plan, en los grupos
     libres (interiores y suma que no cabe), como su propia familia.

LA LECTURA PARCIAL la hace `lectura_ampliada.py`: por regimen, x de n dentro,
el intervalo de Wilson al 95 % de esa fraccion y el estado (completo, parcial
o decidido por futilidad), sin tocar el criterio.

RETOMAR otra noche: `corre_mediciones.py --desde <k>` con otra `--salida`, y
AMPLIACION_PREVIOS con los JSON anteriores (separados por comas), para que la
parada por futilidad cuente tambien lo de las noches previas. El lanzador lo
hace solo con RETOMA=<k> (accion `validacion_ampliada`).
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

MEDICION = "M-A2"
QUE_DECIDE = ("reposo verificado o regla declarada, por regimen; muestra "
              "estratificada por regimen y caso (validacion ampliada)")

# En orden de prioridad: primero los que menos horas juzgadas tuvieron el
# 2026-09-19 (CANON §14.5). Son los regimenes del nucleo con mercado que
# aparecen en la matriz canonica (por_regimen_13casos.csv): «mixto» no esta.
REGIMENES = ("cuantal", "compradores_cortos", "excluidos", "un_comprador",
             "suma_no_cabe", "interiores", "topados")
# Los trece casos de la matriz, en el orden de CASOS_MATRIZ del lanzador.
CASOS = ("E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU")
GRUPOS_LIBRES = ("interiores", "suma_no_cabe")
MU = 1.0
K = 1000.0
UMBRAL = 0.95                      # el de veredicto.UMBRAL (ADR 0060)
# Los mismos puntos de control que M-A (teq 0 a 160).
CORTES = {1000.0: [0, 2e-3, 5e-3, 1e-2, 2e-2, 4e-2, 8e-2, 0.16],
          1.0: [0, 2, 5, 10, 20, 40, 80, 160]}
ACELERADA = "V3a acelerada"
SIN_ACELERAR = "V3a sin acelerar"


def n_max() -> int:
    n = int(os.environ.get("AMPLIACION_HORAS", "40"))
    if n < 5:
        raise ValueError(f"AMPLIACION_HORAS={n}: hacen falta al menos 5 horas "
                         f"por regimen (el minimo del criterio)")
    return n


def tope() -> float:
    t = float(os.environ.get("AMPLIACION_TOPE_S", "10800"))
    if not (t > 0 and math.isfinite(t)):
        raise ValueError(f"AMPLIACION_TOPE_S={t!r}")
    return t


def con_sin_acelerar() -> bool:
    return os.environ.get("AMPLIACION_SIN_ACELERAR", "0") == "1"


def horas_del_regimen(horas, regimen, cuantas) -> list:
    """Las horas de ese regimen, por turno entre los casos: la primera de
    cada caso, despues la segunda de cada uno, y asi hasta `cuantas`.
    Devuelve [(caso, fecha)] sin repetir."""
    listas = [(c, list(horas.get(c, {}).get(regimen, []) or []))
              for c in CASOS]
    fuera, vistas = [], set()
    j = 0
    while len(fuera) < cuantas and any(j < len(l) for _c, l in listas):
        for caso, lista in listas:
            if j < len(lista):
                clave = (caso, lista[j]["fecha"])
                if clave not in vistas:
                    vistas.add(clave)
                    fuera.append(clave)
                    if len(fuera) >= cuantas:
                        break
        j += 1
    return fuera


def _spec(caso, fecha, regimen, k, familia, ronda, n_plan) -> dict:
    return dict(medicion=MEDICION, familia=familia, caso=caso, fecha=fecha,
                grupo=regimen, etq=f"V3a k{k:g}",
                var=dict(mu_ent=MU, k_lento=k), cortes=CORTES[k],
                tope=tope(), nivel="sigma", piso_juego="marginal",
                ronda=ronda, n_plan_grupo=n_plan)


def specs(horas) -> list:
    cuantas = n_max()
    por_reg = {r: horas_del_regimen(horas, r, cuantas) for r in REGIMENES}
    fuera = []
    rondas = max((len(v) for v in por_reg.values()), default=0)
    for j in range(rondas):
        for r in REGIMENES:
            if j < len(por_reg[r]):
                caso, fecha = por_reg[r][j]
                fuera.append(_spec(caso, fecha, r, K, ACELERADA, j,
                                   len(por_reg[r])))
    if con_sin_acelerar():
        libres = {r: por_reg[r] for r in GRUPOS_LIBRES}
        rondas = max((len(v) for v in libres.values()), default=0)
        for j in range(rondas):
            for r in GRUPOS_LIBRES:
                if j < len(libres[r]):
                    caso, fecha = libres[r][j]
                    fuera.append(_spec(caso, fecha, r, 1.0, SIN_ACELERAR, j,
                                       len(libres[r])))
    return fuera


# ── La parada por futilidad ────────────────────────────────────────────────
_PREVIOS = None
_JUICIO = {}


def previos() -> list:
    """Los resultados de las noches anteriores (AMPLIACION_PREVIOS: JSON
    separados por comas), para que la parada cuente lo ya hecho."""
    global _PREVIOS
    if _PREVIOS is None:
        _PREVIOS = []
        for p in (os.environ.get("AMPLIACION_PREVIOS", "") or "").split(","):
            p = p.strip()
            if p:
                _PREVIOS.extend(json.loads(Path(p).read_text(encoding="utf-8")))
    return _PREVIOS


def limite_fuera(n_plan: int, umbral: float = UMBRAL) -> int:
    """Cuantas horas fuera admite un regimen de n_plan horas y aun llega al
    umbral con todas las demas dentro."""
    return int(math.floor((1.0 - umbral) * n_plan + 1e-9))


def hora_fuera(res) -> bool | None:
    """True si la hora (una corrida por hora y familia) cuenta en contra del
    95 %: fuera de tolerancia, sin llegar a teq 160 o fallida; False si
    cuenta a favor; None si no cuenta (omitida, sin mercado o con el recorte
    que movio el reposo). Con el mismo juicio que `veredicto.py`."""
    if res.get("omitida") or res.get("recorte_movio"):
        return None
    # La cache guarda tambien el objeto: un id solo podria reutilizarse.
    clave = id(res)
    if clave in _JUICIO and _JUICIO[clave][0] is res:
        return _JUICIO[clave][1]
    import veredicto as V
    if V.es_falla(res):
        valor = True
    elif not res.get("veredicto"):
        valor = None                     # sin mercado: no esta en la tabla
    else:
        c = V.cuenta_hora([res], "cerrada")
        valor = bool(c["falla"] or not c["juzgada"] or not c["dentro"])
    _JUICIO[clave] = (res, valor)
    return valor


def omite(spec, resultados):
    """Texto si la corrida ya no puede cambiar el rotulo de su regimen."""
    r, fam = spec.get("grupo"), spec.get("familia")
    n_plan = int(spec.get("n_plan_grupo", 0) or 0)
    if not n_plan:
        return None
    fuera = 0
    for res in list(previos()) + list(resultados):
        sp = res.get("spec", {})
        if sp.get("grupo") != r or sp.get("familia") != fam:
            continue
        if hora_fuera(res):
            fuera += 1
    lim = limite_fuera(n_plan)
    if fuera > lim:
        return (f"parada por futilidad: {fuera} horas de {r} ({fam}) fuera, "
                f"sin llegar a teq 160 o fallidas, mas de las {lim} que "
                f"admiten {n_plan} para el 95 %; el regimen queda como regla "
                f"declarada con cualquier resultado de las que faltan")
    return None
