"""PASO 3 — Indices de Sobol reproducibles, con procedencia verificada.

Tres cosas que el modulo anterior no hacia:

  1. VERIFICA LA PROCEDENCIA antes de analizar. Regenera la matriz de muestreo
     con la semilla declarada y comprueba que las columnas de parametros del
     CSV coinciden. Sin esto, un fichero que mezcle dos corridas distintas
     produce indices sin sentido y ninguna alarma: el estimador de Saltelli
     depende del apareamiento A/B/AB, y basta un indice duplicado o una fila de
     otro diseno para romperlo en silencio.
  2. ADJUDICA CONTRA EL INTERVALO, no contra la estimacion puntual. La cota que
     el articulo publica —«ningun parametro interno supera el 0,9 %»— tiene un
     margen de centesimas frente a intervalos de casi un punto: decidirla por
     el valor puntual es fingir una precision que el diseno no da.
  3. LEE LA REFERENCIA SINTETICA DEL DISCO en vez de llevarla transcrita, y
     compara por SOLAPAMIENTO DE INTERVALOS, no por una diferencia fija.

Uso
---
    bash gsa_real/run_servidor.sh analizar M1 full 128

El 5o hueco del lanzador es SIEMPRE el timeout y solo lo usan correr/reanudar.
La semilla va por entorno: SEMILLA=7 bash gsa_real/run_servidor.sh analizar ...
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import (EXCLUIDOS, FACTOR_SALTELLI, NOMBRES, PROBLEMA, RAIZ,  # noqa: E402
                   SALIDAS, SEGUNDO_ORDEN, asegurar_salida)

# UN umbral, no dos, y es el 10 % que declara la tesis (§2.7).
#
# Una version anterior separaba un segundo umbral del 0,5 % para adjudicar la
# cota del 0,9 %, con el argumento de que ahi el sesgo debe ser mucho menor.
# Eran dos errores encadenados:
#
#   1. Con n_base=128 hay 128 bloques, de modo que UN SOLO fallo da 0,78 % y
#      deja la cota no adjudicable. La rama que produce el numero publicado
#      resultaba inalcanzable salvo con cero fallos en 896 evaluaciones.
#   2. El argumento del sesgo no sostiene ese rigor. El descarte de bloques es
#      insesgado si el fallo es independiente de los parametros; cuando depende
#      —que es el caso: son timeouts en zonas rigidas—, el sesgo relativo medido
#      descartando el 16 % de los bloques fue de orden 10 % sobre el indice mas
#      pequeno. Sobre un ST del orden de 0,004 eso son 0,04 puntos
#      porcentuales, dos ordenes por debajo del 0,9 % que se adjudica.
#
# Lo que de verdad protege la cota no es un umbral de fallos mas duro, sino
# adjudicar contra el EXTREMO SUPERIOR del intervalo —que es lo que se hace— y
# publicar la fraccion descartada junto al veredicto, para que quien lea decida.
UMBRAL_DOMINANCIA = 0.10
UMBRAL_COTA = 0.10

# Suelo de resolucion del estimador. Una alarma sobre un parametro cuyo indice
# TOTAL esta por debajo de esto no puede indicar falta de convergencia: no hay
# efecto que converja. Sigue apareciendo en el informe —no se oculta— pero se
# marca como INMATERIAL y no bloquea el veredicto.
#
# El umbral no se elige aqui: es el mismo 0,05 que la seccion de comparacion ya
# usaba para declarar un par «irresoluble», y estaba en el modulo antes de la
# campana. Que se aplique tambien a las alarmas se identifico DESPUES de ver la
# corrida M3, donde `ganancia/b_mean` y `sc/PGB` la disparaban por margenes de
# 1,1e-5 y 2,7e-5 sobre parametros con ST = 0,0000 — mientras M1 la satisfacia
# por +8e-5, un margen del mismo orden. Es decir: el criterio decidia la validez
# de 896 evaluaciones en el quinto decimal, por azar de muestreo.
#
# APLICAR A TODAS LAS COBERTURAS Y DECLARARLO. No altera ningun indice: solo
# cambia si una alarma bloquea el veredicto.
SUELO_RESOLUCION = 0.05

# 100 es el defecto de SALib, pero el semiancho es Z*std de esas replicas y el
# propio std tiene un error del orden del 7 %. Como todo el informe adjudica
# CONTRA LOS EXTREMOS del intervalo, ese ruido entra directo en los veredictos.
# El remuestreo son milisegundos frente a las horas de la corrida.
N_REMUESTRAS = 1000
SEMILLA_ANALISIS = 42
REF_SINTETICA = (RAIZ / "validacion_convergencia" / "salidas" /
                 "sensibilidad" / "sobol_intervalos.csv")

# Parametros que NO son comparables con el GSA sintetico, con su motivo.
NO_COMPARABLES = {
    "PGS": "soporte ampliado a [600,1000] para contener la tarifa real "
           "(escalar del juego 906,27; matriz de liquidacion 773,5-980,4)",
    "PGB": "canal distinto: en el sintetico pi_bolsa = PGB, aqui es la serie real",
}


def leer_referencia():
    """Los indices del GSA sintetico, leidos del CSV del proyecto.

    El CSV trae DOS anchos por indice: `ST_conf`, recalculado por
    `validacion_convergencia/scripts/sobol_intervalos.py` con semilla de
    remuestreo fija, y `ST_conf_guardado`, el historico de la campana original,
    cuya semilla no se fijo. Divergen hasta un 23 % por puro ruido de
    remuestreo, y como el veredicto de abajo es un test de solapamiento, la
    eleccion puede voltearlo. Se toma **el reproducible**; `_guardado` se ignora
    a proposito.

    Dos asimetrias que el informe debe declarar, porque no se pueden corregir
    desde aqui: la referencia usa 100 remuestras (esta corrida usa
    N_REMUESTRAS) y trata sus fallos por IMPUTACION POR LA MEDIA, que es
    justamente lo que este modulo rechaza. Sus ST estan, por tanto, inflados.
    """
    if not REF_SINTETICA.exists():
        return {}
    # Una celda vacia o corrupta reventaba con ValueError DESPUES de haber
    # escrito indices_*.csv y antes del informe, dejando artefactos
    # desparejados. La referencia es un extra: si no se puede leer, se omite la
    # comparacion y el resto del analisis sigue siendo valido.
    ref = {}
    try:
        with open(REF_SINTETICA, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                ref[(r["salida"], r["parametro"])] = (
                    float(r["S1"]), float(r["S1_conf"]),
                    float(r["ST"]), float(r["ST_conf"]))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        print(f"  AVISO: la referencia sintetica no se pudo leer "
              f"({type(exc).__name__}: {exc}). Se omite la comparacion.")
        return {}
    return ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestras", required=True)
    args = ap.parse_args()

    sal = asegurar_salida()
    ruta = sal / args.muestras
    if not ruta.exists():
        print(f"no existe {ruta}")
        return 1
    tag = ruta.stem.replace("muestras_", "")
    meta_p = ruta.with_suffix(".meta.json")

    # ── 1. procedencia ─────────────────────────────────────────────────────
    print("=" * 70)
    print(f"ANALISIS  {ruta.name}")
    print("=" * 70)
    if not meta_p.exists():
        print("  ABORTA: falta el .meta.json de la corrida. Sin el no se puede")
        print("  verificar que el fichero corresponda a un unico diseno.")
        return 1
    try:
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  ABORTA: el .meta.json no se puede leer ({type(exc).__name__}: "
              f"{exc}).")
        return 1
    # Validacion de tipos antes de usarlos. Sin esto, un `n_base` guardado como
    # cadena daba `M_esp = "32"*7` y el mensaje de error decia que el diseno
    # pedia 32323232323232 filas; y un campo ausente reventaba con traza.
    if not isinstance(meta, dict):
        print("  ABORTA: el .meta.json no contiene un objeto.")
        return 1
    for campo, tipo in (("n_base", int), ("semilla", int)):
        if campo not in meta:
            print(f"  ABORTA: al .meta.json le falta el campo '{campo}'.")
            return 1
        if not isinstance(meta[campo], tipo) or isinstance(meta[campo], bool):
            print(f"  ABORTA: '{campo}' es {type(meta[campo]).__name__} "
                  f"({meta[campo]!r}) y debe ser {tipo.__name__}.")
            return 1
    n_base, semilla = meta["n_base"], meta["semilla"]
    if n_base < 1:
        print(f"  ABORTA: n_base={n_base} no tiene sentido.")
        return 1
    M_esp = n_base * FACTOR_SALTELLI
    if meta.get("segundo_orden") != SEGUNDO_ORDEN:
        print(f"  ABORTA: la corrida uso segundo_orden={meta.get('segundo_orden')} "
              f"y el analisis usa {SEGUNDO_ORDEN}. Los indices saldrian mal.")
        return 1
    if meta.get("parametros") != NOMBRES:
        print(f"  ABORTA: la corrida barrio {meta.get('parametros')} "
              f"y este analisis espera {NOMBRES}.")
        return 1

    filas = []
    with open(ruta, newline="", encoding="utf-8") as f:
        lector = csv.DictReader(f)
        cabecera = set(lector.fieldnames or ())
        # Comprobar las columnas ANTES de anunciar «procedencia OK»: faltar una
        # salida daba un KeyError crudo despues de haber dicho que todo cuadraba.
        faltan = ({"idx"} | set(NOMBRES)) - cabecera
        if faltan:
            print(f"  ABORTA: al CSV le faltan columnas: {sorted(faltan)}")
            return 1
        # CAL-43: las SALIDAS se analizan SEGUN LO QUE EL CSV TRAIGA. La cuarta
        # (`brecha_c1`) se anadio despues de la corrida de julio; abortar por su
        # ausencia dejaria inanalizables los CSV historicos, que siguen siendo
        # validos para las tres primeras. Lo que NO se admite es analizar cero
        # salidas ni callarse cual falta.
        salidas_act = [s for s in SALIDAS if s in cabecera]
        if not salidas_act:
            print(f"  ABORTA: el CSV no trae ninguna de las salidas {SALIDAS}.")
            return 1
        if len(salidas_act) != len(SALIDAS):
            ausentes = [s for s in SALIDAS if s not in cabecera]
            print(f"  AVISO: el CSV no trae {ausentes} (corrida anterior a "
                  f"CAL-43). Se analizan solo {salidas_act}.")
        for r in lector:
            if r.get("idx"):
                filas.append(r)
    try:
        filas.sort(key=lambda r: int(r["idx"]))
    except (TypeError, ValueError) as exc:
        print(f"  ABORTA: hay un 'idx' que no es entero ({exc}).")
        return 1
    idx = np.array([int(r["idx"]) for r in filas])

    if len(idx) != M_esp:
        print(f"  ABORTA: hay {len(idx)} filas y el diseno pide {M_esp}. "
              f"Reanuda la corrida.")
        return 1
    if len(set(idx.tolist())) != len(idx):
        print("  ABORTA: hay indices DUPLICADOS. El fichero mezcla corridas.")
        return 1
    if not np.array_equal(idx, np.arange(M_esp)):
        print("  ABORTA: los indices no son 0..M-1 sin huecos.")
        return 1

    from SALib.sample import sobol as sobol_sample
    X = sobol_sample.sample(PROBLEMA, n_base, calc_second_order=SEGUNDO_ORDEN,
                            seed=semilla)
    Xcsv = np.array([[float(r[p]) for p in NOMBRES] for r in filas])
    if not np.allclose(X, Xcsv, rtol=1e-6, atol=1e-9):
        d = np.abs(X - Xcsv).max()
        print(f"  ABORTA: las columnas de parametros NO coinciden con la matriz")
        print(f"  regenerada con semilla {semilla} (diferencia maxima {d:.3g}).")
        print("  El fichero no corresponde a este diseno.")
        return 1
    print(f"  procedencia OK: {M_esp} filas, indices completos, matriz X "
          f"verificada contra la semilla {semilla}")

    # La matriz X depende SOLO de (soportes, n_base, semilla): es identica para
    # M1 y M3, para `full` y para un mes suelto, y para cualquier MTE_ROOT.
    # Verificarla no dice nada sobre QUE DATOS se corrieron. Eso solo consta en
    # el .meta.json, asi que se lee, se contrasta con el nombre del fichero y se
    # arrastra al informe; si no, la unica constancia seria un `tag` que nadie
    # ha verificado contra nada.
    cobertura = meta.get("cobertura", "?")
    horizonte = meta.get("horizonte", "?")
    h_datos = meta.get("huella_datos", "(sin registrar)")
    # `tag` declarado si existe; si no, reconstruido (ficheros anteriores).
    esperado_tag = meta.get("tag") or \
        f"{cobertura}_{str(horizonte).replace(':', '-')}_n{n_base}_s{semilla}"
    es_verificacion = bool(meta.get("verificar"))
    if es_verificacion:
        # NO se rechaza: si el unico fichero analizable tuviera que costar horas
        # de modelo, este tramo no se podria probar nunca — y asi es como se
        # cuelan los fallos de fontaneria. Se analiza, y todo artefacto queda
        # marcado para que no pueda confundirse con una corrida real.
        print("\n  *** FICHERO DE VERIFICACION ***")
        print("  Los valores NO provienen del modelo: se genero con --verificar")
        print("  para ejercitar la fontaneria. Los indices de abajo NO SIGNIFICAN")
        print("  NADA fisicamente. El codigo de salida sera != 0.\n")
    if tag != esperado_tag:
        print(f"  ABORTA: el nombre del fichero dice '{tag}' y el .meta.json "
              f"describe '{esperado_tag}'.")
        print("  Alguien renombro la corrida: no se puede saber sobre que datos es.")
        return 1
    print(f"  datos: cobertura {cobertura}, horizonte {horizonte}, "
          f"N={meta.get('N','?')} T={meta.get('T','?')}h, huella {h_datos}")
    if meta.get("soportes") != PROBLEMA["bounds"]:
        print(f"  ABORTA: la corrida uso soportes {meta.get('soportes')} y este "
              f"analisis declara {PROBLEMA['bounds']}.")
        return 1

    Y = {s: np.array([float(r[s]) for r in filas]) for s in salidas_act}

    # ── 2. indices ─────────────────────────────────────────────────────────
    from SALib.analyze import sobol as sobol_analyze

    # ── tratamiento de fallos: DESCARTE DE BLOQUES, no imputacion ──────────
    # Imputar por la media hace que la fila fallida se comporte como un sorteo
    # independiente, lo que anade aproximadamente +f a CADA ST (ley verificada
    # sobre Ishigami: ST_est ~ (1-f)*ST + f). Para un indice del orden de 0,004
    # —que es el que adjudica la cota del articulo— eso es un factor 17 con solo
    # el 2,4 % de fallos. El sesgo, ademas, no tiene direccion unica cuando los
    # fallos dependen de los parametros, que es el caso: son timeouts en zonas
    # rigidas del integrador.
    #
    # Descartar el BLOQUE de Saltelli completo conserva exactamente el
    # apareamiento A/B/AB. La objecion heredada de
    # analysis/global_sensitivity.py —que excluir romperia el apareamiento— es
    # falsa: rompe excluir FILAS sueltas, no bloques.
    #
    # Precision necesaria: el estimador resultante es insesgado SI el fallo es
    # independiente de los parametros. Aqui no lo es —los timeouts se
    # concentran en zonas rigidas del integrador—, de modo que queda un sesgo
    # residual; medido sobre un banco de pruebas descartando el 16 % de los
    # bloques de forma dependiente, fue de orden 10 % relativo sobre el indice
    # mas pequeno. Es dos ordenes menor que la imputacion por la media, no cero.
    # Por eso el informe publica siempre la fraccion descartada.
    #
    # La estructura de bloques verificada contra SALib 1.5.2: para cada muestra
    # base i el muestreo emite filas contiguas [A_i, AB_i^1..AB_i^D, B_i], y el
    # analisis las recupera con zancada D+2. De ahi B = len(NOMBRES) + 2.
    B = len(NOMBRES) + 2 if not SEGUNDO_ORDEN else 2 * len(NOMBRES) + 2
    n_bloques = M_esp // B

    filas_ind, res, conf, fracs = [], {}, {}, {}
    concluyente_dom = concluyente_cota = True
    n_cruza_total = n_barras = 0
    alarmas_globales: list = []
    alarmas_inmateriales: list = []
    for s in salidas_act:
        y = Y[s]
        # `~isfinite`, no `isnan`: el escritor usa `%.10g`, que serializa un
        # infinito como `inf`, y `float("inf")` se relee sin error. Con isnan
        # el bloque contaminado NO se descartaba, `Y.mean()` se volvia inf y
        # los cinco indices colapsaban a NaN mientras el informe declaraba
        # 0,00 % de fallos y la cota ADJUDICABLE.
        nan = ~np.isfinite(y)
        bloque_malo = nan.reshape(n_bloques, B).any(axis=1)
        frac_b = bloque_malo.sum() / n_bloques
        keep = np.repeat(~bloque_malo, B)
        y_ok = y[keep]
        n_ok = n_bloques - int(bloque_malo.sum())

        dom_ok = frac_b <= UMBRAL_DOMINANCIA
        # La COTA solo versa sobre `ganancia`/`b_mean`. Un AND sobre las tres
        # salidas hacia que un descarte alto en `ie` bloqueara la cota y el
        # informe dijera «la fraccion supera el umbral» de una salida cuya
        # fraccion era 0,00 %: una frase literalmente falsa.
        cota_ok = frac_b <= UMBRAL_COTA
        fracs[s] = frac_b
        concluyente_dom &= dom_ok
        if s == "ganancia":
            concluyente_cota = cota_ok
        print(f"\n  salida '{s}': {nan.sum()} evaluaciones fallidas -> "
              f"{int(bloque_malo.sum())}/{n_bloques} bloques descartados "
              f"({100*frac_b:.2f} %); quedan N={n_ok}")
        print(f"    dominancia {'valida' if dom_ok else 'NO VALIDA'} "
              f"(umbral {100*UMBRAL_DOMINANCIA:.0f} %)"
              + (f"   cota {'adjudicable' if cota_ok else 'NO ADJUDICABLE'} "
                 f"(umbral {100*UMBRAL_COTA:.0f} %)" if s == "ganancia" else ""))
        if n_ok < 8:
            print("    ABORTA: quedan menos de 8 bloques; el estimador no "
                  "tiene sentido.")
            return 1

        # Salida CONSTANTE: la varianza total es cero y los indices de Sobol no
        # estan definidos —son un cociente 0/0—. SALib no lo comprueba y muere
        # con `ValueError: setting an array element with a sequence` a mitad del
        # bucle, dejando artefactos a medias. Se detecta antes y se aborta
        # limpio: no es un fallo del analisis, es que esa salida no responde a
        # ningun parametro del hipercubo, y eso es informacion.
        var = float(np.var(y_ok))
        if var <= 0.0 or not np.isfinite(var):
            print(f"    ABORTA: la salida '{s}' es CONSTANTE sobre todo el "
                  f"hipercubo (varianza {var:.3g}).")
            print(f"    valor unico: {y_ok[0]:.6g}. Los indices de Sobol no "
                  f"estan definidos: no hay varianza que repartir.")
            print("    Revisa si esa salida depende de algun parametro barrido.")
            return 1
        try:
            Si = sobol_analyze.analyze(PROBLEMA, y_ok,
                                       calc_second_order=SEGUNDO_ORDEN,
                                       num_resamples=N_REMUESTRAS,
                                       conf_level=0.95, seed=SEMILLA_ANALISIS,
                                       print_to_console=False)
        except Exception as exc:
            print(f"    ABORTA: SALib fallo sobre la salida '{s}' "
                  f"({type(exc).__name__}: {exc}).")
            return 1
        print(f"    {'parametro':<12} {'S1':>9} {'+-':>8} {'ST':>9} {'+-':>8}")
        for i, p in enumerate(NOMBRES):
            s1, s1c = float(Si["S1"][i]), float(Si["S1_conf"][i])
            st, stc = float(Si["ST"][i]), float(Si["ST_conf"][i])
            cruza = (s1 - s1c <= 0 <= s1 + s1c) or (st - stc <= 0 <= st + stc)
            # Cada violacion se juzga con el criterio que le corresponde, no
            # todas contra el intervalo. Juzgarlas todas contra los extremos
            # hacia el sistema MONOTONO AL REVES: cuanto mas ancho el intervalo,
            # menos alarmas, de modo que una corrida con ST=20 y semiancho 1e31
            # salia sin una sola alarma y con codigo 0.
            #
            #   * ST > 1 y S1 > 1 son imposibles por definicion y se juzgan por
            #     el VALOR PUNTUAL: no son ruido simetrico, son falta de
            #     convergencia.
            #   * S1 < 0 SI es ruido esperable —el estimador de Saltelli para un
            #     parametro nulo sale negativo la mitad de las veces— y por eso
            #     se exige que el intervalo entero quede por debajo de cero.
            #     Alarmar por `s1 < 0` a secas declaraba no fiable cualquier
            #     corrida, incluida la referencia sintetica (8 de 21 filas).
            #   * Un semiancho mayor que el propio rango valido significa que el
            #     indice no esta estimado, aunque su valor puntual parezca sano.
            #
            # Calibrado contra la referencia sintetica, que es un GSA legitimo y
            # convergido: sus 21 filas dan CERO alarmas con estos criterios
            # (max ST = 0,9165; max ST_conf = 0,2588). Un criterio que marcara
            # la referencia estaria mal calibrado.
            alarma = []
            if not (np.isfinite(st) and np.isfinite(s1)
                    and np.isfinite(stc) and np.isfinite(s1c)):
                alarma.append("no-finito")
            else:
                if st > 1.0:
                    alarma.append("ST>1")
                if s1 > 1.0:
                    alarma.append("S1>1")
                if s1 + s1c < 0:
                    alarma.append("S1<0")
                if st < 0:
                    alarma.append("ST<0")
                if st + stc < s1 - s1c:
                    # ST < S1 es imposible por definicion; si los intervalos ni
                    # se rozan, el estimador no ha convergido.
                    alarma.append("ST<S1")
                if stc > 1.0 or s1c > 1.0:
                    alarma.append("IC>rango")
            # Materialidad: una alarma sobre un parametro cuyo ST esta bajo el
            # suelo de resolucion no indica falta de convergencia — no hay
            # efecto que converja. Se conserva visible y se marca; no bloquea.
            inmaterial = bool(alarma) and np.isfinite(st) and \
                abs(st) + (stc if np.isfinite(stc) else 0.0) < SUELO_RESOLUCION
            if alarma:
                etiqueta = f"{s}/{p}: {','.join(alarma)}"
                if inmaterial:
                    alarmas_inmateriales.append(
                        f"{etiqueta}  [INMATERIAL: ST={st:.2e}+-{stc:.2e} < "
                        f"{SUELO_RESOLUCION}]")
                else:
                    alarmas_globales.append(etiqueta)
            n_barras += 2
            n_cruza_total += int(s1 - s1c <= 0 <= s1 + s1c) + int(st - stc <= 0 <= st + stc)
            # La columna `concluyente` se rellena DESPUES del bucle con la
            # condicion GLOBAL. Rellenarla aqui solo podia mirar la propia fila
            # y su propia salida, de modo que salia `si` mientras el informe
            # declaraba la corrida entera no adjudicable — y quien filtrara el
            # CSV sacaba la conclusion contraria a la del informe.
            # `%.10g`, no `%.6f`: los indices nulos son de orden 1e-7 y con seis
            # decimales se escriben como `0.000000` junto a su intervalo. Quien
            # recalcule desde el CSV —una figura, un recuento— concluye que el
            # intervalo toca el cero cuando en memoria no lo tocaba. Paso por
            # esa piedra al recontar las barras: el CSV daba 15 de 30 y el
            # informe, que cuenta sobre los flotantes, 10 de 30.
            filas_ind.append([s, p, f"{s1:.10g}", f"{s1c:.10g}", f"{st:.10g}",
                              f"{stc:.10g}", "si" if cruza else "no",
                              ";".join(alarma), None, f"{frac_b:.4f}"])
            res[(s, p)] = (s1, st)
            conf[(s, p)] = (s1c, stc)
            print(f"    {p:<12} {s1:>9.4f} {s1c:>8.4f} {st:>9.4f} {stc:>8.4f}"
                  f"{'  ' + ','.join(alarma) if alarma else ''}"
                  f"{'  (IC cruza 0)' if cruza else ''}")

    # Condicion global: la misma que rotula la cabecera del informe y la misma
    # que decide el codigo de salida. Un lector del CSV y un lector del informe
    # tienen que poder llegar a la misma conclusion.
    valida_global = concluyente_dom and not alarmas_globales
    for fila in filas_ind:
        fila[8] = "si" if valida_global else "no"

    with open(sal / f"indices_{tag}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["salida", "parametro", "S1", "S1_conf", "ST", "ST_conf",
                    "IC_cruza_cero", "alarma", "concluyente",
                    "frac_bloques_descartados"])
        w.writerows(filas_ind)

    # ── 3. comparacion por solapamiento de intervalos ──────────────────────
    ref = leer_referencia()
    comp, cambios = [], []
    sin_veredicto_comp = False
    if ref:
        print()
        print("=" * 70)
        print("REAL frente a SINTETICO  (ST, con solapamiento de intervalos)")
        print("=" * 70)
        for s in salidas_act:
            for p in NOMBRES:
                if (s, p) not in ref or (s, p) not in res:
                    continue
                st_r, stc_r = res[(s, p)][1], conf[(s, p)][1]
                st_s, stc_s = ref[(s, p)][2], ref[(s, p)][3]
                solapa = (st_r - stc_r) <= (st_s + stc_s) and \
                         (st_s - stc_s) <= (st_r + stc_r)
                # TRES estados, no dos. Marcar un par excluido como «solapan»
                # seria afirmar algo falso sobre los intervalos —PGB sobre la
                # ganancia esta a mas de 20 sigmas— y quien filtrase el CSV por
                # solapan=si lo contaria como acuerdo con el sintetico.
                nota = ""
                if not np.isfinite(st_r) or not np.isfinite(stc_r):
                    # `solapa` con NaN da False, que se leia como «cambia»; y
                    # `max(st_s, nan)` devuelve st_s, que lo etiquetaba
                    # «irresoluble». Un indice que no existe no es un hallazgo.
                    estado, nota = "indisponible", "el indice real no es finito"
                elif p in NO_COMPARABLES:
                    estado, nota = "excluido", NO_COMPARABLES[p]
                elif max(st_s, st_r) < 0.05:
                    # Ventana del orden del ruido del propio estimador: declarar
                    # «cambia» aqui seria leer error de Monte Carlo como hallazgo.
                    estado = "irresoluble"
                    nota = "ambos ST < 0,05: por debajo de la resolucion"
                else:
                    estado = "si" if solapa else "NO"
                comp.append([s, p, f"{st_s:.4f}", f"{stc_s:.4f}",
                             f"{st_r:.4f}", f"{stc_r:.4f}", estado, nota])
                if estado == "NO":
                    cambios.append((s, p, st_s, st_r))
                rotulo = {"si": "solapan",
                          "NO": "NO SOLAPAN <-- cambia",
                          "excluido": "-- excluido",
                          "irresoluble": "-- irresoluble",
                          "indisponible": "-- indisponible"}[estado]
                print(f"  {s:<9} {p:<11} sint {st_s:>7.4f}+-{stc_s:<6.3f} "
                      f"real {st_r:>7.4f}+-{stc_r:<6.3f} {rotulo:<22}"
                      f"{'[' + nota + ']' if nota else ''}")
        with open(sal / f"comparacion_{tag}.csv", "w", newline="",
                  encoding="utf-8") as f:
            w = csv.writer(f)
            # `estado`: si | NO | excluido | irresoluble  (NO es booleano)
            w.writerow(["salida", "parametro", "ST_sintetico", "conf_sintetico",
                        "ST_real", "conf_real", "estado", "nota"])
            w.writerows(comp)
    else:
        print(f"\n  (no se hallo {REF_SINTETICA.name}: se omite la comparacion)")

    # ── 4. informe ─────────────────────────────────────────────────────────
    dom = {}
    for s in salidas_act:
        cand = sorted(((res[(s, p)][1], conf[(s, p)][1], p)
                       for p in NOMBRES if (s, p) in res), reverse=True)
        if len(cand) >= 2:
            st1, c1, p1 = cand[0]
            st2, c2, _ = cand[1]
            dom[s] = (p1, st1, c1, (st1 - c1) > (st2 + c2))

    st_b, c_b = res.get(("ganancia", "b_mean"), (np.nan, np.nan))[1], \
        conf.get(("ganancia", "b_mean"), (np.nan, np.nan))[1]
    cota_sup = 100 * (st_b + c_b)

    inf = [f"# GSA sobre datos reales — {tag}", ""]
    if es_verificacion:
        inf += ["> # ⚠ FICHERO DE VERIFICACION — NO CITAR", ">",
                "> Generado con `--verificar`: los valores no provienen del "
                "modelo. Sirve para comprobar que la cadena completa funciona, "
                "no para concluir nada.", ""]
    inf += [
           f"- Evaluaciones: **{M_esp}** (n_base {n_base}, {len(NOMBRES)} parametros)",
           f"- Semillas: muestreo **{semilla}**, remuestreo **{SEMILLA_ANALISIS}** "
           f"({N_REMUESTRAS} replicas)",
           "- Procedencia verificada contra la matriz regenerada: **si**",
           "- Fallos tratados por **descarte de bloques Saltelli completos**, no "
           "por imputacion",
           # Los rotulos incluyen las alarmas. Sin eso, la cabecera —que es
           # donde un lector se queda— decia «ADJUDICABLE» de una corrida cuyos
           # cinco indices eran NaN, y solo el cuerpo lo desmentia.
           f"- Dominancia: **{'VALIDA' if (concluyente_dom and not alarmas_globales) else 'NO VALIDA'}**"
           f"   ·   Cota: **{'ADJUDICABLE' if (concluyente_cota and not alarmas_globales) else 'NO ADJUDICABLE'}**"
           + ("   (hay alarmas: ver abajo)" if alarmas_globales else ""),
           # La fraccion descartada se PUBLICA, no se deja solo en la consola:
           # es la condicion bajo la cual todo lo demas significa algo.
           "- Bloques descartados por salida: "
           + ", ".join(f"{s} {100*fracs.get(s, 0.0):.2f} %" for s in salidas_act),
           # CAL-43g: el desglose iba HARDCODEADO en «3 salidas» mientras
           # `n_barras` se calculaba. Al entrar `brecha_c1` el informe se
           # contradecia solo: decia «14 de 40» y a renglon seguido «x 3
           # salidas», que dan 30. Ahora sale del propio recuento.
           f"- Barras con IC que contiene el cero: **{n_cruza_total} de "
           f"{n_barras}** (una barra = un indice: "
           f"{n_barras // (2 * max(len(salidas_act), 1))} parametros x 2 "
           f"indices x {len(salidas_act)} salidas). "
           f"En `indices_*.csv` la columna `IC_cruza_cero` es por "
           f"FILA —cruza si lo hace S1 **o** ST—, de modo que su recuento no "
           f"coincide con este ni tiene por que.",
           f"- Datos: cobertura **{cobertura}**, horizonte **{horizonte}**, "
           f"N={meta.get('N','?')} T={meta.get('T','?')} h, huella `{h_datos}`"]
    if alarmas_inmateriales:
        inf += ["", f"> **Alarmas INMATERIALES** ({len(alarmas_inmateriales)}) — "
                f"disparadas por parametros cuyo indice total esta por debajo del "
                f"suelo de resolucion del estimador ({SUELO_RESOLUCION}). No hay "
                f"efecto que pueda converger, de modo que no indican falta de "
                f"convergencia y **no bloquean el veredicto**. Se listan por "
                f"transparencia:", ""]
        for a_ in alarmas_inmateriales:
            inf.append(f"> - {a_}")
        inf += ["", "> El suelo es el mismo 0,05 con que la seccion de "
                "comparacion declara un par «irresoluble». Que se aplicara "
                "tambien a las alarmas se identifico tras la corrida M3; **no "
                "altera ningun indice**, solo si una alarma bloquea el veredicto.",
                ""]
    if alarmas_globales:
        inf += ["", "> ⚠ **Alarmas de convergencia** — indices fuera de [0,1] o no "
                "finitos. Con esto presente, ningun veredicto de abajo es de fiar:",
                ""]
        for a in alarmas_globales:
            inf.append(f"> - {a}")
    inf += ["", "## Parametros excluidos del barrido, y por que", ""]
    for p, razon in EXCLUIDOS.items():
        inf.append(f"- **`{p}`**: {razon}.")
    inf += ["", "## Parametro dominante por salida", ""]
    if not concluyente_dom or alarmas_globales:
        # Sin este aviso, quien salte directo a esta seccion se lleva un
        # dominante «separado del segundo» sin enterarse de que la corrida no
        # cumple las condiciones bajo las que esa frase significa algo.
        inf += ["> **Lo que sigue NO es adjudicable** por lo declarado arriba "
                "(fallos por encima del umbral y/o alarmas). Se lista como "
                "diagnostico de la corrida, no como resultado.", ""]
    for s, (p, st, c, sep) in dom.items():
        nota_sep = ("separado del segundo" if sep else
                    "**NO separado del segundo**: con este diseno no se puede "
                    "afirmar cual domina")
        inf.append(f"- **{s}**: `{p}`, ST = {st:.4f} ± {c:.4f} — {nota_sep}")
    inf += ["", "## La cota que el articulo publica", "",
            "El articulo afirma que ningun parametro de calibracion interna "
            "explica mas del 0,9 % de la varianza de la ganancia.", "",
            f"En el caso de estudio el unico parametro interno que existe es "
            f"`b_mean` — ver las exclusiones de arriba. Su ST es "
            f"**{100*st_b:.3f} %**, con extremo superior del intervalo en "
            f"**{cota_sup:.3f} %**.", ""]

    # La misma regla aplicada a la REFERENCIA, para que se vea de donde viene.
    ref_b = ref.get(("ganancia", "b_mean"))
    ref_a = ref.get(("ganancia", "alpha_mean"))
    if ref_b and ref_a:
        sup_b, sup_a = 100 * (ref_b[2] + ref_b[3]), 100 * (ref_a[2] + ref_a[3])
        # La conclusion se DERIVA de los numeros que se acaban de imprimir. Ir
        # cableada contradecia el proposito de leer la referencia del disco: si
        # se regenera con otros intervalos, la frase tiene que seguirla.
        if max(sup_b, sup_a) > 0.9:
            cierre = ("Es decir, **la cota del 0,9 % ya era no resoluble sobre "
                      "los propios datos que la produjeron**; lo que siga no es "
                      "un descubrimiento del caso real.")
        else:
            cierre = ("Ambos quedan por debajo del 0,9 %: sobre la referencia "
                      "la cota si era resoluble, de modo que una discrepancia "
                      "aqui si seria atribuible al caso de estudio (con la "
                      "salvedad de los seis cambios simultaneos de mas abajo).")
        inf += [f"Aplicando la misma regla al GSA sintetico que originó la "
                f"afirmacion: `b_mean` da extremo superior **{sup_b:.2f} %** y "
                f"`alpha_mean` **{sup_a:.2f} %**. {cierre}", ""]

    if not concluyente_cota:
        inf.append("**SIN VEREDICTO**: la fraccion de bloques descartados supera "
                   f"el {100*UMBRAL_COTA:.1f} % que esta adjudicacion exige. "
                   "Adjudicar una cota sub-1 % con mas fallos que eso es leer el "
                   "ruido del descarte como si fuera senal.")
    elif alarmas_globales:
        inf.append("**SIN VEREDICTO**: hay alarmas de convergencia (ver arriba).")
    elif cota_sup <= 0.9:
        inf.append("La cota **SE SOSTIENE** incluso en el extremo superior del "
                   "intervalo.")
    elif 100 * st_b <= 0.9:
        inf.append("La estimacion puntual queda por debajo del 0,9 %, pero el "
                   "intervalo lo cruza: con este diseno la afirmacion **no es "
                   "resoluble**.")
    else:
        inf.append("La cota **NO SE SOSTIENE**.")

    inf += ["", "## Frente al GSA sintetico", "",
            "Dos asimetrias del lado de la referencia, antes de nada: usa **100 "
            f"remuestras** frente a las {N_REMUESTRAS} de aqui, de modo que sus "
            "intervalos son mas ruidosos; y trata sus fallos por **imputacion "
            "por la media**, que infla sus ST. La comparacion es orientativa, no "
            "un contraste entre dos estimaciones del mismo rigor.", "",
            "Entre las dos corridas cambian **seis cosas a la vez** —los datos, "
            "el hipercubo (5 parametros frente a 7), el soporte de PGS, "
            "`a = c = 0`, la clasificacion de prosumidores y la serie de bolsa "
            "(constante = PGB en el sintetico, horaria real aqui)—, de modo que "
            "una discrepancia **no es atribuible a los datos** sin mas analisis. "
            "Ampliar el soporte de PGS, ademas, mete mas varianza en el "
            "denominador comun y desinfla los indices de los demas parametros "
            "por puro diseno; la magnitud de ese desinflado no se ha medido y "
            "no debe estimarse a ojo.", ""]
    if not ref:
        inf.append("No se hallo la referencia sintetica.")
    elif not concluyente_dom or alarmas_globales:
        inf.append("**SIN VEREDICTO**: la corrida no cumple las condiciones de "
                   "validez declaradas arriba.")
    elif cambios:
        inf.append("Estos indices **no solapan** con los del caso sintetico:")
        for s, p, a, b in cambios:
            inf.append(f"- `{p}` sobre **{s}**: {a:.4f} -> {b:.4f}")
        inf += ["", "Conviene revisar §III-E y §IV-B del articulo y §7.10 de la "
                "tesis a la luz de estos indices, teniendo presente la salvedad "
                "de los seis cambios simultaneos."]
    else:
        # «Comparables» son los que se compararon —solapen o no—, no solo los
        # que solaparon. Contar los "si" hacia desaparecer del informe los pares
        # `irresoluble`, entre ellos `ganancia/b_mean`: justo el parametro sobre
        # el que versa la cota del articulo.
        n_comparables = sum(1 for fila in comp if fila[6] in ("si", "NO"))
        n_irresolubles = sum(1 for fila in comp if fila[6] == "irresoluble")
        n_indisp = sum(1 for fila in comp if fila[6] == "indisponible")
        # Salidas cuyo parametro DOMINANTE en la referencia esta excluido de la
        # comparacion. Para esas no se puede afirmar que «la dominancia se
        # conserva»: precisamente el dominante es lo que no se comparo. En la
        # referencia actual PGB domina `ie` con ST = 0,9165, el mayor de las 21
        # filas, y PGB esta excluido.
        dom_sin_comparar = []
        for s in salidas_act:
            pares = [(ref[(s, q)][2], q) for q in NOMBRES if (s, q) in ref]
            if pares and max(pares)[1] in NO_COMPARABLES:
                dom_sin_comparar.append((s, max(pares)[1]))
        n_excl = len(comp) - n_comparables - n_irresolubles - n_indisp
        desglose = (f"De los {len(comp)} pares: **{n_comparables} comparables**, "
                    f"{n_excl} excluidos por diseno, {n_irresolubles} por debajo "
                    f"de la resolucion del estimador, {n_indisp} sin indice.")
        if n_comparables == 0:
            inf.append(f"**SIN VEREDICTO**: no quedo ni un solo par comparable. "
                       f"{desglose} No hay nada que sostenga una afirmacion en "
                       f"ninguna direccion.")
            sin_veredicto_comp = True
        else:
            inf.append(f"Los {n_comparables} pares comparables solapan con los "
                       f"del caso sintetico. {desglose} Las conclusiones del "
                       f"articulo se sostienen **sobre esos pares**, pero el "
                       f"texto debe decir que ahora estan medidas **sobre el "
                       f"caso de estudio** — que es justo lo que antes no era "
                       f"cierto.")
            if dom_sin_comparar:
                detalle = ", ".join(f"{s} (dominante `{q}`)"
                                    for s, q in dom_sin_comparar)
                inf += ["", f"**No se puede afirmar que la estructura de "
                        f"dominancia se conserve en: {detalle}.** En esas "
                        f"salidas el parametro que domina en la referencia es "
                        f"justamente uno de los excluidos, de modo que no se "
                        f"comparo."]
    if NO_COMPARABLES:
        inf += ["", "Excluidos de la comparacion:"]
        for p, razon in NO_COMPARABLES.items():
            inf.append(f"- `{p}`: {razon}.")

    (sal / f"INFORME_{tag}.md").write_text("\n".join(inf) + "\n", encoding="utf-8")
    # Antes se anunciaba el CSV de comparacion siempre. Sin referencia en disco
    # no se escribe, y si quedaba uno de una corrida anterior el mensaje lo
    # senalaba como recien producido junto a un informe que decia lo contrario.
    escritos = [f"indices_{tag}.csv"]
    if ref:
        escritos.append(f"comparacion_{tag}.csv")
    escritos.append(f"INFORME_{tag}.md")
    print("\n  escritos " + ", ".join(escritos))
    if (es_verificacion or alarmas_globales or not concluyente_dom
            or not concluyente_cota or sin_veredicto_comp):
        # Antes se ignoraba `concluyente_cota`: el script salia con 0 y el
        # lanzador daba la corrida por buena mientras el informe decia
        # «SIN VEREDICTO». El unico aviso quedaba en la prosa.
        print("\n  ATENCION: la corrida NO cumple las condiciones de validez. "
              "Ver el informe.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
