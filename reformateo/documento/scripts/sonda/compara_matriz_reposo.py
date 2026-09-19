"""
La matriz vieja (acoplado, 2026-09-15) frente a la nueva (reposo, D48): la
tabla de M-F, por caso y por institucion. 2026-09-17.

QUE COMPARA. Para cada caso de la matriz y, dentro de el, para la comunidad y
cada institucion:

  energia transada   (kWh) suma de los flujos; por institucion, lo que vende
                     mas lo que compra (en una hora cada una juega un papel)
  precio medio       (COP/kWh) ponderado por energia: suma de `valor` sobre
                     suma de `kwh` de los flujos en que participa
  parte del vendedor sum prima_vendedor / sum (ahorro_comprador +
                     prima_vendedor); por institucion, la de sus ventas (vacia
                     si no vendio nunca)
  beneficio P2P      (COP) la tabla `escenarios`, escenario «P2P», sumada
  el orden P2P       P2P - C_k para cada escenario regulatorio que la corrida
  frente a C_k       escribio (C1, C2, C3, C4, C4_mensual, C5), y P2P colectivo
                     - C4 (y - C4_mensual), con una columna que marca si el
                     signo cambio de la vieja a la nueva

y, SOLO DE LA NUEVA, porque solo la via por reposo escribe lo que hace falta:

  al techo, al piso  (kWh) energia de los compradores servidos liquidada a su
                     techo o al piso del juego (si coinciden, cuenta al techo),
                     con la misma regla y la misma tolerancia que la linea
                     [D48] del motor (`resumen_reposo` de main_simulation.py):
                     |precio - techo| <= 1e-6 (COP/kWh), absoluta. En el
                     almacen, un precio que el motor dejo igual al techo o al
                     piso sale del mismo doble y queda igual en float32.
                     ESA TOLERANCIA EQUIVALE A IGUALDAD EXACTA en el almacen:
                     1e-6 (COP/kWh) esta muy por debajo de la resolucion de
                     float32, que entre 512 y 1 024 es de unos 6,1e-5
                     (COP/kWh), es decir sesenta veces mayor. En ese rango, el
                     de los precios de esta tesis, dos valores float32
                     distintos no pueden caer dentro de la tolerancia: solo
                     caen los que son el mismo valor. Con precios mucho mas
                     pequenos el paso de float32 encoge y la tolerancia
                     volveria a aflojar, pero aqui no ocurre. La tolerancia
                     esta para que la regla coincida con la de la linea [D48],
                     no para absorber redondeo
  excluida           (kWh) deficit de los compradores en `excluidos` (en su
                     techo sin energia, «no cabe») y, aparte, en
                     `excluidos_bajo_piso` (D61 parcial)
  un comprador       (kWh) energia de las horas de un solo comprador (D54);
                     por institucion, la que transo en esas horas
  captura            media simple de `captura` en las horas con mercado y
                     optimo positivo, y la agregada, sum captura x optimo /
                     sum optimo (D55); solo de la comunidad

DE DONDE SALEN LOS ESCENARIOS. No se recalculan: se leen de la tabla
`escenarios` del almacen de cada corrida, una fila por hora, escenario y
agente, que es la que `liquidacion.py` suma en `por_mecanismo` y la que la
compuerta C-165 (`tests/gate_c165_desglose_horario.py`) prueba que suma
exactamente el total del motor. Es la misma cifra que la hoja `Por_agente` de
`outputs/resultados_comparacion.xlsx`, pero con el nombre de cada institucion
en vez de A1 a A5.

EL EMPATE. Las sumas salen de miles de valores float32 del almacen, con un
redondeo del orden de 1e-7 relativo por valor. Una diferencia P2P - C_k cuyo
valor absoluto no pasa de max(--tol-cop, --tol-rel x el mayor de los dos
beneficios) se lee como empate, signo 0, y pasar de empate a un signo tambien
cuenta como cambio. Por defecto, 1 (COP) y 1e-6.

La vieja contra si misma da diferencias cero y ningun cambio de signo: es la
prueba local de solo lectura con E0 de la entrega del 2026-09-15.

`metricas` y `compara` son puras: reciben DataFrames y no leen parquet, de modo
que se prueban sin pyarrow. `carga` lee con `core.almacen.lee`.

Uso, desde la raiz del repositorio:
    python -u reformateo/documento/scripts/sonda/compara_matriz_reposo.py \
        --vieja SALIDAS_SERVIDOR/matriz --nueva SALIDAS_SERVIDOR/matriz_reposo \
        --salida SALIDAS_SERVIDOR/matriz_reposo/compara_matriz_reposo.csv

Cada raiz tiene una carpeta por caso con su `almacen` dentro. `--casos` acota
la lista (por defecto, los que tienen almacen en las dos raices; sin sufijo, las
carpetas del barrido, `<caso>_sigma*`, y `figuras_foro` no son candidatas).
Para el barrido de sigma, `--sufijo-nueva _sigma05` compara la carpeta
`<caso>_sigma05` de la nueva con la `<caso>` de la vieja; con la misma raiz en
las dos, compara el barrido contra la sigma base.

EN CASA. La recogida del servidor se desempaqueta en una carpeta de entrega,
de modo que `--nueva` es la `SALIDAS_SERVIDOR/matriz_reposo` que sale del tar,
y `--vieja`, la de la entrega de la matriz del 15 de septiembre:
    python -u reformateo/documento/scripts/sonda/compara_matriz_reposo.py \
        --vieja SALIDAS_SERVIDOR/entrega_matriz_2026-09-15/SALIDAS_SERVIDOR/matriz \
        --nueva SALIDAS_SERVIDOR/entrega_<nombre>/SALIDAS_SERVIDOR/matriz_reposo \
        --salida SALIDAS_SERVIDOR/entrega_<nombre>/compara_matriz_reposo.csv

NO FINITOS. Una suma de pandas se salta los NaN en silencio, y un NaN en la
tabla de escenarios cambiaria P2P - C_k y su signo sin que nada lo dijera. Por
eso, antes de medir, se exige que sean finitos `kwh`, `valor`, `precio`,
`ahorro_comprador`, `prima_vendedor` y `techo_comprador` de los flujos, el
`faltante` de los agentes, el `valor` de los escenarios y, en las horas con
regimen, `captura` y `excedente_optimo`. Si no, sale con 2 y dice donde.

HORA A HORA (D71, `--por-hora`). La rama cuantal del reposo cambia el reparto
de las horas fragiles y de ninguna mas: frente a la matriz del 17 (la forma
cerrada), la nueva tiene que diferir exactamente en las 216 horas del censo de
M-E y ser identica AL BIT (float32 del almacen) en las demas. `horas_distintas`
lo mide hora a hora, en dos pasos:
  1. las ENTRADAS de la hora (sobrante, faltante, techo y piso de cada agente,
     tabla `agentes`): una hora con alguna entrada distinta no es comparable
     por D71 (por ejemplo, las que cambio la cache nueva de bolsa, H-92, en
     los casos con pisos de bolsa) y se cuenta aparte;
  2. en las horas con las mismas entradas, el MERCADO: el regimen de la tabla
     de horas y lo que transa cada pareja (vendedor, comprador) de `flujos`.
Con `--tol-kwh 0` (defecto) la igualdad es al bit. Imprime, por caso, las
horas con entradas distintas, las del mercado distinto (con la energia que
cambia de manos, sum ½·sum_i |q nueva - q vieja|, y los regimenes de las dos),
y escribe la lista en `<salida sin .csv>_horas.csv`.

Es una MEDICION: sale con 0 si compara al menos un caso. Sale con 2 si un caso
pedido con `--casos` no tiene almacen en alguna de las dos raices, si no hay
ningun caso que comparar o si algun almacen trae valores no finitos.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# La tolerancia de «al techo» y «al piso» de la linea [D48] del motor
# (`resumen_reposo(tol_precio=1e-6)` en main_simulation.py), absoluta.
TOL_PRECIO_D48 = 1e-6     # (COP/kWh)

COMUNIDAD = "comunidad"
# Las que se comparan vieja frente a nueva.
COMUNES = ("kwh_transada", "precio_medio", "parte_vendedor", "beneficio_P2P")
# Las que solo escribe la via por reposo.
SOLO_NUEVA = ("kwh_al_techo", "kwh_al_piso", "kwh_excluida",
              "kwh_excluida_bajo_piso", "kwh_un_comprador", "captura_media",
              "captura_agregada")
ESCENARIOS_P2P = ("C1", "C2", "C3", "C4", "C4_mensual", "C5")
ESCENARIOS_COLECTIVO = ("C4", "C4_mensual")


class DatosNoFinitos(ValueError):
    """Un almacen trae valores no finitos en lo que la comparacion suma."""


# ─── carga ─────────────────────────────────────────────────────────────────


def carpeta(raiz, caso: str, sufijo: str = "") -> Path:
    return Path(raiz) / f"{caso}{sufijo}" / "almacen"


def carga(raiz, caso: str, cobertura: str = "m1", sufijo: str = "") -> dict:
    """Las cuatro tablas del almacen de un caso."""
    from core.almacen import lee

    alm = carpeta(raiz, caso, sufijo)
    return {t: lee(alm, cobertura, t)
            for t in ("horas", "flujos", "agentes", "escenarios")}


# ─── metricas de una corrida ───────────────────────────────────────────────


def _nombres_largos(h: pd.DataFrame, columna: str) -> pd.DataFrame:
    s = h[["hora", columna]].copy()
    s[columna] = s[columna].where(s[columna].notna(), "").astype(str)
    s = s[s[columna] != ""]
    if s.empty:
        return pd.DataFrame({"hora": pd.Series(dtype="int64"),
                             "agente": pd.Series(dtype="object")})
    s = s.assign(agente=s[columna].str.split(";")).explode("agente")
    return s[s["agente"].astype(str) != ""][["hora", "agente"]]


def _exige_finito(tabla: str, d: pd.DataFrame, columnas) -> None:
    """DatosNoFinitos si alguna fila de `d` trae un no finito en `columnas`.

    Una suma de pandas se salta los NaN: sin esto, un NaN cambiaria una cifra
    y su signo sin que nada lo dijera (revision de 4b, importante 1)."""
    columnas = [c for c in columnas if c in d.columns]
    if not columnas or d.empty:
        return
    valores = d[columnas].apply(pd.to_numeric, errors="raise").to_numpy(
        dtype=float)
    malas = ~np.isfinite(valores).all(axis=1)
    if malas.any():
        cuales = [c for k, c in enumerate(columnas)
                  if not np.isfinite(valores[:, k]).all()]
        horas = (sorted(set(d.loc[malas, "hora"]))[:5]
                 if "hora" in d.columns else [])
        raise DatosNoFinitos(
            f"la tabla {tabla} trae {int(malas.sum())} fila(s) con valores no "
            f"finitos en {cuales} (primeras horas: {horas})")


def metricas(tablas: dict, tol_precio: float = TOL_PRECIO_D48):
    """Las metricas de una corrida, por institucion y para la comunidad.

    Devuelve (DataFrame indexado por institucion, con la fila «comunidad»
    primero; diccionario escenario -> Serie de beneficio por institucion;
    lista de avisos). Lanza DatosNoFinitos si lo que suma no es finito."""
    h = tablas["horas"].copy()
    fl = tablas["flujos"].copy()
    ag = tablas["agentes"]
    es = tablas["escenarios"]
    avisos = []
    _exige_finito("flujos", fl, ("kwh", "valor", "precio", "ahorro_comprador",
                                 "prima_vendedor", "techo_comprador"))
    _exige_finito("agentes", ag, ("faltante",))
    _exige_finito("escenarios", es, ("valor",))
    if "regimen" in h.columns:
        con_regimen = h["regimen"].where(h["regimen"].notna(), "") != ""
        _exige_finito("horas", h[con_regimen],
                      ("captura", "excedente_optimo"))
    for c in ("kwh", "valor", "precio", "ahorro_comprador", "prima_vendedor"):
        fl[c] = pd.to_numeric(fl[c], errors="raise").astype(float)

    instituciones = list(dict.fromkeys(ag["agente"]))
    filas = pd.DataFrame(index=[COMUNIDAD] + instituciones,
                         columns=list(COMUNES) + list(SOLO_NUEVA),
                         dtype=float)

    # Lo comun a las dos vias.
    filas.loc[COMUNIDAD, "kwh_transada"] = fl["kwh"].sum()
    filas.loc[COMUNIDAD, "precio_medio"] = (
        fl["valor"].sum() / fl["kwh"].sum() if fl["kwh"].sum() > 0 else np.nan)
    excedente = (fl["ahorro_comprador"] + fl["prima_vendedor"]).sum()
    filas.loc[COMUNIDAD, "parte_vendedor"] = (
        fl["prima_vendedor"].sum() / excedente if excedente > 0 else np.nan)
    for n in instituciones:
        suyo = fl[(fl["vendedor"] == n) | (fl["comprador"] == n)]
        vende = fl[fl["vendedor"] == n]
        kwh = suyo["kwh"].sum()
        filas.loc[n, "kwh_transada"] = kwh
        filas.loc[n, "precio_medio"] = (suyo["valor"].sum() / kwh
                                        if kwh > 0 else np.nan)
        exc_v = (vende["ahorro_comprador"] + vende["prima_vendedor"]).sum()
        filas.loc[n, "parte_vendedor"] = (vende["prima_vendedor"].sum() / exc_v
                                          if exc_v > 0 else np.nan)

    beneficio = (es.assign(valor=pd.to_numeric(es["valor"]).astype(float))
                   .groupby(["escenario", "agente"])["valor"].sum())
    por_escenario = {}
    for e in beneficio.index.get_level_values(0).unique():
        serie = beneficio.loc[e].reindex(instituciones).astype(float)
        serie.loc[COMUNIDAD] = float(serie.sum())
        por_escenario[str(e)] = serie
    if "P2P" in por_escenario:
        filas["beneficio_P2P"] = por_escenario["P2P"].reindex(filas.index)
    else:
        avisos.append("la tabla de escenarios no trae «P2P»")

    # Lo que solo escribe la via por reposo.
    columnas_reposo = {"regimen", "piso_juego", "excluidos",
                       "excluidos_bajo_piso", "captura", "excedente_optimo"}
    faltan = sorted(columnas_reposo - set(h.columns))
    if faltan or "techo_comprador" not in fl.columns:
        avisos.append(f"NO MEDIDO: el almacen no trae las columnas del reposo "
                      f"{faltan or ['techo_comprador']}; las metricas solo "
                      f"de la nueva quedan vacias")
        return filas, por_escenario, avisos

    h["regimen"] = h["regimen"].where(h["regimen"].notna(), "").astype(str)
    h["resuelta"] = h["resuelta"].eq(True)
    fl["techo_comprador"] = fl["techo_comprador"].astype(float)
    cb = fl.groupby(["hora", "comprador"]).agg(
        q=("kwh", "sum"), precio=("precio", "max"),
        techo=("techo_comprador", "max")).reset_index()
    cb = cb.merge(h[["hora", "piso_juego"]], on="hora", how="left")
    cb = cb[cb["q"] > 0.0]
    al_techo = (cb["precio"] - cb["techo"]).abs() <= tol_precio
    al_piso = ~al_techo & ((cb["precio"] - cb["piso_juego"].astype(float))
                           .abs() <= tol_precio)
    for columna, mascara in (("kwh_al_techo", al_techo),
                             ("kwh_al_piso", al_piso)):
        por = cb[mascara].groupby("comprador")["q"].sum()
        filas[columna] = por.reindex(filas.index).fillna(0.0)
        filas.loc[COMUNIDAD, columna] = float(cb.loc[mascara, "q"].sum())

    faltante = ag[["hora", "agente", "faltante"]].assign(
        faltante=lambda d: pd.to_numeric(d["faltante"]).astype(float))
    for columna, lista in (("kwh_excluida", "excluidos"),
                           ("kwh_excluida_bajo_piso", "excluidos_bajo_piso")):
        largo = _nombres_largos(h, lista).merge(faltante,
                                                on=["hora", "agente"],
                                                how="left")
        por = largo.groupby("agente")["faltante"].sum()
        filas[columna] = por.reindex(filas.index).fillna(0.0)
        filas.loc[COMUNIDAD, columna] = float(largo["faltante"].sum())

    uno = set(h.loc[h["regimen"] == "un_comprador", "hora"])
    fl1 = fl[fl["hora"].isin(uno)]
    filas.loc[COMUNIDAD, "kwh_un_comprador"] = fl1["kwh"].sum()
    for n in instituciones:
        filas.loc[n, "kwh_un_comprador"] = fl1.loc[
            (fl1["vendedor"] == n) | (fl1["comprador"] == n), "kwh"].sum()

    optimo = pd.to_numeric(h["excedente_optimo"]).astype(float)
    cap = pd.to_numeric(h["captura"]).astype(float)
    con = h["resuelta"] & (optimo > 0.0)
    if con.any():
        filas.loc[COMUNIDAD, "captura_media"] = float(cap[con].mean())
        filas.loc[COMUNIDAD, "captura_agregada"] = float(
            (cap[con] * optimo[con]).sum() / optimo[con].sum())
    return filas, por_escenario, avisos


# ─── hora a hora (D71) ─────────────────────────────────────────────────────

# Las entradas de la hora que decide el nucleo, por agente.
ENTRADAS = ("sobrante", "faltante", "techo", "piso")


def _por_hora_y_agente(ag: pd.DataFrame) -> pd.DataFrame:
    d = ag[["hora", "agente", "papel"] + list(ENTRADAS)].copy()
    d["agente"] = d["agente"].astype(str)
    d["papel"] = d["papel"].astype(str)
    for c in ENTRADAS:
        d[c] = pd.to_numeric(d[c], errors="raise").astype(float)
    return d.set_index(["hora", "agente"]).sort_index()


def horas_distintas(vieja: dict, nueva: dict,
                    tol_kwh: float = 0.0) -> tuple:
    """Las horas en que la nueva difiere de la vieja (D71). Devuelve
    (entradas, mercado): dos DataFrames con una fila por hora.

    `entradas`: las horas con alguna entrada distinta (sobrante, faltante,
    techo, piso o papel de algun agente, o un agente que solo esta en una), con
    la mayor diferencia; no se comparan por el mercado.
    `mercado`: entre las horas con las mismas entradas, las que tienen otro
    regimen o alguna pareja (vendedor, comprador) con |kwh nueva - kwh vieja|
    > `tol_kwh` (una pareja que falta en un lado cuenta con 0), con el regimen
    de cada una, la mayor diferencia por pareja y la energia que cambia de
    manos, `kwh_movida`. Con `tol_kwh=0` es al bit.

    `kwh_movida` MIDE EL LADO COMPRADOR: ½·sum_i |q nueva - q vieja|, con q lo
    que recibe cada comprador, que es la energia que cambia de manos entre
    compradores (la del censo de M-E en las horas frageles del lado
    comprador, que son todas las de los trece casos). Una hora que solo
    cambiara lo que vende cada vendedor (la rama cuantal del lado vendedor)
    saldria con `max_dif_kwh` > 0 y `kwh_movida` en 0.
    """
    av = _por_hora_y_agente(vieja["agentes"])
    an = _por_hora_y_agente(nueva["agentes"])
    ambos = av.join(an, how="outer", lsuffix="_v", rsuffix="_n")
    # Un agente que solo esta en un lado; un NaN en los dos lados es lo mismo.
    falta = (ambos["papel_v"].isna() | ambos["papel_n"].isna()).to_numpy()
    difs = []
    for c in ENTRADAS:
        a = ambos[f"{c}_v"].to_numpy(dtype=float)
        b = ambos[f"{c}_n"].to_numpy(dtype=float)
        dd = np.abs(b - a)
        difs.append(np.where(np.isnan(a) & np.isnan(b), 0.0,
                             np.where(np.isnan(dd), np.inf, dd)))
    dif_ent = pd.Series(np.max(np.column_stack(difs), axis=1),
                        index=ambos.index)
    papel = (ambos["papel_v"].astype(str) != ambos["papel_n"].astype(str))
    otra = (dif_ent.to_numpy() > 0.0) | falta | papel.to_numpy()
    horas_ent = sorted(set(ambos.index[otra].get_level_values("hora")))
    con_otra_entrada = set(horas_ent)
    entradas = pd.DataFrame(dict(
        hora=horas_ent,
        max_dif=[float(dif_ent.loc[h].max()) for h in horas_ent]))

    def _regimen(t):
        h = t["horas"][["hora", "regimen"]].copy()
        h["regimen"] = h["regimen"].where(h["regimen"].notna(), "") \
            .astype(str)
        return h.set_index("hora")["regimen"]

    rv, rn = _regimen(vieja), _regimen(nueva)
    reg = pd.concat([rv.rename("regimen_vieja"), rn.rename("regimen_nueva")],
                    axis=1).fillna("")

    def _flujos(t):
        f = t["flujos"][["hora", "vendedor", "comprador", "kwh"]].copy()
        f["vendedor"] = f["vendedor"].astype(str)
        f["comprador"] = f["comprador"].astype(str)
        f["kwh"] = pd.to_numeric(f["kwh"], errors="raise").astype(float)
        return f.groupby(["hora", "vendedor", "comprador"])["kwh"].sum()

    fl = pd.concat([_flujos(vieja).rename("v"), _flujos(nueva).rename("n")],
                   axis=1).fillna(0.0)
    fl["dif"] = (fl["n"] - fl["v"]).abs()
    por_hora = fl.groupby(level="hora")["dif"].max()
    q = fl.groupby(level=["hora", "comprador"])[["v", "n"]].sum()
    movida = 0.5 * (q["n"] - q["v"]).abs().groupby(level="hora").sum()
    horas = sorted(set(reg.index) | set(por_hora.index))
    filas = []
    for h in horas:
        if h in con_otra_entrada:
            continue
        rv_h = reg["regimen_vieja"].get(h, "")
        rn_h = reg["regimen_nueva"].get(h, "")
        d = float(por_hora.get(h, 0.0))
        if rv_h != rn_h or d > tol_kwh:
            filas.append(dict(hora=int(h), regimen_vieja=rv_h,
                              regimen_nueva=rn_h, max_dif_kwh=d,
                              kwh_movida=float(movida.get(h, 0.0))))
    mercado = pd.DataFrame(filas, columns=["hora", "regimen_vieja",
                                           "regimen_nueva", "max_dif_kwh",
                                           "kwh_movida"])
    return entradas, mercado


# ─── la comparacion ────────────────────────────────────────────────────────


def _signo(d: float, a: float, b: float, tol_cop: float,
           tol_rel: float) -> float:
    if not (np.isfinite(d) and np.isfinite(a) and np.isfinite(b)):
        return np.nan
    if abs(d) <= max(tol_cop, tol_rel * max(abs(a), abs(b))):
        return 0.0
    return float(np.sign(d))


def _txt(s: float) -> str:
    if not np.isfinite(s):
        return "?"
    return {1.0: "+", -1.0: "-", 0.0: "0"}[s]


def _ordenes(por_escenario: dict) -> dict:
    """Las diferencias que ordenan: nombre -> (serie A, serie B), A - B."""
    fuera = {}
    if "P2P" in por_escenario:
        for c in ESCENARIOS_P2P:
            if c in por_escenario:
                fuera[f"P2P_menos_{c}"] = (por_escenario["P2P"],
                                           por_escenario[c])
    if "P2P_colectivo" in por_escenario:
        for c in ESCENARIOS_COLECTIVO:
            if c in por_escenario:
                fuera[f"P2P_colectivo_menos_{c}"] = (
                    por_escenario["P2P_colectivo"], por_escenario[c])
    return fuera


def compara(vieja: tuple, nueva: tuple, caso: str, tol_cop: float = 1.0,
            tol_rel: float = 1e-6) -> pd.DataFrame:
    """Una fila por institucion (la comunidad primero) con la vieja, la nueva
    y la diferencia (nueva - vieja) de cada metrica comun, lo solo de la
    nueva, y cada orden con su signo en las dos y si cambio."""
    fv, ev, _ = vieja
    fn, en, _ = nueva
    indice = list(dict.fromkeys(list(fn.index) + list(fv.index)))
    ov, on = _ordenes(ev), _ordenes(en)
    filas = []
    for inst in indice:
        fila = dict(caso=caso, institucion=inst)
        for m in COMUNES:
            a = float(fv[m].get(inst, np.nan)) if inst in fv.index else np.nan
            b = float(fn[m].get(inst, np.nan)) if inst in fn.index else np.nan
            fila[f"{m}_vieja"], fila[f"{m}_nueva"] = a, b
            fila[f"{m}_dif"] = b - a
        for m in SOLO_NUEVA:
            fila[f"{m}_nueva"] = (float(fn[m].get(inst, np.nan))
                                  if inst in fn.index else np.nan)
        for nombre in dict.fromkeys(list(ov) + list(on)):
            signos = []
            for lado, ordenes in (("vieja", ov), ("nueva", on)):
                if nombre in ordenes:
                    sa, sb = ordenes[nombre]
                    a = float(sa.get(inst, np.nan))
                    b = float(sb.get(inst, np.nan))
                    d = a - b
                    signos.append(_signo(d, a, b, tol_cop, tol_rel))
                else:
                    d = np.nan
                    signos.append(np.nan)
                fila[f"{nombre}_{lado}"] = d
            fila[f"{nombre}_signo"] = f"{_txt(signos[0])} -> {_txt(signos[1])}"
            fila[f"{nombre}_cambia_signo"] = (
                "no comparable" if not all(np.isfinite(signos))
                else ("si" if signos[0] != signos[1] else "no"))
        filas.append(fila)
    return pd.DataFrame(filas)


# ─── salida ────────────────────────────────────────────────────────────────


def _num(x: float, dec: int = 2) -> str:
    if x is None or not np.isfinite(x):
        return "-"
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def resume(tabla: pd.DataFrame, caso: str) -> None:
    c = tabla[(tabla["caso"] == caso)
              & (tabla["institucion"] == COMUNIDAD)].iloc[0]
    print(f"  --- {caso}")
    print(f"    energia transada   {_num(c['kwh_transada_vieja'])} -> "
          f"{_num(c['kwh_transada_nueva'])} (kWh)")
    print(f"    precio medio       {_num(c['precio_medio_vieja'])} -> "
          f"{_num(c['precio_medio_nueva'])} (COP/kWh)")
    print(f"    parte del vendedor {_num(c['parte_vendedor_vieja'], 3)} -> "
          f"{_num(c['parte_vendedor_nueva'], 3)}")
    print(f"    beneficio P2P      {_num(c['beneficio_P2P_vieja'], 0)} -> "
          f"{_num(c['beneficio_P2P_nueva'], 0)} (COP)")
    e = c["kwh_transada_nueva"]
    uno = c["kwh_un_comprador_nueva"]
    pct = 100.0 * uno / e if np.isfinite(uno) and e > 0 else np.nan
    print(f"    nueva: al techo {_num(c['kwh_al_techo_nueva'])}, al piso "
          f"{_num(c['kwh_al_piso_nueva'])}, excluida "
          f"{_num(c['kwh_excluida_nueva'])} y bajo el piso "
          f"{_num(c['kwh_excluida_bajo_piso_nueva'])} (kWh); captura media "
          f"{_num(c['captura_media_nueva'], 3)} y agregada "
          f"{_num(c['captura_agregada_nueva'], 3)}")
    print(f"    nueva: horas de un solo comprador {_num(uno)} (kWh), "
          f"{_num(pct, 1)} % de la energia (M-H: D54 se reabre si pasa del 5 %)")
    sub = tabla[tabla["caso"] == caso]
    cambios = []
    for col in [x for x in sub.columns if x.endswith("_cambia_signo")]:
        nombre = col[: -len("_cambia_signo")]
        for _, r in sub[sub[col] == "si"].iterrows():
            cambios.append(f"{r['institucion']}: {nombre.replace('_menos_', ' - ')} "
                           f"{r[nombre + '_signo']}")
    if cambios:
        print(f"    CAMBIOS DE SIGNO ({len(cambios)}):")
        for x in cambios:
            print(f"      {x}")
    else:
        print("    ningun orden P2P frente a C_k ni P2P colectivo frente a C4 "
              "cambia de signo")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="La matriz vieja frente a la nueva (M-F, D48).")
    ap.add_argument("--vieja", required=True, help="raiz de la matriz vieja")
    ap.add_argument("--nueva", required=True, help="raiz de la matriz nueva")
    ap.add_argument("--casos", nargs="*", default=None)
    ap.add_argument("--cobertura", default="m1")
    ap.add_argument("--sufijo-vieja", default="")
    ap.add_argument("--sufijo-nueva", default="")
    ap.add_argument("--tol-cop", type=float, default=1.0)
    ap.add_argument("--tol-rel", type=float, default=1e-6)
    ap.add_argument("--por-hora", action="store_true",
                    help="D71: ademas, hora a hora, las horas con entradas "
                         "distintas y, entre las demas, las del mercado "
                         "distinto (regimen o flujos); lista en "
                         "<salida>_horas.csv")
    ap.add_argument("--tol-kwh", type=float, default=0.0,
                    help="D71: diferencia de kwh por pareja que cuenta como "
                         "distinta con --por-hora; 0 (defecto) es al bit")
    ap.add_argument("--salida", required=True, help="CSV de la comparacion")
    a = ap.parse_args(argv)
    # CAL-28b: una consola cp1252 revienta con un caracter fuera de su tabla.
    if (hasattr(sys.stdout, "reconfigure")
            and str(getattr(sys.stdout, "encoding", "")).lower() != "utf-8"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    def tiene(raiz, caso, sufijo):
        return (carpeta(raiz, caso, sufijo) / a.cobertura).is_dir()

    if a.casos:
        casos = list(a.casos)
        faltan = [f"{c} ({lado})" for c in casos
                  for lado, raiz, suf in (("vieja", a.vieja, a.sufijo_vieja),
                                          ("nueva", a.nueva, a.sufijo_nueva))
                  if not tiene(raiz, c, suf)]
        if faltan:
            print(f"  FALTA el almacen de: {', '.join(faltan)}")
            return 2
    else:
        nuevas = Path(a.nueva)
        # Sin sufijo, las carpetas del barrido y las figuras del foro no son
        # casos (revision de 4b, menor 6).
        def es_candidata(nombre: str) -> bool:
            if not nombre.endswith(a.sufijo_nueva):
                return False
            if not a.sufijo_nueva:
                return "_sigma" not in nombre and nombre != "figuras_foro"
            return True

        candidatos = sorted(p.name[: len(p.name) - len(a.sufijo_nueva)]
                            for p in (nuevas.iterdir() if nuevas.is_dir()
                                      else [])
                            if p.is_dir() and es_candidata(p.name))
        casos = [c for c in candidatos if tiene(a.nueva, c, a.sufijo_nueva)
                 and tiene(a.vieja, c, a.sufijo_vieja)]
        solo = [c for c in candidatos if tiene(a.nueva, c, a.sufijo_nueva)
                and not tiene(a.vieja, c, a.sufijo_vieja)]
        if solo:
            print(f"  AVISO: sin almacen en la vieja, no se comparan: {solo}")
    if not casos:
        print("  NO HAY NINGUN CASO QUE COMPARAR")
        return 2

    print("=" * 78)
    print("  LA MATRIZ VIEJA FRENTE A LA NUEVA (M-F)")
    print(f"    vieja = {a.vieja} (sufijo {a.sufijo_vieja!r})")
    print(f"    nueva = {a.nueva} (sufijo {a.sufijo_nueva!r})")
    print(f"    empate si |P2P - C_k| <= max({a.tol_cop:g} (COP), "
          f"{a.tol_rel:g} x beneficio)")
    print("=" * 78)
    partes = []
    por_hora = []
    for caso in casos:
        try:
            t_vieja = carga(a.vieja, caso, a.cobertura, a.sufijo_vieja)
            t_nueva = carga(a.nueva, caso, a.cobertura, a.sufijo_nueva)
            vieja = metricas(t_vieja)
            nueva = metricas(t_nueva)
        except DatosNoFinitos as e:
            print(f"  NO SE PUEDE COMPARAR {caso}: {e}")
            return 2
        if a.por_hora:
            entradas, mercado = horas_distintas(t_vieja, t_nueva, a.tol_kwh)
            cambios = sorted({(str(x), str(y)) for x, y in zip(
                mercado["regimen_vieja"], mercado["regimen_nueva"])})
            print(f"  --- {caso}, hora a hora (D71): {len(entradas)} horas "
                  f"con entradas distintas (no se comparan); {len(mercado)} "
                  f"con las mismas entradas y el mercado distinto, "
                  f"{_num(float(mercado['kwh_movida'].sum()))} (kWh) que "
                  f"cambian de manos; regimenes "
                  f"{', '.join(f'{x} -> {y}' for x, y in cambios) or '-'}")
            por_hora += [entradas.assign(caso=caso, que="entradas"),
                         mercado.assign(caso=caso, que="mercado")]
        for lado, (_, _, avisos) in (("vieja", vieja), ("nueva", nueva)):
            for aviso in avisos:
                if lado == "vieja" and aviso.startswith("NO MEDIDO"):
                    continue
                print(f"  AVISO {caso} ({lado}): {aviso}")
        tabla = compara(vieja, nueva, caso, a.tol_cop, a.tol_rel)
        resume(tabla, caso)
        partes.append(tabla)
    todo = pd.concat(partes, ignore_index=True)
    salida = Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", encoding="utf-8", newline="") as f:
        f.write(f"# vieja={a.vieja}{a.sufijo_vieja and ' sufijo=' + a.sufijo_vieja}; "
                f"nueva={a.nueva}{a.sufijo_nueva and ' sufijo=' + a.sufijo_nueva}; "
                f"cobertura={a.cobertura}; dif = nueva - vieja; empate si "
                f"|P2P - C_k| <= max({a.tol_cop:g} COP, {a.tol_rel:g} x "
                f"beneficio)\n")
        todo.to_csv(f, index=False)
    print(f"\n  {len(casos)} caso(s); tabla en {salida}")
    if a.por_hora:
        horas_csv = salida.with_name(salida.stem + "_horas.csv")
        pd.concat(por_hora, ignore_index=True).to_csv(horas_csv, index=False)
        print(f"  horas distintas en {horas_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
