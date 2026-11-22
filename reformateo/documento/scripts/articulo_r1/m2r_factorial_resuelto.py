"""
m2r_factorial_resuelto.py — AE-5: el factorial de los dos supuestos con el
mercado resuelto en cada esquina, y Shapley sobre él (CANON §14.41)
===============================================================================
Actividad 3.3. Las cuatro esquinas (CANON §14.21; diseño, sección 1):

  v11 p2p      los dos supuestos: el mercado P2P (control: el del canon)
  v10 solo1    residual por miembro; lo intercambiado paga kappa·Cv + Theta del comprador
  v01 solo2    intercambio exento; residual al colectivo en el caso 2, PDE propio
  v00 ninguno  lo intercambiado paga kappa·Cv + Theta; todo al colectivo en el caso 2

Cada esquina se liquida sobre SUS flujos, los de su corrida, con
`scenarios.esquinas_supuestos.liquida_esquina`. Shapley desde v00 y desde C4
con la regla del artículo (`analysis.shapley_factorial`).

Compuertas (falla en voz alta):
  F1  la esquina p2p reproduce los flujos del canon (float32) y su P2P
  F2  las cuatro fórmulas sobre los flujos del canon son las de e1/S
  F3  solo1 no transa y vale C1 en E0, K1, CV2 y SINU
  F4  cada liquidación sobre su corrida es la de su libro (P2P de p2p; P2P −
      ded4·q de solo1; P2P_colectivo de ninguno), en la comunidad y por
      institución; C1 y C4 del libro son los del canon
  F5  el cargo de la corrida es kappa·Cv + Theta del canon
  F6  Shapley cierra por los dos órdenes, desde v00 y desde C4
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import ar2_comun as R
from analysis.shapley_factorial import desde_c4, shapley_dos
from scenarios.esquinas_supuestos import liquida_esquina

M = R.M


def tol(ref) -> float:
    """1 COP, o el float32 del almacen (1e-6 relativo) si es mayor: los libros se
    liquidaron en float64 sobre los flujos en memoria, y aqui se liquida sobre
    los flujos guardados en float32 (CANON §14.21: «dentro del float32»)."""
    return max(1.0, 1e-6 * abs(float(ref)))


def main() -> int:
    med = R.Medicion("m2r", "AE-5: factorial de los dos supuestos con el mercado resuelto en cada esquina")
    DAT, pb = R.bases()
    med.ok("13 almacenes canónicos con sus compuertas y la bolsa de la caché igual a la reconstruida")
    atr = R.A1.atribucion()
    cif = R.A1.cifras_articulo()
    filas, inst = [], []
    for c in R.CASOS:
        L = DAT[c]
        CU, ded1, ded4, mes = L["CU"], L["ded1"], L["ded4"], L["mes"]
        res_c = AS_res = R.AS.resumen(c)
        C1, C4 = float(res_c["C1"]), float(res_c["C4"])
        # F2: las fórmulas sobre los flujos del canon son las de e1/S
        f2 = {}
        for e, col in (("p2p", "P2P"), ("solo1", "v10"), ("solo2", "v01"), ("ninguno", "P2P_colectivo")):
            val, _ = liquida_esquina(e, L["G"], L["D"], L["v"], L["q"], CU, ded1, ded4, mes, pb)
            f2[e] = float(val.sum())
            med.exige(abs(f2[e] - float(atr.loc[c, col])) <= 1.0,
                      f"F2 {c} {e}: {f2[e]:.3f} frente a {col} de e1/S {float(atr.loc[c, col]):.3f}")
        v, kwh, ok_libro = {}, {}, {}
        for e in R.ESQUINAS:
            X = R.carga_corrida(med, R.dir_corrida("esquina", e, c), c, L)
            med.exige(f"--esquina {e}" in X["orden"], f"{c} {e}: la orden no lleva --esquina {e}")
            for k, ref in (("C1", C1), ("C4", C4)):
                med.exige(abs(float(X["res"][k]) - ref) <= 1.0, f"F4 {c} {e}: {k} del libro distinto del canon")
            val, exc = liquida_esquina(e, X["G"], X["D"], X["v"], X["q"], CU, ded1, ded4, mes, pb)
            por = val.sum(axis=1) + X["pagos"]
            v[e], kwh[e] = float(val.sum()), float(X["v"].sum())
            pa = X["pa"].set_index("Agente")
            if e == "p2p":
                med.exige(float(np.abs(X["v"] - L["v"]).max()) <= 1e-4 and float(np.abs(X["q"] - L["q"]).max()) <= 1e-4,
                          f"F1 {c}: los flujos de la esquina p2p no son los del canon")
                med.exige(abs(v[e] - float(res_c["P2P"])) <= tol(res_c["P2P"]), f"F1 {c}: P2P de la esquina p2p distinto del canon")
                libro, por_libro = float(X["res"]["P2P"]), pa["P2P"].to_numpy(float)
            elif e == "solo1":
                libro = float(X["res"]["P2P"]) - float((ded4 * X["q"]).sum())
                por_libro = pa["P2P"].to_numpy(float) - (ded4 * X["q"]).sum(axis=1)
            elif e == "ninguno":
                libro, por_libro = float(X["res"]["P2P_colectivo"]), pa["P2P_colectivo"].to_numpy(float)
            else:
                libro, por_libro = None, None
            if libro is not None:
                med.exige(abs(v[e] - libro) <= tol(libro), f"F4 {c} {e}: {v[e]:.3f} frente a {libro:.3f} del libro")
                med.exige(float(np.abs(por - por_libro).max()) <= tol(np.abs(por_libro).max()), f"F4 {c} {e}: por institución distinto del libro")
            if X["cargo"] is not None:
                med.exige(e in ("solo1", "ninguno"), f"{c} {e}: lleva cargo y no debía")
                med.exige(float(np.abs(X["cargo"] - ded4).max()) <= 0.01,
                          f"F5 {c} {e}: el cargo no es kappa·Cv + Theta del canon "
                          f"({float(np.abs(X['cargo'] - ded4).max()):.4f})")
            else:
                med.exige(e in ("p2p", "solo2"), f"{c} {e}: le falta el cargo")
            for n, ag in enumerate(L["ags"]):
                inst.append(dict(caso=c, esquina=e, institucion=ag, valor_COP=float(por[n]),
                                 vendido_kwh=float(X["v"][n].sum()), comprado_kwh=float(X["q"][n].sum()),
                                 exceso_kwh=float(exc[n].sum())))
        if c in AS_EXACTA:
            med.exige(kwh["solo1"] == 0.0 and abs(v["solo1"] - C1) <= tol(C1),
                      f"F3 {c}: solo1 transa {kwh['solo1']:.4f} kWh o no vale C1 ({v['solo1'] - C1:.3f})")
        sh = shapley_dos(v["ninguno"], v["solo1"], v["solo2"], v["p2p"])
        s4 = desde_c4(sh, v["ninguno"], C4)
        med.exige(abs(sh["shapley_s1"] + sh["shapley_s2"] - sh["total"]) <= 1e-6
                  and abs(sh["orden1_s1"] + sh["orden1_s2"] - sh["total"]) <= 1e-6
                  and abs(sh["orden2_s1"] + sh["orden2_s2"] - sh["total"]) <= 1e-6
                  and abs(s4["shapley_s1"] + s4["shapley_s2"] - (v["p2p"] - C4)) <= 1e-6, f"F6 {c}: Shapley no cierra")
        art1, art2 = float(cif[f"atr__{c}__shapley_s1"]), float(cif[f"atr__{c}__shapley_s2"])
        fil = dict(caso=c, C1_COP=C1, C4_COP=C4,
                   v11_COP=v["p2p"], v10_COP=v["solo1"], v01_COP=v["solo2"], v00_COP=v["ninguno"],
                   v11_kwh=kwh["p2p"], v10_kwh=kwh["solo1"], v01_kwh=kwh["solo2"], v00_kwh=kwh["ninguno"],
                   fijos_v10_COP=f2["solo1"], fijos_v01_COP=f2["solo2"], fijos_v00_COP=f2["ninguno"],
                   total_COP=sh["total"], orden1_s1_COP=sh["orden1_s1"], orden1_s2_COP=sh["orden1_s2"],
                   orden2_s1_COP=sh["orden2_s1"], orden2_s2_COP=sh["orden2_s2"],
                   shapley_s1_COP=sh["shapley_s1"], shapley_s2_COP=sh["shapley_s2"], interaccion_COP=sh["interaccion"],
                   c4_shapley_s1_COP=s4["shapley_s1"], c4_shapley_s2_COP=s4["shapley_s2"],
                   articulo_shapley_s1_MCOP=art1, articulo_shapley_s2_MCOP=art2,
                   v10_menos_C1_COP=v["solo1"] - C1, v00_menos_C4_COP=v["ninguno"] - C4,
                   v01_menos_C4_COP=v["solo2"] - C4, v11_menos_C4_COP=v["p2p"] - C4)
        filas.append(fil)
        med.di(f"{c}: v11 {v['p2p']/M:.3f}, v10 {v['solo1']/M:.3f}, v01 {v['solo2']/M:.3f}, v00 {v['ninguno']/M:.3f} MCOP; "
               f"Shapley desde C4 s1 {s4['shapley_s1']/M:.3f} (artículo {art1:.3f}), s2 {s4['shapley_s2']/M:.3f} ({art2:.3f})")
    med.ok("F1: la esquina p2p reproduce los flujos del canon (1e-4 kWh) y su P2P (1 COP o el float32 del almacén, 1e-6 relativo) en los 13 casos")
    med.ok("F2: las cuatro fórmulas sobre los flujos del canon son P2P, v10, v01 y P2P_colectivo de e1/S (1 COP) en los 13 casos")
    med.ok("F3: solo1 no transa y vale C1 (1 COP o 1e-6 relativo) en E0, K1, CV2 y SINU")
    med.ok("F4: cada liquidación es la de su libro (p2p, solo1 y ninguno; comunidad e instituciones, 1 COP o 1e-6 relativo) y C1 y C4 de "
           "las 52 corridas son los del canon")
    med.ok("F5: el cargo de solo1 y ninguno es kappa·Cv + Theta del canon (0,01 COP/kWh); p2p y solo2 no llevan cargo")
    med.ok("F6: Shapley cierra por los dos órdenes, desde la esquina ninguno y desde C4, en los 13 casos")
    # B1 de la auditoria (2026-11-21): en los ocho casos con corte, el piso de
    # solo1 uso el corte del lado corto entero y en esa esquina se transa mucho
    # menos; v10, y con ella el Shapley, la interaccion y el primer orden,
    # quedan PENDIENTES de la corrida con el punto fijo de su corte. No se
    # registran: van vacias, con su estado.
    for f in filas:
        f["estado"] = "pendiente_B1" if f["caso"] in R.CON_CORTE else "registrado"
        if f["estado"] != "registrado":
            for k in PENDIENTES:
                f[k] = np.nan
    for x in inst:
        x["estado"] = ("pendiente_B1" if x["caso"] in R.CON_CORTE and x["esquina"] == "solo1" else "registrado")
        if x["estado"] != "registrado":
            for k in ("valor_COP", "vendido_kwh", "comprado_kwh", "exceso_kwh"):
                x[k] = np.nan
    T = pd.DataFrame(filas)
    med.tabla(T, "m2r_factorial.csv")
    med.tabla(pd.DataFrame(inst), "m2r_factorial_instituciones.csv")
    fuente = "articulo_r1_resuelta_2026-11-21/m2r_factorial.csv"
    for f in filas:
        c = f["caso"]
        for k in ("v11", "v10", "v01", "v00", "total", "orden1_s1", "orden1_s2", "orden2_s1", "orden2_s2",
                  "shapley_s1", "shapley_s2", "interaccion", "c4_shapley_s1", "c4_shapley_s2",
                  "v10_menos_C1", "v00_menos_C4", "v01_menos_C4", "v11_menos_C4"):
            if np.isfinite(f[f"{k}_COP"]):
                med.pon(f"m2r__{c}__{k}", f[f"{k}_COP"] / M, "MCOP", fuente)
        for k in ("v11", "v10", "v01", "v00"):
            if np.isfinite(f[f"{k}_kwh"]):
                med.pon(f"m2r__{c}__{k}_kwh", f[f"{k}_kwh"], "kWh", fuente)
        for k in ("c4_shapley_s1", "c4_shapley_s2"):
            if not np.isfinite(f[f"{k}_COP"]):
                continue
            art = f[f"articulo_shapley_s{k[-1]}_MCOP"]
            med.pon(f"m2r__{c}__{k}_menos_articulo", f[f"{k}_COP"] / M - art, "MCOP", fuente)
        if f["estado"] == "registrado":
            med.pon(f"m2r__{c}__s1_domina", int(abs(f["c4_shapley_s1_COP"]) > abs(f["c4_shapley_s2_COP"])), "0/1", fuente)
    med.pon("m2r__casos_v00_bajo_C4", int(sum(f["v00_menos_C4_COP"] < -1.0 for f in filas)), "casos", fuente)
    med.pon("m2r__casos_pendientes_B1", int(sum(f["estado"] != "registrado" for f in filas)), "casos", fuente)
    med.cierra()
    return 0


AS_EXACTA = {"E0", "K1", "CV2", "SINU"}
# lo que depende de v10 (B1): no se registra en los casos con corte
PENDIENTES = ("v10_COP", "v10_kwh", "orden1_s1_COP", "orden1_s2_COP", "shapley_s1_COP", "shapley_s2_COP",
              "interaccion_COP", "c4_shapley_s1_COP", "c4_shapley_s2_COP", "v10_menos_C1_COP", "fijos_v10_COP")

if __name__ == "__main__":
    sys.exit(main())
