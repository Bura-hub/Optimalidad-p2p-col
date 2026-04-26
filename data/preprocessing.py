"""
data/preprocessing.py — Preprocesamiento MTE (Actividad 3.1)
=============================================================
Capa semántica que decide *qué punto físico* se mide en cada institución
y garantiza que la demanda entregada al EMS sea **no-negativa por
construcción**. Corre antes del resto del pipeline.

Pipeline ejecutado en ``build_demand_generation()``
---------------------------------------------------
1. Construye eje horario canónico ``idx`` (T_START → T_END, freq=1h).
2. Para cada institución (orden fijo):
   a. Localiza la subcarpeta del medidor de demanda y del inversor EMS.
   b. Lee el medidor (concatena CSVs particionados, deduplica
      timestamps, resamplea a 1h, reindexa).
   c. Lee el inversor EMS (acPower/1000, clip(0), reindexa).
   d. Resuelve no-negatividad según el tipo declarado en
      DEMAND_METER_CONFIG[agent]['kind']:
        * net         → D = max(0, D_net + Σ_3-inversores)
        * net_partial → D = max(0, D_net + 1-inversor)
        * gross       → D = max(0, D_raw)
   e. Aplica _clean() (outliers + interpolación de gaps ≤24h).
3. Apila en arrays (5, T) float64.
4. Sanity check: (D>=0).all() y (G>=0).all() (RuntimeError si falla).
5. Localiza tz America/Bogota.
6. Retorna (D, G, idx_tz).

Problema que resuelve
---------------------
La versión anterior del loader sumaba todos los CSV del folder de
medidores via ``rglob("*.csv")``, mezclando totalizadores, ramales
internos y medidores de inyección (que registran valores negativos
cuando exportan solar). Esto producía:

  * Demanda artificialmente baja al mediodía en Udenar (Bloque Sur
    Med 1 es un net meter agresivo: ~20 % de las horas con valor
    negativo, mínimo −34.6 kW).
  * Una rutina ``_clean()`` que tiraba los negativos como NaN —
    ocultando el problema en lugar de resolverlo.

Solución (capas separadas)
--------------------------
1. **Selección puntual**: por institución, **un solo medidor** define
   la demanda y **un solo inversor** define la generación expuesta al
   EMS.
2. **Reconstrucción net→bruta** para los net meters: si el medidor de
   demanda es net (o net_partial), se suman los inversores físicos que
   el totalizador descontó para revertir el netting. Bookkeeping
   interno; el modelo sigue viendo un solo inversor.
3. **No-negatividad por construcción**. ``_clean()`` ya no necesita
   tratar negativos (se resolvieron aguas arriba).

Configuración elegida
---------------------
=========  ==========================================  ============  ======================  =======================
Inst.      Medidor demanda (subcarpeta)                Tipo          Inversor EMS            Inversores reconstrucción
=========  ==========================================  ============  ======================  =======================
Udenar     Bloque Sur - Medidor 1 - electricMeter      net           Fronius Inverter 1      Fronius 1+2 + Inversor MTE
Mariana    Medidor 1 - Alvernia - electricMeter        net_partial   Fronius - Alvernia      Fronius - Alvernia
UCC        Medidor 1 - UCC - electricMeter             net_partial   Fronius - UCC           Fronius - UCC
HUDN       Medidor 1 - HUDN - electricMeter            gross         Inversor 1 - HUDN       —
Cesmag     Medidor 1 - Cesmag - electricMeter          gross         Inverter 1 - Cesmag     —
=========  ==========================================  ============  ======================  =======================

Tipos:
  - "net"         : neteo agresivo (Udenar, 989 h con D<0 sobre el
                    horizonte v3). Reconstrucción obligatoria con la
                    suma de los 3 inversores físicos.
  - "net_partial" : neteo leve (Mariana 216 h, UCC 112 h con D<0).
                    Reconstrucción a través del inversor único.
  - "gross"       : medidor limpio (HUDN, Cesmag). Solo clip(0)
                    defensivo.

Sobre el horizonte
------------------
T_START = "2025-04-04", T_END = "2025-12-16" (256 días, 6 144 h).
Recorte derivado de la auditoría de calidad: el inversor de HUDN
arranca el 4-Abr y los inversores Fronius Udenar + HUDN caen el 16-Dic.
Detalles en ``outputs/data_quality_report.txt`` y notas § 3.1.

Para análisis con horizonte alternativo, build_demand_generation acepta
``t_start`` y ``t_end`` como kwargs. Sin embargo el resto del repo
asume el default (constants T_START / T_END en xm_data_loader).

Detalle completo de decisiones, verificación empírica del net metering
en Udenar y traza del pipeline: ver
``Documentos/notas_modelo_tesis.md`` § Actividad 3.1.

Auditorías relacionadas
-----------------------
- ``outputs/data_quality_audit.py`` — auditoría de las 27 fuentes
  crudas (cobertura, gaps, negativos, sensores frozen, scoring).
- ``outputs/audit_clean.py`` — diagnóstico post-preprocesamiento
  (D_net vs D_bruta vs G_recon por institución).
- ``outputs/plot_coverage_gantt.py`` — Gantt visual de cobertura.
- ``tests/test_preprocessing.py`` — 8 tests del contrato.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from data.xm_data_loader import (
    _clean,
    _read_one,
    AGENTS,
    COL_DEMAND,
    COL_GEN,
    INVERTER_FOLDER,
    METER_FOLDER,
    T_END,
    T_START,
)

warnings.filterwarnings("ignore")


# ── Configuración por institución ─────────────────────────────────────────────

DEMAND_METER_CONFIG: dict[str, dict] = {
    "Udenar":  {"subfolder": "Bloque Sur - Medidor 1 - electricMeter", "kind": "net"},
    "Mariana": {"subfolder": "Medidor 1 - Alvernia - electricMeter",   "kind": "net_partial"},
    "UCC":     {"subfolder": "Medidor 1 - UCC - electricMeter",        "kind": "net_partial"},
    "HUDN":    {"subfolder": "Medidor 1 - HUDN - electricMeter",       "kind": "gross"},
    "Cesmag":  {"subfolder": "Medidor 1 - Cesmag - electricMeter",     "kind": "gross"},
}

EMS_INVERTER_CONFIG: dict[str, str] = {
    "Udenar":  "Fronius Inverter 1 - inverter",
    "Mariana": "Fronius - Alvernia - inverter",
    "UCC":     "Fronius - UCC - inverter",
    "HUDN":    "Inversor 1 - HUDN - inverter",
    "Cesmag":  "Inverter 1 - Cesmag - inverter",
}

RECONSTRUCTION_INVERTERS_CONFIG: dict[str, list[str]] = {
    "Udenar": [
        "Fronius Inverter 1 - inverter",
        "Fronius Inverter 2 - inverter",
        "Inversor MTE - Udenar - inverter",
    ],
    "Mariana": ["Fronius - Alvernia - inverter"],
    "UCC":     ["Fronius - UCC - inverter"],
    "HUDN":    [],
    "Cesmag":  [],
}


# ── Helpers de lectura ────────────────────────────────────────────────────────

def _find_subdir(parent: Path, name: str) -> Optional[Path]:
    """Busca subcarpeta tolerante a capitalización."""
    if parent is None or not parent.exists():
        return None
    exact = parent / name
    if exact.exists():
        return exact
    for sub in parent.iterdir():
        if sub.is_dir() and sub.name.lower() == name.lower():
            return sub
    return None


def _read_single_meter(folder: Path, col: str, idx: pd.DatetimeIndex,
                       divide_by: float = 1.0) -> pd.Series:
    """
    Lee los CSV de UNA subcarpeta (puede haber varios CSVs si los datos
    están particionados temporalmente — caso v3 con 3 archivos por
    medidor), promedia duplicados, filtra al horizonte indicado por
    `idx`, resamplea a 1h, convierte unidad y reindexa.

    **No clipa negativos**: el caller decide cómo tratarlos.
    """
    parts = []
    for path in sorted(folder.rglob("*.csv")):
        s = _read_one(path, col)
        if s is not None and len(s) > 0:
            parts.append(s)

    if not parts:
        return pd.Series(np.nan, index=idx)

    combined = pd.concat(parts, axis=1).sum(axis=1, min_count=1)
    # Filtra al horizonte indicado por idx (no al T_START/T_END global)
    t_start, t_end = idx[0], idx[-1] + (idx[1] - idx[0])
    combined = combined.loc[t_start:t_end]
    hourly = combined.resample("1h").mean()
    hourly = hourly / divide_by
    return hourly.reindex(idx)


def _read_single_inverter(folder: Path, idx: pd.DatetimeIndex) -> pd.Series:
    """
    Lee la generación de UNA subcarpeta de inversor. Convierte W → kW,
    clipa negativos a 0 (la potencia AC inyectada no puede ser negativa).
    """
    s = _read_single_meter(folder, COL_GEN, idx, divide_by=1000.0)
    return s.clip(lower=0)


def _sum_inverter_reconstruction(agent_dir: Path, subfolders: list[str],
                                 idx: pd.DatetimeIndex) -> pd.Series:
    """
    Suma las series de los inversores listados en ``subfolders`` para
    reconstruir la generación total que el net meter del totalizador
    estaba descontando. Cada serie se rellena con 0 donde el inversor
    correspondiente no tenía cobertura, así que la suma cubre la unión
    de todos los períodos.
    """
    inverter_root = _find_subdir(agent_dir, INVERTER_FOLDER.get(agent_dir.name, "Inverters"))
    if inverter_root is None or not subfolders:
        return pd.Series(0.0, index=idx)

    accum = pd.Series(0.0, index=idx)
    for sub in subfolders:
        inv_dir = _find_subdir(inverter_root, sub)
        if inv_dir is None:
            continue
        g = _read_single_inverter(inv_dir, idx).fillna(0.0)
        accum = accum + g
    return accum


# ── API pública ───────────────────────────────────────────────────────────────

def build_demand_generation(
    root: Path | str,
    *,
    demand_config: dict | None = None,
    ems_inverter_config: dict | None = None,
    reconstruction_inverters_config: dict | None = None,
    t_start: str | None = None,
    t_end: str | None = None,
    verbose: bool = True,
) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    """
    Construye los arreglos D[N,T] y G[N,T] para el EMS aplicando la
    selección puntual de medidor/inversor por institución y la
    reconstrucción net→bruta donde corresponda.

    Parámetros
    ----------
    root : ruta a ``MedicionesMTE/``.
    demand_config, ems_inverter_config, reconstruction_inverters_config :
        dicts opcionales para sobreescribir las configuraciones default.
        Útil para pruebas o análisis comparativo (ej. UCC con Med 1 vs
        Med 2). Si son ``None`` se usan los defaults del módulo.
    verbose : si ``True`` imprime el reporte de carga por institución.

    Retorna
    -------
    (D, G, idx_tz) con shapes (5, 5160) y tz ``America/Bogota``.
    """
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(f"Carpeta no encontrada: {root}")

    d_cfg = demand_config or DEMAND_METER_CONFIG
    e_cfg = ems_inverter_config or EMS_INVERTER_CONFIG
    r_cfg = reconstruction_inverters_config or RECONSTRUCTION_INVERTERS_CONFIG

    ts = t_start or T_START
    te = t_end or T_END
    idx = pd.date_range(ts, te, freq="1h", inclusive="left")

    if verbose:
        print(f"\n[preprocessing] Raiz: {root}")
        print(f"  Periodo: {ts} -> {te}  ({len(idx)} horas)")
        print(f"  Estrategia: 1 medidor + 1 inversor EMS por institucion; "
              f"reconstruccion net->bruta donde aplique\n")

    D_list, G_list = [], []

    for n, agent in enumerate(AGENTS):
        adir = _find_subdir(root, agent)
        if adir is None:
            if verbose:
                print(f"  A{n} {agent}: CARPETA NO ENCONTRADA - usando ceros")
            D_list.append(np.zeros(len(idx)))
            G_list.append(np.zeros(len(idx)))
            continue

        # ── Demanda: medidor único ────────────────────────────────────
        meter_root = _find_subdir(adir, METER_FOLDER[agent])
        cfg_d = d_cfg.get(agent)
        D_raw = pd.Series(np.nan, index=idx)
        kind = "gross"
        if meter_root is not None and cfg_d is not None:
            mdir = _find_subdir(meter_root, cfg_d["subfolder"])
            kind = cfg_d.get("kind", "gross")
            if mdir is not None:
                D_raw = _read_single_meter(mdir, COL_DEMAND, idx, divide_by=1.0)
            elif verbose:
                print(f"  A{n} {agent}: subcarpeta de medidor no encontrada "
                      f"({cfg_d['subfolder']})")
        elif verbose:
            print(f"  A{n} {agent}: sin carpeta de medidores")

        # ── Generación EMS: un solo inversor ──────────────────────────
        inv_root = _find_subdir(adir, INVERTER_FOLDER[agent])
        ems_sub = e_cfg.get(agent)
        G_ems = pd.Series(0.0, index=idx)
        if inv_root is not None and ems_sub is not None:
            ems_dir = _find_subdir(inv_root, ems_sub)
            if ems_dir is not None:
                G_ems = _read_single_inverter(ems_dir, idx).fillna(0.0)
            elif verbose:
                print(f"  A{n} {agent}: subcarpeta de inversor EMS no encontrada "
                      f"({ems_sub})")
        elif verbose:
            print(f"  A{n} {agent}: sin carpeta de inversores")

        # ── Reconstrucción / clipping según semántica ────────────────
        if kind in ("net", "net_partial"):
            G_recon = _sum_inverter_reconstruction(
                adir, r_cfg.get(agent, []), idx,
            ).fillna(0.0)
            D_filled = D_raw.fillna(0.0)
            D_recon = (D_filled + G_recon).clip(lower=0.0)

            n_neg_raw = int((D_raw < 0).sum())
            n_recon = int((G_recon > 0).sum())
            n_clipped_zero = int(((D_filled + G_recon) < 0).sum())

            tag = "NET METER" if kind == "net" else "NET PARTIAL"
            if verbose:
                print(f"  A{n} {agent}  [{tag}]")
                print(f"    Medidor: {cfg_d['subfolder']}")
                print(f"    Inversor EMS: {ems_sub}")
                print(f"    Inversores reconstruccion ({len(r_cfg.get(agent, []))}): "
                      f"{', '.join(r_cfg.get(agent, [])) or '-'}")
                print(f"    horas D_net<0:        {n_neg_raw:5d}")
                print(f"    horas reconstruidas:  {n_recon:5d}  (G_recon>0)")
                if n_clipped_zero > 0:
                    print(f"    horas D_bruta clipeadas a 0 tras suma: {n_clipped_zero:5d}")
        else:
            n_neg = int((D_raw < 0).sum())
            D_recon = D_raw.clip(lower=0.0)
            if verbose:
                print(f"  A{n} {agent}  [GROSS METER]")
                print(f"    Medidor: {cfg_d['subfolder'] if cfg_d else '-'}")
                print(f"    Inversor EMS: {ems_sub}")
                print(f"    horas D_raw<0 truncadas: {n_neg:5d}"
                      + (f"  (revisar)" if n_neg > 50 else ""))

        # ── Limpieza estándar (outliers + gaps) ──────────────────────
        D = _clean(D_recon, f"{agent}/D")
        G = _clean(G_ems, f"{agent}/G")

        if verbose:
            print(f"    D  media={D.mean():6.2f} kW  max={D.max():6.2f} kW  "
                  f"horas>0={int((D>0).sum()):4d}/{len(D)}")
            print(f"    G  media={G.mean():6.2f} kW  max={G.max():6.2f} kW  "
                  f"horas>0={int((G>0).sum()):4d}/{len(G)}\n")

        D_list.append(D.values)
        G_list.append(G.values)

    D_arr = np.array(D_list, dtype=float)
    G_arr = np.array(G_list, dtype=float)

    # Sanity check del contrato no-negatividad
    if (D_arr < 0).any():
        raise RuntimeError(
            "[preprocessing] BUG: la demanda tiene valores negativos tras "
            "el preprocesamiento. Revisar el pipeline."
        )
    if (G_arr < 0).any():
        raise RuntimeError(
            "[preprocessing] BUG: la generacion tiene valores negativos "
            "tras el preprocesamiento."
        )

    if verbose:
        print(f"  D shape: {D_arr.shape}  G shape: {G_arr.shape}")
        print(f"  D total comunidad: {D_arr.sum():.0f} kWh")
        print(f"  G total comunidad: {G_arr.sum():.0f} kWh")
        print(f"  Cobertura G/D:     {G_arr.sum()/max(D_arr.sum(),1):.3f}")

    idx_tz = idx.tz_localize(
        "America/Bogota",
        nonexistent="shift_forward",
        ambiguous="infer",
    )
    return D_arr, G_arr, idx_tz
