"""
intangibles_autoconsumo.py — Beneficio monetario frente a intangible
(Actividad 3.3) y el incentivo a consumir en el sitio, sin simular
===============================================================================
Actividad 3.3 de la propuesta (descomponer el bienestar del mercado P2P en el
beneficio monetario directo y los intangibles: satisfacción, equidad y
aversión al riesgo) y la pregunta de la propuesta de si el mercado incentiva
más consumo en el sitio que el reparto administrativo. Cálculo DERIVADO del
canon: no simula el mercado ni usa el servidor. Lee artefactos con huella en
`Documentos/canon_2026-09/HUELLAS.csv` (tamaño y `sha256` de cada uno antes de
leerlo, con `atribucion_supuestos.lee` y `c2_ppa.lee`) e importa, sin
copiarlas, las funciones de los puntos S (`atribucion_supuestos.py`), P
(`c2_ppa.py`) y PC (`p2p_comunitario.py`).

LOS SIETE MECANISMOS: C1, C2 (el PPA de la propuesta, §14.22, a la media de
la serie de XM), C3, C4, C5, el mercado P2P y el P2P colectivo (§14.23). Los
de la tabla `escenarios` del almacén (C1, C3, C4, C5 y P2P) se suman por mes;
C2 se recalcula mes a mes como A + PP·S (lineal en PP) y el P2P colectivo con
la liquidación de `p2p_comunitario.py`. No entran la columna `C2` del almacén
(el contrato interno de CAL-52), `C4_mensual` (alias de C4) ni
`P2P_colectivo` del almacén (la vía legal de hoy, v(0,0) de §14.21).

1. SATISFACCIÓN. La demanda de cada institución en cada hora es una sola
   (tabla `agentes`), la misma en los siete: el mercado solo cambia de dónde
   viene la energía que falta (compra dentro o a la red), no cuánta se
   consume. Compuertas: D = autoconsumo + compra dentro + compra a la red y
   faltante = compra dentro + compra a la red en cada hora; las columnas SC y
   SS de la hoja `Resumen` son iguales en C1 a C5 y valen Σ autoconsumo / ΣG
   y Σ autoconsumo / ΣD; las del mercado, (autoconsumo + transado) / ΣG y / ΣD.
   La utilidad de consumo del modelo base, U_i(D_i) = λ_i·D_i − θ_i·D_i²
   (`Documentos/copy/Bienestar6p.py`, `Welfarei`, línea 50; λ = 100 y θ = 0,5
   en `main_simulation.py`, `AgentParams`) y la del programa de respuesta de
   la demanda, U_k = ln(1 + Σ_n D_k^n) (`core/dr_program.py`), dependen solo de
   D, de modo que su diferencia entre mecanismos es cero por construcción.

2. AVERSIÓN AL RIESGO. Por caso, institución y mecanismo, el costo neto de la
   energía de cada mes, C_m = F_m − B_m (F_m, la factura del mes sin generación,
   Σ_h D·CU; B_m, el beneficio del mecanismo en el mes), normalizado a un mes
   de 30 días (C_m · 30 / días del mes en el horizonte: abril empieza el 4 y
   diciembre termina el 15). Sobre los nueve meses: media, desviación típica
   muestral (ddof = 1) y coeficiente de variación. La prima de riesgo es un
   SUPUESTO de esta medición:
     principal, media-CVaR (Guerrero et al. [26] de la revisión de la Act. 1.2,
       §4): cada mes el agente paga E[C] + β·(CVaR_0,95(C) − E[C]); con C
       normal, CVaR_0,95 − E = κ·σ, κ = φ(z_0,95) / 0,05 = 2,0627; en el
       horizonte, π = n·β·κ·σ, con n = 256 / 30 meses de 30 días, y
       β ∈ {0,05; 0,10; 0,20}: los extremos del rango de [26] (Tabla 1.4) y
       el valor adoptado η = 0,1, que la Tabla 1.4 interpreta como aversión
       moderada;
     contraste, media-varianza: π = n·½·ρ·σ², con ρ = γ / F̄ (γ el mismo β,
       F̄ la factura media normalizada del mes de la institución), es decir,
       aversión relativa constante sobre la escala de la factura.
   La comunidad suma las primas de sus instituciones (cada una carga su
   riesgo); la prima conjunta, con la σ del costo de la comunidad, se da al
   lado. La brecha ajustada es (B_X − π_X) − (B_Y − π_Y).

3. EQUIDAD. Ya medida (CANON §14.6: Gini y precio de la justicia): solo se
   enlaza.

4. INCENTIVO A CONSUMIR EN EL SITIO (estimación posterior por elasticidad,
   NO una simulación de respuesta de la demanda, que está apagada: «sin DR»).
   En cada flujo del mercado el comprador paga p = mín(precio, techo) (CAL-35)
   en lugar de su tarifa CU = techo: rebaja relativa r = (CU − p) / CU.
     precio medio (la estimación del encargo): ΔD_ih = |ε|·Σ_flujos r·kWh;
       equivale a aplicar la elasticidad a toda la demanda de la hora con la
       rebaja del precio medio que paga;
     precio marginal (variante): solo donde la compra dentro cubre todo el
       faltante de la hora (el kWh adicional se compraría dentro, al precio
       interno): ΔD_ih = |ε|·r̄_ih·D_ih, con el tope del residual de la
       comunidad en la hora (Σ máx(s − v, 0)), repartido a prorrata si no
       alcanza. No es una cota del primero: cuenta menos horas, pero aplica
       la rebaja a toda la demanda de la hora.
   ε ∈ {−0,197; −0,37; −0,468} (revisión de la Act. 1.2, §2: Zabaloy y Viego
   [19], −0,197 a −0,468; Marques et al. [20], −0,37; la Tabla 1.2 no adopta
   ninguno, y −0,37 se toma como central). La autosuficiencia de la comunidad
   es (autoconsumo + transado) / D (la del mercado en `Resumen`); con el
   consumo inducido, dos cotas: cubierto por la red, (au + q)/(D + ΔD), o por
   el residual de la comunidad en la hora, (au + q + mín(ΔD_h, sr_h))/(D + ΔD).
   En C1, C2, C3 y C4 el comprador paga su tarifa por cada kWh que importa:
   ningún precio horario distinto, efecto cero. El P2P colectivo usa los
   mismos flujos y precios del mercado: el mismo efecto. C5 no se estima.

COMPUERTAS (falla en voz alta; ningún `except`; todo finito): las de los
puntos S y P que se ejecutan (tarifas, horizonte, bolsa y contratos) y 7
propias, listadas en procedencia.txt.

Escribe en SALIDAS_SERVIDOR/intangibles_autoconsumo_2026-10-06/:

    riesgo_13casos.csv        caso × institución (y comunidad) × mecanismo
    brechas_riesgo_13casos.csv caso × institución (y comunidad) × comparación
    costo_mensual.csv         caso × institución × mecanismo × mes
    autoconsumo_13casos.csv   caso × institución (y comunidad)
    satisfaccion_13casos.csv  caso: la demanda única y SC y SS de Resumen
    README.md                 qué es cada fichero y las tablas de la comunidad
    procedencia.txt           commit, versiones, huellas y compuertas, sin fecha

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/intangibles_autoconsumo.py

Registrado en HUELLAS.csv como grupo `e1/IA` (CANON §14.31).

Actividad 3.3.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import math
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
import p2p_comunitario as PCm  # noqa: E402

SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
SALIDA = SALIDAS / "intangibles_autoconsumo_2026-10-06"
CASOS = AS.CASOS
LIBRO = "SALIDAS_SERVIDOR/matriz_reposo/{}/outputs/resultados_comparacion.xlsx"
M = 1e6
T_HORAS = 6144
DIAS_BASE = 30.0
N_EQ = T_HORAS / 24.0 / DIAS_BASE            # 8,5333 meses de 30 días en el horizonte
ALFA = 0.95                                  # nivel del CVaR
BETAS = {"005": 0.05, "010": 0.10, "020": 0.20}     # [26]: 0,05-0,20; η adoptado 0,1 (Tabla 1.4)
BETA_ADOPTADO = "010"
EPS = {"0197": -0.197, "037": -0.37, "0468": -0.468}  # [19] −0,197 a −0,468; [20] −0,37
EPS_CENTRAL = "037"
MECS_ALM = ["C1", "C3", "C4", "C5", "P2P"]   # de la tabla escenarios del almacén
MECS = ["C1", "C2ppa", "C3", "C4", "C5", "P2P", "P2Pcom"]
COMPARA = [("P2P", "C1"), ("P2P", "C4"), ("P2P", "C2ppa"), ("P2P", "C3"), ("P2P", "C5"),
           ("P2Pcom", "C4"), ("P2Pcom", "C1"), ("P2Pcom", "P2P")]
EMPATE = 1.0                                 # COP: la convención de los signos del canon
N_PARES = 64
F_DESC = "descomposicion_p2p_2026-09-27/descomposicion_13casos.csv"
F_ATR = "atribucion_supuestos_2026-09-30/atribucion_13casos.csv"
F_PPA = "c2_ppa_2026-10-02/c2_ppa_13casos.csv"
F_PC = "p2p_comunitario_2026-10-02/p2p_comunitario_13casos.csv"
MODULOS = ["core/opciones_externas.py", "core/settlement.py", "data/cedenar_tariff.py", "data/xm_prices.py",
           "data/precios_contratos.py", "scenarios/scenario_c4_creg101072.py", "scenarios/_pi_gs.py"]
IMPORTADOS = ["reformateo/documento/scripts/articulo/atribucion_supuestos.py",
              "reformateo/documento/scripts/articulo/c2_ppa.py",
              "reformateo/documento/scripts/articulo/p2p_comunitario.py"]

COMPUERTAS: list[str] = []


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[intangibles] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    COMPUERTAS.append(msg)
    print(f"[intangibles]   OK  {msg}")


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


def finito(x, qué: str):
    exige(bool(np.isfinite(np.asarray(x, dtype=float)).all()), f"{qué}: valores no finitos")
    return x


# ── Funciones puras (las prueba tests/test_intangibles_autoconsumo.py) ──────
def kappa_cvar(alfa: float = ALFA) -> float:
    """(CVaR_α − media) / σ de una normal: φ(z_α) / (1 − α)."""
    if not 0.0 < alfa < 1.0:
        raise ValueError(f"alfa {alfa}")
    # z_α por bisección sobre la función de distribución normal (math.erf)
    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if 0.5 * (1.0 + math.erf(mid / math.sqrt(2.0))) < alfa:
            lo = mid
        else:
            hi = mid
    z = 0.5 * (lo + hi)
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi) / (1.0 - alfa)


KAPPA = kappa_cvar(ALFA)


def normaliza_mes(x_mes, dias_mes, base: float = DIAS_BASE) -> np.ndarray:
    """Lleva cada mes a `base` días: x · base / días. `x_mes` (..., K)."""
    x = np.asarray(x_mes, dtype=float)
    d = np.asarray(dias_mes, dtype=float)
    if d.shape != x.shape[-1:] or not bool((d > 0).all()):
        raise ValueError(f"días {d}")
    return x * base / d


def dispersion(x) -> tuple[float, float, float]:
    """(media, desviación típica muestral, CV) de una serie; CV = NaN si la
    media no es positiva (no se rellena: el coeficiente no está definido)."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 1 or x.size < 2 or not bool(np.isfinite(x).all()):
        raise ValueError(f"serie inválida {x}")
    mu, sd = float(x.mean()), float(x.std(ddof=1))
    return mu, sd, (sd / mu if mu > 0.0 else float("nan"))


def prima_cvar(sd: float, beta: float, n: float = N_EQ, kappa: float = KAPPA) -> float:
    """Prima media-CVaR del horizonte: n · β · κ · σ (COP)."""
    if not (sd >= 0.0 and beta >= 0.0 and n > 0.0):
        raise ValueError(f"sd {sd}, beta {beta}, n {n}")
    return float(n * beta * kappa * sd)


def prima_mv(sd: float, gamma: float, escala: float, n: float = N_EQ) -> float:
    """Prima media-varianza del horizonte: n · ½ · (γ / escala) · σ² (COP)."""
    if not (sd >= 0.0 and gamma >= 0.0 and escala > 0.0 and n > 0.0):
        raise ValueError(f"sd {sd}, gamma {gamma}, escala {escala}")
    return float(n * 0.5 * gamma / escala * sd * sd)


def signo(x, tol: float = EMPATE) -> np.ndarray:
    b = np.asarray(x, dtype=float)
    return np.where(b > tol, 1, np.where(b < -tol, -1, 0)).astype(int)


def consumo_inducido(R, eps: float) -> np.ndarray:
    """ΔD = |ε| · R, con R = Σ r·kWh (o r·D): la respuesta de corto plazo a la
    rebaja relativa de precio. ε tiene que ser negativa."""
    if not eps < 0.0:
        raise ValueError(f"elasticidad no negativa: {eps}")
    R = np.asarray(R, dtype=float)
    if not bool((R >= -1e-12).all()):
        raise ValueError("rebaja ponderada negativa")
    return -eps * np.maximum(R, 0.0)


def tope_comunidad(X, sr_h) -> np.ndarray:
    """(N, T): X repartido a prorrata para que su suma de cada hora no pase del
    residual de la comunidad en la hora, sr_h (T,)."""
    X = np.asarray(X, dtype=float)
    sr = np.asarray(sr_h, dtype=float)
    tot = X.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        f = np.where(tot > sr, np.where(tot > 0, sr / np.where(tot > 0, tot, 1.0), 0.0), 1.0)
    return X * f[None, :]


# ── Un caso ─────────────────────────────────────────────────────────────────
def mensual(x: np.ndarray, mes: np.ndarray, K: int) -> np.ndarray:
    """(N, T) → (N, K): la suma de cada mes."""
    out = np.zeros((x.shape[0], K))
    for k in range(K):
        out[:, k] = x[:, mes == k].sum(axis=1)
    return out


def caso(c: str, TT, cap, pb, idx, meses, dias, pp_media, desc, atr, ppa, pc):
    L = AS.carga(c, TT, cap)
    ags, N, mes = L["ags"], L["N"], L["mes"]
    K = len(meses)
    s, d, v, q, CUa, au, D, G = L["s"], L["d"], L["v"], L["q"], L["CU"], L["au"], L["D"], L["G"]
    T = s.shape[1]
    exige(T == T_HORAS and K == 9, f"{c}: {T} horas y {K} meses")
    lab = np.asarray(idx.strftime("%Y-%m"))
    exige(bool((np.array([meses.index(x) for x in lab]) == mes).all()), f"{c}: el mes del almacén no es el del horizonte")
    a = AS.almacen(c, "agentes")
    exige(list(dict.fromkeys(a.agente)) == ags, f"{c}: orden de agentes")

    def piv(col):
        return a.pivot(index="agente", columns="hora", values=col).loc[ags].to_numpy(dtype=float)

    cred = piv("compra_red")
    finito(cred, f"{c} compra_red")
    # ── 1. satisfacción: la demanda es una sola ────────────────────────────
    d_bal = max(float(np.abs(D - (au + q + cred)).max()), float(np.abs(d - (q + cred)).max()))
    exige(d_bal <= 1e-3, f"{c}: D ≠ autoconsumo + compra dentro + compra a la red ({d_bal:.2e} kWh)")
    libro = AS.lee(LIBRO.format(c), f"outputs/{c}")
    R = pd.read_excel(libro, sheet_name="Resumen").set_index("Escenario")
    PA = pd.read_excel(libro, sheet_name="Por_agente")
    exige(len(PA) == N, f"{c}: Por_agente con {len(PA)} filas")
    sc_f, ss_f = float(au.sum() / G.sum()), float(au.sum() / D.sum())
    sc_m, ss_m = float((au.sum() + q.sum()) / G.sum()), float((au.sum() + q.sum()) / D.sum())
    d_ss = 0.0
    for x in ["C1", "C2", "C3", "C4", "C5"]:
        d_ss = max(d_ss, abs(float(R.loc[x, "SC"]) - sc_f), abs(float(R.loc[x, "SS"]) - ss_f))
    for x in ["P2P", "P2P_colectivo"]:
        d_ss = max(d_ss, abs(float(R.loc[x, "SC"]) - sc_m), abs(float(R.loc[x, "SS"]) - ss_m))
    exige(d_ss <= 1e-5, f"{c}: SC o SS de Resumen ≠ los del almacén ({d_ss:.2e})")
    sat = dict(caso=c, n_instituciones=N, demanda_kwh=float(D.sum()), generacion_kwh=float(G.sum()),
               autoconsumo_kwh=float(au.sum()), transado_kwh=float(q.sum()),
               compra_red_P2P_kwh=float(cred.sum()), faltante_kwh=float(d.sum()),
               SC_C1_a_C5=sc_f, SS_C1_a_C5=ss_f, SC_P2P=sc_m, SS_P2P=ss_m,
               dif_max_balance_kwh=d_bal, dif_max_SC_SS_Resumen=d_ss, dif_utilidad_consumo=0.0)

    # ── 2. beneficio de cada mecanismo, mes a mes (N, K) ───────────────────
    e = AS.almacen(c, "escenarios").astype({"valor": "float64"})
    B = {}
    tol_pa = max(2.0, 2e-7 * abs(float(R.loc["P2P", "Ganancia_neta_COP"])))
    d_pa = 0.0
    for x in MECS_ALM:
        ex = e[e.escenario == x]
        tab = ex.pivot_table(index="agente", columns="mes", values="valor", aggfunc="sum").reindex(index=ags, columns=meses)
        finito(tab.to_numpy(), f"{c} {x} mensual")
        B[x] = tab.to_numpy(dtype=float)
        b_pa = PA[x].to_numpy(dtype=float)
        d_pa = max(d_pa, float(np.abs(B[x].sum(axis=1) - b_pa).max()),
                   abs(float(B[x].sum()) - float(R.loc[x, "Ganancia_neta_COP"])))
    exige(d_pa <= tol_pa, f"{c}: la suma de los meses ≠ Por_agente o Resumen ({d_pa:.3f} COP)")
    # C2 (PPA a la media de XM): A + PP·S, con la CU de la tarifa del proyecto (como c2_ppa.py)
    CU, _, _ = CP.tarifas(ags, idx)
    exige(float(np.abs(CU - CUa).max()) <= 1e-3, f"{c}: CU de la tarifa ≠ techo del almacén")
    # autoconsumo y excedente de G y D, como c2_ppa.py (el almacén los guarda en float32)
    B["C2ppa"] = mensual(np.minimum(G, D) * CU + pp_media * np.maximum(G - D, 0.0), mes, K)
    p_ = ppa[ppa.caso == c].set_index("institucion")
    exige(list(p_.index) == ags + ["comunidad"], f"{c}: instituciones del PPA")
    d_ppa = float(np.abs(B["C2ppa"].sum(axis=1) - p_.loc[ags, "B_C2_media_COP"].to_numpy(float)).max())
    exige(d_ppa <= 1e-3, f"{c}: C2 mensual ≠ B_C2_media_COP de e1/P ({d_ppa:.2e} COP)")
    # P2P colectivo: la liquidación de p2p_comunitario.py, hora a hora
    cs, _, _ = PCm.caso_art20_sin_10(L["capk"], N)
    ded = PCm.deduccion_caso(cs, L["kap"], L["Cv"], L["Th"])
    fl = AS.almacen(c, "flujos").astype({k: "float64" for k in ["kwh", "precio", "techo_comprador", "piso_vendedor",
                                                                 "ahorro_comprador", "prima_vendedor"]})
    pag = PCm.pagos_internos(fl.vendedor.to_numpy(), fl.comprador.to_numpy(), fl.hora.to_numpy(), fl.kwh.to_numpy(),
                             fl.precio.to_numpy(), fl.techo_comprador.to_numpy(), ags, T)
    sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
    col, _ = AS.colectivo(sr, dr, CUa, ded, mes, pb, PCm.igual(N, mes), f"{c} P2P colectivo")
    B["P2Pcom"] = mensual(au * CUa + CUa * q + pag + col, mes, K)
    pcc = pc[pc.caso == c].set_index("institucion")
    exige(list(pcc.index) == ags + ["comunidad"], f"{c}: instituciones del P2P colectivo")
    d_pc = float(np.abs(B["P2Pcom"].sum(axis=1) - pcc.loc[ags, "P2Pcom_COP"].to_numpy(float)).max())
    exige(d_pc <= 1e-3, f"{c}: P2P colectivo mensual ≠ P2Pcom_COP de e1/PC ({d_pc:.2e} COP)")
    for x in MECS:
        finito(B[x], f"{c} {x}")
    F = mensual(D * CU, mes, K)                       # la factura sin generación, común a todos

    # ── tablas de riesgo ───────────────────────────────────────────────────
    filas_m, filas_r, filas_b = [], [], []
    PR = {}                                           # (mecanismo) → dict de primas por institución
    for x in MECS:
        Cm = F - B[x]
        Cn = normaliza_mes(Cm, dias)
        Bn = normaliza_mes(B[x], dias)
        Fn = normaliza_mes(F, dias)
        pr = {k: np.zeros(N) for k in [f"cvar_b{b}" for b in BETAS] + [f"mv_g{b}" for b in BETAS]}
        for i in range(N):
            for k in range(K):
                filas_m.append(dict(caso=c, institucion=ags[i], mecanismo=x, mes=meses[k], dias=float(dias[k]),
                                    factura_COP=F[i, k], beneficio_COP=B[x][i, k], costo_COP=Cm[i, k],
                                    costo_30d_COP=Cn[i, k]))
        for i in list(range(N)) + ["comunidad"]:
            if i == "comunidad":
                cn, bn, fn = Cn.sum(axis=0), Bn.sum(axis=0), Fn.sum(axis=0)
                cm7 = Cm.sum(axis=0)[1:8]
            else:
                cn, bn, fn = Cn[i], Bn[i], Fn[i]
                cm7 = Cm[i, 1:8]
            mu, sd, cv = dispersion(cn)
            mub, sdb, cvb = dispersion(bn)
            muf = float(fn.mean())
            _, sd7, cv7 = dispersion(cm7)
            f = dict(caso=c, institucion="comunidad" if i == "comunidad" else ags[i], mecanismo=x,
                     beneficio_COP=float(B[x].sum() if i == "comunidad" else B[x][i].sum()),
                     factura_COP=float(F.sum() if i == "comunidad" else F[i].sum()),
                     media_costo_30d_COP=mu, sd_costo_30d_COP=sd, cv_costo=cv,
                     media_beneficio_30d_COP=mub, sd_beneficio_30d_COP=sdb, cv_beneficio=cvb,
                     media_factura_30d_COP=muf, sd_costo_7meses_COP=sd7, cv_costo_7meses=cv7)
            f["costo_COP"] = f["factura_COP"] - f["beneficio_COP"]
            if i == "comunidad":
                for b in BETAS:
                    f[f"prima_cvar_b{b}_COP"] = float(pr[f"cvar_b{b}"].sum())
                    f[f"prima_mv_g{b}_COP"] = float(pr[f"mv_g{b}"].sum())
                    f[f"prima_cvar_conjunta_b{b}_COP"] = prima_cvar(sd, BETAS[b])
            else:
                for b, beta in BETAS.items():
                    pr[f"cvar_b{b}"][i] = prima_cvar(sd, beta)
                    pr[f"mv_g{b}"][i] = prima_mv(sd, beta, muf)
                    f[f"prima_cvar_b{b}_COP"] = pr[f"cvar_b{b}"][i]
                    f[f"prima_mv_g{b}_COP"] = pr[f"mv_g{b}"][i]
                    f[f"prima_cvar_conjunta_b{b}_COP"] = np.nan
            for b in BETAS:
                f[f"beneficio_ajustado_cvar_b{b}_COP"] = f["beneficio_COP"] - f[f"prima_cvar_b{b}_COP"]
            f["prima_cvar_sobre_beneficio_b010_pct"] = 100 * f["prima_cvar_b010_COP"] / f["beneficio_COP"]
            filas_r.append(f)
        PR[x] = pr
    # ── brechas con y sin riesgo ───────────────────────────────────────────
    for X, Y in COMPARA:
        for i in list(range(N)) + ["comunidad"]:
            sel = slice(None) if i == "comunidad" else i
            br = float(B[X][sel].sum() - B[Y][sel].sum())
            f = dict(caso=c, institucion="comunidad" if i == "comunidad" else ags[i], comparacion=f"{X}_menos_{Y}",
                     brecha_COP=br, signo=int(signo(br)))
            for b in BETAS:
                dp = float(PR[X][f"cvar_b{b}"][sel].sum() - PR[Y][f"cvar_b{b}"][sel].sum())
                f[f"dprima_cvar_b{b}_COP"] = dp
                f[f"brecha_ajustada_cvar_b{b}_COP"] = br - dp
                f[f"signo_ajustado_cvar_b{b}"] = int(signo(br - dp))
            dpm = float(PR[X]["mv_g010"][sel].sum() - PR[Y]["mv_g010"][sel].sum())
            f["dprima_mv_g010_COP"] = dpm
            f["brecha_ajustada_mv_g010_COP"] = br - dpm
            f["signo_ajustado_mv_g010"] = int(signo(br - dpm))
            filas_b.append(f)

    # ── 4. autoconsumo: el precio interno que ve el comprador ──────────────
    ix = {x: i for i, x in enumerate(ags)}
    iv = fl.vendedor.map(ix).to_numpy(dtype=int)
    ic = fl.comprador.map(ix).to_numpy(dtype=int)
    h = fl.hora.to_numpy(dtype=int)
    k_ = fl.kwh.to_numpy()
    te = fl.techo_comprador.to_numpy()
    pe = np.minimum(fl.precio.to_numpy(), te)
    pi = fl.piso_vendedor.to_numpy()
    exige(bool((te > 0).all()) and bool((k_ >= 0).all()), f"{c}: techo no positivo o kWh negativo en flujos")
    d_te = float(np.abs(te - CUa[ic, h]).max()) if len(fl) else 0.0
    exige(d_te <= 1e-3, f"{c}: el techo del flujo no es la CU del comprador ({d_te:.2e})")
    r = (te - pe) / te
    exige(bool((r >= 0).all()) and bool((r <= 1).all()), f"{c}: rebaja fuera de [0, 1]")
    Q = np.zeros((N, T))
    Rw = np.zeros((N, T))
    np.add.at(Q, (ic, h), k_)
    np.add.at(Rw, (ic, h), r * k_)
    d_q = float(np.abs(Q - q).max())
    exige(d_q <= 1e-3, f"{c}: lo comprado en flujos ≠ compra_p2p ({d_q:.2e} kWh)")
    de = desc[desc.caso == c].set_index("agente")
    ahorro = np.bincount(ic, weights=(te - pe) * k_, minlength=N)
    d_ah = float(np.abs(ahorro - de.loc[ags, "banda_comprador"].to_numpy(float)).max())
    exige(d_ah <= 1.0, f"{c}: Σ (CU − p)·kWh ≠ banda_comprador de e1/C5 ({d_ah:.3f} COP)")
    exige(abs(float(q.sum()) - float(atr.loc[c, "transado_kwh"])) <= 1e-3, f"{c}: transado ≠ atribucion_13casos.csv")
    srh = sr.sum(axis=0)                               # el residual de la comunidad en la hora
    full = (Q > 0) & (Q >= d - 1e-6)                    # la compra dentro cubre todo el faltante
    rbar_h = np.where(Q > 0, Rw / np.where(Q > 0, Q, 1.0), 0.0)
    prima_v = np.bincount(iv, weights=(pe - pi) * k_, minlength=N)
    base_v = np.bincount(iv, weights=pi * k_, minlength=N)
    filas_a = []
    dD = {e_: consumo_inducido(Rw, ev) for e_, ev in EPS.items()}
    dDm = {e_: tope_comunidad(consumo_inducido(np.where(full, rbar_h * D, 0.0), ev), srh) for e_, ev in EPS.items()}
    for e_ in EPS:
        exige(bool((dDm[e_].sum(axis=0) <= srh + 1e-9).all()), f"{c}: el tope marginal no se respeta")
    for i in list(range(N)) + ["comunidad"]:
        sel = slice(None) if i == "comunidad" else slice(i, i + 1)
        qq = float(Q[sel].sum())
        hc = (Q[sel] > 0)
        f = dict(caso=c, institucion="comunidad" if i == "comunidad" else ags[i],
                 comprado_dentro_kwh=qq, horas_con_compra=int(hc.any(axis=0).sum()),
                 agente_horas_con_compra=int(hc.sum()),
                 rebaja_media=float(Rw[sel].sum() / qq) if qq > 0 else np.nan,
                 ahorro_comprador_COP=float(ahorro.sum() if i == "comunidad" else ahorro[i]),
                 demanda_total_kwh=float(D[sel].sum()),
                 demanda_horas_compra_kwh=float(D[sel][hc].sum()),
                 agente_horas_precio_marginal=int(full[sel].sum()),
                 demanda_horas_precio_marginal_kwh=float(D[sel][full[sel]].sum()),
                 prima_relativa_vendedor=(float(prima_v.sum() / base_v.sum()) if i == "comunidad"
                                          else (float(prima_v[i] / base_v[i]) if base_v[i] > 0 else np.nan)))
        for e_ in EPS:
            x = float(dD[e_][sel].sum())
            xm = float(dDm[e_][sel].sum())
            f[f"dD_medio_e{e_}_kwh"] = x
            f[f"dD_medio_e{e_}_pct_horas"] = 100 * x / f["demanda_horas_compra_kwh"] if f["demanda_horas_compra_kwh"] > 0 else np.nan
            f[f"dD_medio_e{e_}_pct_total"] = 100 * x / f["demanda_total_kwh"]
            f[f"dD_marginal_e{e_}_kwh"] = xm
            f[f"dD_marginal_e{e_}_pct_total"] = 100 * xm / f["demanda_total_kwh"]
        if i == "comunidad":
            Dt, aut, Gt = float(D.sum()), float(au.sum()), float(G.sum())
            f["SS_mercado"] = (aut + qq) / Dt
            f["SC_mercado"] = (aut + qq) / Gt
            f["SS_C1_a_C5"] = aut / Dt
            for e_ in EPS:
                dh = dD[e_].sum(axis=0)
                loc = float(np.minimum(dh, srh).sum())
                x = float(dh.sum())
                xm = float(dDm[e_].sum())
                f[f"cubierto_local_e{e_}_kwh"] = loc
                f[f"SS_red_e{e_}"] = (aut + qq) / (Dt + x)
                f[f"SS_local_e{e_}"] = (aut + qq + loc) / (Dt + x)
                f[f"dSS_local_e{e_}_pp"] = 100 * (f[f"SS_local_e{e_}"] - f["SS_mercado"])
                f[f"dSS_red_e{e_}_pp"] = 100 * (f[f"SS_red_e{e_}"] - f["SS_mercado"])
                f[f"SS_marginal_e{e_}"] = (aut + qq + xm) / (Dt + xm)
                f[f"dSS_marginal_e{e_}_pp"] = 100 * (f[f"SS_marginal_e{e_}"] - f["SS_mercado"])
                f[f"SC_local_e{e_}"] = (aut + qq + loc) / Gt
        filas_a.append(f)
    info = dict(d_bal=d_bal, d_ss=d_ss, d_pa=d_pa, d_ppa=d_ppa, d_pc=d_pc, d_q=d_q, d_ah=d_ah, d_te=d_te, caso_art20=cs)
    return sat, filas_m, filas_r, filas_b, filas_a, info


# ── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    t0 = _dt.datetime.now()
    sucio_mod = git("status", "--short", "--", *MODULOS)
    exige(sucio_mod == "", f"módulos de producción con cambios sin commit:\n{sucio_mod}")
    ok("los módulos de producción que se importan están como en HEAD: " + ", ".join(MODULOS))
    print("[intangibles] 1. tarifas, capacidades, horizonte, bolsa, contratos y artefactos del canon")
    TT = AS.tarifas()
    cap = AS.capacidades()
    idx, _ = CP.horizonte()
    pb = CP.bolsa(idx)
    exige(pb.shape == (T_HORAS,) and bool(np.isfinite(pb).all()), "bolsa incompleta")
    pc_h = CP.contratos(idx)
    pp_media = float(pc_h.mean())
    lab = list(idx.strftime("%Y-%m"))
    meses = sorted(set(lab))
    dias = np.array([lab.count(m) / 24.0 for m in meses])
    exige(len(meses) == 9 and float(dias.sum()) == 256.0 and bool((dias == np.round(dias)).all())
          and dias[0] == 27.0 and dias[-1] == 15.0, f"meses {meses}, días {dias}")
    desc = pd.read_csv(AS.lee(F_DESC, "e1/C5"))
    atr = pd.read_csv(AS.lee(F_ATR, "e1/S")).set_index("caso")
    ppa = pd.read_csv(AS.lee(F_PPA, "e1/P"), keep_default_na=False, na_values=[""])
    exige(bool((np.abs(ppa.PP_media_COP_kWh.dropna().to_numpy(float) - pp_media) <= 5e-7).all()),   # CSV a 6 decimales
          f"la media de XM ({pp_media}) no es la de e1/P")
    pc = pd.read_csv(AS.lee(F_PC, "e1/PC"), keep_default_na=False, na_values=[""])
    print("[intangibles] 2. los 13 casos")
    SAT, FM, FR, FB, FA, INFO = [], [], [], [], [], {}
    for c in CASOS:
        sat, fm, fr, fb, fa, info = caso(c, TT, cap, pb, idx, meses, dias, pp_media, desc, atr, ppa, pc)
        SAT.append(sat)
        FM += fm
        FR += fr
        FB += fb
        FA += fa
        INFO[c] = info
        r_ = {x["mecanismo"]: x for x in fr if x["institucion"] == "comunidad"}
        a_ = fa[-1]
        print(f"[intangibles]   {c}: CV del costo P2P {r_['P2P']['cv_costo']:.3f}, C4 {r_['C4']['cv_costo']:.3f}; "
              f"prima β=0,10 P2P {r_['P2P']['prima_cvar_b010_COP'] / M:.3f} MCOP; ΔD (ε=−0,37) "
              f"{a_['dD_medio_e037_kwh']:,.1f} kWh")
    S, Mm, Rr, Bb, A = (pd.DataFrame(x) for x in (SAT, FM, FR, FB, FA))
    mx = {k: max(i[k] for i in INFO.values()) for k in ["d_bal", "d_ss", "d_pa", "d_ppa", "d_pc", "d_q", "d_ah", "d_te"]}
    ok(f"satisfacción: en cada hora D = autoconsumo + compra dentro + compra a la red y faltante = compra dentro + "
       f"compra a la red (≤ {mx['d_bal']:.1e} kWh); SC y SS de la hoja Resumen son Σ au / ΣG y Σ au / ΣD en C1 a C5 y "
       f"(Σ au + transado) / ΣG y / ΣD en P2P y P2P_colectivo (≤ {mx['d_ss']:.1e}), en los 13 casos: la demanda es "
       "una sola y la utilidad de consumo no cambia entre mecanismos")
    ok(f"la suma de los meses de C1, C3, C4, C5 y P2P de la tabla escenarios es Por_agente por institución y Resumen "
       f"por comunidad (≤ {mx['d_pa']:.3f} COP, tolerancia máx(2 COP, 2e-7·P2P)), en los 13 casos")
    ok(f"C2 mes a mes (A + PP·S con PP = {pp_media:.4f} COP/kWh, la media de XM de e1/P) suma B_C2_media_COP de "
       f"c2_ppa_13casos.csv (≤ {mx['d_ppa']:.1e} COP), y el P2P colectivo mes a mes, con la liquidación de "
       f"p2p_comunitario.py, suma P2Pcom_COP de p2p_comunitario_13casos.csv (≤ {mx['d_pc']:.1e} COP), por institución, "
       "en los 13 casos")
    ok(f"horizonte de 9 meses ({meses[0]} a {meses[-1]}), {int(dias.sum())} días, abril de {int(dias[0])} y diciembre "
       f"de {int(dias[-1])}; costos normalizados a 30 días; κ = φ(z_0,95) / 0,05 = {KAPPA:.6f}; n = {N_EQ:.6f} meses "
       "de 30 días")
    ok(f"autoconsumo: en cada flujo el techo es la CU del comprador (≤ {mx['d_te']:.1e}), la rebaja (CU − mín(precio, "
       f"CU)) / CU está en [0, 1], lo comprado por flujos es compra_p2p (≤ {mx['d_q']:.1e} kWh), Σ (CU − p)·kWh es "
       f"banda_comprador de descomposicion_13casos.csv (e1/C5, ≤ {mx['d_ah']:.3f} COP) y lo transado el de "
       "atribucion_13casos.csv (e1/S); el tope del residual de la comunidad se respeta en cada hora")
    # la comunidad es la suma de sus instituciones; todo finito
    for c in CASOS:
        for x in MECS:
            t = Rr[(Rr.caso == c) & (Rr.mecanismo == x)]
            cm, ins = t[t.institucion == "comunidad"].iloc[0], t[t.institucion != "comunidad"]
            for k in ["beneficio_COP", "factura_COP", "costo_COP"] + [f"prima_cvar_b{b}_COP" for b in BETAS]:
                exige(abs(float(ins[k].sum()) - float(cm[k])) <= 1e-6 * max(1.0, abs(float(cm[k]))), f"{c} {x}: comunidad ≠ suma en {k}")
            exige(abs(float(cm.beneficio_COP) - float(Mm[(Mm.caso == c) & (Mm.mecanismo == x)].beneficio_COP.sum())) <= 1e-3,
                  f"{c} {x}: la tabla mensual no suma el beneficio")
        t = A[A.caso == c]
        cm, ins = t[t.institucion == "comunidad"].iloc[0], t[t.institucion != "comunidad"]
        for k in ["comprado_dentro_kwh", "demanda_total_kwh", "ahorro_comprador_COP"] + [f"dD_medio_e{e}_kwh" for e in EPS]:
            exige(abs(float(ins[k].sum()) - float(cm[k])) <= 1e-6 * max(1.0, abs(float(cm[k]))), f"{c}: autoconsumo, comunidad ≠ suma en {k}")
        for X, Y in COMPARA:
            t = Bb[(Bb.caso == c) & (Bb.comparacion == f"{X}_menos_{Y}")]
            cm, ins = t[t.institucion == "comunidad"].iloc[0], t[t.institucion != "comunidad"]
            exige(abs(float(ins.brecha_COP.sum()) - float(cm.brecha_COP)) <= 1e-3, f"{c} {X}−{Y}: brecha ≠ suma")
    finito(Mm.drop(columns=["caso", "institucion", "mecanismo", "mes"]).to_numpy(dtype=float), "costo mensual")
    finito(Bb.drop(columns=["caso", "institucion", "comparacion"]).to_numpy(dtype=float), "brechas")
    finito(S.drop(columns=["caso"]).to_numpy(dtype=float), "satisfacción")
    nan_ok = Rr.drop(columns=["caso", "institucion", "mecanismo", "cv_costo", "cv_costo_7meses", "cv_beneficio",
                              "prima_cvar_conjunta_b005_COP", "prima_cvar_conjunta_b010_COP",
                              "prima_cvar_conjunta_b020_COP"])
    finito(nan_ok.to_numpy(dtype=float), "riesgo")
    # el CV queda vacío (NaN, no se rellena) exactamente donde el costo medio no es positivo
    exige(bool((Rr.cv_costo.isna() == (Rr.media_costo_30d_COP <= 0)).all()), "CV vacío donde el costo medio es positivo")
    n_cv_vacio = int(Rr.cv_costo.isna().sum())
    exige(len(Rr) == 77 * len(MECS) and len(Bb) == 77 * len(COMPARA) and len(A) == 77 and len(S) == 13
          and len(Mm) == 64 * len(MECS) * 9, "filas de las tablas")
    ok("la comunidad es la suma de sus instituciones (beneficio, factura, costo, primas, compra dentro, demanda, "
       "ahorro, consumo inducido y brechas); la tabla mensual suma el beneficio; todo finito salvo el CV, vacío en las "
       f"{n_cv_vacio} filas con el costo medio no positivo y solo en ellas; {len(Rr)} filas de riesgo, {len(Bb)} de "
       f"brechas, {len(A)} de autoconsumo, {len(Mm)} mensuales")
    # pares institución-caso cuyo signo cambia al descontar el riesgo
    ins = Bb[Bb.institucion != "comunidad"]
    exige(all(len(ins[ins.comparacion == f"{X}_menos_{Y}"]) == N_PARES for X, Y in COMPARA), "pares ≠ 64")
    exige(not ("cedenar" in Rr.to_csv().lower() or "cedenar" in A.to_csv().lower()), "comercializador nombrado")
    SALIDA.mkdir(parents=True, exist_ok=True)
    kw = dict(index=False, encoding="utf-8", lineterminator="\n", float_format="%.6f")
    Rr.to_csv(SALIDA / "riesgo_13casos.csv", **kw)
    Bb.to_csv(SALIDA / "brechas_riesgo_13casos.csv", **kw)
    Mm.to_csv(SALIDA / "costo_mensual.csv", **kw)
    A.to_csv(SALIDA / "autoconsumo_13casos.csv", **kw)
    S.to_csv(SALIDA / "satisfaccion_13casos.csv", **kw)
    escribe_readme(Rr, Bb, A, S, pp_media)
    guion = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    sucio = git("status", "--short", "--untracked-files=all", "--", guion)
    leidos = list(AS.LEIDOS) + [x for x in CP.LEIDOS if x not in AS.LEIDOS]
    todas = ([f"(atribucion_supuestos) {x}" for x in AS.COMPUERTAS] + [f"(c2_ppa) {x}" for x in CP.COMPUERTAS]
             + COMPUERTAS)
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh_:
        fh = CP._Anonimo(fh_)              # el nombre de cada comercializador, enmascarado como [A] o [B]
        fh.write("rutas: el nombre de cada comercializador va enmascarado como [A] o [B]; el sha256 identifica "
                 "el fichero\n")
        fh.write("intangibles_autoconsumo.py: beneficio monetario frente a intangible (satisfacción, aversión al riesgo; "
                 "la equidad es §14.6) y el incentivo a consumir en el sitio por elasticidad, derivados sin simular\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n" + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + guion + "\n")
        fh.write("guiones importados (sha256; sin commit si no están en HEAD):\n")
        for g in IMPORTADOS:
            datos = (RAIZ / g).read_bytes()
            est = git("status", "--short", "--untracked-files=all", "--", g)
            fh.write(f"  {g}  {len(datos)}  {hashlib.sha256(datos).hexdigest()}  {est or '(como en HEAD)'}\n")
        fh.write("registrado en HUELLAS.csv como grupo e1/IA (CANON §14.31)\n")
        fh.write("no simula: lee los almacenes y los libros de la matriz del 19 de septiembre y las salidas de los "
                 "puntos C5, S, P y PC\n")
        fh.write(f"supuestos: prima media-CVaR n·β·κ·σ con β en {sorted(BETAS.values())}, α = {ALFA}, κ = {KAPPA:.6f}, "
                 f"n = {N_EQ:.6f}; contraste media-varianza n·½·(γ/F̄)·σ²; elasticidades {sorted(EPS.values())}; "
                 f"PP del C2 = {pp_media:.6f} COP/kWh\n")
        fh.write(f"huellas: {AS.HUELLAS.relative_to(RAIZ).as_posix()}; {len(leidos)} artefactos leídos, todos con la "
                 "huella comprobada:\n")
        for g, r in leidos:
            fh.write(f"  {g}  {r}\n")
        fh.write("insumos de data/ (sin huella en el canon; sha256):\n")
        vistos = set()
        for rel, n, sh in CP.INSUMOS:
            if rel in vistos:
                continue
            vistos.add(rel)
            fh.write(f"  {rel}  {n}  {sh}\n")
        fh.write(f"compuertas: {len(todas)}, todas OK:\n")
        for cpt in todas:
            fh.write(f"  OK  {cpt}\n")
        fh.write(f"filas: riesgo {len(Rr)}, brechas {len(Bb)}, autoconsumo {len(A)}, satisfacción {len(S)}, "
                 f"mensual {len(Mm)}\n")
        fh.write("salvedades: la prima es un supuesto (media-CVaR con normal; la variabilidad mes a mes incluye la "
                 "estacionalidad, que no es riesgo en sentido estricto); el consumo inducido es una estimación por "
                 "elasticidad, no una simulación de respuesta de la demanda (sin DR); no se simula nada\n")
        fh.write("sin fecha: la hora de la corrida solo se imprime en la consola\n")
    print(f"[intangibles] corrida del {t0.isoformat(timespec='seconds')}, {(_dt.datetime.now() - t0).total_seconds():.0f} s")
    print(f"[intangibles] {len(leidos)} artefactos, {len(todas)} compuertas; salida en {SALIDA}")
    return 0


def _n(x: float, d: int = 2) -> str:
    """Número a la española: coma decimal, espacio de miles y signo «−»."""
    if not np.isfinite(x):
        return "—"
    if round(float(x), d) == 0.0:
        x = 0.0
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",").replace("-", "−")


NOMBRE = {"C1": "C1", "C2ppa": "C2", "C3": "C3", "C4": "C4", "C5": "C5", "P2P": "Mercado P2P", "P2Pcom": "P2P colectivo"}


def escribe_readme(Rr, Bb, A, S, pp_media) -> None:
    Rc = Rr[Rr.institucion == "comunidad"].set_index(["caso", "mecanismo"])
    Bc = Bb[Bb.institucion == "comunidad"].set_index(["caso", "comparacion"])
    Ac = A[A.institucion == "comunidad"].set_index("caso")
    L = ["# Beneficio intangible e incentivo a consumir en el sitio (Actividad 3.3)", "",
         "Guion: `reformateo/documento/scripts/articulo/intangibles_autoconsumo.py` (CANON §14.31, grupo `e1/IA` de "
         "`HUELLAS.csv`). Cálculo derivado del canon, sin simular: lee los almacenes y los libros de la matriz del 19 "
         "de septiembre y las salidas de los puntos C5, S, P y PC.", "",
         "## Ficheros", "",
         "- `satisfaccion_13casos.csv`: por caso, la demanda, la generación, el autoconsumo, lo transado y las "
         "columnas SC y SS de la hoja `Resumen` recalculadas del almacén. La demanda es una sola en los siete "
         "mecanismos; la diferencia de utilidad de consumo es cero por construcción.",
         "- `costo_mensual.csv`: caso × institución × mecanismo × mes: factura sin generación (Σ D·CU), beneficio, "
         "costo neto (factura − beneficio) y costo normalizado a 30 días.",
         "- `riesgo_13casos.csv`: caso × institución (y comunidad) × mecanismo: media, desviación típica y CV del "
         "costo mensual normalizado (y del beneficio), las primas media-CVaR (β = 0,05, 0,10 y 0,20) y media-varianza, "
         "y el beneficio ajustado. La comunidad suma las primas de sus instituciones; `prima_cvar_conjunta_*` es la "
         "de la σ del costo de la comunidad.",
         "- `brechas_riesgo_13casos.csv`: caso × institución (y comunidad) × comparación: la brecha, la diferencia "
         "de primas y la brecha ajustada, con sus signos (empate a menos de 1 COP).",
         "- `autoconsumo_13casos.csv`: caso × institución (y comunidad): lo comprado dentro, la rebaja relativa "
         "media ponderada por energía, el consumo inducido con ε = −0,197, −0,37 y −0,468 (precio medio y precio "
         "marginal) y, en la comunidad, la autosuficiencia con el consumo inducido.",
         "- `procedencia.txt`: commit, versiones, huellas leídas, insumos y compuertas.", "",
         "Nombres: `C2ppa` es el C2 de la tesis (el PPA de §14.22, a la media de XM, "
         f"{_n(pp_media, 2)} COP/kWh); `P2Pcom` es el P2P colectivo (§14.23).", "",
         "## Supuestos (declarados)", "",
         "- Costo neto del mes = factura sin generación − beneficio del mecanismo, normalizado a 30 días.",
         f"- Prima principal media-CVaR: π = n·β·κ·σ, n = 256/30, κ = φ(z_0,95)/0,05 = {_n(KAPPA, 4)}; β = 0,05 y "
         "0,20 (rango de Guerrero et al. [26] en la Tabla 1.4 de la revisión de la Act. 1.2) y 0,10 (el η adoptado).",
         "- Contraste media-varianza: π = n·½·(γ/F̄)·σ², γ = β, F̄ la factura media normalizada de la institución.",
         "- Elasticidad de corto plazo: −0,197 y −0,468 (Zabaloy y Viego [19]) y −0,37 (Marques et al. [20], central).",
         "", "## Satisfacción y equidad", "",
         "- La utilidad de consumo del modelo base es U_i(D_i) = λ_i·D_i − θ_i·D_i² (`Documentos/copy/Bienestar6p.py`, "
         "`Welfarei`, línea 50, llamada con el faltante D_i = D − G en la línea 225; `JoinFinal.m`, λ y θ en las líneas "
         "25 y 26 y D_i en la 51); en la corrida, λ = 100 y θ = 0,5 (`main_simulation.py`, líneas 1068 a 1073). La del "
         "programa de respuesta de la demanda es U_k = ln(1 + Σ_n D_k^n) (`core/dr_program.py`, línea 8).",
         "- La demanda es una sola: `AgentParams.alpha` vale cero por defecto (`core/ems_p2p.py`, líneas 290 a 294), "
         "`run_dr_program` devuelve D sin cambio (líneas 2089 a 2091) y `main_simulation.py` solo la sustituye si hay "
         "flexibilidad (líneas 1415 a 1424). `run_comparison` recibe esa demanda «real FIJA» "
         "(`scenarios/comparison_engine.py`, línea 152) y la pasa sin tocarla a C1 (línea 292), C2 (309), C3 (411), "
         "C4 (424), C5 (485) y el P2P por el colectivo (738). Con los datos, `satisfaccion_13casos.csv`: en cada hora "
         "D = autoconsumo + compra dentro + compra a la red, y SC y SS de `Resumen` salen de esa sola demanda.",
         "- Por tanto ΔU = 0 entre los siete mecanismos, por construcción. La satisfacción no separa los mecanismos.",
         "- La equidad ya está medida: el Gini del beneficio por institución y el precio de la justicia del mercado "
         "frente a C4 (CANON §14.6), y el Gini de C2 y del P2P colectivo (§14.22 y §14.23).",
         "", "## 1. El costo mensual y la prima de la comunidad (β = 0,10)", "",
         "| Caso | CV P2P | CV C4 | CV C1 | CV P2P colectivo | Prima P2P (MCOP) | Prima C4 (MCOP) | Prima C1 (MCOP) | "
         "P2P − C4 (MCOP) | ajustada | P2P − C1 (MCOP) | ajustada |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c in CASOS:
        L.append(f"| {c} | {_n(Rc.loc[(c, 'P2P'), 'cv_costo'], 3)} | {_n(Rc.loc[(c, 'C4'), 'cv_costo'], 3)} | "
                 f"{_n(Rc.loc[(c, 'C1'), 'cv_costo'], 3)} | {_n(Rc.loc[(c, 'P2Pcom'), 'cv_costo'], 3)} | "
                 f"{_n(Rc.loc[(c, 'P2P'), 'prima_cvar_b010_COP'] / M, 3)} | {_n(Rc.loc[(c, 'C4'), 'prima_cvar_b010_COP'] / M, 3)} | "
                 f"{_n(Rc.loc[(c, 'C1'), 'prima_cvar_b010_COP'] / M, 3)} | "
                 f"{_n(Bc.loc[(c, 'P2P_menos_C4'), 'brecha_COP'] / M, 3)} | "
                 f"{_n(Bc.loc[(c, 'P2P_menos_C4'), 'brecha_ajustada_cvar_b010_COP'] / M, 3)} | "
                 f"{_n(Bc.loc[(c, 'P2P_menos_C1'), 'brecha_COP'] / M, 3)} | "
                 f"{_n(Bc.loc[(c, 'P2P_menos_C1'), 'brecha_ajustada_cvar_b010_COP'] / M, 3)} |")
    L += ["", "## 2. El consumo inducido en la comunidad (ε = −0,37)", "",
          "| Caso | Comprado dentro (kWh) | Rebaja media (%) | ΔD precio medio (kWh) | ΔD / demanda en esas horas (%) | "
          "ΔD / demanda del horizonte (%) | ΔD precio marginal (kWh) | SS del mercado (%) | ΔSS, residual local (pp) | "
          "ΔSS, red (pp) |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c in CASOS:
        r = Ac.loc[c]
        L.append(f"| {c} | {_n(r.comprado_dentro_kwh, 1)} | {_n(100 * r.rebaja_media, 2)} | {_n(r.dD_medio_e037_kwh, 1)} | "
                 f"{_n(r.dD_medio_e037_pct_horas, 3)} | {_n(r.dD_medio_e037_pct_total, 4)} | "
                 f"{_n(r.dD_marginal_e037_kwh, 1)} | {_n(100 * r.SS_mercado, 2)} | {_n(r.dSS_local_e037_pp, 4)} | "
                 f"{_n(r.dSS_red_e037_pp, 4)} |")
    L += ["", "En C1, C2, C3 y C4 el comprador paga su tarifa por cada kWh que importa: el efecto es cero. El P2P "
          "colectivo usa los mismos flujos y precios del mercado: el mismo efecto que el mercado. C5 no se estima.", "",
          "## Salvedades", "",
          "- La prima es un supuesto de esta medición, no un parámetro del canon. La variabilidad mes a mes incluye "
          "la estacionalidad de la demanda y de la generación, que es previsible: la prima es una cota del costo del "
          "riesgo, no una medida de riesgo puro. Nueve meses dan una σ con poca precisión.",
          "- El consumo inducido es una estimación posterior por elasticidad, no una simulación de respuesta de la "
          "demanda, que el modelo tiene apagada («sin DR»). Las elasticidades son residenciales de América Latina; la "
          "demanda institucional es más rígida. La variante de precio marginal solo cuenta las horas en que la compra "
          "dentro cubre todo el faltante de la hora.",
          "- El lado del vendedor va en sentido contrario y no se estima: con el mercado, consumir su propio excedente "
          "le cuesta el precio interno y no su piso (`prima_relativa_vendedor`).", ""]
    (SALIDA / "README.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    sys.exit(main())
