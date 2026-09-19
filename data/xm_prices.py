"""
xm_prices.py  — Precios de bolsa XM y calibración del parámetro b
==================================================================
Brayan S. Lopez-Mendez · Udenar 2026

FUENTES DE DATOS (prioridad):
  1. API de XM (servapibi.xm.com.co, POST directo; ya no hace falta
     pydataxm), a traves de la cache data/precios_bolsa_xm_api.csv
  2. CSV descargado de Sinergox XM (descarga manual)
  3. Sintético calibrado con promedios mensuales REALES XM (solo sin API)

REGENERAR LA CACHE (una peticion por segundo, cada una anotada):
  python data/xm_prices.py --regenera-cache 2025-04-04 2026-02-01
      --registro outputs/run_<fecha>_descargas_xm.log   (en la misma linea)

DESCARGA MANUAL:
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
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

# Aqui habia un `warnings.filterwarnings("ignore")` global: al importar este
# modulo se callaban TODOS los avisos del proceso, incluido el del alias de
# despacho de core/ems_p2p.py, y el modulo MTE lo importa en cada hora. Se
# quito en la tarea P (2026-09-19). Si hace falta callar un aviso concreto,
# se filtra solo ese, con un `warnings.catch_warnings()` local.

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


# ── 1. API de XM (servapibi.xm.com.co) ───────────────────────────────────────
#
# Defecto 1 del informe del modulo MTE (2026-09-17): la cache de bolsa llevaba
# FECHAS FABRICADAS. pydataxm 0.3.16 pasa TODAS las columnas por
# `pd.to_numeric(errors="coerce")`, fecha incluida, de modo que la fecha
# llegaba siempre vacia; el parser la reconstruia por la posicion de la fila,
# los bloques de 28 dias pedian dos veces el dia frontera, y cada frontera
# corria un dia todo lo que venia despues. Desde el 2025-07-30 la cache estaba
# corrida de 1 a 7 dias, y la cola real se perdia al recortar.
#
# Ahora la peticion se hace directamente al API (POST, el mismo cuerpo que usa
# pydataxm por dentro) y la fecha se lee del JSON, que la trae en texto. Los
# bloques no se solapan, la fecha repetida se comprueba y se descarta, y el
# calendario se exige completo, 24 horas por dia. Una peticion por segundo
# como mucho, y cada una queda impresa (y en `registro`, si se da).

XM_API_HORARIO = "https://servapibi.xm.com.co/hourly"
XM_METRICA_BOLSA = "PrecBolsNaci"      # Precio Bolsa Nacional por Sistema
XM_ENTIDAD_BOLSA = "Sistema"
_XM_DIAS_POR_PETICION = 28             # el API admite 31 (MaxDays)
_XM_PAUSA_S = 1.0                      # una peticion por segundo como mucho
_XM_ULTIMA_PETICION = [0.0]
# Decimales de la cache: los de la cache de la tesis desde df80cbe. La serie
# que devuelve la descarga es la misma que se guarda, redondeada aqui.
_DECIMALES_CACHE = 2


def _xm_post(url: str, cuerpo: dict, registro: Optional[str] = None) -> dict:
    """Una peticion al API de XM, con pausa y registro. Falla en voz alta."""
    import json
    import time
    import urllib.error
    import urllib.request

    espera = _XM_PAUSA_S - (time.monotonic() - _XM_ULTIMA_PETICION[0])
    if espera > 0:
        time.sleep(espera)
    peticion = urllib.request.Request(
        url, data=json.dumps(cuerpo).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json"})
    cuando = datetime.now().astimezone().isoformat(timespec="seconds")
    _XM_ULTIMA_PETICION[0] = time.monotonic()
    try:
        with urllib.request.urlopen(peticion, timeout=60) as r:
            codigo, contenido = r.status, r.read()
    except urllib.error.HTTPError as e:
        codigo, contenido = e.code, e.read()
    linea = (f"{cuando}\tPOST {url}\t{json.dumps(cuerpo)}\t{codigo}\t"
             f"{len(contenido)} bytes")
    print(f"    [xm_api] {linea}")
    if registro:
        with open(registro, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    if codigo != 200:
        raise RuntimeError(f"El API de XM respondio {codigo} a {cuerpo}: "
                           f"{contenido[:300]!r}")
    return json.loads(contenido)


def _parse_api_items(items, metrica: str = XM_METRICA_BOLSA) -> pd.DataFrame:
    """Items del API horario a una tabla ancha: fecha real + Hour01..Hour24.

    La fecha se lee del campo ``Date`` con formato estricto: nunca se
    reconstruye por la posicion de la fila (defecto 1).
    """
    filas = []
    for it in items:
        entidades = it.get("HourlyEntities") or []
        if len(entidades) != 1:
            raise ValueError(f"{metrica} {it.get('Date')!r}: se esperaba una "
                             f"entidad, llegaron {len(entidades)}")
        valores = entidades[0]["Values"]
        filas.append({"Date": it["Date"],
                      **{f"Hour{h:02d}": valores.get(f"Hour{h:02d}")
                         for h in range(1, 25)}})
    df = pd.DataFrame(filas, columns=["Date"]
                      + [f"Hour{h:02d}" for h in range(1, 25)])
    return _parse_api_df(df)


def _parse_api_df(df: pd.DataFrame) -> pd.DataFrame:
    """Tabla ancha (Date, Hour01..Hour24) con la fecha como indice.

    La fecha tiene que venir en el dato (``YYYY-MM-DD``). Si falta o no se
    puede leer, es un error: antes se fabricaba por la posicion de la fila.
    """
    if "Date" not in df.columns:
        raise ValueError(f"La respuesta de XM no trae la columna Date "
                         f"({list(df.columns)}): sin fecha no se puede "
                         f"ubicar ningun precio")
    fechas = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="coerce")
    if fechas.isna().any():
        malas = df.loc[fechas.isna(), "Date"].tolist()[:5]
        raise ValueError(f"Fechas de XM ilegibles: {malas}. No se reconstruyen "
                         f"por posicion (defecto 1)")
    horas = [f"Hour{h:02d}" for h in range(1, 25)]
    tabla = df[horas].apply(pd.to_numeric, errors="coerce")
    tabla.index = pd.DatetimeIndex(fechas, name="Date")
    return tabla


def _deduplica_fechas(tabla: pd.DataFrame) -> pd.DataFrame:
    """Quita las fechas repetidas si son identicas; si difieren, falla."""
    rep = tabla.index.duplicated(keep=False)
    if not rep.any():
        return tabla.sort_index()
    for fecha, grupo in tabla[rep].groupby(level=0):
        if not all(grupo.iloc[i].equals(grupo.iloc[0])
                   for i in range(1, len(grupo))):
            raise ValueError(f"La fecha {fecha.date()} aparece {len(grupo)} "
                             f"veces con valores distintos")
    return tabla[~tabla.index.duplicated(keep="first")].sort_index()


def _serie_horaria(tabla: pd.DataFrame, dt_start, dt_end) -> pd.Series:
    """Tabla ancha por dia -> serie horaria en [dt_start, dt_end), completa.

    Exige el calendario entero y 24 horas con valor en cada dia: un dia o una
    hora que falte es un error, no se rellena (defecto 1).
    """
    dias = pd.date_range(dt_start, dt_end, freq="D", inclusive="left")
    fuera = tabla.index[(tabla.index < dias[0]) | (tabla.index > dias[-1])]
    if len(fuera):
        raise ValueError(f"XM devolvio dias fuera de lo pedido: "
                         f"{[str(d.date()) for d in fuera[:5]]}")
    tabla = tabla.reindex(dias)
    faltan_dia = tabla.index[tabla.isna().all(axis=1)]
    if len(faltan_dia):
        raise ValueError(f"Faltan {len(faltan_dia)} dias de {XM_METRICA_BOLSA} "
                         f"en [{dias[0].date()}, {dt_end}): "
                         f"{[str(d.date()) for d in faltan_dia[:10]]}")
    incompletos = tabla.index[tabla.isna().any(axis=1)]
    if len(incompletos):
        raise ValueError(f"{len(incompletos)} dias sin las 24 horas: "
                         f"{[str(d.date()) for d in incompletos[:10]]}")
    valores = tabla.to_numpy(dtype=float).reshape(-1)
    idx = pd.date_range(dias[0], periods=len(valores), freq="1h")
    return pd.Series(valores, index=idx, name="Precio_COP_kWh")


def _redondea_cache(serie: pd.Series) -> pd.Series:
    """Redondeo de la cache, con el ``round`` de Python como el de siempre."""
    return pd.Series([round(float(v), _DECIMALES_CACHE) for v in serie],
                     index=serie.index, name=serie.name, dtype=float)


def download_via_api(t_start="2025-07-01", t_end="2026-02-01",
                     save_path=None, registro=None, as_series=False):
    """
    Descarga el precio de bolsa horario del API de XM (``PrecBolsNaci``).

    Horizonte ``[t_start, t_end)`` en dias enteros (``"YYYY-MM-DD"``, t_end
    exclusivo). Devuelve la serie redondeada a ``_DECIMALES_CACHE``, la misma
    que se guarda en ``save_path``; ``as_series=True`` la devuelve con su
    indice horario. Pide bloques de hasta 28 dias SIN solape, a una peticion
    por segundo como mucho, e imprime cada peticion (y la anota en
    ``registro``, si se da). Cualquier fallo es un error: no hay datos a
    medias ni fechas reconstruidas (defecto 1).
    """
    dt_start = datetime.strptime(t_start, "%Y-%m-%d")
    dt_end = datetime.strptime(t_end, "%Y-%m-%d")
    if dt_end <= dt_start:
        raise ValueError(f"Horizonte vacio: [{t_start}, {t_end})")
    ultimo_dia = dt_end - timedelta(days=1)

    print(f"  [xm_api] {XM_METRICA_BOLSA} {t_start} -> {t_end} (exclusivo), "
          f"bloques de {_XM_DIAS_POR_PETICION} dias")
    bloques = []
    actual = dt_start
    while actual <= ultimo_dia:
        fin = min(actual + timedelta(days=_XM_DIAS_POR_PETICION - 1),
                  ultimo_dia)
        cuerpo = {"MetricId": XM_METRICA_BOLSA,
                  "StartDate": actual.strftime("%Y-%m-%d"),
                  "EndDate": fin.strftime("%Y-%m-%d"),     # inclusivo
                  "Entity": XM_ENTIDAD_BOLSA, "Filter": []}
        respuesta = _xm_post(XM_API_HORARIO, cuerpo, registro=registro)
        bloque = _parse_api_items(respuesta.get("Items") or [])
        pedidos = pd.date_range(actual, fin, freq="D")
        if not bloque.index.isin(pedidos).all():
            raise ValueError(f"El bloque {cuerpo['StartDate']}..."
                             f"{cuerpo['EndDate']} trajo dias fuera de lo "
                             f"pedido")
        bloques.append(bloque)
        actual = fin + timedelta(days=1)

    tabla = _deduplica_fechas(pd.concat(bloques))
    serie = _redondea_cache(_serie_horaria(tabla, dt_start, dt_end))
    print(f"  [xm_api] {len(serie)} h, media={serie.mean():.0f} COP/kWh")
    if save_path:
        _save_csv(serie, save_path)
        print(f"  [xm_api] Cache guardada en: {save_path}")
    return serie if as_series else serie.to_numpy(dtype=float)


# ── 2. CSV de precios (cache del API o descarga manual de Sinergox) ──────────

def _lee_csv_precios(path: Path) -> pd.Series:
    """Lee un CSV de precios a una serie horaria indexada por su hora REAL.

    Formatos aceptados:
      Wide:  Fecha ; Variable ; Hora 1 ; Hora 2 ; ... ; Hora 24
      Long:  Fecha , Hora (1 a 24) , Precio_COP_kWh
      SIMEM: Date , Values.Hour01 , ... , Values.Hour24
    Una hora repetida con valores distintos, una hora fuera de 1..24 o una
    fecha ilegible son errores. Las horas que faltan no se inventan: quedan
    ausentes del indice.
    """
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        first = f.readline()
    sep = ";" if first.count(";") > first.count(",") else ","
    df = pd.read_csv(path, sep=sep, encoding="utf-8-sig", low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]
    print(f"  [xm_csv] {path.name} — {len(df)} filas, cols: {list(df.columns[:6])}")

    fecha_col = next((c for c in df.columns
                      if any(k in c.lower() for k in ["fecha", "date", "time"])), None)
    hora_cols = [c for c in df.columns
                 if any(c.strip().lower().startswith(p)
                        for p in ["hora ", "hour ", "h0", "h1", "h2",
                                  "values.hour", "value.hour"])]
    price_col = next((c for c in df.columns
                      if any(k in c.lower()
                             for k in ["precio", "price", "valor", "bolsa", "kwh"])), None)
    hour_col = next((c for c in df.columns
                     if c.strip().lower() in ["hora", "hour", "h", "hh"]), None)
    if fecha_col is None:
        raise ValueError(f"{path.name}: sin columna de fecha. Columnas: "
                         f"{list(df.columns[:10])}")
    fechas = pd.to_datetime(df[fecha_col], errors="coerce")
    if fechas.isna().any():
        raise ValueError(f"{path.name}: {int(fechas.isna().sum())} fechas "
                         f"ilegibles, p. ej. "
                         f"{df.loc[fechas.isna(), fecha_col].tolist()[:3]}")

    if len(hora_cols) >= 10:
        def hn(c):
            digits = "".join(x for x in c if x.isdigit())
            return int(digits) if digits else 99
        hc = sorted(hora_cols, key=hn)
        if [hn(c) for c in hc] != list(range(1, 25)):
            raise ValueError(f"{path.name}: las columnas de hora no son 1..24: "
                             f"{hc}")
        tabla = df[hc].apply(pd.to_numeric, errors="coerce")
        tabla.index = pd.DatetimeIndex(fechas.dt.normalize())
        tabla = _deduplica_fechas(tabla)
        valores = tabla.to_numpy(dtype=float).reshape(-1)
        idx = (tabla.index.repeat(24)
               + pd.to_timedelta(np.tile(np.arange(24), len(tabla)), unit="h"))
        serie = pd.Series(valores, index=idx)
    elif price_col is not None:
        valores = pd.to_numeric(df[price_col], errors="coerce")
        if hour_col:
            h = pd.to_numeric(df[hour_col], errors="coerce")
            if h.isna().any() or not h.between(1, 24).all() \
                    or not (h == h.round()).all():
                raise ValueError(f"{path.name}: la columna {hour_col!r} tiene "
                                 f"horas fuera de 1..24 o vacias")
            idx = fechas.dt.normalize() + pd.to_timedelta(h - 1, unit="h")
        else:
            idx = fechas
        serie = pd.Series(valores.to_numpy(dtype=float),
                          index=pd.DatetimeIndex(idx))
    else:
        raise ValueError(f"{path.name}: formato no reconocido. Columnas: "
                         f"{list(df.columns[:10])}")

    serie = serie[~serie.isna()]
    rep = serie.index.duplicated(keep=False)
    if rep.any():
        distintas = serie[rep].groupby(level=0).nunique()
        if (distintas > 1).any():
            raise ValueError(f"{path.name}: {int((distintas > 1).sum())} horas "
                             f"repetidas con precios distintos, p. ej. "
                             f"{distintas[distintas > 1].index[0]}")
        serie = serie[~serie.index.duplicated(keep="first")]
    return serie.sort_index()


def load_xm_prices(csv_path, t_start="2025-07-01", t_end="2026-02-01",
                   estricto=False):
    """
    Precios horarios de ``[t_start, t_end)`` leidos de un CSV, por su fecha.

    Devuelve un vector con exactamente una hora por cada hora del horizonte,
    o ``None`` si el fichero no existe o no tiene ninguna hora del horizonte.
    Si cubre el horizonte solo en parte, devuelve ``None`` (la cache se
    vuelve a pedir) o, con ``estricto=True``, falla nombrando las horas que
    faltan. Nunca rellena con la mediana (defecto 7): antes pedir del
    2026-01-28 al 2026-02-05 devolvia las 96 horas inexistentes de febrero a
    196,79, y un rango del todo fuera devolvia un vector de NaN en vez de
    ``None``, con lo que el defecto 1 no se veia nunca.
    """
    path = Path(csv_path)
    if not path.exists():
        return None
    serie = _lee_csv_precios(path)
    t0 = pd.Timestamp(t_start)
    t1 = pd.Timestamp(t_end)
    if t1 <= t0:
        raise ValueError(f"Horizonte vacio: [{t_start}, {t_end})")
    idx = pd.date_range(t0, t1, freq="1h", inclusive="left")
    horizonte = serie.reindex(idx)
    faltan = idx[horizonte.isna().to_numpy()]
    if len(faltan) == len(idx):
        print(f"  [xm_csv] {path.name} no tiene ninguna hora de "
              f"[{t_start}, {t_end})")
        return None
    if len(faltan):
        msg = (f"{path.name} no cubre [{t_start}, {t_end}): faltan "
               f"{len(faltan)} de {len(idx)} horas, de {faltan[0]} a "
               f"{faltan[-1]}")
        if estricto:
            raise ValueError(msg + ". No se rellenan (defecto 7)")
        print(f"  [xm_csv] {msg}; no se usa")
        return None
    prices = horizonte.to_numpy(dtype=float)
    print(f"  [xm_csv] {len(prices)}h, media={prices.mean():.0f} COP/kWh")
    return prices


# ── 3. Sintético calibrado ────────────────────────────────────────────────────

def generate_synthetic_prices(T, t_start="2025-07-01",
                               scenario="2025_real", seed=42, dt=1.0):
    """
    Serie sintética calibrada con promedios mensuales REALES de XM.
    Incluye patrón intradiario colombiano y efecto día de semana.
    """
    rng = np.random.default_rng(seed)
    ref = XM_PRICES_REFERENCE.get(scenario, XM_PRICES_REFERENCE["2025_real"])
    dt_start = pd.Timestamp(t_start)
    idx    = pd.date_range(dt_start, periods=T, freq=_paso(dt))
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

# CAL-43: procedencia efectiva de la ultima serie de bolsa devuelta por
# `get_pi_bolsa`. Existe porque el intento 4 sustituye la serie real por
# una SINTETICA y hasta ahora eso solo se sabia leyendo stdout.
ULTIMA_FUENTE = None

def get_pi_bolsa(T, t_start="2025-07-01", t_end="2026-02-01",
                 csv_path=None, use_api=True,
                 scenario="2025_real", seed=42,
                 apply_ceiling=True,
                 ceiling_level="PES",
                 dt=1.0):
    """
    Obtiene vector de precios bolsa pi_bolsa (T,) en COP/kWh.

    Prioridad de fuentes: API de XM (por su cache, que tiene que cubrir el
    horizonte entero) → CSV local → sintético calibrado. Con ``use_api``, un
    fallo de la descarga es un error: ya no cae a los sinteticos.

    Parameters
    ----------
    apply_ceiling : bool
        Si True (default), aplica el techo CREG 101 066/2024 a la serie
        antes de retornarla. Ver ``apply_creg101066_ceiling``. CAL-14.
    ceiling_level : {"PEI", "PE", "PES"}
        Nivel del techo. Default ``"PES"`` (techo absoluto superior).
    dt : float
        Duracion del paso en horas (CAL-46). XM publica precio HORARIO, de
        modo que a paso fino cada precio se replica sobre los subpasos de su
        hora: la resolucion de la bolsa no acota la del modelo, solo la del
        residual y la de los escenarios regulatorios. `T` cuenta pasos, no
        horas. Antes de CAL-46, pedir T pasos de quince minutos devolvia una
        serie horaria truncada y rellenada con la mediana, sin aviso.
    """
    global ULTIMA_FUENTE
    base_dir = Path(__file__).parent

    # Numero de horas de reloj que cubre el horizonte de T pasos.
    if dt == 1.0:
        n_sub, T_horas = 1, T
    else:
        n_sub = 1.0 / dt
        if abs(n_sub - round(n_sub)) > 1e-9:
            raise ValueError(f"paso de {dt} h no divide la hora en partes enteras")
        n_sub = int(round(n_sub))
        T_horas = int(np.ceil(T / n_sub))

    prices = None
    ULTIMA_FUENTE = None

    # Intento 1: API de XM, a traves de su cache. La cache canonica
    # (`precios_bolsa_xm_api.csv`, versionada) solo vale si cubre el horizonte
    # ENTERO, por fecha (defecto 1: antes valia cualquier fichero con ese
    # nombre, sin mirar sus fechas, y lo que faltara se rellenaba con la
    # mediana). Si no lo cubre, se descarga ese horizonte a una cache que
    # lleva el horizonte en el nombre; la canonica solo se reescribe a mano,
    # con `--regenera-cache`. Un fallo de la descarga es un error: no cae en
    # silencio a los precios sinteticos.
    if use_api:
        cache = base_dir / CACHE_BOLSA
        prices = load_xm_prices(str(cache), t_start, t_end)
        if prices is not None:
            ULTIMA_FUENTE = f"cache_api:{cache.name}"
        else:
            cache_h = _cache_de_horizonte(base_dir, t_start, t_end)
            prices = load_xm_prices(str(cache_h), t_start, t_end)
            if prices is not None:
                ULTIMA_FUENTE = f"cache_api:{cache_h.name}"
            else:
                prices = download_via_api(t_start, t_end,
                                          save_path=str(cache_h))
                ULTIMA_FUENTE = f"api_xm:{cache_h.name}"

    # Intento 2: CSV explícito. Si cubre el horizonte solo en parte, error.
    if prices is None and csv_path:
        prices = load_xm_prices(csv_path, t_start, t_end, estricto=True)
        if prices is not None:
            ULTIMA_FUENTE = f"csv:{Path(csv_path).name}"

    # Intento 3: CSV automático en data/. Igual: en parte, error.
    if prices is None:
        for name in ["precios_bolsa_xm.csv", "xm_precios_bolsa.csv",
                      "precio_bolsa_xm.csv", "PrecioBolsa.csv",
                      "Precio_Bolsa_Nacional.csv"]:
            p = base_dir / name
            if p.exists():
                prices = load_xm_prices(str(p), t_start, t_end, estricto=True)
                if prices is not None:
                    ULTIMA_FUENTE = f"csv_auto:{name}"
                    break

    # Intento 4: sintético calibrado (solo sin API, use_api=False)
    if prices is None:
        print(f"  [xm] Sintético calibrado. Para datos reales:")
        print(f"    use_api=True (descarga del API de XM, servapibi.xm.com.co)")
        print(f"    o descargar CSV de sinergox.xm.com.co → Históricos → Precios")
        print(f"    y guardarlo como: {base_dir}/precios_bolsa_xm.csv")
        # CAL-43: la sustitucion por precios SINTETICOS solo dejaba rastro
        # en una linea de stdout. Si el log se pierde o no se lee, una
        # corrida entera puede salir de precios inventados sin que nada en
        # el artefacto lo diga. `ULTIMA_FUENTE` viaja a la hoja Diagnostico.
        ULTIMA_FUENTE = f"SINTETICO:{scenario}"
        prices = generate_synthetic_prices(T_horas, t_start, scenario, seed)

    prices = _adj(prices, T_horas)

    # CAL-46: de horario al paso del modelo. El precio de una hora rige en
    # todos sus subpasos.
    if n_sub != 1:
        prices = np.repeat(prices, n_sub)[:T]

    # CAL-14: aplicar techo CREG 101 066/2024 (PES por defecto).
    if apply_ceiling:
        prices, diag = apply_creg101066_ceiling(
            prices, t_start, level=ceiling_level,
            return_diagnostics=True, dt=dt)
        _print_ceiling_summary(diag, level=ceiling_level)

    return prices


def _adj(prices, T):
    """Las T primeras horas del horizonte, que empieza en t_start.

    Si la serie trae menos de T horas es un error (defecto 7): antes se
    rellenaba el final con la mediana, sin aviso.
    """
    prices = np.asarray(prices, dtype=float)
    if len(prices) < T:
        raise ValueError(
            f"La serie de bolsa trae {len(prices)} horas y el horizonte pide "
            f"{T}. No se rellena con la mediana (defecto 7).")
    return prices[:T]


# Cache canonica de la bolsa horaria (versionada; ver `--regenera-cache`).
CACHE_BOLSA = "precios_bolsa_xm_api.csv"


def _cache_de_horizonte(base_dir: Path, t_start, t_end) -> Path:
    """Cache de una descarga que la canonica no cubre: el horizonte en el nombre."""
    d0 = pd.Timestamp(t_start).strftime("%Y-%m-%d")
    d1 = pd.Timestamp(t_end).strftime("%Y-%m-%d")
    return base_dir / f"precios_bolsa_xm_api_{d0}_{d1}.csv"


def _save_csv(serie: pd.Series, path):
    """Escribe la cache con la hora REAL de cada precio (defecto 1).

    Antes recibia un vector y le ponia fechas por posicion desde el inicio
    pedido, de modo que el fichero salia denso y contiguo aunque los datos
    estuvieran corridos. Ahora exige la serie con su indice horario, y el
    fichero se escribe entero a un temporal antes de sustituir al anterior.
    """
    if not isinstance(serie, pd.Series) \
            or not isinstance(serie.index, pd.DatetimeIndex):
        raise TypeError("_save_csv necesita una serie con indice horario "
                        "(DatetimeIndex): sin la hora real no se escribe")
    rows = [{"Fecha": ts.strftime("%Y-%m-%d"),
             "Hora": ts.hour + 1,
             "Precio_COP_kWh": round(float(p), _DECIMALES_CACHE)}
            for ts, p in serie.items()]
    tmp = Path(str(path) + ".tmp")
    pd.DataFrame(rows).to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)


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

# Inversor de cada institucion, es decir la clave de B_CALIBRATED que le toca.
# Los nombres se comparan TAL CUAL: un nombre que no este aqui escrito
# exactamente igual es un error (defecto 4a del informe del modulo MTE,
# 2026-09-17). Antes caia en silencio al valor por defecto, y con los nombres
# en minusculas las cinco salian con el mismo b, sin error ni aviso: se perdia
# la heterogeneidad de CAL-6 que el arreglo del 2026-05-06 habia recuperado.
INVERTER_BY_AGENT = {
    "Udenar":  "Udenar_fronius",
    "Mariana": "Mariana_fronius",
    "UCC":     "UCC_fronius",
    "HUDN":    "HUDN_fronius",
    "Cesmag":  "Cesmag_inv",
}

# Irradiancia de referencia del ajuste de b y la que se supone por defecto
# (kWh/m2/dia).
_IRR_REF_B = 4.5
_IRR_DEFECTO_B = 4.2


def _ajuste_irradiancia(irradiance_kwh_m2_day: float) -> float:
    """Factor que multiplica la tabla B_CALIBRATED (CAL-6)."""
    return _IRR_REF_B / max(irradiance_kwh_m2_day, 1.0)


def calibrate_b_parameters(agent_names, *,
                           irradiance_kwh_m2_day=_IRR_DEFECTO_B):
    """LCOE empírico por agente (CAL-6 corregido 2026-05-06).

    El lookup original `B_CALIBRATED.get(f"{n.lower()}_fronius", ...)`
    fallaba por case-mismatch (las claves de B_CALIBRATED están
    capitalizadas, p.ej. "Udenar_fronius") y todas las búsquedas caían
    al fallback `default_pasto = 220`. Como consecuencia los 5 agentes
    obtenían el mismo valor uniforme, anulando la heterogeneidad
    intencional de CAL-6 (Cesmag = 210 por inversor distinto).

    Fix: dict explícito INVERTER_BY_AGENT que matchea las claves reales
    de B_CALIBRATED.

    Qué devuelve de verdad (defecto 4c, 2026-09-18): la tabla por el ajuste
    de irradiancia, ``B_CALIBRATED[inversor] × adj`` con
    ``adj = 4,5 / max(irradiancia, 1)``. Con la irradiancia por defecto,
    4,2 kWh/m2/dia, ``adj = 1,0714...`` y el vector de las cinco es
    ``{241,07 × 4; 225,00}``: los cuatro Fronius a 241,0714... y Cesmag a
    225,00 exactos. **No** es la tabla ``{225, 225, 225, 225, 210}``. Que
    Cesmag salga en 225 es una coincidencia del ajuste (210 × 4,5 / 4,2), no
    un vector sin escalar. El ajuste es una decision de calibracion
    documentada y no se cambia: moveria el b de todas las horas.

    Un nombre que no este en ``INVERTER_BY_AGENT`` escrito exactamente igual
    lanza ``ValueError`` (defecto 4a). ``capacity_kw`` se elimino (defecto
    4d): b no depende de la capacidad instalada y ningun llamador lo pasaba;
    la irradiancia va por nombre, para que un segundo argumento posicional
    falle en vez de leerse como irradiancia.
    """
    desconocidos = [n for n in agent_names if n not in INVERTER_BY_AGENT]
    if desconocidos:
        pistas = {n: k for n in desconocidos for k in INVERTER_BY_AGENT
                  if str(n).strip().lower() == k.lower()}
        raise ValueError(
            f"Agentes sin inversor conocido: {desconocidos}. Los nombres "
            f"validos son {list(INVERTER_BY_AGENT)}, escritos exactamente asi"
            + (f"; quiza quiso decir {pistas}" if pistas else "")
            + ". Antes caian en silencio al valor por defecto y se perdia la "
              "heterogeneidad de b (defecto 4a).")
    adj = _ajuste_irradiancia(irradiance_kwh_m2_day)
    b = [B_CALIBRATED[INVERTER_BY_AGENT[n]] * adj for n in agent_names]
    return np.array(b, dtype=float)


def get_b_for_real_data(N, agent_names):
    """Vector b (N,) en COP/kWh para el modo real.

    Si hay menos nombres que agentes, los que faltan llevan el valor por
    defecto de la tabla con el MISMO ajuste de irradiancia que los demas
    (defecto 4b): antes quedaban sin ajustar, en otra escala.
    """
    b = calibrate_b_parameters(agent_names)
    if len(b) < N:
        relleno = (B_CALIBRATED["default_pasto"]
                   * _ajuste_irradiancia(_IRR_DEFECTO_B))
        b = np.pad(b, (0, N-len(b)), constant_values=relleno)
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
# Spec: especificacion de diseno interna (CAL-14, techo PES CREG 101 066)

_CEILING_LEVEL_COL = {
    "PEI": "pei_cop_kwh",
    "PE":  "pe_cop_kwh",
    "PES": "pes_cop_kwh",
}


def _hora_local(t, nombre: str = "t_start") -> pd.Timestamp:
    """Instante como hora local de America/Bogota, sin zona (defecto 6).

    Una fecha u hora SIN zona ya es hora local de Bogota y se devuelve tal
    cual: no se toca ni se reinterpreta (el modulo MTE depende de eso). Una
    CON zona designa un instante absoluto y se convierte a America/Bogota
    antes de quitarle la zona; antes lanzaba un ``TypeError`` al compararla
    con la fecha de vigencia. Una hora UTC escrita sin zona no se puede
    distinguir de una local: el llamador tiene que pasarla con su zona.
    """
    ts = pd.Timestamp(t)
    if ts is pd.NaT:
        raise ValueError(f"{nombre}={t!r} no es una fecha")
    if ts.tz is not None:
        ts = ts.tz_convert("America/Bogota").tz_localize(None)
    return ts


def load_creg_ceiling(
    t_start: str,
    t_end: str,
    level: str = "PES",
    csv_path: Optional[str] = None,
    return_info: bool = False,
) -> pd.Series:
    """
    Carga la tabla mensual de precios de escasez CREG 101 066/2024.

    Parameters
    ----------
    t_start, t_end : str o Timestamp
        Horizonte ``[t_start, t_end)``, con ``t_end`` EXCLUSIVO y con su
        hora: el ultimo mes es el que contiene el ultimo instante anterior a
        ``t_end``. ``"2026-02-01"`` llega hasta enero; ``"2025-12-01 01:00"``
        cubre diciembre. Hora local de America/Bogota; una fecha con zona se
        convierte (ver ``_hora_local``).
    level : {"PEI", "PE", "PES"}
        Nivel de techo a devolver. Default ``"PES"`` (techo absoluto superior).
    csv_path : str, optional
        Ruta al CSV. Default ``data/precios_escasez_creg.csv``.
    return_info : bool
        Si True devuelve ``(serie, info)``, con ``info["meses_tabla"]`` (los
        meses que traen valor en el fichero) e ``info["meses_interpolados"]``
        (los que no lo traen y se interpolaron entre dos que si).

    Returns
    -------
    pd.Series
        Serie indexada por ``pd.Period(freq="M")`` con el techo en COP/kWh
        para cada mes del horizonte. Un mes sin valor ENTRE dos meses con
        valor se interpola linealmente en el tiempo.

    Raises
    ------
    FileNotFoundError
        Si el CSV no existe.
    ValueError
        Si ``level`` no esta en ``{"PEI", "PE", "PES"}``; si el horizonte
        esta vacio; o si pide un mes anterior al primero o posterior al
        ultimo con valor en la tabla (defecto 3: antes se le daba el techo
        del mes mas cercano, sin aviso).
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
            f"Ver la especificacion de diseno interna del techo PES (CAL-14)."
        )

    df = pd.read_csv(path)
    df["mes"] = pd.PeriodIndex(df["mes"], freq="M")
    df = df.set_index("mes").sort_index()

    col = _CEILING_LEVEL_COL[level]
    # Defecto 2: t_end llega con su hora y es exclusivo. Antes llegaba
    # truncado a la fecha y aqui se le restaba un dia entero a ciegas, de
    # modo que un horizonte que terminaba el dia 1 de un mes antes de la
    # medianoche pedia hasta el mes ANTERIOR y el techo del ultimo mes no
    # estaba: KeyError tres lineas despues.
    t0 = _hora_local(t_start, "t_start")
    t1 = _hora_local(t_end, "t_end")
    if t1 <= t0:
        raise ValueError(
            f"Horizonte vacio para el techo {level}: t_end={t1} no es "
            f"posterior a t_start={t0}.")
    last_period = (t1 - pd.Timedelta(1, "ns")).to_period("M")
    target_idx = pd.period_range(start=t0.to_period("M"), end=last_period,
                                 freq="M")
    if len(target_idx) == 0:
        raise ValueError(
            f"El horizonte [{t0}, {t1}) no contiene ningun mes para el "
            f"techo {level}.")

    con_valor = df.index[df[col].notna()]
    if len(con_valor) == 0:
        raise ValueError(
            f"El fichero {path.name} no trae ningun valor del techo {level}. "
            f"Antes esto devolvia valores no numericos que el minimo "
            f"propagaba en silencio a la serie de bolsa. Ver H-50.")
    primero, ultimo = con_valor.min(), con_valor.max()
    fuera = [str(p) for p in target_idx if p < primero or p > ultimo]
    if fuera:
        raise ValueError(
            f"El techo {level} no esta publicado para {fuera}: "
            f"{path.name} lo trae de {primero} a {ultimo}. Un mes fuera de "
            f"la tabla no se deduce de los vecinos; hay que anadir su fila "
            f"con el valor oficial (defecto 3: antes se propagaba el mes mas "
            f"cercano sin aviso).")

    # H-50 y defecto 3: la interpolacion solo rellena huecos INTERIORES, y se
    # hace sobre el calendario mensual completo de la tabla, de modo que el
    # techo de un mes es el mismo se pida como se pida (antes se hacia sobre
    # la union del rango pedido con el indice del fichero, y con una fila
    # ausente el peso de cada vecino dependia de la ventana).
    calendario = pd.period_range(primero, ultimo, freq="M")
    serie = df[col].reindex(calendario)
    meses_tabla = [str(p) for p in target_idx if pd.notna(serie.loc[p])]
    if serie.isna().any():
        serie = serie.interpolate(method="linear", limit_area="inside")
    serie = serie.reindex(target_idx)
    meses_interp = [str(p) for p in target_idx if str(p) not in meses_tabla]

    if serie.isna().any():
        faltan = [str(p) for p in serie.index[serie.isna()]]
        raise ValueError(
            f"El techo {level} queda sin valor para {faltan} en {path.name}. "
            f"Antes esto devolvia valores no numericos que el minimo "
            f"propagaba en silencio a la serie de bolsa. Ver H-50.")

    if return_info:
        return serie, {"meses_tabla": meses_tabla,
                       "meses_interpolados": meses_interp}
    return serie


def _paso(dt: float) -> str:
    """Frecuencia de pandas para un paso de `dt` horas (CAL-46).

    Con el paso horario devuelve exactamente ``"1h"``, de modo que el eje
    reconstruido es identico al de antes de CAL-46.
    """
    if dt == 1.0:
        return "1h"
    minutos = dt * 60.0
    if abs(minutos - round(minutos)) > 1e-9:
        raise ValueError(f"paso de {dt} h no es un numero entero de minutos")
    return f"{int(round(minutos))}min"


def apply_creg101066_ceiling(
    pi_bolsa: np.ndarray,
    t_start: str,
    level: str = "PES",
    effective_date: str = "2024-12-01",
    csv_path: Optional[str] = None,
    return_diagnostics: bool = False,
    dt: float = 1.0,
):
    """
    Aplica el techo CREG 101 066/2024 al precio de bolsa horario.

    Para cada hora ``k``, si la fecha local de esa hora es ``>= effective_date``,
    el precio se recorta a ``min(pi_bolsa[k], ceiling[mes_de_k])``. Antes de
    ``effective_date`` la serie se devuelve sin cambios.

    Parameters
    ----------
    pi_bolsa : np.ndarray  shape (T,)
        Serie horaria de precios de bolsa en COP/kWh. Tiene que ser finita:
        un NaN o un infinito es un ``ValueError`` (defecto 5; el minimo con
        el techo dejaba pasar el NaN sin aviso).
    t_start : str o Timestamp
        Inicio del horizonte, ``"YYYY-MM-DD"`` o con hora. **Hora local de
        America/Bogota sin zona**, y asi se interpreta siempre: una fecha sin
        zona no se toca. Una con zona se convierte a America/Bogota y se le
        quita la zona (defecto 6; antes lanzaba ``TypeError``). Una hora UTC
        escrita sin zona se leeria como local: pasela con su zona.
    level : {"PEI", "PE", "PES"}
        Nivel del techo. Default ``"PES"`` (techo absoluto superior).
    effective_date : str
        Fecha desde la cual aplica CREG 101 066/2024. Default ``"2024-12-01"``.
    csv_path : str, optional
        Override de la ruta al CSV de techos.
    dt : float
        Duracion del paso en horas (CAL-46). Default 1.0.
    return_diagnostics : bool
        Si True, devuelve ``(pi_capped, diag)`` con metricas de recorte.

    Returns
    -------
    np.ndarray  shape (T,)
        Serie con techo aplicado.
    dict (opcional)
        Diagnosticos: ``hours_capped``, ``fraction``, ``delta_cop_total``,
        ``by_month``, y ``meses_tabla`` / ``meses_interpolados``: que meses
        tomaron el techo de su fila de la tabla y cuales de una interpolacion
        entre dos filas (defecto 3).

    Raises
    ------
    ValueError
        Serie vacia o no finita; o un mes del horizonte, desde la vigencia,
        fuera de la tabla de techos (ver ``load_creg_ceiling``).
    """
    pi = np.asarray(pi_bolsa, dtype=float).copy()
    if pi.ndim != 1:
        raise ValueError(f"pi_bolsa tiene que ser un vector (T,); llego con "
                         f"forma {pi.shape}")
    T = len(pi)
    if T == 0:
        raise ValueError("pi_bolsa esta vacia: no hay horizonte al que "
                         "aplicarle el techo")
    # Defecto 5: el minimo propaga el NaN; la serie de bolsa se valida antes.
    no_finitos = np.flatnonzero(~np.isfinite(pi))
    if no_finitos.size:
        raise ValueError(
            f"pi_bolsa tiene {no_finitos.size} de {T} valores no finitos "
            f"(NaN o infinito), el primero en la posicion {no_finitos[0]}. "
            f"El minimo con el techo los dejaria pasar sin aviso. Ver H-50.")

    # CAL-46: antes el eje se reconstruia suponiendo una hora por posicion.
    # Con T pasos de quince minutos eso construia un horizonte cuatro veces
    # mas largo y buscaba el techo de meses que la serie nunca alcanza.
    t0 = _hora_local(t_start, "t_start")
    idx = pd.date_range(t0, periods=T, freq=_paso(dt))
    eff = _hora_local(effective_date, "effective_date")
    # Defecto 2: el final del horizonte viaja con su hora y es exclusivo.
    # Antes se truncaba a la fecha, y un horizonte que acababa el dia 1 de un
    # mes antes de la medianoche perdia ese mes: KeyError.
    t_end = idx[-1] + pd.Timedelta(hours=dt)

    # Solo necesitan techo los pasos desde la vigencia de la resolucion.
    rige = idx >= eff
    if rige.any():
        ceil_monthly, info_tabla = load_creg_ceiling(
            idx[rige][0], t_end, level=level, csv_path=csv_path,
            return_info=True)
    else:
        ceil_monthly = None
        info_tabla = {"meses_tabla": [], "meses_interpolados": []}
    # Vector horario de techo: misma longitud que pi
    ceil_per_hour = np.array([
        ceil_monthly.loc[ts.to_period("M")] if ts >= eff else np.inf
        for ts in idx
    ], dtype=float)

    # H-50: el minimo propaga los valores no numericos sin avisar, y una
    # serie de bolsa entera en ese estado atraviesa la corrida hasta el
    # final sin que nada falle. Se comprueba antes de aplicarlo.
    if not np.all(np.isfinite(ceil_per_hour) | np.isinf(ceil_per_hour)):
        raise ValueError(
            f"El techo horario {level} tiene valores no numericos en "
            f"{int(np.isnan(ceil_per_hour).sum())} de {T} pasos. Aplicar el "
            f"minimo los propagaria a toda la serie de bolsa. Ver H-50.")

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
        "meses_tabla":        info_tabla["meses_tabla"],
        "meses_interpolados": info_tabla["meses_interpolados"],
    }
    # Defecto 8: `delta_mean` es el recorte medio de las horas RECORTADAS del
    # mes (0,0 si ninguna), que es como se lee junto a `hours_capped`. Antes
    # promediaba sobre todas las horas del mes: diez horas recortadas en 100
    # (COP/kWh) en un mes de 720 salian como 1,39. `delta_total` es la suma.
    serie = pd.Series(pi_pre - pi, index=idx)
    for period, sub in serie.groupby(serie.index.to_period("M")):
        recortadas = sub[sub > 0]
        diag["by_month"][str(period)] = {
            "hours_capped": int(len(recortadas)),
            "delta_mean":   (float(recortadas.mean()) if len(recortadas)
                             else 0.0),
            "delta_total":  float(sub.sum()),
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
              f"{'Recorte medio COP/kWh':>22}")
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
    ap.add_argument("--regenera-cache", nargs=2, metavar=("INICIO", "FIN"),
                    default=None,
                    help="descarga [INICIO, FIN) del API de XM y REESCRIBE "
                         f"data/{CACHE_BOLSA}")
    ap.add_argument("--registro", default=None,
                    help="fichero al que se anade cada peticion al API")
    args = ap.parse_args()

    if args.regenera_cache:
        inicio, fin = args.regenera_cache
        download_via_api(inicio, fin,
                         save_path=str(Path(__file__).parent / CACHE_BOLSA),
                         registro=args.registro)
        raise SystemExit(0)

    # Ya no escribe `precios_bolsa_generados.csv`: nadie lo leia, y la copia
    # que habia en el arbol era la cache corrida del defecto 1.
    prices = get_pi_bolsa(T=args.T, use_api=args.api or (not args.synth),
                           csv_path=args.csv)
    print_price_summary(prices)
