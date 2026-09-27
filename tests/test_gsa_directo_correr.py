"""Pruebas de `gsa_directo/correr.py` con el evaluador FALSO (T3).

Actividad 4.1. Segundos, sin datos: el modo `--verificar` recorre toda la
maquinaria (pool con ventana, CSV con fsync, meta, reanudar, humo) sin el
modelo. Todo escribe en carpetas temporales.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from gsa_directo import comun, correr  # noqa: E402

N = 16
M = N * comun.B


def _corre(tmp, *extra):
    return correr.ejecuta(["--caso", "E0", "--n-base", str(N),
                           "--procesos", "2", "--verificar",
                           "--salidas", str(tmp), *extra])


def _csv(tmp):
    return tmp / "E0" / f"muestras_E0_n{N}_s42_VERIF.csv"


def _filas(tmp):
    with open(_csv(tmp), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_corrida_completa_y_meta(tmp_path):
    assert _corre(tmp_path) == 0
    filas = _filas(tmp_path)
    assert sorted(int(r["idx"]) for r in filas) == list(range(M))
    meta = json.loads((tmp_path / "E0" / f"muestras_E0_n{N}_s42_VERIF"
                       ".meta.json").read_text(encoding="utf-8"))
    assert meta["M"] == M and meta["verificar"] is True
    assert meta["huella"] == comun.huella_diseno("E0", N)
    assert set(meta["punto_base"]) == set(comun.columnas_salida(
        comun.INSTITUCIONES))
    # Las entradas escritas son la muestra de Saltelli, fila por fila.
    X = comun.muestra(N)
    for r in filas:
        i = int(r["idx"])
        np.testing.assert_array_equal([float(r[c]) for c in comun.NOMBRES],
                                      X[i])


def test_sin_reanudar_no_pisa(tmp_path):
    assert _corre(tmp_path) == 0
    assert _corre(tmp_path) == 2


def test_reanudar_reintenta_las_fallidas_sin_duplicar(tmp_path, monkeypatch):
    monkeypatch.setenv("GSA_DIRECTO_FALSO_FALLA", "3,7")
    # Sin la parada temprana: con n = 16 un solo bloque fallido ya es mas
    # del 1 % y pararia (esa parada se prueba aparte).
    assert _corre(tmp_path, "--tolera-fallos") == 0
    filas = _filas(tmp_path)
    malas = {int(r["idx"]) for r in filas if r["motivo"]}
    assert malas == {3, 7}
    monkeypatch.delenv("GSA_DIRECTO_FALSO_FALLA", raising=False)
    assert _corre(tmp_path, "--reanudar") == 0
    filas = _filas(tmp_path)
    idx = [int(r["idx"]) for r in filas]
    assert sorted(idx) == list(range(M))          # sin duplicados
    assert not any(r["motivo"] for r in filas)
    assert (_csv(tmp_path).with_suffix(".csv.bak")).exists()


def test_reanudar_repara_una_fila_truncada(tmp_path):
    assert _corre(tmp_path) == 0
    texto = _csv(tmp_path).read_text(encoding="utf-8")
    lineas = texto.splitlines()
    ultima = lineas[-1]
    idx_ultima = int(ultima.split(",")[0])
    # Un corte a mitad de escritura: la ultima fila queda a medias.
    _csv(tmp_path).write_text("\n".join(lineas[:-1]) + "\n"
                              + ultima[: len(ultima) // 3],
                              encoding="utf-8")
    assert _corre(tmp_path, "--reanudar") == 0
    filas = _filas(tmp_path)
    idx = [int(r["idx"]) for r in filas]
    assert sorted(idx) == list(range(M))
    assert idx.count(idx_ultima) == 1


def test_reanudar_sin_pendientes_no_toca_nada(tmp_path):
    assert _corre(tmp_path) == 0
    antes = _csv(tmp_path).read_bytes()
    assert _corre(tmp_path, "--reanudar") == 0
    assert _csv(tmp_path).read_bytes() == antes


def test_reanudar_con_otro_dato_aborta(tmp_path):
    assert _corre(tmp_path) == 0
    meta_p = tmp_path / "E0" / f"muestras_E0_n{N}_s42_VERIF.meta.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    meta["huella_datos"] = "otro"
    meta_p.write_text(json.dumps(meta), encoding="utf-8")
    assert _corre(tmp_path, "--reanudar") == 2


def test_n_que_no_es_potencia_de_dos_aborta(tmp_path):
    assert correr.ejecuta(["--caso", "E0", "--n-base", "24", "--verificar",
                           "--salidas", str(tmp_path)]) == 2


def test_humo_imprime_mediana_y_plan(tmp_path, capsys):
    rc = correr.ejecuta(["--caso", "E0", "--humo", "4", "--procesos", "2",
                         "--verificar", "--salidas", str(tmp_path),
                         "--proyecta", "E0:2048 E2:2048"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "HUMO_MEDIANA_MS=" in out
    assert "NBASE_PROPUESTO=2048" in out
    assert "CASOS_NOCHE=E0 E2" in out
    assert not any(tmp_path.iterdir())       # el humo no escribe nada


def test_plan_de_la_noche():
    # 8 s y 16 procesos: E0 + E2 a 2 048 son 7,96 h y caben en 9.
    p = correr.planifica(8.0, 16, [("E0", 2048), ("E2", 2048)], 9.0)
    assert p["n_diseno"] == 2048 and not p["recortado"] and not p["siguiente"]
    # 12 s (ronda 2, m-1): E0 cabe solo a 2 048 y va; E2 pasa a la noche
    # siguiente CON SU n. Ya no se recortan los dos a 1 024.
    p = correr.planifica(12.0, 16, [("E0", 2048), ("E2", 2048)], 9.0)
    assert [(c, n) for c, n, _ in p["noche"]] == [("E0", 2048)]
    assert p["siguiente"] == ["E2"] and not p["recortado"]
    # 20 s: ni E0 solo cabe a 2 048 (9,96 h): se recorta E0, y solo E0.
    p = correr.planifica(20.0, 16, [("E0", 2048), ("E2", 2048)], 9.0)
    assert [(c, n) for c, n, _ in p["noche"]] == [("E0", 1024)]
    assert p["recortado"] and p["n_diseno"] == 1024
    assert p["siguiente"] == ["E2"]
    # Noche del 4: E4 a 2 048 no se recorta; de los diez, lo que no cabe pasa
    # a la noche siguiente, en su orden.
    nueve = [(c, 512) for c in comun.CASOS_SOBOL if c not in
             comun.CASOS_DISENO]
    assert len(nueve) == 9 and "CV2" not in dict(nueve)
    p = correr.planifica(8.0, 16, [("E4", 2048)] + nueve, 9.0)
    assert p["n_diseno"] == 2048
    assert [c for c, _, _ in p["noche"]] == ["E4", "E1", "E3", "E5", "P1",
                                             "P2"]
    assert p["siguiente"] == ["K1", "I1", "N1", "SINU"]
    assert p["horas_total"] <= 9.0
    # Con FORZAR, todo y sin recorte.
    p = correr.planifica(8.0, 16, [("E4", 2048)] + nueve, 9.0, forzar=True)
    assert not p["siguiente"] and p["n_diseno"] == 2048


def test_los_doce_sin_casos_no_recortan_el_diseno():
    """Ronda 2, m-1: lanzar sin CASOS (los doce) a 8 s y 16 procesos no
    recorta E0, E2 y E4 a 1 024 para meterlos juntos: corre E0 y E2 a 2 048
    esta noche y deja E4 (a 2 048) y los demas para la siguiente, que es el
    calendario del diseno."""
    doce = [(c, comun.n_base_de(c)) for c in comun.CASOS_SOBOL]
    p = correr.planifica(8.0, 16, doce, 9.0)
    assert [(c, n) for c, n, _ in p["noche"]] == [("E0", 2048), ("E2", 2048)]
    assert not p["recortado"] and p["n_diseno"] == 2048
    assert p["siguiente"][0] == "E4" and len(p["siguiente"]) == 10
    # A 5,5 s caben los tres de diseno, a 2 048, y algo del resto.
    p = correr.planifica(5.5, 16, doce, 9.0)
    assert [c for c, _, _ in p["noche"]][:3] == ["E0", "E2", "E4"]
    assert all(n == 2048 for c, n, _ in p["noche"] if c in comun.CASOS_DISENO)


def test_plan_que_no_cabe_ni_con_el_minimo():
    p = correr.planifica(3600.0, 1, [("E0", 2048)], 1.0)
    assert not p["cabe"] and p["n_diseno"] == correr.N_MINIMO


@pytest.mark.parametrize("fila,ok", [
    ({"motivo": "", "idx": "1", **{s: "1.0" for s in comun.SALIDAS}}, True),
    ({"motivo": "ValueError: x", "idx": "1",
      **{s: "" for s in comun.SALIDAS}}, False),
    ({"motivo": "", "idx": "1", **{s: "nan" for s in comun.SALIDAS}}, False),
])
def test_fila_valida(fila, ok):
    cols = list(fila)
    assert correr.fila_valida(fila, cols) is ok


# ── Ronda de arreglos de la tarea G ─────────────────────────────────────────
def test_cv2_no_corre_el_sobol(tmp_path, capsys):
    """I-1: CV2 es E0 con Cv x 2; f_cv lo sacaria del rango aprobado."""
    assert correr.ejecuta(["--caso", "CV2", "--n-base", str(N), "--verificar",
                           "--salidas", str(tmp_path)]) == 2
    assert "no corre el Sobol" in capsys.readouterr().out
    assert not any(tmp_path.iterdir())
    with pytest.raises(SystemExit):
        correr._lee_pedidos("E0:2048 CV2:512")


def test_parada_temprana_por_bloques_fallidos(tmp_path, monkeypatch, capsys):
    """I-2: con n = 16 un bloque fallido ya es mas del 1 % del caso: la
    corrida para con codigo 8 en vez de terminar y dejarlo al analisis."""
    monkeypatch.setenv("GSA_DIRECTO_FALSO_FALLA", "3")
    assert _corre(tmp_path) == 8
    out = capsys.readouterr().out
    assert "PARADA TEMPRANA" in out and "SEGURO" in out
    filas = _filas(tmp_path)
    assert len(filas) < M                       # no llego al final
    assert {int(r["idx"]) for r in filas if r["motivo"]} == {3}


def _alimenta(r, n, fallidos, pos=0):
    """Pasa los n bloques por la Recuento, fila a fila y en orden, con una
    fila fallida en cada bloque de `fallidos`; devuelve (veredicto, bloque)
    en cuanto para, o ('', n)."""
    B = comun.B
    fallidos = set(fallidos)
    for b in range(n):
        for k in range(B):
            falla = b in fallidos and k == pos
            r.anota(b * B + k, fallo=falla)
            if k == B - 1 or falla:
                v = r.veredicto()
                if v:
                    return v, b
    return "", n


def test_recuento_seguro_y_tasa():
    B = comun.B
    assert correr.FACTOR_TASA == 4
    # n = 2 048: la tasa mira desde 256 bloques terminados y para con mas del
    # 4 % de ellos (10,24): 10 no, 11 si, y el mensaje dice TASA.
    r = correr.Recuento(2048)
    assert r.minimo == 256
    v, b = _alimenta(r, 256, range(0, 250, 25))             # 10 fallidos
    assert v == ""
    r = correr.Recuento(2048)
    v, b = _alimenta(r, 256, range(0, 253, 23))             # 11 fallidos
    assert v.startswith("TASA") and "sugiere un fallo sistematico" in v
    assert b == 255
    # Antes del minimo solo para lo SEGURO: mas del 1 % de los 512 bloques.
    r = correr.Recuento(512)
    for b in range(5):
        r.anota(b * B, fallo=True)
    assert r.veredicto() == ""
    r.anota(5 * B, fallo=True)
    assert r.veredicto().startswith("SEGURO")              # 6 > 5,12
    assert "el analisis lo rechazara" in r.veredicto()
    # Las filas buenas de una tanda anterior cuentan como terminadas.
    r = correr.Recuento(64, ya_buenas=range(16 * B))
    assert r.terminados == 16


def test_el_prefijo_nunca_trunca_el_csv_ni_el_respaldo(tmp_path, monkeypatch):
    """M-6: si la reescritura del prefijo muere antes del fsync, el CSV y su
    .bak quedan enteros (antes el CSV se truncaba y el siguiente --reanudar
    pisaba el .bak bueno con el truncado)."""
    monkeypatch.setenv("GSA_DIRECTO_FALSO_FALLA", "5")
    assert _corre(tmp_path, "--tolera-fallos") == 0
    monkeypatch.delenv("GSA_DIRECTO_FALSO_FALLA", raising=False)
    antes = _csv(tmp_path).read_bytes()

    def muere(fd):
        raise OSError("corte simulado antes del fsync")

    monkeypatch.setattr(correr.os, "fsync", muere)
    with pytest.raises(OSError):
        _corre(tmp_path, "--reanudar")
    monkeypatch.undo()                  # devuelve fsync (y todo lo demas)
    monkeypatch.delenv("GSA_DIRECTO_FALSO_FALLA", raising=False)
    assert _csv(tmp_path).read_bytes() == antes
    assert not _csv(tmp_path).with_suffix(".csv.bak").exists()
    # Y la reanudacion de verdad deja el .bak igual al CSV de antes.
    assert _corre(tmp_path, "--reanudar") == 0
    assert _csv(tmp_path).with_suffix(".csv.bak").read_bytes() == antes
    assert not any(p.suffix == ".tmp" for p in (tmp_path / "E0").iterdir())


def test_un_caso_no_se_amplia_reutilizando_filas(tmp_path, capsys):
    """M-4: con una corrida de n = 16, pedir n = 32 se rechaza en claro."""
    assert _corre(tmp_path) == 0
    capsys.readouterr()
    rc = correr.ejecuta(["--caso", "E0", "--n-base", "32", "--procesos", "2",
                         "--verificar", "--salidas", str(tmp_path)])
    assert rc == 2
    assert "no se amplia reutilizando sus filas" in capsys.readouterr().out
    assert not (tmp_path / "E0" / "muestras_E0_n32_s42_VERIF.csv").exists()


def test_reanudar_con_otro_codigo_avisa_y_lo_guarda(tmp_path, capsys):
    """M-5: la meta guarda la lista de versiones del codigo; si cambia entre
    tandas, se avisa."""
    assert _corre(tmp_path) == 0
    meta_p = tmp_path / "E0" / f"muestras_E0_n{N}_s42_VERIF.meta.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    assert "descuento de comercializar" in meta["rotulos"]["f_cv"]
    meta["codigo"] = "otro"
    meta.pop("codigos")
    meta_p.write_text(json.dumps(meta), encoding="utf-8")
    capsys.readouterr()
    assert _corre(tmp_path, "--reanudar") == 0
    assert "el CODIGO cambio" in capsys.readouterr().out
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    assert meta["codigos"][0] == "otro" and len(meta["codigos"]) == 2


# ── Ronda 2 de la tarea G ───────────────────────────────────────────────────
def test_casos_que_el_analisis_acepta_no_paran():
    """R-1: los escenarios de la re-revision que paraban con el umbral simple
    y el analisis aceptaba: ahora ninguno para."""
    n512, n2048 = 512, 2048
    # S1: dos fallos en los bloques 0 y 1 (0,39 %).
    assert _alimenta(correr.Recuento(n512), n512, [0, 1])[0] == ""
    # S2: cinco fallos repartidos parejos (0,98 %).
    assert _alimenta(correr.Recuento(n512), n512,
                     [0, 100, 200, 300, 400])[0] == ""
    # S6: tres fallos en los primeros 256 de 2 048.
    assert _alimenta(correr.Recuento(n2048), n2048, [0, 1, 2])[0] == ""
    # S7: veinte fallos repartidos parejos en 2 048 (0,98 %).
    assert _alimenta(correr.Recuento(n2048), n2048,
                     range(0, 2000, 100))[0] == ""


def _monte_carlo(n, p, reps, semilla):
    rng = np.random.default_rng(semilla)
    fp = paradas = 0
    bloques = []
    for _ in range(reps):
        falla = np.flatnonzero(rng.random(n) < p)
        v, b = _alimenta(correr.Recuento(n), n, falla,
                         pos=int(rng.integers(0, comun.B)))
        if v:
            paradas += 1
            bloques.append(b)
            if falla.size <= correr.UMBRAL_FALLOS * n:
                fp += 1
    return fp, paradas, bloques


def test_monte_carlo_cero_falsos_positivos_al_medio_por_ciento():
    """R-1: con un 0,5 % de bloques fallidos (independientes), ninguna
    parada en un caso que el analisis aceptaria. Con n = 512 es cierto por
    construccion (la tasa al 4 % no se adelanta a la regla segura); con
    n = 2 048 lo fija el Monte Carlo."""
    fp, _, _ = _monte_carlo(512, 0.005, 300, 11)
    assert fp == 0
    fp, _, _ = _monte_carlo(2048, 0.005, 60, 12)
    assert fp == 0
    # Por construccion en n = 512: con 4 % desde el bloque 128, la tasa pide
    # al menos 6 fallidos, que ya es mas del 1 % de 512.
    assert int(correr.FACTOR_TASA * correr.UMBRAL_FALLOS * 128) + 1 \
        > correr.UMBRAL_FALLOS * 512


def test_monte_carlo_detecta_un_caso_roto_al_cinco_por_ciento():
    """R-1: un caso con un 5 % de bloques fallidos para siempre, y pronto:
    la mediana, antes de un tercio de la corrida con n = 512 y en el minimo
    de la tasa (256 bloques) con n = 2 048; ninguno pasa de la mitad."""
    _, paradas, bloques = _monte_carlo(512, 0.05, 100, 21)
    assert paradas == 100 and np.median(bloques) < 512 // 3
    assert max(bloques) < 512 // 2
    _, paradas, bloques = _monte_carlo(2048, 0.05, 30, 22)
    assert paradas == 30 and np.median(bloques) <= 256
    assert max(bloques) < 2048 // 2


def test_la_meta_se_escribe_atomica(tmp_path, monkeypatch):
    """m-2: si la escritura muere antes del fsync, la meta vieja queda
    entera; si termina, no queda ningun temporal."""
    ruta = tmp_path / "m.meta.json"
    correr.escribe_atomico(ruta, json.dumps({"a": 1}))
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"a": 1}

    def muere(fd):
        raise OSError("corte simulado")

    monkeypatch.setattr(correr.os, "fsync", muere)
    with pytest.raises(OSError):
        correr.escribe_atomico(ruta, json.dumps({"a": 2, "b": list(range(99))}))
    monkeypatch.undo()
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"a": 1}
    correr.escribe_atomico(ruta, json.dumps({"a": 3}))
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"a": 3}
    assert not (tmp_path / "m.meta.json.tmp").exists()
