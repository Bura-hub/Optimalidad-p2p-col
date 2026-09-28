"""Pruebas del evaluador del GSA directo (T2, apartado 6.6 del diseno).

Actividad 4.1.

- factores sobre matrices sinteticas (6.6.1): la bolsa se escala ANTES del
  techo PES; f_peaje no toca la deduccion con plantas de hasta 100 kW y si
  con mas; e_G no cambia la capacidad instalada;
- el estado global del regimen no regulado en el inicializador, y el techo
  de E0 (703,6 a 817,0 COP/kWh);
- sobre un dia real sin horas fragiles: b x 1,7 y mu en {0,5; 2} no mueven
  nada (6.6.6), y f_peaje mueve el colectivo y no C1 ni el mercado;
- LENTA (6.6.5): el evaluador con los factores en 1 sobre un dia da los
  mismos beneficios que `main_simulation.main(single_day=...)`, que escribe
  en una carpeta temporal (nunca en outputs/ de la raiz).

Las de datos reales se saltan si no esta MedicionesMTE_v3.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from gsa_directo import comun, evaluador  # noqa: E402

MTE = Path(os.environ.get("MTE_ROOT", RAIZ / "MedicionesMTE_v3"))
HAY_DATOS = MTE.is_dir() and any(MTE.iterdir())
DIA = "2025-08-01"          # agosto de E0: sin horas fragiles (piloto)
datos_reales = pytest.mark.skipif(not HAY_DATOS,
                                  reason="sin MedicionesMTE_v3")


def _pes_abril_2025() -> float:
    return float(evaluador.aplica_bolsa(np.array([1e9]), 1.0, "2025-04-04")[0])


def _sinteticos(N=5, T=48, cap=17.55):
    rng = np.random.default_rng(0)
    return evaluador.Insumos(
        caso="E0", nombres=comun.INSTITUCIONES[:N],
        D=rng.uniform(5, 50, (N, T)), G=rng.uniform(0, 40, (N, T)),
        t0="2025-04-04", cap=np.full(N, cap),
        pi_gs=np.full((N, T), 750.0), pi_gs_eff=780.0, b=np.full(N, 240.0),
        month_labels=np.full(T, 202504), mes_m=np.array(["2025-04"] * T),
        bolsa_cruda=np.full(T, 300.0), cvm=np.full((N, T), 40.0),
        cu_G=np.full((N, T), 300.0), cu_Cvm=np.full((N, T), 40.0),
        cu_COT=np.full((N, T), 5.0), tolls=np.full((N, T), 200.0),
        mem=np.full((N, T), 20.0), pi_G=np.full((N, T), 345.0),
        pes=np.full(T, 900.0), pi_c5=np.full(T, 280.0), pi_gb=280.0,
        pi_ppa=300.0, fuente_bolsa="sintetica")


# ── 6.6.1: los factores sobre matrices sinteticas ──────────────────────────
def test_bolsa_se_escala_antes_del_techo():
    pes = _pes_abril_2025()
    assert 0 < pes < 1e9
    cruda = np.array([0.6 * pes, 0.2 * pes, 2.0 * pes])
    b = evaluador.aplica_bolsa(cruda, 4.0, "2025-04-04")
    # 0,6·PES·4 = 2,4·PES se recorta al PES: el techo va DESPUES del factor.
    np.testing.assert_allclose(b, [pes, 0.8 * pes, pes])
    # Una serie por encima del PES sale recortada al PES aun con factor 1.
    assert evaluador.aplica_bolsa(np.array([3 * pes]), 1.0,
                                  "2025-04-04")[0] == pes


def test_factores_se_aplican_donde_dice_el_diseno():
    ins = _sinteticos()
    x = np.array([2.0, 1.5, 1.1, 0.85, 1.05, 0.95])
    f = evaluador.aplica_factores(ins, x)
    np.testing.assert_array_equal(f["cvm"], ins.cvm * 2.0)
    np.testing.assert_array_equal(f["techo"], ins.pi_gs * 1.1)
    np.testing.assert_array_equal(f["tolls"], ins.tolls * 0.85)
    np.testing.assert_array_equal(f["G"], ins.G * 1.05)
    np.testing.assert_array_equal(f["D"], ins.D * 0.95)
    assert f["pi_gs_eff"] == pytest.approx(ins.pi_gs_eff * 1.1)
    np.testing.assert_allclose(f["bolsa"], 450.0)


def test_e_g_no_cambia_la_capacidad():
    ins = _sinteticos()
    cap = ins.cap.copy()
    evaluador.aplica_factores(ins, [1, 1, 1, 1, 1.05, 1])
    np.testing.assert_array_equal(ins.cap, cap)


def test_f_peaje_en_la_deduccion_solo_por_encima_de_100_kw():
    from core.opciones_externas import deduccion_art25
    for cap, debe_cambiar in ((17.55, False), (17.55 * 7, True)):
        ins = _sinteticos(cap=cap)
        d = [deduccion_art25(f["cvm"], f["tolls"], ins.cap)
             for f in (evaluador.aplica_factores(ins, [1, 1, 1, fp, 1, 1])
                       for fp in (0.85, 1.15))]
        assert (not np.array_equal(d[0], d[1])) == debe_cambiar


def test_entrada_no_finita_falla_en_voz_alta():
    with pytest.raises(ValueError):
        evaluador.aplica_factores(_sinteticos(), [1, np.nan, 1, 1, 1, 1])
    with pytest.raises(ValueError):
        evaluador.aplica_factores(_sinteticos(), [1, 1, 1])


def test_inicializador_pone_el_regimen_no_regulado():
    from data.cedenar_tariff import (INSTITUTION_PROFILE,
                                     aplicar_regimen_no_regulado)
    aplicar_regimen_no_regulado(False)
    historico = dict(INSTITUTION_PROFILE)
    evaluador.inicia_proceso()
    tras_inicio = dict(INSTITUTION_PROFILE)
    assert tras_inicio != historico
    aplicar_regimen_no_regulado(True)
    assert dict(INSTITUTION_PROFILE) == tras_inicio


# ── Con datos reales ────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def datos(tmp_path_factory):
    if not HAY_DATOS:
        pytest.skip("sin MedicionesMTE_v3")
    return evaluador.carga_mte(str(MTE),
                               tmp_path_factory.mktemp("cache_mte"))


@datos_reales
def test_techo_de_e0_no_regulado(datos):
    ins = evaluador.prepara_caso("E0", datos)
    assert ins.pi_gs.shape == (5, 6144)
    assert ins.pi_gs.min() == pytest.approx(703.6, abs=0.05)
    assert ins.pi_gs.max() == pytest.approx(817.0, abs=0.05)
    assert ins.fuente_bolsa.startswith("cache_api")


@pytest.fixture(scope="module")
def dia(datos):
    return evaluador.prepara_caso("E0", datos, dia=DIA)


@datos_reales
def test_un_dia_salidas_finitas_y_sin_cuantales(dia):
    y = evaluador.evalua(dia, comun.PUNTO_BASE)
    cols = comun.columnas_salida(dia.nombres)
    assert list(y) == cols and len(cols) == 14 + 1 + 4 + 15
    assert all(np.isfinite(v) for v in y.values())
    assert y["n_cuantal"] == 0 and y["retiros"] == 0
    assert y["C2"] == pytest.approx(y["P2P"], rel=1e-9)


@datos_reales
def test_b_y_mu_sin_efecto_en_un_dia_sin_horas_fragiles(dia):
    y0 = evaluador.evalua(dia, comun.PUNTO_BASE)
    assert evaluador.evalua(dia, comun.PUNTO_BASE, b_factor=1.7) == y0
    for mu in (0.5, 2.0):
        assert evaluador.evalua(dia, comun.PUNTO_BASE, mu=mu) == y0


@datos_reales
def test_f_peaje_mueve_el_colectivo_y_no_c1(dia):
    a = evaluador.evalua(dia, [1, 1, 1, 0.85, 1, 1])
    b = evaluador.evalua(dia, [1, 1, 1, 1.15, 1, 1])
    assert a["C1"] == b["C1"] and a["P2P"] == b["P2P"]
    assert a["C4"] > b["C4"]
    assert a["P2P_colectivo"] > b["P2P_colectivo"]


@datos_reales
def test_un_dia_contra_main_lenta(dia, tmp_path):
    """6.6.5: el evaluador y `main()` dan los mismos beneficios en un dia.
    `main()` escribe en `tmp_path` (--out-dir), nunca en la raiz."""
    import main_simulation as ms
    ms.main(use_real_data=True, full_horizon=False, run_analysis=False,
            single_day=DIA, include_c5=True, out_dir=str(tmp_path),
            metodo="reposo", modo_presupuesto="sigma",
            regla_precio="uniforme", despacho_vendedores="piso",
            exencion_contribucion=True, procesos=2)
    res = pd.read_excel(tmp_path / "outputs" / "resultados_comparacion.xlsx",
                        sheet_name="Resumen")
    canon = dict(zip(res["Escenario"], res["Ganancia_neta_COP"]))
    y = evaluador.evalua(dia, comun.PUNTO_BASE)
    for e in ("P2P", "P2P_colectivo", "C1", "C2", "C3", "C4", "C5"):
        assert y[e] == pytest.approx(canon[e], rel=1e-9, abs=1e-6), e

def test_despacho_defecto_y_valores():
    """C-207 (revision C1-C8): el defecto de `despacho` es «piso», la regla
    de la matriz canonica, en la funcion publica y en la interna (la que usa
    la compuerta del punto base, que reproduce el canon al peso con el
    defecto); un valor desconocido falla en voz alta antes de evaluar."""
    import inspect
    assert inspect.signature(
        evaluador.evalua_comparacion).parameters["despacho"].default == "piso"
    assert inspect.signature(
        evaluador._evalua).parameters["despacho"].default == "piso"
    with pytest.raises(ValueError, match="despacho"):
        evaluador.evalua_comparacion(None, comun.PUNTO_BASE, despacho="merito")
