"""
Presupuesto y vuelta anterior de la parada por estacionario (D36, D37), y el
codigo de salida de la corrida (D38). Arreglo final del conjunto, 2026-09-14.

La revision final encontro que la parada por estacionario de D26 (hasta el
horizonte 0,4) chocaba con el plazo por hora de D24: una hora que necesitaba
0,2 o 0,4 vencia y perdia tambien la solucion que ya tenia de las vueltas
anteriores. El autor decidio que la parada conserve la ultima vuelta buena y
no empiece una vuelta que no quepa en un presupuesto de evaluaciones del
integrador (D36); que una vuelta que falla deje la hora con la anterior
(D37); y que la corrida salga con codigo 3 si hubo alguna excepcion o mas
del 1 % de horas vencidas (D38).

SIN INTEGRAR DE VERDAD. `solve_coupled_for_hour` se sustituye con
`monkeypatch` EN EL MODULO DEL MOTOR, donde ahora se importa a nivel de
modulo (D36), por una funcion que devuelve trayectorias fabricadas, cada una
con su `nfev`, segun el horizonte que se le pida. Cada caso fija asi exacto
cuantas vueltas hay, cuanto cuesta cada una, cual es estacionaria y cual
falla, y corre en milisegundos. La hora es la primera con mercado del caso
sintetico de la compuerta C-165, la misma de `test_palancas_acoplado.py`.
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
    AgentParams, EMSP2P, GridParams, HourlyResult, SolverParams,
    FACTOR_CRECIMIENTO_DOBLEZ, _run_hour_worker,
)
from core.market_prep import classify_agents, compute_generation_limit  # noqa: E402
from gate_c165_desglose_horario import _caso  # noqa: E402
from main_simulation import codigo_de_salida, cuenta_para_salida  # noqa: E402

PGS, PGB = 1250.0, 114.0
T_SPAN = 0.02          # horizonte de la primera vuelta en todos los casos


# ─── ayudantes ──────────────────────────────────────────────────────────────


def _hora():
    """La primera hora del caso sintetico de C-165 con vendedores y
    compradores a la vez, con sus series completas para armar el motor."""
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


def _args(h, horizonte_max, presupuesto, pi_gb_j=None):
    """La tupla de 29 campos de `_run_hour_worker`, via acoplada, con la
    parada (`horizonte_max`) y el presupuesto al final. `pi_gb_j` no uniforme
    activa la restriccion de participacion de H-43."""
    sv = SolverParams()
    return (h["k"], h["g_klim"], h["d_k"], h["g_k"], h["sids"], h["bids"],
            h["a"], h["b"], h["lam"], h["theta"], h["etha"],
            PGS, PGB, sv.tau, sv.tau_buyers, sv.t_span, sv.n_points,
            sv.stackelberg_iters, sv.stackelberg_tol, sv.stackelberg_max,
            sv.ode_method, sv.buyer_competition,
            "acoplado", T_SPAN, pi_gb_j, False,
            1e-6, horizonte_max, presupuesto)


def _vuelta(J, I, i, *, nfev, estacionaria=False, exito=True, finita=True):
    """La trayectoria fabricada de la vuelta `i` (0 la primera).

    El precio sube en rampa. Si la vuelta es estacionaria, sube en la primera
    mitad y se queda quieto: el ultimo decimo no se mueve nada. Si no, sube
    hasta el final y el ultimo decimo recorre el 7,7 % del recorrido, muy por
    encima del 1 % de TOL_ESTACIONARIO. Cada vuelta tiene su propio volumen y
    su propio precio final, para poder decir cual se conservo.
    """
    n = 40
    if estacionaria:
        rampa = np.concatenate([np.linspace(0.0, 1.0, n // 2),
                                np.ones(n - n // 2)])
    else:
        rampa = np.linspace(0.0, 1.0, n)
    final = 500.0 + 10.0 * i
    pi_t = 300.0 + (final - 300.0) * np.tile(rampa, (I, 1))
    if not finita:
        # "Exito" del integrador con un precio no finito al final: el
        # recorrido sale `nan` y, sin la guarda, pasaria por estacionario.
        pi_t[0, -1] = np.nan
    # D47: la trayectoria fabricada lleva tambien `P_t`, como la de verdad,
    # porque el motor mide sobre ella el residuo del reparto. Quieta: todas
    # las parejas valen lo mismo en todos los pasos, de modo que el residuo
    # del reparto de estas vueltas es cero y no cambia ninguna de estas
    # cifras, que son las del criterio sobre el precio.
    P_t = np.full((J, I, n), 0.01 * (i + 1))
    return SimpleNamespace(P_star=P_t[:, :, -1].copy(),
                           pi_star=pi_t[:, -1].copy(), pi_t=pi_t, P_t=P_t,
                           success=exito, nfev=nfev, njev=0,
                           message="fabricada")


def _integrador(monkeypatch, guion):
    """Sustituye el integrador del motor por uno que sigue `guion`, una lista
    con los argumentos de `_vuelta` de cada vuelta, en orden. La vuelta se
    reconoce por el horizonte pedido (T_SPAN, 2·T_SPAN, 4·T_SPAN...).
    Devuelve la lista de horizontes pedidos y la de trayectorias fabricadas,
    que se llenan a medida que el motor llama."""
    pedidos, fabricadas = [], []

    def falso(**kw):
        h = float(kw["t_span"][1])
        i = int(round(np.log2(h / T_SPAN)))
        pedidos.append(h)
        tr = _vuelta(len(kw["G_net_j"]), len(kw["D_net_i"]), i, **guion[i])
        fabricadas.append(tr)
        return tr

    monkeypatch.setattr(motor, "solve_coupled_for_hour", falso)
    return pedidos, fabricadas


def _es_la_vuelta(res, tr):
    """El resultado de la hora es exactamente el de esa vuelta."""
    return (res.P_star is not None
            and np.array_equal(res.P_star, np.asarray(tr.P_star, dtype=float))
            and np.array_equal(res.pi_star,
                               np.clip(np.asarray(tr.pi_star, dtype=float),
                                       PGB, PGS)))


# ─── D36: el presupuesto ────────────────────────────────────────────────────


def test_presupuesto_pequeno_para_tras_la_primera_vuelta_y_la_conserva(
        monkeypatch):
    # 100 gastadas + 100 x 2,56 estimadas = 356 > 150: la segunda vuelta no
    # se empieza, y la hora se queda con la primera, idéntica.
    pedidos, fab = _integrador(monkeypatch, [dict(nfev=100),
                                             dict(nfev=256)])
    res = _run_hour_worker(_args(_hora(), 8 * T_SPAN, 150))
    assert pedidos == [T_SPAN]
    assert res.parada_acoplado == "presupuesto"
    assert res.horizonte_usado == T_SPAN
    assert res.motivo == ""
    assert _es_la_vuelta(res, fab[0])


def test_el_cociente_medido_entre_dos_vueltas_manda_sobre_la_constante(
        monkeypatch):
    # Vueltas de 100 y 400 evaluaciones: el cociente medido es 4. Con la
    # constante (2,56) la tercera se estimaria en 1024 y cabria en 1600
    # (500 + 1024 = 1524); con el medido se estima en 1600 y no cabe
    # (500 + 1600 = 2100). Se queda con la segunda.
    assert 500 + 400 * FACTOR_CRECIMIENTO_DOBLEZ <= 1600
    pedidos, fab = _integrador(monkeypatch, [dict(nfev=100), dict(nfev=400),
                                             dict(nfev=1600)])
    res = _run_hour_worker(_args(_hora(), 8 * T_SPAN, 1600))
    assert pedidos == [T_SPAN, 2 * T_SPAN]
    assert res.parada_acoplado == "presupuesto"
    assert res.horizonte_usado == 2 * T_SPAN
    assert _es_la_vuelta(res, fab[1])


def test_con_la_parada_apagada_el_presupuesto_no_actua(monkeypatch):
    # Un presupuesto de una sola evaluacion no toca la resolucion unica.
    pedidos, fab = _integrador(monkeypatch, [dict(nfev=100)])
    res = _run_hour_worker(_args(_hora(), None, 1))
    assert pedidos == [T_SPAN]
    assert res.parada_acoplado == "una_vuelta"
    assert res.horizonte_usado == T_SPAN
    assert _es_la_vuelta(res, fab[0])


# ─── D37: la vuelta que falla ───────────────────────────────────────────────


def test_si_falla_la_segunda_vuelta_se_conserva_la_primera(monkeypatch):
    pedidos, fab = _integrador(monkeypatch, [dict(nfev=100),
                                             dict(nfev=256, exito=False)])
    res = _run_hour_worker(_args(_hora(), 8 * T_SPAN, 10**9))
    assert pedidos == [T_SPAN, 2 * T_SPAN]
    assert res.parada_acoplado == "fallo_vuelta"
    assert res.horizonte_usado == T_SPAN
    assert res.motivo == ""
    assert _es_la_vuelta(res, fab[0])


def test_si_falla_la_primera_vuelta_la_hora_queda_sin_mercado_con_motivo(
        monkeypatch):
    pedidos, _ = _integrador(monkeypatch, [dict(nfev=100, exito=False)])
    res = _run_hour_worker(_args(_hora(), 8 * T_SPAN, 10**9))
    assert pedidos == [T_SPAN]
    assert res.P_star is None
    assert res.motivo.startswith("integrador sin exito")
    assert res.motivo == f"integrador sin exito al horizonte {T_SPAN:g}"
    assert res.parada_acoplado == "fallo_vuelta"
    assert res.horizonte_usado == 0.0


def test_con_la_parada_apagada_la_vuelta_fallida_tambien_deja_motivo(
        monkeypatch):
    # Antes de D37 esta hora volvia sin mercado y sin motivo. Sigue sin
    # mercado (ninguna cifra cambia) y ahora dice por que.
    _integrador(monkeypatch, [dict(nfev=100, exito=False)])
    res = _run_hour_worker(_args(_hora(), None, None))
    assert res.P_star is None
    assert res.motivo == f"integrador sin exito al horizonte {T_SPAN:g}"
    assert res.parada_acoplado == "una_vuelta"


# ─── D26: estacionario y tope, con su motivo ────────────────────────────────


def test_estacionario_en_la_segunda_vuelta(monkeypatch):
    pedidos, fab = _integrador(monkeypatch, [
        dict(nfev=100), dict(nfev=256, estacionaria=True), dict(nfev=655)])
    res = _run_hour_worker(_args(_hora(), 8 * T_SPAN, 10**9))
    assert pedidos == [T_SPAN, 2 * T_SPAN]
    assert res.parada_acoplado == "estacionario"
    assert res.horizonte_usado == 2 * T_SPAN
    assert _es_la_vuelta(res, fab[1])


def test_tope_sin_estacionario(monkeypatch):
    pedidos, fab = _integrador(monkeypatch, [dict(nfev=100), dict(nfev=256)])
    res = _run_hour_worker(_args(_hora(), 2 * T_SPAN, 10**9))
    assert pedidos == [T_SPAN, 2 * T_SPAN]
    assert res.parada_acoplado == "tope"
    assert res.horizonte_usado == 2 * T_SPAN
    assert _es_la_vuelta(res, fab[1])


# ─── la construccion de la tupla en produccion ──────────────────────────────


def test_el_presupuesto_viaja_desde_SolverParams_en_los_dos_caminos(
        monkeypatch):
    # `run_single_hour` y el lote de `EMSP2P.run` arman la tupla desde
    # `SolverParams`; los dos tienen que llevar el presupuesto al trabajador.
    h = _hora()
    N = h["a"].shape[0]
    sv = SolverParams(parallel=False, metodo="acoplado",
                      t_span_acoplado=T_SPAN,
                      horizonte_max_acoplado=8 * T_SPAN,
                      presupuesto_eval_acoplado=150)
    ems = EMSP2P(
        agents=AgentParams(N=N, a=h["a"], b=h["b"], c=h["c"], lam=h["lam"],
                           theta=h["theta"], etha=h["etha"]),
        grid=GridParams(pi_gs=PGS, pi_gb=PGB), solver=sv)

    pedidos, _ = _integrador(monkeypatch, [dict(nfev=100), dict(nfev=256)])
    res = ems.run_single_hour(h["k"], h["D"], h["G"])
    assert pedidos == [T_SPAN]
    assert res.parada_acoplado == "presupuesto"

    pedidos, _ = _integrador(monkeypatch, [dict(nfev=100), dict(nfev=256)])
    resultados, _, _ = ems.run(h["D"][:, [h["k"]]], h["G"][:, [h["k"]]])
    assert pedidos == [T_SPAN]
    assert resultados[0].parada_acoplado == "presupuesto"


@pytest.mark.parametrize("malo", [0, -5, True, 2.5])
def test_SolverParams_rechaza_un_presupuesto_que_no_es_entero_positivo(malo):
    with pytest.raises(ValueError):
        SolverParams(presupuesto_eval_acoplado=malo)


# ─── D38: el codigo de salida ───────────────────────────────────────────────


def test_codigo_de_salida_cero_sin_nada():
    assert codigo_de_salida(0, 0, 0, 0) == 0
    assert codigo_de_salida(1126, 0, 0, 0) == 0


def test_codigo_de_salida_tres_con_una_sola_excepcion():
    assert codigo_de_salida(1126, 0, 1, 0) == 3


def test_codigo_de_salida_tres_con_vencidas_por_encima_del_uno_por_ciento():
    assert codigo_de_salida(100, 2, 0, 0) == 3
    assert codigo_de_salida(1000, 11, 0, 0) == 3


def test_codigo_de_salida_tres_con_sin_exito_por_encima_del_uno_por_ciento():
    # D44: la hora que D41 corta queda «integrador sin exito»; sola ya cuenta.
    assert codigo_de_salida(100, 0, 0, 2) == 3
    assert codigo_de_salida(1000, 0, 0, 11) == 3


def test_codigo_de_salida_tres_cuando_la_suma_pasa_aunque_ninguna_sola_pase():
    # D44: el umbral se aplica a la suma. Una de cien vencida y una sin exito
    # son el 1 % cada una (ninguna pasa sola) y el 2 % juntas; seis y cinco de
    # mil son el 0,6 % y el 0,5 %, y el 1,1 % juntas.
    assert codigo_de_salida(100, 1, 0, 0) == 0
    assert codigo_de_salida(100, 0, 0, 1) == 0
    assert codigo_de_salida(100, 1, 0, 1) == 3
    assert codigo_de_salida(1000, 6, 0, 0) == 0
    assert codigo_de_salida(1000, 0, 0, 5) == 0
    assert codigo_de_salida(1000, 6, 0, 5) == 3


def test_codigo_de_salida_cero_justo_en_el_uno_por_ciento():
    # La frontera: «mas del 1 %» es estricto, y se mide sobre la suma de
    # vencidas y sin exito (D44). Una de cien y diez de mil son exactamente
    # el 1 % y salen con 0; una mas, con 3 (casos anteriores).
    assert codigo_de_salida(100, 1, 0, 0) == 0
    assert codigo_de_salida(1000, 10, 0, 0) == 0
    assert codigo_de_salida(300, 3, 0, 0) == 0
    assert codigo_de_salida(1000, 5, 0, 5) == 0
    assert codigo_de_salida(300, 2, 0, 1) == 0
    assert codigo_de_salida(1000, 0, 0, 10) == 0


def test_codigo_de_salida_rechaza_conteos_imposibles():
    with pytest.raises(ValueError):
        codigo_de_salida(10, 11, 0, 0)   # mas vencidas que horas de mercado
    with pytest.raises(ValueError):
        codigo_de_salida(10, 6, 0, 5)    # vencidas mas sin exito, tambien
    with pytest.raises(ValueError):
        codigo_de_salida(10, -1, 0, 0)
    with pytest.raises(ValueError):
        codigo_de_salida(10, 0, 0, -1)
    with pytest.raises(TypeError):
        codigo_de_salida(10, 0, 0)       # D44: la cuenta sin exito es obligatoria


def test_cuenta_para_salida_define_el_denominador():
    # Una hora sin un lado (no cuenta), una resuelta, una vencida (sin ids,
    # pero cuenta), una con excepcion y una sin exito del integrador (con
    # ids, cuentan; la sin exito lleva su propio conteo desde D44).
    horas = [
        HourlyResult(k=0),
        HourlyResult(k=1, seller_ids=[0], buyer_ids=[1]),
        HourlyResult(k=2, motivo="vencio el plazo por hora de 15 min"),
        HourlyResult(k=3, seller_ids=[0], buyer_ids=[1],
                     motivo="excepcion del acoplado: ValueError: x"),
        HourlyResult(k=4, seller_ids=[0], buyer_ids=[1],
                     motivo="integrador sin exito al horizonte 0.05"),
    ]
    assert cuenta_para_salida(horas) == (4, 1, 1, 1)


# ─── re-revision: el reintento de H-43 y las vueltas no finitas ─────────────


def _integrador_por_J(monkeypatch, guiones):
    """Como `_integrador`, pero con un guion por numero de vendedores: el
    conjunto completo de la hora (dos) y el reducido de H-43 (uno) siguen
    guiones distintos. Devuelve los horizontes pedidos por cada uno."""
    pedidos = {J: [] for J in guiones}

    def falso(**kw):
        J, I = len(kw["G_net_j"]), len(kw["D_net_i"])
        h = float(kw["t_span"][1])
        i = int(round(np.log2(h / T_SPAN)))
        pedidos[J].append(h)
        return _vuelta(J, I, i, **guiones[J][i])

    monkeypatch.setattr(motor, "solve_coupled_for_hour", falso)
    return pedidos


def _espia_presupuesto(monkeypatch):
    """Anota, en cada llamada a `_resuelve_acoplado`, cuantos vendedores trae
    y que presupuesto recibe, y deja que resuelva igual."""
    vistos = []
    original = motor._resuelve_acoplado

    def espia(**kw):
        vistos.append((len(kw["a_j"]), kw["presupuesto_eval"]))
        return original(**kw)

    monkeypatch.setattr(motor, "_resuelve_acoplado", espia)
    return vistos


# Pisos por vendedor que retiran a sids[0] (el mercado le paga 500 < 600) y
# dejan a sids[1] (500 > 300), como en test_palancas_acoplado.py.
PISO_H43 = np.array([600.0, 300.0])


def test_el_reintento_de_h43_recibe_solo_lo_que_queda_del_presupuesto(
        monkeypatch):
    # Conjunto completo: una vuelta estacionaria de 100 evaluaciones, y H-43
    # retira a un vendedor. Conjunto reducido: una primera vuelta de 100 que
    # no es estacionaria. Con lo que queda (400 - 100 = 300), la segunda se
    # estima en 256 y no cabe (100 + 256 = 356 > 300): para en
    # «presupuesto». Con el presupuesto entero (400) si cabria y doblaria.
    h = _hora()
    assert len(h["sids"]) == 2, "esta prueba necesita dos vendedores"
    assert 100 + 100 * FACTOR_CRECIMIENTO_DOBLEZ <= 400
    assert 100 + 100 * FACTOR_CRECIMIENTO_DOBLEZ > 300
    pedidos = _integrador_por_J(monkeypatch, {
        2: [dict(nfev=100, estacionaria=True)],
        1: [dict(nfev=100), dict(nfev=256), dict(nfev=655)]})
    vistos = _espia_presupuesto(monkeypatch)
    res = _run_hour_worker(_args(h, 8 * T_SPAN, 400, pi_gb_j=PISO_H43))
    assert vistos == [(2, 400), (1, 300)]
    assert pedidos[1] == [T_SPAN]
    assert res.retirados == [h["sids"][0]]
    assert res.P_star is not None
    assert res.parada_acoplado == "presupuesto"
    assert res.horizonte_usado == T_SPAN


def test_si_el_conjunto_completo_agoto_el_presupuesto_el_reducido_hace_una_vuelta(
        monkeypatch):
    # El conjunto completo gasta 500 de 400 (su primera vuelta corre
    # siempre). Queda max(1, 400 - 500) = 1: el reducido hace su primera
    # vuelta y no dobla.
    h = _hora()
    pedidos = _integrador_por_J(monkeypatch, {
        2: [dict(nfev=500, estacionaria=True)],
        1: [dict(nfev=100), dict(nfev=256)]})
    vistos = _espia_presupuesto(monkeypatch)
    res = _run_hour_worker(_args(h, 8 * T_SPAN, 400, pi_gb_j=PISO_H43))
    assert vistos == [(2, 400), (1, 1)]
    assert pedidos[1] == [T_SPAN]
    assert res.parada_acoplado == "presupuesto"


def test_con_la_parada_apagada_el_reintento_de_h43_recibe_el_presupuesto_tal_cual(
        monkeypatch):
    # Sin parada el presupuesto es inerte y pasa sin descontar nada.
    h = _hora()
    _integrador_por_J(monkeypatch, {2: [dict(nfev=100)], 1: [dict(nfev=100)]})
    vistos = _espia_presupuesto(monkeypatch)
    res = _run_hour_worker(_args(h, None, 400, pi_gb_j=PISO_H43))
    assert vistos == [(2, 400), (1, 400)]
    assert res.parada_acoplado == "una_vuelta"


def test_una_vuelta_no_finita_no_desplaza_a_la_buena(monkeypatch):
    # La segunda vuelta dice «exito» pero trae un precio no finito: su
    # recorrido `nan` pasaria por estacionario. Cuenta como fallida (D37).
    pedidos, fab = _integrador(monkeypatch, [
        dict(nfev=100), dict(nfev=256, finita=False)])
    res = _run_hour_worker(_args(_hora(), 8 * T_SPAN, 10**9))
    assert pedidos == [T_SPAN, 2 * T_SPAN]
    assert res.parada_acoplado == "fallo_vuelta"
    assert res.horizonte_usado == T_SPAN
    assert res.motivo == ""
    assert _es_la_vuelta(res, fab[0])


def test_una_primera_vuelta_no_finita_deja_la_hora_sin_mercado_con_motivo(
        monkeypatch):
    _integrador(monkeypatch, [dict(nfev=100, finita=False)])
    res = _run_hour_worker(_args(_hora(), 8 * T_SPAN, 10**9))
    assert res.P_star is None
    assert res.motivo == f"integrador sin exito al horizonte {T_SPAN:g}"
    assert res.parada_acoplado == "fallo_vuelta"
    assert res.horizonte_usado == 0.0
