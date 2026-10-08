"""
bienestar_chacon.py — La descomposición del bienestar del modelo base en el
resultado publicado del mercado P2P (Actividad 3.3), sin simular
===============================================================================
Actividad 3.3 de la propuesta: descomponer el bienestar del mercado P2P en el
beneficio monetario directo (flujos de caja) y los beneficios intangibles que
el modelo base pone en sus funciones de bienestar (satisfacción y aversión al
riesgo). Las funciones son las del documento extenso de Chacón et al., ecs. (6),
(7) y (14):

    vendedor j:   W_j = U_j(D_j*) + R_j − H_j
                  U(x) = λ·x − (θ/2)·x²,   R_j = Σ_i P_ji·π_i,
                  H_j = a_j·(Σ_i P_ji)² + b_j·Σ_i P_ji + c_j
    comprador i:  W_i = U_i(G_i^lim) + π_gb·Σ_j P_ji·ln(1/(π_i + 1))
                        − β_i·Σ_{ℓ≠i} π_ℓ·Σ_j P_jℓ

El segundo término del comprador es el que el modelo base dice que «incorpora
la aversión al riesgo» (aversión relativa de Pratt); β_i es la urgencia por la
energía, es decir, la competencia entre compradores, no una aversión al riesgo.
La traducción del proyecto de estas dos funciones es la forma «extensa» de
`core.replicator_buyers.buyer_welfare` y `core.replicator_sellers.seller_welfare`;
la compuerta 5 comprueba, hora a hora, que lo que aquí se suma término a término
es lo que esas dos funciones devuelven.

Cálculo DERIVADO del canon: no simula el mercado ni usa el servidor. Lee solo
artefactos con huella en `Documentos/canon_2026-09/HUELLAS.csv` (tamaño y
`sha256` de cada uno antes de leerlo, con `atribucion_supuestos.lee` y
`atribucion_supuestos.almacen`): las tablas `agentes`, `flujos` y `horas` del
almacén y el libro de cada uno de los 13 casos de la matriz del 19 de
septiembre, `compara_matriz_reposo.csv`, `descomposicion_13casos.csv` (e1/C5),
`c2_ppa_13casos.csv` (e1/P) y `p2p_comunitario_13casos.csv` (e1/PC).

LOS TÉRMINOS, hora a hora, sobre la forma cerrada publicada (los flujos del
almacén):

  monetario (COP). π_i es el precio que paga el comprador i en la hora: el
    precio uniforme de la hora topado por su techo (CAL-35, D51), que es la
    columna `precio` de cada flujo (compuerta 1). R_j = Σ_i P_ji·π_i y el pago
    del comprador, Σ_j P_ji·π_i. De ahí la prima del vendedor sobre su piso,
    R_j − Σ_i P_ji·piso_j, y el ahorro del comprador bajo su techo,
    Σ_j P_ji·techo_i − pago_i: su suma es el ahorro del intercambio (la banda de
    §14.8) y su cociente, la parte del vendedor del canon (compuerta 3).
  satisfacción (unidades de utilidad del modelo). U(x) con λ = 100 y θ = 0,5
    (`main_simulation.py`, `AgentParams` del modo real; los del documento
    extenso y de `JoinFinal.m`, líneas 25 y 26). x es la energía que cada
    institución consume de su propia generación: D* para el vendedor (G ≥ D) y
    G^lim para el comprador (G ≤ D), es decir, mín(G, D) en las dos, el
    autoconsumo del almacén. Se da en todas las horas y en las horas en que la
    institución entra al mercado. Es física: igual en los siete mecanismos
    (compuerta 4).
  pago logarítmico, la «aversión al riesgo» del modelo base (unidades de
    utilidad). π_gb·Σ_j P_ji·ln(1/(π_i + 1)). En el modelo base π_gb es un
    escalar, el precio al que la red compra. Aquí cada vendedor tiene su piso
    (la permuta o la bolsa, lo que la red le paga). Dos lecturas:
      (a) principal: π_gb = el piso del juego de la hora (`piso_juego` de la
          tabla `horas`, el del vendedor marginal, D63 y D68). Es el número que
          el solucionador pone en lugar de π_gb en el término de pago de la
          aptitud del comprador (`core/coupled_ode_convergence.py`, «pagos =
          −piso_barrera·ΣP/(π + 1)», la derivada de este término respecto del
          precio), en la barrera y en la cota baja del precio;
      (b) alternativa: el piso de cada vendedor, Σ_j piso_j·P_ji·ln(1/(π_i+1)):
          π_gb es lo que la red le pagaría a ESE vendedor por su energía.
  competencia (unidades de utilidad). −β·Σ_{ℓ≠i} π_ℓ·Σ_j P_jℓ, con β = 0,1
    (`etha` de `AgentParams`; `etha0` de `JoinFinal.m`, línea 27). Los
    compradores de la hora son los del juego, los que aparecen en sus flujos (`compradores` de la
    tabla `horas`, compuerta 2).
  costo de producción (COP del modelo). H_j = b_j·Σ_i P_ji, con a_j = 0 y
    c_j = 0 (CAL-32; `main_simulation.py`) y b_j de `get_b_for_real_data`
    (241,07 COP/kWh; 225 en Cesmag; la tabla de parámetros del anexo G). NO
    ENTRA EN EL SOLUCIONADOR: el despacho es por el piso creciente y b_j solo
    acota un límite de generación que no recorta.

LOS SIETE MECANISMOS. El beneficio monetario neto de cada uno es el del canon
(hoja `Resumen` y `Por_agente` para C1, C3, C4, C5 y el mercado; e1/P para C2,
el PPA de §14.22; e1/PC para el P2P colectivo, §14.23). La satisfacción es la
misma en los siete. El pago interno, R_j, el término logarítmico y el de
competencia solo existen donde hay un precio interno: el mercado y el P2P
colectivo, que liquida con los mismos flujos y precios. En C1 a C5 valen cero.

Los términos intangibles van en las unidades de utilidad del modelo y NO se
suman con el beneficio monetario. La lectura del término logarítmico como
aversión al riesgo no se sostiene (anexo G, «Los parámetros»): el precio de
cada hora es cierto, de modo que no hay lotería sobre la que aversar. Se
calcula como el modelo base lo define.

COMPUERTAS (falla en voz alta; ningún `except`; todo finito): 8 propias,
listadas en procedencia.txt.

Escribe en SALIDAS_SERVIDOR/bienestar_chacon_2026-10-07/:

    bienestar_13casos.csv     caso × institución (y comunidad): los términos
    mecanismos_13casos.csv    caso × institución (y comunidad) × mecanismo
    bienestar_horas.csv       caso × hora con mercado: la comunidad
    README.md                 qué es cada fichero y las tablas de la comunidad
    procedencia.txt           commit, versiones, huellas y compuertas, sin fecha

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/bienestar_chacon.py

Registrado en HUELLAS.csv como grupo `e1/BC` (CANON §14.34).

Actividad 3.3.
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
from core.replicator_buyers import buyer_welfare  # noqa: E402
from core.replicator_sellers import seller_welfare  # noqa: E402
from data.xm_prices import get_b_for_real_data  # noqa: E402

SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
SALIDA = SALIDAS / "bienestar_chacon_2026-10-07"
CASOS = AS.CASOS
LIBRO = "SALIDAS_SERVIDOR/matriz_reposo/{}/outputs/resultados_comparacion.xlsx"
COMPARA = "compara_matriz_reposo.csv"
F_DESC = "descomposicion_p2p_2026-09-27/descomposicion_13casos.csv"
F_PPA = "c2_ppa_2026-10-02/c2_ppa_13casos.csv"
F_PC = "p2p_comunitario_2026-10-02/p2p_comunitario_13casos.csv"
T_HORAS = 6144
M = 1e6
LAM = 100.0                 # λ, preferencia por el autoconsumo (modelo base)
THETA = 0.5                 # θ, saciedad (modelo base)
BETA = 0.1                  # β, urgencia o competencia entre compradores (modelo base)
B_ESPERADO = {241.07142857142858, 225.0}     # b_j del anexo G (COP/kWh)
MECS_ALM = ["C1", "C3", "C4", "C5", "P2P"]
MECS = ["C1", "C2ppa", "C3", "C4", "C5", "P2P", "P2Pcom"]
CON_PRECIO = ("P2P", "P2Pcom")               # los que liquidan con un precio interno
MODULOS = ["core/replicator_buyers.py", "core/replicator_sellers.py", "data/xm_prices.py"]
IMPORTADOS = ["reformateo/documento/scripts/articulo/atribucion_supuestos.py"]

COMPUERTAS: list[str] = []


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[bienestar] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    COMPUERTAS.append(msg)
    print(f"[bienestar]   OK  {msg}")


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


def finito(x, qué: str):
    exige(bool(np.isfinite(np.asarray(x, dtype=float)).all()), f"{qué}: valores no finitos")
    return x


# ── Funciones puras (las prueba tests/test_bienestar_chacon.py) ─────────────
def utilidad(x, lam: float = LAM, theta: float = THETA) -> np.ndarray:
    """U(x) = λ·x − (θ/2)·x², ec. (7) del documento extenso. x ≥ 0 (kWh)."""
    x = np.asarray(x, dtype=float)
    if not bool((x >= -1e-9).all()):
        raise ValueError("energía de autoconsumo negativa")
    return lam * x - 0.5 * theta * x * x


def pago_log(kwh, precio, pgb) -> np.ndarray:
    """π_gb·P·ln(1/(π + 1)), elemento a elemento: el segundo término de la
    ec. (14) para un flujo (o la suma de flujos de un comprador, que comparten
    precio). Exige kWh ≥ 0, precio ≥ 0 y π_gb ≥ 0."""
    k, p, g = (np.asarray(v, dtype=float) for v in (kwh, precio, pgb))
    if not (bool((k >= 0).all()) and bool((p >= 0).all()) and bool((g >= 0).all())):
        raise ValueError("kWh, precio o piso negativos")
    return g * k * np.log(1.0 / (p + 1.0))


def competencia(pagos, beta: float = BETA) -> np.ndarray:
    """−β·Σ_{ℓ≠i} π_ℓ·Σ_j P_jℓ para cada comprador de una hora, con `pagos` el
    vector (I,) de Σ_j P_jℓ·π_ℓ. Con un solo comprador vale cero."""
    p = np.asarray(pagos, dtype=float)
    if p.ndim != 1 or not bool((p >= 0).all()):
        raise ValueError("pagos de la hora inválidos")
    return -beta * (p.sum() - p)


def costo_produccion(x, b, a=0.0, c=0.0) -> np.ndarray:
    """H_j = a_j·x² + b_j·x + c_j con x = Σ_i P_ji (kWh vendidos)."""
    x = np.asarray(x, dtype=float)
    if not bool((x >= 0).all()):
        raise ValueError("energía vendida negativa")
    return a * x * x + b * x + c


# ── Un caso ─────────────────────────────────────────────────────────────────
def caso(c: str, desc: pd.DataFrame, cmp_: pd.DataFrame, ppa: pd.DataFrame, pc: pd.DataFrame):
    a = AS.almacen(c, "agentes")
    fl = AS.almacen(c, "flujos")
    hs = AS.almacen(c, "horas")
    ags = list(dict.fromkeys(a.agente))
    N = len(ags)
    ix = {x: i for i, x in enumerate(ags)}
    exige(len(a) == T_HORAS * N and len(hs) == T_HORAS, f"{c}: filas de agentes u horas")
    finito(a[["demanda", "generacion", "autoconsumo", "techo", "piso"]].to_numpy(dtype=float), f"{c} agentes")

    def piv(col):
        return a.pivot(index="agente", columns="hora", values=col).loc[ags].to_numpy(dtype=float)

    G, D, au, cu, pis = (piv(k) for k in ["generacion", "demanda", "autoconsumo", "techo", "piso"])
    T = G.shape[1]
    fl = fl.astype({k: "float64" for k in ["kwh", "precio", "valor", "techo_comprador", "piso_vendedor"]})
    finito(fl[["kwh", "precio", "valor", "techo_comprador", "piso_vendedor"]].to_numpy(), f"{c} flujos")
    hs = hs.set_index("hora").sort_index()
    exige(bool((hs.index.to_numpy() == np.arange(T)).all()), f"{c}: horas no consecutivas")
    iv = fl.vendedor.map(ix).to_numpy(dtype=int)
    ic = fl.comprador.map(ix).to_numpy(dtype=int)
    h = fl.hora.to_numpy(dtype=int)
    k = fl.kwh.to_numpy()
    p = fl.precio.to_numpy()
    te = fl.techo_comprador.to_numpy()
    pv = fl.piso_vendedor.to_numpy()

    # ── 1. el precio de cada comprador es el uniforme de la hora topado por su techo
    pu = hs.precio_uniforme.to_numpy(dtype=float)[h]
    pj = hs.piso_juego.to_numpy(dtype=float)
    finito(pu, f"{c}: precio uniforme en horas con flujos")
    d_pu = float(np.abs(p - np.minimum(pu, te)).max())
    d_val = float((np.abs(fl.valor.to_numpy() - k * p) / np.maximum(1.0, k * p)).max())   # float32 del almacén
    d_te = float(np.abs(te - cu[ic, h]).max())
    d_pv = float(np.abs(pv - pis[iv, h]).max())
    exige(d_pu <= 1e-3 and d_val <= 1e-6 and d_te <= 1e-3 and d_pv <= 1e-3 and bool((k >= 0).all()),
          f"{c}: precio ≠ mín(uniforme, techo) ({d_pu:.2e}), valor ≠ kWh·precio ({d_val:.2e}), techo o piso del "
          f"flujo distintos de los del agente ({d_te:.2e}, {d_pv:.2e}) o un flujo con energía negativa")
    g = fl.groupby(["hora", "comprador"]).precio.nunique()
    exige(int(g.max()) == 1, f"{c}: un comprador con dos precios en una hora")
    horas_m = np.unique(h)
    exige(bool(hs.resuelta.to_numpy()[horas_m].all()) and int(hs.resuelta.sum()) == len(horas_m),
          f"{c}: las horas con flujos no son las horas resueltas")
    finito(pj[horas_m], f"{c}: piso del juego en horas con mercado")

    # ── 2. compradores y vendedores de cada hora
    Q = np.zeros((N, T))        # comprado dentro
    V = np.zeros((N, T))        # vendido dentro
    PAG = np.zeros((N, T))      # pago del comprador Σ_j P_ji·π_i
    REC = np.zeros((N, T))      # R_j = Σ_i P_ji·π_i
    BASE_V = np.zeros((N, T))   # Σ_i P_ji·piso_j
    TECHO_Q = np.zeros((N, T))  # Σ_j P_ji·techo_i
    LOG_A = np.zeros((N, T))    # π_gb = piso del juego
    LOG_B = np.zeros((N, T))    # π_gb = piso de cada vendedor
    np.add.at(Q, (ic, h), k)
    np.add.at(V, (iv, h), k)
    np.add.at(PAG, (ic, h), k * p)
    np.add.at(REC, (iv, h), k * p)
    np.add.at(BASE_V, (iv, h), k * pv)
    np.add.at(TECHO_Q, (ic, h), k * te)
    np.add.at(LOG_A, (ic, h), pago_log(k, p, pj[h]))
    np.add.at(LOG_B, (ic, h), pago_log(k, p, pv))
    # el almacén guarda la matriz P entera de la hora, con sus ceros: compradores y vendedores de la hora son
    # los que aparecen en sus flujos (los del juego), reciban o no energía
    esC, esV = np.zeros((N, T), dtype=bool), np.zeros((N, T), dtype=bool)
    esC[ic, h] = True
    esV[iv, h] = True
    exige(not bool((esC & esV).any()), f"{c}: una institución compra y vende en la misma hora")
    nC = esC.sum(axis=0)
    nV = esV.sum(axis=0)
    d_n = max(float(np.abs(nC[horas_m] - hs.compradores.to_numpy(dtype=float)[horas_m]).max()),
              float(np.abs(nV[horas_m] - hs.vendedores.to_numpy(dtype=float)[horas_m]).max()))
    exige(d_n == 0.0, f"{c}: compradores o vendedores de la hora distintos de la tabla horas")
    q_alm, v_alm = piv("compra_p2p"), piv("vende_p2p")
    d_q = max(float(np.abs(Q - q_alm).max()), float(np.abs(V - v_alm).max()))
    exige(d_q <= 1e-3, f"{c}: lo comprado o vendido por flujos ≠ compra_p2p/vende_p2p ({d_q:.2e} kWh)")
    d_r = float(np.abs(REC.sum(axis=0) - PAG.sum(axis=0)).max())
    exige(d_r <= 1e-6 * max(1.0, float(PAG.sum(axis=0).max())), f"{c}: Σ R_j ≠ Σ pagos en una hora ({d_r:.2e})")
    COMP = np.zeros((N, T))
    for hh in horas_m:
        sel = np.flatnonzero(esC[:, hh])
        COMP[sel, hh] = competencia(PAG[sel, hh])
    d_c = float(np.abs(COMP.sum(axis=0) + BETA * np.maximum(nC - 1, 0) * PAG.sum(axis=0)).max())
    exige(d_c <= 1e-6 * max(1.0, float(PAG.sum(axis=0).max())),
          f"{c}: Σ competencia ≠ −β·(|I| − 1)·Σ pagos ({d_c:.2e})")
    exige(bool((LOG_A <= 0).all()) and bool((LOG_B <= 0).all()) and bool((COMP <= 0).all()),
          f"{c}: término logarítmico o de competencia positivo")

    # ── satisfacción
    d_au = float(np.abs(au - np.minimum(G, D)).max())
    exige(d_au <= 1e-3, f"{c}: autoconsumo ≠ mín(G, D) ({d_au:.2e} kWh)")
    U = utilidad(np.minimum(G, D))
    part = esC | esV
    U_m = np.where(part, U, 0.0)
    b = get_b_for_real_data(N, ags)
    exige(set(np.round(b, 9)) <= {round(x, 9) for x in B_ESPERADO}, f"{c}: b_j {b} no es el del anexo G")
    H = costo_produccion(V, b[:, None])

    # ── 3. el monetario cuadra con el canon
    prima_v = REC - BASE_V
    ahorro_c = TECHO_Q - PAG
    de = desc[desc.caso == c].set_index("agente")
    d_bv = float(np.abs(prima_v.sum(axis=1) - de.loc[ags, "banda_vendedor"].to_numpy(float)).max())
    d_bc = float(np.abs(ahorro_c.sum(axis=1) - de.loc[ags, "banda_comprador"].to_numpy(float)).max())
    exige(d_bv <= 1.0 and d_bc <= 1.0, f"{c}: prima del vendedor o ahorro del comprador ≠ banda de e1/C5 "
          f"({d_bv:.3f}, {d_bc:.3f} COP)")
    cc = cmp_[(cmp_.caso == c) & (cmp_.institucion == "comunidad")]
    exige(len(cc) == 1, f"{c}: sin fila de comunidad en {COMPARA}")
    cc = cc.iloc[0]
    parte = float(prima_v.sum() / (prima_v.sum() + ahorro_c.sum()))
    pmed = float(PAG.sum() / Q.sum())
    d_parte = abs(parte - float(cc.parte_vendedor_nueva))
    d_pmed = abs(pmed - float(cc.precio_medio_nueva))
    d_kwh = abs(float(Q.sum()) - float(cc.kwh_transada_nueva))
    exige(d_parte <= 1e-6 and d_pmed <= 1e-4 and d_kwh <= 1e-3,
          f"{c}: parte del vendedor ({d_parte:.2e}), precio medio ({d_pmed:.2e}) o energía ({d_kwh:.2e}) ≠ "
          f"{COMPARA}")

    # ── 4. la satisfacción es igual en los siete mecanismos
    libro = AS.lee(LIBRO.format(c), f"outputs/{c}")
    R = pd.read_excel(libro, sheet_name="Resumen").set_index("Escenario")
    PA = pd.read_excel(libro, sheet_name="Por_agente")
    exige(len(PA) == N, f"{c}: Por_agente con {len(PA)} filas")
    Gt, aut, qt = float(G.sum()), float(au.sum()), float(Q.sum())
    d_sc = 0.0
    for x in ["C1", "C2", "C3", "C4", "C4_mensual", "C5"]:
        d_sc = max(d_sc, abs(float(R.loc[x, "SC"]) * Gt - aut) / aut)
    for x in ["P2P", "P2P_colectivo"]:
        d_sc = max(d_sc, abs(float(R.loc[x, "SC"]) * Gt - qt - aut) / aut)
    exige(d_sc <= 1e-5, f"{c}: el autoconsumo implícito en SC de la hoja Resumen no es el del almacén ({d_sc:.2e})")

    # ── 5. la suma de los términos es lo que devuelven las funciones del proyecto
    lam = np.full(N, LAM)
    th = np.full(N, THETA)
    et = np.full(N, BETA)
    d_w = 0.0
    for hh in horas_m:
        ci = np.flatnonzero(esC[:, hh])
        vj = np.flatnonzero(esV[:, hh])
        f_ = h == hh
        P = np.zeros((len(vj), len(ci)))
        pos_v = {x: n for n, x in enumerate(vj)}
        pos_c = {x: n for n, x in enumerate(ci)}
        np.add.at(P, (np.array([pos_v[x] for x in iv[f_]]), np.array([pos_c[x] for x in ic[f_]])), k[f_])
        pr = np.zeros(len(ci))
        pr[[pos_c[x] for x in ic[f_]]] = p[f_]
        wi = buyer_welfare(pr, P, au[ci, hh], lam[ci], th[ci], et[ci], forma="extensa", pi_gb=float(pj[hh]))
        wj = seller_welfare(P, au[vj, hh], np.zeros(len(vj)), b[vj], lam[vj], th[vj], pr, forma="extensa",
                            D_auto=au[vj, hh], c_j=np.zeros(len(vj)))
        mi = float((U[ci, hh] + LOG_A[ci, hh] + COMP[ci, hh]).sum())
        mj = float((U[vj, hh] + REC[vj, hh] - H[vj, hh]).sum())
        d_w = max(d_w, abs(wi - mi) / max(1.0, abs(wi)), abs(wj - mj) / max(1.0, abs(wj)))
    exige(d_w <= 1e-9, f"{c}: los términos no suman buyer_welfare/seller_welfare (forma extensa) ({d_w:.2e})")

    # ── tablas
    filas = []
    for i in list(range(N)) + ["comunidad"]:
        sel = slice(None) if i == "comunidad" else slice(i, i + 1)
        f = dict(caso=c, institucion="comunidad" if i == "comunidad" else ags[i],
                 b_COP_kWh=float(np.nan if i == "comunidad" else b[i]),
                 horas_comprador=int(esC[sel].sum()), horas_vendedor=int(esV[sel].sum()),
                 comprado_kwh=float(Q[sel].sum()), vendido_kwh=float(V[sel].sum()),
                 pago_COP=float(PAG[sel].sum()), R_COP=float(REC[sel].sum()),
                 prima_vendedor_COP=float(prima_v[sel].sum()), ahorro_comprador_COP=float(ahorro_c[sel].sum()),
                 autoconsumo_kwh=float(au[sel].sum()), autoconsumo_mercado_kwh=float(np.where(part, au, 0.0)[sel].sum()),
                 U=float(U[sel].sum()), U_horas_mercado=float(U_m[sel].sum()),
                 U_comprador=float(np.where(esC, U, 0.0)[sel].sum()), U_vendedor=float(np.where(esV, U, 0.0)[sel].sum()),
                 log_piso_juego=float(LOG_A[sel].sum()), log_piso_vendedor=float(LOG_B[sel].sum()),
                 competencia=float(COMP[sel].sum()), H_COP=float(H[sel].sum()))
        f["ahorro_intercambio_COP"] = f["prima_vendedor_COP"] + f["ahorro_comprador_COP"]
        f["W_comprador"] = f["U_comprador"] + f["log_piso_juego"] + f["competencia"]
        f["W_vendedor"] = f["U_vendedor"] + f["R_COP"] - f["H_COP"]
        filas.append(f)
    cm = filas[-1]
    cm["parte_vendedor"] = parte
    cm["precio_medio_COP_kWh"] = pmed
    cm["piso_juego_medio_COP_kWh"] = float((pj[h] * k).sum() / k.sum())
    for kk in ["log_piso_juego", "log_piso_vendedor", "competencia", "R_COP", "H_COP", "ahorro_intercambio_COP"]:
        cm[kk + "_por_kwh"] = cm[kk] / cm["comprado_kwh"]
    cm["U_por_kwh_autoconsumo"] = cm["U"] / cm["autoconsumo_kwh"]
    cm["horas_mercado"] = int(len(horas_m))
    for f in filas[:-1]:
        for kk in ["parte_vendedor", "precio_medio_COP_kWh", "piso_juego_medio_COP_kWh", "log_piso_juego_por_kwh",
                   "log_piso_vendedor_por_kwh", "competencia_por_kwh", "R_COP_por_kwh", "H_COP_por_kwh",
                   "ahorro_intercambio_COP_por_kwh", "U_por_kwh_autoconsumo", "horas_mercado"]:
            f[kk] = np.nan
    # los siete mecanismos
    ppc = ppa[ppa.caso == c].set_index("institucion")
    pcc = pc[pc.caso == c].set_index("institucion")
    exige(list(ppc.index) == ags + ["comunidad"] and list(pcc.index) == ags + ["comunidad"],
          f"{c}: instituciones de e1/P o e1/PC")
    filas_m = []
    for i in list(range(N)) + ["comunidad"]:
        fi = filas[-1] if i == "comunidad" else filas[i]
        for x in MECS:
            if x in MECS_ALM:
                ben = float(R.loc[x, "Ganancia_neta_COP"]) if i == "comunidad" else float(PA[x].iloc[i])
            elif x == "C2ppa":
                ben = float(ppc.loc["comunidad" if i == "comunidad" else ags[i], "B_C2_media_COP"])
            else:
                ben = float(pcc.loc["comunidad" if i == "comunidad" else ags[i], "P2Pcom_COP"])
            con = x in CON_PRECIO
            filas_m.append(dict(caso=c, institucion=fi["institucion"], mecanismo=x, beneficio_COP=ben,
                                pago_interno_COP=fi["pago_COP"] if con else 0.0, R_COP=fi["R_COP"] if con else 0.0,
                                U=fi["U"], log_piso_juego=fi["log_piso_juego"] if con else 0.0,
                                log_piso_vendedor=fi["log_piso_vendedor"] if con else 0.0,
                                competencia=fi["competencia"] if con else 0.0))
    # comunidad hora a hora
    fh = pd.DataFrame(dict(caso=c, hora=horas_m, regimen=hs.regimen_cerrado.to_numpy()[horas_m],
                           compradores=nC[horas_m], vendedores=nV[horas_m], kwh=Q[:, horas_m].sum(axis=0),
                           pago_COP=PAG[:, horas_m].sum(axis=0), piso_juego=pj[horas_m],
                           U_mercado=U_m[:, horas_m].sum(axis=0), log_piso_juego=LOG_A[:, horas_m].sum(axis=0),
                           log_piso_vendedor=LOG_B[:, horas_m].sum(axis=0), competencia=COMP[:, horas_m].sum(axis=0),
                           H_COP=H[:, horas_m].sum(axis=0)))
    info = dict(d_pu=d_pu, d_val=d_val, d_te=d_te, d_pv=d_pv, d_q=d_q, d_r=d_r, d_c=d_c, d_au=d_au, d_bv=d_bv,
                d_bc=d_bc, d_parte=d_parte, d_pmed=d_pmed, d_kwh=d_kwh, d_sc=d_sc, d_w=d_w, n_horas=len(horas_m))
    return filas, filas_m, fh, info


# ── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    t0 = _dt.datetime.now()
    sucio_mod = git("status", "--short", "--", *MODULOS)
    exige(sucio_mod == "", f"módulos de producción con cambios sin commit:\n{sucio_mod}")
    ok("los módulos de producción que se importan están como en HEAD: " + ", ".join(MODULOS))
    print("[bienestar] 1. artefactos del canon")
    desc = pd.read_csv(AS.lee(F_DESC, "e1/C5"))
    cmp_ = pd.read_csv(AS.lee(COMPARA, "comparacion"), skiprows=1)
    ppa = pd.read_csv(AS.lee(F_PPA, "e1/P"), keep_default_na=False, na_values=[""])
    pc = pd.read_csv(AS.lee(F_PC, "e1/PC"), keep_default_na=False, na_values=[""])
    print("[bienestar] 2. los 13 casos")
    FI, FM, FH, INFO = [], [], [], {}
    for c in CASOS:
        filas, fm, fh, info = caso(c, desc, cmp_, ppa, pc)
        FI += filas
        FM += fm
        FH.append(fh)
        INFO[c] = info
        cm = filas[-1]
        print(f"[bienestar]   {c}: {info['n_horas']} horas con mercado, {cm['comprado_kwh']:,.1f} kWh; pago "
              f"{cm['pago_COP'] / M:.3f} MCOP; log/kWh {cm['log_piso_juego_por_kwh']:,.1f}; competencia/kWh "
              f"{cm['competencia_por_kwh']:,.2f}; U {cm['U'] / M:.3f} M")
    Bi, Mm, Hh = pd.DataFrame(FI), pd.DataFrame(FM), pd.concat(FH, ignore_index=True)
    mx = {k: max(i[k] for i in INFO.values()) for k in next(iter(INFO.values())) if k != "n_horas"}
    ok(f"precio: en cada flujo el precio es el uniforme de la hora topado por el techo del comprador (≤ "
       f"{mx['d_pu']:.1e} COP/kWh), el valor es kWh·precio (≤ {mx['d_val']:.1e} relativo, el float32 del almacén), techo y piso son los del "
       f"agente (≤ {max(mx['d_te'], mx['d_pv']):.1e}), un solo precio por comprador y hora, y las horas con flujos "
       "son las resueltas, todas con piso del juego finito, en los 13 casos")
    ok(f"compradores y vendedores: los de cada hora son los de la tabla horas; lo comprado y vendido por flujos es "
       f"compra_p2p y vende_p2p (≤ {mx['d_q']:.1e} kWh); nadie compra y vende en la misma hora; Σ R_j = Σ pagos en "
       f"cada hora (≤ {mx['d_r']:.1e} COP)")
    ok(f"monetario: la prima del vendedor (R_j − Σ P_ji·piso_j) y el ahorro del comprador (Σ P_ji·techo_i − pago) son "
       f"banda_vendedor y banda_comprador de descomposicion_13casos.csv (e1/C5) por institución (≤ "
       f"{max(mx['d_bv'], mx['d_bc']):.3f} COP); la parte del vendedor (≤ {mx['d_parte']:.1e}), el precio medio "
       f"(≤ {mx['d_pmed']:.1e} COP/kWh) y la energía (≤ {mx['d_kwh']:.1e} kWh) de la comunidad son los de "
       f"compara_matriz_reposo.csv, en los 13 casos")
    ok(f"satisfacción: el autoconsumo es mín(G, D) en cada hora (≤ {mx['d_au']:.1e} kWh) y el que implica SC de la "
       f"hoja Resumen es el mismo en C1, C2, C3, C4, C4_mensual, C5, P2P y P2P_colectivo (≤ {mx['d_sc']:.1e} "
       "relativo; en los dos últimos, SC·ΣG − transado): la satisfacción U es igual en todos los mecanismos")
    ok(f"fidelidad: en cada hora con mercado, U + término logarítmico (piso del juego) + competencia de los "
       f"compradores es buyer_welfare(forma='extensa') y U + R − H de los vendedores es seller_welfare("
       f"forma='extensa'), ≤ {mx['d_w']:.1e} relativo, en los 13 casos")
    ok(f"competencia: Σ_i −β·Σ_(ℓ≠i) pago_ℓ = −β·(|I| − 1)·Σ pagos en cada hora (≤ {mx['d_c']:.1e}); el término "
       "logarítmico (las dos lecturas) y el de competencia nunca son positivos; b_j es el del anexo G (241,07 y 225)")
    # la comunidad es la suma; todo finito; los mecanismos
    solo_cm = ["parte_vendedor", "precio_medio_COP_kWh", "piso_juego_medio_COP_kWh", "log_piso_juego_por_kwh",
               "log_piso_vendedor_por_kwh", "competencia_por_kwh", "R_COP_por_kwh", "H_COP_por_kwh",
               "ahorro_intercambio_COP_por_kwh", "U_por_kwh_autoconsumo", "horas_mercado"]
    num = [x for x in Bi.columns if x not in ["caso", "institucion", "b_COP_kWh"] + solo_cm]
    D70: list[float] = []
    for c in CASOS:
        t = Bi[Bi.caso == c]
        cm, ins = t[t.institucion == "comunidad"].iloc[0], t[t.institucion != "comunidad"]
        for kk in ["comprado_kwh", "vendido_kwh", "pago_COP", "R_COP", "prima_vendedor_COP", "ahorro_comprador_COP",
                   "U", "U_horas_mercado", "log_piso_juego", "log_piso_vendedor", "competencia", "H_COP",
                   "W_comprador", "W_vendedor"]:
            exige(abs(float(ins[kk].sum()) - float(cm[kk])) <= 1e-6 * max(1.0, abs(float(cm[kk]))),
                  f"{c}: comunidad ≠ suma en {kk}")
        exige(abs(float(cm.pago_COP) - float(cm.R_COP)) <= 1e-6 * float(cm.pago_COP), f"{c}: Σ R ≠ Σ pagos")
        exige(abs(float(cm.comprado_kwh) - float(cm.vendido_kwh)) <= 1e-6, f"{c}: comprado ≠ vendido")
        hc = Hh[Hh.caso == c]
        for kk, col in [("pago_COP", "pago_COP"), ("log_piso_juego", "log_piso_juego"), ("competencia", "competencia"),
                        ("U_horas_mercado", "U_mercado"), ("comprado_kwh", "kwh")]:
            exige(abs(float(hc[col].sum()) - float(cm[kk])) <= 1e-6 * max(1.0, abs(float(cm[kk]))),
                  f"{c}: la tabla horaria no suma {kk}")
        mc = Mm[(Mm.caso == c) & (Mm.institucion == "comunidad")].set_index("mecanismo")
        exige(float(mc.U.max() - mc.U.min()) == 0.0, f"{c}: U distinta entre mecanismos")
        exige(bool((mc.loc[["C1", "C2ppa", "C3", "C4", "C5"], ["pago_interno_COP", "R_COP", "log_piso_juego",
                                                               "log_piso_vendedor", "competencia"]] == 0).all().all()),
              f"{c}: término interno distinto de cero fuera del mercado")
        if c in AS.SIN_AGOTAR:          # §14.8 (H-70): sin cupo agotado, P2P − C1 es la banda repartida
            d70 = abs(float(mc.loc["P2P", "beneficio_COP"]) - float(mc.loc["C1", "beneficio_COP"])
                      - float(cm.ahorro_intercambio_COP))
            D70.append(d70)
            exige(d70 <= 2.0, f"{c}: P2P − C1 ≠ ahorro del intercambio ({d70:.3f} COP)")
    es_cm = (Bi.institucion == "comunidad").to_numpy()
    finito(Bi[num].to_numpy(dtype=float), "bienestar")
    finito(Bi.loc[es_cm, solo_cm].to_numpy(dtype=float), "bienestar, comunidad")
    finito(Bi.loc[~es_cm, "b_COP_kWh"].to_numpy(dtype=float), "bienestar, b_j")
    exige(bool(Bi.loc[~es_cm, solo_cm].isna().all().all()) and bool(Bi.loc[es_cm, "b_COP_kWh"].isna().all()),
          "columnas de la comunidad llenas en una institución, o b_j en la comunidad")
    finito(Mm.drop(columns=["caso", "institucion", "mecanismo"]).to_numpy(dtype=float), "mecanismos")
    finito(Hh.drop(columns=["caso", "regimen"]).to_numpy(dtype=float), "horas")
    n_ins = int((Bi.institucion != "comunidad").sum())
    exige(len(Bi) == n_ins + 13 and len(Mm) == len(Bi) * len(MECS), "filas de las tablas")
    exige(not any("cedenar" in x.to_csv().lower() for x in (Bi, Mm, Hh)), "comercializador nombrado")
    ok(f"la comunidad es la suma de sus instituciones y la tabla horaria suma la comunidad; U es la misma en los siete "
       f"mecanismos y el pago interno, R, el término logarítmico y el de competencia valen cero en C1, C2, C3, C4 y "
       f"C5; en {', '.join(AS.SIN_AGOTAR)} (nadie agota el cupo, §14.8) el beneficio del mercado menos el de C1 es el "
       f"ahorro del intercambio (≤ {max(D70):.3f} COP); todo finito; {len(Bi)} filas por institución ({n_ins} pares "
       f"institución-caso), {len(Mm)} de mecanismos, {len(Hh)} horas")
    SALIDA.mkdir(parents=True, exist_ok=True)
    kw = dict(index=False, encoding="utf-8", lineterminator="\n", float_format="%.6f")
    Bi.to_csv(SALIDA / "bienestar_13casos.csv", **kw)
    Mm.to_csv(SALIDA / "mecanismos_13casos.csv", **kw)
    Hh.to_csv(SALIDA / "bienestar_horas.csv", **kw)
    escribe_readme(Bi, Mm)
    guion = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    sucio = git("status", "--short", "--untracked-files=all", "--", guion)
    leidos = list(AS.LEIDOS)
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("bienestar_chacon.py: la descomposición del bienestar del modelo base (ecs. 6, 7 y 14 del documento "
                 "extenso) en el resultado publicado del mercado P2P, derivada sin simular\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n" + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + guion + "\n")
        fh.write("guiones importados (sha256; sin commit si no están en HEAD):\n")
        for g in IMPORTADOS + MODULOS:
            datos = (RAIZ / g).read_bytes()
            est = git("status", "--short", "--untracked-files=all", "--", g)
            fh.write(f"  {g}  {len(datos)}  {hashlib.sha256(datos).hexdigest()}  {est or '(como en HEAD)'}\n")
        fh.write("registrado en HUELLAS.csv como grupo e1/BC (CANON §14.34)\n")
        fh.write("no simula: lee las tablas agentes, flujos y horas de los almacenes y los libros de la matriz del 19 "
                 "de septiembre, compara_matriz_reposo.csv y las salidas de los puntos C5, P y PC\n")
        fh.write(f"parámetros del modelo base: lambda = {LAM}, theta = {THETA}, beta = {BETA}, a_j = 0, c_j = 0, b_j de "
                 "get_b_for_real_data (241,071429 y 225); pi_gb, lectura (a) el piso del juego de la hora y (b) el "
                 "piso de cada vendedor\n")
        fh.write(f"huellas: {AS.HUELLAS.relative_to(RAIZ).as_posix()}; {len(leidos)} artefactos leídos, todos con la "
                 "huella comprobada:\n")
        for g, r in leidos:
            fh.write(f"  {g}  {r}\n")
        fh.write(f"compuertas: {len(COMPUERTAS)}, todas OK:\n")
        for cpt in COMPUERTAS:
            fh.write(f"  OK  {cpt}\n")
        fh.write(f"filas: bienestar {len(Bi)}, mecanismos {len(Mm)}, horas {len(Hh)}\n")
        fh.write("salvedades: los términos intangibles van en unidades de utilidad del modelo y no se suman con el "
                 "beneficio monetario; la lectura del término logarítmico como aversión al riesgo no se sostiene "
                 "(el precio de cada hora es cierto); H_j no entra en el solucionador; no se simula nada\n")
        fh.write("sin fecha: la hora de la corrida solo se imprime en la consola\n")
    print(f"[bienestar] corrida del {t0.isoformat(timespec='seconds')}, {(_dt.datetime.now() - t0).total_seconds():.0f} s")
    print(f"[bienestar] {len(leidos)} artefactos, {len(COMPUERTAS)} compuertas; salida en {SALIDA}")
    return 0


def _n(x: float, d: int = 2) -> str:
    """Número a la española: coma decimal, espacio de miles y signo «−»."""
    if not np.isfinite(x):
        return "·"
    if round(float(x), d) == 0.0:
        x = 0.0
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",").replace("-", "−")


def escribe_readme(Bi: pd.DataFrame, Mm: pd.DataFrame) -> None:
    C = Bi[Bi.institucion == "comunidad"].set_index("caso")
    L = ["# La descomposición del bienestar del modelo base (Actividad 3.3)", "",
         "Guion: `reformateo/documento/scripts/articulo/bienestar_chacon.py` (CANON §14.34, grupo `e1/BC` de "
         "`HUELLAS.csv`). Cálculo derivado del canon, sin simular: evalúa los términos de las funciones de bienestar "
         "del documento extenso del modelo base (ecs. 6, 7 y 14) sobre los flujos y precios publicados del mercado "
         "P2P, hora a hora, en los 13 casos.", "",
         "## Ficheros", "",
         "- `bienestar_13casos.csv`: caso × institución (y comunidad). Monetario (COP): pago del comprador, R del "
         "vendedor, prima del vendedor sobre su piso, ahorro del comprador bajo su techo y su suma, el ahorro del "
         "intercambio. Intangibles (unidades de utilidad): U en todas las horas y en las horas de mercado, el término "
         "logarítmico con las dos lecturas de π_gb y el de competencia. H, el costo de producción del modelo (COP, "
         "no entra en el solucionador). W_comprador = U + logarítmico (piso del juego) + competencia y W_vendedor = "
         "U + R − H, en las horas en que la institución entra al mercado. En la fila de la comunidad, además, los "
         "valores por kWh transado, la parte del vendedor y el precio medio.",
         "- `mecanismos_13casos.csv`: caso × institución (y comunidad) × mecanismo (C1, C2ppa, C3, C4, C5, P2P y "
         "P2Pcom): el beneficio monetario del canon, el pago interno, R, U y los dos términos que solo tiene el "
         "precio interno.",
         "- `bienestar_horas.csv`: caso × hora con mercado, la comunidad.",
         "- `procedencia.txt`: commit, versiones, huellas leídas y compuertas.", "",
         "## Las definiciones", "",
         "- π_i es el precio que paga el comprador: el uniforme de la hora topado por su techo (columna `precio` de "
         "los flujos).",
         "- U(x) = λ·x − (θ/2)·x², λ = 100, θ = 0,5, con x = mín(G, D) (el autoconsumo).",
         "- Logarítmico: π_gb·Σ_j P_ji·ln(1/(π_i + 1)). Lectura (a), π_gb = el piso del juego de la hora (el del "
         "vendedor marginal, el que el solucionador usa en la aptitud del comprador). Lectura (b), el piso de cada "
         "vendedor.",
         "- Competencia: −β·Σ_(ℓ≠i) π_ℓ·Σ_j P_jℓ, β = 0,1, entre los compradores del juego de la hora (los que aparecen en sus flujos, reciban o no energía).",
         "- H_j = b_j·Σ_i P_ji, con a_j = c_j = 0 y b_j = 241,07 COP/kWh (225 en Cesmag).", "",
         "## 1. La comunidad por caso", "",
         "| Caso | Transado (kWh) | Pago = R (MCOP) | Ahorro del intercambio (MCOP) | Parte del vendedor | U (millones) | "
         "Logarítmico (a) (millones) | (b) | Competencia (millones) | H (MCOP) |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c in CASOS:
        r = C.loc[c]
        L.append(f"| {c} | {_n(r.comprado_kwh, 1)} | {_n(r.pago_COP / M, 3)} | {_n(r.ahorro_intercambio_COP / M, 3)} | "
                 f"{_n(r.parte_vendedor, 3)} | {_n(r.U / M, 3)} | {_n(r.log_piso_juego / M, 3)} | "
                 f"{_n(r.log_piso_vendedor / M, 3)} | {_n(r.competencia / M, 3)} | {_n(r.H_COP / M, 3)} |")
    L += ["", "## 2. Por kWh transado (la comunidad)", "",
          "| Caso | Precio medio (COP/kWh) | Piso del juego medio | Logarítmico (a) por kWh | (b) por kWh | "
          "Competencia por kWh | U por kWh de autoconsumo |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for c in CASOS:
        r = C.loc[c]
        L.append(f"| {c} | {_n(r.precio_medio_COP_kWh, 2)} | {_n(r.piso_juego_medio_COP_kWh, 2)} | "
                 f"{_n(r.log_piso_juego_por_kwh, 1)} | {_n(r.log_piso_vendedor_por_kwh, 1)} | "
                 f"{_n(r.competencia_por_kwh, 2)} | {_n(r.U_por_kwh_autoconsumo, 2)} |")
    L += ["", "## Salvedades", "",
          "- Los términos intangibles van en las unidades de utilidad del modelo y no se suman con el beneficio "
          "monetario.",
          "- U es la misma en los siete mecanismos: es física. El término logarítmico y el de competencia solo "
          "existen donde hay un precio interno (el mercado y el P2P colectivo); en C1 a C5 valen cero por "
          "definición, no por medición.",
          "- La lectura del término logarítmico como aversión al riesgo no se sostiene: el precio de cada hora es "
          "cierto. Se calcula como el modelo base lo define.",
          "- H no entra en el solucionador: el despacho es por el piso creciente.", ""]
    (SALIDA / "README.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    sys.exit(main())
