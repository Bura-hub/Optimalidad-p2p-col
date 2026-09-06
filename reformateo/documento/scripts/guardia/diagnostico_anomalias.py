"""Diagnostico de las anomalias vistas en la primera pasada."""
import sys, pickle
from pathlib import Path
import numpy as np
import pandas as pd

SP = Path(sys.argv[1]); OUT = SP / "salidas"
RAIZ = Path(r"C:\Users\burav\Documentos\MaIE - UDENAR\Proyectos\SistemaBL\MedicionesMTE_v3")
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 50); pd.set_option("display.max_rows", 500)

datos = {}
for p in sorted(SP.glob("crudo_*.pkl")):
    with open(p, "rb") as f:
        df = pickle.load(f)
    nombre = p.stem.replace("crudo_", ""); inst = nombre.split("_")[0]
    datos[(inst, nombre[len(inst) + 1:].replace("_", " "))] = df
corto = lambda inst, med: f"{inst[:6]} {med.split('Medidor ')[1][0]}"

# 1. Frecuencia > 60.2: simultaneidad entre medidores
print("=== 1. EXCURSIONES DE FRECUENCIA fuera de 59.8-60.2: cuantos medidores las ven a la vez ===")
F = pd.DataFrame({corto(i, m): df["frequency"] for (i, m), df in datos.items()})
fuera = (F < 59.8) | (F > 60.2)
n_simult = fuera.sum(axis=1)
ev = F[n_simult > 0].copy(); ev["n_medidores"] = n_simult[n_simult > 0]
print(ev["n_medidores"].value_counts().sort_index().to_string())
print("\nInstantes con >=10 medidores fuera de banda (evento de sistema):")
print(ev[ev.n_medidores >= 10].round(2).to_string())
print("\nInstantes fuera de banda vistos por 1 a 3 medidores, resumen por medidor:")
solo = ev[ev.n_medidores <= 3]
for c in F.columns:
    s = solo[c][(solo[c] < 59.8) | (solo[c] > 60.2)]
    if len(s):
        print(f"  {c}: {len(s)} muestras; f entre {s.min():.2f} y {s.max():.2f}; fechas {s.index.min()} .. {s.index.max()}; "
              f"dias distintos={s.index.normalize().nunique()}")
# Mariana 2/3/4 a 60.6-60.77
print("\n--- Mariana 2/3/4 por encima de 60.5 Hz: que ve Mariana 1 en esos instantes, y P ---")
m2 = datos[("Mariana", "Medidor 2 - Alvernia - electricMeter")]; m1 = datos[("Mariana", "Medidor 1 - Alvernia - electricMeter")]
m3 = datos[("Mariana", "Medidor 3 - Alvernia - electricMeter")]; m4 = datos[("Mariana", "Medidor 4 - Alvernia - electricMeter")]
sel = m2.index[m2["frequency"] > 60.5]
tab = pd.DataFrame({"f_M2": m2.loc[sel, "frequency"], "f_M3": m3["frequency"].reindex(sel), "f_M4": m4["frequency"].reindex(sel),
                    "f_M1": m1["frequency"].reindex(sel), "P_M1": m1["totalActivePower"].reindex(sel),
                    "P_M2": m2.loc[sel, "totalActivePower"], "VA_M2": m2.loc[sel, "voltagePhaseA"], "VA_M1": m1["voltagePhaseA"].reindex(sel)})
print(f"{len(sel)} muestras; dias: {sorted(set(sel.normalize().strftime('%Y-%m-%d')))}")
print(tab.head(12).round(3).to_string()); print("..."); print(tab.tail(6).round(3).to_string())
# Todas las muestras de Mariana 2 fuera de banda: distribucion por dia
s = m2["frequency"][(m2["frequency"] < 59.8) | (m2["frequency"] > 60.2)]
print("\nMariana 2 fuera de banda por dia:"); print(s.groupby(s.index.normalize()).agg(["count", "min", "max"]).to_string())

# 2. Tension: eventos fuera de +-10% con nominal por muestra
print("\n=== 2. EVENTOS DE TENSION fuera de +-10 % (nominal por muestra: 127/220/440) ===")
def nominal_muestra(V):
    med = V.median(axis=1); cand = np.array([127.0, 220.0, 440.0])
    return pd.Series(cand[np.abs(med.values[:, None] - cand[None, :]).argmin(axis=1)], index=V.index)
for (inst, med), df in datos.items():
    V = df[["voltagePhaseA", "voltagePhaseB", "voltagePhaseC"]]; nom = nominal_muestra(V)
    fuera = (V.min(axis=1) < 0.9 * nom) | (V.max(axis=1) > 1.1 * nom)
    if not fuera.any():
        continue
    sub = df[fuera]
    # episodios: muestras separadas por <= 10 min
    t = sub.index.to_series(); ep = (t.diff() > pd.Timedelta("10min")).cumsum()
    print(f"\n{corto(inst, med)}: {int(fuera.sum())} muestras en {ep.nunique()} episodios")
    for e, g in sub.groupby(ep.values):
        Vg = g[["voltagePhaseA", "voltagePhaseB", "voltagePhaseC"]]
        print(f"  {g.index.min()} .. {g.index.max()}  n={len(g)}  VA/VB/VC min={Vg.min().round(1).tolist()} max={Vg.max().round(1).tolist()}  "
              f"P media={g['totalActivePower'].mean():.3f} kW  f=[{g['frequency'].min():.2f},{g['frequency'].max():.2f}]")
        if e > 12:
            print("  ..."); break

# 3. HUDN sobretension: perfil por hora del dia de la fraccion > +5 %
print("\n=== 3. HUDN 1: fraccion de muestras con alguna fase > 133.35 V (+5 % de 127) por hora del dia ===")
h1 = datos[("HUDN", "Medidor 1 - HUDN - electricMeter")]
alta = (h1[["voltagePhaseA", "voltagePhaseB", "voltagePhaseC"]].max(axis=1) > 133.35)
print((alta.groupby(h1.index.hour).mean() * 100).round(1).to_string())
print("Fraccion global HUDN 1 > +5 %:", round(alta.mean() * 100, 2), "%; por mes:")
print((alta.groupby(h1.index.to_period("M")).mean() * 100).round(1).to_string())

# 4. Cesmag 4: duplicados y regimenes
print("\n=== 4. CESMAG 4: archivos de origen, duplicados, regimenes de tension ===")
carp = RAIZ / "Cesmag" / "eletricMeter" / "Medidor 4 - Cesmag - electricMeter"
partes = []
for p in sorted(carp.glob("*.csv")):
    d = pd.read_csv(p, usecols=["date", "voltagePhaseA", "voltagePhaseB", "voltagePhaseC", "totalActivePower", "frequency"], low_memory=False)
    d["date"] = pd.to_datetime(d["date"], errors="coerce"); d = d.dropna(subset=["date"]); d["archivo"] = p.name[:30]
    print(f"  {p.name}: filas={len(d)} rango {d.date.min()} .. {d.date.max()}  dup internos={int(d.date.duplicated().sum())}")
    partes.append(d)
c4 = pd.concat(partes, ignore_index=True)
c4 = c4[(c4.date >= "2025-04-04") & (c4.date < "2025-12-16")]
dup = c4[c4.date.duplicated(keep=False)].sort_values("date")
print(f"  filas horizonte={len(c4)}; filas con instante repetido={len(dup)}")
if len(dup):
    g = dup.groupby("date")
    ident = g.agg(vA_rango=("voltagePhaseA", lambda s: s.max() - s.min()), P_rango=("totalActivePower", lambda s: s.max() - s.min()),
                  n=("voltagePhaseA", "size"), archivos=("archivo", lambda s: "|".join(sorted(set(s)))))
    print("  instantes repetidos:", len(ident), "; con lecturas identicas:", int(((ident.vA_rango == 0) & (ident.P_rango == 0)).sum()),
          "; con lecturas distintas:", int(((ident.vA_rango > 0) | (ident.P_rango > 0)).sum()))
    print("  rango de fechas de los repetidos:", ident.index.min(), "..", ident.index.max())
    print("  combinaciones de archivos:", ident.archivos.value_counts().head(5).to_dict())
    print("  ejemplo de instante con lecturas distintas:")
    ej = ident[(ident.vA_rango > 0)].head(3)
    for t in ej.index:
        print(dup[dup.date == t][["date", "archivo", "voltagePhaseA", "voltagePhaseB", "voltagePhaseC", "totalActivePower"]].to_string(index=False))
    print("  mediana de VA por regimen en los repetidos con lecturas distintas (archivo 1 vs 2):")
    dd = dup[dup.date.isin(ident[(ident.vA_rango > 0)].index)]
    print(dd.groupby("archivo")["voltagePhaseA"].describe().round(1).to_string())
c4u = c4.groupby("date").mean(numeric_only=True)
print("  mediana mensual de VA (tras promediar duplicados, como hace el pipeline):")
print(c4u["voltagePhaseA"].groupby(c4u.index.to_period("M")).median().round(1).to_string())
print("  fraccion de muestras con VA < 200 V por mes:")
print((c4u["voltagePhaseA"] < 200).groupby(c4u.index.to_period("M")).mean().round(3).to_string())

# 5. Udenar 3: por fase
print("\n=== 5. UDENAR 3: tension por fase ===")
u3 = datos[("Udenar", "Bloque Sur - Medidor 3 - electricMeter")]
print(u3[["voltagePhaseA", "voltagePhaseB", "voltagePhaseC", "currentPhaseA", "currentPhaseB", "currentPhaseC",
          "activePowerPhaseA", "activePowerPhaseB", "activePowerPhaseC", "totalActivePower"]].describe().round(3).to_string())

# 6. Discrepancias grandes de la suma de fases: contexto (rampas)
print("\n=== 6. |r| > 0.5 kW: contexto de rampa (P en t-1, t, t+1) ===")
for (inst, med), df in datos.items():
    P = df["totalActivePower"]; r = (df["activePowerPhaseA"] + df["activePowerPhaseB"] + df["activePowerPhaseC"]) - P
    sel = r.abs() > 0.5
    if not sel.any():
        continue
    print(f"\n{corto(inst, med)}: {int(sel.sum())} muestras")
    idx = np.where(sel.values)[0][:8]
    for i in idx:
        lo, hi = max(i - 1, 0), min(i + 2, len(df))
        w = df.iloc[lo:hi]
        print(f"  {df.index[i]}  r={r.iloc[i]:+.3f}  P[t-1,t,t+1]={P.iloc[lo:hi].round(3).tolist()}  "
              f"fases(t)={w.iloc[min(1, i - lo)][['activePowerPhaseA','activePowerPhaseB','activePowerPhaseC']].round(3).tolist()}")
print("\nLISTO DIAG")
