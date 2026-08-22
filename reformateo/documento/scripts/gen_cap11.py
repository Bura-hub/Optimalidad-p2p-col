"""
gen_cap11.py — Figuras del capítulo 11: robustez.
==================================================
Tres niveles de robustez, de menos a más exigente: barridos de un solo
parámetro, el mapa de dos parámetros, y la descomposición de la varianza
sobre todo el hipercubo.

La sensibilidad global corre sobre el caso de estudio real —896
evaluaciones por cobertura— y no sobre el caso sintético de referencia.
Es la que decide si el resultado depende del recurso o de la calibración.

    python scripts/gen_cap11.py
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

# Nombres legibles de los parámetros y de las salidas del análisis global.
PARAMS = {
    "factor_PV": "Recurso solar",
    "factor_D":  "Nivel de demanda",
    "PGS":       "Tarifa minorista",
    "PGB":       "Piso de precio",
    "b_mean":    "Costo de generar",
}
SALIDAS = {
    "ganancia":  "Ganancia del P2P",
    "sc":        "Autoconsumo",
    "ie":        "Reparto entre lados",
    "brecha_c1": "Ventaja sobre C1",
}


# ─────────────────────────────────────────────────────────────────────────────
def f111_sensibilidad_local():
    """
    F11.1 y F11.2 — Barridos de un solo parámetro.

    A la izquierda, el piso de precio del juego; a la derecha, el factor
    de recurso solar. En cada uno se dibuja la ganancia del mercado P2P
    junto a la del mecanismo colectivo en base mensual, que es la vara de
    comparación, para que el cruce —si lo hay— se vea directamente.
    """
    fig, axes = plt.subplots(2, 2, figsize=(E.ANCHO_COMPLETO, 5.2))
    filas = []
    for k, cob in enumerate(("m1", "m3")):
        for j, (hoja, xcol, xlab, titulo) in enumerate((
            ("SA1_PGB", "PGB_COP_kWh", "Piso de precio [COP/kWh]",
             "Sensibilidad al piso de precio"),
            ("SA2_PV", "PV_factor", "Factor de recurso solar",
             "Sensibilidad al recurso"),
        )):
            ax = axes[j, k]
            s = D.hoja(cob, "analisis", hoja).sort_values(xcol)
            for mec, col in (("P2P", "Net_P2P"),
                             ("C1", "Net_C1"),
                             ("C4_mensual", "Net_C4_mensual")):
                ax.plot(s[xcol], s[col], marker="o", markersize=3.2,
                        color=E.color_mecanismo(mec), linewidth=1.5,
                        label=E.etiqueta_mecanismo(mec))
            ax.set_xlabel(xlab)
            E.eje_espanol(ax, "y", "millones", 1)
            if j == 0:
                ax.set_title(E.TITULO_COBERTURA[cob].replace(" (", "\n("),
                             color=E.COBERTURAS[cob], fontweight="bold", pad=8)
            if k == 0:
                ax.set_ylabel("Ganancia neta [COP]")
            if j == 0 and k == 0:
                ax.legend(fontsize=7, loc="best")
            for _, f in s.iterrows():
                filas.append({"cobertura": cob.upper(), "barrido": hoja,
                              "x": f[xcol], "Net_P2P": f["Net_P2P"],
                              "Net_C1": f["Net_C1"],
                              "Net_C4_mensual": f["Net_C4_mensual"]})
    fig.tight_layout()
    return E.guardar(fig, "f11_01_sensibilidad_local", datos=pd.DataFrame(filas),
                     procedencia=["canonica_{m1,m3}/outputs/"
                                  "resultados_analisis.xlsx (hojas SA1_PGB y SA2_PV)"])


# ─────────────────────────────────────────────────────────────────────────────
def f116_sobol():
    """
    F11.6 — Descomposición de la varianza.

    Índice total de cada parámetro sobre cada una de las cuatro salidas,
    con su intervalo de confianza. Un índice total próximo a cero
    significa que ese parámetro no mueve la salida ni por sí solo ni en
    combinación con otros.

    La lectura que interesa al documento es doble: el recurso solar
    gobierna la ganancia, y el costo de generar —que es el parámetro
    calibrado internamente, y por tanto el más discutible— no la gobierna
    en absoluto. La calibración no decide el resultado.
    """
    orden = list(PARAMS.keys())
    fig, axes = plt.subplots(len(SALIDAS), 2, figsize=(E.ANCHO_COMPLETO, 7.0),
                             sharex=True)
    filas = []
    for k, cob in enumerate(("m1", "m3")):
        idx = D.indices_sobol(cob)
        for j, (sal, sal_nom) in enumerate(SALIDAS.items()):
            ax = axes[j, k]
            sub = idx[idx["salida"] == sal].set_index("parametro").reindex(orden)
            y = np.arange(len(orden))
            colores = [E.MECANISMOS["P2P"] if p == "factor_PV"
                       else (E.NEUTRO if p not in ("factor_D", "PGB")
                             else E.MECANISMOS["C4"]) for p in orden]
            ax.barh(y, sub["ST"], 0.6, color=colores,
                    xerr=sub["ST_conf"], error_kw=dict(ecolor="#555555",
                                                       lw=0.8, capsize=2))
            ax.set_yticks(y)
            ax.set_yticklabels([PARAMS[p] for p in orden], fontsize=7)
            ax.invert_yaxis()
            ax.set_xlim(0, 1.05)
            if j == 0:
                ax.set_title(E.TITULO_COBERTURA[cob].replace(" (", "\n("),
                             color=E.COBERTURAS[cob], fontweight="bold", pad=8)
            if k == 0:
                ax.text(-0.42, 0.5, sal_nom, transform=ax.transAxes,
                        rotation=90, va="center", ha="center", fontsize=8,
                        fontweight="bold")
            if j == len(SALIDAS) - 1:
                ax.set_xlabel("Índice total de Sobol $S_T$")
            for i, (v, c) in enumerate(zip(sub["ST"], sub["ST_conf"])):
                ax.text(min(v + c + 0.03, 1.0), i, E.fmt_miles(v, 3),
                        va="center", fontsize=6.5)
            for p in orden:
                filas.append({"cobertura": cob.upper(), "salida": sal,
                              "parametro": p, "S1": float(sub.loc[p, "S1"]),
                              "S1_conf": float(sub.loc[p, "S1_conf"]),
                              "ST": float(sub.loc[p, "ST"]),
                              "ST_conf": float(sub.loc[p, "ST_conf"])})
    fig.tight_layout()
    return E.guardar(fig, "f11_06_sobol", datos=pd.DataFrame(filas),
                     procedencia=["gsa_real/salidas/indices_M{1,3}_full_n128_s42.csv",
                                  "896 evaluaciones por cobertura, semilla 42"])


# ─────────────────────────────────────────────────────────────────────────────
def f117_aditividad():
    """
    F11.7 — Qué salidas son aditivas y cuáles viven de las interacciones.

    Se compara la suma de los índices de primer orden con la suma de los
    totales. Si las dos coinciden, los parámetros actúan por separado y la
    salida es aditiva; si la segunda es mayor, la diferencia es la parte
    que solo aparece cuando dos parámetros se mueven a la vez.

    La ganancia resulta esencialmente aditiva, mientras que el reparto
    entre lados está dominado por interacciones. Son dos regímenes
    distintos y conviene no tratarlos igual al interpretar.
    """
    fig, ax = E.figura(alto=3.3)
    filas = []
    etiquetas, x = list(SALIDAS.values()), np.arange(len(SALIDAS))
    ancho = 0.38
    for k, cob in enumerate(("m1", "m3")):
        idx = D.indices_sobol(cob)
        frac = []
        for sal in SALIDAS:
            sub = idx[idx["salida"] == sal]
            s1, st = sub["S1"].clip(lower=0).sum(), sub["ST"].sum()
            inter = max(0.0, 100 * (st - s1) / st) if st > 0 else 0.0
            frac.append(inter)
            filas.append({"cobertura": cob.upper(), "salida": sal,
                          "suma_S1": float(s1), "suma_ST": float(st),
                          "pct_interacciones": inter})
        b = ax.bar(x + (k - 0.5) * ancho, frac, ancho,
                   color=E.COBERTURAS[cob], label=cob.upper())
        for xi, v in zip(x + (k - 0.5) * ancho, frac):
            ax.text(xi, v + 1.2, E.fmt_miles(v, 1) + " %", ha="center",
                    fontsize=7, color=E.COBERTURAS[cob])
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas, fontsize=8)
    ax.set_ylabel("Varianza explicada solo por\ninteracciones [%]")
    ax.set_title("Salidas aditivas frente a salidas con interacción", pad=8)
    ax.legend(fontsize=7.5)
    E.eje_espanol(ax, "y", "miles")
    fig.tight_layout()
    return E.guardar(fig, "f11_07_aditividad", datos=pd.DataFrame(filas),
                     procedencia=["gsa_real/salidas/indices_M{1,3}_full_n128_s42.csv"])


# ─────────────────────────────────────────────────────────────────────────────
def f118_lado_corto():
    """
    F11.8 — El mecanismo del lado corto.

    La influencia del nivel de demanda sobre la ganancia cambia de orden
    de magnitud al pasar de una cobertura a la otra. La explicación es que
    lo que limita el volumen transado es siempre el lado escaso: cuando la
    demanda medida es enorme frente a la generación —cobertura M1—, mover
    la demanda no cambia nada, porque lo escaso es el recurso; cuando las
    dos son comparables —cobertura M3—, la demanda pasa a importar.

    Es una predicción que se enunció antes de medirla, y conviene
    contarla en ese orden.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.2),
                                   gridspec_kw={"width_ratios": [1, 1.35]})
    filas = []
    st = {}
    for cob in ("m1", "m3"):
        idx = D.indices_sobol(cob)
        sub = idx[idx["salida"] == "ganancia"].set_index("parametro")
        st[cob] = sub

    # Panel izquierdo: el salto del parámetro de demanda.
    vals = [float(st[c].loc["factor_D", "ST"]) for c in ("m1", "m3")]
    errs = [float(st[c].loc["factor_D", "ST_conf"]) for c in ("m1", "m3")]
    ax1.bar([0, 1], vals, 0.5, color=[E.COBERTURAS["m1"], E.COBERTURAS["m3"]],
            yerr=errs, error_kw=dict(ecolor="#555555", lw=0.9, capsize=3))
    ax1.set_xticks([0, 1])
    ax1.set_xticklabels(["M1\ncobertura 19,1 %", "M3\ncobertura 91,2 %"],
                        fontsize=7.5)
    ax1.set_ylabel("$S_T$ del nivel de demanda\nsobre la ganancia")
    ax1.set_title("La demanda pasa a importar", pad=8)
    factor = vals[1] / vals[0] if vals[0] > 0 else np.nan
    ax1.annotate("", xy=(1, vals[1]), xytext=(0, vals[0]),
                 arrowprops=dict(arrowstyle="->", color=E.ALERTA, lw=1.4,
                                 connectionstyle="arc3,rad=-0.25"))
    ax1.text(0.5, max(vals) * 0.55, f"$\\times$ {E.fmt_miles(factor, 0)}",
             ha="center", fontsize=11, fontweight="bold", color=E.ALERTA)
    for i, v in enumerate(vals):
        ax1.text(i, v + max(vals) * 0.06, E.fmt_miles(v, 3), ha="center",
                 fontsize=7.5)
    ax1.set_ylim(0, max(vals) * 1.35)

    # Panel derecho: el lado escaso de cada cobertura.
    for k, cob in enumerate(("m1", "m3")):
        series, _ = D.preproceso(cob)
        dem = sum(series[f"{i}__D_limpia"] for i in D.AGENTES).sum()
        gen = sum(series[f"{i}__G_limpia"] for i in D.AGENTES).sum()
        ax2.barh([k + 0.16], [gen], 0.3, color=E.MECANISMOS["C5"],
                 label="Generación" if k == 0 else None)
        ax2.barh([k - 0.16], [dem], 0.3, color=E.NEUTRO,
                 label="Demanda" if k == 0 else None)
        # En las dos coberturas la generación es el lado corto; lo que
        # cambia es *cuánto*. Con el 19,1 % la demanda queda tan lejos de
        # ser restrictiva que moverla no altera el volumen; con el 91,2 %
        # las dos magnitudes son comparables y la demanda empieza a
        # limitar en las horas de mayor producción. Decir «lo escaso es el
        # recurso» en ambos casos sería cierto pero vaciaría el argumento.
        razon = gen / dem
        nota = ("la demanda queda muy por encima:\nmoverla no cambia el volumen"
                if razon < 0.5 else
                "las dos magnitudes se acercan:\nla demanda empieza a limitar")
        ax2.text(max(dem, gen) * 1.04, k,
                 f"G/D = {E.fmt_miles(100 * razon, 1)} %\n{nota}",
                 va="center", fontsize=7, color=E.COBERTURAS[cob],
                 linespacing=1.3)
        filas.append({"cobertura": cob.upper(),
                      "ST_factor_D_ganancia": vals[k],
                      "demanda_kWh": dem, "generacion_kWh": gen,
                      "razon_G_sobre_D": gen / dem})
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(["M1", "M3"], fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xlabel("Energía en el horizonte [kWh]")
    ax2.set_title("Por qué: cuál es el lado escaso", pad=8)
    ax2.legend(fontsize=7.5, loc="lower center")
    E.eje_espanol(ax2, "x", "miles")
    ax2.set_xlim(0, 620000)
    ax2.tick_params(axis="x", labelrotation=15, labelsize=7)

    fig.tight_layout()
    return E.guardar(fig, "f11_08_lado_corto", datos=pd.DataFrame(filas),
                     procedencia=["gsa_real/salidas/indices_M{1,3}_full_n128_s42.csv",
                                  "reformateo/documento/datos_cache/preproceso_{m1,m3}.npz"])


if __name__ == "__main__":
    D.verificar_canon()
    print("\nCapítulo 11 — robustez")
    f111_sensibilidad_local()
    f116_sobol()
    f117_aditividad()
    f118_lado_corto()
    print("\nlisto.")
