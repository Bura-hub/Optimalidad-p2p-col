"""Las evaluaciones deterministas fuera del Sobol (apartado 5.3, D76).

Actividad 4.1.

En cada uno de los trece casos, con los seis factores en 1:

- la SENSIBILIDAD DECLARADA A MU de la rama cuantal (D71): mu = 0,5, 1 y 2.
  Es una eleccion de modelado sin distribucion defendible, y por eso va
  aparte del Sobol, que corre con mu = 1;
- el CONTRAFACTICO DE LA BOLSA DE 2024: la serie horaria de 2024
  (`data/precios_bolsa_xm_audit_2024.csv`) desde el 4 de abril de 2024, las
  6 144 horas, puesta sobre el calendario de 2025 y con el techo PES de 2025
  aplicado despues. Conserva la forma horaria y estacional de un ano de El
  Nino, que un factor no conserva. El desfase de dia de semana (el 4 de
  abril de 2024 fue jueves y el de 2025 viernes) se declara.

Escribe `deterministas.csv`: una fila por caso y variante, con todas las
salidas y la diferencia contra el punto base de la parte del vendedor, el
excedente y cada brecha.

    python -u gsa_directo/deterministas.py --salida SALIDAS_SERVIDOR/gsa_directo/base/deterministas.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from gsa_directo import comun  # noqa: E402

CSV_2024 = comun.RAIZ / "data" / "precios_bolsa_xm_audit_2024.csv"
DESDE_2024 = "2024-04-04"
VARIANTES = (("base", 1.0, False), ("mu_0.5", 0.5, False),
             ("mu_2", 2.0, False), ("bolsa_2024", 1.0, True))
DIFERENCIAS = ("parte_vendedor", "excedente") + tuple(comun.BRECHAS)


def bolsa_2024_desplazada(T: int, desde: str = DESDE_2024,
                          csv_path=CSV_2024) -> np.ndarray:
    """Las T horas de la serie de 2024 desde `desde`, CRUDAS (el techo PES
    de 2025 lo pone el evaluador con el `t0` del caso). Falla si faltan."""
    from data.xm_prices import load_xm_prices
    t0 = pd.Timestamp(desde)
    t1 = t0 + pd.Timedelta(hours=int(T))
    serie = load_xm_prices(str(csv_path), t0, t1, estricto=True)
    if serie is None or len(serie) != T:
        raise ValueError(f"la serie de 2024 no cubre {T} horas desde {desde}")
    serie = np.asarray(serie, dtype=float)
    if not np.all(np.isfinite(serie)):
        raise ValueError("la serie de 2024 trae valores no finitos")
    return serie


_EST = {}


def _inicia(datos):
    from gsa_directo import evaluador
    evaluador.inicia_proceso()
    comun.salida_utf8()
    _EST["datos"] = datos


def _tarea(args):
    caso, variante, mu, con_2024 = args
    from gsa_directo import evaluador
    if caso not in _EST:
        _EST[caso] = evaluador.prepara_caso(caso, _EST["datos"])
    ins = _EST[caso]
    t0 = time.time()
    try:
        cruda = bolsa_2024_desplazada(ins.T) if con_2024 else None
        y = evaluador.evalua(ins, comun.PUNTO_BASE, mu=mu, bolsa_cruda=cruda)
        return caso, variante, y, time.time() - t0, ""
    except ValueError as exc:
        return caso, variante, None, time.time() - t0, \
            f"{type(exc).__name__}: {exc}"


def ejecuta(argv=None) -> int:
    comun.salida_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--casos", nargs="+", default=list(comun.ORDEN_CASOS))
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--salida", default=str(comun.salidas_defecto() / "base"
                                            / "deterministas.csv"))
    ap.add_argument("--sin-escribir", action="store_true")
    ap.add_argument("--mte-root", default=None)
    ap.add_argument("--cache", default=None)
    args = ap.parse_args(argv)

    from gsa_directo import evaluador
    cache = (Path(args.cache) if args.cache else
             None if args.sin_escribir else comun.salidas_defecto() / "cache")
    datos = evaluador.carga_mte(args.mte_root, cache)
    trabajos = [(c, v, mu, b) for c in args.casos for v, mu, b in VARIANTES]
    print(f"DETERMINISTAS · {len(args.casos)} casos x {len(VARIANTES)} "
          f"variantes (mu 0,5 / 1 / 2 y la bolsa de 2024)")
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.procesos, initializer=_inicia,
                             initargs=(datos,)) as ex:
        res = list(ex.map(_tarea, trabajos))
    por = {(c, v): (y, s, m) for c, v, y, s, m in res}
    filas, fallos = [], 0
    for c in args.casos:
        yb = por[(c, "base")][0]
        for v, _mu, _b in VARIANTES:
            y, s, m = por[(c, v)]
            fila = dict(caso=c, variante=v, seg=round(s, 3), motivo=m)
            if y is None:
                fallos += 1
            else:
                fila.update(y)
                if yb is not None:
                    for k in DIFERENCIAS:
                        fila[f"dif_{k}"] = y[k] - yb[k]
            filas.append(fila)
            if y is None:
                print(f"  {c:<5} {v:<11} FALLA: {m[:100]}")
            else:
                d = "" if yb is None or v == "base" else (
                    f"  dif. parte {y['parte_vendedor'] - yb['parte_vendedor']:+.4f}"
                    f"  dif. P2P-C4 {y['P2P_menos_C4'] - yb['P2P_menos_C4']:+,.0f}"
                    f"  dif. P2P-C5 {y['P2P_menos_C5'] - yb['P2P_menos_C5']:+,.0f}")
                print(f"  {c:<5} {v:<11} P2P {y['P2P']:>14,.0f}  parte "
                      f"{y['parte_vendedor']:.4f}  cuantales "
                      f"{y['n_cuantal']:.0f}{d}")
    print(f"  {len(trabajos)} evaluaciones en {time.time() - t0:.0f} s; "
          f"fallos {fallos}")
    if not args.sin_escribir:
        destino = Path(args.salida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        campos = []
        for f in filas:
            for k in f:
                if k not in campos:
                    campos.append(k)
        with open(destino, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=campos)
            w.writeheader()
            for f in filas:
                w.writerow({k: (repr(v) if isinstance(v, float) else v)
                            for k, v in f.items()})
        print(f"  escrito {destino}")
    print("DETERMINISTAS TERMINADAS" + ("" if not fallos else
                                        f" CON {fallos} FALLOS"))
    return 0 if not fallos else 1


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    sys.exit(ejecuta())
