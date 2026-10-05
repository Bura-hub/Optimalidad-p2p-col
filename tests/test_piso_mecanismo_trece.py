"""El piso del vendedor de H1 y H2 sobre los datos reales de LOS TRECE CASOS
de la tesis (2026-10-05), antes de correr la matriz con `--piso-mecanismo`.

Actividades 2.1 y 4.1. Con datos (LENTAS: `-k "not lenta"` las salta). Por
caso, los insumos del punto base de `gsa_directo.evaluador.prepara_caso` (la
replica de `main()` con `--data real --full --include-c5 --no-regulado` y la
opcion del caso) y:

- el piso c1 reproduce el `piso` del almacen de la matriz del canon (entrega
  del 2026-09-19) en todas las horas-agente, a la precision float32 del
  almacen: los insumos son los del canon;
- h1 y h2 son finitos y no negativos en las horas-vendedor;
- antes del corte, h1 es c1 mas la deduccion de la planta y h2 es c1 mas la
  deduccion solo en las plantas del numeral 2 (> 100 kW);
- desde el corte, h2 menos su cargo es la mezcla de cesion
  f*p_ces + (1 - f)*bolsa, con f en [0, 1];
- h2 es c1 al bit justo en los casos sin corte y sin plantas del numeral 2
  (E0, K1, CV2 y SINU), y las plantas del numeral 2 son las de E4, E5 y P2
  (todas) y la UCC en I1 y N1.

Y el piso del P2P colectivo (``p2pcom``, el fondo con el reparto igual):

- el caso del art. 20 sin la regla del 10 % es el 2 solo en E4, E5 y P2;
- la deducción del fondo es la individual de cada planta salvo la de la UCC
  en I1 y N1 (planta del numeral 2 en un autogenerador colectivo del caso 1);
- el piso es el mismo para todos los vendedores de cada hora, finito, entre la
  bolsa y el crédito, y, donde nadie agota su parte del fondo, el crédito
  medio de la comunidad.

Unos 2 (s) por caso mas la carga del MTE:

    .venv/Scripts/python.exe -m pytest tests/test_piso_mecanismo_trece.py -q
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

from core.opciones_externas import (LIMITE_AGPE_KW,  # noqa: E402
                                    LIMITE_NUMERAL_1_KW, deduccion_art25,
                                    fraccion_cedida, piso_mecanismo,
                                    precio_cesion, precio_permuta_por_periodo,
                                    residual_proporcional)
from scenarios.scenario_c4_creg101072 import capacidad_por_usuario_art18  # noqa: E402

MTE = Path(os.environ.get("MTE_ROOT", RAIZ / "MedicionesMTE_v3"))
# La matriz del canon: MATRIZ_CANON si se da (en el servidor la pone la
# accion `matriz_mecanismo`), si no la entrega del 2026-09-19.
MATRIZ_CANON = Path(os.environ.get("MATRIZ_CANON") or (
    RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
    / "SALIDAS_SERVIDOR" / "matriz_reposo"))
if not MATRIZ_CANON.is_absolute():
    MATRIZ_CANON = RAIZ / MATRIZ_CANON
CASOS = ("E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU")
H2_IGUAL_A_C1 = {"E0", "K1", "CV2", "SINU"}
NUMERAL_2 = {"E4": {"Udenar", "Mariana", "UCC", "HUDN", "Cesmag"},
             "E5": {"Udenar", "Mariana", "UCC", "HUDN", "Cesmag"},
             "P2": {"Udenar", "Mariana", "UCC", "HUDN", "Cesmag"},
             "I1": {"UCC"}, "N1": {"UCC"}}
TOL_FLOAT32 = 1e-3     # COP/kWh: el almacen guarda el piso en float32

pytestmark = pytest.mark.skipif(
    not (MTE.is_dir() and any(MTE.iterdir()) and MATRIZ_CANON.is_dir()),
    reason="sin los datos del MTE o sin la matriz del canon")


@pytest.fixture(scope="module")
def datos(tmp_path_factory):
    from gsa_directo import evaluador
    return evaluador.carga_mte(str(MTE), tmp_path_factory.mktemp("cache_mte"))


def _pisos(caso, datos):
    from gsa_directo import comun, evaluador
    ins = evaluador.prepara_caso(caso, datos)
    f = evaluador.aplica_factores(ins, comun.PUNTO_BASE)
    G, D, bolsa, techo = f["G"], f["D"], f["bolsa"], f["techo"]
    ded = deduccion_art25(f["cvm"], f["tolls"], ins.cap)
    arg = (G, D, techo, ded, bolsa, ins.mes_m)
    c1, perm = piso_mecanismo(*arg, "c1")
    h1, _ = piso_mecanismo(*arg, "h1", capacidad_kw=ins.cap)
    h2, _ = piso_mecanismo(*arg, "h2", capacidad_kw=ins.cap)
    return ins, G, D, bolsa, ded, perm, c1, h1, h2


@pytest.mark.parametrize("caso", CASOS)
def test_lenta_piso_h1_h2_en_los_trece_casos(caso, datos):
    ins, G, D, bolsa, ded, perm, c1, h1, h2 = _pisos(caso, datos)
    N, T = c1.shape
    vende = np.maximum(G - D, 0.0) > 1e-9

    # c1 es el piso del canon, hora-agente por hora-agente
    ag = pd.concat(pd.read_parquet(p) for p in sorted(glob.glob(
        str(MATRIZ_CANON / caso / "almacen" / "m1" / "agentes" / "*.parquet"))))
    idx = {n: i for i, n in enumerate(ins.nombres)}
    alm = np.full((N, T), np.nan)
    alm[[idx[a] for a in ag.agente], ag.hora.to_numpy()] = ag.piso.to_numpy()
    assert not np.isnan(alm).any(), f"{caso}: el almacen no cubre todas las horas-agente"
    assert np.abs(alm - c1).max() <= TOL_FLOAT32, caso

    # finitos y no negativos donde se vende
    for nombre, p in (("h1", h1), ("h2", h2)):
        assert np.isfinite(p).all(), f"{caso}: {nombre} no finito"
        assert (p[vende] >= 0).all(), f"{caso}: {nombre} negativo"

    # antes del corte, c1 mas el cargo del intercambio
    grande = np.asarray(ins.cap) > LIMITE_NUMERAL_1_KW
    assert {ins.nombres[i] for i in np.flatnonzero(grande)} == NUMERAL_2.get(caso, set()), caso
    cargo2 = np.where(grande[:, None], ded, 0.0)
    np.testing.assert_allclose(h1[perm], (c1 + ded)[perm], rtol=0, atol=1e-9)
    np.testing.assert_allclose(h2[perm], (c1 + cargo2)[perm], rtol=0, atol=1e-9)

    # desde el corte, la mezcla de cesion mas el cargo
    iny_r, ret_r = residual_proporcional(G, D)
    f = fraccion_cedida(iny_r, ret_r, ins.mes_m)
    assert ((f >= 0) & (f <= 1)).all(), caso
    mezcla = np.broadcast_to(f * precio_cesion(iny_r, bolsa, ins.mes_m)
                             + (1 - f) * bolsa, c1.shape)
    np.testing.assert_allclose((h2 - cargo2)[~perm], mezcla[~perm],
                               rtol=0, atol=1e-9)

    # donde H2 no cambia nada, es c1 al bit; donde cambia, cambia en vendedores
    if caso in H2_IGUAL_A_C1:
        assert perm[vende].all() and not grande.any(), caso
        np.testing.assert_array_equal(h2, c1)
    else:
        assert (np.abs(h2 - c1)[vende] > 1e-9).any(), caso


CASO2_P2PCOM = {"E4", "E5", "P2"}


@pytest.mark.parametrize("caso", CASOS)
def test_lenta_piso_p2pcom_en_los_trece_casos(caso, datos):
    from gsa_directo import comun, evaluador
    ins = evaluador.prepara_caso(caso, datos)
    f = evaluador.aplica_factores(ins, comun.PUNTO_BASE)
    G, D, bolsa, techo = f["G"], f["D"], f["bolsa"], f["techo"]
    cap = np.asarray(ins.cap, dtype=float)
    caso2 = (capacidad_por_usuario_art18(cap, cap.size) > LIMITE_NUMERAL_1_KW
             or float(cap.sum()) > LIMITE_AGPE_KW)
    assert caso2 == (caso in CASO2_P2PCOM), caso
    ded_ind = deduccion_art25(f["cvm"], f["tolls"], cap)
    ded_fondo = f["cvm"] + (f["tolls"] if caso2 else 0.0)
    distintas = {ins.nombres[i] for i in range(cap.size)
                 if not np.array_equal(ded_fondo[i], ded_ind[i])}
    assert distintas == ({"UCC"} if caso in ("I1", "N1") else set()), caso
    piso, perm = piso_mecanismo(G, D, techo, ded_ind, bolsa, ins.mes_m, "p2pcom",
                                capacidad_kw=cap, deduccion_fondo=ded_fondo)
    assert np.isfinite(piso).all() and (piso == piso[0]).all(), caso
    cred = precio_permuta_por_periodo(techo, ded_fondo, ins.mes_m)
    lo = np.minimum(bolsa, cred.min(0)) - 1e-9
    hi = np.maximum(bolsa, cred.max(0)) + 1e-9
    assert ((piso[0] >= lo) & (piso[0] <= hi)).all(), caso
    llenos = perm.all(axis=0)
    np.testing.assert_allclose(piso[0][llenos], cred.mean(0)[llenos], rtol=0, atol=1e-9)
