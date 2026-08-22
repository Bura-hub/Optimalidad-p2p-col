"""DIAGNOSTICO — ¿las MAGNITUDES PUBLICADAS dependen del ajuste del integrador?

POR QUE ESTE Y NO EL ANTERIOR
-----------------------------
`diagnostico_maxstep.py` intentaba comparar estados internos de LSODA y no
sirve: (a) convertia los NaN del caso actual a cero antes de comparar, de modo
que toda diferencia salia 1,00 por construccion; y (b) su referencia
—`max_step=2.5e-7` sobre `t_span=0.005`— obliga a 20 000 pasos, LSODA topa sus
limites internos y devuelve valores absurdos (P_tot de 3e5 kW cuando la
comunidad entera mueve del orden de 50 kW). Dos fallos, ningun veredicto.

Ademas la pregunta estaba mal planteada. Que un estado INTERMEDIO tenga NaN no
dice nada por si solo: con `stackelberg_iters=2` cada hora resuelve varias
veces y solo la ultima alimenta el resultado. Lo que decide si hay un problema
es si **las tres magnitudes que se publican cambian** al mover el ajuste del
integrador.

EL EXPERIMENTO
--------------
Se corre el MISMO punto del hipercubo con varias configuraciones del
integrador, inyectadas envolviendo `solve_ivp` desde fuera (sin tocar `core/`),
y se comparan `ganancia`, `sc` e `ie` — exactamente lo que lee el GSA.

  * Si las tres coinciden entre configuraciones, los resultados son robustos al
    ajuste y los NaN intermedios son irrelevantes: LSODA se autorregula.
  * Si difieren, el numero publicado depende de un parametro cuya
    justificacion —`core/replicator_sellers.py:157`— cita un regimen que
    produccion no usa, y eso afecta a las corridas canonicas, no solo al GSA.

NO MODIFICA NADA.

Uso
---
    .venv/bin/python gsa_real/diagnostico_robustez_solver.py --horizonte mes:2025-08
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Configuraciones a contrastar. La primera es la de PRODUCCION tal cual.
# Las demas la aprietan por vias distintas para que un acuerdo no pueda venir
# de que todas fallen igual.
# Ojo con apretar `max_step`: sobre t_span=0.005 un techo de 1e-6 fuerza 5000
# pasos por integracion y multiplica el coste por cien —tres horas para una
# sola configuracion—. La comparacion util no es bajar el techo a mano sino
# CONTRASTAR INTEGRADORES INDEPENDIENTES, todos adaptativos:
#
#   * quitar el techo (max_step=inf) prueba directamente si el 2e-4 importa;
#   * BDF y Radau son otros dos metodos rigidos, con control de paso propio;
#   * rtol/atol mas estrictos apretan la precision sin imponer un paso minimo.
#
# Si cuatro integradores distintos coinciden, el resultado no es un artefacto
# de ninguno de ellos.
CONFIGS = [
    ("produccion",      {}),
    ("sin max_step",    {"max_step": np.inf}),
    ("BDF",             {"method": "BDF"}),
    ("Radau",           {"method": "Radau"}),
    ("tol 1e-9/1e-12",  {"rtol": 1e-9, "atol": 1e-12}),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cobertura", choices=["M1", "M3"], default="M1")
    ap.add_argument("--horizonte", default="mes:2025-08")
    # Por defecto el CENTRO del hipercubo: el punto mas representativo. La
    # esquina degenerada se prueba con --punto minimos.
    ap.add_argument("--punto", choices=["centro", "minimos", "mucho-sol"],
                    default="centro")
    args = ap.parse_args()

    import scipy.integrate as si
    # `comun` PRIMERO: es quien inserta la raiz del repo en sys.path. Al reves
    # da ModuleNotFoundError: No module named 'core'.
    from comun import NOMBRES, SOPORTES, evaluar
    import core.replicator_sellers as rs

    lo = np.array([b[0] for b in SOPORTES])
    hi = np.array([b[1] for b in SOPORTES])
    if args.punto == "minimos":
        p = lo.copy()
    elif args.punto == "mucho-sol":
        p = (lo + hi) / 2.0; p[2] = hi[2]
    else:
        p = (lo + hi) / 2.0

    print("=" * 78)
    print("ROBUSTEZ DE LAS SALIDAS FRENTE AL AJUSTE DEL INTEGRADOR")
    print("=" * 78)
    print(f"  cobertura {args.cobertura}   horizonte {args.horizonte}   "
          f"punto '{args.punto}'")
    print("  " + "  ".join(f"{n}={v:g}" for n, v in zip(NOMBRES, p)))
    print()
    print(f"  {'configuracion':<18} {'s':>7}  {'ganancia':>16} {'sc':>10} "
          f"{'ie':>10}  {'no-fin':>7}")

    original = si.solve_ivp
    filas = []
    for nombre, extra in CONFIGS:
        no_fin = [0]

        def envuelto(fun, t_span, y0, __extra=extra, __nf=no_fin, **kw):
            kw2 = dict(kw)
            kw2.update(__extra)
            sol = original(fun, t_span, y0, **kw2)
            if not np.all(np.isfinite(np.asarray(sol.y))):
                __nf[0] += 1
            return sol

        rs.solve_ivp = envuelto
        t0 = time.time()
        try:
            g, sc, ie, _br, motivo = evaluar(p, args.cobertura,
                                             args.horizonte)
        except Exception as exc:                       # pragma: no cover
            g = sc = ie = float("nan"); motivo = type(exc).__name__
        dt = time.time() - t0
        rs.solve_ivp = original
        filas.append((nombre, g, sc, ie))
        print(f"  {nombre:<18} {dt:>7.1f}  {g:>16.6f} {sc:>10.6f} {ie:>10.6f}"
              f"  {no_fin[0]:>7}" + (f"   [{motivo}]" if motivo else ""))

    # ── descartar configuraciones INAPLICABLES ─────────────────────────────
    # Una configuracion cuyo resultado es fisicamente imposible no es una
    # respuesta alternativa: es basura, y usarla como referencia invierte el
    # veredicto. `sc` es el autoconsumo, un COCIENTE acotado en [0, 1]; BDF y
    # Radau llegan a dar 3.7e3 y 3.2e5 porque el lado derecho no es suave
    # —lleva proyecciones al simplex y recortes— y el Newton de los metodos
    # implicitos diverge sobre el. No son contraejemplos del ajuste de
    # produccion; son metodos que no aplican a este sistema.
    def aplicable(g, sc, ie):
        return (np.isfinite(g) and np.isfinite(sc) and np.isfinite(ie)
                and -0.01 <= sc <= 1.01 and abs(ie) <= 10.0 and g >= 0.0)

    base = filas[0]
    if not aplicable(*base[1:]):
        print("\n  SIN VEREDICTO: la propia configuracion de PRODUCCION "
              "devolvio valores fuera de rango fisico.")
        return 2

    print()
    print(f"  {'configuracion':<18} {'d_ganancia rel':>16} {'d_sc rel':>12} "
          f"{'d_ie rel':>12}  estado")
    peor_vol = peor_ie = 0.0
    n_aplicables = 0
    for nombre, g, sc, ie in filas[1:]:
        if not aplicable(g, sc, ie):
            print(f"  {nombre:<18} {'—':>16} {'—':>12} {'—':>12}  "
                  f"INAPLICABLE (sc={sc:.4g} fuera de [0,1])")
            continue
        n_aplicables += 1
        ds = [abs(a - r) / max(abs(r), 1e-12)
              for a, r in ((g, base[1]), (sc, base[2]), (ie, base[3]))]
        # El VOLUMEN (ganancia, autoconsumo) y el REPARTO (equidad) se juzgan
        # aparte: la tesis ya documenta que el ciclo de periodo 2 deja el
        # reparto indeterminado mientras el volumen es robusto.
        peor_vol = max(peor_vol, ds[0], ds[1])
        peor_ie = max(peor_ie, ds[2])
        print(f"  {nombre:<18} {ds[0]:>16.3e} {ds[1]:>12.3e} {ds[2]:>12.3e}  ok")

    print()
    print("=" * 78)
    if n_aplicables == 0:
        print("  SIN VEREDICTO: ninguna configuracion alternativa resulto")
        print("  aplicable, de modo que no hay con que contrastar produccion.")
        return 2
    print(f"  configuraciones aplicables      : {n_aplicables} de {len(filas)-1}")
    print(f"  peor discrepancia en VOLUMEN    : {peor_vol:.3e}  (ganancia, sc)")
    print(f"  peor discrepancia en REPARTO    : {peor_ie:.3e}  (ie)")
    print()
    if peor_vol >= 1e-3:
        print("  NO ROBUSTO. El VOLUMEN depende del ajuste del integrador por")
        print("  encima del 0,1 %. Resolverlo ANTES de lanzar las 896")
        print("  evaluaciones, y revisar las corridas canonicas.")
        return 1
    if peor_vol < 1e-6:
        print("  ROBUSTO. El volumen no depende del ajuste del integrador.")
    else:
        print(f"  ROBUSTO CON MATIZ. El volumen se mueve {100*peor_vol:.4f} %,")
        print("  del orden del ruido numerico esperable. Declararlo, no frena.")
    if peor_ie >= 1e-3:
        print(f"  El REPARTO (ie) se mueve {100*peor_ie:.3f} %, mas que el")
        print("  volumen. Es coherente con el ciclo de periodo 2 que la tesis")
        print("  ya declara: lo indeterminado es el reparto, no el volumen.")
        print("  No es un hallazgo nuevo ni frena la corrida; se reporta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
