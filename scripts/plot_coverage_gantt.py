"""
Genera un Gantt de cobertura temporal para los 27 CSV de MTE
(20 medidores + 7 inversores).

Cada fila: una fuente. Eje X: tiempo Jul 1 -> Feb 1 (resolucion diaria).
Verde: datos validos. Gris: sin cobertura. Rojo claro: stale (sensor frozen).

Marca con * la fuente seleccionada en config (DEMAND_METER_CONFIG /
EMS_INVERTER_CONFIG).

Salida: graficas/data_coverage_gantt.png
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from data.xm_data_loader import (
    _read_one, AGENTS, METER_FOLDER, INVERTER_FOLDER,
    COL_DEMAND, COL_GEN, T_START, T_END,
)
from data.preprocessing import (
    DEMAND_METER_CONFIG, EMS_INVERTER_CONFIG,
    _find_subdir,
)


def load_daily_mask(folder: Path, col: str, divide_by: float,
                    days_idx: pd.DatetimeIndex):
    """
    Devuelve (valid_mask, stale_mask) por dia para una SUBCARPETA.
    Concatena todos los CSVs (v3 tiene multiple particiones temporales).
    """
    parts = []
    for path in sorted(folder.rglob("*.csv")):
        s = _read_one(path, col)
        if s is not None and len(s) > 0:
            parts.append(s)
    if not parts:
        return (np.zeros(len(days_idx), dtype=bool),
                np.zeros(len(days_idx), dtype=bool))
    s = pd.concat(parts, axis=1).sum(axis=1, min_count=1)
    s = s / divide_by
    # Filtrar al horizonte de days_idx
    s = s.loc[days_idx[0]:days_idx[-1] + pd.Timedelta(days=1)]
    if len(s) == 0:
        return (np.zeros(len(days_idx), dtype=bool),
                np.zeros(len(days_idx), dtype=bool))

    # 1h resample para detectar stale
    s_1h = s.resample("1h").mean()
    valid = s_1h.notna()

    # Stale: runs >24h de valores casi iguales
    diffs = np.abs(s_1h.diff().fillna(1.0).values)
    is_stale_h = diffs < 1e-3
    # Marcar como stale si run actual >= 24h
    stale_h = np.zeros(len(s_1h), dtype=bool)
    cur = 0
    for i, x in enumerate(is_stale_h):
        if x:
            cur += 1
        else:
            cur = 0
        if cur >= 24:
            stale_h[i] = True
            # Backfill todo el run
            for j in range(max(0, i - cur + 1), i + 1):
                stale_h[j] = True

    # Agregar a granularidad diaria
    s_1h.index = pd.to_datetime(s_1h.index)
    daily_valid = valid.groupby(s_1h.index.normalize()).any().reindex(days_idx, fill_value=False)
    daily_stale = pd.Series(stale_h, index=s_1h.index).groupby(s_1h.index.normalize()).any().reindex(days_idx, fill_value=False)

    return daily_valid.values, daily_stale.values


def main():
    import os as _os
    repo = Path(__file__).resolve().parents[1]
    root = Path(_os.environ.get("MTE_ROOT", str(repo / "MedicionesMTE_v3")))
    ts = _os.environ.get("MTE_T_START", T_START)
    te = _os.environ.get("MTE_T_END", T_END)
    print(f"Gantt sobre {root} | {ts} -> {te}")

    # Eje diario
    days = pd.date_range(ts, te, freq="1D", inclusive="left")

    rows = []  # (label, valid_mask, stale_mask, kind, is_selected)

    for agent in AGENTS:
        adir = _find_subdir(root, agent)
        if adir is None:
            continue

        # Medidores
        meter_root = _find_subdir(adir, METER_FOLDER[agent])
        selected_meter = DEMAND_METER_CONFIG.get(agent, {}).get("subfolder", "")
        if meter_root:
            for sub in sorted(meter_root.iterdir()):
                if not sub.is_dir():
                    continue
                csvs = list(sub.glob("*.csv"))
                if not csvs:
                    continue
                valid, stale = load_daily_mask(sub, COL_DEMAND, 1.0, days)
                short = sub.name.replace(" - electricMeter", "").replace(" - Alvernia", "")
                short = short.replace(" - UCC", "").replace(" - HUDN", "").replace(" - Cesmag", "")
                short = short.replace("Bloque Sur - ", "")
                is_sel = (sub.name == selected_meter)
                rows.append((
                    f"{agent} | M | {short}" + (" *" if is_sel else ""),
                    valid, stale, "meter", is_sel,
                ))

        # Inversores
        inv_root = _find_subdir(adir, INVERTER_FOLDER[agent])
        selected_inv = EMS_INVERTER_CONFIG.get(agent, "")
        if inv_root:
            for sub in sorted(inv_root.iterdir()):
                if not sub.is_dir():
                    continue
                csvs = list(sub.glob("*.csv"))
                if not csvs:
                    continue
                valid, stale = load_daily_mask(sub, COL_GEN, 1000.0, days)
                short = sub.name.replace(" - inverter", "")
                short = short.replace(" - Alvernia", "").replace(" - UCC", "")
                short = short.replace(" - HUDN", "").replace(" - Cesmag", "")
                short = short.replace(" - Udenar", "")
                is_sel = (sub.name == selected_inv)
                rows.append((
                    f"{agent} | I | {short}" + (" *" if is_sel else ""),
                    valid, stale, "inverter", is_sel,
                ))

    n = len(rows)
    fig, ax = plt.subplots(figsize=(13, max(6, 0.32 * n)))

    bar_h = 0.8
    for i, (label, valid, stale, kind, is_sel) in enumerate(rows):
        y = n - 1 - i  # rows top-down
        # Sin datos: gris
        ax.barh(y, len(days), left=days[0], height=bar_h,
                color="#EEEEEE", edgecolor="none", align="center")
        # Validos: verde / azul claro segun kind
        valid_color = "#3DAA6F" if kind == "meter" else "#3D7DAA"
        # Trazar como bloques contiguos
        i_start = None
        for j, v in enumerate(np.r_[valid, [False]]):
            if v and i_start is None:
                i_start = j
            elif not v and i_start is not None:
                ax.barh(y, days[j - 1] - days[i_start] + pd.Timedelta(days=1),
                        left=days[i_start], height=bar_h,
                        color=valid_color, edgecolor="none", align="center")
                i_start = None
        # Stale: rojo claro encima
        i_start = None
        for j, sv in enumerate(np.r_[stale, [False]]):
            if sv and i_start is None:
                i_start = j
            elif not sv and i_start is not None:
                ax.barh(y, days[j - 1] - days[i_start] + pd.Timedelta(days=1),
                        left=days[i_start], height=bar_h * 0.7,
                        color="#E37B6F", edgecolor="none", align="center", alpha=0.85)
                i_start = None

    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in reversed(rows)], fontsize=8)
    ax.set_xlim(days[0], days[-1])
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")
    ax.set_xlabel("Fecha")
    ax.set_title("Cobertura temporal de las 27 fuentes MTE\n"
                 "(* = fuente seleccionada en config | M = medidor | I = inversor)",
                 fontsize=11, fontweight="bold")
    ax.grid(True, axis="x", alpha=0.3)

    # Leyenda
    handles = [
        mpatches.Patch(color="#3DAA6F", label="Medidor: dato valido"),
        mpatches.Patch(color="#3D7DAA", label="Inversor: dato valido"),
        mpatches.Patch(color="#E37B6F", label="Stale (sensor frozen >24h)"),
        mpatches.Patch(color="#EEEEEE", label="Sin cobertura"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=8, framealpha=0.95)

    # Separadores entre instituciones
    cumulative = 0
    boundary_ys = []
    for agent in AGENTS:
        n_agent = sum(1 for r in rows if r[0].startswith(agent + " "))
        cumulative += n_agent
        boundary_ys.append(cumulative)
    for b in boundary_ys[:-1]:
        ax.axhline(n - b - 0.5, color="black", linewidth=0.5, alpha=0.4)

    plt.tight_layout()
    out = repo / "graficas" / "data_coverage_gantt.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"OK -> {out}")


if __name__ == "__main__":
    main()
