"""
scripts/swarm_regulatory_validator.py — CAL-24 Swarm validador regulatorio
============================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0 + 4.1 + 4.2

Valida coherencia regulatoria entre codigo (scenarios/), ADRs y
resoluciones CREG mediante 3 agentes especializados:

  - CREG174Validator     -> C1 (Excedentes Tipo 1/2 + Cvm,i,j puro)
  - CREG101072Validator  -> C4 (Decreto 2236 + PDE + herencia CREG 174)
  - CREG101066Validator  -> C3 (Techo PES sobre pi_bolsa)

Modos:
  --mode local  (default): heuristicas estaticas, ~1s, deterministico.
  --mode swarm           : MCP claude-flow swarm_init + agent_spawn,
                           requiere MCP activo (graceful degradation
                           a `local` si MCP no responde).

Referencia: docs/adr/0024-cal24-swarm-validador-regulatorio.md
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _wrap_stdout_utf8():
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                       encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer,
                                       encoding="utf-8", errors="replace")


# ─── Estructura de resultado ────────────────────────────────────────────────


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class AgentVerdict:
    agent: str
    family: str   # familia CREG
    scenario: str
    checks: list[Check] = field(default_factory=list)

    @property
    def n_passed(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def n_total(self) -> int:
        return len(self.checks)

    @property
    def verdict(self) -> str:
        if self.n_total == 0:
            return "EMPTY"
        if self.n_passed == self.n_total:
            return "PASS"
        if self.n_passed >= self.n_total * 0.7:
            return "PARCIAL"
        return "FAIL"

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "family": self.family,
            "scenario": self.scenario,
            "verdict": self.verdict,
            "n_passed": self.n_passed,
            "n_total": self.n_total,
            "checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail}
                for c in self.checks
            ],
        }


# ─── Helpers de validacion ──────────────────────────────────────────────────


def _file_contains(path: Path, patterns: list[str | re.Pattern]) -> dict:
    """Devuelve dict {pattern: True/False} con presencia de cada patron."""
    if not path.exists():
        return {str(p): False for p in patterns}
    text = path.read_text(encoding="utf-8", errors="replace")
    out = {}
    for p in patterns:
        if isinstance(p, re.Pattern):
            out[p.pattern] = bool(p.search(text))
        else:
            out[p] = p in text
    return out


def _adr_estado(adr_filename: str, root: Path = ROOT) -> str | None:
    """Lee el estado del ADR desde el frontmatter / primera línea con `Estado:`."""
    p = root / "docs" / "adr" / adr_filename
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\*\*Estado:\*\*\s*([A-Za-z]+)", text)
    return m.group(1) if m else None


# ─── Agentes especializados ─────────────────────────────────────────────────


def validate_creg_174(root: Path = ROOT) -> AgentVerdict:
    """C1 — CREG 174/2021 art. 22-25 (Excedentes Tipo 1/Tipo 2)."""
    v = AgentVerdict(
        agent="CREG174Validator",
        family="CREG 174/2021",
        scenario="C1",
    )

    code = root / "scenarios" / "scenario_c1_creg174.py"
    code_checks = _file_contains(code, [
        "Tipo 1", "Tipo 2",
        re.compile(r"[Cc]vm|component_c|componente.?[Cc]"),
        re.compile(r"month_labels|period|mensual"),
        re.compile(r"pi_gs\s*-\s*[Cc]vm|pi_gs\s*-\s*c_arr|pi_gs\s*-\s*c\["),
    ])
    v.checks.append(Check("scenario_c1 implementa Excedentes Tipo 1",
                           code_checks["Tipo 1"]))
    v.checks.append(Check("scenario_c1 implementa Excedentes Tipo 2",
                           code_checks["Tipo 2"]))
    v.checks.append(Check("scenario_c1 menciona componente Cvm/component_c (CREG 119/2007 art. 11)",
                           code_checks[r"[Cc]vm|component_c|componente.?[Cc]"]))
    v.checks.append(Check("scenario_c1 implementa balance mensual (period/month_labels)",
                           code_checks[r"month_labels|period|mensual"]))
    v.checks.append(Check("ADR-0010 (CAL-10) Accepted",
                           _adr_estado("0010-cal10-creg174-tipo-1-2-componente-c.md")
                           == "Accepted"))
    return v


def validate_creg_101072(root: Path = ROOT) -> AgentVerdict:
    """C4 — Decreto 2236/2023 + CREG 101 072/2025 (Comunidades Energéticas)."""
    v = AgentVerdict(
        agent="CREG101072Validator",
        family="Decreto 2236/2023 + CREG 101 072/2025",
        scenario="C4",
    )

    code = root / "scenarios" / "scenario_c4_creg101072.py"
    code_checks = _file_contains(code, [
        "PDE", "Tipo 1", "Tipo 2",
        re.compile(r"pi_gs\s*-\s*[Cc]vm|cvm"),
        re.compile(r"pi_bolsa|bolsa"),
    ])
    v.checks.append(Check("scenario_c4 implementa PDE (Porcentaje Distribución Excedentes)",
                           code_checks["PDE"]))
    v.checks.append(Check("scenario_c4 distingue Tipo 1 (intracomunitaria)",
                           code_checks["Tipo 1"]))
    v.checks.append(Check("scenario_c4 distingue Tipo 2 (residual a bolsa)",
                           code_checks["Tipo 2"]))
    v.checks.append(Check("scenario_c4 hereda Cvm,i,j de CREG 174 art. 25",
                           code_checks[r"pi_gs\s*-\s*[Cc]vm|cvm"]))
    v.checks.append(Check("ADR-0015 (CAL-15) Accepted",
                           _adr_estado("0015-cal15-c4-creg101072-tipo-1-2-cvm.md")
                           == "Accepted"))
    return v


def validate_creg_101066(root: Path = ROOT) -> AgentVerdict:
    """C3 — CREG 101 066/2024 (Techo PES sobre PTB)."""
    v = AgentVerdict(
        agent="CREG101066Validator",
        family="CREG 101 066/2024",
        scenario="C3",
    )

    xm_prices = root / "data" / "xm_prices.py"
    csv = root / "data" / "precios_escasez_creg.csv"
    code_checks = _file_contains(xm_prices, [
        "apply_creg101066_ceiling",
        "load_creg_ceiling",
        re.compile(r"apply_ceiling\s*=\s*True"),
    ])
    v.checks.append(Check("xm_prices.py define apply_creg101066_ceiling",
                           code_checks["apply_creg101066_ceiling"]))
    v.checks.append(Check("xm_prices.py define load_creg_ceiling",
                           code_checks["load_creg_ceiling"]))
    v.checks.append(Check("get_pi_bolsa default apply_ceiling=True",
                           code_checks[r"apply_ceiling\s*=\s*True"]))
    v.checks.append(Check("CSV precios_escasez_creg.csv cargado (>=7 meses)",
                           csv.exists() and len(csv.read_text(encoding="utf-8")
                                                   .strip().splitlines()) >= 8))
    v.checks.append(Check("ADR-0014 (CAL-14) Accepted",
                           _adr_estado("0014-cal14-creg101066-pes-ceiling.md")
                           == "Accepted"))
    return v


# ─── Orquestador ────────────────────────────────────────────────────────────


def run_all_local(root: Path = ROOT) -> list[AgentVerdict]:
    return [
        validate_creg_174(root),
        validate_creg_101072(root),
        validate_creg_101066(root),
    ]


def aggregate_verdict(verdicts: list[AgentVerdict]) -> str:
    if not verdicts:
        return "EMPTY"
    individuals = [v.verdict for v in verdicts]
    if all(i == "PASS" for i in individuals):
        return "PASS"
    if any(i == "FAIL" for i in individuals):
        return "FAIL"
    return "PARCIAL"


def print_report(verdicts: list[AgentVerdict],
                  json_only: bool = False) -> None:
    if json_only:
        out = {
            "verdicts": [v.to_dict() for v in verdicts],
            "aggregate": aggregate_verdict(verdicts),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    print("=" * 78)
    print(" CAL-24 — Validador regulatorio swarm (modo local)")
    print("=" * 78)
    for v in verdicts:
        print(f"  {v.agent:22s} {v.verdict:8s} ({v.n_passed}/{v.n_total} checks)")
        for c in v.checks:
            mark = "✓" if c.passed else "✗"
            print(f"        {mark} {c.name}")
            if not c.passed and c.detail:
                print(f"           {c.detail}")
        print()
    print(f"  Veredicto agregado: {aggregate_verdict(verdicts)}")
    print("=" * 78)


# ─── Modo swarm (MCP, opcional) ─────────────────────────────────────────────


def run_swarm_mode() -> int:
    """Stub para invocar MCP claude-flow. En produccion usaria el MCP real;
    aqui hace graceful degradation a modo local."""
    try:
        # Si el MCP estuviera disponible se invocarian:
        #   mcp__claude_flow__swarm_init({"topology": "mesh", "maxAgents": 3})
        #   mcp__claude_flow__agent_spawn({"agentType": "researcher", ...})
        # Como este script corre standalone Python, no tiene acceso a esos MCPs.
        # En la sesion Claude se invocarian directamente; aqui caemos a local.
        print("  [CAL-24] modo swarm requiere MCP claude-flow activo en sesion Claude.")
        print("  [CAL-24] graceful degradation -> modo local")
        verdicts = run_all_local()
        print_report(verdicts)
        return 0 if aggregate_verdict(verdicts) == "PASS" else 1
    except Exception as e:
        print(f"  [CAL-24] Error en swarm: {e}; cayendo a local")
        verdicts = run_all_local()
        print_report(verdicts)
        return 0 if aggregate_verdict(verdicts) == "PASS" else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("local", "swarm"), default="local")
    ap.add_argument("--json-only", action="store_true",
                    help="Solo emite JSON a stdout, sin reporte humano.")
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1 si veredicto agregado != PASS.")
    args = ap.parse_args()

    if args.mode == "swarm":
        return run_swarm_mode()

    verdicts = run_all_local()
    print_report(verdicts, json_only=args.json_only)
    if args.strict and aggregate_verdict(verdicts) != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    _wrap_stdout_utf8()
    sys.exit(main())
