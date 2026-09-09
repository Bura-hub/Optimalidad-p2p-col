"""
El aparato de figuras del foro, todas leídas del almacén de la corrida.

PARA QUÉ SON. Para proyectar en una ponencia, no para imprimir en un artículo.
De ahí el diseño: **una idea por figura, pocas series, rótulos grandes**. Una
figura que se entiende en veinte segundos de pie desde la última fila.

LA REGLA QUE LAS GOBIERNA A TODAS: ninguna vuelve a simular y ninguna cifra se
escribe a mano. Todas leen del almacén, que es lo que la corrida oficial
escribió, y cada una deja su tabla de datos y su nota de procedencia al lado.

LAS HORAS PROTAGONISTAS SE ELIGEN POR CRITERIO MEDIDO, no por conveniencia
narrativa. Cuatro categorías fijadas de antemano, que el almacén resuelve solo y
que cada figura declara en su pie:

  típica              la mediana de las horas con al menos dos vendedores y
                      tres compradores
  escasez de oferta   la de menor cociente entre oferta y demanda netas
  exceso de oferta    la de mayor cociente
  patológica          precio pegado a una cota, u oferta y demanda casi
                      empatadas

LOS CUATRO GRUPOS:

  A · cómo se acuerda el precio. Sobre esas horas: la trayectoria del precio
      con la banda de cada comprador dibujada y **el multiplicador que muerde**
      en el eje gemelo, que es lo que explica por qué el precio se detiene
      donde se detiene; el reparto entre las dos partes; y las potencias por
      pareja a lo largo de la integración.
  C · la discusión de precios en un día: las veinticuatro horas con su banda,
      su acuerdo, quién entra y quién se retira.
  D · la comparación regulatoria: la liquidación por institución llevada a
      figura, y el mercado frente a los cinco escenarios.

EL GRUPO B —lo que el modelo base hacía y no reproducimos: el sistema sin
filtrar y el barrido del término de rivalidad— **no vive aquí**, porque no se
puede leer del almacén: exige correr el modelo con otros parámetros. Va en su
propio guion para que la regla de esta carpeta siga siendo cierta sin
excepciones.

Uso:
    python gen_foro.py CARPETA_DEL_ALMACEN
    python gen_foro.py CARPETA_DEL_ALMACEN --cobertura m3 --grupo A
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
for _p in (RAIZ, AQUI):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import estilo as E  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

CATEGORIAS = ("tipica", "escasez", "exceso", "patologica")
ROTULO = {
    "tipica": "hora típica",
    "escasez": "escasez de oferta",
    "exceso": "exceso de oferta",
    "patologica": "hora patológica",
}


# ══════════════════════════════════════════════════════════════════════════
#  La elección de las horas, que es lo primero que hay que poder defender
# ══════════════════════════════════════════════════════════════════════════

def elige_horas(destino, cobertura: str) -> dict:
    """Las cuatro horas protagonistas, con el criterio que las eligió.

    Devuelve un diccionario de categoría a un registro con la hora, el valor
    del criterio y una frase que la figura imprime en su pie. Que la frase
    salga de aquí y no del pie es deliberado: así la figura no puede afirmar
    un criterio distinto del que se aplicó.
    """
    from core.almacen import lee

    h = lee(destino, cobertura, "horas")
    ag = lee(destino, cobertura, "agentes")
    if h.empty or ag.empty:
        raise ValueError(f"el almacén de {destino} no tiene horas ni agentes")

    h = h[h["resuelta"].astype(bool)].copy()
    if h.empty:
        raise ValueError("ninguna hora del almacén resolvió")

    # Oferta y demanda NETAS de cada hora, que es lo que decide el lado corto.
    bal = (ag.groupby("hora", observed=True)
             .agg(oferta=("sobrante", "sum"), demanda=("faltante", "sum"))
             .reset_index())
    h = h.merge(bal, on="hora", how="left")
    h["cociente"] = h["oferta"] / h["demanda"].clip(lower=1e-9)

    fuera = {}

    # ── típica: la mediana de las horas con mercado de verdad ────────────
    amplias = h[(h["vendedores"] >= 2) & (h["compradores"] >= 3)]
    if amplias.empty:                       # comunidad pequeña: se relaja
        amplias = h[(h["vendedores"] >= 1) & (h["compradores"] >= 2)]
    if not amplias.empty:
        s = amplias.sort_values("volumen").reset_index(drop=True)
        r = s.iloc[len(s) // 2]
        fuera["tipica"] = dict(
            hora=int(r["hora"]), criterio=float(r["volumen"]),
            frase=(f"la mediana por volumen de las {len(amplias)} horas con al "
                   f"menos {int(amplias['vendedores'].min())} vendedores y "
                   f"{int(amplias['compradores'].min())} compradores"))

    # ── escasez y exceso de oferta ───────────────────────────────────────
    con = h[h["demanda"] > 1e-6]
    if not con.empty:
        r = con.loc[con["cociente"].idxmin()]
        fuera["escasez"] = dict(
            hora=int(r["hora"]), criterio=float(r["cociente"]),
            frase=(f"la de menor cociente entre oferta y demanda netas, "
                   f"{E.fmt_miles(r['cociente'], 3)}"))
        r = con.loc[con["cociente"].idxmax()]
        fuera["exceso"] = dict(
            hora=int(r["hora"]), criterio=float(r["cociente"]),
            frase=(f"la de mayor cociente entre oferta y demanda netas, "
                   f"{E.fmt_miles(r['cociente'], 3)}"))

    # ── patológica: precio pegado a una cota, o los dos lados empatados ──
    #
    # Se mide contra la banda REAL de esa hora, no contra una constante. Un
    # precio a menos del uno por ciento de su cota es un precio que la
    # dinamica no eligio: lo eligio la restriccion.
    banda = (ag.groupby("hora", observed=True)
               .agg(techo=("techo", "max"), piso=("piso", "min"))
               .reset_index())
    h = h.merge(banda, on="hora", how="left")
    ancho = (h["techo"] - h["piso"]).clip(lower=1e-9)
    pegado = np.minimum((h["precio_medio"] - h["piso"]).abs(),
                        (h["techo"] - h["precio_medio"]).abs()) / ancho
    empate = (h["cociente"] - 1.0).abs()
    h["patologia"] = np.minimum(pegado, empate)
    if h["patologia"].notna().any():
        r = h.loc[h["patologia"].idxmin()]
        cual = ("con el precio pegado a una cota de su banda"
                if float(pegado.loc[r.name]) <= float(empate.loc[r.name])
                else "con la oferta y la demanda casi empatadas")
        fuera["patologica"] = dict(
            hora=int(r["hora"]), criterio=float(r["patologia"]),
            frase=f"la más extrema {cual}")

    return fuera


# ══════════════════════════════════════════════════════════════════════════
#  Grupo A · cómo se acuerda el precio
# ══════════════════════════════════════════════════════════════════════════

def _tray(destino, cobertura, k) -> pd.DataFrame:
    from core.almacen import lee
    t = lee(destino, cobertura, "trayectorias")
    return t[t["hora"] == k].sort_values("paso").reset_index(drop=True)


def _columnas(t: pd.DataFrame, prefijo: str) -> list:
    """Las columnas del prefijo QUE ESA HORA TIENE DE VERDAD.

    La tabla de trayectorias es la union de todas las horas del horizonte, y
    los papeles cambian de una a otra: una institucion que compra a las once y
    vende a las doce aporta columnas de las dos clases. En la hora en que no
    juega ese papel, su columna esta vacia.

    Dibujarla igualmente no pinta nada pero **si añade una entrada a la
    leyenda**, y una leyenda que promete una serie que no esta es peor que una
    serie de menos: el lector la busca.
    """
    return [c for c in t.columns
            if c.startswith(prefijo) and t[c].notna().any()]


def _agentes_hora(destino, cobertura, k) -> pd.DataFrame:
    from core.almacen import lee
    a = lee(destino, cobertura, "agentes")
    return a[a["hora"] == k].reset_index(drop=True)


def a1_acuerdo(destino, cobertura: str, k: int, cat: str, frase: str):
    """La trayectoria del precio, con la banda y el multiplicador que muerde.

    ES LA FIGURA QUE EXPLICA EL MECANISMO, y lo que el modelo base no podía
    dibujar: sus cotas eran constantes escritas a mano y sus multiplicadores no
    salían de la integración. Aquí las cotas son las medidas de cada comprador
    y el multiplicador es el que la integración calculó.

    El eje izquierdo lleva el precio y las bandas; el derecho, el multiplicador
    del vendedor, que es el que dice **cuándo deja de poder ofrecer más**. Si el
    precio se detiene a la vez que el multiplicador despega, la figura ha
    contado por qué.
    """
    t = _tray(destino, cobertura, k)
    ag = _agentes_hora(destino, cobertura, k)
    if t.empty:
        return None
    cols = _columnas(t, "precio_")
    if not cols:
        return None

    fig, ax = E.figura(alto=3.6)
    ax2 = ax.twinx()

    # Las bandas de cada comprador, al fondo. Son el escenario, no la trama.
    #
    # AGRUPADAS POR VALOR, y no una por agente: varias instituciones comparten
    # comercializador y por tanto techo, de modo que dibujar una linea y un
    # rotulo por cada una imprime tres rotulos encima del mismo pixel y no se
    # lee ninguno. Se dibuja una linea por techo DISTINTO, rotulada con
    # quienes lo comparten.
    techos = {}
    for c in cols:
        n = c.replace("precio_", "")
        f = ag[ag["agente"] == n]
        if f.empty:
            continue
        techos.setdefault(round(float(f["techo"].iloc[0]), 1), []).append(n)
    for te, quienes in sorted(techos.items()):
        ax.axhline(te, color=E.NEUTRO, linewidth=0.8, linestyle=":", zorder=1)
        nom = ", ".join(E.etiqueta_institucion(x) for x in quienes)
        ax.annotate(f"techo de {nom}", xy=(t["t"].iloc[-1], te), fontsize=7,
                    color=E.NEUTRO, ha="right", va="bottom", xytext=(0, 2),
                    textcoords="offset points")
    pisos = ag[ag["papel"] == "vendedor"]["piso"]
    if not pisos.empty:
        p = float(pisos.min())
        ax.axhline(p, color=E.NEUTRO, linewidth=0.8, linestyle=":", zorder=1)
        ax.annotate("piso del vendedor", xy=(t["t"].iloc[-1], p), fontsize=7,
                    color=E.NEUTRO, ha="right", va="bottom", xytext=(0, 2),
                    textcoords="offset points")

    # Las curvas de precio. VARIAS PUEDEN COINCIDIR: dos compradores con el
    # mismo techo y el mismo vendedor acuerdan el mismo precio, y entonces la
    # ultima dibujada tapa a las anteriores y la leyenda promete cuatro series
    # donde solo se ven dos. Se agrupan las que coinciden y se rotula el grupo.
    #
    # El criterio de coincidencia es VISUAL, no exacto: dos curvas que nunca
    # se separan mas de medio peso por kilovatio hora ocupan el mismo pixel en
    # una figura cuyo eje abarca decenas. Exigir igualdad al bit dejaria el
    # defecto intacto por diferencias que nadie puede ver.
    JUNTAS = 0.5
    grupos: list[tuple[list[str], np.ndarray]] = []
    for c in cols:
        v = t[c].to_numpy(dtype=float)
        for quienes, ref in grupos:
            if float(np.max(np.abs(v - ref))) <= JUNTAS:
                quienes.append(c.replace("precio_", ""))
                break
        else:
            grupos.append(([c.replace("precio_", "")], v))
    for quienes, serie in grupos:
        nom = " = ".join(E.etiqueta_institucion(x) for x in quienes)
        ax.plot(t["t"], serie, linewidth=2.2,
                color=E.color_institucion(quienes[0]), label=nom, zorder=3)

    lam = [c for c in _columnas(t, "lam_")
           if not c.startswith("lam_filt")]
    if lam:
        m = t[lam].abs().max(axis=1)
        ax2.plot(t["t"], m, linewidth=1.6, color=E.ALERTA, linestyle="--",
                 zorder=2)
        ax2.set_ylabel("multiplicador del vendedor", color=E.ALERTA)
        ax2.tick_params(axis="y", colors=E.ALERTA)

    ax.set_xlabel("Tiempo de integración")
    ax.set_ylabel("Precio acordado (COP/kWh)")
    ax.set_title(f"Cómo se acuerda el precio · {ROTULO[cat]}", pad=8)
    ax.legend(loc="center left", fontsize=8, frameon=False)
    E.eje_espanol(ax, "y", "miles", 0)
    fig.text(0.01, 0.005,
             f"Nota. Hora {k} de la frontera {cobertura.upper()}, elegida por "
             f"criterio medido: {frase}. Las líneas punteadas son la banda "
             f"medida de cada agente y la discontinua es el multiplicador de "
             f"la restricción del vendedor, que crece mientras esa restricción "
             f"sigue activa. Dos compradores con el mismo techo acuerdan el "
             f"mismo precio; cuando eso pasa, sus curvas se dibujan juntas y "
             f"la leyenda lo dice.",
             fontsize=6.6, color=E.NEUTRO, ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.145, 1, 1))
    datos = t[["t"] + cols + lam].copy()
    return E.guardar(fig, f"foro_a1_acuerdo_{cat}_{cobertura}", datos=datos,
                     procedencia=[f"{destino}/{cobertura}/trayectorias",
                                  f"{destino}/{cobertura}/agentes"])


def a2_reparto(destino, cobertura: str, k: int, cat: str, frase: str):
    """Quién se queda con el excedente de esa hora, y contra qué patrón.

    El excedente de un intercambio es el ancho de la banda por la energía, y no
    depende del precio: lo que el precio decide es **el reparto**. Esta figura
    lo dice en la única unidad en que se puede decir, que es el porcentaje, y
    lo pone al lado del reparto a la mitad, que es el que el contrato interno
    produce por construcción.
    """
    from core.almacen import lee

    fl = lee(destino, cobertura, "flujos")
    f = fl[fl["hora"] == k]
    if f.empty:
        return None
    aho = float(f["ahorro_comprador"].sum())
    pri = float(f["prima_vendedor"].sum())
    tot = aho + pri
    if tot <= 1e-9:
        return None

    fig, ax = E.figura(alto=2.4)
    y = [1, 0]
    izq = [50.0, 100 * aho / tot]
    der = [50.0, 100 * pri / tot]
    ax.barh(y, izq, color=E.DESPUES, height=0.55, label="compradores")
    ax.barh(y, der, left=izq, color=E.ALERTA, height=0.55, label="vendedores")
    for yy, a_, b_ in zip(y, izq, der):
        ax.text(a_ / 2, yy, E.fmt_miles(a_, 2) + " %", ha="center", va="center",
                color="white", fontsize=9, fontweight="bold")
        ax.text(a_ + b_ / 2, yy, E.fmt_miles(b_, 2) + " %", ha="center",
                va="center", color="white", fontsize=9, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(["contrato a precio pactado", "mercado entre pares"])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Reparto del excedente (%)")
    ax.set_title(f"Quién se queda con el excedente · {ROTULO[cat]}", pad=8)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.55), ncol=2,
              fontsize=8, frameon=False)
    fig.text(0.01, 0.005,
             f"Nota. Hora {k} de la frontera {cobertura.upper()}: {frase}. El "
             f"excedente total es el mismo en las dos filas, porque es el "
             f"ancho de la banda por la energía y no depende del precio; lo "
             f"que cambia es quién se lo lleva.",
             fontsize=6.6, color=E.NEUTRO, ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.24, 1, 1))
    datos = pd.DataFrame({"reparto": ["contrato", "mercado"],
                          "compradores_pct": izq, "vendedores_pct": der,
                          "excedente_COP": [tot, tot]})
    return E.guardar(fig, f"foro_a2_reparto_{cat}_{cobertura}", datos=datos,
                     procedencia=[f"{destino}/{cobertura}/flujos"])


def a3_potencias(destino, cobertura: str, k: int, cat: str, frase: str):
    """Las potencias por pareja a lo largo de la integración.

    Es la figura que muestra que el reparto de la energía **se decide antes que
    el precio**: las potencias se estabilizan primero y el precio sigue
    moviéndose sobre una asignación ya fija. Es la observación que sostiene por
    qué el volumen transado no depende del precio.
    """
    t = _tray(destino, cobertura, k)
    if t.empty:
        return None
    cols = _columnas(t, "P_")
    if not cols:
        return None

    fig, ax = E.figura(alto=3.2)
    for c in sorted(cols, key=lambda x: -float(t[x].iloc[-1])):
        v, cp = c[2:].split("_", 1)
        ax.plot(t["t"], t[c], linewidth=2.0,
                color=E.color_institucion(cp),
                label=f"{E.etiqueta_institucion(v)} → "
                      f"{E.etiqueta_institucion(cp)}")
    ax.set_xlabel("Tiempo de integración")
    ax.set_ylabel("Energía de la pareja (kWh)")
    ax.set_title(f"Cómo se reparte la energía · {ROTULO[cat]}", pad=8)
    ax.legend(loc="best", fontsize=7.5, frameon=False, ncol=2)
    fig.text(0.01, 0.005,
             f"Nota. Hora {k} de la frontera {cobertura.upper()}: {frase}. Una "
             f"línea por pareja que intercambió energía.",
             fontsize=6.6, color=E.NEUTRO, ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.105, 1, 1))
    return E.guardar(fig, f"foro_a3_potencias_{cat}_{cobertura}",
                     datos=t[["t"] + cols],
                     procedencia=[f"{destino}/{cobertura}/trayectorias"])


# ══════════════════════════════════════════════════════════════════════════
#  Grupo C · la discusión de precios en un día
# ══════════════════════════════════════════════════════════════════════════

def elige_dia(destino, cobertura: str) -> str:
    """El día con más variación de precio entre sus horas de mercado.

    Se elige por criterio y no por conveniencia: el día cuyo precio acordado
    recorre el mayor tramo de su banda es el que más tiene que enseñar.
    """
    from core.almacen import lee

    h = lee(destino, cobertura, "horas")
    h = h[h["resuelta"].astype(bool)].copy()
    if h.empty:
        raise ValueError("ninguna hora resolvió")
    h["dia"] = pd.to_datetime(h["fecha"]).dt.date
    g = (h.groupby("dia", observed=True)["precio_medio"]
          .agg(["min", "max", "count"]).reset_index())
    g = g[g["count"] >= 3] if (g["count"] >= 3).any() else g
    g["recorrido"] = g["max"] - g["min"]
    return str(g.loc[g["recorrido"].idxmax(), "dia"])


def c1_dia(destino, cobertura: str, dia: str):
    """Las veinticuatro horas de un día: la banda, el acuerdo y los papeles.

    Es la figura de la discusión de precios. Arriba, la banda de la comunidad
    hora a hora con el precio que se acordó dentro; abajo, cuántos venden,
    cuántos compran y **cuántos se retiraron**, que es lo que el criterio de
    participación produce y que ninguna figura del proyecto mostraba.
    """
    from core.almacen import lee

    h = lee(destino, cobertura, "horas")
    ag = lee(destino, cobertura, "agentes")
    h = h[pd.to_datetime(h["fecha"]).dt.date.astype(str) == dia].copy()
    ag = ag[pd.to_datetime(ag["fecha"]).dt.date.astype(str) == dia].copy()
    if h.empty:
        return None
    b = (ag.groupby("hora_del_dia", observed=True)
           .agg(techo=("techo", "max"), piso=("piso", "min"))
           .reset_index())
    h = h.merge(b, on="hora_del_dia", how="left").sort_values("hora_del_dia")

    fig, (ax, ax2) = plt.subplots(
        2, 1, figsize=(E.ANCHO_COMPLETO, 5.0), sharex=True,
        gridspec_kw=dict(height_ratios=[2.1, 1.0], hspace=0.12))

    # LAS DOS COTAS COMO LINEAS, y no solo como relleno. Con el relleno solo,
    # una banda ancha se come la figura y no se ve DONDE esta cada cota, que es
    # justo lo que hay que leer: el techo apenas se mueve y el piso se desploma.
    ax.fill_between(h["hora_del_dia"], h["piso"], h["techo"],
                    color=E.NEUTRO, alpha=0.13, linewidth=0)
    ax.plot(h["hora_del_dia"], h["techo"], linewidth=1.4, color=E.NEUTRO,
            linestyle="--", label="techo: lo que paga a la red")
    ax.plot(h["hora_del_dia"], h["piso"], linewidth=1.4, color=E.ALERTA,
            linestyle="--", label="piso: lo que la red le paga")

    # EL PRECIO SOLO DONDE HUBO MERCADO, y sin unir horas que no son
    # contiguas. Unirlas dibuja un mercado continuo que no existio: en las
    # horas sin acuerdo no hay precio, y una linea recta entre las once de la
    # manana y las cuatro de la tarde afirma que si lo hubo.
    serie = h.set_index("hora_del_dia")["precio_medio"].reindex(range(24))
    serie[~h.set_index("hora_del_dia")["resuelta"].astype(bool)
           .reindex(range(24), fill_value=False)] = np.nan
    ax.plot(serie.index, serie.values, marker="o", markersize=5,
            linewidth=2.6, color=E.DESPUES,
            label="precio acordado dentro de la comunidad")
    ax.set_ylabel("Precio (COP/kWh)")
    ax.set_title(f"Un día de mercado · {dia}", pad=8)
    # DENTRO, arriba a la izquierda. Encima del titulo se lo comia, y debajo
    # del eje se solapaba con el panel de los papeles, que empieza pegado. El
    # hueco de la manana esta vacio de datos y es donde cabe.
    ax.legend(loc="upper left", fontsize=7.5, framealpha=0.92,
              borderpad=0.5, labelspacing=0.35)
    E.eje_espanol(ax, "y", "miles", 0)

    pap = (ag.groupby(["hora_del_dia", "papel"], observed=True).size()
             .unstack(fill_value=0))
    for p, col in (("vendedor", E.ALERTA), ("comprador", E.DESPUES),
                   ("retirado", "#7B3F00")):
        if p in pap.columns:
            ax2.plot(pap.index, pap[p], marker="s", markersize=3.5,
                     linewidth=1.8, color=col, label=p + "es"
                     if p != "retirado" else "retirados")
    ax2.set_xlabel("Hora del día")
    ax2.set_ylabel("Agentes")
    ax2.set_xticks(range(0, 24, 2))
    ax2.set_ylim(-0.4, float(pap.to_numpy().max()) + 2.2)
    ax2.legend(loc="upper center", fontsize=7.5, frameon=False, ncol=3,
               columnspacing=1.4, handlelength=1.6)

    # EL PIE DESCRIBE LO QUE ESTA FIGURA MUESTRA, y se calcula. La version
    # anterior afirmaba que la banda se ensancha al mediodia porque ahi se
    # agota el credito de permuta. Eso era cierto del dia con el que se probo
    # y falso de este, donde el credito ya venia agotado y la banda es ancha
    # desde la primera hora. Un pie que afirma en vez de describir sobrevive
    # impreso hasta que alguien mira la figura al lado del texto.
    _anchos = (h["techo"] - h["piso"])
    _hay = h["resuelta"].astype(bool).sum()
    fig.text(0.01, 0.005,
             f"Nota. Frontera {cobertura.upper()}. El día se eligió por "
             f"criterio medido: el de mayor recorrido del precio entre sus "
             f"horas de mercado. Hubo acuerdo en {_hay} de las 24 horas y el "
             f"precio solo se dibuja en esas. La banda va del piso "
             f"al techo y ese día mide entre "
             f"{E.fmt_miles(_anchos.min(), 0)} y "
             f"{E.fmt_miles(_anchos.max(), 0)} (COP/kWh).",
             fontsize=6.6, color=E.NEUTRO, ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.165, 1, 1))
    return E.guardar(fig, f"foro_c1_dia_{cobertura}",
                     datos=h[["hora_del_dia", "piso", "techo", "precio_medio",
                              "vendedores", "compradores", "retirados",
                              "volumen"]],
                     procedencia=[f"{destino}/{cobertura}/horas",
                                  f"{destino}/{cobertura}/agentes"])


# ══════════════════════════════════════════════════════════════════════════
#  Grupo D · la comparación regulatoria
# ══════════════════════════════════════════════════════════════════════════

def d1_liquidacion(destino, cobertura: str):
    """La frase del asesor, hecha figura.

    A cuánto le pagaría la red el excedente a cada institución y a cuánto lo
    coloca dentro de la comunidad. Es la comparación que él pidió poder hacer
    para una entidad, y aquí están las cinco.
    """
    from liquidacion import factura

    f = factura(destino, cobertura, "mes")
    tot = f.groupby("agente", observed=True).agg(
        cobro=("cobro_sin_mercado", "sum"), kwh_c=("faltante", "sum"),
        pago=("pago_sin_mercado", "sum"), kwh_v=("sobrante", "sum"),
        dc=("paga_dentro", "sum"), kdc=("kwh_compra_p2p", "sum"),
        dv=("cobra_dentro", "sum"), kdv=("kwh_vende_p2p", "sum"))
    with np.errstate(divide="ignore", invalid="ignore"):
        tot["red_paga"] = np.where(tot["kwh_v"] > 1e-9,
                                   tot["pago"] / tot["kwh_v"].clip(lower=1e-12),
                                   np.nan)
        tot["dentro_vende"] = np.where(
            tot["kdv"] > 1e-9, tot["dv"] / tot["kdv"].clip(lower=1e-12), np.nan)
        tot["red_cobra"] = np.where(tot["kwh_c"] > 1e-9,
                                    tot["cobro"] / tot["kwh_c"].clip(lower=1e-12),
                                    np.nan)
        tot["dentro_compra"] = np.where(
            tot["kdc"] > 1e-9, tot["dc"] / tot["kdc"].clip(lower=1e-12), np.nan)
    tot = tot.reindex([n for n in E.ORDEN_INSTITUCIONES if n in tot.index])

    fig, ax = E.figura(alto=3.4)
    y = np.arange(len(tot))
    alto = 0.34
    ax.barh(y + alto / 2, tot["red_cobra"], alto, color=E.NEUTRO,
            label="lo que la red le cobraría")
    ax.barh(y - alto / 2, tot["dentro_compra"], alto, color=E.DESPUES,
            label="lo que paga dentro de la comunidad")
    for i, (a_, b_) in enumerate(zip(tot["red_cobra"], tot["dentro_compra"])):
        if np.isfinite(a_):
            ax.text(a_ + 8, i + alto / 2, E.fmt_miles(a_, 1), va="center",
                    fontsize=7.5, color=E.NEUTRO)
        if np.isfinite(b_):
            ax.text(b_ + 8, i - alto / 2, E.fmt_miles(b_, 1), va="center",
                    fontsize=7.5, color=E.DESPUES)
    ax.set_yticks(y)
    ax.set_yticklabels([E.etiqueta_institucion(n) for n in tot.index])
    ax.invert_yaxis()
    ax.set_xlabel("Precio efectivo de la energía que compra (COP/kWh)")
    ax.set_title("Lo que le cuesta a cada institución la energía que compra",
                 pad=8)
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    fig.text(0.01, 0.005,
             f"Nota. Frontera {cobertura.upper()}. Los dos precios están "
             f"ponderados por energía. El de la red es el contrafáctico, es "
             f"decir lo que le cobraría por todo lo que le falta si no hubiera "
             f"mercado.",
             fontsize=6.6, color=E.NEUTRO, ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.075, 1, 1))
    return E.guardar(fig, f"foro_d1_liquidacion_{cobertura}",
                     datos=tot.reset_index(),
                     procedencia=[f"{destino}/{cobertura}/agentes",
                                  f"{destino}/{cobertura}/flujos"])


def d2_mecanismos(destino, cobertura: str):
    """Cuánto pierde cada institución si le imponen el mecanismo equivocado.

    POR QUE NO SE DIBUJA EL BENEFICIO ABSOLUTO, que es lo primero que uno hace.
    Los seis mecanismos liquidan cifras muy parecidas para una misma
    institucion, de modo que seis barras absolutas salen del mismo largo y la
    figura no ensena nada: el titulo afirma que a cada quien le conviene algo
    distinto y las barras no lo muestran. Desde la ultima fila de un auditorio,
    peor todavia.

    Lo que si se ve es **la distancia al mejor**, con el ganador en cero. Y en
    porcentaje del beneficio de esa institucion, no en pesos, porque las cinco
    son de tamanos muy distintos y una diferencia de doscientos mil pesos no
    significa lo mismo para la mas grande que para la mas pequena.

    Y asi aparece lo que en pesos absolutos quedaba escondido: **la discusion no
    es simetrica**. Para el mayor generador, elegir mal cuesta la quinta parte
    de su beneficio; para las demas, menos de la vigesima. Hay una institucion
    con mucho mas en juego que las otras cuatro, y eso es justo lo que vuelve
    dificil el acuerdo del que habla el asesor regulatorio.
    """
    from liquidacion import por_mecanismo

    m = por_mecanismo(destino, cobertura, "mes")
    meses = sorted(str(x) for x in m["mes"].unique())
    tramo = (f"el mes de {meses[0]}" if len(meses) == 1
             else f"los {len(meses)} meses de {meses[0]} a {meses[-1]}")
    escs = [c for c in E.ORDEN_MECANISMOS if c in m.columns]
    t = m.groupby("agente", observed=True)[escs].sum()
    t = t.reindex([n for n in E.ORDEN_INSTITUCIONES if n in t.index])

    mejor_val = t.max(axis=1)
    perdida = 100.0 * (mejor_val.values[:, None] - t.values) /         np.maximum(mejor_val.values[:, None], 1e-9)
    perdida = pd.DataFrame(perdida, index=t.index, columns=escs)

    fig, ax = E.figura(alto=3.5)
    y = np.arange(len(t))
    alto = 0.78 / max(len(escs), 1)
    for i, e in enumerate(escs):
        off = (i - (len(escs) - 1) / 2) * alto
        ax.barh(y + off, perdida[e], alto * 0.9,
                color=E.color_mecanismo(e), label=E.etiqueta_mecanismo(e))

    for j, n in enumerate(t.index):
        gana = t.loc[n, escs].idxmax()
        k = escs.index(gana)
        off = (k - (len(escs) - 1) / 2) * alto
        # El ganador esta en cero y por tanto no tiene barra que lo senale.
        ax.plot(0, j + off, marker="o", markersize=6, color=E.ALERTA, zorder=5)
        # EL ROTULO VA AL FINAL DE LA FILA Y A SU ALTURA MEDIA, no pegado a la
        # marca. Junto a la marca caia sobre la barra del vecino de abajo y se
        # leia como si fuera de la institucion siguiente.
        ax.annotate(f"le conviene {E.etiqueta_mecanismo(gana)}",
                    xy=(float(perdida.loc[n].max()), j), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=7.4,
                    color=E.ALERTA, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels([E.etiqueta_institucion(n) for n in t.index])
    ax.invert_yaxis()
    # Sitio a la derecha para el rotulo mas largo, que es el de la fila con la
    # barra mas corta y por tanto el que mas se sale.
    ax.set_xlim(-0.3, float(perdida.to_numpy().max()) * 1.55)
    ax.set_xlabel("Lo que pierde frente al mejor mecanismo, en % de su beneficio")
    ax.set_title("Elegir mal el mecanismo no cuesta lo mismo a todos", pad=8)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.155), ncol=6,
              fontsize=7, frameon=False, columnspacing=1.1, handlelength=1.3)

    peor = perdida.max(axis=1)
    arriba, resto = peor.idxmax(), peor.drop(peor.idxmax())
    fig.text(0.01, 0.005,
             f"Nota. Frontera {cobertura.upper()}, sobre {tramo}. Cada barra es "
             f"la distancia al mecanismo que más le conviene a esa institución, "
             f"que va en cero y lleva marca. En pesos absolutos los seis "
             f"mecanismos liquidan cifras muy parecidas y la comparación no se "
             f"ve; en distancia al mejor sí. A {E.etiqueta_institucion(arriba)} "
             f"elegir mal le cuesta hasta el {E.fmt_miles(peor.max(), 1)} % de "
             f"su beneficio y a las demás menos del "
             f"{E.fmt_miles(resto.max(), 1)} %.",
             fontsize=6.6, color=E.NEUTRO, ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.175, 1, 1))
    datos = perdida.reset_index().assign(**{
        "unidad": "% del beneficio de la institucion"})
    return E.guardar(fig, f"foro_d2_mecanismos_{cobertura}", datos=datos,
                     procedencia=[f"{destino}/{cobertura}/escenarios"])


# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("destino", help="carpeta del almacén de la corrida")
    ap.add_argument("--cobertura", default="m1")
    ap.add_argument("--grupo", default="ACD", help="letras de los grupos: ACD")
    ap.add_argument("--figuras", default=None,
                    help="carpeta de salida; por defecto la del documento")
    a = ap.parse_args()

    if a.figuras:
        E.DIR_FIGURAS = Path(a.figuras)
        E.DIR_FIGURAS.mkdir(parents=True, exist_ok=True)

    hechas = 0
    if "A" in a.grupo.upper():
        horas = elige_horas(a.destino, a.cobertura)
        print(f"\nGrupo A · cómo se acuerda el precio")
        for cat in CATEGORIAS:
            r = horas.get(cat)
            if r is None:
                print(f"  [omitida] no hay {ROTULO[cat]} en esta corrida")
                continue
            print(f"  {ROTULO[cat]}: hora {r['hora']} — {r['frase']}")
            for f in (a1_acuerdo, a2_reparto, a3_potencias):
                if f(a.destino, a.cobertura, r["hora"], cat, r["frase"]):
                    hechas += 1

    if "C" in a.grupo.upper():
        dia = elige_dia(a.destino, a.cobertura)
        print(f"\nGrupo C · la discusión de precios en un día")
        print(f"  día elegido: {dia}")
        if c1_dia(a.destino, a.cobertura, dia):
            hechas += 1

    if "D" in a.grupo.upper():
        print(f"\nGrupo D · la comparación regulatoria")
        for f in (d1_liquidacion, d2_mecanismos):
            if f(a.destino, a.cobertura):
                hechas += 1

    print(f"\n{hechas} figuras en {E.DIR_FIGURAS}")


if __name__ == "__main__":
    main()
