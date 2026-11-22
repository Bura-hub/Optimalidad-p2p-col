"""El piso y el cargo de las cuatro esquinas del factorial (AE-5) sobre los
datos reales de los trece casos, y frente a las corridas del servidor.

Actividad 3.3. Revisión r1 del artículo; M1 de la auditoría del 2026-11-21
(`revision_r1/auditoria_codigo_ae45.md`). Con los insumos del punto base de
`gsa_directo.evaluador.prepara_caso` (la réplica de `main()`):

- `piso_esquina("p2p")` es `piso_residual` al bit y el piso del almacén del
  canon (float32), sin cargo;
- solo1 tiene el piso de p2p y el cargo kappa·Cv + Theta (cvm + peajes);
  solo2 y ninguno, CU − kappa·Cv − Theta antes del corte y la bolsa después,
  y ninguno, el mismo cargo; solo2, ninguno;
- en E0, K1, CV2 y SINU (nadie agota su crédito) la banda de solo1 es
  negativa en toda hora con vendedor y comprador: nadie transa;
- si están las corridas (`SALIDAS_SERVIDOR/matriz_esquina_<e>/<caso>`), su
  piso y su cargo son los recalculados aquí (float32).

Lenta (unos 3 s por caso más la carga del MTE). Uso:
    .venv/Scripts/python.exe -m pytest tests/test_piso_esquina_trece.py -q
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core.opciones_externas import (deduccion_art25, deduccion_caso2,  # noqa: E402
                                    piso_esquina, piso_residual)

MTE = Path(os.environ.get("MTE_ROOT", RAIZ / "MedicionesMTE_v3"))
MATRIZ_CANON = Path(os.environ.get("MATRIZ_CANON") or (
    RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19" / "SALIDAS_SERVIDOR" / "matriz_reposo"))
if not MATRIZ_CANON.is_absolute():
    MATRIZ_CANON = RAIZ / MATRIZ_CANON
CASOS = ("E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1", "CV2", "SINU")
SIN_CORTE = {"E0", "K1", "CV2", "SINU"}
TOL32 = 1e-3

pytestmark = pytest.mark.skipif(not (MTE.is_dir() and MATRIZ_CANON.is_dir()),
                                reason="sin los datos del MTE o sin la matriz del canon")


@pytest.fixture(scope="module")
def datos(tmp_path_factory):
    from gsa_directo import evaluador
    return evaluador.carga_mte(str(MTE), tmp_path_factory.mktemp("cache_mte"))


def _matriz(d: Path, col: str, nombres):
    ag = pd.concat(pd.read_parquet(p) for p in sorted(glob.glob(str(d / "almacen" / "m1" / "agentes" / "*.parquet"))))
    return ag.pivot(index="agente", columns="hora", values=col).loc[nombres].to_numpy(float)


@pytest.mark.parametrize("caso", CASOS)
def test_lenta_piso_y_cargo_de_las_cuatro_esquinas(caso, datos):
    from gsa_directo import comun, evaluador
    ins = evaluador.prepara_caso(caso, datos)
    f = evaluador.aplica_factores(ins, comun.PUNTO_BASE)
    G, D, bolsa, techo = f["G"], f["D"], f["bolsa"], f["techo"]
    ded1 = deduccion_art25(f["cvm"], f["tolls"], ins.cap)
    ded4 = deduccion_caso2(f["cvm"], f["tolls"])
    arg = (G, D, techo, ded1, ded4, bolsa, ins.mes_m)
    base, perm0 = piso_residual(G, D, techo, ded1, bolsa, ins.mes_m)
    p, e, c = piso_esquina("p2p", *arg)
    assert np.array_equal(p, base) and np.array_equal(e, perm0) and c is None
    assert np.abs(_matriz(MATRIZ_CANON / caso, "piso", ins.nombres) - p).max() <= TOL32
    vende = np.maximum(G - D, 0.0) > 1e-9
    compra = np.maximum(D - G, 0.0) > 1e-9
    pisos = {"p2p": (p, None)}
    for esq in ("solo1", "solo2", "ninguno"):
        q, eq, cq = piso_esquina(esq, *arg)
        assert np.isfinite(q).all() and (q[vende] >= 0).all(), (caso, esq)
        if esq == "solo1":
            assert np.array_equal(q, base) and np.array_equal(cq, ded4)
        else:
            antes = np.isclose(q, techo - ded4, atol=1e-9)
            despues = np.isclose(q, np.broadcast_to(bolsa, q.shape), atol=1e-9)
            assert (antes | despues)[vende].all(), (caso, esq)
            assert (cq is None) == (esq == "solo2"), (caso, esq)
            if esq == "ninguno":
                assert np.array_equal(cq, ded4)
        pisos[esq] = (q, cq)
    if caso in SIN_CORTE:
        q, cq = pisos["solo1"]
        for k in np.flatnonzero(vende.any(0) & compra.any(0)):
            banda = (techo[compra[:, k], k] - cq[compra[:, k], k]).max() - q[vende[:, k], k].min()
            assert banda < 0, (caso, k, banda)
    for esq, (q, cq) in pisos.items():
        d = RAIZ / "SALIDAS_SERVIDOR" / f"matriz_esquina_{esq}" / caso
        if not d.is_dir():
            continue
        assert np.abs(_matriz(d, "piso", ins.nombres) - q).max() <= TOL32, (caso, esq)
        f_c = d / "almacen" / "cargo_comprador.npy"
        assert f_c.is_file() == (cq is not None), (caso, esq)
        if cq is not None:
            assert np.abs(np.load(f_c) - cq).max() <= TOL32, (caso, esq)
