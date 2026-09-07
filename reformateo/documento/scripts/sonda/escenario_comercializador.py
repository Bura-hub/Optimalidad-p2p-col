"""
Sonda del escenario de comercializador (H-45).

Distinta de `techo_regimen.py`, y la diferencia es el fondo del asunto. Alli
solo se cambiaba el numero que entra al juego; aqui se cambia **el perfil
tarifario**, de modo que el cambio viaja al techo, al piso de permuta, al
limite economico de generacion, a la clasificacion en vendedores y
compradores y a la liquidacion. Por eso aqui el volumen SI puede moverse.

Tres escenarios:

  real       cuatro instituciones con ASC y el CESMAG con Cedenar, que es
             lo que dice el archivo de consumos y confirmo el asesor.
  asc        las cinco con ASC.
  cedenar    las cinco con Cedenar.

CUIDADO AL LEER, porque hay una trampa. El excedente del mercado es el ancho
de la banda por la energia transada, y el ancho de la banda es el cargo de
comercializar, que en Cedenar es mucho mayor que en ASC. Un escenario con
banda mas ancha produce MAS excedente de mercado y al mismo tiempo una
factura PEOR, porque la alternativa de red tambien es mas cara. Por eso esta
sonda informa las dos cosas:

  excedente   lo que el mercado ahorra frente a no tener mercado
  factura     lo que la comunidad paga de verdad, con mercado y sin el

El escenario que conviene es el de menor FACTURA, no el de mayor excedente.

Uso:
    python reformateo/documento/scripts/sonda/escenario_comercializador.py
        [--dia FECHA] [--muestra N]
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

ESCENARIOS = (("real", None), ("asc", "asc"), ("cedenar", "cedenar"))
SALIDA = AQUI.parents[1] / "validacion_horaria"

_DAT: dict = {}


def _datos(escenario: str, cobertura: str):
    from paso_a_paso import carga
    llave = (escenario, cobertura)
    if llave not in _DAT:
        com = dict(ESCENARIOS)[escenario]
        _DAT[llave] = carga(cobertura, comercializador=com)
    return _DAT[llave]


def _una(args):
    """Resuelve UNA hora en UN escenario. Corre en un proceso.

    La unidad de trabajo es la hora y el escenario, no la hora entera. Con
    los tres juntos una hora dificil retiene un proceso el triple y el
    reparto se desequilibra; separados, el que se desocupa toma la
    siguiente. Ademas cada proceso necesita entonces UN juego de datos y no
    tres, que es lo que multiplicaba la memoria.
    """
    cobertura, k, solo = args
    from core.settlement import compute_savings
    from paso_a_paso import resuelve

    filas = []
    for escenario, _ in [e for e in ESCENARIOS if e[0] == solo]:
        dat = _datos(escenario, cobertura)
        try:
            r = resuelve(dat, int(k))
        except Exception:
            r = None
        if r is None:
            filas.append(dict(cobertura=cobertura, hora=int(k),
                              escenario=escenario, resuelta=False))
            continue

        bids, sids = r["bids"], r["sids"]
        techo_i = dat["techo"][bids, int(k)]     # el de ESE escenario
        piso_j = r["piso_j"]
        P = np.asarray(r["P"], float)
        pi = np.asarray(r["pi"], float)
        G_net, D_net = r["G_net"], r["D_net"]

        S_i, SR_j = compute_savings(P, pi, techo_i, piso_j)
        excedente = float(S_i.sum() + SR_j.sum())

        # La factura de la comunidad SIN mercado: cada comprador cubre su
        # deficit en la red a su techo, y cada vendedor coloca su sobrante en
        # la red a su piso. Con mercado, la misma cuenta menos el excedente.
        sin_mercado = float(np.sum(D_net * techo_i) - np.sum(G_net * piso_j))

        filas.append(dict(
            cobertura=cobertura, hora=int(k), escenario=escenario,
            resuelta=True,
            J=len(sids), I=len(bids),
            volumen=float(P.sum()),
            oferta=float(G_net.sum()), demanda=float(D_net.sum()),
            techo_medio=float(np.mean(techo_i)),
            piso_medio=float(np.mean(piso_j)),
            ancho_banda=float(np.mean(techo_i)) - float(np.mean(piso_j)),
            excedente=excedente,
            ahorro=float(S_i.sum()), prima=float(SR_j.sum()),
            factura_sin=sin_mercado,
            factura_con=sin_mercado - excedente,
            retirados=len(r["retirados"]),
        ))
    return filas


def horas_del_dia(cobertura: str, fecha: str) -> list[int]:
    idx = pd.DatetimeIndex(_datos("real", cobertura)["idx"])
    return [int(i) for i in np.where(idx.strftime("%Y-%m-%d") == fecha)[0]]


def horas_activas(cobertura: str) -> np.ndarray:
    """Horas con vendedor y comprador en el escenario REAL, sin resolver."""
    from core.market_prep import classify_agents, compute_generation_limit
    from data.xm_prices import get_b_for_real_data

    dat = _datos("real", cobertura)
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
    ap.add_argument("--muestra", type=int, default=0)
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--procesos", type=int,
                    default=max(1, (os.cpu_count() or 4) - 2))
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

    # Una tarea por hora Y escenario. Ver la nota de `_una`.
    tareas = [(cob, k, esc) for cob, k in horas for esc, _ in ESCENARIOS]
    print(f"  {len(horas)} horas · {len(ESCENARIOS)} escenarios = "
          f"{len(tareas)} tareas · {args.procesos} procesos", flush=True)

    # Los tres juegos de datos se arman AQUI, antes de abrir los procesos. En
    # Linux los hijos heredan esa memoria sin copiarla, de modo que ninguno
    # vuelve a leer el 1,7 GB de mediciones ni a rehacer las tarifas. Sin
    # esto cada proceso lo hacia por su cuenta, y con treinta procesos eso
    # son treinta lecturas del mismo disco al arrancar.
    coberturas = sorted({c for c, _ in horas})
    for esc, _ in ESCENARIOS:
        for cob in coberturas:
            _datos(esc, cob)
    print(f"  datos en memoria: {len(_DAT)} juegos "
          f"({len(ESCENARIOS)} escenarios x {len(coberturas)} fronteras)",
          flush=True)

    # Reparto de a UNA tarea y recogida por terminacion, no por orden de
    # envio. Con el reparto en bloques del defecto, un trabajador al que le
    # tocan dos horas dificiles muele mientras los demas terminan y se
    # paran: medido el 2026-09-07, dos procesos a pleno rendimiento y dos
    # parados, con el contador detenido en 10 de 80 durante 49 minutos
    # porque la primera hora lenta retenia toda la cuenta.
    filas = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.procesos) as ex:
        pendientes = {ex.submit(_una, t): t for t in tareas}
        for i, fut in enumerate(as_completed(pendientes), 1):
            filas.extend(fut.result())
            if i % 5 == 0 or i == len(tareas):
                seg = time.time() - t0
                queda = seg / i * (len(tareas) - i)
                print(f"    {i}/{len(tareas)}  ({seg/60:.1f} min, "
                      f"faltan ~{queda/60:.0f})", flush=True)

    d = pd.DataFrame(filas)
    SALIDA.mkdir(parents=True, exist_ok=True)
    csv = SALIDA / f"escenario_comercializador_{etiqueta}.csv"
    d.to_csv(csv, index=False)

    ok = d[d.resuelta.fillna(False)]
    print(flush=True)
    print(f"  Escenario de comercializador · {etiqueta}", flush=True)
    print("  " + "=" * 84, flush=True)
    for cob in ("m1", "m3"):
        s = ok[ok.cobertura == cob]
        if s.empty:
            continue
        print(flush=True)
        print(f"  frontera {cob.upper()}", flush=True)
        print(f"  {'escenario':>10s} {'horas':>6s} {'volumen':>9s} "
              f"{'banda':>8s} {'excedente':>11s} {'factura sin':>12s} "
              f"{'factura con':>12s} {'ahorro %':>9s}", flush=True)
        for esc, _ in ESCENARIOS:
            t = s[s.escenario == esc]
            if t.empty:
                continue
            sin, con = t.factura_sin.sum(), t.factura_con.sum()
            print(f"  {esc:>10s} {len(t):6d} {t.volumen.sum():9.2f} "
                  f"{t.ancho_banda.mean():8.1f} {t.excedente.sum():11.1f} "
                  f"{sin:12.1f} {con:12.1f} "
                  f"{100.0 * (sin - con) / abs(sin) if abs(sin) > 1e-9 else 0:9.2f}",
                  flush=True)
    print(flush=True)
    print(f"  csv: {csv}", flush=True)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
