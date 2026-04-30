"""
scripts/cal9_delta_report.py — delta CAL-8 → CAL-9
===================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Compara dos archivos `outputs/resultados_comparacion.xlsx` generados antes
y después del refactor pi_gs (N,) → (N, T):

    python scripts/cal9_delta_report.py \
        --pre outputs/pre_cal9_resultados.xlsx \
        --post outputs/resultados_comparacion.xlsx

Reporta delta absoluto y relativo en métricas clave por escenario y por
agente, y persiste el resumen en
``outputs/cal9_delta_report.md``.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd


def _read_sheets(xlsx: Path) -> dict[str, pd.DataFrame]:
    """Carga todas las hojas relevantes del Excel de comparación."""
    return {
        name: pd.read_excel(xlsx, sheet_name=name)
        for name in pd.ExcelFile(xlsx).sheet_names
    }


def _agg_table(sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Hoja "Resumen" con net_benefit por escenario."""
    name = next((s for s in sheets
                 if s.lower().startswith(("resumen", "agreg"))), None)
    if name is None:
        raise ValueError("No se encontró hoja Resumen/Agregado en el Excel.")
    return sheets[name]


def _per_agent_table(sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Hoja "Por_agente" con net_benefit per-agente per-escenario."""
    name = next((s for s in sheets
                 if s.lower().replace("_", "").startswith(("poragente", "agente"))),
                None)
    if name is None:
        return pd.DataFrame()
    return sheets[name]


def _delta_row(pre: float, post: float) -> tuple[float, float]:
    delta = post - pre
    rel = (delta / pre * 100.0) if abs(pre) > 1e-9 else float("nan")
    return delta, rel


def main(pre_path: Path, post_path: Path, out_path: Path) -> None:
    pre = _read_sheets(pre_path)
    post = _read_sheets(post_path)

    lines: list[str] = []
    lines.append("# CAL-9 — Delta numérico vs CAL-8")
    lines.append("")
    lines.append(f"- Pre  (CAL-8): `{pre_path}`")
    lines.append(f"- Post (CAL-9): `{post_path}`")
    lines.append("")

    # ── 1. Agregado por escenario ────────────────────────────────────────
    pre_agg = _agg_table(pre)
    post_agg = _agg_table(post)
    nb_col = next((c for c in pre_agg.columns
                   if c.startswith("Ganancia") or c.lower().startswith("net")),
                  None)
    if nb_col is None:
        raise ValueError("No se encontró columna de net_benefit en Agregado.")

    lines.append("## Beneficio neto agregado por escenario")
    lines.append("")
    lines.append("| Escenario | CAL-8 (COP) | CAL-9 (COP) | Δ COP | Δ % |")
    lines.append("|---|---:|---:|---:|---:|")
    merged = pre_agg.merge(
        post_agg, on="Escenario", how="outer", suffixes=("_pre", "_post"),
    )
    for _, row in merged.iterrows():
        esc = row["Escenario"]
        pre_v = float(row[f"{nb_col}_pre"])
        post_v = float(row[f"{nb_col}_post"])
        d, r = _delta_row(pre_v, post_v)
        lines.append(
            f"| {esc} | {pre_v:,.0f} | {post_v:,.0f} | {d:+,.0f} | {r:+.3f}% |"
        )
    lines.append("")

    # ── 2. Per-agente per-escenario ─────────────────────────────────────
    pre_pa = _per_agent_table(pre)
    post_pa = _per_agent_table(post)
    if not pre_pa.empty and not post_pa.empty:
        agent_col = pre_pa.columns[0]
        scenarios = [c for c in pre_pa.columns
                     if c != agent_col and c in post_pa.columns]
        lines.append("## Beneficio neto por agente y escenario")
        lines.append("")
        for esc in scenarios:
            lines.append(f"### {esc}")
            lines.append("")
            lines.append("| Agente | CAL-8 (COP) | CAL-9 (COP) | Δ COP | Δ % |")
            lines.append("|---|---:|---:|---:|---:|")
            mer = pre_pa[[agent_col, esc]].merge(
                post_pa[[agent_col, esc]], on=agent_col,
                suffixes=("_pre", "_post"),
            )
            for _, row in mer.iterrows():
                pre_v = float(row[f"{esc}_pre"])
                post_v = float(row[f"{esc}_post"])
                d, r = _delta_row(pre_v, post_v)
                lines.append(
                    f"| {row[agent_col]} | {pre_v:,.0f} | {post_v:,.0f} "
                    f"| {d:+,.0f} | {r:+.3f}% |"
                )
            lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Reporte CAL-9 -> {out_path}")
    sys_stdout = sys.stdout
    try:
        for ln in lines[:25]:
            sys_stdout.buffer.write((ln + "\n").encode("utf-8", "replace"))
        sys_stdout.buffer.flush()
    except AttributeError:
        for ln in lines[:25]:
            print(ln)
    if len(lines) > 25:
        print("  ...")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Reporte delta CAL-8 → CAL-9 (pi_gs escalar vs temporal)"
    )
    ap.add_argument("--pre",  default="outputs/pre_cal9_resultados.xlsx")
    ap.add_argument("--post", default="outputs/resultados_comparacion.xlsx")
    ap.add_argument("--out",  default="outputs/cal9_delta_report.md")
    args = ap.parse_args()

    main(Path(args.pre), Path(args.post), Path(args.out))
