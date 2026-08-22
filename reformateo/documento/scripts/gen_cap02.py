"""
gen_cap02.py — Figuras del capítulo 2: el dato crudo.
======================================================
Qué se midió, con qué instrumentos y durante cuánto tiempo. Las tres
figuras responden a la pregunta que un revisor hace primero: ¿de dónde
salen estos datos y cuánto hay de ellos?

Requiere el censo de fuentes:

    python scripts/cache_fuentes.py
    python scripts/gen_cap02.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estilo as E
import datos as D

CACHE = Path(__file__).resolve().parent.parent / "datos_cache"


def _censo() -> pd.DataFrame:
    p = CACHE / "fuentes.csv"
    if not p.exists():
        raise FileNotFoundError(
            "Falta fuentes.csv. Generarlo con: python scripts/cache_fuentes.py")
    d = pd.read_csv(p, encoding="utf-8-sig")
    d["inicio"] = pd.to_datetime(d["inicio"])
    d["fin"] = pd.to_datetime(d["fin"])
    return d


# ─────────────────────────────────────────────────────────────────────────────
def f22_gantt():
    """
    F2.2 — Cobertura temporal de las veintisiete fuentes.

    Una barra por fuente, del primer al último registro. La franja
    sombreada es el horizonte del estudio, y el argumento de la figura es
    que su inicio no se eligió: viene impuesto por la última fuente en
    entrar en servicio.

    Las fuentes que el modelo usa se dibujan en color; las auxiliares, en
    gris, para que se vea que el conjunto instrumentado es mayor que el
    conjunto empleado.
    """
    d = _censo()
    d = d.sort_values(["institucion", "clase", "fuente"],
                      key=lambda s: s.map(
                          {a: i for i, a in enumerate(D.AGENTES)}).fillna(
                          pd.Series(range(len(s)), index=s.index))
                      if s.name == "institucion" else s)

    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 5.2))
    y, etiquetas, colores_y = [], [], []
    for i, (_, f) in enumerate(d.iterrows()):
        usado = f["papel"] != "no usado"
        color = (E.color_institucion(f["institucion"]) if usado else "#CFCFCF")
        ax.barh(i, (f["fin"] - f["inicio"]).days, left=f["inicio"],
                height=0.62, color=color)
        etiquetas.append(f"{f['fuente'][:34]}")
        colores_y.append(E.color_institucion(f["institucion"])
                         if usado else "#9A9A9A")
        y.append(i)

    ini, fin = pd.Timestamp(D.T_START), pd.Timestamp(D.T_END)
    ax.axvspan(ini, fin, color=E.MECANISMOS["P2P"], alpha=0.13, zorder=0)
    for v in (ini, fin):
        ax.axvline(v, color=E.MECANISMOS["P2P"], linewidth=1.3, zorder=4)
    ax.text(ini, len(d) - 0.2, " horizonte del estudio ",
            color=E.MECANISMOS["P2P"], fontsize=7.5, fontweight="bold",
            va="bottom")

    ax.set_yticks(y)
    ax.set_yticklabels(etiquetas, fontsize=5.6)
    for t, c in zip(ax.get_yticklabels(), colores_y):
        t.set_color(c)
    ax.invert_yaxis()
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
    ax.tick_params(axis="x", labelsize=7)
    ax.set_xlabel("Fecha")
    ax.set_title("Cobertura temporal de las 27 fuentes instrumentadas",
                 pad=8)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return E.guardar(fig, "f2_02_gantt_fuentes", datos=d, procedencia=[
        "MedicionesMTE_v3/ (recorrido de las 27 subcarpetas de medidor "
        "e inversor)",
        "censo generado por scripts/cache_fuentes.py"])


# ─────────────────────────────────────────────────────────────────────────────
def f23_cobertura_fuentes():
    """
    F2.3 — Cuánto dato hay en cada fuente.

    Cobertura horaria sobre el horizonte, por fuente. Los inversores se
    evalúan solo en la franja diurna: contar la noche como dato faltante
    confundiría la ausencia de sol con la ausencia de medición.

    La figura sirve para localizar las excepciones, que son dos y están
    acotadas.
    """
    d = _censo()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(E.ANCHO_COMPLETO, 4.2),
                                   gridspec_kw={"width_ratios": [1.5, 1]})

    med = d[d["clase"] == "medidor"].reset_index(drop=True)
    y = np.arange(len(med))
    colores = [E.color_institucion(i) if p != "no usado" else "#CFCFCF"
               for i, p in zip(med["institucion"], med["papel"])]
    ax1.barh(y, med["cobertura_pct"], 0.64, color=colores)
    ax1.set_yticks(y)
    ax1.set_yticklabels([f"{f[:30]}" for f in med["fuente"]], fontsize=5.8)
    ax1.invert_yaxis()
    ax1.set_xlim(0, 108)
    ax1.axvline(med["cobertura_pct"].mean(), color=E.ALERTA,
                linestyle="--", linewidth=1.2)
    ax1.text(med["cobertura_pct"].mean() - 1, len(med) - 0.4,
             f"media {E.fmt_miles(med['cobertura_pct'].mean(), 1)} %",
             color=E.ALERTA, fontsize=7, ha="right", va="bottom")
    ax1.set_xlabel("Cobertura horaria sobre el horizonte [%]")
    ax1.set_title("Los 20 medidores", pad=8)

    inv = d[d["clase"] == "inversor"].reset_index(drop=True)
    y2 = np.arange(len(inv))
    ax2.barh(y2, inv["cobertura_diurna_pct"], 0.6,
             color=[E.color_institucion(i) for i in inv["institucion"]])
    ax2.set_yticks(y2)
    ax2.set_yticklabels([f"{f[:26]}" for f in inv["fuente"]], fontsize=5.8)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 118)
    for j, v in enumerate(inv["cobertura_diurna_pct"]):
        ax2.text(v + 2, j, E.fmt_miles(v, 0) + " %", va="center", fontsize=6.5)
    ax2.set_xlabel("Cobertura diurna (06--18 h) [%]")
    ax2.set_title("Los 7 inversores", pad=8)

    fig.tight_layout()
    return E.guardar(fig, "f2_03_cobertura_fuentes", datos=d, procedencia=[
        "censo generado por scripts/cache_fuentes.py sobre MedicionesMTE_v3/"])


# ─────────────────────────────────────────────────────────────────────────────
def f24_horizonte():
    """
    F2.4 — Por qué el horizonte empieza cuando empieza.

    Fecha del primer registro de cada fuente que el modelo usa. El inicio
    del horizonte no se eligió: lo fija la última fuente en entrar en
    servicio, porque antes de esa fecha la comunidad no está completa.
    """
    d = _censo()
    usadas = d[d["papel"] != "no usado"].sort_values("inicio").reset_index(
        drop=True)

    fig, ax = plt.subplots(figsize=(E.ANCHO_COMPLETO, 3.6))
    y = np.arange(len(usadas))
    ax.scatter(usadas["inicio"], y, s=42, zorder=4,
               color=[E.color_institucion(i) for i in usadas["institucion"]],
               edgecolors="white", linewidths=0.6)
    limite = usadas["inicio"].max()
    for j, ini in enumerate(usadas["inicio"]):
        ax.plot([ini, limite], [j, j], color="#DDDDDD", linewidth=1.0,
                zorder=1)

    ax.axvline(limite, color=E.ALERTA, linewidth=1.6, zorder=5)
    ultima = usadas.iloc[-1]
    ax.text(limite, -1.3,
            f" la última en entrar: {ultima['fuente'][:28]}\n"
            f" {limite.date()}",
            color=E.ALERTA, fontsize=7.5, va="top", fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels([f"{f[:32]}" for f in usadas["fuente"]], fontsize=6)
    ax.invert_yaxis()
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.tick_params(axis="x", labelsize=7, labelrotation=25)
    ax.set_xlabel("Primer registro de 2025")
    ax.set_title("El inicio del horizonte lo impone la última fuente "
                 "en entrar en servicio", pad=8)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return E.guardar(fig, "f2_04_horizonte", datos=usadas, procedencia=[
        "censo generado por scripts/cache_fuentes.py sobre MedicionesMTE_v3/",
        "constantes T_START y T_END en data/xm_data_loader.py"])


if __name__ == "__main__":
    print("\nCapítulo 2 — el dato crudo")
    f22_gantt()
    f23_cobertura_fuentes()
    f24_horizonte()
    print("\nlisto.")
