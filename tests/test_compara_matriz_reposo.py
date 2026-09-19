"""
La comparacion de la matriz vieja con la nueva (M-F, D48). 2026-09-17.

Prueba `reformateo/documento/scripts/sonda/compara_matriz_reposo.py` con
almacenes sinteticos, sin parquet ni pyarrow.

Las tablas se escriben a mano con el esquema del almacen, y con cifras
redondas, de modo que cada metrica se puede calcular en la cabeza: tres horas
(una con dos compradores, una de un solo comprador con un excluido y una sin
ganancia), cinco instituciones y dos escenarios regulatorios. Se prueba:

  - cada metrica de M-F, de la comunidad y por institucion;
  - que la vieja contra si misma da diferencias cero y ningun cambio de signo;
  - que un orden P2P frente a C_k que cambia de signo se marca, tambien el que
    pasa de empate a un signo, y que el empate respeta la tolerancia;
  - que un almacen de la via acoplada, sin las columnas del reposo, deja vacias
    las metricas solo de la nueva y lo avisa;
  - la linea de ordenes: el CSV con su cabecera «#» y los codigos de salida.

La prueba de solo lectura con E0 de la entrega del 2026-09-15 (la vieja contra
si misma, diferencias cero) se hizo con el Python del sistema, que trae
pyarrow (informe de la tarea 4b).
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

import compara_matriz_reposo as cmp  # noqa: E402

NOMBRES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]


def _horas(con_reposo=True):
    d = pd.DataFrame(dict(
        hora=[0, 1, 2], resuelta=[True, True, False],
        motivo=[None, None, "sin mercado esa hora"],
        regimen=["interiores", "un_comprador", "sin_ganancia"],
        piso_juego=[700.0, 700.0, 900.0],
        excluidos=["", "HUDN", ""], excluidos_bajo_piso=["", "", ""],
        captura=[0.9, 1.0, 0.0], excedente_optimo=[100.0, 50.0, 0.0]))
    if not con_reposo:
        d = d.drop(columns=["regimen", "piso_juego", "excluidos",
                            "excluidos_bajo_piso", "captura",
                            "excedente_optimo"])
    return d


def _flujos():
    filas = [
        # hora, vendedor, comprador, kwh, precio, techo, piso
        (0, "Udenar", "Mariana", 2.0, 750.0, 800.0, 700.0),
        (0, "Udenar", "UCC", 3.0, 800.0, 800.0, 700.0),
        (1, "Cesmag", "Mariana", 1.0, 700.0, 780.0, 700.0),
        (1, "Cesmag", "HUDN", 0.0, 700.0, 690.0, 700.0),
    ]
    return pd.DataFrame([dict(hora=k, vendedor=v, comprador=c, kwh=e,
                              precio=p, valor=e * p, precio_reposo=p,
                              techo_comprador=t, piso_vendedor=s,
                              ahorro_comprador=(t - p) * e,
                              prima_vendedor=(p - s) * e)
                         for k, v, c, e, p, t, s in filas])


def _agentes():
    filas = []
    for k in (0, 1, 2):
        for n in NOMBRES:
            faltante = 4.0 if (k, n) == (1, "HUDN") else 1.0
            filas.append(dict(hora=k, agente=n, faltante=faltante,
                              sobrante=0.0, papel="comprador"))
    return pd.DataFrame(filas)


def _escenarios(valores):
    """valores: {escenario: [beneficio de las cinco, en orden]}, repartido en
    dos horas para que la suma importe."""
    filas = []
    for esc, vals in valores.items():
        for n, v in zip(NOMBRES, vals):
            filas += [dict(hora=0, escenario=esc, agente=n, valor=v * 0.25),
                      dict(hora=1, escenario=esc, agente=n, valor=v * 0.75)]
    return pd.DataFrame(filas)


VIEJOS = {"P2P": [1000.0, 500.0, 200.0, 100.0, 300.0],
          "C2": [900.0, 500.5, 250.0, 100.0, 300.0],
          "P2P_colectivo": [950.0, 480.0, 190.0, 90.0, 290.0],
          "C4": [940.0, 490.0, 180.0, 95.0, 300.0]}
NUEVOS = {"P2P": [850.0, 500.0, 200.0, 100.0, 300.0],
          "C2": [900.0, 480.0, 250.0, 100.0, 300.0],
          "P2P_colectivo": [950.0, 480.0, 190.0, 90.0, 290.0],
          "C4": [940.0, 490.0, 180.0, 95.0, 300.0]}


def _tablas(escenarios=VIEJOS, con_reposo=True):
    return dict(horas=_horas(con_reposo), flujos=_flujos(),
                agentes=_agentes(), escenarios=_escenarios(escenarios))


# ─── las metricas ──────────────────────────────────────────────────────────


def test_las_metricas_de_la_comunidad_y_por_institucion():
    filas, esc, avisos = cmp.metricas(_tablas())
    assert avisos == []
    c = filas.loc[cmp.COMUNIDAD]
    assert c["kwh_transada"] == pytest.approx(6.0)
    assert c["precio_medio"] == pytest.approx(4600.0 / 6.0)
    # excedente 200 + 300 + 80; primas 100 + 300 + 0
    assert c["parte_vendedor"] == pytest.approx(400.0 / 580.0)
    assert c["beneficio_P2P"] == pytest.approx(2100.0)
    assert c["kwh_al_techo"] == pytest.approx(3.0)
    assert c["kwh_al_piso"] == pytest.approx(1.0)
    assert c["kwh_excluida"] == pytest.approx(4.0)
    assert c["kwh_excluida_bajo_piso"] == pytest.approx(0.0)
    assert c["kwh_un_comprador"] == pytest.approx(1.0)
    assert c["captura_media"] == pytest.approx(0.95)
    assert c["captura_agregada"] == pytest.approx(140.0 / 150.0)

    assert filas.loc["Udenar", "kwh_transada"] == pytest.approx(5.0)
    assert filas.loc["Udenar", "precio_medio"] == pytest.approx(780.0)
    assert filas.loc["Udenar", "parte_vendedor"] == pytest.approx(0.8)
    assert filas.loc["Mariana", "kwh_transada"] == pytest.approx(3.0)
    assert filas.loc["Mariana", "precio_medio"] == pytest.approx(2200.0 / 3)
    assert np.isnan(filas.loc["Mariana", "parte_vendedor"])
    assert filas.loc["Cesmag", "parte_vendedor"] == pytest.approx(0.0)
    assert filas.loc["UCC", "kwh_al_techo"] == pytest.approx(3.0)
    assert filas.loc["Mariana", "kwh_al_piso"] == pytest.approx(1.0)
    assert filas.loc["HUDN", "kwh_excluida"] == pytest.approx(4.0)
    assert filas.loc["Cesmag", "kwh_un_comprador"] == pytest.approx(1.0)
    assert filas.loc["Mariana", "kwh_un_comprador"] == pytest.approx(1.0)
    assert filas.loc["HUDN", "kwh_un_comprador"] == pytest.approx(0.0)
    assert np.isnan(filas.loc["Udenar", "captura_media"])
    assert esc["C2"].loc["Mariana"] == pytest.approx(500.5)


def test_un_almacen_sin_columnas_del_reposo_deja_vacio_lo_de_la_nueva():
    filas, _, avisos = cmp.metricas(_tablas(con_reposo=False))
    assert any(a.startswith("NO MEDIDO") for a in avisos)
    assert filas[list(cmp.SOLO_NUEVA)].isna().all().all()
    assert filas.loc[cmp.COMUNIDAD, "kwh_transada"] == pytest.approx(6.0)


# ─── la comparacion ────────────────────────────────────────────────────────


def test_la_vieja_contra_si_misma_da_cero():
    m = cmp.metricas(_tablas())
    t = cmp.compara(m, m, "E0")
    difs = [c for c in t.columns if c.endswith("_dif")]
    assert len(difs) == len(cmp.COMUNES)
    valores = t[difs].to_numpy(dtype=float)
    finitos = valores[np.isfinite(valores)]
    assert finitos.size and np.all(finitos == 0.0)
    cambios = [c for c in t.columns if c.endswith("_cambia_signo")]
    assert set(cambios) == {"P2P_menos_C2_cambia_signo",
                            "P2P_menos_C4_cambia_signo",
                            "P2P_colectivo_menos_C4_cambia_signo"}
    assert set(t[cambios].to_numpy().ravel()) == {"no"}


def test_marca_el_cambio_de_signo_y_el_empate():
    t = cmp.compara(cmp.metricas(_tablas(VIEJOS)),
                    cmp.metricas(_tablas(NUEVOS)), "E0").set_index(
                        "institucion")
    # Udenar: +100 en la vieja, -50 en la nueva.
    assert t.loc["Udenar", "P2P_menos_C2_vieja"] == pytest.approx(100.0)
    assert t.loc["Udenar", "P2P_menos_C2_nueva"] == pytest.approx(-50.0)
    assert t.loc["Udenar", "P2P_menos_C2_signo"] == "+ -> -"
    assert t.loc["Udenar", "P2P_menos_C2_cambia_signo"] == "si"
    # Mariana: -0,5 (COP) es empate con la tolerancia de 1 (COP); +20 despues.
    assert t.loc["Mariana", "P2P_menos_C2_signo"] == "0 -> +"
    assert t.loc["Mariana", "P2P_menos_C2_cambia_signo"] == "si"
    # UCC no cambia; el colectivo frente a C4 tampoco.
    assert t.loc["UCC", "P2P_menos_C2_cambia_signo"] == "no"
    assert set(t["P2P_colectivo_menos_C4_cambia_signo"]) == {"no"}
    # La comunidad: 2 100 frente a 2 050,5 en la vieja (+49,5) y 1 950 frente
    # a 2 030 en la nueva (-80).
    assert t.loc[cmp.COMUNIDAD, "P2P_menos_C2_vieja"] == pytest.approx(49.5)
    assert t.loc[cmp.COMUNIDAD, "P2P_menos_C2_signo"] == "+ -> -"
    assert t.loc[cmp.COMUNIDAD, "beneficio_P2P_dif"] == pytest.approx(-150.0)


def test_el_empate_obedece_a_la_tolerancia():
    v, n = cmp.metricas(_tablas(VIEJOS)), cmp.metricas(_tablas(NUEVOS))
    t = cmp.compara(v, n, "E0", tol_cop=0.1).set_index("institucion")
    assert t.loc["Mariana", "P2P_menos_C2_signo"] == "- -> +"


def test_al_techo_con_la_tolerancia_de_d48():
    # 1e-6 (COP/kWh) absoluta, la de `resumen_reposo`: medio millonesimo por
    # debajo del techo cuenta al techo; dos millonesimos, no.
    t = _tablas()
    fl = t["flujos"]
    m = (fl["hora"] == 0) & (fl["comprador"] == "UCC")
    fl.loc[m, "precio"] = 800.0 - 5e-7
    assert cmp.metricas(t)[0].loc["UCC", "kwh_al_techo"] == pytest.approx(3.0)
    fl.loc[m, "precio"] = 800.0 - 2e-6
    assert cmp.metricas(t)[0].loc["UCC", "kwh_al_techo"] == pytest.approx(0.0)
    assert cmp.TOL_PRECIO_D48 == 1e-6


def test_instituciones_en_distinto_orden_se_alinean_por_nombre():
    v = _tablas(VIEJOS)
    n = _tablas(NUEVOS)
    orden = ["Cesmag", "HUDN", "UCC", "Mariana", "Udenar"]
    n["agentes"] = (n["agentes"].set_index("agente").loc[orden]
                    .reset_index())
    n["escenarios"] = (n["escenarios"].set_index("agente").loc[orden]
                       .reset_index())
    t = cmp.compara(cmp.metricas(v), cmp.metricas(n), "E0").set_index(
        "institucion")
    assert list(t.index[1:]) == orden
    assert t.loc["Udenar", "P2P_menos_C2_signo"] == "+ -> -"
    assert t.loc["Mariana", "P2P_menos_C2_signo"] == "0 -> +"
    assert t.loc["Udenar", "beneficio_P2P_vieja"] == pytest.approx(1000.0)
    assert t.loc["Udenar", "beneficio_P2P_nueva"] == pytest.approx(850.0)
    assert t.loc["Udenar", "kwh_transada_dif"] == pytest.approx(0.0)


# ─── no finitos (revision de 4b, importante 1) ─────────────────────────────


@pytest.mark.parametrize("tabla,columna,fila", [
    ("flujos", "kwh", 0),
    ("flujos", "techo_comprador", 1),
    ("agentes", "faltante", 3),
    ("escenarios", "valor", 5),
    ("horas", "captura", 0),
    ("horas", "excedente_optimo", 1),
])
def test_un_no_finito_se_rechaza(tabla, columna, fila):
    t = _tablas()
    t[tabla].loc[fila, columna] = np.nan if fila % 2 else np.inf
    with pytest.raises(cmp.DatosNoFinitos, match=columna):
        cmp.metricas(t)


def test_un_no_finito_en_una_hora_sin_regimen_no_cuenta():
    # En las horas sin vendedores o sin compradores el almacen deja la captura
    # vacia: no es un dato, y no se rechaza.
    t = _tablas()
    t["horas"].loc[2, "regimen"] = None
    t["horas"].loc[2, "captura"] = np.nan
    cmp.metricas(t)


def test_main_sale_con_2_con_un_no_finito(tmp_path, monkeypatch, capsys):
    vieja, nueva = _raices(tmp_path, ["E0"], ["E0"])

    def carga(raiz, caso, cobertura="m1", sufijo=""):
        t = _tablas()
        if Path(raiz) == nueva:
            t["escenarios"].loc[0, "valor"] = np.nan
        return t

    monkeypatch.setattr(cmp, "carga", carga)
    assert cmp.main(["--vieja", str(vieja), "--nueva", str(nueva),
                     "--salida", str(tmp_path / "c.csv")]) == 2
    assert "NO SE PUEDE COMPARAR E0" in capsys.readouterr().out
    assert not (tmp_path / "c.csv").exists()


def test_un_escenario_que_falta_en_un_lado_no_es_comparable():
    sin_c4 = {k: v for k, v in NUEVOS.items() if k != "C4"}
    t = cmp.compara(cmp.metricas(_tablas(VIEJOS)),
                    cmp.metricas(_tablas(sin_c4)), "E0")
    assert set(t["P2P_menos_C4_cambia_signo"]) == {"no comparable"}


# ─── la linea de ordenes ───────────────────────────────────────────────────


def _raices(tmp_path, casos_viejos, casos_nuevos, sufijo_nueva=""):
    vieja, nueva = tmp_path / "matriz", tmp_path / "matriz_reposo"
    for c in casos_viejos:
        (vieja / c / "almacen" / "m1").mkdir(parents=True)
    for c in casos_nuevos:
        (nueva / f"{c}{sufijo_nueva}" / "almacen" / "m1").mkdir(parents=True)
    return vieja, nueva


def test_main_escribe_el_csv_con_su_cabecera(tmp_path, monkeypatch, capsys):
    vieja, nueva = _raices(tmp_path, ["E0", "K1"], ["E0", "K1", "P1"])

    def carga(raiz, caso, cobertura="m1", sufijo=""):
        return _tablas(VIEJOS if Path(raiz) == vieja else NUEVOS)

    monkeypatch.setattr(cmp, "carga", carga)
    salida = tmp_path / "sal" / "compara.csv"
    assert cmp.main(["--vieja", str(vieja), "--nueva", str(nueva),
                     "--salida", str(salida)]) == 0
    texto = capsys.readouterr().out
    assert "sin almacen en la vieja, no se comparan: ['P1']" in texto
    assert "CAMBIOS DE SIGNO" in texto
    assert "M-H" in texto
    assert salida.read_text(encoding="utf-8").startswith("# vieja=")
    t = pd.read_csv(salida, comment="#")
    assert sorted(set(t["caso"])) == ["E0", "K1"]
    assert len(t) == 2 * (1 + len(NOMBRES))


def test_sin_sufijo_el_barrido_y_las_figuras_no_son_candidatas(
        tmp_path, monkeypatch, capsys):
    vieja, nueva = _raices(tmp_path, ["E0"], ["E0", "E0_sigma05",
                                              "E0_sigma1"])
    (nueva / "figuras_foro").mkdir()
    monkeypatch.setattr(cmp, "carga",
                        lambda raiz, caso, cobertura="m1", sufijo="": _tablas())
    assert cmp.main(["--vieja", str(vieja), "--nueva", str(nueva),
                     "--salida", str(tmp_path / "c.csv")]) == 0
    texto = capsys.readouterr().out
    assert "sin almacen en la vieja" not in texto
    t = pd.read_csv(tmp_path / "c.csv", comment="#")
    assert sorted(set(t["caso"])) == ["E0"]


def test_main_con_sufijo_del_barrido(tmp_path, monkeypatch):
    vieja, nueva = _raices(tmp_path, ["E0"], ["E0"], sufijo_nueva="_sigma05")
    pedidos = []

    def carga(raiz, caso, cobertura="m1", sufijo=""):
        pedidos.append((Path(raiz).name, caso, sufijo))
        return _tablas()

    monkeypatch.setattr(cmp, "carga", carga)
    assert cmp.main(["--vieja", str(vieja), "--nueva", str(nueva),
                     "--sufijo-nueva", "_sigma05", "--casos", "E0",
                     "--salida", str(tmp_path / "c.csv")]) == 0
    assert ("matriz_reposo", "E0", "_sigma05") in pedidos
    assert ("matriz", "E0", "") in pedidos


def test_main_sale_con_2_si_falta_un_caso_pedido(tmp_path, capsys):
    vieja, nueva = _raices(tmp_path, ["E0"], ["E0", "K1"])
    assert cmp.main(["--vieja", str(vieja), "--nueva", str(nueva),
                     "--casos", "E0", "K1",
                     "--salida", str(tmp_path / "c.csv")]) == 2
    assert "FALTA el almacen de: K1 (vieja)" in capsys.readouterr().out
    assert not (tmp_path / "c.csv").exists()


def test_main_sale_con_2_sin_casos(tmp_path):
    vieja, nueva = _raices(tmp_path, [], [])
    assert cmp.main(["--vieja", str(vieja), "--nueva", str(nueva),
                     "--salida", str(tmp_path / "c.csv")]) == 2


# ─── D71: hora a hora (tarea Q) ────────────────────────────────────────────


def _con_entradas(t, techo=800.0, piso=700.0):
    """Las tablas de `_tablas` con el techo y el piso de cada agente, que
    `horas_distintas` compara como entradas de la hora."""
    t = {k: v.copy() for k, v in t.items()}
    t["agentes"] = t["agentes"].assign(techo=techo, piso=piso)
    return t


def test_por_hora_la_vieja_contra_si_misma_no_difiere():
    t = _con_entradas(_tablas())
    entradas, mercado = cmp.horas_distintas(t, _con_entradas(_tablas()))
    assert entradas.empty and mercado.empty


def test_por_hora_el_reparto_cuantal_de_una_hora_se_ve_con_su_energia():
    vieja = _con_entradas(_tablas())
    nueva = _con_entradas(_tablas())
    # La hora 0 pasa a «cuantal»: UCC cede 0,5 (kWh) a Mariana.
    h, fl = nueva["horas"], nueva["flujos"]
    h.loc[h["hora"] == 0, "regimen"] = "cuantal"
    fl.loc[(fl["hora"] == 0) & (fl["comprador"] == "Mariana"), "kwh"] += 0.5
    fl.loc[(fl["hora"] == 0) & (fl["comprador"] == "UCC"), "kwh"] -= 0.5
    entradas, mercado = cmp.horas_distintas(vieja, nueva)
    assert entradas.empty
    assert mercado["hora"].tolist() == [0]
    fila = mercado.iloc[0]
    assert (fila["regimen_vieja"], fila["regimen_nueva"]) == ("interiores",
                                                              "cuantal")
    assert fila["max_dif_kwh"] == pytest.approx(0.5)
    assert fila["kwh_movida"] == pytest.approx(0.5)


def test_por_hora_es_al_bit_salvo_con_tolerancia():
    vieja = _con_entradas(_tablas())
    nueva = _con_entradas(_tablas())
    fl = nueva["flujos"]
    fl.loc[(fl["hora"] == 1) & (fl["comprador"] == "Mariana"), "kwh"] += 1e-7
    assert cmp.horas_distintas(vieja, nueva)[1]["hora"].tolist() == [1]
    assert cmp.horas_distintas(vieja, nueva, tol_kwh=1e-6)[1].empty
    # Una pareja que solo esta en un lado cuenta con cero.
    nueva["flujos"] = pd.concat([fl, fl[fl["hora"] == 0].iloc[[0]].assign(
        comprador="HUDN", kwh=0.25)], ignore_index=True)
    assert 0 in cmp.horas_distintas(vieja, nueva, 1e-6)[1]["hora"].tolist()


def test_por_hora_una_hora_con_otras_entradas_va_aparte():
    """La cache nueva de bolsa (H-92) cambia el piso de los vendedores de
    bolsa: esa hora no se compara por D71, aunque su mercado cambie."""
    vieja = _con_entradas(_tablas())
    nueva = _con_entradas(_tablas())
    ag, fl = nueva["agentes"], nueva["flujos"]
    ag.loc[(ag["hora"] == 1) & (ag["agente"] == "Cesmag"), "piso"] = 650.0
    fl.loc[fl["hora"] == 1, "kwh"] *= 0.5
    entradas, mercado = cmp.horas_distintas(vieja, nueva)
    assert entradas["hora"].tolist() == [1]
    assert entradas["max_dif"].iloc[0] == pytest.approx(50.0)
    assert mercado.empty
    # Un agente que falta en un lado tambien es otra entrada.
    nueva["agentes"] = ag[~((ag["hora"] == 2) & (ag["agente"] == "UCC"))]
    assert cmp.horas_distintas(vieja, nueva)[0]["hora"].tolist() == [1, 2]


def test_main_por_hora_escribe_la_lista(tmp_path, monkeypatch, capsys):
    vieja, nueva = _raices(tmp_path, ["E0"], ["E0"])

    def carga(raiz, caso, cobertura="m1", sufijo=""):
        t = _con_entradas(_tablas())
        if Path(raiz) == nueva:
            t["horas"].loc[t["horas"]["hora"] == 0, "regimen"] = "cuantal"
        return t

    monkeypatch.setattr(cmp, "carga", carga)
    salida = tmp_path / "compara.csv"
    assert cmp.main(["--vieja", str(vieja), "--nueva", str(nueva),
                     "--salida", str(salida), "--por-hora"]) == 0
    texto = capsys.readouterr().out
    assert ("E0, hora a hora (D71): 0 horas con entradas distintas (no se "
            "comparan); 1 con las mismas entradas y el mercado distinto") \
        in texto
    assert "interiores -> cuantal" in texto
    lista = pd.read_csv(tmp_path / "compara_horas.csv")
    assert lista["hora"].tolist() == [0] and lista["que"].tolist() == [
        "mercado"]
