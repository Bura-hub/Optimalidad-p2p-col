"""Cercanía a la infactibilidad y deserción unilateral hacia C1 (actividad 4.1).

Punto C7 de la preparación antes de redactar (2026-09-27); C-212.

La propuesta pide identificar «bajo qué condiciones el mercado P2P se vuelve
infactible o el método de solución deja de converger», cuánto «se acerca a la
infactibilidad ante perturbaciones extremas de precio» y «bajo qué relación
P_bolsa > P_P2P los vendedores tendrían incentivo a desertar». Se lee de las
muestras del GSA directo (12 casos, 150 528 evaluaciones, sin simular nada):

- CONVERGENCIA: evaluaciones fallidas (el método por reposo no falla si no hay
  ninguna; la fila `motivo` vacía).
- CERCANÍA A LA INFACTIBILIDAD: el mercado se «apaga» cuando pierde horas con
  intercambio o energía. Por intervalo de f_bolsa (el nivel de la bolsa antes
  del techo PES), la energía transada relativa a la del punto base, las horas
  con mercado y las horas «sin_ganancia» (D61).
- DESERCIÓN HORARIA: `retiros` (D67: un vendedor que vendería bajo su
  alternativa se retira de la hora). Si es cero en todas las filas, la
  restricción de participación del motor evita la deserción hora a hora.
- DESERCIÓN UNILATERAL HACIA C1: una institución preferiría salir del mercado
  y autogenerar sola si su P2P − C1 es negativo. Probabilidad por institución
  en la caja entera y por intervalo de f_bolsa.

Salida en SALIDAS_SERVIDOR/infactibilidad_desercion_2026-09-27/:
cercania_por_fbolsa.csv, desercion_c1.csv, desercion_c1_por_fbolsa.csv,
procedencia.txt.
"""
from __future__ import annotations

import datetime as dt
import glob
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
GSA = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_gsa_directo_completo_2026-09-27"
       / "SALIDAS_SERVIDOR" / "gsa_directo")
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "infactibilidad_desercion_2026-09-27"
CASOS = ["E0", "E2", "E4", "E1", "E3", "E5", "P1", "P2", "K1", "I1", "N1",
         "SINU"]
INST = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
CORTES = [0.75, 1.0, 1.5, 2.0, 3.0, 4.0]


def lee(caso: str) -> tuple[pd.DataFrame, dict]:
    fs = glob.glob(str(GSA / caso / f"muestras_{caso}_n*_s42.csv"))
    if len(fs) != 1:
        raise FileNotFoundError(f"{caso}: se esperaba un CSV de muestras, hay {fs}")
    d = pd.read_csv(fs[0], dtype={"motivo": str}, keep_default_na=True)
    base = pd.read_csv(GSA / "base" / "punto_base.csv")
    b = base[base["caso"] == caso]
    if len(b) != 1:
        raise ValueError(f"{caso}: falta su punto base")
    return d, b.iloc[0].to_dict()


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    cer, des, desb = [], [], []
    for caso in CASOS:
        d, b = lee(caso)
        fallidas = int(d["motivo"].fillna("").str.strip().ne("").sum())
        ok = d[d["motivo"].fillna("").str.strip().eq("")].copy()
        for col in ("energia", "n_horas_mercado", "n_sin_ganancia", "retiros"):
            if not np.isfinite(ok[col].to_numpy()).all():
                raise ValueError(f"{caso}: {col} no finito")
        e0 = float(b["energia"])
        ok["tramo"] = pd.cut(ok["f_bolsa"], CORTES, include_lowest=True)
        g = ok.groupby("tramo", observed=True).agg(
            filas=("energia", "size"),
            energia_rel_media=("energia", lambda s: s.mean() / e0),
            energia_rel_min=("energia", lambda s: s.min() / e0),
            horas_mercado_media=("n_horas_mercado", "mean"),
            sin_ganancia_media=("n_sin_ganancia", "mean"),
            sin_ganancia_max=("n_sin_ganancia", "max")).reset_index()
        g.insert(0, "caso", caso)
        g["tramo"] = g["tramo"].astype(str)
        g["evaluaciones_fallidas_caso"] = fallidas
        g["retiros_max_caso"] = float(ok["retiros"].max())
        cer.append(g)
        presentes = [i for i in INST if f"P2P_menos_C1__{i}" in ok.columns]
        if not presentes:
            raise ValueError(f"{caso}: sin columnas por institución")
        for inst in presentes:                    # SINU no tiene a Udenar
            col = f"P2P_menos_C1__{inst}"
            if not np.isfinite(ok[col].to_numpy()).all():
                raise ValueError(f"{caso}: {col} no finito")
            base_v = float(b[col])
            des.append(dict(caso=caso, institucion=inst, P2P_menos_C1_base=base_v,
                            p_desercion=float((ok[col] < 0).mean()),
                            minimo=float(ok[col].min())))
            h = ok.groupby("tramo", observed=True)[col].apply(
                lambda s: float((s < 0).mean())).reset_index(name="p_desercion")
            h.insert(0, "institucion", inst)
            h.insert(0, "caso", caso)
            h["tramo"] = h["tramo"].astype(str)
            desb.append(h)
    c = pd.concat(cer, ignore_index=True)
    dd = pd.DataFrame(des)
    db = pd.concat(desb, ignore_index=True)
    c.to_csv(SALIDA / "cercania_por_fbolsa.csv", index=False)
    dd.to_csv(SALIDA / "desercion_c1.csv", index=False)
    db.to_csv(SALIDA / "desercion_c1_por_fbolsa.csv", index=False)
    cabeza = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ,
                            capture_output=True, text=True, check=True
                            ).stdout.strip()
    (SALIDA / "procedencia.txt").write_text(
        f"guion: reformateo/documento/scripts/infactibilidad_desercion.py\n"
        f"codigo: {cabeza}\nfecha: {dt.datetime.now().isoformat(timespec='seconds')}\n"
        f"fuente: {GSA.relative_to(RAIZ).as_posix()} (canon 2026-09, bloque 9)\n",
        encoding="utf-8")
    print(f"  evaluaciones fallidas en los 12 casos: "
          f"{int(c.groupby('caso')['evaluaciones_fallidas_caso'].first().sum())}")
    print(f"  retiros máximos (D67): {c['retiros_max_caso'].max():g}")
    print("\n  energía relativa media por tramo de f_bolsa")
    print(c.pivot(index="caso", columns="tramo", values="energia_rel_media")
          .reindex(CASOS).round(3).to_string())
    print("\n  horas sin ganancia, media por tramo")
    print(c.pivot(index="caso", columns="tramo", values="sin_ganancia_media")
          .reindex(CASOS).round(1).to_string())
    print("\n  P(deserción hacia C1) en la caja, > 0")
    print(dd[dd.p_desercion > 0].round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
