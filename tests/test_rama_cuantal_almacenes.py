"""
La rama cuantal del reposo (D71) sobre los 13 almacenes de la matriz del
2026-09-17. Tarea Q, 2026-09-19; el diseno, con sus esperados, en
`.superpowers/sdd/2026-09-16-reposo/diseno-rama-cuantal.md` (sec. 6.2 y 8.7).

QUE SE PRUEBA. Cada hora con mercado de cada almacen se reconstruye de su tabla
`agentes`, como hace el censo de M-E (`censo_fragiles.entradas_de_hora`), y se
resuelve dos veces con el nucleo: con la rama apagada (`mu_cuantal=0.0`, la
forma cerrada con que se escribio la matriz) y con el defecto (la rama
encendida, mu = 1). Se comprueba:

  - la forma cerrada reproduce lo que el almacen guardo (regimen, volumen y lo
    que recibe cada comprador), en todas las horas;
  - el regimen es «cuantal» exactamente en las 216 horas fragiles del censo
    (E0 57, E1 22, E2 14, E3 4, K1 50, I1 9, N1 11, P1 3, SINU 46; ninguna en
    E4, E5, CV2 y P2), y si esta la salida del censo de la tarea 4e, en las
    mismas horas y con el mismo apartamiento (1e-9 relativo);
  - en las 216: del lado de los compradores (lo despachado, al bit el
    cerrado), un solo estado y el MISMO que el cerrado (precios, S, ell y
    regimen cerrado al bit), sin excluidos;
  - la energia que cambia de manos, sum ½·sum_i |q cuantal - q cerrado|, es
    48,5 (kWh) en los 13 casos (19,53 en E0, 0,82 en K1, 20,51 en SINU);
  - en las demas horas, TODOS los campos de antes de D71 al bit entre la rama
    encendida y apagada;
  - la comparacion hora a hora (`compara_matriz_reposo.horas_distintas`)
    entre una matriz cerrada y una cuantal, con las mismas entradas, muestra
    exactamente las 216 horas, al bit en float32 (sec. 8.7).

SE SALTA si los almacenes no estan (no viajan con git) o si falta pyarrow para
leerlos. Corre en uno o dos minutos: unas 31 000 resoluciones del nucleo.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
for _p in (RAIZ, RAIZ / "reformateo" / "documento" / "scripts" / "sonda",
           RAIZ / "reformateo" / "documento" / "scripts" / "sonda" / "consenso"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from core.reposo_mercado import ReposoHora, resuelve_reposo  # noqa: E402

MATRIZ = RAIZ / ("SALIDAS_SERVIDOR/entrega_validacion_2026-09-19/"
                 "SALIDAS_SERVIDOR/matriz_reposo")
CENSO_4E = RAIZ / (".superpowers/sdd/2026-09-16-reposo/task-4e-salidas/"
                   "censo_fragiles_13_casos.json")
CASOS = ("CV2", "E0", "E1", "E2", "E3", "E4", "E5", "I1", "K1", "N1", "P1",
         "P2", "SINU")
FRAGILES = dict(E0=57, E1=22, E2=14, E3=4, K1=50, I1=9, N1=11, P1=3, SINU=46,
                E4=0, E5=0, CV2=0, P2=0)
CAMPOS_ANTES_DE_D71 = tuple(
    f.name for f in dataclasses.fields(ReposoHora)
    if f.name not in ("regimen_cerrado", "apartamiento", "mu_cuantal"))


def _hay_almacenes() -> str:
    faltan = [c for c in CASOS if not (MATRIZ / c / "almacen" / "m1").is_dir()]
    if faltan:
        return f"faltan los almacenes de {faltan} en {MATRIZ}"
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        return "falta pyarrow para leer los almacenes"
    return ""


pytestmark = pytest.mark.skipif(bool(_hay_almacenes()),
                                reason=_hay_almacenes() or "-")


def _igual_al_bit(a, b) -> list:
    malos = []
    for campo in CAMPOS_ANTES_DE_D71:
        x, y = getattr(a, campo), getattr(b, campo)
        if isinstance(x, np.ndarray):
            if not (isinstance(y, np.ndarray) and x.dtype == y.dtype
                    and np.array_equal(x, y)):
                malos.append(campo)
        elif type(x) is not type(y) or x != y:
            malos.append(campo)
    return malos


@pytest.fixture(scope="module")
def matriz():
    """{caso: dict(tablas, horas={hora: (ent, cerrado, rama, fila)})}."""
    from censo_fragiles import (SIN_MERCADO, comprueba, entradas_de_hora,
                                lee_almacen)
    fuera = {}
    for caso in CASOS:
        agentes, flujos, horas = lee_almacen(MATRIZ / caso / "almacen")
        ag_h = {int(h): sub for h, sub in agentes.groupby("hora")}
        fl_h = {int(h): sub for h, sub in flujos.groupby("hora")}
        vacio = flujos.iloc[0:0]
        por_hora, no_repro = {}, []
        for fila in horas.to_dict("records"):
            reg = str(fila.get("regimen", "") or "")
            if not bool(fila.get("resuelta", False)) or reg in SIN_MERCADO:
                continue
            h = int(fila["hora"])
            ent = entradas_de_hora(ag_h[h])
            args = (ent["s"], ent["d"], np.zeros(len(ent["vend"])),
                    ent["techo"], ent["piso_j"])
            cerrado = resuelve_reposo(*args, mu_cuantal=0.0)
            rama = resuelve_reposo(*args)
            motivo = comprueba(cerrado, ent, fila, fl_h.get(h, vacio))
            if motivo:
                no_repro.append((h, motivo))
            por_hora[h] = (ent, cerrado, rama)
        fuera[caso] = dict(tablas=dict(agentes=agentes, flujos=flujos,
                                       horas=horas),
                           horas=por_hora, no_repro=no_repro)
    return fuera


def test_la_forma_cerrada_reproduce_la_matriz_del_17(matriz):
    for caso, m in matriz.items():
        assert m["no_repro"] == [], (caso, m["no_repro"][:5])
    assert sum(len(m["horas"]) for m in matriz.values()) == 15363


def test_cuantal_exactamente_en_las_216_horas_fragiles(matriz):
    por_caso = {caso: sorted(h for h, (_, _, r) in m["horas"].items()
                             if r.regimen == "cuantal")
                for caso, m in matriz.items()}
    assert {c: len(v) for c, v in por_caso.items()} == FRAGILES
    assert sum(len(v) for v in por_caso.values()) == 216
    if CENSO_4E.is_file():
        censo = json.loads(CENSO_4E.read_text(encoding="utf-8"))
        for caso, m in matriz.items():
            lista = {int(x["hora"]): x for x in
                     censo[caso]["horas_fragiles_lista"]}
            assert sorted(lista) == por_caso[caso], caso
            for h, x in lista.items():
                rama = m["horas"][h][2]
                apart = max(x["dq"], x["ds"]) / x["E"]
                assert rama.apartamiento == pytest.approx(apart, rel=1e-9), \
                    (caso, h)


def test_en_las_216_el_estado_cuantal_es_el_cerrado(matriz):
    movida = {}
    for caso, m in matriz.items():
        total = 0.0
        for h, (ent, cerrado, rama) in m["horas"].items():
            if rama.regimen != "cuantal":
                continue
            assert rama.regimen_cerrado == cerrado.regimen, (caso, h)
            assert cerrado.regimen in ("excluidos", "topados"), (caso, h)
            # Del lado de los compradores: lo despachado, al bit.
            assert np.array_equal(rama.s_despachado, cerrado.s_despachado)
            assert rama.n_soluciones == 1, (caso, h)
            assert np.array_equal(rama.pi_reposo, cerrado.pi_reposo)
            assert rama.S == cerrado.S and rama.ell == cerrado.ell
            assert rama.piso == cerrado.piso and rama.E == cerrado.E
            assert rama.excluidos == (), (caso, h)
            assert rama.apartamiento > 1e-3
            total += 0.5 * float(np.abs(rama.q - cerrado.q).sum())
        movida[caso] = total
    assert sum(movida.values()) == pytest.approx(48.5, abs=0.1)
    assert movida["E0"] == pytest.approx(19.53, abs=0.01)
    assert movida["K1"] == pytest.approx(0.82, abs=0.01)
    assert movida["SINU"] == pytest.approx(20.51, abs=0.01)


def test_en_las_demas_horas_todo_al_bit(matriz):
    n = 0
    for caso, m in matriz.items():
        for h, (ent, cerrado, rama) in m["horas"].items():
            if rama.regimen == "cuantal":
                continue
            assert _igual_al_bit(rama, cerrado) == [], (caso, h)
            assert rama.regimen_cerrado == rama.regimen
            assert rama.apartamiento <= 1e-3
            n += 1
    assert n == 15363 - 216


def _flujos(tablas, horas, cual):
    """La tabla de flujos del almacen con el reparto de `cual` (1 cerrado,
    2 rama) en cada hora con mercado, en float32 como `Almacen._vuelca`."""
    import pandas as pd
    filas = []
    for h, trio in horas.items():
        ent, r = trio[0], trio[cual]
        for j, v in enumerate(ent["vend"]):
            for i, c in enumerate(ent["comp"]):
                filas.append((h, v, c, float(np.float32(r.P[j, i]))))
    return pd.DataFrame(filas, columns=["hora", "vendedor", "comprador",
                                        "kwh"])


def test_la_comparacion_hora_a_hora_muestra_exactamente_las_216(matriz):
    """Sec. 8.7: una matriz con la rama frente a la del 17, con las mismas
    entradas, difiere en las 216 horas y en ninguna mas. Al bit (float32)
    frente a la cerrada recalculada; y frente al almacen guardado del 17, con
    una holgura de 1e-5 (kWh) por pareja, porque las entradas del almacen ya
    son float32 y el reparto recalculado con ellas se aparta del guardado en
    el ultimo bit de precision sencilla."""
    import compara_matriz_reposo as cmp
    total = total_guardado = 0
    for caso, m in matriz.items():
        t = m["tablas"]
        horas_rama = t["horas"].copy()
        for h, (_, _, rama) in m["horas"].items():
            horas_rama.loc[horas_rama["hora"] == h, "regimen"] = rama.regimen
        cerrada = dict(agentes=t["agentes"], horas=t["horas"],
                       flujos=_flujos(t, m["horas"], 1))
        con_rama = dict(agentes=t["agentes"], horas=horas_rama,
                        flujos=_flujos(t, m["horas"], 2))
        entradas, mercado = cmp.horas_distintas(cerrada, con_rama)
        esperadas = sorted(h for h, (_, _, r) in m["horas"].items()
                           if r.regimen == "cuantal")
        assert entradas.empty, caso
        assert sorted(mercado["hora"]) == esperadas, caso
        assert set(mercado["regimen_nueva"]) <= {"cuantal"}
        total += len(mercado)
        entradas, mercado = cmp.horas_distintas(t, con_rama, tol_kwh=1e-5)
        assert entradas.empty and sorted(mercado["hora"]) == esperadas, caso
        total_guardado += len(mercado)
    assert total == total_guardado == 216


HORAS_MD = RAIZ / ("SALIDAS_SERVIDOR/entrega_validacion_2026-09-19/"
                   "SALIDAS_SERVIDOR/validacion_reposo")


@pytest.mark.skipif(not HORAS_MD.is_dir(),
                    reason=f"faltan las horas de la muestra de M-D en "
                           f"{HORAS_MD}")
def test_md_la_muestra_de_50_horas_es_estable_con_la_rama():
    """Sec. 6.3: la muestra de M-D (50 horas de E0, armadas de su almacen).
    Con la forma cerrada, las cuatro horas NO estables eran las cuatro
    frageles (tarea 4e); con la rama, las 50 son estables y quietas, y las
    cuatro frageles, estables. «Fragil» se decide con la forma cerrada."""
    import medicion_estabilidad as MD
    from censo_fragiles import horas_del_almacen
    from corre_mediciones import carga_horas
    tareas = MD.specs(carga_horas(HORAS_MD), 10)
    assert len(tareas) == 50
    armadas = {}
    for caso in sorted({sp["caso"] for sp in tareas}):
        fechas = [sp["fecha"] for sp in tareas if sp["caso"] == caso]
        for fecha, e0 in horas_del_almacen(MATRIZ / caso / "almacen",
                                           fechas).items():
            armadas[(caso, fecha)] = e0
    vistas = {}
    for sp in tareas:
        clave = (sp["caso"], sp["fecha"])
        if clave in vistas:
            continue
        rama = MD.analiza(sp, e0=armadas[clave])
        cerrado = MD.analiza(dict(sp, cerrada=dict(mu_cuantal=0.0)),
                             e0=armadas[clave])
        assert not rama.get("sin_mercado") and not rama.get("recorte_movio")
        vistas[clave] = (rama, cerrado)
    fragiles = [c for c, (r, _) in vistas.items() if r["fragil"]]
    no_estables_cerrado = [c for c, (_, k) in vistas.items()
                           if not k["estable"]]
    assert len(fragiles) == 4
    assert sorted(no_estables_cerrado) == sorted(fragiles)
    for clave, (rama, cerrado) in vistas.items():
        assert rama["estable"] and rama["quieta"], clave
        assert rama["fragil"] is cerrado["fragil"], clave
        assert (rama["regimen"] == "cuantal") is rama["fragil"], clave
        if rama["fragil"]:
            assert rama["residuo_P"] < 1e-8, clave
            assert rama["mayor_fuera_de_neutras"] < 0.0, clave
