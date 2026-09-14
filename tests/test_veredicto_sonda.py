"""tests/test_veredicto_sonda.py -- el veredicto de la palanca de H-79
(subproyecto 2, D25; brief en
.superpowers/sdd/2026-09-14-oraculo-anexo4/brief-lanzador.md).

Prueba `decide_veredicto`, de
reformateo/documento/scripts/sonda/reparto_vs_integrador.py, con tablas
SINTETICAS: nunca resuelve un mercado ni carga datos del MTE. La funcion solo
lee columnas de una tabla ya comparada contra produccion (`delta_puntos`,
`excedente_delta_%` y, para el caso raro del excedente de produccion en cero,
`excedente`) y decide que variante -- tolerancia o horizonte -- supera algun
criterio.

Los dos criterios (fijados antes de medir, en el modulo de la sonda):
  - 1 punto porcentual de la tajada del vendedor (UMBRAL_PUNTOS);
  - 0,1 % del excedente (UMBRAL_EXCEDENTE_PCT).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reformateo" / "documento" / "scripts" / "sonda"))

from reparto_vs_integrador import (  # noqa: E402
    UMBRAL_EXCEDENTE_PCT, UMBRAL_PUNTOS, decide_veredicto,
)


def _tabla(filas: dict) -> pd.DataFrame:
    """Arma una tabla de variantes con las columnas que `main` ya calcula.

    `filas` es {nombre_variante: (delta_puntos, excedente_delta_%, excedente)}.
    `excedente_delta_%` puede ser `np.nan`, para el caso raro del excedente de
    produccion en cero.
    """
    df = pd.DataFrame.from_dict(filas, orient="index",
                                columns=["delta_puntos", "excedente_delta_%",
                                         "excedente"])
    return df


# ─── 1 · ninguna variante supera ningun criterio ────────────────────────────


def test_ninguna_variante_supera():
    tabla = _tabla({
        "produccion": (0.0, 0.0, 1000.0),
        "relativa_x0,1": (0.3, 0.02, 1000.5),
        "horizonte_x2": (-0.2, -0.05, 999.0),
    })
    v = decide_veredicto(tabla)
    assert v == {"reparto_depende": False, "excedente_cambia": False,
                "palanca": []}


# ─── 2 · solo la tolerancia supera el reparto ───────────────────────────────


def test_solo_tolerancia_por_reparto():
    tabla = _tabla({
        "produccion": (0.0, 0.0, 1000.0),
        "relativa_x0,1": (1.5, 0.02, 1000.2),   # 1,5 puntos: supera
        "horizonte_x2": (0.1, 0.03, 999.0),
    })
    v = decide_veredicto(tabla)
    assert v["reparto_depende"] is True
    assert v["excedente_cambia"] is False
    assert v["palanca"] == ["tolerancia"]


# ─── 3 · solo el horizonte supera el excedente ──────────────────────────────


def test_solo_horizonte_por_excedente():
    tabla = _tabla({
        "produccion": (0.0, 0.0, 1000.0),
        "relativa_x0,1": (0.4, 0.05, 1000.5),
        "horizonte_x2": (0.2, 0.15, 1001.5),    # 0,15 %: supera
    })
    v = decide_veredicto(tabla)
    assert v["reparto_depende"] is False
    assert v["excedente_cambia"] is True
    assert v["palanca"] == ["horizonte"]


# ─── 4 · las dos variantes superan, en orden tolerancia-horizonte ───────────


def test_las_dos_variantes_superan():
    tabla = _tabla({
        "produccion": (0.0, 0.0, 1000.0),
        "relativa_x0,1": (2.0, 0.2, 1002.0),
        "horizonte_x2": (1.2, 0.3, 1003.0),
    })
    v = decide_veredicto(tabla)
    assert v["reparto_depende"] is True
    assert v["excedente_cambia"] is True
    # El orden es SIEMPRE tolerancia antes que horizonte, sin importar el
    # orden de las filas de la tabla de entrada.
    assert v["palanca"] == ["tolerancia", "horizonte"]


def test_orden_de_filas_no_importa():
    """La misma tabla del caso anterior, con las filas en el orden opuesto."""
    tabla = _tabla({
        "horizonte_x2": (1.2, 0.3, 1003.0),
        "relativa_x0,1": (2.0, 0.2, 1002.0),
        "produccion": (0.0, 0.0, 1000.0),
    })
    v = decide_veredicto(tabla)
    assert v["palanca"] == ["tolerancia", "horizonte"]


# ─── 5 · caso borde: excedente de produccion en cero ────────────────────────


def test_excedente_produccion_cero_con_cambio():
    # `main` deja excedente_delta_% en NaN cuando el excedente de produccion
    # es ~0 (no hay base para un cambio relativo); de cero a algo SI cuenta.
    tabla = _tabla({
        "produccion": (0.0, np.nan, 0.0),
        "relativa_x0,1": (0.1, np.nan, 0.0),
        "horizonte_x2": (0.1, np.nan, 3.5),     # de 0 a 3,5: cambia
    })
    v = decide_veredicto(tabla)
    assert v["excedente_cambia"] is True
    assert v["palanca"] == ["horizonte"]


def test_excedente_produccion_cero_sin_cambio():
    tabla = _tabla({
        "produccion": (0.0, np.nan, 0.0),
        "relativa_x0,1": (0.1, np.nan, 0.0),
        "horizonte_x2": (0.1, np.nan, 0.0),
    })
    v = decide_veredicto(tabla)
    assert v == {"reparto_depende": False, "excedente_cambia": False,
                "palanca": []}


# ─── 6 · una variante ausente no es un error ────────────────────────────────


def test_variante_ausente_no_aporta_palanca():
    # Tabla sintetica con una sola variante candidata, como se veria en una
    # prueba que no corrio la de horizonte.
    tabla = _tabla({
        "produccion": (0.0, 0.0, 1000.0),
        "relativa_x0,1": (5.0, 5.0, 1050.0),
    })
    v = decide_veredicto(tabla)
    assert v["reparto_depende"] is True
    assert v["excedente_cambia"] is True
    assert v["palanca"] == ["tolerancia"]


def test_tabla_sin_ninguna_variante_candidata():
    tabla = _tabla({"produccion": (0.0, 0.0, 1000.0)})
    v = decide_veredicto(tabla)
    assert v == {"reparto_depende": False, "excedente_cambia": False,
                "palanca": []}


# ─── 7 · los umbrales son exactamente los de la sonda, y son parametrizables ─


def test_umbrales_por_omision_son_los_de_la_sonda():
    assert UMBRAL_PUNTOS == 1.0
    assert UMBRAL_EXCEDENTE_PCT == 0.1


def test_frontera_es_mayor_o_igual():
    """El criterio del script es `not peor < umbral`, es decir >=: la
    igualdad exacta con el umbral SI supera."""
    tabla = _tabla({
        "produccion": (0.0, 0.0, 1000.0),
        "relativa_x0,1": (1.0, 0.0, 1000.0),    # exactamente 1,0 punto
        "horizonte_x2": (0.0, 0.1, 1001.0),     # exactamente 0,1 %
    })
    v = decide_veredicto(tabla)
    assert v["reparto_depende"] is True
    assert v["excedente_cambia"] is True
    assert v["palanca"] == ["tolerancia", "horizonte"]


def test_umbral_personalizado_mas_estricto():
    tabla = _tabla({
        "produccion": (0.0, 0.0, 1000.0),
        "relativa_x0,1": (0.5, 0.05, 1000.5),
        "horizonte_x2": (0.3, 0.02, 1000.2),
    })
    # Con los umbrales por omision, ninguna supera.
    assert decide_veredicto(tabla)["palanca"] == []
    # Pero con umbrales mas estrictos, las dos superan.
    v = decide_veredicto(tabla, umbral_puntos=0.4, umbral_excedente_pct=0.01)
    assert v["palanca"] == ["tolerancia", "horizonte"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
