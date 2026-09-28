"""El efecto de cruzar el umbral de 100 kW por planta: E4 frente a 7 × P1.

Punto C8 de la preparación antes de redactar (2026-09-27); actividad 4.1; C-213.

Diseño de la matriz de escalado (D10 a D12, spec 4.12): E4 multiplica la
generación por 7 (plantas de 122,85 kW, sobre el umbral del art. 25 num. 2 de la
CREG 174) y P1 divide la demanda por 7 (el mismo patrón de cobertura con las
plantas de 17,55 kW, bajo el umbral). La clasificación del art. 25 y el volumen
son homogéneos de grado uno en (G, D), de modo que, salvo en los umbrales,
E4 = 7 × P1 en energía y en dinero. La diferencia E4 − 7 × P1 de cada mecanismo
aísla lo que cuesta cruzar el umbral: la permuta de cada planta pasa a pagar
T + D + Cv + PR + R en lugar de solo Cv. C4 ya está en el caso 2 del art. 20 en
los dos casos (cinco fronteras, reparto del 20 %), y C5 exime al usuario de esos
límites (CREG 101 099, art. 16 ii).

Lee la hoja `Resumen` y `Por_agente` de los dos casos del canon. Salida en
SALIDAS_SERVIDOR/umbral_100kw_2026-09-27/umbral_100kw.csv y procedencia.txt.
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
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "umbral_100kw_2026-09-27"
MECANISMOS = ["P2P", "P2P_colectivo", "C1", "C2", "C3", "C4", "C5"]
FACTOR = 7.0


def resumen(caso: str) -> dict:
    libro = MATRIZ / caso / "outputs" / "resultados_comparacion.xlsx"
    r = pd.read_excel(libro, sheet_name="Resumen")
    w = {str(e): float(v) for e, v in zip(r["Escenario"], r["Ganancia_neta_COP"])}
    for e in MECANISMOS:
        if not np.isfinite(w[e]):
            raise ValueError(f"{caso}: {e} no finito")
    return w


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    e4, p1 = resumen("E4"), resumen("P1")
    filas = []
    for e in MECANISMOS:
        filas.append(dict(mecanismo=e, E4=e4[e], P1_por_7=FACTOR * p1[e],
                          efecto_umbral=e4[e] - FACTOR * p1[e],
                          efecto_pct=100 * (e4[e] - FACTOR * p1[e])
                          / abs(FACTOR * p1[e])))
    df = pd.DataFrame(filas)
    for x, y in (("P2P", "C1"), ("P2P", "C4"), ("P2P", "C5"),
                 ("P2P_colectivo", "C4"), ("C4", "C1")):
        a = df.set_index("mecanismo")
        filas.append(dict(mecanismo=f"{x} - {y}",
                          E4=a.loc[x, "E4"] - a.loc[y, "E4"],
                          P1_por_7=a.loc[x, "P1_por_7"] - a.loc[y, "P1_por_7"],
                          efecto_umbral=a.loc[x, "efecto_umbral"]
                          - a.loc[y, "efecto_umbral"], efecto_pct=np.nan))
    df = pd.DataFrame(filas)
    df.to_csv(SALIDA / "umbral_100kw.csv", index=False)
    cabeza = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ,
                            capture_output=True, text=True, check=True
                            ).stdout.strip()
    (SALIDA / "procedencia.txt").write_text(
        f"guion: reformateo/documento/scripts/umbral_100kw.py\n"
        f"codigo: {cabeza}\nfecha: {dt.datetime.now().isoformat(timespec='seconds')}\n"
        f"fuente: hoja Resumen de E4 y P1 en {MATRIZ.relative_to(RAIZ).as_posix()} "
        f"(canon 2026-09)\n", encoding="utf-8")
    v = df.copy()
    for c in ("E4", "P1_por_7", "efecto_umbral"):
        v[c] = v[c] / 1e6
    print(v.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
