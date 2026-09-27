"""
D72 · El análisis de optimalidad del canon, rehecho desde los trece almacenes.

POR QUÉ EXISTE. El análisis de optimalidad de la matriz del 2026-09-19 se
calculó con un beneficio del P2P que no era el liquidado (H-94): su total no
coincidía con la hoja `Resumen` en ninguno de los trece casos, y la
clasificación hora a hora y la Fig. 14 de las salidas originales no se citan.
D72 fija el beneficio en el de la liquidación y el resultado en el mes. Esa
liquidación por agente y hora ya está en la tabla `escenarios` de cada
almacén, de modo que **no hace falta volver a correr la matriz**: este guion
la lee y aplica `analysis/optimality.py`, el mismo código que usará toda
corrida futura.

QUÉ LEE (y nada más):
  <caso>/almacen/m1/escenarios   el dinero de P2P y C4 por agente y hora
  <caso>/almacen/m1/horas        la fecha y el mes de cada hora
  <caso>/almacen/m1/agentes      demanda, generación y papel (para el GDR)
  <caso>/almacen/m1/flujos       quién vendió a quién y cuánto (para el GDR)
  <caso>/outputs/resultados_comparacion.xlsx, hojas `Resumen` y `Por_agente`,
                                 solo para comprobar el total

QUÉ ESCRIBE, en `SALIDAS_SERVIDOR/entrega_matriz_reposo_2026-09-19/optimalidad_D72/`:
  <caso>_mensual.csv             agente (y la comunidad) x mes: P2P, C4,
                                 diferencia y quién domina
  <caso>_horaria.csv             la hora a hora DESCRIPTIVA
  resumen_13casos.csv            por caso y agente: meses que domina cada uno,
                                 horizonte, la hora a hora de la comunidad y la
                                 comprobación contra el `Resumen`
  figuras/fig14_<caso>.*         la Fig. 14 nueva de cada caso, con sus CSV,
                                 su .mat y su .fuente.txt
  figuras/d72_mensual_13casos.*  la comunidad, mes a mes, en los trece casos
  procedencia.txt                qué se leyó y con qué código (sin hora)

LAS HUELLAS (I-1). Los PNG, los CSV y los .fuente.txt salen idénticos bit a
bit en cada regeneración y están en `HUELLAS.csv`. Los .mat llevan la hora
en que se escribieron y `procedencia.txt` lleva el commit: esos dos quedan
fuera de las huellas.

LA COMPROBACIÓN, EN VOZ ALTA. El total del horizonte de P2P y de C4, en la
comunidad y en cada institución, tiene que ser el de `Resumen` y `Por_agente`
a un peso (el almacén guarda float32: la suma difiere a lo sumo en 0,12 COP).
Si no lo es, el guion se detiene con `ValueError` y no escribe nada más.

Uso:
    .venv/Scripts/python.exe reformateo/documento/scripts/optimalidad_d72.py
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analysis.optimality import (COMUNIDAD, TOL_COP,  # noqa: E402
                                 analyze_hourly_dominance, tabla_horaria)
from core.almacen import lee  # noqa: E402

ENTREGA = RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
BASE = ENTREGA / "SALIDAS_SERVIDOR" / "matriz_reposo"
DESTINO = ENTREGA / "optimalidad_D72"
CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU"]
ORDEN = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]


def _rel(p: Path) -> str:
    """Ruta relativa al repositorio; absoluta si cae fuera (una prueba)."""
    q = Path(p).resolve()
    try:
        return str(q.relative_to(RAIZ)).replace(os.sep, "/")
    except ValueError:
        return str(q)


def _matriz(df: pd.DataFrame, col: str, nombres: list, T: int) -> np.ndarray:
    p = df.pivot(index="agente", columns="hora", values=col)
    p = p.reindex(index=nombres, columns=range(T))
    if p.isna().any().any():
        raise ValueError(f"{col}: la tabla del almacen tiene huecos")
    # float32 del almacen a float64 ANTES de sumar nada.
    return p.to_numpy(dtype=np.float64)


def _resultados(flujos: pd.DataFrame, papel: pd.DataFrame, nombres: list,
                T: int) -> list:
    """El mercado de cada hora, desde los flujos: decide actividad y GDR."""
    por_hora = {k: g for k, g in flujos.groupby("hora")}
    out = []
    for k in range(T):
        sids = [n for n, a in enumerate(nombres) if papel.at[a, k] == "vendedor"]
        bids = [n for n, a in enumerate(nombres)
                if papel.at[a, k] == "comprador"]
        g = por_hora.get(k)
        if g is None or float(g["kwh"].astype(np.float64).sum()) <= 1e-6:
            out.append(SimpleNamespace(P_star=None, seller_ids=sids,
                                       buyer_ids=bids))
            continue
        P = np.zeros((len(sids), len(bids)))
        for v, c, e in zip(g["vendedor"], g["comprador"], g["kwh"]):
            j, i = nombres.index(v), nombres.index(c)
            if j not in sids or i not in bids:
                raise ValueError(f"hora {k}: el flujo {v}->{c} no casa con "
                                 f"los papeles de la tabla de agentes")
            P[sids.index(j), bids.index(i)] += float(e)
        out.append(SimpleNamespace(P_star=P, seller_ids=sids, buyer_ids=bids))
    return out


def analiza_caso(caso: str):
    alm = BASE / caso / "almacen"
    esc = lee(alm, "m1", "escenarios")
    horas = lee(alm, "m1", "horas").sort_values("hora").reset_index(drop=True)
    agentes = lee(alm, "m1", "agentes")
    flujos = lee(alm, "m1", "flujos")
    T = len(horas)
    if list(horas["hora"]) != list(range(T)):
        raise ValueError(f"{caso}: la tabla de horas no es 0..{T - 1}")
    nombres = [n for n in ORDEN if n in set(agentes["agente"])]
    P = _matriz(esc[esc["escenario"] == "P2P"], "valor", nombres, T)
    C = _matriz(esc[esc["escenario"] == "C4"], "valor", nombres, T)
    D = _matriz(agentes, "demanda", nombres, T)
    G = _matriz(agentes, "generacion", nombres, T)
    papel = agentes.pivot(index="agente", columns="hora", values="papel")
    res = _resultados(flujos, papel, nombres, T)

    xl = BASE / caso / "outputs" / "resultados_comparacion.xlsx"
    resumen = pd.read_excel(xl, sheet_name="Resumen").set_index(
        "Escenario")["Ganancia_neta_COP"]
    por_agente = pd.read_excel(xl, sheet_name="Por_agente")
    ref = {"P2P": float(resumen["P2P"]), "C4": float(resumen["C4"])}

    s = analyze_hourly_dominance(
        p2p_horario=P, c4_horario=C, p2p_results=res, D=D, G_klim=G,
        month_labels=horas["mes"].astype(str).to_numpy(),
        agent_names=nombres, referencia_liquidacion=ref)

    # Cada institución: su horizonte es el de `Por_agente`, que rotula A1..AN
    # en el orden de los agentes de la corrida.
    if len(por_agente) != len(nombres):
        raise ValueError(f"{caso}: Por_agente tiene {len(por_agente)} filas "
                         f"y el almacen {len(nombres)} agentes")
    difs = {}
    for n, a in enumerate(nombres):
        fila = por_agente.iloc[n]
        if str(fila["Agente"]) != f"A{n + 1}":
            raise ValueError(f"{caso}: Por_agente fila {n} es "
                             f"{fila['Agente']!r}, no A{n + 1}")
        p, c, _ = s.mensual.total(a)
        for e, v in (("P2P", p), ("C4", c)):
            d = v - float(fila[e])
            if abs(d) > TOL_COP:
                raise ValueError(f"{caso} {a}: {e} del horizonte {v:,.2f} no "
                                 f"es el de Por_agente {float(fila[e]):,.2f}")
            difs[(a, e)] = d
    difs[(COMUNIDAD, "P2P")] = s.B_p2p_total - ref["P2P"]
    difs[(COMUNIDAD, "C4")] = s.B_c4_total - ref["C4"]
    return s, nombres, ref, difs


def figura_resumen(tablas: dict, carpeta: Path) -> Path:
    """La comunidad, P2P − C4 por mes, en los trece casos (millones de COP)."""
    casos = list(tablas)
    meses = list(dict.fromkeys(m for c in casos for m in tablas[c]["mes"]))
    Z = np.full((len(casos), len(meses)), np.nan)
    for r, c in enumerate(casos):
        t = tablas[c]
        for _, f in t.iterrows():
            Z[r, meses.index(f["mes"])] = f["delta_COP"] / 1e6
    vmax = float(np.nanmax(np.abs(Z)))
    fig, ax = plt.subplots(figsize=(11, 6.5))
    from matplotlib.colors import LinearSegmentedColormap
    from visualization.plots import COLORS_ESC
    cmap = LinearSegmentedColormap.from_list(
        "c4_p2p", [COLORS_ESC["C4"], "#FFFFFF", COLORS_ESC["P2P"]])
    im = ax.imshow(Z, aspect="auto", cmap=cmap, vmin=-vmax, vmax=vmax)
    ax.grid(visible=False)
    for r in range(Z.shape[0]):
        for k in range(Z.shape[1]):
            v = Z[r, k]
            ax.text(k, r, f"{v:+.2f}", ha="center", va="center", fontsize=7.5,
                    color="white" if abs(v) > 0.6 * vmax else "#222")
    ax.set_xticks(np.arange(len(meses)))
    ax.set_xticklabels(meses, fontsize=9)
    ax.set_yticks(np.arange(len(casos)))
    rot = []
    for c in casos:
        t = tablas[c]
        rot.append(f"{c}  ({t['delta_COP'].sum() / 1e6:+.2f}; "
                   f"{int((t['domina'] == 'P2P').sum())}/"
                   f"{int((t['domina'] == 'C4').sum())} meses)")
    ax.set_yticklabels(rot, fontsize=8.5)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("P2P − C4 de la comunidad (millones de COP)", fontsize=8)
    ax.set_title("P2P − C4 de la comunidad, mes a mes, en los trece casos "
                 "(D72; entre paréntesis: horizonte y meses que domina "
                 "P2P/C4)", fontsize=10, fontweight="bold")
    carpeta.mkdir(parents=True, exist_ok=True)
    png = carpeta / "d72_mensual_13casos.png"
    fig.savefig(png, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    largo = pd.concat([t.assign(caso=c) for c, t in tablas.items()],
                      ignore_index=True)[["caso", "mes", "B_P2P_COP",
                                          "B_C4_COP", "delta_COP", "domina"]]
    largo.to_csv(carpeta / "d72_mensual_13casos.csv", index=False,
                 encoding="utf-8")
    return png


def fuente(png: Path, rutas: list, nota: str = "") -> None:
    texto = ("Figura: " + png.stem + "\nArtefactos leidos:\n"
             + "".join(f"  - {r}\n" for r in rutas)
             + "Generada por: reformateo/documento/scripts/optimalidad_d72.py"
             + " (D72)\n" + (nota + "\n" if nota else ""))
    png.with_suffix("").with_name(png.stem + ".fuente.txt").write_text(
        texto, encoding="utf-8")


def _git() -> str:
    """El commit del código. Si git falla, falla el guion (M-5): la
    procedencia de un artefacto del canon no se escribe «desconocida»."""
    h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ,
                       capture_output=True, text=True, check=True)
    s = subprocess.run(["git", "status", "--porcelain", "--",
                        "analysis/optimality.py",
                        "reformateo/documento/scripts/optimalidad_d72.py",
                        "visualization/plots.py",
                        "visualization/matlab_export.py",
                        "core/almacen.py"],
                       cwd=RAIZ, capture_output=True, text=True, check=True)
    return h.stdout.strip() + (" con cambios sin commit en: "
                               + "; ".join(l[3:] for l in
                                           s.stdout.splitlines())
                               if s.stdout.strip() else "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--casos", default=",".join(CASOS))
    ap.add_argument("--destino", default=str(DESTINO))
    args = ap.parse_args()
    from visualization.plots import plot_optimality

    destino = Path(args.destino)
    figs = destino / "figuras"
    destino.mkdir(parents=True, exist_ok=True)
    casos = [c.strip() for c in args.casos.split(",") if c.strip()]

    filas, tablas_com = [], {}
    for caso in casos:
        s, nombres, ref, difs = analiza_caso(caso)
        mm = s.mensual
        mm.tabla().to_csv(destino / f"{caso}_mensual.csv", index=False,
                          encoding="utf-8")
        tabla_horaria(s).to_csv(destino / f"{caso}_horaria.csv", index=False,
                                encoding="utf-8")
        png = Path(plot_optimality(s, out_dir=str(figs), currency="COP",
                                   nombre=f"fig14_{caso}.png", estricto=True))
        # M-5: la figura no vale sin sus hermanos de datos.
        for suf in (".png", "__mensual.csv", "__resumen.csv",
                    "__horaria.csv", ".mat"):
            h = png.with_name(png.stem + suf)
            if not h.exists():
                raise FileNotFoundError(f"{caso}: falta {h.name}")
        alm = BASE / caso / "almacen" / "m1"
        fuente(png, [_rel(alm / t) for t in ("escenarios", "horas", "agentes",
                                            "flujos")]
               + [_rel(BASE / caso / "outputs" / "resultados_comparacion.xlsx")
                  + " (Resumen y Por_agente, solo la comprobacion)"])
        t = mm.tabla()
        tablas_com[caso] = t[t["agente"] == COMUNIDAD].reset_index(drop=True)
        r = mm.resumen()
        for _, f in r.iterrows():
            a = f["agente"]
            fila = {"caso": caso, **f.to_dict(),
                    "dif_P2P_vs_liquidacion_COP": difs[(a, "P2P")],
                    "dif_C4_vs_liquidacion_COP": difs[(a, "C4")]}
            if a == COMUNIDAD:
                fila.update({
                    "Resumen_P2P_COP": ref["P2P"], "Resumen_C4_COP": ref["C4"],
                    "horas": s.T_total, "horas_mercado": s.n_active,
                    "horas_P2P_dom": s.n_p2p_dom, "horas_C4_dom": s.n_c4_dom,
                    "horas_neutral": s.n_neutral,
                    "umbral_horario_COP": s.threshold_cop,
                    "delta_horas_mercado_COP": s.delta_total,
                    "delta_horas_sin_mercado_COP": s.delta_inactivas})
            filas.append(fila)
        c = mm.cuenta(COMUNIDAD)
        print(f"  {caso:<5} P2P-C4 {s.delta_horizonte:>15,.2f} COP  meses "
              f"P2P/C4/emp {c['P2P']}/{c['C4']}/{c['empate']}  horas "
              f"{s.n_p2p_dom}/{s.n_c4_dom}/{s.n_neutral}  dif. con Resumen "
              f"{difs[(COMUNIDAD, 'P2P')]:+.3f} / {difs[(COMUNIDAD, 'C4')]:+.3f}")

    pd.DataFrame(filas).to_csv(destino / "resumen_13casos.csv", index=False,
                               encoding="utf-8")
    png = figura_resumen(tablas_com, figs)
    fuente(png, [_rel(BASE / c / "almacen" / "m1" / "escenarios")
                 for c in casos])
    (destino / "procedencia.txt").write_text(
        "D72 · analisis de optimalidad del canon 2026-09-19, rehecho desde "
        "los almacenes\n"
        # I-1: sin la hora de generación. Este fichero lleva el commit y
        # queda fuera de las huellas, igual que los .mat (llevan la hora).
        f"Codigo: {_git()}\n"
        "Guion: reformateo/documento/scripts/optimalidad_d72.py\n"
        "Modulo: analysis/optimality.py (analyze_hourly_dominance, D72)\n"
        f"Casos: {', '.join(casos)}\n"
        "Lee: <caso>/almacen/m1/{escenarios,horas,agentes,flujos} y, solo "
        "para comprobar, <caso>/outputs/resultados_comparacion.xlsx\n"
        f"Comprobacion: P2P y C4 del horizonte, comunidad y cada institucion, "
        f"iguales a Resumen y Por_agente a {TOL_COP:.0f} COP\n",
        encoding="utf-8")
    print(f"  escrito en {_rel(destino)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
