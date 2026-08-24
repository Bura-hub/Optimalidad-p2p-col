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


def _nt2(categoria: str, solo_horizonte: bool = True) -> pd.DataFrame:
    """
    Serie mensual del nivel de tensión 2, que es el de la comunidad.

    Se recorta al horizonte del estudio (2025-04 .. 2025-12) por la misma
    razón por la que ``datos.precios_bolsa`` recorta la serie de bolsa: el
    CSV transcrito llega hasta abril de 2026, cuatro meses **fuera** de las
    6.144 h simuladas. Sin el recorte, un promedio rotulado «media del
    horizonte» no era la media del horizonte (792,06 en vez de 795,68
    COP/kWh en la categoría oficial) y esa cifra se propagaba a la banda de
    precios de F5.7.
    """
    t = D.tarifas_cedenar()
    t = t[(t["categoria"] == categoria) & (t["nivel_tension"] == 2)]
    if solo_horizonte:
        t = t[(t["mes"] >= D.T_START[:7]) & (t["mes"] <= D.T_END[:7])]
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
    media = float(b["Precio_COP_kWh"].mean())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.2),
                                   gridspec_kw={"width_ratios": [1.7, 1]})
    ax1.plot(b["ts"], b["Precio_COP_kWh"], color=E.NEUTRO, linewidth=0.35,
             alpha=0.55, label="Precio horario")
    ax1.plot(diaria.index, diaria.values, color=E.MECANISMOS["C3"],
             linewidth=1.5, label="Media diaria")
    ax1.axhline(media, color=E.ALERTA, linestyle="--", linewidth=1.1,
                label=f"Media: {E.fmt_miles(media, 1)} COP/kWh")
    ax1.set_ylabel("Precio de bolsa (COP/kWh)")
    ax1.set_xlabel("Fecha")
    ax1.set_title("Serie del mercado mayorista", pad=8)
    # La leyenda iba «upper right», justo encima de los dos maximos de la
    # serie (2.224 y 2.218 COP/kWh, 15 y 30 de agosto): tapaba el dato mas
    # llamativo de la figura. Arriba a la izquierda no hay nada que tapar,
    # porque abril y mayo se mueven por debajo de 1.000 COP/kWh.
    ax1.legend(fontsize=7, loc="upper left")
    ax1.tick_params(axis="x", labelrotation=25, labelsize=6.5)
    E.eje_espanol(ax1, "y", "miles")

    # Los dos maximos de la serie son horas sueltas: con 6.144 puntos en
    # 4 pulgadas, su trazo mide menos de un pixel y se perdian, de modo que
    # el eje llegaba a 2.200 sin que se viera por que. Se marcan con punto.
    picos = b.nlargest(2, "Precio_COP_kWh")
    ax1.plot(picos["ts"], picos["Precio_COP_kWh"], linestyle="none",
             marker="o", markersize=3.2, markerfacecolor="none",
             markeredgecolor=E.NEUTRO, markeredgewidth=0.9, zorder=5)
    # Ojo con el rotulo: estas dos horas NO tocan el precio de escasez. El
    # de agosto de 2025 fue 898 COP/kWh (data/precios_escasez_creg.csv), de
    # modo que el maximo de bolsa lo dobla largamente. Se rotulan como lo
    # que son, los dos maximos de la serie, sin atribuirles causa.
    cima, seg = picos.iloc[0], picos.iloc[1]
    ax1.annotate(f"los dos máximos del horizonte:\n"
                 f"{E.fmt_miles(cima['Precio_COP_kWh'], 0)} y "
                 f"{E.fmt_miles(seg['Precio_COP_kWh'], 0)} COP/kWh",
                 xy=(cima["ts"], cima["Precio_COP_kWh"]),
                 xytext=(0.99, 0.80), textcoords="axes fraction",
                 fontsize=6.6, color=E.NEUTRO, ha="right", va="top",
                 arrowprops=dict(arrowstyle="->", color=E.NEUTRO, lw=0.7,
                                 shrinkB=3))

    perfil = b.groupby(b["ts"].dt.hour)["Precio_COP_kWh"]
    med, q1, q3 = perfil.median(), perfil.quantile(0.25), perfil.quantile(0.75)
    ax2.fill_between(med.index, q1.values, q3.values,
                     color=E.MECANISMOS["C3"], alpha=0.25,
                     label="Rango intercuartílico")
    ax2.plot(med.index, med.values, color=E.MECANISMOS["C3"], linewidth=1.7,
             label="Mediana horaria")
    ax2.set_xlabel("Hora del día")
    ax2.set_ylabel("Precio de bolsa (COP/kWh)")
    ax2.set_title("Patrón intradiario", pad=8)
    ax2.set_xticks(range(0, 24, 4))
    ax2.set_xlim(0, 23)
    ax2.legend(fontsize=6.6, loc="upper left")
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
    versión oficial, y **solo los nueve meses del horizonte**: el CSV
    transcrito llega hasta abril de 2026 y esos cuatro meses de más no
    pertenecen al estudio. Las cifras salen del CSV transcrito de los PDF,
    no de valores fijados en el código.
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
    ax1.set_xticklabels([m[5:] + "/" + m[2:4] for m in t["mes"]], fontsize=7,
                        rotation=45)
    ax1.set_ylabel("Costo unitario (COP/kWh)")
    ax1.set_xlabel("Mes de facturación")
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
    ax2.set_xlim(0, max(medias) * 1.72)
    ax2.set_xlabel("Aporte medio al costo\nunitario (COP/kWh)")
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
    # CESMAG va en mayusculas: es sigla. Se toma de E.etiqueta_institucion
    # y no se escribe a mano, para que el rotulo no vuelva a divergir.
    privadas = (", ".join(E.etiqueta_institucion(i)
                          for i in ("Mariana", "UCC"))
                + " y " + E.etiqueta_institucion("Cesmag"))
    ax.plot(x, com["CU_aplicado"], marker="s", markersize=3.4,
            color=E.ALERTA, linewidth=1.6,
            label=f"Comercial — {privadas}")
    ax.fill_between(x, ofi["CU_aplicado"], com["CU_aplicado"],
                    color=E.ALERTA, alpha=0.12)
    ax.set_xticks(x)
    ax.set_xticklabels([m[5:] + "/" + m[2:4] for m in ofi["mes"]],
                       fontsize=7, rotation=45)
    ax.set_ylabel("Costo unitario (COP/kWh)")
    ax.set_xlabel("Mes de facturación")
    ax.set_title("La misma comunidad, dos categorías tarifarias", pad=8)
    # La leyenda estaba «lower right», encima de las dos curvas en los
    # ultimos meses. El centro de la figura es la franja vacia entre ellas.
    ax.legend(fontsize=7.5, loc="center left", bbox_to_anchor=(0.02, 0.52))
    E.eje_espanol(ax, "y", "miles")
    ax.set_xlim(-0.4, len(x) - 0.6)

    brecha = (com["CU_aplicado"].to_numpy() - ofi["CU_aplicado"].to_numpy())
    ax.text(0.98, 0.47,
            f"diferencia media: {E.fmt_miles(brecha.mean(), 1)} COP/kWh "
            f"({E.fmt_miles(100 * brecha.mean() / ofi['CU_aplicado'].mean(), 1)} %)"
            "\n— la contribución de ley del 20 %",
            transform=ax.transAxes, va="center", ha="right", fontsize=7.5)

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
    por debajo de lo que el comprador pagaría comprándola a su
    comercializador. Esa doble condición define una banda, y todo el juego
    del capítulo 6 ocurre dentro de ella.

    El techo **no es único**: depende de la categoría tarifaria del
    comprador. Un precio entre la tarifa oficial y la comercial deja de
    convenirle a Udenar y al HUDN, que son las dos oficiales, y solo sigue
    conviniéndole a las tres privadas. La liquidación recoge exactamente
    eso con un tope por agente (CAL-35: pi_eff = min(pi*, pi_gs[i,k])).

    La versión anterior de esta figura sombreaba de un solo color desde la
    **mediana** de bolsa hasta la tarifa **comercial** y rotulaba todo el
    tramo «el precio de equilibrio vive aquí». Eso era la unión de las
    bandas, no la banda: afirmaba ganancia mutua en 159 COP/kWh en los que
    dos de los cinco agentes ya perderían. Aquí se separan los dos tramos.
    """
    b = D.precios_bolsa()["Precio_COP_kWh"]   # horizonte canonico
    ofi, com = _nt2("oficial"), _nt2("comercial")

    piso_media = float(b.mean())
    piso_mediana = float(b.median())
    techo_ofi = float(ofi["CU_aplicado"].mean())
    techo_com = float(com["CU_aplicado"].mean())

    fig, ax = E.figura(alto=3.2)

    # Tramo comun a cualquier par: por encima del precio de bolsa y por
    # debajo del techo mas bajo de los dos, que es el oficial.
    ax.axhspan(piso_media, techo_ofi, color=E.MECANISMOS["P2P"], alpha=0.13)
    # Tramo que solo le sirve al par cuyo comprador es privado.
    ax.axhspan(techo_ofi, techo_com, color=E.ALERTA, alpha=0.11)

    niveles = [
        ("Bolsa, mediana horaria", piso_mediana, E.MECANISMOS["C3"], ":"),
        ("Bolsa, media del horizonte", piso_media, E.MECANISMOS["C3"], "-"),
        ("Tarifa oficial (Udenar, HUDN)", techo_ofi, E.MECANISMOS["P2P"], "-"),
        ("Tarifa comercial (Mariana, UCC, CESMAG)", techo_com, E.ALERTA, "-"),
    ]
    for nom, v, c, ls in niveles:
        ax.axhline(v, color=c, linewidth=1.5, linestyle=ls)
        ax.text(0.985, v + 8, f"{nom}: {E.fmt_miles(v, 0)}", color=c,
                fontsize=7.2, va="bottom", ha="right",
                transform=ax.get_yaxis_transform())

    ax.text(0.035, (piso_media + techo_ofi) / 2,
            "banda de ganancia mutua\n"
            "vale para cualquier par de la comunidad\n"
            f"(ancho: {E.fmt_miles(techo_ofi - piso_media, 0)} COP/kWh)",
            ha="left", va="center", fontsize=8, style="italic",
            color=E.MECANISMOS["P2P"], transform=ax.get_yaxis_transform())
    ax.text(0.035, (techo_ofi + techo_com) / 2,
            "aquí solo gana el par cuyo comprador es privado",
            ha="left", va="center", fontsize=7.2, style="italic",
            color=E.ALERTA, transform=ax.get_yaxis_transform())
    ax.text(0.035, piso_media / 2,
            "por debajo del precio de bolsa el vendedor prefiere la red",
            ha="left", va="center", fontsize=7.2, style="italic",
            color=E.NEUTRO, transform=ax.get_yaxis_transform())

    ax.set_xlim(0, 1)
    ax.set_xticks([])
    ax.set_ylim(0, techo_com * 1.13)
    ax.set_ylabel("Precio de la energía (COP/kWh)")
    ax.set_title("Piso y techo del precio entre pares", pad=8)
    E.eje_espanol(ax, "y", "miles")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return E.guardar(fig, "f5_07_banda",
                     datos=pd.DataFrame(
                         [{"nivel": n, "valor_COP_kWh": v}
                          for n, v, _, _ in niveles]
                         + [{"nivel": "ancho de la banda comun",
                             "valor_COP_kWh": techo_ofi - piso_media}]),
                     procedencia=["data/precios_bolsa_xm_api.csv",
                                  "data/tarifas_cedenar_mensual.csv "
                                  "(meses del horizonte, 2025-04 a 2025-12)"])


if __name__ == "__main__":
    D.verificar_canon()
    print("\nCapítulo 5 — los precios")
    f51_bolsa()
    f53_cu_desglose()
    f54_oficial_comercial()
    f57_banda()
    print("\nlisto.")
