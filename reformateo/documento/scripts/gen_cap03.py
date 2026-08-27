"""
gen_cap03.py — Figuras del capítulo 3: la domesticación del dato.
==================================================================
Es el capítulo central del documento: el que muestra qué le pasa al dato
entre el medidor y el modelo. Cada figura aísla una etapa y la enseña
como un antes y un después.

    python scripts/gen_cap03.py

Requiere el caché de estados intermedios:

    python scripts/cache_crudo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estilo as E
import datos as D


# ── Utilidades comunes al capítulo ───────────────────────────────────────────
# El nombre interno del tipo de medidor viene del pipeline y está en
# inglés. En el documento no se imprime así: el Capítulo 3 habla de
# medidor neto, neto parcial y bruto, y la figura debe usar el mismo
# vocabulario que el texto que la explica.
TIPO_ES = {"net": "neto", "net_partial": "neto parcial", "gross": "bruto"}

MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun",
            "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre",
                "diciembre"]
DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado",
           "domingo"]


def _rotulo_cobertura(fig, cobertura: str, y: float = 1.0) -> None:
    """
    Estampa la frontera de medición sobre la figura.

    Ninguna figura del documento debe poder leerse fuera de contexto: la
    versión M1 y la M3 de una misma figura son casi idénticas en forma y
    solo se distinguen por los números, de modo que sin este rótulo un
    lector que vea el PNG suelto no sabe cuál tiene delante.
    """
    fig.suptitle(E.TITULO_COBERTURA[cobertura], fontsize=8.5,
                 fontweight="bold", color=E.COBERTURAS[cobertura], y=y)


def _mes_es(periodo) -> str:
    """'2025-04' -> 'abr'. El eje de meses del documento va en español."""
    return MESES_ES[int(str(periodo)[5:7]) - 1]


# ─────────────────────────────────────────────────────────────────────────────
def verificar_inversores():
    """
    Compuerta de las cifras que el capítulo cita sobre los inversores.

    El párrafo de la unidad y el recorte no lleva figura, de modo que sus
    cifras no quedan atadas a ningún generador. Esta comprobación cumple
    ese papel: si el dato crudo cambia de versión, la corrida se detiene
    en vez de dejar en el texto un número que ya no reproduce.

    No dibuja nada.
    """
    import cache_crudo as CC

    raiz = CC.raiz_mte()
    T0, T1 = pd.Timestamp("2025-04-04"), pd.Timestamp("2025-12-16")
    total = 0
    peor = 0.0
    for carpeta in sorted(raiz.glob("*/[Ii]nverter*/*/")):
        partes = []
        for p in sorted(carpeta.rglob("*.csv")):
            d = pd.read_csv(p, usecols=["date", "acPower"], low_memory=False)
            ts = pd.to_datetime(d["date"], errors="coerce")
            v = pd.to_numeric(d["acPower"], errors="coerce")
            partes.append(pd.Series(v[ts.notna()].values, index=ts[ts.notna()]))
        if not partes:
            continue
        s = pd.concat(partes).sort_index()
        h = s[(s.index >= T0) & (s.index < T1)]
        assert float(h.min()) == 0.0, (carpeta.name, float(h.min()))
        assert float(s.min()) == 0.0, (carpeta.name, float(s.min()))
        assert int((h < 0).sum()) == 0, carpeta.name
        # la división conmuta con la media; el recorte no, y por eso se mide
        a = h.groupby(h.index).mean().resample("1h").mean() / 1000.0
        b = (h / 1000.0).groupby(h.index).mean().resample("1h").mean()
        peor = max(peor, float((a - b).abs().max()))
        total += len(h)

    assert total == 793981, total
    assert peor < 1e-14, peor
    print(f"  [inversores] {total:,d} lecturas, mínimo 0 W en los siete, "
          f"conmutación {peor:.1e} kW — cifras del capítulo intactas")
    return total, peor


# ─────────────────────────────────────────────────────────────────────────────
def f31_archivo_a_serie():
    """
    El recorrido de una hora real, del archivo a la serie horaria.

    La etapa 1 del pipeline es la única que el capítulo describía sin
    enseñar: transporta, ordena y convierte, y en prosa todo eso es
    invisible. Esta figura la traza sobre un dato concreto.

    El ejemplo es la UCC porque es la única institución donde la fusión
    de instantes repetidos ocurre dentro del horizonte, y la hora es
    solar para que el carril del inversor lleve vatios con sentido y la
    división entre mil se vea sobre un número real.
    """
    import cache_crudo as CC

    raiz = CC.raiz_mte()
    dir_med = raiz / "UCC" / "electricMeter" / "Medidor 1 - UCC - electricMeter"
    dir_inv = raiz / "UCC" / "inverter" / "Fronius - UCC - inverter"

    H0 = pd.Timestamp("2025-11-06 13:00")
    H1 = H0 + pd.Timedelta(hours=1)
    DIA = pd.Timestamp("2025-11-06")
    HOR0, HOR1 = pd.Timestamp("2025-04-04"), pd.Timestamp("2025-12-16")

    def _tramos(carpeta, col):
        out = []
        for p in sorted(carpeta.rglob("*.csv")):
            d = pd.read_csv(p, usecols=["date", col], low_memory=False)
            ts = pd.to_datetime(d["date"], errors="coerce")
            v = pd.to_numeric(d[col], errors="coerce")
            ok = ts.notna()
            out.append(pd.Series(v[ok].values, index=ts[ok]).sort_index())
        return out

    tramos_med = _tramos(dir_med, "totalActivePower")
    tramos_inv = _tramos(dir_inv, "acPower")

    # La hora en el medidor: filas crudas, instantes únicos y duplicados.
    crudo = pd.concat(tramos_med)
    crudo = crudo[(crudo.index >= H0) & (crudo.index < H1)].sort_index()
    fundida = crudo.groupby(level=0).mean().sort_index()
    conteo = crudo.index.value_counts()
    inst_dup = sorted(conteo[conteo > 1].index)
    media_med = float(fundida.mean())
    media_cruda = float(crudo.mean())

    # La hora en el inversor.
    inv = pd.concat(tramos_inv)
    inv = inv[(inv.index >= H0) & (inv.index < H1)].sort_index()
    media_inv = float(inv.mean())

    # El día completo, desde el caché de estados intermedios.
    series, _ = D.preproceso("m1")
    dia_d = series["UCC__D_raw"].loc[DIA:DIA + pd.Timedelta(hours=23)]
    dia_g = series["UCC__G_ems"].loc[DIA:DIA + pd.Timedelta(hours=23)]

    # Compuerta. Si el dato crudo cambia de versión, la figura se detiene
    # en vez de dibujar un ejemplo que ya no es el que el texto describe.
    assert (len(crudo), len(fundida), len(inst_dup)) == (38, 30, 8), \
        (len(crudo), len(fundida), len(inst_dup))
    assert len(inv) == 30, len(inv)
    assert (inv >= 0).all(), "el recorte a cero sí actuaría"
    assert all(crudo.loc[[i]].nunique() == 1 for i in inst_dup), \
        "las lecturas repetidas no son idénticas"
    assert abs(media_med - float(dia_d.loc[H0])) < 1e-9
    assert abs(media_inv / 1000 - float(dia_g.loc[H0])) < 1e-9

    # ── Lienzo ───────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(E.ANCHO_COMPLETO, 5.45))
    gs = fig.add_gridspec(3, 2, height_ratios=[0.92, 2.05, 1.05],
                          hspace=0.80, wspace=0.30)
    ax_a = fig.add_subplot(gs[0, :])
    ax_b1 = fig.add_subplot(gs[1, 0])
    ax_b2 = fig.add_subplot(gs[1, 1])
    ax_c1 = fig.add_subplot(gs[2, 0])
    ax_c2 = fig.add_subplot(gs[2, 1])

    # ── Zona A: dónde viven los archivos ────────────────────────────────
    def _carril(tramos, y):
        piezas = []
        for s in tramos:
            a = mdates.date2num(s.index[0] + pd.Timedelta(days=5))
            b = mdates.date2num(s.index[-1] - pd.Timedelta(days=5))
            piezas.append((a, max(b - a, 1.0)))
        ax_a.broken_barh(piezas, (y - 0.26, 0.52), facecolors=E.APOYO,
                         edgecolors=E.NEUTRO, linewidth=0.6, zorder=3)

    _carril(tramos_med, 1)
    _carril(tramos_inv, 0)
    ax_a.axvspan(HOR0, HOR1, color=E.DESPUES, alpha=0.08, zorder=1)
    for x in (HOR0, HOR1):
        ax_a.axvline(x, color=E.DESPUES, ls=(0, (3, 2)), lw=0.8, zorder=2)
    ax_a.text(HOR0 + (HOR1 - HOR0) / 2, 2.22,
              "horizonte de estudio (6.144 h)",
              ha="center", va="center", fontsize=7.2, color=E.DESPUES)
    for x in (pd.Timestamp("2025-03-05"), pd.Timestamp("2026-02-25")):
        ax_a.text(x, -1.00, "se descarta", ha="center", va="center",
                  fontsize=7, style="italic", color=E.NEUTRO)
    ax_a.axvline(DIA, color=E.ANTES, lw=1.2, zorder=4)
    ax_a.plot([mdates.date2num(DIA)], [1.62], marker="v", ms=5,
              color=E.ANTES, zorder=5)
    ax_a.text(DIA - pd.Timedelta(days=7), 1.62,
              "el ejemplo: 6 de noviembre, 13 horas",
              ha="right", va="center", fontsize=7.2, color=E.ANTES)
    ax_a.set_xlim(pd.Timestamp("2025-02-01"), pd.Timestamp("2026-05-10"))
    ax_a.set_ylim(-1.5, 2.55)
    ax_a.set_yticks([0, 1])
    ax_a.set_yticklabels(["inversor", "medidor"], fontsize=7.2)
    ticks = [pd.Timestamp(x) for x in ("2025-03-01", "2025-06-01",
                                       "2025-09-01", "2025-12-01",
                                       "2026-03-01")]
    ax_a.set_xticks(ticks)
    ax_a.set_xticklabels([E.fmt_fecha(x, "mes") for x in ticks], fontsize=7.2)
    ax_a.grid(False)
    for lado in ("left", "right", "top"):
        ax_a.spines[lado].set_visible(False)

    # ── Zona B1: la hora en el medidor ──────────────────────────────────
    minutos = [(t - H0).total_seconds() / 60 for t in fundida.index]
    ax_b1.plot(minutos, fundida.values, color="#CCCCCC", lw=0.7, zorder=2)
    ax_b1.scatter(minutos, fundida.values, s=14, color=E.NEUTRO, zorder=3)
    mdup = [(t - H0).total_seconds() / 60 for t in inst_dup]
    vdup = [float(fundida.loc[t]) for t in inst_dup]
    ax_b1.scatter(mdup, vdup, s=52, facecolors="none", edgecolors=E.ANTES,
                  lw=1.1, zorder=4)
    ax_b1.annotate("8 instantes traen la lectura\npor duplicado: se funden en una",
                   xy=(mdup[2], vdup[2]), xytext=(1.5, 44.8),
                   fontsize=7.2, color=E.ANTES, linespacing=1.25,
                   ha="left", va="top",
                   arrowprops=dict(arrowstyle="-", color=E.ANTES, lw=0.8,
                                   shrinkA=1, shrinkB=4,
                                   connectionstyle="arc3,rad=-0.25"))
    ax_b1.axhline(media_med, color=E.DESPUES, ls=(0, (4, 2)), lw=1.6, zorder=5)
    ax_b1.text(59.5, media_med + 0.55,
               f"media de las 30 muestras: {E.fmt_miles(media_med, 2)} kW",
               ha="right", va="bottom", fontsize=7.2, color=E.DESPUES,
               zorder=6, bbox=dict(facecolor="white", edgecolor="none",
                                   alpha=0.88, pad=1.4))
    ax_b1.text(1, 23.0, "las lecturas repetidas son idénticas al bit",
               fontsize=6.9, style="italic", color="#555555",
               ha="left", va="bottom")
    ax_b1.set_ylim(22, 45.5)
    ax_b1.set_yticks([25, 30, 35, 40])
    ax_b1.set_ylabel("Potencia activa (kW)", fontsize=8)
    ax_b1.set_title(f"Medidor: {len(crudo)} filas, {len(fundida)} instantes",
                    fontsize=8.2, pad=6)

    # ── Zona B2: la hora en el inversor ─────────────────────────────────
    minutos_i = [(t - H0).total_seconds() / 60 for t in inv.index]
    ax_b2.plot(minutos_i, inv.values, color="#CCCCCC", lw=0.7, zorder=2)
    ax_b2.scatter(minutos_i, inv.values, s=14, color=E.NEUTRO, zorder=3)
    ax_b2.axhline(media_inv, color=E.DESPUES, ls=(0, (4, 2)), lw=1.6, zorder=5)
    ax_b2.text(59.5, media_inv + 55,
               f"media: {E.fmt_miles(media_inv)} W\n"
               f"entre mil: {E.fmt_miles(media_inv / 1000, 3)} kW",
               ha="right", va="bottom", fontsize=7.2, color=E.DESPUES,
               linespacing=1.25, zorder=6,
               bbox=dict(facecolor="white", edgecolor="none",
                         alpha=0.88, pad=1.4))
    ax_b2.text(1, 3350, "ninguna lectura es negativa: el recorte no actúa",
               fontsize=6.9, style="italic", color="#555555",
               ha="left", va="bottom")
    ax_b2.set_ylim(3300, 5500)
    ax_b2.set_yticks([3500, 4000, 4500, 5000])
    E.eje_espanol(ax_b2, "y", "miles")
    ax_b2.set_ylabel("Potencia de corriente alterna (W)", fontsize=8)
    ax_b2.set_title(f"Inversor: {len(inv)} lecturas (W)", fontsize=8.2, pad=6)

    for ax in (ax_b1, ax_b2):
        ax.set_xlim(-2, 62)
        ax.set_xticks([0, 15, 30, 45, 60])
        ax.set_xticklabels(["13:00", "13:15", "13:30", "13:45", "14:00"],
                           fontsize=7.4)
        ax.set_xlabel("Hora de la lectura", fontsize=8)
        ax.tick_params(axis="y", labelsize=7.4)

    # ── Zonas C: el aterrizaje en la serie del día ──────────────────────
    for ax, serie, valor, tope, tks, titulo, dec in (
            (ax_c1, dia_d, media_med, 46, [0, 20, 40],
             "La serie horaria del medidor", 2),
            (ax_c2, dia_g, media_inv / 1000, 13, [0, 5, 10],
             "La serie horaria del inversor", 2)):
        colores = [E.DESPUES if h == 13 else E.APOYO for h in range(24)]
        ax.bar(range(24), serie.values, width=0.8, color=colores, zorder=3)
        ax.text(13, valor + tope * 0.06, E.fmt_miles(valor, dec),
                ha="center", va="bottom", fontsize=7, color=E.DESPUES,
                zorder=6, bbox=dict(facecolor="white", edgecolor="none",
                                    alpha=0.88, pad=1.2))
        ax.set_ylim(0, tope)
        ax.set_yticks(tks)
        ax.set_xlim(-1, 24)
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xlabel("Hora del día", fontsize=8)
        ax.set_ylabel("Potencia media (kW)", fontsize=8)
        ax.set_title(titulo, fontsize=8.2, pad=5)
        ax.tick_params(labelsize=7.4)

    _rotulo_cobertura(fig, "m1", y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.95))

    # El lazo entre la hora ampliada y su lugar en el día no se dibuja
    # con flechas: cruzarían los rótulos de eje y los títulos de abajo.
    # Lo cierra la barra resaltada, que lleva la misma cifra y el mismo
    # color que la línea de la media del panel de encima.

    # ── El rastro ────────────────────────────────────────────────────────
    filas = []
    for s in tramos_med:
        filas.append(dict(zona="tramo_medidor", instante=s.index[0].isoformat(),
                          fin=s.index[-1].isoformat(), valor="", unidad="kW",
                          n_lecturas=len(s)))
    for s in tramos_inv:
        filas.append(dict(zona="archivo_inversor", instante=s.index[0].isoformat(),
                          fin=s.index[-1].isoformat(), valor="", unidad="W",
                          n_lecturas=len(s)))
    for t, v in fundida.items():
        filas.append(dict(zona="medidor_2min", instante=t.isoformat(), fin="",
                          valor=round(float(v), 6), unidad="kW",
                          n_lecturas=int(conteo.loc[t])))
    for t, v in inv.items():
        filas.append(dict(zona="inversor_2min", instante=t.isoformat(), fin="",
                          valor=float(v), unidad="W", n_lecturas=1))
    for t, v in dia_d.items():
        filas.append(dict(zona="serie_horaria_medidor", instante=t.isoformat(),
                          fin="", valor=round(float(v), 6), unidad="kW",
                          n_lecturas=""))
    for t, v in dia_g.items():
        filas.append(dict(zona="serie_horaria_inversor", instante=t.isoformat(),
                          fin="", valor=round(float(v), 6), unidad="kW",
                          n_lecturas=""))

    print(f"  [f3.1] hora {H0}: {len(crudo)} filas -> {len(fundida)} instantes "
          f"-> {media_med:.6f} kW  |  inversor {media_inv:.1f} W -> "
          f"{media_inv/1000:.3f} kW  |  sin fundir daría {media_cruda:.6f} kW")

    return E.guardar(
        fig, "f3_01_archivo_a_serie_m1", datos=pd.DataFrame(filas),
        procedencia=[
            "MedicionesMTE_v3/UCC/electricMeter/Medidor 1 - UCC - electricMeter/"
            " (3 CSV, columna totalActivePower)",
            "MedicionesMTE_v3/UCC/inverter/Fronius - UCC - inverter/"
            " (columna acPower)",
            "reformateo/documento/datos_cache/preproceso_m1.npz"
            " (verificacion de los dos valores horarios)",
            "pipeline: data/preprocessing.py + data/xm_data_loader.py",
        ])


# ─────────────────────────────────────────────────────────────────────────────
def f32_demanda_negativa(cobertura: str = "m1"):
    """
    F3.2 — La demanda que el medidor entrega en negativo.

    Dos paneles. Izquierda: el perfil medio por hora del día de las cinco
    instituciones tal como sale del medidor, con la franja bajo cero
    sombreada. Derecha: cuántas horas cae bajo cero cada institución y en
    qué hora del día ocurre.

    El argumento de la figura es que el valor negativo no es ruido: se
    concentra al mediodía, que es exactamente cuando el sol produce. Un
    medidor que resta la generación antes de reportar no está midiendo la
    demanda del edificio, y por eso hay que revertir la resta.
    """
    series, horas = D.preproceso(cobertura)
    resumen = D.conteo_negativas(cobertura)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.8),
                                   gridspec_kw={"width_ratios": [1.2, 1]})

    filas = []
    minimo_perfil = 0.0
    for inst in E.ORDEN_INSTITUCIONES:
        s = series[f"{inst}__D_raw"]
        perfil = s.groupby(s.index.hour).mean()
        minimo_perfil = min(minimo_perfil, float(perfil.min()))
        ax1.plot(perfil.index, perfil.values, color=E.color_institucion(inst),
                 label=E.etiqueta_institucion(inst), linewidth=1.6)
        for h, v in perfil.items():
            filas.append({"institucion": inst, "hora": h, "D_raw_media_kW": v})

    ax1.axhline(0, color="#333333", linewidth=1.0)
    lo, hi = ax1.get_ylim()
    # Techo ampliado: la leyenda va dentro del eje y sin este margen se
    # imprimiría encima del pico de la institución más cargada.
    hi = hi + 0.42 * (hi - lo)
    pie = []
    if minimo_perfil < 0:
        # Suelo ampliado también: el rótulo de la banda va dentro de ella,
        # y si la banda termina justo donde termina la curva, el rótulo se
        # imprime encima de la curva que pretende explicar.
        lo = lo - 0.42 * (hi - lo)
        ax1.axhspan(lo, 0, color=E.ANTES, alpha=0.10, zorder=0)
        ax1.text(11.5, (lo + minimo_perfil) / 2,
                 "zona imposible: la demanda\nde un edificio no es negativa",
                 ha="center", va="center", fontsize=7.2, color=E.ANTES,
                 style="italic", linespacing=1.35)
    else:
        # En M3 ningún perfil medio cae bajo cero, aunque sí lo hagan
        # horas sueltas. Decirlo evita que el lector concluya que en esta
        # cobertura el fenómeno no existe. Va al pie y no dentro del eje:
        # con las cinco curvas apoyadas en el suelo no queda hueco.
        pie.append("Ningún perfil medio cae bajo cero en esta cobertura; "
                   "las horas negativas son sueltas (panel derecho).")
    ax1.set_ylim(lo, hi)
    ax1.set_xlabel("Hora del día")
    ax1.set_ylabel("Demanda del medidor (kW)")
    ax1.set_title("Perfil medio tal como llega del medidor", pad=8)
    ax1.set_xticks(range(0, 24, 3))
    ax1.legend(ncol=3, loc="upper left", fontsize=7, columnspacing=1.0,
               handlelength=1.4, handletextpad=0.5)

    # Panel derecho: cuántas horas bajo cero, y con qué tipo de medidor
    r = resumen.set_index("institucion").reindex(E.ORDEN_INSTITUCIONES)
    colores = [E.ANTES if n > 0 else E.NEUTRO for n in r["horas_negativas"]]
    ax2.barh(range(len(r)), r["horas_negativas"], color=colores, height=0.62)
    ax2.set_yticks(range(len(r)))
    ax2.set_yticklabels([f"{E.etiqueta_institucion(i)}\n"
                         f"(medidor {TIPO_ES.get(t, t)})"
                         for i, t in zip(r.index, r["tipo_medidor"])],
                        fontsize=7.2)
    ax2.invert_yaxis()
    ax2.set_xlabel("Horas con demanda negativa (de 6.144)")
    ax2.set_title("Alcance del problema por institución", pad=8)
    E.eje_espanol(ax2, "x", "miles")

    tope = max(r["horas_negativas"].max(), 1)
    anomalas = []
    for i, (n, mn, t, rec) in enumerate(zip(
            r["horas_negativas"], r["min_D_raw_kW"], r["tipo_medidor"],
            r["horas_reconstruidas"])):
        if n > 0:
            ax2.text(n + tope * 0.04, i,
                     f"{E.fmt_miles(n)} h  ·  mín {E.fmt_miles(mn, 1)} kW",
                     va="center", fontsize=7.2, color=E.ANTES)
            if t == "gross":
                anomalas.append((r.index[i], int(n), int(rec)))
        else:
            ax2.text(tope * 0.04, i, "sin negativos", va="center",
                     fontsize=7.2, color=E.NEUTRO, style="italic")
    ax2.set_xlim(0, tope * 1.78)

    # Un medidor declarado bruto que aun asi entrega horas negativas es
    # una contradiccion aparente, y el lector la ve en la figura. No es un
    # error de la figura: en esa cobertura el pipeline no reconstruye ese
    # medidor, sino que recorta las horas a cero. Se declara al pie.
    for inst, n, rec in anomalas:
        pie.append(
            f"{E.etiqueta_institucion(inst)} conserva {E.fmt_miles(n)} h bajo "
            f"cero pese a estar declarada como medidor bruto en esta "
            f"cobertura: el pipeline\nno la reconstruye "
            f"({E.fmt_miles(rec)} h reconstruidas) y esas horas se recortan "
            f"a cero.")
    if pie:
        fig.text(0.5, -0.03, "\n".join(pie), ha="center", va="top",
                 fontsize=6.8, color="#555555", style="italic",
                 linespacing=1.45)

    _rotulo_cobertura(fig, cobertura)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    return E.guardar(
        fig, f"f3_02_demanda_negativa_{cobertura}",
        datos=pd.DataFrame(filas).merge(
            r.reset_index()[["institucion", "tipo_medidor", "horas_negativas",
                             "min_D_raw_kW"]], on="institucion"),
        procedencia=[
            "MedicionesMTE_v3/ (medidores de demanda, columna totalActivePower)",
            "reformateo/documento/datos_cache/preproceso_%s.npz" % cobertura,
            "pipeline: data/preprocessing.py::build_demand_generation",
        ])


# ─────────────────────────────────────────────────────────────────────────────
def f33_reconstruccion(cobertura: str = "m1", institucion: str = "Udenar",
                       dia: str = "2025-07-16"):
    """
    F3.3 — La reconstrucción net→bruta: antes y después.

    La figura estrella del documento. Muestra sobre un día concreto qué
    entrega el medidor (que baja a valores negativos al mediodía), qué
    generaron los inversores que ese medidor había descontado, y qué
    demanda resulta al devolverle esa generación.

    El panel derecho generaliza a las 6.144 h con el perfil medio, para
    que no quede la duda de si el día elegido es representativo.
    """
    series, horas = D.preproceso(cobertura)
    resumen = D.conteo_negativas(cobertura).set_index("institucion")

    D_raw = series[f"{institucion}__D_raw"]
    G_rec = series[f"{institucion}__G_recon"]
    D_rec = series[f"{institucion}__D_recon"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.7))

    # ── Panel izquierdo: un día, hora a hora ────────────────────────────
    d0, d1 = pd.Timestamp(dia), pd.Timestamp(dia) + pd.Timedelta(days=1)
    sl = slice(d0, d1 - pd.Timedelta(hours=1))
    x = np.arange(24)
    dr, gr, dd = D_raw[sl].values, G_rec[sl].values, D_rec[sl].values

    ax1.axhline(0, color="#333333", linewidth=1.0, zorder=3)
    ax1.fill_between(x, 0, gr, color=E.APOYO, alpha=0.85, zorder=1,
                     label="Generación que el medidor había restado")
    ax1.plot(x, dr, color=E.ANTES, linewidth=1.9, zorder=4,
             label="Antes: lectura del medidor")
    ax1.plot(x, dd, color=E.DESPUES, linewidth=1.9, zorder=5,
             label="Después: demanda reconstruida")

    bajo = dr < 0
    if bajo.any():
        ax1.fill_between(x, dr, 0, where=bajo, color=E.ANTES, alpha=0.22,
                         zorder=2, interpolate=True)
        # La flecha apunta al mínimo real del día, que es donde el
        # argumento se ve con más claridad. El texto va abajo a la
        # derecha: a partir de la caída de la tarde la lectura vuelve a
        # ser positiva y ese cuadrante queda libre, mientras que abajo a
        # la izquierda el texto se imprimía encima de la propia curva.
        h_min = int(np.nanargmin(dr))
        lo1, hi1 = ax1.get_ylim()
        ax1.set_ylim(lo1 - 0.16 * (hi1 - lo1), hi1)
        ax1.annotate("el medidor reporta\nmenos energía\nde la que el\n"
                     "edificio gastó",
                     xy=(h_min, dr[h_min]),
                     xytext=(0.99, 0.02), textcoords="axes fraction",
                     fontsize=7.2, color=E.ANTES, ha="right", va="bottom",
                     linespacing=1.35,
                     arrowprops=dict(arrowstyle="->", color=E.ANTES, lw=0.9,
                                     connectionstyle="arc3,rad=0.2"))

    dia_ts = pd.Timestamp(dia)
    ax1.set_xlabel("Hora del día")
    ax1.set_ylabel("Potencia (kW)")
    ax1.set_title(f"Un día: {E.etiqueta_institucion(institucion)}, "
                  f"{DIAS_ES[dia_ts.weekday()]} "
                  f"{dia_ts.day} de {MESES_LARGOS[dia_ts.month - 1]} "
                  f"de {dia_ts.year}", pad=8)
    ax1.set_xticks(range(0, 24, 3))

    # ── Panel derecho: el horizonte completo ────────────────────────────
    p_raw = D_raw.groupby(D_raw.index.hour).mean()
    p_rec = D_rec.groupby(D_rec.index.hour).mean()
    p_gen = G_rec.groupby(G_rec.index.hour).mean()

    ax2.axhline(0, color="#333333", linewidth=1.0, zorder=3)
    ax2.fill_between(p_gen.index, 0, p_gen.values, color=E.APOYO, alpha=0.85,
                     zorder=1)
    ax2.plot(p_raw.index, p_raw.values, color=E.ANTES, linewidth=1.9, zorder=4)
    ax2.plot(p_rec.index, p_rec.values, color=E.DESPUES, linewidth=1.9, zorder=5)
    ax2.set_xlabel("Hora del día")
    ax2.set_ylabel("Potencia media (kW)")
    ax2.set_title("Las 6.144 h: perfil medio por hora", pad=8)
    ax2.set_xticks(range(0, 24, 3))

    n_neg = int(resumen.loc[institucion, "horas_negativas"])
    mn = float(resumen.loc[institucion, "min_D_raw_kW"])
    dif = (D_rec.sum() - D_raw.fillna(0).sum())
    # Se ancla abajo a la izquierda: es la única zona del panel que las
    # tres series dejan libre (la caída de la lectura ocupa el centro).
    ax2.text(0.02, 0.04,
             f"{E.fmt_miles(n_neg)} h bajo cero\n"
             f"mínimo {E.fmt_miles(mn, 1)} kW\n"
             f"devueltos {E.fmt_miles(dif)} kWh",
             transform=ax2.transAxes, ha="left", va="bottom", fontsize=7.2,
             linespacing=1.35,
             bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                       edgecolor=E.NEUTRO, linewidth=0.6, alpha=0.95))

    # La leyenda es común a los dos paneles y va fuera de los ejes: dentro
    # del panel izquierdo tapaba el máximo del área de generación, que es
    # justo la magnitud cuyo tamaño explica la caída de la lectura.
    fig.legend(*ax1.get_legend_handles_labels(), loc="lower center",
               bbox_to_anchor=(0.5, -0.05), ncol=3, fontsize=7.2,
               frameon=False, columnspacing=1.6, handlelength=1.8)

    _rotulo_cobertura(fig, cobertura)
    fig.tight_layout(rect=(0, 0, 1, 0.955))

    tabla = pd.DataFrame({
        "hora": p_raw.index,
        "D_medidor_kW": p_raw.values,
        "G_restada_kW": p_gen.values,
        "D_reconstruida_kW": p_rec.values,
    })
    return E.guardar(
        fig, f"f3_03_reconstruccion_{cobertura}", datos=tabla,
        procedencia=[
            f"MedicionesMTE_v3/{institucion}/ (medidor de demanda e inversores)",
            f"reformateo/documento/datos_cache/preproceso_{cobertura}.npz",
            "regla: D = max(0, D_net + suma de inversores) — data/preprocessing.py",
        ])


# ─────────────────────────────────────────────────────────────────────────────
def f35_outliers_imputacion(cobertura: str = "m1"):
    """
    F3.5/F3.6 — Lo que la limpieza marca y lo que rellena.

    Panel izquierdo: la serie de una institución con los valores atípicos
    señalados y el umbral dibujado, para que se vea que el criterio no
    recorta picos operativos legítimos. Panel derecho: cuántas horas
    quedaron imputadas por mes en cada institución.
    """
    series, horas = D.preproceso(cobertura)
    resumen = D.conteo_negativas(cobertura).set_index("institucion")

    # Para el panel izquierdo se elige la institución con más atípicos;
    # si ninguna tiene, se muestra la de mayor imputación.
    r = resumen.reindex(E.ORDEN_INSTITUCIONES)
    inst = (r["outliers_D"].idxmax() if r["outliers_D"].max() > 0
            else r["imputadas_D"].idxmax())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.5))

    s = series[f"{inst}__D_recon"]
    out = series[f"{inst}__mask_out_D"].astype(bool)
    umbral = float(resumen.loc[inst, "umbral_outlier_D_kW"])

    ax1.plot(s.index, s.values, color=E.NEUTRO, linewidth=0.5, alpha=0.85,
             label="Demanda reconstruida")
    if np.isfinite(umbral):
        ax1.axhline(umbral, color=E.ALERTA, linewidth=1.1, linestyle="--",
                    label=f"Umbral: {E.fmt_miles(umbral, 1)} kW")
    if out.any():
        ax1.scatter(s.index[out], s[out], s=22, color=E.ANTES, zorder=5,
                    label=f"Atípicos: {E.fmt_miles(int(out.sum()))} h",
                    edgecolors="white", linewidths=0.4)
    ax1.set_ylabel("Demanda (kW)")
    ax1.set_xlabel("Mes de 2025")
    ax1.set_title(f"Criterio de atípicos: {E.etiqueta_institucion(inst)}",
                  pad=8)
    # Techo ampliado y leyenda a la derecha: los atípicos están sobre el
    # umbral y a la izquierda del eje, que es justo donde la leyenda se
    # imprimía antes. Tapaba los cuatro puntos que la figura existe para
    # enseñar.
    lo1, hi1 = ax1.get_ylim()
    ax1.set_ylim(lo1, hi1 + 0.30 * (hi1 - lo1))
    ax1.legend(loc="upper right", fontsize=7)
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax1.xaxis.set_major_formatter(
        FuncFormatter(lambda v, _: MESES_ES[mdates.num2date(v).month - 1]))
    ax1.tick_params(axis="x", labelsize=7)

    # Panel derecho: imputación por mes
    meses = None
    matriz = []
    for i in E.ORDEN_INSTITUCIONES:
        imp = series[f"{i}__mask_imp_D"].astype(bool)
        por_mes = imp.groupby(imp.index.to_period("M")).sum()
        meses = por_mes.index
        matriz.append(por_mes.values)
    matriz = np.array(matriz, dtype=float)

    im = ax2.imshow(matriz, aspect="auto", cmap="YlOrBr", vmin=0)
    ax2.set_xticks(range(len(meses)))
    # Nombre corto de mes: con «04/25 … 12/25» las nueve etiquetas se
    # solapaban entre sí y con el rótulo del eje.
    ax2.set_xticklabels([_mes_es(m) for m in meses], fontsize=7)
    ax2.set_yticks(range(len(E.ORDEN_INSTITUCIONES)))
    ax2.set_yticklabels([E.etiqueta_institucion(i)
                         for i in E.ORDEN_INSTITUCIONES], fontsize=7.5)
    ax2.set_xlabel("Mes de 2025")
    ax2.set_title(f"Horas imputadas por mes  ·  "
                  f"{E.fmt_miles(matriz.sum())} h en total", pad=8)
    ax2.grid(False)
    corte = 0.62 * matriz.max() if matriz.max() else 1
    for i in range(matriz.shape[0]):
        for j in range(matriz.shape[1]):
            v = int(matriz[i, j])
            if v:
                # Sobre las celdas más oscuras el gris de siempre era
                # ilegible; el texto se aclara donde el relleno se oscurece.
                ax2.text(j, i, str(v), ha="center", va="center", fontsize=6.2,
                         color="white" if matriz[i, j] > corte else "#333333")
    cb = fig.colorbar(im, ax=ax2, fraction=0.045, pad=0.03)
    cb.set_label("Horas imputadas", fontsize=7.5)
    cb.ax.tick_params(labelsize=7)

    _rotulo_cobertura(fig, cobertura)
    fig.tight_layout(rect=(0, 0, 1, 0.955))

    tabla = pd.DataFrame(matriz, index=E.ORDEN_INSTITUCIONES,
                         columns=[str(m) for m in meses]
                         ).reset_index(names="institucion")
    return E.guardar(
        fig, f"f3_05_outliers_imputacion_{cobertura}", datos=tabla,
        procedencia=[
            f"reformateo/documento/datos_cache/preproceso_{cobertura}.npz",
            "criterio: max(Q75 + 5*IQR, P99,5 * 1,2) — data/xm_data_loader.py::_clean",
        ])


# ─────────────────────────────────────────────────────────────────────────────
def f37_matrices(cobertura: str = "m1"):
    """
    F3.7 — Lo que el modelo recibe finalmente.

    Las dos matrices que salen del pipeline, dibujadas como mapas de hora
    del día contra día del horizonte. La generación traza una banda diurna
    nítida que sigue el arco solar; la demanda muestra la semana laboral
    en franjas verticales.

    Es la comprobación visual de que el resultado del preprocesamiento
    tiene la estructura que debe tener: si la banda solar apareciera de
    noche, o la semana no se distinguiera, habría un error de zona horaria
    o de alineación temporal.
    """
    series, horas = D.preproceso(cobertura)
    dem = sum(series[f"{i}__D_limpia"] for i in D.AGENTES)
    gen = sum(series[f"{i}__G_limpia"] for i in D.AGENTES)

    fig, axes = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.6))
    filas = []
    for ax, (serie, nom, cmap) in zip(axes, ((dem, "Demanda", "Greys"),
                                             (gen, "Generación", "YlOrBr"))):
        base = serie.index.normalize()
        m = pd.DataFrame({"v": serie.values, "h": serie.index.hour,
                          "d": (base - base[0]).days})
        piv = m.pivot_table(index="h", columns="d", values="v", aggfunc="mean")
        # vmin=0 fija el origen de la escala de color. Sin él, el cero de
        # la generación nocturna y la carga base nocturna de la demanda
        # —que no es cero, sino decenas de kilovatios— se pintaban del
        # mismo tono claro, y el mapa sugería que de noche no hay consumo.
        im = ax.imshow(piv.values, aspect="auto", origin="lower", cmap=cmap,
                       vmin=0, extent=[0, piv.shape[1], 0, 24])

        # Marcas mensuales: «día 137 del horizonte» no le dice nada a
        # nadie, y sin calendario no se puede leer el receso de julio ni
        # el cierre de diciembre que la propia figura enseña.
        inicio = base[0]
        meses = list(pd.date_range(inicio.normalize(), base[-1], freq="MS"))
        # El horizonte arranca el día 4, de modo que abril no tiene marca
        # de primero de mes: sin este tick el eje parecería empezar en mayo.
        ticks = [0] + [(f - inicio).days for f in meses]
        etiquetas = [MESES_ES[inicio.month - 1]] + [MESES_ES[f.month - 1]
                                                    for f in meses]
        ax.set_xticks(ticks)
        ax.set_xticklabels(etiquetas, fontsize=7)
        ax.set_xlim(0, piv.shape[1])
        ax.set_xlabel("Mes de 2025")
        ax.set_ylabel("Hora del día")
        ax.set_yticks(range(0, 25, 6))
        ax.set_title(f"{nom} de la comunidad  ·  máx "
                     f"{E.fmt_miles(np.nanmax(piv.values))} kW", pad=8)
        ax.grid(False)
        cb = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
        cb.set_label("Potencia media horaria (kW)", fontsize=7)
        cb.ax.tick_params(labelsize=7)
        for h in piv.index:
            filas.append({"magnitud": nom, "hora": int(h),
                          "media_kW": float(piv.loc[h].mean())})

    # Las dos escalas de color son independientes, y hay que decirlo: el
    # mismo tono oscuro vale 150 kW en un panel y 57 en el otro, de modo
    # que comparar la intensidad de un panel con la del otro no significa
    # nada. Lo comparable es la estructura, que es a lo que va la figura.
    fig.text(0.5, -0.035,
             "Cada panel lleva su propia escala de color, indicada en su "
             "barra: los tonos no son comparables entre paneles.",
             ha="center", va="top", fontsize=7, color="#555555",
             style="italic")

    _rotulo_cobertura(fig, cobertura)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    return E.guardar(fig, f"f3_07_matrices_{cobertura}",
                     datos=pd.DataFrame(filas),
                     procedencia=[f"reformateo/documento/datos_cache/"
                                  f"preproceso_{cobertura}.npz"])


# ─────────────────────────────────────────────────────────────────────────────
def f38_perfiles_instituciones(cobertura: str = "m1"):
    """
    F3.8 — Cinco ritmos distintos.

    Perfil medio de demanda y generación de cada institución. Aunque
    comparten ciudad y clima, no comparten rutina: un hospital no se
    parece a un campus universitario, y esa diferencia es justamente la
    que hace posible el intercambio.
    """
    series, _ = D.preproceso(cobertura)
    fig, axes = plt.subplots(2, 3, figsize=(E.ANCHO_COMPLETO, 4.2), sharex=True)
    filas = []
    for ax, inst in zip(axes.ravel(), D.AGENTES):
        d = series[f"{inst}__D_limpia"]
        g = series[f"{inst}__G_limpia"]
        pdm = d.groupby(d.index.hour).mean()
        pgm = g.groupby(g.index.hour).mean()
        ax.fill_between(pgm.index, 0, pgm.values, color=E.MECANISMOS["C5"],
                        alpha=0.30)
        ax.plot(pgm.index, pgm.values, color=E.MECANISMOS["C5"], linewidth=1.4)
        ax.plot(pdm.index, pdm.values, color=E.color_institucion(inst),
                linewidth=1.6)
        # El porcentaje es la razón entre lo generado y lo consumido POR EL
        # CIRCUITO MEDIDO. Sin el rótulo «G/D» el lector lo lee como
        # autosuficiencia de la institución, y en M3 aparecen valores por
        # encima del 100 % que con esa lectura no tendrían sentido.
        cob_pct = 100 * g.sum() / d.sum() if d.sum() else float("nan")
        ax.set_title(f"{E.etiqueta_institucion(inst)}  ·  "
                     f"G/D = {E.fmt_miles(cob_pct, 0)} %", pad=5,
                     color=E.color_institucion(inst), fontsize=8.5)
        ax.set_xticks(range(0, 24, 6))
        for h in pdm.index:
            filas.append({"institucion": inst, "hora": int(h),
                          "demanda_kW": pdm[h], "generacion_kW": pgm[h]})

    # El sexto panel resume la comunidad completa.
    ax = axes.ravel()[5]
    dt = sum(series[f"{i}__D_limpia"] for i in D.AGENTES)
    gt = sum(series[f"{i}__G_limpia"] for i in D.AGENTES)
    pdt = dt.groupby(dt.index.hour).mean()
    pgt = gt.groupby(gt.index.hour).mean()
    ax.fill_between(pgt.index, 0, pgt.values, color=E.MECANISMOS["C5"], alpha=0.30)
    ax.plot(pgt.index, pgt.values, color=E.MECANISMOS["C5"], linewidth=1.4,
            label="Generación fotovoltaica")
    ax.plot(pdt.index, pdt.values, color="black", linewidth=1.7,
            label="Demanda (en el color de cada institución)")
    ax.set_title(f"Comunidad  ·  "
                 f"G/D = {E.fmt_miles(100 * gt.sum() / dt.sum(), 0)} %",
                 pad=5, fontsize=8.5)
    ax.set_xticks(range(0, 24, 6))

    for ax in axes[1, :]:
        ax.set_xlabel("Hora del día")
    for ax in axes[:, 0]:
        ax.set_ylabel("Potencia media (kW)")

    # La leyenda va al pie de la figura: dentro del sexto panel se
    # imprimía sobre la curva de demanda de la comunidad.
    fig.legend(*axes.ravel()[5].get_legend_handles_labels(),
               loc="lower center", bbox_to_anchor=(0.5, -0.055), ncol=2,
               fontsize=7.2, frameon=False, columnspacing=2.0,
               handlelength=1.8)
    # Sin esta advertencia, comparar el tamaño del área verde entre
    # paneles induce a error: la UCC llega a 37 kW y CESMAG a 8, y las
    # dos ocupan el mismo alto de panel.
    fig.text(0.5, -0.10,
             "Cada panel tiene su propia escala vertical: lo comparable "
             "entre ellos es la forma del perfil, no su altura.",
             ha="center", va="top", fontsize=7, color="#555555",
             style="italic")

    _rotulo_cobertura(fig, cobertura)
    fig.tight_layout(rect=(0, 0, 1, 0.945))
    return E.guardar(fig, f"f3_08_perfiles_instituciones_{cobertura}",
                     datos=pd.DataFrame(filas),
                     procedencia=[f"reformateo/documento/datos_cache/"
                                  f"preproceso_{cobertura}.npz"])


# ─────────────────────────────────────────────────────────────────────────────
def f39_ritmos(cobertura: str = "m1"):
    """
    F3.9 y F3.10 — El ritmo semanal y el anual.

    A la izquierda, día hábil frente a fin de semana: la demanda cae pero
    la generación no, de modo que el excedente disponible para intercambio
    es mayor precisamente cuando hay menos gente en los edificios. A la
    derecha, el recorrido a lo largo del horizonte, que en esta latitud
    varía poco pero no nada.
    """
    series, _ = D.preproceso(cobertura)
    dem = sum(series[f"{i}__D_limpia"] for i in D.AGENTES)
    gen = sum(series[f"{i}__G_limpia"] for i in D.AGENTES)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.3))
    filas = []
    for nombre, mascara, trazo in (("Día hábil", dem.index.weekday < 5, "-"),
                                   ("Fin de semana", dem.index.weekday >= 5, "--")):
        pdm = dem[mascara].groupby(dem[mascara].index.hour).mean()
        pgm = gen[mascara].groupby(gen[mascara].index.hour).mean()
        ax1.plot(pdm.index, pdm.values, trazo, color=E.NEUTRO, linewidth=1.7,
                 label=f"Demanda · {nombre.lower()}")
        ax1.plot(pgm.index, pgm.values, trazo, color=E.MECANISMOS["C5"],
                 linewidth=1.7, label=f"Generación · {nombre.lower()}")
        for h in pdm.index:
            filas.append({"corte": nombre, "hora": int(h),
                          "demanda_kW": pdm[h], "generacion_kW": pgm[h]})
    habil, finde = dem.index.weekday < 5, dem.index.weekday >= 5
    caida = 100 * (1 - dem[finde].mean() / dem[habil].mean())
    # «La generación no cambia» es una afirmación medible, y hay que
    # medirla antes de escribirla: entre día hábil y fin de semana la
    # media varía lo que diga este número, no cero.
    var_gen = 100 * (gen[finde].mean() / gen[habil].mean() - 1)
    signo = "sube" if var_gen >= 0 else "baja"
    # Techo ampliado: la anotación va dentro del eje y sin margen se
    # imprimía sobre el pico de la demanda de día hábil.
    lo1, hi1 = ax1.get_ylim()
    ax1.set_ylim(lo1, hi1 + 0.22 * (hi1 - lo1))
    ax1.text(0.03, 0.97,
             f"la demanda cae {E.fmt_miles(caida, 1)} % el fin de semana;\n"
             f"la generación apenas cambia "
             f"({signo} {E.fmt_miles(abs(var_gen), 1)} %)",
             transform=ax1.transAxes, va="top", fontsize=7.2,
             linespacing=1.35)
    ax1.set_xlabel("Hora del día")
    ax1.set_ylabel("Potencia media (kW)")
    ax1.set_title("Ritmo semanal", pad=8)
    ax1.set_xticks(range(0, 24, 3))

    med_g = gen.groupby(gen.index.to_period("M")).mean()
    med_d = dem.groupby(dem.index.to_period("M")).mean()
    x = np.arange(len(med_g))
    ax2.plot(x, med_d.values, marker="o", markersize=3.4, color=E.NEUTRO,
             linewidth=1.6, label="Demanda")
    ax2.plot(x, med_g.values, marker="s", markersize=3.4,
             color=E.MECANISMOS["C5"], linewidth=1.6, label="Generación")
    ax2.set_xticks(x)
    ax2.set_xticklabels([_mes_es(p) for p in med_g.index], fontsize=7)
    ax2.set_xlabel("Mes de 2025")
    ax2.set_ylabel("Potencia media (kW)")
    # Desde cero: con el eje arrancando en el mínimo, una serie que va de
    # 8,3 a 13,2 kW parece desplomarse, y la comparación entre las dos
    # magnitudes —que es de lo que trata el panel— queda deformada.
    ax2.set_ylim(0, max(med_d.max(), med_g.max()) * 1.18)
    ax2.set_title("Recorrido a lo largo del horizonte", pad=8)
    ax2.legend(fontsize=7.5, loc="upper right", ncol=2)
    for p, vd, vg in zip(med_g.index, med_d.values, med_g.values):
        filas.append({"corte": "mensual", "hora": str(p),
                      "demanda_kW": vd, "generacion_kW": vg})

    # La leyenda del panel izquierdo son cuatro entradas largas y ninguna
    # esquina del eje las admite sin cruzar una curva: van al pie.
    fig.legend(*ax1.get_legend_handles_labels(), loc="lower center",
               bbox_to_anchor=(0.5, -0.09), ncol=2, fontsize=7,
               frameon=False, columnspacing=2.2, handlelength=2.2)

    _rotulo_cobertura(fig, cobertura)
    fig.tight_layout(rect=(0, 0, 1, 0.945))
    return E.guardar(fig, f"f3_09_ritmos_{cobertura}", datos=pd.DataFrame(filas),
                     procedencia=[f"reformateo/documento/datos_cache/"
                                  f"preproceso_{cobertura}.npz"])


if __name__ == "__main__":
    D.verificar_canon()
    print("\nCapítulo 3 — la domesticación del dato")
    verificar_inversores()
    f31_archivo_a_serie()
    for cob in ("m1", "m3"):
        f32_demanda_negativa(cob)
    f33_reconstruccion("m1", "Udenar")
    for cob in ("m1", "m3"):
        f37_matrices(cob)
        f38_perfiles_instituciones(cob)
        f39_ritmos(cob)
    for cob in ("m1", "m3"):
        f35_outliers_imputacion(cob)
    print("\nlisto.")
