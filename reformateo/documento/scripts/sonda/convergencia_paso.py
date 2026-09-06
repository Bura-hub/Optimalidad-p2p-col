# -*- coding: utf-8 -*-
"""
convergencia_paso.py — Cuánto sobrestima el paso horario, y dónde para.
========================================================================
El autoconsumo es el mínimo entre generación y demanda, y el mínimo de dos
promedios es mayor o igual que el promedio de los mínimos. Promediar la
hora antes de tomar el mínimo lo sobrestima, y H-28 acotó ese sesgo **por
abajo** con la sonda de quince minutos: 1,53 % y 2,67 %. Lo que falta es la
cota por arriba, es decir, la asíntota.

Este barrido la calcula recorriendo el mismo dato a ocho ventanas de
promedio, de una hora a dos minutos, que es la resolución nativa.

Tres decisiones de método, y las tres importan:

1. **No pasa por la limpieza.** La cascada de `_clean` está escrita en
   *conteos de pasos* y no en duraciones: «huecos de hasta 3 h» son en
   realidad tres pasos, que a dos minutos serían seis minutos. Aplicarla
   mezclaría el sesgo del promedio con un cambio de criterio de imputación.
   Aquí se mide sobre el dato reconstruido y sin tratar.

2. **Solo horas con cobertura nativa completa.** Se exige que las treinta
   ranuras de la hora estén presentes en la demanda y en la generación de
   **las cinco** instituciones a la vez. Sin esa restricción, una ventana
   fina «pierde» energía que la hora sí recoge, y el resultado confundiría
   el sesgo del promedio con la cobertura del dato.

3. **No corre el modelo.** El autoconsumo y el lado corto son aritmética
   sobre las matrices; el juego no interviene.

    python scripts/sonda/convergencia_paso.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))

from data.preprocessing import (                       # noqa: E402
    DEMAND_METER_CONFIG,
    EMS_INVERTER_BACKFILL_CONFIG,
    EMS_INVERTER_CONFIG,
    PAPER_METER_DEMAND_CONFIG,
    RECONSTRUCTION_INVERTERS_CONFIG,
    _find_subdir,
    _read_ems_generation,
    _read_single_meter,
    _sum_inverter_reconstruction,
)
from data.xm_data_loader import (                      # noqa: E402
    AGENTS, COL_DEMAND, INVERTER_FOLDER, METER_FOLDER, T_END, T_START,
)

SALIDAS = Path(__file__).resolve().parent / "salidas"
CACHE = Path(__file__).resolve().parents[2] / "datos_cache" / "nativo_horizonte"

# Las ventanas de promedio, en minutos. La de 60 es la del canon y la de 2
# es la nativa; las intermedias dibujan la curva.
PASOS_MIN = [60, 30, 20, 15, 12, 10, 6, 4, 2]


def raiz_mte() -> Path:
    env = os.environ.get("MTE_ROOT")
    if env and Path(env).exists():
        return Path(env)
    for nombre in ("MedicionesMTE_v3", "MedicionesMTE"):
        if (RAIZ / nombre).exists():
            return RAIZ / nombre
    raise FileNotFoundError("No se encuentra MedicionesMTE; defina MTE_ROOT.")


def construir_nativo(cobertura: str) -> pd.DataFrame:
    """D y G de las cinco instituciones a paso nativo, sin limpiar."""
    root = raiz_mte()
    idx = pd.date_range(T_START, T_END, freq="2min", inclusive="left")
    d_cfg = DEMAND_METER_CONFIG if cobertura == "m1" else PAPER_METER_DEMAND_CONFIG
    print(f"\n[{cobertura.upper()}] {len(idx):,} ranuras de dos minutos")

    cols = {}
    for agente in AGENTS:
        t0 = time.time()
        adir = _find_subdir(root, agente)
        cfg = d_cfg.get(agente, {})
        tipo = cfg.get("kind", "gross")

        meter_root = _find_subdir(adir, METER_FOLDER[agente])
        mdir = _find_subdir(meter_root, cfg["subfolder"]) if meter_root else None
        D_raw = (_read_single_meter(mdir, COL_DEMAND, idx, divide_by=1.0)
                 if mdir is not None else pd.Series(np.nan, index=idx))
        if float(cfg.get("scale", 1.0)) != 1.0:
            D_raw = D_raw * float(cfg["scale"])

        inv_root = _find_subdir(adir, INVERTER_FOLDER[agente])
        G_ems = (_read_ems_generation(
                     inv_root, EMS_INVERTER_CONFIG[agente],
                     EMS_INVERTER_BACKFILL_CONFIG.get(agente), idx,
                     etiqueta=agente, verbose=False)
                 if inv_root is not None else pd.Series(0.0, index=idx))

        if tipo in ("net", "net_partial"):
            G_recon = _sum_inverter_reconstruction(
                adir, RECONSTRUCTION_INVERTERS_CONFIG.get(agente, []), idx)
            # Sin `fillna`: si falta un insumo, la ranura queda ausente y la
            # restriccion de cobertura la excluye. El pipeline rellena con
            # cero, pero aqui eso falsearia el mínimo.
            D = (D_raw + G_recon.fillna(0.0)).clip(lower=0.0)
            presente_D = D_raw.notna() & G_recon.notna()
        else:
            D = D_raw.clip(lower=0.0)
            presente_D = D_raw.notna()

        cols[f"{agente}__D"] = D
        cols[f"{agente}__G"] = G_ems
        cols[f"{agente}__ok"] = presente_D & G_ems.notna()
        print(f"  {agente:8s} {tipo:12s} cobertura nativa "
              f"{100 * cols[f'{agente}__ok'].mean():5.2f} %   "
              f"[{time.time() - t0:4.0f} s]", flush=True)

    return pd.DataFrame(cols, index=idx)


def horas_completas(d: pd.DataFrame) -> pd.Series:
    """Las horas de reloj con las 30 ranuras presentes en las cinco series."""
    ok = pd.concat([d[f"{a}__ok"] for a in AGENTS], axis=1).all(axis=1)
    por_hora = ok.groupby(ok.index.floor("h")).sum()
    return por_hora == 30


def barrido(d: pd.DataFrame, buenas: pd.Series) -> pd.DataFrame:
    """Autoconsumo y lado corto de la comunidad a cada ventana de promedio."""
    dentro = d.index.floor("h").isin(buenas[buenas].index)
    d = d[dentro]
    filas = []
    for minutos in PASOS_MIN:
        dt = minutos / 60.0
        clave = d.index.floor(f"{minutos}min")
        auto_com = 0.0
        auto_por_inst = {}
        exc = pd.Series(0.0, index=sorted(set(clave)))
        dfc = pd.Series(0.0, index=exc.index)
        for a in AGENTS:
            G = d[f"{a}__G"].groupby(clave).mean().clip(lower=0.0)
            D = d[f"{a}__D"].groupby(clave).mean().clip(lower=0.0)
            auto = float(np.minimum(G, D).sum()) * dt
            auto_por_inst[a] = auto
            auto_com += auto
            exc = exc.add((G - D).clip(lower=0.0), fill_value=0.0)
            dfc = dfc.add((D - G).clip(lower=0.0), fill_value=0.0)
        lado_corto = float(np.minimum(exc, dfc).sum()) * dt
        fila = {"paso_min": minutos, "autoconsumo_kWh": auto_com,
                "lado_corto_kWh": lado_corto, "bloques": len(exc)}
        fila.update({f"auto_{a}": v for a, v in auto_por_inst.items()})
        filas.append(fila)
    return pd.DataFrame(filas)


def main() -> int:
    SALIDAS.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    todo = []
    for cobertura in ("m1", "m3"):
        pkl = CACHE / f"nativo_{cobertura}.parquet"
        if pkl.exists():
            d = pd.read_parquet(pkl)
            print(f"\n[{cobertura.upper()}] desde caché: {len(d):,} ranuras")
        else:
            d = construir_nativo(cobertura)
            d.to_parquet(pkl)
        buenas = horas_completas(d)
        n_h = len(buenas)
        print(f"  horas con las cinco series completas: {int(buenas.sum()):,} "
              f"de {n_h:,}  ({100 * buenas.mean():.1f} %)")
        b = barrido(d, buenas)
        b.insert(0, "frontera", cobertura.upper())
        b["horas_base"] = int(buenas.sum())
        todo.append(b)

    t = pd.concat(todo, ignore_index=True)
    # Todo relativo al límite nativo, que es la mejor aproximación al valor
    # verdadero que el dato permite.
    for f in ("M1", "M3"):
        m = t.frontera == f
        for col in ("autoconsumo_kWh", "lado_corto_kWh"):
            lim = float(t.loc[m & (t.paso_min == 2), col].iloc[0])
            t.loc[m, col.replace("_kWh", "_vs_nativo_pct")] = \
                100.0 * (t.loc[m, col] / lim - 1.0)

    pd.set_option("display.width", 220)
    print("\n=== Autoconsumo y lado corto de la comunidad, por ventana ===")
    print(t[["frontera", "paso_min", "horas_base", "autoconsumo_kWh",
             "autoconsumo_vs_nativo_pct", "lado_corto_kWh",
             "lado_corto_vs_nativo_pct"]].round(2).to_string(index=False))

    print("\n=== La cota que buscabamos ===")
    for f in ("M1", "M3"):
        m = t.frontera == f
        h = float(t.loc[m & (t.paso_min == 60), "autoconsumo_vs_nativo_pct"].iloc[0])
        q = float(t.loc[m & (t.paso_min == 15), "autoconsumo_vs_nativo_pct"].iloc[0])
        lc = float(t.loc[m & (t.paso_min == 60), "lado_corto_vs_nativo_pct"].iloc[0])
        print(f"  {f}: la hora sobrestima el autoconsumo en {h:+.2f} % frente "
              f"al nativo (el cuarto de hora, {q:+.2f} %); "
              f"y subestima el lado corto en {lc:+.2f} %")

    t.to_csv(SALIDAS / "convergencia_paso.csv", index=False,
             encoding="utf-8-sig")
    print(f"\nescrito en {SALIDAS / 'convergencia_paso.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
