"""
m2_factorial_fijos.py — M2 acotada: las cuatro combinaciones de los dos
supuestos con los flujos fijos, Shapley sobre ellas y la diferencia con la
atribución que publica el artículo
===============================================================================
Comentario AE-5 de la revisión r1. No simula ni vuelve a liquidar: lee las
esquinas que ya calculó el punto S del canon (`atribucion_13casos.csv`, grupo
e1/S, CANON §14.21).

LAS CUATRO COMBINACIONES, con los flujos del mercado fijos:

  v00  ninguno      todo pasa por el fondo de C4, caso 2, con el porcentaje
                    que sale de los flujos (columna P2P_colectivo)
  v10  solo el 1    residual por miembro, como en C1, y cada kWh intercambiado
                    paga la deducción del caso 2 del comprador (κ·Cv + Θ)
  v01  solo el 2    intercambio exento y residual al fondo de C4, caso 2
  v11  los dos      el mercado P2P

QUÉ SIGNIFICA «FLUJOS FIJOS». En las cuatro esquinas, cada miembro vende y
compra dentro los mismos kWh, en las mismas horas, que en el mercado P2P del
canon. Solo cambia cómo se liquidan. NO se vuelve a resolver el mercado, de modo
que una esquina obliga a transar aunque el par pierda. Por eso v10 queda bajo C1
donde transar con cargos no compensa. El factorial con el mercado resuelto en
cada esquina no está hecho: exige un piso nuevo en el núcleo.

LA ATRIBUCIÓN DEL ARTÍCULO usa otras esquinas: parte de C4 (no de v00) y mide
«solo el 1» con C1, donde nadie transa (no con v10).

LA COTA. La esquina «solo el 1» con el mercado resuelto queda entre
máx(C1, v10) y el mercado P2P (CANON §14.21). Con ella se acota el Shapley del
supuesto 1 que da el artículo.

Escribe m2_factorial.csv.

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo_r1/m2_factorial_fijos.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import ar1_comun as C

FU = "atribucion_supuestos_2026-09-30/atribucion_13casos.csv (e1/S), columnas P2P_colectivo, v10, v01, P2P, C1 y C4"


def main() -> int:
    med = C.Medicion("m2", "factorial de los dos supuestos con los flujos fijos y Shapley sobre él")
    A = C.atribucion()
    cif = C.cifras_articulo()
    med.exige(list(A.index) == C.CASOS, "casos distintos en atribucion_13casos.csv")
    T = pd.DataFrame(index=A.index)
    T["v00"], T["v10"], T["v01"], T["v11"], T["C1"], T["C4"] = A.P2P_colectivo, A.v10, A.v01, A.P2P, A.C1, A.C4
    # Shapley sobre el factorial con flujos fijos
    T["fijos_s1_primero"] = T.v10 - T.v00                 # el 1 sin el 2
    T["fijos_s1_despues"] = T.v11 - T.v01                 # el 1 con el 2
    T["fijos_s2_primero"] = T.v01 - T.v00
    T["fijos_s2_despues"] = T.v11 - T.v10
    T["fijos_shapley_s1"] = 0.5 * (T.fijos_s1_primero + T.fijos_s1_despues)
    T["fijos_shapley_s2"] = 0.5 * (T.fijos_s2_primero + T.fijos_s2_despues)
    T["fijos_total"] = T.v11 - T.v00
    T["fijos_interaccion"] = T.fijos_s1_despues - T.fijos_s1_primero
    med.exige(float((T.fijos_shapley_s1 + T.fijos_shapley_s2 - T.fijos_total).abs().max()) <= 1e-6,
              "Shapley con flujos fijos no suma v11 − v00")
    for k, col in (("fijos_s1_primero", "fijos_s1_sin_s2"), ("fijos_s1_despues", "fijos_s1_con_s2"),
                   ("fijos_s2_primero", "fijos_s2_sin_s1"), ("fijos_s2_despues", "fijos_s2_con_s1"),
                   ("fijos_interaccion", "fijos_interaccion")):
        med.exige(float((T[k] - A[col]).abs().max()) <= 1e-3, f"{k} distinto de la columna {col} del punto S")
    med.ok("los cuatro incrementos y la interacción con flujos fijos son las columnas fijos_* del punto S, y Shapley suma v11 − v00")
    # La atribución que publica el artículo
    T["art_shapley_s1"], T["art_shapley_s2"], T["art_total"] = A.shapley_s1, A.shapley_s2, A.P2P_menos_C4
    for c in C.CASOS:
        for k in ("shapley_s1", "shapley_s2"):
            med.exige(abs(T.loc[c, f"art_{k}"] / C.M - float(cif[f"atr__{c}__{k}"])) <= 1e-6, f"{c}: {k} distinto de atr__{c}__{k}")
    med.ok("la atribución actual es la de las claves atr__<caso>__shapley_s1 y _s2 del artículo, en los 13 casos")
    T["dif_shapley_s1"] = T.fijos_shapley_s1 - T.art_shapley_s1
    T["dif_shapley_s2"] = T.fijos_shapley_s2 - T.art_shapley_s2
    T["dif_total"] = T.fijos_total - T.art_total          # = C4 − v00: lo que el mercado sin supuestos queda bajo C4
    T["v00_menos_C4"] = T.v00 - T.C4
    T["v10_menos_C1"] = T.v10 - T.C1
    # Cota de la esquina «solo el 1» con el mercado resuelto y del Shapley del artículo (base C4)
    T["solo1_min"] = np.maximum(T.C1, T.v10)
    exacta = A.c1_esquina_exacta.astype(bool)
    T["solo1_max"] = np.where(exacta, T.C1, T.v11)        # donde con cargos nadie transaría, la esquina es C1
    T["cota_shapley_s1_min"] = 0.5 * ((T.solo1_min - T.C4) + (T.v11 - T.v01))
    T["cota_shapley_s1_max"] = 0.5 * ((T.solo1_max - T.C4) + (T.v11 - T.v01))
    T["cota_shapley_s2_min"] = T.art_total - T.cota_shapley_s1_max
    T["cota_shapley_s2_max"] = T.art_total - T.cota_shapley_s1_min
    T["C1_esquina_exacta"] = A.c1_esquina_exacta.astype(int)
    T["ganancia_max_par_con_cargos_COP_kWh"] = A.ganancia_max_intercambio_con_cargos
    ex = T[T.C1_esquina_exacta == 1]
    med.exige(sorted(ex.index) == sorted(["E0", "K1", "CV2", "SINU"]) and bool((ex.solo1_min == ex.C1).all())
              and float((ex.cota_shapley_s1_min - ex.art_shapley_s1).abs().max()) <= 1e-6,
              "donde C1 es la esquina exacta, la cota inferior no es la atribución del artículo")
    med.ok("en E0, K1, CV2 y SINU, donde con cargos ningún par gana, C1 es la esquina exacta y la cota inferior del Shapley del supuesto 1 es la cifra del artículo")
    med.exige(bool((T.cota_shapley_s1_min >= T.art_shapley_s1 - 1e-6).all()), "la cota inferior queda bajo la cifra del artículo")
    med.ok("el Shapley del supuesto 1 que publica el artículo es una cota inferior en los 13 casos")
    signo = lambda x: np.sign(np.where(np.abs(x) < 0.5, 0.0, x))
    T["s1_cambia_de_signo"] = (signo(T.fijos_shapley_s1) * signo(T.art_shapley_s1) < 0).astype(int)
    manda = lambda s1, s2: np.where(s1 > s2, 1, 2)
    T["manda_articulo"] = manda(T.art_shapley_s1, T.art_shapley_s2)
    T["manda_fijos"] = manda(T.fijos_shapley_s1, T.fijos_shapley_s2)
    med.tabla(T.reset_index(), "m2_factorial.csv")
    cop = ["v00", "v10", "v01", "v11", "fijos_s1_primero", "fijos_s1_despues", "fijos_s2_primero", "fijos_s2_despues",
           "fijos_shapley_s1", "fijos_shapley_s2", "fijos_total", "fijos_interaccion", "dif_shapley_s1", "dif_shapley_s2",
           "dif_total", "v00_menos_C4", "v10_menos_C1", "solo1_min", "solo1_max", "cota_shapley_s1_min",
           "cota_shapley_s1_max", "cota_shapley_s2_min", "cota_shapley_s2_max"]
    for c, r in T.iterrows():
        for k in cop:
            med.pon(f"m2__{c}__{k}", r[k] / C.M, "MCOP", FU)
        med.pon(f"m2__{c}__v00_menos_C4_sobre_ventaja_pct", 100 * r.v00_menos_C4 / r.art_total, "% de P2P − C4", FU)
        med.pon(f"m2__{c}__manda_articulo", int(r.manda_articulo), "supuesto", FU)
        med.pon(f"m2__{c}__manda_fijos", int(r.manda_fijos), "supuesto", FU)
    med.pon("m2__casos_manda_distinto", int((T.manda_articulo != T.manda_fijos).sum()), "casos de 13", FU)
    med.pon("m2__casos_s1_cambia_de_signo", int(T.s1_cambia_de_signo.sum()), "casos de 13", FU)
    med.pon("m2__interaccion_fijos_max_abs", float(T.fijos_interaccion.abs().max() / C.M), "MCOP", FU)
    for c in ["E0", "E3", "E4", "I1", "SINU"]:
        r = T.loc[c]
        med.di(f"  {c}: artículo s1 {r.art_shapley_s1 / C.M:.3f}, s2 {r.art_shapley_s2 / C.M:.3f} (total {r.art_total / C.M:.3f}); "
               f"flujos fijos s1 {r.fijos_shapley_s1 / C.M:.3f}, s2 {r.fijos_shapley_s2 / C.M:.3f} (total {r.fijos_total / C.M:.3f}); "
               f"cota del s1 con el mercado resuelto [{r.cota_shapley_s1_min / C.M:.3f}; {r.cota_shapley_s1_max / C.M:.3f}]; "
               f"v00 − C4 {r.v00_menos_C4 / C.M:.3f}; v10 − C1 {r.v10_menos_C1 / C.M:.3f}")
    med.di(f"  manda otro supuesto con flujos fijos en: {', '.join(T.index[T.manda_articulo != T.manda_fijos]) or 'ningún caso'}; "
           f"el Shapley del supuesto 1 cambia de signo en: {', '.join(T.index[T.s1_cambia_de_signo == 1]) or 'ningún caso'}")
    med.cierra()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
