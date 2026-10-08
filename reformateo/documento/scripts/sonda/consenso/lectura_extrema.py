"""La lectura de la dinamica con precios extremos (DX, M-A2X), por regimen y
familia de precio.

Actividades 1.1 y 4.1.

    python -u reformateo/documento/scripts/sonda/consenso/lectura_extrema.py \\
        SALIDAS_SERVIDOR/dinamica_extrema/m_a2x.json [mas JSON] \\
        --horas SALIDAS_SERVIDOR/dinamica_extrema \\
        --base SALIDAS_SERVIDOR/validacion_ampliada/lectura_m_a2.csv \\
        --salida SALIDAS_SERVIDOR/dinamica_extrema/lectura_m_a2x.txt \\
        --csv SALIDAS_SERVIDOR/dinamica_extrema/lectura_m_a2x.csv

EL CRITERIO NO SE TOCA: la tabla es la de `lectura_ampliada.lectura` (que
usa `agrupa`, `cuenta_hora` y `rotulo` de `veredicto.py` tal cual), con el
plan de `medicion_extrema.specs`; cada familia de precio es una familia del
veredicto, de modo que sale una fila por regimen y familia de precio. Anade:

  - la ENERGIA: en cada corrida juzgada, la mayor |E_dinamica - E_cerrada| en
    teq 80 y 160 (en M-A2 fue menor de 1e-8 kWh en todas), por familia;
  - y, con `--base` (el `lectura_m_a2.csv` de M-A2, la de los precios del
    punto base), la fraccion dentro de cada regimen con los precios del punto
    base, al lado, para comparar. No se suman ni se promedian.

Solo escribe lo que se le pide con --salida y --csv.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

TEQ = (80.0, 160.0)


def plan_por_grupo(horas_dir) -> dict:
    """{(regimen, familia): [(caso, fecha)]} del plan de M-A2X."""
    import medicion_extrema as MX
    from corre_mediciones import carga_horas
    plan = {}
    for sp in MX.specs(carga_horas(Path(horas_dir))):
        plan.setdefault((sp["grupo"], sp["familia"]), []).append(
            (sp["caso"], sp["fecha"]))
    return plan


def energia(resultados) -> dict:
    """{familia: (corridas juzgadas, max |E_din - E_cerrada| en teq 80 y 160)}
    con la referencia «cerrada»."""
    fuera = {}
    for r in resultados:
        if not r.get("veredicto") or r.get("omitida"):
            continue
        E = float(r["cerrada"]["cerrada"]["E"])
        fam = r["spec"].get("familia", "")
        n, peor = fuera.get(fam, (0, 0.0))
        hubo = False
        for f in r.get("filas", []):
            if any(abs(float(f["teq"]) - t) < 1e-9 for t in TEQ):
                hubo = True
                peor = max(peor, abs(sum(float(q) for q in f["q"]) - E))
        fuera[fam] = (n + int(hubo), peor)
    return fuera


def lee_base(ruta) -> dict:
    """{regimen: (dentro, hechas, fraccion)} de `lectura_m_a2.csv`."""
    with open(ruta, newline="", encoding="utf-8") as fh:
        return {f["regimen"]: (int(f["dentro"]), int(f["hechas"]),
                               float(f["fraccion"]))
                for f in csv.DictReader(fh)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("json", nargs="*")
    ap.add_argument("--horas", default=None)
    ap.add_argument("--base", default=None,
                    help="lectura_m_a2.csv de M-A2 (precios del punto base)")
    ap.add_argument("--salida", default=None)
    ap.add_argument("--csv", default=None)
    args = ap.parse_args(argv)
    if not args.json:
        print("  falta al menos un JSON de M-A2X")
        return 2
    import lectura_ampliada as LA
    rutas = [Path(p).resolve() for p in args.json]
    horas_dir = Path(args.horas).resolve() if args.horas else rutas[0].parent
    fichero_plan = horas_dir / "PLAN"
    if fichero_plan.is_file():
        for par in fichero_plan.read_text(encoding="utf-8").split():
            if "=" in par:
                k, v = par.split("=", 1)
                os.environ.setdefault(k, v.replace(",", " "))
    resultados = LA.lee(rutas)
    plan = plan_por_grupo(horas_dir)
    total_plan = sum(len(v) for v in plan.values())
    hechas = len({(r["spec"]["grupo"], r["spec"]["familia"],
                   r["spec"]["caso"], r["spec"]["fecha"]) for r in resultados})
    info = (f"plan: {total_plan} corridas (de {horas_dir}); con resultado u "
            f"omitidas: {hechas}; JSON: {', '.join(p.name for p in rutas)}")
    filas = LA.lectura(resultados, plan)
    base = lee_base(args.base) if args.base else {}
    for f in filas:
        b = base.get(f["regimen"])
        f["base_dentro_hechas"] = f"{b[0]}/{b[1]}" if b else ""
        f["base_fraccion"] = b[2] if b else ""
    t = LA.texto(filas, info).replace(
        "LECTURA DE LA VALIDACION AMPLIADA (M-A2)",
        "LECTURA DE LA DINAMICA CON PRECIOS EXTREMOS (M-A2X), por regimen y "
        "familia de precio")
    lineas = [t, "  ENERGIA en teq 80 y 160 (max |E_dinamica - E_cerrada|, kWh):"]
    for fam, (n, peor) in sorted(energia(resultados).items()):
        lineas.append(f"    {fam:<28s} {n:4d} corridas  {peor:.3e}")
    if base:
        lineas += ["", "  CON LOS PRECIOS DEL PUNTO BASE (M-A2, lectura_m_a2.csv; "
                   "otra muestra, no se suma):"]
        for f in filas:
            if f["base_dentro_hechas"]:
                fr = (f"{100 * f['fraccion']:5.1f} %" if f["hechas"] else "-")
                lineas.append(f"    {f['regimen']:<19s} {f['familia']:<28s} "
                              f"extremo {f['dentro']}/{f['hechas']} ({fr}); "
                              f"base {f['base_dentro_hechas']} "
                              f"({100 * f['base_fraccion']:.1f} %)")
    texto = "\n".join(lineas) + "\n"
    print(texto, flush=True)
    if args.salida:
        Path(args.salida).write_text(texto, encoding="utf-8")
        print(f"  escrito {args.salida}")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(filas[0]) if filas
                               else ["regimen"])
            w.writeheader()
            for f in filas:
                w.writerow(f)
        print(f"  escrito {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
