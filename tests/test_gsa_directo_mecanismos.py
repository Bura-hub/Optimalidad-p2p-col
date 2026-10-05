"""Pruebas de C2 como PPA (C2ppa, CANON §14.22), del P2P colectivo (P2Pcom,
§14.23) y de H1, el credito mutualizado (§14.26), en el evaluador del GSA
directo (2026-10-02 y 2026-10-04).

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
puntos P, PC y H1). En el punto base, todos los factores en 1, el evaluador
reproduce C2ppa de `SALIDAS_SERVIDOR/c2_ppa_2026-10-02/`, P2Pcom de
`SALIDAS_SERVIDOR/p2p_comunitario_2026-10-02/` y H1 de
`SALIDAS_SERVIDOR/hibrido_por_planta_2026-10-04/`, institucion por
institucion y en la comunidad, en LOS TRECE CASOS de la tesis (no solo los
cinco del articulo: el caso 2 del art. 20 en E4, E5 y P2, plantas mixtas en
I1 y N1, sin Udenar en SINU), y las salidas de D75 no cambian frente al
`punto_base.csv` del canon (entrega del 2026-09-27). Unos 4 (s) por caso.

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


@pytest.mark.parametrize("caso", list(comun.ORDEN_CASOS))
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
    assert ins.caso_pcom == (2 if caso in ("E4", "E5", "P2") else 1)
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


@pytest.mark.parametrize("caso", list(comun.ORDEN_CASOS))
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


# ── H1, el credito mutualizado (2026-10-04, CANON §14.26) ───────────────────
GUION_H1 = (RAIZ / "reformateo" / "documento" / "scripts" / "articulo"
            / "hibrido_por_planta.py")
H1_CSV = (RAIZ / "SALIDAS_SERVIDOR" / "hibrido_por_planta_2026-10-04"
          / "hibrido_13casos.csv")
CAP_MIXTA = np.array([17.55, 150.209928, 17.55, 17.55])   # como I1


def test_numeral_de_cada_planta_por_su_capacidad():
    np.testing.assert_array_equal(
        evaluador.numeral_planta([17.55, 100.0, 100.01, 150.209928]),
        [1, 1, 2, 2])
    with pytest.raises(ValueError):
        evaluador.numeral_planta([17.55, -1.0])


def test_h1_conserva_la_energia_y_la_compensacion_suma_cero():
    """La formula reparte lo inyectado de cada mes, nadie recibe mas que su
    importacion restante y la compensacion suma cero."""
    x = _sinteticos()
    s = np.maximum(x["G"] - x["D"], 0.0)
    d = np.maximum(x["D"] - x["G"], 0.0)
    W, TR = evaluador.pde_primero_propio(s, d, x["mes"])
    for m, t in TR.items():
        assert t["asignado"].sum() == pytest.approx(t["S"].sum(), rel=1e-12)
        assert t["cedido"].sum() == pytest.approx(t["recibido"].sum(),
                                                  rel=1e-12, abs=1e-9)
        assert (t["recibido"] <= t["R"] + 1e-9).all()
        assert W[m].sum() == pytest.approx(1.0, abs=1e-12)
    b, comp = evaluador.valor_h1(x["G"], x["D"], x["CU"], x["Cv"], x["Th"],
                                 CAP_MIXTA, x["mes"], x["pb"])
    assert np.isfinite(b).all() and abs(comp.sum()) < 1e-6
    # con todas las plantas en el numeral 1 la deduccion es kappa*Cv
    frac = evaluador.fraccion_numeral2(TR, np.zeros(x["N"]))
    np.testing.assert_array_equal(
        evaluador.deduccion_por_origen(frac, x["Cv"], x["Th"], x["mes"]),
        x["Cv"])
    with pytest.raises(ValueError, match="1 MW"):
        evaluador.valor_h1(x["G"], x["D"], x["CU"], x["Cv"], x["Th"],
                           np.full(x["N"], 300.0), x["mes"], x["pb"])


def test_colectivo_pesos_con_el_pde_igual_es_colectivo_igual():
    x = _sinteticos()
    s = np.maximum(x["G"] - x["D"], 0.0)
    d = np.maximum(x["D"] - x["G"], 0.0)
    igual = {m: np.full(x["N"], 1.0 / x["N"]) for m in np.unique(x["mes"])}
    a = evaluador.colectivo_pesos(s, d, x["CU"], x["Cv"], x["mes"], x["pb"],
                                  igual)
    b = evaluador.colectivo_igual(s, d, x["CU"], x["Cv"], x["mes"], x["pb"])
    for u, v in zip(a, b):
        np.testing.assert_allclose(u, v, rtol=1e-12, atol=1e-9)


@pytest.mark.skipif(not (GUION_H1.exists() and HUELLAS.exists()),
                    reason="sin el guion del punto H1 o sin HUELLAS.csv")
@pytest.mark.parametrize("cap", [CAP_MIXTA, np.full(4, 17.55),
                                 np.full(4, 122.85)])
def test_h1_portado_es_el_del_punto_h1(cap):
    """Sobre datos sinteticos, con plantas mixtas, todas del numeral 1 y
    todas del 2, H1 y su compensacion son los de «H1 fondo» de
    `hibrido_por_planta.py` (kappa ya dentro del Cv)."""
    sys.path.insert(0, str(GUION_H1.parent))
    spec = importlib.util.spec_from_file_location("hibrido_por_planta",
                                                  GUION_H1)
    hb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hb)
    x = _sinteticos()
    N, T = x["N"], x["T"]
    G, D, CU, pb, mes = x["G"], x["D"], x["CU"], x["pb"], x["mes"]
    s, d, au = np.maximum(G - D, 0), np.maximum(D - G, 0), np.minimum(G, D)
    n2 = (hb.numeral_planta(cap) == 2).astype(float)
    W0, TR0 = hb.pde_primero_propio(s, d, mes)
    ded0 = hb.ded_por_origen(hb.fraccion_numeral2_traza(TR0, n2), 1.0,
                             x["Cv"], x["Th"], mes)
    cero = np.zeros((N, T))
    ref = hb.valor_hibrido(au, s, d, cero, cero, CU, cero, cero, ded0, mes,
                           pb, W0, "prueba")["val"]
    comp_ref = hb.compensacion(TR0, hb.precio_compensacion(s, pb, mes))
    b, comp = evaluador.valor_h1(G, D, CU, x["Cv"], x["Th"], cap, mes, pb)
    np.testing.assert_allclose(b, ref, rtol=1e-12, atol=1e-6)
    np.testing.assert_allclose(comp, comp_ref, rtol=1e-12, atol=1e-6)


@pytest.mark.parametrize("caso", list(comun.ORDEN_CASOS))
def test_punto_base_reproduce_h1_lenta(datos, caso):
    """En el punto base, H1 y H1 compensado por institucion y H1 de la
    comunidad son los de `hibrido_13casos.csv` (§14.26), y sus brechas las
    del punto H1, en los trece casos. I1 y N1 tienen plantas a los dos lados
    de 100 kW; la comunidad tambien es la de H1_CANON de la compuerta."""
    if not H1_CSV.exists():
        pytest.skip("sin las salidas del punto H1")
    h = pd.read_csv(H1_CSV, keep_default_na=False, na_values=[""])
    h = h[h.caso == caso].set_index("institucion")
    ins = evaluador.prepara_caso(caso, datos)
    out, nuevos = evaluador.evalua_mecanismos_nuevos(ins, comun.PUNTO_BASE)
    assert list(h.index[:-1]) == ins.nombres
    ref = h.loc[ins.nombres, "H1_fondo_COP"].to_numpy(dtype=float)
    assert np.abs(nuevos["H1"] - ref).max() <= TOL_PESO
    ref_c = h.loc[ins.nombres, "H1_fondo_compensado_COP"].to_numpy(dtype=float)
    assert np.abs(nuevos["H1comp"] - ref_c).max() <= TOL_PESO
    assert abs(out["H1"] - float(h.loc["comunidad", "H1_fondo_COP"])) \
        <= TOL_COMUNIDAD_PCOM
    assert out["H1"] == pytest.approx(nuevos["H1"].sum(), abs=1e-6)
    from gsa_directo import compuerta_punto_base as cpb
    assert cpb.H1_CANON[caso] == float(h.loc["comunidad", "H1_fondo_COP"])
    cm = h.loc["comunidad"]
    tol_b = TOL_COMUNIDAD_PCOM + 2 * TOL_PESO
    for b, col in (("H1_menos_C4", "brecha_H1_fondo_menos_C4_COP"),
                   ("H1_menos_C1", "brecha_H1_fondo_menos_C1_COP"),
                   ("H1_menos_P2P", "brecha_H1_fondo_menos_P2P_COP"),
                   ("H1_menos_P2Pcom", "brecha_H1_fondo_menos_P2Pcom_COP")):
        assert abs(out[b] - float(cm[col])) <= tol_b, (b, out[b], cm[col])
    for nombre in ins.nombres:
        for b, col in (("H1_menos_C4", "brecha_H1_fondo_menos_C4_COP"),
                       ("H1comp_menos_C1",
                        "brecha_H1_fondo_compensado_menos_C1_COP")):
            assert abs(out[f"{b}__{nombre}"] - float(h.loc[nombre, col])) \
                <= 2 * TOL_PESO + 1.0, (b, nombre)
