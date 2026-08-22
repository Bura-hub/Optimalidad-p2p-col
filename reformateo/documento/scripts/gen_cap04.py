"""
gen_cap04.py — Figuras del capítulo 4: la frontera de medición.
================================================================
El estudio corre sobre dos coberturas de medición distintas, y no son dos
versiones del mismo cálculo: responden preguntas diferentes. M1 mide el
campus completo por su totalizador; M3 mide solo el circuito que alimenta
el fotovoltaico. La generación es la misma en las dos —el mismo inversor—,
de modo que lo único que cambia es el denominador.

Ese cambio de denominador basta para invertir quién vende y quién compra.
La bifurcación es, por tanto, un resultado del trabajo y no un detalle de
implementación; este capítulo la trata como tal.

    python scripts/gen_cap04.py
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


def _totales(cobertura: str):
    """Demanda y generación horarias agregadas de la comunidad."""
    series, horas = D.preproceso(cobertura)
    dem = sum(series[f"{i}__D_limpia"] for i in D.AGENTES)
    gen = sum(series[f"{i}__G_limpia"] for i in D.AGENTES)
    return series, horas, dem, gen


# ─────────────────────────────────────────────────────────────────────────────
def f42_cobertura():
    """
    F4.2 — Qué mide cada frontera.

    La generación es idéntica en las dos coberturas (mismo inversor por
    institución); lo único que cambia es la demanda contra la que se
    compara. De ahí que la cobertura pase del 19,1 % al 91,2 % sin que se
    haya instalado un solo panel más.

    Las cifras se miden del caché, no se fijan en el código.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.4),
                                   gridspec_kw={"width_ratios": [1, 1.35]})

    filas, resumen = [], {}
    for cob in ("m1", "m3"):
        series, _, dem, gen = _totales(cob)
        resumen[cob] = (dem.sum(), gen.sum(), 100 * gen.sum() / dem.sum())
        for inst in D.AGENTES:
            d = series[f"{inst}__D_limpia"].sum()
            g = series[f"{inst}__G_limpia"].sum()
            filas.append({"cobertura": cob.upper(), "institucion": inst,
                          "demanda_kWh": d, "generacion_kWh": g,
                          "cobertura_pct": 100 * g / d if d else np.nan})

    # ── Panel izquierdo: la comunidad ───────────────────────────────────
    x = np.arange(2)
    dems = [resumen[c][0] for c in ("m1", "m3")]
    gens = [resumen[c][1] for c in ("m1", "m3")]
    ax1.bar(x - 0.19, dems, 0.36, color=E.NEUTRO, label="Demanda medida")
    ax1.bar(x + 0.19, gens, 0.36, color=E.MECANISMOS["C5"], label="Generación")
    ax1.set_xticks(x)
    ax1.set_xticklabels(["M1\ntotalizadores", "M3\nsubmedidores"])
    ax1.set_ylabel("Energía en el horizonte [kWh]")
    ax1.set_title("La comunidad completa", pad=8)
    E.eje_espanol(ax1, "y", "miles")
    ax1.legend(loc="upper right", fontsize=7.5)
    for i, c in enumerate(("m1", "m3")):
        ax1.text(i, max(dems) * 0.055, f"{E.fmt_miles(resumen[c][2], 1)} %",
                 ha="center", fontsize=9, fontweight="bold",
                 color=E.COBERTURAS[c])
    ax1.text(0.5, -0.30, "la generación no cambia: cambia el denominador",
             transform=ax1.transAxes, ha="center", fontsize=7.5,
             style="italic", color=E.NEUTRO)

    # ── Panel derecho: institución por institución ──────────────────────
    df = pd.DataFrame(filas)
    ancho, y = 0.36, np.arange(len(D.AGENTES))
    for k, cob in enumerate(("m1", "m3")):
        sub = df[df.cobertura == cob.upper()].set_index("institucion") \
                .reindex(D.AGENTES)
        ax2.barh(y + (k - 0.5) * ancho, sub["cobertura_pct"], ancho,
                 color=E.COBERTURAS[cob], label=cob.upper())
        for j, v in enumerate(sub["cobertura_pct"]):
            ax2.text(v + 2, y[j] + (k - 0.5) * ancho, E.fmt_miles(v, 0) + " %",
                     va="center", fontsize=7, color=E.COBERTURAS[cob])
    ax2.axvline(100, color=E.ALERTA, linestyle="--", linewidth=1.0)
    ax2.text(101, len(D.AGENTES) - 0.35, "autosuficiencia\nnominal",
             fontsize=6.8, color=E.ALERTA, va="top")
    ax2.set_yticks(y)
    ax2.set_yticklabels([E.etiqueta_institucion(i) for i in D.AGENTES], fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xlabel("Generación sobre demanda medida [%]")
    ax2.set_title("Por institución", pad=8)
    ax2.legend(loc="lower right", fontsize=7.5)

    fig.tight_layout()
    return E.guardar(fig, "f4_02_cobertura", datos=df, procedencia=[
        "reformateo/documento/datos_cache/preproceso_m1.npz",
        "reformateo/documento/datos_cache/preproceso_m3.npz",
        "configuraciones: DEMAND_METER_CONFIG y PAPER_METER_DEMAND_CONFIG",
    ])


# ─────────────────────────────────────────────────────────────────────────────
def f43_perfiles_m1_m3():
    """
    F4.3 — Los mismos días vistos por las dos fronteras.

    Perfil medio por hora de la comunidad en cada cobertura. La curva de
    generación es exactamente la misma en los dos paneles; la de demanda
    cae casi un factor cinco. Es la forma más directa de mostrar que la
    frontera de medición no cambia el recurso, solo la escala contra la
    que se lo mide.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.5, compartir_y=False)
    filas = []
    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
        _, _, dem, gen = _totales(cob)
        pd_, pg = dem.groupby(dem.index.hour).mean(), gen.groupby(gen.index.hour).mean()
        ax.fill_between(pg.index, 0, pg.values, color=E.MECANISMOS["C5"],
                        alpha=0.28, zorder=1)
        ax.plot(pg.index, pg.values, color=E.MECANISMOS["C5"], linewidth=1.7,
                label="Generación", zorder=3)
        ax.plot(pd_.index, pd_.values, color=E.NEUTRO, linewidth=1.7,
                label="Demanda medida", zorder=4)
        ax.set_xlabel("Hora del día")
        ax.set_xticks(range(0, 24, 3))
        ax.legend(loc="upper left", fontsize=7.5)
        cob_pct = 100 * gen.sum() / dem.sum()
        ax.text(0.97, 0.95, f"cobertura {E.fmt_miles(cob_pct, 1)} %",
                transform=ax.transAxes, ha="right", va="top", fontsize=7.5,
                color=E.COBERTURAS[cob], fontweight="bold")
        for h in pd_.index:
            filas.append({"cobertura": cob.upper(), "hora": int(h),
                          "demanda_media_kW": pd_[h], "generacion_media_kW": pg[h]})
    ax_m1.set_ylabel("Potencia media [kW]")
    ax_m3.set_ylabel("Potencia media [kW]")
    fig.tight_layout()
    return E.guardar(fig, "f4_03_perfiles_m1_m3", datos=pd.DataFrame(filas),
                     procedencia=[
                         "reformateo/documento/datos_cache/preproceso_m1.npz",
                         "reformateo/documento/datos_cache/preproceso_m3.npz"])


# ─────────────────────────────────────────────────────────────────────────────
def f44_inversion_papeles():
    """
    F4.4 — La inversión de los papeles.

    Barras divergentes: hacia la derecha la energía que cada institución
    aporta al mercado, hacia la izquierda la que absorbe. Las cinco
    instituciones conservan el mismo orden vertical en los dos paneles, de
    modo que el cambio de frontera se lee como un vuelco del perfil.

    Es la figura que sostiene la regla de redacción más importante del
    documento: ningún superlativo se escribe sin decir de qué cobertura
    habla, porque el mayor vendedor de M1 casi no vende en M3, y el mayor
    comprador de M3 apenas compra en M1.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.9, compartir_y=True,
                                   titulos=False)
    filas = []
    reparto = {c: D.reparto_p2p(c).set_index("institucion").reindex(D.AGENTES)
               for c in ("m1", "m3")}
    tope = max(max(r["vende_pct"].max(), r["compra_pct"].max())
               for r in reparto.values())

    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
        r = reparto[cob]
        y = np.arange(len(D.AGENTES))
        ax.barh(y, r["vende_pct"], 0.6, color=E.MECANISMOS["C5"])
        ax.barh(y, -r["compra_pct"], 0.6, color=E.MECANISMOS["C2"])
        ax.axvline(0, color="#333333", linewidth=1.0)
        # En lugar de una leyenda, que taparía la fila más larga, el
        # sentido de cada lado se rotula sobre el propio eje.
        ax.text(0.02, 1.03, "$\\leftarrow$ compra", transform=ax.transAxes,
                ha="left", va="bottom", fontsize=8, fontweight="bold",
                color=E.MECANISMOS["C2"])
        ax.text(0.98, 1.03, "vende $\\rightarrow$", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=8, fontweight="bold",
                color=E.MECANISMOS["C5"])
        ax.set_yticks(y)
        ax.set_yticklabels([E.etiqueta_institucion(i) for i in D.AGENTES], fontsize=8)
        ax.invert_yaxis()
        ax.set_xlim(-tope * 1.32, tope * 1.32)
        ax.set_xlabel("Participación en la energía transada [%]")
        ax.xaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: E.fmt_miles(abs(v), 0)))

        for j, (v, c) in enumerate(zip(r["vende_pct"], r["compra_pct"])):
            if v >= 1.0:
                ax.text(v + tope * 0.04, j, E.fmt_miles(v, 1),
                        va="center", fontsize=7, color=E.MECANISMOS["C5"])
            if c >= 1.0:
                ax.text(-c - tope * 0.04, j, E.fmt_miles(c, 1), va="center",
                        ha="right", fontsize=7, color=E.MECANISMOS["C2"])
            filas.append({"cobertura": cob.upper(), "institucion": D.AGENTES[j],
                          "vende_pct": v, "compra_pct": c})

        # Titulo puesto aqui, con hueco extra, para que quepan encima los
        # rotulos de sentido sin chocar con el nombre de la cobertura.
        ax.set_title(E.TITULO_COBERTURA[cob].replace(" (", "\n("),
                     color=E.COBERTURAS[cob], fontweight="bold", pad=22)

        # Se resalta el papel dominante de cada frontera.
        dom_v, dom_c = r["vende_pct"].idxmax(), r["compra_pct"].idxmax()
        ax.text(0.5, -0.34,
                f"vende sobre todo {E.etiqueta_institucion(dom_v)} · "
                f"compra sobre todo {E.etiqueta_institucion(dom_c)}",
                transform=ax.transAxes, ha="center", fontsize=7.5,
                style="italic", color=E.COBERTURAS[cob])

    fig.tight_layout()
    return E.guardar(fig, "f4_04_inversion_papeles", datos=pd.DataFrame(filas),
                     procedencia=[
                         "SALIDAS_SERVIDOR/entrega_canonica_2026-08/canonica_m1/"
                         "outputs/p2p_breakdown_flujos.csv",
                         "SALIDAS_SERVIDOR/entrega_canonica_2026-08/canonica_m3/"
                         "outputs/p2p_breakdown_flujos.csv"])


# ─────────────────────────────────────────────────────────────────────────────
def f45_embudo():
    """
    F4.5 — El embudo de horas de mercado.

    De las 6.144 h del horizonte, solo una fracción llega a tener mercado.
    El embudo lo hace explícito en cuatro escalones: horizonte, horas con
    generación, horas en que alguna institución tiene excedente físico, y
    horas en que efectivamente se transó.

    El escalón del excedente usa la definición física (generación menos
    demanda del propio agente). El del mercado sale de los flujos
    liquidados, que es el dato duro.
    """
    etapas = ["Horizonte", "Con generación", "Con excedente", "Con mercado"]
    fig, ax = E.figura(alto=3.3)
    filas = []

    for k, cob in enumerate(("m1", "m3")):
        series, horas, dem, gen = _totales(cob)
        exc = sum(np.maximum(series[f"{i}__G_limpia"] - series[f"{i}__D_limpia"], 0)
                  for i in D.AGENTES)
        n = [len(horas), int((gen > 0).sum()), int((exc > 0).sum()),
             D.flujos_p2p(cob)["hora"].nunique()]
        x = np.arange(len(etapas)) + (k - 0.5) * 0.38
        ax.bar(x, n, 0.36, color=E.COBERTURAS[cob], label=cob.upper())
        for xi, v in zip(x, n):
            ax.text(xi, v + 90, E.fmt_miles(v), ha="center", fontsize=7.2,
                    color=E.COBERTURAS[cob])
        for e, v in zip(etapas, n):
            filas.append({"cobertura": cob.upper(), "etapa": e, "horas": v,
                          "pct_del_horizonte": 100 * v / len(horas)})

    ax.set_xticks(range(len(etapas)))
    ax.set_xticklabels(etapas)
    ax.set_ylabel("Horas")
    ax.set_title("De las 6.144 h del horizonte a las horas con mercado", pad=8)
    E.eje_espanol(ax, "y", "miles")
    ax.legend(loc="upper right", fontsize=7.5)
    ax.set_ylim(0, 6144 * 1.13)
    fig.tight_layout()
    return E.guardar(fig, "f4_05_embudo_horas", datos=pd.DataFrame(filas),
                     procedencia=[
                         "reformateo/documento/datos_cache/preproceso_{m1,m3}.npz",
                         "SALIDAS_SERVIDOR/entrega_canonica_2026-08/canonica_"
                         "{m1,m3}/outputs/p2p_breakdown_flujos.csv"])


if __name__ == "__main__":
    D.verificar_canon()
    print("\nCapítulo 4 — la frontera de medición")
    f42_cobertura()
    f43_perfiles_m1_m3()
    f44_inversion_papeles()
    f45_embudo()
    print("\nlisto.")
