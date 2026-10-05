"""
prevision_corte.py — Cuánto del mercado P2P depende de conocer el mes de
antemano: las horas en que, en tiempo real, no se sabe si el vendedor pasó su
corte
===============================================================================
Actividades 2.1 y 3.3 de la propuesta. Cálculo DERIVADO del canon: no simula
el mercado ni usa el servidor. Lee artefactos con huella en
`Documentos/canon_2026-09/HUELLAS.csv` (con `atribucion_supuestos.lee`) y usa
las funciones del propio proyecto (`core.opciones_externas.residual_proporcional`
y `reparto_anexo4`), las mismas con las que el motor fija el piso
(`piso_residual`).

LA PREGUNTA (del autor, 2026-10-04). El piso del vendedor es la permuta antes
de su hora del corte hx del Anexo 4 y la bolsa desde ella. hx es la hora en que
la inyección acumulada del mes alcanza la importación TOTAL del mes, de modo
que el motor la calcula con el mes completo, como si se conociera desde su
inicio. La liquidación del art. 25 también usa el mes completo, pero al
cierre, que es lo que hace la norma. Lo que en tiempo real no se conoce es el
estado del vendedor en cada hora, que el mercado necesita para fijar su piso.

LO QUE SE SABE EN TIEMPO REAL. En la hora k se conocen la inyección y la
importación acumuladas del mes hasta k. Si la inyección acumulada va por
debajo de la importación acumulada, la hora es crédito con certeza, porque la
importación del mes solo puede crecer. Si la alcanza o la pasa, la hora es
incierta: será crédito solo si el miembro importa más en lo que queda del mes.
Nunca es exceso con certeza antes del cierre.

QUÉ SE MIDE. Con las mismas series residuales aproximadas con que el motor fija
el corte del piso (`residual_proporcional`: el lado corto de cada hora repartido
en proporción a la inyección y a la importación), cada hora-vendedor (miembro
con sobrante, s > 0) cae en una de tres clases:
    seguro    : crédito con certeza en tiempo real;
    incierto-crédito : incierta en tiempo real y crédito con el mes completo;
    incierto-exceso  : incierta en tiempo real y exceso con el mes completo
                       (tras el corte del piso que usó el motor).
Por clase: horas-vendedor, sobrante (kWh), energía vendida dentro (kWh) y ahorro
del intercambio de lo vendido (prima del vendedor + ahorro del comprador, COP,
la banda de CANON §14.8 y §14.25). Una regla sin previsión que tome toda hora
incierta como crédito se equivoca en la clase incierto-exceso; una que la tome
como bolsa, en la clase incierto-crédito.

COMPUERTAS (falla en voz alta; ningún `except`; todo finito):
  - el corte recalculado con `residual_proporcional` y `reparto_anexo4` sobre G y
    D del almacén es el del piso del motor (la marca de `corte_fondo_derivados`,
    piso ≠ permuta) en las horas con sobrante;
  - ninguna hora segura está tras el corte (por construcción del Anexo 4);
  - las tres clases suman las horas-vendedor, el sobrante, la energía vendida y
    el ahorro de cada institución y de la comunidad;
  - la energía vendida es la transada de `atribucion_13casos.csv` (e1/S) y el
    ahorro, la banda de `descomposicion_13casos.csv` (e1/C5), por comunidad;
  - donde nadie agota el cupo (E0, P2, K1, CV2 y SINU) no hay clase
    incierto-exceso.

Escribe en SALIDAS_SERVIDOR/prevision_corte_2026-10-04/:

    prevision_13casos.csv   caso × institución (y comunidad)
    resumen.md              la comunidad por caso
    procedencia.txt         commit, versiones, huellas y compuertas, sin fecha

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/prevision_corte.py

SALVEDADES: mide la exposición del supuesto, no una regla en tiempo real
simulada: los flujos son los del motor con el piso del mes completo. El
residual es el aproximado del piso. No usa pronósticos.

Actividades 2.1 y 3.3.
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
import corte_fondo_derivados as CF  # noqa: E402
from core.opciones_externas import (precio_permuta_por_periodo, reparto_anexo4,  # noqa: E402
                                    residual_proporcional)

SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
SALIDA = SALIDAS / "prevision_corte_2026-10-04"
CASOS = AS.CASOS
SIN_CORTE = AS.SIN_AGOTAR
M = 1e6
UMBRAL_SOBRANTE = 1e-9
CLASES = ("seguro", "incierto_credito", "incierto_exceso")
MODULOS = ["core/opciones_externas.py"]
IMPORTADOS = ["reformateo/documento/scripts/articulo/atribucion_supuestos.py",
              "reformateo/documento/scripts/articulo/corte_fondo_derivados.py"]

COMPUERTAS: list[str] = []


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[prevision] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    COMPUERTAS.append(msg)
    print(f"[prevision]   OK  {msg}")


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


# ── Funciones puras (las prueba tests/test_prevision_corte.py) ──────────────
def seguro_en_linea(iny: np.ndarray, ret: np.ndarray, mes: np.ndarray) -> np.ndarray:
    """(N, T) True donde, con lo conocido hasta la hora k inclusive, la hora es
    crédito con certeza: la inyección acumulada del mes hasta k es menor que la
    importación acumulada hasta k, que solo puede crecer hasta el cierre."""
    iny, ret = np.asarray(iny, dtype=float), np.asarray(ret, dtype=float)
    exige(iny.shape == ret.shape, "seguro_en_linea: formas distintas")
    exige(bool(np.isfinite(iny).all() and np.isfinite(ret).all()), "seguro_en_linea: no finitos")
    out = np.zeros(iny.shape, dtype=bool)
    mes = np.asarray(mes)
    for m in np.unique(mes):
        h = np.flatnonzero(mes == m)
        out[:, h] = np.cumsum(iny[:, h], axis=1) < np.cumsum(ret[:, h], axis=1)
    return out


def credito_pronosticado(iny: np.ndarray, ret: np.ndarray, mes: np.ndarray) -> np.ndarray:
    """(N, T) True donde un pronóstico simple, con lo conocido hasta la hora k
    inclusive, da la hora por crédito: la importación del mes se extrapola en
    línea recta con la observada, R = R_k · (horas del mes / horas transcurridas),
    nunca por debajo de R_k, y la hora es crédito si la inyección acumulada va
    por debajo de R. No usa nada posterior a k salvo la longitud del mes."""
    iny, ret = np.asarray(iny, dtype=float), np.asarray(ret, dtype=float)
    exige(iny.shape == ret.shape, "credito_pronosticado: formas distintas")
    out = np.zeros(iny.shape, dtype=bool)
    mes = np.asarray(mes)
    for m in np.unique(mes):
        h = np.flatnonzero(mes == m)
        t = np.arange(1, h.size + 1, dtype=float)
        rk = np.cumsum(ret[:, h], axis=1)
        out[:, h] = np.cumsum(iny[:, h], axis=1) < rk * (h.size / t)[None, :]
    return out


def clases(sobrante: np.ndarray, seguro: np.ndarray, tras: np.ndarray) -> np.ndarray:
    """(N, T) entero: −1 sin sobrante; 0 seguro; 1 incierto y crédito con el
    mes completo; 2 incierto y exceso con el mes completo. Falla si una hora
    segura está tras el corte."""
    sobrante = np.asarray(sobrante, dtype=bool)
    seguro, tras = np.asarray(seguro, dtype=bool), np.asarray(tras, dtype=bool)
    exige(not bool((seguro & tras & sobrante).any()), "una hora segura en tiempo real está tras el corte")
    k = np.full(sobrante.shape, -1, dtype=int)
    k[sobrante & seguro] = 0
    k[sobrante & ~seguro & ~tras] = 1
    k[sobrante & ~seguro & tras] = 2
    return k


def por_clase(x: np.ndarray, k: np.ndarray) -> dict:
    """Suma de `x` en cada clase (0, 1, 2), con su total."""
    x, k = np.asarray(x, dtype=float), np.asarray(k)
    exige(x.shape == k.shape, "por_clase: formas distintas")
    out = {c: float(x[k == i].sum()) for i, c in enumerate(CLASES)}
    out["total"] = float(x[k >= 0].sum())
    return out


# ── Un caso ─────────────────────────────────────────────────────────────────
def caso(c: str, TT, cap, desc, atr) -> tuple[list[dict], dict]:
    L = AS.carga(c, TT, cap)
    ags, N, mes = L["ags"], L["N"], L["mes"]
    G, D, s = L["G"], L["D"], L["s"]
    perm = precio_permuta_por_periodo(L["CU"], L["ded1"], mes)
    tras_motor = CF.marca_corte(L["piso"], perm)
    sh, dh = residual_proporcional(G, D)
    _, _, en_perm = reparto_anexo4(sh, dh, mes)
    tras = ~en_perm
    sob = s > UMBRAL_SOBRANTE
    n_dif = int((tras[sob] != tras_motor[sob]).sum())
    exige(n_dif == 0, f"{c}: el corte recalculado difiere del piso del motor en {n_dif} horas-vendedor")
    seg = seguro_en_linea(sh, dh, mes)
    k = clases(sob, seg, tras)
    pron = credito_pronosticado(sh, dh, mes)
    exige(bool((pron | ~seg).all()), f"{c}: el pronóstico da por exceso una hora segura")
    # error del pronóstico: 1 = lo da por exceso y es crédito; 2 = lo da por crédito y es exceso
    e = np.full(k.shape, -1, dtype=int)
    e[sob] = 0
    e[sob & ~pron & ~tras] = 1
    e[sob & pron & tras] = 2
    if c in SIN_CORTE:
        exige(not bool((k == 2).any()), f"{c}: horas incierto-exceso donde nadie agota el cupo")

    fl = AS.almacen(c, "flujos").astype({x: "float64" for x in ["kwh", "prima_vendedor", "ahorro_comprador"]})
    CF.finito(fl[["kwh", "prima_vendedor", "ahorro_comprador"]].to_numpy(), f"{c} flujos")
    ix = {a: i for i, a in enumerate(ags)}
    iv = fl.vendedor.map(ix).to_numpy(dtype=int)
    h = fl.hora.to_numpy(dtype=int)
    kw = fl.kwh.to_numpy()
    b = (fl.prima_vendedor + fl.ahorro_comprador).to_numpy()
    kf = k[iv, h]
    exige(bool((kf >= 0).all()), f"{c}: un flujo sale de un vendedor sin sobrante")

    a_ = atr.loc[c]
    de = desc[desc.caso == c].set_index("agente")
    d_e = abs(float(kw.sum()) - float(a_.transado_kwh))
    d_b = abs(float(b.sum()) - float(de.loc["comunidad", "banda"]))
    exige(d_e <= 1e-3 and d_b <= 1.0, f"{c}: energía ({d_e:.2e} kWh) o ahorro ({d_b:.3f} COP) ≠ canon")

    filas = []
    for i in list(range(N)) + ["comunidad"]:
        if i == "comunidad":
            selk, self_ = np.ones(k.shape, bool), np.ones(len(fl), bool)
            nombre = "comunidad"
        else:
            selk = np.zeros(k.shape, bool)
            selk[i] = True
            self_ = iv == i
            nombre = ags[i]
        f = dict(caso=c, institucion=nombre)
        kk = np.where(selk, k, -1)
        for qn, x in [("horas", np.ones(k.shape)), ("sobrante_kwh", s)]:
            pc = por_clase(x, kk)
            f[f"{qn}_total"] = pc["total"]
            for cl in CLASES:
                f[f"{qn}_{cl}"] = pc[cl]
        kfs = np.where(self_, kf, -1)
        for qn, x in [("vendido_kwh", kw), ("ahorro_COP", b)]:
            pc = por_clase(x, kfs)
            f[f"{qn}_total"] = pc["total"]
            for cl in CLASES:
                f[f"{qn}_{cl}"] = pc[cl]
        ee = np.where(selk, e, -1)
        efs = np.where(self_, e[iv, h], -1)
        for qn, x, kk_ in [("horas", np.ones(k.shape), ee), ("vendido_kwh", kw, efs), ("ahorro_COP", b, efs)]:
            f[f"{qn}_pronostico_yerra_a_bolsa"] = float(x[kk_ == 1].sum())
            f[f"{qn}_pronostico_yerra_a_credito"] = float(x[kk_ == 2].sum())
        for qn in ["horas", "sobrante_kwh", "vendido_kwh", "ahorro_COP"]:
            suma = sum(f[f"{qn}_{cl}"] for cl in CLASES)
            tol = 1.0 if qn == "ahorro_COP" else 1e-6
            exige(abs(suma - f[f"{qn}_total"]) <= tol * max(1.0, abs(f[f"{qn}_total"])) if qn != "horas"
                  else suma == f[f"{qn}_total"], f"{c} {nombre}: las clases no suman el total de {qn}")
        filas.append(f)
    com = filas[-1]
    exige(abs(com["vendido_kwh_total"] - float(kw.sum())) <= 1e-6, f"{c}: energía vendida por clases ≠ flujos")
    info = dict(d_e=d_e, d_b=d_b)
    return filas, info


# ── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    t0 = _dt.datetime.now()
    sucio_mod = git("status", "--short", "--", *MODULOS)
    exige(sucio_mod == "", f"módulos de producción con cambios sin commit:\n{sucio_mod}")
    ok("los módulos de producción que se importan están como en HEAD: " + ", ".join(MODULOS))
    print("[prevision] 1. tarifas, capacidades y artefactos del canon")
    TT = AS.tarifas()
    cap = AS.capacidades()
    desc = pd.read_csv(AS.lee(CF.F_DESC, "e1/C5"))
    atr = pd.read_csv(AS.lee(CF.F_ATR, "e1/S")).set_index("caso")
    print("[prevision] 2. los 13 casos")
    filas, info = [], {}
    for c in CASOS:
        fc, info[c] = caso(c, TT, cap, desc, atr)
        filas += fc
        r = fc[-1]
        inc_e = r["vendido_kwh_incierto_credito"] + r["vendido_kwh_incierto_exceso"]
        print(f"[prevision]   {c}: incierto {inc_e:,.1f} de {r['vendido_kwh_total']:,.1f} kWh vendidos dentro; "
              f"horas-vendedor inciertas {r['horas_incierto_credito'] + r['horas_incierto_exceso']:.0f} de "
              f"{r['horas_total']:.0f}")
    T = pd.DataFrame(filas)
    mx = {x: max(i_[x] for i_ in info.values()) for x in ["d_e", "d_b"]}
    ok("el corte recalculado con residual_proporcional y reparto_anexo4 sobre G y D del almacén es el del piso del "
       "motor (piso ≠ permuta) en todas las horas con sobrante de los 13 casos")
    ok("el pronóstico lineal de la importación del mes nunca da por exceso una hora segura, en los 13 casos")
    ok("ninguna hora segura en tiempo real está tras el corte; donde nadie agota el cupo (E0, P2, K1, CV2 y SINU) no "
       "hay horas incierto-exceso")
    ok(f"las tres clases suman las horas-vendedor, el sobrante, la energía vendida y el ahorro de cada institución y "
       f"de la comunidad; la energía vendida es la transada de atribucion_13casos.csv (e1/S, ≤ {mx['d_e']:.1e} kWh) y "
       f"el ahorro la banda de descomposicion_13casos.csv (e1/C5, ≤ {mx['d_b']:.3f} COP)")
    CF.finito(T.drop(columns=["caso", "institucion"]).to_numpy(dtype=float), "tabla")
    exige(len(T) == 77, f"{len(T)} filas, no 77")
    exige("cedenar" not in T.to_csv().lower() and "asc," not in T.to_csv().lower(), "comercializador nombrado")
    SALIDA.mkdir(parents=True, exist_ok=True)
    T.to_csv(SALIDA / "prevision_13casos.csv", index=False, encoding="utf-8", lineterminator="\n", float_format="%.6f")
    escribe_resumen(T)
    guion = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    sucio = git("status", "--short", "--untracked-files=all", "--", guion)
    leidos = list(AS.LEIDOS)
    todas = [f"(atribucion_supuestos) {x}" for x in AS.COMPUERTAS] + COMPUERTAS
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("prevision_corte.py: las horas-vendedor en que, en tiempo real, no se sabe si el vendedor pasó su "
                 "corte hx, y la energía y el ahorro del intercambio que caen en ellas, derivados sin simular\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n" + (sucio or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + guion + "\n")
        fh.write("guiones importados (sha256; sin commit si no están en HEAD):\n")
        for g in IMPORTADOS:
            datos = (RAIZ / g).read_bytes()
            est = git("status", "--short", "--untracked-files=all", "--", g)
            fh.write(f"  {g}  {len(datos)}  {hashlib.sha256(datos).hexdigest()}  {est or '(como en HEAD)'}\n")
        fh.write("no simula: lee los almacenes de la matriz del 19 de septiembre y las salidas de los puntos C5 y S\n")
        fh.write(f"huellas: {AS.HUELLAS.relative_to(RAIZ).as_posix()}; {len(leidos)} artefactos leídos, todos con la "
                 "huella comprobada:\n")
        for g, r in leidos:
            fh.write(f"  {g}  {r}\n")
        fh.write(f"compuertas: {len(todas)}, todas OK:\n")
        for cpt in todas:
            fh.write(f"  OK  {cpt}\n")
        fh.write(f"filas de prevision_13casos.csv: {len(T)}\n")
        fh.write("salvedades: mide la exposición del supuesto de conocer el mes, no simula una regla en tiempo real; "
                 "flujos del motor fijos; residual aproximado del piso; sin pronósticos\n")
        fh.write("sin fecha: la hora de la corrida solo se imprime en la consola\n")
    print(f"[prevision] corrida del {t0.isoformat(timespec='seconds')}, {(_dt.datetime.now() - t0).total_seconds():.0f} s")
    print(f"[prevision] {len(leidos)} artefactos, {len(todas)} compuertas; salida en {SALIDA}")
    return 0


def _pc(a: float, b: float) -> float:
    return 100.0 * a / b if b > 0 else float("nan")


def escribe_resumen(T: pd.DataFrame) -> None:
    n = CF._n
    C = T[T.institucion == "comunidad"].set_index("caso")
    L = ["# Cuánto del mercado P2P depende de conocer el mes de antemano: la comunidad por caso", "",
         "Fuente: `prevision_13casos.csv` de esta carpeta (guion `reformateo/documento/scripts/articulo/"
         "prevision_corte.py`). Derivado, sin simular. Una hora-vendedor es **segura** si en tiempo real ya se sabe que "
         "es crédito (la inyección acumulada del mes va por debajo de la importación acumulada); si no, es **incierta**, "
         "y con el mes completo resulta crédito o exceso.", "",
         "| Caso | Horas-vendedor | Inciertas (%) | Vendido dentro (kWh) | Incierto (%) | de ello crédito (%) | "
         "de ello exceso (%) | Ahorro (MCOP) | Ahorro incierto (%) | Pronóstico: vendido mal clasificado (%) | "
         "Pronóstico: ahorro mal clasificado (%) |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in C.iterrows():
        hi = r.horas_incierto_credito + r.horas_incierto_exceso
        vi = r.vendido_kwh_incierto_credito + r.vendido_kwh_incierto_exceso
        ai = r.ahorro_COP_incierto_credito + r.ahorro_COP_incierto_exceso
        L.append(f"| {c} | {n(r.horas_total, 0)} | {n(_pc(hi, r.horas_total), 1)} | {n(r.vendido_kwh_total, 1)} | "
                 f"{n(_pc(vi, r.vendido_kwh_total), 1)} | {n(_pc(r.vendido_kwh_incierto_credito, r.vendido_kwh_total), 1)} | "
                 f"{n(_pc(r.vendido_kwh_incierto_exceso, r.vendido_kwh_total), 1)} | {n(r.ahorro_COP_total / M, 3)} | "
                 f"{n(_pc(ai, r.ahorro_COP_total), 1)} | "
                 f"{n(_pc(r.vendido_kwh_pronostico_yerra_a_bolsa + r.vendido_kwh_pronostico_yerra_a_credito, r.vendido_kwh_total), 1)} | "
                 f"{n(_pc(r.ahorro_COP_pronostico_yerra_a_bolsa + r.ahorro_COP_pronostico_yerra_a_credito, r.ahorro_COP_total), 1)} |")
    L += ["", "Pronóstico: la importación del mes extrapolada en línea recta con la observada hasta la hora (nunca "
          "menos que ella); mal clasificado = la hora que da por exceso y es crédito, o al revés.", "",
          "«de ello crédito»: lo que una regla sin previsión que tome la hora incierta como bolsa valoraría mal; "
          "«de ello exceso»: lo que una que la tome como crédito valoraría mal. Salvedades: flujos del motor con el piso "
          "del mes completo; residual aproximado del piso; no se simula una regla en tiempo real.", ""]
    (SALIDA / "resumen.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    sys.exit(main())
