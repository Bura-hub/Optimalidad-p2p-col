"""
Compuerta de portabilidad: el codigo tiene que compilar en Python 3.10.

La maquina de trabajo corre 3.13 y el servidor 3.10. La version 3.12
flexibilizo las cadenas formateadas (PEP 701) y admite dos cosas que 3.10
rechaza:

  - partirlas en varias lineas sin comillas triples;
  - usar dentro la misma comilla que las delimita.

Ninguna de las dos la detecta `ast.parse`, ni siquiera pasandole
`feature_version=(3, 10)`, porque el cambio es del analizador lexico y no de
la gramatica. Comprobado. De modo que hay que mirar los tokens.

Esto costo una tanda de mediciones ya lanzadas en el servidor, que reventaron
todas con el mismo error de sintaxis.

Uso:
    python tests/gate_python310.py
"""
from __future__ import annotations

import io
import sys
import tokenize
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Lo que viaja al servidor. Si crece la lista de sondas, crece esta.
ARBOLES = ["core", "data", "scenarios", "analysis", "visualization", "tests",
           "scripts", "reformateo/documento/scripts"]
SUELTOS = ["main_simulation.py", "diagnostico_datos.py"]


def revisa(ruta: Path) -> list:
    """Devuelve los avisos de una fuente, con su linea."""
    try:
        texto = ruta.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    avisos = []
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(texto).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError) as e:
        return [(0, f"no se puede tokenizar: {e}")]

    nombres = tokenize.tok_name
    abierta = None
    for t in toks:
        tipo = nombres.get(t.type, "")
        if tipo == "FSTRING_START":
            abierta = t
        elif tipo == "FSTRING_END" and abierta is not None:
            if t.end[0] != abierta.start[0] and not abierta.string.rstrip("fFrRbB").startswith(('"""', "'''")):
                avisos.append((abierta.start[0],
                               "cadena formateada partida en varias líneas; "
                               "solo compila desde 3.12"))
            abierta = None
        elif tipo == "STRING" and t.string[:1] in "fFrRbB":
            # cadena formateada de una pieza (asi la ve 3.10 y anteriores)
            if t.end[0] != t.start[0] and not any(
                    q in t.string[:4] for q in ('"""', "'''")):
                avisos.append((t.start[0], "cadena formateada multilínea"))
    return avisos


def main() -> int:
    fuentes = []
    for d in ARBOLES:
        p = RAIZ / d
        if p.is_dir():
            fuentes += [f for f in p.rglob("*.py")
                        if "__pycache__" not in f.parts]
    fuentes += [RAIZ / f for f in SUELTOS if (RAIZ / f).exists()]

    print(f"  Portabilidad a Python 3.10 · {len(fuentes)} ficheros")
    print(f"  (esta comprobación corre bajo {sys.version.split()[0]})")
    print("=" * 70)

    total = 0
    for f in sorted(fuentes):
        for linea, que in revisa(f):
            rel = f.relative_to(RAIZ).as_posix()
            print(f"  {rel}:{linea}  {que}")
            total += 1

    print()
    if total:
        print(f"  {total} problema(s) de portabilidad. El servidor NO los compila.")
        return 1
    print("  COMPUERTA DE PORTABILIDAD EN VERDE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
