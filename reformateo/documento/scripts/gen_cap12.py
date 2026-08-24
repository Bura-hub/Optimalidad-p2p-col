"""
gen_cap12.py — Figuras del capítulo 12: factibilidad y equidad.
================================================================
Que un mecanismo rinda más en el agregado no basta. Tiene que además
caber en la norma, convenir a cada participante por separado, y repartir
lo ganado de una manera que nadie considere abusiva. Este capítulo
recorre esas tres condiciones.

Sobre el umbral del 10 %
------------------------
Las dos figuras regulatorias de este capítulo se rehicieron el 2026-08-22
por la razón que registra C-17 en ``CORRECCIONES.md``. El artículo 20,
numeral 1, condición iii de la Resolución CREG 101 072 de 2025 acota el
**Porcentaje de Distribución de Excedentes**, que el artículo 19 obliga a
que sume el 100 % entre todos los usuarios. No acota la cuota de
cobertura de cada agente sobre la demanda del conjunto, que es otra
magnitud y suma la cobertura total, no el 100 %.

La diferencia no es de matiz. Dibujada contra la cuota de cobertura, la
figura concluía que en M1 las cinco instituciones caben dentro del
límite; el propio artefacto canónico dice lo contrario para las cinco y
en las dos coberturas. Y la figura de escalamiento reproducía la prueba
que ``analysis/feasibility.py`` retiró en CAL-41, porque el reparto de
excedentes es un cociente de capacidades y no se mueve al escalar a
todos los miembros por un factor común.

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

LIMITE_PDE_PCT = 10.0     # art. 20 num. 1 iii, CREG 101 072 de 2025
LIMITE_KW = 100.0         # art. 20 num. 1 ii, capacidad por usuario


def _pde_por_institucion() -> pd.Series:
    """
    Porcentaje de Distribución de Excedentes de cada institución.

    Es el reparto proporcional a la capacidad que fija el artículo 19 y
    que implementa el escenario colectivo: la generación media de cada
    agente sobre la suma de las cinco. Se calcula desde la columna
    ``G_mean_kW`` de la hoja canónica ``FA4_Robustez_Escala``, que es
    idéntica en las dos coberturas porque la capacidad instalada no
    depende de la frontera de medición.

    Se comprueba contra la columna ``Cumple_10pct`` de la hoja
    ``FA_CREG101072``: las cinco deben quedar por encima del 10 %.
    """
    g = D.hoja("m1", "analisis", "FA4_Robustez_Escala")
    col_ag = [c for c in g.columns if "gente" in c.lower()][0]
    g = g.set_index(col_ag).reindex(D.AGENTES)["G_mean_kW"].astype(float)
    return 100.0 * g / g.sum()


# ─────────────────────────────────────────────────────────────────────────────
def f121_cumplimiento():
    """
    F12.1 — Por qué el régimen colectivo no cabe en su caso general.

    A la izquierda, el reparto de excedentes que le tocaría a cada
    institución y el límite del diez por ciento que impone el artículo 20.
    Como ese reparto tiene que sumar el cien por ciento entre todos, pedir
    que cada uno esté por debajo del diez exige once participantes o más;
    con cinco es aritméticamente imposible, y las cinco quedan fuera. No
    es un incumplimiento: manda la permuta al Caso 2 del mismo artículo,
    que es un régimen válido y solo cambia cómo se valora.

    A la derecha, la cuota de cobertura de cada institución sobre la
    demanda del conjunto. Es un diagnóstico útil y es lo que el artefacto
    llama participación, pero **no es el criterio de la norma**: las
    cinco cuotas suman la cobertura total de cada frontera, 19,1 % en M1 y
    91,2 % en M3, no el cien por ciento. Por eso ese panel no lleva la
    línea del diez por ciento.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.6),
                                   gridspec_kw={"width_ratios": [1, 1]})
    filas = []
    y = np.arange(len(D.AGENTES))

    # ── Panel izquierdo: el criterio de la norma ────────────────────────────
    pde = _pde_por_institucion()
    veredicto = {}
    for cob in ("m1", "m3"):
        f = D.hoja(cob, "analisis", "FA_CREG101072")
        col_ag = [c for c in f.columns if "gente" in c.lower()][0]
        f = f[f[col_ag].isin(D.AGENTES)].set_index(col_ag).reindex(D.AGENTES)
        veredicto[cob] = f["Cumple_10pct"].astype(float)

    colores = [E.MECANISMOS["C5"] if v < LIMITE_PDE_PCT else E.ANTES
               for v in pde]
    ax1.barh(y, pde.values, 0.62, color=colores)
    ax1.axvline(LIMITE_PDE_PCT, color=E.ALERTA, linestyle="--", linewidth=1.3)
    ax1.set_yticks(y)
    ax1.set_yticklabels([E.etiqueta_institucion(i) for i in D.AGENTES],
                        fontsize=8)
    ax1.set_ylim(len(D.AGENTES) - 0.4, -0.6)
    ax1.set_xlim(0, float(pde.max()) * 1.42)
    ax1.set_xlabel("Reparto de excedentes por usuario (%)", fontsize=8.5)
    ax1.set_title("El criterio del artículo 20", pad=8)
    for j, v in enumerate(pde.values):
        ax1.text(v + float(pde.max()) * 0.03, j, E.fmt_miles(v, 1) + " %",
                 va="center", fontsize=7.2, color=colores[j])
    ax1.annotate(f"límite del {int(LIMITE_PDE_PCT)} %",
                 xy=(LIMITE_PDE_PCT, 1.0), xycoords=("data", "axes fraction"),
                 xytext=(3, -2), textcoords="offset points",
                 color=E.ALERTA, fontsize=7.2, va="top", ha="left")
    n_fuera = int((pde >= LIMITE_PDE_PCT).sum())
    ax1.text(0.5, -0.30,
             f"{n_fuera} de 5 por encima del límite: con cinco usuarios\n"
             "el Caso 1 es aritméticamente inalcanzable",
             transform=ax1.transAxes, ha="center", fontsize=7.2,
             style="italic", color=E.ANTES, linespacing=1.3)

    # ── Panel derecho: la cuota de cobertura, que es otra cosa ──────────────
    ancho = 0.36
    cuota = {}
    for k, cob in enumerate(("m1", "m3")):
        f = D.hoja(cob, "analisis", "FA_CREG101072")
        col_ag = [c for c in f.columns if "gente" in c.lower()][0]
        f = f[f[col_ag].isin(D.AGENTES)].set_index(col_ag).reindex(D.AGENTES)
        cuota[cob] = f["Participacion_pct"].astype(float)
        ax2.barh(y + (0.5 - k) * ancho, cuota[cob].values, ancho,
                 color=E.COBERTURAS[cob],
                 label=f"{cob.upper()} (suma "
                       f"{E.fmt_miles(cuota[cob].sum(), 1)} %)")
    ax2.set_yticks(y)
    ax2.set_yticklabels([E.etiqueta_institucion(i) for i in D.AGENTES],
                        fontsize=8)
    ax2.set_ylim(len(D.AGENTES) - 0.4, -0.6)
    ax2.set_xlim(0, max(c.max() for c in cuota.values()) * 1.30)
    ax2.set_xlabel("Cuota de cobertura (%)", fontsize=8.5)
    ax2.set_title("Diagnóstico, no criterio", pad=8)
    ax2.legend(fontsize=7, loc="lower right")
    ax2.text(0.5, -0.30,
             "las cinco cuotas suman la cobertura de cada frontera,\n"
             "no el 100 %: el límite del artículo 20 no se mide aquí",
             transform=ax2.transAxes, ha="center", fontsize=7.2,
             style="italic", color=E.NEUTRO, linespacing=1.3)

    for inst in D.AGENTES:
        filas.append({"institucion": inst,
                      "pde_pct": float(pde[inst]),
                      "cumple_10pct_norma": bool(pde[inst] < LIMITE_PDE_PCT),
                      "cumple_10pct_canon_M1": bool(veredicto["m1"][inst]),
                      "cumple_10pct_canon_M3": bool(veredicto["m3"][inst]),
                      "cuota_cobertura_M1_pct": float(cuota["m1"][inst]),
                      "cuota_cobertura_M3_pct": float(cuota["m3"][inst])})

    fig.tight_layout(rect=[0, 0.09, 1, 1])
    return E.guardar(fig, "f12_01_cumplimiento", datos=pd.DataFrame(filas),
                     procedencia=[
                         "canonica_{m1,m3}/outputs/resultados_analisis.xlsx "
                         "(hoja FA_CREG101072: columnas Participacion_pct y "
                         "Cumple_10pct)",
                         "canonica_m1/outputs/resultados_analisis.xlsx "
                         "(hoja FA4_Robustez_Escala: columna G_mean_kW, de la "
                         "que se obtiene el reparto de excedentes, "
                         "proporcional a la capacidad segun el art. 19)",
                         "criterio: CREG 101 072 de 2025, art. 20 num. 1 iii; "
                         "ver C-17 en CORRECCIONES.md"])


# ─────────────────────────────────────────────────────────────────────────────
def f122_racionalidad_individual():
    """
    F12.2 — A quién le conviene quedarse.

    Diferencia, para cada institución, entre el beneficio de permanecer en
    el mercado entre pares y el de desertar en solitario al mecanismo
    colectivo, dejando a las otras cuatro dentro. Una barra negativa
    señala a un participante que, mirando solo su cuenta, preferiría
    marcharse; el artefacto lo rotula «en riesgo».

    Es la prueba más exigente del trabajo, porque un mecanismo que
    conviene al conjunto pero no a alguno de sus miembros no es estable:
    ese miembro se va, y el conjunto cambia.

    Ojo con confundirla con la Figura 10.8. Aquella compara la ganancia
    neta de cada institución bajo dos mecanismos que rigen para todos, el
    P2P y el colectivo en base mensual. Esta compara el beneficio de un
    agente en dos situaciones distintas del mismo juego, y su referencia
    es el colectivo en base horaria. Los signos no tienen por qué
    coincidir, y de hecho no coinciden para la Universidad de Nariño.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.7, compartir_y=False)
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
        ax.set_yticklabels([E.etiqueta_institucion(i) for i in D.AGENTES],
                           fontsize=8)
        ax.invert_yaxis()
        rango = max(abs(rel.min()), abs(rel.max()))
        ax.set_xlim(-rango * 1.32, rango * 1.32)
        for j, v in enumerate(rel.values):
            etiqueta = f"{'+' if v >= 0 else ''}{E.fmt_miles(v, 1)} %"
            if abs(v) > rango * 0.42:
                ax.text(v - np.sign(v) * rango * 0.04, j, etiqueta,
                        va="center", ha="right" if v >= 0 else "left",
                        fontsize=7.2, color="white", fontweight="bold")
            else:
                ax.text(v + np.sign(v) * rango * 0.05, j, etiqueta,
                        va="center", ha="left" if v >= 0 else "right",
                        fontsize=7.2, color=colores[j])
        n_neg = int((rel < 0).sum())
        if n_neg == 0:
            nota = "ninguna preferiría marcharse"
        elif n_neg == 1:
            nota = "1 de 5 preferiría marcharse"
        else:
            nota = f"{n_neg} de 5 preferirían marcharse"
        ax.text(0.5, -0.17, nota, transform=ax.transAxes, ha="center",
                fontsize=7.5, style="italic", color=E.COBERTURAS[cob])
        for inst in D.AGENTES:
            filas.append({"cobertura": cob.upper(), "institucion": inst,
                          "delta_rel_pct": float(rel[inst]),
                          "B_P2P_COP": float(f.loc[inst, "B_P2P_COP"]),
                          "B_C4_COP": float(f.loc[inst, "B_C4_COP"]),
                          "pi_gb_critico": float(f.loc[inst, "pi_gb_critico"]),
                          "estado": f.loc[inst, "Estado"]})
    fig.tight_layout(rect=[0, 0.155, 1, 1])
    fig.supxlabel("Beneficio de permanecer en el P2P frente a desertar al\n"
                  "colectivo en base horaria (%)", fontsize=8.5, y=0.055)
    return E.guardar(fig, "f12_02_racionalidad_individual",
                     datos=pd.DataFrame(filas),
                     procedencia=["canonica_{m1,m3}/outputs/"
                                  "resultados_analisis.xlsx (hoja FA_DesercionIR)"])


# ─────────────────────────────────────────────────────────────────────────────
def f125_equidad():
    """
    F12.5 y F12.6 — Cuánto cuesta repartir mejor.

    A la izquierda, la desigualdad del reparto en cada mecanismo medida
    con el índice de Gini: cuanto más bajo, más parejo. Se marca el
    mecanismo más igualitario de cada cobertura, que no es el mismo: en M1
    es la autogeneración individual y en M3 el régimen remoto.

    A la derecha, el precio de la equidad, es decir, qué fracción del
    beneficio total se sacrifica al pasar del mecanismo más eficiente al
    más igualitario. Las dos barras no comparan la misma pareja, y por eso
    cada una declara la suya: en M1 se va del mercado entre pares a la
    autogeneración individual, y en M3 del colectivo en base mensual al
    régimen remoto. Leerlas como si midieran lo mismo sería el error que
    la figura trata de evitar.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.6),
                                   gridspec_kw={"width_ratios": [1.7, 1]})
    filas = []
    orden = ["P2P", "C1", "C2", "C4", "C4_mensual", "C5"]
    # Rotulo corto pero sin ambiguedad: "C4" a secas designaria dos objetos
    # distintos, el horario y el mensual, y el mensual es el que rige.
    CORTO = {"P2P": "P2P", "C1": "C1", "C2": "C2 = C3", "C4": "C4\nhorario",
             "C4_mensual": "C4\nmensual", "C5": "C5"}
    ancho = 0.38
    gini = {}
    for k, cob in enumerate(("m1", "m3")):
        pof = D.hoja(cob, "comparacion", "PoF_Fairness").set_index("escenario")
        disp = [m for m in orden if m in pof.index]
        x = np.arange(len(disp))
        vals = [float(pof.loc[m, "gini"]) for m in disp]
        gini[cob] = dict(zip(disp, vals))
        ax1.bar(x + (k - 0.5) * ancho, vals, ancho, color=E.COBERTURAS[cob],
                label=cob.upper())
        for xi, m, v in zip(x + (k - 0.5) * ancho, disp, vals):
            ax1.text(xi, v + max(vals) * 0.015, E.fmt_miles(v, 3),
                     ha="center", fontsize=6.2, color=E.COBERTURAS[cob],
                     rotation=90, va="bottom")
            filas.append({"cobertura": cob.upper(), "mecanismo": m, "gini": v,
                          "beneficio_total": float(pof.loc[m, "beneficio_total"])})
        # El mas igualitario de cada cobertura, que es el destino del
        # "precio de la equidad" del panel derecho.
        j_min = int(np.argmin(vals))
        ax1.scatter([x[j_min] + (k - 0.5) * ancho], [vals[j_min] * 0.5],
                    marker="v", s=38, color="white", zorder=5,
                    edgecolors=E.COBERTURAS[cob], linewidths=1.2)
    ax1.set_xticks(range(len(disp)))
    ax1.set_xticklabels([CORTO[m] for m in disp], fontsize=7.5)
    ax1.set_ylabel("Índice de Gini del reparto", fontsize=8.5)
    ax1.set_title("Desigualdad del reparto (menor es mejor)", pad=8)
    ax1.set_ylim(0, max(max(v.values()) for v in gini.values()) * 1.42)
    ax1.legend(fontsize=7.5, loc="upper left", ncol=2)
    E.eje_espanol(ax1, "y", "miles", 3)
    ax1.text(0.5, -0.30, "$\\blacktriangledown$  el más igualitario de cada "
             "cobertura", transform=ax1.transAxes, ha="center", fontsize=7,
             style="italic", color=E.NEUTRO)

    # Panel derecho: precio de la equidad.
    pofs = [float(D.hoja(c, "comparacion", "Metricas_extra")
                  .iloc[0]["PoF_Bertsimas2011"]) * 100 for c in ("m1", "m3")]
    tope = max(pofs)
    for k, cob in enumerate(("m1", "m3")):
        extra = D.hoja(cob, "comparacion", "Metricas_extra").iloc[0]
        pofv = pofs[k]
        ax2.bar([k], [pofv], 0.5, color=E.COBERTURAS[cob])
        ax2.text(k, pofv + tope * 0.03, E.fmt_miles(pofv, 2) + " %",
                 ha="center", fontsize=8, color=E.COBERTURAS[cob])
        # Cada barra declara entre qué dos mecanismos se mide, y va encima y
        # no dentro: en M1 la barra es demasiado baja para contener el rótulo.
        ef = CORTO[str(extra["PoF_escenario_eficiente"])].replace("\n", " ")
        eq = CORTO[str(extra["PoF_escenario_equitativo"])].replace("\n", " ")
        ax2.text(k, pofv + tope * 0.12, f"de {ef}\na {eq}",
                 ha="center", va="bottom", fontsize=7,
                 color=E.COBERTURAS[cob], linespacing=1.35)
        filas.append({"cobertura": cob.upper(), "mecanismo": "__PoF__",
                      "gini": np.nan, "beneficio_total": np.nan,
                      "pof_pct": pofv,
                      "eficiente": extra["PoF_escenario_eficiente"],
                      "equitativo": extra["PoF_escenario_equitativo"]})
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["M1", "M3"], fontsize=8)
    ax2.set_xlim(-0.6, 1.6)
    ax2.set_ylabel("Beneficio sacrificado (%)", fontsize=8.5)
    ax2.set_title("Precio de la equidad", pad=8)
    ax2.set_ylim(0, tope * 1.45)
    E.eje_espanol(ax2, "y", "miles", 1)
    ax2.text(0.5, -0.30, "cada barra tiene su propia pareja",
             transform=ax2.transAxes, ha="center", fontsize=7,
             style="italic", color=E.NEUTRO)

    fig.tight_layout(rect=[0, 0.075, 1, 1])
    return E.guardar(fig, "f12_05_equidad", datos=pd.DataFrame(filas),
                     procedencia=["canonica_{m1,m3}/outputs/"
                                  "resultados_comparacion.xlsx "
                                  "(hojas PoF_Fairness y Metricas_extra)"])


# ─────────────────────────────────────────────────────────────────────────────
def f127_escalamiento():
    """
    F12.7 — Hasta dónde aguanta el régimen colectivo.

    Si la comunidad duplicara o triplicara su capacidad instalada,
    ¿seguiría cabiendo en los límites del esquema colectivo? La cota que
    muerde al crecer es la de capacidad por usuario del artículo 20, no la
    del reparto de excedentes: ese reparto es un cociente entre las
    capacidades de los miembros, de modo que multiplicarlas todas por el
    mismo factor lo deja exactamente igual y ninguna escala puede cambiar
    el Caso por esa vía.

    A la izquierda, el pico de generación de cada institución en las tres
    escalas evaluadas por el canon, frente al límite de cien kilovatios. A
    la derecha, el factor exacto al que cada una lo alcanzaría, que es la
    respuesta a la pregunta del título. Las dos coberturas comparten la
    figura porque comparten el dato: la capacidad instalada no depende de
    la frontera de medición, y la hoja canónica trae los mismos picos en
    las dos.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.5),
                                   gridspec_kw={"width_ratios": [1.5, 1]})
    filas = []
    f = D.hoja("m1", "analisis", "FA4_Robustez_Escala")
    col_ag = [c for c in f.columns if "gente" in c.lower()][0]
    f = f.set_index(col_ag).reindex(D.AGENTES)
    pico = f["G_max_kW"].astype(float)
    y = np.arange(len(D.AGENTES))

    # Se dibuja de mayor a menor escala, de modo que cada nivel quede
    # visible como un tramo propio y no se lea como una barra apilada.
    for mult, alpha in ((3, 0.28), (2, 0.52), (1, 0.95)):
        ax1.barh(y, pico * mult, 0.62, color=E.MECANISMOS["C4"], alpha=alpha,
                 edgecolor="white", linewidth=0.5,
                 label=f"$\\times$ {mult}")
    ax1.axvline(LIMITE_KW, color=E.ALERTA, linestyle="--", linewidth=1.3,
                zorder=5)
    ax1.annotate(f"límite por usuario: {int(LIMITE_KW)} kW",
                 xy=(LIMITE_KW, 1.0), xycoords=("data", "axes fraction"),
                 xytext=(-4, -2), textcoords="offset points",
                 color=E.ALERTA, fontsize=7.2, va="top", ha="right")
    ax1.set_yticks(y)
    ax1.set_yticklabels([E.etiqueta_institucion(i) for i in D.AGENTES],
                        fontsize=8)
    ax1.set_ylim(len(D.AGENTES) - 0.4, -0.6)
    ax1.set_xlim(0, LIMITE_KW * 1.12)
    ax1.set_xlabel("Pico de generación al escalar (kW)", fontsize=8.5)
    ax1.set_title("Capacidad por usuario", pad=8)
    man, rot = ax1.get_legend_handles_labels()
    ax1.legend(man[::-1], rot[::-1], fontsize=7.5, loc="lower right",
               title="Capacidad instalada", title_fontsize=7, ncol=3,
               handlelength=1.2, columnspacing=1.0)

    # Panel derecho: el factor exacto al que se alcanza el limite.
    factor = LIMITE_KW / pico
    ax2.hlines(y, 0, factor.values, color=E.MECANISMOS["C4"], linewidth=1.6)
    ax2.scatter(factor.values, y, s=42, color=E.MECANISMOS["C4"], zorder=4,
                edgecolors="white", linewidths=0.9)
    for j, v in enumerate(factor.values):
        ax2.text(v + factor.max() * 0.045, j,
                 f"$\\times$ {E.fmt_miles(v, 1)}", va="center", fontsize=7.2,
                 color=E.MECANISMOS["C4"])
    # Franja de las escalas que el canon llegó a evaluar.
    ax2.axvspan(1, 3, color=E.APOYO, alpha=0.6, zorder=0)
    ax2.set_yticks(y)
    ax2.set_yticklabels([])
    ax2.set_ylim(len(D.AGENTES) - 0.4, -0.6)
    ax2.set_xlim(0, factor.max() * 1.30)
    ax2.set_xlabel("Factor al que se alcanza el límite", fontsize=8.5)
    ax2.set_title("Margen de crecimiento", pad=8)
    critica = factor.idxmin()
    ax2.text(0.5, -0.38,
             f"la primera en alcanzarlo sería "
             f"{E.etiqueta_institucion(critica)}, a "
             f"$\\times$ {E.fmt_miles(factor.min(), 1)}\n"
             "franja sombreada: escalas evaluadas por el canon",
             transform=ax2.transAxes, ha="center", fontsize=7.2,
             style="italic", color=E.MECANISMOS["C4"], linespacing=1.3)

    ax1.text(0.5, -0.38,
             "el reparto de excedentes no aparece: es invariante a un\n"
             "escalado común de todos los miembros",
             transform=ax1.transAxes, ha="center", fontsize=7.2,
             style="italic", color=E.NEUTRO, linespacing=1.3)

    for inst in D.AGENTES:
        filas.append({"institucion": inst,
                      "pico_kW": float(pico[inst]),
                      "pico_x2_kW": float(pico[inst] * 2),
                      "pico_x3_kW": float(pico[inst] * 3),
                      "factor_limite_100kW": float(factor[inst]),
                      "cumple_2x": bool(f.loc[inst, "2x_cumple"]),
                      "cumple_3x": bool(f.loc[inst, "3x_cumple"]),
                      "escala_max_ok": float(f.loc[inst, "Escala_max_ok"])})
    fig.tight_layout(rect=[0, 0.115, 1, 1])
    return E.guardar(fig, "f12_07_escalamiento", datos=pd.DataFrame(filas),
                     procedencia=[
                         "canonica_m1/outputs/resultados_analisis.xlsx "
                         "(hoja FA4_Robustez_Escala: G_max_kW, 2x_cumple, "
                         "3x_cumple y Escala_max_ok; identica en canonica_m3)",
                         "criterio: CREG 101 072 de 2025, art. 20 num. 1 ii; "
                         "la invariancia del reparto de excedentes ante un "
                         "escalado comun esta en analysis/feasibility.py (CAL-41)"])


if __name__ == "__main__":
    D.verificar_canon()
    print("\nCapítulo 12 — factibilidad y equidad")
    f121_cumplimiento()
    f122_racionalidad_individual()
    f125_equidad()
    f127_escalamiento()
    print("\nlisto.")
