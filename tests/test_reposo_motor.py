"""
El motor resuelve el mercado por el reposo (`--metodo reposo`; D48). 2026-09-17.

QUE SE PRUEBA. La tarea 1 construyo el nucleo puro `core/reposo_mercado.py`,
que calcula en forma cerrada el reposo del juego regularizado de una hora. Esta
prueba cubre su conexion al motor (`core/ems_p2p.py`) y a la linea de ordenes
(`main_simulation.py`):

  - la via por reposo del motor da EXACTAMENTE lo que el nucleo con las mismas
    entradas, por `EMSP2P.run_single_hour` y por el lote de `EMSP2P.run`;
  - la participacion de los vendedores (paso 7, C-151) con el precio
    liquidado: el retirado sale con su fila en cero, sigue en `seller_ids`
    (la trampa de H-43) y el conjunto reducido vuelve a pasar por el nucleo;
  - la captura y las cotas de optimalidad (D55) se calculan DESPUES de la
    participacion;
  - la compuerta de la participacion de la revision de la tarea 1: tras ella,
    ningun vendedor despachado cobra por debajo de su piso y la parte del
    vendedor no es negativa;
  - las cotas de optimalidad se miden sobre quien puede comerciar al final:
    los excluidos por D61 entran con cantidad cero (revision de la tarea 2);
  - D63 a D69 (tarea 5a): con el piso del vendedor marginal la participacion
    es una guarda inerte (D67): nadie se retira, en horas a mano y en miles de
    horas al azar con las tres opciones de despacho; los retiros de la via por
    reposo se cuentan en `retiros_reposo` y llegan a la linea [D48] y al
    codigo de salida de D38; los campos nuevos (piso marginal, renta
    inframarginal, parte del juego, vendedores no despachados) llegan al
    resultado de la hora y al almacen; "merito" es alias de "costo";
  - las vias acoplada y alternada no cambian: contra literales calculados con
    el CODIGO BASE (commit a392cbd), y la tupla de 32 campos contra la de 36;
  - los valores desconocidos se rechazan en `SolverParams`, en la tupla y en
    la linea de ordenes, y con datos reales sin `--metodo` la via es reposo;
  - el camino de excepcion del reposo: el ValueError del nucleo, la vuelta
    reducida que revienta, el costo cuadratico no nulo (CAL-32) y el polvo
    negativo de los netos; la hora queda con su motivo, sin anotarse como
    resuelta, y cuenta para el codigo de salida 3;
  - la linea [D48] y las columnas del almacen, con una corrida SINTETICA
    minima de `main` en una carpeta temporal.

SIN DATOS REALES. La hora sale del caso sintetico de la compuerta C-165 (la
misma `_hora` de `test_criterio_reparto.py`), y las horas de participacion y
de un solo comprador se arman a mano con literales.

COMO SE PRUEBA UN BLOQUE QUE YA NO MUERDE. Con D63 la participacion no retira
a nadie, pero el bloque no cambia (D67) y tiene que seguir funcionando si
alguna vez retira. Las pruebas de su mecanica (la fila en cero, la recursion,
las cotas del conjunto reducido, la energia ofrecida y comerciable de los
retirados, el motivo de la vuelta que revienta) sustituyen el nucleo del motor
por `_nucleo_con_piso_minimo`, que resuelve la hora con el piso minimo de los
vendedores con ganancia posible, la regla de D62 con la que se escribieron, y
cuentan los retiros en `retiros_reposo`. Las pruebas de la regla vigente usan
el nucleo tal cual.
"""
from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import scipy

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import core.almacen as almacen_mod  # noqa: E402
import core.ems_p2p as motor  # noqa: E402
from core.ems_p2p import (  # noqa: E402
    CAMPOS_REPOSO, PREFIJO_EXCEPCION_REPOSO, TOL_NETO_REPOSO, TOL_REPARTO,
    AgentParams, EMSP2P, GridParams, HourlyResult, SolverParams,
    _entradas_reposo, _run_hour_worker)
from core.reposo_mercado import (  # noqa: E402
    captura, cotas_optimalidad, resuelve_reposo)
from gate_c165_desglose_horario import _caso  # noqa: E402
from test_criterio_reparto import _hora  # noqa: E402

PGS, PGB = 1250.0, 114.0
T_ACO = 0.002          # horizonte corto del acoplado, para que corra en segundos
# Pisos por vendedor que retiran a sids[0] en la via acoplada (el mercado le
# paga 500 < 600), como en `test_arranque_acoplado.py`; sirven para que la
# comparacion de las otras vias pase por la recursion de H-43.
PISO_H43 = np.array([600.0, 300.0])
# D64: el despacho por defecto es "piso" (antes "merito").
DEFECTOS_REPOSO = ("sigma", None, "uniforme", "piso")


def _nucleo_con_piso_minimo(monkeypatch):
    """Sustituye el nucleo del motor por uno que resuelve la hora con el piso
    MINIMO de los vendedores con ganancia posible (la regla de D62, con la que
    la participacion retiraba): a cada vendedor activo cuyo piso no supera el
    techo mayor de los compradores activos se le da ese minimo; los demas
    conservan el suyo y siguen fuera por D61. La participacion del motor mide
    a cada vendedor contra SU piso (`pi_gb_j`), de modo que el de piso alto
    vuelve a quedar bajo el suyo y se retira: es la forma de ejercer el bloque
    de D67, que con el nucleo vigente no muerde."""
    original = motor.resuelve_reposo

    def piso_minimo(s, d, b, techo, piso_j, **kw):
        s_, d_ = np.asarray(s, float), np.asarray(d, float)
        t = np.broadcast_to(np.asarray(techo, float), d_.shape)
        p = np.array(np.broadcast_to(np.asarray(piso_j, float), s_.shape))
        if np.any(d_ > 0):
            pueden = (s_ > 0) & (p <= t[d_ > 0].max())
            if pueden.any():
                p[pueden] = p[pueden].min()
        return original(s, d, b, techo, p, **kw)

    monkeypatch.setattr(motor, "resuelve_reposo", piso_minimo)
    return original


# ─── piezas ────────────────────────────────────────────────────────────────


def _agentes(h):
    N = h["a"].shape[0]
    return AgentParams(N=N, a=h["a"], b=h["b"], c=h["c"], lam=h["lam"],
                       theta=h["theta"], etha=h["etha"])


def _netos(h, sids=None, bids=None):
    sids = h["sids"] if sids is None else sids
    bids = h["bids"] if bids is None else bids
    s = np.array([h["g_klim"][j] - h["d_k"][j] for j in sids])
    d = np.array([h["d_k"][i] - h["g_klim"][i] for i in bids])
    return s, d


def _args32(h, metodo, pi_gb_j=None, pi_gs=PGS, pi_gb=PGB):
    """La tupla de 32 campos de `_run_hour_worker`, la de antes de D48."""
    sv = SolverParams()
    return (h["k"], h["g_klim"], h["d_k"], h["g_k"], h["sids"], h["bids"],
            h["a"], h["b"], h["lam"], h["theta"], h["etha"],
            pi_gs, pi_gb, sv.tau, sv.tau_buyers, sv.t_span, sv.n_points,
            sv.stackelberg_iters, sv.stackelberg_tol, sv.stackelberg_max,
            sv.ode_method, sv.buyer_competition,
            metodo, T_ACO, pi_gb_j, False,
            1e-6, None, None, "factible", "precio", TOL_REPARTO)


def _cotas_por_agente(h, techo_buyers=None, piso_sellers=None):
    """Matrices (N, T) de techo y piso del caso sintetico, con valores dados
    para los compradores y los vendedores de la hora `h`."""
    N, T = h["D"].shape
    techo = np.full((N, T), PGS)
    piso = np.full((N, T), PGB)
    if techo_buyers is not None:
        techo[h["bids"], :] = np.asarray(techo_buyers, dtype=float)[:, None]
    if piso_sellers is not None:
        piso[h["sids"], :] = np.asarray(piso_sellers, dtype=float)[:, None]
    return techo, piso


# La hora armada a mano de la participacion. Dos vendedores con 5 (kWh) de
# excedente cada uno: el 0 es el mas barato (b = 210 (COP/kWh)) y tiene el piso
# mas alto (1 200); el 1 cuesta 225 y su piso es 300. Dos compradores con
# deficit de 1 y 5 (kWh) y techos de 1 250 y 400. Sobran vendedores.
#   - Con D62 (merito por b y piso minimo) despachaban 5 el 0 y 1 el 1, el
#     excedente antes de la participacion era 1 250 + 400·5 - (1 200·5 + 300)
#     = -3 050 (COP) con un optimo de 550, el 0 cobraba 387,5 < 1 200 y se
#     retiraba.
#   - Con D63 (el nucleo vigente) la caminata cierra en 300: al nivel 300 el
#     volumen es 5 y al nivel 1 200, min(10; 1) = 1. Vende sus 5 (kWh) el 1,
#     el 0 no despacha, nadie cobra bajo su piso y nadie se retira.
#   - Con `_nucleo_con_piso_minimo`, los dos en el mismo piso despachan 3 y
#     3, el 0 cobra 387,5 y se retira, y el 1 vende sus 5 (kWh) en la vuelta
#     reducida, como antes.
MANO = dict(
    D=np.array([[1.0], [1.0], [1.0], [5.0]]),
    G=np.array([[6.0], [6.0], [0.0], [0.0]]),
    b=np.array([210.0, 225.0, 225.0, 225.0]),
    techo=np.array([[1250.0], [1250.0], [1250.0], [400.0]]),
    piso=np.array([[1200.0], [300.0], [300.0], [300.0]]))


def _ems_mano(**solver):
    N = MANO["D"].shape[0]
    return EMSP2P(
        AgentParams(N=N, a=np.zeros(N), b=MANO["b"], c=np.zeros(N),
                    lam=np.full(N, 100.0), theta=np.full(N, 0.5),
                    etha=np.full(N, 0.1)),
        GridParams(PGS, 300.0, MANO["techo"], MANO["piso"]),
        SolverParams(parallel=False, metodo="reposo", **solver))


def _igual_al_bit(a: HourlyResult, b: HourlyResult, campos) -> None:
    for campo in campos:
        x, y = getattr(a, campo), getattr(b, campo)
        if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
            assert x is not None and y is not None, campo
            assert np.array_equal(x, y), campo
        else:
            assert x == y, campo


CAMPOS_DE_SIEMPRE = ("P_star", "pi_star", "P_int", "P_ext", "SC", "SS", "IE",
                     "PS", "PSR", "Wj_total", "Wi_total", "iters_used",
                     "norm_rel_final", "seller_ids", "buyer_ids", "retirados",
                     "motivo", "horizonte_usado", "parada_acoplado",
                     "residuo_reparto", "evaluaciones")


# ─── la via por reposo es el nucleo ────────────────────────────────────────


def test_run_single_hour_da_exactamente_el_nucleo_con_cotas_escalares():
    h = _hora()
    ems = EMSP2P(_agentes(h), GridParams(PGS, PGB),
                 SolverParams(parallel=False, metodo="reposo"))
    res = ems.run_single_hour(h["k"], h["D"], h["G"])
    s, d = _netos(h)
    rep = resuelve_reposo(s, d, h["b"][h["sids"]], PGS, PGB)
    assert res.motivo == "" and res.retirados == []
    assert np.array_equal(res.P_star, rep.P)
    assert np.array_equal(res.pi_star, rep.p_liquidado)
    assert np.array_equal(res.pi_reposo, rep.pi_reposo)
    assert res.regimen == rep.regimen
    assert res.presupuesto == rep.S
    assert res.precio_comun == rep.ell
    assert res.precio_uniforme == rep.p_u
    assert res.piso_juego == rep.piso
    assert res.n_soluciones == rep.n_soluciones
    assert res.orden_merito == [h["sids"][j] for j in rep.orden_merito]
    # D63 y D69: los campos nuevos, tal cual del nucleo.
    assert res.piso_marginal == rep.piso_marginal == rep.piso
    assert res.renta_inframarginal == rep.renta_inframarginal
    assert res.parte_juego == rep.parte_juego
    assert res.vendedores_no_despachados == [
        h["sids"][j] for j in rep.vendedores_no_despachados]
    assert res.retiros_reposo == 0
    optimo, peor = cotas_optimalidad(s, d, PGS, PGB, rep.E)
    assert res.excedente_optimo == optimo and res.excedente_peor == peor
    assert res.captura == captura(rep.excedente, optimo)
    # Nada que integrar.
    assert res.iters_used == 0 and res.norm_rel_final == 0.0
    assert res.residuo_reparto == 0.0 and res.horizonte_usado == 0.0
    assert res.parada_acoplado == "reposo" and res.evaluaciones == 0
    assert np.isfinite(res.segundos) and res.segundos >= 0.0


def test_run_single_hour_da_exactamente_el_nucleo_con_cotas_por_agente():
    # El techo de cada comprador y el piso de cada vendedor, como la corrida
    # con datos reales (C-146, H-49). Pisos distintos pero bajo el precio
    # liquidado: nadie se retira y el resultado es el del nucleo.
    h = _hora()
    techo, piso = _cotas_por_agente(h, techo_buyers=[780.0, 792.0, 816.0],
                                    piso_sellers=[314.0, 328.0])
    ems = EMSP2P(_agentes(h), GridParams(PGS, PGB, techo, piso),
                 SolverParams(parallel=False, metodo="reposo"))
    res = ems.run_single_hour(h["k"], h["D"], h["G"])
    s, d = _netos(h)
    rep = resuelve_reposo(s, d, h["b"][h["sids"]], techo[h["bids"], h["k"]],
                          piso[h["sids"], h["k"]])
    assert res.retirados == []
    assert np.array_equal(res.P_star, rep.P)
    assert np.array_equal(res.pi_star, rep.p_liquidado)
    assert res.regimen == rep.regimen
    assert res.presupuesto == rep.S


def test_las_opciones_viajan_hasta_el_nucleo():
    h = _hora()
    s, d = _netos(h)
    for kw in (dict(modo_presupuesto="sigma", sigma_nivel=0.5),
               dict(regla_precio="puja"),
               dict(despacho_vendedores="llenado"),
               dict(despacho_vendedores="costo"),
               dict(modo_presupuesto="algoritmo3")):
        ems = EMSP2P(_agentes(h), GridParams(PGS, PGB),
                     SolverParams(parallel=False, metodo="reposo", **kw))
        res = ems.run_single_hour(h["k"], h["D"], h["G"])
        nucleo = dict(kw)
        if "sigma_nivel" in nucleo:
            nucleo["sigma"] = nucleo.pop("sigma_nivel")
        if nucleo.get("modo_presupuesto") == "algoritmo3":
            nucleo["pi_gs"] = PGS
        rep = resuelve_reposo(s, d, h["b"][h["sids"]], PGS, PGB, **nucleo)
        assert np.array_equal(res.P_star, rep.P), kw
        assert np.array_equal(res.pi_star, rep.p_liquidado), kw
        assert res.presupuesto == rep.S, kw


def test_el_lote_de_run_da_lo_mismo_que_run_single_hour():
    # Techos y pisos al azar, con pisos por encima de algunos techos, para
    # que el lote pase tambien por D61 y por la participacion.
    h = _hora()
    D, G = h["D"], h["G"]
    N, T = D.shape
    rng = np.random.default_rng(5)
    techo = rng.uniform(650.0, 1250.0, (N, T))
    piso = rng.uniform(150.0, 700.0, (N, T))
    ems = EMSP2P(_agentes(h), GridParams(PGS, PGB, techo, piso),
                 SolverParams(parallel=False, metodo="reposo"))
    lote, _, _ = ems.run(D, G)
    assert len(lote) == T
    for k in range(T):
        una = ems.run_single_hour(k, D, G)
        _igual_al_bit(lote[k], una, CAMPOS_DE_SIEMPRE + CAMPOS_REPOSO)


# ─── la participacion (paso 7) ─────────────────────────────────────────────


def test_d67_con_el_piso_marginal_el_de_piso_alto_no_se_retira():
    """D63 y D67. La hora sintetica con pisos 900 y 300: con D62 el precio
    liquidado era 782,8 (COP/kWh), el de 900 quedaba bajo su piso y se
    retiraba. Con el piso marginal (vendedores cortos: despachan los dos) el
    piso del juego es 900, los dos cobran 1 077,87 y nadie se retira."""
    h = _hora()
    piso_j = np.array([900.0, 300.0])
    s, d = _netos(h)
    completo = resuelve_reposo(s, d, h["b"][h["sids"]], PGS, piso_j)
    assert np.all(completo.s_despachado > 0.0)
    assert completo.piso == 900.0 and completo.p_u >= 900.0
    res = _run_hour_worker(_args32(h, "reposo", pi_gb_j=piso_j)
                           + DEFECTOS_REPOSO)
    assert res.motivo == "" and res.retirados == []
    assert res.retiros_reposo == 0
    assert np.array_equal(res.P_star, completo.P)
    assert np.array_equal(res.pi_star, completo.p_liquidado)
    assert res.piso_juego == res.piso_marginal == 900.0
    assert res.renta_inframarginal == completo.renta_inframarginal > 0.0
    assert res.captura == captura(completo.excedente, res.excedente_optimo)


def test_la_participacion_usa_la_tolerancia_del_nucleo_por_reposo(monkeypatch):
    """Revision de la tarea 5a, menor 1: por la via del reposo la
    participacion compara con la MISMA holgura con que el nucleo da la hora
    por buena (`TOL_COBERTURA_REL` relativa al piso); las otras vias conservan
    la absoluta de 1e-9, para seguir identicas al bit."""
    import dataclasses

    from core.ems_p2p import tol_participacion
    from core.reposo_mercado import TOL_COBERTURA_REL
    assert tol_participacion("reposo", 700.0) == TOL_COBERTURA_REL * 700.0
    assert tol_participacion("reposo", -700.0) == TOL_COBERTURA_REL * 700.0
    assert tol_participacion("reposo", 0.5) == TOL_COBERTURA_REL
    for via in ("acoplado", "alternado"):
        assert tol_participacion(via, 700.0) == 1e-9

    # La hora: dos vendedores de 2 (kWh) con pisos 700 y 300 y un comprador de
    # 5 (kWh); vendedores cortos, el piso del juego es 700 y los dos cobran
    # 700. Se liquida 1e-8 (COP/kWh) por debajo: dentro de la holgura del
    # nucleo (7e-7 con piso 700), fuera de la absoluta de 1e-9.
    tupla = dict(G=[3.0, 3.0, 0.0], D=[1.0, 1.0, 5.0], sids=[0, 1], bids=[2],
                 techo=1000.0, piso_j=[700.0, 300.0])
    original = motor.resuelve_reposo

    def liquida_bajo(rebaja):
        def parche(*a, **kw):
            r = original(*a, **kw)
            return dataclasses.replace(
                r, p_liquidado=r.p_liquidado - rebaja)
        return parche

    limpia = _run_hour_worker(_tupla_mano(**tupla))
    assert limpia.piso_juego == 700.0 and limpia.retirados == []

    monkeypatch.setattr(motor, "resuelve_reposo", liquida_bajo(1e-8))
    dentro = _run_hour_worker(_tupla_mano(**tupla))
    assert dentro.motivo == ""
    assert dentro.retirados == [] and dentro.retiros_reposo == 0
    # Con una rebaja de verdad, la guarda sigue mordiendo.
    monkeypatch.setattr(motor, "resuelve_reposo", liquida_bajo(1e-4))
    fuera = _run_hour_worker(_tupla_mano(**tupla))
    assert fuera.retirados == [0] and fuera.retiros_reposo == 1


def test_s2_por_el_motor_nadie_se_retira():
    """Fable, sec. 7, prueba 9: la hora S2 (un vendedor en bolsa, piso 350, y
    otro en permuta, piso 693; dos compradores de techos 731 y 777) por
    `_run_hour_worker`. Con D62 el de permuta cobraba 552 y se retiraba."""
    res = _run_hour_worker(_tupla_mano(
        G=[3.0, 3.0, 0.0, 0.0], D=[1.0, 1.0, 3.0, 3.0], sids=[0, 1],
        bids=[2, 3], techo=np.array([731.0, 777.0]),
        piso_j=[350.0, 693.0]))
    assert res.motivo == "" and res.retirados == []
    assert res.retiros_reposo == 0
    assert res.piso_juego == 693.0 and res.presupuesto == pytest.approx(1447.0)
    assert np.allclose(res.pi_star, [723.5, 723.5])
    assert res.renta_inframarginal == pytest.approx(686.0)
    assert res.parte_juego == pytest.approx(122.0)


def test_el_vendedor_bajo_su_piso_sale_con_la_fila_en_cero_y_sigue_en_la_lista(
        monkeypatch):
    # El bloque de la participacion, ejercido con el piso minimo
    # (`_nucleo_con_piso_minimo`). Con los dos, el precio liquidado es 782,8
    # (COP/kWh): el piso 900 de sids[0] queda encima y se retira; sids[1]
    # (piso 300) se queda.
    h = _hora()
    assert len(h["sids"]) == 2, "esta prueba necesita dos vendedores"
    piso_j = np.array([900.0, 300.0])
    s, d = _netos(h)
    _nucleo_con_piso_minimo(monkeypatch)
    completo = motor.resuelve_reposo(s, d, h["b"][h["sids"]], PGS, piso_j)
    assert np.all(completo.s_despachado > 0.0)
    assert completo.p_u < piso_j[0]

    res = _run_hour_worker(_args32(h, "reposo", pi_gb_j=piso_j)
                           + DEFECTOS_REPOSO)
    assert res.motivo == ""
    assert res.retirados == [h["sids"][0]]
    # D67: el retiro se cuenta.
    assert res.retiros_reposo == 1
    # La trampa de H-43: el retirado sigue en la lista, con su fila en cero.
    assert res.seller_ids == h["sids"]
    assert np.all(res.P_star[0, :] == 0.0)
    # El conjunto reducido se resolvio con el nucleo.
    reducido = resuelve_reposo(s[[1]], d, h["b"][[h["sids"][1]]], PGS,
                               piso_j[[1]])
    assert np.array_equal(res.P_star[1:, :], reducido.P)
    assert np.array_equal(res.pi_star, reducido.p_liquidado)
    assert res.regimen == reducido.regimen
    assert res.presupuesto == reducido.S
    assert res.piso_juego == reducido.piso == 300.0
    assert res.parada_acoplado == "reposo"

    # Y lo mismo por `run_single_hour`, con el piso como matriz por agente.
    techo, piso = _cotas_por_agente(h, piso_sellers=piso_j)
    techo[:] = PGS
    ems = EMSP2P(_agentes(h), GridParams(PGS, PGB, techo, piso),
                 SolverParams(parallel=False, metodo="reposo"))
    una = ems.run_single_hour(h["k"], h["D"], h["G"])
    _igual_al_bit(una, res, ("P_star", "pi_star", "retirados", "seller_ids",
                             "regimen", "presupuesto", "captura",
                             "retiros_reposo"))


def test_la_recursion_conserva_la_via_y_las_opciones(monkeypatch):
    h = _hora()
    llamadas = []
    original = _nucleo_con_piso_minimo(monkeypatch)
    minimo = motor.resuelve_reposo

    def espia(*a, **kw):
        llamadas.append((len(a[0]), kw["modo_presupuesto"], kw["sigma"],
                         kw["regla_precio"], kw["despacho_vendedores"]))
        return minimo(*a, **kw)

    monkeypatch.setattr(motor, "resuelve_reposo", espia)
    opciones = ("sigma", 0.5, "puja", "costo")
    res = _run_hour_worker(_args32(h, "reposo",
                                   pi_gb_j=np.array([1000.0, 300.0]))
                           + opciones)
    assert res.retirados == [h["sids"][0]] and res.retiros_reposo == 1
    assert llamadas == [(2,) + opciones, (1,) + opciones]
    assert original is resuelve_reposo


def test_la_captura_se_calcula_despues_de_la_participacion(monkeypatch):
    s, d = np.array([5.0, 5.0]), np.array([1.0, 5.0])
    b, techo, piso = (np.array([210.0, 225.0]), np.array([1250.0, 400.0]),
                      np.array([1200.0, 300.0]))
    # D63: la caminata cierra en 300, vende el 1 y el 0 no despacha. Nadie
    # cobra bajo su piso, el excedente del conjunto completo no es negativo y
    # la captura sale sin participacion que valga.
    vigente = resuelve_reposo(s, d, b, techo, piso)
    assert vigente.vendedores_no_despachados == (0,)
    assert vigente.excedente >= 0.0
    # Las cotas se miden sobre quien puede comerciar al final, de modo que el
    # vendedor que la caminata deja fuera entra con cantidad cero (revision
    # final, importante 1). Con el dentro, el peor usaria su piso de 1 200 y
    # daria -4 000 (COP), un mercado que no existe.
    optimo, peor = cotas_optimalidad([0.0, 5.0], d, techo, piso, vigente.E)
    assert (optimo, peor) == (1350.0, 500.0)
    assert cotas_optimalidad(s, d, techo, piso, vigente.E)[1] == -4000.0
    res = _ems_mano().run_single_hour(0, MANO["D"], MANO["G"])
    assert res.motivo == "" and res.retirados == [] and res.retiros_reposo == 0
    assert np.array_equal(res.P_star, vigente.P)
    assert res.excedente_optimo == optimo and res.excedente_peor == peor
    assert res.captura == captura(vigente.excedente, optimo)

    # Con el piso minimo (D62) el 0 despacha, cobra 387,5 < 1 200 y el motor
    # lo retira; la captura sale del conjunto final, el del vendedor 1.
    _nucleo_con_piso_minimo(monkeypatch)
    res = _ems_mano().run_single_hour(0, MANO["D"], MANO["G"])
    assert res.motivo == ""
    assert res.seller_ids == [0, 1] and res.buyer_ids == [2, 3]
    assert res.retirados == [0] and res.retiros_reposo == 1
    reducido = resuelve_reposo(s[[1]], d, b[[1]], techo, piso[[1]])
    opt_r, peor_r = cotas_optimalidad(s[[1]], d, techo, piso[[1]], reducido.E)
    assert np.array_equal(res.P_star[1:, :], reducido.P)
    assert res.excedente_optimo == opt_r and res.excedente_peor == peor_r
    assert res.captura == captura(reducido.excedente, opt_r)
    assert 0.0 <= res.captura <= 1.0 + 1e-9


def _comprueba_participacion(res, piso_por_agente):
    """La compuerta: ningun despachado bajo su piso y parte del vendedor no
    negativa, con el precio liquidado de la hora."""
    P = np.asarray(res.P_star, dtype=float)
    p = np.asarray(res.pi_star, dtype=float)
    ingreso_total, costo_piso = 0.0, 0.0
    for a, j in enumerate(res.seller_ids):
        colocado = float(P[a, :].sum())
        if colocado <= 1e-9:
            continue
        ingreso = float(np.dot(P[a, :], p))
        assert ingreso / colocado >= piso_por_agente[j] - 1e-9, (
            f"hora {res.k}: el vendedor {j} cobra {ingreso / colocado} bajo "
            f"su piso {piso_por_agente[j]}")
        ingreso_total += ingreso
        costo_piso += piso_por_agente[j] * colocado
    assert ingreso_total - costo_piso >= -1e-9 * max(1.0, costo_piso), (
        f"hora {res.k}: parte del vendedor negativa")


def test_compuerta_de_la_participacion_con_dos_despachados_de_pisos_distintos(
        monkeypatch):
    # (a) La hora armada a mano: con D63 nadie queda bajo su piso.
    res = _ems_mano().run_single_hour(0, MANO["D"], MANO["G"])
    assert res.retirados == []
    _comprueba_participacion(res, MANO["piso"][:, 0])

    # (b) La hora sintetica con pisos 700 y 300 y con 900 y 300: con D63 los
    # dos despachan y ninguno se retira.
    h = _hora()
    s, d = _netos(h)
    for piso_j in ([700.0, 300.0], [900.0, 300.0]):
        completo = resuelve_reposo(s, d, h["b"][h["sids"]], PGS, piso_j)
        assert np.all(completo.s_despachado > 0.0), piso_j
        res = _run_hour_worker(_args32(h, "reposo", pi_gb_j=np.array(piso_j))
                               + DEFECTOS_REPOSO)
        assert res.retirados == [] and res.retiros_reposo == 0
        piso_agente = np.full(h["D"].shape[0], np.inf)
        piso_agente[h["sids"]] = piso_j
        _comprueba_participacion(res, piso_agente)

    # (c) Con el piso minimo (D62), la de 900 retira, y tras la participacion
    # la compuerta tambien se cumple: el bloque sigue haciendo su trabajo.
    # (Solo la hora que retira: sin retiro, el nucleo sustituto mide el
    # excedente con el piso minimo, sobre el optimo verdadero, y la captura
    # lanzaria; es un artefacto de la sustitucion, no del motor.)
    _nucleo_con_piso_minimo(monkeypatch)
    piso_j = [900.0, 300.0]
    res = _run_hour_worker(_args32(h, "reposo", pi_gb_j=np.array(piso_j))
                           + DEFECTOS_REPOSO)
    assert res.retirados == [h["sids"][0]] and res.retiros_reposo == 1
    piso_agente = np.full(h["D"].shape[0], np.inf)
    piso_agente[h["sids"]] = piso_j
    _comprueba_participacion(res, piso_agente)


@pytest.mark.parametrize("despacho", ["piso", "costo", "llenado"])
def test_compuerta_de_la_participacion_sobre_horas_sinteticas_con_cotas_al_azar(
        despacho):
    # Muchas horas con techos y pisos por agente al azar, incluidos pisos por
    # encima de techos (D61) y vendedores sobrantes: ninguna hora falla, en
    # todas las que tienen mercado se cumple la compuerta y, con el piso del
    # vendedor marginal (D63), NINGUNA retira (D67). Con "costo" el lazo de
    # exclusion puede oscilar y la hora queda con su motivo (se cuenta).
    D, G = _caso(T=72, semilla=23)
    N, T = D.shape
    agentes = AgentParams(N=N, a=np.zeros(N),
                          b=np.array([225.0, 210.0, 225.0, 225.0, 210.0]),
                          c=np.zeros(N), lam=np.full(N, 100.0),
                          theta=np.full(N, 0.5), etha=np.full(N, 0.1))
    con_mercado = varios_pisos = oscilan = 0
    for semilla in range(4):
        rng = np.random.default_rng(semilla)
        techo = rng.uniform(650.0, 1250.0, (N, T))
        piso = rng.uniform(100.0, 1100.0, (N, T))
        ems = EMSP2P(agentes, GridParams(PGS, PGB, techo, piso),
                     SolverParams(parallel=False, metodo="reposo",
                                  despacho_vendedores=despacho))
        resultados, _, _ = ems.run(D, G)
        for r in resultados:
            if despacho == "costo" and "oscila" in r.motivo:
                oscilan += 1
                continue
            assert r.motivo == "", (semilla, r.k, r.motivo)
            assert r.retirados == [] and r.retiros_reposo == 0, (semilla, r.k)
            if r.P_star is None:
                continue
            con_mercado += 1
            colocan = np.asarray(r.P_star).sum(axis=1) > 1e-9
            varios_pisos += len({piso[j, r.k] for j, c in
                                 zip(r.seller_ids, colocan) if c}) > 1
            _comprueba_participacion(r, piso[:, r.k])
            assert 0.0 <= r.captura <= 1.0 + 1e-9
    # La muestra ejercita de verdad pisos distintos entre los que venden.
    assert con_mercado > 50 and varios_pisos > 20
    if despacho != "costo":
        assert oscilan == 0


def test_la_hora_sin_ganancia_posible_no_tiene_mercado_y_anota_su_causa():
    # D61: el piso de los dos vendedores (1 300) sobre el techo de todos los
    # compradores (1 250). Sin error, sin mercado, con la causa.
    h = _hora()
    res = _run_hour_worker(_args32(h, "reposo",
                                   pi_gb_j=np.array([1300.0, 1300.0]),
                                   pi_gb=1300.0) + DEFECTOS_REPOSO)
    assert res.motivo == "" and res.P_star is None
    assert res.regimen == "sin_ganancia"
    assert res.vendedores_excluidos == h["sids"]
    assert res.parada_acoplado == "reposo"


def _tupla_mano(G, D, sids, bids, techo, piso_j, b=225.0, a=0.0, **opciones):
    """La tupla de 36 campos de una hora armada a mano (via reposo)."""
    G = np.asarray(G, dtype=float)
    D = np.asarray(D, dtype=float)
    N = G.size
    piso_j = np.asarray(piso_j, dtype=float)
    cola = dict(zip(("modo_presupuesto", "sigma_nivel", "regla_precio",
                     "despacho_vendedores"), DEFECTOS_REPOSO))
    cola.update(opciones)
    return (0, G, D, G.copy(), list(sids), list(bids),
            np.full(N, float(a)) if np.ndim(a) == 0 else np.asarray(a, float),
            np.full(N, float(b)) if np.ndim(b) == 0 else np.asarray(b, float),
            np.full(N, 100.0), np.full(N, 0.5), np.full(N, 0.1),
            techo, float(np.min(piso_j)),
            0.001, 0.01, (0.0, 0.005), 150, 2, 1e-3, 10, "LSODA", "aggregate",
            "reposo", 0.05, piso_j, False, 1e-6, None, None, "factible",
            "precio", TOL_REPARTO,
            cola["modo_presupuesto"], cola["sigma_nivel"],
            cola["regla_precio"], cola["despacho_vendedores"])


# ─── las cotas de optimalidad (D55), sobre quien puede comerciar ───────────


@pytest.mark.parametrize("caso", ["vendedor_sin_ganancia",
                                  "comprador_bajo_el_piso"])
def test_las_cotas_se_miden_sobre_quien_puede_comerciar(caso):
    if caso == "vendedor_sin_ganancia":
        # El ejemplo de la revision: dos vendedores de 5 (kWh) con pisos 300 y
        # 1 300, y un comprador de 5 (kWh) con techo 1 250. El de piso 1 300
        # no puede venderle a nadie (D61). Sin ponerlo a cero, el peor reparto
        # le daria a el la energia: 5·1 250 - 5·1 300 = -250 (COP).
        G, D = [6.0, 6.0, 0.0], [1.0, 1.0, 5.0]
        sids, bids, techo, piso = [0, 1], [2], 1250.0, [300.0, 1300.0]
        esperado, peor_sin_arreglo = 4750.0, -250.0
    else:
        # Un vendedor de 5 (kWh) con piso 500 y dos compradores: 3 (kWh) con
        # techo 1 250 y 4 (kWh) con techo 450, bajo el piso del juego (D61
        # parcial). E = 3 (kWh). Sin ponerlo a cero, el peor le daria la
        # energia al de techo 450: 3·450 - 3·500 = -150 (COP).
        G, D = [6.0, 0.0, 0.0], [1.0, 3.0, 4.0]
        sids, bids, techo, piso = [0], [1, 2], np.array([1250.0, 450.0]), [500.0]
        esperado, peor_sin_arreglo = 2250.0, -150.0
    res = _run_hour_worker(_tupla_mano(G, D, sids, bids, techo, piso))
    assert res.motivo == "" and res.retirados == []
    if caso == "vendedor_sin_ganancia":
        assert res.vendedores_excluidos == [1]
    else:
        assert res.excluidos_bajo_piso == [2]
    s = np.array([G[j] - D[j] for j in sids])
    d = np.array([D[i] - G[i] for i in bids])
    rep = resuelve_reposo(s, d, np.full(len(sids), 225.0), techo, piso)
    # Lo que daria el nucleo con todos dentro: el optimo es el mismo, el peor
    # no.
    optimo_todos, peor_todos = cotas_optimalidad(s, d, techo, piso, rep.E)
    assert optimo_todos == pytest.approx(esperado)
    assert peor_todos == pytest.approx(peor_sin_arreglo)
    # El motor mide las dos cotas sobre quien puede comerciar.
    assert res.excedente_optimo == pytest.approx(esperado)
    assert res.excedente_peor == pytest.approx(esperado)
    # Con optimo igual al peor, la captura no tiene convencion aparte: es
    # excedente / optimo, y aqui el reposo alcanza el optimo.
    assert rep.excedente == pytest.approx(esperado)
    assert res.captura == captura(rep.excedente, esperado) == 1.0


def test_las_cotas_descuentan_a_los_que_la_caminata_deja_fuera():
    """Revision final, importante 1: las cotas se miden sobre quien puede
    comerciar al final, y eso incluye descontar a los NO DESPACHADOS de la
    caminata (D65), no solo a los de D61 y a los compradores bajo el piso.

    La hora: s = (2; 10; 10) (kWh) con pisos (100; 700; 750) y un comprador de
    5 (kWh) con techo 800. La caminata cierra en 700 (volumen 2 al nivel 100 y
    5 a los otros dos), despachan 2 el de 100 y 3 el de 700, y el de 750 queda
    fuera. El optimo no lo usaria nunca: 5·800 - (2·100 + 3·700) = 1 700
    (COP). El peor SI lo usaria, y mediria un mercado que no existe: con el de
    750 dentro da 5·800 - 5·750 = 250 (COP); descontandolo, 5·800 - 5·700 =
    500 (COP), que es el peor de verdad."""
    res = _run_hour_worker(_tupla_mano(
        G=[3.0, 11.0, 11.0, 0.0], D=[1.0, 1.0, 1.0, 5.0], sids=[0, 1, 2],
        bids=[3], techo=800.0, piso_j=[100.0, 700.0, 750.0]))
    assert res.motivo == "" and res.retirados == []
    assert res.piso_juego == 700.0
    assert res.vendedores_no_despachados == [2]
    assert np.allclose(res.P_star[:, 0], [2.0, 3.0, 0.0])
    assert res.excedente_optimo == pytest.approx(1700.0)
    assert res.excedente_peor == pytest.approx(500.0)
    # Lo que daria sin descontarlo, que es lo que se corrigio.
    s, d = np.array([2.0, 10.0, 10.0]), np.array([5.0])
    piso = np.array([100.0, 700.0, 750.0])
    optimo_todos, peor_todos = cotas_optimalidad(s, d, [800.0], piso, 5.0)
    assert optimo_todos == pytest.approx(1700.0)
    assert peor_todos == pytest.approx(250.0)
    # Y la captura sigue siendo la del excedente sobre el optimo.
    rep = resuelve_reposo(s, d, np.full(3, 225.0), [800.0], piso)
    assert res.captura == captura(rep.excedente, 1700.0)


def test_el_retiro_que_deja_la_hora_sin_mercado_nombra_a_sus_retirados(
        monkeypatch):
    """Revision final, importante 2: si la participacion retira a alguno y el
    conjunto reducido se queda sin mercado, la hora tiene que nombrar igual a
    sus retirados. Antes volvia antes de asignarlos: [D48] y D38 contaban el
    retiro, pero el almacen no anotaba a nadie como «retirado» y la compuerta
    `cero_retiros` salia en verde.

    Se fuerza con un nucleo que liquida por debajo del piso del primero en el
    conjunto completo y que declara «sin_ganancia» el conjunto reducido."""
    import dataclasses
    original = motor.resuelve_reposo

    def fabricada(s, *a, **kw):
        r = original(s, *a, **kw)
        if np.size(s) > 1:      # el conjunto completo: el de piso 700 cobra
            return dataclasses.replace(                      # menos que su piso
                r, p_liquidado=np.full_like(r.p_liquidado, 500.0))
        return dataclasses.replace(r, regimen="sin_ganancia")

    monkeypatch.setattr(motor, "resuelve_reposo", fabricada)
    res = _run_hour_worker(_tupla_mano(
        G=[3.0, 3.0, 0.0], D=[1.0, 1.0, 5.0], sids=[0, 1], bids=[2],
        techo=800.0, piso_j=[700.0, 300.0]))
    assert res.P_star is None and res.motivo == ""
    assert res.retiros_reposo == 1
    assert res.retirados == [0]
    assert res.regimen == "sin_ganancia"
    # Y el resumen la cuenta como hora que perdio el mercado, con su energia
    # POSIBLE, fuera de la transada (revision final, menor 1).
    import main_simulation as ms
    piso = np.array([700.0, 300.0, 0.0])
    resumen = ms.resumen_reposo([res], np.full(3, 800.0), piso=piso)
    assert resumen["sin_mercado_tras_retiro"] == [1, pytest.approx(4.0)]
    assert resumen["transada"] == 0.0
    assert resumen["retiros_reposo"] == 1 and resumen["retiros"] == 1
    linea = ms.linea_resumen_reposo(resumen)
    assert ("horas que perdieron el mercado tras un retiro: 1 h (4.00 kWh "
            "posibles, sin transar)") in linea
    assert "en las horas SIN MERCADO, la energia POSIBLE, no transada" in linea
    assert ms.salida_d38([res], "reposo")[0] == 3


def test_con_retiro_las_cotas_salen_del_conjunto_reducido_con_el_mismo_criterio(
        monkeypatch):
    # La hora armada a mano con el piso minimo: tras retirar al vendedor 0,
    # las cotas son las del vendedor 1 solo, con los mismos ceros de D61
    # (ninguno aqui).
    _nucleo_con_piso_minimo(monkeypatch)
    res = _ems_mano().run_single_hour(0, MANO["D"], MANO["G"])
    assert res.retirados == [0]
    d = np.array([1.0, 5.0])
    techo = np.array([1250.0, 400.0])
    reducido = resuelve_reposo([5.0], d, [225.0], techo, [300.0])
    optimo, peor = cotas_optimalidad([5.0], d, techo, [300.0], reducido.E)
    assert (res.excedente_optimo, res.excedente_peor) == (optimo, peor)


def test_con_retiro_y_excluidos_en_la_vuelta_reducida_el_peor_es_de_quien_comercia(
        monkeypatch):
    # La hora armada a mano (MANO) con dos agentes mas: el vendedor 4 (5 (kWh),
    # piso 1 300, sobre el techo de todos: D61) y el comprador 5 (2 (kWh),
    # techo 250, bajo el piso del juego: D61 parcial). Con el piso minimo, el
    # vendedor 0 se retira igual que en MANO, y en la vuelta reducida, con los
    # vendedores 1 y 4, siguen fuera el 4 y el 5.
    _nucleo_con_piso_minimo(monkeypatch)
    G = [6.0, 6.0, 0.0, 0.0, 6.0, 0.0]
    D = [1.0, 1.0, 1.0, 5.0, 1.0, 2.0]
    techo = np.array([1250.0, 400.0, 250.0])
    b = [210.0, 225.0, 225.0, 225.0, 225.0, 225.0]
    res = _run_hour_worker(_tupla_mano(G, D, sids=[0, 1, 4], bids=[2, 3, 5],
                                       techo=techo,
                                       piso_j=[1200.0, 300.0, 1300.0], b=b))
    assert res.motivo == ""
    assert res.retirados == [0] and res.retiros_reposo == 1
    assert res.vendedores_excluidos == [4]
    assert res.excluidos_bajo_piso == [5]
    # Las cotas del conjunto reducido (vendedores 1 y 4), sobre quien puede
    # comerciar: el 4 y el 5 con cantidad cero.
    s_red, d = np.array([5.0, 5.0]), np.array([1.0, 5.0, 2.0])
    piso_red = np.array([300.0, 1300.0])
    reducido = resuelve_reposo(s_red, d, [225.0, 225.0], techo, piso_red)
    assert reducido.E == 5.0
    optimo, peor = cotas_optimalidad([5.0, 0.0], [1.0, 5.0, 0.0], techo,
                                     piso_red, reducido.E)
    assert (optimo, peor) == (1350.0, 500.0)
    assert res.excedente_optimo == optimo
    assert res.excedente_peor == peor
    # Con los excluidos dentro, el peor usaria primero el piso 1 300 y el
    # techo 250: -4 800 (COP), un mercado que no existe.
    _, peor_todos = cotas_optimalidad(s_red, d, techo, piso_red, reducido.E)
    assert peor_todos == -4800.0
    # Con el nucleo vigente (D63) la misma hora no retira a nadie: la
    # caminata deja al 0 sin despachar y el 4 sigue fuera por D61.
    monkeypatch.undo()
    vigente = _run_hour_worker(_tupla_mano(
        G, D, sids=[0, 1, 4], bids=[2, 3, 5], techo=techo,
        piso_j=[1200.0, 300.0, 1300.0], b=b))
    assert vigente.retirados == [] and vigente.retiros_reposo == 0
    assert vigente.vendedores_excluidos == [4]
    assert vigente.vendedores_no_despachados == [0]


# ─── el piso del vendedor marginal en el motor (D63 a D67) ────────────────


def test_el_piso_del_juego_es_el_del_marginal_y_nadie_se_retira(monkeypatch):
    """Sustituye a la prueba de D62 del piso tras un retiro. Tres vendedores
    de 5 (kWh): C (b = 200, piso 1 000), A (b = 210, piso 500) y D (b = 225,
    piso 200); un comprador de 8 (kWh), techo 1 200.

    Con D62 despachaban C y A por merito, el piso del juego era 500, C se
    retiraba, despues A, y quedaba D solo: 5 de 8 (kWh). Con D63 la caminata
    cierra en 500 (volumen 5 al nivel 200 y 8 al nivel 500): despachan D (5) y
    A (3) al piso marginal, 500; C no despacha. Nadie se retira, el nucleo se
    llama una vez y D cobra su renta, (500 - 200)·5. Con "costo" despachan C y
    A, el marginal es C y el piso 1 000: tampoco retira."""
    pisos = []
    original = motor.resuelve_reposo

    def espia(*a, **kw):
        r = original(*a, **kw)
        pisos.append(r.piso)
        return r

    monkeypatch.setattr(motor, "resuelve_reposo", espia)
    tupla = dict(G=[6.0, 6.0, 6.0, 0.0], D=[1.0, 1.0, 1.0, 8.0],
                 sids=[0, 1, 2], bids=[3], techo=1200.0,
                 piso_j=[1000.0, 500.0, 200.0],
                 b=[200.0, 210.0, 225.0, 225.0])
    res = _run_hour_worker(_tupla_mano(**tupla))
    assert res.motivo == ""
    assert pisos == [500.0]
    assert res.retirados == [] and res.retiros_reposo == 0
    assert res.piso_juego == res.piso_marginal == 500.0
    assert res.presupuesto == 500.0 and np.array_equal(res.pi_star, [500.0])
    assert np.allclose(res.P_star[:, 0], [0.0, 3.0, 5.0])
    assert res.vendedores_no_despachados == [0]
    assert res.orden_merito == [2, 1, 0]
    assert res.renta_inframarginal == pytest.approx(1500.0)
    assert res.parte_juego == pytest.approx(0.0, abs=1e-9)

    pisos.clear()
    rc = _run_hour_worker(_tupla_mano(**tupla, despacho_vendedores="costo"))
    assert pisos == [1000.0] and rc.retirados == []
    assert np.allclose(rc.P_star[:, 0], [5.0, 3.0, 0.0])
    assert rc.renta_inframarginal == pytest.approx(1500.0)


def test_el_resumen_mide_la_energia_ofrecida_y_comerciable_de_los_retirados(
        monkeypatch):
    import main_simulation as ms
    # La hora de la prueba anterior con el piso minimo, que retira a C y A,
    # con 5 (kWh) de excedente neto cada uno: 10 (kWh) ofrecidos que no se
    # transaron. D vende 5 y el comprador (techo 1 200) queda con 8 - 5 = 3
    # (kWh) sin cubrir. C (piso 1 000 < 1 200) toma primero, por ser el de piso
    # mas alto, los 3 (kWh); a A (piso 500) no le queda deficit. Comerciables:
    # 3.
    _nucleo_con_piso_minimo(monkeypatch)
    piso = np.array([1000.0, 500.0, 200.0, 0.0])
    res = _run_hour_worker(_tupla_mano(
        G=[6.0, 6.0, 6.0, 0.0], D=[1.0, 1.0, 1.0, 8.0], sids=[0, 1, 2],
        bids=[3], techo=1200.0, piso_j=piso[:3],
        b=[200.0, 210.0, 225.0, 225.0]))
    assert res.retirados == [0, 1] and res.retiros_reposo == 2
    techo = np.full(4, 1200.0)
    resumen = ms.resumen_reposo([res], techo, piso=piso)
    assert resumen["retiros"] == 2 and resumen["horas_retiro"] == 1
    assert resumen["retiros_reposo"] == 2
    assert resumen["retirada_ofrecida"] == 10.0
    assert resumen["retirada_comerciable"] == 3.0
    assert resumen["transada"] == 5.0
    linea = ms.linea_resumen_reposo(resumen)
    assert ("10.00 kWh ofrecidos por los retirados (su excedente neto, sin "
            "transar), de los que 3.00 kWh eran comerciables") in linea
    assert "retiros de la via por reposo: 2, debe ser 0 (D67)" in linea
    # Si el comprador no acepta el piso de ninguno (techo 450 < 500 y 1 000),
    # nada es comerciable. Y con el paso de quince minutos, energia por 0,25.
    resumen = ms.resumen_reposo([res], np.full(4, 450.0), piso=piso)
    assert resumen["retirada_comerciable"] == 0.0
    resumen = ms.resumen_reposo([res], techo, dt=0.25, piso=piso)
    assert resumen["retirada_ofrecida"] == 2.5
    assert resumen["retirada_comerciable"] == 0.75
    # Con retirados y sin el piso de cada vendedor, en voz alta.
    with pytest.raises(ValueError, match="piso de cada vendedor"):
        ms.resumen_reposo([res], techo)


def test_la_hora_en_que_se_retiran_todos_nombra_a_sus_retirados(monkeypatch):
    # D67: si la participacion retirara a TODOS por la via del reposo, la hora
    # queda sin mercado, pero nombra a los retirados y los cuenta, para que el
    # almacen y la compuerta de cero retiros los vean. Se fuerza con un nucleo
    # que liquida a 100 (COP/kWh), bajo el piso de los dos.
    import dataclasses
    original = motor.resuelve_reposo

    def barato(*a, **kw):
        r = original(*a, **kw)
        return dataclasses.replace(r, p_liquidado=np.full_like(
            r.p_liquidado, 100.0))

    monkeypatch.setattr(motor, "resuelve_reposo", barato)
    res = _run_hour_worker(_tupla_mano(
        G=[3.0, 3.0, 0.0], D=[1.0, 1.0, 5.0], sids=[0, 1], bids=[2],
        techo=1000.0, piso_j=[300.0, 400.0]))
    assert res.P_star is None and res.motivo == ""
    assert res.retirados == [0, 1] and res.retiros_reposo == 2
    import main_simulation as ms
    assert ms.cuenta_retiros_reposo([res]) == 2


@pytest.mark.parametrize("despacho", ["piso", "costo", "llenado"])
def test_d67_ningun_retiro_en_horas_al_azar_con_las_tres_opciones(
        monkeypatch, despacho):
    # Sustituye a la prueba de D62 de que el piso nunca sube tras un retiro:
    # con el piso del vendedor marginal no hay retiro que mirar. En 1 500
    # horas al azar por opcion, con pisos y techos que se cruzan, el nucleo se
    # llama UNA vez por hora (sin vuelta reducida), nadie se retira y
    # `retiros_reposo` queda en 0. Con "costo" el lazo puede oscilar y la
    # hora queda con su motivo, en voz alta; se cuenta aparte.
    llamadas = []
    original = motor.resuelve_reposo

    def espia(*a, **kw):
        llamadas.append(1)
        return original(*a, **kw)

    monkeypatch.setattr(motor, "resuelve_reposo", espia)
    rng = np.random.default_rng(11)
    con_mercado = oscilan = 0
    for _ in range(1500):
        J, I = int(rng.integers(2, 5)), int(rng.integers(1, 5))
        G = np.concatenate([rng.uniform(1.0, 10.0, J), np.zeros(I)])
        D = np.concatenate([rng.uniform(0.0, 0.9, J) * G[:J],
                            rng.uniform(0.5, 10.0, I)])
        llamadas.clear()
        res = _run_hour_worker(_tupla_mano(
            G, D, range(J), range(J, J + I), rng.uniform(500.0, 1300.0, I),
            rng.uniform(100.0, 1200.0, J),
            b=rng.choice([200.0, 210.0, 225.0, 240.0], J + I),
            despacho_vendedores=despacho))
        if despacho == "costo" and "oscila" in res.motivo:
            oscilan += 1
            continue
        assert res.motivo == ""
        assert len(llamadas) == 1
        assert res.retirados == [] and res.retiros_reposo == 0
        con_mercado += res.P_star is not None
    assert con_mercado > 1000
    if despacho != "costo":
        assert oscilan == 0


# ─── las otras vias no cambian ─────────────────────────────────────────────


@pytest.mark.parametrize("metodo", ["alternado", "acoplado"])
@pytest.mark.parametrize("pi_gb_j", [None, PISO_H43], ids=["sin_piso",
                                                          "con_h43"])
def test_las_otras_vias_dan_lo_mismo_con_la_tupla_de_32_y_la_de_36(
        metodo, pi_gb_j):
    h = _hora()
    viejo = _run_hour_worker(_args32(h, metodo, pi_gb_j=pi_gb_j))
    nuevo = _run_hour_worker(_args32(h, metodo, pi_gb_j=pi_gb_j)
                             + DEFECTOS_REPOSO)
    # Las opciones del reposo son inertes fuera de su via.
    otras = _run_hour_worker(_args32(h, metodo, pi_gb_j=pi_gb_j)
                             + ("c136", None, "puja", "llenado"))
    # (Por la alternada con PISO_H43 la hora queda sin mercado: se retiran los
    # dos. La comparacion vale igual, campo por campo.)
    if pi_gb_j is None or metodo == "acoplado":
        assert viejo.P_star is not None
    for r in (nuevo, otras):
        _igual_al_bit(viejo, r, CAMPOS_DE_SIEMPRE)
    # Y los campos del reposo quedan en sus valores neutros.
    for r in (viejo, nuevo, otras):
        assert r.regimen == "" and r.pi_reposo is None
        assert r.presupuesto == r.precio_uniforme == r.captura == 0.0
        assert r.excluidos == [] and r.orden_merito == []
        assert r.n_soluciones == 0


def test_la_tupla_de_32_campos_y_la_de_36_dan_lo_mismo_por_la_via_del_reposo():
    # Una tupla de 32 campos con metodo "reposo" (que no deberia existir antes
    # de D48, pero puede armarse) toma los defectos de produccion.
    h = _hora()
    a = _run_hour_worker(_args32(h, "reposo", pi_gb_j=PISO_H43))
    b = _run_hour_worker(_args32(h, "reposo", pi_gb_j=PISO_H43)
                         + DEFECTOS_REPOSO)
    _igual_al_bit(a, b, ("P_star", "pi_star", "retirados") + CAMPOS_REPOSO)


# La identidad al bit INDEPENDIENTE del codigo nuevo. Estos literales se
# calcularon con el CODIGO BASE de la tarea 2, el commit a392cbd (HEAD al
# empezar), extraido de solo lectura con `git archive a392cbd core data | tar
# -x` a una carpeta aparte, con el guion `tests/literales/literales_base.py`
# (ver `tests/literales/README.md`), sobre la hora `_hora()` y la tupla de 32
# campos de `_args32`, en Windows con Python 3.13.7, numpy 2.4.4 y scipy
# 1.17.1. Las entradas se fijan con su huella, que se comprueba siempre.
#
# CUANDO CORRE. El acoplado y la alternada integran con LSODA, cuyo resultado
# al bit depende de la plataforma y de numpy y scipy (H-84), no del parche de
# Python. En Windows con las versiones de numpy y scipy de
# `requirements-lock.txt` la prueba CORRE, y si los literales no coinciden
# FALLA: o cambio una via que no debia, o cambio el entorno fijado y hay que
# regenerarlos. Fuera de ese entorno se salta, con el motivo.
HUELLA_BASE = "d035ddb833b066fd"
ENTORNO_BASE = ("Windows", "3.13.7", "2.4.4", "1.17.1")


def _versiones_del_lock() -> dict:
    """Las versiones de numpy y scipy fijadas en `requirements-lock.txt`.
    Si falta alguna, KeyError: el entorno fijado tiene que poder leerse."""
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
ESCALARES_BASE = ("SC", "SS", "IE", "PS", "PSR", "Wj_total", "Wi_total",
                  "norm_rel_final", "horizonte_usado", "residuo_reparto")
BASE_BIT = {
    ("alternado", "sin_piso"): dict(
        forma=(2, 3),
        P_star=["0x1.4b9dab41c083cp+1", "0x1.61a60d31aeb85p-4",
                "0x1.4ba8ada6eccd4p+1", "0x1.47615aa1024b7p-3",
                "0x1.5d21b1b0c786ap-8", "0x1.476c39069da56p-3"],
        pi_star=["0x1.c800000000000p+6", "0x1.3880000000000p+10",
                 "0x1.c800000000000p+6"],
        escalares=["0x1.fffffffffffffp-1", "0x1.caf87dd688070p-1",
                   "0x1.ef37ba3895d6fp-1", "0x1.8971c4be1a880p+6",
                   "0x1.a38ed0795e015p+0", "-0x1.6520ba5da8785p+9",
                   "0x1.2945f6767a4fcp+10", "0x1.c6122058fc133p-14",
                   "0x0.0p+0", "0x0.0p+0"],
        retirados=[], iters_used=2, evaluaciones=0,
        motivo="", parada_acoplado=""),
    ("alternado", "con_h43"): dict(
        P_star=None, pi_star=None,
        escalares=["0x0.0p+0"] * 10,
        retirados=[], iters_used=0, evaluaciones=0,
        motivo="", parada_acoplado=""),
    ("acoplado", "sin_piso"): dict(
        forma=(2, 3),
        P_star=["0x1.0b32a6a18d6d8p+1", "0x1.00470b3c93d74p-4",
                "0x1.8f1eab3301d86p+1", "0x1.07c8f26a8a34cp-3",
                "0x1.fa0218a8ef5bep-9", "0x1.8a0598a466ab9p-3"],
        pi_star=["0x1.9adfc9dc6d7acp+9", "0x1.c75a9b410ad66p+9",
                 "0x1.7fc59ae287a65p+9"],
        escalares=["0x1.0000000000005p+0", "0x1.caf87dd68807bp-1",
                   "-0x1.88034c6ef0bcap-3", "0x1.436f5b1254fb3p+5",
                   "0x1.dc90a4edab04ep+5", "-0x1.64f5f45c81fa2p+9",
                   "0x1.c492b91b4483bp+8", "0x1.5c7101c02f0f3p-5",
                   "0x1.0624dd2f1a9fcp-9", "0x1.38d961264f706p-9"],
        retirados=[], iters_used=300, evaluaciones=3831,
        motivo="", parada_acoplado="una_vuelta"),
    ("acoplado", "con_h43"): dict(
        forma=(2, 3),
        P_star=["0x1.0b32a6a18d6d8p+1", "0x1.00470b3c93d74p-4",
                "0x1.8f1eab3301d86p+1", "0x1.07c8f26a8a34cp-3",
                "0x1.fa0218a8ef5bep-9", "0x1.8a0598a466ab9p-3"],
        pi_star=["0x1.9adfc9dc6d7acp+9", "0x1.c75a9b410ad66p+9",
                 "0x1.7fc59ae287a65p+9"],
        escalares=["0x1.0000000000005p+0", "0x1.caf87dd68807bp-1",
                   "0x1.8147007d67fcdp-2", "0x1.133fde187e4f6p+6",
                   "0x1.f300879e06c28p+4", "-0x1.64f5f45c81fa2p+9",
                   "0x1.c492b91b4483bp+8", "0x1.5c7101c02f0f3p-5",
                   "0x1.0624dd2f1a9fcp-9", "0x1.38d961264f706p-9"],
        retirados=[], iters_used=300, evaluaciones=3831,
        motivo="", parada_acoplado="una_vuelta"),
}


def _huella_hora(h):
    """La misma huella que `literales_base.py`: las entradas de la hora, los
    identificadores y las cotas de la tupla, en float64 e int64."""
    m = hashlib.sha256()
    for clave in ("g_klim", "d_k", "g_k", "a", "b", "lam", "theta", "etha"):
        m.update(np.ascontiguousarray(h[clave], dtype=np.float64).tobytes())
    m.update(np.array([h["k"]] + list(h["sids"]) + [-1] + list(h["bids"]),
                      dtype=np.int64).tobytes())
    m.update(np.array([PGS, PGB, T_ACO, *PISO_H43], dtype=np.float64)
             .tobytes())
    return m.hexdigest()[:16]


def test_la_hora_de_los_literales_base_es_la_misma():
    assert _huella_hora(_hora()) == HUELLA_BASE


@pytest.mark.skipif(
    not EN_EL_ENTORNO_DEL_LOCK,
    reason=f"los literales del codigo base valen en Windows con numpy "
           f"{LOCK['numpy']} y scipy {LOCK['scipy']} (requirements-lock.txt; "
           f"se calcularon en {ENTORNO_BASE}); LSODA no es identico al bit "
           f"entre plataformas (H-84). Para este entorno, regenerarlos con "
           f"tests/literales/literales_base.py")
@pytest.mark.parametrize("clave", sorted(BASE_BIT))
def test_las_otras_vias_dan_al_bit_lo_del_codigo_base(clave):
    metodo, nombre = clave
    esperado = BASE_BIT[clave]
    h = _hora()
    piso = None if nombre == "sin_piso" else PISO_H43
    for tupla in (_args32(h, metodo, pi_gb_j=piso),
                  _args32(h, metodo, pi_gb_j=piso) + DEFECTOS_REPOSO):
        r = _run_hour_worker(tupla)
        if esperado["P_star"] is None:
            assert r.P_star is None and r.pi_star is None
        else:
            assert np.shape(r.P_star) == esperado["forma"]
            assert [float(v).hex() for v in np.ravel(r.P_star)] == \
                esperado["P_star"]
            assert [float(v).hex() for v in r.pi_star] == esperado["pi_star"]
        assert [float(getattr(r, c)).hex() for c in ESCALARES_BASE] == \
            esperado["escalares"]
        assert list(r.retirados) == esperado["retirados"]
        assert r.iters_used == esperado["iters_used"]
        assert r.evaluaciones == esperado["evaluaciones"]
        assert r.motivo == esperado["motivo"]
        assert r.parada_acoplado == esperado["parada_acoplado"]


# ─── lo desconocido se rechaza ─────────────────────────────────────────────


@pytest.mark.parametrize("kw", [
    dict(metodo="reposos"),
    dict(modo_presupuesto="sigmas"),
    dict(regla_precio="subasta"),
    dict(despacho_vendedores="orden"),
    dict(sigma_nivel=1.5),
    dict(sigma_nivel=-0.1),
    dict(sigma_nivel=float("nan")),
    dict(sigma_nivel=True),
    dict(sigma_nivel="0.5"),
    dict(sigma_nivel=0.5, modo_presupuesto="c136"),
])
def test_solver_params_rechaza_lo_desconocido(kw):
    with pytest.raises(ValueError):
        SolverParams(**kw)


def test_solver_params_acepta_los_valores_validos():
    for kw in (dict(metodo="reposo"), dict(sigma_nivel=0.0),
               dict(sigma_nivel=1), dict(modo_presupuesto="c136"),
               dict(modo_presupuesto="algoritmo3", regla_precio="puja",
                    despacho_vendedores="llenado")):
        SolverParams(**kw)
    sv = SolverParams()
    assert (sv.modo_presupuesto, sv.sigma_nivel, sv.regla_precio,
            sv.despacho_vendedores) == DEFECTOS_REPOSO
    assert sv.despacho_vendedores == "piso"
    # El defecto de la clase no cambia: la via de produccion la decide la
    # linea de ordenes.
    assert sv.metodo == "alternado"


def test_merito_es_alias_de_costo_con_aviso(monkeypatch):
    """D64, decision del controlador: "merito" (el nombre viejo del despacho
    por costo) se acepta como alias de "costo", con un aviso, en
    `SolverParams` y en la tupla del trabajador armada a mano, para no romper
    ordenes ni tuplas guardadas. Da exactamente lo mismo que "costo"."""
    with pytest.warns(UserWarning, match="nombre viejo"):
        sv = SolverParams(despacho_vendedores="merito")
    assert sv.despacho_vendedores == "costo"
    tupla = dict(G=[6.0, 6.0, 6.0, 0.0], D=[1.0, 1.0, 1.0, 8.0],
                 sids=[0, 1, 2], bids=[3], techo=1200.0,
                 piso_j=[1000.0, 500.0, 200.0],
                 b=[200.0, 210.0, 225.0, 225.0])
    vistos = []
    original = motor.resuelve_reposo

    def espia(*a, **kw):
        vistos.append(kw["despacho_vendedores"])
        return original(*a, **kw)

    monkeypatch.setattr(motor, "resuelve_reposo", espia)
    with pytest.warns(UserWarning, match="se usa 'costo'"):
        viejo = _run_hour_worker(_tupla_mano(**tupla,
                                             despacho_vendedores="merito"))
    costo = _run_hour_worker(_tupla_mano(**tupla, despacho_vendedores="costo"))
    assert vistos == ["costo", "costo"]
    _igual_al_bit(viejo, costo, CAMPOS_DE_SIEMPRE + CAMPOS_REPOSO)
    # Y con "piso" la hora es otra: el marginal es A (500), no C (1 000).
    piso = _run_hour_worker(_tupla_mano(**tupla))
    assert viejo.piso_juego == 1000.0 and piso.piso_juego == 500.0
    # Un valor desconocido sigue rechazandose, sin alias.
    with pytest.raises(ValueError, match="merito"):
        SolverParams(despacho_vendedores="meritos")


def test_la_tupla_de_32_campos_rellena_el_despacho_por_piso():
    # D64: el shim de 32 a 36 campos rellena "piso" (antes "merito"). La
    # hora de C, A y D: por piso el marginal es A (500); por costo seria C.
    G, D = [6.0, 6.0, 6.0, 0.0], [1.0, 1.0, 1.0, 8.0]
    t36 = _tupla_mano(G, D, [0, 1, 2], [3], 1200.0, [1000.0, 500.0, 200.0],
                      b=[200.0, 210.0, 225.0, 225.0])
    assert len(t36) == 36 and t36[35] == "piso"
    r32 = _run_hour_worker(t36[:32])
    r36 = _run_hour_worker(t36)
    _igual_al_bit(r32, r36, CAMPOS_DE_SIEMPRE + CAMPOS_REPOSO)
    assert r32.piso_juego == 500.0


@pytest.mark.parametrize("cola", [
    ("sigmas", None, "uniforme", "piso"),
    ("sigma", 2.0, "uniforme", "piso"),
    ("c136", 0.5, "uniforme", "piso"),
    ("sigma", None, "subasta", "piso"),
    ("sigma", None, "uniforme", "orden"),
])
def test_la_tupla_rechaza_lo_desconocido_aun_sin_mercado(cola):
    h = _hora()
    for sids in (h["sids"], []):
        hh = dict(h, sids=sids)
        with pytest.raises(ValueError):
            _run_hour_worker(_args32(hh, "reposo") + cola)


def test_la_tupla_rechaza_una_via_desconocida():
    with pytest.raises(ValueError, match="metodo"):
        _run_hour_worker(_args32(_hora(), "acoplada") + DEFECTOS_REPOSO)


# ─── el camino de excepcion del reposo (C-190, D38) ────────────────────────


# Una hora de H-32 con el presupuesto "c136": un vendedor de 5 (kWh) y dos
# compradores de 1 y 2 (kWh), techo 700 y piso 400. El arranque comun,
# 1 400/3 = 466,7 (COP/kWh), cae dentro de las dos bandas, el interruptor no
# dispara y S = 700 < 2·400: el nucleo lanza.
HORA_H32 = dict(G=[6.0, 0.0, 0.0], D=[1.0, 1.0, 2.0], sids=[0], bids=[1, 2],
                techo=700.0, piso_j=[400.0])


def test_el_valueerror_del_nucleo_deja_motivo_y_cuenta_para_el_codigo_3():
    import main_simulation as ms
    with pytest.raises(ValueError, match="H-32"):
        resuelve_reposo([5.0], [1.0, 2.0], [225.0], 700.0, [400.0],
                        modo_presupuesto="c136")
    res = _run_hour_worker(_tupla_mano(**HORA_H32,
                                       modo_presupuesto="c136"))
    assert res.motivo.startswith(f"{PREFIJO_EXCEPCION_REPOSO}: ValueError")
    assert "H-32" in res.motivo
    assert res.P_star is None and res.pi_star is None
    assert res.regimen == "" and res.parada_acoplado == "reposo"
    # Cuenta como hora de mercado con excepcion, y el codigo de salida es 3.
    cuenta = ms.cuenta_para_salida([res])
    assert cuenta == (1, 0, 1, 0)
    assert ms.codigo_de_salida(*cuenta) == 3
    # Y el resumen la cuenta aparte, fuera de los regimenes.
    resumen = ms.resumen_reposo([res], 700.0)
    assert resumen["horas_excepcion"] == 1
    assert all(n == 0 for n, _ in resumen["regimenes"].values())
    # Con el presupuesto de produccion la misma hora resuelve.
    assert _run_hour_worker(_tupla_mano(**HORA_H32)).motivo == ""


def test_d38_un_retiro_por_la_via_del_reposo_da_codigo_3_citando_d67(
        monkeypatch):
    """D67 y D38: con `metodo="reposo"` y algun retiro, el codigo de salida es
    3, con una linea que cita D67. Las otras vias no cuentan `retiros_reposo`
    (no lo llenan). Sin retiros, 0, y la linea dice que deben ser 0."""
    import main_simulation as ms
    h = _hora()
    limpia = _run_hour_worker(_args32(h, "reposo",
                                      pi_gb_j=np.array([900.0, 300.0]))
                              + DEFECTOS_REPOSO)
    codigo, linea = ms.salida_d38([limpia], "reposo")
    assert codigo == 0
    assert linea.startswith("[D38] codigo de salida 0: ninguna hora con "
                            "excepcion")
    assert "0 retiros de vendedor por la via del reposo, que debe dar 0 " \
        "(D67)" in linea

    _nucleo_con_piso_minimo(monkeypatch)
    retiro = _run_hour_worker(_args32(h, "reposo",
                                      pi_gb_j=np.array([900.0, 300.0]))
                              + DEFECTOS_REPOSO)
    assert retiro.retiros_reposo == 1 and retiro.motivo == ""
    assert ms.cuenta_retiros_reposo([limpia, retiro]) == 1
    assert ms.cuenta_para_salida([limpia, retiro]) == (2, 0, 0, 0)
    assert ms.codigo_de_salida(2, 0, 0, 0) == 0
    assert ms.codigo_de_salida(2, 0, 0, 0, n_retiros_reposo=1) == 3
    codigo, linea = ms.salida_d38([limpia, retiro], "reposo")
    assert codigo == 3
    assert "la participacion retiro 1 vendedores por la via del reposo" in linea
    assert "un retiro es un hallazgo (D67)" in linea
    assert "Todas las salidas ya estan escritas" in linea
    # Por otra via el mismo resultado no cuenta: el campo es de la via.
    assert ms.salida_d38([limpia, retiro], "acoplado")[0] == 0
    with pytest.raises(ValueError):
        ms.codigo_de_salida(2, 0, 0, 0, n_retiros_reposo=-1)


def test_la_vuelta_reducida_que_revienta_sube_su_motivo(monkeypatch):
    # Con el piso minimo (D62), para que haya vuelta reducida: con D63 la hora
    # no retira a nadie.
    h = _hora()
    llamadas = []
    _nucleo_con_piso_minimo(monkeypatch)
    original = motor.resuelve_reposo

    def revienta_la_segunda(*a, **kw):
        llamadas.append(len(a[0]))
        if len(llamadas) == 2:
            raise ValueError("fabricada en la vuelta reducida")
        return original(*a, **kw)

    monkeypatch.setattr(motor, "resuelve_reposo", revienta_la_segunda)
    res = _run_hour_worker(_args32(h, "reposo",
                                   pi_gb_j=np.array([900.0, 300.0]))
                           + DEFECTOS_REPOSO)
    # El conjunto completo y el reducido, con un vendedor.
    assert llamadas == [2, 1]
    assert res.motivo == (f"{PREFIJO_EXCEPCION_REPOSO}: ValueError: "
                          f"fabricada en la vuelta reducida")
    assert res.P_star is None
    # Los campos del reposo son los de la vuelta que produjo el resultado,
    # la reducida, que no llego a tener regimen.
    assert res.regimen == ""


def test_un_costo_cuadratico_no_nulo_sale_por_c190():
    # CAL-32: el nucleo supone a_j = 0.
    res = _run_hour_worker(_tupla_mano(
        G=[6.0, 0.0], D=[1.0, 2.0], sids=[0], bids=[1], techo=1000.0,
        piso_j=[300.0], a=[2.17, 0.0]))
    assert res.motivo.startswith(f"{PREFIJO_EXCEPCION_REPOSO}: ValueError: "
                                 f"CAL-32")
    assert res.P_star is None
    # El a_j de un COMPRADOR no entra al reposo y no se objeta.
    res = _run_hour_worker(_tupla_mano(
        G=[6.0, 0.0], D=[1.0, 2.0], sids=[0], bids=[1], techo=1000.0,
        piso_j=[300.0], a=[0.0, 2.17]))
    assert res.motivo == "" and res.regimen == "un_comprador"


def test_main_rechaza_el_reposo_con_costo_cuadratico(tmp_path):
    import main_simulation as ms
    assert ms.error_costo_cuadratico("reposo", [0.0, 0.0]) is None
    assert ms.error_costo_cuadratico("acoplado", [2.17, 0.0]) is None
    assert "CAL-32" in ms.error_costo_cuadratico("reposo", [2.17, 0.0])
    # El caso sintetico del modelo base trae a no nulos.
    with pytest.raises(ValueError, match="CAL-32"):
        ms.main(use_real_data=False, run_analysis=False, metodo="reposo",
                out_dir=str(tmp_path))


def test_el_polvo_negativo_de_los_netos_se_lleva_a_cero():
    s, d = _entradas_reposo(np.zeros(2), [-TOL_NETO_REPOSO, -2e-9],
                            [-5e-10, 3.0])
    assert s.tolist() == [0.0, -2e-9]
    assert d.tolist() == [0.0, 3.0]
    # En el motor: un comprador con demanda 0 y generacion 5e-10 (kWh)
    # queda como comprador (`classify_agents`) con deficit -5e-10. Se lleva a
    # cero y la hora resuelve con el otro comprador.
    res = _run_hour_worker(_tupla_mano(
        G=[6.0, 0.0, 5e-10], D=[1.0, 3.0, 0.0], sids=[0], bids=[1, 2],
        techo=1000.0, piso_j=[300.0]))
    assert res.motivo == ""
    assert res.regimen == "un_comprador"
    assert res.P_star[0, 1] == 0.0 and res.P_star[0, 0] == 3.0


def test_un_neto_mas_negativo_que_el_polvo_sigue_lanzando():
    res = _run_hour_worker(_tupla_mano(
        G=[6.0, 0.0, 1e-8], D=[1.0, 3.0, 0.0], sids=[0], bids=[1, 2],
        techo=1000.0, piso_j=[300.0]))
    assert res.motivo.startswith(f"{PREFIJO_EXCEPCION_REPOSO}: ValueError")
    assert "negativas" in res.motivo
    assert res.P_star is None


# ─── la linea de ordenes ───────────────────────────────────────────────────


def _cli(*flags):
    """La linea de ordenes en un subproceso. SALVAGUARDA: `MTE_ROOT` apunta a
    una carpeta que no existe, de modo que si alguna validacion dejara pasar
    una llamada con `--data real`, el cargador fallaria al abrir la carpeta en
    vez de correr datos reales en esta maquina (regla principal de
    CLAUDE.md)."""
    entorno = dict(os.environ,
                   MTE_ROOT=str(RAIZ / "no_existe_carpeta_de_mediciones"))
    return subprocess.run([sys.executable, str(RAIZ / "main_simulation.py"),
                           *flags], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=str(RAIZ),
                          env=entorno, timeout=120)


def test_la_ayuda_muestra_las_opciones_nuevas():
    res = _cli("--help")
    assert res.returncode == 0, res.stderr
    for opcion in ("--metodo", "reposo", "--modo-presupuesto",
                   "--sigma-nivel", "--regla-precio",
                   "--despacho-vendedores"):
        assert opcion in res.stdout, opcion


@pytest.mark.parametrize("flags,mensaje", [
    (("--metodo", "reposos"), "invalid choice"),
    (("--regla-precio", "subasta"), "invalid choice"),
    (("--modo-presupuesto", "otro"), "invalid choice"),
    (("--despacho-vendedores", "orden"), "invalid choice"),
    # La sigma, con `--data real`: sin datos reales el rechazo de CAL-32 del
    # caso sintetico sale antes y la sigma no llega a validarse. Todas fallan
    # al validar los argumentos, antes de cargar ningun dato, y el mensaje que
    # se afirma es el del error, que la linea de uso de argparse no contiene.
    (("--data", "real", "--metodo", "reposo", "--sigma-nivel", "1.5"),
     "tiene que ser un numero finito entre 0 y 1 o la palabra 'base'"),
    (("--data", "real", "--metodo", "reposo", "--sigma-nivel", "nan"),
     "tiene que ser un numero finito entre 0 y 1 o la palabra 'base'"),
    (("--data", "real", "--metodo", "reposo", "--sigma-nivel", "tres"),
     "tiene que ser un numero entre 0 y 1 o la palabra 'base'"),
    (("--data", "real", "--metodo", "reposo", "--sigma-nivel", "0.5",
      "--modo-presupuesto", "c136"),
     "--sigma-nivel solo aplica a --modo-presupuesto sigma, no a c136"),
    # El GSA no usa la via por reposo, y lo dice (no el error de CAL-32).
    (("--gsa", "--metodo", "reposo"),
     "--gsa corre el analisis de sensibilidad global con su propio mercado"),
])
def test_un_valor_invalido_sale_con_error(flags, mensaje):
    res = _cli(*flags)
    assert res.returncode == 2, (res.returncode, res.stdout[-500:])
    assert mensaje in res.stderr, res.stderr[-800:]
    # El mensaje afirmado no es la linea de uso, y no se cargo nada.
    assert mensaje not in res.stderr.split("error:")[0]
    assert "Cargando datos" not in res.stdout
    assert "CAL-32" not in res.stderr


def test_con_datos_reales_y_sin_metodo_la_via_es_reposo():
    import main_simulation as ms
    metodo, aviso = ms.resuelve_metodo(None, datos_reales=True)
    assert metodo == "reposo" and "REPOSO" in aviso
    # Con --metodo explicito no cambia nada, y sin aviso.
    for pedido in ("acoplado", "alternado", "reposo"):
        assert ms.resuelve_metodo(pedido, datos_reales=True) == (pedido, None)
    # El caso sintetico y el GSA conservan la alternada.
    assert ms.resuelve_metodo(None, datos_reales=False) == ("alternado", None)
    assert ms.resuelve_metodo(None, datos_reales=True, gsa=True) == (
        "alternado", None)
    with pytest.raises(ValueError):
        ms.resuelve_metodo("reposos", datos_reales=True)


# ─── la linea [D48] y el almacen ───────────────────────────────────────────


def test_el_resumen_cuenta_la_hora_de_un_solo_comprador_y_la_sin_ganancia():
    import main_simulation as ms
    # Un vendedor (5 (kWh) de excedente, piso 300) y un comprador (2 (kWh)
    # de deficit, techo 1 000): D54, paga el piso.
    uno = _run_hour_worker((
        0, np.array([6.0, 0.0]), np.array([1.0, 2.0]), np.array([6.0, 0.0]),
        [0], [1], np.zeros(2), np.full(2, 225.0), np.full(2, 100.0),
        np.full(2, 0.5), np.full(2, 0.1), 1000.0, 300.0,
        0.001, 0.01, (0.0, 0.005), 150, 2, 1e-3, 10, "LSODA", "aggregate",
        "reposo", 0.05, None, False, 1e-6, None, None, "factible", "precio",
        TOL_REPARTO) + DEFECTOS_REPOSO)
    assert uno.regimen == "un_comprador"
    assert np.array_equal(uno.pi_star, [300.0])
    h = _hora()
    sin = _run_hour_worker(_args32(h, "reposo",
                                   pi_gb_j=np.array([1300.0, 1300.0]),
                                   pi_gb=1300.0) + DEFECTOS_REPOSO)
    sin.k = 1
    assert sin.regimen == "sin_ganancia"
    s, d = _netos(h)
    resumen = ms.resumen_reposo([uno, sin], techo=np.array([1000.0, 1000.0,
                                                           PGS, PGS, PGS]))
    assert resumen["regimenes"]["un_comprador"] == [1, 2.0]
    assert resumen["un_comprador"] == 2.0
    assert resumen["al_piso"] == 2.0 and resumen["al_techo"] == 0.0
    assert resumen["topada_reposo"] == 0.0
    assert resumen["transada"] == 2.0
    assert resumen["horas_excepcion"] == 0
    horas, energia = resumen["regimenes"]["sin_ganancia"]
    assert horas == 1 and energia == pytest.approx(min(s.sum(), d.sum()))
    assert resumen["vendedores_excluidos"][0] == 1
    assert resumen["vendedores_excluidos"][1] == pytest.approx(s.sum())
    linea = ms.linea_resumen_reposo(resumen)
    assert linea.startswith("Horas por regimen: interiores 0 h")
    assert "sin_ganancia 1 h" in linea and "un_comprador 1 h" in linea


def test_el_resumen_separa_lo_topado_en_el_reposo_de_lo_liquidado_al_techo():
    import dataclasses

    import main_simulation as ms
    h = _hora()
    res = _run_hour_worker(_args32(h, "reposo") + DEFECTOS_REPOSO)
    assert res.regimen == "topados"
    q = res.P_star.sum(axis=0)
    topados = (np.abs(res.pi_reposo - PGS) <= 1e-6) & (q > 0.0)
    assert topados.any() and res.precio_uniforme < PGS
    resumen = ms.resumen_reposo([res], PGS)
    # Topados en el reposo, pero liquidados al precio uniforme: ahorro no
    # nulo, nada al techo.
    assert resumen["topada_reposo"] == pytest.approx(float(q[topados].sum()))
    assert resumen["al_techo"] == 0.0
    linea = ms.linea_resumen_reposo(resumen)
    assert "energia liquidada al techo (ahorro cero) 0.00 kWh" in linea
    assert "energia topada en el reposo" in linea
    # Una hora con motivo no entra en ningun regimen, aunque traiga uno: la
    # cuenta [C-190], y aqui solo las horas con excepcion del reposo.
    rota = dataclasses.replace(res, motivo=f"{PREFIJO_EXCEPCION_REPOSO}: "
                                           f"ValueError: en las cotas")
    otra = dataclasses.replace(res, motivo="vencio el plazo por hora de 15 min")
    resumen = ms.resumen_reposo([rota, otra], PGS)
    assert resumen["horas_excepcion"] == 1
    assert resumen["regimenes"]["topados"] == [0, 0.0]
    assert resumen["topada_reposo"] == resumen["transada"] == 0.0


def _almacen_en_memoria(monkeypatch):
    """Sustituye el volcado a parquet por uno en memoria. La prueba mira el
    ESQUEMA de las tablas, no el formato, y el entorno de pruebas puede no
    traer el motor de parquet (en `.venv` no esta pyarrow)."""
    tablas = {}

    def vuelca(self, tabla):
        filas = self._buf[tabla]
        if not filas:
            return
        tablas.setdefault(tabla, []).append(pd.DataFrame(filas))
        self._partes[tabla] += 1
        self._buf[tabla] = []

    monkeypatch.setattr(almacen_mod, "_comprueba_motor",
                        lambda comprimir="zstd": None)
    monkeypatch.setattr(almacen_mod.Almacen, "_vuelca", vuelca)
    return tablas


COLUMNAS_HORAS = ("regimen", "presupuesto", "precio_comun", "precio_uniforme",
                  "piso_juego", "n_soluciones", "excedente_optimo",
                  "excedente_peor", "captura", "excluidos",
                  "excluidos_bajo_piso", "vendedores_excluidos",
                  "orden_merito",
                  # D63, D65 y D69 (tarea 5a)
                  "piso_marginal", "renta_inframarginal", "parte_juego",
                  "vendedores_no_despachados")


def _sintetico_con_a_cero(monkeypatch, ms):
    """El caso sintetico del modelo base con a = 0 (CAL-32), sin tocar los
    datos: se sustituye la funcion que `main` usa para leer los parametros.
    Con a = 0 el primer agente (b = 1 243,8 < techo 1 250) sigue generando."""
    original = ms.get_agent_params

    def con_a_cero():
        p = original()
        p["a"] = np.zeros_like(p["a"])
        return p

    monkeypatch.setattr(ms, "get_agent_params", con_a_cero)


@pytest.mark.parametrize("metodo", ["reposo", "alternado"])
def test_la_corrida_sintetica_escribe_la_linea_d48_y_las_columnas(
        metodo, monkeypatch, tmp_path, capsys):
    import main_simulation as ms
    tablas = _almacen_en_memoria(monkeypatch)
    if metodo == "reposo":
        _sintetico_con_a_cero(monkeypatch, ms)
    ms.main(use_real_data=False, run_analysis=False, metodo=metodo,
            out_dir=str(tmp_path / "salida"),
            almacen=str(tmp_path / "almacen"))
    salida = capsys.readouterr().out
    inicio = ("[D48] Mercado por reposo en forma cerrada: presupuesto sigma, "
              "sigma base ((I-1)/I), liquidacion uniforme, despacho piso")
    if metodo == "reposo":
        assert inicio in salida
        assert "[D48] Horas por regimen: interiores" in salida
        # D67 y D69: los retiros de la via, que deben ser 0, y la prima
        # descompuesta, en la linea final.
        assert "retiros de la via por reposo: 0, debe ser 0 (D67)" in salida
        assert ("prima de los vendedores descompuesta (D69): renta "
                "inframarginal") in salida
    else:
        assert "[D48]" not in salida
    horas = pd.concat(tablas["horas"], ignore_index=True)
    flujos = pd.concat(tablas["flujos"], ignore_index=True)
    # El esquema no depende de la via.
    for col in COLUMNAS_HORAS:
        assert col in horas.columns, col
    assert "precio_reposo" in flujos.columns
    resueltas = horas[horas["resuelta"] == True]  # noqa: E712
    assert len(resueltas) > 0
    if metodo == "reposo":
        assert set(resueltas["regimen"]) <= set(
            ms.resumen_reposo([], 0.0)["regimenes"])
        assert (resueltas["presupuesto"] > 0).all()
        assert (flujos["precio_reposo"] > 0).all()
        assert resueltas["captura"].between(0.0, 1.0 + 1e-9).all()
    else:
        assert (resueltas["regimen"] == "").all()
        assert (resueltas[["presupuesto", "captura"]] == 0.0).all().all()
        assert (flujos["precio_reposo"] == 0.0).all()
        # Las columnas de D63 a D69, con sus valores neutros.
        assert (resueltas[["piso_marginal", "renta_inframarginal",
                           "parte_juego"]] == 0.0).all().all()
        assert (resueltas["vendedores_no_despachados"] == "").all()


def test_una_hora_que_revienta_en_main_no_se_anota_resuelta_y_da_codigo_3(
        monkeypatch, tmp_path, capsys):
    import main_simulation as ms
    tablas = _almacen_en_memoria(monkeypatch)
    _sintetico_con_a_cero(monkeypatch, ms)
    # Secuencial, para que la sustitucion del nucleo alcance a las horas (en
    # paralelo las resuelven otros procesos).
    monkeypatch.setattr(ms, "SolverParams",
                        lambda **kw: SolverParams(**dict(kw, parallel=False)))
    llamadas = []
    original = motor.resuelve_reposo

    def revienta_la_tercera(*a, **kw):
        llamadas.append(1)
        if len(llamadas) == 3:
            raise ValueError("fabricada en main")
        return original(*a, **kw)

    monkeypatch.setattr(motor, "resuelve_reposo", revienta_la_tercera)
    _, p2p = ms.main(use_real_data=False, run_analysis=False,
                     metodo="reposo", out_dir=str(tmp_path / "salida"),
                     almacen=str(tmp_path / "almacen"))
    salida = capsys.readouterr().out
    rotas = [r for r in p2p if r.motivo]
    assert len(rotas) == 1
    k = rotas[0].k
    assert rotas[0].motivo == (f"{PREFIJO_EXCEPCION_REPOSO}: ValueError: "
                               f"fabricada en main")
    # La linea [C-190] la lista y la final [D48] la cuenta aparte.
    assert "[C-190] 1 de 24 horas terminaron con excepcion" in salida
    assert ("horas del reposo con excepcion, fuera de los regimenes: 1 "
            "(ver [C-190])") in salida
    # El almacen la anota sin resolver, con su motivo, y una sola fila.
    horas = pd.concat(tablas["horas"], ignore_index=True)
    fila = horas[horas["hora"] == k]
    assert len(fila) == 1
    assert not bool(fila["resuelta"].iloc[0])
    assert fila["motivo"].iloc[0].startswith(PREFIJO_EXCEPCION_REPOSO)
    # Y el codigo de salida de la corrida es 3.
    assert ms.codigo_de_salida(*ms.cuenta_para_salida(p2p)) == 3


def test_la_linea_de_ordenes_rechaza_el_reposo_con_el_sintetico_del_modelo_base():
    res = _cli("--metodo", "reposo")
    assert res.returncode == 2, (res.returncode, res.stdout[-500:])
    assert "CAL-32" in res.stderr
