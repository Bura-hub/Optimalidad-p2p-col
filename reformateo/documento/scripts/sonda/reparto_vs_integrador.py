"""
Depende el reparto de la via acoplada del integrador (tarea 15, D16, H-79).

H-37 midio que el reparto de la via ALTERNADA depende del paso fijo de su
bloque comprador. La corrida oficial usa la ACOPLADA, que integra con paso
adaptativo (LSODA, tolerancias 1e-6, H-51) y nunca pasa por ese bloque. Esta
sonda mide la pregunta equivalente: si el reparto se mueve al apretar diez
veces las tolerancias o al doblar el horizonte, que con 0,05 deja sin llegar
al estacionario a un tercio de las horas.

Criterio fijado ANTES de medir: si la tajada del vendedor del agregado de la
muestra cambia menos de un punto porcentual en las dos variantes, el reparto
no depende del integrador y no se toca el codigo. Si cambia mas, se corrige
antes de la corrida oficial el mando que la mueva: la tolerancia o el
horizonte del acoplado.

Un segundo criterio, fijado tambien antes de medir: si el excedente del
agregado de la muestra cambia mas de 0,1 % en alguna variante, el integrador
mueve el agregado del mercado y no solo su reparto, y se corrige antes de la
corrida oficial en cualquier caso.

La muestra son horas con mercado que resuelven las tres variantes, recorridas
en orden aleatorio con semilla fija en la frontera principal hasta reunir las
pedidas. Una variante cuya integracion falla no cuenta como resuelta ni entra
al agregado, igual que en produccion (core/ems_p2p.py, la hora sin exito se
marca sin mercado). En local solo el humo (--horas 2); la medicion
(--horas 20) va al servidor.

`--factor-generacion F` escala la generacion de las cinco como el orquestador
(acepta 1/7), para medir en un caso de la matriz de escalado (spec 4.12).

Codigo de salida: 0 si los dos criterios se cumplen; 1 sin datos; 2 si salta
DEPENDE o EXCEDENTE: CAMBIA, para que el lanzador detenga la cadena.

Uso:
    python reparto_vs_integrador.py --horas 2
    python reparto_vs_integrador.py --horas 20 --salida sonda_t15.csv
    python reparto_vs_integrador.py --horas 1 --factor-generacion 7
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paso_a_paso import carga, resuelve  # noqa: E402

VARIANTES = {
    "produccion": None,
    "tolerancia_x0,1": {"rtol": 1e-7, "atol": 1e-7},
    "horizonte_x2": {"t_span": (0.0, 0.10)},
}
UMBRAL_PUNTOS = 1.0
UMBRAL_EXCEDENTE_PCT = 0.1


def mide(dat: dict, r: dict) -> dict:
    """Prima del vendedor, excedente y precios en cota de una hora resuelta.

    Las mismas cuentas que `informa` de paso_a_paso.py: la prima sobre el
    piso de cada vendedor y el ahorro contra el techo de cada comprador.
    """
    k = r["k"]
    prima = ahorro = 0.0
    for a, j in enumerate(r["sids"]):
        for i in range(len(r["bids"])):
            q = float(r["P"][a, i])
            if q <= 1e-9:
                continue
            prima += (r["pi"][i] - dat["piso"][j, k]) * q
            ahorro += (r["techo_i"][i] - r["pi"][i]) * q
    en_cota = 0
    for i in range(len(r["bids"])):
        ancho = r["techo_i"][i] - r["piso_h"]
        pos = (r["pi"][i] - r["piso_h"]) / ancho if ancho > 1e-9 else 0.0
        en_cota += int(pos < 1e-6 or pos > 1 - 1e-6)
    return dict(prima_vendedor=prima, excedente=prima + ahorro,
                en_cota=en_cota, compradores=len(r["bids"]),
                exito=bool(getattr(r["tr"], "success", True)))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--horas", type=int, default=2)
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--salida", default=None)
    ap.add_argument("--factor-generacion", default="1", metavar="F",
                    help="I-8 b: escala la generacion de las cinco, como el "
                         "orquestador (acepta 1/7)")
    a = ap.parse_args()

    from data.escalado import lee_factor
    factor = lee_factor(a.factor_generacion)
    dat = carga("m1", factor_generacion=factor)
    if factor != 1.0:
        print(f"  generacion x{factor:g} (spec 4.11); el piso sigue el "
              f"numeral del art. 25 de la capacidad escalada")
    D, G = dat["D"], dat["G"]
    activas = np.flatnonzero(((G - D) > 0).any(axis=0)
                             & ((D - G) > 0).any(axis=0))
    rng = np.random.default_rng(a.semilla)
    orden = rng.permutation(activas)

    # Las horas se recorren en orden aleatorio hasta reunir las pedidas que
    # resuelven las tres variantes. Una hora con papeles en la medicion bruta
    # puede quedarse sin mercado tras el limite economico de generacion, y
    # contarla dejaria la muestra corta sin decirlo.
    filas = []
    completas = 0
    for k in orden:
        if completas >= a.horas:
            break
        filas_k = []
        for nombre, sol in VARIANTES.items():
            t0 = time.perf_counter()
            r = resuelve(dat, int(k), solucionador=sol)
            seg = time.perf_counter() - t0
            fila = dict(hora=int(k), variante=nombre, segundos=seg,
                        resuelta=r is not None)
            if r is not None:
                fila.update(mide(dat, r))
            # I-8 a: una integracion fallida no es una hora resuelta.
            # Produccion la marca sin mercado (core/ems_p2p.py, `success`
            # falso), de modo que aqui no cuenta como completa ni entra al
            # agregado.
            fila["valida"] = bool(fila["resuelta"] and fila.get("exito", False))
            filas_k.append(fila)
            marca = ("" if fila["valida"] or not fila["resuelta"]
                     else "  FALLO del integrador")
            print(f"  hora {int(k):5d}  {nombre:16s} {seg:7.1f} s{marca}")
            if not fila["valida"] and nombre == "produccion":
                break              # sin mercado: no se gastan las otras dos
        filas.extend(filas_k)
        if (len(filas_k) == len(VARIANTES)
                and all(f["valida"] for f in filas_k)):
            completas += 1
    df = pd.DataFrame(filas)
    if a.salida:
        df.to_csv(a.salida, index=False)
    if df.empty:
        print("VEREDICTO: SIN DATOS (ninguna hora con mercado)")
        return 1

    fallidas = int((df["resuelta"] & ~df["valida"]).sum())
    if fallidas:
        print(f"\nAVISO: {fallidas} variante(s) con fallo del integrador; su "
              f"hora no cuenta como completa ni entra al agregado")
    ok = df[df["valida"]]
    # Solo las horas que las tres variantes resuelven, para comparar lo mismo.
    comunes = ok.groupby("hora")["variante"].nunique()
    comunes = comunes[comunes == len(VARIANTES)].index
    ok = ok[ok["hora"].isin(comunes)]
    if ok.empty:
        print("VEREDICTO: SIN DATOS (ninguna hora resuelta por las tres)")
        return 1
    tabla = ok.groupby("variante").agg(
        prima=("prima_vendedor", "sum"), excedente=("excedente", "sum"),
        en_cota=("en_cota", "sum"), compradores=("compradores", "sum"))
    tabla["tajada_%"] = 100 * tabla["prima"] / tabla["excedente"]
    tabla["en_cota_%"] = 100 * tabla["en_cota"] / tabla["compradores"]
    base = float(tabla.loc["produccion", "tajada_%"])
    tabla["delta_puntos"] = tabla["tajada_%"] - base
    exc0 = float(tabla.loc["produccion", "excedente"])
    # Guarda de cero: sin excedente de produccion no hay cambio relativo que
    # calcular; se avisa en vez de dividir.
    exc_con_base = abs(exc0) > 1e-12
    if exc_con_base:
        tabla["excedente_delta_%"] = 100 * (tabla["excedente"] - exc0) / exc0
    else:
        tabla["excedente_delta_%"] = np.nan
        print("\nAVISO: el excedente de produccion es cero; el cambio "
              "relativo del excedente no se calcula")
    print(f"\nHoras comparadas: {len(comunes)}")
    print(tabla[["excedente", "excedente_delta_%", "tajada_%", "delta_puntos",
                 "en_cota_%"]].round(3).to_string())
    peor = float(tabla["delta_puntos"].abs().max())
    depende = not peor < UMBRAL_PUNTOS
    print(f"\nVEREDICTO: {'DEPENDE' if depende else 'NO DEPENDE'}"
          f" (peor cambio {peor:.3f} puntos; umbral {UMBRAL_PUNTOS})")
    # Con bandas distintas por agente el excedente depende de QUE parejas
    # transan y de quien se retira, no solo de cuanto se transa: si el
    # integrador no llego al estacionario puede moverse el agregado y no
    # solo el reparto (hora 663 del humo de la ronda 1).
    if exc_con_base:
        peor_exc = float(tabla["excedente_delta_%"].abs().max())
        cambia = not peor_exc < UMBRAL_EXCEDENTE_PCT
        print(f"EXCEDENTE: {'CAMBIA' if cambia else 'SE CONSERVA'}"
              f" (peor cambio {peor_exc:.3f} %; umbral "
              f"{UMBRAL_EXCEDENTE_PCT} %)")
    else:
        # De cero a algo es un cambio; de cero a cero, no.
        cambia = bool((tabla["excedente"].abs() > 1e-12).any())
        print(f"EXCEDENTE: {'CAMBIA' if cambia else 'SE CONSERVA'}"
              f" (excedente de produccion cero)")
    # I-8 c: el lanzador detiene la cadena con un codigo distinto de cero.
    if depende or cambia:
        print("SALIDA: 2 (salto un criterio fijado antes de medir)")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
