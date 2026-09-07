"""
Sonda del peso del jugador virtual (H-46).

El bloque comprador es una dinamica de replicador sobre los precios, con una
estrategia mas que compradores: el jugador virtual, que absorbe el resto del
presupuesto. Cada estrategia entra en la aptitud media con un peso, y ese
peso es lo que mantiene el precio dentro de su banda porque se anula en las
dos cotas.

En el fichero original el peso se arma en DOS piezas. Para los compradores
reales es el producto de barrera; para el jugador virtual es **su propio
precio**. Esta traduccion le aplica la barrera tambien a el.

No es cosmetico. Con las cotas del modelo base y un precio de 1.000
(COP/kWh), la barrera vale 221.500 y el precio vale 1.000, un factor de 221.
El peso entra en la aptitud media y la aptitud media entra en la deriva de
TODOS los precios, de modo que la diferencia no se queda en el virtual.

Que decide esta sonda. Si el volumen y el excedente no se mueven, que es lo
esperable por H-33 y D-7, la eleccion es de fidelidad al modelo base y no de
resultado, y entonces conviene adoptar la forma del original. Si se mueven,
hay que medir cuanto antes de decidir.

Uso:
    python reformateo/documento/scripts/sonda/peso_virtual.py
        [--dia FECHA] [--muestra N] [--cobertura m1|m3|ambas]
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

FORMAS = ("barrera", "precio")
SALIDA = AQUI.parents[1] / "validacion_horaria"
PEGADO = 0.01          # a menos del uno por ciento de la banda, esta pegado

_DAT: dict = {}


def _datos(cobertura: str):
    from paso_a_paso import carga
    if cobertura not in _DAT:
        _DAT[cobertura] = carga(cobertura)
    return _DAT[cobertura]


def _una(args):
    """Resuelve UNA hora con UNA forma del peso. Corre en un proceso.

    La unidad de trabajo es la hora y la forma, no la hora entera, para que
    una hora dificil no retenga un proceso el doble de tiempo.
    """
    cobertura, k, solo = args
    from core.settlement import compute_savings
    from paso_a_paso import resuelve

    dat = _datos(cobertura)
    filas = []
    for forma in [f for f in FORMAS if f == solo]:
        try:
            r = resuelve(dat, int(k), peso_virtual=forma)
        except Exception:
            r = None
        if r is None:
            filas.append(dict(cobertura=cobertura, hora=int(k),
                              forma=forma, resuelta=False))
            continue

        techo_i, piso_j = r["techo_i"], r["piso_j"]
        piso_h = float(r["piso_h"])
        P = np.asarray(r["P"], float)
        pi = np.asarray(r["pi"], float)
        S_i, SR_j = compute_savings(P, pi, techo_i, piso_j)
        total = float(S_i.sum() + SR_j.sum())

        ancho = np.maximum(techo_i - piso_h, 1e-12)
        pos = (pi - piso_h) / ancho
        comprado = P.sum(axis=0)

        filas.append(dict(
            cobertura=cobertura, hora=int(k), forma=forma, resuelta=True,
            J=len(r["sids"]), I=len(r["bids"]),
            volumen=float(P.sum()),
            excedente=total,
            ahorro=float(S_i.sum()), prima=float(SR_j.sum()),
            tajada_vendedor=(100.0 * float(SR_j.sum()) / total
                             if abs(total) > 1e-9 else np.nan),
            precio_medio=float(np.average(pi,
                                          weights=np.maximum(comprado, 1e-12))),
            posicion_media=float(np.mean(pos)),
            pegados=int(np.sum((pos <= PEGADO) | (pos >= 1.0 - PEGADO))),
            n_precios=len(pi),
            retirados=len(r["retirados"]),
            sin_ahorro=int(np.sum((comprado > 1e-9) & (S_i <= 1e-6))),
        ))
    return filas


def horas_del_dia(cobertura: str, fecha: str) -> list[int]:
    idx = pd.DatetimeIndex(_datos(cobertura)["idx"])
    return [int(i) for i in np.where(idx.strftime("%Y-%m-%d") == fecha)[0]]


def horas_activas(cobertura: str) -> np.ndarray:
    from core.market_prep import classify_agents, compute_generation_limit
    from data.xm_prices import get_b_for_real_data

    dat = _datos(cobertura)
    D, G = dat["D"], dat["G"]
    N, T = D.shape
    a = np.zeros(N); c = np.zeros(N)
    b = get_b_for_real_data(N, dat["nombres"])
    out = [k for k in range(T)
           if all(classify_agents(
               compute_generation_limit(G[:, k], a, b, c, dat["techo"][:, k]),
               D[:, k])[1:])]
    return np.array(out, dtype=int)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dia", default="2025-05-02")
    ap.add_argument("--muestra", type=int, default=0)
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--cobertura", default="ambas",
                    choices=("m1", "m3", "ambas"))
    ap.add_argument("--procesos", type=int,
                    default=max(1, (os.cpu_count() or 4) - 2))
    args = ap.parse_args()

    cobs = ("m1", "m3") if args.cobertura == "ambas" else (args.cobertura,)
    horas = []
    if args.muestra:
        rng = np.random.default_rng(args.semilla)
        for cob in cobs:
            act = horas_activas(cob)
            n = min(args.muestra, len(act))
            horas += [(cob, int(k))
                      for k in rng.choice(act, size=n, replace=False)]
        etiqueta = f"muestra{args.muestra}"
    else:
        for cob in cobs:
            horas += [(cob, k) for k in horas_del_dia(cob, args.dia)]
        etiqueta = args.dia

    # Una tarea por hora Y forma. Ver la nota de `_una`.
    tareas = [(cob, k, f) for cob, k in horas for f in FORMAS]
    print(f"  {len(horas)} horas · {len(FORMAS)} formas = {len(tareas)} "
          f"tareas · {args.procesos} procesos", flush=True)

    # Los datos se arman aqui, antes de abrir los procesos: en Linux los
    # hijos heredan esa memoria y ninguno relee las mediciones.
    for cob in sorted({c for c, _ in horas}):
        _datos(cob)
    print(f"  datos en memoria: {sorted(_DAT)}", flush=True)

    filas = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.procesos) as ex:
        pendientes = {ex.submit(_una, t): t for t in tareas}
        for i, fut in enumerate(as_completed(pendientes), 1):
            filas.extend(fut.result())
            if i % 5 == 0 or i == len(tareas):
                seg = time.time() - t0
                print(f"    {i}/{len(tareas)}  ({seg/60:.1f} min, "
                      f"faltan ~{seg/i*(len(tareas)-i)/60:.0f})", flush=True)

    d = pd.DataFrame(filas)
    SALIDA.mkdir(parents=True, exist_ok=True)
    csv = SALIDA / f"peso_virtual_{etiqueta}.csv"
    d.to_csv(csv, index=False)

    ok = d[d.resuelta.fillna(False)]
    print(flush=True)
    print(f"  Peso del jugador virtual · {etiqueta}", flush=True)
    print("  " + "=" * 78, flush=True)
    for cob in cobs:
        s = ok[ok.cobertura == cob]
        if s.empty:
            continue
        print(flush=True)
        print(f"  frontera {cob.upper()}", flush=True)
        print(f"  {'forma':>9s} {'horas':>6s} {'volumen':>10s} "
              f"{'excedente':>12s} {'vend %':>7s} {'posicion':>9s} "
              f"{'pegados':>8s} {'retirados':>10s}", flush=True)
        for f in FORMAS:
            t = s[s.forma == f]
            if t.empty:
                continue
            print(f"  {f:>9s} {len(t):6d} {t.volumen.sum():10.3f} "
                  f"{t.excedente.sum():12.1f} "
                  f"{np.average(t.tajada_vendedor.fillna(0)):7.1f} "
                  f"{t.posicion_media.mean():9.3f} "
                  f"{t.pegados.sum():8d} {t.retirados.sum():10d}", flush=True)

        # Lo que decide: si el volumen y el excedente no se mueven, la
        # eleccion es de fidelidad y no de resultado.
        p = s.pivot(index="hora", columns="forma",
                    values=["volumen", "excedente"]).dropna()
        if not p.empty:
            dv = (p["volumen"]["precio"] - p["volumen"]["barrera"]).abs()
            de = (p["excedente"]["precio"] - p["excedente"]["barrera"]).abs()
            rel = de / p["excedente"]["barrera"].abs().clip(lower=1e-9)
            print(f"    max|dif| volumen   {dv.max():.3e} kWh", flush=True)
            print(f"    max|dif| excedente {de.max():.3e} COP "
                  f"({100*rel.max():.3f} % del mayor)", flush=True)
    print(flush=True)
    print(f"  csv: {csv}", flush=True)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
