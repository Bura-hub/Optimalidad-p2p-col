"""La liquidación de las cuatro esquinas (`scenarios/esquinas_supuestos.py`)
sobre los flujos del canon reproduce las de §14.21 (`atribucion_13casos.csv`,
e1/S) en los trece casos (F2).

Actividad 3.3. Revisión r1 del artículo; M1 y M2 de la auditoría del
2026-11-21 (con `min(G, D)` en lugar de la columna `autoconsumo` del almacén,
F2 cierra a 0,24 COP como mucho; la tolerancia es 1 COP). Lee el canon con
huella (`atribucion_supuestos.lee`). Lenta: un minuto. Uso:
    .venv/Scripts/python.exe -m pytest tests/test_esquinas_supuestos.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parent.parent
ARTICULO = RAIZ / "reformateo" / "documento" / "scripts" / "articulo"
for p in (str(RAIZ), str(ARTICULO)):
    if p not in sys.path:
        sys.path.insert(0, p)

CANON = RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
pytestmark = pytest.mark.skipif(not CANON.is_dir(), reason="sin la matriz del canon")
CASOS = ("E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1", "CV2", "SINU")


@pytest.fixture(scope="module")
def base():
    import atribucion_supuestos as AS
    import c2_ppa as CP
    import pandas as pd
    TT, cap = AS.tarifas(), AS.capacidades()
    idx, _ = CP.horizonte()
    atr = pd.read_csv(AS.lee("atribucion_supuestos_2026-09-30/atribucion_13casos.csv", "e1/S")).set_index("caso")
    return AS, TT, cap, CP.bolsa(idx), atr


@pytest.mark.parametrize("caso", CASOS)
def test_lenta_las_cuatro_esquinas_son_las_de_14_21(caso, base):
    from scenarios.esquinas_supuestos import liquida_esquina
    AS, TT, cap, pb, atr = base
    L = AS.carga(caso, TT, cap)
    for esq, col in (("p2p", "P2P"), ("solo1", "v10"), ("solo2", "v01"), ("ninguno", "P2P_colectivo")):
        val, _ = liquida_esquina(esq, L["G"], L["D"], L["v"], L["q"], L["CU"], L["ded1"], L["ded4"], L["mes"], pb)
        assert abs(float(val.sum()) - float(atr.loc[caso, col])) <= 1.0, (caso, esq)
        assert np.isfinite(val).all(), (caso, esq)
