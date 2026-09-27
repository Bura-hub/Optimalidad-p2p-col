"""
contrafactico_comercializador.py — Las cinco instituciones con un solo
comercializador, como exige el art. 10 num. 1 de la CREG 101 072 para el
autogenerador colectivo (A2, H-97, 2026-09-27).
==========================================================================
«Las fronteras comerciales para consumo de energia y entrega de excedentes
pertenecientes a un mismo AC deberan ser representadas por el mismo agente
comercializador» (Resolucion CREG 101 072, art. 10 num. 1).

El canon NO cambia: liquida todos los mecanismos con el reparto real (cuatro
instituciones con ASC, Cesmag con CEDENAR; CAL-47, H-75). Este guion mide el
contrafactico en los trece casos de la matriz y en todos los mecanismos, con
tres variantes:

    real      el reparto real, sin forzar (debe reproducir el canon al peso)
    asc       las cinco con ASC
    cedenar   las cinco con CEDENAR

Cada variante se prepara con `evaluador.prepara_caso(..., comercializador=)`,
que fuerza el perfil tarifario justo despues del regimen no regulado y lo
restituye al salir, y se evalua en el punto base del GSA (los seis factores en
1, mu = 1) con `evaluador.evalua_comparacion`. El guion restituye ademas el
reparto real al terminar cada variante (`forzar_comercializador(None)` en un
`finally` que no traga la excepcion) y comprueba que quedo restituido.

Compuerta de coherencia: la variante `real` tiene que reproducir al peso la
hoja `Resumen` (y `Por_agente`, la energia, la parte del vendedor y las horas
cuantales) del canon en los trece casos, con las mismas comprobaciones que
`gsa_directo/compuerta_punto_base.py`. Si no, se detiene sin escribir nada.

Escribe en SALIDAS_SERVIDOR/contrafactico_comercializador_2026-09-27/:

    mecanismos_13casos.csv   caso, variante, beneficio de cada mecanismo,
                             energia, parte del vendedor (la del almacen),
                             horas cuantales y el ancho de banda
    brechas_13casos.csv      por caso y variante, seis brechas con su signo y
                             si cambia respecto de `real`
    por_institucion.csv      por caso, variante e institucion, P2P - C1,
                             P2P - C4 y P2P - C5 con su signo y si cambia
    compuerta_real.csv       las comprobaciones de la variante real
    procedencia.txt          commit, fecha, orden, dato, resultado

No escribe en `outputs/` ni en `graficas/`.

    python -u reformateo/documento/scripts/contrafactico_comercializador.py

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

VARIANTES = ("real", "asc", "cedenar")
MECANISMOS = ("P2P", "P2P_colectivo", "C1", "C2", "C3", "C4", "C5")
BRECHAS = {                      # nombre -> (minuendo, sustraendo)
    "P2P_menos_C1": ("P2P", "C1"),
    "P2P_menos_C4": ("P2P", "C4"),
    "P2P_menos_C5": ("P2P", "C5"),
    "P2Pcol_menos_C1": ("P2P_colectivo", "C1"),
    "C4_menos_C1": ("C4", "C1"),
    "P2Pcol_menos_C4": ("P2P_colectivo", "C4"),
}
BRECHAS_INST = ("P2P_menos_C1", "P2P_menos_C4", "P2P_menos_C5")
TOL_PESO = 0.5
MATRIZ_CANON = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
                / "SALIDAS_SERVIDOR" / "matriz_reposo")
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "contrafactico_comercializador_2026-09-27"


def signo(v: float) -> str:
    """'+', '-' o '0' (dentro de medio peso)."""
    if not np.isfinite(v):
        raise ValueError(f"brecha no finita: {v!r}")
    return "0" if abs(v) <= TOL_PESO else ("+" if v > 0 else "-")


def exige_reparto_real() -> None:
    """Falla si el perfil tarifario no quedo en el regimen no regulado con el
    reparto real (el estado en que `prepara_caso` deja el modulo)."""
    from data.cedenar_tariff import (COMERCIALIZADOR, INSTITUTION_PROFILE,
                                     _PERFIL_NO_REGULADO)
    malos = {k: v.comercializador for k, v in INSTITUTION_PROFILE.items()
             if v.comercializador != COMERCIALIZADOR[k]}
    if dict(INSTITUTION_PROFILE) != _PERFIL_NO_REGULADO:
        malos["perfil"] = "no es el del regimen no regulado con el reparto real"
    if malos:
        raise RuntimeError(f"el reparto real no quedo restituido: {malos}")


def evalua_variante(evaluador, caso: str, datos, variante: str):
    """(ins, out, cr) de un caso con un comercializador; restituye siempre."""
    from data.cedenar_tariff import forzar_comercializador
    com = None if variante == "real" else variante
    try:
        ins = evaluador.prepara_caso(caso, datos, comercializador=com)
        out, cr = evaluador.evalua_comparacion(ins, comun.PUNTO_BASE)
    finally:
        forzar_comercializador(None)
    exige_reparto_real()
    if ins.comercializador != com:
        raise RuntimeError(f"{caso} {variante}: los insumos dicen "
                           f"{ins.comercializador!r}")
    return ins, out, cr


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True,
                       text=True, check=True)
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
    from gsa_directo import compuerta_punto_base as cpb

    malos = [c for c in args.casos if c not in comun.CASOS]
    if malos:
        raise SystemExit(f"casos desconocidos: {malos}")
    matriz = Path(args.matriz)
    registros = cpb._registros_de(matriz, None)
    if registros is None:
        raise SystemExit(f"no se hallan los registros D71 junto a {matriz}")
    ajenos = [c for c in args.casos
              if cpb.huella_libro(matriz / c) != cpb.HUELLAS_CANON[c]]
    if ajenos:
        raise SystemExit(f"la matriz no es la del canon 2026-09 en {ajenos}")
    mte_root = args.mte_root or comun.mte_root_defecto()
    if not Path(mte_root).is_dir():
        raise SystemExit(f"MTE_ROOT no es una carpeta: {mte_root}")
    salida = Path(args.salida)

    print("=" * 72)
    print("CONTRAFACTICO: UN SOLO COMERCIALIZADOR (art. 10 num. 1, CREG "
          "101 072), punto base")
    print("=" * 72)
    print(f"  matriz     {matriz}")
    print(f"  registros  {registros}")
    print(f"  MTE_ROOT   {mte_root}")
    t0 = time.time()
    datos = evaluador.carga_mte(mte_root, args.cache)
    print(f"  carga del MTE en {time.time() - t0:.1f} s")

    mec, brechas, inst, compuerta = [], [], [], []
    for caso in args.casos:
        base = {}
        for variante in VARIANTES:
            t1 = time.time()
            ins, out, cr = evalua_variante(evaluador, caso, datos, variante)
            seg = time.time() - t1
            if variante == "real":
                canon = cpb.lee_canon(matriz / caso, ins.nombres, registros,
                                      caso, canon_fijo=True)
                pa = {e: np.asarray(v, dtype=float)
                      for e, v in cr.net_benefit_per_agent.items()}
                net = {e: float(v) for e, v in cr.net_benefit.items()}
                filas = cpb.compara(caso, out, pa, net, canon, ins.nombres)
                compuerta.extend(filas)
                malas = [f for f in filas if not f[6]]
                if malas:
                    for f in malas:
                        print(f"  COMPUERTA {caso} DIFIERE {f[1]}: canon "
                              f"{f[2]:,.6f}  evaluado {f[3]:,.6f}")
                    print("CONTRAFACTICO COMERCIALIZADOR: la variante real NO "
                          "reproduce el canon; se detiene sin escribir")
                    return 1
            energia = float(out["energia"])
            fila = dict(caso=caso, variante=variante)
            fila.update({m: float(out[m]) for m in MECANISMOS})
            fila.update(
                energia_kWh=energia,
                parte_vendedor_almacen=float(out["parte_vendedor"]),
                horas_cuantales=int(out["n_cuantal"]),
                horas_mercado=int(out["n_horas_mercado"]),
                excedente_COP=float(out["excedente"]),
                # El ancho de banda: el nominal es el Cv medio (componente de
                # comercializar, CAL-47, con el factor del caso); el efectivo,
                # el excedente del mercado por kWh transado.
                cv_medio_COP_kWh=float(np.mean(ins.cvm)),
                techo_medio_COP_kWh=float(np.mean(ins.pi_gs)),
                pi_gs_eff_COP_kWh=float(ins.pi_gs_eff),
                ancho_efectivo_COP_kWh=(float(out["excedente"]) / energia
                                        if energia > 0 else float("nan")),
                seg=round(seg, 2))
            for n, nombre in enumerate(ins.nombres):
                fila[f"cv_medio_{nombre}"] = float(np.mean(ins.cvm[n]))
            no_finitos = [k for k, v in fila.items()
                          if isinstance(v, float) and not np.isfinite(v)
                          and not (k.startswith("ancho") and energia == 0)]
            if no_finitos:
                raise ValueError(f"{caso} {variante}: no finitos en "
                                 f"{no_finitos}")
            mec.append(fila)

            fb = dict(caso=caso, variante=variante)
            for b, (a, c) in BRECHAS.items():
                v = float(out[a]) - float(out[c])
                s = signo(v)
                if variante == "real":
                    base[b] = s
                fb[b] = v
                fb[f"signo_{b}"] = s
                fb[f"cambia_{b}"] = bool(s != base[b])
            brechas.append(fb)

            for nombre in ins.nombres:
                fi = dict(caso=caso, variante=variante, institucion=nombre)
                for b in BRECHAS_INST:
                    v = float(out[f"{b}__{nombre}"])
                    s = signo(v)
                    if variante == "real":
                        base[(nombre, b)] = s
                    fi[b] = v
                    fi[f"signo_{b}"] = s
                    fi[f"cambia_{b}"] = bool(s != base[(nombre, b)])
                inst.append(fi)

            print(f"  {caso:<5} {variante:<8} {seg:5.1f} s  P2P "
                  f"{out['P2P'] / 1e6:9.3f}  C1 {out['C1'] / 1e6:9.3f}  C4 "
                  f"{out['C4'] / 1e6:9.3f}  C5 {out['C5'] / 1e6:9.3f}  col "
                  f"{out['P2P_colectivo'] / 1e6:9.3f} MCOP  E "
                  f"{energia:10.1f} kWh  cuantal {int(out['n_cuantal'])}"
                  + ("  canon al peso" if variante == "real" else ""))

    dm = pd.DataFrame(mec)
    db = pd.DataFrame(brechas)
    di = pd.DataFrame(inst)
    dc = pd.DataFrame(compuerta, columns=["caso", "comprobacion", "canon",
                                          "evaluado", "dif", "tol", "ok"])
    # En `mecanismos` la columna `cv_medio_Udenar` queda vacia en SINU (no
    # esta Udenar); lo demas se comprobo fila a fila arriba.
    for nombre, df in (("brechas", db), ("por_institucion", di)):
        num = df.select_dtypes(include=[np.number])
        if not np.all(np.isfinite(num.to_numpy(dtype=float))):
            raise ValueError(f"{nombre}: hay valores no finitos")

    salida.mkdir(parents=True, exist_ok=True)
    dm.to_csv(salida / "mecanismos_13casos.csv", index=False,
              float_format="%.6f")
    db.to_csv(salida / "brechas_13casos.csv", index=False,
              float_format="%.6f")
    di.to_csv(salida / "por_institucion.csv", index=False,
              float_format="%.6f")
    dc.to_csv(salida / "compuerta_real.csv", index=False,
              float_format="%.6f")

    cambian = int(db[[f"cambia_{b}" for b in BRECHAS]].to_numpy().sum())
    cambian_i = int(di[[f"cambia_{b}" for b in BRECHAS_INST]]
                    .to_numpy().sum())
    orden = " ".join([Path(sys.executable).name, "-u",
                      "reformateo/documento/scripts/"
                      "contrafactico_comercializador.py"]
                     + (argv if argv is not None else sys.argv[1:]))
    sucio = git("status", "--short", "--", "scenarios", "analysis", "core",
                "gsa_directo", "data", "main_simulation.py")
    with open(salida / "procedencia.txt", "w", encoding="utf-8") as fh:
        fh.write("A2 / H-97: contrafactico de un solo comercializador "
                 "(art. 10 num. 1, CREG 101 072)\n")
        fh.write(f"fecha: {dt.datetime.now().isoformat(timespec='seconds')}\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("arbol de trabajo (codigo) con cambios sin commit:\n"
                 + (sucio or "(ninguno)") + "\n")
        fh.write(f"orden: {orden}\n")
        fh.write(f"MTE_ROOT: {mte_root}\n")
        fh.write(f"huella del dato: {comun.huella_datos(mte_root)}\n")
        fh.write(f"canon de comparacion: {matriz}\n")
        fh.write("punto: seis factores en 1, mu = 1 (evaluador del GSA "
                 "directo, prepara_caso(comercializador=...) y "
                 "evalua_comparacion)\n")
        fh.write(f"variantes: {' '.join(VARIANTES)}\n")
        fh.write(f"casos: {' '.join(args.casos)}\n")
        fh.write(f"compuerta de la variante real: {len(dc)} comprobaciones, "
                 f"todas al peso\n")
        fh.write(f"brechas de comunidad con signo distinto del real: "
                 f"{cambian}; por institucion: {cambian_i}\n")
    print(f"\n  escrito en {salida}")
    print(f"  compuerta de la variante real: {len(dc)} comprobaciones, todas "
          f"al peso")
    print(f"  signos que cambian respecto de real: {cambian} de comunidad, "
          f"{cambian_i} por institucion")
    print(f"CONTRAFACTICO COMERCIALIZADOR: variante real al peso con el canon "
          f"en {len(args.casos)} casos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
