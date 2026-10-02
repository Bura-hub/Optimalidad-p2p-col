"""
Pruebas de las funciones puras de
`reformateo/documento/scripts/articulo/p2p_colectivo_derivados.py` (las
mediciones de la tesis rehechas para el P2P colectivo y C2; Actividades 2.1,
2.2, 3.2 y 4.2).

Datos sintéticos y pequeños: no leen el canon ni escriben nada. Corren en
segundos:

    .venv/Scripts/python.exe -m pytest tests/test_p2p_colectivo_derivados.py -q
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "p2p_colectivo_derivados",
    RAIZ / "reformateo" / "documento" / "scripts" / "articulo" / "p2p_colectivo_derivados.py")
pd_ = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pd_)
PC = pd_.PC
AS = pd_.AS


@pytest.fixture
def datos():
    rng = np.random.default_rng(7)
    N, T = 4, 96
    G = np.clip(rng.normal(5.0, 4.0, (N, T)), 0.0, None)
    D = np.clip(rng.normal(4.0, 2.0, (N, T)), 0.0, None)
    CU = rng.uniform(600.0, 800.0, (N, T))
    pb = rng.uniform(80.0, 500.0, T)
    mes = np.repeat([0, 1, 2], T // 3)
    ded = np.repeat(rng.uniform(30.0, 300.0, (N, 1)), T, axis=1)
    s, d, au = np.maximum(G - D, 0.0), np.maximum(D - G, 0.0), np.minimum(G, D)
    v, q = pd_.lado_corto(s, d, np.ones(T, dtype=bool))
    return dict(N=N, T=T, CU=CU, pb=pb, mes=mes, ded=ded, s=s, d=d, au=au, v=v, q=q)


def test_horario_suma_el_valor_del_punto_pc(datos):
    x = datos
    W = PC.igual(x["N"], x["mes"])
    pag = np.zeros((x["N"], x["T"]))
    H = pd_.horario(x["au"], x["s"], x["d"], x["v"], x["q"], x["CU"], pag, x["ded"], x["mes"], x["pb"], W, "prueba")
    ref, _ = PC.valor_comunitario(x["au"], x["s"], x["d"], x["v"], x["q"], x["CU"], pag, x["ded"], x["mes"], x["pb"],
                                  W, "prueba")
    assert H.shape == (x["N"], x["T"])
    assert np.allclose(H.sum(axis=1), ref, rtol=0, atol=1e-6)
    # sin intercambio es C4 con esa deducción
    cero = np.zeros_like(pag)
    H4 = pd_.horario(x["au"], x["s"], x["d"], cero, cero, x["CU"], cero, x["ded"], x["mes"], x["pb"], W, "C4")
    col, _ = AS.colectivo(x["s"], x["d"], x["CU"], x["ded"], x["mes"], x["pb"], W, "C4")
    assert np.allclose(H4, x["au"] * x["CU"] + col)


def test_por_mes_conserva_el_total(datos):
    x = datos
    H = np.arange(x["N"] * x["T"], dtype=float).reshape(x["N"], x["T"])
    Pm = pd_.por_mes(H, x["mes"], 3)
    assert Pm.shape == (x["N"], 3)
    assert np.allclose(Pm.sum(axis=1), H.sum(axis=1))
    assert np.allclose(Pm[:, 1], H[:, 32:64].sum(axis=1))


def test_lado_corto_es_el_lado_corto(datos):
    x = datos
    hay = np.arange(x["T"]) % 2 == 0
    v, q = pd_.lado_corto(x["s"], x["d"], hay)
    vol = np.minimum(x["s"].sum(0), x["d"].sum(0))
    assert np.allclose(v.sum(0), np.where(hay, vol, 0.0))
    assert np.allclose(q.sum(0), np.where(hay, vol, 0.0))
    assert (v <= x["s"] + 1e-12).all() and (q <= x["d"] + 1e-12).all()


def test_coincidencia_del_p2p_colectivo(datos):
    x = datos
    W = PC.igual(x["N"], x["mes"])
    cero = np.zeros_like(x["s"])
    # sin intercambio, el factor es el de C4 con el reparto igual
    c4 = pd_._razon([pd_._cuenta_mes(np.full(x["N"], 1.0 / x["N"])[:, None] * x["s"][:, x["mes"] == m].sum(0)[None, :],
                                     x["d"][:, x["mes"] == m]) for m in range(3)])
    assert pd_.coincidencia_p2pcol(x["s"], x["d"], cero, cero, x["mes"], W) == pytest.approx(c4)
    # con intercambio, entre cero y uno, y no menor que sin él (lo transado coincide)
    f = pd_.coincidencia_p2pcol(x["s"], x["d"], x["v"], x["q"], x["mes"], W)
    assert 0.0 <= f <= 1.0 and f >= c4 - 1e-12
    # si todo el excedente se transa, coincide todo
    s1 = np.minimum(x["s"], x["d"][::-1])
    assert pd_.coincidencia_p2pcol(s1, x["d"][::-1], s1, s1, x["mes"], W) == pytest.approx(1.0) or s1.sum() == 0


def test_clase_del_precio_de_la_justicia():
    assert pd_.clase_pof(10.0, 9.0, 0.10, 0.12) == "domina"
    assert pd_.clase_pof(10.0, 9.0, 0.13, 0.12) == "intercambio"
    assert pd_.clase_pof(8.0, 9.0, 0.13, 0.12) == "C4 domina"
    assert pd_.clase_pof(8.0, 9.0, 0.11, 0.12) == "C4 deja más"
    with pytest.raises(ValueError):
        pd_.clase_pof(np.nan, 9.0, 0.1, 0.1)


def test_cambia_con_empate_a_un_peso():
    assert pd_.cambia(5.0, -5.0)
    assert not pd_.cambia(5.0, 0.5 + 4.0)
    assert pd_.cambia(-0.5, 5.0)            # de empate a positivo cuenta como cambio
    assert not pd_.cambia(0.4, -0.9)        # empate a empate
