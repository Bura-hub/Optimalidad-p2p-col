"""Corre una medicion de la validacion del reposo y guarda su JSON.

QUE HACE. Toma un guion de medicion (`medicion_*.py`), que dice QUE horas y
con QUE variantes hay que integrar, y por cada una: prepara la hora
(`preparacion.prepara`), construye el lado derecho del arnes, integra por
tramos con tope, y en cada punto de control anota el reparto, los precios, sus
derivadas y la distancia al reposo en forma cerrada. Al final aplica el
criterio de consenso y escribe el JSON.

    python -u reformateo/documento/scripts/sonda/consenso/corre_mediciones.py \\
        --medicion medicion_regimenes \\
        --salida SALIDAS_SERVIDOR/validacion_reposo/m_a_regimenes.json \\
        --procesos 30 --tope-total 14400

PROTOCOLO DE UN GUION DE MEDICION. Define `MEDICION` (el rotulo, por ejemplo
"M-A"), `QUE_DECIDE` (una linea) y `specs(horas)`, que devuelve la lista de
especificaciones. `horas` es lo que `selecciona_horas.py` dejo escrito.

UNA ESPECIFICACION es un diccionario con:
    medicion        el rotulo de la medicion ("M-A", ...), con que
                    `veredicto.py` sabe que juicio le toca al JSON;
    caso, fecha     la hora (`arnes.hora_de`);
    etq             el rotulo de la variante, que sale en el registro;
    familia         el MODELO que se prueba. El veredicto exige que todas las
                    corridas de una hora y una familia esten dentro, y cuenta
                    cada familia aparte: las dos aceleraciones de M-A o los
                    cuatro arranques de M-C son una familia (el mismo modelo);
                    los dos costos de M-B o las dos formas del jugador virtual
                    de M-G son dos (critico 1 de la revision de 4c);
    grupo           el estrato de la muestra (el regimen lo pone el nucleo);
    tolerancia      opcional, la que la medicion declara (tol_q_rel, tol_p);
                    sin ella, la de M-A, que depende de k y del regimen;
    var             los ganchos de `arnes.construye` (mu_ent, k_lento,
                    b_vend, peso, ...). `b_vend="PISO"` es el costo del
                    vendedor por su alternativa (D64) y se resuelve aqui;
    cortes          los puntos de control, en tiempo SIN equivalencia (el
                    tiempo equivalente es t·k);
    tope            segundos de pared de esa corrida;
    y las de `preparacion.prepara` (cerrada, referencias, piso_juego, nivel,
    sigma, recorta_vendedores, recorta_compradores).

REGLAS DE LA CASA que este guion cumple: nunca canaliza su salida (la
redirige el lanzador), escribe el JSON despues de CADA corrida (una parada no
deja la noche en blanco), somete al pool en ventana acotada (CAL-43e) y tiene
tope por corrida y tope total, con el mensaje de como retomar.
"""
import argparse
import importlib
import json
import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

TOPE_CORRIDA = 3600.0      # (s) por corrida, si la especificacion no dice otra
# N3 de la re-revision de 4c: el codigo de salida de una medicion a la que el
# tope total le dejo corridas sin hacer. No es un fallo del codigo, pero
# tampoco es una medicion completa. El mismo que `veredicto.CODIGO_INCOMPLETA`.
CODIGO_INCOMPLETA = 4


def carga_horas(directorio) -> dict:
    """Lo que `selecciona_horas.py` dejo escrito, por caso.

    Devuelve {caso: {regimen: [ {hora, fecha, ...}, ... ]}}. Si no hay
    ninguno, devuelve un diccionario vacio y cada guion decide si puede seguir
    con sus horas de respaldo.
    """
    d = Path(directorio)
    fuera = {}
    if not d.is_dir():
        return fuera
    for f in sorted(d.glob("horas_*.json")):
        datos = json.loads(f.read_text(encoding="utf-8"))
        fuera[datos["caso"]] = datos["por_regimen"]
    return fuera


def banner_vacia(medicion, horas_dir) -> str:
    """El aviso de una medicion planificada que no produjo ninguna corrida.

    «Nada que correr» se leia como exito y salia con 0 (medio 1 de la revision
    de 4c). Casi siempre es que la seleccion de horas no dejo nada para esta
    medicion: falto un almacen, o el grupo que pide quedo vacio.
    """
    raya = "=" * 70
    return (f"\n  {raya}\n"
            f"  {medicion}: CERO CORRIDAS. Esta medicion estaba planificada y no\n"
            f"  produjo ninguna especificacion, de modo que NO SE MIDIO NADA.\n"
            f"  Mira los horas_<caso>.json de {horas_dir} (o el registro de\n"
            f"  selecciona_horas.py): falta el almacen de algun caso, o el grupo\n"
            f"  que esta medicion pide quedo sin horas.\n"
            f"  {raya}")


def limpia(x):
    """Todo a tipos que el JSON entiende."""
    import numpy as np
    if isinstance(x, dict):
        return {str(k): limpia(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [limpia(v) for v in x]
    if isinstance(x, np.ndarray):
        return [limpia(v) for v in x.tolist()]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, slice):
        return str(x)
    return x


def trabajo(spec):
    """Una hora con una variante: integrarla y medir su distancia al reposo."""
    import numpy as np
    import arnes as A
    import preparacion as PR

    t0 = time.perf_counter()
    pre = PR.prepara(spec)
    if pre["sin_mercado"]:
        return dict(spec=spec, msg="sin mercado", filas=[], avisos=pre["avisos"],
                    cerrada={}, veredicto={}, seg=time.perf_counter() - t0)
    e = pre["e"]
    var = dict(spec.get("var", {}))
    # D64 / D68: el costo del vendedor en la dinamica. "PISO" es el costo de su
    # alternativa (lo que deja de cobrarle a la red), que depende de la hora y
    # por eso se resuelve aqui; "LCOE" (o nada) es el b_j de los datos, que es
    # el defecto del arnes. Un vector se pasa tal cual.
    costo = var.get("b_vend")
    if isinstance(costo, str):
        if costo == "PISO":
            var["b_vend"] = e["piso_j"]
        elif costo == "LCOE":
            var.pop("b_vend")
        else:
            raise ValueError(f"b_vend={costo!r}; use 'PISO', 'LCOE' o un vector")
    elif costo is None:
        var.pop("b_vend", None)
    if pre["precios0"] is not None:
        var["precios0"] = pre["precios0"]
    rhs, X0, ix = A.construye(e, **var)
    I, J = ix["I"], ix["J"]
    k = float(var.get("k_lento", 1.0))
    out, msg = A.integra_tramos(rhs, X0, spec["cortes"],
                                tope_s=float(spec.get("tope", TOPE_CORRIDA)))
    refs = pre["referencias"]
    filas = []
    for (t, X, nf, s) in out:
        r = A.resumen(e, X)
        d = rhs(t, X)
        dq = d[ix["P"]].reshape(J, I).sum(axis=0)
        dp = d[ix["pi"]][:I]
        filas.append(dict(
            t=float(t), teq=float(t) * k, p=r["p"], q=r["q"], P=r["P"],
            sj=r["P"].sum(axis=1), pv=r["pv"], ppond=r["ppond"],
            parte=r["parte"], suma=r["suma"], nfev=int(nf), seg=float(s),
            dq_dt=float(np.max(np.abs(dq))) / k,
            dp_dt=float(np.max(np.abs(dp))) / k,
            dist={nombre: PR.distancias(r, ref) for nombre, ref in refs.items()}))
    base = pre["base"]
    # Medio 3: la tolerancia que la medicion declara, si la declara; si no, la
    # de M-A, que depende de la aceleracion y del regimen.
    tol = PR.tolerancias(base["regimen"], k,
                         declarada=spec.get("tolerancia"))
    E = float(base["E"])
    veredicto = {}
    for nombre in refs:
        veredicto[nombre] = dict(
            consenso=PR.criterio_consenso(filas, nombre, E, tol),
            teq80=PR.en_teq(filas, nombre, E, tol, 80.0),
            teq160=PR.en_teq(filas, nombre, E, tol, 160.0),
            final=(PR.dentro(filas[-1], nombre, E, tol) if filas else False))
    # La P de cada punto de control ocupa mucho y no se lee: solo la del
    # ultimo. Las distancias, que son lo que se mira, quedan todas.
    for f in filas[:-1]:
        f.pop("P", None)
    return dict(spec=spec, msg=msg, avisos=pre["avisos"],
                # Critico 2: una corrida que no cabe en su tope se corta, y
                # eso es un resultado que se publica, no una falla.
                cortada=(msg != "ok"),
                teq_alcanzado=(filas[-1]["teq"] if filas else 0.0),
                nfev=(filas[-1]["nfev"] if filas else 0),
                # Medio 5: si el recorte movio el reposo, la hora no cuenta.
                recorte_movio=bool(pre.get("recorte_movio", False)),
                regimen=base["regimen"], E=E, piso_juego=pre["piso_juego"],
                modo_piso=pre["modo_piso"], vend=e["vend"], comp=e["comp"],
                gn=e["gn"], dn=e["dn"], techo=e["techo"], piso_j=e["piso_j"],
                sel_j=pre["sel_j"], sel_i=pre["sel_i"],
                tolerancia=tol, cerrada=refs, filas=filas,
                veredicto=veredicto, seg=time.perf_counter() - t0)


def imprime(n, total, res):
    import numpy as np
    sp = res["spec"]
    print(f"=== [{n}/{total}] {sp['caso']} {sp['fecha']} | {sp['etq']} | "
          f"{res['msg']} | {res['seg']:.0f} s | regimen "
          f"{res.get('regimen', '?')} | E = {res.get('E', 0.0):.4f} kWh",
          flush=True)
    for a in res.get("avisos", []):
        print(f"    aviso: {a}", flush=True)
    for f in res["filas"]:
        linea = (f"  teq={f['teq']:<8g} p={np.round(f['p'], 2).tolist()} "
                 f"q={np.round(f['q'], 4).tolist()} "
                 f"|dq/dt|={f['dq_dt']:.1e} |dp/dt|={f['dp_dt']:.1e}")
        for nombre, d in f["dist"].items():
            linea += (f" | {nombre}: dq={d['dq']:.2e} dp={d['dp']:.2e} "
                      f"dsj={d['dsj']:.2e}")
        linea += f" nfev={f['nfev']} {f['seg']:.0f}s"
        print(linea, flush=True)
    for nombre, v in res.get("veredicto", {}).items():
        c = v["consenso"]
        print(f"    {nombre}: consenso {'SI en teq ' + format(c['teq'], 'g') if c['llega'] else 'NO'}"
              f" | teq 80 {'dentro' if v['teq80']['dentro'] else 'fuera'}"
              f" | teq 160 {'dentro' if v['teq160']['dentro'] else 'fuera'}"
              f" | tolerancia {res['tolerancia']['clase']} "
              f"({res['tolerancia']['motivo']})", flush=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--medicion", required=True,
                    help="modulo del guion de medicion, por ejemplo "
                         "medicion_regimenes")
    ap.add_argument("--salida", required=True, help="el JSON que se escribe")
    ap.add_argument("--procesos", type=int, default=8)
    ap.add_argument("--tope-total", type=float, default=0.0,
                    help="(s) de pared de toda la medicion; 0 = sin tope")
    ap.add_argument("--desde", type=int, default=0,
                    help="indice de la primera especificacion, para retomar")
    ap.add_argument("--horas", default="SALIDAS_SERVIDOR/validacion_reposo",
                    help="carpeta con los horas_<caso>.json de seleccion")
    args = ap.parse_args(argv)

    salida = Path(args.salida).resolve()
    salida.parent.mkdir(parents=True, exist_ok=True)
    horas = carga_horas(Path(args.horas).resolve())
    mod = importlib.import_module(args.medicion)
    specs = list(mod.specs(horas))
    total = len(specs)
    pendientes = list(enumerate(specs))[args.desde:]
    print(f"{getattr(mod, 'MEDICION', args.medicion)}: "
          f"{getattr(mod, 'QUE_DECIDE', '')}", flush=True)
    print(f"  {total} corridas ({len(pendientes)} por correr desde "
          f"{args.desde}), {args.procesos} procesos, salida {salida}",
          flush=True)
    if total == 0:
        # Medio 1: una medicion planificada sin corridas no es un exito.
        print(banner_vacia(getattr(mod, "MEDICION", args.medicion),
                           Path(args.horas)), flush=True)
        return 3
    if not pendientes:
        print(f"  --desde {args.desde} deja fuera las {total} corridas: no se "
              f"corrio nada", flush=True)
        return 2

    resultados = []
    t0 = time.perf_counter()
    hechos = set()
    with ProcessPoolExecutor(max_workers=args.procesos) as ex:
        # Ventana acotada de sometimiento (CAL-43e): nunca se someten todas
        # las corridas de golpe.
        ventana = max(2 * args.procesos, args.procesos + 1)
        en_vuelo = {}
        cola = list(pendientes)
        while cola or en_vuelo:
            while cola and len(en_vuelo) < ventana:
                n, sp = cola.pop(0)
                en_vuelo[ex.submit(trabajo, sp)] = (n, sp)
            if not en_vuelo:
                break
            listos, _ = wait(list(en_vuelo), return_when=FIRST_COMPLETED)
            for fu in listos:
                n, sp = en_vuelo.pop(fu)
                try:
                    res = fu.result()
                except Exception as exc:                      # noqa: BLE001
                    print(f"=== FALLA [{n}/{total}] {sp['caso']} {sp['fecha']} "
                          f"{sp['etq']}: {type(exc).__name__}: {exc}",
                          flush=True)
                    res = dict(spec=sp, msg=f"FALLA {type(exc).__name__}: {exc}",
                               filas=[], veredicto={}, cerrada={}, seg=0.0)
                else:
                    imprime(n, total, res)
                # N3: cada registro dice de que plan salio y cual de sus
                # corridas es, para que `veredicto.py` sepa si falta alguna.
                res["plan_total"] = total
                res["plan_indice"] = n
                resultados.append(res)
                hechos.add(n)
                salida.write_text(json.dumps(limpia(resultados)),
                                  encoding="utf-8")
            if (args.tope_total and cola
                    and time.perf_counter() - t0 > args.tope_total):
                print(f"  TOPE TOTAL de {args.tope_total:.0f} s: no se someten "
                      f"mas corridas; quedan {len(cola)}. Las que ya estan "
                      f"corriendo terminan con su propio tope.", flush=True)
                cola = []
    seg = time.perf_counter() - t0
    print(f"  {len(hechos)} corridas en {seg:.0f} s; JSON en {salida}",
          flush=True)
    faltan = faltantes(total, hechos, args.desde)
    if faltan:
        print(f"  MEDICION INCOMPLETA: quedaron {len(faltan)} corridas sin "
              f"hacer de {total - args.desde} (la primera es la {faltan[0]})",
              flush=True)
        print(f"  RETOMA con:  --desde {faltan[0]} --salida "
              f"{salida.with_name(salida.stem + '_resto.json').name}",
              flush=True)
        print("  (el JSON de esta parte queda escrito; el veredicto se calcula "
              "sobre los dos: veredicto.py acepta varios)", flush=True)
    # Menor 3 de la revision de 4c: sin `except`. Si el resumen del veredicto
    # falla, la medicion sale con error y se ve; el JSON ya esta escrito, y
    # `veredicto.py` lo puede releer cuando se arregle lo que fallo.
    import veredicto
    print(veredicto.resume(resultados), flush=True)
    # N3: una medicion cortada por el tope no sale con 0, que el lanzador leia
    # como completa. Sale con CODIGO_INCOMPLETA y el lanzador la anota como
    # «incompleta».
    return CODIGO_INCOMPLETA if faltan else 0


def faltantes(total: int, hechos, desde: int = 0) -> list:
    """Los indices del plan, desde `desde`, que no se llegaron a correr."""
    return [n for n in range(desde, total) if n not in hechos]


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
