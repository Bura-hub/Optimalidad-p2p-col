"""
m5_componentes.py — M5: los cargos evitados (C1 − C4) y el ahorro del
intercambio, repartidos por componente de la tarifa
===============================================================================
Comentarios C-6 y C-1 de la revisión r1. No simula: vuelve a liquidar C1 y C4
con `core.opciones_externas.reparto_anexo4` sobre las series del almacén.

LA IDENTIDAD. Con c1 y x1 el crédito y el exceso de C1, y c4 y x4 los de C4
(kWh por miembro y hora),

  C1 − C4 = Σ c4·Θ − Σ c1·Θ·[planta en el numeral 2]     cargos de red
          + Σ c4·κCv − Σ c1·κCv                          comercialización
          + Σ c1·CU − Σ c4·CU                            tarifa de quien acredita
          + Σ x1·π_b − Σ x4·π_b                          exceso a la bolsa

El primer término se parte en transmisión (T), distribución (D), pérdidas (PR)
y restricciones (R), con los componentes mensuales de la tarifa publicada de
cada comercializador (fila oficial, nivel de tensión 2), los mismos ficheros de
`data/` que usa el grupo e1/D. Su suma por mes es el Θ del almacén (compuerta).

LO QUE DICE CADA TÉRMINO. Los dos primeros son cargos que C4 descuenta y C1 no:
dinero que deja de recibir el operador de red, el sistema o el comercializador.
Los dos últimos no son cargos. Salen de que C4 reparte el excedente por igual:
el crédito lo recibe otro miembro, con otra tarifa, y la energía que va a la
bolsa es otra.

EL AHORRO DEL INTERCAMBIO se parte, par a par, en el Cv del vendedor, los cargos
de red de su planta si está en el numeral 2, la diferencia de tarifas entre
comprador y vendedor y, desde el corte, la tarifa del comprador menos la bolsa.

Escribe m5_cargos_evitados.csv y m5_ahorro_intercambio.csv.

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo_r1/m5_componentes.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import ar1_comun as C

COMP = {"T": "Tm", "D": "Dnm", "PR": "PR", "R": "Rm"}
FICH = {"ASC": "data/tarifas_asc_mensual.csv", "CEDENAR": "data/tarifas_cedenar_mensual.csv"}
FU = "C1 y C4 reliquidados con reparto_anexo4 sobre el almacén; componentes de data/tarifas_*_mensual.csv (fila oficial, nivel 2)"


def componentes(med: C.Medicion) -> dict:
    out = {}
    for com, rel in FICH.items():
        t = pd.read_csv(med.insumo(rel), comment="#")
        t = t[(t.categoria == "oficial") & (t.nivel_tension == 2) & (t.propiedad == "cedenar")].set_index("mes")
        med.exige(t.index.is_unique and not t[list(COMP.values())].isna().any().any(), f"{com}: tarifa mensual incompleta")
        out[com] = t
    return out


def main() -> int:
    med = C.Medicion("m5", "cargos evitados y ahorro del intercambio por componente de la tarifa")
    AS = C.AS
    DAT, pb = C.casos_cargados(med)
    A = C.atribucion()
    cif = C.cifras_articulo()
    TAR = componentes(med)
    a0 = AS.almacen("E0", "agentes")
    mes_h = a0[a0.agente == a0.agente.iloc[0]].sort_values("hora").mes.to_numpy()
    # Media del horizonte de cada componente = la del grupo e1/D
    dd = pd.read_csv(AS.lee("cifras_datos_2026-09-28/cifras.csv", "e1/D")).set_index("clave").valor
    w = pd.Series(mes_h).value_counts()
    for com, t in TAR.items():
        for k, col in COMP.items():
            v = float((t.loc[w.index, col] * w).sum() / w.sum())
            med.exige(abs(v - float(dd[f"tarifa_media__{com}__{col}"])) <= 0.006, f"{com} {col}: media {v:.3f} distinta de e1/D")
    med.ok("la media del horizonte de T, D, PR y R de cada comercializador es la del grupo e1/D")
    filas, filas_x = [], []
    peor = 0.0
    for c, L in DAT.items():
        N, mes, CU, s, d = L["N"], L["mes"], L["CU"], L["s"], L["d"]
        com_ag = ["CEDENAR" if a == "Cesmag" else "ASC" for a in L["ags"]]
        K = {k: np.vstack([TAR[cm].loc[list(mes_h), col].to_numpy(dtype=float) for cm in com_ag]) for k, col in COMP.items()}
        th = sum(K.values())
        dif = float(np.abs(th - L["Th"]).max())
        peor = max(peor, dif)
        med.exige(dif <= 0.02, f"{c}: T + D + PR + R difiere del Θ del almacén en {dif:.4f} COP/kWh")
        num2 = (L["capk"] > 100.0)[:, None].astype(float)
        c1, x1, _ = AS.reparto_anexo4(s, d, mes)
        c4, x4 = np.zeros_like(s), np.zeros_like(s)
        for m in np.unique(mes):
            h = np.flatnonzero(mes == m)
            asign = np.full((N, 1), 1.0 / N) * s[:, h].sum(axis=0)[None, :]
            c4[:, h], x4[:, h], _ = AS.reparto_anexo4(asign, d[:, h])
        kCv = L["kap"] * L["Cv"]
        v1 = float((c1 * (CU - L["ded1"]) + x1 * pb[None, :]).sum())
        v4 = float((c4 * (CU - L["ded4"]) + x4 * pb[None, :]).sum())
        tot = float(A.loc[c, "C1"] - A.loc[c, "C4"])
        med.exige(abs((v1 - v4) - tot) <= max(2.0, 2e-7 * abs(A.loc[c, "C1"])), f"{c}: C1 − C4 reliquidado difiere del punto S en {(v1 - v4) - tot:.2f} COP")
        f = dict(caso=c, C1_menos_C4=tot, credito_C1_kwh=float(c1.sum()), credito_C4_kwh=float(c4.sum()),
                 exceso_C1_kwh=float(x1.sum()), exceso_C4_kwh=float(x4.sum()))
        for k in COMP:
            f[f"red_{k}_C4"] = float((c4 * K[k]).sum())
            f[f"red_{k}_C1"] = float((c1 * K[k] * num2).sum())
            f[f"red_{k}"] = f[f"red_{k}_C4"] - f[f"red_{k}_C1"]
        f["red_ajuste"] = float(((c4 - c1 * num2) * (L["Th"] - th)).sum())      # redondeo de la tarifa publicada
        f["red_total"] = sum(f[f"red_{k}"] for k in COMP) + f["red_ajuste"]
        f["comercializacion"] = float((c4 * kCv).sum() - (c1 * kCv).sum())
        f["tarifa_de_quien_acredita"] = float((c1 * CU).sum() - (c4 * CU).sum())
        f["exceso_a_la_bolsa"] = float((x1 * pb[None, :]).sum() - (x4 * pb[None, :]).sum())
        f["reparto"] = f["comercializacion"] + f["tarifa_de_quien_acredita"] + f["exceso_a_la_bolsa"]
        cierre = f["red_total"] + f["reparto"] - (v1 - v4)
        med.exige(abs(cierre) <= 1.0, f"{c}: los términos no suman C1 − C4 ({cierre:.3f} COP)")
        f["red_total_sobre_C1_C4_pct"] = 100 * f["red_total"] / tot
        filas.append(f)

        # El ahorro del intercambio, par a par
        fl = AS.almacen(c, "flujos").astype({"kwh": "float64", "techo_comprador": "float64", "piso_vendedor": "float64"})
        ags = {a: i for i, a in enumerate(L["ags"])}
        iv, h = fl.vendedor.map(ags).to_numpy(), fl.hora.to_numpy()
        kwh, techo, piso = fl.kwh.to_numpy(), fl.techo_comprador.to_numpy(), fl.piso_vendedor.to_numpy()
        perm = CU[iv, h] - L["ded1"][iv, h]
        antes = np.abs(piso - perm) <= 1e-2                      # la marca de CANON §14.25
        cv_v = np.where(antes, kCv[iv, h], 0.0)
        th_v = np.where(antes, (L["Th"] * num2)[iv, h], 0.0)
        dif_t = np.where(antes, techo - CU[iv, h], 0.0)
        tras = np.where(antes, 0.0, techo - piso)
        g = dict(caso=c, transado_kwh=float(kwh.sum()), transado_tras_corte_kwh=float(kwh[~antes].sum()),
                 Cv_del_vendedor=float((cv_v * kwh).sum()), red_del_vendedor_numeral2=float((th_v * kwh).sum()),
                 diferencia_de_tarifas=float((dif_t * kwh).sum()), tras_el_corte=float((tras * kwh).sum()))
        g["ahorro_del_intercambio"] = float(((techo - piso) * kwh).sum())
        partes = g["Cv_del_vendedor"] + g["red_del_vendedor_numeral2"] + g["diferencia_de_tarifas"] + g["tras_el_corte"]
        med.exige(abs(partes - g["ahorro_del_intercambio"]) <= max(5.0, 1e-5 * g["ahorro_del_intercambio"]),
                  f"{c}: las partes del ahorro del intercambio no suman ({partes - g['ahorro_del_intercambio']:.2f} COP)")
        med.exige(abs(g["ahorro_del_intercambio"] / C.M - float(cif[f"com__{c}__banda"])) <= 2e-5,
                  f"{c}: el ahorro del intercambio no es com__{c}__banda")
        filas_x.append(g)
    med.ok(f"T + D + PR + R de la tarifa publicada es el Θ del almacén en cada institución y mes (diferencia máxima {peor:.4f} COP/kWh)")
    med.ok("C1 − C4 reliquidado es el del punto S, y sus términos lo suman a menos de 1 COP, en los 13 casos")
    med.ok("el ahorro del intercambio par a par es com__<caso>__banda y sus cuatro partes lo suman, en los 13 casos")
    T, X = pd.DataFrame(filas), pd.DataFrame(filas_x)
    med.tabla(T, "m5_cargos_evitados.csv")
    med.tabla(X, "m5_ahorro_intercambio.csv")
    for _, r in T.iterrows():
        for k in (["C1_menos_C4", "red_total", "red_ajuste", "comercializacion", "tarifa_de_quien_acredita",
                   "exceso_a_la_bolsa", "reparto"] + [f"red_{k}" for k in COMP]):
            med.pon(f"m5__{r.caso}__{k}", r[k] / C.M, "MCOP", FU)
        med.pon(f"m5__{r.caso}__red_total_sobre_C1_C4_pct", r.red_total_sobre_C1_C4_pct, "%", FU)
        for k in ("credito_C1_kwh", "credito_C4_kwh", "exceso_C1_kwh", "exceso_C4_kwh"):
            med.pon(f"m5__{r.caso}__{k}", r[k], "kWh", FU)
    for _, r in X.iterrows():
        for k in ("Cv_del_vendedor", "red_del_vendedor_numeral2", "diferencia_de_tarifas", "tras_el_corte", "ahorro_del_intercambio"):
            med.pon(f"m5__{r.caso}__intercambio__{k}", r[k] / C.M, "MCOP", "flujos del almacén, par a par (banda = techo del comprador menos piso del vendedor)")
    e = T.set_index("caso").loc["E0"]
    x = X.set_index("caso").loc["E0"]
    med.di(f"  E0: C1 − C4 = {e.C1_menos_C4 / C.M:.3f} MCOP = red {e.red_total / C.M:.3f} (T {e.red_T / C.M:.3f}, D {e.red_D / C.M:.3f}, "
           f"PR {e.red_PR / C.M:.3f}, R {e.red_R / C.M:.3f}) + comercialización {e.comercializacion / C.M:.3f} + tarifa de quien "
           f"acredita {e.tarifa_de_quien_acredita / C.M:.3f} + exceso {e.exceso_a_la_bolsa / C.M:.3f}")
    med.di(f"  E0: ahorro del intercambio {x.ahorro_del_intercambio / C.M:.3f} MCOP = Cv del vendedor {x.Cv_del_vendedor / C.M:.3f} "
           f"+ diferencia de tarifas {x.diferencia_de_tarifas / C.M:.3f}")
    med.cierra()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
