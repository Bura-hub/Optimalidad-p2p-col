"""
gen_cap02.py — Figuras del capítulo 2: el dato crudo.
======================================================
Qué se midió, con qué instrumentos y durante cuánto tiempo. Las tres
figuras responden a la pregunta que un revisor hace primero: ¿de dónde
salen estos datos y cuánto hay de ellos?

Requiere el censo de fuentes:

    python scripts/cache_fuentes.py
    python scripts/gen_cap02.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estilo as E
import datos as D

CACHE = Path(__file__).resolve().parent.parent / "datos_cache"

# Papeles que hacen falta para que la comunidad esté completa: el medidor
# de cada cobertura y el inversor que define la generación. Los dos
# inversores de reconstrucción de Udenar NO entran. Uno de ellos arranca
# el 3 de septiembre de 2025 y, si se contara, tanto F2.2 como F2.4
# señalarían a Udenar como la fuente que fija el inicio del horizonte,
# que es falso: lo fija el inversor del HUDN el 4 de abril.
ESENCIALES = {"M1", "M3", "M1+M3", "EMS"}


def _censo() -> pd.DataFrame:
    p = CACHE / "fuentes.csv"
    if not p.exists():
        raise FileNotFoundError(
            "Falta fuentes.csv. Generarlo con: python scripts/cache_fuentes.py")
    d = pd.read_csv(p, encoding="utf-8-sig")
    d["inicio"] = pd.to_datetime(d["inicio"])
    d["fin"] = pd.to_datetime(d["fin"])
    return d


# ─────────────────────────────────────────────────────────────────────────────
def _etiquetar(d: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza el nombre de cada equipo a «Entidad - Medidor N» o
    «Entidad - Inversor N», y fija el orden de dibujo.

    Los nombres crudos de la plataforma son heterogéneos: el medidor de
    Udenar se llama «Bloque Sur - Medidor 1 - electricMeter» y el inversor
    de Mariana, «Fronius - Alvernia - inverter». Traen el sitio, la marca
    y la clase de equipo mezclados, y en la figura no aportan nada que la
    institución y el número no digan ya.

    Los inversores se numeran por orden alfabético del nombre crudo dentro
    de cada institución, que para Udenar deja al «Inversor MTE» en tercer
    lugar. Es el que entró en servicio en septiembre.
    """
    import re
    filas = []
    for inst in D.AGENTES:
        sub = d[d["institucion"] == inst]
        med = sub[sub["clase"] == "medidor"].copy()
        med["n"] = med["fuente"].str.extract(r"Medidor\s*(\d+)").astype(float)
        med = med.sort_values("n")
        for _, f in med.iterrows():
            filas.append({**f, "etiqueta": f"{E.etiqueta_institucion(inst)} - "
                                          f"Medidor {int(f['n'])}"})
        inv = sub[sub["clase"] == "inversor"].sort_values("fuente")
        for k, (_, f) in enumerate(inv.iterrows(), start=1):
            filas.append({**f, "etiqueta": f"{E.etiqueta_institucion(inst)} - "
                                          f"Inversor {k}"})
    return pd.DataFrame(filas)


def f22_gantt():
    """
    F2.2 — Cobertura temporal de las veintisiete fuentes.

    Una barra por equipo, del primer al último registro, agrupadas por
    institución.

    **Por qué se agrupa por institución y no por clase de equipo.** La
    pregunta que la figura responde es desde cuándo hay dato y qué
    determina el inicio del horizonte. Para responderla hay que ver cuándo
    quedó completa cada institución, porque el modelo necesita de cada
    sitio un medidor y un inversor: sin generación no hay prosumidor y sin
    demanda no hay agente. Separando todos los medidores de todos los
    inversores, comprobar si un sitio está operativo obligaría a saltar
    entre dos bloques distantes.

    Hay además una prueba concreta de que la agrupación importa. El HUDN
    fija el inicio del horizonte, y dentro del HUDN lo último en entrar en
    servicio es el inversor, no el medidor. Ese detalle, que lo que
    faltaba era la generación y no la medida, solo se ve si el inversor
    está junto a sus medidores.

    Dentro de cada institución van primero los medidores, en su orden de
    numeración, y después los inversores: de lo que se mide a lo que se
    genera, que es el orden en que los toma el pipeline.
    """
    d = _etiquetar(_censo())

    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 5.6))

    # Bandas alternas de fondo, una por institución, para que los cinco
    # bloques se distingan sin necesidad de líneas divisorias.
    y0 = 0
    for k, inst in enumerate(D.AGENTES):
        n = int((d["institucion"] == inst).sum())
        if k % 2 == 0:
            ax.axhspan(y0 - 0.5, y0 + n - 0.5, color="#F4F4F4", zorder=0)
        y0 += n

    ini, fin = pd.Timestamp(D.T_START), pd.Timestamp(D.T_END)
    ax.axvspan(ini, fin, color=E.MECANISMOS["P2P"], alpha=0.12, zorder=1)
    for v in (ini, fin):
        ax.axvline(v, color=E.MECANISMOS["P2P"], linewidth=1.3, zorder=5)

    # El inicio del horizonte lo fija la última fuente ESENCIAL en entrar
    # en servicio, es decir, la que hace falta para que las cinco
    # instituciones esten operativas: el medidor de cada cobertura y el
    # inversor que define la generacion. Los dos inversores de
    # reconstruccion de Udenar quedan fuera del calculo, porque uno de
    # ellos entra en septiembre y no condiciona el arranque.
    ESENCIALES = {"M1", "M3", "M1+M3", "EMS"}
    esenciales = d[d["papel"].isin(ESENCIALES)]
    idx_tope = esenciales["inicio"].idxmax()

    etiquetas, colores_y = [], []
    for i, (j, f) in enumerate(d.iterrows()):
        usado = f["papel"] != "no usado"
        color = E.color_institucion(f["institucion"]) if usado else "#D5D5D5"
        # El inversor se dibuja hachurado: distingue la clase de equipo sin
        # gastar un segundo color, que ya está tomado por la institución.
        ax.barh(i, (f["fin"] - f["inicio"]).days, left=f["inicio"],
                height=0.6, color=color, zorder=3,
                hatch="///" if f["clase"] == "inversor" else None,
                edgecolor="white" if f["clase"] == "inversor" else "none",
                linewidth=0.0)
        if usado:
            ax.plot([f["inicio"]], [i], marker="o", markersize=3.4,
                    color=color, zorder=6, markeredgecolor="white",
                    markeredgewidth=0.5)
        if j == idx_tope:
            ax.plot([f["inicio"]], [i], marker="o", markersize=8,
                    markerfacecolor="none", markeredgecolor=E.ALERTA,
                    markeredgewidth=1.6, zorder=7)
        etiquetas.append(f["etiqueta"])
        colores_y.append(color if usado else "#9A9A9A")

    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(etiquetas, fontsize=6.2)
    for tick, c in zip(ax.get_yticklabels(), colores_y):
        tick.set_color(c)
    ax.set_ylim(len(d) - 0.5, -0.5)

    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
    ax.tick_params(axis="x", labelsize=7)
    ax.set_xlabel("Fecha")
    ax.grid(axis="y", visible=False)

    ax.text(ini, -1.15, " horizonte del estudio ",
            color=E.MECANISMOS["P2P"], fontsize=8, fontweight="bold",
            va="bottom")
    ax.annotate("fija el inicio", xy=(d.loc[idx_tope, "inicio"], idx_tope),
                xytext=(18, -26), textcoords="offset points",
                fontsize=7.2, color=E.ALERTA, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=E.ALERTA, lw=1.0))

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(facecolor=E.NEUTRO, label="Medidor"),
        Patch(facecolor=E.NEUTRO, hatch="///", edgecolor="white",
              label="Inversor"),
        Patch(facecolor="#D5D5D5", label="No empleado por el modelo"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.075), fontsize=7,
        ncol=3, frameon=False)

    fig.tight_layout()
    return E.guardar(fig, "f2_02_gantt_fuentes",
                     datos=d.drop(columns=["n"], errors="ignore"),
                     procedencia=[
                         "MedicionesMTE_v3/ (recorrido de las 27 subcarpetas "
                         "de medidor e inversor)",
                         "censo generado por scripts/cache_fuentes.py"])


# ─────────────────────────────────────────────────────────────────────────────
def _inversores_de_reconstruccion() -> set:
    """
    Nombres de los inversores que entran en la reconstrucción net→bruta.

    El censo (``cache_fuentes.py``) rotula cada inversor con **un solo**
    papel: «EMS» si es el que define la generación del modelo y
    «reconstrucción» en caso contrario. Esa clasificación excluyente
    esconde que los dos papeles se solapan: el inversor EMS de Udenar,
    Mariana y la UCC interviene además en la reconstrucción de su propia
    demanda. Sin este cruce, la figura daría a entender que la
    reconstrucción de Udenar usa dos inversores, y el Capítulo 3 dice
    —correctamente— que usa tres.
    """
    try:
        raiz = Path(__file__).resolve().parents[3]
        if str(raiz) not in sys.path:
            sys.path.insert(0, str(raiz))
        from data.preprocessing import RECONSTRUCTION_INVERTERS_CONFIG
        return {n for v in RECONSTRUCTION_INVERTERS_CONFIG.values() for n in v}
    except Exception:                                   # pragma: no cover
        return set()


RECONSTRUCTORES = _inversores_de_reconstruccion()


def _sufijo_papel(papel: str, fuente: str = "") -> str:
    """Papel del equipo dentro del modelo, en el vocabulario del documento."""
    if papel == "EMS":
        return (" · generación y reconstrucción"
                if fuente in RECONSTRUCTORES else " · generación")
    return {"M1": " · M1", "M3": " · M3", "M1+M3": " · M1 y M3",
            "reconstrucción": " · reconstrucción", "no usado": ""}.get(papel, "")


def f23_cobertura_fuentes():
    """
    F2.3 — Cuánto dato hay en cada fuente.

    Cobertura horaria sobre el horizonte, por fuente. Los inversores se
    evalúan solo en la franja diurna: contar la noche como dato faltante
    confundiría la ausencia de sol con la ausencia de medición.

    La figura sirve para localizar las excepciones, que son dos y están
    acotadas: el Medidor 4 de Udenar, que es auxiliar, y el tercer
    inversor de Udenar, que entró en servicio en septiembre. Las dos se
    señalan sobre su propia barra, porque el promedio las esconde.

    Los equipos se rotulan por institución y número, no por el nombre que
    les da la plataforma. Ese nombre trae el sitio en lugar de la entidad
    —«Bloque Sur» por Udenar, «Alvernia» por Mariana— y obligaría al
    lector a saberse la correspondencia para poder leer la figura.
    """
    d = _etiquetar(_censo())
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 4.6),
                                   gridspec_kw={"width_ratios": [1.55, 1]})

    # ── Los veinte medidores ────────────────────────────────────────────
    med = d[d["clase"] == "medidor"].reset_index(drop=True)
    y = np.arange(len(med))
    usado = med["papel"] != "no usado"
    colores = [E.color_institucion(i) if u else "#CFCFCF"
               for i, u in zip(med["institucion"], usado)]
    ax1.barh(y, med["cobertura_pct"], 0.64, color=colores, zorder=3)
    ax1.set_yticks(y)
    ax1.set_yticklabels([e + _sufijo_papel(p, f) for e, p, f in
                         zip(med["etiqueta"], med["papel"], med["fuente"])],
                        fontsize=6.0)
    for tick, u in zip(ax1.get_yticklabels(), usado):
        tick.set_color("#333333" if u else "#9A9A9A")
    ax1.invert_yaxis()
    # Un renglón y medio de aire arriba, para la línea de la media.
    ax1.set_ylim(len(med) - 0.4, -2.0)
    ax1.set_xlim(0, 118)

    m = med["cobertura_pct"].mean()
    ax1.axvline(m, color=E.ALERTA, linestyle="--", linewidth=1.2, zorder=4)
    ax1.text(m - 1.5, -1.85, f"media de los 20: {E.fmt_miles(m, 1)} %",
             color=E.ALERTA, fontsize=7, ha="right", va="top")
    ax1.set_xlabel("Cobertura horaria sobre el horizonte (%)")
    ax1.set_title("Los 20 medidores  ·  las 24 h", pad=8)

    # El valor va al final de cada barra, no en una anotación con flecha:
    # con veinte barras contiguas no hay ningún hueco donde poner una caja
    # de texto sin tapar la etiqueta de otro equipo. El único que baja del
    # 95 % —auxiliar— queda destacado en color.
    for k, v in enumerate(med["cobertura_pct"]):
        bajo = v < 95
        # Alineadas en columna, a la derecha de la linea de la media: si
        # cada una siguiera a su barra, la del medidor corto cruzaria esa
        # linea y quedaria ilegible.
        ax1.text(101, k, E.fmt_miles(v, 1) + " %", va="center", ha="left",
                 fontsize=5.8, color=E.ALERTA if bajo else "#555555",
                 fontweight="bold" if bajo else "normal")

    # ── Los siete inversores ────────────────────────────────────────────
    inv = d[d["clase"] == "inversor"].reset_index(drop=True)
    y2 = np.arange(len(inv))
    ax2.barh(y2, inv["cobertura_diurna_pct"], 0.6, zorder=3,
             color=[E.color_institucion(i) for i in inv["institucion"]])
    ax2.set_yticks(y2)
    ax2.set_yticklabels([e + _sufijo_papel(p, f) for e, p, f in
                         zip(inv["etiqueta"], inv["papel"], inv["fuente"])],
                        fontsize=5.6)
    ax2.invert_yaxis()
    ax2.set_ylim(len(inv) - 0.4, -2.0)
    ax2.set_xlim(0, 145)
    for k, v in enumerate(inv["cobertura_diurna_pct"]):
        # En columna, salvo la barra corta: ahi el valor va pegado a su
        # barra para dejar libre la columna a la explicacion de por que
        # esa barra es corta.
        ax2.text(103 if v > 60 else v + 3, k, E.fmt_miles(v, 1) + " %",
                 va="center", ha="left", fontsize=6.5, color="#333333")

    m2 = inv["cobertura_diurna_pct"].mean()
    ems = inv[inv["papel"] == "EMS"]["cobertura_diurna_pct"]
    ax2.axvline(m2, color=E.ALERTA, linestyle="--", linewidth=1.2, zorder=4)
    ax2.text(m2 - 3, -1.85, f"media de los 7: {E.fmt_miles(m2, 1)} %",
             color=E.ALERTA, fontsize=7, ha="right", va="top")
    ax2.set_xlabel("Cobertura diurna, 06:00–18:00 (%)")
    ax2.set_title("Los 7 inversores  ·  solo horas de sol", pad=8)

    # La aclaración va a la derecha del valor, en la misma fila: el hueco
    # que deja la barra corta es el único sitio donde no tapa nada.
    k = int(inv["cobertura_diurna_pct"].idxmin())
    ax2.text(103, k, "entró en servicio\nen septiembre", fontsize=6.6,
             color=E.ALERTA, ha="left", va="center", linespacing=1.35)

    from matplotlib.patches import Patch
    fig.legend(handles=[
        Patch(facecolor=E.color_institucion("Udenar"),
              label="Empleado por el modelo (color de la institución)"),
        Patch(facecolor="#CFCFCF", label="Auxiliar, no empleado"),
    ], loc="lower center", bbox_to_anchor=(0.5, -0.035), ncol=2,
        fontsize=7, frameon=False)
    # La media de los siete la arrastra un solo equipo; la cifra que
    # importa para el modelo es la de los cinco que definen la generación.
    fig.text(0.5, -0.075,
             f"Los cinco inversores que definen la generación del modelo "
             f"cubren entre el {E.fmt_miles(ems.min(), 1)} % y el "
             f"{E.fmt_miles(ems.max(), 1)} % de las horas de sol.",
             ha="center", fontsize=7, color="#555555", style="italic")

    fig.tight_layout()
    return E.guardar(fig, "f2_03_cobertura_fuentes",
                     datos=d.drop(columns=["n"], errors="ignore"),
                     procedencia=[
        "censo generado por scripts/cache_fuentes.py sobre MedicionesMTE_v3/"])


# ─────────────────────────────────────────────────────────────────────────────
def f24_horizonte():
    """
    F2.4 — Por qué el horizonte empieza cuando empieza.

    Fecha del primer registro de cada fuente **esencial**. El inicio del
    horizonte no se eligió: lo fija la última de ellas en entrar en
    servicio, porque antes de esa fecha la comunidad no está completa.

    **Qué cuenta como esencial y por qué importa.** Solo las fuentes que
    el modelo lee: el medidor de cada cobertura en cada institución y el
    inversor que define su generación. Los dos inversores que Udenar
    aporta únicamente a la reconstrucción de su demanda quedan fuera, y
    no por comodidad: uno de ellos entra en servicio el 3 de septiembre
    de 2025, cinco meses después del inicio del horizonte, de modo que
    contarlo haría que la figura señalara como causa del arranque a un
    equipo que no lo causa. La causa es el inversor del HUDN, que empieza
    a registrar el 4 de abril a las 05:58, y esa es exactamente la fecha
    de inicio del horizonte.
    """
    d = _etiquetar(_censo())
    esn = (d[d["papel"].isin(ESENCIALES)]
           .sort_values("inicio").reset_index(drop=True))

    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 3.6))
    y = np.arange(len(esn))
    limite = esn["inicio"].max()
    for j, ini in enumerate(esn["inicio"]):
        ax.plot([ini, limite], [j, j], color="#DDDDDD", linewidth=1.0,
                zorder=1)
    ax.scatter(esn["inicio"], y, s=42, zorder=4,
               color=[E.color_institucion(i) for i in esn["institucion"]],
               edgecolors="white", linewidths=0.6)

    ax.axvline(limite, color=E.ALERTA, linewidth=1.6, zorder=5)
    ultima = esn.iloc[-1]

    ax.set_yticks(y)
    ax.set_yticklabels([e + _sufijo_papel(p, f) for e, p, f in
                        zip(esn["etiqueta"], esn["papel"], esn["fuente"])],
                       fontsize=6.0)
    for tick, inst in zip(ax.get_yticklabels(), esn["institucion"]):
        tick.set_color(E.color_institucion(inst))
    ax.invert_yaxis()
    ax.set_ylim(len(esn) - 0.4, -1.0)

    # El eje se recorta a los datos: si llegara hasta septiembre —que es
    # cuando entra el tercer inversor de Udenar, que no es esencial— la
    # mitad derecha de la figura quedaría vacía.
    ax.set_xlim(esn["inicio"].min() - pd.Timedelta(days=6),
                limite + pd.Timedelta(days=12))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_minor_locator(mdates.DayLocator(bymonthday=[15]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.tick_params(axis="x", labelsize=7)
    ax.set_xlabel("Fecha del primer registro (2025)")

    # La anotación se ancla abajo a la izquierda, que es la única zona
    # del eje sin nada dibujado: las tres últimas fuentes entran ya al
    # final, de modo que sus líneas de espera son cortas y dejan libre
    # todo lo anterior a marzo.
    ax.annotate(f"{ultima['etiqueta']}\n"
                f"{limite.strftime('%d/%m a las %H:%M')} — fija el inicio\n"
                f"del horizonte: 4 de abril de 2025",
                xy=(limite, len(esn) - 1),
                xytext=(0.015, 0.035), textcoords="axes fraction",
                fontsize=7.2, color=E.ALERTA, fontweight="bold",
                ha="left", va="bottom", linespacing=1.45,
                arrowprops=dict(arrowstyle="->", color=E.ALERTA, lw=1.0,
                                connectionstyle="arc3,rad=-0.18"))

    ax.set_title("Las fuentes que el modelo necesita, por entrada en servicio",
                 pad=8)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return E.guardar(fig, "f2_04_horizonte",
                     datos=esn.drop(columns=["n"], errors="ignore"),
                     procedencia=[
        "censo generado por scripts/cache_fuentes.py sobre MedicionesMTE_v3/",
        "constantes T_START y T_END en data/xm_data_loader.py"])


# ─────────────────────────────────────────────────────────────────────────────
CACHE_REACTIVA = (Path(__file__).resolve().parent.parent / "figuras"
                  / "cache_reactiva_horaria.csv")
UMBRAL = 0.5      # la norma compara la reactiva contra la mitad de la activa
P_MIN = 0.5       # kW; por debajo se considera que la hora no tiene consumo


def _reactiva() -> pd.DataFrame:
    """
    Serie horaria de potencia activa y reactiva, por institución y frontera.

    La comparación se hace sobre la energía de cada hora, que es como la
    plantea la norma, y no sobre las muestras de dos minutos.
    """
    if not CACHE_REACTIVA.exists():
        raise FileNotFoundError(
            "Falta cache_reactiva_horaria.csv. Generarlo con: "
            "python scripts/cache_reactiva.py")
    d = pd.read_csv(CACHE_REACTIVA, parse_dates=["ts"])
    d["P"] = d["P_kW"].clip(lower=0)
    d["Q"] = d["Q_kvar"].abs()
    d["exceso"] = (d["Q"] - UMBRAL * d["P"]).clip(lower=0)
    d["con_consumo"] = d["P"] > P_MIN
    d["en_exceso"] = d["con_consumo"] & (d["Q"] > UMBRAL * d["P"])
    return d


def _tarifa_red() -> pd.Series:
    """Cargo por uso de redes (transmisión más distribución), mes a mes."""
    tar = D.tarifas_cedenar()
    nt2 = tar[(tar["nivel_tension"] == 2) & (tar["propiedad"] == "cedenar")]
    return (nt2.assign(TD=nt2["Tm"] + nt2["Dnm"])
               .groupby("mes")["TD"].mean())


TOPE_RAZON = 2.0    # recorta el 0,7 % de las horas y hace legible el resto


def f25_reactiva_series():
    """
    F2.5 — La razón entre reactiva y activa, hora a hora, en las diez
    fronteras.

    Una fila por institución y una columna por frontera. La línea gruesa
    es la mediana diaria y la mancha de fondo son las horas sueltas; la
    zona sombreada por encima de la línea discontinua es donde la norma
    cobra.

    Frente a un resumen en dos cifras, la serie muestra el recorrido: si
    el incumplimiento arranca desde el primer día o aparece a mitad del
    horizonte, si es continuo o intermitente, y si hay tramos sin dato.
    Nada de eso cabe en un porcentaje.
    """
    d = _reactiva()
    d = d[d["con_consumo"]].copy()
    d["razon"] = (d["Q"] / d["P"]).clip(upper=TOPE_RAZON)
    d["dia"] = d["ts"].dt.floor("D")

    fig, axes = plt.subplots(len(D.AGENTES), 2, sharex=True, sharey=True,
                             figsize=(E.ANCHO_COMPLETO, 7.0))
    for col, cob in enumerate(("m1", "m3")):
        axes[0, col].set_title(E.titulo_cobertura(cob, dos_lineas=True),
                               color=E.COBERTURAS[cob], fontweight="bold",
                               pad=8, fontsize=8.5)
        g = d[d["cobertura"] == cob]
        for fila, inst in enumerate(D.AGENTES):
            ax = axes[fila, col]
            gi = g[g["institucion"] == inst]
            c = E.color_institucion(inst)

            ax.axhline(UMBRAL, color=E.ALERTA, lw=1.0, ls="--", zorder=4)

            if not gi.empty:
                ax.plot(gi["ts"], gi["razon"], color=c, lw=0.25, alpha=0.26,
                        zorder=2)
                md = gi.groupby("dia")["razon"].median()
                ax.plot(md.index, md.values, color=c, lw=1.0, zorder=3)
                # Solo se sombrea lo que de verdad se cobra. Tinar de
                # fondo toda la banda superior hacia que los paneles
                # cumplidores parecieran tan cargados como los otros.
                ax.fill_between(md.index, UMBRAL, md.values,
                                where=md.values > UMBRAL, interpolate=True,
                                color=E.ALERTA, alpha=0.30, zorder=1,
                                linewidth=0)
                pct = 100 * gi["en_exceso"].sum() / len(gi)
                ax.text(0.985, 0.88, f"{E.fmt_miles(pct, 1)} % de sus horas",
                        transform=ax.transAxes, ha="right", va="top",
                        fontsize=6.2,
                        color=E.ALERTA if pct >= 50 else "#5A5A5A",
                        fontweight="bold" if pct >= 50 else "normal")
                # Una serie con muy pocas horas de consumo no admite la
                # misma lectura que las demas.
                if len(gi) < 0.2 * 6144:
                    ax.text(0.015, 0.88,
                            f"solo {E.fmt_miles(100 * len(gi) / 6144, 0)} % "
                            f"de las horas con consumo",
                            transform=ax.transAxes, ha="left", va="top",
                            fontsize=5.8, color=E.NEUTRO, style="italic")
            else:
                ax.text(0.5, 0.5, "sin dato", transform=ax.transAxes,
                        ha="center", va="center", fontsize=7,
                        color=E.NEUTRO, style="italic")

            ax.set_ylim(0, TOPE_RAZON)
            ax.set_yticks([0, 0.5, 1.0, 1.5])
            ax.grid(axis="x", visible=False)
            if col == 0:
                ax.set_ylabel(E.etiqueta_institucion(inst), fontsize=7.5,
                              color=c, fontweight="bold", rotation=0,
                              ha="right", va="center", labelpad=8)

    for col in (0, 1):
        ax = axes[-1, col]
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(
            FuncFormatter(lambda v, _: E.fmt_fecha(mdates.num2date(v), "mes")))
        ax.set_xlabel("Fecha")

    fig.supylabel("Energía reactiva sobre energía activa, por hora",
                  fontsize=8)
    fig.tight_layout()

    salida = (d.groupby(["cobertura", "institucion", "dia"])["razon"]
                .median().reset_index()
                .rename(columns={"razon": "razon_mediana_diaria"}))
    return E.guardar(fig, "f2_05_reactiva_series", datos=salida,
                     procedencia=[
                         "cache generado por scripts/cache_reactiva.py sobre "
                         "MedicionesMTE_v3/",
                         "umbral del 50 % de la Resolucion CREG 015 de 2018"])


def tabla_reactiva() -> pd.DataFrame:
    """
    Las cifras que sostienen la tabla del texto.

    Se imprimen para poder contrastarlas contra lo escrito sin volver a
    correr nada.
    """
    d = _reactiva()
    td = _tarifa_red()
    d["mes_txt"] = d["ts"].dt.strftime("%Y-%m")
    d["costo"] = d["exceso"] * d["mes_txt"].map(td)
    filas = []
    for cob in ("m1", "m3"):
        g = d[d["cobertura"] == cob]
        for inst in D.AGENTES:
            gi = g[g["institucion"] == inst]
            con = gi[gi["con_consumo"]]
            filas.append({
                "cobertura": cob.upper(),
                "institucion": E.etiqueta_institucion(inst),
                "horas_consumo": len(con),
                "horas_exceso": int(gi["en_exceso"].sum()),
                "pct_exceso": round(100 * gi["en_exceso"].sum() / len(con), 1)
                              if len(con) else float("nan"),
                "razon_mediana": round((con["Q"] / con["P"]).median(), 2)
                                 if len(con) else float("nan"),
                "exceso_kvarh": int(round(gi["exceso"].sum())),
                "cargo_COP": int(round(gi["costo"].sum())),
            })
    r = pd.DataFrame(filas)
    print("\n  tabla del exceso de reactivo")
    print(r.to_string(index=False))
    for cob, g in r.groupby("cobertura"):
        print(f"    {cob} total: {g['exceso_kvarh'].sum():,} kvarh | "
              f"{g['cargo_COP'].sum():,} COP".replace(",", "."))
    r.to_csv(E.DIR_FIGURAS / "t2_reactiva.csv", index=False,
             encoding="utf-8-sig")
    return r


def f26_reactiva_estructura():
    """
    F2.6 — Cuándo ocurre el exceso.

    Fila superior, la razón entre reactiva y activa según la hora del día;
    fila inferior, según el mes. La línea marca el umbral de la norma.

    La figura responde a si el exceso es un episodio o una condición
    permanente de la instalación. Una curva que vive por encima del umbral
    a cualquier hora y en cualquier mes describe lo segundo, y entonces el
    cargo no es una excepción sino parte de la factura corriente.
    """
    d = _reactiva()
    d = d[d["con_consumo"]].copy()
    d["hora"] = d["ts"].dt.hour
    d["mes"] = d["ts"].dt.to_period("M").dt.to_timestamp()
    d["razon"] = d["Q"] / d["P"]
    # Horas del horizonte en cada frontera, para juzgar que serie es escasa.
    bruto = pd.read_csv(CACHE_REACTIVA, usecols=["cobertura", "institucion"])
    total_horas = (bruto.groupby("cobertura")["institucion"].count()
                   / len(D.AGENTES))

    fig, axes = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 2.9),
                             sharey=True)
    axes = axes.reshape(1, 2)
    for col, cob in enumerate(("m1", "m3")):
        axes[0, col].set_title(E.titulo_cobertura(cob, dos_lineas=True),
                               color=E.COBERTURAS[cob], fontweight="bold",
                               pad=8)
        g = d[d["cobertura"] == cob]
        horizonte = int(total_horas[cob])
        for inst in D.AGENTES:
            gi = g[g["institucion"] == inst]
            if gi.empty:
                continue
            c = E.color_institucion(inst)
            eti = E.etiqueta_institucion(inst)
            # Una serie con muy pocas horas de consumo no es comparable
            # con las demas y no debe invitar a compararla. En la frontera
            # secundaria, Mariana no tiene un medidor util.
            escasa = len(gi) < 0.2 * horizonte
            estilo = dict(color=c, lw=1.1 if escasa else 1.5,
                          ls=":" if escasa else "-", zorder=3,
                          alpha=0.75 if escasa else 1.0)
            ph = gi.groupby("hora")["razon"].median()
            axes[0, col].plot(ph.index, ph.values, label=eti, **estilo)

        ax = axes[0, col]
        ax.axhspan(UMBRAL, 1.35, color=E.ALERTA, alpha=0.07, zorder=0)
        ax.axhline(UMBRAL, color=E.ALERTA, lw=1.2, ls="--", zorder=4)
        ax.set_ylim(0, 1.35)
        ax.set_xlim(0, 23)
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xlabel("Hora del día")

    axes[0, 0].set_ylabel("Reactiva sobre activa\n(mediana por hora del día)")
    # El rotulo va en el panel de la izquierda, bajo la linea, que es
    # donde ninguna curva pasa en las dos fronteras.
    axes[0, 0].text(0.98, UMBRAL - 0.04, "umbral de la norma",
                    transform=axes[0, 0].get_yaxis_transform(),
                    ha="right", va="top", fontsize=6.6,
                    color=E.ALERTA, fontweight="bold")

    manejadores, etiquetas = axes[0, 0].get_legend_handles_labels()
    fig.legend(manejadores, etiquetas, loc="lower center", ncol=5,
               fontsize=7, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.085, 1, 1))

    salida = (d.groupby(["cobertura", "institucion", "hora"])["razon"]
                .median().reset_index()
                .rename(columns={"razon": "razon_mediana"}))
    return E.guardar(fig, "f2_06_reactiva_estructura", datos=salida,
                     procedencia=[
                         "cache generado por scripts/cache_reactiva.py sobre "
                         "MedicionesMTE_v3/"])


def reactiva_resumen() -> None:
    """Imprime las cifras que el texto cita, para poder contrastarlas."""
    d = _reactiva()
    td = _tarifa_red()
    d["mes_txt"] = d["ts"].dt.strftime("%Y-%m")
    d["costo"] = d["exceso"] * d["mes_txt"].map(td)
    print("\n  exceso de energia reactiva")
    for cob, g in d.groupby("cobertura"):
        con = g["con_consumo"].sum()
        print(f"    {cob.upper()}: {100*g['en_exceso'].sum()/con:4.1f} % de "
              f"{int(con)} horas | {g['exceso'].sum():8.0f} kvarh | "
              f"{g['costo'].sum():12,.0f} COP".replace(",", "."))


def efecto_mercado_reactivo() -> None:
    """
    Cuanto movería el mercado entre pares el cargo por energía reactiva.

    Es la única vía por la que el reactivo podría alterar la comparación
    entre mecanismos, y hasta aquí estaba enunciada sin cifrar. El mercado
    reduce la energía activa que cada comprador toma de la red; como el
    umbral de la norma es la mitad de esa energía, el umbral baja y una
    parte mayor del reactivo pasa a ser facturable.

    Se calcula **por usuario**, que es como aplica la norma, y no sobre el
    agregado de la comunidad: agregando, el exceso de una institución se
    compensa con el consumo activo de otra y la cifra sale mucho menor.

    Supuesto declarado: cada kilovatio hora comprado en el mercado
    desplaza uno de importación de la red en el medidor del comprador.
    """
    td = _tarifa_red()
    d0 = _reactiva()
    for cob in ("m1", "m3"):
        flujos = pd.read_excel(
            D.CANON / f"canonica_{cob}" / "outputs" / "p2p_breakdown.xlsx",
            sheet_name="Flujos_Transaccion")
        flujos["ts"] = (pd.Timestamp(D.T_START)
                        + pd.to_timedelta(flujos["hora"] - 1, unit="h"))
        compra = (flujos.groupby(["ts", "comprador"])["kWh_transados"].sum()
                        .rename("delta").rename_axis(["ts", "institucion"]))
        r = d0[d0["cobertura"] == cob].copy()
        n0 = len(r)
        r = (r.set_index(["ts", "institucion"]).join(compra, how="left")
              .fillna({"delta": 0.0}))
        # El nombre del nivel importa: si no coincide, pandas alinea solo
        # por la hora y devuelve un producto cruzado que multiplica el
        # cargo por dos. Ya paso una vez.
        assert len(r) == n0, f"el cruce altero las filas: {n0} -> {len(r)}"
        r = r.reset_index()
        r["TD"] = r["ts"].dt.strftime("%Y-%m").map(td)
        sin = (r["Q"] - UMBRAL * r["P"]).clip(lower=0)
        con = (r["Q"] - UMBRAL * (r["P"] - r["delta"]).clip(lower=0)).clip(lower=0)
        c_sin, c_con = (sin * r["TD"]).sum(), (con * r["TD"]).sum()
        print(f"\n  {cob.upper()} · efecto del mercado sobre el cargo")
        print(f"    sin mercado {c_sin:12,.0f} COP".replace(",", "."))
        print(f"    con mercado {c_con:12,.0f} COP".replace(",", "."))
        print(f"    diferencia  {c_con - c_sin:12,.0f} COP".replace(",", "."))


if __name__ == "__main__":
    print("\nCapítulo 2 — el dato crudo")
    f22_gantt()
    f23_cobertura_fuentes()
    f24_horizonte()
    f25_reactiva_series()
    f26_reactiva_estructura()
    reactiva_resumen()
    tabla_reactiva()
    efecto_mercado_reactivo()
    print("\nlisto.")
