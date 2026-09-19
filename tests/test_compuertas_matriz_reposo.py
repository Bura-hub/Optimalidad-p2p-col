"""
La compuerta de salida de la matriz con el reposo (D48 a D69; M-F). 2026-09-17.

Prueba `reformateo/documento/scripts/sonda/compuertas_matriz_reposo.py` sobre un
almacen sintetico, sin datos reales y sin parquet.

EL ALMACEN SINTETICO se escribe con la clase de produccion,
`core.almacen.Almacen`, y con las mismas llamadas y argumentos con que
`main_simulation.py` lo llena por la via por reposo: la tabla de agentes con
los papeles y los retirados, la de horas con las columnas del reposo, y la de
flujos con el techo, el piso y el precio del reposo. Cada hora se resuelve con
el nucleo (`core.reposo_mercado.resuelve_reposo`) y la participacion de los
vendedores (C-151) se emula como la hace el motor: el vendedor cuyo ingreso
medio queda bajo su piso se retira, el conjunto reducido se vuelve a resolver
y su fila queda en cero. No se usa el motor (`core/ems_p2p.py`), que otra
tarea edita en paralelo; el esquema del almacen no cambia en esa ronda.

El volcado a parquet se sustituye por uno en memoria que CONSERVA LA CONVERSION
A float32 de `Almacen._vuelca`: la compuerta tiene que pasar en verde con los
redondeos de precision sencilla, que es como llegan los almacenes del
servidor. `.venv` no trae pyarrow; el almacen en parquet de verdad se comprobo
aparte con el Python del sistema (informe de la tarea 4b).

Las horas cubren los regimenes interiores, excluidos, compradores cortos, un
comprador, topados con cifras grandes y decimales arbitrarios, sin ganancia, una
hora sin vendedores ni compradores, un vendedor excluido por D61, un comprador
excluido bajo el piso, dos vendedores de pisos distintos (con renta
inframarginal) y un vendedor que la caminata competitiva deja sin despachar
(D65). Despues se rompe a proposito cada identidad y se comprueba que la
compuerta falla con su mensaje.

TAREA Q (D71). La hora 14 es FRAGIL (la familia de la hora 12 de E0): el
nucleo la publica «cuantal», con Mariana y UCC recibiendo su parte, y la
compuerta la acepta en verde. La identidad nueva `cuantal` (regimen «cuantal»
si y solo si el apartamiento pasa de 1e-3) se rompe a proposito en sus cinco
formas; las tres columnas de D71 son exigidas.

TAREA 5A (D63 a D69). Con el piso del vendedor marginal la participacion no
retira a nadie: la hora 8, que antes retiraba a Mariana (cobraba 750 con piso
760), ahora la despacha a 780 con los dos compradores. El almacen en verde no
tiene retiros, y la identidad `cero_retiros` lo exige. El retiro se prueba en
un almacen aparte (`tablas_con_retiro`), con una hora cuyo retiro se FUERZA
como lo anotaria el motor si la participacion retirara a alguien: es el caso
que la compuerta tiene que detener.
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

import compuertas_matriz_reposo as cm  # noqa: E402
import core.almacen as almacen_mod  # noqa: E402
from core.market_prep import classify_agents  # noqa: E402
from core.reposo_mercado import (captura, cotas_optimalidad,  # noqa: E402
                                 resuelve_reposo)

NOMBRES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
# Costos lineales sinteticos, con Cesmag el mas barato. Con datos reales el
# motor recibe 225 (COP/kWh) para Cesmag y 241,07 para las demas, tras el ajuste
# por irradiancia de data/xm_prices.py (H-89); 210 y 225 son los de la tabla de
# calibracion, antes del ajuste.
B = np.array([225.0, 225.0, 225.0, 225.0, 210.0])
SIN_MERCADO = ("sin_mercado", "sin_ganancia")

# hora: (generacion, demanda, techo, piso) de las cinco instituciones.
HORAS = {
    # interiores: un vendedor, tres compradores, bandas iguales
    0: ([20, 0, 0, 0, 3], [5, 6, 7, 8, 3], [800] * 5, [700] * 5),
    # excluidos: Mariana, con el techo mas bajo, queda sin energia
    1: ([12, 0, 0, 0, 2], [2, 6, 6, 6, 2], [800, 780, 800, 900, 800],
        [700] * 5),
    # compradores cortos con orden de merito (Cesmag primero)
    2: ([12, 0, 0, 1, 10], [2, 5, 4, 1, 2], [800] * 5,
        [700, 700, 700, 700, 690]),
    # HUDN excluido bajo el piso (D61 parcial)
    3: ([20, 0, 0, 0, 3], [5, 6, 7, 8, 3], [800, 800, 800, 650, 800],
        [700] * 5),
    # Cesmag excluido como vendedor sin ganancia posible (D61)
    4: ([12, 0, 0, 1, 7], [2, 8, 9, 1, 2], [800] * 5,
        [700, 700, 700, 700, 900]),
    # sin ganancia: el piso del unico vendedor supera todos los techos
    5: ([12, 0, 1, 1, 1], [2, 8, 1, 1, 1], [800] * 5, [900] * 5),
    # sin compradores: la hora no llega al nucleo
    6: ([5, 5, 5, 5, 5], [1, 1, 1, 1, 1], [800] * 5, [700] * 5),
    # un comprador (D54)
    7: ([12, 0, 2, 2, 2], [2, 4, 2, 2, 2], [800] * 5, [700] * 5),
    # dos vendedores de pisos 700 y 760, vendedores cortos. Con D62 cobraban
    # 750 y Mariana (piso 760) se retiraba; con D63 el piso del juego es 760 y
    # los dos cobran 780: renta inframarginal 600 y parte del juego 400 (COP)
    8: ([12, 12, 0, 0, 3], [2, 2, 15, 15, 3], [800] * 5,
        [700, 760, 700, 700, 700]),
    # dos vendedores de pisos 700 y 720 que cobran 773,33 (COP/kWh)
    9: ([12, 8, 0, 0, 0], [2, 2, 7, 8, 9], [800] * 5,
        [700, 720, 700, 700, 700]),
    # topados, con cientos de kWh y decimales arbitrarios (float32)
    10: ([905.123, 0, 0, 0, 461.77], [5.123, 700.5, 500.25, 400.125, 11.77],
         [800, 812.345, 799.99, 923.21, 800],
         [612.3456, 600, 600, 600, 598.76]),
    # D65: Udenar (3 (kWh), piso 600) y Mariana (10 (kWh), piso 750); UCC
    # (2, techo 800) y HUDN (3, techo 700). Al nivel 600 el volumen es 3; al
    # nivel 750, min(13; 2) = 2. Cierra en 600: vende Udenar y Mariana queda
    # no despachada, fuera de la oferta (sin descontarla, E daria 5)
    12: ([4, 12, 0, 0, 3], [1, 2, 2, 3, 3], [800, 800, 800, 700, 800],
         [600, 750, 600, 600, 600]),
    # D71, una hora FRAGIL, la familia de la hora 12 de E0 con la tarifa de
    # abril: vende Udenar 10 (kWh) con piso 695,68; Mariana y UCC compran en
    # su techo de 734,30 y Cesmag, con 12 (kWh) de deficit, queda interior a
    # 1,59 (COP/kWh) por encima. La forma cerrada la da toda a Cesmag
    # («excluidos»); la rama cuantal le da a Mariana y a UCC su parte.
    14: ([12, 0, 0, 1, 0], [2, 6, 7, 1, 12], [800, 734.30, 734.30, 800, 794.62],
         [695.68] * 5),
}
# La hora con un retiro FORZADO (D67): la de la hora 8 con Mariana retirada,
# como la anotaria el motor si la participacion la retirara. Solo va en el
# almacen de `tablas_con_retiro`.
HORA_RETIRO = 11
# Y la hora que PIERDE EL MERCADO tras el retiro (revision final, importante
# 2): retirado Udenar, el unico que queda es Mariana, con el piso 900 sobre
# el techo de todos: la hora queda sin mercado, sin resolver, pero con su
# retirado anotado, y `cero_retiros` tiene que verlo igual.
HORA_RETIRO_SIN_MERCADO = 13
RETIRO = {HORA_RETIRO: ([12, 12, 0, 0, 3], [2, 2, 15, 15, 3], [800] * 5,
                        [700, 760, 700, 700, 700]),
          HORA_RETIRO_SIN_MERCADO: ([12, 12, 0, 0, 3], [2, 2, 15, 15, 3],
                                    [800] * 5, [700, 900, 700, 700, 700])}
RETIRADOS_FORZADOS = {HORA_RETIRO: [1], HORA_RETIRO_SIN_MERCADO: [0]}


# ─── el almacen sintetico ──────────────────────────────────────────────────


def _resuelve(G, D, techo, piso, forzados=()):
    """La hora como el motor: nucleo y participacion (C-151). `forzados`
    retira de entrada a esos vendedores, para escribir la hora que la
    compuerta de cero retiros (D67) tiene que detener."""
    _, sids, bids = classify_agents(G, D)
    if not sids or not bids:
        return sids, bids, None, [], []
    d = np.array([D[i] - G[i] for i in bids])
    quedan = [j for j in sids if j not in forzados]
    retirados = [j for j in sids if j in forzados]
    while True:
        s = np.array([G[j] - D[j] for j in quedan])
        rep = resuelve_reposo(s, d, B[quedan], techo[bids], piso[quedan])
        if rep.regimen in SIN_MERCADO:
            break
        fuera = []
        for u, j in enumerate(quedan):
            colocado = float(rep.P[u].sum())
            if colocado <= 1e-9:
                continue
            if float(rep.P[u] @ rep.p_liquidado) / colocado < piso[j] - 1e-9:
                fuera.append(j)
        if not fuera:
            break
        assert len(fuera) < len(quedan), "el fixture no retira a todos"
        retirados += fuera
        quedan = [j for j in quedan if j not in fuera]
    return sids, bids, rep, quedan, retirados


def _texto(ids):
    return ";".join(NOMBRES[n] for n in ids)


def escribe_hora(alm, k, G, D, techo, piso, forzados=()):
    """Anota una hora en el almacen como `main_simulation.py` (via reposo)."""
    G, D = np.asarray(G, float), np.asarray(D, float)
    techo, piso = np.asarray(techo, float), np.asarray(piso, float)
    sids, bids, rep, quedan, retirados = _resuelve(G, D, techo, piso,
                                                   forzados)
    N = len(NOMBRES)
    P = np.zeros((len(sids), len(bids)))
    if rep is not None and rep.regimen not in SIN_MERCADO:
        for u, j in enumerate(quedan):
            P[sids.index(j)] = rep.P[u]
    cp, vp = np.zeros(N), np.zeros(N)
    for a, j in enumerate(sids):
        vp[j] = P[a].sum()
    for b, i in enumerate(bids):
        cp[i] = P[:, b].sum()
    alm.anota_agentes(k, NOMBRES, D, G, techo, piso, sids=sids, bids=bids,
                      retirados=retirados, compra_p2p=cp, vende_p2p=vp)
    # Los escenarios, en toda hora, como main_simulation.py. Cifras
    # sinteticas: P2P y C2 distintos en todas las instituciones.
    p2p = np.array([1000.0 + 10.0 * n + k for n in range(N)])
    alm.anota_escenarios(k, {"P2P": p2p, "C2": p2p - 40.0 - np.arange(N)},
                         NOMBRES)
    if rep is None:
        alm.sin_resolver(k, "sin mercado esa hora")
        return
    if rep.regimen in SIN_MERCADO:
        optimo = peor = cap = 0.0
    else:
        s = np.array([G[j] - D[j] for j in quedan])
        d = np.array([D[i] - G[i] for i in bids])
        optimo, peor = cotas_optimalidad(s, d, techo[bids], piso[quedan],
                                         rep.E)
        cap = captura(rep.excedente, optimo)
    columnas = dict(
        regimen=rep.regimen, presupuesto=float(rep.S),
        precio_comun=0.0 if rep.ell is None else float(rep.ell),
        precio_uniforme=float(rep.p_u), piso_juego=float(rep.piso),
        piso_marginal=float(rep.piso_marginal),
        renta_inframarginal=float(rep.renta_inframarginal),
        parte_juego=float(rep.parte_juego),
        n_soluciones=int(rep.n_soluciones), excedente_optimo=float(optimo),
        excedente_peor=float(peor), captura=float(cap),
        excluidos=_texto(bids[i] for i in rep.excluidos),
        excluidos_bajo_piso=_texto(bids[i] for i in rep.excluidos_bajo_piso),
        vendedores_excluidos=_texto(quedan[j]
                                    for j in rep.vendedores_excluidos),
        vendedores_no_despachados=_texto(
            quedan[j] for j in rep.vendedores_no_despachados),
        orden_merito=_texto(quedan[j] for j in rep.orden_merito),
        # D71: la rama cuantal, como `columnas_reposo` de main_simulation.py.
        regimen_cerrado=str(rep.regimen_cerrado),
        apartamiento=float(rep.apartamiento),
        mu_cuantal=float(rep.mu_cuantal))
    if rep.regimen in SIN_MERCADO:
        alm.anota_hora(k, resuelta=False, motivo="sin mercado esa hora",
                       **columnas)
        return
    pi = np.asarray(rep.p_liquidado, float)
    alm.anota_hora(k, resuelta=True, vendedores=len(sids),
                   compradores=len(bids), retirados=len(retirados),
                   volumen=float(P.sum()), precio_medio=float(pi.mean()),
                   **columnas)
    alm.anota_flujos(k, P, pi, sids, bids, NOMBRES, techo_i=techo[bids],
                     piso_j=piso[sids], pi_reposo=rep.pi_reposo)


def construye(alm, horas=HORAS, forzados=None):
    """Escribe todas las horas y cierra el almacen. `forzados`: {hora:
    vendedores retirados de entrada}."""
    forzados = forzados or {}
    for k, (G, D, techo, piso) in horas.items():
        escribe_hora(alm, k, G, D, techo, piso, forzados.get(k, ()))
    alm.cierra()


def _almacen_en_memoria(monkeypatch):
    """El volcado a parquet sustituido por uno en memoria, CON la conversion a
    float32 de `Almacen._vuelca`."""
    tablas = {}

    def vuelca(self, tabla):
        filas = self._buf[tabla]
        if not filas:
            return
        d = pd.DataFrame(filas)
        for col in d.columns:
            if d[col].dtype == "float64":
                d[col] = d[col].astype("float32")
        tablas.setdefault(tabla, []).append(d)
        self._partes[tabla] += 1
        self._buf[tabla] = []

    monkeypatch.setattr(almacen_mod, "_comprueba_motor",
                        lambda comprimir="zstd": None)
    monkeypatch.setattr(almacen_mod.Almacen, "_vuelca", vuelca)
    return tablas


@pytest.fixture
def tablas(monkeypatch, tmp_path):
    crudo = _almacen_en_memoria(monkeypatch)
    alm = almacen_mod.Almacen(tmp_path / "almacen", cobertura="m1")
    construye(alm)
    return {t: pd.concat(partes, ignore_index=True)
            for t, partes in crudo.items()}


@pytest.fixture
def tablas_con_retiro(monkeypatch, tmp_path):
    """El almacen en verde mas la hora 11, con Mariana retirada a la fuerza."""
    crudo = _almacen_en_memoria(monkeypatch)
    alm = almacen_mod.Almacen(tmp_path / "almacen", cobertura="m1")
    construye(alm, horas={**HORAS, **RETIRO}, forzados=RETIRADOS_FORZADOS)
    return {t: pd.concat(partes, ignore_index=True)
            for t, partes in crudo.items()}


def _corre(t):
    return cm.comprueba(t["horas"], t["flujos"], t["agentes"],
                        t["escenarios"], caso="SINT")


def _mensajes(inf, identidad):
    return " | ".join(msg for _, msg in inf.fallos[identidad])


def _fila(d, k, **filtro):
    m = d["hora"] == k
    for col, val in filtro.items():
        m &= d[col] == val
    assert m.any(), (k, filtro)
    return m


# ─── en verde ──────────────────────────────────────────────────────────────


def test_el_almacen_sintetico_cubre_lo_que_se_quiere_probar(tablas):
    h = tablas["horas"].set_index("hora")
    assert h.loc[0, "regimen"] == "interiores"
    assert h.loc[1, "regimen"] == "excluidos"
    assert h.loc[1, "excluidos"] == "Mariana"
    assert h.loc[2, "regimen"] == "compradores_cortos"
    assert h.loc[3, "excluidos_bajo_piso"] == "HUDN"
    assert h.loc[4, "vendedores_excluidos"] == "Cesmag"
    assert h.loc[5, "regimen"] == "sin_ganancia"
    assert not bool(h.loc[5, "resuelta"])
    assert h.loc[6, "motivo"] == "sin mercado esa hora"
    assert h.loc[7, "regimen"] == "un_comprador"
    assert h.loc[10, "regimen"] == "topados"
    ag = tablas["agentes"]
    # D63: con el piso marginal nadie se retira; la hora 8 despacha a los dos
    # vendedores, con renta para el de piso 700.
    assert "retirado" not in set(ag["papel"])
    assert set(ag.loc[ag["hora"] == 8, "papel"]) >= {"vendedor", "comprador"}
    assert h.loc[8, "piso_juego"] == h.loc[8, "piso_marginal"] == 760.0
    assert h.loc[8, "renta_inframarginal"] == pytest.approx(600.0)
    assert h.loc[8, "parte_juego"] == pytest.approx(400.0)
    assert h.loc[12, "vendedores_no_despachados"] == "Mariana"
    assert h.loc[12, "piso_juego"] == 600.0
    assert tablas["flujos"]["kwh"].dtype == np.float32
    assert "precio_reposo" in tablas["flujos"].columns


def test_en_verde(tablas, capsys):
    inf = _corre(tablas)
    assert inf.verde, {k: v for k, v in inf.fallos.items() if v}
    assert inf.retiros == (0, 0)
    renta, juego, prima = inf.prima
    assert renta > 0.0 and renta + juego == pytest.approx(prima, rel=1e-6)
    cm.imprime(inf)
    salida = capsys.readouterr().out
    assert salida.rstrip().splitlines()[-1] == \
        "COMPUERTA MATRIZ REPOSO SINT EN VERDE"
    for regimen in ("interiores", "topados", "compradores_cortos",
                    "un_comprador", "sin_ganancia"):
        assert regimen in salida
    assert ("Retiros de la participacion (D67, deben ser 0): 0 vendedores en "
            "0 horas") in salida
    assert "Prima de los vendedores de las horas resueltas (D69)" in salida


def test_cuenta_aparte_lo_descontado_por_cada_causa(tablas):
    inf = _corre(tablas)
    # hora 4: Cesmag, 5 (kWh) de oferta; hora 12: Mariana, 10 (kWh) no
    # despachados; hora 3: HUDN, 8 (kWh) de demanda; ningun retiro.
    assert inf.descuentos["vendedores_excluidos"] == (1, pytest.approx(5.0))
    assert inf.descuentos["vendedores_no_despachados"] == (
        1, pytest.approx(10.0))
    assert inf.descuentos["retirados"] == (0, 0.0)
    assert inf.descuentos["excluidos_bajo_piso"] == (1, pytest.approx(8.0))
    r = inf.resumen.set_index("regimen")
    assert r.loc["interiores", "horas"] >= 3
    assert r.loc["sin_ganancia", "resueltas"] == 0
    assert r.loc[cm.SIN_IDS, "horas"] == 1


# ─── cada identidad, rota a proposito ──────────────────────────────────────


def test_falla_el_volumen(tablas):
    ag = tablas["agentes"]
    ag.loc[_fila(ag, 0, agente="Udenar"), "sobrante"] += 1.0
    inf = _corre(tablas)
    assert not inf.verde
    assert [k for k, _ in inf.fallos["volumen"]] == [0]
    assert "suma de flujos" in _mensajes(inf, "volumen")
    assert not inf.fallos["excedente"] and not inf.fallos["ingreso"]


def test_falla_el_volumen_si_no_se_descuenta_al_retirado(tablas_con_retiro):
    t = tablas_con_retiro
    ag = t["agentes"]
    assert set(ag.loc[ag["hora"] == HORA_RETIRO, "papel"]) >= {"retirado"}
    inf = _corre(t)
    # Con el retirado descontado el volumen cuadra (solo falla cero_retiros).
    assert not inf.fallos["volumen"]
    assert inf.descuentos["retirados"] == (1, pytest.approx(10.0))
    ag.loc[_fila(ag, HORA_RETIRO, agente="Mariana"), "papel"] = "vendedor"
    inf = _corre(t)
    assert [k for k, _ in inf.fallos["volumen"]] == [HORA_RETIRO]


def test_falla_el_volumen_si_no_se_descuenta_al_no_despachado(tablas):
    # D65: sin descontar a Mariana (10 (kWh), piso 750), E seria min(13; 5) =
    # 5 y no los 3 (kWh) que se transan.
    h = tablas["horas"]
    h.loc[_fila(h, 12), "vendedores_no_despachados"] = ""
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["volumen"]] == [12]
    assert "demanda 5,000000" in _mensajes(inf, "volumen")


def test_falla_si_un_vendedor_esta_en_las_dos_listas(tablas):
    h = tablas["horas"]
    h.loc[_fila(h, 4), "vendedores_no_despachados"] = "Cesmag"
    inf = _corre(tablas)
    assert "a la vez en vendedores_excluidos (D61) y en " \
        "vendedores_no_despachados (D65)" in _mensajes(inf, "estado")


# ─── cero retiros (D67) y prima descompuesta (D69) ─────────────────────────


def test_cero_retiros_en_verde(tablas):
    inf = _corre(tablas)
    assert not inf.fallos["cero_retiros"] and inf.retiros == (0, 0)


def test_falla_cero_retiros_si_la_participacion_retiro_a_alguien(
        tablas_con_retiro, capsys):
    inf = _corre(tablas_con_retiro)
    assert not inf.verde
    assert [k for k, _ in inf.fallos["cero_retiros"]] == [
        HORA_RETIRO, HORA_RETIRO_SIN_MERCADO]
    assert "la participacion retiro a Mariana" in _mensajes(inf,
                                                             "cero_retiros")
    assert "la participacion retiro a Udenar" in _mensajes(inf,
                                                            "cero_retiros")
    assert "(D67)" in _mensajes(inf, "cero_retiros")
    assert inf.retiros == (2, 2)
    # Solo esa identidad: las dos horas forzadas cuadran en todo lo demas.
    for otra in cm.IDENTIDADES:
        if otra != "cero_retiros":
            assert not inf.fallos[otra], otra
    cm.imprime(inf)
    salida = capsys.readouterr().out
    assert "2 vendedores en 2 horas" in salida
    assert "cero_retiros: 2 fallo(s) en 2 hora(s)" in salida


def test_falla_cero_retiros_en_la_hora_que_perdio_el_mercado(
        tablas_con_retiro):
    """Revision final, importante 2: la hora que se queda sin mercado tras el
    retiro no tiene flujos ni sale resuelta, pero su retirado esta en la tabla
    de agentes y la compuerta lo ve."""
    t = tablas_con_retiro
    h = t["horas"].set_index("hora")
    assert not bool(h.loc[HORA_RETIRO_SIN_MERCADO, "resuelta"])
    assert h.loc[HORA_RETIRO_SIN_MERCADO, "regimen"] == "sin_ganancia"
    ag = t["agentes"]
    fila = ag[(ag["hora"] == HORA_RETIRO_SIN_MERCADO)
              & (ag["agente"] == "Udenar")]
    assert list(fila["papel"]) == ["retirado"]
    inf = _corre(t)
    assert HORA_RETIRO_SIN_MERCADO in [k for k, _ in inf.fallos["cero_retiros"]]
    # Sin el retirado en la tabla de agentes, la compuerta no vería nada: es
    # justo lo que pasaba antes del arreglo del motor.
    ag.loc[fila.index, "papel"] = "inactivo"
    inf = _corre(t)
    assert [k for k, _ in inf.fallos["cero_retiros"]] == [HORA_RETIRO]


def test_prima_descompuesta_en_verde(tablas):
    inf = _corre(tablas)
    assert not inf.fallos["prima_descompuesta"]
    # La peor desviacion es del redondeo float32: en la hora topada, con 1 350
    # (kWh) a unos 800 (COP/kWh), unas centesimas de peso, dentro de su cota.
    r = inf.resumen.set_index("regimen")
    assert (r["prima"].dropna() <= 0.05).all()
    assert r.loc["topados", "prima"] > 1e-2


def test_falla_la_prima_descompuesta(tablas):
    h = tablas["horas"]
    h.loc[_fila(h, 8), "renta_inframarginal"] += 5.0
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["prima_descompuesta"]] == [8]
    assert "renta inframarginal 605,0000" in _mensajes(inf,
                                                        "prima_descompuesta")
    for otra in cm.IDENTIDADES:
        if otra != "prima_descompuesta":
            assert not inf.fallos[otra], otra


def test_un_almacen_anterior_a_d63_no_se_puede_comprobar(tablas):
    with pytest.raises(cm.AlmacenIncompleto, match="anterior a D63"):
        cm.comprueba(tablas["horas"].drop(columns=["piso_marginal"]),
                     tablas["flujos"], tablas["agentes"],
                     tablas["escenarios"])


def test_un_almacen_de_otra_via_sale_con_2(tablas, monkeypatch, capsys):
    """Revision de la tarea 5a, menor 2: las columnas del reposo se escriben
    en todas las vias con valores neutros, de modo que un almacen acoplado
    pasa `_exige`. Lo que lo delata es que ninguna hora resuelta trae
    regimen: no se puede comprobar con esta compuerta, y sale con 2, no con
    1."""
    h = tablas["horas"]
    resueltas = h["resuelta"].eq(True)
    assert resueltas.any()
    h.loc[resueltas, "regimen"] = ""
    for col in ("presupuesto", "precio_comun", "precio_uniforme",
                "piso_juego", "piso_marginal", "renta_inframarginal",
                "parte_juego", "captura"):
        h.loc[resueltas, col] = 0.0
    with pytest.raises(cm.AlmacenIncompleto, match="no es de la via por "
                                                   "reposo"):
        _corre(tablas)
    monkeypatch.setattr(cm, "carga", lambda almacen, cobertura: tablas)
    assert cm.main(["x/E0/almacen"]) == 2
    salida = capsys.readouterr().out
    assert "NO SE PUEDE COMPROBAR" in salida
    assert "SOLO para almacenes por reposo" in salida


def test_un_almacen_sin_ninguna_hora_resuelta_sale_con_2(tablas, monkeypatch,
                                                         capsys):
    """Tarea 5c: sin horas resueltas ninguna identidad mira nada, de modo que
    la compuerta saldria EN VERDE sin haber comprobado una sola hora, y el
    detector de via tampoco puede decir de cual es. Sale con 2 y lo dice."""
    h = tablas["horas"]
    assert h["resuelta"].eq(True).any()
    h["resuelta"] = False
    with pytest.raises(cm.AlmacenIncompleto,
                       match="NO HA COMPROBADO NADA") as e:
        _corre(tablas)
    assert f"ninguna de las {len(h)} horas" in str(e.value)
    monkeypatch.setattr(cm, "carga", lambda almacen, cobertura: tablas)
    assert cm.main(["x/E0/almacen"]) == 2
    salida = capsys.readouterr().out
    assert "NO SE PUEDE COMPROBAR" in salida
    assert "NO HA COMPROBADO NADA" in salida


def test_falla_el_excedente(tablas):
    h = tablas["horas"]
    h.loc[_fila(h, 0), "captura"] *= 0.9
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["excedente"]] == [0]
    assert "captura x optimo" in _mensajes(inf, "excedente")
    assert not inf.fallos["captura"] and not inf.fallos["volumen"]


def test_falla_el_excedente_de_las_filas(tablas):
    fl = tablas["flujos"]
    fl.loc[_fila(fl, 9, vendedor="Udenar", comprador="UCC"),
           "ahorro_comprador"] += 1.0
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["excedente"]] == [9]
    assert "ahorro_comprador + prima_vendedor" in _mensajes(inf, "excedente")


def test_falla_el_ingreso(tablas):
    fl = tablas["flujos"]
    fl.loc[_fila(fl, 0, comprador="Mariana"), "precio_reposo"] += 1.0
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["ingreso"]] == [0]
    assert "p_liquidado" in _mensajes(inf, "ingreso")
    assert not inf.fallos["precios"]


def test_falla_un_precio_de_la_hora_bajo_el_piso(tablas):
    h = tablas["horas"]
    m = _fila(h, 0)
    h.loc[m, "precio_uniforme"] = h.loc[m, "piso_juego"] - 5.0
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["precios"]] == [0]
    assert "precio uniforme" in _mensajes(inf, "precios")
    assert not inf.fallos["ingreso"] and not inf.fallos["vendedores"]


def test_falla_un_precio_liquidado_sobre_el_techo(tablas):
    fl = tablas["flujos"]
    m = _fila(fl, 2, comprador="UCC")
    fl.loc[m, "precio"] = fl.loc[m, "techo_comprador"] + 5.0
    inf = _corre(tablas)
    assert 2 in [k for k, _ in inf.fallos["precios"]]
    assert "UCC: liquidado" in _mensajes(inf, "precios")


def test_falla_un_vendedor_bajo_su_piso(tablas):
    # La comprobacion usa el piso DE CADA VENDEDOR, no el del juego. Hora 9:
    # los dos cobran 773,33 (COP/kWh), con el piso del juego en 720, el de
    # Mariana (D63). Se reescribe la hora como la dejaria la regla vieja (D62):
    # piso del juego 700, el de Udenar, y todos los precios 60 abajo, en
    # 713,33. Mariana (piso 720) cobra bajo su piso aunque el precio siga
    # sobre el piso del juego y el ingreso se conserve; Udenar queda cubierto.
    # La parte del juego baja con la prima, para que solo falle la identidad
    # de los vendedores.
    fl = tablas["flujos"]
    h = tablas["horas"]
    m = _fila(fl, 9)
    vol = float(fl.loc[m, "kwh"].sum())
    fl.loc[m, "precio"] -= 60.0
    fl.loc[m, "precio_reposo"] -= 60.0
    mh = _fila(h, 9)
    h.loc[mh, "piso_juego"] = 700.0
    h.loc[mh, ["precio_uniforme", "precio_comun"]] -= 60.0
    h.loc[mh, "parte_juego"] -= 60.0 * vol
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["vendedores"]] == [9]
    assert "Mariana coloca" in _mensajes(inf, "vendedores")
    assert "bajo su piso 720" in _mensajes(inf, "vendedores")
    assert "Udenar" not in _mensajes(inf, "vendedores")
    for otra in ("precios", "ingreso", "excedente", "volumen",
                 "prima_descompuesta"):
        assert not inf.fallos[otra], otra


def test_falla_la_parte_negativa_de_los_vendedores(tablas):
    fl = tablas["flujos"]
    m = _fila(fl, 7)
    fl.loc[m, "precio"] -= 10.0
    inf = _corre(tablas)
    assert "parte de los vendedores negativa" in _mensajes(inf, "vendedores")


def test_falla_la_captura(tablas):
    h = tablas["horas"]
    h.loc[_fila(h, 0), "captura"] = 1.5
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["captura"]] == [0]
    assert "fuera de [0, 1]" in _mensajes(inf, "captura")


def test_falla_la_finitud(tablas):
    h = tablas["horas"]
    h.loc[_fila(h, 0), "presupuesto"] = np.nan
    fl = tablas["flujos"]
    fl.loc[_fila(fl, 2, comprador="UCC"), "precio_reposo"] = np.inf
    inf = _corre(tablas)
    horas = sorted({k for k, _ in inf.fallos["finitud"]})
    assert horas == [0, 2]
    assert "presupuesto" in _mensajes(inf, "finitud")


def test_falla_si_una_hora_sin_mercado_tiene_flujos(tablas):
    fl = tablas["flujos"]
    fila = fl[fl["hora"] == 7].iloc[[0]].copy()
    fila["hora"] = 5
    tablas["flujos"] = pd.concat([fl, fila], ignore_index=True)
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["sin_mercado"]] == [5]
    assert "sin_ganancia" in _mensajes(inf, "sin_mercado")


def test_falla_una_hora_con_excepcion_del_reposo(tablas):
    h = tablas["horas"]
    m = _fila(h, 3)
    h.loc[m, "resuelta"] = False
    h.loc[m, "motivo"] = "excepcion del reposo: ValueError: prueba"
    tablas["flujos"] = tablas["flujos"][tablas["flujos"]["hora"] != 3]
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["estado"]] == [3]
    assert "excepcion del reposo" in _mensajes(inf, "estado")


def test_falla_una_lista_que_nombra_a_quien_no_esta(tablas):
    h = tablas["horas"]
    h.loc[_fila(h, 4), "vendedores_excluidos"] = "Mariana"
    inf = _corre(tablas)
    assert "vendedores_excluidos nombra a Mariana" in _mensajes(inf, "estado")


def test_un_almacen_sin_columnas_del_reposo_no_se_puede_comprobar(tablas):
    with pytest.raises(cm.AlmacenIncompleto, match="regimen"):
        cm.comprueba(tablas["horas"].drop(columns=["regimen"]),
                     tablas["flujos"], tablas["agentes"],
                     tablas["escenarios"])


# ─── ramas que la primera entrega no probaba (revision de 4b, menor 5) ─────


def test_falla_un_precio_del_reposo_sobre_el_techo(tablas):
    fl = tablas["flujos"]
    m = _fila(fl, 0, comprador="Mariana")
    fl.loc[m, "precio_reposo"] = fl.loc[m, "techo_comprador"] + 5.0
    inf = _corre(tablas)
    assert 0 in [k for k, _ in inf.fallos["precios"]]
    assert "Mariana: liquidado" in _mensajes(inf, "precios")
    assert "y del reposo [805,0000; 805,0000]" in _mensajes(inf, "precios")


def test_falla_el_precio_comun_de_la_hora_fuera_de_la_banda(tablas):
    h = tablas["horas"]
    h.loc[_fila(h, 0), "precio_comun"] = 810.0
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["precios"]] == [0]
    assert "precio comun de la hora" in _mensajes(inf, "precios")
    assert not inf.fallos["ingreso"] and not inf.fallos["vendedores"]


@pytest.mark.parametrize("hora,lista", [(4, "vendedores_excluidos"),
                                        (3, "excluidos_bajo_piso")])
def test_falla_el_volumen_si_no_se_descuenta_una_exclusion(tablas, hora,
                                                            lista):
    h = tablas["horas"]
    h.loc[_fila(h, hora), lista] = ""
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["volumen"]] == [hora]


def test_la_cota_del_volumen_no_la_infla_el_lado_largo(tablas):
    # Hora 2, compradores cortos: E es la demanda, 9 (kWh). Con la oferta de
    # Cesmag a un millon de kWh, una cota que sumara los dos lados valdria
    # 0,12 (kWh) y taparia un error de 1e-4 (kWh); con 2·E no lo tapa.
    ag = tablas["agentes"]
    ag.loc[_fila(ag, 2, agente="Cesmag"), "sobrante"] = 1e6
    fl = tablas["flujos"]
    m = _fila(fl, 2, vendedor="Cesmag", comprador="Mariana")
    fl.loc[m, "kwh"] = fl.loc[m, "kwh"] + np.float32(1e-4)
    inf = _corre(tablas)
    assert 2 in [k for k, _ in inf.fallos["volumen"]]


def test_falla_un_regimen_desconocido(tablas):
    h = tablas["horas"]
    h.loc[_fila(h, 0), "regimen"] = "raro"
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["estado"]] == [0]
    assert "regimen desconocido 'raro'" in _mensajes(inf, "estado")


def test_falla_una_hora_resuelta_sin_regimen(tablas):
    h = tablas["horas"]
    h.loc[_fila(h, 0), "regimen"] = ""
    inf = _corre(tablas)
    assert 0 in [k for k, _ in inf.fallos["estado"]]
    assert "hora resuelta sin regimen" in _mensajes(inf, "estado")


def test_falla_si_hay_flujos_de_una_hora_que_no_esta(tablas):
    fl = tablas["flujos"]
    fila = fl[fl["hora"] == 7].iloc[[0]].copy()
    fila["hora"] = 99
    tablas["flujos"] = pd.concat([fl, fila], ignore_index=True)
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["estado"]] == [99]
    assert "no esta en la tabla de horas" in _mensajes(inf, "estado")


# ─── no finitos en agentes y escenarios (revision de 4b, importante 1) ─────


def test_falla_un_nan_en_la_tabla_de_agentes(tablas):
    ag = tablas["agentes"]
    ag.loc[_fila(ag, 0, agente="Udenar"), "sobrante"] = np.nan
    inf = _corre(tablas)
    assert 0 in [k for k, _ in inf.fallos["finitud"]]
    assert "sobrante o el faltante no finito" in _mensajes(inf, "finitud")


def test_falla_un_nan_en_la_tabla_de_escenarios(tablas):
    es = tablas["escenarios"]
    es.loc[_fila(es, 1, escenario="C2", agente="UCC"), "valor"] = np.nan
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["finitud"]] == [1]
    assert "escenario trae un valor no finito" in _mensajes(inf, "finitud")


# ─── P2P frente a C2 (sintesis §6; revision de 4b, menor 13) ───────────────


def _c2_igual_a_p2p(es, agentes=None):
    """Pone el C2 de esas instituciones (todas si None) igual al P2P."""
    es = es.copy()
    p2p = es["escenario"] == "P2P"
    c2 = es["escenario"] == "C2"
    if agentes is not None:
        p2p &= es["agente"].isin(agentes)
        c2 &= es["agente"].isin(agentes)
    es.loc[c2, "valor"] = es.loc[p2p, "valor"].to_numpy()
    return es


def test_p2p_y_c2_distintos_en_verde(tablas):
    inf = _corre(tablas)
    assert inf.p2p_c2 and not any(c for _, _, c in inf.p2p_c2.values())
    assert set(inf.p2p_c2) == set(NOMBRES)


def test_falla_si_p2p_y_c2_coinciden_en_todas(tablas, capsys):
    tablas["escenarios"] = _c2_igual_a_p2p(tablas["escenarios"])
    inf = _corre(tablas)
    assert not inf.verde
    assert [k for k, _ in inf.fallos["p2p_c2"]] == [cm.DEL_CASO]
    assert "defecto viejo" in _mensajes(inf, "p2p_c2")
    for otra in cm.IDENTIDADES[:-1]:
        assert not inf.fallos[otra], otra
    cm.imprime(inf)
    assert capsys.readouterr().out.rstrip().splitlines()[-1].startswith(
        "    caso: P2P y C2 coinciden en las 5 instituciones")


def test_avisa_sin_fallar_si_coinciden_solo_en_algunas(tablas):
    tablas["escenarios"] = _c2_igual_a_p2p(tablas["escenarios"], ["Udenar"])
    inf = _corre(tablas)
    assert inf.verde
    assert inf.p2p_c2["Udenar"][2] and not inf.p2p_c2["UCC"][2]
    assert any("coinciden en 1 de las 5" in a for a in inf.avisos)


def test_sin_c2_no_se_puede_comprobar(tablas):
    es = tablas["escenarios"]
    tablas["escenarios"] = es[es["escenario"] != "C2"]
    with pytest.raises(cm.AlmacenIncompleto, match="C2"):
        _corre(tablas)


# ─── la linea de ordenes ───────────────────────────────────────────────────


@pytest.mark.parametrize("rompe,codigo,final", [
    (False, 0, "COMPUERTA MATRIZ REPOSO E0 EN VERDE"),
    (True, 1, "COMPUERTA MATRIZ REPOSO E0 FALLA"),
])
def test_main_sale_con_su_codigo(tablas, monkeypatch, capsys, rompe, codigo,
                                 final):
    if rompe:
        h = tablas["horas"]
        h.loc[_fila(h, 0), "captura"] = 1.5
    monkeypatch.setattr(cm, "carga", lambda almacen, cobertura: tablas)
    assert cm.main(["SALIDAS_SERVIDOR/matriz_reposo/E0/almacen"]) == codigo
    salida = capsys.readouterr().out
    assert final in salida
    if rompe:
        assert salida.rstrip().splitlines()[-1].startswith("    hora 0:")


def test_main_sin_columnas_sale_con_2(tablas, monkeypatch, capsys):
    tablas["horas"] = tablas["horas"].drop(columns=["captura"])
    monkeypatch.setattr(cm, "carga", lambda almacen, cobertura: tablas)
    assert cm.main(["x/K1/almacen", "--caso", "K1"]) == 2
    assert "NO SE PUEDE COMPROBAR" in capsys.readouterr().out


# ─── D71: la rama cuantal (tarea Q) ────────────────────────────────────────


def test_la_hora_fragil_sale_cuantal_y_la_compuerta_la_acepta(tablas, capsys):
    """La hora 14, de la familia de la hora 12 de E0: la forma cerrada es
    «excluidos» (todo a Cesmag) y el nucleo publica el reposo cuantal, con
    Mariana y UCC recibiendo su parte. La compuerta la acepta en verde: el
    volumen, el excedente, los precios y la cobertura valen igual."""
    h = tablas["horas"].set_index("hora")
    assert h.loc[14, "regimen"] == "cuantal"
    assert h.loc[14, "regimen_cerrado"] == "excluidos"
    assert h.loc[14, "apartamiento"] == pytest.approx(0.289, abs=1e-3)
    assert h.loc[14, "mu_cuantal"] == 1.0
    assert h.loc[14, "excluidos"] == ""
    # Fuera de la hora fragil, el regimen cerrado es el regimen y el
    # apartamiento no pasa del umbral.
    otras = h[(h.index != 14) & (h["regimen"].fillna("") != "")]
    assert (otras["regimen_cerrado"] == otras["regimen"]).all()
    assert (otras["apartamiento"] <= 1e-3).all()
    fl = tablas["flujos"]
    recibe = fl[fl["hora"] == 14].groupby("comprador")["kwh"].sum()
    assert recibe["Mariana"] > 1.0 and recibe["UCC"] > 1.0
    inf = _corre(tablas)
    assert inf.verde, {k: v for k, v in inf.fallos.items() if v}
    assert inf.cuantal == (1, 0, 0)
    cm.imprime(inf)
    salida = capsys.readouterr().out
    assert ("Horas «cuantal» (D71): 1; con n_soluciones distinto de 1: 0 "
            "(esperado 0); del lado de los vendedores: 0") in salida
    assert "cuantal" in inf.resumen["regimen"].tolist()


@pytest.mark.parametrize("hora,columna,valor,mensaje", [
    (14, "apartamiento", 5e-4, "que no pasa de 0.001"),
    (0, "apartamiento", 0.01, "tendria que ser «cuantal»"),
    (14, "regimen_cerrado", "cuantal", "que no es de mercado"),
    (14, "regimen_cerrado", "sin_ganancia", "que no es de mercado"),
    (14, "mu_cuantal", 0.0, "con la rama apagada"),
    (0, "regimen_cerrado", "topados", "fuera de «cuantal» son el mismo"),
])
def test_falla_la_identidad_cuantal(tablas, hora, columna, valor, mensaje):
    h = tablas["horas"]
    if isinstance(valor, float):
        valor = np.float32(valor)
    h.loc[_fila(h, hora), columna] = valor
    inf = _corre(tablas)
    assert [k for k, _ in inf.fallos["cuantal"]] == [hora]
    assert mensaje in _mensajes(inf, "cuantal")
    for otra in cm.IDENTIDADES:
        if otra != "cuantal":
            assert not inf.fallos[otra], otra


def test_la_frontera_del_umbral_admite_el_redondeo_float32(tablas):
    # Un apartamiento de 1e-3 guardado en float32 queda a medio epsilon del
    # umbral; ni la hora cuantal ni una que no lo es fallan por eso.
    h = tablas["horas"]
    h.loc[_fila(h, 14), "apartamiento"] = np.float32(1e-3)
    h.loc[_fila(h, 0), "apartamiento"] = np.float32(1e-3)
    inf = _corre(tablas)
    assert not inf.fallos["cuantal"]


def test_avisa_de_las_horas_cuantales_con_otros_estados_y_del_lado_vendedor(
        tablas):
    h = tablas["horas"]
    h.loc[_fila(h, 14), "n_soluciones"] = np.float32(2.0)
    inf = _corre(tablas)
    assert inf.verde and inf.cuantal == (1, 1, 0)
    assert any("n_soluciones distinto de 1" in a and "[14]" in a
               for a in inf.avisos)
    h.loc[_fila(h, 14), "regimen_cerrado"] = "compradores_cortos"
    inf = _corre(tablas)
    assert inf.verde and inf.cuantal == (1, 1, 1)
    assert any("del lado de los vendedores" in a for a in inf.avisos)


def test_un_almacen_anterior_a_d71_no_se_puede_comprobar(tablas):
    with pytest.raises(cm.AlmacenIncompleto, match="anterior a D71"):
        cm.comprueba(tablas["horas"].drop(columns=["regimen_cerrado",
                                                   "apartamiento",
                                                   "mu_cuantal"]),
                     tablas["flujos"], tablas["agentes"],
                     tablas["escenarios"])


def test_el_nombre_del_caso_sale_de_la_carpeta():
    assert cm.nombre_caso("SALIDAS_SERVIDOR/matriz_reposo/E0/almacen") == "E0"
    assert cm.nombre_caso("otra/cosa") == "cosa"
