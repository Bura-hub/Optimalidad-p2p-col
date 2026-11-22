"""
m9_tope_precio.py — El tope del precio único en la tarifa del comprador
(revisión r1, III-B, duda I-5; CANON §14.41)
===============================================================================
Actividad 1.1. Recalcula desde los almacenes del canon con huella (matriz del
2026-09-19, tablas `flujos` y `horas`) lo que midió la comprobación de r4
(`revision_r1/comprobaciones_r4.md`, punto 3), sin copiar sus cifras:

  - las horas con mercado (volumen > 0 en `horas`) y las horas en que el tope
    actúa: algún comprador servido tiene `techo_comprador` < `precio_uniforme`
    − 1e-3 y paga `precio` = `techo_comprador` (1e-3: el float32 del almacén);
  - la energía de esas horas y la de los compradores topados;
  - el ingreso de los vendedores: Σ precio·kWh = Σ precio_reposo·kWh en cada hora;
  - ningún vendedor despachado cobra bajo su piso, por transacción ni de media;
  - el traslado entre compradores: Σ_topados (π̄ − techo_i)·q_i, con π̄ el
    ingreso del reposo sobre la energía de la hora;
  - el ahorro del intercambio Σ (techo − piso)·kWh.

Compuertas: la energía topada es `kwh_al_techo_nueva` de
`compara_matriz_reposo.csv` (0,01 kWh) y el ahorro del intercambio es
`com__<caso>__banda` de e1/L (1 COP), en los 13 casos.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import ar2_comun as R

TOL = 1e-3


def main() -> int:
    med = R.Medicion("m9", "el tope del precio único en la tarifa del comprador")
    comp = pd.read_csv(R.AS.lee("compara_matriz_reposo.csv", "comparacion"), comment="#")
    comp = comp[comp.institucion == "comunidad"].set_index("caso")
    cif = R.A1.cifras_articulo()
    filas = []
    for c in R.CASOS:
        fl = R.AS.almacen(c, "flujos").astype({k: "float64" for k in
                                                ("kwh", "precio", "precio_reposo", "techo_comprador", "piso_vendedor")})
        # los flujos de 0 kWh (pares sin energia que el almacen tambien anota)
        # no son transacciones: ni cobran ni pagan
        n0 = int((fl.kwh <= 0).sum())
        fl = fl[fl.kwh > 0].copy()
        h = R.AS.almacen(c, "horas")
        con = h[h.volumen.astype(float) > 0]
        pu = h.set_index("hora").precio_uniforme.astype(float)
        fl["pu"] = fl.hora.map(pu)
        top = (fl.techo_comprador < fl.pu - TOL) & ((fl.precio - fl.techo_comprador).abs() <= TOL) & (fl.kwh > 0)
        horas_top = set(fl.hora[top])
        E = fl.groupby("hora").kwh.sum()
        ing = (fl.kwh * fl.precio).groupby(fl.hora).sum()
        ing_rep = (fl.kwh * fl.precio_reposo).groupby(fl.hora).sum()
        pbar = ing_rep / E
        fl["pbar"] = fl.hora.map(pbar)
        # el tope solo aparece en compradores: un comprador topado lo es en todos sus flujos de la hora
        qtop = fl[top].groupby(["hora", "comprador"]).agg(q=("kwh", "sum"), techo=("techo_comprador", "first"),
                                                          pbar=("pbar", "first"))
        traslado = float(((qtop.pbar - qtop.techo) * qtop.q).sum())
        med.exige(bool((qtop.pbar > qtop.techo).all()), f"{c}: un comprador topado no pagaria mas que su tarifa sin el tope")
        ahorro = float(((fl.techo_comprador - fl.piso_vendedor) * fl.kwh).sum())
        ahorro_top = float(((fl.techo_comprador - fl.piso_vendedor) * fl.kwh)[fl.hora.isin(horas_top)].sum())
        dif_ing = float((ing - ing_rep).abs().max()) if len(ing) else 0.0
        bajo_tx = int((fl.precio < fl.piso_vendedor - TOL).sum())
        med_v = fl.groupby(["hora", "vendedor"]).apply(
            lambda x: pd.Series(dict(p=(x.kwh * x.precio).sum() / x.kwh.sum(), piso=x.piso_vendedor.iloc[0])),
            include_groups=False) if len(fl) else pd.DataFrame(columns=["p", "piso"])
        bajo_med = int((med_v.p < med_v.piso - TOL).sum())
        en_top = med_v[med_v.index.get_level_values(0).isin(horas_top)]
        margen_top = float((en_top.p - en_top.piso).min()) if len(en_top) else np.nan
        sobre_tarifa = int((fl.precio > fl.techo_comprador + TOL).sum())
        kwh_top = float(fl.kwh[top].sum())
        med.exige(abs(kwh_top - float(comp.loc[c, "kwh_al_techo_nueva"])) <= 0.01,
                  f"{c}: energía topada {kwh_top:.3f} frente a kwh_al_techo_nueva {float(comp.loc[c, 'kwh_al_techo_nueva']):.3f}")
        med.exige(abs(ahorro / R.M - float(cif[f"com__{c}__banda"])) * R.M <= 1.0,
                  f"{c}: ahorro del intercambio distinto de com__{c}__banda")
        med.exige(bajo_tx == 0 and bajo_med == 0 and sobre_tarifa == 0 and dif_ing <= 1e-2,
                  f"{c}: alguien cobra bajo su piso ({bajo_tx}, {bajo_med}), paga sobre su tarifa ({sobre_tarifa}) "
                  f"o el ingreso no se conserva ({dif_ing:.4f})")
        kwh_horas_top = float(E[E.index.isin(horas_top)].sum())
        filas.append(dict(caso=c, horas_mercado=int(len(con)), horas_tope=len(horas_top),
                          horas_tope_pct=100 * len(horas_top) / len(con), kwh_transado=float(E.sum()),
                          kwh_horas_tope=kwh_horas_top, kwh_horas_tope_pct=100 * kwh_horas_top / float(E.sum()),
                          kwh_topados=kwh_top, kwh_topados_pct=100 * kwh_top / float(E.sum()),
                          traslado_COP=traslado, ahorro_COP=ahorro, ahorro_horas_tope_COP=ahorro_top,
                          traslado_pct_ahorro=100 * traslado / ahorro,
                          traslado_pct_ahorro_horas_tope=100 * traslado / ahorro_top if ahorro_top > 0 else np.nan,
                          ingreso_dif_max_COP=dif_ing, bajo_piso_transacciones=bajo_tx, bajo_piso_vendedor_hora=bajo_med,
                          margen_min_horas_tope=margen_top, sobre_tarifa=sobre_tarifa))
        med.di(f"{c}: {len(horas_top)} de {len(con)} horas con tope; traslado {traslado:,.0f} COP; {n0} flujos de 0 kWh fuera")
    med.ok("energía de los compradores topados = kwh_al_techo_nueva de compara_matriz_reposo.csv (0,01 kWh) en los 13 casos")
    med.ok("ahorro del intercambio Σ (techo − piso)·kWh = com__<caso>__banda de e1/L (1 COP) en los 13 casos")
    med.ok("en los 13 casos: ingreso conservado (0,01 COP por hora), nadie cobra bajo su piso (por transacción ni de "
           "media), nadie paga sobre su tarifa, y todo topado pagaría más que su tarifa sin el tope")
    T = pd.DataFrame(filas)
    med.tabla(T, "m9_tope.csv")
    fuente = "articulo_r1_resuelta_2026-11-21/m9_tope.csv"
    for f in filas:
        p = f"m9__{f['caso']}__"
        for k in ("horas_mercado", "horas_tope", "bajo_piso_transacciones", "bajo_piso_vendedor_hora", "sobre_tarifa"):
            med.pon(p + k, int(f[k]), "n", fuente)
        for k, u in (("horas_tope_pct", "%"), ("kwh_horas_tope", "kWh"), ("kwh_horas_tope_pct", "%"),
                     ("kwh_topados", "kWh"), ("kwh_topados_pct", "%"), ("traslado_COP", "COP"), ("ahorro_COP", "COP"),
                     ("traslado_pct_ahorro", "%"), ("ingreso_dif_max_COP", "COP")):
            med.pon(p + k, float(f[k]), u, fuente)
        for k, u in (("traslado_pct_ahorro_horas_tope", "%"), ("margen_min_horas_tope", "COP/kWh")):
            if np.isfinite(f[k]):
                med.pon(p + k, float(f[k]), u, fuente)
    med.pon("m9__13casos__horas_tope", int(T.horas_tope.sum()), "n", fuente)
    med.pon("m9__13casos__horas_mercado", int(T.horas_mercado.sum()), "n", fuente)
    med.pon("m9__13casos__traslado_COP", float(T.traslado_COP.sum()), "COP", fuente)
    med.pon("m9__13casos__bajo_piso", int(T.bajo_piso_transacciones.sum() + T.bajo_piso_vendedor_hora.sum()), "n", fuente)
    med.cierra()
    return 0


if __name__ == "__main__":
    sys.exit(main())
