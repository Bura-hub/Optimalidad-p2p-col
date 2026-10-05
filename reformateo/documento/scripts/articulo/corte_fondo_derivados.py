"""
corte_fondo_derivados.py — El corte hx y el fondo del P2P colectivo, medidos
en energía y en pesos sin simular
===============================================================================
Actividades 2.1, 3.3 y 4.2 de la propuesta. Cálculo DERIVADO del canon: no
simula el mercado ni usa el servidor. Lee artefactos con huella en
`Documentos/canon_2026-09/HUELLAS.csv` (comprueba tamaño y `sha256` de cada uno
antes de leerlo, con `atribucion_supuestos.lee`) y liquida la energía con la
función del propio proyecto (`core.opciones_externas.reparto_anexo4`).

Dos ideas del trabajo (dictamen del 2026-10-04 sobre el corte y el fondo):

  1. EL CORTE. El piso del vendedor cambia en su hora del corte hx del Anexo 4
     de la CREG 101 072: antes, su residual es crédito y el piso es la permuta
     del numeral de su planta (CU − deducción); desde hx, es exceso y el piso
     es la bolsa de la hora con su tope. Un flujo del almacén está «tras el
     corte» si el piso de su vendedor en esa hora (tabla `agentes`) difiere de
     la permuta en más de 0,01 COP/kWh, la misma marca con la que el punto S
     reconstruye la bolsa (CANON §14.21). Es el corte aproximado del piso que
     usó el motor; el de la liquidación (`reparto_anexo4` sobre el residual)
     se da al lado y se declara la diferencia.
     Por caso e institución: la energía transada antes y tras el corte, el
     ahorro del intercambio (la banda de CANON §14.8: prima del vendedor sobre
     su piso más ahorro del comprador bajo su techo) antes y tras el corte, y,
     para la comunidad, el ahorro por kWh transado (el ancho efectivo), que es
     la banda media techo − piso ponderada por la energía transada.

  2. EL FONDO. En el P2P colectivo (CANON §14.23) el residual de cada miembro,
     sr = max(s − v, 0), entra al fondo de la hora y se reparte igual (1/N);
     cada parte se acredita contra la importación residual del mes del
     miembro, dr = max(d − q, 0), con el corte del Anexo 4. En el mercado P2P
     cada miembro acredita su propio residual. Por miembro y mes, con A la
     asignación del fondo y S su propio residual:
       recibido = max(A − S, 0), cedido = max(S − A, 0);
       ganado   = crédito con el fondo − crédito propio, donde A > S;
       perdido  = crédito propio − crédito con el fondo, donde A < S;
       neto     = ganado − perdido = exceso del P2P − exceso del P2P colectivo.
     «Ganado» es el residual que el fondo lleva a miembros que todavía importan
     y se acredita; «neto», la energía que el fondo saca de la bolsa frente al
     mercado P2P (negativa donde la manda a la bolsa: N1).
     Además, la energía de exceso a la bolsa en C1, en el mercado P2P, en el
     P2P colectivo y en C4.

COMPUERTAS (falla en voz alta; ningún `except`; todo finito):
  - el piso de cada flujo es el de su vendedor en la tabla `agentes`, y donde
    está tras el corte es la bolsa reconstruida del punto S (e1/S);
  - por flujo, prima + ahorro = (techo − piso) × kWh, de modo que el ahorro
    por kWh es la banda media ponderada por energía;
  - lo antes y lo tras el corte suman lo total (energía al 1e-6 kWh, ahorro al
    peso), el ahorro total es la banda de `descomposicion_13casos.csv` (e1/C5)
    de la comunidad y de cada institución, y la energía transada es la de
    `atribucion_13casos.csv` (e1/S);
  - el exceso de C1, del mercado P2P y de C4 es el de `atribucion_13casos.csv`,
    y el del P2P colectivo y de C4 por institución, el de
    `p2p_comunitario_13casos.csv` (e1/PC), con sus residuales;
  - en el fondo, lo asignado suma lo aportado cada mes, lo recibido es lo
    cedido, el crédito de cada miembro y mes es mín(inyección, importación) y
    neto = exceso del P2P − exceso del P2P colectivo;
  - donde nadie agota el cupo (E0, P2, K1, CV2 y SINU, CANON §14.8) no hay
    energía tras el corte, y en los otros ocho sí.

Escribe en SALIDAS_SERVIDOR/corte_fondo_2026-10-04/:

    corte_fondo_13casos.csv   caso × institución (y comunidad)
    resumen.md                las tablas de la comunidad y N1 por institución
    procedencia.txt           commit, versiones, huellas y compuertas, sin fecha

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/corte_fondo_derivados.py

Registrado en HUELLAS.csv como grupo `e1/CF` (CANON §14.25).

Actividades 2.1, 3.3 y 4.2.
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
from core.opciones_externas import precio_permuta_por_periodo, reparto_anexo4  # noqa: E402

SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
SALIDA = SALIDAS / "corte_fondo_2026-10-04"
CASOS = AS.CASOS
SIN_CORTE = AS.SIN_AGOTAR            # E0, P2, K1, CV2 y SINU: nadie agota el cupo (CANON §14.8)
M = 1e6
TOL_PISO = 1e-2                      # COP/kWh: la marca del punto S (§14.21)
F_DESC = "descomposicion_p2p_2026-09-27/descomposicion_13casos.csv"
F_ATR = "atribucion_supuestos_2026-09-30/atribucion_13casos.csv"
F_BOLSA = "atribucion_supuestos_2026-09-30/bolsa_reconstruida.csv"
F_PC = "p2p_comunitario_2026-10-02/p2p_comunitario_13casos.csv"
MODULOS = ["core/opciones_externas.py", "scenarios/scenario_c4_creg101072.py"]
IMPORTADOS = ["reformateo/documento/scripts/articulo/atribucion_supuestos.py"]

COMPUERTAS: list[str] = []


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[corte_fondo] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    COMPUERTAS.append(msg)
    print(f"[corte_fondo]   OK  {msg}")


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


def finito(x, qué: str):
    exige(bool(np.isfinite(np.asarray(x, dtype=float)).all()), f"{qué}: valores no finitos")
    return x


# ── Funciones puras (las prueba tests/test_corte_fondo_derivados.py) ─────────
def marca_corte(piso: np.ndarray, permuta: np.ndarray, tol: float = TOL_PISO) -> np.ndarray:
    """(N, T) True donde el piso del agente no es la permuta de su numeral: su
    residual ya pasó el corte hx y el piso es la bolsa."""
    piso, permuta = np.asarray(piso, dtype=float), np.asarray(permuta, dtype=float)
    finito(piso, "piso")
    finito(permuta, "permuta")
    return np.abs(piso - permuta) > tol


def parte(x: np.ndarray, tras: np.ndarray) -> tuple[float, float]:
    """(antes, tras) del corte: las sumas de `x` donde `tras` es False y True."""
    x = np.asarray(x, dtype=float)
    tras = np.asarray(tras, dtype=bool)
    exige(x.shape == tras.shape, "parte: formas distintas")
    finito(x, "parte")
    return float(x[~tras].sum()), float(x[tras].sum())


def ancho(banda: float, kwh: float) -> float:
    """Ahorro del intercambio por kWh transado (COP/kWh); NaN si no hay energía
    (no se rellena: el canon no lo cita donde no está definido)."""
    exige(np.isfinite(banda) and np.isfinite(kwh) and kwh >= 0.0, f"ancho: banda {banda}, kWh {kwh}")
    return float(banda / kwh) if kwh > 0.0 else float("nan")


def fondo_energia(sr: np.ndarray, dr: np.ndarray, mes: np.ndarray, pesos: dict) -> tuple[np.ndarray, ...]:
    """El colectivo del P2P colectivo solo en energía (como
    `atribucion_supuestos.colectivo`, sin valorar): el fondo de cada hora,
    Σ sr, repartido con los pesos del mes y acreditado contra dr con el Anexo
    4. Devuelve (asignación, crédito, exceso), cada una (N, T)."""
    sr, dr = np.asarray(sr, dtype=float), np.asarray(dr, dtype=float)
    N, T = sr.shape
    A, cr, ex = np.zeros((N, T)), np.zeros((N, T)), np.zeros((N, T))
    for m in np.unique(mes):
        h = np.flatnonzero(mes == m)
        w = np.asarray(pesos[m], dtype=float)
        exige(abs(w.sum() - 1.0) <= 1e-9 and bool((w >= 0).all()), f"pesos del mes {m} no suman 1")
        a = w[:, None] * sr[:, h].sum(axis=0)[None, :]
        c, e, _ = reparto_anexo4(a, dr[:, h])
        A[:, h], cr[:, h], ex[:, h] = a, c, e
    return A, cr, ex


def balance_fondo(A, S, cr_fondo, cr_propio, mes) -> dict:
    """Por miembro (N,), sumando sus meses: lo que el reparto le da por encima
    de su propio residual (recibido) o le quita (cedido), y el crédito que gana
    donde recibe y pierde donde cede, frente a acreditar su propio residual."""
    A, S, cf, cp = (np.asarray(x, dtype=float) for x in (A, S, cr_fondo, cr_propio))
    N = A.shape[0]
    out = {k: np.zeros(N) for k in ["recibido", "cedido", "ganado", "perdido"]}
    for m in np.unique(mes):
        h = mes == m
        a, s = A[:, h].sum(axis=1), S[:, h].sum(axis=1)
        dc = cf[:, h].sum(axis=1) - cp[:, h].sum(axis=1)
        out["recibido"] += np.maximum(a - s, 0.0)
        out["cedido"] += np.maximum(s - a, 0.0)
        out["ganado"] += np.where(a > s, dc, 0.0)
        out["perdido"] += np.where(a < s, -dc, 0.0)
    out["neto"] = out["ganado"] - out["perdido"]
    return out


# ── Un caso ─────────────────────────────────────────────────────────────────
def caso(c: str, TT, cap, pb, desc, atr, pc) -> tuple[list[dict], dict]:
    L = AS.carga(c, TT, cap)
    ags, N, mes = L["ags"], L["N"], L["mes"]
    s, d, v, q = L["s"], L["d"], L["v"], L["q"]
    perm = precio_permuta_por_periodo(L["CU"], L["ded1"], mes)
    tras = marca_corte(L["piso"], perm)
    # la bolsa: donde el piso no es la permuta, es la bolsa reconstruida del punto S
    pbm = np.broadcast_to(pb, tras.shape)
    exige(bool(np.isfinite(pbm[tras]).all()), f"{c}: horas tras el corte sin bolsa reconstruida")
    d_bolsa = float(np.abs(L["piso"][tras] - pbm[tras]).max()) if tras.any() else 0.0
    exige(d_bolsa <= 1e-3, f"{c}: el piso tras el corte no es la bolsa reconstruida ({d_bolsa:.2e})")

    fl = AS.almacen(c, "flujos").astype({k: "float64" for k in ["kwh", "precio", "techo_comprador", "piso_vendedor",
                                                                 "prima_vendedor", "ahorro_comprador"]})
    finito(fl[["kwh", "techo_comprador", "piso_vendedor", "prima_vendedor", "ahorro_comprador"]].to_numpy(), f"{c} flujos")
    ix = {a: i for i, a in enumerate(ags)}
    iv = fl.vendedor.map(ix).to_numpy(dtype=int)
    ic = fl.comprador.map(ix).to_numpy(dtype=int)
    h = fl.hora.to_numpy(dtype=int)
    k = fl.kwh.to_numpy()
    pri, aho = fl.prima_vendedor.to_numpy(), fl.ahorro_comprador.to_numpy()
    b = pri + aho
    d_pv = float(np.abs(fl.piso_vendedor.to_numpy() - L["piso"][iv, h]).max()) if len(fl) else 0.0
    exige(d_pv <= 1e-3, f"{c}: piso del flujo ≠ piso de su vendedor en agentes ({d_pv:.2e})")
    w = (fl.techo_comprador.to_numpy() - fl.piso_vendedor.to_numpy()) * k
    d_w = float(np.abs(w - b).max()) if len(fl) else 0.0
    exige(d_w <= 0.01 and abs(float(w.sum() - b.sum())) <= 1.0,
          f"{c}: prima + ahorro ≠ (techo − piso) × kWh ({d_w:.4f} por flujo, {w.sum() - b.sum():.4f} en total)")
    t = tras[iv, h]
    # corte de la liquidación (Anexo 4 sobre el residual), para declarar la diferencia
    sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
    _, _, en_perm = reparto_anexo4(sr, dr, mes)
    t_liq = (~en_perm)[iv, h]

    # exceso y crédito: C1 (bruto, por miembro), P2P (residual, por miembro), P2P colectivo (residual al fondo) y C4
    cr1, ex1, _ = reparto_anexo4(s, d, mes)
    crp, exp_, _ = reparto_anexo4(sr, dr, mes)
    igual = {m: np.full(N, 1.0 / N) for m in np.unique(mes)}
    A, crc, exc = fondo_energia(sr, dr, mes, igual)
    A4, cr4, ex4 = fondo_energia(s, d, mes, igual)
    for x, qué in [(cr1, "C1"), (crp, "P2P"), (crc, "P2P colectivo"), (cr4, "C4")]:
        finito(x, f"{c} crédito {qué}")
    # el crédito de cada miembro y mes es mín(inyección, importación): el cupo del Anexo 4
    for iny, imp, cr, qué in [(s, d, cr1, "C1"), (sr, dr, crp, "P2P"), (A, dr, crc, "P2P colectivo"), (A4, d, cr4, "C4")]:
        for m in np.unique(mes):
            hh = mes == m
            dif = np.abs(cr[:, hh].sum(axis=1) - np.minimum(iny[:, hh].sum(axis=1), imp[:, hh].sum(axis=1)))
            exige(float(dif.max()) <= 1e-6, f"{c} {qué}: crédito del mes ≠ mín(inyección, importación)")
    for m in np.unique(mes):
        hh = mes == m
        exige(abs(float(A[:, hh].sum() - sr[:, hh].sum())) <= 1e-6, f"{c}: el fondo del mes {m} no reparte lo aportado")
    BF = balance_fondo(A, sr, crc, crp, mes)
    exige(abs(float(BF["recibido"].sum() - BF["cedido"].sum())) <= 1e-6, f"{c}: lo recibido no es lo cedido")
    neto_ex = float(exp_.sum() - exc.sum())
    exige(abs(float(BF["neto"].sum()) - neto_ex) <= 1e-6,
          f"{c}: ganado − perdido = {BF['neto'].sum():.6f} ≠ exceso P2P − P2P colectivo = {neto_ex:.6f}")

    # contra el canon
    a_ = atr.loc[c]
    d_e = max(abs(float(ex1.sum()) - a_.exceso_kwh__C1), abs(float(exp_.sum()) - a_.exceso_kwh__P2P),
              abs(float(ex4.sum()) - a_.exceso_kwh__C4), abs(float(k.sum()) - a_.transado_kwh))
    exige(d_e <= 1e-3, f"{c}: exceso de C1, P2P o C4, o energía transada ≠ atribucion_13casos.csv ({d_e:.2e} kWh)")
    p_ = pc[pc.caso == c].set_index("institucion")
    exige(list(p_.index) == ags + ["comunidad"], f"{c}: instituciones de p2p_comunitario_13casos.csv")
    d_pc = 0.0
    for col, x in [("exceso_kwh_P2Pcom", exc), ("exceso_kwh_C4_sin10", ex4), ("residual_iny_kwh", sr),
                   ("residual_imp_kwh", dr), ("vendido_dentro_kwh", v), ("comprado_dentro_kwh", q)]:
        d_pc = max(d_pc, float(np.abs(x.sum(axis=1) - p_.loc[ags, col].to_numpy(float)).max()),
                   abs(float(x.sum()) - float(p_.loc["comunidad", col])))
    exige(d_pc <= 1e-3, f"{c}: exceso o residuales ≠ p2p_comunitario_13casos.csv ({d_pc:.2e} kWh)")
    de = desc[desc.caso == c].set_index("agente")
    bv = np.bincount(iv, weights=pri, minlength=N)
    bc = np.bincount(ic, weights=aho, minlength=N)
    d_b = max(float(np.abs(bv - de.loc[ags, "banda_vendedor"].to_numpy(float)).max()),
              float(np.abs(bc - de.loc[ags, "banda_comprador"].to_numpy(float)).max()),
              abs(float(b.sum()) - float(de.loc["comunidad", "banda"])))
    exige(d_b <= 1.0, f"{c}: la banda ≠ descomposicion_13casos.csv ({d_b:.3f} COP)")

    # antes y tras el corte; compuerta de la suma contra los totales calculados aparte
    ea, et = parte(k, t)
    ba, bt = parte(b, t)
    exige(abs(ea + et - float(fl.kwh.sum())) <= 1e-6 and abs(ba + bt - float((fl.prima_vendedor + fl.ahorro_comprador).sum())) <= 1.0,
          f"{c}: antes + tras ≠ total")
    if c in SIN_CORTE:
        exige(et == 0.0 and not tras.any(), f"{c}: energía tras el corte donde nadie agota el cupo ({et} kWh)")
    else:
        exige(et > 0.0, f"{c}: sin energía tras el corte donde se agota el cupo")

    filas = []
    for i in list(range(N)) + ["comunidad"]:
        if i == "comunidad":
            sv, sc, sel = np.ones(len(fl), bool), np.ones(len(fl), bool), slice(None)
        else:
            sv, sc, sel = iv == i, ic == i, slice(i, i + 1)
        f = dict(caso=c, institucion="comunidad" if i == "comunidad" else ags[i])
        f["vendido_kwh"] = float(k[sv].sum())
        f["vendido_antes_kwh"], f["vendido_tras_kwh"] = parte(k[sv], t[sv])
        f["comprado_kwh"] = float(k[sc].sum())
        f["comprado_antes_kwh"], f["comprado_tras_kwh"] = parte(k[sc], t[sc])
        f["vendido_tras_corte_liquidacion_kwh"] = float(k[sv & t_liq].sum())
        f["banda_vendedor_antes_COP"], f["banda_vendedor_tras_COP"] = parte(pri[sv], t[sv])
        f["banda_comprador_antes_COP"], f["banda_comprador_tras_COP"] = parte(aho[sc], t[sc])
        f["banda_antes_COP"] = f["banda_vendedor_antes_COP"] + f["banda_comprador_antes_COP"]
        f["banda_tras_COP"] = f["banda_vendedor_tras_COP"] + f["banda_comprador_tras_COP"]
        f["banda_COP"] = f["banda_antes_COP"] + f["banda_tras_COP"]
        if i == "comunidad":
            f["ancho_COP_kWh"] = ancho(f["banda_COP"], f["vendido_kwh"])
            f["ancho_antes_COP_kWh"] = ancho(f["banda_antes_COP"], f["vendido_antes_kwh"])
            f["ancho_tras_COP_kWh"] = ancho(f["banda_tras_COP"], f["vendido_tras_kwh"])
            f["horas_tras_con_venta"] = int(np.unique(h[t]).size)
            f["agente_horas_tras_corte"] = int(tras.sum())
        else:
            f["ancho_COP_kWh"] = f["ancho_antes_COP_kWh"] = f["ancho_tras_COP_kWh"] = np.nan
            f["horas_tras_con_venta"] = int(np.unique(h[sv & t]).size)
            f["agente_horas_tras_corte"] = int(tras[i].sum())
        f["inyeccion_kwh"] = float(s[sel].sum())
        f["importacion_kwh"] = float(d[sel].sum())
        f["residual_iny_kwh"] = float(sr[sel].sum())
        f["residual_imp_kwh"] = float(dr[sel].sum())
        for qn, cr, ex in [("C1", cr1, ex1), ("P2P", crp, exp_), ("P2Pcol", crc, exc), ("C4", cr4, ex4)]:
            f[f"credito_{qn}_kwh"] = float(cr[sel].sum())
            f[f"exceso_{qn}_kwh"] = float(ex[sel].sum())
        f["exceso_C1_menos_P2P_kwh"] = f["exceso_C1_kwh"] - f["exceso_P2P_kwh"]
        f["exceso_P2P_menos_P2Pcol_kwh"] = f["exceso_P2P_kwh"] - f["exceso_P2Pcol_kwh"]
        f["fondo_asignado_kwh"] = float(A[sel].sum())
        for kk in ["recibido", "cedido", "ganado", "perdido", "neto"]:
            f[f"fondo_{kk}_kwh"] = float(BF[kk][sel].sum())
        filas.append(f)
    info = dict(d_bolsa=d_bolsa, d_pv=d_pv, d_w=d_w, d_e=d_e, d_pc=d_pc, d_b=d_b,
                desacuerdo=float(k[t != t_liq].sum()))
    return filas, info


# ── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    t0 = _dt.datetime.now()
    sucio_mod = git("status", "--short", "--", *MODULOS)
    exige(sucio_mod == "", f"módulos de producción con cambios sin commit:\n{sucio_mod}")
    ok("los módulos de producción que se importan están como en HEAD: " + ", ".join(MODULOS))
    print("[corte_fondo] 1. tarifas, capacidades, bolsa y artefactos del canon")
    TT = AS.tarifas()
    cap = AS.capacidades()
    bt = pd.read_csv(AS.lee(F_BOLSA, "e1/S"))
    finito(bt.bolsa, "bolsa reconstruida")
    pb = np.full(6144, np.nan)
    pb[bt.hora.to_numpy(dtype=int)] = bt.bolsa.to_numpy(dtype=float)
    desc = pd.read_csv(AS.lee(F_DESC, "e1/C5"))
    atr = pd.read_csv(AS.lee(F_ATR, "e1/S")).set_index("caso")
    pc = pd.read_csv(AS.lee(F_PC, "e1/PC"), keep_default_na=False, na_values=[""])
    print("[corte_fondo] 2. los 13 casos")
    filas, info = [], {}
    for c in CASOS:
        fc, info[c] = caso(c, TT, cap, pb, desc, atr, pc)
        filas += fc
        com = fc[-1]
        print(f"[corte_fondo]   {c}: tras el corte {com['vendido_tras_kwh']:,.1f} de {com['vendido_kwh']:,.1f} kWh, "
              f"{com['banda_tras_COP'] / M:.3f} de {com['banda_COP'] / M:.3f} MCOP; fondo neto "
              f"{com['fondo_neto_kwh']:,.1f} kWh")
    T = pd.DataFrame(filas)
    mx = {k_: max(i_[k_] for i_ in info.values()) for k_ in ["d_bolsa", "d_pv", "d_w", "d_e", "d_pc", "d_b"]}
    ok(f"el piso de cada flujo es el de su vendedor en agentes (≤ {mx['d_pv']:.1e}) y, tras el corte, la bolsa "
       f"reconstruida del punto S (e1/S, ≤ {mx['d_bolsa']:.1e} COP/kWh); por flujo, prima + ahorro = (techo − piso) × kWh "
       f"(≤ {mx['d_w']:.4f} COP), así que el ahorro por kWh es la banda media ponderada por energía, en los 13 casos")
    ok(f"lo antes y lo tras el corte suman lo total (energía y ahorro); el ahorro total es la banda de "
       f"descomposicion_13casos.csv (e1/C5) de la comunidad y de cada institución (≤ {mx['d_b']:.3f} COP) y la energía "
       f"transada la de atribucion_13casos.csv (e1/S); en E0, P2, K1, CV2 y SINU no hay energía tras el corte y en los "
       "otros ocho sí")
    ok(f"el exceso de C1, del mercado P2P y de C4 es el de atribucion_13casos.csv (≤ {mx['d_e']:.1e} kWh) y el del P2P "
       f"colectivo, C4 y los residuales por institución, los de p2p_comunitario_13casos.csv (e1/PC, ≤ {mx['d_pc']:.1e} kWh)")
    ok("fondo: lo asignado suma lo aportado cada mes, lo recibido es lo cedido, el crédito de cada miembro y mes es "
       "mín(inyección, importación) en C1, P2P, P2P colectivo y C4, y ganado − perdido = exceso del P2P − exceso del P2P "
       "colectivo (≤ 1e-6 kWh), en los 13 casos")
    num = T.drop(columns=["caso", "institucion", "ancho_COP_kWh", "ancho_antes_COP_kWh", "ancho_tras_COP_kWh"])
    finito(num.to_numpy(dtype=float), "tabla")
    exige(len(T) == 77, f"{len(T)} filas, no 77")
    exige("cedenar" not in T.to_csv().lower() and "asc," not in T.to_csv().lower(), "comercializador nombrado")
    SALIDA.mkdir(parents=True, exist_ok=True)
    T.to_csv(SALIDA / "corte_fondo_13casos.csv", index=False, encoding="utf-8", lineterminator="\n", float_format="%.6f")
    escribe_resumen(T, info)
    guion = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    sucio = git("status", "--short", "--untracked-files=all", "--", guion)
    leidos = list(AS.LEIDOS)
    todas = [f"(atribucion_supuestos) {x}" for x in AS.COMPUERTAS] + COMPUERTAS
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("corte_fondo_derivados.py: el corte hx (energía y ahorro del intercambio antes y tras el corte) y el "
                 "fondo del P2P colectivo (residual redistribuido y exceso a la bolsa), derivados sin simular\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n" + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + guion + "\n")
        fh.write("guiones importados (sha256; sin commit si no están en HEAD):\n")
        for g in IMPORTADOS:
            datos = (RAIZ / g).read_bytes()
            est = git("status", "--short", "--untracked-files=all", "--", g)
            fh.write(f"  {g}  {len(datos)}  {hashlib.sha256(datos).hexdigest()}  {est or '(como en HEAD)'}\n")
        fh.write("registrado en HUELLAS.csv como grupo e1/CF (CANON §14.25)\n")
        fh.write("no simula: lee los almacenes de la matriz del 19 de septiembre y las salidas de los puntos C5, S y PC\n")
        fh.write(f"huellas: {AS.HUELLAS.relative_to(RAIZ).as_posix()}; {len(leidos)} artefactos leídos, todos con la "
                 "huella comprobada:\n")
        for g, r in leidos:
            fh.write(f"  {g}  {r}\n")
        fh.write(f"compuertas: {len(todas)}, todas OK:\n")
        for cpt in todas:
            fh.write(f"  OK  {cpt}\n")
        fh.write(f"filas de corte_fondo_13casos.csv: {len(T)}\n")
        fh.write("salvedades: el corte es el aproximado del piso que usó el motor (el de la liquidación se da al lado); "
                 "flujos del motor fijos; el P2P colectivo es una propuesta regulatoria; no se simula\n")
        fh.write("sin fecha: la hora de la corrida solo se imprime en la consola\n")
    print(f"[corte_fondo] corrida del {t0.isoformat(timespec='seconds')}, {(_dt.datetime.now() - t0).total_seconds():.0f} s")
    print(f"[corte_fondo] {len(leidos)} artefactos, {len(todas)} compuertas; salida en {SALIDA}")
    return 0


def _n(x: float, d: int = 2) -> str:
    """Número a la española: coma decimal, espacio de miles y signo «−»."""
    if not np.isfinite(x):
        return "—"
    if round(float(x), d) == 0.0:
        x = 0.0
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",").replace("-", "−")


def escribe_resumen(T: pd.DataFrame, info: dict) -> None:
    C = T[T.institucion == "comunidad"].set_index("caso")
    L = ["# El corte hx y el fondo del P2P colectivo: la comunidad por caso", "",
         "Fuente: `corte_fondo_13casos.csv` de esta carpeta (guion "
         "`reformateo/documento/scripts/articulo/corte_fondo_derivados.py`; CANON §14.25). Cálculo derivado, sin simular. "
         "«Tras el corte»: el piso del vendedor en esa hora es la bolsa (su residual pasó la hora hx del Anexo 4).", "",
         "## 1. El corte en el mercado P2P", "",
         "| Caso | Transado (kWh) | Antes (kWh) | Tras (kWh) | Tras (%) | Ahorro antes (MCOP) | Ahorro tras (MCOP) | "
         "Ahorro tras (%) | COP/kWh antes | COP/kWh tras | COP/kWh total | Tras, corte de la liquidación (kWh) |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in C.iterrows():
        pe = 100 * r.vendido_tras_kwh / r.vendido_kwh
        pb_ = 100 * r.banda_tras_COP / r.banda_COP
        L.append(f"| {c} | {_n(r.vendido_kwh, 1)} | {_n(r.vendido_antes_kwh, 1)} | {_n(r.vendido_tras_kwh, 1)} | "
                 f"{_n(pe, 1)} | {_n(r.banda_antes_COP / M, 3)} | {_n(r.banda_tras_COP / M, 3)} | {_n(pb_, 1)} | "
                 f"{_n(r.ancho_antes_COP_kWh)} | {_n(r.ancho_tras_COP_kWh)} | {_n(r.ancho_COP_kWh)} | "
                 f"{_n(r.vendido_tras_corte_liquidacion_kwh, 1)} |")
    L += ["", "El ahorro por kWh es la banda media (techo del comprador − piso del vendedor) ponderada por la energía "
          "transada: por flujo, prima + ahorro = (techo − piso) × kWh. Energía transada donde el corte del piso y el de "
          "la liquidación no coinciden: " + "; ".join(f"{c} {_n(i['desacuerdo'], 1)}" for c, i in info.items()
                                                     if i["desacuerdo"] > 0) + " kWh.", "",
          "## 2. Exceso a la bolsa (kWh)", "",
          "| Caso | C1 | Mercado P2P | P2P colectivo | C4 | C1 − mercado | Mercado − P2P colectivo |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for c, r in C.iterrows():
        L.append(f"| {c} | {_n(r.exceso_C1_kwh, 1)} | {_n(r.exceso_P2P_kwh, 1)} | {_n(r.exceso_P2Pcol_kwh, 1)} | "
                 f"{_n(r.exceso_C4_kwh, 1)} | {_n(r.exceso_C1_menos_P2P_kwh, 1)} | {_n(r.exceso_P2P_menos_P2Pcol_kwh, 1)} |")
    L += ["", "## 3. El fondo del P2P colectivo frente al mercado P2P (kWh)", "",
          "Por miembro y mes: recibido = máx(asignado − propio, 0); ganado, el crédito que gana quien recibe (el "
          "residual que llega a quien todavía importa y se acredita); perdido, el que pierde quien cede; neto = ganado − "
          "perdido = exceso del mercado − exceso del P2P colectivo.", "",
          "| Caso | Residual al fondo | Redistribuido | Ganado | Perdido | Neto |", "|---|---:|---:|---:|---:|---:|"]
    for c, r in C.iterrows():
        L.append(f"| {c} | {_n(r.residual_iny_kwh, 1)} | {_n(r.fondo_recibido_kwh, 1)} | {_n(r.fondo_ganado_kwh, 1)} | "
                 f"{_n(r.fondo_perdido_kwh, 1)} | {_n(r.fondo_neto_kwh, 1)} |")
    n1 = T[(T.caso == "N1") & (T.institucion != "comunidad")]
    L += ["", "## 4. N1 por institución (kWh)", "",
          "| Institución | Exceso, mercado | Exceso, P2P colectivo | Recibido | Cedido | Ganado | Perdido |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for _, r in n1.iterrows():
        L.append(f"| {r.institucion} | {_n(r.exceso_P2P_kwh, 1)} | {_n(r.exceso_P2Pcol_kwh, 1)} | "
                 f"{_n(r.fondo_recibido_kwh, 1)} | {_n(r.fondo_cedido_kwh, 1)} | {_n(r.fondo_ganado_kwh, 1)} | "
                 f"{_n(r.fondo_perdido_kwh, 1)} |")
    menos = [c for c, r in C.iterrows() if r.exceso_P2P_menos_P2Pcol_kwh > 1e-6]
    mas = [c for c, r in C.iterrows() if r.exceso_P2P_menos_P2Pcol_kwh < -1e-6]
    L += ["", f"El P2P colectivo manda menos a la bolsa que el mercado P2P en {', '.join(menos)}; más en "
          f"{', '.join(mas) or 'ninguno'}; lo mismo en los demás.", "",
          "Salvedades: el corte es el aproximado del piso que usó el motor; los flujos del mercado son los del motor, "
          "fijos; el P2P colectivo es una propuesta regulatoria (CANON §14.23); no se simula nada.", ""]
    (SALIDA / "resumen.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    sys.exit(main())
