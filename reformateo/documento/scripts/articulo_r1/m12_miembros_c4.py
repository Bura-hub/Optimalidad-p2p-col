"""
m12_miembros_c4.py — Las instituciones que ganan menos con el mercado P2P que
con C4, y con C1 (CANON §14.41, punto 6)
===============================================================================
Actividades 3.2 y 4.2. Revisión r1 del artículo: se cita que en E0 cuatro de
las cinco instituciones quedan por debajo de C4, que son 25 de los 64 pares
institución-caso de los 13 casos, y que ninguna queda por debajo de C1. El
canon tiene los 25 y los 0 de 64 como claves (`institucion__P2P_menos_C4__negativos`
e `institucion__P2P_menos_C1__negativos`, §14.18, grupo e1/R) y cada brecha de
E0 frente a C4 (`institucion__E0__<institución>__P2P_menos_C4`), pero no el
recuento de E0 ni las brechas de E0 frente a C1. Este guion los da como claves,
sin simular, desde dos artefactos con huella del canon del 19-sep:

  compara_matriz_reposo.csv (grupo comparacion)    P2P − C1 y P2P − C4 por
                                                   institución, columnas *_nueva
  optimalidad_D72/resumen_13casos.csv (optimalidad_D72)  P2P − C4 por institución
                                                   en el horizonte (delta_COP)

«Por debajo» es una brecha negativa, la convención de los 25 de 64 (§14.18).
Se informa además cuántas quedan a menos de max(1 COP, 1e-6 del beneficio),
el empate de `compara_matriz_reposo.csv`.

Compuertas:
  P1  64 pares institución-caso (13 casos; Udenar falta en uno), sin la fila de
      la comunidad, en las dos fuentes, con los mismos pares
  P2  P2P − C4 de las dos fuentes coincide en cada par (1 COP)
  P3  los recuentos reproducen las claves de §14.18 (25 y 0 de 64) y las
      brechas de E0 frente a C4 son las de `institucion__E0__*`
  P4  ningún par a menos del umbral de empate cambia el recuento
"""
from __future__ import annotations

import sys

import pandas as pd

import ar2_comun as R

AS = R.AS
M = R.M
F_CMP = "compara_matriz_reposo.csv"
F_D72 = "optimalidad_D72/resumen_13casos.csv"
F_R = "cifras_cap07_2026-09-28/cifras.csv"
FUENTE = "compara_matriz_reposo.csv (canon del 19-sep), columnas P2P_menos_C1_nueva y P2P_menos_C4_nueva"


def main() -> int:
    med = R.Medicion("m12", "las instituciones por debajo de C4 y de C1 con el mercado P2P")
    cmp_ = pd.read_csv(AS.lee(F_CMP, "comparacion"), comment="#")
    cmp_ = cmp_[cmp_.institucion != "comunidad"].set_index(["caso", "institucion"])
    d72 = pd.read_csv(AS.lee(F_D72, "optimalidad_D72"))
    d72 = d72[d72.agente != "Comunidad"].set_index(["caso", "agente"])
    med.exige(len(cmp_) == 64 and len(d72) == 64 and set(cmp_.index) == set(d72.index),
              "los pares institución-caso no son 64 o no coinciden entre las dos fuentes")
    med.ok("P1: 64 pares institución-caso en las dos fuentes, los mismos, sin la fila de la comunidad")
    a = cmp_.P2P_menos_C4_nueva.astype(float)
    b = d72.delta_COP.astype(float).reindex(a.index)
    med.exige(bool(((a - b).abs() <= 1.0).all()), "P2P − C4 distinto entre compara_matriz_reposo.csv y resumen_13casos.csv")
    med.ok(f"P2: P2P − C4 coincide en los 64 pares (máx. {float((a - b).abs().max()):.4f} COP)")
    c4 = a
    c1 = cmp_.P2P_menos_C1_nueva.astype(float)
    ben = cmp_.beneficio_P2P_nueva.astype(float).abs()
    umbral = ben.mul(1e-6).clip(lower=1.0)
    n4, n1 = int((c4 < 0).sum()), int((c1 < 0).sum())
    e0 = c4.xs("E0", level="caso")
    e0c1 = c1.xs("E0", level="caso")
    r = pd.read_csv(AS.lee(F_R, "e1/R")).set_index("clave").valor
    med.exige(n4 == int(float(r["institucion__P2P_menos_C4__negativos"])) == 25
              and n1 == int(float(r["institucion__P2P_menos_C1__negativos"])) == 0,
              "los recuentos no reproducen las claves de §14.18")
    med.exige(all(abs(float(e0[i]) - float(r[f"institucion__E0__{i}__P2P_menos_C4"])) <= 1.0 for i in e0.index),
              "las brechas de E0 frente a C4 no son las de institucion__E0__*")
    med.ok("P3: 25 de 64 bajo C4 y 0 de 64 bajo C1, como §14.18; las brechas de E0 frente a C4 son las de institucion__E0__*")
    cerca4 = int(((c4.abs() <= umbral)).sum())
    cerca1 = int(((c1.abs() <= umbral)).sum())
    med.exige(cerca4 == 0 and cerca1 == 0, f"{cerca4} y {cerca1} pares en empate cambiarían el recuento")
    med.ok("P4: ningún par queda a menos del umbral de empate, ni frente a C4 ni frente a C1")
    bajo = [i for i in e0.index if e0[i] < 0]
    med.di(f"  E0: {len(bajo)} de {len(e0)} bajo C4 ({', '.join(bajo)}); {int((e0c1 < 0).sum())} bajo C1, "
           f"la menor P2P − C1 {float(e0c1.min()) / M:.4f} MCOP ({e0c1.idxmin()}); 13 casos: {n4} y {n1} de 64")
    T = pd.DataFrame({"P2P_menos_C1_COP": c1, "P2P_menos_C4_COP": c4, "umbral_empate_COP": umbral}).reset_index()
    med.tabla(T, "m12_miembros_c4.csv")
    med.pon("miembros__E0__instituciones", len(e0), "instituciones", FUENTE)
    med.pon("miembros__E0__bajo_C4", len(bajo), "instituciones", FUENTE + "; P2P − C4 < 0")
    med.pon("miembros__E0__bajo_C1", int((e0c1 < 0).sum()), "instituciones", FUENTE + "; P2P − C1 < 0")
    med.pon("miembros__E0__min_P2P_menos_C1", float(e0c1.min()) / M, "MCOP", FUENTE + f"; la de {e0c1.idxmin()}")
    med.pon("miembros__E0__min_P2P_menos_C4", float(e0.min()) / M, "MCOP", FUENTE + f"; la de {e0.idxmin()}")
    for i in e0.index:
        med.pon(f"miembros__E0__{i}__P2P_menos_C1", float(e0c1[i]) / M, "MCOP", FUENTE)
    med.pon("miembros__pares", 64, "pares", FUENTE)
    med.pon("miembros__pares_bajo_C4", n4, "pares", FUENTE + "; = institucion__P2P_menos_C4__negativos (e1/R)")
    med.pon("miembros__pares_bajo_C1", n1, "pares", FUENTE + "; = institucion__P2P_menos_C1__negativos (e1/R)")
    med.cierra()
    return 0


if __name__ == "__main__":
    sys.exit(main())
