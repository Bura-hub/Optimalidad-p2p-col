"""Maquinaria compartida del GSA sobre DATOS REALES.

POR QUE EXISTE
--------------
`analysis/global_sensitivity.py` corre el analisis global de sensibilidad sobre
el CASO SINTETICO de 6 agentes y 24 horas del modelo base, no sobre el caso de
estudio. El propio orquestador lo declara y rechaza la combinacion:

    main_simulation.py:1505
    ap.error("--gsa corre el modelo de referencia sintetico y es "
             "incompatible con --full/--analysis/--include-c5/...")

pero la tesis (§7.1, §7.10) y el articulo lo narran como si caracterizara el
benchmark de 6 144 h. Este modulo corre el analisis sobre los datos reales.

DISENO — CINCO parametros, no siete. Las dos exclusiones son resultados.
-----------------------------------------------------------------------
El GSA sintetico barre siete. Aqui se barren cinco, y las dos exclusiones no
son un atajo sino consecuencias del caso de estudio que conviene declarar:

  * `alpha_mean` (flexibilidad de demanda) SE EXCLUYE. El orquestador **no
    pasa `alpha`** en modo datos reales (`main_simulation.py:252-257`), de modo
    que `AgentParams` lo deja en ceros y el programa de respuesta a la demanda
    queda apagado — es la premisa «SIN DR» de toda la tesis, y esta en la
    cabecera del propio orquestador. Barrerlo aqui haria dos danos: mediria un
    mecanismo que el caso de estudio no tiene, y activaria en cada muestra un
    SLSQP de N*T variables que sobre 6 144 h vuelve cada evaluacion
    impracticable. Consecuencia para el manuscrito: **del caso de estudio no se
    puede afirmar nada sobre la flexibilidad de demanda**; el ST de 0,008 que
    hoy se publica proviene del caso sintetico, donde el DR si esta activo.

  * `pi_ppa` (precio del contrato bilateral) SE EXCLUYE. Solo entra en el
    escenario C2 y ninguna de las tres salidas evaluadas proviene de C2, de
    modo que su indice es cero **por construccion**, no por medicion. La tesis
    ya lo declara asi en §7.10. Barrerlo gastaria una dimension entera del
    diseno en ruido.

  Con `calc_second_order=False` (S2 no se usa en el informe, y el sintetico
  tampoco lo reporta):  M = n_base * (5 + 2) = n_base * 7.
  El factor vive en `FACTOR_SALTELLI`, que se deriva de `SEGUNDO_ORDEN` para
  que el muestreo y el analisis no puedan discrepar. Con n_base=128 -> 896.

QUE SE CONSERVA para que la comparacion tenga sentido
-----------------------------------------------------
Los soportes de PGB, factor_PV, factor_D y b_mean son identicos a los del GSA
sintetico. El esquema de muestreo es el mismo. Las tres salidas son las mismas.

QUE CAMBIA, y por que
---------------------
  1. DATOS reales del MTE, cobertura M1 o M3.
  2. SOLUCIONADOR identico al del orquestador en datos reales
     (`main_simulation.py:259`: `tau=0.001`, `t_span=(0,0.005)`,
     `n_points=150`, `stackelberg_iters=2`), con `parallel=False` porque aqui
     la paralelizacion es por procesos.
     Frente al GSA sintetico la diferencia NO esta en la ODE —el sintetico usa
     los DEFAULTS `t_span=(0,0.01)`, `n_points=300`, que son mas caros con el
     mismo dt—, sino en el criterio de Stackelberg: el sintetico lo relaja a
     `tol=5e-3, max=4` (`analysis/global_sensitivity.py:147`) y aqui rigen los
     estrictos `tol=1e-3, max=10`.
  3. `a = c = 0` — convencion del caso de estudio (CAL-32). Deja a `b_mean`
     como unico parametro de costo, que es lo que el articulo afirma que no
     gobierna la ganancia.
  4. `prosumer_ids = range(N)` FIJO, como el orquestador
     (`main_simulation.py:221`). Clasificar dinamicamente segun quien vendio
     cambiaria la DEFINICION de la metrica dentro del hipercubo: en la esquina
     de poca generacion y mucha demanda la lista se encoge y la ganancia salta
     decenas de puntos, y Sobol lo atribuiria al modelo.
  5. `pi_bolsa` es la SERIE HORARIA REAL, sin reescalar. `PGB` mueve
     unicamente el piso de la banda del juego. Reescalar la serie al nivel
     barrido —como se hacia en una version anterior de este modulo— derogaba en
     silencio el techo CREG 101 066 que el pipeline ya habia aplicado y
     producia precios de hasta 6 094 COP/kWh, ocho veces la tarifa minorista.
  6. Soporte de PGS ampliado a [600, 1000]. El valor del caso de estudio es
     `community_effective_pi_gs = 906,27` COP/kWh y la matriz de liquidacion
     recorre [773,5 - 980,4] EN EL NOMINAL, AMBOS FUERA del [500, 750] del GSA
     sintetico: con aquel soporte el barrido nunca visitaba la tarifa real.
     **Consecuencia: el indice de PGS no es directamente comparable con el
     sintetico**, y el informe lo marca.

     Tres salvedades del soporte que hay que declarar al publicar el indice de
     PGS, porque no son neutrales:
       (a) BAJO EL BARRIDO la matriz recorre [512,1 - 1081,8], no [773,5 -
           980,4]. Este ultimo es solo el nominal.
       (b) El soporte es ASIMETRICO respecto del caso: el nominal 906,27 cae en
           el percentil 76,6, de modo que el diseno explora un -33,8 % por
           debajo y solo un +10,3 % por encima. El indice de PGS queda
           gobernado por la rama descendente.
       (c) Con los cargos regulados reales (T+D+PR+Rm+Cvm+COT = 492,44 COP/kWh
           sobre un CU base NT2 de 797,04), el piso alcanzable es 559,9. El
           tramo [600, 671] —el 17,8 % del ancho del soporte— no corresponde a
           ningun escenario tarifario alcanzable. Es un barrido de estres, no
           una caracterizacion de la incertidumbre tarifaria real: los 13 meses
           del CSV Cedenar solo recorren [871,9 - 928,9], un +/-3 %.

  7. `pi_gs` DESDOBLADO en sus dos papeles, como en produccion: el escalar entra
     al juego (`GridParams`) y la matriz (N,T) a la liquidacion
     (`run_comparison`). Ver la nota en `cargar_datos`.
     Alcance real, que conviene no exagerar: de las tres salidas **solo
     `ganancia` ve la matriz**. `sc` es fisica (volumenes) y `ie` sale de
     `r.IE`, que usa exclusivamente el escalar. Es fiel a produccion —alli el IE
     tambien es escalar—, pero el argumento de «el autoconsumo se valora agente
     a agente» aplica unicamente a `ganancia`.

SIMPLIFICACION DECLARADA — Y SU CADUCIDAD (CAL-43)
--------------------------------------------------
Hasta CAL-43, `run_comparison` se invocaba con el juego minimo de argumentos.
Era valido porque las TRES salidas de entonces dependian solo de
`p2p_results`, `D`, `G_klim`, `pi_gs`, `pi_gb`, `pi_bolsa` y `prosumer_ids`, y
el propio modulo advertia: «si se anade una salida de un escenario regulado,
ESTO DEJA DE SER VALIDO».

La cuarta salida `brecha_c1` es exactamente ese caso, de modo que la
simplificacion CADUCA y hay que pasar lo que C1 necesita:

  * `month_labels` — el periodo de facturacion. Sin el, C1 netea las 6 144 h
    como un unico periodo; con el, mes a mes, como la CREG 174 y como
    produccion.
  * `component_c` — el Cvm literal de CEDENAR. Con el defecto `"auto"`,
    C = 0,1385 x pi_gs **escala con el PGS barrido**, de modo que el indice de
    Sobol de PGS sobre la brecha mediria un artefacto del modo de respaldo.

Lo que NO se pasa, y por que no hace falta: `pde`, `capacity` y `tolls` solo
entran en C4/C5, y ninguna de las cuatro salidas proviene de C4 ni de C5.

Las tres salidas anteriores no se mueven por esto: P2P, C2, C3 y C4 no dependen
de `month_labels` ni de `component_c`. Verificado en
`Documentos/auditoria_artefactos_2026-08-07/fase_a/verificar_a1_plomeria.py`.

NO modifica nada fuera de gsa_real/.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

SALIDA = Path(__file__).resolve().parent / "salidas"
CACHE = SALIDA / "cache"

# ── Los cinco parametros barridos ───────────────────────────────────────────
NOMBRES = ["PGB", "PGS", "factor_PV", "factor_D", "b_mean"]
SOPORTES = [
    # CAL-42: identico al sintetico porque el 114 ES el piso adimensional del
    # modelo base, no una cifra de la CREG 101 066. Cota de estres declarada.
    [114.0, 500.0],    # PGB   COP/kWh  — cota declarada, no normativa
    [600.0, 1000.0],   # PGS   COP/kWh  — AMPLIADO: contiene el real 906,27
    [0.5, 2.0],        # factor_PV      — identico
    [0.7, 1.5],        # factor_D       — identico
    [150.0, 400.0],    # b_mean COP/kWh — identico; el real es 225-241
]
PROBLEMA = {"num_vars": len(NOMBRES), "names": NOMBRES, "bounds": SOPORTES}

# Los indices de segundo orden NO se usan en el informe. Activarlos casi
# duplicaria el numero de evaluaciones para nada: con calc_second_order=True
# el esquema pide n_base*(2D+2), y con False n_base*(D+2).
#
# UNA SOLA FUENTE DE VERDAD, a proposito: si el muestreo y el analisis
# discreparan en esta bandera, SALib puede aceptar el vector y estimar un
# diseno inexistente EN SILENCIO. Ambos guiones importan estas dos constantes.
SEGUNDO_ORDEN = False
FACTOR_SALTELLI = (2 * len(NOMBRES) + 2) if SEGUNDO_ORDEN else (len(NOMBRES) + 2)

# CAL-43 (A2): la CUARTA salida es la BRECHA, no un nivel mas.
#
# Las tres primeras son niveles del P2P. Sobol sobre ellas responde «que gobierna
# cuanto vale el P2P», y el articulo la usaba para sostener que el ORDENAMIENTO
# frente a la regulacion es robusto — cosa que esos tres indices no miden. La
# objecion es legitima: un nivel puede ser insensible mientras el orden se
# invierte, porque el comparador se mueve igual.
#
# `brecha_c1` = B_P2P - B_C1 sobre el mismo punto del hipercubo. Su signo ES el
# ordenamiento, de modo que ST sobre ella responde la pregunta que el titulo
# hace. C1 ya se calculaba dentro de `run_comparison` y se descartaba: el coste
# adicional es cero.
#
# Se elige C1 —no C4— porque es el unico comparador cuyo ordenamiento frente al
# P2P NO es incondicional (el barrido SA-2 lo invierte para phi en [1,7; 2,6]),
# y por tanto el unico donde la pregunta tiene respuesta no trivial.
SALIDAS = ["ganancia", "sc", "ie", "brecha_c1"]

# Parametros excluidos del barrido, con su razon. El informe los reproduce.
EXCLUIDOS = {
    "alpha_mean": "el caso de estudio corre SIN programa de respuesta a la "
                  "demanda (el orquestador no pasa alpha), de modo que el "
                  "parametro no existe en el modelo evaluado",
    "pi_ppa":     "solo entra en el escenario C2 y ninguna de las cuatro "
                  "salidas proviene de C2: su indice seria cero por "
                  "construccion",
}


# ═══════════════════════════════════════════════════════════════════════════
#  Carga de datos — cacheada en disco (.npz) para no releer 609 MB por muestra
# ═══════════════════════════════════════════════════════════════════════════
_MEM: dict = {}


def _ruta_cache(cobertura: str, horizonte: str) -> Path:
    return CACHE / f"datos_{cobertura}_{horizonte.replace(':', '-')}.npz"


def cargar_datos(cobertura: str = "M1", horizonte: str = "full",
                 verbose: bool = False, forzar: bool = False):
    """Devuelve SIETE elementos: (D, G, pi_bolsa, nombres, pi_gs_mat,
    pi_gs_eff, extras).

    `pi_gs_mat` y `pi_gs_eff` son el desdoble de la tarifa que hace produccion:
    la matriz `(N, T)` que entra a la LIQUIDACION y el escalar ponderado que
    entra al JUEGO. Quien llame debe desempaquetar los siete — un llamador que
    se quedo en cuatro tras ampliar esta firma reventaba la corrida entera con
    un `ValueError: too many values to unpack` despues de 14 s de carga.

    `extras` (CAL-43) es un DICCIONARIO, a proposito: la firma queda fijada en
    siete y lo que se anada en el futuro no vuelve a romper a los llamadores.
    Trae hoy dos claves:

      `meses`   vector `(T,)` de etiquetas `AAAAMM`, el mismo que construye
                `main_simulation.py:138`. Sin el, C1 netea TODO el horizonte
                como un unico periodo de facturacion, que es un regimen que la
                CREG 174 no contempla y que sobrestima C1.
      `cvm_mat` matriz `(N, T)` del componente Cvm literal de CEDENAR
                (CREG 119/2007 art. 11), el mismo `component_c` que pasa
                produccion (`main_simulation.py:304`). Importa mas de lo que
                parece: con el defecto `"auto"`, C = 0,1385 x pi_gs **escala
                con el PGS barrido**, de modo que la brecha P2P-C1 se movia por
                un artefacto del modo de respaldo y no por la tarifa real. Con
                la matriz literal, Cvm no escala — que es lo que hace la norma.


    La primera llamada lee el dataset completo del MTE (~14 s, ~450 MB de pico)
    y deja un `.npz` de medio megabyte. Las siguientes leen el `.npz` en
    milisegundos. Sin esto, y dado que cada evaluacion corre en un proceso
    nuevo, las 512+ muestras releerian el dataset entero una y otra vez.
    """
    clave = (cobertura, horizonte)
    if clave in _MEM and not forzar:
        return _MEM[clave]

    mte_root = os.environ.get("MTE_ROOT", str(RAIZ / "MedicionesMTE_v3"))
    proc = huella_datos(mte_root, cobertura, horizonte)

    CLAVES = {"D", "G", "pi_bolsa", "nombres", "pi_gs_mat", "pi_gs_eff",
              "meses", "cvm_mat", "procedencia"}
    npz = _ruta_cache(cobertura, horizonte)
    if npz.exists() and not forzar:
        # `with`: sin cerrar el NpzFile, `os.replace` sobre el mismo nombre
        # falla en Windows con PermissionError al regenerar. Y el try/except:
        # un `.npz` truncado (un scp a medias) hacia que CADA evaluacion
        # devolviera NaN con motivo=BadZipFile, gastando la noche entera en vez
        # de regenerarlo.
        try:
            with np.load(npz, allow_pickle=True) as z:
                claves = set(z.files)
                vieja = str(z["procedencia"]) if "procedencia" in claves \
                    else "(sin marca)"
                if not CLAVES <= claves:
                    # CAL-43: DECIR QUE FALTA. El mensaje anterior nombraba una
                    # clave fija («la matriz de liquidacion»), de modo que al
                    # ampliar el formato mentia sobre el motivo real.
                    print("  [cache] formato antiguo, faltan %s -> se regenera"
                          % sorted(CLAVES - claves))
                elif vieja != proc:
                    # Un cache de OTRO dataset bajo el mismo nombre se leeria en
                    # silencio y toda la corrida saldria de datos equivocados.
                    print(f"  [cache] procedencia distinta -> se regenera\n"
                          f"          en disco: {vieja}\n          ahora   : {proc}")
                else:
                    res = (z["D"], z["G"], z["pi_bolsa"], list(z["nombres"]),
                           z["pi_gs_mat"], float(z["pi_gs_eff"]),
                           {"meses": z["meses"], "cvm_mat": z["cvm_mat"]})
                    _MEM[clave] = res
                    return res
        except Exception as exc:
            print(f"  [cache] ilegible ({type(exc).__name__}) -> se regenera")

    from data.xm_data_loader import MTEDataLoader
    import pandas as pd

    demand_cfg = None
    if cobertura.upper() == "M3":
        from data.preprocessing import PAPER_METER_DEMAND_CONFIG
        demand_cfg = PAPER_METER_DEMAND_CONFIG
    elif cobertura.upper() != "M1":
        raise ValueError(f"cobertura desconocida: {cobertura}")

    loader = MTEDataLoader(mte_root, demand_config=demand_cfg)
    D, G, idx = loader.load(verbose=verbose)

    # Misma llamada que el orquestador en modo --full (main_simulation.py:163)
    from data.xm_prices import get_pi_bolsa
    t_ini = idx[0].strftime("%Y-%m-%d")
    t_fin = (idx[-1] + pd.Timedelta(hours=1)).strftime("%Y-%m-%d")
    pi_bolsa = np.asarray(get_pi_bolsa(D.shape[1], t_start=t_ini, t_end=t_fin,
                                       scenario="2025_normal"), dtype=float)

    # 'dia-promedio' se retiro a proposito: promediar por hora del dia destruye
    # el indice horario, y sin indice no hay matriz de tarifas por agente y mes
    # —que es lo que entra a la liquidacion—. Ademas no reproducia el modo
    # perfil-diario del orquestador, que llama a get_pi_bolsa(24) con sus
    # propios defaults (main:180-187), no promedia la serie real.
    if horizonte.startswith("mes:"):
        objetivo = horizonte.split(":", 1)[1]
        mask = np.asarray(pd.PeriodIndex(idx, freq="M").astype(str) == objetivo)
        if not mask.any():
            raise ValueError(f"el mes {objetivo} no esta en el horizonte")
        D, G, pi_bolsa, idx = D[:, mask], G[:, mask], pi_bolsa[mask], idx[mask]
    elif horizonte != "full":
        raise ValueError(f"horizonte desconocido: {horizonte} "
                         f"(validos: 'full', 'mes:AAAA-MM')")

    nombres = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"][:D.shape[0]]

    # El orquestador NO usa un solo pi_gs: usa DOS objetos (main:104-119).
    #   * escalar `community_effective_pi_gs`  -> entra al JUEGO (GridParams)
    #   * matriz (N,T) `pi_gs_per_agent_hourly` -> entra a la LIQUIDACION
    # Colapsarlos en un escalar movia la ganancia del punto nominal en torno a
    # un 1 %, porque el autoconsumo —el 93 % de la ganancia P2P— se valora
    # agente a agente y su tarifa efectiva no coincide con la del juego.
    # Se guardan ambos; `evaluar` mueve la matriz proporcionalmente al PGS
    # barrido, de modo que en el punto nominal reproduce produccion exactamente
    # y fuera de el conserva la heterogeneidad entre instituciones.
    from data.cedenar_tariff import (community_effective_pi_gs,
                                     cvm_per_agent_hourly,
                                     pi_gs_per_agent_hourly)
    pi_gs_mat = np.asarray(pi_gs_per_agent_hourly(nombres, idx), dtype=float)
    # CAL-43: mismo helper que main_simulation.py:304.
    cvm_mat = np.asarray(cvm_per_agent_hourly(nombres, idx), dtype=float)
    pi_gs_eff = float(community_effective_pi_gs(
        nombres, idx[0], idx[-1] + pd.Timedelta(hours=1),
        weights=D.mean(axis=1)))
    # CAL-43: mismo constructor que main_simulation.py:138 (AAAAMM entero).
    meses = np.array([ts.year * 100 + ts.month for ts in idx], dtype=int)
    if verbose:
        print(f"  pi_gs escalar (juego) = {pi_gs_eff:.2f} COP/kWh; "
              f"matriz (liquidacion) {pi_gs_mat.shape}, "
              f"rango [{pi_gs_mat.min():.1f}, {pi_gs_mat.max():.1f}]")
        print(f"  periodos de facturacion (C1): {len(set(meses.tolist()))} "
              f"meses, de {meses.min()} a {meses.max()}")
        print(f"  Cvm literal Cedenar: {cvm_mat.shape}, rango "
              f"[{cvm_mat.min():.1f}, {cvm_mat.max():.1f}] COP/kWh")

    npz.parent.mkdir(parents=True, exist_ok=True)
    # Escritura ATOMICA. Si dos procesos coinciden aqui (o si uno muere a mitad
    # del volcado), un `.npz` truncado se leeria como cache valido y toda la
    # corrida saldria de el. El temporal lleva el PID para que no colisionen.
    # Se pasa un descriptor abierto, no la ruta: con una ruta que no acaba en
    # `.npz` numpy le anade la extension y `os.replace` no encontraria nada.
    tmp = npz.parent / f"{npz.name}.tmp{os.getpid()}"
    with open(tmp, "wb") as fh:
        np.savez_compressed(fh, D=D, G=G, pi_bolsa=pi_bolsa,
                            nombres=np.array(nombres, dtype=object),
                            pi_gs_mat=pi_gs_mat, pi_gs_eff=pi_gs_eff,
                            meses=meses, cvm_mat=cvm_mat,
                            procedencia=np.array(proc))
    os.replace(tmp, npz)
    res = (D, G, pi_bolsa, nombres, pi_gs_mat, pi_gs_eff,
           {"meses": meses, "cvm_mat": cvm_mat})
    _MEM[clave] = res
    return res


# ═══════════════════════════════════════════════════════════════════════════
#  Evaluacion de UNA muestra
# ═══════════════════════════════════════════════════════════════════════════
def evaluar(params, cobertura: str = "M1", horizonte: str = "full",
            silenciar: bool = True):
    """Corre el modelo con un punto del hipercubo.

    Devuelve (ganancia, sc, ie, brecha_c1, motivo) — las cuatro `SALIDAS` en su
    orden, y al final el motivo. `motivo` es "" si todo fue bien, o el tipo de
    excepcion: distinguir un fallo numerico de uno de entorno importa al
    analizar, y el modulo anterior los confundia todos en un NaN mudo.

    CAL-43: la arity paso de 4 a 5. Los CSV de corridas anteriores NO tienen la
    columna `brecha_c1`, de modo que `--reanudar` sobre ellos reevalua todo; es
    lo correcto, porque a esas filas les falta una salida.
    """
    # El desvio se RESTAURA al salir (ver el `finally` del final). La version
    # anterior lo dejaba puesto: llamada desde el proceso principal —como hace
    # 1_calibrar— se tragaba en silencio todo lo que se imprimiera despues, y
    # fugaba un descriptor por llamada.
    _out, _err, _f, _fd = sys.stdout, sys.stderr, None, None
    if silenciar:
        # Igual que analysis/global_sensitivity.py:96-108 y por la misma razon
        # (CAL-39/CAL-28b): sin esto, 14 procesos escriben barras de progreso
        # sobre el mismo descriptor y un caracter no-ASCII bajo locale C mata
        # la evaluacion.
        try:
            reg = SALIDA / "workers"
            reg.mkdir(parents=True, exist_ok=True)
            _f = open(reg / f"w_{os.getpid()}.log", "a", encoding="utf-8",
                      buffering=1)
        except OSError:
            _f = open(os.devnull, "w", encoding="utf-8")
        sys.stdout = sys.stderr = _f
        # ...y TAMBIEN a nivel de descriptor. LSODA es Fortran (ODEPACK) y
        # escribe sus avisos directamente al fd 2, sin pasar por sys.stderr:
        # reasignar los objetos de Python no lo captura. Sin esto, 30 workers
        # vuelcan sus avisos entrelazados en el unico log de nohup y lo vuelven
        # ilegible. Van al log del worker, que es donde sirven de diagnostico.
        try:
            _fd = (os.dup(1), os.dup(2))
            os.dup2(_f.fileno(), 1)
            os.dup2(_f.fileno(), 2)
        except OSError:
            _fd = None

    from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams
    from scenarios import run_comparison

    import core.replicator_sellers as _rs
    _rs._fast_mode = False          # feedback_fast_mode_deprecado

    pgb, pgs, f_pv, f_d, b_mean = map(float, params)

    try:
        D0, G0, pi_bolsa, _, pi_gs_mat0, pi_gs_eff0, extras = cargar_datos(
            cobertura, horizonte)
        G = G0 * f_pv
        D = D0 * f_d
        N = D.shape[0]

        # El barrido mueve la tarifa minorista, que en produccion es DOS
        # objetos. Se escala la matriz de liquidacion por el mismo factor que
        # el escalar del juego: en el punto nominal (pgs = pi_gs_eff0) la
        # matriz queda IDENTICA a la de produccion, y fuera de el se conserva
        # la heterogeneidad entre instituciones (Udenar/HUDN ~797 frente a
        # Mariana/UCC/Cesmag ~956). Antes se pasaba `pgs` escalar a ambos, lo
        # que valoraba el autoconsumo —el 93 % de la ganancia P2P— a una tarifa
        # que ninguna institucion paga.
        pi_gs_liq = pi_gs_mat0 * (pgs / pi_gs_eff0)

        # alpha NO se pasa: queda en ceros y el DR queda apagado, igual que en
        # main_simulation.py:252-257. Ver la nota del encabezado.
        agents = AgentParams(
            N=N, a=np.zeros(N), b=np.full(N, b_mean), c=np.zeros(N),
            lam=np.full(N, 100.0), theta=np.full(N, 0.5), etha=np.full(N, 0.1),
        )
        grid = GridParams(pi_gs=pgs, pi_gb=pgb)
        # parallel=False es INDISPENSABLE: el defecto es True y abriria un
        # tercer nivel de paralelismo dentro de cada worker.
        solver = SolverParams(tau=0.001, t_span=(0.0, 0.005), n_points=150,
                              stackelberg_iters=2, parallel=False)

        ems = EMSP2P(agents, grid, solver)
        resultados, G_klim, D_star = ems.run(D, G)

        # Fijo, como el orquestador. Ver nota 4 del encabezado.
        prosumidores = list(range(N))
        consumidores: list = []

        # pi_bolsa es la serie REAL sin reescalar; PGB solo mueve el piso del
        # juego. Ver nota 5 del encabezado.
        # CAL-43: `month_labels` y `component_c` entran porque la cuarta salida
        # SI proviene de un escenario regulado. Ver «SIMPLIFICACION DECLARADA —
        # Y SU CADUCIDAD» en la cabecera del modulo.
        #
        # `cvm_mat` NO se reescala con el PGS barrido, a proposito: el Cvm de la
        # CREG 119/2007 es un cargo propio del comercializador y en el CSV de
        # CEDENAR varia mes a mes con independencia del CU. Escalarlo
        # reintroduciria justo el acoplamiento artificial que el modo "auto"
        # tenia y que esto viene a quitar.
        _T = D_star.shape[1]
        cr = run_comparison(
            D=D_star, G_klim=G_klim, G_raw=G,
            p2p_results=resultados,
            pi_gs=pi_gs_liq[:, :_T], pi_gb=pgb,
            pi_bolsa=pi_bolsa[:_T],
            prosumer_ids=prosumidores,
            consumer_ids=consumidores,
            month_labels=np.asarray(extras["meses"])[:_T],
            component_c=np.asarray(extras["cvm_mat"])[:, :_T],
        )
        return (float(cr.net_benefit.get("P2P", 0.0)),
                float(cr.self_consumption.get("P2P", 0.0)),
                float(cr.equity_index.get("P2P", 0.0)),
                float(cr.net_benefit.get("P2P", 0.0))
                - float(cr.net_benefit.get("C1", 0.0)),
                "")

    except Exception as exc:                             # pragma: no cover
        nan = float("nan")
        return nan, nan, nan, nan, type(exc).__name__

    finally:
        sys.stdout, sys.stderr = _out, _err
        if _fd is not None:
            # restaurar los descriptores ANTES de cerrar el fichero
            try:
                os.dup2(_fd[0], 1); os.dup2(_fd[1], 2)
                os.close(_fd[0]);   os.close(_fd[1])
            except OSError:
                pass
        if _f is not None:
            try:
                _f.close()
            except OSError:
                pass


def huella_datos(mte_root: str, cobertura: str, horizonte: str) -> str:
    """Huella de la FUENTE de datos: ruta, cobertura, horizonte e inventario de
    los ficheros bajo `mte_root` (ruta relativa + tamano, sin leer contenido).

    Sirve para dos cosas: invalidar el cache `.npz` si el dataset cambio, y
    dejar constancia en el `.meta.json` de sobre que datos se corrio. Sin ella,
    apuntar MTE_ROOT a otra copia reutilizaba el cache viejo en silencio.
    """
    raiz = Path(mte_root)
    inventario = []
    if raiz.is_dir():
        for p in sorted(raiz.rglob("*")):
            if p.is_file() and p.suffix.lower() in (".csv", ".xlsx", ".xls"):
                try:
                    inventario.append(f"{p.relative_to(raiz).as_posix()}:{p.stat().st_size}")
                except OSError:
                    continue
    # MTE_ROOT no es la unica fuente: la serie de bolsa y el preprocesado
    # tambien entran en D, G y pi_bolsa. Sin ellos, cambiar el CSV de precios
    # reutilizaba el cache con la serie vieja sin decir nada.
    otras = []
    for rel in ("data/precios_bolsa_xm_api.csv", "data/xm_precios_bolsa.csv",
                "data/precios_escasez_creg.csv", "data/preprocessing.py",
                "data/xm_prices.py", "data/xm_data_loader.py",
                # el CSV de tarifas determina pi_gs_mat y pi_gs_eff, que quedan
                # CONGELADOS en el .npz: sin el en la huella, anadir un mes o
                # corregir un CU se ignoraba en silencio
                "data/cedenar_tariff.py", "data/tarifas_cedenar_mensual.csv",
                "data/mem_costs_no_regulado.csv"):
        q = RAIZ / rel
        if q.is_file():
            try:
                otras.append(f"{rel}:{q.stat().st_size}")
            except OSError:
                pass
    s = f"{raiz.as_posix()}|{cobertura}|{horizonte}|{len(inventario)}|" \
        + "|".join(inventario) + "||" + "|".join(otras)
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def huella_diseno(cobertura, horizonte, n_base, semilla, segundo_orden) -> str:
    """Huella del diseno, para detectar que se mezclen dos corridas distintas."""
    s = f"{cobertura}|{horizonte}|{n_base}|{semilla}|{segundo_orden}|" \
        f"{'/'.join(NOMBRES)}|{SOPORTES}"
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def asegurar_salida() -> Path:
    SALIDA.mkdir(parents=True, exist_ok=True)
    return SALIDA
