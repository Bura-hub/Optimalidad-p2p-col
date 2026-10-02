"""Pruebas de C2 como PPA (C2ppa, CANON §14.22) y del P2P colectivo (P2Pcom,
§14.23) en el evaluador del GSA directo (2026-10-02).

Actividades 4.1 y 4.2 (las brechas contra los mecanismos).

Sin datos (segundos, corren tambien en el servidor, en el paso 2 de la
accion):

- la clasificacion del art. 20 sin la regla del 10 % por la capacidad
  instalada (la de `p2p_comunitario.caso_art20_sin_10`);
- la deduccion de cada caso;
- los flujos del mercado: pagos internos que suman cero con el techo del
  comprador (CAL-35);
- sin intercambio y con la deduccion del caso 2, el P2P colectivo portado es
  `run_c4_creg101072` mensual de produccion con el PDE igual;
- C2ppa es `run_c2_bilateral` de produccion con `pi_contrato` = PP;
- si estan los guiones de los puntos P y PC, la liquidacion portada es la de
  `p2p_comunitario.valor_comunitario` sobre los mismos datos sinteticos.

Con datos (LENTAS: `-k "not lenta"` las salta; el servidor no tiene los
puntos P y PC). En el punto base, todos los factores en 1, el evaluador
reproduce C2ppa de `SALIDAS_SERVIDOR/c2_ppa_2026-10-02/` y P2Pcom de
`SALIDAS_SERVIDOR/p2p_comunitario_2026-10-02/`, institucion por institucion y
en la comunidad, en E0 (caso 1, nadie agota), E2 (caso 1, credito agotado en
parte de los meses) y E4 (caso 2), y las salidas de D75 no cambian frente al
`punto_base.csv` del canon (entrega del 2026-09-27).

TOLERANCIAS. Las del paquete en el punto base (`compuerta_punto_base`: la
menor entre 1e-6 relativa y medio peso), salvo P2Pcom de la COMUNIDAD, que se
compara al peso (1 COP): los puntos P y PC liquidan con las series del
almacen, guardadas en float32 (G, D, el techo y los flujos), y en E4 la suma
de esas diferencias llega a 0,58 COP (0,75 en P2). Medido el 2026-10-02: con
los mismos flujos el portado y el evaluador difieren en 0,035 COP; lo demas
es la precision de la referencia. Por institucion, todo cae bajo 0,5 COP.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import warnings
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from gsa_directo import comun, evaluador  # noqa: E402

MTE = Path(os.environ.get("MTE_ROOT", RAIZ / "MedicionesMTE_v3"))
HAY_DATOS = MTE.is_dir() and any(MTE.iterdir())
P_CSV = RAIZ / "SALIDAS_SERVIDOR" / "c2_ppa_2026-10-02" / "c2_ppa_13casos.csv"
PC_CSV = (RAIZ / "SALIDAS_SERVIDOR" / "p2p_comunitario_2026-10-02"
          / "p2p_comunitario_13casos.csv")
PUNTO_BASE_CANON = (RAIZ / "SALIDAS_SERVIDOR"
                    / "entrega_gsa_directo_completo_2026-09-27"
                    / "SALIDAS_SERVIDOR" / "gsa_directo" / "base"
                    / "punto_base.csv")
GUION_PC = (RAIZ / "reformateo" / "documento" / "scripts" / "articulo"
            / "p2p_comunitario.py")
HUELLAS = RAIZ / "Documentos" / "canon_2026-09" / "HUELLAS.csv"
TOL_PESO = 0.5           # la de compuerta_punto_base
TOL_COMUNIDAD_PCOM = 1.0  # al peso: la referencia es float32 (docstring)


# ── Sin datos ───────────────────────────────────────────────────────────────
def test_clasificacion_del_art20_sin_la_regla_del_10():
    """La de §14.23: CINAC = suma / fronteras <= 100 kW y suma <= 1 MW."""
    f = evaluador.caso_art20_sin_10
    assert f([17.55] * 5, 5)[0] == 1                                   # E0
    assert f([122.85] * 5, 5)[:2] == (2, pytest.approx(122.85))        # E4
    assert f([175.5] * 5, 5)[0] == 2                                   # E5
    caso, cin, suma = f([17.55, 17.55, 150.209928, 17.55, 17.55], 5)   # I1
    assert caso == 1 and cin == pytest.approx(44.081986)
    assert suma == pytest.approx(220.409928)
    assert f([17.55] * 4, 4)[0] == 1                                   # SINU
    assert f([100.0] * 5, 5)[0] == 1 and f([100.01] * 5, 5)[0] == 2
    assert f([300.0] * 5, 5)[0] == 2                                   # > 1 MW


def test_deduccion_de_cada_caso():
    cvm = np.full((2, 3), 40.0)
    tolls = np.full((2, 3), 250.0)
    np.testing.assert_array_equal(evaluador.deduccion_pcom(1, cvm, tolls), cvm)
    np.testing.assert_array_equal(evaluador.deduccion_pcom(2, cvm, tolls),
                                  cvm + tolls)
    with pytest.raises(ValueError, match="caso"):
        evaluador.deduccion_pcom(3, cvm, tolls)


def _sinteticos(N=4, T=96, semilla=11):
    rng = np.random.default_rng(semilla)
    G = np.clip(rng.normal(5.0, 4.0, (N, T)), 0.0, None)
    D = np.clip(rng.normal(4.0, 2.0, (N, T)), 0.0, None)
    CU = np.repeat(rng.uniform(600.0, 800.0, (N, 3)), T // 3, axis=1)
    pb = rng.uniform(80.0, 500.0, T)
    mes = np.repeat(["2025-04", "2025-05", "2025-06"], T // 3)
    Cv = np.repeat(rng.uniform(30.0, 50.0, (N, 1)), T, axis=1)
    Th = np.repeat(rng.uniform(200.0, 300.0, (N, 1)), T, axis=1)
    s, d = np.maximum(G - D, 0.0), np.maximum(D - G, 0.0)
    tr = np.minimum(s.sum(0), d.sum(0))
    ss, dd = s.sum(0), d.sum(0)
    v = np.where(ss > 0, s * tr / np.where(ss > 0, ss, 1.0), 0.0)
    q = np.where(dd > 0, d * tr / np.where(dd > 0, dd, 1.0), 0.0)
    return dict(N=N, T=T, G=G, D=D, CU=CU, pb=pb, mes=mes, Cv=Cv, Th=Th,
                v=v, q=q)


def test_flujos_del_mercado_y_pagos_con_el_techo():
    """Dos horas: vendedores 0 y 1, compradores 2 y 3; en la segunda el
    precio del mercado pasa del techo del comprador 3 y paga su techo."""
    techo = np.array([[700.0] * 2, [700.0] * 2, [650.0] * 2, [600.0, 610.0]])
    res = [SimpleNamespace(k=0, seller_ids=[0, 1], buyer_ids=[2, 3],
                           P_star=np.array([[1.0, 2.0], [0.5, 0.0]]),
                           pi_star=np.array([500.0, 550.0])),
           SimpleNamespace(k=1, seller_ids=[1], buyer_ids=[3],
                           P_star=np.array([[3.0]]),
                           pi_star=np.array([640.0])),
           SimpleNamespace(k=1, seller_ids=[], buyer_ids=[], P_star=None,
                           pi_star=None)]
    v, q, pag = evaluador.flujos_mercado(res, techo, 4, 2)
    np.testing.assert_allclose(v[:, 0], [3.0, 0.5, 0.0, 0.0])
    np.testing.assert_allclose(q[:, 0], [0.0, 0.0, 1.5, 2.0])
    np.testing.assert_allclose(pag[:, 0], [500 + 1100, 250, -750, -1100])
    np.testing.assert_allclose(pag[:, 1], [0, 3 * 610.0, 0, -3 * 610.0])
    assert np.abs(pag.sum(axis=0)).max() < 1e-9


def test_sin_intercambio_y_en_el_caso_2_es_c4_de_produccion():
    """La guarda que corre en cada evaluacion, aqui sobre datos sinteticos:
    con v = q = pagos = 0 y la deduccion del caso 2, el P2P colectivo
    portado es `run_c4_creg101072` mensual (Anexo 4, PDE igual)."""
    from scenarios.scenario_c4_creg101072 import run_c4_creg101072
    x = _sinteticos()
    N, T = x["N"], x["T"]
    cero = np.zeros((N, T))
    ded2 = evaluador.deduccion_pcom(2, x["Cv"], x["Th"])
    rep, _ = evaluador.valor_p2p_colectivo(x["G"], x["D"], cero, cero, cero,
                                           x["CU"], ded2, x["mes"], x["pb"])
    etiquetas = np.array([int(m.replace("-", "")) for m in x["mes"]])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        r = run_c4_creg101072(x["D"], x["G"], x["CU"], x["pb"],
                              np.full(N, 1.0 / N), np.full(N, 17.55),
                              component_c=x["Cv"], mode="monthly_hx",
                              month_labels=etiquetas, tolls=x["Th"], caso=2)
    mot = np.array([r["per_agent"][n]["net_benefit"] for n in range(N)])
    np.testing.assert_allclose(rep, mot, rtol=1e-12, atol=1e-6)


def test_c2ppa_es_run_c2_bilateral_de_produccion():
    from scenarios.scenario_c2_bilateral import run_c2_bilateral
    x = _sinteticos()
    pp = 287.41
    b = evaluador.valor_c2_ppa(x["G"], x["D"], x["CU"], pp)
    r = run_c2_bilateral(x["D"], x["G"], x["CU"], 0.0, 0.0,
                         list(range(x["N"])), [], pi_bolsa=x["pb"], dt=1.0,
                         pi_contrato=pp, cobertura_contrato=1.0)
    ref = np.array([r["per_agent"][n]["net_benefit"] for n in range(x["N"])])
    np.testing.assert_allclose(b, ref, rtol=1e-12, atol=1e-6)
    # lineal en PP con pendiente el excedente
    s = np.maximum(x["G"] - x["D"], 0.0).sum(axis=1)
    np.testing.assert_allclose(
        evaluador.valor_c2_ppa(x["G"], x["D"], x["CU"], pp + 10.0) - b,
        10.0 * s, rtol=1e-12)


@pytest.mark.skipif(not (GUION_PC.exists() and HUELLAS.exists()),
                    reason="sin el guion del punto PC o sin HUELLAS.csv")
def test_la_liquidacion_portada_es_la_del_punto_pc():
    """Sobre los mismos datos sinteticos, la del evaluador es la de
    `p2p_comunitario.valor_comunitario` (con `atribucion_supuestos.colectivo`)
    con el PDE igual, en el caso 1 y en el caso 2, con y sin intercambio."""
    spec = importlib.util.spec_from_file_location("p2p_comunitario", GUION_PC)
    pcm = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(GUION_PC.parent))
    spec.loader.exec_module(pcm)
    x = _sinteticos()
    N, T = x["N"], x["T"]
    G, D, CU, pb, mes = x["G"], x["D"], x["CU"], x["pb"], x["mes"]
    s, d, au = np.maximum(G - D, 0), np.maximum(D - G, 0), np.minimum(G, D)
    rng = np.random.default_rng(3)
    pag = rng.normal(0.0, 100.0, (N, T))
    pag -= pag.mean(axis=0, keepdims=True)
    igual = {m: np.full(N, 1.0 / N) for m in np.unique(mes)}
    for caso in (1, 2):
        ded = evaluador.deduccion_pcom(caso, x["Cv"], x["Th"])
        ded_ref = pcm.deduccion_caso(caso, 1.0, x["Cv"], x["Th"])
        np.testing.assert_array_equal(ded, ded_ref)
        for v, q, p in ((x["v"], x["q"], pag), (0 * s, 0 * s, 0 * s)):
            mio, ex = evaluador.valor_p2p_colectivo(G, D, v, q, p, CU, ded,
                                                    mes, pb)
            ref, ex_ref = pcm.valor_comunitario(au, s, d, v, q, CU, p, ded,
                                                mes, pb, igual, "prueba")
            np.testing.assert_allclose(mio, ref, rtol=1e-12, atol=1e-6)
            np.testing.assert_allclose(ex.sum(axis=1), ex_ref, rtol=1e-12,
                                       atol=1e-9)


# ── Con datos: el punto base contra los puntos P y PC (LENTAS) ──────────────
@pytest.fixture(scope="module")
def datos(tmp_path_factory):
    if not HAY_DATOS:
        pytest.skip("sin MedicionesMTE_v3")
    return evaluador.carga_mte(str(MTE), tmp_path_factory.mktemp("cache_mte"))


def _referencias():
    if not (P_CSV.exists() and PC_CSV.exists()):
        pytest.skip("sin las salidas de los puntos P y PC")
    p = pd.read_csv(P_CSV, keep_default_na=False, na_values=[""])
    pc = pd.read_csv(PC_CSV, keep_default_na=False, na_values=[""])
    return p, pc


@pytest.mark.parametrize("caso", ["E0", "E2", "E4"])
def test_punto_base_reproduce_p_y_pc_lenta(datos, caso):
    p, pc = _referencias()
    ins = evaluador.prepara_caso(caso, datos)
    out, nuevos = evaluador.evalua_mecanismos_nuevos(ins, comun.PUNTO_BASE)
    p = p[p.caso == caso].set_index("institucion")
    pc = pc[pc.caso == caso].set_index("institucion")
    assert list(pc.index[:-1]) == ins.nombres == list(p.index[:-1])
    # el PP y el caso del art. 20 son los de los puntos P y PC
    assert ins.pp_c2 == pytest.approx(float(p.loc["comunidad",
                                                  "PP_media_COP_kWh"]),
                                      abs=1e-6)
    assert ins.pp_c2 == pytest.approx(287.41, abs=0.005)
    assert ins.caso_pcom == int(pc.loc["comunidad", "caso_art20"])
    assert ins.caso_pcom == (2 if caso == "E4" else 1)
    assert ins.cinac_kw == pytest.approx(float(pc.loc["comunidad",
                                                      "cinac_kw"]), abs=1e-5)
    # C2ppa: al peso del paquete, por institucion y en la comunidad
    ref = p.loc[ins.nombres, "B_C2_media_COP"].to_numpy(dtype=float)
    assert np.abs(nuevos["C2ppa"] - ref).max() <= TOL_PESO
    assert abs(out["C2ppa"] - float(p.loc["comunidad", "B_C2_media_COP"])) \
        <= TOL_PESO
    # P2Pcom: medio peso por institucion, un peso en la comunidad
    ref = pc.loc[ins.nombres, "P2Pcom_COP"].to_numpy(dtype=float)
    assert np.abs(nuevos["P2Pcom"] - ref).max() <= TOL_PESO
    assert abs(out["P2Pcom"] - float(pc.loc["comunidad", "P2Pcom_COP"])) \
        <= TOL_COMUNIDAD_PCOM
    assert out["P2Pcom"] == pytest.approx(nuevos["P2Pcom"].sum(), abs=1e-6)
    assert out["C2ppa"] == pytest.approx(nuevos["C2ppa"].sum(), abs=1e-6)
    # las brechas de la comunidad, contra las de los puntos P y PC
    cm, cp = pc.loc["comunidad"], p.loc["comunidad"]
    tol_b = TOL_COMUNIDAD_PCOM + 2 * TOL_PESO
    for b, col in (("P2Pcom_menos_C4", "brecha_P2Pcom_menos_C4_COP"),
                   ("P2Pcom_menos_C1", "brecha_P2Pcom_menos_C1_COP"),
                   ("P2Pcom_menos_P2P", "brecha_P2Pcom_menos_P2P_COP"),
                   ("P2Pcom_menos_C2ppa", "brecha_P2Pcom_menos_C2ppa_COP")):
        assert abs(out[b] - float(cm[col])) <= tol_b, b
    for b, col in (("C2ppa_menos_C1", "brecha_C2_media_menos_C1_COP"),
                   ("C2ppa_menos_C4", "brecha_C2_media_menos_C4_COP"),
                   ("C2ppa_menos_P2P", "brecha_C2_media_menos_P2P_COP")):
        assert abs(out[b] - float(cp[col])) <= 2 * TOL_PESO, b
    # y por institucion, las mismas brechas
    for n, nombre in enumerate(ins.nombres):
        assert abs(out[f"P2Pcom_menos_C4__{nombre}"]
                   - float(pc.loc[nombre, "brecha_P2Pcom_menos_C4_COP"])) \
            <= 2 * TOL_PESO + 1.0
        assert abs(out[f"C2ppa_menos_C1__{nombre}"]
                   - float(p.loc[nombre, "brecha_C2_media_menos_C1_COP"])) \
            <= 2 * TOL_PESO + 1.0


@pytest.mark.parametrize("caso", ["E0", "E2", "E4"])
def test_punto_base_de_d75_sin_cambio_lenta(datos, caso):
    """Las salidas de D75, los conteos y C2 del punto base son las del canon
    (`base/punto_base.csv` de la entrega del 2026-09-27), con las
    tolerancias de la compuerta del punto base."""
    if not PUNTO_BASE_CANON.exists():
        pytest.skip("sin la entrega del GSA del canon")
    ref = pd.read_csv(PUNTO_BASE_CANON).set_index("caso").loc[caso]
    ins = evaluador.prepara_caso(caso, datos)
    y = evaluador.evalua(ins, comun.PUNTO_BASE)
    for k in list(comun.SALIDAS_D75) + ["C2"] + list(comun.CONTEOS):
        if k == "energia":
            tol = 0.01
        elif k == "parte_vendedor":
            tol = 5e-4
        elif k in comun.CONTEOS:
            tol = 0.0
        else:
            tol = min(1e-6 * max(abs(float(ref[k])), 1.0), TOL_PESO)
        assert abs(y[k] - float(ref[k])) <= tol, (k, y[k], float(ref[k]))
    for nombre in ins.nombres:
        for b in ("P2P_menos_C1", "P2P_menos_C4", "P2P_menos_C5"):
            k = f"{b}__{nombre}"
            assert abs(y[k] - float(ref[k])) <= 2 * TOL_PESO, k
