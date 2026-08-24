# -*- coding: utf-8 -*-
"""
cache_reactiva.py — energía reactiva hora a hora, por institución y frontera
===========================================================================

Documento de proceso · Capítulo 2 · Actividad 1.0

Recorre los diez medidores que el modelo emplea, uno por institución en
cada frontera, y deja la potencia activa y la reactiva agregadas a la hora
sobre el horizonte del estudio.

**Por qué a la hora y no a la muestra.** La regla de la CREG compara la
energía reactiva contra el cincuenta por ciento de la activa *en cada
periodo horario*. Contar muestras de dos minutos por encima del umbral
responde a otra pregunta y da un número distinto, más alto, porque los
instantes de baja carga pesan igual que los de carga alta. La primera
medición de esta sesión se hizo así y hubo que rehacerla.

Salida: figuras/cache_reactiva_horaria.csv
    ts · institucion · cobertura · P_kW · Q_kvar · n_muestras

Uso:
    python scripts/cache_reactiva.py
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
MTE = Path(os.environ.get("MTE_ROOT", RAIZ / "MedicionesMTE_v3"))
SALIDA = Path(__file__).resolve().parents[1] / "figuras"

AGENTES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
FRONTERA = {"Medidor 1": "m1", "Medidor 3": "m3"}
T_INI, T_FIN = "2025-04-04", "2025-12-16 23:59"

COLS = ["date", "totalActivePower", "totalReactivePower"]


def _ficheros(institucion: str, medidor: str) -> list[str]:
    """Los CSV de un medidor concreto, sea cual sea la carpeta intermedia."""
    patron = str(MTE / institucion / "*" / "*" / "*.csv")
    return [f for f in glob.glob(patron)
            if medidor in os.path.basename(os.path.dirname(f))]


def construir() -> pd.DataFrame:
    filas = []
    for inst in AGENTES:
        for medidor, cob in FRONTERA.items():
            fs = _ficheros(inst, medidor)
            if not fs:
                print(f"  · {inst} {medidor}: sin ficheros")
                continue
            d = pd.concat([pd.read_csv(f, usecols=COLS) for f in fs],
                          ignore_index=True)
            d["ts"] = pd.to_datetime(d["date"], errors="coerce")
            d = d.dropna(subset=["ts"]).set_index("ts").sort_index()
            d = d.loc[T_INI:T_FIN]
            if d.empty:
                print(f"  · {inst} {medidor}: sin dato en el horizonte")
                continue
            h = d.resample("1h").agg(
                P_kW=("totalActivePower", "mean"),
                Q_kvar=("totalReactivePower", "mean"),
                n_muestras=("totalActivePower", "count"),
            ).dropna(subset=["P_kW", "Q_kvar"])
            h = h[h["n_muestras"] > 0].reset_index()
            h["institucion"] = inst
            h["cobertura"] = cob
            filas.append(h)
            print(f"  · {inst:8s} {medidor} ({cob}): {len(h):5d} h")
    if not filas:
        sys.exit("no se recuperó ninguna serie")
    return pd.concat(filas, ignore_index=True)


def main() -> None:
    print(f"Recorriendo {MTE}")
    if not MTE.is_dir():
        sys.exit(f"no existe {MTE}")
    d = construir()
    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / "cache_reactiva_horaria.csv"
    d.to_csv(destino, index=False, encoding="utf-8")
    print(f"\n{len(d):,} filas -> {destino}".replace(",", "."))

    # Comprobacion inmediata, para no arrastrar un cache mudo.
    P = d["P_kW"].clip(lower=0)
    con = P > 0.5
    exceso = con & (d["Q_kvar"].abs() > 0.5 * P)
    print(f"horas con consumo: {int(con.sum()):,}".replace(",", "."))
    print(f"de ellas, en exceso: {int(exceso.sum()):,} "
          f"({100 * exceso.sum() / con.sum():.1f} %)".replace(",", "."))


if __name__ == "__main__":
    main()
