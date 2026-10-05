"""Pruebas de `reformateo/documento/scripts/articulo/h2_exacto.py` (2026-10-05):
el cargo del intercambio de H2 a cargo del vendedor. Sin datos; segundos.

Actividades 2.1 y 2.2. La compuerta con datos (la liquidación reproduce el H2
de e1/H1 en los trece casos con el almacén del canon) va dentro del guion.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "reformateo" / "documento" / "scripts" / "articulo"))
sys.path.insert(0, str(RAIZ))

X = pytest.importorskip("h2_exacto")


def test_cargo_vendedor_solo_numeral_2_con_su_tarifa():
    ags = ["A", "B", "C"]
    num = {"A": 1, "B": 2, "C": 2}
    Cv = np.array([[10.0, 10.0], [20.0, 21.0], [30.0, 30.0]])
    Th = np.array([[1.0, 1.0], [2.0, 3.0], [4.0, 4.0]])
    vend = ["A", "B", "B", "C"]
    hora = [0, 0, 1, 1]
    kwh = [5.0, 2.0, 1.0, 3.0]
    g = X.cargo_vendedor(vend, hora, kwh, num, ags, 1.0, Cv, Th, 2)
    # A (numeral 1) no paga; B paga 2·(20+2) en la hora 0 y 1·(21+3) en la 1; C, 3·(30+4)
    np.testing.assert_allclose(g, [[0.0, 0.0], [44.0, 24.0], [0.0, 102.0]])
    # con kap = 2 (CV2) se dobla solo el Cv
    g2 = X.cargo_vendedor(vend, hora, kwh, num, ags, 2.0, Cv, Th, 2)
    np.testing.assert_allclose(g2[1], [2 * (40 + 2), 1 * (42 + 3)])


def test_sin_ventas_del_numeral_2_no_hay_cargo():
    g = X.cargo_vendedor(["A"], [0], [7.0], {"A": 1}, ["A"], 1.0, np.ones((1, 1)), np.ones((1, 1)), 1)
    assert (g == 0).all()


def test_pagador_desconocido_falla():
    with pytest.raises(ValueError, match="pagador"):
        X.liquida_h2({}, None, None, "nadie", "x")
