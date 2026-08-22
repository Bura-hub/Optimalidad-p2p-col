"""DIAGNOSTICO — ¿el `max_step` de produccion produce resultados equivocados?

LA PREGUNTA
-----------
`core/replicator_sellers.py:157` fija

    _max_step = 2e-4  # con VEL_GRAD_GSA=1e3: step×eigenvalue <= 2e-4*1e4=2<2.5

pero esa linea NO esta dentro del `if _fast_mode`, a diferencia de `_rtol` y
`_atol` (lineas 155-156). Y `_fast_mode` es False por defecto (linea 30), de
modo que la linea 62 toma `_vg = VEL_GRAD = 1e6`, no `VEL_GRAD_GSA = 1e3`.

Con el autovalor mil veces mayor, la propia aritmetica del comentario da
`2e-4 * 1e7 = 2000`, no 2. Es decir: **la justificacion del valor cita un
regimen que produccion no usa**. Y esto no es exclusivo del GSA — el
orquestador (`main_simulation.py`) corre con el mismo `_fast_mode=False`.

LO QUE ESO NO IMPLICA
---------------------
`max_step` es una COTA SUPERIOR, no un paso fijo. LSODA es adaptativo: si el
Newton no converge, reduce el paso por su cuenta. Un techo demasiado alto es,
en principio, un problema de eficiencia y de robustez, no necesariamente de
correccion. Que el comentario este mal NO demuestra que los numeros lo esten.

EL EXPERIMENTO
--------------
Se envuelve `solve_ivp` desde fuera (sin tocar `core/`) y se guardan los
argumentos EXACTOS de cada integracion cuyo estado devuelto contenga algun
valor no finito. Despues se resuelve cada una de nuevo con un `max_step`
coherente con VEL_GRAD=1e6 —el que el propio comentario pediria, h <= 2.5/1e7—
y se compara el estado final, que es lo unico que `solve_sellers` lee.

  * Si coinciden, el techo alto es cosmetico: LSODA ya se estaba
    autorregulando y los resultados publicados son correctos.
  * Si difieren, hay numeros plausibles pero equivocados en el pipeline
    canonico, y eso hay que resolverlo antes de publicar nada.

NO MODIFICA NADA.

Uso
---
    .venv/bin/python gsa_real/diagnostico_maxstep.py --cobertura M1 --horas 6144
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import cargar_datos  # noqa: E402

# h <= 2.5 / autovalor, con autovalor ~ VEL_GRAD * 10 = 1e7. Es el mismo
# criterio que el comentario de la linea 157, aplicado al VEL_GRAD real.
MAX_STEP_COHERENTE = 2.5e-7


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cobertura", choices=["M1", "M3"], default="M1")
    ap.add_argument("--horizonte", default="full")
    ap.add_argument("--horas", type=int, default=6144)
    ap.add_argument("--max-replays", type=int, default=25,
                    help="cuantas integraciones sospechosas re-resolver")
    ap.add_argument("--pgb", type=float, default=114.0)
    ap.add_argument("--pgs", type=float, default=600.0)
    ap.add_argument("--f-pv", type=float, default=0.5)
    ap.add_argument("--f-d", type=float, default=0.7)
    ap.add_argument("--b", type=float, default=150.0)
    args = ap.parse_args()

    import scipy.integrate as si
    from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams
    import core.replicator_sellers as rs

    rs._fast_mode = False
    print("=" * 70)
    print("DIAGNOSTICO max_step  —  ¿numeros plausibles pero equivocados?")
    print("=" * 70)
    print(f"  VEL_GRAD efectivo   {rs.VEL_GRAD if not rs._fast_mode else rs.VEL_GRAD_GSA:.0e}")
    print(f"  max_step que corre  {2e-4:.1e}   (justificado para VEL_GRAD=1e3)")
    print(f"  max_step coherente  {MAX_STEP_COHERENTE:.1e}   (para VEL_GRAD=1e6)")
    print(f"  punto: PGB={args.pgb} PGS={args.pgs} f_pv={args.f_pv} "
          f"f_d={args.f_d} b={args.b}")

    original = si.solve_ivp
    sospechosas = []
    n_llamadas = 0

    def auditado(fun, t_span, y0, **kw):
        nonlocal n_llamadas
        sol = original(fun, t_span, y0, **kw)
        n_llamadas += 1
        if not np.all(np.isfinite(np.asarray(sol.y))):
            if len(sospechosas) < args.max_replays:
                # copia defensiva: y0 y args son reutilizados por el llamador
                sospechosas.append((fun, tuple(t_span), np.array(y0, copy=True),
                                    dict(kw), np.array(sol.y[:, -1], copy=True)))
        return sol

    rs.solve_ivp = auditado

    D, G, pi_bolsa, nombres, pi_gs_mat, pi_gs_eff, _extras = cargar_datos(
        args.cobertura, args.horizonte, verbose=False)
    T = min(args.horas, D.shape[1])
    D, G = D[:, :T] * args.f_d, G[:, :T] * args.f_pv
    N = D.shape[0]

    agents = AgentParams(
        N=N, a=np.zeros(N), b=np.full(N, args.b), c=np.zeros(N),
        lam=np.full(N, 100.0), theta=np.full(N, 0.5), etha=np.full(N, 0.1))
    grid = GridParams(pi_gs=args.pgs, pi_gb=args.pgb)
    solver = SolverParams(tau=0.001, t_span=(0.0, 0.005), n_points=150,
                          stackelberg_iters=2, parallel=False)
    EMSP2P(agents, grid, solver).run(D, G)

    rs.solve_ivp = original     # a partir de aqui, sin auditoria

    print(f"\n  integraciones            {n_llamadas}")
    print(f"  con estado no finito     {len(sospechosas)} (guardadas para replay)")
    if not sospechosas:
        print("\n  No hubo ninguna. Nada que comparar en este punto del "
              "hipercubo.")
        return 0

    # ── replay con el max_step coherente ───────────────────────────────────
    print(f"\n  Re-resolviendo {len(sospechosas)} con max_step="
          f"{MAX_STEP_COHERENTE:.1e} ...\n")
    print(f"    {'#':>3}  {'|dP| max':>12}  {'|dP| rel':>10}  {'P_tot act':>12}"
          f"  {'P_tot ref':>12}  finito")
    peor_abs = peor_rel = 0.0
    n_finitas = 0
    for i, (fun, t_span, y0, kw, y_final_actual) in enumerate(sospechosas):
        kw2 = dict(kw)
        kw2["max_step"] = MAX_STEP_COHERENTE
        sol2 = original(fun, t_span, y0, **kw2)
        y_ref = np.asarray(sol2.y[:, -1])
        fin = bool(np.all(np.isfinite(y_ref)))
        n_finitas += int(fin)
        # Solo el bloque de P importa: es lo unico que solve_sellers lee.
        nP = N * N
        Pa = np.clip(np.nan_to_num(y_final_actual[:nP], nan=0.0), 0.0, None)
        Pr = np.clip(np.nan_to_num(y_ref[:nP], nan=0.0), 0.0, None)
        d_abs = float(np.max(np.abs(Pa - Pr)))
        denom = max(float(np.max(np.abs(Pr))), 1e-12)
        d_rel = d_abs / denom
        peor_abs = max(peor_abs, d_abs)
        peor_rel = max(peor_rel, d_rel)
        print(f"    {i:>3}  {d_abs:>12.4e}  {d_rel:>10.2e}  "
              f"{Pa.sum():>12.4f}  {Pr.sum():>12.4f}  {'si' if fin else 'NO'}")

    print()
    print("=" * 70)
    print(f"  replays con estado final finito : {n_finitas}/{len(sospechosas)}")
    print(f"  peor discrepancia absoluta en P : {peor_abs:.6e} kW")
    print(f"  peor discrepancia relativa en P : {peor_rel:.6e}")
    print()
    if peor_rel < 1e-6:
        print("  VEREDICTO: el techo alto es COSMETICO. LSODA ya se autorregula")
        print("  y el estado final coincide con el del max_step coherente.")
        print("  Los resultados publicados no estan afectados.")
        return 0
    print("  VEREDICTO: el max_step SI cambia el resultado.")
    print("  Hay numeros plausibles pero distintos en el pipeline canonico.")
    print("  NO lanzar las 896 evaluaciones hasta resolverlo, y revisar que")
    print("  implica para las corridas canonicas ya publicadas.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
