"""
test_fa3_cumplimiento.py
-------------------------
Tarea 19, Step 3b (hallazgo de la re-revisión de la tarea 17).

`analyze_withdrawal_risk` (FA-3, analysis/feasibility.py) dejaba
`compliant = True` fijo, sin reasignarlo nunca: `community_at_risk` salía
siempre falso y `n_risky_withdrawals` siempre cero, aunque el comentario del
propio archivo (CAL-41) ya anunciaba la regla que debía aplicarse. Como FA-3
corre en el modo ligero (D27) en las trece corridas del servidor, ese
resultado era estructural y no medido: la Fig. 17 (plot_robustness_c4)
habría dicho siempre «Ningún retiro invalida el régimen AGRC».

El arreglo conecta `compliant` a la MISMA regla y la MISMA constante que el
motor ya aplica al colectivo completo
(`scenarios/scenario_c4_creg101072.py::_validate_capacity`): la suma de
capacidades del AC restante no puede exceder el límite AGPE de la UPME
281/2015 (`AGPE_LIMIT_KW` = 1000 kW). CAL-41 retiró la regla del 10 % y la
de 100 kW como condición de cumplimiento —el Caso 2 del art. 20 es un
régimen válido—, así que estas pruebas NO las restauran como condición de
`compliant`; solo verifican que siguen apareciendo en `violated_rules`.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pytest

from analysis.feasibility import analyze_withdrawal_risk
from scenarios.scenario_c4_creg101072 import AGPE_LIMIT_KW


def _comunidad_sintetica(capacidad_kw):
    """Cinco fronteras sintéticas, demanda constante y excedente diurno.

    Reutilizable con distinta capacidad instalada para mover el resultado
    de `compliant` sin cambiar nada más del escenario.
    """
    N, T = 5, 24
    D = np.full((N, T), 3.0)
    G = np.zeros((N, T))
    # Pico diurno proporcional a la capacidad instalada (factor de planta
    # 0,6), como en un panel real: con 17,55 kW el pico queda muy por debajo
    # de los 100 kW del art. 20 num. 1 ii; con 300 kW lo supera.
    G[:, 8:18] = float(capacidad_kw) * 0.6
    G_klim = G.copy()

    agent_names  = [f"A{i+1}" for i in range(N)]
    prosumer_ids = list(range(N))
    pi_gb    = 200.0
    pi_bolsa = np.full(T, pi_gb)
    pde      = np.full(N, 1.0 / N)
    capacity = np.full(N, float(capacidad_kw))

    # Beneficios base cualesquiera (no intervienen en la regla de capacidad).
    net_benefit_p2p     = np.full(N, 1000.0)
    net_benefit_c4_full = np.full(N, 900.0)

    return dict(
        D=D, G=G, G_klim=G_klim,
        pi_gs=800.0, pi_gb=pi_gb, pi_bolsa=pi_bolsa, pde=pde,
        prosumer_ids=prosumer_ids, agent_names=agent_names,
        net_benefit_p2p=net_benefit_p2p,
        net_benefit_c4_full=net_benefit_c4_full,
        capacity=capacity, verbose=False,
    )


def test_capacidad_real_ningun_retiro_es_riesgoso():
    """17,55 kW por planta (Spec 4.11, H-67): muy por debajo del límite AGPE.

    Con la capacidad instalada real, la comunidad restante nunca se acerca
    al límite de 1 MW: ningún retiro debe marcar riesgo.
    """
    kwargs = _comunidad_sintetica(17.55)
    report = analyze_withdrawal_risk(**kwargs)

    assert report.community_at_risk is False
    assert report.n_risky_withdrawals == 0
    assert all(info["compliant"] for info in report.by_agent.values())


def test_capacidad_que_excede_el_limite_agpe_marca_riesgo():
    """Capacidad sintética que, al retirar cualquiera, deja > 1 MW.

    5 × 300 kW = 1500 kW instalados; al retirar un agente quedan 1200 kW,
    por encima de `AGPE_LIMIT_KW` (1000 kW, UPME 281/2015). Ese es el único
    criterio que CAL-41 conserva como invalidante del AGRC (Caso 3): la
    comunidad restante debe marcarse en riesgo para los cinco retiros.
    """
    kwargs = _comunidad_sintetica(300.0)
    report = analyze_withdrawal_risk(**kwargs)

    assert float(np.sum(kwargs["capacity"])) - 300.0 > AGPE_LIMIT_KW
    assert report.community_at_risk is True
    assert report.n_risky_withdrawals == len(kwargs["prosumer_ids"])
    for info in report.by_agent.values():
        assert info["compliant"] is False
        assert any("Caso3" in regla for regla in info["violated_rules"])


def test_las_reglas_10pct_y_100kw_no_condicionan_compliant():
    """CAL-41: el Caso 2 (10 % o 100 kW) sigue siendo un AGRC válido.

    Con 300 kW por planta el límite de 100 kW por usuario también se supera,
    y con cuatro agentes restantes el PDE igual (25 %) supera el 10 %. Ambas
    deben seguir apareciendo en `violated_rules` como diagnóstico, pero la
    causa real de `compliant=False` en este escenario es solo el límite AGPE
    (ya cubierto arriba); aquí se confirma que las dos reglas de Caso 2 se
    siguen informando sin ser, por sí solas, las que deciden `compliant`.
    """
    kwargs = _comunidad_sintetica(300.0)
    report = analyze_withdrawal_risk(**kwargs)

    for info in report.by_agent.values():
        reglas = info["violated_rules"]
        assert "100kW→Caso2" in reglas
        assert "PDE≥10%→Caso2" in reglas
