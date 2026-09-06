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
from matplotlib.transforms import Bbox
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
def f32_demanda_negativa():
    """
    F3.2 — La demanda que el medidor entrega en negativo.

    Una fila por frontera. A la izquierda, el perfil de la institución que
    carga con el fenómeno en esa frontera, dibujado dos veces, en promedio
    y en mínimo de cada hora, sobre las cuatro restantes en promedio y en
    gris de contexto. A la derecha, cuántas horas caen bajo cero en cada
    hora del día, apiladas por institución.

    **Por qué van las dos curvas y no una.** Las dos fronteras no admiten
    la misma lectura: bajo M1 el promedio horario de Udenar entra en la
    zona imposible, y bajo M3 ningún promedio lo hace, de modo que dibujar
    solo promedios dejaría la segunda fila sin fenómeno y dibujar solo
    mínimos perdería lo que la primera enseña, que es que el neteo arrastra
    la media entera de una institución y no unos pocos casos sueltos.
    Medido: con el mínimo dibujado, la excursión negativa del promedio de
    Udenar ocupa el 16,9 % del alto de su panel, y sin él, el 25,9 %; sigue
    siendo legible, de modo que caben las dos.

    Esto corrige además un defecto de la versión anterior: en la frontera
    secundaria la curva destacada era el mínimo de cada hora y las cuatro
    de contexto seguían siendo promedios, sin que nada lo dijera. Eran
    objetos distintos comparados en el mismo par de ejes.

    El conteo por institución, la fracción, el mínimo y la energía hacia la
    red no se repiten aquí: los da la tabla de los tipos de medidor. La
    figura se queda con lo que solo se ve dibujando, que es la forma de la
    campana solar y el promedio que se hunde.
    """
    fig, ejes = plt.subplots(2, 2, figsize=(E.ANCHO_COMPLETO, 6.0),
                             gridspec_kw={"width_ratios": [1, 1.18]})
    filas = []

    for fila, cob in enumerate(("m1", "m3")):
        ax1, ax2 = ejes[fila]
        series, _ = D.preproceso(cob)

        negativas = {i: series[f"{i}__D_raw"] for i in E.ORDEN_INSTITUCIONES
                     if (series[f"{i}__D_raw"] < 0).any()}
        assert negativas, f"ninguna institución con negativos en {cob}"
        principal = max(negativas, key=lambda i: int((negativas[i] < 0).sum()))
        s = negativas[principal]
        media = s.groupby(s.index.hour).mean()
        minimo = s.groupby(s.index.hour).min()

        # ── Izquierda: la curva que se hunde, y las que no ───────────────
        # Las otras cuatro van en gris de contexto y en promedio, que es la
        # misma definicion que la curva gruesa de su fila: cinco colores
        # compitiendo enterrarian la lectura, y comparar un minimo contra
        # cuatro promedios compararia objetos distintos.
        otras = []
        for inst in E.ORDEN_INSTITUCIONES:
            if inst == principal:
                continue
            o = series[f"{inst}__D_raw"]
            otras.append(o.groupby(o.index.hour).mean())
        for k, o in enumerate(otras):
            ax1.plot(o.index, o.values, color="#BFBFBF", linewidth=1.1,
                     zorder=2, label="Las otras cuatro, en promedio"
                     if k == 0 else None)

        color = E.color_institucion(principal)
        etiqueta = E.etiqueta_institucion(principal)
        ax1.plot(minimo.index, minimo.values, color=color, linewidth=1.1,
                 linestyle=(0, (4, 2)), zorder=3,
                 label=f"{etiqueta}, mínimo de cada hora")
        ax1.plot(media.index, media.values, color=color, linewidth=2.0,
                 zorder=4, label=f"{etiqueta}, en promedio")
        ax1.axhline(0, color="#333333", linewidth=1.0, zorder=3)

        techo = max([float(media.max())] + [float(o.max()) for o in otras])
        piso = float(minimo.min())
        alto = techo - piso
        lo, hi = piso - 0.10 * alto, techo + 0.34 * alto
        ax1.set_ylim(lo, hi)
        ax1.axhspan(lo, 0, color=E.ANTES, alpha=0.09, zorder=0)
        ax1.legend(loc="upper left", fontsize=6.6, frameon=False,
                   handlelength=1.4, handletextpad=0.5, borderpad=0.2,
                   labelspacing=0.3)

        # La zona imposible se rotula una vez, en la fila de arriba: la
        # banda es identica en las dos y el rotulo repetido gasta el sitio
        # que necesita la curva.
        if fila == 0:
            # Dos palabras y en el único hueco de la banda, que son las
            # horas de noche a la izquierda: la glosa de dos líneas que
            # había antes la cruzaban las dos curvas, porque el mínimo de
            # cada hora recorre la banda entera de las 6 a las 18. Lo que
            # decía la glosa lo dice ahora el pie.
            ax1.text(0.3, -0.07 * (0 - lo), "zona imposible", ha="left",
                     va="top", fontsize=7.0, color=E.ANTES, style="italic",
                     zorder=5)

        # Lo unico que se rotula del perfil es lo que la tabla no trae: si
        # el promedio entra o no en la zona imposible. Los minimos por
        # institucion los publica la tabla de los tipos de medidor.
        if float(media.min()) < 0:
            h = int(media.idxmin())
            ax1.annotate(f"el promedio baja\na "
                         f"{E.fmt_miles(float(media.min()), 1)} kW a las {h}",
                         xy=(h, float(media.min())),
                         xytext=(h + 4.2, float(media.min()) - 0.01 * alto),
                         fontsize=6.8, color=color, ha="left", va="center",
                         linespacing=1.3,
                         arrowprops=dict(arrowstyle="-", color=color, lw=0.7,
                                         shrinkA=1, shrinkB=3), zorder=6)
        else:
            # Sobre el tramo final de la propia curva, que es la única
            # región libre: arriba a la derecha se imprimía sobre la
            # leyenda y en medio cruzaba las cuatro de contexto.
            ax1.text(23.4, float(media.iloc[-1]) + 0.05 * alto,
                     "el promedio no entra\nen la zona imposible",
                     fontsize=6.8, color=color, ha="right", va="bottom",
                     linespacing=1.3, zorder=6)

        ax1.set_xlabel("Hora del día", fontsize=7.6)
        ax1.set_ylabel("Demanda del medidor (kW)", fontsize=7.6)
        ax1.set_xticks(range(0, 24, 6))
        ax1.tick_params(labelsize=7)
        if fila == 0:
            ax1.set_title("Cómo llega del medidor", pad=8)

        for h in range(24):
            filas.append({"zona": "perfil", "frontera": cob.upper(),
                          "institucion": principal, "hora": h,
                          "promedio_kW": round(float(media[h]), 6),
                          "minimo_kW": round(float(minimo[h]), 6)})

        # ── Derecha: cuándo ocurre ──────────────────────────────────────
        conteos = {i: (t < 0).groupby(t.index.hour).sum()
                          .reindex(range(24), fill_value=0)
                   for i, t in negativas.items()}
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
            filas += [{"zona": "horas_negativas", "frontera": cob.upper(),
                       "institucion": inst, "hora": int(h), "horas": int(x)}
                      for h, x in conteos[inst].items() if x]

        pico = int(np.argmax(base))
        con_dato = np.flatnonzero(base > 0)
        h0, h1 = int(con_dato[0]) - 1, int(con_dato[-1]) + 1
        ax2.annotate(f"{E.fmt_miles(base[pico])} horas",
                     xy=(pico, base[pico]),
                     xytext=(pico + (h1 - pico) * 0.42, base[pico] * 1.13),
                     fontsize=6.8, color="#555555", ha="left", va="center",
                     arrowprops=dict(arrowstyle="-", color="#999999", lw=0.8,
                                     shrinkA=1, shrinkB=3), zorder=6)
        ax2.set_ylim(0, base.max() * 1.42)
        ax2.set_xlim(h0 - 0.6, h1 + 0.6)
        ax2.set_xlabel("Hora del día", fontsize=7.6)
        ax2.set_ylabel("Horas con lectura negativa", fontsize=7.6)
        ax2.set_xticks(range(h0 + (h0 % 2), h1 + 1, 2))
        ax2.tick_params(labelsize=7)
        ax2.text(h1 + 0.4, base.max() * 1.36,
                 f"{E.fmt_miles(base.sum())} horas en total",
                 ha="right", va="center", fontsize=6.8, color="#555555")
        ax2.legend(loc="upper left", fontsize=6.6, frameon=False,
                   handlelength=1.1, handletextpad=0.5, borderpad=0.2,
                   labelspacing=0.3)
        if fila == 0:
            ax2.set_title("Cuándo ocurre", pad=8)

        # La frontera rotula la fila entera, en su color, fuera del area de
        # dato, como en la anatomia del umbral.
        ax1.text(-0.30, 0.5, E.titulo_cobertura(cob, dos_lineas=True),
                 transform=ax1.transAxes, rotation=90, fontsize=7.0,
                 fontweight="bold", color=E.COBERTURAS[cob], ha="center",
                 va="center")

    fig.tight_layout(rect=(0, 0, 1, 0.995), h_pad=2.6)
    return E.guardar(
        fig, "f3_02_demanda_negativa", datos=pd.DataFrame(filas),
        procedencia=[
            "reformateo/documento/datos_cache/preproceso_m1.npz",
            "reformateo/documento/datos_cache/preproceso_m3.npz",
        ])


# ─────────────────────────────────────────────────────────────────────────────
def f32b_profundidad():
    """
    F3.3 — Hasta dónde baja la lectura de cada medidor, en las dos fronteras.

    Sustituye a la curva de duración que ocupaba este sitio. Aquella tenía
    en el eje horizontal un percentil de horas ordenadas, es decir un orden
    y no una magnitud, y el lector llegaba a ella desde la figura de la
    demanda negativa, cuyo eje horizontal es la hora del día.

    Qué añade sobre la tabla de los tipos. La tabla publica el conteo de
    horas bajo cero, la fracción, el mínimo y la energía hacia la red. No
    dice a qué profundidad ocurre la inversión de ordinario, y la
    diferencia importa: en Udenar la mitad central de las lecturas
    negativas cae entre −15,1 y −3,9 kW, con mediana de −8,7, mientras que
    el mínimo publicado, −33,6 kW, es casi cuatro veces esa mediana.

    La forma. Una fila por institución en el orden fijo, una sola magnitud
    en el eje horizontal, los kilovatios, y un panel por frontera. Cada
    fila lleva la lectura mediana del medidor, el recorrido desde esa
    mediana hasta su lectura más baja, y la mitad central de sus lecturas
    negativas cuando las tiene.

    **Las dos escalas son independientes, y tienen que serlo.** El
    recorrido dibujado abarca 51 kW en la frontera principal y 3,8 en la
    secundaria, es decir, un factor de 13; con una escala común las cinco
    filas de la derecha cabrían en el 7 % del ancho y la figura no podría
    dibujar lo que afirma.

    **El vacío de la derecha es el hallazgo, no una carencia.** Bajo M3
    solo la Universidad Mariana cruza el cero, y apenas, porque es la
    única institución sin medidor secundario y se representa escalando su
    totalizador. Los otros cuatro circuitos nunca se acercan al cero, y es
    lo que sostiene que la lectura imposible sea un asunto de la frontera
    principal.

    La identidad de cada fila la lleva su rótulo y su posición, no el
    color, de modo que la figura sobrevive impresa en escala de grises.
    """
    # El contrato es la tabla impresa del capítulo, no solo el caché. Si el
    # caché cambia de versión, la figura se detiene antes de dibujar otra
    # cosa con los mismos rótulos.
    # CAL-45: Mariana pasa de 213 a 210. Las tres que faltan son lecturas
    # del hundimiento de tension del 29 de agosto, que el guardia retira:
    # no eran flujo inverso sino un equipo averiado.
    HORAS_TABLA = {"m1": {"Udenar": 1517, "Mariana": 210, "UCC": 94,
                          "HUDN": 0, "Cesmag": 0},
                   "m3": {"Udenar": 0, "Mariana": 210, "UCC": 0,
                          "HUDN": 0, "Cesmag": 0}}
    MIN_TABLA = {"m1": {"Udenar": -33.567, "Mariana": -2.411, "UCC": -5.909},
                 "m3": {"Mariana": -0.723}}
    # Las medianas de las negativas y las cajas son las cifras nuevas que
    # el pie publica, y por eso entran también en la compuerta.
    NEGMED_PIE = {"m1": {"Udenar": -8.678, "Mariana": -0.596, "UCC": -1.938},
                  "m3": {"Mariana": -0.179}}
    CAJA_PIE = {"m1": {"Udenar": (-15.051, -3.902)},
                "m3": {"Mariana": (-0.333, -0.093)}}
    FRAC_TABLA = {"Udenar": 73.8, "Mariana": 21.3, "UCC": 11.7,
                  "HUDN": 0.0, "Cesmag": 0.0}
    TIPO_TABLA = {"Udenar": "net", "Mariana": "net_partial",
                  "UCC": "net_partial", "HUDN": "gross", "Cesmag": "gross"}

    datos = {}
    for cob in ("m1", "m3"):
        series, _ = D.preproceso(cob)
        resumen = D.conteo_negativas(cob).set_index("institucion")
        med, minimo, caja, negmed = {}, {}, {}, {}
        for inst in E.ORDEN_INSTITUCIONES:
            v = series[f"{inst}__D_raw"].dropna().values
            assert not np.isnan(v).any(), inst
            assert 5900 <= len(v) <= 6144, (inst, len(v))

            n_neg = int((v < 0).sum())
            assert n_neg == HORAS_TABLA[cob][inst], (cob, inst, n_neg)
            assert n_neg == int(resumen.loc[inst, "horas_negativas"]), (cob, inst)

            med[inst] = float(np.median(v))
            minimo[inst] = float(v.min())
            if inst in MIN_TABLA[cob]:
                assert abs(minimo[inst] - MIN_TABLA[cob][inst]) < 1e-3, \
                    (cob, inst, minimo[inst])
                neg = v[v < 0]
                caja[inst] = (float(np.percentile(neg, 25)),
                              float(np.percentile(neg, 75)))
                negmed[inst] = float(np.median(neg))
            else:
                assert minimo[inst] > 0, (cob, inst, minimo[inst])

            if cob == "m1":
                g = float(series[f"{inst}__G_recon"].sum())
                d = float(series[f"{inst}__D_recon"].sum())
                assert abs(round(100 * g / d, 1) - FRAC_TABLA[inst]) < 0.05, inst

        for i, v in NEGMED_PIE[cob].items():
            assert abs(negmed[i] - v) < 1e-3, (cob, i, negmed[i], v)
        for i, (lo, hi) in CAJA_PIE[cob].items():
            assert abs(caja[i][0] - lo) < 1e-3 and abs(caja[i][1] - hi) < 1e-3, \
                (cob, i, caja[i])
        datos[cob] = (series, med, minimo, caja, negmed)

    # Las afirmaciones que la figura dibuja y el pie enuncia.
    series1, med1, min1, caja1, negmed1 = datos["m1"]
    # CAL-45: el minimo de CESMAG era el propio fallo de tension del 17 de
    # junio, con las fases A y B hundidas y el medidor informando 0,195 kW.
    # Retirado el fallo, el minimo real de la serie es 2,588 kW.
    assert abs(min1["Cesmag"] - 2.588) < 5e-4, min1["Cesmag"]
    assert 6 < min1["HUDN"] < 7, min1["HUDN"]
    assert 3.7 < min1["Udenar"] / negmed1["Udenar"] < 4.0, \
        min1["Udenar"] / negmed1["Udenar"]
    assert min1["Udenar"] < caja1["Udenar"][0] < negmed1["Udenar"] \
        < caja1["Udenar"][1] < 0, caja1["Udenar"]
    su = series1["Udenar__D_raw"]
    assert round(100 * int((su < 0).sum()) / len(su), 1) == 24.7
    assert round(100 * int((su < 0).sum()) / int(su.notna().sum()), 1) == 25.1
    gu, du = series1["Udenar__G_recon"], series1["Udenar__D_recon"]
    mediodia = (gu > du)[gu.index.hour == 12]
    assert mediodia.mean() > 0.5, float(mediodia.mean())
    # Y lo que sostiene el panel de la derecha: allí cruza el cero una sola.
    cruzan_m3 = [i for i in E.ORDEN_INSTITUCIONES if datos["m3"][2][i] < 0]
    assert cruzan_m3 == ["Mariana"], cruzan_m3

    # ── Lienzo ───────────────────────────────────────────────────────────
    fig, ejes = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 3.1),
                             sharey=True, gridspec_kw={"width_ratios": [1.35, 1]})
    marcas = {}
    for ax, cob in zip(ejes, ("m1", "m3")):
        series, med, minimo, caja, negmed = datos[cob]
        E.eje_instituciones(ax, eje="y")
        ax.grid(visible=False, axis="y")
        ax.grid(visible=True, axis="x")

        # El margen se calcula del dato y no se fija a mano: las dos
        # fronteras abarcan 51 y 3,8 kW.
        piso = min(minimo.values())
        techo = max(med.values())
        ancho = techo - piso
        xlo, xhi = piso - 0.10 * ancho, techo + 0.24 * ancho
        ax.set_xlim(xlo, xhi)
        ax.axvspan(xlo, 0, color=E.ANTES, alpha=0.07, zorder=0)
        ax.axvline(0, color="#333333", linewidth=1.0, zorder=2)

        # Las marcas se registran en coordenadas de dato, no como
        # artistas: el extremo en pantalla de una colección de líneas no
        # es fiable y la prueba de oclusión fallaría sobre otro objeto.
        marcas[cob] = []
        for k, inst in enumerate(E.ORDEN_INSTITUCIONES):
            c = E.color_institucion(inst)
            ax.plot([minimo[inst], med[inst]], [k, k], color=c, linewidth=1.4,
                    solid_capstyle="butt", zorder=4)
            marcas[cob].append((f"recorrido {inst}", minimo[inst], med[inst],
                                k - 0.02, k + 0.02))
            if inst in caja:
                lo, hi = caja[inst]
                ax.add_patch(Rectangle((lo, k - 0.17), hi - lo, 0.34,
                                       facecolor=c, edgecolor="white",
                                       linewidth=0.5, zorder=5))
                marcas[cob].append((f"caja {inst}", lo, hi, k - 0.17, k + 0.17))
            ax.plot([minimo[inst]], [k], marker="o", markersize=5.2, color=c,
                    markeredgecolor="white", markeredgewidth=0.7, zorder=6)
            marcas[cob].append((f"mínimo {inst}", minimo[inst], minimo[inst],
                                k, k))
            # La lectura mediana, en tinta y no en color: es la referencia
            # contra la que se mide el descenso, y es la misma en las diez.
            ax.vlines(med[inst], k - 0.21, k + 0.21, color=E.TINTA,
                      linewidth=1.8, zorder=7)
            marcas[cob].append((f"mediana {inst}", med[inst], med[inst],
                                k - 0.21, k + 0.21))

        ax.set_xlabel("Lectura del medidor (kW)", fontsize=7.6)
        ax.set_title(E.titulo_cobertura(cob, dos_lineas=True),
                     color=E.COBERTURAS[cob], fontweight="bold", pad=8,
                     fontsize=8.2)
        ax.tick_params(labelsize=7.5)

    # Segunda columna de rótulos en el panel de la izquierda, fuera del
    # área de dato: el tipo que la subsección asigna a cada medidor.
    # Puesta al lado de la geometría deja ver que el neto parcial se
    # parece más al bruto que al neto.
    axd = ejes[0].twinx()
    axd.set_ylim(ejes[0].get_ylim())
    axd.grid(visible=False)
    axd.spines["right"].set_visible(False)
    axd.set_yticks(range(len(E.ORDEN_INSTITUCIONES)))
    axd.set_yticklabels([E.TIPO_MEDIDOR_ES[TIPO_TABLA[i]]
                         for i in E.ORDEN_INSTITUCIONES], fontsize=7.0,
                        color=E.NEUTRO)
    axd.tick_params(axis="y", length=0, pad=8)
    # La columna cae en el hueco entre los dos paneles, de modo que sin
    # cabecera podría leerse como propia del de la derecha. El tipo es una
    # propiedad de la frontera principal: en la secundaria los cinco son
    # circuitos derivados.
    axd.text(1.01, 1.015, "tipo en M1", transform=axd.transAxes, ha="left",
             va="bottom", fontsize=6.3, color=E.NEUTRO)

    # Un solo rótulo por panel, y sin cifra: los valores exactos van al
    # pie y al CSV hermano. En el panel de la derecha el rótulo dice lo
    # que el vacío significa, que es que solo un circuito cruza el cero.
    t1 = ejes[0].text(ejes[0].get_xlim()[0] + 0.03 * (ejes[0].get_xlim()[1]
                                                      - ejes[0].get_xlim()[0]),
                      3.72, "flujo invertido, es decir,\ndel circuito hacia la red",
                      ha="left", va="center", fontsize=7.0, style="italic",
                      color=E.ANTES, linespacing=1.35, zorder=9)
    # En el panel de la derecha la banda del flujo invertido está casi
    # vacía y es estrecha, de modo que el rótulo va girado dentro de ella:
    # horizontal no cabía en ninguna fila sin tocar un recorrido, y la
    # prueba de oclusión lo cazó contra el de CESMAG.
    x3lo, x3hi = ejes[1].get_xlim()
    t3 = ejes[1].text(x3lo + 0.03 * (x3hi - x3lo), 2.0,
                      "solo un circuito cruza el cero",
                      ha="center", va="center", rotation=90, fontsize=6.8,
                      style="italic", color=E.ANTES, zorder=9)

    leyenda = [
        Line2D([], [], color=E.TINTA, linestyle="none", marker="|",
               markersize=8, markeredgewidth=1.8, label="Lectura mediana"),
        Line2D([], [], color=E.NEUTRO, linestyle="none", marker="o",
               markersize=5.2, markeredgecolor="white", markeredgewidth=0.7,
               label="Lectura más baja"),
        Line2D([], [], color=E.NEUTRO, linewidth=1.4,
               label="Recorrido entre ambas"),
        Patch(facecolor=E.NEUTRO, edgecolor="white", linewidth=0.5,
              label="Mitad central de las lecturas negativas"),
    ]
    fig.legend(handles=leyenda, loc="lower center", ncol=4, fontsize=7.0,
               frameon=False, handlelength=1.5, handletextpad=0.5,
               columnspacing=1.4, bbox_to_anchor=(0.5, -0.015))

    fig.tight_layout(rect=(0, 0.09, 1, 0.995))

    # ── Ningún rótulo puede tapar dato ───────────────────────────────────
    # Las marcas se llevan a pantalla desde sus coordenadas de dato y se
    # ensanchan 2,6 puntos, que es el radio del marcador del mínimo más la
    # mitad del grosor de la línea de la mediana.
    fig.canvas.draw()
    HOLGURA = 2.6 * fig.dpi / 72.0
    for ax, cob, t in ((ejes[0], "m1", t1), (ejes[1], "m3", t3)):
        bt = t.get_window_extent()
        for nombre, x0, x1, y0, y1 in marcas[cob]:
            (px0, py0), (px1, py1) = ax.transData.transform([(x0, y0), (x1, y1)])
            bm = Bbox([[min(px0, px1) - HOLGURA, min(py0, py1) - HOLGURA],
                       [max(px0, px1) + HOLGURA, max(py0, py1) + HOLGURA]])
            assert not bt.overlaps(bm), (t.get_text(), cob, nombre)
        bax = ax.get_window_extent()
        assert bax.contains(*bt.min) and bax.contains(*bt.max), t.get_text()
    bl = fig.legends[0].get_window_extent()
    bf = fig.get_window_extent()
    assert bl.x0 >= bf.x0 and bl.x1 <= bf.x1, (bl.x0, bl.x1, bf.x1)

    filas = []
    for cob in ("m1", "m3"):
        series, med, minimo, caja, negmed = datos[cob]
        for inst in E.ORDEN_INSTITUCIONES:
            filas.append({
                "frontera": cob.upper(), "institucion": inst,
                "tipo_en_m1": E.TIPO_MEDIDOR_ES[TIPO_TABLA[inst]],
                "horas_con_dato": int(series[f"{inst}__D_raw"].notna().sum()),
                "horas_negativas": HORAS_TABLA[cob][inst],
                "mediana_kW": round(med[inst], 6),
                "minimo_kW": round(minimo[inst], 6),
                "negativas_p25_kW": round(caja[inst][0], 6) if inst in caja else "",
                "negativas_mediana_kW": round(negmed[inst], 6) if inst in negmed else "",
                "negativas_p75_kW": round(caja[inst][1], 6) if inst in caja else ""})

    return E.guardar(
        fig, "f3_02b_profundidad", datos=pd.DataFrame(filas),
        procedencia=[
            "reformateo/documento/datos_cache/preproceso_m1.npz",
            "reformateo/documento/datos_cache/preproceso_m3.npz",
        ])


# ─────────────────────────────────────────────────────────────────────────────
def f33_reconstruccion(cobertura: str = "m1", institucion: str = "Udenar",
                       dia: str = "2025-11-07"):
    """
    F3.3 — La reconstrucción net→bruta, dibujada como la operación que es.

    La figura estrella del documento. La versión anterior dibujaba tres
    series sueltas: la lectura del medidor, la generación desde el eje
    cero y la demanda reconstruida. El lector tenía que sumar de cabeza,
    hora por hora, para comprobar que la primera más la segunda daban la
    tercera. Aquí la generación se dibuja como la banda vertical entre la
    lectura y la demanda reconstruida, que es lo que dice la ecuación: la
    reconstruida es la lectura levantada por la generación. La suma se ve
    sin aritmética.

    El día no se busca por código ni se elige por favorable. Es el viernes
    7 de noviembre de 2025, y se fija aquí por dos razones. Primera, cae
    en el tramo posterior al 3 de septiembre de 2025, cuando los tres
    inversores de Udenar registran a la vez; antes de esa fecha el del
    proyecto no medía, la suma iba incompleta y la reconstrucción se
    quedaba corta, de modo que un día de ese tramo enseñaría el método con
    el sesgo de cobertura encima, que es asunto de la subsección del costo
    y no de esta. Segunda, ninguna de sus 24 horas llega al recorte a
    cero, de modo que la banda entre las dos curvas es la generación y no
    una mezcla de generación y recorte. Las dos condiciones se comprueban
    con asertos antes de dibujar: si el día dejara de cumplirlas, la
    corrida se detiene en vez de publicar una figura que afirma una
    igualdad que no se cumple.

    El panel derecho generaliza a las 6.144 horas con el perfil medio, en
    la misma escala vertical, para que se vea que el día no es
    excepcional. La franja de abajo cierra con la misma cuenta en energía
    sobre el horizonte completo, que es donde el recorte a cero deja de
    ser un hilo invisible y se puede medir.
    """
    series, horas = D.preproceso(cobertura)

    D_raw = series[f"{institucion}__D_raw"]
    G_rec = series[f"{institucion}__G_recon"]
    D_rec = series[f"{institucion}__D_recon"]

    # El pipeline reconstruye con la lectura ausente tratada como nula, de
    # modo que aquí se rellena igual. Con la media saltando los huecos, la
    # identidad D_recon = D_neto + G + recorte dejaría de cerrar en el
    # perfil medio por las horas sin lectura, y la figura afirmaría una
    # igualdad que sus propias curvas no cumplen.
    D_neto = D_raw.fillna(0.0)
    recorte = (-(D_neto + G_rec)).clip(lower=0.0)
    assert float((D_rec - (D_neto + G_rec + recorte)).abs().max()) < 1e-9

    # ── El día: 24 horas, con la operación a la vista ───────────────────
    d0 = pd.Timestamp(dia)
    sl = slice(d0, d0 + pd.Timedelta(hours=23))
    x = np.arange(24)
    dr = D_neto[sl].to_numpy(dtype=float)
    gr = G_rec[sl].to_numpy(dtype=float)
    dd = D_rec[sl].to_numpy(dtype=float)

    assert len(dr) == 24, (dia, len(dr))
    assert not D_raw[sl].isna().any(), f"{dia}: hay horas sin lectura de medidor"
    assert d0 >= pd.Timestamp("2025-09-03"), (
        f"{dia} es anterior al 3 de septiembre de 2025: la suma de "
        "inversores va incompleta y la reconstrucción se queda corta")
    assert float(recorte[sl].sum()) < 1e-9, (
        f"{dia} tiene horas con recorte a cero: la banda entre las dos "
        "curvas ya no sería la generación")
    assert np.allclose(dd, dr + gr, atol=1e-9)

    fig = plt.figure(figsize=(E.ANCHO_COMPLETO, 5.0))
    gs = fig.add_gridspec(2, 2, width_ratios=(1.42, 1.0),
                          height_ratios=(1.0, 0.34))
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1], sharey=ax1)
    axb = fig.add_subplot(gs[1, :])
    ax2.tick_params(labelleft=False)

    ax1.axhline(0, color="#333333", linewidth=0.9, zorder=3)
    ax1.fill_between(x, dr, dd, color=E.APOYO, zorder=1)
    ax1.plot(x, dd, color=E.DESPUES, linewidth=2.2, zorder=4)
    ax1.plot(x, dr, color=E.ANTES, linewidth=1.4, zorder=5)

    lo, hi = float(min(dr.min(), dd.min())), float(max(dr.max(), dd.max()))
    alto = hi - lo
    ax1.set_ylim(lo - 0.09 * alto, hi + 0.13 * alto)

    # La cota se planta en la hora de lectura más baja, que es donde la
    # banda es más elocuente. La flecha mide la banda y el rótulo dice
    # cuánto mide: ahí queda la operación, hecha una vez y a la vista.
    h = int(np.argmin(dr))
    ax1.annotate("", xy=(h, dd[h]), xytext=(h, dr[h]), zorder=6,
                 arrowprops=dict(arrowstyle="<->", color=E.TINTA, lw=0.9,
                                 shrinkA=0, shrinkB=0))
    for extremo in (dr[h], dd[h]):
        ax1.plot([h - 0.22, h + 0.22], [extremo, extremo], color=E.TINTA,
                 lw=0.9, solid_capstyle="butt", zorder=6)
    ax1.text(h + 0.42, (dr[h] + dd[h]) / 2 + 0.055 * alto,
             f"{E.fmt_miles(gr[h], 1)} kW de generación",
             rotation=90, ha="left", va="center", fontsize=7.2,
             color=E.TINTA, zorder=6)

    ax1.set_xlabel("Hora del día")
    ax1.set_ylabel("Potencia (kW)")
    ax1.set_title(f"{E.etiqueta_institucion(institucion)}, "
                  f"{E.fmt_fecha(d0, 'dia')}", pad=8)
    ax1.set_xticks(range(0, 24, 3))
    ax1.set_xlim(-0.6, 23.6)

    # ── El horizonte: el mismo dibujo sobre el perfil medio ─────────────
    idx = np.arange(24)
    p_neto = D_neto.groupby(D_neto.index.hour).mean().to_numpy(dtype=float)
    p_gen = G_rec.groupby(G_rec.index.hour).mean().to_numpy(dtype=float)
    p_rec = D_rec.groupby(D_rec.index.hour).mean().to_numpy(dtype=float)
    p_cor = recorte.groupby(recorte.index.hour).mean().to_numpy(dtype=float)
    assert np.allclose(p_rec, p_neto + p_gen + p_cor, atol=1e-9)

    ax2.axhline(0, color="#333333", linewidth=0.9, zorder=3)
    ax2.fill_between(idx, p_neto, p_neto + p_gen, color=E.APOYO, zorder=1)
    # El recorte a cero queda como un hilo bajo la curva azul. No se
    # rotula aquí: en potencia media son seis décimas de kW, y una llamada
    # a un trazo de esa altura pesa más que el trazo. Lo nombra la franja
    # de energía, que usa este mismo gris y donde ya se puede medir.
    ax2.fill_between(idx, p_neto + p_gen, p_rec, color=E.NEUTRO, alpha=0.65,
                     zorder=2)
    ax2.plot(idx, p_rec, color=E.DESPUES, linewidth=2.2, zorder=4)
    ax2.plot(idx, p_neto, color=E.ANTES, linewidth=1.4, zorder=5)
    ax2.set_xlabel("Hora del día")
    ax2.set_title(f"El promedio de las {E.fmt_miles(len(horas))} horas", pad=8)
    ax2.set_xticks(range(0, 24, 6))
    ax2.set_xlim(-0.6, 23.6)

    # ── La franja de energía: la misma cuenta sobre el horizonte ────────
    e_neto = float(D_neto.sum())
    e_gen = float(G_rec.sum())
    e_cor = float(recorte.sum())
    e_rec = float(D_rec.sum())
    assert abs(e_neto + e_gen + e_cor - e_rec) < 1e-6

    hueco = 0.0025 * e_rec          # el blanco que separa un tramo del otro
    tramos = [
        ("lectura del medidor", e_neto, E.ANTES, 0.80),
        ("generación devuelta", e_gen, E.APOYO, 1.00),
        ("recorte a cero", e_cor, E.NEUTRO, 0.65),
    ]
    izq = 0.0
    for k, (nombre, valor, color, opac) in enumerate(tramos):
        # El ultimo tramo llega hasta el total: descontarle el hueco lo
        # dejaba corto frente a la cota azul que mide justo ese total.
        ancho = valor - (hueco if k < len(tramos) - 1 else 0.0)
        axb.barh(0, ancho, left=izq, height=0.46, color=color,
                 alpha=opac, zorder=3)
        izq += valor

    axb.plot([0, e_rec], [-0.52, -0.52], color=E.DESPUES, lw=2.0,
             solid_capstyle="butt", zorder=3)
    for xx in (0.0, e_rec):
        axb.plot([xx, xx], [-0.66, -0.38], color=E.DESPUES, lw=2.0, zorder=3)
    axb.text(e_rec / 2, -0.80,
             f"demanda reconstruida: {E.fmt_miles(e_rec)} kWh",
             ha="center", va="top", fontsize=7.6, color=E.DESPUES)

    # Los dos tramos anchos se rotulan encima y centrados; el recorte no
    # admite rótulo dentro ni encima sin pisar al vecino, de modo que sube
    # una línea y baja a buscarlo con un hilo.
    izq = 0.0
    for k, (nombre, valor, _color, _opac) in enumerate(tramos):
        centro = izq + valor / 2
        if k < 2:
            axb.text(centro, 0.36, f"{nombre}\n{E.fmt_miles(valor)} kWh",
                     ha="center", va="bottom", fontsize=7.6, color=E.TINTA,
                     linespacing=1.3)
        else:
            axb.annotate(f"{nombre}\n{E.fmt_miles(valor)} kWh",
                         xy=(centro, 0.25), xytext=(e_rec, 1.30),
                         ha="right", va="top", fontsize=7.6, color=E.TINTA,
                         linespacing=1.3,
                         arrowprops=dict(arrowstyle="-", color=E.NEUTRO,
                                         lw=0.7, shrinkA=2, shrinkB=1,
                                         connectionstyle="arc3,rad=-0.25"))
        izq += valor

    axb.set_xlim(-0.012 * e_rec, 1.012 * e_rec)
    axb.set_ylim(-1.15, 1.45)
    axb.set_title("La misma cuenta en energía, sobre el horizonte completo",
                  pad=6, loc="left")
    axb.set_axis_off()

    # La leyenda es común a los dos paneles de potencia y va al pie: dentro
    # del panel del día taparía la banda, que es la magnitud que la figura
    # existe para enseñar.
    fig.legend(handles=[
        Line2D([], [], color=E.ANTES, lw=1.6,
               label="Antes: lectura del medidor"),
        Patch(facecolor=E.APOYO, label="Generación devuelta"),
        Line2D([], [], color=E.DESPUES, lw=2.2,
               label="Después: demanda reconstruida"),
    ], loc="lower center", bbox_to_anchor=(0.5, -0.035), ncol=3, fontsize=7.4,
        frameon=False, columnspacing=1.6, handlelength=1.8)

    _rotulo_cobertura(fig, cobertura)
    # El rect no recorta por arriba: tight_layout ya reserva el sitio del
    # rotulo de cobertura, y descontarlo dos veces dejaba media pulgada
    # de blanco entre ese rotulo y los titulos de los paneles.
    fig.tight_layout(rect=(0, 0.02, 1, 1.0))

    filas = []
    for k in range(24):
        filas += [
            {"bloque": "dia", "clave": k, "serie": "lectura_medidor",
             "valor": float(dr[k]), "unidad": "kW"},
            {"bloque": "dia", "clave": k, "serie": "generacion_devuelta",
             "valor": float(gr[k]), "unidad": "kW"},
            {"bloque": "dia", "clave": k, "serie": "demanda_reconstruida",
             "valor": float(dd[k]), "unidad": "kW"},
            {"bloque": "promedio", "clave": k, "serie": "lectura_medidor",
             "valor": float(p_neto[k]), "unidad": "kW"},
            {"bloque": "promedio", "clave": k, "serie": "generacion_devuelta",
             "valor": float(p_gen[k]), "unidad": "kW"},
            {"bloque": "promedio", "clave": k, "serie": "recorte_a_cero",
             "valor": float(p_cor[k]), "unidad": "kW"},
            {"bloque": "promedio", "clave": k, "serie": "demanda_reconstruida",
             "valor": float(p_rec[k]), "unidad": "kW"},
        ]
    for nombre, valor in (("lectura_medidor", e_neto),
                          ("generacion_devuelta", e_gen),
                          ("recorte_a_cero", e_cor),
                          ("demanda_reconstruida", e_rec)):
        filas.append({"bloque": "energia", "clave": "horizonte",
                      "serie": nombre, "valor": valor, "unidad": "kWh"})

    return E.guardar(
        fig, f"f3_03_reconstruccion_{cobertura}", datos=pd.DataFrame(filas),
        procedencia=[
            f"MedicionesMTE_v3/{institucion}/ (medidor de demanda e inversores)",
            f"reformateo/documento/datos_cache/preproceso_{cobertura}.npz",
            f"día del panel izquierdo: {dia} (tramo con los tres inversores "
            "registrando, sin horas recortadas)",
            "regla: D = max(0, D_net + suma de inversores) — data/preprocessing.py",
        ])


# ─────────────────────────────────────────────────────────────────────────────
# ── La etapa de limpieza: el umbral y la escalera ────────────────────────────
# Las dos figuras que siguen sustituyen a la antigua F3.5, que metia en un
# solo par de paneles dos ideas distintas, el criterio de atipicos y el
# relleno de huecos, y no podia sostener ninguna de las dos: el panel del
# umbral dibujaba una sola linea horizontal sobre 6.144 horas, de modo que
# no se veia cual de los dos terminos del maximo mandaba ni a que distancia
# quedaba la masa de la serie, y el panel de la derecha repartia por mes
# unas horas cuyo mecanismo de relleno no declaraba. Ahora son dos figuras,
# una por idea, y el mes se retira porque la variable que decide el
# tratamiento es la longitud del hueco, no el calendario.


def _cascada_instrumentada(s: pd.Series) -> dict:
    """
    Replica de ``xm_data_loader._clean`` con una fotografia por etapa.

    Devuelve el umbral, sus dos candidatos y una mascara por destino:
    retirada por atipico, interpolada, arrastrada hacia adelante,
    arrastrada hacia atras y puesta a cero. La serie final se compara
    contra la del pipeline en el sitio donde se usa, de modo que la
    instrumentacion no pueda desviarse en silencio.
    """
    # CAL-45: la etapa perdio su primer paso, el umbral distribucional de
    # atipicos. Lo que retira dato ahora es el guardia fisico, que actua
    # sobre la lectura de dos minutos y aguas arriba de esta funcion. Los
    # candidatos del umbral se conservan como diagnostico, porque siguen
    # describiendo la forma de la serie, pero ya no cortan nada.
    q25, q75 = s.quantile(0.25), s.quantile(0.75)
    p995 = s.quantile(0.995)
    iqr = q75 - q25
    cand_tukey = q75 + 5 * iqr if iqr > 0 else np.inf
    cand_piso = p995 * 1.2 if np.isfinite(p995) else np.inf
    umbral = max(cand_tukey, cand_piso)

    m_out = pd.Series(False, index=s.index)

    s1 = s.copy()
    entran = s1.isna()
    s2 = s1.interpolate(method="time", limit=3)
    m_int = s1.isna() & s2.notna()
    s3 = s2.ffill(limit=24)
    m_ff = s2.isna() & s3.notna()
    s4 = s3.bfill(limit=24)
    m_bf = s3.isna() & s4.notna()
    s5 = s4.fillna(0.0)
    m_ze = s4.isna()

    return {"umbral": float(umbral), "tukey": float(cand_tukey),
            "piso": float(cand_piso), "q25": float(q25), "q75": float(q75),
            "p995": float(p995), "max": float(s.max()),
            "limpia": s5, "entran": entran, "out": m_out, "interp": m_int,
            "ffill": m_ff, "bfill": m_bf, "cero": m_ze}


def _censo_limpieza(cobertura: str):
    """Estado de la limpieza en las diez series de una frontera."""
    series, _ = D.preproceso(cobertura)
    filas, detalle = [], {}
    for inst in E.ORDEN_INSTITUCIONES:
        for magnitud, entrada, salida in (
                ("demanda", f"{inst}__D_recon", f"{inst}__D_limpia"),
                ("generación", f"{inst}__G_ems", f"{inst}__G_limpia")):
            r = _cascada_instrumentada(series[entrada])
            # La compuerta del capitulo: si la replica no reprodujera la
            # serie del pipeline, la figura estaria describiendo otro
            # calculo. Se detiene antes de dibujar.
            dif = float(np.abs(r["limpia"].values - series[salida].values).max())
            assert dif == 0.0, (f"la réplica de la limpieza no reproduce "
                                f"{salida}: max|dif| = {dif}")
            detalle[(inst, magnitud)] = r
            filas.append({
                "institucion": inst, "magnitud": magnitud,
                "entran": int(r["entran"].sum()), "atipicos": int(r["out"].sum()),
                "interpoladas": int(r["interp"].sum()),
                "arrastradas": int(r["ffill"].sum() + r["bfill"].sum()),
                "cero": int(r["cero"].sum()),
                "umbral_kW": r["umbral"], "cand_tukey_kW": r["tukey"],
                "cand_piso_kW": r["piso"],
                "manda": ("primer criterio" if r["tukey"] >= r["piso"]
                          else "segundo criterio"),
                "q25_kW": r["q25"], "q75_kW": r["q75"], "p995_kW": r["p995"],
                "max_kW": r["max"], "serie_entrada": entrada})
    return pd.DataFrame(filas), detalle, series


def _bajo_de_los_ejes(fig, ejes, holgura: float = 0.012) -> float:
    """
    Altura, en coordenadas de figura, justo debajo del rotulo mas bajo.

    Existe porque una leyenda de figura colocada a una altura elegida a
    ojo se imprime encima de los rotulos de eje en cuanto cambia el
    tamaño de la letra o el numero de lineas. Aqui se mide sobre el
    render y la leyenda no puede tapar nada.
    """
    fig.canvas.draw()
    render = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    y = min(inv.transform((0, ax.get_tightbbox(render).y0))[1] for ax in ejes)
    return y - holgura


def _rachas(mascara: pd.Series) -> list:
    """Rachas maximales de horas marcadas, como (inicio, fin, longitud)."""
    v = mascara.values
    fuera, i = [], 0
    while i < len(v):
        if v[i]:
            j = i
            while j < len(v) and v[j]:
                j += 1
            fuera.append((mascara.index[i], mascara.index[j - 1], j - i))
            i = j
        else:
            i += 1
    return fuera


# ─────────────────────────────────────────────────────────────────────────────
def _separar_etiquetas(ys, minimo, tope=None):
    """
    Reparte alturas de rotulo que caerian una sobre otra.

    Los cuatro valores que rotula la anatomia del umbral pueden quedar muy
    juntos: en la UCC el segundo criterio y el maximo observado distan
     6,9 kW sobre un panel de 150, es decir, ocho puntos tipograficos
    para dos rotulos de seis. Aqui se separan por el minimo pedido
    conservando el orden.
    """
    orden = sorted(range(len(ys)), key=lambda i: ys[i])
    fuera = list(ys)
    for k in range(1, len(orden)):
        i, j = orden[k - 1], orden[k]
        if fuera[j] - fuera[i] < minimo:
            fuera[j] = fuera[i] + minimo
    if tope is not None and orden:
        exceso = fuera[orden[-1]] - tope
        if exceso > 0:
            for i in orden:
                fuera[i] -= exceso
    return fuera


# ─────────────────────────────────────────────────────────────────────────────
def f33b_reconstruccion_mosaico():
    """
    F3.3b — A quién se le aplica la reconstrucción y a quién no.

    La figura anterior enseña la operación sobre un día y una institución.
    Esta es la vista de conjunto y tiene otro trabajo: enseñar de un vistazo
    quién recibe generación de vuelta y quién no. Diez paneles, cinco
    instituciones por dos fronteras, con el perfil medio horario de las
    6.144 horas y no un día concreto, porque cinco días distintos no se
    comparan entre sí.

    **Siete de los diez paneles salen sin banda, y eso es el contenido.**
    En la frontera principal el Hospital y CESMAG entregan lectura bruta,
    de modo que no hay generación que devolverles; en la secundaria no la
    entrega ninguno de los cinco. La fila de abajo es el control de la de
    arriba: prueba de un vistazo que la reconstrucción es un asunto de la
    frontera principal, que es algo que el capítulo venía afirmando en
    prosa.

    **Escalas verticales independientes por panel.** Medido sobre los
    perfiles medios: con una escala común a los diez, el recorrido entero
    del Hospital ocuparía el 4,8 % del alto de su panel y el de CESMAG el
    10 %, de modo que las dos filas quedarían en líneas planas por
    aplastamiento y no por ausencia de banda, que es justo la distinción
    que la figura existe para enseñar. Lo que se compara entre paneles no
    es una altura sino si hay banda o no, y eso no depende de la escala.
    La energía devuelta va escrita en cada panel para que el ancho de la
    banda no se lea como magnitud.

    La codificación es la de la figura anterior, de manera que la lectura
    se transfiera sin releer la leyenda.
    """
    fig, ejes = plt.subplots(2, 5, figsize=(E.ANCHO_COMPLETO, 4.9),
                             sharex=True)
    idx = np.arange(24)
    filas, resumen = [], {}

    for fila, cob in enumerate(("m1", "m3")):
        series, horas = D.preproceso(cob)
        for col, inst in enumerate(E.ORDEN_INSTITUCIONES):
            ax = ejes[fila][col]
            D_raw = series[f"{inst}__D_raw"]
            G_rec = series[f"{inst}__G_recon"]
            D_rec = series[f"{inst}__D_recon"]
            D_neto = D_raw.fillna(0.0)
            # La serie reconstruida conserva el hueco donde el medidor no
            # trajo lectura y no hay generación que sumarle, de modo que
            # las dos curvas hay que promediarlas sobre las mismas horas.
            # Promediando una con el hueco relleno y la otra sin él, los
            # dos medidores brutos salían con banda: 0,10 kW en el
            # Hospital y 0,04 en CESMAG, que no es generación devuelta
            # sino la ausencia de 113 y 117 horas.
            D_rec_lleno = D_rec.fillna(0.0)
            assert (D_rec.isna() & D_raw.notna()).sum() == 0, (cob, inst)
            recorte = (-(D_neto + G_rec)).clip(lower=0.0)
            # La misma identidad que comprueba la figura del caso: la
            # demanda reconstruida es la lectura más la generación devuelta
            # más lo que el recorte a cero añade. Se compara sobre las
            # series ya rellenas: el máximo de pandas descarta los huecos
            # en silencio y la comprobación se saltaría justo las horas
            # que aquí importan.
            dif = np.abs(D_rec_lleno.to_numpy(float)
                         - (D_neto + G_rec + recorte).to_numpy(float))
            assert np.isfinite(dif).all() and dif.max() < 1e-9, (cob, inst)

            p_neto = D_neto.groupby(D_neto.index.hour).mean().to_numpy(float)
            p_gen = G_rec.groupby(G_rec.index.hour).mean().to_numpy(float)
            p_rec = D_rec_lleno.groupby(
                D_rec_lleno.index.hour).mean().to_numpy(float)
            p_cor = recorte.groupby(recorte.index.hour).mean().to_numpy(float)
            assert np.allclose(p_rec, p_neto + p_gen + p_cor, atol=1e-9), \
                (cob, inst)
            # Y la consecuencia visible: sin generación devuelta no hay
            # banda de ningún grosor. Lo que pueda quedar entre las dos
            # curvas es entonces el recorte a cero, que va en gris.
            if float(G_rec.sum()) == 0.0:
                assert np.allclose(p_gen, 0.0, atol=1e-12), (cob, inst)
            devuelto = float(G_rec.sum())
            n_horas = int((G_rec > 0).sum())
            recortado = float(recorte.sum())
            resumen[(cob, inst)] = (devuelto, n_horas, recortado)

            ax.fill_between(idx, p_neto, p_neto + p_gen, color=E.APOYO,
                            zorder=1)
            ax.fill_between(idx, p_neto + p_gen, p_rec, color=E.NEUTRO,
                            alpha=0.65, zorder=2)
            if min(p_neto.min(), p_rec.min()) < 0:
                ax.axhline(0, color="#333333", linewidth=0.8, zorder=3)
            ax.plot(idx, p_rec, color=E.DESPUES, linewidth=1.7, zorder=4)
            ax.plot(idx, p_neto, color=E.ANTES, linewidth=1.1, zorder=5)

            lo = float(min(p_neto.min(), p_rec.min()))
            hi = float(max(p_neto.max(), p_rec.max()))
            alto = max(hi - lo, 1e-6)
            ax.set_ylim(lo - 0.12 * alto, hi + 0.30 * alto)
            ax.set_xlim(-0.6, 23.6)
            ax.set_xticks(range(0, 24, 6))
            ax.tick_params(labelsize=6.4)

            # Cada panel dice si recibe generación de vuelta y cuánta, o
            # por qué no la recibe. Sin esta línea, un panel plano se lee
            # como una figura a medio hacer.
            if devuelto > 0:
                tag, tinta = f"devuelve {E.fmt_miles(devuelto)} kWh", E.DESPUES
            elif recortado >= 1:
                # Sin generación que devolver la reconstrucción se reduce
                # al recorte, y en la Universidad Mariana bajo M3 todavía
                # muerde: es el hilo gris de ese panel.
                tag = f"solo recorta {E.fmt_miles(recortado)} kWh"
                tinta = E.NEUTRO
            else:
                tag, tinta = "el medidor no netea", E.NEUTRO
            ax.text(0.5, 1.015, tag, transform=ax.transAxes, fontsize=6.0,
                    color=tinta, ha="center", va="bottom")

            if fila == 0:
                ax.set_title(E.etiqueta_institucion(inst), fontsize=8.2,
                             pad=13)
            else:
                ax.set_xlabel("Hora del día", fontsize=7.2)

            for h in range(24):
                filas.append({"bloque": "perfil", "frontera": cob.upper(),
                              "institucion": inst, "hora": h,
                              "lectura_kW": round(float(p_neto[h]), 6),
                              "devuelta_kW": round(float(p_gen[h]), 6),
                              "reconstruida_kW": round(float(p_rec[h]), 6)})

        ejes[fila][0].set_ylabel("Demanda (kW)", fontsize=7.4)
        # La frontera rotula la fila entera, en su color, fuera del área de
        # dato, igual que en la anatomía del umbral.
        ejes[fila][0].text(-0.62, 0.5, E.titulo_cobertura(cob, dos_lineas=True),
                           transform=ejes[fila][0].transAxes, rotation=90,
                           fontsize=7.0, fontweight="bold",
                           color=E.COBERTURAS[cob], ha="center", va="center")

    # Las tres afirmaciones que sostiene la figura, comprobadas antes de
    # publicarla: quién devuelve en la frontera principal, y que en la
    # secundaria no devuelve nadie.
    for inst, esperado in (("Udenar", 32691.4), ("Mariana", 12549.1),
                           ("UCC", 15378.0), ("HUDN", 0.0), ("Cesmag", 0.0)):
        assert abs(resumen[("m1", inst)][0] - esperado) < 0.1, \
            (inst, resumen[("m1", inst)])
    assert all(resumen[("m3", i)][0] == 0.0 for i in E.ORDEN_INSTITUCIONES), \
        {i: resumen[("m3", i)][0] for i in E.ORDEN_INSTITUCIONES}

    for (cob, inst), (dev, n, rec) in resumen.items():
        filas.append({"bloque": "resumen", "frontera": cob.upper(),
                      "institucion": inst, "devuelto_kWh": round(dev, 3),
                      "horas_con_devolucion": n,
                      "recorte_a_cero_kWh": round(rec, 3)})

    fig.tight_layout(rect=(0, 0.075, 1, 0.995), h_pad=2.4, w_pad=0.7)
    fig.legend(handles=[
        Line2D([], [], color=E.ANTES, lw=1.6,
               label="Antes: lectura del medidor"),
        Patch(facecolor=E.APOYO, label="Generación devuelta"),
        Line2D([], [], color=E.DESPUES, lw=2.2,
               label="Después: demanda reconstruida")],
        loc="upper center",
        bbox_to_anchor=(0.5, _bajo_de_los_ejes(fig, ejes.ravel(), 0.006)),
        ncol=3, fontsize=7.0, frameon=False, columnspacing=1.6,
        handlelength=1.8)

    return E.guardar(
        fig, "f3_03b_reconstruccion_mosaico", datos=pd.DataFrame(filas),
        procedencia=[
            "reformateo/documento/datos_cache/preproceso_m1.npz",
            "reformateo/documento/datos_cache/preproceso_m3.npz",
            "regla: D = max(0, D_net + suma de inversores) — "
            "data/preprocessing.py",
        ])


# La anatomia del umbral se dibuja para las diez series de demanda de las
# dos fronteras en una sola imagen. Los valores no viajan con la figura:
# los publica la tabla del umbral, que da por entidad el rango
# intercuartilico, la distancia de la cola, los dos candidatos con el
# aplicado en negrita y las horas retiradas. Ese reparto es lo que permite
# meter diez paneles donde antes cabian tres: sin los rotulos largos, cada
# panel solo tiene que sostener la geometria.
ANATOMIA_ALTO_MINIMO_PT = 9.0   # alto de copia por debajo del cual el
                                # ordinal saldria fuera de su caja


def f34_anatomia_umbral():
    """
    F3.4b — La anatomia del umbral: el rango intercuartilico como longitud.

    La figura del umbral dice quien manda en cada serie, pero no como se
    construye ninguno de los dos candidatos. Aqui el ``5 · IQR`` deja de
    ser notacion: la caja de la mitad central se apila cinco veces sobre el
    tercer cuartil y el primer criterio es donde aterriza la quinta copia,
    de modo que la multiplicacion se cuenta con el ojo.

    Diez paneles, cinco instituciones en el orden fijo a lo ancho y las dos
    fronteras apiladas, de manera que comparar una institucion entre M1 y
    M3 sea mirar hacia abajo. Las escalas verticales son independientes
    porque los rangos van de 0,32 a 24,35 kW; lo que se compara entre
    paneles no es una altura sino una relacion, que es si la cola con su
    prolongacion queda por encima o por debajo de la quinta copia. Esa
    relacion no depende de la escala de cada panel.

    Los ordinales de las copias se imprimen donde caben, y esa condicion se
    mide sobre el render ya compuesto y no se decide a ojo.
    """
    X_CAJA, ANCHO, X_COLA = 0.28, 0.34, 0.95
    datos, filas, pendientes = {}, [], []

    for cob in ("m1", "m3"):
        series, _ = D.preproceso(cob)
        for inst in E.ORDEN_INSTITUCIONES:
            s = series[f"{inst}__D_recon"]
            q25, q75 = float(s.quantile(0.25)), float(s.quantile(0.75))
            p995 = float(s.quantile(0.995))
            iqr = q75 - q25
            c1, c2 = q75 + 5 * iqr, 1.2 * p995
            datos[(cob, inst)] = {
                "q25": q25, "q75": q75, "iqr": iqr, "p995": p995,
                "c1": c1, "c2": c2, "umbral": max(c1, c2),
                "max": float(s.max()), "cola_iqr": (p995 - q75) / iqr,
                "manda": "primer criterio" if c1 >= c2 else "segundo criterio"}

    fig, ejes = plt.subplots(2, 5, figsize=(E.ANCHO_COMPLETO, 5.3))
    for fila, cob in enumerate(("m1", "m3")):
        for col, inst in enumerate(E.ORDEN_INSTITUCIONES):
            ax = ejes[fila][col]
            d = datos[(cob, inst)]
            iqr, q25, q75 = d["iqr"], d["q25"], d["q75"]
            alto = max(d["c1"], d["c2"], d["max"])
            bajo = max(0.0, q25 - 0.10 * alto)
            ax.set_ylim(bajo, alto * 1.07)
            ax.set_xlim(-0.15, 1.32)
            span = ax.get_ylim()[1] - ax.get_ylim()[0]

            # La caja: la mitad central de las lecturas, que es el rango
            # intercuartilico dibujado como lo que es, una longitud.
            ax.add_patch(Rectangle((X_CAJA, q25), ANCHO, iqr,
                                   facecolor=E.APAGADO, edgecolor=E.TINTA,
                                   linewidth=0.9, zorder=3))

            # Cinco copias de esa misma caja, apiladas sobre el tercer
            # cuartil. Mismo ancho y mismo alto que la de abajo: son la
            # misma longitud repetida, y por eso se pueden contar.
            for k in range(5):
                base = q75 + k * iqr
                ax.add_patch(Rectangle((X_CAJA, base), ANCHO, iqr,
                                       facecolor=E.FONDO_BANDA,
                                       edgecolor=E.NEUTRO, linewidth=0.7,
                                       zorder=3))
                pendientes.append((ax, iqr / span, X_CAJA + ANCHO / 2,
                                   base + iqr / 2, str(k + 1)))

            # La cola: hasta donde llega el percentil 99,5 desde el cuerpo,
            # y su prolongacion del 20 %. El percentil se marca con una
            # raya y no con un circulo hueco, porque el circulo hueco ya
            # significa otra cosa en la figura siguiente.
            ax.plot([X_COLA, X_COLA], [q75, d["p995"]], color=E.NEUTRO,
                    linewidth=0.8, linestyle=":", zorder=3)
            ax.plot([X_COLA - 0.12, X_COLA + 0.12], [d["p995"], d["p995"]],
                    color=E.NEUTRO, linewidth=1.2, zorder=5)
            ax.add_patch(Rectangle((X_COLA - 0.10, d["p995"]), 0.20,
                                   0.2 * d["p995"], facecolor=E.ALERTA,
                                   alpha=0.22, edgecolor=E.ALERTA,
                                   linewidth=0.7, zorder=3))

            # Los dos cortes. El que manda va en ambar y con trazo lleno; el
            # que pierde, en gris y discontinuo. El maximo de la formula se
            # lee entonces sin aritmetica: gana el mas alto y es el pintado.
            gana_primero = d["c1"] >= d["c2"]
            assert (d["c1"] if gana_primero else d["c2"]) == d["umbral"]
            for valor, es_ganador in ((d["c1"], gana_primero),
                                      (d["c2"], not gana_primero)):
                ax.plot([0.0, 1.20], [valor, valor],
                        color=E.ALERTA if es_ganador else E.NEUTRO,
                        linewidth=1.4 if es_ganador else 0.9,
                        linestyle="-" if es_ganador else (0, (3.5, 2)),
                        zorder=6)
            ax.plot([X_CAJA - 0.05, X_CAJA + ANCHO + 0.05],
                    [d["max"], d["max"]], color=E.TINTA, linewidth=1.0,
                    zorder=6)

            # Lo unico escrito en el panel: quien es y cuanto mide su
            # rango. El resto de los valores los publica la tabla.
            if fila == 0:
                ax.set_title(E.etiqueta_institucion(inst), fontsize=8.2,
                             pad=13)
            ax.text(0.5, 1.015, f"IQR = {E.fmt_miles(iqr, 1)} kW",
                    transform=ax.transAxes, fontsize=6.3, color=E.NEUTRO,
                    ha="center", va="bottom")
            ax.set_xticks([])
            ax.spines["bottom"].set_visible(False)
            ax.grid(axis="x", visible=False)
            ax.grid(axis="y", linewidth=0.5)
            ax.tick_params(axis="y", labelsize=6.4)
            # Un decimal solo cuando hace falta: con el eje llegando a
            # 160 kW, «160,0» gasta ancho y no informa de nada.
            dec = 0 if span > 30 else 1
            ax.yaxis.set_major_formatter(
                FuncFormatter(lambda v, _, d=dec: E.fmt_miles(v, d)))

            filas.append({"frontera": cob.upper(), "institucion": inst,
                          "q25_kW": d["q25"], "q75_kW": d["q75"],
                          "iqr_kW": iqr, "primer_criterio_kW": d["c1"],
                          "p995_kW": d["p995"],
                          "segundo_criterio_kW": d["c2"],
                          "umbral_kW": d["umbral"], "max_kW": d["max"],
                          "manda": d["manda"],
                          "cola_sobre_q75_en_iqr": d["cola_iqr"]})

        ejes[fila][0].set_ylabel("Demanda (kW)", fontsize=7.4)
        # La frontera rotula la fila entera, en su color, fuera del area de
        # dato. Va en dos lineas porque el nombre completo mide 2,3
        # pulgadas y la fila solo tiene 1,9 de alto.
        ejes[fila][0].text(-0.78, 0.5, E.titulo_cobertura(cob, dos_lineas=True),
                           transform=ejes[fila][0].transAxes, rotation=90,
                           fontsize=7.0, fontweight="bold",
                           color=E.COBERTURAS[cob], ha="center", va="center")

    fig.tight_layout(rect=(0, 0.085, 1, 0.995), w_pad=0.6, h_pad=2.2)

    # Los ordinales, decididos sobre el render ya compuesto: una copia que
    # mide menos de nueve puntos tipograficos no puede alojar su numero.
    puestos = 0
    for ax, fraccion, x, y, texto in pendientes:
        alto_pt = fraccion * ax.get_position().height * fig.get_figheight() * 72
        if alto_pt >= ANATOMIA_ALTO_MINIMO_PT:
            ax.text(x, y, texto, fontsize=5.6, color=E.NEUTRO, ha="center",
                    va="center", zorder=4)
            puestos += 1
    print(f"  [anatomía] ordinales impresos: {puestos} de {len(pendientes)}")

    fig.legend(handles=[
        Patch(facecolor=E.APAGADO, edgecolor=E.TINTA, linewidth=0.9,
              label="Mitad central de las lecturas (IQR)"),
        Patch(facecolor=E.FONDO_BANDA, edgecolor=E.NEUTRO, linewidth=0.7,
              label="Cinco copias del mismo rango"),
        Line2D([], [], color=E.NEUTRO, linewidth=1.2, label="Percentil 99,5"),
        Patch(facecolor=E.ALERTA, alpha=0.22, edgecolor=E.ALERTA,
              linewidth=0.7, label="Su prolongación del 20 %"),
        Line2D([], [], color=E.ALERTA, linewidth=1.4,
               label="Criterio que fija el umbral"),
        Line2D([], [], color=E.NEUTRO, linewidth=0.9, linestyle=(0, (3.5, 2)),
               label="Criterio descartado"),
        Line2D([], [], color=E.TINTA, linewidth=1.0,
               label="Máximo observado")],
        loc="upper center",
        bbox_to_anchor=(0.5, _bajo_de_los_ejes(fig, ejes.ravel(), 0.008)),
        ncol=4, fontsize=6.6, frameon=False, handlelength=1.6,
        columnspacing=1.4, labelspacing=0.5)

    return E.guardar(
        fig, "f3_04b_anatomia_umbral", datos=pd.DataFrame(filas),
        procedencia=[
            "reformateo/documento/datos_cache/preproceso_m1.npz",
            "reformateo/documento/datos_cache/preproceso_m3.npz",
            "criterio: max(Q75 + 5*IQR, P99,5 * 1,2) — "
            "data/xm_data_loader.py::_clean",
        ])


# ─────────────────────────────────────────────────────────────────────────────
def _series_derivadas() -> set:
    """
    Pares (institución, frontera) cuya serie no es una medición propia.

    Una institución sin medidor en una frontera se representa escalando el
    de la otra. Eso no se declara aquí a mano: se comprueba sobre el dato,
    exigiendo que el cociente entre las dos series sea constante en todo
    el horizonte, y se atribuye a la frontera cuya serie es la fracción,
    que es la que se obtuvo multiplicando. La única que cumple hoy es la
    Universidad Mariana bajo M3, con un cociente de 0,3 y desviación
    5,9e-18, mientras que en las otras cuatro el cociente varía entre
    0,08 y 2,5.
    """
    s = {c: D.preproceso(c)[0] for c in ("m1", "m3")}
    fuera = set()
    for inst in E.ORDEN_INSTITUCIONES:
        # Las series que se comparan son las que ve el umbral: la lectura
        # del medidor para la demanda y la generación tal como entra al
        # filtro. La generación devuelta no sirve, porque en la frontera
        # secundaria vale cero en las cinco y un cociente nulo es
        # constante sin que haya ninguna serie escalada.
        for magnitud, sufijo in (("demanda", "D_raw"), ("generación", "G_ems")):
            a = s["m1"][f"{inst}__{sufijo}"]
            b = s["m3"][f"{inst}__{sufijo}"]
            ok = a.notna() & b.notna() & (a.abs() > 1e-9)
            if not ok.any():
                continue
            razon = (b[ok] / a[ok])
            if float(razon.std()) >= 1e-9:
                continue
            factor = float(razon.mean())
            if abs(factor) < 1e-12:
                continue
            if abs(factor) < 1:
                fuera.add(("m3", inst, magnitud))
            elif abs(factor) > 1:
                fuera.add(("m1", inst, magnitud))
    return fuera


def _caso_atipico(cobertura: str, censo, detalle, series, derivadas):
    """
    La hora retirada que la figura dibuja, elegida por regla.

    Entre todas las horas que el umbral retira se toman las aisladas, es
    decir, aquellas cuya hora anterior y posterior no lo están, y de esas
    la que más sobresale del umbral en términos relativos. La aislación es
    imprescindible por dos razones: en un tramo de horas seguidas no se ve
    que la interpolación cierre el hueco, y el tramo de tres horas del 24
    de abril es una rampa de mañana cuya primera hora sobresale un 1,3 %,
    de modo que enseñaría un criterio que apenas discrimina.

    Quedan fuera las series que no son una medición propia de esa
    frontera sino la de la otra escalada: dibujarlas repetiría en la
    segunda fila el mismo aparato y la misma hora de la primera, con otro
    eje, y la fila dejaría de comprobar nada.

    Devuelve ``None`` cuando la frontera no tiene ninguna hora retirada
    aislada. No es una hipótesis: si el multiplicador del primer criterio
    pasara de 5 a 7, la frontera principal se quedaría sin ninguna.
    """
    mejor = None
    for inst in E.ORDEN_INSTITUCIONES:
        for magnitud in ("demanda", "generación"):
            if (cobertura, inst, magnitud) in derivadas:
                continue
            r = detalle[(inst, magnitud)]
            m = r["out"]
            if not m.any():
                continue
            clave = censo.loc[(censo.institucion == inst) &
                              (censo.magnitud == magnitud),
                              "serie_entrada"].iat[0]
            entrada = series[clave]
            for t in m.index[m]:
                pos = m.index.get_loc(t)
                previo = bool(m.iloc[pos - 1]) if pos > 0 else False
                post = bool(m.iloc[pos + 1]) if pos + 1 < len(m) else False
                if previo or post:
                    continue
                exceso = (entrada[t] - r["umbral"]) / r["umbral"]
                if mejor is None or exceso > mejor["exceso"]:
                    mejor = {"inst": inst, "magnitud": magnitud, "hora": t,
                             "exceso": exceso, "entra": float(entrada[t]),
                             "umbral": r["umbral"],
                             "sale": float(r["limpia"][t]),
                             "entrada": entrada, "limpia": r["limpia"]}
    return mejor


def f35_umbral_caso():
    """
    F3.5 — La hora que el umbral retira, y con qué se queda la serie.

    Una fila por frontera, y en cada una la hora retirada con su antes y su
    después sobre una ventana de tres días, que es la escala a la que un
    pico se distingue de la operación normal. Sobre las 6.144 horas del
    horizonte esa hora es un marcador sobre una maraña.

    **Qué dejó de hacer esta figura.** Tenía un segundo panel con el
    criterio de las diez series en múltiplos del percentil 99,5 de cada
    una. Se retiró por cinco razones, y las tres primeras son de lectura:
    el eje era compartido pero cada fila usaba su propia normalización, de
    modo que invitaba a comparar magnitudes que no lo son; el círculo del
    corte del primer criterio solo asomaba en dos de las diez filas y en
    las otras ocho quedaba oculto bajo el rombo, sin que nada lo advirtiera;
    y el rombo se llamaba umbral aplicado pero su posición era el umbral
    dividido por el percentil, de manera que el mismo objeto aparecía dos
    veces, dibujado y en la columna del margen, con dos valores distintos.
    La quinta razón es la decisiva: la anatomía del umbral construye los
    dos candidatos en kilovatios reales, para las diez series y las dos
    fronteras, y la tabla del umbral publica los valores. Aquel panel era
    una versión comprimida y normalizada de lo mismo.

    Queda el caso, que es lo único que no hace ninguna otra pieza.
    """
    derivadas = _series_derivadas()
    fig, ejes = plt.subplots(2, 1, figsize=(E.ANCHO_COMPLETO, 4.4))
    filas, hallados = [], 0

    for fila, cob in enumerate(("m1", "m3")):
        ax = ejes[fila]
        censo, detalle, series = _censo_limpieza(cob)
        mejor = _caso_atipico(cob, censo, detalle, series, derivadas)

        if mejor is None:
            # Que una frontera se quede sin caso es un resultado posible, no
            # un fallo: con el multiplicador del primer criterio en 7 la
            # principal no retiraría ninguna hora. El panel lo dice.
            ax.set_xticks([])
            ax.set_yticks([])
            for lado in ("top", "right", "bottom", "left"):
                ax.spines[lado].set_visible(False)
            ax.add_patch(Rectangle((0.02, 0.06), 0.96, 0.88,
                                   transform=ax.transAxes,
                                   facecolor=E.FONDO_BANDA, edgecolor="none"))
            ax.text(0.5, 0.5, "ninguna hora retirada en esta frontera",
                    transform=ax.transAxes, ha="center", va="center",
                    fontsize=8.0, color=E.NEUTRO, style="italic")
            filas.append({"frontera": cob.upper(), "caso": "ninguno"})
            continue

        hallados += 1
        t = mejor["hora"]
        ventana = slice(t - pd.Timedelta("36h"), t + pd.Timedelta("36h"))
        obs = mejor["entrada"][ventana]
        fin = mejor["limpia"][ventana]
        ancla_previa = float(mejor["entrada"][t - pd.Timedelta("1h")])
        ancla_post = float(mejor["entrada"][t + pd.Timedelta("1h")])

        # El contrato de lo que se dibuja: la hora sobresale del umbral,
        # queda aislada, y por eso la interpolación la deja justo en el
        # punto medio de sus dos vecinas.
        assert mejor["entra"] > mejor["umbral"], (cob, mejor["entra"])
        assert abs(mejor["sale"] - (ancla_previa + ancla_post) / 2) < 1e-6, \
            (cob, mejor["sale"], ancla_previa, ancla_post)

        # La serie que entra al umbral, por debajo y con trazo propio: sin
        # ella el «antes» eran dos marcadores sueltos y la figura entregaba
        # solo la salida. Las dos curvas coinciden en toda la ventana menos
        # donde la limpieza intervino, que es lo que prueba que el
        # tratamiento es puntual y no un alisado de la serie entera.
        tocadas = int((~np.isclose(obs.values, fin.values, equal_nan=True)).sum())
        ax.plot(obs.index, obs.values, color=E.ANTES, linewidth=0.9,
                linestyle=(0, (2, 1.5)), zorder=3,
                label="Serie que entra al umbral")
        ax.plot(fin.index, fin.values, color=E.TINTA, linewidth=1.4, zorder=5,
                label="Serie ya limpia")
        ax.axhline(mejor["umbral"], color=E.ALERTA, linewidth=1.1,
                   linestyle="--",
                   label=f"Umbral: {E.fmt_miles(mejor['umbral'], 1)} kW")
        lo = float(min(fin.min(), obs.min()))
        hi = float(max(obs.max(), mejor["entra"]))
        margen = 0.16 * (hi - lo)
        ax.axhspan(mejor["umbral"], hi + 3 * margen, color=E.ALERTA,
                   alpha=0.07, linewidth=0, zorder=0)
        ax.plot([t], [mejor["entra"]], marker="o", markersize=7,
                markerfacecolor="white", markeredgecolor=E.ANTES,
                markeredgewidth=1.6, linestyle="none",
                label="Lectura retirada", zorder=6)
        ax.plot([t], [mejor["sale"]], marker="s", markersize=6,
                color=E.DESPUES, linestyle="none",
                label="Valor con que quedó", zorder=6)
        ax.annotate("", xy=(t, mejor["sale"]), xytext=(t, mejor["entra"]),
                    arrowprops=dict(arrowstyle="->", color=E.NEUTRO,
                                    linewidth=0.9, shrinkA=4, shrinkB=4))
        ax.plot([t - pd.Timedelta("1h"), t + pd.Timedelta("1h")],
                [ancla_previa, ancla_post], color=E.DESPUES, linewidth=0.9,
                linestyle=":", zorder=4)
        ax.set_ylim(lo - margen, hi + 1.9 * margen)
        # Cuántas horas de la ventana difieren entre entrada y salida. En
        # la frontera secundaria esa institución arrastra 119 horas
        # tratadas frente a las 4 de la principal, de modo que la cifra
        # cambia de una fila a otra y conviene que se lea.
        ax.text(0.995, 0.035, f"{tocadas} de {len(obs)} horas de la ventana "
                f"difieren entre las dos curvas", transform=ax.transAxes,
                fontsize=6.2, color=E.NEUTRO, ha="right", va="bottom")
        ax.set_ylabel("Demanda (kW)" if mejor["magnitud"] == "demanda"
                      else "Generación (kW)", fontsize=7.6)
        ax.set_title(f"{E.etiqueta_institucion(mejor['inst'])}, "
                     f"{E.fmt_fecha(t, 'dia_corto')}: entra con "
                     f"{E.fmt_miles(mejor['entra'], 1)} kW y sale con "
                     f"{E.fmt_miles(mejor['sale'], 1)} kW", fontsize=8.2,
                     pad=6)
        # Una marca por día: con marcas cada doce horas las siete etiquetas
        # se imprimían una encima de otra.
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=(12,)))
        ax.xaxis.set_major_formatter(FuncFormatter(
            lambda v, _: mdates.num2date(v).strftime("%d/%m")))
        ax.tick_params(labelsize=7)
        if fila == 1:
            ax.set_xlabel("Día y mes de 2025", fontsize=7.6)

        filas.append({
            "frontera": cob.upper(), "caso": "dibujado",
            "institucion": mejor["inst"], "magnitud": mejor["magnitud"],
            "hora": str(t), "horas_ventana": len(obs),
            "horas_que_difieren": tocadas, "entra_kW": mejor["entra"],
            "umbral_kW": mejor["umbral"],
            "exceso_pct": 100 * mejor["exceso"], "sale_kW": mejor["sale"],
            "ancla_previa_kW": ancla_previa, "ancla_posterior_kW": ancla_post})

    assert hallados, "ninguna frontera tiene una hora retirada aislada"
    fig.tight_layout(rect=(0, 0.075, 1, 0.995), h_pad=2.2)

    # La frontera rotula la fila entera, fuera del área de dato. Su sitio
    # se mide sobre el render y no se fija en fracción del eje: los dos
    # paneles tienen marcas de distinto ancho, de modo que a una fracción
    # fija el rótulo caía sobre el del eje en uno de los dos.
    fig.canvas.draw()
    render = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    for ax, cob in zip(ejes, ("m1", "m3")):
        bb = Bbox(inv.transform(ax.get_tightbbox(render)))
        # El desplazamiento cuenta el ancho del propio rótulo girado, que
        # son dos líneas de 7 puntos: con 0,012 el rótulo se montaba sobre
        # el del eje y la prueba de oclusión lo cazó en las dos filas.
        fig.text(bb.x0 - 0.030, (bb.y0 + bb.y1) / 2,
                 E.titulo_cobertura(cob, dos_lineas=True), rotation=90,
                 fontsize=7.0, fontweight="bold", color=E.COBERTURAS[cob],
                 ha="center", va="center")
    # La leyenda es común a las dos filas y se coloca midiendo, por debajo
    # del rótulo de eje más bajo.
    marcas = [
        Line2D([], [], color=E.ANTES, linewidth=0.9, linestyle=(0, (2, 1.5)),
               label="Serie que entra al umbral"),
        Line2D([], [], color=E.TINTA, linewidth=1.4, label="Serie ya limpia"),
        Line2D([], [], color=E.ALERTA, linewidth=1.1, linestyle="--",
               label="Umbral de atípicos"),
        Line2D([], [], marker="o", markerfacecolor="white", linestyle="none",
               markeredgecolor=E.ANTES, markeredgewidth=1.6, markersize=7,
               label="Lectura retirada"),
        Line2D([], [], marker="s", color=E.DESPUES, linestyle="none",
               markersize=6, label="Valor con que quedó"),
    ]
    fig.legend(handles=marcas, loc="upper center",
               bbox_to_anchor=(0.5, _bajo_de_los_ejes(fig, ejes, 0.008)),
               ncol=5, fontsize=6.5, frameon=False, handlelength=1.8,
               columnspacing=1.2)

    return E.guardar(
        fig, "f3_05_umbral_caso", datos=pd.DataFrame(filas),
        procedencia=[
            "reformateo/documento/datos_cache/preproceso_m1.npz",
            "reformateo/documento/datos_cache/preproceso_m3.npz",
            "criterio: max(Q75 + 5*IQR, P99,5 * 1,2) — "
            "data/xm_data_loader.py::_clean",
            "caso: hora retirada aislada de mayor exceso relativo sobre el "
            "umbral, elegida por regla y no fijada a mano",
        ])


# Los tres huecos de la escalera van fijados en el generador y no buscados
# por codigo, igual que el dia de la reconstruccion: los asertos comprueban
# que cada uno mantiene la longitud y el reparto que la figura afirma, y
# detienen la corrida si dejan de tenerlos. Los dos primeros son del mismo
# medidor bajo M1, que es donde la rampa de la interpolacion se ve, porque
# bajo M3 ese mismo hueco de tres horas cae en vez de subir y la recta no
# se distingue de una linea plana. El tercero es el hueco mas largo de todo
# el estudio, que esta bajo M3, y se comprueba que lo sigue siendo en las
# dos fronteras.
HUECOS_ESCALERA = [
    ("m1", "HUDN", "2025-07-26 05:00", 3, (3, 0, 0)),
    ("m1", "HUDN", "2025-12-12 21:00", 13, (3, 10, 0)),
    ("m3", "UCC", "2025-12-11 09:00", 49, (3, 24, 22)),
]
# Alcance de la cascada: 3 horas de interpolacion mas 24 de arrastre hacia
# adelante mas 24 hacia atras. Se calcula aqui una sola vez porque es la
# cifra contra la que la figura mide el hueco mas largo del estudio.
ALCANCE_CASCADA = 3 + 24 + 24


def f36_escalera_huecos():
    """
    F3.6 — La escalera: la longitud del hueco decide el tratamiento.

    Tres huecos reales de longitud creciente, uno por peldaño, con el eje
    horizontal en horas desde el inicio del hueco, que es la magnitud de la
    que depende la regla. Los tres comparten figura a proposito: separados,
    la unica diferencia entre ellos, la longitud, viajaria entre paginas,
    que es donde peor se compara.

    Abajo, el presupuesto de horas de las diez series de demanda, las cinco
    instituciones en las dos fronteras. Presentarlo por una sola frontera
    engaña: bajo M1, Udenar y la UCC salen con cero horas tratadas, y eso
    no significa que no tuvieran cortes sino que su medidor es neto y el
    recorte a cero de la reconstruccion cerro esos huecos antes de que la
    limpieza los viera. Bajo M3, las mismas dos instituciones acumulan 97 y
    126 horas.

    El cuarto tratamiento, el relleno con cero, no tiene ningun caso que
    enseñar. La cascada cierra cualquier hueco de hasta 51 horas y el mas
    largo del estudio mide 49, de modo que en las veinte series de las dos
    fronteras ninguna hora llega a el. Eso se publica como resultado, no se
    omite.
    """
    censo, detalle, series, mas_largo = {}, {}, {}, 0
    for cob in ("m1", "m3"):
        c, d, s = _censo_limpieza(cob)
        censo[cob] = c[c.magnitud == "demanda"].set_index("institucion")
        detalle[cob], series[cob] = d, s
        for inst in E.ORDEN_INSTITUCIONES:
            for magnitud in ("demanda", "generación"):
                for _, _, n in _rachas(d[(inst, magnitud)]["entran"]):
                    mas_largo = max(mas_largo, n)

    fig = plt.figure(figsize=(E.ANCHO_COMPLETO, 6.0))
    malla = fig.add_gridspec(2, 3, height_ratios=(1.0, 1.06), hspace=0.62,
                             wspace=0.32)
    ejes = [fig.add_subplot(malla[0, j]) for j in range(3)]
    ax_pres = fig.add_subplot(malla[1, :2])
    ax_cero = fig.add_subplot(malla[1, 2])

    filas_csv = []
    largo_declarado = max(x[3] for x in HUECOS_ESCALERA)
    for ax, (cob, inst, inicio, largo, reparto) in zip(ejes, HUECOS_ESCALERA):
        r = detalle[cob][(inst, "demanda")]
        t0 = pd.Timestamp(inicio)
        candidatas = [x for x in _rachas(r["entran"]) if x[0] == t0]
        assert candidatas, f"{cob}/{inst}: no hay hueco que empiece en {t0}"
        _, t1, n = candidatas[0]
        assert n == largo, f"{inst} {t0}: el hueco mide {n} h, no {largo}"
        tramo = slice(t0, t1)
        n_int = int(r["interp"][tramo].sum())
        n_ff = int(r["ffill"][tramo].sum())
        n_bf = int(r["bfill"][tramo].sum())
        assert (n_int, n_ff, n_bf) == reparto, (
            f"{inst} {t0}: reparto {(n_int, n_ff, n_bf)}, no {reparto}")
        assert int(r["cero"][tramo].sum()) == 0, (
            f"{inst} {t0}: hay horas rellenas con cero")
        if largo == largo_declarado:
            assert n == mas_largo, (
                f"el tercer peldaño mide {n} h y el hueco más largo del "
                f"estudio mide {mas_largo}")

        entrada = series[cob][censo[cob].loc[inst, "serie_entrada"]]
        limpia = r["limpia"]
        idx = r["entran"].index
        ctx = max(2, int(round(0.22 * n)))
        ini_v = idx[max(0, idx.get_loc(t0) - ctx)]
        fin_v = idx[min(len(idx) - 1, idx.get_loc(t1) + ctx)]

        def eje_x(ts):
            return (pd.DatetimeIndex(ts) - t0) / pd.Timedelta("1h")

        obs = entrada[ini_v:fin_v]
        ax.axvspan(-0.5, n - 0.5, facecolor="none", edgecolor="#CFCFCF",
                   hatch="///", linewidth=0.0, zorder=0)
        ax.plot(eje_x(obs.index), obs.values, color=E.TINTA, linewidth=1.1,
                zorder=4)
        vis = obs.dropna()
        ax.plot(eje_x(vis.index), vis.values, marker="o", markersize=2.4,
                linestyle="none", color=E.TINTA, zorder=4)

        rell = limpia[tramo]
        # El puente incluye las dos anclas: sin ellas el relleno arranca
        # separado de la serie observada y se lee como otra curva.
        puente = limpia[t0 - pd.Timedelta("1h"):t1 + pd.Timedelta("1h")]
        ax.plot(eje_x(puente.index), puente.values, color=E.NEUTRO,
                linewidth=0.8, zorder=3)
        for mascara, color, marca, ancho in (
                (r["interp"], E.DESPUES, "o", 1.8),
                (r["ffill"], E.NEUTRO, "s", 1.5),
                (r["bfill"], E.NEUTRO, "^", 1.5)):
            m = mascara[tramo]
            if not m.any():
                continue
            sub = rell[m.values]
            ax.plot(eje_x(sub.index), sub.values, color=color, linewidth=ancho,
                    zorder=5)
            # Con mas de doce puntos los marcadores se funden en una barra
            # continua; entonces la forma la lleva uno solo, en el centro.
            if len(sub) <= 12:
                ax.plot(eje_x(sub.index), sub.values, marker=marca,
                        markersize=3.6, linestyle="none", color=color, zorder=6)
            else:
                c = sub.iloc[[len(sub) // 2]]
                ax.plot(eje_x(c.index), c.values, marker=marca, markersize=4.6,
                        linestyle="none", color=color, zorder=6)

        ancla_previa = float(entrada[t0 - pd.Timedelta("1h")])
        ancla_post = float(entrada[t1 + pd.Timedelta("1h")])
        ax.plot([-1, n], [ancla_previa, ancla_post], marker="o", markersize=4.6,
                linestyle="none", color=E.TINTA, zorder=7)

        vals = np.concatenate([vis.values, rell.values])
        lo, hi = float(vals.min()), float(vals.max())
        span = max(hi - lo, 1e-6)
        base = lo - 0.52 * span
        ax.set_ylim(base - 0.05 * span, hi + 0.18 * span)

        # La meseta no se queda en la ultima lectura observada sino en la
        # tercera hora interpolada. Solo se rotula cuando la separacion es
        # dibujable: por debajo del 4 % del alto del panel, la linea de
        # referencia y la meseta se imprimirian una encima de la otra.
        meseta = float(rell.iloc[2]) if n > 3 else np.nan
        if n > 3 and abs(meseta - ancla_previa) > 0.04 * span:
            ax.axhline(ancla_previa, color=E.TINTA, linewidth=0.7,
                       linestyle=":", alpha=0.75, zorder=2)
            ax.text(n * 0.52, ancla_previa - 0.04 * span,
                    "última lectura observada", fontsize=5.9, color=E.TINTA,
                    ha="center", va="top")

        # Las llaves de longitud, bajo el dato. Miden en horas, que es lo
        # que se compara entre paneles: los tres tienen el mismo ancho
        # impreso y escalas horizontales distintas, de modo que la
        # comparacion la lleva la cifra y no la longitud del trazo.
        tramos = [(0, reparto[0]), (reparto[0], reparto[1]),
                  (reparto[0] + reparto[1], reparto[2])]
        niveles = [0.06, 0.20, 0.34]
        for k, (desde, cuantas) in enumerate(tramos):
            if not cuantas:
                continue
            y = base + niveles[k] * span
            ax.plot([desde - 0.4, desde + cuantas - 0.6], [y, y],
                    color=E.NEUTRO, linewidth=0.8, solid_capstyle="butt")
            for xx in (desde - 0.4, desde + cuantas - 0.6):
                ax.plot([xx, xx], [y - 0.028 * span, y + 0.028 * span],
                        color=E.NEUTRO, linewidth=0.8)
            ax.text(desde + cuantas / 2 - 0.5, y + 0.040 * span,
                    f"{cuantas} h", fontsize=6.4, color=E.NEUTRO,
                    ha="center", va="bottom")

        # La banda de las llaves queda bajo el dato y no es area de medida:
        # rotularla con marcas del eje invita a leer que la serie bajo
        # hasta ahi, y en el hueco de 49 horas la marca del cero caia
        # dentro de la banda.
        ax.set_yticks([v for v in ax.get_yticks()
                       if lo - 0.03 * span <= v <= hi + 0.18 * span])
        ax.set_xlim(-ctx - 0.6, n + ctx + 0.6)
        ax.set_title(f"{E.etiqueta_institucion(inst)} · "
                     f"{t0.day} {MESES_ES[t0.month - 1]} {t0.year}\n"
                     f"hueco de {n} horas", fontsize=8.2, pad=14)
        # Cada panel declara su frontera: los tres ya no salen de la misma.
        ax.text(0.5, 1.015, E.COBERTURA_NOMBRE[cob], transform=ax.transAxes,
                fontsize=6.0, fontweight="bold", color=E.COBERTURAS[cob],
                ha="center", va="bottom")
        ax.set_xlabel("Horas desde el inicio del hueco", fontsize=7.2)
        ax.tick_params(labelsize=7)
        ax.xaxis.set_major_locator(
            MultipleLocator(1 if n <= 4 else (6 if n <= 16 else 12)))
        filas_csv.append({
            "bloque": "peldaño", "frontera": cob.upper(), "institucion": inst,
            "inicio": str(t0), "horas": n, "interpoladas": n_int,
            "arrastre_adelante": n_ff, "arrastre_atras": n_bf, "cero": 0,
            "ancla_previa_kW": ancla_previa, "ancla_posterior_kW": ancla_post,
            "meseta_kW": meseta})
    ejes[0].set_ylabel("Demanda (kW)")

    # ── el presupuesto de horas, en las dos fronteras ────────────────────
    tope = max(float((censo[c]["interpoladas"] + censo[c]["arrastradas"]).max())
               for c in ("m1", "m3"))
    borrados = []
    for k, inst in enumerate(E.ORDEN_INSTITUCIONES):
        for j, cob in enumerate(("m1", "m3")):
            f = censo[cob].loc[inst]
            n_i, n_a = int(f["interpoladas"]), int(f["arrastradas"])
            y = k - 0.19 + 0.38 * j
            ax_pres.text(-0.012 * tope, y, cob.upper(), fontsize=6.2,
                         fontweight="bold", color=E.COBERTURAS[cob],
                         ha="right", va="center")
            if n_i:
                ax_pres.barh(y, n_i, height=0.30, color=E.DESPUES, zorder=3)
            if n_a:
                ax_pres.barh(y, n_a, left=n_i, height=0.30, color=E.NEUTRO,
                             edgecolor="white", linewidth=1.2, zorder=3)
            total = n_i + n_a
            if total:
                rotulo = f"{E.fmt_miles(total)} h"
                if f["atipicos"]:
                    rotulo += f"  ({int(f['atipicos'])} del umbral)"
                ax_pres.text(total + 0.015 * tope, y, rotulo, fontsize=6.4,
                             color=E.TINTA, va="center")
            else:
                # Un cero que no significa ausencia de cortes. Dejarlo en
                # «ninguna» era la lectura falsa que esta figura corrige.
                ax_pres.text(0.015 * tope, y, "0 · huecos cerrados antes",
                             fontsize=6.4, color=E.ALERTA, va="center")
                borrados.append(inst)
            filas_csv.append({
                "bloque": "presupuesto", "frontera": cob.upper(),
                "institucion": inst, "horas": total, "interpoladas": n_i,
                "arrastradas": n_a, "cero": 0,
                "atipicos_retirados": int(f["atipicos"])})
    E.eje_instituciones(ax_pres, eje="y")
    ax_pres.tick_params(axis="y", labelsize=7.5, pad=22)
    ax_pres.set_xlim(-0.13 * tope, tope * 1.42)
    ax_pres.set_xlabel("Horas tratadas en la serie de demanda (h)", fontsize=7.4)
    ax_pres.tick_params(axis="x", labelsize=7)
    ax_pres.grid(axis="y", visible=False)
    ax_pres.spines["left"].set_visible(False)
    ax_pres.set_title(
        f"El presupuesto: {E.fmt_miles(censo['m1']['entran'].sum())} horas "
        f"tratadas en M1 y {E.fmt_miles(censo['m3']['entran'].sum())} en M3",
        fontsize=8.5, pad=6)

    # ── el peldaño que no existe ─────────────────────────────────────────
    ax_cero.axis("off")
    ax_cero.add_patch(Rectangle((0.03, 0.04), 0.94, 0.90,
                                transform=ax_cero.transAxes,
                                facecolor=E.FONDO_BANDA, edgecolor="none",
                                zorder=0))
    ax_cero.text(0.5, 0.74, "0", fontsize=32, color=E.TINTA, ha="center",
                 va="center", transform=ax_cero.transAxes)
    ax_cero.text(0.5, 0.45, "horas rellenas con cero\nen las veinte series",
                 fontsize=7.0, color=E.TINTA, ha="center", va="center",
                 transform=ax_cero.transAxes)
    ax_cero.text(0.5, 0.19, f"el hueco más largo mide {mas_largo} h\ny la "
                 f"cascada alcanza {ALCANCE_CASCADA} h", fontsize=6.4,
                 color=E.NEUTRO, ha="center", va="center",
                 transform=ax_cero.transAxes)
    filas_csv.append({
        "bloque": "resumen", "institucion": "las veinte series",
        "interpoladas": int(sum(censo[c]["interpoladas"].sum()
                                for c in ("m1", "m3"))),
        "arrastradas": int(sum(censo[c]["arrastradas"].sum()
                               for c in ("m1", "m3"))),
        "cero": 0, "horas": int(sum(censo[c]["entran"].sum()
                                    for c in ("m1", "m3"))),
        "hueco_mas_largo_h": mas_largo, "alcance_cascada_h": ALCANCE_CASCADA})

    fig.tight_layout(rect=(0, 0.045, 1, 0.995))
    y_ejes = _bajo_de_los_ejes(fig, ejes, 0.008)
    # Una sola leyenda para los dos bloques: las llaves de los paneles
    # miden y esta nombra, de modo que ningun rotulo tenga que caber junto
    # a un tramo de tres horas.
    fig.legend(handles=[
        Line2D([], [], color=E.TINTA, linewidth=1.1, marker="o", markersize=3.4,
               label="Lectura observada"),
        Line2D([], [], color=E.DESPUES, linewidth=1.8, marker="o",
               markersize=3.6, label="Interpolación, hasta 3 h"),
        Line2D([], [], color=E.NEUTRO, linewidth=1.5, marker="s",
               markersize=3.6, label="Arrastre hacia adelante, hasta 24 h"),
        Line2D([], [], color=E.NEUTRO, linewidth=1.5, marker="^",
               markersize=3.6, label="Arrastre hacia atrás, hasta 24 h")],
        loc="upper center", bbox_to_anchor=(0.5, y_ejes), ncol=4, fontsize=6.8,
        frameon=False, handlelength=1.9, columnspacing=1.5)

    # La nota que impide la lectura falsa, bajo la franja y no en el pie:
    # quien mira solo el dibujo tiene que poder leerla ahi.
    if borrados:
        cuales = " y ".join(E.etiqueta_institucion(i) for i in borrados)
        fig.text(0.5, _bajo_de_los_ejes(fig, [ax_pres], 0.006),
                 f"Bajo M1, {cuales} llevan medidor neto y la reconstrucción "
                 f"cerró sus huecos antes de la limpieza: ese cero no es "
                 f"ausencia de cortes.", fontsize=6.4, color=E.ALERTA,
                 ha="center", va="top")

    return E.guardar(
        fig, "f3_06_escalera_huecos", datos=pd.DataFrame(filas_csv),
        procedencia=[
            "reformateo/documento/datos_cache/preproceso_m1.npz",
            "reformateo/documento/datos_cache/preproceso_m3.npz",
            "cascada: interpolación temporal límite 3 h, arrastre hacia "
            "adelante y hacia atrás límite 24 h, resto a cero — "
            "data/xm_data_loader.py::_clean",
            "los tres huecos van fijados en el generador y comprobados con "
            "asertos de longitud y reparto antes de dibujar",
        ])


# ─────────────────────────────────────────────────────────────────────────────
# Longitud de Pasto, en grados, y meridiano del huso. Entran en una sola
# cuenta, el mediodia solar del sitio, y por eso viven aqui y no en un
# modulo de datos: no son una medicion del proyecto sino la posicion de la
# ciudad y el convenio horario del pais.
LON_PASTO = -77.28
MERIDIANO_UTC5 = -75.0
# La vara de la banda del mediodia. Un huso mal puesto vale una hora
# entera, de modo que es la magnitud del fallo que esa banda descarta.
VARA_MINUTOS = 60


def _matriz_hora_dia(serie: pd.Series) -> pd.DataFrame:
    """Pivote hora del dia (24 filas) contra dia del horizonte."""
    base = serie.index.normalize()
    m = pd.DataFrame({"v": serie.values, "h": serie.index.hour, "d": base})
    return m.pivot_table(index="h", columns="d", values="v", aggfunc="mean")


def _mediodia_solar(dias) -> pd.Series:
    """
    Mediodia solar de Pasto, en hora local, dia a dia.

    Es el instante en que el sol cruza el meridiano del sitio. Se separa
    del mediodia del reloj por dos terminos: la distancia en longitud al
    meridiano del huso, que para Pasto son algo mas de nueve minutos, y la
    ecuacion del tiempo, que a lo largo del año vale hasta un cuarto de
    hora. Ninguno de los dos sale del dato medido, y por eso la curva
    sirve de patron externo contra el cual medirlo.
    """
    doy = np.array([d.dayofyear for d in dias])
    b = 2 * np.pi * (doy - 1) / 365.0
    ecuacion = 229.18 * (0.000075 + 0.001868 * np.cos(b) - 0.032077 * np.sin(b)
                         - 0.014615 * np.cos(2 * b) - 0.040849 * np.sin(2 * b))
    return pd.Series(12 + (MERIDIANO_UTC5 - LON_PASTO) * 4 / 60 - ecuacion / 60,
                     index=dias)


def _hora_media_generacion(piv: pd.DataFrame) -> pd.Series:
    """
    Hora media de la generacion de cada dia, ponderada por la energia.

    La hora h integra el intervalo [h, h+1), de modo que su centro en el
    reloj es h + 0,5: sin ese medio la cuenta sale media hora temprana.
    """
    centro = np.arange(24) + 0.5
    peso = piv.values.sum(axis=0)
    media = (centro[:, None] * piv.values).sum(axis=0) / np.where(peso > 0, peso, 1)
    return pd.Series(np.where(peso > 1, media, np.nan), index=piv.columns)


def f37_matrices():
    """
    F3.7 — Las tres comprobaciones con las que cierra el capítulo.

    Sustituye a los dos mapas de calor de hora contra día. Aquellos daban
    0,21 mm de papel por día, de modo que el eje de días no era legible
    sino una trama, y las tres comprobaciones que se les atribuían no se
    podían hacer sobre ellos con una vara: la zona horaria se juzgaba a
    ojo entre dos marcas separadas 17,7 mm; el difuminado de la banda
    solar no tenía unidad y además un desfase sistemático la desplaza en
    vez de difuminarla, de modo que la imagen no separaba las dos
    hipótesis; y la semana laboral es una estructura diaria que sobrevive
    a cualquier error de agregación horaria, que es lo que la figura decía
    estar comprobando. Barajar los 256 días al azar daba una imagen
    indistinguible de la real.

    Ahora son tres bandas que comparten el eje de días, de manera que una
    anomalía se lee verticalmente en las tres a la vez, y cada una lleva
    su vara dibujada:

      * el mediodía medido contra el solar de Pasto, con las dos reglas a
        una hora, que es lo que valdría el fallo que descarta;
      * la razón entre generación y demanda del día, adimensional y por
        eso comparable entre fronteras, con la regla en 1;
      * las horas que la limpieza tuvo que reponer, en mariposa.

    La generación es la MISMA serie en las dos fronteras, porque M1 y M3
    se separan en el circuito de consumo y no en el fotovoltaico. Un
    aserto lo comprueba antes de dibujar: es la premisa de la primera
    banda y del rótulo que la acompaña.
    """
    dem, rep, gen = {}, {}, None
    for cob in ("m1", "m3"):
        series, _ = D.preproceso(cob)
        dem[cob] = sum(series[f"{i}__D_limpia"] for i in D.AGENTES)
        g = sum(series[f"{i}__G_limpia"] for i in D.AGENTES)
        if gen is None:
            gen = g
        else:
            assert np.abs(gen.values - g.values).max() == 0, (
                "la generación difiere entre M1 y M3: la primera banda dejó "
                "de tener premisa y hay que investigarlo antes de publicar")
        # Horas que la limpieza tuvo que reponer, sumadas sobre las cinco
        # instituciones. Las retiradas por el umbral ya están dentro de las
        # imputadas, pero la unión se escribe entera para que la cuenta no
        # dependa de esa contención.
        m = None
        for i in D.AGENTES:
            u = (series[f"{i}__mask_imp_D"].astype(bool)
                 | series[f"{i}__mask_out_D"].astype(bool)
                 | series[f"{i}__mask_imp_G"].astype(bool)
                 | series[f"{i}__mask_out_G"].astype(bool))
            m = u.astype(int) if m is None else m + u.astype(int)
        rep[cob] = m.resample("D").sum()

    piv = _matriz_hora_dia(gen)
    dias = piv.columns
    x = np.arange(len(dias))
    medio = _hora_media_generacion(piv)
    solar = _mediodia_solar(dias)
    desfase = 60 * (medio - solar)
    e_gen = gen.resample("D").sum().reindex(dias)
    razon = {c: (e_gen / dem[c].resample("D").sum().reindex(dias))
             for c in ("m1", "m3")}
    movil = {c: razon[c].rolling(15, center=True, min_periods=5).median()
             for c in ("m1", "m3")}

    inicio = dias[0]
    meses = list(pd.date_range(inicio.normalize(), dias[-1], freq="MS"))
    marcas = [0] + [(f - inicio).days for f in meses]
    rotulos = [MESES_ES[inicio.month - 1]] + [MESES_ES[f.month - 1] for f in meses]

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(E.ANCHO_COMPLETO, 5.3), sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.0, 0.85]})

    # ── Banda 1: el mediodía medido contra el solar ──────────────────────
    # El eje se acota a la vara y media, no al recorrido del dato: con el
    # dato entero dentro, la banda de una hora quedaría en un hilo y la
    # comprobación dejaría de poder hacerse. Los días que se salen no se
    # ocultan, se fijan al borde con otra marca.
    alto = 1.25 * VARA_MINUTOS / 60
    ax1.plot(x, solar.values, color=E.TINTA, linewidth=1.2, zorder=4)
    for signo in (1, -1):
        ax1.plot(x, solar.values + signo * VARA_MINUTOS / 60, color=E.ALERTA,
                 linewidth=0.9, linestyle=(0, (4, 2)), zorder=3)
    dentro = desfase.abs() <= alto * 60
    ax1.plot(x[dentro.fillna(False)], medio.values[dentro.fillna(False)],
             marker="o", linestyle="none", markersize=1.8, color=E.GENERACION,
             markeredgewidth=0, zorder=5)
    fuera = (desfase.abs() > alto * 60).fillna(False)
    for k in x[fuera]:
        arriba = desfase.iloc[k] > 0
        ax1.plot([k], [solar.iloc[k] + (alto if arriba else -alto)],
                 marker="^" if arriba else "v", linestyle="none",
                 markersize=4.0, markerfacecolor="white",
                 markeredgecolor=E.ANTES, markeredgewidth=0.9, zorder=6)
    ax1.set_ylim(float(solar.min()) - 1.32 * alto,
                 float(solar.max()) + 1.32 * alto)
    ax1.set_ylabel("Hora local", fontsize=7.6)
    ax1.tick_params(labelsize=7)
    ax1.set_title("El mediodía de la generación contra el solar de Pasto  ·  "
                  "la generación es la misma en las dos fronteras",
                  fontsize=8.2, pad=6)
    # Los rótulos de la vara van fuera de sus curvas y no encima: entre
    # las dos reglas está la nube entera.
    k = int(0.62 * len(dias))
    ax1.text(k, float(solar.iloc[k]) + VARA_MINUTOS / 60 + 0.06,
             f"+{VARA_MINUTOS} min", fontsize=6.2, color=E.ALERTA,
             ha="center", va="bottom")
    # El de abajo se aparta del recuento, que ocupa el centro de la
    # franja inferior: la prueba de oclusión los encontró tocándose.
    ax1.text(int(0.90 * len(dias)),
             float(solar.iloc[int(0.90 * len(dias))]) - VARA_MINUTOS / 60 - 0.06,
             f"−{VARA_MINUTOS} min", fontsize=6.2, color=E.ALERTA,
             ha="center", va="top")
    j = int(0.22 * len(dias))
    ax1.text(j, float(solar.iloc[j]) - 1.22 * alto,
             f"desfase medio {E.fmt_miles(desfase.mean(), 1)} min · "
             f"{int(dentro.sum())} de {int(desfase.notna().sum())} días "
             f"dentro de la vara", fontsize=6.2, color=E.NEUTRO, ha="left",
             va="bottom")

    # ── Banda 2: qué fracción del día cubre el sol ───────────────────────
    # La razón es adimensional y por eso admite las dos fronteras en un
    # mismo eje, cosa que los kilovatios no: M1 y M3 miden circuitos de
    # tamaño distinto.
    ax2.axhline(1.0, color=E.NEUTRO, linewidth=0.9, linestyle=(0, (4, 2)),
                zorder=2)
    estilos = {"m1": dict(linestyle="-", marker="o"),
               "m3": dict(linestyle=(0, (3.5, 2)), marker="^")}
    for cob in ("m1", "m3"):
        ax2.plot(x, razon[cob].values, marker=estilos[cob]["marker"],
                 linestyle="none", markersize=1.7, color=E.COBERTURAS[cob],
                 alpha=0.42, markeredgewidth=0, zorder=3)
        ax2.plot(x, movil[cob].values, color=E.COBERTURAS[cob], linewidth=1.6,
                 linestyle=estilos[cob]["linestyle"], zorder=5)
        med = float(razon[cob].median())
        ax2.text(len(dias) + 2, float(movil[cob].dropna().iloc[-1]),
                 f"{cob.upper()} · mediana {E.fmt_miles(med, 2)}", fontsize=6.4,
                 color=E.COBERTURAS[cob], ha="left", va="center")
    sobre = int((razon["m3"] > 1).sum())
    # La franja de encima del dato queda libre a propósito para el
    # recuento: dentro de la nube el rótulo se imprimía sobre los puntos.
    ax2.text(2, 2.62, f"M3 pasa de 1 en {sobre} de {len(dias)} días; M1 en "
             f"{int((razon['m1'] > 1).sum())}", fontsize=6.2, color=E.NEUTRO,
             ha="left", va="center")
    ax2.set_ylim(0, 2.80)
    ax2.set_yticks([0, 0.5, 1.0, 1.5, 2.0])
    ax2.set_yticklabels(["0", "0,5", "1", "1,5", "2"])
    ax2.set_ylabel("Generación\nsobre demanda", fontsize=7.6)
    ax2.tick_params(labelsize=7)

    # ── Banda 3: las horas que la limpieza repuso ────────────────────────
    # En mariposa y con la misma escala hacia arriba y hacia abajo: el
    # sentido es lo que distingue las dos fronteras, y la altura tiene que
    # seguir siendo comparable entre ellas.
    tope = max(float(rep["m1"].max()), float(rep["m3"].max()))
    ax3.axhline(0, color=E.TINTA, linewidth=0.8, zorder=4)
    ax3.bar(x, rep["m1"].reindex(dias).values, width=1.0, color=E.COBERTURAS["m1"],
            linewidth=0, zorder=3)
    ax3.bar(x, -rep["m3"].reindex(dias).values, width=1.0, facecolor="white",
            edgecolor=E.COBERTURAS["m3"], linewidth=0.6, zorder=3)
    ax3.set_ylim(-1.18 * tope, 1.18 * tope)
    ax3.set_yticks([-120, -60, 0, 60])
    ax3.set_yticklabels(["120", "60", "0", "60"])
    ax3.set_ylabel("Horas repuestas", fontsize=7.6)
    ax3.tick_params(labelsize=7)
    for cob, y, va in (("m1", 0.62 * tope, "bottom"), ("m3", -0.62 * tope, "top")):
        ax3.text(2, y, f"{cob.upper()} · {E.fmt_miles(rep[cob].sum())} h",
                 fontsize=6.4, color=E.COBERTURAS[cob], ha="left", va=va,
                 fontweight="bold")
    ax3.set_xticks(marcas)
    ax3.set_xticklabels(rotulos, fontsize=7)
    ax3.set_xlim(-3, len(dias) + 2)
    ax3.set_xlabel("Mes de 2025", fontsize=7.6)

    # ── El rastro: una fila por día, con todo lo dibujado ────────────────
    filas = pd.DataFrame({
        "fecha": [str(d.date()) for d in dias],
        "mediodia_medido_h": medio.values,
        "mediodia_solar_h": solar.values,
        "desfase_min": desfase.values,
        "razon_gd_m1": razon["m1"].values,
        "razon_gd_m3": razon["m3"].values,
        "razon_movil_m1": movil["m1"].values,
        "razon_movil_m3": movil["m3"].values,
        "horas_repuestas_m1": rep["m1"].reindex(dias).values,
        "horas_repuestas_m3": rep["m3"].reindex(dias).values,
    })

    fig.tight_layout(rect=(0, 0, 0.905, 0.995), h_pad=1.4)
    return E.guardar(
        fig, "f3_07_matrices", datos=filas,
        procedencia=[
            "reformateo/documento/datos_cache/preproceso_m1.npz",
            "reformateo/documento/datos_cache/preproceso_m3.npz",
            "mediodía solar: longitud de Pasto -77,28 grados, meridiano del "
            "huso -75, ecuación del tiempo de Spencer (1971); no entra "
            "ningún dato medido en esa curva",
            "la generación es byte a byte la misma en las dos fronteras; el "
            "generador lo comprueba con un aserto antes de dibujar",
        ])


# ─────────────────────────────────────────────────────────────────────────────
def f38_perfiles_instituciones():
    """
    F3.8 — Cinco ritmos distintos, y qué queda de ellos en la otra frontera.

    Cada perfil va dividido por su propia media diaria. La subsección
    afirma algo sobre la FORMA del día, y la versión anterior daba a cada
    panel su propia escala vertical y lo advertía al pie: «lo comparable
    entre ellos es la forma del perfil, no su altura». Es decir, pedía
    comparar formas y las dibujaba a escalas distintas, que es lo que
    impide compararlas. Normalizadas, los cinco caen sobre un mismo eje y
    la diferencia de forma pasa a ser geometría. El nivel absoluto no se
    pierde: se declara en la columna del sexto panel.

    El sexto panel lleva la evidencia de la afirmación del título, que es
    a qué distancia media queda la forma de cada institución de las otras
    cuatro. El Hospital es el caso aparte y no por poco: su perfil apenas
    se mueve, su fin de semana vale el 97 % del día laboral, y su
    distancia media a las demás es la mayor del conjunto.

    Cada panel lleva además las dos curvas de la misma institución en las
    dos fronteras, de modo que se vea qué queda de la forma al cambiar de
    circuito. La cifra que acompaña a cada título es la correlación entre
    esas dos curvas, que mide si las subidas y bajadas caen en las mismas
    horas; no mide la amplitud, y por eso Udenar puede conservar la forma
    con un recorrido casi doble.
    """
    perfil, nivel, gdr = {}, {}, {}
    for cob in ("m1", "m3"):
        series, _ = D.preproceso(cob)
        for inst in D.AGENTES:
            d = series[f"{inst}__D_limpia"]
            g = series[f"{inst}__G_limpia"]
            media = float(d.mean())
            assert media > 0, (cob, inst)
            perfil[(cob, inst)] = (d.groupby(d.index.hour).mean() / media).values
            nivel[(cob, inst)] = media
            gdr[(cob, inst)] = 100 * float(g.sum()) / float(d.sum())

    # La evidencia del título: cuánto se separa la forma de cada una de las
    # otras cuatro, medido como diferencia media entre perfiles ya
    # normalizados. La matriz entera no se dibuja porque son diez números
    # y lo que la afirmación necesita es el resumen por institución.
    pares = {}
    for a in D.AGENTES:
        for b in D.AGENTES:
            if a < b:
                pares[(a, b)] = float(np.abs(perfil[("m1", a)]
                                             - perfil[("m1", b)]).mean())
    lejania = {a: float(np.mean([v for k, v in pares.items() if a in k]))
               for a in D.AGENTES}
    forma = {a: float(np.corrcoef(perfil[("m1", a)], perfil[("m3", a)])[0, 1])
             for a in D.AGENTES}

    fig, ejes = plt.subplots(2, 3, figsize=(E.ANCHO_COMPLETO, 4.3),
                             sharex=False)
    hora = np.arange(24)
    tope = max(v.max() for v in perfil.values())
    filas = []

    for ax, inst in zip(ejes.ravel()[:5], D.AGENTES):
        ax.axhline(1.0, color=E.NEUTRO, linewidth=0.7, linestyle=(0, (4, 2)),
                   zorder=2)
        for cob, ancho, trazo, marca in (("m1", 1.7, "-", "o"),
                                         ("m3", 1.3, (0, (3.5, 2)), "^")):
            ax.plot(hora, perfil[(cob, inst)], color=E.COBERTURAS[cob],
                    linewidth=ancho, linestyle=trazo, marker=marca,
                    markersize=2.6, markevery=(0 if cob == "m1" else 2, 4),
                    zorder=4 if cob == "m1" else 3)
        # La marca de la Universidad Mariana remite a la declaración de
        # honestidad: bajo la frontera secundaria su medidor no recibe la
        # reconstrucción que sí recibe bajo la principal, de modo que su
        # curva hunde el mediodía. Se dibuja tal cual y se señala.
        estrella = "*" if inst == "Mariana" else ""
        ax.set_title(f"{E.etiqueta_institucion(inst)}{estrella}  ·  forma "
                     f"{E.fmt_miles(forma[inst], 2)}", fontsize=8.0,
                     color=E.color_institucion(inst), pad=5)
        ax.set_ylim(0, tope * 1.10)
        ax.set_xlim(-0.5, 23.5)
        ax.set_xticks(range(0, 24, 6))
        ax.tick_params(labelsize=6.8)
        ax.set_yticks([0, 1, 2])
        for h in range(24):
            filas.append({"bloque": "perfil", "institucion": inst, "hora": h,
                          "m1_sobre_su_media": perfil[("m1", inst)][h],
                          "m3_sobre_su_media": perfil[("m3", inst)][h]})
    for k in (0, 3):
        ejes.ravel()[k].set_ylabel("Demanda sobre\nsu media diaria",
                                   fontsize=7.4)
    for k in (3, 4):
        ejes.ravel()[k].set_xlabel("Hora del día", fontsize=7.4)
    ejes.ravel()[2].set_xlabel("Hora del día", fontsize=7.4)

    # ── El sexto panel: la evidencia y el nivel ─────────────────────────
    ax = ejes.ravel()[5]
    E.eje_instituciones(ax, eje="y")
    ax.grid(visible=False, axis="y")
    ax.grid(visible=True, axis="x")
    X_ROTULO = 0.62
    for k, inst in enumerate(D.AGENTES):
        ax.plot([0, lejania[inst]], [k, k], color=E.color_institucion(inst),
                linewidth=1.2, solid_capstyle="butt", zorder=3)
        ax.plot([lejania[inst]], [k], marker="o", markersize=5.0,
                color=E.color_institucion(inst), markeredgecolor="white",
                markeredgewidth=0.7, zorder=4)
        ax.text(X_ROTULO, k, f"{E.fmt_miles(nivel[('m1', inst)], 1)} · "
                f"{E.fmt_miles(nivel[('m3', inst)], 1)}", fontsize=6.2,
                color=E.NEUTRO, ha="right", va="center")
        filas.append({"bloque": "resumen", "institucion": inst,
                      "distancia_media_a_las_otras": lejania[inst],
                      "forma_m1_m3": forma[inst],
                      "media_diaria_m1_kW": nivel[("m1", inst)],
                      "media_diaria_m3_kW": nivel[("m3", inst)],
                      "gd_m1_pct": gdr[("m1", inst)],
                      "gd_m3_pct": gdr[("m3", inst)]})
    for (a, b), v in pares.items():
        filas.append({"bloque": "par", "institucion": f"{a} y {b}",
                      "distancia_media_a_las_otras": v})
    ax.set_xlim(0, 0.66)
    ax.set_xticks([0, 0.2, 0.4])
    ax.set_xticklabels(["0", "0,2", "0,4"])
    ax.set_ylim(len(D.AGENTES) - 0.5, -0.85)
    ax.tick_params(labelsize=6.8)
    ax.set_xlabel("Distancia media de su forma\na las otras cuatro",
                  fontsize=7.4)
    ax.text(X_ROTULO, -0.70, "media diaria M1 · M3 (kW)", fontsize=6.2,
            color=E.NEUTRO, ha="right", va="center")

    fig.tight_layout(rect=(0, 0.065, 1, 0.995), h_pad=1.8, w_pad=1.2)
    fig.legend(handles=[
        Line2D([], [], color=E.COBERTURAS["m1"], linewidth=1.7, marker="o",
               markersize=2.8, label=E.COBERTURA_NOMBRE["m1"]),
        Line2D([], [], color=E.COBERTURAS["m3"], linewidth=1.3, marker="^",
               markersize=2.8, linestyle=(0, (3.5, 2)),
               label=E.COBERTURA_NOMBRE["m3"])],
        loc="upper center",
        bbox_to_anchor=(0.5, _bajo_de_los_ejes(fig, ejes.ravel(), 0.008)),
        ncol=2, fontsize=6.9, frameon=False, handlelength=2.2,
        columnspacing=2.0)

    return E.guardar(
        fig, "f3_08_perfiles_instituciones", datos=pd.DataFrame(filas),
        procedencia=[
            "reformateo/documento/datos_cache/preproceso_m1.npz",
            "reformateo/documento/datos_cache/preproceso_m3.npz",
            "cada perfil va dividido por su propia media diaria; la "
            "distancia entre formas es la diferencia media entre dos "
            "perfiles ya normalizados",
        ])


# ─────────────────────────────────────────────────────────────────────────────
def f39_ritmos():
    """
    F3.9 y F3.10 — El ritmo semanal y el anual, en las dos fronteras.

    A la izquierda, día hábil frente a fin de semana, una fila por
    frontera y en kilovatios: la demanda cae y la generación no, de modo
    que el excedente disponible para intercambio es mayor precisamente
    cuando hay menos gente en los edificios. Las dos filas hacen falta
    porque la asimetría no vale lo mismo en las dos: en el circuito
    principal la generación no alcanza a la demanda en ninguna hora ni
    siquiera el fin de semana, y en el secundario la supera en las horas
    de sol y la supera mucho más el fin de semana.

    El eje va en kilovatios y no normalizado a propósito: lo que el panel
    tiene que dejar ver es si la generación cruza a la demanda, y eso solo
    se ve con las dos magnitudes en la misma escala. Por eso cada frontera
    lleva su fila, con su propia escala: sus demandas medias se separan
    por un factor de casi cinco.

    A la derecha, el recorrido mensual. Aporta sobre la banda diaria de la
    figura de cierre porque aquella lleva la razón entre generación y
    demanda, y una razón no dice cuál de los dos términos se movió: aquí
    se ve que la demanda recorre un factor de 1,76 en el circuito
    principal y de 1,58 en el secundario mientras la generación se queda
    en 1,11, y que en el secundario la demanda mensual y la generación van
    casi montadas, que es la forma visible de una razón próxima a uno.
    """
    dem, gen = {}, None
    for cob in ("m1", "m3"):
        series, _ = D.preproceso(cob)
        dem[cob] = sum(series[f"{i}__D_limpia"] for i in D.AGENTES)
        g = sum(series[f"{i}__G_limpia"] for i in D.AGENTES)
        if gen is None:
            gen = g
        else:
            assert np.abs(gen.values - g.values).max() == 0, (
                "la generación difiere entre M1 y M3: el panel mensual "
                "dibuja una sola curva y dejaría de ser cierto")

    fig = plt.figure(figsize=(E.ANCHO_COMPLETO, 4.4))
    malla = fig.add_gridspec(2, 2, width_ratios=[1.0, 0.92], wspace=0.30,
                             hspace=0.55)
    ejes = [fig.add_subplot(malla[0, 0]), fig.add_subplot(malla[1, 0])]
    ax_mes = fig.add_subplot(malla[:, 1])
    filas = []

    # ── El ritmo semanal, una fila por frontera ──────────────────────────
    for ax, cob in zip(ejes, ("m1", "m3")):
        d, g = dem[cob], gen
        hab, fin = d.index.weekday < 5, d.index.weekday >= 5
        for nombre, mascara, trazo in (("día hábil", hab, "-"),
                                       ("fin de semana", fin, (0, (3.5, 2)))):
            pd_ = d[mascara].groupby(d[mascara].index.hour).mean()
            pg_ = g[mascara].groupby(g[mascara].index.hour).mean()
            ax.plot(pd_.index, pd_.values, linestyle=trazo, color=E.TINTA,
                    linewidth=1.6, zorder=4)
            ax.plot(pg_.index, pg_.values, linestyle=trazo,
                    color=E.GENERACION, linewidth=1.6, zorder=3)
            for h in pd_.index:
                filas.append({"bloque": "semana", "frontera": cob.upper(),
                              "corte": nombre, "hora": int(h),
                              "demanda_kW": float(pd_[h]),
                              "generacion_kW": float(pg_[h])})
        caida = 100 * (1 - d[fin].mean() / d[hab].mean())
        var_g = 100 * (g[fin].mean() / g[hab].mean() - 1)
        # Las horas de sol son donde la comparación entre las dos
        # magnitudes decide algo: fuera de ellas la generación es cero y
        # la resta no informa.
        sol = (d.index.hour >= 8) & (d.index.hour <= 16)
        exc = {"habil": float((g - d)[sol & hab].mean()),
               "finde": float((g - d)[sol & fin].mean())}
        lo, hi = ax.get_ylim()
        ax.set_ylim(min(0, lo), hi + 0.20 * (hi - lo))
        # Una sola cifra dentro del panel, junto a la geometría que nombra:
        # la distancia entre las dos curvas de demanda.
        ax.text(0.985, 0.94, f"la demanda cae {E.fmt_miles(caida, 1)} %",
                transform=ax.transAxes, ha="right", va="top", fontsize=6.6,
                color=E.TINTA)
        ax.set_title(E.titulo_cobertura(cob), fontsize=8.0,
                     color=E.COBERTURAS[cob], pad=5)
        ax.set_ylabel("Potencia media (kW)", fontsize=7.4)
        ax.set_xticks(range(0, 24, 6))
        ax.tick_params(labelsize=7)
        filas.append({"bloque": "semana", "frontera": cob.upper(),
                      "corte": "resumen", "caida_demanda_pct": caida,
                      "cambio_generacion_pct": var_g,
                      "gen_menos_dem_habil_kW": exc["habil"],
                      "gen_menos_dem_finde_kW": exc["finde"]})
    ejes[1].set_xlabel("Hora del día", fontsize=7.4)

    # ── El recorrido mensual ─────────────────────────────────────────────
    med_g = gen.groupby(gen.index.to_period("M")).mean()
    x = np.arange(len(med_g))
    rotulos_mes = []
    for cob, marca, trazo in (("m1", "o", "-"), ("m3", "^", (0, (3.5, 2)))):
        med = dem[cob].groupby(dem[cob].index.to_period("M")).mean()
        ax_mes.plot(x, med.values, marker=marca, markersize=3.2, linestyle=trazo,
                    color=E.COBERTURAS[cob], linewidth=1.5, zorder=4)
        # El rótulo va en dos líneas: en una sola, las tres etiquetas del
        # margen se comían la cuarta parte del panel y los nueve meses del
        # eje se imprimían pegados.
        rotulos_mes.append((float(med.values[-1]),
                            f"{cob.upper()}\n×{E.fmt_miles(med.max() / med.min(), 2)}",
                            E.COBERTURAS[cob]))
        for p, v in zip(med.index, med.values):
            filas.append({"bloque": "mes", "frontera": cob.upper(),
                          "corte": str(p), "demanda_kW": float(v)})
    ax_mes.plot(x, med_g.values, marker="s", markersize=3.2,
                color=E.GENERACION, linewidth=1.5, zorder=3)
    rotulos_mes.append((float(med_g.values[-1]),
                        f"generación\n×{E.fmt_miles(med_g.max() / med_g.min(), 2)}",
                        E.GENERACION))
    for p, v in zip(med_g.index, med_g.values):
        filas.append({"bloque": "mes", "frontera": "M1 = M3", "corte": str(p),
                      "generacion_kW": float(v)})
    ax_mes.set_xticks(x)
    ax_mes.set_xticklabels([_mes_es(p) for p in med_g.index], fontsize=6.2)
    ax_mes.set_xlim(-0.5, len(x) + 0.9)
    # Desde cero: con el eje arrancando en el mínimo, una serie que va de
    # 8,4 a 13,2 kW parece desplomarse, y la comparación entre las dos
    # magnitudes, que es de lo que trata el panel, queda deformada.
    ax_mes.set_ylim(0, max(float(med_g.max()),
                           max(float(dem[c].groupby(
                               dem[c].index.to_period("M")).mean().max())
                               for c in ("m1", "m3"))) * 1.14)
    ax_mes.set_xlabel("Mes de 2025", fontsize=7.4)
    ax_mes.set_ylabel("Potencia media (kW)", fontsize=7.4)
    ax_mes.set_title("Recorrido a lo largo del horizonte", fontsize=8.0, pad=5)
    ax_mes.tick_params(labelsize=7)
    # Los tres rótulos del margen se reparten: la demanda del circuito
    # secundario y la generación acaban el horizonte a 1,1 kW una de otra,
    # que sobre este eje son tres puntos tipográficos para dos rótulos de
    # dos líneas.
    alturas = _separar_etiquetas([r[0] for r in rotulos_mes],
                                 0.075 * ax_mes.get_ylim()[1],
                                 tope=0.94 * ax_mes.get_ylim()[1])
    for y, (_, texto, color) in zip(alturas, rotulos_mes):
        ax_mes.text(x[-1] + 0.22, y, texto, fontsize=6.4, color=color,
                    ha="left", va="center", linespacing=1.25)

    fig.tight_layout(rect=(0, 0.075, 1, 0.995))
    fig.legend(handles=[
        Line2D([], [], color=E.TINTA, linewidth=1.6, label="Demanda · día hábil"),
        Line2D([], [], color=E.TINTA, linewidth=1.6, linestyle=(0, (3.5, 2)),
               label="Demanda · fin de semana"),
        Line2D([], [], color=E.GENERACION, linewidth=1.6,
               label="Generación · día hábil"),
        Line2D([], [], color=E.GENERACION, linewidth=1.6, linestyle=(0, (3.5, 2)),
               label="Generación · fin de semana")],
        loc="upper center",
        bbox_to_anchor=(0.5, _bajo_de_los_ejes(fig, ejes + [ax_mes], 0.008)),
        ncol=4, fontsize=6.6, frameon=False, handlelength=2.0,
        columnspacing=1.4)

    return E.guardar(
        fig, "f3_09_ritmos", datos=pd.DataFrame(filas),
        procedencia=[
            "reformateo/documento/datos_cache/preproceso_m1.npz",
            "reformateo/documento/datos_cache/preproceso_m3.npz",
            "la generación es byte a byte la misma en las dos fronteras; el "
            "generador lo comprueba con un aserto antes de dibujar",
        ])


if __name__ == "__main__":
    D.verificar_canon()
    print("\nCapítulo 3 — la domesticación del dato")
    verificar_inversores()
    f31_archivo_a_serie()
    f31d_duplicados()
    f31b_energia_hora()
    f31c_hora_incompleta()
    f32_demanda_negativa()
    f32b_profundidad()
    f33_reconstruccion("m1", "Udenar")
    f33b_reconstruccion_mosaico()
    f37_matrices()
    f38_perfiles_instituciones()
    f39_ritmos()
    # CAL-45: la anatomia del umbral y la figura del caso perdieron su
    # objeto al retirarse el criterio distribucional. Las sustituyen las dos
    # del guardia, que viven en su propio generador porque son la prueba de
    # esa decision y conviene que se puedan rehacer solas.
    import gen_cal45
    gen_cal45.f310_umbral_nativo()
    gen_cal45.f311_fallo_tension()
    f36_escalera_huecos()
    print("\nlisto.")
