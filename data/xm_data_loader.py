"""
xm_data_loader.py  (v5 — IO + limpieza; selección puntual delegada)
-------------------------------------------------------------------
Este módulo conserva la capa de **lectura, agregación legacy y limpieza
genérica** (outliers + gaps). La selección puntual de qué medidor e
inversor usa cada institución, junto con la reconstrucción net→bruta,
vive ahora en ``data/preprocessing.py`` (Actividad 3.1, ver
``Documentos/notas_modelo_tesis.md``).

  Medidores (electricMeter / eletricMeter):
    - Columna exacta: 'totalActivePower'
    - Unidad: kW directamente
    - Resolución: 2 minutos → resample a 1h (media)
    - 4 medidores por institución; el preprocesamiento elige uno

  Inversores (Inverter / inverter / Inverters):
    - Columna exacta: 'acPower'
    - Unidad: W enteros (→ /1000 = kW)
    - 1-3 inversores por institución; el EMS ve uno solo

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

T_START = "2025-04-04"   # Horizonte sólido común sobre MedicionesMTE_v3
T_END   = "2025-12-16"   # (ver auditoría § 3.1): HUDN inversor arranca
                         # 2025-04-04 (max_start), HUDN+Fronius Udenar
                         # caen ~17-Dic. 257 días sin imputación.

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
    [LEGACY] Lee todos los CSV en la carpeta y sus subcarpetas y los
    suma. Conservado por compatibilidad con scripts antiguos; el
    pipeline principal ya no lo usa — ver ``data/preprocessing.py``
    para la selección puntual por institución.

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
    Limpieza genérica de series horarias (outliers + gaps). La
    no-negatividad se resuelve aguas arriba en ``preprocessing.py``
    (reconstrucción net→bruta o clip(lower=0) según semántica), por lo
    que aquí ya no se tratan los negativos como NaN.

    1. Outliers extremos → NaN, con umbral robusto a distribuciones bimodales:
       umbral = max(Q75 + 5·IQR, P99.5 · 1.2).
       El piso P99.5·1.2 evita cortar picos operacionales legítimos cuando
       la carga base es muy estable (IQR chico) — p. ej. Cesmag D.
    2. Interpolación lineal para gaps ≤ 3 h
    3. Forward/backward fill para gaps ≤ 24 h
    4. Resto → 0 (horas nocturnas para generación)
    """
    s = s.copy()

    q25, q75 = s.quantile(0.25), s.quantile(0.75)
    p995 = s.quantile(0.995)
    iqr = q75 - q25
    umbral_iqr = q75 + 5 * iqr if iqr > 0 else np.inf
    umbral_p995 = p995 * 1.2 if np.isfinite(p995) else np.inf
    umbral = max(umbral_iqr, umbral_p995)
    if np.isfinite(umbral) and umbral > 0:
        s[s > umbral] = np.nan

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

    def __init__(self, root_path: str,
                 demand_config: Optional[dict] = None,
                 ems_inverter_config: Optional[dict] = None,
                 reconstruction_inverters_config: Optional[dict] = None):
        self.root = Path(root_path)
        if not self.root.exists():
            raise FileNotFoundError(f"Carpeta no encontrada: {self.root}")
        self._demand_cfg = demand_config
        self._ems_inv_cfg = ems_inverter_config
        self._recon_inv_cfg = reconstruction_inverters_config

    def load(self, verbose: bool = True
             ) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
        # La selección puntual de medidor/inversor por institución y la
        # reconstrucción net→bruta viven en data/preprocessing.py.
        from data.preprocessing import build_demand_generation
        return build_demand_generation(
            self.root,
            demand_config=self._demand_cfg,
            ems_inverter_config=self._ems_inv_cfg,
            reconstruction_inverters_config=self._recon_inv_cfg,
            verbose=verbose,
        )

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
