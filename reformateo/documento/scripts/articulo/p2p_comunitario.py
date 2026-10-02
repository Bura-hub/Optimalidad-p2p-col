"""
p2p_comunitario.py — El «P2P comunitario»: el mercado entre pares con el
autogenerador colectivo como interfaz con la red, frente a C4 y al canon
===============================================================================
Actividades 2.1 y 2.2 de la propuesta (escenarios regulatorios y su
comparación). Cálculo DERIVADO del canon: no simula el mercado ni usa el
servidor. Lee artefactos con huella en `Documentos/canon_2026-09/HUELLAS.csv`
(comprueba tamaño y `sha256` de cada uno antes de leerlo) e importa, en lugar
de copiarlas, las funciones de `atribucion_supuestos.py` (punto S: `carga`,
`tarifas`, `capacidades`, `colectivo`, `art25`, `pesos`, `almacen`, `lee`) y
de `c2_ppa.py` (punto P: `horizonte`, `bolsa`, `gini`, `signo_brecha`,
`tabla_canon`).

QUÉ ES (propuesta regulatoria del autor, 2026-10-02; reemplaza al «mercado P2P
por el colectivo» de `scenarios/scenario_p2p_colectivo.py`, que queda en el
canon como la esquina v(0,0) del punto S):

  * Intercambio interno. Cada hora los miembros intercambian con los flujos y
    los precios del mercado P2P tal como quedaron en el almacén de cada caso
    (`vende_p2p`, `compra_p2p` y la tabla `flujos`). Lo intercambiado NO paga
    ningún cargo y NO entra al fondo ni al porcentaje (PDE): el comprador
    ahorra su CU por cada kWh comprado dentro y paga al vendedor el precio del
    mercado con el techo de su tarifa (CAL-35, como `run_p2p_colectivo`). Los
    pagos internos suman cero.
  * El residual al colectivo. sr = max(s − v, 0) y dr = max(d − q, 0). El fondo
    común de cada hora es Σ sr; se reparte con el PDE y se liquida con
    `colectivo(...)` (la del colectivo mensual del motor): crédito hasta la
    importación residual del mes de cada miembro y exceso a la bolsa horaria
    desde el corte hx del Anexo 4, con el perfil horario declarado.
  * El caso del art. 20 de la CREG 101 072 SIN la regla del 10 % (ni las 11
    fronteras): caso 1 si la capacidad instalada por usuario del art. 18
    (CINAC = suma de las capacidades instaladas de las plantas / número de
    fronteras: 5, o 4 en SINU) es ≤ 100 kW y la suma ≤ 1 MW; si no, caso 2.
    Caso 1: se deduce solo κ·Cv (numeral 1 del art. 25 de la CREG 174, también
    para las plantas de más de 100 kW de I1 y N1: lectura literal, pregunta
    abierta 2). Caso 2: κ·Cv + Θ. κ = 2 en CV2 y 1 en los demás.

El umbral se mide como manda la norma: capacidad instalada (art. 18, art. 20 y
art. 25). Ninguna norma, concepto de la CREG ni operador de red clasifica por
lo exportado (901 079, pp. 48-49; 901 286, p. 43; conceptos 1717/2023,
3023/2026 y 11110/2025).

QUÉ CALCULA, por caso (13) × institución y para la comunidad:

  1. Base: el P2P comunitario con el PDE igual (art. 9, 1/N) sobre el fondo
     residual, en el caso de su CINAC.
  2. C4 en el caso de la CINAC sin intercambio (q = v = 0, PDE igual): «C4 sin
     la regla del 10 %». Descomposición exacta:
        P2Pcom − C4 = (C4_sin10 − C4) + (P2Pcom − C4_sin10)
     lo que vale quitar la regla del 10 % y lo que vale el intercambio exento.
     Las dos reformas se solapan: es el ORDEN DIRECTO. El ORDEN INVERSO
     (añadido el 2026-10-02) pone primero el intercambio exento con la regla
     del 10 % vigente, el P2P comunitario con el residual en el caso 2
     (κ·Cv + Θ = ded4, PDE igual), «P2Pcom caso 2»:
        P2Pcom − C4 = (P2Pcom caso 2 − C4) + (P2Pcom − P2Pcom caso 2)
     y SHAPLEY es la media de los dos órdenes (como el punto S, §14.21). En
     E4, E5 y P2 (caso 2) los dos órdenes coinciden y quitar la regla vale 0.
  3. Sensibilidad PDE por importación (las dos a la vez): el P2P comunitario
     con el PDE de cada mes proporcional a la importación residual (dr), y C4
     con el de la importación del mes (d; `pde_por_regla("importacion")`, la
     regla de H-100). Se verifica C4 por importación (caso 2) contra
     `spread_estatico_2026-09-27/spread_13casos.csv` (e1/C3).
  4. Sensibilidad «caso 1 para todos»: P2P comunitario y C4 sin la regla del
     10 % con κ·Cv en los 13 casos (segunda reforma: medida comercial de lo
     exportado, sin base vigente).
  5. Dato: la potencia residual horaria máxima por frontera (máx_h sr) y la
     del excedente bruto (máx_h s), en kW (paso horario).
  6. Gini de la ganancia por institución (fila de la comunidad) con
     `core.settlement.gini_index`, la función del Gini entre mecanismos del
     canon (C-214), con su compuerta como en c2_ppa.py.
  7. Comparaciones: P2Pcom frente a C1, C4, P2P (con supuestos), P2P por el
     colectivo, C2 (PPA a la media de XM, punto P), C5 y C3; pares
     institución-caso (64, convención de «25 de 64») por encima de C4 y C1.

LA BOLSA es la de la caché de XM que usó la corrida (`c2_ppa.bolsa`, completa
en las 6 144 horas y con compuerta contra la reconstruida del punto S); la
reconstruida tiene huecos y el reparto igual del residual pone exceso en horas
sin ella (E5, §14.21).

COMPUERTAS (falla en voz alta; ningún `except`; todo finito): con κ·Cv + Θ y
el PDE de v01 reproduce v01 de `atribucion_13casos.csv` al peso; sin
intercambio, en el caso 2 y con PDE igual reproduce C4 canónico (comunidad e
institución); los pagos internos suman cero y, con el residual por miembro
(art. 25), reproducen el P2P canónico por institución; el colectivo con el
PDE del mercado reproduce el P2P por el colectivo por institución; C4 por
importación = H-100; C4 sin la regla del 10 % con κ·Cv = C4 con 11
fronteras del contrafáctico del art. 18 (A1) por institución; el caso 1 queda cerca del P2P canónico donde la
deducción del numeral 1 es la de cada planta y nadie agota el cupo (se
informa, no se exige); el P2P comunitario en el caso 2 de la comunidad cae
dentro de [v01_igual_min, v01_igual_max] de `atribucion_13casos.csv` (al peso
donde las cotas coinciden); en el caso 2 es el P2P comunitario al peso; las
dos identidades y la de Shapley cierran en cada fila.

Escribe en SALIDAS_SERVIDOR/p2p_comunitario_2026-10-02/:

    p2p_comunitario_13casos.csv   una fila por caso × institución y una
                                  «comunidad» por caso
    resumen.md                    la comunidad por caso
    procedencia.txt               commit, versiones, huellas, insumos y
                                  compuertas, sin fecha: con el mismo HEAD y
                                  los mismos guiones, los tres ficheros salen
                                  iguales byte a byte entre corridas

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/p2p_comunitario.py

SALVEDADES: es una propuesta regulatoria, no la norma vigente (requiere
declarar el intercambio exento de cargos y quitar la regla del 10 % a los
colectivos pequeños); los flujos son los del motor, fijos: exactos donde el
piso del vendedor no cambia (caso 1 con plantas en el numeral 1) y aproximados
en E4, E5 y P2 (piso CU − Cv − Θ); comercializador único (art. 10) y perfil
horario declarado como supuestos; los comercializadores se nombran A y B.

Registrado en HUELLAS.csv como grupo `e1/PC` (CANON §14.23).

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
from scenarios.scenario_c4_creg101072 import (  # noqa: E402
    AGPE_LIMIT_KW, capacidad_por_usuario_art18, compute_pde_weights, pde_por_regla, resolve_caso_art20)

SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
SALIDA = SALIDAS / "p2p_comunitario_2026-10-02"
CASOS = AS.CASOS
LIBRO = "SALIDAS_SERVIDOR/matriz_reposo/{}/outputs/resultados_comparacion.xlsx"
UMBRAL_KW = 100.0                    # art. 20 num. 1 ii (CINAC del art. 18)
CASO1_ESPERADO = {"E0", "E1", "E2", "E3", "P1", "K1", "CV2", "SINU", "I1", "N1"}
NUMERAL1_SIN_AGOTAR = ["E0", "K1", "CV2", "SINU"]   # caso 1, plantas ≤ 100 kW y nadie agota (CANON §14.8)
MECS_CANON = ["C1", "C4", "P2P", "P2P_colectivo", "C5", "C3"]
COMPARA = ["C1", "C4", "P2P", "P2P_colectivo", "C2ppa", "C5", "C3"]
N_PARES = 64
EMPATE = CP.EMPATE
M = 1e6
# módulos de producción que se importan: tienen que estar como en HEAD
MODULOS = ["core/opciones_externas.py", "core/settlement.py", "data/cedenar_tariff.py", "data/xm_prices.py",
           "data/precios_contratos.py", "scenarios/scenario_c4_creg101072.py", "scenarios/scenario_c2_bilateral.py",
           "scenarios/scenario_c3_spot.py", "scenarios/_pi_gs.py"]
IMPORTADOS = ["reformateo/documento/scripts/articulo/atribucion_supuestos.py",
              "reformateo/documento/scripts/articulo/c2_ppa.py"]
SOLO_COMUNIDAD = ["pot_residual_comunidad_max_kw", "pot_excedente_comunidad_max_kw", "gini_P2Pcom", "gini_C4_sin10",
                  "gini_C4", "gini_P2P", "gini_C1", "gini_C2ppa", "gini_P2Pcom_imp", "gini_P2Pcom_c1todos"]

COMPUERTAS: list[str] = []


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[p2p_comunitario] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    COMPUERTAS.append(msg)
    print(f"[p2p_comunitario]   OK  {msg}")


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


def finito(x, qué: str):
    exige(bool(np.isfinite(np.asarray(x, dtype=float)).all()), f"{qué}: valores no finitos")
    return x


# ── Funciones puras (las prueba tests/test_p2p_comunitario.py) ──────────────
def caso_art20_sin_10(capk, n_fronteras: int, umbral_kw: float = UMBRAL_KW,
                      limite_kw: float = AGPE_LIMIT_KW) -> tuple[int, float, float]:
    """(caso, CINAC, suma) del art. 20 de la CREG 101 072 sin la regla del 10 %:
    caso 1 si la CINAC del art. 18 (suma de capacidades instaladas / fronteras)
    es ≤ `umbral_kw` y la suma ≤ `limite_kw`; si no, caso 2."""
    capk = np.asarray(capk, dtype=float)
    cin = capacidad_por_usuario_art18(capk, n_fronteras)
    suma = float(capk.sum())
    caso = 1 if (cin <= umbral_kw and suma <= limite_kw) else 2
    # la función de producción, con el PDE fuera de juego, decide lo mismo por capacidad
    prod = resolve_caso_art20(np.full(n_fronteras, 1.0 / n_fronteras), capk, umbral_kw,
                              pde_limit=np.inf, n_fronteras=n_fronteras)
    if suma <= limite_kw and prod != caso:
        raise ValueError(f"caso {caso} distinto del de resolve_caso_art20 ({prod})")
    return caso, cin, suma


def deduccion_caso(caso: int, kap: float, Cv: np.ndarray, Th: np.ndarray) -> np.ndarray:
    """Caso 1: κ·Cv (numeral 1 del art. 25). Caso 2: κ·Cv + Θ (numeral 2)."""
    if caso not in (1, 2):
        raise ValueError(f"caso {caso!r}")
    Cv = np.asarray(Cv, dtype=float)
    return kap * Cv + (np.asarray(Th, dtype=float) if caso == 2 else 0.0)


def pagos_internos(vendedor, comprador, hora, kwh, precio, techo, ags: list[str], T: int) -> np.ndarray:
    """(N, T): + lo que cobra el vendedor, − lo que paga el comprador, al precio
    del mercado con el techo de la tarifa del comprador (CAL-35)."""
    idx = {a: i for i, a in enumerate(ags)}
    iv = np.array([idx[x] for x in vendedor], dtype=int)
    ic = np.array([idx[x] for x in comprador], dtype=int)
    h = np.asarray(hora, dtype=int)
    dinero = np.asarray(kwh, dtype=float) * np.minimum(np.asarray(precio, dtype=float), np.asarray(techo, dtype=float))
    P = np.zeros((len(ags), T))
    np.add.at(P, (iv, h), dinero)
    np.add.at(P, (ic, h), -dinero)
    return P


def pesos_proporcionales(x: np.ndarray, mes: np.ndarray) -> dict:
    """{mes: (N,)} proporcional a Σ_mes x; un mes con suma nula cae al reparto
    igual (como `pde_por_regla`)."""
    N = x.shape[0]
    out = {}
    for m in np.unique(mes):
        t = x[:, mes == m].sum(axis=1)
        out[m] = (np.full(N, 1.0 / N) if not float(t.sum()) > 0.0
                  else compute_pde_weights(t, method="excedentes_proportional"))
    return out


def igual(N: int, mes: np.ndarray) -> dict:
    return {m: np.full(N, 1.0 / N) for m in np.unique(mes)}


CLASES_ORDEN = {
    "sin10_domina": "quitar la regla del 10 % domina por los dos órdenes",
    "intercambio_domina": "el intercambio exento domina por los dos órdenes",
    "depende_orden": "depende del orden",
    "solo_intercambio": "todo es intercambio (caso 2: quitar la regla no vale nada)",
}


def clasifica_ordenes(sin10: float, intercambio: float, sin10_inv: float, intercambio_inv: float,
                      tol: float = 1.0) -> str:
    """Clase de un caso con los dos órdenes de P2Pcom − C4: «solo_intercambio»
    si quitar la regla del 10 % no vale nada por ninguno de los dos (|x| ≤ tol,
    caso 2); si no, qué término es mayor en cada orden: el mismo por los dos
    («sin10_domina» o «intercambio_domina») o uno distinto («depende_orden»)."""
    vals = np.array([sin10, intercambio, sin10_inv, intercambio_inv], dtype=float)
    if not np.isfinite(vals).all():
        raise ValueError(f"valores no finitos: {vals}")
    if abs(sin10) <= tol and abs(sin10_inv) <= tol:
        return "solo_intercambio"
    d, i = sin10 > intercambio, sin10_inv > intercambio_inv
    return "sin10_domina" if (d and i) else "intercambio_domina" if (not d and not i) else "depende_orden"


def valor_comunitario(au, s, d, v, q, CU, pagos, ded, mes, pb, pesos, qué: str):
    """((N,) beneficio, (N,) exceso kWh) del P2P comunitario: autoconsumo a la
    tarifa, ahorro CU·q del comprador, pagos internos (suman cero) y el
    colectivo sobre el residual (sr, dr). Con q = v = 0 y pagos = 0 es C4 con
    la deducción `ded`."""
    sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
    col, ex = AS.colectivo(sr, dr, CU, ded, mes, pb, pesos, qué)
    return (au * CU + CU * q + pagos + col).sum(axis=1), ex.sum(axis=1)


# ── Un caso ─────────────────────────────────────────────────────────────────
def caso(c: str, TT, cap, pb, atr, spread, ppa, t146, a1) -> tuple[list[dict], dict]:
    L = AS.carga(c, TT, cap)
    N, ags, mes = L["N"], L["ags"], L["mes"]
    s, d, v, q, CU, au = L["s"], L["d"], L["v"], L["q"], L["CU"], L["au"]
    T = s.shape[1]
    sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
    cs, cin, suma = caso_art20_sin_10(L["capk"], N)
    ded1 = deduccion_caso(1, L["kap"], L["Cv"], L["Th"])
    ded2 = deduccion_caso(2, L["kap"], L["Cv"], L["Th"])
    exige(float(np.abs(ded2 - L["ded4"]).max()) == 0.0, f"{c}: la deducción del caso 2 no es ded4 de atribucion")
    ded = ded1 if cs == 1 else ded2
    cero = np.zeros((N, T))
    # pagos internos
    fl = AS.almacen(c, "flujos").astype({"kwh": "float64", "precio": "float64", "techo_comprador": "float64"})
    pag = pagos_internos(fl.vendedor.to_numpy(), fl.comprador.to_numpy(), fl.hora.to_numpy(), fl.kwh.to_numpy(),
                         fl.precio.to_numpy(), fl.techo_comprador.to_numpy(), ags, T)
    finito(pag, f"{c} pagos")
    escala = float(np.abs(pag).sum()) or 1.0
    exige(float(np.abs(pag.sum(axis=0)).max()) <= 1e-6 * escala, f"{c}: los pagos internos no suman cero por hora")
    W_ig = igual(N, mes)
    W_impr = pesos_proporcionales(dr, mes)
    W_impd = pde_por_regla("importacion", L["G"], L["D"], mes)
    W_impd2 = pesos_proporcionales(d, mes)
    exige(all(float(np.abs(W_impd[m] - W_impd2[m]).max()) <= 1e-6 for m in W_impd), f"{c}: PDE por importación ≠ pde_por_regla")

    def VC(vv, qq, pp, dd, W, qué):
        return valor_comunitario(au, s, d, vv, qq, CU, pp, dd, mes, pb, W, f"{c} {qué}")

    P2Pcom, exP = VC(v, q, pag, ded, W_ig, "P2P comunitario")
    C4s10, exC = VC(cero, cero, cero, ded, W_ig, "C4 sin la regla del 10 %")
    C4, _ = VC(cero, cero, cero, ded2, W_ig, "C4")
    # orden inverso: primero el intercambio exento con la regla del 10 % vigente
    # (residual en el caso 2, κ·Cv + Θ = ded4, PDE igual), después quitar la regla
    P2Pcom_c2, _ = VC(v, q, pag, ded2, W_ig, "P2P comunitario en el caso 2")
    P2Pcom_imp, _ = VC(v, q, pag, ded, W_impr, "P2P comunitario, PDE por importación residual")
    C4_imp, _ = VC(cero, cero, cero, ded2, W_impd, "C4 por importación")
    C4s10_imp, _ = VC(cero, cero, cero, ded, W_impd, "C4 sin 10 % por importación")
    P2Pcom_c1, _ = VC(v, q, pag, ded1, W_ig, "P2P comunitario, caso 1 para todos")
    C4s10_c1, _ = VC(cero, cero, cero, ded1, W_ig, "C4 sin 10 %, caso 1 para todos")
    # reproducciones
    v01, _ = VC(v, q, cero, ded2, AS.pesos(sr, mes), "v01")
    p2p_rep = (au * CU + CU * q + pag + AS.art25(sr, dr, CU, L["ded1"], mes, pb, f"{c} residual P2P")[0]).sum(axis=1)
    col_rep = (au * CU + pag + AS.colectivo(s, d, CU, ded2, mes, pb, AS.pesos(q + sr, mes), f"{c} P2P colectivo")[0]).sum(axis=1)
    libro = AS.lee(LIBRO.format(c), f"outputs/{c}")
    R = pd.read_excel(libro, sheet_name="Resumen").set_index("Escenario")["Ganancia_neta_COP"]
    PA = pd.read_excel(libro, sheet_name="Por_agente")
    exige(len(PA) == N, f"{c}: Por_agente con {len(PA)} filas")
    B = {}
    for x in MECS_CANON:
        b = PA[x].to_numpy(dtype=float)
        finito(b, f"{c} Por_agente {x}")
        exige(abs(b.sum() - R[x]) <= max(0.01, 1e-12 * abs(R[x])), f"{c} {x}: Por_agente no suma Resumen")
        dif = np.abs(b - L["por_agente"][x].to_numpy())
        exige(float(dif.max()) <= max(2.0, 2e-7 * abs(R["P2P"])), f"{c} {x}: Por_agente ≠ almacén ({dif.max():.3f})")
        B[x] = b
    pp = ppa[ppa.caso == c].set_index("institucion")
    exige(list(pp.index) == ags + ["comunidad"], f"{c}: instituciones del PPA {list(pp.index)}")
    B["C2ppa"] = pp.loc[ags, "B_C2_media_COP"].to_numpy(dtype=float)
    exige(abs(B["C2ppa"].sum() - float(pp.loc["comunidad", "B_C2_media_COP"])) <= 1e-3, f"{c}: PPA comunidad ≠ suma")
    # Gini canónico (C-214)
    pf = pd.read_excel(libro, sheet_name="PoF_Fairness").set_index("escenario")["gini"]
    dgini = max(abs(CP.gini(B[x]) - float(pf[x])) for x in ["C1", "C4", "P2P", "P2P_colectivo", "C3", "C5"])
    exige(dgini <= 1e-12, f"{c}: gini_index(Por_agente) ≠ PoF_Fairness en {dgini:.2e}")
    for x, col in [("P2P", "Gini P2P"), ("C4", "Gini C4")]:
        exige(f"{float(pf[x]):.3f}".replace(".", ",") == t146.loc[c, col], f"{c}: Gini {x} ≠ CANON §14.6")
    g_ppa = CP.gini(B["C2ppa"])
    exige(abs(g_ppa - float(pp.loc["comunidad", "gini_C2_media"])) <= 5e-7, f"{c}: Gini del PPA ≠ e1/P")
    # diferencias de las compuertas
    aux = dict(
        c=c, caso=cs, cinac=cin, suma=suma, N=N,
        d_v01=float(v01.sum() - atr.loc[c, "v01"]),
        d_c4_com=float(C4.sum() - R["C4"]), d_c4_ins=float(np.abs(C4 - B["C4"]).max()),
        d_p2p_ins=float(np.abs(p2p_rep - B["P2P"]).max()), d_col_ins=float(np.abs(col_rep - B["P2P_colectivo"]).max()),
        d_c4imp=float(C4_imp.sum() - spread.loc[c, "C4_importacion_COP"]),
        d_a1=float(max(abs(C4s10_c1.sum() - a1.loc[c, "total_COP"]),
                       np.abs(C4s10_c1 - a1.loc[c, ags].to_numpy(dtype=float)).max())),
        d_pag=float(np.abs(pag.sum(axis=0)).max()), d_gini=dgini,
        caso1_menos_P2P=float(P2Pcom.sum() - R["P2P"]),
        tol=max(1.0, 1e-7 * abs(R["P2P"])),
        d_sin10_caso2=float(np.abs(C4s10 - C4).max()) if cs == 2 else 0.0,
        d_c1todos=float(max(np.abs(P2Pcom_c1 - P2Pcom).max(), np.abs(C4s10_c1 - C4s10).max())) if cs == 1 else 0.0,
        # orden inverso frente a v01 con el reparto igual del punto S (cotas por la bolsa reconstruida)
        p2pcom_c2=float(P2Pcom_c2.sum()), v01ig_min=float(atr.loc[c, "v01_igual_min"]),
        v01ig_max=float(atr.loc[c, "v01_igual_max"]),
        d_c2_caso2=float(np.abs(P2Pcom_c2 - P2Pcom).max()) if cs == 2 else 0.0,
    )
    com = {a: str(pp.loc[a, "comercializador"]) for a in ags}
    capk = L["capk"]
    V = dict(P2Pcom=P2Pcom, C4_sin10=C4s10, C4=C4, P2Pcom_imp=P2Pcom_imp, C4_imp=C4_imp, C4_sin10_imp=C4s10_imp,
             P2Pcom_c1todos=P2Pcom_c1, C4_sin10_c1todos=C4s10_c1)
    filas = []
    for i in list(range(N)) + ["comunidad"]:
        sel = slice(None) if i == "comunidad" else slice(i, i + 1)
        f = dict(caso=c, institucion="comunidad" if i == "comunidad" else ags[i],
                 comercializador="" if i == "comunidad" else com[ags[i]],
                 n_fronteras=N, suma_cap_kw=suma, cinac_kw=cin,
                 cap_planta_kw=float(capk.max() if i == "comunidad" else capk[i]), caso_art20=cs,
                 inyeccion_kwh=float(s[sel].sum()), importacion_kwh=float(d[sel].sum()),
                 vendido_dentro_kwh=float(v[sel].sum()), comprado_dentro_kwh=float(q[sel].sum()),
                 residual_iny_kwh=float(sr[sel].sum()), residual_imp_kwh=float(dr[sel].sum()),
                 pagos_internos_COP=float(pag[sel].sum()),
                 exceso_kwh_P2Pcom=float(exP[sel].sum()), exceso_kwh_C4_sin10=float(exC[sel].sum()))
        for k, x in V.items():
            f[f"{k}_COP"] = float(x[sel].sum())
        for pre, a, b_, cc in [("", "P2Pcom", "C4_sin10", "C4"), ("imp_", "P2Pcom_imp", "C4_sin10_imp", "C4_imp"),
                               ("c1todos_", "P2Pcom_c1todos", "C4_sin10_c1todos", "C4")]:
            f[f"{pre}P2Pcom_menos_C4_COP"] = f[f"{a}_COP"] - f[f"{cc}_COP"]
            f[f"{pre}dec_sin10_COP"] = f[f"{b_}_COP"] - f[f"{cc}_COP"]
            f[f"{pre}dec_intercambio_COP"] = f[f"{a}_COP"] - f[f"{b_}_COP"]
        for x in COMPARA:
            f[f"B_{x}_COP"] = float(B[x][sel].sum())
        for x in COMPARA:
            f[f"brecha_P2Pcom_menos_{x}_COP"] = f["P2Pcom_COP"] - f[f"B_{x}_COP"]
            f[f"signo_P2Pcom_menos_{x}"] = int(CP.signo_brecha(f[f"brecha_P2Pcom_menos_{x}_COP"]))
        f["imp_C4_imp_menos_P2P_COP"] = f["C4_imp_COP"] - f["B_P2P_COP"]
        f["imp_P2Pcom_menos_P2P_COP"] = f["P2Pcom_imp_COP"] - f["B_P2P_COP"]
        f["pot_residual_max_kw"] = float(sr[sel].max())
        f["pot_excedente_max_kw"] = float(s[sel].max())
        if i == "comunidad":
            f["pot_residual_comunidad_max_kw"] = float(sr.sum(axis=0).max())
            f["pot_excedente_comunidad_max_kw"] = float(s.sum(axis=0).max())
            f["gini_P2Pcom"] = CP.gini(P2Pcom)
            f["gini_C4_sin10"] = CP.gini(C4s10)
            f["gini_C4"] = float(pf["C4"])
            f["gini_P2P"] = float(pf["P2P"])
            f["gini_C1"] = float(pf["C1"])
            f["gini_C2ppa"] = g_ppa
            f["gini_P2Pcom_imp"] = CP.gini(P2Pcom_imp)
            f["gini_P2Pcom_c1todos"] = CP.gini(P2Pcom_c1)
        else:
            for k in SOLO_COMUNIDAD:
                f[k] = np.nan
        # los dos órdenes de la base y Shapley (como el punto S, §14.21), al final de la fila
        f["P2Pcom_caso2_COP"] = float(P2Pcom_c2[sel].sum())
        f["inv_dec_intercambio_COP"] = f["P2Pcom_caso2_COP"] - f["C4_COP"]
        f["inv_dec_sin10_COP"] = f["P2Pcom_COP"] - f["P2Pcom_caso2_COP"]
        f["sh_dec_sin10_COP"] = (f["dec_sin10_COP"] + f["inv_dec_sin10_COP"]) / 2
        f["sh_dec_intercambio_COP"] = (f["dec_intercambio_COP"] + f["inv_dec_intercambio_COP"]) / 2
        f["interaccion_ordenes_COP"] = f["inv_dec_sin10_COP"] - f["dec_sin10_COP"]
        filas.append(f)
    return filas, aux


def main() -> int:
    t0 = _dt.datetime.now()
    sucio_mod = git("status", "--short", "--", *MODULOS)
    exige(sucio_mod == "", f"módulos de producción con cambios sin commit:\n{sucio_mod}")
    ok("los módulos de producción que se importan están como en HEAD: " + ", ".join(MODULOS))
    print("[p2p_comunitario] 1. tarifas, capacidades, horizonte y bolsa")
    TT = AS.tarifas()
    cap = AS.capacidades()
    idx, _ = CP.horizonte()
    pb = CP.bolsa(idx)
    exige(pb.shape == (6144,) and bool(np.isfinite(pb).all()), "bolsa incompleta")
    atr = pd.read_csv(AS.lee("atribucion_supuestos_2026-09-30/atribucion_13casos.csv", "e1/S")).set_index("caso")
    spread = pd.read_csv(AS.lee("spread_estatico_2026-09-27/spread_13casos.csv", "e1/C3")).set_index("caso")
    ppa = pd.read_csv(AS.lee("c2_ppa_2026-10-02/c2_ppa_13casos.csv", "e1/P"), keep_default_na=False, na_values=[""])
    ppa["comercializador"] = ppa.comercializador.fillna("")
    exige(set(ppa.comercializador) <= {"A", "B", ""}, "comercializadores del PPA sin anonimizar")
    a1 = pd.read_csv(AS.lee("contrafacticos_art18_2026-09-27/contrafacticos_13casos.csv", "e1/A1"))
    a1 = a1[a1.contrafactico == "C4_11_fronteras"].set_index("caso")
    exige(sorted(a1.index) == sorted(CASOS) and bool((a1.caso_art20 == 1).all()), "A1: C4 con 11 fronteras")
    t146 = CP.tabla_canon("### 14.6 ·", "Caso")
    exige(list(t146.index) == CASOS, "CANON §14.6: casos")
    print("[p2p_comunitario] 2. los 13 casos")
    filas, AUX = [], {}
    for c in CASOS:
        fc, aux = caso(c, TT, cap, pb, atr, spread, ppa, t146, a1)
        filas += fc
        AUX[c] = aux
        print(f"[p2p_comunitario]   {c}: caso {aux['caso']} (CINAC {aux['cinac']:.2f} kW, suma {aux['suma']:.2f} kW); "
              f"v01 a {aux['d_v01']:+.3f} COP; C4 a {aux['d_c4_com']:+.3f} COP")
    T = pd.DataFrame(filas)
    # ── compuertas ──────────────────────────────────────────────────────────
    clas = {c: AUX[c]["caso"] for c in CASOS}
    exige({c for c in CASOS if clas[c] == 1} == CASO1_ESPERADO,
          f"clasificación distinta de la esperada: {clas}")
    ok("clasificación del art. 20 sin la regla del 10 % (CINAC = suma de capacidades instaladas / fronteras, ≤ 100 kW, "
       "y suma ≤ 1 MW; misma decisión que resolve_caso_art20 por capacidad): caso 1 en "
       + ", ".join(c for c in CASOS if clas[c] == 1) + "; caso 2 en " + ", ".join(c for c in CASOS if clas[c] == 2)
       + "; CINAC " + ", ".join(f"{c} {AUX[c]['cinac']:.2f}" for c in CASOS) + " kW")
    dv = max(abs(a["d_v01"]) for a in AUX.values())
    exige(dv <= 1.0, f"v01 no se reproduce al peso ({dv:.3f} COP)")
    ok(f"con κ·Cv + Θ y el PDE de v01 (pesos de sr) el P2P comunitario reproduce v01 de atribucion_13casos.csv (e1/S) "
       f"en los 13 casos (diferencia máxima {dv:.3f} COP)")
    d4 = max(max(abs(a["d_c4_com"]), a["d_c4_ins"]) for a in AUX.values())
    exige(d4 <= 1.0, f"C4 no se reproduce ({d4:.3f} COP)")
    ok(f"sin intercambio, en el caso 2 y con el PDE igual reproduce C4 canónico: la comunidad (hoja Resumen) y cada "
       f"institución (Por_agente), diferencia máxima {d4:.3f} COP, en los 13 casos")
    dp = max(a["d_pag"] for a in AUX.values())
    dpi = max(a["d_p2p_ins"] for a in AUX.values())
    dci = max(a["d_col_ins"] for a in AUX.values())
    exige(dpi <= 2.0 and dci <= 2.0, f"pagos internos: P2P ({dpi:.3f}) o P2P colectivo ({dci:.3f}) por institución no se reproducen")
    ok(f"pagos internos (kWh × mín(precio, techo del comprador), CAL-35): suman cero en cada hora (≤ {dp:.1e} COP) y, con "
       f"el residual por miembro (art. 25) o con el colectivo del mercado, reproducen P2P y P2P colectivo de Por_agente por "
       f"institución (≤ {dpi:.3f} y {dci:.3f} COP), en los 13 casos")
    di = max(abs(a["d_c4imp"]) for a in AUX.values())
    exige(di <= 1.0, f"C4 por importación ≠ spread_13casos.csv ({di:.3f} COP)")
    e4 = T[(T.caso == "E4") & (T.institucion == "comunidad")].iloc[0]
    exige(abs(e4.imp_C4_imp_menos_P2P_COP / M - 0.18) < 0.005, f"E4: C4 por importación − P2P = {e4.imp_C4_imp_menos_P2P_COP:.0f}")
    ok(f"C4 con el PDE por importación del mes (caso 2) = C4_importacion_COP de spread_13casos.csv (e1/C3, H-100) en los 13 "
       f"casos (≤ {di:.3f} COP); en E4 supera al mercado por {e4.imp_C4_imp_menos_P2P_COP / M:.3f} MCOP")
    da1 = max(a["d_a1"] for a in AUX.values())
    exige(da1 <= 1.0, f"C4 sin 10 % con el caso 1 para todos ≠ C4 con 11 fronteras de A1 ({da1:.3f} COP)")
    ok(f"C4 sin la regla del 10 % con κ·Cv («caso 1 para todos») = C4 con 11 fronteras del contrafáctico del art. 18 "
       f"(contrafacticos_13casos.csv, e1/A1, caso 1 en los 13) en la comunidad y por institución (≤ {da1:.3f} COP): "
       "el colectivo de las cinco en el caso 1 es el mismo objeto por las dos vías")
    s2 = max(a["d_sin10_caso2"] for a in AUX.values())
    s1 = max(a["d_c1todos"] for a in AUX.values())
    exige(s2 == 0.0 and s1 == 0.0, "C4 sin 10 % ≠ C4 en el caso 2, o «caso 1 para todos» ≠ base en el caso 1")
    ok("en el caso 2 (E4, E5, P2) C4 sin la regla del 10 % es C4 exactamente; en el caso 1, «caso 1 para todos» es la base")
    num = T.drop(columns=["caso", "institucion", "comercializador"] + SOLO_COMUNIDAD)
    finito(num, "tabla")
    es_com = T.institucion == "comunidad"
    finito(T.loc[es_com, SOLO_COMUNIDAD], "columnas de la comunidad")
    exige(bool(T.loc[~es_com, SOLO_COMUNIDAD].isna().all().all()), "columnas de la comunidad con valor en una institución")
    for c in CASOS:
        t = T[T.caso == c]
        cm = t[t.institucion == "comunidad"].iloc[0]
        ins = t[t.institucion != "comunidad"]
        for k in num.columns:
            if k.startswith(("pot_", "signo_", "n_fronteras", "suma_cap", "cinac", "cap_planta", "caso_art20")):
                continue
            exige(abs(ins[k].sum() - cm[k]) <= 1e-6 * max(1.0, abs(cm[k])), f"{c}: comunidad ≠ suma en {k}")
        exige(abs(cm.pagos_internos_COP) <= 1e-6 * max(1.0, float(ins.pagos_internos_COP.abs().sum())), f"{c}: pagos ≠ 0")
        for pre in ["", "imp_", "c1todos_"]:
            exige(abs(cm[f"{pre}dec_sin10_COP"] + cm[f"{pre}dec_intercambio_COP"] - cm[f"{pre}P2Pcom_menos_C4_COP"]) <= 1e-6,
                  f"{c}: la descomposición {pre or 'base'} no cierra")
        exige(abs(cm.pot_residual_max_kw - ins.pot_residual_max_kw.max()) == 0.0, f"{c}: potencia de la comunidad")
    ok("todo finito; la comunidad es la suma de sus instituciones; los pagos internos de la comunidad suman cero; las tres "
       "descomposiciones P2Pcom − C4 = (C4 sin 10 % − C4) + (P2Pcom − C4 sin 10 %) cierran (≤ 1e-6 COP); el Gini y las "
       "potencias de la comunidad, solo en su fila")
    # ── los dos órdenes y Shapley ───────────────────────────────────────────
    tol_v = 1.0
    fuera, dif_ig = [], {}
    for c in CASOS:
        a = AUX[c]
        x, lo, hi = a["p2pcom_c2"], a["v01ig_min"], a["v01ig_max"]
        finito([x, lo, hi], f"{c}: P2Pcom en el caso 2 y cotas de v01 igual")
        if not (lo - tol_v <= x <= hi + tol_v):
            fuera.append(f"{c}: {x:.3f} fuera de [{lo:.3f}, {hi:.3f}]")
        dif_ig[c] = x - lo if hi == lo else None
    exige(not fuera, "P2Pcom en el caso 2 fuera de [v01_igual_min, v01_igual_max]: " + "; ".join(fuera))
    iguales = {c: v for c, v in dif_ig.items() if v is not None}
    di_max = max(abs(v) for v in iguales.values())
    acot = [c for c in CASOS if dif_ig[c] is None]
    ok(f"orden inverso: el P2P comunitario con el residual en el caso 2 (κ·Cv + Θ = ded4, PDE igual) de la comunidad cae "
       f"dentro de [v01_igual_min, v01_igual_max] de atribucion_13casos.csv (e1/S) en los 13 casos; donde las cotas "
       f"coinciden ({len(iguales)} casos) a {di_max:.3f} COP como mucho; acotado en " + ", ".join(acot)
       + " (exceso en horas sin bolsa reconstruida; aquí, la bolsa de la caché de XM)")
    d2 = max(a["d_c2_caso2"] for a in AUX.values())
    com = T[es_com].set_index("caso")
    caso2 = [c for c in CASOS if clas[c] == 2]
    exige(d2 == 0.0, f"en el caso 2 el P2P comunitario en el caso 2 ≠ P2P comunitario ({d2:.3e} COP)")
    for c in caso2:
        r = com.loc[c]
        exige(r.dec_sin10_COP == 0.0 and r.inv_dec_sin10_COP == 0.0 and r.interaccion_ordenes_COP == 0.0
              and r.inv_dec_intercambio_COP == r.dec_intercambio_COP, f"{c}: los dos órdenes no coinciden en el caso 2")
    ok("en el caso 2 (" + ", ".join(caso2) + ") el P2P comunitario en el caso 2 es el P2P comunitario al peso (diferencia "
       f"{d2:.1f} COP por institución): los dos órdenes coinciden y quitar la regla del 10 % vale cero por los dos")
    pares = [("dec_sin10_COP", "dec_intercambio_COP"), ("inv_dec_sin10_COP", "inv_dec_intercambio_COP"),
             ("sh_dec_sin10_COP", "sh_dec_intercambio_COP")]
    de = 0.0
    for a_, b_ in pares:
        de = max(de, float((T[a_] + T[b_] - T.P2Pcom_menos_C4_COP).abs().max()))
    de = max(de, float((T.inv_dec_intercambio_COP - (T.P2Pcom_caso2_COP - T.C4_COP)).abs().max()),
             float((T.inv_dec_sin10_COP - (T.P2Pcom_COP - T.P2Pcom_caso2_COP)).abs().max()),
             float((T.interaccion_ordenes_COP - (T.dec_intercambio_COP - T.inv_dec_intercambio_COP)).abs().max()))
    exige(de <= 1e-6, f"las identidades de los dos órdenes no cierran ({de:.2e} COP)")
    ok(f"las dos identidades P2Pcom − C4 = (C4 sin 10 % − C4) + (P2Pcom − C4 sin 10 %) = (P2Pcom − P2Pcom caso 2) + "
       f"(P2Pcom caso 2 − C4) y la de Shapley cierran en cada fila (≤ {de:.1e} COP); la interacción es la diferencia de "
       "los dos órdenes; todo finito y la comunidad es la suma también en las columnas nuevas")
    dg = max(a["d_gini"] for a in AUX.values())
    ok(f"Gini (C-214): core.settlement.gini_index sobre Por_agente reproduce PoF_Fairness (≤ {dg:.1e}) en C1, C4, P2P, "
       "P2P colectivo, C3 y C5, los de P2P y C4 de CANON §14.6 a tres decimales y el del PPA de c2_ppa_13casos.csv "
       "(a sus seis decimales), en los 13 casos; el del P2P comunitario es la misma función sobre su beneficio por institución")
    ins = T[~es_com]
    exige(len(ins) == N_PARES, f"pares: {len(ins)}")
    exige(bool((ins.groupby("caso").size().reindex(CASOS) == [4 if c == "SINU" else 5 for c in CASOS]).all()), "pares por caso")
    exige("Udenar" not in set(ins[ins.caso == "SINU"].institucion), "SINU con Udenar")
    sobre = {x: int((ins[f"signo_P2Pcom_menos_{x}"] == 1).sum()) for x in COMPARA}
    emp = {x: int((ins[f"signo_P2Pcom_menos_{x}"] == 0).sum()) for x in COMPARA}
    ok(f"pares institución-caso: {N_PARES} (12 casos × 5 y SINU × 4, sin Udenar), la convención de «25 de 64»; el P2P "
       f"comunitario queda por encima de C4 en {sobre['C4']} (empates {emp['C4']}) y de C1 en {sobre['C1']} "
       f"(empates {emp['C1']})")
    cerca = {c: AUX[c]["caso1_menos_P2P"] for c in NUMERAL1_SIN_AGOTAR}
    ok("informativo, no se exige: en el caso 1 con todas las plantas en el numeral 1 y nadie agotando el cupo, P2Pcom − "
       "P2P canónico = " + ", ".join(f"{c} {v / M:+.4f}" for c, v in cerca.items()) + " MCOP (reparto igual del residual "
       "entre tarifas A y B en lugar de cada uno el suyo)")
    exige(set(T.comercializador) <= {"A", "B", ""}, "comercializador sin anonimizar")
    # ── salida ──────────────────────────────────────────────────────────────
    SALIDA.mkdir(parents=True, exist_ok=True)
    T.to_csv(SALIDA / "p2p_comunitario_13casos.csv", index=False, encoding="utf-8", lineterminator="\n",
             float_format="%.6f")
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
        fh.write("p2p_comunitario.py: el P2P comunitario (intercambio interno exento, residual al autogenerador "
                 "colectivo en el caso del art. 20 de la CREG 101 072 sin la regla del 10 %), propuesta regulatoria\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n" + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + guion + "\n")
        fh.write("guiones importados (sha256; sin commit si no están en HEAD):\n")
        for g in IMPORTADOS:
            datos = (RAIZ / g).read_bytes()
            est = git("status", "--short", "--untracked-files=all", "--", g)
            fh.write(f"  {g}  {len(datos)}  {hashlib.sha256(datos).hexdigest()}  {est or '(como en HEAD)'}\n")
        fh.write("registrado en HUELLAS.csv como grupo e1/PC (CANON §14.23)\n")
        fh.write("no simula: lee el almacén y los libros de la matriz del 19 de septiembre y las salidas de los "
                 "puntos S, P y C3\n")
        fh.write("CANON.md leído como texto solo para la compuerta del Gini (tabla de §14.6, a tres decimales)\n")
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
        fh.write("salvedades: propuesta regulatoria, no la norma vigente; flujos del motor fijos (exactos en el caso 1 "
                 "con plantas en el numeral 1, aproximados en E4, E5 y P2); comercializador único y perfil horario "
                 "declarado como supuestos; no se simula\n")
        fh.write("sin fecha: la hora de la corrida solo se imprime en la consola\n")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    cm = T[es_com].set_index("caso")
    print(cm[["caso_art20", "cinac_kw", "suma_cap_kw", "pot_residual_max_kw", "pot_excedente_max_kw",
              "pot_residual_comunidad_max_kw"]].round(2))
    print((cm[["C4_COP", "C4_sin10_COP", "P2Pcom_COP", "B_P2P_COP", "P2Pcom_menos_C4_COP", "dec_sin10_COP",
               "dec_intercambio_COP", "brecha_P2Pcom_menos_C1_COP", "brecha_P2Pcom_menos_C2ppa_COP",
               "brecha_P2Pcom_menos_P2P_COP"]] / M).round(3))
    print((cm[["imp_P2Pcom_menos_C4_COP", "imp_dec_sin10_COP", "imp_dec_intercambio_COP", "c1todos_P2Pcom_menos_C4_COP",
               "c1todos_dec_sin10_COP", "c1todos_dec_intercambio_COP"]] / M).round(3))
    print(cm[["gini_P2Pcom", "gini_C4_sin10", "gini_C4", "gini_P2P", "gini_C1", "gini_C2ppa"]].round(3))
    print((cm[["P2Pcom_caso2_COP", "dec_sin10_COP", "dec_intercambio_COP", "inv_dec_intercambio_COP",
               "inv_dec_sin10_COP", "sh_dec_sin10_COP", "sh_dec_intercambio_COP", "interaccion_ordenes_COP"]] / M).round(3))
    print(f"[p2p_comunitario] corrida del {t0.isoformat(timespec='seconds')}, {(_dt.datetime.now() - t0).total_seconds():.0f} s")
    print(f"[p2p_comunitario] {len(leidos)} artefactos, {len(CP.INSUMOS)} insumos, {len(todas)} compuertas; salida en {SALIDA}")
    return 0


def _n(x: float, d: int = 3) -> str:
    return CP._n(x, d)


def escribe_resumen(T: pd.DataFrame) -> None:
    cm = T[T.institucion == "comunidad"].set_index("caso")
    ins = T[T.institucion != "comunidad"]
    L = ["# P2P comunitario: la comunidad por caso", "",
         "Fuente: `p2p_comunitario_13casos.csv` de esta carpeta (guion "
         "`reformateo/documento/scripts/articulo/p2p_comunitario.py`; CANON §14.23). Cálculo derivado, sin simular. "
         "Propuesta regulatoria: el intercambio interno, con los flujos y precios del mercado, no paga cargos ni entra "
         "al fondo; el residual va al autogenerador colectivo con el PDE igual, en el caso del art. 20 de la CREG "
         "101 072 que da la capacidad instalada por usuario (CINAC, art. 18) sin la regla del 10 %.", "",
         "## Clasificación y potencias (kW)", "",
         "| Caso | Suma de plantas | CINAC | Caso del art. 20 | Residual máx. por frontera | Excedente máx. por "
         "frontera | Residual máx. de la comunidad |",
         "|---|---:|---:|:-:|---:|---:|---:|"]
    for c, r in cm.iterrows():
        L.append(f"| {c} | {_n(r.suma_cap_kw, 2)} | {_n(r.cinac_kw, 2)} | {int(r.caso_art20)} | "
                 f"{_n(r.pot_residual_max_kw, 2)} | {_n(r.pot_excedente_max_kw, 2)} | {_n(r.pot_residual_comunidad_max_kw, 2)} |")
    L += ["", "## Base: PDE igual, caso según la CINAC (MCOP)", "",
          "| Caso | C4 | C4 sin 10 % | P2P comunitario | P2P (con supuestos) | P2Pcom − C4 | Quitar el 10 % | "
          "Intercambio exento | P2Pcom − C1 | P2Pcom − C2 (PPA) | P2Pcom − P2P | Gini P2Pcom | Gini C4 | Gini P2P |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in cm.iterrows():
        L.append(f"| {c} | " + " | ".join(_n(r[k] / M) for k in [
            "C4_COP", "C4_sin10_COP", "P2Pcom_COP", "B_P2P_COP", "P2Pcom_menos_C4_COP", "dec_sin10_COP",
            "dec_intercambio_COP", "brecha_P2Pcom_menos_C1_COP", "brecha_P2Pcom_menos_C2ppa_COP",
            "brecha_P2Pcom_menos_P2P_COP"]) + " | " + " | ".join(_n(r[k]) for k in ["gini_P2Pcom", "gini_C4", "gini_P2P"]) + " |")
    L += ["", "## Los dos órdenes y Shapley (MCOP)", "",
          "Las dos reformas se solapan, de modo que la atribución de P2Pcom − C4 a cada una depende del orden (como los "
          "supuestos del punto S, CANON §14.21). Orden directo: primero quitar la regla del 10 % (C4 sin 10 % − C4) y "
          "después el intercambio exento (P2Pcom − C4 sin 10 %). Orden inverso: primero el intercambio exento con la regla "
          "del 10 % vigente, es decir, el P2P comunitario con el residual en el caso 2 (κ·Cv + Θ, PDE igual; «P2Pcom caso "
          "2» − C4), y después quitar la regla (P2Pcom − P2Pcom caso 2). Shapley: la media de los dos órdenes. "
          "Interacción: quitar la regla por el inverso menos por el directo. Se citan los dos órdenes o Shapley, nunca uno "
          "solo.", "",
          "| Caso | Caso del art. 20 | P2Pcom − C4 | P2Pcom caso 2 | Directo: quitar el 10 % | Directo: intercambio | "
          "Inverso: intercambio | Inverso: quitar el 10 % | Shapley: quitar el 10 % | Shapley: intercambio | Interacción | "
          "Quitar el 10 %: directo (%) | Quitar el 10 %: inverso (%) | Quitar el 10 %: Shapley (%) | Clase |",
          "|---|:-:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    clases = {}
    for c, r in cm.iterrows():
        clases[c] = clasifica_ordenes(r.dec_sin10_COP, r.dec_intercambio_COP, r.inv_dec_sin10_COP,
                                      r.inv_dec_intercambio_COP)
        tot = r.P2Pcom_menos_C4_COP
        L.append(f"| {c} | {int(r.caso_art20)} | " + " | ".join(_n(r[k] / M) for k in [
            "P2Pcom_menos_C4_COP", "P2Pcom_caso2_COP", "dec_sin10_COP", "dec_intercambio_COP", "inv_dec_intercambio_COP",
            "inv_dec_sin10_COP", "sh_dec_sin10_COP", "sh_dec_intercambio_COP", "interaccion_ordenes_COP"]) + " | "
            + " | ".join(_n(100 * r[k] / tot, 0) for k in ["dec_sin10_COP", "inv_dec_sin10_COP", "sh_dec_sin10_COP"])
            + f" | {CLASES_ORDEN[clases[c]]} |")
    L += ["", "Clasificación de los casos con los dos órdenes:", ""]
    for k, rot in CLASES_ORDEN.items():
        lista = [c for c in cm.index if clases[c] == k]
        L.append(f"- {rot[0].upper() + rot[1:]}: " + (", ".join(lista) if lista else "ninguno") + f" ({len(lista)}).")
    sh = cm.sh_dec_sin10_COP.sum() / M
    L += ["", f"En los 13 casos, P2Pcom − C4 suma {_n(cm.P2Pcom_menos_C4_COP.sum() / M, 2)} MCOP: quitar la regla del 10 % "
          f"pone {_n(cm.dec_sin10_COP.sum() / M, 2)} por el orden directo, {_n(cm.inv_dec_sin10_COP.sum() / M, 2)} por el "
          f"inverso y {_n(sh, 2)} por Shapley; el intercambio exento, {_n(cm.dec_intercambio_COP.sum() / M, 2)}, "
          f"{_n(cm.inv_dec_intercambio_COP.sum() / M, 2)} y {_n(cm.sh_dec_intercambio_COP.sum() / M, 2)}."]
    L += ["", "## Brechas frente a los demás mecanismos (MCOP)", "",
          "| Caso | − P2P colectivo | − C5 | − C3 |", "|---|---:|---:|---:|"]
    for c, r in cm.iterrows():
        L.append(f"| {c} | " + " | ".join(_n(r[f'brecha_P2Pcom_menos_{x}_COP'] / M) for x in ["P2P_colectivo", "C5", "C3"]) + " |")
    L += ["", "## Sensibilidades (MCOP)", "",
          "PDE por importación: el P2P comunitario con el PDE de cada mes proporcional a la importación residual y C4 con "
          "el de la importación (las dos a la vez). Caso 1 para todos: κ·Cv en los 13 casos (segunda reforma, sin base "
          "vigente).", "",
          "| Caso | Imp.: P2Pcom − C4 | Imp.: quitar el 10 % | Imp.: intercambio | Imp.: C4 − P2P | Imp.: P2Pcom − P2P | "
          "C1 todos: P2Pcom − C4 | C1 todos: quitar el 10 % | C1 todos: intercambio |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in cm.iterrows():
        L.append(f"| {c} | " + " | ".join(_n(r[k] / M) for k in [
            "imp_P2Pcom_menos_C4_COP", "imp_dec_sin10_COP", "imp_dec_intercambio_COP", "imp_C4_imp_menos_P2P_COP",
            "imp_P2Pcom_menos_P2P_COP", "c1todos_P2Pcom_menos_C4_COP", "c1todos_dec_sin10_COP",
            "c1todos_dec_intercambio_COP"]) + " |")
    L += ["", "## Pares institución-caso", "",
          f"Pares: {len(ins)} (12 casos con cinco instituciones y SINU con cuatro, sin Udenar). Con el P2P comunitario por "
          "encima (empate a menos de 1 COP no cuenta):", "",
          "| Frente a | Pares por encima |", "|---|---:|"]
    for x in COMPARA:
        L.append(f"| {x} | {int((ins[f'signo_P2Pcom_menos_{x}'] == 1).sum())} |")
    L += ["", "Salvedades: propuesta regulatoria (intercambio exento de cargos y sin la regla del 10 % para colectivos "
          "pequeños); flujos del motor fijos, exactos en el caso 1 con plantas en el numeral 1 y aproximados en E4, E5 y "
          "P2; comercializador único (art. 10) y perfil horario declarado como supuestos; no se simula nada.", ""]
    (SALIDA / "resumen.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    sys.exit(main())
