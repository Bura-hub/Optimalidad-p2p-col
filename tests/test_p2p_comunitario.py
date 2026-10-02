"""
Pruebas de las funciones puras de `reformateo/documento/scripts/articulo/p2p_comunitario.py`
(el P2P comunitario: intercambio exento y residual al autogenerador colectivo;
Actividades 2.1 y 2.2).

Datos sintéticos y pequeños: no leen el canon ni escriben nada. Corren en
segundos:

    .venv/Scripts/python.exe -m pytest tests/test_p2p_comunitario.py -q
"""
from __future__ import annotations

import importlib.util
import warnings
from pathlib import Path

import numpy as np
import pytest

from scenarios.scenario_c4_creg101072 import run_c4_creg101072

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "p2p_comunitario", RAIZ / "reformateo" / "documento" / "scripts" / "articulo" / "p2p_comunitario.py")
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)


@pytest.fixture
def datos():
    rng = np.random.default_rng(11)
    N, T = 4, 96
    G = np.clip(rng.normal(5.0, 4.0, (N, T)), 0.0, None)
    D = np.clip(rng.normal(4.0, 2.0, (N, T)), 0.0, None)
    CU = rng.uniform(600.0, 800.0, (N, T))
    pb = rng.uniform(80.0, 500.0, T)
    mes = np.repeat([0, 1, 2], T // 3)
    Cv = np.repeat(rng.uniform(30.0, 50.0, (N, 1)), T, axis=1)
    Th = np.repeat(rng.uniform(200.0, 300.0, (N, 1)), T, axis=1)
    s, d, au = np.maximum(G - D, 0.0), np.maximum(D - G, 0.0), np.minimum(G, D)
    # un intercambio factible: cada hora se transa el lado corto, repartido a prorrata
    tr = np.minimum(s.sum(0), d.sum(0))
    v = np.where(s.sum(0) > 0, s * tr / np.where(s.sum(0) > 0, s.sum(0), 1.0), 0.0)
    q = np.where(d.sum(0) > 0, d * tr / np.where(d.sum(0) > 0, d.sum(0), 1.0), 0.0)
    return dict(N=N, T=T, G=G, D=D, CU=CU, pb=pb, mes=mes, Cv=Cv, Th=Th, s=s, d=d, au=au, v=v, q=q)


def test_clasificacion_por_capacidad_instalada():
    assert pc.caso_art20_sin_10([17.55] * 5, 5)[0] == 1                       # E0
    assert pc.caso_art20_sin_10([122.85] * 5, 5)[:2] == (2, pytest.approx(122.85))  # E4
    assert pc.caso_art20_sin_10([175.5] * 5, 5)[0] == 2                       # E5
    caso, cin, suma = pc.caso_art20_sin_10([17.55, 17.55, 150.209928, 17.55, 17.55], 5)   # I1
    assert caso == 1 and cin == pytest.approx(44.081986) and suma == pytest.approx(220.409928)
    assert pc.caso_art20_sin_10([48.8076, 82.294, 150.2099, 75.7919, 71.0889], 5)[0] == 1  # N1
    assert pc.caso_art20_sin_10([17.55] * 4, 4)[0] == 1                       # SINU, cuatro fronteras
    assert pc.caso_art20_sin_10([100.0] * 5, 5)[0] == 1                       # el umbral incluye los 100 kW
    assert pc.caso_art20_sin_10([100.01] * 5, 5)[0] == 2
    # las fronteras que solo consumen bajan la CINAC (palanca legal del art. 18)
    assert pc.caso_art20_sin_10([122.85] * 5 + [0.0] * 6, 11)[:2] == (1, pytest.approx(614.25 / 11))
    assert pc.caso_art20_sin_10([40.0] * 20, 20)[0] == 1
    # pero la suma no puede pasar de 1 MW, por baja que sea la CINAC
    assert pc.caso_art20_sin_10([60.0] * 20, 20)[0] == 2                      # 1 200 kW > 1 MW
    assert pc.caso_art20_sin_10([90.0] * 12, 12)[0] == 2                      # 1 080 kW > 1 MW


def test_deduccion_del_caso(datos):
    Cv, Th = datos["Cv"], datos["Th"]
    assert np.array_equal(pc.deduccion_caso(1, 1.0, Cv, Th), Cv)
    assert np.array_equal(pc.deduccion_caso(1, 2.0, Cv, Th), 2.0 * Cv)
    assert np.array_equal(pc.deduccion_caso(2, 1.0, Cv, Th), Cv + Th)
    with pytest.raises(ValueError):
        pc.deduccion_caso(3, 1.0, Cv, Th)


def test_pagos_internos_suman_cero_con_techo():
    ags = ["a", "b", "c"]
    P = pc.pagos_internos(["a", "a", "c"], ["b", "c", "b"], [0, 1, 1], [2.0, 1.0, 3.0],
                          [500.0, 900.0, 400.0], [700.0, 800.0, 450.0], ags, 2)
    assert np.allclose(P.sum(axis=0), 0.0)
    assert P[0, 0] == pytest.approx(1000.0) and P[1, 0] == pytest.approx(-1000.0)
    assert P[0, 1] == pytest.approx(800.0)              # el precio se recorta al techo del comprador
    assert P[2, 1] == pytest.approx(-800.0 + 1200.0)
    assert P[1, 1] == pytest.approx(-1200.0)


def test_pesos_proporcionales_con_mes_vacio():
    x = np.array([[1.0, 3.0, 0.0, 0.0], [3.0, 1.0, 0.0, 0.0]])
    w = pc.pesos_proporcionales(x, np.array([0, 0, 1, 1]))
    assert np.allclose(w[0], [0.5, 0.5]) and np.allclose(w[1], [0.5, 0.5])
    w = pc.pesos_proporcionales(np.array([[1.0, 0.0], [3.0, 0.0]]), np.array([0, 1]))
    assert np.allclose(w[0], [0.25, 0.75]) and np.allclose(w[1], [0.5, 0.5])


@pytest.mark.parametrize("caso", [1, 2])
def test_sin_intercambio_es_el_colectivo_de_produccion(datos, caso):
    """Con q = v = 0 y sin pagos, el P2P comunitario es C4 (run_c4_creg101072,
    monthly_hx, PDE igual) con la deducción del caso."""
    N, T = datos["N"], datos["T"]
    ded = pc.deduccion_caso(caso, 1.0, datos["Cv"], datos["Th"])
    cero = np.zeros((N, T))
    val, _ = pc.valor_comunitario(datos["au"], datos["s"], datos["d"], cero, cero, datos["CU"], cero, ded,
                                  datos["mes"], datos["pb"], pc.igual(N, datos["mes"]), "prueba")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = run_c4_creg101072(datos["D"], datos["G"], datos["CU"], datos["pb"], np.full(N, 1.0 / N), None,
                              component_c=ded, tolls=None, mode="monthly_hx", month_labels=datos["mes"],
                              caso=1, dt=1.0)
    ref = np.array([r["per_agent"][n]["net_benefit"] for n in range(N)])
    assert np.allclose(val, ref, rtol=0, atol=1e-6)


def test_el_precio_interno_solo_reparte(datos):
    """Los pagos internos cambian el reparto, no el total; el intercambio quita
    del fondo lo transado y el comprador ahorra su CU."""
    N, T, mes = datos["N"], datos["T"], datos["mes"]
    ded = pc.deduccion_caso(1, 1.0, datos["Cv"], datos["Th"])
    W = pc.igual(N, mes)
    rng = np.random.default_rng(3)
    pag = rng.normal(0.0, 100.0, (N, T))
    pag -= pag.mean(axis=0, keepdims=True)
    a, _ = pc.valor_comunitario(datos["au"], datos["s"], datos["d"], datos["v"], datos["q"], datos["CU"],
                                np.zeros((N, T)), ded, mes, datos["pb"], W, "sin pagos")
    b, _ = pc.valor_comunitario(datos["au"], datos["s"], datos["d"], datos["v"], datos["q"], datos["CU"],
                                pag, ded, mes, datos["pb"], W, "con pagos")
    assert a.sum() == pytest.approx(b.sum(), abs=1e-6)
    assert np.allclose(b - a, pag.sum(axis=1))
    # si se transa todo lo que se puede, el residual de un lado es cero en cada hora
    sr = np.maximum(datos["s"] - datos["v"], 0.0)
    dr = np.maximum(datos["d"] - datos["q"], 0.0)
    assert float(np.minimum(sr.sum(0), dr.sum(0)).max()) <= 1e-9


def test_descomposicion_cierra(datos):
    N, T, mes = datos["N"], datos["T"], datos["mes"]
    cero = np.zeros((N, T))
    W = pc.igual(N, mes)
    d1 = pc.deduccion_caso(1, 1.0, datos["Cv"], datos["Th"])
    d2 = pc.deduccion_caso(2, 1.0, datos["Cv"], datos["Th"])
    arg = (datos["au"], datos["s"], datos["d"])
    p2pcom = pc.valor_comunitario(*arg, datos["v"], datos["q"], datos["CU"], cero, d1, mes, datos["pb"], W, "p")[0].sum()
    c4s10 = pc.valor_comunitario(*arg, cero, cero, datos["CU"], cero, d1, mes, datos["pb"], W, "s")[0].sum()
    c4 = pc.valor_comunitario(*arg, cero, cero, datos["CU"], cero, d2, mes, datos["pb"], W, "c")[0].sum()
    assert c4s10 > c4                                     # quitar Θ no puede bajar el crédito
    assert (c4s10 - c4) + (p2pcom - c4s10) == pytest.approx(p2pcom - c4, abs=1e-6)


# ── Los dos órdenes y Shapley (añadido el 2026-10-02) ───────────────────────
def _cuatro(datos, caso):
    """(P2Pcom, C4 sin 10 %, C4, P2Pcom caso 2) de la comunidad con PDE igual."""
    N, T, mes = datos["N"], datos["T"], datos["mes"]
    cero = np.zeros((N, T))
    W = pc.igual(N, mes)
    ded = pc.deduccion_caso(caso, 1.0, datos["Cv"], datos["Th"])
    d2 = pc.deduccion_caso(2, 1.0, datos["Cv"], datos["Th"])
    arg = (datos["au"], datos["s"], datos["d"])

    def vc(v, q, dd):
        return pc.valor_comunitario(*arg, v, q, datos["CU"], cero, dd, mes, datos["pb"], W, "o")[0].sum()

    return vc(datos["v"], datos["q"], ded), vc(cero, cero, ded), vc(cero, cero, d2), vc(datos["v"], datos["q"], d2)


def test_dos_ordenes_y_shapley_cierran(datos):
    p2pcom, c4s10, c4, p2pcom_c2 = _cuatro(datos, 1)
    total = p2pcom - c4
    dir_s, dir_i = c4s10 - c4, p2pcom - c4s10
    inv_i, inv_s = p2pcom_c2 - c4, p2pcom - p2pcom_c2
    assert dir_s + dir_i == pytest.approx(total, abs=1e-6)
    assert inv_s + inv_i == pytest.approx(total, abs=1e-6)
    sh_s, sh_i = (dir_s + inv_s) / 2, (dir_i + inv_i) / 2
    assert sh_s + sh_i == pytest.approx(total, abs=1e-6)
    # la interacción es la diferencia entre los dos órdenes, igual para los dos términos
    assert inv_s - dir_s == pytest.approx(dir_i - inv_i, abs=1e-6)
    # con el intercambio, el residual pesa menos: quitar Θ vale menos si va después
    assert inv_s <= dir_s + 1e-9


def test_en_el_caso_2_los_ordenes_coinciden(datos):
    p2pcom, c4s10, c4, p2pcom_c2 = _cuatro(datos, 2)
    assert p2pcom_c2 == p2pcom and c4s10 == c4          # al peso: el mismo cálculo
    assert (c4s10 - c4) == 0.0 and (p2pcom - p2pcom_c2) == 0.0


def test_p2pcom_caso2_es_v01_con_reparto_igual(datos):
    """El P2P comunitario en el caso 2 (sin pagos, que suman cero) es v01 con el
    reparto igual del punto S (`esquinas`, v01_igual_min = v01_igual_max con la
    bolsa completa)."""
    N, T, mes = datos["N"], datos["T"], datos["mes"]
    d2 = pc.deduccion_caso(2, 1.0, datos["Cv"], datos["Th"])
    L = dict(c="prueba", s=datos["s"], d=datos["d"], v=datos["v"], q=datos["q"], CU=datos["CU"], mes=mes, N=N,
             au=datos["au"], ded1=pc.deduccion_caso(1, 1.0, datos["Cv"], datos["Th"]), ded4=d2, Th=datos["Th"])
    out, _ = pc.AS.esquinas(L, datos["pb"])
    p2pcom_c2 = _cuatro(datos, 1)[3]
    assert out["v01_igual_min"].sum() == pytest.approx(out["v01_igual_max"].sum(), abs=1e-9)
    assert p2pcom_c2 == pytest.approx(out["v01_igual_min"].sum(), abs=1e-6)


def test_clasifica_ordenes():
    M = 1e6                                               # en COP; la tolerancia es 1 COP
    assert pc.clasifica_ordenes(18.6 * M, 1.4 * M, 14.3 * M, 5.7 * M) == "sin10_domina"       # E1
    assert pc.clasifica_ordenes(1.66 * M, 0.33 * M, 0.39 * M, 1.60 * M) == "depende_orden"    # E0
    assert pc.clasifica_ordenes(1.04 * M, 0.33 * M, 0.0, 1.37 * M) == "depende_orden"         # K1
    assert pc.clasifica_ordenes(0.0, 5.55 * M, 0.0, 5.55 * M) == "solo_intercambio"           # E4
    assert pc.clasifica_ordenes(0.2 * M, 3.0 * M, 0.1 * M, 3.1 * M) == "intercambio_domina"
    assert pc.clasifica_ordenes(0.4, 3.0 * M, -0.3, 3.0 * M) == "solo_intercambio"           # a menos de 1 COP
    with pytest.raises(ValueError):
        pc.clasifica_ordenes(float("nan"), 1.0, 1.0, 1.0)
