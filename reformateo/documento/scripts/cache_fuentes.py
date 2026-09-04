"""
cache_fuentes.py — Censo de cobertura de las veintisiete fuentes crudas.
========================================================================
El capítulo 2 necesita saber, fuente por fuente, desde cuándo hasta cuándo
hay dato y qué fracción del horizonte cubre. Esa información no está en
ningún artefacto del canon —el canon guarda resultados, no diagnóstico de
adquisición— y hay que reconstruirla recorriendo los archivos.

El recorrido es deliberadamente barato: de cada archivo se leen solo las
columnas de fecha y de medida, nunca el archivo completo.

    python scripts/cache_fuentes.py

Salida: ``datos_cache/fuentes.csv``, una fila por fuente.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from data.xm_data_loader import (                      # noqa: E402
    AGENTS, COL_DATE, COL_DEMAND, COL_GEN,
    INVERTER_FOLDER, METER_FOLDER, T_END, T_START,
)
from data.preprocessing import (                       # noqa: E402
    DEMAND_METER_CONFIG, EMS_INVERTER_BACKFILL_CONFIG, EMS_INVERTER_CONFIG,
    PAPER_METER_DEMAND_CONFIG, RECONSTRUCTION_INVERTERS_CONFIG,
    _find_subdir,
)

CACHE = Path(__file__).resolve().parent.parent / "datos_cache"


def raiz_mte() -> Path:
    import os
    env = os.environ.get("MTE_ROOT")
    if env and Path(env).exists():
        return Path(env)
    for n in ("MedicionesMTE_v3", "MedicionesMTE"):
        if (RAIZ / n).exists():
            return RAIZ / n
    raise FileNotFoundError("no se encuentra MedicionesMTE")


def _resumir(carpeta: Path, columna: str, idx: pd.DatetimeIndex) -> dict:
    """Primera y última marca con dato, y cobertura sobre el horizonte."""
    partes = []
    for csv in sorted(carpeta.rglob("*.csv")):
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                d = pd.read_csv(csv, usecols=[COL_DATE, columna], encoding=enc)
                break
            except (UnicodeDecodeError, ValueError):
                d = None
        if d is None or d.empty:
            continue
        d[COL_DATE] = pd.to_datetime(d[COL_DATE], errors="coerce")
        d = d.dropna(subset=[COL_DATE])
        partes.append(d)
    if not partes:
        return {}

    d = pd.concat(partes, ignore_index=True)
    s = (d.set_index(COL_DATE)[columna]
         .groupby(level=0).mean()
         .resample("1h").mean()
         .reindex(idx))
    con_dato = int(s.notna().sum())
    diurno = s[(s.index.hour >= 6) & (s.index.hour <= 18)]
    return {
        "inicio": d[COL_DATE].min(),
        "fin": d[COL_DATE].max(),
        "n_archivos": len(partes),
        "horas_con_dato": con_dato,
        "cobertura_pct": 100.0 * con_dato / len(idx),
        "cobertura_diurna_pct": 100.0 * float(diurno.notna().mean()),
    }


def construir() -> Path:
    root = raiz_mte()
    idx = pd.date_range(T_START, T_END, freq="1h", inclusive="left")
    usados_m1 = {a: DEMAND_METER_CONFIG[a]["subfolder"] for a in AGENTS}
    usados_m3 = {a: PAPER_METER_DEMAND_CONFIG[a]["subfolder"] for a in AGENTS}

    filas = []
    for agente in AGENTS:
        adir = _find_subdir(root, agente)
        if adir is None:
            continue

        med_root = _find_subdir(adir, METER_FOLDER[agente])
        if med_root is not None:
            for sub in sorted(p for p in med_root.iterdir() if p.is_dir()):
                r = _resumir(sub, COL_DEMAND, idx)
                if not r:
                    continue
                papel = []
                if sub.name == usados_m1[agente]:
                    papel.append("M1")
                if sub.name == usados_m3[agente]:
                    papel.append("M3")
                filas.append({"institucion": agente, "clase": "medidor",
                              "fuente": sub.name,
                              "papel": "+".join(papel) or "no usado", **r})

        inv_root = _find_subdir(adir, INVERTER_FOLDER[agente])
        if inv_root is not None:
            for sub in sorted(p for p in inv_root.iterdir() if p.is_dir()):
                r = _resumir(sub, COL_GEN, idx)
                if not r:
                    continue
                # CAL-44: tres papeles, no dos. Los Fronius de Udenar
                # son referencia para extender el inversor designado y
                # sumandos de la reconstrucción net->bruta; ninguno de los
                # dos los mete en un cálculo por sí mismos.
                if sub.name == EMS_INVERTER_CONFIG[agente]:
                    papel = "EMS"
                else:
                    papeles = []
                    if sub.name == EMS_INVERTER_BACKFILL_CONFIG.get(agente):
                        papeles.append("referencia")
                    if sub.name in RECONSTRUCTION_INVERTERS_CONFIG.get(agente, []):
                        papeles.append("reconstrucción")
                    papel = "+".join(papeles) or "no usado"
                filas.append({"institucion": agente, "clase": "inversor",
                              "fuente": sub.name, "papel": papel, **r})
        print(f"  {agente}: {sum(1 for f in filas if f['institucion'] == agente)} fuentes")

    df = pd.DataFrame(filas)
    CACHE.mkdir(parents=True, exist_ok=True)
    destino = CACHE / "fuentes.csv"
    df.to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"\n  total de fuentes: {len(df)}"
          f"  ({int((df.clase == 'medidor').sum())} medidores, "
          f"{int((df.clase == 'inversor').sum())} inversores)")
    print(f"  -> {destino.name}")
    return destino


if __name__ == "__main__":
    construir()
