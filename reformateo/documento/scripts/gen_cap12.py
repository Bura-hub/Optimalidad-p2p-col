"""
gen_cap12.py — Figuras del capítulo 12: factibilidad y equidad.
================================================================
Que un mecanismo rinda más en el agregado no basta. Tiene que además
caber en la norma, convenir a cada participante por separado, y repartir
lo ganado de una manera que nadie considere abusiva. Este capítulo
recorre esas tres condiciones.

    python scripts/gen_cap12.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estilo as E
import datos as D


# ─────────────────────────────────────────────────────────────────────────────
def f121_cumplimiento():
    """
    F12.1 — Los dos límites del régimen colectivo.

    La norma del esquema colectivo impone que ningún participante supere
    el diez por ciento de la energía del conjunto ni cierta capacidad
    instalada. Se comprueban los dos sobre la comunidad real.

    El resultado importa para el capítulo 8: con solo cinco fronteras
    comerciales, la primera condición no puede cumplirse, y de ahí que el
    escenario colectivo tenga que liquidarse por la vía alternativa que
    prevé el propio artículo.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.4, compartir_y=True)
    filas = []
    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
        f = D.hoja(cob, "analisis", "FA_CREG101072")
        col_ag = [c for c in f.columns if "gente" in c.lower()][0]
        f = f[f[col_ag].isin(D.AGENTES)].set_index(col_ag).reindex(D.AGENTES)
        y = np.arange(len(D.AGENTES))
        part = f["Participacion_pct"].astype(float)
        colores = [E.MECANISMOS["C5"] if v <= 10 else E.ANTES for v in part]
        ax.barh(y, part, 0.62, color=colores)
        ax.axvline(10, color=E.ALERTA, linestyle="--", linewidth=1.3)
        ax.text(10.6, -0.62, "límite del 10 %", color=E.ALERTA, fontsize=7.2,
                va="center")
        ax.set_yticks(y)
        ax.set_yticklabels(D.AGENTES, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("Participación en la energía del conjunto [%]")
        for j, v in enumerate(part):
            ax.text(v + 1.2, j, E.fmt_miles(v, 1) + " %", va="center",
                    fontsize=7.2, color=colores[j])
        ax.set_xlim(0, max(part.max() * 1.32, 14))
        n_ok = int((part <= 10).sum())
        ax.text(0.5, -0.30,
                f"{n_ok} de 5 dentro del límite",
                transform=ax.transAxes, ha="center", fontsize=7.5,
                style="italic", color=E.COBERTURAS[cob])
        for inst, v in part.items():
            filas.append({"cobertura": cob.upper(), "institucion": inst,
                          "participacion_pct": float(v),
                          "cumple_10pct": bool(v <= 10)})
    fig.tight_layout()
    return E.guardar(fig, "f12_01_cumplimiento", datos=pd.DataFrame(filas),
                     procedencia=["canonica_{m1,m3}/outputs/"
                                  "resultados_analisis.xlsx (hoja FA_CREG101072)"])


# ─────────────────────────────────────────────────────────────────────────────
def f122_racionalidad_individual():
    """
    F12.2 — A quién le conviene participar.

    Diferencia de cada institución entre quedarse en el mercado entre
    pares y acogerse al mecanismo colectivo. Una barra negativa señala a
    un participante que, mirando solo su cuenta, preferiría marcharse.

    Es la prueba más exigente del trabajo, porque un mecanismo que
    conviene al conjunto pero no a alguno de sus miembros no es estable:
    ese miembro se va, y el conjunto cambia.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.5, compartir_y=False)
    filas = []
    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
        f = D.hoja(cob, "analisis", "FA_DesercionIR")
        col_ag = [c for c in f.columns if "gente" in c.lower()][0]
        f = f.set_index(col_ag).reindex(D.AGENTES)
        rel = f["Delta_n_rel"].astype(float) * 100
        y = np.arange(len(D.AGENTES))
        colores = [E.MECANISMOS["P2P"] if v >= 0 else E.ANTES for v in rel]
        ax.barh(y, rel.values, 0.62, color=colores)
        ax.axvline(0, color="#333333", linewidth=1.0)
        ax.set_yticks(y)
        ax.set_yticklabels(D.AGENTES, fontsize=8)
        ax.invert_yaxis()
        rango = max(abs(rel.min()), abs(rel.max()))
        ax.set_xlim(-rango * 1.5, rango * 1.5)
        for j, v in enumerate(rel.values):
            ax.text(v + np.sign(v) * rango * 0.06, j,
                    f"{'+' if v >= 0 else ''}{E.fmt_miles(v, 1)} %",
                    va="center", ha="left" if v >= 0 else "right",
                    fontsize=7.2, color=colores[j])
        ax.set_xlabel("Ventaja de participar frente a no hacerlo [%]")
        n_neg = int((rel < 0).sum())
        ax.text(0.5, -0.30,
                "a todas les conviene participar" if n_neg == 0
                else f"a {n_neg} de 5 no le conviene",
                transform=ax.transAxes, ha="center", fontsize=7.5,
                style="italic", color=E.COBERTURAS[cob])
        for inst in D.AGENTES:
            filas.append({"cobertura": cob.upper(), "institucion": inst,
                          "delta_rel_pct": float(rel[inst]),
                          "B_P2P_COP": float(f.loc[inst, "B_P2P_COP"]),
                          "B_C4_COP": float(f.loc[inst, "B_C4_COP"]),
                          "pi_gb_critico": float(f.loc[inst, "pi_gb_critico"])})
    fig.tight_layout()
    return E.guardar(fig, "f12_02_racionalidad_individual",
                     datos=pd.DataFrame(filas),
                     procedencia=["canonica_{m1,m3}/outputs/"
                                  "resultados_analisis.xlsx (hoja FA_DesercionIR)"])


# ─────────────────────────────────────────────────────────────────────────────
def f125_equidad():
    """
    F12.5 y F12.6 — Cuánto cuesta repartir mejor.

    A la izquierda, la desigualdad del reparto en cada mecanismo medida
    con el índice de Gini: cuanto más bajo, más parejo. A la derecha, el
    precio de la equidad, es decir, qué fracción del beneficio total se
    sacrifica al pasar del reparto más eficiente al más igualitario.

    La comparación se hace en tres dimensiones y no en una sola, porque un
    mecanismo puede ganar en total y perder en reparto, y presentar solo
    el total sería quedarse con media respuesta.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.4),
                                   gridspec_kw={"width_ratios": [1.5, 1]})
    filas = []
    orden = ["P2P", "C1", "C2", "C4", "C4_mensual", "C5"]
    ancho = 0.38
    for k, cob in enumerate(("m1", "m3")):
        pof = D.hoja(cob, "comparacion", "PoF_Fairness").set_index("escenario")
        disp = [m for m in orden if m in pof.index]
        x = np.arange(len(disp))
        vals = [float(pof.loc[m, "gini"]) for m in disp]
        ax1.bar(x + (k - 0.5) * ancho, vals, ancho, color=E.COBERTURAS[cob],
                label=cob.upper())
        for m, v in zip(disp, vals):
            filas.append({"cobertura": cob.upper(), "mecanismo": m, "gini": v,
                          "beneficio_total": float(pof.loc[m, "beneficio_total"])})
    ax1.set_xticks(range(len(disp)))
    ax1.set_xticklabels([E.etiqueta_mecanismo(m).split(" · ")[0] for m in disp],
                        fontsize=7.5)
    ax1.set_ylabel("Índice de Gini del reparto")
    ax1.set_title("Desigualdad del reparto (menor es mejor)", pad=8)
    ax1.legend(fontsize=7.5)
    E.eje_espanol(ax1, "y", "miles", 3)

    # Panel derecho: precio de la equidad.
    for k, cob in enumerate(("m1", "m3")):
        extra = D.hoja(cob, "comparacion", "Metricas_extra").iloc[0]
        pofv = float(extra["PoF_Bertsimas2011"]) * 100
        ax2.bar([k], [pofv], 0.5, color=E.COBERTURAS[cob])
        ax2.text(k, pofv * 1.04, E.fmt_miles(pofv, 2) + " %", ha="center",
                 fontsize=8, color=E.COBERTURAS[cob])
        filas.append({"cobertura": cob.upper(), "mecanismo": "__PoF__",
                      "gini": np.nan, "beneficio_total": np.nan,
                      "pof_pct": pofv,
                      "eficiente": extra["PoF_escenario_eficiente"],
                      "equitativo": extra["PoF_escenario_equitativo"]})
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["M1", "M3"], fontsize=8)
    ax2.set_ylabel("Beneficio sacrificado [%]")
    ax2.set_title("Precio de la equidad", pad=8)
    ax2.set_ylim(0, max(f.get("pof_pct", 0) for f in filas
                        if "pof_pct" in f) * 1.30)
    E.eje_espanol(ax2, "y", "miles", 1)

    fig.tight_layout()
    return E.guardar(fig, "f12_05_equidad", datos=pd.DataFrame(filas),
                     procedencia=["canonica_{m1,m3}/outputs/"
                                  "resultados_comparacion.xlsx "
                                  "(hojas PoF_Fairness y Metricas_extra)"])


# ─────────────────────────────────────────────────────────────────────────────
def f127_escalamiento():
    """
    F12.7 — Hasta dónde aguanta el régimen colectivo.

    Si la comunidad duplicara o triplicara su capacidad instalada,
    ¿seguiría cabiendo en los límites del esquema colectivo? La respuesta
    marca el horizonte de validez del escenario de referencia: no es una
    conclusión sobre hoy, sino sobre cuánto margen queda.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.2, compartir_y=True)
    filas = []
    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
        f = D.hoja(cob, "analisis", "FA4_Robustez_Escala")
        col_ag = [c for c in f.columns if "gente" in c.lower()][0]
        f = f.set_index(col_ag).reindex(D.AGENTES)
        share = f["Share_actual_%"].astype(float)
        y = np.arange(len(D.AGENTES))
        for mult, alpha in ((1, 0.95), (2, 0.55), (3, 0.30)):
            ax.barh(y, share * mult, 0.62, color=E.MECANISMOS["C4"],
                    alpha=alpha, zorder=3 - mult,
                    label=f"$\\times$ {mult}" if ax is ax_m1 else None)
        ax.axvline(10, color=E.ALERTA, linestyle="--", linewidth=1.3, zorder=5)
        ax.set_yticks(y)
        ax.set_yticklabels(D.AGENTES, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("Participación al escalar [%]")
        for inst in D.AGENTES:
            filas.append({"cobertura": cob.upper(), "institucion": inst,
                          "share_actual_pct": float(share[inst]),
                          "cumple_2x": f.loc[inst, "2x_cumple"],
                          "cumple_3x": f.loc[inst, "3x_cumple"],
                          "escala_max_ok": f.loc[inst, "Escala_max_ok"]})
    ax_m1.legend(fontsize=7.5, loc="lower right", title="Capacidad",
                 title_fontsize=7)
    fig.tight_layout()
    return E.guardar(fig, "f12_07_escalamiento", datos=pd.DataFrame(filas),
                     procedencia=["canonica_{m1,m3}/outputs/"
                                  "resultados_analisis.xlsx (hoja FA4_Robustez_Escala)"])


if __name__ == "__main__":
    D.verificar_canon()
    print("\nCapítulo 12 — factibilidad y equidad")
    f121_cumplimiento()
    f122_racionalidad_individual()
    f125_equidad()
    f127_escalamiento()
    print("\nlisto.")
