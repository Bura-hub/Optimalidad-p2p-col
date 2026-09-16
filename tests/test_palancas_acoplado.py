"""
Las dos palancas del acoplado, D35 y D26 (2026-09-14).

La sonda de H-79 corre en el servidor antes de la matriz de 13 corridas y
decide, para cada hora, si el reparto o el excedente dependen del
integrador. Si la palanca es la tolerancia relativa, produccion la aprieta
a 1e-7 (D35); si es el horizonte, el acoplado para por estacionario en vez
de horizonte fijo (D26). Las dos existen ya como opciones de `SolverParams`,
apagadas por defecto e identicas al bit a como estaba antes de esta tarea.

Esta prueba NO corre el lazo paralelo ni multiproceso: cada caso resuelve
una sola hora con `_run_hour_worker` (o el ayudante `_resuelve_acoplado`
que este ya usa por dentro), sobre el caso sintetico de la compuerta C-165
(`gate_c165_desglose_horario._caso`), para que corra en segundos.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import core.ems_p2p as ems_p2p_mod  # noqa: E402
from core.ems_p2p import (  # noqa: E402
    SolverParams, AgentParams, GridParams, EMSP2P,
    _run_hour_worker, _resuelve_acoplado,
)
from core.coupled_ode_convergence import solve_coupled_for_hour  # noqa: E402
from core.market_prep import compute_generation_limit, classify_agents  # noqa: E402
from gate_c165_desglose_horario import _caso  # noqa: E402

PGS, PGB = 1250.0, 114.0
SV = SolverParams(tau=0.001, tau_buyers=0.01, t_span=(0.0, 0.005),
                  n_points=120, metodo="acoplado", t_span_acoplado=0.02)


def _hora_con_mercado():
    """La primera hora del caso sintetico de C-165 con vendedores y
    compradores a la vez (pocas horas, rapido). Guarda tambien las series
    D, G completas y `c`, para poder armar `AgentParams`/`EMSP2P` y ejercer
    la construccion de la tupla en produccion (`EMSP2P.run_single_hour` y
    `EMSP2P.run`), no solo `_run_hour_worker` a mano."""
    D, G = _caso(T=24)
    N = D.shape[0]
    a = np.zeros(N); b = np.full(N, 225.0); c = np.zeros(N)
    lam = np.full(N, 100.0); theta = np.full(N, 0.5); etha = np.full(N, 0.1)
    for k in range(D.shape[1]):
        g_klim = compute_generation_limit(G[:, k], a, b, c, PGS)
        _, sids, bids = classify_agents(g_klim, D[:, k])
        if sids and bids:
            return dict(k=k, g_klim=g_klim, d_k=D[:, k].copy(),
                       g_k=G[:, k].copy(), sids=sids, bids=bids,
                       a=a, b=b, c=c, lam=lam, theta=theta, etha=etha,
                       D=D, G=G)
    raise RuntimeError("ninguna hora del caso sintetico de C-165 tiene "
                       "vendedores y compradores a la vez")


def _args(h, rtol_aco=1e-6, horizonte_max_aco=None, pi_gb_j=None):
    """La tupla de `_run_hour_worker` para la hora de `_hora_con_mercado`,
    con las dos palancas al final (D35, D26). `pi_gb_j=None` (defecto) deja
    inerte la restriccion de participacion (H-43); con un vector no uniforme
    la activa (ronda de arreglo 3)."""
    return (h["k"], h["g_klim"], h["d_k"], h["g_k"], h["sids"], h["bids"],
            h["a"], h["b"], h["lam"], h["theta"], h["etha"],
            PGS, PGB, SV.tau, SV.tau_buyers, SV.t_span, SV.n_points,
            SV.stackelberg_iters, SV.stackelberg_tol, SV.stackelberg_max,
            SV.ode_method, SV.buyer_competition,
            SV.metodo, SV.t_span_acoplado, pi_gb_j, False,
            rtol_aco, horizonte_max_aco)


def _redes(h):
    """G_net_j / D_net_i de la hora, como los arma `_run_hour_worker`."""
    g_klim, d_k, sids, bids = h["g_klim"], h["d_k"], h["sids"], h["bids"]
    G_net_j = np.array([g_klim[j] - d_k[j] for j in sids])
    D_net_i = np.array([d_k[i] - g_klim[i] for i in bids])
    return G_net_j, D_net_i


def test_valores_por_defecto_dan_una_sola_resolucion_al_horizonte_de_produccion():
    # Bullet 3 del brief: con los valores por defecto (rtol_acoplado=1e-6,
    # horizonte_max_acoplado=None) el resultado es identico al de la tupla
    # vieja de 26 campos, de antes de que existieran las dos palancas, y
    # `horizonte_usado` es el horizonte de produccion (t_span_acoplado).
    h = _hora_con_mercado()
    args_de_siempre = _args(h)[:26]           # tupla anterior a D35/D26
    res_de_siempre = _run_hour_worker(args_de_siempre)
    res_con_defecto = _run_hour_worker(_args(h))

    assert res_con_defecto.P_star is not None
    assert np.array_equal(res_de_siempre.P_star, res_con_defecto.P_star)
    assert np.array_equal(res_de_siempre.pi_star, res_con_defecto.pi_star)
    assert res_con_defecto.horizonte_usado == SV.t_span_acoplado


def test_rtol_acoplado_activo_es_identico_a_llamar_directo():
    # Bullet 1 del brief: con rtol_acoplado=1e-7 el resultado de la hora es
    # identico (np.array_equal) al de llamar directo a
    # solve_coupled_for_hour(..., rtol=1e-7).
    h = _hora_con_mercado()
    res = _run_hour_worker(_args(h, rtol_aco=1e-7))
    assert res.P_star is not None

    G_net_j, D_net_i = _redes(h)
    tr = solve_coupled_for_hour(
        G_net_j=G_net_j, D_net_i=D_net_i,
        a_j=h["a"][h["sids"]], b_j=h["b"][h["sids"]],
        lam_j=h["lam"][h["sids"]], theta_j=h["theta"][h["sids"]],
        G_klim_i=h["g_klim"][h["bids"]], lam_i=h["lam"][h["bids"]],
        theta_i=h["theta"][h["bids"]], etha_i=h["etha"][h["bids"]],
        pi_gs=PGS, pi_gb=PGB, tau_sellers=SV.tau, tau_buyers=SV.tau_buyers,
        t_span=(0.0, SV.t_span_acoplado), n_points=SV.n_points, rtol=1e-7,
        buyer_competition=SV.buyer_competition)

    assert np.array_equal(res.P_star, np.asarray(tr.P_star, dtype=float))
    assert np.array_equal(
        res.pi_star, np.clip(np.asarray(tr.pi_star, dtype=float), PGB, PGS))


def test_horizonte_max_acoplado_dobla_y_es_identico_al_resolver_directo():
    # Bullet 2 del brief: con horizonte_max_acoplado activo y la tolerancia
    # de estacionario forzada a cero, una hora se resuelve con el horizonte
    # doble, y su resultado es identico al de resolverla directamente con
    # ese horizonte; horizonte_usado (aqui, `h` de `_resuelve_acoplado`, que
    # es exactamente lo que `_run_hour_worker` copia a
    # `HourlyResult.horizonte_usado`) lo dice.
    #
    # `tol_estacionario=0.0` fuerza la parada a nunca disparar antes del
    # tope: es un argumento con valor por defecto de `_resuelve_acoplado`
    # (por defecto, la constante de modulo TOL_ESTACIONARIO), no una
    # mutacion de esa constante.
    h = _hora_con_mercado()
    G_net_j, D_net_i = _redes(h)
    horizonte_max = 2.0 * SV.t_span_acoplado

    kwargs_comunes = dict(
        G_net_j=G_net_j, D_net_i=D_net_i,
        a_j=h["a"][h["sids"]], b_j=h["b"][h["sids"]],
        lam_j=h["lam"][h["sids"]], theta_j=h["theta"][h["sids"]],
        G_klim_i=h["g_klim"][h["bids"]], lam_i=h["lam"][h["bids"]],
        theta_i=h["theta"][h["bids"]], etha_i=h["etha"][h["bids"]],
        pi_gs=PGS, pi_gb=PGB, tau_sellers=SV.tau, tau_buyers=SV.tau_buyers,
        n_points=SV.n_points, buyer_competition=SV.buyer_competition,
    )

    # D36: `_resuelve_acoplado` devuelve ademas por que paro.
    tr, horizonte_usado, parada, _gastado = _resuelve_acoplado(
        G_net_j=G_net_j, D_net_i=D_net_i,
        a_j=h["a"][h["sids"]], b_j=h["b"][h["sids"]],
        lam_j=h["lam"][h["sids"]], theta_j=h["theta"][h["sids"]],
        G_klim_i=h["g_klim"][h["bids"]], lam_i=h["lam"][h["bids"]],
        theta_i=h["theta"][h["bids"]], etha_i=h["etha"][h["bids"]],
        pi_gs=PGS, pi_gb=PGB, tau=SV.tau, tau_buyers=SV.tau_buyers,
        n_points=SV.n_points, buyer_competition=SV.buyer_competition,
        guarda_tr=False, t_span_aco=SV.t_span_acoplado,
        rtol_aco=SV.rtol_acoplado, horizonte_max_aco=horizonte_max,
        tol_estacionario=0.0)

    # Una sola vuelta: nunca estacionario (tol forzada a cero) y el segundo
    # horizonte ya pasa el tope, de modo que para exactamente en el doble.
    assert horizonte_usado == horizonte_max
    assert parada == "tope"

    directo = solve_coupled_for_hour(
        t_span=(0.0, horizonte_max), rtol=SV.rtol_acoplado,
        **kwargs_comunes)

    assert np.array_equal(np.asarray(tr.P_star, dtype=float),
                          np.asarray(directo.P_star, dtype=float))
    assert np.array_equal(np.asarray(tr.pi_star, dtype=float),
                          np.asarray(directo.pi_star, dtype=float))


def test_palancas_activas_en_produccion_via_EMSP2P_run_single_hour():
    # Ronda de arreglo 1: las pruebas anteriores arman la tupla de
    # `_run_hour_worker` a mano; ninguna pasa por la construccion real de
    # produccion (`EMSP2P.run_single_hour`, que arma esa misma tupla desde
    # `SolverParams`). Esta prueba si, con las dos palancas ACTIVAS a la vez
    # (rtol_acoplado=1e-7, horizonte_max_acoplado = el doble del horizonte
    # de produccion), y compara contra la misma llamada directa que usan las
    # pruebas 2 y 3.
    #
    # No fuerza `tol_estacionario`: con la TOL_ESTACIONARIO real (0,01), esta
    # hora (comprobado) no esta en estacionario al horizonte de produccion,
    # de modo que la parada dobla una vez y llega exactamente al tope, igual
    # que la prueba anterior con la tolerancia forzada a cero.
    h = _hora_con_mercado()
    N = h["a"].shape[0]
    horizonte_max = 2.0 * SV.t_span_acoplado
    sv_activo = SolverParams(
        tau=SV.tau, tau_buyers=SV.tau_buyers, t_span=SV.t_span,
        n_points=SV.n_points, stackelberg_iters=SV.stackelberg_iters,
        parallel=False, metodo="acoplado", t_span_acoplado=SV.t_span_acoplado,
        rtol_acoplado=1e-7, horizonte_max_acoplado=horizonte_max)

    G_net_j, D_net_i = _redes(h)
    directo = solve_coupled_for_hour(
        G_net_j=G_net_j, D_net_i=D_net_i,
        a_j=h["a"][h["sids"]], b_j=h["b"][h["sids"]],
        lam_j=h["lam"][h["sids"]], theta_j=h["theta"][h["sids"]],
        G_klim_i=h["g_klim"][h["bids"]], lam_i=h["lam"][h["bids"]],
        theta_i=h["theta"][h["bids"]], etha_i=h["etha"][h["bids"]],
        pi_gs=PGS, pi_gb=PGB, tau_sellers=SV.tau, tau_buyers=SV.tau_buyers,
        t_span=(0.0, horizonte_max), n_points=SV.n_points, rtol=1e-7,
        buyer_competition=SV.buyer_competition,
        # D45 (2026-09-16): `SolverParams` arranca con el reparto factible y
        # `solve_coupled_for_hour` conserva el del modelo base, de modo que la
        # comparacion tiene que pedir el de produccion para comparar lo mismo.
        # Lo que esta prueba mide son las PALANCAS, no el arranque.
        arranque=sv_activo.arranque_acoplado)
    pi_directo = np.clip(np.asarray(directo.pi_star, dtype=float), PGB, PGS)

    # (a) `run_single_hour`: una hora suelta, la misma via de diagnostico
    # que ya honra las cotas de `GridParams`.
    ems = EMSP2P(
        agents=AgentParams(N=N, a=h["a"], b=h["b"], c=h["c"], lam=h["lam"],
                           theta=h["theta"], etha=h["etha"]),
        grid=GridParams(pi_gs=PGS, pi_gb=PGB),
        solver=sv_activo,
    )
    res_single = ems.run_single_hour(h["k"], h["D"], h["G"])
    assert res_single.P_star is not None
    assert res_single.horizonte_usado == horizonte_max
    assert np.array_equal(res_single.P_star,
                          np.asarray(directo.P_star, dtype=float))
    assert np.array_equal(res_single.pi_star, pi_directo)

    # (b) `EMSP2P.run`, el lote real de produccion (`jobs.append(...)`),
    # sobre una sola hora y sin paralelo, para que corra en segundos: se
    # comprueba tambien, no solo `run_single_hour`.
    D_una_hora = h["D"][:, [h["k"]]]
    G_una_hora = h["G"][:, [h["k"]]]
    resultados, _, _ = ems.run(D_una_hora, G_una_hora)
    assert len(resultados) == 1
    res_lote = resultados[0]
    assert res_lote.P_star is not None
    assert res_lote.horizonte_usado == horizonte_max
    assert np.array_equal(res_lote.P_star, np.asarray(directo.P_star, dtype=float))
    assert np.array_equal(res_lote.pi_star, pi_directo)


def test_excepcion_en_acoplado_no_tumba_la_hora_y_deja_motivo(monkeypatch):
    # Ronda de arreglo 2: fallar en voz alta (regla principal de CLAUDE.md,
    # fila "cifras que salen sin error pero son falsas"). Sin integrar de
    # verdad: se monkeypatchea `_resuelve_acoplado` (la funcion que
    # `_run_hour_worker` llama en la rama acoplada) para que reviente, y se
    # comprueba que la hora vuelve sin mercado pero con el motivo de la
    # excepcion, no muda.
    def _revienta(**kwargs):
        raise ValueError("boom de prueba")

    monkeypatch.setattr(ems_p2p_mod, "_resuelve_acoplado", _revienta)

    h = _hora_con_mercado()
    res = ems_p2p_mod._run_hour_worker(_args(h))

    assert res.P_star is None
    assert res.motivo.startswith("excepcion del acoplado")
    assert "ValueError" in res.motivo
    assert "boom de prueba" in res.motivo
    assert res.horizonte_usado == 0.0


def test_excepcion_en_reintento_de_h43_propaga_el_motivo(monkeypatch):
    # Ronda de arreglo 3: si el reintento de la restriccion de participacion
    # (H-43, conjunto reducido) revienta, su `motivo` tiene que subir al
    # marco exterior; si no, la hora vuelve "sin mercado" muda un nivel mas
    # arriba, el mismo fallo mudo que cierra C-190.
    #
    # Se fuerza la retirada con pisos por vendedor NO uniformes (`pi_gb_j`),
    # y se monkeypatchea `_resuelve_acoplado` (no `solve_coupled_for_hour`,
    # para no integrar de verdad) con una version que:
    #   - en la primera llamada (el conjunto completo, dos vendedores)
    #     fabrica una resolucion donde el vendedor 0 queda por debajo de su
    #     piso y el vendedor 1 por encima, para que H-43 retire solo al 0;
    #   - en la segunda llamada (el conjunto reducido, un solo vendedor,
    #     la de `sub = _run_hour_worker(...)`) revienta.
    # Las dos llamadas se distinguen por cuantos vendedores traen (`a_j`),
    # no por un contador, porque es la forma mas directa de identificar
    # "es la vuelta del conjunto reducido" sin acoplarse al orden de las
    # llamadas.
    h = _hora_con_mercado()
    assert len(h["sids"]) == 2, "esta prueba necesita dos vendedores en la hora"
    piso_v = np.array([600.0, 300.0])   # retira al vendedor sids[0], no al 1

    def _resuelve_acoplado_fake(**kwargs):
        J_local = len(kwargs["a_j"])
        if J_local == 2:
            # Conjunto completo: P_star fabricado, vendedor 0 vende solo al
            # comprador 0 (ingreso 500 < piso 600, se retira), vendedor 1
            # reparte entre los otros dos (ingreso 500 > piso 300, se queda).
            P_star = np.array([[5.0, 0.0, 0.0], [0.0, 2.5, 2.5]])
            pi_star = np.array([500.0, 500.0, 500.0])
            pi_t = np.tile(pi_star[:, None], (1, 10))
            # D47: la trayectoria fabricada lleva tambien `P_t`, como la de
            # verdad, porque el motor mide sobre ella el residuo del reparto.
            P_t = np.tile(P_star[:, :, None], (1, 1, 10))
            tr = SimpleNamespace(P_star=P_star, pi_star=pi_star, pi_t=pi_t,
                                P_t=P_t, success=True)
            # D36: `_resuelve_acoplado` devuelve ademas por que paro.
            return tr, kwargs["t_span_aco"], "una_vuelta", 0
        # Conjunto reducido (un solo vendedor): revienta.
        raise ValueError("boom del conjunto reducido")

    monkeypatch.setattr(ems_p2p_mod, "_resuelve_acoplado",
                        _resuelve_acoplado_fake)

    res = ems_p2p_mod._run_hour_worker(_args(h, pi_gb_j=piso_v))

    assert res.P_star is None
    assert res.motivo.startswith("excepcion del acoplado")
    assert "ValueError" in res.motivo
    assert "boom del conjunto reducido" in res.motivo
    assert res.horizonte_usado == 0.0
