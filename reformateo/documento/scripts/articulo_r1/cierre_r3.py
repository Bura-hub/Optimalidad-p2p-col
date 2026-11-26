"""
cierre_r3.py — Corre m13 (la reconstrucción de Udenar) y junta `cifras.csv`,
`GUIONES.csv` y `procedencia.txt` (CANON §14.42)
===============================================================================
Antes deja en `logs/canon_antes.log` la salida de `verificar_canon_2026-09.py`,
que tiene que terminar en INTACTO. Sin fecha en ningún fichero.

    PYTHONUNBUFFERED=1 python -u reformateo/documento/scripts/articulo_r1/cierre_r3.py
"""
from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy

for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[4]
AQUI = Path(__file__).resolve().parent
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "articulo_r1_reconstruccion_2026-11-25"
GUIONES = ["reformateo/documento/scripts/articulo_r1/ar1_comun.py",
           "reformateo/documento/scripts/articulo_r1/m13_reconstruccion_udenar.py",
           "reformateo/documento/scripts/articulo_r1/cierre_r3.py",
           "data/preprocessing.py"]


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.rstrip("\n")


def main() -> int:
    (SALIDA / "logs").mkdir(parents=True, exist_ok=True)
    v = subprocess.run([sys.executable, "-u", str(RAIZ / "Documentos/canon_2026-09/verificar_canon_2026-09.py")],
                       cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)
    (SALIDA / "logs" / "canon_antes.log").write_text("\n".join(
        x for x in v.stdout.splitlines() if x.strip()).rstrip() + "\n", encoding="utf-8", newline="\n")
    if v.returncode != 0 or not v.stdout.rstrip().endswith("CANON 2026-09 INTACTO"):
        raise SystemExit("[ar3:cierre] el canon no está intacto antes de medir")
    r = subprocess.run([sys.executable, "-u", str(AQUI / "m13_reconstruccion_udenar.py")], cwd=RAIZ,
                       capture_output=True, text=True, encoding="utf-8", timeout=3600)
    if r.returncode != 0:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        raise SystemExit(f"[ar3:cierre] m13 terminó con código {r.returncode}")
    c = pd.read_csv(SALIDA / "cifras_m13.csv", dtype=str, keep_default_na=False)
    log = (SALIDA / "logs" / "m13.log").read_text(encoding="utf-8").splitlines()
    comp = [x.split("  OK  ", 1)[1] for x in log if "  OK  " in x and x.startswith("[ar1:m13]")]
    fin = [x for x in log if x.endswith(" cifras") and " compuertas, " in x]
    if not fin or f"{len(comp)} compuertas, {len(c)} cifras" not in fin[-1] or c.clave.duplicated().any():
        raise SystemExit("[ar3:cierre] el registro de m13 no cuadra con sus cifras y compuertas")
    c.to_csv(SALIDA / "cifras.csv", index=False, lineterminator="\n")
    (SALIDA / "cifras_m13.csv").unlink()
    with open(SALIDA / "GUIONES.csv", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("ruta,bytes,sha256\n")
        for g in GUIONES:
            d = (RAIZ / g).read_bytes()
            fh.write(f"{g},{len(d)},{hashlib.sha256(d).hexdigest()}\n")
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("articulo_r1_reconstruccion: la reconstrucción de la generación de Udenar (CAL-44), CANON §14.42\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("cambios sin commit en los guiones y módulos de GUIONES.csv:\n")
        fh.write((git("status", "--porcelain", "--", *GUIONES) or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, scipy {scipy.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u reformateo/documento/scripts/articulo_r1/cierre_r3.py\n")
        fh.write("no simula: lee las dos series de inversor de Udenar de MedicionesMTE_v3 con data/preprocessing.py "
                 "(datos privados, sin huella en el canon); la serie reconstruida se ata al almacén con huella de E0 "
                 "por la compuerta T3\n")
        fh.write(f"compuertas: {len(comp)}\n")
        fh.write(f"cifras: {len(c)}\n")
        fh.write("\n".join(f"  - {x}" for x in comp) + "\n")
    print(f"[ar3:cierre] {len(comp)} compuertas, {len(c)} cifras, {len(GUIONES)} guiones y módulos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
