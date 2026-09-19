"""
La compuerta de salida de la matriz con el reposo (D48 a D69; M-F). 2026-09-17.

QUE COMPRUEBA. La corrida de un caso de la matriz por `--metodo reposo` deja su
almacen (`core/almacen.py`). Este guion lo lee y comprueba, hora a hora, las
identidades del reposo en forma cerrada (seccion 5.1 de
`.superpowers/sdd/2026-09-16-sonda-equilibrio/fable-report.md`, y su seccion 6),
con el piso del vendedor marginal (D63 a D69, `fable-retiro-report.md`).
Falla con codigo distinto de cero en cuanto una hora no cumple:

  volumen      la suma de los flujos es la E del reposo, y
               E = min(oferta de los vendedores que pueden vender, demanda de
               los compradores que siguen en la hora). Se descuenta lo que el
               almacen declara fuera: `vendedores_excluidos` (D61),
               `vendedores_no_despachados` (los de piso sobre el nivel de
               cierre de la caminata, D65), los retirados por la participacion
               (C-151, papel «retirado») y `excluidos_bajo_piso` (D61
               parcial). Las cuatro causas se cuentan aparte, en horas y
               energia.
  excedente    el excedente guardado es sum (techo_i - piso_j)·P_ji, en sus dos
               formas: captura·excedente_optimo (tabla de horas) y la suma de
               ahorro_comprador + prima_vendedor (tabla de flujos).
  ingreso      sum_i p_liquidado_i·q_i = sum_i precio_reposo_i·q_i (D51).
  precios      ningun precio de un comprador servido, liquidado o del reposo,
               fuera de [piso del juego, techo del comprador]; y el precio
               uniforme y el comun de la hora, dentro de [piso del juego, techo
               mayor de la hora].
  vendedores   ningun vendedor despachado cobra, en promedio ponderado, bajo
               SU PISO (el `piso_vendedor` de sus flujos, no el piso del juego:
               es el teorema de cobertura de D63), y la parte de los vendedores
               de la hora no es negativa.
  captura      en [0, 1] cuando el optimo es positivo (D55).
  finitud      ningun NaN ni infinito en las columnas del reposo de la tabla
               de horas, en las de los flujos, en el sobrante y el faltante de
               la tabla de agentes, ni en el valor de la tabla de escenarios.
  sin_mercado  las horas sin mercado (`sin_mercado`, `sin_ganancia` y toda
               hora no resuelta) no tienen flujos.
  estado       toda hora resuelta tiene regimen de mercado; toda hora no
               resuelta lo es por «sin mercado esa hora» y no por una excepcion
               o un plazo vencido; ningun nombre de las listas falta en la
               tabla de agentes.
  cero_retiros D67: en un almacen por reposo NINGUNA hora tiene vendedores con
               papel «retirado». Con el piso del vendedor marginal todo
               despachado cobra al menos su piso, y la participacion (C-151)
               queda como guarda inerte: un retiro es un hallazgo, y falla.
  prima_descompuesta  D69: en las horas resueltas (con regimen de mercado),
               renta_inframarginal + parte_juego de la tabla de horas es la
               prima de los vendedores de sus flujos, sum (precio -
               piso_vendedor)·kwh.
  cuantal      D71: en toda hora con regimen, «cuantal» si y solo si el
               apartamiento pasa de TOL_FRAGIL_REL (1e-3, con la holgura del
               float32); una hora «cuantal» tiene un regimen cerrado de mercado
               y mu_cuantal > 0; cualquier otra, el regimen cerrado igual a su
               regimen. Informa, sin fallar, cuantas horas son «cuantal», cuantas
               de ellas con n_soluciones distinto de 1 (sec. 8.3 del diseno,
               esperado 0) y cuantas del lado de los vendedores (regimen
               cerrado de compradores cortos o de un comprador; sec. 8.2: si
               alguna, se mide M-D con el costo en el piso antes de publicar).
  p2p_c2       del caso entero, no de una hora (sintesis §6): el beneficio
               P2P y el de C2 de la tabla `escenarios` NO coinciden en todas
               las instituciones con energia P2P mayor que cero. Que coincidan
               en todas es el sintoma del defecto viejo (el mercado reducido a
               C2) y falla; que coincidan en algunas se informa sin fallar.
               Coinciden si |P2P - C2| <= max(1 (COP), 1e-6 x el mayor de los
               dos), el mismo empate de `compara_matriz_reposo.py`.

LAS TOLERANCIAS Y EL REDONDEO DEL ALMACEN. El almacen guarda los numeros en
precision sencilla (float32, `Almacen._vuelca`), con un error relativo de hasta
medio epsilon, unos 6e-8. Las tolerancias nominales del encargo (1e-6 (kWh) en
el volumen, 0,01 (COP) en el excedente, 1e-9 relativo en el ingreso) son mas
finas que ese redondeo en las horas grandes: con 300 (kWh) a 800 (COP/kWh), el
redondeo del excedente llega a centesimas de peso. Por eso cada comprobacion
usa la tolerancia nominal MAS una cota del redondeo float32 calculada para esa
hora (epsilon de float32 por la suma de los valores absolutos que intervienen).
El motor ya comprueba las identidades en float64 con las tolerancias nominales
(`core/reposo_mercado._comprueba`); esta compuerta comprueba lo que quedo
ESCRITO. El resumen dice cuantas horas pasan la cota de redondeo sin pasar la
nominal, para que ninguna se esconda en ella.

LO QUE EL ALMACEN NO GUARDA. La E del reposo no se escribe: se reconstruye de
la tabla de agentes (sobrante, faltante y papel) y de las listas de la tabla de
horas. Se supone que el sobrante y el faltante guardados son los que entraron
al nucleo; los dos salen de la misma generacion limite y la misma demanda de la
corrida (con la respuesta a la demanda apagada, como en los datos reales). El
excedente del reposo tampoco se escribe como tal: se compara la forma de los
flujos contra captura·optimo, que es lo que la hora guarda de el.

La funcion `comprueba` es pura: recibe los DataFrames de las cuatro tablas y no
lee parquet, de modo que se prueba sin pyarrow. `carga` lee el almacen con
`core.almacen.lee`, que si lo necesita. Misma separacion que
`censo_convergencia.py` y `compara_arranque.py`.

Uso, desde la raiz del repositorio:
    python -u reformateo/documento/scripts/sonda/compuertas_matriz_reposo.py \
        SALIDAS_SERVIDOR/matriz_reposo/E0/almacen --cobertura m1

Codigos de salida: 0 en verde; 1 si alguna hora (o el caso, en p2p_c2) no
cumple; 2 si no se puede comprobar (no hay almacen, no trae las columnas del
reposo ni las de D63, D69 y D71, ninguna hora resuelta trae regimen porque el
almacen es de otra via, o la tabla de escenarios no trae P2P y C2).
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.reposo_mercado import REGIMENES, TOL_FRAGIL_REL  # noqa: E402

# Epsilon de float32: el almacen guarda todo en precision sencilla.
EPS32 = float(np.finfo(np.float32).eps)

# Tolerancias nominales (encargo de la tarea 4b).
TOL_VOLUMEN = 1e-6        # (kWh)
TOL_EXCEDENTE = 0.01      # (COP)
TOL_INGRESO_REL = 1e-9    # relativa
TOL_PRECIO = 1e-6         # (COP/kWh)
TOL_CAPTURA = 1e-6        # adimensional
TOL_COLOCADO = 1e-9       # (kWh): bajo esto un vendedor no coloca nada
# El empate de P2P frente a C2, igual que en compara_matriz_reposo.py: las
# sumas salen de miles de valores float32.
TOL_EMPATE_COP = 1.0      # (COP)
TOL_EMPATE_REL = 1e-6     # relativa

SIN_MERCADO = ("sin_mercado", "sin_ganancia")
MOTIVO_SIN_MERCADO = "sin mercado esa hora"
# Rotulo del resumen para las horas sin vendedores o sin compradores, que no
# llegan al nucleo y no llevan regimen.
SIN_IDS = "(sin ids)"

IDENTIDADES = ("volumen", "excedente", "ingreso", "precios", "vendedores",
               "captura", "finitud", "sin_mercado", "estado", "cero_retiros",
               "prima_descompuesta", "cuantal", "p2p_c2")
# La «hora» con que se anota un fallo del caso entero (p2p_c2).
DEL_CASO = -1

COLUMNAS = {
    "horas": ("hora", "resuelta", "regimen", "presupuesto", "precio_comun",
              "precio_uniforme", "piso_juego", "piso_marginal",
              "n_soluciones", "renta_inframarginal", "parte_juego",
              "excedente_optimo", "excedente_peor", "captura", "excluidos",
              "excluidos_bajo_piso", "vendedores_excluidos",
              "vendedores_no_despachados",
              # D71: la rama cuantal de las horas fragiles.
              "regimen_cerrado", "apartamiento", "mu_cuantal"),
    "flujos": ("hora", "vendedor", "comprador", "kwh", "precio", "valor",
               "precio_reposo", "techo_comprador", "ahorro_comprador",
               "piso_vendedor", "prima_vendedor"),
    "agentes": ("hora", "agente", "papel", "sobrante", "faltante"),
    "escenarios": ("hora", "escenario", "agente", "valor"),
}
NUMERICAS_HORAS = ("presupuesto", "precio_comun", "precio_uniforme",
                   "piso_juego", "piso_marginal", "n_soluciones",
                   "renta_inframarginal", "parte_juego", "excedente_optimo",
                   "excedente_peor", "captura", "apartamiento", "mu_cuantal")
# D71: los regimenes cerrados de una hora «cuantal» del lado de los vendedores
# (con compradores cortos, que es donde ese lado puede ser fragil).
CERRADOS_LADO_VENDEDOR = ("compradores_cortos", "un_comprador")
NUMERICAS_FLUJOS = ("kwh", "precio", "valor", "precio_reposo",
                    "techo_comprador", "ahorro_comprador", "piso_vendedor",
                    "prima_vendedor")

# Cuantos ejemplos por identidad se imprimen en la lista de fallos.
EJEMPLOS = 10


class AlmacenIncompleto(ValueError):
    """El almacen no trae lo que la compuerta necesita para comprobar."""


@dataclass
class Informe:
    caso: str
    fallos: dict = field(default_factory=lambda: {i: [] for i in IDENTIDADES})
    resumen: pd.DataFrame = field(default_factory=pd.DataFrame)
    descuentos: dict = field(default_factory=dict)
    redondeo: dict = field(default_factory=dict)
    avisos: list = field(default_factory=list)
    n_horas: int = 0
    n_resueltas: int = 0
    kwh: float = 0.0
    # P2P frente a C2 (sintesis §6): {institucion: (P2P, C2, coinciden)} de
    # las instituciones con energia P2P mayor que cero.
    p2p_c2: dict = field(default_factory=dict)
    # D67: (vendedores con papel «retirado», horas en que aparecen); debe ser
    # (0, 0).
    retiros: tuple = (0, 0)
    # D69: la prima de los vendedores de las horas resueltas, descompuesta
    # (COP): (renta inframarginal, parte del juego, prima de los flujos).
    prima: tuple = (0.0, 0.0, 0.0)

    # D71: (horas «cuantal», de ellas con n_soluciones != 1, de ellas del lado
    # de los vendedores).
    cuantal: tuple = (0, 0, 0)

    @property
    def verde(self) -> bool:
        return not any(self.fallos.values())


# ─── formato ───────────────────────────────────────────────────────────────


def _num(x: float, dec: int = 2) -> str:
    """Cifra con espacio de miles y coma decimal."""
    if x is None or not np.isfinite(x):
        return "-"
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def _cie(x: float) -> str:
    """Notacion cientifica con coma decimal."""
    if x is None or not np.isfinite(x):
        return "-"
    return f"{x:.2e}".replace(".", ",")


# ─── piezas ────────────────────────────────────────────────────────────────


def _exige(tabla: pd.DataFrame, nombre: str) -> None:
    faltan = [c for c in COLUMNAS[nombre] if c not in tabla.columns]
    if faltan:
        pista = ""
        if nombre == "horas" and "regimen" in faltan:
            pista = (" La tabla de horas no trae el regimen: el almacen no es "
                     "de la via por reposo (--metodo reposo), o es anterior "
                     "a D48.")
        elif nombre == "horas" and "piso_marginal" in faltan:
            pista = (" La tabla de horas no trae el piso marginal ni la prima "
                     "descompuesta: el almacen es anterior a D63 y D69 (el "
                     "piso del juego era el minimo de los que despachan).")
        elif nombre == "horas" and "regimen_cerrado" in faltan:
            pista = (" La tabla de horas no trae la rama cuantal: el almacen "
                     "es anterior a D71 (2026-09-19), de la forma cerrada en "
                     "todas las horas. Para compararlo con uno posterior, "
                     "compara_matriz_reposo.py --por-hora.")
        if nombre == "flujos" and "techo_comprador" in faltan:
            pista = (" El almacen escribe el techo y el piso de cada flujo "
                     "solo con --full o --day.")
        raise AlmacenIncompleto(
            f"la tabla {nombre} no trae las columnas {faltan}.{pista}")


def _a_float(d: pd.DataFrame, columnas) -> pd.DataFrame:
    for c in columnas:
        d[c] = pd.to_numeric(d[c], errors="raise").astype(float)
    return d


def _lista_larga(h: pd.DataFrame, columna: str) -> pd.DataFrame:
    """Una fila (hora, agente) por cada nombre de la lista `columna`, que el
    almacen guarda como texto con los nombres separados por punto y coma."""
    s = h[["hora", columna]].copy()
    s[columna] = s[columna].where(s[columna].notna(), "").astype(str)
    s = s[s[columna] != ""]
    if s.empty:
        return pd.DataFrame({"hora": pd.Series(dtype="int64"),
                             "agente": pd.Series(dtype="object")})
    s = s.assign(agente=s[columna].str.split(";")).explode("agente")
    s = s[s["agente"].astype(str) != ""]
    return s[["hora", "agente"]].reset_index(drop=True)


def _fuera_de_lista(base: pd.DataFrame, lista: pd.DataFrame, valor: str):
    """Separa las filas de `base` (hora, agente, valor) en las que NO estan en
    `lista` y las que si. Devuelve (suma por hora fuera, suma por hora
    dentro, filas de la lista que no casan con ninguna de `base`)."""
    marca = lista.assign(_en_lista=True)
    m = base.merge(marca, on=["hora", "agente"], how="left")
    en = m["_en_lista"].eq(True)
    fuera = m[~en].groupby("hora")[valor].sum()
    dentro = m[en].groupby("hora")[valor].sum()
    cruce = lista.merge(base[["hora", "agente"]], on=["hora", "agente"],
                        how="left", indicator=True)
    huerfanas = cruce[cruce["_merge"] == "left_only"][["hora", "agente"]]
    return fuera, dentro, huerfanas


def _anota(inf: Informe, identidad: str, horas, mensajes) -> None:
    for k, msg in zip(horas, mensajes):
        inf.fallos[identidad].append((int(k), msg))


def _no_finitas(d: pd.DataFrame, columnas) -> pd.Series:
    """Cierto en las filas con algun valor no finito en `columnas`."""
    return pd.Series(~np.isfinite(d[list(columnas)].to_numpy(dtype=float))
                     .all(axis=1), index=d.index)


def _p2p_frente_a_c2(inf: Informe, es: pd.DataFrame,
                     fl: pd.DataFrame) -> None:
    """El beneficio P2P frente al de C2 por institucion (sintesis §6).

    `es` trae ya `valor` en float y sin filas no finitas. Falla (del caso
    entero) si coinciden en TODAS las instituciones con energia P2P mayor que
    cero; si coinciden en algunas, lo avisa. Sin ninguna institucion con
    energia P2P no hay nada que comprobar, y tambien lo avisa."""
    escenarios = set(es["escenario"].astype(str))
    faltan = [e for e in ("P2P", "C2") if e not in escenarios]
    if faltan:
        raise AlmacenIncompleto(
            f"la tabla escenarios no trae {faltan}: no se puede comprobar "
            f"P2P frente a C2")
    suma = es.groupby(["escenario", "agente"])["valor"].sum()
    p2p, c2 = suma.loc["P2P"], suma.loc["C2"]
    energia = (fl.groupby("vendedor")["kwh"].sum()
               .add(fl.groupby("comprador")["kwh"].sum(), fill_value=0.0))
    con = [a for a in p2p.index if float(energia.get(a, 0.0)) > 0.0]
    if not con:
        inf.avisos.append("ninguna institucion con energia P2P: P2P frente a "
                          "C2 no se comprueba")
        return
    for a in con:
        v_p2p = float(p2p.get(a, np.nan))
        v_c2 = float(c2.get(a, np.nan))
        tol = max(TOL_EMPATE_COP,
                  TOL_EMPATE_REL * max(abs(v_p2p), abs(v_c2)))
        inf.p2p_c2[a] = (v_p2p, v_c2, bool(abs(v_p2p - v_c2) <= tol))
    iguales = [a for a, (_, _, c) in inf.p2p_c2.items() if c]
    if len(iguales) == len(con):
        _anota(inf, "p2p_c2", [DEL_CASO],
               [f"P2P y C2 coinciden en las {len(con)} instituciones con "
                f"energia P2P ({', '.join(con)}): es el sintoma del defecto "
                f"viejo, el mercado reducido a C2"])
    elif iguales:
        inf.avisos.append(
            f"P2P y C2 coinciden en {len(iguales)} de las {len(con)} "
            f"instituciones con energia P2P ({', '.join(iguales)}); no falla "
            f"porque no coinciden en todas")


# ─── la compuerta ──────────────────────────────────────────────────────────


def comprueba(horas: pd.DataFrame, flujos: pd.DataFrame,
              agentes: pd.DataFrame, escenarios: pd.DataFrame,
              caso: str = "") -> Informe:
    """Las identidades del reposo, hora a hora, sobre las tablas del almacen,
    y P2P frente a C2 sobre el caso entero.

    Lanza `AlmacenIncompleto` si falta alguna columna, si ninguna hora del
    almacen esta resuelta (no habria nada que comprobar), si el almacen no es
    de la via por reposo (ninguna hora resuelta trae regimen), o si faltan P2P
    o C2 en los escenarios. No imprime nada."""
    for tabla, nombre in ((horas, "horas"), (flujos, "flujos"),
                          (agentes, "agentes"), (escenarios, "escenarios")):
        _exige(tabla, nombre)
    inf = Informe(caso=caso)

    h = horas.copy()
    if "motivo" not in h.columns:
        h["motivo"] = ""
    h["hora"] = h["hora"].astype("int64")
    h["resuelta"] = h["resuelta"].eq(True)
    h["regimen"] = h["regimen"].where(h["regimen"].notna(), "").astype(str)
    h["motivo"] = h["motivo"].where(h["motivo"].notna(), "").astype(str)
    if h["hora"].duplicated().any():
        repetidas = sorted(set(h.loc[h["hora"].duplicated(), "hora"]))
        _anota(inf, "estado", repetidas,
               ["la hora tiene mas de una fila en la tabla de horas"]
               * len(repetidas))
        h = h.drop_duplicates("hora", keep="first")
    h = h.set_index("hora", drop=False).sort_index()

    fl = _a_float(flujos.copy(), NUMERICAS_FLUJOS)
    fl["hora"] = fl["hora"].astype("int64")
    ag = _a_float(agentes.copy(), ("sobrante", "faltante"))
    ag["hora"] = ag["hora"].astype("int64")

    inf.n_horas = int(len(h))
    resueltas = h["resuelta"]
    inf.n_resueltas = int(resueltas.sum())

    # ── de que via es este almacen (revision de la tarea 5a, menor 2) ───
    # Las columnas del reposo se escriben en TODAS las vias, con valores
    # neutros, de modo que su presencia no dice la via. Lo que la dice es el
    # REGIMEN de las horas resueltas: por reposo lo tienen todas, y por las
    # otras vias ninguna. Un almacen acoplado o alternado no se puede
    # comprobar con esta compuerta (todas sus horas fallarian `estado` y
    # `cero_retiros` no querria decir nada): sale con 2 y lo dice.
    #
    # Y si NINGUNA hora esta resuelta, el detector de arriba no puede decir
    # de que via es, y ninguna identidad mira nada: la compuerta saldria
    # verde sin haber comprobado una sola hora, que es lo peor que puede
    # hacer. Sale con 2 y dice que no ha comprobado nada (tarea 5c).
    if not inf.n_resueltas:
        raise AlmacenIncompleto(
            f"ninguna de las {inf.n_horas} horas del almacen esta resuelta: "
            f"no hay nada que comprobar y la compuerta NO HA COMPROBADO NADA. "
            f"Sin horas resueltas tampoco se sabe si el almacen es de la via "
            f"por reposo. Revisa el registro de la corrida ([C-190], [D24] y "
            f"[D38]) antes de leer esto como un caso en verde")
    if not (h.loc[resueltas, "regimen"] != "").any():
        raise AlmacenIncompleto(
            f"ninguna de las {inf.n_resueltas} horas resueltas trae regimen: "
            f"el almacen no es de la via por reposo (--metodo reposo), sino "
            f"de la acoplada o la alternada. Esta compuerta es SOLO para "
            f"almacenes por reposo; para los de las otras vias estan las "
            f"compuertas de la matriz vieja")

    # ── finitud ─────────────────────────────────────────────────────────
    con_regimen = h[h["regimen"] != ""]
    num_h = con_regimen[list(NUMERICAS_HORAS)].apply(
        pd.to_numeric, errors="coerce").astype(float)
    malas = num_h.index[~np.isfinite(num_h.to_numpy()).all(axis=1)]
    _anota(inf, "finitud", malas,
           [f"columnas no finitas en la tabla de horas: "
            f"{[c for c in NUMERICAS_HORAS if not np.isfinite(num_h.loc[k, c])]}"
            for k in malas])
    fin_fl = np.isfinite(fl[list(NUMERICAS_FLUJOS)].to_numpy()).all(axis=1)
    if not fin_fl.all():
        malas = sorted(set(fl.loc[~fin_fl, "hora"]))
        _anota(inf, "finitud", malas,
               ["algun flujo trae un valor no finito"] * len(malas))
    # Revision de 4b, importante 1: el sobrante y el faltante hacen la E, y un
    # NaN los sacaria de la suma sin decir nada.
    malas_ag = _no_finitas(ag, ("sobrante", "faltante"))
    if malas_ag.any():
        malas = sorted(set(ag.loc[malas_ag, "hora"]))
        _anota(inf, "finitud", malas,
               ["algun agente trae el sobrante o el faltante no finito"]
               * len(malas))
    # Y el valor de los escenarios, que decide P2P frente a C2; se comprueba
    # sin sus filas no finitas, que ya fallan aqui.
    es = escenarios.copy()
    es["valor"] = pd.to_numeric(es["valor"], errors="raise").astype(float)
    es["hora"] = es["hora"].astype("int64")
    malas_es = _no_finitas(es, ("valor",))
    if malas_es.any():
        malas = sorted(set(es.loc[malas_es, "hora"]))
        _anota(inf, "finitud", malas,
               ["algun escenario trae un valor no finito"] * len(malas))
    hn = num_h.reindex(h.index)

    # ── estado ──────────────────────────────────────────────────────────
    desconocido = h[(h["regimen"] != "") & ~h["regimen"].isin(REGIMENES)]
    _anota(inf, "estado", desconocido.index,
           [f"regimen desconocido {r!r}" for r in desconocido["regimen"]])
    sin_reg = h[resueltas & (h["regimen"] == "")]
    _anota(inf, "estado", sin_reg.index,
           ["hora resuelta sin regimen: no es de la via por reposo"]
           * len(sin_reg))
    res_sin = h[resueltas & h["regimen"].isin(SIN_MERCADO)]
    _anota(inf, "estado", res_sin.index,
           [f"hora resuelta con regimen {r!r}, que no tiene mercado"
            for r in res_sin["regimen"]])
    no_res = h[~resueltas & (h["motivo"] != MOTIVO_SIN_MERCADO)]
    _anota(inf, "estado", no_res.index,
           [f"hora sin resolver: {m or '(sin motivo)'}"
            for m in no_res["motivo"]])
    tras_retiro = h[~resueltas & (h["regimen"] != "")
                    & ~h["regimen"].isin(SIN_MERCADO)
                    & (h["motivo"] == MOTIVO_SIN_MERCADO)]
    if len(tras_retiro):
        inf.avisos.append(
            f"{len(tras_retiro)} horas con regimen de mercado quedaron sin "
            f"mercado (la participacion retiro a todos, o el conjunto "
            f"reducido no dio mercado); se comprueba que no tengan flujos")

    # ── agregados de los flujos por hora ────────────────────────────────
    fl["_kwh_abs"] = fl["kwh"].abs()
    fl["_banda"] = fl["techo_comprador"] - fl["piso_vendedor"]
    fl["_exc"] = fl["_banda"] * fl["kwh"]
    fl["_exc_cota"] = (fl["kwh"].abs() * (fl["techo_comprador"].abs()
                                          + fl["piso_vendedor"].abs())
                       + fl["_exc"].abs())
    fl["_filas"] = fl["ahorro_comprador"] + fl["prima_vendedor"]
    fl["_filas_cota"] = (fl["ahorro_comprador"].abs()
                         + fl["prima_vendedor"].abs())
    fl["_ing_liq"] = fl["kwh"] * fl["precio"]
    fl["_ing_rep"] = fl["kwh"] * fl["precio_reposo"]
    fl["_ing_cota"] = fl["_ing_liq"].abs() + fl["_ing_rep"].abs()
    fl["_prima"] = (fl["precio"] - fl["piso_vendedor"]) * fl["kwh"]
    fl["_prima_cota"] = fl["kwh"].abs() * (fl["precio"].abs()
                                           + fl["piso_vendedor"].abs())
    por_hora = fl.groupby("hora").agg(
        n_flujos=("kwh", "size"), vol=("kwh", "sum"),
        vol_abs=("_kwh_abs", "sum"),
        exc=("_exc", "sum"), exc_cota=("_exc_cota", "sum"),
        filas=("_filas", "sum"), filas_cota=("_filas_cota", "sum"),
        ing_liq=("_ing_liq", "sum"), ing_rep=("_ing_rep", "sum"),
        ing_cota=("_ing_cota", "sum"), prima=("_prima", "sum"),
        prima_cota=("_prima_cota", "sum"))
    horas_sin_fila = sorted(set(por_hora.index) - set(h.index))
    _anota(inf, "estado", horas_sin_fila,
           ["hay flujos de una hora que no esta en la tabla de horas"]
           * len(horas_sin_fila))
    t = por_hora.reindex(h.index).fillna(0.0)
    t["regimen"] = h["regimen"]
    t["resuelta"] = resueltas

    # ── sin mercado: ninguna hora sin mercado tiene flujos ─────────────
    con_flujos = t[(~t["resuelta"]) & (t["n_flujos"] > 0)]
    _anota(inf, "sin_mercado", con_flujos.index,
           [f"hora sin mercado (regimen {r or SIN_IDS}) con {int(n)} flujos"
            for r, n in zip(con_flujos["regimen"], con_flujos["n_flujos"])])

    # ── volumen ─────────────────────────────────────────────────────────
    vendedores = ag[ag["papel"] == "vendedor"][["hora", "agente", "sobrante"]]
    compradores = ag[ag["papel"] == "comprador"][["hora", "agente",
                                                   "faltante"]]
    retirados = ag[ag["papel"] == "retirado"]
    ve = _lista_larga(h, "vendedores_excluidos")
    vnd = _lista_larga(h, "vendedores_no_despachados")
    ebp = _lista_larga(h, "excluidos_bajo_piso")
    exc_nc = _lista_larga(h, "excluidos")
    # D65: la oferta que cuenta no trae ni a los de D61 ni a los que la
    # caminata deja fuera por su piso. Las dos listas son disjuntas por
    # construccion; se descuentan juntas y se cuentan aparte.
    oferta, _, _ = _fuera_de_lista(
        vendedores, pd.concat([ve, vnd], ignore_index=True), "sobrante")
    _, desc_ve, huerf_ve = _fuera_de_lista(vendedores, ve, "sobrante")
    _, desc_vnd, huerf_vnd = _fuera_de_lista(vendedores, vnd, "sobrante")
    demanda, desc_ebp, huerf_ebp = _fuera_de_lista(compradores, ebp,
                                                   "faltante")
    _, _, huerf_exc = _fuera_de_lista(compradores, exc_nc, "faltante")
    ambas = ve.merge(vnd, on=["hora", "agente"], how="inner")
    _anota(inf, "estado", ambas["hora"],
           [f"{a} esta a la vez en vendedores_excluidos (D61) y en "
            f"vendedores_no_despachados (D65)" for a in ambas["agente"]])
    for huerf, lista, papel in ((huerf_ve, "vendedores_excluidos", "vendedor"),
                                (huerf_vnd, "vendedores_no_despachados",
                                 "vendedor"),
                                (huerf_ebp, "excluidos_bajo_piso",
                                 "comprador"),
                                (huerf_exc, "excluidos", "comprador")):
        _anota(inf, "estado", huerf["hora"],
               [f"la lista {lista} nombra a {a}, que esa hora no es {papel}"
                for a in huerf["agente"]])
    t["oferta"] = oferta.reindex(t.index).fillna(0.0)
    t["demanda"] = demanda.reindex(t.index).fillna(0.0)
    t["E"] = np.minimum(t["oferta"], t["demanda"])
    t["dev_vol"] = (t["vol"] - t["E"]).abs()
    # El redondeo de E es el de su lado corto, no la suma de los dos lados: con
    # uno largo la cota se inflaria y taparia errores (revision de 4b, menor
    # 3). Los dos terminos, con epsilon entero, dan margen sobre el medio
    # epsilon de cada valor.
    t["cota_vol"] = TOL_VOLUMEN + EPS32 * (2.0 * t["E"] + t["vol_abs"])
    chk = t[t["resuelta"]]
    malas = chk[chk["dev_vol"] > chk["cota_vol"]]
    _anota(inf, "volumen", malas.index,
           [f"suma de flujos {_num(v, 6)} (kWh) frente a E = min(oferta "
            f"{_num(o, 6)}, demanda {_num(d, 6)}) = {_num(e, 6)} (kWh); "
            f"dif {_cie(dv)}, cota {_cie(c)}"
            for v, o, d, e, dv, c in zip(malas["vol"], malas["oferta"],
                                         malas["demanda"], malas["E"],
                                         malas["dev_vol"],
                                         malas["cota_vol"])])

    ret_h = retirados.groupby("hora")["sobrante"].sum()
    resueltas_idx = t.index[t["resuelta"]]
    for causa, serie in (("vendedores_excluidos", desc_ve),
                         ("vendedores_no_despachados", desc_vnd),
                         ("retirados", ret_h),
                         ("excluidos_bajo_piso", desc_ebp)):
        s = serie.reindex(resueltas_idx).dropna()
        n_horas = int(s.index.nunique())
        # Una hora que declara a alguien fuera cuenta aunque su cantidad sea
        # cero (un vendedor sin excedente no se retira, pero por si acaso).
        inf.descuentos[causa] = (n_horas, float(s.sum()))

    # ── excedente ───────────────────────────────────────────────────────
    t["optimo"] = hn["excedente_optimo"]
    t["captura"] = hn["captura"]
    t["exc_guardado"] = t["captura"] * t["optimo"]
    t["dev_exc_captura"] = (t["exc_guardado"] - t["exc"]).abs()
    t["cota_exc_captura"] = TOL_EXCEDENTE + EPS32 * (
        2.0 * t["exc_guardado"].abs() + t["exc_cota"])
    t["dev_exc_filas"] = (t["filas"] - t["exc"]).abs()
    t["cota_exc_filas"] = TOL_EXCEDENTE + EPS32 * (t["filas_cota"]
                                                   + t["exc_cota"])
    t["dev_exc"] = np.maximum(t["dev_exc_captura"], t["dev_exc_filas"])
    chk = t[t["resuelta"]]
    malas = chk[(chk["dev_exc_captura"] > chk["cota_exc_captura"])
                | ~np.isfinite(chk["dev_exc_captura"])]
    _anota(inf, "excedente", malas.index,
           [f"captura x optimo = {_num(g, 4)} (COP) frente a "
            f"suma (techo - piso) x P = {_num(e, 4)} (COP); dif {_cie(dv)}, "
            f"cota {_cie(c)}"
            for g, e, dv, c in zip(malas["exc_guardado"], malas["exc"],
                                   malas["dev_exc_captura"],
                                   malas["cota_exc_captura"])])
    malas = chk[chk["dev_exc_filas"] > chk["cota_exc_filas"]]
    _anota(inf, "excedente", malas.index,
           [f"suma de ahorro_comprador + prima_vendedor = {_num(f, 4)} (COP) "
            f"frente a suma (techo - piso) x P = {_num(e, 4)} (COP); dif "
            f"{_cie(dv)}, cota {_cie(c)}"
            for f, e, dv, c in zip(malas["filas"], malas["exc"],
                                   malas["dev_exc_filas"],
                                   malas["cota_exc_filas"])])

    # ── ingreso ─────────────────────────────────────────────────────────
    base = np.maximum(t["ing_rep"].abs(), 1.0)
    t["dev_ing"] = (t["ing_liq"] - t["ing_rep"]).abs() / base
    t["cota_ing"] = TOL_INGRESO_REL + 2.0 * EPS32 * t["ing_cota"] / base
    chk = t[t["resuelta"]]
    malas = chk[chk["dev_ing"] > chk["cota_ing"]]
    _anota(inf, "ingreso", malas.index,
           [f"sum p_liquidado x q = {_num(a, 4)} (COP) frente a "
            f"sum precio_reposo x q = {_num(b, 4)} (COP); dif relativa "
            f"{_cie(dv)}, cota {_cie(c)}"
            for a, b, dv, c in zip(malas["ing_liq"], malas["ing_rep"],
                                   malas["dev_ing"], malas["cota_ing"])])

    # ── precios ─────────────────────────────────────────────────────────
    cb = fl.groupby(["hora", "comprador"]).agg(
        q=("kwh", "sum"), p_min=("precio", "min"), p_max=("precio", "max"),
        r_min=("precio_reposo", "min"), r_max=("precio_reposo", "max"),
        techo=("techo_comprador", "max")).reset_index()
    cb = cb.merge(hn[["piso_juego"]].rename_axis("hora").reset_index(),
                  on="hora", how="left")
    cb = cb.merge(t[["resuelta"]].rename_axis("hora").reset_index(),
                  on="hora", how="left")
    servidos = cb[(cb["q"] > 0.0) & cb["resuelta"].eq(True)].copy()
    lo, hi = servidos["piso_juego"], servidos["techo"]
    escala = np.maximum.reduce([servidos["p_max"].abs(),
                                servidos["r_max"].abs(), lo.abs(), hi.abs()])
    servidos["cota"] = TOL_PRECIO + 2.0 * EPS32 * escala
    servidos["exceso"] = np.maximum.reduce([
        lo - servidos["p_min"], servidos["p_max"] - hi,
        lo - servidos["r_min"], servidos["r_max"] - hi,
        np.zeros(len(servidos))])
    malas = servidos[servidos["exceso"] > servidos["cota"]]
    _anota(inf, "precios", malas["hora"],
           [f"{c}: liquidado [{_num(a, 4)}; {_num(b, 4)}] y del reposo "
            f"[{_num(r1, 4)}; {_num(r2, 4)}] frente a [piso del juego "
            f"{_num(p, 4)}; techo {_num(te, 4)}] (COP/kWh)"
            for c, a, b, r1, r2, p, te in zip(
                malas["comprador"], malas["p_min"], malas["p_max"],
                malas["r_min"], malas["r_max"], malas["piso_juego"],
                malas["techo"])])
    t["exceso_precio"] = (servidos.groupby("hora")["exceso"].max()
                          .reindex(t.index).fillna(0.0))
    techo_hora = servidos.groupby("hora")["techo"].max().reindex(t.index)
    for columna, nombre in (("precio_uniforme", "uniforme"),
                            ("precio_comun", "comun")):
        p = hn[columna]
        piso = hn["piso_juego"]
        cota = TOL_PRECIO + 2.0 * EPS32 * np.maximum(p.abs(),
                                                     techo_hora.abs())
        exceso = np.maximum.reduce([piso - p, p - techo_hora,
                                    pd.Series(0.0, index=t.index)])
        ok = t["resuelta"] & techo_hora.notna()
        t["exceso_precio"] = np.where(ok, np.maximum(t["exceso_precio"],
                                                     exceso),
                                      t["exceso_precio"])
        malas = t[ok & (exceso > cota)]
        _anota(inf, "precios", malas.index,
               [f"precio {nombre} de la hora {_num(p.loc[k], 4)} fuera de "
                f"[piso del juego {_num(piso.loc[k], 4)}; techo mayor "
                f"{_num(techo_hora.loc[k], 4)}] (COP/kWh)"
                for k in malas.index])

    # ── vendedores ──────────────────────────────────────────────────────
    # El piso con que se compara a cada vendedor es EL SUYO, el
    # `piso_vendedor` de sus flujos, y no el piso del juego de la tabla de
    # horas: es el teorema de cobertura de D63. Con el piso del juego, un
    # vendedor de piso mayor que cobrara entre los dos pasaria sin verse.
    cv = fl.groupby(["hora", "vendedor"]).agg(
        colocado=("kwh", "sum"), ingreso=("_ing_liq", "sum"),
        piso=("piso_vendedor", "max")).reset_index()
    cv = cv.merge(t[["resuelta"]].rename_axis("hora").reset_index(),
                  on="hora", how="left")
    desp = cv[(cv["colocado"] > TOL_COLOCADO) & cv["resuelta"].eq(True)].copy()
    desp["medio"] = desp["ingreso"] / desp["colocado"]
    desp["exceso"] = desp["piso"] - desp["medio"]
    desp["cota"] = TOL_COLOCADO + 2.0 * EPS32 * (desp["medio"].abs()
                                                  + desp["piso"].abs())
    malas = desp[desp["exceso"] > desp["cota"]]
    _anota(inf, "vendedores", malas["hora"],
           [f"{v} coloca {_num(c, 6)} (kWh) a {_num(m, 4)} (COP/kWh) de "
            f"media, bajo su piso {_num(p, 4)} (COP/kWh)"
            for v, c, m, p in zip(malas["vendedor"], malas["colocado"],
                                  malas["medio"], malas["piso"])])
    t["exceso_vendedor"] = (desp.groupby("hora")["exceso"].max()
                            .clip(lower=0.0).reindex(t.index).fillna(0.0))
    t["cota_parte"] = 2.0 * EPS32 * t["prima_cota"] + TOL_COLOCADO
    # El + 0.0 quita el cero negativo que deja el recorte.
    t["exceso_parte"] = (-t["prima"]).clip(lower=0.0) + 0.0
    chk = t[t["resuelta"]]
    malas = chk[chk["exceso_parte"] > chk["cota_parte"]]
    _anota(inf, "vendedores", malas.index,
           [f"parte de los vendedores negativa: sum (precio - piso) x P = "
            f"{_num(-e, 4)} (COP)" for e in malas["exceso_parte"]])

    # ── cero retiros (D67) ──────────────────────────────────────────────
    # En toda hora, resuelta o no: la participacion que retira a todos deja
    # la hora sin mercado, y tambien es un hallazgo.
    if len(retirados):
        por_hora_ret = retirados.groupby("hora")["agente"].apply(
            lambda a: ", ".join(sorted(map(str, a))))
        _anota(inf, "cero_retiros", por_hora_ret.index,
               [f"la participacion retiro a {n} (papel «retirado»): con el "
                f"piso del vendedor marginal todo despachado cobra al menos "
                f"su piso y no deberia retirarse nadie (D67)"
                for n in por_hora_ret])
    inf.retiros = (int(len(retirados)), int(retirados["hora"].nunique()))

    # ── prima descompuesta (D69) ────────────────────────────────────────
    t["renta"] = hn["renta_inframarginal"]
    t["parte_juego"] = hn["parte_juego"]
    t["dev_prima"] = (t["renta"] + t["parte_juego"] - t["prima"]).abs()
    t["cota_prima"] = TOL_EXCEDENTE + 2.0 * EPS32 * (
        t["prima_cota"] + t["renta"].abs() + t["parte_juego"].abs())
    chk = t[t["resuelta"] & ~t["regimen"].isin(SIN_MERCADO)
            & (t["regimen"] != "")]
    malas = chk[(chk["dev_prima"] > chk["cota_prima"])
                | ~np.isfinite(chk["dev_prima"])]
    _anota(inf, "prima_descompuesta", malas.index,
           [f"renta inframarginal {_num(r, 4)} + parte del juego "
            f"{_num(j, 4)} (COP) frente a la prima de los flujos, sum "
            f"(precio - piso_vendedor) x kwh = {_num(p, 4)} (COP); dif "
            f"{_cie(dv)}, cota {_cie(c)}"
            for r, j, p, dv, c in zip(malas["renta"], malas["parte_juego"],
                                      malas["prima"], malas["dev_prima"],
                                      malas["cota_prima"])])
    inf.prima = (float(chk["renta"].sum()), float(chk["parte_juego"].sum()),
                 float(chk["prima"].sum()))

    # ── la rama cuantal (D71) ───────────────────────────────────────────
    # El apartamiento se guarda en float32: la frontera de 1e-3 se juzga con
    # dos epsilon de holgura, para no fallar por el redondeo del almacen.
    cr = h.loc[h["regimen"] != "", ["regimen", "regimen_cerrado"]].copy()
    cr["regimen_cerrado"] = cr["regimen_cerrado"].where(
        cr["regimen_cerrado"].notna(), "").astype(str)
    cr["apart"] = hn.loc[cr.index, "apartamiento"]
    cr["mu"] = hn.loc[cr.index, "mu_cuantal"]
    cr["n_sol"] = hn.loc[cr.index, "n_soluciones"]
    es_c = cr["regimen"] == "cuantal"
    alto = cr["apart"] > TOL_FRAGIL_REL * (1.0 + 2.0 * EPS32)
    bajo = cr["apart"] <= TOL_FRAGIL_REL * (1.0 - 2.0 * EPS32)
    de_mercado = set(REGIMENES) - {"cuantal"} - set(SIN_MERCADO)
    for k in cr.index[es_c & bajo]:
        _anota(inf, "cuantal", [k], [
            f"hora «cuantal» con apartamiento {_cie(cr.loc[k, 'apart'])}·E, "
            f"que no pasa de {TOL_FRAGIL_REL:g}"])
    for k in cr.index[~es_c & alto]:
        _anota(inf, "cuantal", [k], [
            f"hora «{cr.loc[k, 'regimen']}» con apartamiento "
            f"{_cie(cr.loc[k, 'apart'])}·E, sobre {TOL_FRAGIL_REL:g}: tendria "
            f"que ser «cuantal»"])
    for k in cr.index[es_c & ~cr["regimen_cerrado"].isin(de_mercado)]:
        _anota(inf, "cuantal", [k], [
            f"hora «cuantal» con regimen cerrado "
            f"{cr.loc[k, 'regimen_cerrado']!r}, que no es de mercado"])
    for k in cr.index[es_c & ~(cr["mu"] > 0.0)]:
        _anota(inf, "cuantal", [k], [
            f"hora «cuantal» con mu_cuantal {cr.loc[k, 'mu']}: con la rama "
            f"apagada no hay horas cuantales"])
    for k in cr.index[~es_c & (cr["regimen_cerrado"] != cr["regimen"])]:
        _anota(inf, "cuantal", [k], [
            f"hora «{cr.loc[k, 'regimen']}» con regimen cerrado "
            f"{cr.loc[k, 'regimen_cerrado']!r}: fuera de «cuantal» son el "
            f"mismo"])
    otra_sol = es_c & (cr["n_sol"] != 1)
    lado_v = es_c & cr["regimen_cerrado"].isin(CERRADOS_LADO_VENDEDOR)
    n_c, n_sol, n_vend = int(es_c.sum()), int(otra_sol.sum()), \
        int(lado_v.sum())
    inf.cuantal = (n_c, n_sol, n_vend)
    if n_sol:
        inf.avisos.append(
            f"{n_sol} de las {n_c} horas «cuantal» tienen n_soluciones "
            f"distinto de 1 (D71, sec. 8.3: esperado 0): "
            f"{[int(k) for k in cr.index[otra_sol][:10]]}")
    if n_vend:
        inf.avisos.append(
            f"{n_vend} horas «cuantal» del lado de los vendedores (D71, sec. "
            f"8.2): medir M-D con el costo del vendedor en su piso antes de "
            f"publicar: {[int(k) for k in cr.index[lado_v][:10]]}")

    # ── captura ─────────────────────────────────────────────────────────
    chk = t[t["resuelta"] & (t["optimo"] > 0.0)]
    t["exceso_captura"] = 0.0
    exceso = np.maximum(-chk["captura"], chk["captura"] - 1.0).clip(lower=0.0)
    t.loc[chk.index, "exceso_captura"] = exceso
    malas = chk[exceso > TOL_CAPTURA]
    _anota(inf, "captura", malas.index,
           [f"captura {_num(c, 6)} fuera de [0, 1] con optimo "
            f"{_num(o, 4)} (COP)"
            for c, o in zip(malas["captura"], malas["optimo"])])

    # ── redondeo: sobre la nominal pero dentro de la cota float32 ──────
    chk = t[t["resuelta"]]
    inf.redondeo = {
        "volumen": int(((chk["dev_vol"] > TOL_VOLUMEN)
                        & (chk["dev_vol"] <= chk["cota_vol"])).sum()),
        "excedente": int(((chk["dev_exc"] > TOL_EXCEDENTE)
                          & (chk["dev_exc_captura"]
                             <= chk["cota_exc_captura"])
                          & (chk["dev_exc_filas"]
                             <= chk["cota_exc_filas"])).sum()),
        "ingreso": int(((chk["dev_ing"] > TOL_INGRESO_REL)
                        & (chk["dev_ing"] <= chk["cota_ing"])).sum()),
    }

    # ── resumen por regimen ─────────────────────────────────────────────
    t["grupo"] = t["regimen"].where(t["regimen"] != "", SIN_IDS)
    filas = []
    for g in list(REGIMENES) + [SIN_IDS]:
        sub = t[t["grupo"] == g]
        res = sub[sub["resuelta"]]
        hay = len(res) > 0
        filas.append(dict(
            regimen=g, horas=int(len(sub)), resueltas=int(len(res)),
            kwh=float(res["vol"].sum()),
            volumen=float(res["dev_vol"].max()) if hay else np.nan,
            excedente=float(res["dev_exc"].max()) if hay else np.nan,
            ingreso=float(res["dev_ing"].max()) if hay else np.nan,
            precios=float(res["exceso_precio"].max()) if hay else np.nan,
            vendedores=float(res["exceso_vendedor"].max()) if hay else np.nan,
            parte=float(res["exceso_parte"].max()) if hay else np.nan,
            captura=float(res["exceso_captura"].max()) if hay else np.nan,
            prima=float(res["dev_prima"].max()) if hay else np.nan))
    inf.resumen = pd.DataFrame(filas)
    inf.kwh = float(t.loc[t["resuelta"], "vol"].sum())

    # ── P2P frente a C2, del caso entero ────────────────────────────────
    _p2p_frente_a_c2(inf, es[~malas_es], fl)

    for identidad in IDENTIDADES:
        inf.fallos[identidad].sort(key=lambda par: par[0])
    return inf


# ─── salida ────────────────────────────────────────────────────────────────


def imprime(inf: Informe) -> None:
    caso = inf.caso or "(sin nombre)"
    print("=" * 78)
    print(f"  COMPUERTA DE SALIDA DE LA MATRIZ CON EL REPOSO - caso {caso}")
    print("=" * 78)
    print(f"  horas del almacen {inf.n_horas}; resueltas (con mercado) "
          f"{inf.n_resueltas}; energia transada {_num(inf.kwh)} (kWh)")
    print()
    print("  Resumen por regimen. Las desviaciones son las peores de las horas")
    print("  resueltas: volumen |suma de flujos - E| (kWh); excedente (COP);")
    print("  ingreso relativo; y, en las desigualdades, lo que se sale de su")
    print("  cota: precios (COP/kWh), vendedores bajo su piso (COP/kWh), parte")
    print("  negativa (COP) y captura fuera de [0, 1]; prima |renta + parte")
    print("  del juego - prima| (COP, D69). Cero es dentro.")
    print(f"  {SIN_IDS}: horas sin vendedores o sin compradores, que no llegan")
    print("  al nucleo y no llevan regimen.")
    cab = (f"  {'regimen':<22}{'horas':>6}{'kWh':>14}{'volumen':>10}"
           f"{'excedente':>10}{'ingreso':>10}{'precios':>10}"
           f"{'vendedor':>10}{'parte':>10}{'captura':>10}{'prima':>10}")
    print(cab)
    print("  " + "-" * (len(cab) - 2))
    for _, r in inf.resumen.iterrows():
        print(f"  {r['regimen']:<22}{r['horas']:>6}{_num(r['kwh']):>14}"
              f"{_cie(r['volumen']):>10}{_cie(r['excedente']):>10}"
              f"{_cie(r['ingreso']):>10}{_cie(r['precios']):>10}"
              f"{_cie(r['vendedores']):>10}{_cie(r['parte']):>10}"
              f"{_cie(r['captura']):>10}{_cie(r['prima']):>10}")
    print()
    print(f"  Retiros de la participacion (D67, deben ser 0): "
          f"{inf.retiros[0]} vendedores en {inf.retiros[1]} horas")
    print(f"  Horas «cuantal» (D71): {inf.cuantal[0]}; con n_soluciones "
          f"distinto de 1: {inf.cuantal[1]} (esperado 0); del lado de los "
          f"vendedores: {inf.cuantal[2]}")
    renta, juego, prima = inf.prima
    print(f"  Prima de los vendedores de las horas resueltas (D69): renta "
          f"inframarginal {_num(renta)} (COP) + parte del juego "
          f"{_num(juego)} (COP) = {_num(renta + juego)} (COP); de los flujos, "
          f"{_num(prima)} (COP)")
    print()
    print("  Lo que se descuenta de la oferta o de la demanda, por causa")
    print("  (horas resueltas que lo declaran, y energia):")
    for causa, (n, e) in inf.descuentos.items():
        lado = "demanda" if causa == "excluidos_bajo_piso" else "oferta"
        print(f"    {causa:<26} {n:>5} h   {_num(e):>12} (kWh) de {lado}")
    print()
    print("  Horas sobre la tolerancia nominal pero dentro de la cota del")
    print("  redondeo float32 del almacen (volumen 1e-6 (kWh), excedente")
    print("  0,01 (COP), ingreso 1e-9 relativo):")
    for identidad, n in inf.redondeo.items():
        print(f"    {identidad:<10} {n} h")
    print()
    print("  P2P frente a C2 por institucion con energia P2P (COP; «=» si")
    print("  coinciden dentro de max(1 (COP), 1e-6 del mayor)):")
    for a, (v_p2p, v_c2, igual) in inf.p2p_c2.items():
        print(f"    {a:<10} P2P {_num(v_p2p, 0):>16}  C2 {_num(v_c2, 0):>16}"
              f"  {'=' if igual else 'distintos'}")
    for aviso in inf.avisos:
        print(f"  AVISO: {aviso}")
    print()
    if inf.verde:
        print(f"COMPUERTA MATRIZ REPOSO {caso} EN VERDE")
        return
    n_ident = sum(1 for v in inf.fallos.values() if v)
    print(f"COMPUERTA MATRIZ REPOSO {caso} FALLA en {n_ident} "
          f"identidad(es); lista de fallos:")
    for identidad in IDENTIDADES:
        lista = inf.fallos[identidad]
        if not lista:
            continue
        horas = sorted({k for k, _ in lista if k != DEL_CASO})
        print(f"  {identidad}: {len(lista)} fallo(s) en {len(horas)} hora(s)")
        for k, msg in lista[:EJEMPLOS]:
            donde = "caso" if k == DEL_CASO else f"hora {k}"
            print(f"    {donde}: {msg}")
        if len(lista) > EJEMPLOS:
            print(f"    ... y {len(lista) - EJEMPLOS} mas")


def carga(almacen, cobertura: str) -> dict:
    """Las cuatro tablas del almacen. Sin flujos (ninguna hora con mercado) la
    tabla sale vacia, y la compuerta falla si alguna hora resolvio. Sin horas,
    agentes o escenarios, FileNotFoundError."""
    from core.almacen import lee

    tablas = {"horas": lee(almacen, cobertura, "horas"),
              "agentes": lee(almacen, cobertura, "agentes"),
              "escenarios": lee(almacen, cobertura, "escenarios")}
    try:
        tablas["flujos"] = lee(almacen, cobertura, "flujos")
    except FileNotFoundError:
        print("  AVISO: el almacen no tiene flujos; ninguna hora deberia "
              "haber resuelto")
        tablas["flujos"] = pd.DataFrame({c: pd.Series(dtype="float64")
                                         for c in COLUMNAS["flujos"]})
    return tablas


def nombre_caso(almacen) -> str:
    """`SALIDAS_SERVIDOR/matriz_reposo/E0/almacen` -> E0."""
    p = Path(almacen)
    return p.parent.name if p.name == "almacen" else p.name


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Compuerta de salida de la matriz con el reposo (D48).")
    ap.add_argument("almacen", help="carpeta del almacen de la corrida")
    ap.add_argument("--cobertura", default="m1")
    ap.add_argument("--caso", default=None,
                    help="nombre del caso para la linea final; por defecto, "
                         "la carpeta que contiene al almacen")
    a = ap.parse_args(argv)
    # CAL-28b: una consola cp1252 revienta con un caracter fuera de su tabla.
    if (hasattr(sys.stdout, "reconfigure")
            and str(getattr(sys.stdout, "encoding", "")).lower() != "utf-8"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    caso = a.caso or nombre_caso(a.almacen)
    try:
        tablas = carga(a.almacen, a.cobertura)
    except FileNotFoundError as e:
        print(f"COMPUERTA MATRIZ REPOSO {caso}: NO SE PUEDE COMPROBAR: {e}")
        return 2
    try:
        inf = comprueba(tablas["horas"], tablas["flujos"], tablas["agentes"],
                        tablas["escenarios"], caso=caso)
    except AlmacenIncompleto as e:
        print(f"COMPUERTA MATRIZ REPOSO {caso}: NO SE PUEDE COMPROBAR: {e}")
        return 2
    imprime(inf)
    return 0 if inf.verde else 1


if __name__ == "__main__":
    sys.exit(main())
