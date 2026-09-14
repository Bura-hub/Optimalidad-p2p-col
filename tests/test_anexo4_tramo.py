"""Compuerta del tramo del Anexo 4 de la CREG 101 072 (C-175, C-177).

El corte hx es la primera hora en que la inyeccion acumulada desde el inicio
del mes alcanza la importacion TOTAL del mes. La inyeccion de esa hora se parte
y desde ahi todo es exceso. Las pruebas anteriores eran ciegas a la diferencia
con el criterio viejo (acumulado contra acumulado); la primera de estas no.
"""
import numpy as np
import pytest

from core.opciones_externas import (
    LIMITE_AGPE_KW, deduccion_art25, piso_residual, precio_permuta_por_periodo,
    reparto_anexo4, residual_proporcional, tramo_permuta,
)


def test_adelanto_que_se_revierte_es_todo_credito():
    # Hora 1 inyecta 2 sin haber importado; despues importa 40. Con el criterio
    # viejo todo lo posterior iba a bolsa; con el del mes, todo es credito.
    iny = np.array([[0.0, 2.0, 0.0, 0.0, 1.0]])
    ret = np.array([[0.0, 0.0, 20.0, 20.0, 0.0]])
    cred, exc, perm = reparto_anexo4(iny, ret)
    assert exc.sum() == 0.0
    np.testing.assert_array_equal(cred, iny)
    assert perm.all()


def test_hx_a_mano_parte_la_hora_del_corte():
    # Importacion del mes = 5. Inyeccion acumulada: 2, 4, 7 -> corte en k=2,
    # donde 2 de sus 3 kWh son exceso y 1 es credito.
    iny = np.array([[2.0, 2.0, 3.0, 4.0]])
    ret = np.array([[0.0, 0.0, 0.0, 0.0]])
    ret[0, 0] = 5.0
    cred, exc, perm = reparto_anexo4(iny, ret)
    np.testing.assert_allclose(exc, [[0.0, 0.0, 2.0, 4.0]])
    np.testing.assert_allclose(cred, [[2.0, 2.0, 1.0, 0.0]])
    np.testing.assert_array_equal(perm, [[True, True, False, False]])


def test_sin_importacion_el_corte_es_la_primera_hora_con_inyeccion():
    iny = np.array([[0.0, 3.0, 1.0]])
    ret = np.zeros((1, 3))
    cred, exc, perm = reparto_anexo4(iny, ret)
    np.testing.assert_allclose(exc, iny)
    np.testing.assert_array_equal(perm, [[True, False, False]])


def test_cada_mes_tiene_su_propio_corte():
    iny = np.array([[3.0, 3.0, 3.0, 3.0]])
    ret = np.array([[0.0, 4.0, 0.0, 10.0]])
    mes = np.array([1, 1, 2, 2])
    cred, exc, _ = reparto_anexo4(iny, ret, mes)
    # mes 1: cupo 4, acumulado 3, 6 -> exceso 2 en k=1
    # mes 2: cupo 10, acumulado 3, 6 -> sin exceso
    np.testing.assert_allclose(exc, [[0.0, 2.0, 0.0, 0.0]])
    np.testing.assert_allclose(cred + exc, iny)


def test_tramo_permuta_sobre_brutas_y_residuales():
    G = np.array([[5.0, 0.0], [0.0, 0.0]])
    D = np.array([[1.0, 1.0], [2.0, 2.0]])
    mes = np.array([1, 1])
    # Bruto: el agente 0 inyecta 4 e importa 1 -> corte en k=0.
    assert not tramo_permuta(G, D, mes)[0, 0]
    # Residual: coloca dentro el lado corto (2 de sus 4); inyecta 2 contra un
    # cupo de 1, sigue cortando en k=0.
    iny_r, ret_r = residual_proporcional(G, D)
    np.testing.assert_allclose(iny_r[:, 0], [2.0, 0.0])
    np.testing.assert_allclose(ret_r[:, 0], [0.0, 0.0])
    assert not tramo_permuta(G, D, mes, iny=iny_r, ret=ret_r)[0, 0]


def test_lectura_comercial_vender_todo_dentro_no_consume_cupo():
    # Spec, verificacion 2: el vendedor coloca todo su excedente dentro.
    G = np.array([[3.0, 0.0], [0.0, 0.0]])
    D = np.array([[1.0, 5.0], [2.0, 2.0]])
    iny_r, ret_r = residual_proporcional(G, D)
    assert iny_r[0, 0] == 0.0           # nada llega al comercializador
    assert ret_r[1, 0] == 0.0           # el comprador no importa lo que compro
    cred, exc, _ = reparto_anexo4(iny_r, ret_r)
    assert exc.sum() == 0.0


def test_deduccion_por_capacidad():
    cvm = np.full((3, 2), 40.0)
    tolls = np.full((3, 2), 300.0)
    ded = deduccion_art25(cvm, tolls, np.array([17.55, 98.3, 122.9]))
    np.testing.assert_allclose(ded[:, 0], [40.0, 40.0, 340.0])
    np.testing.assert_allclose(deduccion_art25(cvm, None, None), cvm)


def test_deduccion_exige_peajes_si_hay_planta_grande():
    with pytest.raises(ValueError, match="peajes"):
        deduccion_art25(np.full((1, 2), 40.0), None, np.array([122.9]))


def test_deduccion_rechaza_planta_fuera_de_agpe():
    with pytest.raises(ValueError, match="AGPE"):
        deduccion_art25(np.full((1, 2), 40.0), np.full((1, 2), 1.0),
                        np.array([LIMITE_AGPE_KW + 1.0]))


def test_precio_permuta_es_la_media_del_periodo():
    cu = np.array([[800.0, 900.0, 700.0, 700.0]])
    ded = np.array([[40.0, 60.0, 50.0, 50.0]])
    p = precio_permuta_por_periodo(cu, ded, np.array([1, 1, 2, 2]))
    np.testing.assert_allclose(p, [[800.0, 800.0, 650.0, 650.0]])


def test_piso_residual_permuta_antes_del_corte_y_bolsa_despues():
    G = np.array([[5.0, 5.0, 0.0], [0.0, 0.0, 0.0]])
    D = np.array([[0.0, 0.0, 30.0], [1.0, 1.0, 1.0]])
    cu = np.full((2, 3), 800.0)
    ded = np.full((2, 3), 40.0)
    bolsa = np.array([150.0, 160.0, 170.0])
    piso, perm = piso_residual(G, D, cu, ded, bolsa, np.array([1, 1, 1]))
    # Residual del agente 0: inyecta 4 y 4 contra un cupo de 30 -> permuta.
    np.testing.assert_allclose(piso[0], [760.0, 760.0, 760.0])
    assert perm[0].all()


def _c1_referencia_c175(surplus_h, deficit_h):
    """Copia congelada del bucle de C1 tras C-175, para la identidad al bit."""
    n_h = len(surplus_h)
    t1, t2 = np.zeros(n_h), np.zeros(n_h)
    cupo = float(np.sum(deficit_h))
    acum, hx = 0.0, None
    for k in range(n_h):
        acum += surplus_h[k]
        if hx is None:
            if acum > cupo:
                s2 = min(surplus_h[k], acum - cupo)
                t2[k], t1[k], hx = s2, surplus_h[k] - s2, k
            else:
                t1[k] = surplus_h[k]
        else:
            t2[k] = surplus_h[k]
    return t1, t2, hx


def test_c1_reproduce_al_bit_el_bucle_de_c175():
    from scenarios.scenario_c1_creg174 import run_c1_creg174
    rng = np.random.default_rng(11)
    N, T = 4, 24 * 6
    D = rng.uniform(0, 4, (N, T))
    G = rng.uniform(0, 6, (N, T))
    mes = np.repeat([1, 2, 3], 48)
    pi_gs = np.full((N, T), 810.0)
    pb = rng.uniform(80, 400, T)
    res = run_c1_creg174(D, G, pi_gs, pb, list(range(N)), mes,
                         component_c=45.0)
    for n in range(N):
        for m, mm in enumerate((1, 2, 3)):
            h = np.flatnonzero(mes == mm)
            Gh, Dh = np.maximum(G[n, h], 0), np.maximum(D[n, h], 0)
            a = np.minimum(Gh, Dh)
            _, t2, hx = _c1_referencia_c175(Gh - a, Dh - a)
            assert res[n]["hx_history"][m] == hx
        # Mismo orden de suma que C1: ahorros por periodo, ingresos por
        # periodo, y al final los dos totales.
        ahorro, ingreso = 0.0, 0.0
        for mm in (1, 2, 3):
            h = np.flatnonzero(mes == mm)
            Gh, Dh = np.maximum(G[n, h], 0), np.maximum(D[n, h], 0)
            a = np.minimum(Gh, Dh)
            t1, t2, _ = _c1_referencia_c175(Gh - a, Dh - a)
            ahorro += float(np.sum(a)) * 810.0 + float(np.sum(t1)) * 765.0
            ingreso += float(np.dot(t2, pb[h]))
        assert res[n]["net_benefit"] == ahorro + ingreso


def test_c1_numeral_2_con_planta_grande():
    from scenarios.scenario_c1_creg174 import run_c1_creg174
    D = np.full((2, 24), 3.0)
    G = np.zeros((2, 24)); G[:, 10:14] = 5.0          # 8 kWh de excedente
    pi_gs = np.full((2, 24), 800.0)
    pb = np.full(24, 200.0)
    r = run_c1_creg174(D, G, pi_gs, pb, [0, 1], component_c=40.0,
                       capacidad_kw=np.array([98.3, 122.9]),
                       tolls=np.full((2, 24), 300.0))
    # Todo es credito (importa 60 frente a 8 inyectados).
    assert r[0]["savings"] - r[1]["savings"] == pytest.approx(8.0 * 300.0)
