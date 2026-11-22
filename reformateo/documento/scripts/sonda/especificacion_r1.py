"""
especificacion_r1.py — lo que cada corrida de la revisión r1 (AE-5 y AE-4)
TIENE que cumplir, contra el canon (M1 de la auditoría del 2026-11-21).

Actividad 3.3. La usa `compuerta_r1.py --canon <matriz del canon>`. Las
compuertas de siempre comprueban identidades internas (con el piso y el cargo
del propio almacén); esta compara con el canon, de modo que un cargo o un piso
mal puestos fallan:

  S5  C1, C3, C4 y C5 del libro son los del canon (1 COP)
  T   demanda, generación y tarifa de cada agente son las del canon (al bit)
  F5  solo1 y ninguno: cargo_comprador.npy = kappa·Cv + Theta del comprador,
      con Cv y Theta de E0 y P2 del canon por institución y mes; las demás, sin
      cargo; y el techo de cada flujo es la tarifa del comprador menos su cargo
  P   el piso de toda hora-vendedor es la permuta de la esquina o la bolsa de
      la hora: en p2p, solo1 y el corte, la permuta del canon del caso (el
      numeral de su planta); en solo2 y ninguno, CU − kappa·Cv − Theta
  F1  p2p: los flujos y el P2P del libro son los del canon
  S4  el corte secuencial en E0, P2, K1, CV2 y SINU: los flujos del canon
  F3  solo1 en E0, K1, CV2 y SINU: nadie transa y P2P = C1

Las filas se alinean por fecha, de modo que sirve también para las corridas de
un día. Línea final en verde: «COMPUERTA ESPECIFICACION R1 <caso> EN VERDE».
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
ESQ_CARGO = ("solo1", "ninguno")
CONTROLES = ("E0", "P2", "K1", "CV2", "SINU")
SIN_CORTE = ("E0", "K1", "CV2", "SINU")


def marcador(alm: Path):
    alm = Path(alm)
    for m in ("ESQUINA", "CORTE"):
        f = alm.parent.parent / m
        if f.is_file():
            return m.lower(), f.read_text(encoding="utf-8").strip()
    return None, None


def especificacion(alm: Path, cobertura: str, caso: str, canon: Path) -> int:
    from core.almacen import lee
    from data.xm_prices import get_pi_bolsa
    alm, canon = Path(alm), Path(canon)
    malas = []

    def exige(ok, msg):
        print(("  BIEN  " if ok else "  MAL   ") + msg)
        if not ok:
            malas.append(msg)

    tipo, valor = marcador(alm)
    if tipo is None:
        print(f"COMPUERTA ESPECIFICACION R1 {caso}: NO SE PUEDE COMPROBAR: sin marcador ESQUINA ni CORTE")
        return 2
    esq = valor.split("+")[0] if tipo == "esquina" else "p2p"
    print("=" * 78)
    print(f"  COMPUERTA ESPECIFICACION R1 - caso {caso} ({tipo} = {valor}; canon {canon})")
    print("=" * 78)
    try:
        a = lee(str(alm), cobertura, "agentes")
        ac = lee(str(canon / caso / "almacen"), "m1", "agentes")
        e0 = lee(str(canon / "E0" / "almacen"), "m1", "agentes")
        p2 = lee(str(canon / "P2" / "almacen"), "m1", "agentes")
    except FileNotFoundError as e:
        print(f"COMPUERTA ESPECIFICACION R1 {caso}: NO SE PUEDE COMPROBAR: {e}")
        return 2
    try:
        fl = lee(str(alm), cobertura, "flujos")
    except FileNotFoundError:
        fl = pd.DataFrame(columns=["hora", "fecha", "vendedor", "comprador", "kwh", "precio", "techo_comprador"])
    libro = alm.parent / "outputs" / "resultados_comparacion.xlsx"
    libro_c = canon / caso / "outputs" / "resultados_comparacion.xlsx"
    res = pd.read_excel(libro, "Resumen").set_index("Escenario")["Ganancia_neta_COP"]
    resc = pd.read_excel(libro_c, "Resumen").set_index("Escenario")["Ganancia_neta_COP"]
    orden = str(pd.read_excel(libro, "Diagnostico", keep_default_na=False).comando.iloc[0])
    kap = 2.0 if "--factor-cv 2" in orden else 1.0
    completo = len(a) == len(ac)
    for k in ("C1", "C3", "C4", "C5"):
        if completo and k in res.index:
            exige(abs(float(res[k]) - float(resc[k])) <= 1.0,
                  f"S5: {k} del libro {float(res[k]):,.2f} = canon {float(resc[k]):,.2f} COP")
    key = ["fecha", "agente"]
    m = a[key + ["hora", "mes", "demanda", "generacion", "techo", "piso", "sobrante", "vende_p2p"]].merge(
        ac[key + ["demanda", "generacion", "techo", "piso"]], on=key, suffixes=("", "_c"), how="left")
    exige(bool(m.techo_c.notna().all() and (m.demanda == m.demanda_c).all()
               and (m.generacion == m.generacion_c).all() and (m.techo == m.techo_c).all()),
          f"T: demanda, generación y tarifa de las {len(m)} filas son las del canon")
    t0 = e0.groupby(["agente", "mes"])[["techo", "piso"]].first().astype(float)
    t2 = p2.groupby(["agente", "mes"])[["piso"]].first().astype(float)
    cv, th = (t0.techo - t0.piso), (t0.piso - t2.piso)
    m["cv"] = [kap * float(cv.get((g, ms), np.nan)) for g, ms in zip(m.agente, m.mes)]
    m["th"] = [float(th.get((g, ms), np.nan)) for g, ms in zip(m.agente, m.mes)]
    exige(bool(m.cv.notna().all() and m.th.notna().all()), "F5: Cv y Theta del canon para todos los agentes y meses")
    ags = list(dict.fromkeys(a.agente))
    T_h = int(a.hora.max()) + 1
    f_c = alm / "cargo_comprador.npy"
    if esq in ESQ_CARGO:
        exige(f_c.is_file(), f"F5: la esquina {esq} lleva cargo_comprador.npy")
        if f_c.is_file():
            cargo = np.load(f_c)
            espera = np.zeros((len(ags), T_h))
            for n, g in enumerate(ags):
                x = m[m.agente == g].sort_values("hora")
                espera[n] = (x.cv + x.th).to_numpy()
            dmax = float(np.abs(cargo - espera).max()) if cargo.shape == espera.shape else np.inf
            exige(dmax <= 0.01, f"F5: el cargo es kappa·Cv + Theta del comprador (|dif| máx. {dmax:.4f} COP/kWh)")
            if len(fl) and cargo.shape == espera.shape:
                ti = a.set_index(["hora", "agente"]).techo.astype(float)
                tn = np.array([ti[(int(h), c)] - cargo[ags.index(c), int(h)] for h, c in zip(fl.hora, fl.comprador)])
                d2 = float(np.abs(fl.techo_comprador.astype(float).to_numpy() - tn).max())
                exige(d2 <= 0.01, f"F5: el techo de cada flujo es la tarifa del comprador menos su cargo (|dif| {d2:.4f})")
    else:
        exige(not f_c.is_file(), f"F5: la esquina {esq} no lleva cargo")
    fechas = pd.to_datetime(a[a.agente == ags[0]].sort_values("hora").fecha)
    pb = np.asarray(get_pi_bolsa(T_h, t_start=fechas.iloc[0].strftime("%Y-%m-%d"),
                                 t_end=(fechas.iloc[-1] + pd.Timedelta(hours=1)).strftime("%Y-%m-%d"),
                                 csv_path=str(RAIZ / "data" / "xm_precios_bolsa.csv"), scenario="2025_normal"),
                    dtype=float)
    m["bolsa"] = pb[m.hora.to_numpy(int)]
    v = m[m.sobrante > 1e-9].copy()
    es_bolsa = ((v.piso - v.bolsa).abs() <= 0.01).to_numpy()
    if esq in ("solo2", "ninguno"):
        perm = ((v.piso - (v.techo - v.cv - v.th)).abs() <= 0.01).to_numpy()
        txt = "CU − kappa·Cv − Theta"
    else:
        cbol = (v.piso_c - v.bolsa).abs() <= 0.01
        pm = v[~cbol].groupby(["agente", "mes"]).piso_c.agg(lambda x: x.round(4).mode().iloc[0])
        ref = np.array([pm.get((g, ms), np.nan) for g, ms in zip(v.agente, v.mes)])
        perm = np.abs(v.piso.to_numpy() - ref) <= 0.01
        txt = "la permuta del canon del caso (el numeral de su planta)"
    exige(bool((perm | es_bolsa).all()),
          f"P: el piso de las {len(v)} horas-vendedor es {txt} o la bolsa de la hora "
          f"({int((~(perm | es_bolsa)).sum())} no)")
    if (tipo == "esquina" and valor == "p2p") or (tipo == "corte" and valor.startswith("secuencial")
                                                  and caso in CONTROLES):
        flc = lee(str(canon / caso / "almacen"), "m1", "flujos")
        flc = flc[flc.fecha.isin(set(a.fecha))]
        k3 = ["fecha", "vendedor", "comprador"]
        mm = fl[k3 + ["kwh"]].merge(flc[k3 + ["kwh"]], on=k3, how="outer", suffixes=("", "_c"), indicator=True)
        solo = int((mm._merge != "both").sum())
        dk = float((mm.kwh.astype(float) - mm.kwh_c.astype(float)).abs().max()) if len(mm) else 0.0
        etq = "F1" if tipo == "esquina" else "S4"
        exige(solo == 0 and dk <= 1e-4, f"{etq}: los {len(fl)} flujos son los del canon (sin pareja {solo}, |dkWh| {dk:.1e})")
        if completo:
            exige(abs(float(res["P2P"]) - float(resc["P2P"])) <= max(1.0, 1e-6 * abs(float(resc["P2P"]))),
                  f"{etq}: P2P del libro {float(res['P2P']):,.2f} = canon {float(resc['P2P']):,.2f} COP")
    if esq == "solo1" and caso in SIN_CORTE:
        e = float(a.vende_p2p.astype(float).sum())
        exige(e == 0.0 and abs(float(res["P2P"]) - float(res["C1"])) <= max(1.0, 1e-6 * abs(float(res["C1"]))),
              f"F3: solo1 no transa ({e:.4f} kWh) y P2P = C1")
    if malas:
        print(f"COMPUERTA ESPECIFICACION R1 {caso} CON {len(malas)} FALLOS")
        return 1
    print(f"COMPUERTA ESPECIFICACION R1 {caso} EN VERDE")
    return 0
