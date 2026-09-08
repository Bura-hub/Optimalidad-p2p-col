"""
Sonda del criterio de participacion (H-43, C-149).

Un vendedor no entra al mercado si el mercado le paga menos que su
alternativa de fuera. La pregunta es CUANDO se considera que eso ocurre, y
el criterio anterior lo medía mal.

  maximo    se retira si TODAS sus parejas quedan bajo su piso, mirando el
            MEJOR de sus precios. Bastaba colocar una cantidad infima a un
            comprador que pagara bien para quedarse vendiendo el grueso a
            perdida. Medido: 16 casos con prima negativa y CERO retirados.
  ingreso   se retira si su ingreso ponderado por energia queda bajo su
            piso, que es lo mismo que exigir prima no negativa. Es lo que
            decide un vendedor racional, y es el defecto desde C-149.

QUE DECIDE ESTA SONDA. El criterio correcto tiene un costo: saca del mercado
a vendedores que antes entraban, y con ellos su energia. En cuatro horas
sueltas el volumen caia entre un 77 y un 92 %, salvo una en que no caia nada
y el excedente subia un 42,7 %. Hay que saber cual de las dos cosas es la
regla y cual la excepcion antes de dar el cambio por bueno.

Uso:
    python reformateo/documento/scripts/sonda/participacion.py --muestra 40
"""
from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[3]
for _p in (RAIZ, AQUI):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import hilos  # noqa: E402,F401   un hilo por proceso, y ANTES que numpy

import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402

from recoge import recoge  # noqa: E402

CRITERIOS = ("maximo", "ingreso")
SALIDA = AQUI.parents[1] / "validacion_horaria"

_DAT: dict = {}


def _datos(cobertura: str):
    from paso_a_paso import carga
    if cobertura not in _DAT:
        _DAT[cobertura] = carga(cobertura)
    return _DAT[cobertura]


def _una(args):
    """Resuelve UNA hora con UN criterio."""
    cobertura, k, criterio = args
    from core.settlement import compute_savings
    from paso_a_paso import resuelve

    dat = _datos(cobertura)
    try:
        r = resuelve(dat, int(k), criterio=criterio)
    except Exception:
        r = None
    if r is None:
        return [dict(cobertura=cobertura, hora=int(k), criterio=criterio,
                     resuelta=False)]

    P = np.asarray(r["P"], float)
    pi = np.asarray(r["pi"], float)
    S_i, SR_j = compute_savings(P, pi, r["techo_i"], r["piso_j"])
    total = float(S_i.sum() + SR_j.sum())
    return [dict(
        cobertura=cobertura, hora=int(k), criterio=criterio, resuelta=True,
        J=len(r["sids"]), I=len(r["bids"]), retirados=len(r["retirados"]),
        volumen=float(P.sum()), excedente=total,
        ahorro=float(S_i.sum()), prima=float(SR_j.sum()),
        # el que decide: cuantos vendedores acaban por debajo de su piso
        vendedores_a_perdida=int(np.sum(SR_j < -1e-6)),
        peor_prima=float(np.min(SR_j)) if len(SR_j) else np.nan,
    )]


def horas_activas(cobertura: str) -> np.ndarray:
    from core.market_prep import classify_agents, compute_generation_limit
    from data.xm_prices import get_b_for_real_data

    dat = _datos(cobertura)
    D, G = dat["D"], dat["G"]
    N, T = D.shape
    a = np.zeros(N); c = np.zeros(N)
    b = get_b_for_real_data(N, dat["nombres"])
    return np.array([k for k in range(T)
                     if all(classify_agents(
                         compute_generation_limit(
                             G[:, k], a, b, c, dat["techo"][:, k]),
                         D[:, k])[1:])], dtype=int)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=40)
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--plazo", type=float, default=45.0,
                    help="plazo total en minutos; al agotarse se anota lo que "
                         "no resolvio y se sigue con lo que hay")
    ap.add_argument("--procesos", type=int,
                    default=max(1, (os.cpu_count() or 4) - 2))
    args = ap.parse_args()

    rng = np.random.default_rng(args.semilla)
    horas = []
    for cob in ("m1", "m3"):
        act = horas_activas(cob)
        n = min(args.muestra, len(act))
        horas += [(cob, int(k)) for k in rng.choice(act, size=n, replace=False)]

    tareas = [(cob, k, cr) for cob, k in horas for cr in CRITERIOS]
    print(f"  {len(horas)} horas · {len(CRITERIOS)} criterios = "
          f"{len(tareas)} tareas · {args.procesos} procesos", flush=True)
    print(f"  datos en memoria: {sorted(_DAT)}", flush=True)

    SALIDA.mkdir(parents=True, exist_ok=True)
    csv = SALIDA / f"participacion_muestra{args.muestra}.csv"
    d = recoge(_una, tareas, args.procesos, csv, plazo_min=args.plazo,
               describe=lambda t: f"{t[0]} hora {t[1]} criterio {t[2]}")

    ok = d[d.resuelta.fillna(False)]
    print(flush=True)
    print(f"  Criterio de participacion · muestra{args.muestra}", flush=True)
    print("  " + "=" * 82, flush=True)
    for cob in ("m1", "m3"):
        s = ok[ok.cobertura == cob]
        if s.empty:
            continue
        print(flush=True)
        print(f"  frontera {cob.upper()}", flush=True)
        print(f"  {'criterio':>9s} {'horas':>6s} {'volumen':>10s} "
              f"{'excedente':>12s} {'prima':>11s} {'retirados':>10s} "
              f"{'vend. a perdida':>16s}", flush=True)
        for cr in CRITERIOS:
            t = s[s.criterio == cr]
            if t.empty:
                continue
            print(f"  {cr:>9s} {len(t):6d} {t.volumen.sum():10.2f} "
                  f"{t.excedente.sum():12.1f} {t.prima.sum():11.1f} "
                  f"{int(t.retirados.sum()):10d} "
                  f"{int(t.vendedores_a_perdida.sum()):16d}", flush=True)

        p = s.pivot(index="hora", columns="criterio",
                    values=["volumen", "excedente", "retirados"]).dropna()
        if not p.empty:
            dv = 100 * (p["volumen"]["ingreso"] - p["volumen"]["maximo"]) \
                 / p["volumen"]["maximo"].clip(lower=1e-9)
            de = 100 * (p["excedente"]["ingreso"] - p["excedente"]["maximo"]) \
                 / p["excedente"]["maximo"].abs().clip(lower=1e-9)
            toca = int((p["retirados"]["ingreso"]
                        > p["retirados"]["maximo"]).sum())
            print(f"    el criterio nuevo retira mas en {toca} de {len(p)} horas",
                  flush=True)
            print(f"    volumen:   mediana {dv.median():+.1f} %  "
                  f"peor {dv.min():+.1f} %  mejor {dv.max():+.1f} %", flush=True)
            print(f"    excedente: mediana {de.median():+.1f} %  "
                  f"peor {de.min():+.1f} %  mejor {de.max():+.1f} %", flush=True)
    print(flush=True)
    print(f"  csv: {csv}", flush=True)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
