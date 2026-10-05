"""
Pruebas de las funciones puras de `reformateo/documento/scripts/articulo/hibrido_por_planta.py`
(el híbrido H1, autogenerador colectivo de crédito mutualizado con la deducción
por la planta de origen, y H2; Actividades 2.1 y 2.2).

Datos sintéticos y pequeños: no leen el canon ni escriben nada. Corren en
segundos:

    .venv/Scripts/python.exe -m pytest tests/test_hibrido_por_planta.py -q
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "hibrido_por_planta", RAIZ / "reformateo" / "documento" / "scripts" / "articulo" / "hibrido_por_planta.py")
hb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hb)
AS, PC = hb.AS, hb.PC


@pytest.fixture
def datos():
    rng = np.random.default_rng(23)
    N, T = 4, 96
    G = np.clip(rng.normal(5.0, 4.0, (N, T)), 0.0, None)
    D = np.clip(rng.normal(4.0, 2.0, (N, T)), 0.0, None)
    mes = np.repeat([0, 1, 2], T // 3)
    # tarifas constantes en el mes, como el almacén
    CU = np.repeat(rng.uniform(600.0, 800.0, (N, 3)), T // 3, axis=1)
    Cv = np.repeat(rng.uniform(30.0, 50.0, (N, 3)), T // 3, axis=1)
    Th = np.repeat(rng.uniform(200.0, 300.0, (N, 3)), T // 3, axis=1)
    pb = rng.uniform(80.0, 500.0, T)
    s, d, au = np.maximum(G - D, 0.0), np.maximum(D - G, 0.0), np.minimum(G, D)
    tr = np.minimum(s.sum(0), d.sum(0))
    v = np.where(s.sum(0) > 0, s * tr / np.where(s.sum(0) > 0, s.sum(0), 1.0), 0.0)
    q = np.where(d.sum(0) > 0, d * tr / np.where(d.sum(0) > 0, d.sum(0), 1.0), 0.0)
    return dict(N=N, T=T, G=G, D=D, CU=CU, Cv=Cv, Th=Th, pb=pb, mes=mes, s=s, d=d, au=au, v=v, q=q)


def test_numeral_por_capacidad_instalada():
    assert list(hb.numeral_planta([17.55, 100.0, 100.01, 150.209928, 0.0])) == [1, 1, 2, 2, 1]
    with pytest.raises(ValueError):
        hb.numeral_planta([10.0, -1.0])
    with pytest.raises(ValueError):
        hb.numeral_planta([10.0, np.nan])


def test_formula_primero_lo_propio(datos):
    s, d, mes, N = datos["s"], datos["d"], datos["mes"], datos["N"]
    W, TR = hb.pde_primero_propio(s, d, mes)
    for m, t in TR.items():
        assert W[m].sum() == pytest.approx(1.0) and (W[m] >= 0).all()
        assert t["asignado"].sum() == pytest.approx(t["S"].sum())
        assert t["cedido"].sum() == pytest.approx(t["recibido"].sum())
        assert (t["recibido"] <= t["R"] + 1e-9).all() and (t["cedido"] <= t["X"] + 1e-9).all()
        # primero lo propio: nadie queda con menos de mín(S, D)
        assert (t["asignado"] >= np.minimum(t["S"], t["D"]) - 1e-9).all()
    # nadie agota: el reparto es la propia inyección
    W2, TR2 = hb.pde_primero_propio(s, d + 50.0, mes)
    for m, t in TR2.items():
        assert np.allclose(t["asignado"], t["S"]) and np.allclose(t["cedido"], 0.0)
    # sobrante de la comunidad: los que importan quedan justo en su importación, el resto vuelve a quien sobra
    S_h = np.array([[10.0, 10.0], [0.0, 0.0], [1.0, 1.0]])
    D_h = np.array([[2.0, 2.0], [3.0, 3.0], [1.0, 1.0]])
    _, t = hb.pde_primero_propio(S_h, D_h, np.array([0, 0]))
    t = t[0]
    assert np.allclose(t["asignado"], [14.0, 6.0, 2.0]) and np.allclose(t["cedido"], [6.0, 0.0, 0.0])
    assert np.allclose(t["devuelto"], [10.0, 0.0, 0.0])
    # un mes sin inyección cae al reparto igual
    W0, _ = hb.pde_primero_propio(np.zeros((N, 4)), np.ones((N, 4)), np.zeros(4, dtype=int))
    assert np.allclose(W0[0], 1.0 / N)
    with pytest.raises(ValueError):
        hb.pde_primero_propio(-s, d, mes)


def test_traza_del_origen():
    # miembro 0 (numeral 2) con sobrante, 1 y 2 (numeral 1) que importan
    S_h = np.array([[10.0], [0.0], [1.0]])
    D_h = np.array([[2.0], [6.0], [3.0]])
    n2 = np.array([1.0, 0.0, 0.0])
    _, TR = hb.pde_primero_propio(S_h, D_h, np.array([0]))
    f = hb.fraccion_numeral2_traza(TR, n2)[0]
    # 0: propio 2 de su planta; 1: recibe 8·6/8 = 6 del sobrante, todo del 0; 2: propio 1 y recibe 2 del 0
    assert f == pytest.approx([1.0, 1.0, 2.0 / 3.0])
    # sin plantas mixtas la fracción es 0 o 1 exactos
    for n in (np.zeros(3), np.ones(3)):
        g = hb.fraccion_numeral2_traza(TR, n)[0]
        assert np.array_equal(g, n)
    mz = hb.fraccion_numeral2_mezcla(S_h, n2, np.array([0]))[0]
    assert mz == pytest.approx(np.full(3, 10.0 / 11.0))


def test_deduccion_por_origen_es_la_del_caso_al_bit(datos):
    Cv, Th, mes, N = datos["Cv"], datos["Th"], datos["mes"], datos["N"]
    for kap in (1.0, 2.0):
        for caso, x in ((1, 0.0), (2, 1.0)):
            fr = {m: np.full(N, x) for m in np.unique(mes)}
            assert np.array_equal(hb.ded_por_origen(fr, kap, Cv, Th, mes), PC.deduccion_caso(caso, kap, Cv, Th))
    fr = {m: np.full(N, 0.25) for m in np.unique(mes)}
    assert np.allclose(hb.ded_por_origen(fr, 1.0, Cv, Th, mes), Cv + 0.25 * Th)


def test_colectivo_con_traza_es_el_del_motor(datos):
    s, d, CU, Cv, mes, pb, N = datos["s"], datos["d"], datos["CU"], datos["Cv"], datos["mes"], datos["pb"], datos["N"]
    W, _ = hb.pde_primero_propio(s, d, mes)
    val, cr, ex, asg = hb.colectivo_traza(s, d, CU, Cv, mes, pb, W, "prueba")
    ref, ex_ref = AS.colectivo(s, d, CU, Cv, mes, pb, W, "prueba")
    assert np.array_equal(val, ref) and np.array_equal(ex, ex_ref)
    assert np.allclose(cr + ex, asg) and np.allclose(asg.sum(axis=0), s.sum(axis=0))


def test_cargo_del_intercambio(datos):
    q, Cv, Th = datos["q"], datos["Cv"], datos["Th"]
    q1, q2 = 0.3 * q, 0.7 * q
    assert np.array_equal(hb.cargo_intercambio(q1, q2, 1.0, Cv, Th, "exento"), np.zeros_like(Cv))
    assert np.allclose(hb.cargo_intercambio(q1, q2, 2.0, Cv, Th, "H1"), q1 * 2 * Cv + q2 * (2 * Cv + Th))
    assert np.allclose(hb.cargo_intercambio(q1, q2, 1.0, Cv, Th, "H2"), q2 * (Cv + Th))
    assert np.allclose(hb.cargo_intercambio(q1, q2, 1.0, Cv, Th, "H2theta"), q2 * Th)
    with pytest.raises(ValueError):
        hb.cargo_intercambio(q1, q2, 1.0, Cv, Th, "otra")
    ags = ["a", "b", "c"]
    q1_, q2_ = hb.compras_por_numeral(["a", "c", "a"], ["b", "b", "c"], [0, 0, 1], [1.0, 2.0, 3.0],
                                      {"a": 1, "b": 1, "c": 2}, ags, 2)
    assert q1_[1, 0] == 1.0 and q2_[1, 0] == 2.0 and q1_[2, 1] == 3.0 and q1_.sum() + q2_.sum() == 6.0


def test_con_el_intercambio_exento_es_el_p2p_colectivo(datos):
    x = datos
    N, mes = x["N"], x["mes"]
    W = PC.igual(N, mes)
    pag = np.zeros((N, x["T"]))
    ded = PC.deduccion_caso(1, 1.0, x["Cv"], x["Th"])
    h = hb.valor_hibrido(x["au"], x["s"], x["d"], x["v"], x["q"], x["CU"], pag, np.zeros_like(pag), ded, mes,
                         x["pb"], W, "prueba")
    ref, _ = PC.valor_comunitario(x["au"], x["s"], x["d"], x["v"], x["q"], x["CU"], pag, ded, mes, x["pb"], W, "prueba")
    assert np.array_equal(h["val"], ref)


def test_h2_con_la_formula_es_el_mercado_si_nadie_agota(datos):
    x = datos
    d = x["d"] + 20.0                      # nadie agota su cupo residual en ningún mes
    sr, dr = np.maximum(x["s"] - x["v"], 0.0), np.maximum(d - x["q"], 0.0)
    W, TR = hb.pde_primero_propio(sr, dr, x["mes"])
    assert all(np.allclose(t["cedido"], 0.0) for t in TR.values())
    ded1 = PC.deduccion_caso(1, 1.0, x["Cv"], x["Th"])
    pag = np.zeros((x["N"], x["T"]))
    h = hb.valor_hibrido(x["au"], x["s"], d, x["v"], x["q"], x["CU"], pag, np.zeros_like(pag), ded1, x["mes"],
                         x["pb"], W, "prueba")
    mercado = (x["au"] * x["CU"] + x["CU"] * x["q"] + pag
               + AS.art25(sr, dr, x["CU"], ded1, x["mes"], x["pb"], "prueba")[0]).sum(axis=1)
    assert np.allclose(h["val"], mercado, rtol=0, atol=1e-6)


def test_compensacion_suma_cero(datos):
    s, d, mes, pb = datos["s"], datos["d"], datos["mes"], datos["pb"]
    _, TR = hb.pde_primero_propio(s, d, mes)
    pre = hb.precio_compensacion(s, pb, mes)
    assert all(pb.min() - 1e-9 <= p <= pb.max() + 1e-9 for p in pre.values())
    comp = hb.compensacion(TR, pre)
    assert abs(comp.sum()) <= 1e-6 * max(1.0, np.abs(comp).sum())


def test_descomposicion_cierra():
    r = hb.descomposicion(128.0, 115.0, 116.0, 125.0)
    assert r["total"] == 13.0
    assert r["fondo_fondo_primero"] + r["numeral_fondo_primero"] == pytest.approx(13.0)
    assert r["numeral_numeral_primero"] + r["fondo_numeral_primero"] == pytest.approx(13.0)
    assert r["fondo_shapley"] + r["numeral_shapley"] == pytest.approx(13.0)
    assert r["interaccion"] == pytest.approx(r["fondo_numeral_primero"] - r["fondo_fondo_primero"])
    with pytest.raises(ValueError):
        hb.descomposicion(np.nan, 1.0, 1.0, 1.0)
