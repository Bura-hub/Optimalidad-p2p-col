"""
data_quality_audit.py - Auditoria exhaustiva de calidad de datos MTE.

Para las 5 instituciones x {4 medidores, 1-3 inversores} = 27 CSVs:
  - Cobertura temporal (start, end, % horizonte)
  - Resolucion (median dt entre muestras)
  - Gaps (mayor gap, conteo por tamano)
  - Negativos (count, min, frac)
  - Stale runs (sensor frozen)
  - Outliers (count > p99.5 * 2)
  - Distribucion estadistica (mean, max, p995, IQR)
  - Clasificacion net/gross/partial-net automatica

Recomienda:
  - Mejor medidor de demanda por institucion
  - Mejor inversor EMS por institucion
  - Inversores de reconstruccion para Udenar (net meter)
  - Horizonte comun usable

Salidas:
  stdout: reporte legible
  outputs/data_quality_report.txt (mismo reporte archivado)
  outputs/data_quality_metrics.csv (tabla maestra con todas las metricas)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import io
import numpy as np
import pandas as pd

from data.xm_data_loader import (
    _read_one,
    AGENTS, METER_FOLDER, INVERTER_FOLDER,
    COL_DEMAND, COL_GEN,
    T_START, T_END,
)
from data.preprocessing import (
    _find_subdir,
    DEMAND_METER_CONFIG, EMS_INVERTER_CONFIG, RECONSTRUCTION_INVERTERS_CONFIG,
)


# ── Captura dual stdout: pantalla + archivo ─────────────────────────────────

class _Tee:
    def __init__(self, *streams):
        self.streams = streams
    def write(self, x):
        for s in self.streams:
            s.write(x)
    def flush(self):
        for s in self.streams:
            s.flush()


# ── Analisis por CSV ────────────────────────────────────────────────────────

def analyze_csv(folder: Path, col: str, divide_by: float,
                idx: pd.DatetimeIndex) -> dict:
    """Calcula metricas para una SUBCARPETA (concatenando sus CSVs)."""
    parts = []
    for p in sorted(folder.rglob("*.csv")):
        s_part = _read_one(p, col)
        if s_part is not None and len(s_part) > 0:
            parts.append(s_part)
    if not parts:
        return {"error": "no_data", "path": str(folder)}
    s = pd.concat(parts, axis=1).sum(axis=1, min_count=1)
    path = sorted(folder.rglob("*.csv"))[0]  # para reportar ubicacion

    # Reescalar unidad
    s = s / divide_by

    # Filtrar al horizonte de interes (idx)
    s = s.loc[idx[0]:idx[-1]]
    if len(s) == 0:
        return {"error": "no_data_in_horizon", "path": str(path)}

    # Resolucion: median dt
    dts = s.index.to_series().diff().dropna()
    res_sec = float(dts.median().total_seconds()) if len(dts) > 0 else float("nan")
    res_jitter = float(dts.std().total_seconds()) if len(dts) > 0 else 0.0

    # Cobertura
    t_start = s.index.min()
    t_end = s.index.max()
    horizon_hours = (idx[-1] - idx[0]).total_seconds() / 3600 + 1
    coverage_hours = (t_end - t_start).total_seconds() / 3600 + 1
    coverage_pct = 100.0 * coverage_hours / horizon_hours

    # Resamplear a 1h para gap/stats analysis homogeneo
    s_1h = s.resample("1h").mean().reindex(idx)

    # Gaps (NaN runs)
    is_nan = s_1h.isna()
    gap_runs = []
    if is_nan.any():
        # Identificar runs contiguos de NaN
        run_id = (is_nan != is_nan.shift()).cumsum()
        for _, group in s_1h.groupby(run_id):
            if group.isna().all():
                gap_runs.append(len(group))
    gap_runs = np.array(gap_runs) if gap_runs else np.array([0])
    largest_gap_h = int(gap_runs.max())
    n_gap_gt_1h = int((gap_runs > 1).sum())
    n_gap_gt_24h = int((gap_runs > 24).sum())
    n_gap_gt_7d = int((gap_runs > 168).sum())
    total_nan_hours = int(is_nan.sum())

    # Negativos / zeros
    valid = s_1h.dropna()
    n_neg = int((valid < 0).sum())
    min_val = float(valid.min()) if len(valid) > 0 else float("nan")
    frac_neg = n_neg / max(len(valid), 1)
    n_zero = int((valid == 0).sum())
    frac_zero = n_zero / max(len(valid), 1)

    # Stale runs (valores constantes)
    if len(valid) > 0:
        # Tolerancia 1e-3: valores casi iguales
        diffs = np.abs(valid.diff().fillna(1.0).values)
        is_stale = diffs < 1e-3
        # Longest run de stale
        if is_stale.any():
            run_lens = []
            cur = 0
            for x in is_stale:
                if x:
                    cur += 1
                else:
                    if cur > 0:
                        run_lens.append(cur)
                    cur = 0
            if cur > 0:
                run_lens.append(cur)
            longest_stale_h = max(run_lens) if run_lens else 0
            n_stale_gt_24h = sum(1 for x in run_lens if x > 24)
        else:
            longest_stale_h = 0
            n_stale_gt_24h = 0
    else:
        longest_stale_h = 0
        n_stale_gt_24h = 0

    # Estadisticas
    if len(valid) > 0:
        mean = float(valid.mean())
        median = float(valid.median())
        p95 = float(valid.quantile(0.95))
        p99 = float(valid.quantile(0.99))
        p995 = float(valid.quantile(0.995))
        max_v = float(valid.max())
        std = float(valid.std())
        q25 = float(valid.quantile(0.25))
        q75 = float(valid.quantile(0.75))
        iqr = q75 - q25

        # Outliers
        outlier_thr = max(p995 * 2, mean + 5 * std) if std > 0 else float("inf")
        n_outliers = int((valid > outlier_thr).sum()) if np.isfinite(outlier_thr) else 0
    else:
        mean = median = p95 = p99 = p995 = max_v = std = q25 = q75 = iqr = float("nan")
        n_outliers = 0

    return {
        "path": str(path.relative_to(path.parents[3])) if len(path.parents) >= 4 else str(path),
        "rows": int(len(s)),
        "t_start": str(t_start),
        "t_end": str(t_end),
        "coverage_pct": round(coverage_pct, 1),
        "horizon_hours": int(horizon_hours),
        "total_nan_hours": total_nan_hours,
        "resolution_sec": round(res_sec, 1) if not np.isnan(res_sec) else None,
        "res_jitter_sec": round(res_jitter, 2),
        "largest_gap_h": largest_gap_h,
        "n_gap_gt_1h": n_gap_gt_1h,
        "n_gap_gt_24h": n_gap_gt_24h,
        "n_gap_gt_7d": n_gap_gt_7d,
        "n_neg": n_neg,
        "frac_neg": round(frac_neg, 4),
        "min_val": round(min_val, 2) if not np.isnan(min_val) else None,
        "n_zero": n_zero,
        "frac_zero": round(frac_zero, 4),
        "longest_stale_h": longest_stale_h,
        "n_stale_gt_24h": n_stale_gt_24h,
        "mean": round(mean, 3) if not np.isnan(mean) else None,
        "median": round(median, 3) if not np.isnan(median) else None,
        "p95": round(p95, 3) if not np.isnan(p95) else None,
        "p99": round(p99, 3) if not np.isnan(p99) else None,
        "p995": round(p995, 3) if not np.isnan(p995) else None,
        "max": round(max_v, 3) if not np.isnan(max_v) else None,
        "std": round(std, 3) if not np.isnan(std) else None,
        "q25": round(q25, 3) if not np.isnan(q25) else None,
        "q75": round(q75, 3) if not np.isnan(q75) else None,
        "iqr": round(iqr, 3) if not np.isnan(iqr) else None,
        "n_outliers": n_outliers,
        "_series": s_1h,  # se elimina antes de exportar a CSV
    }


def detect_net_metering(s_1h: pd.Series) -> tuple[str, dict]:
    """Heuristica para clasificar si una serie horaria es net / gross / partial."""
    valid = s_1h.dropna()
    if len(valid) == 0:
        return "unknown", {}

    n_neg = int((valid < 0).sum())
    frac_neg = n_neg / len(valid)
    min_val = float(valid.min())

    # Perfil hora-del-dia
    by_hour = valid.groupby(valid.index.hour).mean()
    night_avg = by_hour.loc[[0, 1, 2, 3, 4, 5]].mean()
    midday_avg = by_hour.loc[[10, 11, 12, 13, 14]].mean()
    midday_drop_ratio = midday_avg / max(abs(night_avg), 1e-3) if night_avg > 0 else float("nan")

    # Reglas
    if frac_neg > 0.05 or min_val < -1.0:
        cls = "net_aggressive"
    elif frac_neg > 0.001:
        cls = "net_partial"
    elif midday_avg < 0.5 * night_avg and night_avg > 0.5:
        cls = "net_partial_or_low_midday"  # ambiguo
    else:
        cls = "gross"

    return cls, {
        "frac_neg": round(frac_neg, 4),
        "min_val": round(min_val, 2),
        "night_avg_kw": round(float(night_avg), 2),
        "midday_avg_kw": round(float(midday_avg), 2),
        "midday_drop_ratio": round(float(midday_drop_ratio), 2) if not np.isnan(midday_drop_ratio) else None,
    }


# ── Scoring ─────────────────────────────────────────────────────────────────

def score_meter_for_demand(metrics: dict, net_class: str,
                           expected_kw_range: tuple[float, float] = (1.0, 100.0)) -> tuple[float, list]:
    """Score 0-100 + lista de notas explicativas."""
    notes = []
    score = 0.0

    # Coverage (peso 30)
    cov = metrics["coverage_pct"]
    cov_score = min(cov, 100.0)
    score += 0.30 * cov_score
    if cov < 90:
        notes.append(f"cobertura {cov:.0f}% (-)")

    # Net penalty (peso 25): GROSS gana puntos completos; NET pierde
    net_pen_map = {
        "gross": 100.0,
        "net_partial_or_low_midday": 70.0,
        "net_partial": 40.0,
        "net_aggressive": 10.0,
        "unknown": 50.0,
    }
    net_score = net_pen_map.get(net_class, 50.0)
    score += 0.25 * net_score
    if net_class != "gross":
        notes.append(f"clase={net_class}")

    # Stale (peso 15)
    stale_h = metrics.get("longest_stale_h", 0)
    if stale_h > 168:
        stale_score = 0.0
        notes.append(f"sensor frozen {stale_h}h consecutivas (--)")
    elif stale_h > 24:
        stale_score = 50.0
        notes.append(f"stale runs {stale_h}h (-)")
    else:
        stale_score = 100.0
    score += 0.15 * stale_score

    # Resolution (peso 10)
    res = metrics.get("resolution_sec") or 0
    if 60 <= res <= 240:
        res_score = 100.0
    elif res < 600:
        res_score = 70.0
    else:
        res_score = 30.0
        notes.append(f"resolucion {res}s (no es 2 min)")
    score += 0.10 * res_score

    # Magnitude in expected range (peso 10)
    max_v = metrics.get("max") or 0
    lo, hi = expected_kw_range
    if lo <= max_v <= hi:
        mag_score = 100.0
    elif max_v < lo:
        mag_score = 30.0
        notes.append(f"max={max_v} < {lo} (parece ramal interno)")
    else:
        mag_score = 60.0
        notes.append(f"max={max_v} > {hi} (atipicamente alto)")
    score += 0.10 * mag_score

    # Outliers (peso 10)
    n_out = metrics.get("n_outliers", 0)
    if n_out == 0:
        out_score = 100.0
    elif n_out < 5:
        out_score = 80.0
    elif n_out < 20:
        out_score = 50.0
    else:
        out_score = 20.0
        notes.append(f"{n_out} outliers (-)")
    score += 0.10 * out_score

    return round(score, 1), notes


def score_inverter(metrics: dict, expected_kw_range: tuple[float, float] = (3.0, 30.0)
                   ) -> tuple[float, list]:
    """Score para inversores: prioriza coverage + magnitude."""
    notes = []
    score = 0.0

    cov = metrics["coverage_pct"]
    cov_score = min(cov, 100.0)
    score += 0.45 * cov_score
    if cov < 90:
        notes.append(f"cov {cov:.0f}%")

    max_v = metrics.get("max") or 0
    lo, hi = expected_kw_range
    if lo <= max_v <= hi:
        mag_score = 100.0
    elif max_v < lo:
        mag_score = 40.0
        notes.append(f"max={max_v}kW chico")
    else:
        mag_score = 70.0
    score += 0.30 * mag_score

    stale_h = metrics.get("longest_stale_h", 0)
    if stale_h > 168:  # >1 sem stale fuera de "noche" sospechoso
        stale_score = 30.0
        notes.append(f"stale {stale_h}h")
    else:
        stale_score = 100.0
    score += 0.15 * stale_score

    n_neg = metrics.get("n_neg", 0)
    neg_score = 100.0 if n_neg == 0 else 50.0
    score += 0.10 * neg_score

    return round(score, 1), notes


# ── Pipeline principal ──────────────────────────────────────────────────────

def main():
    import os as _os
    repo = Path(__file__).resolve().parents[1]
    root = Path(_os.environ.get("MTE_ROOT", str(repo / "MedicionesMTE_v3")))
    ts = _os.environ.get("MTE_T_START", T_START)
    te = _os.environ.get("MTE_T_END", T_END)
    if not root.exists():
        print(f"ERROR: {root} no existe.")
        return

    out_txt = repo / "outputs" / "data_quality_report.txt"
    out_csv = repo / "outputs" / "data_quality_metrics.csv"
    buf = io.StringIO()
    sys.stdout = _Tee(sys.__stdout__, buf)

    idx = pd.date_range(ts, te, freq="1h", inclusive="left")

    print("=" * 90)
    print(f"AUDITORIA DE CALIDAD DE DATOS MTE  -  raiz: {root}")
    print(f"Periodo objetivo: {ts} -> {te}  ({len(idx)} horas)")
    print("=" * 90)

    all_metrics = []  # filas para CSV
    inst_data = {}    # {agent: {meters: [...], inverters: [...]}}

    # --- Fase 1: leer todos los CSVs ---
    print("\n[1/4] Leyendo CSVs...")
    for n, agent in enumerate(AGENTS):
        adir = _find_subdir(root, agent)
        if adir is None:
            print(f"  {agent}: CARPETA NO ENCONTRADA")
            continue

        meters_info = []
        meter_root = _find_subdir(adir, METER_FOLDER[agent])
        if meter_root:
            for sub in sorted(meter_root.iterdir()):
                if not sub.is_dir():
                    continue
                csvs = list(sub.rglob("*.csv"))
                if not csvs:
                    continue
                # Concatena todos los CSVs de la subcarpeta (v3 los particiona)
                m = analyze_csv(sub, COL_DEMAND, divide_by=1.0, idx=idx)
                m["agent"] = agent
                m["category"] = "meter"
                m["subfolder"] = sub.name
                if "_series" in m and m["_series"] is not None:
                    cls, ev = detect_net_metering(m["_series"])
                    m["net_class"] = cls
                    m["net_evidence"] = ev
                meters_info.append(m)

        inverters_info = []
        inv_root = _find_subdir(adir, INVERTER_FOLDER[agent])
        if inv_root:
            for sub in sorted(inv_root.iterdir()):
                if not sub.is_dir():
                    continue
                csvs = list(sub.rglob("*.csv"))
                if not csvs:
                    continue
                m = analyze_csv(sub, COL_GEN, divide_by=1000.0, idx=idx)
                m["agent"] = agent
                m["category"] = "inverter"
                m["subfolder"] = sub.name
                inverters_info.append(m)

        inst_data[agent] = {"meters": meters_info, "inverters": inverters_info}
        all_metrics.extend(meters_info)
        all_metrics.extend(inverters_info)

    # --- Fase 2: scoring ---
    print("[2/4] Scoring medidores e inversores...")
    # Rango esperado por institucion (kW): heuristico basado en tamano del campus
    expected_demand_range = {
        "Udenar":  (5.0, 100.0),
        "Mariana": (5.0, 100.0),
        "UCC":     (5.0, 100.0),
        "HUDN":    (5.0, 50.0),
        "Cesmag":  (3.0, 50.0),
    }
    expected_inverter_range = (3.0, 25.0)

    for agent, info in inst_data.items():
        rng = expected_demand_range.get(agent, (1.0, 100.0))
        for m in info["meters"]:
            cls = m.get("net_class", "unknown")
            score, notes = score_meter_for_demand(m, cls, rng)
            m["score"] = score
            m["score_notes"] = notes
        for inv in info["inverters"]:
            score, notes = score_inverter(inv, expected_inverter_range)
            inv["score"] = score
            inv["score_notes"] = notes

    # --- Fase 3: imprimir reporte ---
    print("[3/4] Generando reporte...\n")

    # § 1 Resumen ejecutivo
    n_meters = sum(len(d["meters"]) for d in inst_data.values())
    n_invs = sum(len(d["inverters"]) for d in inst_data.values())
    avg_cov_meters = np.mean([m["coverage_pct"] for d in inst_data.values() for m in d["meters"]])
    avg_cov_invs = np.mean([m["coverage_pct"] for d in inst_data.values() for m in d["inverters"]])
    net_meters = [(d["agent"] if False else agent, m["subfolder"]) for agent, d in inst_data.items()
                   for m in d["meters"] if m.get("net_class", "gross") != "gross"]
    stale_sources = [(agent, m["subfolder"], m["longest_stale_h"])
                      for agent, d in inst_data.items()
                      for m in d["meters"] + d["inverters"]
                      if m.get("longest_stale_h", 0) > 168]

    print("=" * 90)
    print("§1 - RESUMEN EJECUTIVO")
    print("=" * 90)
    print(f"  Medidores analizados:  {n_meters}")
    print(f"  Inversores analizados: {n_invs}")
    print(f"  Cobertura promedio medidores: {avg_cov_meters:.1f}%")
    print(f"  Cobertura promedio inversores: {avg_cov_invs:.1f}%")
    print(f"  Net meters detectados ({len(net_meters)}):")
    for a, s in net_meters:
        print(f"    - {a}: {s}")
    if stale_sources:
        print(f"  Sensores con stale runs > 7 dias ({len(stale_sources)}):")
        for a, s, h in stale_sources:
            print(f"    - {a}: {s}  ({h}h)")
    else:
        print("  Sensores frozen > 7 dias: ninguno")

    # § 2 Por institucion
    print()
    print("=" * 90)
    print("§2 - DETALLE POR INSTITUCION")
    print("=" * 90)
    for agent in AGENTS:
        info = inst_data.get(agent)
        if not info:
            continue
        print(f"\n[{agent}]  Carpeta: {agent}/{METER_FOLDER[agent]}/  +  {agent}/{INVERTER_FOLDER[agent]}/")
        print()
        print(f"  MEDIDORES ({len(info['meters'])}):")
        print(f"    {'#':>2} {'subfolder':<48} {'cov%':>5} {'min':>6} {'max':>6} {'mean':>6} "
              f"{'neg_h':>5} {'class':<28} {'score':>5}")
        # Ordenar por score descendente
        meters_sorted = sorted(info["meters"], key=lambda m: -m.get("score", 0))
        for i, m in enumerate(meters_sorted, 1):
            cls = m.get("net_class", "?")
            print(f"    {i:>2} {m['subfolder']:<48} {m['coverage_pct']:>5.1f} "
                  f"{(m.get('min_val') or 0):>6.1f} "
                  f"{(m.get('max') or 0):>6.1f} "
                  f"{(m.get('mean') or 0):>6.2f} "
                  f"{m.get('n_neg', 0):>5d} "
                  f"{cls:<28} "
                  f"{m.get('score', 0):>5.1f}")
            if m.get("score_notes"):
                print(f"        notes: {' | '.join(m['score_notes'])}")

        print()
        print(f"  INVERSORES ({len(info['inverters'])}):")
        print(f"    {'#':>2} {'subfolder':<48} {'cov%':>5} {'rango':<25} {'max':>6} "
              f"{'mean':>6} {'score':>5}")
        invs_sorted = sorted(info["inverters"], key=lambda m: -m.get("score", 0))
        for i, inv in enumerate(invs_sorted, 1):
            t_s = inv["t_start"][:10]
            t_e = inv["t_end"][:10]
            print(f"    {i:>2} {inv['subfolder']:<48} {inv['coverage_pct']:>5.1f} "
                  f"{t_s}->{t_e:<11} "
                  f"{(inv.get('max') or 0):>6.1f} "
                  f"{(inv.get('mean') or 0):>6.2f} "
                  f"{inv.get('score', 0):>5.1f}")
            if inv.get("score_notes"):
                print(f"        notes: {' | '.join(inv['score_notes'])}")

        # Recomendacion
        print()
        print(f"  RECOMENDACION {agent}:")
        if meters_sorted:
            top_m = meters_sorted[0]
            print(f"    Demanda: {top_m['subfolder']}  (score {top_m.get('score', 0):.1f}, "
                  f"clase {top_m.get('net_class', '?')})")
        if invs_sorted:
            top_inv = invs_sorted[0]
            print(f"    EMS inverter: {top_inv['subfolder']}  (score {top_inv.get('score', 0):.1f}, "
                  f"cov {top_inv['coverage_pct']:.0f}%)")
        # Reconstruccion solo si net
        if meters_sorted and meters_sorted[0].get("net_class", "gross") != "gross":
            recon = [inv["subfolder"] for inv in invs_sorted]
            print(f"    Inversores reconstruccion: {recon}")

        # Diff vs config actual
        cur_d = DEMAND_METER_CONFIG.get(agent, {}).get("subfolder", "")
        cur_e = EMS_INVERTER_CONFIG.get(agent, "")
        rec_d = meters_sorted[0]["subfolder"] if meters_sorted else "?"
        rec_e = invs_sorted[0]["subfolder"] if invs_sorted else "?"
        if rec_d != cur_d or rec_e != cur_e:
            print(f"    >> Cambio sugerido vs config actual:")
            if rec_d != cur_d:
                print(f"       Demanda:  {cur_d!r:<50} -> {rec_d!r}")
            if rec_e != cur_e:
                print(f"       Inversor: {cur_e!r:<50} -> {rec_e!r}")

    # § 3 Horizonte comun
    print()
    print("=" * 90)
    print("§3 - HORIZONTE COMUN USABLE")
    print("=" * 90)
    # Para la config recomendada (top 1 score por institucion)
    starts = []
    ends = []
    for agent in AGENTS:
        info = inst_data.get(agent, {})
        ms = sorted(info.get("meters", []), key=lambda m: -m.get("score", 0))
        ivs = sorted(info.get("inverters", []), key=lambda m: -m.get("score", 0))
        if ms:
            starts.append((agent, "meter", ms[0]["t_start"][:10], ms[0]["t_end"][:10]))
        if ivs:
            starts.append((agent, "inv", ivs[0]["t_start"][:10], ivs[0]["t_end"][:10]))

    if starts:
        max_start = max(pd.Timestamp(s[2]) for s in starts)
        min_end = min(pd.Timestamp(s[3]) for s in starts)
        print(f"  Para la config TOP-1 score por institucion:")
        for a, k, ts, te in starts:
            print(f"    {a:<10} {k:<6} {ts} -> {te}")
        if max_start <= min_end:
            common_days = (min_end - max_start).days + 1
            print(f"\n  Horizonte comun: {max_start.date()} -> {min_end.date()}  ({common_days} dias)")
            target_days = (idx[-1] - idx[0]).days + 1
            print(f"  Cobertura comun vs horizonte objetivo: {100*common_days/target_days:.1f}%")
        else:
            print(f"\n  ! Horizonte comun VACIO (max_start={max_start.date()} > min_end={min_end.date()})")
            print("    Sera necesario imputar/recortar.")

    # § 4 Recomendaciones finales
    print()
    print("=" * 90)
    print("§4 - RESUMEN DE RECOMENDACIONES")
    print("=" * 90)
    print()
    print("  Config TOP-1 score por institucion vs config actual:")
    print()
    print(f"    {'Inst':<10} {'Item':<10} {'Actual':<50} {'Recomendado':<50}")
    print("    " + "-" * 122)
    for agent in AGENTS:
        info = inst_data.get(agent, {})
        ms = sorted(info.get("meters", []), key=lambda m: -m.get("score", 0))
        ivs = sorted(info.get("inverters", []), key=lambda m: -m.get("score", 0))
        cur_d = DEMAND_METER_CONFIG.get(agent, {}).get("subfolder", "")
        cur_e = EMS_INVERTER_CONFIG.get(agent, "")
        rec_d = ms[0]["subfolder"] if ms else "?"
        rec_e = ivs[0]["subfolder"] if ivs else "?"
        flag_d = "" if rec_d == cur_d else "  <-- CAMBIO"
        flag_e = "" if rec_e == cur_e else "  <-- CAMBIO"
        print(f"    {agent:<10} demanda    {cur_d:<50} {rec_d:<50}{flag_d}")
        print(f"    {agent:<10} EMS inv    {cur_e:<50} {rec_e:<50}{flag_e}")

    # --- Fase 4: guardar archivos ---
    print()
    print("[4/4] Guardando archivos...")
    sys.stdout = sys.__stdout__
    out_txt.write_text(buf.getvalue(), encoding="utf-8")
    print(f"  Reporte texto -> {out_txt}")

    # CSV de metricas (eliminar _series)
    rows = []
    for m in all_metrics:
        m2 = {k: v for k, v in m.items() if k not in {"_series", "score_notes", "net_evidence"}}
        m2["score_notes"] = "; ".join(m.get("score_notes", []))
        rows.append(m2)
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    print(f"  CSV metricas -> {out_csv}")
    print()
    print("Listo.")


if __name__ == "__main__":
    main()
