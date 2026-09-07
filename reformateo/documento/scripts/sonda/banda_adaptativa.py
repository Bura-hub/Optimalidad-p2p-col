"""
La banda adaptativa, y la condición de existencia del mercado (CAL-47).

Mide la banda cuando las dos cotas dejan de ser constantes y pasan a ser lo
que cada parte obtiene si no negocia, **agente por agente y hora por hora**:

    techo_i(k)  el costo unitario de esa institución en ese mes
    piso_j(k)   la permuta mientras la inyección acumulada del mes no supere
                al retiro, y el precio de bolsa de esa hora a partir de ahí

Y responde de paso la pregunta que decide si el mecanismo puede existir:
**qué pasa si la energía intercambiada entre pares paga cargos de red.**

No corre el juego. La banda y el excedente no dependen del precio, por la
identidad del excedente, de modo que todo lo que sigue es aritmética sobre
las series y no requiere resolver ningún equilibrio.

Uso:
    python banda_adaptativa.py
    python banda_adaptativa.py --cobertura m3
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))

from core.opciones_externas import (  # noqa: E402
    banda_vacia, piso_comunitario, piso_por_vendedor, resumen, tramo_permuta)

AGENTES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]


def series(cob: str):
    from data.preprocessing import PAPER_METER_DEMAND_CONFIG
    from data.xm_data_loader import MTEDataLoader

    cfg = PAPER_METER_DEMAND_CONFIG if cob == "m3" else None
    loader = MTEDataLoader(os.environ.get("MTE_ROOT",
                                          str(RAIZ / "MedicionesMTE_v3")),
                           demand_config=cfg)
    return loader.load(verbose=False)


def tarifa(idx) -> pd.DataFrame:
    t = pd.read_csv(RAIZ / "data" / "tarifas_cedenar_mensual.csv", comment="#")
    t = t[(t.nivel_tension == 2) & (t.categoria == "oficial")
          & (t.propiedad == "cedenar")]
    return t.set_index("mes")


def bolsa_horaria(idx) -> np.ndarray:
    b = pd.read_csv(RAIZ / "data" / "precios_bolsa_xm_api.csv")
    b["ts"] = pd.to_datetime(b["Fecha"]) + pd.to_timedelta(b["Hora"] - 1, "h")
    llaves = pd.DatetimeIndex(idx)
    if llaves.tz is not None:
        llaves = llaves.tz_localize(None)
    s = b.set_index("ts")["Precio_COP_kWh"].reindex(llaves)
    assert not s.isna().any(), "faltan horas de bolsa"
    return s.to_numpy(float)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cobertura", default="m1", choices=["m1", "m3"])
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    D, G, idx = series(args.cobertura)
    N, T = D.shape
    mes = pd.Series(idx).dt.strftime("%Y-%m").to_numpy()
    t = tarifa(idx)
    cu_k = t.loc[mes, "CU_aplicado"].to_numpy(float)
    cvm_k = t.loc[mes, "Cvm"].to_numpy(float)
    peaje_k = t.loc[mes, ["Tm", "Dnm", "PR", "Rm"]].sum(axis=1).to_numpy(float)
    bolsa = bolsa_horaria(idx)

    cu = np.tile(cu_k, (N, 1))
    cvm = np.tile(cvm_k, (N, 1))

    perm = tramo_permuta(G, D, mes)
    piso_nk = piso_por_vendedor(cu, cvm, bolsa, perm)
    piso_k = piso_comunitario(piso_nk, G, D)
    techo_k = cu_k

    print(f"La banda adaptativa · cobertura {args.cobertura.upper()} · "
          f"{T} horas")
    print("=" * 74)

    print("\n1 · En qué tramo se liquida el excedente de cada institución")
    r = resumen(perm, G, D, AGENTES)
    print(f"  {'institución':12s} {'excedente kWh':>14s} {'permuta':>9s} "
          f"{'a bolsa':>9s}")
    for nombre in AGENTES:
        frac, tot = r[nombre]
        print(f"  {nombre:12s} {tot:14.1f} {100*frac:8.1f} % "
              f"{100*(1-frac):8.1f} %")
    frac, tot = r["_comunidad"]
    print(f"  {'COMUNIDAD':12s} {tot:14.1f} {100*frac:8.1f} % "
          f"{100*(1-frac):8.1f} %")

    print("\n2 · La banda que resulta, hora a hora")
    ancho = techo_k - piso_k
    excedente = np.maximum(G - D, 0.0).sum(axis=0)
    activa = excedente > 1e-9
    vacia = banda_vacia(techo_k, piso_k)
    print(f"  ancho medio ponderado por excedente: "
          f"{np.average(ancho[activa], weights=excedente[activa]):7.2f} COP/kWh")
    print(f"  recorrido del ancho: {ancho[activa].min():7.2f} a "
          f"{ancho[activa].max():7.2f}")
    print(f"  horas con la banda vacía: {int(vacia.sum())} de {T} "
          f"({100*vacia.mean():.2f} %)")
    print(f"  de ellas con excedente que colocar: "
          f"{int((vacia & activa).sum())}")

    print("\n3 · La condición de existencia: ¿y si el intercambio paga red?")
    techo_sin = techo_k - peaje_k
    ancho_sin = techo_sin - piso_k
    vacia_sin = banda_vacia(techo_sin, piso_k)
    print(f"  peaje medio (transmisión, distribución, pérdidas y "
          f"restricciones): {peaje_k.mean():7.2f} COP/kWh")
    print(f"  techo sin exención: {techo_sin.mean():7.2f} de media")
    print(f"  ancho medio: {np.average(ancho_sin[activa], weights=excedente[activa]):7.2f}"
          f"  (era {np.average(ancho[activa], weights=excedente[activa]):7.2f})")
    print(f"  **horas con la banda VACÍA: {int(vacia_sin.sum())} de {T} "
          f"({100*vacia_sin.mean():.1f} %)**")
    e_con = float((ancho[activa] * excedente[activa]).sum())
    e_sin = float((np.maximum(ancho_sin, 0.0)[activa]
                   * excedente[activa]).sum())
    print(f"  excedente máximo colocable: {e_con:14,.0f} COP con exención")
    print(f"  {'':29s}{e_sin:14,.0f} COP sin ella "
          f"({100*(e_sin-e_con)/e_con:+.1f} %)")

    print("\n4 · El mismo corte, separando los dos regímenes del vendedor")
    # Una hora se clasifica por dónde está la mayor parte de SU excedente,
    # no por si algún agente cruzó: con cinco agentes casi siempre hay uno
    # de cada clase, y exigir unanimidad no seleccionaría ninguna hora.
    exc_nk = np.maximum(G - D, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        frac_perm = (exc_nk * perm).sum(axis=0) / exc_nk.sum(axis=0)
    frac_perm = np.nan_to_num(frac_perm)
    for nombre, sel in [("permuta", (frac_perm > 0.5) & activa),
                        ("bolsa", (frac_perm <= 0.5) & activa)]:
        if not sel.any():
            print(f"  {nombre:12s} sin horas")
            continue
        print(f"  {nombre:12s} {int(sel.sum()):5d} horas · "
              f"ancho con exención {np.average(ancho[sel], weights=excedente[sel]):7.2f} · "
              f"sin ella {np.average(ancho_sin[sel], weights=excedente[sel]):7.2f} · "
              f"vacía sin ella {100*vacia_sin[sel].mean():5.1f} %")


if __name__ == "__main__":
    main()
