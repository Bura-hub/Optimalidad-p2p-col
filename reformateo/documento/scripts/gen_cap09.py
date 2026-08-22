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
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.9, compartir_y=False)
    etiquetas = ["Caso 1\nhorario", "Caso 2\nhorario", "Caso 2\nmensual"]
    colores = ["#CFCFCF", E.MECANISMOS["C4"], E.MECANISMOS["C4_mensual"]]
    filas = []

    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
        jun = _resumen_junio(cob).set_index("mecanismo")["ganancia_COP"]
        ago = D.resumen(cob).set_index("mecanismo")["ganancia_COP"]
        valores = [float(jun["C4"]), float(ago["C4"]), float(ago["C4_mensual"])]
        p2p = float(ago["P2P"])

        x = np.arange(3)
        barras = ax.bar(x, valores, 0.58, color=colores)
        # La versión retirada se dibuja con borde discontinuo, para que se
        # distinga de las dos vigentes sin necesidad de leyenda. bar() no
        # acepta una lista de estilos, así que se aplica barra por barra.
        barras[0].set_edgecolor("#8A8A8A")
        barras[0].set_linestyle("--")
        barras[0].set_linewidth(1.1)
        ax.axhline(p2p, color=E.MECANISMOS["P2P"], linewidth=1.6,
                   linestyle="--", zorder=5)
        # El rótulo va encima de su propia línea, no sobre ella: centrado
        # verticalmente quedaba tachado por el trazo discontinuo.
        ax.text(2.90, p2p, "P2P", color=E.MECANISMOS["P2P"], fontsize=8,
                fontweight="bold", va="bottom", ha="right")

        ax.set_xticks(x)
        ax.set_xticklabels(etiquetas, fontsize=7.5)
        E.eje_espanol(ax, "y", "millones", 1)
        lo = min(min(valores), p2p) * 0.965
        hi = max(max(valores), p2p) * 1.035
        ax.set_ylim(lo, hi)
        ax.set_xlim(-0.6, 2.9)

        for xi, v in zip(x, valores):
            ax.text(xi, v + (hi - lo) * 0.02, E.fmt_millones(v, 2),
                    ha="center", fontsize=7.4)

        # El veredicto de cada cobertura, en sus propios términos.
        gana = "el colectivo supera al P2P" if valores[2] > p2p \
            else "el P2P se mantiene arriba"
        ax.text(0.5, -0.30, gana, transform=ax.transAxes, ha="center",
                fontsize=8, fontweight="bold", color=E.COBERTURAS[cob])

        # La versión retirada se marca en la propia figura.
        ax.text(0, lo + (hi - lo) * 0.045, "retirada", ha="center",
                fontsize=6.8, color="#7A7A7A", style="italic")

        for e, v in zip(["C4_caso1_horario", "C4_caso2_horario",
                         "C4_caso2_mensual"], valores):
            filas.append({"cobertura": cob.upper(), "version": e,
                          "ganancia_COP": v, "p2p_COP": p2p,
                          "delta_vs_p2p_pct": 100 * (v - p2p) / p2p})

    ax_m1.set_ylabel("Ganancia neta [COP]")
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
    agosto. Todos los mecanismos salen en cero salvo el colectivo: el
    mercado P2P reproduce exactamente, hasta el punto de que sus archivos
    de flujos son idénticos byte a byte entre las dos corridas.

    Es la evidencia de que el cambio de resultados no vino de un cambio de
    datos ni de una deriva del solucionador, sino de una única decisión
    regulatoria deliberada.
    """
    fig, ax = E.figura(alto=3.2)
    mecanismos = ["P2P", "C1", "C2", "C3", "C4", "C5"]
    filas = []
    ancho = 0.38

    for k, cob in enumerate(("m1", "m3")):
        jun = _resumen_junio(cob).set_index("mecanismo")["ganancia_COP"]
        ago = D.resumen(cob).set_index("mecanismo")["ganancia_COP"]
        difs = []
        for m in mecanismos:
            a, b = float(jun[m]), float(ago[m])
            difs.append(100 * (b - a) / a)
            filas.append({"cobertura": cob.upper(), "mecanismo": m,
                          "junio_COP": a, "agosto_COP": b,
                          "dif_pct": 100 * (b - a) / a})
        x = np.arange(len(mecanismos)) + (k - 0.5) * ancho
        ax.bar(x, difs, ancho, color=E.COBERTURAS[cob], label=cob.upper())
        for xi, v in zip(x, difs):
            if abs(v) > 0.01:
                ax.text(xi, v + (0.12 if v > 0 else -0.35),
                        E.fmt_miles(v, 2) + " %", ha="center", fontsize=7,
                        color=E.COBERTURAS[cob])

    ax.axhline(0, color="#333333", linewidth=1.0)
    ax.set_xticks(range(len(mecanismos)))
    ax.set_xticklabels([E.etiqueta_mecanismo(m).split(" · ")[0]
                        for m in mecanismos])
    ax.set_ylabel("Diferencia agosto frente a junio [%]")
    ax.set_title("Solo el escenario colectivo cambió entre corridas", pad=8)
    ax.legend(loc="upper left", fontsize=7.5)
    E.eje_espanol(ax, "y", "miles", 1)

    ax.annotate("cinco mecanismos reproducen exactamente:\n"
                "los archivos de flujos del P2P son idénticos byte a byte",
                xy=(1.0, 0), xytext=(0.30, 0.28), textcoords="axes fraction",
                fontsize=7.2, color=E.NEUTRO, ha="left",
                arrowprops=dict(arrowstyle="->", color=E.NEUTRO, lw=0.8))

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
