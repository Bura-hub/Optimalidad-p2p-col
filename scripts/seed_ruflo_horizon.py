"""Sembrado del horizon de cierre de tesis en namespace 'horizons'.

Registra un horizon multi-mes con hitos del manuscrito, datos de campo
y defensa. Cada hito tambien se almacena como entrada individual para
busqueda semantica granular.

Idempotente: re-ejecutar sobrescribe.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HORIZON_KEY = "horizon-tesis-cierre"
TARGET_DATE = "2026-07-31"  # tentativo: defensa Q3 2026
CREATED = "2026-04-30"

MILESTONES = [
    {
        "id": "m1-cap4-borrador",
        "name": "Capitulo 4 (Resultados) — borrador",
        "criteria": "Documentos/FinalTesis/cap4_resultados.tex con tablas SA-1/2, FA-1/2, IR §3.14, RPE, PoF",
        "estimated_due": "2026-05-15",
        "status": "pending",
        "blocks": ["m4-revision-pantoja"],
    },
    {
        "id": "m2-cap5-borrador",
        "name": "Capitulo 5 (Conclusiones) — borrador",
        "criteria": "Cap 5 con sintesis de hallazgos, limitaciones, trabajo futuro",
        "estimated_due": "2026-05-25",
        "status": "pending",
        "blocks": ["m4-revision-pantoja"],
    },
    {
        "id": "m3-apendices-A-B",
        "name": "Apendice A (Calibracion) + Apendice B (Reproducibilidad)",
        "criteria": "Apendice A alineado con ADRs 0001-0008; Apendice B con manual --full y comandos pytest",
        "estimated_due": "2026-06-05",
        "status": "pending",
        "blocks": ["m4-revision-pantoja"],
    },
    {
        "id": "m4-revision-pantoja",
        "name": "Revision asesor Andres Pantoja",
        "criteria": "Comentarios incorporados sobre Caps 4-5 + Apendices",
        "estimated_due": "2026-06-20",
        "status": "pending",
        "blocks": ["m5-revision-obando"],
    },
    {
        "id": "m5-revision-obando",
        "name": "Revision asesor German Obando",
        "criteria": "Comentarios incorporados, manuscrito v1 listo",
        "estimated_due": "2026-07-05",
        "status": "pending",
        "blocks": ["m7-defensa"],
    },
    {
        "id": "m6-datos-campo",
        "name": "Datos de campo confirmados",
        "criteria": "Factura Cedenar con NT real per institucion + ficha tecnica inversores (LCOE) + autores refs [22][24][26][27]",
        "estimated_due": "2026-05-30",
        "status": "pending",
        "blocks": ["m4-revision-pantoja"],
    },
    {
        "id": "m7-defensa",
        "name": "Defensa publica",
        "criteria": "Fecha oficial agendada, presentacion lista, simulacros 1 y 2 ejecutados",
        "estimated_due": TARGET_DATE,
        "status": "pending",
        "blocks": [],
    },
]


def store(key: str, value: str, namespace: str) -> bool:
    flat = value.replace("\n", " | ").replace('"', "'")
    cmd = (
        f'npx @claude-flow/cli@latest memory store '
        f'--key "{key}" --value "{flat}" --namespace "{namespace}" --upsert'
    )
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", shell=True,
    )
    ok = proc.returncode == 0 and "Data stored successfully" in (proc.stdout + proc.stderr)
    if not ok:
        print(f"  FAIL {key}: {proc.stderr.strip()[:150]}")
    return ok


def main() -> int:
    # 1. Horizon principal (resumen estructurado)
    horizon = {
        "objective": "Cierre de tesis MaIE Udenar 2026: manuscrito + revision asesores + defensa",
        "created": CREATED,
        "targetDate": TARGET_DATE,
        "currentMilestone": "m1-cap4-borrador",
        "milestones_count": len(MILESTONES),
        "milestones_pending": len(MILESTONES),
        "milestones_done": 0,
        "drift_threshold_days": 7,
        "milestone_ids": [m["id"] for m in MILESTONES],
    }
    horizon_value = (
        f"objective: {horizon['objective']} | "
        f"target_date: {horizon['targetDate']} | "
        f"current: {horizon['currentMilestone']} | "
        f"milestones: {horizon['milestones_count']} pending | "
        f"drift_threshold: {horizon['drift_threshold_days']} dias | "
        f"ids: {','.join(horizon['milestone_ids'])}"
    )
    print(f"[horizon] storing main horizon ({len(horizon_value)} chars)...")
    ok_main = store(HORIZON_KEY, horizon_value, "horizons")

    # 2. Cada hito como entrada individual (busqueda granular)
    ok_count = 0
    for m in MILESTONES:
        key = f"horizon-milestone-{m['id']}"
        value = (
            f"horizon: {HORIZON_KEY} | id: {m['id']} | name: {m['name']} | "
            f"criteria: {m['criteria']} | due: {m['estimated_due']} | "
            f"status: {m['status']} | blocks: {','.join(m['blocks']) or 'none'}"
        )
        print(f"[horizon] storing {key} ({len(value)} chars)...")
        if store(key, value, "horizons"):
            ok_count += 1

    total = len(MILESTONES) + 1
    done = ok_count + (1 if ok_main else 0)
    print(f"[horizon] hecho: {done}/{total} entradas en namespace 'horizons'")
    print(f"[horizon] target_date: {TARGET_DATE}")
    print("[horizon] AVISO: target_date es tentativo. Ajustar cuando se confirme fecha defensa.")
    return 0 if done == total else 1


if __name__ == "__main__":
    sys.exit(main())
