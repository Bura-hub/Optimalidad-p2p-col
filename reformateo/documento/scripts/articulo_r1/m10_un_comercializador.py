"""
m10_un_comercializador.py — La esquina «ninguno» (v00) con un solo
comercializador, como exige el art. 10, num. 1, de la CREG 101 072
(CANON §14.41, punto 4)
===============================================================================
Actividades 2.1 y 3.3. Revisión r1 del artículo: un árbitro objetó que v00
tiene dos comercializadores dentro de un mismo autogenerador colectivo, y el
art. 10, num. 1, exige que todas las fronteras de un AC las represente el
mismo agente (`revision_r1/art10_comercializadores.md`). Decisión del autor
(2026-11-22): se declara sin otra corrida; el canon conserva las dos tarifas,
como C4 (H-97); se dice que, con un solo comercializador, v00 iguala a C4 en
E0 y SINU.

No simula. Sobre los almacenes de la esquina «ninguno» (r1m/) y el canon
(e1/S, la caché de bolsa), con `scenarios.esquinas_supuestos`:

  v00 − C4                    la cifra de m2r (dos tarifas), reproducida
  sin pares cruzados          v00 sin los flujos entre miembros de
                              comercializador distinto, menos C4
  sin intercambio             v00 con v = q = 0 (el PDE de la inyección), menos C4
  un solo comercializador     v00 y C4 con la tarifa (CU y kappa·Cv + Theta) de
                              un miembro del A, o del B, para todos

Los comercializadores salen de las tarifas: los miembros con la misma CU en
todas las horas son del mismo comercializador.

Cuándo la cifra con un solo comercializador es EXACTA y cuándo INDICATIVA. Con
una sola tarifa, el crédito de un kWh vale lo mismo para cualquier miembro. Si
además nadie tiene exceso, ni con el PDE del mercado ni con el reparto igual,
el total del colectivo no depende del PDE ni de lo transado: v00 = C4 al peso,
y un mercado resuelto con esa tarifa (banda cero antes del corte, y sin corte)
daría lo mismo. Si hay exceso (casos con corte), el total depende de qué
miembro recibe el fondo y en qué hora, y con una sola tarifa el mercado
transaría otra cosa: la cifra sobre los flujos de dos tarifas es indicativa,
y la exacta exige resolver de nuevo «ninguno» con la tarifa única.

Compuertas:
  U1  v00 reproduce `m2r__<caso>__v00_menos_C4` (1 COP o el float32) y C4 con
      las mismas funciones es el del canon (1 COP)
  U2  los miembros de un mismo comercializador tienen la misma CU y el mismo
      kappa·Cv + Theta en todas las horas, y hay exactamente dos comercializadores
  U3  la descomposición cierra: (v00 − v00 sin cruzados) + (v00 sin cruzados − C4)
      = v00 − C4; y donde nadie tiene exceso, el término de los pares cruzados
      es su banda, Σ (techo del comprador − piso del vendedor)·kWh (1 COP)
  U4  donde la cifra es exacta, v00 − C4 con un solo comercializador es 0 al
      peso con las dos tarifas (A y B) y con los tres PDE
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import ar2_comun as R
from scenarios.esquinas_supuestos import colectivo, liquida_esquina, pesos_mes

M = R.M
CINCO = ["E0", "E3", "E4", "I1", "SINU"]


def tol(ref) -> float:
    return max(1.0, 1e-6 * abs(float(ref)))


def main() -> int:
    med = R.Medicion("m10", "la esquina ninguno con un solo comercializador (art. 10 de la CREG 101 072)")
    DAT, pb = R.bases()
    med.ok("almacenes canónicos con sus compuertas y la bolsa de la caché igual a la reconstruida")
    m2r = pd.read_csv(R.SALIDA / "m2r_factorial.csv").set_index("caso")
    filas = []
    for c in CINCO:
        L = DAT[c]
        ags, N = L["ags"], L["N"]
        CU, ded1, ded4, mes = L["CU"], L["ded1"], L["ded4"], L["mes"]
        G, D, s, d = L["G"], L["D"], L["s"], L["d"]
        C4 = float(R.AS.resumen(c)["C4"])
        dir_ = R.dir_corrida("esquina", "ninguno", c)
        X = R.carga_corrida(med, dir_, c, L)
        # U2: los comercializadores, de las tarifas
        grupos = []
        for i in range(N):
            for g in grupos:
                if np.array_equal(CU[i], CU[g[0]]):
                    g.append(i)
                    break
            else:
                grupos.append([i])
        med.exige(len(grupos) == 2, f"U2 {c}: {len(grupos)} comercializadores, se esperaban 2")
        for g in grupos:
            med.exige(all(np.array_equal(ded4[i], ded4[g[0]]) for i in g),
                      f"U2 {c}: miembros del mismo comercializador con distinta deducción del caso 2")
        com = {ags[i]: k for k, g in enumerate(grupos) for i in g}
        iA = grupos[0][0] if len(grupos[0]) > 1 else grupos[1][0]      # el A es el de varios miembros
        iB = grupos[1][0] if len(grupos[0]) > 1 else grupos[0][0]
        # U1: v00 y C4
        v00, _ = liquida_esquina("ninguno", G, D, X["v"], X["q"], CU, ded1, ded4, mes, pb)
        v00 = float(v00.sum())
        med.exige(abs((v00 - C4) / M - float(m2r.loc[c, "v00_menos_C4_COP"]) / M) * M <= tol(C4),
                  f"U1 {c}: v00 − C4 no reproduce m2r")
        igual = {m: np.full(N, 1.0 / N) for m in np.unique(mes)}
        auto = np.minimum(G, D) * CU
        r4, ex4 = colectivo(s, d, CU, ded4, mes, pb, igual)
        c4f = float((auto + r4).sum())
        med.exige(abs(c4f - C4) <= tol(C4), f"U1 {c}: C4 con las mismas funciones {c4f:.2f} frente al canon {C4:.2f}")
        # sin pares cruzados
        fl = R._lee_partes(med, dir_, "flujos").astype({"kwh": "float64"})
        cruz = np.array([com[a] != com[b] for a, b in zip(fl.vendedor, fl.comprador)], dtype=bool)
        f2 = fl[~cruz]

        def mat(f, col):
            return f.groupby([col, "hora"]).kwh.sum().unstack(fill_value=0.0).reindex(
                index=ags, columns=range(6144), fill_value=0.0).to_numpy()

        v2, q2 = mat(f2, "vendedor"), mat(f2, "comprador")
        v00_sc = float(liquida_esquina("ninguno", G, D, v2, q2, CU, ded1, ded4, mes, pb)[0].sum())
        v00_0 = float(liquida_esquina("ninguno", G, D, 0 * v2, 0 * q2, CU, ded1, ded4, mes, pb)[0].sum())
        banda_cruz = float(((fl.techo_comprador.astype(float) - fl.piso_vendedor.astype(float)) * fl.kwh)[cruz].sum())
        sr = np.maximum(s - X["v"], 0.0)
        pde_m = pesos_mes(X["q"] + sr, mes)
        _, ex_m = colectivo(s, d, CU, ded4, mes, pb, pde_m)
        sin_exceso = float(ex_m.sum()) == 0.0 and float(ex4.sum()) == 0.0
        med.exige(abs((v00 - v00_sc) + (v00_sc - C4) - (v00 - C4)) <= 1e-6, f"U3 {c}: la descomposición no cierra")
        if sin_exceso:
            med.exige(abs((v00 - v00_sc) - banda_cruz) <= 1.0,
                      f"U3 {c}: el término de los pares cruzados {v00 - v00_sc:.2f} no es su banda {banda_cruz:.2f}")
        # un solo comercializador
        uno = {}
        for nom, k in (("A", iA), ("B", iB)):
            CUx = np.repeat(CU[k][None, :], N, 0)
            d4x = np.repeat(ded4[k][None, :], N, 0)
            autox = np.minimum(G, D) * CUx
            rq, exq = colectivo(s, d, CUx, d4x, mes, pb, pde_m)
            ri, exi = colectivo(s, d, CUx, d4x, mes, pb, igual)
            r0, ex0 = colectivo(s, d, CUx, d4x, mes, pb, pesos_mes(s, mes))
            c4x = float((autox + ri).sum())
            uno[nom] = dict(mercado=float((autox + rq).sum()) - c4x, sin_intercambio=float((autox + r0).sum()) - c4x,
                            exceso=float(exq.sum() + exi.sum() + ex0.sum()))
        exacto = sin_exceso and all(u["exceso"] == 0.0 for u in uno.values())
        if exacto:
            med.exige(all(abs(u["mercado"]) <= 1.0 and abs(u["sin_intercambio"]) <= 1.0 for u in uno.values()),
                      f"U4 {c}: con un solo comercializador y sin exceso, v00 − C4 no es 0")
        fil = dict(caso=c, exacto=int(exacto), comercializador_B=",".join(ags[i] for g in grupos if iB in g for i in g),
                   v00_menos_C4_COP=v00 - C4, sin_cruzados_menos_C4_COP=v00_sc - C4, sin_intercambio_menos_C4_COP=v00_0 - C4,
                   termino_cruzados_COP=v00 - v00_sc, termino_pde_dos_tarifas_COP=v00_sc - C4, banda_cruzados_COP=banda_cruz,
                   kwh_cruzados=float(fl.kwh[cruz].sum()), kwh_transados=float(fl.kwh.sum()),
                   exceso_kwh_dos_tarifas=float(ex_m.sum() + ex4.sum()),
                   un_comercializador_A_COP=uno["A"]["mercado"], un_comercializador_B_COP=uno["B"]["mercado"],
                   un_comercializador_A_sin_intercambio_COP=uno["A"]["sin_intercambio"],
                   un_comercializador_B_sin_intercambio_COP=uno["B"]["sin_intercambio"],
                   exceso_kwh_un_comercializador=uno["A"]["exceso"] + uno["B"]["exceso"])
        filas.append(fil)
        med.di(f"{c} ({'exacto' if exacto else 'indicativo'}): v00 − C4 {fil['v00_menos_C4_COP']/M:+.4f}; cruzados "
               f"{fil['termino_cruzados_COP']/M:+.4f} + PDE con dos tarifas {fil['termino_pde_dos_tarifas_COP']/M:+.4f}; "
               f"un comercializador A {uno['A']['mercado']/M:+.4f}, B {uno['B']['mercado']/M:+.4f} MCOP")
    exactos = [f["caso"] for f in filas if f["exacto"]]
    med.exige(exactos == ["E0", "SINU"], f"la cifra exacta es la de {exactos}, se esperaba E0 y SINU")
    med.ok("U1: v00 − C4 reproduce m2r y C4 con las mismas funciones es el del canon (1 COP o 1e-6 relativo) en los 5 casos")
    med.ok("U2: dos comercializadores, el A (varios miembros) y el B (Unicesmag), con la misma CU y la misma deducción del "
           "caso 2 dentro de cada uno")
    med.ok("U3: la descomposición cierra; en E0 y SINU el término de los pares cruzados es su banda (1 COP)")
    med.ok("U4: en E0 y SINU, sin exceso con ningún PDE, v00 − C4 con un solo comercializador (A o B) es 0 al peso; en E3, "
           "E4 e I1 hay exceso y la cifra es indicativa")
    T = pd.DataFrame(filas)
    med.tabla(T, "m10_un_comercializador.csv")
    fuente = "articulo_r1_resuelta_2026-11-21/m10_un_comercializador.csv"
    for f in filas:
        p = f"m10__{f['caso']}__"
        med.pon(p + "exacto", int(f["exacto"]), "0/1", fuente)
        for k in ("v00_menos_C4", "sin_cruzados_menos_C4", "sin_intercambio_menos_C4", "termino_cruzados",
                  "termino_pde_dos_tarifas", "banda_cruzados", "un_comercializador_A", "un_comercializador_B",
                  "un_comercializador_A_sin_intercambio", "un_comercializador_B_sin_intercambio"):
            med.pon(p + k, f[f"{k}_COP"] / M, "MCOP", fuente)
        for k in ("kwh_cruzados", "kwh_transados", "exceso_kwh_dos_tarifas", "exceso_kwh_un_comercializador"):
            med.pon(p + k, f[k], "kWh", fuente)
    med.cierra()
    return 0


if __name__ == "__main__":
    sys.exit(main())
