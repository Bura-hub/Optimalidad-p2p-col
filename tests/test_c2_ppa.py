"""
Pruebas de las compuertas puras de `reformateo/documento/scripts/articulo/c2_ppa.py`
(el C2 de la propuesta como PPA de todo el excedente; Actividad 2.1).

Datos sintéticos y pequeños: no leen el canon ni escriben nada. Corren en
segundos:

    .venv/Scripts/python.exe -m pytest tests/test_c2_ppa.py -q
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from scenarios.scenario_c2_bilateral import run_c2_bilateral
from scenarios.scenario_c3_spot import run_c3_spot

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "c2_ppa", RAIZ / "reformateo" / "documento" / "scripts" / "articulo" / "c2_ppa.py")
c2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c2)


@pytest.fixture
def datos():
    rng = np.random.default_rng(7)
    N, T = 3, 72
    G = np.clip(rng.normal(5.0, 4.0, (N, T)), 0.0, None)
    D = np.clip(rng.normal(4.0, 2.0, (N, T)), 0.0, None)
    CU = rng.uniform(600.0, 800.0, (N, T))
    pb = rng.uniform(80.0, 500.0, T)
    mem = np.repeat(rng.uniform(14.0, 18.0, (N, 1)), T, axis=1)
    au = np.minimum(G, D)
    S_h = np.maximum(G - D, 0.0)
    A = (au * CU).sum(axis=1)
    return dict(N=N, T=T, G=G, D=D, CU=CU, pb=pb, mem=mem, A=A, S_h=S_h)


def test_ppa_lineal_en_el_precio(datos):
    A, S_h = datos["A"], datos["S_h"]
    S = S_h.sum(axis=1)
    b1, b2 = c2.valor_ppa(A, S_h, 250.0), c2.valor_ppa(A, S_h, 300.0)
    assert np.allclose((b2 - b1) / 50.0, S, rtol=0, atol=1e-9)
    assert np.allclose(c2.valor_ppa(A, S_h, 0.0), A)
    # una serie que es constante da lo mismo que el escalar
    assert np.allclose(c2.valor_ppa(A, S_h, np.full(datos["T"], 287.0)), A + 287.0 * S)


def test_precio_de_equilibrio_reproduce_el_beneficio(datos):
    A, S = datos["A"], datos["S_h"].sum(axis=1)
    B = A + np.array([1e5, 2e5, 3e5])
    pp = c2.precio_equilibrio(B, A, S)
    assert np.allclose(A + pp * S, B, rtol=0, atol=1e-8)
    assert np.allclose(c2.valor_ppa(A, datos["S_h"], pp[:, None]), B, rtol=0, atol=1e-6)


def test_precio_de_equilibrio_vacio_sin_excedente():
    pp = c2.precio_equilibrio(np.array([10.0, 20.0]), np.array([5.0, 20.0]), np.array([1.0, 0.0]))
    assert pp[0] == 5.0 and np.isnan(pp[1])


def test_c3_es_el_ppa_con_la_bolsa_neta(datos):
    d = datos
    r = run_c3_spot(d["D"], d["G"], d["CU"], d["pb"], list(range(d["N"])), [], mem_costs=d["mem"])
    c3 = np.array([r["per_agent"][n]["net_benefit"] for n in range(d["N"])])
    assert np.allclose(c2.c3_valor(d["A"], d["S_h"], d["pb"], d["mem"]), c3, rtol=1e-12, atol=1e-6)
    pnet = np.maximum(d["pb"][None, :] - d["mem"], 0.0)
    assert np.allclose(c2.valor_ppa(d["A"], d["S_h"], pnet), c3, rtol=1e-12, atol=1e-6)


def test_c3_recorta_donde_la_bolsa_no_cubre_mem(datos):
    d = datos
    pb = d["pb"].copy()
    pb[:10] = 5.0                       # bajo MEM: C3 no paga esas horas
    r = run_c3_spot(d["D"], d["G"], d["CU"], pb, list(range(d["N"])), [], mem_costs=d["mem"])
    c3 = np.array([r["per_agent"][n]["net_benefit"] for n in range(d["N"])])
    assert np.allclose(c2.c3_valor(d["A"], d["S_h"], pb, d["mem"]), c3, rtol=1e-12, atol=1e-6)


def test_run_c2_bilateral_es_A_mas_PP_por_S(datos):
    d = datos
    for pp in (287.41, np.linspace(283.0, 295.0, d["T"])):
        r = run_c2_bilateral(d["D"], d["G"], d["CU"], 0.0, 0.0, list(range(d["N"])), [],
                             pi_bolsa=d["pb"], pi_contrato=pp, cobertura_contrato=1.0)
        b = np.array([r["per_agent"][n]["net_benefit"] for n in range(d["N"])])
        assert np.allclose(b, c2.valor_ppa(d["A"], d["S_h"], pp), rtol=1e-12, atol=1e-6)
        assert all(r["per_agent"][n]["grid_revenue"] == 0.0 for n in range(d["N"]))


def test_k_estrella_iguala_c3_al_ppa(datos):
    d = datos
    S = d["S_h"].sum()
    objetivo = 287.41 * S
    k = c2.k_estrella(d["S_h"], d["pb"], d["mem"], objetivo)
    c3k = c2.c3_valor(d["A"], d["S_h"], d["pb"], d["mem"], k).sum()
    assert abs(c3k - (d["A"].sum() + objetivo)) <= 1e-6 * objetivo
    # con la bolsa sin recorte, C3 es lineal en k y k* tiene forma cerrada
    k_cerrada = (objetivo + (d["S_h"] * d["mem"]).sum()) / (d["S_h"] * d["pb"][None, :]).sum()
    assert k >= (d["mem"] / d["pb"][None, :])[d["S_h"] > 0].max()
    assert abs(k - k_cerrada) <= 1e-10 * k_cerrada


def test_k_estrella_falla_en_voz_alta_sin_excedente():
    with pytest.raises(ValueError):
        c2.k_estrella(np.zeros((1, 4)), np.full(4, 100.0), np.full((1, 4), 15.0), 10.0)


def test_signo_brecha_con_empate():
    s = c2.signo_brecha(np.array([2.0, -2.0, 0.5, -0.9, 0.0, 1.0, -1.0]))
    assert s.tolist() == [1, -1, 0, 0, 0, 0, 0]
    assert s.dtype.kind == "i"
    assert c2.signo_brecha(3.0, tol=5.0) == 0


def test_gini_es_el_del_canon():
    from core.settlement import gini_index
    v = np.array([11.45e6, 9.08e6, 11.14e6, 9.36e6, 5.47e6])
    assert c2.gini(v) == gini_index(v)
    assert c2.gini(np.full(4, 7.0)) == 0.0
    # escala: el Gini no cambia si todos los beneficios se multiplican
    assert abs(c2.gini(3.0 * v) - c2.gini(v)) <= 1e-15
    # dos de cuatro con todo: G = (2·(3+4)·1)/(4·2) − 5/4 = 0,5
    assert abs(c2.gini(np.array([0.0, 0.0, 1.0, 1.0])) - 0.5) <= 1e-15


def test_gini_falla_en_voz_alta_con_no_finitos():
    with pytest.raises(SystemExit):
        c2.gini(np.array([1.0, np.nan, 2.0]))
