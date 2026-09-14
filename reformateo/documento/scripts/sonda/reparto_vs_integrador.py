"""
Depende el reparto de la via acoplada del integrador (tarea 15, D16, H-79).

H-37 midio que el reparto de la via ALTERNADA depende del paso fijo de su
bloque comprador. La corrida oficial usa la ACOPLADA, que integra con paso
adaptativo (LSODA, tolerancias 1e-6, H-51) y nunca pasa por ese bloque. Esta
sonda mide la pregunta equivalente: si el reparto se mueve al apretar diez
veces la tolerancia relativa o al doblar el horizonte, que con 0,05 deja sin
llegar al estacionario a un tercio de las horas.

La variante de tolerancia solo aprieta la RELATIVA, a 1e-7; la absoluta se
deja en 1e-6, la de produccion (D25). Apretar tambien la absoluta reproduce
H-51: esa variante estricta no termino en 660 (s) sobre la hora 4184 a
factor de generacion 7, mientras que produccion tarda 140 (s) y esta
variante, con solo la relativa, 133 (s). Es la regla principal de CLAUDE.md:
la tolerancia absoluta del acoplado nunca se baja de 1e-6; para medir
sensibilidad a la tolerancia se aprieta solo la relativa.

Cada variante tiene un plazo (`--plazo-variante`, 15 min por omision). La
resuelve un trabajador persistente que carga los datos una sola vez; si una
variante lo pasa, se mata al trabajador y se abre otro, porque uno atascado
no atiende la cancelacion (C-156), y la variante vencida cuenta como no
resuelta, igual que una que falla.

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

Subproyecto 2 (D25): `--veredicto-json RUTA` escribe ademas el veredicto de
la palanca (que variante supera algun criterio) en un JSON, para que la
accion `matriz` del lanzador decida sin volver a correr esta sonda. La decide
`decide_veredicto`, funcion pura que solo lee la tabla ya comparada; se
prueba con tablas sinteticas en tests/test_veredicto_sonda.py.

Uso:
    python reparto_vs_integrador.py --horas 2
    python reparto_vs_integrador.py --horas 20 --salida sonda_t15.csv
    python reparto_vs_integrador.py --horas 1 --factor-generacion 7
    python reparto_vs_integrador.py --horas 20 --factor-generacion 1 \
        --veredicto-json SALIDAS_SERVIDOR/sonda79/veredicto_E0.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paso_a_paso import carga, resuelve  # noqa: E402

VARIANTES = {
    "produccion": None,
    "relativa_x0,1": {"rtol": 1e-7, "atol": 1e-6},
    "horizonte_x2": {"t_span": (0.0, 0.10)},
}
UMBRAL_PUNTOS = 1.0
UMBRAL_EXCEDENTE_PCT = 0.1

# Subproyecto 2 (accion `sonda79` del lanzador): que variante activa que
# palanca del acoplado si supera alguno de los dos criterios. D35 (tolerancia
# relativa a 1e-7) y D26 (el acoplado para por estacionario en vez de
# horizonte fijo).
VARIANTE_A_PALANCA = {
    "relativa_x0,1": "tolerancia",
    "horizonte_x2": "horizonte",
}


def decide_veredicto(tabla: pd.DataFrame, umbral_puntos: float = UMBRAL_PUNTOS,
                     umbral_excedente_pct: float = UMBRAL_EXCEDENTE_PCT) -> dict:
    """El veredicto de la palanca, a partir de la tabla ya comparada contra
    produccion (subproyecto 2, D25).

    FUNCION PURA: solo lee las columnas de una tabla ya armada por `main`
    (`delta_puntos`, `excedente_delta_%` y, para el caso raro del excedente
    de produccion en cero, `excedente`); no resuelve ningun mercado ni toca
    disco. Se prueba con tablas sinteticas en tests/test_veredicto_sonda.py.

    Para cada variante candidata (tolerancia, horizonte) mira si supera
    alguno de los dos criterios fijados antes de medir (1 punto de reparto
    del vendedor, 0,1 % del excedente) y devuelve:

        {"reparto_depende": bool, "excedente_cambia": bool,
         "palanca": ["tolerancia"] | ["horizonte"]
                     | ["tolerancia", "horizonte"] | []}

    Una variante ausente de la tabla (por ejemplo una prueba sintetica con
    una sola fila) no aporta palanca: no es un error.
    """
    reparto_depende = False
    excedente_cambia = False
    palanca: list[str] = []
    for variante, campo in VARIANTE_A_PALANCA.items():
        if variante not in tabla.index:
            continue
        fila = tabla.loc[variante]
        supera_puntos = abs(float(fila.get("delta_puntos", 0.0))) >= umbral_puntos
        delta_exc = fila.get("excedente_delta_%", np.nan)
        if pd.notna(delta_exc):
            supera_excedente = abs(float(delta_exc)) >= umbral_excedente_pct
        else:
            # Excedente de produccion ~0 (ver la guarda de cero en `main`): el
            # cambio relativo no existe, pero de cero a algo SI es un cambio.
            supera_excedente = abs(float(fila.get("excedente", 0.0))) > 1e-12
        if supera_puntos:
            reparto_depende = True
        if supera_excedente:
            excedente_cambia = True
        if supera_puntos or supera_excedente:
            palanca.append(campo)
    return {"reparto_depende": reparto_depende,
            "excedente_cambia": excedente_cambia, "palanca": palanca}


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


_DAT = None


def _inicia(factor):
    """En el trabajador: carga los datos una sola vez."""
    global _DAT
    from paso_a_paso import carga
    _DAT = carga("m1", factor_generacion=factor)


def _una_variante(k, sol):
    """En el trabajador: resuelve UNA hora con UNA variante y mide."""
    from paso_a_paso import resuelve
    t0 = time.perf_counter()
    r = resuelve(_DAT, int(k), solucionador=sol)
    seg = time.perf_counter() - t0
    if r is None:
        return dict(resuelta=False, segundos=seg)
    m = mide(_DAT, r)
    m.update(resuelta=True, segundos=seg)
    return m


def _trabajador(factor):
    return ProcessPoolExecutor(max_workers=1, initializer=_inicia,
                               initargs=(factor,))


def _con_plazo(ex, factor, k, sol, plazo_s):
    """(medidas, trabajador). Si la variante vence, mata al trabajador y abre
    otro: un trabajador atascado no atiende la cancelacion (C-156)."""
    f = ex.submit(_una_variante, k, sol)
    try:
        return f.result(timeout=plazo_s), ex
    except FuturesTimeout:
        for p in list(getattr(ex, "_processes", {}).values()):
            if p.is_alive():
                p.terminate()
        ex.shutdown(wait=False, cancel_futures=True)
        return (dict(resuelta=False, segundos=plazo_s,
                     motivo=f"vencio el plazo por variante de "
                            f"{plazo_s / 60:.0f} min"),
                _trabajador(factor))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--horas", type=int, default=2)
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--salida", default=None)
    ap.add_argument("--factor-generacion", default="1", metavar="F",
                    help="I-8 b: escala la generacion de las cinco, como el "
                         "orquestador (acepta 1/7)")
    ap.add_argument("--plazo-variante", dest="plazo_variante", type=float,
                    default=15.0, metavar="MIN",
                    help="D25: plazo por variante, en minutos, contado "
                         "desde que arranca en el trabajador persistente. "
                         "La variante que lo pasa cuenta como no resuelta, "
                         "con su motivo, y se reemplaza el trabajador "
                         "(C-156).")
    ap.add_argument("--veredicto-json", dest="veredicto_json", default=None,
                    metavar="RUTA",
                    help="subproyecto 2 (D25): ademas de imprimir la tabla, "
                         "escribe el veredicto de la palanca (JSON con "
                         "reparto_depende, excedente_cambia y palanca) en "
                         "esta ruta. No cambia el codigo de salida: la "
                         "accion `sonda79` del lanzador sigue sin detenerse "
                         "por el codigo 2.")
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

    plazo_s = a.plazo_variante * 60.0
    ex = _trabajador(factor)

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
            fila, ex = _con_plazo(ex, factor, int(k), sol, plazo_s)
            fila["hora"] = int(k)
            fila["variante"] = nombre
            # I-8 a: una integracion fallida no es una hora resuelta.
            # Produccion la marca sin mercado (core/ems_p2p.py, `success`
            # falso), de modo que aqui no cuenta como completa ni entra al
            # agregado. Una variante vencida (D25) tampoco.
            fila["valida"] = bool(fila["resuelta"] and fila.get("exito", False))
            filas_k.append(fila)
            motivo = fila.get("motivo")
            marca = (f"  {motivo}" if motivo else
                     "" if fila["valida"] or not fila["resuelta"]
                     else "  FALLO del integrador")
            print(f"  hora {int(k):5d}  {nombre:16s} {fila['segundos']:7.1f}"
                  f" s{marca}")
            if not fila["valida"] and nombre == "produccion":
                break              # sin mercado: no se gastan las otras dos
        filas.extend(filas_k)
        if (len(filas_k) == len(VARIANTES)
                and all(f["valida"] for f in filas_k)):
            completas += 1
    ex.shutdown(wait=True, cancel_futures=True)
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

    # Subproyecto 2 (D25): el veredicto de la palanca, ademas de la tabla de
    # arriba. No cambia el codigo de salida.
    if a.veredicto_json:
        veredicto = decide_veredicto(tabla)
        ruta = Path(a.veredicto_json)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(veredicto, ensure_ascii=False, indent=2)
                        + "\n", encoding="utf-8")
        print(f"\n  veredicto escrito en {ruta}")

    # I-8 c: el lanzador detiene la cadena con un codigo distinto de cero.
    if depende or cambia:
        print("SALIDA: 2 (salto un criterio fijado antes de medir)")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
