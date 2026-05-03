"""
scripts/check_scenario_duplication.py — F1 detector duplicación entre escenarios
==================================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Detecta código casi-idéntico entre las funciones públicas de
`scenarios/scenario_c*.py` mediante similitud de secuencias sobre AST
normalizado (variables renombradas, docstrings/comentarios removidos).

Útil para identificar oportunidades de refactor a `scenarios/_common.py`
donde el mismo bloque (e.g. autoconsumo, settlement de excedentes) se
duplica entre C1, C2, C3, C4.

Uso:
  python scripts/check_scenario_duplication.py
  python scripts/check_scenario_duplication.py --threshold 0.85
  python scripts/check_scenario_duplication.py --pattern "scenarios/scenario_c*.py"

Salida: pares de funciones ordenados por similitud descendente.
"""
from __future__ import annotations

import argparse
import ast
import io
import sys
from difflib import SequenceMatcher
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                   encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer,
                                   encoding="utf-8", errors="replace")

DEFAULT_THRESHOLD = 0.85
DEFAULT_PATTERN = "scenarios/scenario_c*.py"


def normalize_ast(node: ast.AST) -> str:
    """
    Convierte un nodo AST a cadena normalizada:
      - sin variables locales especificas (renombradas a v0, v1, ...)
      - sin docstrings ni comentarios
      - sin literales numericos (reemplazados por NUM)
    Esto hace que dos funciones con la misma estructura pero distintos
    nombres de variables se vean iguales.
    """
    cleaned = ast.parse("")
    cleaned.body = [_strip(node)]
    # Renombrado: caminamos por todos los Name() y Arguments() y los
    # reemplazamos por placeholders ordinales.
    name_map: dict[str, str] = {}

    def map_name(n: str) -> str:
        if n not in name_map:
            name_map[n] = f"v{len(name_map)}"
        return name_map[n]

    for node_walk in ast.walk(cleaned):
        # Renombrar variables locales (no funciones builtin / atributos)
        if isinstance(node_walk, ast.Name):
            node_walk.id = map_name(node_walk.id)
        elif isinstance(node_walk, ast.arg):
            node_walk.arg = map_name(node_walk.arg)
        elif isinstance(node_walk, ast.Constant):
            # Reemplazar literales numericos / strings por placeholder
            if isinstance(node_walk.value, (int, float)):
                node_walk.value = 0
            elif isinstance(node_walk.value, str):
                node_walk.value = ""
    return ast.dump(cleaned, annotate_fields=False)


def _strip(node: ast.AST) -> ast.AST:
    """Remueve docstring (primera Expression Constant) si existe."""
    if hasattr(node, "body") and node.body:
        first = node.body[0]
        if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            node.body = node.body[1:]
    return node


def extract_functions(path: Path) -> list[tuple[str, str, int]]:
    """
    Extrae funciones top-level del archivo. Devuelve lista de tuplas
    (nombre_funcion, ast_normalizado, lineno).
    """
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    out: list[tuple[str, str, int]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Saltamos funciones triviales (< 10 lineas)
            if (node.end_lineno or node.lineno) - node.lineno < 10:
                continue
            normalized = normalize_ast(node)
            out.append((node.name, normalized, node.lineno))
    return out


def similarity(a: str, b: str) -> float:
    """Similitud SequenceMatcher entre dos cadenas (0..1)."""
    return SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def pairwise_compare(funcs: list[tuple[Path, str, str, int]],
                      threshold: float) -> list[dict]:
    """
    Compara todas las funciones entre archivos distintos.
    Devuelve pares con similarity >= threshold.
    """
    pairs: list[dict] = []
    n = len(funcs)
    for i in range(n):
        for j in range(i + 1, n):
            f_a, n_a, code_a, ln_a = funcs[i]
            f_b, n_b, code_b, ln_b = funcs[j]
            # Solo comparar entre archivos distintos
            if f_a == f_b:
                continue
            sim = similarity(code_a, code_b)
            if sim >= threshold:
                pairs.append({
                    "file_a": str(f_a),
                    "func_a": n_a,
                    "line_a": ln_a,
                    "file_b": str(f_b),
                    "func_b": n_b,
                    "line_b": ln_b,
                    "similarity": round(sim, 4),
                })
    pairs.sort(key=lambda p: -p["similarity"])
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",
                    default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--pattern", default=DEFAULT_PATTERN,
                    help="Glob para archivos a comparar (default scenarios/scenario_c*.py)")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help=f"Similarity minima [0,1] (default {DEFAULT_THRESHOLD})")
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1 si hay pares por encima del umbral.")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    paths = sorted(root.glob(args.pattern))
    if not paths:
        print(f"[!] Ningun archivo coincide con {args.pattern}",
              file=sys.stderr)
        return 1

    print(f"  [F1] Analizando {len(paths)} archivos:")
    for p in paths:
        print(f"        {p.relative_to(root)}")
    print(f"  [F1] threshold = {args.threshold}")

    funcs: list[tuple[Path, str, str, int]] = []
    for p in paths:
        for name, code, lineno in extract_functions(p):
            funcs.append((p.relative_to(root), name, code, lineno))

    print(f"  [F1] funciones top-level >= 10 lineas: {len(funcs)}")
    pairs = pairwise_compare(funcs, args.threshold)

    print()
    print("=" * 78)
    print(f" F1 - Pares de funciones similares (>= {args.threshold})")
    print("=" * 78)

    if not pairs:
        print("  [OK] No hay duplicacion por encima del umbral.")
        return 0

    print(f"  Encontrados {len(pairs)} pares:")
    print()
    for p in pairs:
        print(f"  {p['similarity']:.3f}  "
              f"{p['file_a']}:{p['line_a']}::{p['func_a']}  <->  "
              f"{p['file_b']}:{p['line_b']}::{p['func_b']}")

    if args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
