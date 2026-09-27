"""Analisis del GSA directo de UN caso (apartados 5 y 6 del diseno, D73-D77).

Actividad 4.1 (y 4.2 por las brechas contra los mecanismos regulatorios).

Lee el CSV de `correr.py` y su `.meta.json`, y:

1. PROCEDENCIA: regenera la muestra de Saltelli con el n y la semilla de la
   meta y exige que las entradas del CSV coincidan fila a fila;
2. BLOQUES: toma el prefijo de bloques completos (un fichero interrumpido es
   analizable hasta su ultimo bloque completo) y descarta el BLOQUE entero
   de cada evaluacion fallida, sin imputar nada. Mas del 1 % de bloques
   descartados DETIENE el analisis (codigo 3) y obliga a mirar los motivos;
3. INDICES: S1, ST y S2 de las catorce salidas de comunidad con 1 000
   remuestreos, ANIDADOS sobre los primeros 16, 32, ..., n bloques del mismo
   CSV (la curva de convergencia sale de la misma corrida);
4. CONVERGENCIA: por brecha y entrada, |ST(n) - ST(n/2)| <= 0,02 y
   semiancho al 95 % <= 0,05; en los niveles, <= 0,03 y <= 0,08;
5. DECISION: la probabilidad de inversion de cada brecha (de comunidad y por
   institucion) contra el signo del punto base, con intervalo por
   remuestreo, y el coeficiente de variacion de cada mecanismo. Se calculan
   sobre las filas A y B de cada bloque, que son las muestras independientes
   del hipercubo (las AB y BA son sus permutaciones);
6. IDENTIDADES (6.5): C2 == P2P en todas las filas (CAL-52) y retiros = 0
   (D67), que DETIENEN si fallan (codigo 1); P2P - C1 == excedente (H-70) y
   la energia sin efecto de f_cv, f_bolsa, f_tarifa y f_peaje, que se miden
   y se informan sin detener (ver el informe de la tarea G).

Escribe `indices_<caso>.csv`, `s2_<caso>.csv`, `inversion_<caso>.csv` e
`INFORME_<caso>.md` junto al CSV.

    python -u gsa_directo/analizar.py --caso E0 --n-base 2048
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from gsa_directo import comun  # noqa: E402

UMBRAL_DESCARTE = 0.01
REMUESTREOS = 1000
N_MIN_CURVA = 16
CRITERIOS = {
    "brecha": (0.02, 0.05),
    "nivel": (0.03, 0.08),
}
TOL_C2 = 1e-6
TOL_H70 = 1e-6


def clase(salida: str) -> str:
    if salida in comun.BRECHAS:
        return "brecha"
    if salida in comun.NIVELES:
        return "nivel"
    return "otra"


# ── Bloques ─────────────────────────────────────────────────────────────────
def prefijo_de_bloques(presentes: np.ndarray, B: int) -> int:
    """Numero de bloques completos al principio (todas sus filas escritas)."""
    n = presentes.size // B
    completos = presentes[: n * B].reshape(n, B).all(axis=1)
    malos = np.flatnonzero(~completos)
    return int(malos[0]) if malos.size else int(n)


def bloques_validos(validas: np.ndarray, n_bloques: int, B: int) -> np.ndarray:
    """(n_bloques,) True si las B filas del bloque son buenas."""
    return validas[: n_bloques * B].reshape(n_bloques, B).all(axis=1)


def filas_de(bloques: np.ndarray, B: int) -> np.ndarray:
    return np.repeat(bloques, B)


def filas_ab(n_bloques: int, B: int) -> np.ndarray:
    """Mascara de las filas A (primera) y B (ultima) de cada bloque."""
    m = np.zeros(n_bloques * B, dtype=bool)
    m[0::B] = True
    m[B - 1::B] = True
    return m


# ── Indices ─────────────────────────────────────────────────────────────────
def indices(problema: dict, y: np.ndarray, semilla: int = comun.SEMILLA,
            remuestreos: int = REMUESTREOS):
    """S1, ST, S2 con sus semianchos; None si la varianza es nula."""
    from SALib.analyze import sobol as sobol_analyze
    y = np.asarray(y, dtype=float)
    if not np.all(np.isfinite(y)):
        raise ValueError("salida no finita dentro de los bloques validos")
    if np.var(y) <= 0.0:
        return None
    return sobol_analyze.analyze(problema, y, calc_second_order=True,
                                 num_resamples=remuestreos, conf_level=0.95,
                                 seed=semilla, print_to_console=False)


def niveles_de_n(n_disponible: int) -> list:
    ns, n = [], N_MIN_CURVA
    while n <= n_disponible:
        ns.append(n)
        n *= 2
    if not ns and n_disponible > 0:
        ns = [n_disponible]
    return ns


def analiza(X: np.ndarray, Y: dict, validas: np.ndarray,
            presentes: np.ndarray, base: dict = None,
            problema: dict = comun.PROBLEMA, B: int = comun.B,
            salidas=comun.SALIDAS, extra_inversion=(),
            semilla: int = comun.SEMILLA, remuestreos: int = REMUESTREOS,
            motivos=None) -> dict:
    """El analisis entero sobre matrices ya leidas. `Y[s]` es (M,), con NaN
    donde la fila falta o fallo; `validas` y `presentes` son (M,)."""
    nombres_x = list(problema["names"])
    n_disp = prefijo_de_bloques(presentes, B)
    if n_disp == 0:
        return dict(n_disponible=0, detenido="no hay ni un bloque completo")
    bv = bloques_validos(validas, n_disp, B)
    n_desc = int((~bv).sum())
    frac = n_desc / n_disp
    r = dict(n_disponible=n_disp, n_descartados=n_desc, frac_descartados=frac,
             detenido=None, motivos=dict(motivos or {}), filas=[], s2=[],
             curva=[], inversion=[], cv={}, identidades=[], salidas=list(
                 salidas), entradas=nombres_x)
    if frac > UMBRAL_DESCARTE:
        r["detenido"] = (f"{n_desc} de {n_disp} bloques descartados "
                         f"({100 * frac:.2f} %), mas del "
                         f"{100 * UMBRAL_DESCARTE:.0f} %")
        return r

    ns = niveles_de_n(n_disp)
    r["niveles_n"] = ns
    for n in ns:
        keep = filas_de(bv[:n], B)
        filas_n = np.arange(n * B)[keep]
        for s in salidas:
            Si = indices(problema, Y[s][filas_n], semilla, remuestreos)
            for i, x in enumerate(nombres_x):
                r["filas"].append(dict(
                    n=n, n_validos=int(bv[:n].sum()), salida=s, entrada=x,
                    rotulo_entrada=comun.ROTULOS.get(x, x), clase=clase(s),
                    S1=np.nan if Si is None else float(Si["S1"][i]),
                    S1_conf=np.nan if Si is None else float(Si["S1_conf"][i]),
                    ST=np.nan if Si is None else float(Si["ST"][i]),
                    ST_conf=np.nan if Si is None else float(Si["ST_conf"][i]),
                    varianza_nula=Si is None))
            if n == ns[-1] and Si is not None:
                S2 = np.asarray(Si["S2"], dtype=float)
                S2c = np.asarray(Si["S2_conf"], dtype=float)
                for i in range(len(nombres_x)):
                    for k in range(i + 1, len(nombres_x)):
                        r["s2"].append(dict(n=n, salida=s,
                                            entrada_i=nombres_x[i],
                                            entrada_k=nombres_x[k],
                                            rotulo_i=comun.ROTULOS.get(
                                                nombres_x[i], nombres_x[i]),
                                            rotulo_k=comun.ROTULOS.get(
                                                nombres_x[k], nombres_x[k]),
                                            S2=float(S2[i, k]),
                                            S2_conf=float(S2c[i, k])))
    df = pd.DataFrame(r["filas"])
    r["convergencia"] = convergencia(df, ns)

    # Decision: sobre las filas A y B de los bloques validos.
    ab = filas_ab(n_disp, B) & filas_de(bv, B)
    rng = np.random.default_rng(semilla)
    idx_ab = np.flatnonzero(ab)
    boot = rng.integers(0, idx_ab.size, size=(remuestreos, idx_ab.size))
    for s in list(comun.BRECHAS) + list(extra_inversion):
        if s not in Y:
            continue
        y = Y[s][idx_ab]
        if base is None or s not in base:
            signo = np.sign(np.median(y))
            origen = "mediana (sin punto base)"
        else:
            signo = np.sign(base[s])
            origen = "punto base"
        inv = (np.sign(y) != signo).astype(float)
        p_boot = inv[boot].mean(axis=1)
        r["inversion"].append(dict(
            salida=s, base=(np.nan if base is None else base.get(s, np.nan)),
            signo_referencia=int(signo), referencia=origen,
            p_inversion=float(inv.mean()),
            p_inf=float(np.percentile(p_boot, 2.5)),
            p_sup=float(np.percentile(p_boot, 97.5)),
            minimo=float(y.min()), maximo=float(y.max()), n_filas=int(y.size)))
    for s in comun.NIVELES + ("C2",):
        if s in Y:
            y = Y[s][idx_ab]
            r["cv"][s] = float(np.std(y) / abs(np.mean(y)))

    r["identidades"] = identidades(Y, filas_de(bv, B), df, ns, base)
    return r


def convergencia(df: pd.DataFrame, ns: list) -> list:
    """Veredicto por salida con clase (brecha o nivel) en el ultimo par."""
    out = []
    if len(ns) < 2:
        return out
    a = df[df.n == ns[-2]].set_index(["salida", "entrada"])
    b = df[df.n == ns[-1]].set_index(["salida", "entrada"])
    for (s, x), fila in b.iterrows():
        c = clase(s)
        if c not in CRITERIOS:
            continue
        tol_d, tol_c = CRITERIOS[c]
        d = abs(float(fila.ST) - float(a.loc[(s, x)].ST))
        ok = bool(np.isfinite(d) and d <= tol_d and fila.ST_conf <= tol_c) \
            or bool(fila.varianza_nula)
        out.append(dict(salida=s, entrada=x, clase=c, n=ns[-1],
                        dST=d, ST_conf=float(fila.ST_conf), tol_dST=tol_d,
                        tol_conf=tol_c, cumple=ok))
    return out


def identidades(Y: dict, keep: np.ndarray, df: pd.DataFrame, ns: list,
                base) -> list:
    out = []
    if "C2" in Y and "P2P" in Y:
        d = np.abs(Y["C2"][keep] - Y["P2P"][keep]) / np.maximum(
            np.abs(Y["P2P"][keep]), 1.0)
        out.append(dict(identidad="C2 == P2P (CAL-52)", dura=True,
                        medida=float(d.max()) if d.size else 0.0,
                        tolerancia=TOL_C2,
                        cumple=bool(d.size == 0 or d.max() <= TOL_C2)))
    if "retiros" in Y:
        m = float(np.nanmax(Y["retiros"][keep])) if keep.any() else 0.0
        out.append(dict(identidad="retiros = 0 (D67)", dura=True, medida=m,
                        tolerancia=0.0, cumple=m == 0.0))
    if "P2P_menos_C1" in Y and "excedente" in Y:
        d = np.abs(Y["P2P_menos_C1"][keep] - Y["excedente"][keep]) / \
            np.maximum(np.abs(Y["excedente"][keep]), 1.0)
        out.append(dict(identidad="P2P - C1 == excedente (H-70)", dura=False,
                        medida=float(d.max()) if d.size else 0.0,
                        tolerancia=TOL_H70,
                        cumple=bool(d.size == 0 or d.max() <= TOL_H70)))
    if ns and "energia" in set(df.salida):
        ult = df[(df.n == ns[-1]) & (df.salida == "energia")]
        for x in ("f_cv", "f_bolsa", "f_tarifa", "f_peaje"):
            f = ult[ult.entrada == x]
            if f.empty:
                continue
            st, cf = float(f.ST.iloc[0]), float(f.ST_conf.iloc[0])
            out.append(dict(identidad=f"energia sin efecto de {x} (ST = 0 "
                                      f"dentro del intervalo)", dura=False,
                            medida=st, tolerancia=cf,
                            cumple=bool(abs(st) <= cf + 1e-12)))
    return out


# ── Lectura del CSV ─────────────────────────────────────────────────────────
def lee_corrida(csv_path: Path, meta: dict):
    """(X, Y, validas, presentes, motivos) en el orden de la muestra."""
    M = int(meta["M"])
    df = pd.read_csv(csv_path, dtype={"motivo": str}, keep_default_na=True)
    df = df[pd.to_numeric(df["idx"], errors="coerce").notna()]
    df["idx"] = df["idx"].astype(int)
    df = df[(df.idx >= 0) & (df.idx < M)]
    df["motivo"] = df["motivo"].fillna("").astype(str)
    # Si un indice quedo dos veces, gana la fila buena.
    df["_buena"] = (df["motivo"].str.strip() == "")
    df = df.sort_values(["idx", "_buena"]).drop_duplicates("idx", keep="last")
    presentes = np.zeros(M, dtype=bool)
    presentes[df.idx.to_numpy()] = True
    X = np.full((M, len(comun.NOMBRES)), np.nan)
    X[df.idx.to_numpy()] = df[comun.NOMBRES].to_numpy(dtype=float)
    cols = [c for c in meta["columnas"] if c not in ("idx", "seg", "rss_mb",
                                                     "motivo")
            and c not in comun.NOMBRES]
    Y = {}
    for c in cols:
        v = np.full(M, np.nan)
        v[df.idx.to_numpy()] = pd.to_numeric(df[c], errors="coerce").to_numpy()
        Y[c] = v
    fin = np.all(np.isfinite(np.vstack([Y[s] for s in comun.SALIDAS])),
                 axis=0)
    buenas = np.zeros(M, dtype=bool)
    buenas[df.idx.to_numpy()] = df["_buena"].to_numpy()
    validas = presentes & buenas & fin
    motivos = df.loc[~df["_buena"], "motivo"].str.split(":").str[0] \
        .value_counts().to_dict()
    return X, Y, validas, presentes, motivos


def procedencia(X: np.ndarray, presentes: np.ndarray, meta: dict) -> str:
    """'' si las entradas del CSV son la muestra de la meta; si no, el fallo."""
    Xr = comun.muestra(int(meta["n_base"]), int(meta["semilla"]))
    if Xr.shape[0] != int(meta["M"]):
        return f"la muestra regenerada tiene {Xr.shape[0]} filas y no {meta['M']}"
    if list(meta.get("entradas", [])) != list(comun.NOMBRES) or \
            meta.get("soportes") != comun.SOPORTES:
        return "las entradas o los rangos de la meta no son los del diseno"
    d = np.abs(X[presentes] - Xr[presentes])
    if d.size and not np.all(d <= 1e-12 * np.maximum(np.abs(Xr[presentes]),
                                                      1.0)):
        filas = np.flatnonzero(presentes)[np.any(
            d > 1e-12 * np.maximum(np.abs(Xr[presentes]), 1.0), axis=1)]
        return f"{filas.size} filas con entradas distintas de la muestra " \
               f"(primeras: {filas[:5].tolist()})"
    return ""


# ── Informe ─────────────────────────────────────────────────────────────────
ORDEN_INFORME = ("P2P_menos_C4", "P2Pcol_menos_C1", "C4_menos_C1",
                 "P2P_menos_C5", "P2P_menos_C1", "parte_vendedor",
                 "excedente", "energia", "P2P", "P2P_colectivo", "C1", "C3",
                 "C4", "C5")


def informe(r: dict, caso: str, meta: dict) -> str:
    L = [f"# GSA directo · caso {caso} ({meta.get('opcion') or 'sin opcion'})",
         "",
         f"Muestra de Saltelli de segundo orden, n_base {meta.get('n_base')}, "
         f"semilla {meta.get('semilla')}, {comun.B} filas por bloque; "
         f"huella {meta.get('huella')}, dato {meta.get('huella_datos')}, "
         f"codigo {meta.get('codigo')}. Actividad 4.1 (D73 a D79).", ""]
    if meta.get("verificar"):
        L += ["> **NUMEROS FALSOS**: corrida de verificacion de la maquinaria.",
              ""]
    L += ["## Bloques", "",
          f"- Bloques completos: {r['n_disponible']} de "
          f"{meta.get('n_base')}.",
          f"- Descartados (bloque de Saltelli entero por una evaluacion "
          f"fallida, sin imputar): {r.get('n_descartados', 0)} "
          f"({100 * r.get('frac_descartados', 0):.2f} %; umbral "
          f"{100 * UMBRAL_DESCARTE:.0f} %).",
          f"- Motivos: {r.get('motivos') or 'ninguno'}.", ""]
    if r.get("detenido"):
        L += [f"**ANALISIS DETENIDO: {r['detenido']}.** Hay que mirar los "
              f"motivos antes de publicar ningun indice.", ""]
        return "\n".join(L)
    df = pd.DataFrame(r["filas"])
    nmax = r["niveles_n"][-1]
    ult = df[df.n == nmax]
    L += ["## Entradas", "", "| Entrada | Que es | Rango |", "|---|---|---|"]
    for x, s in zip(comun.NOMBRES, comun.SOPORTES):
        L.append(f"| {x} | {comun.ROTULOS[x]} | [{s[0]:g}; {s[1]:g}] |")
    L += ["",
          "f_cv NO es el Cv de la tarifa: es el factor sobre el componente de "
          "comercializar que el art. 25 descuenta de la permuta para el piso "
          "del vendedor (y el que usan C1, C4, el colectivo y los residuales, "
          "como `--factor-cv` de `main()`, D7). No mueve C5 ni el techo.", "",
          "## Antes de leer la tabla", "",
          "- **P2P - C1 es una identidad** (H-70): el ancho de la banda por la "
          "energia. Su ST sobre f_cv es una comprobacion, no un hallazgo.",
          "- Los niveles miden sobre todo la tarifa (el autoconsumo se valora "
          "a ella); la comparacion de robustez se lee en el coeficiente de "
          "variacion y en las brechas.",
          "- e_G y e_D se reparten la cobertura dentro del error; se publica "
          "tambien su suma como «error de medida».", "",
          f"## Indices totales (ST) con n = {nmax}, semiancho al 95 %", "",
          "| Salida | " + " | ".join(r["entradas"]) + " | ST(e_G) + ST(e_D) |",
          "|---|" + "---:|" * (len(r["entradas"]) + 1)]
    for s in ORDEN_INFORME:
        f = ult[ult.salida == s].set_index("entrada")
        if f.empty:
            continue
        if f.varianza_nula.all():
            L.append(f"| {s} | " + " | ".join("var. nula" for _ in
                                             r["entradas"]) + " | |")
            continue
        celdas = [f"{f.loc[x].ST:.3f} (±{f.loc[x].ST_conf:.3f})"
                  for x in r["entradas"]]
        em = f.loc["e_G"].ST + f.loc["e_D"].ST
        L.append(f"| {s} | " + " | ".join(celdas) + f" | {em:.3f} |")
    L += ["", f"## Indices de primer orden (S1) con n = {nmax}", "",
          "| Salida | " + " | ".join(r["entradas"]) + " |",
          "|---|" + "---:|" * len(r["entradas"])]
    for s in ORDEN_INFORME:
        f = ult[ult.salida == s].set_index("entrada")
        if f.empty or f.varianza_nula.all():
            continue
        L.append(f"| {s} | " + " | ".join(f"{f.loc[x].S1:.3f}"
                                         for x in r["entradas"]) + " |")
    s2 = pd.DataFrame(r["s2"])
    L += ["", "## Interacciones de segundo orden con |S2| > 0,02", ""]
    if not s2.empty:
        g = s2[s2.S2.abs() > 0.02].sort_values("S2", key=np.abs,
                                               ascending=False)
        if g.empty:
            L.append("Ninguna.")
        else:
            L += ["| Salida | Par | S2 | semiancho |", "|---|---|---:|---:|"]
            for _, f in g.iterrows():
                L.append(f"| {f.salida} | {f.entrada_i} × {f.entrada_k} | "
                         f"{f.S2:.3f} | {f.S2_conf:.3f} |")
    L += ["", "## Convergencia con n (bloques anidados)", "",
          "| n | semiancho ST maximo | mediana |", "|---:|---:|---:|"]
    for n in r["niveles_n"]:
        d = df[(df.n == n) & ~df.varianza_nula]
        L.append(f"| {n} | {d.ST_conf.max():.3f} | {d.ST_conf.median():.3f} |")
    conv = pd.DataFrame(r["convergencia"])
    if conv.empty:
        L += ["", "Un solo nivel de n: sin veredicto de convergencia."]
    else:
        no = conv[~conv.cumple]
        L += ["", f"Criterio (apartado 6.3), entre n = {r['niveles_n'][-2]} "
                  f"y n = {nmax}: brechas |dST| <= 0,02 y semiancho <= 0,05; "
                  f"niveles <= 0,03 y <= 0,08.", "",
              ("**CONVERGE** en todas las brechas y niveles." if no.empty else
               f"**NO CONVERGE** en {len(no)} pares salida-entrada:")]
        for _, f in no.iterrows():
            L.append(f"- {f.salida} / {f.entrada}: dST {f.dST:.3f} (tope "
                     f"{f.tol_dST}), semiancho {f.ST_conf:.3f} (tope "
                     f"{f.tol_conf})")
    L += ["", "## Probabilidad de inversion (filas A y B de los bloques "
              "validos; intervalo al 95 % por remuestreo)", "",
          "| Brecha | Punto base (COP) | P(inversion) | Intervalo | Minimo | "
          "Maximo |", "|---|---:|---:|---|---:|---:|"]
    for f in r["inversion"]:
        L.append(f"| {f['salida']} | {f['base']:,.0f} | "
                 f"{100 * f['p_inversion']:.2f} % | "
                 f"[{100 * f['p_inf']:.2f}; {100 * f['p_sup']:.2f}] % | "
                 f"{f['minimo']:,.0f} | {f['maximo']:,.0f} |")
    L += ["", "## Coeficiente de variacion de cada mecanismo", "",
          "| Mecanismo | CV |", "|---|---:|"]
    for s, v in r["cv"].items():
        L.append(f"| {s} | {100 * v:.2f} % |")
    L += ["", "## Identidades (apartado 6.5)", "",
          "| Identidad | Clase | Medida | Tolerancia | Cumple |",
          "|---|---|---:|---:|---|"]
    for f in r["identidades"]:
        L.append(f"| {f['identidad']} | {'detiene' if f['dura'] else 'se informa'}"
                 f" | {f['medida']:.3g} | {f['tolerancia']:.3g} | "
                 f"{'si' if f['cumple'] else '**NO**'} |")
    return "\n".join(L) + "\n"


def escribe(r: dict, carpeta: Path, caso: str, meta: dict) -> list:
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = []
    if r.get("filas"):
        p = carpeta / f"indices_{caso}.csv"
        pd.DataFrame(r["filas"]).to_csv(p, index=False)
        rutas.append(p)
    if r.get("s2"):
        p = carpeta / f"s2_{caso}.csv"
        pd.DataFrame(r["s2"]).to_csv(p, index=False)
        rutas.append(p)
    if r.get("inversion"):
        p = carpeta / f"inversion_{caso}.csv"
        pd.DataFrame(r["inversion"]).to_csv(p, index=False)
        rutas.append(p)
    p = carpeta / f"INFORME_{caso}.md"
    p.write_text(informe(r, caso, meta), encoding="utf-8")
    rutas.append(p)
    return rutas


def ejecuta(argv=None) -> int:
    comun.salida_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--caso", required=True, choices=list(comun.CASOS_SOBOL))
    ap.add_argument("--n-base", type=int, default=None)
    ap.add_argument("--semilla", type=int, default=comun.SEMILLA)
    ap.add_argument("--salidas", default=str(comun.salidas_defecto()))
    ap.add_argument("--verificar", action="store_true",
                    help="analiza la corrida de verificacion (_VERIF)")
    ap.add_argument("--remuestreos", type=int, default=REMUESTREOS)
    args = ap.parse_args(argv)
    n = args.n_base or comun.n_base_de(args.caso)
    tag = f"{args.caso}_n{n}_s{args.semilla}" + ("_VERIF" if args.verificar
                                                 else "")
    carpeta = Path(args.salidas) / args.caso
    csv_p = carpeta / f"muestras_{tag}.csv"
    meta_p = carpeta / f"muestras_{tag}.meta.json"
    print("=" * 70)
    print(f"ANALISIS GSA DIRECTO · caso {args.caso} · {csv_p.name}")
    print("=" * 70)
    if not csv_p.exists() or not meta_p.exists():
        print(f"  ABORTA: falta {csv_p if not csv_p.exists() else meta_p}")
        return 2
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    if meta.get("huella") != comun.huella_diseno(args.caso, n, args.semilla):
        print("  ABORTA: la huella de la meta no es la de este diseno.")
        return 2
    X, Y, validas, presentes, motivos = lee_corrida(csv_p, meta)
    fallo = procedencia(X, presentes, meta)
    if fallo:
        print(f"  ABORTA (procedencia): {fallo}")
        return 2
    print(f"  filas escritas {int(presentes.sum())}/{meta['M']} · buenas "
          f"{int(validas.sum())} · motivos {motivos or 'ninguno'}")
    extra = [c for c in Y if "__" in c]
    r = analiza(X, Y, validas, presentes, base=meta.get("punto_base"),
                extra_inversion=extra, semilla=args.semilla,
                remuestreos=args.remuestreos, motivos=motivos)
    rutas = escribe(r, carpeta, args.caso, meta)
    for p in rutas:
        print(f"  escrito {p}")
    if r.get("detenido"):
        print(f"  ANALISIS DETENIDO: {r['detenido']}")
        return 3
    duras = [f for f in r["identidades"] if f["dura"] and not f["cumple"]]
    for f in r["identidades"]:
        print(f"  identidad {f['identidad']}: {'cumple' if f['cumple'] else 'NO CUMPLE'}"
              f" (medida {f['medida']:.3g}, tolerancia {f['tolerancia']:.3g})"
              + ("" if f["dura"] else " [se informa]"))
    conv = r.get("convergencia") or []
    no = [c for c in conv if not c["cumple"]]
    print(f"  bloques: {r['n_disponible']} completos, "
          f"{r['n_descartados']} descartados; n analizados "
          f"{r['niveles_n']}; convergencia: "
          + ("sin veredicto (un nivel)" if not conv else
             "CONVERGE" if not no else f"NO CONVERGE en {len(no)} pares"))
    if duras:
        print(f"  IDENTIDAD ROTA: {[f['identidad'] for f in duras]}")
        return 1
    print(f"ANALISIS GSA DIRECTO {args.caso} TERMINADO")
    return 0


if __name__ == "__main__":
    sys.exit(ejecuta())
