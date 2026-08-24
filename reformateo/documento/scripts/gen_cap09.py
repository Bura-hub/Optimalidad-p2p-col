"""
gen_cap09.py — Figuras del capítulo 9: cómo evolucionó el modelo.
==================================================================
Este capítulo cuenta la parte del trabajo que normalmente se borra: las
decisiones que cambiaron las cifras y los hallazgos que se cayeron al
comprobarlos.

Aquí es el único lugar del documento donde se dibujan artefactos
superados —la versión del escenario colectivo que se dejó de publicar, o
las cifras de una corrida anterior—, siempre rotulados como tales. En
cualquier otro capítulo eso sería un defecto; en éste es el contenido.

    python scripts/gen_cap09.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estilo as E
import datos as D

warnings.filterwarnings("ignore")


def _resumen_junio(cobertura: str) -> pd.DataFrame:
    """
    Hoja ``Resumen`` del canon de junio.

    Se usa **solo** en este capítulo y solo para mostrar de qué se venía.
    El canon de junio es referencia histórica: sigue siendo válido salvo
    en el escenario colectivo, que es justamente lo que aquí interesa
    contrastar.
    """
    base = D.CANON_JUNIO / f"canonica_{cobertura}"
    for cand in (base / "resultados_comparacion.xlsx",
                 base / "outputs" / "resultados_comparacion.xlsx"):
        if cand.exists():
            df = pd.read_excel(cand, sheet_name="Resumen")
            return df.rename(columns={"Escenario": "mecanismo",
                                      "Ganancia_neta_COP": "ganancia_COP"})
    raise FileNotFoundError(f"sin canon de junio para {cobertura}")


# ─────────────────────────────────────────────────────────────────────────────
def f93_tres_versiones_c4():
    """
    F9.3 — Las tres versiones del escenario colectivo.

    El mismo escenario regulatorio liquidado de tres maneras distintas a
    lo largo del trabajo: primero bajo el Caso 1 del artículo 20, luego
    bajo el Caso 2 en base horaria, y finalmente bajo el Caso 2 en base
    mensual, que es la que corresponde al período de facturación.

    Es la figura más importante del capítulo porque la tercera versión
    **cambia el resultado del estudio en una de las dos coberturas**: en
    M3 el mecanismo colectivo pasa a superar al mercado P2P. El P2P se
    dibuja como línea de referencia para que ese cruce se vea.

    Se dibuja con puntos y no con barras. Para que el cruce con la línea
    del P2P sea visible hay que recortar el eje vertical —en M1 los tres
    valores caben en el 3 % superior de la escala— y una barra recortada
    miente sobre la proporción: en la versión anterior 39,09 M y 31,84 M
    se veían como cinco a uno. Un punto no tiene área que exagerar. La
    magnitud del cruce, que el eje recortado ya no puede dar, se imprime
    en el veredicto de cada panel.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=4.0, compartir_y=False)
    etiquetas = ["Caso 1\nhorario", "Caso 2\nhorario", "Caso 2\nmensual"]
    colores = ["#CFCFCF", E.MECANISMOS["C4"], E.MECANISMOS["C4_mensual"]]
    filas = []

    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
        jun = _resumen_junio(cob).set_index("mecanismo")["ganancia_COP"]
        ago = D.resumen(cob).set_index("mecanismo")["ganancia_COP"]
        valores = [float(jun["C4"]), float(ago["C4"]), float(ago["C4_mensual"])]
        p2p = float(ago["P2P"])

        x = np.arange(3)
        lo, hi = min(min(valores), p2p), max(max(valores), p2p)
        margen = (hi - lo) * 0.30
        lo, hi = lo - margen, hi + margen

        ax.axhline(p2p, color=E.MECANISMOS["P2P"], linewidth=1.6,
                   linestyle="--", zorder=2)
        ax.text(2.62, p2p + (hi - lo) * 0.015, "P2P (referencia)",
                color=E.MECANISMOS["P2P"], fontsize=7.5, fontweight="bold",
                va="bottom", ha="right")

        for xi, v, c in zip(x, valores, colores):
            # Tallo tenue como guia de lectura; el dato es el punto. El
            # tallo no arranca en cero, y por eso no puede leerse como area.
            ax.plot([xi, xi], [lo, v], color=c, linewidth=0.8, alpha=0.45,
                    zorder=3)
            ax.plot([xi], [v], marker="o", markersize=9, linestyle="none",
                    markerfacecolor="none" if xi == 0 else c,
                    markeredgecolor="#8A8A8A" if xi == 0 else c,
                    markeredgewidth=1.6, zorder=4)
            ax.text(xi, v + (hi - lo) * 0.055, E.fmt_millones(v, 2),
                    ha="center", fontsize=7.6)

        ax.set_xticks(x)
        ax.set_xticklabels(etiquetas, fontsize=7.5)
        E.eje_espanol(ax, "y", "millones", 1)
        ax.set_ylim(lo, hi)
        ax.set_xlim(-0.55, 2.65)
        ax.set_ylabel("Ganancia neta (COP)")

        # El veredicto de cada cobertura, en sus propios terminos.
        d = 100 * (valores[2] - p2p) / p2p
        gana = ("el colectivo supera al P2P" if valores[2] > p2p
                else "el P2P se mantiene arriba")
        ax.text(0.5, -0.30, f"{gana} ({E.fmt_miles(d, 1)} %)",
                transform=ax.transAxes, ha="center",
                fontsize=8, fontweight="bold", color=E.COBERTURAS[cob])

        # La version retirada se marca en la propia figura.
        ax.text(0, lo + (hi - lo) * 0.045, "retirada", ha="center",
                fontsize=6.8, color="#7A7A7A", style="italic")
        ax.text(0.985, 0.02, "eje vertical recortado", transform=ax.transAxes,
                fontsize=6.2, color=E.NEUTRO, style="italic",
                ha="right", va="bottom")

        for e, v in zip(["C4_caso1_horario", "C4_caso2_horario",
                         "C4_caso2_mensual"], valores):
            filas.append({"cobertura": cob.upper(), "version": e,
                          "ganancia_COP": v, "p2p_COP": p2p,
                          "delta_vs_p2p_pct": 100 * (v - p2p) / p2p})

    fig.tight_layout()
    return E.guardar(fig, "f9_03_tres_versiones_c4", datos=pd.DataFrame(filas),
                     procedencia=[
                         "Caso 1: SALIDAS_SERVIDOR/entrega_canonica/canonica_"
                         "{m1,m3}/ (canon de junio, referencia historica)",
                         "Casos 2: SALIDAS_SERVIDOR/entrega_canonica_2026-08/"
                         "canonica_{m1,m3}/outputs/resultados_comparacion.xlsx",
                         "el Caso 1 se muestra solo como decision superada; no "
                         "se publica como resultado"])


# ─────────────────────────────────────────────────────────────────────────────
def f95_reproducibilidad():
    """
    F9.5 — Qué cambió entre corridas y qué no.

    Diferencia relativa de cada mecanismo entre el canon de junio y el de
    agosto. Todos salen en cero salvo el colectivo: el mercado P2P
    reproduce exactamente, hasta el punto de que sus archivos de flujos
    son idénticos byte a byte entre las dos corridas.

    Es la evidencia de que el cambio de resultados no vino de un cambio de
    datos ni de una deriva del solucionador, sino de una única decisión
    regulatoria deliberada.

    Dos cosas que la versión anterior de la figura no decía:

    1. **C2 y C3 son el mismo resultado por construcción** (se comprueba
       aquí mismo, antes de dibujar). Ocupaban dos columnas y se leían
       como dos comprobaciones independientes; ahora ocupan una,
       rotulada ``C2 = C3``.
    2. **Una barra de altura cero no se ve.** Los cinco mecanismos que
       reproducen exactamente no dejaban ninguna marca en el papel, de
       modo que la afirmación central de la figura vivía solo en el texto
       de la anotación. Ahora cada cero lleva su propia marca y su
       ``0,00 %``.

    Y una advertencia de fondo: en C4 no se comparan dos corridas del
    mismo objeto. Junio liquidaba el Caso 1 del artículo 20 y agosto
    liquida el Caso 2 (CAL-41). La diferencia mide esa decisión, no la
    reproducibilidad del código.
    """
    fig, ax = E.figura(alto=3.3)
    grupos = [("P2P", ["P2P"]), ("C1", ["C1"]), ("C2 = C3", ["C2", "C3"]),
              ("C4", ["C4"]), ("C5", ["C5"])]
    filas = []
    ancho = 0.38
    difs_por_cob = {}

    for cob in ("m1", "m3"):
        jun = _resumen_junio(cob).set_index("mecanismo")["ganancia_COP"]
        ago = D.resumen(cob).set_index("mecanismo")["ganancia_COP"]
        # C2 == C3 por construccion: se comprueba, no se supone.
        assert abs(float(ago["C2"]) - float(ago["C3"])) < 1e-6, \
            f"C2 y C3 dejaron de coincidir en {cob}: eso es un hallazgo"
        difs = []
        for etiqueta, claves in grupos:
            a, b = float(jun[claves[0]]), float(ago[claves[0]])
            difs.append(100 * (b - a) / a)
            filas.append({"cobertura": cob.upper(), "mecanismo": etiqueta,
                          "junio_COP": a, "agosto_COP": b,
                          "dif_pct": 100 * (b - a) / a})
        difs_por_cob[cob] = difs

    piso = min(min(d) for d in difs_por_cob.values())
    ax.set_ylim(piso * 1.38, 0.42)

    for k, cob in enumerate(("m1", "m3")):
        difs = difs_por_cob[cob]
        x = np.arange(len(grupos)) + (k - 0.5) * ancho
        ax.bar(x, difs, ancho, color=E.COBERTURAS[cob], label=cob.upper())
        for xi, v in zip(x, difs):
            if abs(v) > 0.01:
                # Desplazado hacia afuera del par: centrado en su propia
                # barra, el rotulo de M1 invadia la barra de M3.
                ax.text(xi + (k - 0.5) * 0.34, v - abs(piso) * 0.05,
                        E.fmt_miles(v, 2) + " %",
                        ha="center", va="top", fontsize=7,
                        color=E.COBERTURAS[cob])
            else:
                # Un cero exacto no tiene barra. Se le pone una marca para
                # que se vea que fue medido y dio cero, no que falta.
                ax.plot([xi - ancho / 2.4, xi + ancho / 2.4], [0, 0],
                        color=E.COBERTURAS[cob], linewidth=2.6,
                        solid_capstyle="butt", zorder=4)
                ax.text(xi, abs(piso) * 0.035, "0,00 %", ha="center",
                        va="bottom", fontsize=6.4, color=E.COBERTURAS[cob])

    ax.axhline(0, color="#333333", linewidth=1.0, zorder=3)
    ax.set_xticks(range(len(grupos)))
    ax.set_xticklabels([g for g, _ in grupos])
    ax.set_xlabel("Mecanismo")
    ax.set_ylabel("Diferencia agosto frente a junio (%)")
    ax.set_title("Solo el escenario colectivo cambió entre corridas", pad=8)
    ax.legend(loc="lower left", fontsize=7.5)
    E.eje_espanol(ax, "y", "miles", 1)

    ax.text(0.025, 0.72,
            "P2P, C1, C2 = C3 y C5 reproducen exactamente:\n"
            "los archivos de flujos del P2P son idénticos byte a byte",
            transform=ax.transAxes, fontsize=7.2, color=E.NEUTRO, ha="left",
            va="center")
    ax.text(0.985, 0.055,
            "en C4 no se comparan dos corridas del mismo objeto:\n"
            "junio liquidaba el Caso 1 del art. 20 y agosto el Caso 2",
            transform=ax.transAxes, fontsize=6.8, color=E.ALERTA, ha="right",
            va="bottom", style="italic")

    fig.tight_layout()
    return E.guardar(fig, "f9_05_reproducibilidad", datos=pd.DataFrame(filas),
                     procedencia=[
                         "SALIDAS_SERVIDOR/entrega_canonica/ (junio)",
                         "SALIDAS_SERVIDOR/entrega_canonica_2026-08/ (agosto)",
                         "identidad byte a byte verificada por Documentos/"
                         "auditoria_artefactos_2026-08-07/verificar_canon_2026-08.py"])


if __name__ == "__main__":
    D.verificar_canon()
    print("\nCapítulo 9 — cómo evolucionó el modelo")
    f93_tres_versiones_c4()
    f95_reproducibilidad()
    print("\nlisto.")
