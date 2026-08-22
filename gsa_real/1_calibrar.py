"""PASO 1 — Medir el costo de una evaluacion antes de comprometer la corrida.

Cada sonda corre con TIMEOUT y en proceso aislado. Sin eso, una sonda cara
bloquea el paso que existe justamente para descubrir que hay sondas caras.

La proyeccion incluye el costo de la carga de datos, que en la corrida real se
paga una vez (queda cacheada en .npz) pero conviene ver por separado.

Uso
---
    bash gsa_real/run_servidor.sh calibrar M1 full 128
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import (FACTOR_SALTELLI, NOMBRES, PROBLEMA, asegurar_salida,  # noqa: E402
                   cargar_datos, evaluar)

TECHO_SONDA_S = 1800     # ninguna sonda puede bloquear mas de media hora


def puntos_sonda():
    """De la mas barata a la mas cara: si la primera ya se pasa de tiempo, se
    sabe enseguida en vez de esperar a la ultima."""
    lo = np.array([b[0] for b in PROBLEMA["bounds"]])
    hi = np.array([b[1] for b in PROBLEMA["bounds"]])
    mid = (lo + hi) / 2.0
    poco_sol = mid.copy(); poco_sol[2] = lo[2]          # factor_PV bajo
    mucho_sol = mid.copy(); mucho_sol[2] = hi[2]        # factor_PV alto
    return [("minimos", lo), ("poco sol", poco_sol), ("centro", mid),
            ("mucho sol", mucho_sol), ("maximos", hi)]


def _sonda(args):
    params, cob, hor = args
    return evaluar(params, cob, hor)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cobertura", choices=["M1", "M3"], default="M1")
    ap.add_argument("--horizonte", default="full")
    ap.add_argument("--n-base-objetivo", type=int, default=128)
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()

    workers = args.workers or max(1, (multiprocessing.cpu_count() or 4) - 2)
    print("=" * 70)
    print(f"CALIBRACION  cobertura={args.cobertura}  horizonte={args.horizonte}")
    print("=" * 70)
    print(f"  metodo de arranque de procesos: {multiprocessing.get_start_method()}")

    t0 = time.time()
    D, G, pb, nombres, _pi_gs_mat, pi_gs_eff, _extras = cargar_datos(
        args.cobertura, args.horizonte, verbose=True)
    t_carga = time.time() - t0
    print(f"\n  datos: N={D.shape[0]}  T={D.shape[1]} h   (carga {t_carga:.1f} s)")
    print(f"  agentes: {', '.join(nombres)}")
    print(f"  cobertura G/D: {G.sum()/D.sum():.4f}")
    print(f"  bolsa real: media {pb.mean():.1f}  max {pb.max():.1f} COP/kWh")
    print(f"  pi_gs nominal del caso: {pi_gs_eff:.2f} COP/kWh "
          f"({'DENTRO' if PROBLEMA['bounds'][1][0] <= pi_gs_eff <= PROBLEMA['bounds'][1][1] else 'FUERA'} "
          f"del soporte de PGS {PROBLEMA['bounds'][1]})")
    print(f"  parametros barridos ({len(NOMBRES)}): {', '.join(NOMBRES)}\n")

    tiempos, fallos = [], 0
    for etiqueta, p in puntos_sonda():
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_sonda, (p, args.cobertura, args.horizonte))
            try:
                g, sc, ie, br, motivo = fut.result(timeout=TECHO_SONDA_S)
            except Exception as exc:
                for pr in (ex._processes or {}).values():
                    try:
                        pr.kill()
                    except Exception:
                        pass
                g = sc = ie = br = float("nan")
                motivo = f"TIMEOUT>{TECHO_SONDA_S}s" if "Timeout" in type(exc).__name__ \
                    else type(exc).__name__
        dt = time.time() - t0
        ok = not np.isnan(g)
        if ok:
            tiempos.append(dt)
        else:
            fallos += 1
        detalle = (f"ganancia={g:.4e}  SC={sc:.4f}  IE={ie:+.4f}  "
                   f"brecha_C1={br:+.4e}" if ok
                   else f"FALLO [{motivo}]")
        print(f"  {etiqueta:<11} {dt:>8.1f} s   {detalle}", flush=True)

    if not tiempos:
        print("\n  ERROR: ninguna sonda completo. Revisar MTE_ROOT y los datos.")
        return 1

    t_med = float(np.median(tiempos))
    t_max = float(np.max(tiempos))
    M = args.n_base_objetivo * FACTOR_SALTELLI
    sec = M * t_med
    par = sec / workers

    print()
    print("=" * 70)
    print("PROYECCION")
    print("=" * 70)
    print(f"  mediana por evaluacion   {t_med:>9.1f} s")
    print(f"  maxima observada         {t_max:>9.1f} s   ({fallos} fallos)")
    print(f"  M = n_base*{FACTOR_SALTELLI} con n_base={args.n_base_objetivo}: "
          f"{M} evaluaciones")
    print(f"  secuencial               {sec/3600:>9.1f} h")
    print(f"  con {workers} procesos   {par/3600:>9.1f} h   ({par/86400:.2f} dias)")
    print()
    rec = max(120, int(15 * t_max))
    print(f"  TIMEOUT RECOMENDADO: {rec} s  (15x la sonda mas lenta)")
    print()
    if par / 3600 <= 12:
        print(f"  CABE. Lanzar:  bash gsa_real/run_servidor.sh correr "
              f"{args.cobertura} {args.horizonte} {args.n_base_objetivo} {rec}")
    else:
        n_alt = max(32, args.n_base_objetivo // 4)
        print(f"  NO CABE en 12 h. Opciones, en orden de preferencia:")
        print(f"    a) n_base {n_alt}  ->  {par*n_alt/args.n_base_objetivo/3600:.1f} h "
              f"(intervalos mas anchos)")
        print(f"    b) --horizonte mes:2025-08  ->  ~1/8 del costo por evaluacion")
        print(f"    Preferir (b) sobre (a): un n_base bajo da intervalos tan")
        print(f"    anchos que la comparacion deja de ser informativa.")

    destino = asegurar_salida() / (
        f"calibracion_{args.cobertura}_{args.horizonte.replace(':','-')}.json")
    destino.write_text(json.dumps({
        "cobertura": args.cobertura, "horizonte": args.horizonte,
        "metodo_arranque": multiprocessing.get_start_method(),
        "N": int(D.shape[0]), "T": int(D.shape[1]),
        "cobertura_GD": float(G.sum() / D.sum()),
        "bolsa_media": float(pb.mean()),
        "t_carga_s": t_carga, "tiempos_s": tiempos, "fallos": fallos,
        "t_mediana_s": t_med, "t_maxima_s": t_max,
        "workers": workers, "n_base_objetivo": args.n_base_objetivo, "M": M,
        "proyeccion_secuencial_h": sec / 3600,
        "proyeccion_paralela_h": par / 3600,
        "timeout_recomendado_s": rec,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  escrito {destino.name}")
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
