"""
Sonda del regimen del techo (H-45).

La pregunta que responde: el limite superior del precio, que es lo que cada
comprador le paga a la red, tiene que ser uno solo para la comunidad o uno
por comprador. En esta comunidad no es academico, porque cuatro
instituciones compran a un comercializador y la quinta a otro, y sus costos
unitarios difieren.

Se comparan cuatro regimenes sobre las mismas horas:

  escalar   el mayor de los techos entra al solucionador y el propio se
            aplica despues como recorte. Es lo que se hacia hasta el
            2026-09-07.
  propio    el techo de cada comprador entra al solucionador.
  minimo    todos al techo mas bajo de la hora.
  maximo    todos al techo mas alto de la hora.

REGLA DE EVALUACION, que es lo que hace comparable a los cuatro: el ahorro
de un comprador se mide SIEMPRE contra su techo REAL, es decir contra lo que
de verdad le costaria a el comprarle a la red. Un regimen que le deje pagar
por encima de su techo real produce ahorro negativo, y eso es exactamente lo
que hay que ver.

Uso:
    python reformateo/documento/scripts/sonda/techo_regimen.py [--dia FECHA]
"""
from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[3]
for _p in (RAIZ, AQUI):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import hilos  # noqa: E402,F401   un hilo por proceso, y ANTES que numpy

import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402

REGIMENES = ("escalar", "propio", "minimo", "maximo")
SALIDA = AQUI.parents[1] / "validacion_horaria"


def _una(args):
    """Resuelve UNA hora en UN regimen. Corre en un proceso.

    La unidad de trabajo es la hora y el regimen, no la hora entera. Con las
    cuatro juntas una hora dificil retiene un proceso cuatro veces mas y el
    reparto se desequilibra; separadas, el que se desocupa toma la siguiente.
    """
    cobertura, k, reg = args
    from core.settlement import compute_savings
    from paso_a_paso import carga, resuelve

    dat = _DAT.get(cobertura)
    if dat is None:
        dat = carga(cobertura)
        _DAT[cobertura] = dat

    filas = []
    for _ in (0,):
        try:
            r = resuelve(dat, int(k), techo=reg)
        except Exception:
            r = None
        if r is None:
            continue
        bids = r["bids"]
        techo_real = dat["techo"][bids, int(k)]     # el de verdad, siempre
        pi = np.asarray(r["pi"], float)
        P = np.asarray(r["P"], float)
        S_i, SR_j = compute_savings(P, pi, techo_real, r["piso_j"])
        comprado = P.sum(axis=0)
        activos = comprado > 1e-9
        total = float(S_i.sum() + SR_j.sum())
        filas.append(dict(
            cobertura=cobertura, hora=int(k), regimen=reg,
            volumen=float(P.sum()),
            excedente=total,
            ahorro=float(S_i.sum()), prima=float(SR_j.sum()),
            tajada_vendedor=(100.0 * float(SR_j.sum()) / total
                             if abs(total) > 1e-9 else np.nan),
            compradores=int(activos.sum()),
            sin_ahorro=int(np.sum(activos & (S_i <= 1e-6))),
            con_perdida=int(np.sum(activos & (S_i < -1e-6))),
            retirados=len(r["retirados"]),
            precio_medio=float(np.average(pi, weights=np.maximum(comprado, 1e-12))),
        ))
    return filas


_DAT: dict = {}


def horas_del_dia(cobertura: str, fecha: str) -> list[int]:
    from paso_a_paso import carga
    dat = _DAT.setdefault(cobertura, carga(cobertura))
    idx = pd.DatetimeIndex(dat["idx"])
    return [int(i) for i in np.where(idx.strftime("%Y-%m-%d") == fecha)[0]]


def horas_activas(cobertura: str) -> np.ndarray:
    """Horas con al menos un vendedor y un comprador, sin resolver el juego."""
    from core.market_prep import classify_agents, compute_generation_limit
    from data.xm_prices import get_b_for_real_data
    from paso_a_paso import carga

    dat = _DAT.setdefault(cobertura, carga(cobertura))
    D, G = dat["D"], dat["G"]
    N, T = D.shape
    a = np.zeros(N); c = np.zeros(N)
    b = get_b_for_real_data(N, dat["nombres"])
    out = []
    for k in range(T):
        gk = compute_generation_limit(G[:, k], a, b, c, dat["techo"][:, k])
        _, sids, bids = classify_agents(gk, D[:, k])
        if sids and bids:
            out.append(k)
    return np.array(out, dtype=int)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dia", default="2025-05-02")
    ap.add_argument("--muestra", type=int, default=0,
                    help="horas activas al azar del horizonte, en vez de un dia")
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--procesos", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    args = ap.parse_args()

    horas = []
    if args.muestra:
        rng = np.random.default_rng(args.semilla)
        for cob in ("m1", "m3"):
            act = horas_activas(cob)
            n = min(args.muestra, len(act))
            horas += [(cob, int(k))
                      for k in rng.choice(act, size=n, replace=False)]
        etiqueta = f"muestra{args.muestra}"
    else:
        for cob in ("m1", "m3"):
            horas += [(cob, k) for k in horas_del_dia(cob, args.dia)]
        etiqueta = args.dia

    # Una tarea por hora Y regimen. Ver la nota de `_una`.
    tareas = [(cob, k, reg) for cob, k in horas for reg in REGIMENES]
    print(f"  {len(horas)} horas · {len(REGIMENES)} regimenes = "
          f"{len(tareas)} tareas · {args.procesos} procesos", flush=True)

    # Los datos ya estan cargados aqui, porque calcular las horas activas los
    # necesito. En Linux los procesos hijo heredan esa memoria sin copiarla,
    # de modo que ninguno vuelve a leer el 1,7 GB de mediciones. En Windows
    # no, y cada uno los relee como antes.
    print(f"  datos en memoria: {sorted(_DAT)}", flush=True)

    filas = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.procesos) as ex:
        pendientes = {ex.submit(_una, t): t for t in tareas}
        for i, fut in enumerate(as_completed(pendientes), 1):
            filas.extend(fut.result())
            if i % 20 == 0 or i == len(tareas):
                seg = time.time() - t0
                print(f"    {i}/{len(tareas)}  ({seg/60:.1f} min, "
                      f"faltan ~{seg/i*(len(tareas)-i)/60:.0f})", flush=True)

    if not filas:
        print("  ninguna hora resolvio", flush=True)
        return 1

    d = pd.DataFrame(filas)
    SALIDA.mkdir(parents=True, exist_ok=True)
    csv = SALIDA / f"techo_regimen_{etiqueta}.csv"
    d.to_csv(csv, index=False)

    print(flush=True)
    print(f"  Regimen del techo · {etiqueta}", flush=True)
    print("  " + "=" * 76, flush=True)
    for cob in ("m1", "m3"):
        s = d[d.cobertura == cob]
        if s.empty:
            continue
        print(flush=True)
        print(f"  frontera {cob.upper()}", flush=True)
        print(f"  {'regimen':>9s} {'horas':>6s} {'volumen':>10s} "
              f"{'excedente':>12s} {'ahorro':>11s} {'prima':>11s} "
              f"{'vend %':>7s} {'sin ahorro':>11s} {'con perdida':>12s}",
              flush=True)
        for reg in REGIMENES:
            t = s[s.regimen == reg]
            if t.empty:
                continue
            print(f"  {reg:>9s} {len(t):6d} {t.volumen.sum():10.2f} "
                  f"{t.excedente.sum():12.1f} {t.ahorro.sum():11.1f} "
                  f"{t.prima.sum():11.1f} "
                  f"{np.average(t.tajada_vendedor.fillna(0)):7.1f} "
                  f"{t.sin_ahorro.sum():11d} {t.con_perdida.sum():12d}",
                  flush=True)
    print(flush=True)
    print(f"  csv: {csv}", flush=True)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
