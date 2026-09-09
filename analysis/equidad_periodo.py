"""
La equidad por mes, por día y por hora del día (C-165).

QUE FALTABA, Y POR QUE IMPORTA. El coeficiente de Gini, el precio de la
equidad y el cociente frente al colectivo **solo existían agregados al
horizonte entero**. De modo que la tesis podía decir que el mercado reparte de
tal manera en nueve meses, pero no en cuáles: ni en qué meses reparte mejor, ni
a qué horas del día, ni si el reparto de un lunes se parece al de un domingo.

Es media pregunta del capítulo de equidad, y toda la de la discusión de precios.

DE DONDE SALE, Y NO SE VUELVE A SIMULAR. De la tabla de escenarios del almacén,
que trae una fila por hora, mecanismo y agente con el dinero **anotado en la
hora que lo genera**. La compuerta de C-165 prueba que esas anotaciones suman
exactamente el total publicado, de modo que cualquier agregación por período es
una partición de la cifra oficial y no una segunda cuenta.

LAS TRES MÉTRICAS, Y QUÉ MIDE CADA UNA:

  · el coeficiente de Gini, que mide **cuán desigual** es el reparto entre los
    agentes de ese período;
  · el cociente frente al colectivo, que mide **cuánto mejor o peor** le va al
    mercado que al mecanismo regulatorio colectivo en ese período;
  · el precio de la equidad, que mide **cuánto beneficio total cuesta** elegir
    el mecanismo más equitativo en vez del más eficiente, en ese período.

UNA CAUTELA QUE HAY QUE DECLARAR. El índice de equidad de los escenarios parte
a los agentes en dos grupos por su cobertura solar, y esa partición se calcula
**una sola vez sobre el horizonte entero**, no período a período. Cambiarla en
cada mes haría que el índice de enero y el de julio hablaran de grupos
distintos, y dejarían de ser comparables. Aquí se conserva la partición global.

Actividad 3.2.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd

PERIODOS = ("mes", "fecha", "hora_del_dia", "dia_semana")


def _gini(v: np.ndarray) -> float:
    """El mismo coeficiente que usa el motor, sobre valores absolutos."""
    x = np.sort(np.abs(np.asarray(v, dtype=float)))
    n = x.size
    if n == 0:
        return 0.0
    s = float(x.sum())
    if s <= 1e-12:
        return 0.0
    i = np.arange(1, n + 1)
    return float((2.0 * float(np.dot(i, x)) - (n + 1) * s) / (n * s))


def tabla(destino: Union[str, Path], cobertura: str,
          periodo: str = "mes",
          colectivo: str = "C4",
          mercado: str = "P2P") -> pd.DataFrame:
    """Una fila por período y mecanismo, con beneficio, Gini y cociente.

    Parameters
    ----------
    destino, cobertura
        El almacén de la corrida y la frontera que se lee.
    periodo
        ``mes``, ``fecha`` (el día), ``hora_del_dia`` o ``dia_semana``.
    colectivo
        El mecanismo contra el que se calcula el cociente. Por defecto el
        colectivo horario, que es el contraste que el modelo base plantea.
    mercado
        El mecanismo que se compara. Por defecto el mercado entre pares.
    """
    if periodo not in PERIODOS:
        raise ValueError(f"periodo={periodo!r}; se espera uno de {PERIODOS}")
    from core.almacen import lee

    d = lee(destino, cobertura, "escenarios")
    if d.empty:
        raise ValueError(
            f"la tabla de escenarios del almacén está vacía en {destino}. "
            f"La llena la corrida con la bandera del almacén activada; sin "
            f"ella no hay de dónde sacar las métricas por período.")

    # El almacen guarda la marca de tiempo completa. Agrupar por ella daria
    # una fila por HORA con la etiqueta de un dia, que es justo la confusion
    # que este modulo existe para deshacer.
    if periodo == "fecha":
        d = d.copy()
        d["fecha"] = pd.to_datetime(d["fecha"]).dt.date

    # Beneficio de cada agente en cada periodo y mecanismo.
    g = (d.groupby([periodo, "escenario", "agente"], observed=True)["valor"]
          .sum().reset_index())

    filas = []
    for (p, esc), sub in g.groupby([periodo, "escenario"], observed=True):
        v = sub["valor"].to_numpy(dtype=float)
        filas.append({periodo: p, "escenario": esc,
                      "beneficio_COP": float(v.sum()),
                      "gini": _gini(v),
                      "agentes": int(v.size)})
    t = pd.DataFrame(filas)

    # El cociente frente al colectivo, período a período. Misma definición que
    # la agregada: la diferencia relativa al beneficio del mercado.
    piv = t.pivot(index=periodo, columns="escenario", values="beneficio_COP")
    if mercado in piv.columns and colectivo in piv.columns:
        w_m, w_c = piv[mercado], piv[colectivo]
        rpe = (w_m - w_c) / w_m.abs().clip(lower=1.0)
        t = t.merge(rpe.rename("cociente_vs_colectivo").reset_index(),
                    on=periodo, how="left")

    return t.sort_values([periodo, "escenario"]).reset_index(drop=True)


def precio_de_la_equidad(t: pd.DataFrame, periodo: str = "mes") -> pd.DataFrame:
    """El precio de la equidad período a período.

    Es la definición de Bertsimas, Farias y Trichakis: cuánto beneficio total
    se pierde al elegir el mecanismo **más equitativo** en vez del **más
    eficiente**. Aquí se calcula dentro de cada período, con los mecanismos de
    ese período, de modo que puede señalar a mecanismos distintos en meses
    distintos, y eso es un resultado, no un defecto.
    """
    filas = []
    for p, sub in t.groupby(periodo, observed=True):
        s = sub.set_index("escenario")
        eficiente = s["beneficio_COP"].idxmax()
        equitativo = s["gini"].idxmin()
        w_ef = float(s.loc[eficiente, "beneficio_COP"])
        w_eq = float(s.loc[equitativo, "beneficio_COP"])
        filas.append({
            periodo: p,
            "eficiente": eficiente, "beneficio_eficiente_COP": w_ef,
            "equitativo": equitativo, "beneficio_equitativo_COP": w_eq,
            "precio_equidad": ((w_ef - w_eq) / w_ef) if abs(w_ef) > 1e-9
                              else float("nan"),
        })
    return pd.DataFrame(filas).sort_values(periodo).reset_index(drop=True)


def imprime(destino: Union[str, Path], cobertura: str,
            periodo: str = "mes", mercado: str = "P2P") -> pd.DataFrame:
    """La tabla por consola, en el formato del resto de informes."""
    t = tabla(destino, cobertura, periodo=periodo, mercado=mercado)
    pof = precio_de_la_equidad(t, periodo=periodo)

    print(f"\n  EQUIDAD POR {periodo.replace('_', ' ').upper()}  —  "
          f"frontera {cobertura.upper()}")
    print("  " + "-" * 76)
    print(f"  {periodo:<12} {'Mecanismo':<12} {'Beneficio':>14} "
          f"{'Gini':>7} {'vs colectivo':>13}")
    for p, sub in t.groupby(periodo, observed=True):
        for _, r in sub.iterrows():
            c = r.get("cociente_vs_colectivo", float("nan"))
            print(f"  {str(p):<12} {r['escenario']:<12} "
                  f"{r['beneficio_COP']:>14,.0f} {r['gini']:>7.4f} "
                  f"{c:>13.4f}")
        print()

    print(f"  EL PRECIO DE LA EQUIDAD, {periodo.replace('_', ' ')} a "
          f"{periodo.replace('_', ' ')}")
    print("  " + "-" * 76)
    print(f"  {periodo:<12} {'más eficiente':<14} {'más equitativo':<14} "
          f"{'precio':>8}")
    for _, r in pof.iterrows():
        print(f"  {str(r[periodo]):<12} {r['eficiente']:<14} "
              f"{r['equitativo']:<14} {r['precio_equidad']:>8.4f}")
    return t


if __name__ == "__main__":
    import argparse
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("destino", help="carpeta del almacén de la corrida")
    ap.add_argument("--cobertura", default="m1")
    ap.add_argument("--periodo", default="mes", choices=list(PERIODOS))
    raw = ap.parse_args()
    imprime(raw.destino, raw.cobertura, periodo=raw.periodo)
