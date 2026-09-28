"""El peso de la regla declarada de despacho de vendedores (D64), en los 13 casos.

Actividad 1.1. Punto C1 de la preparación antes de redactar (2026-09-27),
segunda parte; C-207.

La validación dinámica no alcanzó el régimen «compradores_cortos», que lleva
el 24 % de la energía de la matriz (ver `energia_por_regimen.py`). Ahí la
energía la fija el lado corto, sea cual sea la regla; lo que la regla
declarada decide es qué vendedor despacha (D64). Este guion mide cuánto se
mueven los beneficios y las brechas si el despacho sigue otra regla: «costo»
(por costo b_j creciente, el mérito de D52) o «llenado» (por niveles entre
todos), frente a «piso», la de la matriz canónica.

Evalúa con el evaluador del GSA en el punto base (factores en 1, μ = 1). La
variante «piso» tiene que reproducir al peso la hoja `Resumen` del canon.

Salida en SALIDAS_SERVIDOR/peso_regla_despacho_2026-09-27/:
  mecanismos.csv       caso, regla, beneficio de cada mecanismo y energía
  brechas.csv          caso, regla, brechas de comunidad y su cambio frente a «piso»
  por_institucion.csv  caso, regla, institución, P2P, P2P − C1, P2P − C4
  procedencia.txt

Uso:
    .venv/Scripts/python.exe reformateo/documento/scripts/peso_regla_despacho.py
"""
from __future__ import annotations

import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from gsa_directo import comun, evaluador  # noqa: E402

MATRIZ = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
          / "SALIDAS_SERVIDOR" / "matriz_reposo")
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "peso_regla_despacho_2026-09-27"
REGLAS = ("piso", "costo", "llenado")
MECANISMOS = ("P2P", "P2P_colectivo", "C1", "C2", "C3", "C4", "C5")
BRECHAS = {"P2P_menos_C1": ("P2P", "C1"), "P2P_menos_C4": ("P2P", "C4"),
           "P2P_menos_C5": ("P2P", "C5"),
           "P2Pcol_menos_C1": ("P2P_colectivo", "C1"),
           "P2Pcol_menos_C4": ("P2P_colectivo", "C4")}
TOL_PESO = 0.5                       # COP: «al peso»


def resumen_canon(caso: str) -> dict:
    libro = MATRIZ / caso / "outputs" / "resultados_comparacion.xlsx"
    if not libro.is_file():
        raise FileNotFoundError(f"falta el libro del canon de {caso}: {libro}")
    res = pd.read_excel(libro, sheet_name="Resumen")
    return {str(e): float(v) for e, v in
            zip(res["Escenario"], res["Ganancia_neta_COP"])}


def main() -> int:
    comun.salida_utf8()
    SALIDA.mkdir(parents=True, exist_ok=True)
    mte_root = comun.mte_root_defecto()
    datos = evaluador.carga_mte(mte_root, None)
    mec, bre, inst, fuera = [], [], [], []
    for caso in comun.ORDEN_CASOS:
        ins = evaluador.prepara_caso(caso, datos)
        canon = resumen_canon(caso)
        base = None
        for regla in REGLAS:
            t0 = time.time()
            out, cr = evaluador.evalua_comparacion(ins, comun.PUNTO_BASE,
                                                   despacho=regla)
            nb = {e: float(cr.net_benefit[e]) for e in MECANISMOS}
            if not all(np.isfinite(v) for v in nb.values()):
                raise ValueError(f"{caso}/{regla}: beneficio no finito")
            if regla == "piso":
                for e in MECANISMOS:
                    if abs(nb[e] - canon[e]) > TOL_PESO:
                        fuera.append((caso, e, nb[e], canon[e]))
                base = nb
            mec.append(dict(caso=caso, regla=regla, energia_kwh=out["energia"],
                            parte_vendedor=out["parte_vendedor"], **nb))
            fila = dict(caso=caso, regla=regla)
            for b, (x, y) in BRECHAS.items():
                v, v0 = nb[x] - nb[y], base[x] - base[y]
                fila[b] = v
                fila[f"cambio_{b}"] = v - v0
                fila[f"signo_cambia_{b}"] = bool(np.sign(v) != np.sign(v0))
            bre.append(fila)
            for n, nombre in enumerate(ins.nombres):
                p2p = float(cr.net_benefit_per_agent["P2P"][n])
                inst.append(dict(
                    caso=caso, regla=regla, institucion=nombre, P2P=p2p,
                    P2P_menos_C1=p2p - float(cr.net_benefit_per_agent["C1"][n]),
                    P2P_menos_C4=p2p - float(cr.net_benefit_per_agent["C4"][n])))
            print(f"  {caso:5} {regla:8} P2P {nb['P2P']:16,.0f}  "
                  f"energía {out['energia']:10.2f}  ({time.time() - t0:.1f} s)")
    if fuera:
        for f in fuera:
            print(f"  FUERA DEL PESO: {f}")
        raise SystemExit("la regla «piso» no reproduce el canon: se detiene")

    pd.DataFrame(mec).to_csv(SALIDA / "mecanismos.csv", index=False)
    bdf = pd.DataFrame(bre)
    bdf.to_csv(SALIDA / "brechas.csv", index=False)
    idf = pd.DataFrame(inst)
    base = idf[idf.regla == "piso"].set_index(["caso", "institucion"])
    for regla in ("costo", "llenado"):
        r = idf[idf.regla == regla].set_index(["caso", "institucion"])
        idf.loc[idf.regla == regla, "signo_cambia_P2P_menos_C4"] = (
            np.sign(r["P2P_menos_C4"]) != np.sign(base["P2P_menos_C4"])).values
    idf.to_csv(SALIDA / "por_institucion.csv", index=False)

    cabeza = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ,
                            capture_output=True, text=True, check=True
                            ).stdout.strip()
    sucio = subprocess.run(["git", "status", "--porcelain", "gsa_directo"],
                           cwd=RAIZ, capture_output=True, text=True,
                           check=True).stdout.strip()
    (SALIDA / "procedencia.txt").write_text(
        f"guion: reformateo/documento/scripts/peso_regla_despacho.py\n"
        f"codigo: {cabeza}{' (con cambios sin commit en gsa_directo)' if sucio else ''}\n"
        f"fecha: {dt.datetime.now().isoformat(timespec='seconds')}\n"
        f"MTE_ROOT: {mte_root}\nhuella del dato: {comun.huella_datos(mte_root)}\n"
        f"reglas: {REGLAS}; «piso» reproduce el Resumen del canon al peso "
        f"(tolerancia {TOL_PESO} COP)\n", encoding="utf-8")

    print("\n  cambio de las brechas de comunidad frente a «piso» (COP)")
    cols = ["caso", "regla"] + [f"cambio_{b}" for b in BRECHAS]
    print(bdf[bdf.regla != "piso"][cols].round(0).to_string(index=False))
    n_sig = int(bdf[[f"signo_cambia_{b}" for b in BRECHAS]].to_numpy().sum())
    print(f"\n  brechas de comunidad que cambian de signo: {n_sig}")
    ch = idf[idf.regla != "piso"]["signo_cambia_P2P_menos_C4"].sum()
    print(f"  pares institución-caso que cambian de signo en P2P − C4: {int(ch)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
