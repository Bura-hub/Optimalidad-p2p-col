"""Medicion del guardia fisico sobre los 20 medidores, paso de dos minutos.
Solo lee los pickles del scratchpad; no toca el proyecto."""
import sys, pickle
from pathlib import Path
import numpy as np
import pandas as pd

SP = Path(sys.argv[1])
OUT = SP / "salidas"; OUT.mkdir(exist_ok=True)
T0, T1 = "2025-04-04", "2025-12-16"
IDX = pd.date_range(T0, T1, freq="1h", inclusive="left")   # 6144 h

# Series que usa el pipeline
M1 = {"Udenar": "Bloque Sur - Medidor 1 - electricMeter", "Mariana": "Medidor 1 - Alvernia - electricMeter",
      "UCC": "Medidor 1 - UCC - electricMeter", "HUDN": "Medidor 1 - HUDN - electricMeter",
      "Cesmag": "Medidor 1 - Cesmag - electricMeter"}
M3 = {"Udenar": "Bloque Sur - Medidor 3 - electricMeter", "Mariana": "Medidor 1 - Alvernia - electricMeter",
      "UCC": "Medidor 3 - UCC - electricMeter", "HUDN": "Medidor 3 - HUDN - electricMeter",
      "Cesmag": "Medidor 3 - Cesmag - electricMeter"}
# Las once horas que el criterio viejo retira (frontera, institucion, hora)
ONCE = [("M1", "Mariana", "2025-04-24 08:00"), ("M1", "Mariana", "2025-04-24 09:00"),
        ("M1", "Mariana", "2025-04-24 10:00"), ("M1", "Mariana", "2025-10-01 09:00"),
        ("M3", "Mariana", "2025-04-24 08:00"), ("M3", "Mariana", "2025-04-24 09:00"),
        ("M3", "Mariana", "2025-04-24 10:00"), ("M3", "Mariana", "2025-10-01 09:00"),
        ("M3", "Mariana", "2025-08-14 08:00"),
        ("M3", "Cesmag", "2025-04-04 09:00"), ("M3", "Cesmag", "2025-05-09 09:00")]

Q = [0, 0.001, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999, 1.0]


def qdict(s, pref):
    s = s.dropna()
    d = {f"{pref}_n": len(s)}
    if len(s):
        qs = s.quantile(Q)
        for q, v in zip(Q, qs):
            d[f"{pref}_q{q:g}"] = float(v)
    return d


datos = {}
for p in sorted(SP.glob("crudo_*.pkl")):
    with open(p, "rb") as f:
        df = pickle.load(f)
    nombre = p.stem.replace("crudo_", "")
    inst = nombre.split("_")[0]
    medidor = nombre[len(inst) + 1:].replace("_", " ")
    datos[(inst, medidor)] = df

print(f"{len(datos)} medidores cargados", flush=True)

# ───────────────────────── 1. Caracterizacion ─────────────────────────
carac = []
for (inst, med), df in datos.items():
    V = df[["voltagePhaseA", "voltagePhaseB", "voltagePhaseC"]]
    vmed = float(np.nanmedian(V.values))
    nominal = 127.0 if abs(vmed - 127) < abs(vmed - 120) else 120.0
    P = df["totalActivePower"]
    PA, PB, PC = df["activePowerPhaseA"], df["activePowerPhaseB"], df["activePowerPhaseC"]
    r = (PA + PB + PC) - P
    fila = dict(inst=inst, medidor=med, n_muestras=len(df), v_mediana_3f=vmed, nominal_supuesto=nominal)
    fila.update(qdict(V.min(axis=1), "Vmin3f")); fila.update(qdict(V.max(axis=1), "Vmax3f"))
    fila["V_muestras_alguna_fase_cero"] = int((V <= 0.5).any(axis=1).sum())
    fila["V_muestras_tres_fases_cero"] = int((V <= 0.5).all(axis=1).sum())
    fila["V_muestras_nan_alguna"] = int(V.isna().any(axis=1).sum())
    fila.update(qdict(df["frequency"], "f"))
    fila["f_muestras_cero"] = int((df["frequency"] <= 1).sum()); fila["f_nan"] = int(df["frequency"].isna().sum())
    fila.update(qdict(df["totalPowerFactor"], "PF"))
    fila["PF_negativos"] = int((df["totalPowerFactor"] < 0).sum())
    fila["PF_mayor_1"] = int((df["totalPowerFactor"] > 1.0001).sum())
    fila["P_negativos"] = int((P < 0).sum()); fila["P_nan"] = int(P.isna().sum())
    fila.update(qdict(P, "P"))
    fila.update(qdict(r, "r")); fila.update(qdict(r.abs(), "absr"))
    rel = (r.abs() / P.abs().clip(lower=0.05))
    fila.update(qdict(rel, "relr"))
    for c, k in [("totalActivePower", "res_P"), ("activePowerPhaseA", "res_PA")]:
        u = np.sort(df[c].dropna().unique()); d = np.diff(u); d = d[d > 1e-9]
        fila[k] = float(d.min()) if len(d) else np.nan
    fila["outputStatus_valores"] = str(sorted(df["outputStatus"].dropna().unique().tolist())[:10])
    fila["n_fases_nan"] = int((PA.isna() | PB.isna() | PC.isna()).sum())
    carac.append(fila)
carac = pd.DataFrame(carac)
carac.to_csv(OUT / "caracterizacion.csv", index=False)

# ruido de la suma de fases por nivel de potencia
filas = []
for (inst, med), df in datos.items():
    P = df["totalActivePower"]
    r = (df["activePowerPhaseA"] + df["activePowerPhaseB"] + df["activePowerPhaseC"]) - P
    ok = P.notna() & r.notna()
    P, r = P[ok], r[ok]
    bins = [-np.inf, 0, 0.5, 1, 2, 5, 10, 20, 50, 100, np.inf]
    cat = pd.cut(P.abs(), bins)
    g = pd.DataFrame({"absP": P.abs(), "r": r, "cat": cat}).groupby("cat", observed=True)
    for c, sub in g:
        relv = sub.r.abs() / sub.absP.clip(lower=0.05)
        filas.append(dict(inst=inst, medidor=med, nivel=str(c), n=len(sub), r_mediana=sub.r.median(),
                          r_mad=float((sub.r - sub.r.median()).abs().median()),
                          absr_p50=sub.r.abs().quantile(0.5), absr_p99=sub.r.abs().quantile(0.99),
                          absr_p999=sub.r.abs().quantile(0.999), absr_max=sub.r.abs().max(),
                          rel_p50=relv.quantile(0.5), rel_p99=relv.quantile(0.99), rel_max=relv.max()))
pd.DataFrame(filas).to_csv(OUT / "ruido_suma_fases_por_nivel.csv", index=False)


# ───────────────────────── 2. Banderas por muestra ─────────────────────────
def banderas(df, nominal):
    V = df[["voltagePhaseA", "voltagePhaseB", "voltagePhaseC"]]
    vmin, vmax = V.min(axis=1), V.max(axis=1)
    f = df["frequency"]; pf = df["totalPowerFactor"]; P = df["totalActivePower"]
    r = (df["activePowerPhaseA"] + df["activePowerPhaseB"] + df["activePowerPhaseC"]) - P
    absP = P.abs()
    B = {}
    for lo, hi, tag in [(-10, 5, "V_ntc1340_-10+5"), (-10, 10, "V_pm10"), (-8, 8, "V_pm8"),
                        (-5, 5, "V_pm5"), (-15, 15, "V_pm15"), (-50, 50, "V_pm50")]:
        B[tag] = (vmin < nominal * (1 + lo / 100)) | (vmax > nominal * (1 + hi / 100))
    B["V_alguna_fase_nan"] = V.isna().any(axis=1)
    for lo, hi, tag in [(59.8, 60.2, "f_creg025_59.8-60.2"), (59.9, 60.1, "f_59.9-60.1"),
                        (59.7, 60.3, "f_59.7-60.3"), (59.5, 60.5, "f_59.5-60.5"), (59.0, 61.0, "f_59-61")]:
        B[tag] = (f < lo) | (f > hi)
    B["f_nan"] = f.isna()
    for th in [0.894, 0.9, 0.85, 0.8, 0.7, 0.5]:
        B[f"PF_lt_{th}"] = pf.abs() < th
        B[f"PF_lt_{th}_P>1kW"] = (pf.abs() < th) & (absP > 1.0)
    B["PF_nan"] = pf.isna()
    for rel, piso, tag in [(0.01, 0.02, "S_1pct"), (0.02, 0.02, "S_2pct"), (0.05, 0.05, "S_5pct"),
                           (0.10, 0.05, "S_10pct"), (0.20, 0.10, "S_20pct"), (0.50, 0.10, "S_50pct")]:
        B[tag] = r.abs() > np.maximum(piso, rel * absP)
    for k, tag in [(0.1, "S_abs_0.1kW"), (0.5, "S_abs_0.5kW"), (1.0, "S_abs_1kW"), (5.0, "S_abs_5kW")]:
        B[tag] = r.abs() > k
    B["S_nan"] = r.isna() & P.notna()
    B = pd.DataFrame(B, index=df.index).fillna(False).astype(bool)
    return B, P


censo = []
detalle_muestra = {}
for (inst, med), df in datos.items():
    nominal = float(carac.loc[(carac.inst == inst) & (carac.medidor == med), "nominal_supuesto"].iloc[0])
    B, P = banderas(df, nominal)
    detalle_muestra[(inst, med)] = (B, P)
    hora = df.index.floor("h")
    n_por_hora = pd.Series(1, index=df.index).groupby(hora).sum().reindex(IDX, fill_value=0)
    horas_vacias = int((n_por_hora == 0).sum())
    horas_incompletas = int(((n_por_hora > 0) & (n_por_hora < 30)).sum())
    for col in B.columns:
        m = B[col]
        nm = int(m.sum())
        h_marc = pd.Series(m.values, index=hora).groupby(level=0).sum()
        h_marc = h_marc[h_marc > 0]
        restantes = (n_por_hora.reindex(h_marc.index) - h_marc)
        if nm:
            g = pd.DataFrame({"P": P.values, "m": m.values}, index=hora)
            media_todo = g.groupby(level=0)["P"].mean()
            media_sin = g[~g.m].groupby(level=0)["P"].mean()
            hh = h_marc.index
            delta = (media_sin.reindex(hh) - media_todo.reindex(hh))
            energia_horas = float(media_todo.reindex(hh).sum())
            delta_sum = float(delta.fillna(-media_todo.reindex(hh)).sum())
        else:
            energia_horas = 0.0; delta_sum = 0.0
        censo.append(dict(inst=inst, medidor=med, bandera=col, muestras=nm, horas=int(len(h_marc)),
                          horas_quedan_lt23=int((restantes < 23).sum()), horas_quedan_0=int((restantes == 0).sum()),
                          muestras_medidor=len(df), horas_vacias_medidor=horas_vacias,
                          horas_incompletas_medidor=horas_incompletas,
                          energia_kWh_horas_marcadas=energia_horas, delta_kWh_si_quito_muestras=delta_sum))
censo = pd.DataFrame(censo)
censo.to_csv(OUT / "censo_por_medidor.csv", index=False)
cols_sum = ["muestras", "horas", "horas_quedan_lt23", "horas_quedan_0",
            "energia_kWh_horas_marcadas", "delta_kWh_si_quito_muestras"]
censo.groupby("bandera")[cols_sum].sum().to_csv(OUT / "censo_total_20_medidores.csv")

filas = []
for front, cfg in [("M1", M1), ("M3", M3)]:
    for inst, med in cfg.items():
        sub = censo[(censo.inst == inst) & (censo.medidor == med)].copy()
        sub.insert(0, "frontera", front)
        filas.append(sub)
censo_pipe = pd.concat(filas)
censo_pipe.to_csv(OUT / "censo_series_pipeline.csv", index=False)
censo_pipe.groupby(["frontera", "bandera"])[cols_sum].sum().to_csv(OUT / "censo_pipeline_total.csv")

# ───────────────────────── 3. Las once horas ─────────────────────────
filas = []
for front, inst, h in ONCE:
    med = (M1 if front == "M1" else M3)[inst]
    df = datos[(inst, med)]
    B, P = detalle_muestra[(inst, med)]
    t = pd.Timestamp(h)
    sub = df[(df.index >= t) & (df.index < t + pd.Timedelta("1h"))]
    Bs = B.loc[sub.index]
    V = sub[["voltagePhaseA", "voltagePhaseB", "voltagePhaseC"]]
    r = (sub["activePowerPhaseA"] + sub["activePowerPhaseB"] + sub["activePowerPhaseC"]) - sub["totalActivePower"]
    filas.append(dict(frontera=front, inst=inst, medidor=med, hora=h, n_muestras=len(sub),
                      P_media=sub["totalActivePower"].mean(), V_min=V.min().min(), V_max=V.max().max(),
                      f_min=sub["frequency"].min(), f_max=sub["frequency"].max(),
                      PF_min=sub["totalPowerFactor"].min(), PF_max=sub["totalPowerFactor"].max(),
                      absr_max=r.abs().max(),
                      rel_r_max=(r.abs() / sub["totalActivePower"].abs().clip(lower=0.05)).max(),
                      banderas_activas=", ".join([c for c in Bs.columns if Bs[c].any()]) or "ninguna"))
pd.DataFrame(filas).to_csv(OUT / "once_horas.csv", index=False)

# ───────────────────────── 4. Detalle de horas marcadas ─────────────────────────
REF = ["V_ntc1340_-10+5", "V_pm10", "f_creg025_59.8-60.2", "f_59.9-60.1", "PF_lt_0.894_P>1kW",
       "S_1pct", "S_2pct", "S_5pct", "S_10pct", "S_20pct"]
filas = []
for (inst, med), (B, P) in detalle_muestra.items():
    df = datos[(inst, med)]
    hora = df.index.floor("h")
    Vmin = df[["voltagePhaseA", "voltagePhaseB", "voltagePhaseC"]].min(axis=1).values
    Vmax = df[["voltagePhaseA", "voltagePhaseB", "voltagePhaseC"]].max(axis=1).values
    rr = ((df["activePowerPhaseA"] + df["activePowerPhaseB"] + df["activePowerPhaseC"]) - P).values
    for col in REF:
        m = B[col]
        if not m.any():
            continue
        g = pd.DataFrame({"P": P.values, "m": m.values, "V": Vmin, "Vmax": Vmax,
                          "f": df["frequency"].values, "pf": df["totalPowerFactor"].values, "r": rr}, index=hora)
        n_h = g.groupby(level=0).size()
        for h, sub in g[g.m].groupby(level=0):
            filas.append(dict(inst=inst, medidor=med, bandera=col, hora=str(h), muestras_marcadas=len(sub),
                              muestras_hora=int(n_h.loc[h]), P_media_hora=float(g.loc[[h], "P"].mean()),
                              P_media_marcadas=float(sub.P.mean()), Vmin=float(sub.V.min()),
                              Vmax=float(sub.Vmax.max()), f_min=float(sub.f.min()), f_max=float(sub.f.max()),
                              pf_min=float(sub.pf.min()), absr_max=float(sub.r.abs().max())))
pd.DataFrame(filas).to_csv(OUT / "horas_marcadas_detalle.csv", index=False)

# ───────────────────────── 5. V=0 frente a P=0 ─────────────────────────
filas = []
for (inst, med), df in datos.items():
    V = df[["voltagePhaseA", "voltagePhaseB", "voltagePhaseC"]]
    P = df["totalActivePower"]
    tres0 = (V <= 0.5).all(axis=1); alguna0 = (V <= 0.5).any(axis=1) & ~tres0
    filas.append(dict(inst=inst, medidor=med, tres_fases_cero=int(tres0.sum()),
                      tres_fases_cero_y_P0=int((tres0 & (P.abs() < 0.01)).sum()),
                      una_o_dos_fases_cero=int(alguna0.sum()),
                      una_o_dos_cero_P_media=float(P[alguna0].mean()) if alguna0.any() else np.nan,
                      f_cero=int((df["frequency"] <= 1).sum()), f_cero_y_V_cero=int(((df["frequency"] <= 1) & tres0).sum())))
pd.DataFrame(filas).to_csv(OUT / "ceros_tension.csv", index=False)
print("ANALISIS LISTO", flush=True)
