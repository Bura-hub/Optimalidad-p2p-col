"""
El censo de la campana de convergencia: que cuesta mirar el reparto (H-86;
D47). 2026-09-16.

QUE MIDE. La campana `convergencia` del lanzador corre la misma semana de dos
casos (E0 y K1) con tres configuraciones del criterio de parada: la de hoy, que
mira solo el precio al horizonte 0,4; y el criterio nuevo, que mira tambien el
reparto, a los horizontes 0,4 y 2,0. Este guion lee los almacenes de esas
corridas y dice, por caso y configuracion:

  - cuantas horas de mercado hay, cuantas resolvieron y cuantas no, con su
    motivo;
  - cuantas pararon por cada motivo del acoplado (estacionario, tope,
    presupuesto, vuelta fallida) y con que horizonte;
  - el residuo del PRECIO y el del REPARTO (mediana, percentil 90 y maximo), y
    cuantas horas quedaron con el reparto por encima del umbral, es decir con
    la energia todavia cambiando de manos al parar;
  - LO QUE COSTO, que es la otra mitad de la decision: los segundos de reloj y
    las evaluaciones del integrador por hora (mediana, percentil 90, maximo y
    suma).

Es lo que hace falta para fijar el horizonte de produccion con el costo MEDIDO
delante, que es lo que D47 exige, en vez de adivinarlo.

DE DONDE SALE CADA NUMERO (`core/almacen.py`, tabla `horas`, una fila por hora):
  resuelta, motivo    si la hora resolvio y, si no, por que. Hora de mercado es
                      la resuelta o la que quedo sin resolver por un motivo
                      distinto de «sin mercado esa hora».
  parada_acoplado     por que paro el acoplado (D36, D37). Solo aparece con la
                      parada por estacionario activa.
  residuo             cuanto se movia el PRECIO en el ultimo decimo (D26).
  residuo_reparto     cuanto se movia el REPARTO (D47).
  segundos            tiempo de reloj de resolver esa hora (D47). Depende de la
                      maquina: se lee como orden de magnitud, no al segundo.
  evaluaciones        evaluaciones del integrador sumadas sobre las vueltas de
                      esa hora (D47). NO depende de la maquina, y es la cuenta
                      con la que D36 hace su presupuesto.

Las cuatro ultimas y el costo existen desde D47: un almacen anterior no las
trae, y entonces **el censo lo dice y no cuenta**. Un cero que en realidad
significa «no medido» es justo el tipo de cifra que este proyecto persigue, de
modo que cada columna ausente sale con su aviso y su bandera `tiene_*`, tambien
en el CSV.

El costo se resume sobre las horas RESUELTAS, que son las unicas cuya fila lo
trae: la hora que no resuelve se anota con su motivo y nada mas. Las horas que
el plazo mata o que el integrador pierde cuestan tiempo que este censo no ve; el
registro de la corrida si lo dice.

Es una MEDICION, no una compuerta: sale con 0 sea cual sea el resultado. Solo
sale con otro codigo si no puede medir (una carpeta sin almacenes, una tabla
que no trae lo que se espera).

La funcion `censa` es pura: recibe el DataFrame de la tabla de horas y no lee
parquet, de modo que se prueba sin pyarrow. `carga` lee el almacen con
`core.almacen.lee`, que si lo necesita. Misma separacion que
`compara_arranque.py`.

Uso, desde la raiz del repositorio:
    python -u reformateo/documento/scripts/sonda/censo_convergencia.py \
        SALIDAS_SERVIDOR/convergencia --cobertura m1 \
        --salida SALIDAS_SERVIDOR/convergencia

La carpeta es la de la campana: cada subcarpeta `<caso>_<configuracion>` con un
`almacen` dentro es una corrida. Tambien admite almacenes sueltos con
`--almacen NOMBRE=RUTA`, repetible.
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

SIN_MERCADO = "sin mercado esa hora"
# Los motivos de parada del acoplado (D36, D37), en el orden en que se
# imprimen. "una_vuelta" es la parada apagada: una sola resolucion.
PARADAS = ("estacionario", "tope", "presupuesto", "fallo_vuelta", "una_vuelta")
# El umbral con que se cuenta una hora como «el reparto seguia moviendose».
# Es el mismo defecto de `SolverParams.tol_reparto`, y se cambia con --tol.
TOL_REPARTO = 0.01
# Las dos columnas del costo por hora (D47). Son nombres FIJOS del almacen, no
# una lista de candidatos: el motor las escribe con estos nombres.
COSTO = ("segundos", "evaluaciones")


def _percentil(v: pd.Series, q: float) -> float:
    v = pd.to_numeric(v, errors="coerce").dropna()
    return float(np.percentile(v, q)) if len(v) else float("nan")


def _suma(v: pd.Series) -> float:
    v = pd.to_numeric(v, errors="coerce").dropna()
    return float(v.sum()) if len(v) else float("nan")


def censa(horas: pd.DataFrame, nombre: str, tol: float = TOL_REPARTO) -> dict:
    """El censo de UN almacen, a partir de su tabla de horas.

    Hora de mercado es la resuelta o la que quedo sin resolver por un motivo
    distinto de «sin mercado esa hora» (faltaba un lado), igual que en
    `compara_arranque.py`.

    Cada columna que el almacen no trae sale con su bandera `tiene_*` en falso,
    sus estadisticas en `nan` y sus contadores en cero, y `imprime` lo avisa:
    un cero que significa «no medido» no puede leerse como una medicion.

    Falla en voz alta si la tabla no trae lo minimo (`hora`, `resuelta`,
    `motivo`) o si trae horas repetidas, que es lo que arruinaria cualquier
    recuento sin avisar (C-173).
    """
    if not (math.isfinite(tol) and tol > 0):
        raise ValueError(f"tol={tol!r}; tiene que ser finita y positiva")
    faltan = {"hora", "resuelta", "motivo"} - set(horas.columns)
    if faltan:
        raise ValueError(f"la tabla de horas de {nombre} no trae "
                         f"{sorted(faltan)}")
    d = horas.copy()
    d["hora"] = d["hora"].astype(int)
    if d["hora"].duplicated().any():
        repetidas = sorted(d.loc[d["hora"].duplicated(), "hora"].unique())
        raise ValueError(f"la tabla de horas de {nombre} trae horas "
                         f"repetidas: {repetidas[:10]}")
    d["resuelta"] = d["resuelta"].astype("boolean").fillna(False).astype(bool)
    d["motivo"] = d["motivo"].fillna("").astype(str)
    d.loc[d["resuelta"], "motivo"] = ""
    de_mercado = d["resuelta"] | ((d["motivo"] != "")
                                  & (d["motivo"] != SIN_MERCADO))
    res = d[d["resuelta"]]

    fila = dict(
        nombre=nombre,
        horas=int(len(d)),
        horas_mercado=int(de_mercado.sum()),
        resueltas=int(d["resuelta"].sum()),
        sin_resolver=int((de_mercado & ~d["resuelta"]).sum()),
    )

    # ── por que paro cada hora ────────────────────────────────────────────
    paradas = Counter({p: 0 for p in PARADAS})
    fila["tiene_parada"] = "parada_acoplado" in res.columns
    if fila["tiene_parada"]:
        paradas.update(res["parada_acoplado"].fillna("").astype(str)
                       .replace("", "sin anotar").tolist())
    for p in PARADAS:
        fila[f"parada_{p}"] = int(paradas.get(p, 0))
    fila["parada_otras"] = int(sum(n for m, n in paradas.items()
                                   if m not in PARADAS))

    # ── los dos residuos ──────────────────────────────────────────────────
    for clave, columna in (("precio", "residuo"),
                           ("reparto", "residuo_reparto")):
        v = (res[columna] if columna in res.columns
             else pd.Series(dtype=float))
        fila[f"residuo_{clave}_mediana"] = _percentil(v, 50)
        fila[f"residuo_{clave}_p90"] = _percentil(v, 90)
        fila[f"residuo_{clave}_max"] = _percentil(v, 100)
    # Las horas que pararon con la energia todavia cambiando de manos. Es la
    # cifra de H-86: con el criterio de hoy no son un fallo, son horas que el
    # criterio no mira.
    fila["tiene_residuo_reparto"] = "residuo_reparto" in res.columns
    if fila["tiene_residuo_reparto"]:
        rr = pd.to_numeric(res["residuo_reparto"], errors="coerce")
        fila["horas_reparto_en_marcha"] = int((rr > tol).sum())
    else:
        fila["horas_reparto_en_marcha"] = 0

    # ── el horizonte y el costo ───────────────────────────────────────────
    if "horizonte_usado" in res.columns:
        hu = pd.to_numeric(res["horizonte_usado"], errors="coerce")
        fila["horizonte_mediana"] = _percentil(hu, 50)
        fila["horizonte_max"] = _percentil(hu, 100)
    else:
        fila["horizonte_mediana"] = float("nan")
        fila["horizonte_max"] = float("nan")
    for columna in COSTO:
        hay = columna in res.columns
        fila[f"tiene_{columna}"] = hay
        v = res[columna] if hay else pd.Series(dtype=float)
        fila[f"{columna}_mediana"] = _percentil(v, 50)
        fila[f"{columna}_p90"] = _percentil(v, 90)
        fila[f"{columna}_max"] = _percentil(v, 100)
        fila[f"{columna}_suma"] = _suma(v)

    fila["motivos_sin_resolver"] = dict(Counter(
        d.loc[de_mercado & ~d["resuelta"], "motivo"].tolist()))
    return fila


# ── lectura, escritura e informe ──────────────────────────────────────────
def carga(almacen, cobertura: str = "m1") -> pd.DataFrame:
    """La tabla de horas de un almacen, con `core.almacen.lee` (necesita
    pyarrow)."""
    from core.almacen import lee
    return lee(almacen, cobertura, "horas")


def almacenes(carpeta, cobertura: str = "m1") -> list:
    """Los almacenes de una carpeta de campana, en orden: cada subcarpeta
    `<caso>_<configuracion>` que tenga dentro un `almacen/<cobertura>/horas`.
    Devuelve pares (nombre, ruta del almacen)."""
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        raise FileNotFoundError(f"no existe la carpeta de la campana: "
                                f"{carpeta}")
    salida = []
    for sub in sorted(p for p in carpeta.iterdir() if p.is_dir()):
        for alm in (sub / "almacen", sub):
            if (alm / cobertura / "horas").is_dir():
                salida.append((sub.name, alm))
                break
    return salida


def _num(v, fmt=".4g") -> str:
    return ("no medido" if v is None
            or (isinstance(v, float) and math.isnan(v)) else format(v, fmt))


def imprime(filas: list, tol: float) -> None:
    p = lambda *a: print(*a, flush=True)  # noqa: E731
    p("=== Censo de la campana de convergencia (H-86, D47) ===")
    p(f"  una hora cuenta como «el reparto seguia moviendose» si su residuo "
      f"del reparto pasa de {tol:g}")
    if any(f.get("tiene_segundos") for f in filas):
        p("  los segundos son TIEMPO DE PARED del trabajador, con varias horas "
          "corriendo a la vez: valen para comparar configuraciones de esta "
          "misma campana, no para leer lo que costaria una hora sola, y su "
          "suma no es la duracion de la corrida. La cifra que no depende de la "
          "maquina es `evaluaciones`")
    for f in filas:
        p("")
        p(f"  --- {f['nombre']}")
        p(f"      horas de la ventana {f['horas']}, de mercado "
          f"{f['horas_mercado']}, resueltas {f['resueltas']}, sin resolver "
          f"{f['sin_resolver']}")
        for motivo, n in sorted(f["motivos_sin_resolver"].items()):
            p(f"           {n} x {motivo}")
        if f["tiene_parada"]:
            p("      motivo de parada: "
              + ", ".join(f"{m} {f['parada_' + m]}" for m in PARADAS)
              + (f", otras {f['parada_otras']}" if f["parada_otras"] else ""))
        else:
            p("      motivo de parada: NO MEDIDO. Este almacen no trae la "
              "columna `parada_acoplado`, que solo se escribe con la parada "
              "por estacionario activa; los contadores valen cero porque no "
              "hay nada que contar, no porque ninguna hora parara asi")
        p(f"      horizonte usado: mediana {_num(f['horizonte_mediana'])}, "
          f"maximo {_num(f['horizonte_max'])}")
        for clave in ("precio", "reparto"):
            p(f"      residuo del {clave}: mediana "
              f"{_num(f['residuo_' + clave + '_mediana'])}, p90 "
              f"{_num(f['residuo_' + clave + '_p90'])}, maximo "
              f"{_num(f['residuo_' + clave + '_max'])}")
        if f["tiene_residuo_reparto"]:
            p(f"      horas que pararon con el reparto en marcha: "
              f"{f['horas_reparto_en_marcha']} de {f['resueltas']} resueltas")
        else:
            p("      horas con el reparto en marcha: NO MEDIDO. Este almacen "
              "no trae la columna `residuo_reparto`, es anterior a D47, y el "
              "recuento no se puede hacer sin volver a correrlo")
        for columna, unidad in (("segundos", "(s)"), ("evaluaciones", "")):
            if f[f"tiene_{columna}"]:
                p(f"      {columna} por hora {unidad}: mediana "
                  f"{_num(f[columna + '_mediana'])}, p90 "
                  f"{_num(f[columna + '_p90'])}, maximo "
                  f"{_num(f[columna + '_max'])}, suma "
                  f"{_num(f[columna + '_suma'], '.6g')}")
            else:
                p(f"      {columna} por hora: NO MEDIDO. Este almacen no trae "
                  f"la columna `{columna}`, es anterior a D47; el coste en "
                  f"tiempo se lee mientras tanto en el registro de la corrida")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Censa los almacenes de la campana de convergencia "
                    "(H-86, D47). Es una medicion: sale con 0 sea cual sea "
                    "el resultado.")
    ap.add_argument("carpeta", nargs="?", default=None,
                    help="carpeta de la campana, con una subcarpeta por "
                         "corrida")
    ap.add_argument("--almacen", action="append", default=[],
                    metavar="NOMBRE=RUTA",
                    help="un almacen suelto, repetible; alternativa a la "
                         "carpeta")
    ap.add_argument("--cobertura", default="m1")
    ap.add_argument("--tol", type=float, default=TOL_REPARTO,
                    help="umbral del residuo del reparto con que se cuenta "
                         "una hora como todavia en marcha")
    ap.add_argument("--salida", default=None,
                    help="carpeta del CSV del censo; sin ella no se escribe")
    args = ap.parse_args(argv)
    if not (math.isfinite(args.tol) and args.tol > 0):
        ap.error("--tol tiene que ser un numero finito y positivo")

    fuentes = []
    for par in args.almacen:
        if "=" not in par:
            ap.error(f"--almacen {par!r} no tiene la forma NOMBRE=RUTA")
        nombre, ruta = par.split("=", 1)
        fuentes.append((nombre, Path(ruta)))
    if args.carpeta:
        fuentes.extend(almacenes(args.carpeta, args.cobertura))
    if not fuentes:
        ap.error("no hay nada que censar: pasa la carpeta de la campana o "
                 "al menos un --almacen NOMBRE=RUTA")

    filas = [censa(carga(ruta, args.cobertura), nombre, args.tol)
             for nombre, ruta in fuentes]
    imprime(filas, args.tol)

    if args.salida:
        salida = Path(args.salida)
        salida.mkdir(parents=True, exist_ok=True)
        ruta = salida / "censo_convergencia.csv"
        tabla = pd.DataFrame([{k: v for k, v in f.items()
                               if k != "motivos_sin_resolver"} for f in filas])
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write(f"# censo_convergencia: umbral del reparto {args.tol:g}; "
                    f"cobertura {args.cobertura}; las columnas `tiene_*` "
                    f"dicen si esa medida existe en el almacen\n")
            tabla.to_csv(f, index=False)
        print(f"\n  censo: {ruta}", flush=True)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
