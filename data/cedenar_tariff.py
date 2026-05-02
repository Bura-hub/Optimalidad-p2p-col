"""
data/cedenar_tariff.py — Tarifa CU mensual de Cedenar por institución MTE
=========================================================================
Brayan S. Lopez-Mendez · Udenar 2026

Actividad 1.0 — calibración de precios para los escenarios C1-C4 con la
tarifa realmente facturada a las cinco instituciones de la comunidad MTE.
Reemplaza el escalar pi_gs = 650 COP/kWh por una serie mensual diferenciada
por (categoría tarifaria, nivel de tensión, propiedad del activo).

Referencia regulatoria
----------------------
    CU = G + T + D + Cv + PR + R          (Res. CREG 119/2007 art. 2)
    Tarifa aplicada = CU + COT            (Res. CREG 101-028/2023)
    No residencial:
        - Oficial/Especial: paga CU exactamente
        - Comercial/Industrial: paga CU + 20 % de contribución

Fuente de datos: https://scl.cedenar.com.co/Out/Tarifas/Tarifas.aspx
La página solo expone los últimos cuatro meses; los meses anteriores deben
solicitarse a Cedenar o reconstruirse desde facturas reales del proyecto MTE.
Los PDFs descargados se archivan en data/cedenar_pdfs/ con la convención
tarifa_YYYY-MM.pdf (ver data/cedenar_pdfs/README.md).

Mapeo institucional (provisional — verificar con factura)
---------------------------------------------------------
| Institución | Régimen jurídico   | Categoría        | NT asumido |
|-------------|--------------------|-----------------|-----------|
| Udenar      | Universidad pública| Oficial/Especial | 2         |
| HUDN        | Hospital público   | Oficial/Especial | 2         |
| Mariana     | Universidad privada| Comercial        | 2         |
| UCC         | Universidad privada| Comercial        | 2         |
| Cesmag      | Universidad privada| Comercial        | 2         |

El nivel de tensión real depende del transformador de cada campus y debe
confirmarse en la factura mensual. NT2 es el supuesto razonable para
campus académicos/hospitalarios con capacidad >5 kW.

API pública
-----------
- load_monthly_tariffs(csv_path)             -> pd.DataFrame
- effective_pi_gs(t_start, t_end, profile)   -> float (promedio horizonte)
- pi_gs_per_agent_hourly(agent_names, idx)   -> np.ndarray (N, T)
- print_tariff_summary(...)                  -> diagnóstico

Notas
-----
- Si una fecha del horizonte cae fuera de los meses cargados en el CSV,
  el módulo emite un warning y usa el fallback (default 650 COP/kWh).
- El módulo NO modifica los escenarios C1-C4: la integración es opt-in
  desde main_simulation.py.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pandas as pd


# ── Default: tarifa Cedenar abril-2026 (PDF tarifa_210.pdf) ──────────────────
# Se conserva en código como fallback verificable cuando el CSV no está.
# Valores en COP/kWh.
DEFAULT_PI_GS_FALLBACK = 650.0

TARIFA_ABRIL_2026 = {
    # (categoria, nivel_tension, propiedad) -> CU_aplicado COP/kWh
    ("oficial",   1, "cedenar"):    951.67,
    ("oficial",   1, "compartida"): 923.53,
    ("oficial",   1, "usuario"):    895.39,
    ("oficial",   2, "cedenar"):    799.16,
    ("oficial",   3, "cedenar"):    707.33,
    ("comercial", 1, "cedenar"):   1142.01,
    ("comercial", 1, "compartida"):1108.24,
    ("comercial", 1, "usuario"):   1074.47,
    ("comercial", 2, "cedenar"):    958.99,
    ("comercial", 3, "cedenar"):    848.80,
}

# ── Perfil tarifario por institución MTE ─────────────────────────────────────
# Asunciones provisionales: verificar nivel de tensión y propiedad con factura.
@dataclass(frozen=True)
class TariffProfile:
    categoria: str           # "oficial" | "comercial"
    nivel_tension: int       # 1 | 2 | 3
    propiedad: str           # "cedenar" | "compartida" | "usuario"


INSTITUTION_PROFILE: dict[str, TariffProfile] = {
    "Udenar":  TariffProfile("oficial",   2, "cedenar"),
    "HUDN":    TariffProfile("oficial",   2, "cedenar"),
    "Mariana": TariffProfile("comercial", 2, "cedenar"),
    "UCC":     TariffProfile("comercial", 2, "cedenar"),
    "Cesmag":  TariffProfile("comercial", 2, "cedenar"),
}


# ── Carga del CSV ───────────────────────────────────────────────────────────

CSV_DEFAULT_PATH = Path(__file__).parent / "tarifas_cedenar_mensual.csv"

# Columnas esperadas en el CSV
_REQUIRED_COLS = {
    "mes", "categoria", "nivel_tension", "propiedad", "CU_aplicado",
}


def load_monthly_tariffs(csv_path: str | Path | None = None) -> pd.DataFrame:
    """
    Lee tarifas_cedenar_mensual.csv y normaliza tipos.

    Columnas mínimas exigidas:
        mes (YYYY-MM), categoria, nivel_tension, propiedad, CU_aplicado.

    Columnas opcionales (componentes CREG 119/2007):
        Gm, Tm, Dnm, Cvm, PR, Rm, COT, fuente.

    Devuelve DataFrame indexado por (mes, categoria, nivel_tension, propiedad)
    con CU_aplicado como columna principal. Filas vacías o con CU_aplicado
    NaN se descartan silenciosamente (placeholders para meses pendientes).
    """
    path = Path(csv_path) if csv_path else CSV_DEFAULT_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró {path}. Crea el CSV con la plantilla "
            f"o invoca cedenar_tariff.print_template()."
        )

    df = pd.read_csv(path, encoding="utf-8-sig",
                     comment="#", skip_blank_lines=True)
    df.columns = [c.strip() for c in df.columns]

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(
            f"{path.name}: faltan columnas obligatorias {sorted(missing)}"
        )

    df["mes"] = df["mes"].astype(str).str.strip()
    df["categoria"] = df["categoria"].astype(str).str.strip().str.lower()
    df["propiedad"] = df["propiedad"].astype(str).str.strip().str.lower()
    df["nivel_tension"] = pd.to_numeric(df["nivel_tension"], errors="coerce")
    df["CU_aplicado"] = pd.to_numeric(df["CU_aplicado"], errors="coerce")

    # Descartar filas placeholder (CU vacío)
    df = df.dropna(subset=["CU_aplicado", "nivel_tension"])
    df["nivel_tension"] = df["nivel_tension"].astype(int)

    return df.set_index(
        ["mes", "categoria", "nivel_tension", "propiedad"]
    ).sort_index()


# ── Lookup mes a mes ────────────────────────────────────────────────────────

def _lookup_pi_gs(df: pd.DataFrame, mes_key: str,
                  profile: TariffProfile,
                  fallback: float = DEFAULT_PI_GS_FALLBACK,
                  warned: set | None = None) -> float:
    """
    Devuelve CU_aplicado para (mes, categoria, NT, propiedad).
    Si el mes no está cargado, usa fallback con warning único por mes.
    """
    key = (mes_key, profile.categoria, profile.nivel_tension, profile.propiedad)
    try:
        return float(df.loc[key, "CU_aplicado"])
    except KeyError:
        if warned is None or mes_key not in warned:
            warnings.warn(
                f"[cedenar_tariff] Mes {mes_key} ausente en CSV para "
                f"{profile.categoria}/NT{profile.nivel_tension}/{profile.propiedad}; "
                f"usando fallback {fallback:.0f} COP/kWh.",
                stacklevel=3,
            )
            if warned is not None:
                warned.add(mes_key)
        return float(fallback)


def _lookup_cvm(df: pd.DataFrame, mes_key: str,
                profile: TariffProfile,
                warned: set | None = None) -> float | None:
    """
    Devuelve el componente Cvm,i,j puro para (mes, categoria, NT, propiedad)
    en COP/kWh.

    CAL-10b.2 (literalidad CREG): la Resolucion CREG 174 de 2021 art. 25
    cita exactamente "el componente Cvm,i,j de la Resolucion CREG 119
    de 2007" para la energia permutada. NO incluye COT (cargo introducido
    en CREG 101 028/2023 que cubre obligaciones tributarias del
    comercializador). El COT se factura a usuarios regulares pero no se
    descuenta sobre la permuta segun la letra de CREG 174 art. 25.

    Versiones anteriores (CAL-10b en commit e06f70a) sumaban Cvm+COT por
    una interpretacion conservadora; tras revision contra el texto
    oficial via WebSearch (gestornormativo.creg.gov.co) se corrige a
    solo Cvm para fidelidad regulatoria.

    Si el mes no esta en el CSV o si Cvm es NaN, retorna None y emite
    warning una vez por mes ausente. El caller decide como rellenar
    (tipicamente as_component_c_array rellena con pi_gs * C_FRACTION).

    Ref: CREG 174/2021 art. 25; CREG 119/2007 art. 11 (definicion Cvm,i,j).
    """
    key = (mes_key, profile.categoria, profile.nivel_tension, profile.propiedad)
    try:
        cvm = float(df.loc[key, "Cvm"])
    except KeyError:
        if warned is None or mes_key not in warned:
            warnings.warn(
                f"[cedenar_tariff] Mes {mes_key} ausente en CSV para "
                f"{profile.categoria}/NT{profile.nivel_tension}/{profile.propiedad}; "
                f"componente C marcado como NaN (caller debe aplicar fallback).",
                stacklevel=3,
            )
            if warned is not None:
                warned.add(mes_key)
        return None

    if not np.isfinite(cvm):
        if warned is None or mes_key not in warned:
            warnings.warn(
                f"[cedenar_tariff] Cvm NaN para {mes_key} "
                f"{profile.categoria}/NT{profile.nivel_tension}; "
                f"componente C marcado como NaN.",
                stacklevel=3,
            )
            if warned is not None:
                warned.add(mes_key)
        return None

    return cvm


def effective_pi_gs(t_start: str | pd.Timestamp,
                    t_end: str | pd.Timestamp,
                    profile: TariffProfile,
                    csv_path: str | Path | None = None,
                    fallback: float = DEFAULT_PI_GS_FALLBACK) -> float:
    """
    Promedio horario-ponderado del CU_aplicado sobre [t_start, t_end).

    Este es el escalar que reemplaza al actual PGS_COP=650 cuando los
    escenarios C1-C4 reciben pi_gs como float. El promedio se pondera por
    el número de horas que cada mes calendario contribuye al horizonte.
    """
    df = load_monthly_tariffs(csv_path)
    idx = pd.date_range(t_start, t_end, freq="1h", inclusive="left")
    if len(idx) == 0:
        return float(fallback)

    warned: set = set()
    by_month = idx.to_series().groupby(idx.to_period("M")).size()
    weights, values = [], []
    for period, n_hours in by_month.items():
        mes_key = str(period)  # "YYYY-MM"
        v = _lookup_pi_gs(df, mes_key, profile, fallback, warned)
        weights.append(int(n_hours))
        values.append(v)

    w = np.asarray(weights, dtype=float)
    v = np.asarray(values, dtype=float)
    return float((w * v).sum() / w.sum())


def effective_pi_gs_per_agent(agent_names: list[str],
                                t_start: str | pd.Timestamp,
                                t_end: str | pd.Timestamp,
                                csv_path: str | Path | None = None,
                                fallback: float = DEFAULT_PI_GS_FALLBACK
                                ) -> np.ndarray:
    """
    Vector pi_gs efectivo por agente (escalar promedio horizonte por institución).

    Para cada `agent_name`, busca su `INSTITUTION_PROFILE` y devuelve el
    promedio horario-ponderado del CU_aplicado sobre [t_start, t_end).
    Si la institución no está mapeada o el mes falta del CSV, usa fallback.

    Devuelve: np.ndarray shape (N,) con pi_gs por agente en COP/kWh.

    Útil para diagnóstico per-agente y para el refactor futuro en que los
    escenarios C1-C4 acepten pi_gs como vector temporal.
    """
    out = np.full(len(agent_names), float(fallback), dtype=float)
    for n, name in enumerate(agent_names):
        prof = INSTITUTION_PROFILE.get(name)
        if prof is None:
            warnings.warn(
                f"[cedenar_tariff] Sin perfil tarifario para '{name}'; "
                f"se usa fallback {fallback:.0f} COP/kWh.",
                stacklevel=2,
            )
            continue
        out[n] = effective_pi_gs(t_start, t_end, prof,
                                  csv_path=csv_path, fallback=fallback)
    return out


def community_effective_pi_gs(agent_names: list[str],
                               t_start: str | pd.Timestamp,
                               t_end: str | pd.Timestamp,
                               weights: np.ndarray | None = None,
                               csv_path: str | Path | None = None,
                               fallback: float = DEFAULT_PI_GS_FALLBACK
                               ) -> float:
    """
    Escalar pi_gs comunitario: promedio (opcionalmente ponderado) del
    `effective_pi_gs_per_agent` entre las N instituciones.

    Parámetros
    ----------
    weights : np.ndarray opcional shape (N,)
        Pesos por agente (p. ej. demanda promedio en kWh). Se normalizan.
        Si es None, promedio aritmético uniforme.

    Devuelve: float — pi_gs comunitario para usar como escalar drop-in en
    el contrato actual de los escenarios C1-C4 (que aceptan pi_gs : float).
    """
    per_agent = effective_pi_gs_per_agent(agent_names, t_start, t_end,
                                            csv_path=csv_path,
                                            fallback=fallback)
    if weights is None:
        return float(per_agent.mean())
    w = np.asarray(weights, dtype=float)
    if w.shape != per_agent.shape:
        raise ValueError(
            f"weights shape {w.shape} != agentes {per_agent.shape}"
        )
    if w.sum() <= 0:
        return float(per_agent.mean())
    return float((per_agent * w).sum() / w.sum())


def pi_gs_per_agent_hourly(agent_names: list[str],
                            hour_index: pd.DatetimeIndex,
                            csv_path: str | Path | None = None,
                            fallback: float = DEFAULT_PI_GS_FALLBACK
                            ) -> np.ndarray:
    """
    Matriz pi_gs por agente y hora: shape (N, T), constante dentro del mes.

    Diseñada para el refactor futuro en que los escenarios C1-C4 acepten
    pi_gs como vector temporal en vez de escalar. Hoy el módulo no la usa.
    """
    df = load_monthly_tariffs(csv_path)
    N, T = len(agent_names), len(hour_index)
    out = np.full((N, T), float(fallback), dtype=float)
    months = hour_index.to_period("M").astype(str).to_numpy()

    warned: set = set()
    for n, name in enumerate(agent_names):
        prof = INSTITUTION_PROFILE.get(name)
        if prof is None:
            warnings.warn(
                f"[cedenar_tariff] Sin perfil tarifario para '{name}'; "
                f"se usa fallback {fallback:.0f} COP/kWh.",
                stacklevel=2,
            )
            continue
        # Cachear por mes para evitar lookups repetidos
        cache: dict[str, float] = {}
        for t in range(T):
            mes_key = months[t]
            if mes_key not in cache:
                cache[mes_key] = _lookup_pi_gs(df, mes_key, prof,
                                                fallback, warned)
            out[n, t] = cache[mes_key]
    return out


def cvm_per_agent_hourly(agent_names: list[str],
                          hour_index: pd.DatetimeIndex,
                          csv_path: str | Path | None = None,
                          ) -> np.ndarray:
    """
    Matriz (N, T) con el componente Cvm,i,j puro por (agente, hora),
    constante dentro del mes.

    CAL-10b.2 (literalidad CREG 174/2021 art. 25): este es el "peaje" de
    comercializacion que el comercializador cobra al AGPE sobre la energia
    permutada (Excedentes Tipo 1 en jerga industria). El texto oficial cita
    literalmente "el componente Cvm,i,j de la Resolucion CREG 119 de 2007".

    Reemplaza la aproximacion proporcional pi_gs * C_FRACTION (~13.85 %)
    introducida en CAL-10 por el dato real del CSV. Por linealidad CREG 174:

        savings_permuta = E_permutada * (pi_gs - Cvm)

    Cargos NO incluidos (revisado 2026-04-30 contra texto oficial):
    - COT (CREG 101 028/2023): cubre obligaciones tributarias del
      comercializador, NO citado en CREG 174 art. 25 sobre permuta.
    - Rm (Restricciones SIN), PR (Perdidas reconocidas): independientes
      de la actividad de comercializacion.

    Si un mes esta ausente del CSV o si Cvm es NaN, esa celda queda
    como np.nan; scenarios._pi_gs.as_component_c_array detecta los NaN y
    rellena con pi_gs[n, k] * C_FRACTION (fallback proporcional CAL-10).

    Historico:
        CAL-10b inicial (commit e06f70a) sumaba Cvm + COT en
        cvm_plus_cot_per_agent_hourly. Tras verificacion del texto oficial
        CREG 174/2021 art. 25 (WebSearch gestornormativo.creg.gov.co), se
        corrige a literalmente Cvm,i,j puro. Funcion renombrada para
        reflejar el contenido real.

    Ref: CREG 174/2021 art. 25; CREG 119/2007 art. 11.
    """
    df = load_monthly_tariffs(csv_path)
    N, T = len(agent_names), len(hour_index)
    out = np.full((N, T), np.nan, dtype=float)
    months = hour_index.to_period("M").astype(str).to_numpy()

    warned: set = set()
    for n, name in enumerate(agent_names):
        prof = INSTITUTION_PROFILE.get(name)
        if prof is None:
            warnings.warn(
                f"[cedenar_tariff] Sin perfil tarifario para '{name}'; "
                f"componente C marcado como NaN para todas sus horas.",
                stacklevel=2,
            )
            continue
        cache: dict[str, float | None] = {}
        for t in range(T):
            mes_key = months[t]
            if mes_key not in cache:
                cache[mes_key] = _lookup_cvm(df, mes_key, prof, warned)
            v = cache[mes_key]
            out[n, t] = v if v is not None else np.nan
    return out


def _lookup_g(df: pd.DataFrame, mes_key: str,
              profile: TariffProfile,
              warned: set | None = None) -> float | None:
    """
    Devuelve el componente G (Generación) del CU para
    (mes, categoría, NT, propiedad) en COP/kWh.

    CAL-12 (literalidad CREG 119/2007 arts. 6-8): G es el único
    componente del CU que se negocia vía contratos bilaterales (mercado
    mayorista). Los demás (T, D, Cvm, PR, Rm, COT) son cargos
    regulados que el usuario paga al OR/STN incluso bajo PPA. Por
    tanto, el ahorro real de un PPA bilateral es (G − π_ppa), no
    (CU − π_ppa). Ver ADR-0012.

    Origen: columna `Gm` del CSV `data/tarifas_cedenar_mensual.csv`,
    transcrita manualmente desde los PDFs `data/cedenar_pdfs/tarifa_*.pdf`
    publicados por CEDENAR.

    Si el mes no está en el CSV o si Gm es NaN, retorna None y emite
    warning una vez por mes ausente.

    Ref: CREG 119/2007 arts. 6-8; ADR-0012 (CAL-12).
    """
    key = (mes_key, profile.categoria, profile.nivel_tension, profile.propiedad)
    try:
        gm = float(df.loc[key, "Gm"])
    except KeyError:
        if warned is None or mes_key not in warned:
            warnings.warn(
                f"[cedenar_tariff] Mes {mes_key} ausente en CSV para "
                f"{profile.categoria}/NT{profile.nivel_tension}/{profile.propiedad}; "
                f"componente G marcado como NaN (caller debe aplicar fallback).",
                stacklevel=3,
            )
            if warned is not None:
                warned.add(mes_key)
        return None

    if not np.isfinite(gm):
        if warned is None or mes_key not in warned:
            warnings.warn(
                f"[cedenar_tariff] Gm NaN para {mes_key} "
                f"{profile.categoria}/NT{profile.nivel_tension}; "
                f"componente G marcado como NaN.",
                stacklevel=3,
            )
            if warned is not None:
                warned.add(mes_key)
        return None

    return gm


def g_component_per_agent_hourly(agent_names: list[str],
                                  hour_index: pd.DatetimeIndex,
                                  csv_path: str | Path | None = None,
                                  ) -> np.ndarray:
    """
    Matriz (N, T) con el componente G (Generación) del CU por
    (agente, hora), constante dentro del mes.

    G es el ÚNICO componente del CU que se negocia vía contratos
    bilaterales (CREG 119/2007 arts. 6-8). Los demás (T+D+Cvm+PR+Rm+COT)
    son cargos regulados que el usuario regulado paga al OR/STN incluso
    bajo PPA bilateral. Por tanto, el ahorro real de un PPA es

        savings = E_PPA × (G − π_ppa)

    NO `(CU − π_ppa)` como asumía C2 pre-CAL-12.

    Origen del dato: columna `Gm` del CSV
    `data/tarifas_cedenar_mensual.csv`, transcrita manualmente desde
    los PDFs `data/cedenar_pdfs/tarifa_*.pdf` (CEDENAR).

    Análoga 1-a-1 a `pi_gs_per_agent_hourly` (CAL-9) y
    `cvm_per_agent_hourly` (CAL-10b.2).

    Si un mes está ausente del CSV o si Gm es NaN, esa celda queda
    como np.nan; los callers deciden cómo rellenar (típicamente con
    `pi_bolsa[k]` como proxy del componente G del comercializador).

    Ref: CREG 119/2007 arts. 6-8; ADR-0012 (CAL-12).
    """
    df = load_monthly_tariffs(csv_path)
    N, T = len(agent_names), len(hour_index)
    out = np.full((N, T), np.nan, dtype=float)
    months = hour_index.to_period("M").astype(str).to_numpy()

    warned: set = set()
    for n, name in enumerate(agent_names):
        prof = INSTITUTION_PROFILE.get(name)
        if prof is None:
            warnings.warn(
                f"[cedenar_tariff] Sin perfil tarifario para '{name}'; "
                f"componente G marcado como NaN para todas sus horas.",
                stacklevel=2,
            )
            continue
        cache: dict[str, float | None] = {}
        for t in range(T):
            mes_key = months[t]
            if mes_key not in cache:
                cache[mes_key] = _lookup_g(df, mes_key, prof, warned)
            v = cache[mes_key]
            out[n, t] = v if v is not None else np.nan
    return out


def g_plus_commercialization_per_agent_hourly(
    agent_names: list[str],
    hour_index: pd.DatetimeIndex,
    csv_path: str | Path | None = None,
) -> np.ndarray:
    """
    Matriz (N, T) con el rango "negociable + ahorro comercialización"
    del CU = G + Cvm + COT, por (agente, hora), constante dentro del mes.

    Esta es la cota natural del precio bilateral PPA cuando el comprador
    es un **usuario no-regulado** (CAL-13, ADR-0013):

      - Bajo CREG 119/2007 arts. 6-8, G es el único componente negociable
        vía contrato bilateral. T+D+PR+Rm son cargos regulados al OR/STN
        que cualquier usuario (regulado o no) paga obligatoriamente.
      - Sin embargo, **Cvm + COT son margen del comercializador minorista**.
        Bajo CREG 086/1996 art. 1 mod. 039/2001, un usuario no-regulado
        no tiene comercializador minorista: contrata directamente con un
        generador (o con un representante del MEM). Por tanto, el usuario
        no-regulado **se ahorra Cvm + COT** además de poder negociar G.
      - El ahorro real del comprador no-regulado vía PPA es:

            savings_cons = E_PPA · ((G + Cvm + COT) − pi_ppa)

        donde el "rango negociable + ahorro de comercialización" es
        (G + Cvm + COT). Ese es el valor devuelto por esta función.

    Origen de datos:
      - G:    columna `Gm` del CSV `data/tarifas_cedenar_mensual.csv`
      - Cvm:  columna `Cvm`
      - COT:  columna `COT`
    Todos transcritos manualmente desde los PDFs
    `data/cedenar_pdfs/tarifa_*.pdf` (CEDENAR mensuales).

    Análoga 1-a-1 a `pi_gs_per_agent_hourly` (CAL-9),
    `cvm_per_agent_hourly` (CAL-10b.2) y
    `g_component_per_agent_hourly` (CAL-12).

    Si un mes está ausente del CSV o si alguno de los componentes es
    NaN, esa celda queda como `np.nan`; los callers deciden cómo
    rellenar (típicamente con `pi_bolsa[k] · ratio` como proxy).

    Ejemplo abril-2026 oficial NT2 (Udenar/HUDN):
      G = 310,96, Cvm = 176,41, COT = 38,73
      ⇒ G + Cvm + COT = 526,10 COP/kWh
      (vs CU completo 799,16 COP/kWh; peajes T+D+PR+Rm = 273,06 COP/kWh)

    Ref: CREG 119/2007 arts. 6-14; CREG 086/1996 art. 1 mod. 039/2001;
         Ley 143/1994 art. 41; ADR-0013 (CAL-13).
    """
    df = load_monthly_tariffs(csv_path)
    N, T = len(agent_names), len(hour_index)
    out = np.full((N, T), np.nan, dtype=float)
    months = hour_index.to_period("M").astype(str).to_numpy()

    warned: set = set()
    for n, name in enumerate(agent_names):
        prof = INSTITUTION_PROFILE.get(name)
        if prof is None:
            warnings.warn(
                f"[cedenar_tariff] Sin perfil tarifario para '{name}'; "
                f"componente G+Cvm+COT marcado como NaN para todas sus horas.",
                stacklevel=2,
            )
            continue
        cache: dict[str, float | None] = {}
        for t in range(T):
            mes_key = months[t]
            if mes_key not in cache:
                key = (mes_key, prof.categoria, prof.nivel_tension,
                       prof.propiedad)
                try:
                    gm = float(df.loc[key, "Gm"])
                    cvm = float(df.loc[key, "Cvm"])
                    cot = float(df.loc[key, "COT"])
                    if (np.isfinite(gm) and np.isfinite(cvm)
                            and np.isfinite(cot)):
                        cache[mes_key] = gm + cvm + cot
                    else:
                        cache[mes_key] = None
                except KeyError:
                    if mes_key not in warned:
                        warnings.warn(
                            f"[cedenar_tariff] Mes {mes_key} ausente en CSV "
                            f"para {prof.categoria}/NT{prof.nivel_tension}/"
                            f"{prof.propiedad}; G+Cvm+COT marcado como NaN.",
                            stacklevel=3,
                        )
                        warned.add(mes_key)
                    cache[mes_key] = None
            v = cache[mes_key]
            out[n, t] = v if v is not None else np.nan
    return out


def tolls_per_agent_hourly(agent_names: list[str],
                             hour_index: pd.DatetimeIndex,
                             csv_path: str | Path | None = None,
                             ) -> np.ndarray:
    """
    Matriz (N, T) con los **peajes regulados** (T + D + PR + Rm) del CU
    por (agente, hora), constante dentro del mes.

    CAL-16 (ADR-0016): los peajes T+D+PR+Rm son cargos regulados que
    cualquier usuario conectado al SIN paga obligatoriamente, sea
    regulado o no-regulado. Bajo CREG 119/2007 arts. 9, 10, 12, 13:

      - T  (Transmisión, STN): art. 9
      - D  (Distribución, OR): art. 10
      - PR (Pérdidas Reconocidas del sistema): art. 12
      - Rm (Restricciones del SIN): art. 13

    Estos componentes NO se ahorran vía PPA bilateral; sirven para
    auditar la reconciliación CU = G + Cvm + COT + (T+D+PR+Rm).

    Origen: columnas `Tm + Dnm + PR + Rm` del CSV
    `data/tarifas_cedenar_mensual.csv`, transcritas de los PDFs
    `data/cedenar_pdfs/tarifa_*.pdf` (CEDENAR).

    Análoga 1-a-1 a `g_component_per_agent_hourly` (CAL-12) y
    `g_plus_commercialization_per_agent_hourly` (CAL-13).

    Si un mes está ausente del CSV o si algún componente es NaN, esa
    celda queda como np.nan; los callers deciden cómo rellenar.

    Ejemplo abril-2026 oficial NT2 (Udenar/HUDN):
      T = 55,95 ; D = 165,37 ; PR = 21,09 ; Rm = 30,64
      ⇒ T+D+PR+Rm = 273,05 COP/kWh
      (vs CU completo 799,16 COP/kWh; G+Cvm+COT = 526,10 COP/kWh)

    Ref: CREG 119/2007 arts. 9, 10, 12, 13; ADR-0016 (CAL-16).
    """
    df = load_monthly_tariffs(csv_path)
    N, T = len(agent_names), len(hour_index)
    out = np.full((N, T), np.nan, dtype=float)
    months = hour_index.to_period("M").astype(str).to_numpy()

    warned: set = set()
    for n, name in enumerate(agent_names):
        prof = INSTITUTION_PROFILE.get(name)
        if prof is None:
            warnings.warn(
                f"[cedenar_tariff] Sin perfil tarifario para '{name}'; "
                f"peajes T+D+PR+Rm marcados como NaN para todas sus horas.",
                stacklevel=2,
            )
            continue
        cache: dict[str, float | None] = {}
        for t in range(T):
            mes_key = months[t]
            if mes_key not in cache:
                key = (mes_key, prof.categoria, prof.nivel_tension,
                       prof.propiedad)
                try:
                    tm  = float(df.loc[key, "Tm"])
                    dnm = float(df.loc[key, "Dnm"])
                    pr  = float(df.loc[key, "PR"])
                    rm  = float(df.loc[key, "Rm"])
                    if (np.isfinite(tm) and np.isfinite(dnm)
                            and np.isfinite(pr) and np.isfinite(rm)):
                        cache[mes_key] = tm + dnm + pr + rm
                    else:
                        cache[mes_key] = None
                except KeyError:
                    if mes_key not in warned:
                        warnings.warn(
                            f"[cedenar_tariff] Mes {mes_key} ausente en CSV "
                            f"para {prof.categoria}/NT{prof.nivel_tension}/"
                            f"{prof.propiedad}; peajes T+D+PR+Rm "
                            f"marcados como NaN.",
                            stacklevel=3,
                        )
                        warned.add(mes_key)
                    cache[mes_key] = None
            v = cache[mes_key]
            out[n, t] = v if v is not None else np.nan
    return out


def tariff_coverage(t_start: str | pd.Timestamp,
                     t_end: str | pd.Timestamp,
                     csv_path: str | Path | None = None) -> dict:
    """
    Devuelve cobertura del CSV sobre el horizonte [t_start, t_end).

    Returns dict con:
        meses_horizonte: list[str]  — meses YYYY-MM presentes en el horizonte
        meses_cargados : list[str]  — meses presentes en el CSV
        meses_faltantes: list[str]  — meses sin datos (caen al fallback)
    """
    df = load_monthly_tariffs(csv_path)
    idx = pd.date_range(t_start, t_end, freq="1h", inclusive="left")
    meses_horizonte = sorted({str(p) for p in idx.to_period("M").unique()})
    meses_cargados_csv = {str(m) for m, *_ in df.index}
    meses_cargados = [m for m in meses_horizonte if m in meses_cargados_csv]
    meses_faltantes = [m for m in meses_horizonte if m not in meses_cargados_csv]
    return {
        "meses_horizonte": meses_horizonte,
        "meses_cargados":  meses_cargados,
        "meses_faltantes": meses_faltantes,
    }


# ── Diagnóstico ─────────────────────────────────────────────────────────────

def print_tariff_summary(csv_path: str | Path | None = None,
                          t_start: str = "2025-07-01",
                          t_end: str = "2026-02-01") -> None:
    """
    Resumen tabular: tarifa efectiva por institución sobre [t_start, t_end).
    Útil para auditar la calibración antes de correr la simulación.
    """
    try:
        df = load_monthly_tariffs(csv_path)
    except FileNotFoundError as e:
        print(f"  [cedenar_tariff] {e}")
        return

    meses_cargados = sorted({str(m) for m, *_ in df.index})
    idx = pd.date_range(t_start, t_end, freq="1h", inclusive="left")
    meses_horizonte = sorted({str(p) for p in idx.to_period("M").unique()})
    faltantes = [m for m in meses_horizonte if m not in meses_cargados]

    print("\n  Tarifa Cedenar — resumen")
    print("  " + "-" * 60)
    print(f"  Horizonte simulación: {t_start} → {t_end}")
    print(f"  Meses cargados en CSV: {len(meses_cargados)} "
          f"({', '.join(meses_cargados) if meses_cargados else 'ninguno'})")
    if faltantes:
        print(f"  Meses faltantes en CSV: {len(faltantes)} "
              f"({', '.join(faltantes)})  → fallback "
              f"{DEFAULT_PI_GS_FALLBACK:.0f} COP/kWh")

    print(f"\n  {'Institución':<10} {'Categoría':<10} {'NT':>3} "
          f"{'Propiedad':<10} {'pi_gs efectiva':>15}")
    print("  " + "-" * 60)
    # El resumen ya reportó arriba los meses faltantes; suprimimos los warnings
    # individuales para no contaminar la salida.
    valores: list[float] = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name, prof in INSTITUTION_PROFILE.items():
            eff = effective_pi_gs(t_start, t_end, prof,
                                  csv_path=csv_path,
                                  fallback=DEFAULT_PI_GS_FALLBACK)
            valores.append(eff)
            print(f"  {name:<10} {prof.categoria:<10} "
                  f"{prof.nivel_tension:>3} {prof.propiedad:<10} "
                  f"{eff:>13.1f} COP/kWh")
    print("  " + "-" * 60)
    print(f"  Promedio simple comunidad: {np.mean(valores):.1f} COP/kWh")
    print(f"  (Comparar con escalar legacy PGS_COP = "
          f"{DEFAULT_PI_GS_FALLBACK:.0f} COP/kWh)")


def print_template() -> None:
    """Imprime una fila de plantilla CSV para copiar/pegar."""
    print("mes,categoria,nivel_tension,propiedad,Gm,Tm,Dnm,Cvm,PR,Rm,"
          "COT,CU_aplicado,fuente")
    print("2025-07,oficial,2,cedenar,,,,,,,,,(pendiente PDF Cedenar)")


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                       encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(
        description="Tarifa Cedenar mensual — Tesis Brayan López"
    )
    ap.add_argument("--csv", default=None,
                    help="Ruta al CSV (default: data/tarifas_cedenar_mensual.csv)")
    ap.add_argument("--t-start", default="2025-07-01")
    ap.add_argument("--t-end",   default="2026-02-01")
    ap.add_argument("--template", action="store_true",
                    help="Imprime una plantilla de fila CSV")
    args = ap.parse_args()

    if args.template:
        print_template()
    else:
        print_tariff_summary(csv_path=args.csv,
                             t_start=args.t_start, t_end=args.t_end)
