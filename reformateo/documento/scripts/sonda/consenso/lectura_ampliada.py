"""La lectura de la validacion ampliada (M-A2), completa o parcial.

Actividades 1.1 y 4.2.

    python -u reformateo/documento/scripts/sonda/consenso/lectura_ampliada.py \\
        SALIDAS_SERVIDOR/validacion_ampliada/m_a2.json [mas JSON] \\
        --horas SALIDAS_SERVIDOR/validacion_ampliada \\
        --salida SALIDAS_SERVIDOR/validacion_ampliada/lectura_m_a2.txt \\
        --csv SALIDAS_SERVIDOR/validacion_ampliada/lectura_m_a2.csv

    python -u .../lectura_ampliada.py --comprueba-canon SALIDAS_SERVIDOR/matriz_reposo

EL CRITERIO NO SE TOCA. El rotulo de cada regimen y familia es el de
`veredicto.py` (`agrupa`, `cuenta_hora` y `rotulo`, importados tal cual): el
95 % o mas de las horas hechas dentro, con cinco como minimo. Esta lectura
anade, sin cambiarlo, lo que hace falta para leer una medicion que no termino:

  - n_plan: las horas que el plan tenia para ese regimen y familia;
  - hechas (n): las que tienen resultado y cuentan (el denominador de
    siempre: dentro + no llega + fuera + falla);
  - omitidas: las que la parada por futilidad no sometio;
  - pendientes: n_plan - hechas - omitidas - apartadas;
  - x de n dentro y el INTERVALO DE WILSON al 95 % de esa fraccion;
  - el ESTADO:
      «completo»               sin pendientes: el rotulo es el final;
      «decidido (futilidad)»   mas horas en contra que floor(0,05·n_plan): ni
                               con todas las pendientes dentro llega al 95 %;
                               el rotulo final es «regla declarada»;
      «parcial»                quedan pendientes; el rotulo es PROVISIONAL, y
                               el intervalo dice que tan lejos esta del 95 %.
    El rotulo que se cita es el del estado «completo» o «decidido»; de uno
    «parcial» solo se cita x de n con su intervalo, como lectura parcial.
  - EVALUABLE: con n < 20, una sola hora fuera deja la fraccion bajo el 95 %,
    de modo que «95 %» exige el 100 %; desde 20 admite una, desde 40 dos. Se
    marca la fila con n >= 20.

Y el desglose por caso de cada regimen (x de n por caso), que es lo que dice
si la muestra estratificada cubrio los trece.

`--comprueba-canon DIR` sale con 0 si los `resultados_comparacion.xlsx` de los
trece casos de DIR tienen la huella del canon 2026-09 (la lista de
`gsa_directo/compuerta_punto_base.py`, copiada de HUELLAS.csv), y con 2 si
no: la muestra se toma de los almacenes de la matriz CANONICA.

Solo escribe lo que se le pide con --salida y --csv.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
RAIZ = AQUI.parents[4]

Z95 = 1.959963984540054
N_EVALUABLE = 20


def wilson(x: int, n: int, z: float = Z95) -> tuple:
    """(bajo, alto) del intervalo de Wilson de x exitos en n; (nan, nan) con
    n = 0."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = x / n
    den = 1.0 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    medio = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centro - medio), min(1.0, centro + medio))


def comprueba_canon(matriz: Path) -> int:
    sys.path.insert(0, str(RAIZ))
    from gsa_directo.compuerta_punto_base import HUELLAS_CANON, huella_libro
    malos = []
    for caso, sha in HUELLAS_CANON.items():
        try:
            h = huella_libro(matriz / caso)
        except OSError as exc:
            malos.append(f"{caso} ({type(exc).__name__})")
            continue
        if h != sha:
            malos.append(caso)
    if malos:
        print(f"  LA MATRIZ {matriz} NO ES LA DEL CANON 2026-09: "
              f"{', '.join(malos)}. La muestra de la validacion ampliada se "
              f"toma de los almacenes de la matriz del 19 de septiembre; "
              f"apunta ALMACENES a ella (en el servidor, "
              f"SALIDAS_SERVIDOR/matriz_reposo, o la entrega desempaquetada).")
        return 2
    print(f"  {matriz}: los trece libros tienen la huella del canon 2026-09")
    return 0


def lee(rutas) -> list:
    fuera = []
    for r in rutas:
        fuera.extend(json.loads(Path(r).read_text(encoding="utf-8")))
    return fuera


def plan_por_grupo(horas_dir) -> dict:
    """{(regimen, familia): [(caso, fecha)]} del plan de M-A2."""
    import medicion_ampliada as M
    from corre_mediciones import carga_horas
    plan = {}
    for sp in M.specs(carga_horas(Path(horas_dir))):
        plan.setdefault((sp["grupo"], sp["familia"]), []).append(
            (sp["caso"], sp["fecha"]))
    return plan


def lectura(resultados, plan) -> list:
    """Una fila por regimen y familia, con el rotulo de veredicto.py."""
    import medicion_ampliada as M
    import veredicto as V
    # Se agrupa por el ESTRATO de la muestra (el regimen del almacen, que la
    # seleccion comprobo), con la misma regla que `veredicto.agrupa`: fuera
    # las del recorte que movio el reposo, dentro las fallidas, fuera las sin
    # mercado. `veredicto.agrupa` agrupa por el regimen que el arnes vuelve a
    # calcular; si alguna hora difiere (una «cuantal» cuyo regimen cerrado es
    # el del almacen), la columna `regimen_distinto` lo dice.
    grupos, omit, apart, distinto = {}, {}, {}, {}
    for r in resultados:
        sp = r.get("spec", {})
        clave = (sp.get("grupo"), sp.get("familia"))
        hora = (sp.get("caso"), sp.get("fecha"))
        if r.get("omitida"):
            omit.setdefault(clave, set()).add(hora)
            continue
        if r.get("recorte_movio"):
            apart.setdefault(clave, set()).add(hora)
            continue
        if not r.get("veredicto") and not V.es_falla(r):
            continue
        if r.get("regimen") and r.get("regimen") != sp.get("grupo"):
            distinto[clave] = distinto.get(clave, 0) + 1
        grupos.setdefault(clave, {}).setdefault(hora, []).append(r)
    claves = sorted(set(plan) | set(grupos) | set(omit),
                    key=lambda k: ((M.REGIMENES.index(k[0])
                                    if k[0] in M.REGIMENES else 99), k[1]))
    filas = []
    for reg, fam in claves:
        horas_g = grupos.get((reg, fam), {})
        cuentas = {h: V.cuenta_hora(c, "cerrada") for h, c in horas_g.items()}
        n = len(cuentas)
        dentro = sum(1 for c in cuentas.values()
                     if c["juzgada"] and c["dentro"])
        fallas = sum(1 for c in cuentas.values() if c["falla"])
        juzg = sum(1 for c in cuentas.values() if c["juzgada"])
        no_llegan = n - juzg - fallas
        en_contra = n - dentro
        n_plan = len(plan.get((reg, fam), [])) or n
        n_omit = len(omit.get((reg, fam), set()))
        n_apart = len(apart.get((reg, fam), set()))
        pendientes = max(0, n_plan - n - n_omit - n_apart)
        lim = M.limite_fuera(n_plan)
        if en_contra > lim:
            estado = "decidido (futilidad)"
        elif pendientes == 0:
            estado = "completo"
        else:
            estado = "parcial"
        rot = V.rotulo(dentro, n)
        if estado == "decidido (futilidad)" and not rot.startswith("regla"):
            # n < 5 con la futilidad ya alcanzada: el rotulo final es regla
            # declarada; lo provisional de veredicto diria «insuficiente».
            rot = f"regla declarada (decidida por futilidad, n = {n})"
        bajo, alto = wilson(dentro, n)
        por_caso = {}
        for (caso, _f), c in cuentas.items():
            a = por_caso.setdefault(caso, [0, 0])
            a[1] += 1
            a[0] += int(c["juzgada"] and c["dentro"])
        filas.append(dict(
            regimen=reg, familia=fam, n_plan=n_plan, hechas=n,
            dentro=dentro, no_llegan=no_llegan, fuera=juzg - dentro,
            fallas=fallas, omitidas=n_omit, apartadas=n_apart,
            pendientes=pendientes, limite_en_contra=lim, estado=estado,
            regimen_distinto=distinto.get((reg, fam), 0),
            evaluable=n >= N_EVALUABLE, rotulo=rot,
            fraccion=(dentro / n if n else float("nan")),
            wilson_bajo=bajo, wilson_alto=alto,
            por_caso=" ".join(f"{c}:{a[0]}/{a[1]}"
                              for c, a in sorted(por_caso.items(),
                                                 key=lambda kv: M.CASOS.index(kv[0])
                                                 if kv[0] in M.CASOS else 99))))
    return filas


def texto(filas, plan_info) -> str:
    l = ["", "  LECTURA DE LA VALIDACION AMPLIADA (M-A2)", "",
         f"  {plan_info}", "",
         f"  {'regimen':<19s} {'familia':<17s} {'plan':>4s} {'hech':>4s} "
         f"{'dent':>4s} {'noll':>4s} {'fuer':>4s} {'fall':>4s} {'omit':>4s} "
         f"{'pend':>4s} {'frac':>6s} {'Wilson 95 %':>15s} {'eval':>4s} "
         f"{'estado':<21s} rotulo"]
    for f in filas:
        fr = "-" if f["hechas"] == 0 else f"{100 * f['fraccion']:5.1f}%"
        wi = ("-" if f["hechas"] == 0 else
              f"[{100 * f['wilson_bajo']:4.1f}; {100 * f['wilson_alto']:5.1f}]")
        l.append(f"  {f['regimen']:<19s} {f['familia']:<17s} {f['n_plan']:4d} "
                 f"{f['hechas']:4d} {f['dentro']:4d} {f['no_llegan']:4d} "
                 f"{f['fuera']:4d} {f['fallas']:4d} {f['omitidas']:4d} "
                 f"{f['pendientes']:4d} {fr:>6s} {wi:>15s} "
                 f"{'si' if f['evaluable'] else 'no':>4s} "
                 f"{f['estado']:<21s} {f['rotulo']}")
    for f in filas:
        if f["regimen_distinto"]:
            l.append(f"  AVISO: {f['regimen_distinto']} horas de "
                     f"{f['regimen']} ({f['familia']}) salen con otro regimen "
                     f"en el arnes; aqui cuentan en su estrato, y en la tabla "
                     f"de veredicto.py en el regimen del arnes")
    l += ["", "  Por caso (dentro/hechas):"]
    for f in filas:
        l.append(f"    {f['regimen']:<19s} {f['familia']:<17s} "
                 f"{f['por_caso'] or '-'}")
    l += ["",
          "  hech = horas con resultado que cuentan (el denominador del "
          "rotulo); noll = sin ninguna corrida en teq 160; fuer = juzgadas "
          "fuera de tolerancia; fall = fallidas; omit = no sometidas por la "
          "parada por futilidad; pend = del plan, sin hacer",
          "  Wilson 95 % = intervalo de la fraccion dentro/hechas; eval = "
          f"n >= {N_EVALUABLE} (desde ahi el 95 % admite una hora en contra)",
          "  estado: completo = rotulo final; decidido (futilidad) = regla "
          "declarada final (mas horas en contra que floor(0,05*plan)); "
          "parcial = rotulo PROVISIONAL, se cita solo x de n con su intervalo",
          "  El criterio es el de veredicto.py, sin cambios: 95 % de las horas "
          "dentro en teq 80 y 160, con cinco como minimo (ADR 0060).", ""]
    return "\n".join(l)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("json", nargs="*")
    ap.add_argument("--horas", default=None,
                    help="carpeta de los horas_<caso>.json (para el plan)")
    ap.add_argument("--salida", default=None)
    ap.add_argument("--csv", default=None)
    ap.add_argument("--comprueba-canon", default=None)
    args = ap.parse_args(argv)
    if args.comprueba_canon:
        return comprueba_canon(Path(args.comprueba_canon).resolve())
    if not args.json:
        print("  falta al menos un JSON de M-A2")
        return 2
    rutas = [Path(p).resolve() for p in args.json]
    salida = Path(args.salida).resolve() if args.salida else None
    csv_p = Path(args.csv).resolve() if args.csv else None
    horas_dir = (Path(args.horas).resolve() if args.horas
                 else rutas[0].parent)
    resultados = lee(rutas)
    # El plan depende de AMPLIACION_HORAS y AMPLIACION_SIN_ACELERAR: se toman
    # del fichero PLAN que el lanzador dejo en la carpeta, si estan ahi y no
    # vienen ya en el entorno (la relectura en casa).
    import os
    fichero_plan = horas_dir / "PLAN"
    if fichero_plan.is_file():
        for par in fichero_plan.read_text(encoding="utf-8").split():
            if "=" in par:
                k, v = par.split("=", 1)
                os.environ.setdefault(k, v)
    plan = plan_por_grupo(horas_dir)
    total_plan = sum(len(v) for v in plan.values())
    hechas = len({(r["spec"]["grupo"], r["spec"]["familia"], r["spec"]["caso"],
                   r["spec"]["fecha"]) for r in resultados})
    info = (f"plan: {total_plan} corridas (de {horas_dir}); con resultado u "
            f"omitidas: {hechas}; JSON: {', '.join(p.name for p in rutas)}")
    filas = lectura(resultados, plan)
    t = texto(filas, info)
    print(t, flush=True)
    if salida:
        salida.write_text(t, encoding="utf-8")
        print(f"  escrito {salida}")
    if csv_p:
        with open(csv_p, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(filas[0]) if filas
                               else ["regimen"])
            w.writeheader()
            for f in filas:
                w.writerow(f)
        print(f"  escrito {csv_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
