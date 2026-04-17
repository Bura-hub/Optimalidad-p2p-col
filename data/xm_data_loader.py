"""
xm_data_loader.py  (v4 — validado con CSV reales de Cesmag)
------------------------------------------------------------
Hallazgos confirmados inspeccionando los CSV reales:

  Medidores (electricMeter / eletricMeter):
    - Columna exacta: 'totalActivePower'
    - Unidad: kW directamente (media ~8 kW, max ~44 kW)
    - Resolución: 2 minutos exactos → resample a 1h (media)
    - 4 medidores por institución → sumar todos

  Inversores (Inverter / inverter / Inverters):
    - Columna exacta: 'acPower'
    - Unidad: W enteros (media ~2300 W cuando activo, max ~15000 W)
              → dividir / 1000 para obtener kW
    - Solo registra cuando hay actividad (desde ~06:00, ceros de noche)
    - 1-3 inversores por institución → sumar todos

  Estación meteorológica:
    - Columna: 'irradiance' [W/m²] (opcional)

Período: 2025-07-01 → 2026-02-01  (5 160 horas para 215 días)
"""

import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional

warnings.filterwarnings("ignore")

# ── Configuración fija ────────────────────────────────────────────────────────

AGENTS = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]

METER_FOLDER    = {"Udenar": "electricMeter", "Mariana": "electricMeter",
                   "UCC":    "electricMeter", "HUDN":    "electricMeter",
                   "Cesmag": "eletricMeter"}   # typo en los datos originales

INVERTER_FOLDER = {"Udenar": "Inverters", "Mariana": "inverter",
                   "UCC":    "inverter",   "HUDN":    "inverter",
                   "Cesmag": "Inverter"}

WEATHER_FOLDER  = {"Udenar": "weatherstation", "Mariana": "weatherstation",
                   "UCC":    "weatherstation",  "HUDN":    "weatherStation",
                   "Cesmag": "weatherstation"}

T_START = "2025-07-01"
T_END   = "2026-02-01"

COL_DATE   = "date"
COL_DEMAND = "totalActivePower"   # kW
COL_GEN    = "acPower"            # W → /1000 → kW
COL_IRRAD  = "irradiance"         # W/m²


# ── Lectura de un CSV ─────────────────────────────────────────────────────────

def _read_one(path: Path, col: str) -> Optional[pd.Series]:
    """
    Lee un CSV y devuelve la columna `col` con índice DatetimeIndex.
    Compatible con pandas >= 2.0 (sin infer_datetime_format).
    """
    raw = path.read_bytes()
    enc = "utf-8"
    for e in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            raw.decode(e)
            enc = e
            break
        except Exception:
            pass

    try:
        df = pd.read_csv(path, encoding=enc, low_memory=False,
                         on_bad_lines="skip")
    except Exception:
        return None

    if COL_DATE not in df.columns or col not in df.columns:
        return None

    # pandas >= 2.0: to_datetime sin infer_datetime_format
    df[COL_DATE] = pd.to_datetime(df[COL_DATE], errors="coerce")
    df = df.dropna(subset=[COL_DATE]).set_index(COL_DATE)
    s  = pd.to_numeric(df[col], errors="coerce")
    # Eliminar timestamps duplicados promediando (evita ValueError en pd.concat)
    if s.index.duplicated().any():
        s = s.groupby(s.index).mean()
    return s


# ── Agregar una carpeta de CSVs → serie horaria ───────────────────────────────

def _aggregate(folder: Path, col: str,
               divide_by: float = 1.0) -> pd.Series:
    """
    Lee todos los CSV en la carpeta y sus subcarpetas,
    suma las series (distintos medidores/inversores = distintas cargas),
    resamplea a 1 hora (media) y filtra el período de interés.

    divide_by: 1.0 para kW (medidores), 1000.0 para W→kW (inversores)
    """
    idx = pd.date_range(T_START, T_END, freq="1h", inclusive="left")

    parts = []
    for path in sorted(folder.rglob("*.csv")):
        s = _read_one(path, col)
        if s is not None and len(s) > 0:
            parts.append(s)

    if not parts:
        return pd.Series(0.0, index=idx)

    # Alinear en el mismo eje temporal y sumar
    combined = pd.concat(parts, axis=1).sum(axis=1, min_count=1)

    # Filtrar período y resamplear a 1 hora (media de mediciones en esa hora)
    combined = combined.loc[T_START:T_END]
    hourly   = combined.resample("1h").mean()

    # Convertir unidad
    hourly = hourly / divide_by

    # Generación no puede ser negativa
    hourly = hourly.clip(lower=0)

    return hourly.reindex(idx)


# ── Limpieza estándar (Actividad 3.1 de la tesis) ────────────────────────────

def _clean(s: pd.Series, label: str = "") -> pd.Series:
    """
    1. Valores negativos → NaN
    2. Outliers estadísticos (Q75 + 5×IQR) → NaN
    3. Interpolación lineal para gaps ≤ 3 h
    4. Forward/backward fill para gaps ≤ 24 h
    5. Resto → 0 (horas nocturnas para generación)
    """
    s = s.copy()
    s[s < 0] = np.nan

    q25, q75 = s.quantile(0.25), s.quantile(0.75)
    iqr = q75 - q25
    if iqr > 0:
        s[s > q75 + 5 * iqr] = np.nan

    s = s.interpolate(method="time", limit=3)
    s = s.ffill(limit=24).bfill(limit=24)
    s = s.fillna(0.0)
    return s


# ── Clase principal ───────────────────────────────────────────────────────────

class MTEDataLoader:
    """
    Carga los datos empíricos del proyecto MTE y devuelve D[N,T] y G[N,T].

    Uso:
        loader = MTEDataLoader("C:/ruta/a/MedicionesMTE")
        D, G, index = loader.load()
        # D.shape == (5, 5160)   demanda real [kW]
        # G.shape == (5, 5160)   generación PV [kW]
        # index: DatetimeIndex horario
    """

    def __init__(self, root_path: str):
        self.root = Path(root_path)
        if not self.root.exists():
            raise FileNotFoundError(f"Carpeta no encontrada: {self.root}")

    def load(self, verbose: bool = True
             ) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:

        idx = pd.date_range(T_START, T_END, freq="1h", inclusive="left")

        if verbose:
            print(f"\n[MTEDataLoader] Raíz: {self.root}")
            print(f"  Período: {T_START} → {T_END}  ({len(idx)} horas)\n")

        D_list, G_list = [], []

        for n, agent in enumerate(AGENTS):
            adir = self._find(self.root, agent)
            if adir is None:
                if verbose:
                    print(f"  A{n} {agent}: CARPETA NO ENCONTRADA — usando ceros")
                D_list.append(np.zeros(len(idx)))
                G_list.append(np.zeros(len(idx)))
                continue

            # ── Demanda: totalActivePower ya en kW ───────────────────────
            mdir = self._find(adir, METER_FOLDER[agent])
            if mdir:
                d_raw = _aggregate(mdir, COL_DEMAND, divide_by=1.0)
                d = _clean(d_raw.reindex(idx).fillna(0), f"{agent}/D")
            else:
                if verbose:
                    print(f"  A{n} {agent}: sin carpeta medidores")
                d = pd.Series(0.0, index=idx)

            # ── Generación: acPower en W → /1000 → kW ────────────────────
            idir = self._find(adir, INVERTER_FOLDER[agent])
            if idir:
                g_raw = _aggregate(idir, COL_GEN, divide_by=1000.0)
                g = _clean(g_raw.reindex(idx).fillna(0), f"{agent}/G")
            else:
                if verbose:
                    print(f"  A{n} {agent}: sin carpeta inversores")
                g = pd.Series(0.0, index=idx)

            if verbose:
                print(f"  A{n} {agent}:")
                print(f"    D  media={d.mean():.2f} kW  "
                      f"max={d.max():.1f} kW  "
                      f"horas>0={int((d>0).sum())}/{len(d)}")
                print(f"    G  media={g.mean():.2f} kW  "
                      f"max={g.max():.1f} kW  "
                      f"horas>0={int((g>0).sum())}/{len(g)}")

            D_list.append(d.values)
            G_list.append(g.values)

        D = np.array(D_list, dtype=float)   # (N, T)
        G = np.array(G_list, dtype=float)   # (N, T)
        T = D.shape[1]

        if verbose:
            print(f"\n  D: {D.shape}  G: {G.shape}")
            print(f"  D total comunidad: {D.sum():.0f} kWh")
            print(f"  G total comunidad: {G.sum():.0f} kWh")
            print(f"  Cobertura G/D:     {G.sum()/max(D.sum(),1):.3f}")

        idx_tz = idx[:T].tz_localize(
            "America/Bogota",
            nonexistent="shift_forward",
            ambiguous="infer",
        )
        return D, G, idx_tz

    def load_weather(self) -> dict:
        """Carga irradiancia de las estaciones meteorológicas (opcional)."""
        result = {}
        idx = pd.date_range(T_START, T_END, freq="1h", inclusive="left")
        for agent in AGENTS:
            adir = self._find(self.root, agent)
            if adir is None:
                continue
            wdir = self._find(adir, WEATHER_FOLDER[agent])
            if wdir is None:
                continue
            parts = []
            for path in sorted(wdir.rglob("*.csv")):
                s = _read_one(path, COL_IRRAD)
                if s is not None and len(s) > 0:
                    parts.append(s)
            if parts:
                combined = pd.concat(parts, axis=1).mean(axis=1)
                combined = combined.loc[T_START:T_END]
                s_hourly = combined.resample("1h").mean().reindex(idx)
                s_hourly.index = idx.tz_localize(
                    "America/Bogota",
                    nonexistent="shift_forward",
                    ambiguous="infer",
                )
                result[agent] = s_hourly
        return result

    def _find(self, parent: Path, name: str) -> Optional[Path]:
        """Busca subcarpeta tolerante a capitalización."""
        exact = parent / name
        if exact.exists():
            return exact
        for sub in parent.iterdir():
            if sub.is_dir() and sub.name.lower() == name.lower():
                return sub
        return None


# ── Helpers de análisis ───────────────────────────────────────────────────────

def slice_horizon(D, G, index, start: str, end: str):
    """Extrae un subhorizonte del período completo."""
    mask = (index >= start) & (index < end)
    return D[:, mask], G[:, mask], index[mask]


def daily_profiles(D, G, index) -> tuple[np.ndarray, np.ndarray]:
    """
    Promedia los perfiles por hora del día (0–23).
    Útil para obtener los 24 valores representativos del modelo.
    Retorna D_avg(N,24) y G_avg(N,24).
    """
    N = D.shape[0]
    h = index.hour
    Da, Ga = np.zeros((N, 24)), np.zeros((N, 24))
    for hh in range(24):
        m = h == hh
        if m.sum() > 0:
            Da[:, hh] = D[:, m].mean(axis=1)
            Ga[:, hh] = G[:, m].mean(axis=1)
    return Da, Ga


def validate_load(D, G, index) -> dict:
    N, T = D.shape
    r = {"n_agents": N, "n_hours": T, "n_days": round(T / 24, 1),
         "start": str(index[0]), "end": str(index[-1])}
    for n, agent in enumerate(AGENTS[:N]):
        d, g = D[n], G[n]
        r[agent] = {
            "D_mean_kW":      round(float(d.mean()), 3),
            "D_max_kW":       round(float(d.max()),  3),
            "D_total_kWh":    round(float(d.sum()),  1),
            "G_mean_kW":      round(float(g.mean()), 3),
            "G_max_kW":       round(float(g.max()),  3),
            "G_total_kWh":    round(float(g.sum()),  1),
            "coverage_ratio": round(float(g.sum() / max(d.sum(), 1)), 4),
            "pct_zero_D":     round(float((d == 0).mean() * 100), 1),
            "pct_zero_G":     round(float((g == 0).mean() * 100), 1),
        }
    return r


def print_validation_report(r: dict) -> None:
    print("\n" + "="*65)
    print("  REPORTE DE CALIDAD — DATOS MTE")
    print("="*65)
    print(f"  Agentes: {r['n_agents']}  "
          f"Horas: {r['n_hours']}  "
          f"Días: {r['n_days']}")
    print(f"  Período: {r['start'][:10]} → {r['end'][:10]}")
    print(f"\n  {'Nodo':<10} {'D_med':>7} {'D_max':>7} "
          f"{'G_med':>7} {'G_max':>7} {'Cober.':>7} {'%0_G':>6}")
    print("  " + "-"*58)
    for agent in AGENTS:
        if agent not in r:
            continue
        a = r[agent]
        print(f"  {agent:<10} "
              f"{a['D_mean_kW']:>7.2f} {a['D_max_kW']:>7.2f} "
              f"{a['G_mean_kW']:>7.2f} {a['G_max_kW']:>7.2f} "
              f"{a['coverage_ratio']:>7.3f} {a['pct_zero_G']:>6.1f}%")
    print("="*65)
