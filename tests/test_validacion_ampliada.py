"""Pruebas de la noche del 2026-10-06 (B4 y B5): la validacion ampliada del
reposo (M-A2) y la tarifa en niveles extremos.

Actividades 1.1, 4.1 y 4.2. Todo sin datos reales ni corridas: la carga del
arnes con un cargador falso, el plan y la parada por futilidad con resultados
sinteticos, el pool con el trabajador falso de las pruebas del consenso, el
intervalo de Wilson con valores de tabla y el lanzador en SECO, comprobando
con el listado de `modelo_base/` y `SALIDAS_SERVIDOR/` antes y despues que no
toca el disco (regla del lanzador, 2026-09-14). Segundos.
"""
from __future__ import annotations

import os
import shutil
import subprocess
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
import corre_mediciones as CM                         # noqa: E402
import lectura_ampliada as LA                         # noqa: E402
import medicion_ampliada as M                         # noqa: E402
import _trabajador_falso_consenso as TF               # noqa: E402
from gsa_directo import comun                         # noqa: E402
from gsa_directo import tarifa_extrema as TE          # noqa: E402

LANZADOR = RAIZ / "modelo_base" / "run_servidor.sh"


# ── la carga del arnes en los casos nuevos ─────────────────────────────────
@pytest.fixture
def cargador_falso(monkeypatch, tmp_path):
    """Demanda y generacion sinteticas con el calendario real (el mismo
    patron que tests/test_arnes_consenso.py)."""
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


def test_los_defectos_nuevos_dejan_la_carga_identica_al_bit(cargador_falso):
    import paso_a_paso as PP
    base = PP.carga("m1")
    otro = PP.carga("m1", factor_demanda=None, escala_agente=None,
                    neto_cero=False, excluir_agente=None)
    uno = PP.carga("m1", factor_demanda=1.0)
    for x in (otro, uno):
        assert list(x["nombres"]) == list(base["nombres"])
        for k in ("D", "G", "techo", "cvm", "peaje", "bolsa", "perm", "piso"):
            assert np.array_equal(base[k], x[k], equal_nan=True), k


def test_excluir_agente_retira_la_fila_y_su_nombre(cargador_falso):
    import paso_a_paso as PP
    D, G = cargador_falso
    sinu = PP.carga("m1", excluir_agente="Udenar")
    assert list(sinu["nombres"]) == ["Mariana", "UCC", "HUDN", "Cesmag"]
    assert np.array_equal(sinu["D"], D[1:])
    assert np.array_equal(sinu["G"], G[1:])
    with pytest.raises(ValueError):
        PP.carga("m1", excluir_agente="Nadie")


def test_las_opciones_del_caso_escalan_como_main(cargador_falso):
    """Cada caso nuevo del arnes con la opcion de CASOS_MATRIZ, leida por
    gsa_directo.comun, igual que `data.escalado.escala_comunidad`."""
    from data.escalado import escala_comunidad, lee_escala_agente
    D, G = cargador_falso
    nombres = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
    for caso in ("E1", "P1", "P2", "I1", "N1"):
        op = comun.opciones_caso(caso)
        De, Ge, _f = escala_comunidad(
            D, G, nombres, factor_generacion=op["factor_generacion"],
            factor_demanda=op["factor_demanda"],
            generacion_por_agente=lee_escala_agente(op["escala_agente"]),
            neto_cero=op["neto_cero"])
        dat, _mapa = A.carga(caso)
        assert np.allclose(dat["D"], De, rtol=0, atol=1e-12), caso
        assert np.allclose(dat["G"], Ge, rtol=0, atol=1e-12), caso
    dat, _ = A.carga("SINU")
    assert list(dat["nombres"]) == ["Mariana", "UCC", "HUDN", "Cesmag"]


def test_el_arnes_cubre_los_trece_casos():
    assert set(A.CASOS_ARNES) == set(comun.CASOS)
    assert set(M.CASOS) == set(comun.CASOS)


# ── el plan de M-A2 ────────────────────────────────────────────────────────
def _horas(por_caso):
    """{caso: {regimen: [{fecha}]}} con `por_caso[caso][regimen]` horas."""
    return {c: {r: [dict(fecha=f"{c}-{r}-{j}") for j in range(n)]
                for r, n in regs.items()}
            for c, regs in por_caso.items()}


def test_el_plan_va_por_rondas_y_por_turno_entre_casos(monkeypatch):
    monkeypatch.setenv("AMPLIACION_HORAS", "5")
    monkeypatch.delenv("AMPLIACION_SIN_ACELERAR", raising=False)
    horas = _horas({"E0": {"cuantal": 4, "topados": 9},
                    "K1": {"cuantal": 1, "topados": 9},
                    "I1": {"topados": 9}})
    sp = M.specs(horas)
    # cuantal: E0-0, K1-0, E0-1, E0-2, E0-3 (5); topados: E0, K1, I1, E0, K1.
    cuantal = [s["fecha"] for s in sp if s["grupo"] == "cuantal"]
    topados = [s["fecha"] for s in sp if s["grupo"] == "topados"]
    assert cuantal == ["E0-cuantal-0", "K1-cuantal-0", "E0-cuantal-1",
                       "E0-cuantal-2", "E0-cuantal-3"]
    assert topados == ["E0-topados-0", "K1-topados-0", "I1-topados-0",
                       "E0-topados-1", "K1-topados-1"]
    # Por rondas, y dentro de cada ronda en el orden de prioridad.
    assert [s["grupo"] for s in sp[:4]] == ["cuantal", "topados",
                                            "cuantal", "topados"]
    assert all(s["n_plan_grupo"] == 5 for s in sp)
    assert all(s["var"] == {"mu_ent": 1.0, "k_lento": 1000.0} for s in sp)
    assert all(s["familia"] == M.ACELERADA and s["medicion"] == "M-A2"
               for s in sp)
    assert all(s["cortes"][-1] * 1000.0 == pytest.approx(160.0) for s in sp)


def test_el_brazo_sin_acelerar_va_al_final_y_solo_en_los_libres(monkeypatch):
    monkeypatch.setenv("AMPLIACION_HORAS", "5")
    monkeypatch.setenv("AMPLIACION_SIN_ACELERAR", "1")
    horas = _horas({"E0": {"interiores": 6, "topados": 6, "suma_no_cabe": 6}})
    sp = M.specs(horas)
    k1 = [i for i, s in enumerate(sp) if s["var"]["k_lento"] == 1.0]
    assert k1 and min(k1) == len(sp) - len(k1)
    assert {sp[i]["grupo"] for i in k1} == {"interiores", "suma_no_cabe"}
    assert all(sp[i]["familia"] == M.SIN_ACELERAR for i in k1)


def test_menos_de_cinco_horas_por_regimen_no_vale(monkeypatch):
    monkeypatch.setenv("AMPLIACION_HORAS", "4")
    with pytest.raises(ValueError):
        M.specs({})


# ── la parada por futilidad ────────────────────────────────────────────────
def test_limite_de_horas_en_contra():
    assert M.limite_fuera(5) == 0
    assert M.limite_fuera(19) == 0
    assert M.limite_fuera(20) == 1
    assert M.limite_fuera(40) == 2
    assert M.limite_fuera(60) == 3


def test_omite_cuando_el_regimen_ya_no_llega_al_95(monkeypatch):
    monkeypatch.setattr(M, "hora_fuera", lambda res: res["fuera"])
    monkeypatch.setattr(M, "_PREVIOS", [])
    sp = dict(grupo="topados", familia=M.ACELERADA, n_plan_grupo=40)
    res = lambda g, f: dict(spec=dict(grupo=g, familia=M.ACELERADA),  # noqa
                            fuera=f)
    dos = [res("topados", True), res("topados", True), res("topados", False),
           res("cuantal", True), res("cuantal", True), res("cuantal", True)]
    assert M.omite(sp, dos) is None                 # 2 en contra de 40: aun
    tres = dos + [res("topados", True)]
    assert "futilidad" in M.omite(sp, tres)          # 3 > 2: decidido
    # Las de otra familia no cuentan.
    otra = dos + [dict(spec=dict(grupo="topados", familia=M.SIN_ACELERAR),
                       fuera=True)]
    assert M.omite(sp, otra) is None


def test_omite_cuenta_las_noches_anteriores(monkeypatch, tmp_path):
    import json
    previo = tmp_path / "m_a2.json"
    previo.write_text(json.dumps([
        dict(spec=dict(grupo="excluidos", familia=M.ACELERADA),
             msg="FALLA x", filas=[], veredicto={})] * 3), encoding="utf-8")
    monkeypatch.setenv("AMPLIACION_PREVIOS", str(previo))
    monkeypatch.setattr(M, "_PREVIOS", None)
    sp = dict(grupo="excluidos", familia=M.ACELERADA, n_plan_grupo=40)
    assert "futilidad" in M.omite(sp, [])
    monkeypatch.setattr(M, "_PREVIOS", None)
    monkeypatch.delenv("AMPLIACION_PREVIOS")
    assert M.omite(sp, []) is None


def test_hora_fuera_con_los_juicios_de_veredicto():
    assert M.hora_fuera(dict(spec={}, omitida=True)) is None
    assert M.hora_fuera(dict(spec={}, recorte_movio=True, veredicto={1: 1}))\
        is None
    assert M.hora_fuera(dict(spec={}, msg="FALLA BrokenProcessPool")) is True
    assert M.hora_fuera(dict(spec={}, msg="sin mercado", veredicto={})) is None


def test_el_pool_no_somete_las_omitidas(tmp_path):
    """Las que `omite_fn` rechaza no se someten (si se sometieran, matarian
    el pool: `muere`), quedan anotadas como hechas y omitidas, y el plan no
    tiene faltantes."""
    plan = TF.plan(mueren={2, 4}, n=6, duerme=0.05)
    omitir = {"h2", "h4"}
    r = CM.corre_plan(list(enumerate(plan)), 6, 2, tmp_path / "x.json",
                      trabajo_fn=TF.trabaja, por_proceso_gb=0, muestreo_s=0.2,
                      omite_fn=lambda sp, res: ("prueba" if sp["fecha"] in
                                                omitir else None))
    assert r["muertes"] == 0
    assert sorted(r["hechos"]) == list(range(6))
    om = [x for x in r["resultados"] if x.get("omitida")]
    assert sorted(x["plan_indice"] for x in om) == [2, 4]
    assert all(x["msg"] == "OMITIDA prueba" for x in om)
    assert CM.faltantes(6, r["hechos"]) == []


def test_sin_omite_fn_todo_corre_como_antes(tmp_path):
    plan = TF.plan(mueren=set(), n=4, duerme=0.02)
    r = CM.corre_plan(list(enumerate(plan)), 4, 2, tmp_path / "x.json",
                      trabajo_fn=TF.trabaja, por_proceso_gb=0, muestreo_s=0.2)
    assert not any(x.get("omitida") for x in r["resultados"])
    assert sorted(r["hechos"]) == list(range(4))


# ── la lectura parcial ─────────────────────────────────────────────────────
def test_wilson_valores_de_tabla():
    bajo, alto = LA.wilson(20, 20)
    assert bajo == pytest.approx(0.8389, abs=1e-4) and alto == 1.0
    bajo, alto = LA.wilson(19, 20)
    assert bajo == pytest.approx(0.7639, abs=1e-4)
    assert alto == pytest.approx(0.9911, abs=1e-4)
    bajo, _ = LA.wilson(73, 73)
    assert bajo >= 0.95 > LA.wilson(72, 72)[0]       # 73 sin fallos: >= 95 %
    assert all(np.isnan(LA.wilson(0, 0)))


def test_la_lectura_dice_el_estado_sin_cambiar_el_rotulo(monkeypatch):
    import veredicto as V

    def cuenta(corridas, nombre):
        c = corridas[0]
        return dict(juzgada=c["j"], falla=False, dentro=c["d"], cortadas=0,
                    guardados=0)
    monkeypatch.setattr(V, "cuenta_hora", cuenta)
    plan = {("topados", M.ACELERADA): [("E0", f"t{i}") for i in range(40)],
            ("cuantal", M.ACELERADA): [("E0", f"c{i}") for i in range(40)],
            ("interiores", M.ACELERADA): [("E0", f"i{i}") for i in range(5)]}

    def r(g, i, j, d):
        return dict(spec=dict(grupo=g, familia=M.ACELERADA, caso="E0",
                              fecha=f"{g[0]}{i}"), regimen=g,
                    veredicto={"cerrada": {}}, j=j, d=d)
    res = ([r("topados", i, True, True) for i in range(20)]           # parcial
           + [r("cuantal", i, i > 2, True) for i in range(6)]          # 3 fuera
           + [dict(spec=dict(grupo="cuantal", familia=M.ACELERADA,
                             caso="E0", fecha=f"c{i}"), omitida=True)
              for i in range(6, 40)]
           + [r("interiores", i, True, True) for i in range(5)])      # completo
    filas = {f["regimen"]: f for f in LA.lectura(res, plan)}
    t = filas["topados"]
    assert (t["estado"], t["hechas"], t["dentro"], t["pendientes"]) == \
        ("parcial", 20, 20, 20)
    assert t["evaluable"] and t["rotulo"].startswith("reposo verificado")
    c = filas["cuantal"]
    assert c["estado"] == "decidido (futilidad)" and c["omitidas"] == 34
    assert c["rotulo"].startswith("regla declarada")
    i = filas["interiores"]
    assert i["estado"] == "completo" and not i["evaluable"]


# ── la tarifa en niveles extremos ──────────────────────────────────────────
def test_tarifa_punto_y_signo():
    x = TE.punto(0.5)
    assert x[comun.NOMBRES.index("f_tarifa")] == 0.5
    assert np.count_nonzero(x != 1.0) == 1
    assert TE.signo(0.4) == 0 and TE.signo(-3.0) == -1 and TE.signo(2.0) == 1
    with pytest.raises(ValueError):
        TE.signo(float("nan"))
    # C1 - C4 es la brecha del GSA con el signo cambiado.
    assert TE.BRECHAS["C1_menos_C4"] == ("C4_menos_C1", -1.0)
    assert TE.BRECHAS["C2ppa_menos_C1"][0] in comun.SALIDAS


def test_tarifa_compara_al_peso_contra_el_punto_base():
    ref = {"caso": "E0", "seg": "1.0", "P2P": repr(46494980.25),
           "parte_vendedor": repr(0.5421)}
    assert TE.compara_referencia({"P2P": 46494980.25 + 0.4,
                                  "parte_vendedor": 0.5421}, ref) == []
    malas = TE.compara_referencia({"P2P": 46494980.25 + 0.6,
                                   "parte_vendedor": 0.5421 + 1e-5}, ref)
    assert {m[0] for m in malas} == {"P2P", "parte_vendedor"}


def test_tarifa_sin_matriz_ni_dia_sale_con_2():
    assert TE.ejecuta(["--casos", "E0", "--sin-escribir"]) == 2
    assert TE.ejecuta(["--dia", "2025-05-09", "--factores", "0.5", "2",
                       "--sin-escribir"]) == 2           # falta f = 1


# ── el lanzador, en SECO ───────────────────────────────────────────────────
def _bash():
    if sys.platform == "win32":
        for c in (os.environ.get("BASH_GIT"),
                  r"C:\Program Files\Git\bin\bash.exe",
                  r"C:\Program Files\Git\usr\bin\bash.exe"):
            if c and Path(c).exists():
                return c
        return None
    return shutil.which("bash")


BASH = _bash()
VARIABLES = ("AMPLIADA_SALIDAS", "TARIFA_SALIDAS", "MATRIZ_CANON", "RETOMA",
             "AMPLIACION_HORAS", "AMPLIACION_TOPE_S", "AMPLIACION_SIN_ACELERAR",
             "FACTORES_CU", "TOPE_GLOBAL_S", "ALMACENES", "CONTENCION",
             "PARA_EN_FALLO", "MEMORIA_POR_PROCESO_GB", "DIA_OK")


def _corre(*args, **env):
    e = dict(os.environ)
    for v in VARIABLES:
        e.pop(v, None)
    e.update(SECO="1", MTE_ROOT=str(RAIZ / "MedicionesMTE_v3"), PROCS="4")
    e.update({k: str(v) for k, v in env.items()})
    r = subprocess.run([BASH, str(LANZADOR), *args], cwd=RAIZ, env=e,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    return r.returncode, r.stdout + r.stderr


def _listado():
    out = []
    for base in ("modelo_base", "SALIDAS_SERVIDOR"):
        for p in sorted((RAIZ / base).rglob("*")):
            try:
                st = p.stat()
            except OSError:
                continue
            out.append((str(p), st.st_size, st.st_mtime_ns))
    return out


@pytest.mark.skipif(BASH is None, reason="sin bash")
def test_seco_validacion_ampliada_no_escribe():
    antes = _listado()
    rc, out = _corre("validacion_ampliada",
                     AMPLIADA_SALIDAS="SALIDAS_SERVIDOR/va_prueba")
    assert _listado() == antes
    assert rc == 0, out
    for paso in range(1, 7):
        assert f"--- {paso}/6" in out
    assert "lectura_ampliada.py --comprueba-canon" in out
    assert out.count("selecciona_horas.py") == 13
    assert "--medicion medicion_ampliada" in out
    assert "--tope-total" in out and "--desde 0" in out
    assert "[SECO] tar czf" in out


@pytest.mark.skipif(BASH is None, reason="sin bash")
def test_seco_validacion_ampliada_retoma():
    antes = _listado()
    rc, out = _corre("validacion_ampliada", RETOMA="57",
                     AMPLIADA_SALIDAS="SALIDAS_SERVIDOR/va_prueba")
    assert _listado() == antes
    assert rc == 0, out
    assert "--desde 57" in out and "m_a2_desde57.json" in out


@pytest.mark.skipif(BASH is None, reason="sin bash")
def test_seco_tarifa_extrema_no_escribe():
    antes = _listado()
    rc, out = _corre("tarifa_extrema", MATRIZ_CANON="SALIDAS_SERVIDOR/x",
                     TARIFA_SALIDAS="SALIDAS_SERVIDOR/te_prueba")
    assert _listado() == antes
    assert rc == 0, out
    assert "gsa_directo/compuerta_punto_base.py --matriz SALIDAS_SERVIDOR/x" \
        in out
    assert "--factores 0.5 0.75 1 1.5 2" in out
    assert "--referencia-base SALIDAS_SERVIDOR/te_prueba/base/punto_base.csv" \
        in out
    assert "--exclude=SALIDAS_SERVIDOR/te_prueba/cache" in out


@pytest.mark.skipif(BASH is None, reason="sin bash")
def test_seco_rechaza_lo_que_no_vale():
    rc, out = _corre("tarifa_extrema", MATRIZ_CANON="SALIDAS_SERVIDOR/x",
                     FACTORES_CU="0.5 2")
    assert rc == 2 and "tiene que llevar 1" in out
    rc, out = _corre("validacion_ampliada", AMPLIADA_SALIDAS="/tmp/fuera")
    assert rc == 2
    rc, out = _corre("validacion_ampliada", RETOMA="x")
    assert rc == 2
