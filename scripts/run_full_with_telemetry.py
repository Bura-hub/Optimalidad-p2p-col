"""
scripts/run_full_with_telemetry.py — D3 Telemetría estructurada de --full
==========================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Wrapper de `main_simulation.py --data real --full --analysis` que
captura eventos estructurados (JSON Lines) en `outputs/telemetry/` y
preserva el log completo para auditoría posterior.

Eventos capturados (uno por línea JSONL):

  - phase_start: cada `[N/5]` del pipeline (carga MTE, P2P, escenarios,
    reporte, exportación).
  - ceiling_applied: bloque `[creg-101-066]` con horas recortadas y
    delta acumulado.
  - cal16_decomposition: línea `[CAL-16] C2 descompuesto: ...` con
    componentes G, Cvm, COT, MEM y pi_upper.
  - monthly_metric: filas del reporte mensual con net_benefit por
    escenario.
  - p2p_summary: línea de cierre P2P con horas activas y kWh totales.
  - completion: `✓ Completado en Ns` con tiempo total.
  - error: cualquier traceback Python detectado.

Uso:
  python scripts/run_full_with_telemetry.py
  python scripts/run_full_with_telemetry.py --tag "post-cal24"
  python scripts/run_full_with_telemetry.py --dry-run  # parser sobre log existente
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TELEMETRY_DIR = ROOT / "outputs" / "telemetry"


def _wrap_stdout_utf8():
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                       encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer,
                                       encoding="utf-8", errors="replace")


# ─── Patrones de eventos ────────────────────────────────────────────────────

RE_PHASE = re.compile(r"^\[(\d+)/5\]\s+(.*?)\.\.\.")
RE_CEILING = re.compile(
    r"\[creg-101-066\]\s+Techo\s+(PEI|PE|PES)\s+aplicado:\s+(\d+)\s+horas\s+recortadas"
    r"\s+\(([0-9.]+)%\s+del\s+horizonte\),\s+delta\s+=\s+([0-9,]+)"
)
RE_CAL16 = re.compile(
    r"\[CAL-16\]\s+C2\s+descompuesto:.*?G[≈=]?\s*([0-9.]+)\s+Cvm[≈=]?\s*([0-9.]+)"
    r"\s+α·COT[≈=]?\s*([0-9.]+).*?MEM[≈=]?\s*([0-9.]+)\s+→\s+pi_upper[≈=]?\s*([0-9.]+)"
)
RE_MONTHLY = re.compile(
    r"^\s*([A-Z][a-z]+\s+\d{4})\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)"
    r"\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*$"
)
RE_COMPLETION = re.compile(r"✓?\s*Completado\s+en\s+([0-9.]+)\s*s")
RE_HORAS_MERCADO = re.compile(r"horas\s+mercado:\s+(\d+)/(\d+).*?([0-9.]+)\s+kWh\s+P2P")
RE_TRACEBACK = re.compile(r"^Traceback\s+\(most recent call last\):")


# ─── Parser ─────────────────────────────────────────────────────────────────

def parse_line(line: str, ts: str) -> dict | None:
    """Devuelve dict de evento si la línea coincide con un patrón conocido."""
    line = line.rstrip("\r\n")

    m = RE_PHASE.search(line)
    if m:
        return {"ts": ts, "event": "phase_start",
                "phase": int(m.group(1)),
                "label": m.group(2).strip()}

    m = RE_CEILING.search(line)
    if m:
        return {"ts": ts, "event": "ceiling_applied",
                "level": m.group(1),
                "hours_capped": int(m.group(2)),
                "fraction_pct": float(m.group(3)),
                "delta_cop_kwh_total": int(m.group(4).replace(",", ""))}

    m = RE_CAL16.search(line)
    if m:
        return {"ts": ts, "event": "cal16_decomposition",
                "g_mean": float(m.group(1)),
                "cvm_mean": float(m.group(2)),
                "cot_alpha_mean": float(m.group(3)),
                "mem_mean": float(m.group(4)),
                "pi_upper": float(m.group(5))}

    m = RE_MONTHLY.match(line)
    if m:
        return {"ts": ts, "event": "monthly_metric",
                "mes": m.group(1),
                "P2P": int(m.group(2).replace(",", "")),
                "C1":  int(m.group(3).replace(",", "")),
                "C3":  int(m.group(4).replace(",", "")),
                "C4":  int(m.group(5).replace(",", "")),
                "IE_P2P": float(m.group(6)),
                "PS_pct": float(m.group(7)),
                "PSR_pct": float(m.group(8)),
                "kWh_P2P": float(m.group(9))}

    m = RE_HORAS_MERCADO.search(line)
    if m:
        return {"ts": ts, "event": "p2p_summary",
                "horas_activas": int(m.group(1)),
                "horas_total": int(m.group(2)),
                "kwh_p2p_total": float(m.group(3))}

    m = RE_COMPLETION.search(line)
    if m:
        return {"ts": ts, "event": "completion",
                "elapsed_s": float(m.group(1))}

    if RE_TRACEBACK.match(line):
        return {"ts": ts, "event": "error", "first_line": line}

    return None


# ─── Wrapper ────────────────────────────────────────────────────────────────

def stream_simulation(cmd: list[str], jsonl_path: Path,
                      log_path: Path) -> int:
    """Ejecuta el subprocess y emite JSONL en tiempo real."""
    print(f"  [D3] cmd: {' '.join(cmd)}")
    print(f"  [D3] JSONL -> {jsonl_path}")
    print(f"  [D3] log   -> {log_path}")

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    n_events = 0
    with jsonl_path.open("w", encoding="utf-8") as jf, \
         log_path.open("w", encoding="utf-8") as lf:
        # Banner inicial
        start_event = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "event": "run_start",
            "cmd": cmd,
        }
        jf.write(json.dumps(start_event, ensure_ascii=False) + "\n")
        n_events += 1

        for line in proc.stdout:
            lf.write(line)
            ts = datetime.now().isoformat(timespec="seconds")
            ev = parse_line(line, ts)
            if ev:
                jf.write(json.dumps(ev, ensure_ascii=False) + "\n")
                jf.flush()
                n_events += 1

        proc.wait()
        end_event = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "event": "run_end",
            "exit_code": proc.returncode,
            "n_events": n_events + 1,
        }
        jf.write(json.dumps(end_event, ensure_ascii=False) + "\n")

    print(f"  [D3] Eventos JSONL emitidos: {n_events}")
    print(f"  [D3] Exit code: {proc.returncode}")
    return proc.returncode


def replay_log(log_path: Path, jsonl_path: Path) -> int:
    """Modo --dry-run: parsea un log existente sin correr la simulacion."""
    if not log_path.exists():
        print(f"  [D3] No existe {log_path}", file=sys.stderr)
        return 1
    n_events = 0
    with log_path.open("r", encoding="utf-8", errors="replace") as lf, \
         jsonl_path.open("w", encoding="utf-8") as jf:
        for line in lf:
            ts = datetime.now().isoformat(timespec="seconds")
            ev = parse_line(line, ts)
            if ev:
                jf.write(json.dumps(ev, ensure_ascii=False) + "\n")
                n_events += 1
    print(f"  [D3] (dry-run) Eventos extraidos: {n_events}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", default="",
                    help="Tag opcional (e.g. 'post-cal24').")
    ap.add_argument("--dry-run", default="",
                    help="Path a un log existente; parsea sin correr la simulacion.")
    ap.add_argument("--full-args", default="--data real --full --analysis",
                    help="Argumentos para main_simulation (default --data real --full --analysis).")
    args = ap.parse_args()

    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
    suffix = args.tag or datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = TELEMETRY_DIR / f"telemetry_{suffix}.jsonl"
    log_path = TELEMETRY_DIR / f"log_{suffix}.txt"

    if args.dry_run:
        return replay_log(Path(args.dry_run), jsonl_path)

    cmd = [sys.executable, str(ROOT / "main_simulation.py")] + \
          args.full_args.split()
    return stream_simulation(cmd, jsonl_path, log_path)


if __name__ == "__main__":
    _wrap_stdout_utf8()
    sys.exit(main())
