"""
La dinamica regularizada como opcion apagada de la via acoplada (D49, D50).
2026-09-17.

QUE SE PRUEBA. `solve_coupled_for_hour` gana tres opciones, apagadas por
defecto: la exploracion entropica del replicador del vendedor
(`mu_entropia`, el termino V3a de la sonda del consenso), el arranque de los
precios en el presupuesto sigma del reposo (`nivel="sigma"`) y el arranque
desde un estado dado (`estado_inicial`). El motor (`SolverParams`, la tupla
del trabajador con su shim de 36 a 38 campos) y la linea de ordenes
(`--mu-entropia`, `--nivel-acoplado`, la linea [D49]) las llevan hasta la via
acoplada.

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
  - los valores invalidos se rechazan en `solve_coupled_for_hour` (tambien
    `nivel="sigma"` con el peso de precio), en `SolverParams`, en la tupla y
    en la linea de ordenes, que ademas avisa [D49] si se piden sin la via
    acoplada;
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
from core.reposo_mercado import presupuesto_precios, resuelve_reposo  # noqa: E402
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
                    b=np.full(2, 225.0), techo=1250.0, piso=114.0)
    s, d, b, techo, piso_j = _entradas(874)
    return dict(G=s, D=d, b=b, techo=techo, piso=float(piso_j[0]))


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
DEFECTOS = dict(mu_entropia=0.0, nivel="c136", estado_inicial=None)


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


def test_la_ayuda_muestra_las_opciones_de_la_dinamica():
    res = _cli("--help")
    assert res.returncode == 0, res.stderr
    for opcion in ("--mu-entropia", "--nivel-acoplado", "c136", "sigma"):
        assert opcion in res.stdout, opcion


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
