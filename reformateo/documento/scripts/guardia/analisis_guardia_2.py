"""Segunda pasada: nominal por medidor, suma de fases en pasos del registro,
guardia final con variantes muestra/hora, solape y las once horas."""
import sys, pickle
from pathlib import Path
import numpy as np
import pandas as pd

SP = Path(sys.argv[1]); OUT = SP / "salidas"; OUT.mkdir(exist_ok=True)
IDX = pd.date_range("2025-04-04", "2025-12-16", freq="1h", inclusive="left")
M1 = {"Udenar": "Bloque Sur - Medidor 1 - electricMeter", "Mariana": "Medidor 1 - Alvernia - electricMeter",
      "UCC": "Medidor 1 - UCC - electricMeter", "HUDN": "Medidor 1 - HUDN - electricMeter",
      "Cesmag": "Medidor 1 - Cesmag - electricMeter"}
M3 = {"Udenar": "Bloque Sur - Medidor 3 - electricMeter", "Mariana": "Medidor 1 - Alvernia - electricMeter",
      "UCC": "Medidor 3 - UCC - electricMeter", "HUDN": "Medidor 3 - HUDN - electricMeter",
      "Cesmag": "Medidor 3 - Cesmag - electricMeter"}
PIPE = {("M1", i): m for i, m in M1.items()} | {("M3", i): m for i, m in M3.items()}
ONCE = [("M1", "Mariana", "2025-04-24 08:00"), ("M1", "Mariana", "2025-04-24 09:00"),
        ("M1", "Mariana", "2025-04-24 10:00"), ("M1", "Mariana", "2025-10-01 09:00"),
        ("M3", "Mariana", "2025-04-24 08:00"), ("M3", "Mariana", "2025-04-24 09:00"),
        ("M3", "Mariana", "2025-04-24 10:00"), ("M3", "Mariana", "2025-10-01 09:00"),
        ("M3", "Mariana", "2025-08-14 08:00"),
        ("M3", "Cesmag", "2025-04-04 09:00"), ("M3", "Cesmag", "2025-05-09 09:00")]

datos = {}
for p in sorted(SP.glob("crudo_*.pkl")):
    with open(p, "rb") as f:
        df = pickle.load(f)
    nombre = p.stem.replace("crudo_", ""); inst = nombre.split("_")[0]
    datos[(inst, nombre[len(inst) + 1:].replace("_", " "))] = df
corto = lambda inst, med: f"{inst[:6]} {med.split('Medidor ')[1][0]}"

# ── nominal por muestra: el mas cercano a la mediana de las tres fases entre 127, 220, 440 ──
def nominal_muestra(V):
    med = V.median(axis=1)
    cand = np.array([127.0, 220.0, 440.0])
    return pd.Series(cand[np.abs(med.values[:, None] - cand[None, :]).argmin(axis=1)], index=V.index)

# ── paso del registro por medidor (propiedad del instrumento) ──
def paso(df):
    u = np.sort(df["activePowerPhaseA"].dropna().unique()); d = np.diff(u); d = d[d > 1e-9]
    return float(np.median(d[d < 1.0])) if len(d) else np.nan   # mediana de los saltos pequenos

info = []
flags = {}
for (inst, med), df in datos.items():
    V = df[["voltagePhaseA", "voltagePhaseB", "voltagePhaseC"]]
    nom = nominal_muestra(V)
    q = paso(df)
    P = df["totalActivePower"]
    r = (df["activePowerPhaseA"] + df["activePowerPhaseB"] + df["activePowerPhaseC"]) - P
    k_r = (r.abs() / q) if (q and np.isfinite(q) and q > 0) else pd.Series(np.nan, index=df.index)
    # |dP| entre muestras consecutivas (kW), para ver si las discrepancias grandes coinciden con rampas
    dP = P.diff().abs()
    dPn = P.diff(-1).abs()
    dPmax = pd.concat([dP, dPn], axis=1).max(axis=1)
    F = {}
    for lo, hi, tag in [(0.90, 1.05, "V_ntc_-10+5"), (0.90, 1.10, "V_pm10"), (0.92, 1.08, "V_pm8"),
                        (0.85, 1.15, "V_pm15"), (0.80, 1.20, "V_pm20"), (0.5, 1.5, "V_pm50")]:
        F[tag] = (V.min(axis=1) < lo * nom) | (V.max(axis=1) > hi * nom)
    f = df["frequency"]
    for lo, hi, tag in [(59.8, 60.2, "f_59.8-60.2"), (59.9, 60.1, "f_59.9-60.1"), (59.7, 60.3, "f_59.7-60.3"),
                        (59.5, 60.5, "f_59.5-60.5"), (59.0, 61.0, "f_59-61")]:
        F[tag] = (f < lo) | (f > hi)
    for k in [1.5, 2, 3, 4, 5, 8, 10]:
        F[f"S_{k}q"] = k_r > k
    for k, rel in [(2, 0.02), (2, 0.05), (3, 0.02), (3, 0.05), (3, 0.10)]:
        F[f"S_{k}q_o_{int(rel*100)}pct"] = r.abs() > np.maximum(k * q if np.isfinite(q) else np.inf, rel * P.abs())
    F = pd.DataFrame(F, index=df.index).fillna(False).astype(bool)
    flags[(inst, med)] = (F, P, r, q, dPmax, nom)
    d = dict(med=corto(inst, med), paso_kW=q,
             nominal_modal=float(nom.mode().iloc[0]), pct_muestras_nominal_modal=float((nom == nom.mode().iloc[0]).mean() * 100),
             VA_med=float(V.iloc[:, 0].median()), VB_med=float(V.iloc[:, 1].median()), VC_med=float(V.iloc[:, 2].median()),
             Vmin_rel_min=float((V.min(axis=1) / nom).min()), Vmax_rel_max=float((V.max(axis=1) / nom).max()),
             r_pasos_p50=float(k_r.quantile(0.5)) if k_r.notna().any() else np.nan,
             r_pasos_p99=float(k_r.quantile(0.99)) if k_r.notna().any() else np.nan,
             r_pasos_p999=float(k_r.quantile(0.999)) if k_r.notna().any() else np.nan,
             r_pasos_max=float(k_r.max()) if k_r.notna().any() else np.nan)
    for k in [1, 1.5, 2, 3, 5, 10]:
        d[f"n_gt_{k}q"] = int((k_r > k).sum())
    # rampas: |dP| mediano en las muestras con |r|>2q frente al global
    sel = k_r > 2
    d["dP_med_global_pasos"] = float((dPmax / q).median()) if np.isfinite(q) else np.nan
    d["dP_med_en_r_gt_2q_pasos"] = float((dPmax[sel] / q).median()) if sel.any() and np.isfinite(q) else np.nan
    d["frac_r_gt_2q_con_dP_gt_5q"] = float(((dPmax[sel] / q) > 5).mean()) if sel.any() and np.isfinite(q) else np.nan
    d["frac_r_gt_3q_con_dP_gt_5q"] = float(((dPmax[k_r > 3] / q) > 5).mean()) if (k_r > 3).any() and np.isfinite(q) else np.nan
    info.append(d)
info = pd.DataFrame(info); info.to_csv(OUT / "info_medidor_2.csv", index=False)
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 50); pd.set_option("display.max_rows", 500)
print("=== NOMINAL, PASO DEL REGISTRO Y SUMA DE FASES EN PASOS ===")
print(info.round(3).to_string(index=False))

# ── censo por bandera: muestras, horas, variantes ──
def censo_bandera(df, F, P, col):
    hora = df.index.floor("h")
    n_h = pd.Series(1, index=hora).groupby(level=0).sum()
    m = F[col]
    if not m.any():
        return dict(muestras=0, horas=0, muestras_en_horas=0, horas_mayoria=0, horas_quedan_lt23=0, horas_quedan_0=0,
                    horas_incompletas=0, horas_completas=0, horas_adyacentes_vacia=0, energia_kWh=0.0,
                    delta_kWh_quitar_muestras=0.0)
    mh = pd.Series(m.values, index=hora).groupby(level=0).sum(); mh = mh[mh > 0]
    nh = n_h.reindex(mh.index)
    rest = nh - mh
    g = pd.DataFrame({"P": P.values, "m": m.values}, index=hora)
    media_todo = g.groupby(level=0)["P"].mean().reindex(mh.index)
    media_sin = g[~g.m].groupby(level=0)["P"].mean().reindex(mh.index)
    delta = (media_sin - media_todo).fillna(-media_todo)
    presentes = set(n_h.index)
    ady = sum(1 for h in mh.index if (h - pd.Timedelta("1h")) not in presentes or (h + pd.Timedelta("1h")) not in presentes)
    return dict(muestras=int(m.sum()), horas=int(len(mh)), muestras_en_horas=int(nh.sum()),
                horas_mayoria=int((mh >= nh / 2).sum()), horas_quedan_lt23=int((rest < 23).sum()),
                horas_quedan_0=int((rest == 0).sum()), horas_incompletas=int((nh < 30).sum()),
                horas_completas=int((nh == 30).sum()), horas_adyacentes_vacia=int(ady),
                energia_kWh=float(media_todo.sum()), delta_kWh_quitar_muestras=float(delta.sum()))

filas = []
for (inst, med), (F, P, r, q, dPmax, nom) in flags.items():
    df = datos[(inst, med)]
    Fx = F.copy()
    Fx["G_final_V10_f0.2_S3q"] = F["V_pm10"] | F["f_59.8-60.2"] | F["S_3q"]
    Fx["G_final_V10_f0.2_S5q"] = F["V_pm10"] | F["f_59.8-60.2"] | F["S_5q"]
    Fx["G_solo_S3q_V10"] = F["V_pm10"] | F["S_3q"]
    for col in Fx.columns:
        d = censo_bandera(df, Fx, P, col); d.update(inst=inst, medidor=med, med=corto(inst, med), bandera=col)
        filas.append(d)
censo = pd.DataFrame(filas); censo.to_csv(OUT / "censo2_por_medidor.csv", index=False)
cols = ["muestras", "horas", "muestras_en_horas", "horas_mayoria", "horas_quedan_lt23", "horas_quedan_0",
        "horas_incompletas", "horas_completas", "horas_adyacentes_vacia", "energia_kWh", "delta_kWh_quitar_muestras"]
print("\n=== CENSO 20 MEDIDORES (nominal corregido) ===")
print(censo.groupby("bandera")[cols].sum().round(1).to_string())
pipe = []
for (front, inst), med in PIPE.items():
    s = censo[(censo.inst == inst) & (censo.medidor == med)].copy(); s.insert(0, "frontera", front); pipe.append(s)
pipe = pd.concat(pipe); pipe.to_csv(OUT / "censo2_pipeline.csv", index=False)
print("\n=== CENSO SERIES DEL PIPELINE, por frontera ===")
print(pipe.groupby(["frontera", "bandera"])[cols].sum().round(1).to_string())
print("\n=== POR MEDIDOR: muestras (m) y horas (h) para las bandas de referencia ===")
ref = ["V_ntc_-10+5", "V_pm10", "V_pm15", "f_59.8-60.2", "f_59.9-60.1", "S_2q", "S_3q", "S_5q", "S_10q",
       "S_3q_o_5pct", "G_final_V10_f0.2_S3q"]
piv_m = censo[censo.bandera.isin(ref)].pivot(index="med", columns="bandera", values="muestras")[ref]
piv_h = censo[censo.bandera.isin(ref)].pivot(index="med", columns="bandera", values="horas")[ref]
print(piv_m.to_string()); print(); print(piv_h.to_string())

# ── las once horas bajo el guardia ──
print("\n=== ONCE HORAS: guardia con nominal corregido y suma en pasos ===")
filas = []
for front, inst, h in ONCE:
    med = PIPE[(front, inst)]; F, P, r, q, dPmax, nom = flags[(inst, med)]
    t = pd.Timestamp(h); sel = (F.index >= t) & (F.index < t + pd.Timedelta("1h"))
    Fs = F[sel]
    filas.append(dict(frontera=front, inst=inst, hora=h, n=int(sel.sum()), paso_kW=q,
                      r_max_pasos=float((r[sel].abs() / q).max()), V_rel_min=float((datos[(inst, med)].loc[sel, ["voltagePhaseA","voltagePhaseB","voltagePhaseC"]].min(axis=1) / nom[sel]).min()),
                      V_rel_max=float((datos[(inst, med)].loc[sel, ["voltagePhaseA","voltagePhaseB","voltagePhaseC"]].max(axis=1) / nom[sel]).max()),
                      V_pm10=int(Fs["V_pm10"].sum()), V_ntc=int(Fs["V_ntc_-10+5"].sum()), f_band=int(Fs["f_59.8-60.2"].sum()),
                      S_2q=int(Fs["S_2q"].sum()), S_3q=int(Fs["S_3q"].sum()), S_1p5q=int(Fs["S_1.5q"].sum())))
print(pd.DataFrame(filas).round(3).to_string(index=False))

# ── detalle de horas marcadas por el guardia final (y por S_3q, V_pm10, f) en las 10 series del pipeline ──
filas = []
for (front, inst), med in PIPE.items():
    F, P, r, q, dPmax, nom = flags[(inst, med)]; df = datos[(inst, med)]
    hora = df.index.floor("h")
    for col in ["V_pm10", "f_59.8-60.2", "S_3q", "S_5q"]:
        m = F[col]
        if not m.any():
            continue
        g = pd.DataFrame({"P": P.values, "m": m.values, "r_pasos": (r.abs() / q).values, "dP_pasos": (dPmax / q).values,
                          "Vmin": df[["voltagePhaseA","voltagePhaseB","voltagePhaseC"]].min(axis=1).values,
                          "Vmax": df[["voltagePhaseA","voltagePhaseB","voltagePhaseC"]].max(axis=1).values,
                          "f": df["frequency"].values}, index=hora)
        n_h = g.groupby(level=0).size()
        for h, sub in g[g.m].groupby(level=0):
            filas.append(dict(frontera=front, inst=inst, bandera=col, hora=str(h), n_marc=len(sub), n_hora=int(n_h.loc[h]),
                              P_media_hora=float(g.loc[[h], "P"].mean()), P_marc=float(sub.P.mean()),
                              r_pasos_max=float(sub.r_pasos.max()), dP_pasos_med=float(sub.dP_pasos.median()),
                              Vmin=float(sub.Vmin.min()), Vmax=float(sub.Vmax.max()), fmin=float(sub.f.min()), fmax=float(sub.f.max())))
det = pd.DataFrame(filas); det.to_csv(OUT / "detalle2_pipeline.csv", index=False)
print("\n=== DETALLE horas marcadas en las series del pipeline ===")
for col in ["V_pm10", "f_59.8-60.2", "S_3q"]:
    s = det[det.bandera == col]
    print(f"\n--- {col}: {len(s)} horas-serie")
    print(s.drop(columns=["bandera"]).round(3).to_string(index=False))
print("\nLISTO 2")
