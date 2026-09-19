"""M-D: si el reposo en forma cerrada es ESTABLE para la dinamica regularizada.

QUE DECIDE. La frase con que se enuncia el resultado en la tesis. Si todas las
direcciones son estables, el reposo es «el reposo al que la dinamica llega»; si
alguna no lo es, la frase pasa a «unico reposo, estable en lo medido», con la
lista de horas donde no.

COMO. En cada hora de la muestra: se arma el estado en el reposo cerrado (el
reparto P y los precios del nucleo, el jugador virtual en su techo, y los
filtros de los multiplicadores EN SU VALOR DE REPOSO, ver abajo), y se calcula
por diferencias centradas el jacobiano del sistema REDUCIDO: el bloque de los
precios y el del reparto, con el termino entropico (mu = 1) y sin acelerar. De
ahi, sus valores propios.

LOS FILTROS EN SU REPOSO (tarea 4e; investigacion-me-md.md, sec. 2). Antes el
estado llevaba los filtros en su ARRANQUE (lambda_filt = beta_filt = 0,
y_filt = 1, gamma = 0,1), que no es el valor que tienen en el reposo, y por eso
M-D daba residuos de 30 a 115 (kWh por unidad de tiempo) y de 1 a 3 valores
propios inestables espurios en topados, «suma no cabe», compradores cortos y
excluidos, que ademas no se juzgaban (n = 0). Ahora (`filtros_de_reposo`):
  - y_filt = 0 y gamma_j = 1000/(VEL_GPC·s_j·(p_j - b_j)), con p_j el precio
    medio que cobra el vendedor: el reposo del bloque del costo;
  - con P de rango uno, ln P_ji = ln s_j + ln q_i - ln E es separable, y el
    reposo del replicador entropico pide beta_filt,i = (pi_i - mu ln q_i) - A
    en los compradores llenos (q = d) y 0 en los demas, y
    lambda_filt,j = (-b_j - mu ln s_j) - B en los vendedores en su capacidad y
    0 en los demas; A y B son el valor comun de los que no muerden (o, si
    todos muerden, el minimo menos 1 000, como en la dinamica: un
    desplazamiento comun no cambia F - Fbar).
Lo que esa descomposicion no puede absorber es el RESIDUO DE ADMISIBILIDAD, y
se publica aparte: la dispersion de pi - mu ln q entre los compradores que no
se llenan (y la de -b - mu ln s entre los vendedores que no se agotan), un
multiplicador que tendria que ser negativo, y la respuesta cuantal que se
aparta del reparto cerrado, que es el criterio del censo de horas fragiles de
M-E (`censo_fragiles.fragilidad`): una hora fragil no es un reposo con mu = 1.

LA RAMA CUANTAL (D71, 2026-09-19). Con la rama, en las horas fragiles el
nucleo publica el reposo cuantal, y ese es el punto que M-D analiza por
defecto (en la hora 12 de E0: 0 inestables, mayor parte real fuera de las
neutras -0,615, residuo 7,5e-11). `--mu-cuantal 0` analiza la forma cerrada de
antes, como la tarea 4e (4 inestables en +6,84). «Fragil» es siempre una
propiedad de la HORA, con la forma cerrada, y en una hora fragil del lado de
los vendedores la dinamica corre con el costo del vendedor en su piso (D68).

LAS DOS DIRECCIONES NEUTRAS son conocidas y no cuentan: la suma de los precios
de los I+1 jugadores se conserva exactamente (la aptitud media del replicador
la anula), y la suma del reparto tambien (el termino entropico la conserva y el
replicador la deja quieta sobre el simplejo). Un valor propio nulo en esas dos
direcciones es la conservacion, no una inestabilidad.

EL RESIDUO, que hay que leer antes que los valores propios. Cada hora publica
|dP/dt| y |dpi/dt| en el estado de reposo (y, para comparar, en el de
arranque de antes). Una hora cuenta como «quieta» si |dP/dt| no pasa de
1e-3·E MAS EL SUELO del recorte de P: el lado derecho recorta P a 1e-10, y
cada entrada nula mete BGRANDE·1e-10 en la aptitud media, unos 1e-4 (kWh por
unidad de tiempo) por entrada, sea cual sea E (`suelo_del_recorte`). Sin
descontarlo, una hora con E pequeno y compradores sin energia salia «no
quieta» por un artefacto.

    python -u medicion_estabilidad.py \\
        --horas SALIDAS_SERVIDOR/validacion_reposo \\
        --salida SALIDAS_SERVIDOR/validacion_reposo/m_d_estabilidad.json \\
        --por-regimen 10

ACEPTACION: partes reales negativas fuera de las direcciones neutras en el
100 % de las horas.

COSTO. Unas cuarenta evaluaciones del lado derecho por hora y un problema de
valores propios de veinte por veinte: segundos para las cincuenta horas.
"""
import argparse
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import numpy as np                                    # noqa: E402
import arnes as A                                     # noqa: E402
import preparacion as PR                              # noqa: E402

MEDICION = "M-D"
QUE_DECIDE = "si el reposo en forma cerrada es estable"

GRUPOS = ("interiores", "topados", "suma_no_cabe", "mixto", "dos_vendedores",
          "compradores_cortos_sin_cesmag")
CASOS = ("E0", "K1", "E4", "E5")
MU = 1.0
# Un valor propio con parte real por debajo de esto, en relacion con el radio
# espectral, cuenta como neutro y no como inestable.
TOL_NEUTRO = 1e-8
# Cuanto tiene que alinearse un vector propio con una direccion conservada
# para darlo por esa direccion.
TOL_ALINEADO = 0.9


def filtros_de_reposo(e, cerrada, mu=MU, tol=1e-9) -> dict:
    """Los filtros de los multiplicadores y el bloque del costo en el valor que
    tienen en el reposo (ver el docstring del modulo), y lo que no se puede
    absorber (el residuo de admisibilidad, en COP/kWh).

    Devuelve dict(gamma, y_filt, lam_filt, bet_filt, dispersion_compradores,
    dispersion_vendedores, negativo, gamma_sin_reposo)."""
    from arnes import VEL_GPC
    I, J = len(e["dn"]), len(e["gn"])
    P = np.asarray(cerrada["P"], float).reshape(J, I)
    pi = np.asarray(cerrada["p"], float)
    q = P.sum(axis=0)
    sj = P.sum(axis=1)
    E = float(cerrada["E"])
    b = np.asarray(e["b"], float)
    d = np.asarray(e["dn"], float)
    g = np.asarray(e["gn"], float)
    tolE = tol * max(1.0, E)
    fuera = dict(dispersion_compradores=0.0, dispersion_vendedores=0.0,
                 negativo=0.0, gamma_sin_reposo=0)

    def lado(v, activos, muerden, clave):
        """El filtro de un lado: 0 en los que no muerden, v - A en los que
        muerden, con A el valor comun de los que no muerden."""
        f = np.zeros(v.size)
        libres = activos & ~muerden
        if libres.any():
            vl = v[libres]
            fuera[clave] = float(vl.max() - vl.min())
            A = 0.5 * float(vl.max() + vl.min())
        elif activos.any():
            A = float(v[activos].min()) - 1000.0
        else:
            return f
        f[muerden] = v[muerden] - A
        fuera["negativo"] = max(fuera["negativo"],
                                float(-np.min(f[muerden], initial=0.0)))
        return np.maximum(f, 0.0)

    servidos = q > tolE
    v_i = np.zeros(I)
    v_i[servidos] = pi[servidos] - mu * np.log(q[servidos])
    bet = lado(v_i, servidos, servidos & (np.abs(q - d) <= tolE),
               "dispersion_compradores")
    activos_j = sj > tolE
    w_j = np.zeros(J)
    w_j[activos_j] = -b[activos_j] - mu * np.log(sj[activos_j])
    lam = lado(w_j, activos_j, activos_j & (np.abs(sj - g) <= tolE),
               "dispersion_vendedores")
    # El bloque del costo: raw_gamma = VEL_GPC·gamma·(H - re) + 1000 = 0.
    re = P @ pi
    margen = re - b * sj
    gamma = np.full(J, 0.1)
    ok = margen > 0
    gamma[ok] = 1000.0 / (VEL_GPC * margen[ok])
    fuera["gamma_sin_reposo"] = int(np.sum(~ok))
    fuera.update(gamma=gamma, y_filt=np.zeros(J), lam_filt=lam, bet_filt=bet)
    return fuera


def estado_en_el_reposo(e, cerrada, precios0, filtros="reposo",
                        mu=MU) -> np.ndarray:
    """El estado completo del arnes con el reparto y los precios del reposo.

    `filtros="reposo"` (por omision, tarea 4e): los filtros en su valor de
    reposo (`filtros_de_reposo`). `filtros="arranque"`: los de antes
    (lambda_filt = beta_filt = 0, y_filt = 1, gamma = 0,1), que son los del
    motor en t = 0; solo para comparar."""
    I, J = len(e["dn"]), len(e["gn"])
    virtual = (float(precios0[-1]) if precios0 is not None
               else float(np.max(e["techo"])))
    pi_all = np.append(np.asarray(cerrada["p"], float), virtual)
    P = np.asarray(cerrada["P"], float)
    if filtros == "arranque":
        return np.concatenate([pi_all, 0.1 * np.ones(J), np.ones(J),
                               P.ravel(), 0.1 * np.ones(J), 0.1 * np.ones(I),
                               np.zeros(J), np.zeros(I)])
    if filtros != "reposo":
        raise ValueError(f"filtros={filtros!r}; use 'reposo' o 'arranque'")
    f = filtros_de_reposo(e, cerrada, mu)
    return np.concatenate([pi_all, f["gamma"], f["y_filt"], P.ravel(),
                           0.1 * np.ones(J), 0.1 * np.ones(I),
                           f["lam_filt"], f["bet_filt"]])


def suelo_del_recorte(X, ix, simplex, escala_v=10.0) -> float:
    """Lo que el recorte de P a 1e-10 mete en |dP/dt|: cada entrada nula suma
    BGRANDE·1e-10 a la aptitud media y aparta F - Fbar de las demas en
    BGRANDE·n_nulas·1e-10/simplex (tarea 4e). Es independiente de E."""
    from arnes import BGRANDE, VEL_RD
    I, J = ix["I"], ix["J"]
    P = np.maximum(np.asarray(X[ix["P"]], float).reshape(J, I), 1e-10)
    nulas = int(np.sum(P <= 1e-10 * (1 + 1e-9)))
    return float(escala_v * VEL_RD * BGRANDE * nulas * 1e-10 * P.max()
                 / max(float(simplex), 1e-12))


def jacobiano_reducido(rhs, X, ix):
    """Diferencias centradas sobre los bloques de precios y de reparto."""
    I, J = ix["I"], ix["J"]
    n_pi = I + 1
    i_P = ix["P"].start
    idx = np.concatenate([np.arange(0, n_pi),
                          np.arange(i_P, i_P + J * I)])
    n = idx.size
    Jac = np.zeros((n, n))
    for c, k in enumerate(idx):
        h = max(1e-6, 1e-6 * abs(float(X[k])))
        Xp = X.copy(); Xp[k] += h
        Xm = X.copy(); Xm[k] -= h
        Jac[:, c] = (np.asarray(rhs(0.0, Xp), float)[idx]
                     - np.asarray(rhs(0.0, Xm), float)[idx]) / (2.0 * h)
    return Jac, idx


def direcciones_neutras(I: int, J: int) -> np.ndarray:
    """Las dos sumas que la dinamica conserva, como vectores unitarios.

    Tienen soportes disjuntos (precios y reparto), de modo que son ortogonales
    y forman una base ortonormal del espacio de lo conservado."""
    n = (I + 1) + J * I
    v1 = np.zeros(n); v1[:I + 1] = 1.0            # suma de los precios
    v2 = np.zeros(n); v2[I + 1:] = 1.0            # suma del reparto
    return np.array([v1 / np.linalg.norm(v1), v2 / np.linalg.norm(v2)])


def alineacion(w, neutras) -> float:
    """Que fraccion de la norma de w cae en el espacio de lo conservado.

    Es la norma de la proyeccion sobre la base ortonormal `neutras`, CON SIGNO:
    un vector de signos alternos y suma cero da 0, aunque su valor absoluto
    fuera paralelo a la suma. La version anterior tomaba `np.abs` del vector
    propio y, ademas, el maximo sobre las dos direcciones en vez de la norma de
    la proyeccion; con las dos cosas, una direccion ortogonal a lo conservado
    se descartaba como neutra y M-D podia publicar «estable» siendo inestable
    (grave 2 de la revision de 4c).
    """
    w = np.asarray(w, dtype=float)
    nw = float(np.linalg.norm(w))
    if nw == 0.0:
        return 0.0
    return float(np.linalg.norm(neutras @ (w / nw)))


def clasifica_valores_propios(Jac, I: int, J: int) -> dict:
    """Los valores propios del reducido, separando lo conservado de lo inestable.

    Un valor propio con parte real por debajo de TOL_NEUTRO veces el radio
    espectral no cuenta. Uno por encima es NEUTRO solo si su subespacio
    invariante cae en el de lo conservado:
      - valor propio real: su vector propio (la parte real o la imaginaria del
        que devuelve `eig`, la de mayor norma, porque `eig` puede devolverlo
        con una fase compleja);
      - par conjugado: el subespacio invariante es el plano {Re w, Im w}, y es
        neutro solo si LAS DOS partes estan alineadas con lo conservado. El par
        se cuenta una vez.
    Devuelve dict(inestables, mayores, radio, mayor_fuera_de_neutras). La
    ultima (D71) es la mayor parte real de los valores propios que no son
    neutros: ni nulos (|parte real| <= TOL_NEUTRO·radio, las dos sumas
    conservadas) ni positivos alineados con lo conservado. Es la cifra que
    dice cuan estable es la hora; `mayores` trae tambien los nulos.
    """
    vals, vecs = np.linalg.eig(np.asarray(Jac, dtype=float))
    radio = max(float(np.max(np.abs(vals))), 1e-300)
    tol = TOL_NEUTRO * radio
    neutras = direcciones_neutras(I, J)
    inestables = []
    fuera = [float(v.real) for v in vals if float(v.real) < -tol]
    for k in range(vals.size):
        re = float(vals[k].real)
        im = float(vals[k].imag)
        if re <= tol:
            continue
        w = vecs[:, k]
        if abs(im) > tol:
            if im < 0.0:
                continue                   # el conjugado ya se conto
            alin = min(alineacion(w.real, neutras), alineacion(w.imag, neutras))
        else:
            v = (w.real if np.linalg.norm(w.real) >= np.linalg.norm(w.imag)
                 else w.imag)
            alin = alineacion(v, neutras)
        if alin >= TOL_ALINEADO:
            continue
        inestables.append(dict(re=re, im=im, alineacion=alin))
        fuera.append(re)
    orden = np.argsort(-vals.real)
    return dict(inestables=inestables, radio=radio,
                mayores=[dict(re=float(vals[k].real), im=float(vals[k].imag))
                         for k in orden[:6]],
                mayor_fuera_de_neutras=(max(fuera) if fuera else None))


def analiza(spec, e0=None) -> dict:
    """Una hora de M-D. `e0`, opcional: la hora ya armada (del almacen, con
    `censo_fragiles.hora_del_almacen`), para no cargar las mediciones.

    D71. El punto que se analiza es la referencia «cerrada» de la hora, la del
    nucleo con las opciones de `spec["cerrada"]`: con las de produccion, en
    las horas fragiles es ya el reposo CUANTAL; con `cerrada=dict(mu_cuantal=
    0.0)`, la forma cerrada de antes. Si la hora es fragil se decide siempre
    con la forma cerrada (`mu_cuantal=0.0`), que es la definicion del censo
    de M-E: es una propiedad de la hora, no del punto. Y en una hora fragil
    del lado de los VENDEDORES la dinamica corre con el costo del vendedor en
    su piso (`b_vend = piso_j`, D68), el de la clave del despacho (D64): con
    el costo nivelado b_j el reposo del lado vendedor es otro, y esa es la
    pregunta de M-B (H-89), no la de la rama (sec. 8.2 del diseno)."""
    from censo_fragiles import fragilidad
    pre = PR.prepara(spec, e0=e0)
    if pre["sin_mercado"]:
        return dict(spec=spec, sin_mercado=True, avisos=pre["avisos"])
    e = pre["e"]
    cerrada = pre["referencias"]["cerrada"]
    # El residuo de admisibilidad del punto, en (kWh): la respuesta cuantal con
    # mu = 1 frente a su reparto (en el punto cuantal, cero). Y la fragilidad
    # de la hora, con la forma cerrada.
    opciones = dict(cerrada.get("opciones", {}))
    r = PR.resuelve(e, **opciones)
    fr = fragilidad(r, e["gn"], e["dn"], e["piso_j"], MU)
    r_cerr = PR.resuelve(e, **dict(opciones, mu_cuantal=0.0))
    fr_cerr = fragilidad(r_cerr, e["gn"], e["dn"], e["piso_j"], MU)
    costo_piso = bool(fr_cerr["fragil"] and fr_cerr["lado"] == "vendedores")
    b_vend = np.asarray(e["piso_j"], float) if costo_piso else None
    e_din = dict(e, b=b_vend) if costo_piso else e
    rhs, _X0, ix = A.construye(e, mu_ent=MU, precios0=pre["precios0"],
                               b_vend=b_vend)
    I, J = ix["I"], ix["J"]
    E = float(cerrada["E"])
    # El residuo en el estado de arranque de antes, solo para comparar.
    d0 = np.asarray(rhs(0.0, estado_en_el_reposo(
        e_din, cerrada, pre["precios0"], filtros="arranque")), float)
    # El estado de reposo, con los filtros en su valor de reposo (tarea 4e),
    # calculados con el mismo costo del vendedor que la dinamica.
    X = estado_en_el_reposo(e_din, cerrada, pre["precios0"], filtros="reposo")
    adm = filtros_de_reposo(e_din, cerrada)
    d = np.asarray(rhs(0.0, X), float)
    residuo_pi = float(np.max(np.abs(d[:I])))
    residuo_P = float(np.max(np.abs(d[ix["P"]])))
    suelo = suelo_del_recorte(X, ix, min(float(np.sum(e["gn"])),
                                         float(np.sum(e["dn"]))))
    Jac, _idx = jacobiano_reducido(rhs, X, ix)
    if not np.all(np.isfinite(Jac)):
        return dict(spec=spec, sin_mercado=False, error="jacobiano no finito",
                    residuo_pi=residuo_pi, residuo_P=residuo_P)
    c = clasifica_valores_propios(Jac, I, J)
    inestables = c["inestables"]
    return dict(spec=spec, sin_mercado=False,
                regimen=cerrada["regimen"],
                regimen_cerrado=cerrada.get("regimen_cerrado",
                                            cerrada["regimen"]),
                E=E, I=I, J=J, radio=c["radio"],
                residuo_pi=residuo_pi, residuo_P=residuo_P, suelo_P=suelo,
                residuo_P_arranque=float(np.max(np.abs(d0[ix["P"]]))),
                residuo_pi_arranque=float(np.max(np.abs(d0[:I]))),
                admisibilidad=dict(
                    cuantal_kwh=float(max(fr["dq"], fr["ds"])),
                    cuantal_rel=float(max(fr["dq"], fr["ds"]) / max(E, 1e-12)),
                    dispersion_compradores=adm["dispersion_compradores"],
                    dispersion_vendedores=adm["dispersion_vendedores"],
                    multiplicador_negativo=adm["negativo"],
                    gamma_sin_reposo=adm["gamma_sin_reposo"]),
                # D71: la fragilidad de la HORA (con la forma cerrada), de que
                # lado, cuanto se aparta y con que costo del vendedor corrio la
                # dinamica.
                fragil=bool(fr_cerr["fragil"]), lado_fragil=fr_cerr["lado"],
                apartamiento_cerrado=float(max(fr_cerr["dq"], fr_cerr["ds"])
                                           / max(fr_cerr["E"], 1e-12)),
                costo_vendedor="alternativa" if costo_piso else "lcoe",
                n_inestables=len(inestables), inestables=inestables[:10],
                mayores=c["mayores"],
                mayor_fuera_de_neutras=c["mayor_fuera_de_neutras"],
                quieta=bool(residuo_P <= 1e-3 * max(E, 1e-12) + suelo),
                estable=bool(not inestables),
                recorte_movio=bool(pre.get("recorte_movio", False)))


def specs(horas, por_regimen=10):
    fuera = []
    for grupo in GRUPOS:
        n = 0
        for caso in CASOS:
            for h in horas.get(caso, {}).get(grupo, []):
                fuera.append(dict(medicion=MEDICION, caso=caso,
                                  fecha=h["fecha"], grupo=grupo,
                                  etq="jacobiano en el reposo",
                                  nivel="sigma", piso_juego="marginal"))
                n += 1
                if n >= por_regimen:
                    break
            if n >= por_regimen:
                break
    return fuera


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horas", default="SALIDAS_SERVIDOR/validacion_reposo")
    ap.add_argument("--salida", required=True)
    ap.add_argument("--por-regimen", type=int, default=10)
    ap.add_argument("--mu-cuantal", dest="mu_cuantal", type=float,
                    default=None, metavar="MU",
                    help="D71: la mu de la rama cuantal del punto que se "
                         "analiza (spec cerrada=dict(mu_cuantal=MU)). Sin "
                         "ella, la de produccion: el reposo cuantal en las "
                         "horas fragiles. 0 analiza la forma cerrada de antes "
                         "en todas las horas, como la tarea 4e")
    ap.add_argument("--almacenes", default=None,
                    help="carpeta con un almacen por caso "
                         "(<carpeta>/<caso>/almacen): cada hora se arma de su "
                         "almacen en vez de cargar las mediciones del caso")
    args = ap.parse_args(argv)

    from corre_mediciones import carga_horas, limpia, banner_vacia
    horas = carga_horas(Path(args.horas).resolve())
    tareas = specs(horas, args.por_regimen)
    if args.mu_cuantal is not None:
        # D71: el punto que se analiza, con esa mu. Las specs de la medicion
        # no cambian: la opcion viaja en la referencia «cerrada».
        tareas = [dict(sp, cerrada=dict(sp.get("cerrada", {}),
                                        mu_cuantal=float(args.mu_cuantal)))
                  for sp in tareas]
    armadas = {}
    if args.almacenes:
        from censo_fragiles import horas_del_almacen
        for caso in sorted({sp["caso"] for sp in tareas}):
            fechas = [sp["fecha"] for sp in tareas if sp["caso"] == caso]
            alm = Path(args.almacenes).resolve() / caso / "almacen"
            for fecha, e0 in horas_del_almacen(alm, fechas).items():
                armadas[(caso, fecha)] = e0
    print(f"M-D: {QUE_DECIDE} - {len(tareas)} horas", flush=True)
    if not tareas:
        # Medio 1: una medicion planificada sin ninguna hora no es un exito.
        print(banner_vacia(MEDICION, Path(args.horas)), flush=True)
        return 3
    resultados = []
    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    for n, sp in enumerate(tareas):
        try:
            if args.almacenes and (sp["caso"], sp["fecha"]) not in armadas:
                raise KeyError(f"la hora {sp['fecha']} no esta en el almacen "
                               f"de {sp['caso']}")
            r = analiza(sp, e0=armadas.get((sp["caso"], sp["fecha"])))
        except Exception as exc:                            # noqa: BLE001
            print(f"  [{n}] FALLA {sp['caso']} {sp['fecha']}: "
                  f"{type(exc).__name__}: {exc}", flush=True)
            r = dict(spec=sp, error=f"{type(exc).__name__}: {exc}")
        resultados.append(r)
        salida.write_text(json.dumps(limpia(resultados)), encoding="utf-8")
        if r.get("sin_mercado") or r.get("error"):
            continue
        # D71: la hora «cuantal» dice su familia de precios; «FRAGIL» es de la
        # hora (con la forma cerrada), y el mayor Re fuera de las neutras es
        # el que dice cuan estable es el punto.
        fuera_n = r.get("mayor_fuera_de_neutras")
        print(f"  [{n}] {sp['caso']} {sp['fecha']} {r['regimen']:<20s} "
              + (f"(cerrado {r['regimen_cerrado']}) "
                 if r["regimen"] == "cuantal" else "")
              + f"I={r['I']} J={r['J']} residuo |dpi|={r['residuo_pi']:.2e} "
              f"|dP|={r['residuo_P']:.2e} (suelo {r['suelo_P']:.1e}; en el "
              f"arranque {r['residuo_P_arranque']:.2e}) admisibilidad "
              f"{r['admisibilidad']['cuantal_rel']:.1e}·E "
              f"{'FRAGIL ' if r['fragil'] else ''}"
              + (f"(lado {r['lado_fragil']}, {r['apartamiento_cerrado']:.3f}·E"
                 f", costo {r['costo_vendedor']}) " if r["fragil"] else "")
              + f"mayor Re={r['mayores'][0]['re']:.3e} "
              f"fuera de las neutras="
              + (f"{fuera_n:.3e} " if fuera_n is not None else "- ")
              + f"inestables={r['n_inestables']} "
              f"{'ESTABLE' if r['estable'] else 'NO ESTABLE'}", flush=True)
    utiles = [r for r in resultados if not r.get("sin_mercado")
              and not r.get("error")]
    # Medio 5: una hora cuyo recorte movio el reposo no cuenta; se dice.
    movidas = [r for r in utiles if r.get("recorte_movio")]
    utiles = [r for r in utiles if not r.get("recorte_movio")]
    # m2 de la re-revision: una hora que cae en dos grupos de la muestra se
    # analiza dos veces (el plan no se toca, para no desincronizarlo de la
    # noche ya lanzada); en el resumen cuenta una sola.
    vistas, unicas = set(), []
    for r in utiles:
        clave = (r["spec"]["caso"], r["spec"]["fecha"])
        if clave not in vistas:
            vistas.add(clave)
            unicas.append(r)
    if len(unicas) < len(utiles):
        print(f"  {len(utiles) - len(unicas)} horas repetidas (caen en dos "
              f"grupos) cuentan una sola vez", flush=True)
    utiles = unicas
    if movidas:
        print(f"  {len(movidas)} horas fuera del veredicto porque el recorte "
              f"movio su reposo:", flush=True)
        for r in movidas[:10]:
            print(f"    {r['spec']['caso']} {r['spec']['fecha']}", flush=True)
    porreg = {}
    for r in utiles:
        # Una hora cuenta para el veredicto solo si el punto ES de reposo
        # tambien para el sistema completo, es decir si el residuo, descontado
        # el suelo del recorte de P (tarea 4e), es pequeno frente al volumen
        # de la hora. Donde no lo es, el jacobiano describe otra cosa y se
        # cuenta aparte.
        quieta = r["residuo_P"] <= (1e-3 * max(r["E"], 1e-12)
                                    + r.get("suelo_P", 0.0))
        n, ok, fuera = porreg.get(r["regimen"], (0, 0, 0))
        porreg[r["regimen"]] = (n + 1, ok + (1 if (quieta and r["estable"])
                                            else 0),
                                fuera + (0 if quieta else 1))
    print("", flush=True)
    print("  ESTABILIDAD POR REGIMEN", flush=True)
    for reg, (n, ok, fuera) in sorted(porreg.items()):
        peor = max((x["residuo_P"] for x in utiles if x["regimen"] == reg),
                   default=0.0)
        quietas = n - fuera
        # Medio 8: con menos de PR.MIN_MUESTRA horas quietas no hay rotulo.
        if quietas < PR.MIN_MUESTRA:
            rotulo = f"muestra insuficiente (n = {quietas})"
        elif ok == quietas:
            rotulo = f"estable en todas (n = {quietas})"
        else:
            rotulo = f"NO estable en {quietas - ok} (n = {quietas})"
        print(f"    {reg:<22s} {ok}/{quietas} estables de las que estan "
              f"quietas ({fuera} con residuo grande, aparte) - peor residuo "
              f"|dP| = {peor:.2e} (kWh por unidad de tiempo) - {rotulo}",
              flush=True)
    # Tarea 4e: lo esperado es «estable salvo en las horas fragiles».
    no_estables = [x for x in utiles if not x["estable"]]
    fragiles = [x for x in utiles if x.get("fragil")]
    print(f"    {len(no_estables)} horas NO estables, {len(fragiles)} "
          f"fragiles (censo de M-E); NO estables que no son fragiles: "
          f"{sum(1 for x in no_estables if not x.get('fragil'))}; fragiles "
          f"estables: {sum(1 for x in fragiles if x['estable'])}", flush=True)
    for x in no_estables[:20]:
        print(f"      NO ESTABLE {x['spec']['caso']} {x['spec']['fecha']} "
              f"{x['regimen']} ({x['n_inestables']} inestables, mayor Re "
              f"{x['mayores'][0]['re']:.3e}) "
              f"{'FRAGIL' if x.get('fragil') else 'NO FRAGIL'}", flush=True)
    print("    El residuo se calcula con los filtros de los multiplicadores en "
          "su valor de reposo;", flush=True)
    print("    el de su arranque (0, 0 y 1), que era el de antes, queda en el "
          "JSON solo para comparar.", flush=True)
    print(f"  escrito {salida}", flush=True)
    if not utiles:
        print("  NINGUNA HORA SE PUDO JUZGAR: mira los FALLA y los sin mercado "
              "de arriba", flush=True)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
