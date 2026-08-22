"""
gen_cap03.py — Figuras del capítulo 3: la domesticación del dato.
==================================================================
Es el capítulo central del documento: el que muestra qué le pasa al dato
entre el medidor y el modelo. Cada figura aísla una etapa y la enseña
como un antes y un después.

    python scripts/gen_cap03.py

Requiere el caché de estados intermedios:

    python scripts/cache_crudo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estilo as E
import datos as D


# ─────────────────────────────────────────────────────────────────────────────
def f32_demanda_negativa(cobertura: str = "m1"):
    """
    F3.2 — La demanda que el medidor entrega en negativo.

    Dos paneles. Izquierda: el perfil medio por hora del día de las cinco
    instituciones tal como sale del medidor, con la franja bajo cero
    sombreada. Derecha: cuántas horas cae bajo cero cada institución y en
    qué hora del día ocurre.

    El argumento de la figura es que el valor negativo no es ruido: se
    concentra al mediodía, que es exactamente cuando el sol produce. Un
    medidor que resta la generación antes de reportar no está midiendo la
    demanda del edificio, y por eso hay que revertir la resta.
    """
    series, horas = D.preproceso(cobertura)
    resumen = D.conteo_negativas(cobertura)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.5),
                                   gridspec_kw={"width_ratios": [1.25, 1]})

    filas = []
    for inst in E.ORDEN_INSTITUCIONES:
        s = series[f"{inst}__D_raw"]
        perfil = s.groupby(s.index.hour).mean()
        ax1.plot(perfil.index, perfil.values, color=E.color_institucion(inst),
                 label=inst, linewidth=1.6)
        for h, v in perfil.items():
            filas.append({"institucion": inst, "hora": h, "D_raw_media_kW": v})

    ax1.axhline(0, color="#333333", linewidth=1.0)
    lim = ax1.get_ylim()
    ax1.axhspan(lim[0], 0, color=E.ANTES, alpha=0.10, zorder=0)
    ax1.set_ylim(lim)
    ax1.text(0.5, 0.06, "zona imposible: la demanda de un edificio no es negativa",
             transform=ax1.transAxes, ha="center", fontsize=7.5,
             color=E.ANTES, style="italic")
    ax1.set_xlabel("Hora del día")
    ax1.set_ylabel("Demanda del medidor [kW]")
    ax1.set_title("Perfil medio tal como llega del medidor", pad=8)
    ax1.set_xticks(range(0, 24, 3))
    ax1.legend(ncol=2, loc="upper left", fontsize=7.5)

    # Panel derecho: cuántas horas bajo cero, y a qué hora del día
    r = resumen.set_index("institucion").reindex(E.ORDEN_INSTITUCIONES)
    colores = [E.ANTES if n > 0 else E.NEUTRO for n in r["horas_negativas"]]
    barras = ax2.barh(range(len(r)), r["horas_negativas"], color=colores,
                      height=0.62)
    ax2.set_yticks(range(len(r)))
    ax2.set_yticklabels([f"{i}\n({t})" for i, t in
                         zip(r.index, r["tipo_medidor"])], fontsize=7.5)
    ax2.invert_yaxis()
    ax2.set_xlabel("Horas con demanda negativa (de 6.144)")
    ax2.set_title("Alcance del problema por institución", pad=8)
    E.eje_espanol(ax2, "x", "miles")

    tope = max(r["horas_negativas"].max(), 1)
    for i, (n, mn) in enumerate(zip(r["horas_negativas"], r["min_D_raw_kW"])):
        if n > 0:
            ax2.text(n + tope * 0.03, i,
                     f"{E.fmt_miles(n)} h  ·  mín {E.fmt_miles(mn, 1)} kW",
                     va="center", fontsize=7.5, color=E.ANTES)
        else:
            ax2.text(tope * 0.03, i, "sin negativos", va="center",
                     fontsize=7.5, color=E.NEUTRO, style="italic")
    ax2.set_xlim(0, tope * 1.55)

    fig.tight_layout()
    return E.guardar(
        fig, f"f3_02_demanda_negativa_{cobertura}",
        datos=pd.DataFrame(filas).merge(
            r.reset_index()[["institucion", "tipo_medidor", "horas_negativas",
                             "min_D_raw_kW"]], on="institucion"),
        procedencia=[
            "MedicionesMTE_v3/ (medidores de demanda, columna totalActivePower)",
            "reformateo/documento/datos_cache/preproceso_%s.npz" % cobertura,
            "pipeline: data/preprocessing.py::build_demand_generation",
        ])


# ─────────────────────────────────────────────────────────────────────────────
def f33_reconstruccion(cobertura: str = "m1", institucion: str = "Udenar",
                       dia: str = "2025-07-16"):
    """
    F3.3 — La reconstrucción net→bruta: antes y después.

    La figura estrella del documento. Muestra sobre un día concreto qué
    entrega el medidor (que baja a valores negativos al mediodía), qué
    generaron los inversores que ese medidor había descontado, y qué
    demanda resulta al devolverle esa generación.

    El panel derecho generaliza a las 6.144 h con el perfil medio, para
    que no quede la duda de si el día elegido es representativo.
    """
    series, horas = D.preproceso(cobertura)
    resumen = D.conteo_negativas(cobertura).set_index("institucion")

    D_raw = series[f"{institucion}__D_raw"]
    G_rec = series[f"{institucion}__G_recon"]
    D_rec = series[f"{institucion}__D_recon"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.7))

    # ── Panel izquierdo: un día, hora a hora ────────────────────────────
    d0, d1 = pd.Timestamp(dia), pd.Timestamp(dia) + pd.Timedelta(days=1)
    sl = slice(d0, d1 - pd.Timedelta(hours=1))
    x = np.arange(24)
    dr, gr, dd = D_raw[sl].values, G_rec[sl].values, D_rec[sl].values

    ax1.axhline(0, color="#333333", linewidth=1.0, zorder=3)
    ax1.fill_between(x, 0, gr, color=E.APOYO, alpha=0.85, zorder=1,
                     label="Generación que el medidor había restado")
    ax1.plot(x, dr, color=E.ANTES, linewidth=1.9, zorder=4,
             label="Antes: lectura del medidor")
    ax1.plot(x, dd, color=E.DESPUES, linewidth=1.9, zorder=5,
             label="Después: demanda reconstruida")

    bajo = dr < 0
    if bajo.any():
        ax1.fill_between(x, dr, 0, where=bajo, color=E.ANTES, alpha=0.22,
                         zorder=2, interpolate=True)
        # La flecha apunta al mínimo real del día, que es donde el
        # argumento se ve con más claridad.
        h_min = int(np.nanargmin(dr))
        ax1.annotate("el medidor reporta menos\nenergía de la que el\nedificio gastó",
                     xy=(h_min, dr[h_min]),
                     xytext=(0.04, 0.06), textcoords="axes fraction",
                     fontsize=7.2, color=E.ANTES, ha="left", va="bottom",
                     arrowprops=dict(arrowstyle="->", color=E.ANTES, lw=0.9,
                                     connectionstyle="arc3,rad=-0.2"))

    ax1.set_xlabel("Hora del día")
    ax1.set_ylabel("Potencia [kW]")
    ax1.set_title(f"Un día: {institucion}, {dia}", pad=8)
    ax1.set_xticks(range(0, 24, 3))
    ax1.legend(loc="upper left", fontsize=7)

    # ── Panel derecho: el horizonte completo ────────────────────────────
    p_raw = D_raw.groupby(D_raw.index.hour).mean()
    p_rec = D_rec.groupby(D_rec.index.hour).mean()
    p_gen = G_rec.groupby(G_rec.index.hour).mean()

    ax2.axhline(0, color="#333333", linewidth=1.0, zorder=3)
    ax2.fill_between(p_gen.index, 0, p_gen.values, color=E.APOYO, alpha=0.85,
                     zorder=1)
    ax2.plot(p_raw.index, p_raw.values, color=E.ANTES, linewidth=1.9, zorder=4)
    ax2.plot(p_rec.index, p_rec.values, color=E.DESPUES, linewidth=1.9, zorder=5)
    ax2.set_xlabel("Hora del día")
    ax2.set_ylabel("Potencia media [kW]")
    ax2.set_title("Las 6.144 h: perfil medio por hora", pad=8)
    ax2.set_xticks(range(0, 24, 3))

    n_neg = int(resumen.loc[institucion, "horas_negativas"])
    mn = float(resumen.loc[institucion, "min_D_raw_kW"])
    dif = (D_rec.sum() - D_raw.fillna(0).sum())
    # Se ancla abajo a la izquierda: es la única zona del panel que las
    # tres series dejan libre (la caída de la lectura ocupa el centro).
    ax2.text(0.02, 0.04,
             f"{E.fmt_miles(n_neg)} h bajo cero\n"
             f"mínimo {E.fmt_miles(mn, 1)} kW\n"
             f"devueltos {E.fmt_miles(dif)} kWh",
             transform=ax2.transAxes, ha="left", va="bottom", fontsize=7.2,
             linespacing=1.35,
             bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                       edgecolor=E.NEUTRO, linewidth=0.6, alpha=0.95))

    fig.tight_layout()

    tabla = pd.DataFrame({
        "hora": p_raw.index,
        "D_medidor_kW": p_raw.values,
        "G_restada_kW": p_gen.values,
        "D_reconstruida_kW": p_rec.values,
    })
    return E.guardar(
        fig, f"f3_03_reconstruccion_{cobertura}", datos=tabla,
        procedencia=[
            f"MedicionesMTE_v3/{institucion}/ (medidor de demanda e inversores)",
            f"reformateo/documento/datos_cache/preproceso_{cobertura}.npz",
            "regla: D = max(0, D_net + suma de inversores) — data/preprocessing.py",
        ])


# ─────────────────────────────────────────────────────────────────────────────
def f35_outliers_imputacion(cobertura: str = "m1"):
    """
    F3.5/F3.6 — Lo que la limpieza marca y lo que rellena.

    Panel izquierdo: la serie de una institución con los valores atípicos
    señalados y el umbral dibujado, para que se vea que el criterio no
    recorta picos operativos legítimos. Panel derecho: cuántas horas
    quedaron imputadas por mes en cada institución.
    """
    series, horas = D.preproceso(cobertura)
    resumen = D.conteo_negativas(cobertura).set_index("institucion")

    # Para el panel izquierdo se elige la institución con más atípicos;
    # si ninguna tiene, se muestra la de mayor imputación.
    r = resumen.reindex(E.ORDEN_INSTITUCIONES)
    inst = (r["outliers_D"].idxmax() if r["outliers_D"].max() > 0
            else r["imputadas_D"].idxmax())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.5))

    s = series[f"{inst}__D_recon"]
    out = series[f"{inst}__mask_out_D"].astype(bool)
    umbral = float(resumen.loc[inst, "umbral_outlier_D_kW"])

    ax1.plot(s.index, s.values, color=E.NEUTRO, linewidth=0.5, alpha=0.85,
             label="Demanda reconstruida")
    if np.isfinite(umbral):
        ax1.axhline(umbral, color=E.ALERTA, linewidth=1.1, linestyle="--",
                    label=f"Umbral: {E.fmt_miles(umbral, 1)} kW")
    if out.any():
        ax1.scatter(s.index[out], s[out], s=22, color=E.ANTES, zorder=5,
                    label=f"Atípicos: {E.fmt_miles(int(out.sum()))} h",
                    edgecolors="white", linewidths=0.4)
    ax1.set_ylabel("Demanda [kW]")
    ax1.set_title(f"Criterio de atípicos: {E.etiqueta_institucion(inst)}",
                  pad=8)
    ax1.legend(loc="upper left", fontsize=7)
    ax1.tick_params(axis="x", labelrotation=25, labelsize=6.5)

    # Panel derecho: imputación por mes
    meses = None
    matriz = []
    for i in E.ORDEN_INSTITUCIONES:
        imp = series[f"{i}__mask_imp_D"].astype(bool)
        por_mes = imp.groupby(imp.index.to_period("M")).sum()
        meses = por_mes.index.astype(str)
        matriz.append(por_mes.values)
    matriz = np.array(matriz, dtype=float)

    im = ax2.imshow(matriz, aspect="auto", cmap="YlOrBr", vmin=0)
    ax2.set_xticks(range(len(meses)))
    ax2.set_xticklabels([m[-2:] + "/" + m[2:4] for m in meses], fontsize=7)
    ax2.set_yticks(range(len(E.ORDEN_INSTITUCIONES)))
    ax2.set_yticklabels([E.etiqueta_institucion(i)
                         for i in E.ORDEN_INSTITUCIONES], fontsize=7.5)
    ax2.set_xlabel("Mes de 2025")
    ax2.set_title("Horas imputadas por mes", pad=8)
    ax2.grid(False)
    for i in range(matriz.shape[0]):
        for j in range(matriz.shape[1]):
            v = int(matriz[i, j])
            if v:
                ax2.text(j, i, str(v), ha="center", va="center", fontsize=6.2,
                         color="#333333")
    cb = fig.colorbar(im, ax=ax2, fraction=0.045, pad=0.03)
    cb.set_label("horas", fontsize=7.5)
    cb.ax.tick_params(labelsize=7)

    fig.tight_layout()

    tabla = pd.DataFrame(matriz, index=E.ORDEN_INSTITUCIONES,
                         columns=meses).reset_index(names="institucion")
    return E.guardar(
        fig, f"f3_05_outliers_imputacion_{cobertura}", datos=tabla,
        procedencia=[
            f"reformateo/documento/datos_cache/preproceso_{cobertura}.npz",
            "criterio: max(Q75 + 5*IQR, P99,5 * 1,2) — data/xm_data_loader.py::_clean",
        ])


# ─────────────────────────────────────────────────────────────────────────────
def f37_matrices(cobertura: str = "m1"):
    """
    F3.7 — Lo que el modelo recibe finalmente.

    Las dos matrices que salen del pipeline, dibujadas como mapas de hora
    del día contra día del horizonte. La generación traza una banda diurna
    nítida que sigue el arco solar; la demanda muestra la semana laboral
    en franjas verticales.

    Es la comprobación visual de que el resultado del preprocesamiento
    tiene la estructura que debe tener: si la banda solar apareciera de
    noche, o la semana no se distinguiera, habría un error de zona horaria
    o de alineación temporal.
    """
    series, horas = D.preproceso(cobertura)
    dem = sum(series[f"{i}__D_limpia"] for i in D.AGENTES)
    gen = sum(series[f"{i}__G_limpia"] for i in D.AGENTES)

    fig, axes = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.4))
    filas = []
    for ax, (serie, nom, cmap) in zip(axes, ((dem, "Demanda", "Greys"),
                                             (gen, "Generación", "YlOrBr"))):
        base = serie.index.normalize()
        m = pd.DataFrame({"v": serie.values, "h": serie.index.hour,
                          "d": (base - base[0]).days})
        piv = m.pivot_table(index="h", columns="d", values="v", aggfunc="mean")
        im = ax.imshow(piv.values, aspect="auto", origin="lower", cmap=cmap,
                       extent=[0, piv.shape[1], 0, 24])
        ax.set_xlabel("Día del horizonte")
        ax.set_ylabel("Hora del día")
        ax.set_yticks(range(0, 25, 6))
        ax.set_title(f"{nom} de la comunidad", pad=8)
        ax.grid(False)
        cb = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
        cb.set_label("kW", fontsize=7.5)
        cb.ax.tick_params(labelsize=7)
        for h in piv.index:
            filas.append({"magnitud": nom, "hora": int(h),
                          "media_kW": float(piv.loc[h].mean())})
    fig.tight_layout()
    return E.guardar(fig, f"f3_07_matrices_{cobertura}",
                     datos=pd.DataFrame(filas),
                     procedencia=[f"reformateo/documento/datos_cache/"
                                  f"preproceso_{cobertura}.npz"])


# ─────────────────────────────────────────────────────────────────────────────
def f38_perfiles_instituciones(cobertura: str = "m1"):
    """
    F3.8 — Cinco ritmos distintos.

    Perfil medio de demanda y generación de cada institución. Aunque
    comparten ciudad y clima, no comparten rutina: un hospital no se
    parece a un campus universitario, y esa diferencia es justamente la
    que hace posible el intercambio.
    """
    series, _ = D.preproceso(cobertura)
    fig, axes = plt.subplots(2, 3, figsize=(E.ANCHO_COMPLETO, 4.2), sharex=True)
    filas = []
    for ax, inst in zip(axes.ravel(), D.AGENTES):
        d = series[f"{inst}__D_limpia"]
        g = series[f"{inst}__G_limpia"]
        pdm = d.groupby(d.index.hour).mean()
        pgm = g.groupby(g.index.hour).mean()
        ax.fill_between(pgm.index, 0, pgm.values, color=E.MECANISMOS["C5"],
                        alpha=0.30)
        ax.plot(pgm.index, pgm.values, color=E.MECANISMOS["C5"], linewidth=1.4)
        ax.plot(pdm.index, pdm.values, color=E.color_institucion(inst),
                linewidth=1.6)
        cob_pct = 100 * g.sum() / d.sum() if d.sum() else float("nan")
        ax.set_title(f"{E.etiqueta_institucion(inst)}  ·  {E.fmt_miles(cob_pct, 0)} %", pad=5,
                     color=E.color_institucion(inst), fontsize=9)
        ax.set_xticks(range(0, 24, 6))
        for h in pdm.index:
            filas.append({"institucion": inst, "hora": int(h),
                          "demanda_kW": pdm[h], "generacion_kW": pgm[h]})

    # El sexto panel resume la comunidad completa.
    ax = axes.ravel()[5]
    dt = sum(series[f"{i}__D_limpia"] for i in D.AGENTES)
    gt = sum(series[f"{i}__G_limpia"] for i in D.AGENTES)
    pdt = dt.groupby(dt.index.hour).mean()
    pgt = gt.groupby(gt.index.hour).mean()
    ax.fill_between(pgt.index, 0, pgt.values, color=E.MECANISMOS["C5"], alpha=0.30)
    ax.plot(pgt.index, pgt.values, color=E.MECANISMOS["C5"], linewidth=1.4,
            label="Generación")
    ax.plot(pdt.index, pdt.values, color="black", linewidth=1.7, label="Demanda")
    ax.set_title(f"Comunidad  ·  {E.fmt_miles(100 * gt.sum() / dt.sum(), 0)} %",
                 pad=5, fontsize=9)
    ax.set_xticks(range(0, 24, 6))
    # Arriba a la derecha: al final del dia la demanda ya ha bajado y
    # la leyenda no cruza ninguna curva.
    ax.legend(fontsize=6.5, loc="upper right")

    for ax in axes[1, :]:
        ax.set_xlabel("Hora del día")
    for ax in axes[:, 0]:
        ax.set_ylabel("Potencia media [kW]")
    fig.tight_layout()
    return E.guardar(fig, f"f3_08_perfiles_instituciones_{cobertura}",
                     datos=pd.DataFrame(filas),
                     procedencia=[f"reformateo/documento/datos_cache/"
                                  f"preproceso_{cobertura}.npz"])


# ─────────────────────────────────────────────────────────────────────────────
def f39_ritmos(cobertura: str = "m1"):
    """
    F3.9 y F3.10 — El ritmo semanal y el anual.

    A la izquierda, día hábil frente a fin de semana: la demanda cae pero
    la generación no, de modo que el excedente disponible para intercambio
    es mayor precisamente cuando hay menos gente en los edificios. A la
    derecha, el recorrido a lo largo del horizonte, que en esta latitud
    varía poco pero no nada.
    """
    series, _ = D.preproceso(cobertura)
    dem = sum(series[f"{i}__D_limpia"] for i in D.AGENTES)
    gen = sum(series[f"{i}__G_limpia"] for i in D.AGENTES)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.3))
    filas = []
    for nombre, mascara, trazo in (("Día hábil", dem.index.weekday < 5, "-"),
                                   ("Fin de semana", dem.index.weekday >= 5, "--")):
        pdm = dem[mascara].groupby(dem[mascara].index.hour).mean()
        pgm = gen[mascara].groupby(gen[mascara].index.hour).mean()
        ax1.plot(pdm.index, pdm.values, trazo, color=E.NEUTRO, linewidth=1.7,
                 label=f"Demanda · {nombre.lower()}")
        ax1.plot(pgm.index, pgm.values, trazo, color=E.MECANISMOS["C5"],
                 linewidth=1.7, label=f"Generación · {nombre.lower()}")
        for h in pdm.index:
            filas.append({"corte": nombre, "hora": int(h),
                          "demanda_kW": pdm[h], "generacion_kW": pgm[h]})
    caida = 100 * (1 - dem[dem.index.weekday >= 5].mean()
                   / dem[dem.index.weekday < 5].mean())
    ax1.text(0.03, 0.96,
             f"la demanda cae {E.fmt_miles(caida, 1)} % el fin de semana;\n"
             f"la generación no cambia",
             transform=ax1.transAxes, va="top", fontsize=7.2)
    ax1.set_xlabel("Hora del día")
    ax1.set_ylabel("Potencia media [kW]")
    ax1.set_title("Ritmo semanal", pad=8)
    ax1.set_xticks(range(0, 24, 3))
    ax1.legend(fontsize=6.3, ncol=2, loc="lower center")

    med_g = gen.groupby(gen.index.to_period("M")).mean()
    med_d = dem.groupby(dem.index.to_period("M")).mean()
    x = np.arange(len(med_g))
    ax2.plot(x, med_d.values, marker="o", markersize=3.4, color=E.NEUTRO,
             linewidth=1.6, label="Demanda")
    ax2.plot(x, med_g.values, marker="s", markersize=3.4,
             color=E.MECANISMOS["C5"], linewidth=1.6, label="Generación")
    ax2.set_xticks(x)
    ax2.set_xticklabels([str(p)[5:] + "/" + str(p)[2:4] for p in med_g.index],
                        fontsize=7, rotation=45)
    ax2.set_ylabel("Potencia media [kW]")
    ax2.set_title("Recorrido a lo largo del horizonte", pad=8)
    ax2.legend(fontsize=7.5)
    for p, vd, vg in zip(med_g.index, med_d.values, med_g.values):
        filas.append({"corte": "mensual", "hora": str(p),
                      "demanda_kW": vd, "generacion_kW": vg})
    fig.tight_layout()
    return E.guardar(fig, f"f3_09_ritmos_{cobertura}", datos=pd.DataFrame(filas),
                     procedencia=[f"reformateo/documento/datos_cache/"
                                  f"preproceso_{cobertura}.npz"])


if __name__ == "__main__":
    D.verificar_canon()
    print("\nCapítulo 3 — la domesticación del dato")
    for cob in ("m1", "m3"):
        f32_demanda_negativa(cob)
    f33_reconstruccion("m1", "Udenar")
    for cob in ("m1", "m3"):
        f37_matrices(cob)
        f38_perfiles_instituciones(cob)
        f39_ritmos(cob)
    for cob in ("m1", "m3"):
        f35_outliers_imputacion(cob)
    print("\nlisto.")
