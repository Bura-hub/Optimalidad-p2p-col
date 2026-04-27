"""
probe_gsa_samples.py — Diagnóstico: identifica qué samples Saltelli cuelgan.

Uso:
    python -u scripts/probe_gsa_samples.py [N_PROBE] [TIMEOUT]
"""
from __future__ import annotations

import io
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FTimeout
from multiprocessing import freeze_support
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _wrap(args):
    idx, x = args
    t0 = time.time()
    try:
        from analysis.global_sensitivity import _eval_sample
        r = _eval_sample(x)
        return idx, time.time() - t0, r, None
    except Exception as e:
        return idx, time.time() - t0, None, repr(e)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))

    import numpy as np
    from SALib.sample.sobol import sample as sobol_sample
    from analysis.global_sensitivity import _build_problem, _PARAM_NAMES

    n_probe = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    problem = _build_problem()
    X = sobol_sample(problem, N=128, calc_second_order=True, seed=42, skip_values=0)
    print(f"Saltelli total: {len(X)} samples; probando {n_probe} primeros (timeout={timeout}s)")
    print(f"Parámetros: {_PARAM_NAMES}\n")

    cuelga = []
    for i in range(n_probe):
        sample_dict = {n: round(float(v), 3) for n, v in zip(_PARAM_NAMES, X[i])}
        print(f"[{i:3d}] {sample_dict}")
        with ProcessPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_wrap, (i, X[i]))
            try:
                idx, dt, r, err = fut.result(timeout=timeout)
                if err:
                    print(f"      EXCEPTION en {dt:.1f}s: {err}")
                else:
                    g, sc, ie = r
                    print(f"      OK en {dt:.1f}s: ganancia={g:,.0f}, sc={sc:.3f}, ie={ie:.3f}")
            except FTimeout:
                print(f"      TIMEOUT >{timeout}s — sample CUELGA")
                cuelga.append((i, sample_dict))
                for p in ex._processes.values():
                    try:
                        p.kill()
                    except Exception:
                        pass

    print(f"\n=== Resumen: {len(cuelga)}/{n_probe} cuelgan ===")
    for i, s in cuelga:
        print(f"  [{i}] {s}")
    return 0


if __name__ == "__main__":
    freeze_support()
    sys.exit(main())
