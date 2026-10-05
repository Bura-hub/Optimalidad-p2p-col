"""
Pruebas de las funciones puras de
`reformateo/documento/scripts/articulo/corte_fondo_derivados.py` (el corte hx
y el fondo del P2P colectivo, derivados sin simular; Actividades 2.1, 3.3 y
4.2; CANON §14.25).

Datos sintéticos y pequeños: no leen el canon ni escriben nada. Corren en
segundos:

    .venv/Scripts/python.exe -m pytest tests/test_corte_fondo_derivados.py -q
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "corte_fondo_derivados",
    RAIZ / "reformateo" / "documento" / "scripts" / "articulo" / "corte_fondo_derivados.py")
cf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cf)
AS = cf.AS


@pytest.fixture
def datos():
    rng = np.random.default_rng(11)
    N, T = 4, 90
    s = np.clip(rng.normal(3.0, 3.0, (N, T)), 0.0, None)
    d = np.clip(rng.normal(2.5, 2.0, (N, T)), 0.0, None)
    v = s * rng.uniform(0.0, 0.5, (N, T))
    q = d * rng.uniform(0.0, 0.5, (N, T))
    mes = np.repeat([0, 1, 2], T // 3)
    return dict(N=N, T=T, s=s, d=d, sr=s - v, dr=d - q, mes=mes)


def test_marca_corte_y_parte_suman_el_total():
    perm = np.array([[600.0, 600.0, 600.0], [500.0, 500.0, 500.0]])
    piso = np.array([[600.0, 600.004, 180.0], [500.0, 210.0, 210.0]])
    t = cf.marca_corte(piso, perm)
    assert t.tolist() == [[False, False, True], [False, True, True]]   # 0,004 < 0,01: sigue en la permuta
    x = np.arange(6.0).reshape(2, 3)
    antes, tras = cf.parte(x, t)
    assert antes == 0.0 + 1.0 + 3.0 and tras == 2.0 + 4.0 + 5.0
    assert antes + tras == x.sum()


def test_marca_corte_rechaza_no_finitos():
    with pytest.raises(SystemExit):
        cf.marca_corte(np.array([np.nan]), np.array([1.0]))


def test_ancho_y_energia_nula():
    assert cf.ancho(1000.0, 4.0) == 250.0
    assert math.isnan(cf.ancho(0.0, 0.0))          # sin energía no se define (no se rellena)
    with pytest.raises(SystemExit):
        cf.ancho(float("inf"), 1.0)


def test_fondo_energia_reproduce_el_colectivo_y_reparte_lo_aportado(datos):
    x = datos
    W = {m: np.full(x["N"], 1.0 / x["N"]) for m in np.unique(x["mes"])}
    A, cr, ex = cf.fondo_energia(x["sr"], x["dr"], x["mes"], W)
    # la misma energía que `atribucion_supuestos.colectivo` (que además valora)
    CU = np.full((x["N"], x["T"]), 700.0)
    _, ex_ref = AS.colectivo(x["sr"], x["dr"], CU, np.full_like(CU, 40.0), x["mes"], np.full(x["T"], 200.0), W, "prueba")
    assert np.allclose(ex, ex_ref, rtol=0, atol=1e-12)
    assert np.allclose(cr + ex, A)
    assert np.allclose(A.sum(axis=0), x["sr"].sum(axis=0))      # cada hora reparte lo aportado
    for m in np.unique(x["mes"]):                               # el crédito del mes es mín(asignado, importación)
        h = x["mes"] == m
        assert np.allclose(cr[:, h].sum(axis=1), np.minimum(A[:, h].sum(axis=1), x["dr"][:, h].sum(axis=1)))


def test_balance_fondo_neto_es_la_diferencia_de_exceso(datos):
    from core.opciones_externas import reparto_anexo4
    x = datos
    W = {m: np.full(x["N"], 1.0 / x["N"]) for m in np.unique(x["mes"])}
    A, crc, exc = cf.fondo_energia(x["sr"], x["dr"], x["mes"], W)
    crp, exp_, _ = reparto_anexo4(x["sr"], x["dr"], x["mes"])
    B = cf.balance_fondo(A, x["sr"], crc, crp, x["mes"])
    assert B["recibido"].sum() == pytest.approx(B["cedido"].sum(), abs=1e-9)
    assert (B["ganado"] >= -1e-12).all() and (B["perdido"] >= -1e-12).all()
    assert B["neto"].sum() == pytest.approx(exp_.sum() - exc.sum(), abs=1e-9)


def test_balance_fondo_caso_a_mano():
    # un mes, dos miembros: el 1 aporta 10 y no importa; el 2 no aporta e importa 4.
    # Reparto igual: cada uno recibe 5. El 2 acredita 4 (ganado 4) y el 1 cede 5
    # sin perder crédito (no importaba): el fondo saca 4 kWh de la bolsa.
    sr = np.array([[10.0], [0.0]])
    dr = np.array([[0.0], [4.0]])
    mes = np.array([0])
    A, cr, ex = cf.fondo_energia(sr, dr, mes, {0: np.array([0.5, 0.5])})
    assert A.ravel().tolist() == [5.0, 5.0] and cr.ravel().tolist() == [0.0, 4.0] and ex.ravel().tolist() == [5.0, 1.0]
    B = cf.balance_fondo(A, sr, cr, np.zeros_like(cr), mes)
    assert B["recibido"].tolist() == [0.0, 5.0] and B["cedido"].tolist() == [5.0, 0.0]
    assert B["ganado"].tolist() == [0.0, 4.0] and B["perdido"].tolist() == [0.0, 0.0]
    assert B["neto"].sum() == 4.0
    # al revés: quien cede todavía importaba, y el receptor no importa: el fondo manda a la bolsa (como N1)
    dr2 = np.array([[6.0], [0.0]])
    A2, cr2, _ = cf.fondo_energia(sr, dr2, mes, {0: np.array([0.5, 0.5])})
    crp2 = np.minimum(sr, dr2)
    B2 = cf.balance_fondo(A2, sr, cr2, crp2, mes)
    assert B2["perdido"].tolist() == [1.0, 0.0] and B2["ganado"].tolist() == [0.0, 0.0] and B2["neto"].sum() == -1.0
