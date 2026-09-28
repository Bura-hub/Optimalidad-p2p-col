"""
spread_estatico.py — El spread de ineficiencia estatica con el colectivo
mensual (C-209, H-100, 2026-09-27).
==========================================================================
La propuesta pide cuantificar el valor del mercado P2P frente a C4 cuando
hay excedente en unos miembros y deficit en otros que el mecanismo estatico
no puede reasignar, «incluyendo la nocion de spread de ineficiencia
estatica». La nocion horaria (`static_spread_c4_vs_p2p`) se retiro con D4 y
C-175: el colectivo se liquida por mes con el Anexo 4.

Definicion (C-209). Cada mes el fondo comun (la inyeccion excedente de
todos) se reparte con el porcentaje; lo asignado a cada miembro es credito
hasta su importacion del mes y el resto va a bolsa desde el corte hx. La
ineficiencia estatica es el excedente que el reparto manda a bolsa por encima
de la importacion de un miembro mientras otro aun tenia importacion que
cubrir. La regla «importacion» (porcentaje de cada mes proporcional a la
importacion del mes) la elimina: es la cota superior del reparto estatico,
porque conoce el mes por adelantado.

    spread (kWh) = exceso a bolsa de C4 igual - el de C4 «importacion»
    spread (COP) = beneficio de C4 «importacion» - el de C4 igual
    recuperado por la via legal (D8) = P2P colectivo - C4
    referencia sin la via legal       = P2P - C4

La regla «importacion» es la cota superior EN ENERGIA (manda a bolsa el
minimo de cada mes, max(F_m - I_m, 0)). En valor no lo es: el spread en COP
se descompone exactamente en energia rescatada de la bolsa, momento (el
exceso cae en otras horas) y composicion (cambia quien recibe el credito);
solo la primera es la ineficiencia estatica propiamente dicha.

En el punto base del GSA (los seis factores en 1, mu = 1), con el evaluador
del GSA directo (`gsa_directo/evaluador.py`), que llama a la misma
`run_comparison` que la corrida. Comprueba que el `Resumen` (P2P, P2P
colectivo, C1 a C5) reproduce el canon (matriz por reposo del 19 de
septiembre) al peso. No escribe en `outputs/` ni en `graficas/`.

Escribe en SALIDAS_SERVIDOR/spread_estatico_2026-09-27/:

    por_caso/<caso>.csv       una fila por caso, en cuanto el caso termina
    por_caso/<caso>_testigos.csv
    spread_13casos.csv        las trece filas juntas (cuando estan todas)
    testigos_resumen.csv      canon frente a recalculado, siete mecanismos
    procedencia.txt           commit, fecha, orden, dato, resultado

Los casos se pueden correr por tandas (`--casos E0 E1`); cada tanda deja su
fila en `por_caso/`, y `--junta` reune las trece sin simular.

    python -u reformateo/documento/scripts/spread_estatico.py [--casos ...]
    python -u reformateo/documento/scripts/spread_estatico.py --junta

Sale con 0 si todos los testigos quedan al peso; con 1 si no.

Actividad 3.2.
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

TESTIGOS = ("P2P", "P2P_colectivo", "C1", "C2", "C3", "C4", "C5")
REGLAS = ("consumo", "aporte", "generacion", "importacion")
TOL_PESO = 0.5
MATRIZ_CANON = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
                / "SALIDAS_SERVIDOR" / "matriz_reposo")
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "spread_estatico_2026-09-27"


def lee_resumen_canon(matriz: Path, caso: str) -> dict:
    libro = matriz / caso / "outputs" / "resultados_comparacion.xlsx"
    if not libro.exists():
        raise FileNotFoundError(f"no esta el libro del canon: {libro}")
    res = pd.read_excel(libro, sheet_name="Resumen")
    out = {str(e): float(v) for e, v in
           zip(res["Escenario"], res["Ganancia_neta_COP"])}
    faltan = [e for e in TESTIGOS if e not in out]
    if faltan:
        raise ValueError(f"{caso}: el Resumen del canon no trae {faltan}")
    malos = [e for e in TESTIGOS if not np.isfinite(out[e])]
    if malos:
        raise ValueError(f"{caso}: valor no finito en el canon: {malos}")
    return out


def finito(nombre: str, v) -> float:
    v = float(v)
    if not np.isfinite(v):
        raise ValueError(f"{nombre}: valor no finito")
    return v


def fila_del_caso(caso: str, ins, cr) -> dict:
    """La fila de la tabla a partir del `ComparisonResult`."""
    if not cr.c4_energia:
        raise ValueError(f"{caso}: la comparacion no trae c4_energia (C-209)")
    for r in REGLAS:
        if f"C4_regla_{r}" not in cr.contrafacticos:
            raise ValueError(f"{caso}: la comparacion no trae C4_regla_{r}")
    nb = cr.net_benefit
    imp = cr.contrafacticos["C4_regla_importacion"]
    cred_i = finito("credito igual", cr.c4_energia["credito_kwh"])
    exc_i = finito("exceso igual", cr.c4_energia["exceso_kwh"])
    cred_m = finito("credito importacion", imp["credito_kwh"])
    exc_m = finito("exceso importacion", imp["exceso_kwh"])
    fondo = cred_i + exc_i
    if abs((cred_m + exc_m) - fondo) > 1e-6 * max(1.0, fondo):
        raise ValueError(f"{caso}: el fondo no cuadra entre las dos reglas "
                         f"({fondo} frente a {cred_m + exc_m})")
    c4 =finito("C4", nb["C4"])
    c4_imp = finito("C4 importacion", imp["total"])
    p2p = finito("P2P", nb["P2P"])
    pcol = finito("P2P colectivo", nb["P2P_colectivo"])
    spread_kwh = exc_i - exc_m
    spread_cop = c4_imp - c4
    # Descomposicion exacta del spread en valor (el autoconsumo no cambia),
    # con p el precio medio del credito y b el de la bolsa del exceso
    # (COP/kWh), «i» el reparto igual y «m» la regla «importacion»:
    #   spread_COP = (cred_m - cred_i) p_i + (exc_m - exc_i) b_i   energia
    #              + exc_m (b_m - b_i)                             momento
    #              + cred_m (p_m - p_i)                            composicion
    # «energia» es el kWh que pasa de la bolsa al credito, la ineficiencia
    # estatica propiamente dicha. «momento»: el exceso cae en otras horas
    # (el corte hx de cada miembro se mueve) y se paga a otra bolsa.
    # «composicion»: cambia QUIEN recibe el credito, y cada institucion lo
    # valora a su tarifa menos su deduccion.
    vc_i = finito("valor credito igual", cr.c4_energia["credito_COP"])
    vb_i = finito("valor bolsa igual", cr.c4_energia["exceso_COP"])
    vc_m = finito("valor credito importacion", imp["credito_COP"])
    vb_m = finito("valor bolsa importacion", imp["exceso_COP"])
    p_i = vc_i / cred_i if cred_i > 0 else 0.0
    p_m = vc_m / cred_m if cred_m > 0 else 0.0
    b_i = vb_i / exc_i if exc_i > 0 else 0.0
    b_m = vb_m / exc_m if exc_m > 0 else 0.0
    efecto_energia = (cred_m - cred_i) * p_i + (exc_m - exc_i) * b_i
    efecto_momento = exc_m * (b_m - b_i)
    efecto_composicion = cred_m * (p_m - p_i)
    suma = efecto_energia + efecto_momento + efecto_composicion
    if abs(suma - spread_cop) > TOL_PESO:
        raise ValueError(f"{caso}: la descomposicion del spread no cierra "
                         f"({suma:.3f} frente a {spread_cop:.3f} COP)")
    fila = dict(
        caso=caso, fondo_kwh=fondo,
        credito_igual_kwh=cred_i, exceso_igual_kwh=exc_i,
        credito_importacion_kwh=cred_m, exceso_importacion_kwh=exc_m,
        spread_kwh=spread_kwh,
        spread_frac_fondo=spread_kwh / fondo if fondo > 0 else float("nan"),
        C4_COP=c4, C4_importacion_COP=c4_imp, spread_COP=spread_cop,
        spread_frac_C4=spread_cop / abs(c4) if c4 else float("nan"),
        spread_energia_COP=efecto_energia,
        spread_momento_COP=efecto_momento,
        spread_composicion_COP=efecto_composicion,
        precio_credito_igual=p_i, precio_credito_importacion=p_m,
        precio_bolsa_igual=b_i, precio_bolsa_importacion=b_m,
        credito_igual_COP=vc_i, credito_importacion_COP=vc_m,
        bolsa_igual_COP=vb_i, bolsa_importacion_COP=vb_m,
        P2P_COP=p2p, P2P_colectivo_COP=pcol,
        colectivo_menos_C4_COP=pcol - c4, P2P_menos_C4_COP=p2p - c4,
        # La fraccion del spread en valor que recupera cada via. Sin spread
        # (menos de medio peso) no hay nada que recuperar: queda vacia y se
        # marca, no se inventa.
        fraccion_definida=bool(spread_cop > TOL_PESO),
        fraccion_colectivo=((pcol - c4) / spread_cop if spread_cop > TOL_PESO
                            else float("nan")),
        fraccion_P2P=((p2p - c4) / spread_cop if spread_cop > TOL_PESO
                      else float("nan")),
        caso_art20_importacion=int(imp["caso_art20"]),
    )
    for r in REGLAS[:-1]:
        d = cr.contrafacticos[f"C4_regla_{r}"]
        fila[f"C4_regla_{r}_COP"] = finito(r, d["total"])
        fila[f"exceso_regla_{r}_kwh"] = finito(r, d["exceso_kwh"])
    # Guardas de la definicion: la regla «importacion» no puede mandar a bolsa
    # mas que ninguna otra.
    for r in ("igual",) + REGLAS[:-1]:
        e = exc_i if r == "igual" else fila[f"exceso_regla_{r}_kwh"]
        if e < exc_m - 1e-6 * max(1.0, fondo):
            raise ValueError(f"{caso}: la regla {r} manda menos a bolsa "
                             f"({e:.6f}) que «importacion» ({exc_m:.6f}); "
                             f"no es la cota que se declara")
    return fila


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


def junta(salida: Path, orden: str, mte_root: str, matriz: Path) -> int:
    por_caso = salida / "por_caso"
    faltan = [c for c in comun.ORDEN_CASOS
              if not (por_caso / f"{c}.csv").exists()]
    if faltan:
        print(f"  faltan casos por correr: {' '.join(faltan)}; no se junta")
        return 0
    df = pd.concat([pd.read_csv(por_caso / f"{c}.csv")
                    for c in comun.ORDEN_CASOS], ignore_index=True)
    dft = pd.concat([pd.read_csv(por_caso / f"{c}_testigos.csv")
                     for c in comun.ORDEN_CASOS], ignore_index=True)
    df.to_csv(salida / "spread_13casos.csv", index=False, float_format="%.6f")
    dft.to_csv(salida / "testigos_resumen.csv", index=False,
               float_format="%.6f")
    malos = dft[dft["dif_COP"].abs() > TOL_PESO]
    with open(salida / "procedencia.txt", "w", encoding="utf-8") as fh:
        fh.write("C-209: spread de ineficiencia estatica con el colectivo "
                 "mensual (H-100)\n")
        fh.write(f"fecha: {dt.datetime.now().isoformat(timespec='seconds')}\n")
        fh.write(f"git rev-parse HEAD: {git_head()}\n")
        fh.write("arbol de trabajo (codigo) con cambios sin commit:\n"
                 + (git_sucio() or "(ninguno)") + "\n")
        fh.write(f"orden de esta llamada: {orden}\n")
        fh.write(f"MTE_ROOT: {mte_root}\n")
        fh.write(f"huella del dato: {comun.huella_datos(mte_root)}\n")
        fh.write(f"canon de comparacion: {matriz}\n")
        fh.write("punto: seis factores en 1, mu = 1 (evaluador del GSA "
                 "directo, evalua_comparacion, despacho 'piso')\n")
        fh.write("definicion: spread_kwh = exceso a bolsa de C4 (reparto "
                 "igual, D5) - el de C4 con la regla 'importacion' (PDE de "
                 "cada mes proporcional a la importacion del mes, cota "
                 "superior en energia, no en valor); spread_COP = C4 "
                 "importacion - C4 = energia + momento + composicion\n")
        fh.write(f"casos: {' '.join(comun.ORDEN_CASOS)}\n")
        fh.write(f"testigos del Resumen fuera del peso: {len(malos)} de "
                 f"{len(dft)}\n")
    print(f"\n  juntado en {salida / 'spread_13casos.csv'}")
    if len(malos):
        for _, f in malos.iterrows():
            print(f"  TESTIGO FUERA DEL PESO {f['caso']} {f['escenario']}: "
                  f"{f['dif_COP']:+,.2f} COP")
        print("SPREAD ESTATICO: EL RESUMEN NO REPRODUCE EL CANON")
        return 1
    print(f"SPREAD ESTATICO: {len(dft)} testigos del Resumen al peso en los "
          f"{len(df)} casos")
    return 0


def main(argv=None) -> int:
    comun.salida_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--matriz", default=str(MATRIZ_CANON))
    ap.add_argument("--salida", default=str(SALIDA))
    ap.add_argument("--casos", nargs="+", default=list(comun.ORDEN_CASOS))
    ap.add_argument("--mte-root", default=None)
    ap.add_argument("--cache", default=None,
                    help="carpeta de cache de la carga del MTE (opcional)")
    ap.add_argument("--junta", action="store_true",
                    help="solo reune las filas de por_caso/, sin simular")
    args = ap.parse_args(argv)

    matriz = Path(args.matriz)
    mte_root = args.mte_root or comun.mte_root_defecto()
    if not Path(mte_root).is_dir():
        raise SystemExit(f"MTE_ROOT no es una carpeta: {mte_root}")
    salida = Path(args.salida)
    orden = " ".join([Path(sys.executable).name, "-u",
                      "reformateo/documento/scripts/spread_estatico.py"]
                     + (argv if argv is not None else sys.argv[1:]))
    if args.junta:
        return junta(salida, orden, mte_root, matriz)

    from gsa_directo import evaluador

    malos = [c for c in args.casos if c not in comun.CASOS]
    if malos:
        raise SystemExit(f"casos desconocidos: {malos}")
    por_caso = salida / "por_caso"
    por_caso.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("SPREAD DE INEFICIENCIA ESTATICA, COLECTIVO MENSUAL (C-209)")
    print("=" * 72)
    print(f"  matriz   {matriz}")
    print(f"  MTE_ROOT {mte_root}")
    t0 = time.time()
    datos = evaluador.carga_mte(mte_root, args.cache)
    print(f"  carga del MTE en {time.time() - t0:.1f} s")

    hay_malos = False
    for caso in args.casos:
        ins = evaluador.prepara_caso(caso, datos)
        canon = lee_resumen_canon(matriz, caso)
        t1 = time.time()
        _out, cr = evaluador.evalua_comparacion(ins, comun.PUNTO_BASE)
        seg = time.time() - t1
        testigos = []
        for e in TESTIGOS:
            v = finito(f"{caso} {e}", cr.net_benefit[e])
            testigos.append(dict(caso=caso, escenario=e, canon_COP=canon[e],
                                 nuevo_COP=v, dif_COP=v - canon[e]))
        fila = fila_del_caso(caso, ins, cr)
        pd.DataFrame([fila]).to_csv(por_caso / f"{caso}.csv", index=False,
                                    float_format="%.6f")
        pd.DataFrame(testigos).to_csv(por_caso / f"{caso}_testigos.csv",
                                      index=False, float_format="%.6f")
        peor = max(abs(t["dif_COP"]) for t in testigos)
        hay_malos |= peor > TOL_PESO
        print(f"\n  {caso:<5} {seg:6.1f} s  testigos: peor dif {peor:.3f} COP"
              f"{'  FUERA DEL PESO' if peor > TOL_PESO else ''}")
        print(f"        fondo {fila['fondo_kwh']:>12,.1f} kWh  exceso igual "
              f"{fila['exceso_igual_kwh']:>12,.1f}  importacion "
              f"{fila['exceso_importacion_kwh']:>12,.1f}  spread "
              f"{fila['spread_kwh']:>10,.1f} kWh")
        print(f"        spread {fila['spread_COP']:>14,.0f} COP (energia "
              f"{fila['spread_energia_COP']:,.0f}, momento "
              f"{fila['spread_momento_COP']:,.0f}, composicion "
              f"{fila['spread_composicion_COP']:,.0f})  colectivo-C4 "
              f"{fila['colectivo_menos_C4_COP']:>+12,.0f}  P2P-C4 "
              f"{fila['P2P_menos_C4_COP']:>+12,.0f}")

    r = junta(salida, orden, mte_root, matriz)
    return 1 if (hay_malos or r) else 0


if __name__ == "__main__":
    sys.exit(main())
