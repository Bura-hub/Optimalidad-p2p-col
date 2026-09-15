"""
Compara dos almacenes de la misma ventana, uno con cada arranque del
solucionador acoplado (H-85; D45 y D46). 2026-09-15.

QUE MIDE. La matriz de trece corridas dejo nueve horas sin resolver por el
arranque del acoplado (H-85): reparte la oferta de cada vendedor a partes
iguales y un comprador de deficit pequeno arranca con varias veces lo que
necesita. El arranque factible (`--arranque-acoplado factible`) las resuelve,
pero puede mover tambien las horas que ya resolvian: en la hora 4184 de E4 el
equilibrio no fija el reparto del precio entre dos compradores, y el arranque
elige un punto de esa direccion. Sobre la misma ventana corrida con los dos
arranques, esta herramienta dice:

  - cuantas horas de mercado hay y cuantas quedaron sin resolver, con su
    motivo, en cada almacen;
  - cuantas horas cambian: alguna entrega por comprador no coincide (ver LAS
    TOLERANCIAS, abajo) o algun precio por comprador difiere en mas de 1e-3
    (COP/kWh), o la hora resolvio con un solo arranque;
  - el maximo y la media de la diferencia de precio por comprador (COP/kWh),
    de entrega (kWh) y de pago (COP), y el pago de cada comprador sumado
    sobre la ventana;
  - las horas de PRECIO INDETERMINADO (D46): las entregas de todos los
    compradores coinciden pero algun precio por comprador difiere en mas de
    1e-3 (COP/kWh). Para ellas, cuanto se mueve el pago de cada comprador y
    si la suma de lo que pagan los compradores se conserva.

Es una medicion, no una compuerta: sale con 0 sea cual sea el resultado.
Solo sale con otro codigo si no puede medir (un almacen ausente, dos
ventanas distintas, una tabla que no trae lo que se espera).

DE DONDE SALE CADA NUMERO (`core/almacen.py`):
  horas   una fila por hora: `resuelta` y `motivo`. Hora de mercado es la
          resuelta o la que quedo sin resolver por un motivo distinto de
          «sin mercado esa hora» (faltaba un lado).
  flujos  una fila por hora, vendedor y comprador, de las horas resueltas:
          `kwh` es la energia del par y `precio` el precio del comprador, el
          mismo para todos sus vendedores. La entrega de un comprador es la
          suma de `kwh` sobre sus vendedores y su pago, precio por entrega.

LAS TOLERANCIAS, y por que la de las entregas es combinada. El almacen
guarda los numeros en precision sencilla (float32): cerca de 20 (kWh) su paso
es de unos 1,9e-6 (kWh), de modo que dos entregas iguales en doble precision
pueden diferir en un paso al guardarse, y con una tolerancia absoluta de
1e-6 una hora de precio indeterminado, justo lo que D46 quiere contar,
saldria como «entregas distintas» por un redondeo. Por eso dos entregas de
un comprador COINCIDEN si

    |b - a| <= max(tol_kwh, tol_rel * max(|a|, |b|))

con tol_kwh = 1e-4 (kWh) y tol_rel = 1e-5 (unas 84 unidades de redondeo de
float32, que cubren tambien los casos de la matriz con energias de cientos
de kWh). La del precio sigue absoluta, 1e-3 (COP/kWh): el paso de float32
cerca de 400 (COP/kWh) es de unos 3e-5. Las tres se cambian con `--tol-kwh`,
`--tol-rel` y `--tol-precio`; el resumen y la primera linea de cada CSV dicen
cuales se usaron, para poder releer el recuento de D46.

LA SUMA QUE SE CONSERVA. En una hora de precio indeterminado, «la suma de lo
que pagan los compradores se conserva» con el mismo criterio combinado: su
diferencia (COP) no pasa de max(tol_precio * E, tol_rel * max(|A|, |B|)),
con E la energia de la hora (kWh), es decir lo que moveria la suma un cambio
de precio por debajo de su tolerancia, y A y B la suma de los pagos con cada
arranque. Se informa tambien la diferencia de la suma de los precios, que en
la hora 4184 es la que se conserva (H-85: dos precios se mueven +-0,41 y su
suma no cambia), aunque la de los pagos no, porque los dos compradores
reciben energias distintas.

LOS CSV llevan en su primera linea, precedida de «#», las tolerancias usadas.
Se leen con `pd.read_csv(ruta, comment="#")`.

La funcion `compara` es pura: recibe los DataFrame y no lee parquet, de modo
que se prueba sin pyarrow (`tests/test_compara_arranque.py`). `carga` lee el
almacen con `core.almacen.lee`, que si lo necesita.

Uso, desde la raiz del repositorio:
    python -u reformateo/documento/scripts/sonda/compara_arranque.py ALMACEN_IGUALES ALMACEN_FACTIBLE --cobertura m1 --etiqueta E4 --salida SALIDAS_SERVIDOR/arranque

El primer almacen es el del arranque de siempre («iguales», A) y el segundo
el del factible (B); las diferencias son B menos A.
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

# Las tolerancias (ver LAS TOLERANCIAS en el docstring). La de las entregas es
# combinada porque el almacen guarda en float32.
TOL_KWH = 1e-4        # (kWh): parte absoluta, entregas por comprador
TOL_REL = 1e-5        # parte relativa, entregas y suma de pagos
TOL_PRECIO = 1e-3     # (COP/kWh): precio por comprador
SIN_MERCADO = "sin mercado esa hora"

# Las clases de una hora, en el orden en que se imprimen.
CLASES = ("igual", "precio_indeterminado", "entregas_distintas",
          "compradores_distintos", "resuelta_solo_en_a", "resuelta_solo_en_b",
          "sin_resolver_en_las_dos", "sin_mercado")
# Las que cuentan como «el resultado cambia».
CAMBIAN = ("precio_indeterminado", "entregas_distintas",
           "compradores_distintos", "resuelta_solo_en_a",
           "resuelta_solo_en_b")


# ── la tabla de horas ─────────────────────────────────────────────────────
def _horas(horas: pd.DataFrame, nombre: str) -> pd.DataFrame:
    """Hora, fecha, si resolvio, su motivo y si fue hora de mercado."""
    faltan = {"hora", "fecha", "resuelta", "motivo"} - set(horas.columns)
    if faltan:
        raise ValueError(f"la tabla de horas de {nombre} no trae "
                         f"{sorted(faltan)}")
    d = horas[["hora", "fecha", "resuelta", "motivo"]].copy()
    d["hora"] = d["hora"].astype(int)
    if d["hora"].duplicated().any():
        repetidas = sorted(d.loc[d["hora"].duplicated(), "hora"].unique())
        raise ValueError(f"la tabla de horas de {nombre} trae horas "
                         f"repetidas: {repetidas[:10]}")
    d["resuelta"] = d["resuelta"].astype("boolean").fillna(False).astype(bool)
    d["motivo"] = d["motivo"].fillna("").astype(str)
    d.loc[d["resuelta"], "motivo"] = ""
    d["de_mercado"] = d["resuelta"] | ((d["motivo"] != "")
                                       & (d["motivo"] != SIN_MERCADO))
    return d.sort_values("hora").reset_index(drop=True)


# ── la tabla de flujos, por comprador ─────────────────────────────────────
def por_comprador(flujos: pd.DataFrame, resueltas, nombre: str) -> pd.DataFrame:
    """Entrega (kWh), precio (COP/kWh) y pago (COP) de cada comprador en cada
    hora resuelta, en doble precision. Falla en voz alta si una hora resuelta
    no trae flujos, si hay un valor no finito o si el precio de un comprador
    no es el mismo para todos sus vendedores."""
    columnas = ["hora", "comprador", "entrega", "precio", "pago"]
    resueltas = set(int(k) for k in resueltas)
    if flujos is None or len(flujos) == 0:
        if resueltas:
            raise ValueError(f"{nombre}: {len(resueltas)} horas resueltas y "
                             f"ningun flujo")
        return pd.DataFrame(columns=columnas)
    faltan = {"hora", "comprador", "kwh", "precio"} - set(flujos.columns)
    if faltan:
        raise ValueError(f"la tabla de flujos de {nombre} no trae "
                         f"{sorted(faltan)}")
    f = flujos[["hora", "comprador", "kwh", "precio"]].copy()
    f["hora"] = f["hora"].astype(int)
    f = f[f["hora"].isin(resueltas)]
    f["kwh"] = f["kwh"].astype("float64")
    f["precio"] = f["precio"].astype("float64")
    if not (np.all(np.isfinite(f["kwh"])) and np.all(np.isfinite(f["precio"]))):
        raise ValueError(f"{nombre}: la tabla de flujos trae valores no "
                         f"finitos en horas resueltas")
    sin_flujos = resueltas - set(f["hora"].unique())
    if sin_flujos:
        raise ValueError(f"{nombre}: horas resueltas sin flujos: "
                         f"{sorted(sin_flujos)[:10]}")
    d = (f.groupby(["hora", "comprador"], sort=True)
          .agg(entrega=("kwh", "sum"), precio=("precio", "first"),
               p_min=("precio", "min"), p_max=("precio", "max"))
          .reset_index())
    if len(d) and float((d["p_max"] - d["p_min"]).max()) > 0.0:
        raise ValueError(f"{nombre}: el precio de algun comprador no es el "
                         f"mismo para todos sus vendedores")
    d["pago"] = d["precio"] * d["entrega"]
    return d[columnas]


# ── la comparacion, pura ──────────────────────────────────────────────────
def _comprueba_tolerancias(tol_kwh, tol_rel, tol_precio) -> None:
    for nombre, v in (("tol_kwh", tol_kwh), ("tol_precio", tol_precio)):
        if not (math.isfinite(v) and v > 0):
            raise ValueError(f"{nombre}={v!r}; tiene que ser finita y "
                             f"positiva")
    if not (math.isfinite(tol_rel) and tol_rel >= 0):
        raise ValueError(f"tol_rel={tol_rel!r}; tiene que ser finita y no "
                         f"negativa (0 deja solo la parte absoluta)")


def compara(horas_a: pd.DataFrame, flujos_a: pd.DataFrame,
            horas_b: pd.DataFrame, flujos_b: pd.DataFrame,
            tol_kwh: float = TOL_KWH, tol_precio: float = TOL_PRECIO,
            tol_rel: float = TOL_REL):
    """Compara el almacen A (arranque de siempre) con el B (factible).

    Dos entregas de un comprador coinciden si
    |b - a| <= max(tol_kwh, tol_rel * max(|a|, |b|)); dos precios, si
    |b - a| <= tol_precio (ver LAS TOLERANCIAS en el docstring del modulo).

    Devuelve `(tabla, detalle, resumen)`:
      tabla    una fila por hora de la ventana, con su clase (`CLASES`), si
               el resultado cambia, si es de precio indeterminado (D46) y las
               diferencias medidas (B menos A);
      detalle  una fila por hora y comprador de las horas resueltas con los
               dos arranques: entrega, precio y pago de cada uno, su
               diferencia y el umbral de la entrega de ese comprador;
      resumen  un diccionario con los conteos, las estadisticas y las
               tolerancias usadas.
    """
    _comprueba_tolerancias(tol_kwh, tol_rel, tol_precio)
    ha = _horas(horas_a, "A")
    hb = _horas(horas_b, "B")
    llaves_a = set(zip(ha["hora"], pd.to_datetime(ha["fecha"])))
    llaves_b = set(zip(hb["hora"], pd.to_datetime(hb["fecha"])))
    if llaves_a != llaves_b:
        raise ValueError(
            f"los dos almacenes no cubren la misma ventana: "
            f"{len(llaves_a - llaves_b)} horas solo en A y "
            f"{len(llaves_b - llaves_a)} solo en B")

    h = ha.merge(hb.drop(columns=["fecha"]), on="hora",
                 suffixes=("_a", "_b"))
    ca = por_comprador(flujos_a, ha.loc[ha["resuelta"], "hora"], "A")
    cb = por_comprador(flujos_b, hb.loc[hb["resuelta"], "hora"], "B")
    ambas = set(h.loc[h["resuelta_a"] & h["resuelta_b"], "hora"])

    det = ca[ca["hora"].isin(ambas)].merge(
        cb[cb["hora"].isin(ambas)], on=["hora", "comprador"], how="outer",
        suffixes=("_a", "_b"), indicator=True)
    for q in ("entrega", "precio", "pago"):
        det[f"dif_{q}"] = det[f"{q}_b"] - det[f"{q}_a"]
    det["en_los_dos"] = det["_merge"] == "both"
    det = det.drop(columns=["_merge"]).sort_values(["hora", "comprador"])
    # La tolerancia combinada de la entrega de cada comprador: absoluta o
    # relativa a la mayor de sus dos entregas, la que sea mayor.
    det["umbral_entrega_kwh"] = np.maximum(
        tol_kwh, tol_rel * np.maximum(det["entrega_a"].abs(),
                                      det["entrega_b"].abs()))
    det["excede_entrega"] = (det["dif_entrega"].abs()
                             > det["umbral_entrega_kwh"])

    columnas_hora = ["compradores", "impares", "exceden_entrega",
                     "max_dif_entrega_kwh", "max_dif_precio",
                     "max_dif_pago_cop", "suma_pago_a", "suma_pago_b",
                     "dif_suma_pago_cop", "umbral_suma_pago_cop",
                     "dif_suma_precio", "energia_kwh"]
    if len(det):
        g = det.assign(
            impar=~det["en_los_dos"],
            ae=det["dif_entrega"].abs(), ap=det["dif_precio"].abs(),
            ag=det["dif_pago"].abs()).groupby("hora")
        ph = pd.DataFrame({
            "compradores": g.size(),
            "impares": g["impar"].sum().astype(int),
            "exceden_entrega": g["excede_entrega"].sum().astype(int),
            "max_dif_entrega_kwh": g["ae"].max(),
            "max_dif_precio": g["ap"].max(),
            "max_dif_pago_cop": g["ag"].max(),
            "suma_pago_a": g["pago_a"].sum(),
            "suma_pago_b": g["pago_b"].sum(),
            "dif_suma_pago_cop": g["dif_pago"].sum(),
            "dif_suma_precio": g["dif_precio"].sum(),
            "energia_kwh": g["entrega_a"].sum(),
        }).reset_index()
        # LA SUMA QUE SE CONSERVA, con el mismo criterio combinado: lo que
        # moveria la suma un cambio de precio por debajo de su tolerancia, o
        # la parte relativa de la mayor de las dos sumas, la que sea mayor.
        ph["umbral_suma_pago_cop"] = np.maximum(
            tol_precio * ph["energia_kwh"],
            tol_rel * np.maximum(ph["suma_pago_a"].abs(),
                                 ph["suma_pago_b"].abs()))
    else:
        ph = pd.DataFrame(columns=["hora"] + columnas_hora)
    t = h.merge(ph, on="hora", how="left")

    def clase(r) -> str:
        if r["resuelta_a"] and r["resuelta_b"]:
            if r["impares"] > 0:
                return "compradores_distintos"
            if r["exceden_entrega"] > 0:
                return "entregas_distintas"
            if r["max_dif_precio"] > tol_precio:
                return "precio_indeterminado"
            return "igual"
        if r["resuelta_a"]:
            return "resuelta_solo_en_a"
        if r["resuelta_b"]:
            return "resuelta_solo_en_b"
        if r["de_mercado_a"] or r["de_mercado_b"]:
            return "sin_resolver_en_las_dos"
        return "sin_mercado"

    t["clase"] = (t.apply(clase, axis=1) if len(t)
                  else pd.Series(dtype=object))
    t["cambia"] = t["clase"].isin(CAMBIAN)
    t["indeterminada"] = t["clase"] == "precio_indeterminado"
    # D46: en la hora de precio indeterminado, si la suma de lo que pagan los
    # compradores se conserva (ver el docstring del modulo). Vacio en las
    # demas horas.
    t["conserva_pago"] = pd.Series(pd.NA, index=t.index, dtype="boolean")
    ind = t["indeterminada"]
    t.loc[ind, "conserva_pago"] = (t.loc[ind, "dif_suma_pago_cop"].abs()
                                   <= t.loc[ind, "umbral_suma_pago_cop"])
    tabla = t[["hora", "fecha", "resuelta_a", "motivo_a", "resuelta_b",
               "motivo_b", "clase", "cambia", "indeterminada",
               "conserva_pago"] + columnas_hora]

    det = det.merge(t[["hora", "fecha", "clase"]], on="hora", how="left")
    detalle = det[["hora", "fecha", "comprador", "clase", "entrega_a",
                   "entrega_b", "dif_entrega", "umbral_entrega_kwh",
                   "excede_entrega", "precio_a", "precio_b",
                   "dif_precio", "pago_a", "pago_b", "dif_pago",
                   "en_los_dos"]].reset_index(drop=True)
    resumen = _resumen(ha, hb, tabla, detalle)
    resumen["tolerancias"] = dict(tol_kwh=float(tol_kwh),
                                  tol_rel=float(tol_rel),
                                  tol_precio=float(tol_precio))
    return tabla, detalle, resumen


def texto_tolerancias(tol: dict) -> str:
    """Las tolerancias usadas, en una linea, para el resumen y los CSV."""
    return (f"entrega: |dif| <= max({tol['tol_kwh']:g} (kWh), "
            f"{tol['tol_rel']:g} x max(|a|, |b|)); precio: |dif| <= "
            f"{tol['tol_precio']:g} (COP/kWh); suma de pagos: |dif| <= "
            f"max({tol['tol_precio']:g} x energia de la hora, "
            f"{tol['tol_rel']:g} x max(|A|, |B|))")


def _estadistica(v: pd.Series) -> tuple:
    """Maximo y media del valor absoluto; NaN si no hay datos."""
    v = v.dropna().abs()
    if not len(v):
        return float("nan"), float("nan")
    return float(v.max()), float(v.mean())


def _resumen(ha, hb, tabla, detalle) -> dict:
    sin_a = ha[ha["de_mercado"] & ~ha["resuelta"]]
    sin_b = hb[hb["de_mercado"] & ~hb["resuelta"]]
    pares = detalle[detalle["en_los_dos"]]
    ventana = (pares.groupby("comprador")[["pago_a", "pago_b", "dif_pago"]]
               .sum())
    ind_horas = set(tabla.loc[tabla["indeterminada"], "hora"])
    pares_ind = pares[pares["hora"].isin(ind_horas)]
    ind_pago = (pares_ind.assign(abs_dif=pares_ind["dif_pago"].abs())
                .groupby("comprador")
                .agg(dif_pago_suma=("dif_pago", "sum"),
                     dif_pago_max_abs=("abs_dif", "max"),
                     horas=("hora", "nunique")))
    ind = tabla[tabla["indeterminada"]]
    clases = Counter({c: 0 for c in CLASES})
    clases.update(tabla["clase"].tolist())
    return dict(
        horas=int(len(tabla)),
        mercado_a=int(ha["de_mercado"].sum()),
        mercado_b=int(hb["de_mercado"].sum()),
        resueltas_a=int(ha["resuelta"].sum()),
        resueltas_b=int(hb["resuelta"].sum()),
        sin_resolver_a=dict(Counter(sin_a["motivo"].tolist())),
        sin_resolver_b=dict(Counter(sin_b["motivo"].tolist())),
        horas_sin_resolver_a=sorted(int(k) for k in sin_a["hora"]),
        horas_sin_resolver_b=sorted(int(k) for k in sin_b["hora"]),
        resueltas_en_las_dos=int((tabla["resuelta_a"]
                                  & tabla["resuelta_b"]).sum()),
        clases={c: int(clases[c]) for c in CLASES},
        cambian=int(tabla["cambia"].sum()),
        indeterminadas=int(tabla["indeterminada"].sum()),
        indeterminadas_conservan_pago=int(ind["conserva_pago"].sum()),
        dif_precio=_estadistica(pares["dif_precio"]),
        dif_entrega=_estadistica(pares["dif_entrega"]),
        dif_pago=_estadistica(pares["dif_pago"]),
        dif_suma_pago_indeterminadas=_estadistica(ind["dif_suma_pago_cop"]),
        pago_ventana=ventana,
        pago_indeterminadas=ind_pago,
    )


# ── lectura, escritura e informe ──────────────────────────────────────────
def carga(almacen, cobertura: str = "m1"):
    """Las tablas de horas y flujos de un almacen, con `core.almacen.lee`
    (necesita pyarrow). Un almacen sin ninguna hora resuelta no tiene partes
    de flujos: se devuelve una tabla vacia solo en ese caso."""
    from core.almacen import lee
    horas = lee(almacen, cobertura, "horas")
    try:
        flujos = lee(almacen, cobertura, "flujos")
    except FileNotFoundError:
        if horas["resuelta"].astype("boolean").fillna(False).any():
            raise
        flujos = pd.DataFrame(columns=["hora", "comprador", "kwh", "precio"])
    return horas, flujos


def escribe(tabla, detalle, salida, etiqueta: str = "",
            tolerancias: dict = None) -> tuple:
    """El CSV hora a hora y el detalle por comprador, en `salida`. Con
    `tolerancias` (el diccionario del resumen), la primera linea de cada CSV
    las dice, precedida de «#»: se leen con `pd.read_csv(..., comment="#")`."""
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    sufijo = f"_{etiqueta}" if etiqueta else ""
    r1 = salida / f"compara_arranque{sufijo}.csv"
    r2 = salida / f"compara_arranque{sufijo}_compradores.csv"
    for ruta, d in ((r1, tabla), (r2, detalle)):
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            if tolerancias is not None:
                f.write(f"# compara_arranque {etiqueta}: tolerancias "
                        f"{texto_tolerancias(tolerancias)}\n")
            d.to_csv(f, index=False)
    return r1, r2


def _num(v, fmt=".6g") -> str:
    return "sin datos" if v is None or (isinstance(v, float)
                                        and math.isnan(v)) else format(v, fmt)


def imprime(r: dict, etiqueta: str = "") -> None:
    p = lambda *a: print(*a, flush=True)  # noqa: E731
    p(f"=== Arranque del acoplado{' ' + etiqueta if etiqueta else ''}: "
      f"A = iguales (el de siempre), B = factible (H-85; D45, D46) ===")
    p(f"  tolerancias: {texto_tolerancias(r['tolerancias'])}")
    p(f"  horas de la ventana: {r['horas']}")
    for lado in ("a", "b"):
        p(f"  {lado.upper()}: {r['mercado_' + lado]} horas de mercado, "
          f"{r['resueltas_' + lado]} resueltas, "
          f"{len(r['horas_sin_resolver_' + lado])} sin resolver")
        for motivo, n in sorted(r["sin_resolver_" + lado].items()):
            p(f"       {n} x {motivo}")
        if r["horas_sin_resolver_" + lado]:
            p(f"       horas: {r['horas_sin_resolver_' + lado][:20]}")
    p(f"  resueltas con los dos arranques: {r['resueltas_en_las_dos']}")
    p("  clases (con las tolerancias de arriba):")
    for c, n in r["clases"].items():
        p(f"       {c:<24s} {n}")
    p(f"  horas cuyo resultado cambia: {r['cambian']}")
    for nombre, clave, u in (("precio por comprador", "dif_precio", "COP/kWh"),
                             ("entrega por comprador", "dif_entrega", "kWh"),
                             ("pago por comprador y hora", "dif_pago", "COP")):
        mx, md = r[clave]
        p(f"  diferencia de {nombre} ({u}): maxima {_num(mx)}, media "
          f"{_num(md)}")
    if len(r["pago_ventana"]):
        p("  pago de cada comprador sumado sobre las horas resueltas con los "
          "dos (COP):")
        for comp, f in r["pago_ventana"].iterrows():
            p(f"       {comp:<10s} A {f['pago_a']:.2f}   B {f['pago_b']:.2f}"
              f"   B-A {f['dif_pago']:+.2f}")
    p(f"  D46, horas de precio indeterminado: {r['indeterminadas']}; "
      f"conservan la suma de los pagos: "
      f"{r['indeterminadas_conservan_pago']}")
    if r["indeterminadas"]:
        mx, md = r["dif_suma_pago_indeterminadas"]
        p(f"       diferencia de la suma de pagos por hora (COP): maxima "
          f"{_num(mx)}, media {_num(md)}")
        for comp, f in r["pago_indeterminadas"].iterrows():
            p(f"       {comp:<10s} su pago se mueve {f['dif_pago_suma']:+.2f}"
              f" (COP) en {int(f['horas'])} horas; como mucho "
              f"{f['dif_pago_max_abs']:.2f} en una")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Compara dos almacenes de la misma ventana, uno con cada "
                    "arranque del acoplado (H-85; D45 y D46). Es una "
                    "medicion: sale con 0 sea cual sea el resultado.")
    ap.add_argument("iguales", help="almacen del arranque de siempre (A)")
    ap.add_argument("factible", help="almacen del arranque factible (B)")
    ap.add_argument("--cobertura", default="m1")
    ap.add_argument("--etiqueta", default="",
                    help="nombre del caso, para el informe y el CSV (E0, E4)")
    ap.add_argument("--salida", default=None,
                    help="carpeta del CSV hora a hora; sin ella no se escribe")
    ap.add_argument("--tol-kwh", dest="tol_kwh", type=float, default=TOL_KWH,
                    help="parte absoluta de la tolerancia de la entrega por "
                         "comprador (kWh)")
    ap.add_argument("--tol-rel", dest="tol_rel", type=float, default=TOL_REL,
                    help="parte relativa de la tolerancia de la entrega por "
                         "comprador y de la suma de los pagos (0 la quita)")
    ap.add_argument("--tol-precio", dest="tol_precio", type=float,
                    default=TOL_PRECIO,
                    help="tolerancia del precio por comprador (COP/kWh)")
    args = ap.parse_args(argv)
    for nombre, v in (("--tol-kwh", args.tol_kwh),
                      ("--tol-precio", args.tol_precio)):
        if not (math.isfinite(v) and v > 0):
            ap.error(f"{nombre} tiene que ser un numero finito y positivo")
    if not (math.isfinite(args.tol_rel) and args.tol_rel >= 0):
        ap.error("--tol-rel tiene que ser un numero finito y no negativo")

    ha, fa = carga(args.iguales, args.cobertura)
    hb, fb = carga(args.factible, args.cobertura)
    tabla, detalle, resumen = compara(ha, fa, hb, fb, tol_kwh=args.tol_kwh,
                                      tol_precio=args.tol_precio,
                                      tol_rel=args.tol_rel)
    imprime(resumen, args.etiqueta)
    if args.salida:
        r1, r2 = escribe(tabla, detalle, args.salida, args.etiqueta,
                         resumen["tolerancias"])
        print(f"  hora a hora:   {r1}", flush=True)
        print(f"  por comprador: {r2}", flush=True)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
