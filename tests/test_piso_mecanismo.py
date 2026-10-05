"""Pruebas del piso del vendedor con los mecanismos H1 y H2 (2026-10-05):
`core.opciones_externas.piso_mecanismo`, `precio_cesion` y `fraccion_cedida`.

Actividad 2.1. Datos sintéticos; corren en segundos:

    .venv/Scripts/python.exe -m pytest tests/test_piso_mecanismo.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.opciones_externas import (fraccion_cedida, piso_mecanismo,  # noqa: E402
                                    piso_residual, precio_cesion,
                                    residual_proporcional, reparto_anexo4)


def _datos(semilla=5, N=4, T=72, escala_D=1.0):
    rng = np.random.default_rng(semilla)
    G = np.clip(rng.normal(4.0, 3.0, (N, T)), 0.0, None)
    D = np.clip(rng.normal(3.0, 1.5, (N, T)), 0.0, None) * escala_D
    CU = np.repeat(rng.uniform(650.0, 800.0, (N, 3)), T // 3, axis=1)
    ded = np.repeat(rng.uniform(30.0, 60.0, (N, 1)), T, axis=1)
    bolsa = rng.uniform(100.0, 500.0, T)
    mes = np.repeat(["2025-04", "2025-05", "2025-06"], T // 3)
    return G, D, CU, ded, bolsa, mes


def test_c1_es_piso_residual_al_bit():
    G, D, CU, ded, b, mes = _datos()
    a, pa = piso_residual(G, D, CU, ded, b, mes)
    c, pc = piso_mecanismo(G, D, CU, ded, b, mes, "c1")
    np.testing.assert_array_equal(a, c)
    np.testing.assert_array_equal(pa, pc)


def test_precio_cesion_a_mano():
    iny = np.array([[1.0, 3.0, 0.0, 2.0], [1.0, 0.0, 0.0, 2.0]])
    b = np.array([100.0, 200.0, 50.0, 400.0])
    p = precio_cesion(iny, b, np.array([0, 0, 1, 1]))
    # mes 0: S = (2, 3), (2*100 + 3*200)/5 = 160; mes 1: S = (0, 4) -> 400
    np.testing.assert_allclose(p, [160.0, 160.0, 400.0, 400.0])


def test_fraccion_cedida_a_mano():
    # un mes: el miembro 0 inyecta 10 e importa 4 (sobrante 6); el 1 inyecta
    # 0 e importa 3 (le falta 3): se cede 3/6 = 0,5
    iny = np.array([[10.0], [0.0]])
    ret = np.array([[4.0], [3.0]])
    np.testing.assert_allclose(fraccion_cedida(iny, ret, np.array([0])), [0.5])
    # si al otro le faltan 9, se cede todo (1); si nadie importa, nada (0)
    np.testing.assert_allclose(fraccion_cedida(iny, np.array([[4.0], [9.0]]), np.array([0])), [1.0])
    np.testing.assert_allclose(fraccion_cedida(iny, np.array([[4.0], [0.0]]), np.array([0])), [0.0])


def test_antes_del_corte_h1_h2_son_c1_mas_el_cargo():
    G, D, CU, ded, b, mes = _datos()
    cap = np.array([17.55, 150.0, 17.55, 120.0])
    c1, en_perm = piso_mecanismo(G, D, CU, ded, b, mes, "c1")
    h1, _ = piso_mecanismo(G, D, CU, ded, b, mes, "h1", capacidad_kw=cap)
    h2, _ = piso_mecanismo(G, D, CU, ded, b, mes, "h2", capacidad_kw=cap)
    grande = (cap > 100.0)[:, None] & np.ones_like(ded, dtype=bool)
    np.testing.assert_allclose(h1[en_perm], (c1 + ded)[en_perm])
    np.testing.assert_allclose(h2[en_perm], (c1 + np.where(grande, ded, 0.0))[en_perm])


def test_desde_el_corte_mezcla_cesion_y_bolsa():
    G, D, CU, ded, b, mes = _datos()
    cap = np.full(4, 17.55)
    _, en_perm = piso_mecanismo(G, D, CU, ded, b, mes, "c1")
    h2, _ = piso_mecanismo(G, D, CU, ded, b, mes, "h2", capacidad_kw=cap)
    iny_r, ret_r = residual_proporcional(G, D)
    f = fraccion_cedida(iny_r, ret_r, mes)
    pc = precio_cesion(iny_r, b, mes)
    esperado = np.broadcast_to(f * pc + (1 - f) * b, h2.shape)
    assert (~en_perm).any(), "los datos de la prueba deben tener horas tras el corte"
    np.testing.assert_allclose(h2[~en_perm], esperado[~en_perm])


def test_h2_sin_plantas_grandes_y_sin_corte_es_c1():
    """Con demanda alta nadie agota el credito: h2 con plantas pequeñas
    es exactamente el piso de c1."""
    G, D, CU, ded, b, mes = _datos(escala_D=50.0)
    _, _, en_perm = reparto_anexo4(*residual_proporcional(G, D), mes)
    assert en_perm.all()
    c1, _ = piso_mecanismo(G, D, CU, ded, b, mes, "c1")
    h2, _ = piso_mecanismo(G, D, CU, ded, b, mes, "h2", capacidad_kw=np.full(4, 50.0))
    np.testing.assert_array_equal(c1, h2)


def test_errores_en_voz_alta():
    G, D, CU, ded, b, mes = _datos()
    with pytest.raises(ValueError, match="mecanismo"):
        piso_mecanismo(G, D, CU, ded, b, mes, "h3")
    with pytest.raises(ValueError, match="capacidad"):
        piso_mecanismo(G, D, CU, ded, b, mes, "h2")
