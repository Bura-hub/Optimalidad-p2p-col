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

B1 de la auditoría (2026-11-21). En los ocho casos con corte, v10 sale del
retome con el punto fijo del corte de solo1 (`matriz_esquina_solo1_iterado`,
`--esquina solo1 --corte-piso iterado`). Donde el punto fijo entra en un ciclo
de dos estados, los dos están corridos (`<caso>_ciclo`) y v10, Shapley y la
interacción se dan como intervalo entre ellos. En los cinco casos sin corte,
v10 es la corrida de solo1 de la matriz (allí no hay corte que fijar).

Compuertas (falla en voz alta):
  F1  la esquina p2p reproduce los flujos del canon (float32) y su P2P
  F2  las cuatro fórmulas sobre los flujos del canon son las de e1/S
  F3  solo1 no transa y vale C1 en E0, K1, CV2 y SINU
  F4  cada liquidación sobre su corrida es la de su libro, en la comunidad y por
      institución; C1 y C4 del libro son los del canon
  F5  el cargo de la corrida es kappa·Cv + Theta del canon
  F6  Shapley cierra por los dos órdenes, desde v00 y desde C4
  F7  el punto fijo de solo1: en cada estado, la marca del piso es la del Anexo 4
      sobre sus propios residuales salvo en las horas-vendedor del ciclo
"""
from __future__ import annotations

import re
import sys

import numpy as np
import pandas as pd

import ar2_comun as R
from analysis.shapley_factorial import desde_c4, shapley_dos
from core.opciones_externas import reparto_anexo4
from scenarios.esquinas_supuestos import liquida_esquina

M = R.M
AS_EXACTA = {"E0", "K1", "CV2", "SINU"}
CLAVES = ("total", "orden1_s1", "orden1_s2", "orden2_s1", "orden2_s2", "shapley_s1", "shapley_s2", "interaccion",
          "c4_shapley_s1", "c4_shapley_s2")


def tol(ref) -> float:
    """1 COP, o el float32 del almacen (1e-6 relativo) si es mayor: los libros se
    liquidaron en float64 sobre los flujos en memoria, y aqui se liquida sobre
    los flujos guardados en float32 (CANON §14.21: «dentro del float32»)."""
    return max(1.0, 1e-6 * abs(float(ref)))


def iteraciones(c: str, ciclo: bool) -> str:
    pat = f"esquina_solo1_iterado_{'ciclo_' if ciclo else ''}{c}_2026-11-21_*.log"
    regs = sorted((R.RAIZ / "modelo_base" / "logs").glob(pat))
    if not regs:
        return ""
    t = regs[-1].read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\[R1\] Corte iterado \(AE-4\): (\d+) iteraciones; .*?: (\[[^\]]*\]); (\w+)", t)
    return f"{m.group(1)} {m.group(2)} {m.group(3)}" if m else ""


def liquida_corrida(med, d, c, L, e, pb):
    """(valor de la comunidad, por institución, kWh, corrida)."""
    X = R.carga_corrida(med, d, c, L)
    val, exc = liquida_esquina(e, X["G"], X["D"], X["v"], X["q"], L["CU"], L["ded1"], L["ded4"], L["mes"], pb)
    return float(val.sum()), val.sum(axis=1) + X["pagos"], float(X["v"].sum()), X, exc


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
        res_c = R.AS.resumen(c)
        C1, C4 = float(res_c["C1"]), float(res_c["C4"])
        f2 = {}
        for e, col in (("p2p", "P2P"), ("solo1", "v10"), ("solo2", "v01"), ("ninguno", "P2P_colectivo")):
            val, _ = liquida_esquina(e, L["G"], L["D"], L["v"], L["q"], CU, ded1, ded4, mes, pb)
            f2[e] = float(val.sum())
            med.exige(abs(f2[e] - float(atr.loc[c, col])) <= 1.0,
                      f"F2 {c} {e}: {f2[e]:.3f} frente a {col} de e1/S {float(atr.loc[c, col]):.3f}")
        v, kwh, por_e = {}, {}, {}
        for e in R.ESQUINAS:
            d = R.dir_corrida("esquina", e, c)
            v[e], por, kwh[e], X, exc = liquida_corrida(med, d, c, L, e, pb)
            med.exige(f"--esquina {e}" in X["orden"], f"{c} {e}: la orden no lleva --esquina {e}")
            for k, ref in (("C1", C1), ("C4", C4)):
                med.exige(abs(float(X["res"][k]) - ref) <= 1.0, f"F4 {c} {e}: {k} del libro distinto del canon")
            pa = X["pa"]
            if e == "p2p":
                med.exige(float(np.abs(X["v"] - L["v"]).max()) <= 1e-4 and float(np.abs(X["q"] - L["q"]).max()) <= 1e-4,
                          f"F1 {c}: los flujos de la esquina p2p no son los del canon")
                med.exige(abs(v[e] - float(res_c["P2P"])) <= tol(res_c["P2P"]), f"F1 {c}: P2P de p2p distinto del canon")
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
                med.exige(float(np.abs(por - por_libro).max()) <= tol(np.abs(por_libro).max()),
                          f"F4 {c} {e}: por institución distinto del libro")
            if X["cargo"] is not None:
                med.exige(e in ("solo1", "ninguno") and float(np.abs(X["cargo"] - ded4).max()) <= 0.01,
                          f"F5 {c} {e}: el cargo no es kappa·Cv + Theta del canon")
            else:
                med.exige(e in ("p2p", "solo2"), f"{c} {e}: le falta el cargo")
            por_e[e] = (por, X, exc)
        if c in AS_EXACTA:
            med.exige(kwh["solo1"] == 0.0 and abs(v["solo1"] - C1) <= tol(C1),
                      f"F3 {c}: solo1 transa {kwh['solo1']:.4f} kWh o no vale C1 ({v['solo1'] - C1:.3f})")
        # v10: en los casos con corte, el punto fijo del retome (uno o dos estados)
        v10_lado_corto, kwh10_lado_corto = v["solo1"], kwh["solo1"]
        est = []
        if c in R.CON_CORTE:
            for k, d in enumerate(R.estados(R.RETOME_ESQ, c)):
                val10, por10, kwh10, X, _ = liquida_corrida(med, d, c, L, "solo1", pb)
                med.exige("--esquina solo1 --corte-piso iterado" in X["orden"] and X["commit"] == "e1a0e40",
                          f"{c}: el retome de solo1 no es --esquina solo1 --corte-piso iterado de e1a0e40")
                for kk, ref in (("C1", C1), ("C4", C4)):
                    med.exige(abs(float(X["res"][kk]) - ref) <= 1.0, f"F4 {c} retome: {kk} del libro distinto del canon")
                libro = float(X["res"]["P2P"]) - float((ded4 * X["q"]).sum())
                med.exige(abs(val10 - libro) <= tol(libro), f"F4 {c} retome: solo1 distinto de su libro")
                med.exige(X["cargo"] is not None and float(np.abs(X["cargo"] - ded4).max()) <= 0.01,
                          f"F5 {c} retome: el cargo no es kappa·Cv + Theta")
                sr = np.maximum(L["s"] - X["v"], 0.0)
                dr = np.maximum(L["d"] - X["q"], 0.0)
                perm = reparto_anexo4(sr, dr, mes)[2]
                piso_perm = np.abs(X["piso"] - (CU - ded1)) <= 0.01
                vende = L["s"] > 1e-9
                mal = int((vende & (piso_perm != perm)).sum())
                est.append(dict(v10=val10, kwh=kwh10, por=por10, mal=mal, ciclo=d.name.endswith("_ciclo")))
            it_a = iteraciones(c, False)
            n_ciclo = [int(x) for x in re.findall(r"\d+", it_a.split("[", 1)[1])][-1] if "CICLO" in it_a else 0
            for x in est:
                med.exige(x["mal"] <= max(n_ciclo, 0) + 0, f"F7 {c}: {x['mal']} horas-vendedor con la marca del piso "
                          f"distinta de su liquidación (el ciclo mueve {n_ciclo})")
            med.exige(("CICLO" in it_a) == (len(est) == 2), f"{c}: el ciclo y el número de estados no cuadran")
        else:
            est.append(dict(v10=v["solo1"], kwh=kwh["solo1"], por=por_e["solo1"][0], mal=0, ciclo=False))
            it_a = ""
        sh = [shapley_dos(v["ninguno"], x["v10"], v["solo2"], v["p2p"]) for x in est]
        s4 = [desde_c4(h, v["ninguno"], C4) for h in sh]
        for h, h4 in zip(sh, s4):
            med.exige(abs(h["shapley_s1"] + h["shapley_s2"] - h["total"]) <= 1e-6
                      and abs(h["orden1_s1"] + h["orden1_s2"] - h["total"]) <= 1e-6
                      and abs(h["orden2_s1"] + h["orden2_s2"] - h["total"]) <= 1e-6
                      and abs(h4["shapley_s1"] + h4["shapley_s2"] - (v["p2p"] - C4)) <= 1e-6, f"F6 {c}: Shapley no cierra")
        art1, art2 = float(cif[f"atr__{c}__shapley_s1"]), float(cif[f"atr__{c}__shapley_s2"])
        fil = dict(caso=c, C1_COP=C1, C4_COP=C4, v11_COP=v["p2p"], v01_COP=v["solo2"], v00_COP=v["ninguno"],
                   v11_kwh=kwh["p2p"], v01_kwh=kwh["solo2"], v00_kwh=kwh["ninguno"],
                   v10_min_COP=min(x["v10"] for x in est), v10_max_COP=max(x["v10"] for x in est),
                   v10_kwh_min=min(x["kwh"] for x in est), v10_kwh_max=max(x["kwh"] for x in est),
                   estados_v10=len(est), iteraciones_v10=it_a,
                   v10_corte_lado_corto_COP=v10_lado_corto, v10_corte_lado_corto_kwh=kwh10_lado_corto,
                   fijos_v10_COP=f2["solo1"], fijos_v01_COP=f2["solo2"], fijos_v00_COP=f2["ninguno"],
                   articulo_shapley_s1_MCOP=art1, articulo_shapley_s2_MCOP=art2,
                   v00_menos_C4_COP=v["ninguno"] - C4, v01_menos_C4_COP=v["solo2"] - C4, v11_menos_C4_COP=v["p2p"] - C4,
                   v10_menos_C1_min_COP=min(x["v10"] for x in est) - C1, v10_menos_C1_max_COP=max(x["v10"] for x in est) - C1)
        todos = [{**a, **{"c4_" + k: b[k] for k in ("shapley_s1", "shapley_s2")}} for a, b in zip(sh, s4)]
        for k in CLAVES:
            vals = [t[k] for t in todos]
            fil[f"{k}_min_COP"], fil[f"{k}_max_COP"] = min(vals), max(vals)
        fil["estado"] = ("intervalo_ciclo" if len(est) == 2 else "punto_fijo" if c in R.CON_CORTE else "sin_corte")
        fil["s1_domina_c4"] = int(all(abs(t["c4_shapley_s1"]) > abs(t["c4_shapley_s2"]) for t in todos)) - int(
            all(abs(t["c4_shapley_s1"]) < abs(t["c4_shapley_s2"]) for t in todos))
        fil["s1_domina_v00"] = int(all(abs(t["shapley_s1"]) > abs(t["shapley_s2"]) for t in todos)) - int(
            all(abs(t["shapley_s1"]) < abs(t["shapley_s2"]) for t in todos))
        fil["c4_shapley_s1_cruza_cero"] = int(fil["c4_shapley_s1_min_COP"] < 0 < fil["c4_shapley_s1_max_COP"])
        fil["shapley_s1_cruza_cero"] = int(fil["shapley_s1_min_COP"] < 0 < fil["shapley_s1_max_COP"])
        fil["interaccion_cruza_cero"] = int(fil["interaccion_min_COP"] < 0 < fil["interaccion_max_COP"])
        filas.append(fil)
        for e in R.ESQUINAS:
            if e == "solo1":
                continue
            por, X, exc = por_e[e]
            for n, ag in enumerate(L["ags"]):
                inst.append(dict(caso=c, esquina=e, estado="registrado", institucion=ag, valor_COP=float(por[n]),
                                 vendido_kwh=float(X["v"][n].sum()), comprado_kwh=float(X["q"][n].sum()),
                                 exceso_kwh=float(exc[n].sum())))
        for k, x in enumerate(est):
            for n, ag in enumerate(L["ags"]):
                inst.append(dict(caso=c, esquina="solo1", estado=("ciclo" if x["ciclo"] else fil["estado"]),
                                 institucion=ag, valor_COP=float(x["por"][n]), vendido_kwh=np.nan,
                                 comprado_kwh=np.nan, exceso_kwh=np.nan))
        med.di(f"{c}: v11 {v['p2p']/M:.3f}, v10 [{fil['v10_min_COP']/M:.3f}, {fil['v10_max_COP']/M:.3f}] "
               f"(lado corto {v10_lado_corto/M:.3f}), v01 {v['solo2']/M:.3f}, v00 {v['ninguno']/M:.3f} MCOP; "
               f"desde C4 s1 [{fil['c4_shapley_s1_min_COP']/M:.3f}, {fil['c4_shapley_s1_max_COP']/M:.3f}] "
               f"(artículo {art1:.3f}), s2 [{fil['c4_shapley_s2_min_COP']/M:.3f}, {fil['c4_shapley_s2_max_COP']/M:.3f}] "
               f"({art2:.3f}); {it_a}")
    med.ok("F1: la esquina p2p reproduce los flujos del canon (1e-4 kWh) y su P2P (1 COP o el float32 del almacén, 1e-6 relativo) en los 13 casos")
    med.ok("F2: las cuatro fórmulas sobre los flujos del canon son P2P, v10, v01 y P2P_colectivo de e1/S (1 COP) en los 13 casos")
    med.ok("F3: solo1 no transa y vale C1 (1 COP o 1e-6 relativo) en E0, K1, CV2 y SINU")
    med.ok("F4: cada liquidación es la de su libro (p2p, solo1, ninguno y el retome de solo1; comunidad e instituciones) y C1 y "
           "C4 de las 52 corridas y de las 14 del retome son los del canon")
    med.ok("F5: el cargo de solo1 (matriz y retome) y de ninguno es kappa·Cv + Theta del canon (0,01 COP/kWh); p2p y solo2 sin cargo")
    med.ok("F6: Shapley cierra por los dos órdenes, desde la esquina ninguno y desde C4, en cada estado de los 13 casos")
    med.ok("F7: en el retome de solo1, la marca del piso es la del Anexo 4 sobre los residuales de su propio estado salvo "
           "en las horas-vendedor que mueve el ciclo; el ciclo y los dos estados cuadran con la línea [R1]")
    T = pd.DataFrame(filas)
    med.tabla(T, "m2r_factorial.csv")
    med.tabla(pd.DataFrame(inst), "m2r_factorial_instituciones.csv")
    fuente = "articulo_r1_resuelta_2026-11-21/m2r_factorial.csv"
    for f in filas:
        c = f["caso"]
        for k in ("v11", "v01", "v00", "v00_menos_C4", "v01_menos_C4", "v11_menos_C4"):
            med.pon(f"m2r__{c}__{k}", f[f"{k}_COP"] / M, "MCOP", fuente)
        for k in ("v11", "v01", "v00"):
            med.pon(f"m2r__{c}__{k}_kwh", f[f"{k}_kwh"], "kWh", fuente)
        for k in ("v10", "v10_menos_C1") + CLAVES:
            lo, hi = f[f"{k}_min_COP"], f[f"{k}_max_COP"]
            med.pon(f"m2r__{c}__{k}_min", lo / M, "MCOP", fuente)
            med.pon(f"m2r__{c}__{k}_max", hi / M, "MCOP", fuente)
            if f["estados_v10"] == 1:
                med.pon(f"m2r__{c}__{k}", lo / M, "MCOP", fuente)
        med.pon(f"m2r__{c}__v10_kwh_min", f["v10_kwh_min"], "kWh", fuente)
        med.pon(f"m2r__{c}__v10_kwh_max", f["v10_kwh_max"], "kWh", fuente)
        med.pon(f"m2r__{c}__estados_v10", int(f["estados_v10"]), "n", fuente)
        for k in ("s1_domina_c4", "s1_domina_v00", "c4_shapley_s1_cruza_cero", "shapley_s1_cruza_cero",
                  "interaccion_cruza_cero"):
            med.pon(f"m2r__{c}__{k}", int(f[k]), "-1/0/1", fuente)
        for k in ("c4_shapley_s1", "c4_shapley_s2"):
            art = f[f"articulo_shapley_s{k[-1]}_MCOP"]
            med.pon(f"m2r__{c}__{k}_min_menos_articulo", f[f"{k}_min_COP"] / M - art, "MCOP", fuente)
            med.pon(f"m2r__{c}__{k}_max_menos_articulo", f[f"{k}_max_COP"] / M - art, "MCOP", fuente)
    med.pon("m2r__casos_v00_bajo_C4", int(sum(f["v00_menos_C4_COP"] < -1.0 for f in filas)), "casos", fuente)
    med.pon("m2r__casos_v10_dos_estados", int(sum(f["estados_v10"] == 2 for f in filas)), "casos", fuente)
    med.pon("m2r__casos_c4_s1_cruza_cero", int(sum(f["c4_shapley_s1_cruza_cero"] for f in filas)), "casos", fuente)
    med.cierra()
    return 0


if __name__ == "__main__":
    sys.exit(main())
