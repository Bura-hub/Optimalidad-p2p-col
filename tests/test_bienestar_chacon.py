"""
Pruebas de las funciones puras de
`reformateo/documento/scripts/articulo/bienestar_chacon.py` (la descomposición
del bienestar del modelo base en el resultado publicado del mercado P2P;
Actividad 3.3; CANON §14.34).

Datos sintéticos y pequeños: no leen el canon ni escriben nada. Corren en
segundos:

    .venv/Scripts/python.exe -m pytest tests/test_bienestar_chacon.py -q
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "bienestar_chacon",
    RAIZ / "reformateo" / "documento" / "scripts" / "articulo" / "bienestar_chacon.py")
bc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bc)

from core.replicator_buyers import buyer_welfare  # noqa: E402
from core.replicator_sellers import seller_welfare  # noqa: E402


def test_parametros_del_modelo_base():
    assert (bc.LAM, bc.THETA, bc.BETA) == (100.0, 0.5, 0.1)


def test_utilidad_cuadratica():
    # U(x) = λx − (θ/2)x²: U(0) = 0, U(10) = 1000 − 25, máximo en x = λ/θ = 200
    assert bc.utilidad(0.0) == 0.0
    assert bc.utilidad(10.0) == pytest.approx(975.0)
    x = np.linspace(0.0, 400.0, 4001)
    assert x[np.argmax(bc.utilidad(x))] == pytest.approx(200.0)
    assert bc.utilidad(400.0) == pytest.approx(0.0)
    with pytest.raises(ValueError):
        bc.utilidad(-1.0)


def test_pago_log_signo_y_derivada():
    # π_gb·P·ln(1/(π+1)) ≤ 0; cero sin energía; su derivada en π es −π_gb·P/(π+1),
    # el término de pago de la aptitud del comprador en el solucionador
    assert bc.pago_log(0.0, 700.0, 690.0) == 0.0
    assert bc.pago_log(2.0, 700.0, 690.0) == pytest.approx(-690.0 * 2.0 * math.log(701.0))
    assert float(bc.pago_log(1.0, 0.0, 690.0)) == 0.0
    p, h = 600.0, 1e-4
    der = (bc.pago_log(3.0, p + h, 500.0) - bc.pago_log(3.0, p - h, 500.0)) / (2 * h)
    assert der == pytest.approx(-500.0 * 3.0 / (p + 1.0), rel=1e-7)
    with pytest.raises(ValueError):
        bc.pago_log(-1.0, 700.0, 690.0)
    with pytest.raises(ValueError):
        bc.pago_log(1.0, 700.0, -1.0)


def test_competencia():
    # un solo comprador: cero; con tres, −β·(suma de los otros); Σ = −β(|I|−1)Σ
    assert bc.competencia(np.array([500.0]))[0] == 0.0
    c = bc.competencia(np.array([100.0, 200.0, 300.0]))
    assert c == pytest.approx([-50.0, -40.0, -30.0])
    assert c.sum() == pytest.approx(-0.1 * 2 * 600.0)
    with pytest.raises(ValueError):
        bc.competencia(np.array([-1.0, 2.0]))


def test_costo_produccion():
    assert bc.costo_produccion(4.0, 241.0) == pytest.approx(964.0)
    assert bc.costo_produccion(4.0, 241.0, a=0.5, c=3.0) == pytest.approx(8.0 + 964.0 + 3.0)
    with pytest.raises(ValueError):
        bc.costo_produccion(-1.0, 241.0)


def test_suma_igual_a_las_funciones_del_proyecto():
    # una hora sintética: 2 vendedores, 3 compradores; los términos sumados a mano
    # son buyer_welfare y seller_welfare en su forma extensa (ecs. 6, 7 y 14)
    P = np.array([[1.0, 0.0, 2.5], [0.5, 1.2, 0.0]])
    pi = np.array([710.0, 690.0, 735.0])
    au_c = np.array([3.0, 0.0, 12.0])
    au_v = np.array([40.0, 7.0])
    b = np.array([241.0, 225.0])
    pgb = 680.0
    pagos = (P * pi[None, :]).sum(axis=0)
    mi = (bc.utilidad(au_c) + bc.pago_log(P.sum(axis=0), pi, pgb) + bc.competencia(pagos)).sum()
    wi = buyer_welfare(pi, P, au_c, np.full(3, 100.0), np.full(3, 0.5), np.full(3, 0.1), forma="extensa", pi_gb=pgb)
    assert mi == pytest.approx(wi, rel=1e-12)
    R = (P * pi[None, :]).sum(axis=1)
    mj = (bc.utilidad(au_v) + R - bc.costo_produccion(P.sum(axis=1), b)).sum()
    wj = seller_welfare(P, au_v, np.zeros(2), b, np.full(2, 100.0), np.full(2, 0.5), pi, forma="extensa",
                        D_auto=au_v, c_j=np.zeros(2))
    assert mj == pytest.approx(wj, rel=1e-12)


def test_numero_a_la_espanola():
    assert bc._n(-20723456.0 / 1e6, 3) == "−20,723"
    assert bc._n(4592.0193, 1) == "4 592,0"
    assert bc._n(float("nan")) == "·"
