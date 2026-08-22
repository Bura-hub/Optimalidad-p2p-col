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

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estilo as E
import datos as D


# ─────────────────────────────────────────────────────────────────────────────
def f101_mercado_horario():
    """
    F10.1 y F10.2 — El mercado hora a hora.

    Arriba, la energía transada por hora del día; abajo, el precio de
    equilibrio en las horas con mercado. El precio se acota entre el piso
    del juego y el techo tarifario, de modo que la banda dibujada explica
    por qué el precio no puede salirse de ahí.

    Se usa la hoja ``P2P_horario`` del libro canónico, que trae las 6.144
    horas con su energía y sus métricas.
    """
    fig, axes = plt.subplots(2, 2, figsize=(E.ANCHO_COMPLETO, 5.0),
                             sharex=True)
    filas = []
    for k, cob in enumerate(("m1", "m3")):
        h = D.hoja(cob, "comparacion", "P2P_horario")
        h["hora_dia"] = h["Hora"] % 24
        energia = h.groupby("hora_dia")["kWh_P2P"].sum()
        activas = h[h["kWh_P2P"] > 0]

        ax = axes[0, k]
        ax.bar(energia.index, energia.values, 0.8,
               color=E.MECANISMOS["P2P"], alpha=0.85)
        ax.set_title(E.TITULO_COBERTURA[cob].replace(" (", "\n("),
                     color=E.COBERTURAS[cob], fontweight="bold", pad=8)
        ax.set_ylabel("Energía transada [kWh]")
        E.eje_espanol(ax, "y", "miles")
        ax.text(0.03, 0.94,
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
        ax.fill_between(med.index, q1.values, q3.values,
                        color=E.MECANISMOS["P2P"], alpha=0.22)
        ax.plot(med.index, med.values, color=E.MECANISMOS["P2P"], linewidth=1.7)
        ax.set_xlabel("Hora del día")
        ax.set_ylabel("Precio de equilibrio\n[COP/kWh]")
        ax.set_xticks(range(0, 24, 3))
        E.eje_espanol(ax, "y", "miles")

        for hh in med.index:
            filas.append({"cobertura": cob.upper(), "hora": int(hh),
                          "kwh": float(energia.get(hh, 0.0)),
                          "precio_mediano": float(med[hh]),
                          "precio_q1": float(q1[hh]), "precio_q3": float(q3[hh])})

    fig.tight_layout()
    return E.guardar(fig, "f10_01_mercado_horario", datos=pd.DataFrame(filas),
                     procedencia=[
                         "canonica_{m1,m3}/outputs/resultados_comparacion.xlsx "
                         "(hoja P2P_horario)",
                         "canonica_{m1,m3}/graficas/"
                         "fig3_mercado_p2p__precio_promedio_COP_kWh.csv"])


# ─────────────────────────────────────────────────────────────────────────────
def f107_ranking():
    """
    F10.7 — Los seis mecanismos sobre una misma vara.

    La figura de resultado principal. Barras horizontales ordenadas por
    ganancia neta, con el P2P destacado y la diferencia porcentual frente
    al mecanismo colectivo en base mensual, que es el que rige.

    Las dos coberturas dan ordenaciones distintas y las dos se muestran:
    en M1 el P2P encabeza; en M3 lo supera el colectivo. Presentar solo la
    primera sería elegir la lectura favorable.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.8, compartir_y=False)
    filas = []
    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
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
        # Se reserva un tercio del ancho a la derecha para las cifras. Van
        # alineadas en columna, no pegadas a la punta de cada barra: así se
        # leen como una tabla y ninguna desborda el panel.
        ax.set_xlim(lo, hi + (hi - lo) * 0.62)
        x_txt = hi + (hi - lo) * 0.60
        for j, (m, v) in enumerate(zip(r["mecanismo"], r["ganancia_COP"])):
            delta = 100 * (v - ref) / ref
            txt = E.fmt_millones(v, 2)
            if m != "C4_mensual":
                txt += f"  ({'+' if delta >= 0 else ''}{E.fmt_miles(delta, 1)} %)"
            ax.text(x_txt, j, txt, va="center", ha="right", fontsize=7.2,
                    fontweight="bold" if m == "P2P" else "normal")
            filas.append({"cobertura": cob.upper(), "mecanismo": m,
                          "ganancia_COP": float(v),
                          "delta_vs_C4mensual_pct": delta})

        ax.set_xlabel("Ganancia neta en el horizonte [COP]")
        E.eje_espanol(ax, "x", "millones", 0)
        ax.tick_params(axis="x", labelrotation=15, labelsize=7)
        # La nota va bajo el eje, donde no puede taparse con la última barra.
        ax.text(0.5, -0.30, "cifras y porcentajes frente a C4 mensual",
                transform=ax.transAxes, ha="center", fontsize=7,
                style="italic", color=E.NEUTRO)
    fig.tight_layout()
    return E.guardar(fig, "f10_07_ranking", datos=pd.DataFrame(filas),
                     procedencia=["canonica_{m1,m3}/outputs/"
                                  "resultados_comparacion.xlsx (hoja Resumen)"])


# ─────────────────────────────────────────────────────────────────────────────
def f108_por_agente():
    """
    F10.8 y F10.9 — Quién gana y quién pierde.

    La ventaja agregada no se reparte por igual. Se muestra la diferencia
    porcentual de cada institución entre el mercado P2P y el mecanismo
    colectivo en base mensual, que es la comparación que importa.

    Las instituciones con barra negativa pierden frente al colectivo: es
    el dato que sostiene la discusión de racionalidad individual del
    capítulo 12, y se presenta sin suavizar.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.5, compartir_y=False)
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
        ax.set_yticklabels([E.etiqueta_institucion(i) for i in D.AGENTES], fontsize=8)
        ax.invert_yaxis()
        rango = max(abs(delta.min()), abs(delta.max()))
        ax.set_xlim(-rango * 1.45, rango * 1.45)
        for j, v in enumerate(delta.values):
            ax.text(v + np.sign(v) * rango * 0.05, j,
                    f"{'+' if v >= 0 else ''}{E.fmt_miles(v, 1)} %",
                    va="center", ha="left" if v >= 0 else "right", fontsize=7.2,
                    color=colores[j])
        ax.set_xlabel("P2P frente a C4 mensual [%]")
        n_pierde = int((delta < 0).sum())
        ax.text(0.5, -0.30,
                f"{n_pierde} de 5 instituciones pierden frente al colectivo"
                if n_pierde else "ninguna institución pierde",
                transform=ax.transAxes, ha="center", fontsize=7.5,
                style="italic", color=E.COBERTURAS[cob])
        for inst, v in delta.items():
            filas.append({"cobertura": cob.upper(), "institucion": inst,
                          "delta_pct": float(v)})
    fig.tight_layout()
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
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.8, compartir_y=False)
    filas = []
    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
        m = D.sibling(cob, "fig12_comparacion_mensual")
        x = np.arange(len(m))
        for mec, col in (("P2P", "ganancia_P2P"),
                         ("C1", "ganancia_C1"),
                         ("C4_mensual", "ganancia_C4_mensual")):
            ax.plot(x, m[col], marker="o", markersize=3.2,
                    color=E.color_mecanismo(mec),
                    label=E.etiqueta_mecanismo(mec), linewidth=1.5)
        ax.set_xticks(x)
        ax.set_xticklabels([str(v)[:3] for v in m["mes"]], fontsize=7,
                           rotation=45)
        ax.set_ylabel("Ganancia mensual [COP]")
        E.eje_espanol(ax, "y", "millones", 1)
        ax.legend(loc="lower center", fontsize=7, ncol=3)

        ax2 = ax.twinx()
        ax2.bar(x, m["horas_mercado"], 0.55, color=E.APOYO, zorder=0,
                alpha=0.8)
        ax2.set_ylabel("Horas con mercado", fontsize=7.5, color="#8A7A5A")
        ax2.tick_params(labelsize=7, colors="#8A7A5A")
        ax2.grid(False)
        ax2.set_ylim(0, m["horas_mercado"].max() * 3.4)
        ax.set_zorder(ax2.get_zorder() + 1)
        ax.patch.set_visible(False)

        for _, fila in m.iterrows():
            filas.append({"cobertura": cob.upper(), "mes": fila["mes"],
                          "horas_mercado": fila["horas_mercado"],
                          "ganancia_P2P": fila["ganancia_P2P"],
                          "ganancia_C1": fila["ganancia_C1"],
                          "ganancia_C4_mensual": fila["ganancia_C4_mensual"]})
    fig.tight_layout()
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
