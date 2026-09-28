"""Precio de la justicia del par P2P frente a C4 en los 13 casos (actividad 3.3).

Punto C2 de la preparación antes de redactar (2026-09-27).

La propuesta define el PoF como «la pérdida relativa de bienestar social al
imponer una restricción de equidad» (Bertsimas, Farias y Trichakis, 2011) y
pide que «compare la eficiencia del mercado P2P con la equidad del escenario
C4 (PDE estático)». La hoja `PoF_Fairness` del canon lo da para cada mecanismo
frente al más eficiente, pero no tabula el par, y rotula como eficiente a C2
cuando empata con P2P al redondeo (CAL-52). Este guion lo lee del canon sin
simular nada:

  PoF(P2P → C4) = (W_P2P − W_C4) / W_P2P

con W el beneficio neto de la comunidad (hoja `Resumen`) y la equidad medida
con el Gini del beneficio por institución (hoja `PoF_Fairness`). Clasifica cada
caso:

  - «intercambio»: C4 es más equitativo (Gini menor) y menos eficiente; el PoF
    es el costo de su equidad;
  - «P2P domina»: el P2P es a la vez más eficiente y más equitativo; no hay
    precio que pagar;
  - «C4 domina», si ocurriera; cualquier otra combinación (p. ej. empate
    exacto) sale como «otro» y se revisa a mano.

Añade, como magnitud distinta, la pérdida de asignación interna del mercado de
D55 (1 − captura agregada, de los almacenes), que el núcleo también llama
precio de la justicia.

Salida: SALIDAS_SERVIDOR/precio_justicia_2026-09-27/pof_p2p_c4_13casos.csv y
procedencia.txt.
"""
from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
MATRIZ = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
          / "SALIDAS_SERVIDOR" / "matriz_reposo")
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "precio_justicia_2026-09-27"
CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU"]
TOL_GINI = 1e-9


def lee(caso: str) -> dict:
    libro = MATRIZ / caso / "outputs" / "resultados_comparacion.xlsx"
    if not libro.is_file():
        raise FileNotFoundError(f"falta {libro}")
    res = pd.read_excel(libro, sheet_name="Resumen")
    w = {str(e): float(v) for e, v in zip(res["Escenario"],
                                          res["Ganancia_neta_COP"])}
    pof = pd.read_excel(libro, sheet_name="PoF_Fairness").set_index("escenario")
    g = {e: float(pof.loc[e, "gini"]) for e in ("P2P", "C4")}
    h = pd.read_parquet(MATRIZ / caso / "almacen" / "m1" / "horas")
    h = h[h["regimen"].notna() & (h["excedente_optimo"] > 0)]
    opt = float(h["excedente_optimo"].sum())
    cap_agr = float((h["captura"] * h["excedente_optimo"]).sum() / opt)
    for v in (*w.values(), *g.values(), cap_agr):
        if not np.isfinite(v):
            raise ValueError(f"{caso}: valor no finito")
    return dict(W_P2P=w["P2P"], W_C4=w["C4"], gini_P2P=g["P2P"],
                gini_C4=g["C4"], captura_agregada=cap_agr)


def clase(d: dict) -> str:
    mas_eficiente = d["W_P2P"] - d["W_C4"]
    mas_equitativo_c4 = d["gini_P2P"] - d["gini_C4"]
    if mas_eficiente > 0 and mas_equitativo_c4 > TOL_GINI:
        return "intercambio"
    if mas_eficiente >= 0 and mas_equitativo_c4 <= TOL_GINI:
        return "P2P domina"
    if mas_eficiente < 0 and mas_equitativo_c4 > TOL_GINI:
        return "C4 domina"
    return "otro"


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    filas = []
    for caso in CASOS:
        d = lee(caso)
        d["PoF_P2P_a_C4"] = (d["W_P2P"] - d["W_C4"]) / d["W_P2P"]
        d["clase"] = clase(d)
        d["perdida_asignacion_D55"] = 1.0 - d["captura_agregada"]
        filas.append(dict(caso=caso, **d))
    df = pd.DataFrame(filas)
    df.to_csv(SALIDA / "pof_p2p_c4_13casos.csv", index=False)
    cabeza = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ,
                            capture_output=True, text=True, check=True
                            ).stdout.strip()
    (SALIDA / "procedencia.txt").write_text(
        f"guion: reformateo/documento/scripts/precio_justicia_p2p_c4.py\n"
        f"codigo: {cabeza}\nfecha: {dt.datetime.now().isoformat(timespec='seconds')}\n"
        f"fuente: hojas Resumen y PoF_Fairness y almacen/m1/horas de "
        f"{MATRIZ.relative_to(RAIZ).as_posix()} (canon 2026-09)\n",
        encoding="utf-8")
    ver = df.copy()
    ver["W_P2P"] = ver["W_P2P"] / 1e6
    ver["W_C4"] = ver["W_C4"] / 1e6
    ver["PoF_P2P_a_C4"] = 100 * ver["PoF_P2P_a_C4"]
    ver["perdida_asignacion_D55"] = 100 * ver["perdida_asignacion_D55"]
    print(ver[["caso", "W_P2P", "W_C4", "gini_P2P", "gini_C4", "PoF_P2P_a_C4",
               "clase", "perdida_asignacion_D55"]].round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
