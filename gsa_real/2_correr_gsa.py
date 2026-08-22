"""PASO 2 — El analisis global de sensibilidad sobre los DATOS REALES.

Escribe cada evaluacion en cuanto termina: el CSV es a la vez resultado y punto
de control. Junto a el deja un `.meta.json` con la huella del diseno, de modo
que reanudar con otra semilla, otro n_base u otro horizonte se detecta y se
rechaza en vez de mezclar dos matrices distintas bajo los mismos indices.

Uso en el servidor
------------------
    bash gsa_real/run_servidor.sh correr   M1 full 128 1800
    bash gsa_real/run_servidor.sh reanudar M1 full 128 1800
"""
from __future__ import annotations

import argparse
import csv
import json
import multiprocessing
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
# `BrokenProcessPool` NO se exporta desde `concurrent.futures`: vive en el
# submodulo `.process`. Importarlo del paquete da ImportError, y `py_compile`
# no lo detecta porque solo analiza sintaxis.
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import (FACTOR_SALTELLI, NOMBRES, PROBLEMA, RAIZ,  # noqa: E402
                   SALIDAS, SEGUNDO_ORDEN, asegurar_salida, cargar_datos,
                   evaluar, huella_datos, huella_diseno)

# CAL-43: `brecha_c1` es la cuarta salida. Se deriva de SALIDAS para que no
# vuelva a haber dos listas que puedan discrepar en silencio.
COLS = ["idx"] + NOMBRES + list(SALIDAS) + ["seg", "motivo"]


def _sonda(params, cobertura, horizonte):
    """Evaluacion FALSA para el modo --verificar.

    Hace todo lo que hace una evaluacion real MENOS resolver el EMS: carga los
    datos desde el proceso hijo —que es donde se rompe el cache o un
    desempaquetado desajustado— y devuelve numeros deterministas.

    Existe porque el modelo ya lo valida el paso 1 con cinco sondas reales. Lo
    que el paso 1 NO toca es esta maquinaria: el desempaquetado de main(), el
    .meta.json, el pool anidado con su timeout, la escritura del punto de
    control y los codigos de salida. Ahi vivian los dos bloqueantes que
    costaron sendas rondas de auditoria, y ninguno necesitaba correr el EMS
    para manifestarse.
    """
    D, G, pb, nom, mat, eff, extras = cargar_datos(cobertura, horizonte)
    if mat.shape != D.shape:
        raise ValueError(f"matriz de liquidacion {mat.shape} != datos {D.shape}")
    n_meses = len(extras["meses"])
    if n_meses != D.shape[1]:
        raise ValueError(f"calendario {n_meses} != horizonte {D.shape[1]}")
    forma_cvm = extras["cvm_mat"].shape
    if forma_cvm != D.shape:
        raise ValueError(f"Cvm {forma_cvm} != datos {D.shape}")
    pgb, pgs, f_pv, f_d, b = (float(v) for v in params)
    # Las CUATRO salidas deben DEPENDER DE LOS CINCO PARAMETROS y ser distintas
    # entre si. Una salida constante tiene varianza cero y los indices de Sobol
    # no estan definidos, de modo que el analisis no llegaria a ejercitarse —
    # que es justo lo que este modo existe para probar.
    base = float(D.sum()) * f_d + float(G.sum()) * f_pv
    return (base * pgs / 1000.0 - b,
            float(G.sum() / D.sum()) * f_pv / (f_pv + f_d),
            (pgs - pgb) / (pgs + pgb) + b / 1e4,
            base * (pgs - pgb) / 5e4 + b,          # CAL-43: brecha_c1 falsa
            "")


def _tarea(args):
    idx, params, cobertura, horizonte, timeout = args[:5]
    fn = _sonda if len(args) > 5 and args[5] else evaluar
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn, params, cobertura, horizonte)
        try:
            g, sc, ie, br, motivo = fut.result(timeout=timeout)
        except Exception as exc:
            for p in (ex._processes or {}).values():
                try:
                    p.kill()
                except Exception:
                    pass
            g = sc = ie = br = float("nan")
            motivo = "timeout" if "Timeout" in type(exc).__name__ else type(exc).__name__
    return idx, params, g, sc, ie, br, time.time() - t0, motivo


def _hechas(ruta: Path) -> set:
    """Indices YA RESUELTOS. Excluye deliberadamente las filas fallidas para
    que --reanudar las reintente: el modulo anterior las daba por hechas y el
    consejo de «subir el timeout y reanudar» no podia funcionar."""
    if not ruta.exists():
        return set()
    ok = set()
    with open(ruta, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            # descarta filas truncadas por un corte a mitad de escritura
            if len(r) < len(COLS) or any(v is None for v in r.values()):
                continue
            try:
                g = float(r["ganancia"])
            except (TypeError, ValueError):
                continue
            if np.isfinite(g):
                ok.add(int(r["idx"]))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cobertura", choices=["M1", "M3"], default="M1")
    ap.add_argument("--horizonte", default="full")
    ap.add_argument("--n-base", type=int, default=128,
                    help=f"potencia de 2; M = n_base*{FACTOR_SALTELLI}")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument("--reanudar", action="store_true")
    ap.add_argument("--forzar", action="store_true",
                    help="permite SOBRESCRIBIR un fichero existente")
    ap.add_argument("--verificar", action="store_true",
                    help="recorre TODO el camino sin resolver el EMS: valida "
                         "la orquestacion en segundos en vez de en horas")
    args = ap.parse_args()

    if args.n_base & (args.n_base - 1):
        print(f"  AVISO: n_base={args.n_base} no es potencia de 2; SALib pierde "
              f"las propiedades de baja discrepancia.")

    workers = args.workers or max(1, (multiprocessing.cpu_count() or 4) - 2)
    from SALib.sample import sobol as sobol_sample
    X = sobol_sample.sample(PROBLEMA, args.n_base,
                            calc_second_order=SEGUNDO_ORDEN, seed=args.semilla)
    M = X.shape[0]
    esperado = args.n_base * FACTOR_SALTELLI
    assert M == esperado, f"M={M} != n_base*{FACTOR_SALTELLI}={esperado}"

    sal = asegurar_salida()
    tag = f"{args.cobertura}_{args.horizonte.replace(':','-')}_n{args.n_base}_s{args.semilla}"
    if args.verificar:
        # Sufijo obligatorio: los numeros del modo verificacion son FALSOS, y
        # un fichero suyo bajo el nombre de una corrida real seria veneno. Con
        # esto es imposible que colisionen aunque se invoque con la semilla
        # canonica.
        tag += "_VERIF"
    destino = sal / f"muestras_{tag}.csv"
    meta_p = sal / f"muestras_{tag}.meta.json"
    huella = huella_diseno(args.cobertura, args.horizonte, args.n_base,
                           args.semilla, SEGUNDO_ORDEN)

    print("=" * 70)
    print("GSA SOBRE DATOS REALES")
    print("=" * 70)
    print(f"  cobertura {args.cobertura}   horizonte {args.horizonte}")
    print(f"  parametros {len(NOMBRES)}: {', '.join(NOMBRES)}")
    print(f"  n_base {args.n_base}  ->  M = {M}   (2do orden: {SEGUNDO_ORDEN})")
    print(f"  semilla {args.semilla}   huella {huella}")
    print(f"  timeout {args.timeout} s   procesos {workers}")
    print(f"  salida  {destino.name}")

    # ── guardas contra mezclar o destruir corridas ─────────────────────────
    if meta_p.exists():
        prev = json.loads(meta_p.read_text(encoding="utf-8"))
        if prev.get("huella") != huella:
            print("\n  ABORTA: ya existe una corrida con OTRO diseno bajo este "
                  "nombre.")
            print(f"    en disco: {prev.get('huella')}   ahora: {huella}")
            print("    Renombra el fichero o cambia los parametros.")
            return 2
    if destino.exists() and destino.stat().st_size > 0 \
            and not args.reanudar and not args.forzar:
        print("\n  ABORTA: el fichero de salida ya tiene datos.")
        print("    Usa --reanudar para continuarlo, o --forzar para borrarlo.")
        return 2

    # precarga: deja el .npz listo para que los workers no relean el dataset
    t0 = time.time()
    D, G, pb, _nom, _pi_gs_mat, pi_gs_eff, _extras = cargar_datos(
        args.cobertura, args.horizonte, verbose=False)
    print(f"  datos   N={D.shape[0]} T={D.shape[1]}h "
          f"cobertura={G.sum()/D.sum():.4f} bolsa={pb.mean():.1f} "
          f"({time.time()-t0:.1f} s)")
    print(f"  pi_gs   nominal {pi_gs_eff:.2f} COP/kWh "
          f"(percentil {100*(pi_gs_eff-PROBLEMA['bounds'][1][0])/(PROBLEMA['bounds'][1][1]-PROBLEMA['bounds'][1][0]):.1f} "
          f"del soporte de PGS)")

    mte_root = os.environ.get("MTE_ROOT", str(RAIZ / "MedicionesMTE_v3"))
    h_datos = huella_datos(mte_root, args.cobertura, args.horizonte)
    print(f"  fuente  {mte_root}  huella {h_datos}")
    if meta_p.exists():
        prev = json.loads(meta_p.read_text(encoding="utf-8"))
        anterior = prev.get("huella_datos")
        if anterior and anterior != h_datos:
            # Mismo diseno pero OTROS datos: reanudar aqui mezclaria dos
            # poblaciones bajo una sola matriz de Sobol.
            print("\n  ABORTA: el diseno coincide pero los DATOS cambiaron.")
            print(f"    en disco: {anterior}   ahora: {h_datos}")
            print("    Revisa MTE_ROOT, o renombra la corrida anterior.")
            return 2

    meta_p.write_text(json.dumps({
        "huella": huella, "huella_datos": h_datos, "mte_root": mte_root,
        # El tag EFECTIVO y la naturaleza del fichero van declarados, no
        # reconstruidos: en modo --verificar el nombre lleva sufijo y la
        # reconstruccion no lo veia, de modo que el analisis lo rechazaba como
        # «alguien renombro la corrida» — cierto pero enganoso.
        "tag": tag, "verificar": bool(args.verificar),
        "cobertura": args.cobertura,
        "horizonte": args.horizonte, "n_base": args.n_base,
        "semilla": args.semilla, "segundo_orden": SEGUNDO_ORDEN,
        "M": M, "parametros": NOMBRES, "soportes": PROBLEMA["bounds"],
        "N": int(D.shape[0]), "T": int(D.shape[1]),
    }, indent=2), encoding="utf-8")

    hechas = _hechas(destino) if args.reanudar else set()
    if hechas:
        print(f"  [reanudar] {len(hechas)} resueltas; se reintentan las fallidas")
    pend = [(i, X[i], args.cobertura, args.horizonte, args.timeout, args.verificar)
            for i in range(M) if i not in hechas]
    if not pend:
        print("\n  nada pendiente.")
        return 0

    # al reanudar se reescribe entero: conserva lo bueno y purga los fallos.
    # El filtro debe ser el MISMO que el de `_hechas`: sin la guarda de fila
    # truncada, una fila cortada cuyo `idx` parcial coincidiera con uno resuelto
    # se reescribia como `10,,,,,,,,,,` y dejaba el CSV inanalizable para
    # siempre —al relanzar, `pend` sale vacio y se retorna antes de reescribir.
    buenas = []
    vistos = set()
    if hechas:
        with open(destino, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if len(r) < len(COLS) or any(v is None for v in r.values()):
                    continue
                if not r.get("idx"):
                    continue
                i = int(r["idx"])
                if i in hechas and i not in vistos:
                    vistos.add(i)
                    buenas.append(r)

    # Respaldo antes de truncar. `open(...,"w")` destruye el fichero en el acto:
    # morir entre esa linea y el final de la reescritura borraba la noche
    # entera, no la muestra en curso.
    if destino.exists() and destino.stat().st_size > 0:
        import shutil
        respaldo = destino.with_suffix(".csv.bak")
        shutil.copy2(destino, respaldo)
        print(f"  respaldo en {respaldo.name} ({respaldo.stat().st_size} bytes)")

    t_ini = time.time()
    n_ok = n_mal = 0
    motivos: dict = {}
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        for r in buenas:
            w.writerow([r[c] for c in COLS])
        f.flush()
        os.fsync(f.fileno())   # el respaldo solo sirve si esto llega a disco

        print(f"\n  arrancando {len(pend)} evaluaciones...\n", flush=True)
        roto = interrumpido = False
        ex = ProcessPoolExecutor(max_workers=workers)
        try:
            futs = [ex.submit(_tarea, t) for t in pend]
            hecho = 0
            try:
                for fut in as_completed(futs, timeout=args.timeout * len(pend) + 3600):
                    try:
                        idx, params, g, sc, ie, br, seg, motivo = fut.result()
                    except BrokenProcessPool as exc:
                        # ProcessPoolExecutor NO reemplaza workers: la muerte de
                        # uno solo (OOM, segfault) rompe el pool entero y TODOS
                        # los futures pendientes fallan en cascada. Seguir aqui
                        # gastaria la noche imprimiendo cientos de errores.
                        print(f"\n  POOL ROTO ({exc}). Se corta esta tanda; lo "
                              f"escrito es valido.", flush=True)
                        roto = True
                        break
                    except Exception as exc:
                        print(f"    [future perdido] {type(exc).__name__}: {exc}",
                              flush=True)
                        continue
                    w.writerow([idx] + [f"{v:.10g}" for v in params]
                               + [f"{g:.10g}", f"{sc:.10g}", f"{ie:.10g}",
                                  f"{br:.10g}", f"{seg:.2f}", motivo])
                    f.flush()
                    os.fsync(f.fileno())
                    hecho += 1
                    if np.isnan(g):
                        n_mal += 1
                        motivos[motivo] = motivos.get(motivo, 0) + 1
                    else:
                        n_ok += 1
                    if hecho % 10 == 0 or hecho == len(pend):
                        el = time.time() - t_ini
                        eta = el / hecho * (len(pend) - hecho)
                        print(f"    {hecho:>5}/{len(pend)}  ok {n_ok}  fallo {n_mal}  "
                              f"{el/3600:.2f} h  eta {eta/3600:.2f} h", flush=True)
            except BaseException as exc:
                # BaseException tambien atrapa Ctrl-C. Con `Exception` a secas el
                # KeyboardInterrupt escapaba, y el cierre del pool se quedaba
                # ejecutando las evaluaciones pendientes tirando cada resultado.
                print(f"\n  INTERRUMPIDO: {type(exc).__name__}: {exc}")
                print("  Lo escrito hasta aqui es valido; relanza con --reanudar.")
                interrumpido = True
        finally:
            # sin cancel_futures el shutdown corre las ~900 pendientes y descarta
            # cada resultado: horas de CPU a la basura
            ex.shutdown(wait=False, cancel_futures=True)

    total = len(buenas) + n_ok
    # Fraccion de fallo sobre el DISENO COMPLETO, no sobre la tanda: es la
    # magnitud que el analisis usa para decidir si los indices son
    # concluyentes, y al reanudar la tanda es una fraccion arbitraria de M.
    n_fallidas = M - total
    frac_mal = n_fallidas / M
    print()
    print("=" * 70)
    print(f"  resueltas {total}/{M}   sin resolver {n_fallidas} ({100*frac_mal:.2f} %)")
    if motivos:
        print(f"  motivos de esta tanda: {motivos}")
    print(f"  tiempo    {(time.time()-t_ini)/3600:.2f} h")
    print()
    rc = 0
    if roto:
        print("  El pool de procesos se rompio (worker muerto: OOM o segfault).")
        print("  Puede haber procesos huerfanos: revisa `pgrep -f 2_correr_gsa.py`.")
        print("  Baja --workers y relanza con --reanudar.")
        rc = 4
    if total < M:
        # Antes esta rama tapaba siempre a la del 10 %, que era codigo muerto:
        # cualquier fallo implica total < M. Ahora el umbral se evalua aparte.
        print(f"  Faltan {n_fallidas}. Relanza con --reanudar "
              f"{'y sube --timeout' if motivos.get('timeout') else ''}.")
        if frac_mal > 0.10:
            print()
            print("  AVISO: mas del 10 % del diseno sin resolver. Es el umbral")
            print("  bajo el cual los indices se declaran NO CONCLUYENTES.")
        rc = rc or (6 if interrumpido else 5)
    elif args.verificar:
        print("  VERIFICACION OK: el camino completo funciona. Los numeros de")
        print("  este fichero son FALSOS (no se resolvio el EMS); borralo.")
    else:
        print(f"  Siguiente: bash gsa_real/run_servidor.sh analizar "
              f"{args.cobertura} {args.horizonte} {args.n_base}")
    # `shutdown(cancel_futures=True)` NO vacia la cola ya entregada a los
    # workers, y el `atexit` de concurrent.futures hace join del hilo gestor:
    # el interprete se quedaria hasta una hora mas quemando nucleos en muestras
    # cuyo resultado ya no se escribe. Cada fila esta fsync'd, asi que salir en
    # seco no pierde nada.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
