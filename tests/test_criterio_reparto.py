"""
El criterio de parada sobre el reparto, y el residuo del reparto guardado
siempre (H-86; D47). 2026-09-16.

QUE SE MIDE. La via acoplada para por estacionario cuando EL PRECIO se mueve
menos del 1 % de su recorrido en el ultimo decimo (`TOL_ESTACIONARIO`, D26). La
medicion del arranque corrida en el servidor encontro que en muchas horas el
precio ya esta quieto mientras el reparto entre compradores sigue moviendose
entero: la hora 109 de E0 paro por estacionario con residuo 0,0065 y su reparto
estaba lejos del punto final, y al horizonte 2,0 converge a darle todo el
excedente a un solo comprador mientras el horizonte de produccion lo reparte
casi por igual entre cuatro (H-86).

D47 anade la medida del reparto como opcion del criterio, y guarda su residuo
SIEMPRE, se use o no: sin el no se puede censar cuantas horas quedaron con la
energia todavia cambiando de manos sin repetir la corrida entera.

SIN DATOS REALES. La hora sale del caso sintetico de la compuerta C-165, la
misma de `test_piso_P.py` y `test_presupuesto_acoplado.py`, y las vueltas del
criterio se fabrican sustituyendo el integrador, sin integrar de verdad.

Cuatro grupos:
  - la medida (`_movimiento_relativo`), con trayectorias sinteticas;
  - con "precio", el resultado es el de antes de D47, al bit;
  - con "precio_y_reparto", una hora de precio quieto y reparto en marcha no
    para por estacionario y sigue doblando el horizonte;
  - el residuo del reparto viaja hasta el resultado de la hora, y un criterio
    o un umbral desconocidos se rechazan en voz alta.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import core.ems_p2p as motor  # noqa: E402
from core.ems_p2p import (  # noqa: E402
    TOL_ESTACIONARIO, TOL_REPARTO, AgentParams, EMSP2P, GridParams,
    SolverParams, _movimiento_relativo, _run_hour_worker)
from core.market_prep import classify_agents, compute_generation_limit  # noqa: E402
from gate_c165_desglose_horario import _caso  # noqa: E402

PGS, PGB = 1250.0, 114.0
T_ACO = 0.002          # horizonte de la primera vuelta, corto para que corra
# Pisos por vendedor que retiran a sids[0] (el mercado le paga 500 < 600) y
# dejan a sids[1] (500 > 300), como en `test_arranque_acoplado.py`. Con ellos,
# la hora pasa por la recursion de H-43 y resuelve DOS veces.
PISO_H43 = np.array([600.0, 300.0])


# ─── la medida ─────────────────────────────────────────────────────────────


def _medida_de_siempre(traj):
    """La medida del precio ANTES de D47, copiada tal cual de las lineas que
    `_movimiento_relativo` reemplaza en `_resuelve_acoplado` y en el
    trabajador."""
    traj = np.asarray(traj, dtype=float)
    cola = int(max(1, traj.shape[1] // 10))
    mov = float(np.max(np.abs(traj[:, -1] - traj[:, -cola])))
    rec = float(np.max(np.abs(traj.max(axis=1) - traj.min(axis=1))))
    return mov / rec if rec > 1e-12 else 0.0


def test_un_reparto_quieto_mide_cero():
    # Todas las parejas valen lo mismo en todos los pasos: no se mueve nada.
    P_t = np.full((3, 2, 40), 1.5)
    assert _movimiento_relativo(P_t, "energia") == 0.0


def test_un_reparto_que_se_mueve_en_una_sola_pareja():
    # Una sola pareja cambia en el ultimo paso, y la medida es lo que esa
    # pareja mueve frente a la ENERGIA TRANSADA de la hora, no frente a su
    # propio recorrido.
    n = 40
    P_t = np.ones((2, 3, n))
    P_t[0, 1, -1] = 1.0 + 0.5
    energia = float(np.sum(P_t[:, :, -1]))      # 6 parejas + 0,5
    assert _movimiento_relativo(P_t, "energia") == pytest.approx(0.5 / energia)
    # El MISMO movimiento sobre una hora que reparte el doble de energia pesa
    # menos: es una fraccion de lo que se reparte, no del propio recorrido de
    # la pareja, que en las dos es el mismo.
    P_gorda = np.full((2, 3, n), 2.0)
    P_gorda[0, 1, -1] += 0.5
    assert (_movimiento_relativo(P_gorda, "energia")
            == pytest.approx(0.5 / 12.5))
    assert (_movimiento_relativo(P_gorda, "energia")
            < _movimiento_relativo(P_t, "energia"))


def test_con_la_energia_casi_nula_la_medida_no_divide_por_cero():
    n = 40
    # La hora sin energia que repartir: todo cero. Ni excepcion ni NaN.
    assert _movimiento_relativo(np.zeros((2, 2, n)), "energia") == 0.0
    # Y una con energia final nula y un movimiento diminuto: el divisor se
    # acota a 1e-12, de modo que la medida sale FINITA en vez de infinita o
    # `nan`. Que sea finita es lo que importa, porque un `nan` no es menor ni
    # mayor que el umbral y dejaria la hora doblando el horizonte sin que
    # nada dijera por que. Esto NO es una guarda contra pasar por estacionaria:
    # 1e-20 sobre 1e-12 son 1e-8, muy por debajo del umbral, y esa hora se
    # declara estacionaria, que es lo correcto cuando no hay energia que
    # repartir.
    P_t = np.zeros((2, 2, n))
    P_t[0, 0, -(n // 10)] = 1e-20        # el primer paso del ultimo decimo
    m = _movimiento_relativo(P_t, "energia")
    assert np.isfinite(m) and m > 0.0


def test_la_medida_del_precio_es_la_de_siempre_al_bit():
    rng = np.random.default_rng(7)
    for forma in ((1, 5), (3, 40), (4, 150)):
        traj = 300.0 + 400.0 * rng.random(forma)
        assert (_movimiento_relativo(traj, "recorrido")
                == _medida_de_siempre(traj))
    # El caso degenerado: un precio que no se mueve nada (recorrido cero).
    quieto = np.full((2, 30), 512.0)
    assert (_movimiento_relativo(quieto, "recorrido")
            == _medida_de_siempre(quieto) == 0.0)
    # Y la trayectoria de un solo punto, la que corta D41.
    uno = np.full((2, 1), 512.0)
    assert (_movimiento_relativo(uno, "recorrido")
            == _medida_de_siempre(uno) == 0.0)


def test_una_normalizacion_desconocida_se_rechaza_en_voz_alta():
    with pytest.raises(ValueError, match="normaliza"):
        _movimiento_relativo(np.ones((2, 10)), "otra")


# ─── la hora sintetica y la tupla ──────────────────────────────────────────


def _hora():
    """La primera hora del caso sintetico de C-165 con vendedores y
    compradores a la vez, la misma de `test_piso_P.py`."""
    D, G = _caso(T=24)
    N = D.shape[0]
    a = np.zeros(N); b = np.full(N, 225.0); c = np.zeros(N)
    lam = np.full(N, 100.0); theta = np.full(N, 0.5); etha = np.full(N, 0.1)
    for k in range(D.shape[1]):
        g_klim = compute_generation_limit(G[:, k], a, b, c, PGS)
        _, sids, bids = classify_agents(g_klim, D[:, k])
        if sids and bids:
            return dict(k=k, g_klim=g_klim, d_k=D[:, k].copy(),
                        g_k=G[:, k].copy(), sids=sids, bids=bids, a=a, b=b,
                        c=c, lam=lam, theta=theta, etha=etha, D=D, G=G)
    raise RuntimeError("ninguna hora del caso sintetico de C-165 tiene "
                       "vendedores y compradores a la vez")


def _args30(h, horizonte_max, presupuesto=10**9, pi_gb_j=None):
    """La tupla de 30 campos de `_run_hour_worker`, la de antes de D47, via
    acoplada y con la parada por estacionario activa. `pi_gb_j=None` (defecto)
    deja inerte la restriccion de participacion (H-43); con un vector no
    uniforme la activa."""
    sv = SolverParams()
    return (h["k"], h["g_klim"], h["d_k"], h["g_k"], h["sids"], h["bids"],
            h["a"], h["b"], h["lam"], h["theta"], h["etha"],
            PGS, PGB, sv.tau, sv.tau_buyers, sv.t_span, sv.n_points,
            sv.stackelberg_iters, sv.stackelberg_tol, sv.stackelberg_max,
            sv.ode_method, sv.buyer_competition,
            "acoplado", T_ACO, pi_gb_j, False,
            1e-6, horizonte_max, presupuesto, sv.arranque_acoplado)


# ─── con "precio", identico al bit a lo de antes de D47 ────────────────────


def test_con_precio_la_tupla_de_30_campos_da_lo_mismo_que_pedirlo():
    h = _hora()
    viejo = _run_hour_worker(_args30(h, 4 * T_ACO))
    nuevo = _run_hour_worker(_args30(h, 4 * T_ACO) + ("precio", TOL_REPARTO))
    assert viejo.P_star is not None and nuevo.P_star is not None
    assert np.array_equal(viejo.P_star, nuevo.P_star)
    assert np.array_equal(viejo.pi_star, nuevo.pi_star)
    for campo in ("motivo", "parada_acoplado", "horizonte_usado",
                  "iters_used", "norm_rel_final", "residuo_reparto"):
        assert getattr(viejo, campo) == getattr(nuevo, campo), campo


def test_con_precio_la_hora_de_produccion_es_la_de_antes_de_d47():
    # La via de produccion (`EMSP2P.run_single_hour`, que arma la tupla desde
    # `SolverParams`) con el criterio por defecto da exactamente la hora de la
    # tupla anterior a D47; y el residuo del precio que anota es, al bit, la
    # medida de siempre sobre la trayectoria que conservo.
    h = _hora()
    N = h["a"].shape[0]
    sv = SolverParams(parallel=False, metodo="acoplado",
                      t_span_acoplado=T_ACO, horizonte_max_acoplado=4 * T_ACO,
                      presupuesto_eval_acoplado=10**9)
    assert sv.criterio_estacionario == "precio"
    ems = EMSP2P(
        agents=AgentParams(N=N, a=h["a"], b=h["b"], c=h["c"], lam=h["lam"],
                           theta=h["theta"], etha=h["etha"]),
        grid=GridParams(pi_gs=PGS, pi_gb=PGB), solver=sv)
    res = ems.run_single_hour(h["k"], h["D"], h["G"],
                              devuelve_trayectoria=True)
    viejo = _run_hour_worker(_args30(h, 4 * T_ACO))
    assert res.P_star is not None
    assert np.array_equal(res.P_star, viejo.P_star)
    assert np.array_equal(res.pi_star, viejo.pi_star)
    assert res.parada_acoplado == viejo.parada_acoplado
    assert res.horizonte_usado == viejo.horizonte_usado
    assert res.norm_rel_final == _medida_de_siempre(res.tr.pi_t)


# ─── con "precio_y_reparto", el integrador fabricado ───────────────────────


def _vuelta(J, I, i, *, reparto_quieto, nfev=100, n=40):
    """La trayectoria fabricada de la vuelta `i` (0 la primera).

    EL PRECIO SIEMPRE ESTA QUIETO: sube en la primera mitad y se queda, de
    modo que su ultimo decimo no se mueve nada y el criterio de D26 declara
    estacionaria la primera vuelta. Lo que cambia entre vueltas es el REPARTO:
    con `reparto_quieto=False` una pareja se lleva 0,5 (kWh) mas en el ultimo
    paso, es decir el 7,7 % de la energia de la hora, muy por encima del 1 %
    de TOL_REPARTO. Cada vuelta tiene su propio volumen, para poder decir cual
    se conservo.
    """
    rampa = np.concatenate([np.linspace(0.0, 1.0, n // 2),
                            np.ones(n - n // 2)])
    pi_t = 300.0 + 200.0 * np.tile(rampa, (I, 1))
    P_t = np.full((J, I, n), 1.0 + i)
    if not reparto_quieto:
        P_t[0, 0, -1] += 0.5
    return SimpleNamespace(P_star=P_t[:, :, -1].copy(),
                           pi_star=pi_t[:, -1].copy(), pi_t=pi_t, P_t=P_t,
                           success=True, nfev=nfev, njev=0,
                           message="fabricada")


def _integrador(monkeypatch, guion):
    """Sustituye el integrador del motor por uno que sigue `guion`, una lista
    con los argumentos de `_vuelta` de cada vuelta, en orden. La vuelta se
    reconoce por el horizonte pedido (T_ACO, 2·T_ACO, 4·T_ACO...)."""
    pedidos, fabricadas = [], []

    def falso(**kw):
        h = float(kw["t_span"][1])
        i = int(round(np.log2(h / T_ACO)))
        pedidos.append(h)
        tr = _vuelta(len(kw["G_net_j"]), len(kw["D_net_i"]), i, **guion[i])
        fabricadas.append(tr)
        return tr

    monkeypatch.setattr(motor, "solve_coupled_for_hour", falso)
    return pedidos, fabricadas


def test_con_precio_esa_misma_hora_para_en_la_primera_vuelta(monkeypatch):
    # El contraste de la prueba siguiente: con el criterio de hoy, el precio
    # quieto basta y la hora para en la primera vuelta, con el reparto todavia
    # en marcha. Es el mecanismo de H-86.
    pedidos, fab = _integrador(monkeypatch, [dict(reparto_quieto=False)] * 3)
    res = _run_hour_worker(_args30(_hora(), 4 * T_ACO)
                           + ("precio", TOL_REPARTO))
    assert pedidos == [T_ACO]
    assert res.parada_acoplado == "estacionario"
    assert res.horizonte_usado == T_ACO
    # Y aun asi el residuo del reparto queda anotado, que es la mitad de D47
    # que no depende del criterio.
    assert res.residuo_reparto == pytest.approx(0.5 / 6.5, rel=1e-12)
    assert res.residuo_reparto > TOL_REPARTO


def test_con_el_criterio_nuevo_no_para_y_dobla_hasta_que_el_reparto_se_quieta(
        monkeypatch):
    # Las dos primeras vueltas tienen el precio quieto y el reparto en marcha:
    # con "precio_y_reparto" no son estacionarias y el horizonte se dobla. La
    # tercera tiene las dos medidas quietas y es la que se conserva.
    pedidos, fab = _integrador(monkeypatch, [
        dict(reparto_quieto=False), dict(reparto_quieto=False),
        dict(reparto_quieto=True)])
    res = _run_hour_worker(_args30(_hora(), 4 * T_ACO)
                           + ("precio_y_reparto", TOL_REPARTO))
    assert pedidos == [T_ACO, 2 * T_ACO, 4 * T_ACO]
    assert res.parada_acoplado == "estacionario"
    assert res.horizonte_usado == 4 * T_ACO
    assert res.motivo == ""
    assert np.array_equal(res.P_star,
                          np.asarray(fab[2].P_star, dtype=float))
    assert res.residuo_reparto == 0.0
    # El precio estaba quieto en las tres: lo que doblo el horizonte fue el
    # reparto, y solo el.
    assert res.norm_rel_final <= TOL_ESTACIONARIO


def test_con_el_criterio_nuevo_el_tope_corta_con_el_reparto_en_marcha(
        monkeypatch):
    # Si el reparto no se quieta nunca, la hora llega al tope y se conserva la
    # ultima vuelta, con su residuo del reparto por encima del umbral: es
    # justo la hora que el censo tiene que poder contar.
    pedidos, fab = _integrador(monkeypatch, [dict(reparto_quieto=False)] * 3)
    res = _run_hour_worker(_args30(_hora(), 2 * T_ACO)
                           + ("precio_y_reparto", TOL_REPARTO))
    assert pedidos == [T_ACO, 2 * T_ACO]
    assert res.parada_acoplado == "tope"
    assert res.horizonte_usado == 2 * T_ACO
    assert res.residuo_reparto == pytest.approx(0.5 / 12.5, rel=1e-12)
    assert res.residuo_reparto > TOL_REPARTO


def test_el_umbral_del_reparto_manda_sobre_la_parada(monkeypatch):
    # Con un umbral por encima de lo que el reparto se mueve (7,7 %), la
    # primera vuelta vuelve a ser estacionaria: el criterio no es una
    # constante escondida.
    pedidos, _ = _integrador(monkeypatch, [dict(reparto_quieto=False)] * 3)
    res = _run_hour_worker(_args30(_hora(), 4 * T_ACO)
                           + ("precio_y_reparto", 0.2))
    assert pedidos == [T_ACO]
    assert res.parada_acoplado == "estacionario"


# ─── el residuo viaja, y lo desconocido se rechaza ─────────────────────────


def test_el_residuo_del_reparto_viaja_hasta_el_resultado_de_la_hora():
    # Sin fabricar nada: la hora sintetica resuelta de verdad por la via de
    # produccion trae el residuo del reparto, y es la medida sobre la
    # trayectoria que conservo.
    h = _hora()
    N = h["a"].shape[0]
    ems = EMSP2P(
        agents=AgentParams(N=N, a=h["a"], b=h["b"], c=h["c"], lam=h["lam"],
                           theta=h["theta"], etha=h["etha"]),
        grid=GridParams(pi_gs=PGS, pi_gb=PGB),
        solver=SolverParams(parallel=False, metodo="acoplado",
                            t_span_acoplado=T_ACO))
    res = ems.run_single_hour(h["k"], h["D"], h["G"],
                              devuelve_trayectoria=True)
    assert res.P_star is not None
    assert res.residuo_reparto == _movimiento_relativo(res.tr.P_t, "energia")
    assert np.isfinite(res.residuo_reparto) and res.residuo_reparto >= 0.0
    # La via alternada no produce trayectoria, y su residuo del reparto es
    # cero, no un valor inventado.
    ems.solver = SolverParams(parallel=False, metodo="alternado")
    assert ems.run_single_hour(h["k"], h["D"], h["G"]).residuo_reparto == 0.0


# ─── el costo de la hora (D47), que es lo que decide el horizonte ──────────


def _vueltas_por_llamada(monkeypatch, nfevs):
    """Sustituye el integrador por uno que devuelve UNA vuelta por llamada, con
    el `nfev` que se le diga y las dos medidas quietas. Anota cuantos
    vendedores traia cada llamada, que es lo que distingue el conjunto completo
    del reducido en la recursion de H-43."""
    vendedores = []

    def falso(**kw):
        J, I = len(kw["G_net_j"]), len(kw["D_net_i"])
        tr = _vuelta(J, I, 0, reparto_quieto=True,
                     nfev=nfevs[len(vendedores)])
        vendedores.append(J)
        return tr

    monkeypatch.setattr(motor, "solve_coupled_for_hour", falso)
    return vendedores


def test_las_evaluaciones_son_la_suma_de_las_vueltas_y_los_segundos_son_finitos(
        monkeypatch):
    # Tres vueltas de 100, 200 y 400 evaluaciones: la hora dobla dos veces
    # porque el reparto no se quieta hasta la tercera, y lo que se anota es lo
    # que gasto EN TODAS, no lo de la que se conservo.
    pedidos, _ = _integrador(monkeypatch, [
        dict(reparto_quieto=False, nfev=100),
        dict(reparto_quieto=False, nfev=200),
        dict(reparto_quieto=True, nfev=400)])
    res = _run_hour_worker(_args30(_hora(), 4 * T_ACO)
                           + ("precio_y_reparto", TOL_REPARTO))
    assert pedidos == [T_ACO, 2 * T_ACO, 4 * T_ACO]
    assert res.evaluaciones == 700
    # El tiempo es de pared y depende de la maquina: lo unico que se puede
    # afirmar de el es que es un numero finito y no negativo.
    assert np.isfinite(res.segundos) and res.segundos >= 0.0


def test_la_recursion_de_h43_suma_las_dos_resoluciones_que_pago_la_hora(
        monkeypatch):
    h = _hora()
    assert len(h["sids"]) == 2, "esta prueba necesita dos vendedores"
    vendedores = _vueltas_por_llamada(monkeypatch, [100, 250])
    res = _run_hour_worker(_args30(h, None, pi_gb_j=PISO_H43)
                           + ("precio", TOL_REPARTO))
    # El conjunto completo, con dos vendedores, y el reducido, con uno.
    assert vendedores == [2, 1]
    assert res.retirados == [h["sids"][0]]
    assert res.evaluaciones == 350
    assert np.isfinite(res.segundos) and res.segundos >= 0.0


def test_la_via_alternada_no_cobra_costo():
    h = _hora()
    N = h["a"].shape[0]
    ems = EMSP2P(
        agents=AgentParams(N=N, a=h["a"], b=h["b"], c=h["c"], lam=h["lam"],
                           theta=h["theta"], etha=h["etha"]),
        grid=GridParams(pi_gs=PGS, pi_gb=PGB),
        solver=SolverParams(parallel=False, metodo="alternado"))
    res = ems.run_single_hour(h["k"], h["D"], h["G"])
    assert res.P_star is not None
    # La via alternada no pasa por el acoplado: su costo no es cero medido,
    # es que no hay nada que medir ahi.
    assert res.segundos == 0.0
    assert res.evaluaciones == 0


def test_una_hora_sin_vendedores_o_sin_compradores_no_cobra_costo():
    h = _hora()
    for clave in ("sids", "bids"):
        hh = dict(h)
        hh[clave] = []
        res = _run_hour_worker(_args30(hh, 4 * T_ACO)
                               + ("precio", TOL_REPARTO))
        assert res.P_star is None, clave
        assert res.motivo == "", clave
        assert res.segundos == 0.0 and res.evaluaciones == 0, clave


def test_un_criterio_o_un_umbral_desconocidos_se_rechazan():
    with pytest.raises(ValueError, match="criterio_estacionario"):
        SolverParams(criterio_estacionario="reparto")
    for malo in (0.0, -1.0, float("nan"), float("inf"), True, "0.01"):
        with pytest.raises(ValueError, match="tol_reparto"):
            SolverParams(tol_reparto=malo)
    # Y en la tupla armada a mano, antes de resolver nada.
    with pytest.raises(ValueError, match="criterio"):
        _run_hour_worker(_args30(_hora(), 4 * T_ACO) + ("otro", TOL_REPARTO))
