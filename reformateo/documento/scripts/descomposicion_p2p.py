"""Descomposición del beneficio monetario del mercado P2P (actividad 3.3).

Punto C5 de la preparación antes de redactar (2026-09-27); C-210.

La propuesta pide descomponer el bienestar del P2P en «beneficio monetario
directo» y beneficios intangibles. La parte monetaria se descompone aquí de
forma exacta, por institución y para la comunidad, leyendo solo los almacenes
del canon:

    P2P = C1 + banda del mercado + efecto de reclasificación

- C1: lo que la institución obtendría sola (autogeneración individual, art. 25).
- Banda del mercado: lo que el mercado reparte en cada intercambio. Al
  vendedor, su prima sobre su alternativa (`prima_vendedor`, medida contra el
  piso del juego; la del almacén, que es la publicable, regla 2 del canon); al
  comprador, su ahorro frente a su techo (`ahorro_comprador`).
- Efecto de reclasificación: el resto. Vender dentro de la comunidad cambia qué
  kWh del excedente residual quedan dentro del cupo mensual de permuta y cuáles
  van a bolsa (D3, C-177), y eso no es banda. En E0 es prácticamente cero
  (H-70: P2P − C1 = banda); con vendedores a bolsa no.

Sustituye como fuente de la descomposición a `fig13_desglose_flujos`, que omite
el crédito del art. 25 y reparte con la prima contra la bolsa (auditoría del
objetivo 3; punto D2).

Salida: SALIDAS_SERVIDOR/descomposicion_p2p_2026-09-27/ con
descomposicion_13casos.csv (caso, agente o «comunidad», P2P, C1, banda
vendedor, banda comprador, banda, reclasificación y P2P − C1) y procedencia.txt.
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
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "descomposicion_p2p_2026-09-27"
CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU"]
TOL_CANON = 0.5                                    # COP
# El almacén guarda en float32: sobre cientos de millones el redondeo es de
# unos pesos. Tolerancia relativa de una millonésima además de la absoluta.
TOL_REL = 1e-6


def caso(c: str) -> pd.DataFrame:
    alm = MATRIZ / c / "almacen" / "m1"
    esc = pd.read_parquet(alm / "escenarios")
    flu = pd.read_parquet(alm / "flujos")
    for col in ("valor",):
        if not np.isfinite(esc[col].to_numpy()).all():
            raise ValueError(f"{c}: escenarios con valores no finitos")
    for col in ("prima_vendedor", "ahorro_comprador"):
        if not np.isfinite(flu[col].to_numpy()).all():
            raise ValueError(f"{c}: flujos con {col} no finito")
    tot = esc.groupby(["escenario", "agente"])["valor"].sum()
    agentes = list(dict.fromkeys(esc["agente"]))
    bv = flu.groupby("vendedor")["prima_vendedor"].sum()
    bc = flu.groupby("comprador")["ahorro_comprador"].sum()
    filas = []
    for a in agentes:
        p2p, c1 = float(tot[("P2P", a)]), float(tot[("C1", a)])
        v, b = float(bv.get(a, 0.0)), float(bc.get(a, 0.0))
        filas.append(dict(caso=c, agente=a, P2P=p2p, C1=c1,
                          banda_vendedor=v, banda_comprador=b, banda=v + b,
                          reclasificacion=p2p - c1 - (v + b),
                          P2P_menos_C1=p2p - c1))
    df = pd.DataFrame(filas)
    com = df.drop(columns=["caso", "agente"]).sum()
    df = pd.concat([df, pd.DataFrame([dict(caso=c, agente="comunidad",
                                           **com.to_dict())])],
                   ignore_index=True)
    # El total de la comunidad tiene que ser el Resumen del canon.
    libro = MATRIZ / c / "outputs" / "resultados_comparacion.xlsx"
    res = pd.read_excel(libro, sheet_name="Resumen")
    w = dict(zip(res["Escenario"].astype(str), res["Ganancia_neta_COP"]))
    for e in ("P2P", "C1"):
        if abs(float(com[e]) - float(w[e])) > max(TOL_CANON,
                                                  TOL_REL * abs(float(w[e]))):
            raise ValueError(f"{c}: {e} del almacén {com[e]:.2f} no es el del "
                             f"Resumen {w[e]:.2f}")
    return df


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    df = pd.concat([caso(c) for c in CASOS], ignore_index=True)
    df.to_csv(SALIDA / "descomposicion_13casos.csv", index=False)
    cabeza = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ,
                            capture_output=True, text=True, check=True
                            ).stdout.strip()
    (SALIDA / "procedencia.txt").write_text(
        f"guion: reformateo/documento/scripts/descomposicion_p2p.py\n"
        f"codigo: {cabeza}\nfecha: {dt.datetime.now().isoformat(timespec='seconds')}\n"
        f"fuente: almacen/m1/escenarios y flujos de "
        f"{MATRIZ.relative_to(RAIZ).as_posix()} (canon 2026-09); la comunidad "
        f"reproduce P2P y C1 del Resumen (tolerancia {TOL_CANON} COP o {TOL_REL:g} relativa; el almacén va en float32)\n",
        encoding="utf-8")
    com = df[df.agente == "comunidad"].set_index("caso")
    ver = com[["P2P_menos_C1", "banda", "banda_vendedor", "banda_comprador",
               "reclasificacion"]] / 1e6
    ver["reclas_%_de_P2P-C1"] = 100 * com.reclasificacion / com.P2P_menos_C1
    print("  comunidad, en millones de COP")
    print(ver.round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
