"""Pruebas de la equidad dentro de la caja del GSA (EQ, 2026-10-07).

Actividades 3.3 y 4.1. Sin corridas: los puntos de la caja frente a la
muestra del GSA, el Gini y la clase con la definicion del canon (C-214,
§14.6), las metricas de un punto sintetico, el resumen por caso, la
comparacion con la fila del GSA y los rechazos de la orden. Si la matriz del
canon esta en la maquina, ademas, que el Gini y la clase de los libros del
canon son los de la tabla de §14.6. Ninguna escribe fuera de `tmp_path`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from gsa_directo import comun                     # noqa: E402
from gsa_directo import equidad_caja as EQ        # noqa: E402

MATRIZ = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
          / "SALIDAS_SERVIDOR" / "matriz_reposo")


def test_los_puntos_son_las_filas_a_y_b_de_la_muestra_del_gsa():
    n = 4
    p = EQ.puntos_caja(n)
    X = comun.muestra(n)
    assert len(p) == 2 * n
    assert [i for i, *_ in p] == [0, 13, 14, 27, 28, 41, 42, 55]
    assert [f for _i, f, *_ in p] == ["A", "B"] * n
    for i, _f, b, x in p:
        assert i // comun.B == b
        assert np.array_equal(x, X[i])
        for (lo, hi), v in zip(comun.SOPORTES, x):
            assert lo <= v <= hi
    # Anidada como el GSA: los puntos de n = 2 son los primeros de n = 4.
    q = EQ.puntos_caja(2)
    for a, b in zip(q, p):
        assert a[0] == b[0] and np.array_equal(a[3], b[3])


def test_el_gini_es_el_del_canon_y_falla_con_no_finitos():
    from core.settlement import gini_index
    v = np.array([11.4e6, 9.1e6, 11.1e6, 9.4e6, 5.5e6])
    assert EQ.gini(v) == gini_index(v)
    assert EQ.gini(np.full(4, 3.0)) == 0.0
    with pytest.raises(ValueError):
        EQ.gini(np.array([1.0, np.nan]))


def test_la_clase_es_la_del_guion_del_canon():
    pj = EQ.guion_pj()
    for W_a, W_c, g_a, g_c in [(10, 9, 0.12, 0.11), (10, 9, 0.11, 0.12),
                               (9, 10, 0.12, 0.11), (9, 10, 0.11, 0.12),
                               (10, 10, 0.11, 0.11)]:
        assert EQ.clase(W_a, W_c, g_a, g_c) == pj.clase(dict(
            W_P2P=W_a, W_C4=W_c, gini_P2P=g_a, gini_C4=g_c))
    assert EQ.clase(10, 9, 0.11, 0.12) == "P2P domina"
    assert EQ.clase(10, 9, 0.12, 0.11) == "intercambio"
    with pytest.raises(ValueError):
        EQ.clase(float("nan"), 1, 0.1, 0.1)


def _ben(escala=1.0):
    base = np.array([5.0, 4.0, 3.0, 2.0, 1.0]) * 1e6
    ben = {m: base * (1.0 + 0.01 * k) * escala
           for k, m in enumerate(EQ.MECANISMOS)}
    # C4 mas parejo y menor: el mercado gana en eficiencia y pierde en Gini.
    ben["C4"] = np.full(5, 2.9e6)
    # H1comp es H1 con una compensacion que suma cero.
    ben["H1comp"] = ben["H1"] + np.array([1.0, -1.0, 2.0, -2.0, 0.0]) * 1e3
    return ben


def _out(ben):
    out = {m: float(np.sum(ben[m])) for m in EQ.MECANISMOS if m != "H1comp"}
    out.update(n_horas_mercado=10.0, n_cuantal=1.0, retiros=0.0)
    return out


def test_metricas_y_fila_de_un_punto():
    ben = _ben()
    nombres = list(comun.INSTITUCIONES)
    EQ.comprueba_suma(_out(ben), ben)
    base = EQ.metricas(ben)
    assert base["C"]["P2P_C4"] == "intercambio"
    f = EQ.fila_punto("E0", 13, "B", 0, np.ones(6), _out(ben), ben,
                      nombres, base)
    assert f["W_P2P"] == pytest.approx(15e6)
    assert f["gini_C4"] == 0.0
    assert f["domina_P2P_C4"] == 0 and f["cambia_P2P_C4"] == 0
    assert f["P2P__Udenar"] == 5e6
    # SINU: la columna de la institucion que falta queda vacia.
    ben4 = {m: v[1:] for m, v in ben.items()}
    f4 = EQ.fila_punto("SINU", 0, "A", 0, np.ones(6), _out(ben4), ben4,
                       nombres[1:], None)
    assert f4["P2P__Udenar"] == "" and f4["cambia_P2P_C4"] == ""
    assert set(EQ.columnas()) >= set(f) - {"gsa_dif_max"}


def test_la_suma_por_institucion_tiene_que_ser_la_comunidad():
    ben = _ben()
    out = _out(ben)
    out["P2P"] += 100.0                     # 1e-6 de 15e6 son 15 COP
    with pytest.raises(ValueError):
        EQ.comprueba_suma(out, ben)


def _fila_txt(caso, fila, dom, cambia, g_p2p, g_c4, w_p2p, w_c4, motivo=""):
    f = {c: "" for c in EQ.columnas()}
    f.update(caso=caso, fila=fila, motivo=motivo, gsa_dif_max="0.0",
             idx="-1" if fila == "base" else "0", bloque="0")
    for m in EQ.MECANISMOS:
        f[f"gini_{m}"] = "0.1"
        f[f"W_{m}"] = "1.0"
    f.update(gini_P2P=str(g_p2p), gini_C4=str(g_c4), W_P2P=str(w_p2p),
             W_C4=str(w_c4), W_P2Pcom=str(w_p2p), gini_P2Pcom=str(g_p2p))
    for p in EQ.PARES:
        f[f"clase_{p}"] = "P2P domina" if dom else "intercambio"
        f[f"domina_{p}"] = str(int(dom))
        f[f"cambia_{p}"] = "" if fila == "base" else str(int(cambia))
    return f


def test_el_resumen_cuenta_lo_que_debe():
    filas = [_fila_txt("E0", "base", 0, 0, 0.12, 0.11, 10, 9)]
    filas += [_fila_txt("E0", "A", 1, 1, 0.10, 0.11, 10, 9) for _ in range(3)]
    filas += [_fila_txt("E0", "B", 0, 0, 0.12, 0.11, 10, 9) for _ in range(5)]
    filas += [_fila_txt("E0", "A", 0, 0, 0, 0, 0, 0, motivo="ValueError: x")]
    r = EQ.resume_caso("E0", filas)
    assert r["n_puntos"] == 9 and r["n_buenas"] == 8 and r["n_fallidas"] == 1
    assert r["domina_P2P_C4_n"] == 3
    assert r["domina_P2P_C4_frac"] == pytest.approx(3 / 8)
    assert r["cambia_P2P_C4_n"] == 3
    assert r["clase_P2P_C4_base"] == "intercambio"
    assert r["gini_P2P_base"] == pytest.approx(0.12)
    assert r["gini_P2P_min"] == pytest.approx(0.10)
    assert r["gini_P2P_mayor_C4_n"] == 5
    assert r["W_P2P_menor_W_C4_n"] == 0
    lo, hi = EQ.wilson(3, 8)
    assert r["domina_P2P_C4_wilson_bajo"] == lo and lo < 3 / 8 < hi
    assert "E0" in EQ.texto_resumen([r], {"E0": "al peso"}, [], None, [])


def test_la_comparacion_con_el_gsa_ve_una_diferencia():
    x = np.array([1.0, 2.0, 1.0, 1.0, 1.0, 1.0])
    out = {"P2P": 46495474.25, "P2P_menos_C4__UCC": -327562.5}
    fila = {n: repr(float(v)) for n, v in zip(comun.NOMBRES, x)}
    fila.update(idx="13", seg="2.4", P2P=repr(out["P2P"]),
                P2P_menos_C4__UCC=repr(out["P2P_menos_C4__UCC"]))
    peor, malas = EQ.compara_gsa(out, x, fila)
    assert peor == 0.0 and malas == []
    fila["P2P"] = repr(out["P2P"] + 2.0)
    _p, malas = EQ.compara_gsa(out, x, fila)
    assert [m[0] for m in malas] == ["P2P"]
    fila["P2P"] = repr(out["P2P"])
    fila["f_bolsa"] = "2.0000001"
    _p, malas = EQ.compara_gsa(out, x, fila)
    assert [m[0] for m in malas] == ["f_bolsa"]


@pytest.mark.parametrize("argv", [
    ["--casos", "CV2", "--dia", "2025-05-09", "--sin-escribir"],
    ["--casos", "X9", "--dia", "2025-05-09", "--sin-escribir"],
    ["--sin-escribir"],                                    # sin --matriz
    ["--dia", "2025-05-09", "--referencia-gsa", "x", "--sin-escribir"],
    ["--n-base", "0", "--dia", "2025-05-09", "--sin-escribir"],
])
def test_rechazos_en_voz_alta(argv):
    assert EQ.ejecuta(argv) == 2


def test_el_reanudar_lee_solo_filas_completas(tmp_path):
    import csv
    ruta = tmp_path / EQ.NOMBRE_PUNTOS
    cols = EQ.columnas()
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerow(_fila_txt("E0", "A", 1, 0, 0.1, 0.11, 10, 9))
        fh.write("E0,13,B\n")                         # truncada por un corte
    filas = EQ.lee_puntos(ruta)
    assert len(filas) == 1 and filas[0]["fila"] == "A"


@pytest.mark.skipif(not (MATRIZ / "E0").is_dir(),
                    reason="sin la matriz del canon en esta maquina")
@pytest.mark.parametrize("caso,g_p2p,g_c4,cl", [
    ("E0", 0.121, 0.115, "intercambio"),
    ("E1", 0.121, 0.143, "P2P domina"),
    ("I1", 0.499, 0.350, "intercambio"),
    ("SINU", 0.125, 0.127, "P2P domina"),
])
def test_el_gini_y_la_clase_reproducen_la_tabla_de_14_6(caso, g_p2p, g_c4,
                                                         cl):
    """La MISMA definicion: el Gini de `Por_agente` del libro del canon con
    `gini` da los de §14.6 a tres decimales, y `clase` da su clase."""
    import pandas as pd
    libro = MATRIZ / caso / "outputs" / "resultados_comparacion.xlsx"
    pa = pd.read_excel(libro, sheet_name="Por_agente")
    res = pd.read_excel(libro, sheet_name="Resumen")
    W = dict(zip(res["Escenario"], res["Ganancia_neta_COP"]))
    gp, gc = EQ.gini(pa["P2P"]), EQ.gini(pa["C4"])
    assert round(gp, 3) == g_p2p and round(gc, 3) == g_c4
    assert EQ.clase(W["P2P"], W["C4"], gp, gc) == cl
