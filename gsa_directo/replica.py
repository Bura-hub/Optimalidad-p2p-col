"""Replica y determinismo del GSA directo (apartado 6.2 del diseno, D73).

Actividad 4.1.

Ocho puntos del hipercubo: el base, el extremo superior de cada entrada con
el resto en 1, y el vertice de los maximos. Se declara un apartamiento del
6.2, que dice «los seis extremos de cada entrada»: aqui va solo el SUPERIOR
de cada una, porque lo que se mide es el determinismo (dos procesos, el
mismo punto) y no la respuesta, y un extremo por entrada ya recorre el
camino de ese factor. Cada uno se evalua DOS VECES, en
dos pools distintos (procesos distintos por construccion), y las salidas
deben coincidir AL BIT; en un caso con horas cuantales, donde `exp` y `log`
admiten 1e-9 relativa (§8 de `INTERFAZ_NUCLEO.md`), con esa tolerancia. Un
punto que falla tiene que fallar igual las dos veces.

Es el control del precio degenerado de agosto (la deriva de `ie`): con el
reposo no hay integrador y el reparto es determinista, y esto lo mide.

    python -u gsa_directo/replica.py --casos E0 --salida SALIDAS_SERVIDOR/gsa_directo/base/replica.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from gsa_directo import comun  # noqa: E402

TOL_CUANTAL = 1e-9


def puntos() -> list:
    """(nombre, x) de los ocho puntos."""
    out = [("base", comun.PUNTO_BASE.copy())]
    for i, nombre in enumerate(comun.NOMBRES):
        x = comun.PUNTO_BASE.copy()
        x[i] = comun.SOPORTES[i][1]
        out.append((f"{nombre}_max", x))
    out.append(("vertice_max", np.array([s[1] for s in comun.SOPORTES])))
    return out


_INS = {}


def _inicia(datos):
    from gsa_directo import evaluador
    evaluador.inicia_proceso()
    comun.salida_utf8()
    _INS["datos"] = datos


def _tarea(args):
    caso, nombre, x = args
    import os
    from gsa_directo import evaluador
    if caso not in _INS:
        _INS[caso] = evaluador.prepara_caso(caso, _INS["datos"])
    try:
        return caso, nombre, os.getpid(), evaluador.evalua(_INS[caso], x), ""
    except ValueError as exc:
        return caso, nombre, os.getpid(), None, f"{type(exc).__name__}: {exc}"


def pasada(trabajos, datos, procesos) -> dict:
    with ProcessPoolExecutor(max_workers=procesos, initializer=_inicia,
                             initargs=(datos,)) as ex:
        return {(c, n): (pid, y, m) for c, n, pid, y, m in
                ex.map(_tarea, trabajos)}


def compara(y1, y2, m1, m2, cuantal: bool) -> dict:
    """Veredicto de un punto: iguales al bit, dentro de 1e-9 o distintos."""
    if y1 is None or y2 is None:
        igual = (y1 is None and y2 is None and m1 == m2)
        return dict(veredicto="falla igual" if igual else "DISTINTO",
                    dif_rel_max=None, motivo=m1 or m2, cumple=igual)
    difs = {k: abs(y1[k] - y2[k]) / max(abs(y1[k]), 1e-12) for k in y1}
    dmax = max(difs.values()) if difs else 0.0
    al_bit = all(y1[k] == y2[k] for k in y1)
    ok = al_bit or (cuantal and dmax <= TOL_CUANTAL)
    return dict(veredicto="al bit" if al_bit else
                ("dentro de 1e-9 (cuantal)" if ok else "DISTINTO"),
                dif_rel_max=dmax, peor=max(difs, key=difs.get) if difs else None,
                motivo="", cumple=bool(ok))


def ejecuta(argv=None) -> int:
    comun.salida_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--casos", nargs="+", default=["E0"])
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--salida", default=str(comun.salidas_defecto() / "base"
                                            / "replica.json"))
    ap.add_argument("--sin-escribir", action="store_true")
    ap.add_argument("--mte-root", default=None)
    ap.add_argument("--cache", default=None)
    args = ap.parse_args(argv)

    from gsa_directo import evaluador
    cache = (Path(args.cache) if args.cache else
             None if args.sin_escribir else comun.salidas_defecto() / "cache")
    datos = evaluador.carga_mte(args.mte_root, cache)
    trabajos = [(c, n, x) for c in args.casos for n, x in puntos()]
    print(f"REPLICA · {len(trabajos)} puntos x 2 pasadas en pools distintos · "
          f"casos {' '.join(args.casos)}")
    t0 = time.time()
    p1 = pasada(trabajos, datos, args.procesos)
    p2 = pasada(trabajos, datos, args.procesos)
    filas = []
    for c, n, x in trabajos:
        pid1, y1, m1 = p1[(c, n)]
        pid2, y2, m2 = p2[(c, n)]
        cuantal = bool((y1 or {}).get("n_cuantal", 0) or
                       (y2 or {}).get("n_cuantal", 0))
        v = compara(y1, y2, m1, m2, cuantal)
        v.update(caso=c, punto=n, x=[float(t) for t in x], pids=[pid1, pid2],
                 procesos_distintos=pid1 != pid2, n_cuantal=(y1 or {}).get(
                     "n_cuantal"))
        filas.append(v)
        print(f"  {c:<5} {n:<14} {v['veredicto']:<26} "
              f"dif. rel. max {v['dif_rel_max'] if v['dif_rel_max'] is not None else '-'}"
              f"  {v['motivo'][:80]}")
    ok = all(f["cumple"] for f in filas)
    res = dict(generado=time.strftime("%Y-%m-%d %H:%M:%S"),
               codigo=comun.version_codigo(), tol_cuantal=TOL_CUANTAL,
               entradas={n: comun.ROTULOS[n] for n in comun.NOMBRES},
               cumple=ok, segundos=round(time.time() - t0, 1), puntos=filas)
    if not args.sin_escribir:
        destino = Path(args.salida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(res, indent=2, ensure_ascii=False),
                           encoding="utf-8")
        print(f"  escrito {destino}")
    print("REPLICA EN VERDE" if ok else "REPLICA EN ROJO")
    return 0 if ok else 1


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    sys.exit(ejecuta())
