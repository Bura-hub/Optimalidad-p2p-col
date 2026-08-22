"""
gen_cap13.py — Figuras del capítulo 13: inferencia estadística.
================================================================
La pregunta que responde el capítulo es si la ventaja diaria del mercado
P2P frente al mecanismo colectivo es un efecto sostenido o el residuo de
unos pocos días afortunados. Se responde con un remuestreo por bloques de
siete días, que preserva la autocorrelación semanal de la serie.

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
    colectivo, día a día sobre los 256 del horizonte. Se marca la media y
    se sombrea el lado desfavorable, para que se vea cuántos días el P2P
    pierde: la ventaja es sostenida, no unánime, y conviene decirlo así.
    """
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.4, compartir_y=False)
    filas = []
    for ax, cob in ((ax_m1, "m1"), (ax_m3, "m3")):
        _, delta = _cargar(cob)
        dias = np.arange(len(delta))
        colores = np.where(delta >= 0, E.MECANISMOS["P2P"], E.ANTES)
        ax.bar(dias, delta, width=1.0, color=colores, linewidth=0)
        ax.axhline(0, color="#333333", linewidth=0.9)
        ax.axhline(delta.mean(), color=E.ALERTA, linewidth=1.3,
                   linestyle="--")
        favorables = 100.0 * (delta > 0).mean()
        ax.text(0.03, 0.95,
                f"media {E.fmt_miles(delta.mean())} COP/día\n"
                f"{E.fmt_miles(favorables, 1)} % de los días a favor",
                transform=ax.transAxes, va="top", fontsize=7.5,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor=E.NEUTRO, linewidth=0.6, alpha=0.92))
        ax.set_xlabel("Día del horizonte")
        E.eje_espanol(ax, "y", "miles")
        for d, v in zip(dias, delta):
            filas.append({"cobertura": cob.upper(), "dia": int(d), "delta_COP": v})
    ax_m1.set_ylabel("P2P $-$ C4 [COP/día]")
    ax_m3.set_ylabel("P2P $-$ C4 [COP/día]")
    fig.tight_layout()
    return E.guardar(fig, "f13_01_serie_diaria", datos=pd.DataFrame(filas),
                     procedencia=[
                         "SALIDAS_SERVIDOR/entrega_canonica_2026-08/canonica_"
                         "{m1,m3}/outputs/daily_series_*.csv",
                         "nota: la serie diaria usa C4 en base horaria (C-20)"])


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
    fig, ax_m1, ax_m3 = E.figura_m1_m3(alto=3.5, compartir_y=False)
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
        ax.text(0, ax.get_ylim()[1] * 0.97, " sin ventaja", color=E.ANTES,
                fontsize=7.2, va="top", ha="left", rotation=90)

        # Anotación del intervalo, sobre el propio histograma.
        ax.annotate("", xy=(lo, max(n) * 1.06), xytext=(hi, max(n) * 1.06),
                    arrowprops=dict(arrowstyle="<->", color=E.MECANISMOS["P2P"],
                                    lw=1.0))
        # Fondo blanco: la etiqueta cae sobre la vertical de la media.
        ax.text((lo + hi) / 2, max(n) * 1.10, "IC 95 %", ha="center",
                fontsize=7.5, color=E.MECANISMOS["P2P"], fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                          edgecolor="none"))
        ax.set_ylim(0, max(n) * 1.24)

        # La caja va al flanco izquierdo, que el histograma deja vacio:
        # entre el cero y el inicio de la distribucion no hay ninguna replica.
        ax.text(0.06, 0.97,
                f"media {E.fmt_miles(media)}\n"
                f"IC [{E.fmt_miles(lo)}; {E.fmt_miles(hi)}]\n"
                f"$d$ de Cohen {E.fmt_miles(float(canon['cohens_d']), 3)}",
                transform=ax.transAxes, ha="left", va="top", fontsize=7.2,
                linespacing=1.35,
                bbox=dict(boxstyle="round,pad=0.32", facecolor="white",
                          edgecolor=E.NEUTRO, linewidth=0.6, alpha=0.95))
        ax.set_xlabel("Media remuestreada de P2P $-$ C4 [COP/día]")
        E.eje_espanol(ax, "x", "miles")
        ax.tick_params(axis="x", labelrotation=20, labelsize=7)
        filas.append({"cobertura": cob.upper(), "delta_mean": media,
                      "ci_95_lower": lo, "ci_95_upper": hi,
                      "cohens_d": float(canon["cohens_d"]),
                      "n_bootstrap": int(canon["n_bootstrap"]),
                      "block_days": int(canon["block_days"]),
                      "n_eff": int(canon["n_eff"])})
    ax_m1.set_ylabel("Réplicas")
    ax_m3.set_ylabel("Réplicas")
    fig.tight_layout()
    return E.guardar(fig, "f13_02_bootstrap", datos=pd.DataFrame(filas),
                     procedencia=[
                         "SALIDAS_SERVIDOR/entrega_canonica_2026-08/canonica_"
                         "{m1,m3}/outputs/bootstrap_42.json",
                         "réplicas recuperadas por scripts/bootstrap_remuestras.py "
                         "(semilla 42; reproduce el canon digito a digito)"])


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
    fig, ax = E.figura(alto=2.7)
    bandas = [(0.0, 0.2, "insignificante"), (0.2, 0.5, "pequeño"),
              (0.5, 0.8, "medio"), (0.8, 1.4, "grande")]
    grises = ["#F2F2F2", "#E4E4E4", "#D2D2D2", "#BFBFBF"]
    for (a, b, etiqueta), g in zip(bandas, grises):
        ax.axvspan(a, b, color=g, zorder=0)
        ax.text((a + b) / 2, 1.42, etiqueta, ha="center", fontsize=7,
                color="#666666")

    filas = []
    for k, cob in enumerate(("m1", "m3")):
        canon = D.bootstrap(cob)
        d = float(canon["cohens_d"])
        y = 1.0 - k * 0.55
        ax.plot([0, d], [y, y], color=E.COBERTURAS[cob], linewidth=2.0,
                zorder=3)
        ax.scatter([d], [y], s=70, color=E.COBERTURAS[cob], zorder=4,
                   edgecolors="white", linewidths=1.0)
        ax.text(d + 0.03, y, f"{cob.upper()}:  $d$ = {E.fmt_miles(d, 3)}"
                f"   ·   $n_{{ef}}$ = {int(canon['n_eff'])} de "
                f"{int(canon['n_days'])} días",
                va="center", fontsize=8, color=E.COBERTURAS[cob])
        filas.append({"cobertura": cob.upper(), "cohens_d": d,
                      "n_eff": int(canon["n_eff"]),
                      "n_days": int(canon["n_days"]),
                      "p_wilcoxon": float(canon["p_valor_wilcoxon"])})

    ax.set_xlim(0, 1.4)
    ax.set_ylim(0.15, 1.62)
    ax.set_yticks([])
    ax.set_xlabel("$d$ de Cohen")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return E.guardar(fig, "f13_03_tamano_efecto", datos=pd.DataFrame(filas),
                     procedencia=[
                         "SALIDAS_SERVIDOR/entrega_canonica_2026-08/canonica_"
                         "{m1,m3}/outputs/bootstrap_42.json"])


if __name__ == "__main__":
    D.verificar_canon()
    print("\nCapítulo 13 — inferencia estadística")
    f131_serie_diaria()
    f132_bootstrap()
    f133_tamano_efecto()
    print("\nlisto.")
