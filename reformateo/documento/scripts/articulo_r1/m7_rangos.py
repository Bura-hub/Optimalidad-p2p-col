"""
m7_rangos.py — M7: de dónde sale cada rango de la caja de sensibilidad
===============================================================================
Comentario C-7 de la revisión r1. No simula. Los rangos son los del análisis de
sensibilidad global del canon (§13.2, decisión D74, especificación
`docs/superpowers/specs/2026-09-26-gsa-directo-design.md`). Aquí se recalcula,
desde artefactos con huella, el dato que sustenta cada uno, y se dice cuál es
un dato histórico y cuál un supuesto.

  de deducción (Cv descontado)   SUPUESTO. El Cv pactado de un usuario no
        regulado no es público. El rango 0,25 a 2 se compara con la distancia
        entre los Cv que publican los dos comercializadores.
  de bolsa                       DATO HISTÓRICO. Medias anuales de la bolsa de
        XM de 2019, 2021, 2023 y 2024 sobre la media del horizonte de 2025 con
        su tope (`data/audit_xm_yearly_summary.csv`, sin huella en el canon:
        se registra su sha256).
  de tarifa (CU)                 DATO HISTÓRICO y margen. Recorrido del CU
        mensual de cada comercializador en los nueve meses, frente a su media.
  de cargos de red (Θ)           DATO HISTÓRICO y margen. Recorrido de Θ
        mensual frente a su media.
  errores de generación y de demanda   SUPUESTO. Exactitud de la telemetría, no
        contrastada. El de demanda cubre también las horas incompletas.

Escribe m7_rangos.csv.

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo_r1/m7_rangos.py
"""
from __future__ import annotations

import pandas as pd

import ar1_comun as C

F_XM = "data/audit_xm_yearly_summary.csv"
FU_L = "cifras_articulo_2026-09-30/cifras.csv (e1/L)"


def main() -> int:
    med = C.Medicion("m7", "sustento de los rangos de la caja de sensibilidad")
    cif = C.cifras_articulo()
    v = lambda k: float(cif[k])
    R = {k: (v(f"gsa__factor__{k}__lo"), v(f"gsa__factor__{k}__hi")) for k in ("f_cv", "f_bolsa", "f_tarifa", "f_peaje", "e_G", "e_D")}
    med.exige(R == {"f_cv": (0.25, 2.0), "f_bolsa": (0.75, 4.0), "f_tarifa": (0.9, 1.1), "f_peaje": (0.85, 1.15),
                    "e_G": (0.95, 1.05), "e_D": (0.95, 1.05)}, f"los rangos de la caja no son los de CANON §13.2: {R}")
    med.ok("los seis rangos son los de CANON §13.2 (claves gsa__factor__* del artículo)")
    filas = []

    def fila(factor, nombre, tipo, sustento, fuente, **cifras):
        lo, hi = R[factor]
        filas.append(dict(factor=factor, nombre=nombre, rango_min=lo, rango_max=hi, tipo=tipo, sustento=sustento, fuente=fuente))
        for k, (x, u) in cifras.items():
            med.pon(f"m7__{factor}__{k}", x, u, fuente)

    # Tarifa y cargos de red: recorrido mensual frente a la media del horizonte
    rec = {}
    for com, et in (("ASC", "A"), ("CEDENAR", "B")):
        for mag in ("CU", "Theta", "Cv"):
            mn, mx, me = (v(f"kwh__{com}__{mag}__{s}") for s in ("min", "max", "media"))
            rec[(et, mag)] = (100 * (mn / me - 1), 100 * (mx / me - 1), me)
    for mag, factor in (("CU", "f_tarifa"), ("Theta", "f_peaje")):
        lo = min(rec[(e, mag)][0] for e in "AB")
        hi = max(rec[(e, mag)][1] for e in "AB")
        m = 100 * (R[factor][1] - 1)
        med.exige(-m < lo and hi < m, f"{factor}: el recorrido mensual ({lo:.1f} a {hi:.1f} %) no cabe en el rango de ±{m:.0f} %")
        nombre = "de tarifa" if mag == "CU" else "de cargos de red"
        fila(factor, nombre, "dato histórico y margen",
             f"en los nueve meses del horizonte, el valor mensual se aparta de su media entre {lo:.1f} y {hi:+.1f} % "
             f"(comercializador A: {rec[('A', mag)][0]:.1f} a {rec[('A', mag)][1]:+.1f} %; B: {rec[('B', mag)][0]:.1f} a {rec[('B', mag)][1]:+.1f} %); "
             f"el rango de ±{m:.0f} % lo cubre con margen",
             FU_L + f", claves kwh__<comercializador>__{mag}__min, __max y __media",
             recorrido_min_pct=(lo, "%"), recorrido_max_pct=(hi, "%"),
             recorrido_A_min_pct=(rec[("A", mag)][0], "%"), recorrido_A_max_pct=(rec[("A", mag)][1], "%"),
             recorrido_B_min_pct=(rec[("B", mag)][0], "%"), recorrido_B_max_pct=(rec[("B", mag)][1], "%"))
    med.ok("el recorrido mensual del CU y de Θ de los dos comercializadores cabe dentro de sus rangos de ±10 % y ±15 %")

    # Cv: el pactado no se conoce
    cvA, cvB = rec[("A", "Cv")][2], rec[("B", "Cv")][2]
    fila("f_cv", "de deducción", "supuesto",
         f"el Cv pactado de un no regulado no es público; los dos comercializadores publican {cvA:.2f} y {cvB:.2f} COP/kWh de media, "
         f"una razón de {cvB / cvA:.2f}; con el rango, el Cv descontado va de {0.25 * cvA:.1f} a {2 * cvA:.1f} COP/kWh con el A "
         f"y de {0.25 * cvB:.1f} a {2 * cvB:.1f} con el B",
         FU_L + ", claves kwh__<comercializador>__Cv__media",
         Cv_A=(cvA, "COP/kWh"), Cv_B=(cvB, "COP/kWh"), razon_B_sobre_A=(cvB / cvA, "veces"),
         Cv_A_min=(0.25 * cvA, "COP/kWh"), Cv_A_max=(2 * cvA, "COP/kWh"), Cv_B_min=(0.25 * cvB, "COP/kWh"), Cv_B_max=(2 * cvB, "COP/kWh"))

    # Bolsa: medias anuales sobre la media de 2025 con tope
    xm = pd.read_csv(med.insumo(F_XM)).set_index("year")
    base = v("bolsa_media_topada")
    med.exige(sorted(xm.index) == [2019, 2021, 2023, 2024] and bool((xm.n >= 8760).all()), "resumen anual de XM inesperado")
    raz = (xm["mean"] / base).to_dict()
    med.exige(R["f_bolsa"][0] <= min(raz.values()) and max(raz.values()) <= R["f_bolsa"][1],
              f"las razones anuales {raz} no caben en el rango de la bolsa")
    med.ok(f"las medias anuales de la bolsa de 2019, 2021, 2023 y 2024 quedan entre {min(raz.values()):.2f} y {max(raz.values()):.2f} veces "
           "la del horizonte con tope, dentro del rango de 0,75 a 4")
    fila("f_bolsa", "de bolsa", "dato histórico",
         f"media anual de la bolsa de XM sobre la media del horizonte de 2025 con su tope ({base:.2f} COP/kWh): "
         + ", ".join(f"{raz[y]:.2f} en {y}" for y in sorted(raz)) + "; el factor se aplica antes del tope",
         f"{F_XM} (insumo con sha256 en el registro) y bolsa_media_topada de {FU_L}",
         base_2025=(base, "COP/kWh"),
         **{f"media_{y}": (float(xm.loc[y, "mean"]), "COP/kWh") for y in sorted(raz)},
         **{f"razon_{y}": (raz[y], "veces") for y in sorted(raz)})

    for k, nombre, extra in (("e_G", "error de generación", ""),
                             ("e_D", "error de demanda", " Cubre también la estimación de las 866 horas incompletas por la media.")):
        fila(k, nombre, "supuesto",
             "exactitud de la telemetría del proyecto, no contrastada (CANON §13.2); la generación y la demanda se mueven solo "
             "dentro de ese error, y sus variaciones mayores las recorren los 13 casos." + extra,
             "CANON §13.2; sin dato que lo mida")
    T = pd.DataFrame(filas)
    med.tabla(T, "m7_rangos.csv")
    med.pon("m7__n_dato_historico", int(T.tipo.str.startswith("dato").sum()), "factores de 6", "m7_rangos.csv")
    med.pon("m7__n_supuesto", int((T.tipo == "supuesto").sum()), "factores de 6", "m7_rangos.csv")
    for _, r in T.iterrows():
        med.di(f"  {r.nombre} [{r.rango_min:g}; {r.rango_max:g}], {r.tipo}: {r.sustento}")
    med.cierra()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
