"""Pruebas de la dinamica con precios extremos (DX, M-A2X), 2026-10-07.

Actividades 1.1 y 4.1. Sin corridas largas: la carga del arnes con los
factores de precio sobre el cargador falso de las pruebas de M-A2 (al bit con
los factores en 1, el techo y la bolsa escalados como `aplica_factores`), la
clave de la cache, la hora que lee `preparacion.prepara`, el plan de M-A2X
por rondas y familias, la parada por futilidad opcional, la seleccion con un
motor falso, el lado derecho al bit con los factores en 1, y la lectura de la
energia. Segundos; ninguna
escribe fuera de `tmp_path`.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parent.parent
CONSENSO = RAIZ / "reformateo" / "documento" / "scripts" / "sonda" / "consenso"
SONDA = CONSENSO.parent
for _p in (RAIZ, SONDA, CONSENSO, Path(__file__).resolve().parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import arnes as A                                     # noqa: E402
import lado_derecho_extremo as LD                     # noqa: E402
import lectura_extrema as LX                          # noqa: E402
import medicion_extrema as MX                         # noqa: E402
import preparacion as PR                              # noqa: E402
import selecciona_extrema as SX                       # noqa: E402
from gsa_directo import comun                         # noqa: E402


@pytest.fixture
def cargador_falso(monkeypatch, tmp_path):
    """El mismo cargador falso de tests/test_validacion_ampliada.py."""
    import pandas as pd
    import data.xm_data_loader as xdl
    from data.cedenar_tariff import INSTITUTION_PROFILE

    idx = pd.date_range("2025-05-05", periods=72, freq="h")
    t = np.arange(72)
    sol = np.clip(np.sin((t % 24 - 6) * np.pi / 12), 0, None)
    G = np.outer(np.array([9.0, 1.2, 0.8, 2.0, 0.6]), sol)
    D = np.outer(np.array([3.0, 1.0, 0.9, 2.5, 1.4]),
                 1.0 + 0.3 * np.cos(t * np.pi / 12))
    monkeypatch.setenv("MTE_ROOT", str(tmp_path))
    monkeypatch.setattr(xdl.MTEDataLoader, "load",
                        lambda self, *a, **k: (D.copy(), G.copy(), idx))
    antes = dict(INSTITUTION_PROFILE)
    A._CACHE.clear()
    yield D, G
    A._CACHE.clear()
    INSTITUTION_PROFILE.clear()
    INSTITUTION_PROFILE.update(antes)


CLAVES = ("D", "G", "techo", "cvm", "peaje", "bolsa", "perm", "piso")


# ── la carga con los factores de precio ────────────────────────────────────
def test_los_factores_en_1_dejan_la_carga_identica_al_bit(cargador_falso):
    import paso_a_paso as PP
    base = PP.carga("m1")
    uno = PP.carga("m1", factor_bolsa=1.0, factor_tarifa=1.0)
    for k in CLAVES:
        assert np.array_equal(base[k], uno[k], equal_nan=True), k


def test_el_techo_y_la_bolsa_se_escalan_como_aplica_factores(cargador_falso):
    import paso_a_paso as PP
    base = PP.carga("m1")
    t2 = PP.carga("m1", factor_tarifa=2.0)
    assert np.array_equal(t2["techo"], 2.0 * np.asarray(base["techo"]))
    for k in ("D", "G", "cvm", "peaje", "bolsa", "perm"):
        assert np.array_equal(base[k], t2[k], equal_nan=True), k
    # En permuta el piso es la tarifa menos la deduccion: sube con el techo.
    perm = np.asarray(base["perm"], bool)
    dif = np.asarray(t2["piso"]) - np.asarray(base["piso"])
    assert np.allclose(dif[perm], np.asarray(base["techo"])[perm], rtol=0,
                       atol=1e-9)
    assert np.array_equal(np.asarray(t2["piso"])[~perm],
                          np.asarray(base["piso"])[~perm])
    b4 = PP.carga("m1", factor_bolsa=4.0)
    assert np.array_equal(b4["techo"], base["techo"])
    b1, bb4 = np.asarray(base["bolsa"]), np.asarray(b4["bolsa"])
    # La cruda por 4 y el techo PES DESPUES: nunca mas que 4 veces, y donde
    # el techo no muerde, exactamente 4 veces.
    assert np.all(bb4 <= 4.0 * b1 + 1e-9) and np.all(bb4 >= b1 - 1e-9)
    assert np.mean(np.isclose(bb4, 4.0 * b1, rtol=0, atol=1e-9)) > 0.5


@pytest.mark.parametrize("malo", [0.0, -1.0, float("nan"), float("inf")])
def test_un_factor_de_precio_no_valido_falla(cargador_falso, malo):
    import paso_a_paso as PP
    with pytest.raises(ValueError):
        PP.carga("m1", factor_tarifa=malo)
    with pytest.raises(ValueError):
        A.lee_precios({"f_bolsa": malo})


def test_lee_precios():
    assert A.lee_precios(None) is None
    assert A.lee_precios({}) == (1.0, 1.0)
    assert A.lee_precios({"f_tarifa": 0.5}) == (1.0, 0.5)
    with pytest.raises(ValueError):
        A.lee_precios({"f_peaje": 1.0})
    with pytest.raises(ValueError):
        A.lee_precios([4.0, 1.0])


def test_la_cache_separa_los_precios(cargador_falso):
    d0, _ = A.carga("E0")
    d2, _ = A.carga("E0", {"f_bolsa": 1.0, "f_tarifa": 2.0})
    assert d0 is not d2 and A.carga("E0")[0] is d0
    assert np.array_equal(d2["techo"], 2.0 * np.asarray(d0["techo"]))
    with pytest.raises(ValueError):
        A.hora_de("CHACON", "22", precios={"f_bolsa": 4.0})


def test_prepara_lee_la_hora_con_sus_precios(monkeypatch):
    vistos = []

    def falsa(caso, fecha, precios=None):
        vistos.append((caso, fecha, precios))
        raise RuntimeError("basta")
    monkeypatch.setattr(A, "hora_de", falsa)
    for sp in (dict(caso="E0", fecha="f"),
               dict(caso="E4", fecha="g", precios={"f_tarifa": 0.6})):
        with pytest.raises(RuntimeError):
            PR.prepara(sp)
    assert vistos == [("E0", "f", None), ("E4", "g", {"f_tarifa": 0.6})]


def test_el_lado_derecho_con_los_factores_en_1_es_el_de_siempre(
        cargador_falso):
    fecha = "2025-05-05 12:00"
    e = A.hora_de("E0", fecha)
    assert len(e["gn"]) and len(e["dn"])          # la hora tiene mercado
    filas = LD.neutra("E0", fecha, n=4)
    assert [q for q, _ok, _d in filas] == ["entradas",
                                           "lado derecho sin variante",
                                           "lado derecho V3a k1000"]
    assert all(ok for _q, ok, _d in filas), filas


# ── el plan de M-A2X ───────────────────────────────────────────────────────
def test_precios_de_cada_familia():
    assert MX.precios_de("bolsa4", "E0") == {"f_bolsa": 4.0, "f_tarifa": 1.0}
    assert MX.precios_de("tarifa2", "P2") == {"f_bolsa": 1.0, "f_tarifa": 2.0}
    assert MX.precios_de("tarifa_baja", "E0")["f_tarifa"] == 0.5
    for c in ("E4", "E5", "P2"):
        assert MX.precios_de("tarifa_baja", c)["f_tarifa"] == 0.6
    # 0,6 es el umbral de §14.32 (0,5906) redondeado hacia arriba.
    assert MX.TARIFA_BAJA_MINIMA == math.ceil(0.5906 * 100) / 100
    x = MX.punto_gsa("bolsa4", "E0")
    assert x[comun.NOMBRES.index("f_bolsa")] == 4.0 and x.sum() == 9.0
    # La bolsa x4 es el extremo de la caja del GSA.
    assert comun.SOPORTES[comun.NOMBRES.index("f_bolsa")][1] == 4.0
    with pytest.raises(ValueError):
        MX.precios_de("bolsa9", "E0")


def _horas(por):
    """{caso__familia: {regimen: [{fecha}]}}."""
    return {MX.clave_horas(c, f): {r: [dict(fecha=f"{c}-{f}-{r}-{j}")
                                       for j in range(n)]
                                   for r, n in regs.items()}
            for (c, f), regs in por.items()}


def test_el_plan_va_por_rondas_familias_y_turno_entre_casos(monkeypatch):
    for v in ("EXTREMA_FAMILIAS", "EXTREMA_REGIMENES", "EXTREMA_FUTILIDAD"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("EXTREMA_HORAS", "5")
    horas = _horas({("E0", "bolsa4"): {"interiores": 4, "topados": 9},
                    ("E4", "bolsa4"): {"interiores": 9},
                    ("E0", "tarifa2"): {"topados": 2}})
    sp = MX.specs(horas)
    inter = [s["fecha"] for s in sp if s["grupo"] == "interiores"]
    assert inter == ["E0-bolsa4-interiores-0", "E4-bolsa4-interiores-0",
                     "E0-bolsa4-interiores-1", "E4-bolsa4-interiores-1",
                     "E0-bolsa4-interiores-2"]
    # Ronda 0: una hora de cada regimen en cada familia, en orden.
    r0 = [(s["familia_precio"], s["grupo"]) for s in sp if s["ronda"] == 0]
    assert r0 == [("bolsa4", "interiores"), ("bolsa4", "topados"),
                  ("tarifa2", "topados")]
    assert all(s["medicion"] == "M-A2X" for s in sp)
    assert all(s["var"] == {"mu_ent": 1.0, "k_lento": 1000.0} for s in sp)
    assert all(s["cortes"][-1] * 1000.0 == pytest.approx(160.0) for s in sp)
    assert all(s["familia"] == f"V3a acelerada ({s['familia_precio']})"
               for s in sp)
    e4 = [s for s in sp if s["caso"] == "E4"]
    assert all(s["precios"] == {"f_bolsa": 4.0, "f_tarifa": 1.0} for s in e4)
    assert all(s["tope"] == 10800.0 and s["nivel"] == "sigma"
               and s["piso_juego"] == "marginal" for s in sp)


def test_variables_del_plan_que_no_valen(monkeypatch):
    monkeypatch.setenv("EXTREMA_HORAS", "4")
    with pytest.raises(ValueError):
        MX.specs({})
    monkeypatch.setenv("EXTREMA_HORAS", "10")
    monkeypatch.setenv("EXTREMA_REGIMENES", "interiores mixto")
    with pytest.raises(ValueError):
        MX.specs({})
    monkeypatch.setenv("EXTREMA_REGIMENES", "interiores,topados")
    monkeypatch.setenv("EXTREMA_FAMILIAS", "bolsa9")
    with pytest.raises(ValueError):
        MX.specs({})


def test_sin_futilidad_por_defecto_y_con_ella_la_regla_de_m_a2(monkeypatch):
    import medicion_ampliada as MA
    monkeypatch.delenv("EXTREMA_FUTILIDAD", raising=False)
    sp = dict(grupo="topados", familia="V3a acelerada (bolsa4)",
              n_plan_grupo=10)
    malo = dict(spec=dict(grupo="topados", familia="V3a acelerada (bolsa4)"),
                msg="FALLA x", filas=[], veredicto={})
    assert MX.omite(sp, [malo] * 5) is None
    monkeypatch.setenv("EXTREMA_FUTILIDAD", "1")
    monkeypatch.setattr(MX, "_PREVIOS", [])
    assert MA.limite_fuera(10) == 0
    assert "futilidad" in MX.omite(sp, [malo])
    otra = dict(malo, spec=dict(grupo="topados",
                                familia="V3a acelerada (tarifa2)"))
    assert MX.omite(sp, [otra]) is None


# ── la seleccion ───────────────────────────────────────────────────────────
class _R:
    def __init__(self, k, regimen, piso, E):
        self.k, self.regimen, self.piso_juego = k, regimen, piso
        self.P_star = None if E is None else np.array([[E]])


def test_por_regimen_deja_fuera_las_horas_sin_mercado():
    g = SX.por_regimen([_R(0, "interiores", 400.0, 1.5),
                        _R(1, "sin_mercado", 0.0, None),
                        _R(2, "sin_ganancia", 0.0, 0.0),
                        _R(3, "topados", 410.0, 2.0),
                        _R(4, "interiores", 405.0, 0.5)])
    assert sorted(g) == ["interiores", "topados"]
    assert [h for h, *_ in g["interiores"]] == [0, 4]
    assert g["topados"][0] == (3, "topados", 410.0, 2.0)


def test_comprueba_rechaza_la_hora_que_no_es_la_del_motor(monkeypatch):
    class _Rep:
        regimen, regimen_cerrado, piso, E, S, n_soluciones = (
            "interiores", "interiores", 400.0, 1.5, 900.0, 1)
    e = dict(gn=np.ones(1), dn=np.ones(2), vend=["a"], comp=["b", "c"])
    monkeypatch.setattr(A, "hora_de", lambda c, f, precios=None: e)
    monkeypatch.setattr(PR, "resuelve", lambda e: _Rep())
    ok, _m, _t = SX.comprueba("E0", "bolsa4", "f", "interiores", 400.0, 1.5)
    assert ok is not None and ok["precios"] == {"f_bolsa": 4.0, "f_tarifa": 1.0}
    assert SX.comprueba("E0", "bolsa4", "f", "topados", 400.0, 1.5)[1] \
        == "otro regimen"
    assert SX.comprueba("E0", "bolsa4", "f", "interiores", 400.01, 1.5)[1] \
        == "otro piso del juego"
    assert SX.comprueba("E0", "bolsa4", "f", "interiores", 400.0, 1.6)[1] \
        == "otra energia"


def test_la_captura_del_motor_deja_el_motor_como_estaba():
    from core import ems_p2p
    antes = ems_p2p.EMSP2P.run
    with SX.captura_motor() as g:
        assert ems_p2p.EMSP2P.run is not antes
        assert g == {}
    assert ems_p2p.EMSP2P.run is antes


# ── la lectura ─────────────────────────────────────────────────────────────
def test_la_energia_se_lee_en_teq_80_y_160():
    fila = lambda teq, q: dict(teq=teq, q=q)                       # noqa
    res = [dict(spec=dict(familia="V3a acelerada (bolsa4)"), veredicto={1: 1},
                cerrada=dict(cerrada=dict(E=1.0)),
                filas=[fila(40.0, [0.2, 0.2]), fila(80.0, [0.5, 0.5]),
                       fila(160.0, [0.5, 0.5 + 1e-9])]),
           dict(spec=dict(familia="V3a acelerada (bolsa4)"), veredicto={},
                cerrada={}, filas=[])]
    n, peor = LX.energia(res)["V3a acelerada (bolsa4)"]
    assert n == 1 and peor == pytest.approx(1e-9, abs=1e-15)


def test_lee_base(tmp_path):
    ruta = tmp_path / "l.csv"
    ruta.write_text("regimen,dentro,hechas,fraccion\ninteriores,31,40,0.775\n",
                    encoding="utf-8")
    assert LX.lee_base(ruta) == {"interiores": (31, 40, 0.775)}
