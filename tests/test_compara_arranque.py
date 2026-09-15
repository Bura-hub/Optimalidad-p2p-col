"""
La comparacion de los dos arranques del acoplado (H-85; D45, D46). 2026-09-15.

Prueba la funcion pura de `reformateo/documento/scripts/sonda/
compara_arranque.py` con dos tablas sinteticas pequenas, sin parquet ni
pyarrow. Las cantidades son diadicas (exactas en float32, que es como las
guarda el almacen), de modo que las diferencias esperadas son exactas.

Siete horas, dos vendedores (V1, V2) y dos compradores (C1, C2):
  0  igual en los dos almacenes;
  1  precio indeterminado: las mismas entregas (1,5 y 3,0 (kWh)) y los
     precios movidos +0,5 y -0,5 (COP/kWh). La suma de los precios se
     conserva y la de los pagos no (+0,75 - 1,5 = -0,75 (COP)), como en la
     hora 4184 de H-85;
  2  precio indeterminado con entregas iguales entre compradores (2,0 y 2,0
     (kWh)): los pagos se mueven +0,5 y -0,5 y su suma se conserva;
  3  entregas distintas: C1 recibe 1,5 con A y 1,25 con B, y su precio pasa
     de 400 a 410;
  4  resuelta con A y sin resolver con B («integrador sin exito»);
  5  sin mercado en los dos;
  6  sin resolver en los dos (vencida con A, sin exito con B).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "reformateo" / "documento" / "scripts" / "sonda"))

import compara_arranque as ca  # noqa: E402

F0 = pd.Timestamp("2025-05-05 00:00")
SIN_EXITO = "integrador sin exito al horizonte 0.05"
VENCIDA = "vencio el plazo por hora de 15 min"


def _horas(filas):
    """filas: (hora, resuelta, motivo); motivo None en las resueltas, como
    las escribe el almacen."""
    return pd.DataFrame([dict(cobertura="m1", hora=k,
                              fecha=F0 + pd.Timedelta(hours=k),
                              resuelta=r, motivo=m) for k, r, m in filas])


def _flujos(filas, tipo=np.float32):
    """filas: (hora, vendedor, comprador, kwh, precio)."""
    return pd.DataFrame([dict(cobertura="m1", hora=k,
                              fecha=F0 + pd.Timedelta(hours=k),
                              vendedor=v, comprador=c, kwh=tipo(e),
                              precio=tipo(p), valor=tipo(e * p))
                         for k, v, c, e, p in filas])


def _hora_de_flujos(k, e11, e21, e12, e22, p1, p2):
    """Los cuatro pares de una hora: V1 y V2 a C1 y C2."""
    return [(k, "V1", "C1", e11, p1), (k, "V2", "C1", e21, p1),
            (k, "V1", "C2", e12, p2), (k, "V2", "C2", e22, p2)]


HORAS_A = _horas([(0, True, None), (1, True, None), (2, True, None),
                  (3, True, None), (4, True, None),
                  (5, False, "sin mercado esa hora"), (6, False, VENCIDA)])
HORAS_B = _horas([(0, True, None), (1, True, None), (2, True, None),
                  (3, True, None), (4, False, SIN_EXITO),
                  (5, False, "sin mercado esa hora"), (6, False, SIN_EXITO)])
FLUJOS_A = _flujos(
    _hora_de_flujos(0, 1.0, 0.5, 2.0, 1.0, 400.0, 300.0)
    + _hora_de_flujos(1, 1.0, 0.5, 2.0, 1.0, 450.0, 250.0)
    + _hora_de_flujos(2, 1.0, 1.0, 1.5, 0.5, 500.0, 350.0)
    + _hora_de_flujos(3, 1.0, 0.5, 2.0, 1.0, 400.0, 300.0)
    + _hora_de_flujos(4, 1.0, 0.5, 2.0, 1.0, 400.0, 300.0))
FLUJOS_B = _flujos(
    _hora_de_flujos(0, 1.0, 0.5, 2.0, 1.0, 400.0, 300.0)
    + _hora_de_flujos(1, 1.0, 0.5, 2.0, 1.0, 450.5, 249.5)
    + _hora_de_flujos(2, 1.0, 1.0, 1.5, 0.5, 500.25, 349.75)
    + _hora_de_flujos(3, 0.75, 0.5, 2.0, 1.0, 410.0, 300.0))

CLASE_ESPERADA = {0: "igual", 1: "precio_indeterminado",
                  2: "precio_indeterminado", 3: "entregas_distintas",
                  4: "resuelta_solo_en_a", 5: "sin_mercado",
                  6: "sin_resolver_en_las_dos"}


@pytest.fixture(scope="module")
def comparacion():
    return ca.compara(HORAS_A, FLUJOS_A, HORAS_B, FLUJOS_B)


def test_cada_hora_cae_en_su_clase(comparacion):
    tabla, _, _ = comparacion
    assert dict(zip(tabla["hora"], tabla["clase"])) == CLASE_ESPERADA
    assert list(tabla.loc[tabla["cambia"], "hora"]) == [1, 2, 3, 4]
    assert list(tabla.loc[tabla["indeterminada"], "hora"]) == [1, 2]


def test_horas_de_mercado_y_sin_resolver_con_su_motivo(comparacion):
    _, _, r = comparacion
    assert r["horas"] == 7
    assert (r["mercado_a"], r["mercado_b"]) == (6, 6)
    assert (r["resueltas_a"], r["resueltas_b"]) == (5, 4)
    assert r["sin_resolver_a"] == {VENCIDA: 1}
    assert r["sin_resolver_b"] == {SIN_EXITO: 2}
    assert r["horas_sin_resolver_b"] == [4, 6]
    assert r["resueltas_en_las_dos"] == 4
    assert r["cambian"] == 4
    assert r["indeterminadas"] == 2
    assert sum(r["clases"].values()) == 7


def test_d46_el_pago_de_cada_comprador_y_la_suma(comparacion):
    tabla, detalle, r = comparacion
    t = tabla.set_index("hora")
    # Hora 1: los precios se mueven +0,5 y -0,5 y su suma se conserva; los
    # pagos se mueven +0,75 y -1,5, y su suma no (energia de la hora 4,5
    # (kWh), tolerancia 1e-3 x 4,5 = 0,0045 (COP)).
    assert t.loc[1, "dif_suma_precio"] == pytest.approx(0.0, abs=1e-12)
    assert t.loc[1, "dif_suma_pago_cop"] == pytest.approx(-0.75, abs=1e-9)
    assert not bool(t.loc[1, "conserva_pago"])
    d1 = detalle[detalle["hora"] == 1].set_index("comprador")
    assert d1.loc["C1", "dif_pago"] == pytest.approx(0.75, abs=1e-9)
    assert d1.loc["C2", "dif_pago"] == pytest.approx(-1.5, abs=1e-9)
    assert d1["dif_entrega"].abs().max() == 0.0
    # Hora 2: con entregas iguales entre compradores la suma se conserva.
    assert t.loc[2, "dif_suma_pago_cop"] == pytest.approx(0.0, abs=1e-9)
    assert bool(t.loc[2, "conserva_pago"])
    assert r["indeterminadas_conservan_pago"] == 1
    # Las horas que no son indeterminadas no dicen nada de la conservacion.
    assert t.loc[[0, 3, 4, 5, 6], "conserva_pago"].isna().all()
    # Por comprador, sobre las dos horas indeterminadas: C1 +0,75 +0,5 y
    # C2 -1,5 -0,5.
    ip = r["pago_indeterminadas"]
    assert ip.loc["C1", "dif_pago_suma"] == pytest.approx(1.25, abs=1e-9)
    assert ip.loc["C2", "dif_pago_suma"] == pytest.approx(-2.0, abs=1e-9)
    assert ip.loc["C2", "dif_pago_max_abs"] == pytest.approx(1.5, abs=1e-9)


def test_maximos_y_medias_sobre_las_horas_resueltas_con_los_dos(comparacion):
    _, detalle, r = comparacion
    # Ocho pares hora-comprador (horas 0 a 3). Precio: 0, 0, 0,5, 0,5,
    # 0,25, 0,25, 10, 0. Entrega: solo C1 en la hora 3, -0,25. Pago: el
    # mayor, C1 en la hora 3, 1,25 x 410 - 1,5 x 400 = -87,5 (COP).
    assert detalle["en_los_dos"].sum() == 8
    assert r["dif_precio"] == pytest.approx((10.0, 11.5 / 8), abs=1e-9)
    assert r["dif_entrega"] == pytest.approx((0.25, 0.25 / 8), abs=1e-9)
    assert r["dif_pago"][0] == pytest.approx(87.5, abs=1e-9)
    # El pago de cada comprador sumado sobre las horas 0 a 3.
    v = r["pago_ventana"]
    assert v.loc["C1", "dif_pago"] == pytest.approx(0.75 + 0.5 - 87.5,
                                                    abs=1e-9)
    assert v.loc["C2", "dif_pago"] == pytest.approx(-1.5 - 0.5, abs=1e-9)
    assert v.loc["C1", "pago_a"] == pytest.approx(
        1.5 * 400 + 1.5 * 450 + 2.0 * 500 + 1.5 * 400, abs=1e-9)


def test_las_tolerancias_por_defecto():
    # Decision del controlador (2026-09-15): la tolerancia de las entregas es
    # combinada, max(1e-4 (kWh), 1e-5 x la mayor entrega), porque el almacen
    # guarda en float32; la del precio sigue absoluta, 1e-3 (COP/kWh).
    assert ca.TOL_KWH == 1e-4
    assert ca.TOL_REL == 1e-5
    assert ca.TOL_PRECIO == 1e-3


def _clase_de_una_hora(e_a, p_a, e_b, p_b, tipo=np.float64, **tol):
    ha = _horas([(0, True, None)])
    fa = _flujos([(0, "V1", "C1", e_a, p_a)], tipo=tipo)
    fb = _flujos([(0, "V1", "C1", e_b, p_b)], tipo=tipo)
    return list(ca.compara(ha, fa, ha, fb, **tol)[0]["clase"])[0]


def test_el_borde_de_las_tolerancias():
    # En doble precision. Por debajo de las dos: 5e-4 (COP/kWh) de precio y
    # 5e-5 (kWh) de entrega, la mitad de cada tolerancia absoluta.
    assert _clase_de_una_hora(1.0, 400.0, 1.0 + 5e-5, 400.0 + 5e-4) == "igual"
    # Por encima, cada una por su lado.
    assert _clase_de_una_hora(1.0, 400.0, 1.0 + 2e-4, 400.0) == \
        "entregas_distintas"
    assert _clase_de_una_hora(1.0, 400.0, 1.0, 400.0 + 2e-3) == \
        "precio_indeterminado"
    # La parte relativa: con 500 (kWh) el umbral es 5e-3 (kWh).
    assert _clase_de_una_hora(500.0, 400.0, 500.0 + 3e-3, 400.0) == "igual"
    assert _clase_de_una_hora(500.0, 400.0, 500.0 + 7e-3, 400.0) == \
        "entregas_distintas"
    # Sin la parte relativa, los 3e-3 (kWh) ya no coinciden.
    assert _clase_de_una_hora(500.0, 400.0, 500.0 + 3e-3, 400.0,
                              tol_rel=0.0) == "entregas_distintas"


def test_un_redondeo_de_float32_en_la_entrega_no_oculta_un_precio_indeterminado():
    # Lo que D46 quiere contar, con los numeros como los guarda el almacen:
    # la entrega cerca de 20 (kWh) difiere en UNA unidad de redondeo de
    # float32 (unos 1,9e-6 (kWh)) y el precio en 0,4 (COP/kWh). Con la
    # tolerancia absoluta de 1e-6 habria salido «entregas distintas».
    e_a = np.float32(19.5)
    e_b = np.nextafter(e_a, np.float32(np.inf))
    assert e_b.dtype == np.float32 and 1e-6 < float(e_b) - float(e_a) < 3e-6
    assert _clase_de_una_hora(e_a, 400.0, e_b, 400.4,
                              tipo=np.float32) == "precio_indeterminado"


def test_una_diferencia_de_entrega_de_un_milesimo_es_entregas_distintas():
    # 1e-3 (kWh) cerca de 20 (kWh) pasa del umbral combinado, 1,95e-4.
    assert _clase_de_una_hora(np.float32(19.5), 400.0, np.float32(19.501),
                              400.0, tipo=np.float32) == "entregas_distintas"


def test_un_comprador_que_falta_en_un_lado_se_marca():
    ha = _horas([(0, True, None)])
    fa = _flujos([(0, "V1", "C1", 1.0, 400.0), (0, "V1", "C2", 1.0, 300.0)])
    fb = _flujos([(0, "V1", "C1", 1.0, 400.0)])
    tabla, detalle, _ = ca.compara(ha, fa, ha, fb)
    assert list(tabla["clase"]) == ["compradores_distintos"]
    assert bool(tabla["cambia"].iloc[0])
    assert int(detalle["en_los_dos"].sum()) == 1


def test_ventanas_distintas_fallan_en_voz_alta():
    hb = _horas([(0, True, None), (1, True, None), (2, True, None),
                 (3, True, None), (4, False, SIN_EXITO),
                 (5, False, "sin mercado esa hora"), (6, False, SIN_EXITO),
                 (7, False, "sin mercado esa hora")])
    with pytest.raises(ValueError, match="misma ventana"):
        ca.compara(HORAS_A, FLUJOS_A, hb, FLUJOS_B)


def test_una_hora_resuelta_sin_flujos_falla_en_voz_alta():
    fb = FLUJOS_B[FLUJOS_B["hora"] != 2]
    with pytest.raises(ValueError, match="sin flujos"):
        ca.compara(HORAS_A, FLUJOS_A, HORAS_B, fb)


def test_un_valor_no_finito_falla_en_voz_alta():
    fb = FLUJOS_B.copy()
    fb.loc[0, "kwh"] = np.nan
    with pytest.raises(ValueError, match="no finitos"):
        ca.compara(HORAS_A, FLUJOS_A, HORAS_B, fb)


def test_la_linea_de_ordenes_escribe_los_csv_y_sale_con_cero(
        monkeypatch, tmp_path, capsys):
    # Sin parquet: el cargador se sustituye por las tablas sinteticas.
    tablas = {"a": (HORAS_A, FLUJOS_A), "b": (HORAS_B, FLUJOS_B)}
    monkeypatch.setattr(ca, "carga", lambda almacen, cobertura="m1":
                        tablas[almacen])
    codigo = ca.main(["a", "b", "--etiqueta", "E4", "--salida",
                      str(tmp_path)])
    assert codigo == 0
    ruta = tmp_path / "compara_arranque_E4.csv"
    hora_a_hora = pd.read_csv(ruta, comment="#")
    assert len(hora_a_hora) == 7
    assert list(hora_a_hora["clase"]) == [CLASE_ESPERADA[k]
                                          for k in range(7)]
    por_comprador = pd.read_csv(tmp_path / "compara_arranque_E4_compradores.csv",
                                comment="#")
    assert len(por_comprador) == 8
    # La primera linea de cada CSV dice que tolerancias se usaron.
    tolerancias = ("max(0.0001 (kWh), 1e-05 x max(|a|, |b|)); precio: "
                   "|dif| <= 0.001 (COP/kWh)")
    for nombre in ("compara_arranque_E4.csv",
                   "compara_arranque_E4_compradores.csv"):
        primera = (tmp_path / nombre).read_text(encoding="utf-8").splitlines()[0]
        assert primera.startswith("# compara_arranque E4: tolerancias ")
        assert tolerancias in primera
    salida = capsys.readouterr().out
    assert "tolerancias: entrega: |dif| <= " + tolerancias in salida
    assert "horas cuyo resultado cambia: 4" in salida
    assert "D46, horas de precio indeterminado: 2" in salida


def test_la_linea_de_ordenes_pasa_las_tolerancias(monkeypatch, tmp_path,
                                                   capsys):
    # Con --tol-rel 0 y --tol-kwh 1e-6 la hora del redondeo de float32 sale
    # como entregas distintas, y el resumen lo dice.
    e_a = np.float32(19.5)
    e_b = np.nextafter(e_a, np.float32(np.inf))
    ha = _horas([(0, True, None)])
    tablas = {"a": (ha, _flujos([(0, "V1", "C1", e_a, 400.0)])),
              "b": (ha, _flujos([(0, "V1", "C1", e_b, 400.4)]))}
    monkeypatch.setattr(ca, "carga", lambda almacen, cobertura="m1":
                        tablas[almacen])
    assert ca.main(["a", "b", "--tol-kwh", "1e-6", "--tol-rel", "0",
                    "--salida", str(tmp_path)]) == 0
    t = pd.read_csv(tmp_path / "compara_arranque.csv", comment="#")
    assert list(t["clase"]) == ["entregas_distintas"]
    assert "max(1e-06 (kWh), 0 x max(|a|, |b|))" in capsys.readouterr().out
