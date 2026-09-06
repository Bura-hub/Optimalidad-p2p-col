"""
gen_cal45.py — Las dos figuras que prueban el cambio del umbral.
================================================================
El capítulo 3 describe todavía el umbral distribucional, porque
retirarlo invalida el canon y el cambio entra con la próxima corrida
canónica junto a H-26 y P-21. Estas dos figuras son la prueba de esa
decisión y se construyen ya, para que el día que el texto cambie no haya
que inventarlas con prisa.

Las dos miran lo mismo desde los dos lados:

  f3_10  El filtro viejo retira **dato bueno**. Las once horas que
         descarta, vistas a su resolución nativa de dos minutos, no son
         espigas: el exceso está repartido en toda la hora.
  f3_11  El filtro viejo deja pasar **dato malo**. El único fallo de
         equipo del horizonte informa una potencia diminuta, y un número
         pequeño nunca sobresale de la cola de su propia distribución.

    python scripts/cache_nativo.py     (una vez)
    python scripts/gen_cal45.py

Ver docs/adr/0045-cal45-guardia-fisico-atipicos.md y C-129.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estilo as E  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import cache_nativo as CN  # noqa: E402


# Los umbrales que el filtro vigente calcula para cada serie. No se
# reescriben a mano: salen del mismo censo que la figura del caso usa, y
# aquí se declaran junto a la hora que gobiernan para que la figura y el
# texto no puedan divergir.
CASOS = {
    "umbral_mariana": dict(
        ventana="umbral_mariana", institucion="Mariana", frontera="m1",
        umbral=35.080868, retiradas=["2025-04-24 08:00", "2025-04-24 09:00",
                                     "2025-04-24 10:00"],
        foco="2025-04-24 09:00",
    ),
    "umbral_cesmag": dict(
        ventana="umbral_cesmag", institucion="Cesmag", frontera="m3",
        umbral=17.594502, retiradas=["2025-05-09 09:00"],
        foco="2025-05-09 09:00",
    ),
}


def _num(x, decimales: int = 1) -> str:
    """Número en español: coma decimal y signo menos de verdad.

    El documento entero escribe la coma. Un rótulo con punto decimal se
    delata en cuanto la figura se pone al lado de su párrafo.
    """
    return (f"{x:.{decimales}f}".replace(".", ",").replace("-", "−"))


def f310_umbral_nativo():
    """
    F3.10 — La hora retirada, a la resolución con que se midió.

    Dos casos, el más débil y el más fuerte de los once. A la izquierda la
    Universidad Mariana el 24 de abril, donde la hora que menos sobresale
    tiene 13 de sus 30 muestras por encima del umbral; a la derecha CESMAG
    el 9 de mayo, donde son 29 de 30, es decir, una racha seguida de 58
    minutos. Enseñar el caso débil junto al fuerte es lo que hace el
    argumento: si ni siquiera el más flojo tiene forma de espiga, ninguno
    la tiene.

    Lo que se dibuja es la demanda **reconstruida**, que es la serie sobre
    la que el filtro calcula su umbral, y no la lectura del medidor. En las
    instituciones de medidor neto parcial las dos difieren justo a las horas
    de sol, que son las de todos los casos.

    La distinción la lleva la geometría y no el color: la muestra que supera
    el umbral va con marca rellena y la que no, hueca.
    """
    fig, ejes = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.1))
    filas = []

    for ax, clave in zip(ejes, ("umbral_mariana", "umbral_cesmag")):
        c = CASOS[clave]
        d = CN.ventana(c["ventana"])
        umbral = c["umbral"]
        retiradas = [pd.Timestamp(t) for t in c["retiradas"]]
        serie = d["D"]

        for t in retiradas:
            ax.axvspan(t, t + pd.Timedelta("1h"), color=E.APOYO,
                       zorder=0, linewidth=0)

        ax.plot(serie.index, serie, color=E.TINTA, linewidth=0.6, zorder=2)
        sobre = serie > umbral
        ax.plot(serie.index[sobre], serie[sobre], linestyle="none", marker="o",
                markersize=2.5, markerfacecolor=E.ANTES,
                markeredgecolor=E.ANTES, zorder=4)
        ax.plot(serie.index[~sobre], serie[~sobre], linestyle="none",
                marker="o", markersize=2.5, markerfacecolor="white",
                markeredgecolor=E.TINTA, markeredgewidth=0.45, zorder=3)

        ax.axhline(umbral, color=E.ANTES, linewidth=1.1,
                   linestyle=(0, (4, 2.2)), zorder=5)
        for t, sub in serie.groupby(serie.index.floor("h")):
            ax.plot([t, t + pd.Timedelta("1h")], [sub.mean()] * 2,
                    color=E.DESPUES, linewidth=1.9, zorder=6,
                    solid_capstyle="butt")

        # La cuenta de cada hora, en la base del eje, donde no estorba.
        y0, y1 = serie.min(), serie.max()
        base = y0 - 0.20 * (y1 - y0)
        for t, sub in serie.groupby(serie.index.floor("h")):
            n = int((sub > umbral).sum())
            if n == 0:
                # Un cero no dice nada y ocupa justo el sitio donde cabe el
                # rótulo que explica la fila.
                continue
            ax.text(t + pd.Timedelta("30min"), base, f"{n}/{len(sub)}",
                    ha="center", va="center", fontsize=6.6,
                    color=E.ANTES if t in retiradas else E.NEUTRO,
                    fontweight="bold" if t in retiradas else "normal")
        ax.text(serie.index[0] + pd.Timedelta("4min"), base,
                "muestras sobre\nel umbral:", ha="left", va="center",
                fontsize=6.0, color=E.NEUTRO, linespacing=1.2)
        ax.set_ylim(base - 0.13 * (y1 - y0), y1 + 0.10 * (y1 - y0))

        foco = pd.Timestamp(c["foco"])
        ax.set_title(f"{E.etiqueta_institucion(c['institucion'])} · "
                     f"{E.fmt_fecha(foco, 'dia_corto')}",
                     color=E.COBERTURAS[c["frontera"]], fontsize=8.4,
                     fontweight="bold", pad=6)
        ax.xaxis.set_major_locator(mdates.HourLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H"))
        ax.set_xlim(serie.index[0] - pd.Timedelta("4min"),
                    serie.index[-1] + pd.Timedelta("6min"))
        ax.set_xlabel("Hora del día", fontsize=7.2, labelpad=2)
        ax.tick_params(labelsize=7)

        for t, sub in serie.groupby(serie.index.floor("h")):
            filas.append({
                "caso": clave, "institucion": c["institucion"],
                "frontera": c["frontera"].upper(), "hora": str(t),
                "retirada": t in retiradas, "umbral_kW": umbral,
                "n_muestras": len(sub), "media_kW": sub.mean(),
                "mediana_kW": sub.median(), "min_kW": sub.min(),
                "max_kW": sub.max(),
                "n_sobre_umbral": int((sub > umbral).sum()),
            })

    ejes[0].set_ylabel("Demanda reconstruida (kW)", fontsize=7.6)

    fig.legend(handles=[
        Line2D([], [], marker="o", linestyle="none", markersize=3.3,
               markerfacecolor=E.ANTES, markeredgecolor=E.ANTES,
               label="Muestra sobre el umbral"),
        Line2D([], [], marker="o", linestyle="none", markersize=3.3,
               markerfacecolor="white", markeredgecolor=E.TINTA,
               label="Muestra bajo el umbral"),
        Line2D([], [], color=E.ANTES, linewidth=1.1, linestyle=(0, (4, 2.2)),
               label="Umbral de la serie"),
        Line2D([], [], color=E.DESPUES, linewidth=1.9,
               label="Media de la hora"),
        Patch(facecolor=E.APOYO, edgecolor="none",
              label="Hora que el filtro retira"),
    ], loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=5,
        fontsize=6.5, frameon=False, handlelength=1.8, columnspacing=1.3)

    fig.tight_layout(rect=(0, 0.11, 1, 1))
    return E.guardar(
        fig, "f3_10_umbral_nativo", datos=pd.DataFrame(filas),
        procedencia=[
            "reformateo/documento/datos_cache/nativo.parquet",
            "MedicionesMTE_v3, lectura cada dos minutos del medidor y del "
            "inversor de cada institucion, reconstruidas con la misma cuenta "
            "que el pipeline hace a paso horario",
            "las medias horarias y el recuento de muestras sobre el umbral "
            "reproducen el censo de las once horas retiradas",
        ])


def f311_fallo_tension():
    """
    F3.11 — El fallo que el criterio de la cola no puede ver.

    La noche del 28 de agosto de 2025 dos de las tres fases del medidor de
    la Universidad Mariana se hunden por debajo de la mitad de su tensión
    nominal mientras la tercera se mantiene. El episodio dura unas quince
    horas y tiene tres tramos que la figura separa: el medidor deja de
    informar durante **siete horas seguidas**, vuelve informando una
    potencia constante de \u22120,10 kW, y la sostiene **seis horas más**,
    incluso después de que la tensión ya se ha restablecido.

    Ahí está el punto ciego del criterio distribucional. Un fallo que
    produce números **pequeños** no sobresale de la cola de la distribución
    de su propia serie, de modo que ninguna regla construida sobre esa cola
    puede verlo, suba o baje el multiplicador. El guardia físico lo marca
    por la tensión, que es un canal que no pasa por la media.
    """
    d = CN.ventana("fallo_mariana")
    nominal = 127.0
    t0, t1 = d.index[0], d.index[-1]
    # La rejilla completa, para que el hueco de telemetria ROMPA la linea en
    # vez de cruzarla. Sin esto el trazo une las dos orillas y el hueco
    # parece dato.
    rejilla = pd.date_range(t0, t1, freq="2min", name="instante")
    falta = ~rejilla.isin(d.index)
    d = d.reindex(rejilla)

    fig, (ax_v, ax_p) = plt.subplots(
        2, 1, figsize=(E.ANCHO_COMPLETO, 4.0), sharex=True,
        gridspec_kw={"height_ratios": [1.35, 1.0], "hspace": 0.12})

    # El hueco de telemetria: no es que valga cero, es que no existe.
    for a, b in _rachas(pd.Series(falta, index=rejilla), rejilla):
        if (b - a) < pd.Timedelta("1h"):
            continue
        for ax in (ax_v, ax_p):
            ax.axvspan(a, b, facecolor="white", edgecolor=E.NEUTRO,
                       hatch="////", linewidth=0.5, zorder=1, alpha=0.9)
        ax_v.annotate(
            f"{(b - a) / pd.Timedelta('1h'):.0f} horas sin\nuna sola lectura",
            xy=(a + (b - a) / 2, 64), ha="center", va="center",
            fontsize=6.3, color=E.NEUTRO, linespacing=1.25, zorder=6)

    # Banda de tolerancia: viene de la norma, no de la distribucion del dato.
    ax_v.axhspan(0.9 * nominal, 1.1 * nominal, color=E.APOYO, zorder=0,
                 linewidth=0)
    ax_v.text(t0 + pd.Timedelta("12min"), 0.9 * nominal - 4,
              "banda de ±10 % del nominal", fontsize=6.2, color=E.NEUTRO,
              va="top", zorder=6)

    for col, guion, ancho in [("VA", "solid", 1.2),
                              ("VB", (0, (4, 1.8)), 1.2),
                              ("VC", (0, (1.1, 1.3)), 1.5)]:
        ax_v.plot(d.index, d[col], color=E.TINTA, linewidth=ancho,
                  linestyle=guion, zorder=4)
    ax_v.set_ylabel("Tensión de fase (V)", fontsize=7.6)
    ax_v.set_ylim(0, 148)

    ax_p.plot(d.index, d["P"], color=E.DESPUES, linewidth=1.1, zorder=4)
    ax_p.axhline(0.0, color=E.NEUTRO, linewidth=0.6, zorder=2)
    ax_p.set_ylabel("Potencia (kW)", fontsize=7.6)
    ax_p.set_ylim(-2.5, 19)

    normal = d["P"][:pd.Timestamp("2025-08-28 23:00")]
    ax_p.annotate(
        f"antes del fallo, {_num(normal.mean())} kW de media",
        xy=(pd.Timestamp("2025-08-28 20:20"), 17.6),
        ha="center", va="top", fontsize=6.4, color=E.TINTA)

    pinada = d["P"][pd.Timestamp("2025-08-29 08:00"):
                    pd.Timestamp("2025-08-29 14:00")]
    ax_p.annotate(
        f"después, clavada en {_num(pinada.iloc[0], 2)} kW durante "
        f"{len(pinada) * 2 / 60:.0f} horas,\ny sigue clavada cuando la "
        f"tensión ya volvió",
        xy=(pd.Timestamp("2025-08-29 09:40"), 0.0),
        xytext=(0, 24), textcoords="offset points", ha="center",
        fontsize=6.4, color=E.TINTA, linespacing=1.3,
        arrowprops=dict(arrowstyle="-", color=E.NEUTRO, linewidth=0.6,
                        shrinkA=1, shrinkB=2))

    ax_p.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    ax_p.xaxis.set_major_formatter(mdates.DateFormatter("%H"))
    ax_p.set_xlim(t0 - pd.Timedelta("10min"), t1 + pd.Timedelta("10min"))
    ax_p.set_xlabel("Del 28 al 29 de agosto de 2025 · una muestra cada dos "
                    "minutos", fontsize=7.2, labelpad=2)
    for ax in (ax_v, ax_p):
        ax.tick_params(labelsize=7)

    # La leyenda va DENTRO del panel de tension, en el hueco que la noche
    # normal deja libre. Al pie no cabe: se monta sobre el rotulo del eje.
    ax_v.legend(handles=[
        Line2D([], [], color=E.TINTA, linewidth=1.2, label="Fase A"),
        Line2D([], [], color=E.TINTA, linewidth=1.2, linestyle=(0, (4, 1.8)),
               label="Fase B"),
        Line2D([], [], color=E.TINTA, linewidth=1.5, linestyle=(0, (1.1, 1.3)),
               label="Fase C"),
        Patch(facecolor="white", edgecolor=E.NEUTRO, hatch="////",
              linewidth=0.5, label="Sin lectura"),
    ], loc="lower left", ncol=2, fontsize=6.4, frameon=False,
        handlelength=1.9, columnspacing=1.4, borderaxespad=0.5,
        labelspacing=0.35)

    fig.tight_layout()

    tabla = d.reset_index()[["instante", "P", "VA", "VB", "VC"]].rename(
        columns={"P": "P_kW", "VA": "VA_V", "VB": "VB_V", "VC": "VC_V"})
    return E.guardar(
        fig, "f3_11_fallo_tension", datos=tabla,
        procedencia=[
            "reformateo/documento/datos_cache/nativo.parquet",
            "MedicionesMTE_v3, Universidad Mariana, lectura cada dos minutos "
            "del medidor que las dos fronteras usan",
            "la banda de tension viene de la norma de calidad de servicio, no "
            "de la distribucion de la propia serie",
        ])


def _rachas(mascara: pd.Series, idx) -> list:
    """Los tramos seguidos en que la máscara es cierta, como (inicio, fin)."""
    salida, dentro, arranque = [], False, None
    for t, v in zip(idx, mascara.values):
        if v and not dentro:
            dentro, arranque = True, t
        elif not v and dentro:
            dentro = False
            salida.append((arranque, t))
    if dentro:
        salida.append((arranque, idx[-1]))
    return salida


if __name__ == "__main__":
    print("\nLas dos figuras de la decision del umbral (CAL-45)")
    f310_umbral_nativo()
    f311_fallo_tension()
    print("\nlisto.")
