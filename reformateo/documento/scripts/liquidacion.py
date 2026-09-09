"""
La liquidación por institución: qué le cobran, qué le pagan y qué se ahorra.

ES LO QUE EL ASESOR PIDIÓ EN LA REUNIÓN PREPARATORIA DEL FORO, y lo dijo así:

    «con lo regulatorio está saliéndole a 900 pesos, al usuario le están
     cobrando 900 pesos, pero los excedentes se los están pagando a 200.
     Mientras que en el óptimo, al vendedor le están pagando mucho más»

    «Así sea que tuvieras los resultados PARA UNA ENTIDAD, ¿cómo hacer esa
     verificación?»

El mínimo exigible era **una sola entidad**. Aquí están las cinco, mes a mes, y
además la misma cuenta para los cinco mecanismos regulatorios y no solo para el
mercado.

QUÉ HACE, Y LO QUE NO HACE. Lee del almacén de la corrida y **no vuelve a
simular**. Cada cifra que imprime es una agregación de filas que la corrida
oficial escribió, de modo que no puede discrepar de la tabla publicada: la
compuerta del desglose por hora prueba que esas filas suman exactamente el
total que el motor reporta.

LAS CUATRO COLUMNAS DE LA PRIMERA TABLA, que son las que el asesor pidió:

  · qué le cobra la red por la energía que importa, al costo unitario de su
    comercializador, que es su techo;
  · a cuánto le paga la red la que exporta, que es su piso;
  · a cuánto compra y vende dentro de la comunidad, que es el precio acordado;
  · y la diferencia, que es lo que el mecanismo le deja.

LA SEGUNDA TABLA pone al lado el beneficio que cada uno de los cinco mecanismos
regulatorios le liquidaría a esa misma institución en ese mismo mes. Es la
comparación que permite decirle a un rector qué le conviene, que es la pregunta
que una ponencia tiene que poder contestar.

Uso:
    python liquidacion.py CARPETA_DEL_ALMACEN
    python liquidacion.py CARPETA_DEL_ALMACEN --cobertura m3 --periodo fecha
    python liquidacion.py CARPETA_DEL_ALMACEN --institucion Udenar
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

PERIODOS = ("mes", "fecha", "hora_del_dia", "dia_semana")


def _tasa(dinero, energia):
    """El precio efectivo: dinero entre energía, y nada donde no hubo energía."""
    e = np.asarray(energia, dtype=float)
    return np.where(e > 1e-9,
                    np.asarray(dinero, dtype=float) / np.maximum(e, 1e-12),
                    np.nan)


def factura(destino, cobertura: str, periodo: str = "mes") -> pd.DataFrame:
    """La factura de cada institución en cada período.

    Se construye sobre dos tablas del almacén: la de agentes, que trae la
    energía y la banda de cada institución hora a hora, y la de flujos, que
    trae el precio al que se cerró cada intercambio.
    """
    from core.almacen import lee

    ag = lee(destino, cobertura, "agentes")
    fl = lee(destino, cobertura, "flujos")
    if ag.empty:
        raise ValueError(
            f"la tabla de agentes del almacén está vacía en {destino}. La "
            f"llena la corrida con la bandera del almacén activada.")
    if periodo == "fecha":
        ag = ag.copy()
        ag["fecha"] = pd.to_datetime(ag["fecha"]).dt.date
        if not fl.empty:
            fl = fl.copy()
            fl["fecha"] = pd.to_datetime(fl["fecha"]).dt.date

    # Lo que cruza la frontera con la red, valorado a la banda de cada hora.
    ag = ag.copy()
    ag["cobro_red"] = ag["compra_red"] * ag["techo"]
    ag["pago_red"] = ag["vende_red"] * ag["piso"]
    # Y lo que HABRÍA cruzado sin mercado, que es el contrafáctico contra el
    # que se mide: todo el faltante al techo y todo el sobrante al piso.
    ag["cobro_sin_mercado"] = ag["faltante"] * ag["techo"]
    ag["pago_sin_mercado"] = ag["sobrante"] * ag["piso"]

    g = (ag.groupby([periodo, "agente"], observed=True)
           .agg(kwh_compra_red=("compra_red", "sum"),
                kwh_vende_red=("vende_red", "sum"),
                kwh_compra_p2p=("compra_p2p", "sum"),
                kwh_vende_p2p=("vende_p2p", "sum"),
                kwh_autoconsumo=("autoconsumo", "sum"),
                faltante=("faltante", "sum"),
                sobrante=("sobrante", "sum"),
                cobro_red=("cobro_red", "sum"),
                pago_red=("pago_red", "sum"),
                cobro_sin_mercado=("cobro_sin_mercado", "sum"),
                pago_sin_mercado=("pago_sin_mercado", "sum"),
                techo_medio=("techo", "mean"),
                piso_medio=("piso", "mean"))
           .reset_index())

    # El dinero que se mueve DENTRO de la comunidad, por institución.
    if not fl.empty:
        # La tabla de flujos ya trae el valor de cada intercambio, que es la
        # energia por el precio acordado. No se recalcula.
        v = (fl.groupby([periodo, "vendedor"], observed=True)["valor"].sum()
               .rename("cobra_dentro").reset_index()
               .rename(columns={"vendedor": "agente"}))
        c = (fl.groupby([periodo, "comprador"], observed=True)["valor"].sum()
               .rename("paga_dentro").reset_index()
               .rename(columns={"comprador": "agente"}))
        g = g.merge(v, on=[periodo, "agente"], how="left")
        g = g.merge(c, on=[periodo, "agente"], how="left")
    g["cobra_dentro"] = g.get("cobra_dentro", 0.0).fillna(0.0)
    g["paga_dentro"] = g.get("paga_dentro", 0.0).fillna(0.0)

    # Lo que paga en total, con mercado y sin él. La diferencia es lo que el
    # mecanismo le deja, y es la columna que el asesor pidió ver.
    g["paga_con_mercado"] = g["cobro_red"] + g["paga_dentro"] - g["pago_red"] \
        - g["cobra_dentro"]
    g["paga_sin_mercado"] = g["cobro_sin_mercado"] - g["pago_sin_mercado"]
    g["ahorro"] = g["paga_sin_mercado"] - g["paga_con_mercado"]

    # Los precios efectivos, que son la frase del asesor hecha número.
    #
    # PONDERADOS POR ENERGÍA, no por hora. La media simple del techo y del piso
    # a lo largo del día cuenta igual una hora en la que la institución mueve
    # treinta kilovatios y una en la que no mueve ninguno, y sale un precio al
    # que nadie compró ni vendió nada. El precio efectivo es el dinero dividido
    # por la energía, y es el único comparable con el de dentro.
    # Y hay DOS tasas de red, no una, porque preguntan cosas distintas:
    #
    #   la efectiva      lo que la red le cobró y le pagó de verdad, por la
    #                    energía que sí cruzó la frontera;
    #   la contrafáctica lo que le habría cobrado y pagado por TODO su
    #                    faltante y TODO su sobrante, es decir si no hubiera
    #                    mercado.
    #
    # La que el asesor quiere comparar contra el precio de dentro es la
    # SEGUNDA, y por una razón que se ve en el primer día que se mira: una
    # institución que coloca todo su excedente dentro de la comunidad no le
    # vende nada a la red, y su tasa efectiva no existe. Decir que no existe
    # sería cierto y sería inútil; lo que hay que decir es a cuánto se lo
    # habrían pagado.
    with np.errstate(divide="ignore", invalid="ignore"):
        g["precio_compra_red"] = _tasa(g["cobro_sin_mercado"], g["faltante"]) \
            if "faltante" in g.columns else np.nan
        g["precio_venta_red"] = _tasa(g["pago_sin_mercado"], g["sobrante"]) \
            if "sobrante" in g.columns else np.nan
        g["precio_compra_red_efectivo"] = _tasa(g["cobro_red"],
                                                g["kwh_compra_red"])
        g["precio_venta_red_efectivo"] = _tasa(g["pago_red"],
                                               g["kwh_vende_red"])
        g["precio_medio_compra_dentro"] = _tasa(g["paga_dentro"],
                                                g["kwh_compra_p2p"])
        g["precio_medio_venta_dentro"] = _tasa(g["cobra_dentro"],
                                               g["kwh_vende_p2p"])
    return g.sort_values([periodo, "agente"]).reset_index(drop=True)


def por_mecanismo(destino, cobertura: str,
                  periodo: str = "mes") -> pd.DataFrame:
    """El beneficio que cada mecanismo le liquida a cada institución."""
    from core.almacen import lee

    d = lee(destino, cobertura, "escenarios")
    if d.empty:
        raise ValueError(
            f"la tabla de escenarios del almacén está vacía en {destino}.")
    if periodo == "fecha":
        d = d.copy()
        d["fecha"] = pd.to_datetime(d["fecha"]).dt.date
    t = (d.groupby([periodo, "agente", "escenario"], observed=True)["valor"]
          .sum().reset_index())
    return (t.pivot(index=[periodo, "agente"], columns="escenario",
                    values="valor").reset_index())


def _m(x) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return f"{x:,.0f}".replace(",", " ")


def _p(x) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return f"{x:,.1f}".replace(".", ",")


def informa(destino, cobertura: str, periodo: str = "mes",
            institucion: str | None = None) -> None:
    f = factura(destino, cobertura, periodo)
    m = por_mecanismo(destino, cobertura, periodo)
    if institucion:
        f = f[f.agente == institucion]
        m = m[m.agente == institucion]
        if f.empty:
            raise ValueError(f"no hay una institución llamada {institucion!r} "
                             f"en la frontera {cobertura.upper()}")

    print("=" * 96)
    print(f"  LA FACTURA DE CADA INSTITUCIÓN  —  frontera {cobertura.upper()}, "
          f"por {periodo.replace('_', ' ')}")
    print("  (a cuanto le cobraria y le pagaria la red, a cuanto compra y "
          "vende dentro, y lo que se ahorra)")
    print("=" * 96)
    print(f"  {'Período':<11} {'Institución':<10} "
          f"{'compra red':>11} {'vende red':>10} {'compra dentro':>14} "
          f"{'vende dentro':>13} {'ahorro':>11}")
    print(f"  {'':11} {'':10} {'COP/kWh':>11} {'COP/kWh':>10} "
          f"{'COP/kWh':>14} {'COP/kWh':>13} {'COP':>11}")
    print("-" * 96)
    for p, sub in f.groupby(periodo, observed=True):
        for _, r in sub.iterrows():
            print(f"  {str(p):<11} {r['agente']:<10} "
                  f"{_p(r['precio_compra_red']):>11} "
                  f"{_p(r['precio_venta_red']):>10} "
                  f"{_p(r['precio_medio_compra_dentro']):>14} "
                  f"{_p(r['precio_medio_venta_dentro']):>13} "
                  f"{_m(r['ahorro']):>11}")
        print()

    escs = [c for c in ("P2P", "C1", "C2", "C3", "C4", "C5") if c in m.columns]
    print("=" * 96)
    print(f"  Y LO QUE LE DEJARÍA CADA MECANISMO REGULATORIO (COP)")
    print("=" * 96)
    cab = "".join(f"{e:>13}" for e in escs)
    print(f"  {'Período':<11} {'Institución':<10}{cab}   {'mejor':>10}")
    print("-" * 96)
    for p, sub in m.groupby(periodo, observed=True):
        for _, r in sub.iterrows():
            vals = {e: float(r[e]) for e in escs if pd.notna(r[e])}
            mejor = max(vals, key=vals.get) if vals else "—"
            fila = "".join(f"{_m(r.get(e)):>13}" for e in escs)
            print(f"  {str(p):<11} {r['agente']:<10}{fila}   {mejor:>10}")
        print()

    # La frase del asesor, medida. Es el titular de la ponencia.
    # La frase se dice con las tasas del HORIZONTE entero, no con la media de
    # las tasas de cada período, que pesaría igual un mes flojo y uno fuerte.
    tot = f.groupby("agente", observed=True).agg(
        cobro=("cobro_sin_mercado", "sum"), kwh_c=("faltante", "sum"),
        pago=("pago_sin_mercado", "sum"), kwh_v=("sobrante", "sum"),
        dentro_c=("paga_dentro", "sum"), kwh_dc=("kwh_compra_p2p", "sum"),
        dentro_v=("cobra_dentro", "sum"), kwh_dv=("kwh_vende_p2p", "sum"),
        ahorro=("ahorro", "sum"))
    with np.errstate(divide="ignore", invalid="ignore"):
        tot["techo"] = _tasa(tot["cobro"], tot["kwh_c"])
        tot["piso"] = _tasa(tot["pago"], tot["kwh_v"])
        tot["compra"] = _tasa(tot["dentro_c"], tot["kwh_dc"])
        tot["venta"] = _tasa(tot["dentro_v"], tot["kwh_dv"])
    print("=" * 96)
    print("  EN UNA FRASE, que es la que el asesor pidió poder decir:")
    print("=" * 96)
    for n, r in tot.iterrows():
        if np.isfinite(r["venta"]):
            print(f"  A {n} la red le paga el excedente a "
                  f"{_p(r['piso'])} COP/kWh; dentro de la comunidad lo vende a "
                  f"{_p(r['venta'])}.")
        if np.isfinite(r["compra"]):
            print(f"  A {n} la red le cobra la energía a "
                  f"{_p(r['techo'])} COP/kWh; dentro de la comunidad la compra "
                  f"a {_p(r['compra'])}.")
    print("=" * 96)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("destino", help="carpeta del almacén de la corrida")
    ap.add_argument("--cobertura", default="m1")
    ap.add_argument("--periodo", default="mes", choices=list(PERIODOS))
    ap.add_argument("--institucion", default=None,
                    help="una sola institución, que es el mínimo que se pidió")
    a = ap.parse_args()
    informa(a.destino, a.cobertura, a.periodo, a.institucion)


if __name__ == "__main__":
    main()
