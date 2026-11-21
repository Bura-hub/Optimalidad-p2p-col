"""
m3_cargos_parciales.py — M3: la ventaja del mercado P2P y del P2P colectivo
cuando lo intercambiado paga una fracción f de los cargos de red
===============================================================================
Comentarios C-1 y C-2 de la revisión r1. No simula: vuelve a liquidar los flujos
del mercado guardados en el almacén de cada caso, con las funciones de
liquidación de `atribucion_supuestos.py` (punto S del canon).

QUÉ SE CALCULA. Cada kWh comprado dentro paga f · Θ, con Θ los cargos de red
(transmisión, distribución, pérdidas y restricciones) de la tarifa del comprador
en su mes, y f en {0; 0,25; 0,5; 0,75; 1}. El Cv sigue exento. Dos lecturas:

  flujos fijos   los kWh que cada par transó en el canon se mantienen aunque el
                 cargo deje al par sin ganancia. Es una cuenta contable: lineal
                 en f, con el cargo total Σ Θ·q. Vale para el mercado P2P y
                 para el P2P colectivo.
  con salida     deja de transar todo par cuya banda neta, techo del comprador
                 menos piso del vendedor menos f · Θ, es negativa; su energía
                 vuelve al residual de cada miembro y se liquida como en C1.
                 Los demás flujos no cambian. Solo para el mercado P2P.

NINGUNA DE LAS DOS VUELVE A RESOLVER EL MERCADO. Con un cargo, el piso del juego
y el despacho serían otros. «Con salida» es exacta donde el cargo deja sin
ganancia a todos los pares (el mercado se apaga y queda C1) y aproximada en lo
demás.

Con f = 1, los flujos fijos reproducen la columna `v10_theta` de
`atribucion_13casos.csv` (compuerta).

Escribe m3_cargos.csv y m3_umbrales.csv.

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo_r1/m3_cargos_parciales.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import ar1_comun as C

FS = [0.0, 0.25, 0.5, 0.75, 1.0]
REJILLA = np.round(np.arange(0.0, 1.0001, 0.01), 2)
FU = "flujos del almacén de cada caso reliquidados (atribucion_supuestos, e1/S; p2p_comunitario, e1/PC)"


def con_salida(L: dict, fl: pd.DataFrame, pb: np.ndarray, f: float) -> tuple[float, float]:
    """Valor de la comunidad (COP) y energía que sigue transándose (kWh) si
    salen los pares con banda neta negativa."""
    AS = C.AS
    ags = {a: i for i, a in enumerate(L["ags"])}
    iv, ic, h = fl.vendedor.map(ags).to_numpy(), fl.comprador.map(ags).to_numpy(), fl.hora.to_numpy()
    neta = fl.techo_comprador.to_numpy() - fl.piso_vendedor.to_numpy() - f * L["Th"][ic, h]
    queda = neta >= -1e-3                       # float32 del almacén: una milésima de COP/kWh
    k = fl.kwh.to_numpy() * queda
    N = L["N"]
    v, q = np.zeros((N, 6144)), np.zeros((N, 6144))
    np.add.at(v, (iv, h), k)
    np.add.at(q, (ic, h), k)
    sr, dr = np.maximum(L["s"] - v, 0.0), np.maximum(L["d"] - q, 0.0)
    rp, _ = AS.art25(sr, dr, L["CU"], L["ded1"], L["mes"], pb, f"{L['c']} residual con salida")
    val = L["au"] * L["CU"] + L["CU"] * q - f * L["Th"] * q + rp
    return float(val.sum()), float(k.sum())


def cruce(fs: np.ndarray, y: np.ndarray):
    """Primer f de la rejilla en que y deja de ser positiva (None si no ocurre)."""
    m = np.flatnonzero(y <= 0)
    return None if m.size == 0 else float(fs[m[0]])


def main() -> int:
    med = C.Medicion("m3", "cargos de red parciales sobre lo intercambiado, con los flujos fijos")
    AS = C.AS
    DAT, pb = C.casos_cargados(med)
    A = C.atribucion()
    PC = C.p2pcom()
    PC = PC[PC.institucion == "comunidad"].set_index("caso")
    filas, umbr = [], []
    for c, L in DAT.items():
        out, _ = AS.esquinas(L, pb)
        P2P, C1, C4 = (float(out[k].sum()) for k in ("P2P", "C1", "C4"))
        for k, x in (("P2P", P2P), ("C1", C1), ("C4", C4)):
            med.exige(abs(x - A.loc[c, k]) <= max(1.0, 1e-7 * abs(x)), f"{c} {k}: la reliquidación difiere del punto S en {x - A.loc[c, k]:.2f} COP")
            med.exige(abs(x - PC.loc[c, f"B_{k}_COP"]) <= max(1.0, 1e-7 * abs(x)), f"{c} {k}: difiere de e1/PC")
        cargo = float((L["Th"] * L["q"]).sum())           # Σ Θ·q, el cargo completo
        med.exige(abs((P2P - cargo) - A.loc[c, "v10_theta"]) <= max(1.0, 1e-7 * abs(P2P)),
                  f"{c}: con f = 1 los flujos fijos no dan v10_theta del punto S")
        Pcom = float(PC.loc[c, "P2Pcom_COP"])
        fl = AS.almacen(c, "flujos").astype({"kwh": "float64", "techo_comprador": "float64", "piso_vendedor": "float64"})
        E = float(fl.kwh.sum())
        v0, k0 = con_salida(L, fl, pb, 0.0)
        med.exige(abs(v0 - P2P) <= max(1.0, 1e-7 * abs(P2P)) and abs(k0 - E) <= 1e-6,
                  f"{c}: con f = 0 la lectura con salida no es el mercado P2P ({v0 - P2P:.2f} COP)")
        sal = {f: con_salida(L, fl, pb, float(f)) for f in REJILLA}
        for f in FS:
            vs, ks = sal[round(f, 2)]
            filas.append(dict(caso=c, f=f, cargo_COP=f * cargo, C1_COP=C1, C4_COP=C4,
                              P2P_fijos_COP=P2P - f * cargo, P2Pcom_fijos_COP=Pcom - f * cargo, P2P_salida_COP=vs,
                              transado_kwh=E, transado_salida_kwh=ks,
                              P2P_fijos_menos_C4=P2P - f * cargo - C4, P2P_fijos_menos_C1=P2P - f * cargo - C1,
                              P2Pcom_fijos_menos_C4=Pcom - f * cargo - C4, P2Pcom_fijos_menos_C1=Pcom - f * cargo - C1,
                              P2P_salida_menos_C4=vs - C4, P2P_salida_menos_C1=vs - C1))
        u = dict(caso=c, cargo_completo_COP=cargo, theta_medio_transado_COP_kWh=cargo / E,
                 P2P_menos_C4_f0=P2P - C4, P2P_menos_C1_f0=P2P - C1, P2Pcom_menos_C4_f0=Pcom - C4, P2Pcom_menos_C1_f0=Pcom - C1)
        for nom, b in (("P2P_C4", P2P - C4), ("P2P_C1", P2P - C1), ("P2Pcom_C4", Pcom - C4), ("P2Pcom_C1", Pcom - C1)):
            fstar = b / cargo                              # lineal: la brecha se anula en b / cargo
            u[f"f_cambio_{nom}_fijos"] = fstar if 0.0 < fstar <= 1.0 else np.nan
        ys = np.array([sal[f][0] for f in REJILLA])
        ks = np.array([sal[f][1] for f in REJILLA])
        fc4, fc1 = cruce(REJILLA, ys - C4), cruce(REJILLA, ys - C1 - 1.0)
        u["f_cambio_P2P_C4_salida"] = np.nan if fc4 is None else fc4
        u["f_P2P_iguala_C1_salida"] = np.nan if fc1 is None else fc1       # ventaja sobre C1 de 1 COP o menos
        apag = np.flatnonzero(ks <= 1e-6)
        u["f_sin_intercambio_salida"] = np.nan if apag.size == 0 else float(REJILLA[apag[0]])
        u["minimo_P2P_salida_menos_C4"] = float((ys - C4).min())
        u["minimo_P2P_salida_menos_C1"] = float((ys - C1).min())
        umbr.append(u)
        med.di(f"  {c}: cargo completo {cargo / C.M:.3f} MCOP; P2P − C4 con f = 0, 0,5 y 1 (fijos): "
               f"{(P2P - C4) / C.M:.3f}, {(P2P - 0.5 * cargo - C4) / C.M:.3f}, {(P2P - cargo - C4) / C.M:.3f}; "
               f"con salida, f = 1: {(sal[1.0][0] - C4) / C.M:.3f} y {sal[1.0][1]:.1f} de {E:.1f} kWh")
    med.ok("la reliquidación reproduce C1, C4 y P2P del punto S y de e1/PC en los 13 casos, y con f = 1 los flujos fijos dan v10_theta")
    med.ok("con f = 0 la lectura con salida es el mercado P2P del canon y conserva toda la energía transada, en los 13 casos")
    T = pd.DataFrame(filas)
    U = pd.DataFrame(umbr)
    sal1 = T[T.f == 1.0].set_index("caso")
    sin = [c for c in C.AS.SIN_AGOTAR]
    m = T[T.caso.isin(sin)]
    med.exige(bool((m.P2P_salida_COP >= m.P2P_fijos_COP - 1.0).all()),
              "donde nadie agota su crédito, la lectura con salida queda bajo los flujos fijos")
    med.ok("donde nadie agota su crédito (E0, P2, K1, CV2 y SINU), con salida el mercado nunca vale menos que con los flujos fijos")
    bajo = sorted(set(T[T.P2P_salida_COP < T.P2P_fijos_COP - 1.0].caso))
    med.di("  con crédito agotado, sacar un par que pierde contra su piso puede bajar el valor de la comunidad, porque su "
           f"energía pasa al residual y parte va a la bolsa: ocurre en {', '.join(bajo) or 'ningún caso'}")
    med.pon("m3__casos_salida_bajo_fijos", len(bajo), "casos de 13", FU)
    med.tabla(T, "m3_cargos.csv")
    med.tabla(U, "m3_umbrales.csv")
    for _, r in T.iterrows():
        ft = f"{int(round(r.f * 100)):03d}"
        for k in ("P2P_fijos_menos_C4", "P2P_fijos_menos_C1", "P2Pcom_fijos_menos_C4", "P2Pcom_fijos_menos_C1",
                  "P2P_salida_menos_C4", "P2P_salida_menos_C1"):
            med.pon(f"m3__{r.caso}__f{ft}__{k}", r[k] / C.M, "MCOP", FU)
        med.pon(f"m3__{r.caso}__f{ft}__transado_salida_kwh", r.transado_salida_kwh, "kWh", FU)
    for _, r in U.iterrows():
        med.pon(f"m3__{r.caso}__cargo_completo", r.cargo_completo_COP / C.M, "MCOP", FU + "; Σ Θ·q con Θ del comprador")
        med.pon(f"m3__{r.caso}__theta_medio_transado", r.theta_medio_transado_COP_kWh, "COP/kWh", FU)
        for k in [x for x in U.columns if x.startswith("f_")]:
            if np.isfinite(r[k]):
                med.pon(f"m3__{r.caso}__{k}", r[k], "fracción", FU)
        med.pon(f"m3__{r.caso}__minimo_P2P_salida_menos_C4", r.minimo_P2P_salida_menos_C4 / C.M, "MCOP", FU)
    n4 = int(U.f_cambio_P2P_C4_fijos.notna().sum())
    n4c = int(U.f_cambio_P2Pcom_C4_fijos.notna().sum())
    ns = int(U.f_cambio_P2P_C4_salida.notna().sum())
    med.pon("m3__casos_P2P_C4_cambia_fijos", n4, "casos de 13", FU)
    med.pon("m3__casos_P2Pcom_C4_cambia_fijos", n4c, "casos de 13", FU)
    med.pon("m3__casos_P2P_C4_cambia_salida", ns, "casos de 13", FU)
    med.di(f"  con los flujos fijos, P2P − C4 cambia de signo antes de f = 1 en {n4} casos "
           f"({', '.join(U[U.f_cambio_P2P_C4_fijos.notna()].caso)}) y el P2P colectivo − C4 en {n4c} "
           f"({', '.join(U[U.f_cambio_P2Pcom_C4_fijos.notna()].caso)}); con salida, P2P − C4 cambia en {ns}")
    med.cierra()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
