"""DIAGNOSTICO — ¿el NaN de LSODA alcanza la potencia transada?

POR QUE EXISTE
--------------
Durante la calibracion sobre datos reales, LSODA emite avisos del tipo

    lsoda--  at t (=r1), too much accuracy requested
             for precision of machine..  see tolsf (=r2)
             r2 = NaN

`tolsf` es el factor de escala de tolerancia de ODEPACK: `eps * ||y||_ewt`, con
`ewt_i = rtol*|y_i| + atol`. Con rtol=1e-6 y atol=1e-6 los pesos no pueden ser
cero, de modo que **tolsf = NaN implica que el vector de estado ya contiene un
NaN o un infinito**.

Y hay algo peor, verificado: LSODA devuelve `sol.success = True` con el estado
en NaN. Comprobar `sol.success` —que `core/replicator_sellers.py` no hace— NO
protegeria. La comprobacion util seria `np.isfinite(sol.y)`.

La pregunta que este guion responde: **¿el NaN alcanza el bloque de P?**

El estado es `y = [P.ravel() (J*I), lam (J), bet (J), lam_filt (J), bet_filt (I)]`
y `solve_sellers` solo lee `sol.y[:J*I, -1]`. Si el NaN se queda en los filtros
—que son la parte rigida, con tau=1e-3— los resultados son sanos. Si alcanza P,
entrarian numeros malos sin ninguna alarma, porque `np.clip` propaga NaN y
nadie mira.

NO MODIFICA NADA. Envuelve `solve_ivp` desde fuera para auditar cada llamada.

Uso
---
    .venv/bin/python gsa_real/diagnostico_lsoda.py --cobertura M1 --horas 400
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import RAIZ, cargar_datos  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cobertura", choices=["M1", "M3"], default="M1")
    ap.add_argument("--horizonte", default="full")
    ap.add_argument("--horas", type=int, default=400,
                    help="cuantas horas auditar (desde el inicio)")
    # Esquina degenerada: es donde LSODA se queja. Son los limites inferiores
    # del hipercubo, la sonda `minimos` de la calibracion.
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

    # ── auditoria: se envuelve solve_ivp SIN tocar core/ ───────────────────
    conteo = {"llamadas": 0, "success_false": 0,
              "estado_no_finito": 0, "P_no_finito": 0, "cols_faltantes": 0}
    peor = {"t": None, "bloque": None}
    original = si.solve_ivp

    def auditado(fun, t_span, y0, **kw):
        sol = original(fun, t_span, y0, **kw)
        conteo["llamadas"] += 1
        if not sol.success:
            conteo["success_false"] += 1
        y = np.asarray(sol.y)
        if kw.get("t_eval") is not None and y.shape[1] != len(kw["t_eval"]):
            conteo["cols_faltantes"] += 1
        if not np.all(np.isfinite(y)):
            conteo["estado_no_finito"] += 1
            # ¿en que bloque? P ocupa las primeras J*I filas; el resto son
            # lam, bet y los dos filtros.
            malas = ~np.isfinite(y).all(axis=1)
            idx = np.where(malas)[0]
            if peor["bloque"] is None:
                peor["bloque"] = idx.tolist()
                peor["t"] = float(sol.t[-1]) if len(sol.t) else None
        return sol

    # `solve_sellers` importa solve_ivp por nombre: hay que parchear ALLI.
    rs.solve_ivp = auditado

    D, G, pi_bolsa, nombres, pi_gs_mat, pi_gs_eff, _extras = cargar_datos(
        args.cobertura, args.horizonte, verbose=False)
    T = min(args.horas, D.shape[1])
    D, G = D[:, :T] * args.f_d, G[:, :T] * args.f_pv
    N = D.shape[0]

    print("=" * 70)
    print(f"DIAGNOSTICO LSODA  {args.cobertura}  primeras {T} h")
    print("=" * 70)
    print(f"  punto: PGB={args.pgb} PGS={args.pgs} f_pv={args.f_pv} "
          f"f_d={args.f_d} b={args.b}")

    agents = AgentParams(
        N=N, a=np.zeros(N), b=np.full(N, args.b), c=np.zeros(N),
        lam=np.full(N, 100.0), theta=np.full(N, 0.5), etha=np.full(N, 0.1))
    grid = GridParams(pi_gs=args.pgs, pi_gb=args.pgb)
    solver = SolverParams(tau=0.001, t_span=(0.0, 0.005), n_points=150,
                          stackelberg_iters=2, parallel=False)

    resultados, G_klim, D_star = EMSP2P(agents, grid, solver).run(D, G)

    # ── que salio de ahi ───────────────────────────────────────────────────
    P_nan = sum(1 for r in resultados
                if r.P_star is not None and not np.all(np.isfinite(r.P_star)))
    pi_nan = sum(1 for r in resultados
                 if r.pi_star is not None and not np.all(np.isfinite(r.pi_star)))
    activas = sum(1 for r in resultados
                  if r.P_star is not None and np.nansum(r.P_star) > 1e-9)

    print()
    print(f"  llamadas a solve_ivp        {conteo['llamadas']}")
    print(f"  con success=False           {conteo['success_false']}")
    print(f"  con columnas faltantes      {conteo['cols_faltantes']}")
    print(f"  con ESTADO no finito        {conteo['estado_no_finito']} "
          f"({100*conteo['estado_no_finito']/max(1,conteo['llamadas']):.1f} %)")
    if peor["bloque"] is not None:
        J = N
        filas_P = [i for i in peor["bloque"] if i < J * J]
        filas_otras = [i for i in peor["bloque"] if i >= J * J]
        print(f"    primer caso: filas no finitas {peor['bloque']}")
        print(f"      en el bloque de P (indices < {J*J}): "
              f"{filas_P if filas_P else 'NINGUNA'}")
        print(f"      en lam/bet/filtros:              {filas_otras}")
    print()
    print(f"  horas con mercado activo    {activas}/{T}")
    print(f"  horas con P_star no finito  {P_nan}")
    print(f"  horas con pi_star no finito {pi_nan}")
    print()
    print("=" * 70)
    if P_nan == 0 and pi_nan == 0:
        print("  VEREDICTO: el NaN NO alcanza la potencia transada ni el precio.")
        print("  Los avisos de LSODA son ruido del bloque rigido (los filtros)")
        print("  y no contaminan las magnitudes que se leen.")
        return 0
    print("  VEREDICTO: el NaN SI alcanza magnitudes que se leen.")
    print(f"    P_star no finito en {P_nan} horas, pi_star en {pi_nan}.")
    print("  Esto NO se detecta aguas arriba: LSODA devuelve success=True con")
    print("  el estado en NaN. Hay que declararlo antes de publicar indices.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
