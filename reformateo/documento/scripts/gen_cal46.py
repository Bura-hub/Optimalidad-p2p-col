"""
gen_cal46.py — La figura del paso de tiempo.
=============================================
El paso horario del modelo no venía de ninguna decisión: se heredó del
Excel de veinticuatro filas del modelo base. La sonda de quince minutos
midió qué pasa al afinarlo, y el barrido de convergencia lleva la medida
hasta la resolución nativa de dos minutos, que es lo más fino que el dato
permite.

La figura enseña lo que ninguna de las dos cifras sueltas enseña: que al
afinar el paso **las dos ramas se separan**. El autoconsumo baja, porque
promediar antes de tomar un mínimo lo sobrestima; y el lado corto sube,
porque la hora borra los papeles de quien está equilibrado en promedio y
comercia dentro de la hora. La primera es común a los seis mecanismos; la
segunda es lo único que el mercado P2P aporta por encima de ellos.

    python scripts/sonda/convergencia_paso.py     (una vez, ~30 s)
    python scripts/gen_cal46.py

Ver docs/adr/0046-cal46-sonda-quince-minutos.md, H-28 y C-132.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estilo as E  # noqa: E402

SALIDAS = Path(__file__).resolve().parent / "sonda" / "salidas"


def _num(x, decimales: int = 1) -> str:
    """Número en español: coma decimal y signo menos de verdad."""
    return f"{x:.{decimales}f}".replace(".", ",").replace("-", "−")


def f312_convergencia_paso():
    """
    F3.12 — Qué se pierde y qué se gana al afinar el paso.

    Eje horizontal invertido a propósito: la hora, que es el paso del
    modelo, queda a la izquierda, y la resolución nativa a la derecha. Se
    lee de izquierda a derecha como «afinar», que es la dirección en que
    el lector piensa la pregunta.

    Las dos curvas se miden contra el valor nativo, que es la mejor
    aproximación al valor verdadero que el dato permite. Ninguna de las
    dos se ha aplanado en los dos minutos, de modo que las dos cifras de
    la hora son **cotas inferiores** de su error, no el error.
    """
    t = pd.read_csv(SALIDAS / "convergencia_paso.csv")
    fig, ejes = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.2),
                             sharey=True)

    for ax, cob in zip(ejes, ("m1", "m3")):
        s = t[t.frontera == cob.upper()].sort_values("paso_min",
                                                     ascending=False)
        x = s.paso_min.values

        ax.axhline(0, color=E.NEUTRO, linewidth=0.7, zorder=1)
        ax.plot(x, s.autoconsumo_vs_nativo_pct, color=E.ANTES, linewidth=1.5,
                marker="o", markersize=3.4, zorder=4)
        ax.plot(x, s.lado_corto_vs_nativo_pct, color=E.DESPUES, linewidth=1.5,
                marker="s", markersize=3.2, linestyle=(0, (4, 2)), zorder=4)

        # Los dos pasos que el documento nombra.
        for paso, etq in ((60, "el paso\ndel modelo"), (15, "la sonda")):
            ax.axvline(paso, color=E.NEUTRO, linewidth=0.6,
                       linestyle=(0, (1.5, 2)), zorder=2)
            ax.annotate(etq, xy=(paso, -30.5), ha="center", va="bottom",
                        fontsize=6.0, color=E.NEUTRO, linespacing=1.2)

        a = float(s[s.paso_min == 60].autoconsumo_vs_nativo_pct.iloc[0])
        c = float(s[s.paso_min == 60].lado_corto_vs_nativo_pct.iloc[0])
        ax.annotate(f"+{_num(a, 2)} %", xy=(60, a), xytext=(7, 5),
                    textcoords="offset points", fontsize=6.6,
                    color=E.ANTES, fontweight="bold")
        ax.annotate(f"{_num(c, 2)} %", xy=(60, c), xytext=(9, -9),
                    textcoords="offset points", fontsize=6.6, va="top",
                    color=E.DESPUES, fontweight="bold")
        # Los ejes del documento escriben el menos, no el guion.
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: _num(v, 0)))

        ax.set_xscale("log")
        ax.set_xlim(78, 1.7)                    # invertido: afinar es ir a la derecha
        ax.set_xticks([60, 30, 15, 10, 6, 4, 2])
        ax.set_xticklabels(["1 h", "30", "15", "10", "6", "4", "2 min"])
        ax.minorticks_off()
        ax.set_ylim(-33, 11)
        ax.set_xlabel("Ventana del promedio", fontsize=7.4, labelpad=2)
        ax.set_title(E.titulo_cobertura(cob, dos_lineas=True),
                     color=E.COBERTURAS[cob], fontsize=8.0,
                     fontweight="bold", pad=6)
        ax.tick_params(labelsize=7)

    ejes[0].set_ylabel("Diferencia contra el valor nativo (%)", fontsize=7.6)

    fig.legend(handles=[
        Line2D([], [], color=E.ANTES, linewidth=1.5, marker="o",
               markersize=3.4,
               label="Autoconsumo · lo que los seis mecanismos comparten"),
        Line2D([], [], color=E.DESPUES, linewidth=1.5, marker="s",
               markersize=3.2, linestyle=(0, (4, 2)),
               label="Lado corto · el techo de lo que el mercado puede mover"),
    ], loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=2,
        fontsize=6.6, frameon=False, handlelength=2.2, columnspacing=1.8)

    fig.tight_layout(rect=(0, 0.10, 1, 1))
    return E.guardar(
        fig, "f3_12_convergencia_paso", datos=t,
        procedencia=[
            "reformateo/documento/scripts/sonda/salidas/convergencia_paso.csv",
            "MedicionesMTE_v3 a paso nativo de dos minutos, con la "
            "reconstruccion net->bruta del pipeline y SIN la etapa de "
            "limpieza, cuya cascada esta escrita en conteos de pasos",
            "solo las horas con las treinta ranuras presentes en las cinco "
            "instituciones a la vez: 5.338 de 6.144 bajo M1 y 5.327 bajo M3",
        ])


if __name__ == "__main__":
    print("\nLa figura del paso de tiempo (CAL-46)")
    f312_convergencia_paso()
    print("\nlisto.")
