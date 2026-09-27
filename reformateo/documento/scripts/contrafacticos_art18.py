"""
contrafacticos_art18.py — Los contrafacticos del colectivo con la capacidad
por usuario del articulo 18 (C-206, 2026-09-27).
==========================================================================
El caso del articulo 20 de la Resolucion CREG 101 072 se decide con la
capacidad instalada por usuario del articulo 18: la suma de las capacidades
del autogenerador colectivo entre el numero de fronteras, contando las que
solo consumen. Hasta C-206 el contrafactico de 11 fronteras comparaba la
planta mayor con los 100 kW, y en E4, E5, P2, I1 y N1 caia en el caso 2.

Este guion recalcula, en el punto base del GSA (los seis factores en 1,
mu = 1), los cinco contrafacticos de los trece casos de la matriz con el
evaluador del GSA directo (`gsa_directo/evaluador.py`), que llama a la misma
`run_comparison` que produce la hoja `Contrafacticos`, y los compara con esa
hoja del canon 2026-09 (matriz por reposo del 19 de septiembre). No escribe
en `outputs/` ni en `graficas/`.

Escribe en SALIDAS_SERVIDOR/contrafacticos_art18_2026-09-27/:

    contrafacticos_13casos.csv      caso, contrafactico, caso_art20, total y
                                    por institucion (COP), recalculados
    comparacion_canon.csv           cada fila frente al canon: caso del
                                    art. 20 antes y despues, diferencias
    procedencia.txt                 commit, fecha, orden, dato

Sale con 0 si solo cambian las filas esperadas (las dos de 11 fronteras en
E4, E5, P2, I1 y N1) y todo lo demas queda al peso; con 1 si no.

    python -u reformateo/documento/scripts/contrafacticos_art18.py

Actividad 2.2.
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from gsa_directo import comun  # noqa: E402

CONTRAFACTICOS = ("C4_11_fronteras", "P2P_colectivo_11_fronteras",
                  "C4_regla_consumo", "C4_regla_aporte",
                  "C4_regla_generacion")
DE_11 = ("C4_11_fronteras", "P2P_colectivo_11_fronteras")
CAMBIAN_ESPERADOS = ("E4", "E5", "P2", "I1", "N1")
TOL_PESO = 0.5
MATRIZ_CANON = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
                / "SALIDAS_SERVIDOR" / "matriz_reposo")
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "contrafacticos_art18_2026-09-27"


def lee_canon(matriz: Path, caso: str, nombres: list) -> dict:
    """{contrafactico: (caso_art20, total, por_institucion)} de la hoja
    `Contrafacticos` del canon, y el Resumen para los testigos."""
    libro = matriz / caso / "outputs" / "resultados_comparacion.xlsx"
    if not libro.exists():
        raise FileNotFoundError(f"no esta el libro del canon: {libro}")
    hoja = pd.read_excel(libro, sheet_name="Contrafacticos")
    cols = [f"A{i + 1}" for i in range(len(nombres))]
    faltan = [c for c in ["contrafactico", "total_COP", "caso_art20"] + cols
              if c not in hoja.columns]
    if faltan or f"A{len(nombres) + 1}" in hoja.columns:
        raise ValueError(f"{caso}: la hoja Contrafacticos no trae las columnas "
                         f"esperadas para {len(nombres)} instituciones "
                         f"(faltan {faltan})")
    out = {}
    for _, f in hoja.iterrows():
        pa = f[cols].to_numpy(dtype=float)
        if not (np.all(np.isfinite(pa)) and np.isfinite(float(f["total_COP"]))):
            raise ValueError(f"{caso} {f['contrafactico']}: valor no finito en "
                             f"el canon")
        out[str(f["contrafactico"])] = (int(f["caso_art20"]),
                                        float(f["total_COP"]), pa)
    faltan = [c for c in CONTRAFACTICOS if c not in out]
    if faltan:
        raise ValueError(f"{caso}: el canon no trae {faltan}")
    res = pd.read_excel(libro, sheet_name="Resumen")
    resumen = {str(e): float(v) for e, v in
               zip(res["Escenario"], res["Ganancia_neta_COP"])}
    return dict(contrafacticos=out, resumen=resumen)


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ,
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def git_sucio() -> str:
    r = subprocess.run(["git", "status", "--short", "--", "scenarios",
                        "analysis", "core", "gsa_directo", "data",
                        "main_simulation.py"],
                       cwd=RAIZ, capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


def main(argv=None) -> int:
    comun.salida_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--matriz", default=str(MATRIZ_CANON))
    ap.add_argument("--salida", default=str(SALIDA))
    ap.add_argument("--casos", nargs="+", default=list(comun.ORDEN_CASOS))
    ap.add_argument("--mte-root", default=None)
    ap.add_argument("--cache", default=None,
                    help="carpeta de cache de la carga del MTE (opcional)")
    args = ap.parse_args(argv)

    from gsa_directo import evaluador
    from scenarios.scenario_c4_creg101072 import capacidad_por_usuario_art18

    malos = [c for c in args.casos if c not in comun.CASOS]
    if malos:
        raise SystemExit(f"casos desconocidos: {malos}")
    matriz = Path(args.matriz)
    mte_root = args.mte_root or comun.mte_root_defecto()
    if not Path(mte_root).is_dir():
        raise SystemExit(f"MTE_ROOT no es una carpeta: {mte_root}")
    salida = Path(args.salida)

    print("=" * 72)
    print("CONTRAFACTICOS DEL COLECTIVO CON EL ART. 18 (C-206), punto base")
    print("=" * 72)
    print(f"  matriz   {matriz}")
    print(f"  MTE_ROOT {mte_root}")
    t0 = time.time()
    datos = evaluador.carga_mte(mte_root, args.cache)
    print(f"  carga del MTE en {time.time() - t0:.1f} s")

    filas, comp, testigos, capus = [], [], [], []
    for caso in args.casos:
        ins = evaluador.prepara_caso(caso, datos)
        canon = lee_canon(matriz, caso, ins.nombres)
        t1 = time.time()
        out, cr = evaluador.evalua_comparacion(ins, comun.PUNTO_BASE)
        seg = time.time() - t1
        capus.append(dict(
            caso=caso, cap_kw=";".join(f"{c:.4f}" for c in ins.cap),
            suma_kw=float(ins.cap.sum()),
            capu_11_kw=capacidad_por_usuario_art18(ins.cap, max(11, ins.N)),
            capu_N_kw=capacidad_por_usuario_art18(ins.cap, ins.N),
            planta_mayor_kw=float(ins.cap.max())))
        # Testigos: lo que no depende del contrafactico debe seguir al peso.
        for e in ("C4", "P2P_colectivo", "P2P", "C1"):
            d = float(cr.net_benefit[e]) - canon["resumen"][e]
            testigos.append((caso, e, canon["resumen"][e],
                             float(cr.net_benefit[e]), d))
        for cf in CONTRAFACTICOS:
            if cf not in cr.contrafacticos:
                raise ValueError(f"{caso}: la comparacion no trae {cf}")
            r = cr.contrafacticos[cf]
            pa = np.asarray(r["por_agente"], dtype=float)
            tot = float(r["total"])
            if not (np.all(np.isfinite(pa)) and np.isfinite(tot)):
                raise ValueError(f"{caso} {cf}: valor no finito")
            fila = dict(caso=caso, contrafactico=cf,
                        caso_art20=int(r["caso_art20"]), total_COP=tot)
            for nombre in comun.INSTITUCIONES:
                fila[nombre] = (float(pa[ins.nombres.index(nombre)])
                                if nombre in ins.nombres else float("nan"))
            filas.append(fila)
            c_caso, c_tot, c_pa = canon["contrafacticos"][cf]
            dif_pa = pa - c_pa
            cambia = (abs(tot - c_tot) > TOL_PESO
                      or float(np.max(np.abs(dif_pa))) > TOL_PESO
                      or c_caso != int(r["caso_art20"]))
            esperado = (cf in DE_11 and caso in CAMBIAN_ESPERADOS)
            fc = dict(caso=caso, contrafactico=cf, caso_art20_canon=c_caso,
                      caso_art20_nuevo=int(r["caso_art20"]),
                      total_canon_COP=c_tot, total_nuevo_COP=tot,
                      dif_total_COP=tot - c_tot,
                      dif_rel=(tot - c_tot) / abs(c_tot) if c_tot else
                      float("nan"),
                      cambia=bool(cambia), se_esperaba_cambio=bool(esperado))
            for nombre in comun.INSTITUCIONES:
                fc[f"dif_{nombre}"] = (
                    float(dif_pa[ins.nombres.index(nombre)])
                    if nombre in ins.nombres else float("nan"))
            comp.append(fc)
        print(f"\n  {caso:<5} {seg:6.1f} s  capacidad por usuario: "
              f"{capus[-1]['capu_11_kw']:.2f} kW con 11 fronteras, "
              f"{capus[-1]['capu_N_kw']:.2f} kW con {ins.N}; planta mayor "
              f"{capus[-1]['planta_mayor_kw']:.2f} kW")
        for fc in comp[-len(CONTRAFACTICOS):]:
            marca = ("cambia" if fc["cambia"] else "al peso")
            print(f"        {fc['contrafactico']:<28} caso {fc['caso_art20_canon']}"
                  f" -> {fc['caso_art20_nuevo']}  canon "
                  f"{fc['total_canon_COP']:>16,.0f}  nuevo "
                  f"{fc['total_nuevo_COP']:>16,.0f}  dif "
                  f"{fc['dif_total_COP']:>+14,.0f}  {marca}")

    salida.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas).to_csv(salida / "contrafacticos_13casos.csv",
                               index=False, float_format="%.6f")
    dfc = pd.DataFrame(comp)
    dfc.to_csv(salida / "comparacion_canon.csv", index=False,
               float_format="%.6f")
    pd.DataFrame(capus).to_csv(salida / "capacidad_por_usuario.csv",
                               index=False, float_format="%.6f")
    dft = pd.DataFrame(testigos, columns=["caso", "escenario", "canon_COP",
                                          "nuevo_COP", "dif_COP"])
    dft.to_csv(salida / "testigos_resumen.csv", index=False,
               float_format="%.6f")

    inesperados = dfc[dfc["cambia"] != dfc["se_esperaba_cambio"]]
    testigos_malos = dft[dft["dif_COP"].abs() > TOL_PESO]
    orden = " ".join([Path(sys.executable).name, "-u",
                      "reformateo/documento/scripts/contrafacticos_art18.py"]
                     + (argv if argv is not None else sys.argv[1:]))
    sucio = git_sucio()
    with open(salida / "procedencia.txt", "w", encoding="utf-8") as fh:
        fh.write(f"C-206: contrafacticos del colectivo con la capacidad por "
                 f"usuario del art. 18\n")
        fh.write(f"fecha: {dt.datetime.now().isoformat(timespec='seconds')}\n")
        fh.write(f"git rev-parse HEAD: {git_head()}\n")
        fh.write("arbol de trabajo (codigo) con cambios sin commit:\n"
                 + (sucio or "(ninguno)") + "\n")
        fh.write(f"orden: {orden}\n")
        fh.write(f"MTE_ROOT: {mte_root}\n")
        fh.write(f"huella del dato: {comun.huella_datos(mte_root)}\n")
        fh.write(f"canon de comparacion: {matriz}\n")
        fh.write(f"punto: seis factores en 1, mu = 1 (evaluador del GSA "
                 f"directo, evalua_comparacion)\n")
        fh.write(f"casos: {' '.join(args.casos)}\n")
        fh.write(f"filas que cambian: {int(dfc['cambia'].sum())} de "
                 f"{len(dfc)}; inesperadas: {len(inesperados)}; testigos "
                 f"del Resumen fuera del peso: {len(testigos_malos)}\n")
    print(f"\n  escrito en {salida}")
    print(f"  filas que cambian: {int(dfc['cambia'].sum())} de {len(dfc)}")
    if len(inesperados) or len(testigos_malos):
        for _, f in inesperados.iterrows():
            print(f"  INESPERADO {f['caso']} {f['contrafactico']}: cambia="
                  f"{f['cambia']}, se esperaba {f['se_esperaba_cambio']}")
        for _, f in testigos_malos.iterrows():
            print(f"  TESTIGO FUERA DEL PESO {f['caso']} {f['escenario']}: "
                  f"{f['dif_COP']:+,.2f} COP")
        print("CONTRAFACTICOS ART. 18: HAY CAMBIOS NO ESPERADOS")
        return 1
    print("CONTRAFACTICOS ART. 18: cambian solo las filas de 11 fronteras de "
          f"{', '.join(CAMBIAN_ESPERADOS)}; todo lo demas al peso")
    return 0


if __name__ == "__main__":
    sys.exit(main())
