"""
run_smoke_campaign.py — Orquestador de la campaña de smokes del núcleo P2P
===========================================================================
ADR-0038 · plan 2026-06-10. Ejecuta los 4 ejes por tiers de costo:

  --tier 0  (local, <5 min)   pytest: flags opt-in + fixtures extremos +
                              monotonía corta.
  --tier 1  (~30-45 min)      SYN completo: R1-R5, C1-C5 (C2 todas las horas
                              sintéticas), P1-P3, S1-S4, A2-SYN. Genera el
                              oráculo sintético si falta.
  --tier 2  (~3-6 h)          COB-M1 horizonte completo: R1-R6, C1-real,
                              C2 TODAS las horas activas, C5, P3-P5, A2;
                              ago-2025: S2, S3, S6. Genera oráculo real.
  --tier 3  (overnight)       COB-M3 horizonte completo: R1-R6, C2 todas
                              las horas activas, C5, P3-P5.

  --only {reparto,equivalencia,precios,solver}   restringe el eje.

Reporte consolidado: outputs/smoke_campaign_report.md (acumulativo entre
tiers, fuente outputs/smoke_campaign_results.json). Exit 1 si cualquier
verificación HARD falla en el tier ejecutado.

Servidor (SERVER_SETUP.md):
  tmux new -s smokes && source .venv/bin/activate && source env.sh
  python scripts/run_smoke_campaign.py --tier N 2>&1 | tee outputs/smoke_tierN.log
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

from smoke_common import (
    ROOT, CheckResult, save_results, hard_failures, setup_stdout_utf8,
)

REF_SYN  = os.path.join(ROOT, "Documentos", "copy", "reference_syn24.json")
REF_REAL = os.path.join(ROOT, "Documentos", "copy",
                        "reference_real_sample.json")


def _ensure_oracle(real: bool) -> None:
    if not os.path.exists(REF_SYN):
        print("  [oráculo] generando referencia sintética…")
        subprocess.run([sys.executable,
                        os.path.join(ROOT, "scripts",
                                     "generate_reference_oracle.py")],
                       check=False, cwd=ROOT)
    if real and not os.path.exists(REF_REAL):
        print("  [oráculo] generando muestra real…")
        subprocess.run([sys.executable,
                        os.path.join(ROOT, "scripts",
                                     "generate_reference_oracle.py"),
                        "--real"],
                       check=False, cwd=ROOT)


def tier0() -> list:
    t0 = time.time()
    files = ["tests/test_core_optin_flags.py",
             "tests/test_smoke_fixtures_extremos.py",
             "tests/test_price_monotonicity_in_imbalance.py"]
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *files, "-q",
         "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=ROOT)
    tail = (proc.stdout or "").strip().splitlines()[-1:]
    return [CheckResult("T0", "tier0", "pytest",
                        "flags opt-in + fixtures + monotonía corta",
                        " ".join(tail), "todos pass",
                        "PASS" if proc.returncode == 0 else "FAIL",
                        0, time.time() - t0,
                        detail="" if proc.returncode == 0
                        else proc.stdout[-2000:])]


def run_tier(tier: int, only: str | None) -> list:
    import smoke_settlement
    import smoke_equivalence
    import smoke_price_dynamics
    import smoke_solver_robustness

    rows = []
    if tier == 0:
        return tier0()

    if tier == 1:
        _ensure_oracle(real=False)
        ds = ["SYN"]
        if only in (None, "reparto"):
            rows += smoke_settlement.run_checks(1, ds)
        if only in (None, "equivalencia"):
            rows += smoke_equivalence.run_checks(1, ds, c2_all=True)
        if only in (None, "precios"):
            rows += smoke_price_dynamics.run_checks(1, ds)
        if only in (None, "solver"):
            rows += smoke_solver_robustness.run_checks(1, ds)
    elif tier == 2:
        _ensure_oracle(real=True)
        if only in (None, "reparto"):
            rows += smoke_settlement.run_checks(2, ["COB-M1"])
        if only in (None, "equivalencia"):
            rows += smoke_equivalence.run_checks(2, ["COB-M1"], c2_all=True)
        if only in (None, "precios"):
            rows += smoke_price_dynamics.run_checks(2, ["COB-M1"])
        if only in (None, "solver"):
            rows += smoke_solver_robustness.run_checks(
                2, ["ago-2025", "COB-M1"])
    elif tier == 3:
        if only in (None, "reparto"):
            rows += smoke_settlement.run_checks(3, ["COB-M3"])
        if only in (None, "equivalencia"):
            rows += smoke_equivalence.run_checks(3, ["COB-M3"], c2_all=True)
        if only in (None, "precios"):
            rows += smoke_price_dynamics.run_checks(3, ["COB-M3"])
        if only in (None, "solver"):
            rows += smoke_solver_robustness.run_checks(3, ["COB-M3"])
    else:
        raise SystemExit(f"tier {tier} desconocido")
    return rows


def main():
    setup_stdout_utf8()
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", type=int, required=True, choices=[0, 1, 2, 3])
    ap.add_argument("--only", choices=["reparto", "equivalencia",
                                       "precios", "solver"])
    args = ap.parse_args()

    t0 = time.time()
    print(f"\n{'='*70}\nCAMPAÑA DE SMOKES — tier {args.tier}"
          + (f" (solo {args.only})" if args.only else "")
          + f"\n{'='*70}")
    rows = run_tier(args.tier, args.only)
    save_results(rows, args.tier)

    fails = hard_failures(rows)
    warns = [r for r in rows if r.verdict == "WARN"]
    print(f"\n{'='*70}")
    print(f"RESULTADO tier {args.tier}: {len(rows)} checks | "
          f"{sum(1 for r in rows if r.verdict == 'PASS')} PASS | "
          f"{len(warns)} WARN | {len(fails)} FAIL | "
          f"{sum(1 for r in rows if r.verdict == 'INFO')} INFO | "
          f"{sum(1 for r in rows if r.verdict == 'SKIP')} SKIP")
    print(f"Tiempo total: {time.time()-t0:.0f}s")
    print(f"Reporte: outputs/smoke_campaign_report.md")
    for r in fails:
        print(f"  ✗ FAIL {r.id} [{r.datos}]: {r.metric} = {r.value}")
    for r in warns:
        print(f"  ◯ WARN {r.id} [{r.datos}]: {r.metric} = {r.value}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
