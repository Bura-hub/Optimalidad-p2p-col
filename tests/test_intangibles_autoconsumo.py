"""
Pruebas de las funciones puras de
`reformateo/documento/scripts/articulo/intangibles_autoconsumo.py` (beneficio
monetario frente a intangible e incentivo a consumir en el sitio, derivados
sin simular; Actividad 3.3; CANON §14.31).

Datos sintéticos y pequeños: no leen el canon ni escriben nada. Corren en
segundos:

    .venv/Scripts/python.exe -m pytest tests/test_intangibles_autoconsumo.py -q
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "intangibles_autoconsumo",
    RAIZ / "reformateo" / "documento" / "scripts" / "articulo" / "intangibles_autoconsumo.py")
ia = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ia)


def test_kappa_cvar_normal():
    # CVaR_0,95 − media de una normal estándar: φ(1,6449) / 0,05 = 2,0627
    assert ia.kappa_cvar(0.95) == pytest.approx(2.062712807, abs=1e-8)
    assert ia.kappa_cvar(0.5) == pytest.approx(2 * math.exp(0) / math.sqrt(2 * math.pi), abs=1e-9)
    with pytest.raises(ValueError):
        ia.kappa_cvar(1.0)


def test_kappa_cvar_contra_muestra():
    rng = np.random.default_rng(7)
    x = rng.normal(0.0, 1.0, 2_000_000)
    q = np.quantile(x, 0.95)
    assert float(x[x >= q].mean()) == pytest.approx(ia.kappa_cvar(0.95), abs=5e-3)


def test_normaliza_mes():
    x = np.array([[27.0, 31.0, 15.0]])
    out = ia.normaliza_mes(x, np.array([27.0, 31.0, 15.0]))
    assert np.allclose(out, 30.0)
    with pytest.raises(ValueError):
        ia.normaliza_mes(x, np.array([27.0, 0.0, 15.0]))


def test_dispersion_y_cv_vacio():
    mu, sd, cv = ia.dispersion([1.0, 2.0, 3.0])
    assert (mu, sd, cv) == pytest.approx((2.0, 1.0, 0.5))
    _, _, cv = ia.dispersion([-1.0, 0.5, 0.2])
    assert math.isnan(cv)
    with pytest.raises(ValueError):
        ia.dispersion([1.0, float("nan")])


def test_primas():
    assert ia.prima_cvar(100.0, 0.1, n=8.0, kappa=2.0) == pytest.approx(160.0)
    assert ia.prima_cvar(0.0, 0.2) == 0.0
    assert ia.prima_mv(10.0, 0.1, escala=50.0, n=2.0) == pytest.approx(2.0 * 0.5 * 0.1 / 50.0 * 100.0)
    with pytest.raises(ValueError):
        ia.prima_cvar(-1.0, 0.1)
    with pytest.raises(ValueError):
        ia.prima_mv(1.0, 0.1, escala=0.0)


def test_n_eq_del_horizonte():
    assert ia.N_EQ == pytest.approx(256.0 / 30.0)


def test_signo():
    assert list(ia.signo([2.0, 0.5, -0.5, -3.0])) == [1, 0, 0, -1]


def test_consumo_inducido():
    R = np.array([[0.0, 10.0], [5.0, 0.0]])
    assert np.allclose(ia.consumo_inducido(R, -0.37), 0.37 * R)
    with pytest.raises(ValueError):
        ia.consumo_inducido(R, 0.2)
    with pytest.raises(ValueError):
        ia.consumo_inducido(-R - 1.0, -0.2)


def test_tope_comunidad():
    X = np.array([[2.0, 1.0, 0.0], [2.0, 0.0, 3.0]])
    sr = np.array([2.0, 5.0, 0.0])
    Y = ia.tope_comunidad(X, sr)
    assert np.allclose(Y[:, 0], [1.0, 1.0])     # a prorrata
    assert np.allclose(Y[:, 1], [1.0, 0.0])     # alcanza
    assert np.allclose(Y[:, 2], [0.0, 0.0])     # sin residual
    assert bool((Y.sum(axis=0) <= sr + 1e-12).all())


def test_mensual():
    x = np.arange(12.0).reshape(2, 6)
    mes = np.array([0, 0, 1, 1, 1, 2])
    out = ia.mensual(x, mes, 3)
    assert np.allclose(out, [[1.0, 9.0, 5.0], [13.0, 27.0, 11.0]])
