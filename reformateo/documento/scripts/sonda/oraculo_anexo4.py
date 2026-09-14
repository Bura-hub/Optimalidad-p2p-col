"""
El oraculo del Anexo 4 (subproyecto 2, paso 1; decisiones D19, D32 y D33).

Antes de gastar corridas en el servidor se comprueba en local que la
autogeneracion individual (C1) liquida el credito de energia como lo dice
la norma. Este guion recalcula la liquidacion con ARITMETICA PROPIA, escrita
directamente desde el texto de la norma, sin llamar a ninguna funcion del
motor para su propia cuenta (en particular, no importa `reparto_anexo4`,
`deduccion_art25` ni `tramo_permuta` de `core/opciones_externas.py`, ni nada
de `scenarios/`), y la compara con la del motor (`run_c1_creg174`) para cada
institucion y cada mes del horizonte. El motor solo se llama para obtener lo
que se compara. No resuelve el mercado entre pares: es liviano y corre en
local.

La norma que implementa `liquida_mes`: Anexo 4 de la Resolucion CREG 101 072
de 2025, que reglamenta el articulo 25 de la Resolucion CREG 174 durante la
transicion, con el paragrafo del articulo 25 en la redaccion de la 101 087
de 2025 (el exceso se valora a la bolsa y no a MCm). Para una frontera y un
mes de facturacion, con la generacion y la demanda medidas y no negativas:

  exportacion  exp_h = max(G_h - D_h, 0)
  importacion  imp_h = max(D_h - G_h, 0)
  autoconsumo  auto_h = min(G_h, D_h)

  Imp = importacion TOTAL del mes (suma de imp_h)

  hx = la PRIMERA hora del mes en que la exportacion acumulada desde la
       primera hora del mes IGUALA O SOBREPASA Imp; en esa hora se reconoce
       como exceso lo que la acumulada supera a Imp (puede ser cero en el
       empate exacto), y desde la hora siguiente toda la exportacion es
       exceso. Si nunca se alcanza, no hay hx y todo es credito.

  credito del mes = exportacion total menos exceso total
                   (es decir, min(exportacion total, Imp))

  dinero, frente a no tener generacion:
      autoconsumo x CU + credito x (CU - deduccion) + suma_h(exceso_h x bolsa_h)

  con CU y la deduccion como PROMEDIO DEL MES de la tarifa de cada
  institucion (la tarifa es mensual), y la deduccion del articulo 25 por
  capacidad: numeral 1 (hasta 100 kW) el componente de comercializar Cv;
  numeral 2 (de 100 kW a 1 MW) Cv + T + D + PR + R.

MATIZ QUE HAY QUE RESPETAR (declarado en el brief): el motor toma como hora
de corte la primera hora con exceso POSITIVO; la norma dice "iguala o
sobrepasa". En el empate exacto las dos dan el mismo dinero (el exceso de
esa hora vale cero), y en el caso limite en que el empate cae en la ULTIMA
hora del mes el motor puede no encontrar ninguna hora de corte (nunca hay
exceso positivo) mientras el oraculo si la marca, sin que el dinero ni la
energia difieran. Este guion informa las dos horas de corte y SOLO cuenta
como discrepancia una diferencia de dinero o de energia, no una hora de
corte distinta con el mismo dinero.

Uso:
    python oraculo_anexo4.py --factor-generacion 1
    python oraculo_anexo4.py --factor-generacion 7
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(AQUI))
from paso_a_paso import carga  # noqa: E402

# Umbrales de discrepancia (brief, seccion "Que construir").
UMBRAL_DINERO_COP = 1.0
UMBRAL_ENERGIA_KWH = 1e-6

# Lectura PROPIA de la capacidad y del umbral del articulo 25 (brief:
# "el oraculo calcula la deduccion con su propia lectura de la capacidad
# ... y el umbral de 100 kW, sin llamar a deduccion_art25"). El valor de la
# placa (17,55 kWp por planta) es el mismo hecho documentado en
# data/capacidad_instalada.py (Informe 4 del MTE, p. 4; H-67), pero se repite
# aqui como constante propia para no depender de ese modulo.
KWP_POR_PLANTA = 17.55
LIMITE_NUMERAL_1_KW = 100.0


def liquida_mes(G_h: np.ndarray, D_h: np.ndarray, cu_h: np.ndarray,
                ded_h: np.ndarray, bolsa_h: np.ndarray) -> dict:
    """Liquida UNA frontera en UN mes con la aritmetica del Anexo 4.

    Todos los parametros son vectores horarios de la MISMA longitud (las
    horas del mes): `G_h`, `D_h` generacion y demanda medidas (kWh, se
    tratan como no negativas); `cu_h` costo unitario CU del agente en cada
    hora (COP/kWh); `ded_h` la deduccion del articulo 25 en cada hora
    (COP/kWh); `bolsa_h` el precio de bolsa de cada hora (COP/kWh).

    Devuelve un dict con `auto, credito, exceso` (kWh, energias del mes),
    `hx` (indice de la hora de corte DENTRO del mes segun la norma, o None
    si nunca se alcanza) y `dinero_auto, dinero_credito, dinero_exceso,
    dinero_total` (COP).
    """
    T = len(G_h)
    auto_h = np.zeros(T)
    exp_h = np.zeros(T)
    imp_h = np.zeros(T)
    for h in range(T):
        g = max(float(G_h[h]), 0.0)
        d = max(float(D_h[h]), 0.0)
        exp_h[h] = max(g - d, 0.0)
        imp_h[h] = max(d - g, 0.0)
        auto_h[h] = min(g, d)

    Imp = 0.0
    for h in range(T):
        Imp += imp_h[h]

    exceso_h = np.zeros(T)
    hx: Optional[int] = None
    acumulado = 0.0
    for h in range(T):
        acumulado += exp_h[h]
        if hx is None:
            if acumulado >= Imp:
                # La hora del corte: lo que la acumulada supera a Imp (cero
                # en el empate exacto).
                exceso_h[h] = acumulado - Imp
                hx = h
            # si todavia no se alcanza, toda la hora es credito (exceso 0)
        else:
            # desde la hora siguiente al corte, toda la exportacion es
            # exceso
            exceso_h[h] = exp_h[h]

    credito_h = exp_h - exceso_h

    auto = float(np.sum(auto_h))
    credito = float(np.sum(credito_h))
    exceso = float(np.sum(exceso_h))

    cu_prom = float(np.mean(cu_h))
    ded_prom = float(np.mean(ded_h))

    dinero_auto = auto * cu_prom
    dinero_credito = credito * (cu_prom - ded_prom)
    dinero_exceso = float(np.dot(exceso_h, np.asarray(bolsa_h, dtype=float)))
    dinero_total = dinero_auto + dinero_credito + dinero_exceso

    return dict(auto=auto, credito=credito, exceso=exceso, hx=hx,
                dinero_auto=dinero_auto, dinero_credito=dinero_credito,
                dinero_exceso=dinero_exceso, dinero_total=dinero_total)


def compara(factor: float) -> dict:
    """Carga m1 al factor dado, liquida con el oraculo y con el motor, y
    devuelve todo lo que hace falta para imprimir el resumen, escribir el
    csv, o comprobarlo desde una prueba.
    """
    from data.capacidad_instalada import capacidad_instalada
    from scenarios.scenario_c1_creg174 import run_c1_creg174

    capacidad_kw_oraculo = KWP_POR_PLANTA * float(factor)
    numeral = 1 if capacidad_kw_oraculo <= LIMITE_NUMERAL_1_KW else 2

    dat = carga("m1", factor_generacion=factor)
    D, G, idx = dat["D"], dat["G"], dat["idx"]
    techo, cvm, peaje, bolsa = dat["techo"], dat["cvm"], dat["peaje"], dat["bolsa"]
    nombres = dat["nombres"]
    N, T = D.shape

    # Deduccion PROPIA del oraculo (numeral 1: solo Cv; numeral 2: Cv+T+D+PR+R).
    ded = cvm.copy() if numeral == 1 else cvm + peaje

    # Etiqueta de mes AAAAMM como entero: `run_c1_creg174` hace int(m) al
    # agrupar, de modo que la etiqueta tiene que admitirlo (a diferencia de
    # "AAAA-MM", que usan otras sondas solo para agrupar con numpy).
    etiquetas = (pd.Series(pd.DatetimeIndex(idx)).dt.strftime("%Y%m")
                 .astype(int).to_numpy())
    meses = sorted(set(int(m) for m in etiquetas))

    # El motor, con los MISMOS D y G, para lo que se compara (brief).
    factores = np.full(N, float(factor))
    capacidad_kw_motor = capacidad_instalada(nombres, factores)
    resultado_motor = run_c1_creg174(
        D, G, techo, bolsa, list(range(N)), month_labels=etiquetas,
        component_c=cvm, capacidad_kw=capacidad_kw_motor, tolls=peaje)
    neto_horario = resultado_motor["neto_horario"]

    filas = []
    for n in range(N):
        hx_hist = resultado_motor[n]["hx_history"]
        for m_idx, mes in enumerate(meses):
            horas = np.flatnonzero(etiquetas == mes)
            r = liquida_mes(G[n, horas], D[n, horas], techo[n, horas],
                            ded[n, horas], bolsa[horas])
            dinero_motor = float(np.sum(neto_horario[n, horas]))
            hx_motor = hx_hist[m_idx]
            dif_dinero = r["dinero_total"] - dinero_motor
            filas.append(dict(
                institucion=nombres[n], mes=int(mes), horas=int(len(horas)),
                auto_kwh=r["auto"], credito_kwh=r["credito"],
                exceso_kwh=r["exceso"],
                hx_oraculo=r["hx"], hx_motor=hx_motor,
                dinero_auto=r["dinero_auto"],
                dinero_credito=r["dinero_credito"],
                dinero_exceso=r["dinero_exceso"],
                dinero_oraculo=r["dinero_total"],
                dinero_motor=dinero_motor, dif_dinero=dif_dinero,
            ))

    df = pd.DataFrame(filas)

    # Energia agregada por institucion (suma de sus meses) contra los
    # totales que ya trae el motor por agente (E_auto, E_permuted_t1,
    # E_tipo2): es la unica granularidad de energia que el motor expone.
    dif_energia_max = 0.0
    energia_por_institucion = []
    for n in range(N):
        sub = df[df.institucion == nombres[n]]
        auto_o = float(sub.auto_kwh.sum())
        cred_o = float(sub.credito_kwh.sum())
        exc_o = float(sub.exceso_kwh.sum())
        auto_m = float(resultado_motor[n]["E_auto"])
        cred_m = float(resultado_motor[n]["E_permuted_t1"])
        exc_m = float(resultado_motor[n]["E_tipo2"])
        difs = (abs(auto_o - auto_m), abs(cred_o - cred_m),
                abs(exc_o - exc_m))
        dif_energia_max = max(dif_energia_max, max(difs))
        energia_por_institucion.append(dict(
            institucion=nombres[n],
            auto_oraculo=auto_o, auto_motor=auto_m,
            credito_oraculo=cred_o, credito_motor=cred_m,
            exceso_oraculo=exc_o, exceso_motor=exc_m,
            dif_max=max(difs)))

    dif_dinero_max = float(df.dif_dinero.abs().max()) if len(df) else 0.0
    con_corte_oraculo = int(df.hx_oraculo.notna().sum())
    con_corte_motor = int(df.hx_motor.notna().sum())

    def _hx_iguales(a, b) -> bool:
        an, bn = a is None or (isinstance(a, float) and np.isnan(a)), \
                 b is None or (isinstance(b, float) and np.isnan(b))
        if an and bn:
            return True
        if an != bn:
            return False
        return int(a) == int(b)

    hx_distinta = int(sum(
        0 if _hx_iguales(a, b) else 1
        for a, b in zip(df.hx_oraculo, df.hx_motor))) if len(df) else 0

    return dict(df=df, resultado_motor=resultado_motor, nombres=nombres,
                meses=meses, factor=float(factor), numeral=numeral,
                capacidad_kw=capacidad_kw_oraculo,
                dif_dinero_max=dif_dinero_max,
                dif_energia_max=dif_energia_max,
                con_corte_oraculo=con_corte_oraculo,
                con_corte_motor=con_corte_motor,
                hx_distinta=hx_distinta,
                energia_por_institucion=energia_por_institucion)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--factor-generacion", default="1", metavar="F",
                    help="escala la generacion de las cinco, como el "
                         "orquestador (acepta 1/7); decide el numeral del "
                         "art. 25 por la capacidad resultante")
    a = ap.parse_args()

    from data.escalado import lee_factor
    factor = lee_factor(a.factor_generacion)

    print(f"oraculo del Anexo 4 -- factor de generacion x{factor:g}")
    r = compara(factor)
    print(f"  capacidad por planta: {r['capacidad_kw']:.2f} kW -> "
          f"numeral {r['numeral']} del art. 25")
    print(f"  instituciones: {len(r['nombres'])} -- meses: {len(r['meses'])} "
          f"-- filas: {len(r['df'])}")

    salida_dir = RAIZ / "outputs" / "oraculo_anexo4"
    salida_dir.mkdir(parents=True, exist_ok=True)
    csv_path = salida_dir / f"oraculo_anexo4_x{factor:g}.csv"
    r["df"].to_csv(csv_path, index=False, encoding="utf-8")

    print("\n  energia agregada por institucion (oraculo vs motor, kWh):")
    for e in r["energia_por_institucion"]:
        print(f"    {e['institucion']:10s} auto {e['auto_oraculo']:10.3f} / "
              f"{e['auto_motor']:10.3f}   credito {e['credito_oraculo']:10.3f}"
              f" / {e['credito_motor']:10.3f}   exceso "
              f"{e['exceso_oraculo']:10.3f} / {e['exceso_motor']:10.3f}   "
              f"dif max {e['dif_max']:.9f}")

    print(f"\n  meses con hora de corte (oraculo): {r['con_corte_oraculo']} "
          f"de {len(r['df'])}")
    print(f"  meses con hora de corte (motor):   {r['con_corte_motor']} "
          f"de {len(r['df'])}")
    if r["hx_distinta"]:
        print(f"  AVISO: {r['hx_distinta']} mes(es) con hora de corte "
              f"distinta entre oraculo y motor (se informa, no cuenta como "
              f"discrepancia si el dinero y la energia coinciden)")

    print(f"\n  diferencia maxima de dinero:  {r['dif_dinero_max']:.6f} (COP)"
          f"  (umbral {UMBRAL_DINERO_COP:g})")
    print(f"  diferencia maxima de energia: {r['dif_energia_max']:.9f} (kWh)"
          f"  (umbral {UMBRAL_ENERGIA_KWH:g})")
    print(f"  csv: {csv_path}")

    discrepa = (r["dif_dinero_max"] > UMBRAL_DINERO_COP
                or r["dif_energia_max"] > UMBRAL_ENERGIA_KWH)
    if discrepa:
        print("\nVEREDICTO: DISCREPANCIA -- no se toca el motor; se informa "
              "para que el controlador decida")
        df = r["df"]
        peores = df[df.dif_dinero.abs() > UMBRAL_DINERO_COP]
        for _, fila in peores.iterrows():
            print(f"  DINERO  {fila.institucion} {fila.mes}: "
                  f"oraculo={fila.dinero_oraculo:.2f} "
                  f"motor={fila.dinero_motor:.2f} "
                  f"dif={fila.dif_dinero:.2f} (COP)")
        for e in r["energia_por_institucion"]:
            if e["dif_max"] > UMBRAL_ENERGIA_KWH:
                print(f"  ENERGIA {e['institucion']}: "
                      f"auto {e['auto_oraculo']:.6f}/{e['auto_motor']:.6f} "
                      f"credito {e['credito_oraculo']:.6f}/"
                      f"{e['credito_motor']:.6f} exceso "
                      f"{e['exceso_oraculo']:.6f}/{e['exceso_motor']:.6f} "
                      f"(kWh)")
        return 1

    print("\nVEREDICTO: COINCIDEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
