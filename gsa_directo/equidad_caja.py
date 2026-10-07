"""La equidad dentro de la caja del analisis de sensibilidad global (EQ,
2026-10-07).

Actividades 3.3 y 4.1. Hasta hoy la equidad (el Gini del beneficio por
institucion) solo se media en el punto base: las muestras del GSA directo
guardan por institucion solo brechas, no el beneficio de cada mecanismo
(CANON §14.19, «Lo que no cubre»). Aqui se mide dentro de la misma caja.

LA CAJA ES LA DEL GSA, SIN CAMBIOS. Los seis factores y sus soportes de
`comun.SOPORTES` (Tabla de factores, D74), en los doce casos del Sobol
(`comun.CASOS_SOBOL`; CV2 queda fuera, como en el GSA). LOS PUNTOS son las
filas A y B de los `n` primeros bloques de la MISMA muestra de Saltelli
(`comun.muestra`, semilla 42): las muestras independientes, las mismas con
que el canon calcula la probabilidad de inversion (§13.2), y las mismas filas
(mismo `idx`) que ya tiene la corrida del GSA. 2·n puntos por caso; con el
defecto n = 512, 1 024 por caso y 12 288 en los doce.

EL MISMO EVALUADOR (`evaluador._evalua_todo`, sin cambios), en una sola
llamada por punto: el beneficio por institucion de los ocho escenarios del
motor y de C2 como PPA, el P2P colectivo, H1 y H1 con la compensacion.

LA EQUIDAD, CON LA DEFINICION DEL CANON (C-214, §14.6): el Gini es
`core.settlement.gini_index` sobre el beneficio neto por institucion, la
funcion que escribe la hoja `PoF_Fairness`; y la clase del par, la de
`reformateo/documento/scripts/precio_justicia_p2p_c4.py` (`clase`, importada
tal cual): «P2P domina» si el mercado tiene a la vez beneficio de comunidad
no menor y Gini no mayor (con la tolerancia de 1e-9 del guion), «intercambio»
si C4 es mas equitativo y menos eficiente, «C4 domina» y «otro». Se aplica al
mercado P2P frente a C4 y al P2P colectivo frente a C4.

LOS CONTROLES, que fallan en voz alta (codigo 1, y ninguna cifra vale):
  1. EL PUNTO BASE (los seis factores en 1), en cada caso, AL PESO contra la
     matriz del canon (`--matriz`, la misma comparacion de
     `compuerta_punto_base.py` que usa `tarifa_extrema.py`, con las huellas
     de los libros) y, con `--referencia-base`, contra el `punto_base.csv` de
     esa compuerta, columna por columna. Se evalua ANTES de la caja: con el
     control en rojo no se corre nada mas.
  2. CADA PUNTO DE LA CAJA, con `--referencia-gsa DIR` (la carpeta del GSA
     con H1, `SALIDAS_SERVIDOR/gsa_directo_h1_2026-10-04`), contra la fila
     del mismo `idx` del CSV de muestras del GSA: las seis entradas y todas
     las salidas comunes (niveles, brechas de comunidad y brechas por
     institucion), al peso. Es la comprobacion de que la caja es la del GSA
     y el evaluador el mismo, punto por punto.
  3. En cada punto, el beneficio de la comunidad de cada mecanismo es la
     suma de sus instituciones (1e-6 relativo).

UNA EVALUACION QUE FALLA no se imputa: queda con su motivo (codigo 3).

SALIDAS en `--salida-dir`:
  - `equidad_puntos.csv`: una fila por caso y punto (el punto base con
    `fila` = «base»): entradas, beneficio de comunidad y Gini de cada
    mecanismo, beneficio por institucion, la clase de los dos pares, si
    domina y si cambia frente al punto base, y la diferencia con el GSA;
  - `equidad_resumen.csv`: una fila por caso: el Gini de cada mecanismo en
    el punto base y su rango en la caja (minimo, p5, mediana, p95, maximo),
    la fraccion de puntos con el mercado (y el P2P colectivo) dominando a C4,
    con su intervalo de Wilson al 95 %, y cuantos puntos cambian la clase del
    punto base;
  - `resumen.txt`, lo mismo legible.

    python -u gsa_directo/equidad_caja.py \\
        --matriz SALIDAS_SERVIDOR/matriz_reposo \\
        --referencia-base SALIDAS_SERVIDOR/equidad_caja/base/punto_base.csv \\
        --referencia-gsa SALIDAS_SERVIDOR/gsa_directo_h1_2026-10-04 \\
        --salida-dir SALIDAS_SERVIDOR/equidad_caja --procesos 16

    python -u gsa_directo/equidad_caja.py --dia 2025-05-09 --casos E0 \\
        --n-base 2 --sin-escribir --procesos 2     # humo de un dia

Codigos: 0 todo bien; 1 un control en rojo; 2 uso; 3 evaluaciones fallidas
(con su motivo); 4 incompleta (el tope de sometimiento dejo puntos sin
correr: `--reanudar` sigue donde quedo).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import os
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from gsa_directo import comun  # noqa: E402

# Los mecanismos cuyo Gini se mide (beneficio por institucion). Los ocho del
# motor menos C2 (el contrato interno de CAL-52), C4_mensual (alias de C4) y
# el viejo mercado por el colectivo; mas C2 como PPA, el P2P colectivo, H1 y
# H1 con la compensacion de quien cede credito.
MECANISMOS = ("P2P", "P2Pcom", "C1", "C2ppa", "C3", "C4", "C5", "H1",
              "H1comp")
# Los pares cuya clase se mide (§14.6 y §14.24): (minuendo, sustraendo).
PARES = {"P2P_C4": ("P2P", "C4"), "P2Pcom_C4": ("P2Pcom", "C4")}
N_BASE = 512
CLASE_DOMINA = "P2P domina"
TOL_SUMA = 1e-6                  # comunidad = suma de instituciones
MAX_ROJOS_GSA = 10               # puntos distintos del GSA antes de parar
Z95 = 1.959963984540054
GUION_PJ = (comun.RAIZ / "reformateo" / "documento" / "scripts"
            / "precio_justicia_p2p_c4.py")
NOMBRE_PUNTOS = "equidad_puntos.csv"
NOMBRE_RESUMEN = "equidad_resumen.csv"

_EST = {}
_PJ = None


# ── La definicion del canon ────────────────────────────────────────────────
def guion_pj():
    """El guion del precio de la justicia (§14.6), importado tal cual: su
    `clase` es la del canon. No lee nada al importarse."""
    global _PJ
    if _PJ is None:
        spec = importlib.util.spec_from_file_location("precio_justicia_p2p_c4",
                                                      GUION_PJ)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _PJ = mod
    return _PJ


def gini(valores) -> float:
    """El Gini del canon (C-214): `core.settlement.gini_index` sobre el
    beneficio neto por institucion. Falla con un valor no finito."""
    from core.settlement import gini_index
    v = np.asarray(valores, dtype=float)
    if v.size == 0 or not np.all(np.isfinite(v)):
        raise ValueError(f"Gini: beneficios no finitos o vacios: {v!r}")
    return float(gini_index(v))


def clase(W_a: float, W_c4: float, g_a: float, g_c4: float) -> str:
    """La clase del par frente a C4, con la funcion del guion del canon."""
    for v in (W_a, W_c4, g_a, g_c4):
        if not math.isfinite(float(v)):
            raise ValueError(f"clase: valor no finito {v!r}")
    return guion_pj().clase(dict(W_P2P=float(W_a), W_C4=float(W_c4),
                                 gini_P2P=float(g_a), gini_C4=float(g_c4)))


def wilson(x: int, n: int) -> tuple:
    if n <= 0:
        return (float("nan"), float("nan"))
    p = x / n
    den = 1.0 + Z95 * Z95 / n
    centro = (p + Z95 * Z95 / (2 * n)) / den
    medio = Z95 * math.sqrt(p * (1 - p) / n + Z95 * Z95 / (4 * n * n)) / den
    return (max(0.0, centro - medio), min(1.0, centro + medio))


# ── Los puntos ─────────────────────────────────────────────────────────────
def puntos_caja(n_base: int) -> list:
    """[(idx, fila, bloque, x)] de las filas A (la primera) y B (la ultima)
    de los `n_base` primeros bloques de la muestra del GSA (semilla 42). El
    `idx` es la fila de la muestra, el mismo del CSV del GSA."""
    if n_base < 1:
        raise ValueError(f"n_base = {n_base}")
    X = comun.muestra(int(n_base))
    B = comun.B
    fuera = []
    for b in range(int(n_base)):
        for fila, i in (("A", b * B), ("B", b * B + B - 1)):
            fuera.append((int(i), fila, b, np.asarray(X[i], dtype=float)))
    return fuera


def beneficios(cr, nuevos) -> dict:
    """{mecanismo: (N,)} del beneficio por institucion de MECANISMOS."""
    pa = {e: np.asarray(v, dtype=float) for e, v
          in cr.net_benefit_per_agent.items()}
    pa.update({k: np.asarray(v, dtype=float) for k, v in nuevos.items()})
    faltan = [m for m in MECANISMOS if m not in pa]
    if faltan:
        raise ValueError(f"el evaluador no trae {faltan}")
    return {m: pa[m].copy() for m in MECANISMOS}


def comprueba_suma(out: dict, ben: dict) -> None:
    """Control 3: la comunidad es la suma de sus instituciones."""
    for m in MECANISMOS:
        if m == "H1comp":            # suma cero frente a H1: es H1
            ref = out["H1"]
        else:
            ref = out[m]
        s = float(np.sum(ben[m]))
        if abs(s - ref) > TOL_SUMA * max(1.0, abs(ref)):
            raise ValueError(f"{m}: la suma por institucion ({s!r}) no es la "
                             f"comunidad ({ref!r})")


def metricas(ben: dict) -> dict:
    """W (comunidad) y Gini de cada mecanismo, y la clase de cada par."""
    W = {m: float(np.sum(ben[m])) for m in MECANISMOS}
    G = {m: gini(ben[m]) for m in MECANISMOS}
    C = {p: clase(W[a], W[c], G[a], G[c]) for p, (a, c) in PARES.items()}
    return dict(W=W, G=G, C=C)


def fila_punto(caso, idx, fila, bloque, x, out, ben, nombres, base) -> dict:
    """La fila de `equidad_puntos.csv`. `base` es lo de `metricas` en el
    punto base del caso (None en el propio punto base)."""
    m = metricas(ben)
    f = dict(caso=caso, idx=idx, fila=fila, bloque=bloque)
    for nombre, v in zip(comun.NOMBRES, np.asarray(x, dtype=float)):
        f[nombre] = float(v)
    for mec in MECANISMOS:
        f[f"W_{mec}"] = m["W"][mec]
        f[f"gini_{mec}"] = m["G"][mec]
    for p in PARES:
        f[f"clase_{p}"] = m["C"][p]
        f[f"domina_{p}"] = int(m["C"][p] == CLASE_DOMINA)
        f[f"cambia_{p}"] = ("" if base is None
                            else int(m["C"][p] != base["C"][p]))
    for mec in MECANISMOS:
        for inst in comun.INSTITUCIONES:
            f[f"{mec}__{inst}"] = (float(ben[mec][nombres.index(inst)])
                                   if inst in nombres else "")
    for k in ("n_horas_mercado", "n_cuantal", "retiros"):
        f[k] = float(out[k])
    return f


def columnas() -> list:
    cols = ["caso", "idx", "fila", "bloque", *comun.NOMBRES]
    cols += [f"W_{m}" for m in MECANISMOS] + [f"gini_{m}" for m in MECANISMOS]
    for p in PARES:
        cols += [f"clase_{p}", f"domina_{p}", f"cambia_{p}"]
    cols += [f"{m}__{i}" for m in MECANISMOS for i in comun.INSTITUCIONES]
    cols += ["n_horas_mercado", "n_cuantal", "retiros", "gsa_dif_max",
             "seg", "rss_mb", "motivo"]
    return cols


# ── La referencia del GSA ──────────────────────────────────────────────────
def lee_gsa(dir_gsa: Path, caso: str, indices) -> dict:
    """{idx: fila} del CSV de muestras del GSA del caso, solo los pedidos.
    Falla en voz alta si no hay un unico CSV o si falta alguno."""
    cands = sorted((dir_gsa / caso).glob(f"muestras_{caso}_n*_s42.csv"))
    if len(cands) != 1:
        raise FileNotFoundError(f"{dir_gsa / caso}: se esperaba un "
                                f"muestras_{caso}_n*_s42.csv y hay "
                                f"{len(cands)}")
    quiero = set(int(i) for i in indices)
    filas = {}
    with open(cands[0], newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            i = int(r["idx"])
            if i in quiero:
                filas[i] = r
    faltan = sorted(quiero - set(filas))
    if faltan:
        raise ValueError(f"{cands[0].name} no trae {len(faltan)} de los "
                         f"puntos pedidos (el primero, {faltan[0]})")
    return filas


def compara_gsa(out: dict, x, fila_gsa: dict) -> tuple:
    """(max |dif|, [(columna, ref, evaluado)] de las que difieren mas que al
    peso). Las entradas, a 1e-12; las salidas comunes, como
    `tarifa_extrema.compara_referencia`."""
    malas = []
    peor = 0.0
    for nombre, v in zip(comun.NOMBRES, np.asarray(x, dtype=float)):
        ref = float(fila_gsa[nombre])
        if not abs(ref - float(v)) <= 1e-12:
            malas.append((nombre, ref, float(v)))
    for col, txt in fila_gsa.items():
        if col not in out or col in comun.NOMBRES:
            continue
        if txt is None or txt == "":
            malas.append((col, float("nan"), float(out[col])))
            continue
        ref = float(txt)
        dif = abs(float(out[col]) - ref)
        tol = min(max(1e-6 * abs(ref), 1e-9), 0.5)
        peor = max(peor, dif if math.isfinite(dif) else math.inf)
        if not (math.isfinite(dif) and dif <= tol):
            malas.append((col, ref, float(out[col])))
    return peor, malas


# ── El pool ────────────────────────────────────────────────────────────────
def _inicia(datos, dia):
    from gsa_directo import evaluador
    evaluador.inicia_proceso()
    comun.salida_utf8()
    _EST["datos"] = datos
    _EST["dia"] = dia


def _tarea(args):
    caso, idx, fila, bloque, x = args
    from gsa_directo import evaluador
    if caso not in _EST:
        _EST[caso] = evaluador.prepara_caso(caso, _EST["datos"],
                                            dia=_EST["dia"])
    ins = _EST[caso]
    t0 = time.time()
    try:
        with evaluador._silencio(True):
            out, cr, nuevos = evaluador._evalua_todo(ins, x, 1.0, None, 1.0)
        ben = beneficios(cr, nuevos)
        comprueba_suma(out, ben)
        pa = {e: np.asarray(v, dtype=float).copy()
              for e, v in cr.net_benefit_per_agent.items()}
        pa.update({k: np.asarray(v, dtype=float).copy()
                   for k, v in nuevos.items()})
        net = {e: float(v) for e, v in cr.net_benefit.items()}
    except ValueError as exc:
        return (caso, idx, fila, bloque, x, None, None, None, None,
                list(ins.nombres), time.time() - t0, comun.rss_mb(),
                f"{type(exc).__name__}: {exc}".replace("\n", " ")[:400])
    return (caso, idx, fila, bloque, x, out, ben,
            pa if fila == "base" else None, net if fila == "base" else None,
            list(ins.nombres), time.time() - t0, comun.rss_mb(), "")


def corre_pool(ex, tareas, al_terminar, procesos, tope_total=0.0,
               t_inicio=None) -> tuple:
    """Somete `tareas` en orden con una ventana acotada (CAL-43e: nunca todas
    de golpe) y llama a `al_terminar` con cada resultado. Con `tope_total`
    (s, desde `t_inicio`) deja de someter. Devuelve (sometidas, cortado)."""
    t_inicio = time.time() if t_inicio is None else t_inicio
    ventana = max(2, 4 * int(procesos))
    cola = iter(tareas)
    vuelo = set()
    sometidas = 0
    cortado = False

    def llena():
        nonlocal sometidas, cortado
        while len(vuelo) < ventana:
            if tope_total and time.time() - t_inicio > tope_total:
                cortado = True
                return
            try:
                t = next(cola)
            except StopIteration:
                return
            vuelo.add(ex.submit(_tarea, t))
            sometidas += 1

    llena()
    parar = False
    while vuelo:
        listos, _ = wait(vuelo, return_when=FIRST_COMPLETED)
        for fu in listos:
            vuelo.discard(fu)
            if al_terminar(fu.result()) == "parar":
                parar = True
        if parar:
            # Las que ya estan en vuelo terminan; no se somete ninguna mas.
            cortado = True
            continue
        if not cortado:
            llena()
    if not cortado:
        try:
            next(cola)
            cortado = True
        except StopIteration:
            pass
    return sometidas, cortado


# ── El CSV ─────────────────────────────────────────────────────────────────
def _txt(v):
    if isinstance(v, float):
        return repr(v)
    return v


def lee_puntos(ruta: Path) -> list:
    if not ruta.exists():
        return []
    with open(ruta, newline="", encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    cols = columnas()
    # Una fila truncada por un corte trae None en las columnas que faltan, y
    # una con columnas de mas, la clave None: las dos se descartan.
    return [f for f in filas if None not in f
            and all(f.get(c) is not None for c in cols) and f.get("caso")]


# ── El resumen ─────────────────────────────────────────────────────────────
def _num(v):
    return float(v) if v not in (None, "") else float("nan")


def resume_caso(caso: str, filas: list) -> dict:
    """Una fila de `equidad_resumen.csv` con las filas de un caso."""
    base = [f for f in filas if f["fila"] == "base" and not f["motivo"]]
    caja = [f for f in filas if f["fila"] in ("A", "B")]
    buenas = [f for f in caja if not f["motivo"]]
    r = dict(caso=caso, n_puntos=len(caja), n_buenas=len(buenas),
             n_fallidas=len(caja) - len(buenas))
    b = base[0] if base else None
    for mec in MECANISMOS:
        g = np.array([_num(f[f"gini_{mec}"]) for f in buenas])
        r[f"gini_{mec}_base"] = _num(b[f"gini_{mec}"]) if b else float("nan")
        if g.size:
            r[f"gini_{mec}_min"] = float(g.min())
            r[f"gini_{mec}_p05"] = float(np.percentile(g, 5))
            r[f"gini_{mec}_p50"] = float(np.percentile(g, 50))
            r[f"gini_{mec}_p95"] = float(np.percentile(g, 95))
            r[f"gini_{mec}_max"] = float(g.max())
    for p, (a, c) in PARES.items():
        n = len(buenas)
        dom = sum(int(f[f"domina_{p}"]) for f in buenas)
        cam = sum(int(f[f"cambia_{p}"]) for f in buenas if f[f"cambia_{p}"]
                  != "")
        lo, hi = wilson(dom, n)
        r[f"clase_{p}_base"] = b[f"clase_{p}"] if b else ""
        r[f"domina_{p}_n"] = dom
        r[f"domina_{p}_frac"] = dom / n if n else float("nan")
        r[f"domina_{p}_wilson_bajo"] = lo
        r[f"domina_{p}_wilson_alto"] = hi
        r[f"cambia_{p}_n"] = cam
        r[f"W_{a}_menor_W_{c}_n"] = sum(
            1 for f in buenas if _num(f[f"W_{a}"]) < _num(f[f"W_{c}"]))
        r[f"gini_{a}_mayor_{c}_n"] = sum(
            1 for f in buenas if _num(f[f"gini_{a}"]) - _num(f[f"gini_{c}"])
            > 1e-9)
        for cl in ("P2P domina", "intercambio", "C4 domina", "otro"):
            r[f"clase_{p}_{cl.replace(' ', '_')}_n"] = sum(
                1 for f in buenas if f[f"clase_{p}"] == cl)
    difs = [_num(f["gsa_dif_max"]) for f in buenas if f["gsa_dif_max"] != ""]
    r["gsa_comprobados"] = len(difs)
    r["gsa_dif_max"] = max(difs) if difs else float("nan")
    return r


def texto_resumen(resumenes: list, control: dict, fallos: list,
                  dia, rojo_gsa: list) -> str:
    l = ["", "  LA EQUIDAD DENTRO DE LA CAJA DEL GSA (EQ): el Gini del "
         "beneficio por institucion", "  (core.settlement.gini_index, C-214) "
         "en las filas A y B de la muestra de Saltelli del GSA", ""]
    for r in resumenes:
        l.append(f"  {r['caso']}: {r['n_buenas']} puntos buenos de "
                 f"{r['n_puntos']} ({r['n_fallidas']} fallidos); comprobados "
                 f"contra el GSA: {r['gsa_comprobados']} (max |dif| "
                 f"{r['gsa_dif_max']:.3g})")
        l.append(f"    {'mecanismo':<8s} {'base':>7s} {'min':>7s} {'p5':>7s} "
                 f"{'p50':>7s} {'p95':>7s} {'max':>7s}")
        for mec in MECANISMOS:
            if f"gini_{mec}_min" not in r:
                continue
            l.append(f"    {mec:<8s} {r[f'gini_{mec}_base']:7.4f} "
                     f"{r[f'gini_{mec}_min']:7.4f} {r[f'gini_{mec}_p05']:7.4f} "
                     f"{r[f'gini_{mec}_p50']:7.4f} {r[f'gini_{mec}_p95']:7.4f} "
                     f"{r[f'gini_{mec}_max']:7.4f}")
        for p, (a, c) in PARES.items():
            fr = r[f"domina_{p}_frac"]
            l.append(f"    {a} frente a {c}: clase en el punto base "
                     f"«{r[f'clase_{p}_base']}»; domina en {r[f'domina_{p}_n']} "
                     f"de {r['n_buenas']} puntos ("
                     + ("-" if not math.isfinite(fr) else f"{100 * fr:.1f} %")
                     + f", Wilson 95 % [{100 * r[f'domina_{p}_wilson_bajo']:.1f}; "
                     f"{100 * r[f'domina_{p}_wilson_alto']:.1f}]); cambia la "
                     f"clase del punto base en {r[f'cambia_{p}_n']}; W_{a} < "
                     f"W_{c} en {r[f'W_{a}_menor_W_{c}_n']}; Gini de {a} mayor "
                     f"en {r[f'gini_{a}_mayor_{c}_n']}")
        l.append("")
    l.append("  CONTROL DEL PUNTO BASE: " + ", ".join(
        f"{c} {v}" for c, v in control.items()))
    if rojo_gsa:
        l.append(f"  CONTROL CONTRA EL GSA EN ROJO en {len(rojo_gsa)} puntos; "
                 f"el primero: {rojo_gsa[0]}")
    if dia:
        l.append(f"  HUMO DE UN DIA ({dia}): sin control contra el canon; "
                 f"estas cifras no son resultados")
    if fallos:
        l.append(f"  EVALUACIONES FALLIDAS: {len(fallos)}")
        for c, i, m in fallos[:20]:
            l.append(f"    {c} idx {i}: {m[:200]}")
    l.append("")
    return "\n".join(l)


def escribe_resumen(ruta: Path, resumenes: list) -> None:
    campos = []
    for r in resumenes:
        for k in r:
            if k not in campos:
                campos.append(k)
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        for r in resumenes:
            w.writerow({k: _txt(v) for k, v in r.items()})


# ── La orden ───────────────────────────────────────────────────────────────
def ejecuta(argv=None) -> int:
    comun.salida_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--matriz", default=None,
                    help="la matriz por reposo del canon (OBLIGATORIA salvo "
                         "con --dia)")
    ap.add_argument("--referencia-base", default=None)
    ap.add_argument("--referencia-gsa", default=None,
                    help="carpeta del GSA con H1: cada punto se compara con "
                         "su fila del CSV de muestras")
    ap.add_argument("--casos", nargs="+", default=list(comun.CASOS_SOBOL))
    ap.add_argument("--n-base", type=int, default=N_BASE)
    ap.add_argument("--max-puntos", type=int, default=0,
                    help="solo los primeros K puntos por caso (humo)")
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--salida-dir", default=str(comun.RAIZ / "SALIDAS_SERVIDOR"
                                                / "equidad_caja"))
    ap.add_argument("--sin-escribir", action="store_true")
    ap.add_argument("--reanudar", action="store_true")
    ap.add_argument("--tope-total", type=float, default=0.0,
                    help="(s) de sometimiento de la caja; 0 = sin tope")
    ap.add_argument("--sin-huella-canon", action="store_true")
    ap.add_argument("--permite-omitir", action="store_true")
    ap.add_argument("--dia", default=None)
    ap.add_argument("--mte-root", default=None)
    ap.add_argument("--cache", default=None)
    args = ap.parse_args(argv)

    malos = [c for c in args.casos if c not in comun.CASOS]
    if malos:
        print(f"  casos desconocidos: {malos}")
        return 2
    fuera = [c for c in args.casos if c in comun.SOLO_DETERMINISTAS]
    if fuera:
        print(f"  {fuera}: fuera de la caja, como en el GSA (CV2 no corre el "
              f"Sobol, comun.SOLO_DETERMINISTAS)")
        return 2
    if args.n_base < 1 or args.procesos < 1:
        print("  --n-base y --procesos tienen que ser positivos")
        return 2
    if args.dia and (args.referencia_gsa or args.referencia_base):
        print("  --dia es un humo sin controles: no se combina con las "
              "referencias")
        return 2
    from gsa_directo import tarifa_extrema as TE
    matriz = None
    if args.dia is None:
        if not args.matriz:
            print("  --matriz es obligatoria (el control del punto base "
                  "contra el canon); solo --dia la omite")
            return 2
        matriz = Path(args.matriz)
        if not matriz.is_absolute():
            matriz = comun.RAIZ / matriz
        if not args.sin_huella_canon:
            from gsa_directo.compuerta_punto_base import (HUELLAS_CANON,
                                                          huella_libro)
            ajenos = []
            for c in args.casos:
                try:
                    if huella_libro(matriz / c) != HUELLAS_CANON.get(c):
                        ajenos.append(c)
                except OSError as exc:
                    print(f"  CANON ILEGIBLE en {c}: {exc}")
                    return 2
            if ajenos:
                print(f"  LA MATRIZ NO ES LA DEL CANON 2026-09: "
                      f"{' '.join(ajenos)}")
                return 2
    ref = None
    if args.referencia_base:
        ref = TE.lee_referencia(Path(args.referencia_base))
        faltan = [c for c in args.casos if c not in ref]
        if faltan:
            print(f"  {args.referencia_base} no trae {faltan}")
            return 2

    puntos = puntos_caja(args.n_base)
    if args.max_puntos:
        puntos = puntos[:args.max_puntos]
    gsa = {}
    if args.referencia_gsa:
        dg = Path(args.referencia_gsa)
        if not dg.is_absolute():
            dg = comun.RAIZ / dg
        for c in args.casos:
            try:
                gsa[c] = lee_gsa(dg, c, [p[0] for p in puntos])
            except (OSError, ValueError) as exc:
                print(f"  REFERENCIA DEL GSA ILEGIBLE en {c}: {exc}")
                return 2

    salida = Path(args.salida_dir)
    ruta_p = salida / NOMBRE_PUNTOS
    hechos = set()
    previas = []
    if not args.sin_escribir:
        previas = lee_puntos(ruta_p)
        if previas and not args.reanudar:
            print(f"  {ruta_p} ya tiene {len(previas)} filas: --reanudar sigue "
                  f"donde quedo, u otra --salida-dir")
            return 2
        hechos = {(f["caso"], int(f["idx"])) for f in previas
                  if f["fila"] in ("A", "B")}

    from gsa_directo import evaluador
    cache = (Path(args.cache) if args.cache else
             None if args.sin_escribir else salida / "cache")
    print("=" * 70)
    print("LA EQUIDAD DENTRO DE LA CAJA DEL GSA (EQ)")
    print("=" * 70)
    print(f"  casos    {' '.join(args.casos)}")
    print(f"  puntos   {len(puntos)} por caso: filas A y B de los "
          f"{args.n_base} primeros bloques de la muestra del GSA (semilla "
          f"{comun.SEMILLA})" + (f", recortados a {args.max_puntos}"
                                 if args.max_puntos else ""))
    print(f"  control  punto base contra "
          + ("NADA (humo de un dia)" if args.dia else
             f"{matriz}" + (f" y {args.referencia_base}" if ref else ""))
          + (f"; cada punto contra el GSA de {args.referencia_gsa}"
             if gsa else "; SIN comparar los puntos con el GSA"))
    print(f"  procesos {args.procesos}"
          + (f"; tope de sometimiento {args.tope_total:.0f} s"
             if args.tope_total else ""))
    if hechos:
        print(f"  reanuda: {len(hechos)} puntos ya escritos")
    t0 = time.time()
    datos = evaluador.carga_mte(args.mte_root, cache)

    base_res = {}
    filas_nuevas = []
    fallos = []
    rojo_gsa = []
    control = {}
    rojo = []
    escritor = {"fh": None, "w": None, "n": 0}
    cols = columnas()

    def abre():
        if args.sin_escribir or escritor["fh"] is not None:
            return
        salida.mkdir(parents=True, exist_ok=True)
        nuevo = not ruta_p.exists() or ruta_p.stat().st_size == 0
        escritor["fh"] = open(ruta_p, "a", newline="", encoding="utf-8")
        escritor["w"] = csv.DictWriter(escritor["fh"], fieldnames=cols)
        if nuevo:
            escritor["w"].writeheader()

    def escribe(f):
        filas_nuevas.append(f)
        if args.sin_escribir:
            return
        abre()
        escritor["w"].writerow({c: _txt(f.get(c, "")) for c in cols})
        escritor["n"] += 1
        escritor["fh"].flush()
        if escritor["n"] % 50 == 0:
            os.fsync(escritor["fh"].fileno())

    def al_base(r):
        base_res[r[0]] = r

    def al_punto(r):
        caso, idx, fila, bloque, x, out, ben, _pa, _net, nom, s, rss, m = r
        if out is None:
            fallos.append((caso, idx, m))
            f = dict(caso=caso, idx=idx, fila=fila, bloque=bloque,
                     seg=round(s, 3), rss_mb=rss, motivo=m)
            for nombre, v in zip(comun.NOMBRES, x):
                f[nombre] = float(v)
            escribe(f)
            return
        f = fila_punto(caso, idx, fila, bloque, x, out, ben, nom,
                       base_metr[caso])
        f["gsa_dif_max"] = ""
        if caso in gsa:
            peor, malas = compara_gsa(out, x, gsa[caso][idx])
            f["gsa_dif_max"] = peor
            if malas:
                rojo_gsa.append((caso, idx, malas[:3]))
                print(f"    DIFIERE DEL GSA {caso} idx {idx}: {malas[:3]}",
                      flush=True)
        f.update(seg=round(s, 3), rss_mb=rss, motivo="")
        escribe(f)
        if len(rojo_gsa) >= MAX_ROJOS_GSA:
            # Si el evaluador o la caja no son los del GSA, lo seran en todos
            # los puntos: se deja de someter en vez de gastar la noche.
            return "parar"
        return None

    base_metr = {}
    with ProcessPoolExecutor(max_workers=args.procesos, initializer=_inicia,
                             initargs=(datos, args.dia)) as ex:
        # ── 1. el punto base, antes de la caja ───────────────────────────
        tareas_base = [(c, -1, "base", -1, comun.PUNTO_BASE.copy())
                       for c in args.casos]
        corre_pool(ex, tareas_base, al_base, args.procesos)
        for c in args.casos:
            (_c, _i, _f, _b, x, out, ben, pa, net, nom, s, rss,
             m) = base_res[c]
            if out is None:
                control[c] = f"FALLA: {m}"
                rojo.append((c, "evaluacion", m))
                continue
            base_metr[c] = metricas(ben)
            if args.dia:
                control[c] = "sin control (humo de un dia)"
            else:
                malas = TE.control_canon(matriz, c, out, pa, net, nom,
                                         args.permite_omitir,
                                         not args.sin_huella_canon)
                if ref is not None:
                    malas += [(c, f"punto_base {col}", r_, v, d, t, False)
                              for col, r_, v, d, t
                              in TE.compara_referencia(out, ref[c])]
                if malas:
                    control[c] = f"DIFIERE en {len(malas)}"
                    for f_ in malas[:20]:
                        print(f"      DIFIERE {c} {f_[1]}: canon {f_[2]!r} "
                              f"evaluado {f_[3]!r} |dif| {f_[4]:.3g} > "
                              f"{f_[5]:.3g}", flush=True)
                    rojo.extend((c, f_[1], "") for f_ in malas)
                else:
                    control[c] = "al peso"
            print(f"  control {c:<5} punto base: {control[c]}; clase P2P-C4 "
                  + (f"«{base_metr[c]['C']['P2P_C4']}», P2Pcom-C4 "
                     f"«{base_metr[c]['C']['P2Pcom_C4']}»"
                     if c in base_metr else "-"), flush=True)
        if rojo:
            print(f"EQUIDAD EN LA CAJA: CONTROL DEL PUNTO BASE EN ROJO en "
                  f"{len({r[0] for r in rojo})} casos; no se corre la caja y "
                  f"NINGUNA cifra vale")
            return 1
        ya_base = {f["caso"] for f in previas if f["fila"] == "base"}
        for c in args.casos:
            if c in ya_base:
                continue
            (_c, _i, _f, _b, x, out, ben, _pa, _net, nom, s, rss,
             _m) = base_res[c]
            fb = fila_punto(c, -1, "base", -1, x, out, ben, nom, None)
            fb.update(gsa_dif_max="", seg=round(s, 3), rss_mb=rss, motivo="")
            escribe(fb)
        # ── 2. la caja ───────────────────────────────────────────────────
        tareas = [(c, i, fila, b, x) for c in args.casos
                  for (i, fila, b, x) in puntos if (c, i) not in hechos]
        print(f"  {len(tareas)} puntos por evaluar", flush=True)
        t_caja = time.time()
        _som, cortado = corre_pool(ex, tareas, al_punto, args.procesos,
                                   args.tope_total, t_caja)
    if escritor["fh"] is not None:
        escritor["fh"].flush()
        os.fsync(escritor["fh"].fileno())
        escritor["fh"].close()
    print(f"  {len(filas_nuevas)} filas nuevas en {time.time() - t0:.0f} s",
          flush=True)

    todas = (lee_puntos(ruta_p) if not args.sin_escribir
             else [{c: _txt(f.get(c, "")) for c in cols}
                   for f in filas_nuevas])
    todas = [{k: ("" if v is None else str(v)) for k, v in f.items()}
             for f in todas]
    resumenes = [resume_caso(c, [f for f in todas if f["caso"] == c])
                 for c in args.casos]
    txt = texto_resumen(resumenes, control, fallos, args.dia, rojo_gsa)
    print(txt)
    if not args.sin_escribir:
        escribe_resumen(salida / NOMBRE_RESUMEN, resumenes)
        (salida / "resumen.txt").write_text(txt, encoding="utf-8")
        print(f"  escrito {salida}/{NOMBRE_PUNTOS}, {NOMBRE_RESUMEN} y "
              f"resumen.txt")
    if rojo_gsa:
        print(f"EQUIDAD EN LA CAJA: {len(rojo_gsa)} PUNTOS DIFIEREN DEL GSA: "
              f"el evaluador o la caja no son los del canon; NINGUNA cifra "
              f"vale")
        return 1
    if cortado:
        print("EQUIDAD EN LA CAJA INCOMPLETA: el tope de sometimiento dejo "
              "puntos sin correr; --reanudar sigue donde quedo")
        return 4
    if fallos:
        print(f"EQUIDAD EN LA CAJA TERMINADA CON {len(fallos)} EVALUACIONES "
              f"FALLIDAS (con su motivo)")
        return 3
    print("EQUIDAD EN LA CAJA TERMINADA: control "
          + ("sin comprobar (humo de un dia)" if args.dia
             else "del punto base AL PESO")
          + (f"; los {sum(r['gsa_comprobados'] for r in resumenes)} puntos "
             f"iguales a los del GSA" if gsa else ""))
    return 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    sys.exit(ejecuta())
