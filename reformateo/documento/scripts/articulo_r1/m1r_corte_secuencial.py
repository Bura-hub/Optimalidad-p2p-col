"""
m1r_corte_secuencial.py — AE-4: la liquidación temporalmente consistente, con
el mercado resuelto de nuevo con el corte del piso fijado hora a hora
(CANON §14.41)
===============================================================================
Actividades 2.2 y 3.3. Tres variantes del corte que entra en el piso del
vendedor (diseño, sección 2; `core/corte_secuencial.py`):

  iterado                punto fijo con los residuales resueltos (conserva la
                         previsión del mes; quita la aproximación del residual)
  secuencial_pronostico  hora a hora, saldo FIFO real y pronóstico lineal (principal)
  secuencial_saldo       hora a hora, con el saldo conocido

La liquidación de cada corrida es el Anexo 4 al cierre sobre los residuales que
resolvió el mercado, que es la FIFO del saldo. Se compara con la liquidación
actual (el mercado del canon): P2P − C4 y P2P − C1, su signo, y por
institución los pares que cambian de signo.

Compuertas (falla en voz alta):
  S2  la FIFO es el Anexo 4 sobre los residuales de cada corrida (1e-9 kWh)
  S5  C1 y C4 del libro de cada corrida son los del canon (1 COP)
  S6  P2P liquidado aquí (FIFO) es el del libro de la corrida, en la comunidad y
      por institución (1 COP)
  S4  en E0, P2, K1, CV2 y SINU el secuencial con pronóstico reproduce la esquina
      p2p (los flujos al bit) y el canon (1e-4 kWh)
  S7  el piso de cada hora-vendedor es la permuta del numeral o la bolsa
"""
from __future__ import annotations

import re
import sys

import numpy as np
import pandas as pd

import ar2_comun as R
from core.corte_secuencial import liquida_fifo
from core.opciones_externas import reparto_anexo4
from scenarios.esquinas_supuestos import liquida_esquina

M = R.M


def tol(ref) -> float:
    """1 COP, o el float32 del almacen (1e-6 relativo) si es mayor: los libros se
    liquidaron en float64 sobre los flujos en memoria, y aqui se liquida sobre
    los flujos guardados en float32 (CANON §14.21: «dentro del float32»)."""
    return max(1.0, 1e-6 * abs(float(ref)))


def iteraciones(c: str, estado: str = "registrado") -> str:
    """La linea [R1] del registro de la corrida: el de la matriz (17-19 h) o, en
    un ciclo, el del retome (corte_iterado_<caso> o corte_iterado_ciclo_<caso>)."""
    pref = "corte_iterado_ciclo_" if estado == "ciclo_b" else "corte_iterado_"
    regs = sorted((R.RAIZ / "modelo_base" / "logs").glob(f"{pref}{c}_2026-11-21_*.log"))
    if estado == "registrado":
        regs = [r for r in regs if r.name.rsplit("_", 1)[1][:2] < "20"]   # los de la matriz, antes del retome
    else:
        regs = [r for r in regs if r.name.rsplit("_", 1)[1][:2] >= "20"]
    if not regs:
        return ""
    t = regs[-1].read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\[R1\] Corte iterado \(AE-4\): (\d+) iteraciones; .*?: (\[[^\]]*\]); (\w+)", t)
    return f"{m.group(1)} {m.group(2)} {m.group(3)}" if m else ""


CICLAN = ("E2", "E3", "E4", "P1", "N1")       # B2: el iterado de la matriz entra en ciclo


def main() -> int:
    med = R.Medicion("m1r", "AE-4: el corte del piso hora a hora, con el mercado resuelto")
    DAT, pb = R.bases()
    med.ok("13 almacenes canónicos con sus compuertas y la bolsa de la caché igual a la reconstruida")
    filas, inst = [], []
    trabajos = []
    for corte in R.CORTES:
        for c in R.CASOS_CORTE[corte]:
            if corte == "iterado" and c in CICLAN:
                # B2: los dos estados del ciclo, del retome; el principal es el de
                # la matriz al bit (el iterado es determinista)
                ds = R.estados(R.RETOME_COR, c)
                med.exige(len(ds) == 2, f"B2 {c}: el retome no trae los dos estados del ciclo")
                A = R.carga_corrida(med, R.dir_corrida("corte", "iterado", c), c, DAT[c])
                B = R.carga_corrida(med, ds[0], c, DAT[c])
                med.exige(np.array_equal(A["v"], B["v"]) and np.array_equal(A["q"], B["q"])
                          and np.array_equal(A["piso"], B["piso"]),
                          f"B2 {c}: el estado principal del retome no es el iterado de la matriz al bit")
                trabajos += [(corte, c, ds[0], "ciclo_a"), (corte, c, ds[1], "ciclo_b")]
            else:
                trabajos.append((corte, c, R.dir_corrida("corte", corte, c), "registrado"))
    for corte, c, d, estado in trabajos:
        if True:
            L = DAT[c]
            CU, ded1, ded4, mes = L["CU"], L["ded1"], L["ded4"], L["mes"]
            res_c = R.AS.resumen(c)
            C1, C4, P0 = float(res_c["C1"]), float(res_c["C4"]), float(res_c["P2P"])
            X = R.carga_corrida(med, d, c, L)
            med.exige(f"--corte-piso {corte}" in X["orden"], f"{c} {corte}: la orden no lleva --corte-piso {corte}")
            for k, ref in (("C1", C1), ("C4", C4)):
                med.exige(abs(float(X["res"][k]) - ref) <= 1.0, f"S5 {c} {corte}: {k} del libro distinto del canon")
            sr, dr = np.maximum(L["s"] - X["v"], 0.0), np.maximum(L["d"] - X["q"], 0.0)
            cr_f, ex_f = liquida_fifo(sr, dr, mes)
            cr_a, ex_a, perm_cierre = reparto_anexo4(sr, dr, mes)
            med.exige(float(np.abs(ex_f - ex_a).max()) <= 1e-9, f"S2 {c} {corte}: FIFO distinta del Anexo 4")
            val, _ = liquida_esquina("p2p", X["G"], X["D"], X["v"], X["q"], CU, ded1, ded4, mes, pb)
            P1 = float(val.sum())
            por = val.sum(axis=1) + X["pagos"]
            pa = X["pa"]
            med.exige(abs(P1 - float(X["res"]["P2P"])) <= tol(X["res"]["P2P"]), f"S6 {c} {corte}: P2P {P1:.3f} frente al libro")
            med.exige(float(np.abs(por - pa["P2P"].to_numpy(float)).max()) <= tol(np.abs(por).max()), f"S6 {c} {corte}: por institución")
            # La cifra que se compara es la del libro de la corrida, como la del
            # canon (los dos en float64 sobre los flujos en memoria); la de aquí,
            # sobre los flujos float32 del almacén, la comprueba S6.
            P1 = float(X["res"]["P2P"])
            # S7 y lo vendido bajo el piso de cierre
            vende = L["s"] > 1e-9
            permuta = CU - ded1
            en_perm = np.abs(X["piso"] - permuta) <= 0.01
            en_bol = np.abs(X["piso"] - pb[None, :]) <= 0.01
            med.exige(bool((en_perm | en_bol)[vende].all()), f"S7 {c} {corte}: piso que no es permuta ni bolsa")
            bajo = vende & ~en_perm & perm_cierre          # piso de bolsa y al cierre es crédito
            sobre = vende & en_perm & ~perm_cierre & ~np.isclose(permuta, pb[None, :])
            kwh_bajo = float((X["v"] * bajo).sum())
            cop_bajo = float((X["v"] * (permuta - pb[None, :]) * bajo).sum())
            kwh_sobre = float((X["v"] * sobre).sum())
            if corte == "secuencial_pronostico" and c in R.CONTROLES:
                Y = R.carga_corrida(med, R.dir_corrida("esquina", "p2p", c), c, L)
                med.exige(np.array_equal(X["v"], Y["v"]) and np.array_equal(X["q"], Y["q"])
                          and np.array_equal(X["piso"], Y["piso"]),
                          f"S4 {c}: el secuencial no reproduce al bit la esquina p2p")
                med.exige(abs(P1 - P0) <= tol(P0), f"S4 {c}: P2P distinto del canon")
            pa0 = DAT[c]["por_agente"]
            fil = dict(corte=corte, caso=c, C1_COP=C1, C4_COP=C4, P2P_canon_COP=P0, P2P_COP=P1,
                       dif_COP=P1 - P0, P2P_C4_canon_COP=P0 - C4, P2P_C4_COP=P1 - C4,
                       P2P_C1_canon_COP=P0 - C1, P2P_C1_COP=P1 - C1,
                       dif_P2P_C4_pct=100 * (P1 - P0) / (P0 - C4) if abs(P0 - C4) > 1 else np.nan,
                       dif_P2P_C1_pct=100 * (P1 - P0) / (P0 - C1) if abs(P0 - C1) > 1 else np.nan,
                       signo_C4_cambia=int(np.sign(P1 - C4) != np.sign(P0 - C4)),
                       signo_C1_cambia=int(np.sign(P1 - C1) != np.sign(P0 - C1)),
                       transado_canon_kwh=float(L["v"].sum()), transado_kwh=float(X["v"].sum()),
                       horas_vendedor_bolsa_canon=int((vende & ~(np.abs(L["piso"] - permuta) <= 0.01)).sum()),
                       horas_vendedor_bolsa=int((vende & ~en_perm).sum()),
                       vendido_bajo_piso_cierre_kwh=kwh_bajo, vendido_bajo_piso_cierre_COP=cop_bajo,
                       vendido_permuta_y_cierre_exceso_kwh=kwh_sobre,
                       exceso_kwh=float(ex_a.sum()), estado=estado,
                       iteraciones=iteraciones(c, estado) if corte == "iterado" else "")
            pares_c1 = pares_c4 = 0
            for n, ag in enumerate(L["ags"]):
                p_old = float(pa0.loc[ag, "P2P"])
                b1, b4 = float(pa0.loc[ag, "C1"]), float(pa0.loc[ag, "C4"])
                cam1 = int(np.sign(round(por[n] - b1)) != np.sign(round(p_old - b1)))
                cam4 = int(np.sign(round(por[n] - b4)) != np.sign(round(p_old - b4)))
                pares_c1 += cam1
                pares_c4 += cam4
                inst.append(dict(corte=corte, caso=c, estado=estado, institucion=ag, P2P_canon_COP=p_old, P2P_COP=float(por[n]),
                                 C1_COP=b1, C4_COP=b4, signo_C1_cambia=cam1, signo_C4_cambia=cam4))
            fil.update(pares_signo_C1_cambia=pares_c1, pares_signo_C4_cambia=pares_c4)
            filas.append(fil)
            med.di(f"{corte} {c}: P2P − C4 {fil['P2P_C4_canon_COP']/M:.3f} -> {fil['P2P_C4_COP']/M:.3f} MCOP "
                   f"({fil['dif_P2P_C4_pct']:+.2f} %); P2P − C1 {fil['P2P_C1_canon_COP']/M:.3f} -> {fil['P2P_C1_COP']/M:.3f}; "
                   f"bajo el piso de cierre {kwh_bajo:.1f} kWh {fil['iteraciones']}")
    med.ok("S2: la FIFO del saldo es el Anexo 4 sobre los residuales de las 29 corridas (1e-9 kWh)")
    med.ok("S5: C1 y C4 del libro de las 29 corridas son los del canon (1 COP)")
    med.ok("S6: P2P liquidado con la FIFO es el del libro de cada corrida, comunidad e instituciones (1 COP o 1e-6 relativo)")
    med.ok("S4: en E0, P2, K1, CV2 y SINU el secuencial con pronóstico es la esquina p2p al bit (flujos y piso) y "
           "el canon (1 COP o 1e-6 relativo)")
    med.ok("S7: el piso de toda hora-vendedor de las 29 corridas es la permuta del numeral o la bolsa de la hora")
    med.ok("B2: en E2, E3, E4, P1 y N1 el iterado se da con los dos estados del ciclo (retome, e1a0e40); el estado "
           "principal del retome es el iterado de la matriz al bit (flujos y piso)")
    T = pd.DataFrame(filas)
    med.tabla(T, "m1r_corte.csv")
    med.tabla(pd.DataFrame(inst), "m1r_corte_instituciones.csv")
    fuente = "articulo_r1_resuelta_2026-11-21/m1r_corte.csv"
    for f in filas:
        p = f"m1r__{f['corte']}__{f['caso']}__" + ("" if f["estado"] == "registrado" else f["estado"] + "__")
        for k in ("dif", "P2P_C4", "P2P_C4_canon", "P2P_C1", "P2P_C1_canon", "vendido_bajo_piso_cierre"):
            med.pon(p + k, f[f"{k}_COP"] / M, "MCOP", fuente)
        for k in ("dif_P2P_C4_pct", "dif_P2P_C1_pct"):
            if np.isfinite(f[k]):
                med.pon(p + k, f[k], "%", fuente)
        for k in ("transado_kwh", "transado_canon_kwh", "vendido_bajo_piso_cierre_kwh"):
            med.pon(p + k, f[k], "kWh", fuente)
        for k in ("signo_C4_cambia", "signo_C1_cambia", "pares_signo_C1_cambia", "pares_signo_C4_cambia",
                  "horas_vendedor_bolsa", "horas_vendedor_bolsa_canon"):
            med.pon(p + k, int(f[k]), "n", fuente)
    for corte in R.CORTES:
        sub = T[(T.corte == corte) & T.caso.isin(R.CON_CORTE)]
        med.pon(f"m1r__{corte}__casos_signo_cambia", int(sub.signo_C4_cambia.sum() + sub.signo_C1_cambia.sum()), "n", fuente)
        med.pon(f"m1r__{corte}__dif_P2P_C4_pct_min", float(sub.dif_P2P_C4_pct.min()), "%", fuente)
        med.pon(f"m1r__{corte}__dif_P2P_C4_pct_max", float(sub.dif_P2P_C4_pct.max()), "%", fuente)
        med.pon(f"m1r__{corte}__pares_signo_cambia", int(sub.pares_signo_C1_cambia.sum() + sub.pares_signo_C4_cambia.sum()),
                "n", fuente)
    # B2: el intervalo entre los dos estados del ciclo
    for c in CICLAN:
        sub = T[(T.corte == "iterado") & (T.caso == c)]
        for k in ("dif_P2P_C4_pct", "dif_P2P_C1_pct"):
            med.pon(f"m1r__iterado__{c}__{k}_min", float(sub[k].min()), "%", fuente)
            med.pon(f"m1r__iterado__{c}__{k}_max", float(sub[k].max()), "%", fuente)
    med.cierra()
    return 0


if __name__ == "__main__":
    sys.exit(main())
