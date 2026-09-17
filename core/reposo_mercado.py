"""
reposo_mercado.py
-----------------
El mercado de una hora en el reposo del juego regularizado, calculado en forma
cerrada (D48 a D55). 2026-09-16.

Por que. La dinamica de replicador del acoplado no converge con un vendedor y
varios compradores: oscila alrededor de un reposo que no alcanza (H-87). Y el
nivel del precio no tiene ancla dentro de la banda colombiana: el unico ancla
del modelo base, la cobertura del costo del vendedor, queda bajo el piso
(H-88). El autor aprobo (D48) resolver cada hora en el reposo del juego con la
regularizacion entropica del replicador del vendedor, que es el punto al que la
dinamica regularizada converge donde se pudo integrar, y calcularlo directo, sin
integrar nada.

Este modulo es SOLO el nucleo puro de ese calculo: funciones sin estado, sin
E/S y sin dependencia del motor. La especificacion es la seccion 5.1 de
`.superpowers/sdd/2026-09-16-sonda-equilibrio/fable-report.md` (pasos 1 a 9);
aqui se implementan los pasos 1 a 6, 8 y 9. El paso 7, la participacion de los
vendedores (C-151), queda para el motor (tarea 2), que usara
`ingreso_por_vendedor`.

Los estados del reposo. Cada comprador con deficit queda en una de tres
posiciones de precio: en su techo (T), interior a un precio comun ell (N) o en
el piso del juego (F). La suma de los precios de los compradores es el
presupuesto S (paso 2): la dinamica la conserva desde que el jugador virtual se
clava en su techo (H-87 sec. 6). Un estado es un reposo si:
  - los precios suman S, con ell dentro de [piso, min techo de N];
  - la energia sale por prioridad de precio (el vendedor sirve primero al
    precio mas alto; a igual precio, llenado por niveles), salvo con
    compradores cortos, donde cada uno recibe su deficit;
  - los de N reciben lo mismo (su aptitud es igual);
  - los de T no reciben mas que los de N, y los de F no reciben menos (la
    aptitud del precio baja con lo que se recibe, sec. 5.1 paso 5).
Con F vacio es el paso 3 (`reposo()` del prototipo de evaluador2); con F no
vacio y un solo interior, el paso 5. `n_soluciones` cuenta los estados
distintos que cumplen, para que ninguna eleccion quede en silencio.

Quien entra y el piso del juego (paso 1; D61, D63 a D65, 2026-09-17). Con
pisos distintos por vendedor y un precio uniforme, el piso del juego es el del
VENDEDOR MARGINAL (D63), no el minimo de los que despachan (D62, sustituida):
con el minimo, el vendedor de piso alto cobraba el mismo precio medio que los
demas, quedaba bajo su piso y la participacion lo retiraba aunque algun
comprador le pagaria (E1 perdia 5 977 (kWh) frente a 10 625 transados). Los
vendedores despachan por su piso (D64) y una caminata competitiva sobre los
pisos decide quien entra de cada lado (D65, `despacho_competitivo`). Con el
piso marginal, todo vendedor despachado cobra al menos su piso: es un teorema
del emparejamiento de rango uno, y `_comprueba` lo verifica en cada hora. La
prima de los vendedores se publica descompuesta en renta inframarginal y parte
del juego (D69).

Tres decisiones de esta implementacion, a la vista en `n_soluciones`:
  - con mas de un reposo del paso 3 (en una exploracion aleatoria de 40 000
    horas sinteticas solo aparecio con deficits empatados) se publica el de
    mas compradores interiores (`_elige_paso3`);
  - la regla del paso 5 se aplica tal cual; si hay reposos y la regla no cae
    en ninguno, ValueError; si no hay ninguno, se publica como regla
    declarada con n_soluciones = 0;
  - el segundo lazo del prototipo (el grupo marginal en el piso y los demas en
    su techo, sin conservar S) NO se usa: contradice la regla del paso 5 y los
    promedios de la dinamica de `valida_reposo_E0.log` (horas 540, 2317, 3062
    y 3086).

Unidades: energia en (kWh), precios y costos en (COP/kWh), ingresos y
excedentes en (COP).

Actividad 2.2 (algoritmos de calculo del mercado); las cotas del paso 9 (D55)
dan la captura y el precio de la justicia de la actividad 3.3.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Optional

import numpy as np

MODOS_PRESUPUESTO = ("sigma", "algoritmo3", "c136")
REGLAS_PRECIO = ("uniforme", "puja")
# D64 (2026-09-17): "piso" (defecto) despacha por el piso de cada vendedor con
# la caminata competitiva de D65; "costo" por el costo nivelado b_j (el merito
# de D52, que queda de comparacion); "llenado" reparte por niveles entre todos
# los que pueden vender. En las tres, el piso del juego es el del vendedor
# marginal (D63): en "costo" y "llenado", el maximo de los despachados.
DESPACHOS_VENDEDORES = ("piso", "costo", "llenado")
REGIMENES = ("interiores", "topados", "excluidos", "mixto", "suma_no_cabe",
             "compradores_cortos", "un_comprador", "sin_mercado",
             "sin_ganancia")

# Tolerancias. Los precios del reposo salen de sumas y restas de techos y
# pisos del orden de 700 (COP/kWh), con error de redondeo del orden de 1e-13;
# 1e-7 (COP/kWh) los separa sin confundir precios distintos de verdad.
TOL_PRECIO = 1e-7
# Energia: relativa al volumen de la hora, max(1, E) (kWh).
TOL_ENERGIA_REL = 1e-9
# Igualdad de costos lineales b_j en el orden de merito (COP/kWh). La forma
# cerrada es el limite mu -> 0+ de la regularizacion (sec. 5.4): prioridad
# estricta y empate solo exacto.
TOL_COSTO = 1e-9
# Igualdad de pisos en la caminata y en el despacho por piso (COP/kWh): dos
# vendedores del mismo tramo tienen el mismo piso al bit; 1e-9 solo absorbe
# el redondeo.
TOL_PISO = 1e-9
# Teorema de cobertura (D63), relativo al piso de cada vendedor: el ingreso
# medio de un despachado es el precio medio de la hora, que sale de un cociente
# con error del orden de 1e-13 relativo; 1e-9 relativo (7e-7 (COP/kWh) con un
# piso de 700) lo separa sin tapar un vendedor de verdad bajo su piso.
TOL_COBERTURA_REL = 1e-9
# Descomposicion de la prima (D69): la identidad renta + parte del juego =
# prima se cumple salvo p*·(sum s despachado - E), redondeo; 1e-9 relativo al
# mayor de max(1, ingreso de la hora, sum piso_j·s_j).
TOL_PRIMA_REL = 1e-9
# Lazo de exclusion de compradores con el piso maximo ("costo" y "llenado"):
# ya no es monotono (sacar un comprador puede bajar el piso y readmitirlo), de
# modo que tiene limite de vueltas y falla en voz alta si oscila.
MAX_VUELTAS_LAZO = 64
# La enumeracion de estados crece como 3^I; la comunidad tiene a lo sumo
# cuatro compradores y el caso de Chacon cinco.
MAX_COMPRADORES = 10


@dataclass(frozen=True)
class ReposoHora:
    """El mercado de una hora en el reposo (sec. 5.1, pasos 1 a 6 y 8).

    Los vectores por comprador y por vendedor tienen la longitud de la entrada,
    incluidos los agentes sin cantidad, que quedan en cero.

    P                 energia por pareja, forma (J, I) (kWh)
    q                 lo que recibe cada comprador (kWh)
    s_despachado      lo que vende cada vendedor (kWh)
    E                 volumen de la hora (kWh): min(sum s, sum d), con s de
                      los vendedores que pueden vender (sin los de
                      `vendedores_excluidos` ni `vendedores_no_despachados`)
                      y d de los compradores que quedan en el juego; 0 sin
                      mercado
    piso              piso del juego (COP/kWh), el del VENDEDOR MARGINAL (D63):
                      con `despacho_vendedores="piso"`, el nivel de cierre p*
                      de la caminata competitiva (D65), que es el piso del
                      ultimo despachado; con "costo" y "llenado", el maximo de
                      piso_j de los que despachan. Nunca cuenta un vendedor
                      excluido por no tener ganancia posible. Sin mercado, el
                      minimo de los vendedores activos, o 0 si no hay
                      vendedores activos
    piso_marginal     igual a `piso`, con el nombre de D63, por claridad
    S                 presupuesto de precios de los compradores en el juego
                      (COP/kWh); con un solo comprador, el piso (D54); 0 sin
                      mercado
    ell               precio comun del grupo interior o del marginal
                      (COP/kWh); el piso con un comprador; None sin mercado
    pi_reposo         precio de cada comprador en el reposo, es decir, el pago
                      segun puja (COP/kWh). Quien no esta en el juego (sin
                      deficit, en `excluidos_bajo_piso`, o toda la hora sin
                      mercado) y el de `excluidos` quedan en su techo
    p_u               precio marginal uniforme de la hora (D51) (COP/kWh); 0
                      sin mercado, porque no hay precio de la hora
    p_liquidado       precio con que se liquida a cada comprador (COP/kWh);
                      sin mercado, el techo (su alternativa)
    regimen           uno de REGIMENES. «sin_ganancia» (D61) es una hora sin
                      mercado porque el piso de TODOS los vendedores activos
                      supera el techo de todos los compradores con deficit:
                      ningun vendedor puede vender a ningun comprador. Su
                      energia posible es min(sum s, sum d) de la entrada
    excluidos         indices de los compradores en el juego que quedan en
                      su techo sin recibir energia (regimen «no cabe»: el
                      vendedor sirve primero a precios mas altos y no le queda)
    excluidos_bajo_piso  indices de los compradores con deficit que salen de la
                      hora porque su techo queda bajo el piso del juego (D61
                      parcial; con "piso", techo_i < p*): sin energia, fuera de
                      S y de sigma, con su precio en el techo. Vacio sin
                      mercado
    vendedores_excluidos  indices de los vendedores activos cuyo piso_j supera
                      el techo de todos los compradores con deficit (D61 del
                      lado de los vendedores): no tienen ganancia posible con
                      nadie, quedan fuera del despacho y de la oferta que
                      decide la rama, con fila de P en cero. En
                      «sin_ganancia», todos los activos
    vendedores_no_despachados  indices de los vendedores activos, con ganancia
                      posible (fuera de `vendedores_excluidos`), cuyo piso_j
                      supera el nivel de cierre p* de la caminata (D65): la
                      competencia los deja fuera, sin energia y fuera de la
                      oferta. Solo con "piso"; vacio con "costo" y "llenado"
                      y sin mercado
    orden_merito      indices de los vendedores con ganancia posible (activos y
                      fuera de `vendedores_excluidos`) en el orden de despacho,
                      estable por indice: por piso_j creciente con "piso"
                      (D64); por b_j creciente con "costo" y "llenado". Vacio
                      sin mercado, tambien en «sin_ganancia», donde nadie
                      puede vender
    n_soluciones      cuantos estados (T, N, F) distintos son reposo en la
                      hora, con F vacio o no; 1 con un comprador y 0 sin
                      mercado. En «suma_no_cabe» y «compradores_cortos», 0
                      dice que la regla del paso 5 se publica como declarada,
                      sin reposo que la respalde (D53)
    excedente         sum (techo_i - piso_j) P_ji (COP)
    ingreso_vendedores  ingreso de cada vendedor con el precio liquidado (COP)
    parte_vendedor    (ingreso total - sum piso_j s_j despachado) / excedente;
                      0 si el excedente es nulo. YA NO PUEDE SER NEGATIVA
                      (D63): con el piso marginal todo despachado cobra al
                      menos su piso, de modo que la prima es no negativa, y
                      `_comprueba` verifica la cobertura de cada uno. La
                      participacion del paso 7 (C-151), en el motor, queda
                      como guarda inerte (D67)
    renta_inframarginal  sum_j (p* - piso_j)·s_despachado_j (COP): lo que
                      cobran por encima de su piso los vendedores de piso
                      menor que el marginal (D69); 0 sin mercado
    parte_juego       (p_medio - p*)·E (COP), con p_medio = ingreso total / E:
                      lo que el reparto del presupuesto entre compradores
                      sube el precio medio sobre el piso marginal (D69).
                      renta_inframarginal + parte_juego = la prima de los
                      vendedores, sum_j (p_medio - piso_j)·s_despachado_j; 0
                      sin mercado
    sigma             la sigma usada en el modo "sigma": la dada o (I-1)/I con
                      I los compradores en el juego (los activos sin mercado;
                      None si no hay ninguno); None en los otros modos
    """
    P: np.ndarray
    q: np.ndarray
    s_despachado: np.ndarray
    E: float
    piso: float
    piso_marginal: float
    S: float
    ell: Optional[float]
    pi_reposo: np.ndarray
    p_u: float
    p_liquidado: np.ndarray
    regimen: str
    excluidos: tuple
    excluidos_bajo_piso: tuple
    vendedores_excluidos: tuple
    vendedores_no_despachados: tuple
    orden_merito: tuple
    n_soluciones: int
    excedente: float
    ingreso_vendedores: np.ndarray
    parte_vendedor: float
    renta_inframarginal: float
    parte_juego: float
    modo_presupuesto: str
    sigma: Optional[float]
    regla_precio: str
    despacho_vendedores: str


@dataclass(frozen=True)
class DespachoHora:
    """Paso 1 (D61, D63 a D65): quien entra de cada lado, el piso del juego y
    lo que vende cada vendedor. Lo devuelve `despacho_competitivo`.

    Los indices son posiciones en los vectores de entrada; `s_despachado` tiene
    la longitud de `s`, con cero en quien no vende.

    causa             "" si hay mercado; "sin_mercado" (sin vendedores o sin
                      compradores con cantidad) o "sin_ganancia" (D61)
    piso              el piso del juego (COP/kWh): p* con "piso"; el maximo de
                      los despachados con "costo" y "llenado". Sin mercado, el
                      minimo de los vendedores activos, o 0 sin ellos
    E                 min(oferta de `pueden_vender`, demanda de `dentro`)
                      (kWh); 0 sin mercado
    dentro            compradores con deficit en el juego (techo_i >= piso)
    pueden_vender     vendedores cuya oferta cuenta: con "piso", los de
                      piso_j <= p*; con "costo" y "llenado", todos los que
                      tienen ganancia posible
    s_despachado      lo que vende cada vendedor (kWh)
    excluidos_bajo_piso        compradores con deficit y techo bajo el piso
    vendedores_excluidos       vendedores activos sin ganancia posible (D61)
    vendedores_no_despachados  con "piso", los de piso_j > p* con ganancia
                               posible; vacio con las otras dos opciones
    despacho          la opcion de despacho
    """
    causa: str
    piso: float
    E: float
    dentro: tuple
    pueden_vender: tuple
    s_despachado: np.ndarray
    excluidos_bajo_piso: tuple
    vendedores_excluidos: tuple
    vendedores_no_despachados: tuple
    despacho: str


# ─── entradas ──────────────────────────────────────────────────────────────


def _vector(nombre: str, x, n: Optional[int] = None,
            escalar: bool = False) -> np.ndarray:
    """Vector float64 finito. Con `escalar`, un escalar se extiende a n."""
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 0:
        if not escalar or n is None:
            raise ValueError(f"{nombre} debe ser un vector, no un escalar")
        arr = np.full(n, float(arr))
    if arr.ndim != 1:
        raise ValueError(f"{nombre} debe ser un vector de una dimension; "
                         f"llego con forma {arr.shape}")
    if n is not None and arr.shape[0] != n:
        raise ValueError(f"las longitudes no cuadran: {nombre} tiene "
                         f"{arr.shape[0]} elementos y se esperaban {n}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{nombre} tiene valores no finitos: {arr}")
    return arr.copy()


def _no_negativo(nombre: str, x: np.ndarray) -> None:
    if np.any(x < 0.0):
        raise ValueError(f"{nombre} tiene cantidades negativas: {x}")


# ─── piezas ────────────────────────────────────────────────────────────────


def _llenado_por_niveles(cap: np.ndarray, total: float) -> np.ndarray:
    """Reparte `total` con x_i = min(cap_i, L) y sum x = total (D52, H-87).

    Lo mismo para todos salvo a quien necesita menos. Si `total` alcanza la
    suma de las capacidades, cada uno recibe la suya.
    """
    cap = np.asarray(cap, dtype=float)
    x = np.zeros(cap.size)
    if cap.size == 0 or total <= 0.0:
        return x
    if total >= float(cap.sum()):
        return cap.copy()
    orden = np.argsort(cap, kind="stable")
    resto = float(total)
    for k, idx in enumerate(orden):
        nivel = resto / (cap.size - k)
        if cap[idx] <= nivel:
            x[idx] = cap[idx]
            resto -= cap[idx]
        else:
            x[orden[k:]] = nivel
            break
    return x


def _grupos(valores: np.ndarray, tol: float, descendente: bool) -> list:
    """Indices agrupados por valor (empates dentro de `tol` respecto al primero
    del grupo), en orden de valor y, dentro del grupo, de indice."""
    signo = -1.0 if descendente else 1.0
    orden = sorted(range(valores.size), key=lambda i: (signo * valores[i], i))
    grupos, k = [], 0
    while k < len(orden):
        g = [orden[k]]
        k += 1
        while k < len(orden) and abs(valores[orden[k]] - valores[g[0]]) <= tol:
            g.append(orden[k])
            k += 1
        grupos.append(np.array(g, dtype=int))
    return grupos


def _sirve(E: float, d: np.ndarray, precios: np.ndarray) -> np.ndarray:
    """Paso 3: el vendedor sirve primero al precio mas alto; a igual precio,
    llenado por niveles. Es `sirve()` del prototipo de evaluador2."""
    q = np.zeros(d.size)
    resto = float(E)
    for g in _grupos(precios, TOL_PRECIO, descendente=True):
        if resto <= 0.0:
            break
        demanda = float(d[g].sum())
        if demanda <= resto:
            q[g] = d[g]
            resto -= demanda
        else:
            q[g] = _llenado_por_niveles(d[g], resto)
            resto = 0.0
    return q


def _despacho(s: np.ndarray, clave: Optional[np.ndarray], total: float,
              modo: str) -> np.ndarray:
    """Paso 6 (D52, D64): lo que vende cada vendedor cuando sobran vendedores.

    "piso": por piso_j creciente (`clave` son los pisos) hasta agotar cada s_j;
    entre vendedores de igual piso, llenado por niveles. "costo": lo mismo por
    b_j creciente (`clave` son los costos). "llenado": llenado por niveles
    entre todos (`clave` no se usa).
    """
    if modo == "llenado":
        return _llenado_por_niveles(s, total)
    tol = TOL_PISO if modo == "piso" else TOL_COSTO
    x = np.zeros(s.size)
    resto = float(total)
    for g in _grupos(clave, tol, descendente=False):
        if resto <= 0.0:
            break
        oferta = float(s[g].sum())
        if oferta <= resto:
            x[g] = s[g]
            resto -= oferta
        else:
            x[g] = _llenado_por_niveles(s[g], resto)
            resto = 0.0
    return x


def _orden_aptitud(q: np.ndarray, techo: np.ndarray, tol_q: float) -> list:
    """Paso 5: los compradores por aptitud decreciente, es decir por lo que
    reciben creciente. Empate (dentro de `tol_q`): primero el techo mas alto,
    cuyo termino de pago -piso q/(pi + 1) pesa menos, y despues el indice."""
    orden = []
    for g in _grupos(q, tol_q, descendente=False):
        orden.extend(sorted(g.tolist(), key=lambda i: (-techo[i], i)))
    return orden


def _regla_saturacion(q_orden: np.ndarray, techo: np.ndarray, piso: float,
                      S: float, tol_q: float):
    """Paso 5 (D53), la regla literal de la sec. 5.1.

    En orden de aptitud (lo que recibe, creciente), cada comprador se satura a
    su techo mientras los que quedan puedan seguir en el piso, es decir,
    mientras suma_techos + techo_k <= S - (quedan)·piso. El primero que no
    cabe queda interior con el resto de S; los demas, en el piso.

    Devuelve (precios, indice del marginal, su precio ell).
    """
    I = techo.size
    z = np.full(I, float(piso))
    suma = 0.0
    for pos, k in enumerate(_orden_aptitud(q_orden, techo, tol_q)):
        quedan = I - pos - 1
        if quedan > 0 and suma + techo[k] <= S - quedan * piso + TOL_PRECIO:
            z[k] = techo[k]
            suma += techo[k]
            continue
        ell = S - suma - quedan * piso
        if ell < piso - TOL_PRECIO or ell > techo[k] + TOL_PRECIO:
            raise ValueError(
                f"regla del paso 5: el marginal {k} queda en {ell:.6f} "
                f"(COP/kWh), fuera de [{piso:.6f}, {techo[k]:.6f}]; el "
                f"presupuesto S = {S:.6f} no es coherente con la banda")
        ell = min(max(ell, piso), techo[k])
        z[k] = ell
        return z, k, float(ell)
    # No ocurre: el ultimo del orden de aptitud tiene `quedan = 0` y cae
    # siempre en la rama del marginal. Es ValueError y no AssertionError a
    # proposito, como el de `_caminata` (revision de la tarea 5a, menor 4):
    # ninguna ruta del nucleo puede tumbar al trabajador, porque el ramal del
    # motor solo recoge ValueError; asi la hora queda con su motivo y cuenta
    # en [C-190] y en D38.
    raise ValueError(f"regla del paso 5: ningun comprador de los {I} quedo "
                     f"marginal, que no puede ocurrir con el orden de "
                     f"aptitud")


def _estados_reposo(E: float, d: np.ndarray, techo: np.ndarray, piso: float,
                    S: float, *, q_fijo: Optional[np.ndarray]) -> list:
    """Enumera los estados (T, N, F) que son reposo (docstring del modulo).

    `q_fijo`: lo que recibe cada comprador si no depende de los precios
    (compradores cortos); si es None, sale por prioridad de precio.
    Devuelve los estados distintos, sin repetir precios y reparto. Si el mismo
    estado sale con F vacio y con F no vacio (todos en el piso, por ejemplo),
    se guarda la version con F vacio, la del paso 3.
    """
    I = d.size
    if I > MAX_COMPRADORES:
        raise ValueError(f"{I} compradores; la enumeracion de reposos admite "
                         f"a lo sumo {MAX_COMPRADORES}")
    tol_q = TOL_ENERGIA_REL * max(1.0, E)
    hallados = []
    for asignacion in itertools.product((0, 1, 2), repeat=I):
        a = np.array(asignacion)
        N = np.flatnonzero(a == 1)
        F = np.flatnonzero(a == 2)
        if N.size == 0:
            continue
        T = np.flatnonzero(a == 0)
        ell = (S - float(techo[T].sum()) - F.size * piso) / N.size
        tope = float(techo[N].min())
        if ell < piso - TOL_PRECIO or ell > tope + TOL_PRECIO:
            continue
        ell = min(max(ell, piso), tope)
        z = techo.copy()
        z[N] = ell
        z[F] = piso
        q = _sirve(E, d, z) if q_fijo is None else q_fijo
        qN = q[N]
        if float(qN.max() - qN.min()) > tol_q:
            continue
        nivel = float(qN.min())
        if T.size and np.any(q[T] > nivel + tol_q):
            continue
        if F.size and np.any(q[F] < nivel - tol_q):
            continue
        estado = dict(T=T, N=N, F=F, ell=float(ell), z=z, q=q.copy())
        for k, h in enumerate(hallados):
            if _mismo_estado(estado, h, tol_q):
                if h["F"].size and not F.size:
                    hallados[k] = estado
                break
        else:
            hallados.append(estado)
    return hallados


def _mismo_estado(a: dict, b: dict, tol_q: float) -> bool:
    return (np.allclose(a["z"], b["z"], rtol=0.0, atol=10 * TOL_PRECIO)
            and np.allclose(a["q"], b["q"], rtol=0.0, atol=10 * tol_q))


def _regla_entre_estados(z: np.ndarray, q: np.ndarray, estados: list,
                         tol_q: float, paso: str) -> None:
    """La regla de saturacion (pasos 5 y 6) se publica siempre, como regla
    declarada (D53). Si hay reposos y la regla no cae en ninguno, la regla
    contradice el juego: se falla en voz alta. Sin reposos (n_soluciones = 0),
    la regla queda como declarada, sin respaldo estacionario."""
    if estados and not any(_mismo_estado(dict(z=z, q=q), h, tol_q)
                           for h in estados):
        raise ValueError(
            f"la regla del {paso} da precios {z} y reparto {q}, que no son "
            f"ninguno de los {len(estados)} reposos de la hora")


def _elige_paso3(estados: list) -> dict:
    """Con mas de un reposo del paso 3, el de mas compradores interiores (el
    llenado mas amplio) y, a igualdad, el de precio comun mas bajo; a igualdad
    de los dos, el primero de la enumeracion. `n_soluciones` lo deja anotado."""
    return sorted(estados, key=lambda h: (-h["N"].size, h["ell"]))[0]


def _precio_uniforme(q: np.ndarray, pi: np.ndarray, techo: np.ndarray,
                     piso: float) -> float:
    """Paso 8 (D51): p_u con sum_i min(p_u, techo_i) q_i = sum_i pi_i q_i.

    La funcion de la izquierda es lineal por tramos y creciente en p_u; se
    resuelve exacta en el tramo que contiene el ingreso. Existe porque el
    ingreso del reposo esta entre piso·E y sum techo_i q_i.
    """
    servidos = np.flatnonzero(q > 0.0)
    if servidos.size == 0:
        return float(piso)
    ingreso = float(np.dot(pi[servidos], q[servidos]))
    orden = np.argsort(techo[servidos], kind="stable")
    t = techo[servidos][orden]
    w = q[servidos][orden]
    base, peso, inferior = 0.0, float(w.sum()), float(piso)
    for k in range(t.size):
        p = (ingreso - base) / peso
        if p <= t[k]:
            if p < inferior - TOL_PRECIO:
                raise ValueError(
                    f"precio uniforme {p:.6f} (COP/kWh) bajo el piso "
                    f"{inferior:.6f}: el ingreso del reposo no cubre piso·E")
            return float(max(p, inferior))
        base += t[k] * w[k]
        peso -= w[k]
        inferior = float(t[k])
        if peso <= 0.0:
            break
    techos_q = float(np.dot(t, w))
    if ingreso - techos_q <= 1e-12 * max(1.0, abs(techos_q)):
        return float(t[-1])
    raise ValueError(f"el ingreso del reposo {ingreso:.6f} (COP) pasa de "
                     f"sum techo·q = {techos_q:.6f}: algun precio sobre su "
                     f"techo")


# ─── paso 1: quien entra y el piso del juego (D61, D63 a D65) ─────────────


def _despachan(desp: np.ndarray) -> np.ndarray:
    """Los vendedores que despachan de verdad: el polvo de redondeo que le
    toque a uno (lo que queda de una resta en el orden de merito) no fija el
    piso ni cuenta para la cobertura. El umbral es TOL_ENERGIA_REL relativo a
    lo despachado en la hora, es decir 1e-9 veces esa suma.

    ES UNA GUARDA DE REDONDEO, NO UN FILTRO DE VENDEDORES PEQUENOS. El corte
    de esta funcion es exacto y se calcula: con 10 (kWh) despachados en la
    hora esta en 1e-8 (kWh). Por debajo, el sobrante se absorbe; por encima,
    el vendedor cuenta aunque sea minusculo, y entonces puede fijar el piso.
    La horquilla de 1e-8 a 1e-7 (kWh) que se cita a veces no es de aqui: es
    el intervalo en que se acoto por medicion el corte de `_caminata`.

    OJO CON LAS CIFRAS QUE SE CITEN AQUI: la perdida maxima medida de 1e-9
    relativo y 2e-9 (kWh) en 40 000 horas es de la SELECCION DE NIVEL de
    `_caminata`, que usa la misma constante con otra base
    (TOL_ENERGIA_REL·max(1, maximo)), y no de este filtro. Que las dos bases
    no coincidan es lo que obliga a `_comprueba` a verificar una desigualdad
    y no la igualdad del piso (revision de la tarea 5a, importante 1)."""
    total = float(desp.sum())
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError(f"no hay nada despachado que medir: la suma de lo "
                         f"despachado es {total}")
    return desp > TOL_ENERGIA_REL * total


def _caminata(s: np.ndarray, d: np.ndarray, techo: np.ndarray,
              piso_j: np.ndarray, comp: np.ndarray, vendibles: np.ndarray,
              vend_excluidos: tuple) -> DespachoHora:
    """D65: la caminata competitiva sobre los pisos (`despacho="piso"`).

    Niveles: los pisos distintos de los vendedores con ganancia posible, en
    orden ascendente (empates dentro de TOL_PISO; el nivel vale el mayor piso
    de su grupo, para que todo vendedor del nivel quede en o bajo el). Para
    cada nivel p, S(p) = oferta de los de piso_j <= p y D(p) = demanda de los
    compradores con techo_i >= p. El nivel de cierre p* es el MENOR que
    maximiza min(S, D), con tolerancia TOL_ENERGIA_REL·max(1, maximo). Entran
    los compradores con techo_i >= p* y pueden vender los vendedores con
    piso_j <= p*; E = min(S(p*), D(p*)). Si S(p*) <= D(p*) despachan todos; si
    no, por piso creciente hasta E, con llenado por niveles en el grupo
    empatado.

    LA TOLERANCIA DEL NIVEL ES UNA GUARDA DE REDONDEO, no un filtro de
    vendedores pequenos (revision de la tarea 5a, importante 2). Solo absorbe
    diferencias de volumen por debajo de 1e-9 relativo: la perdida maxima
    medida es 1e-9 relativo y 2e-9 (kWh) en 40 000 horas. UN VENDEDOR MARGINAL
    MINUSCULO SI SUBE EL PISO DE TODA LA HORA: con 10 (kWh) en el nivel bajo,
    uno de 1e-7 (kWh) en un nivel alto lleva el piso de 616,46 a 693
    (COP/kWh), un 12 % de precio por una diezmillonesima de la energia. Eso es
    la subasta de precio uniforme haciendo lo que hace, y es el riesgo 2 de
    `fable-retiro-report.md`: se mide en M-J, no se corrige aqui.

    Por la minimalidad de p*, el ultimo despachado tiene piso p* (derivado por
    Fable): con compradores cortos, la oferta de los niveles de abajo no
    llega a D(p*), porque si llegara el nivel de abajo tambien maximizaria. Es
    una propiedad de la caminata, no una guarda: `_comprueba` verifica la
    desigualdad que la cobertura necesita (ver alli por que).
    """
    sa, pa = s[vendibles], piso_j[vendibles]
    tc, dc = techo[comp], d[comp]
    niveles, oferta = [], 0.0
    for g in _grupos(pa, TOL_PISO, descendente=False):
        p = float(pa[g].max())
        oferta += float(sa[g].sum())
        niveles.append((p, min(oferta, float(dc[tc >= p].sum()))))
    maximo = max(v for _, v in niveles)
    if maximo <= 0.0:
        # No ocurre: un vendedor con ganancia posible tiene su piso a lo sumo
        # en el techo mayor, y a ese nivel S > 0 y D > 0. Es ValueError y no
        # AssertionError a proposito, como el del paso 5: el ramal del motor
        # solo recoge ValueError, y asi la hora queda con su motivo en vez de
        # tumbar al trabajador (revision de la tarea 5a, menor 4).
        raise ValueError("la caminata da volumen 0 con vendedores que tienen "
                         "ganancia posible, que no puede ocurrir tras excluir "
                         "a los de D61")
    tol = TOL_ENERGIA_REL * max(1.0, maximo)
    p_star = next(p for p, v in niveles if v >= maximo - tol)

    puede = pa <= p_star
    pueden = vendibles[puede]
    no_despachados = tuple(int(j) for j in vendibles[~puede])
    dentro = comp[tc >= p_star]
    bajo_piso = tuple(int(i) for i in comp[tc < p_star])
    sp = s[pueden]
    oferta, demanda = float(sp.sum()), float(d[dentro].sum())
    if oferta <= demanda:
        desp = sp.copy()
    else:
        desp = _despacho(sp, piso_j[pueden], demanda, "piso")
    s_desp = np.zeros(s.size)
    s_desp[pueden] = desp
    return DespachoHora(
        causa="", piso=float(p_star), E=float(min(oferta, demanda)),
        dentro=tuple(int(i) for i in dentro),
        pueden_vender=tuple(int(j) for j in pueden), s_despachado=s_desp,
        excluidos_bajo_piso=bajo_piso, vendedores_excluidos=vend_excluidos,
        vendedores_no_despachados=no_despachados, despacho="piso")


def _lazo_piso_maximo(s: np.ndarray, d: np.ndarray, b: Optional[np.ndarray],
                      techo: np.ndarray, piso_j: np.ndarray, comp: np.ndarray,
                      vendibles: np.ndarray, vend_excluidos: tuple,
                      despacho: str) -> DespachoHora:
    """D63 con `despacho="costo"` o `"llenado"`: el piso del juego es el
    MAXIMO de los pisos de los que despachan, con el lazo de exclusion de
    compradores bajo ese piso (D61 parcial).

    Pueden vender todos los vendedores con ganancia posible; la rama la decide
    su oferta frente a la demanda de los compradores en el juego. Con
    vendedores cortos despachan todos; con compradores cortos, por b_j
    creciente ("costo", el merito de D52) o por niveles entre todos
    ("llenado").

    EL LAZO YA NO ES MONOTONO. Con el minimo (D62) sacar un comprador nunca
    bajaba el piso; con el maximo, sacarlo baja la demanda, el merito despacha
    a menos vendedores y el piso puede bajar hasta readmitirlo. Por eso cada
    vuelta recalcula quien entra desde TODOS los compradores activos (un punto
    fijo: dentro = {techo_i >= piso(dentro)}), y si el lazo vuelve a un
    conjunto ya visto (oscila) o pasa de MAX_VUELTAS_LAZO vueltas, ValueError.
    El comprador de techo mayor nunca sale, porque todo vendedor con ganancia
    posible tiene su piso a lo sumo en ese techo.
    """
    sa, pa = s[vendibles], piso_j[vendibles]
    ba = None if b is None else b[vendibles]
    dentro = comp.copy()
    vistos = {tuple(dentro.tolist())}
    for _ in range(MAX_VUELTAS_LAZO):
        demanda = float(d[dentro].sum())
        if sa.sum() <= demanda:
            desp = sa.copy()
        else:
            desp = _despacho(sa, ba, demanda, despacho)
        despachan = _despachan(desp)
        if not np.any(despachan):
            raise ValueError(
                f"D63 con despacho {despacho!r}: el despacho no deja a ningun "
                f"vendedor sobre el polvo de redondeo, y el piso del juego "
                f"seria el maximo de un conjunto vacio")
        piso = float(np.max(pa[despachan]))
        nuevo = comp[techo[comp] >= piso]
        if np.array_equal(nuevo, dentro):
            break
        clave = tuple(nuevo.tolist())
        if clave in vistos:
            raise ValueError(
                f"D63 con despacho {despacho!r}: el lazo de exclusion de "
                f"compradores bajo el piso maximo oscila (vuelve a los "
                f"compradores {list(clave)} con el piso {piso:.6f} (COP/kWh))")
        vistos.add(clave)
        dentro = nuevo
    else:
        raise ValueError(
            f"D63 con despacho {despacho!r}: el lazo de exclusion de "
            f"compradores no converge en {MAX_VUELTAS_LAZO} vueltas")
    s_desp = np.zeros(s.size)
    s_desp[vendibles] = desp
    return DespachoHora(
        causa="", piso=piso, E=float(min(sa.sum(), d[dentro].sum())),
        dentro=tuple(int(i) for i in dentro),
        pueden_vender=tuple(int(j) for j in vendibles), s_despachado=s_desp,
        excluidos_bajo_piso=tuple(int(i) for i in np.setdiff1d(comp, dentro)),
        vendedores_excluidos=vend_excluidos, vendedores_no_despachados=(),
        despacho=despacho)


def _paso1(s: np.ndarray, d: np.ndarray, b: Optional[np.ndarray],
           techo: np.ndarray, piso_j: np.ndarray,
           despacho: str) -> DespachoHora:
    """Paso 1 sobre entradas ya comprobadas: activos, D61 y el despacho de la
    opcion. Las comprobaciones de techo frente a piso miran solo a los
    compradores con deficit (D61)."""
    vend = np.flatnonzero(s > 0.0)
    comp = np.flatnonzero(d > 0.0)
    J = s.size

    def sin(causa, excluidos=()):
        return DespachoHora(
            causa=causa,
            piso=float(np.min(piso_j[vend])) if vend.size else 0.0, E=0.0,
            dentro=(), pueden_vender=(), s_despachado=np.zeros(J),
            excluidos_bajo_piso=(), vendedores_excluidos=tuple(excluidos),
            vendedores_no_despachados=(), despacho=despacho)

    if vend.size == 0 or comp.size == 0:
        return sin("sin_mercado")
    # D61, del lado de los vendedores (extension simetrica, decision del
    # controlador del 2026-09-17): un vendedor activo cuyo piso supera el techo
    # de TODOS los compradores activos no tiene ganancia posible con nadie y
    # queda fuera del despacho. Si no queda ninguno, la hora es «sin_ganancia»,
    # sin error: es lo mismo que una caminata con volumen maximo 0.
    techo_mayor = float(np.max(techo[comp]))
    sin_ganancia_j = piso_j[vend] > techo_mayor
    vend_excluidos = tuple(int(j) for j in vend[sin_ganancia_j])
    vendibles = vend[~sin_ganancia_j]
    if vendibles.size == 0:
        return sin("sin_ganancia", vend_excluidos)
    if despacho == "piso":
        return _caminata(s, d, techo, piso_j, comp, vendibles, vend_excluidos)
    return _lazo_piso_maximo(s, d, b, techo, piso_j, comp, vendibles,
                             vend_excluidos, despacho)


# ─── funciones publicas ────────────────────────────────────────────────────


def despacho_competitivo(s, d, techo, piso_j, despacho: str = "piso", *,
                         b=None) -> DespachoHora:
    """Paso 1 del reposo (D61, D63 a D65): quien entra de cada lado, el piso
    del juego y lo que vende cada vendedor.

    Entradas: `s` excedentes de los J vendedores (kWh); `d` deficits de los I
    compradores (kWh); `techo` de cada comprador y `piso_j` de cada vendedor
    (COP/kWh), que admiten un escalar. `b` (COP/kWh), solo con "costo".

    `despacho="piso"` (defecto, D64 y D65): la caminata competitiva.
      1. Activos: vendedores con s_j > 0 y compradores con d_i > 0.
      2. Niveles: los pisos distintos de los activos, ascendentes; S(p) =
         oferta con piso_j <= p y D(p) = demanda con techo_i >= p.
      3. p* = el menor nivel que maximiza min(S(p), D(p)). Si el maximo es 0,
         la hora es «sin_ganancia» (D61), con todos los activos en
         `vendedores_excluidos`.
      4. Entran los compradores con techo_i >= p* (los demas, a
         `excluidos_bajo_piso`); pueden vender los de piso_j <= p* (los demas,
         a `vendedores_no_despachados`, salvo los sin ganancia posible con
         nadie, que van a `vendedores_excluidos`).
      5. E = min(S(p*), D(p*)); si S(p*) <= D(p*) despachan todos, y si no, por
         piso creciente hasta E con llenado por niveles en el empate.
      6. El piso del juego es p*, el del ultimo despachado.
    `despacho="costo"`: merito por b_j, como D52; el piso del juego es el
    maximo de los despachados, con el lazo de exclusion de compradores bajo
    ese piso (`_lazo_piso_maximo`, con limite de vueltas).
    `despacho="llenado"`: despachan por niveles todos los que pueden vender
    (D61); el piso es el maximo de sus pisos, con el mismo lazo.
    """
    if despacho not in DESPACHOS_VENDEDORES:
        raise ValueError(f"despacho={despacho!r}; use uno de "
                         f"{DESPACHOS_VENDEDORES}")
    s = _vector("s", s)
    d = _vector("d", d)
    techo = _vector("techo", techo, d.size, escalar=True)
    piso_j = _vector("piso_j", piso_j, s.size, escalar=True)
    _no_negativo("s", s)
    _no_negativo("d", d)
    if despacho == "costo":
        if b is None:
            raise ValueError("el despacho 'costo' ordena por b_j y exige b")
        b = _vector("b", b, s.size)
    elif b is not None:
        b = _vector("b", b, s.size)
    return _paso1(s, d, b, techo, piso_j, despacho)


def presupuesto_precios(techo, piso: float, *, modo: str = "sigma",
                        sigma: Optional[float] = None,
                        pi_gs: Optional[float] = None) -> float:
    """Paso 2 (D50): el presupuesto S de los precios de los compradores.

    El bloque de precios es un replicador sobre un presupuesto fijo (H-87
    sec. 6, H-88): el juego redistribuye S entre los compradores pero no lo
    fija. Tres modos:

    "sigma" (produccion): S = sum_i [piso + sigma·(techo_i - piso)], con
        sigma = (I-1)/I si `sigma` es None (el caso central) o el valor dado,
        en [0, 1] (el barrido sigma en {0, 1/2, (I-1)/I, 1}). Es el Algoritmo 3
        (cada uno abre en I·pi_gs/(I+1)) mas la ec. 24 (el virtual sube a su
        techo y se congela), generalizado a la banda como en H-32. Con I = 1 y
        sigma = (I-1)/I da el piso.
    "algoritmo3": la regla literal del articulo, para reproducir el caso de
        Chacon. Los I+1 jugadores (compradores y virtual) abren en
        I·pi_gs/(I+1) y el virtual se clava en pi_gs: S = (I-1)·pi_gs. Exige
        techo escalar `pi_gs` (todos los techos iguales a el). Si el precio
        comun S/I cae bajo el piso (H-32), ValueError.
    "c136": el presupuesto del arranque de precios de hoy del acoplado
        (`core/coupled_ode_convergence.py`, C-136, H-32, H-45): la suma de los
        arranques de los compradores y del virtual menos el techo mayor, en el
        que se clava el virtual. Incluye el interruptor: el arranque comun
        sum(techo)/(I+1) se usa para cada uno solo si cae dentro de su banda;
        si no, el de ese jugador es piso + (techo - piso)·I/(I+1).
        H-32 con dos compradores: si el arranque comun cae dentro de las dos
        bandas (piso bajo frente a los techos), el interruptor no dispara y
        S = sum(techo) - techo mayor = el techo menor, que queda bajo 2·piso
        cuando el techo menor no llega al doble del piso. Esta funcion lo
        devuelve tal cual, porque es el invariante que tendria la dinamica;
        `resuelve_reposo` lo rechaza con ValueError (451 horas de ocho de los
        trece casos de la matriz del 2026-09-15, con los retirados y con D62;
        464 antes de D62; con el piso marginal de D63 el piso del juego cambia
        en las horas con pisos distintos y la cuenta puede cambiar: se mide en
        la matriz del servidor). Es
        un modo de comparacion, no de produccion: esas horas quedan fuera de
        las comparaciones con «c136».
    """
    if modo not in MODOS_PRESUPUESTO:
        raise ValueError(f"modo={modo!r}; use uno de {MODOS_PRESUPUESTO}")
    if sigma is not None and modo != "sigma":
        raise ValueError(f"sigma solo aplica al modo 'sigma', no a {modo!r}")
    if pi_gs is not None and modo != "algoritmo3":
        raise ValueError(f"pi_gs solo aplica al modo 'algoritmo3', no a "
                         f"{modo!r}")
    techo = _vector("techo", techo)
    I = techo.size
    if I == 0:
        raise ValueError("presupuesto de precios sin compradores")
    piso = float(piso)
    if not np.isfinite(piso):
        raise ValueError(f"piso no finito: {piso}")
    if np.any(techo < piso):
        raise ValueError(f"techo bajo el piso {piso}: {techo}")

    if modo == "sigma":
        if sigma is None:
            s = (I - 1) / I
        else:
            s = float(sigma)
            if not np.isfinite(s) or s < 0.0 or s > 1.0:
                raise ValueError(f"sigma={sigma!r} fuera de [0, 1]")
        return float(np.sum(piso + s * (techo - piso)))

    if modo == "algoritmo3":
        if pi_gs is None:
            raise ValueError("el modo 'algoritmo3' exige el techo escalar "
                             "pi_gs")
        pgs = float(pi_gs)
        if not np.isfinite(pgs):
            raise ValueError(f"pi_gs no finito: {pi_gs}")
        if not np.all(techo == pgs):
            raise ValueError(f"el modo 'algoritmo3' exige techo escalar: "
                             f"los techos {techo} no son todos pi_gs = {pgs}")
        S = (I - 1) * pgs
        if S / I < piso - TOL_PRECIO:
            raise ValueError(
                f"H-32: con el Algoritmo 3 el precio comun (I-1)/I·pi_gs = "
                f"{S / I:.4f} (COP/kWh) cae bajo el piso {piso:.4f}; la regla "
                f"literal supone un piso despreciable frente al techo")
        return float(S)

    # "c136", al pie de la letra del arranque de precios de
    # core/coupled_ode_convergence.py (lineas 370 y 385 a 396). La suma de
    # los I+1 precios se conserva en `_rhs` (replicador); con la barrera, el
    # virtual se clava en el techo mayor y los compradores se quedan el resto.
    simple = float(np.sum(techo))
    n_todos = I + 1
    ci = simple / n_todos
    techo_mayor = float(np.max(techo))
    ci_i = np.where((piso < ci) & (ci < techo), ci,
                    piso + (techo - piso) * I / n_todos)
    ci_v = (ci if piso < ci < techo_mayor
            else piso + (techo_mayor - piso) * I / n_todos)
    return float(np.sum(ci_i) + ci_v - techo_mayor)


def resuelve_reposo(s, d, b, techo, piso_j, *, modo_presupuesto: str = "sigma",
                    sigma: Optional[float] = None,
                    pi_gs: Optional[float] = None,
                    regla_precio: str = "uniforme",
                    despacho_vendedores: str = "piso") -> ReposoHora:
    """El mercado de una hora en el reposo (sec. 5.1, pasos 1 a 6 y 8).

    Entradas: `s` excedentes de los J vendedores (kWh); `d` deficits de los I
    compradores (kWh); `b` costos lineales de los vendedores (COP/kWh), a_j = 0
    (CAL-32); `techo` de cada comprador (H-45) y `piso_j` de cada vendedor
    (CAL-47, H-49) (COP/kWh). `techo` y `piso_j` admiten un escalar.

    Paso 1 (`despacho_competitivo`; D61, D63 a D65). Activos: vendedores con
        s_j > 0 y compradores con d_i > 0. D61 del lado de los vendedores: el
        vendedor activo cuyo piso_j supera el maximo techo de los compradores
        activos queda fuera (en `vendedores_excluidos`); si no queda ninguno,
        la hora es «sin_ganancia» (sin mercado, con su causa). Con
        `despacho_vendedores="piso"` (defecto), la caminata competitiva fija
        el nivel de cierre p*, que es el piso del juego (el del vendedor
        marginal, D63): entran los compradores con techo_i >= p* (los demas, a
        `excluidos_bajo_piso`, D61 parcial) y pueden vender los vendedores con
        piso_j <= p* (los demas, a `vendedores_no_despachados`). Con "costo" y
        "llenado", el piso del juego es el maximo de los despachados, con el
        lazo de exclusion de compradores. E = min(oferta de los que pueden
        vender, demanda de los que quedan).
    Paso 2. S = presupuesto_precios(techo, piso, ...) sobre los que quedan.
    Vendedores cortos (sum s <= sum d). Todos los que pueden vender venden su
        excedente.
        Paso 3: los reposos con F vacio (N interiores a precio comun, los demas
        en su techo); con mas de uno, `_elige_paso3`.
        Paso 5 (D53), si no hay ninguno: la regla de saturacion con el orden de
        aptitud por lo que cada uno recibe en el llenado por niveles; el
        reparto sale por prioridad de precio.
    Compradores cortos (sum s > sum d), paso 6. q_i = d_i; los vendedores
        despachan segun `despacho_vendedores` (D64: por piso; o por costo o por
        llenado); precios con la regla del paso 5 sobre todos, ordenados por
        deficit creciente.
    Paso 4. Emparejamiento de rango uno: P_ji = s_j·q_i/E, con s_j lo
        despachado.
    Paso 8 (D51). p_u conserva el ingreso del reposo; "uniforme" liquida a
        min(p_u, techo_i) y "puja" a pi_reposo. Los dos quedan calculados.
    D54 y D66. Con un solo comprador, su precio es el piso del juego en todos
        los modos, y S es ese piso: con "piso", el piso marginal p*.
    D69. La prima de los vendedores se descompone en renta inframarginal y
        parte del juego.
    Sin vendedores o sin compradores con cantidad: "sin_mercado". Sin mercado
        (tambien «sin_ganancia»), energias y dinero en cero y precios en el
        techo de cada comprador.
    """
    if modo_presupuesto not in MODOS_PRESUPUESTO:
        raise ValueError(f"modo_presupuesto={modo_presupuesto!r}; use uno de "
                         f"{MODOS_PRESUPUESTO}")
    if regla_precio not in REGLAS_PRECIO:
        raise ValueError(f"regla_precio={regla_precio!r}; use uno de "
                         f"{REGLAS_PRECIO}")
    if despacho_vendedores not in DESPACHOS_VENDEDORES:
        raise ValueError(f"despacho_vendedores={despacho_vendedores!r}; use "
                         f"uno de {DESPACHOS_VENDEDORES}")
    if sigma is not None and modo_presupuesto != "sigma":
        raise ValueError(f"sigma solo aplica al modo 'sigma', no a "
                         f"{modo_presupuesto!r}")
    if pi_gs is not None and modo_presupuesto != "algoritmo3":
        raise ValueError(f"pi_gs solo aplica al modo 'algoritmo3', no a "
                         f"{modo_presupuesto!r}")
    if sigma is not None:
        sg = float(sigma)
        if not np.isfinite(sg) or sg < 0.0 or sg > 1.0:
            raise ValueError(f"sigma={sigma!r} fuera de [0, 1]")

    s = _vector("s", s)
    J = s.size
    d = _vector("d", d)
    I = d.size
    b = _vector("b", b, J)
    techo = _vector("techo", techo, I, escalar=True)
    piso_j = _vector("piso_j", piso_j, J, escalar=True)
    _no_negativo("s", s)
    _no_negativo("d", d)
    opciones = (modo_presupuesto, sigma, regla_precio, despacho_vendedores)

    # Paso 1 (D61, D63 a D65): quien entra de cada lado, el piso del juego y
    # lo que vende cada vendedor.
    paso1 = _paso1(s, d, b, techo, piso_j, despacho_vendedores)
    if paso1.causa:
        return _sin_mercado(paso1, techo, int(np.count_nonzero(d > 0.0)),
                            *opciones)
    piso = paso1.piso
    dentro = np.asarray(paso1.dentro, dtype=int)
    pueden = np.asarray(paso1.pueden_vender, dtype=int)
    # El orden de despacho de los vendedores con ganancia posible, estable por
    # indice: por piso con "piso" (D64), por costo con las otras dos.
    vendibles = np.setdiff1d(np.flatnonzero(s > 0.0),
                             np.asarray(paso1.vendedores_excluidos, dtype=int))
    clave = piso_j if despacho_vendedores == "piso" else b
    orden_merito = tuple(int(vendibles[k]) for k in
                         np.argsort(clave[vendibles], kind="stable"))
    # La rama (vendedores o compradores cortos) la decide la oferta de todos los
    # vendedores QUE PUEDEN VENDER: si la oferta de los que despachan iguala la
    # demanda, la hora sigue en compradores cortos, y q = d es lo mismo que
    # daria la prioridad de precio con E = sum d (lo prueba
    # `test_oferta_de_los_que_despachan_igual_a_la_demanda`).
    sa = s[pueden]

    da, ta = d[dentro], techo[dentro]
    Ia = dentro.size
    E = float(min(sa.sum(), da.sum()))
    tol_q = TOL_ENERGIA_REL * max(1.0, E)
    sigma_usada = None
    if modo_presupuesto == "sigma":
        sigma_usada = (Ia - 1) / Ia if sigma is None else float(sigma)

    if Ia == 1:
        # D54 y D66: un solo comprador paga el piso, como en el articulo, en
        # todos los modos; el piso ya es el del vendedor marginal (D63), de
        # modo que los inframarginales cobran su renta.
        S = piso
        z = np.array([piso])
        ell = piso
        n_sol = 1
        regimen = "un_comprador"
        qa = np.array([E]) if sa.sum() <= da.sum() else da.copy()
    else:
        S = presupuesto_precios(ta, piso, modo=modo_presupuesto, sigma=sigma,
                                pi_gs=pi_gs)
        if S < Ia * piso - TOL_PRECIO or S > float(ta.sum()) + TOL_PRECIO:
            h32 = ""
            if modo_presupuesto == "c136":
                h32 = ("; es H-32 en el modo 'c136': el arranque comun "
                       "sum(techo)/(I+1) cae dentro de las bandas y el virtual "
                       "se lleva el techo mayor (con dos compradores, S es el "
                       "techo menor, bajo 2·piso)")
            raise ValueError(
                f"presupuesto S = {S:.6f} (COP/kWh) fuera de [I·piso, "
                f"sum techo] = [{Ia * piso:.6f}, {float(ta.sum()):.6f}]{h32}")
        if sa.sum() <= da.sum():
            estados = _estados_reposo(E, da, ta, piso, S, q_fijo=None)
            paso3 = [h for h in estados if not h["F"].size]
            if paso3:
                elegido = _elige_paso3(paso3)
                z, qa, ell = elegido["z"], elegido["q"], elegido["ell"]
                T = elegido["T"]
                reciben = bool(np.any(qa[T] > tol_q)) if T.size else False
                sin_nada = bool(np.any(qa[T] <= tol_q)) if T.size else False
                if not T.size:
                    regimen = "interiores"
                elif reciben and sin_nada:
                    regimen = "mixto"
                elif reciben:
                    regimen = "topados"
                else:
                    regimen = "excluidos"
            else:
                # El orden de aptitud sale del llenado puro, no del q del
                # reposo: siempre que hay reposo los dos coinciden (medido en
                # la revision de la tarea 1), y sin reposo el q del reposo no
                # da un orden estable (oscila entre dos), mientras el llenado
                # da una regla declarada determinista.
                llenado = _llenado_por_niveles(da, E)
                z, _, ell = _regla_saturacion(llenado, ta, piso, S, tol_q)
                qa = _sirve(E, da, z)
                _regla_entre_estados(z, qa, estados, tol_q, "paso 5")
                regimen = "suma_no_cabe"
        else:
            qa = da.copy()
            z, _, ell = _regla_saturacion(qa, ta, piso, S, tol_q)
            estados = _estados_reposo(E, da, ta, piso, S, q_fijo=qa)
            _regla_entre_estados(z, qa, estados, tol_q, "paso 6")
            regimen = "compradores_cortos"
        n_sol = len(estados)

    # Paso 4: emparejamiento de rango uno sobre lo despachado.
    q = np.zeros(I)
    q[dentro] = qa
    s_desp = paso1.s_despachado.copy()
    P = np.outer(s_desp, q) / E

    pi_reposo = techo.copy()
    pi_reposo[dentro] = z
    excluidos = tuple(int(i) for i in dentro if q[i] <= tol_q)

    # Paso 8: liquidacion.
    p_u = _precio_uniforme(q, pi_reposo, techo, piso)
    if regla_precio == "uniforme":
        p_liq = np.minimum(p_u, techo)
    else:
        p_liq = pi_reposo.copy()

    excedente = float(np.sum((techo[None, :] - piso_j[:, None]) * P))
    ingreso = ingreso_por_vendedor(P, p_liq)
    ingreso_total = float(ingreso.sum())
    prima = float(ingreso_total - np.dot(piso_j, s_desp))
    parte = prima / excedente if abs(excedente) > 1e-12 else 0.0
    # D69: la prima descompuesta. La renta inframarginal es lo que cobran
    # sobre su piso los vendedores de piso menor que el marginal; la parte del
    # juego, lo que el presupuesto de los compradores sube el precio medio
    # (p_medio = ingreso / E) sobre el piso marginal: (p_medio - p*)·E, que es
    # ingreso - p*·E.
    renta = float(np.dot(piso - piso_j, s_desp))
    parte_juego = float(ingreso_total - piso * E)

    resultado = ReposoHora(
        P=P, q=q, s_despachado=s_desp, E=E, piso=piso, piso_marginal=piso,
        S=float(S), ell=float(ell), pi_reposo=pi_reposo, p_u=float(p_u),
        p_liquidado=p_liq, regimen=regimen, excluidos=excluidos,
        excluidos_bajo_piso=paso1.excluidos_bajo_piso,
        vendedores_excluidos=paso1.vendedores_excluidos,
        vendedores_no_despachados=paso1.vendedores_no_despachados,
        orden_merito=orden_merito, n_soluciones=int(n_sol),
        excedente=excedente, ingreso_vendedores=ingreso,
        parte_vendedor=float(parte), renta_inframarginal=renta,
        parte_juego=parte_juego, modo_presupuesto=modo_presupuesto,
        sigma=sigma_usada, regla_precio=regla_precio,
        despacho_vendedores=despacho_vendedores)
    _comprueba(resultado, s, d, techo, dentro, piso_j, paso1.pueden_vender)
    return resultado


def _sin_mercado(paso1: DespachoHora, techo: np.ndarray, n_comp: int,
                 modo: str, sigma, regla: str, despacho: str) -> ReposoHora:
    """La hora sin mercado: «sin_mercado» (sin vendedores o sin compradores con
    cantidad) o «sin_ganancia» (D61), con la causa en `paso1.causa`. La
    convencion de precios es la de un comprador fuera del juego en una hora con
    mercado: su techo. El piso es el minimo de los vendedores activos, o 0 sin
    ellos; el orden de merito queda vacio porque nadie vende; la renta y la
    parte del juego, en cero. `vendedores_excluidos`: en «sin_ganancia», todos
    los activos. `n_comp`: los compradores con deficit, para la sigma."""
    J, I = paso1.s_despachado.size, techo.size
    sigma_usada = None
    if modo == "sigma":
        if sigma is not None:
            sigma_usada = float(sigma)
        elif n_comp:
            sigma_usada = (n_comp - 1) / n_comp
    return ReposoHora(
        P=np.zeros((J, I)), q=np.zeros(I), s_despachado=np.zeros(J), E=0.0,
        piso=paso1.piso, piso_marginal=paso1.piso, S=0.0,
        ell=None, pi_reposo=techo.copy(), p_u=0.0, p_liquidado=techo.copy(),
        regimen=paso1.causa, excluidos=(), excluidos_bajo_piso=(),
        vendedores_excluidos=paso1.vendedores_excluidos,
        vendedores_no_despachados=(), orden_merito=(),
        n_soluciones=0, excedente=0.0, ingreso_vendedores=np.zeros(J),
        parte_vendedor=0.0, renta_inframarginal=0.0, parte_juego=0.0,
        modo_presupuesto=modo, sigma=sigma_usada,
        regla_precio=regla, despacho_vendedores=despacho)


def _comprueba(r: ReposoHora, s: np.ndarray, d: np.ndarray,
               techo: np.ndarray, dentro: np.ndarray,
               piso_j: np.ndarray, pueden_vender: tuple) -> None:
    """Fallar en voz alta (H-50, CAL-28b): las identidades de la hora.

    Con D63 se anaden cuatro: el piso del juego no queda bajo el mayor piso de
    los que despachan; el piso del juego es el de algun vendedor que puede
    vender; el teorema de cobertura del rango uno (ningun despachado cobra de
    media bajo su piso, con TOL_COBERTURA_REL relativa al piso); y la
    descomposicion de la prima de D69 (renta + parte del juego = prima,
    TOL_PRIMA_REL). Los despachados son los de `_despachan`: el polvo de
    redondeo no cuenta.
    """
    tol_q = 1e-6 * max(1.0, r.E)
    campos = (r.P, r.q, r.s_despachado, r.pi_reposo, r.p_liquidado,
              r.ingreso_vendedores)
    if not all(np.all(np.isfinite(c)) for c in campos) or not np.all(
            np.isfinite([r.E, r.piso, r.S, r.p_u, r.excedente,
                         r.parte_vendedor, r.renta_inframarginal,
                         r.parte_juego])):
        raise ValueError("el reposo produjo valores no finitos")
    if np.any(r.P < 0.0):
        raise ValueError("el reposo produjo energia negativa")
    if np.any(r.s_despachado > s + tol_q) or np.any(r.q > d + tol_q):
        raise ValueError("el reposo reparte mas que la capacidad de algun "
                         "agente")
    if np.any(np.abs(r.P.sum(axis=1) - r.s_despachado) > tol_q):
        raise ValueError("las filas de P no suman lo despachado")
    if abs(float(r.q.sum()) - r.E) > tol_q or \
            np.any(np.abs(r.P.sum(axis=0) - r.q) > tol_q):
        raise ValueError("el reparto del reposo no suma el volumen E")
    suma = float(r.pi_reposo[dentro].sum())
    if abs(suma - r.S) > 10 * TOL_PRECIO * max(1, dentro.size):
        raise ValueError(f"los precios del reposo suman {suma:.9f}, no el "
                         f"presupuesto S = {r.S:.9f} (COP/kWh)")
    servidos = r.q > 0.0
    if np.any(r.p_liquidado[servidos] < r.piso - TOL_PRECIO) or np.any(
            r.p_liquidado[servidos] > techo[servidos] + TOL_PRECIO):
        raise ValueError("un precio liquidado quedo fuera de [piso, techo]")
    if r.regla_precio == "uniforme":
        reposo = float(np.dot(r.pi_reposo, r.q))
        liquidado = float(np.dot(r.p_liquidado, r.q))
        if abs(liquidado - reposo) > 1e-9 * max(1.0, abs(reposo)):
            raise ValueError(f"la liquidacion uniforme no conserva el ingreso "
                             f"del reposo: {liquidado:.9f} frente a "
                             f"{reposo:.9f} (COP)")

    # D63: lo que la cobertura necesita es una DESIGUALDAD, el piso del juego
    # por encima del mayor piso de los que despachan, y que el piso del juego
    # sea el de algun vendedor que puede vender. La IGUALDAD con el mayor piso
    # de los despachados es una propiedad de la caminata, no una guarda: el
    # filtro de polvo de `_despachan` y la tolerancia del nivel de cierre no
    # miden sobre la misma base, y en una hora con dos vendedores de oferta
    # por debajo de 1e-9 relativo en niveles distintos la igualdad falla por
    # redondeo (revision de la tarea 5a, importante 1: 56 de 141 082 horas
    # adversarias). Tumbar esa hora detendria la matriz por nada: el precio
    # esta bien, y quien despacha cobra de sobra.
    desp = _despachan(r.s_despachado)
    if not np.any(desp):
        raise ValueError("el reposo no despacho a ningun vendedor en una hora "
                         "con mercado")
    marginal = float(np.max(piso_j[desp]))
    if r.piso < marginal - TOL_PISO * max(1.0, abs(marginal)) or \
            r.piso_marginal != r.piso:
        raise ValueError(f"D63: el piso del juego {r.piso:.9f} queda bajo el "
                         f"mayor piso de los que despachan {marginal:.9f} "
                         f"(COP/kWh): algun despachado cobraria bajo su piso")
    suyos = piso_j[np.asarray(pueden_vender, dtype=int)]
    if not np.any(np.abs(suyos - r.piso) <= TOL_PISO * np.maximum(
            1.0, np.abs(suyos))):
        raise ValueError(f"D63: el piso del juego {r.piso:.9f} (COP/kWh) no "
                         f"es el piso de ningun vendedor que puede vender "
                         f"({np.array2string(suyos, precision=6)}): el piso "
                         f"del juego es el de un vendedor, el marginal")
    # Teorema de cobertura del rango uno: con P_ji = s_j·q_i/E, todo
    # despachado cobra de media el precio medio de la hora, que no baja del
    # piso del juego, y el piso del juego no baja del suyo.
    medio = r.ingreso_vendedores[desp] / r.s_despachado[desp]
    cota = piso_j[desp] - TOL_COBERTURA_REL * np.maximum(1.0,
                                                          np.abs(piso_j[desp]))
    if np.any(medio < cota):
        k = int(np.argmax(cota - medio))
        j = int(np.flatnonzero(desp)[k])
        raise ValueError(f"D63: el vendedor {j} cobra de media "
                         f"{float(medio[k]):.9f} (COP/kWh), bajo su piso "
                         f"{float(piso_j[j]):.9f}")
    # D69: renta inframarginal + parte del juego = prima de los vendedores.
    ingreso = float(r.ingreso_vendedores.sum())
    costo = float(np.dot(piso_j, r.s_despachado))
    prima = ingreso - costo
    if abs(r.renta_inframarginal + r.parte_juego - prima) > \
            TOL_PRIMA_REL * max(1.0, abs(ingreso), abs(costo)):
        raise ValueError(f"D69: renta inframarginal "
                         f"{r.renta_inframarginal:.9f} + parte del juego "
                         f"{r.parte_juego:.9f} no es la prima {prima:.9f} "
                         f"(COP)")


def ingreso_por_vendedor(P, p_liquidado) -> np.ndarray:
    """Ingreso de cada vendedor, sum_i P_ji·p_i (COP). Lo usa la participacion
    de los vendedores (paso 7, C-151) en el motor."""
    P = np.asarray(P, dtype=float)
    if P.ndim != 2:
        raise ValueError(f"P debe ser una matriz (J, I); llego con forma "
                         f"{P.shape}")
    p = _vector("p_liquidado", p_liquidado, P.shape[1])
    if not np.all(np.isfinite(P)):
        raise ValueError("P tiene valores no finitos")
    return P @ p


def cotas_optimalidad(s, d, techo, piso_j, E: float):
    """Paso 9 (D55): el mejor y el peor reparto del mismo volumen E.

    El valor de un reparto es separable, sum_i techo_i·S_i - sum_j piso_j·s_j,
    con S_i lo que recibe cada comprador y s_j lo que vende cada vendedor.
    Optimo: llenar primero a los compradores de techo mas alto y despachar
    primero a los vendedores de piso mas bajo. Peor: al reves. Devuelve
    (optimo, peor) (COP). La captura del reposo es `captura(excedente,
    optimo)`.
    """
    s = _vector("s", s)
    d = _vector("d", d)
    techo = _vector("techo", techo, d.size, escalar=True)
    piso_j = _vector("piso_j", piso_j, s.size, escalar=True)
    _no_negativo("s", s)
    _no_negativo("d", d)
    E = float(E)
    if not np.isfinite(E) or E < 0.0:
        raise ValueError(f"volumen E = {E} no finito o negativo")
    tope = float(min(s.sum(), d.sum()))
    if E > tope + TOL_ENERGIA_REL * max(1.0, tope):
        raise ValueError(f"volumen E = {E} mayor que el lado corto {tope}")
    E = min(E, tope)

    def llena(cap, clave):
        x = np.zeros(cap.size)
        resto = E
        for k in sorted(range(cap.size), key=clave):
            x[k] = min(cap[k], resto)
            resto -= x[k]
        return x

    opt = (float(np.dot(techo, llena(d, lambda i: (-techo[i], i))))
           - float(np.dot(piso_j, llena(s, lambda j: (piso_j[j], j)))))
    peor = (float(np.dot(techo, llena(d, lambda i: (techo[i], i))))
            - float(np.dot(piso_j, llena(s, lambda j: (-piso_j[j], j)))))
    return opt, peor


def captura(excedente: float, optimo: float) -> float:
    """Captura del reposo, excedente / optimo (D55; el precio de la justicia de
    la actividad 3.3 es 1 - captura).

    Con optimo nulo (sin excedente que capturar: bandas nulas o volumen cero)
    la captura es 1 por convencion, si el excedente tambien es nulo. Fallan en
    voz alta: un excedente mayor que el optimo, un optimo negativo, y un
    excedente negativo (con optimo nulo o positivo), que solo puede venir de un
    vendedor despachado con el piso sobre el techo de quien le compra; la
    captura se calcula despues de la participacion del paso 7.
    """
    excedente, optimo = float(excedente), float(optimo)
    if not (np.isfinite(excedente) and np.isfinite(optimo)):
        raise ValueError("captura con valores no finitos")
    tol = 1e-9 * max(1.0, abs(optimo))
    if excedente > optimo + tol:
        raise ValueError(f"excedente {excedente} mayor que el optimo {optimo}")
    if abs(optimo) <= tol:
        if excedente < -tol:
            raise ValueError(f"captura no definida: optimo nulo y excedente "
                             f"{excedente}")
        return 1.0
    if optimo < 0.0:
        raise ValueError(f"captura no definida con optimo negativo {optimo} "
                         f"(algun vendedor con piso sobre el techo de todos)")
    if excedente < -tol:
        raise ValueError(f"captura negativa: excedente {excedente} con optimo "
                         f"{optimo} (algun despachado con el piso sobre el "
                         f"techo de quien le compra; falta la participacion)")
    return excedente / optimo
