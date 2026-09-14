# -*- coding: utf-8 -*-
"""Grupo F · las figuras del rediseño de la ponencia (2026-09-09).

QUE ENTRA Y POR QUE. El autor reordeno la charla: fuera las dos fronteras de
medicion, fuera el desglose del costo unitario, fuera el colectivo horario, y
el modelo base deja de presentarse con ecuaciones. En su lugar hacen falta
cuatro piezas que el aparato no producia:

  f1  las curvas de generacion y demanda, y QUIEN vende y quien compra en cada
      hora, que es lo que sostiene que el papel no es fijo
  f2  el diagrama de flujo del ejercicio, que sustituye a las ecuaciones
  f3  un dia liquidado al detalle: quien vende a quien, cuanta energia y a que
      precio
  f4  los dos tramos de la autogeneracion individual, que la charla nombra y
      nunca habia dibujado. SALIO DE LA PONENCIA (C-175): dibujaba el disparo
      horario que la norma no aplica. La funcion sigue definida, solo como
      registro, y `main()` ya no la invoca

Todas leen del almacen de la corrida oficial y ninguna vuelve a simular.
Ninguna lleva pie de nota: la lamina ya trae el suyo.
"""
import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estilo as E  # noqa: E402


def _lee(destino, cobertura, tabla):
    from core.almacen import lee
    return lee(destino, cobertura, tabla)


# ══════════════════════════════════════════════════════════════════════════
#  f1 · Las curvas, y quien es quien
# ══════════════════════════════════════════════════════════════════════════

def f1_curvas(destino, cobertura: str, dia: str):
    """El balance neto de cada institucion, hora a hora. UN SOLO PANEL.

    LA PRIMERA VERSION NO SE ENTENDIA, y el defecto era de diseno, no de
    ejecucion. Tenia dos paneles que no se hablaban: arriba dos curvas
    agregadas con un area sombreada que NO era el hueco entre ellas sino otra
    magnitud sobre el mismo eje, y abajo una rejilla de papeles sin relacion
    visible con lo de arriba. Ademas el naranja y el azul significaban dos
    cosas distintas en la misma figura.

    ESTA VERSION DICE LO MISMO CON UNA SOLA IDEA GRAFICA. Cada barra es una
    hora. Hacia arriba, lo que le SOBRA a cada institucion; hacia abajo, lo que
    le FALTA. Mismo color para la misma institucion en los dos sentidos, de
    modo que **se ve a la misma barra cambiar de lado**, que es justo lo que
    hay que decir.

    Y EL LADO CORTO SE VE SOLO: la energia que se transa es la menor de las
    dos pilas, y va marcada. No hay que explicarlo, se mira.
    """
    ag = _lee(destino, cobertura, "agentes")
    ag = ag[ag["fecha"].dt.date.astype(str) == dia]
    if ag.empty:
        return None

    orden = [n for n in E.ORDEN_INSTITUCIONES if n in set(ag["agente"])]
    horas = sorted(ag["hora_del_dia"].unique())
    x = np.arange(len(horas))

    def por(col, inst):
        s = ag[ag["agente"] == inst].set_index("hora_del_dia")[col]
        return s.reindex(horas, fill_value=0.0).values

    fig, ax = E.figura(alto=3.9)

    arriba = np.zeros(len(horas))
    abajo = np.zeros(len(horas))
    for n in orden:
        so, fa = por("sobrante", n), por("faltante", n)
        c = E.color_institucion(n)
        ax.bar(x, so, 0.74, bottom=arriba, color=c, edgecolor="white",
               linewidth=0.7, label=E.etiqueta_institucion(n))
        ax.bar(x, -fa, 0.74, bottom=abajo, color=c, edgecolor="white",
               linewidth=0.7, alpha=0.55)
        arriba += so
        abajo -= fa

    # La energia que de verdad se transa: la menor de las dos pilas.
    transable = np.minimum(arriba, -abajo)
    hay = transable > 1e-6
    ax.plot(x[hay], transable[hay], marker="o", markersize=5.5, linewidth=2.0,
            color="#1F2332", zorder=6, label="lo que se puede transar")

    ax.axhline(0, color="#1F2332", linewidth=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{k:02d}" for k in horas], fontsize=8)
    ax.set_xlabel("Hora del día")
    # UN SOLO ROTULO DE MAGNITUD. La version anterior puso «Le sobra» y «Le
    # falta» dentro de la misma cadena, y matplotlib la centra: los dos
    # terminos salieron cambiados de sitio. El sentido lo dicen las dos
    # palabras verticales, que van pegadas al eje y no se pueden invertir.
    # EN ENERGIA, no en potencia. El paso es horario, de modo que el
    # numero es el mismo; se rotula como energia porque es lo que se
    # liquida y porque asi lo hacen las demas laminas del mazo.
    ax.set_ylabel("Energía (kWh)")
    ax.set_title("Quién vende y quién compra lo decide la hora, "
                 "no la institución", pad=8)
    # LA LEYENDA VA FUERA DEL AREA DE DIBUJO. Dentro no cabe: arriba a la
    # izquierda parece haber sitio, pero al ocupar tres columnas se cruza con
    # las barras de venta del mediodia. Debajo del eje no estorba a nada.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=6,
              fontsize=8.0, frameon=False, handlelength=1.6,
              columnspacing=1.4)

    lim = ax.get_ylim()
    ax.text(-1.15, lim[1] * 0.42, "VENDE", rotation=90, va="center",
            ha="center", fontsize=9.0, color=E.NEUTRO, fontweight="bold")
    ax.text(-1.15, lim[0] * 0.45, "COMPRA", rotation=90, va="center",
            ha="center", fontsize=9.0, color=E.NEUTRO, fontweight="bold")

    datos = pd.DataFrame({"hora": horas, "sobra_total": arriba,
                          "falta_total": -abajo, "transable": transable})
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    return E.guardar(fig, f"foro_f1_curvas_{cobertura}", datos=datos,
                     procedencia=[f"{destino}/{cobertura}/agentes"])


# ══════════════════════════════════════════════════════════════════════════
#  f2 · El diagrama de flujo, que sustituye a las ecuaciones
# ══════════════════════════════════════════════════════════════════════════

def f2_flujo(destino, cobertura: str):
    """El ejercicio entero en un flujo, sin una sola ecuacion.

    SUSTITUYE A LA LAMINA DE ECUACIONES. Lo que la sala necesita saber no es
    como se deriva la aptitud, sino que hay un dato medido, que de el sale
    quien vende y quien compra, que el precio se busca DENTRO de dos cotas, y
    que el resultado se compara contra dos figuras que ya existen en la norma.

    LAS DOS COTAS LLEVAN CAJA PROPIA Y COLOR, porque son la pieza que el modelo
    base deja sin definir y todo lo demas de la charla existe para ponerles
    valor.

    LA REJILLA SE FIJA EN UNA TABLA Y NO A OJO. La primera version puso las
    coordenadas a mano y dos cajas se solaparon: los titulos se pisaban y no se
    veia hasta renderizar. Aqui las filas y las columnas se calculan.
    """
    # ANCHO DE LAMINA, no de columna: esta figura se proyecta. Con el
    # ancho del documento se quedaba en poco mas de la mitad de la
    # lamina y el aire sobrante la hacia ver pequena.
    fig, ax = plt.subplots(figsize=(E.ANCHO_LAMINA, 4.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    VERDE = "#056734"
    # Tres columnas iguales con canal entre ellas, y tres filas.
    CAN, MAR = 4.0, 1.0
    AN3 = (100 - 2 * MAR - 2 * CAN) / 3          # ancho de columna en la reja de tres
    AN2 = (100 - 2 * MAR - CAN) / 2              # ancho en la reja de dos
    COL3 = [MAR + i * (AN3 + CAN) for i in range(3)]
    COL2 = [MAR + i * (AN2 + CAN) for i in range(2)]
    F1, F2, F3 = 44.0, 22.0, 1.5                 # base de cada fila
    AL1, AL2, AL3 = 15.0, 15.0, 13.0

    def caja(x, y, an, al, titulo, cuerpo="", color=E.APOYO, texto="#1F2332",
             borde=None):
        ax.add_patch(FancyBboxPatch(
            (x, y), an, al, boxstyle="round,pad=0.5,rounding_size=1.1",
            facecolor=color, edgecolor=borde or color, linewidth=1.5))
        ax.text(x + an / 2, y + al - 2.4, titulo, ha="center", va="top",
                fontsize=9.0, fontweight="bold", color=texto)
        if cuerpo:
            ax.text(x + an / 2, y + al - 6.0, cuerpo, ha="center", va="top",
                    fontsize=7.6, color=texto, linespacing=1.4)

    def flecha(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                     mutation_scale=13, linewidth=1.5,
                                     color=E.NEUTRO, shrinkA=1, shrinkB=1))

    # ── Fila 1 · de la medida al balance ────────────────────────────────
    caja(COL3[0], F1, AN3, AL1, "1 · Lo que se mide",
         "Generación y demanda\nde cada institución,\nhora a hora")
    caja(COL3[1], F1, AN3, AL1, "2 · El balance de la hora",
         "¿genera más de lo que\nconsume? vende.\nSi no, compra")
    caja(COL3[2], F1, AN3, AL1, "3 · Cuánta energía hay",
         "La fija el lado corto: el\nmenor entre lo que sobra\ny lo que falta")
    for i in (0, 1):
        flecha(COL3[i] + AN3, F1 + AL1 / 2, COL3[i + 1], F1 + AL1 / 2)

    # ── Fila 2 · las cotas y el mercado ─────────────────────────────────
    caja(COL2[1], F2, AN2, AL2, "4 · Las dos cotas",
         "$\\pi_{gb}$, lo que la red le paga al que vende\n"
         "$\\pi_{gs}$, lo que la red le cobra al que compra\n"
         "El precio acordado cae entre las dos",
         color="#E6F0E8", borde=VERDE, texto="#0B3D24")
    caja(COL2[0], F2, AN2, AL2, "5 · El mercado entre pares",
         "Maximiza la actividad conjunta de\nvendedores y compradores\n"
         "fijando el precio dentro de la banda",
         color=E.DESPUES, texto="white")
    flecha(COL3[2] + AN3 / 2, F1, COL3[2] + AN3 / 2, F2 + AL2)
    flecha(COL2[1], F2 + AL2 / 2, COL2[0] + AN2, F2 + AL2 / 2)

    # ── Fila 3 · contra qué se compara, y qué se responde ───────────────
    ax.text(COL3[0], F3 + AL3 + 1.6, "6 · Y se compara, hora a hora, contra:",
            fontsize=9.0, fontweight="bold", color="#1F2332", ha="left")
    caja(COL3[0], F3, AN3, AL3, "Autogeneración individual",
         "CREG 174\nexcedentes tipo 1 y tipo 2")
    caja(COL3[1], F3, AN3, AL3, "Colectivo mensual",
         "CREG 101 072\nreparto por porcentaje")
    caja(COL3[2], F3, AN3, AL3, "7 · La respuesta",
         "¿a quién le conviene qué,\ny cuánto le cuesta\nelegir mal?",
         color=E.APOYO)
    flecha(COL2[0] + AN2 / 4, F2, COL3[0] + AN3 / 2, F3 + AL3)
    flecha(COL2[0] + AN2 / 2, F2, COL3[1] + AN3 / 2, F3 + AL3)
    flecha(COL3[1] + AN3, F3 + AL3 / 2, COL3[2], F3 + AL3 / 2)

    fig.tight_layout(pad=0.4)
    return E.guardar(fig, f"foro_f2_flujo_{cobertura}",
                     procedencia=["diagrama; no lee datos"])


# ══════════════════════════════════════════════════════════════════════════
#  f3 · El dia liquidado al detalle
# ══════════════════════════════════════════════════════════════════════════

def f3_dia_detalle(destino, cobertura: str, dia: str):
    """Quien vende a quien, cuanta energia y a que precio, hora por hora.

    ES LA LAMINA QUE CONVIERTE EL MECANISMO EN ALGO CONCRETO. Las demas dicen
    cuanto se ahorra; esta dice quien le vendio a quien.

    SE COLOREA POR COMPRADOR, no por vendedor. La primera version lo hizo al
    reves y salio una figura de un solo color, porque en esta comunidad
    practicamente solo vende una institucion. La dimension que informa es a
    QUIEN le vendio.

    EL PANEL DE ABAJO LLEVA LOS PRECIOS con la banda de fondo, y ahi se ve lo
    que distingue a este mecanismo de un precio unico: **en la misma hora, el
    mismo vendedor coloca con dos compradores a precios distintos.**
    """
    fl = _lee(destino, cobertura, "flujos")
    fl = fl[fl["fecha"].dt.date.astype(str) == dia]
    if fl.empty:
        return None

    # EL POLVO NUMERICO NO SE DIBUJA. La dinamica de replicador arranca con
    # energia en TODAS las parejas y nunca lleva ninguna exactamente a cero,
    # de modo que quedan parejas con centesimas de kilovatio hora que no son
    # tratos. El almacen las conserva a proposito, porque perderlas seria
    # perder informacion; la figura no las pinta, porque presentarlas como
    # ventas hacia que el titulo nombrara tres vendedores donde solo hay uno.
    UMBRAL = 0.01           # (kWh) en la hora
    fl = fl[fl["kwh"] >= UMBRAL]
    if fl.empty:
        return None

    horas = sorted(fl["hora_del_dia"].unique())
    compradores = [n for n in E.ORDEN_INSTITUCIONES
                   if n in set(fl["comprador"])]

    fig, (ax, ax2) = plt.subplots(
        2, 1, figsize=(E.ANCHO_LAMINA, 4.4), sharex=True,
        gridspec_kw={"height_ratios": [1.35, 1.0], "hspace": 0.16})

    # ── arriba: la energia, apilada por comprador ───────────────────────
    base = np.zeros(len(horas))
    for c in compradores:
        alt = np.array([float(fl[(fl["hora_del_dia"] == k) &
                                 (fl["comprador"] == c)]["kwh"].sum())
                        for k in horas])
        ax.bar(range(len(horas)), alt, 0.70, bottom=base,
               color=E.color_institucion(c), edgecolor="white", linewidth=1.0,
               label=f"le compra {E.etiqueta_institucion(c)}")
        base += alt
    ax.set_ylabel("Energía (kWh)")
    ax.legend(loc="upper left", fontsize=7.8, ncol=2, framealpha=0.92)
    pesos = fl.groupby("vendedor")["kwh"].sum().sort_values(ascending=False)
    vend = ", ".join(E.etiqueta_institucion(v) for v in pesos.index)
    ax.set_title(f"Un día liquidado · {dia} · vende {vend}", pad=8)

    # UNA HORA PUEDE TRANSAR TAN POCO QUE SU BARRA NO SE VEA, y entonces
    # aparece su precio abajo sin nada arriba, que se lee como un error. Se
    # rotula el total de esas horas: la geometria no puede decirlo y el rotulo
    # si.
    tot = fl.groupby("hora_del_dia")["kwh"].sum()
    for i, h in enumerate(horas):
        v = float(tot.get(h, 0.0))
        if 0 < v < 0.03 * float(tot.max()):
            ax.text(i, v + 0.10, f"{E.fmt_miles(v, 2)} kWh", ha="center",
                    va="bottom", fontsize=7.4, color=E.NEUTRO, style="italic")

    # ── abajo: el precio de cada trato, dentro de la banda ──────────────
    te = float(fl["techo_comprador"].max())
    pi_ = float(fl["piso_vendedor"].min())
    ax2.axhspan(pi_, te, color=E.APOYO, alpha=0.45)
    ax2.axhline(te, color=E.NEUTRO, linewidth=1.4, linestyle="--")
    ax2.axhline(pi_, color=E.NEUTRO, linewidth=1.4, linestyle="--")
    for val, rot in ((te, "techo: lo que le cobra la red"),
                     (pi_, "piso: lo que la red le paga")):
        ax2.text(-0.35, val, rot, va="bottom", ha="left", fontsize=7.6,
                 color=E.NEUTRO, style="italic")
    for x, k in enumerate(horas):
        sub = fl[fl["hora_del_dia"] == k]
        for _, r in sub.iterrows():
            ax2.plot(x, float(r["precio"]), marker="o", markersize=7,
                     color=E.color_institucion(r["comprador"]),
                     markeredgecolor="white", markeredgewidth=0.9, zorder=3)
    ax2.set_xticks(range(len(horas)))
    ax2.set_xticklabels([f"{k:02d}" for k in horas])
    ax2.set_xlabel("Hora del día")
    ax2.set_ylabel("Precio (COP/kWh)")
    E.eje_espanol(ax2, "y", "miles", 0)

    fig.tight_layout()
    datos = fl[["hora_del_dia", "vendedor", "comprador", "kwh", "precio",
                "valor", "techo_comprador", "piso_vendedor"]].sort_values(
                    ["hora_del_dia", "vendedor", "comprador"])
    return E.guardar(fig, f"foro_f3_dia_{cobertura}", datos=datos,
                     procedencia=[f"{destino}/{cobertura}/flujos"])


# ══════════════════════════════════════════════════════════════════════════
#  f4 · Los dos tramos de la autogeneracion individual
# ══════════════════════════════════════════════════════════════════════════

def f4_tramos(destino, cobertura: str, agente: str = "Udenar",
              mes: str = "2025-06"):
    """El credito de energia, y donde se agota. UNA SOLA CURVA.

    RETIRADA DE LA PONENCIA (C-175): dibuja el disparo horario que la norma
    no aplica. Se conserva solo como registro.

    LA VERSION ANTERIOR PEDIA DEMASIADO AL OJO. Dibujaba dos curvas
    acumuladas y obligaba a juzgar cual iba por encima, en una figura donde la
    diferencia que decide vale dos kilovatios hora sobre un eje que llega a
    tres mil. Ademas rotulaba el tramo 1 en el panel del mes, donde ese tramo
    mide trece horas de setecientas veinte y no se ve.

    AQUI SE DIBUJA LA DIFERENCIA, que es literalmente el criterio de la norma:
    el credito se agota **cuando la inyeccion acumulada pasa por encima del
    retiro acumulado**, es decir cuando esta curva cruza el cero. Una linea y
    una referencia, y la condicion se mira en vez de deducirse.

    DOS PANELES PORQUE LA ESCALA LO EXIGE. El cruce vale +2 (kWh) y el mes
    termina en −2.170: en un solo eje el cruce es invisible. El de la derecha
    amplia el primer dia, que es donde ocurre.
    """
    ag = _lee(destino, cobertura, "agentes")
    a = ag[(ag["agente"] == agente) & (ag["mes"] == mes)].sort_values("hora")
    if a.empty:
        return None
    iny = a["sobrante"].cumsum().values
    ret = a["faltante"].cumsum().values
    dif = iny - ret                      # >0 significa credito agotado
    t = np.arange(len(dif))
    cruza = int(np.argmax(dif > 0)) if (dif > 0).any() else None

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(E.ANCHO_LAMINA, 3.6),
        gridspec_kw={"width_ratios": [1.9, 1.0], "wspace": 0.24})

    for eje, hasta, tit in ((ax, len(t), f"El mes entero · {mes}"),
                            (ax2, min(30, len(t)), "El primer día, ampliado")):
        tt, dd = t[:hasta], dif[:hasta]
        eje.axhspan(0, max(dd.max(), 1) * 1.6, color=E.ALERTA, alpha=0.10)
        eje.plot(tt, dd, linewidth=2.4, color=E.DESPUES)
        eje.fill_between(tt, 0, dd, where=dd > 0, color=E.ALERTA, alpha=0.55)
        eje.axhline(0, color="#1F2332", linewidth=1.5)
        if cruza is not None and cruza < hasta:
            eje.axvline(cruza, color="#056734", linewidth=1.6, linestyle="--")
        eje.set_xlabel("Hora del mes")
        eje.set_title(tit, fontsize=9.5, pad=6)
    ax.set_ylabel("Inyección acumulada − retiro acumulado (kWh)")

    if cruza is not None:
        ax2.annotate("aquí cruza,\ny ya no vuelve",
                     xy=(cruza, 0), xytext=(cruza + 7, dif[:30].min() * 0.45),
                     fontsize=8.2, color="#056734", fontweight="bold",
                     linespacing=1.3,
                     arrowprops=dict(arrowstyle="->", color="#056734", lw=1.4))
        # El unico bloque de texto del panel, y va en la esquina vacia: la
        # curva desciende, de modo que arriba a la derecha no hay nada.
        ax.text(0.985, 0.93,
                f"Cruza en la hora {cruza + 1} de {len(t)}." + chr(10)
                + f"A partir de ahí, el "
                + f"{E.fmt_miles(100 * (len(t) - cruza) / len(t), 0)} % del mes"
                + chr(10) + "se liquida a precio de bolsa.",
                transform=ax.transAxes, ha="right", va="top", fontsize=8.4,
                color="#056734", fontweight="bold", linespacing=1.35)

    fig.suptitle(f"El crédito se agota cuando esta curva pasa por encima de "
                 f"cero · {E.etiqueta_institucion(agente)}",
                 y=0.99, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    datos = pd.DataFrame({"hora_del_mes": t, "inyeccion_acum": iny,
                          "retiro_acum": ret, "diferencia": dif})
    return E.guardar(fig, f"foro_f4_tramos_{cobertura}", datos=datos,
                     procedencia=[f"{destino}/{cobertura}/agentes"])


# ══════════════════════════════════════════════════════════════════════════

def elige_dia(destino, cobertura):
    """El día con más parejas liquidadas, que es el que mejor ilustra."""
    fl = _lee(destino, cobertura, "flujos")
    if fl.empty:
        return None
    c = fl.groupby(fl["fecha"].dt.date.astype(str)).size().sort_values()
    return c.index[-1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("destino")
    p.add_argument("--cobertura", default="m1")
    p.add_argument("--dia", default=None)
    p.add_argument("--libro", default=None)
    a = p.parse_args()

    raiz = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(raiz))

    dia = a.dia or elige_dia(a.destino, a.cobertura)
    libro = a.libro or (f"{raiz}/SALIDAS_SERVIDOR/oficial_{a.cobertura}"
                        "/outputs/resultados_comparacion.xlsx")
    print(f"Grupo F · rediseño de la ponencia · día elegido: {dia}")
    hechas = 0
    # `f2_flujo` sale de la lista: la lamina que la usaba se retiro por decirlo
    # dos veces, y su ultimo paso vive ahora dentro de `f7_modelo`.
    for f, args in ((f1_curvas, (a.destino, a.cobertura, dia)),
                    (f3_dia_detalle, (a.destino, a.cobertura, dia)),
                    # f4_tramos sale (C-175): dibujaba el disparo viejo;
                    # f9_agpe ensena el balance del mes.
                    (f5_tres, (a.destino, a.cobertura, libro)),
                    (f6_precios, (a.destino, a.cobertura)),
                    (f7_modelo, (a.destino, a.cobertura)),
                    (f8_perfiles, (a.destino, a.cobertura)),
                    (f9_agpe, (a.destino, a.cobertura)),
                    (f10_reparto, (a.destino, a.cobertura)),
                    (f11_sin_udenar, (a.destino, a.cobertura))):
        r = f(*args)
        if r:
            hechas += 1
    print(f"\n{hechas} figuras en {E.DIR_FIGURAS}")




# ══════════════════════════════════════════════════════════════════════════
#  f5 · Los tres mecanismos, institucion por institucion
# ══════════════════════════════════════════════════════════════════════════

def f5_tres(destino, cobertura: str, libro: str):
    """Que gana o pierde cada institucion si cambia de mecanismo. EN PESOS.

    LA VERSION ANTERIOR NO SE ENTENDIA, y el defecto era el punto de
    referencia. Dibujaba lo que cada una pierde **frente a su propio mejor
    mecanismo**, de modo que el cero significaba una cosa distinta en cada
    grupo y los porcentajes no eran comparables entre si: el 16,4 de una y el
    4,1 de otra eran fracciones de bases distintas.

    ESTA VERSION USA UNA SOLA REFERENCIA PARA TODAS, y es la que la sala
    entiende sin explicacion: **lo que hacen hoy**, que es autogeneracion
    individual. Cada barra dice cuanto ganaria o perderia esa institucion si
    se pasara al mercado, o si se pasara al colectivo.

    Y VA EN PESOS, no en porcentaje. Asi las barras son comparables entre
    instituciones, se pueden sumar, y se ve de una vez lo que de verdad
    ocurre: al colectivo **cuatro ganan y una pierde**, y lo que pierde esa
    una es mas que lo que ganan las otras cuatro juntas.
    """
    import pandas as pd
    a = pd.read_excel(libro, sheet_name="Por_agente")
    a["inst"] = a["Agente"].map(dict(zip(["A1", "A2", "A3", "A4", "A5"],
                                         E.ORDEN_INSTITUCIONES)))
    t = a.set_index("inst")[["P2P", "C1", "C4_mensual"]].reindex(
        E.ORDEN_INSTITUCIONES)
    d = pd.DataFrame({"al mercado entre pares": t["P2P"] - t["C1"],
                      "al colectivo mensual": t["C4_mensual"] - t["C1"]})

    fig, ax = E.figura(alto=3.6, ancho=E.ANCHO_LAMINA)
    x = np.arange(len(d))
    an = 0.34
    COL = {"al mercado entre pares": E.DESPUES,
           "al colectivo mensual": E.ALERTA}
    for i, c in enumerate(d.columns):
        v = d[c].values / 1e6
        ax.bar(x + (i - 0.5) * an, v, an * 0.92, color=COL[c], label=c)
        for xx, vv in zip(x + (i - 0.5) * an, v):
            # Por debajo de diez mil pesos el redondeo a dos decimales
            # imprime «-0,00», que no dice nada y encima parece un error.
            rot = "casi nada" if abs(vv) < 0.01 else E.fmt_miles(vv, 2)
            ax.text(xx, vv + (0.045 if vv >= 0 else -0.045), rot, ha="center",
                    va="bottom" if vv >= 0 else "top",
                    fontsize=7.8, color=COL[c], fontweight="bold")

    ax.axhline(0, color="#1F2332", linewidth=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels([E.etiqueta_institucion(n) for n in d.index])
    ax.set_ylabel("Frente a lo que hace hoy (millones de COP)")
    ax.set_title("Qué gana o pierde cada institución si cambia de mecanismo",
                 pad=8)
    ax.legend(loc="upper left", fontsize=8.2, framealpha=0.94)
    m = max(abs(d.values.min()), abs(d.values.max())) / 1e6
    ax.set_ylim(-m * 1.30, m * 0.70)
    # La referencia se nombra dentro del dibujo: sin ella el cero no dice nada.
    ax.text(0.99, 0.04, "el cero es la autogeneración individual," + chr(10)
                        + "que es lo que hacen hoy",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8,
            color=E.NEUTRO, style="italic", linespacing=1.3)

    datos = d.copy()
    datos["hoy_individual"] = t["C1"]
    return E.guardar(fig, f"foro_f5_tres_{cobertura}", datos=datos.reset_index(),
                     procedencia=[libro])


# ══════════════════════════════════════════════════════════════════════════
#  f6 · Los dos precios: lo que paga al comprar y lo que recibe al vender
# ══════════════════════════════════════════════════════════════════════════

def f6_precios(destino, cobertura: str):
    """Le cuesta menos comprar Y le rinde mas vender. LAS DOS MITADES.

    LA FIGURA ANTERIOR SOLO CONTABA UNA. Dibujaba el precio de compra y nunca
    el de venta, de modo que la frase de la lamina, que son dos cosas a la vez,
    se quedaba a medias. Y la leyenda caia encima de la ultima institucion.

    DOS PANELES CON LA MISMA REJA. A la izquierda lo que paga por la energia
    que compra, donde **mas bajo es mejor**; a la derecha lo que recibe por la
    que vende, donde **mas alto es mejor**. El gris es siempre la red y el
    color es siempre la comunidad, de modo que el mensaje es que **el color
    esta del lado bueno en los dos paneles**.
    """
    ag = _lee(destino, cobertura, "agentes")
    fl = _lee(destino, cobertura, "flujos")

    filas = []
    for n in E.ORDEN_INSTITUCIONES:
        a = ag[ag["agente"] == n]
        c = fl[fl["comprador"] == n]
        v = fl[fl["vendedor"] == n]
        def tasa(num, den):
            d = float(den)
            return float(num) / d if d > 1e-9 else np.nan
        filas.append(dict(
            inst=n,
            # EL PRECIO DE LA RED ES EL CONTRAFACTICO, de modo que se pesa
            # sobre TODO lo que le falta y todo lo que le sobra, es decir
            # sobre lo que habria cruzado la frontera si no hubiera mercado.
            # Pesarlo solo sobre el residual da otro numero, y responde a otra
            # pregunta: el precio de lo que quedo sin colocar.
            red_cobra=tasa((a["faltante"] * a["techo"]).sum(), a["faltante"].sum()),
            dentro_compra=tasa(c["valor"].sum(), c["kwh"].sum()),
            red_paga=tasa((a["sobrante"] * a["piso"]).sum(), a["sobrante"].sum()),
            dentro_vende=tasa(v["valor"].sum(), v["kwh"].sum())))
    d = pd.DataFrame(filas).set_index("inst")

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_LAMINA, 3.6),
                                  sharey=True, gridspec_kw={"wspace": 0.08})
    y = np.arange(len(d))
    al = 0.34
    for eje, (cred, ccom), tit, col, mejor in (
            (ax, ("red_cobra", "dentro_compra"),
             "Lo que PAGA por lo que compra", E.DESPUES, "más bajo es mejor"),
            (ax2, ("red_paga", "dentro_vende"),
             "Lo que RECIBE por lo que vende", E.ALERTA, "más alto es mejor")):
        eje.barh(y + al / 2, d[cred], al, color=E.NEUTRO,
                 label="con la red, si no hubiera mercado")
        eje.barh(y - al / 2, d[ccom], al, color=col,
                 label="dentro de la comunidad")
        for i, (a_, b_) in enumerate(zip(d[cred], d[ccom])):
            if np.isnan(a_) or np.isnan(b_):
                continue
            eje.text(a_ + 12, i + al / 2, E.fmt_miles(a_, 1), va="center",
                     fontsize=7.6, color=E.NEUTRO)
            eje.text(b_ + 12, i - al / 2, E.fmt_miles(b_, 1), va="center",
                     fontsize=7.6, color=col, fontweight="bold")
        eje.set_title(tit, fontsize=10, pad=16)
        eje.text(0.5, 1.015, mejor, transform=eje.transAxes, ha="center",
                 va="bottom", fontsize=8, color=E.NEUTRO, style="italic")
        eje.set_xlabel("Precio efectivo (COP/kWh)")
        eje.set_xlim(0, max(d[[cred, ccom]].max()) * 1.22)
        # LA LEYENDA VA DENTRO DE SU PANEL. Fuera, al pie, se montaba sobre el
        # rotulo del eje: una leyenda de figura no la ve el ajuste automatico
        # y acababa a la misma altura. Dentro cabe, porque el eje se estira un
        # 22 % por encima de la barra mas larga y esa esquina queda vacia.
        eje.legend(loc="lower right", fontsize=7.8, frameon=True,
                   framealpha=0.94, edgecolor="none", borderpad=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels([E.etiqueta_institucion(n) for n in d.index])
    ax.invert_yaxis()
    # Una banda libre debajo de la ultima institucion, que es donde se sienta
    # la leyenda. Sin ella la leyenda tapaba las barras del CESMAG.
    ax.set_ylim(len(d) + 0.35, -0.65)
    # NI SUPERTITULO NI LEYENDA DENTRO. El primero chocaba con los titulos de
    # los dos paneles, y la segunda caia encima de la ultima institucion. El
    # titulo lo pone la lamina; la leyenda va debajo y sirve a los dos.
    fig.tight_layout()
    return E.guardar(fig, f"foro_f6_precios_{cobertura}", datos=d.reset_index(),
                     procedencia=[f"{destino}/{cobertura}/agentes",
                                  f"{destino}/{cobertura}/flujos"])


# ══════════════════════════════════════════════════════════════════════════
#  f7 · El modelo por dentro, y que le anadimos
# ══════════════════════════════════════════════════════════════════════════

def f7_modelo(destino, cobertura: str):
    """El modelo por dentro, de la medida a la comparacion. DIAGRAMA.

    QUE SE AUDITO DE LA VERSION ANTERIOR, y por que se rehizo entera. No era un
    problema de contenido sino de oficio:

      1. Iba con TIPOGRAFIA DE REMATES, heredada del estilo de las graficas.
         En una grafica es correcta; en un diagrama canta, porque un diagrama
         se lee como un objeto de diseno y no como una figura de datos.
      2. Las cajas llevaban BORDE COMPLETO y esquinas muy redondeadas, con lo
         que parecian botones. Aqui llevan relleno plano y una BARRA DE ACENTO
         a la izquierda, que es la gramatica de tarjeta que ya usa el mazo.
      3. No habia JERARQUIA: rotulo y cuerpo competian al mismo peso. Ahora
         cada paso lleva su numero en un disco, su titulo en versalitas y su
         cuerpo mas claro.
      4. La leyenda era la de la libreria, pegada abajo. Ahora son dos muestras
         colocadas a proposito, alineadas con la reja.
      5. Las cajas tenian ALTURAS DISTINTAS sin ritmo. Aqui hay tres bandas y
         dentro de cada banda todas las tarjetas miden lo mismo.

    Y UN CAMBIO DE CONTENIDO: entra el ultimo paso, la comparacion contra las
    dos normas, que vivia en un diagrama aparte. Al retirarse aquella lamina,
    este diagrama pasa a contar el ejercicio completo.

    EL COLOR SIGUE DICIENDO DE QUIEN ES CADA PIEZA: gris, del modelo publicado;
    azul, su juego; verde, lo que anade esta tesis.
    """
    import matplotlib as mpl

    GRIS, VERDE, AZUL = "#9AA0A6", "#2E7D32", "#2C5F7C"
    TINTA, FONDO = "#1F2332", "#F4F4F2"

    # La tipografia de palo seco se fija SOLO para esta figura y se devuelve al
    # salir: el resto del aparato sigue con la suya.
    previo = mpl.rcParams["font.family"]
    mpl.rcParams["font.family"] = "DejaVu Sans"
    try:
        # LA PROPORCION LA MANDA LA LAMINA, y no el ancho de columna del
        # documento. Con el ancho de columna la figura salia casi cuadrada y en
        # la diapositiva solo llegaba a 6,15 de las 10,80 pulgadas utiles: se
        # proyectaba pequena y con dos palmos de aire a cada lado. A dos por
        # uno llena 9,4 de esas 10,80, que es lo que un diagrama debe hacer.
        AN_FIG, AL_FIG = E.ANCHO_LAMINA, 4.35
        fig, ax = plt.subplots(figsize=(AN_FIG, AL_FIG))
        ax.set_xlim(0, 100)
        # El lienzo llega a 63 para que la fila de muestras tenga aire
        # propio: a 58 se comia el borde superior de la primera banda.
        ax.set_ylim(0, 63)
        ax.axis("off")
        # Pulgadas por unidad de lienzo en cada eje. Como no son iguales, un
        # circulo pedido en unidades sale elipse: de ahi la funcion `disco`.
        UX, UY = AN_FIG / 100.0, AL_FIG / 63.0

        def disco(cx, cy, radio, color, z):
            ax.add_patch(mpl.patches.Ellipse(
                (cx, cy), 2 * radio / UX, 2 * radio / UY,
                facecolor=color, edgecolor="none", zorder=z))

        # ── La reja. Tres columnas y tres bandas, y nada fuera de ella ────
        MAR, CAN = 1.0, 3.0
        AN1 = (100 - 2 * MAR - 2 * CAN) / 3          # una columna
        AN2 = 2 * AN1 + CAN                          # dos columnas
        C = [MAR + i * (AN1 + CAN) for i in range(3)]
        A, B, D = 41.0, 20.0, 2.2                    # base de cada banda
        HA, HB, HD = 16.0, 17.0, 14.0                # altura de cada banda

        def tarjeta(x, y, an, al, num, tit, cue, acento, relleno=FONDO,
                    tinta=TINTA):
            ax.add_patch(mpl.patches.FancyBboxPatch(
                (x, y), an, al, boxstyle="round,pad=0,rounding_size=0.6",
                facecolor=relleno, edgecolor="none", zorder=2))
            # La barra de acento, que es lo que dice de quien es la pieza.
            ax.add_patch(mpl.patches.Rectangle((x, y), 0.062 / UX, al,
                                               facecolor=acento,
                                               edgecolor="none", zorder=3))
            if num:
                disco(x + 3.4, y + al - 3.3, 0.105, acento, 4)
                ax.text(x + 3.4, y + al - 3.3, num, ha="center", va="center",
                        fontsize=7.4, color="white", fontweight="bold",
                        zorder=5)
            ax.text(x + 6.2, y + al - 3.3, tit.upper(), ha="left", va="center",
                    fontsize=8.3, color=tinta, fontweight="bold", zorder=5)
            if cue:
                ax.text(x + 3.4, y + al - 6.6, cue, ha="left", va="top",
                        fontsize=7.3, color=tinta, linespacing=1.45, zorder=5,
                        alpha=0.92)

        def flecha(p1, p2, color=GRIS, ancho=1.6):
            ax.add_patch(mpl.patches.FancyArrowPatch(
                p1, p2, arrowstyle="-|>,head_width=2.6,head_length=4.4",
                mutation_scale=1, linewidth=ancho, color=color,
                shrinkA=2, shrinkB=2, zorder=6, joinstyle="miter"))

        # ── Banda A · lo que entra ────────────────────────────────────────
        tarjeta(C[0], A, AN1, HA, "1", "El dato de la hora",
                "Generación y demanda\nde cada institución", GRIS)
        tarjeta(C[1], A, AN1, HA, "2", "Quién es quién",
                "Le sobra, vende.\nLe falta, compra.\nSe rehace cada hora", GRIS)
        tarjeta(C[2], A, AN1, HA, "3", "Las dos cotas",
                "Techo: su costo unitario\nPiso: permuta, o bolsa\nsi ya se agotó",
                VERDE)
        flecha((C[0] + AN1, A + HA / 2), (C[1], A + HA / 2))
        flecha((C[1] + AN1, A + HA / 2), (C[2], A + HA / 2))

        # ── Banda B · el juego, y la decision ─────────────────────────────
        ax.add_patch(mpl.patches.FancyBboxPatch(
            (C[1], B), AN2, HB, boxstyle="round,pad=0,rounding_size=0.6",
            facecolor=AZUL, edgecolor="none", zorder=2))
        disco(C[1] + 3.4, B + HB - 3.3, 0.105, "white", 4)
        ax.text(C[1] + 3.4, B + HB - 3.3, "4", ha="center", va="center",
                fontsize=7.4, color=AZUL, fontweight="bold", zorder=5)
        ax.text(C[1] + 6.2, B + HB - 3.3, "EL JUEGO", ha="left", va="center",
                fontsize=8.3, color="white", fontweight="bold", zorder=5)
        ax.text(C[1] + AN2 - 2.2, B + HB - 3.3,
                "las tres piezas se integran a la vez", ha="right",
                va="center", fontsize=7.0, color="white", alpha=0.80, zorder=5)
        pieza = (AN2 - 4 * 2.2) / 3
        for i, (t, c) in enumerate((
                ("la energía", "va a las parejas que\nrinden más que la media"),
                ("el precio", "se mueve dentro de la\nbanda y se frena en\nlas cotas"),
                ("los límites", "su precio sombra sube\nmientras se incumplan"))):
            px = C[1] + 2.2 + i * (pieza + 2.2)
            ax.add_patch(mpl.patches.FancyBboxPatch(
                (px, B + 2.0), pieza, HB - 7.4,
                boxstyle="round,pad=0,rounding_size=0.5",
                facecolor="white", alpha=0.13, edgecolor="none", zorder=3))
            ax.text(px + pieza / 2, B + HB - 6.6, t, ha="center", va="top",
                    fontsize=7.8, color="white", fontweight="bold", zorder=5)
            ax.text(px + pieza / 2, B + HB - 9.4, c, ha="center", va="top",
                    fontsize=6.9, color="white", alpha=0.90, linespacing=1.4,
                    zorder=5)

        tarjeta(C[0], B, AN1, HB, "5", "¿Alguien se retira?",
                "Un vendedor se va si el\nmercado le paga menos\nque su propio piso",
                VERDE)
        flecha((C[2] + AN1 / 2, A), (C[2] + AN1 / 2, B + HB))
        flecha((C[1], B + HB * 0.62), (C[0] + AN1, B + HB * 0.62))
        flecha((C[0] + AN1, B + HB * 0.28), (C[1], B + HB * 0.28), VERDE)
        ax.text((C[0] + AN1 + C[1]) / 2, B + HB * 0.28 + 1.1, "sí",
                ha="center", va="bottom", fontsize=7.4, color=VERDE,
                fontweight="bold", zorder=6)

        # ── Banda D · lo que sale ─────────────────────────────────────────
        tarjeta(C[0], D, AN1, HD, "6", "Liquidación",
                "Cada pareja a su precio.\nLo que no se colocó,\na la red", GRIS)
        tarjeta(C[1], D, AN2, HD, "7", "Y se compara contra",
                "", GRIS)
        for i, (nom, ref) in enumerate((
                ("Autogeneración individual", "CREG 174 · crédito de energía,\nexcedentes tipo 1 y tipo 2"),
                ("Colectivo mensual", "CREG 101 072 · reparto\npor porcentaje acordado"))):
            px = C[1] + 3.4 + i * (AN2 / 2 - 1.0)
            ax.text(px, D + HD - 7.0, nom, ha="left", va="top", fontsize=7.6,
                    color=TINTA, fontweight="bold", zorder=5)
            ax.text(px, D + HD - 9.6, ref, ha="left", va="top", fontsize=6.9,
                    color=TINTA, alpha=0.80, linespacing=1.4, zorder=5)
        flecha((C[0] + AN1 / 2, B), (C[0] + AN1 / 2, D + HD), VERDE)
        ax.text(C[0] + AN1 / 2 + 1.4, (B + D + HD) / 2, "no", ha="left",
                va="center", fontsize=7.4, color=VERDE, fontweight="bold",
                zorder=6)
        flecha((C[0] + AN1, D + HD / 2), (C[1], D + HD / 2))

        # ── Las dos muestras, colocadas en la reja y no en una leyenda ────
        for i, (c, t) in enumerate(((GRIS, "del modelo publicado"),
                                    (AZUL, "su juego"),
                                    (VERDE, "lo que añade esta tesis"))):
            x = C[0] + i * 26.5
            ax.add_patch(mpl.patches.Rectangle((x, 60.0), 0.17 / UX, 1.0,
                                               facecolor=c, edgecolor="none"))
            ax.text(x + 0.24 / UX, 60.5, t, ha="left", va="center",
                    fontsize=7.4, color=TINTA, alpha=0.85)

        fig.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.005)
        return E.guardar(fig, f"foro_f7_modelo_{cobertura}",
                         procedencia=["diagrama; refleja el orden del "
                                      "orquestador"])
    finally:
        mpl.rcParams["font.family"] = previo


# ════════════════════════════════════════════════════════════════════════
#  f8 · El dia medio de cada institucion
# ════════════════════════════════════════════════════════════════════════

def f8_perfiles(destino, cobertura: str, laboral: str = None,
                festivo: str = "2025-08-17"):
    """Generacion y consumo de cada institucion, en dos dias contrastados.

    POR QUE NO EL DIA MEDIO, que fue la primera version y estaba mal. En el dia
    medio **el excedente desaparece**: promediar cruza horas de dias distintos
    y lo que en cada uno sobraba se cancela contra lo que en otro faltaba. La
    figura ensenaba cinco paneles sin un solo excedente y prometia justo lo
    contrario. Ni siquiera el domingo medio lo conserva: de las cinco, solo una
    sobrevive al promedio.

    El excedente es un fenomeno de HORAS CONCRETAS, no de la media. De modo que
    se dibujan dos dias reales.

    ARRIBA UN DIA LABORAL. El consumo esta en su nivel de trabajo y **no sobra
    nada en ninguna de las cinco**.

    ABAJO UN DOMINGO. El mismo sol, y el consumo desplomado. **Las cinco
    instituciones tienen excedente**, y el area sombreada lo ensena.

    UN TOPE POR FILA, Y NO UNO SOLO PARA LAS DOS. Esta es la correccion que
    hace legible la figura, y conviene dejar escrito por que. Con tope unico lo
    fija la Cooperativa, que un dia laboral llega a 63 kWh; el domingo entero
    de las cinco no pasa de 13, de modo que la fila de abajo quedaba pegada al
    suelo y **los excedentes de cuatro instituciones no se veian**. Era una
    figura que prometia el excedente y no lo ensenaba.

    El aumento no se disimula, SE DECLARA: la fila de arriba lleva sombreada la
    franja que abajo se amplia, con su cota rotulada. Asi la sala ve a la vez
    cuanto se amplio y cuanto consume cada una en un dia de trabajo.

    Y DE AHI SALE LA FRASE que la charla necesita, que no es la obvia: **el
    excedente no aparece porque haya mas sol, aparece cuando baja el consumo.**
    Es la misma mecanica que despues explica por que el credito de permuta se
    agota un domingo.

    EN KILOVATIOS HORA. El paso es horario, de modo que la potencia media de la
    hora y la energia de esa hora son el mismo numero; se rotula como energia
    porque es lo que se liquida.
    """
    ag = _lee(destino, cobertura, "agentes")
    ag = ag.assign(dia=ag["fecha"].dt.date.astype(str))

    if laboral is None:
        # El dia laboral se elige por criterio y no a dedo: entre semana, del
        # mismo mes que el festivo, el de consumo mas cercano a la mediana.
        lab = ag[(ag["dia_semana"] < 5) & (ag["mes"] == festivo[:7])]
        por = lab.groupby("dia")["demanda"].sum()
        laboral = str((por - por.median()).abs().idxmin())

    orden = [n for n in E.ORDEN_INSTITUCIONES if n in set(ag["agente"])]
    dias = [(laboral, "Un día laboral"), (festivo, "Un domingo")]
    topes = []
    for dia, _ in dias:
        s = ag[ag["dia"] == dia]
        topes.append(float(max(s["demanda"].max(),
                               s["generacion"].max())) * 1.12)

    fig, ejes = plt.subplots(2, len(orden), figsize=(E.ANCHO_LAMINA, 4.6),
                             sharex=True, sharey="row",
                             gridspec_kw={"wspace": 0.12, "hspace": 0.36})
    sub_lab = None
    for fila, (dia, rot) in enumerate(dias):
        sub = ag[ag["dia"] == dia]
        if fila == 0:
            sub_lab = sub
        for col, n in enumerate(orden):
            eje = ejes[fila, col]
            s = sub[sub["agente"] == n].set_index("hora_del_dia").sort_index()
            h = s.index.values
            dem, gen = s["demanda"].values, s["generacion"].values
            if fila == 0:
                # La franja que abajo se amplia, dibujada aqui para que el
                # cambio de escala se vea y no haya que anunciarlo de palabra.
                eje.axhspan(0, topes[1], color="#90A4AE", alpha=0.16,
                            zorder=0, linewidth=0)
                eje.axhline(topes[1], color="#607D8B", linewidth=0.7,
                            linestyle=(0, (4, 2)), zorder=1)
            eje.plot(h, dem, linewidth=1.8, color=E.DESPUES, zorder=4)
            eje.fill_between(h, 0, dem, color=E.DESPUES, alpha=0.18, zorder=2)
            eje.plot(h, gen, linewidth=1.8, color=E.ALERTA, zorder=4)
            # EL EXCEDENTE, QUE ES LO QUE LA FIGURA VIENE A ENSENAR: se rellena
            # solo donde la generacion supera al consumo, y con un color que no
            # se usa para otra cosa.
            eje.fill_between(h, dem, gen, where=gen > dem, interpolate=True,
                             color="#2E7D32", alpha=0.85, zorder=3)
            sob = float(s["sobrante"].sum())
            if sob > 1e-6:
                eje.text(0.04, 0.94, f"+{E.fmt_miles(sob, 1)} kWh",
                         transform=eje.transAxes, ha="left", va="top",
                         fontsize=7.8, color="#2E7D32", fontweight="bold",
                         zorder=6)
            if fila == 0:
                eje.set_title(E.etiqueta_institucion(n), fontsize=9.5, pad=5)
            eje.set_xticks([0, 6, 12, 18])
            eje.set_xlim(0, 23)
            eje.set_ylim(0, topes[fila])
            eje.tick_params(labelsize=8)
        marca = " · escala ampliada" if fila else ""
        ejes[fila, 0].set_ylabel(
            f"{rot}{chr(10)}{dia}{marca}{chr(10)}Energía (kWh)", fontsize=8.8)
    # El rotulo de la franja va al panel mas despejado y POR ENCIMA de la
    # cota, no dentro de ella: puesto en el primero se montaba sobre las
    # curvas y no se leia ninguno de los dos.
    despejado = min(range(len(orden)),
                    key=lambda c: float(sub_lab[sub_lab["agente"] ==
                                                orden[c]]["demanda"].max()))
    ejes[0, despejado].text(
        0.5, topes[1] + (topes[0] - topes[1]) * 0.06,
        f"la franja gris es{chr(10)}lo que se amplía abajo",
        fontsize=6.8, color="#455A64", ha="left", va="bottom", zorder=6)

    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor=E.DESPUES, alpha=0.5,
                              label="lo que consume"),
                        Patch(facecolor=E.ALERTA, label="lo que genera"),
                        Patch(facecolor="#2E7D32", alpha=0.85,
                              label="lo que le SOBRA, y puede vender")],
               loc="lower center", ncol=3, fontsize=9, frameon=False,
               bbox_to_anchor=(0.5, 0.005))
    fig.supxlabel("Hora del día", fontsize=10, y=0.105)
    fig.suptitle("El excedente no aparece porque haya más sol: "
                 "aparece cuando baja el consumo", y=0.995, fontsize=11.5)
    fig.subplots_adjust(left=0.095, right=0.99, top=0.87, bottom=0.20,
                        wspace=0.12, hspace=0.36)

    datos = (ag[ag["dia"].isin([laboral, festivo])]
             [["dia", "agente", "hora_del_dia", "demanda", "generacion",
               "sobrante"]])
    return E.guardar(fig, f"foro_f8_perfiles_{cobertura}", datos=datos,
                     procedencia=[f"{destino}/{cobertura}/agentes"])


def f9_agpe(destino, cobertura: str, mes: str = "2025-07"):
    """Como se clasifica el excedente de un autogenerador, con un mes real.

    QUE DICE LA NORMA, y es lo que la figura dibuja. El articulo 25 de la
    Resolucion CREG 174, en el texto que le dio el articulo 28 de la
    Resolucion CREG 101 072 de 2025, clasifica **al cierre de cada periodo de
    facturacion**: los excedentes acumulados que igualan la importacion se
    reconocen como credito de energia, y los que la superan se valoran a la
    variable del mercado. La comparacion es entre acumulados del mes.

    QUE SE AUDITO DE LA PRIMERA VERSION, y por que se rehizo:

      1. UN TERCIO DEL ANCHO ERA HUECO MUERTO. El eje llegaba a -62 solo para
         alojar un bloque de texto que flotaba entre el nombre y la barra, y
         un eje con zona negativa sin significado invita a leer valores
         negativos donde no los hay. Ahora el dato absoluto es parte del
         rotulo de la fila y el eje empieza en cero.
      2. CUATRO DE CINCO BARRAS ERAN INVISIBLES. Con cuotas de 0,4 a 4,9 % la
         barra no hacia ningun trabajo y lo unico legible era la cifra escrita
         al lado.
      3. Y EL PEOR: LA BARRA NO TENIA CONTRA QUE MEDIRSE. La figura afirma que
         el excedente cabe dentro del cupo y **el cupo no estaba dibujado**;
         solo habia una linea al cien por ciento, lejos a la derecha, y el ojo
         no completa esa distancia.

    DE AHI LA FORMA QUE TIENE AHORA: cada fila lleva su cupo dibujado entero,
    como una regla, y la barra verde se lee como su llenado. Una barra casi
    vacia ya no es una barra que no se ve: es una regla que esta casi vacia, y
    eso es exactamente lo que la lamina quiere decir.

    POR QUE MEDIDO EN PORCENTAJE. Porque el tope del credito **no es el mismo
    para todas**: cada una tiene el suyo, que es su propia importacion del mes.
    En kilovatios hora habria cinco topes distintos y no se podrian comparar.
    """
    ag = _lee(destino, cobertura, "agentes")
    d = (ag[ag["mes"] == mes].groupby("agente")[["sobrante", "faltante"]]
         .sum())
    d = d[d["faltante"] > 0]
    d["cuota"] = 100.0 * d["sobrante"] / d["faltante"]
    # Ordenada por lo unico que ordena aqui: cuanto se acerca cada una al tope.
    d = d.sort_values("cuota", ascending=False)

    VERDE, NARANJA, CUPO = "#2E7D32", "#C75B12", "#DFE3E1"
    TOPE = 118.0
    fig, ax = plt.subplots(figsize=(E.ANCHO_LAMINA, 3.6))
    y = np.arange(len(d))

    ax.axvspan(100, TOPE, color=NARANJA, alpha=0.10, zorder=0, linewidth=0)
    for i, (n, r) in enumerate(d.iterrows()):
        # EL CUPO, dibujado entero. Es la pieza que faltaba: sin el, una barra
        # del 0,4 % no se distingue de un error de dibujo.
        ax.barh(i, 100, 0.62, color=CUPO, edgecolor="none", zorder=1)
        ax.barh(i, r["cuota"], 0.62, color=VERDE, edgecolor="none", zorder=2)
        # La cifra va al final de SU barra, sobre el cupo todavia libre. En
        # una columna a la derecha caia dentro de la banda del tipo 2, que es
        # justo lo contrario de lo que la cifra dice.
        ax.text(r["cuota"] + 1.6, i, f"{E.fmt_miles(r['cuota'], 1)} %",
                va="center", ha="left", fontsize=8.8, color=VERDE,
                fontweight="bold", zorder=4)
    ax.axvline(100, color=NARANJA, linewidth=1.8, zorder=3)

    ax.set_yticks(y)
    ax.set_yticklabels(
        [f"{E.etiqueta_institucion(n)}{chr(10)}"
         f"{E.fmt_miles(r['sobrante'], 0)} de {E.fmt_miles(r['faltante'], 0)}"
         f" kWh" for n, r in d.iterrows()], fontsize=8.8)
    for t in ax.get_yticklabels():
        t.set_linespacing(1.5)
    ax.tick_params(axis="y", length=0)
    ax.invert_yaxis()
    ax.set_xlim(0, TOPE)
    ax.set_ylim(len(d) - 0.35, -1.30)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0", "25 %", "50 %", "75 %", "100 %"])
    ax.set_xlabel("Excedente del mes, medido contra la importación de ese "
                  "mismo mes", fontsize=9.5)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.grid(False)

    # Los dos rotulos que convierten la figura en una regla y no en un dato.
    ax.text(50, -1.02, "CRÉDITO DE ENERGÍA · tipo 1", ha="center",
            va="center", fontsize=8.6, color=VERDE, fontweight="bold")
    ax.text(98, -0.52, "el tope de cada una es su propia importación",
            ha="right", va="center", fontsize=7.8, color=E.NEUTRO,
            style="italic")
    ax.text(109, -1.02, "tipo 2", ha="center", va="center", fontsize=8.6,
            color=NARANJA, fontweight="bold")
    ax.text(109, -0.42, "al mercado", ha="center", va="center", fontsize=7.4,
            color=NARANJA)

    fig.suptitle("Ninguna agota su crédito: el excedente del mes cabe entero "
                 f"dentro de su importación · {mes}", y=0.985, fontsize=11.5)
    fig.subplots_adjust(left=0.145, right=0.985, top=0.87, bottom=0.155)

    datos = d.reset_index()
    return E.guardar(fig, f"foro_f9_agpe_{cobertura}", datos=datos,
                     procedencia=[f"{destino}/{cobertura}/agentes"])


CVM_COMERCIALIZAR = 174.45      # (COP/kWh) componente de comercializar


def _colectivo(ag, miembros):
    """Reparto del colectivo mensual, y lo que vale frente a liquidar solo.

    LA CLASIFICACION VA AL CIERRE DEL MES, que es lo que manda el articulo 25
    de la Resolucion CREG 174 en el texto que le dio el articulo 28 de la
    Resolucion CREG 101 072 de 2025: los excedentes acumulados que igualan la
    importacion son credito de energia. **No es lo que hace todavia la corrida
    oficial**, que dispara hora a hora, y por eso estas cifras no coinciden
    con las de la lamina del resultado hasta que se vuelva a correr.

    Devuelve, por miembro: el porcentaje de reparto, lo que aporta al fondo,
    y lo que gana o pierde frente a la autogeneracion individual.
    """
    sub = ag[ag["agente"].isin(miembros)]
    media = sub.groupby("agente")["generacion"].mean()
    pde = media / media.sum()          # art. 19, proporcional a la generación
    aporte = sub.groupby("agente")["sobrante"].sum()
    solo = {n: 0.0 for n in miembros}
    junto = {n: 0.0 for n in miembros}
    for _, g in sub.groupby("mes"):
        fondo = g["sobrante"].sum()
        for n in miembros:
            gn = g[g["agente"] == n]
            exceso = gn["sobrante"].sum()
            importa = gn["faltante"].sum()
            vale = float(gn["techo"].median()) - CVM_COMERCIALIZAR
            solo[n] += min(exceso, importa) * vale
            junto[n] += min(float(pde[n]) * fondo, importa) * vale
    gana = {n: (junto[n] - solo[n]) / 1e6 for n in miembros}
    return pde, aporte / aporte.sum(), gana


def f10_reparto(destino, cobertura: str):
    """Lo que cada una aporta al fondo comun, y lo que el reparto le reconoce.

    ES LA FIGURA QUE EXPLICA EL COLECTIVO EN UNA SOLA MIRADA. El mecanismo
    suma los excedentes de todas en un fondo mensual y devuelve a cada miembro
    **su porcentaje del fondo, no lo que puso**. Cuando esas dos cantidades no
    coinciden, hay transferencia; y aqui no coinciden en absoluto.

    LAS DOS BARRAS SON LA MISMA MAGNITUD, un porcentaje del mismo fondo, y por
    eso pueden ir en la misma reja y restarse con la vista. La diferencia en
    puntos va escrita, porque es la cifra que decide si a una institucion le
    conviene firmar.

    Y LA LINEA DEL VEINTE POR CIENTO NO ES DECORACION. El articulo 19 admite
    repartir por capacidad instalada, y las cinco plantas son identicas: eso
    daria un quinto a cada una. El porcentaje que usa el motor sale de la
    generacion **medida**, que en esta frontera depende de lo que cada medidor
    alcanza a ver. De ahi que al CESMAG le toque la mitad de lo que le daria
    su placa.
    """
    ag = _lee(destino, cobertura, "agentes")
    miembros = [n for n in E.ORDEN_INSTITUCIONES if n in set(ag["agente"])]
    pde, aporte, _ = _colectivo(ag, miembros)
    d = pd.DataFrame({"aporta": 100 * aporte, "recibe": 100 * pde})
    d = d.sort_values("aporta", ascending=False)

    APORTA, RECIBE = "#C75B12", "#2C5F7C"
    fig, ax = plt.subplots(figsize=(E.ANCHO_LAMINA, 3.6))
    y = np.arange(len(d))
    al = 0.34
    ax.barh(y - al / 2, d["aporta"], al, color=APORTA,
            label="lo que aporta al fondo")
    ax.barh(y + al / 2, d["recibe"], al, color=RECIBE,
            label="lo que el reparto le reconoce")
    for i, (n, r) in enumerate(d.iterrows()):
        ax.text(r["aporta"] + 1.2, i - al / 2, f"{E.fmt_miles(r['aporta'], 1)} %",
                va="center", ha="left", fontsize=8.4, color=APORTA,
                fontweight="bold")
        ax.text(r["recibe"] + 1.2, i + al / 2, f"{E.fmt_miles(r['recibe'], 1)} %",
                va="center", ha="left", fontsize=8.4, color=RECIBE,
                fontweight="bold")
        dif = r["recibe"] - r["aporta"]
        signo = "+" if dif > 0 else ""
        ax.text(96, i, f"{signo}{E.fmt_miles(dif, 1)} pp", va="center",
                ha="right", fontsize=8.6,
                color=(E.ALERTA if dif < 0 else E.DESPUES), fontweight="bold")

    ax.axvline(100 / len(d), color=E.NEUTRO, linewidth=1.0,
               linestyle=(0, (4, 2)), zorder=0)
    # Los dos rotulos van en la banda de encabezado, no al pie: abajo el de la
    # placa se salia del lienzo y arriba explica la linea que tiene al lado.
    ax.text(100 / len(d) + 1.2, -0.85,
            "lo que daría la placa, idéntica en las cinco", ha="left",
            va="center", fontsize=7.6, color=E.NEUTRO, style="italic")
    ax.text(96, -0.85, "diferencia", va="center", ha="right", fontsize=8.0,
            color=E.NEUTRO, style="italic")

    ax.set_yticks(y)
    ax.set_yticklabels([E.etiqueta_institucion(n) for n in d.index],
                       fontsize=9.5)
    ax.tick_params(axis="y", length=0)
    ax.invert_yaxis()
    ax.set_xlim(0, 96)
    ax.set_ylim(len(d) - 0.4, -1.15)
    ax.set_xlabel("Porcentaje del excedente de la comunidad", fontsize=9.5)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.set_xticks([0, 20, 40, 60, 80])
    ax.set_xticklabels(["0", "20 %", "40 %", "60 %", "80 %"])
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    # La leyenda sale del area de datos: dentro tapaba la cifra de la ultima
    # fila, y no hay ningun hueco que no este ocupado por una barra o por la
    # columna de diferencias.
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.005), ncol=2,
              fontsize=8.4, frameon=False)
    fig.suptitle("El colectivo reparte por porcentaje acordado, no por lo que "
                 "cada una pone", y=0.985, fontsize=11.5)
    fig.subplots_adjust(left=0.115, right=0.985, top=0.815, bottom=0.155)

    return E.guardar(fig, f"foro_f10_reparto_{cobertura}",
                     datos=d.reset_index(),
                     procedencia=[f"{destino}/{cobertura}/agentes"])


def f11_sin_udenar(destino, cobertura: str, quien: str = "Udenar"):
    """Que le pasa al colectivo si se retira quien mas excedente aporta.

    LA PREGUNTA QUE CONTESTA es la que hace cualquiera que mire el resultado
    por institucion: si a una sola le perjudica el colectivo, que se salga.
    La figura mide que ocurre entonces con las otras cuatro.

    EL CERO ES EL MISMO EN LAS DOS SERIES y es la autogeneracion individual,
    que **no cambia** cuando alguien se retira, porque cada una liquida sola.
    Por eso las dos barras son comparables: miden lo mismo contra la misma
    referencia.

    LAS DOS SERIES SE CALCULAN CON EL MISMO CRITERIO, la clasificacion al
    cierre del mes del articulo 25. No coinciden con la lamina del resultado,
    que todavia sale de la corrida con el disparo horario.
    """
    ag = _lee(destino, cobertura, "agentes")
    todos = [n for n in E.ORDEN_INSTITUCIONES if n in set(ag["agente"])]
    quedan = [n for n in todos if n != quien]
    _, _, con = _colectivo(ag, todos)
    _, _, sin = _colectivo(ag, quedan)
    d = pd.DataFrame({"con": [con[n] for n in quedan],
                      "sin": [sin[n] for n in quedan]}, index=quedan)

    CON, SIN = "#C75B12", "#8C8C8C"
    fig, ax = plt.subplots(figsize=(E.ANCHO_LAMINA, 3.6))
    x = np.arange(len(d))
    an = 0.34
    ax.bar(x - an / 2, d["con"], an, color=CON,
           label=f"comunidad de {len(todos)}, con "
                 f"{E.etiqueta_institucion(quien)}")
    ax.bar(x + an / 2, d["sin"], an, color=SIN,
           label=f"comunidad de {len(quedan)}, sin "
                 f"{E.etiqueta_institucion(quien)}")
    for i, (n, r) in enumerate(d.iterrows()):
        for dx, v, c in ((-an / 2, r["con"], CON), (an / 2, r["sin"], SIN)):
            ax.text(i + dx, v + (0.02 if v >= 0 else -0.02),
                    E.fmt_miles(v, 2), ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=8.4, color=c,
                    fontweight="bold")
    ax.axhline(0, color=E.TINTA if hasattr(E, "TINTA") else "#1F2332",
               linewidth=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels([E.etiqueta_institucion(n) for n in d.index],
                       fontsize=9.5)
    ax.set_ylabel("Frente a lo que hace hoy (millones de COP)", fontsize=9.5)
    tope = float(max(d.max().max(), 0.1)) * 1.35
    # El suelo deja sitio a la cifra que cuelga de la barra negativa: con 1,45
    # el rotulo caia partido por el borde.
    suelo = float(min(d.min().min(), -0.05)) * 2.6
    ax.set_ylim(suelo, tope)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", fontsize=8.4, frameon=True, framealpha=0.94,
              edgecolor="none")
    # La nota va arriba a la derecha, que es el unico hueco que ninguna barra
    # ocupa: abajo se montaba sobre las dos barras negativas.
    ax.text(0.99, 0.97, "el cero es la autogeneración individual,"
                        f"{chr(10)}que no cambia si alguien se retira",
            transform=ax.transAxes, ha="right", va="top", fontsize=7.8,
            color=E.NEUTRO, style="italic", linespacing=1.5)
    fig.suptitle(f"Sin {E.etiqueta_institucion(quien)}, el colectivo deja de "
                 f"convenirle a la mitad", y=0.985, fontsize=11.5)
    fig.subplots_adjust(left=0.085, right=0.985, top=0.87, bottom=0.115)

    return E.guardar(fig, f"foro_f11_sin_{quien.lower()}_{cobertura}",
                     datos=d.reset_index(),
                     procedencia=[f"{destino}/{cobertura}/agentes"])


if __name__ == "__main__":
    main()
