"""
scripts/ruflo_snapshot_run.py — A4 Snapshot post-run en Ruflo (namespace 'runs')
=================================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Wrapper post-run que captura las metricas clave de
`outputs/resultados_comparacion.xlsx` y las almacena en Ruflo namespace
`runs` para comparacion historica entre corridas (pre-CAL vs post-CAL,
distintos sub-periodos, etc.).

Datos del snapshot:
  - Fecha y hora del run.
  - Lista de CALs activos al momento del run (lectura de `docs/adr/README.md`).
  - Net benefit por escenario (P2P, C1, C2, C3, C4).
  - Indices SC, SS, IE.
  - kWh totales transados en P2P.
  - Gini por escenario (estimado de Por_agente).
  - Ventaja P2P vs C1 y P2P vs C4.

Uso:
  python scripts/ruflo_snapshot_run.py
  python scripts/ruflo_snapshot_run.py --xlsx outputs/resultados_comparacion.xlsx
  python scripts/ruflo_snapshot_run.py --tag "post-CAL-23" --dry-run

El tag se prefija a la clave Ruflo (default: timestamp).
"""
from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                   encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer,
                                   encoding="utf-8", errors="replace")

DEFAULT_XLSX = ROOT / "outputs" / "resultados_comparacion.xlsx"
ADR_README = ROOT / "docs" / "adr" / "README.md"

RE_README_TABLE_ROW = re.compile(
    r"^\|\s*(\d{4}\*?)\s*\|\s*CAL[-‑–](\d{1,3})\s*:", re.MULTILINE
)


def _gini(values: np.ndarray) -> float:
    v = np.asarray(values, dtype=float).flatten()
    if v.size == 0 or np.all(v == 0):
        return 0.0
    if np.any(v < 0):
        v = v - v.min()
    v = np.sort(v)
    n = v.size
    cum = np.cumsum(v)
    return float((2 * np.sum(np.arange(1, n + 1) * v) - (n + 1) * cum[-1])
                  / (n * cum[-1]))


def extract_run_metrics(xlsx_path: Path) -> dict:
    """Lee el xlsx de comparacion y extrae las metricas clave."""
    xl = pd.ExcelFile(xlsx_path)
    out: dict = {}

    if "Resumen" in xl.sheet_names:
        df = pd.read_excel(xl, "Resumen")
        for _, r in df.iterrows():
            esc = r["Escenario"]
            out[f"net_benefit_{esc}"] = float(r.get("Ganancia_neta_COP", 0))
            out[f"SC_{esc}"] = float(r.get("SC", 0))
            out[f"SS_{esc}"] = float(r.get("SS", 0))
            out[f"IE_{esc}"] = float(r.get("IE", 0))

    if "Por_agente" in xl.sheet_names:
        df = pd.read_excel(xl, "Por_agente")
        out["n_agentes"] = int(len(df))
        for esc in ["P2P", "C1", "C2", "C3", "C4"]:
            if esc in df.columns:
                out[f"gini_{esc}"] = round(_gini(df[esc].to_numpy()), 4)

    if "P2P_horario" in xl.sheet_names:
        df = pd.read_excel(xl, "P2P_horario")
        if "kWh_P2P" in df.columns:
            out["kWh_P2P_total"] = round(float(df["kWh_P2P"].sum()), 3)
            out["horas_p2p_activas"] = int((df["kWh_P2P"] > 1e-4).sum())
            out["horas_total"] = int(len(df))

    return out


def get_active_cals(adr_readme: Path = ADR_README) -> list[int]:
    """Lee CALs Accepted desde la tabla en docs/adr/README.md."""
    if not adr_readme.exists():
        return []
    text = adr_readme.read_text(encoding="utf-8")
    cals = sorted({int(m.group(2))
                    for m in RE_README_TABLE_ROW.finditer(text)})
    return cals


def build_snapshot_text(metrics: dict, cals: list[int],
                         fecha_iso: str, tag: str = "") -> str:
    """Compone un texto semantico denso con todas las metricas + CALs."""
    parts = [f"Snapshot run {fecha_iso}"]
    if tag:
        parts.append(f"tag={tag}")
    if cals:
        parts.append(f"CALs activos: {len(cals)} ADRs Accepted "
                      f"({min(cals)}-{max(cals)})")

    nb = []
    for esc in ["P2P", "C1", "C2", "C3", "C4"]:
        if f"net_benefit_{esc}" in metrics:
            nb.append(f"net_benefit_{esc}={metrics[f'net_benefit_{esc}']:.0f}")
    if nb:
        parts.append(" ".join(nb))

    rpe_pairs = []
    if "net_benefit_P2P" in metrics and "net_benefit_C1" in metrics:
        rpe_p2p_c1 = (metrics["net_benefit_P2P"] - metrics["net_benefit_C1"]
                       ) / max(abs(metrics["net_benefit_C1"]), 1e-9)
        rpe_pairs.append(f"RPE_P2P_vs_C1={rpe_p2p_c1:+.4f}")
    if "net_benefit_P2P" in metrics and "net_benefit_C4" in metrics:
        rpe_p2p_c4 = (metrics["net_benefit_P2P"] - metrics["net_benefit_C4"]
                       ) / max(abs(metrics["net_benefit_C4"]), 1e-9)
        rpe_pairs.append(f"RPE_P2P_vs_C4={rpe_p2p_c4:+.4f}")
    if rpe_pairs:
        parts.append(" ".join(rpe_pairs))

    for k in ("IE_P2P", "kWh_P2P_total", "horas_p2p_activas",
              "horas_total", "n_agentes"):
        if k in metrics:
            parts.append(f"{k}={metrics[k]}")

    gini_pairs = [f"gini_{esc}={metrics.get(f'gini_{esc}')}"
                   for esc in ("P2P", "C1", "C2", "C3", "C4")
                   if f"gini_{esc}" in metrics]
    if gini_pairs:
        parts.append(" ".join(gini_pairs))

    parts.append("actividad 1.0 4.1 4.2")
    return " | ".join(parts)


def store_snapshot(key: str, text: str, namespace: str = "runs") -> bool:
    """Almacena via npx claude-flow memory store --upsert."""
    flat = text.replace("\n", " | ").replace('"', "'")
    cmd = (
        f'npx @claude-flow/cli@latest memory store '
        f'--key "{key}" --value "{flat}" --namespace "{namespace}" --upsert'
    )
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", shell=True,
    )
    out = proc.stdout + proc.stderr
    return proc.returncode == 0 and "Data stored successfully" in out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xlsx", default=str(DEFAULT_XLSX))
    ap.add_argument("--tag", default="",
                    help="Tag opcional para la clave Ruflo (e.g. 'post-CAL-23')")
    ap.add_argument("--namespace", default="runs")
    ap.add_argument("--dry-run", action="store_true",
                    help="No almacena en Ruflo; solo imprime el snapshot.")
    args = ap.parse_args()

    xlsx = Path(args.xlsx)
    if not xlsx.exists():
        print(f"  [A4] No existe {xlsx}; corre `python main_simulation.py "
              f"--data real --full` primero.")
        return 1

    try:
        rel_xlsx = xlsx.relative_to(ROOT)
    except ValueError:
        rel_xlsx = xlsx  # xlsx fuera del repo (e.g. tests con tmp_path)
    print(f"  [A4] Extrayendo metricas de {rel_xlsx}...")
    metrics = extract_run_metrics(xlsx)
    cals = get_active_cals()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    text = build_snapshot_text(metrics, cals, fecha, tag=args.tag)
    key_suffix = args.tag or datetime.now().strftime("%Y%m%d-%H%M")
    key = f"run-{key_suffix}"

    print(f"  [A4] CALs activos: {len(cals)} ({min(cals) if cals else '-'} a "
          f"{max(cals) if cals else '-'})")
    print(f"  [A4] Metricas extraidas: {len(metrics)} keys")
    print(f"  [A4] Snapshot key: {key}")
    print()
    print(f"  [A4] Texto semantico ({len(text)} chars):")
    print(f"        {text}")

    if args.dry_run:
        print()
        print("  [A4] dry-run, NO almacenado en Ruflo.")
        return 0

    if store_snapshot(key, text, namespace=args.namespace):
        print()
        print(f"  [A4] Snapshot almacenado en namespace '{args.namespace}'.")
        return 0
    else:
        print()
        print(f"  [A4] Fallo al almacenar; revisa npx claude-flow.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
