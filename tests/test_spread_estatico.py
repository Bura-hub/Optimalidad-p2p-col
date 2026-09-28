"""El spread de ineficiencia estatica con el colectivo mensual (C-209, H-100).

La regla «importacion» de `pde_por_regla` reparte el fondo de cada mes en
proporcion a la importacion del mes de cada miembro; es la cota superior en energia del
reparto estatico. El spread en energia es el exceso a bolsa de C4 con el
reparto igual menos el de C4 con esa regla.

Actividad 3.2.
"""
import warnings

import numpy as np
import pytest

from scenarios.scenario_c4_creg101072 import (
    compute_pde_weights, pde_por_regla, run_c4_creg101072,
)

warnings.filterwarnings("ignore")


def _c4(D, G, pde, mes, pde_mensual=None, pb=None):
    T = D.shape[1]
    return run_c4_creg101072(
        D, G, np.full(D.shape, 800.0),
        np.full(T, 150.0) if pb is None else pb, pde,
        component_c=40.0, mode="monthly_hx", month_labels=mes,
        pde_mensual=pde_mensual)


def _energia(r):
    a = r["aggregate"]
    return a["total_E_permuta_t1"], a["total_E_excedente_t2"]


# Dos meses: el miembro 0 solo inyecta y el 1 solo importa. En el mes 1 el
# fondo (4) no pasa de la importacion (6); en el mes 2 (10 frente a 2) si.
D2 = np.array([[0.0, 0.0, 0.0, 0.0], [3.0, 3.0, 1.0, 1.0]])
G2 = np.array([[2.0, 2.0, 5.0, 5.0], [0.0, 0.0, 0.0, 0.0]])
MES2 = np.array([1, 1, 2, 2])


def test_importacion_convierte_en_credito_lo_que_el_igual_manda_a_bolsa():
    pm = pde_por_regla("importacion", G2, D2, MES2)
    np.testing.assert_allclose(pm[1], [0.0, 1.0])
    np.testing.assert_allclose(pm[2], [0.0, 1.0])
    igual = np.array([0.5, 0.5])
    r_igual = _c4(D2, G2, igual, MES2)
    r_imp = _c4(D2, G2, igual, MES2, pde_mensual=pm)
    cred_i, exc_i = _energia(r_igual)
    cred_m, exc_m = _energia(r_imp)
    # Igual: mes 1, el 0 recibe 2 y no importa (2 a bolsa), el 1 recibe 2 a
    # credito; mes 2, 5 y 5: el 0 manda 5, el 1 acredita 2 y manda 3.
    assert cred_i == pytest.approx(4.0)
    assert exc_i == pytest.approx(10.0)
    # Importacion: mes 1, los 4 al 1, todo credito; mes 2, 10 al 1: 2 de
    # credito y 8 a bolsa, el minimo posible (10 - 2).
    assert cred_m == pytest.approx(6.0)
    assert exc_m == pytest.approx(8.0)
    # Spread en energia: 2 kWh, todos del mes 1.
    assert exc_i - exc_m == pytest.approx(2.0)
    # Y en valor: esos 2 kWh pasan de la bolsa (150) al credito (800 - 40).
    dif = (r_imp["aggregate"]["total_net_benefit"]
           - r_igual["aggregate"]["total_net_benefit"])
    assert dif == pytest.approx(2.0 * (760.0 - 150.0))


def test_con_excedente_mayor_que_la_importacion_las_dos_saturan():
    # Solo el mes 2 del ejemplo: fondo 10, importacion 2.
    D, G, mes = D2[:, 2:], G2[:, 2:], MES2[2:]
    igual = np.array([0.5, 0.5])
    pm = pde_por_regla("importacion", G, D, mes)
    exc_i = _energia(_c4(D, G, igual, mes))[1]
    exc_m = _energia(_c4(D, G, igual, mes, pde_mensual=pm))[1]
    assert exc_i == pytest.approx(8.0)
    assert exc_m == pytest.approx(8.0)


def test_importacion_da_el_exceso_minimo_de_cada_mes():
    rng = np.random.default_rng(11)
    N, T = 4, 120
    D = rng.uniform(0, 3, (N, T))
    G = rng.uniform(0, 4, (N, T)) * (rng.random((N, T)) < 0.6)
    mes = np.repeat([1, 2, 3], 40)
    igual = np.full(N, 0.25)
    exc_min = 0.0
    for m in (1, 2, 3):
        idx = mes == m
        F = np.maximum(G[:, idx] - D[:, idx], 0).sum()
        I = np.maximum(D[:, idx] - G[:, idx], 0).sum()
        exc_min += max(F - I, 0.0)
    exc = {}
    for regla in ("igual", "consumo", "aporte", "generacion", "importacion"):
        pm = pde_por_regla(regla, G, D, mes)
        exc[regla] = _energia(_c4(D, G, igual, mes, pde_mensual=pm))[1]
    assert exc["importacion"] == pytest.approx(exc_min, rel=1e-12, abs=1e-9)
    for regla, e in exc.items():
        assert e >= exc["importacion"] - 1e-9, regla


def test_mes_sin_importacion_cae_al_igual():
    D = np.array([[1.0, 1.0, 0.0, 0.0], [1.0, 1.0, 2.0, 2.0]])
    G = np.array([[3.0, 3.0, 1.0, 1.0], [2.0, 2.0, 0.0, 0.0]])
    mes = np.array([1, 1, 2, 2])
    pm = pde_por_regla("importacion", G, D, mes)
    # Mes 1: nadie importa (G >= D en todos): reparto igual.
    np.testing.assert_array_equal(pm[1], [0.5, 0.5])
    # Mes 2: solo importa el 1.
    np.testing.assert_allclose(pm[2], [0.0, 1.0])


def test_importacion_falla_con_no_finitos():
    D = np.array([[1.0, np.nan], [1.0, 1.0]])
    G = np.ones((2, 2))
    with pytest.raises(ValueError, match="no finitos"):
        pde_por_regla("importacion", G, D, np.array([1, 1]))
    with pytest.raises(ValueError, match="no finitos"):
        pde_por_regla("importacion", D.T * np.inf, G, np.array([1, 1]))


def _pde_por_regla_anterior(regla, G, D, month_labels=None):
    """Copia literal de `pde_por_regla` antes de C-209, para comprobar que
    las cuatro reglas que ya existian no cambian."""
    G = np.maximum(np.asarray(G, dtype=float), 0.0)
    D = np.maximum(np.asarray(D, dtype=float), 0.0)
    N, T = G.shape
    etiquetas = (np.zeros(T, dtype=int) if month_labels is None
                 else np.asarray(month_labels))
    gen = G.mean(axis=1)
    out = {}
    for mes in np.unique(etiquetas):
        idx = np.flatnonzero(etiquetas == mes)
        if regla == "igual":
            out[int(mes)] = compute_pde_weights(np.ones(N), method="equal")
            continue
        if regla == "consumo":
            m = D[:, idx].sum(axis=1)
        elif regla == "aporte":
            m = np.maximum(G[:, idx] - D[:, idx], 0.0).sum(axis=1)
        elif regla == "generacion":
            m = gen
        else:
            raise ValueError(regla)
        out[int(mes)] = compute_pde_weights(m, method="excedentes_proportional")
    return out


@pytest.mark.parametrize("regla", ["igual", "consumo", "aporte", "generacion"])
@pytest.mark.parametrize("con_meses", [True, False])
def test_las_otras_reglas_no_cambian_al_bit(regla, con_meses):
    rng = np.random.default_rng(5)
    D = rng.uniform(-0.5, 3, (5, 96))
    G = rng.uniform(-0.2, 4, (5, 96))
    G[:, 48:60] = 0.0          # horas sin sol: un mes con poco aporte
    mes = np.repeat([202507, 202508, 202509, 202510], 24) if con_meses else None
    nuevo = pde_por_regla(regla, G, D, mes)
    viejo = _pde_por_regla_anterior(regla, G, D, mes)
    assert nuevo.keys() == viejo.keys()
    for k in viejo:
        assert np.array_equal(nuevo[k], viejo[k]), (regla, k)


def test_regla_desconocida_sigue_fallando():
    with pytest.raises(ValueError, match="desconocida"):
        pde_por_regla("capacidad", np.ones((2, 2)), np.ones((2, 2)))


def test_la_comparacion_guarda_la_energia_del_colectivo():
    from core.ems_p2p import HourlyResult
    from scenarios.comparison_engine import run_comparison
    rng = np.random.default_rng(8)
    D = rng.uniform(0, 3, (5, 48))
    G = rng.uniform(0, 4, (5, 48))
    mes = np.repeat([1, 2], 24)
    cr = run_comparison(
        D=D, G_klim=G, G_raw=G,
        p2p_results=[HourlyResult(k=k) for k in range(48)],
        pi_gs=np.full((5, 48), 800.0), pi_gb=150.0,
        pi_bolsa=np.full(48, 150.0), prosumer_ids=list(range(5)),
        consumer_ids=[], capacity=np.full(5, 17.55), component_c=40.0,
        tolls=np.full((5, 48), 300.0), month_labels=mes)
    fondo = float(np.maximum(G - D, 0).sum())
    e = cr.c4_energia
    assert e["credito_kwh"] + e["exceso_kwh"] == pytest.approx(fondo)
    for nombre in ("C4_11_fronteras", "C4_regla_consumo", "C4_regla_aporte",
                   "C4_regla_generacion", "C4_regla_importacion"):
        d = cr.contrafacticos[nombre]
        assert d["credito_kwh"] + d["exceso_kwh"] == pytest.approx(fondo)
        assert d["exceso_kwh"] >= cr.contrafacticos[
            "C4_regla_importacion"]["exceso_kwh"] - 1e-9
    imp = cr.contrafacticos["C4_regla_importacion"]
    assert e["exceso_kwh"] >= imp["exceso_kwh"] - 1e-9
    # El C4 del canon con el reparto igual no cambia: su energia es la de una
    # llamada directa.
    r = run_c4_creg101072(D, G, np.full((5, 48), 800.0), np.full(48, 150.0),
                          np.full(5, 0.2), np.full(5, 17.55), component_c=40.0,
                          tolls=np.full((5, 48), 300.0), mode="monthly_hx",
                          month_labels=mes)
    assert e["exceso_kwh"] == r["aggregate"]["total_E_excedente_t2"]
    assert cr.net_benefit["C4"] == pytest.approx(
        r["aggregate"]["total_net_benefit"], rel=1e-12)
