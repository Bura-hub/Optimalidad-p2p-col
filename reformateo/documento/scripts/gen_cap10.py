"""
gen_cap10.py — Figuras del capítulo 10: del flujo horario a la cifra agregada.
==============================================================================
Primer capítulo del documento en que aparecen resultados. El orden es
estrictamente ascendente —hora, día, mes, agregado— para que la cifra
final llegue como consecuencia de lo anterior y no como titular.

Todas las series salen de los siblings del canon de agosto, de modo que
lo que cambia respecto a las figuras canónicas es solo la presentación:
los valores son los mismos.

    python scripts/gen_cap10.py
"""

from __future__ import annotations

import calendar
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estilo as E
import datos as D

# Piso de precio nominal del juego, en COP/kWh. Es el valor central del
# barrido SA1_PGB del canon (fila PGB = 280) y el que rige la corrida
# canónica. Se dibuja porque explica la forma de la curva de precio: en la
# cobertura M3 casi la mitad de las horas con mercado liquidan justo ahí.
PISO_PRECIO = 280.0

# Meses del sibling mensual, para detectar los truncados por el horizonte.
MESES_ES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}


def _horas_del_mes(etiqueta: str) -> int:
    """'Abr 2025' -> 720. Horas que tendría el mes completo."""
    abrev, anio = str(etiqueta).split()
    return 24 * calendar.monthrange(int(anio), MESES_ES[abrev])[1]


# ─────────────────────────────────────────────────────────────────────────────
def f101_mercado_horario():
    """
    F10.1 y F10.2 — El mercado hora a hora.

    Arriba, la energía transada por hora del día; abajo, el precio de
    equilibrio en las horas con mercado, resumido por su mediana y su
    recorrido intercuartílico. Se traza además el piso de precio del
    juego, porque es lo que explica la forma de la curva: en la cobertura
    M3 el precio se apoya en el piso durante casi la mitad de las horas
    con mercado, mientras que en M1 nunca se acerca.

    Se usa la hoja ``P2P_horario`` del libro canónico, que trae las 6.144
    horas con su energía y sus métricas.

    Una trampa del artefacto: la columna ``Hora`` está numerada de 1 a
    6.144 y la primera hora del horizonte es la medianoche del 2025-04-04,
    de modo que la hora del día es ``(Hora - 1) % 24``. Con ``Hora % 24``
    el panel de energía quedaba desplazado una hora respecto al de precio,
    que se indexa por posición, y los dos paneles de una misma columna se
    contradecían.
    """
    fig, axes = plt.subplots(2, 2, figsize=(E.ANCHO_COMPLETO, 5.2),
                             sharex=True)
    filas = []
    for k, cob in enumerate(("m1", "m3")):
        h = D.hoja(cob, "comparacion", "P2P_horario")
        h["hora_dia"] = (h["Hora"] - 1) % 24
        energia = h.groupby("hora_dia")["kWh_P2P"].sum().reindex(
            range(24), fill_value=0.0)
        activas = h[h["kWh_P2P"] > 0]

        ax = axes[0, k]
        ax.bar(energia.index, energia.values, 0.8,
               color=E.MECANISMOS["P2P"], alpha=0.85)
        ax.set_title(E.TITULO_COBERTURA[cob].replace(" (", "\n("),
                     color=E.COBERTURAS[cob], fontweight="bold", pad=8)
        if k == 0:
            ax.set_ylabel("Energía transada (kWh)")
        E.eje_espanol(ax, "y", "miles")
        ax.set_ylim(0, energia.max() * 1.20)
        ax.text(0.03, 0.97,
                f"{E.fmt_miles(h['kWh_P2P'].sum())} kWh en "
                f"{E.fmt_miles(len(activas))} horas con mercado",
                transform=ax.transAxes, va="top", fontsize=7.2)

        # Precio de equilibrio: mediana y recorrido intercuartílico por hora.
        ax = axes[1, k]
        sib = D.sibling(cob, "fig3_mercado_p2p__precio_promedio_COP_kWh")
        precio = sib.iloc[:, 0].to_numpy(dtype=float)
        dfp = pd.DataFrame({"hora_dia": np.arange(len(precio)) % 24,
                            "precio": precio})
        dfp = dfp[dfp["precio"] > 0]
        g = dfp.groupby("hora_dia")["precio"]
        med, q1, q3 = g.median(), g.quantile(0.25), g.quantile(0.75)
        en_piso = 100.0 * np.isclose(dfp["precio"], PISO_PRECIO).mean()

        ax.fill_between(med.index, q1.values, q3.values,
                        color=E.MECANISMOS["P2P"], alpha=0.22, linewidth=0,
                        label="Recorrido intercuartílico")
        ax.plot(med.index, med.values, color=E.MECANISMOS["P2P"],
                linewidth=1.7, label="Mediana por hora")
        ax.axhline(PISO_PRECIO, color=E.ALERTA, linestyle="--", linewidth=1.2,
                   label=f"Piso de precio ({E.fmt_miles(PISO_PRECIO)} COP/kWh)")
        ax.set_xlabel("Hora del día")
        if k == 0:
            ax.set_ylabel("Precio de equilibrio\n(COP/kWh)")
        ax.set_xticks(range(0, 24, 3))
        ax.set_xlim(-0.7, 23.7)
        E.eje_espanol(ax, "y", "miles")
        tope = max(q3.max(), med.max())
        ax.set_ylim(PISO_PRECIO - (tope - PISO_PRECIO) * 0.10,
                    tope + (tope - PISO_PRECIO) * 0.34)
        # La nota va al flanco superior derecho, que en las dos coberturas
        # queda vacio: pasadas las 18 h no hay mercado.
        ax.text(0.98, 0.96,
                f"{E.fmt_miles(en_piso, 1)} % de las horas\n"
                f"con mercado liquidan\nen el piso",
                transform=ax.transAxes, ha="right", va="top", fontsize=7,
                color=E.ALERTA, linespacing=1.3)
        if k == 0:
            ax.legend(fontsize=6.8, loc="upper left", ncol=1,
                      handlelength=1.6, labelspacing=0.35)

        for hh in range(24):
            filas.append({"cobertura": cob.upper(), "hora": int(hh),
                          "kwh": float(energia.get(hh, 0.0)),
                          "precio_mediano": float(med.get(hh, np.nan)),
                          "precio_q1": float(q1.get(hh, np.nan)),
                          "precio_q3": float(q3.get(hh, np.nan)),
                          "pct_horas_en_piso": en_piso})

    fig.tight_layout()
    return E.guardar(fig, "f10_01_mercado_horario", datos=pd.DataFrame(filas),
                     procedencia=[
                         "canonica_{m1,m3}/outputs/resultados_comparacion.xlsx "
                         "(hoja P2P_horario)",
                         "canonica_{m1,m3}/graficas/"
                         "fig3_mercado_p2p__precio_promedio_COP_kWh.csv",
                         "piso de precio: 280 COP/kWh, valor nominal del "
                         "barrido SA1_PGB del mismo canon"])


# ─────────────────────────────────────────────────────────────────────────────
def f107_ranking():
    """
    F10.7 — Los seis mecanismos sobre una misma vara.

    La figura de resultado principal. Barras horizontales ordenadas por
    ganancia neta, con el P2P destacado y la diferencia porcentual frente
    al mecanismo colectivo en base mensual, que es el que rige.

    Las dos coberturas dan ordenaciones distintas y las dos se muestran:
    en M1 el P2P encabeza; en M3 lo supera el colectivo en base mensual,
    por 4,54 millones de pesos. Presentar solo la primera sería elegir la
    lectura favorable.

    Las dos coberturas van una sobre otra y no una al lado de la otra,
    que es la disposición del resto del documento. El motivo es de
    espacio: los rótulos de los seis mecanismos y la columna de cifras no
    caben en media caja sin pisarse, y esta es la figura de la que cuelga
    todo el capítulo.
    """
    fig, axes = plt.subplots(2, 1, figsize=(E.ANCHO_COMPLETO, 5.9))
    filas = []
    for ax, cob in zip(axes, ("m1", "m3")):
        ax.set_title(E.TITULO_COBERTURA[cob], color=E.COBERTURAS[cob],
                     fontweight="bold", pad=6, fontsize=9.5)
        r = D.resumen(cob).sort_values("ganancia_COP")
        # C3 coincide con C2 por construccion: se muestra una sola vez y se
        # rotula como par, para no contar dos veces el mismo resultado.
        r = r[r["mecanismo"] != "C3"]
        y = np.arange(len(r))
        colores = [E.color_mecanismo(m) for m in r["mecanismo"]]
        ax.barh(y, r["ganancia_COP"], 0.62, color=colores)
        ax.set_yticks(y)
        ax.set_yticklabels(
            [E.etiqueta_mecanismo(m) + (" $=$ C3" if m == "C2" else "")
             for m in r["mecanismo"]], fontsize=7.5)

        ref = float(r[r["mecanismo"] == "C4_mensual"]["ganancia_COP"].iloc[0])
        lo = r["ganancia_COP"].min() * 0.955
        hi = r["ganancia_COP"].max()
        # Se reserva la banda derecha para las cifras. Van alineadas a la
        # izquierda sobre una misma columna, de modo que se lean como una
        # tabla y ninguna toque la punta de su barra.
        ax.set_xlim(lo, hi + (hi - lo) * 0.52)
        x_txt = hi + (hi - lo) * 0.04
        for j, (m, v) in enumerate(zip(r["mecanismo"], r["ganancia_COP"])):
            delta = 100 * (v - ref) / ref
            txt = E.fmt_millones(v, 2)
            if m != "C4_mensual":
                txt += f"  ({'+' if delta >= 0 else ''}{E.fmt_miles(delta, 1)} %)"
            else:
                txt += "  (referencia)"
            ax.text(x_txt, j, txt, va="center", ha="left", fontsize=7.6,
                    fontweight="bold" if m == "P2P" else "normal")
            filas.append({"cobertura": cob.upper(), "mecanismo": m,
                          "ganancia_COP": float(v),
                          "delta_vs_C4mensual_pct": delta})

        # Marcas solo sobre el tramo con datos: el resto del ancho es la
        # columna de cifras y no representa magnitud alguna.
        ticks = plt.MaxNLocator(5, steps=[1, 2, 5, 10]).tick_values(lo, hi)
        ax.set_xticks([t for t in ticks if lo <= t <= hi])
        E.eje_espanol(ax, "x", "millones", 0)
        ax.tick_params(axis="x", labelsize=7.5)

    fig.tight_layout(rect=[0, 0.085, 1, 1], h_pad=2.2)
    fig.supxlabel("Ganancia neta en el horizonte (COP)", fontsize=9, y=0.052)
    fig.text(0.5, 0.010,
             "cifras en millones de pesos; los porcentajes son frente a "
             "C4 · colectivo (mensual), que es la versión que rige",
             ha="center", fontsize=7, style="italic", color=E.NEUTRO)
    return E.guardar(fig, "f10_07_ranking", datos=pd.DataFrame(filas),
                     procedencia=["canonica_{m1,m3}/outputs/"
                                  "resultados_comparacion.xlsx (hoja Resumen)"])


# ─────────────────────────────────────────────────────────────────────────────
def f108_por_agente():
    """
    F10.8 y F10.9 — Quién gana y quién pierde.

    La ventaja agregada no se reparte por igual. Se muestra la diferencia
    porcentual de la ganancia neta de cada institución entre el mercado
    P2P y el mecanismo colectivo en base mensual, que es la comparación
    que importa.

    No debe confundirse con la Figura 12.2, que compara otra cosa: allí lo
    que se contrasta es el beneficio de permanecer en el mercado frente al
    de desertar en solitario al colectivo en base horaria, y por eso da
    signos distintos para la misma institución.

    Las instituciones con barra negativa pierden frente al colectivo: es
    el dato que sostiene la discusión de racionalidad individual del
    capítulo 12, y se presenta sin suavizar.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.6, compartir_y=False)
    filas = []
    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
        s = D.sibling(cob, "fig6_ganancia_por_agente")
        col_ag = [c for c in s.columns if "agente" in c.lower()][0]
        s = s.set_index(col_ag).reindex(D.AGENTES)
        delta = 100 * (s["ganancia_P2P_COP"] - s["ganancia_C4_mensual_COP"]) \
            / s["ganancia_C4_mensual_COP"]
        y = np.arange(len(delta))
        colores = [E.MECANISMOS["P2P"] if v >= 0 else E.ANTES for v in delta]
        ax.barh(y, delta.values, 0.62, color=colores)
        ax.axvline(0, color="#333333", linewidth=1.0)
        ax.set_yticks(y)
        ax.set_yticklabels([E.etiqueta_institucion(i) for i in D.AGENTES],
                           fontsize=8)
        ax.invert_yaxis()
        rango = max(abs(delta.min()), abs(delta.max()))
        ax.set_xlim(-rango * 1.30, rango * 1.30)
        for j, v in enumerate(delta.values):
            etiqueta = f"{'+' if v >= 0 else ''}{E.fmt_miles(v, 1)} %"
            # Las barras largas llevan la cifra dentro, en blanco: fuera
            # chocaría con los rótulos de institución del panel.
            if abs(v) > rango * 0.42:
                ax.text(v - np.sign(v) * rango * 0.04, j, etiqueta,
                        va="center", ha="right" if v >= 0 else "left",
                        fontsize=7.2, color="white", fontweight="bold")
            else:
                ax.text(v + np.sign(v) * rango * 0.05, j, etiqueta,
                        va="center", ha="left" if v >= 0 else "right",
                        fontsize=7.2, color=colores[j])
        n_pierde = int((delta < 0).sum())
        if n_pierde == 0:
            nota = "ninguna pierde frente al colectivo"
        elif n_pierde == 1:
            nota = "1 de 5 pierde frente al colectivo"
        else:
            nota = f"{n_pierde} de 5 pierden frente al colectivo"
        ax.text(0.5, -0.17, nota, transform=ax.transAxes, ha="center",
                fontsize=7.5, style="italic", color=E.COBERTURAS[cob])
        for inst, v in delta.items():
            filas.append({"cobertura": cob.upper(), "institucion": inst,
                          "delta_pct": float(v)})

    fig.tight_layout(rect=[0, 0.13, 1, 1])
    fig.supxlabel("Ganancia neta: P2P frente a C4 · colectivo (mensual) (%)",
                  fontsize=9, y=0.045)
    return E.guardar(fig, "f10_08_por_agente", datos=pd.DataFrame(filas),
                     procedencia=["canonica_{m1,m3}/graficas/"
                                  "fig6_ganancia_por_agente.csv"])


# ─────────────────────────────────────────────────────────────────────────────
def f105_mensual():
    """
    F10.5 — Mes a mes.

    Ganancia de los tres mecanismos de referencia por mes, con las horas
    de mercado de cada uno superpuestas. Sirve para comprobar que la
    ventaja no procede de un mes atípico y para ver cómo la disponibilidad
    del recurso arrastra el resultado.

    Dos meses del horizonte están truncados y hay que decirlo, porque de
    otro modo su caída se leería como estacionalidad: el horizonte empieza
    el 4 de abril y termina el 16 de diciembre, así que abril aporta 648
    horas y diciembre solo 360, frente a las 720 o 744 de un mes completo.
    El desplome de diciembre es aritmética del calendario, no del mercado.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=4.0, compartir_y=False)
    filas = []
    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
        m = D.sibling(cob, "fig12_comparacion_mensual")
        x = np.arange(len(m))
        parcial = [float(t) < 0.99 * _horas_del_mes(v)
                   for t, v in zip(m["T_mes"], m["mes"])]

        # Los meses truncados se marcan antes de dibujar nada, para que la
        # banda quede por debajo de las series.
        for j, es_parcial in enumerate(parcial):
            if es_parcial:
                ax.axvspan(j - 0.5, j + 0.5, color=E.APOYO, alpha=0.55,
                           zorder=0)

        series = {}
        for mec, col in (("P2P", "ganancia_P2P"),
                         ("C1", "ganancia_C1"),
                         ("C4_mensual", "ganancia_C4_mensual")):
            ax.plot(x, m[col], marker="o", markersize=3.2,
                    color=E.color_mecanismo(mec),
                    label=E.etiqueta_mecanismo(mec), linewidth=1.5, zorder=4)
            series[mec] = m[col].to_numpy(float)

        ax.set_xticks(x)
        ax.set_xticklabels([str(v)[:3] for v in m["mes"]], fontsize=7,
                           rotation=45)
        ax.set_xlim(-0.6, len(m) - 0.4)
        if ax is ax_m1:
            ax.set_ylabel("Ganancia mensual (COP)")
        E.eje_espanol(ax, "y", "millones", 1)

        todos = np.concatenate(list(series.values()))
        piso, techo = todos.min(), todos.max()
        # Holgura arriba para la leyenda y abajo para que los marcadores de
        # diciembre no queden pegados al eje.
        ax.set_ylim(piso - (techo - piso) * 0.09,
                    techo + (techo - piso) * 0.26)
        ax.legend(loc="upper left", fontsize=7, ncol=1, handlelength=1.6,
                  labelspacing=0.3)

        idx_parcial = [j for j, p in enumerate(parcial) if p]
        nota_truncados = ""
        if idx_parcial:
            nombres = " y ".join(str(m["mes"].iloc[j])[:3].lower()
                                 for j in idx_parcial)
            horas = " y ".join(f"{int(m['T_mes'].iloc[j])} h"
                               for j in idx_parcial)
            nota_truncados = (
                f"franja sombreada: {nombres} están truncados por el "
                f"horizonte ({horas}); su caída no es estacional")

        ax2 = ax.twinx()
        ax2.bar(x, m["horas_mercado"], 0.55, color=E.APOYO, zorder=1,
                alpha=0.9)
        if ax is ax_m3:
            ax2.set_ylabel("Horas con mercado", fontsize=7.5, color="#8A7A5A")
        ax2.tick_params(labelsize=7, colors="#8A7A5A")
        ax2.grid(False)
        ax2.set_ylim(0, m["horas_mercado"].max() * 3.4)
        ax.set_zorder(ax2.get_zorder() + 1)
        ax.patch.set_visible(False)

        for (_, fila), es_parcial in zip(m.iterrows(), parcial):
            filas.append({"cobertura": cob.upper(), "mes": fila["mes"],
                          "T_mes": fila["T_mes"], "mes_truncado": es_parcial,
                          "horas_mercado": fila["horas_mercado"],
                          "ganancia_P2P": fila["ganancia_P2P"],
                          "ganancia_C1": fila["ganancia_C1"],
                          "ganancia_C4_mensual": fila["ganancia_C4_mensual"]})
    fig.tight_layout(rect=[0, 0.055, 1, 1])
    fig.text(0.5, 0.012, nota_truncados, ha="center", fontsize=6.8,
             style="italic", color="#7A6A4A")
    return E.guardar(fig, "f10_05_mensual", datos=pd.DataFrame(filas),
                     procedencia=["canonica_{m1,m3}/graficas/"
                                  "fig12_comparacion_mensual.csv"])


if __name__ == "__main__":
    D.verificar_canon()
    print("\nCapítulo 10 — resultados")
    f101_mercado_horario()
    f105_mensual()
    f107_ranking()
    f108_por_agente()
    print("\nlisto.")
