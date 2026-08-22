"""
gen_cap05.py — Figuras del capítulo 5: los precios.
====================================================
La energía medida es solo la mitad del dato. La otra mitad es su precio,
y de ella dependen todas las cifras del estudio: el mismo kilovatio-hora
vale distinto según quién lo compre, en qué mes y bajo qué mecanismo.

El capítulo reconstruye esa segunda mitad desde las fuentes primarias:
la serie horaria de bolsa, el techo regulatorio de escasez y las tarifas
mensuales transcritas de los PDF del comercializador.

    python scripts/gen_cap05.py
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

# Categoría tarifaria de cada institución (data/cedenar_tariff.py): las
# públicas pagan el costo unitario exacto; las privadas, con contribución.
CATEGORIA = {"Udenar": "oficial", "HUDN": "oficial",
             "Mariana": "comercial", "UCC": "comercial", "Cesmag": "comercial"}


def _nt2(categoria: str) -> pd.DataFrame:
    """Serie mensual del nivel de tensión 2, que es el de la comunidad."""
    t = D.tarifas_cedenar()
    t = t[(t["categoria"] == categoria) & (t["nivel_tension"] == 2)]
    return t.groupby("mes", as_index=False).first().sort_values("mes")


# ─────────────────────────────────────────────────────────────────────────────
def f51_bolsa():
    """
    F5.1 — La serie de bolsa.

    Precio horario del mercado mayorista sobre el horizonte del estudio.
    Se dibuja la serie horaria en gris y la media diaria encima, para que
    se vea a la vez la dispersión intradiaria y la tendencia.

    Es el precio al que se liquida el excedente que no encuentra
    comprador dentro de la comunidad, de modo que fija el suelo económico
    de todo el ejercicio.
    """
    b = D.precios_bolsa()          # ya recortada al horizonte canonico
    diaria = b.set_index("ts")["Precio_COP_kWh"].resample("1D").mean()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.2),
                                   gridspec_kw={"width_ratios": [1.7, 1]})
    ax1.plot(b["ts"], b["Precio_COP_kWh"], color=E.NEUTRO, linewidth=0.35,
             alpha=0.55, label="Horario")
    ax1.plot(diaria.index, diaria.values, color=E.MECANISMOS["C3"],
             linewidth=1.5, label="Media diaria")
    ax1.axhline(b["Precio_COP_kWh"].mean(), color=E.ALERTA, linestyle="--",
                linewidth=1.1,
                label=f"Media del horizonte: "
                      f"{E.fmt_miles(b['Precio_COP_kWh'].mean(), 1)}")
    ax1.set_ylabel("Precio de bolsa [COP/kWh]")
    ax1.set_title("Serie del mercado mayorista", pad=8)
    ax1.legend(fontsize=7, loc="upper right")
    ax1.tick_params(axis="x", labelrotation=25, labelsize=6.5)
    E.eje_espanol(ax1, "y", "miles")

    perfil = b.groupby(b["ts"].dt.hour)["Precio_COP_kWh"]
    med, q1, q3 = perfil.median(), perfil.quantile(0.25), perfil.quantile(0.75)
    ax2.fill_between(med.index, q1.values, q3.values,
                     color=E.MECANISMOS["C3"], alpha=0.25)
    ax2.plot(med.index, med.values, color=E.MECANISMOS["C3"], linewidth=1.7)
    ax2.set_xlabel("Hora del día")
    ax2.set_title("Patrón intradiario", pad=8)
    ax2.set_xticks(range(0, 24, 4))
    E.eje_espanol(ax2, "y", "miles")

    tabla = pd.DataFrame({"hora": med.index, "mediana": med.values,
                          "q1": q1.values, "q3": q3.values})
    fig.tight_layout()
    return E.guardar(fig, "f5_01_bolsa", datos=tabla,
                     procedencia=["data/precios_bolsa_xm_api.csv "
                                  "(cache de la API de XM, recortado a las "
                                  "6.144 h del horizonte canonico)"])


# ─────────────────────────────────────────────────────────────────────────────
def f53_cu_desglose():
    """
    F5.3 — De qué se compone la tarifa.

    Barras apiladas del costo unitario mes a mes, separando sus siete
    componentes regulatorias. Importa porque cada mecanismo del capítulo 8
    exime al usuario de componentes distintas: el mercado entre pares no
    paga las de red, el colectivo descuenta unas, el individual otras. Sin
    este desglose, esas diferencias no se pueden leer.

    Se dibuja el nivel de tensión 2, que es el de la comunidad, en su
    versión oficial. Las cifras salen del CSV transcrito de los PDF, no de
    valores fijados en el código.
    """
    comp = [("Gm", "Generación"), ("Tm", "Transmisión"),
            ("Dnm", "Distribución"), ("Cvm", "Comercialización"),
            ("PR", "Pérdidas"), ("Rm", "Restricciones"),
            ("COT", "Otros (COT)")]
    colores = ["#1F6F8B", "#5B8C5A", "#C1642A", "#9B6BA8",
               "#B0913B", "#8C8C8C", "#D8D2C4"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.6),
                                   gridspec_kw={"width_ratios": [1.6, 1]})
    t = _nt2("oficial")
    x = np.arange(len(t))
    base = np.zeros(len(t))
    for (col, nom), c in zip(comp, colores):
        ax1.bar(x, t[col].values, 0.72, bottom=base, color=c, label=nom)
        base += t[col].values
    ax1.plot(x, t["CU_aplicado"].values, color="black", linewidth=1.4,
             marker="o", markersize=3, label="Costo unitario")
    ax1.set_xticks(x)
    ax1.set_xticklabels([m[5:] + "/" + m[2:4] for m in t["mes"]], fontsize=6.5,
                        rotation=45)
    ax1.set_ylabel("COP/kWh")
    ax1.set_title("Composición del costo unitario (nivel 2, oficial)", pad=8)
    ax1.legend(fontsize=6.3, ncol=4, loc="upper center")
    ax1.set_ylim(0, t["CU_aplicado"].max() * 1.42)
    E.eje_espanol(ax1, "y", "miles")

    # Panel derecho: reparto medio de las componentes.
    medias = [t[c].mean() for c, _ in comp]
    total = sum(medias)
    y = np.arange(len(comp))
    ax2.barh(y, medias, 0.64, color=colores)
    ax2.set_yticks(y)
    ax2.set_yticklabels([n for _, n in comp], fontsize=7)
    ax2.invert_yaxis()
    for j, v in enumerate(medias):
        ax2.text(v + total * 0.012, j,
                 f"{E.fmt_miles(v, 0)}  ({E.fmt_miles(100 * v / total, 0)} %)",
                 va="center", fontsize=6.8)
    ax2.set_xlim(0, max(medias) * 1.65)
    ax2.set_xlabel("Media del horizonte [COP/kWh]")
    ax2.set_title("Peso de cada componente", pad=8)
    E.eje_espanol(ax2, "x", "miles")

    fig.tight_layout()
    return E.guardar(fig, "f5_03_cu_desglose", datos=t,
                     procedencia=["data/tarifas_cedenar_mensual.csv "
                                  "(transcrito de data/cedenar_pdfs/*.pdf)"])


# ─────────────────────────────────────────────────────────────────────────────
def f54_oficial_comercial():
    """
    F5.4 — Dos tarifas para la misma comunidad.

    Las instituciones públicas pagan el costo unitario exacto; las
    privadas, el mismo costo con la contribución del veinte por ciento.
    Sobre el mismo campus y el mismo mes, el kilovatio-hora vale distinto
    según quién lo consuma.

    Es la razón de que la liquidación use una matriz de precios por agente
    y por mes, y no un único número para toda la comunidad.
    """
    ofi, com = _nt2("oficial"), _nt2("comercial")
    fig, ax = E.figura(alto=3.2)
    x = np.arange(len(ofi))
    ax.plot(x, ofi["CU_aplicado"], marker="o", markersize=3.4,
            color=E.MECANISMOS["P2P"], linewidth=1.6,
            label="Oficial — Udenar y HUDN")
    ax.plot(x, com["CU_aplicado"], marker="s", markersize=3.4,
            color=E.ALERTA, linewidth=1.6,
            label="Comercial — Mariana, UCC y Cesmag")
    ax.fill_between(x, ofi["CU_aplicado"], com["CU_aplicado"],
                    color=E.ALERTA, alpha=0.12)
    ax.set_xticks(x)
    ax.set_xticklabels([m[5:] + "/" + m[2:4] for m in ofi["mes"]],
                       fontsize=6.5, rotation=45)
    ax.set_ylabel("Costo unitario [COP/kWh]")
    ax.set_title("La misma comunidad, dos categorías tarifarias", pad=8)
    ax.legend(fontsize=7.5, loc="lower right")
    E.eje_espanol(ax, "y", "miles")

    brecha = (com["CU_aplicado"].to_numpy() - ofi["CU_aplicado"].to_numpy())
    ax.text(0.03, 0.94,
            f"diferencia media: {E.fmt_miles(brecha.mean(), 1)} COP/kWh "
            f"({E.fmt_miles(100 * brecha.mean() / ofi['CU_aplicado'].mean(), 1)} %)",
            transform=ax.transAxes, va="top", fontsize=7.5)

    tabla = pd.DataFrame({"mes": ofi["mes"].values,
                          "CU_oficial": ofi["CU_aplicado"].values,
                          "CU_comercial": com["CU_aplicado"].values,
                          "brecha": brecha})
    fig.tight_layout()
    return E.guardar(fig, "f5_04_oficial_comercial", datos=tabla,
                     procedencia=["data/tarifas_cedenar_mensual.csv"])


# ─────────────────────────────────────────────────────────────────────────────
def f57_banda():
    """
    F5.7 — La banda dentro de la que se mueve el precio del mercado.

    Un intercambio entre pares solo interesa a las dos partes si el precio
    queda por encima de lo que el vendedor obtendría inyectando a la red y
    por debajo de lo que el comprador pagaría comprándola. Esa doble
    condición define una banda, y todo el juego del capítulo 6 ocurre
    dentro de ella.

    Los extremos se calculan de las series reales: el piso, del precio de
    bolsa; el techo, de las dos categorías tarifarias.
    """
    b = D.precios_bolsa()["Precio_COP_kWh"]   # horizonte canonico
    ofi, com = _nt2("oficial"), _nt2("comercial")

    fig, ax = E.figura(alto=3.0)
    niveles = [
        ("Bolsa (media)", float(b.mean()), E.MECANISMOS["C3"]),
        ("Bolsa (mediana)", float(b.median()), E.MECANISMOS["C3"]),
        ("Tarifa oficial", float(ofi["CU_aplicado"].mean()), E.MECANISMOS["P2P"]),
        ("Tarifa comercial", float(com["CU_aplicado"].mean()), E.ALERTA),
    ]
    piso = min(n[1] for n in niveles[:2])
    techo = max(n[1] for n in niveles[2:])
    ax.axhspan(piso, techo, color=E.MECANISMOS["P2P"], alpha=0.10)
    ax.text(0.5, (piso + techo) / 2,
            "banda de ganancia mutua\nel precio de equilibrio vive aquí",
            ha="center", va="center", fontsize=8.5, style="italic",
            color=E.MECANISMOS["P2P"])

    for j, (nom, v, c) in enumerate(niveles):
        ax.axhline(v, color=c, linewidth=1.5,
                   linestyle="-" if j in (0, 2, 3) else ":")
        ax.text(0.985, v, f" {nom}: {E.fmt_miles(v, 0)} ", color=c,
                fontsize=7.5, va="bottom", ha="right",
                transform=ax.get_yaxis_transform())

    ax.set_xlim(0, 1)
    ax.set_xticks([])
    ax.set_ylim(0, techo * 1.15)
    ax.set_ylabel("COP/kWh")
    ax.set_title("Piso y techo del precio entre pares", pad=8)
    E.eje_espanol(ax, "y", "miles")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return E.guardar(fig, "f5_07_banda",
                     datos=pd.DataFrame(
                         [{"nivel": n, "valor_COP_kWh": v} for n, v, _ in niveles]),
                     procedencia=["data/precios_bolsa_xm_api.csv",
                                  "data/tarifas_cedenar_mensual.csv"])


if __name__ == "__main__":
    D.verificar_canon()
    print("\nCapítulo 5 — los precios")
    f51_bolsa()
    f53_cu_desglose()
    f54_oficial_comercial()
    f57_banda()
    print("\nlisto.")
