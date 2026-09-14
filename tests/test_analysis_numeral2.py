"""Regresion de --analysis con una planta de mas de 100 kW (revision final).

C-1 e I-2: el corte por sub-periodos y los tres barridos de sensibilidad que
liquidaban con el proxy de la capacidad reciben la capacidad instalada real y
los peajes del numeral 2 del art. 25 de la CREG 174. Con 122,85 kW y peajes
no lanzan; sin peajes, el ValueError de siempre. Datos sinteticos del modelo
base de Chacon, con el mercado resuelto de verdad.

Y los peajes no finitos en las filas del numeral 2 se rechazan en vez de
aceptar un relleno.
"""
import warnings

import numpy as np
import pytest

from core.ems_p2p import AgentParams, EMSP2P, GridParams, HourlyResult, \
    SolverParams
from data.base_case_data import (GRID_PARAMS, get_agent_params,
                                 get_demand_profiles, get_generation_profiles,
                                 get_pde_weights)

warnings.filterwarnings("ignore")

# Una planta en el numeral 2 (el E4 de la matriz) y tres en el numeral 1;
# los dos consumidores del caso base no tienen planta.
CAP = np.array([122.85, 17.55, 17.55, 17.55, 0.0, 0.0])
PROS, CONS = [0, 1, 2, 3], [4, 5]


@pytest.fixture(scope="module")
def base():
    # Doce horas, de la madrugada a la tarde: hay deficit y excedente para
    # la planta grande (credito que el numeral 2 puede gravar) y el mercado
    # se resuelve en la mitad del tiempo del dia entero.
    G = get_generation_profiles()[:, 5:17]
    D = get_demand_profiles()[:, 5:17]
    N, T = D.shape
    agents = AgentParams(**get_agent_params())
    grid = GridParams(**GRID_PARAMS)
    solver = SolverParams(tau=0.001, t_span=(0.0, 0.005), n_points=120,
                          stackelberg_iters=2, parallel=False)
    res, G_klim, D_star = EMSP2P(agents, grid, solver).run(D, G)
    return dict(D=D_star, G=G, G_klim=G_klim, res=res, agents=agents,
                grid=grid, solver=solver, pde=get_pde_weights(),
                tolls=np.full((N, T), 250.0))


def _pgb(b, tolls, capacity=CAP):
    from analysis.sensitivity import run_sensitivity_pgb
    return run_sensitivity_pgb(
        D=b["D"], G=b["G"], G_klim=b["G_klim"], agents=b["agents"],
        grid_base=b["grid"], solver=b["solver"], p2p_results_base=b["res"],
        pi_gb_range=np.array([114.0, 300.0]), pde=b["pde"],
        prosumer_ids=PROS, verbose=False, tolls=tolls, capacity=capacity)


def _pv(b, tolls, factores=(1.0,)):
    from analysis.sensitivity import run_sensitivity_pv
    return run_sensitivity_pv(
        D=b["D"], G_base=b["G"], agents=b["agents"], grid=b["grid"],
        solver=b["solver"], pv_factors=np.array(factores), pde=b["pde"],
        prosumer_ids=PROS, verbose=False, tolls=tolls, capacity=CAP)


def _pgs(b, tolls):
    from analysis.sensitivity import run_sensitivity_pgs
    return run_sensitivity_pgs(
        D=b["D"], G=b["G"], agents=b["agents"], grid_base=b["grid"],
        solver=b["solver"], pde=b["pde"], prosumer_ids=PROS,
        consumer_ids=CONS, pi_gs_range=np.array([b["grid"].pi_gs]),
        verbose=False, capacity=CAP, tolls=tolls)


def _sub(b, tolls):
    from analysis.subperiod import run_subperiod_analysis
    return run_subperiod_analysis(
        D=b["D"], G=b["G"], agents=b["agents"], grid=b["grid"],
        solver=b["solver"], pde=b["pde"], prosumer_ids=PROS,
        consumer_ids=CONS, pi_gs=b["grid"].pi_gs, capacity=CAP,
        agent_names=[f"A{n + 1}" for n in range(6)], verbose=False,
        month_labels=None, component_c="auto", tolls=tolls)


ENTRADAS = {"SA-1 pgb": _pgb, "SA-2 pv": _pv, "SA-3 pgs": _pgs,
            "sub-periodos": _sub}


@pytest.mark.parametrize("nombre", list(ENTRADAS))
def test_con_peajes_no_lanza(base, nombre):
    out = ENTRADAS[nombre](base, base["tolls"])
    assert len(out) >= 1


@pytest.mark.parametrize("nombre", list(ENTRADAS))
def test_sin_peajes_lanza_el_error_de_siempre(base, nombre):
    with pytest.raises(ValueError, match="no se pasaron los peajes"):
        ENTRADAS[nombre](base, None)


def test_el_barrido_liquida_con_el_numeral_de_la_capacidad_real(base):
    # Con el proxy viejo (generacion media, pocos kW) C1 liquidaba la planta
    # grande con el numeral 1; con la capacidad real paga los peajes sobre
    # lo permutado y gana menos.
    real = _pgb(base, base["tolls"])
    proxy = _pgb(base, base["tolls"], capacity=None)
    for r, p in zip(real, proxy):
        assert r.net_per_agent["C1"][0] < p.net_per_agent["C1"][0]
        assert r.net_per_agent["C1"][1] == pytest.approx(
            p.net_per_agent["C1"][1], rel=1e-12)


def test_el_barrido_de_generacion_omite_el_punto_fuera_de_agpe(base):
    # Por diez, la planta grande pasa de 1 MW: el punto se omite con aviso
    # en vez de detener el barrido.
    out = _pv(base, base["tolls"], factores=(1.0, 10.0))
    assert [r.param_value for r in out] == [1.0]


def test_peajes_no_finitos_en_el_numeral_2_se_rechazan():
    from core.opciones_externas import deduccion_art25
    cvm = np.full((2, 3), 40.0)
    cap = np.array([122.85, 17.55])
    t = np.full((2, 3), 250.0)
    t[0, 1] = np.nan
    with pytest.raises(ValueError, match="no finitos"):
        deduccion_art25(cvm, t, cap)
    # En la fila del numeral 1 los peajes no se usan: un NaN alli no detiene
    # nada.
    t = np.full((2, 3), 250.0)
    t[1, 1] = np.nan
    out = deduccion_art25(cvm, t, cap)
    np.testing.assert_allclose(out, [[290.0] * 3, [40.0] * 3])


def test_run_comparison_no_rellena_los_peajes_del_numeral_2():
    from scenarios.comparison_engine import run_comparison
    D = np.array([[1.0, 5.0, 1.0, 5.0], [3.0, 3.0, 3.0, 3.0]])
    G = np.array([[4.0, 0.0, 4.0, 0.0], [0.0, 0.0, 0.0, 0.0]])
    t = np.full((2, 4), 250.0)
    t[0, 2] = np.nan
    with pytest.raises(ValueError, match="no finitos"):
        run_comparison(
            D=D, G_klim=G, G_raw=G, p2p_results=[HourlyResult(k=k)
                                                 for k in range(4)],
            pi_gs=np.full((2, 4), 800.0), pi_gb=150.0,
            pi_bolsa=np.full(4, 150.0), prosumer_ids=[0, 1],
            consumer_ids=[], capacity=np.array([122.85, 17.55]),
            component_c=40.0, tolls=t)
