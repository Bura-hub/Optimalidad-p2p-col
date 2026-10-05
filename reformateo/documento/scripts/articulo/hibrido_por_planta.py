"""
hibrido_por_planta.py — El híbrido H1, «autogenerador colectivo de crédito
mutualizado», y su segunda etapa H2, frente a C4, C1, el mercado P2P y el P2P
colectivo
===============================================================================
Actividades 2.1 y 2.2 de la propuesta (escenarios regulatorios y su
comparación). Cálculo DERIVADO del canon: no simula el mercado ni usa el
servidor. Lee artefactos con huella en `Documentos/canon_2026-09/HUELLAS.csv`
(comprueba tamaño y `sha256` de cada uno antes de leerlo) e importa, en lugar
de copiarlas, las funciones de `atribucion_supuestos.py` (punto S),
`c2_ppa.py` (punto P) y `p2p_comunitario.py` (punto PC, el P2P colectivo).

QUÉ ES (diseño que el autor aprobó estudiar el 2026-10-04; análisis previo en
el scratchpad de la sesión, `analisis_hibrido.md`):

  H1. El mismo mercado P2P (los flujos y precios del almacén de cada caso) con
      el residual al fondo común del autogenerador colectivo (CREG 101 072,
      art. 21), pero:
        * cada kWh del fondo se deduce con el numeral del art. 25 de la CREG
          174 que corresponde a SU PLANTA DE ORIGEN (numeral 1, κ·Cv, si la
          planta tiene hasta 100 kW de capacidad instalada; numeral 2,
          κ·Cv + Θ, si pasa de 100 kW), y no con el caso del art. 20 ni con la
          regla del 10 %;
        * el fondo se reparte con la fórmula «primero cada miembro su propia
          exportación; el sobrante, a quien todavía importa» (ver abajo);
        * el intercambio PAGA: cada kWh comprado dentro paga la deducción del
          numeral de la planta del vendedor (κ·Cv o κ·Cv + Θ), la misma que
          pagaría ese kWh si pasara por el fondo. Ningún kWh paga menos de lo
          que pagaría su planta como AGPE individual (no hay exención). La
          paga el comprador, que es la frontera a la que se acredita, como en
          el fondo. Los pagos internos del mercado (precio con el techo del
          comprador, CAL-35) se conservan y suman cero.
  H2. H1 más la exención del Cv del intercambio dentro del numeral 1: lo que
      vende una planta de hasta 100 kW no paga nada (es el intercambio exento
      del P2P colectivo); lo que vende una de más de 100 kW paga κ·Cv + Θ como
      en H1. Variante H2θ (la del análisis, §5.3, como `v10_theta` del punto
      S): el intercambio de una planta del numeral 2 paga solo Θ.
  H1 fondo. La lectura literal del análisis (§5.1): sin intercambio, el fondo
      es toda la inyección (s, d en lugar de sr, dr), con la misma deducción
      por planta y la misma fórmula. Difiere de H1 solo en a quién se asigna
      cada kWh, porque en H1 el kWh intercambiado ya paga lo que pagaría en el
      fondo.

LA FÓRMULA DEL PDE («primero lo propio»), POR MES. Con S_i y D_i la inyección
y la importación (residuales en H1 y H2, brutas en H1 fondo) de cada miembro
en el mes:
    propio_i  = mín(S_i, D_i)
    X_i = S_i − propio_i (sobrante),  R_i = D_i − propio_i (importación que le
    queda); se entrega mín(ΣX, ΣR) en proporción a R_i; lo que sobra de ΣX
    vuelve a su dueño en proporción a X_i (y va a la bolsa desde hx).
    PDE_i = (propio_i + recibido_i + devuelto_i) / ΣS.
Se elige el MES y no la hora porque el crédito del art. 21 y el cupo se
liquidan por mes (C-175: cupo = importación del mes, Anexo 4), el PDE se
declara por periodo (art. 19) y el análisis lo pone como una fórmula que el
comercializador calcula al cierre del ciclo con el acuerdo de reporte del
art. 19 (C-224). El perfil horario del fondo es el del colectivo
(`atribucion_supuestos.colectivo`), como en C4 y en el P2P colectivo.

TRAZABILIDAD DEL ORIGEN, proporcional en el mes: lo propio y lo devuelto
vienen de la planta del miembro; lo recibido, del sobrante de todas, en
proporción a su X. Con los repartos igual y por importación, todo kWh del
fondo lleva la mezcla de la comunidad del mes. La deducción que recibe el
miembro j es κ·Cv_j + Θ_j · (fracción de su asignación que viene de plantas
del numeral 2), con el Cv y el Θ de la tarifa de j (la frontera acreditada,
como el motor en C4).

DESCOMPOSICIÓN (lo que el análisis echa en falta, §3): P2Pcom − P2P (mercado)
se parte en lo que pone el fondo y lo que pone que la planta grande pase al
numeral 1 (I1 y N1, lectura literal de la pregunta abierta 2), por los dos
órdenes y Shapley:
    X = P2Pcom con la deducción por planta (intercambio exento, PDE igual)
    Y = mercado P2P con el residual por miembro deducido con el caso del P2P
        colectivo (en I1 y N1, todas en el numeral 1)
    orden «fondo primero»:   fondo = X − P2P,    numeral = P2Pcom − X
    orden «numeral primero»: numeral = Y − P2P,  fondo = P2Pcom − Y
En los once casos sin plantas mixtas X = P2Pcom e Y = P2P al bit (compuerta).

CESIÓN Y COMPENSACIÓN. Quien cede crédito (su sobrante va a otro) pierde la
bolsa que ese kWh le habría dado; quien lo recibe, gana su tarifa menos la
deducción. Se mide la energía cedida y recibida por institución y una
compensación por contrato civil declarada: el que recibe paga al que cede la
bolsa del mes ponderada por el perfil del fondo (Σ_h SR_h·pb_h / Σ_h SR_h).
Suma cero. Se cuentan los pares institución-caso bajo C1 y bajo C4 sin ella y
con ella.

COMPUERTAS (falla en voz alta; ningún `except`; todo finito):
  * con el intercambio exento, la deducción del caso y el PDE igual, la función
    del híbrido reproduce el P2P colectivo de `p2p_comunitario_13casos.csv`
    (e1/PC) por institución al peso en los 13 casos;
  * en los once casos sin plantas mixtas la deducción por planta es la del caso
    al bit, y entonces X = P2Pcom; H1 fondo con PDE igual = C4_sin10 y con PDE
    por importación = C4_sin10_imp; y en los ocho casos con todas las plantas
    en el numeral 1, H2 con PDE por importación residual = P2Pcom_imp
    (por institución, e1/PC);
  * la reliquidación del mercado por miembro reproduce B_P2P de e1/PC; Y = P2P
    en los once; donde nadie agota el cupo con todas las plantas en el numeral
    1 (E0, K1, CV2, SINU) H2 con la fórmula reproduce el mercado P2P (si no,
    se informa cuánto se separa);
  * la liquidación del fondo con traza reproduce `atribucion_supuestos.
    colectivo` al bit; la energía se conserva: lo vendido es lo comprado en
    cada hora, crédito + exceso = asignado, la suma de lo asignado es el fondo
    de cada hora, el crédito del mes no pasa de la importación del mes, y
    autoconsumo + vendido dentro + fondo = generación de la comunidad;
  * los repartos de la fórmula suman el fondo de cada mes, lo cedido es lo
    recibido, nadie recibe más que su importación restante; la fracción del
    numeral 2 está en [0, 1]; la compensación suma cero;
  * las identidades de la descomposición y de Shapley cierran en cada fila; la
    comunidad es la suma de sus instituciones.

Escribe en SALIDAS_SERVIDOR/hibrido_por_planta_2026-10-04/:

    hibrido_13casos.csv    una fila por caso × institución y una «comunidad»
                           por caso
    resumen.md             la comunidad por caso
    procedencia.txt        commit, versiones, huellas, insumos y compuertas,
                           sin fecha (dos corridas: iguales byte a byte)

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/hibrido_por_planta.py

SALVEDADES: es una propuesta regulatoria, no la norma vigente (H1 exige
cambiar el art. 20 de la CREG 101 072 para el AC de hasta 1 MW y aclarar que el
PDE puede declararse como fórmula; H2 además exime del Cv al intercambio del
numeral 1). Los flujos son los del motor, fijos: con el intercambio pagando la
deducción, el piso del vendedor cambia y el mercado transaría otra cosa, de
modo que H1 y H2 con flujos son aproximados donde el piso cambia; H1 fondo no
usa flujos y es exacto. El costo del crédito mutualizado para los demás
usuarios no se mide (no hay modelo de traslado al CU). Comercializador único
(art. 10) y perfil horario declarado como supuestos; los comercializadores se
nombran A y B.

Sin registrar en HUELLAS.csv (borrador del registro en el scratchpad de la
sesión, `registro_h1_borrador.md`).

Actividades 2.1 y 2.2.
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
AQUI = Path(__file__).resolve().parent
for _p in (str(RAIZ), str(AQUI)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import atribucion_supuestos as AS  # noqa: E402
import c2_ppa as CP  # noqa: E402
import p2p_comunitario as PC  # noqa: E402
from core.opciones_externas import reparto_anexo4  # noqa: E402
from scenarios.scenario_c4_creg101072 import pde_por_regla  # noqa: E402

SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
SALIDA = SALIDAS / "hibrido_por_planta_2026-10-04"
CASOS = AS.CASOS
F_PC = "p2p_comunitario_2026-10-02/p2p_comunitario_13casos.csv"
UMBRAL_KW = PC.UMBRAL_KW                 # art. 25 de la CREG 174: numeral 1 hasta 100 kW
MIXTOS_ESPERADOS = {"I1", "N1"}          # plantas a los dos lados de 100 kW
NUMERAL1_SIN_AGOTAR = PC.NUMERAL1_SIN_AGOTAR
N_PARES = PC.N_PARES
EMPATE = CP.EMPATE
M = 1e6
MODULOS = PC.MODULOS
IMPORTADOS = PC.IMPORTADOS + ["reformateo/documento/scripts/articulo/p2p_comunitario.py"]
REGLAS_CARGO = ("exento", "H1", "H2", "H2theta")
HIBRIDOS = ["H1", "H2", "H2theta", "H1_fondo", "H1_compensado"]
CONTRA = ["C4", "C1", "P2P", "P2Pcom"]
SOLO_COMUNIDAD = ["gini_H1", "gini_H2", "gini_H1_fondo", "gini_H1_compensado", "gini_P2Pcom", "gini_C4", "gini_C1",
                  "gini_P2P"]

COMPUERTAS: list[str] = []


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[hibrido] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    COMPUERTAS.append(msg)
    print(f"[hibrido]   OK  {msg}")


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


def finito(x, qué: str):
    exige(bool(np.isfinite(np.asarray(x, dtype=float)).all()), f"{qué}: valores no finitos")
    return x


# ── Funciones puras (las prueba tests/test_hibrido_por_planta.py) ───────────
def numeral_planta(capk, umbral_kw: float = UMBRAL_KW) -> np.ndarray:
    """Numeral del art. 25 de la CREG 174 de cada planta por su capacidad
    instalada: 1 hasta `umbral_kw` (incluido), 2 por encima."""
    capk = np.asarray(capk, dtype=float)
    if not np.isfinite(capk).all() or (capk < 0).any():
        raise ValueError(f"capacidades no válidas: {capk}")
    return np.where(capk <= umbral_kw, 1, 2).astype(int)


def pde_primero_propio(S_h: np.ndarray, D_h: np.ndarray, mes: np.ndarray) -> tuple[dict, dict]:
    """El PDE de la fórmula «primero cada miembro su propia exportación; el
    sobrante, a quien todavía importa», por mes. Devuelve ({mes: (N,) pesos},
    {mes: traza}), con la traza en kWh del mes: propio, sobrante X, restante R,
    recibido, devuelto, cedido y asignado. Un mes sin inyección cae al reparto
    igual (no hay nada que repartir)."""
    S_h, D_h = np.asarray(S_h, dtype=float), np.asarray(D_h, dtype=float)
    if S_h.shape != D_h.shape or (S_h < 0).any() or (D_h < 0).any():
        raise ValueError("inyección o importación con forma distinta o negativas")
    N = S_h.shape[0]
    W, TR = {}, {}
    for m in np.unique(mes):
        S = S_h[:, mes == m].sum(axis=1)
        D = D_h[:, mes == m].sum(axis=1)
        propio = np.minimum(S, D)
        X = S - propio
        R = D - propio
        pool, RR = float(X.sum()), float(R.sum())
        entrega = min(pool, RR)
        recibido = entrega * R / RR if RR > 0.0 else np.zeros(N)
        devuelto = (pool - entrega) * X / pool if pool > 0.0 else np.zeros(N)
        cedido = entrega * X / pool if pool > 0.0 else np.zeros(N)
        asignado = propio + recibido + devuelto
        tot = float(S.sum())
        W[m] = asignado / tot if tot > 0.0 else np.full(N, 1.0 / N)
        TR[m] = dict(S=S, D=D, propio=propio, X=X, R=R, pool=pool, entrega=entrega, recibido=recibido,
                     devuelto=devuelto, cedido=cedido, asignado=asignado)
    return W, TR


def fraccion_numeral2_traza(TR: dict, n2: np.ndarray) -> dict:
    """{mes: (N,)} fracción de lo asignado a cada miembro que viene de plantas
    del numeral 2, con la traza de la fórmula: lo propio y lo devuelto, de su
    planta; lo recibido, del sobrante de todas en proporción a X."""
    n2 = np.asarray(n2, dtype=float)
    out = {}
    for m, t in TR.items():
        mezcla = float((t["X"] * n2).sum()) / t["pool"] if t["pool"] > 0.0 else 0.0
        num = t["propio"] * n2 + t["recibido"] * mezcla + t["devuelto"] * n2
        a = t["asignado"]
        f = np.where(a > 0.0, num / np.where(a > 0.0, a, 1.0), n2)
        out[m] = np.clip(f, 0.0, 1.0)
    return out


def fraccion_numeral2_mezcla(S_h: np.ndarray, n2: np.ndarray, mes: np.ndarray) -> dict:
    """{mes: (N,)} con un reparto que no traza el origen (igual, importación):
    cada kWh del fondo lleva la mezcla de la comunidad en el mes."""
    S_h = np.asarray(S_h, dtype=float)
    n2 = np.asarray(n2, dtype=float)
    N = S_h.shape[0]
    out = {}
    for m in np.unique(mes):
        S = S_h[:, mes == m].sum(axis=1)
        tot = float(S.sum())
        f = float((S * n2).sum()) / tot if tot > 0.0 else float(n2.mean())
        out[m] = np.full(N, min(max(f, 0.0), 1.0))
    return out


def ded_por_origen(frac2: dict, kap: float, Cv: np.ndarray, Th: np.ndarray, mes: np.ndarray) -> np.ndarray:
    """(N, T) deducción del art. 25 por la planta de origen: κ·Cv_j + Θ_j por
    la fracción del numeral 2 de lo que recibe j. Con fracción 0 es el numeral
    1 (κ·Cv) y con 1 el numeral 2 (κ·Cv + Θ), al bit como `deduccion_caso`."""
    Cv, Th = np.asarray(Cv, dtype=float), np.asarray(Th, dtype=float)
    ded = kap * Cv
    extra = np.zeros_like(Th)
    for m, f in frac2.items():
        h = mes == m
        extra[:, h] = Th[:, h] * np.asarray(f, dtype=float)[:, None]
    return ded + extra


def compras_por_numeral(vendedor, comprador, hora, kwh, n_de: dict, ags: list[str], T: int) -> tuple[np.ndarray, np.ndarray]:
    """(q1, q2), (N, T): lo que cada miembro compra dentro a plantas del
    numeral 1 y del numeral 2 (`n_de`: agente → numeral)."""
    idx = {a: i for i, a in enumerate(ags)}
    ic = np.array([idx[x] for x in comprador], dtype=int)
    nv = np.array([n_de[x] for x in vendedor], dtype=int)
    h = np.asarray(hora, dtype=int)
    k = np.asarray(kwh, dtype=float)
    q1, q2 = np.zeros((len(ags), T)), np.zeros((len(ags), T))
    np.add.at(q1, (ic[nv == 1], h[nv == 1]), k[nv == 1])
    np.add.at(q2, (ic[nv == 2], h[nv == 2]), k[nv == 2])
    return q1, q2


def cargo_intercambio(q1: np.ndarray, q2: np.ndarray, kap: float, Cv: np.ndarray, Th: np.ndarray,
                      regla: str) -> np.ndarray:
    """(N, T) lo que paga el comprador por lo comprado dentro, con el Cv y el Θ
    de su tarifa. «exento»: nada (P2P colectivo). «H1»: el numeral de la planta
    del vendedor (κ·Cv o κ·Cv + Θ). «H2»: el numeral 1 exento y el 2 como H1.
    «H2theta»: el numeral 1 exento y el 2 solo Θ."""
    Cv, Th = np.asarray(Cv, dtype=float), np.asarray(Th, dtype=float)
    if regla == "exento":
        return np.zeros_like(Cv)
    if regla == "H1":
        return q1 * (kap * Cv) + q2 * (kap * Cv + Th)
    if regla == "H2":
        return q2 * (kap * Cv + Th)
    if regla == "H2theta":
        return q2 * Th
    raise ValueError(f"regla {regla!r}")


def colectivo_traza(iny, ret, CU, ded, mes, pb, pesos, qué: str):
    """Como `atribucion_supuestos.colectivo` (el colectivo mensual del motor),
    devolviendo además el crédito y lo asignado: (valor, crédito, exceso,
    asignado), cada uno (N, T)."""
    N, T = iny.shape
    val, crs, exs, asg = np.zeros((N, T)), np.zeros((N, T)), np.zeros((N, T)), np.zeros((N, T))
    for m in np.unique(mes):
        h = np.flatnonzero(mes == m)
        w = np.asarray(pesos[m], dtype=float)
        exige(abs(w.sum() - 1.0) <= 1e-9 and (w >= 0).all(), f"{qué}: pesos del mes {m} no suman 1")
        asign = w[:, None] * iny[:, h].sum(axis=0)[None, :]
        cr, ex, _ = reparto_anexo4(asign, ret[:, h])
        pr = CU[:, h].mean(axis=1) - ded[:, h].mean(axis=1)
        val[:, h] = cr * pr[:, None] + AS.valor_exceso(ex, pb[h], qué)
        crs[:, h], exs[:, h], asg[:, h] = cr, ex, asign
    return val, crs, exs, asg


def valor_hibrido(au, s, d, v, q, CU, pagos, cargo, ded, mes, pb, pesos, qué: str) -> dict:
    """El valor hora a hora (N, T) de un híbrido: autoconsumo a la tarifa,
    ahorro CU·q del comprador menos el cargo del intercambio, pagos internos
    (suman cero) y el colectivo sobre el residual (sr, dr). Con q = v = 0 y
    pagos = cargo = 0 es C4 con la deducción `ded` y el reparto `pesos`."""
    sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
    col, cr, ex, asg = colectivo_traza(sr, dr, CU, ded, mes, pb, pesos, qué)
    H = au * CU + CU * q - cargo + pagos + col
    return dict(H=H, val=H.sum(axis=1), cr=cr, ex=ex, asg=asg, sr=sr, dr=dr)


def precio_compensacion(SR_h: np.ndarray, pb: np.ndarray, mes: np.ndarray) -> dict:
    """{mes: COP/kWh} la bolsa del mes ponderada por el perfil horario del
    fondo de la comunidad (Σ_h SR_h·pb_h / Σ_h SR_h); 0 sin fondo."""
    SR = np.asarray(SR_h, dtype=float).sum(axis=0)
    out = {}
    for m in np.unique(mes):
        h = mes == m
        tot = float(SR[h].sum())
        out[m] = float((SR[h] * pb[h]).sum()) / tot if tot > 0.0 else 0.0
    return out


def compensacion(TR: dict, precio: dict) -> np.ndarray:
    """(N,) COP: quien cede cobra el precio del mes por lo cedido y quien
    recibe lo paga por lo recibido. Suma cero porque lo cedido es lo recibido."""
    N = len(next(iter(TR.values()))["S"])
    out = np.zeros(N)
    for m, t in TR.items():
        out += precio[m] * (t["cedido"] - t["recibido"])
    return out


def descomposicion(p2pcom: float, p2p: float, x_planta: float, y_caso: float) -> dict:
    """P2Pcom − P2P en el fondo y el numeral, por los dos órdenes y Shapley."""
    vals = np.array([p2pcom, p2p, x_planta, y_caso], dtype=float)
    if not np.isfinite(vals).all():
        raise ValueError(f"valores no finitos: {vals}")
    fA, nA = x_planta - p2p, p2pcom - x_planta          # fondo primero
    nB, fB = y_caso - p2p, p2pcom - y_caso              # numeral primero
    return dict(total=p2pcom - p2p, fondo_fondo_primero=fA, numeral_fondo_primero=nA,
                numeral_numeral_primero=nB, fondo_numeral_primero=fB,
                fondo_shapley=(fA + fB) / 2, numeral_shapley=(nA + nB) / 2, interaccion=fB - fA)


# ── Un caso ─────────────────────────────────────────────────────────────────
def caso(c: str, TT, cap, pb, PCT: pd.DataFrame) -> tuple[list[dict], dict]:
    L = AS.carga(c, TT, cap)
    N, ags, mes = L["N"], L["ags"], L["mes"]
    s, d, v, q, CU, au, G, D = L["s"], L["d"], L["v"], L["q"], L["CU"], L["au"], L["G"], L["D"]
    kap, Cv, Th = L["kap"], L["Cv"], L["Th"]
    T = s.shape[1]
    sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
    num = numeral_planta(L["capk"])
    n2 = (num == 2).astype(float)
    mixto = bool(len(set(num)) > 1)
    exige(bool((np.abs(L["ded1"] - (kap * Cv + np.where(L["capk"][:, None] > 100.0, Th, 0.0))) == 0).all()),
          f"{c}: ded1 del punto S no es el numeral de la planta")
    cs, cin, suma = PC.caso_art20_sin_10(L["capk"], N)
    exige(suma <= PC.AGPE_LIMIT_KW, f"{c}: la comunidad pasa de 1 MW ({suma:.1f} kW): H1 no aplica")
    ded_caso = PC.deduccion_caso(cs, kap, Cv, Th)
    cero = np.zeros((N, T))
    fl = AS.almacen(c, "flujos").astype({"kwh": "float64", "precio": "float64", "techo_comprador": "float64"})
    pag = PC.pagos_internos(fl.vendedor.to_numpy(), fl.comprador.to_numpy(), fl.hora.to_numpy(), fl.kwh.to_numpy(),
                            fl.precio.to_numpy(), fl.techo_comprador.to_numpy(), ags, T)
    finito(pag, f"{c} pagos")
    q1, q2 = compras_por_numeral(fl.vendedor.to_numpy(), fl.comprador.to_numpy(), fl.hora.to_numpy(),
                                 fl.kwh.to_numpy(), dict(zip(ags, num)), ags, T)
    exige(float(np.abs(q1 + q2 - q).max()) <= 1e-3, f"{c}: compras por numeral ≠ compra_p2p")
    exige(float(np.abs(v.sum(axis=0) - q.sum(axis=0)).max()) <= 1e-3, f"{c}: lo vendido ≠ lo comprado en una hora")
    # repartos
    W_ig = PC.igual(N, mes)
    W_impr = PC.pesos_proporcionales(dr, mes)
    W_impd = pde_por_regla("importacion", G, D, mes)
    W_f, TR_f = pde_primero_propio(sr, dr, mes)           # H1 y H2: el residual
    W_f0, TR_f0 = pde_primero_propio(s, d, mes)           # H1 fondo: toda la inyección
    # deducción por planta de origen
    ded_mez_r = ded_por_origen(fraccion_numeral2_mezcla(sr, n2, mes), kap, Cv, Th, mes)
    ded_mez_b = ded_por_origen(fraccion_numeral2_mezcla(s, n2, mes), kap, Cv, Th, mes)
    fr_f = fraccion_numeral2_traza(TR_f, n2)
    fr_f0 = fraccion_numeral2_traza(TR_f0, n2)
    ded_f = ded_por_origen(fr_f, kap, Cv, Th, mes)
    ded_f0 = ded_por_origen(fr_f0, kap, Cv, Th, mes)
    for k_, x in [("mezcla residual", ded_mez_r), ("mezcla bruta", ded_mez_b), ("fórmula", ded_f), ("fórmula fondo", ded_f0)]:
        finito(x, f"{c} deducción {k_}")
        exige(bool((x >= kap * Cv - 1e-9).all() and (x <= kap * Cv + Th + 1e-9).all()),
              f"{c}: deducción {k_} fuera de [κ·Cv, κ·Cv + Θ]")
    cargo = {r: cargo_intercambio(q1, q2, kap, Cv, Th, r) for r in REGLAS_CARGO}

    def VH(vv, qq, pp, cg, dd, W, qué):
        return valor_hibrido(au, s, d, vv, qq, CU, pp, cg, dd, mes, pb, W, f"{c} {qué}")

    V = {}
    V["chk_P2Pcom"] = VH(v, q, pag, cargo["exento"], ded_caso, W_ig, "P2P colectivo (compuerta)")
    V["P2Pcom_planta"] = VH(v, q, pag, cargo["exento"], ded_mez_r, W_ig, "P2P colectivo por planta (X)")
    V["H1"] = VH(v, q, pag, cargo["H1"], ded_f, W_f, "H1")
    V["H1_igual"] = VH(v, q, pag, cargo["H1"], ded_mez_r, W_ig, "H1, PDE igual")
    V["H1_imp"] = VH(v, q, pag, cargo["H1"], ded_mez_r, W_impr, "H1, PDE por importación residual")
    V["H2"] = VH(v, q, pag, cargo["H2"], ded_f, W_f, "H2")
    V["H2_igual"] = VH(v, q, pag, cargo["H2"], ded_mez_r, W_ig, "H2, PDE igual")
    V["H2_imp"] = VH(v, q, pag, cargo["H2"], ded_mez_r, W_impr, "H2, PDE por importación residual")
    V["H2theta"] = VH(v, q, pag, cargo["H2theta"], ded_f, W_f, "H2θ")
    V["H1_fondo"] = VH(cero, cero, cero, cero, ded_f0, W_f0, "H1 fondo")
    V["H1_fondo_igual"] = VH(cero, cero, cero, cero, ded_mez_b, W_ig, "H1 fondo, PDE igual")
    V["H1_fondo_imp"] = VH(cero, cero, cero, cero, ded_mez_b, W_impd, "H1 fondo, PDE por importación")
    for k_, x in V.items():
        finito(x["H"], f"{c} {k_}")
    # el mercado por miembro: con la deducción de su planta (P2P) y con la del caso (Y)
    p2p_rep = (au * CU + CU * q + pag + AS.art25(sr, dr, CU, L["ded1"], mes, pb, f"{c} P2P")[0]).sum(axis=1)
    y_caso = (au * CU + CU * q + pag + AS.art25(sr, dr, CU, ded_caso, mes, pb, f"{c} P2P con el caso")[0]).sum(axis=1)
    # compensación de quien cede crédito en H1 (sobre el residual) y en H1 fondo
    pre_r = precio_compensacion(sr, pb, mes)
    pre_b = precio_compensacion(s, pb, mes)
    comp = compensacion(TR_f, pre_r)
    comp0 = compensacion(TR_f0, pre_b)
    # ── compuertas del caso ─────────────────────────────────────────────────
    pc = PCT[PCT.caso == c].set_index("institucion")
    exige(list(pc.index) == ags + ["comunidad"], f"{c}: instituciones del punto PC")
    ref = {k_: pc.loc[ags, k_].to_numpy(dtype=float) for k_ in
           ["P2Pcom_COP", "P2Pcom_imp_COP", "C4_sin10_COP", "C4_sin10_imp_COP", "B_C1_COP", "B_C4_COP", "B_P2P_COP"]}
    for k_, x in ref.items():
        finito(x, f"{c} e1/PC {k_}")
    # la liquidación con traza = la del motor, al bit
    val_as, _ = AS.colectivo(V["H1"]["sr"], V["H1"]["dr"], CU, ded_f, mes, pb, W_f, f"{c} H1 (AS)")
    d_traza = float(np.abs((au * CU + CU * q - cargo["H1"] + pag + val_as) - V["H1"]["H"]).max())
    # energía
    d_en, d_gen = 0.0, 0.0
    for k_, x in V.items():
        SRh = x["sr"].sum(axis=0)
        d_en = max(d_en, float(np.abs(x["asg"].sum(axis=0) - SRh).max()),
                   float(np.abs(x["cr"] + x["ex"] - x["asg"]).max()))
        for m in np.unique(mes):
            h = mes == m
            exige(bool((x["cr"][:, h].sum(axis=1) <= x["dr"][:, h].sum(axis=1) + 1e-6).all()),
                  f"{c} {k_}: crédito del mes {m} sobre la importación")
            vv = v if not k_.startswith("H1_fondo") else cero
            # autoconsumo, sobrante y faltante del almacén cuadran con G y D a 1e-3 kWh por celda (float32;
            # compuerta de atribucion_supuestos.carga): el balance se exige a esa tolerancia
            gen = float(G[:, h].sum())
            bal = float(au[:, h].sum() + vv[:, h].sum() + x["asg"][:, h].sum())
            exige(abs(bal - gen) <= 1e-3 * N * int(h.sum()), f"{c} {k_}: balance de energía del mes {m}")
            d_gen = max(d_gen, abs(bal - gen))
    # repartos de la fórmula
    d_rep = 0.0
    for TR in (TR_f, TR_f0):
        for m, t in TR.items():
            esc = max(1.0, float(t["S"].sum()))
            d_rep = max(d_rep, abs(float(t["asignado"].sum() - t["S"].sum())) / esc,
                        abs(float(t["cedido"].sum() - t["recibido"].sum())) / esc)
            exige(bool((t["recibido"] <= t["R"] + 1e-9 * esc).all()), f"{c}: alguien recibe más que su importación restante")
            exige(bool((t["cedido"] <= t["X"] + 1e-9 * esc).all()), f"{c}: alguien cede más que su sobrante")
    exige(abs(float(comp.sum())) <= 1e-6 * max(1.0, float(np.abs(comp).sum())) and
          abs(float(comp0.sum())) <= 1e-6 * max(1.0, float(np.abs(comp0).sum())), f"{c}: la compensación no suma cero")
    aux = dict(
        c=c, mixto=mixto, caso=cs, n_num2=int(n2.sum()),
        d_p2pcom=float(np.abs(V["chk_P2Pcom"]["val"] - ref["P2Pcom_COP"]).max()),
        d_p2p=float(np.abs(p2p_rep - ref["B_P2P_COP"]).max()),
        d_ded_caso=float(max(np.abs(ded_mez_r - ded_caso).max(), np.abs(ded_mez_b - ded_caso).max(),
                             np.abs(ded_f - ded_caso).max(), np.abs(ded_f0 - ded_caso).max())),
        d_x=float(np.abs(V["P2Pcom_planta"]["val"] - V["chk_P2Pcom"]["val"]).max()),
        d_y=float(np.abs(y_caso - p2p_rep).max()),
        d_f_ig=float(np.abs(V["H1_fondo_igual"]["val"] - ref["C4_sin10_COP"]).max()),
        d_f_imp=float(np.abs(V["H1_fondo_imp"]["val"] - ref["C4_sin10_imp_COP"]).max()),
        d_h2_imp=float(np.abs(V["H2_imp"]["val"] - ref["P2Pcom_imp_COP"]).max()),
        d_h2_p2p=float(np.abs(V["H2"]["val"] - p2p_rep).max()),
        d_h2_p2p_com=float(V["H2"]["val"].sum() - p2p_rep.sum()),
        d_h2_h1=float(np.abs(V["H2"]["val"] - V["H1"]["val"]).max()),
        agota=bool(any((t["X"] > 1e-9).any() for t in TR_f.values())),
        d_traza=d_traza, d_en=d_en, d_gen=d_gen, d_rep=d_rep,
    )
    # ── filas ───────────────────────────────────────────────────────────────
    filas = []
    TRs = {k_: np.zeros(N) for k_ in ["cedido", "recibido", "propio", "devuelto"]}
    TR0s = {k_: np.zeros(N) for k_ in ["cedido", "recibido"]}
    for t in TR_f.values():
        for k_ in TRs:
            TRs[k_] += t[k_]
    for t in TR_f0.values():
        for k_ in TR0s:
            TR0s[k_] += t[k_]
    val = {k_: x["val"] for k_, x in V.items() if not k_.startswith("chk")}
    val["H1_compensado"] = V["H1"]["val"] + comp
    val["H1_fondo_compensado"] = V["H1_fondo"]["val"] + comp0
    val["P2P_caso"] = y_caso
    val["P2Pcom_calc"] = V["chk_P2Pcom"]["val"]     # = B_P2Pcom a 1e-6 COP (compuerta)
    val["P2P_reliq"] = p2p_rep                       # = B_P2P a 0,3 COP (compuerta)
    REF = dict(C4=ref["B_C4_COP"], C1=ref["B_C1_COP"], P2P=ref["B_P2P_COP"], P2Pcom=ref["P2Pcom_COP"],
               P2Pcom_imp=ref["P2Pcom_imp_COP"], C4_sin10=ref["C4_sin10_COP"], C4_sin10_imp=ref["C4_sin10_imp_COP"])
    for i in list(range(N)) + ["comunidad"]:
        sel = slice(None) if i == "comunidad" else slice(i, i + 1)
        f = dict(caso=c, institucion="comunidad" if i == "comunidad" else ags[i],
                 comercializador="" if i == "comunidad" else str(pc.loc[ags[i], "comercializador"]),
                 n_fronteras=N, cap_planta_kw=float(L["capk"].max() if i == "comunidad" else L["capk"][i]),
                 numeral_planta=int(num.max() if i == "comunidad" else num[i]),
                 plantas_numeral2=int(n2.sum() if i == "comunidad" else n2[i]),
                 mixto=int(mixto), caso_art20_P2Pcom=cs,
                 inyeccion_kwh=float(s[sel].sum()), importacion_kwh=float(d[sel].sum()),
                 vendido_dentro_kwh=float(v[sel].sum()), comprado_dentro_kwh=float(q[sel].sum()),
                 comprado_a_numeral2_kwh=float(q2[sel].sum()),
                 residual_iny_kwh=float(sr[sel].sum()), residual_imp_kwh=float(dr[sel].sum()),
                 H1_propio_kwh=float(TRs["propio"][sel].sum()), H1_cedido_kwh=float(TRs["cedido"][sel].sum()),
                 H1_recibido_kwh=float(TRs["recibido"][sel].sum()), H1_devuelto_kwh=float(TRs["devuelto"][sel].sum()),
                 H1_credito_kwh=float(V["H1"]["cr"][sel].sum()), H1_exceso_kwh=float(V["H1"]["ex"][sel].sum()),
                 H1_fondo_cedido_kwh=float(TR0s["cedido"][sel].sum()),
                 H1_fondo_recibido_kwh=float(TR0s["recibido"][sel].sum()),
                 H1_fondo_exceso_kwh=float(V["H1_fondo"]["ex"][sel].sum()),
                 cargo_intercambio_H1_COP=float(cargo["H1"][sel].sum()),
                 cargo_intercambio_H2_COP=float(cargo["H2"][sel].sum()),
                 cargo_intercambio_H2theta_COP=float(cargo["H2theta"][sel].sum()),
                 pagos_internos_COP=float(pag[sel].sum()),
                 compensacion_H1_COP=float(comp[sel].sum()), compensacion_H1_fondo_COP=float(comp0[sel].sum()))
        for k_, x in val.items():
            f[f"{k_}_COP"] = float(x[sel].sum())
        for k_, x in REF.items():
            f[f"B_{k_}_COP"] = float(x[sel].sum())
        for h in HIBRIDOS + ["H1_fondo_compensado"]:
            for x in CONTRA:
                b = f[f"{h}_COP"] - f[f"B_{x}_COP"]
                f[f"brecha_{h}_menos_{x}_COP"] = b
                f[f"signo_{h}_menos_{x}"] = int(CP.signo_brecha(b))
        f["brecha_H2_menos_H1_COP"] = f["H2_COP"] - f["H1_COP"]
        f["brecha_H1_menos_H1_fondo_COP"] = f["H1_COP"] - f["H1_fondo_COP"]
        # con los valores reliquidados aquí, para que el numeral sea cero exacto donde no hay plantas mixtas
        dc = descomposicion(f["P2Pcom_calc_COP"], f["P2P_reliq_COP"], f["P2Pcom_planta_COP"], f["P2P_caso_COP"])
        for k_, x in dc.items():
            f[f"dec_P2Pcom_menos_P2P_{k_}_COP"] = x
        if i == "comunidad":
            f["gini_H1"] = CP.gini(val["H1"])
            f["gini_H2"] = CP.gini(val["H2"])
            f["gini_H1_fondo"] = CP.gini(val["H1_fondo"])
            f["gini_H1_compensado"] = CP.gini(val["H1_compensado"])
            f["gini_P2Pcom"] = CP.gini(REF["P2Pcom"])
            f["gini_C4"] = CP.gini(REF["C4"])
            f["gini_C1"] = CP.gini(REF["C1"])
            f["gini_P2P"] = CP.gini(REF["P2P"])
        else:
            for k_ in SOLO_COMUNIDAD:
                f[k_] = np.nan
        filas.append(f)
    return filas, aux


# ── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    t0 = _dt.datetime.now()
    sucio_mod = git("status", "--short", "--", *MODULOS)
    exige(sucio_mod == "", f"módulos de producción con cambios sin commit:\n{sucio_mod}")
    ok("los módulos de producción que se importan están como en HEAD: " + ", ".join(MODULOS))
    print("[hibrido] 1. tarifas, capacidades, horizonte, bolsa y el punto PC")
    TT = AS.tarifas()
    cap = AS.capacidades()
    idx, _ = CP.horizonte()
    pb = CP.bolsa(idx)
    exige(pb.shape == (6144,) and bool(np.isfinite(pb).all()), "bolsa incompleta")
    PCT = pd.read_csv(AS.lee(F_PC, "e1/PC"), keep_default_na=False, na_values=[""])
    PCT["comercializador"] = PCT.comercializador.fillna("")
    exige(set(PCT.comercializador) <= {"A", "B", ""}, "comercializadores del punto PC sin anonimizar")
    print("[hibrido] 2. los 13 casos")
    filas, AUX = [], {}
    for c in CASOS:
        fc, aux = caso(c, TT, cap, pb, PCT)
        filas += fc
        AUX[c] = aux
        print(f"[hibrido]   {c}: {'mixto' if aux['mixto'] else 'sin plantas mixtas'}, {aux['n_num2']} plantas en el "
              f"numeral 2; P2P colectivo a {aux['d_p2pcom']:.2e} COP")
    T = pd.DataFrame(filas)
    # ── compuertas ──────────────────────────────────────────────────────────
    mixtos = {c for c in CASOS if AUX[c]["mixto"]}
    exige(mixtos == MIXTOS_ESPERADOS, f"casos con plantas mixtas: {sorted(mixtos)}")
    puros = [c for c in CASOS if c not in mixtos]
    num1 = [c for c in puros if AUX[c]["n_num2"] == 0]
    num2 = [c for c in puros if AUX[c]["n_num2"] > 0]
    ok(f"numeral de cada planta por su capacidad instalada (art. 25, ≤ 100 kW): plantas mixtas solo en "
       f"{', '.join(sorted(mixtos))}; todas en el numeral 1 en {', '.join(num1)}; todas en el 2 en {', '.join(num2)}")
    d = max(a["d_p2pcom"] for a in AUX.values())
    exige(d <= 1e-3, f"la función del híbrido no reproduce el P2P colectivo ({d:.2e} COP)")
    ok(f"con el intercambio exento, la deducción del caso del P2P colectivo y el PDE igual, la función del híbrido "
       f"reproduce P2Pcom_COP de p2p_comunitario_13casos.csv (e1/PC) por institución en los 13 casos (≤ {d:.1e} COP)")
    d = max(AUX[c]["d_ded_caso"] for c in puros)
    exige(d == 0.0, f"sin plantas mixtas la deducción por planta no es la del caso al bit ({d:.2e})")
    d = max(AUX[c]["d_x"] for c in puros)
    exige(d == 0.0, f"sin plantas mixtas el P2P colectivo por planta ≠ P2P colectivo ({d:.2e})")
    ok("en los once casos sin plantas mixtas la deducción por planta de origen (con la mezcla y con la traza de la "
       "fórmula, residual y bruta) es la del caso del P2P colectivo al bit, y el P2P colectivo con la deducción por "
       "planta (X) es el P2P colectivo al bit")
    d1 = max(AUX[c]["d_f_ig"] for c in puros)
    d2 = max(AUX[c]["d_f_imp"] for c in puros)
    exige(d1 <= 1e-3 and d2 <= 1e-3, f"H1 fondo ≠ C4 sin 10 % ({d1:.2e}) o por importación ({d2:.2e})")
    ok(f"en los once casos sin plantas mixtas H1 fondo con el PDE igual = C4_sin10_COP y con el PDE por importación "
       f"(pde_por_regla) = C4_sin10_imp_COP de e1/PC, por institución (≤ {max(d1, d2):.1e} COP)")
    d = max(AUX[c]["d_h2_imp"] for c in num1)
    exige(d <= 1e-3, f"H2 con PDE por importación ≠ P2Pcom_imp en el numeral 1 ({d:.2e})")
    ok(f"en los {len(num1)} casos con todas las plantas en el numeral 1 ({', '.join(num1)}) H2 con el PDE por "
       f"importación residual = P2Pcom_imp_COP de e1/PC por institución (≤ {d:.1e} COP)")
    d = max(AUX[c]["d_h2_h1"] for c in num2)
    exige(d == 0.0, f"con todas las plantas en el numeral 2, H2 ≠ H1 ({d:.2e})")
    ok(f"con todas las plantas en el numeral 2 ({', '.join(num2)}) H2 = H1 al bit (no hay intercambio del numeral 1)")
    dp = max(a["d_p2p"] for a in AUX.values())
    dy = max(AUX[c]["d_y"] for c in puros)
    exige(dp <= 2.0 and dy == 0.0, f"P2P reliquidado ({dp:.3f}) o Y = P2P ({dy:.2e})")
    ok(f"la reliquidación del mercado por miembro (art. 25, numeral de cada planta) reproduce B_P2P_COP de e1/PC por "
       f"institución (≤ {dp:.3f} COP) y, sin plantas mixtas, el mercado con la deducción del caso (Y) es el mercado al bit")
    sin_ag = {c: (AUX[c]["d_h2_p2p"], AUX[c]["agota"]) for c in NUMERAL1_SIN_AGOTAR}
    nadie = [c for c, (_, ag) in sin_ag.items() if not ag]
    dn = max([sin_ag[c][0] for c in nadie], default=0.0)
    exige(dn <= 2.0, f"H2 con la fórmula ≠ mercado P2P donde nadie agota ({dn:.3f} COP)")
    ok("H2 con la fórmula frente al mercado P2P reliquidado en los casos del numeral 1 sin agotar (CANON §14.8): "
       + "; ".join(f"{c} {'nadie agota el cupo residual del mes' if not ag else 'alguien agota algún mes'}, "
                   f"máx. por institución {dd:.3f} COP" for c, (dd, ag) in sin_ag.items())
       + f" — donde nadie agota es el mercado al peso (≤ {dn:.3f} COP)")
    dt = max(a["d_traza"] for a in AUX.values())
    exige(dt == 0.0, f"la liquidación con traza ≠ atribucion_supuestos.colectivo ({dt:.2e})")
    de = max(a["d_en"] for a in AUX.values())
    exige(de <= 1e-6, f"la energía no se conserva ({de:.2e})")
    dg = max(a["d_gen"] for a in AUX.values())
    dr_ = max(a["d_rep"] for a in AUX.values())
    exige(dr_ <= 1e-9, f"los repartos no suman el fondo ({dr_:.2e})")
    ok(f"la liquidación del fondo con traza reproduce atribucion_supuestos.colectivo al bit; energía: lo vendido es lo "
       f"comprado en cada hora, crédito + exceso = asignado y lo asignado suma el fondo de cada hora, el crédito del mes "
       f"no pasa de la importación del mes (≤ {de:.1e} kWh) y autoconsumo + vendido dentro + fondo = generación de la "
       f"comunidad en cada mes (≤ {dg:.1e} kWh por mes, el redondeo float32 del almacén), en las doce liquidaciones de los 13 casos; la fórmula reparte todo el fondo de cada "
       f"mes, lo cedido es lo recibido (≤ {dr_:.1e} relativo), nadie recibe más que su importación restante ni cede más "
       "que su sobrante; deducción en [κ·Cv, κ·Cv + Θ]; la compensación suma cero")
    num_ = T.drop(columns=["caso", "institucion", "comercializador"] + SOLO_COMUNIDAD)
    finito(num_, "tabla")
    es_com = T.institucion == "comunidad"
    finito(T.loc[es_com, SOLO_COMUNIDAD], "columnas de la comunidad")
    for c in CASOS:
        t = T[T.caso == c]
        cm = t[t.institucion == "comunidad"].iloc[0]
        ins = t[t.institucion != "comunidad"]
        for k in num_.columns:
            if k.startswith(("signo_", "n_fronteras", "cap_planta", "numeral_planta", "mixto", "caso_art20")):
                continue
            exige(abs(ins[k].sum() - cm[k]) <= 1e-6 * max(1.0, abs(cm[k])), f"{c}: comunidad ≠ suma en {k}")
    pre = "dec_P2Pcom_menos_P2P_"
    di = max(float((T[pre + "fondo_fondo_primero_COP"] + T[pre + "numeral_fondo_primero_COP"] - T[pre + "total_COP"]).abs().max()),
             float((T[pre + "fondo_numeral_primero_COP"] + T[pre + "numeral_numeral_primero_COP"] - T[pre + "total_COP"]).abs().max()),
             float((T[pre + "fondo_shapley_COP"] + T[pre + "numeral_shapley_COP"] - T[pre + "total_COP"]).abs().max()))
    exige(di <= 1e-6, f"la descomposición no cierra ({di:.2e})")
    cm = T[es_com].set_index("caso")
    exige(bool((cm.loc[puros, [pre + "numeral_fondo_primero_COP", pre + "numeral_numeral_primero_COP"]] == 0).all().all()),
          "sin plantas mixtas el término del numeral no es cero")
    ok(f"la descomposición P2Pcom − P2P = fondo + numeral cierra por los dos órdenes y por Shapley en cada fila "
       f"(≤ {di:.1e} COP) y el término del numeral es cero exacto en los once casos sin plantas mixtas; todo finito; la "
       "comunidad es la suma de sus instituciones; el Gini, solo en su fila")
    ins = T[~es_com]
    exige(len(ins) == N_PARES, f"pares: {len(ins)}")
    exige(set(T.comercializador) <= {"A", "B", ""}, "comercializador sin anonimizar")
    exige("cedenar" not in T.to_csv().lower(), "comercializador nombrado")
    # ── salida ──────────────────────────────────────────────────────────────
    SALIDA.mkdir(parents=True, exist_ok=True)
    T.to_csv(SALIDA / "hibrido_13casos.csv", index=False, encoding="utf-8", lineterminator="\n", float_format="%.6f")
    escribe_resumen(T)
    guion = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    sucio = git("status", "--short", "--untracked-files=all", "--", guion)
    leidos = list(dict.fromkeys(AS.LEIDOS + CP.LEIDOS))
    todas = ([f"(atribucion_supuestos) {x}" for x in AS.COMPUERTAS] + [f"(c2_ppa) {x}" for x in CP.COMPUERTAS]
             + COMPUERTAS)
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh_:
        fh = CP._Anonimo(fh_)
        fh.write("rutas: el nombre de cada comercializador va enmascarado como [A] o [B]; el sha256 identifica "
                 "el fichero\n")
        fh.write("hibrido_por_planta.py: H1, autogenerador colectivo de crédito mutualizado (deducción por el numeral de "
                 "la planta de origen, PDE «primero lo propio», intercambio que paga su numeral) y H2 (H1 con el "
                 "intercambio del numeral 1 exento del Cv), propuesta regulatoria\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n" + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + guion + "\n")
        fh.write("guiones importados (sha256; sin commit si no están en HEAD):\n")
        for g in IMPORTADOS:
            datos = (RAIZ / g).read_bytes()
            est = git("status", "--short", "--untracked-files=all", "--", g)
            fh.write(f"  {g}  {len(datos)}  {hashlib.sha256(datos).hexdigest()}  {est or '(como en HEAD)'}\n")
        fh.write("sin registrar en HUELLAS.csv\n")
        fh.write("no simula: lee el almacén y los libros de la matriz del 19 de septiembre y la salida del punto PC\n")
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
        fh.write(f"filas: {len(T)}\n")
        fh.write("salvedades: propuesta regulatoria, no la norma vigente; flujos del motor fijos (H1 y H2 aproximados "
                 "donde el piso del vendedor cambia; H1 fondo exacto); costo del crédito mutualizado para los demás "
                 "usuarios no medido; comercializador único y perfil horario declarado como supuestos; no se simula\n")
        fh.write("sin fecha: la hora de la corrida solo se imprime en la consola\n")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print((cm[["B_C1_COP", "B_C4_COP", "B_P2P_COP", "B_P2Pcom_COP", "H1_COP", "H2_COP", "H2theta_COP", "H1_fondo_COP",
               "H1_compensado_COP"]] / M).round(3))
    print((cm[["brecha_H1_menos_C4_COP", "brecha_H1_menos_P2P_COP", "brecha_H1_menos_P2Pcom_COP",
               "brecha_H2_menos_C4_COP", "brecha_H2_menos_P2P_COP", "brecha_H2_menos_P2Pcom_COP"]] / M).round(3))
    print((cm[[pre + k + "_COP" for k in ["total", "fondo_fondo_primero", "numeral_fondo_primero",
                                          "numeral_numeral_primero", "fondo_numeral_primero", "fondo_shapley",
                                          "numeral_shapley"]]] / M).round(3))
    print(f"[hibrido] corrida del {t0.isoformat(timespec='seconds')}, {(_dt.datetime.now() - t0).total_seconds():.0f} s")
    print(f"[hibrido] {len(leidos)} artefactos, {len(CP.INSUMOS)} insumos, {len(todas)} compuertas; salida en {SALIDA}")
    return 0


def _n(x: float, d: int = 3) -> str:
    return CP._n(x, d)


def escribe_resumen(T: pd.DataFrame) -> None:
    cm = T[T.institucion == "comunidad"].set_index("caso")
    ins = T[T.institucion != "comunidad"]
    pre = "dec_P2Pcom_menos_P2P_"
    L = ["# Híbrido H1 (crédito mutualizado por planta) y H2: la comunidad por caso", "",
         "Fuente: `hibrido_13casos.csv` de esta carpeta (guion "
         "`reformateo/documento/scripts/articulo/hibrido_por_planta.py`). Cálculo derivado, sin simular, sin registrar en "
         "el canon. Propuesta regulatoria. H1: los flujos del mercado P2P; el intercambio paga la deducción del numeral "
         "(art. 25 de la CREG 174) de la planta del vendedor; el residual va al fondo del autogenerador colectivo (art. 21 "
         "de la CREG 101 072), cada kWh deducido con el numeral de su planta de origen, repartido por mes con «primero lo "
         "propio, el sobrante a quien todavía importa». H2: H1 con el intercambio del numeral 1 exento del Cv. H2θ: además "
         "lo que vende una planta del numeral 2 paga solo Θ. H1 fondo: sin intercambio, toda la inyección al fondo. MCOP.", "",
         "## Beneficio neto de la comunidad (MCOP)", "",
         "| Caso | Plantas en el num. 2 | C1 | C4 | Mercado P2P | P2P colectivo | H1 | H2 | H2θ | H1 fondo |",
         "|---|:-:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in cm.iterrows():
        L.append(f"| {c} | {int(r.plantas_numeral2)} | " + " | ".join(_n(r[k] / M) for k in [
            "B_C1_COP", "B_C4_COP", "B_P2P_COP", "B_P2Pcom_COP", "H1_COP", "H2_COP", "H2theta_COP", "H1_fondo_COP"]) + " |")
    tot = cm[["B_C1_COP", "B_C4_COP", "B_P2P_COP", "B_P2Pcom_COP", "H1_COP", "H2_COP", "H2theta_COP", "H1_fondo_COP"]].sum()
    L.append("| **13 casos** | | " + " | ".join(_n(x / M, 2) for x in tot) + " |")
    m11 = cm[cm.mixto == 0]
    tot = m11[["B_C1_COP", "B_C4_COP", "B_P2P_COP", "B_P2Pcom_COP", "H1_COP", "H2_COP", "H2theta_COP", "H1_fondo_COP"]].sum()
    L.append("| **11 sin mixtas** | | " + " | ".join(_n(x / M, 2) for x in tot) + " |")
    L += ["", "## Brechas de la comunidad (MCOP)", "",
          "| Caso | H1 − C4 | H1 − C1 | H1 − P2P | H1 − P2Pcom | H2 − C4 | H2 − C1 | H2 − P2P | H2 − P2Pcom | H2θ − P2Pcom |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in cm.iterrows():
        L.append(f"| {c} | " + " | ".join(_n(r[f"brecha_{h}_menos_{x}_COP"] / M) for h, x in [
            ("H1", "C4"), ("H1", "C1"), ("H1", "P2P"), ("H1", "P2Pcom"), ("H2", "C4"), ("H2", "C1"), ("H2", "P2P"),
            ("H2", "P2Pcom"), ("H2theta", "P2Pcom")]) + " |")
    L += ["", "## El PDE: igual, por importación y la fórmula (MCOP)", "",
          "| Caso | H1 igual | H1 imp. | H1 fórmula | H2 igual | H2 imp. | H2 fórmula | H1 fondo igual | H1 fondo imp. | "
          "H1 fondo fórmula | H1 − H1 fondo |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in cm.iterrows():
        L.append(f"| {c} | " + " | ".join(_n(r[k] / M) for k in [
            "H1_igual_COP", "H1_imp_COP", "H1_COP", "H2_igual_COP", "H2_imp_COP", "H2_COP", "H1_fondo_igual_COP",
            "H1_fondo_imp_COP", "H1_fondo_COP", "brecha_H1_menos_H1_fondo_COP"]) + " |")
    L += ["", "## P2P colectivo − mercado P2P: el fondo y el numeral (MCOP)", "",
          "X = P2P colectivo con la deducción por planta; Y = mercado con el residual deducido con el caso del P2P "
          "colectivo. Fondo primero: fondo = X − P2P, numeral = P2Pcom − X. Numeral primero: numeral = Y − P2P, fondo = "
          "P2Pcom − Y. Shapley: la media. Sin plantas mixtas el numeral es cero exacto.", "",
          "| Caso | P2Pcom − P2P | Fondo (fondo primero) | Numeral (fondo primero) | Numeral (numeral primero) | "
          "Fondo (numeral primero) | Fondo, Shapley | Numeral, Shapley |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in cm.iterrows():
        L.append(f"| {c} | " + " | ".join(_n(r[pre + k + "_COP"] / M) for k in [
            "total", "fondo_fondo_primero", "numeral_fondo_primero", "numeral_numeral_primero", "fondo_numeral_primero",
            "fondo_shapley", "numeral_shapley"]) + " |")
    L += ["", "## Crédito cedido y compensación (H1)", "",
          "Mutualizado: kWh del sobrante residual de un miembro acreditados a otro (en C1 irían a la bolsa). Compensación "
          "declarada: quien recibe paga a quien cede la bolsa del mes ponderada por el perfil del fondo.", "",
          "| Caso | Mutualizado (kWh) | Exceso a bolsa (kWh) | Compensación pagada (MCOP) | H1 compensado − C1 | Gini H1 | "
          "Gini H1 comp. | Gini P2Pcom | Gini C4 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in cm.iterrows():
        t = ins[ins.caso == c]
        L.append(f"| {c} | {_n(r.H1_recibido_kwh, 0)} | {_n(r.H1_exceso_kwh, 0)} | "
                 f"{_n(t.compensacion_H1_COP.clip(lower=0).sum() / M)} | {_n(r.brecha_H1_compensado_menos_C1_COP / M)} | "
                 + " | ".join(_n(r[k]) for k in ["gini_H1", "gini_H1_compensado", "gini_P2Pcom", "gini_C4"]) + " |")
    L += ["", "## Pares institución-caso (64)", "",
          "Con el híbrido por encima (empate a menos de 1 COP no cuenta) y por debajo:", "",
          "| Híbrido | − C4 encima / debajo | − C1 encima / debajo | − P2P encima / debajo | − P2Pcom encima / debajo |",
          "|---|---|---|---|---|"]
    for h in HIBRIDOS + ["H1_fondo_compensado"]:
        L.append(f"| {h} | " + " | ".join(f"{int((ins[f'signo_{h}_menos_{x}'] == 1).sum())} / "
                                          f"{int((ins[f'signo_{h}_menos_{x}'] == -1).sum())}" for x in CONTRA) + " |")
    L += ["", "Salvedades: propuesta regulatoria; flujos del motor fijos (H1 y H2 aproximados donde el piso del vendedor "
          "cambia; H1 fondo exacto); el costo del crédito mutualizado para los demás usuarios no se mide; comercializador "
          "único (art. 10) y perfil horario declarado como supuestos; no se simula nada.", ""]
    (SALIDA / "resumen.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    sys.exit(main())
