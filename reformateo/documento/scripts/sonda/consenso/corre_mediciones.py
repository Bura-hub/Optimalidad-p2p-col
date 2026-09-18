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
                    cuatro arranques de M-C son una familia en la tabla, que
                    no rotula M-C (su juicio propio separa los dos
                    arranques de precios, H-90);
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

UN TRABAJADOR MUERTO NO TUMBA LA MEDICION (tarea 4d, noche del 2026-09-18).
Esa noche M-A, M-B y M-C murieron con `BrokenProcessPool`: un trabajador
«terminated abruptly», muy probablemente por falta de memoria (30 procesos de
hasta ~1 GB con la plataforma MTE en la misma maquina y la swap llena), y el
`submit` siguiente lanzo la excepcion y la medicion entera salio con 1. Ahora,
cuando el pool se rompe (en el `submit` o en el `result`):
  - se imprime la memoria de la maquina (`/proc/meminfo`: MemAvailable, y la
    swap) y el RSS de cada trabajador en el ultimo muestreo, que se toma cada
    `MUESTREO_S` segundos mientras corren (despues de la muerte ya no se puede
    leer: el pool mata a los demas);
  - las corridas en vuelo que ya habian terminado se anotan con su resultado;
  - las que no, VUELVEN A LA COLA (decision del controlador sobre 4d). Al
    romperse, el pool mata a todos sus trabajadores, de modo que casi todas
    son victimas de rebote de una sola que revento la memoria, y se rehacen;
  - SOLO SON SOSPECHOSAS LAS QUE PODIAN ESTAR CORRIENDO (M1 de la revision de
    4d). El pool alimenta a sus trabajadores en FIFO, de modo que solo las
    `n_proc + 1` primeras en vuelo por orden de sometimiento pueden haber
    estado corriendo. Solo esas cuentan la muerte y vuelven UNA vez; las demas
    estaban en espera, vuelven a la cola normal, en paralelo, sin contarles
    nada. Se lleva la cuenta de muertes por corrida (su indice del plan): la
    que ya estaba entre las que podian correr en una muerte anterior y vuelve a
    estarlo se anota como FALLA, con la causa «trabajador muerto (probable
    falta de memoria)» y `trabajador_muerto`, y no se reencola mas;
  - para que la culpable se aisle y las victimas no caigan otra vez con ella,
    las reencoladas («sospechosas») corren DE UNA EN UNA: nunca hay dos en
    vuelo a la vez, mientras el resto del plan llena los demas procesos;
  - se abre un pool nuevo, otra vez con el tope de memoria, y se sigue.
Si el pool muere `MAX_MUERTES` (3) veces en la misma medicion, algo sistematico
lo mata: se para en voz alta y se sale con 1, con el JSON escrito (las que
podian estar corriendo en esa tercera muerte, como FALLA), la lista de los
indices que faltan y la orden para retomar.
Una corrida anotada como FALLA por trabajador muerto es un fallo de la
maquina, no del modelo: el veredicto la sigue contando como «falla» en el
denominador (N2 y m-b, criterio conservador), pero dice cuantas de las
fallidas son de la maquina.

EL TOPE DE MEMORIA. Antes de abrir cada pool, si MemAvailable / procesos baja
de `--memoria-por-proceso` (1,5 GB por omision, o MEMORIA_POR_PROCESO_GB en el
entorno; 0 lo quita), los procesos se reducen a los que caben, y se dice en el
registro: mejor ir lento que matar trabajadores o a la plataforma. Donde no hay
`/proc/meminfo` (Windows) no hay tope, y tambien se dice.
"""
import argparse
import importlib
import json
import multiprocessing as mp
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

TOPE_CORRIDA = 3600.0      # (s) por corrida, si la especificacion no dice otra
# N3 de la re-revision de 4c: el codigo de salida de una medicion a la que el
# tope total le dejo corridas sin hacer. No es un fallo del codigo, pero
# tampoco es una medicion completa. El mismo que `veredicto.CODIGO_INCOMPLETA`.
CODIGO_INCOMPLETA = 4

# Tarea 4d: el pool que muere MAX_MUERTES veces en una medicion la para (con 1).
MAX_MUERTES = 3
CAUSA_MUERTE = "trabajador muerto (probable falta de memoria)"
# La memoria que se reserva por proceso al abrir el pool (GB), y cada cuanto se
# muestrea el RSS de los trabajadores mientras corren (s).
MEMORIA_POR_PROCESO_GB = 1.5
MUESTREO_S = 30.0
MEMINFO = "/proc/meminfo"
PROC = "/proc"


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


def tramos(indices) -> str:
    """Los indices del plan en tramos: [3, 4, 5, 9, 12, 13] -> «3-5, 9, 12-13».
    Para decir que falta sin una lista de cien numeros."""
    xs = sorted(set(int(i) for i in indices))
    if not xs:
        return "ninguno"
    partes, ini, ant = [], xs[0], xs[0]
    for x in xs[1:] + [None]:
        if x is not None and x == ant + 1:
            ant = x
            continue
        partes.append(f"{ini}" if ini == ant else f"{ini}-{ant}")
        if x is not None:
            ini = ant = x
    return ", ".join(partes)


# ── la memoria de la maquina y de los trabajadores (tarea 4d) ─────────────
def memoria(ruta=MEMINFO):
    """Los campos de `/proc/meminfo` que interesan, en kB: MemTotal,
    MemAvailable, SwapTotal y SwapFree. None si no se puede leer (Windows)."""
    try:
        texto = Path(ruta).read_text(encoding="ascii", errors="replace")
    except OSError:
        return None
    fuera = {}
    for linea in texto.splitlines():
        clave, _, resto = linea.partition(":")
        if clave in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
            try:
                fuera[clave] = int(resto.split()[0])
            except (IndexError, ValueError):
                continue
    return fuera or None


def rss_kb(pid, proc=PROC):
    """El RSS de un proceso (kB), de `/proc/<pid>/status`; None si no se
    puede leer (el proceso ya no esta, o no es Linux)."""
    try:
        texto = (Path(proc) / str(pid) / "status").read_text(
            encoding="ascii", errors="replace")
    except OSError:
        return None
    for linea in texto.splitlines():
        if linea.startswith("VmRSS:"):
            try:
                return int(linea.split()[1])
            except (IndexError, ValueError):
                return None
    return None


def rss_trabajadores(ex, proc=PROC) -> dict:
    """{pid: RSS (kB)} de los trabajadores vivos del pool. Lee el atributo
    `_processes` del `ProcessPoolExecutor` (privado, pero estable desde 3.3);
    un pool sin el devuelve un diccionario vacio."""
    procesos = dict(getattr(ex, "_processes", None) or {})
    fuera = {}
    for pid in procesos:
        r = rss_kb(pid, proc)
        if r is not None:
            fuera[pid] = r
    return fuera


def _gb(kb) -> str:
    return f"{kb / 2**20:.1f}"


def texto_memoria(ruta=MEMINFO) -> str:
    """Una linea con la memoria de la maquina, para el registro."""
    m = memoria(ruta)
    if not m:
        return f"memoria: no se puede leer {ruta}"
    partes = []
    if "MemAvailable" in m:
        partes.append(f"MemAvailable {_gb(m['MemAvailable'])} GB"
                      + (f" de {_gb(m['MemTotal'])}" if "MemTotal" in m else ""))
    if "SwapTotal" in m:
        partes.append(f"swap libre {_gb(m.get('SwapFree', 0))} GB de "
                      f"{_gb(m['SwapTotal'])}")
    return "memoria: " + "; ".join(partes)


def procesos_por_memoria(pedidos, por_proceso_gb=MEMORIA_POR_PROCESO_GB,
                         ruta=MEMINFO) -> tuple:
    """(procesos, texto): los pedidos, o menos si no caben en la memoria.

    Si MemAvailable / pedidos baja de `por_proceso_gb`, se reducen a los que
    caben (uno como minimo, con aviso si ni ese cabe). Sin /proc/meminfo, o con
    `por_proceso_gb` <= 0, se quedan los pedidos. El texto va al registro."""
    pedidos = max(1, int(pedidos))
    if por_proceso_gb <= 0:
        return pedidos, (f"  memoria: sin tope por proceso "
                         f"(--memoria-por-proceso 0); {pedidos} procesos")
    m = memoria(ruta)
    if not m or "MemAvailable" not in m:
        return pedidos, (f"  memoria: no se puede leer MemAvailable de {ruta} "
                         f"(no es Linux); sin tope de memoria, {pedidos} "
                         f"procesos")
    disponible_gb = m["MemAvailable"] / 2**20
    caben = int(disponible_gb // por_proceso_gb)
    if caben >= pedidos:
        return pedidos, (f"  memoria: MemAvailable {disponible_gb:.1f} GB; "
                         f"caben {caben} procesos de {por_proceso_gb:g} GB, se "
                         f"usan los {pedidos} pedidos")
    n = max(1, caben)
    texto = (f"  === MEMORIA: MemAvailable {disponible_gb:.1f} GB / {pedidos} "
             f"procesos = {disponible_gb / pedidos:.2f} GB por proceso, por "
             f"debajo de {por_proceso_gb:g} GB: SE REDUCEN A {n} PROCESOS "
             f"(mejor lento que matar trabajadores o a la plataforma) ===")
    if caben < 1:
        texto += ("\n  === Ni uno cabe con ese margen: se corre con 1, y puede "
                  "morir. Mira que mas ocupa la memoria. ===")
    return n, texto


def informe_muerte(muertes, rss, t_rss, ruta=MEMINFO,
                   max_muertes=MAX_MUERTES) -> str:
    """Lo que se imprime cuando el pool muere: la memoria de ahora y el RSS de
    los trabajadores en el ultimo muestreo."""
    lineas = [f"  === EL POOL MURIO ({muertes} de {max_muertes} permitidas): un "
              f"trabajador termino de golpe, {CAUSA_MUERTE} ===",
              f"  {texto_memoria(ruta)}"]
    if rss:
        hace = time.perf_counter() - t_rss if t_rss is not None else float("nan")
        suma = sum(rss.values())
        detalle = ", ".join(f"{pid}: {kb / 1024:.0f} MB"
                            for pid, kb in sorted(rss.items()))
        lineas.append(f"  RSS de los trabajadores en el ultimo muestreo (hace "
                      f"{hace:.0f} s): {detalle}; suma {suma / 1024:.0f} MB, el "
                      f"mayor {max(rss.values()) / 1024:.0f} MB")
    else:
        lineas.append("  RSS de los trabajadores: no se pudo leer (sin /proc, o "
                      "murio antes del primer muestreo)")
    return "\n".join(lineas)


def corre_plan(pendientes, total, procesos, salida, tope_total=0.0,
               trabajo_fn=None, fabrica=None,
               por_proceso_gb=MEMORIA_POR_PROCESO_GB, max_muertes=MAX_MUERTES,
               meminfo=MEMINFO, proc=PROC, muestreo_s=MUESTREO_S) -> dict:
    """Corre las `pendientes` [(indice, spec)] en un pool y escribe `salida`
    despues de cada corrida. Sobrevive a un trabajador muerto (ver el
    docstring del modulo).

    `trabajo_fn` es la funcion de cada corrida (`trabajo`) y `fabrica(n)` abre
    el pool (un `ProcessPoolExecutor` de n procesos); las dos se cambian en las
    pruebas. Devuelve dict(resultados, hechos, muertes, perdidas,
    reencoladas, devueltas, sospechosas, detenida, seg): `perdidas`, los
    indices anotados como FALLA por un trabajador muerto; `reencoladas`, las
    sospechosas que volvieron a la cola (una vez cada una); `devueltas`, las
    que estaban en espera en el pool y volvieron sin contarles la muerte;
    `sospechosas`, por cada muerte, los indices que podian estar corriendo;
    `detenida`, si se paro por morir el pool `max_muertes` veces.
    """
    trabajo_fn = trabajo_fn or trabajo
    fabrica = fabrica or (lambda n: ProcessPoolExecutor(max_workers=n))
    resultados, hechos, perdidas, reencoladas = [], set(), [], []
    devueltas, sospechosas_por_muerte = [], []
    t0 = time.perf_counter()
    cola = list(pendientes)
    muertes = 0
    detenida = False
    # Cuantas muertes del pool vio cada corrida (indice del plan) en vuelo.
    muertes_de = {}

    def sospechosa(n):
        return muertes_de.get(n, 0) > 0

    def siguiente(en_vuelo):
        """La posicion en la cola de la proxima corrida que se puede someter:
        la primera, salvo que sea sospechosa y ya haya otra en vuelo."""
        hay = any(sospechosa(n) for n, _sp in en_vuelo.values())
        for i, (n, _sp) in enumerate(cola):
            if not (hay and sospechosa(n)):
                return i
        return None

    def registra(res, n):
        # N3: cada registro dice de que plan salio y cual de sus corridas es,
        # para que `veredicto.py` sepa si falta alguna.
        res["plan_total"] = total
        res["plan_indice"] = n
        resultados.append(res)
        hechos.add(n)
        # Escritura atomica (menor 3 de la re-revision de 4d): una senal del
        # esperador o del operador a mitad de la escritura dejaria un JSON
        # truncado e ilegible; con el temporal y os.replace queda el anterior.
        temporal = salida.with_name(salida.name + ".tmp")
        temporal.write_text(json.dumps(limpia(resultados)), encoding="utf-8")
        os.replace(temporal, salida)

    def fuera_de_tiempo():
        return bool(tope_total and time.perf_counter() - t0 > tope_total)

    while True:
        n_proc, texto = procesos_por_memoria(procesos, por_proceso_gb, meminfo)
        print(texto, flush=True)
        ex = fabrica(n_proc)
        # Ventana acotada de sometimiento (CAL-43e): nunca se someten todas
        # las corridas de golpe.
        ventana = max(2 * n_proc, n_proc + 1)
        en_vuelo = {}
        rss, t_rss = {}, None
        roto = False
        try:
            while cola or en_vuelo:
                while cola and len(en_vuelo) < ventana:
                    i = siguiente(en_vuelo)
                    if i is None:
                        break                # solo quedan sospechosas y ya
                    n, sp = cola[i]          # hay una en vuelo
                    try:
                        fu = ex.submit(trabajo_fn, sp)
                    except BrokenProcessPool:
                        roto = True          # esta no llego a someterse: sigue en
                        break                # la cola y corre en el pool nuevo
                    cola.pop(i)
                    en_vuelo[fu] = (n, sp)
                if roto or not en_vuelo:
                    break
                # Con plazo: entre dos corridas que terminan se muestrea el RSS de
                # los trabajadores, que despues de una muerte ya no se puede leer.
                listos, _ = wait(list(en_vuelo), timeout=muestreo_s,
                                 return_when=FIRST_COMPLETED)
                muestra = rss_trabajadores(ex, proc)
                if muestra:
                    rss, t_rss = muestra, time.perf_counter()
                for fu in sorted(listos, key=lambda f: en_vuelo[f][0]):
                    n, sp = en_vuelo[fu]
                    try:
                        res = fu.result()
                    except BrokenProcessPool:
                        roto = True          # se anota abajo, con las demas
                        continue
                    except Exception as exc:                      # noqa: BLE001
                        print(f"=== FALLA [{n}/{total}] {sp['caso']} {sp['fecha']} "
                              f"{sp['etq']}: {type(exc).__name__}: {exc}",
                              flush=True)
                        res = dict(spec=sp, msg=f"FALLA {type(exc).__name__}: {exc}",
                                   filas=[], veredicto={}, cerrada={}, seg=0.0)
                    else:
                        imprime(n, total, res)
                    del en_vuelo[fu]
                    registra(res, n)
                if roto:
                    break
                if cola and fuera_de_tiempo():
                    print(f"  TOPE TOTAL de {tope_total:.0f} s: no se someten "
                          f"mas corridas; quedan {len(cola)}. Las que ya estan "
                          f"corriendo terminan con su propio tope.", flush=True)
                    cola = []
        except BaseException:
            # Una interrupcion (o un error del propio guion) no deja el
            # pool abierto: lo que hacia el `with` de antes.
            ex.shutdown(wait=False, cancel_futures=True)
            raise
        if not roto:
            ex.shutdown(wait=True)
            break

        # ── el pool murio ─────────────────────────────────────────────────
        muertes += 1
        print(informe_muerte(muertes, rss, t_rss, meminfo, max_muertes),
              flush=True)
        # Primero se cierra: asi el pool termina de marcar como fallidas las
        # que tenia pendientes y ninguna queda a medias.
        ex.shutdown(wait=True, cancel_futures=True)
        para = muertes >= max_muertes
        vuelven = []
        # Las que habian terminado antes de la muerte se anotan con su
        # resultado. `en_vuelo` guarda el orden de sometimiento.
        sin_terminar = []
        for fu, (n, sp) in list(en_vuelo.items()):
            if fu.done() and not fu.cancelled() and fu.exception() is None:
                res = fu.result()
                imprime(n, total, res)
                registra(res, n)
            else:
                sin_terminar.append((n, sp))
        # M1 de la revision de 4d: el pool alimenta a sus trabajadores en
        # FIFO, asi que solo las n_proc + 1 primeras sin terminar, por orden
        # de sometimiento, podian estar corriendo. Solo esas son sospechosas.
        podian = {n for n, _sp in sin_terminar[:n_proc + 1]}
        sospechosas_por_muerte.append(sorted(podian))
        for n, sp in sorted(sin_terminar, key=lambda x: x[0]):
            if n not in podian:
                # Estaba en espera en el pool: no pudo matarlo. Vuelve a la
                # cola normal, sin contarle la muerte (o queda sin hacer si la
                # medicion para aqui).
                print(f"=== {'SIN HACER' if para else 'DE VUELTA'} [{n}/{total}] "
                      f"{sp['caso']} {sp['fecha']} {sp['etq']}: estaba en "
                      f"espera en el pool, no llego a correr; "
                      f"{'queda sin hacer' if para else 'vuelve a la cola sin contarle la muerte'}",
                      flush=True)
                vuelven.append((n, sp))
                if not para:
                    devueltas.append(n)
                continue
            muertes_de[n] = muertes_de.get(n, 0) + 1
            if muertes_de[n] < 2 and not para:
                # Decision del controlador: vuelve a la cola UNA vez.
                print(f"=== REENCOLADA [{n}/{total}] {sp['caso']} {sp['fecha']} "
                      f"{sp['etq']}: podia estar corriendo cuando murio el "
                      f"pool; se rehace una vez, sin otra sospechosa en vuelo",
                      flush=True)
                vuelven.append((n, sp))
                reencoladas.append(n)
                continue
            motivo = ("en vuelo en dos muertes del pool" if muertes_de[n] >= 2
                      else f"en vuelo en la muerte {muertes}, que para la "
                           f"medicion")
            print(f"=== FALLA [{n}/{total}] {sp['caso']} {sp['fecha']} "
                  f"{sp['etq']}: {CAUSA_MUERTE} ({motivo})", flush=True)
            res = dict(spec=sp,
                       msg=f"FALLA BrokenProcessPool: {CAUSA_MUERTE} ({motivo})",
                       filas=[], veredicto={}, cerrada={}, seg=0.0,
                       trabajador_muerto=muertes,
                       muertes_en_vuelo=muertes_de[n])
            perdidas.append(n)
            registra(res, n)
        cola = sorted(cola + vuelven, key=lambda x: x[0])
        if para:
            detenida = True
            raya = "=" * 70
            print(f"\n  {raya}\n  EL POOL MURIO {muertes} VECES EN ESTA "
                  f"MEDICION: algo sistematico lo mata (casi seguro la\n  "
                  f"memoria). SE PARA AQUI, con {len(cola)} corridas sin "
                  f"hacer: indices {tramos(n for n, _sp in cola)}.\n  Baja "
                  f"PROCS o sube --memoria-por-proceso, mira que mas ocupa la "
                  f"memoria de la\n  maquina y retoma con la orden de abajo.\n"
                  f"  {raya}", flush=True)
            break
        if cola and fuera_de_tiempo():
            print(f"  TOPE TOTAL de {tope_total:.0f} s: no se abre otro pool; "
                  f"quedan {len(cola)} corridas.", flush=True)
            cola = []
        if not cola:
            break
        print(f"  se abre un pool nuevo y se sigue con las {len(cola)} corridas "
              f"que quedan", flush=True)
    return dict(resultados=resultados, hechos=hechos, muertes=muertes,
                perdidas=perdidas, reencoladas=reencoladas,
                devueltas=devueltas, sospechosas=sospechosas_por_muerte,
                detenida=detenida, seg=time.perf_counter() - t0)


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
    ap.add_argument("--memoria-por-proceso", type=float,
                    default=float(os.environ.get("MEMORIA_POR_PROCESO_GB",
                                                 MEMORIA_POR_PROCESO_GB)),
                    help="(GB) que se reservan por proceso al abrir el pool; "
                         "si MemAvailable no da, se abren menos. 0 = sin tope")
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

    plan = corre_plan(pendientes, total, args.procesos, salida,
                      tope_total=args.tope_total,
                      por_proceso_gb=args.memoria_por_proceso)
    resultados, hechos = plan["resultados"], plan["hechos"]
    print(f"  {len(hechos)} corridas en {plan['seg']:.0f} s; JSON en {salida}",
          flush=True)
    if plan["muertes"]:
        print(f"  el pool murio {plan['muertes']} veces: "
              f"{len(plan['reencoladas'])} sospechosas volvieron a la cola una "
              f"vez (indices {tramos(plan['reencoladas'])}) y "
              f"{len(plan['devueltas'])} que estaban en espera volvieron sin "
              f"contarles nada (indices {tramos(plan['devueltas'])})",
              flush=True)
    if plan["perdidas"]:
        print(f"  {len(plan['perdidas'])} corridas anotadas como FALLA porque "
              f"murio su trabajador: indices {sorted(plan['perdidas'])}. Son "
              f"un fallo de la maquina, no del modelo; el veredicto las cuenta "
              f"como falla y dice cuantas son.", flush=True)
    faltan = faltantes(total, hechos, args.desde)
    if faltan:
        print(f"  MEDICION INCOMPLETA: quedaron {len(faltan)} corridas sin "
              f"hacer de {total - args.desde} (la primera es la {faltan[0]})",
              flush=True)
        print(f"  FALTAN los indices: {tramos(faltan)}", flush=True)
        print(f"  RETOMA con:  --desde {faltan[0]} --salida "
              f"{salida.with_name(salida.stem + '_resto.json').name}",
              flush=True)
        print("  (el JSON de esta parte queda escrito; el veredicto se calcula "
              "sobre los dos: veredicto.py acepta varios)", flush=True)
    if plan["detenida"]:
        # Tarea 4d: el pool murio MAX_MUERTES veces. Sale con 1, en voz alta; el
        # JSON esta escrito y `veredicto.py` lo puede leer aparte.
        print(f"  === DETENIDA: el pool murio {plan['muertes']} veces; sale "
              f"con 1 ===", flush=True)
        return 1
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
