"""Pruebas de las compuertas del GSA directo (T5 y T6): el punto base contra
un canon SINTETICO, la replica y el desplazamiento de la bolsa de 2024.

Actividad 4.1. Segundos; la de la bolsa de 2024 lee un CSV de `data/`.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from gsa_directo import comun, compuerta_punto_base as cpb  # noqa: E402
from gsa_directo import deterministas, evaluador, replica  # noqa: E402

NOMBRES = comun.INSTITUCIONES
BENEFICIO = {"P2P": 46495474.04465938, "P2P_colectivo": 44475558.72824585,
             "C1": 46199822.48397852, "C2": 46495474.04465939,
             "C3": 42773224.39266975, "C4": 44486055.30044089,
             "C4_mensual": 44486055.30044089, "C5": 44261386.19389968}


def _canon_sintetico(carpeta: Path, cuantal: int = 57) -> Path:
    """Un caso con la estructura de la matriz: libro, CSV de flujos y un
    almacen con sus tablas de flujos y horas en Parquet."""
    out = carpeta / "outputs"
    out.mkdir(parents=True)
    pa = pd.DataFrame({"Agente": [f"A{i + 1}" for i in range(5)],
                       **{e: np.full(5, v / 5) for e, v in BENEFICIO.items()}})
    with pd.ExcelWriter(out / "resultados_comparacion.xlsx") as w:
        pd.DataFrame({"Escenario": list(BENEFICIO),
                      "Ganancia_neta_COP": list(BENEFICIO.values())}
                     ).to_excel(w, sheet_name="Resumen", index=False)
        pa.to_excel(w, sheet_name="Por_agente", index=False)
    pd.DataFrame({"kWh_transados": [2000.0, 2592.019]}).to_csv(
        out / "p2p_breakdown_flujos.csv", index=False)
    for tabla, df in (
            ("flujos", pd.DataFrame({"kwh": [2000.0, 2592.019],
                                     "prima_vendedor": [100.0, 60.0],
                                     "ahorro_comprador": [80.0, 55.0]})),
            ("horas", pd.DataFrame({"hora": np.arange(cuantal + 3),
                                    "regimen": ["cuantal"] * cuantal
                                    + ["topados"] * 3}))):
        d = carpeta / "almacen" / "m1" / tabla
        d.mkdir(parents=True)
        df.to_parquet(d / "parte_0000.parquet")
    return carpeta


def _registro(carpeta: Path, cuantal: int = 57) -> Path:
    reg = carpeta / "logs"
    reg.mkdir()
    (reg / "matriz_reposo_compuerta_E0_2026-09-19_1720.log").write_text(
        f"  Horas «cuantal» (D71): {cuantal}; con n_soluciones distinto de 1: "
        f"0\n", encoding="utf-8")
    return reg


def _lee(tmp_path: Path, **kw) -> dict:
    """El canon sintetico con su registro D71: todas las comprobaciones con
    referencia."""
    return cpb.lee_canon(_canon_sintetico(tmp_path / "E0", **kw), NOMBRES,
                         _registro(tmp_path), "E0")


def _evaluado():
    out = {k: BENEFICIO[k] for k in ("P2P", "P2P_colectivo", "C1", "C2",
                                     "C3", "C4", "C5")}
    out.update(energia=4592.019, parte_vendedor=160 / 295, n_cuantal=57.0,
               retiros=0.0)
    pa = {e: np.full(5, v / 5) for e, v in BENEFICIO.items()}
    return out, pa, dict(BENEFICIO)


def test_canon_sintetico_al_peso(tmp_path):
    canon = _lee(tmp_path)
    out, pa, net = _evaluado()
    filas = cpb.compara("E0", out, pa, net, canon, NOMBRES)
    assert filas and all(f[6] for f in filas)


def test_h1_de_la_comunidad_al_peso(tmp_path):
    """2026-10-04: con `h1_canon`, H1 de la comunidad se compara a un peso
    (CANON §14.26); sin el (el contraste de f_cv = 2) no se compara. Los
    trece casos tienen su valor en H1_CANON."""
    canon = _lee(tmp_path)
    out, pa, net = _evaluado()
    out["H1"] = cpb.H1_CANON["E0"] + 0.9
    filas = cpb.compara("E0", out, pa, net, canon, NOMBRES,
                        h1_canon=cpb.H1_CANON["E0"])
    assert all(f[6] for f in filas) and any(f[1].startswith("H1") for f in filas)
    out["H1"] = cpb.H1_CANON["E0"] + 1.1
    malas = [f for f in cpb.compara("E0", out, pa, net, canon, NOMBRES,
                                    h1_canon=cpb.H1_CANON["E0"]) if not f[6]]
    assert len(malas) == 1 and malas[0][1].startswith("H1")
    assert not any(f[1].startswith("H1")
                   for f in cpb.compara("E0", out, pa, net, canon, NOMBRES))
    assert set(cpb.H1_CANON) == set(comun.CASOS)


@pytest.mark.parametrize("donde", ["Resumen", "Por_agente"])
def test_un_peso_de_diferencia_se_detecta(tmp_path, donde):
    canon = _lee(tmp_path)
    out, pa, net = _evaluado()
    if donde == "Resumen":
        net["C4"] += 1.0
    else:
        pa["C1"][2] += 1.0
    malas = [f for f in cpb.compara("E0", out, pa, net, canon, NOMBRES)
             if not f[6]]
    assert len(malas) == 1 and malas[0][1].startswith(donde)


def test_cuantales_retiros_parte_y_energia(tmp_path):
    canon = _lee(tmp_path)
    for campo, valor in (("n_cuantal", 56.0), ("retiros", 1.0),
                         ("parte_vendedor", 160 / 295 + 1e-3),
                         ("energia", 4592.019 + 0.02)):
        out, pa, net = _evaluado()
        out[campo] = valor
        assert not all(f[6] for f in cpb.compara("E0", out, pa, net, canon,
                                                  NOMBRES)), campo


def test_registro_de_la_compuerta_de_salida(tmp_path):
    reg = tmp_path / "logs"
    reg.mkdir()
    (reg / "matriz_reposo_compuerta_E0_2026-09-19_1720.log").write_text(
        "  Horas «cuantal» (D71): 57; con n_soluciones distinto de 1: 0\n",
        encoding="utf-8")
    canon = cpb.lee_canon(_canon_sintetico(tmp_path / "E0"), NOMBRES, reg,
                          "E0")
    assert canon["cuantal_reg"] == 57


def test_sin_referencia_no_se_omite_en_silencio(tmp_path):
    """M-7: sin el registro D71 (o sin una columna de Por_agente) la
    comprobacion no desaparece: cuenta como diferencia, salvo que se pida
    expresamente omitirla, y entonces pasa marcada."""
    canon = cpb.lee_canon(_canon_sintetico(tmp_path / "E0"), NOMBRES)
    assert canon["cuantal_reg"] is None
    out, pa, net = _evaluado()
    malas = [f for f in cpb.compara("E0", out, pa, net, canon, NOMBRES)
             if not f[6]]
    assert len(malas) == 1
    assert malas[0][1] == "horas cuantales (registro D71)" + cpb.SIN_REFERENCIA
    filas = cpb.compara("E0", out, pa, net, canon, NOMBRES,
                        permite_omitir=True)
    assert all(f[6] for f in filas)
    assert sum(f[1].endswith(cpb.SIN_REFERENCIA) for f in filas) == 1
    # Una columna que falta en Por_agente, igual.
    canon = _lee(tmp_path / "otro")
    canon["por_agente"]["C4_mensual"] = None
    malas = [f for f in cpb.compara("E0", out, pa, net, canon, NOMBRES)
             if not f[6]]
    assert [f[1] for f in malas] == ["Por_agente C4_mensual"
                                     + cpb.SIN_REFERENCIA]


def test_huellas_del_canon_iguales_a_las_de_huellas_csv():
    """M-8: las huellas embebidas son las de Documentos/canon_2026-09 (que
    no viaja al servidor). Se salta donde Documentos/ no esta."""
    huellas = RAIZ / "Documentos" / "canon_2026-09" / "HUELLAS.csv"
    if not huellas.exists():
        pytest.skip("sin Documentos/canon_2026-09/HUELLAS.csv")
    h = pd.read_csv(huellas)
    h = h[h.ruta.str.endswith("/outputs/resultados_comparacion.xlsx")
          & h.ruta.str.startswith("SALIDAS_SERVIDOR/matriz_reposo/")]
    leidas = {r.split("/")[2]: s for r, s in zip(h.ruta, h.sha256)}
    assert leidas == cpb.HUELLAS_CANON
    assert set(cpb.HUELLAS_CANON) == set(comun.CASOS)


def test_la_compuerta_exige_la_matriz_y_rechaza_una_ajena(tmp_path, capsys):
    """M-8: sin --matriz no arranca; con una matriz que no es la del canon,
    para con 2 antes de evaluar nada."""
    with pytest.raises(SystemExit):
        cpb.ejecuta(["--casos", "E0", "--sin-escribir"])
    _canon_sintetico(tmp_path / "E0")
    rc = cpb.ejecuta(["--matriz", str(tmp_path), "--casos", "E0",
                      "--sin-contraste", "--sin-escribir"])
    assert rc == 2
    assert "NO ES LA DEL CANON" in capsys.readouterr().out


def test_canon_que_falta(tmp_path):
    with pytest.raises(cpb.CanonIlegible):
        cpb.lee_canon(tmp_path / "no_esta", NOMBRES)


# ── Replica ─────────────────────────────────────────────────────────────────
def test_ocho_puntos():
    p = replica.puntos()
    assert len(p) == 8 and p[0][0] == "base"
    assert np.array_equal(p[-1][1], [s[1] for s in comun.SOPORTES])


def test_replica_detecta_una_salida_cambiada():
    y = {"P2P": 1.0, "C1": 2.0}
    assert replica.compara(y, dict(y), "", "", False)["cumple"]
    z = dict(y, C1=2.0 + 1e-12)
    assert not replica.compara(y, z, "", "", False)["cumple"]
    assert replica.compara(y, z, "", "", True)["cumple"]      # cuantal
    assert not replica.compara(y, dict(y, C1=2.1), "", "", True)["cumple"]
    assert replica.compara(None, None, "ValueError: a", "ValueError: a",
                           False)["cumple"]
    assert not replica.compara(y, None, "", "ValueError: a", False)["cumple"]


# ── La bolsa de 2024 desplazada (T6) ────────────────────────────────────────
def test_bolsa_2024_desplazada_un_dia():
    from data.xm_prices import load_xm_prices
    s = deterministas.bolsa_2024_desplazada(24)
    ref = load_xm_prices(str(deterministas.CSV_2024), "2024-04-04",
                         "2024-04-05", estricto=True)
    np.testing.assert_array_equal(s, ref)
    # El techo es el PES de 2025 (el t0 del caso), no el de 2024 (la
    # 101 066 no regia en abril de 2024 y no recortaria nada).
    pes = float(evaluador.aplica_bolsa(np.array([1e9]), 1.0, "2025-04-04")[0])
    con_techo = evaluador.aplica_bolsa(s, 1.0, "2025-04-04")
    np.testing.assert_array_equal(con_techo, np.minimum(s, pes))
    assert np.array_equal(evaluador.aplica_bolsa(s, 1.0, "2024-04-04"), s)


def test_bolsa_2024_cubre_el_horizonte():
    s = deterministas.bolsa_2024_desplazada(6144)
    assert s.shape == (6144,) and np.all(np.isfinite(s))
    # De El Nino: la media de la ventana es 705,7 (COP/kWh), apartado 5.3.
    assert s.mean() == pytest.approx(705.7, abs=0.5)



def test_el_registro_d71_es_el_del_canon_y_no_el_ultimo(tmp_path):
    """m-3: la compuerta toma el registro de la matriz del 19 de septiembre,
    no el ultimo por nombre."""
    reg = tmp_path / "logs"
    reg.mkdir()
    for nombre, n in (("matriz_reposo_compuerta_E0_2026-09-19_1720.log", 57),
                      ("matriz_reposo_compuerta_E0_2026-10-01_0100.log", 99)):
        (reg / nombre).write_text(
            f"  Horas «cuantal» (D71): {n}; con n_soluciones distinto de 1: 0",
            encoding="utf-8")
    # Sin canon fijo (canon sintetico): el unico de la fecha del canon.
    canon = cpb.lee_canon(_canon_sintetico(tmp_path / "E0"), NOMBRES, reg,
                          "E0")
    assert canon["cuantal_reg"] == 57
    # Con canon fijo: el del canon por nombre y huella; este no lo es.
    ruta, nota = cpb.elige_registro(reg, "E0", canon_fijo=True)
    assert ruta is None and "no esta" in nota
    (reg / cpb.REGISTROS_CANON["E0"][0]).write_text("otro", encoding="utf-8")
    ruta, nota = cpb.elige_registro(reg, "E0", canon_fijo=True)
    assert ruta is None and "huella" in nota
    # Dos de la fecha del canon sin canon fijo: ambiguo, ninguno.
    (reg / "matriz_reposo_compuerta_E0_2026-09-19_2359.log").write_text(
        "x", encoding="utf-8")
    ruta, nota = cpb.elige_registro(reg, "E0", canon_fijo=False)
    assert ruta is None and "ambiguo" in nota


def test_los_registros_del_canon_estan_en_la_entrega():
    """m-3: donde esta la entrega del 19, los trece registros del canon se
    hallan por nombre y huella."""
    reg = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
           / "modelo_base" / "logs")
    if not reg.is_dir():
        pytest.skip("sin la entrega del 19 de septiembre")
    for caso in comun.CASOS:
        ruta, nota = cpb.elige_registro(reg, caso, canon_fijo=True)
        assert ruta is not None, (caso, nota)
