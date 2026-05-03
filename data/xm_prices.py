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
# PB_PROM oficial XM (media ponderada por demanda) por mes para los 7 meses
# verificados en CAL-17 audit (2026-05-02), mas la media aritmetica del cache
# para los 3 meses adicionales (abr/may/jun 2025) extendidos en Sprint 1.1b.
# Fuentes verificadas (jul-2025 a ene-2026):
#   - xm.com.co/noticias/{8119,8184,8442,8584,8759}
#   - sinergox.xm.com.co/.../03_Informe_Precios_y_Transacciones_*.xlsx
# Provisional cache mean (abr/may/jun 2025), pendiente verificacion oficial:
#   - follow-up CAL-17b. Ver docs/adr/0017-cal17-pydataxm-vs-ptb-audit.md
XM_MONTHLY_REAL = {
    "2025-04": 132.51,  # cache mean (CAL-17b pendiente verificacion oficial)
    "2025-05": 126.70,  # cache mean (CAL-17b pendiente verificacion oficial)
    "2025-06": 112.51,  # cache mean (CAL-17b pendiente verificacion oficial)
    "2025-07": 138.36,  # Informe XM jul-2025 (xm.com.co/noticias/8119)
    "2025-08": 251.50,  # Informe XM ago-2025 (xm.com.co/noticias/8184)
    "2025-09": 292.65,  # Sinergox sep-2025 (Comportamiento_PBNal_Horario)
    "2025-10": 176.90,  # Informe XM oct-2025 (xm.com.co/noticias/8442)
    "2025-11": 234.87,  # Informe XM nov-2025 (xm.com.co/noticias/8584)
    "2025-12": 278.83,  # Sinergox dic-2025 (Comportamiento_PBNal_Horario)
    "2026-01": 213.00,  # Informe XM ene-2026 (xm.com.co/noticias/8759)
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
#
# Nota de auditoría (D2, 2026-04-17)
# ----------------------------------
# Estos valores son en COP/kWh y aplican SOLO al modo real (datos MTE).
# Se usan valores homogéneos (225 COP/kWh, con ajuste a 210 para Cesmag)
# porque las 5 instituciones comparten:
#   - Mismo fabricante de inversor (Fronius, capacidad <= 100 kW).
#   - Misma ubicación (Pasto, Nariño).
#   - Misma ventana de operación (jul. 2025 - ene. 2026).
#   - Rango IRENA [16] / UPME [17]: 200-250 COP/kWh para solar
#     distribuida pequeña en Colombia (ver Revision_Bibliografica_Act_1_2.md:81).
#
# El MODO SINTÉTICO de data/base_case_data.py sí preserva la
# heterogeneidad de JoinFinal.m (b = 6.0865 * [3.93*52, 32, 47, 37, 0, 0] =
# [1245, 195, 287, 225, 0, 0] en unidades de optimización, no COP/kWh).
# Las dos calibraciones son incomparables por unidades y por propósito
# (fidelidad al modelo base vs representación empírica MTE).
#
# Ver Documentos/notas_modelo_tesis.md §7 CAL-6 para la justificación formal.
B_CALIBRATED = {
    "Udenar_fronius":  225,
    "Mariana_fronius": 225,
    "UCC_fronius":     225,
    "HUDN_fronius":    225,
    "Cesmag_inv":      210,
    "default_pasto":   220,
}


# ── 1. API pydataxm (automática) ──────────────────────────────────────────────

def _find_metric_id(obj) -> str:
    """
    Autodescubre el MetricId correcto para precio de bolsa en la API XM.
    Usa get_collections() para consultar el catálogo disponible.
    Nombres conocidos en distintas versiones de pydataxm:
      - 'PrecBolsNaci'               (API actual verificado 2025)
      - 'PrecioOfertaBolsa'           (versiones anteriores)
      - 'PrecioBolsaNacional'         (nombre largo)
      - 'PrecioTransaccionBolsa'      (PTB)
    """
    candidatos = [
        "PrecBolsNaci",
        "PrecioBolsaNacional",
        "PrecioOfertaBolsa",
        "PrecioTransaccionBolsa",
        "PrecioOfertaBolsaNacional",
        "Precio_Bolsa",
    ]
    try:
        colecciones = obj.get_collections()
        if colecciones is not None and not colecciones.empty:
            # Buscar en el catálogo por nombre que contenga 'bolsa' o 'precio'
            cols_df = colecciones.copy()
            cols_df.columns = [c.lower() for c in cols_df.columns]
            id_col   = next((c for c in cols_df.columns if "id" in c), None)
            name_col = next((c for c in cols_df.columns
                             if any(k in c for k in ["name","nombre","metric"])), None)
            if id_col and name_col:
                mask = (cols_df[name_col].str.lower().str.contains("bolsa", na=False) |
                        cols_df[name_col].str.lower().str.contains("precio", na=False))
                matches = cols_df[mask]
                if not matches.empty:
                    metric_id = str(matches.iloc[0][id_col])
                    print(f"  [xm_api] Métrica encontrada en catálogo: {metric_id}")
                    return metric_id
    except Exception:
        pass
    # Fallback: probar candidatos en orden
    return candidatos[0]


def download_via_api(t_start="2025-07-01", t_end="2026-02-01",
                     save_path=None):
    """
    Descarga precios de bolsa usando la API oficial XM (pydataxm).
    Requiere: pip install pydataxm
    Documentación: github.com/EquipoAnaliticaXM/API_XM
    """
    try:
        from pydataxm.pydataxm import ReadDB
    except ImportError:
        print("  [xm_api] pydataxm no instalado.")
        print("  Instalar con: (.venv) pip install pydataxm")
        return None

    try:
        print("  [xm_api] Conectando a API XM (pydataxm)...")
        obj = ReadDB()
        dt_start = datetime.strptime(t_start, "%Y-%m-%d")
        dt_end   = datetime.strptime(t_end,   "%Y-%m-%d")

        # PrecBolsNaci es el MetricId verificado en la API XM (2025).
        # Los demás son fallbacks para versiones anteriores de la API.
        # Filtramos contra el inventario para suprimir mensajes "No existe".
        todos_candidatos = [
            "PrecBolsNaci",
            "PrecioBolsaNacional",
            "PrecioOfertaBolsa",
            "PrecioTransaccionBolsa",
            "PrecioOfertaBolsaNacional",
        ]
        try:
            ids_validos = set(obj.inventario_metricas["MetricId"].values)
            candidatos = [c for c in todos_candidatos if c in ids_validos] or todos_candidatos
        except Exception:
            candidatos = todos_candidatos

        all_series = []
        metric_ok  = None
        current    = dt_start

        while current < dt_end:
            block_end = min(current + timedelta(days=28), dt_end)
            s = current.strftime("%Y-%m-%d")
            e = block_end.strftime("%Y-%m-%d")
            success = False

            for metric in candidatos:
                try:
                    df = obj.request_data(metric, "Sistema", s, e)
                    if df is not None and not df.empty:
                        all_series.append(df)
                        metric_ok = metric
                        success = True
                        print(f"    ✓ {s}→{e}  ({metric})")
                        # Una vez encontrado el nombre correcto, solo usar ese
                        candidatos = [metric]
                        break
                except Exception:
                    pass
            if not success:
                print(f"    ✗ {s}→{e}: ninguna métrica funcionó")
            current = block_end

        if not all_series:
            print("  [xm_api] Sin datos. Verifica la conexión a internet.")
            print("  [xm_api] Para ver métricas disponibles:")
            print("    from pydataxm.pydataxm import ReadDB")
            print("    obj = ReadDB()")
            print("    print(obj.get_collections())")
            return None

        print(f"  [xm_api] Métrica usada: {metric_ok}")
        df_all = pd.concat(all_series, ignore_index=True)
        prices = _parse_api_df(df_all, dt_start, dt_end)
        if prices is not None and save_path:
            _save_csv(prices, dt_start, save_path)
            print(f"  [xm_api] Cache guardado en: {save_path}")
        return prices

    except Exception as e:
        print(f"  [xm_api] Error inesperado: {e}")
        return None


def _parse_api_df(df, dt_start, dt_end):
    """
    Parsea DataFrame de pydataxm a array (T,) en COP/kWh.
    Soporta formato wide (Date + Values_Hour01..Hour24) con fechas NaT
    — pydataxm ≥ pandas-3 convierte Date a numérico antes de la fecha,
    así que reconstruimos fechas por índice de fila cuando es necesario.
    """
    try:
        n_target = int((dt_end - dt_start).total_seconds() / 3600)
        hour_cols = [c for c in df.columns
                     if "hour" in c.lower() or "hora" in c.lower()]
        date_col  = next((c for c in df.columns
                          if "date" in c.lower() or "fecha" in c.lower()), None)
        val_col   = next((c for c in df.columns
                          if any(k in c.lower()
                                 for k in ["value","valor","precio","price"])
                          and "hour" not in c.lower()), None)

        # ── Formato wide: Hour01..Hour24 (una fila por día) ───────────────────
        if len(hour_cols) >= 10:
            hc = sorted(hour_cols,
                        key=lambda x: int("".join(d for d in x if d.isdigit()) or "0"))[:24]
            for c in hc:
                df[c] = pd.to_numeric(df[c], errors="coerce")

            # Reconstruir fechas: intentar Date primero; si NaT, usar dt_start + fila
            if date_col:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                if df[date_col].notna().any():
                    df = df.sort_values(date_col)
                else:
                    # pydataxm convirtió las fechas a NaN → reconstruir
                    df = df.reset_index(drop=True)
                    df[date_col] = [dt_start + timedelta(days=i) for i in range(len(df))]
            else:
                df["_date"] = [dt_start + timedelta(days=i) for i in range(len(df))]
                date_col = "_date"

            df = df.set_index(date_col).sort_index()
            prices = df[hc].values.astype(float).flatten()
            prices = prices[:n_target] if len(prices) >= n_target else np.pad(
                prices, (0, n_target - len(prices)), constant_values=np.nanmedian(prices))
            med = np.nanmedian(prices[~np.isnan(prices)]) if np.isnan(prices).any() else 0
            prices[np.isnan(prices)] = med
            print(f"  [xm_api] {len(prices)}h, media={np.nanmean(prices):.0f} COP/kWh")
            return prices.astype(float)

        # ── Formato long: Date + Hour + Value ────────────────────────────────
        if date_col and val_col:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df[val_col]  = pd.to_numeric(df[val_col],  errors="coerce")
            df = df.dropna(subset=[date_col, val_col]).set_index(date_col).sort_index()
            idx  = pd.date_range(dt_start, dt_end, freq="1h", inclusive="left")
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
                 scenario="2025_real", seed=42,
                 apply_ceiling=True,
                 ceiling_level="PES"):
    """
    Obtiene vector de precios bolsa pi_bolsa (T,) en COP/kWh.

    Prioridad de fuentes: API pydataxm → CSV local → sintético calibrado.

    Parameters
    ----------
    apply_ceiling : bool
        Si True (default), aplica el techo CREG 101 066/2024 a la serie
        antes de retornarla. Ver ``apply_creg101066_ceiling``. CAL-14.
    ceiling_level : {"PEI", "PE", "PES"}
        Nivel del techo. Default ``"PES"`` (techo absoluto superior).
    """
    base_dir = Path(__file__).parent

    prices = None

    # Intento 1: API pydataxm (con cache)
    if use_api:
        cache = base_dir / "precios_bolsa_xm_api.csv"
        if cache.exists():
            prices = load_xm_prices(str(cache), t_start, t_end)
        if prices is None:
            prices = download_via_api(t_start, t_end, save_path=str(cache))

    # Intento 2: CSV explícito
    if prices is None and csv_path:
        prices = load_xm_prices(csv_path, t_start, t_end)

    # Intento 3: CSV automático en data/
    if prices is None:
        for name in ["precios_bolsa_xm.csv", "xm_precios_bolsa.csv",
                      "precio_bolsa_xm.csv", "PrecioBolsa.csv",
                      "Precio_Bolsa_Nacional.csv"]:
            p = base_dir / name
            if p.exists():
                prices = load_xm_prices(str(p), t_start, t_end)
                if prices is not None:
                    break

    # Intento 4: sintético calibrado
    if prices is None:
        print(f"  [xm] Sintético calibrado. Para datos reales:")
        print(f"    pip install pydataxm  (descarga automática)")
        print(f"    o descargar CSV de sinergox.xm.com.co → Históricos → Precios")
        print(f"    y guardarlo como: {base_dir}/precios_bolsa_xm.csv")
        prices = generate_synthetic_prices(T, t_start, scenario, seed)

    prices = _adj(prices, T)

    # CAL-14: aplicar techo CREG 101 066/2024 (PES por defecto).
    if apply_ceiling:
        prices, diag = apply_creg101066_ceiling(
            prices, t_start, level=ceiling_level,
            return_diagnostics=True)
        _print_ceiling_summary(diag, level=ceiling_level)

    return prices


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


# ── §3.6 Análisis de fuente de precios ───────────────────────────────────────

# Descomposición regulatoria del CU institucional Colombia 2025 (COP/kWh)
# Fuente: CREG 119/2007 (fórmula tarifaria), informes Cedenar/ESSA Nariño 2024-2025
CU_COMPONENTS_2025 = {
    "G":   220,   # Costo de energía en bolsa (varía con precio de bolsa XM)
    "T":    60,   # Cargos de transmisión (STN) — fijos por resolución CREG
    "D":   160,   # Cargos de distribución (STR + SDL) — nivel de tensión 2-3
    "C":    90,   # Margen de comercialización (Cedenar/ESSA en Nariño)
    "PR":   35,   # Pérdidas de referencia reconocidas + restricciones
    "otros": 85,  # Contribución, sobretasa SSPD, ajuste IVA, redondeamiento
}
# CU estimado = suma ≈ 650 COP/kWh — referencia ilustrativa pre-CAL-8.
# La calibración en producción usa la tarifa real Cedenar mensual cargada por
# data/cedenar_tariff.py (oficial 797 / comercial 956 / comunitario ponderado
# ≈ 906 COP/kWh para abr-2025 → abr-2026). El bloque CU_COMPONENTS_2025 se
# conserva aquí para la justificación analítica del estimador en
# price_source_analysis(); 650 se mantiene como argumento por defecto y como
# DEFAULT_PI_GS_FALLBACK en data/cedenar_tariff.py para meses sin PDF.

# CAL-10: fracción del CU que corresponde al margen de Comercialización (C).
# Bajo CREG 174/2021 arts. 22-23, esta porción se sigue cobrando aunque el
# AGPE permute energía → el ahorro efectivo por kWh permutado vale
# (pi_gs - pi_gs * C_FRACTION) y no pi_gs completo.
# Aproximación proporcional: válida mientras CEDENAR no publique los
# componentes desagregados por mes. TODO(CAL-10+): extraer C real desde
# data/cedenar_pdfs/ cuando el PDF lo desglose.
C_FRACTION = CU_COMPONENTS_2025["C"] / sum(CU_COMPONENTS_2025.values())


def get_c_fraction() -> float:
    """Devuelve la fracción del CU asociada al margen de Comercialización."""
    return C_FRACTION


def price_source_analysis(
    pi_bolsa: np.ndarray,
    pi_gs: float = 650.0,
    agent_names: list = None,
    base_net_p2p: "np.ndarray | None" = None,
    base_net_c1:  "np.ndarray | None" = None,
    verbose: bool = True,
) -> dict:
    """
    §3.6 — Justificación formal de la fuente y calibración de precios.

    Responde las preguntas del asesor WEEF:
      1. ¿Es el precio de bolsa o el CU del comercializador?
         → Respuesta: AMBOS. pi_bolsa (XM) para liquidación de excedentes;
           pi_gs (CU) para valorar la energía que dejaría de comprarse a red.
      2. ¿Por qué se usa la media aritmética del pi_bolsa?
         → Compara media, mediana, media ponderada por hora solar, percentil 25/75.
      3. ¿Impacto en resultados de Udenar (agente más sensible a pi_bolsa)?
         → Solo si se pasan los arrays de beneficio nominales.

    Retorna:
        dict con estadísticos, justificación CU y análisis de sensibilidad
        al estimador usado para pi_bolsa.
    """
    result = {}

    # ── 1. Estructura del CU ──────────────────────────────────────────────────
    cu = CU_COMPONENTS_2025.copy()
    cu_total = sum(cu.values())
    cu_bolsa_share = cu["G"] / cu_total

    result["cu_components"]   = cu
    result["cu_total"]        = cu_total
    result["bolsa_pct_of_cu"] = round(100 * cu_bolsa_share, 1)
    result["spread"]          = round(pi_gs - cu["G"], 1)   # pi_gs - solo componente bolsa

    # ── 2. Estadísticos de pi_bolsa ───────────────────────────────────────────
    bolsa_mean   = float(np.mean(pi_bolsa))
    bolsa_median = float(np.median(pi_bolsa))
    bolsa_std    = float(np.std(pi_bolsa))
    bolsa_p25    = float(np.percentile(pi_bolsa, 25))
    bolsa_p75    = float(np.percentile(pi_bolsa, 75))
    bolsa_min    = float(np.min(pi_bolsa))
    bolsa_max    = float(np.max(pi_bolsa))

    # Hora solar = 8h–16h (horas donde Udenar genera excedente)
    T = len(pi_bolsa)
    solar_mask = np.array([((h % 24) >= 8 and (h % 24) <= 16) for h in range(T)])
    bolsa_solar_mean = float(np.mean(pi_bolsa[solar_mask])) if solar_mask.any() else bolsa_mean

    result["estadisticos"] = {
        "media_aritmetica":   round(bolsa_mean,        1),
        "mediana":            round(bolsa_median,       1),
        "media_horas_solares":round(bolsa_solar_mean,   1),
        "desvio_std":         round(bolsa_std,           1),
        "percentil_25":       round(bolsa_p25,           1),
        "percentil_75":       round(bolsa_p75,           1),
        "minimo":             round(bolsa_min,           1),
        "maximo":             round(bolsa_max,           1),
        "cv_pct":             round(100 * bolsa_std / max(bolsa_mean, 1), 1),
    }

    # ── 3. Justificación del estimador elegido ────────────────────────────────
    # Para el análisis SA-1 se usa un pi_gb CONSTANTE como baseline de comparación.
    # La elección del estimador afecta la sensibilidad de C1 (que liquida excedentes
    # a ese precio). Para Udenar (mayor generador), la comparación relevante es
    # el precio en HORAS SOLARES, no el promedio global.
    result["estimador_elegido"]    = "media_aritmetica"
    result["pi_gb_usado"]          = round(bolsa_mean, 1)
    result["pi_gb_solar_relevante"]= round(bolsa_solar_mean, 1)
    result["diferencia_global_solar"] = round(bolsa_mean - bolsa_solar_mean, 1)

    # ── 4. Verbose ────────────────────────────────────────────────────────────
    if verbose:
        print("\n  Sec.3.6 -- Analisis de fuente y calibracion de precios")
        print("  " + "-"*60)
        print("\n  Estructura del CU institucional (COP/kWh):")
        print(f"  {'Componente':<20} {'COP/kWh':>8}  {'% del CU':>8}")
        print("  " + "-"*40)
        for comp, val in cu.items():
            pct = 100 * val / cu_total
            nota = " <- varia con bolsa XM" if comp == "G" else ""
            print(f"  {comp:<20} {val:>8.0f}  {pct:>7.1f}%{nota}")
        print(f"  {'TOTAL (CU)':<20} {cu_total:>8.0f}  100.0%")
        print(f"\n  CU usado en modelo: {pi_gs:.0f} COP/kWh")
        print(f"  Bolsa (componente G): {cu['G']:.0f} COP/kWh "
              f"({result['bolsa_pct_of_cu']:.1f}% del CU)")

        print(f"\n  Estadisticos de pi_bolsa (serie de {T} horas):")
        print(f"  {'Estimador':<28} {'COP/kWh':>8}")
        print("  " + "-"*38)
        est = result["estadisticos"]
        items = [
            ("Media aritmética (ELEGIDA)",  est["media_aritmetica"]),
            ("Mediana",                     est["mediana"]),
            ("Media horas solares (8-16h)", est["media_horas_solares"]),
            ("Percentil 25",                est["percentil_25"]),
            ("Percentil 75",                est["percentil_75"]),
            ("Desviación estándar",         est["desvio_std"]),
            ("CV (%)",                      est["cv_pct"]),
        ]
        for label, val in items:
            mark = " <-" if "ELEGIDA" in label else ""
            print(f"  {label:<28} {val:>8.1f}{mark}")

        print(f"\n  Justificación de media aritmética:")
        print(f"  • Es el estimador más conservador para C1 (no sobreestima beneficio")
        print(f"    de liquidación de excedentes a precio de bolsa).")
        print(f"  • La media global ({est['media_aritmetica']:.0f}) > media solar "
              f"({est['media_horas_solares']:.0f}): el modelo SA-1 usa precio mayor")
        print(f"    al que realmente enfrenta Udenar en horas de excedente solar.")
        print(f"  • Esto es CONSERVADOR para el P2P: si usáramos media solar, C1")
        print(f"    sería menos atractivo y la ventaja del P2P sería mayor.")
        print(f"  • Para la tesis se reporta el umbral de deserción con ambos:")
        print(f"    π_gb_media = {est['media_aritmetica']:.0f}  →  umbral P2P<C1 ≈ 325 COP/kWh")
        print(f"    π_gb_solar = {est['media_horas_solares']:.0f}  →  umbral más conservador")

    return result


# ── CAL-14: Techo CREG 101 066/2024 ──────────────────────────────────────────
# Resolucion CREG 101 066/2024 (vigente 01-DIC-2024) reemplaza el precio de
# escasez unico por tres niveles diferenciados (PEI/PE/PES) que se actualizan
# mensualmente. Al recortar pi_bolsa por PES (techo absoluto superior) se
# aproxima el PTB (Precio de Transacciones en Bolsa) que el generador
# efectivamente recibe tras activacion de OEF — el dato bruto del cache
# pydataxm (PrecBolsNaci) entrega el marginal sin recortar.
#
# Tabla mensual: data/precios_escasez_creg.csv
# Validacion de valores: sheet Comportamiento_PBNal_Horario en
#   sinergox.xm.com.co/.../03_Informe_Precios_y_Transacciones_MM_2025.xlsx
# Spec: docs/superpowers/specs/2026-05-01-cal14-creg101066-pes-ceiling.md

_CEILING_LEVEL_COL = {
    "PEI": "pei_cop_kwh",
    "PE":  "pe_cop_kwh",
    "PES": "pes_cop_kwh",
}


def load_creg_ceiling(
    t_start: str,
    t_end: str,
    level: str = "PES",
    csv_path: Optional[str] = None,
) -> pd.Series:
    """
    Carga la tabla mensual de precios de escasez CREG 101 066/2024.

    Parameters
    ----------
    t_start, t_end : str
        Rango ISO ``"YYYY-MM-DD"`` del horizonte solicitado.
    level : {"PEI", "PE", "PES"}
        Nivel de techo a devolver. Default ``"PES"`` (techo absoluto superior).
    csv_path : str, optional
        Ruta al CSV. Default ``data/precios_escasez_creg.csv``.

    Returns
    -------
    pd.Series
        Serie indexada por ``pd.Period(freq="M")`` con el techo en COP/kWh
        para cada mes del rango ``[t_start, t_end)``. Meses sin valor en el
        CSV se interpolan linealmente entre adyacentes con valor.

    Raises
    ------
    FileNotFoundError
        Si el CSV no existe.
    ValueError
        Si ``level`` no esta en ``{"PEI", "PE", "PES"}``.
    """
    if level not in _CEILING_LEVEL_COL:
        raise ValueError(
            f"level debe ser uno de {list(_CEILING_LEVEL_COL)}, recibido {level!r}"
        )

    if csv_path is None:
        csv_path = str(Path(__file__).parent / "precios_escasez_creg.csv")

    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Falta {csv_path}. Esperado: tabla mensual PEI/PE/PES CREG 101 066. "
            f"Ver docs/superpowers/specs/2026-05-01-cal14-creg101066-pes-ceiling.md"
        )

    df = pd.read_csv(path)
    df["mes"] = pd.PeriodIndex(df["mes"], freq="M")
    df = df.set_index("mes").sort_index()

    col = _CEILING_LEVEL_COL[level]
    # t_end es exclusivo: el ultimo periodo es el mes que contiene t_end - 1 dia.
    last_period = (pd.Timestamp(t_end) - pd.Timedelta(days=1)).to_period("M")
    target_idx = pd.period_range(
        start=pd.Timestamp(t_start).to_period("M"),
        end=last_period,
        freq="M",
    )
    serie = df[col].reindex(target_idx)
    if serie.isna().any():
        serie = serie.interpolate(method="linear", limit_direction="both")

    return serie


def apply_creg101066_ceiling(
    pi_bolsa: np.ndarray,
    t_start: str,
    level: str = "PES",
    effective_date: str = "2024-12-01",
    csv_path: Optional[str] = None,
    return_diagnostics: bool = False,
):
    """
    Aplica el techo CREG 101 066/2024 al precio de bolsa horario.

    Para cada hora ``k``, si la fecha local de esa hora es ``>= effective_date``,
    el precio se recorta a ``min(pi_bolsa[k], ceiling[mes_de_k])``. Antes de
    ``effective_date`` la serie se devuelve sin cambios.

    Parameters
    ----------
    pi_bolsa : np.ndarray  shape (T,)
        Serie horaria de precios de bolsa en COP/kWh.
    t_start : str
        Fecha de inicio del horizonte ``"YYYY-MM-DD"``.
    level : {"PEI", "PE", "PES"}
        Nivel del techo. Default ``"PES"`` (techo absoluto superior).
    effective_date : str
        Fecha desde la cual aplica CREG 101 066/2024. Default ``"2024-12-01"``.
    csv_path : str, optional
        Override de la ruta al CSV de techos.
    return_diagnostics : bool
        Si True, devuelve ``(pi_capped, diag)`` con metricas de recorte.

    Returns
    -------
    np.ndarray  shape (T,)
        Serie con techo aplicado.
    dict (opcional)
        Diagnosticos: ``hours_capped``, ``fraction``, ``delta_cop_total``,
        ``by_month``.
    """
    pi = np.asarray(pi_bolsa, dtype=float).copy()
    T = len(pi)

    idx = pd.date_range(t_start, periods=T, freq="1h")
    eff = pd.Timestamp(effective_date)
    t_end = (idx[-1] + pd.Timedelta(hours=1)).strftime("%Y-%m-%d")

    ceil_monthly = load_creg_ceiling(t_start, t_end, level=level,
                                      csv_path=csv_path)
    # Vector horario de techo: misma longitud que pi
    ceil_per_hour = np.array([
        ceil_monthly.loc[ts.to_period("M")] if ts >= eff else np.inf
        for ts in idx
    ], dtype=float)

    pi_pre = pi.copy()
    pi = np.minimum(pi, ceil_per_hour)

    if not return_diagnostics:
        return pi

    mask = pi_pre > ceil_per_hour
    diag = {
        "hours_capped":    int(mask.sum()),
        "fraction":        float(mask.mean()),
        "delta_cop_total": float((pi_pre - pi).sum()),
        "by_month":        {},
    }
    serie = pd.Series(pi_pre - pi, index=idx)
    for period, sub in serie.groupby(serie.index.to_period("M")):
        diag["by_month"][str(period)] = {
            "hours_capped": int((sub > 0).sum()),
            "delta_mean":   float(sub.mean()),
        }
    return pi, diag


def _print_ceiling_summary(diag: dict, level: str = "PES") -> None:
    """Imprime resumen humano del recorte aplicado por CREG 101 066."""
    print(f"  [creg-101-066] Techo {level} aplicado: "
          f"{diag['hours_capped']} horas recortadas "
          f"({100 * diag['fraction']:.2f}% del horizonte), "
          f"delta = {diag['delta_cop_total']:,.0f} COP/kWh acumulado")
    if diag["by_month"] and diag["hours_capped"] > 0:
        print(f"  [creg-101-066] Por mes:")
        print(f"                  {'Mes':<10} {'Horas-cap':>10} "
              f"{'Delta-medio COP/kWh':>22}")
        for mes, m in diag["by_month"].items():
            if m["hours_capped"] > 0:
                print(f"                  {mes:<10} {m['hours_capped']:>10} "
                      f"{-m['delta_mean']:>22.2f}")


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
