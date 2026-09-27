"""Pruebas de `gsa_directo/analizar.py` (T4, apartado 6.6.4 del diseno).

Actividad 4.1. Sobre la funcion de Ishigami (tres entradas activas y tres
mudas, para tener los 14 renglones por bloque del diseno), con fallos
inyectados: descarte por bloques, umbral del 1 %, analisis anidado,
probabilidad de inversion, procedencia e identidades. Y de punta a punta
sobre la corrida FALSA de `correr.py`. Segundos, sin datos.
"""
import csv
import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from gsa_directo import analizar as an, comun, correr  # noqa: E402

PROB = {"num_vars": 6, "names": ["x1", "x2", "x3", "m1", "m2", "m3"],
        "bounds": [[-np.pi, np.pi]] * 6}


def _ishigami(X):
    return (np.sin(X[:, 0]) + 7 * np.sin(X[:, 1]) ** 2
            + 0.1 * X[:, 2] ** 4 * np.sin(X[:, 0]))


def _muestra(n):
    from SALib.sample import sobol as s
    return s.sample(PROB, n, calc_second_order=True, seed=42)


@pytest.fixture(scope="module")
def base256():
    X = _muestra(256)
    Y = {"ishi": _ishigami(X), "P2P_menos_C4": X[:, 0].copy()}
    return X, Y


def _analiza(X, Y, validas=None, presentes=None, base=None):
    M = X.shape[0]
    validas = np.ones(M, bool) if validas is None else validas
    presentes = np.ones(M, bool) if presentes is None else presentes
    return an.analiza(X, Y, validas, presentes, base=base, problema=PROB,
                      salidas=("ishi",), remuestreos=200)


def _st(r, n, x):
    return next(f["ST"] for f in r["filas"] if f["n"] == n
                and f["salida"] == "ishi" and f["entrada"] == x)


def test_ishigami_sin_fallos(base256):
    X, Y = base256
    r = _analiza(X, Y)
    assert r["detenido"] is None and r["n_descartados"] == 0
    assert r["niveles_n"] == [16, 32, 64, 128, 256]
    assert _st(r, 256, "x1") == pytest.approx(0.558, abs=0.08)
    assert _st(r, 256, "x2") == pytest.approx(0.442, abs=0.08)
    assert _st(r, 256, "x3") == pytest.approx(0.244, abs=0.08)
    for m in ("m1", "m2", "m3"):
        assert abs(_st(r, 256, m)) < 1e-12
    assert r["s2"] and {f["n"] for f in r["s2"]} == {256}


def test_anidado_igual_a_la_corrida_pequena(base256):
    """Los indices con los primeros 64 bloques de la muestra de 256 son los
    de una corrida de 64."""
    X, Y = base256
    r = _analiza(X, Y)
    X64 = _muestra(64)
    assert np.array_equal(X64, X[: 64 * comun.B])
    r64 = _analiza(X64, {k: v[: 64 * comun.B] for k, v in Y.items()})
    for x in PROB["names"]:
        assert _st(r, 64, x) == _st(r64, 64, x)


def test_un_fallo_descarta_su_bloque_entero(base256):
    X, Y = base256
    val = np.ones(X.shape[0], bool)
    val[5 * comun.B + 3] = False                  # una fila del bloque 5
    Yn = {k: v.copy() for k, v in Y.items()}
    Yn["ishi"][5 * comun.B + 3] = np.nan
    r = _analiza(X, Yn, validas=val)
    assert r["n_descartados"] == 1 and r["detenido"] is None
    # Igual que analizar a mano sin ese bloque.
    keep = np.ones(X.shape[0], bool)
    keep[5 * comun.B:6 * comun.B] = False
    from SALib.analyze import sobol
    Si = sobol.analyze(PROB, Y["ishi"][keep], calc_second_order=True,
                       num_resamples=200, seed=42)
    assert _st(r, 256, "x1") == pytest.approx(Si["ST"][0], rel=1e-12)


def test_mas_del_uno_por_ciento_detiene(base256):
    X, Y = base256
    val = np.ones(X.shape[0], bool)
    for b in (1, 50, 200):                        # 3/256 = 1,17 %
        val[b * comun.B] = False
    r = _analiza(X, Y, validas=val)
    assert r["detenido"] and "3 de 256" in r["detenido"]
    val[200 * comun.B] = True                     # 2/256 = 0,78 %: sigue
    assert _analiza(X, Y, validas=val)["detenido"] is None


def test_fichero_interrumpido_se_analiza_hasta_su_ultimo_bloque(base256):
    X, Y = base256
    pres = np.ones(X.shape[0], bool)
    pres[100 * comun.B + 7:] = False              # corte a mitad del 100
    r = _analiza(X, Y, validas=pres.copy(), presentes=pres)
    assert r["n_disponible"] == 100 and r["n_descartados"] == 0
    assert r["niveles_n"] == [16, 32, 64]


def test_probabilidad_de_inversion(base256):
    X, Y = base256
    r = _analiza(X, Y, base={"P2P_menos_C4": 1.0})
    f = next(f for f in r["inversion"] if f["salida"] == "P2P_menos_C4")
    # y = x1 uniforme en [-pi, pi] y signo base positivo: la mitad invierte.
    assert f["p_inversion"] == pytest.approx(0.5, abs=0.08)
    assert f["p_inf"] <= f["p_inversion"] <= f["p_sup"]
    assert f["n_filas"] == 2 * 256                # solo las filas A y B


def test_convergencia_informa_por_clase(base256):
    X, Y = base256
    Yb = {"P2P_menos_C4": Y["ishi"], "P2P": 4e7 + Y["ishi"]}
    r = an.analiza(X, Yb, np.ones(X.shape[0], bool),
                   np.ones(X.shape[0], bool), problema=PROB,
                   salidas=("P2P_menos_C4", "P2P"), remuestreos=200)
    clases = {c["clase"] for c in r["convergencia"]}
    assert clases == {"brecha", "nivel"}
    assert all(c["n"] == 256 for c in r["convergencia"])


def test_identidades_duras(base256):
    X, _ = base256
    M = X.shape[0]
    Y = {"P2P": np.full(M, 4e7), "C2": np.full(M, 4e7),
         "retiros": np.zeros(M)}
    ids = an.identidades(Y, np.ones(M, bool), an.pd.DataFrame(
        {"salida": [], "n": []}), [], None)
    assert all(i["cumple"] for i in ids)
    Y["C2"][10] += 1e3
    Y["retiros"][3] = 1
    ids = {i["identidad"]: i for i in an.identidades(
        Y, np.ones(M, bool), an.pd.DataFrame({"salida": [], "n": []}), [],
        None)}
    assert not ids["C2 == P2P (CAL-52)"]["cumple"]
    assert not ids["retiros = 0 (D67)"]["cumple"]


# ── De punta a punta sobre la corrida falsa ─────────────────────────────────
def _corrida_falsa(tmp):
    assert correr.ejecuta(["--caso", "E0", "--n-base", "16", "--procesos",
                           "2", "--verificar", "--salidas", str(tmp)]) == 0
    return tmp / "E0" / "muestras_E0_n16_s42_VERIF.csv"


def _analiza_falsa(tmp):
    return an.ejecuta(["--caso", "E0", "--n-base", "16", "--verificar",
                       "--salidas", str(tmp), "--remuestreos", "100"])


def test_punta_a_punta(tmp_path):
    _corrida_falsa(tmp_path)
    assert _analiza_falsa(tmp_path) == 0
    for f in ("indices_E0.csv", "s2_E0.csv", "inversion_E0.csv",
              "INFORME_E0.md"):
        assert (tmp_path / "E0" / f).exists(), f
    texto = (tmp_path / "E0" / "INFORME_E0.md").read_text(encoding="utf-8")
    assert "NUMEROS FALSOS" in texto and "identidad** (H-70)" in texto


def test_procedencia_detecta_una_entrada_cambiada(tmp_path):
    p = _corrida_falsa(tmp_path)
    with open(p, newline="", encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    filas[4]["f_bolsa"] = "3.9999"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    assert _analiza_falsa(tmp_path) == 2


def test_identidad_rota_detiene(tmp_path):
    p = _corrida_falsa(tmp_path)
    with open(p, newline="", encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    filas[0]["C2"] = str(float(filas[0]["C2"]) + 1e4)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    assert _analiza_falsa(tmp_path) == 1
