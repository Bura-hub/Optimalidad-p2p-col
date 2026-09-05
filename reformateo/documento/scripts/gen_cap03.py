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
    # El eje se acota a las horas que tienen dato: sobre 0 a 23 la mitad
    # del panel queda vacía y las barras se estrechan sin necesidad.
    con_dato = np.flatnonzero(base > 0)
    h0, h1 = int(con_dato[0]) - 1, int(con_dato[-1]) + 1
    ax2.annotate(f"{E.fmt_miles(base[pico])} horas",
                 xy=(pico, base[pico]),
                 xytext=(pico + (h1 - pico) * 0.42, base[pico] * 1.13),
                 fontsize=7.2, color="#555555", ha="left", va="center",
                 arrowprops=dict(arrowstyle="-", color="#999999", lw=0.8,
                                 shrinkA=1, shrinkB=3), zorder=6)
    # Las instituciones sin negativos no se dibujan: la leyenda de tres
    # ya lo dice, y el rotulo dentro del panel chocaba con las barras.
    # Quienes son lo dice el cuerpo del texto.
    ax2.set_ylim(0, base.max() * 1.42)
    ax2.set_xlim(h0 - 0.6, h1 + 0.6)
    ax2.set_xlabel("Hora del día")
    ax2.set_ylabel("Horas con lectura negativa")
    ax2.set_title("Cuándo ocurre", pad=8)
    ax2.set_xticks(range(h0 + (h0 % 2), h1 + 1, 2))
    ax2.text(h1 + 0.4, base.max() * 1.36,
             f"{E.fmt_miles(base.sum())} horas en total",
             ha="right", va="center", fontsize=7.2, color="#555555")
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
def f32b_profundidad(cobertura: str = "m1"):
    """
    F3.3 — Hasta dónde baja la lectura de cada medidor.

    Sustituye a la curva de duración que ocupaba este sitio. Aquella
    tenía en el eje horizontal un percentil de horas ordenadas, es decir
    un orden y no una magnitud, y el lector llegaba a ella desde la
    figura de la demanda negativa, cuyo eje horizontal es la hora del
    día. Medido sobre aquel render: el 80 % de las lecturas de las cinco
    instituciones cabía en 15 puntos tipográficos del panel izquierdo,
    y en el derecho los cruces de Mariana y de la UCC quedaban a 9,6
    puntos con un marcador de 4,5, de modo que la gradación entre los
    dos casos intermedios no se podía leer.

    Qué añade esta figura sobre la tabla de los tipos. La tabla publica
    el conteo de horas bajo cero y el mínimo, que es un extremo. No dice
    a qué profundidad ocurre la inversión de ordinario, y la diferencia
    importa: en Udenar la mitad central de las lecturas negativas cae
    entre −15,1 y −3,9 kW, con mediana de −8,7, mientras que el mínimo
    publicado, −33,6 kW, es casi cuatro veces esa mediana.

    La forma. Una fila por institución, en el orden fijo del documento,
    y una sola magnitud en el eje horizontal, los kilovatios, que es la
    misma del eje vertical de las dos figuras vecinas. Cada fila lleva la
    lectura mediana del medidor, el recorrido desde esa mediana hasta su
    lectura más baja, y la mitad central de sus lecturas negativas cuando
    las tiene. La comparación entre lo que el medidor marca de ordinario
    y hasta dónde desciende es la gradación misma, y en el HUDN y en
    CESMAG ese recorrido no llega a tocar el cero.

    La identidad de cada fila la lleva su rótulo y su posición, no el
    color, de modo que la figura sobrevive impresa en escala de grises.

    Solo M1. En M3 los cinco medidores son brutos y no hay gradación.
    """
    series, _ = D.preproceso(cobertura)
    resumen = D.conteo_negativas(cobertura).set_index("institucion")

    # El contrato es la tabla impresa del capítulo, no solo el caché. Si
    # el caché cambia de versión, la figura se detiene antes de dibujar
    # otra cosa con los mismos rótulos.
    HORAS_TABLA = {"Udenar": 1517, "Mariana": 213, "UCC": 94,
                   "HUDN": 0, "Cesmag": 0}
    MIN_TABLA = {"Udenar": -33.567, "Mariana": -2.411, "UCC": -5.909}
    # Las tres medianas y los dos mínimos que no cruzan son las cifras
    # nuevas que el pie publica, y por eso entran también en la compuerta.
    NEGMED_PIE = {"Udenar": -8.678, "Mariana": -0.590, "UCC": -1.938}
    CAJA_PIE = {"Udenar": (-15.051, -3.902)}
    FRAC_TABLA = {"Udenar": 73.8, "Mariana": 21.3, "UCC": 11.7,
                  "HUDN": 0.0, "Cesmag": 0.0}
    TIPO_TABLA = {"Udenar": "net", "Mariana": "net_partial",
                  "UCC": "net_partial", "HUDN": "gross", "Cesmag": "gross"}

    med = {}      # lectura mediana de cada medidor
    minimo = {}   # su lectura más baja
    caja = {}     # mitad central de sus lecturas negativas
    negmed = {}   # mediana de sus lecturas negativas
    for inst in E.ORDEN_INSTITUCIONES:
        v = series[f"{inst}__D_raw"].dropna().values
        assert not np.isnan(v).any(), inst
        assert 5900 <= len(v) <= 6144, (inst, len(v))

        n_neg = int((v < 0).sum())
        assert n_neg == HORAS_TABLA[inst], (inst, n_neg, HORAS_TABLA[inst])
        assert n_neg == int(resumen.loc[inst, "horas_negativas"]), inst

        med[inst] = float(np.median(v))
        minimo[inst] = float(v.min())
        if inst in MIN_TABLA:
            assert abs(minimo[inst] - MIN_TABLA[inst]) < 1e-3, (inst, minimo[inst])
            neg = v[v < 0]
            caja[inst] = (float(np.percentile(neg, 25)),
                          float(np.percentile(neg, 75)))
            negmed[inst] = float(np.median(neg))
        else:
            assert minimo[inst] > 0, (inst, minimo[inst])

        g = float(series[f"{inst}__G_recon"].sum())
        d = float(series[f"{inst}__D_recon"].sum())
        assert abs(round(100 * g / d, 1) - FRAC_TABLA[inst]) < 0.05, inst

    # Las afirmaciones que la figura dibuja y el pie enuncia.
    assert abs(minimo["Cesmag"] - 0.195) < 5e-4, minimo["Cesmag"]
    assert 6 < minimo["HUDN"] < 7, minimo["HUDN"]
    for i, v in NEGMED_PIE.items():
        assert abs(negmed[i] - v) < 1e-3, (i, negmed[i], v)
    for i, (lo, hi) in CAJA_PIE.items():
        assert abs(caja[i][0] - lo) < 1e-3 and abs(caja[i][1] - hi) < 1e-3,             (i, caja[i])
    # Y la relación que el pie enuncia: el mínimo casi cuadruplica la
    # inversión ordinaria de Udenar.
    assert 3.7 < minimo["Udenar"] / negmed["Udenar"] < 4.0,         minimo["Udenar"] / negmed["Udenar"]
    assert minimo["Udenar"] < caja["Udenar"][0] < negmed["Udenar"] \
        < caja["Udenar"][1] < 0, caja["Udenar"]
    # La proporción de horas de Udenar, tal como el texto la publica.
    su = series["Udenar__D_raw"]
    assert round(100 * int((su < 0).sum()) / len(su), 1) == 24.7
    assert round(100 * int((su < 0).sum()) / int(su.notna().sum()), 1) == 25.1
    # Y la nota al pie: al mediodía la inversión es lo ordinario en Udenar.
    gu, du = series["Udenar__G_recon"], series["Udenar__D_recon"]
    mediodia = (gu > du)[gu.index.hour == 12]
    assert mediodia.mean() > 0.5, float(mediodia.mean())

    # La otra frontera: allí solo Mariana baja de cero, las mismas horas.
    otras, _ = D.preproceso("m3" if cobertura == "m1" else "m1")
    neg_m3 = {i: int((otras[f"{i}__D_raw"].dropna() < 0).sum())
              for i in E.ORDEN_INSTITUCIONES}
    assert neg_m3 == {"Udenar": 0, "Mariana": 213, "UCC": 0,
                      "HUDN": 0, "Cesmag": 0}, neg_m3

    # ── Lienzo ───────────────────────────────────────────────────────────
    fig, ax = E.figura(alto=2.7)
    E.eje_instituciones(ax, eje="y")
    ax.grid(visible=False, axis="y")
    ax.grid(visible=True, axis="x")

    XLO, XHI = -37.5, 13.5
    ax.set_xlim(XLO, XHI)
    ax.axvspan(XLO, 0, color=E.ANTES, alpha=0.07, zorder=0)
    ax.axvline(0, color="#333333", linewidth=1.0, zorder=2)

    # Las marcas se registran en coordenadas de dato, no como artistas.
    # El extremo en pantalla de una coleccion de lineas no es fiable y
    # devolvia una caja que no correspondia a la marca, de modo que la
    # prueba de oclusion habria fallado sobre un objeto equivocado.
    marcas = []   # (nombre, x0, x1, y0, y1) en unidades de dato
    for k, inst in enumerate(E.ORDEN_INSTITUCIONES):
        c = E.color_institucion(inst)
        # El recorrido de la lectura mediana a la más baja.
        ax.plot([minimo[inst], med[inst]], [k, k], color=c,
                linewidth=1.4, solid_capstyle="butt", zorder=4)
        marcas.append((f"recorrido {inst}", minimo[inst], med[inst],
                       k - 0.02, k + 0.02))
        # La mitad central de las lecturas negativas, donde las hay.
        if inst in caja:
            lo, hi = caja[inst]
            ax.add_patch(Rectangle((lo, k - 0.17), hi - lo, 0.34,
                                   facecolor=c, edgecolor="white",
                                   linewidth=0.5, zorder=5))
            marcas.append((f"caja {inst}", lo, hi, k - 0.17, k + 0.17))
        # La lectura más baja.
        ax.plot([minimo[inst]], [k], marker="o", markersize=5.2,
                color=c, markeredgecolor="white", markeredgewidth=0.7,
                zorder=6)
        marcas.append((f"mínimo {inst}", minimo[inst], minimo[inst],
                       k, k))
        # La lectura mediana, en tinta y no en color: es la referencia
        # contra la que se mide el descenso, y es la misma en las cinco.
        ax.vlines(med[inst], k - 0.21, k + 0.21, color=E.TINTA,
                  linewidth=1.8, zorder=7)
        marcas.append((f"mediana {inst}", med[inst], med[inst],
                       k - 0.21, k + 0.21))

    # Segunda columna de rótulos, fuera del área de dato: el tipo que la
    # subsección asigna a cada medidor. Puesta al lado de la geometría
    # deja ver que el neto parcial se parece más al bruto que al neto.
    axd = ax.twinx()
    axd.set_ylim(ax.get_ylim())
    axd.grid(visible=False)
    axd.spines["right"].set_visible(False)
    axd.set_yticks(range(len(E.ORDEN_INSTITUCIONES)))
    axd.set_yticklabels([E.TIPO_MEDIDOR_ES[TIPO_TABLA[i]]
                         for i in E.ORDEN_INSTITUCIONES], fontsize=7.6,
                        color=E.NEUTRO)
    axd.tick_params(axis="y", length=0, pad=12)

    # Un solo rótulo, y sin cifra. La mediana de las lecturas negativas,
    # que es lo que la tabla no da, va al pie y al CSV hermano: leer
    # valores exactos sobre el papel no es tarea de la figura. Y que el
    # mínimo de CESMAG roce el cero sin cruzarlo lo dice su marca, puesta
    # sobre la línea del cero; el rótulo que lo decía quedaba en el
    # mismo renglón que la columna de tipos y se leía pegado a ella.
    t3 = ax.text(XLO + 1.2, 3.72, "flujo invertido, es decir,"
                 + chr(10) + "del circuito hacia la red",
                 ha="left", va="center", fontsize=7.2, style="italic",
                 color=E.ANTES, linespacing=1.35, zorder=9)

    ax.set_xlabel("Lectura del medidor (kW)")
    ax.set_title("Hasta dónde baja la lectura de cada medidor", pad=8)
    ax.set_xticks([-30, -20, -10, 0, 10])

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
    fig.legend(handles=leyenda, loc="lower center", ncol=4, fontsize=7.6,
               frameon=False, handlelength=1.5, handletextpad=0.5,
               columnspacing=1.4, bbox_to_anchor=(0.5, -0.012))

    _rotulo_cobertura(fig, cobertura)
    fig.tight_layout(rect=(0, 0.08, 1, 0.945))

    # ── Ningún rótulo puede tapar dato ───────────────────────────────────
    # Las marcas se llevan a pantalla desde sus coordenadas de dato y se
    # ensanchan 2,6 puntos, que es el radio del marcador del mínimo más
    # la mitad del grosor de la línea de la mediana.
    fig.canvas.draw()
    HOLGURA = 2.6 * fig.dpi / 72.0
    cajas = []
    for nombre, x0, x1, y0, y1 in marcas:
        (px0, py0), (px1, py1) = ax.transData.transform([(x0, y0), (x1, y1)])
        cajas.append((nombre, Bbox([[min(px0, px1) - HOLGURA,
                                     min(py0, py1) - HOLGURA],
                                    [max(px0, px1) + HOLGURA,
                                     max(py0, py1) + HOLGURA]])))
    bt = t3.get_window_extent()
    for nombre, bm in cajas:
        assert not bt.overlaps(bm), (t3.get_text(), nombre)
    # Y ningún rótulo se sale de la caja del panel.
    bax = ax.get_window_extent()
    assert bax.contains(*bt.min) and bax.contains(*bt.max), t3.get_text()
    # Ni la leyenda se sale del ancho de la figura.
    bl = fig.legends[0].get_window_extent()
    bf = fig.get_window_extent()
    assert bl.x0 >= bf.x0 and bl.x1 <= bf.x1, (bl.x0, bl.x1, bf.x1)

    filas = [{"institucion": inst,
              "tipo": E.TIPO_MEDIDOR_ES[TIPO_TABLA[inst]],
              "horas_con_dato": int(series[f"{inst}__D_raw"].notna().sum()),
              "horas_negativas": HORAS_TABLA[inst],
              "mediana_kW": round(med[inst], 6),
              "minimo_kW": round(minimo[inst], 6),
              "negativas_p25_kW": round(caja[inst][0], 6) if inst in caja else "",
              "negativas_mediana_kW": round(negmed[inst], 6) if inst in negmed else "",
              "negativas_p75_kW": round(caja[inst][1], 6) if inst in caja else ""}
             for inst in E.ORDEN_INSTITUCIONES]

    print("  [f3.3] mediana de las lecturas negativas: " + ", ".join(
        f"{i} {negmed[i]:.2f} kW" for i in negmed))

    return E.guardar(
        fig, f"f3_02b_profundidad_{cobertura}", datos=pd.DataFrame(filas),
        procedencia=[D.rel(D.CACHE / f"preproceso_{cobertura}.npz"),
                     D.rel(D.CACHE / f"preproceso_{cobertura}_resumen.csv")])


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
    q25, q75 = s.quantile(0.25), s.quantile(0.75)
    p995 = s.quantile(0.995)
    iqr = q75 - q25
    cand_tukey = q75 + 5 * iqr if iqr > 0 else np.inf
    cand_piso = p995 * 1.2 if np.isfinite(p995) else np.inf
    umbral = max(cand_tukey, cand_piso)

    m_out = pd.Series(False, index=s.index)
    if np.isfinite(umbral) and umbral > 0:
        m_out = s > umbral
    m_out = m_out.fillna(False)

    s1 = s.copy()
    s1[m_out] = np.nan
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
                "manda": ("cerca de Tukey" if r["tukey"] >= r["piso"]
                          else "piso del percentil"),
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
def f35_umbral_atipicos(cobertura: str = "m1"):
    """
    F3.5 — El umbral: que retira y por que esta donde esta.

    Panel izquierdo, el caso: la hora que el criterio retira y el valor con
    que quedo, sobre una ventana de tres dias, que es la escala a la que un
    pico se distingue de la operacion normal. Sobre las 6.144 horas del
    horizonte esa hora es un marcador sobre una maraña.

    Paneles derechos, la regla: una fila por serie con su mitad central, su
    cola hasta el maximo observado y los dos candidatos del umbral, en
    multiplos del percentil 99,5 de la propia serie. La normalizacion no es
    cosmetica: los diez umbrales de la frontera principal van de 10,2 a
    154,8 kW, mas de un orden de magnitud, de modo que en kilovatios las
    filas pequeñas no podrian dibujar ninguna diferencia. Normalizados, el
    piso es una sola vertical en 1,2 comun a las diez filas, y basta mirar
    a que lado de esa vertical cae la cerca de Tukey para saber cual de los
    dos manda.
    """
    censo, detalle, series = _censo_limpieza(cobertura)

    # ── el caso del panel izquierdo ──────────────────────────────────────
    # Regla: entre todas las horas retiradas, las aisladas (ni la anterior
    # ni la posterior lo estan) y de esas la que mas sobresale del umbral en
    # terminos relativos. La aislada es imprescindible: en un tramo de horas
    # seguidas no se ve que la interpolacion cierre el hueco, y el tramo del
    # 24 de abril, tres horas de la rampa de mañana, sobresale un 1,3 %, de
    # modo que enseñaria un criterio que apenas discrimina.
    mejor = None
    for inst in E.ORDEN_INSTITUCIONES:
        for magnitud in ("demanda", "generación"):
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
                             "umbral": r["umbral"], "sale": float(r["limpia"][t]),
                             "entrada": entrada, "limpia": r["limpia"]}
    assert mejor is not None, (f"{cobertura}: ninguna hora retirada por el "
                               "umbral queda aislada; el panel del caso se "
                               "queda sin objeto")

    t = mejor["hora"]
    ventana = slice(t - pd.Timedelta("36h"), t + pd.Timedelta("36h"))
    obs = mejor["entrada"][ventana]
    fin = mejor["limpia"][ventana]
    ancla_previa = float(mejor["entrada"][t - pd.Timedelta("1h")])
    ancla_post = float(mejor["entrada"][t + pd.Timedelta("1h")])

    fig = plt.figure(figsize=(E.ANCHO_COMPLETO, 3.9))
    malla = fig.add_gridspec(2, 2, width_ratios=(1.0, 1.18),
                             height_ratios=(1.0, 1.0), wspace=0.30, hspace=0.24)
    ax_caso = fig.add_subplot(malla[:, 0])
    ax_dem = fig.add_subplot(malla[0, 1])
    ax_gen = fig.add_subplot(malla[1, 1], sharex=ax_dem)

    # ── panel del caso ───────────────────────────────────────────────────
    ax_caso.plot(fin.index, fin.values, color=E.TINTA, linewidth=1.0,
                 label="Serie ya limpia")
    ax_caso.axhline(mejor["umbral"], color=E.ALERTA, linewidth=1.1,
                    linestyle="--",
                    label=f"Umbral: {E.fmt_miles(mejor['umbral'], 1)} kW")
    lo = float(min(fin.min(), obs.min()))
    hi = float(max(obs.max(), mejor["entra"]))
    margen = 0.16 * (hi - lo)
    ax_caso.axhspan(mejor["umbral"], hi + 3 * margen, color=E.ALERTA,
                    alpha=0.07, linewidth=0, zorder=0)
    ax_caso.plot([t], [mejor["entra"]], marker="o", markersize=7,
                 markerfacecolor="white", markeredgecolor=E.ANTES,
                 markeredgewidth=1.6, linestyle="none",
                 label="Lectura retirada", zorder=6)
    ax_caso.plot([t], [mejor["sale"]], marker="s", markersize=6,
                 color=E.DESPUES, linestyle="none",
                 label="Valor con que quedó", zorder=6)
    ax_caso.annotate("", xy=(t, mejor["sale"]), xytext=(t, mejor["entra"]),
                     arrowprops=dict(arrowstyle="->", color=E.NEUTRO,
                                     linewidth=0.9, shrinkA=4, shrinkB=4))
    ax_caso.plot([t - pd.Timedelta("1h"), t + pd.Timedelta("1h")],
                 [ancla_previa, ancla_post], color=E.DESPUES, linewidth=0.9,
                 linestyle=":", zorder=4)
    ax_caso.set_ylim(lo - margen, hi + 1.75 * margen)
    ax_caso.set_ylabel("Demanda (kW)" if mejor["magnitud"] == "demanda"
                       else "Generación (kW)")
    ax_caso.set_xlabel("Día y mes de 2025")
    ax_caso.set_title(f"El caso: {E.etiqueta_institucion(mejor['inst'])}, "
                      f"{E.fmt_fecha(t, 'dia_corto')}", pad=7)
    # Una marca por dia: con marcas cada doce horas las siete etiquetas se
    # imprimian una encima de otra.
    ax_caso.xaxis.set_major_locator(mdates.DayLocator())
    ax_caso.xaxis.set_minor_locator(mdates.HourLocator(byhour=(12,)))
    ax_caso.xaxis.set_major_formatter(FuncFormatter(
        lambda v, _: mdates.num2date(v).strftime("%d/%m")))
    ax_caso.tick_params(axis="x", labelsize=7)
    # La leyenda cae dentro de la banda que marca la zona que el umbral
    # retira; sin fondo propio, sus rotulos se leerian como parte de ella.
    ax_caso.legend(loc="upper left", fontsize=6.8, handlelength=1.6,
                   borderpad=0.25, labelspacing=0.3, frameon=True,
                   facecolor="white", edgecolor="none", framealpha=0.92)

    # ── paneles de la regla ──────────────────────────────────────────────
    # La columna de umbrales en kilovatios va a la derecha del dato y no
    # sobre el: el candidato mas alejado, el de la UCC, cae en 2,49 y la
    # cifra se imprimia encima de su rombo.
    X_ROTULO = 3.02
    filas_csv = []
    for ax, magnitud in ((ax_dem, "demanda"), (ax_gen, "generación")):
        sub = censo[censo.magnitud == magnitud].set_index("institucion")
        for k, inst in enumerate(E.ORDEN_INSTITUCIONES):
            f = sub.loc[inst]
            p = f["p995_kW"]
            q25, q75 = f["q25_kW"] / p, f["q75_kW"] / p
            cola, tukey = f["max_kW"] / p, f["cand_tukey_kW"] / p
            umbral = f["umbral_kW"] / p
            ax.plot([q75, cola], [k, k], color=E.NEUTRO, linewidth=0.9,
                    solid_capstyle="butt", zorder=2)
            ax.plot([cola, cola], [k - 0.17, k + 0.17], color=E.NEUTRO,
                    linewidth=0.9, zorder=2)
            ax.barh(k, q75 - q25, left=q25, height=0.36, color=E.APAGADO,
                    edgecolor="white", linewidth=0.6, zorder=3)
            ax.plot([tukey], [k], marker="o", markersize=6.2,
                    markerfacecolor="white", markeredgecolor=E.NEUTRO,
                    markeredgewidth=1.1, linestyle="none", zorder=4)
            ax.plot([umbral], [k], marker="D", markersize=5.0, color=E.ALERTA,
                    linestyle="none", zorder=5)
            ax.text(X_ROTULO, k, E.fmt_miles(f["umbral_kW"], 1), fontsize=6.4,
                    color=E.NEUTRO, ha="right", va="center")
            if f["atipicos"]:
                # En la ultima fila el rotulo iria contra el eje inferior;
                # ahi se pone encima del renglon y no debajo.
                ultima = k == len(E.ORDEN_INSTITUCIONES) - 1
                ax.text(umbral + 0.05, k - 0.28 if ultima else k + 0.28,
                        f"{int(f['atipicos'])} h retiradas",
                        fontsize=6.2, color=E.ANTES, ha="left",
                        va="bottom" if ultima else "top")
            filas_csv.append({
                "bloque": "criterio", "institucion": inst, "magnitud": magnitud,
                "q25_kW": f["q25_kW"], "q75_kW": f["q75_kW"], "p995_kW": p,
                "max_kW": f["max_kW"], "cand_tukey_kW": f["cand_tukey_kW"],
                "cand_piso_kW": f["cand_piso_kW"], "umbral_kW": f["umbral_kW"],
                "manda": f["manda"], "horas_retiradas": int(f["atipicos"])})
        ax.axvline(1.2, color=E.ALERTA, linewidth=1.0, linestyle="--",
                   alpha=0.85, zorder=1)
        E.eje_instituciones(ax, eje="y")
        ax.tick_params(axis="y", labelsize=7)
        ax.set_xlim(0, 3.06)
        ax.set_xticks([0, 0.5, 1.0, 1.5, 2.0, 2.5])
        ax.set_title(magnitud.capitalize(), pad=5, fontsize=8.5)
        ax.grid(axis="y", visible=False)
    ax_dem.tick_params(axis="x", labelbottom=False)
    # Los dos rotulos de cabecera van dentro del area, colgando del borde
    # superior: por encima del eje se imprimian sobre el titulo del panel.
    ax_dem.text(1.26, -0.46, "piso: 1,2 × P99,5", fontsize=6.3, color=E.ALERTA,
                ha="left", va="top")
    # La cabecera de la columna va sobre el borde superior y no dentro:
    # dentro se imprimia contra la cifra de la primera fila.
    ax_dem.text(X_ROTULO, -0.60, "umbral (kW)", fontsize=6.3, color=E.NEUTRO,
                ha="right", va="bottom")
    ax_gen.set_xlabel("Múltiplos del percentil 99,5 de la propia serie",
                      fontsize=7.6)
    ax_gen.xaxis.set_major_formatter(FuncFormatter(lambda v, _: E.fmt_miles(v, 1)))

    marcas = [
        Patch(facecolor=E.APAGADO, edgecolor="white",
              label="Mitad central de las lecturas"),
        Line2D([], [], color=E.NEUTRO, linewidth=0.9,
               label="Hasta el máximo observado"),
        Line2D([], [], marker="o", markerfacecolor="white", linestyle="none",
               markeredgecolor=E.NEUTRO, markersize=6.2,
               label="Cerca de Tukey"),
        Line2D([], [], marker="D", color=E.ALERTA, linestyle="none",
               markersize=5.0, label="Umbral aplicado"),
    ]
    filas_csv.append({
        "bloque": "caso", "institucion": mejor["inst"],
        "magnitud": mejor["magnitud"], "hora": str(t),
        "entra_kW": mejor["entra"], "umbral_kW": mejor["umbral"],
        "exceso_pct": 100 * mejor["exceso"], "sale_kW": mejor["sale"],
        "ancla_previa_kW": ancla_previa, "ancla_posterior_kW": ancla_post})

    _rotulo_cobertura(fig, cobertura)
    fig.tight_layout(rect=(0, 0.10, 1, 0.945))
    # La leyenda se coloca despues de componer y por debajo del rotulo de
    # eje mas bajo, medido sobre el render: fijarla a una altura elegida a
    # ojo la imprimia encima de los dos rotulos de eje.
    fig.legend(handles=marcas, loc="upper center",
               bbox_to_anchor=(0.5, _bajo_de_los_ejes(fig, (ax_caso, ax_gen))),
               ncol=4, fontsize=6.8, frameon=False, handlelength=1.6,
               columnspacing=1.4, labelspacing=0.25)
    return E.guardar(
        fig, f"f3_05_umbral_atipicos_{cobertura}",
        datos=pd.DataFrame(filas_csv),
        procedencia=[
            f"reformateo/documento/datos_cache/preproceso_{cobertura}.npz",
            "criterio: max(Q75 + 5*IQR, P99,5 * 1,2) — "
            "data/xm_data_loader.py::_clean",
            f"caso: {mejor['inst']}, {t}, hora retirada aislada de mayor "
            "exceso relativo sobre el umbral",
        ])


# ─────────────────────────────────────────────────────────────────────────────
# Los tres huecos de la escalera van fijados en el generador y no buscados
# por codigo, igual que el dia de la reconstruccion: los asertos comprueban
# que cada uno mantiene la longitud y el reparto que la figura afirma, y
# detienen la corrida si dejan de tenerlos. El tercero es el hueco mas largo
# de su frontera, y eso tambien se comprueba. En M1 el mas largo empata
# entre el Hospital y CESMAG con 42 horas; se toma el primero en el orden
# fijo de instituciones, que ademas es el mismo medidor de los otros dos
# peldaños, de modo que los tres paneles comparan el mismo aparato.
HUECOS_ESCALERA = {
    "m1": [("HUDN", "2025-07-26 05:00", 3, (3, 0, 0)),
           ("HUDN", "2025-12-12 21:00", 13, (3, 10, 0)),
           ("HUDN", "2025-12-07 22:00", 42, (3, 24, 15))],
    "m3": [("HUDN", "2025-07-26 05:00", 3, (3, 0, 0)),
           ("HUDN", "2025-12-12 21:00", 13, (3, 10, 0)),
           ("UCC", "2025-12-11 09:00", 49, (3, 24, 22))],
}
# Alcance de la cascada: 3 horas de interpolacion mas 24 de arrastre hacia
# adelante mas 24 hacia atras. Se calcula aqui una sola vez porque es la
# cifra contra la que la figura mide el hueco mas largo del estudio.
ALCANCE_CASCADA = 3 + 24 + 24


def f36_escalera_huecos(cobertura: str = "m1"):
    """
    F3.6 — La escalera: la longitud del hueco decide el tratamiento.

    Tres huecos reales de longitud creciente, uno por peldaño, con el eje
    horizontal en horas desde el inicio del hueco, que es la magnitud de la
    que depende la regla. Los tres comparten figura a proposito: separados,
    la unica diferencia entre ellos, la longitud, viajaria entre paginas,
    que es donde peor se compara.

    El cuarto tratamiento, el relleno con cero, no tiene ningun caso que
    enseñar. La cascada cierra cualquier hueco de hasta 51 horas y el mas
    largo del estudio mide 49, de modo que en las veinte series de las dos
    fronteras ninguna hora llega a el. Eso se publica como resultado, no se
    omite.
    """
    censo, detalle, series = _censo_limpieza(cobertura)
    dem = censo[censo.magnitud == "demanda"].set_index("institucion")

    # El hueco mas largo de la frontera, medido, para comprobar el tercer
    # peldaño y para la cifra que cierra la figura.
    mas_largo = 0
    for inst in E.ORDEN_INSTITUCIONES:
        for magnitud in ("demanda", "generación"):
            for _, _, n in _rachas(detalle[(inst, magnitud)]["entran"]):
                mas_largo = max(mas_largo, n)

    fig = plt.figure(figsize=(E.ANCHO_COMPLETO, 5.2))
    malla = fig.add_gridspec(2, 3, height_ratios=(1.0, 0.88), hspace=0.68,
                             wspace=0.32)
    ejes = [fig.add_subplot(malla[0, j]) for j in range(3)]
    ax_pres = fig.add_subplot(malla[1, :2])
    ax_cero = fig.add_subplot(malla[1, 2])

    filas_csv = []
    largo_max_declarado = max(x[2] for x in HUECOS_ESCALERA[cobertura])
    for ax, (inst, inicio, largo, reparto) in zip(ejes,
                                                  HUECOS_ESCALERA[cobertura]):
        r = detalle[(inst, "demanda")]
        t0 = pd.Timestamp(inicio)
        candidatas = [x for x in _rachas(r["entran"]) if x[0] == t0]
        assert candidatas, f"{cobertura}/{inst}: no hay hueco que empiece en {t0}"
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
        if largo == largo_max_declarado:
            assert n == mas_largo, (
                f"{cobertura}: el tercer peldaño mide {n} h y el hueco más "
                f"largo de la frontera mide {mas_largo}")

        entrada = series[dem.loc[inst, "serie_entrada"]]
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
        ax.set_ylim(base - 0.05 * span, hi + 0.16 * span)

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
        # El nombre del mecanismo no cabe junto a la cifra en el peldaño
        # largo, donde los tres tramos se reparten el mismo ancho impreso:
        # las llaves miden y la leyenda comun nombra.
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

        ax.set_xlim(-ctx - 0.6, n + ctx + 0.6)
        ax.set_title(f"{E.etiqueta_institucion(inst)} · "
                     f"{t0.day} {MESES_ES[t0.month - 1]} {t0.year}\n"
                     f"hueco de {n} horas", fontsize=8.2, pad=5)
        ax.set_xlabel("Horas desde el inicio del hueco", fontsize=7.2)
        ax.tick_params(labelsize=7)
        ax.xaxis.set_major_locator(
            MultipleLocator(1 if n <= 4 else (6 if n <= 16 else 12)))
        filas_csv.append({
            "bloque": "peldaño", "institucion": inst, "inicio": str(t0),
            "horas": n, "interpoladas": n_int, "arrastre_adelante": n_ff,
            "arrastre_atras": n_bf, "cero": 0,
            "ancla_previa_kW": ancla_previa, "ancla_posterior_kW": ancla_post,
            "meseta_kW": meseta})
    ejes[0].set_ylabel("Demanda (kW)")

    # ── el presupuesto de horas ──────────────────────────────────────────
    total_int = int(dem["interpoladas"].sum())
    total_arr = int(dem["arrastradas"].sum())
    tope = float((dem["interpoladas"] + dem["arrastradas"]).max())
    for k, inst in enumerate(E.ORDEN_INSTITUCIONES):
        f = dem.loc[inst]
        n_i, n_a = int(f["interpoladas"]), int(f["arrastradas"])
        if n_i:
            ax_pres.barh(k, n_i, height=0.5, color=E.DESPUES, zorder=3)
        if n_a:
            ax_pres.barh(k, n_a, left=n_i, height=0.5, color=E.NEUTRO,
                         edgecolor="white", linewidth=1.2, zorder=3)
        total = n_i + n_a
        if total:
            rotulo = f"{E.fmt_miles(total)} h"
            if f["atipicos"]:
                rotulo += f"  ({int(f['atipicos'])} del umbral)"
            ax_pres.text(total + 0.02 * tope, k, rotulo, fontsize=6.6,
                         color=E.TINTA, va="center")
        else:
            ax_pres.text(0.02 * tope, k, "ninguna", fontsize=6.6,
                         color=E.NEUTRO, va="center", style="italic")
        filas_csv.append({
            "bloque": "presupuesto", "institucion": inst, "horas": total,
            "interpoladas": n_i, "arrastradas": n_a, "cero": 0,
            "atipicos_retirados": int(f["atipicos"])})
    E.eje_instituciones(ax_pres, eje="y")
    ax_pres.tick_params(axis="y", labelsize=7.5)
    ax_pres.set_xlim(0, max(1.0, tope) * 1.52)
    ax_pres.set_xlabel("Horas tratadas en la serie de demanda (h)", fontsize=7.4)
    ax_pres.tick_params(axis="x", labelsize=7)
    ax_pres.grid(axis="y", visible=False)
    ax_pres.set_title(f"El presupuesto: {E.fmt_miles(total_int)} horas "
                      f"interpoladas y {E.fmt_miles(total_arr)} arrastradas",
                      fontsize=8.5, pad=6)

    # ── el peldaño que no existe ─────────────────────────────────────────
    ax_cero.axis("off")
    ax_cero.add_patch(Rectangle((0.03, 0.04), 0.94, 0.90,
                                transform=ax_cero.transAxes,
                                facecolor=E.FONDO_BANDA, edgecolor="none",
                                zorder=0))
    ax_cero.text(0.5, 0.74, "0", fontsize=32, color=E.TINTA, ha="center",
                 va="center", transform=ax_cero.transAxes)
    ax_cero.text(0.5, 0.45, "horas rellenas con cero\nen las diez series",
                 fontsize=7.0, color=E.TINTA, ha="center", va="center",
                 transform=ax_cero.transAxes)
    ax_cero.text(0.5, 0.19, f"el hueco más largo mide {mas_largo} h\ny la "
                 f"cascada alcanza {ALCANCE_CASCADA} h", fontsize=6.4,
                 color=E.NEUTRO, ha="center", va="center",
                 transform=ax_cero.transAxes)
    filas_csv.append({
        "bloque": "resumen", "institucion": "las diez series",
        "interpoladas": total_int, "arrastradas": total_arr,
        "cero": int(censo["cero"].sum()),
        "atipicos_retirados": int(censo["atipicos"].sum()),
        "hueco_mas_largo_h": mas_largo, "alcance_cascada_h": ALCANCE_CASCADA})

    _rotulo_cobertura(fig, cobertura)
    fig.tight_layout(rect=(0, 0, 1, 0.945))
    # Una sola leyenda para los dos bloques: las llaves de los paneles
    # miden y esta nombra, de modo que ningun rotulo tenga que caber junto
    # a un tramo de tres horas. Va medida bajo la fila de arriba.
    fig.legend(handles=[
        Line2D([], [], color=E.TINTA, linewidth=1.1, marker="o", markersize=3.4,
               label="Lectura observada"),
        Line2D([], [], color=E.DESPUES, linewidth=1.8, marker="o",
               markersize=3.6, label="Interpolación, hasta 3 h"),
        Line2D([], [], color=E.NEUTRO, linewidth=1.5, marker="s",
               markersize=3.6, label="Arrastre hacia adelante, hasta 24 h"),
        Line2D([], [], color=E.NEUTRO, linewidth=1.5, marker="^",
               markersize=3.6, label="Arrastre hacia atrás, hasta 24 h")],
        loc="upper center",
        bbox_to_anchor=(0.5, _bajo_de_los_ejes(fig, ejes, 0.008)),
        ncol=4, fontsize=6.8, frameon=False, handlelength=1.9,
        columnspacing=1.5)
    return E.guardar(
        fig, f"f3_06_escalera_huecos_{cobertura}", datos=pd.DataFrame(filas_csv),
        procedencia=[
            f"reformateo/documento/datos_cache/preproceso_{cobertura}.npz",
            "cascada: interpolación temporal límite 3 h, arrastre hacia "
            "adelante y hacia atrás límite 24 h, resto a cero — "
            "data/xm_data_loader.py::_clean",
            "los tres huecos van fijados en el generador y comprobados con "
            "asertos de longitud y reparto antes de dibujar",
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
    f32b_profundidad("m1")
    f33_reconstruccion("m1", "Udenar")
    for cob in ("m1", "m3"):
        f37_matrices(cob)
        f38_perfiles_instituciones(cob)
        f39_ritmos(cob)
    for cob in ("m1", "m3"):
        f35_umbral_atipicos(cob)
        f36_escalera_huecos(cob)
    print("\nlisto.")
