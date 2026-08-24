"""
gen_cap13.py — Figuras del capítulo 13: inferencia estadística.
================================================================
La pregunta que responde el capítulo es si la ventaja diaria del mercado
P2P frente al mecanismo colectivo es un efecto sostenido o el residuo de
unos pocos días afortunados. Se responde con un remuestreo por bloques de
siete días, que preserva la autocorrelación semanal de la serie.

Contra cuál C4
--------------
Las tres figuras comparan el P2P contra el **colectivo en base horaria**,
que es la única versión que trae la serie diaria del canon: sus columnas
suman 51,54 millones en M1 y 31,84 en M3, que son exactamente las cifras
de C4 horario del libro de comparación, y no las de C4 mensual. El
capítulo 10 compara contra la versión mensual, que es la que rige. Los
rótulos lo dicen en las tres figuras porque, sin decirlo, el capítulo
parecería contradecir al 10: en la cobertura M3 el P2P gana el 99,2 % de
los días contra el colectivo horario y aun así pierde por 4,54 millones
contra el mensual en el agregado del horizonte.

Las réplicas las recupera ``bootstrap_remuestras.py``, que reproduce las
cifras publicadas dígito a dígito.

    python scripts/bootstrap_remuestras.py     # una vez
    python scripts/gen_cap13.py
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

CACHE = Path(__file__).resolve().parent.parent / "datos_cache"

# Rótulo del comparador, para que ninguna de las tres figuras deje al
# lector adivinando de qué C4 se habla.
REFERENCIA = "C4 · colectivo (horario)"


def _cargar(cobertura: str):
    boot = CACHE / f"bootstrap_replicas_{cobertura}.npy"
    delta = CACHE / f"bootstrap_delta_{cobertura}.npy"
    if not boot.exists():
        raise FileNotFoundError(
            "Faltan las réplicas. Generarlas con: "
            "python scripts/bootstrap_remuestras.py")
    return np.load(boot), np.load(delta)


# ─────────────────────────────────────────────────────────────────────────────
def f131_serie_diaria():
    """
    F13.1 — La serie que entra al remuestreo.

    Diferencia diaria entre la ganancia del mercado P2P y la del mecanismo
    colectivo en base horaria, día a día sobre los 256 del horizonte.

    Los días desfavorables son pocos y muy pequeños: en M1 son ocho, y el
    peor vale 473 pesos frente a una escala de decenas de miles, de modo
    que dibujados a escala no se ven. Por eso la banda bajo el cero va
    sombreada y cada día desfavorable lleva su propia marca: la ventaja es
    sostenida, no unánime, y conviene poder contar las excepciones. Se
    separan además los días sin diferencia alguna, que son aquellos en que
    no hubo mercado y que contar como desfavorables sería inexacto.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.7, compartir_y=False)
    filas = []
    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
        _, delta = _cargar(cob)
        dias = np.arange(len(delta))
        colores = np.where(delta > 0, E.MECANISMOS["P2P"], E.ANTES)
        ax.bar(dias, delta, width=1.0, color=colores, linewidth=0, zorder=3)

        tope = float(delta.max())
        piso = -0.11 * tope
        ax.set_ylim(piso, tope * 1.30)
        ax.axhspan(piso, 0, color=E.ANTES, alpha=0.07, zorder=0)
        ax.axhline(0, color="#333333", linewidth=0.9, zorder=2)
        ax.axhline(delta.mean(), color=E.ALERTA, linewidth=1.3,
                   linestyle="--", zorder=4)

        n_favor = int((delta > 0).sum())
        n_cero = int((delta == 0).sum())
        n_contra = int((delta < 0).sum())
        # Cada día desfavorable, con marca propia bajo el cero: a escala
        # son invisibles y el recuento quedaría sin respaldo visual.
        if n_contra:
            ax.scatter(dias[delta < 0], np.full(n_contra, piso * 0.55),
                       marker="v", s=14, color=E.ANTES, zorder=5)
            # El rotulo de las marcas va en la caja de cifras y no en la
            # banda: las marcas ocupan casi todo el ancho y cualquier
            # etiqueta puesta ahi acabaria encima de alguna.
            cola = ("$\\blacktriangledown$  "
                    f"{E.fmt_miles(n_contra)} en contra "
                    f"(el peor, {E.fmt_miles(delta.min())} COP)")
        else:
            ax.text(len(delta) * 0.99, piso * 0.55, "ningún día en contra",
                    ha="right", va="center", fontsize=6.6, color=E.ANTES)
            cola = "ninguno en contra"

        ax.text(0.03, 0.96,
                f"media {E.fmt_miles(delta.mean())} COP/día\n"
                f"{E.fmt_miles(n_favor)} días a favor · "
                f"{E.fmt_miles(n_cero)} sin diferencia\n" + cola,
                transform=ax.transAxes, va="top", fontsize=7.2,
                linespacing=1.35,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor=E.NEUTRO, linewidth=0.6, alpha=0.92))
        ax.set_xlabel("Día del horizonte", fontsize=8.5)
        ax.set_xlim(-3, len(delta) + 2)
        E.eje_espanol(ax, "y", "miles")
        for d, v in zip(dias, delta):
            filas.append({"cobertura": cob.upper(), "dia": int(d),
                          "delta_COP": v, "dias_a_favor": n_favor,
                          "dias_sin_diferencia": n_cero,
                          "dias_en_contra": n_contra})
    ax_m1.set_ylabel(f"P2P $-$ {REFERENCIA}\n(COP/día)", fontsize=8.5)
    ax_m3.set_ylabel(f"P2P $-$ {REFERENCIA}\n(COP/día)", fontsize=8.5)
    fig.tight_layout()
    return E.guardar(fig, "f13_01_serie_diaria", datos=pd.DataFrame(filas),
                     procedencia=[
                         "SALIDAS_SERVIDOR/entrega_canonica_2026-08/canonica_"
                         "{m1,m3}/outputs/daily_series_*.csv (columnas nb_p2p "
                         "y nb_c4)",
                         "la columna nb_c4 suma 51,54 M en M1 y 31,84 M en M3: "
                         "es C4 en base horaria, no C4 mensual"])


# ─────────────────────────────────────────────────────────────────────────────
def f132_bootstrap():
    """
    F13.2 — La distribución del remuestreo.

    Histograma de las 10.000 réplicas de la media, con el intervalo del
    95 % marcado y el cero señalado. El argumento es geométrico: si el
    intervalo completo cae a la derecha del cero, la ventaja no es
    atribuible al azar del muestreo.

    Las cifras reproducen el artefacto canónico dígito a dígito; la
    comprobación la hace ``bootstrap_remuestras.py`` antes de guardar.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.7, compartir_y=False)
    filas = []
    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
        boot, delta = _cargar(cob)
        canon = D.bootstrap(cob)
        lo, hi = float(canon["ci_95_lower"]), float(canon["ci_95_upper"])
        media = float(canon["delta_mean"])

        n, bordes, parches = ax.hist(boot, bins=60, color=E.MECANISMOS["P2P"],
                                     alpha=0.30, edgecolor="none")
        # Se resalta el tramo central: el 95 % de las réplicas.
        for b, p in zip(bordes[:-1], parches):
            if lo <= b <= hi:
                p.set_alpha(0.75)

        ax.axvline(media, color=E.MECANISMOS["P2P"], linewidth=1.8)
        for v in (lo, hi):
            ax.axvline(v, color=E.MECANISMOS["P2P"], linewidth=1.1,
                       linestyle="--")
        ax.axvline(0, color=E.ANTES, linewidth=1.5)
        ax.set_ylim(0, max(n) * 1.24)
        # El rótulo del cero va a media altura: arriba lo tapaba la caja de
        # cifras y abajo se salía del eje.
        ax.text(0, max(n) * 0.50, " sin ventaja", color=E.ANTES,
                fontsize=7.2, va="center", ha="left", rotation=90)

        # Anotación del intervalo, sobre el propio histograma.
        ax.annotate("", xy=(lo, max(n) * 1.06), xytext=(hi, max(n) * 1.06),
                    arrowprops=dict(arrowstyle="<->", color=E.MECANISMOS["P2P"],
                                    lw=1.0))
        # Fondo blanco: la etiqueta cae sobre la vertical de la media.
        ax.text((lo + hi) / 2, max(n) * 1.10, "IC 95 %", ha="center",
                fontsize=7.5, color=E.MECANISMOS["P2P"], fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                          edgecolor="none"))

        # La caja va al flanco izquierdo, que el histograma deja vacio:
        # entre el cero y el inicio de la distribucion no hay ninguna replica.
        ax.text(0.10, 0.97,
                f"media {E.fmt_miles(media)}\n"
                f"IC [{E.fmt_miles(lo)}; {E.fmt_miles(hi)}]\n"
                f"$d$ de Cohen {E.fmt_miles(float(canon['cohens_d']), 3)}",
                transform=ax.transAxes, ha="left", va="top", fontsize=7.2,
                linespacing=1.35,
                bbox=dict(boxstyle="round,pad=0.32", facecolor="white",
                          edgecolor=E.NEUTRO, linewidth=0.6, alpha=0.95))
        E.eje_espanol(ax, "x", "miles")
        ax.tick_params(axis="x", labelrotation=20, labelsize=7)
        filas.append({"cobertura": cob.upper(), "delta_mean": media,
                      "ci_95_lower": lo, "ci_95_upper": hi,
                      "cohens_d": float(canon["cohens_d"]),
                      "n_bootstrap": int(canon["n_bootstrap"]),
                      "block_days": int(canon["block_days"]),
                      "n_eff": int(canon["n_eff"])})
    ax_m1.set_ylabel("Réplicas", fontsize=8.5)
    ax_m3.set_ylabel("Réplicas", fontsize=8.5)
    fig.tight_layout(rect=[0, 0.13, 1, 1])
    fig.supxlabel(f"Media remuestreada de P2P $-$ {REFERENCIA} (COP/día)",
                  fontsize=8.5, y=0.045)
    return E.guardar(fig, "f13_02_bootstrap", datos=pd.DataFrame(filas),
                     procedencia=[
                         "SALIDAS_SERVIDOR/entrega_canonica_2026-08/canonica_"
                         "{m1,m3}/outputs/bootstrap_42.json",
                         "réplicas recuperadas por scripts/bootstrap_remuestras.py "
                         "(semilla 42; reproduce el canon digito a digito)",
                         "la referencia es C4 en base horaria, la unica que trae "
                         "la serie diaria del canon"])


# ─────────────────────────────────────────────────────────────────────────────
def f133_tamano_efecto():
    """
    F13.3 — Tamaño del efecto y muestra efectiva.

    El valor p dice si el efecto existe; el tamaño del efecto dice si
    importa. Se sitúa la *d* de Cohen de cada cobertura sobre las bandas
    convencionales, y se declara la muestra efectiva: al remuestrear por
    bloques de siete días, 256 días valen como 36 observaciones
    independientes, no como 256.
    """
    fig, ax = E.figura(alto=3.0)
    bandas = [(0.0, 0.2, "insignificante"), (0.2, 0.5, "pequeño"),
              (0.5, 0.8, "medio"), (0.8, 1.4, "grande")]
    grises = ["#F2F2F2", "#E4E4E4", "#D2D2D2", "#BFBFBF"]
    for (a, b, etiqueta), g in zip(bandas, grises):
        ax.axvspan(a, b, color=g, zorder=0)
        ax.text((a + b) / 2, 1.44, etiqueta, ha="center", fontsize=7,
                color="#666666")

    filas = []
    for k, cob in enumerate(("m1", "m3")):
        canon = D.bootstrap(cob)
        d = float(canon["cohens_d"])
        p = float(canon["p_valor_wilcoxon"])
        y = 1.05 - k * 0.50
        ax.plot([0, d], [y, y], color=E.COBERTURAS[cob], linewidth=2.0,
                zorder=3)
        ax.scatter([d], [y], s=70, color=E.COBERTURAS[cob], zorder=4,
                   edgecolors="white", linewidths=1.0)
        ax.text(d + 0.03, y + 0.09,
                f"{cob.upper()}:  $d$ = {E.fmt_miles(d, 3)}",
                va="center", fontsize=8, color=E.COBERTURAS[cob])
        exp_p = int(np.ceil(np.log10(p)))
        ax.text(d + 0.03, y - 0.09,
                f"$n_{{ef}}$ = {int(canon['n_eff'])} de "
                f"{int(canon['n_days'])} días  ·  Wilcoxon "
                f"$p < 10^{{{exp_p}}}$",
                va="center", fontsize=6.6, color=E.COBERTURAS[cob])
        filas.append({"cobertura": cob.upper(), "cohens_d": d,
                      "n_eff": int(canon["n_eff"]),
                      "n_days": int(canon["n_days"]),
                      "p_wilcoxon": p})

    ax.set_xlim(0, 1.4)
    ax.set_ylim(0.20, 1.66)
    ax.set_yticks([])
    ax.set_xlabel(f"$d$ de Cohen de la diferencia diaria P2P $-$ {REFERENCIA}")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return E.guardar(fig, "f13_03_tamano_efecto", datos=pd.DataFrame(filas),
                     procedencia=[
                         "SALIDAS_SERVIDOR/entrega_canonica_2026-08/canonica_"
                         "{m1,m3}/outputs/bootstrap_42.json",
                         "la referencia es C4 en base horaria"])


if __name__ == "__main__":
    D.verificar_canon()
    print("\nCapítulo 13 — inferencia estadística")
    f131_serie_diaria()
    f132_bootstrap()
    f133_tamano_efecto()
    print("\nlisto.")
