"""
xm_prices.py  — Precios de bolsa XM y calibración del parámetro b
==================================================================
Brayan S. Lopez-Mendez · Udenar 2026

FUENTES DE DATOS (prioridad):
  1. API pydataxm  →  pip install pydataxm  (automática, sin descarga manual)
  2. CSV descargado de Sinergox XM (descarga manual)
  3. Sintético calibrado con promedios mensuales REALES XM

CÓMO INSTALAR pydataxm:
  pip install pydataxm
  El sistema la usa automáticamente en la próxima ejecución.

DESCARGA MANUAL (si no quieres instalar pydataxm):
  1. Ir a sinergox.xm.com.co
  2. Históricos → Precios → Precio de Bolsa Nacional (Col$/kWh)
  3. Seleccionar Jul 2025 - Ene 2026, exportar como Excel
  4. En Excel: Archivo → Guardar como → CSV UTF-8
  5. Copiar a: tesis_p2p/data/precios_bolsa_xm.csv

DATOS REALES VERIFICADOS (informes mensuales xm.com.co):
  Jul-2025: 138 COP/kWh  |  Ago-2025: 251 COP/kWh
  Sep-2025: 305 COP/kWh  |  Oct-2025: 177 COP/kWh
  Nov-2025: 235 COP/kWh  |  Dic-2025: ~200 (estimado)
  Ene-2026: ~220 (estimado)
"""

import os
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

# ── Promedios mensuales REALES verificados (COP/kWh) ─────────────────────────
# Fuente: Informes mensuales XM publicados en xm.com.co/noticias
XM_MONTHLY_REAL = {
    "2025-07": 138.4,   # Informe ago-2025: 138 COP/kWh
    "2025-08": 251.5,   # Informe sep-2025: 251 COP/kWh
    "2025-09": 304.8,   # Informe oct-2025: 304.8 COP/kWh
    "2025-10": 176.9,   # Informe nov-2025: 176.9 COP/kWh
    "2025-11": 234.9,   # Informe dic-2025: 234.87 COP/kWh
    "2025-12": 200.0,   # Estimado (tendencia post-El Niño 2024-2025)
    "2026-01": 220.0,   # Estimado
}

# Patrón intradiario colombiano (factor multiplicador por hora)
# Basado en análisis estadístico de series históricas XM 2022-2024
HOURLY_PATTERN_COL = np.array([
    0.85, 0.82, 0.80, 0.79, 0.80, 0.85,   # 0-5h: valle nocturno
    0.92, 1.00, 1.08, 1.10, 1.08, 1.05,   # 6-11h: rampa mañana
    1.05, 1.03, 1.02, 1.03, 1.05, 1.10,   # 12-17h: tarde
    1.18, 1.20, 1.15, 1.08, 1.00, 0.90,   # 18-23h: pico nocturno
])

# Factor día de semana (domingos ~10% más baratos en Colombia)
DOW_FACTOR = np.array([1.02, 1.03, 1.03, 1.03, 1.02, 0.98, 0.90])

# Escenarios para análisis de sensibilidad
XM_PRICES_REFERENCE = {
    "2025_real":     {"mean": 221, "std": 65,  "min": 80,   "max": 400},
    "2025_normal":   {"mean": 221, "std": 65,  "min": 80,   "max": 400},
    "2025_el_nino":  {"mean": 420, "std": 120, "min": 250,  "max": 800},
    "2024_escasez":  {"mean": 700, "std": 200, "min": 350,  "max": 1200},
    "2025_lluvioso": {"mean": 140, "std": 40,  "min": 60,   "max": 280},
}

# Parámetro b calibrado por institución (LCOE solar Pasto 2025)
B_CALIBRATED = {
    "Udenar_fronius":  225,
    "Mariana_fronius": 225,
    "UCC_fronius":     225,
    "HUDN_fronius":    225,
    "Cesmag_inv":      210,
    "default_pasto":   220,
}


# ── 1. API pydataxm (automática) ──────────────────────────────────────────────

def download_via_api(t_start="2025-07-01", t_end="2026-02-01",
                     save_path=None):
    """Descarga precios usando la API oficial XM (pydataxm).
    Requiere: pip install pydataxm
    """
    try:
        from pydataxm.pydataxm import ReadDB
    except ImportError:
        print("  [xm_api] pydataxm no instalado. Ejecutar: pip install pydataxm")
        return None

    try:
        print("  [xm_api] Conectando a API XM...")
        obj = ReadDB()
        dt_start = datetime.strptime(t_start, "%Y-%m-%d")
        dt_end   = datetime.strptime(t_end,   "%Y-%m-%d")
        all_series = []
        current = dt_start
        while current < dt_end:
            block_end = min(current + timedelta(days=28), dt_end)
            s = current.strftime("%Y-%m-%d")
            e = block_end.strftime("%Y-%m-%d")
            try:
                df = obj.request_data("PrecioOfertaBolsa", "Sistema", s, e)
                if df is not None and not df.empty:
                    all_series.append(df)
                    print(f"    ✓ {s} → {e}")
            except Exception as ex:
                print(f"    ✗ {s} → {e}: {ex}")
            current = block_end

        if not all_series:
            return None

        df_all = pd.concat(all_series, ignore_index=True)
        prices = _parse_api_df(df_all, dt_start, dt_end)
        if prices is not None and save_path:
            _save_csv(prices, dt_start, save_path)
            print(f"  [xm_api] Cache guardado: {save_path}")
        return prices
    except Exception as e:
        print(f"  [xm_api] Error: {e}")
        return None


def _parse_api_df(df, dt_start, dt_end):
    """Parsea DataFrame de pydataxm a array (T,) en COP/kWh."""
    try:
        hour_cols = [c for c in df.columns
                     if "hour" in c.lower() or "hora" in c.lower()]
        date_col  = next((c for c in df.columns
                          if "date" in c.lower() or "fecha" in c.lower()), None)
        val_col   = next((c for c in df.columns
                          if any(k in c.lower()
                                 for k in ["value","valor","precio","price"])), None)

        # Formato wide: Date + Hour01..Hour24
        if date_col and len(hour_cols) >= 10:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()
            mask = (df.index >= str(dt_start.date())) & (df.index < str(dt_end.date()))
            df = df[mask]
            for c in hour_cols:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            prices = df[sorted(hour_cols, key=lambda x: int(''.join(d for d in x if d.isdigit()) or '0'))[:24]].values.flatten().astype(float)
            n = int((dt_end - dt_start).total_seconds() / 3600)
            prices = prices[:n] if len(prices) >= n else np.pad(prices, (0, n-len(prices)), constant_values=np.nanmedian(prices))
            prices[np.isnan(prices)] = np.nanmedian(prices[~np.isnan(prices)])
            print(f"  [xm_api] {len(prices)}h, media={np.nanmean(prices):.0f} COP/kWh")
            return prices.astype(float)

        # Formato long: Date + Hour + Value
        if date_col and val_col:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df[val_col]  = pd.to_numeric(df[val_col],  errors="coerce")
            df = df.dropna(subset=[date_col, val_col]).set_index(date_col).sort_index()
            idx = pd.date_range(dt_start, dt_end, freq="1h", inclusive="left")
            serie = df[val_col].resample("1h").mean().reindex(idx)
            serie = serie.interpolate("time", limit=6).fillna(serie.median())
            print(f"  [xm_api] {len(serie)}h, media={serie.mean():.0f} COP/kWh")
            return serie.values.astype(float)
    except Exception as e:
        print(f"  [xm_api] Parse error: {e}")
    return None


# ── 2. CSV descargado de Sinergox ─────────────────────────────────────────────

def load_xm_prices(csv_path, t_start="2025-07-01", t_end="2026-02-01"):
    """
    Carga precios XM desde CSV descargado manualmente de Sinergox.

    Formatos aceptados automáticamente:
      Wide:  Fecha ; Variable ; Hora 1 ; Hora 2 ; ... ; Hora 24
      Long:  Fecha , Hora , Precio_COP_kWh
      SIMEM: Date , Values.Hour01 , ... , Values.Hour24
    """
    path = Path(csv_path)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            first = f.readline()
        sep = ";" if first.count(";") > first.count(",") else ","
        df  = pd.read_csv(path, sep=sep, encoding="utf-8-sig",
                          low_memory=False, on_bad_lines="skip")
        df.columns = [str(c).strip() for c in df.columns]
        print(f"  [xm_csv] {path.name} — {len(df)} filas, cols: {list(df.columns[:6])}")

        fecha_col = next((c for c in df.columns
                          if any(k in c.lower() for k in ["fecha","date","time"])), None)
        hora_cols = [c for c in df.columns
                     if any(c.strip().lower().startswith(p)
                            for p in ["hora ","hour ","h0","h1","h2","values.hour","value.hour"])]
        price_col = next((c for c in df.columns
                          if any(k in c.lower()
                                 for k in ["precio","price","valor","bolsa","kwh"])), None)
        hour_col  = next((c for c in df.columns
                          if c.strip().lower() in ["hora","hour","h","hh"]), None)

        if len(hora_cols) >= 10 and fecha_col:
            # Formato Wide
            df[fecha_col] = pd.to_datetime(df[fecha_col], errors="coerce")
            df = df.dropna(subset=[fecha_col]).sort_values(fecha_col)
            mask = (df[fecha_col] >= t_start) & (df[fecha_col] < t_end)
            df   = df[mask]
            if df.empty:
                return None
            def hn(c):
                digits = "".join(x for x in c if x.isdigit())
                return int(digits) if digits else 99
            hc = sorted(hora_cols, key=hn)[:24]
            for c in hc:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            prices = df[hc].values.astype(float).flatten()
            n = int((pd.Timestamp(t_end) - pd.Timestamp(t_start)).total_seconds() / 3600)
            if len(prices) > n:
                prices = prices[:n]
            elif len(prices) < n:
                prices = np.pad(prices, (0, n-len(prices)), constant_values=np.nanmedian(prices))
            prices[np.isnan(prices)] = np.nanmedian(prices[~np.isnan(prices)])
            print(f"  [xm_csv] Wide {len(prices)}h, media={prices.mean():.0f} COP/kWh")
            return prices.astype(float)

        if fecha_col and price_col:
            # Formato Long
            df[fecha_col]  = pd.to_datetime(df[fecha_col], errors="coerce")
            df[price_col]  = pd.to_numeric(df[price_col],  errors="coerce")
            df = df.dropna(subset=[fecha_col, price_col])
            if hour_col:
                df[hour_col] = pd.to_numeric(df[hour_col], errors="coerce").fillna(1) - 1
                df["_dt"] = df[fecha_col] + pd.to_timedelta(
                    df[hour_col].clip(0,23).astype(int), unit="h")
            else:
                df["_dt"] = df[fecha_col]
            df = df.set_index("_dt").sort_index()
            idx   = pd.date_range(t_start, t_end, freq="1h", inclusive="left")
            serie = df[price_col].resample("1h").mean().reindex(idx)
            serie = serie.interpolate("time", limit=6).fillna(serie.median())
            print(f"  [xm_csv] Long {len(serie)}h, media={serie.mean():.0f} COP/kWh")
            return serie.values.astype(float)

        print(f"  [xm_csv] Formato no reconocido. Columnas: {list(df.columns[:10])}")
    except Exception as e:
        print(f"  [xm_csv] Error: {e}")
    return None


# ── 3. Sintético calibrado ────────────────────────────────────────────────────

def generate_synthetic_prices(T, t_start="2025-07-01",
                               scenario="2025_real", seed=42):
    """
    Serie sintética calibrada con promedios mensuales REALES de XM.
    Incluye patrón intradiario colombiano y efecto día de semana.
    """
    rng = np.random.default_rng(seed)
    ref = XM_PRICES_REFERENCE.get(scenario, XM_PRICES_REFERENCE["2025_real"])
    dt_start = pd.Timestamp(t_start)
    idx    = pd.date_range(dt_start, periods=T, freq="1h")
    prices = np.zeros(T)

    for i, dt in enumerate(idx):
        month_key = dt.strftime("%Y-%m")
        if scenario in ("2025_real", "2025_normal") and month_key in XM_MONTHLY_REAL:
            monthly_mean = XM_MONTHLY_REAL[month_key]
        else:
            base = XM_MONTHLY_REAL.get(month_key, ref["mean"])
            monthly_mean = base * ref["mean"] / 221.0
        mu_h   = monthly_mean * HOURLY_PATTERN_COL[dt.hour] * DOW_FACTOR[dt.dayofweek]
        std_h  = mu_h * 0.28
        s2     = np.log(1 + (std_h / max(mu_h, 1)) ** 2)
        prices[i] = rng.lognormal(np.log(max(mu_h, 1)) - s2/2, np.sqrt(s2))

    prices = np.clip(prices, ref["min"], ref["max"])
    print(f"  [xm_synth] '{scenario}': {T}h, media={prices.mean():.0f} "
          f"(rango {prices.min():.0f}-{prices.max():.0f}) COP/kWh")
    return prices.astype(float)


# ── Función principal ─────────────────────────────────────────────────────────

def get_pi_bolsa(T, t_start="2025-07-01", t_end="2026-02-01",
                 csv_path=None, use_api=True,
                 scenario="2025_real", seed=42):
    """
    Obtiene vector de precios bolsa pi_bolsa (T,) en COP/kWh.
    Prioridad: API pydataxm → CSV local → sintético calibrado.
    """
    base_dir = Path(__file__).parent

    # Intento 1: API pydataxm (con cache)
    if use_api:
        cache = base_dir / "precios_bolsa_xm_api.csv"
        if cache.exists():
            prices = load_xm_prices(str(cache), t_start, t_end)
            if prices is not None:
                return _adj(prices, T)
        prices = download_via_api(t_start, t_end, save_path=str(cache))
        if prices is not None:
            return _adj(prices, T)

    # Intento 2: CSV explícito
    if csv_path:
        prices = load_xm_prices(csv_path, t_start, t_end)
        if prices is not None:
            return _adj(prices, T)

    # Intento 3: CSV automático en data/
    for name in ["precios_bolsa_xm.csv", "xm_precios_bolsa.csv",
                  "precio_bolsa_xm.csv", "PrecioBolsa.csv",
                  "Precio_Bolsa_Nacional.csv"]:
        p = base_dir / name
        if p.exists():
            prices = load_xm_prices(str(p), t_start, t_end)
            if prices is not None:
                return _adj(prices, T)

    # Intento 4: sintético calibrado
    print(f"  [xm] Sintético calibrado. Para datos reales:")
    print(f"    pip install pydataxm  (descarga automática)")
    print(f"    o descargar CSV de sinergox.xm.com.co → Históricos → Precios")
    print(f"    y guardarlo como: {base_dir}/precios_bolsa_xm.csv")
    return generate_synthetic_prices(T, t_start, scenario, seed)


def _adj(prices, T):
    if len(prices) >= T:
        return prices[:T]
    return np.pad(prices, (0, T-len(prices)), constant_values=np.nanmedian(prices))


def _save_csv(prices, dt_start, path):
    rows = [{"Fecha": (dt_start + timedelta(hours=i)).strftime("%Y-%m-%d"),
             "Hora": (dt_start + timedelta(hours=i)).hour + 1,
             "Precio_COP_kWh": round(float(p), 2)}
            for i, p in enumerate(prices)]
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def print_price_summary(prices, t_start="2025-07-01", label="Precios XM"):
    dt_idx  = pd.date_range(t_start, periods=len(prices), freq="1h")
    serie   = pd.Series(prices, index=dt_idx)
    monthly = serie.resample("ME").mean()
    print(f"\n  {label} — Resumen mensual (COP/kWh):")
    print(f"  {'Mes':<12} {'Media':>8} {'Min':>8} {'Max':>8}  Fuente")
    print(f"  {'-'*52}")
    for dt, val in monthly.items():
        key = dt.strftime("%Y-%m")
        src = "REAL" if key in XM_MONTHLY_REAL else "est."
        mo  = serie[serie.index.to_period("M") == dt.to_period("M")]
        print(f"  {dt.strftime('%b-%Y'):<12} {val:>8.0f} "
              f"{mo.min():>8.0f} {mo.max():>8.0f}  {src}")
    print(f"  {'Total':<12} {prices.mean():>8.0f} {prices.min():>8.0f} {prices.max():>8.0f}")


# ── Calibración parámetro b ───────────────────────────────────────────────────

def calibrate_b_parameters(agent_names, capacity_kw=None,
                             irradiance_kwh_m2_day=4.2):
    irr_ref = 4.5
    adj = irr_ref / max(irradiance_kwh_m2_day, 1.0)
    b = [B_CALIBRATED.get(f"{n.lower()}_fronius",
         B_CALIBRATED["default_pasto"]) * adj for n in agent_names]
    return np.array(b, dtype=float)


def get_b_for_real_data(N, agent_names):
    b = calibrate_b_parameters(agent_names)
    if len(b) < N:
        b = np.pad(b, (0, N-len(b)), constant_values=B_CALIBRATED["default_pasto"])
    return b[:N]


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Precios bolsa XM — Tesis Brayan López")
    ap.add_argument("--api",   action="store_true")
    ap.add_argument("--synth", action="store_true")
    ap.add_argument("--csv",   default=None)
    ap.add_argument("--T",     type=int, default=5160)
    args = ap.parse_args()

    prices = get_pi_bolsa(T=args.T, use_api=args.api or (not args.synth),
                           csv_path=args.csv)
    print_price_summary(prices)
    out = Path(__file__).parent / "precios_bolsa_generados.csv"
    _save_csv(prices, datetime(2025, 7, 1), str(out))
    print(f"\n  Guardado en: {out}")
