"""
Pruebas de las funciones puras de
`reformateo/documento/scripts/articulo/prevision_corte.py` (cuánto del mercado
P2P depende de conocer el mes de antemano; Actividades 2.1 y 3.3).

Datos sintéticos y pequeños: no leen el canon ni escriben nada. Corren en
segundos:

    .venv/Scripts/python.exe -m pytest tests/test_prevision_corte.py -q
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "prevision_corte",
    RAIZ / "reformateo" / "documento" / "scripts" / "articulo" / "prevision_corte.py")
pv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pv)
from core.opciones_externas import reparto_anexo4  # noqa: E402


@pytest.fixture
def datos():
    rng = np.random.default_rng(7)
    N, T = 4, 120
    iny = np.clip(rng.normal(2.0, 2.5, (N, T)), 0.0, None)
    ret = np.clip(rng.normal(1.5, 1.5, (N, T)), 0.0, None)
    mes = np.repeat([0, 1, 2], T // 3)
    return dict(N=N, T=T, iny=iny, ret=ret, mes=mes)


def test_seguro_a_mano():
    """Un miembro, un mes de cuatro horas: importa 3 en la primera y 1 en la
    tercera; inyecta 1, 1, 0 y 5. La inyección acumulada (1, 2, 2, 7) va por
    debajo de la importación acumulada (3, 3, 4, 4) en las tres primeras."""
    iny = np.array([[1.0, 1.0, 0.0, 5.0]])
    ret = np.array([[3.0, 0.0, 1.0, 0.0]])
    s = pv.seguro_en_linea(iny, ret, np.zeros(4, dtype=int))
    assert s.tolist() == [[True, True, True, False]]


def test_seguro_nunca_esta_tras_el_corte(datos):
    """Lo que es seguro en tiempo real es crédito con el mes completo."""
    seg = pv.seguro_en_linea(datos["iny"], datos["ret"], datos["mes"])
    _, _, en_perm = reparto_anexo4(datos["iny"], datos["ret"], datos["mes"])
    assert not bool((seg & ~en_perm).any())
    assert seg.any() and (~seg).any()


def test_el_mes_reinicia_lo_acumulado():
    """Lo inyectado en un mes no cuenta en el siguiente."""
    iny = np.array([[5.0, 0.0, 0.0, 1.0]])
    ret = np.array([[0.0, 1.0, 2.0, 0.0]])
    s = pv.seguro_en_linea(iny, ret, np.array([0, 0, 1, 1]))
    assert s.tolist() == [[False, False, True, True]]


def test_clases_parten_las_horas_con_sobrante():
    sob = np.array([[True, True, True, False]])
    seg = np.array([[True, False, False, False]])
    tras = np.array([[False, False, True, True]])
    k = pv.clases(sob, seg, tras)
    assert k.tolist() == [[0, 1, 2, -1]]
    with pytest.raises(SystemExit):
        pv.clases(sob, np.array([[True, True, True, True]]), tras)


def test_por_clase_suma_el_total():
    x = np.array([[1.0, 2.0, 3.0, 4.0]])
    k = np.array([[0, 1, 2, -1]])
    pc = pv.por_clase(x, k)
    assert pc == {"seguro": 1.0, "incierto_credito": 2.0, "incierto_exceso": 3.0, "total": 6.0}


def test_pronostico_contiene_lo_seguro_y_solo_usa_el_pasado(datos):
    """El pronóstico nunca da por exceso una hora segura (R extrapolada ≥ R_k),
    y cambiar las horas posteriores a k no cambia su clasificación en k."""
    iny, ret, mes = datos["iny"], datos["ret"], datos["mes"]
    seg = pv.seguro_en_linea(iny, ret, mes)
    p = pv.credito_pronosticado(iny, ret, mes)
    assert bool((p | ~seg).all())
    k = 15
    iny2, ret2 = iny.copy(), ret.copy()
    iny2[:, k + 1:40] *= 3.0
    ret2[:, k + 1:40] *= 0.2
    p2 = pv.credito_pronosticado(iny2, ret2, mes)
    np.testing.assert_array_equal(p[:, :k + 1], p2[:, :k + 1])


def test_pronostico_a_mano():
    """Mes de cuatro horas: tras la primera, importación observada 2, extrapolada
    2 · 4/1 = 8; la inyección acumulada 3 < 8 es crédito. En la segunda,
    2 · 4/2 = 4 frente a 3 + 2 = 5: exceso."""
    iny = np.array([[3.0, 2.0, 0.0, 0.0]])
    ret = np.array([[2.0, 0.0, 0.0, 0.0]])
    p = pv.credito_pronosticado(iny, ret, np.zeros(4, dtype=int))
    assert p.tolist() == [[True, False, False, False]]
