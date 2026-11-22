"""El corte secuencial (AE-4) sobre los datos reales: la cadena por meses es el
motor al bit (S1) en E0 y E3 completos, y la FIFO del saldo es el Anexo 4
sobre los residuales del canon en los trece casos (S2).

Actividades 2.2 y 3.3. Revisión r1 del artículo; M1 de la auditoría del
2026-11-21. El motor se arma como `gsa_directo.evaluador` (la réplica de
`main()` por la vía del reposo). Lenta: unos dos minutos. Uso:
    .venv/Scripts/python.exe -m pytest tests/test_corte_secuencial.py -q
"""
from __future__ import annotations

import dataclasses
import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core.corte_secuencial import liquida_fifo, resuelve_secuencial  # noqa: E402
from core.opciones_externas import deduccion_art25, piso_residual, reparto_anexo4  # noqa: E402

MTE = Path(os.environ.get("MTE_ROOT", RAIZ / "MedicionesMTE_v3"))
MATRIZ_CANON = Path(os.environ.get("MATRIZ_CANON") or (
    RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19" / "SALIDAS_SERVIDOR" / "matriz_reposo"))
if not MATRIZ_CANON.is_absolute():
    MATRIZ_CANON = RAIZ / MATRIZ_CANON
CASOS = ("E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1", "CV2", "SINU")
pytestmark = pytest.mark.skipif(not (MTE.is_dir() and MATRIZ_CANON.is_dir()),
                                reason="sin los datos del MTE o sin la matriz del canon")


@pytest.fixture(scope="module")
def datos(tmp_path_factory):
    from gsa_directo import evaluador
    return evaluador.carga_mte(str(MTE), tmp_path_factory.mktemp("cache_mte"))


def _motor(caso, datos):
    from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams
    from data.base_case_data import GRID_PARAMS_REAL
    from gsa_directo import comun, evaluador
    ins = evaluador.prepara_caso(caso, datos)
    f = evaluador.aplica_factores(ins, comun.PUNTO_BASE)
    G, D, bolsa, techo = f["G"], f["D"], f["bolsa"], f["techo"]
    ded = deduccion_art25(f["cvm"], f["tolls"], ins.cap)
    piso, _ = piso_residual(G, D, techo, ded, bolsa, ins.mes_m)
    N = D.shape[0]
    grid = GridParams(**{**GRID_PARAMS_REAL, "pi_gs": f["pi_gs_eff"]}, pi_gs_agente=techo, pi_gb_agente=piso)
    agents = AgentParams(N=N, a=np.zeros(N), b=ins.b, c=np.zeros(N), lam=np.full(N, 100.0),
                         theta=np.full(N, 0.5), etha=np.full(N, 0.1))
    solver = SolverParams(
        tau=0.001, t_span=(0.0, 0.005), n_points=150, stackelberg_iters=2, parallel=False, metodo="reposo",
        t_span_acoplado=0.05, rtol_acoplado=1e-6, arranque_acoplado="factible", modo_presupuesto="sigma",
        sigma_nivel=None, regla_precio="uniforme", despacho_vendedores="piso", mu_cuantal=1.0,
        buyer_competition="aggregate", plazo_hora_s=None)
    return EMSP2P(agents, grid, solver), D, G, techo, ded, bolsa, ins.mes_m, piso


def _iguales(r0, r1):
    assert len(r0) == len(r1)
    malas = []
    for a, b in zip(r0, r1):
        for f in dataclasses.fields(a):
            if f.name in ("segundos", "tr"):
                continue
            x, y = getattr(a, f.name), getattr(b, f.name)
            if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
                ok = (x is None and y is None) or (x is not None and y is not None
                                                   and np.array_equal(np.asarray(x), np.asarray(y), equal_nan=True))
            else:
                try:
                    ok = bool(x == y) or (x != x and y != y)
                except ValueError:
                    ok = np.array_equal(np.asarray(x), np.asarray(y))
            if not ok:
                malas.append((a.k, f.name))
    return malas


@pytest.mark.parametrize("caso", ["E0", "E3"])
def test_lenta_la_cadena_fija_es_el_motor_en_el_horizonte(caso, datos):
    e, D, G, techo, ded, bolsa, mes, piso = _motor(caso, datos)
    r0, _, _ = e.run(D, G)
    r1, p1, _, _ = resuelve_secuencial(e, D, G, techo, ded, bolsa, mes, regla="fija", procesos=1)
    assert not _iguales(r0, r1)[:5]
    assert np.array_equal(p1, piso)


@pytest.mark.parametrize("caso", CASOS)
def test_lenta_fifo_es_el_anexo4_en_los_residuales_del_canon(caso):
    ag = pd.concat(pd.read_parquet(p) for p in sorted(glob.glob(
        str(MATRIZ_CANON / caso / "almacen" / "m1" / "agentes" / "*.parquet"))))
    piv = lambda c: ag.pivot(index="agente", columns="hora", values=c).to_numpy(float)
    sr = np.maximum(piv("sobrante") - piv("vende_p2p"), 0.0)
    dr = np.maximum(piv("faltante") - piv("compra_p2p"), 0.0)
    mes = ag[ag.agente == ag.agente.iloc[0]].sort_values("hora").mes.to_numpy()
    cr, ex = liquida_fifo(sr, dr, mes)
    cr4, ex4, _ = reparto_anexo4(sr, dr, mes)
    assert np.abs(ex - ex4).max() <= 1e-9 and np.abs(cr - cr4).max() <= 1e-9, caso
