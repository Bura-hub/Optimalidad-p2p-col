"""
scripts/check_cal_consistency.py — F2 detector de inconsistencias CAL-N
========================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Verifica la consistencia de las referencias CAL-N (calibración numerada)
en todo el repositorio contra la fuente de verdad `docs/adr/README.md`.

Detecta tres tipos de issue:

1. **Huérfanos**: un CAL-N citado en código/docs/CSV pero sin ADR
   correspondiente en `docs/adr/`. Ejemplo histórico: CAL-15 vs CAL-17
   (Sprint 1.1 hallazgo).
2. **No citados**: un ADR existe pero ningún archivo lo referencia
   (puede ser válido si el ADR es nuevo).
3. **Conflictos de numeración**: el mismo CAL-N aparece en múltiples
   archivos ADR (caso conocido: CAL-15 y CAL-16 ambos como slug `0011`).

Uso:
  python scripts/check_cal_consistency.py
  python scripts/check_cal_consistency.py --strict        # exit code 1 si hay issues
  python scripts/check_cal_consistency.py --root <path>   # custom root

Salida: tabla en consola + JSON estructurado en stderr para CI.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

def _wrap_stdout_utf8():
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                       encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer,
                                       encoding="utf-8", errors="replace")

# Regex globales
RE_CAL_REF = re.compile(r"\bCAL[-‑–](\d{1,3})\b")  # CAL-N en cualquier texto
RE_ADR_FILENAME = re.compile(r"^(\d{4})-cal(\d{1,3})-", re.IGNORECASE)
RE_README_TABLE_ROW = re.compile(
    r"^\|\s*(\d{4}\*?)\s*\|\s*CAL[-‑–](\d{1,3})\s*:", re.MULTILINE
)

# Extensiones a escanear (solo texto)
SCAN_EXTS = {".py", ".md", ".csv", ".txt", ".rst", ".yaml", ".yml"}
EXCLUDE_DIRS = {".venv", "__pycache__", ".git", "node_modules",
                 ".pytest_cache", ".mypy_cache", ".ruff_cache",
                 ".worktrees", "MedicionesMTE",
                 "MedicionesMTE_v3", "outputs", ".vscode", ".idea"}


def find_adr_dir(root: Path) -> Path:
    p = root / "docs" / "adr"
    if not p.is_dir():
        raise FileNotFoundError(f"No existe {p}; este repo no tiene ADRs?")
    return p


def parse_adr_readme(adr_dir: Path) -> tuple[dict[int, str], set[int]]:
    """
    Devuelve:
      - known_cals: dict {N: adr_id (ej '0019')} desde la tabla.
      - mentioned_cals: set {N, ...} desde TODO el README (incluye notas).
    """
    readme = adr_dir / "README.md"
    if not readme.exists():
        raise FileNotFoundError(readme)
    text = readme.read_text(encoding="utf-8")

    known: dict[int, str] = {}
    for m in RE_README_TABLE_ROW.finditer(text):
        adr_id, n = m.group(1), int(m.group(2))
        # Si CAL-N aparece en multiples filas, conservar la mas alta (Accepted reciente)
        known[n] = adr_id

    mentioned = {int(m.group(1)) for m in RE_CAL_REF.finditer(text)}
    return known, mentioned


def parse_adr_filenames(adr_dir: Path) -> dict[int, list[Path]]:
    """Mapea CAL-N a lista de archivos ADR con ese numero en el slug."""
    out: dict[int, list[Path]] = defaultdict(list)
    for adr in sorted(adr_dir.glob("0*.md")):
        m = RE_ADR_FILENAME.match(adr.name)
        if m:
            n = int(m.group(2))
            out[n].append(adr)
    return out


def scan_repo_references(root: Path,
                          excluded_files: set[Path] | None = None
                          ) -> dict[int, list[tuple[Path, int]]]:
    """
    Escanea todo el repo buscando referencias CAL-N.
    Devuelve {N: [(file, line_number), ...]}.
    """
    excluded_files = excluded_files or set()
    refs: dict[int, list[tuple[Path, int]]] = defaultdict(list)
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SCAN_EXTS:
            continue
        # Skip excluded dirs
        try:
            rel_parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in EXCLUDE_DIRS for part in rel_parts):
            continue
        if path in excluded_files:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            for m in RE_CAL_REF.finditer(line):
                refs[int(m.group(1))].append((path, ln))
    return refs


def detect_issues(known_cals: dict[int, str],
                   mentioned_cals: set[int],
                   adr_filenames: dict[int, list[Path]],
                   refs: dict[int, list[tuple[Path, int]]],
                   root: Path) -> dict:
    """Detecta huérfanos, no citados y conflictos."""
    referenced = set(refs.keys())
    documented = set(known_cals.keys()) | set(adr_filenames.keys()) | mentioned_cals

    huerfanos = sorted(referenced - documented)
    no_citados = sorted(set(known_cals.keys()) - referenced)
    conflictos = {n: [str(p.relative_to(root)) for p in paths]
                   for n, paths in adr_filenames.items()
                   if len(paths) > 1}

    # ADRs en filename pero sin entrada en tabla README (post-mortem CAL-17 case)
    no_en_readme = sorted(set(adr_filenames.keys()) - set(known_cals.keys()))

    return {
        "huerfanos": [
            {"cal": n, "refs": [{"file": str(p.relative_to(root)),
                                  "line": ln}
                                 for p, ln in refs[n][:5]]}
            for n in huerfanos
        ],
        "no_citados": no_citados,
        "no_en_readme": no_en_readme,
        "conflictos_slug": conflictos,
        "summary": {
            "total_known_in_table": len(known_cals),
            "total_referenced": len(referenced),
            "total_files_with_adr": len(adr_filenames),
            "huerfanos_count": len(huerfanos),
            "no_citados_count": len(no_citados),
            "conflictos_count": len(conflictos),
            "no_en_readme_count": len(no_en_readme),
        },
    }


def print_human_report(issues: dict) -> None:
    s = issues["summary"]
    print()
    print("=" * 78)
    print(" F2 - Verificacion de consistencia CAL-N")
    print("=" * 78)
    print(f"  ADRs en tabla README: {s['total_known_in_table']}")
    print(f"  Archivos ADR (.md):    {s['total_files_with_adr']}")
    print(f"  CAL-N referenciados:   {s['total_referenced']}")
    print()

    if issues["huerfanos"]:
        print(f"  [!] HUERFANOS ({s['huerfanos_count']}): "
              f"citados pero sin ADR")
        for h in issues["huerfanos"]:
            print(f"      CAL-{h['cal']}:")
            for r in h["refs"]:
                print(f"        {r['file']}:{r['line']}")
        print()
    else:
        print("  [OK] Sin huerfanos: todos los CAL-N citados existen.")

    if issues["conflictos_slug"]:
        print(f"  [!] CONFLICTOS DE SLUG ({s['conflictos_count']}): "
              f"mismo CAL-N en multiples ADRs")
        for n, paths in issues["conflictos_slug"].items():
            print(f"      CAL-{n}:")
            for p in paths:
                print(f"        {p}")
        print()
    else:
        print("  [OK] Sin conflictos de slug.")

    if issues["no_en_readme"]:
        print(f"  [!] ADRs SIN ENTRADA EN README ({s['no_en_readme_count']}):")
        for n in issues["no_en_readme"]:
            print(f"      CAL-{n}")
        print()
    else:
        print("  [OK] Todos los ADRs tienen fila en README.")

    if issues["no_citados"]:
        print(f"  [.] ADRs no citados en repo ({s['no_citados_count']}): "
              f"no es un error pero puede ser señal de ADR muerto")
        for n in issues["no_citados"]:
            print(f"      CAL-{n}")
        print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1 si hay huerfanos, conflictos o ADRs sin README.")
    ap.add_argument("--json-only", action="store_true",
                    help="Solo emite JSON a stdout, sin reporte humano.")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    adr_dir = find_adr_dir(root)
    known, mentioned = parse_adr_readme(adr_dir)
    filenames = parse_adr_filenames(adr_dir)
    refs = scan_repo_references(root)
    issues = detect_issues(known, mentioned, filenames, refs, root)

    if args.json_only:
        print(json.dumps(issues, indent=2, ensure_ascii=False))
    else:
        print_human_report(issues)
        # JSON tambien a stderr para CI/agentes
        print(json.dumps(issues, ensure_ascii=False), file=sys.stderr)

    if args.strict:
        s = issues["summary"]
        if (s["huerfanos_count"] or s["conflictos_count"]
                or s["no_en_readme_count"]):
            return 1
    return 0


if __name__ == "__main__":
    _wrap_stdout_utf8()
    sys.exit(main())
