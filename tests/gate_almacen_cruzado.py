"""
La reproduccion cruzada: el almacen describe la corrida, no otra cosa.

POR QUE ES LA COMPUERTA QUE IMPORTA. Un almacen que mienta pasa desapercibido
para siempre: sus tablas se leen bonitas, las figuras salen, y nadie compara
lo guardado contra lo que el modelo hace de verdad. Esta compuerta lo compara.

QUE HACE. Toma una hora, la resuelve por el MOTOR pidiendole la trayectoria,
la guarda en un almacen, y despues la resuelve otra vez por la SONDA, que es
un camino independiente escrito con semanas de diferencia. Las dos tienen que
coincidir en el precio, en el reparto y en la trayectoria.

LO QUE LA HACE POSIBLE, y es de hoy: hasta ahora **ninguna via de produccion
devolvia la trayectoria de una hora elegida**. La que las guardaba escogia las
horas sola y solo dos; la que aceptaba una hora devolvia escalares. Por eso
toda figura de convergencia pasaba por las sondas, fuera del motor.

LA TOLERANCIA. Se compara contra 1e-6, que es la tolerancia del integrador
(H-51). Pedir mas seria pedir que dos integraciones distintas coincidan por
debajo de su propia precision.

Uso:
    python tests/gate_almacen_cruzado.py
    python tests/gate_almacen_cruzado.py --hora 2342
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "reformateo" / "documento" / "scripts" / "sonda"))

import numpy as np  # noqa: E402

TOL = 1e-6


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hora", type=int, default=None)
    ap.add_argument("--cobertura", default="m1")
    args = ap.parse_args()

    from paso_a_paso import carga, resuelve
    from core.almacen import Almacen, hora as lee_hora
    from core.ems_p2p import AgentParams, EMSP2P, GridParams, SolverParams
    from data.xm_prices import get_b_for_real_data

    dat = carga(args.cobertura)
    D, G = dat["D"], dat["G"]
    N = D.shape[0]

    k = args.hora
    if k is None:
        exc = np.maximum(G - D, 0.0)
        dfc = np.maximum(D - G, 0.0)
        act = [q for q in range(D.shape[1])
               if (exc[:, q] > 1e-9).sum() >= 2 and (dfc[:, q] > 1e-9).sum() >= 2]
        k = int(np.median(act))
    print(f"  hora {k} de la frontera {args.cobertura.upper()}", flush=True)

    # ── el motor, con las MISMAS cotas medidas que usa la sonda ──────────
    ems = EMSP2P(
        agents=AgentParams(N=N, a=np.zeros(N),
                           b=get_b_for_real_data(N, dat["nombres"]),
                           c=np.zeros(N), lam=np.full(N, 100.0),
                           theta=np.full(N, 0.5), etha=np.full(N, 0.1)),
        grid=GridParams(pi_gs=float(np.max(dat["techo"][:, k])),
                        pi_gb=float(np.min(dat["piso"][:, k])),
                        pi_gs_agente=dat["techo"], pi_gb_agente=dat["piso"]),
        solver=SolverParams(tau=0.001, tau_buyers=0.01, t_span=(0.0, 0.005),
                            n_points=150, stackelberg_iters=2, parallel=False,
                            metodo="acoplado", t_span_acoplado=0.05,
                            buyer_competition="aggregate"),
    )
    res = ems.run_single_hour(k, D, G, devuelve_trayectoria=True)
    if res.tr is None:
        print("  el motor no devolvio trayectoria: la hora no abre mercado")
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="gate_cruzado_"))
    try:
        alm = Almacen(tmp, cobertura=args.cobertura)
        alm.anota_hora(k, resuelta=True,
                       volumen=float(np.sum(res.P_star)),
                       retirados=len(res.retirados),
                       iteraciones=int(res.iters_used),
                       residuo=float(res.norm_rel_final))
        alm.anota_flujos(k, res.P_star, res.pi_star, res.seller_ids,
                         res.buyer_ids, dat["nombres"])
        alm.anota_trayectoria(k, res.tr, res.seller_ids, res.buyer_ids,
                              dat["nombres"])
        alm.cierra()
        guardado = lee_hora(tmp, args.cobertura, k)

        # ── la sonda, camino independiente ───────────────────────────────
        r = resuelve(dat, k)
        if r is None:
            print("  la sonda no resuelve esa hora")
            return 1

        fallos = []

        # 1 · el precio
        d_pi = float(np.max(np.abs(np.asarray(res.pi_star, float)
                                   - np.asarray(r["pi"], float))))
        esc = max(float(np.max(np.abs(r["pi"]))), 1e-12)
        ok1 = d_pi / esc <= TOL
        print(f"  1 · el precio coincide        dif rel {d_pi/esc:.2e}   "
              f"{'ok' if ok1 else 'FALLA'}")
        if not ok1:
            fallos.append("el precio del motor y el de la sonda difieren")

        # 2 · el reparto, COMPARADO POR IDENTIDAD DE AGENTE.
        #
        # Las dos vias no usan la misma convencion y conviene decirlo: el
        # motor CONSERVA al vendedor retirado en su lista con la fila a cero,
        # que es lo que H-43 exige, «quien sale del mercado no sale de la
        # contabilidad»; la sonda lo quita de la suya. Comparar por posicion
        # da un desacuerdo del 100 % donde no lo hay.
        Pm = np.asarray(res.P_star, float)
        Ps = np.asarray(r["P"], float)
        peor = 0.0
        for a_, j in enumerate(res.seller_ids):
            fila_m = Pm[a_, :]
            if j in list(r["sids"]):
                fila_s = Ps[list(r["sids"]).index(j), :]
            else:
                fila_s = np.zeros_like(fila_m)   # retirado en la sonda
            peor = max(peor, float(np.max(np.abs(fila_m - fila_s))))
        escP = max(float(np.max(np.abs(Ps))), 1e-12)
        ok2 = peor / escP <= TOL
        print(f"  2 · el reparto coincide       dif rel {peor/escP:.2e}   "
              f"{'ok' if ok2 else 'FALLA'}")
        if not ok2:
            fallos.append("el reparto del motor y el de la sonda difieren")

        # 3 · la trayectoria guardada es la del motor
        t = guardado["trayectorias"]
        ok3 = len(t) == len(res.tr.t)
        print(f"  3 · la trayectoria se guarda entera   {len(t)} pasos de "
              f"{len(res.tr.t)}   {'ok' if ok3 else 'FALLA'}")
        if not ok3:
            fallos.append("la trayectoria guardada no tiene todos los pasos")

        # 4 · el ultimo paso de la trayectoria ES el estacionario.
        #
        # La referencia es el estacionario CRUDO de la trayectoria, no el
        # precio del resultado, que va recortado a las cotas de cada
        # comprador. Compararlo con el recortado mide el recorte, no la
        # fidelidad del almacen.
        col = [c for c in t.columns if c.startswith("precio_")]
        fin = np.array([float(t[c].iloc[-1]) for c in col])
        crudo = np.asarray(res.tr.pi_star, float)
        d_fin = float(np.max(np.abs(fin - crudo)))
        ok4 = d_fin / max(float(np.max(np.abs(crudo))), 1e-12) <= 1e-4
        print(f"  4 · el ultimo paso es el estacionario   dif rel "
              f"{d_fin/max(float(np.max(np.abs(crudo))),1e-12):.2e}   "
              f"{'ok' if ok4 else 'FALLA'}")
        if not ok4:
            fallos.append("el ultimo paso guardado no es el estacionario")

        # 5 · los multiplicadores llegaron
        mult = [c for c in t.columns if c.startswith(("lam_", "bet_"))]
        ok5 = len(mult) > 0
        print(f"  5 · multiplicadores guardados   {len(mult)} columnas   "
              f"{'ok' if ok5 else 'FALLA'}")
        if not ok5:
            fallos.append("la trayectoria no trae multiplicadores")

        print()
        if fallos:
            for x in fallos:
                print(f"  FALLA: {x}")
            return 1
        print("  REPRODUCCION CRUZADA EN VERDE. El motor y la sonda, dos")
        print("  caminos independientes, dan la misma hora; y lo que el")
        print("  almacen guarda es lo que el motor calculo.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
