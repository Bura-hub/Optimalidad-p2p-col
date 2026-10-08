"""Escoge y comprueba las horas de la dinamica con precios extremos (DX, M-A2X).

Actividades 1.1 y 4.1.

QUE HACE. Para cada caso y familia de precio de `medicion_extrema.py` (la
bolsa x4, la tarifa x0,5 o 0,6 y x2):

  1. corre el MOTOR del evaluador del GSA directo con los factores de esa
     familia (`evaluador._evalua_todo` en el punto de las seis entradas, sin
     cambios: es la misma via, al peso, que la matriz del canon con todos los
     factores en 1, lo que comprueba la compuerta del punto base), y se queda
     con el resultado de cada una de las 6 144 horas (`EMSP2P.run` se
     intercepta, no se reimplementa);
  2. agrupa las horas por el regimen que les da el motor y muestrea, con
     semilla, las de los regimenes pedidos;
  3. COMPRUEBA cada hora con el arnes, cargada con los mismos factores
     (`arnes.hora_de(caso, fecha, precios)`, que pasa por
     `paso_a_paso.carga(factor_bolsa, factor_tarifa)`): el reposo en forma
     cerrada del arnes tiene que dar el mismo regimen que el motor (o su
     regimen cerrado, D71), el mismo piso del juego (1e-6 COP/kWh) y la misma
     energia (1e-6·max(1, E) kWh). Es la comprobacion que `selecciona_horas.py`
     hace contra el almacen, aqui contra el motor con los factores: si no
     coincide, el arnes y el motor no ven la misma hora y la hora no entra.

Escribe un `horas_<caso>__<familia>.json` por caso y familia, con la forma de
`selecciona_horas.py` y la clave `<caso>__<familia>` en `caso`, que es lo que
`medicion_extrema.specs` lee. Sale con 1 si en algun grupo se descarta mas del
30 % de las horas examinadas (el umbral de `selecciona_horas.py`) o si un
regimen pedido queda sin horas en TODOS los casos de una familia; con 2 si una
evaluacion del motor falla (por ejemplo, piso negativo).

    python -u reformateo/documento/scripts/sonda/consenso/selecciona_extrema.py \\
        --salida-dir SALIDAS_SERVIDOR/dinamica_extrema --procesos 16

SOLO ESCRIBE SUS JSON.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import numpy as np                                   # noqa: E402
import arnes as A                                    # noqa: E402
import medicion_extrema as MX                        # noqa: E402
import preparacion as PR                             # noqa: E402

TOL_PISO = 1e-6          # (COP/kWh): arnes y motor en doble precision
TOL_E_REL = 1e-6         # veces max(1, E) (kWh)
DESCARTE_MAXIMO = 0.30   # el de selecciona_horas.py
SIN_MERCADO = ("sin_mercado", "sin_ganancia")

_EST = {}


@contextlib.contextmanager
def captura_motor():
    """Intercepta `EMSP2P.run` para quedarse con los resultados por hora de la
    evaluacion, sin tocar lo que devuelve."""
    from core import ems_p2p
    orig = ems_p2p.EMSP2P.run
    guardado = {}

    def run(self, *a, **k):
        r = orig(self, *a, **k)
        guardado["res"] = r[0]
        return r
    ems_p2p.EMSP2P.run = run
    try:
        yield guardado
    finally:
        ems_p2p.EMSP2P.run = orig


def motor_con_factores(ins, x) -> list:
    """Los resultados por hora del motor del evaluador en el punto x."""
    from gsa_directo import evaluador
    with captura_motor() as g, evaluador._silencio(True):
        evaluador._evalua_todo(ins, x, 1.0, None, 1.0)
    if "res" not in g:
        raise RuntimeError("el evaluador no paso por EMSP2P.run")
    return list(g["res"])


def por_regimen(res) -> dict:
    """{regimen: [(hora, regimen, piso_juego, E)]} de las horas con mercado."""
    fuera = {}
    for r in res:
        reg = str(getattr(r, "regimen", "") or "")
        if not reg or reg in SIN_MERCADO:
            continue
        E = (float(np.sum(r.P_star)) if r.P_star is not None else 0.0)
        fuera.setdefault(reg, []).append((int(r.k), reg,
                                          float(r.piso_juego), E))
    return fuera


def comprueba(caso, familia, fecha, reg_motor, piso_motor, E_motor):
    """(hora buena o None, motivo, texto), como `selecciona_horas.py`."""
    precios = MX.precios_de(familia, caso)
    try:
        e = A.hora_de(caso, fecha, precios=precios)
        r = PR.resuelve(e)
    except Exception as exc:                        # noqa: BLE001
        return (None, f"el arnes no la resuelve ({type(exc).__name__})",
                f"{fecha}: {type(exc).__name__}: {exc}")
    mismo = reg_motor in (r.regimen, getattr(r, "regimen_cerrado", r.regimen))
    dif_piso = abs(float(r.piso) - piso_motor)
    dif_E = abs(float(r.E) - E_motor)
    if not mismo:
        motivo = "otro regimen"
    elif not dif_piso <= TOL_PISO:
        motivo = "otro piso del juego"
    elif not dif_E <= TOL_E_REL * max(1.0, abs(E_motor)):
        motivo = "otra energia"
    else:
        return (dict(fecha=fecha, regimen=r.regimen,
                     regimen_cerrado=getattr(r, "regimen_cerrado", r.regimen),
                     regimen_motor=reg_motor, E=float(r.E),
                     piso=float(r.piso), S=float(r.S),
                     n_soluciones=int(r.n_soluciones), J=len(e["gn"]),
                     I=len(e["dn"]), vendedores=list(e["vend"]),
                     compradores=list(e["comp"]), precios=precios), "", "")
    return (None, motivo,
            f"{fecha} no coincide con el motor: regimen {r.regimen} frente a "
            f"{reg_motor}, piso {float(r.piso):.6f} frente a {piso_motor:.6f}, "
            f"E {float(r.E):.6f} frente a {E_motor:.6f}")


def _inicia(datos):
    from gsa_directo import evaluador, comun
    evaluador.inicia_proceso()
    comun.salida_utf8()
    _EST["datos"] = datos


def selecciona(caso, familia, regimenes, por_reg, semilla, datos=None) -> dict:
    """El JSON de un caso y una familia (sin escribirlo)."""
    from gsa_directo import evaluador
    datos = _EST.get("datos") if datos is None else datos
    clave_ins = ("ins", caso)
    if clave_ins not in _EST:
        _EST[clave_ins] = evaluador.prepara_caso(caso, datos)
    ins = _EST[clave_ins]
    x = MX.punto_gsa(familia, caso)
    t0 = time.time()
    res = motor_con_factores(ins, x)
    t_motor = time.time() - t0
    dat, _mapa = A.carga(caso, MX.precios_de(familia, caso))
    idx = list(dat["idx"])
    if len(idx) != ins.T or len(res) != ins.T:
        raise ValueError(f"{caso} {familia}: el arnes carga {len(idx)} horas, "
                         f"el evaluador {ins.T} y el motor devolvio {len(res)}")
    grupos = por_regimen(res)
    conteo = {g: len(v) for g, v in sorted(grupos.items())}
    rng = np.random.default_rng([int(semilla), MX.CASOS.index(caso),
                                 MX.FAMILIAS.index(familia)])
    sel, examen, avisos, excesivos = {}, {}, [], []
    for g in regimenes:
        cand = grupos.get(g, [])
        if not cand:
            sel[g] = []
            examen[g] = dict(examinadas=0, descartadas=0, motivos={})
            continue
        ancho = min(len(cand), 2 * por_reg)
        elegidas = sorted(rng.choice(len(cand), size=ancho,
                                     replace=False).tolist())
        buenas, motivos = [], {}
        examinadas = 0
        for i in elegidas:
            if len(buenas) >= por_reg:
                break
            h, reg, piso, E = cand[i]
            examinadas += 1
            fecha = A.clave(idx[h])
            b, motivo, texto = comprueba(caso, familia, fecha, reg, piso, E)
            if b is None:
                motivos[motivo] = motivos.get(motivo, 0) + 1
                avisos.append(f"{g}: hora {h} {texto}")
                continue
            b.update(hora=h, grupo=g)
            buenas.append(b)
        desc = examinadas - len(buenas)
        sel[g] = buenas
        examen[g] = dict(examinadas=examinadas, descartadas=desc,
                         motivos=motivos)
        if examinadas and desc / examinadas > DESCARTE_MAXIMO:
            excesivos.append((g, examinadas, desc, motivos))
    return dict(caso=MX.clave_horas(caso, familia), caso_base=caso,
                familia=familia, precios=MX.precios_de(familia, caso),
                punto_gsa=[float(v) for v in x], semilla=int(semilla),
                por_regimen_pedido=int(por_reg), regimenes=list(regimenes),
                horas_por_regimen_motor=conteo, seg_motor=round(t_motor, 2),
                generado=datetime.now().isoformat(timespec="seconds"),
                por_regimen=sel, examen=examen, avisos=avisos,
                excesivos=[list(e) for e in excesivos])


def _tarea(args):
    caso, familia, regimenes, por_reg, semilla = args
    try:
        return caso, familia, selecciona(caso, familia, regimenes, por_reg,
                                         semilla), ""
    except Exception as exc:                        # noqa: BLE001
        # Se anota y se sale con 2 en voz alta: ningun JSON a medias.
        return caso, familia, None, f"{type(exc).__name__}: {exc}"[:400]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--casos", nargs="+", default=list(MX.CASOS))
    ap.add_argument("--familias", nargs="+", default=list(MX.FAMILIAS))
    ap.add_argument("--regimenes", nargs="+", default=list(MX.REGIMENES))
    ap.add_argument("--por-regimen", type=int, default=10,
                    help="horas comprobadas por regimen, caso y familia")
    ap.add_argument("--semilla", type=int, default=1)
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--salida-dir", required=True)
    ap.add_argument("--mte-root", default=None)
    ap.add_argument("--cache", default=None)
    args = ap.parse_args(argv)
    malos = ([c for c in args.casos if c not in MX.CASOS]
             + [f for f in args.familias if f not in MX.FAMILIAS])
    if malos:
        print(f"  casos o familias desconocidos: {malos}")
        return 2
    import medicion_ampliada as MA
    malos = [r for r in args.regimenes if r not in MA.REGIMENES]
    if malos or args.por_regimen < 1:
        print(f"  regimenes desconocidos {malos} o --por-regimen < 1")
        return 2
    from gsa_directo import evaluador
    salida = Path(args.salida_dir)
    t0 = time.time()
    datos = evaluador.carga_mte(args.mte_root,
                                Path(args.cache) if args.cache else None)
    tareas = [(c, f, tuple(args.regimenes), args.por_regimen, args.semilla)
              for f in args.familias for c in args.casos]
    print(f"  seleccion DX: {len(tareas)} pares caso-familia, "
          f"{args.procesos} procesos", flush=True)
    with ProcessPoolExecutor(max_workers=args.procesos, initializer=_inicia,
                             initargs=(datos,)) as ex:
        resultados = list(ex.map(_tarea, tareas))
    codigo = 0
    fallidas = [(c, f, m) for c, f, j, m in resultados if j is None]
    for c, f, m in fallidas:
        print(f"  === FALLA {c} {f}: {m}", flush=True)
    if fallidas:
        print(f"  {len(fallidas)} evaluaciones del motor fallaron: no se "
              f"escribe nada", flush=True)
        return 2
    salida.mkdir(parents=True, exist_ok=True)
    total = {}
    for c, f, j, _m in resultados:
        ruta = salida / f"horas_{MX.clave_horas(c, f)}.json"
        ruta.write_text(json.dumps(j, indent=1), encoding="utf-8")
        n = {g: len(v) for g, v in j["por_regimen"].items()}
        for g, k in n.items():
            total[(f, g)] = total.get((f, g), 0) + k
        print(f"  {c:<5} {f:<12} motor {j['seg_motor']:5.1f} s; "
              + ", ".join(f"{g} {k}/{j['examen'][g]['examinadas']}"
                          for g, k in n.items()), flush=True)
        for e in j["excesivos"]:
            print(f"  === DEMASIADAS HORAS DESCARTADAS en {c} {f} {e[0]}: "
                  f"{e[2]} de {e[1]} ({e[3]})", flush=True)
            codigo = 1
    print("  horas comprobadas por familia y regimen (suma de los casos):",
          flush=True)
    for f in args.familias:
        print(f"    {f:<12} " + ", ".join(
            f"{g} {total.get((f, g), 0)}" for g in args.regimenes), flush=True)
        for g in args.regimenes:
            if total.get((f, g), 0) == 0:
                print(f"  === SIN HORAS: {g} en {f}, en ningun caso",
                      flush=True)
                codigo = 1
    print(f"  escrito {salida}/horas_<caso>__<familia>.json en "
          f"{time.time() - t0:.0f} s", flush=True)
    return codigo


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    raise SystemExit(main())
