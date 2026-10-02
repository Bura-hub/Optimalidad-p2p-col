"""
c2_ppa.py — El escenario C2 de la propuesta: la venta de TODO el excedente a
precio pactado (PPA), por institución, frente a los mecanismos del canon
===============================================================================
Actividad 2.1 de la propuesta (escenarios regulatorios). Cálculo DERIVADO del
canon: no simula el mercado ni nada en el servidor. Lee artefactos con huella
en `Documentos/canon_2026-09/HUELLAS.csv` (comprueba tamaño y `sha256` de cada
uno antes de leerlo) y los insumos de `data/` con los que se corrió la matriz
del 19 de septiembre (registra su `sha256` en la procedencia).

QUÉ ES EL C2 AQUÍ. La investigación regulatoria del 2026-10-02
(`Documentos/regulacion/investigacion_c2_ppa_2026-10-02/`) concluye que la
única forma legal de un «contrato bilateral a precio fijo» para el excedente de
un AGPE solar es la del art. 23, num. 2, lit. a) de la CREG 174 (redacción del
art. 27 de la 101 072): cada institución, por separado, vende TODO su
excedente horario a un generador o comercializador que lo destine a usuarios
no regulados, a un precio pactado libremente PP, SIN crédito de energía. Su
liquidación es la del art. 26 lit. c): VE = Σ_h ExcT_h · PP_h. La importación
se sigue pagando a su tarifa y el autoconsumo vale la tarifa (CU), como en
todos los mecanismos. No hay versión colectiva (el art. 20 de la 101 072 no
remite al lit. a) para un AC 100 % FNCER de 1 MW o menos).

Como el PPA no altera el mercado entre pares ni la operación, su beneficio es
lineal en el precio:

    B^C2_n(PP) = A_n + Σ_h S_{n,h} · PP_h,     A_n = Σ_h min(G, D)_{n,h} · CU_{n,h}

con S_{n,h} = max(G − D, 0) el excedente horario (la columna `sobrante` del
almacén; se comprueba). Con PP constante, B^C2 = A + PP · S.

QUÉ CALCULA, por caso (13) × institución y para la comunidad (suma):

  * S (kWh) y A (COP).
  * Los precios de equilibrio PP*_X = (B^X − A) / S frente a X ∈ {C1, C4,
    P2P, P2P por el colectivo, C3}, con B^X de la hoja `Por_agente` del libro
    canónico de cada caso (float64; suma la hoja `Resumen`). Con S = 0 se deja
    vacío y se dice por qué.
  * El valor del PPA y las brechas C2 − X con (a) PP constante = media horaria
    de la serie de XM de contratos del mercado no regulado en el horizonte;
    (b) PP mensual = esa serie mes a mes; (c) PP en su mínimo y en su máximo
    del horizonte.
  * k*: el factor por el que habría que multiplicar la bolsa para que vender
    todo a la bolsa (C3) iguale al PPA a la media de XM. C3 es
    A + Σ S · max(k·bolsa − MEM, 0): lineal en k mientras k·bolsa ≥ MEM en
    toda hora con excedente; si no, lineal a trozos y creciente. k* se despeja
    exactamente (biseccion sobre la función a trozos) y se informa desde qué k
    es lineal.
  * La parte del excedente que en C1 es crédito (tipo 1) y la que es exceso
    (tipo 2), con `core.opciones_externas.reparto_anexo4`, como
    `atribucion_supuestos.py`.

Añadido el 2026-10-02 (segunda tarea), al final de cada fila:

  * El signo de C2 − X a la media de XM por fila (`signo_C2_media_menos_X`:
    +1 si el PPA queda por encima, −1 por debajo y 0 si empatan a menos de
    1 COP). Los pares institución-caso se cuentan con la convención del canon
    para «25 de 64 pares bajo C4» (CANON §12 y §14.18, `cifras_cap07`): 64 pares,
    los 12 casos de cinco instituciones y SINU con cuatro (la comunidad sin
    Udenar), y cuentan también las tres instituciones de K1 sin excedente.
    Compuerta: con esa convención, las columnas B_P2P y B_C4, B_C1 de esta
    tabla dan los 25 pares bajo C4 y los 0 bajo C1 de `cifras_cap07`. Los
    empates son exactamente esas tres de K1 frente a C1 y frente a C3 (sin
    excedente, el PPA, C1 y C3 valen solo el autoconsumo).
  * El Gini de la ganancia por institución, en la fila de la comunidad
    (vacío en las de institución, porque es una medida entre instituciones):
    del PPA a la media de XM (`gini_C2_media`) y de cada mecanismo del canon
    (`gini_<X>`, de la hoja `PoF_Fairness`). Misma definición y misma función
    que el Gini entre mecanismos del canon (C-214): `core.settlement.gini_index`
    sobre el beneficio neto por institución, que es la que escribe la hoja
    `PoF_Fairness` (`scenarios/comparison_engine.py`). Compuertas: esa
    función sobre `Por_agente` reproduce la hoja (≤ 1e-12) en los cinco
    mecanismos y los 13 casos, y la tabla de CANON §14.6 (Gini P2P y C4, la
    de la tabla de equidad de la tesis) a tres decimales.

DECISIONES.

  * B^X por institución: hoja `Por_agente` del libro canónico (es float64 y
    suma `Resumen` al céntimo). Se comprueba contra la tabla `escenarios` del
    almacén (float32) institución por institución.
  * La bolsa horaria es la de `data.xm_prices.get_pi_bolsa` con la caché
    `data/precios_bolsa_xm_api.csv` (la que registra la hoja `Diagnostico` de
    los 13 casos), con el techo de la 101 066 como en la corrida. No se
    descarga nada: si la caché no cubre el horizonte, falla. Compuerta: es
    la bolsa reconstruida del canon (`bolsa_reconstruida.csv`, grupo `e1/S`)
    en las 5 395 horas donde esa se conoce.
  * CU y MEM (FAZNI + 0,04·G + representante) por institución y hora, de
    `data.cedenar_tariff` en el régimen no regulado, como la corrida
    (`--no-regulado`). Compuerta: CU = `techo` del almacén.
  * Compuerta de C3: con PP_{n,h} = max(bolsa_h − MEM_{n,h}, 0) el PPA
    reproduce C3 canónico institución por institución (la fórmula es la de
    `scenarios.scenario_c3_spot.run_c3_spot`, que también se ejecuta).
  * Compuerta de `run_c2_bilateral`: con las series G y D del almacén (float32)
    y `pi_contrato` = PP, cobertura 1 y sin consumidores puros, la función de
    producción da A + PP·S, con PP constante y con la serie mensual.
  * Los nombres de los comercializadores no salen: «A» (el de Udenar,
    Mariana, UCC y HUDN) y «B» (el de Cesmag).

SALVEDADES (van también a la procedencia y a CANON §14.22): el PPA es
individual y de todo el excedente; no hay oferta pública real de compra de
excedentes de AGPE a precio pactado; la serie de XM es una referencia
mayorista (probablemente generosa para un vendedor pequeño); no se simula.

Falla en voz alta: ningún `except` que trague, ningún NaN rellenado; todo
valor numérico se comprueba finito, salvo las celdas que quedan vacías por
S = 0, que llevan su motivo.

Escribe en SALIDAS_SERVIDOR/c2_ppa_2026-10-02/:

    c2_ppa_13casos.csv   una fila por caso × institución y una «comunidad»
    resumen.md           la comunidad por caso
    procedencia.txt      commit, versiones, huellas, insumos y compuertas, sin
                         fecha: con el mismo HEAD y el mismo guion, los tres
                         ficheros salen iguales byte a byte entre corridas

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/c2_ppa.py

Registrado en HUELLAS.csv como grupo `e1/P` (CANON §14.22).

Actividad 2.1.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[4]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

HUELLAS = RAIZ / "Documentos" / "canon_2026-09" / "HUELLAS.csv"
SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
BASE_MATRIZ = SALIDAS / "entrega_matriz_reposo_2026-09-19"
SALIDA = SALIDAS / "c2_ppa_2026-10-02"
PREF_ALM = "SALIDAS_SERVIDOR/matriz_reposo/{}/almacen/m1/{}/"
LIBRO = "SALIDAS_SERVIDOR/matriz_reposo/{}/outputs/resultados_comparacion.xlsx"
CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1", "CV2", "SINU"]
MECS = ["C1", "C4", "P2P", "P2P_colectivo", "C3"]
VARIANTES = ["media", "mensual", "minimo", "maximo"]
T_HORAS = 6144
INICIO = pd.Timestamp("2025-04-04 00:00")
FUENTE_BOLSA = "cache_api:precios_bolsa_xm_api.csv"
# módulos de producción que este guion importa: tienen que estar como en HEAD
MODULOS = ["core/opciones_externas.py", "core/settlement.py", "data/cedenar_tariff.py", "data/xm_prices.py",
           "data/precios_contratos.py", "scenarios/scenario_c2_bilateral.py",
           "scenarios/scenario_c3_spot.py", "scenarios/_pi_gs.py"]
M = 1e6
CANON_MD = RAIZ / "Documentos" / "canon_2026-09" / "CANON.md"
EMPATE = 1.0                         # COP: |C2 − X| por debajo es empate (ruido float32 del almacén)
N_PARES = 64                         # 12 casos × 5 instituciones + SINU × 4 (convención de «25 de 64»)
CAP07 = "cifras_cap07_2026-09-28/cifras.csv"   # grupo e1/R: los pares del canon
GINI_COLS = ["gini_C2_media"] + [f"gini_{x}" for x in MECS]

LEIDOS: list[tuple[str, str]] = []
INSUMOS: list[tuple[str, int, str]] = []
COMPUERTAS: list[str] = []


# ── Funciones puras (las prueba tests/test_c2_ppa.py) ───────────────────────
def valor_ppa(A: np.ndarray, S_h: np.ndarray, PP) -> np.ndarray:
    """B^C2 = A + Σ_h S_h · PP_h por institución. `S_h` (N, T); `PP` escalar,
    (T,) o (N, T)."""
    S_h = np.asarray(S_h, dtype=float)
    pp = np.broadcast_to(np.asarray(PP, dtype=float), S_h.shape)
    return np.asarray(A, dtype=float) + (S_h * pp).sum(axis=-1)


def precio_equilibrio(B, A, S):
    """PP* = (B − A) / S; NaN donde S = 0 (la celda queda vacía con su motivo,
    no se rellena)."""
    B, A, S = (np.asarray(x, dtype=float) for x in (B, A, S))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(S > 0, (B - A) / np.where(S > 0, S, 1.0), np.nan)


def bolsa_neta(pb: np.ndarray, mem: np.ndarray, k: float = 1.0) -> np.ndarray:
    """Lo que C3 paga por kWh excedente: max(k·bolsa − MEM, 0), (N, T)."""
    return np.maximum(k * np.asarray(pb, dtype=float)[None, :] - np.asarray(mem, dtype=float), 0.0)


def c3_valor(A: np.ndarray, S_h: np.ndarray, pb: np.ndarray, mem: np.ndarray, k: float = 1.0) -> np.ndarray:
    """C3 por institución con la bolsa multiplicada por k (como run_c3_spot)."""
    return valor_ppa(A, S_h, bolsa_neta(pb, mem, k))


def k_estrella(S_h: np.ndarray, pb: np.ndarray, mem: np.ndarray, objetivo: float,
               tol: float = 1e-13) -> float:
    """El k ≥ 0 con Σ S·max(k·bolsa − MEM, 0) = objetivo (> 0). La función es
    continua, creciente y lineal a trozos en k; se despeja por bisección hasta
    `tol` relativo. Falla si no hay excedente con bolsa positiva."""
    S_h = np.asarray(S_h, dtype=float)
    m = (S_h > 0) & (np.asarray(pb, dtype=float)[None, :] > 0)
    if not m.any():
        raise ValueError("sin excedente con bolsa positiva: k* no existe")
    s = S_h[m]
    p = np.broadcast_to(np.asarray(pb, dtype=float)[None, :], S_h.shape)[m]
    me = np.asarray(mem, dtype=float)[m]

    def f(k):
        return float((s * np.maximum(k * p - me, 0.0)).sum()) - objetivo

    lo, hi = 0.0, 1.0
    if f(lo) >= 0:
        raise ValueError("objetivo no positivo: k* no existe")
    while f(hi) < 0:
        hi *= 2.0
        if hi > 1e6:
            raise ValueError("k* no acotado")
    while hi - lo > tol * hi:
        mid = 0.5 * (lo + hi)
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
    return hi


def signo_brecha(brecha, tol: float = EMPATE) -> np.ndarray:
    """+1 si la brecha C2 − X supera `tol`, −1 si queda por debajo de −`tol`, 0
    (empate) en medio. Entero."""
    b = np.asarray(brecha, dtype=float)
    return np.where(b > tol, 1, np.where(b < -tol, -1, 0)).astype(int)


def gini(valores) -> float:
    """El Gini entre mecanismos del canon (C-214): `core.settlement.gini_index`
    sobre el beneficio neto por institución, la función que escribe la hoja
    `PoF_Fairness`. Falla si algún valor no es finito."""
    from core.settlement import gini_index
    v = np.asarray(valores, dtype=float)
    finito(v, "Gini: beneficios")
    return float(gini_index(v))


# ── Lectura con huella ──────────────────────────────────────────────────────
def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[c2_ppa] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    COMPUERTAS.append(msg)
    print(f"[c2_ppa]   OK  {msg}")


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


def finito(x, qué: str):
    exige(bool(np.isfinite(np.asarray(x, dtype=float)).all()), f"{qué}: valores no finitos")
    return x


_H: pd.DataFrame | None = None


def _huellas() -> pd.DataFrame:
    global _H
    if _H is None:
        _H = pd.read_csv(HUELLAS)
        exige(list(_H.columns) == ["grupo", "ruta", "bytes", "sha256"], f"cabecera inesperada en {HUELLAS}")
    return _H


def _base(grupo: str) -> Path:
    return SALIDAS if grupo.startswith("e1/") else BASE_MATRIZ


def lee(ruta: str, grupo: str) -> Path:
    H = _huellas()
    f = H[(H.ruta == ruta) & (H.grupo == grupo)]
    exige(len(f) == 1, f"{ruta}: {len(f)} filas en HUELLAS.csv (se esperaba 1)")
    fila = f.iloc[0]
    p = _base(grupo) / ruta
    exige(p.is_file(), f"no existe {p}")
    datos = p.read_bytes()
    exige(len(datos) == int(fila.bytes), f"{ruta}: {len(datos)} bytes, huella {fila.bytes}")
    exige(hashlib.sha256(datos).hexdigest() == fila.sha256, f"{ruta}: sha256 distinto de la huella")
    if (grupo, ruta) not in LEIDOS:
        LEIDOS.append((grupo, ruta))
    return p


def almacen(c: str, tabla: str) -> pd.DataFrame:
    H = _huellas()
    pref = PREF_ALM.format(c, tabla)
    rutas = sorted(r for r in H[H.grupo == f"almacen/{c}"].ruta if r.startswith(pref))
    exige(len(rutas) >= 1, f"{c}: sin partes de «{tabla}» en HUELLAS.csv")
    en_disco = sorted(p.name for p in (BASE_MATRIZ / pref).glob("*.parquet"))
    exige(en_disco == [r.rsplit("/", 1)[1] for r in rutas], f"{c} {tabla}: partes en disco distintas de HUELLAS.csv")
    return pd.concat([pd.read_parquet(lee(r, f"almacen/{c}")) for r in rutas], ignore_index=True)


def insumo(rel: str) -> Path:
    """Un fichero de `data/` sin huella en el canon: se registra su sha256."""
    p = RAIZ / rel
    exige(p.is_file(), f"no existe el insumo {rel}")
    datos = p.read_bytes()
    INSUMOS.append((rel, len(datos), hashlib.sha256(datos).hexdigest()))
    return p


# ── Insumos comunes ─────────────────────────────────────────────────────────
def horizonte() -> tuple[pd.DatetimeIndex, list[str]]:
    a = almacen("E0", "agentes")
    x = a[a.agente == a.agente.iloc[0]].sort_values("hora")
    idx = pd.DatetimeIndex(x.fecha.to_numpy())
    exige(len(idx) == T_HORAS and idx[0] == INICIO, f"horizonte: {len(idx)} horas desde {idx[0]}")
    exige(bool((idx == pd.date_range(INICIO, periods=T_HORAS, freq="h")).all()), "horizonte: horas no consecutivas")
    exige(list(x.mes) == list(idx.strftime("%Y-%m")), "horizonte: la columna mes no es el mes de la fecha")
    ok(f"horizonte: {T_HORAS} horas consecutivas de {idx[0]:%Y-%m-%d %H:%M} a {idx[-1]:%Y-%m-%d %H:%M}, "
       "con el mes de la fecha")
    return idx, list(idx.strftime("%Y-%m"))


def bolsa(idx: pd.DatetimeIndex) -> np.ndarray:
    from data import xm_prices
    cache = insumo("data/" + xm_prices.CACHE_BOLSA)
    t0, t1 = idx[0].strftime("%Y-%m-%d"), (idx[-1] + pd.Timedelta(hours=1)).strftime("%Y-%m-%d")
    exige(xm_prices.load_xm_prices(str(cache), t0, t1) is not None,
          "la caché de bolsa no cubre el horizonte (no se descarga nada)")
    pb = np.asarray(xm_prices.get_pi_bolsa(T_HORAS, t_start=t0, t_end=t1, csv_path=None, use_api=True,
                                           scenario="2025_normal", dt=1.0), dtype=float)
    exige(xm_prices.ULTIMA_FUENTE == FUENTE_BOLSA, f"fuente de la bolsa {xm_prices.ULTIMA_FUENTE}")
    exige(pb.shape == (T_HORAS,), "bolsa: forma")
    finito(pb, "bolsa")
    exige(bool((pb >= 0).all()), "bolsa negativa")
    # contra la bolsa reconstruida del canon (punto S)
    br = pd.read_csv(lee("atribucion_supuestos_2026-09-30/bolsa_reconstruida.csv", "e1/S"))
    h = br.hora.to_numpy()
    dif = np.abs(pb[h] - br.bolsa.to_numpy())
    es_piso = (br.fuente == "piso").to_numpy()
    exige(float(dif[es_piso].max()) <= 1e-3, f"bolsa distinta de la reconstruida (piso) en {dif[es_piso].max():.5f}")
    exige(float(dif[~es_piso].max()) <= 0.25, f"bolsa distinta de la reconstruida (escenarios) en {dif[~es_piso].max():.4f}")
    ok(f"bolsa de la caché ({FUENTE_BOLSA}, con el techo de la 101 066) = bolsa reconstruida del canon (e1/S) en "
       f"{int(es_piso.sum())} horas del piso (≤ {dif[es_piso].max():.1e} COP/kWh) y {int((~es_piso).sum())} despejadas "
       f"(≤ {dif[~es_piso].max():.3f})")
    return pb


def contratos(idx: pd.DatetimeIndex) -> np.ndarray:
    from data import precios_contratos as pc
    insumo(pc.FUENTE.relative_to(RAIZ).as_posix())
    cob = pc.cobertura(idx[0].strftime("%Y-%m-%d"), idx[-1].strftime("%Y-%m-%d"))
    exige(not cob["faltan"] and not cob["fuera_de_banda"], f"serie de contratos: {cob}")
    pc_h = np.asarray(pc.precio_horario(idx), dtype=float)
    finito(pc_h, "serie de contratos")
    serie = pc.carga().set_index("mes").no_regulado
    exige(bool(np.array_equal(pc_h, serie.reindex(idx.strftime("%Y-%m")).to_numpy(dtype=float))),
          "precio_horario no es la serie mensual hora a hora")
    ok(f"serie de XM de contratos del mercado no regulado: 9 meses de 2025-04 a 2025-12, media horaria "
       f"{pc_h.mean():.4f}, mínimo {pc_h.min():.4f} y máximo {pc_h.max():.4f} COP/kWh")
    return pc_h


def tarifas(ags: list[str], idx: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray, dict]:
    from data import cedenar_tariff as ct
    for f in ["data/tarifas_asc_mensual.csv", "data/tarifas_cedenar_mensual.csv", "data/mem_costs_no_regulado.csv"]:
        if f not in [r for r, _, _ in INSUMOS]:
            insumo(f)
    ct.aplicar_regimen_no_regulado(True)
    CU = np.asarray(ct.pi_gs_per_agent_hourly(ags, idx), dtype=float)
    mem = np.asarray(ct.mem_costs_per_agent_hourly(ags, idx), dtype=float)
    finito(CU, "CU")
    finito(mem, "MEM")
    exige(bool((mem > 0).all()), "MEM no positivo")
    com = {a: ct.INSTITUTION_PROFILE[a].comercializador for a in ags}
    return CU, mem, com


# ── Un caso ─────────────────────────────────────────────────────────────────
def caso(c: str, idx, pb, pc_h) -> tuple[list[dict], dict]:
    from scenarios.scenario_c2_bilateral import run_c2_bilateral
    from scenarios.scenario_c3_spot import run_c3_spot
    from core.opciones_externas import reparto_anexo4

    a = almacen(c, "agentes")
    e = almacen(c, "escenarios")
    ags = list(dict.fromkeys(a.agente))
    N = len(ags)
    exige(len(a) == T_HORAS * N, f"{c}: {len(a)} filas de agentes")
    cols = ["demanda", "generacion", "autoconsumo", "sobrante", "faltante", "techo"]
    finito(a[cols].to_numpy(dtype=float), f"agentes {c}")

    def piv(col):
        return a.pivot(index="agente", columns="hora", values=col).loc[ags].to_numpy(dtype=float)

    G, D = piv("generacion"), piv("demanda")
    au_alm, s_alm, d_alm, techo = (piv(k) for k in ["autoconsumo", "sobrante", "faltante", "techo"])
    exige(bool((G >= 0).all() and (D >= 0).all()), f"{c}: G o D negativos")
    au = np.minimum(G, D)
    S_h = np.maximum(G - D, 0.0)
    R_h = np.maximum(D - G, 0.0)
    for nom, x, y in [("autoconsumo", au, au_alm), ("sobrante", S_h, s_alm), ("faltante", R_h, d_alm)]:
        exige(float(np.abs(x - y).max()) <= 1e-3, f"{c}: {nom} del almacén ≠ el de G y D")
    CU, mem, com = tarifas(ags, idx)
    exige(float(np.abs(CU - techo).max()) <= 1e-3, f"{c}: CU de la tarifa ≠ techo del almacén ({np.abs(CU - techo).max():.5f})")
    A = (au * CU).sum(axis=1)
    S = S_h.sum(axis=1)

    # B^X canónicos: Por_agente (float64), contra Resumen y contra el almacén
    libro = lee(LIBRO.format(c), f"outputs/{c}")
    R = pd.read_excel(libro, sheet_name="Resumen").set_index("Escenario")["Ganancia_neta_COP"]
    PA = pd.read_excel(libro, sheet_name="Por_agente")
    exige(len(PA) == N, f"{c}: Por_agente tiene {len(PA)} filas para {N} instituciones")
    finito(PA[MECS].to_numpy(dtype=float), f"Por_agente {c}")
    ev = e.astype({"valor": "float64"}).groupby(["escenario", "agente"]).valor.sum().unstack(0).loc[ags]
    B = {}
    for x in MECS:
        b = PA[x].to_numpy(dtype=float)
        exige(abs(b.sum() - R[x]) <= max(0.01, 1e-12 * abs(R[x])), f"{c} {x}: Por_agente no suma Resumen")
        dif = np.abs(b - ev[x].to_numpy())
        exige(float(dif.max()) <= max(2.0, 2e-7 * abs(R["P2P"])), f"{c} {x}: Por_agente ≠ almacén en {dif.max():.3f} COP")
        B[x] = b
    # Gini canónico (C-214): la hoja PoF_Fairness es gini_index sobre Por_agente
    pf = pd.read_excel(libro, sheet_name="PoF_Fairness").set_index("escenario")["gini"]
    finito(pf[MECS].to_numpy(dtype=float), f"PoF_Fairness {c}")
    GI = {x: float(pf[x]) for x in MECS}
    dgini = max(abs(gini(B[x]) - GI[x]) for x in MECS)
    exige(dgini <= 1e-12, f"{c}: gini_index(Por_agente) ≠ PoF_Fairness en {dgini:.2e}")
    # C3 canónico = PPA con PP = max(bolsa − MEM, 0) hora a hora
    pnet = bolsa_neta(pb, mem)
    c3_ppa = valor_ppa(A, S_h, pnet)
    r3 = run_c3_spot(D, G, CU, pb, list(range(N)), [], dt=1.0, mem_costs=mem)
    c3_fun = np.array([r3["per_agent"][n]["net_benefit"] for n in range(N)])
    dfun = float(np.abs(c3_fun - c3_ppa).max())
    exige(dfun <= 1e-6 * max(1.0, float(np.abs(c3_ppa).max())), f"{c}: valor_ppa ≠ run_c3_spot en {dfun:.3e}")
    d3 = np.abs(c3_ppa - B["C3"])
    tol3 = np.maximum(1.0, 1e-8 * np.abs(B["C3"]))
    exige(bool((d3 <= tol3).all()), f"{c}: el PPA con PP = bolsa − MEM no reproduce C3 ({d3.max():.3f} COP)")
    # run_c2_bilateral (producción) con pi_contrato = PP, cobertura total
    pp_media = float(pc_h.mean())
    dmax2 = 0.0
    for nombre, pp in [("media", pp_media), ("mensual", pc_h)]:
        r2 = run_c2_bilateral(D, G, CU, 0.0, 0.0, list(range(N)), [], pi_bolsa=pb, dt=1.0,
                              pi_contrato=pp, cobertura_contrato=1.0)
        b2 = np.array([r2["per_agent"][n]["net_benefit"] for n in range(N)])
        gr = np.array([r2["per_agent"][n]["grid_revenue"] for n in range(N)])
        ref = valor_ppa(A, S_h, pp)
        d2 = float(np.abs(b2 - ref).max())
        exige(d2 <= 1e-6 * max(1.0, float(np.abs(ref).max())), f"{c}: run_c2_bilateral ({nombre}) ≠ A + PP·S en {d2:.3e}")
        exige(float(np.abs(gr).max()) == 0.0, f"{c}: run_c2_bilateral ({nombre}) vende algo a la bolsa con cobertura 1")
        dmax2 = max(dmax2, d2)
    # tipo 1 / tipo 2 en C1 (art. 25 y Anexo 4 por institución)
    mes = np.array(idx.strftime("%Y%m").astype(int))
    cr, ex, _ = reparto_anexo4(S_h, R_h, mes)
    exige(float(np.abs(cr + ex - S_h).max()) <= 1e-9, f"{c}: crédito + exceso ≠ inyección")
    # linealidad de C3 en k: desde qué k no recorta ninguna hora con excedente
    hay = S_h > 0
    exige(bool((pb[None, :].repeat(N, 0)[hay] > 0).all()), f"{c}: hora con excedente y bolsa nula")
    cociente = np.where(hay, mem / np.where(pb > 0, pb, np.inf)[None, :], 0.0)
    recorta = hay & (pb[None, :] <= mem)

    PP = {"media": np.full(T_HORAS, pp_media), "mensual": pc_h,
          "minimo": np.full(T_HORAS, float(pc_h.min())), "maximo": np.full(T_HORAS, float(pc_h.max()))}
    filas = []
    for i in list(range(N)) + ["comunidad"]:
        sel = slice(None) if i == "comunidad" else slice(i, i + 1)
        nom = "comunidad" if i == "comunidad" else ags[i]
        Ai, Si = float(A[sel].sum()), float(S[sel].sum())
        f = dict(caso=c, institucion=nom,
                 comercializador="" if i == "comunidad" else com[ags[i]],
                 excedente_kwh=Si, importacion_kwh=float(R_h[sel].sum()),
                 autoconsumo_kwh=float(au[sel].sum()), A_autoconsumo_COP=Ai)
        for x in MECS:
            f[f"B_{x}_COP"] = float(B[x][sel].sum())
        f["C3_reconstruido_COP"] = float(c3_ppa[sel].sum())
        for x in MECS:
            f[f"PPeq_{x}_COP_kWh"] = float(precio_equilibrio(f[f"B_{x}_COP"], Ai, Si))
        f["motivo_vacio"] = "" if Si > 0 else "excedente nulo: sin precio de equilibrio ni k*"
        for v in VARIANTES:
            b2 = float(valor_ppa(A[sel], S_h[sel], PP[v]).sum())
            f[f"PP_{v}_COP_kWh"] = float((S_h[sel] * PP[v][None, :]).sum() / Si) if Si > 0 else float(PP[v].mean())
            f[f"B_C2_{v}_COP"] = b2
            for x in MECS:
                f[f"brecha_C2_{v}_menos_{x}_COP"] = b2 - f[f"B_{x}_COP"]
        if Si > 0:
            obj = pp_media * Si
            k = k_estrella(S_h[sel], pb, mem[sel], obj)
            alc = float(c3_valor(A[sel], S_h[sel], pb, mem[sel], k).sum())
            exige(abs(alc - (Ai + obj)) <= max(1e-6, 1e-9 * (Ai + obj)), f"{c} {nom}: k* no iguala C3 al PPA")
            f["k_estrella"] = k
            f["k_lineal_desde"] = float(cociente[sel].max())
        else:
            f["k_estrella"] = np.nan
            f["k_lineal_desde"] = np.nan
        f["horas_excedente_bolsa_bajo_MEM"] = int(recorta[sel].sum())
        f["credito_C1_kwh"] = float(cr[sel].sum())
        f["exceso_C1_kwh"] = float(ex[sel].sum())
        f["fraccion_credito_C1"] = float(cr[sel].sum() / Si) if Si > 0 else np.nan
        # añadido el 2026-10-02: signo de C2 − X a la media y Gini (solo la comunidad)
        for x in MECS:
            f[f"signo_C2_media_menos_{x}"] = int(signo_brecha(f[f"brecha_C2_media_menos_{x}_COP"]))
        if i == "comunidad":
            f["gini_C2_media"] = gini(valor_ppa(A, S_h, PP["media"]))
            for x in MECS:
                f[f"gini_{x}"] = GI[x]
        else:
            for k in GINI_COLS:
                f[k] = np.nan
        filas.append(f)
    aux = dict(c=c, ags=ags, com=com, d3=float(d3.max()), dfun=dfun, d2=dmax2,
               recorta=int(recorta.sum()), exceso_c1=float(ex.sum()), dgini=dgini)
    return filas, aux


def main() -> int:
    t0 = _dt.datetime.now()
    sucio_mod = git("status", "--short", "--", *MODULOS)
    exige(sucio_mod == "", f"módulos de producción con cambios sin commit:\n{sucio_mod}")
    ok("los módulos de producción que se importan están como en HEAD: " + ", ".join(MODULOS))
    print("[c2_ppa] 1. horizonte, bolsa y serie de contratos")
    idx, _ = horizonte()
    pb = bolsa(idx)
    pc_h = contratos(idx)
    print("[c2_ppa] 2. los 13 casos")
    filas, AUX = [], {}
    for c in CASOS:
        fc, aux = caso(c, idx, pb, pc_h)
        filas += fc
        AUX[c] = aux
        print(f"[c2_ppa]   {c}: C3 reproducido a {aux['d3']:.3f} COP; run_c2_bilateral a {aux['d2']:.1e}")
    # fuente de la bolsa del Diagnostico de cada caso
    for c in CASOS:
        dg = pd.read_excel(lee(LIBRO.format(c), f"outputs/{c}"), sheet_name="Diagnostico")
        exige(str(dg.fuente_bolsa.iloc[0]) == FUENTE_BOLSA, f"{c}: fuente_bolsa {dg.fuente_bolsa.iloc[0]}")
    ok(f"la hoja Diagnostico de los 13 casos registra la misma fuente de bolsa ({FUENTE_BOLSA})")
    ok("CU de la tarifa mensual del proyecto (régimen no regulado) = techo del almacén (≤ 1e-3 COP/kWh); autoconsumo, "
       "sobrante y faltante del almacén = min(G, D), max(G − D, 0) y max(D − G, 0) (≤ 1e-3 kWh), en los 13 casos")
    ok("B^X de Por_agente (C1, C4, P2P, P2P colectivo, C3) suma la hoja Resumen (≤ 0,01 COP) y es la tabla "
       "escenarios del almacén por institución (≤ máx(2 COP, 2e-7·P2P)), en los 13 casos")
    d3 = max(a["d3"] for a in AUX.values())
    ok(f"C3: el PPA con PP = max(bolsa − MEM, 0) hora a hora reproduce C3 de Por_agente institución por "
       f"institución (diferencia máxima {d3:.3f} COP, tolerancia máx(1 COP, 1e-8)) y es run_c3_spot (≤ 1e-6 relativo), "
       "en los 13 casos")
    ok("run_c2_bilateral con pi_contrato = PP (media y serie mensual), cobertura 1 y sin consumidores puros da "
       f"A + Σ S·PP por institución (≤ {max(a['d2'] for a in AUX.values()):.1e} COP) y nada a la bolsa, en los 13 casos")
    com = AUX["E0"]["com"]
    a_com = com["Udenar"]
    exige(all(AUX[c]["com"][x] == a_com for c in CASOS for x in AUX[c]["ags"] if x != "Cesmag")
          and all(AUX[c]["com"].get("Cesmag", "") not in ("", a_com) for c in CASOS), "comercializadores: no son A y B")
    rot = {a_com: "A", com["Cesmag"]: "B"}
    T = pd.DataFrame(filas)
    T["comercializador"] = T.comercializador.map(lambda v: rot.get(v, v))
    exige(set(T.comercializador) <= {"A", "B", ""}, "rótulo de comercializador sin anonimizar")
    # compuertas sobre la tabla
    num = T.drop(columns=["caso", "institucion", "comercializador", "motivo_vacio"] + GINI_COLS)
    vacio = T.excedente_kwh <= 0
    es_com = T.institucion == "comunidad"
    cols_vacias = [k for k in num.columns if k.startswith("PPeq_")] + ["k_estrella", "k_lineal_desde", "fraccion_credito_C1"]
    finito(num.loc[~vacio], "tabla (filas con excedente)")
    finito(num.loc[vacio].drop(columns=cols_vacias), "tabla (filas sin excedente)")
    exige(bool(num.loc[vacio, cols_vacias].isna().all().all()) and bool((T.loc[vacio, "motivo_vacio"] != "").all()),
          "filas sin excedente: celdas vacías sin motivo")
    finito(T.loc[es_com, GINI_COLS], "Gini de la comunidad")
    exige(bool(T.loc[~es_com, GINI_COLS].isna().all().all()), "Gini con valor en una fila de institución")
    ok(f"todo finito; {int(vacio.sum())} filas con excedente nulo dejan vacíos PP*, k* y la fracción de crédito, "
       f"con su motivo ({', '.join(T.loc[vacio, 'caso'] + '/' + T.loc[vacio, 'institucion'])}); el Gini, medida "
       "entre instituciones, solo en la fila de la comunidad")
    for x in MECS:
        r = T.loc[~vacio]
        rec = r.A_autoconsumo_COP + r[f"PPeq_{x}_COP_kWh"] * r.excedente_kwh
        exige(float((rec - r[f"B_{x}_COP"]).abs().max()) <= 1e-6, f"PP* de {x} no reproduce B^{x}")
        exige(float((r[f"B_C2_media_COP"] - r[f"B_{x}_COP"] - (r.PP_media_COP_kWh - r[f"PPeq_{x}_COP_kWh"]) * r.excedente_kwh)
                    .abs().max()) <= 1e-6, f"brecha a la media de {x} ≠ (PP − PP*)·S")
    ok("A + PP*_X·S = B^X (≤ 1e-6 COP) y C2 − X = (PP − PP*_X)·S a la media de XM, en todas las filas con excedente")
    for c in CASOS:
        t = T[T.caso == c]
        com_ = t[t.institucion == "comunidad"].iloc[0]
        ins = t[t.institucion != "comunidad"]
        for k in ["excedente_kwh", "A_autoconsumo_COP"] + [f"B_{x}_COP" for x in MECS] + \
                 [f"B_C2_{v}_COP" for v in VARIANTES] + ["credito_C1_kwh", "exceso_C1_kwh"]:
            exige(abs(ins[k].sum() - com_[k]) <= 1e-6 * max(1.0, abs(com_[k])), f"{c}: comunidad ≠ suma en {k}")
        R = pd.read_excel(lee(LIBRO.format(c), f"outputs/{c}"), sheet_name="Resumen").set_index("Escenario")["Ganancia_neta_COP"]
        for x in MECS:
            exige(abs(com_[f"B_{x}_COP"] - R[x]) <= 0.01, f"{c}: comunidad {x} ≠ Resumen")
        # lineal en PP: el valor a la media está entre el del mínimo y el del máximo, y la recta pasa por los tres
        pend = (com_.B_C2_maximo_COP - com_.B_C2_minimo_COP) / (com_.PP_maximo_COP_kWh - com_.PP_minimo_COP_kWh)
        exige(abs(pend - com_.excedente_kwh) <= 1e-6 * max(1.0, com_.excedente_kwh), f"{c}: la pendiente de B^C2 en PP no es S")
        exige(abs(com_.B_C2_minimo_COP + pend * (com_.PP_media_COP_kWh - com_.PP_minimo_COP_kWh) - com_.B_C2_media_COP)
              <= 1e-6 * com_.B_C2_media_COP, f"{c}: B^C2 no es lineal en PP")
    ok("la comunidad es la suma de sus instituciones; sus B^X son la hoja Resumen (≤ 0,01 COP); B^C2 es lineal en PP "
       "con pendiente S (mínimo, media y máximo de XM sobre una recta), en los 13 casos")
    at = pd.read_csv(lee("atribucion_supuestos_2026-09-30/atribucion_13casos.csv", "e1/S")).set_index("caso")
    for c in CASOS:
        com_ = T[(T.caso == c) & (T.institucion == "comunidad")].iloc[0]
        exige(abs(com_.exceso_C1_kwh - at.loc[c, "exceso_kwh__C1"]) <= 0.05, f"{c}: exceso de C1 ≠ atribución")
        exige(abs(com_.excedente_kwh - at.loc[c, "inyeccion_kwh"]) <= 0.05, f"{c}: excedente ≠ inyección de la atribución")
    ok("excedente y exceso (tipo 2) de C1 de la comunidad = los de atribucion_13casos.csv (e1/S) a 0,05 kWh, en los 13 casos")
    rec = int(T[T.institucion == "comunidad"].horas_excedente_bolsa_bajo_MEM.sum())
    kk = T[(T.institucion == "comunidad")]
    lineal = bool((kk.k_estrella >= kk.k_lineal_desde).all())
    ok(f"C3 en la bolsa: {rec} pares institución-hora con excedente y bolsa ≤ MEM en los 13 casos; k* de la comunidad "
       f"{'≥' if lineal else 'no siempre ≥'} el k desde el que C3 es lineal en la bolsa; k* iguala C3 al PPA a la media "
       "(≤ 1e-9 relativo)")
    # Gini (añadido el 2026-10-02): la función del canon reproduce la hoja y la tabla de CANON §14.6
    t146 = tabla_canon("### 14.6 ·", "Caso")
    exige(list(t146.index) == CASOS, f"CANON §14.6: casos {list(t146.index)}")
    for c in CASOS:
        g = T[(T.caso == c) & es_com].iloc[0]
        for x, col in [("P2P", "Gini P2P"), ("C4", "Gini C4")]:
            exige(f"{g[f'gini_{x}']:.3f}".replace(".", ",") == t146.loc[c, col],
                  f"{c}: Gini de {x} {g[f'gini_{x}']:.6f} no es el {t146.loc[c, col]} de CANON §14.6")
    ok("Gini (C-214): core.settlement.gini_index sobre Por_agente reproduce la hoja PoF_Fairness (≤ "
       f"{max(a['dgini'] for a in AUX.values()):.1e}) en C1, C4, P2P, P2P colectivo y C3, y los Gini de P2P y C4 "
       "de la tabla de CANON §14.6 (la de equidad de la tesis) a tres decimales, en los 13 casos; el del PPA es la "
       "misma función sobre A + PP·S por institución, a la media de XM")
    # pares institución-caso (añadido el 2026-10-02): la convención de «25 de 64»
    ins = T[~es_com]
    exige(len(ins) == N_PARES, f"pares institución-caso: {len(ins)}, no {N_PARES}")
    exige(bool((ins.groupby("caso").size().reindex(CASOS) == [4 if c == "SINU" else 5 for c in CASOS]).all()),
          "pares: no son 12 casos de cinco instituciones y SINU con cuatro")
    exige("Udenar" not in set(ins[ins.caso == "SINU"].institucion), "SINU con Udenar")
    c7 = pd.read_csv(lee(CAP07, "e1/R"), dtype={"valor": str}).set_index("clave").valor
    for x, k in [("C4", "institucion__P2P_menos_C4__negativos"), ("C1", "institucion__P2P_menos_C1__negativos")]:
        d_ = ins.B_P2P_COP - ins[f"B_{x}_COP"]
        exige(int((d_ < 0).sum()) == int(c7[k]) == int((signo_brecha(d_) < 0).sum()),
              f"pares con P2P − {x} < 0: {(d_ < 0).sum()}, cifras_cap07 {c7[k]}")
    emp = {x: set(zip(ins.loc[ins[f"signo_C2_media_menos_{x}"] == 0, "caso"],
                      ins.loc[ins[f"signo_C2_media_menos_{x}"] == 0, "institucion"])) for x in MECS}
    sin_exc = set(zip(T.loc[vacio, "caso"], T.loc[vacio, "institucion"]))
    exige(emp["C1"] == sin_exc and emp["C3"] == sin_exc and not any(emp[x] for x in ["C4", "P2P", "P2P_colectivo"]),
          f"empates del PPA (|C2 − X| ≤ {EMPATE} COP) fuera de las filas sin excedente frente a C1 y C3: {emp}")
    sobre = {x: int((ins[f"signo_C2_media_menos_{x}"] == 1).sum()) for x in MECS}
    ok(f"pares institución-caso: {N_PARES} (12 casos × 5 y SINU × 4, sin Udenar; cuentan las tres de K1 sin "
       "excedente), la convención del canon: con ella P2P − C4 < 0 en "
       f"{c7['institucion__P2P_menos_C4__negativos']} y P2P − C1 < 0 en {c7['institucion__P2P_menos_C1__negativos']}, "
       f"como cifras_cap07 (e1/R); el PPA a la media queda por encima de C1 en {sobre['C1']}, de C4 en {sobre['C4']} "
       f"y de P2P en {sobre['P2P']}; los únicos empates (≤ {EMPATE:g} COP) son las {len(sin_exc)} filas sin excedente "
       "frente a C1 y C3")
    # salida
    SALIDA.mkdir(parents=True, exist_ok=True)
    T.to_csv(SALIDA / "c2_ppa_13casos.csv", index=False, encoding="utf-8", lineterminator="\n", float_format="%.6f")
    escribe_resumen(T, pc_h)
    guion = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    sucio = git("status", "--short", "--untracked-files=all", "--", guion)
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh_:
        fh = _Anonimo(fh_)
        fh.write("rutas: el nombre de cada comercializador va enmascarado como [A] o [B]; el sha256 identifica "
                 "el fichero\n")
        fh.write("c2_ppa.py: el C2 de la propuesta, venta de todo el excedente a precio pactado por institución "
                 "(CREG 174 art. 23 num. 2 lit. a y art. 26 lit. c), frente a los mecanismos del canon\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n" + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + guion + "\n")
        fh.write("registrado en HUELLAS.csv como grupo e1/P (CANON §14.22)\n")
        fh.write("no simula: lee el almacén y los libros de la matriz del 19 de septiembre\n")
        fh.write("CANON.md leído como texto solo para la compuerta del Gini (tabla de §14.6, a tres decimales)\n")
        fh.write(f"huellas: {HUELLAS.relative_to(RAIZ).as_posix()}; {len(LEIDOS)} artefactos leídos, todos con la huella comprobada:\n")
        for g, r in LEIDOS:
            fh.write(f"  {g}  {r}\n")
        fh.write(f"insumos de data/ (sin huella en el canon; sha256 registrado): {len(INSUMOS)}\n")
        for r, b, h in INSUMOS:
            fh.write(f"  {r}  {b}  {h}\n")
        fh.write(f"compuertas: {len(COMPUERTAS)}, todas OK:\n")
        for cpt in COMPUERTAS:
            fh.write(f"  OK  {cpt}\n")
        fh.write(f"filas: {len(T)}\n")
        fh.write("salvedades: PPA individual de todo el excedente, sin crédito; no hay oferta pública real de compra "
                 "de excedentes de AGPE a precio pactado; la serie de XM es una referencia mayorista; no se simula\n")
        fh.write("sin fecha: la hora de la corrida solo se imprime en la consola\n")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    cm = T[T.institucion == "comunidad"].set_index("caso")
    print(cm[["excedente_kwh", "PPeq_C1_COP_kWh", "PPeq_C4_COP_kWh", "PPeq_P2P_COP_kWh",
              "PPeq_P2P_colectivo_COP_kWh", "PPeq_C3_COP_kWh", "k_estrella", "fraccion_credito_C1"]].round(3))
    print((cm[[f"brecha_C2_media_menos_{x}_COP" for x in MECS]] / M).round(3))
    print(f"[c2_ppa] corrida del {t0.isoformat(timespec='seconds')}, {(_dt.datetime.now() - t0).total_seconds():.0f} s")
    print(f"[c2_ppa] {len(LEIDOS)} artefactos, {len(INSUMOS)} insumos, {len(COMPUERTAS)} compuertas; salida en {SALIDA}")
    return 0


class _Anonimo:
    """Escribe enmascarando el nombre de los comercializadores en las rutas
    (`[A]`, el de Udenar, Mariana, UCC y HUDN; `[B]`, el de Cesmag)."""

    def __init__(self, fh):
        self.fh = fh

    def write(self, t: str) -> None:
        t = t.replace("tarifas_asc_", "tarifas_[A]_").replace("cedenar", "[B]")
        exige("cedenar" not in t.lower() and "_asc" not in t.lower(), "nombre de comercializador en la procedencia")
        self.fh.write(t)


def tabla_canon(prefijo: str, primera: str) -> pd.DataFrame:
    """La tabla Markdown cuya primera columna es `primera` en la sección de
    CANON.md que empieza por `prefijo`, como cadenas indexadas por esa columna."""
    lineas = CANON_MD.read_text(encoding="utf-8").splitlines()
    ini = [i for i, l in enumerate(lineas) if l.startswith(prefijo)]
    exige(len(ini) == 1, f"CANON.md: {len(ini)} encabezados «{prefijo}»")
    fin = next((j for j in range(ini[0] + 1, len(lineas)) if lineas[j].startswith("#")), len(lineas))
    sec = lineas[ini[0]:fin]
    cab_i = [i for i, l in enumerate(sec) if l.startswith(f"| {primera} |")]
    exige(len(cab_i) == 1, f"CANON.md {prefijo}: {len(cab_i)} tablas con «{primera}»")
    bloque = []
    for l in sec[cab_i[0]:]:
        if not l.startswith("|"):
            break
        bloque.append(l)
    celdas = [[x.strip() for x in l.strip().strip("|").split("|")] for l in bloque]
    exige(all(len(f) == len(celdas[0]) for f in celdas), f"CANON.md {prefijo}: tabla irregular")
    return pd.DataFrame(celdas[2:], columns=celdas[0]).set_index(primera)


def _n(x: float, d: int = 2) -> str:
    """Número a la española: coma decimal y espacio fino de miles."""
    s = f"{x:,.{d}f}"
    return s.replace(",", " ").replace(".", ",")


def escribe_resumen(T: pd.DataFrame, pc_h: np.ndarray) -> None:
    cm = T[T.institucion == "comunidad"].set_index("caso")
    L = ["# C2 (PPA de todo el excedente) frente al canon: la comunidad por caso", "",
         "Fuente: `c2_ppa_13casos.csv` de esta carpeta (guion `reformateo/documento/scripts/articulo/c2_ppa.py`; "
         "CANON §14.22). Cálculo derivado, sin simular. Cada institución vende todo su excedente horario a precio "
         "pactado, sin crédito (CREG 174 art. 23 num. 2 lit. a y art. 26 lit. c); la comunidad es la suma.", "",
         f"PP de referencia: serie de XM de contratos del mercado no regulado, media horaria del horizonte "
         f"{_n(float(pc_h.mean()))} COP/kWh (mínimo {_n(float(pc_h.min()))}, máximo {_n(float(pc_h.max()))}).", "",
         "## Precios de equilibrio PP* (COP/kWh)", "",
         "PP* es el precio pactado con el que el PPA iguala al mecanismo. Por encima de PP*, el PPA gana.", "",
         "| Caso | S (kWh) | C1 | C4 | P2P | P2P colectivo | C3 | Crédito en C1 (%) |",
         "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in cm.iterrows():
        L.append(f"| {c} | {_n(r.excedente_kwh)} | {_n(r.PPeq_C1_COP_kWh)} | {_n(r.PPeq_C4_COP_kWh)} | "
                 f"{_n(r.PPeq_P2P_COP_kWh)} | {_n(r.PPeq_P2P_colectivo_COP_kWh)} | {_n(r.PPeq_C3_COP_kWh)} | "
                 f"{_n(100 * r.fraccion_credito_C1, 1)} |")
    L += ["", "## Valor del PPA a la media de XM y brechas (MCOP)", "",
          "| Caso | C2 (media) | C2 − C1 | C2 − C4 | C2 − P2P | C2 − P2P colectivo | C2 − C3 | k* |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in cm.iterrows():
        L.append(f"| {c} | {_n(r.B_C2_media_COP / M, 3)} | " + " | ".join(
            _n(r[f'brecha_C2_media_menos_{x}_COP'] / M, 3) for x in MECS) + f" | {_n(r.k_estrella, 3)} |")
    L += ["", "## Brechas C2 − C1 con las otras variantes de PP (MCOP)", "",
          "| Caso | PP mensual | PP mínimo | PP máximo |", "|---|---:|---:|---:|"]
    for c, r in cm.iterrows():
        L.append(f"| {c} | " + " | ".join(_n(r[f'brecha_C2_{v}_menos_C1_COP'] / M, 3)
                                         for v in ["mensual", "minimo", "maximo"]) + " |")
    ins = T[T.institucion != "comunidad"]
    L += ["", "## Equidad (Gini) y pares institución-caso", "",
          "Gini de la ganancia por institución (la función del Gini entre mecanismos del canon, C-214; el del PPA, a "
          "la media de XM). Pares: instituciones del caso con el PPA a la media por encima de cada mecanismo "
          "(empate a menos de 1 COP no cuenta).", "",
          "| Caso | Gini C2 (PPA) | Gini P2P | Gini C4 | Gini C1 | Gini P2P colectivo | Gini C3 | Instituciones | "
          "PPA > C1 | PPA > C4 | PPA > P2P | PPA > P2P colectivo |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in cm.iterrows():
        i_ = ins[ins.caso == c]
        L.append(f"| {c} | " + " | ".join(_n(r[k], 3) for k in ["gini_C2_media", "gini_P2P", "gini_C4", "gini_C1",
                                                                  "gini_P2P_colectivo", "gini_C3"])
                 + f" | {len(i_)} | " + " | ".join(str(int((i_[f'signo_C2_media_menos_{x}'] == 1).sum()))
                                                    for x in ["C1", "C4", "P2P", "P2P_colectivo"]) + " |")
    L.append(f"| Total | | | | | | | {len(ins)} | " + " | ".join(
        str(int((ins[f'signo_C2_media_menos_{x}'] == 1).sum())) for x in ["C1", "C4", "P2P", "P2P_colectivo"]) + " |")
    L += ["", f"Pares: {len(ins)}, con la convención del canon para «25 de 64 pares bajo C4» (12 casos con cinco "
          "instituciones y SINU con cuatro, sin Udenar; cuentan las tres instituciones de K1 sin excedente, que frente "
          "a C1 y a C3 empatan con el PPA porque los tres valen solo el autoconsumo).", "",
          "k*: factor por el que habría que multiplicar la bolsa de cada hora para que vender todo el excedente "
          "a la bolsa (C3, con los costos del mercado mayorista) iguale al PPA a la media de XM.", "",
          "Salvedades: el PPA es individual y de todo el excedente (no hay versión colectiva legal); no se encontró "
          "oferta pública de compra de excedentes de AGPE a precio pactado; la serie de XM es una referencia "
          "mayorista, probablemente generosa para un vendedor pequeño; no se simula nada.", ""]
    (SALIDA / "resumen.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    sys.exit(main())
