"""
La figura de la eficiencia del emparejamiento (H-39).

Enseña, hora a hora y en las dos fronteras, cuánto del ahorro alcanzable
captura el mercado, frente a un reparto proporcional ciego que mueve
exactamente el mismo volumen.

  f7_01  el rango que el emparejamiento puede decidir, con las dos marcas

Cada hora se dibuja como el segmento que va del peor reparto posible al
óptimo. Dentro de ese segmento van dos marcas: el reparto ciego y el que
produce el mercado. Si la marca del mercado queda por encima de la del
reparto ciego, el juego aportó algo esa hora.

Las horas de banda uniforme, es decir aquellas en que todos los compradores
comparten techo y todos los vendedores comparten piso, tienen el segmento
colapsado en el tope, porque allí cualquier reparto del mismo volumen vale
exactamente igual y no hay nada que decidir.

Los datos salen de las dos sondas, que hay que haber corrido antes:

    python sonda/eficiencia.py       --cobertura m1 --muestra 30
    python sonda/cotas_excedente.py  --cobertura m1 --muestra 30

Uso:
    python gen_eficiencia.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import estilo as E  # noqa: E402

SALIDAS = AQUI / "sonda" / "salidas"


def _n(x, dec=1):
    """Número con coma decimal, como el resto del documento."""
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def carga(cob: str) -> pd.DataFrame:
    """Cruza las dos sondas por hora y deja lo que la figura dibuja."""
    ef = pd.read_csv(SALIDAS / f"eficiencia_{cob}.csv")
    ct = pd.read_csv(SALIDAS / f"cotas_{cob}.csv")
    d = ef.merge(ct[["k", "mejor", "peor", "ef_ciego"]], on="k")
    d["peor_pct"] = 100.0 * d["peor"] / d["mejor"]
    d["ventaja"] = d["ef_aco"] - d["ef_ciego"]
    # se ordena por la ventaja, de modo que el signo recorra el eje de una
    # sola vez y la comparación entre fronteras se lea sin contar puntos
    return d.sort_values("ventaja", ascending=False).reset_index(drop=True)


def dibuja(ax, d: pd.DataFrame, cob: str) -> None:
    x = np.arange(len(d))
    color = E.COBERTURAS[cob]

    # el rango que el emparejamiento puede decidir: del peor reparto al óptimo
    ax.vlines(x, d["peor_pct"], 100.0, color=E.APAGADO, lw=2.6,
              zorder=1, label="_")

    # el tramo entre las dos marcas, que es lo que el juego gana o pierde.
    # Continuo cuando gana y discontinuo cuando pierde, de modo que la
    # distinción sobreviva impresa en gris
    gana = d["ventaja"] > 1e-6
    pierde = d["ventaja"] < -1e-6
    for masc, estilo in ((gana, "-"), (pierde, ":")):
        if masc.any():
            ax.vlines(x[masc.values], d.loc[masc, "ef_ciego"],
                      d.loc[masc, "ef_aco"], color=color, lw=1.4,
                      linestyles=estilo, zorder=2)

    ax.plot(x, d["ef_ciego"], "o", ms=4.2, mfc="white", mec=E.TINTA,
            mew=0.9, ls="none", zorder=3)
    ax.plot(x, d["ef_aco"], "D", ms=4.0, mfc=color, mec=color,
            ls="none", zorder=4)

    ax.axhline(100.0, color=E.TINTA, lw=0.8, ls="--", zorder=0)
    ax.set_ylim(0, 108)
    ax.set_xlim(-1, len(d))
    ax.set_xticks([])
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0 %", "25 %", "50 %", "75 %", "100 %"])
    ax.grid(axis="y", alpha=0.25)

    # el recuento, dentro del eje, porque es lo que la figura demuestra
    ng, np_ = int(gana.sum()), int(pierde.sum())
    ax.text(0.02, 0.06, f"gana {ng} · empata {len(d) - ng - np_} · pierde {np_}",
            transform=ax.transAxes, fontsize=8, color=E.TINTA,
            va="bottom", ha="left")


def main() -> None:
    faltan = [f for cob in ("m1", "m3")
              for f in (SALIDAS / f"eficiencia_{cob}.csv",
                        SALIDAS / f"cotas_{cob}.csv") if not f.exists()]
    if faltan:
        print("  faltan salidas de las sondas:")
        for f in faltan:
            print(f"    {f}")
        raise SystemExit(1)

    datos = {cob: carga(cob) for cob in ("m1", "m3")}
    fig, ax1, ax3 = E.figura_m1_m3(alto=3.3, compartir_y=True)
    dibuja(ax1, datos["m1"], "m1")
    dibuja(ax3, datos["m3"], "m3")
    ax1.set_ylabel("Ahorro capturado, sobre el alcanzable")

    # El rótulo del eje y la leyenda ocupan dos renglones propios bajo los
    # paneles. Se colocan a mano, porque el ayudante de rótulo común llama a
    # su vez al ajuste automático y la leyenda acaba encima del rótulo.
    fig.tight_layout(rect=(0, 0.16, 1, 1))
    fig.text(0.5, 0.105, "Horas de la muestra, ordenadas por la ventaja "
                         "del mercado sobre el reparto ciego",
             ha="center", va="center", fontsize=9.5)

    from matplotlib.lines import Line2D
    marcas = [
        Line2D([], [], color=E.APAGADO, lw=2.6,
               label="Rango que decide el emparejamiento"),
        Line2D([], [], marker="o", ls="none", ms=4.2, mfc="white",
               mec=E.TINTA, mew=0.9, label="Reparto proporcional ciego"),
        Line2D([], [], marker="D", ls="none", ms=4.0, mfc=E.TINTA,
               mec=E.TINTA, label="Mercado entre pares"),
    ]
    fig.legend(handles=marcas, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 0.005), fontsize=8.5,
               handletextpad=0.5, columnspacing=1.8)

    tabla = pd.concat([d.assign(frontera=c.upper()) for c, d in datos.items()])
    cols = ["frontera", "k", "J", "I", "uniforme", "mejor", "peor_pct",
            "ef_ciego", "ef_aco", "ef_alt", "efvol_aco", "ventaja"]
    ruta = E.guardar(fig, "f7_01_eficiencia_emparejamiento",
                     datos=tabla[cols],
                     procedencia=[
                         "reformateo/documento/scripts/sonda/salidas/eficiencia_m1.csv",
                         "reformateo/documento/scripts/sonda/salidas/eficiencia_m3.csv",
                         "reformateo/documento/scripts/sonda/salidas/cotas_m1.csv",
                         "reformateo/documento/scripts/sonda/salidas/cotas_m3.csv"])

    print()
    for cob, d in datos.items():
        w = d["mejor"]
        print(f"  {cob.upper()}: mercado media {_n(d['ef_aco'].mean())} % · "
              f"ponderada {_n(np.average(d['ef_aco'], weights=w))} % · "
              f"ciego media {_n(d['ef_ciego'].mean())} % · "
              f"volumen {_n(d['efvol_aco'].mean())} %")
    print(f"  {ruta}")


if __name__ == "__main__":
    main()
