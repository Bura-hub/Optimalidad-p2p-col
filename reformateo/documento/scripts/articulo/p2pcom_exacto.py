"""
p2pcom_exacto.py — El P2P colectivo exacto: el mercado con el piso del fondo
(la matriz de trece casos con `--piso-mecanismo p2pcom`) liquidado como P2P
colectivo
===============================================================================
Actividades 2.1 y 2.2 de la propuesta. No simula: lee los almacenes de
`SALIDAS_SERVIDOR/entrega_matriz_p2pcom_<fecha>/SALIDAS_SERVIDOR/matriz_p2pcom/`
y los artefactos del canon con huella (tarifas, capacidades, bolsa y la salida
del punto PC, grupo e1/PC, y de H2 exacto, grupo e1/H2).

QUÉ ES (CANON §14.23): cada hora el mercado P2P resuelve quién vende a quién y
a qué precio, sin cargos; el residual entra al fondo del autogenerador
colectivo, se reparte en partes iguales y se liquida contra la importación
residual de cada miembro con la deducción del caso del art. 20 sin la regla
del 10 %.

POR QUÉ «EXACTO». El P2P colectivo del canon (e1/PC) se liquidó sobre los
flujos del mercado formado con el piso de C1. En el P2P colectivo el kWh que
no se vende vale para la comunidad su parte igual del fondo: el crédito de la
tarifa de cada miembro menos la deducción del fondo, mientras le quede
importación en el mes, y la bolsa desde su corte (decisión del 2026-10-05,
C-307, ADR 0063; `core.opciones_externas.piso_fondo_igual`). La matriz se
resolvió con ese piso; aquí se liquida sobre esos flujos.

COMPUERTAS (falla en voz alta; ningún `except`; todo finito):
  * la liquidación de aquí, con el almacén del canon, reproduce P2Pcom_COP de
    p2p_comunitario_13casos.csv (e1/PC) por institución en los trece casos;
  * la matriz se corrió con el piso p2pcom (fichero MECANISMO);
  * energía: lo vendido es lo comprado en cada hora, los pagos internos suman
    cero, el fondo se conserva y el balance de cada mes cierra;
  * la comunidad es la suma de sus instituciones.

Escribe en SALIDAS_SERVIDOR/p2pcom_exacto_<fecha>/: p2pcom_exacto_13casos.csv,
resumen.md y procedencia.txt (con el sha256 de cada parte de los almacenes).

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/p2pcom_exacto.py --entrega entrega_matriz_p2pcom_<fecha>
"""
from __future__ import annotations

import argparse
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
import h2_exacto as HX  # noqa: E402
import hibrido_por_planta as HP  # noqa: E402
import p2p_comunitario as PC  # noqa: E402

SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
F_PC = "p2p_comunitario_2026-10-02/p2p_comunitario_13casos.csv"
F_H2 = "h2_exacto_2026-10-05/h2_exacto_13casos.csv"
CASOS = AS.CASOS
CONTRA = ["C4", "C1", "P2P"]
M = 1e6

COMPUERTAS: list[str] = []
LEIDOS: list[tuple[str, int, str]] = []
MATRIZ = None


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[p2pcom_exacto] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    COMPUERTAS.append(msg)
    print(f"[p2pcom_exacto]   OK  {msg}")


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


def almacen_nuevo(c: str, tabla: str) -> pd.DataFrame:
    d = MATRIZ / c / "almacen" / "m1" / tabla
    partes = sorted(d.glob("*.parquet"))
    exige(len(partes) >= 1, f"{c}: sin partes de «{tabla}» en {d}")
    out = []
    for p in partes:
        datos = p.read_bytes()
        r = p.relative_to(SALIDAS).as_posix()
        if r not in [x[0] for x in LEIDOS]:
            LEIDOS.append((r, len(datos), hashlib.sha256(datos).hexdigest()))
        out.append(pd.read_parquet(p))
    return pd.concat(out, ignore_index=True)


def carga(c: str, TT, cap, nuevo: bool):
    if not nuevo:
        return AS.carga(c, TT, cap), AS.almacen(c, "flujos")
    original = AS.almacen
    AS.almacen = almacen_nuevo
    try:
        L = AS.carga(c, TT, cap)
    finally:
        AS.almacen = original
    return L, almacen_nuevo(c, "flujos")


def liquida_p2pcom(L: dict, fl: pd.DataFrame, pb: np.ndarray, qué: str) -> dict:
    """El P2P colectivo sobre los flujos `fl`: intercambio exento, residual al
    fondo con el reparto igual y la deducción del caso sin la regla del 10 %."""
    N, ags, mes = L["N"], L["ags"], L["mes"]
    s, d, v, q, CU, au = L["s"], L["d"], L["v"], L["q"], L["CU"], L["au"]
    kap, Cv, Th = L["kap"], L["Cv"], L["Th"]
    T = s.shape[1]
    fl = fl.astype({"kwh": "float64", "precio": "float64", "techo_comprador": "float64"})
    pag = PC.pagos_internos(fl.vendedor.to_numpy(), fl.comprador.to_numpy(), fl.hora.to_numpy(), fl.kwh.to_numpy(),
                            fl.precio.to_numpy(), fl.techo_comprador.to_numpy(), ags, T)
    HP.finito(pag, f"{qué} pagos")
    cs, _, suma = PC.caso_art20_sin_10(L["capk"], N)
    exige(suma <= PC.AGPE_LIMIT_KW, f"{qué}: la comunidad pasa de 1 MW")
    ded = PC.deduccion_caso(cs, kap, Cv, Th)
    R = HP.valor_hibrido(au, s, d, v, q, CU, pag, np.zeros((N, T)), ded, mes, pb, PC.igual(N, mes), qué)
    R.update(pag=pag, caso=cs)
    return R


def main() -> int:
    global MATRIZ
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrega", required=True, help="carpeta de la entrega dentro de SALIDAS_SERVIDOR/")
    a = ap.parse_args()
    t0 = _dt.datetime.now()
    MATRIZ = SALIDAS / a.entrega / "SALIDAS_SERVIDOR" / "matriz_p2pcom"
    fecha = a.entrega.rsplit("_", 1)[-1]
    SALIDA = SALIDAS / f"p2pcom_exacto_{fecha}"
    exige(MATRIZ.is_dir(), f"no existe {MATRIZ}: trae la entrega del servidor")
    mec = (MATRIZ / "MECANISMO").read_text(encoding="utf-8").strip()
    exige(mec == "p2pcom", f"la matriz se corrió con el piso «{mec}», no con p2pcom")
    sucio = git("status", "--short", "--", *HP.MODULOS)
    exige(sucio == "", f"módulos de producción con cambios sin commit:\n{sucio}")
    print("[p2pcom_exacto] 1. tarifas, capacidades, bolsa, el punto PC y H2 exacto")
    TT = AS.tarifas()
    cap = AS.capacidades()
    idx, _ = CP.horizonte()
    pb = CP.bolsa(idx)
    exige(pb.shape == (6144,) and bool(np.isfinite(pb).all()), "bolsa incompleta")
    PCT = pd.read_csv(AS.lee(F_PC, "e1/PC"), keep_default_na=False, na_values=[""])
    H2T = pd.read_csv(AS.lee(F_H2, "e1/H2"), keep_default_na=False, na_values=[""])
    print("[p2pcom_exacto] 2. los trece casos")
    filas, d_ref, d_en = [], 0.0, 0.0
    for c in CASOS:
        ref = PCT[PCT.caso == c].set_index("institucion")
        h2 = H2T[H2T.caso == c].set_index("institucion")
        L0, fl0 = carga(c, TT, cap, nuevo=False)
        R0 = liquida_p2pcom(L0, fl0, pb, f"{c} canon")
        exige(list(ref.index) == L0["ags"] + ["comunidad"], f"{c}: instituciones de e1/PC")
        d_ref = max(d_ref, float(np.abs(R0["val"] - ref.loc[L0["ags"], "P2Pcom_COP"].to_numpy(float)).max()))
        L, fl = carga(c, TT, cap, nuevo=True)
        exige(L["ags"] == L0["ags"], f"{c}: instituciones distintas en el almacén nuevo")
        R = liquida_p2pcom(L, fl, pb, f"{c} exacto")
        HP.finito(R["H"], f"{c} exacto")
        d_en = max(d_en, HX.energia(L0, R0, f"{c} canon"), HX.energia(L, R, f"{c} exacto"))
        ags, N = L["ags"], L["N"]
        for i in list(range(N)) + ["comunidad"]:
            sel = slice(None) if i == "comunidad" else slice(i, i + 1)
            nombre = "comunidad" if i == "comunidad" else ags[i]
            r, rh = ref.loc[nombre], h2.loc[nombre]
            f = dict(caso=c, institucion=nombre,
                     comercializador="" if pd.isna(r.comercializador) else str(r.comercializador),
                     caso_art20=int(R["caso"]),
                     vendido_dentro_kwh=float(L["v"][sel].sum()), comprado_dentro_kwh=float(L["q"][sel].sum()),
                     vendido_dentro_canon_kwh=float(L0["v"][sel].sum()),
                     residual_iny_kwh=float(R["sr"][sel].sum()), credito_kwh=float(R["cr"][sel].sum()),
                     exceso_kwh=float(R["ex"][sel].sum()), pagos_internos_COP=float(R["pag"][sel].sum()),
                     P2Pcom_exacto_COP=float(R["val"][sel].sum()), P2Pcom_aprox_COP=float(r.P2Pcom_COP),
                     H2_exacto_COP=float(rh.H2_exacto_COP))
            for x in CONTRA:
                f[f"B_{x}_COP"] = float(r[f"B_{x}_COP"])
            for x in CONTRA + ["H2_exacto"]:
                ref_x = f[f"B_{x}_COP"] if x in CONTRA else f["H2_exacto_COP"]
                b = f["P2Pcom_exacto_COP"] - ref_x
                f[f"brecha_P2Pcom_exacto_menos_{x}_COP"] = b
                f[f"signo_P2Pcom_exacto_menos_{x}"] = int(CP.signo_brecha(b))
            f["brecha_P2Pcom_exacto_menos_aprox_COP"] = f["P2Pcom_exacto_COP"] - f["P2Pcom_aprox_COP"]
            f["gini_P2Pcom_exacto"] = CP.gini(R["val"]) if i == "comunidad" else np.nan
            filas.append(f)
        cm = filas[-1]
        print(f"[p2pcom_exacto]   {c}: exacto {cm['P2Pcom_exacto_COP'] / M:9.3f} MCOP, aprox "
              f"{cm['P2Pcom_aprox_COP'] / M:9.3f}, H2 exacto {cm['H2_exacto_COP'] / M:9.3f}; transado "
              f"{cm['vendido_dentro_kwh']:10.1f} kWh (canon {cm['vendido_dentro_canon_kwh']:10.1f})")
    T = pd.DataFrame(filas)
    exige(d_ref <= 1e-3, f"la liquidación de aquí no reproduce P2Pcom_COP de e1/PC ({d_ref:.2e} COP)")
    ok(f"con el almacén del canon, la liquidación reproduce P2Pcom_COP de p2p_comunitario_13casos.csv (e1/PC) por "
       f"institución en los trece casos (≤ {d_ref:.1e} COP)")
    ok(f"energía en las 26 liquidaciones: lo vendido es lo comprado en cada hora, los pagos internos suman cero, el "
       f"fondo se conserva (≤ {d_en:.1e} kWh), el crédito del mes no pasa de la importación y el balance de cada mes "
       "cierra con la generación")
    num_ = T.drop(columns=["caso", "institucion", "comercializador", "gini_P2Pcom_exacto"])
    HP.finito(num_, "tabla")
    for c in CASOS:
        t = T[T.caso == c]
        cm = t[t.institucion == "comunidad"].iloc[0]
        ins = t[t.institucion != "comunidad"]
        for k in num_.columns:
            if k.startswith(("signo_", "caso_art20")):
                continue
            exige(abs(ins[k].sum() - cm[k]) <= max(1e-3, 1e-6 * abs(cm[k])), f"{c}: comunidad ≠ suma en {k}")
    ok("la comunidad es la suma de sus instituciones (≤ 1e-3 COP o 1e-6 relativo); todo finito")
    exige(set(T.comercializador) <= {"A", "B", ""} and "cedenar" not in T.to_csv().lower(), "comercializador nombrado")
    SALIDA.mkdir(parents=True, exist_ok=True)
    T.to_csv(SALIDA / "p2pcom_exacto_13casos.csv", index=False, encoding="utf-8", lineterminator="\n",
             float_format="%.6f")
    cm = T[T.institucion == "comunidad"].set_index("caso")
    with open(SALIDA / "resumen.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# P2P colectivo exacto en los trece casos (MCOP de la comunidad)\n\n")
        fh.write("| Caso | C4 | C1 | P2P | P2P col. aprox. | P2P col. exacto | exacto − aprox. | exacto − C4 | "
                 "H2 exacto | exacto − H2 | Transado (MWh) | Transado canon (MWh) |\n")
        fh.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for c, r in cm.iterrows():
            fh.write(f"| {c} | {r.B_C4_COP / M:.3f} | {r.B_C1_COP / M:.3f} | {r.B_P2P_COP / M:.3f} | "
                     f"{r.P2Pcom_aprox_COP / M:.3f} | {r.P2Pcom_exacto_COP / M:.3f} | "
                     f"{r.brecha_P2Pcom_exacto_menos_aprox_COP / M:.3f} | {r.brecha_P2Pcom_exacto_menos_C4_COP / M:.3f} | "
                     f"{r.H2_exacto_COP / M:.3f} | {r.brecha_P2Pcom_exacto_menos_H2_exacto_COP / M:.3f} | "
                     f"{r.vendido_dentro_kwh / 1e3:.2f} | {r.vendido_dentro_canon_kwh / 1e3:.2f} |\n")
    guion = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh_:
        fh = CP._Anonimo(fh_)
        fh.write("p2pcom_exacto.py: el P2P colectivo sobre el mercado resuelto con el piso del fondo (matriz_p2pcom)\n")
        fh.write(f"entrega: {a.entrega}\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n"
                 + (git("status", "--short", "--untracked-files=all", "--", guion) or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write(f"orden: python -u {guion} --entrega {a.entrega}\n")
        leidos = list(dict.fromkeys(AS.LEIDOS + CP.LEIDOS))
        fh.write(f"artefactos del canon leídos con su huella: {len(leidos)}\n")
        for g, r in leidos:
            fh.write(f"  {g}  {r}\n")
        fh.write(f"partes del almacén de matriz_p2pcom leídas (sin huella todavía; ruta, bytes, sha256): {len(LEIDOS)}\n")
        for r, b, h in LEIDOS:
            fh.write(f"  {r}  {b}  {h}\n")
        fh.write(f"compuertas: {len(COMPUERTAS)}, todas OK:\n")
        for cpt in COMPUERTAS:
            fh.write(f"  OK  {cpt}\n")
        fh.write(f"filas: {len(T)}\n")
        fh.write("salvedades: propuesta regulatoria; el piso usa el residual aproximado con los totales del mes "
                 "(CANON §14.27); comercializador único y perfil horario declarado como supuestos; no se simula aquí\n")
    pd.set_option("display.width", 250)
    print((cm[["B_C4_COP", "B_C1_COP", "B_P2P_COP", "P2Pcom_aprox_COP", "P2Pcom_exacto_COP", "H2_exacto_COP"]] / M).round(3))
    print(f"[p2pcom_exacto] {(_dt.datetime.now() - t0).total_seconds():.0f} s; {len(COMPUERTAS)} compuertas; salida en {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
