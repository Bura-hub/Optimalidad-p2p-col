"""
m4a_periodos.py — M4a: la comunidad medida (E0) por meses y por tramos, según
la generación de Udenar sea reconstruida o medida
===============================================================================
Comentario C-4 de la revisión r1. No simula: suma por mes las tablas
`escenarios`, `flujos` y `agentes` del almacén de E0 (con huella).

POR QUÉ POR MES. C1, C4 y el residual del mercado P2P se liquidan con el
crédito del mes (art. 25 y Anexo 4), así que el mes es la unidad más pequeña en
que una brecha frente a C1 o C4 tiene sentido (CANON §12, D72). Ninguna brecha
se da por día ni por hora.

LOS TRAMOS. La generación de Udenar es la del inversor del proyecto desde el 3
de septiembre de 2025 y, antes, la de otro inversor del sitio escalada por
1,2053 (CANON §14.17: 3 666 horas previas). Septiembre es mixto: sus primeras
66 horas son reconstruidas. Diciembre llega al día 15.

  reconstruida        abril a agosto de 2025
  medida              septiembre a diciembre (septiembre con 66 h reconstruidas)
  medida, enteros     octubre y noviembre

Escribe m4a_meses.csv y m4a_tramos.csv.

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo_r1/m4a_periodos.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import ar1_comun as C

MECS = ["P2P", "C1", "C4", "C3", "C5"]     # C2 del almacén es el contrato interno y C4_mensual un alias: no entran
TRAMOS = {"reconstruida": ["2025-04", "2025-05", "2025-06", "2025-07", "2025-08"],
          "medida": ["2025-09", "2025-10", "2025-11", "2025-12"],
          "medida_enteros": ["2025-10", "2025-11"],
          "horizonte": ["2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12"]}
H_RECON = 3666
FU = "almacén de E0 (tablas escenarios, flujos y agentes, grupo almacen/E0), suma por mes"


def derivadas(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    t["P2P_C4"] = t.P2P - t.C4
    t["P2P_C1"] = t.P2P - t.C1
    t["C1_C4"] = t.C1 - t.C4
    t["P2P_C4_pct"] = 100 * t.P2P_C4 / t.C4
    t["P2P_C1_pct"] = 100 * t.P2P_C1 / t.C1
    t["C1_C4_sobre_P2P_C4_pct"] = 100 * t.C1_C4 / t.P2P_C4
    t["transado_sobre_inyeccion_pct"] = 100 * t.transado_kwh / t.inyeccion_kwh
    t["P2P_C4_por_kwh_inyectado"] = t.P2P_C4 / t.inyeccion_kwh
    t["C1_C4_por_kwh_inyectado"] = t.C1_C4 / t.inyeccion_kwh
    t["P2P_C1_por_kwh_transado"] = t.P2P_C1 / t.transado_kwh
    t["inyeccion_udenar_pct"] = 100 * t.inyeccion_udenar_kwh / t.inyeccion_kwh
    return t


def main() -> int:
    med = C.Medicion("m4a", "E0 por meses y por tramos de la generación de Udenar")
    AS = C.AS
    a = AS.almacen("E0", "agentes")
    e = AS.almacen("E0", "escenarios").astype({"valor": "float64"})
    fl = AS.almacen("E0", "flujos").astype({"kwh": "float64"})
    num = ["demanda", "generacion", "sobrante", "faltante", "vende_p2p", "compra_p2p"]
    a = a.astype({k: "float64" for k in num})
    AS.finito(a[num].to_numpy(), "agentes E0")
    AS.finito(e.valor.to_numpy(), "escenarios E0")
    meses = TRAMOS["horizonte"]
    med.exige(sorted(a.mes.unique()) == meses, "los meses del almacén no son los nueve del horizonte")
    t = e[e.escenario.isin(MECS)].pivot_table(index="mes", columns="escenario", values="valor", aggfunc="sum")[MECS]
    g = a.groupby("mes")
    t["horas"] = a[a.agente == a.agente.iloc[0]].groupby("mes").hora.count()
    t["horas_con_mercado"] = fl.groupby("mes").hora.nunique().reindex(meses, fill_value=0)
    t["transado_kwh"] = fl.groupby("mes").kwh.sum().reindex(meses, fill_value=0.0)
    t["demanda_kwh"], t["generacion_kwh"] = g.demanda.sum(), g.generacion.sum()
    t["inyeccion_kwh"], t["importacion_kwh"] = g.sobrante.sum(), g.faltante.sum()
    u = a[a.agente == "Udenar"].groupby("mes")
    t["generacion_udenar_kwh"], t["inyeccion_udenar_kwh"] = u.generacion.sum(), u.sobrante.sum()
    t["vendido_udenar_kwh"] = u.vende_p2p.sum()
    t["demanda_udenar_kwh"] = u.demanda.sum()
    hr = a[(a.agente == "Udenar") & (a.hora < H_RECON)].groupby("mes").hora.count().reindex(meses, fill_value=0)
    t["horas_udenar_reconstruida"] = hr

    # Compuertas
    cif = C.cifras_articulo()
    for mec in ["P2P", "C1", "C4"]:
        dif = t[mec].sum() / C.M - float(cif[f"com__E0__{mec}"])
        med.exige(abs(dif) <= 1e-5, f"la suma de los meses de {mec} difiere del canon en {dif * C.M:.1f} COP")
    med.ok("la suma de los nueve meses de P2P, C1 y C4 es la del canon (com__E0__*, a menos de 10 COP)")
    med.exige(abs(t.transado_kwh.sum() - float(cif["e0__energia_transada"])) <= 1e-3
              and int(t.horas_con_mercado.sum()) == int(float(cif["e0__horas_con_mercado"]))
              and abs(t.inyeccion_kwh.sum() - float(cif["e0__inyeccion_kwh"])) <= 1e-2,
              "energía transada, horas con mercado o inyección distintas de las del canon")
    med.ok("la energía transada (4 592,02 kWh), las horas con mercado (1 126) y la inyección (6 006,47 kWh) son las del canon")
    d72 = pd.read_csv(AS.lee("optimalidad_D72/E0_mensual.csv", "optimalidad_D72"))
    d72 = d72[d72.agente == "Comunidad"].set_index("mes")
    dif = max(float((t.P2P - d72.B_P2P_COP).abs().max()), float((t.C4 - d72.B_C4_COP).abs().max()))
    med.exige(dif <= 5.0, f"P2P o C4 por mes difieren de optimalidad_D72/E0_mensual.csv en {dif:.2f} COP")
    med.ok(f"P2P y C4 de cada mes son los de optimalidad_D72/E0_mensual.csv (diferencia máxima {dif:.2f} COP)")
    dd = pd.read_csv(AS.lee("cifras_datos_2026-09-28/cifras.csv", "e1/D")).set_index("clave").valor
    med.exige(int(float(dd["udenar_horas_sin_MTE_antes"])) == H_RECON and int(hr.sum()) == H_RECON
              and int(hr["2025-09"]) == 66 and int(hr[TRAMOS["reconstruida"]].sum()) == 3600,
              "las horas reconstruidas de Udenar no son las 3 666 del canon (3 600 de abril a agosto y 66 de septiembre)")
    med.ok("Udenar: 3 666 horas previas al inversor del proyecto (e1/D), 3 600 de abril a agosto y 66 de septiembre")

    tm = derivadas(t).reset_index()
    med.tabla(tm, "m4a_meses.csv")
    filas = []
    sumables = MECS + ["horas", "horas_con_mercado", "transado_kwh", "demanda_kwh", "generacion_kwh", "inyeccion_kwh",
                       "importacion_kwh", "generacion_udenar_kwh", "inyeccion_udenar_kwh", "vendido_udenar_kwh",
                       "demanda_udenar_kwh", "horas_udenar_reconstruida"]
    for nom, ms in TRAMOS.items():
        f = t.loc[ms, sumables].sum()
        f["tramo"], f["meses"] = nom, len(ms)
        filas.append(f)
    tt = derivadas(pd.DataFrame(filas).set_index("tramo"))
    tt["parte_de_P2P_C4_pct"] = 100 * tt.P2P_C4 / tt.P2P_C4["horizonte"]
    tt["parte_del_transado_pct"] = 100 * tt.transado_kwh / tt.transado_kwh["horizonte"]
    tt["parte_de_la_inyeccion_pct"] = 100 * tt.inyeccion_kwh / tt.inyeccion_kwh["horizonte"]
    tt["generacion_udenar_kwh_dia"] = tt.generacion_udenar_kwh / (tt.horas / 24)
    tt["inyeccion_kwh_dia"] = tt.inyeccion_kwh / (tt.horas / 24)
    tt["demanda_udenar_kwh_dia"] = tt.demanda_udenar_kwh / (tt.horas / 24)
    tt["inyeccion_udenar_kwh_dia"] = tt.inyeccion_udenar_kwh / (tt.horas / 24)
    tt["transado_kwh_dia"] = tt.transado_kwh / (tt.horas / 24)
    med.tabla(tt.reset_index(), "m4a_tramos.csv")
    med.exige(bool((tm.P2P_C4 > 0).all()) and bool((tm.P2P_C1 > 0).all()) and bool((tm.C1_C4 > 0).all()),
              "alguna brecha mensual de E0 no es positiva")
    med.ok("P2P − C4, P2P − C1 y C1 − C4 son positivas en los nueve meses de E0")

    cols_mes = ["P2P", "C1", "C4", "C3", "C5", "P2P_C4", "P2P_C1", "C1_C4", "P2P_C4_pct", "transado_kwh",
                "horas_con_mercado", "inyeccion_kwh", "generacion_udenar_kwh", "inyeccion_udenar_kwh"]
    uni = lambda k: ("%" if k.endswith("_pct") else "kWh" if k.endswith("_kwh") else "h" if k.startswith("horas")
                     else "COP/kWh" if "_por_kwh_" in k else "kWh/día" if k.endswith("_dia") else "COP")
    for _, f in tm.iterrows():
        for k in cols_mes:
            med.pon(f"m4a__E0__{f.mes}__{k}", f[k], uni(k), FU)
    cols_tr = cols_mes + ["P2P_C1_pct", "C1_C4_sobre_P2P_C4_pct", "transado_sobre_inyeccion_pct",
                          "P2P_C4_por_kwh_inyectado", "C1_C4_por_kwh_inyectado", "P2P_C1_por_kwh_transado",
                          "inyeccion_udenar_pct", "parte_de_P2P_C4_pct", "parte_del_transado_pct",
                          "parte_de_la_inyeccion_pct", "generacion_udenar_kwh_dia", "inyeccion_kwh_dia", "demanda_udenar_kwh_dia",
                          "inyeccion_udenar_kwh_dia", "transado_kwh_dia", "horas"]
    for nom, f in tt.iterrows():
        for k in cols_tr:
            med.pon(f"m4a__E0__{nom}__{k}", f[k], uni(k), FU + f"; tramo {nom}: {', '.join(TRAMOS[nom])}")
    for nom in ["reconstruida", "medida", "medida_enteros", "horizonte"]:
        f = tt.loc[nom]
        med.di(f"  {nom}: P2P − C4 = {f.P2P_C4 / C.M:.3f} MCOP ({f.P2P_C4_pct:.2f} % de C4); P2P − C1 = {f.P2P_C1 / C.M:.3f}; "
               f"transado {f.transado_kwh:.1f} kWh; inyección {f.inyeccion_kwh:.1f} kWh; "
               f"P2P − C4 por kWh inyectado {f.P2P_C4_por_kwh_inyectado:.1f} COP/kWh; "
               f"Udenar: generación {f.generacion_udenar_kwh_dia:.1f}, demanda {f.demanda_udenar_kwh_dia:.1f} e inyección "
               f"{f.inyeccion_udenar_kwh_dia:.1f} kWh/día")
    med.cierra()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
