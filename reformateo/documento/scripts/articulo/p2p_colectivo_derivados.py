"""
p2p_colectivo_derivados.py — Las mediciones de la tesis hechas con el viejo
«mercado P2P por el colectivo», rehechas para el P2P colectivo y para C2
===============================================================================
Actividades 2.1, 2.2, 3.2 y 4.2 de la propuesta. Cálculo DERIVADO del canon: no
simula el mercado ni usa el servidor. Lee artefactos con huella en
`Documentos/canon_2026-09/HUELLAS.csv` (comprueba tamaño y `sha256` de cada uno
antes de leerlo) e importa, en lugar de copiarlas, las funciones de
`atribucion_supuestos.py` (punto S), `c2_ppa.py` (punto P) y
`p2p_comunitario.py` (punto PC) y la cuenta del factor de coincidencia de
`analysis/coincidencia.py`.

NOMBRE. Desde el 2026-10-02, por decisión del autor, el «P2P comunitario» del
punto PC (CANON §14.23) se llama **P2P colectivo** y reemplaza por completo al
viejo «mercado P2P por el colectivo» (la vía legal de hoy, esquina v(0,0) del
punto S). Las claves `*P2Pcom*` y las columnas `P2Pcom_*` conservan su nombre;
aquí el P2P colectivo es `P2Pcol` en las columnas nuevas, y el viejo mecanismo,
cuando se reproduce como compuerta, `P2P_colectivo_viejo`. C2 es el PPA de
todo el excedente por institución a la media de XM (punto P).

QUÉ CALCULA (una sección por medición de la tesis que citaba el viejo):

  1. Mes a mes (D72, CANON §12, y subperíodos, §14.9): P2P colectivo − C4,
     − C1, − C5 y − P2P, y C2 − C4, − C1 y − C5, por caso, mes e institución
     (117 meses-caso). Compuerta: el mercado da P2P − C4 > 0 en 116 de 117
     meses (I1, diciembre de 2025, −41 804 COP), P2P − C1 en 116 (P1, diciembre,
     −1 371) y P2P − C5 en 117, con el mes de la tabla `escenarios` del
     almacén = `optimalidad_D72/<caso>_mensual.csv` = `meses_condicion.csv`.
     Con los terciles de `meses_condicion.csv`, la ventaja media por tercil
     (compuerta: la del mercado, 1,12/1,27/1,35 por generación, etc.).
  2. Barrido de σ (§14.4): el P2P colectivo con los flujos y precios de las 39
     corridas del barrido (almacenes con huella, e1/B1), por caso e
     institución; qué signos frente a C1, C2, C3, C4 y C5 cambian. Compuerta:
     la reliquidación del almacén de cada σ reproduce P2P y el viejo colectivo
     de su libro por institución, y los signos del viejo colectivo frente a C4
     que cambian son los de §14.4. C2 no tiene mercado: no depende de σ.
  3. El COT en la deducción (§14.16): el P2P colectivo con κ·(Cv + COT) en la
     institución del comercializador B. Compuerta: C1 y C4 con el COT = los
     del contrafáctico (e1/T) y P2P por institución por dos vías; P2P y el
     viejo colectivo con los flujos del canon = los del contrafáctico (los
     flujos no cambian). C2 no deduce: solo se mueven sus brechas con C1 y C4.
  4. Un solo comercializador (§14.3): el contrafáctico RE-SIMULÓ el mercado con
     el evaluador del GSA y no guardó almacenes. El P2P colectivo y C2 se
     derivan con las tarifas de A (o de B) para las cinco y los flujos del
     canon fijos. Compuerta: C1 y C4 = los del contrafáctico; la aproximación
     de los flujos fijos se mide en P2P y en el viejo colectivo.
  5. Retiro de un miembro (§14.13): el contrafáctico re-simuló sin almacenes.
     C4 y C1 sin cada miembro son exactos; los flujos del mercado de cuatro se
     aproximan con el lado corto (D-7) repartido en proporción a s y d, en las
     horas en que el de cinco transó, al precio medio de la hora. La
     aproximación se calibra en el mercado y el viejo colectivo contra su canon
     de cuatro miembros. C2 es individual: quien se queda no cambia.
  6. Factor de coincidencia (D20, `analysis/coincidencia.py`): el del P2P
     colectivo es lo transado (coincide por construcción) más el residual
     repartido por el colectivo contra la importación residual. Compuerta:
     reproduce la hoja `Coincidencia` en C1, C4, P2P y el viejo colectivo. C2
     no acredita contra importación: no aplica, como C3.
  7. Otras: el precio de la justicia frente a C4 (§14.6) y su clase; el efecto
     del umbral de 100 kW (E4 − 7 × P1, §14.11); las 11 fronteras (el caso 1
     para todos del punto PC); el techo literal del Anexo 4 (§14.16), con
     cambio cero exacto porque en las 38 horas no hay excedente.

Escribe en SALIDAS_SERVIDOR/p2p_colectivo_derivados_2026-10-02/:

    mensual_13casos.csv          caso × mes × institución (y comunidad)
    sigma_13casos.csv            σ × caso × institución (y comunidad)
    cot_13casos.csv              caso × institución (y comunidad)
    comercializador_13casos.csv  variante (A, B) × caso × institución
    retiro_comunidad.csv         caso × retirada (54)
    retiro_quienes_quedan.csv    caso × retirada × institución que se queda (216)
    coincidencia_13casos.csv     caso
    otros_13casos.csv            caso: precio de la justicia, umbral, 11 fronteras, techo
    resumen.md                   las tablas de la comunidad
    procedencia.txt              commit, versiones, huellas, insumos y compuertas,
                                 sin fecha (dos corridas: iguales byte a byte)

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/p2p_colectivo_derivados.py

SALVEDADES: el P2P colectivo es una propuesta regulatoria (§14.23); los flujos
del mercado son los del motor, fijos, salvo en σ (los de cada corrida); en el
comercializador único y el retiro son una aproximación declarada y calibrada;
los comercializadores se nombran A y B.

Registrado en HUELLAS.csv como grupo `e1/PD` (CANON §14.24).

Actividades 2.1, 2.2, 3.2 y 4.2.
"""
from __future__ import annotations

import contextlib
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
AQUI = Path(__file__).resolve().parent
for _p in (str(RAIZ), str(AQUI)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import atribucion_supuestos as AS  # noqa: E402
import c2_ppa as CP  # noqa: E402
import p2p_comunitario as PC  # noqa: E402
from analysis.coincidencia import _cuenta_mes, _razon  # noqa: E402

SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
SALIDA = SALIDAS / "p2p_colectivo_derivados_2026-10-02"
CASOS = AS.CASOS
M = 1e6
EMPATE = CP.EMPATE
LIBRO = PC.LIBRO
F_PC = "p2p_comunitario_2026-10-02/p2p_comunitario_13casos.csv"
F_PPA = "c2_ppa_2026-10-02/c2_ppa_13casos.csv"
F_MESES = "subperiodos_2026-09-27/meses_condicion.csv"
F_D72 = "optimalidad_D72/{}_mensual.csv"
F_COT = "contrafactico_techo_cot_2026-09-28/{}"
F_COM = "contrafactico_comercializador_2026-09-27/{}"
F_RET = "retiro_miembro_2026-09-27/{}"
BARRIDO = "entrega_barrido_sigma_2026-09-27/SALIDAS_SERVIDOR/matriz_reposo/{c}_sigma{s}/"
SIGMAS = ["0", "05", "1"]
SIGMA_VAL = {"0": 0.0, "05": 0.5, "1": 1.0}
# variante del código del proyecto -> rótulo publicable (los nombres no salen)
VARIANTES_COM = {"asc": "A", "cedenar": "B"}
MODULOS = PC.MODULOS + ["analysis/coincidencia.py"]
IMPORTADOS = PC.IMPORTADOS + ["reformateo/documento/scripts/articulo/p2p_comunitario.py"]
# brechas del P2P colectivo que se siguen (contra quién) y de C2
CONTRA = ["C1", "C4", "C5", "C3", "C2ppa", "P2P"]
CONTRA_C2 = ["C1", "C4", "C5"]

# Lo que el canon escribe y aquí se reproduce como compuerta (CANON.md)
MES_EN_CONTRA = {"C4": ("I1", "2025-12", -41804), "C1": ("P1", "2025-12", -1371)}   # §12 y §14.9
TERCILES_P2P_C4 = {"t_generacion": (1.12, 1.27, 1.35), "t_bolsa": (1.41, 1.23, 1.11),
                   "t_demanda": (1.05, 1.39, 1.30)}   # §14.9 (MCOP por mes; bajo, medio, alto)
B1_CAMBIAN = {"0": {"E0": 18806, "SINU": 2088}, "05": {"E0": 18758, "SINU": 1850},
              "1": {"CV2": -70794, "P2": -177572}}   # §14.4: viejo colectivo − C4 que cambia de signo
UMBRAL_P2P = -33.50                                   # §14.11: P2P, E4 − 7 × P1 (MCOP)
HORAS_TECHO = 38                                      # §14.16
RETIRO_ESTABLES_P2P = 182                             # §14.13
RETIRO_COL_CAMBIAN = 17                               # §14.13
TOL_FLUJOS_COT = 1000.0     # COP: con el COT, E5 reparte la misma energía algo distinto entre parejas (607 COP)

COMPUERTAS: list[str] = []


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[p2p_colectivo_derivados] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    COMPUERTAS.append(msg)
    print(f"[p2p_colectivo_derivados]   OK  {msg}")


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


def finito(x, qué: str):
    exige(bool(np.isfinite(np.asarray(x, dtype=float)).all()), f"{qué}: valores no finitos")
    return x


# ── Funciones puras (las prueba tests/test_p2p_colectivo_derivados.py) ──────
def horario(au, s, d, v, q, CU, pag, ded, mes, pb, pesos, qué: str) -> np.ndarray:
    """(N, T) el valor hora a hora del P2P colectivo (como `p2p_comunitario.
    valor_comunitario`, sin sumar): autoconsumo a la tarifa, ahorro CU·q del
    comprador, pagos internos y el colectivo sobre el residual. Con v = q = 0 y
    pagos = 0 es C4 con la deducción `ded` y el reparto `pesos`."""
    sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
    col, _ = AS.colectivo(sr, dr, CU, ded, mes, pb, pesos, qué)
    return au * CU + CU * q + pag + col


def por_mes(H: np.ndarray, mes: np.ndarray, n_meses: int) -> np.ndarray:
    """(N, M) las sumas mensuales de una matriz (N, T)."""
    H = np.asarray(H, dtype=float)
    return np.stack([H[:, mes == m].sum(axis=1) for m in range(n_meses)], axis=1)


def coincidencia_p2pcol(s, d, v, q, mes, pesos) -> float:
    """Factor de coincidencia (D20, opción C) del P2P colectivo: lo transado
    dentro coincide por construcción (D-7) y el residual de la comunidad, Σ sr
    con el perfil horario y el reparto `pesos`, se acredita contra la
    importación residual dr de cada miembro, con el corte del Anexo 4."""
    sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
    SR = sr.sum(axis=0)
    pares = [_cuenta_mes(np.asarray(pesos[m], dtype=float)[:, None] * SR[None, mes == m], dr[:, mes == m])
             for m in np.unique(mes)]
    dentro = float(np.asarray(q, dtype=float).sum())
    pares.append((dentro, dentro))
    return _razon(pares)


def lado_corto(s, d, horas_con_mercado) -> tuple[np.ndarray, np.ndarray]:
    """Aproximación de los flujos de un mercado sin re-simularlo: en cada hora
    con mercado el volumen es el lado corto, mín(Σ s, Σ d) (D-7), y se reparte
    en proporción a la inyección (lo vendido) y a la importación (lo comprado).
    Devuelve (v, q), (N, T); Σ v = Σ q en cada hora."""
    s, d = np.asarray(s, dtype=float), np.asarray(d, dtype=float)
    S, D = s.sum(axis=0), d.sum(axis=0)
    vol = np.where(np.asarray(horas_con_mercado, dtype=bool), np.minimum(S, D), 0.0)
    v = np.where(S > 0, s / np.where(S > 0, S, 1.0) * vol, 0.0)
    q = np.where(D > 0, d / np.where(D > 0, D, 1.0) * vol, 0.0)
    return v, q


def clase_pof(w_x: float, w_c4: float, g_x: float, g_c4: float) -> str:
    """Clase del precio de la justicia (CANON §14.6) de un mecanismo X frente a
    C4: «domina» si deja más y reparte con menos desigualdad, «intercambio» si
    deja más pero C4 reparte con más equidad, «C4 domina» si C4 deja más y es
    más equitativo, «C4 deja más» en el caso restante."""
    vals = np.array([w_x, w_c4, g_x, g_c4], dtype=float)
    if not np.isfinite(vals).all():
        raise ValueError(f"valores no finitos: {vals}")
    if w_x > w_c4:
        return "domina" if g_x <= g_c4 else "intercambio"
    return "C4 domina" if g_c4 <= g_x else "C4 deja más"


def cambia(antes, despues) -> np.ndarray:
    """True donde el signo (con empate a 1 COP) de una brecha cambia."""
    return CP.signo_brecha(antes) != CP.signo_brecha(despues)


# ── Lectura ─────────────────────────────────────────────────────────────────
@contextlib.contextmanager
def almacen_desde(lector):
    """Durante el bloque, `atribucion_supuestos.almacen` lee de `lector` (para
    reutilizar `AS.carga` con los almacenes del barrido de σ)."""
    viejo = AS.almacen
    AS.almacen = lector
    try:
        yield
    finally:
        AS.almacen = viejo


def almacen_sigma(s: str):
    def lector(c: str, tabla: str) -> pd.DataFrame:
        pref = BARRIDO.format(c=c, s=s) + f"almacen/m1/{tabla}/"
        H = AS._H
        rutas = sorted(r for r in H[H.grupo == "e1/B1"].ruta if r.startswith(pref))
        exige(len(rutas) >= 1, f"σ {s} {c}: sin partes de «{tabla}» en HUELLAS.csv")
        en_disco = sorted(p.name for p in (SALIDAS / pref).glob("*.parquet"))
        exige(en_disco == [r.rsplit("/", 1)[1] for r in rutas], f"σ {s} {c} {tabla}: partes en disco ≠ HUELLAS.csv")
        return pd.concat([pd.read_parquet(AS.lee(r, "e1/B1")) for r in rutas], ignore_index=True)
    return lector


def flujos(c: str) -> pd.DataFrame:
    return AS.almacen(c, "flujos").astype({"kwh": "float64", "precio": "float64", "techo_comprador": "float64"})


def pagos(fl: pd.DataFrame, ags: list[str], T: int, techo: np.ndarray | None = None) -> np.ndarray:
    """Pagos internos de los flujos (CAL-35); con `techo` (N, T), el techo del
    comprador es la tarifa de esa matriz y no la del almacén."""
    if techo is None:
        tc = fl.techo_comprador.to_numpy()
    else:
        ix = {a: i for i, a in enumerate(ags)}
        ic = fl.comprador.map(ix).to_numpy(dtype=int)
        tc = np.asarray(techo, dtype=float)[ic, fl.hora.to_numpy()]
    P = PC.pagos_internos(fl.vendedor.to_numpy(), fl.comprador.to_numpy(), fl.hora.to_numpy(), fl.kwh.to_numpy(),
                          fl.precio.to_numpy(), tc, ags, T)
    finito(P, "pagos internos")
    return P


def libro(c: str, ruta: str | None = None, grupo: str | None = None) -> dict:
    p = AS.lee(ruta or LIBRO.format(c), grupo or f"outputs/{c}")
    R = pd.read_excel(p, sheet_name="Resumen").set_index("Escenario")["Ganancia_neta_COP"]
    PA = pd.read_excel(p, sheet_name="Por_agente")
    finito(R, f"{c} Resumen")
    return dict(R=R, PA=PA, ruta=p)


def tarifas_variante(ags: list[str], idx: pd.DatetimeIndex, variante: str | None = None) -> dict:
    """CU, Cv, Θ (cargos de red T + D + PR + R) y COT por institución y hora, de
    `data.cedenar_tariff` en el régimen no regulado, con el reparto real de
    comercializadores o, con `variante`, el forzado (que se restituye al salir,
    también si algo falla)."""
    from data import cedenar_tariff as ct
    ct.aplicar_regimen_no_regulado(True)
    if variante is not None:
        ct.forzar_comercializador(variante)
    try:
        CU = np.asarray(ct.pi_gs_per_agent_hourly(ags, idx), dtype=float)
        Cv = np.asarray(ct.cvm_per_agent_hourly(ags, idx), dtype=float)
        cu = ct.cu_components_per_agent_hourly(ags, idx)
        Th = np.asarray(cu["T"], float) + np.asarray(cu["D"], float) + np.asarray(cu["PR"], float) \
            + np.asarray(cu["R"], float)
        COT = np.asarray(cu["COT"], dtype=float)
        es_b = np.array([ct.INSTITUTION_PROFILE[a].comercializador == "cedenar" for a in ags])
    finally:
        if variante is not None:
            ct.forzar_comercializador(None)
    for k, x in [("CU", CU), ("Cv", Cv), ("Θ", Th), ("COT", COT)]:
        finito(x, f"tarifas {variante or 'real'}: {k}")
    return dict(CU=CU, Cv=Cv, Th=Th, COT=COT, es_b=es_b)


# ── La base de cada caso ────────────────────────────────────────────────────
def base(c: str, TT, cap, pb, idx, etiquetas, pp_media, PCT, PPA) -> dict:
    L = AS.carga(c, TT, cap)
    ags, N, mes = L["ags"], L["N"], L["mes"]
    T = L["s"].shape[1]
    meses = sorted(set(etiquetas))
    exige(bool((mes == np.array([meses.index(x) for x in etiquetas])).all()), f"{c}: meses del almacén ≠ horizonte")
    fl = flujos(c)
    pag = pagos(fl, ags, T)
    cs, cin, suma = PC.caso_art20_sin_10(L["capk"], N)
    ded1 = PC.deduccion_caso(1, L["kap"], L["Cv"], L["Th"])
    ded2 = PC.deduccion_caso(2, L["kap"], L["Cv"], L["Th"])
    ded = ded1 if cs == 1 else ded2
    W = PC.igual(N, mes)
    cero = np.zeros((N, T))
    Hp = horario(L["au"], L["s"], L["d"], L["v"], L["q"], L["CU"], pag, ded, mes, pb, W, f"{c} P2P colectivo")
    H4 = horario(L["au"], L["s"], L["d"], cero, cero, L["CU"], cero, ded2, mes, pb, W, f"{c} C4")
    finito(Hp, f"{c} P2P colectivo horario")
    pc = PCT[PCT.caso == c].set_index("institucion")
    exige(list(pc.index) == ags + ["comunidad"], f"{c}: instituciones del punto PC")
    d_pc = max(float(np.abs(Hp.sum(axis=1) - pc.loc[ags, "P2Pcom_COP"].to_numpy(float)).max()),
               float(np.abs(H4.sum(axis=1) - pc.loc[ags, "C4_COP"].to_numpy(float)).max()))
    # C2 (PPA a la media de XM) hora a hora, como c2_ppa.py
    CUt, _, _ = CP.tarifas(ags, idx)
    S_h = np.maximum(L["G"] - L["D"], 0.0)
    H2 = np.minimum(L["G"], L["D"]) * CUt + S_h * pp_media
    pp = PPA[PPA.caso == c].set_index("institucion")
    exige(list(pp.index) == ags + ["comunidad"], f"{c}: instituciones del punto P")
    d_ppa = float(np.abs(H2.sum(axis=1) - pp.loc[ags, "B_C2_media_COP"].to_numpy(float)).max())
    lb = libro(c)
    PA = lb["PA"]
    exige(len(PA) == N, f"{c}: Por_agente con {len(PA)} filas")
    B = {x: PA[x].to_numpy(dtype=float) for x in ["P2P", "P2P_colectivo", "C1", "C3", "C4", "C5"]}
    for x, b in B.items():
        finito(b, f"{c} Por_agente {x}")
        exige(abs(b.sum() - lb["R"][x]) <= max(0.01, 1e-12 * abs(lb["R"][x])), f"{c} {x}: Por_agente ≠ Resumen")
    B["C2ppa"] = pp.loc[ags, "B_C2_media_COP"].to_numpy(dtype=float)
    B["P2Pcol"] = Hp.sum(axis=1)
    e = AS.almacen(c, "escenarios").astype({"valor": "float64"})
    em = e.groupby(["escenario", "agente", "mes"]).valor.sum()
    alm_mes = {x: np.array([[float(em.get((x, a, m), 0.0)) for m in meses] for a in ags])
               for x in ["P2P", "C1", "C4", "C5"]}
    return dict(c=c, L=L, ags=ags, N=N, mes=mes, meses=meses, T=T, fl=fl, pag=pag, caso=cs, cinac=cin, suma=suma,
                ded_caso1=ded1, ded_caso2=ded2, ded=ded, W=W, Hp=Hp, H4=H4, H2=H2, CUt=CUt, S_h=S_h, B=B, R=lb["R"],
                alm_mes=alm_mes, d_pc=d_pc, d_ppa=d_ppa, pc=pc, pp=pp, libro=lb["ruta"])


def filas_brechas(f: dict, val: dict, pre: str, contra: list[str], quien: str) -> None:
    """Añade a la fila `f` las brechas `quien` − X y su signo."""
    for x in contra:
        b = val[quien] - val[x]
        f[f"{pre}{quien}_menos_{x}_COP"] = b
        f[f"{pre}signo_{quien}_menos_{x}"] = int(CP.signo_brecha(b))


# ── 1. Mes a mes ────────────────────────────────────────────────────────────
def mensual(BS: dict) -> pd.DataFrame:
    mc = pd.read_csv(AS.lee(F_MESES, "e1/C6")).set_index(["caso", "mes"])
    filas, dif_d72, dif_mc, dif_c4, dif_tot = [], 0.0, 0.0, 0.0, 0.0
    for c in CASOS:
        b = BS[c]
        ags, mes, meses, nm = b["ags"], b["mes"], b["meses"], len(b["meses"])
        d72 = pd.read_csv(AS.lee(F_D72.format(c), "optimalidad_D72")).set_index(["agente", "mes"])
        Pm = por_mes(b["Hp"], mes, nm)
        C4m = por_mes(b["H4"], mes, nm)
        C2m = por_mes(b["H2"], mes, nm)
        A = b["alm_mes"]
        dif_tot = max(dif_tot, float(np.abs(Pm.sum(axis=1) - b["B"]["P2Pcol"]).max()),
                      float(np.abs(C2m.sum(axis=1) - b["B"]["C2ppa"]).max()))
        dif_c4 = max(dif_c4, float((np.abs(C4m - A["C4"]) / np.maximum(1.0, 1e-7 * np.abs(A["C4"]))).max()))
        for i, a in enumerate(ags):
            for j, m in enumerate(meses):
                r = d72.loc[(a, m)]
                dif_d72 = max(dif_d72, abs(A["P2P"][i, j] - r.B_P2P_COP), abs(A["C4"][i, j] - r.B_C4_COP))
        for j, m in enumerate(meses):
            r = mc.loc[(c, m)]
            for x in ["P2P", "C1", "C4", "C5"]:
                v = A[x][:, j].sum()
                dif_mc = max(dif_mc, abs(v - r[x]) / max(1.0, 2e-7 * abs(v)))
            for i in list(range(len(ags))) + ["comunidad"]:
                sel = slice(None) if i == "comunidad" else slice(i, i + 1)
                val = dict(P2P=A["P2P"][sel, j].sum(), C1=A["C1"][sel, j].sum(), C4=A["C4"][sel, j].sum(),
                           C5=A["C5"][sel, j].sum(), P2Pcol=Pm[sel, j].sum(), C2ppa=C2m[sel, j].sum())
                f = dict(caso=c, mes=m, institucion="comunidad" if i == "comunidad" else ags[i],
                         B_P2P_COP=val["P2P"], B_C1_COP=val["C1"], B_C4_COP=val["C4"], B_C5_COP=val["C5"],
                         P2Pcol_COP=val["P2Pcol"], C2ppa_COP=val["C2ppa"])
                filas_brechas(f, val, "", ["C4", "C1", "C5"], "P2P")
                filas_brechas(f, val, "", ["C4", "C1", "C5", "P2P"], "P2Pcol")
                filas_brechas(f, val, "", CONTRA_C2, "C2ppa")
                for t in ["t_generacion", "t_demanda", "t_bolsa"]:
                    f[t] = r[t] if i == "comunidad" else ""
                filas.append(f)
    X = pd.DataFrame(filas)
    finito(X.drop(columns=["caso", "mes", "institucion", "t_generacion", "t_demanda", "t_bolsa"]), "mes a mes")
    exige(dif_d72 <= 0.01, f"meses del almacén ≠ optimalidad_D72 ({dif_d72:.4f} COP)")
    exige(dif_mc <= 1.0, f"meses del almacén ≠ meses_condicion ({dif_mc:.3f})")
    exige(dif_c4 <= 1.0, f"C4 mensual reliquidado ≠ almacén ({dif_c4:.3f})")
    exige(dif_tot <= 1e-3, f"meses del P2P colectivo o de C2 no suman su horizonte ({dif_tot:.2e} COP)")
    com = X[X.institucion == "comunidad"]
    exige(len(com) == 117, f"meses-caso: {len(com)}, no 117")
    for x, (cc, mm, v) in MES_EN_CONTRA.items():
        neg = com[com[f"signo_P2P_menos_{x}"] < 0]
        exige(len(neg) == 1 and (neg.caso.iloc[0], neg.mes.iloc[0]) == (cc, mm)
              and round(float(neg[f"P2P_menos_{x}_COP"].iloc[0])) == v,
              f"el mercado bajo {x}: {list(zip(neg.caso, neg.mes, neg[f'P2P_menos_{x}_COP'].round()))}")
    exige(int((com.signo_P2P_menos_C5 > 0).sum()) == 117, "el mercado no supera a C5 en los 117 meses")
    for t, esp in TERCILES_P2P_C4.items():
        g = com.groupby(t).P2P_menos_C4_COP.mean() / M
        got = tuple(round(float(g[n]), 2) for n in ["bajo", "medio", "alto"])
        exige(got == esp, f"terciles del mercado por {t}: {got}, no {esp}")
        exige(int(com.groupby(t).size().min()) == 39, f"terciles por {t}: no 39 meses cada uno")
    ok(f"mes a mes: la tabla escenarios del almacén = optimalidad_D72/<caso>_mensual.csv (≤ {dif_d72:.1e} COP) y = "
       "meses_condicion.csv (e1/C6); C4 reliquidado = almacén por institución y mes (≤ 1 COP); el mercado queda sobre C4 "
       "en 116 de 117 meses (I1, 2025-12, −41 804 COP), sobre C1 en 116 (P1, 2025-12, −1 371) y sobre C5 en 117, y la "
       "ventaja media sobre C4 por tercil es la de CANON §14.9 (1,12/1,27/1,35 por generación; 1,41/1,23/1,11 por "
       "bolsa; 1,05/1,39/1,30 por demanda); los meses del P2P colectivo y de C2 suman su horizonte (≤ 1e-3 COP)")
    return X


# ── 2. El barrido de σ ──────────────────────────────────────────────────────
def sigma(BS: dict, TT, cap, pb) -> pd.DataFrame:
    filas, d_rep, d_can = [], 0.0, 0.0
    cambian_viejo = {s: {} for s in SIGMAS}
    for s in SIGMAS:
        for c in CASOS:
            b = BS[c]
            with almacen_desde(almacen_sigma(s)):
                Ls = AS.carga(c, TT, cap)
                fls = flujos(c)
            ags, N, mes, T = b["ags"], b["N"], b["mes"], b["T"]
            exige(Ls["ags"] == ags, f"σ {s} {c}: instituciones")
            for k in ["G", "D", "CU", "s", "d", "au"]:
                exige(float(np.abs(Ls[k] - b["L"][k]).max()) <= 1e-6, f"σ {s} {c}: {k} distinto de la base")
            pag = pagos(fls, ags, T)
            Hs = horario(Ls["au"], Ls["s"], Ls["d"], Ls["v"], Ls["q"], Ls["CU"], pag, b["ded"], mes, pb, b["W"],
                         f"σ {s} {c} P2P colectivo")
            sr, dr = np.maximum(Ls["s"] - Ls["v"], 0.0), np.maximum(Ls["d"] - Ls["q"], 0.0)
            au_cu = Ls["au"] * Ls["CU"]
            p2p = (au_cu + Ls["CU"] * Ls["q"] + pag + AS.art25(sr, dr, Ls["CU"], Ls["ded1"], mes, pb, "σ")[0]).sum(axis=1)
            col = (au_cu + pag + AS.colectivo(Ls["s"], Ls["d"], Ls["CU"], Ls["ded4"], mes, pb,
                                              AS.pesos(Ls["q"] + sr, mes), "σ")[0]).sum(axis=1)
            lb = libro(c, BARRIDO.format(c=c, s=s) + "outputs/resultados_comparacion.xlsx", "e1/B1")
            PA = lb["PA"]
            d_rep = max(d_rep, float(np.abs(p2p - PA.P2P.to_numpy(float)).max()),
                        float(np.abs(col - PA.P2P_colectivo.to_numpy(float)).max()))
            for x in ["C1", "C3", "C4", "C5"]:
                d_can = max(d_can, float(np.abs(PA[x].to_numpy(float) - b["B"][x]).max()))
            v0 = b["R"]["P2P_colectivo"] - b["R"]["C4"]
            v1 = lb["R"]["P2P_colectivo"] - lb["R"]["C4"]
            if cambia(v0, v1):
                cambian_viejo[s][c] = round(float(v1))
            P2Pcol = Hs.sum(axis=1)
            for i in list(range(N)) + ["comunidad"]:
                sel = slice(None) if i == "comunidad" else slice(i, i + 1)
                val = {x: float(b["B"][x][sel].sum()) for x in ["C1", "C4", "C5", "C3", "C2ppa"]}
                val["P2P"] = float(p2p[sel].sum())
                val["P2Pcol"] = float(P2Pcol[sel].sum())
                base_ = {x: float(b["B"]["P2Pcol"][sel].sum() - b["B"][x][sel].sum()) for x in CONTRA}
                f = dict(sigma=SIGMA_VAL[s], caso=c, institucion="comunidad" if i == "comunidad" else ags[i],
                         energia_kwh=float(Ls["q"][sel].sum()), P2Pcol_COP=val["P2Pcol"],
                         P2Pcol_base_COP=float(b["B"]["P2Pcol"][sel].sum()), B_P2P_sigma_COP=val["P2P"],
                         P2P_colectivo_viejo_sigma_COP=float(col[sel].sum()),
                         pagos_internos_COP=float(pag[sel].sum()))
                filas_brechas(f, val, "", CONTRA, "P2Pcol")
                for x in CONTRA:
                    f[f"cambia_P2Pcol_menos_{x}"] = int(cambia(base_[x], f[f"P2Pcol_menos_{x}_COP"]))
                filas.append(f)
    exige(d_rep <= 2.0, f"σ: la reliquidación del almacén no reproduce P2P o el viejo colectivo ({d_rep:.3f} COP)")
    exige(d_can <= 1.0, f"σ: C1, C3, C4 o C5 de un libro del barrido ≠ canon ({d_can:.3f} COP)")
    exige(cambian_viejo == B1_CAMBIAN, f"σ: el viejo colectivo − C4 cambia de signo en {cambian_viejo}, no {B1_CAMBIAN}")
    X = pd.DataFrame(filas)
    finito(X.drop(columns=["caso", "institucion"]), "σ")
    ok(f"σ: con el almacén de cada una de las 39 corridas (e1/B1) la reliquidación reproduce P2P y el viejo colectivo "
       f"de su libro por institución (≤ {d_rep:.3f} COP); C1, C3, C4 y C5 del libro = canon (≤ {d_can:.3f} COP); el "
       "viejo colectivo − C4 cambia de signo donde dice CANON §14.4 (σ = 0: E0 +18 806, SINU +2 088; σ = 0,5: E0 "
       "+18 758, SINU +1 850; σ = 1: CV2 −70 794, P2 −177 572 COP)")
    return X


# ── 3. El COT en la deducción ───────────────────────────────────────────────
def cot(BS: dict, idx, pb) -> pd.DataFrame:
    mec = pd.read_csv(AS.lee(F_COT.format("mecanismos_13casos.csv"), "e1/T"))
    mec = mec[mec.variante == "cot"].set_index("caso")
    pi = pd.read_csv(AS.lee(F_COT.format("por_institucion.csv"), "e1/T"))
    pi = pi[pi.variante == "cot"].set_index(["caso", "institucion"])
    br = pd.read_csv(AS.lee(F_COT.format("brechas_13casos.csv"), "e1/T"))
    brc = br[br.variante == "cot"]
    ccols = [k for k in brc.columns if k.startswith("cambia_")]
    cambios = [(cc, k) for cc, r in brc.set_index("caso").iterrows() for k in ccols if bool(r[k])]
    exige(cambios == [("E1", "cambia_P2Pcol_menos_C4")], f"COT: brechas que cambian en el contrafáctico: {cambios}")
    filas, d14, dvia, dfijo, dpag_max, d_base = [], 0.0, 0.0, 0.0, 0.0, 0.0
    for c in CASOS:
        b = BS[c]
        L, ags, N, mes = b["L"], b["ags"], b["N"], b["mes"]
        tv = tarifas_variante(ags, idx)
        for k, x in [("CU", L["CU"]), ("Cv", L["Cv"]), ("Th", L["Th"])]:
            exige(float(np.abs(tv[k] - x).max()) <= 1e-3, f"{c}: {k} de la tarifa ≠ el del almacén")
        exige(bool((tv["es_b"] == np.array([a == "Cesmag" for a in ags])).all()),
              f"{c}: la institución del comercializador B no es solo Cesmag")
        Cv = L["Cv"] + np.where(tv["es_b"][:, None], tv["COT"], 0.0)
        ded1 = L["kap"] * Cv + np.where(L["capk"][:, None] > 100.0, L["Th"], 0.0)   # C1: numeral de cada planta
        ded2 = L["kap"] * Cv + L["Th"]                                               # C4: caso 2
        ded = PC.deduccion_caso(b["caso"], L["kap"], Cv, L["Th"])                    # P2P colectivo: su caso
        cero = np.zeros_like(L["s"])
        s, d, v, q, CU, au = L["s"], L["d"], L["v"], L["q"], L["CU"], L["au"]
        sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
        C4 = horario(au, s, d, cero, cero, CU, cero, ded2, mes, pb, b["W"], f"{c} C4 con COT").sum(axis=1)
        C1 = (au * CU + AS.art25(s, d, CU, ded1, mes, pb, f"{c} C1 con COT")[0]).sum(axis=1)
        P2Pf = (au * CU + CU * q + b["pag"] + AS.art25(sr, dr, CU, ded1, mes, pb, "COT")[0]).sum(axis=1)
        colf = (au * CU + b["pag"] + AS.colectivo(s, d, CU, ded2, mes, pb, AS.pesos(q + sr, mes), "COT")[0]).sum(axis=1)
        P2Pcol = horario(au, s, d, v, q, CU, b["pag"], ded, mes, pb, b["W"], f"{c} P2P colectivo con COT").sum(axis=1)
        sin_cot = horario(au, s, d, v, q, CU, b["pag"], PC.deduccion_caso(b["caso"], L["kap"], L["Cv"], L["Th"]), mes,
                          pb, b["W"], f"{c} P2P colectivo sin COT").sum(axis=1)
        d_base = max(d_base, float(np.abs(sin_cot - b["B"]["P2Pcol"]).max()))
        r = mec.loc[c]
        d14 = max(d14, abs(C4.sum() - r.C4), abs(C1.sum() - r.C1))
        dfijo = max(dfijo, abs(P2Pf.sum() - r.P2P), abs(colf.sum() - r.P2P_colectivo))
        p2p_i = np.array([C4[i] + pi.loc[(c, a), "P2P_menos_C4"] for i, a in enumerate(ags)])
        p2p_i1 = np.array([C1[i] + pi.loc[(c, a), "P2P_menos_C1"] for i, a in enumerate(ags)])
        c5_i = np.array([p2p_i[i] - pi.loc[(c, a), "P2P_menos_C5"] for i, a in enumerate(ags)])
        dvia = max(dvia, float(np.abs(p2p_i - p2p_i1).max()))
        # Con los flujos fijos (la energía no cambia con el COT), lo único que el contrafáctico mueve por
        # institución fuera de la deducción son los precios internos: la diferencia son los pagos internos,
        # que suman cero. El P2P colectivo usa los mismos flujos y pagos, así que se corrige con ella.
        dpag = p2p_i - P2Pf
        # en E5 la energía de la comunidad es la misma pero su reparto entre parejas cambia un poco: la
        # comunidad del mercado con los flujos del canon queda a 607 COP del contrafáctico (se declara)
        exige(abs(float(dpag.sum())) <= TOL_FLUJOS_COT, f"{c}: el cambio de los pagos internos con el COT no suma cero")
        dpag_max = max(dpag_max, float(np.abs(dpag).max()))
        P2Pcol = P2Pcol + dpag
        exige(abs(c5_i.sum() - r.C5) <= 2.0 and abs(r.C5 - b["R"]["C5"]) <= 0.5, f"{c}: C5 con el COT")
        for i in list(range(N)) + ["comunidad"]:
            sel = slice(None) if i == "comunidad" else slice(i, i + 1)
            val = dict(C1=float(C1[sel].sum()), C4=float(C4[sel].sum()), C5=float(c5_i[sel].sum()),
                       C3=float(b["B"]["C3"][sel].sum()), C2ppa=float(b["B"]["C2ppa"][sel].sum()),
                       P2P=float(p2p_i[sel].sum()), P2Pcol=float(P2Pcol[sel].sum()))
            base_ = {x: float(b["B"]["P2Pcol"][sel].sum() - b["B"][x][sel].sum()) for x in CONTRA}
            base2 = {x: float(b["B"]["C2ppa"][sel].sum() - b["B"][x][sel].sum()) for x in ["C1", "C4"]}
            f = dict(caso=c, institucion="comunidad" if i == "comunidad" else ags[i], caso_art20=b["caso"],
                     C1_cot_COP=val["C1"], C4_cot_COP=val["C4"], C5_COP=val["C5"], C3_COP=val["C3"],
                     C2ppa_COP=val["C2ppa"], P2P_cot_COP=val["P2P"], P2Pcol_cot_COP=val["P2Pcol"],
                     P2Pcol_base_COP=float(b["B"]["P2Pcol"][sel].sum()),
                     d_P2Pcol_COP=val["P2Pcol"] - float(b["B"]["P2Pcol"][sel].sum()),
                     d_C4_COP=val["C4"] - float(b["B"]["C4"][sel].sum()), d_C1_COP=val["C1"] - float(b["B"]["C1"][sel].sum()),
                     d_pagos_internos_COP=float(dpag[sel].sum()))
            filas_brechas(f, val, "", CONTRA, "P2Pcol")
            for x in CONTRA:
                f[f"cambia_P2Pcol_menos_{x}"] = int(cambia(base_[x], f[f"P2Pcol_menos_{x}_COP"]))
            filas_brechas(f, val, "", ["C1", "C4"], "C2ppa")
            for x in ["C1", "C4"]:
                f[f"cambia_C2ppa_menos_{x}"] = int(cambia(base2[x], f[f"C2ppa_menos_{x}_COP"]))
            filas.append(f)
    exige(d14 <= 1.0, f"COT: C1 o C4 reliquidados ≠ el contrafáctico ({d14:.3f} COP)")
    exige(d_base == 0.0, f"COT: sin el COT, el P2P colectivo no es el de la base ({d_base:.2e} COP)")
    exige(dvia <= 2.0, f"COT: P2P por institución por las dos vías ({dvia:.3f} COP)")
    exige(dfijo <= TOL_FLUJOS_COT, f"COT: P2P o el viejo colectivo con los flujos del canon ≠ contrafáctico ({dfijo:.3f} COP)")
    X = pd.DataFrame(filas)
    finito(X.drop(columns=["caso", "institucion"]), "COT")
    ok(f"COT: Cv, CU y Θ de la tarifa = los del almacén y, sin el COT, el P2P colectivo es el de la base al bit; C1 y C4 con κ·(Cv + COT) en la institución de B = los del "
       f"contrafáctico (e1/T, ≤ {d14:.3f} COP); P2P por institución por C1 y por C4 coincide (≤ {dvia:.3f} COP); P2P "
       f"y el viejo colectivo de la comunidad con los flujos del canon = contrafáctico (≤ {dfijo:.0f} COP, en E5; ≤ 1 COP "
       "en los otros doce): la energía no cambia con el COT; por institución el contrafáctico mueve además los pagos internos (precios), hasta "
       f"{dpag_max:,.0f} COP, que suman cero y se llevan al P2P colectivo, que así es exacto; en el contrafáctico cambia "
       "de signo una brecha de comunidad, el viejo colectivo − C4 en E1 (CANON §14.16)")
    return X


# ── 4. Un solo comercializador ──────────────────────────────────────────────
def comercializador(BS: dict, idx, pb, pp_media) -> pd.DataFrame:
    mec = pd.read_csv(AS.lee(F_COM.format("mecanismos_13casos.csv"), "e1/A2")).set_index(["variante", "caso"])
    pi = pd.read_csv(AS.lee(F_COM.format("por_institucion.csv"), "e1/A2")).set_index(["variante", "caso", "institucion"])
    br = pd.read_csv(AS.lee(F_COM.format("brechas_13casos.csv"), "e1/A2"))
    brv = br[br.variante != "real"]
    # «15 brechas del colectivo frente a C1 o a C4» (CANON §14.3): las del viejo colectivo y las de C4 − C1
    n_col = int(sum(brv[k].astype(bool).sum() for k in brv.columns if k.startswith(("cambia_P2Pcol", "cambia_C4"))))
    n_mer = int(sum(brv[k].astype(bool).sum() for k in brv.columns if k.startswith("cambia_P2P_menos")))
    exige(n_col == 15 and n_mer == 0, f"comercializador: {n_col} brechas del viejo colectivo y de C4 − C1 cambian, {n_mer} del mercado")
    filas, d14, dvia, dfijo = [], 0.0, 0.0, {"A": 0.0, "B": 0.0}
    for var, rot in VARIANTES_COM.items():
        for c in CASOS:
            b = BS[c]
            L, ags, N, mes = b["L"], b["ags"], b["N"], b["mes"]
            tv = tarifas_variante(ags, idx, var)
            CU = tv["CU"]
            ded1 = L["kap"] * tv["Cv"] + np.where(L["capk"][:, None] > 100.0, tv["Th"], 0.0)   # C1
            ded2 = L["kap"] * tv["Cv"] + tv["Th"]                                                 # C4
            ded = PC.deduccion_caso(b["caso"], L["kap"], tv["Cv"], tv["Th"])                      # P2P colectivo
            s, d, v, q, au = L["s"], L["d"], L["v"], L["q"], L["au"]
            sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
            cero = np.zeros_like(s)
            pag = pagos(b["fl"], ags, b["T"], techo=CU)
            C4 = horario(au, s, d, cero, cero, CU, cero, ded2, mes, pb, b["W"], f"{rot} {c} C4").sum(axis=1)
            C1 = (au * CU + AS.art25(s, d, CU, ded1, mes, pb, f"{rot} {c} C1")[0]).sum(axis=1)
            P2Pf = (au * CU + CU * q + pag + AS.art25(sr, dr, CU, ded1, mes, pb, "com")[0]).sum(axis=1)
            colf = (au * CU + pag + AS.colectivo(s, d, CU, ded2, mes, pb, AS.pesos(q + sr, mes), "com")[0]).sum(axis=1)
            P2Pcol = horario(au, s, d, v, q, CU, pag, ded, mes, pb, b["W"], f"{rot} {c} P2P colectivo").sum(axis=1)
            C2 = (np.minimum(L["G"], L["D"]) * CU + b["S_h"] * pp_media).sum(axis=1)
            r = mec.loc[(var, c)]
            d14 = max(d14, abs(C4.sum() - r.C4), abs(C1.sum() - r.C1))
            p2p_i = np.array([C4[i] + pi.loc[(var, c, a), "P2P_menos_C4"] for i, a in enumerate(ags)])
            p2p_i1 = np.array([C1[i] + pi.loc[(var, c, a), "P2P_menos_C1"] for i, a in enumerate(ags)])
            c5_i = np.array([p2p_i[i] - pi.loc[(var, c, a), "P2P_menos_C5"] for i, a in enumerate(ags)])
            dvia = max(dvia, float(np.abs(p2p_i - p2p_i1).max()), abs(c5_i.sum() - r.C5))
            ef_p2p, ef_col = float(P2Pf.sum() - r.P2P), float(colf.sum() - r.P2P_colectivo)
            dfijo[rot] = max(dfijo[rot], abs(ef_p2p), abs(ef_col))
            for i in list(range(N)) + ["comunidad"]:
                sel = slice(None) if i == "comunidad" else slice(i, i + 1)
                val = dict(C1=float(C1[sel].sum()), C4=float(C4[sel].sum()), C5=float(c5_i[sel].sum()),
                           C2ppa=float(C2[sel].sum()), P2P=float(p2p_i[sel].sum()), P2Pcol=float(P2Pcol[sel].sum()))
                if i == "comunidad":
                    val["C3"] = float(r.C3)
                base_ = {x: float(b["B"]["P2Pcol"][sel].sum() - b["B"][x][sel].sum()) for x in ["C1", "C4", "C5"]}
                base2 = {x: float(b["B"]["C2ppa"][sel].sum() - b["B"][x][sel].sum()) for x in ["C1", "C4", "C5"]}
                f = dict(variante=rot, caso=c, institucion="comunidad" if i == "comunidad" else ags[i],
                         energia_canon_kwh=float(q[sel].sum()),
                         energia_contrafactico_kwh=float(r.energia_kWh) if i == "comunidad" else np.nan,
                         C1_COP=val["C1"], C4_COP=val["C4"], C5_COP=val["C5"], C3_COP=val.get("C3", np.nan),
                         C2ppa_COP=val["C2ppa"], P2P_COP=val["P2P"], P2Pcol_COP=val["P2Pcol"],
                         P2P_flujos_canon_menos_contrafactico_COP=ef_p2p if i == "comunidad" else np.nan,
                         col_viejo_flujos_canon_menos_contrafactico_COP=ef_col if i == "comunidad" else np.nan)
                filas_brechas(f, val, "", ["C1", "C4", "C5", "P2P"], "P2Pcol")
                for x in ["C1", "C4", "C5"]:
                    f[f"cambia_P2Pcol_menos_{x}"] = int(cambia(base_[x], f[f"P2Pcol_menos_{x}_COP"]))
                filas_brechas(f, val, "", ["C1", "C4", "C5"], "C2ppa")
                for x in ["C1", "C4", "C5"]:
                    f[f"cambia_C2ppa_menos_{x}"] = int(cambia(base2[x], f[f"C2ppa_menos_{x}_COP"]))
                filas.append(f)
    exige(d14 <= 1.0, f"comercializador: C1 o C4 reliquidados ≠ el contrafáctico ({d14:.3f} COP)")
    exige(dvia <= 2.0, f"comercializador: P2P por institución por las dos vías o C5 ({dvia:.3f} COP)")
    X = pd.DataFrame(filas)
    finito(X.drop(columns=["variante", "caso", "institucion", "energia_contrafactico_kwh", "C3_COP",
                           "P2P_flujos_canon_menos_contrafactico_COP",
                           "col_viejo_flujos_canon_menos_contrafactico_COP"]), "comercializador")
    exige(set(X.variante) == {"A", "B"}, "comercializador: variantes sin anonimizar")
    ok(f"comercializador único (e1/A2, re-simulado con el evaluador del GSA, sin almacenes): C1 y C4 con las tarifas "
       f"de A o de B para las cinco = los del contrafáctico (≤ {d14:.3f} COP); P2P por institución por C1 y por C4 "
       f"coincide y C5 suma la comunidad (≤ {dvia:.3f} COP); en el contrafáctico cambian 15 brechas del viejo colectivo "
       "y de C4 frente a C1 o a C4 y ninguna del mercado (CANON §14.3); los flujos del canon, fijos, dejan P2P y el viejo colectivo "
       f"a {dfijo['A'] / M:.3f} MCOP como mucho con A y a {dfijo['B'] / M:.3f} con B del contrafáctico re-simulado")
    return X, dfijo


# ── 5. El retiro de un miembro ──────────────────────────────────────────────
def retiro(BS: dict, pb) -> tuple[pd.DataFrame, pd.DataFrame]:
    co = pd.read_csv(AS.lee(F_RET.format("comunidad.csv"), "e1/B2"))
    qq = pd.read_csv(AS.lee(F_RET.format("quienes_quedan.csv"), "e1/B2")).set_index(["caso", "retirada", "institucion"])
    exige(int((co.retirada != "ninguna").sum()) == 54 and len(qq) == 216, "retiro: 54 comunidades y 216 pares")
    exige(int(co[co.retirada != "ninguna"].cambia_P2Pcol_menos_C4.astype(bool).sum()) == RETIRO_COL_CAMBIAN,
          "retiro: el viejo colectivo − C4 no cambia en 17 de 54")
    exige(int((qq.mas_estable == "P2P").sum()) == RETIRO_ESTABLES_P2P, "retiro: no 182 pares más estables en P2P")
    fc, fq = [], []
    d4, d1, err = 0.0, 0.0, dict(energia=0.0, P2P_com=0.0, col_com=0.0)
    acuerdo, err_ins = 0, []
    for _, r in co[co.retirada != "ninguna"].iterrows():
        c, ret = r.caso, r.retirada
        b = BS[c]
        L, ags, mes = b["L"], b["ags"], b["mes"]
        keep = [i for i, a in enumerate(ags) if a != ret]
        exige(len(keep) == 4, f"{c} sin {ret}: {len(keep)} instituciones")
        ags2 = [ags[i] for i in keep]
        n = len(keep)
        s, d, CU, au = (L[k][keep] for k in ["s", "d", "CU", "au"])
        ded1, ded2 = L["ded1"][keep], L["ded4"][keep]   # numeral de cada planta (art. 25) y caso 2
        cs, cin, suma = PC.caso_art20_sin_10(L["capk"][keep], n)
        ded = PC.deduccion_caso(cs, L["kap"], L["Cv"][keep], L["Th"][keep])
        W = PC.igual(n, mes)
        cero = np.zeros_like(s)
        C4 = horario(au, s, d, cero, cero, CU, cero, ded2, mes, pb, W, f"{c} sin {ret} C4").sum(axis=1)
        C1 = b["B"]["C1"][keep]
        # el mercado de cuatro, aproximado: lado corto en las horas en que el de cinco transó, al precio medio
        hay = b["L"]["q"].sum(axis=0) > 1e-9
        v, q = lado_corto(s, d, hay)
        fl = b["fl"]
        dinero = fl.kwh * np.minimum(fl.precio, fl.techo_comprador)
        g = pd.DataFrame({"h": fl.hora, "k": fl.kwh, "d": dinero}).groupby("h").sum()
        ph = np.zeros(b["T"])
        ph[g.index.to_numpy()] = (g.d / g.k).to_numpy()
        pag = (v - q) * ph[None, :]
        sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
        P2Pcol = horario(au, s, d, v, q, CU, pag, ded, mes, pb, W, f"{c} sin {ret} P2P colectivo").sum(axis=1)
        p2p_ap = (au * CU + CU * q + pag + AS.art25(sr, dr, CU, ded1, mes, pb, "retiro")[0]).sum(axis=1)
        col_ap = (au * CU + pag + AS.colectivo(s, d, CU, ded2, mes, pb, AS.pesos(q + sr, mes), "retiro")[0]).sum(axis=1)
        d4 = max(d4, abs(C4.sum() - r.C4))
        err["energia"] = max(err["energia"], abs(q.sum() - r.energia_kWh) / max(1.0, r.energia_kWh))
        err["P2P_com"] = max(err["P2P_com"], abs(p2p_ap.sum() - r.P2P))
        err["col_com"] = max(err["col_com"], abs(col_ap.sum() - r.P2P_colectivo))
        C2 = b["B"]["C2ppa"][keep]
        val = dict(P2Pcol=float(P2Pcol.sum()), C4=float(C4.sum()), C1=float(C1.sum()), C5=float(r.C5),
                   C2ppa=float(C2.sum()))
        com_completa = dict(P2Pcol=float(b["B"]["P2Pcol"].sum()), C4=float(b["R"]["C4"]), C1=float(b["R"]["C1"]),
                            C5=float(b["R"]["C5"]), C2ppa=float(b["B"]["C2ppa"].sum()))
        f = dict(caso=c, retirada=ret, n_instituciones=n, caso_art20_P2Pcol=cs, cinac_kw=cin,
                 P2Pcol_COP=val["P2Pcol"], C4_COP=val["C4"], C1_COP=val["C1"], C5_COP=val["C5"], C2ppa_COP=val["C2ppa"],
                 energia_aprox_kwh=float(q.sum()), energia_canon_kwh=float(r.energia_kWh),
                 P2P_aprox_menos_canon_COP=float(p2p_ap.sum() - r.P2P),
                 col_viejo_aprox_menos_canon_COP=float(col_ap.sum() - r.P2P_colectivo))
        filas_brechas(f, val, "", ["C4", "C1", "C5"], "P2Pcol")
        filas_brechas(f, val, "", ["C4", "C1", "C5"], "C2ppa")
        for quien in ["P2Pcol", "C2ppa"]:
            for x in ["C4", "C1", "C5"]:
                f[f"cambia_{quien}_menos_{x}"] = int(cambia(com_completa[quien] - com_completa[x],
                                                            f[f"{quien}_menos_{x}_COP"]))
        perd_p, perd_4 = 0.0, 0.0
        for j, a in enumerate(ags2):
            i = keep[j]
            w = qq.loc[(c, ret, a)]
            d4 = max(d4, abs(C4[j] - w.C4_sin))
            d1 = max(d1, abs(C1[j] - w.C1_sin))
            completa = float(b["B"]["P2Pcol"][i])
            pp_ = completa - float(P2Pcol[j])
            p4 = float(w.perdida_C4)
            perd_p += pp_
            perd_4 += p4
            # calibración: la misma aproximación en el mercado frente a su canon de cuatro
            pm = float(w.P2P_completa) - float(p2p_ap[j])
            est_ap = "P2P" if abs(pm) < abs(p4) else ("C4" if abs(pm) > abs(p4) else "igual")
            acuerdo += int(est_ap == w.mas_estable)
            err_ins.append(float(p2p_ap[j] - w.P2P_sin))
            fq.append(dict(caso=c, retirada=ret, institucion=a, P2Pcol_completa_COP=completa,
                           P2Pcol_sin_COP=float(P2Pcol[j]), perdida_P2Pcol_COP=pp_,
                           perdida_rel_P2Pcol=pp_ / abs(completa), perdida_C4_COP=p4,
                           perdida_rel_C4=float(w.perdida_rel_C4), perdida_C2ppa_COP=0.0,
                           mas_estable=("P2Pcol" if abs(pp_) < abs(p4) else ("C4" if abs(pp_) > abs(p4) else "igual")),
                           P2Pcol_sin_menos_C4_sin_COP=float(P2Pcol[j] - C4[j]),
                           signo_P2Pcol_sin_menos_C4_sin=int(CP.signo_brecha(P2Pcol[j] - C4[j])),
                           cambia_P2Pcol_menos_C4=int(cambia(completa - float(b["B"]["C4"][i]), P2Pcol[j] - C4[j])),
                           P2P_sin_aprox_menos_canon_COP=float(p2p_ap[j] - w.P2P_sin),
                           mas_estable_mercado_aprox=est_ap, mas_estable_mercado_canon=str(w.mas_estable)))
        f["perdida_quedan_P2Pcol_COP"] = perd_p
        f["perdida_quedan_C4_COP"] = perd_4
        fc.append(f)
    exige(d4 <= 1.0, f"retiro: C4 sin cada miembro ≠ canon ({d4:.3f} COP)")
    exige(d1 <= 1.0, f"retiro: C1 de quien se queda ≠ canon ({d1:.3f} COP)")
    exige(err["energia"] <= 0.01, f"retiro: la energía del lado corto se aparta de la de las 54 comunidades ({err['energia']:.2e})")
    Xc, Xq = pd.DataFrame(fc), pd.DataFrame(fq)
    finito(Xc.drop(columns=["caso", "retirada"]), "retiro (comunidad)")
    finito(Xq.drop(columns=["caso", "retirada", "institucion", "mas_estable", "mas_estable_mercado_aprox",
                            "mas_estable_mercado_canon"]), "retiro (quienes quedan)")
    ei = np.abs(np.array(err_ins))
    ok(f"retiro (e1/B2, re-simulado sin almacenes): C4 sin cada miembro (reparto 1/4, caso 2) y C1 de quien se queda = "
       f"canon en las 54 comunidades y los 216 pares (≤ {max(d4, d1):.3f} COP); el lado corto en las horas con mercado "
       f"reproduce la energía de las 54 a {100 * err['energia']:.2f} % como mucho; calibración de la aproximación en el mercado y el viejo colectivo de la "
       f"comunidad: ≤ {err['P2P_com'] / M:.3f} y ≤ {err['col_com'] / M:.3f} MCOP; por institución, |error| mediano "
       f"{np.median(ei):,.0f} COP y máximo {ei.max():,.0f}; la clase «se mueve menos» del mercado coincide con el "
       f"canon en {acuerdo} de 216 pares")
    return Xc, Xq, dict(err=err, ei_med=float(np.median(ei)), ei_max=float(ei.max()), acuerdo=acuerdo)


# ── 6. El factor de coincidencia ────────────────────────────────────────────
def coincidencia(BS: dict) -> pd.DataFrame:
    filas, dmax = [], 0.0
    for c in CASOS:
        b = BS[c]
        L, mes, N = b["L"], b["mes"], b["N"]
        s, d, v, q = L["s"], L["d"], L["v"], L["q"]
        sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
        S = s.sum(axis=0)
        hoja = pd.read_excel(AS.lee(LIBRO.format(c), f"outputs/{c}"), sheet_name="Coincidencia").set_index(
            "escenario")["valor"]
        meses = np.unique(mes)
        mio = dict(
            C1=_razon([_cuenta_mes(s[:, mes == m], d[:, mes == m]) for m in meses]),
            C4=_razon([_cuenta_mes(np.full(N, 1.0 / N)[:, None] * S[None, mes == m], d[:, mes == m]) for m in meses]),
            P2P=_razon([_cuenta_mes(sr[:, mes == m], dr[:, mes == m]) for m in meses] + [(float(q.sum()),) * 2]),
            P2P_colectivo=_razon([_cuenta_mes(np.asarray(w, float)[:, None] * S[None, mes == m], d[:, mes == m])
                                  for m, w in AS.pesos(q + sr, mes).items()]))
        for x, vx in mio.items():
            dmax = max(dmax, abs(vx - float(hoja[x])))
        pcol = coincidencia_p2pcol(s, d, v, q, mes, b["W"])
        finito([pcol], f"{c} coincidencia del P2P colectivo")
        exige(0.0 <= pcol <= 1.0, f"{c}: coincidencia del P2P colectivo fuera de [0, 1]")
        filas.append(dict(caso=c, coincidencia_P2Pcol=pcol, coincidencia_P2P=float(hoja["P2P"]),
                          coincidencia_C4=float(hoja["C4"]), coincidencia_C1=float(hoja["C1"]),
                          coincidencia_P2P_colectivo_viejo=float(hoja["P2P_colectivo"]),
                          coincidencia_C5=float(hoja["C5"]), coincidencia_C2ppa=np.nan,
                          transado_kwh=float(q.sum()), residual_iny_kwh=float(sr.sum())))
    exige(dmax <= 1e-6, f"coincidencia: no se reproduce la hoja ({dmax:.2e})")
    ok(f"coincidencia (D20, analysis/coincidencia.py): C1, C4, P2P y el viejo colectivo reliquidados del almacén "
       f"reproducen la hoja Coincidencia en los 13 casos (≤ {dmax:.1e}); C2 (PPA) no acredita contra importación: "
       "no aplica, como C3")
    return pd.DataFrame(filas)


# ── 7. Otras mediciones ─────────────────────────────────────────────────────
def otros(BS: dict, PCT: pd.DataFrame, pb, idx) -> pd.DataFrame:
    t146 = CP.tabla_canon("### 14.6 ·", "Caso")
    com = PCT[PCT.institucion == "comunidad"].set_index("caso")
    pon_ = pd.read_csv(AS.lee(F_COT.format("precios_escasez_xm.csv"), "e1/T")).set_index("mes").pon_cop_kwh
    ha = pd.read_csv(AS.lee(F_COT.format("horas_afectadas.csv"), "e1/T"))
    etiquetas = idx.strftime("%Y-%m")
    horas = pb > pon_.reindex(etiquetas).to_numpy(dtype=float)
    exige(int(horas.sum()) == HORAS_TECHO == int(ha[ha.caso == "E0"].horas_bolsa_sobre_PrecEscaPon.sum()),
          f"techo: {int(horas.sum())} horas con la bolsa sobre el ponderado, no {HORAS_TECHO}")
    filas = []
    for c in CASOS:
        b = BS[c]
        r = com.loc[c]
        w_p, w_4, w_x = float(r.B_P2P_COP), float(r.B_C4_COP), float(r.P2Pcom_COP)
        g_p, g_4, g_x = float(r.gini_P2P), float(r.gini_C4), float(r.gini_P2Pcom)
        cl = clase_pof(w_p, w_4, g_p, g_4)
        exige({"domina": "P2P domina", "intercambio": "intercambio"}[cl] == t146.loc[c, "Clase"],
              f"{c}: clase del mercado {cl} ≠ CANON §14.6")
        exige(f"{100 * (w_p - w_4) / w_p:.1f}".replace(".", ",") == t146.loc[c, "Precio de la justicia (%)"],
              f"{c}: precio de la justicia del mercado ≠ CANON §14.6")
        exige(float(b["L"]["s"][:, horas].sum()) == 0.0, f"{c}: excedente en una hora con la bolsa sobre el ponderado")
        filas.append(dict(caso=c, W_P2Pcol_COP=w_x, W_C4_COP=w_4, gini_P2Pcol=g_x, gini_C4=g_4,
                          pof_P2Pcol=(w_x - w_4) / w_x, clase_P2Pcol=clase_pof(w_x, w_4, g_x, g_4),
                          pof_P2P=(w_p - w_4) / w_p, clase_P2P=cl,
                          once_fronteras_P2Pcol_COP=float(r.P2Pcom_c1todos_COP),
                          once_fronteras_P2Pcol_menos_P2P_COP=float(r.P2Pcom_c1todos_COP - r.B_P2P_COP),
                          once_fronteras_P2Pcol_menos_C4_COP=float(r.c1todos_P2Pcom_menos_C4_COP),
                          techo_horas=int(horas.sum()), techo_excedente_kwh=float(b["L"]["s"][:, horas].sum()),
                          techo_cambio_P2Pcol_COP=0.0, techo_cambio_C2ppa_COP=0.0))
    X = pd.DataFrame(filas).set_index("caso")
    um = {x: (X.loc["E4", k] - 7 * X.loc["P1", k]) for x, k in [("P2Pcol", "W_P2Pcol_COP"), ("C4", "W_C4_COP")]}
    um["P2P"] = float(com.loc["E4", "B_P2P_COP"] - 7 * com.loc["P1", "B_P2P_COP"])
    um["P2Pcol_c1todos"] = float(com.loc["E4", "P2Pcom_c1todos_COP"] - 7 * com.loc["P1", "P2Pcom_c1todos_COP"])
    um["C2ppa"] = float(com.loc["E4", "B_C2ppa_COP"] - 7 * com.loc["P1", "B_C2ppa_COP"])
    exige(round(um["P2P"] / M, 2) == UMBRAL_P2P and abs(um["C4"]) < 1e-3,
          f"umbral: P2P E4 − 7 × P1 = {um['P2P'] / M:.3f}, C4 {um['C4']:.4f}")
    for k, v in um.items():
        X[f"umbral_E4_menos_7P1_{k}_COP"] = v
    ok(f"precio de la justicia: la clase y el porcentaje del mercado frente a C4 son los de CANON §14.6 en los 13 "
       f"casos; umbral: P2P E4 − 7 × P1 = {UMBRAL_P2P:.2f} MCOP y C4 = 0 (CANON §14.11); techo literal: {HORAS_TECHO} "
       "horas con la bolsa sobre el ponderado (= horas_afectadas.csv) y en ninguna hay excedente en los 13 casos, así "
       "que el P2P colectivo (y C2, que no usa la bolsa) cambian cero exacto")
    return X.reset_index()


# ── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    t0 = _dt.datetime.now()
    sucio_mod = git("status", "--short", "--", *MODULOS)
    exige(sucio_mod == "", f"módulos de producción con cambios sin commit:\n{sucio_mod}")
    ok("los módulos de producción que se importan están como en HEAD: " + ", ".join(MODULOS))
    print("[p2p_colectivo_derivados] 1. tarifas, capacidades, horizonte, bolsa y contratos")
    TT = AS.tarifas()
    cap = AS.capacidades()
    idx, etiquetas = CP.horizonte()
    pb = CP.bolsa(idx)
    pc_h = CP.contratos(idx)
    pp_media = float(pc_h.mean())
    PCT = pd.read_csv(AS.lee(F_PC, "e1/PC"), keep_default_na=False, na_values=[""])
    PPA = pd.read_csv(AS.lee(F_PPA, "e1/P"), keep_default_na=False, na_values=[""])
    exige(abs(pp_media - 287.4104) < 5e-5, f"media de XM {pp_media}")
    print("[p2p_colectivo_derivados] 2. la base de los 13 casos")
    BS = {c: base(c, TT, cap, pb, idx, etiquetas, pp_media, PCT, PPA) for c in CASOS}
    dpc = max(b["d_pc"] for b in BS.values())
    dpp = max(b["d_ppa"] for b in BS.values())
    exige(dpc <= 1e-3 and dpp <= 1e-3, f"la base no reproduce el punto PC ({dpc:.2e}) o el P ({dpp:.2e})")
    ok(f"base: el P2P colectivo y C4 hora a hora suman, por institución, los de p2p_comunitario_13casos.csv (e1/PC, "
       f"≤ {dpc:.1e} COP) y C2 los de c2_ppa_13casos.csv (e1/P, ≤ {dpp:.1e} COP), en los 13 casos")
    print("[p2p_colectivo_derivados] 3. mes a mes")
    MEN = mensual(BS)
    print("[p2p_colectivo_derivados] 4. barrido de σ")
    SIG = sigma(BS, TT, cap, pb)
    print("[p2p_colectivo_derivados] 5. COT en la deducción")
    COT = cot(BS, idx, pb)
    print("[p2p_colectivo_derivados] 6. comercializador único")
    COM, dfijo = comercializador(BS, idx, pb, pp_media)
    print("[p2p_colectivo_derivados] 7. retiro de un miembro")
    RC, RQ, cal = retiro(BS, pb)
    print("[p2p_colectivo_derivados] 8. factor de coincidencia")
    CO = coincidencia(BS)
    print("[p2p_colectivo_derivados] 9. otras")
    OT = otros(BS, PCT, pb, idx)
    for X in [MEN, SIG, COT, COM, RC, RQ, CO, OT]:
        exige("cedenar" not in X.to_csv().lower() and "asc," not in X.to_csv().lower(), "comercializador nombrado")
    SALIDA.mkdir(parents=True, exist_ok=True)
    tablas = {"mensual_13casos.csv": MEN, "sigma_13casos.csv": SIG, "cot_13casos.csv": COT,
              "comercializador_13casos.csv": COM, "retiro_comunidad.csv": RC, "retiro_quienes_quedan.csv": RQ,
              "coincidencia_13casos.csv": CO, "otros_13casos.csv": OT}
    for nombre, X in tablas.items():
        X.to_csv(SALIDA / nombre, index=False, encoding="utf-8", lineterminator="\n", float_format="%.6f")
    escribe_resumen(MEN, SIG, COT, COM, RC, RQ, CO, OT, cal, dfijo)
    guion = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    sucio = git("status", "--short", "--untracked-files=all", "--", guion)
    leidos = list(dict.fromkeys(AS.LEIDOS + CP.LEIDOS))
    todas = ([f"(atribucion_supuestos) {x}" for x in AS.COMPUERTAS] + [f"(c2_ppa) {x}" for x in CP.COMPUERTAS]
             + COMPUERTAS)
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh_:
        fh = CP._Anonimo(fh_)
        fh.write("rutas: el nombre de cada comercializador va enmascarado como [A] o [B]; el sha256 identifica "
                 "el fichero\n")
        fh.write("p2p_colectivo_derivados.py: las mediciones de la tesis hechas con el viejo mercado por el colectivo, "
                 "rehechas para el P2P colectivo (antes P2P comunitario, punto PC) y para C2 como PPA (punto P)\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n" + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + guion + "\n")
        fh.write("guiones importados (sha256; sin commit si no están en HEAD):\n")
        for g in IMPORTADOS:
            datos = (RAIZ / g).read_bytes()
            est = git("status", "--short", "--untracked-files=all", "--", g)
            fh.write(f"  {g}  {len(datos)}  {hashlib.sha256(datos).hexdigest()}  {est or '(como en HEAD)'}\n")
        fh.write("registrado en HUELLAS.csv como grupo e1/PD (CANON §14.24)\n")
        fh.write("no simula: lee los almacenes y libros de la matriz del 19 de septiembre y del barrido de sigma, y las "
                 "salidas de los puntos PC, P, S, A1, A2, T, B2, C6 y D72\n")
        fh.write("CANON.md leído como texto solo para la compuerta del precio de la justicia (tabla de §14.6)\n")
        fh.write(f"huellas: {AS.HUELLAS.relative_to(RAIZ).as_posix()}; {len(leidos)} artefactos leídos, todos con la "
                 "huella comprobada:\n")
        for g, r in leidos:
            fh.write(f"  {g}  {r}\n")
        fh.write(f"insumos de data/ (sin huella en el canon; sha256 registrado): {len(CP.INSUMOS)}\n")
        for r, b, h in CP.INSUMOS:
            fh.write(f"  {r}  {b}  {h}\n")
        fh.write(f"compuertas: {len(todas)}, todas OK:\n")
        for cpt in todas:
            fh.write(f"  OK  {cpt}\n")
        for nombre, X in tablas.items():
            fh.write(f"filas de {nombre}: {len(X)}\n")
        fh.write("salvedades: el P2P colectivo es una propuesta regulatoria; flujos del motor fijos (salvo en sigma, los "
                 "de cada corrida); en el comercializador único y el retiro la aproximación de los flujos está declarada "
                 "y calibrada; no se simula\n")
        fh.write("sin fecha: la hora de la corrida solo se imprime en la consola\n")
    print(f"[p2p_colectivo_derivados] corrida del {t0.isoformat(timespec='seconds')}, "
          f"{(_dt.datetime.now() - t0).total_seconds():.0f} s")
    print(f"[p2p_colectivo_derivados] {len(leidos)} artefactos, {len(CP.INSUMOS)} insumos, {len(todas)} compuertas; "
          f"salida en {SALIDA}")
    return 0


def _n(x: float, d: int = 3) -> str:
    return CP._n(x, d)


def escribe_resumen(MEN, SIG, COT, COM, RC, RQ, CO, OT, cal, dfijo) -> None:
    L = ["# P2P colectivo y C2: las mediciones derivadas", "",
         "Fuente: los CSV de esta carpeta (guion `reformateo/documento/scripts/articulo/p2p_colectivo_derivados.py`; "
         "CANON §14.24). Cálculo derivado, sin simular. P2P colectivo: la propuesta regulatoria de CANON §14.23 (antes "
         "«P2P comunitario»); C2: el PPA de todo el excedente a la media de XM (§14.22). MCOP salvo donde se dice.", ""]
    com = MEN[MEN.institucion == "comunidad"]
    L += ["## 1. Mes a mes (117 meses-caso de la comunidad)", "",
          "| Brecha | Meses positivos | Negativos | Empates (≤ 1 COP) | Meses negativos |", "|---|---:|---:|---:|---|"]
    for quien, x in [("P2P", "C4"), ("P2P", "C1"), ("P2P", "C5"), ("P2Pcol", "C4"), ("P2Pcol", "C1"), ("P2Pcol", "C5"),
                     ("P2Pcol", "P2P"), ("C2ppa", "C4"), ("C2ppa", "C1"), ("C2ppa", "C5")]:
        s = com[f"signo_{quien}_menos_{x}"]
        neg = com[s < 0]
        lista = ", ".join(f"{a} {m}" for a, m in zip(neg.caso, neg.mes)) if len(neg) <= 12 else f"{len(neg)} meses"
        L.append(f"| {quien} − {x} | {int((s > 0).sum())} | {int((s < 0).sum())} | {int((s == 0).sum())} | {lista} |")
    ins = MEN[MEN.institucion != "comunidad"]
    L += ["", f"Por institución y mes ({len(ins)} pares institución-mes): " + "; ".join(
        f"{q} − {x} positivo en {int((ins[f'signo_{q}_menos_{x}'] > 0).sum())}"
        for q, x in [("P2P", "C4"), ("P2Pcol", "C4"), ("P2P", "C1"), ("P2Pcol", "C1"), ("C2ppa", "C4"), ("C2ppa", "C1")]) + "."]
    L += ["", "Ventaja media por mes sobre C4, por tercil (39 meses cada uno, MCOP):", "",
          "| Tercil | P2P, generación | P2Pcol, generación | P2P, bolsa | P2Pcol, bolsa | P2P, demanda | P2Pcol, demanda |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for n in ["bajo", "medio", "alto"]:
        fila = [n]
        for t in ["t_generacion", "t_bolsa", "t_demanda"]:
            for k in ["P2P_menos_C4_COP", "P2Pcol_menos_C4_COP"]:
                fila.append(_n(com[com[t] == n][k].mean() / M, 2))
        L.append("| " + " | ".join(fila) + " |")
    s0 = SIG[SIG.institucion == "comunidad"]
    si = SIG[SIG.institucion != "comunidad"]
    L += ["", "## 2. Barrido de σ", "",
          "| σ | P2Pcol − C4, mín. (caso) | Brechas de comunidad que cambian | Pares institución-brecha que cambian "
          "(C1, C2, C3, C4, C5) | Cuáles |", "|---|---|---:|---:|---|"]
    for sv in sorted(SIG.sigma.unique()):
        c_ = s0[s0.sigma == sv]
        i_ = si[si.sigma == sv]
        n_com = int(sum(c_[f"cambia_P2Pcol_menos_{x}"].sum() for x in ["C1", "C4", "C5", "C3", "C2ppa"]))
        cam = [(r.caso, r.institucion, x) for _, r in i_.iterrows() for x in ["C1", "C4", "C5", "C3", "C2ppa"]
               if r[f"cambia_P2Pcol_menos_{x}"]]
        k = c_.P2Pcol_menos_C4_COP.idxmin()
        L.append(f"| {_n(sv, 1)} | {_n(c_.P2Pcol_menos_C4_COP.min() / M)} ({c_.loc[k, 'caso']}) | {n_com} | {len(cam)} | "
                 + "; ".join(f"{a} {b} − {x}" for a, b, x in cam) + " |")
    c_ = COT[COT.institucion == "comunidad"]
    L += ["", "## 3. El COT en la deducción (comunidad)", "",
          "| Caso | ΔP2Pcol | ΔC4 | ΔC1 | P2Pcol − C4 | P2Pcol − C1 | C2 − C4 | C2 − C1 | Cambian |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in c_.iterrows():
        cam = [f"P2Pcol − {x}" for x in CONTRA if r[f"cambia_P2Pcol_menos_{x}"]] + \
              [f"C2 − {x}" for x in ["C1", "C4"] if r[f"cambia_C2ppa_menos_{x}"]]
        L.append(f"| {r.caso} | " + " | ".join(_n(r[k] / M) for k in ["d_P2Pcol_COP", "d_C4_COP", "d_C1_COP",
                 "P2Pcol_menos_C4_COP", "P2Pcol_menos_C1_COP", "C2ppa_menos_C4_COP", "C2ppa_menos_C1_COP"])
                 + f" | {', '.join(cam) or '—'} |")
    ci = COT[COT.institucion != "comunidad"]
    L += ["", f"Pares institución-caso que cambian de signo con el COT: "
          f"{int(sum(ci[f'cambia_P2Pcol_menos_{x}'].sum() for x in CONTRA))} del P2P colectivo, "
          f"{int(sum(ci[f'cambia_C2ppa_menos_{x}'].sum() for x in ['C1', 'C4']))} de C2."]
    L += ["", "## 4. Un solo comercializador (comunidad)", "",
          f"Flujos del canon fijos: frente al contrafáctico re-simulado, P2P y el viejo colectivo quedan a "
          f"{_n(dfijo['A'] / M)} MCOP como mucho con A y a {_n(dfijo['B'] / M)} con B.", "",
          "| Variante | Caso | P2Pcol − C1 | P2Pcol − C4 | P2Pcol − C5 | C2 − C1 | C2 − C4 | C2 − C5 | Cambian |",
          "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in COM[COM.institucion == "comunidad"].iterrows():
        cam = [f"{q} − {x}" for q in ["P2Pcol", "C2ppa"] for x in ["C1", "C4", "C5"] if r[f"cambia_{q}_menos_{x}"]]
        L.append(f"| {r.variante} | {r.caso} | " + " | ".join(_n(r[f'{q}_menos_{x}_COP'] / M) for q in ["P2Pcol", "C2ppa"]
                                                              for x in ["C1", "C4", "C5"]) + f" | {', '.join(cam) or '—'} |")
    ci = COM[COM.institucion != "comunidad"]
    for v in ["A", "B"]:
        x_ = ci[ci.variante == v]
        cam = [f"{r.caso} {r.institucion} {q} − {k}" for _, r in x_.iterrows() for q in ["P2Pcol", "C2ppa"]
               for k in ["C1", "C4", "C5"] if r[f"cambia_{q}_menos_{k}"]]
        L += ["", f"Pares institución-caso que cambian de signo con todas en {v}: {len(cam)} (" + "; ".join(cam) + ")."]
    L += ["", "## 5. Retiro de un miembro (54 comunidades de cuatro)", "",
          f"Aproximación de los flujos (lado corto en las horas con mercado, al precio medio de la hora), calibrada en el "
          f"mercado: comunidad a {_n(cal['err']['P2P_com'] / M)} MCOP como mucho, el viejo colectivo a "
          f"{_n(cal['err']['col_com'] / M)}; por institución, |error| mediano {_n(cal['ei_med'], 0)} COP y máximo "
          f"{_n(cal['ei_max'], 0)}; la clase «se mueve menos» del mercado coincide con el canon en {cal['acuerdo']} de 216.", "",
          "| Brecha de la comunidad | Comunidades con signo distinto del de la comunidad completa | Mínimo (MCOP) |",
          "|---|---:|---:|"]
    for q in ["P2Pcol", "C2ppa"]:
        for x in ["C4", "C1", "C5"]:
            L.append(f"| {q} − {x} | {int(RC[f'cambia_{q}_menos_{x}'].sum())} | {_n(RC[f'{q}_menos_{x}_COP'].min() / M)} |")
    cam = [f"{r.caso} sin {r.retirada}: {q} − {x} = {_n(r[f'{q}_menos_{x}_COP'] / M)}" for _, r in RC.iterrows()
           for q in ["P2Pcol", "C2ppa"] for x in ["C4", "C1", "C5"] if r[f"cambia_{q}_menos_{x}"]]
    L += ["", "Comunidades con una brecha que cambia de signo: " + ("; ".join(cam) or "ninguna") + ". Caso del art. 20 "
          f"del P2P colectivo sin el miembro: caso 1 en {int((RC.caso_art20_P2Pcol == 1).sum())}, caso 2 en "
          f"{int((RC.caso_art20_P2Pcol == 2).sum())}. Pares (quien se queda) con P2Pcol − C4 que cambia de signo: "
          f"{int(RQ.cambia_P2Pcol_menos_C4.sum())}."]
    L += ["", "| Sale | Pares | Mediana \\|pérdida\\| P2Pcol (miles) | Mediana \\|pérdida\\| C4 (miles) | P2Pcol pierde / gana | "
          "Se mueve menos con P2Pcol |", "|---|---:|---:|---:|---:|---:|"]
    for ret, g in list(RQ.groupby("retirada", sort=False)) + [("Todas", RQ)]:
        L.append(f"| {ret} | {len(g)} | {_n(g.perdida_P2Pcol_COP.abs().median() / 1e3, 0)} "
                 f"({_n(100 * g.perdida_rel_P2Pcol.abs().median(), 2)} %) | {_n(g.perdida_C4_COP.abs().median() / 1e3, 0)} "
                 f"({_n(100 * g.perdida_rel_C4.abs().median(), 2)} %) | {int((g.perdida_P2Pcol_COP > 0).sum())} / "
                 f"{int((g.perdida_P2Pcol_COP < 0).sum())} | {int((g.mas_estable == 'P2Pcol').sum())} |")
    L += ["", "## 6. Factor de coincidencia", "", "| Caso | P2Pcol | P2P | C4 | Viejo colectivo |", "|---|---:|---:|---:|---:|"]
    for _, r in CO.iterrows():
        L.append(f"| {r.caso} | {_n(r.coincidencia_P2Pcol)} | {_n(r.coincidencia_P2P)} | {_n(r.coincidencia_C4)} | "
                 f"{_n(r.coincidencia_P2P_colectivo_viejo)} |")
    L += ["", "C2 no acredita contra importación (vende todo el excedente): no tiene factor, como C3.", "",
          "## 7. Precio de la justicia frente a C4, 11 fronteras y umbral", "",
          "| Caso | PoF P2Pcol (%) | Clase | PoF P2P (%) | Clase P2P | 11 fronteras: P2Pcol − P2P | − C4 |",
          "|---|---:|---|---:|---|---:|---:|"]
    for _, r in OT.iterrows():
        L.append(f"| {r.caso} | {_n(100 * r.pof_P2Pcol, 1)} | {r.clase_P2Pcol} | {_n(100 * r.pof_P2P, 1)} | {r.clase_P2P} | "
                 f"{_n(r.once_fronteras_P2Pcol_menos_P2P_COP / M)} | {_n(r.once_fronteras_P2Pcol_menos_C4_COP / M)} |")
    o = OT.iloc[0]
    L += ["", "Umbral de 100 kW, E4 − 7 × P1 (MCOP): " + "; ".join(
        f"{k} {_n(o[f'umbral_E4_menos_7P1_{k}_COP'] / M, 2)}" for k in ["P2P", "P2Pcol", "P2Pcol_c1todos", "C4", "C2ppa"])
          + ". Techo literal del Anexo 4: en las 38 horas con la bolsa sobre el ponderado no hay excedente en ningún "
          "caso, así que el P2P colectivo y C2 cambian cero exacto.", "",
          "Salvedades: el P2P colectivo es una propuesta regulatoria; flujos del motor fijos salvo en σ; en el "
          "comercializador único y en el retiro, aproximación declarada y calibrada; no se simula nada.", ""]
    (SALIDA / "resumen.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    sys.exit(main())
