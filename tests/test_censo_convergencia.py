"""
El censo de la campana de convergencia (H-86; D47). 2026-09-16.

Prueba la funcion pura de `reformateo/documento/scripts/sonda/
censo_convergencia.py` con tablas de horas sinteticas, sin parquet ni pyarrow,
con la misma forma que `tests/test_compara_arranque.py`.

La tabla base tiene seis horas: cuatro resueltas, con sus paradas, residuos y
costos; una de mercado sin resolver («integrador sin exito»); y una sin mercado.
Los costos son 1, 2, 3 y 4 (s) y 10, 20, 30 y 40 evaluaciones, de modo que la
mediana, el percentil 90, el maximo y la suma son exactos y se pueden escribir
a mano.

Lo que mas importa aqui es lo que el censo hace cuando **no hay medida**: un
almacen anterior a D47 no trae `residuo_reparto`, `segundos` ni `evaluaciones`,
y uno corrido sin la parada por estacionario no trae `parada_acoplado`. En esos
casos el censo tiene que decir «no medido» y no un cero que se lea como una
medicion.
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

import censo_convergencia as cc  # noqa: E402

F0 = pd.Timestamp("2025-05-05 00:00")
SIN_EXITO = "integrador sin exito al horizonte 0.4"
SIN_MERCADO = "sin mercado esa hora"

# hora, resuelta, motivo, parada, residuo, residuo_reparto, horizonte,
# segundos, evaluaciones
FILAS = [
    (0, True, None, "estacionario", 0.001, 0.000, 0.05, 1.0, 10),
    (1, True, None, "estacionario", 0.004, 0.020, 0.05, 2.0, 20),
    (2, True, None, "tope", 0.030, 0.400, 0.40, 3.0, 30),
    (3, True, None, "presupuesto", 0.020, 0.150, 0.20, 4.0, 40),
    (4, False, SIN_EXITO, None, None, None, None, None, None),
    (5, False, SIN_MERCADO, None, None, None, None, None, None),
]


def _horas(filas=FILAS, quitar=()):
    """La tabla de horas del almacen, con las columnas que se le pidan menos
    las de `quitar`, que es como sale un almacen anterior a D47."""
    d = pd.DataFrame([dict(cobertura="m1", hora=k,
                           fecha=F0 + pd.Timedelta(hours=k),
                           resuelta=r, motivo=m, parada_acoplado=pa,
                           residuo=rp, residuo_reparto=rr,
                           horizonte_usado=hu, segundos=s, evaluaciones=e)
                      for k, r, m, pa, rp, rr, hu, s, e in filas])
    return d.drop(columns=list(quitar))


@pytest.fixture(scope="module")
def censo():
    return cc.censa(_horas(), "E0_hoy")


# ─── el recuento ───────────────────────────────────────────────────────────


def test_cuenta_las_horas_y_los_motivos(censo):
    assert censo["nombre"] == "E0_hoy"
    assert censo["horas"] == 6
    # De mercado son las cuatro resueltas y la que fallo, no la sin mercado.
    assert censo["horas_mercado"] == 5
    assert censo["resueltas"] == 4
    assert censo["sin_resolver"] == 1
    assert censo["motivos_sin_resolver"] == {SIN_EXITO: 1}


def test_cuenta_los_motivos_de_parada_y_el_horizonte(censo):
    assert censo["tiene_parada"] is True
    assert censo["parada_estacionario"] == 2
    assert censo["parada_tope"] == 1
    assert censo["parada_presupuesto"] == 1
    assert censo["parada_fallo_vuelta"] == 0
    assert censo["parada_una_vuelta"] == 0
    assert censo["parada_otras"] == 0
    # El horizonte de las resueltas: 0,05 · 0,05 · 0,4 · 0,2.
    assert censo["horizonte_mediana"] == pytest.approx(0.125)
    assert censo["horizonte_max"] == pytest.approx(0.40)


def test_resume_los_dos_residuos_y_cuenta_el_reparto_en_marcha(censo):
    # Precio: 0,001 · 0,004 · 0,03 · 0,02.
    assert censo["residuo_precio_mediana"] == pytest.approx(0.012)
    assert censo["residuo_precio_max"] == pytest.approx(0.03)
    # Reparto: 0 · 0,02 · 0,4 · 0,15; con el umbral 0,01, tres pasan.
    assert censo["tiene_residuo_reparto"] is True
    assert censo["residuo_reparto_mediana"] == pytest.approx(0.085)
    assert censo["residuo_reparto_max"] == pytest.approx(0.4)
    assert censo["horas_reparto_en_marcha"] == 3


def test_el_umbral_del_reparto_manda():
    # Con el umbral en 0,1 solo quedan las dos de arriba.
    assert cc.censa(_horas(), "x", tol=0.1)["horas_reparto_en_marcha"] == 2
    assert cc.censa(_horas(), "x", tol=0.5)["horas_reparto_en_marcha"] == 0


def test_resume_el_costo_por_hora(censo):
    # Segundos 1 · 2 · 3 · 4; evaluaciones 10 · 20 · 30 · 40.
    assert censo["tiene_segundos"] is True
    assert censo["segundos_mediana"] == pytest.approx(2.5)
    assert censo["segundos_p90"] == pytest.approx(3.7)
    assert censo["segundos_max"] == pytest.approx(4.0)
    assert censo["segundos_suma"] == pytest.approx(10.0)
    assert censo["tiene_evaluaciones"] is True
    assert censo["evaluaciones_mediana"] == pytest.approx(25.0)
    assert censo["evaluaciones_p90"] == pytest.approx(37.0)
    assert censo["evaluaciones_max"] == pytest.approx(40.0)
    assert censo["evaluaciones_suma"] == pytest.approx(100.0)


def test_el_costo_se_resume_solo_sobre_las_resueltas():
    # La hora sin resolver no trae costo, y no puede arrastrar la suma ni
    # convertirse en un cero que baje la mediana.
    filas = [list(f) for f in FILAS]
    filas[4][7], filas[4][8] = 99.0, 9900      # no deberia contarse
    censo = cc.censa(_horas([tuple(f) for f in filas]), "x")
    assert censo["segundos_suma"] == pytest.approx(10.0)
    assert censo["evaluaciones_max"] == pytest.approx(40.0)


# ─── lo que no se midio ────────────────────────────────────────────────────


def test_sin_la_columna_de_parada_lo_dice_y_no_cuenta(capsys):
    censo = cc.censa(_horas(quitar=["parada_acoplado"]), "viejo")
    assert censo["tiene_parada"] is False
    assert all(censo[f"parada_{p}"] == 0 for p in cc.PARADAS)
    cc.imprime([censo], cc.TOL_REPARTO)
    salida = capsys.readouterr().out
    assert "motivo de parada: NO MEDIDO" in salida
    assert "no porque ninguna hora parara asi" in salida


def test_sin_el_residuo_del_reparto_lo_dice_y_no_cuenta(capsys):
    censo = cc.censa(_horas(quitar=["residuo_reparto"]), "viejo")
    assert censo["tiene_residuo_reparto"] is False
    assert censo["horas_reparto_en_marcha"] == 0
    assert np.isnan(censo["residuo_reparto_max"])
    # El del precio sigue estando, y se mide.
    assert censo["residuo_precio_max"] == pytest.approx(0.03)
    cc.imprime([censo], cc.TOL_REPARTO)
    salida = capsys.readouterr().out
    assert "horas con el reparto en marcha: NO MEDIDO" in salida
    assert "anterior a D47" in salida


def test_sin_el_costo_lo_dice_y_no_inventa_la_columna(capsys):
    censo = cc.censa(_horas(quitar=["segundos", "evaluaciones"]), "viejo")
    for columna in cc.COSTO:
        assert censo[f"tiene_{columna}"] is False
        for q in ("mediana", "p90", "max", "suma"):
            assert np.isnan(censo[f"{columna}_{q}"])
    cc.imprime([censo], cc.TOL_REPARTO)
    salida = capsys.readouterr().out
    assert "segundos por hora: NO MEDIDO" in salida
    assert "evaluaciones por hora: NO MEDIDO" in salida
    assert "se lee mientras tanto en el registro de la corrida" in salida


def test_un_almacen_sin_ninguna_hora_resuelta_no_revienta():
    filas = [(0, False, SIN_EXITO, None, None, None, None, None, None)]
    censo = cc.censa(_horas(filas), "vacio")
    assert (censo["resueltas"], censo["horas_mercado"]) == (0, 1)
    assert np.isnan(censo["segundos_mediana"])
    assert censo["horas_reparto_en_marcha"] == 0


# ─── fallar en voz alta ────────────────────────────────────────────────────


def test_una_tabla_incompleta_falla_en_voz_alta():
    with pytest.raises(ValueError, match="no trae"):
        cc.censa(_horas(quitar=["motivo"]), "x")


def test_las_horas_repetidas_fallan_en_voz_alta():
    d = pd.concat([_horas(), _horas()], ignore_index=True)
    with pytest.raises(ValueError, match="repetidas"):
        cc.censa(d, "x")


def test_un_umbral_que_no_es_positivo_falla_en_voz_alta():
    for malo in (0.0, -1.0, float("nan")):
        with pytest.raises(ValueError, match="tol"):
            cc.censa(_horas(), "x", tol=malo)


# ─── la carpeta de la campana y la linea de ordenes ────────────────────────


def test_encuentra_los_almacenes_de_una_carpeta(tmp_path):
    for nombre in ("E0_hoy", "K1_reparto20"):
        (tmp_path / nombre / "almacen" / "m1" / "horas").mkdir(parents=True)
    # Una subcarpeta sin almacen no cuenta, y otra cobertura tampoco.
    (tmp_path / "suelta").mkdir()
    (tmp_path / "E0_m3" / "almacen" / "m3" / "horas").mkdir(parents=True)
    hallados = cc.almacenes(tmp_path, "m1")
    assert [n for n, _ in hallados] == ["E0_hoy", "K1_reparto20"]
    assert all(r.name == "almacen" for _, r in hallados)
    with pytest.raises(FileNotFoundError, match="carpeta de la campana"):
        cc.almacenes(tmp_path / "no_existe", "m1")


def test_la_linea_de_ordenes_escribe_el_csv_y_sale_con_cero(
        monkeypatch, tmp_path, capsys):
    # Sin parquet: el cargador se sustituye por las tablas sinteticas.
    tablas = {"a": _horas(), "b": _horas(quitar=["segundos", "evaluaciones"])}
    monkeypatch.setattr(cc, "carga",
                        lambda almacen, cobertura="m1": tablas[str(almacen)])
    codigo = cc.main(["--almacen", "E0_hoy=a", "--almacen", "E0_viejo=b",
                      "--salida", str(tmp_path)])
    assert codigo == 0
    ruta = tmp_path / "censo_convergencia.csv"
    tabla = pd.read_csv(ruta, comment="#")
    assert list(tabla["nombre"]) == ["E0_hoy", "E0_viejo"]
    assert list(tabla["tiene_segundos"]) == [True, False]
    assert tabla.loc[0, "segundos_suma"] == pytest.approx(10.0)
    assert pd.isna(tabla.loc[1, "segundos_suma"])
    assert list(tabla["horas_reparto_en_marcha"]) == [3, 3]
    primera = ruta.read_text(encoding="utf-8").splitlines()[0]
    assert primera.startswith("# censo_convergencia: umbral del reparto 0.01")
    assert "las columnas `tiene_*` dicen si esa medida existe" in primera
    salida = capsys.readouterr().out
    assert "--- E0_hoy" in salida and "--- E0_viejo" in salida
    assert "segundos por hora: NO MEDIDO" in salida


def test_la_linea_de_ordenes_pasa_el_umbral(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cc, "carga",
                        lambda almacen, cobertura="m1": _horas())
    assert cc.main(["--almacen", "x=a", "--tol", "0.1",
                    "--salida", str(tmp_path)]) == 0
    tabla = pd.read_csv(tmp_path / "censo_convergencia.csv", comment="#")
    assert list(tabla["horas_reparto_en_marcha"]) == [2]
    assert "pasa de 0.1" in capsys.readouterr().out


def test_sin_fuentes_la_linea_de_ordenes_se_queja():
    with pytest.raises(SystemExit):
        cc.main([])
