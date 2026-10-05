"""
h2_exacto.py — H2 exacto: el mercado con el piso del vendedor de H2 (la matriz
de trece casos del 2026-10-05, `--piso-mecanismo h2`) liquidado como H2
===============================================================================
Actividades 2.1 y 2.2 de la propuesta. No simula: lee los almacenes de
`SALIDAS_SERVIDOR/entrega_matriz_h2_2026-10-05/SALIDAS_SERVIDOR/matriz_h2/`
(trece casos, cada uno con su compuerta de salida EN VERDE en el servidor) y
los artefactos del canon con huella (tarifas, capacidades, bolsa y la salida
de `hibrido_por_planta.py`, grupo e1/H1).

QUÉ ES H2 (CANON §14.26, diseño aprobado el 2026-10-05): H1, el autogenerador
colectivo de crédito mutualizado (fondo de C4 deducido por el numeral de la
planta de origen y repartido «primero lo propio»), con el intercambio entre
miembros exento del Cv en las plantas del numeral 1 (hasta 100 kW). Lo que
vende una planta del numeral 2 paga κ·Cv + Θ.

POR QUÉ «EXACTO». `hibrido_por_planta.py` liquidó H2 sobre los flujos del
mercado del canon, que se formó con el piso de C1; con el cargo del
intercambio y el fondo, el piso del vendedor es otro y el mercado transa otra
cosa. La matriz del 2026-10-05 resolvió cada hora con el piso de H2
(`core.opciones_externas.piso_mecanismo`): antes del corte, el de C1; desde el
corte, la cesión al fondo y la bolsa; más el cargo del numeral 2. Aquí se
liquida H2 sobre ESOS flujos.

QUIÉN PAGA EL CARGO. En el mercado el cargo está en el piso del vendedor, de
modo que lo paga el VENDEDOR, con la deducción de su propia tarifa (como el
piso). Es la cifra de H2. La variante «comprador» (el cargo a quien compra,
con su tarifa, como en `hibrido_por_planta.py`) se publica al lado: el
agregado de la comunidad difiere solo por la tarifa con que se cobra.

COMPUERTAS (falla en voz alta; ningún `except`; todo finito):
  * la liquidación de aquí, con el almacén del canon y el cargo al comprador,
    reproduce H2_COP de hibrido_13casos.csv (e1/H1) por institución en los
    trece casos: el código es el mismo;
  * en E0, K1, CV2 y SINU (sin corte y sin plantas del numeral 2, donde el
    piso de H2 es el de C1 al bit) los flujos del almacén nuevo son los del
    canon y H2 exacto es H2 aproximado al peso;
  * energía: lo vendido es lo comprado en cada hora, los pagos internos suman
    cero, lo asignado suma el fondo, crédito + exceso = asignado y autoconsumo
    + vendido dentro + fondo = generación de la comunidad en cada mes;
  * la comunidad es la suma de sus instituciones.

Escribe en SALIDAS_SERVIDOR/h2_exacto_2026-10-05/: h2_exacto_13casos.csv
(caso × institución y «comunidad»), resumen.md y procedencia.txt (con el
sha256 de cada parte de los almacenes leídos, para registrarlos).

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo/h2_exacto.py
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
import hibrido_por_planta as HP  # noqa: E402
import p2p_comunitario as PC  # noqa: E402

SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
MATRIZ_H2 = SALIDAS / "entrega_matriz_h2_2026-10-05" / "SALIDAS_SERVIDOR" / "matriz_h2"
SALIDA = SALIDAS / "h2_exacto_2026-10-05"
F_H1 = "hibrido_por_planta_2026-10-04/hibrido_13casos.csv"
CASOS = AS.CASOS
IGUAL_A_C1 = {"E0", "K1", "CV2", "SINU"}     # piso de H2 = piso de C1 al bit (test_piso_mecanismo_trece)
CONTRA = ["C4", "C1", "P2P", "P2Pcom"]
M = 1e6

COMPUERTAS: list[str] = []
LEIDOS_H2: list[tuple[str, int, str]] = []


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[h2_exacto] COMPUERTA FALLIDA: {msg}")


def ok(msg: str) -> None:
    COMPUERTAS.append(msg)
    print(f"[h2_exacto]   OK  {msg}")


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


# ── El almacén nuevo (sin huella todavía: se registra su sha256) ────────────
def almacen_h2(c: str, tabla: str) -> pd.DataFrame:
    d = MATRIZ_H2 / c / "almacen" / "m1" / tabla
    partes = sorted(d.glob("*.parquet"))
    exige(len(partes) >= 1, f"{c}: sin partes de «{tabla}» en {d}")
    out = []
    for p in partes:
        datos = p.read_bytes()
        r = p.relative_to(SALIDAS).as_posix()
        if r not in [x[0] for x in LEIDOS_H2]:
            LEIDOS_H2.append((r, len(datos), hashlib.sha256(datos).hexdigest()))
        out.append(pd.read_parquet(p))
    return pd.concat(out, ignore_index=True)


def carga(c: str, TT, cap, nuevo: bool) -> tuple[dict, pd.DataFrame]:
    """`AS.carga` sobre el almacén del canon (nuevo=False) o el de matriz_h2
    (nuevo=True), con sus mismas comprobaciones; y los flujos del mismo."""
    if not nuevo:
        return AS.carga(c, TT, cap), AS.almacen(c, "flujos")
    original = AS.almacen
    AS.almacen = almacen_h2
    try:
        L = AS.carga(c, TT, cap)
    finally:
        AS.almacen = original
    return L, almacen_h2(c, "flujos")


# ── Funciones puras (las prueba tests/test_h2_exacto.py) ────────────────────
def cargo_vendedor(vendedor, hora, kwh, num_de: dict, ags: list[str], kap: float, Cv: np.ndarray,
                   Th: np.ndarray, T: int) -> np.ndarray:
    """(N, T) lo que paga cada VENDEDOR por lo que vende dentro en H2: nada si
    su planta es del numeral 1; κ·Cv + Θ de su propia tarifa si es del 2 (lo
    que el piso de H2 le suma, `piso_mecanismo`)."""
    idx = {a: i for i, a in enumerate(ags)}
    iv = np.array([idx[x] for x in vendedor], dtype=int)
    nv = np.array([num_de[x] for x in vendedor], dtype=int)
    h = np.asarray(hora, dtype=int)
    k = np.asarray(kwh, dtype=float)
    Cv, Th = np.asarray(Cv, dtype=float), np.asarray(Th, dtype=float)
    q2 = np.zeros((len(ags), T))
    sel = nv == 2
    np.add.at(q2, (iv[sel], h[sel]), k[sel])
    return q2 * (kap * Cv + Th)


def liquida_h2(L: dict, fl: pd.DataFrame, pb: np.ndarray, pagador: str, qué: str) -> dict:
    """H2 sobre los flujos `fl` y la caracterización `L` de un almacén."""
    if pagador not in ("vendedor", "comprador"):
        raise ValueError(f"pagador {pagador!r}")
    N, ags, mes = L["N"], L["ags"], L["mes"]
    s, d, v, q, CU, au = L["s"], L["d"], L["v"], L["q"], L["CU"], L["au"]
    kap, Cv, Th = L["kap"], L["Cv"], L["Th"]
    T = s.shape[1]
    fl = fl.astype({"kwh": "float64", "precio": "float64", "techo_comprador": "float64"})
    pag = PC.pagos_internos(fl.vendedor.to_numpy(), fl.comprador.to_numpy(), fl.hora.to_numpy(), fl.kwh.to_numpy(),
                            fl.precio.to_numpy(), fl.techo_comprador.to_numpy(), ags, T)
    HP.finito(pag, f"{qué} pagos")
    num = HP.numeral_planta(L["capk"])
    n2 = (num == 2).astype(float)
    sr, dr = np.maximum(s - v, 0.0), np.maximum(d - q, 0.0)
    W_f, TR_f = HP.pde_primero_propio(sr, dr, mes)
    ded_f = HP.ded_por_origen(HP.fraccion_numeral2_traza(TR_f, n2), kap, Cv, Th, mes)
    if pagador == "comprador":
        q1, q2 = HP.compras_por_numeral(fl.vendedor.to_numpy(), fl.comprador.to_numpy(), fl.hora.to_numpy(),
                                        fl.kwh.to_numpy(), dict(zip(ags, num)), ags, T)
        cargo = HP.cargo_intercambio(q1, q2, kap, Cv, Th, "H2")
    else:
        cargo = cargo_vendedor(fl.vendedor.to_numpy(), fl.hora.to_numpy(), fl.kwh.to_numpy(),
                               dict(zip(ags, num)), ags, kap, Cv, Th, T)
    R = HP.valor_hibrido(au, s, d, v, q, CU, pag, cargo, ded_f, mes, pb, W_f, qué)
    R.update(cargo=cargo, pag=pag, num=num, TR=TR_f)
    return R


def energia(L: dict, R: dict, qué: str) -> float:
    """Compuertas de energía de una liquidación; devuelve el mayor desvío."""
    G, au, v, q, mes, N = L["G"], L["au"], L["v"], L["q"], L["mes"], L["N"]
    exige(float(np.abs(v.sum(0) - q.sum(0)).max()) <= 1e-3, f"{qué}: lo vendido ≠ lo comprado en una hora")
    exige(float(np.abs(R["pag"].sum(0)).max()) <= 1e-6, f"{qué}: los pagos internos no suman cero")
    d = max(float(np.abs(R["asg"].sum(0) - R["sr"].sum(0)).max()),
            float(np.abs(R["cr"] + R["ex"] - R["asg"]).max()))
    exige(d <= 1e-6, f"{qué}: la energía del fondo no se conserva ({d:.2e})")
    for m in np.unique(mes):
        h = mes == m
        bal = float(au[:, h].sum() + v[:, h].sum() + R["asg"][:, h].sum())
        exige(abs(bal - float(G[:, h].sum())) <= 1e-3 * N * int(h.sum()), f"{qué}: balance del mes {m}")
        exige(bool((R["cr"][:, h].sum(1) <= R["dr"][:, h].sum(1) + 1e-6).all()), f"{qué}: crédito sobre la importación")
    return d


def main() -> int:
    t0 = _dt.datetime.now()
    exige(MATRIZ_H2.is_dir(), f"no existe {MATRIZ_H2}: trae la entrega del servidor (MONTAJE_SERVIDOR.md)")
    mec = (MATRIZ_H2 / "MECANISMO").read_text(encoding="utf-8").strip()
    exige(mec == "h2", f"la matriz se corrió con el piso «{mec}», no con h2")
    sucio_mod = git("status", "--short", "--", *HP.MODULOS)
    exige(sucio_mod == "", f"módulos de producción con cambios sin commit:\n{sucio_mod}")
    print("[h2_exacto] 1. tarifas, capacidades, bolsa y la salida de H1 (e1/H1)")
    TT = AS.tarifas()
    cap = AS.capacidades()
    idx, _ = CP.horizonte()
    pb = CP.bolsa(idx)
    exige(pb.shape == (6144,) and bool(np.isfinite(pb).all()), "bolsa incompleta")
    H1T = pd.read_csv(AS.lee(F_H1, "e1/H1"), keep_default_na=False, na_values=[""])
    print("[h2_exacto] 2. los trece casos")
    filas, d_ref, d_igual, d_en = [], 0.0, 0.0, 0.0
    for c in CASOS:
        ref = H1T[H1T.caso == c].set_index("institucion")
        # (a) el código: canon + cargo al comprador = H2 de e1/H1
        L0, fl0 = carga(c, TT, cap, nuevo=False)
        R0 = liquida_h2(L0, fl0, pb, "comprador", f"{c} canon")
        exige(list(ref.index) == L0["ags"] + ["comunidad"], f"{c}: instituciones de e1/H1")
        d_ref = max(d_ref, float(np.abs(R0["val"] - ref.loc[L0["ags"], "H2_COP"].to_numpy(float)).max()))
        # (b) H2 exacto: los flujos del mercado con el piso de H2
        L, fl = carga(c, TT, cap, nuevo=True)
        exige(L["ags"] == L0["ags"], f"{c}: instituciones distintas en el almacén nuevo")
        Rv = liquida_h2(L, fl, pb, "vendedor", f"{c} H2 exacto")
        Rc = liquida_h2(L, fl, pb, "comprador", f"{c} H2 exacto, cargo al comprador")
        for R_, q_ in ((R0, "canon"), (Rv, "exacto"), (Rc, "exacto comprador")):
            HP.finito(R_["H"], f"{c} {q_}")
        d_en = max(d_en, energia(L0, R0, f"{c} canon"), energia(L, Rv, f"{c} H2 exacto"),
                   energia(L, Rc, f"{c} H2 exacto comprador"))
        if c in IGUAL_A_C1:
            dv = max(float(np.abs(L["v"] - L0["v"]).max()), float(np.abs(L["q"] - L0["q"]).max()))
            exige(dv <= 1e-3, f"{c}: el piso de H2 es el de C1 y los flujos cambian ({dv:.2e} kWh)")
            d_igual = max(d_igual, float(np.abs(Rv["val"] - ref.loc[L0["ags"], "H2_COP"].to_numpy(float)).max()))
        ags, N = L["ags"], L["N"]
        for i in list(range(N)) + ["comunidad"]:
            sel = slice(None) if i == "comunidad" else slice(i, i + 1)
            nombre = "comunidad" if i == "comunidad" else ags[i]
            r = ref.loc[nombre]
            f = dict(caso=c, institucion=nombre,
                     comercializador="" if pd.isna(r.comercializador) else str(r.comercializador),
                     numeral_planta=int(Rv["num"].max() if i == "comunidad" else Rv["num"][i]),
                     vendido_dentro_kwh=float(L["v"][sel].sum()), comprado_dentro_kwh=float(L["q"][sel].sum()),
                     vendido_dentro_canon_kwh=float(L0["v"][sel].sum()),
                     comprado_dentro_canon_kwh=float(L0["q"][sel].sum()),
                     residual_iny_kwh=float(Rv["sr"][sel].sum()), credito_kwh=float(Rv["cr"][sel].sum()),
                     exceso_kwh=float(Rv["ex"][sel].sum()),
                     cargo_vendedor_COP=float(Rv["cargo"][sel].sum()), cargo_comprador_COP=float(Rc["cargo"][sel].sum()),
                     pagos_internos_COP=float(Rv["pag"][sel].sum()),
                     H2_exacto_COP=float(Rv["val"][sel].sum()), H2_exacto_cargo_comprador_COP=float(Rc["val"][sel].sum()),
                     H2_aprox_COP=float(r.H2_COP), H1_aprox_COP=float(r.H1_COP), H1_fondo_COP=float(r.H1_fondo_COP))
            for x in CONTRA:
                f[f"B_{x}_COP"] = float(r[f"B_{x}_COP"])
            for h_ in ("H2_exacto", "H2_aprox"):
                for x in CONTRA:
                    b = f[f"{h_}_COP"] - f[f"B_{x}_COP"]
                    f[f"brecha_{h_}_menos_{x}_COP"] = b
                    f[f"signo_{h_}_menos_{x}"] = int(CP.signo_brecha(b))
            f["brecha_H2_exacto_menos_H2_aprox_COP"] = f["H2_exacto_COP"] - f["H2_aprox_COP"]
            f["brecha_H2_exacto_menos_H1_fondo_COP"] = f["H2_exacto_COP"] - f["H1_fondo_COP"]
            if i == "comunidad":
                f["gini_H2_exacto"] = CP.gini(Rv["val"])
                f["gini_B_P2Pcom"] = float(r.gini_P2Pcom)
                f["gini_B_C4"] = float(r.gini_C4)
            else:
                f["gini_H2_exacto"] = f["gini_B_P2Pcom"] = f["gini_B_C4"] = np.nan
            filas.append(f)
        cm = filas[-1]
        print(f"[h2_exacto]   {c}: H2 exacto {cm['H2_exacto_COP'] / M:9.3f} MCOP, aprox {cm['H2_aprox_COP'] / M:9.3f}, "
              f"P2Pcom {cm['B_P2Pcom_COP'] / M:9.3f}; transado {cm['vendido_dentro_kwh']:10.1f} kWh "
              f"(canon {cm['vendido_dentro_canon_kwh']:10.1f})")
    T = pd.DataFrame(filas)
    exige(d_ref <= 1e-3, f"la liquidación de aquí no reproduce H2_COP de e1/H1 ({d_ref:.2e} COP)")
    ok(f"con el almacén del canon y el cargo al comprador, la liquidación reproduce H2_COP de hibrido_13casos.csv "
       f"(e1/H1) por institución en los trece casos (≤ {d_ref:.1e} COP)")
    exige(d_igual <= 1.0, f"en E0, K1, CV2 y SINU H2 exacto ≠ H2 aproximado ({d_igual:.3f} COP)")
    ok(f"en E0, K1, CV2 y SINU (piso de H2 = piso de C1) los flujos del almacén nuevo son los del canon (≤ 1e-3 kWh) "
       f"y H2 exacto es H2 aproximado por institución (≤ {d_igual:.3f} COP)")
    ok(f"energía en las 39 liquidaciones: lo vendido es lo comprado en cada hora, los pagos internos suman cero, el "
       f"fondo se conserva (≤ {d_en:.1e} kWh), el crédito del mes no pasa de la importación y el balance de cada mes "
       "cierra con la generación")
    es_com = T.institucion == "comunidad"
    num_ = T.drop(columns=["caso", "institucion", "comercializador", "gini_H2_exacto", "gini_B_P2Pcom", "gini_B_C4"])
    HP.finito(num_, "tabla")
    for c in CASOS:
        t = T[T.caso == c]
        cm = t[t.institucion == "comunidad"].iloc[0]
        ins = t[t.institucion != "comunidad"]
        for k in num_.columns:
            if k.startswith(("signo_", "numeral_planta")):
                continue
            # piso de 1e-3 COP: las referencias de e1/H1 vienen de un CSV con seis
            # decimales, y una brecha de la comunidad cercana a cero (K1) no
            # admite una tolerancia solo relativa
            exige(abs(ins[k].sum() - cm[k]) <= max(1e-3, 1e-6 * abs(cm[k])), f"{c}: comunidad ≠ suma en {k}")
    ok("la comunidad es la suma de sus instituciones (≤ 1e-3 COP o 1e-6 relativo); todo finito")
    exige(set(T.comercializador) <= {"A", "B", ""} and "cedenar" not in T.to_csv().lower(), "comercializador nombrado")
    # ── salida ──────────────────────────────────────────────────────────────
    SALIDA.mkdir(parents=True, exist_ok=True)
    T.to_csv(SALIDA / "h2_exacto_13casos.csv", index=False, encoding="utf-8", lineterminator="\n", float_format="%.6f")
    cm = T[es_com].set_index("caso")
    with open(SALIDA / "resumen.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# H2 exacto en los trece casos (MCOP de la comunidad)\n\n")
        fh.write("| Caso | C4 | C1 | P2P | P2P colectivo | H2 aprox. | H2 exacto | H2 exacto − P2P colectivo | "
                 "H2 exacto − C4 | Transado (MWh) | Transado canon (MWh) |\n")
        fh.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for c, r in cm.iterrows():
            fh.write(f"| {c} | {r.B_C4_COP / M:.3f} | {r.B_C1_COP / M:.3f} | {r.B_P2P_COP / M:.3f} | "
                     f"{r.B_P2Pcom_COP / M:.3f} | {r.H2_aprox_COP / M:.3f} | {r.H2_exacto_COP / M:.3f} | "
                     f"{r.brecha_H2_exacto_menos_P2Pcom_COP / M:.3f} | {r.brecha_H2_exacto_menos_C4_COP / M:.3f} | "
                     f"{r.vendido_dentro_kwh / 1e3:.2f} | {r.vendido_dentro_canon_kwh / 1e3:.2f} |\n")
    guion = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh_:
        fh = CP._Anonimo(fh_)
        fh.write("h2_exacto.py: H2 sobre el mercado resuelto con el piso de H2 (matriz_h2, 2026-10-05)\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("este guion con cambios sin commit:\n"
                 + (git("status", "--short", "--untracked-files=all", "--", guion) or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u " + guion + "\n")
        leidos = list(dict.fromkeys(AS.LEIDOS + CP.LEIDOS))
        fh.write(f"artefactos del canon leídos con su huella: {len(leidos)}\n")
        for g, r in leidos:
            fh.write(f"  {g}  {r}\n")
        fh.write(f"partes del almacén de matriz_h2 leídas (sin huella todavía; ruta, bytes, sha256): {len(LEIDOS_H2)}\n")
        for r, b, h in LEIDOS_H2:
            fh.write(f"  {r}  {b}  {h}\n")
        fh.write(f"compuertas: {len(COMPUERTAS)}, todas OK:\n")
        for cpt in COMPUERTAS:
            fh.write(f"  OK  {cpt}\n")
        fh.write(f"filas: {len(T)}\n")
        fh.write("salvedades: propuesta regulatoria, no la norma vigente; el corte del piso usa el residual "
                 "aproximado con los totales del mes (CANON §14.27); comercializador único y perfil horario "
                 "declarado como supuestos; no se simula aquí\n")
    pd.set_option("display.width", 250)
    print((cm[["B_C4_COP", "B_C1_COP", "B_P2P_COP", "B_P2Pcom_COP", "H2_aprox_COP", "H2_exacto_COP",
               "H2_exacto_cargo_comprador_COP"]] / M).round(3))
    print(f"[h2_exacto] {(_dt.datetime.now() - t0).total_seconds():.0f} s; {len(COMPUERTAS)} compuertas; salida en {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
