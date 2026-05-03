"""
scenarios/_c2_cxc.py — CAL-23 Cargo por Confiabilidad (CXC) opt-in para C2
============================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 3.1-3.3

Helper para cargar el componente CXC mensual desde
`data/cxc_costs.csv` y construir la matriz `(N, T)` consumida por
`run_c2_bilateral` cuando `cxc_component` no es None.

Diseno opt-in: el modulo NO se integra al flujo principal de
`main_simulation.py`. Llamarlo explicitamente desde una sensibilidad
o desde un escenario derivado.

Decision regulatoria (ADR-0023): default `cxc_alpha = 0.0` (cota
conservadora, usuario no-regulado sigue pagando CXC bajo PPA).

Referencia: docs/adr/0023-cal23-c2-cxc-cargo-confiabilidad.md
            data/cxc_costs.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

CSV_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "cxc_costs.csv"


def load_cxc_monthly(csv_path: str | Path | None = None) -> pd.DataFrame:
    """Lee `data/cxc_costs.csv` y devuelve DataFrame indexado por `mes`."""
    path = Path(csv_path) if csv_path else CSV_DEFAULT_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontro {path}. CXC opt-in requiere CSV mensual; "
            f"si no quiere usar CXC pase `cxc_component=None` (default)."
        )
    df = pd.read_csv(path, encoding="utf-8-sig",
                      comment="#", skip_blank_lines=True)
    if "mes" not in df.columns or "cxc_cop_kwh" not in df.columns:
        raise ValueError(
            f"CSV {path} debe tener columnas `mes` y `cxc_cop_kwh`."
        )
    df["mes"] = df["mes"].astype(str)
    df = df.dropna(subset=["cxc_cop_kwh"]).set_index("mes").sort_index()
    return df


def cxc_per_agent_hourly(agent_names: list[str],
                           hour_index: pd.DatetimeIndex,
                           csv_path: str | Path | None = None,
                           ) -> np.ndarray:
    """
    Construye la matriz (N, T) con el componente CXC para cada agente y hora.

    CAL-23: el CXC es uniforme por mes (no varia por agente, a diferencia
    del Cvm). Si un mes esta ausente del CSV se usa NaN; el caller decide.

    Devuelve: np.ndarray shape (N, T) en COP/kWh.
    """
    df = load_cxc_monthly(csv_path)
    N, T = len(agent_names), len(hour_index)
    out = np.full((N, T), np.nan, dtype=float)
    months = hour_index.to_period("M").astype(str).to_numpy()
    for n in range(N):
        for t in range(T):
            mes = months[t]
            if mes in df.index:
                out[n, t] = float(df.loc[mes, "cxc_cop_kwh"])
    return out
