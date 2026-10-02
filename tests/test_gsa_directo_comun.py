"""Pruebas de `gsa_directo/comun.py` (T1 del GSA directo, D73-D79).

Actividad 4.1. Segundos, sin datos.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from gsa_directo import comun  # noqa: E402


def test_b_es_catorce_y_seis_entradas():
    assert comun.D_ENTRADAS == 6
    assert comun.B == 14
    assert comun.PROBLEMA["num_vars"] == 6
    assert len(comun.SALIDAS_D75) == 14
    # 2026-10-02: C2ppa y P2Pcom y sus siete brechas, AL FINAL.
    assert len(comun.SALIDAS) == 14 + 2 + 7
    assert comun.SALIDAS[:14] == comun.SALIDAS_D75


def test_rangos_del_diseno_tal_cual():
    esperado = {"f_cv": [0.25, 2.0], "f_bolsa": [0.75, 4.0],
                "f_tarifa": [0.90, 1.10], "f_peaje": [0.85, 1.15],
                "e_G": [0.95, 1.05], "e_D": [0.95, 1.05]}
    assert dict(zip(comun.NOMBRES, comun.SOPORTES)) == esperado


@pytest.mark.parametrize("n", [16, 32])
def test_bloques_anidados_con_la_semilla_del_diseno(n):
    """Los n primeros bloques de la muestra de 64 son la muestra de n."""
    X64 = comun.muestra(64)
    Xn = comun.muestra(n)
    assert Xn.shape == (n * comun.B, 6)
    assert np.array_equal(Xn, X64[: n * comun.B])


def test_muestra_dentro_de_los_rangos():
    X = comun.muestra(16)
    for i, (a, b) in enumerate(comun.SOPORTES):
        assert X[:, i].min() >= a and X[:, i].max() <= b


def test_huella_cambia_con_un_soporte(monkeypatch):
    h = comun.huella_diseno("E0", 2048)
    otro = [list(s) for s in comun.SOPORTES]
    otro[1] = [0.9, 4.9]
    monkeypatch.setattr(comun, "SOPORTES", otro)
    assert comun.huella_diseno("E0", 2048) != h


def test_huella_cambia_con_caso_n_y_semilla():
    h = comun.huella_diseno("E0", 2048, 42)
    assert h != comun.huella_diseno("E2", 2048, 42)
    assert h != comun.huella_diseno("E0", 1024, 42)
    assert h != comun.huella_diseno("E0", 2048, 7)


def test_n_de_cada_caso():
    assert [comun.n_base_de(c) for c in ("E0", "E2", "E4")] == [2048] * 3
    assert {comun.n_base_de(c) for c in comun.CASOS
            if c not in ("E0", "E2", "E4")} == {512}
    assert sorted(comun.ORDEN_CASOS) == sorted(comun.CASOS)


def test_casos_iguales_a_los_del_lanzador():
    """La opcion de cada caso es la de CASOS_MATRIZ de run_servidor.sh:
    si alguien cambia una, esta prueba lo dice."""
    texto = (RAIZ / "modelo_base" / "run_servidor.sh").read_text(
        encoding="utf-8")
    bloque = re.search(r"^CASOS_MATRIZ=\((.*?)^\)", texto, re.S | re.M)
    assert bloque
    pares = re.findall(r'"([A-Z0-9]+):([^"]*)"', bloque.group(1))
    assert dict(pares) == comun.CASOS


def test_opciones_de_los_casos():
    assert comun.opciones_caso("P1")["factor_demanda"] == pytest.approx(1 / 7)
    assert comun.opciones_caso("P2")["factor_generacion"] == 7.0
    assert comun.opciones_caso("I1")["escala_agente"] == "UCC:neto_cero"
    assert comun.opciones_caso("N1")["neto_cero"] is True
    assert comun.opciones_caso("CV2")["factor_cv"] == 2.0
    assert comun.nombres_caso("SINU") == ["Mariana", "UCC", "HUDN", "Cesmag"]
    with pytest.raises(ValueError):
        comun.opciones_caso("E9")


def test_columnas_por_institucion():
    assert len(comun.salidas_institucion(comun.INSTITUCIONES)) == 5 * 10
    assert len(comun.salidas_institucion(comun.nombres_caso("SINU"))) == 4 * 10
    cols = comun.columnas_salida(comun.INSTITUCIONES)
    assert cols[:23] == list(comun.SALIDAS) and "C2" in cols
    assert len(cols) == len(set(cols))


def test_cv2_fuera_del_sobol_y_en_la_compuerta():
    """Ronda de arreglos de la tarea G, I-1: CV2 NO corre el Sobol (f_cv lo
    sacaria del rango aprobado), pero sigue entre los trece de la compuerta
    del punto base y de las deterministas. Si alguien lo devuelve a
    CASOS_GSA del lanzador o a CASOS_SOBOL, esta prueba falla."""
    assert "CV2" not in comun.CASOS_SOBOL
    assert "CV2" in comun.ORDEN_CASOS and "CV2" in comun.CASOS
    assert set(comun.CASOS_SOBOL) | {"CV2"} == set(comun.CASOS)
    texto = (RAIZ / "modelo_base" / "run_servidor.sh").read_text(
        encoding="utf-8")
    m = re.search(r'^CASOS_GSA="([^"]*)"', texto, re.M)
    assert m, "no se halla CASOS_GSA en el lanzador"
    assert "CV2" not in m.group(1).split()
    assert tuple(m.group(1).split()) == comun.CASOS_SOBOL


def test_rotulo_de_f_cv():
    """f_cv se rotula como el descuento del art. 25, no como el Cv de la
    tarifa."""
    assert comun.ROTULOS["f_cv"] == ("descuento de comercializar sobre la "
                                     "permuta (art. 25)")
    assert set(comun.ROTULOS) == set(comun.NOMBRES)


def test_salidas_de_d75_sin_cambiar_y_las_nuevas_al_final():
    """2026-10-02: las catorce de D75 conservan nombre, orden y definicion;
    la brecha vieja del colectivo sigue siendo la del VIEJO mercado por el
    colectivo, y las nuevas (C2ppa, P2Pcom) van detras, con su definicion."""
    assert comun.SALIDAS_D75 == (
        "P2P", "P2P_colectivo", "C1", "C3", "C4", "C5", "energia",
        "excedente", "parte_vendedor", "P2P_menos_C1", "P2P_menos_C4",
        "P2Pcol_menos_C1", "C4_menos_C1", "P2P_menos_C5")
    assert comun.BRECHAS["P2Pcol_menos_C1"] == ("P2P_colectivo", "C1")
    assert comun.SALIDAS[14:16] == ("P2Pcom", "C2ppa")
    assert comun.BRECHAS_NUEVAS == {
        "P2Pcom_menos_C4": ("P2Pcom", "C4"),
        "P2Pcom_menos_C1": ("P2Pcom", "C1"),
        "P2Pcom_menos_P2P": ("P2Pcom", "P2P"),
        "C2ppa_menos_C1": ("C2ppa", "C1"),
        "C2ppa_menos_C4": ("C2ppa", "C4"),
        "C2ppa_menos_P2P": ("C2ppa", "P2P"),
        "P2Pcom_menos_C2ppa": ("P2Pcom", "C2ppa")}
    assert list(comun.BRECHAS)[:5] == ["P2P_menos_C1", "P2P_menos_C4",
                                       "P2Pcol_menos_C1", "C4_menos_C1",
                                       "P2P_menos_C5"]
    assert set(comun.BRECHAS_NUEVAS) <= set(comun.BRECHAS_INSTITUCION)
    # «C2» sigue siendo la identidad de CAL-52, no el PPA.
    assert comun.IDENTIDADES == ("C2",) and "C2ppa" not in comun.IDENTIDADES
