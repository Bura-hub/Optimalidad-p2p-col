"""
Compuerta de C-156: el plazo POR TAREA de la recogida.

Lo que hay que probar, y son cuatro cosas:

  1. Sin tareas atascadas, la medicion cierra sola y devuelve todas las filas.
  2. Con una tarea atascada, corta al pasar el plazo POR TAREA y NO espera al
     total. Es el defecto que motiva el cambio: el 2026-09-08 tres tareas
     costaron 29 minutos de procesos ociosos.
  3. La tarea atascada queda anotada como no resuelta, no desaparece.
  4. El proceso atascado se TERMINA. No basta con cancelar: esta en codigo
     nativo y no atiende la cancelacion.

La funcion de prueba no toca el modelo: duerme. Lo que se prueba es la
recogida, no el integrador.

Uso:
    python tests/gate_c156_plazo_por_tarea.py
"""
from __future__ import annotations

import multiprocessing
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "reformateo" / "documento" / "scripts" / "sonda"))

import pandas as pd  # noqa: E402

from recoge import recoge  # noqa: E402


def _tarea(t):
    """Duerme lo que le digan. Con `None` no acaba nunca."""
    cob, k, seg = t
    if seg is None:
        while True:
            time.sleep(1.0)
    time.sleep(seg)
    return [dict(cobertura=cob, hora=k, resuelta=True, seg=seg)]


def main() -> int:
    tmp = Path(RAIZ / "outputs" / "_gate_c156")
    tmp.mkdir(parents=True, exist_ok=True)
    fallos = []

    # 1 · sin atascos, cierra sola
    t0 = time.time()
    d = recoge(_tarea, [("m1", k, 0.2) for k in range(8)], 4,
               tmp / "sanas.csv", plazo_min=5.0, plazo_tarea_min=1.0, cada=4)
    dur = time.time() - t0
    ok1 = len(d) == 8 and bool(d.resuelta.all()) and dur < 30
    print(f"  1 · ocho tareas sanas: {len(d)} filas en {dur:.1f} s  "
          f"{'ok' if ok1 else 'FALLA'}")
    if not ok1:
        fallos.append("no cierra sola con tareas sanas")

    # 2 y 3 · una atascada: corta por el plazo POR TAREA, no por el total
    t0 = time.time()
    tareas = [("m1", k, 0.2) for k in range(6)] + [("m1", 99, None)]
    d = recoge(_tarea, tareas, 4, tmp / "atascada.csv",
               plazo_min=10.0, plazo_tarea_min=0.5, cada=3)
    dur = time.time() - t0
    sanas = int(d.resuelta.fillna(False).sum())
    colgadas = int((~d.resuelta.fillna(False)).sum())
    ok2 = dur < 120 and sanas == 6 and colgadas == 1
    print(f"  2 · una atascada: corta a los {dur:.1f} s "
          f"(el plazo total eran 600) {'ok' if ok2 else 'FALLA'}")
    print(f"  3 · queda anotada: {sanas} resueltas y {colgadas} sin resolver  "
          f"{'ok' if ok2 else 'FALLA'}")
    if dur >= 120:
        fallos.append("espera al plazo total en vez de cortar por tarea")
    if sanas != 6 or colgadas != 1:
        fallos.append(f"filas mal: {sanas} resueltas, {colgadas} colgadas")

    # 4 · no queda ningun hijo vivo
    time.sleep(1.5)
    vivos = [p for p in multiprocessing.active_children()]
    print(f"  4 · hijos vivos tras el corte: {len(vivos)}  "
          f"{'ok' if not vivos else 'FALLA'}")
    if vivos:
        fallos.append(f"{len(vivos)} trabajadores sobreviven al corte")

    print()
    if fallos:
        for f in fallos:
            print(f"  FALLA: {f}")
        return 1
    print("  C-156 en verde: el plazo por tarea corta sin esperar al total,")
    print("  la tarea atascada queda anotada y no sobrevive ningun proceso.")
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
