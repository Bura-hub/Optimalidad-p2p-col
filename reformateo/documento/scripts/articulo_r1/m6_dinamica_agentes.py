"""
m6_dinamica_agentes.py — M6: la dinámica frente a la forma cerrada, agente por
agente, en las horas de la validación
===============================================================================
Comentarios C-3, AE-3 y AE-6 de la revisión r1. No integra nada: lee las
integraciones guardadas de la validación ampliada (`m_a2.json`, grupo e1/VA,
CANON §14.33) y de la dinámica con precios extremos (`m_a2x.json` y
`m_a2x_desde71.json`, grupo e1/DX, CANON §14.37).

QUÉ SE COMPARA. En cada hora, el último punto de control de la integración
(tiempo equivalente 160, u 80 si el tope la cortó antes) frente a la forma
cerrada de la misma hora:

  energía     la que recibe cada comprador y la que entrega cada vendedor;
  precio      el precio de reposo de cada comprador;
  pago        lo que paga cada comprador y cobra cada vendedor. Los dos
              resultados se liquidan con la MISMA regla del artículo: un precio
              uniforme que conserva el ingreso Σ p·q, con tope en la tarifa de
              cada comprador, y el ingreso repartido entre vendedores en
              proporción a lo que entregan. Así la diferencia de pago viene del
              resultado y no de la regla de liquidación;
  beneficio   del comprador, (tarifa − lo que paga por kWh) · energía; del
              vendedor, (ingreso medio − su piso) · energía.

LAS CLASES son las del veredicto fijado de antemano: «dentro» (dentro de la
tolerancia en los tiempos equivalentes 80 y 160), «no llega» (sin tiempo
equivalente 160) y «fuera» (las demás, incluidas las que solo están dentro en
el tiempo equivalente 160).

EL REPARTO ENTRE VENDEDORES no entra en el veredicto, que juzga la energía y el
precio de cada comprador. Aquí se cuenta aparte: horas en que lo que entrega
algún vendedor difiere en más del 1 % de la energía de la hora. Cuando la
demanda es la menor, la forma cerrada despacha por piso creciente y la dinámica
reparte de otro modo, y eso cambia el ahorro del intercambio de esa hora.

Compuertas: los recuentos son los del canon (99 de 141 y 74 de 120) y el precio
uniforme recalculado sobre la forma cerrada es el que ella guarda.

Escribe m6_agentes.csv, m6_horas.csv y m6_resumen.csv.

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo_r1/m6_dinamica_agentes.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import ar1_comun as C

F_VA = "validacion_ampliada_2026-10-06/m_a2.json"
F_DX = ["dinamica_extrema_2026-10-07/m_a2x.json", "dinamica_extrema_2026-10-07/m_a2x_desde71.json"]
FU = "m_a2.json (e1/VA) y m_a2x.json con m_a2x_desde71.json (e1/DX): último punto de control frente a la forma cerrada"


def uniforme(q: np.ndarray, p: np.ndarray, techo: np.ndarray) -> np.ndarray:
    """Precio que paga cada comprador: un precio único que conserva Σ p·q, con
    tope en la tarifa de cada uno (ec. del precio uniforme del artículo)."""
    ingreso = float((p * q).sum())
    act = q > 0
    if not act.any():
        return np.minimum(p, techo)
    lo, hi = 0.0, float(techo[act].max())
    f = lambda x: float((np.minimum(x, techo) * q).sum()) - ingreso
    if f(hi) < 0:                       # el ingreso pide más que los techos: cada uno paga su techo
        return techo.copy()
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
    return np.minimum(hi, techo)


def corridas(med: C.Medicion) -> list[dict]:
    va = json.loads(C.AS.lee(F_VA, "e1/VA").read_text(encoding="utf-8"))
    dx = {}
    for f in F_DX:                      # la reanudación desde la corrida 71 sustituye a las de la noche anterior
        for r in json.loads(C.AS.lee(f, "e1/DX").read_text(encoding="utf-8")):
            dx[r["plan_indice"]] = r
    med.exige(len(va) == 280 and len(dx) == 120, f"se esperaban 280 corridas de M-A2 y 120 de M-A2X, hay {len(va)} y {len(dx)}")
    return va + [dx[k] for k in sorted(dx)]


def main() -> int:
    med = C.Medicion("m6", "dinámica frente a forma cerrada por agente, en las horas de la validación")
    ag, hs = [], []
    peor_pu = 0.0
    for r in corridas(med):
        if not r.get("veredicto"):
            continue                    # omitida por la parada por futilidad: no se integró
        sp, v = r["spec"], r["veredicto"]["cerrada"]
        t160 = bool(v["teq160"]["hay"])
        dentro = t160 and bool(v["teq80"]["dentro"]) and bool(v["teq160"]["dentro"])
        clase = "dentro" if dentro else ("fuera" if t160 else "no_llega")
        fila = r["filas"][-1]
        ce = r["cerrada"]["cerrada"]
        techo, piso_j = np.array(r["techo"], float), np.array(r["piso_j"], float)
        qd, pd_, sd = np.array(fila["q"], float), np.array(fila["p"], float), np.array(fila["sj"], float)
        qc, pc, sc = np.array(ce["q"], float), np.array(ce["p"], float), np.array(ce["sj"], float)
        med.exige(len(qd) == len(qc) == len(techo) == len(r["comp"]) and len(sd) == len(sc) == len(piso_j) == len(r["vend"]),
                  f"{sp['caso']} {sp['fecha']}: tamaños distintos")
        for x in (qd, pd_, sd, qc, pc, sc, techo, piso_j):
            med.exige(bool(np.isfinite(x).all()), f"{sp['caso']} {sp['fecha']}: valores no finitos")
        uc, ud = uniforme(qc, pc, techo), uniforme(qd, pd_, techo)
        act = qc > 1e-9
        if act.any() and ce.get("p_u") is not None:
            # el precio uniforme guardado, con su tope, da el mismo pago
            dpu = abs(float((np.minimum(ce["p_u"], techo) * qc).sum()) - float((uc * qc).sum())) / max(float(qc.sum()), 1e-12)
            peor_pu = max(peor_pu, dpu)
        Ec, Ed = float(qc.sum()), float(qd.sum())
        ing_c, ing_d = float((uc * qc).sum()), float((ud * qd).sum())
        mc, mdn = (ing_c / Ec if Ec > 0 else 0.0), (ing_d / Ed if Ed > 0 else 0.0)
        med_ = dict(medicion=sp["medicion"], familia=sp.get("familia_precio", "base"), caso=sp["caso"], fecha=sp["fecha"],
                    regimen=sp["grupo"], clase=clase, teq=float(fila["teq"]))
        for i, nom in enumerate(r["comp"]):
            ag.append(dict(med_, agente=nom, papel="comprador", energia_cerrada=qc[i], energia_dinamica=qd[i],
                           precio_reposo_cerrada=pc[i], precio_reposo_dinamica=pd_[i],
                           pago_cerrada=uc[i] * qc[i], pago_dinamica=ud[i] * qd[i],
                           beneficio_cerrada=(techo[i] - uc[i]) * qc[i], beneficio_dinamica=(techo[i] - ud[i]) * qd[i]))
        for j, nom in enumerate(r["vend"]):
            ag.append(dict(med_, agente=nom, papel="vendedor", energia_cerrada=sc[j], energia_dinamica=sd[j],
                           precio_reposo_cerrada=mc, precio_reposo_dinamica=mdn,
                           pago_cerrada=mc * sc[j], pago_dinamica=mdn * sd[j],
                           beneficio_cerrada=(mc - piso_j[j]) * sc[j], beneficio_dinamica=(mdn - piso_j[j]) * sd[j]))
        ahorro_c = float((techo * qc).sum() - (piso_j * sc).sum())
        ahorro_d = float((techo * qd).sum() - (piso_j * sd).sum())
        hs.append(dict(med_, E_cerrada=Ec, E_dinamica=Ed, dE=abs(Ed - Ec),
                       dq_max=float(np.abs(qd - qc).max()), dp_max=float(np.abs(pd_ - pc).max()),
                       dq_max_rel=float(np.abs(qd - qc).max()) / Ec if Ec > 0 else 0.0,
                       dsj_max=float(np.abs(sd - sc).max()),
                       dsj_max_rel=float(np.abs(sd - sc).max()) / Ec if Ec > 0 else 0.0,
                       ingreso_cerrada=ing_c, ingreso_dinamica=ing_d, precio_medio_cerrada=mc, precio_medio_dinamica=mdn,
                       ahorro_intercambio_cerrada=ahorro_c, ahorro_intercambio_dinamica=ahorro_d,
                       parte_vendedor_cerrada=(ing_c - float((piso_j * sc).sum())) / ahorro_c if ahorro_c > 0 else np.nan,
                       parte_vendedor_dinamica=(ing_d - float((piso_j * sd).sum())) / ahorro_d if ahorro_d > 0 else np.nan,
                       n_compradores=len(qc), n_vendedores=len(sc)))
    Ag, H = pd.DataFrame(ag), pd.DataFrame(hs)
    for k in ("energia", "precio_reposo", "pago", "beneficio"):
        Ag[f"d_{k}"] = Ag[f"{k}_dinamica"] - Ag[f"{k}_cerrada"]
    Ag["d_pago_por_kwh"] = np.where(Ag.energia_cerrada > 1e-9, Ag.d_pago / Ag.energia_cerrada.where(Ag.energia_cerrada > 1e-9, 1.0), 0.0)
    H["d_ahorro_intercambio"] = H.ahorro_intercambio_dinamica - H.ahorro_intercambio_cerrada
    H["d_precio_medio"] = H.precio_medio_dinamica - H.precio_medio_cerrada
    H["d_ingreso"] = H.ingreso_dinamica - H.ingreso_cerrada
    # traspaso entre compradores y vendedores: lo que cambia el ingreso de los vendedores
    b = Ag.groupby(["medicion", "familia", "caso", "fecha"]).d_beneficio.agg(lambda x: float(np.abs(x).sum()))
    H = H.merge(b.rename("suma_abs_d_beneficio").reset_index(), on=["medicion", "familia", "caso", "fecha"])

    cont = H.groupby(["medicion", "clase"]).size().unstack(fill_value=0)
    va, dx = cont.loc["M-A2"], cont.loc["M-A2X"]
    med.exige((int(va.sum()), int(va["dentro"]), int(va["fuera"]), int(va["no_llega"])) == (141, 99, 22, 20),
              f"M-A2: {dict(va)} no es 141 horas con 99 dentro, 22 fuera y 20 que no llegan")
    med.exige((int(dx.sum()), int(dx["dentro"])) == (120, 74), f"M-A2X: {dict(dx)} no es 120 horas con 74 dentro")
    med.ok("los recuentos son los del canon: 141 horas con 99 dentro, 22 fuera y 20 que no llegan (§14.33), y 120 con 74 dentro (§14.37)")
    med.exige(peor_pu <= 1e-6, f"el precio uniforme recalculado difiere del guardado en {peor_pu:.2e} COP/kWh")
    med.ok(f"el precio uniforme recalculado sobre la forma cerrada da el pago del precio que ella guarda (≤ {peor_pu:.1e} COP/kWh)")
    con160 = H[H.teq >= 80]
    med.exige(float(H.dE.max()) <= 1e-6, f"la energía total difiere en {H.dE.max():.2e} kWh")
    med.ok(f"la energía total transada de la dinámica es la de la forma cerrada en las {len(H)} horas (diferencia máxima {H.dE.max():.1e} kWh)")
    med.tabla(Ag, "m6_agentes.csv")
    med.tabla(H, "m6_horas.csv")
    filas = []
    for (m, cl), g in H.groupby(["medicion", "clase"]):
        a = Ag[(Ag.medicion == m) & (Ag.clase == cl)]
        ac, av = a[a.papel == "comprador"], a[a.papel == "vendedor"]
        filas.append(dict(medicion=m, clase=cl, horas=len(g), agentes=len(a),
                          energia_kwh=float(g.E_cerrada.sum()),
                          dE_max_kwh=float(g.dE.max()), dq_max_rel_mediana=float(g.dq_max_rel.median()), dq_max_rel_max=float(g.dq_max_rel.max()),
                          dp_max_mediana=float(g.dp_max.median()), dp_max_max=float(g.dp_max.max()),
                          d_precio_medio_mediana=float(g.d_precio_medio.abs().median()), d_precio_medio_max=float(g.d_precio_medio.abs().max()),
                          ingreso_cerrada_COP=float(g.ingreso_cerrada.sum()), d_ingreso_COP=float(g.d_ingreso.sum()),
                          suma_abs_d_ingreso_COP=float(g.d_ingreso.abs().sum()),
                          ahorro_cerrada_COP=float(g.ahorro_intercambio_cerrada.sum()),
                          d_ahorro_COP=float(g.d_ahorro_intercambio.sum()), suma_abs_d_ahorro_COP=float(g.d_ahorro_intercambio.abs().sum()),
                          d_beneficio_compradores_COP=float(ac.d_beneficio.sum()), d_beneficio_vendedores_COP=float(av.d_beneficio.sum()),
                          d_pago_por_kwh_abs_mediana=float(ac[ac.energia_cerrada > 1e-9].d_pago_por_kwh.abs().median()),
                          d_pago_por_kwh_abs_max=float(ac[ac.energia_cerrada > 1e-9].d_pago_por_kwh.abs().max()),
                          horas_un_comprador=int((g.n_compradores == 1).sum()),
                          horas_despacho_distinto=int((g.dsj_max_rel > 0.01).sum()),
                          horas_varios_vendedores=int((g.n_vendedores > 1).sum())))
    R = pd.DataFrame(filas)
    R["d_ingreso_sobre_ingreso_pct"] = 100 * R.d_ingreso_COP / R.ingreso_cerrada_COP
    R["d_ahorro_sobre_ahorro_pct"] = 100 * R.d_ahorro_COP / R.ahorro_cerrada_COP
    med.tabla(R, "m6_resumen.csv")
    for _, r in R.iterrows():
        pre = f"m6__{r.medicion.replace('-', '')}__{r.clase}"
        med.pon(f"{pre}__horas", int(r.horas), "h", FU)
        med.pon(f"{pre}__energia_kwh", r.energia_kwh, "kWh", FU)
        med.pon(f"{pre}__dE_max_kwh", r.dE_max_kwh, "kWh", FU)
        med.pon(f"{pre}__dq_max_rel_max", 100 * r.dq_max_rel_max, "% de la energía de la hora", FU)
        med.pon(f"{pre}__dp_max_mediana", r.dp_max_mediana, "COP/kWh", FU)
        med.pon(f"{pre}__dp_max_max", r.dp_max_max, "COP/kWh", FU)
        med.pon(f"{pre}__d_precio_medio_max", r.d_precio_medio_max, "COP/kWh", FU)
        med.pon(f"{pre}__ingreso_cerrada", r.ingreso_cerrada_COP, "COP", FU)
        med.pon(f"{pre}__d_ingreso", r.d_ingreso_COP, "COP", FU + "; ingreso de los vendedores, dinámica menos forma cerrada")
        med.pon(f"{pre}__d_ingreso_pct", r.d_ingreso_sobre_ingreso_pct, "%", FU)
        med.pon(f"{pre}__ahorro_cerrada", r.ahorro_cerrada_COP, "COP", FU)
        med.pon(f"{pre}__d_ahorro", r.d_ahorro_COP, "COP", FU + "; ahorro del intercambio (techo menos piso por energía)")
        med.pon(f"{pre}__d_ahorro_pct", r.d_ahorro_sobre_ahorro_pct, "%", FU)
        med.pon(f"{pre}__d_beneficio_compradores", r.d_beneficio_compradores_COP, "COP", FU)
        med.pon(f"{pre}__d_beneficio_vendedores", r.d_beneficio_vendedores_COP, "COP", FU)
        med.pon(f"{pre}__horas_un_comprador", int(r.horas_un_comprador), "h", FU)
        med.pon(f"{pre}__horas_despacho_distinto", int(r.horas_despacho_distinto), "h", FU + "; reparto entre vendedores a más del 1 % de la energía de la hora")
        med.pon(f"{pre}__horas_varios_vendedores", int(r.horas_varios_vendedores), "h", FU)
        med.di(f"  {r.medicion} {r.clase}: {int(r.horas)} h, {r.energia_kwh:.1f} kWh; dq máx {100 * r.dq_max_rel_max:.2f} % de E; "
               f"dp mediana {r.dp_max_mediana:.3f} y máx {r.dp_max_max:.1f} COP/kWh; ingreso de vendedores "
               f"{r.d_ingreso_sobre_ingreso_pct:+.2f} %; ahorro del intercambio {r.d_ahorro_sobre_ahorro_pct:+.3f} %; "
               f"compradores {r.d_beneficio_compradores_COP:+.0f} y vendedores {r.d_beneficio_vendedores_COP:+.0f} COP; "
               f"despacho entre vendedores distinto en {int(r.horas_despacho_distinto)} de {int(r.horas_varios_vendedores)} h con varios vendedores")
    med.cierra()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
