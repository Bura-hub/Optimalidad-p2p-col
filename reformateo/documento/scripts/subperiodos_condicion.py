"""Subperíodos por condición operativa (actividad 3.2), sin volver a simular.

Punto C6 de la preparación antes de redactar (2026-09-27); C-211.

La propuesta pide evaluar «diferentes subperíodos —semanas, días— con
condiciones operativas diversas —alta o baja generación solar, picos o valles
de demanda, precios de bolsa extremos o típicos—». D72 fija que la comparación
de dinero con la regulación solo está bien definida por mes (por debajo del mes
depende de cómo se anota en cada hora el crédito del cupo mensual), de modo que
este guion separa dos preguntas:

1. MESES POR CONDICIÓN (la comparación regulatoria): cada mes de cada caso se
   clasifica por la generación, la demanda y el precio medio de bolsa de la
   comunidad (tercil bajo, medio y alto dentro del caso), y se leen P2P − C1,
   P2P − C4 y P2P − C5 del mes, sumando la tabla `escenarios` del almacén.
2. DÍAS POR CONDICIÓN (el comportamiento del propio mercado): cada día se
   clasifica igual y se describen magnitudes que sí están bien definidas por
   hora: energía transada, banda repartida por kWh, parte del vendedor, captura
   agregada y parte de la energía en los regímenes con regla declarada.

Fuentes: almacenes del canon (`agentes`, `horas`, `flujos`, `escenarios`) y la
caché de bolsa corregida `data/precios_bolsa_xm_api.csv` (H-92; precio crudo,
antes del techo PES, solo para clasificar).

Salida en SALIDAS_SERVIDOR/subperiodos_2026-09-27/: meses_condicion.csv,
dias_condicion.csv, resumen_meses.csv, resumen_dias.csv y procedencia.txt.
"""
from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
MATRIZ = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
          / "SALIDAS_SERVIDOR" / "matriz_reposo")
BOLSA = RAIZ / "data" / "precios_bolsa_xm_api.csv"
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "subperiodos_2026-09-27"
CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU"]
DECLARADOS = {"compradores_cortos", "excluidos"}
NIVELES = ["bajo", "medio", "alto"]


def tercil(s: pd.Series) -> pd.Series:
    """Tercil dentro de la serie (bajo, medio, alto), por rango."""
    r = s.rank(method="first")
    return pd.cut(r, 3, labels=NIVELES).astype(str)


def bolsa_diaria() -> pd.Series:
    b = pd.read_csv(BOLSA, encoding="utf-8-sig")
    if not np.isfinite(b["Precio_COP_kWh"].to_numpy()).all():
        raise ValueError("bolsa con valores no finitos")
    b["dia"] = pd.to_datetime(b["Fecha"]).dt.normalize()
    return b.groupby("dia")["Precio_COP_kWh"].mean()


def un_caso(c: str, bd: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    alm = MATRIZ / c / "almacen" / "m1"
    ag = pd.read_parquet(alm / "agentes")
    ho = pd.read_parquet(alm / "horas")
    fl = pd.read_parquet(alm / "flujos")
    es = pd.read_parquet(alm / "escenarios")
    for d, cols in ((ag, ["demanda", "generacion"]), (fl, ["kwh"]),
                    (es, ["valor"])):
        for col in cols:
            if not np.isfinite(d[col].to_numpy()).all():
                raise ValueError(f"{c}: {col} no finito")
    ag["dia"] = ag["fecha"].dt.normalize()
    ho["dia"] = ho["fecha"].dt.normalize()
    fl["dia"] = fl["fecha"].dt.normalize()

    # ── condiciones por día y por mes (comunidad) ────────────────────────
    gd = ag.groupby("dia")[["generacion", "demanda"]].sum()
    gd["bolsa"] = bd.reindex(gd.index)
    if gd["bolsa"].isna().any():
        raise ValueError(f"{c}: días sin precio de bolsa en la caché")
    gd["mes"] = gd.index.strftime("%Y-%m")

    # ── meses: dinero por mecanismo ─────────────────────────────────────
    em = es.groupby(["mes", "escenario"])["valor"].sum().unstack()
    gm = gd.groupby("mes").agg(generacion=("generacion", "sum"),
                               demanda=("demanda", "sum"),
                               bolsa=("bolsa", "mean"))
    m = gm.join(em[["P2P", "C1", "C4", "C5"]])
    m["P2P_menos_C1"] = m["P2P"] - m["C1"]
    m["P2P_menos_C4"] = m["P2P"] - m["C4"]
    m["P2P_menos_C5"] = m["P2P"] - m["C5"]
    for v in ("generacion", "demanda", "bolsa"):
        m[f"t_{v}"] = tercil(m[v])
    m.insert(0, "caso", c)

    # ── días: el propio mercado ─────────────────────────────────────────
    fl["banda"] = fl["prima_vendedor"] + fl["ahorro_comprador"]
    fd = fl.groupby("dia").agg(kwh=("kwh", "sum"), banda=("banda", "sum"),
                               prima=("prima_vendedor", "sum"))
    hm = ho[ho["regimen"].notna()].copy()
    sin_int = hm["regimen"].isin(["sin_mercado", "sin_ganancia"])
    for col in ("volumen", "captura", "excedente_optimo"):
        if not np.isfinite(hm.loc[~sin_int, col].to_numpy()).all():
            raise ValueError(f"{c}: {col} no finito en horas con intercambio")
    # Sin intercambio no hay volumen ni óptimo por construcción: cero explícito.
    hm.loc[sin_int, ["volumen", "excedente_optimo"]] = hm.loc[
        sin_int, ["volumen", "excedente_optimo"]].fillna(0.0)
    opt = hm[hm["excedente_optimo"] > 0]
    cap = (opt.assign(num=opt["captura"] * opt["excedente_optimo"])
           .groupby("dia")[["num", "excedente_optimo"]].sum())
    dec = (hm.assign(dv=np.where(hm["regimen"].isin(DECLARADOS),
                                 hm["volumen"], 0.0))
           .groupby("dia")[["dv", "volumen"]].sum())
    d = gd.join(fd, how="left").join(cap, how="left").join(dec, how="left")
    d[["kwh", "banda", "prima", "dv", "volumen"]] = d[
        ["kwh", "banda", "prima", "dv", "volumen"]].fillna(0.0)
    for v in ("generacion", "demanda", "bolsa"):
        d[f"t_{v}"] = tercil(d[v])
    d.insert(0, "caso", c)
    return m.reset_index(), d.reset_index()


def resume_meses(m: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for v in ("generacion", "demanda", "bolsa"):
        g = m.groupby(["caso", f"t_{v}"]).agg(
            meses=("mes", "size"), P2P_menos_C1=("P2P_menos_C1", "sum"),
            P2P_menos_C4=("P2P_menos_C4", "sum"),
            P2P_menos_C5=("P2P_menos_C5", "sum"),
            meses_P2P_bajo_C4=("P2P_menos_C4", lambda s: int((s < 0).sum())),
            meses_P2P_bajo_C5=("P2P_menos_C5", lambda s: int((s < 0).sum())))
        g = g.reset_index().rename(columns={f"t_{v}": "nivel"})
        g.insert(1, "condicion", v)
        filas.append(g)
    return pd.concat(filas, ignore_index=True)


def resume_dias(d: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for v in ("generacion", "demanda", "bolsa"):
        g = d.groupby(["caso", f"t_{v}"]).agg(
            dias=("dia", "size"), kwh=("kwh", "sum"), banda=("banda", "sum"),
            prima=("prima", "sum"), num=("num", "sum"),
            opt=("excedente_optimo", "sum"), dv=("dv", "sum"),
            vol=("volumen", "sum")).reset_index()
        g["kwh_por_dia"] = g["kwh"] / g["dias"]
        g["banda_por_kwh"] = np.where(g["kwh"] > 0, g["banda"] / g["kwh"], np.nan)
        g["parte_vendedor"] = np.where(g["banda"] > 0, g["prima"] / g["banda"],
                                       np.nan)
        g["captura"] = np.where(g["opt"] > 0, g["num"] / g["opt"], np.nan)
        g["parte_regla_declarada"] = np.where(g["vol"] > 0, g["dv"] / g["vol"],
                                              np.nan)
        g = g.rename(columns={f"t_{v}": "nivel"})
        g.insert(1, "condicion", v)
        filas.append(g[["caso", "condicion", "nivel", "dias", "kwh_por_dia",
                        "banda_por_kwh", "parte_vendedor", "captura",
                        "parte_regla_declarada"]])
    return pd.concat(filas, ignore_index=True)


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    bd = bolsa_diaria()
    ms, ds = zip(*(un_caso(c, bd) for c in CASOS))
    m = pd.concat(ms, ignore_index=True)
    d = pd.concat(ds, ignore_index=True)
    m.to_csv(SALIDA / "meses_condicion.csv", index=False)
    d.to_csv(SALIDA / "dias_condicion.csv", index=False)
    rm, rd = resume_meses(m), resume_dias(d)
    rm.to_csv(SALIDA / "resumen_meses.csv", index=False)
    rd.to_csv(SALIDA / "resumen_dias.csv", index=False)
    cabeza = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ,
                            capture_output=True, text=True, check=True
                            ).stdout.strip()
    (SALIDA / "procedencia.txt").write_text(
        f"guion: reformateo/documento/scripts/subperiodos_condicion.py\n"
        f"codigo: {cabeza}\nfecha: {dt.datetime.now().isoformat(timespec='seconds')}\n"
        f"fuente: almacenes del canon ({MATRIZ.relative_to(RAIZ).as_posix()}) y "
        f"data/precios_bolsa_xm_api.csv (H-92)\n"
        f"regla: el dinero frente a la regulación solo por mes (D72); por día, "
        f"solo magnitudes del propio mercado\n", encoding="utf-8")
    print("  meses en que el P2P queda bajo C4 y bajo C5, por tercil de bolsa")
    x = rm[rm.condicion == "bolsa"].pivot(index="caso", columns="nivel",
                                          values="meses_P2P_bajo_C5")
    print(x.reindex(CASOS)[NIVELES].to_string())
    print("\n  E0, días por tercil de generación y de bolsa")
    print(rd[(rd.caso == "E0") & (rd.condicion.isin(["generacion", "bolsa"]))]
          .round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
