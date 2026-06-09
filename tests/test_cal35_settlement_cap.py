"""CAL-35 — settlement P2P con techo por agente (ADR-0035).

Fixture: 3 agentes, 2 horas. Agente 0 = vendedor comercial (956);
agente 1 = comprador OFICIAL (797); agente 2 = comprador comercial (956).
Hora 0 con mercado a pi_star=906 (sobre el techo del oficial);
hora 1 sin mercado.
"""
import numpy as np
import pytest

from core.ems_p2p import HourlyResult
from scenarios.comparison_engine import (
    _p2p_monetary_benefit, _p2p_flow_breakdown, _effective_buyer_prices,
)

PI_GB = 182.0


def _fixture(pi_gs_oficial=797.0):
    D      = np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]])
    G_klim = np.array([[4.0, 0.0], [0.0, 0.0], [0.0, 0.0]])
    pi_gs  = np.array([[956.0, 956.0],
                       [pi_gs_oficial, pi_gs_oficial],
                       [956.0, 956.0]])
    results = [
        HourlyResult(k=0, P_star=np.array([[1.0, 2.0]]),
                     pi_star=np.array([906.0, 906.0]),
                     seller_ids=[0], buyer_ids=[1, 2]),
        HourlyResult(k=1),  # sin mercado
    ]
    return D, G_klim, pi_gs, results


def test_helper_capa_por_comprador():
    pi_gs = np.array([[956.0], [797.0], [956.0]])
    out = _effective_buyer_prices(np.array([906.0, 906.0]), [1, 2], pi_gs, 0)
    assert out.tolist() == [797.0, 906.0]


def test_homogeneo_es_noop():
    """Con techos homogéneos (956 para todos) el cap es min(906,956)=906:
    el resultado coincide con la fórmula histórica que usaba pi_star crudo."""
    D, G_klim, pi_gs, results = _fixture(pi_gs_oficial=956.0)
    net = _p2p_monetary_benefit(results, D, G_klim, pi_gs, PI_GB,
                                prosumer_ids=[0],
                                pi_bolsa=np.array([182.0, 182.0]))
    # vendedor: auto 956 + 906*3 = 3674 ; compradores: (956-906)*1 y *2
    assert net[0] == pytest.approx(956.0 + 906.0 * 3.0)
    assert net[1] == pytest.approx(50.0)
    assert net[2] == pytest.approx(100.0)


def test_heterogeneo_comprador_oficial_no_paga_sobre_su_techo():
    D, G_klim, pi_gs, results = _fixture()
    net = _p2p_monetary_benefit(results, D, G_klim, pi_gs, PI_GB,
                                prosumer_ids=[0],
                                pi_bolsa=np.array([182.0, 182.0]))
    # vendedor cobra 797 al oficial y 906 al comercial: auto 956 + 797 + 1812
    assert net[0] == pytest.approx(956.0 + 797.0 * 1.0 + 906.0 * 2.0)
    # comprador oficial ya NO sobre-paga: ahorro 0 (no negativo)
    assert net[1] == pytest.approx(0.0)
    assert net[2] == pytest.approx(100.0)


def test_total_comunitario_invariante_al_cap():
    """Vendedor + comprador = pi_gs[i]·kWh: el precio se cancela. El total con
    cap (heterogéneo) y sin necesidad de cap (homogéneo) cumple la identidad."""
    for pgs_of in (797.0, 956.0):
        D, G_klim, pi_gs, results = _fixture(pi_gs_oficial=pgs_of)
        net = _p2p_monetary_benefit(results, D, G_klim, pi_gs, PI_GB,
                                    prosumer_ids=[0],
                                    pi_bolsa=np.array([182.0, 182.0]))
        esperado = 956.0 + (pgs_of * 1.0 + 956.0 * 2.0)  # auto + Σ pgs_i·kWh
        assert float(np.sum(net)) == pytest.approx(esperado)


def test_flow_breakdown_usa_precio_efectivo():
    D, G_klim, pi_gs, results = _fixture()
    prima, ahorro = _p2p_flow_breakdown(results, pi_gs, PI_GB)
    # income capado = 797+1812 = 2609; baseline = 3*182 = 546
    assert prima == pytest.approx(2609.0 - 546.0)
    # oficial: 0 ; comercial: (956-906)*2 = 100
    assert ahorro == pytest.approx(100.0)
