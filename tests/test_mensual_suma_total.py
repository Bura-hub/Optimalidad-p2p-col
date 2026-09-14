"""Los meses y los dias suman exactamente el total (C-165, C-177).

Un dia no es un periodo de facturacion: reliquidarlo por separado rompe el
cupo del mes. La serie diaria se obtiene sumando el desglose horario.
"""
import warnings

import numpy as np
import pytest

from core.ems_p2p import HourlyResult
from scenarios.comparison_engine import run_comparison

warnings.filterwarnings("ignore")


def _caso():
    rng = np.random.default_rng(12)
    N, T = 3, 96
    D = rng.uniform(0, 3, (N, T))
    G = rng.uniform(0, 4, (N, T))
    res = []
    for k in range(T):
        exc = np.maximum(G[:, k] - D[:, k], 0)
        dfc = np.maximum(D[:, k] - G[:, k], 0)
        s, b = list(np.flatnonzero(exc > 0)), list(np.flatnonzero(dfc > 0))
        if s and b:
            corto = min(exc[s].sum(), dfc[b].sum())
            P = np.outer(exc[s] / exc[s].sum(), dfc[b] / dfc[b].sum()) * corto
            res.append(HourlyResult(k=k, P_star=P,
                                    pi_star=np.full(len(b), 600.0),
                                    seller_ids=s, buyer_ids=b))
        else:
            res.append(HourlyResult(k=k))
    kw = dict(D=D, G_klim=G, G_raw=G, p2p_results=res,
              pi_gs=np.full((N, T), 800.0), pi_gb=150.0,
              pi_bolsa=rng.uniform(80, 400, T), prosumer_ids=list(range(N)),
              consumer_ids=[], month_labels=np.repeat([202507, 202508], 48),
              pde=np.full(N, 1 / N), capacity=np.full(N, 17.55),
              component_c=40.0, tolls=np.full((N, T), 300.0))
    return kw


def test_la_suma_de_los_meses_es_el_total():
    from analysis.monthly_report import compute_monthly_metrics
    kw = _caso()
    cr = run_comparison(**kw)
    meses = compute_monthly_metrics(**kw)
    for esc in ("P2P", "C1", "C4"):
        suma = sum(m["net_benefit"][esc] for m in meses)
        assert suma == pytest.approx(cr.net_benefit[esc], rel=1e-10), esc


def test_con_neto_horario_los_meses_suman_el_total_en_todas_las_columnas():
    # I-5 (revision final): con el desglose horario del motor, cada columna
    # del informe mensual suma el total de run_comparison. C2 es el contrato
    # interno (lleva piso) y no el PPA de CAL-37, y entra P2P_colectivo.
    from analysis.monthly_report import compute_monthly_metrics
    kw = _caso()
    N, T = kw["D"].shape
    cr = run_comparison(**kw, piso_agente=np.full((N, T), 500.0),
                        include_c5=True)
    meses = compute_monthly_metrics(**kw, include_c5=True,
                                    neto_horario=cr.neto_horario)
    columnas = set(meses[0]["net_benefit"])
    assert {"P2P", "P2P_colectivo", "C1", "C2", "C3", "C4", "C4_mensual",
            "C5"} <= columnas
    for esc in columnas:
        suma = sum(m["net_benefit"][esc] for m in meses)
        assert suma == pytest.approx(cr.net_benefit[esc], rel=1e-10), esc


def test_la_suma_de_los_dias_es_el_total():
    from main_simulation import _compute_daily_series
    kw = _caso()
    cr = run_comparison(**kw)
    s = _compute_daily_series(cr, 96, 1.0)
    assert len(s) == 4
    assert s["nb_p2p"].sum() == pytest.approx(cr.net_benefit["P2P"], rel=1e-12)
    assert s["nb_c4"].sum() == pytest.approx(cr.net_benefit["C4"], rel=1e-12)
