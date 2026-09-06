"""Carga el crudo a dos minutos de los 20 medidores, solo columnas del guardia,
solo horizonte canonico. Salida: pickle por medidor en el scratchpad."""
import sys, time, pickle
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(r"C:\Users\burav\Documentos\MaIE - UDENAR\Proyectos\SistemaBL")
MTE = RAIZ / "MedicionesMTE_v3"
SP = Path(sys.argv[1])
T0, T1 = "2025-04-04", "2025-12-16"

COLS = ["date", "frequency", "outputStatus",
        "currentPhaseA", "currentPhaseB", "currentPhaseC", "neutralCurrent",
        "voltagePhaseA", "voltagePhaseB", "voltagePhaseC",
        "totalActivePower", "activePowerPhaseA", "activePowerPhaseB", "activePowerPhaseC",
        "totalPowerFactor", "powerFactorPhaseA", "powerFactorPhaseB", "powerFactorPhaseC",
        "totalApparentPower", "totalReactivePower",
        "currentActivePowerDemand", "cumulativeActivePower"]

METER_FOLDER = {"Udenar": "electricMeter", "Mariana": "electricMeter",
                "UCC": "electricMeter", "HUDN": "electricMeter", "Cesmag": "eletricMeter"}

def leer(path):
    raw = path.read_bytes()
    enc = "utf-8"
    for e in ["utf-8-sig", "utf-8", "cp1252", "latin-1"]:
        try:
            raw.decode(e); enc = e; break
        except Exception:
            pass
    df = pd.read_csv(path, encoding=enc, low_memory=False, on_bad_lines="skip",
                     usecols=lambda c: c in COLS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    for c in df.columns:
        if c != "date":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

resumen = []
t_ini = time.time()
for inst, mf in METER_FOLDER.items():
    root = MTE / inst / mf
    for sub in sorted(root.iterdir()):
        if not sub.is_dir():
            continue
        partes = [leer(p) for p in sorted(sub.glob("*.csv"))]
        df = pd.concat(partes, ignore_index=True)
        n_total = len(df)
        df = df[(df["date"] >= T0) & (df["date"] < T1)]
        n_hor = len(df)
        n_dup = int(df["date"].duplicated().sum())
        # duplicados de instante: se funden promediando, como hace el pipeline (P-17)
        df = df.groupby("date", sort=True).mean()
        n_uni = len(df)
        # rejilla: cuantos instantes no caen en el minuto par
        no_par = int((df.index.minute % 2 != 0).sum() + (df.index.second != 0).sum())
        nombre = sub.name
        with open(SP / f"crudo_{inst}_{nombre.replace(' ', '_')}.pkl", "wb") as f:
            pickle.dump(df, f, protocol=5)
        resumen.append(dict(inst=inst, medidor=nombre, filas_archivo=n_total,
                            filas_horizonte=n_hor, duplicados=n_dup, instantes_unicos=n_uni,
                            instantes_fuera_rejilla=no_par,
                            t_min=str(df.index.min()), t_max=str(df.index.max())))
        print(f"{inst:8s} {nombre:45s} filas={n_total:8d} horiz={n_hor:7d} dup={n_dup:5d} "
              f"unicos={n_uni:7d} no_par={no_par}  [{time.time()-t_ini:5.0f}s]", flush=True)

pd.DataFrame(resumen).to_csv(SP / "carga_resumen.csv", index=False)
print("LISTO", flush=True)
