"""Por qué las horas cuantales dependen de los dos comercializadores (D71).

Punto C10 de la preparación antes de redactar (2026-09-27); H-105.

Con un solo comercializador las 216 horas cuantales de la matriz desaparecen
(H-97). Hipótesis: la fragilidad del reposo exige compradores con techos
distintos, y en esta comunidad eso solo ocurre porque Cesmag (CEDENAR) tiene
otro costo unitario que las cuatro de ASC. Se comprueba en los almacenes del
canon: en cada hora con mercado, si hay al menos dos compradores con techos
distintos y si Cesmag compra.

Salida: SALIDAS_SERVIDOR/cuantal_techos_2026-09-27/cuantal_techos.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
MATRIZ = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
          / "SALIDAS_SERVIDOR" / "matriz_reposo")
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "cuantal_techos_2026-09-27"
CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU"]
TOL = 1e-6                                          # COP/kWh
SIN_INTERCAMBIO = {"sin_mercado", "sin_ganancia"}


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    filas = []
    for c in CASOS:
        alm = MATRIZ / c / "almacen" / "m1"
        h = pd.read_parquet(alm / "horas")
        a = pd.read_parquet(alm / "agentes")
        if not np.isfinite(a["techo"].to_numpy()).all():
            raise ValueError(f"{c}: techo no finito")
        comp = a[a["papel"].astype(str) == "comprador"]
        g = comp.groupby("hora").agg(
            techo_min=("techo", "min"), techo_max=("techo", "max"),
            compradores=("agente", "size"),
            cesmag_compra=("agente", lambda s: "Cesmag" in set(s)))
        hm = (h[h["regimen"].notna() & ~h["regimen"].isin(SIN_INTERCAMBIO)]
              .set_index("hora")[["regimen"]].join(g, how="left"))
        if hm["compradores"].isna().any():
            raise ValueError(f"{c}: horas con mercado sin compradores en agentes")
        hm["techos_distintos"] = (hm["techo_max"] - hm["techo_min"]) > TOL
        hm["cuantal"] = hm["regimen"] == "cuantal"
        for es_c, sub in hm.groupby("cuantal"):
            filas.append(dict(
                caso=c, cuantal=bool(es_c), horas=len(sub),
                techos_distintos=int(sub["techos_distintos"].sum()),
                cesmag_compra=int(sub["cesmag_compra"].astype(bool).sum())))
    df = pd.DataFrame(filas)
    df.to_csv(SALIDA / "cuantal_techos.csv", index=False)
    t = df.groupby("cuantal")[["horas", "techos_distintos", "cesmag_compra"]].sum()
    t["pct_techos_distintos"] = 100 * t["techos_distintos"] / t["horas"]
    print(t.round(1).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
