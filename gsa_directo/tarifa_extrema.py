"""La tarifa (CU) en niveles extremos: contrastes deterministas fuera de la caja
del Sobol (B5, 2026-10-06).

Actividad 4.1. La propuesta pide variar «el precio de bolsa o de red hasta
niveles extremos». El GSA directo movio la tarifa solo entre 0,9 y 1,1
(`f_tarifa`, CANON §13.2). Aqui, en los trece casos y con las otras cinco
entradas en 1, `f_tarifa` toma 0,5, 0,75, 1, 1,5 y 2.

EL MISMO EVALUADOR. `evaluador.evalua_detalle` acepta cualquier punto: la caja
(`comun.SOPORTES`) solo la usa la muestra de Saltelli. `f_tarifa` escala el
techo (N, T) de cada comprador y el escalar comunitario (apartado 4 del
diseno). Del techo cuelgan el piso de permuta del vendedor (art. 25: tarifa
menos la deduccion), el limite economico de generacion, el mercado entero y la
liquidacion de los ocho escenarios, de C2 como PPA, del P2P colectivo y de H1.
La bolsa, el Cv y los peajes no se mueven.

EL CONTROL, f = 1. Tiene que reproducir el canon AL PESO:
  - contra la matriz del canon (`--matriz`, OBLIGATORIA salvo con `--dia`):
    la misma comparacion que `compuerta_punto_base.py` (hojas Resumen y
    Por_agente, energia, parte del vendedor, horas cuantales, retiros y H1),
    importada tal cual, con las huellas de los libros comprobadas antes;
  - y, con `--referencia-base`, contra el `punto_base.csv` que la compuerta
    acaba de escribir, columna por columna (incluidos C2 como PPA, el P2P
    colectivo y las brechas por institucion), al peso.
  Si el control no esta en verde, sale con 1: ninguna cifra extrema valdria.

LAS BRECHAS QUE SE MIDEN (la comunidad), en cada caso y factor, con su signo
y si cambia frente a f = 1:
  P2P - C1          `P2P_menos_C1` (el margen propio del mercado, H-70)
  P2P - C4          `P2P_menos_C4`
  P2P colectivo - C4  `P2Pcom_menos_C4` (el P2P colectivo citable, §14.23)
  C1 - C4           -`C4_menos_C1`
  C2 - C1           `C2ppa_menos_C1`: el C2 de la PROPUESTA es el PPA
                    (§14.22); la columna `C2` del motor es el contrato
                    interno de CAL-52 (identico a P2P en el agregado) y solo
                    se guarda como identidad.
Y por institucion, los pares institucion-caso frente a C4: P2P, P2P
colectivo, C2 (PPA) y C1 menos C4, con su signo y si cambia frente a f = 1.

UNA EVALUACION QUE FALLA no se imputa: el evaluador falla en voz alta (piso
negativo en una hora-vendedor, salida no finita, hora sin resolver) y aqui se
anota con su motivo. Con f_tarifa = 0,5 puede pasar que la tarifa quede por
debajo de la deduccion del art. 25 en alguna hora-vendedor: eso es un
resultado (el credito de permuta neto se vuelve negativo) y se lee como tal.
Por eso, en cada caso se calcula tambien EL MENOR f_tarifa CON EL PISO NO
NEGATIVO (`umbral_piso`, biseccion sobre la receta del piso del evaluador,
sin mercado), y donde un factor pedido cae por debajo se anade una fila en
ese umbral redondeado hacia arriba a la centesima (`extra_umbral` = 1): la
tarifa mas baja que el modelo puede evaluar. `--sin-umbral` no la anade.
Sale con 3 si alguna evaluacion extrema fallo y el control esta en verde.

    python -u gsa_directo/tarifa_extrema.py \\
        --matriz SALIDAS_SERVIDOR/matriz_reposo \\
        --referencia-base SALIDAS_SERVIDOR/tarifa_extrema/base/punto_base.csv \\
        --salida-dir SALIDAS_SERVIDOR/tarifa_extrema --procesos 16

    python -u gsa_directo/tarifa_extrema.py --dia 2025-05-09 --casos E0 E4 \\
        --sin-escribir --procesos 2          # humo de un dia, sin control

Escribe en `--salida-dir`: `tarifa_extrema_comunidad.csv` (una fila por caso
y factor), `tarifa_extrema_instituciones.csv` (una por caso, factor,
institucion y brecha) y `resumen.txt`.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from gsa_directo import comun  # noqa: E402

FACTORES = (0.5, 0.75, 1.0, 1.5, 2.0)
I_TARIFA = comun.NOMBRES.index("f_tarifa")
# Las cinco brechas de comunidad pedidas: nombre -> (columna, signo).
BRECHAS = {
    "P2P_menos_C1": ("P2P_menos_C1", 1.0),
    "P2P_menos_C4": ("P2P_menos_C4", 1.0),
    "P2Pcom_menos_C4": ("P2Pcom_menos_C4", 1.0),
    "C1_menos_C4": ("C4_menos_C1", -1.0),
    "C2ppa_menos_C1": ("C2ppa_menos_C1", 1.0),
}
ROTULOS = {
    "P2P_menos_C1": "P2P - C1",
    "P2P_menos_C4": "P2P - C4",
    "P2Pcom_menos_C4": "P2P colectivo - C4",
    "C1_menos_C4": "C1 - C4",
    "C2ppa_menos_C1": "C2 (PPA) - C1",
}
# Por institucion, frente a C4: nombre -> (minuendo, sustraendo) del
# beneficio por institucion.
BRECHAS_INST = {
    "P2P_menos_C4": ("P2P", "C4"),
    "P2Pcom_menos_C4": ("P2Pcom", "C4"),
    "C2ppa_menos_C4": ("C2ppa", "C4"),
    "C1_menos_C4": ("C1", "C4"),
}
TOL_SIGNO = 0.5                   # (COP): por debajo de medio peso, «cero»

_EST = {}


def signo(v: float) -> int:
    if not math.isfinite(v):
        raise ValueError(f"brecha no finita: {v!r}")
    return 0 if abs(v) <= TOL_SIGNO else (1 if v > 0 else -1)


def punto(f: float) -> np.ndarray:
    x = comun.PUNTO_BASE.copy()
    x[I_TARIFA] = float(f)
    return x


def _inicia(datos, dia):
    from gsa_directo import evaluador
    evaluador.inicia_proceso()
    comun.salida_utf8()
    _EST["datos"] = datos
    _EST["dia"] = dia


def umbral_piso(ins, lo: float = 0.05, iteraciones: int = 40) -> float:
    """El menor f_tarifa (las demas entradas en 1) con el piso del vendedor
    no negativo en todas las horas-vendedor: por debajo, la tarifa no cubre
    la deduccion del art. 25 en alguna hora de permuta y el evaluador se
    niega a evaluar (piso negativo). Biseccion sobre la MISMA receta del
    evaluador (`deduccion_art25` y `piso_residual`), sin mercado: el piso
    crece con la tarifa. 0 si ni con `lo` hay piso negativo."""
    from gsa_directo import evaluador
    from core.opciones_externas import deduccion_art25, piso_residual

    def negativo(f):
        fa = evaluador.aplica_factores(ins, punto(f))
        ded = deduccion_art25(fa["cvm"], fa["tolls"], ins.cap)
        piso, _ = piso_residual(fa["G"], fa["D"], fa["techo"], ded,
                                fa["bolsa"], ins.mes_m)
        vende = np.maximum(fa["G"] - fa["D"], 0.0) > 1e-9
        return bool((np.asarray(piso)[vende] < 0).any())

    if not negativo(lo):
        return 0.0
    if negativo(1.0):
        return float("nan")             # ni en el punto base: no deberia
    a, b = lo, 1.0                       # negativo(a), no negativo(b)
    for _ in range(iteraciones):
        m = 0.5 * (a + b)
        if negativo(m):
            a = m
        else:
            b = m
    return b


def _tarea(args):
    caso, f = args
    from gsa_directo import evaluador
    if caso not in _EST:
        _EST[caso] = evaluador.prepara_caso(caso, _EST["datos"],
                                            dia=_EST["dia"])
    ins = _EST[caso]
    t0 = time.time()
    umbral = umbral_piso(ins) if f == 1.0 else None
    try:
        # Una sola evaluacion por punto: lo que `evalua_detalle` (los ocho
        # escenarios por institucion) y `evalua_mecanismos_nuevos` (C2ppa,
        # P2Pcom, H1 y H1comp por institucion) devuelven por separado sale de
        # la misma llamada interna.
        with evaluador._silencio(True):
            out, cr, nuevos = evaluador._evalua_todo(ins, punto(f), 1.0,
                                                     None, 1.0)
    except ValueError as exc:
        return caso, f, None, None, None, list(ins.nombres), \
            time.time() - t0, f"{type(exc).__name__}: {exc}"[:400], umbral
    pa = {e: np.asarray(v, dtype=float).copy()
          for e, v in cr.net_benefit_per_agent.items()}
    pa.update({k: np.asarray(v, dtype=float).copy()
               for k, v in nuevos.items()})
    net = {e: float(v) for e, v in cr.net_benefit.items()}
    return (caso, f, out, pa, net, list(ins.nombres), time.time() - t0, "",
            umbral)


def compara_referencia(out: dict, fila_ref: dict) -> list:
    """[(columna, ref, evaluado, |dif|, tol)] de las que difieren mas que
    «al peso» (min(1e-6 relativa, 0,5)) frente al punto_base.csv."""
    malas = []
    for col, txt in fila_ref.items():
        if col in ("caso", "seg") or col not in out:
            continue
        ref = float(txt)
        v = float(out[col])
        tol = min(max(1e-6 * abs(ref), 1e-9), 0.5)
        dif = abs(v - ref)
        if not (math.isfinite(dif) and dif <= tol):
            malas.append((col, ref, v, dif, tol))
    return malas


def lee_referencia(ruta: Path) -> dict:
    with open(ruta, newline="", encoding="utf-8") as fh:
        return {r["caso"]: r for r in csv.DictReader(fh)}


def control_canon(matriz: Path, caso, out, pa, net, nombres,
                  permite_omitir: bool, canon_fijo: bool) -> list:
    """La comparacion de `compuerta_punto_base.compara`, tal cual."""
    from gsa_directo import compuerta_punto_base as CPB
    registros = CPB._registros_de(matriz, None)
    canon = CPB.lee_canon(matriz / caso, nombres, registros, caso,
                          canon_fijo=canon_fijo)
    filas = CPB.compara(caso, out, pa, net, canon, nombres,
                        permite_omitir=permite_omitir,
                        h1_canon=CPB.H1_CANON.get(caso))
    return [f for f in filas if not f[6]]


def ejecuta(argv=None) -> int:
    comun.salida_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--matriz", default=None,
                    help="la matriz por reposo del canon (OBLIGATORIA salvo "
                         "con --dia)")
    ap.add_argument("--referencia-base", default=None,
                    help="punto_base.csv de compuerta_punto_base.py, contra "
                         "el que se compara f = 1 columna por columna")
    ap.add_argument("--factores", nargs="+", type=float,
                    default=list(FACTORES))
    ap.add_argument("--casos", nargs="+", default=list(comun.ORDEN_CASOS))
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--salida-dir", default=str(comun.RAIZ / "SALIDAS_SERVIDOR"
                                                / "tarifa_extrema"))
    ap.add_argument("--sin-escribir", action="store_true")
    ap.add_argument("--sin-huella-canon", action="store_true")
    ap.add_argument("--permite-omitir", action="store_true")
    ap.add_argument("--dia", default=None,
                    help="humo de un dia (replica --day): sin control contra "
                         "el canon")
    ap.add_argument("--mte-root", default=None)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--sin-umbral", action="store_true",
                    help="no anade la fila de la tarifa mas baja evaluable "
                         "donde un factor pedido cae bajo el umbral del piso")
    args = ap.parse_args(argv)

    malos = [c for c in args.casos if c not in comun.CASOS]
    if malos:
        print(f"  casos desconocidos: {malos}")
        return 2
    factores = sorted(set(float(f) for f in args.factores))
    if 1.0 not in factores:
        print("  falta f = 1 en --factores: es el control (y la base del signo)")
        return 2
    if any(not (f > 0 and math.isfinite(f)) for f in factores):
        print(f"  factores no validos: {factores}")
        return 2
    matriz = None
    if args.dia is None:
        if not args.matriz:
            print("  --matriz es obligatoria (el control f = 1 contra el "
                  "canon); solo --dia la omite")
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
        ref = lee_referencia(Path(args.referencia_base))
        faltan = [c for c in args.casos if c not in ref]
        if faltan:
            print(f"  {args.referencia_base} no trae {faltan}")
            return 2

    from gsa_directo import evaluador
    salida = Path(args.salida_dir)
    cache = (Path(args.cache) if args.cache else
             None if args.sin_escribir else salida / "cache")
    print("=" * 70)
    print("TARIFA EN NIVELES EXTREMOS (B5): f_tarifa en "
          f"{', '.join(f'{f:g}' for f in factores)}, el resto en 1")
    print("=" * 70)
    print(f"  casos    {' '.join(args.casos)}")
    print(f"  control  f = 1 contra "
          + ("NADA (humo de un dia)" if args.dia else
             f"{matriz}" + (f" y {args.referencia_base}" if ref else "")))
    print(f"  procesos {args.procesos}")
    t0 = time.time()
    datos = evaluador.carga_mte(args.mte_root, cache)
    trabajos = [(c, f) for c in args.casos for f in factores]
    extra = {}
    with ProcessPoolExecutor(max_workers=args.procesos, initializer=_inicia,
                             initargs=(datos, args.dia)) as ex:
        res = list(ex.map(_tarea, trabajos))
        umbrales = {r[0]: r[8] for r in res if r[1] == 1.0}
        # La tarifa MAS BAJA QUE SE PUEDE EVALUAR, en los casos donde un
        # factor pedido cayo por debajo de su umbral del piso: el umbral
        # redondeado hacia arriba a la centesima. Es una fila mas, rotulada
        # (`extra_umbral`), que no sustituye a la pedida: esa queda como
        # FALLA con su motivo. `--sin-umbral` no la anade.
        if not args.sin_umbral:
            for c, f, out, *_r in res:
                u = umbrales.get(c)
                if (out is None and f < 1.0 and u is not None
                        and math.isfinite(u) and 0.0 < u < 1.0):
                    fu = math.ceil(u * 100.0 - 1e-9) / 100.0
                    if fu not in factores and fu < 1.0:
                        extra[c] = fu
            if extra:
                res += list(ex.map(_tarea, sorted(extra.items())))
    print(f"  {len(trabajos) + len(extra)} evaluaciones en "
          f"{time.time() - t0:.0f} s"
          + (f" ({len(extra)} en la tarifa mas baja evaluable)" if extra
             else ""))
    por = {(c, f): (out, pa, net, nom, s, m)
           for c, f, out, pa, net, nom, s, m, _u in res}

    # ── el control ──────────────────────────────────────────────────────────
    control = {}
    rojo = []
    for c in args.casos:
        out, pa, net, nom, _s, m = por[(c, 1.0)]
        if out is None:
            control[c] = f"FALLA: {m}"
            rojo.append((c, "evaluacion", m))
            continue
        if args.dia:
            control[c] = "sin control (humo de un dia)"
            continue
        malas = control_canon(matriz, c, out, pa, net, nom,
                              args.permite_omitir, not args.sin_huella_canon)
        if ref is not None:
            malas += [(c, f"punto_base {col}", r, v, d, t, False)
                      for col, r, v, d, t in compara_referencia(out, ref[c])]
        if malas:
            control[c] = f"DIFIERE en {len(malas)}"
            for f_ in malas[:20]:
                print(f"      DIFIERE {c} {f_[1]}: canon {f_[2]!r} evaluado "
                      f"{f_[3]!r} |dif| {f_[4]:.3g} > {f_[5]:.3g}")
            rojo.extend((c, f_[1], "") for f_ in malas)
        else:
            control[c] = "al peso"
        print(f"  control {c:<5} f = 1: {control[c]}")

    # ── las filas ───────────────────────────────────────────────────────────
    filas_com, filas_inst, fallos = [], [], []
    for c in args.casos:
        base = por[(c, 1.0)]
        for f in sorted(factores + ([extra[c]] if c in extra else [])):
            es_extra = int(c in extra and f == extra[c])
            out, pa, net, nom, s, m = por[(c, f)]
            fila = dict(caso=c, f_tarifa=f, extra_umbral=es_extra,
                        seg=round(s, 3), motivo=m,
                        control=(control[c] if f == 1.0 else ""),
                        f_tarifa_min_piso=umbrales.get(c))
            if out is None:
                fallos.append((c, f, m))
                filas_com.append(fila)
                continue
            fila.update(out)
            for b, (col, sg) in BRECHAS.items():
                v = sg * float(out[col])
                fila[f"brecha_{b}"] = v
                fila[f"signo_{b}"] = signo(v)
                if base[0] is not None:
                    vb = sg * float(base[0][col])
                    fila[f"base_{b}"] = vb
                    fila[f"cambia_signo_{b}"] = int(signo(v) != signo(vb))
            filas_com.append(fila)
            for n, inst in enumerate(nom):
                for b, (a, z) in BRECHAS_INST.items():
                    v = float(pa[a][n] - pa[z][n])
                    fi = dict(caso=c, f_tarifa=f, extra_umbral=es_extra,
                              institucion=inst, brecha=b,
                              valor=v, signo=signo(v))
                    if base[0] is not None:
                        vb = float(base[1][a][n] - base[1][z][n])
                        fi.update(valor_base=vb, signo_base=signo(vb),
                                  cambia_signo=int(signo(v) != signo(vb)))
                    filas_inst.append(fi)

    txt = resumen(filas_com, filas_inst, factores, args.casos, control,
                  fallos, args.dia, umbrales)
    print(txt)
    if not args.sin_escribir:
        salida.mkdir(parents=True, exist_ok=True)
        escribe_csv(salida / "tarifa_extrema_comunidad.csv", filas_com)
        escribe_csv(salida / "tarifa_extrema_instituciones.csv", filas_inst)
        (salida / "resumen.txt").write_text(txt, encoding="utf-8")
        print(f"  escrito {salida}/tarifa_extrema_comunidad.csv, "
              f"tarifa_extrema_instituciones.csv y resumen.txt")
    if rojo:
        print(f"TARIFA EXTREMA: CONTROL EN ROJO en "
              f"{len({r[0] for r in rojo})} casos; NINGUNA cifra vale")
        return 1
    if fallos:
        print(f"TARIFA EXTREMA TERMINADA CON {len(fallos)} EVALUACIONES "
              f"FALLIDAS (con su motivo); control "
              + ("sin comprobar (humo)" if args.dia else "EN VERDE"))
        return 3
    print("TARIFA EXTREMA TERMINADA: control "
          + ("sin comprobar (humo de un dia)" if args.dia else "EN VERDE, al peso")
          + f"; {len(filas_com)} evaluaciones")
    return 0


def escribe_csv(ruta: Path, filas: list) -> None:
    campos = []
    for f in filas:
        for k in f:
            if k not in campos:
                campos.append(k)
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        for f in filas:
            w.writerow({k: (repr(v) if isinstance(v, float) else v)
                        for k, v in f.items()})


def resumen(filas_com, filas_inst, factores, casos, control, fallos,
            dia, umbrales=None) -> str:
    l = ["", "  BRECHAS DE COMUNIDAD (MCOP) POR CASO Y FACTOR SOBRE LA CU",
         "  (* = cambia de signo frente a f = 1)", ""]
    cab = f"  {'caso':<5} {'f':>5}  " + "  ".join(
        f"{ROTULOS[b]:>18s}" for b in BRECHAS)
    l.append(cab)
    cambios = []
    for fila in filas_com:
        if fila.get("motivo"):
            l.append(f"  {fila['caso']:<5} {fila['f_tarifa']:>5g}  FALLA: "
                     f"{fila['motivo'][:120]}")
            continue
        celdas = []
        for b in BRECHAS:
            v = fila[f"brecha_{b}"] / 1e6
            marca = "*" if fila.get(f"cambia_signo_{b}") else " "
            if marca == "*":
                cambios.append((fila["caso"], fila["f_tarifa"], ROTULOS[b],
                                fila[f"base_{b}"] / 1e6, v))
            celdas.append(f"{v:17.3f}{marca}")
        l.append(f"  {fila['caso']:<5} {fila['f_tarifa']:>5g}  "
                 + "  ".join(celdas)
                 + ("   (la tarifa mas baja evaluable)"
                    if fila.get("extra_umbral") else ""))
    l += ["", f"  CAMBIOS DE SIGNO DE LA COMUNIDAD: {len(cambios)}"]
    for c, f, b, vb, v in cambios:
        l.append(f"    {c} f = {f:g}: {b} pasa de {vb:.3f} a {v:.3f} MCOP")
    l += ["", "  PARES INSTITUCION-CASO FRENTE A C4 (cuantos por debajo de C4; "
          "cambios de signo frente a f = 1)", ""]
    hay_extra = any(x.get("extra_umbral") for x in filas_inst)
    columnas = [(f"f={f:g}", f) for f in factores] + (
        [("f=umbral", None)] if hay_extra else [])
    l.append(f"  {'brecha':<18s} " + " ".join(f"{e:>12s}"
                                               for e, _f in columnas))
    for b in BRECHAS_INST:
        celdas = []
        for _e, f in columnas:
            sel = [x for x in filas_inst if x["brecha"] == b
                   and ((f is None and x.get("extra_umbral"))
                        or (f is not None and not x.get("extra_umbral")
                            and x["f_tarifa"] == f))]
            neg = sum(1 for x in sel if x["signo"] < 0)
            cam = sum(1 for x in sel if x.get("cambia_signo"))
            celdas.append(f"{neg:>3d}/{len(sel):<3d} c{cam:<3d}")
        l.append(f"  {b:<18s} " + " ".join(f"{x:>12s}" for x in celdas))
    l.append("  (n/m cN = n de m pares por debajo de C4; N cambian de signo "
             "frente a f = 1; f=umbral = la tarifa mas baja evaluable de los "
             "casos donde la pedida cae bajo el umbral del piso)")
    cam_inst = [x for x in filas_inst if x.get("cambia_signo")]
    if cam_inst:
        l += ["", "  Los pares que cambian de signo:"]
        for x in cam_inst:
            l.append(f"    {x['caso']:<5} f = {x['f_tarifa']:g} "
                     f"{x['institucion']:<8s} {x['brecha']:<16s} "
                     f"{x['valor_base'] / 1e6:10.3f} -> {x['valor'] / 1e6:10.3f} MCOP")
    if umbrales:
        l += ["", "  EL MENOR f_tarifa CON EL PISO DEL VENDEDOR NO NEGATIVO "
              "(por debajo, la tarifa no cubre la deduccion del art. 25 en "
              "alguna hora de permuta y el evaluador no evalua):"]
        l.append("    " + "  ".join(
            (f"{c} <0,05" if umbrales.get(c) == 0.0 else
             f"{c} {umbrales[c]:.4f}") for c in casos
            if umbrales.get(c) is not None))
    l += ["", "  CONTROL f = 1: " + ", ".join(f"{c} {control[c]}"
                                               for c in casos)]
    if dia:
        l.append(f"  HUMO DE UN DIA ({dia}): sin control contra el canon; "
                 f"estas cifras no son resultados")
    if fallos:
        l += ["", f"  EVALUACIONES FALLIDAS: {len(fallos)}"]
        for c, f, m in fallos:
            l.append(f"    {c} f = {f:g}: {m[:200]}")
    l.append("")
    return "\n".join(l)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    sys.exit(ejecuta())
