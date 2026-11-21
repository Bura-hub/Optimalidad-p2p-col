"""
cierre.py — Corre las ocho mediciones de la revisión r1 del artículo y junta
`cifras.csv`, `GUIONES.csv` y `procedencia.txt` (CANON §14.40)
===============================================================================
Corre, en este orden, m8, m4a, m3, m5, m6, m2, m1 y m7, cada una en su proceso
y en primer plano. Si una falla, se detiene. Después:

  cifras.csv        todas las cifras (clave, valor, unidad, fuente), en el orden
                    de las mediciones; las parciales `cifras_<m>.csv` se borran
  GUIONES.csv       ruta, bytes y sha256 de cada guion de esta carpeta
  procedencia.txt   HEAD, versiones, orden, compuertas de cada medición,
                    artefactos leídos con huella e insumos con su sha256

Sin fecha en ningún fichero: con el mismo HEAD y los mismos guiones, dos
corridas dan los mismos ficheros byte a byte.

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo_r1/cierre.py
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
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "articulo_r1_2026-11-21"
ORDEN = [("m8", "m8_trm.py"), ("m4a", "m4a_periodos.py"), ("m3", "m3_cargos_parciales.py"), ("m5", "m5_componentes.py"),
         ("m6", "m6_dinamica_agentes.py"), ("m2", "m2_factorial_fijos.py"), ("m1", "m1_liquidacion.py"), ("m7", "m7_rangos.py")]


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.rstrip("\n")


def main() -> int:
    for nom, guion in ORDEN:
        print(f"[ar1:cierre] corre {guion}", flush=True)
        r = subprocess.run([sys.executable, "-u", str(AQUI / guion)], cwd=RAIZ, capture_output=True, text=True,
                           encoding="utf-8", timeout=1800)
        if r.returncode != 0:
            print(r.stdout[-3000:])
            print(r.stderr[-3000:])
            raise SystemExit(f"[ar1:cierre] {guion} terminó con código {r.returncode}")
    partes, n_comp, lineas, leidos, insumos = [], 0, [], [], []
    for nom, guion in ORDEN:
        p = SALIDA / f"cifras_{nom}.csv"
        c = pd.read_csv(p, dtype=str, keep_default_na=False)
        if list(c.columns) != ["clave", "valor", "unidad", "fuente"] or len(c) == 0:
            raise SystemExit(f"[ar1:cierre] {p.name} sin cifras o con otra cabecera")
        partes.append(c)
        log = (SALIDA / "logs" / f"{nom}.log").read_text(encoding="utf-8").splitlines()
        comp = [x.split("  OK  ", 1)[1] for x in log if "  OK  " in x]
        fin = [x for x in log if x.endswith(" cifras") and " compuertas, " in x]
        if not fin or f"{len(comp)} compuertas, {len(c)} cifras" not in fin[-1]:
            raise SystemExit(f"[ar1:cierre] el registro de {nom} no cuadra con sus cifras y compuertas")
        n_comp += len(comp)
        lineas.append(f"{nom} ({guion}): {len(comp)} compuertas, {len(c)} cifras")
        lineas += [f"  - {x}" for x in comp]
        modo = None
        for x in log:
            if "artefactos leídos con huella" in x:
                modo = leidos
            elif "insumos sin huella" in x:
                modo = insumos
            elif x.startswith("[ar1:"):
                modo = None
            elif modo is not None and x.startswith("  "):
                if x.strip() not in modo:
                    modo.append(x.strip())
    cif = pd.concat(partes, ignore_index=True)
    if cif.clave.duplicated().any():
        raise SystemExit(f"[ar1:cierre] claves repetidas: {list(cif.clave[cif.clave.duplicated()])[:5]}")
    cif.to_csv(SALIDA / "cifras.csv", index=False, lineterminator="\n")
    for nom, _ in ORDEN:
        (SALIDA / f"cifras_{nom}.csv").unlink()
    guiones = sorted(AQUI.glob("*.py"))
    with open(SALIDA / "GUIONES.csv", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("ruta,bytes,sha256\n")
        for g in guiones:
            d = g.read_bytes()
            fh.write(f"{g.relative_to(RAIZ).as_posix()},{len(d)},{hashlib.sha256(d).hexdigest()}\n")
    rel = AQUI.relative_to(RAIZ).as_posix()
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("articulo_r1: mediciones M1 a M8 para la revisión r1 del artículo (envío 11297), CANON §14.40\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("cambios sin commit en los guiones:\n")
        fh.write((git("status", "--porcelain", "--", rel) or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, scipy {scipy.__version__}, pandas {pd.__version__}\n")
        fh.write(f"orden: python -u {rel}/cierre.py\n")
        fh.write("no simula: no importa el motor ni resuelve el mercado; no toca core/, scenarios/ ni analysis/\n")
        fh.write(f"compuertas: {n_comp}\n")
        fh.write(f"cifras: {len(cif)}\n")
        fh.write("\n".join(lineas) + "\n")
        fh.write(f"artefactos leídos con huella: {len(leidos)}\n")
        fh.write("\n".join(f"  {x}" for x in sorted(leidos)) + "\n")
        fh.write(f"insumos sin huella en el canon, con su tamaño y su sha256: {len(insumos)}\n")
        fh.write("\n".join(f"  {x}" for x in sorted(insumos)) + "\n")
        fh.write("guiones (GUIONES.csv):\n")
        fh.write("\n".join(f"  {g.name}" for g in guiones) + "\n")
    print(f"[ar1:cierre] {n_comp} compuertas, {len(cif)} cifras, {len(guiones)} guiones, {len(leidos)} artefactos con huella, "
          f"{len(insumos)} insumos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
