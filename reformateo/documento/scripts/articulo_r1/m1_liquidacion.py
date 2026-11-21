"""
m1_liquidacion.py — M1 acotada: la liquidación del crédito del mes. Cotas del
canon y liquidación secuencial hora a hora con los flujos guardados
===============================================================================
Comentario AE-4 de la revisión r1. No simula ni toca el núcleo: reúne las cotas
de los puntos CF y PV del canon (§14.25 y §14.27) y vuelve a liquidar, con los
flujos del almacén, el crédito del mes de C1, de C4 y del residual del mercado
P2P con una regla secuencial.

QUÉ ES APROXIMADO HOY Y QUÉ NO.
  1. El piso del vendedor en el juego usa una hora del corte calculada antes del
     mercado, con residuales aproximados y los totales del mes completo. Es lo
     único aproximado. Los flujos del almacén se formaron con ese piso.
  2. La liquidación NO es aproximada: parte el residual real de cada miembro
     con el Anexo 4 al cierre del mes (`reparto_anexo4`), que es lo que manda
     la norma.

A. LAS COTAS DEL CANON. Por caso: la energía transada con el piso del vendedor
ya en la bolsa, la que queda tras el corte de la liquidación, y la parte de lo
vendido cuyo estado no se conoce hasta el cierre y la que un pronóstico lineal
clasifica mal. Donde nadie agota su crédito no hay corte y la aproximación no
actúa.

B. LA LIQUIDACIÓN SECUENCIAL, con los flujos fijos. El Anexo 4 mira el mes
entero al cierre: es exceso lo inyectado desde la hora en que la inyección
acumulada alcanza la importación TOTAL del mes. Una liquidación que actualiza
el saldo hora a hora no conoce ese total. Aquí se lleva un saldo corrido por
miembro y mes:
  - lo importado en la hora se cubre primero con el exceso provisional que haya,
    y lo que falte queda como importación por cubrir;
  - lo inyectado cubre primero la importación por cubrir, y lo que sobre queda
    como exceso provisional de esa hora;
  - al cierre, el exceso provisional que no se cubrió es exceso definitivo y se
    paga a la bolsa de su hora.
El crédito total del mes es el mismo que con el Anexo 4, mín(inyección,
importación). Cambia a qué horas se asigna el exceso y, por tanto, con qué bolsa
se paga. Dos variantes, según qué exceso provisional se cubre primero: el más
antiguo (FIFO) o el más reciente (LIFO). La variante FIFO da, hora por hora, la
misma partición que el Anexo 4 (compuerta). La LIFO no está en la norma: mide
cuánto pesaría otro orden.

LO QUE NO CUBRE. Los flujos son los del canon: con un piso calculado hora a hora
el mercado transaría otra cosa, y eso exige un piso nuevo en el núcleo.

Escribe m1_cotas.csv y m1_secuencial.csv.

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo_r1/m1_liquidacion.py
"""
from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd

import ar1_comun as C

F_CF = "corte_fondo_2026-10-04/corte_fondo_13casos.csv"
F_PV = "prevision_corte_2026-10-04/prevision_13casos.csv"
FU_A = "corte_fondo_13casos.csv (e1/CF) y prevision_13casos.csv (e1/PV), filas de la comunidad"
FU_B = "series del almacén reliquidadas hora a hora con saldo corrido, flujos fijos"


def secuencial(iny: np.ndarray, ret: np.ndarray, mes: np.ndarray, fifo: bool) -> np.ndarray:
    """Exceso definitivo (kWh, misma forma que `iny`) con el saldo corrido."""
    N, T = iny.shape
    ex = np.zeros((N, T))
    for n in range(N):
        for m in np.unique(mes):
            por_cubrir = 0.0
            cola: deque = deque()               # (hora, kWh) de exceso provisional
            for k in np.flatnonzero(mes == m):
                d = ret[n, k]
                while d > 1e-12 and cola:
                    h, x = cola[0] if fifo else cola[-1]
                    usa = min(x, d)
                    d -= usa
                    if x - usa <= 1e-12:
                        cola.popleft() if fifo else cola.pop()
                    elif fifo:
                        cola[0] = (h, x - usa)
                    else:
                        cola[-1] = (h, x - usa)
                por_cubrir += d
                s = iny[n, k]
                usa = min(s, por_cubrir)
                por_cubrir -= usa
                if s - usa > 1e-12:
                    cola.append((k, s - usa))
            for h, x in cola:
                ex[n, h] += x
    return ex


def main() -> int:
    med = C.Medicion("m1", "liquidación del crédito: cotas del canon y liquidación secuencial con flujos fijos")
    AS = C.AS
    # A. Las cotas del canon
    cf = pd.read_csv(AS.lee(F_CF, "e1/CF"))
    pv = pd.read_csv(AS.lee(F_PV, "e1/PV"))
    cf, pv = (x[x.institucion == "comunidad"].set_index("caso").loc[C.CASOS] for x in (cf, pv))
    K = pd.DataFrame(index=C.CASOS)
    K["transado_kwh"] = cf.vendido_kwh
    K["tras_corte_del_piso_kwh"] = cf.vendido_tras_kwh
    K["tras_corte_de_la_liquidacion_kwh"] = cf.vendido_tras_corte_liquidacion_kwh
    K["dif_cortes_kwh"] = (cf.vendido_tras_corte_liquidacion_kwh - cf.vendido_tras_kwh)
    K["tras_corte_del_piso_pct"] = 100 * cf.vendido_tras_kwh / cf.vendido_kwh
    K["exceso_P2P_kwh"], K["exceso_C1_kwh"] = cf.exceso_P2P_kwh, cf.exceso_C1_kwh
    K["incierto_pct"] = 100 * (pv.vendido_kwh_incierto_credito + pv.vendido_kwh_incierto_exceso) / pv.vendido_kwh_total
    K["ahorro_incierto_pct"] = 100 * (pv.ahorro_COP_incierto_credito + pv.ahorro_COP_incierto_exceso) / pv.ahorro_COP_total
    K["mal_clasificado_pct"] = 100 * (pv.vendido_kwh_pronostico_yerra_a_bolsa + pv.vendido_kwh_pronostico_yerra_a_credito) / pv.vendido_kwh_total
    K["ahorro_mal_clasificado_pct"] = 100 * (pv.ahorro_COP_pronostico_yerra_a_bolsa + pv.ahorro_COP_pronostico_yerra_a_credito) / pv.ahorro_COP_total
    K["aproximacion_actua"] = (cf.vendido_tras_kwh > 1e-6).astype(int)
    sin = sorted(K.index[K.aproximacion_actua == 0])
    med.exige(sin == sorted(AS.SIN_AGOTAR) and bool((K.loc[sin, "incierto_pct"] == 0).all())
              and bool((K.loc[sin, "exceso_P2P_kwh"].abs() < 1e-6).all()),
              f"los casos sin energía tras el corte no son E0, P2, K1, CV2 y SINU: {sin}")
    med.ok("en E0, P2, K1, CV2 y SINU no hay energía transada tras el corte, ni horas inciertas, ni exceso: la aproximación no actúa")
    con = K[K.aproximacion_actua == 1]
    med.exige(round(float(con.incierto_pct.min()), 1) == 20.2 and round(float(con.incierto_pct.max()), 1) == 99.0
              and round(float(con.mal_clasificado_pct.min()), 1) == 0.8 and round(float(con.mal_clasificado_pct.max()), 1) == 1.4
              and round(float(con.ahorro_mal_clasificado_pct.max()), 1) == 2.6,
              "las cotas de la previsión no son las de CANON §14.27 (20,2 a 99,0 %; 0,8 a 1,4 %; 2,6 %)")
    med.ok("en los ocho casos con corte, las cotas son las de CANON §14.27: del 20,2 al 99,0 % de lo vendido en horas inciertas, del 0,8 al 1,4 % mal clasificado y como mucho el 2,6 % del ahorro")
    med.tabla(K.reset_index(names="caso"), "m1_cotas.csv")
    for c, r in K.iterrows():
        for k in K.columns:
            u = "%" if k.endswith("_pct") else "kWh" if k.endswith("_kwh") else "0/1"
            med.pon(f"m1__{c}__{k}", r[k], u, FU_A)

    # B. La liquidación secuencial con los flujos fijos
    DAT, pb = C.casos_cargados(med)
    filas = []
    for c, L in DAT.items():
        s, d, v, q, CU, mes, N = L["s"], L["d"], L["v"], L["q"], L["CU"], L["mes"], L["N"]
        sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
        asign = np.zeros_like(s)
        for m in np.unique(mes):
            h = np.flatnonzero(mes == m)
            asign[:, h] = s[:, h].sum(axis=0)[None, :] / N
        series = {"C1": (s, d, L["ded1"]), "P2P": (sr, dr, L["ded1"]), "C4": (asign, d, L["ded4"])}
        f = dict(caso=c)
        for mec, (iny, ret, ded) in series.items():
            _, xa, _ = AS.reparto_anexo4(iny, ret, mes)
            va = float((xa * pb[None, :]).sum())
            f[f"exceso_{mec}_kwh"] = float(xa.sum())
            f[f"bolsa_media_anexo4_{mec}"] = va / xa.sum() if xa.sum() > 1e-9 else np.nan
            for nom, fifo in (("fifo", True), ("lifo", False)):
                xs = secuencial(iny, ret, mes, fifo)
                med.exige(abs(float(xs.sum()) - float(xa.sum())) <= 1e-6 * max(1.0, float(xa.sum())),
                          f"{c} {mec} {nom}: el exceso secuencial ({xs.sum():.4f}) no es el del Anexo 4 ({xa.sum():.4f})")
                por_mes = max(abs(float(xs[n, mes == m].sum() - xa[n, mes == m].sum())) for n in range(N) for m in np.unique(mes))
                med.exige(por_mes <= 1e-6, f"{c} {mec} {nom}: el exceso por miembro y mes difiere en {por_mes:.2e} kWh")
                vs = float((xs * pb[None, :]).sum())
                f[f"d_{mec}_{nom}"] = vs - va                       # el crédito no cambia: solo el valor del exceso
                f[f"kwh_en_otra_hora_{mec}_{nom}"] = 0.5 * float(np.abs(xs - xa).sum())
                f[f"bolsa_media_{nom}_{mec}"] = vs / xs.sum() if xs.sum() > 1e-9 else np.nan
        out, _ = AS.esquinas(L, pb)
        P2P, C1, C4 = (float(out[k].sum()) for k in ("P2P", "C1", "C4"))
        f.update(P2P=P2P, C1=C1, C4=C4, P2P_menos_C4=P2P - C4, P2P_menos_C1=P2P - C1)
        for nom in ("fifo", "lifo"):
            f[f"d_P2P_menos_C4_{nom}"] = f[f"d_P2P_{nom}"] - f[f"d_C4_{nom}"]
            f[f"d_P2P_menos_C1_{nom}"] = f[f"d_P2P_{nom}"] - f[f"d_C1_{nom}"]
            f[f"d_P2P_menos_C4_{nom}_pct"] = 100 * f[f"d_P2P_menos_C4_{nom}"] / f["P2P_menos_C4"]
            f[f"d_P2P_menos_C1_{nom}_pct"] = 100 * f[f"d_P2P_menos_C1_{nom}"] / f["P2P_menos_C1"]
            f[f"P2P_menos_C4_{nom}"] = f["P2P_menos_C4"] + f[f"d_P2P_menos_C4_{nom}"]
            f[f"P2P_menos_C1_{nom}"] = f["P2P_menos_C1"] + f[f"d_P2P_menos_C1_{nom}"]
        filas.append(f)
        med.di(f"  {c}: exceso P2P {f['exceso_P2P_kwh']:.0f} kWh; P2P − C4 {f['P2P_menos_C4'] / C.M:.3f} MCOP, con FIFO "
               f"{f['d_P2P_menos_C4_fifo'] / C.M:+.3f} ({f['d_P2P_menos_C4_fifo_pct']:+.2f} %) y con LIFO "
               f"{f['d_P2P_menos_C4_lifo'] / C.M:+.3f} ({f['d_P2P_menos_C4_lifo_pct']:+.2f} %); P2P − C1 con FIFO "
               f"{f['d_P2P_menos_C1_fifo_pct']:+.2f} % y con LIFO {f['d_P2P_menos_C1_lifo_pct']:+.2f} %")
    med.ok("el exceso secuencial de cada miembro y mes es el del Anexo 4, en kWh, en C1, C4 y el residual del mercado P2P de los 13 casos: solo cambia a qué horas se asigna")
    S = pd.DataFrame(filas).set_index("caso")
    cero = S.loc[AS.SIN_AGOTAR, [k for k in S.columns if k.startswith("d_") and not k.endswith("_pct")]].abs().to_numpy().max()
    med.exige(float(cero) <= 1e-6, f"donde nadie agota su crédito la liquidación secuencial cambia {cero:.4f} COP")
    med.ok("en E0, P2, K1, CV2 y SINU la liquidación secuencial da lo mismo que el Anexo 4, al peso")
    otra = float(S[[k for k in S.columns if k.startswith("kwh_en_otra_hora") and k.endswith("fifo")]].to_numpy().max())
    med.exige(otra <= 1e-6, f"la variante FIFO asigna {otra:.4f} kWh de exceso a otra hora que el Anexo 4")
    med.ok("la variante FIFO reproduce la partición del Anexo 4 hora por hora en C1, C4 y el residual del mercado P2P de los 13 casos: "
           "liquidar al cierre con el Anexo 4 equivale a llevar el saldo hora a hora cubriendo primero el exceso más antiguo")
    med.pon("m1__fifo_kwh_en_otra_hora_max", otra, "kWh", FU_B)
    sig = [k for k in ("fifo", "lifo") if bool(((S[f"P2P_menos_C4_{k}"] > 0) & (S[f"P2P_menos_C1_{k}"] > 0)).all())]
    med.exige(sig == ["fifo", "lifo"], "con la liquidación secuencial alguna brecha del mercado frente a C1 o C4 deja de ser positiva")
    med.ok("con las dos variantes secuenciales, P2P − C4 y P2P − C1 siguen positivas en los 13 casos")
    med.tabla(S.reset_index(), "m1_secuencial.csv")
    for c, r in S.iterrows():
        for nom in ("fifo", "lifo"):
            for b in ("P2P_menos_C4", "P2P_menos_C1"):
                med.pon(f"m1__{c}__d_{b}_{nom}", r[f"d_{b}_{nom}"] / C.M, "MCOP", FU_B)
                med.pon(f"m1__{c}__d_{b}_{nom}_pct", r[f"d_{b}_{nom}_pct"], "% de la brecha", FU_B)
            for mec in ("C1", "P2P", "C4"):
                med.pon(f"m1__{c}__d_{mec}_{nom}", r[f"d_{mec}_{nom}"] / C.M, "MCOP", FU_B)
                med.pon(f"m1__{c}__kwh_en_otra_hora_{mec}_{nom}", r[f"kwh_en_otra_hora_{mec}_{nom}"], "kWh", FU_B)
    con = S.loc[[c for c in C.CASOS if c not in AS.SIN_AGOTAR]]
    for b in ("P2P_menos_C4", "P2P_menos_C1"):
        x = con[[f"d_{b}_fifo_pct", f"d_{b}_lifo_pct"]].to_numpy()
        med.pon(f"m1__{b}__d_pct_min", float(x.min()), "% de la brecha", FU_B + "; ocho casos con corte, las dos variantes")
        med.pon(f"m1__{b}__d_pct_max", float(x.max()), "% de la brecha", FU_B + "; ocho casos con corte, las dos variantes")
        med.di(f"  en los ocho casos con corte, {b} cambia entre {x.min():+.2f} y {x.max():+.2f} % con la liquidación secuencial")
    med.cierra()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
