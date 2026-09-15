"""
El arranque factible del solucionador acoplado, como opcion apagada (H-85;
D45). 2026-09-15.

La matriz de trece corridas dejo nueve horas sin resolver por el arranque del
acoplado: reparte la oferta de cada vendedor a partes iguales entre los
compradores, y en la hora 753 de E4 (generacion por siete) el comprador 1,
con un deficit de 1,90 (kWh), recibe 10,45 al empezar; su multiplicador de
demanda desborda hacia t = 7,2e-6 y el corte de D41 detiene la hora. El
arranque factible reparte en proporcion al lado corto: ningun comprador
arranca con mas de lo que necesita y ningun vendedor ofrece mas de lo que
tiene. D45: se implementa como opcion, apagada por defecto e identica al bit
a lo de antes, y se mide en el servidor antes de adoptarla.

SIN DATOS REALES. Las entradas de la hora 753 son literales hexadecimales
(`float.fromhex`), identicos al bit en cualquier maquina. Se sacaron una vez
con `paso_a_paso.carga("m1", factor_generacion=7)` y la receta `entradas` de
los guiones de H-85 (`anatomia_arranque.py`), y su huella SHA-256 (G_net,
D_net, a, b, G_klim, techo y piso, en float64) se comprueba.

Cuatro grupos:
  - la regla del arranque: el factible cumple las dos capacidades en los dos
    casos del mercado, el de siempre se reproduce al bit, y una regla
    desconocida se rechaza;
  - el motor: con el defecto el trabajador da lo mismo que con la tupla vieja
    de 29 campos, el factible por `EMSP2P.run_single_hour` y por el lote de
    `EMSP2P.run` es identico a llamar directamente, y la regla viaja por los
    tres sitios que arman la tupla (con la recursion de H-43);
  - la hora 753, rapida: al horizonte corto el arranque de siempre desborda y
    D41 la corta, y el factible termina sin valores no finitos;
  - la hora 753, lenta (unos 4 (min) en la maquina de trabajo): el factible
    al horizonte de produccion termina, y ningun comprador recibe mas que su
    deficit.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import core.coupled_ode_convergence as ccc  # noqa: E402
import core.ems_p2p as motor  # noqa: E402
from core.coupled_ode_convergence import (  # noqa: E402
    _arranque_P0, solve_coupled_for_hour)
from core.ems_p2p import (  # noqa: E402
    AgentParams, EMSP2P, GridParams, SolverParams, _run_hour_worker)
from core.market_prep import classify_agents, compute_generation_limit  # noqa: E402
from gate_c165_desglose_horario import _caso  # noqa: E402


def _hex(v):
    return np.array([float.fromhex(x) for x in v], dtype=float)


# ─── la hora 753 de E4 (generacion por siete), al bit ──────────────────────
# 2025-05-05 9:00; vendedores 0, 3 y 4, compradores 1 y 2. La oferta no
# cubre la demanda (20,897 frente a 20,927 (kWh)).

# Excedente neto de cada vendedor y deficit neto de cada comprador (kWh).
GN = _hex(["0x1.855b2d11d6690p+1", "0x1.41916872b020cp+3",
           "0x1.f39c9a8e448a4p+2"])
DN = _hex(["0x1.e608770e9bea0p+0", "0x1.3072f608770e9p+4"])
# Coeficientes de costo de los vendedores y generacion limite de los
# compradores (kWh).
A = _hex(["0x0.0p+0", "0x0.0p+0", "0x0.0p+0"])
B = _hex(["0x1.e224924924924p+7", "0x1.e224924924924p+7",
          "0x1.c200000000000p+7"])
GK = _hex(["0x1.5cc59050d3e66p+4", "0x1.9d7b4a2339c0fp+4"])
# Techo de cada comprador y piso de la hora (COP/kWh).
TECHO = _hex(["0x1.6d903afb7e910p+9"] * 2)
PISO = float.fromhex("0x1.3e2e147ae147ap+8")
HUELLA = "3d05c2c225d2e5c2"

T_CORTO = 0.001        # cubre el desborde del arranque de siempre, t = 7,2e-6
T_PRODUCCION = 0.05


def _huella(gn, dn, a, b, gk, techo, piso):
    m = hashlib.sha256()
    for v in (gn, dn, a, b, gk, techo):
        m.update(np.ascontiguousarray(v, dtype=np.float64).tobytes())
    m.update(np.float64(piso).tobytes())
    return m.hexdigest()[:16]


def _resuelve(arranque, t_fin, gn=GN, dn=DN):
    """La receta de H-84 y H-85: los parametros de produccion del acoplado.
    La tolerancia absoluta queda en su defecto de 1e-6 (H-51). Comprueba la
    huella antes de usar los literales, para que una prueba suelta
    (`-k rapida`) no los use sin comprobar."""
    assert _huella(GN, DN, A, B, GK, TECHO, PISO) == HUELLA, \
        "los literales de la hora 753 no son los de la huella"
    J, I = len(gn), len(dn)
    return solve_coupled_for_hour(
        G_net_j=gn, D_net_i=dn, a_j=A, b_j=B,
        lam_j=np.full(J, 100.0), theta_j=np.full(J, 0.5),
        G_klim_i=GK, lam_i=np.full(I, 100.0), theta_i=np.full(I, 0.5),
        etha_i=np.full(I, 0.1), pi_gs=TECHO, pi_gb=PISO,
        tau_sellers=0.001, tau_buyers=0.01, t_span=(0.0, t_fin),
        n_points=150, rtol=1e-6, buyer_competition="aggregate",
        arranque=arranque)


def _finita(tr):
    return all(np.all(np.isfinite(np.asarray(getattr(tr, c), dtype=float)))
               for c in ("pi_t", "P_t", "pi_star", "P_star", "W_t"))


# ─── la regla del arranque ─────────────────────────────────────────────────


def _de_siempre(G, D):
    """El arranque de antes de D45, copiado tal cual de las lineas que
    `_arranque_P0` reemplaza en `solve_coupled_for_hour`."""
    G = np.asarray(G, dtype=float)
    D = np.asarray(D, dtype=float)
    J, I = len(G), len(D)
    if float(np.sum(G)) >= float(np.sum(D)):
        P0 = np.tile(D / J, (J, 1))
    else:
        P0 = np.tile(G / I, (I, 1)).T
    return np.clip(P0, 1e-10, None)


# Los dos casos del mercado, cada uno dos veces: la oferta cubre la demanda
# (sum_G >= sum_D) o no. Uno de cada lado tiene un comprador de deficit muy
# pequeno, el que el arranque de siempre desborda.
CASOS = {
    "oferta_cubre": (np.array([5.0, 3.0]), np.array([1.0, 2.0, 0.5])),
    "oferta_cubre_deficit_pequeno": (np.array([4.2, 0.3, 7.1]),
                                     np.array([0.05, 6.0])),
    "demanda_cubre": (np.array([1.0, 0.5]), np.array([2.0, 3.0, 1.0])),
    "hora_753": (GN, DN),
}


@pytest.mark.parametrize("caso", list(CASOS))
def test_el_factible_cumple_las_dos_capacidades(caso):
    G, D = CASOS[caso]
    P0 = _arranque_P0(G, D, "factible")
    assert P0.shape == (len(G), len(D))
    assert np.all(P0 >= 1e-10)
    recibe, ofrece = P0.sum(axis=0), P0.sum(axis=1)
    holgura = 1e-12 * max(float(np.sum(G)), float(np.sum(D)))
    # Ningun comprador arranca con mas de su deficit (sumas por columna) y
    # ningun vendedor ofrece mas de su excedente (sumas por fila).
    assert np.all(recibe <= D + holgura), (recibe, D)
    assert np.all(ofrece <= G + holgura), (ofrece, G)
    # Y el lado corto se agota: el reparto no deja nada del lado corto sin
    # asignar al arrancar.
    if float(np.sum(G)) >= float(np.sum(D)):
        np.testing.assert_allclose(recibe, D, rtol=1e-12)
    else:
        np.testing.assert_allclose(ofrece, G, rtol=1e-12)


@pytest.mark.parametrize("caso", list(CASOS))
def test_iguales_reproduce_el_arranque_de_siempre_al_bit(caso):
    G, D = CASOS[caso]
    assert np.array_equal(_arranque_P0(G, D, "iguales"), _de_siempre(G, D))
    assert np.array_equal(_arranque_P0(G, D), _de_siempre(G, D))


def test_el_arranque_de_siempre_desborda_al_comprador_de_la_hora_753():
    # H-85: el comprador 1 (deficit 1,90 (kWh)) recibe 10,45 al empezar, 5,5
    # veces lo que necesita; con el factible, como mucho su deficit.
    recibe = _arranque_P0(GN, DN, "iguales").sum(axis=0)
    assert recibe[0] == pytest.approx(10.4486, abs=1e-4)
    assert recibe[0] > 5 * DN[0]
    assert np.all(_arranque_P0(GN, DN, "factible").sum(axis=0) <= DN)


class _Alto(Exception):
    """Detiene `solve_coupled_for_hour` justo al llamar al integrador."""


def _captura_X0(monkeypatch):
    """Sustituye el integrador del modulo por uno que guarda el estado
    inicial y se detiene sin integrar nada."""
    vistos = []

    def falso(fun, t_span, y0, **kw):
        vistos.append(np.array(y0, dtype=float, copy=True))
        raise _Alto()

    monkeypatch.setattr(ccc, "solve_ivp", falso)
    return vistos


def _estado_inicial(monkeypatch, G, D, **kw):
    vistos = _captura_X0(monkeypatch)
    J, I = len(G), len(D)
    with pytest.raises(_Alto):
        solve_coupled_for_hour(
            G_net_j=G, D_net_i=D, a_j=np.zeros(J), b_j=np.full(J, 225.0),
            lam_j=np.full(J, 100.0), theta_j=np.full(J, 0.5),
            G_klim_i=np.full(I, 5.0), lam_i=np.full(I, 100.0),
            theta_i=np.full(I, 0.5), etha_i=np.full(I, 0.1),
            pi_gs=1250.0, pi_gb=114.0, t_span=(0.0, 0.01), **kw)
    assert len(vistos) == 1
    X0 = vistos[0]
    i0 = (I + 1) + 2 * J
    return X0, X0[i0:i0 + J * I].reshape(J, I)


@pytest.mark.parametrize("caso", list(CASOS))
def test_solve_coupled_arranca_con_la_regla_pedida(monkeypatch, caso):
    # Con el defecto, el estado inicial que recibe el integrador lleva la
    # oferta de siempre, al bit; con "factible", la del reparto factible. El
    # resto del estado inicial (precios, filtros, multiplicadores) es el
    # mismo con las dos reglas.
    G, D = CASOS[caso]
    X0_defecto, P0_defecto = _estado_inicial(monkeypatch, G, D)
    X0_iguales, _ = _estado_inicial(monkeypatch, G, D, arranque="iguales")
    X0_factible, P0_factible = _estado_inicial(monkeypatch, G, D,
                                               arranque="factible")
    assert np.array_equal(P0_defecto, _de_siempre(G, D))
    assert np.array_equal(X0_defecto, X0_iguales)
    assert np.array_equal(P0_factible, _arranque_P0(G, D, "factible"))
    J, I = len(G), len(D)
    i0 = (I + 1) + 2 * J
    fuera_de_P = np.r_[0:i0, i0 + J * I:len(X0_defecto)]
    assert np.array_equal(X0_defecto[fuera_de_P], X0_factible[fuera_de_P])


def test_una_regla_desconocida_se_rechaza_en_voz_alta():
    G, D = CASOS["oferta_cubre"]
    with pytest.raises(ValueError, match="arranque"):
        _arranque_P0(G, D, "otro")
    J, I = len(G), len(D)
    comunes = dict(a_j=np.zeros(J), b_j=np.full(J, 225.0),
                   lam_j=np.full(J, 100.0), theta_j=np.full(J, 0.5),
                   G_klim_i=np.full(I, 5.0), lam_i=np.full(I, 100.0),
                   theta_i=np.full(I, 0.5), etha_i=np.full(I, 0.1))
    with pytest.raises(ValueError, match="arranque"):
        solve_coupled_for_hour(G_net_j=G, D_net_i=D, arranque="otro",
                               **comunes)
    # Tambien en la hora sin mercado, que vuelve antes de arrancar.
    with pytest.raises(ValueError, match="arranque"):
        solve_coupled_for_hour(G_net_j=np.zeros(J), D_net_i=D,
                               arranque="otro", **comunes)
    with pytest.raises(ValueError, match="arranque"):
        SolverParams(arranque_acoplado="otro")
    with pytest.raises(ValueError, match="arranque"):
        _run_hour_worker(_args29(_hora()) + ("otro",))
    # El factible sin oferta no devuelve un NaN: falla.
    with pytest.raises(ValueError, match="factible"):
        _arranque_P0(np.zeros(2), D, "factible")


# ─── el motor ──────────────────────────────────────────────────────────────

PGS, PGB = 1250.0, 114.0
T_ACO = 0.002          # horizonte corto para que corra en segundos
# Pisos por vendedor que retiran a sids[0] (el mercado le paga 500 < 600) y
# dejan a sids[1] (500 > 300), como en test_presupuesto_acoplado.py.
PISO_H43 = np.array([600.0, 300.0])


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


def _args29(h, pi_gb_j=None):
    """La tupla vieja de 29 campos de `_run_hour_worker`, via acoplada, con
    la parada apagada: la de antes de D45."""
    sv = SolverParams()
    return (h["k"], h["g_klim"], h["d_k"], h["g_k"], h["sids"], h["bids"],
            h["a"], h["b"], h["lam"], h["theta"], h["etha"],
            PGS, PGB, sv.tau, sv.tau_buyers, sv.t_span, sv.n_points,
            sv.stackelberg_iters, sv.stackelberg_tol, sv.stackelberg_max,
            sv.ode_method, sv.buyer_competition,
            "acoplado", T_ACO, pi_gb_j, False,
            1e-6, None, None)


def _directo(h, sv, arranque):
    sids, bids = h["sids"], h["bids"]
    return solve_coupled_for_hour(
        G_net_j=np.array([h["g_klim"][j] - h["d_k"][j] for j in sids]),
        D_net_i=np.array([h["d_k"][i] - h["g_klim"][i] for i in bids]),
        a_j=h["a"][sids], b_j=h["b"][sids], lam_j=h["lam"][sids],
        theta_j=h["theta"][sids], G_klim_i=h["g_klim"][bids],
        lam_i=h["lam"][bids], theta_i=h["theta"][bids],
        etha_i=h["etha"][bids], pi_gs=PGS, pi_gb=PGB, tau_sellers=sv.tau,
        tau_buyers=sv.tau_buyers, t_span=(0.0, T_ACO),
        n_points=sv.n_points, rtol=1e-6,
        buyer_competition=sv.buyer_competition, arranque=arranque)


def test_con_el_defecto_el_trabajador_da_lo_mismo_que_la_tupla_de_29_campos():
    # Alcance: el shim convierte la tupla de 29 campos en la de 30, de modo
    # que las dos llamadas corren el codigo nuevo; lo que esta prueba afirma
    # es que el shim rellena con «iguales». La identidad al bit con el
    # arranque de antes (D45) la prueban
    # `test_iguales_reproduce_el_arranque_de_siempre_al_bit` y
    # `test_solve_coupled_arranca_con_la_regla_pedida`, que captura el estado
    # inicial real que recibe el integrador.
    h = _hora()
    viejo = _run_hour_worker(_args29(h))
    nuevo = _run_hour_worker(_args29(h) + ("iguales",))
    assert viejo.P_star is not None and nuevo.P_star is not None
    assert np.array_equal(viejo.P_star, nuevo.P_star)
    assert np.array_equal(viejo.pi_star, nuevo.pi_star)
    for campo in ("motivo", "parada_acoplado", "horizonte_usado",
                  "iters_used", "norm_rel_final", "retirados"):
        assert getattr(viejo, campo) == getattr(nuevo, campo), campo


def test_el_factible_por_el_motor_es_identico_a_llamar_directo():
    h = _hora()
    N = h["a"].shape[0]
    sv = SolverParams(parallel=False, metodo="acoplado",
                      t_span_acoplado=T_ACO, arranque_acoplado="factible")
    directo = _directo(h, sv, "factible")
    assert directo.success, directo.message
    P_directo = np.asarray(directo.P_star, dtype=float)
    pi_directo = np.clip(np.asarray(directo.pi_star, dtype=float), PGB, PGS)
    # La prueba separa: en esta hora los dos arranques no dan lo mismo al
    # horizonte corto, de modo que un arranque que no viajara la haria
    # fallar.
    iguales = _directo(h, sv, "iguales")
    assert not (np.array_equal(np.asarray(iguales.P_star, dtype=float),
                               P_directo)
                and np.array_equal(np.asarray(iguales.pi_star, dtype=float),
                                   np.asarray(directo.pi_star, dtype=float)))

    ems = EMSP2P(
        agents=AgentParams(N=N, a=h["a"], b=h["b"], c=h["c"], lam=h["lam"],
                           theta=h["theta"], etha=h["etha"]),
        grid=GridParams(pi_gs=PGS, pi_gb=PGB), solver=sv)
    # `run_single_hour`, la via de diagnostico.
    res = ems.run_single_hour(h["k"], h["D"], h["G"])
    assert res.P_star is not None, res.motivo
    assert np.array_equal(res.P_star, P_directo)
    assert np.array_equal(res.pi_star, pi_directo)
    # El lote de `EMSP2P.run`, sobre una sola hora y sin paralelo.
    resultados, _, _ = ems.run(h["D"][:, [h["k"]]], h["G"][:, [h["k"]]])
    assert len(resultados) == 1 and resultados[0].P_star is not None
    assert np.array_equal(resultados[0].P_star, P_directo)
    assert np.array_equal(resultados[0].pi_star, pi_directo)


def _espia(monkeypatch):
    """Sustituye el integrador del motor por uno que anota, en cada llamada,
    cuantos vendedores trae y con que arranque, y devuelve una trayectoria
    fabricada con precio final 500 (COP/kWh) para todos los compradores."""
    vistos = []

    def falso(**kw):
        J, I = len(kw["G_net_j"]), len(kw["D_net_i"])
        vistos.append((J, kw["arranque"]))
        pi_t = np.tile(np.linspace(300.0, 500.0, 20), (I, 1))
        return SimpleNamespace(P_star=np.full((J, I), 0.01),
                               pi_star=pi_t[:, -1].copy(), pi_t=pi_t,
                               success=True, nfev=10, njev=0,
                               message="fabricada")

    monkeypatch.setattr(motor, "solve_coupled_for_hour", falso)
    return vistos


def test_la_regla_viaja_por_los_tres_sitios_que_arman_la_tupla(monkeypatch):
    h = _hora()
    assert len(h["sids"]) == 2, "esta prueba necesita dos vendedores"
    vistos = _espia(monkeypatch)
    # La recursion de H-43: el piso retira a un vendedor y el conjunto
    # reducido se resuelve con el mismo arranque.
    res = _run_hour_worker(_args29(h, pi_gb_j=PISO_H43) + ("factible",))
    assert res.retirados == [h["sids"][0]]
    assert vistos == [(2, "factible"), (1, "factible")]

    N = h["a"].shape[0]
    agentes = AgentParams(N=N, a=h["a"], b=h["b"], c=h["c"], lam=h["lam"],
                          theta=h["theta"], etha=h["etha"])
    for regla, sv in (
            ("factible", SolverParams(parallel=False, metodo="acoplado",
                                      t_span_acoplado=T_ACO,
                                      arranque_acoplado="factible")),
            ("iguales", SolverParams(parallel=False, metodo="acoplado",
                                     t_span_acoplado=T_ACO))):
        ems = EMSP2P(agents=agentes, grid=GridParams(pi_gs=PGS, pi_gb=PGB),
                     solver=sv)
        # `run_single_hour`.
        vistos.clear()
        ems.run_single_hour(h["k"], h["D"], h["G"])
        assert vistos == [(2, regla)]
        # El lote de `EMSP2P.run`.
        vistos.clear()
        ems.run(h["D"][:, [h["k"]]], h["G"][:, [h["k"]]])
        assert vistos == [(2, regla)]


# ─── la hora 753, rapida ───────────────────────────────────────────────────


def test_los_literales_son_la_hora_753_al_bit():
    assert _huella(GN, DN, A, B, GK, TECHO, PISO) == HUELLA
    assert float(np.sum(GN)) < float(np.sum(DN))


def test_rapida_el_arranque_de_siempre_desborda_y_d41_lo_corta():
    with np.errstate(all="ignore"):
        tr = _resuelve("iguales", T_CORTO)
    print(f"    iguales: {tr.message}   evaluaciones {tr.nfev}")
    assert tr.success is False
    assert tr.message.startswith("lado derecho no finito en t=")
    # Solo el punto inicial: la hora no avanzo hasta el horizonte.
    assert tr.t.shape == (1,)


def test_rapida_el_factible_termina_sin_valores_no_finitos():
    tr = _resuelve("factible", T_CORTO)
    recibe = np.asarray(tr.P_star, dtype=float).sum(axis=0)
    print(f"    factible: precio {np.array2string(tr.pi_star, precision=4)}"
          f"   recibe {np.array2string(recibe, precision=6)} (kWh)"
          f"   evaluaciones {tr.nfev}")
    assert tr.success, tr.message
    assert _finita(tr)
    assert tr.t[-1] == T_CORTO


# ─── la hora 753, lenta ────────────────────────────────────────────────────


def test_lenta_el_factible_al_horizonte_de_produccion_resuelve_la_hora_753():
    # Unos 250 (s) en la maquina de trabajo. Las cifras son las del
    # experimento en memoria de H-85
    # (`outputs/run_2026-09-15_arranque_E4_h753.log`): 1 579 181
    # evaluaciones, precio 412,947 · 318,18 (COP/kWh), entregas
    # 1,8985 · 18,9987 (kWh).
    tr = _resuelve("factible", T_PRODUCCION)
    recibe = np.asarray(tr.P_star, dtype=float).sum(axis=0)
    print(f"    precio {np.array2string(tr.pi_star, precision=4)}"
          f"   recibe {np.array2string(recibe, precision=6)} (kWh)"
          f"   deficit {np.array2string(DN, precision=6)} (kWh)"
          f"   evaluaciones {tr.nfev}")
    assert tr.success, tr.message
    assert _finita(tr)
    assert tr.t[-1] == T_PRODUCCION
    assert np.all(recibe <= DN + 1e-6), (recibe, DN)
    assert recibe == pytest.approx([1.8985, 18.9987], abs=1e-3)
