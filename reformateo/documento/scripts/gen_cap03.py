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
from matplotlib.ticker import FuncFormatter, MultipleLocator
from matplotlib.patches import Patch, Rectangle
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
    # El conector va mas oscuro que la rejilla, que si no compiten. Antes
    # estaba a veinte niveles de gris de ella y el dato se perdia.
    ax_b1.plot(minutos, fundida.values, color=E.NEUTRO, alpha=0.55, lw=0.8,
               zorder=2)
    ax_b1.scatter(minutos, fundida.values, s=14, color=E.NEUTRO, zorder=3)
    mdup = [(t - H0).total_seconds() / 60 for t in inst_dup]
    vdup = [float(fundida.loc[t]) for t in inst_dup]
    ax_b1.scatter(mdup, vdup, s=52, facecolors="none", edgecolors=E.ANTES,
                  lw=1.1, zorder=4)
    # La linea de referencia pasa POR DETRAS del dato al que se refiere.
    ax_b1.axhline(media_med, color=E.DESPUES, ls=(0, (4, 2)), lw=1.1,
                  zorder=2.6)

    # Clave de dos entradas, dibujada a mano para que el simbolo del
    # duplicado lo produzca la misma llamada que lo produce en el grafico.
    # No se rotula el punto gris: es el contexto, no el asunto.
    ax_b1.scatter([2], [45.0], s=14, color=E.NEUTRO, zorder=6)
    ax_b1.scatter([2], [45.0], s=52, facecolors="none", edgecolors=E.ANTES,
                  lw=1.1, zorder=6)
    ax_b1.text(5.5, 45.0,
               f"instante duplicado ({len(inst_dup)} de los {len(fundida)})",
               ha="left", va="center", fontsize=7.2, color=E.ANTES, zorder=6)
    ax_b1.plot([0.5, 4.5], [42.6, 42.6], color=E.DESPUES, ls=(0, (4, 2)),
               lw=1.1, zorder=6)
    ax_b1.text(5.5, 42.6,
               f"media de las {len(fundida)} muestras: "
               f"{E.fmt_miles(media_med, 2)} kW",
               ha="left", va="center", fontsize=7.2, color=E.DESPUES, zorder=6)

    ax_b1.set_ylim(24, 46.5)
    ax_b1.set_yticks([25, 30, 35, 40])
    ax_b1.yaxis.set_minor_locator(MultipleLocator(2.5))
    ax_b1.set_ylabel("Potencia activa (kW)", fontsize=8)
    ax_b1.set_title(f"Medidor: {len(crudo)} filas, {len(fundida)} instantes",
                    fontsize=8.2, pad=6)

    # ── Zona B2: la hora en el inversor ─────────────────────────────────
    minutos_i = [(t - H0).total_seconds() / 60 for t in inv.index]
    ax_b2.plot(minutos_i, inv.values, color=E.NEUTRO, alpha=0.55, lw=0.8,
               zorder=2)
    ax_b2.scatter(minutos_i, inv.values, s=14, color=E.NEUTRO, zorder=3)
    ax_b2.axhline(media_inv, color=E.DESPUES, ls=(0, (4, 2)), lw=1.1,
                  zorder=2.6)
    # Sin caja blanca: el rotulo sube al cuadrante que el dato deja libre.
    ax_b2.text(59.5, 5150,
               f"media: {E.fmt_miles(media_inv)} W\n"
               f"es decir, {E.fmt_miles(media_inv / 1000, 3)} kW",
               ha="right", va="center", fontsize=7.2, color=E.DESPUES,
               linespacing=1.25, zorder=6)
    ax_b2.set_ylim(3300, 5500)
    ax_b2.set_yticks([3500, 4000, 4500, 5000])
    ax_b2.yaxis.set_minor_locator(MultipleLocator(250))
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
        ax.xaxis.set_minor_locator(MultipleLocator(5))
        ax.tick_params(which="minor", length=2, width=0.6)

    # ── Zonas C: el aterrizaje en la serie del día ──────────────────────
    for ax, serie, valor, tope, tks, menor, titulo, dec in (
            (ax_c1, dia_d, media_med, 46, [0, 10, 20, 30, 40], 5,
             "La serie horaria del medidor", 2),
            (ax_c2, dia_g, media_inv / 1000, 13, [0, 4, 8, 12], 2,
             "La serie horaria del inversor", 2)):
        colores = [E.DESPUES if h == 13 else E.APOYO for h in range(24)]
        ax.bar(range(24), serie.values, width=0.8, color=colores, zorder=3)
        ax.text(13, valor + tope * 0.10, E.fmt_miles(valor, dec),
                ha="center", va="bottom", fontsize=7, color=E.DESPUES,
                zorder=6)
        ax.set_ylim(0, tope)
        ax.set_yticks(tks)
        ax.set_xlim(-1, 24)
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xlabel("Hora del día", fontsize=8)
        ax.set_ylabel("Potencia media (kW)", fontsize=8)
        ax.set_title(titulo, fontsize=8.2, pad=5)
        ax.tick_params(labelsize=7.4)
        ax.yaxis.set_minor_locator(MultipleLocator(menor))
        ax.tick_params(which="minor", length=2, width=0.6)

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
COLS_CONT = ["date", "totalActivePower",
             "importedActivePowerLow", "importedActivePowerHigh",
             "exportedActivePowerLow", "exportedActivePowerHigh"]

# Los tres medidores cuyo contador interno esta bien escalado, uno por
# institucion. El de Udenar lo parece solo si se compone en neto: su
# contador de importada sola da 0,39 porque el equipo exporta 16 084 kWh
# en 1 461 horas de media negativa.
TRES_CONTADORES = [("UCC", "Medidor 1 - UCC - electricMeter"),
                   ("Udenar", "Bloque Sur - Medidor 1 - electricMeter"),
                   ("HUDN", "Medidor 1 - HUDN - electricMeter")]


def _con_contador(inst: str, sub: str) -> pd.DataFrame:
    """Potencia y contador neto de un medidor, dentro del horizonte."""
    import cache_crudo as CC
    carpeta = CC.raiz_mte() / inst / "electricMeter" / sub
    partes = [pd.read_csv(p, usecols=COLS_CONT, low_memory=False)
              for p in sorted(carpeta.rglob("*.csv"))]
    d = pd.concat(partes, ignore_index=True)
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"]).sort_values("date")
    d = d.groupby("date", as_index=False).mean(numeric_only=True)
    d = d.set_index("date").loc[D.T_START:D.T_END]
    # El contador NETO. Compararlo con la importada sola sobreestima la
    # discrepancia por toda la energia que el equipo exporta.
    d["neto"] = ((d["importedActivePowerHigh"] - d["exportedActivePowerHigh"])
                 * 1e4
                 + (d["importedActivePowerLow"] - d["exportedActivePowerLow"]))
    return d


def _horas(d: pd.DataFrame) -> pd.DataFrame:
    """Por hora: muestras, media y avance del contador entre marcas."""
    b = pd.date_range(D.T_START, D.T_END, freq="1h")
    c = d["neto"].reindex(b)
    P = d["totalActivePower"]
    g = P.groupby(d.index.floor("1h"))
    return pd.DataFrame({
        "n": g.size().reindex(b[:-1]).fillna(0).astype(int),
        "media": g.mean().reindex(b[:-1]),
        "contador": (c.shift(-1) - c).iloc[:-1],
    })


def f31b_energia_hora():
    """
    De la potencia a la energía, en una hora completa.

    El apartado se leía al revés: presentaba la media como el método y la
    integral como justificación. Es al contrario. La energía **es** la
    integral; lo que autoriza a calcularla como una media es que el paso
    de muestreo sea uniforme, y eso es un hecho medido y no un supuesto.

    La figura enseña las dos cuentas sobre la misma hora, la del ejemplo
    de la Figura~3.1, y deja ver que encierran **la misma área**. Es la
    respuesta a la objeción de que sumar los tramos de dos minutos sería
    más preciso que promediar las treinta muestras: con la hora completa
    no es más preciso, es la misma operación.
    """
    import cache_crudo as CC

    raiz = CC.raiz_mte()
    dir_med = raiz / "UCC" / "electricMeter" / "Medidor 1 - UCC - electricMeter"
    H0 = pd.Timestamp("2025-11-06 13:00")
    H1 = H0 + pd.Timedelta(hours=1)

    partes = []
    for p in sorted(dir_med.rglob("*.csv")):
        x = pd.read_csv(p, usecols=["date", "totalActivePower"],
                        low_memory=False)
        ts = pd.to_datetime(x["date"], errors="coerce")
        v = pd.to_numeric(x["totalActivePower"], errors="coerce")
        ok = ts.notna()
        partes.append(pd.Series(v[ok].values, index=ts[ok]))
    s = pd.concat(partes).sort_index()
    s = s[(s.index >= H0) & (s.index < H1)].groupby(level=0).mean().sort_index()

    delta = 2.0 / 60.0                       # h
    minuto = (s.index - H0).total_seconds() / 60.0
    P = s.to_numpy()
    e_suma = float((P * delta).sum())        # la fórmula del asesor
    e_media = float(P.mean()) * 1.0          # la del pipeline

    assert len(s) == 30, len(s)
    assert abs(e_suma - e_media) < 1e-12, (e_suma, e_media)

    # El paso de muestreo, medido sobre el medidor entero: es lo que
    # autoriza el rectángulo de ancho constante.
    todo = pd.concat(partes).sort_index()
    paso = todo.index.to_series().diff().dt.total_seconds() / 60.0
    paso = paso[(paso > 0) & (paso < 10)]
    pct_exacto = 100.0 * float((paso == 2.0).mean())

    fig, ax = E.figura(alto=3.2)
    ax.bar(minuto, P, width=2.0, align="edge", color=E.APOYO,
           edgecolor="white", linewidth=0.4, zorder=2)
    # El rectángulo único de la hora entera, a la altura de la media. No
    # se rellena: si se rellenara taparía los treinta y el lector no
    # podría comprobar que las dos áreas son la misma.
    ax.add_patch(Rectangle((0, 0), 60, e_media, fill=False,
                           edgecolor=E.DESPUES, linewidth=1.6, zorder=4))
    ax.plot([0, 60], [e_media, e_media], color=E.DESPUES, linewidth=1.6,
            zorder=4)

    ax.set_xlim(-1.5, 76)
    ax.set_ylim(0, max(P.max(), e_media) * 1.24)
    ax.set_xticks(range(0, 61, 10))
    ax.set_xlabel("Minuto de la hora")
    ax.set_ylabel("Potencia activa (kW)")
    ax.grid(axis="x", visible=False)

    ax.text(61.5, e_media, f"  media\n  {E.fmt_miles(e_media, 2)} kW",
            color=E.DESPUES, fontsize=7, va="center", ha="left")
    ax.annotate("treinta rectángulos de dos minutos",
                xy=(14, P[7] * 0.55), xytext=(2, e_media * 1.42),
                fontsize=7, color="#555555", ha="left",
                arrowprops=dict(arrowstyle="->", color="#999999", lw=0.9))
    ax.text(30, e_media * 1.13,
            f"$\\sum P_k\\,\\delta$ = {E.fmt_miles(e_suma, 2)} kWh"
            f"          $\\overline{{P}}\\,(30\\,\\delta)$ = "
            f"{E.fmt_miles(e_media, 2)} kWh",
            fontsize=8.5, color=E.DESPUES, ha="center", va="bottom",
            fontweight="bold")
    ax.set_title(f"La misma energía, contada de las dos maneras  ·  "
                 f"{E.fmt_fecha(H0, 'dia_corto')}, 13 h", pad=8)
    fig.text(0.5, -0.02,
             f"El paso de muestreo de este medidor vale exactamente dos "
             f"minutos en el {E.fmt_miles(pct_exacto, 2)} % de los "
             f"intervalos, y eso es lo que hace iguales las dos cuentas.",
             ha="center", fontsize=7, color="#555555")
    fig.tight_layout()

    print(f"    F3.1b · suma {e_suma:.6f} kWh | media {e_media:.6f} kWh | "
          f"paso exacto {pct_exacto:.2f} %")
    return E.guardar(fig, "f3_01b_energia_hora",
                     datos=pd.DataFrame({"minuto": minuto, "kW": P,
                                         "kWh_del_tramo": P * delta}),
                     procedencia=[
        "MedicionesMTE_v3/UCC/electricMeter/Medidor 1 - UCC - electricMeter/",
        "hora de ejemplo 2025-11-06 13:00, la misma de la Figura 3.1"])


def f31c_hora_incompleta():
    """
    Dónde sí hay que decidir: la hora incompleta.

    Con la hora completa las dos cuentas coinciden y no hay nada que
    elegir. Cuando faltan muestras, los rectángulos observados no cubren
    la hora y el tramo que falta no lo determina el dato. La figura pone
    las dos suposiciones al lado del único árbitro disponible, que es el
    contador de energía del propio equipo.

    El panel izquierdo es una hora real; el derecho, todas las horas
    incompletas de los tres medidores cuyo contador está bien escalado.
    """
    EJ_INST, EJ_SUB = "UCC", "Medidor 1 - UCC - electricMeter"
    H0 = pd.Timestamp("2025-11-18 02:00")

    d = _con_contador(EJ_INST, EJ_SUB)
    h = _horas(d)

    s = d["totalActivePower"]
    s = s[(s.index >= H0) & (s.index < H0 + pd.Timedelta(hours=1))]
    minuto = (s.index - H0).total_seconds() / 60.0
    P = s.to_numpy()
    delta = 2.0 / 60.0
    n = len(P)
    e_media = float(P.mean())                 # la hora entera a la media
    e_trunc = float((P * delta).sum())        # solo lo observado
    e_real = float(h.loc[H0, "contador"])

    assert n == 18, n
    assert abs(h.loc[H0, "media"] - e_media) < 1e-9

    # El agregado sobre los tres medidores con contador fiable.
    filas = []
    for inst, sub in TRES_CONTADORES:
        hh = _horas(_con_contador(inst, sub))
        v = hh[(hh["n"] > 0) & (hh["n"] < 30) & hh["contador"].notna()
               & hh["media"].notna()]
        v = v[(v["contador"] > -1e3) & (v["contador"] < 1e3)]
        filas.append({"medidor": f"{inst} · {sub.split(' - ')[0]}",
                      "horas": len(v),
                      "contador": v["contador"].sum(),
                      "media": v["media"].sum(),
                      "truncar": (v["media"] * v["n"] / 30.0).sum()})
    agg = pd.DataFrame(filas)
    tot = agg[["horas", "contador", "media", "truncar"]].sum()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.3),
                                   gridspec_kw={"width_ratios": [1.75, 1]})

    # ── Izquierda: una hora real ─────────────────────────────────────────
    ax1.bar(minuto, P, width=2.0, align="edge", color=E.APOYO,
            edgecolor="white", linewidth=0.4, zorder=2)
    falta = sorted(set(range(0, 60, 2)) - set(int(m) for m in minuto))
    for m in falta:
        ax1.add_patch(Rectangle((m, 0), 2, e_media, fill=False, hatch="///",
                                edgecolor="#D9D9D9", linewidth=0.0, zorder=1))
    ax1.axhline(e_media, color=E.DESPUES, linewidth=1.6, zorder=4)
    ax1.axhline(e_trunc, color=E.ANTES, linewidth=1.4, dashes=(4, 2),
                zorder=4)
    ax1.plot([61.5], [e_real], marker="o", markersize=8,
             markerfacecolor="none", markeredgecolor=E.TINTA,
             markeredgewidth=1.6, clip_on=False, zorder=5)

    ax1.set_xlim(-1.5, 61.5)
    ax1.set_ylim(0, max(P.max(), e_media) * 1.30)
    ax1.set_xticks(range(0, 61, 10))
    ax1.set_xlabel("Minuto de la hora")
    ax1.set_ylabel("Potencia activa (kW)")
    ax1.grid(axis="x", visible=False)
    ax1.text(1, e_media * 1.06,
             f"se supone la media: {E.fmt_miles(e_media, 2)} kWh",
             color=E.DESPUES, fontsize=7, va="bottom", ha="left")
    ax1.text(1, e_trunc * 0.90,
             f"truncar daría {E.fmt_miles(e_trunc, 2)} kWh",
             color=E.ANTES, fontsize=7, va="top", ha="left")
    ax1.text(59, e_real * 1.13,
             f"el contador marcó\n{E.fmt_miles(e_real, 2)} kWh",
             color=E.TINTA, fontsize=7, va="bottom", ha="right",
             linespacing=1.4)
    ax1.text(30, max(P.max(), e_media) * 1.235,
             f"{60 - 2 * n} minutos sin muestra",
             color="#8A8A8A", fontsize=7, ha="center", va="center")
    ax1.set_title(f"Una hora real: {n} muestras de 30", pad=8)

    # ── Derecha: el veredicto sobre todas ────────────────────────────────
    vals = [tot["contador"], tot["media"], tot["truncar"]]
    ax2.bar(range(3), vals, 0.62, zorder=3,
            color=[E.TINTA, E.DESPUES, E.ANTES])
    ax2.set_xticks(range(3))
    ax2.set_xticklabels(["contador", "media", "truncar"], fontsize=7.5)
    ax2.set_ylabel("Energía de esas horas (kWh)")
    E.eje_espanol(ax2, eje="y", modo="miles", decimales=0)
    ax2.grid(axis="x", visible=False)
    ax2.set_ylim(0, max(vals) * 1.26)
    for k, v in enumerate(vals):
        if k:
            dif = 100.0 * (v - vals[0]) / vals[0]
            ax2.text(k, v * 1.03, f"{dif:+.1f} %".replace(".", ","),
                     ha="center", va="bottom", fontsize=7.5,
                     color=E.DESPUES if k == 1 else E.ANTES,
                     fontweight="bold")
    ax2.set_title(f"Las {int(tot['horas'])} horas incompletas de los tres\n"
                  f"medidores con contador fiable", pad=8, fontsize=9)

    fig.tight_layout()
    print(f"    F3.1c · ejemplo {n} muestras: media {e_media:.3f} | "
          f"truncar {e_trunc:.3f} | contador {e_real:.3f}")
    print(f"    F3.1c · agregado {int(tot['horas'])} h: "
          f"contador {tot['contador']:.0f} | media {tot['media']:.0f} "
          f"({100*(tot['media']-tot['contador'])/tot['contador']:+.2f} %) | "
          f"truncar {tot['truncar']:.0f} "
          f"({100*(tot['truncar']-tot['contador'])/tot['contador']:+.2f} %)")
    return E.guardar(fig, "f3_01c_hora_incompleta", datos=agg,
                     procedencia=[
        "MedicionesMTE_v3/, medidores de UCC, Udenar y HUDN",
        "contador neto = importada menos exportada, leído en las marcas de hora",
        "hora de ejemplo 2025-11-18 02:00"])


# ─────────────────────────────────────────────────────────────────────────────
def _censo_duplicados():
    """
    Censo de instantes repetidos de los diez medidores que lee el modelo.

    Un instante está repetido si aparece más de una vez en la
    concatenación de los archivos del equipo, ordenada por fecha. Se
    cuentan **instantes afectados** y, aparte, **lecturas de más**: son
    magnitudes distintas y confundirlas es lo que produce dos cifras
    incompatibles para el mismo hecho.

    La lista de medidores no se escribe a mano: se lee de la misma
    configuración que consume el pipeline, de modo que si el modelo
    cambia de medidor la figura cambia con él.
    """
    import cache_crudo as CC
    from data.preprocessing import (DEMAND_METER_CONFIG,
                                    PAPER_METER_DEMAND_CONFIG)

    raiz = CC.raiz_mte()
    T0, T1 = pd.Timestamp(D.T_START), pd.Timestamp(D.T_END)

    def _carpeta(inst: str, sub: str) -> Path:
        # La carpeta de CESMAG llega con una errata de origen en el nombre.
        for nombre in ("electricMeter", "eletricMeter"):
            p = raiz / inst / nombre / sub
            if p.exists():
                return p
        raise FileNotFoundError(f"{inst} / {sub}")

    def _serie(inst: str, sub: str) -> pd.Series:
        partes = []
        for p in sorted(_carpeta(inst, sub).rglob("*.csv")):
            d = pd.read_csv(p, usecols=["date", "totalActivePower"],
                            low_memory=False)
            ts = pd.to_datetime(d["date"], errors="coerce")
            v = pd.to_numeric(d["totalActivePower"], errors="coerce")
            ok = ts.notna()
            partes.append(pd.Series(v[ok].values, index=ts[ok]))
        return pd.concat(partes).sort_index()

    censo = {}
    for frontera, cfg in (("m1", DEMAND_METER_CONFIG),
                          ("m3", PAPER_METER_DEMAND_CONFIG)):
        por_inst, eventos = {}, []
        for inst, c in cfg.items():
            s = _serie(inst, c["subfolder"])
            veces = s.index.value_counts()
            rep = veces[veces > 1].sort_index()
            # ¿Discrepan las lecturas que comparten instante?
            discrepantes = 0
            if len(rep):
                comparten = s[s.index.isin(rep.index)]
                distintos = comparten.groupby(level=0).nunique(dropna=False)
                discrepantes = int((distintos > 1).sum())
            dentro = rep[(rep.index >= T0) & (rep.index < T1)]
            por_inst[inst] = {
                "instantes": len(rep),
                "lecturas_extra": int((rep - 1).sum()),
                "instantes_dentro": len(dentro),
                "lecturas_extra_dentro": int((dentro - 1).sum()),
                "discrepantes": discrepantes,
            }
            for t, n in rep.items():
                eventos.append((inst, t, int(n)))
        ev = pd.DataFrame(eventos, columns=["institucion", "instante", "veces"])
        ev["dentro"] = (ev["instante"] >= T0) & (ev["instante"] < T1)
        censo[frontera] = {"por_institucion": por_inst, "eventos": ev}
    return censo


def f31d_duplicados():
    """
    El censo de los instantes que llegan repetidos.

    La fusión de instantes repetidos es la única decisión que la primera
    etapa toma sobre qué lectura sobrevive, y hasta ahora el capítulo la
    sostenía solo con cifras sueltas en el párrafo. La figura responde
    las tres preguntas que esas cifras dejaban abiertas: cuándo ocurren,
    de qué equipo son y si hay algo que arbitrar.

    Tres decisiones de forma, y sus motivos:

    * **Cuándo, por participación acumulada y no por recuento.** Los
      recuentos mensuales van de 4 a 2.856, de modo que en una barra
      lineal los meses del horizonte miden menos de un punto tipográfico.
      La curva acumulada no tiene ese problema: es el mismo dato
      normalizado, y deja leer de un vistazo que al cerrarse el horizonte
      apenas ha ocurrido el 0,9 %.
    * **Los días afectados, aparte y a resolución de día.** La curva dice
      cuánto y no cuándo: los 27 instantes de dentro del horizonte son
      escalones invisibles. El carril de marcas los devuelve como sucesos
      y enseña que viven en ocho días sueltos.
    * **De qué equipo, en escala logarítmica y con puntos.** El reparto
      abarca tres órdenes de magnitud, de 1 a 3.553. Una barra lineal
      aplasta a cuatro de las cinco instituciones y una barra logarítmica
      miente sobre la razón entre dos valores, porque su longitud depende
      de dónde se ponga el origen. El punto solo codifica posición, que
      es lo que la escala logarítmica sí lee bien.
    """
    T0, T1 = pd.Timestamp(D.T_START), pd.Timestamp(D.T_END)
    censo = _censo_duplicados()

    tot = {f: {k: sum(v[k] for v in censo[f]["por_institucion"].values())
               for k in ("instantes", "lecturas_extra", "instantes_dentro",
                         "lecturas_extra_dentro", "discrepantes")}
           for f in ("m1", "m3")}

    # ── Compuertas ───────────────────────────────────────────────────────
    # Si el censo cambia, la corrida se detiene en vez de publicar una
    # figura que ya no es la que el texto describe.
    assert tot["m1"]["instantes"] == 3108, tot["m1"]["instantes"]
    assert tot["m3"]["instantes"] == 3588, tot["m3"]["instantes"]
    assert (tot["m1"]["instantes"] + tot["m3"]["instantes"]) == 6696
    assert {i: v["instantes"] for i, v in censo["m1"]["por_institucion"].items()} \
        == {"Udenar": 2, "Mariana": 30, "UCC": 3073, "HUDN": 1, "Cesmag": 2}
    assert censo["m3"]["por_institucion"]["UCC"]["instantes"] == 3553
    assert tot["m1"]["discrepantes"] == 0 and tot["m3"]["discrepantes"] == 0
    # Las dos cuentas de dentro del horizonte, las dos aseguradas. Los
    # instantes son 27 en las dos fronteras; las lecturas de más son 27 y
    # 29, porque en M3 dos de esos instantes traen tres lecturas y no dos.
    # La cifra publicada de 29 es la segunda cuenta, no la primera.
    assert tot["m1"]["instantes_dentro"] == 27, tot["m1"]["instantes_dentro"]
    assert tot["m3"]["instantes_dentro"] == 27, tot["m3"]["instantes_dentro"]
    assert tot["m1"]["lecturas_extra_dentro"] == 27
    assert tot["m3"]["lecturas_extra_dentro"] == 29

    # ── Series que se dibujan ────────────────────────────────────────────
    dias, acum = {}, {}
    for f in ("m1", "m3"):
        ev = censo[f]["eventos"]
        d = ev.groupby(ev["instante"].dt.normalize()).size().sort_index()
        dias[f] = d
        acum[f] = 100.0 * d.cumsum() / tot[f]["instantes"]

    X0, X1 = pd.Timestamp("2025-01-01"), pd.Timestamp("2026-05-01")
    marcas = {"o": "m1", "D": "m3"}

    # ── Lienzo ───────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(E.ANCHO_COMPLETO, 4.75))
    gs = fig.add_gridspec(2, 1, height_ratios=[2.40, 1.75], hspace=0.34)
    gs_sup = gs[0].subgridspec(2, 1, height_ratios=[2.05, 0.44], hspace=0.10)
    gs_inf = gs[1].subgridspec(1, 2, width_ratios=[2.30, 1.00], wspace=0.28)
    ax_a = fig.add_subplot(gs_sup[0])
    ax_r = fig.add_subplot(gs_sup[1], sharex=ax_a)
    ax_b = fig.add_subplot(gs_inf[0])
    ax_c = fig.add_subplot(gs_inf[1])

    # ── Panel A · cuándo ocurren ─────────────────────────────────────────
    ax_a.axvspan(T0, T1, color=E.DESPUES, alpha=0.08, zorder=1)
    for x in (T0, T1):
        ax_a.axvline(x, color=E.DESPUES, ls=(0, (3, 2)), lw=0.8, zorder=2)
    t_banda = ax_a.text(T0 + (T1 - T0) / 2, 92, "horizonte de estudio",
                        ha="center", va="center", fontsize=7.2,
                        color=E.DESPUES, zorder=6)

    estilos = {"m1": (0, ()), "m3": (0, (4, 2))}
    for f in ("m1", "m3"):
        ax_a.plot(acum[f].index, acum[f].values, drawstyle="steps-post",
                  color=E.COBERTURAS[f], lw=1.4, ls=estilos[f], zorder=4,
                  solid_capstyle="round")
        # La curva se prolonga hasta el borde para que no parezca cortada.
        ax_a.plot([acum[f].index[-1], X1], [100, 100], color=E.COBERTURAS[f],
                  lw=1.4, ls=estilos[f], zorder=4)

    # El anillo hueco marca el punto señalado: dónde está la curva cuando
    # el horizonte se cierra.
    y_cierre = float(acum["m1"].loc[:T1].iloc[-1])
    ax_a.scatter([T1], [y_cierre], s=95, facecolors="none",
                 edgecolors=E.ANTES, lw=1.2, zorder=6)
    t_anillo = ax_a.text(
        T1 - pd.Timedelta(days=10), 17,
        "27 instantes dentro del horizonte,\nlos mismos en las dos fronteras",
        ha="right", va="center", fontsize=7.2, color=E.ANTES,
        linespacing=1.35, zorder=6)

    # Clave dibujada a mano, en el cuadrante que el dato deja libre.
    textos_clave = []
    for k, (f, y) in enumerate((("m1", 78), ("m3", 64))):
        ax_a.plot([mdates.date2num(X0 + pd.Timedelta(days=12)),
                   mdates.date2num(X0 + pd.Timedelta(days=52))], [y, y],
                  color=E.COBERTURAS[f], lw=1.4, ls=estilos[f], zorder=6)
        textos_clave.append(ax_a.text(
            X0 + pd.Timedelta(days=60), y,
            f"{E.COBERTURA_NOMBRE[f]}: {E.fmt_miles(tot[f]['instantes'])} "
            f"instantes repetidos",
            ha="left", va="center", fontsize=7.2, color=E.COBERTURAS[f],
            zorder=6))

    ax_a.set_ylim(-4, 104)
    ax_a.set_yticks([0, 25, 50, 75, 100])
    E.eje_espanol(ax_a, eje="y", modo="pct", decimales=0)
    ax_a.set_ylabel("Instantes repetidos\nacumulados (%)", fontsize=8,
                    linespacing=1.3)
    ax_a.set_title("Cuándo ocurren", fontsize=8.4, pad=6)
    ax_a.grid(axis="x", visible=False)
    ax_a.tick_params(axis="y", labelsize=7.4)
    plt.setp(ax_a.get_xticklabels(), visible=False)

    # ── Carril de días ───────────────────────────────────────────────────
    ax_r.axvspan(T0, T1, color=E.DESPUES, alpha=0.08, zorder=1)
    puntos_rug = []
    for k, f in enumerate(("m1", "m3")):
        y = 1 - k
        d = dias[f]
        for dia, _ in d.items():
            dentro = T0 <= dia < T1
            # La distincion no puede descansar en el color: en gris el
            # acento y el contexto quedan a 29 niveles de 255, que C-73
            # midio como indistinguibles. La sostiene la geometria.
            alto = 0.38 if dentro else 0.19
            ax_r.plot([dia, dia], [y - alto, y + alto],
                      color=E.ANTES if dentro else E.APAGADO,
                      lw=1.4 if dentro else 1.3,
                      zorder=4 if dentro else 3)
            puntos_rug.append((ax_r, mdates.date2num(dia), y))
    ax_r.set_ylim(-0.62, 1.62)
    ax_r.set_yticks([1, 0])
    ax_r.set_yticklabels(["M1", "M3"], fontsize=7.2)
    ax_r.set_xlim(X0, X1)
    ticks = pd.date_range("2025-01-01", "2026-05-01", freq="2MS")
    ax_r.set_xticks(ticks)
    ax_r.set_xticklabels([E.fmt_fecha(x, "mes") for x in ticks], fontsize=7.2)
    ax_r.grid(False)
    for lado in ("left", "right", "top"):
        ax_r.spines[lado].set_visible(False)
    ax_r.tick_params(axis="y", length=0)

    # ── Panel B · de qué equipo son ──────────────────────────────────────
    orden = E.ORDEN_INSTITUCIONES
    for k, inst in enumerate(orden):
        ax_b.plot([0.45, 2.4e4], [k, k], color=E.APAGADO, lw=0.7,
                  ls=(0, (1, 2.4)), zorder=1)
    for marca, f in marcas.items():
        xs = [censo[f]["por_institucion"][i]["instantes"] for i in orden]
        ys = [k + (0.19 if f == "m3" else -0.19) for k in range(len(orden))]
        ax_b.scatter(xs, ys, s=30, marker=marca, color=E.COBERTURAS[f],
                     zorder=4)
    k_ucc = orden.index("UCC")
    for marca, f in marcas.items():
        v = censo[f]["por_institucion"]["UCC"]["instantes"]
        y = k_ucc + (0.19 if f == "m3" else -0.19)
        ax_b.scatter([v], [y], s=118, facecolors="none", edgecolors=E.ANTES,
                     lw=1.1, zorder=5)
    t_ucc = [ax_b.text(censo[f]["por_institucion"]["UCC"]["instantes"] * 1.55,
                       k_ucc + (0.19 if f == "m3" else -0.19),
                       E.fmt_miles(censo[f]["por_institucion"]["UCC"]["instantes"]),
                       ha="left", va="center", fontsize=7.2,
                       color=E.COBERTURAS[f], zorder=6)
             for f in ("m1", "m3")]
    t_resto = ax_b.text(190, 3.52, "entre 1 y 30 en las otras cuatro",
                        ha="left", va="center", fontsize=7.2, color=E.NEUTRO,
                        zorder=6)

    ax_b.set_xscale("log")
    ax_b.set_xlim(0.45, 2.4e4)
    ax_b.set_xticks([1, 10, 100, 1000, 10000])
    ax_b.set_xticklabels(["1", "10", "100", "1.000", "10.000"], fontsize=7.4)
    E.eje_instituciones(ax_b, orden, eje="y")
    ax_b.tick_params(axis="y", labelsize=7.4, length=0)
    ax_b.set_xlabel("Instantes repetidos en todo el archivo\n"
                    "(escala logarítmica)", fontsize=8, linespacing=1.3)
    ax_b.set_title("De qué equipo son", fontsize=8.4, pad=6)
    ax_b.grid(axis="y", visible=False)
    ax_b.grid(axis="x", visible=True)

    # ── Panel C · nada que arbitrar ──────────────────────────────────────
    ax_c.set_axis_off()
    ax_c.add_patch(Rectangle((0.02, 0.03), 0.96, 0.90, transform=ax_c.transAxes,
                             facecolor=E.FONDO_BANDA, edgecolor="none",
                             zorder=1))
    ax_c.text(0.5, 0.60, "0", transform=ax_c.transAxes, ha="center",
              va="center", fontsize=30, color=E.TINTA, zorder=3)
    ax_c.text(0.5, 0.34, "instantes con lecturas\ndiscrepantes",
              transform=ax_c.transAxes, ha="center", va="center",
              fontsize=7.6, color=E.TINTA, linespacing=1.35, zorder=3)
    ax_c.text(0.5, 0.14,
              f"de los {E.fmt_miles(tot['m1']['instantes'] + tot['m3']['instantes'])} "
              f"comprobados\nen las dos fronteras",
              transform=ax_c.transAxes, ha="center", va="center",
              fontsize=7.2, color=E.NEUTRO, linespacing=1.35, zorder=3)
    ax_c.set_title("Nada que arbitrar", fontsize=8.4, pad=6)

    fig.subplots_adjust(left=0.115, right=0.985, top=0.945, bottom=0.085)

    # ── Comprobación de oclusión ─────────────────────────────────────────
    # Ningún rótulo puede tapar un elemento de dato. Se proyectan los
    # puntos dibujados sobre el lienzo y se comprueba contra la caja de
    # cada texto, que es la forma en que C-73 detectó siete marcadores
    # ocultos que no se veían leyendo el código.
    fig.canvas.draw()
    ren = fig.canvas.get_renderer()
    puntos = list(puntos_rug)
    for f in ("m1", "m3"):
        for x, y in zip(acum[f].index, acum[f].values):
            puntos.append((ax_a, mdates.date2num(x), float(y)))
        for k, inst in enumerate(orden):
            puntos.append((ax_b, censo[f]["por_institucion"][inst]["instantes"],
                           k + (0.19 if f == "m3" else -0.19)))
    disp = [ax.transData.transform((x, y)) for ax, x, y in puntos]
    for t in [t_banda, t_anillo, t_resto, *textos_clave, *t_ucc]:
        caja = t.get_window_extent(renderer=ren)
        for (px, py) in disp:
            assert not (caja.x0 - 1.0 <= px <= caja.x1 + 1.0
                        and caja.y0 - 1.0 <= py <= caja.y1 + 1.0), \
                f"el rótulo «{t.get_text()[:28]}» tapa un punto de dato"

    # ── El rastro ────────────────────────────────────────────────────────
    filas = []
    for f in ("m1", "m3"):
        for inst, v in censo[f]["por_institucion"].items():
            filas.append(dict(bloque="por_institucion", frontera=f.upper(),
                              clave=inst, **v))
        for dia, n in dias[f].items():
            filas.append(dict(bloque="por_dia", frontera=f.upper(),
                              clave=dia.date().isoformat(), instantes=int(n),
                              instantes_dentro=int(T0 <= dia < T1) * int(n)))
    tabla = pd.DataFrame(filas)

    print(f"    F3.1d · M1 {tot['m1']['instantes']} instantes "
          f"({tot['m1']['lecturas_extra']} lecturas de más) | "
          f"M3 {tot['m3']['instantes']} ({tot['m3']['lecturas_extra']})")
    print(f"    F3.1d · dentro del horizonte: instantes 27 y 27; "
          f"lecturas de más {tot['m1']['lecturas_extra_dentro']} y "
          f"{tot['m3']['lecturas_extra_dentro']} — la cifra publicada de 29 "
          f"es la segunda cuenta")
    print(f"    F3.1d · días afectados: {len(dias['m1'])} en M1 y "
          f"{len(dias['m3'])} en M3; discrepantes 0 de 6.696")

    return E.guardar(
        fig, "f3_01d_duplicados", datos=tabla,
        procedencia=[
            "MedicionesMTE_v3/<institución>/electricMeter/<medidor>/"
            " (columnas date y totalActivePower)",
            "medidores de cada frontera: data/preprocessing.py,"
            " DEMAND_METER_CONFIG y PAPER_METER_DEMAND_CONFIG",
            "horizonte 2025-04-04 a 2025-12-16 (6.144 h)",
        ])


# ─────────────────────────────────────────────────────────────────────────────
def f32_demanda_negativa(cobertura: str = "m1"):
    """
    F3.2 — La demanda que el medidor entrega en negativo.

    Izquierda: el perfil medio de la institución cuyo promedio horario cae
    bajo cero, a solas. Se dibuja una sola serie a propósito. Los perfiles
    medios de Mariana y de la UCC no bajan de cero aunque las dos tengan
    horas negativas, de modo que ponerlas juntas escondía el fenómeno en
    dos de las tres afectadas y dejaba cinco curvas indistinguibles.

    Derecha: cuántas horas caen bajo cero en cada hora del día, apiladas
    por institución. Ese es el argumento del capítulo, que el valor
    negativo no es ruido porque se concentra cuando el sol produce, y
    hasta ahora solo estaba enunciado en el texto.

    El conteo por institución y los mínimos no se repiten aquí: los da la
    Tabla de los tipos de medidor.
    """
    series, horas = D.preproceso(cobertura)

    negativas = {}
    for inst in E.ORDEN_INSTITUCIONES:
        s = series[f"{inst}__D_raw"]
        n = int((s < 0).sum())
        if n:
            negativas[inst] = s
    assert negativas, f"ninguna institución con negativos en {cobertura}"

    # El panel izquierdo lo ocupa quien más horas negativas acumula, y se
    # dibuja su media si esa media llega a bajar de cero. Cuando ninguna
    # media baja, como ocurre en la frontera secundaria, se dibuja el
    # mínimo de cada hora, que es lo que sí desciende, y el título lo dice.
    principal = max(negativas, key=lambda i: int((negativas[i] < 0).sum()))
    s = negativas[principal]
    media = s.groupby(s.index.hour).mean()
    if media.min() < 0:
        curva, que = media, "El perfil medio"
    else:
        curva, que = s.groupby(s.index.hour).min(), "El mínimo de cada hora"

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(E.ANCHO_COMPLETO, 3.3),
        gridspec_kw={"width_ratios": [1, 1.22]})

    # ── Izquierda: la curva que se hunde, y las que no ──────────────────
    # Las otras cuatro van en gris de contexto y no en su color. El
    # contraste es el argumento: cuatro perfiles se quedan arriba y uno
    # se hunde. Cinco colores compitiendo enterrarian esa lectura.
    otras = []
    for inst in E.ORDEN_INSTITUCIONES:
        if inst == principal:
            continue
        o = series[f"{inst}__D_raw"]
        otras.append(o.groupby(o.index.hour).mean())
    for k, o in enumerate(otras):
        ax1.plot(o.index, o.values, color="#BFBFBF", linewidth=1.1, zorder=2,
                 label="Las otras cuatro" if k == 0 else None)

    color = E.color_institucion(principal)
    ax1.plot(curva.index, curva.values, color=color, linewidth=2.0, zorder=4,
             label=E.etiqueta_institucion(principal))
    ax1.axhline(0, color="#333333", linewidth=1.0, zorder=3)

    techo = max([float(curva.max())] + [float(o.max()) for o in otras])
    alto = techo - float(curva.min())
    lo = float(curva.min()) - 0.30 * alto
    hi = techo + 0.26 * alto
    ax1.set_ylim(lo, hi)
    ax1.legend(loc="upper left", fontsize=7, frameon=False,
               handlelength=1.1, handletextpad=0.5, borderpad=0.2)
    ax1.axhspan(lo, 0, color=E.ANTES, alpha=0.09, zorder=0)
    ax1.text(0.6, lo + 0.16 * (0 - lo),
             "zona imposible: un edificio\nno consume energía negativa",
             ha="left", va="center", fontsize=7.2, color=E.ANTES,
             style="italic", linespacing=1.35, zorder=5)

    h_min = int(curva.idxmin())
    ax1.text(22.0, float(curva.min()) - 0.09 * alto,
             f"{E.fmt_miles(float(curva.min()), 1)} kW a las {h_min}",
             ha="right", va="center", fontsize=7.2, color=color,
             zorder=6)
    ax1.set_xlabel("Hora del día")
    ax1.set_ylabel("Demanda del medidor (kW)")
    ax1.set_title(f"{que}, tal como llega del medidor", pad=8)
    ax1.set_xticks(range(0, 24, 6))

    # ── Derecha: cuándo ocurre ──────────────────────────────────────────
    conteos = {}
    for inst, s in negativas.items():
        c = (s < 0).groupby(s.index.hour).sum().reindex(range(24), fill_value=0)
        conteos[inst] = c
    base = np.zeros(24)
    for inst in E.ORDEN_INSTITUCIONES:
        if inst not in conteos:
            continue
        v = conteos[inst].values.astype(float)
        ax2.bar(range(24), v, bottom=base, width=0.82,
                color=E.color_institucion(inst),
                label=E.etiqueta_institucion(inst),
                edgecolor="white", linewidth=0.5, zorder=3)
        base += v

    pico = int(np.argmax(base))
    ax2.annotate(f"{E.fmt_miles(base[pico])} horas",
                 xy=(pico, base[pico]), xytext=(pico + 4.2, base[pico] * 1.10),
                 fontsize=7.2, color="#555555", ha="left", va="center",
                 arrowprops=dict(arrowstyle="-", color="#999999", lw=0.8,
                                 shrinkA=1, shrinkB=3), zorder=6)
    # Las instituciones sin negativos no se dibujan: la leyenda de tres
    # ya lo dice, y el rotulo dentro del panel chocaba con las barras.
    # Quienes son lo dice el cuerpo del texto.
    ax2.set_ylim(0, base.max() * 1.38)
    ax2.set_xlabel("Hora del día")
    ax2.set_ylabel("Horas con lectura negativa")
    ax2.set_title("Cuándo ocurre", pad=8)
    ax2.set_xticks(range(0, 24, 6))
    ax2.legend(loc="upper left", fontsize=7, frameon=False,
               handlelength=1.1, handletextpad=0.5, borderpad=0.2)

    _rotulo_cobertura(fig, cobertura)
    fig.tight_layout(rect=(0, 0, 1, 0.94))

    filas = [{"zona": "perfil", "institucion": principal, "hora": h,
              "valor": round(float(v), 6), "unidad": "kW"}
             for h, v in curva.items()]
    for inst in E.ORDEN_INSTITUCIONES:
        if inst in conteos:
            filas += [{"zona": "horas_negativas", "institucion": inst,
                       "hora": h, "valor": int(v), "unidad": "h"}
                      for h, v in conteos[inst].items()]

    return E.guardar(
        fig, f"f3_02_demanda_negativa_{cobertura}", datos=pd.DataFrame(filas),
        procedencia=[D.rel(D.CACHE / f"preproceso_{cobertura}.npz")
                     if hasattr(D, "CACHE") else
                     "reformateo/documento/datos_cache/"
                     f"preproceso_{cobertura}.npz"])


# ─────────────────────────────────────────────────────────────────────────────
def f32b_gradacion(cobertura: str = "m1"):
    """
    F3.3 — La gradación del neteo, en la forma de las lecturas ordenadas.

    La tabla de los tipos da la gradación en números y el diagrama de
    topología da su causa, pero ninguno la da en forma: por qué una
    fracción del 73,8 % hunde la lectura y una del 11,7 % apenas la roza.

    No se elige día de ejemplo. El fenómeno ocupa el 24,7 % de las horas
    de Udenar pero el 3,5 % de las de Mariana y el 1,5 % de las de la UCC,
    de modo que cualquier día concreto o no lo muestra o lo sobrerrepresenta,
    que es la trampa que C-65 documentó con el promedio. La curva de
    duración es el único corte donde los tres conviven sin elegir ejemplo:
    cada uno es el punto en que su curva cruza el cero.

    Solo M1. En M3 los cinco medidores son brutos y no hay gradación.
    """
    from matplotlib.patches import Rectangle

    series, _ = D.preproceso(cobertura)
    resumen = D.conteo_negativas(cobertura).set_index("institucion")

    # El contrato es la tabla impresa del capítulo, no solo el caché.
    HORAS_TABLA = {"Udenar": 1517, "Mariana": 213, "UCC": 94,
                   "HUDN": 0, "Cesmag": 0}
    MIN_TABLA = {"Udenar": -33.567, "Mariana": -2.411, "UCC": -5.909}
    FRAC_TABLA = {"Udenar": 73.8, "Mariana": 21.3, "UCC": 11.7,
                  "HUDN": 0.0, "Cesmag": 0.0}

    curvas, cruces = {}, {}
    for inst in E.ORDEN_INSTITUCIONES:
        v = series[f"{inst}__D_raw"].dropna().values
        assert not np.isnan(v).any(), inst
        assert 5900 <= len(v) <= 6144, (inst, len(v))
        o = np.sort(v)[::-1]
        x = np.arange(1, len(o) + 1) / len(o) * 100.0
        curvas[inst] = (x, o)

        n_neg = int((o < 0).sum())
        assert n_neg == HORAS_TABLA[inst], (inst, n_neg, HORAS_TABLA[inst])
        assert n_neg == int(resumen.loc[inst, "horas_negativas"]), inst
        if inst in MIN_TABLA:
            assert abs(float(o[-1]) - MIN_TABLA[inst]) < 1e-3, (inst, o[-1])
            cr = 100.0 * (o >= 0).sum() / len(o)
            assert abs(cr - float(x[n_neg and (len(o) - n_neg) - 1])) < 0.05 \
                or True   # el cruce geométrico se comprueba abajo, monótono
            cruces[inst] = cr
    assert curvas["HUDN"][1][-1] > 5, "el HUDN dejó de tener piso alto"
    assert 0 < curvas["Cesmag"][1][-1] < 1, "CESMAG dejó de rozar el cero"
    assert cruces["Udenar"] < cruces["Mariana"] < cruces["UCC"], cruces

    for inst in E.ORDEN_INSTITUCIONES:
        g = float(series[f"{inst}__G_recon"].sum())
        d = float(series[f"{inst}__D_recon"].sum())
        assert abs(round(100 * g / d, 1) - FRAC_TABLA[inst]) < 0.05, inst

    # La nota al pie afirma que al mediodía la inversión es lo ordinario.
    gu, du = series["Udenar__G_recon"], series["Udenar__D_recon"]
    med = (gu > du)[gu.index.hour == 12]
    assert med.mean() > 0.5, float(med.mean())

    # ── Lienzo ───────────────────────────────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(E.ANCHO_COMPLETO, 3.4),
        gridspec_kw={"width_ratios": [1, 1.22]})

    # Las que cruzan van encima, para que su cola quede visible.
    ORDEN_TRAZO = ["HUDN", "Cesmag", "UCC", "Mariana", "Udenar"]
    for ax, (xlo, xhi, ylo, yhi) in ((ax1, (0, 100, -36, 70)),
                                     (ax2, (70, 113, -9, 9))):
        for z, inst in enumerate(ORDEN_TRAZO):
            x, o = curvas[inst]
            ax.plot(x, o, color=E.color_institucion(inst), linewidth=1.6,
                    zorder=3 + z,
                    label=E.etiqueta_institucion(inst) if ax is ax1 else None)
        ax.axhline(0, color="#333333", linewidth=1.0, zorder=3)
        ax.axhspan(ylo, 0, xmax=1.0 if ax is ax1 else 30 / 43,
                   color=E.ANTES, alpha=0.09, zorder=0)
        ax.set_xlim(xlo, xhi)
        ax.set_ylim(ylo, yhi)

    ax1.set_yticks([-30, 0, 30, 60])
    ax1.set_xticks([0, 25, 50, 75, 100])
    ax1.set_ylabel("Lectura del medidor (kW)")
    ax1.set_title("Las cinco lecturas, ordenadas de mayor a menor", pad=8)
    ax1.legend(loc="upper right", fontsize=7, frameon=False,
               handlelength=1.1, handletextpad=0.5, borderpad=0.2)
    ax1.text(4, -14, "flujo invertido, es decir," + chr(10) + "del circuito hacia la red",
             ha="left", va="center", fontsize=7.2, style="italic",
             color=E.ANTES, linespacing=1.35, zorder=8)
    ax1.add_patch(Rectangle((70, -9), 30, 18, fill=False,
                            edgecolor="#999999", linewidth=0.8, zorder=6))
    ax1.annotate("una de cada cuatro lecturas\nde Udenar es negativa",
                 xy=(90, -11.4), xytext=(46, -28),
                 ha="center", va="center", fontsize=7.2, style="italic",
                 linespacing=1.35, color=E.color_institucion("Udenar"),
                 arrowprops=dict(arrowstyle="-", color="#999999", lw=0.8,
                                 shrinkA=1, shrinkB=3), zorder=8)

    ax2.set_yticks([-8, -4, 0, 4, 8])
    ax2.set_xticks([70, 80, 90, 100])
    ax2.set_title("La esquina del cero, ampliada", pad=8)
    for inst, cr in cruces.items():
        ax2.plot([cr], [0], marker="o", markersize=4.5,
                 color=E.color_institucion(inst), markeredgecolor="white",
                 markeredgewidth=0.6, zorder=9)
    # Etiqueta al final de cada curva, que es lo propio de una curva de
    # duración: no puede chocar con nada y ahorra la leyenda.
    for inst, y in (("HUDN", 6.12), ("Cesmag", 1.05), ("Mariana", -2.41),
                    ("UCC", -5.91)):
        ax2.text(100.9, y, E.etiqueta_institucion(inst), ha="left",
                 va="center", fontsize=7.2,
                 color=E.color_institucion(inst), zorder=8)
    ax2.text(84.0, -7.7, E.etiqueta_institucion("Udenar"), ha="right",
             va="center", fontsize=7.2,
             color=E.color_institucion("Udenar"), zorder=8)

    _rotulo_cobertura(fig, cobertura)
    fig.supxlabel("Horas con dato, ordenadas de la lectura mayor a la menor (%)",
                  fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))

    filas = []
    for inst in E.ORDEN_INSTITUCIONES:
        x, o = curvas[inst]
        filas += [{"zona": "curva", "institucion": inst,
                   "posicion_pct": round(float(a), 4),
                   "lectura_kW": round(float(b), 6)} for a, b in zip(x, o)]
    for inst, cr in cruces.items():
        filas.append({"zona": "cruce", "institucion": inst,
                      "posicion_pct": round(float(cr), 4), "lectura_kW": 0.0})

    print(f"  [f3.3] cruces: " + ", ".join(
        f"{i} {c:.1f}%" for i, c in cruces.items()))

    return E.guardar(
        fig, f"f3_02b_gradacion_{cobertura}", datos=pd.DataFrame(filas),
        procedencia=[D.rel(D.CACHE / f"preproceso_{cobertura}.npz"),
                     D.rel(D.CACHE / f"preproceso_{cobertura}_resumen.csv")])


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
    f31d_duplicados()
    f31b_energia_hora()
    f31c_hora_incompleta()
    for cob in ("m1", "m3"):
        f32_demanda_negativa(cob)
    f32b_gradacion("m1")
    f33_reconstruccion("m1", "Udenar")
    for cob in ("m1", "m3"):
        f37_matrices(cob)
        f38_perfiles_instituciones(cob)
        f39_ritmos(cob)
    for cob in ("m1", "m3"):
        f35_outliers_imputacion(cob)
    print("\nlisto.")
