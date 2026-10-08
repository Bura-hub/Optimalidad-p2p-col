"""El lado derecho del arnes con precios extremos, al bit (DX, M-A2X).

Actividades 1.1 y 4.1. Lo que hace creible la medicion de la dinamica con
precios extremos, en dos partes, las dos AL BIT:

  1. CON LOS FACTORES EN 1, la carga con precios (`arnes.hora_de(caso, fecha,
     precios={"f_bolsa": 1, "f_tarifa": 1})`, que pasa por la multiplicacion
     de `paso_a_paso.carga`) da exactamente las mismas entradas de la hora que
     la carga de siempre, la de la matriz y de M-A2 (todas las claves, con
     `np.array_equal`), y el lado derecho que se integra (`arnes.construye`,
     con la variante de M-A2, V3a k = 1 000, y sin variante) da la misma
     salida en el arranque y en 2·n + 1 estados perturbados por bloque. Son
     las horas del paso 2/6 de `validacion_ampliada` (las cuatro de siempre y
     las dos de SINU e I1).
  2. CON LOS FACTORES DE CADA FAMILIA, el lado derecho del arnes frente al del
     motor (`arnes.comprueba_contra_el_motor`) en las diez ramas de
     `arnes.ramas`, igual que el paso 2/6, en horas escogidas por
     `selecciona_extrema.py` (la primera de cada regimen en E0 y en E4, de
     `--horas`).

Sale con 0 si todo coincide al bit y con 1 si algo difiere o no se pudo
comprobar. Solo lee; no escribe nada.

    python -u reformateo/documento/scripts/sonda/consenso/lado_derecho_extremo.py \\
        --horas SALIDAS_SERVIDOR/dinamica_extrema
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import numpy as np                                   # noqa: E402
import arnes as A                                    # noqa: E402
import medicion_extrema as MX                        # noqa: E402

# Las del paso 2/6 de `validacion_ampliada` (run_servidor.sh).
HORAS_PASO_2 = (("E0", "2025-05-09 13:00"), ("E0", "2025-05-10 10:00"),
                ("K1", "2025-05-11 08:00"), ("E4", "2025-05-07 07:00"),
                ("SINU", "2025-09-07 13:00"), ("I1", "2025-10-01 13:00"))
NEUTRO = {"f_bolsa": 1.0, "f_tarifa": 1.0}
VARIANTES = (("sin variante", {}),
             ("V3a k1000", dict(mu_ent=MX.MU, k_lento=MX.K)))


def iguales(a, b) -> bool:
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return bool(np.array_equal(np.asarray(a), np.asarray(b)))
    return a == b


def neutra(caso, fecha, n=20, semilla=1) -> list:
    """[(que, ok, detalle)] de la parte 1 en una hora."""
    e1 = A.hora_de(caso, fecha)
    e2 = A.hora_de(caso, fecha, precios=dict(NEUTRO))
    fuera = []
    malas = sorted(k for k in set(e1) | set(e2)
                   if k not in e1 or k not in e2 or not iguales(e1[k], e2[k]))
    fuera.append(("entradas", not malas, f"difieren {malas}" if malas else
                  f"{len(e1)} claves iguales"))
    for rot, var in VARIANTES:
        f1, X1, ix = A.construye(e1, **var)
        f2, X2, _ = A.construye(e2, **var)
        ok = bool(np.array_equal(X1, X2))
        rng = np.random.default_rng(semilla)
        tramos = A.bloques(ix["I"], ix["J"], X1.size)
        cargado = A.estado_cargado(X1, ix["I"], ix["J"], rng)
        estados = ([X1] + [A.perturba(X1, tramos, rng, 0.05) for _ in range(n)]
                   + [cargado]
                   + [A.perturba(cargado, tramos, rng, 0.05)
                      for _ in range(n)])
        peor = 0.0
        for X in estados:
            a, b = np.asarray(f1(0.0, X)), np.asarray(f2(0.0, X))
            if not np.array_equal(a, b):
                ok = False
                peor = max(peor, float(np.max(np.abs(a - b))))
        fuera.append((f"lado derecho {rot}", ok,
                      f"{len(estados)} estados" + ("" if ok
                                                   else f", |dif| {peor:.2e}")))
    return fuera


def horas_extremas(dir_horas: Path, familias, casos=("E0", "E4")) -> list:
    """[(caso, familia, fecha, regimen)]: la primera hora de cada regimen de
    la seleccion en cada caso pedido."""
    fuera = []
    for fam in familias:
        for caso in casos:
            ruta = dir_horas / f"horas_{MX.clave_horas(caso, fam)}.json"
            if not ruta.is_file():
                raise FileNotFoundError(f"falta {ruta}: corre antes "
                                        f"selecciona_extrema.py")
            d = json.loads(ruta.read_text(encoding="utf-8"))
            for reg, lista in d["por_regimen"].items():
                if lista:
                    fuera.append((caso, fam, lista[0]["fecha"], reg))
    return fuera


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horas", required=True,
                    help="carpeta con los horas_<caso>__<familia>.json")
    ap.add_argument("--familias", nargs="+", default=list(MX.FAMILIAS))
    ap.add_argument("--casos-extremos", nargs="+", default=["E0", "E4"])
    ap.add_argument("--solo-neutra", action="store_true")
    ap.add_argument("pares", nargs="*",
                    help="pares caso fecha para la parte 1 (por defecto, las "
                         "seis del paso 2/6)")
    args = ap.parse_args(argv)
    if len(args.pares) % 2:
        print("  los pares van de dos en dos: caso y fecha")
        return 2
    pares = ([(args.pares[k], args.pares[k + 1])
              for k in range(0, len(args.pares), 2)] or list(HORAS_PASO_2))
    malas = 0
    print("1. Con los factores en 1: la hora y el lado derecho, al bit, "
          "frente a la carga de siempre", flush=True)
    for caso, fecha in pares:
        for que, ok, det in neutra(caso, fecha):
            malas += int(not ok)
            print(f"  {caso} {fecha} {que:<26s} "
                  f"{'IDENTICO' if ok else 'DIFIERE'} ({det})", flush=True)
    if not args.solo_neutra:
        print("2. Con los factores de cada familia: el lado derecho del arnes "
              "frente al del motor, en las diez ramas", flush=True)
        todos = {n for n, _ in A.bloques(1, 1)}
        try:
            horas = horas_extremas(Path(args.horas), args.familias,
                                   tuple(args.casos_extremos))
        except FileNotFoundError as exc:
            print(f"  NO SE PUEDE COMPROBAR: {exc}", flush=True)
            return 1
        if not horas:
            print("  NO HAY HORAS que comprobar en la seleccion", flush=True)
            return 1
        for caso, fam, fecha, reg in horas:
            e = A.hora_de(caso, fecha, precios=MX.precios_de(fam, caso))
            try:
                lista = A.ramas(e)
            except ValueError as exc:
                print(f"  {caso} {fam} {fecha} ({reg}): NO SE PUEDE COMPROBAR: "
                      f"{exc}", flush=True)
                malas += 1
                continue
            for rot, kw in lista:
                r = A.comprueba_contra_el_motor(e, **kw)
                faltan = sorted(todos - set(r["bloques_ejercidos"]))
                ok = r["identico"] and not faltan
                malas += int(not ok)
                print(f"  {caso} {fam:<11s} {fecha} {reg:<18s} {rot} "
                      f"{'IDENTICO' if r['identico'] else 'DIFIERE'} "
                      f"|dif|={r['dif_abs']:.1e}"
                      f"{' SIN EJERCER ' + str(faltan) if faltan else ''}",
                      flush=True)
    if malas:
        print(f"  EL LADO DERECHO DE LA DINAMICA EXTREMA DIFIERE, o no se pudo "
              f"comprobar, en {malas} comprobaciones", flush=True)
        return 1
    print("  el lado derecho de la dinamica extrema es el de siempre con los "
          "factores en 1 y el del motor con los factores, al bit", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
