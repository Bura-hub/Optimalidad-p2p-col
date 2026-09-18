"""
La dinamica regularizada como opcion apagada de la via acoplada (D49, D50), y
las dos palancas con que se le pregunta si llega al reposo de produccion
(D68). 2026-09-17.

QUE SE PRUEBA. `solve_coupled_for_hour` gana tres opciones, apagadas por
defecto: la exploracion entropica del replicador del vendedor
(`mu_entropia`, el termino V3a de la sonda del consenso), el arranque de los
precios en el presupuesto sigma del reposo (`nivel="sigma"`) y el arranque
desde un estado dado (`estado_inicial`). D68 anade otras dos, tambien
apagadas: el costo del vendedor que entra en la dinamica
(`costo_vendedor="alternativa"`, el piso piso_j en vez del costo nivelado b_j)
y el escalar de piso que recibe el juego (`piso_juego="marginal"`, el p* de la
caminata competitiva del nucleo en vez del menor de los pisos). El motor
(`SolverParams`, la tupla del trabajador con sus shims de 36 a 38 y de 38 a
40 campos) y la linea de ordenes (`--mu-entropia`, `--nivel-acoplado`,
`--costo-vendedor`, `--piso-juego`, las lineas [D49] y [D68]) las llevan hasta
la via acoplada.

  - con los defectos, IDENTICO AL BIT a la version de antes: el estado inicial
    que recibe el integrador, el lado derecho en tres estados y una
    trayectoria corta, contra huellas SHA-256 calculadas con el codigo de
    antes del cambio;
  - con mu > 0 el lado derecho cambia solo en el bloque de P, y en
    exactamente el termino de `scratchpad/consenso/arnes.py`;
  - con `nivel="sigma"` la suma de los precios reales iniciales es el
    presupuesto del nucleo, y el virtual arranca en su techo;
  - `estado_inicial` se respeta, y desde el reposo el reparto arranca quieto
    solo en las horas no rigidas de la compuerta (max |dP/dt|);
  - con `costo_vendedor="alternativa"` el lado derecho cambia SOLO en los tres
    bloques indexados por el vendedor (gamma, su filtro y P) y cambia
    exactamente en la diferencia entre b_j y piso_j, y sin `piso_j` se
    rechaza;
  - con `piso_juego="marginal"` el escalar del juego es el MISMO NUMERO que da
    `despacho_competitivo` del nucleo para esa hora;
  - los valores invalidos se rechazan en `solve_coupled_for_hour` (tambien
    `nivel="sigma"` con el peso de precio), en `SolverParams`, en la tupla y
    en la linea de ordenes, que ademas avisa [D49] o [D68] si se piden sin la
    via acoplada;
  - el shim y los tres sitios que arman la tupla;
  - la compuerta `tests/gate_reposo_cero_dinamica.py` ejecutada directa:
    corre las dos horas rapidas y sale con 0, con un fallo forzado sale
    distinto de 0, y con `HORIZONTE_COMPUERTA` no vacia se niega y sale con 2;
    por pytest, un horizonte parcial nunca aprueba, y el horizonte tiene que
    estar en (0, 5] y ser multiplo de 0,1.

LAS HUELLAS DE ANTES. Se calcularon el 2026-09-17, ANTES de tocar
`core/coupled_ode_convergence.py` (identico entonces al del commit a392cbd),
corriendo este mismo fichero como guion (`python tests/
test_dinamica_regularizada.py`, que imprime la tabla con `_genera`), en
Windows con Python 3.13.7, numpy 2.4.4 y scipy 1.17.1; y se volvieron a
calcular despues del cambio, con el mismo resultado. Las del estado inicial y
del lado derecho son aritmetica de numpy y corren siempre; las de la
trayectoria integran con LSODA, cuyo resultado al bit depende de la
plataforma y de numpy y scipy (H-84), y solo corren en el entorno de
`requirements-lock.txt` en Windows, como `tests/test_reposo_motor.py`.

SIN DATOS REALES. Dos casos: uno sintetico de techo escalar (1 250 y 114
(COP/kWh), donde el arranque de C-136 no dispara su interruptor) y la hora
874 de E0 con los literales y la huella de `tests/test_reposo_mercado.py`
(techos por comprador, donde si lo dispara). Las horas del motor salen del
caso sintetico de C-165 (`_hora` de `tests/test_criterio_reparto.py`).
"""
from __future__ import annotations

import contextlib
import hashlib
import os
import platform
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import scipy

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import core.coupled_ode_convergence as ccc  # noqa: E402
import core.ems_p2p as motor  # noqa: E402
from core.coupled_ode_convergence import solve_coupled_for_hour  # noqa: E402
from core.ems_p2p import (  # noqa: E402
    TOL_REPARTO, AgentParams, EMSP2P, GridParams, SolverParams,
    _run_hour_worker)
from core.replicator_buyers import VEL_GPC  # noqa: E402
from core.replicator_sellers import VEL_RD  # noqa: E402
from core.reposo_mercado import (  # noqa: E402
    despacho_competitivo, presupuesto_precios, resuelve_reposo)
from test_criterio_reparto import _hora  # noqa: E402
from test_reposo_mercado import _entradas  # noqa: E402


# ─── piezas ────────────────────────────────────────────────────────────────


class _Alto(Exception):
    """Detiene `solve_coupled_for_hour` justo al llamar al integrador."""


@contextlib.contextmanager
def _integrador(falso):
    """Sustituye el integrador del modulo mientras dura el bloque. No usa
    `monkeypatch` para que `_genera` corra tambien fuera de pytest."""
    original = ccc.solve_ivp
    ccc.solve_ivp = falso
    try:
        yield
    finally:
        ccc.solve_ivp = original


def _caso(nombre):
    if nombre == "escalar":
        return dict(G=np.array([5.0, 3.0]), D=np.array([1.0, 2.0, 0.5]),
                    b=np.full(2, 225.0), techo=1250.0, piso=114.0,
                    # D68: dos pisos distintos, el menor igual al escalar, para
                    # que el caso sirva a las dos palancas.
                    piso_j=np.array([114.0, 180.0]))
    s, d, b, techo, piso_j = _entradas(874)
    return dict(G=s, D=d, b=b, techo=techo, piso=float(piso_j[0]),
                piso_j=np.asarray(piso_j, dtype=float))


# D68: la hora del «cruce de cotas» de la especificacion (prueba 5 del apartado
# 7 de `fable-retiro-report.md`), donde el piso del vendedor MARGINAL (700) no
# es el menor de los pisos (300): el segundo comprador, con techo 650, no
# alcanza a pagarlo y sale del juego. Es el unico caso de este fichero en que
# las dos opciones de `piso_juego` dan numeros distintos.
CASO_CRUCE = dict(G=np.array([1.0, 1.0]), D=np.array([1.5, 1.0]),
                  b=np.array([225.0, 240.0]),
                  techo=np.array([800.0, 650.0]), piso=300.0,
                  piso_j=np.array([300.0, 700.0]))
# El mismo cruce con los dos techos por encima del piso marginal, de modo que
# el arranque sigma queda definido y el escalar del juego se puede LEER del
# estado inicial, no solo comparar.
CASO_CRUCE_ALTO = dict(CASO_CRUCE, techo=np.array([800.0, 750.0]))
PISO_MARGINAL_CRUCE = 700.0


def _kw(c, **extra):
    """Los parametros de produccion del acoplado; rtol = atol = 1e-6 (H-51)."""
    J, I = len(c["G"]), len(c["D"])
    kw = dict(G_net_j=c["G"], D_net_i=c["D"], a_j=np.zeros(J), b_j=c["b"],
              lam_j=np.full(J, 100.0), theta_j=np.full(J, 0.5),
              G_klim_i=np.zeros(I), lam_i=np.full(I, 100.0),
              theta_i=np.full(I, 0.5), etha_i=np.full(I, 0.1),
              pi_gs=c["techo"], pi_gb=c["piso"], tau_sellers=0.001,
              tau_buyers=0.01, rtol=1e-6, atol=1e-6)
    kw.update(extra)
    return kw


def _captura(c, **extra):
    """(X0, fun): el estado inicial y el lado derecho que recibe el
    integrador, sin integrar nada."""
    vistos = []

    def falso(fun, t_span, y0, **kw):
        vistos.append((np.array(y0, dtype=float, copy=True), fun))
        raise _Alto()

    with _integrador(falso):
        try:
            solve_coupled_for_hour(**_kw(c, t_span=(0.0, 0.01), **extra))
        except _Alto:
            pass
    assert len(vistos) == 1
    return vistos[0]


def _estados(X0):
    """Tres estados deterministas donde evaluar el lado derecho: el inicial y
    dos perturbados (multiplicativa y aditiva, para mover tambien los ceros)."""
    n = np.arange(X0.size, dtype=float)
    return [X0,
            X0 * (1.0 + 0.05 * np.sin(n + 1.0)) + 0.1 * np.cos(n + 2.0),
            X0 * (1.0 + 0.05 * np.sin(n + 3.0)) + 0.1 * np.cos(n + 4.0)]


def _huella(*arrays):
    m = hashlib.sha256()
    for a in arrays:
        m.update(np.ascontiguousarray(a, dtype=np.float64).tobytes())
    return m.hexdigest()[:16]


def _bloques(c):
    """Los indices del estado: precios (I+1) y P (J*I)."""
    J, I = len(c["G"]), len(c["D"])
    i0 = I + 1 + 2 * J
    return I, J, slice(0, I + 1), slice(i0, i0 + J * I)


FORMAS = (("barrera", "aggregate"), ("precio", "matrix"))
T_CORTO = 0.002
# D68 anade `costo_vendedor`, `piso_j` y `piso_juego`: escritas con su valor
# por defecto tampoco pueden cambiar nada.
DEFECTOS = dict(mu_entropia=0.0, nivel="c136", estado_inicial=None,
                costo_vendedor="lcoe", piso_j=None, piso_juego="minimo",
                despacho_vendedores="piso")


def _trayectoria(c, arranque, **extra):
    return solve_coupled_for_hour(**_kw(c, t_span=(0.0, T_CORTO), n_points=5,
                                        arranque=arranque, **extra))


def _genera():
    """Imprime la tabla de huellas. Corrido con el codigo de antes del cambio
    dio `HUELLAS_DE_ANTES`."""
    for nombre in ("escalar", "h874"):
        c = _caso(nombre)
        for arranque in ("iguales", "factible"):
            X0, _ = _captura(c, arranque=arranque)
            print(f'("{nombre}", "{arranque}", "X0"): "{_huella(X0)}",')
            for peso, comp in FORMAS:
                X0, fun = _captura(c, arranque=arranque, peso_virtual=peso,
                                   buyer_competition=comp)
                h = _huella(*[fun(0.0, X) for X in _estados(X0)])
                print(f'("{nombre}", "{arranque}", "rhs {peso} {comp}"): '
                      f'"{h}",')
            tr = _trayectoria(c, arranque)
            print(f'("{nombre}", "{arranque}", "trayectoria"): '
                  f'"{_huella(tr.t, tr.pi_t, tr.P_t, tr.W_t)}",  '
                  f'# exito {tr.success}, nfev {tr.nfev}, njev {tr.njev}')


HUELLAS_DE_ANTES = {
    ("escalar", "iguales", "X0"): "f48ef8fa6c88dbee",
    ("escalar", "iguales", "rhs barrera aggregate"): "d40544a84773d350",
    ("escalar", "iguales", "rhs precio matrix"): "ea9115bc8b6ee553",
    ("escalar", "iguales", "trayectoria"): "2a05661d4acdeeb3",
    ("escalar", "factible", "X0"): "5843255413f7c4e3",
    ("escalar", "factible", "rhs barrera aggregate"): "362570dcbbdeb3d9",
    ("escalar", "factible", "rhs precio matrix"): "6313157184818d40",
    ("escalar", "factible", "trayectoria"): "2c4610e391631d94",
    ("h874", "iguales", "X0"): "1695a494fc2f1413",
    ("h874", "iguales", "rhs barrera aggregate"): "7901fd7620a7d6e9",
    ("h874", "iguales", "rhs precio matrix"): "6fb6d8e9035232c0",
    ("h874", "iguales", "trayectoria"): "a7f53b11ccacca18",
    ("h874", "factible", "X0"): "6923e8433c34cf84",
    ("h874", "factible", "rhs barrera aggregate"): "04e57823f0a235ec",
    ("h874", "factible", "rhs precio matrix"): "dae7a34d8b063cc4",
    ("h874", "factible", "trayectoria"): "ed8b64799dc5274f",
}
# (nfev, njev) de las trayectorias de antes.
EVALUACIONES_DE_ANTES = {
    ("escalar", "iguales"): (4990, 122), ("escalar", "factible"): (7312, 212),
    ("h874", "iguales"): (30928, 912), ("h874", "factible"): (1364, 34),
}


def _versiones_del_lock() -> dict:
    versiones = {}
    for linea in (RAIZ / "requirements-lock.txt").read_text(
            encoding="utf-8").splitlines():
        nombre, _, version = linea.strip().partition("==")
        if nombre.strip().lower() in ("numpy", "scipy"):
            versiones[nombre.strip().lower()] = version.strip()
    return {"numpy": versiones["numpy"], "scipy": versiones["scipy"]}


LOCK = _versiones_del_lock()
EN_EL_ENTORNO_DEL_LOCK = (platform.system() == "Windows"
                          and np.__version__ == LOCK["numpy"]
                          and scipy.__version__ == LOCK["scipy"])
CASOS = [(n, a) for n in ("escalar", "h874") for a in ("iguales", "factible")]


# ─── con los defectos, identico al bit ─────────────────────────────────────


@pytest.mark.skipif(
    not EN_EL_ENTORNO_DEL_LOCK,
    reason=f"las huellas se calcularon en Windows con numpy {LOCK['numpy']} y "
           f"scipy {LOCK['scipy']} (requirements-lock.txt); ni el estado "
           f"inicial ni el lado derecho son identicos al bit entre "
           f"plataformas, porque las reducciones de numpy suman en otro orden "
           f"(H-84). Para este entorno, regenerarlas con `_genera()`")
@pytest.mark.parametrize("nombre, arranque", CASOS)
@pytest.mark.parametrize("explicitos", [False, True],
                         ids=["omitidos", "explicitos"])
def test_con_los_defectos_el_estado_inicial_y_el_lado_derecho_son_los_de_antes(
        nombre, arranque, explicitos):
    c = _caso(nombre)
    extra = dict(DEFECTOS) if explicitos else {}
    X0, _ = _captura(c, arranque=arranque, **extra)
    assert _huella(X0) == HUELLAS_DE_ANTES[(nombre, arranque, "X0")]
    for peso, comp in FORMAS:
        X0, fun = _captura(c, arranque=arranque, peso_virtual=peso,
                           buyer_competition=comp, **extra)
        h = _huella(*[fun(0.0, X) for X in _estados(X0)])
        assert h == HUELLAS_DE_ANTES[(nombre, arranque, f"rhs {peso} {comp}")]


@pytest.mark.skipif(
    not EN_EL_ENTORNO_DEL_LOCK,
    reason=f"las huellas de la trayectoria valen en Windows con numpy "
           f"{LOCK['numpy']} y scipy {LOCK['scipy']} (requirements-lock.txt); "
           f"LSODA no es identico al bit entre plataformas (H-84)")
@pytest.mark.parametrize("nombre, arranque", CASOS)
def test_con_los_defectos_la_trayectoria_corta_es_la_de_antes(nombre,
                                                              arranque):
    c = _caso(nombre)
    for extra in ({}, dict(DEFECTOS)):
        tr = _trayectoria(c, arranque, **extra)
        assert tr.success, tr.message
        assert (_huella(tr.t, tr.pi_t, tr.P_t, tr.W_t)
                == HUELLAS_DE_ANTES[(nombre, arranque, "trayectoria")])
        assert (tr.nfev, tr.njev) == EVALUACIONES_DE_ANTES[(nombre, arranque)]


# ─── la exploracion entropica ──────────────────────────────────────────────


@pytest.mark.parametrize("nombre", ["escalar", "h874"])
@pytest.mark.parametrize("mu", [1.0, 1, 0.3])
def test_con_mu_el_lado_derecho_cambia_solo_en_P_con_el_termino_del_arnes(
        nombre, mu):
    c = _caso(nombre)
    I, J, _, bloque_P = _bloques(c)
    X0, fun0 = _captura(c, arranque="factible")
    X0_mu, fun_mu = _captura(c, arranque="factible", mu_entropia=mu)
    # El termino no toca el arranque.
    assert np.array_equal(X0, X0_mu)
    fuera = np.r_[0:bloque_P.start, bloque_P.stop:X0.size]
    for X in _estados(X0):
        r0, r_mu = fun0(0.0, X), fun_mu(0.0, X)
        # Fuera del bloque de P, identico al bit.
        assert np.array_equal(r0[fuera], r_mu[fuera])
        # En el bloque de P, exactamente el termino V3a de
        # `scratchpad/consenso/arnes.py` (lineas 251 a 255), restado despues
        # del factor 10 y sobre la P leida con el piso de 1e-10.
        P = np.maximum(X[bloque_P].reshape(J, I), 1e-10)
        lnP = np.log(P)
        m = float(np.sum(P * lnP)) / float(np.sum(P))
        termino = (P * (lnP - m)).ravel()
        assert np.array_equal(r_mu[bloque_P], r0[bloque_P] - mu * termino)
        assert not np.array_equal(r_mu[bloque_P], r0[bloque_P])
        # Conserva la suma de P.
        assert abs(termino.sum()) <= 1e-12 * np.abs(termino).sum()


# ─── el arranque sigma ─────────────────────────────────────────────────────


CASOS_SIGMA = {
    "escalar": _caso("escalar"),
    "h874": _caso("h874"),
    "techos_distintos": dict(G=np.array([4.0]), D=np.array([1.0, 2.0, 3.0]),
                             b=np.full(1, 225.0),
                             techo=np.array([700.0, 760.0, 810.0]),
                             piso=650.0),
    "un_comprador": dict(G=np.array([4.0, 1.0]), D=np.array([2.0]),
                         b=np.full(2, 225.0), techo=np.array([731.0]),
                         piso=690.0),
}


@pytest.mark.parametrize("nombre", list(CASOS_SIGMA))
def test_con_sigma_los_precios_reales_suman_el_presupuesto_del_nucleo(nombre):
    c = CASOS_SIGMA[nombre]
    I, J, bloque_pi, _ = _bloques(c)
    techo = np.broadcast_to(np.asarray(c["techo"], dtype=float), (I,))
    X0_c136, _ = _captura(c, arranque="factible")
    X0, _ = _captura(c, arranque="factible", nivel="sigma")
    S = presupuesto_precios(techo, c["piso"], modo="sigma")
    reales = X0[:I]
    # La suma es el presupuesto del nucleo, al bit.
    assert float(np.sum(reales)) == S
    sigma = (I - 1) / I
    np.testing.assert_allclose(reales, c["piso"] + sigma * (techo - c["piso"]),
                               rtol=0, atol=1e-9)
    # El virtual, en su techo, donde la barrera lo congela.
    assert X0[I] == float(np.max(techo))
    # El resto del estado inicial no cambia.
    assert np.array_equal(X0[I + 1:], X0_c136[I + 1:])


def test_con_sigma_un_techo_bajo_el_piso_se_rechaza():
    c = dict(CASOS_SIGMA["techos_distintos"], techo=np.array([600.0, 760.0,
                                                              810.0]))
    with pytest.raises(ValueError, match="techo bajo el piso"):
        _captura(c, nivel="sigma")
    # Con el arranque de siempre, el interruptor de C-136 lo absorbe.
    _captura(c)


def test_sigma_con_el_peso_de_precio_se_rechaza_aun_sin_mercado():
    # Menor 4 de la revision: sin la barrera el virtual no se congela y la
    # suma de precios no se conserva (H-46, H-90).
    c = _caso("h874")
    with pytest.raises(ValueError, match=r"H-46.*H-90"):
        _captura(c, nivel="sigma", peso_virtual="precio")
    with pytest.raises(ValueError, match=r"H-46.*H-90"):
        solve_coupled_for_hour(**_kw(dict(c, G=np.zeros(1)), nivel="sigma",
                                     peso_virtual="precio"))
    # Cada opcion por separado sigue valiendo.
    _captura(c, nivel="sigma", peso_virtual="barrera")
    _captura(c, nivel="c136", peso_virtual="precio")


# ─── el estado inicial ─────────────────────────────────────────────────────


def _reposo_874():
    s, d, b, techo, piso_j = _entradas(874)
    return resuelve_reposo(s, d, b, techo, piso_j)


@pytest.mark.parametrize("nivel", ["c136", "sigma"])
def test_el_estado_inicial_se_respeta(nivel):
    c = _caso("h874")
    I, J, _, bloque_P = _bloques(c)
    rep = _reposo_874()
    # Un P con un cero, para ver que no se recorta a 1e-10.
    P = rep.P.copy()
    P[0, 0] = 0.0
    X0_nivel, _ = _captura(c, nivel=nivel)
    X0, _ = _captura(c, nivel=nivel,
                     estado_inicial=dict(P=P, pi=rep.pi_reposo))
    assert np.array_equal(X0[:I], rep.pi_reposo)
    assert np.array_equal(X0[bloque_P], P.ravel()) and X0[bloque_P][0] == 0.0
    # El virtual, segun `nivel`; los multiplicadores y filtros, como siempre.
    assert X0[I] == X0_nivel[I]
    resto = np.r_[I + 1:bloque_P.start, bloque_P.stop:X0.size]
    assert np.array_equal(X0[resto], X0_nivel[resto])


@pytest.mark.parametrize("k, esperado, rigida", [
    (853, 0.0, False), (2120, 3.0e-4, False), (874, 86.3, True),
    (4766, 32.7, True)])
def test_desde_el_reposo_el_reparto_arranca_quieto_solo_en_las_no_rigidas(
        k, esperado, rigida):
    """Menor 1 de la revision: max |dP/dt| en el arranque de la compuerta,
    con los multiplicadores de siempre (kWh por unidad de tiempo). Solo evalua
    el lado derecho una vez: no integra."""
    import gate_reposo_cero_dinamica as compuerta
    _, kw = compuerta._llamada(k)
    vistos = []

    def falso(fun, t_span, y0, **kw_ivp):
        vistos.append((np.array(y0, dtype=float, copy=True), fun))
        raise _Alto()

    with _integrador(falso):
        with pytest.raises(_Alto):
            solve_coupled_for_hour(**kw)
    X0, fun = vistos[0]
    J, I = len(kw["G_net_j"]), len(kw["D_net_i"])
    i0 = I + 1 + 2 * J
    dPdt = float(np.max(np.abs(fun(0.0, X0)[i0:i0 + J * I])))
    print(f"    hora {k}: max |dP/dt| = {dPdt:.4g} (kWh por unidad de tiempo)")
    if rigida:
        assert dPdt == pytest.approx(esperado, rel=5e-3)
    else:
        assert dPdt <= 1e-3 and dPdt == pytest.approx(esperado, abs=5e-5)


def test_el_estado_inicial_no_se_combina_con_el_arranque_factible():
    rep = _reposo_874()
    with pytest.raises(ValueError, match="factible"):
        _captura(_caso("h874"), arranque="factible",
                 estado_inicial=dict(P=rep.P, pi=rep.pi_reposo))


# ─── D68: el costo del vendedor ────────────────────────────────────────────


CASOS_D68 = {"escalar": _caso("escalar"), "h874": _caso("h874"),
             "cruce": CASO_CRUCE}


def _sin_polvo(x):
    """La misma limpieza que la del modulo, para comprobar contra ella."""
    x = np.array(x, dtype=float, copy=True)
    x[(x < 0.0) & (x >= -ccc.TOL_NETO_CAMINATA)] = 0.0
    return x


def _cerca_con_escala(medido, esperado, escala=None):
    """Compara una DIFERENCIA de dos lados derechos con su forma analitica. La
    diferencia se calcula restando dos numeros del tamano de `escala`, de modo
    que arrastra el redondeo de esa resta y puede valer cero por cancelacion
    exacta: la tolerancia absoluta va atada a ese tamano, no a cero. Sin
    `escala`, el mayor de los dos lados."""
    medido = np.atleast_1d(np.asarray(medido, dtype=float))
    esperado = np.atleast_1d(np.asarray(esperado, dtype=float))
    if escala is None:
        escala = max(float(np.max(np.abs(medido))),
                     float(np.max(np.abs(esperado))))
    np.testing.assert_allclose(medido, esperado, rtol=1e-9,
                               atol=1e-9 * max(float(escala), 1.0))


def _bloques_del_vendedor(c):
    """Los tres bloques del estado indexados por el VENDEDOR: gamma (J), su
    filtro y_filt (J) y la oferta P (J*I). Son los unicos donde el costo del
    vendedor entra en el lado derecho."""
    J, I = len(c["G"]), len(c["D"])
    g0 = I + 1
    return slice(g0, g0 + J), slice(g0 + J, g0 + 2 * J), \
        slice(g0 + 2 * J, g0 + 2 * J + J * I)


@pytest.mark.parametrize("nombre", list(CASOS_D68))
def test_con_la_alternativa_es_lo_mismo_que_llamar_con_b_igual_al_piso(nombre):
    """El costo del vendedor entra en DOS sitios del lado derecho y en ningun
    otro: la aptitud del replicador y el termino de la ecuacion 16. Si eso es
    cierto, pedir `costo_vendedor="alternativa"` con piso_j tiene que dar
    exactamente lo mismo que llamar con `b_j = piso_j` y el costo de siempre.
    Identidad al bit, sin tolerancia."""
    c = CASOS_D68[nombre]
    pisos = c["piso_j"]
    X0_alt, fun_alt = _captura(c, costo_vendedor="alternativa", piso_j=pisos)
    X0_sus, fun_sus = _captura(dict(c, b=pisos))
    # El costo no toca el arranque.
    assert np.array_equal(X0_alt, X0_sus)
    assert np.array_equal(X0_alt, _captura(c)[0])
    for X in _estados(X0_alt):
        assert np.array_equal(fun_alt(0.0, X), fun_sus(0.0, X))


@pytest.mark.parametrize("nombre", list(CASOS_D68))
def test_con_la_alternativa_el_lado_derecho_cambia_solo_en_el_vendedor(nombre):
    """Y cambia exactamente en la diferencia entre b_j y piso_j: el termino de
    la ecuacion 16 mueve gamma y su filtro, y la aptitud mueve P."""
    c = CASOS_D68[nombre]
    J, I = len(c["G"]), len(c["D"])
    pisos = c["piso_j"]
    dc = pisos - np.asarray(c["b"], dtype=float)
    assert np.any(dc != 0.0), "el caso no distingue las dos opciones"
    b_gamma, b_yfilt, b_P = _bloques_del_vendedor(c)
    simplex = min(float(np.sum(c["G"])), float(np.sum(c["D"])))
    X0, fun0 = _captura(c)
    _, fun_alt = _captura(c, costo_vendedor="alternativa", piso_j=pisos)
    fuera = np.r_[0:b_gamma.start, b_P.stop:X0.size]
    movio_P = False
    for X in _estados(X0):
        r0, r_alt = fun0(0.0, X), fun_alt(0.0, X)
        # Fuera de los tres bloques del vendedor, identico al bit: el precio,
        # los multiplicadores y el filtro del multiplicador no ven el costo.
        assert np.array_equal(r0[fuera], r_alt[fuera])
        for bloque in (b_gamma, b_yfilt):
            assert not np.array_equal(r0[bloque], r_alt[bloque])
        movio_P = movio_P or not np.array_equal(r0[b_P], r_alt[b_P])
        # El termino de la ecuacion 16: Delta H_j = (piso_j - b_j)·sum_i P_ji,
        # que entra en gamma y, dividido por tau, en su filtro.
        P = np.maximum(X[b_P].reshape(J, I), 1e-10)
        gamma = X[b_gamma]
        d_raw = VEL_GPC * gamma * (dc * P.sum(axis=1))
        _cerca_con_escala(r_alt[b_gamma] - r0[b_gamma], 0.08 * d_raw)
        _cerca_con_escala(r_alt[b_yfilt] - r0[b_yfilt], 0.08 * d_raw / 0.01)
        # La aptitud del replicador: Delta F_ji = -(piso_j - b_j), y la media
        # ponderada se mueve con ella. Con un solo vendedor y la oferta del
        # arranque la media absorbe el cambio entero y la diferencia es cero:
        # por eso el bloque de P se exige distinto en ALGUNO de los estados, no
        # en todos.
        dF = -np.repeat(dc[:, None], I, axis=1)
        dbar = float(np.sum(P * dF)) / simplex
        _cerca_con_escala(r_alt[b_P] - r0[b_P],
                          10.0 * (P * VEL_RD * (dF - dbar)).ravel(),
                          10.0 * VEL_RD * float(np.max(P * np.abs(dF))))
    assert movio_P


def test_la_alternativa_sin_el_piso_por_vendedor_se_rechaza_aun_sin_mercado():
    c = _caso("escalar")
    with pytest.raises(ValueError, match="piso_j"):
        _captura(c, costo_vendedor="alternativa")
    with pytest.raises(ValueError, match="piso_j"):
        solve_coupled_for_hour(**_kw(dict(c, G=np.zeros(2)),
                                     costo_vendedor="alternativa"))


@pytest.mark.parametrize("piso_j", [
    [114.0], [[114.0, 180.0]], np.zeros((2, 1)), [114.0, np.nan],
    [114.0, np.inf], ["a", "b"]], ids=repr)
def test_un_piso_por_vendedor_mal_formado_se_rechaza(piso_j):
    with pytest.raises(ValueError, match="piso_j"):
        _captura(_caso("escalar"), costo_vendedor="alternativa",
                 piso_j=piso_j)


@pytest.mark.parametrize("nombre", list(CASOS_D68))
def test_el_piso_por_vendedor_solo_no_cambia_nada(nombre):
    """Pasar `piso_j` sin pedir ninguna de las dos palancas no puede mover
    nada: es un dato que la via no usa."""
    c = CASOS_D68[nombre]
    X0, fun0 = _captura(c)
    X0_p, fun_p = _captura(c, piso_j=c["piso_j"])
    assert np.array_equal(X0, X0_p)
    for X in _estados(X0):
        assert np.array_equal(fun0(0.0, X), fun_p(0.0, X))


# ─── D68: el piso del vendedor marginal ────────────────────────────────────


def test_el_nucleo_da_el_piso_marginal_del_cruce_de_cotas():
    # El caso de la especificacion: p* = 700, el piso del segundo vendedor, y
    # el comprador de techo 650 queda fuera.
    d = despacho_competitivo(CASO_CRUCE["G"], CASO_CRUCE["D"],
                             CASO_CRUCE["techo"], CASO_CRUCE["piso_j"])
    assert d.piso == PISO_MARGINAL_CRUCE and d.causa == ""
    assert d.E == 1.5 and d.dentro == (0,)
    # Y no es el menor de los pisos, que es el que recibe la via de siempre.
    assert CASO_CRUCE["piso"] == float(np.min(CASO_CRUCE["piso_j"]))


def test_con_marginal_el_escalar_del_juego_es_el_p_del_nucleo():
    """El escalar que recibe la barrera con `piso_juego="marginal"` es el mismo
    numero que da `despacho_competitivo`. Se comprueba sin leerlo por dentro:
    la hora con la palanca tiene que dar, al bit, lo mismo que la misma hora
    llamada con ese numero como piso y la opcion de siempre."""
    c = CASO_CRUCE
    p_estrella = float(despacho_competitivo(c["G"], c["D"], c["techo"],
                                            c["piso_j"]).piso)
    assert p_estrella == PISO_MARGINAL_CRUCE
    X0_m, fun_m = _captura(c, piso_juego="marginal", piso_j=c["piso_j"])
    X0_p, fun_p = _captura(dict(c, piso=p_estrella))
    assert np.array_equal(X0_m, X0_p)
    for X in _estados(X0_m):
        assert np.array_equal(fun_m(0.0, X), fun_p(0.0, X))
    # Y NO es lo que da el menor de los pisos, que es la via de siempre.
    assert not np.array_equal(X0_m, _captura(c)[0])


def test_con_marginal_el_arranque_sigma_se_levanta_hasta_el_p_del_nucleo():
    """El escalar del juego leido del estado inicial: con `nivel="sigma"` la
    suma de los precios reales es el presupuesto del nucleo calculado CON EL
    PISO MARGINAL, y cada precio abre en p* + (I-1)/I·(techo_i - p*)."""
    c = CASO_CRUCE_ALTO
    I = len(c["D"])
    p_estrella = float(despacho_competitivo(c["G"], c["D"], c["techo"],
                                            c["piso_j"]).piso)
    assert p_estrella == PISO_MARGINAL_CRUCE
    X0, _ = _captura(c, nivel="sigma", piso_juego="marginal",
                     piso_j=c["piso_j"])
    assert float(np.sum(X0[:I])) == presupuesto_precios(
        c["techo"], p_estrella, modo="sigma")
    sigma = (I - 1) / I
    np.testing.assert_allclose(
        X0[:I], p_estrella + sigma * (c["techo"] - p_estrella),
        rtol=0, atol=1e-9)
    # Y con el menor de los pisos abre mucho mas abajo: es otro presupuesto.
    X0_min, _ = _captura(c, nivel="sigma")
    assert float(np.sum(X0_min[:I])) == presupuesto_precios(
        c["techo"], c["piso"], modo="sigma")
    assert float(np.sum(X0_min[:I])) < float(np.sum(X0[:I]))


@pytest.mark.parametrize("nombre", ["escalar", "h874"])
def test_con_un_solo_nivel_de_piso_marginal_y_minimo_coinciden(nombre):
    """Con todos los vendedores en el mismo piso, el marginal ES el minimo: la
    palanca da la misma hora, al bit. En 'escalar' hay dos pisos distintos pero
    la demanda cabe entera en el vendedor barato, de modo que p* vuelve a ser
    el menor."""
    c = CASOS_D68[nombre]
    X0, fun0 = _captura(c)
    X0_m, fun_m = _captura(c, piso_juego="marginal", piso_j=c["piso_j"])
    assert np.array_equal(X0, X0_m)
    for X in _estados(X0):
        assert np.array_equal(fun0(0.0, X), fun_m(0.0, X))


@pytest.mark.parametrize("nombre", list(CASOS_D68))
def test_marginal_sin_el_piso_por_vendedor_repite_el_escalar(nombre):
    """Sin `piso_j` la caminata corre con el escalar repetido: un solo nivel, y
    el marginal vuelve a ser el que llego. No se rechaza, porque es la
    respuesta correcta cuando no hay pisos distintos que declarar."""
    c = CASOS_D68[nombre]
    X0, fun0 = _captura(c)
    X0_m, fun_m = _captura(c, piso_juego="marginal")
    assert np.array_equal(X0, X0_m)
    for X in _estados(X0):
        assert np.array_equal(fun0(0.0, X), fun_m(0.0, X))


def test_la_caminata_del_acoplado_perdona_el_polvo_de_los_netos():
    """Medio 1 de la revision. Los netos de una hora real se calculan restando
    dos medidas y traen briznas negativas: un comprador con demanda cero y una
    brizna de generacion llega con deficit -5e-10. El nucleo las rechaza, de
    modo que sin limpiarlas la hora reventaria POR LA ACOPLADA mientras el
    reposo la resuelve, y la comparacion de D68 mediria la diferencia entre dos
    filtros en vez de entre dos mercados."""
    c = CASO_CRUCE
    polvo = np.r_[c["D"], -5e-10]
    sucio = dict(c, D=polvo, techo=np.r_[c["techo"], 700.0])
    # La via de produccion ya lo perdona, con la misma tolerancia.
    assert motor.TOL_NETO_REPOSO == ccc.TOL_NETO_CAMINATA
    X0, _ = _captura(sucio, piso_juego="marginal", piso_j=c["piso_j"])
    assert np.all(np.isfinite(X0))
    # Y el piso sale el mismo que sin la brizna: el polvo no mueve la caminata.
    assert despacho_competitivo(c["G"], _sin_polvo(polvo),
                                sucio["techo"], c["piso_j"]).piso == \
        PISO_MARGINAL_CRUCE
    # Lo que se limpia es SOLO lo que ve la caminata: el deficit que se integra
    # sigue siendo el que llego, con su brizna. N3 de la re-revision: se
    # compara contra la misma hora, con la brizna intacta, llamada con el piso
    # de siempre fijado en p*; por esa via no corre ninguna caminata ni se
    # limpia nada. Si la limpieza se colara al integrador, el lado derecho
    # dejaria de coincidir.
    X0_ref, fun_ref = _captura(dict(sucio, piso=PISO_MARGINAL_CRUCE))
    X0_m, fun_m = _captura(sucio, piso_juego="marginal", piso_j=c["piso_j"])
    assert np.array_equal(X0_m, X0_ref)
    for X in _estados(X0_m):
        assert np.array_equal(fun_m(0.0, X), fun_ref(0.0, X))


def test_el_polvo_grande_no_se_perdona():
    """La tolerancia perdona el polvo, no un deficit negativo de verdad."""
    c = CASO_CRUCE
    sucio = dict(c, D=np.r_[c["D"], -1e-6],
                 techo=np.r_[c["techo"], 700.0])
    with pytest.raises(ValueError, match="no negativ|negativ"):
        _captura(sucio, piso_juego="marginal", piso_j=c["piso_j"])


def test_con_marginal_un_estado_inicial_bajo_el_p_se_rechaza():
    c = CASO_CRUCE
    J, I = len(c["G"]), len(c["D"])
    P = np.full((J, I), 0.5)
    # Dentro de la banda del piso que llega (300) pero bajo el marginal (700).
    pi = np.array([500.0, 640.0])
    _captura(c, estado_inicial=dict(P=P, pi=pi))
    with pytest.raises(ValueError, match="vendedor marginal"):
        _captura(c, piso_juego="marginal", piso_j=c["piso_j"],
                 estado_inicial=dict(P=P, pi=pi))


def test_con_marginal_el_comprador_de_techo_bajo_sigue_transando_a_su_techo():
    """Medio 2 de la revision, y es la diferencia que M-A viene a medir: el
    reposo EXCLUYE al comprador cuyo techo no alcanza el piso marginal, y la
    dinamica NO lo excluye. Su banda queda invertida, el recorte lo deja en su
    techo, y desde ahi se lleva energia igual: compra por debajo del piso del
    juego. Cifras del caso del cruce al horizonte 0,05, con el arranque de la
    propia funcion."""
    c = CASO_CRUCE
    # El reposo lo deja fuera: p* = 700 y su techo es 650.
    desp = despacho_competitivo(c["G"], c["D"], c["techo"], c["piso_j"])
    assert desp.piso == PISO_MARGINAL_CRUCE and desp.dentro == (0,)
    assert desp.excluidos_bajo_piso == (1,)
    # La dinamica no. Tolerancias flojas: LSODA no es identico al bit entre
    # plataformas (H-84), pero el fenomeno y su orden de magnitud si lo son.
    tr = solve_coupled_for_hour(**_kw(c, t_span=(0.0, 0.05),
                                      piso_juego="marginal",
                                      piso_j=c["piso_j"]))
    assert tr.success, tr.message
    q = tr.P_star.sum(axis=0)
    # Se queda EXACTAMENTE en su techo, que es donde lo deja el recorte, y ese
    # techo esta por debajo del piso del juego.
    assert tr.pi_star[1] == c["techo"][1] < PISO_MARGINAL_CRUCE
    # Y transa: no esta congelado ni excluido.
    assert q[1] > 0.0


@pytest.mark.skipif(
    not EN_EL_ENTORNO_DEL_LOCK,
    reason=f"las cifras del caso del cruce son de LSODA y se midieron en "
           f"Windows con numpy {LOCK['numpy']} y scipy {LOCK['scipy']} "
           f"(requirements-lock.txt); no son identicas entre plataformas "
           f"(H-84). Lo que no depende de la plataforma lo fija la prueba "
           f"anterior en cualquier maquina")
def test_con_marginal_las_cifras_del_comprador_de_techo_bajo():
    """N4 de la re-revision: las cifras del caso del cruce al horizonte 0,05,
    bajo la guarda del entorno donde se midieron."""
    c = CASO_CRUCE
    tr = solve_coupled_for_hour(**_kw(c, t_span=(0.0, 0.05),
                                      piso_juego="marginal",
                                      piso_j=c["piso_j"]))
    assert tr.success, tr.message
    q = tr.P_star.sum(axis=0)
    np.testing.assert_allclose(tr.pi_star, [738.25, 650.00], rtol=0, atol=0.5)
    np.testing.assert_allclose(q, [1.5, 0.5], rtol=0, atol=0.01)
    assert abs(float(q.sum()) - 2.0) <= 1e-6
    # La cuarta parte del volumen al horizonte 0,05; al 0,01 es el 30,7 %, de
    # modo que la fraccion depende de cuanto se integre.
    assert 0.24 <= q[1] / q.sum() <= 0.26


def test_una_hora_sin_ganancia_con_el_piso_marginal_es_una_hora_sin_mercado():
    """Menor 3 y N1 de la re-revision: si la caminata declara la hora sin
    ganancia (D61), produccion la deja sin mercado, y la dinamica hace lo
    simetrico: no integra y devuelve la trayectoria de hora sin mercado, con
    la causa en el mensaje. NO lanza: una excepcion contaria en C-190 y haria
    salir la corrida de M-A con el codigo 3 de D38 por un regimen previsto."""
    # Techos por debajo de todos los pisos: nadie puede pagar, volumen 0.
    c = dict(CASO_CRUCE, techo=np.array([250.0, 240.0]))
    assert despacho_competitivo(c["G"], c["D"], c["techo"],
                                c["piso_j"]).causa == "sin_ganancia"
    tr = solve_coupled_for_hour(**_kw(c, piso_juego="marginal",
                                      piso_j=c["piso_j"]))
    assert tr.success
    assert "sin_ganancia" in tr.message
    assert np.array_equal(tr.P_star, np.zeros_like(tr.P_star))
    assert np.all(tr.pi_star == c["piso"])
    # Es la MISMA trayectoria que el caso degenerado de siempre: el motor las
    # trata igual.
    assert np.array_equal(tr.P_t, np.zeros_like(tr.P_t))
    # Con el piso de siempre la hora se integra como siempre: la compuerta es
    # de la palanca, no del caso.
    _captura(c)


def test_el_bienestar_sigue_contando_el_costo_nivelado():
    """Menor 6: la promesa del docstring. Con `costo_vendedor="alternativa"` la
    dinamica despacha por piso_j, pero `_compute_welfare_trajectory` sigue
    contando b_j, que es la definicion publicada. Se comprueba sustituyendo el
    calculo del bienestar por un espia que anota el costo que recibe."""
    c = _caso("escalar")
    vistos = []
    original = ccc._compute_welfare_trajectory

    def espia(**kw):
        vistos.append(np.array(kw["b_j"], dtype=float, copy=True))
        return original(**kw)

    ccc._compute_welfare_trajectory = espia
    try:
        for extra in ({}, dict(costo_vendedor="alternativa",
                               piso_j=c["piso_j"])):
            solve_coupled_for_hour(**_kw(c, t_span=(0.0, T_CORTO), n_points=5,
                                         **extra))
    finally:
        ccc._compute_welfare_trajectory = original
    assert len(vistos) == 2
    for b in vistos:
        assert np.array_equal(b, np.asarray(c["b"], dtype=float))
        assert not np.array_equal(b, c["piso_j"])


def test_el_piso_marginal_sigue_la_regla_de_despacho_que_se_le_pida():
    """Menor 5: el piso del acoplado usa la MISMA regla de despacho que la
    corrida del reposo con la que se compara. En el cruce, "piso" da 700 y
    "llenado" da el maximo de los pisos de quienes despachan."""
    c = CASO_CRUCE
    pisos = {d: float(despacho_competitivo(c["G"], c["D"], c["techo"],
                                           c["piso_j"], d, b=c["b"]).piso)
             for d in ("piso", "costo", "llenado")}
    assert pisos["piso"] == PISO_MARGINAL_CRUCE
    for regla, p in pisos.items():
        X0_regla, _ = _captura(c, piso_juego="marginal", piso_j=c["piso_j"],
                               despacho_vendedores=regla)
        X0_directo, _ = _captura(dict(c, piso=p))
        assert np.array_equal(X0_regla, X0_directo), regla
    # El defecto es "piso", el de produccion (D64).
    assert np.array_equal(
        _captura(c, piso_juego="marginal", piso_j=c["piso_j"])[0],
        _captura(c, piso_juego="marginal", piso_j=c["piso_j"],
                 despacho_vendedores="piso")[0])


@pytest.mark.parametrize("regla", ["otro", "merito", "Piso", None, ""],
                         ids=repr)
def test_una_regla_de_despacho_desconocida_se_rechaza_aun_sin_mercado(regla):
    c = _caso("escalar")
    with pytest.raises(ValueError, match="despacho_vendedores"):
        _captura(c, despacho_vendedores=regla)
    with pytest.raises(ValueError, match="despacho_vendedores"):
        solve_coupled_for_hour(**_kw(dict(c, G=np.zeros(2)),
                                     despacho_vendedores=regla))


def test_el_recorte_deja_al_comprador_de_techo_bajo_en_su_techo():
    """Menor 4: la rama explicita del recorte con la banda invertida. El
    resultado es el mismo que antes; lo que se comprueba es que ningun precio
    sale por encima de su techo ni por debajo de min(piso, techo)."""
    c = CASO_CRUCE
    tr = solve_coupled_for_hour(**_kw(c, t_span=(0.0, T_CORTO), n_points=5,
                                      piso_juego="marginal",
                                      piso_j=c["piso_j"]))
    techo = np.asarray(c["techo"], dtype=float)[:, None]
    piso_i = np.minimum(PISO_MARGINAL_CRUCE, techo)
    assert np.all(tr.pi_t <= techo + 0.0) and np.all(tr.pi_t >= piso_i - 0.0)
    # El de techo bajo, clavado en su techo en toda la trayectoria.
    assert np.all(tr.pi_t[1, :] == c["techo"][1])


# ─── D68: lo invalido se rechaza ───────────────────────────────────────────


COSTOS_INVALIDOS = ["otro", "LCOE", "b_j", None, "", 1]
PISOS_JUEGO_INVALIDOS = ["otro", "Minimo", "marginal ", None, "", 0]


@pytest.mark.parametrize("costo", COSTOS_INVALIDOS, ids=repr)
def test_solve_coupled_rechaza_un_costo_invalido_aun_sin_mercado(costo):
    c = _caso("escalar")
    with pytest.raises(ValueError, match="costo_vendedor"):
        _captura(c, costo_vendedor=costo, piso_j=c["piso_j"])
    with pytest.raises(ValueError, match="costo_vendedor"):
        solve_coupled_for_hour(**_kw(dict(c, G=np.zeros(2)),
                                     costo_vendedor=costo))


@pytest.mark.parametrize("piso", PISOS_JUEGO_INVALIDOS, ids=repr)
def test_solve_coupled_rechaza_un_piso_del_juego_invalido_aun_sin_mercado(
        piso):
    c = _caso("escalar")
    with pytest.raises(ValueError, match="piso_juego"):
        _captura(c, piso_juego=piso)
    with pytest.raises(ValueError, match="piso_juego"):
        solve_coupled_for_hour(**_kw(dict(c, G=np.zeros(2)), piso_juego=piso))


# ─── lo invalido se rechaza ────────────────────────────────────────────────


MU_INVALIDOS = [-1.0, -1e-12, float("nan"), float("inf"), True, "1", None]
NIVELES_INVALIDOS = ["otro", "C136", None, "", 1]


def _estados_invalidos():
    rep = _reposo_874()
    P, pi = rep.P, rep.pi_reposo
    techo = _entradas(874)[3]
    malo = P.copy()
    malo[0, 1] = np.nan
    negativo = P.copy()
    negativo[0, 2] = -1e-12
    return {
        "no_diccionario": [P, pi],
        "sin_pi": dict(P=P),
        "sin_P": dict(pi=pi),
        "clave_de_mas": dict(P=P, pi=pi, lam=np.ones(1)),
        "P_forma": dict(P=P.ravel(), pi=pi),
        "pi_forma": dict(P=P, pi=pi[:3]),
        "P_no_finita": dict(P=malo, pi=pi),
        "P_negativa": dict(P=negativo, pi=pi),
        "pi_bajo_el_piso": dict(P=P, pi=np.r_[692.0, pi[1:]]),
        "pi_sobre_su_techo": dict(P=P, pi=np.r_[techo[0] + 1e-9, pi[1:]]),
        "pi_no_numerico": dict(P=P, pi=["a", "b", "c", "d"]),
    }


@pytest.mark.parametrize("mu", MU_INVALIDOS, ids=repr)
def test_solve_coupled_rechaza_mu_invalido_aun_sin_mercado(mu):
    c = _caso("escalar")
    with pytest.raises(ValueError, match="mu_entropia"):
        _captura(c, mu_entropia=mu)
    with pytest.raises(ValueError, match="mu_entropia"):
        solve_coupled_for_hour(**_kw(dict(c, G=np.zeros(2)), mu_entropia=mu))


@pytest.mark.parametrize("nivel", NIVELES_INVALIDOS, ids=repr)
def test_solve_coupled_rechaza_nivel_invalido_aun_sin_mercado(nivel):
    c = _caso("escalar")
    with pytest.raises(ValueError, match="nivel"):
        _captura(c, nivel=nivel)
    with pytest.raises(ValueError, match="nivel"):
        solve_coupled_for_hour(**_kw(dict(c, G=np.zeros(2)), nivel=nivel))


@pytest.mark.parametrize("caso", list(_estados_invalidos()))
def test_solve_coupled_rechaza_un_estado_inicial_invalido(caso):
    with pytest.raises(ValueError, match="estado_inicial"):
        _captura(_caso("h874"), estado_inicial=_estados_invalidos()[caso])


@pytest.mark.parametrize("kw", [dict(mu_entropia=m) for m in MU_INVALIDOS]
                         + [dict(nivel_acoplado=n) for n in NIVELES_INVALIDOS],
                         ids=repr)
def test_solver_params_rechaza_lo_invalido(kw):
    with pytest.raises(ValueError, match="mu_entropia|nivel_acoplado"):
        SolverParams(**kw)


def test_solver_params_acepta_lo_valido_y_sus_defectos_apagan():
    sv = SolverParams()
    assert (sv.mu_entropia, sv.nivel_acoplado) == (0.0, "c136")
    for kw in (dict(mu_entropia=0), dict(mu_entropia=1.0),
               dict(mu_entropia=np.float64(2.5)), dict(nivel_acoplado="sigma"),
               dict(mu_entropia=1.0, nivel_acoplado="sigma",
                    metodo="acoplado")):
        SolverParams(**kw)


@pytest.mark.parametrize("kw", [dict(costo_vendedor=c)
                                for c in COSTOS_INVALIDOS]
                         + [dict(piso_juego=p)
                            for p in PISOS_JUEGO_INVALIDOS], ids=repr)
def test_solver_params_rechaza_lo_invalido_de_d68(kw):
    with pytest.raises(ValueError, match="costo_vendedor|piso_juego"):
        SolverParams(**kw)


def test_solver_params_acepta_lo_valido_de_d68_y_sus_defectos_apagan():
    sv = SolverParams()
    assert (sv.costo_vendedor, sv.piso_juego) == ("lcoe", "minimo")
    for kw in (dict(costo_vendedor="alternativa"), dict(piso_juego="marginal"),
               dict(costo_vendedor="alternativa", piso_juego="marginal",
                    metodo="acoplado")):
        SolverParams(**kw)


# ─── el motor: la tupla, su shim y los tres sitios ─────────────────────────

PGS, PGB = 1250.0, 114.0
T_ACO = 0.002
PISO_H43 = np.array([600.0, 300.0])
DEFECTOS_REPOSO = ("sigma", None, "uniforme", "merito")
CAMPOS_DE_SIEMPRE = ("P_star", "pi_star", "P_int", "P_ext", "SC", "SS", "IE",
                     "PS", "PSR", "Wj_total", "Wi_total", "iters_used",
                     "norm_rel_final", "seller_ids", "buyer_ids", "retirados",
                     "motivo", "horizonte_usado", "parada_acoplado",
                     "residuo_reparto", "evaluaciones")


def _args36(h, metodo="acoplado", pi_gb_j=None):
    """La tupla de 36 campos de `_run_hour_worker`, la de antes de D49."""
    sv = SolverParams()
    return (h["k"], h["g_klim"], h["d_k"], h["g_k"], h["sids"], h["bids"],
            h["a"], h["b"], h["lam"], h["theta"], h["etha"],
            PGS, PGB, sv.tau, sv.tau_buyers, sv.t_span, sv.n_points,
            sv.stackelberg_iters, sv.stackelberg_tol, sv.stackelberg_max,
            sv.ode_method, sv.buyer_competition,
            metodo, T_ACO, pi_gb_j, False,
            1e-6, None, None, "factible", "precio", TOL_REPARTO,
            *DEFECTOS_REPOSO)


def _igual_al_bit(a, b, campos):
    for campo in campos:
        x, y = getattr(a, campo), getattr(b, campo)
        if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
            assert x is not None and y is not None, campo
            assert np.array_equal(x, y), campo
        else:
            assert x == y, campo


@pytest.mark.parametrize("metodo", ["acoplado", "alternado", "reposo"])
def test_la_tupla_de_36_y_la_de_38_con_los_defectos_dan_lo_mismo(metodo):
    h = _hora()
    if metodo == "reposo":
        # La via por reposo no admite costo cuadratico (CAL-32).
        h = dict(h, a=np.zeros_like(h["a"]))
    viejo = _run_hour_worker(_args36(h, metodo))
    assert len(_args36(h, metodo)) == 36
    for cola in ((0.0, "c136"), (0, "c136")):
        nuevo = _run_hour_worker(_args36(h, metodo) + cola)
        _igual_al_bit(viejo, nuevo, CAMPOS_DE_SIEMPRE)
    if metodo == "acoplado":
        assert viejo.P_star is not None


@pytest.mark.parametrize("metodo", ["alternado", "reposo"])
def test_fuera_del_acoplado_las_opciones_son_inertes(metodo):
    h = dict(_hora(), a=np.zeros_like(_hora()["a"]))
    viejo = _run_hour_worker(_args36(h, metodo))
    nuevo = _run_hour_worker(_args36(h, metodo) + (1.0, "sigma"))
    _igual_al_bit(viejo, nuevo, CAMPOS_DE_SIEMPRE)


@pytest.mark.parametrize("cola", [(m, "c136") for m in MU_INVALIDOS]
                         + [(0.0, n) for n in NIVELES_INVALIDOS], ids=repr)
def test_la_tupla_rechaza_lo_invalido_aun_sin_mercado(cola):
    h = _hora()
    for sids in (h["sids"], []):
        with pytest.raises(ValueError, match="mu_entropia|nivel_acoplado"):
            _run_hour_worker(_args36(dict(h, sids=sids)) + cola)


# ─── D68: la tupla de 40 campos, su shim y los tres sitios ─────────────────


def _args38(h, metodo="acoplado", pi_gb_j=None):
    """La tupla de 38 campos de `_run_hour_worker`, la de antes de D68."""
    return _args36(h, metodo, pi_gb_j) + (0.0, "c136")


@pytest.mark.parametrize("metodo", ["acoplado", "alternado", "reposo"])
def test_la_tupla_de_38_y_la_de_40_con_los_defectos_dan_lo_mismo(metodo):
    h = _hora()
    if metodo == "reposo":
        # La via por reposo no admite costo cuadratico (CAL-32).
        h = dict(h, a=np.zeros_like(h["a"]))
    assert len(_args38(h, metodo)) == 38
    viejo = _run_hour_worker(_args38(h, metodo))
    nuevo = _run_hour_worker(_args38(h, metodo) + ("lcoe", "minimo"))
    assert len(_args38(h, metodo) + ("lcoe", "minimo")) == 40
    _igual_al_bit(viejo, nuevo, CAMPOS_DE_SIEMPRE)
    # Y la de 36 sigue llegando al mismo sitio por la cadena de shims.
    _igual_al_bit(viejo, _run_hour_worker(_args36(h, metodo)),
                  CAMPOS_DE_SIEMPRE)
    if metodo == "acoplado":
        assert viejo.P_star is not None


@pytest.mark.parametrize("metodo", ["alternado", "reposo"])
def test_fuera_del_acoplado_las_palancas_del_piso_son_inertes(metodo):
    h = dict(_hora(), a=np.zeros_like(_hora()["a"]))
    viejo = _run_hour_worker(_args38(h, metodo, pi_gb_j=PISO_H43))
    nuevo = _run_hour_worker(_args38(h, metodo, pi_gb_j=PISO_H43)
                             + ("alternativa", "marginal"))
    _igual_al_bit(viejo, nuevo, CAMPOS_DE_SIEMPRE)


@pytest.mark.parametrize("cola", [(c, "minimo") for c in COSTOS_INVALIDOS]
                         + [("lcoe", p) for p in PISOS_JUEGO_INVALIDOS],
                         ids=repr)
def test_la_tupla_rechaza_lo_invalido_de_d68_aun_sin_mercado(cola):
    h = _hora()
    for sids in (h["sids"], []):
        with pytest.raises(ValueError, match="costo_vendedor|piso_juego"):
            _run_hour_worker(_args38(dict(h, sids=sids)) + cola)


def _espia(monkeypatch):
    """Sustituye el integrador del motor por uno que anota, en cada llamada,
    cuantos vendedores trae y con que opciones de la dinamica, y devuelve una
    trayectoria fabricada con precio final 500 (COP/kWh), como en
    `tests/test_arranque_acoplado.py`."""
    vistos = []

    def falso(**kw):
        J, I = len(kw["G_net_j"]), len(kw["D_net_i"])
        vistos.append((J, kw["mu_entropia"], kw["nivel"]))
        pi_t = np.tile(np.linspace(300.0, 500.0, 20), (I, 1))
        return SimpleNamespace(P_star=np.full((J, I), 0.01),
                               pi_star=pi_t[:, -1].copy(), pi_t=pi_t,
                               P_t=np.full((J, I, pi_t.shape[1]), 0.01),
                               success=True, nfev=10, njev=0,
                               message="fabricada")

    monkeypatch.setattr(motor, "solve_coupled_for_hour", falso)
    return vistos


def _agentes(h):
    N = h["a"].shape[0]
    return AgentParams(N=N, a=h["a"], b=h["b"], c=h["c"], lam=h["lam"],
                       theta=h["theta"], etha=h["etha"])


def test_las_opciones_viajan_por_los_tres_sitios_que_arman_la_tupla(
        monkeypatch):
    h = _hora()
    assert len(h["sids"]) == 2, "esta prueba necesita dos vendedores"
    vistos = _espia(monkeypatch)
    # La recursion de H-43: el piso retira a un vendedor y el conjunto
    # reducido se resuelve con las mismas opciones.
    res = _run_hour_worker(_args36(h, pi_gb_j=PISO_H43) + (0.7, "sigma"))
    assert res.retirados == [h["sids"][0]]
    assert vistos == [(2, 0.7, "sigma"), (1, 0.7, "sigma")]
    for mu, nivel in ((0.7, "sigma"), (0.0, "c136")):
        ems = EMSP2P(agents=_agentes(h), grid=GridParams(pi_gs=PGS, pi_gb=PGB),
                     solver=SolverParams(parallel=False, metodo="acoplado",
                                         t_span_acoplado=T_ACO,
                                         mu_entropia=mu, nivel_acoplado=nivel))
        vistos.clear()
        ems.run_single_hour(h["k"], h["D"], h["G"])
        assert vistos == [(2, mu, nivel)]
        vistos.clear()
        ems.run(h["D"][:, [h["k"]]], h["G"][:, [h["k"]]])
        assert vistos == [(2, mu, nivel)]


def _espia_d68(monkeypatch):
    """Como `_espia`, pero anota las palancas de D68 y el vector de pisos que
    la hora le pasa a la via acoplada."""
    vistos = []

    def falso(**kw):
        J, I = len(kw["G_net_j"]), len(kw["D_net_i"])
        piso_j = kw["piso_j"]
        vistos.append((J, kw["costo_vendedor"], kw["piso_juego"],
                       None if piso_j is None
                       else tuple(np.asarray(piso_j, dtype=float))))
        pi_t = np.tile(np.linspace(300.0, 500.0, 20), (I, 1))
        return SimpleNamespace(P_star=np.full((J, I), 0.01),
                               pi_star=pi_t[:, -1].copy(), pi_t=pi_t,
                               P_t=np.full((J, I, pi_t.shape[1]), 0.01),
                               success=True, nfev=10, njev=0,
                               message="fabricada")

    monkeypatch.setattr(motor, "solve_coupled_for_hour", falso)
    return vistos


def _pisos_por_agente(h):
    """La matriz (N, T) de pisos con `PISO_H43` en los dos vendedores de la
    hora, para que los tres sitios pasen un vector de verdad."""
    N, T = h["a"].shape[0], h["D"].shape[1]
    m = np.full((N, T), PGB)
    for u, j in enumerate(h["sids"]):
        m[j, :] = PISO_H43[u]
    return m


def test_las_palancas_del_piso_viajan_por_los_tres_sitios(monkeypatch):
    h = _hora()
    assert len(h["sids"]) == 2, "esta prueba necesita dos vendedores"
    vistos = _espia_d68(monkeypatch)
    # Sitio 1, la recursion de H-43: el piso retira a un vendedor y el conjunto
    # reducido se resuelve con las mismas palancas y con SU trozo de pisos.
    res = _run_hour_worker(_args38(h, pi_gb_j=PISO_H43)
                           + ("alternativa", "marginal"))
    assert res.retirados == [h["sids"][0]]
    assert vistos == [(2, "alternativa", "marginal", (600.0, 300.0)),
                      (1, "alternativa", "marginal", (300.0,))]
    # Sitios 2 y 3, `run_single_hour` y `run`, con el piso por agente puesto.
    # `run` recibe la hora sola, de modo que su matriz de pisos tiene una sola
    # columna.
    pisos_m = _pisos_por_agente(h)
    for costo, piso in (("alternativa", "marginal"), ("lcoe", "minimo")):
        sv = SolverParams(parallel=False, metodo="acoplado",
                          t_span_acoplado=T_ACO, costo_vendedor=costo,
                          piso_juego=piso)

        def _motor(m):
            return EMSP2P(agents=_agentes(h),
                          grid=GridParams(pi_gs=PGS, pi_gb=PGB,
                                          pi_gb_agente=m),
                          solver=sv)

        for correr in (
                lambda: _motor(pisos_m).run_single_hour(h["k"], h["D"],
                                                        h["G"]),
                lambda: _motor(pisos_m[:, [h["k"]]]).run(
                    h["D"][:, [h["k"]]], h["G"][:, [h["k"]]])):
            vistos.clear()
            correr()
            assert vistos[0] == (2, costo, piso, (600.0, 300.0)), vistos


def test_por_el_motor_las_palancas_del_piso_llegan_a_la_via_acoplada():
    """Sin espia: la hora resuelta por el motor con las dos palancas activas es
    la misma que la llamada directa con ellas, y NO la de los defectos."""
    h = _hora()
    sids, bids = h["sids"], h["bids"]
    pisos = PISO_H43.copy()
    grid = GridParams(pi_gs=PGS, pi_gb=PGB, pi_gb_agente=_pisos_por_agente(h))
    sv = SolverParams(parallel=False, metodo="acoplado", t_span_acoplado=T_ACO,
                      costo_vendedor="alternativa", piso_juego="marginal")
    comun = dict(
        G_net_j=np.array([h["g_klim"][j] - h["d_k"][j] for j in sids]),
        D_net_i=np.array([h["d_k"][i] - h["g_klim"][i] for i in bids]),
        a_j=h["a"][sids], b_j=h["b"][sids], lam_j=h["lam"][sids],
        theta_j=h["theta"][sids], G_klim_i=h["g_klim"][bids],
        lam_i=h["lam"][bids], theta_i=h["theta"][bids],
        etha_i=h["etha"][bids], pi_gs=PGS, pi_gb=float(np.min(pisos)),
        tau_sellers=sv.tau, tau_buyers=sv.tau_buyers, t_span=(0.0, T_ACO),
        n_points=sv.n_points, rtol=1e-6,
        buyer_competition=sv.buyer_competition,
        arranque=sv.arranque_acoplado)
    directo = solve_coupled_for_hour(**comun, costo_vendedor="alternativa",
                                     piso_j=pisos, piso_juego="marginal")
    assert directo.success, directo.message
    res = EMSP2P(agents=_agentes(h), grid=grid, solver=sv).run_single_hour(
        h["k"], h["D"], h["G"])
    assert res.P_star is not None, res.motivo
    assert np.array_equal(res.P_star, np.asarray(directo.P_star, dtype=float))
    # La prueba separa: con los defectos la hora no da lo mismo.
    defecto = solve_coupled_for_hour(**comun)
    assert not np.array_equal(np.asarray(defecto.P_star, dtype=float),
                              np.asarray(directo.P_star, dtype=float))


def test_pedir_la_alternativa_sin_piso_por_agente_deja_la_hora_con_su_motivo():
    """Fallar en voz alta: sin `pi_gb_agente` la hora no tiene con que
    sustituir b_j, y la via acoplada la rechaza. El motor la anota con su
    motivo (C-190), que es lo que hace salir la corrida con el codigo 3 de
    D38."""
    h = _hora()
    res = _run_hour_worker(_args38(h) + ("alternativa", "minimo"))
    assert res.P_star is None
    assert "piso_j" in res.motivo and "excepcion del acoplado" in res.motivo


def test_por_el_motor_la_dinamica_regularizada_es_identica_a_llamar_directo():
    h = _hora()
    sids, bids = h["sids"], h["bids"]
    sv = SolverParams(parallel=False, metodo="acoplado", t_span_acoplado=T_ACO,
                      mu_entropia=1.0, nivel_acoplado="sigma")
    directo = solve_coupled_for_hour(
        G_net_j=np.array([h["g_klim"][j] - h["d_k"][j] for j in sids]),
        D_net_i=np.array([h["d_k"][i] - h["g_klim"][i] for i in bids]),
        a_j=h["a"][sids], b_j=h["b"][sids], lam_j=h["lam"][sids],
        theta_j=h["theta"][sids], G_klim_i=h["g_klim"][bids],
        lam_i=h["lam"][bids], theta_i=h["theta"][bids],
        etha_i=h["etha"][bids], pi_gs=PGS, pi_gb=PGB, tau_sellers=sv.tau,
        tau_buyers=sv.tau_buyers, t_span=(0.0, T_ACO), n_points=sv.n_points,
        rtol=1e-6, buyer_competition=sv.buyer_competition,
        arranque=sv.arranque_acoplado, mu_entropia=1.0, nivel="sigma")
    assert directo.success, directo.message
    res = EMSP2P(agents=_agentes(h), grid=GridParams(pi_gs=PGS, pi_gb=PGB),
                 solver=sv).run_single_hour(h["k"], h["D"], h["G"])
    assert res.P_star is not None, res.motivo
    assert np.array_equal(res.P_star, np.asarray(directo.P_star, dtype=float))
    assert np.array_equal(res.pi_star, np.clip(directo.pi_star, PGB, PGS))
    # La prueba separa: con los defectos la hora no da lo mismo.
    defecto = EMSP2P(agents=_agentes(h), grid=GridParams(pi_gs=PGS, pi_gb=PGB),
                     solver=SolverParams(parallel=False, metodo="acoplado",
                                         t_span_acoplado=T_ACO)
                     ).run_single_hour(h["k"], h["D"], h["G"])
    assert not np.array_equal(defecto.pi_star, res.pi_star)


# ─── la linea de ordenes ───────────────────────────────────────────────────


def test_la_linea_d49_solo_sale_con_la_dinamica_activa():
    import main_simulation as ms
    assert ms.linea_dinamica_regularizada(SolverParams()) is None
    uno = ms.linea_dinamica_regularizada(SolverParams(mu_entropia=1.0))
    assert "mu = 1 (COP/kWh)" in uno and "sigma" not in uno
    dos = ms.linea_dinamica_regularizada(SolverParams(nivel_acoplado="sigma"))
    assert "presupuesto sigma" in dos and "mu =" not in dos
    ambas = ms.linea_dinamica_regularizada(
        SolverParams(mu_entropia=0.5, nivel_acoplado="sigma"))
    assert "mu = 0.5" in ambas and "presupuesto sigma" in ambas
    assert "no es la via de produccion (D48)" in ambas


def test_la_linea_d68_solo_sale_con_alguna_palanca_activa():
    import main_simulation as ms
    assert ms.linea_palancas_del_piso(SolverParams()) is None
    uno = ms.linea_palancas_del_piso(
        SolverParams(costo_vendedor="alternativa"))
    assert "alternativa piso_j" in uno and "vendedor marginal" not in uno
    dos = ms.linea_palancas_del_piso(SolverParams(piso_juego="marginal"))
    assert "vendedor marginal" in dos and "alternativa piso_j" not in dos
    ambas = ms.linea_palancas_del_piso(
        SolverParams(costo_vendedor="alternativa", piso_juego="marginal"))
    assert "alternativa piso_j" in ambas and "vendedor marginal" in ambas
    assert "no cambian la via de produccion" in ambas


class _Para(Exception):
    """Detiene `main` al construir el motor, antes de resolver ni escribir
    nada."""


@pytest.mark.parametrize("mu, nivel, linea", [
    (0.7, "sigma", True), (0.0, "c136", False)])
def test_main_lleva_las_opciones_hasta_el_motor_y_anuncia_d49(
        monkeypatch, capsys, tmp_path, mu, nivel, linea):
    import main_simulation as ms
    vistos = []

    def para(agents, grid, solver):
        vistos.append(solver)
        raise _Para()

    monkeypatch.setattr(ms, "EMSP2P", para)
    with pytest.raises(_Para):
        ms.main(use_real_data=False, metodo="acoplado", mu_entropia=mu,
                nivel_acoplado=nivel, out_dir=str(tmp_path))
    assert len(vistos) == 1
    assert (vistos[0].metodo, vistos[0].mu_entropia,
            vistos[0].nivel_acoplado) == ("acoplado", mu, nivel)
    assert ("[D49] Dinamica regularizada" in capsys.readouterr().out) == linea
    # Nada escrito: `main` se detuvo antes de resolver el mercado.
    assert not any(tmp_path.iterdir())


def _cli(*flags):
    """La linea de ordenes en un subproceso. SALVAGUARDA, como en
    `tests/test_reposo_motor.py`: `MTE_ROOT` apunta a una carpeta que no
    existe, de modo que nada puede cargar datos reales. Solo se prueban la
    ayuda y los errores, que salen antes de `main`."""
    entorno = dict(os.environ,
                   MTE_ROOT=str(RAIZ / "no_existe_carpeta_de_mediciones"))
    return subprocess.run([sys.executable, str(RAIZ / "main_simulation.py"),
                           *flags], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=str(RAIZ),
                          env=entorno, timeout=120)


@pytest.mark.parametrize("costo, piso, linea", [
    ("lcoe", "marginal", True), ("lcoe", "minimo", False)])
def test_main_lleva_las_palancas_del_piso_hasta_el_motor_y_anuncia_d68(
        monkeypatch, capsys, tmp_path, costo, piso, linea):
    import main_simulation as ms
    vistos = []

    def para(agents, grid, solver):
        vistos.append(solver)
        raise _Para()

    monkeypatch.setattr(ms, "EMSP2P", para)
    with pytest.raises(_Para):
        ms.main(use_real_data=False, metodo="acoplado", costo_vendedor=costo,
                piso_juego=piso, out_dir=str(tmp_path))
    assert len(vistos) == 1
    assert (vistos[0].metodo, vistos[0].costo_vendedor,
            vistos[0].piso_juego) == ("acoplado", costo, piso)
    assert ("[D68] Palancas del piso marginal" in capsys.readouterr().out
            ) == linea
    # Nada escrito: `main` se detuvo antes de resolver el mercado.
    assert not any(tmp_path.iterdir())


def test_main_rechaza_la_alternativa_sin_el_piso_por_vendedor(monkeypatch,
                                                              tmp_path):
    """La compuerta de arranque: `main` sabe si la corrida trae la matriz de
    pisos por agente, y sin ella rechaza `--costo-vendedor alternativa` ANTES
    de resolver ninguna hora. El caso sintetico nunca la trae."""
    import main_simulation as ms
    llamadas = []

    def para(agents, grid, solver):
        llamadas.append(solver)
        raise _Para()

    monkeypatch.setattr(ms, "EMSP2P", para)
    with pytest.raises(ValueError, match=r"--data real.*--full.*--day"):
        ms.main(use_real_data=False, metodo="acoplado",
                costo_vendedor="alternativa", out_dir=str(tmp_path))
    # Ni siquiera se construyo el motor, y no se escribio nada.
    assert llamadas == []
    assert not any(tmp_path.iterdir())
    # La otra palanca no la necesita: el piso marginal sale de la caminata, que
    # con un piso escalar tiene un solo nivel.
    with pytest.raises(_Para):
        ms.main(use_real_data=False, metodo="acoplado", piso_juego="marginal",
                out_dir=str(tmp_path))
    assert len(llamadas) == 1
    # Y sin la via acoplada la palanca es inerte: no se rechaza, se avisa.
    llamadas.clear()
    with pytest.raises(_Para):
        ms.main(use_real_data=False, metodo="alternado",
                costo_vendedor="alternativa", out_dir=str(tmp_path))
    assert len(llamadas) == 1


def test_la_ayuda_muestra_las_opciones_de_la_dinamica():
    res = _cli("--help")
    assert res.returncode == 0, res.stderr
    for opcion in ("--mu-entropia", "--nivel-acoplado", "c136", "sigma",
                   "--costo-vendedor", "--piso-juego", "lcoe", "alternativa",
                   "minimo", "marginal"):
        assert opcion in res.stdout, opcion


def test_pedir_las_palancas_del_piso_sin_la_via_acoplada_avisa_d68():
    res = _cli("--metodo", "alternado", "--full", "--costo-vendedor",
               "alternativa", "--piso-juego", "marginal")
    assert res.returncode == 2, (res.returncode, res.stdout[-500:])
    assert ("[D68] AVISO: --costo-vendedor, --piso-juego no tiene efecto "
            "sin --metodo acoplado: la via alternado no integra la dinamica"
            ) in res.stdout, res.stdout[-800:]
    assert "CAL-48" in res.stderr and "Cargando datos" not in res.stdout
    # Sin pedirlas, no hay aviso.
    res = _cli("--metodo", "alternado", "--full")
    assert res.returncode == 2 and "[D68]" not in res.stdout


@pytest.mark.parametrize("flags", [
    ("--costo-vendedor", "otro"), ("--costo-vendedor", "LCOE"),
    ("--piso-juego", "otro"), ("--piso-juego", "Marginal")])
def test_un_valor_invalido_de_las_palancas_del_piso_sale_con_error(flags):
    res = _cli(*flags)
    assert res.returncode == 2, (res.returncode, res.stdout[-500:])
    assert "invalid choice" in res.stderr, res.stderr[-800:]
    assert "Cargando datos" not in res.stdout


def test_pedir_la_dinamica_sin_la_via_acoplada_avisa_d49():
    # Menor 6 de la revision. `--metodo alternado --full` sale por `ap.error`
    # (CAL-48) DESPUES del aviso y antes de cargar ningun dato.
    res = _cli("--metodo", "alternado", "--full", "--mu-entropia", "1",
               "--nivel-acoplado", "sigma")
    assert res.returncode == 2, (res.returncode, res.stdout[-500:])
    assert ("[D49] AVISO: --mu-entropia, --nivel-acoplado no tiene efecto "
            "sin --metodo acoplado: la via alternado no integra la dinamica"
            ) in res.stdout, res.stdout[-800:]
    assert "CAL-48" in res.stderr and "Cargando datos" not in res.stdout
    # Sin pedirlas, no hay aviso.
    res = _cli("--metodo", "alternado", "--full")
    assert res.returncode == 2 and "[D49]" not in res.stdout


@pytest.mark.parametrize("flags, mensaje", [
    (("--mu-entropia", "-1"), "--mu-entropia tiene que ser un numero finito"),
    (("--mu-entropia", "nan"), "--mu-entropia tiene que ser un numero finito"),
    (("--mu-entropia", "inf"), "--mu-entropia tiene que ser un numero finito"),
    (("--mu-entropia", "uno"), "invalid float value"),
    (("--nivel-acoplado", "otro"), "invalid choice"),
])
def test_un_valor_invalido_de_la_dinamica_sale_con_error(flags, mensaje):
    res = _cli(*flags)
    assert res.returncode == 2, (res.returncode, res.stdout[-500:])
    assert mensaje in res.stderr, res.stderr[-800:]
    assert "Cargando datos" not in res.stdout


# ─── la compuerta ejecutada directa (importante 1 de la revision) ──────────

COMPUERTA = RAIZ / "tests" / "gate_reposo_cero_dinamica.py"
# Un complemento de pytest que fuerza el fallo de la compuerta sin tocarla:
# pone la tolerancia de precio en negativo en el modulo recogido.
FUERZA_FALLO = '''
def pytest_collection_modifyitems(session, config, items):
    for item in items:
        item.module.TOL_PI = -1.0
'''


def _compuerta(entorno_extra=None, por_pytest=False):
    """La compuerta en un subproceso, sin horizonte parcial ni tope heredados:
    directa (`python tests/gate_reposo_cero_dinamica.py`) o por
    `python -m pytest ... -k "not lenta"`. Corre solo las dos horas rapidas
    (unos segundos)."""
    entorno = {k: v for k, v in os.environ.items()
               if k not in ("HORIZONTE_COMPUERTA", "TOPE_COMPUERTA_S",
                            "PYTEST_ADDOPTS")}
    entorno.update(entorno_extra or {})
    orden = [sys.executable, "-u", str(COMPUERTA)]
    if por_pytest:
        orden = [sys.executable, "-u", "-m", "pytest", str(COMPUERTA), "-k",
                 "not lenta", "-s", "-q", "-p", "no:cacheprovider"]
    return subprocess.run(orden, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=str(RAIZ),
                          env=entorno, timeout=300)


def _compuerta_directa(entorno_extra=None):
    return _compuerta(entorno_extra)


def test_la_compuerta_directa_corre_las_dos_rapidas_y_sale_con_cero():
    res = _compuerta_directa()
    assert res.returncode == 0, (res.stdout[-1500:], res.stderr[-800:])
    assert "2 passed, 2 deselected" in res.stdout, res.stdout[-800:]
    assert "hora 853 (interiores)" in res.stdout
    assert "hora 2120 (excluidos)" in res.stdout


def test_la_compuerta_directa_con_un_fallo_forzado_sale_distinto_de_cero(
        tmp_path):
    (tmp_path / "fuerza_fallo_compuerta.py").write_text(FUERZA_FALLO,
                                                        encoding="utf-8")
    res = _compuerta_directa({"PYTHONPATH": str(tmp_path),
                              "PYTEST_ADDOPTS": "-p fuerza_fallo_compuerta"})
    assert res.returncode not in (0, None), res.stdout[-800:]
    assert "2 failed" in res.stdout, res.stdout[-800:]


def test_por_pytest_con_horizonte_parcial_las_horas_salen_saltadas():
    # Por `python -m pytest` el horizonte parcial se admite (es para medir las
    # lentas en el servidor), y las horas dentro de la aceptacion salen
    # SALTADAS, nunca aprobadas.
    res = _compuerta({"HORIZONTE_COMPUERTA": "0.5"}, por_pytest=True)
    assert res.returncode == 0, (res.stdout[-1500:], res.stderr[-800:])
    assert "2 skipped, 2 deselected" in res.stdout, res.stdout[-800:]
    assert "HORIZONTE PARCIAL t = 0.5" in res.stdout


@pytest.mark.parametrize("valor", ["0.5", " 1 ", "5", "0.25", "uno"])
def test_directa_con_horizonte_parcial_se_niega_y_sale_con_dos(valor):
    # Ronda de arreglos 2: directa, la variable no vacia (valida o no) no se
    # admite; antes salia con 0 y «2 skipped».
    res = _compuerta_directa({"HORIZONTE_COMPUERTA": valor})
    assert res.returncode == 2, (res.returncode, res.stdout[-800:],
                                 res.stderr[-800:])
    assert "exige t = 5" in res.stderr, res.stderr[-800:]
    assert "python -m pytest" in res.stderr
    assert "passed" not in res.stdout and "skipped" not in res.stdout


def test_directa_con_la_variable_vacia_corre_como_siempre():
    res = _compuerta_directa({"HORIZONTE_COMPUERTA": "  "})
    assert res.returncode == 0, (res.stdout[-1500:], res.stderr[-800:])
    assert "2 passed, 2 deselected" in res.stdout


@pytest.mark.parametrize("valor, horizonte, puntos", [
    ("", 5.0, 51), ("0.5", 0.5, 6), (" 1 ", 1.0, 11), ("2", 2.0, 21),
    ("0.3", 0.3, 4), ("0.7", 0.7, 8), ("5.0", 5.0, 51)])
def test_el_horizonte_valido_da_un_punto_de_control_cada_decima(
        monkeypatch, valor, horizonte, puntos):
    import gate_reposo_cero_dinamica as compuerta
    monkeypatch.setenv("HORIZONTE_COMPUERTA", valor)
    assert compuerta._horizonte() == (horizonte, puntos)
    t = np.linspace(0.0, horizonte, puntos)
    np.testing.assert_allclose(np.diff(t), 0.1, rtol=0, atol=1e-12)


@pytest.mark.parametrize("valor, motivo", [
    ("0", "tiene que estar en"), ("-1", "tiene que estar en"),
    ("6", "tiene que estar en"), ("nan", "tiene que estar en"),
    ("inf", "tiene que estar en"), ("uno", "no es un numero"),
    ("0.25", "multiplo de 0.1"), ("0.05", "multiplo de 0.1"),
    ("1.23", "multiplo de 0.1"), ("4.95", "multiplo de 0.1")])
def test_un_horizonte_invalido_o_que_no_es_multiplo_de_una_decima_se_rechaza(
        monkeypatch, valor, motivo):
    import gate_reposo_cero_dinamica as compuerta
    monkeypatch.setenv("HORIZONTE_COMPUERTA", valor)
    with pytest.raises(ValueError, match=motivo):
        compuerta._horizonte()


def test_por_pytest_un_horizonte_invalido_falla_al_importar():
    res = _compuerta({"HORIZONTE_COMPUERTA": "0.25"}, por_pytest=True)
    assert res.returncode != 0, res.stdout[-800:]
    assert "multiplo de 0.1" in res.stdout + res.stderr, res.stdout[-800:]
    assert "passed" not in res.stdout and "skipped" not in res.stdout


if __name__ == "__main__":
    _genera()
