"""Corre la muestra de Saltelli de UN caso sobre el modelo por reposo (D73).

Actividad 4.1.

Cada evaluacion se escribe en cuanto termina, con `fsync`: el CSV es a la vez
resultado y punto de control. Junto a el va un `.meta.json` con la huella del
diseno y la del dato, y el punto base evaluado en el proceso padre, de modo
que reanudar con otro diseno u otro dato se rechaza en vez de mezclar dos
poblaciones bajo los mismos indices.

Los indices se SOMETEN EN ORDEN, con una ventana acotada (CAL-43e: nunca las
M de una vez): un fichero interrumpido tiene completo un prefijo de bloques
de Saltelli, que `analizar.py` analiza hasta su ultimo bloque completo.

Uso (el lanzador lo hace solo: `bash modelo_base/run_servidor.sh gsa_directo`):

    python -u gsa_directo/correr.py --caso E0 --n-base 2048 --procesos 16 --reanudar
    python -u gsa_directo/correr.py --caso E0 --humo 32 --procesos 16 \
        --proyecta "E0:2048 E2:2048" --tope-noche-h 9
    python -u gsa_directo/correr.py --caso E0 --dia 2025-08-01 --humo 4   # local

Codigos de salida: 0 todas las filas escritas (buenas o con su motivo de
fallo); 2 guarda de diseno o de dato (tambien: CV2, que no corre el Sobol, o
un caso que ya tiene una corrida con otro n); 3 el punto base no evalua; 4
el pool se rompio; 5 faltan filas; 6 interrumpido o colgado; 7 (humo) los
casos de diseno no caben en la noche ni con el n minimo; 8 PARADA TEMPRANA
por bloques fallidos (ronda de arreglos de la tarea G, I-2; ronda 2, R-1).

Parada temprana. `analizar.py` detiene el caso si mas del 1 % de los
bloques de Saltelli tienen una evaluacion fallida. Para no descubrirlo tras
horas de servidor, la corrida cuenta los bloques fallidos mientras escribe
y para (codigo 8, con los motivos) por uno de dos motivos, que el mensaje
distingue:

- SEGURO: los bloques fallidos ya pasan del 1 % de los n_base del caso;
  ningun resto de la corrida puede bajarlo, y el analisis LO RECHAZARA. Es
  exacto: nunca para un caso que el analisis aceptaria;
- TASA: tras al menos `max(16, min(n_base/4, 256))` bloques terminados (128
  con n = 512, 256 con n = 2 048), los bloques fallidos TERMINADOS pasan de
  FACTOR_TASA veces el umbral (4 %) de los terminados. La tasa SUGIERE un
  fallo sistematico; el analisis podria aceptar el caso.

  Por que 4 (ronda 2, R-1). Con el umbral simple, un 0,5 % de fallos paraba
  entre el 25 y el 29 % de los casos buenos (Monte Carlo de la re-revision).
  La re-revision propuso el triple; medido con esta misma clase (2 000
  repeticiones por punto, `scratchpad/mc_tasa.py`), el triple aun da falsos
  positivos con n = 512: 1 de 2 000 con p = 0,5 % y 11 de 2 000 con p = 0,8 %
  y con 1 %. Con el cuadruple, CERO en todos los puntos (p de 0,2 % a 1 %,
  n = 512 y 2 048), y un caso roto se detecta igual de pronto: con p = 5 %,
  en el bloque 111 (n = 512) y 255 (n = 2 048); con p = 20 %, en el 27 y el
  102, lo mismo que con el triple. Con n = 512 la tasa nunca se adelanta a
  la regla segura (6 > 5,12 en el bloque 128), asi que alli no puede dar un
  falso positivo por construccion; con n = 2 048 adelanta la parada de un
  caso roto del bloque ~412 al 256.

Las evaluaciones son deterministas: `--reanudar` volveria a fallar en las
mismas filas. Hay que mirar los motivos. `--tolera-fallos` desactiva la
parada (en el lanzador, `TOLERA_FALLOS=1`); el analisis sigue rechazando el
caso si los bloques descartados pasan del 1 %.

Un caso NO se amplia reutilizando sus filas: si ya tiene una corrida con
otro n (por ejemplo, el humo lo recorto a 1 024 y ahora se quiere 2 048), la
nueva se rechaza (codigo 2) en vez de correr al lado. Los n' primeros
bloques de la muestra de n SON la muestra de n', pero esta herramienta no
siembra una corrida con otra: la muestra de n se corre entera, despues de
mover la anterior a otra carpeta.

El humo imprime tres lineas que el lanzador lee: `NBASE_PROPUESTO=` (el n de
los casos de diseno de la noche; recortado solo si el primero ni solo cabe), `CASOS_NOCHE=` (los que
caben, en orden) y `CASOS_SIGUIENTE=` (los que pasan a la noche siguiente).
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import csv
import json
import os
import re
import shutil
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from gsa_directo import comun  # noqa: E402

COLS_ENTRADA = ["idx"] + list(comun.NOMBRES)
COLS_COLA = ["seg", "rss_mb", "motivo"]
N_MINIMO = 64
UMBRAL_FALLOS = 0.01          # el mismo del analisis (UMBRAL_DESCARTE)
FACTOR_TASA = 4               # la regla de la tasa para con 4 x el umbral (R-1)


def columnas(nombres) -> list:
    return COLS_ENTRADA + comun.columnas_salida(nombres) + COLS_COLA


# ── El evaluador falso (modo --verificar) ───────────────────────────────────
class InsumosFalsos:
    """Sin datos: solo lo que el camino de orquestacion necesita."""

    def __init__(self, caso: str):
        self.caso = caso
        self.nombres = comun.nombres_caso(caso)
        self.fuente_bolsa = "FALSO"
        self.fechas = ["FALSO", "FALSO"]


def evalua_falso(ins, x, idx: int = -1) -> dict:
    """Numeros FALSOS y deterministas que dependen de las seis entradas.

    Recorre todo el camino menos el modelo: la maquinaria (pool, ventana,
    CSV con fsync, reanudar, humo) se prueba en segundos. Los indices de
    `GSA_DIRECTO_FALSO_FALLA` («3,7») fallan, para probar el reintento."""
    falla = os.environ.get("GSA_DIRECTO_FALSO_FALLA", "")
    if falla and str(idx) in [s.strip() for s in falla.split(",")]:
        raise ValueError(f"falso: el indice {idx} falla a proposito")
    x = np.asarray(x, dtype=float)
    f_cv, f_b, f_t, f_p, e_g, e_d = x
    base = 4.6e7 * f_t * (0.8 * e_d + 0.2 * e_g)
    out = {"P2P": base + 3e5 * f_cv, "C1": base, "C2": base + 3e5 * f_cv,
           "C3": base * 0.92 - 1e4 * f_b, "C4": base * 0.96 - 2e5 * f_p,
           "C5": base * 0.95 - 5e4 * f_b, "P2P_colectivo": base * 0.96
           - 1.5e5 * f_p, "P2Pcom": base * 1.01 - 1e5 * f_p,
           "C2ppa": base * 0.95 + 1e5 * e_g,
           "H1": base * 0.99 - 8e4 * f_p}
    out["H1comp"] = out["H1"]
    out["energia"] = 4592.0 * e_g
    out["excedente"] = 3e5 * f_cv
    out["parte_vendedor"] = 0.54 + 0.01 * np.sin(f_cv)
    for b, (a, c) in comun.BRECHAS.items():
        out[b] = out[a] - out[c]
    out.update(n_horas_mercado=1126.0, n_cuantal=0.0, n_sin_ganancia=0.0,
               retiros=0.0)
    for k, nombre in enumerate(ins.nombres):
        for b, (a, c) in comun.BRECHAS_INSTITUCION.items():
            out[f"{b}__{nombre}"] = (out[a] - out[c]) / 5.0 + 1e3 * (k - 2)
    return {c: float(out[c]) for c in comun.columnas_salida(ins.nombres)}


# ── Estado de cada proceso del pool ─────────────────────────────────────────
_INS = None
_FALSO = False
_TOPE = None


def _inicia(ins, falso: bool, tope_eval) -> None:
    global _INS, _FALSO, _TOPE
    _INS, _FALSO, _TOPE = ins, bool(falso), tope_eval
    comun.salida_utf8()
    if not falso:
        from gsa_directo import evaluador
        evaluador.inicia_proceso()
        # Las importaciones pesadas, aqui y no en la primera evaluacion: si
        # no, la mediana del humo mediria importaciones (la mitad de 32
        # evaluaciones con 16 procesos serian primeras).
        import main_simulation  # noqa: F401
        import scenarios  # noqa: F401
        from core import ems_p2p, reposo_mercado  # noqa: F401


class TopeEvaluacion(Exception):
    pass


@contextlib.contextmanager
def _alarma(segundos):
    """Tope de pared por evaluacion con SIGALRM (Linux). En Windows no hay
    alarma: el tope queda en el esperador del padre y en el `timeout` del
    lanzador."""
    import signal
    if not segundos or not hasattr(signal, "setitimer"):
        yield
        return

    def _salta(signum, frame):
        raise TopeEvaluacion(f"la evaluacion paso de {segundos} s")

    anterior = signal.signal(signal.SIGALRM, _salta)
    signal.setitimer(signal.ITIMER_REAL, float(segundos))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, anterior)


def _tarea(args):
    i, x = args
    t0 = time.time()
    motivo = ""
    y = None
    try:
        with _alarma(_TOPE):
            if _FALSO:
                y = evalua_falso(_INS, x, i)
            else:
                from gsa_directo import evaluador
                y = evaluador.evalua(_INS, x)
    except Exception as exc:        # se anota el motivo; no se imputa nada
        motivo = f"{type(exc).__name__}: {exc}".replace("\n", " ")[:240]
        y = None
    return i, y, time.time() - t0, comun.rss_mb(), motivo


# ── El punto de control ─────────────────────────────────────────────────────
def fila_valida(r: dict, cols: list) -> bool:
    """Una fila completa, sin motivo de fallo y con salidas finitas."""
    if r is None or len(r) < len(cols) or any(r.get(c) is None for c in cols):
        return False
    if (r.get("motivo") or "").strip():
        return False
    try:
        int(r["idx"])
        vals = [float(r[c]) for c in comun.SALIDAS]
    except (TypeError, ValueError):
        return False
    return bool(np.all(np.isfinite(vals)))


def lee_filas(ruta: Path, cols: list) -> dict:
    """{idx: fila} de las filas COMPLETAS (buenas o fallidas con motivo);
    descarta las truncadas por un corte a mitad de escritura. Si un indice
    aparece dos veces, gana la ultima buena."""
    filas = {}
    if not ruta.exists():
        return filas
    with open(ruta, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if len(r) < len(cols) or any(r.get(c) is None for c in cols):
                continue
            if None in r:            # columnas de mas: fila corrupta
                continue
            try:
                i = int(r["idx"])
                float(r[cols[-2]])   # rss_mb: la penultima columna existe
            except (TypeError, ValueError):
                continue
            if i in filas and fila_valida(filas[i], cols) \
                    and not fila_valida(r, cols):
                continue
            filas[i] = r
    return filas


def _formato(v) -> str:
    return "" if v is None else f"{float(v):.17g}"


def escribe_atomico(ruta: Path, texto: str) -> None:
    """Escribe `texto` en `ruta` por un temporal con `fsync` y `os.replace`:
    un corte deja el fichero viejo o el nuevo entero, nunca uno truncado
    (ronda 2 de la tarea G, m-2: la meta se reescribe en cada tanda, y una
    meta truncada hacia morir el siguiente --reanudar con JSONDecodeError)."""
    tmp = ruta.with_name(ruta.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(texto)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, ruta)


def reescribe_prefijo(destino: Path, cols: list, buenas: dict) -> None:
    """Deja en `destino` la cabecera y las filas buenas SIN truncarlo nunca
    (ronda de arreglos de la tarea G, M-6).

    Antes se copiaba el CSV al `.bak` y se truncaba para reescribirlo: si la
    tanda moria antes del `fsync` y se reanudaba otra vez, el `.bak` bueno se
    pisaba con el CSV truncado. Ahora el prefijo se escribe a un temporal
    con `fsync` y se cambia con `os.replace`, que es atomico; el `.bak` se
    hace igual, por temporal. Ni el CSV ni su respaldo pueden quedar a
    medias: un corte deja el fichero viejo o el nuevo entero."""
    tmp = destino.with_name(destino.name + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i in sorted(buenas):
            w.writerow([buenas[i][c] for c in cols])
        f.flush()
        os.fsync(f.fileno())
    if destino.exists() and destino.stat().st_size > 0:
        respaldo = destino.with_suffix(".csv.bak")
        tmp_bak = respaldo.with_name(respaldo.name + ".tmp")
        shutil.copy2(destino, tmp_bak)
        with open(tmp_bak, "rb+") as fb:
            os.fsync(fb.fileno())
        os.replace(tmp_bak, respaldo)
        print(f"  respaldo en {respaldo.name}")
    os.replace(tmp, destino)


class Recuento:
    """Bloques de Saltelli terminados y fallidos mientras se escribe, para
    la parada temprana (ronda de arreglos de la tarea G, I-2; ver el
    docstring del modulo)."""

    def __init__(self, n_base: int, ya_buenas=(), B: int = comun.B):
        self.n_base, self.B = int(n_base), int(B)
        self.filas = collections.Counter(int(i) // self.B for i in ya_buenas)
        self.terminados = sum(1 for v in self.filas.values() if v == self.B)
        self.fallidos = set()
        self.fallidos_terminados = 0
        self.minimo = max(16, min(self.n_base // 4, 256))

    def anota(self, i: int, fallo: bool) -> None:
        b = int(i) // self.B
        self.filas[b] += 1
        if fallo:
            self.fallidos.add(b)
        if self.filas[b] == self.B:
            self.terminados += 1
            if b in self.fallidos:
                self.fallidos_terminados += 1

    def veredicto(self) -> str:
        """'' si se sigue; si no, por que se para (empieza por SEGURO o por
        TASA). La tasa cuenta solo bloques TERMINADOS en el numerador y en
        el denominador; lo seguro, cualquier bloque con una fila fallida,
        porque ese bloque se descarta entero pase lo que pase."""
        nf = len(self.fallidos)
        if nf > UMBRAL_FALLOS * self.n_base:
            return (f"SEGURO: {nf} bloques fallidos de {self.n_base}, mas del "
                    f"{100 * UMBRAL_FALLOS:.0f} % del caso entero: el "
                    f"analisis lo rechazara")
        nt = self.fallidos_terminados
        if self.terminados >= self.minimo and \
                nt > FACTOR_TASA * UMBRAL_FALLOS * self.terminados:
            return (f"TASA: {nt} bloques fallidos de {self.terminados} "
                    f"terminados ({100 * nt / self.terminados:.2f} %), mas "
                    f"del {100 * FACTOR_TASA * UMBRAL_FALLOS:.0f} % ({FACTOR_TASA} "
                    f"veces el umbral): la tasa sugiere un fallo "
                    f"sistematico, aunque el analisis aun podria aceptar el "
                    f"caso")
        return ""


PATRON_META = re.compile(r"^muestras_(?P<caso>[A-Z0-9]+)_n(?P<n>\d+)_s"
                         r"(?P<s>\d+)(?P<suf>.*)\.meta\.json$")


def corridas_con_otro_n(carpeta: Path, caso: str, n_base: int, semilla: int,
                        sufijo: str) -> list:
    """Las metas del mismo caso, semilla y sufijo con OTRO n (M-4)."""
    out = []
    if not carpeta.is_dir():
        return out
    for p in sorted(carpeta.glob(f"muestras_{caso}_n*.meta.json")):
        m = PATRON_META.match(p.name)
        if m and m["caso"] == caso and int(m["s"]) == int(semilla) \
                and m["suf"] == sufijo and int(m["n"]) != int(n_base):
            out.append(p)
    return out


# ── Plan de la noche a partir del humo ──────────────────────────────────────
def planifica(mediana_s: float, procesos: int, pedidos: list, tope_h: float,
              forzar: bool = False) -> dict:
    """Que casos caben en la noche, con que n, y cuales pasan a la siguiente.

    `pedidos` es [(caso, n)] en orden de prioridad. Reglas (apartados 7.2 y
    7.3 del diseno, con la enmienda de la ronda 2 de la tarea G, m-1):

    1. Los casos de diseno pedidos (E0, E2, E4) van primero, en su orden y
       CON SU n (2 048, D77), y detras los demas, en su orden. Cada uno entra
       si cabe en lo que queda de la noche; el primero que no cabe pasa a la
       noche siguiente con su n intacto, y con el todos los de detras (el
       orden de prioridad se conserva). Asi, lanzar los doce a 8 s y 16
       procesos corre E0 y E2 a 2 048 esta noche y deja E4 y el resto para
       la siguiente, que es el calendario del 7.3; antes se recortaban los
       tres casos de diseno a 1 024 para meterlos juntos, y por M-4 ese
       recorte ya no se deshace.
    2. RECORTE solo si el humo dice que no cabe: si el PRIMER caso de la
       noche es de diseno y ni el solo cabe en `tope_h`, su n se recorta a la
       mayor potencia de dos que quepa (hasta N_MINIMO), y se dice.
    3. Con `forzar`, ni se recorta ni se aplaza nada.
    """
    procesos = max(1, int(procesos))

    def horas(n):
        return n * comun.B * mediana_s / procesos / 3600.0

    diseno = [(c, n) for c, n in pedidos if c in comun.CASOS_DISENO]
    resto = [(c, n) for c, n in pedidos if c not in comun.CASOS_DISENO]
    ordenados = diseno + resto
    nd0 = max([n for _, n in diseno] or [0])
    nd = nd0
    noche, siguiente, usado = [], [], 0.0
    for k, (c, n) in enumerate(ordenados):
        if forzar:
            noche.append((c, n, horas(n)))
            usado += horas(n)
            continue
        if k == 0 and c in comun.CASOS_DISENO and horas(n) > tope_h:
            while horas(n) > tope_h and n > N_MINIMO:
                n //= 2
            nd = n
        if not siguiente and usado + horas(n) <= tope_h:
            noche.append((c, n, horas(n)))
            usado += horas(n)
        else:
            siguiente.append(c)
    cabe = forzar or (bool(noche) and usado <= tope_h)
    return dict(n_diseno=nd, n_diseno_pedido=nd0, recortado=nd != nd0,
                noche=noche, siguiente=siguiente, horas_total=usado,
                cabe=cabe)


def _lee_pedidos(texto: str) -> list:
    pedidos = []
    for par in (texto or "").split():
        caso, n = par.split(":", 1)
        if caso not in comun.CASOS_SOBOL:
            raise SystemExit(f"--proyecta: {caso!r} no corre el Sobol "
                             f"(casos: {' '.join(comun.CASOS_SOBOL)})")
        pedidos.append((caso, int(n)))
    return pedidos


# ── El pool con ventana acotada ─────────────────────────────────────────────
def _corre_pool(pend, X, ins, falso, procesos, tope_eval, ventana,
                al_terminar, espera_max):
    """Somete `pend` EN ORDEN, con como mucho `ventana` en vuelo, y llama a
    `al_terminar(resultado)` por cada evaluacion. Devuelve el estado:
    "ok", "roto", "colgado", "interrumpido" o "parada" (si `al_terminar`
    devuelve "parar": la parada temprana por bloques fallidos)."""
    ex = ProcessPoolExecutor(max_workers=procesos, initializer=_inicia,
                             initargs=(ins, falso, tope_eval))
    estado = "ok"
    try:
        cola = iter(pend)
        vuelo = set()

        def llena():
            while len(vuelo) < ventana:
                try:
                    i = next(cola)
                except StopIteration:
                    return
                vuelo.add(ex.submit(_tarea, (i, X[i])))

        llena()
        while vuelo:
            hechos, _ = wait(vuelo, timeout=espera_max,
                             return_when=FIRST_COMPLETED)
            if not hechos:
                print(f"\n  COLGADO: ninguna evaluacion termino en "
                      f"{espera_max:.0f} s. Lo escrito vale; relanza con "
                      f"--reanudar.", flush=True)
                estado = "colgado"
                break
            for fut in hechos:
                vuelo.discard(fut)
                try:
                    res = fut.result()
                except BrokenProcessPool as exc:
                    print(f"\n  POOL ROTO ({exc}): murio un trabajador (OOM "
                          f"o segfault). Lo escrito vale.", flush=True)
                    estado = "roto"
                    break
                except Exception as exc:
                    # `_tarea` atrapa los fallos de la evaluacion; esto es la
                    # maquinaria. La fila falta y el cierre lo dice (codigo 5).
                    print(f"    [evaluacion perdida] {type(exc).__name__}: "
                          f"{exc}", flush=True)
                    continue
                if al_terminar(res) == "parar":
                    estado = "parada"
                    break
            if estado != "ok":
                break
            llena()
    except BaseException as exc:
        print(f"\n  INTERRUMPIDO: {type(exc).__name__}: {exc}", flush=True)
        estado = "interrumpido"
    finally:
        if estado == "ok":
            ex.shutdown(wait=True)
        else:
            _derriba(ex)
    return estado


def _derriba(ex) -> None:
    """Cierra el pool SIN esperar lo que ya esta en los trabajadores, y los
    mata: `shutdown(wait=False)` no lo hace, y con `os._exit` despues los
    trabajadores quedaban huerfanos (medido en Windows el 2026-09-26: uno
    siguio vivo con la tuberia de salida abierta)."""
    procesos = list((getattr(ex, "_processes", None) or {}).values())
    ex.shutdown(wait=False, cancel_futures=True)
    for pr in procesos:
        try:
            pr.kill()
        except (OSError, ValueError, AttributeError) as exc:
            print(f"    no se pudo matar al trabajador {pr}: {exc}", flush=True)


# ── Humo ────────────────────────────────────────────────────────────────────
def humo(args, ins, falso) -> int:
    X = comun.muestra(args.n_base, args.semilla)[: args.humo]
    segs, rss, motivos = [], [], {}
    t0 = time.time()

    def anota(res):
        i, y, seg, mb, motivo = res
        segs.append(seg)
        rss.append(mb)
        if motivo:
            motivos[i] = motivo

    estado = _corre_pool(list(range(len(X))), X, ins, falso, args.procesos,
                         args.tope_eval, max(1, 2 * args.procesos), anota,
                         espera_max=max(3.0 * args.tope_eval, 600.0))
    reloj = time.time() - t0
    if not segs:
        print("  HUMO SIN EVALUACIONES: nada termino.")
        return 1
    med = float(np.median(segs))
    print()
    print(f"  humo: {len(segs)} evaluaciones en {reloj:.1f} s de reloj con "
          f"{args.procesos} procesos ({estado})")
    print(f"  segundos por evaluacion: mediana {med:.2f}  p90 "
          f"{np.percentile(segs, 90):.2f}  maximo {max(segs):.2f}")
    rss_ok = [m for m in rss if np.isfinite(m)]
    if rss_ok:
        print(f"  memoria residente maxima por trabajador: {max(rss_ok):.0f} MB "
              f"(mediana {np.median(rss_ok):.0f} MB)")
    else:
        print("  memoria residente: no medible en esta maquina")
    if motivos:
        print(f"  AVISO: {len(motivos)} evaluaciones fallaron: "
              f"{sorted(set(motivos.values()))[:5]}")
    if len(motivos) == len(segs):
        print("  HUMO EN ROJO: fallaron todas.")
        return 1
    print(f"HUMO_MEDIANA_MS={int(round(med * 1000))}")
    rc = 0
    pedidos = _lee_pedidos(args.proyecta) or [(args.caso, args.n_base)]
    p = planifica(med, args.procesos, pedidos, args.tope_noche_h,
                  forzar=args.forzar_n)
    print()
    print(f"  plan con {args.procesos} procesos y {med:.2f} s por evaluacion "
          f"(tope de la noche {args.tope_noche_h:g} h):")
    for c, n, h in p["noche"]:
        print(f"    {c:<5} n = {n:>5}  M = {n * comun.B:>6}  {h:6.2f} h")
    print(f"    total {p['horas_total']:.2f} h")
    if p["recortado"]:
        print(f"  RECORTE: con la mediana del humo, {p['noche'][0][0] if p['noche'] else 'el primer caso'} "
              f"no cabe solo en la noche con n = {p['n_diseno_pedido']}; va "
              f"con n = {p['n_diseno']}, y por M-4 no se ampliara despues "
              f"reutilizando sus filas (FORZAR=1 no recorta)")
    if p["siguiente"]:
        print(f"  NO CABEN ESTA NOCHE y pasan a la siguiente, con su n: "
              f"{' '.join(p['siguiente'])}")
    if not p["cabe"]:
        print(f"  NO CABE: el primer caso no entra en "
              f"{args.tope_noche_h:g} h (ni recortado a n = {N_MINIMO} si es "
              f"de diseno). Parte la lista, o FORZAR=1.")
        rc = 7
    print(f"NBASE_PROPUESTO={p['n_diseno'] or args.n_base}")
    print(f"CASOS_NOCHE={' '.join(c for c, _, _ in p['noche'])}")
    print(f"CASOS_SIGUIENTE={' '.join(p['siguiente'])}")
    return rc


# ── La corrida ──────────────────────────────────────────────────────────────
def ejecuta(argv=None) -> int:
    comun.salida_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--caso", required=True, choices=list(comun.CASOS))
    ap.add_argument("--n-base", type=int, default=None,
                    help="potencia de dos; por defecto 2048 en E0/E2/E4 y "
                         "512 en los demas (D77)")
    ap.add_argument("--semilla", type=int, default=comun.SEMILLA)
    ap.add_argument("--procesos", type=int, default=None)
    ap.add_argument("--reanudar", action="store_true")
    ap.add_argument("--forzar", action="store_true",
                    help="sobrescribe un CSV con datos (sin --reanudar)")
    ap.add_argument("--tope-eval", type=float, default=300.0,
                    help="tope de pared por evaluacion (s), por SIGALRM")
    ap.add_argument("--ventana", type=int, default=None,
                    help="evaluaciones en vuelo (defecto 4 x procesos)")
    ap.add_argument("--humo", type=int, default=0, metavar="N")
    ap.add_argument("--proyecta", default="",
                    help="con --humo: «E0:2048 E2:2048 E1:512 ...»")
    ap.add_argument("--tope-noche-h", type=float, default=9.0)
    ap.add_argument("--forzar-n", action="store_true",
                    help="con --humo: ni recorta n ni aplaza casos")
    ap.add_argument("--tolera-fallos", action="store_true",
                    help="sin parada temprana por bloques fallidos (codigo "
                         "8); el analisis los rechazara igual si pasan del "
                         "1 %%")
    ap.add_argument("--salidas", default=str(comun.salidas_defecto()))
    ap.add_argument("--mte-root", default=None)
    ap.add_argument("--cache", default=None,
                    help="carpeta del .npz de la carga (defecto "
                         "<salidas>/cache)")
    ap.add_argument("--dia", default=None,
                    help="solo para humos locales: replica --day")
    ap.add_argument("--verificar", action="store_true",
                    help="evaluador FALSO: prueba la maquinaria en segundos")
    args = ap.parse_args(argv)

    if args.caso in comun.SOLO_DETERMINISTAS:
        print(f"  ABORTA: {args.caso} no corre el Sobol (ronda de arreglos de "
              f"la tarea G, I-1). Es E0 con el costo de comercializar x2, y el "
              f"Sobol de E0 ya recorre f_cv en [0,25; 2]; sobre {args.caso}, "
              f"f_cv multiplicaria un cvm que ya viene x2 y saldria del rango "
              f"aprobado (D74). {args.caso} queda como contraste "
              f"determinista en la compuerta del punto base.")
        return 2
    if args.n_base is None:
        args.n_base = comun.n_base_de(args.caso)
    if not comun.es_potencia_de_dos(args.n_base):
        print(f"  ABORTA: n_base = {args.n_base} no es potencia de dos; se "
              f"pierde el anidamiento de los bloques.")
        return 2
    if args.procesos is None:
        env = os.environ.get("PROCS", "").strip()
        args.procesos = (int(env) if env.isdigit() and int(env) > 0
                         else max(1, (os.cpu_count() or 4) - 2))
    ventana = args.ventana or 4 * args.procesos
    salidas = Path(args.salidas)
    cache = Path(args.cache) if args.cache else salidas / "cache"

    print("=" * 70)
    print(f"GSA DIRECTO (D73) · caso {args.caso} ({comun.CASOS[args.caso] or 'sin opcion'})"
          + ("  · VERIFICAR: numeros FALSOS" if args.verificar else ""))
    print("=" * 70)

    t0 = time.time()
    if args.verificar:
        ins = InsumosFalsos(args.caso)
        h_datos = "FALSO"
        mte_root = "FALSO"
    else:
        from gsa_directo import evaluador
        mte_root = args.mte_root or comun.mte_root_defecto()
        h_datos = comun.huella_datos(mte_root)
        ins = evaluador.prepara_caso(args.caso, mte_root=mte_root,
                                     cache_dir=cache, dia=args.dia)
    print(f"  insumos en {time.time() - t0:.1f} s · agentes {ins.nombres} · "
          f"bolsa {ins.fuente_bolsa} · horizonte {ins.fechas[0]} a "
          f"{ins.fechas[-1]}")
    print(f"  procesos {args.procesos} · ventana {ventana} · tope por "
          f"evaluacion {args.tope_eval:g} s")

    if args.humo:
        return humo(args, ins, args.verificar)

    X = comun.muestra(args.n_base, args.semilla)
    M = X.shape[0]
    cols = columnas(ins.nombres)
    tag = (f"{args.caso}_n{args.n_base}_s{args.semilla}"
           + ("_VERIF" if args.verificar else "")
           + (f"_dia{args.dia}" if args.dia else ""))
    carpeta = salidas / args.caso
    destino = carpeta / f"muestras_{tag}.csv"
    meta_p = carpeta / f"muestras_{tag}.meta.json"
    huella = comun.huella_diseno(args.caso, args.n_base, args.semilla)
    print(f"  n_base {args.n_base} -> M = {M} ({comun.B} filas por bloque); "
          f"semilla {args.semilla}; huella {huella}; dato {h_datos}")
    print(f"  salida {destino}")

    sufijo = tag[len(f"{args.caso}_n{args.n_base}_s{args.semilla}"):]
    otras = corridas_con_otro_n(carpeta, args.caso, args.n_base,
                                args.semilla, sufijo)
    if otras:
        print(f"\n  ABORTA: {args.caso} ya tiene una corrida con otro n: "
              f"{', '.join(p.name for p in otras)}. Un caso no se amplia "
              f"reutilizando sus filas: la muestra de n = {args.n_base} se "
              f"corre ENTERA (aunque sus primeros bloques sean los de la "
              f"otra). Si es lo que quieres, mueve la corrida anterior a otra "
              f"carpeta y relanza; si querias retomarla, pide su n.")
        return 2
    codigo = comun.version_codigo()
    codigos = [codigo]
    if meta_p.exists():
        prev = json.loads(meta_p.read_text(encoding="utf-8"))
        if prev.get("huella") != huella:
            print(f"\n  ABORTA: ya hay una corrida con OTRO diseno bajo este "
                  f"nombre ({prev.get('huella')} frente a {huella}).")
            return 2
        if prev.get("huella_datos") != h_datos:
            print(f"\n  ABORTA: el diseno coincide pero el DATO cambio "
                  f"({prev.get('huella_datos')} frente a {h_datos}). Reanudar "
                  f"mezclaria dos poblaciones; renombra la corrida anterior.")
            return 2
        # 2026-10-02: la huella del diseno no lleva las salidas. Una corrida
        # con las columnas de antes de C2ppa y P2Pcom no se retoma con las
        # nuevas: mezclaria filas de dos esquemas bajo los mismos indices.
        if prev.get("columnas") is not None and list(prev["columnas"]) != cols:
            print(f"\n  ABORTA: ya hay una corrida con OTRAS columnas de salida "
                  f"bajo este nombre ({len(prev['columnas'])} frente a "
                  f"{len(cols)}): es de otra version de las salidas (p. ej. "
                  f"antes de C2ppa y P2Pcom). Usa otra carpeta de salidas "
                  f"(GSA_SALIDAS en el lanzador) o mueve la anterior.")
            return 2
        codigos = list(prev.get("codigos") or [prev.get("codigo")])
        if codigos[-1] != codigo:
            print(f"\n  AVISO: el CODIGO cambio desde la tanda anterior "
                  f"({codigos[-1]} frente a {codigo}). Si fue un `git pull` "
                  f"que toca core/ o scenarios/, las filas nuevas y las viejas "
                  f"son de dos versiones del modelo (M-5): no se hace git "
                  f"pull con un caso a medias.")
            codigos.append(codigo)
    if destino.exists() and destino.stat().st_size > 0 \
            and not args.reanudar and not args.forzar:
        print("\n  ABORTA: el CSV ya tiene datos; --reanudar lo continua, "
              "--forzar lo borra.")
        return 2

    # El punto base, en el padre: si no evalua, ninguna fila vale.
    t1 = time.time()
    try:
        if args.verificar:
            base = evalua_falso(ins, comun.PUNTO_BASE)
        else:
            from gsa_directo import evaluador
            base = evaluador.evalua(ins, comun.PUNTO_BASE)
    except Exception as exc:
        print(f"\n  ABORTA: el punto base no evalua: {type(exc).__name__}: "
              f"{exc}")
        return 3
    print(f"  punto base en {time.time() - t1:.1f} s: P2P "
          f"{base['P2P']:,.2f} · C1 {base['C1']:,.2f} · energia "
          f"{base['energia']:,.3f} · parte del vendedor "
          f"{base['parte_vendedor']:.4f} · cuantales {base['n_cuantal']:.0f}"
          f" · P2Pcom {base['P2Pcom']:,.2f} · C2ppa {base['C2ppa']:,.2f}"
          f" · H1 {base['H1']:,.2f}")

    carpeta.mkdir(parents=True, exist_ok=True)
    import scipy
    import SALib  # noqa: F401
    from importlib.metadata import version as _v
    escribe_atomico(meta_p, json.dumps({
        "huella": huella, "huella_datos": h_datos, "mte_root": mte_root,
        "tag": tag, "verificar": bool(args.verificar), "caso": args.caso,
        "opcion": comun.CASOS[args.caso], "dia": args.dia,
        "n_base": args.n_base, "semilla": args.semilla,
        "segundo_orden": comun.SEGUNDO_ORDEN, "B": comun.B, "M": M,
        "entradas": comun.NOMBRES, "soportes": comun.SOPORTES,
        "salidas": list(comun.SALIDAS), "columnas": cols,
        "nombres": ins.nombres, "fuente_bolsa": ins.fuente_bolsa,
        "horizonte": ins.fechas, "codigo": codigo, "codigos": codigos,
        "rotulos": {n: comun.ROTULOS[n] for n in comun.NOMBRES},
        "versiones": {"python": sys.version.split()[0],
                      "numpy": np.__version__, "scipy": scipy.__version__,
                      "SALib": _v("SALib")},
        "punto_base": base,
    }, indent=2, ensure_ascii=False))

    previas = lee_filas(destino, cols) if args.reanudar else {}
    buenas = {i: r for i, r in previas.items() if fila_valida(r, cols)}
    if previas:
        print(f"  [reanudar] {len(buenas)} buenas de {len(previas)} escritas; "
              f"se reintentan {len(previas) - len(buenas)} fallidas")
    pend = [i for i in range(M) if i not in buenas]
    if not pend:
        print("\n  nada pendiente: las M filas estan buenas.")
        return 0

    reescribe_prefijo(destino, cols, buenas)

    n_ok = n_mal = 0
    motivos: dict = {}
    recuento = Recuento(args.n_base, buenas)
    parada = [""]
    t_ini = time.time()
    with open(destino, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        cada = max(1, min(500, len(pend) // 100 or 1))
        print(f"\n  arrancando {len(pend)} evaluaciones...\n", flush=True)

        def escribe(res):
            nonlocal n_ok, n_mal
            i, y, seg, mb, motivo = res
            if y is None:
                vals = [""] * (len(cols) - len(COLS_ENTRADA) - len(COLS_COLA))
                n_mal += 1
                motivos[motivo.split(":")[0]] = \
                    motivos.get(motivo.split(":")[0], 0) + 1
            else:
                vals = [_formato(y[c]) for c in comun.columnas_salida(
                    ins.nombres)]
                n_ok += 1
            w.writerow([i] + [_formato(v) for v in X[i]] + vals
                       + [f"{seg:.3f}", f"{mb:.1f}", motivo])
            f.flush()
            os.fsync(f.fileno())
            hecho = n_ok + n_mal
            if hecho % cada == 0 or hecho == len(pend):
                el = time.time() - t_ini
                eta = el / hecho * (len(pend) - hecho)
                print(f"    {hecho:>6}/{len(pend)}  ok {n_ok}  fallo {n_mal}  "
                      f"{el / 3600:.2f} h  eta {eta / 3600:.2f} h", flush=True)
            recuento.anota(i, y is None)
            if not args.tolera_fallos:
                v = recuento.veredicto()
                if v:
                    parada[0] = v
                    return "parar"
            return ""

        estado = _corre_pool(pend, X, ins, args.verificar, args.procesos,
                             args.tope_eval, ventana, escribe,
                             espera_max=max(3.0 * args.tope_eval, 600.0))

    escritas = len(buenas) + n_ok + n_mal
    print()
    print("=" * 70)
    print(f"  filas escritas {escritas}/{M} · buenas {len(buenas) + n_ok} · "
          f"fallidas {n_mal} · {(time.time() - t_ini) / 3600:.2f} h")
    if motivos:
        print(f"  motivos de fallo de esta tanda: {motivos}")
    if estado == "parada":
        print(f"  PARADA TEMPRANA (codigo 8): {parada[0]}.")
        if parada[0].startswith("SEGURO"):
            print("  Ya pasa del 1 % de n_base: el analisis LO RECHAZARA sea "
                  "cual sea el resto de la corrida.")
        else:
            print("  La tasa sugiere un fallo SISTEMATICO; el caso aun podria "
                  "quedar por debajo del 1 % al final. Si los motivos no "
                  "muestran un defecto, --tolera-fallos (TOLERA_FALLOS=1 en "
                  "el lanzador) sigue hasta el final y deja decidir al "
                  "analisis.")
        print("  Las evaluaciones son deterministas: --reanudar sin mas "
              "volveria a parar en el mismo punto (salvo los topes de "
              "tiempo). Mira los motivos de arriba y la columna `motivo` "
              "del CSV antes de relanzar.")
        return 8
    if estado == "roto":
        print("  Baja --procesos y relanza con --reanudar.")
        return 4
    if estado in ("colgado", "interrumpido"):
        return 6
    if escritas < M:
        print(f"  Faltan {M - escritas} filas: relanza con --reanudar.")
        return 5
    if args.verificar:
        print("  VERIFICACION OK: los numeros de este fichero son FALSOS.")
    else:
        print(f"  Siguiente: python -u gsa_directo/analizar.py --caso "
              f"{args.caso} --n-base {args.n_base}")
    return 0


def main():
    rc = ejecuta()
    # Sin esto, el `atexit` de concurrent.futures esperaria a las
    # evaluaciones ya entregadas a los trabajadores; cada fila esta en disco.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
