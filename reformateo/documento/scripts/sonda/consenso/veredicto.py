"""Lee los JSON de una medicion y dice que se publica como reposo verificado
y que como regla declarada.

    python -u reformateo/documento/scripts/sonda/consenso/veredicto.py \\
        SALIDAS_SERVIDOR/validacion_reposo/m_a_regimenes.json \\
        --salida SALIDAS_SERVIDOR/validacion_reposo/veredicto_m_a.txt

Acepta varios JSON (por ejemplo el de una corrida y el de su retomada).

LA CLAVE (critico 1 de la revision de 4c). Se cuenta por (regimen, referencia,
FAMILIA). La familia es el MODELO que se prueba, y la pone cada guion de
medicion: las dos aceleraciones de M-A son el mismo modelo y van juntas; los
dos costos del vendedor de M-B, las dos formas del jugador virtual de M-G o los
tres mu de M-E son modelos distintos y se cuentan aparte. M-C no se lee por la
tabla generica sino por su juicio propio: sus dos arranques de precios no son
el mismo modelo (H-90; re-revision 3). Antes se agrupaba por hora sin mirar
la variante, y en M-B las tres reglas salian en 0 % porque se exigia que un
mismo reparto casara con dos modelos que van a sitios distintos a proposito.

COMO SE CUENTA UNA HORA, dentro de su familia:
  - se juzga con las corridas que llegaron al punto de control de teq 160; las
    que se cortaron antes (por su tope) se publican como «cortadas», que es
    informacion, y no hunden la hora si otra corrida suya llego (critico 2);
  - una hora SIN NINGUNA corrida en teq 160 no sale de la cuenta: sigue en el
    denominador y cuenta como «no llega» (N2 de la re-revision). Antes salia, y
    con 10 horas, 5 dentro y 5 cortadas, el rotulo era «verificado (n = 5)»;
  - «80y160»: TODAS las juzgadas dentro de su tolerancia en teq 80 y 160 (la de
    cada corrida: estricta, floja o la que declara la medicion);
  - «alguna»: al menos una juzgada dentro;
  - «llegan»: todas las juzgadas cumplen el criterio de consenso;
  - «dP<=1e-3E»: todas las juzgadas con max|dP_ji| <= 1e-3·E en teq 160, que
    es la aceptacion de M-B.
Una hora cuyo recorte movio el reposo NO cuenta: se aparta y se dice (medio 5).
Una hora que fallo porque murio el trabajador del pool (tarea 4d) SI cuenta,
como «falla», con el criterio conservador de N2 y m-b; la columna «muerto»
dice cuantas de las «falla» son de la maquina y no del modelo.

EL ROTULO, sobre TODAS las horas del grupo. Con menos de cinco horas, «muestra
insuficiente»; si no, con el 95 % o mas dentro, «reposo verificado»; por
debajo, «regla declarada», con su porcentaje. Siempre con el n (medio 2). El
95 % lo fija la sec. 6 de
`.superpowers/sdd/2026-09-16-sonda-equilibrio/fable-report.md`.

LA MEDICION INCOMPLETA (N3). Encima de la tabla se dice si se hicieron todas
las corridas del plan. Los JSON nuevos traen `plan_total`; en los de la noche
lanzada antes del arreglo, el plan se deduce de los `horas_<caso>.json` (de
`--horas`, o de la carpeta del primer JSON) y del guion de la medicion. Si
falta alguna, sale «MEDICION INCOMPLETA: N de M» y el codigo de salida es 4.

EL JUICIO PROPIO. Si el JSON es de una sola medicion y su guion trae
`veredicto(resultados)`, se imprime despues de la tabla: M-B (que regla
reproduce cada costo), M-C (la multiplicidad dentro de cada arranque de
precios, los arranques sigma frente a la forma cerrada y la dependencia del
presupuesto), M-E (los tres mu entre si) y M-G (la tabla publicada). En las
cuatro la tabla generica no rotula.

Nada de esto decide por si mismo: deja la tabla con la que el autor rotula cada
regimen en la tesis.
"""
import importlib
import json
import math
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

UMBRAL = 0.95
MIN_MUESTRA = 5       # el mismo de preparacion.MIN_MUESTRA; aqui sin importar
                      # numpy ni el arnes, para que el veredicto sea ligero
TOL_P_REL = 1e-3      # |dP_ji| <= 1e-3·E (kWh), la aceptacion de M-B
TEQ_JUICIO = (80.0, 160.0)
# El de preparacion.TOL_DERIVADA: por debajo, el estado esta quieto (N5).
TOL_DERIVADA = 1e-3
# El codigo de una medicion INCOMPLETA: quedaron corridas del plan sin hacer
# (N3 de la re-revision de 4c). El mismo que devuelve corre_mediciones.py.
CODIGO_INCOMPLETA = 4

# El guion de cada medicion, para su juicio propio.
GUIONES = {"M-A": "medicion_regimenes", "M-B": "medicion_merito_vendedores",
           "M-C": "medicion_suma_no_cabe", "M-D": "medicion_estabilidad",
           "M-E": "medicion_mu", "M-G": "medicion_chacon"}
# Las mediciones cuyo criterio NO es la tabla generica. En M-G es la tabla
# publicada. En M-B es el reparto entre VENDEDORES (dP): con compradores cortos
# cada comprador recibe su deficit con las tres reglas, de modo que q y p
# coinciden en las tres y el rotulo generico diria «reposo verificado» tambien
# para la regla que pierde. En M-E es la comparacion de los tres mu entre si
# (N4): con dos horas por grupo, cada fila generica tiene n = 2 y diria
# «muestra insuficiente» sin que eso sea el resultado. En M-C, su juicio en
# tres partes (re-revision 3): la tabla generica juntaria los arranques
# «medio» con la forma cerrada de sigma, que no es su reposo (H-90), y
# rotularia «regla declarada» por construccion.
SIN_ROTULO_GENERICO = ("M-B", "M-C", "M-E", "M-G")


def es_falla(res) -> bool:
    """La corrida fallo al correr (su registro trae «FALLA ...» y ningun
    punto de control)."""
    return str(res.get("msg", "")).startswith("FALLA")


def es_muerto(res) -> bool:
    """La corrida fallo porque murio el trabajador del pool (tarea 4d): un
    fallo de la maquina, no del modelo. Sigue contando como «falla» en el
    denominador (N2 y m-b, criterio conservador); solo se dice cuantas son."""
    return es_falla(res) and (res.get("trabajador_muerto") is not None
                              or "trabajador muerto" in str(res.get("msg", "")))


def texto_muertas(k) -> str:
    """El inciso que dice cuantas de las fallidas son de la maquina."""
    return f" ({k} por trabajador muerto: fallo de la maquina)" if k else ""


def _prep():
    """`preparacion`, que se importa solo cuando hace falta: trae el arnes, y
    el arnes se situa en la raiz del repositorio al importarse (por eso
    `main` resuelve antes todas las rutas)."""
    import preparacion
    return preparacion


def tolerancia_de(res) -> tuple:
    """(tolerancia, fuente) de una corrida, RECALCULADA con la
    `preparacion.tolerancias` de hoy (NM2 de la re-revision 2 de 4c): la que la
    medicion declara, si la declara, o la de M-A por regimen y aceleracion. Si
    el registro no trae el regimen, la que se guardo al correr, y se dice."""
    sp = res.get("spec", {})
    reg = res.get("regimen")
    if reg:
        k = float(sp.get("var", {}).get("k_lento", 1.0))
        return (_prep().tolerancias(reg, k, declarada=sp.get("tolerancia")),
                "recalculada")
    guardada = res.get("tolerancia")
    if guardada:
        return guardada, "guardada (el registro no trae el regimen)"
    return None, "sin tolerancia: el registro no trae regimen ni tolerancia"


def teq_final_del_plan(res) -> float:
    """El tiempo equivalente al que la corrida DEBIA llegar: el ultimo de sus
    cortes por su aceleracion. En M-A, M-C y M-E es 160; en el brazo k = 1 de
    M-G, 40, por diseño."""
    sp = res.get("spec", {})
    cortes = sp.get("cortes")
    if not cortes:
        return TEQ_JUICIO[-1]
    k = float(sp.get("var", {}).get("k_lento", 1.0))
    return float(cortes[-1]) * k


def quietud(res, tolerancia=None) -> tuple:
    """(quieta, motivo) del estado final de una corrida.

    Esta QUIETA si se cumplen las dos cosas:
      - N5: en sus dos ultimos puntos de control las derivadas del reparto y
        de los precios, por unidad de tiempo equivalente, valen menos de 1e-3;
      - NM1 de la re-revision 2: entre dos puntos de control el estado no se
        movio mas que la tolerancia: |q(b) - q(a)| <= tol_q y
        |p(b) - p(a)| <= tol_p. El umbral de la derivada es absoluto y no
        escala con E: con dq/dt justo bajo 1e-3 el reparto todavia se mueve
        unos 0,08 (kWh) entre teq 80 y 160, cuarenta veces 1e-3·E. Sin esta
        segunda condicion, un transitorio lento se leia como reposo.

    LOS DOS PUNTOS son teq 80 y teq 160. Para una corrida cuyos cortes terminan
    antes de teq 160 POR DISEÑO (el brazo k = 1 de M-G, hasta teq 40), son sus
    dos ultimos puntos, teq 20 y 40 (re-revision 3 de 4c): sin esto ese brazo
    nunca se leia contra la tabla. Una corrida CORTADA por su tope antes de
    llegar al final de sus cortes no esta quieta, y una con cortes hasta 160 sin
    punto en teq 80 o en 160 tampoco: no hay con que comprobarlo.

    LA TOLERANCIA es la de la medicion recalculada (`tolerancia_de`), salvo que
    se de otra en `tolerancia`: un diccionario con `tol_p` y `tol_q_rel` (veces
    E) o `tol_q_abs` (kWh). M-G da la de su tabla (re-revision 3).

    POR MAGNITUDES (re-revision 4 de 4c, menor de M-G): si `tolerancia` trae
    `magnitudes`, un diccionario {magnitud: tolerancia absoluta} con las que
    lee la tabla de la medicion ("q", "p", "ppond", "parte"), la quietud se
    juzga SOLO con esas: el desplazamiento de cada una entre los dos puntos
    frente a su tolerancia, y la derivada del reparto solo si se lee "q", y la
    de los precios solo si se lee "p" o "ppond" (de la parte del vendedor no se
    guarda derivada: la cubre su desplazamiento). Asi el brazo de precio de
    M-G, cuya tabla lee `ppond` y `parte`, no se queda sin lectura porque su
    reparto todavia converja como 1/t con los precios ya quietos en el piso.
    Sin `magnitudes`, todo como antes: las dos derivadas, q y p.
    """
    magnitudes = (tolerancia or {}).get("magnitudes")
    filas = res.get("filas") or []
    if len(filas) < 2:
        return False, "sin puntos de control"
    if magnitudes is None:
        derivadas = ("dq_dt", "dp_dt")
    else:
        derivadas = tuple(
            d for d, lee in (("dq_dt", "q" in magnitudes),
                             ("dp_dt", "p" in magnitudes
                              or "ppond" in magnitudes)) if lee)
    if not all(float(f[d]) < TOL_DERIVADA for f in filas[-2:]
               for d in derivadas):
        return False, "todavia EN MOVIMIENTO (derivadas por encima de 1e-3)"
    fin = teq_final_del_plan(res)
    if fin < TEQ_JUICIO[-1] - 1e-6:
        # Termina antes de teq 160 por diseño: sus dos ultimos puntos, si llego
        # al final de sus cortes.
        if res.get("cortada") or abs(float(filas[-1]["teq"]) - fin) > 1e-6:
            return False, (f"cortada antes del final de sus cortes (teq {fin:g}): "
                           f"no se puede comprobar")
        fa, fb = filas[-2], filas[-1]
    else:
        fa, fb = punto(res, 80.0), punto(res, 160.0)
        if fa is None or fb is None:
            return False, "sin puntos en teq 80 y 160: no se puede comprobar"
    ta, tb = float(fa["teq"]), float(fb["teq"])
    if magnitudes is not None:
        return _quietud_por_magnitudes(fa, fb, ta, tb, magnitudes)
    if tolerancia is None:
        tolerancia, _fuente = tolerancia_de(res)
    if tolerancia is None:
        return False, "sin tolerancia con que comprobarlo"
    if tolerancia.get("tol_q_abs") is not None:
        tol_q = float(tolerancia["tol_q_abs"])
    else:
        tol_q = (float(tolerancia["tol_q_rel"])
                 * max(float(res.get("E", 0.0)), 1e-12))
    dq = max((abs(float(a) - float(b)) for a, b in zip(fb["q"], fa["q"])),
             default=0.0)
    dp = max((abs(float(a) - float(b)) for a, b in zip(fb["p"], fa["p"])),
             default=0.0)
    if dq > tol_q or dp > float(tolerancia["tol_p"]):
        return False, (f"todavia EN MOVIMIENTO entre teq {ta:g} y {tb:g} "
                       f"(|dq| = {dq:.2e} (kWh), |dp| = {dp:.2e} (COP/kWh))")
    return True, f"QUIETO (entre teq {ta:g} y {tb:g})"


# Las unidades de las magnitudes que leen las tablas, para los motivos.
UNIDADES = {"q": "(kWh)", "p": "(COP/kWh)", "ppond": "(COP/kWh)",
            "parte": "(fraccion)"}


def _desplazamiento(fa, fb, magnitud) -> float:
    """max |fb[m] - fa[m]| de una magnitud escalar o por comprador. Un NaN en
    los dos puntos (la parte del vendedor sin excedente) no es movimiento; en
    uno solo, si (infinito). Formas distintas, tambien infinito."""
    a, b = fa[magnitud], fb[magnitud]
    a = [float(x) for x in (a if isinstance(a, (list, tuple)) else [a])]
    b = [float(x) for x in (b if isinstance(b, (list, tuple)) else [b])]
    if len(a) != len(b):
        return math.inf
    peor = 0.0
    for x, y in zip(a, b):
        if math.isnan(x) and math.isnan(y):
            continue
        d = abs(y - x)
        peor = max(peor, math.inf if math.isnan(d) else d)
    return peor


def _quietud_por_magnitudes(fa, fb, ta, tb, magnitudes) -> tuple:
    """El desplazamiento entre los dos puntos de cada magnitud que lee la
    tabla, frente a su tolerancia (ver `quietud`)."""
    faltan = [m for m in magnitudes if m not in fa or m not in fb]
    if faltan:
        return False, (f"sin {', '.join(faltan)} en los puntos de control: no "
                       f"se puede comprobar")
    difs = {m: _desplazamiento(fa, fb, m) for m in magnitudes}
    texto = ", ".join(f"|d{m}| = {d:.2e} {UNIDADES.get(m, '')}".rstrip()
                      for m, d in difs.items())
    if any(d > float(magnitudes[m]) for m, d in difs.items()):
        return False, (f"todavia EN MOVIMIENTO entre teq {ta:g} y {tb:g} "
                       f"({texto})")
    return True, (f"QUIETO (entre teq {ta:g} y {tb:g}, en lo que lee su tabla: "
                  f"{', '.join(magnitudes)})")


def esta_quieta(res, tolerancia=None) -> bool:
    """Si el estado final esta quieto (ver `quietud`)."""
    return quietud(res, tolerancia)[0]


def _hora(res) -> tuple:
    sp = res["spec"]
    return (sp["caso"], sp["fecha"])


def familia(res) -> str:
    sp = res["spec"]
    return str(sp.get("familia", sp.get("etq", "")))


def regimen_de_seleccion(spec, horas) -> str:
    """El regimen de una hora segun los ficheros de seleccion, que lo guardan
    comprobado contra el almacen. Es lo unico que dice el regimen de una hora
    cuyas corridas fallaron todas (m-b), porque una corrida fallida no llega a
    calcularlo. '?' si no esta."""
    if not horas:
        return "?"
    por_grupo = horas.get(spec.get("caso"), {})
    candidatos = ([por_grupo.get(spec.get("grupo"), [])]
                  + list(por_grupo.values()))
    for lista in candidatos:
        for h in lista or []:
            if h.get("fecha") == spec.get("fecha") and h.get("regimen"):
                return str(h["regimen"])
    return "?"


def agrupa(resultados, horas=None) -> tuple:
    """({(regimen, referencia, familia): {hora: [corridas]}}, [apartadas]).

    m-b de la re-revision 2: una corrida FALLIDA tambien entra, con el regimen
    de su hora segun la seleccion (`regimen_de_seleccion`) y las referencias
    de su especificacion. Asi, una hora cuyas corridas fallaron todas sigue en
    el denominador, como «falla», en vez de desaparecer.
    """
    fuera, apartadas = {}, []
    for res in resultados:
        if res.get("recorte_movio"):
            apartadas.append(res)
            continue
        if res.get("veredicto"):
            reg = res.get("regimen", "?")
            nombres = list(res["veredicto"])
        elif es_falla(res):
            sp = res.get("spec", {})
            reg = regimen_de_seleccion(sp, horas)
            nombres = list(sp.get("referencias") or {}) or ["cerrada"]
        else:
            continue                    # sin mercado: se lista aparte
        for nombre in nombres:
            fuera.setdefault((reg, nombre, familia(res)), {}).setdefault(
                _hora(res), []).append(res)
    return fuera, apartadas


def punto(res, teq):
    """La fila del punto de control de ese tiempo equivalente, o None."""
    for f in res.get("filas", []):
        if abs(float(f["teq"]) - teq) < 1e-6:
            return f
    return None


def rejuzga(res, nombre) -> dict:
    """Los indicadores de una corrida frente a una referencia, RECALCULADOS.

    NM2 de la re-revision 2: `dentro` en teq 80 y 160 y el criterio de
    consenso se recalculan desde lo que el JSON guarda (`filas[*].dist`,
    `dq_dt`, `dp_dt`) con la `preparacion.tolerancias`, `dentro` y
    `criterio_consenso` de HOY, de modo que un cambio en ellas se recoge al
    releer la noche. Si falta algun dato para recalcular, se usan los
    indicadores guardados al correr y `fuente` lo dice.
    """
    guardado = (res.get("veredicto") or {}).get(nombre)
    filas = res.get("filas") or []
    tol, fuente_tol = tolerancia_de(res)
    motivo = None
    if not filas:
        motivo = "sin puntos de control"
    elif tol is None or fuente_tol != "recalculada":
        motivo = fuente_tol
    elif any(nombre not in (f.get("dist") or {}) for f in filas):
        motivo = f"falta la distancia a '{nombre}' en algun punto"
    if motivo is None:
        PR = _prep()
        E = float(res.get("E", 0.0))
        t80 = PR.en_teq(filas, nombre, E, tol, 80.0)
        t160 = PR.en_teq(filas, nombre, E, tol, 160.0)
        return dict(hay160=bool(t160["hay"]),
                    dentro80=bool(t80["dentro"]),
                    dentro160=bool(t160["dentro"]),
                    llega=bool(PR.criterio_consenso(filas, nombre, E, tol)
                               ["llega"]),
                    clase=str(tol.get("clase", "?")), fuente="recalculado")
    if guardado:
        return dict(hay160=bool(guardado["teq160"]["hay"]),
                    dentro80=bool(guardado["teq80"]["dentro"]),
                    dentro160=bool(guardado["teq160"]["dentro"]),
                    llega=bool(guardado["consenso"]["llega"]),
                    clase=str((res.get("tolerancia") or {}).get("clase", "?")),
                    fuente=f"guardado ({motivo})")
    return dict(hay160=False, dentro80=False, dentro160=False, llega=False,
                clase="?", fuente=f"nada ({motivo})")


def juzgable(res, nombre) -> bool:
    """Una corrida se juzga si llego al punto de control de teq 160."""
    return (not es_falla(res)) and rejuzga(res, nombre)["hay160"]


def cuenta_hora(corridas, nombre) -> dict:
    """Lo que una hora aporta a su fila del veredicto, dentro de su familia.

    Los indicadores se recalculan (`rejuzga`, NM2). Una hora cuyas corridas
    fallaron todas sale con `falla=True` y cuenta en el denominador (m-b).
    """
    if corridas and all(es_falla(c) for c in corridas):
        # Tarea 4d: si todas fallaron porque murio su trabajador, la hora es
        # «falla» de la maquina; cuenta igual, pero la tabla lo dice aparte.
        return dict(juzgada=False, falla=True, cortadas=0, guardados=0,
                    muerto=all(es_muerto(c) for c in corridas))
    vivas = [c for c in corridas if not es_falla(c)]
    juicios = [(c, rejuzga(c, nombre)) for c in vivas]
    juzgadas = [(c, j) for c, j in juicios if j["hay160"]]
    cortadas = len(vivas) - len(juzgadas)
    guardados = sum(1 for _c, j in juicios if j["fuente"] != "recalculado")
    if not juzgadas:
        return dict(juzgada=False, falla=False, cortadas=cortadas,
                    guardados=guardados)
    ok = [j["dentro80"] and j["dentro160"] for _c, j in juzgadas]
    E = max(float(juzgadas[0][0].get("E", 0.0)), 1e-12)
    dP = []
    peor_dq = peor_dp = 0.0
    for c, _j in juzgadas:
        for teq in TEQ_JUICIO:
            f = punto(c, teq)
            if f is None:
                continue
            d = f["dist"].get(nombre, {})
            peor_dq = max(peor_dq, float(d.get("dq", float("inf"))))
            peor_dp = max(peor_dp, float(d.get("dp", float("inf"))))
        f160 = punto(c, TEQ_JUICIO[-1])
        dP.append(float(f160["dist"].get(nombre, {}).get("dP", float("inf")))
                  if f160 is not None else float("inf"))
    clases = sorted({j["clase"] for _c, j in juzgadas})
    return dict(juzgada=True, falla=False, cortadas=cortadas,
                guardados=guardados, dentro=all(ok), alguna=any(ok),
                llega=all(j["llega"] for _c, j in juzgadas),
                con_dP=all(x <= TOL_P_REL * E for x in dP),
                peor_dq=peor_dq, peor_dp=peor_dp, clases=clases)


def rotulo(dentro: int, n: int) -> str:
    if n < MIN_MUESTRA:
        return f"muestra insuficiente (n = {n})"
    frac = dentro / n
    if frac >= UMBRAL:
        return f"reposo verificado (n = {n})"
    return f"regla declarada ({100 * frac:.0f} %, n = {n})"


def tabla(resultados, rotular=True, horas=None) -> str:
    grupos, apartadas = agrupa(resultados, horas)
    lineas = ["", "  VEREDICTO POR REGIMEN, REFERENCIA Y FAMILIA", ""]
    if apartadas:
        lineas.append(f"  {len(apartadas)} corridas APARTADAS porque el recorte "
                      f"movio el reposo de su hora (no cuentan):")
        for r in apartadas[:10]:
            lineas.append(f"    {r['spec']['caso']} {r['spec']['fecha']} "
                          f"{r['spec']['etq']}")
        lineas.append("")
    if not grupos:
        return "\n".join(lineas + ["  (ninguna corrida con veredicto: mira los "
                                   "mensajes de arriba)"])
    lineas.append(f"  {'regimen':<19s} {'referencia':<11s} {'familia':<22s} "
                  f"{'horas':>5s} {'juzg':>4s} {'nolleg':>6s} {'falla':>5s} "
                  f"{'muerto':>6s} "
                  f"{'cort':>4s} {'llegan':>6s} {'80y160':>6s} {'alguna':>6s} "
                  f"{'dP<=1e-3E':>9s} {'peor dq':>9s} {'peor dp':>8s} "
                  f"tolerancia  rotulo")
    total_guardados = 0
    for (reg, nombre, fam), horas_g in sorted(grupos.items()):
        cuentas = [cuenta_hora(c, nombre) for c in horas_g.values()]
        juzg = [c for c in cuentas if c["juzgada"]]
        # N2: el denominador son TODAS las horas del grupo. Una hora sin
        # ninguna corrida en teq 160 cuenta como «no llega», y una cuyas
        # corridas fallaron todas, como «falla» (m-b); ninguna sale de la
        # cuenta.
        n = len(horas_g)
        fallas = sum(1 for c in cuentas if c["falla"])
        muertas = sum(1 for c in cuentas if c["falla"] and c.get("muerto"))
        no_llegan = n - len(juzg) - fallas
        cortadas = sum(c["cortadas"] for c in cuentas)
        total_guardados += sum(c["guardados"] for c in cuentas)
        dentro = sum(c["dentro"] for c in juzg)
        alguna = sum(c["alguna"] for c in juzg)
        llegan = sum(c["llega"] for c in juzg)
        con_dP = sum(c["con_dP"] for c in juzg)
        peor_dq = max((c["peor_dq"] for c in juzg), default=float("nan"))
        peor_dp = max((c["peor_dp"] for c in juzg), default=float("nan"))
        clases = ",".join(sorted({k for c in juzg for k in c["clases"]})) or "-"
        rot = rotulo(dentro, n) if rotular else "(ver el juicio propio)"
        lineas.append(f"  {reg:<19s} {nombre:<11s} {fam:<22s} {n:5d} "
                      f"{len(juzg):4d} {no_llegan:6d} {fallas:5d} "
                      f"{muertas:6d} "
                      f"{cortadas:4d} {llegan:6d} {dentro:6d} {alguna:6d} "
                      f"{con_dP:9d} {peor_dq:9.2e} {peor_dp:8.2e} "
                      f"{clases:<11s} {rot}")
    lineas += ["",
               "  horas = horas del grupo, que son el DENOMINADOR del rotulo; "
               "juzg = las que tienen alguna corrida en teq 160; nolleg = las "
               "que no, y cuentan como «no llega»; falla = las que fallaron en "
               "todas sus corridas, y cuentan igual; muerto = de las falla, "
               "las que fallaron porque murio el trabajador del pool (fallo de "
               "la maquina, no del modelo; siguen en el denominador); "
               "cort = corridas que no "
               "llegaron a teq 160 (cortadas por su tope, o con cortes que "
               "terminan antes, como el brazo k = 1 de M-G)",
               "  llegan = todas las juzgadas cumplen el criterio de consenso "
               "(dos puntos seguidos dentro y derivadas bajo 1e-3)",
               "  80y160 = todas las juzgadas dentro de su tolerancia en teq 80 "
               "y 160; alguna = al menos una",
               "  dP<=1e-3E = todas las juzgadas con max|dP_ji| <= 1e-3*E en "
               "teq 160 (la aceptacion de M-B)",
               "  peor dq y peor dp: en kWh y COP/kWh, en los puntos de juicio "
               "(teq 80 y 160)",
               "  llegan, 80y160 y alguna se RECALCULAN al releer, con la "
               "tolerancia y el criterio de consenso de hoy (NM2)"]
    if total_guardados:
        lineas.append(f"  AVISO: en {total_guardados} juicios de corrida no se "
                      f"pudo recalcular (falta un dato) y se uso el indicador "
                      f"guardado al correr")
    lineas.append("")
    return "\n".join(lineas)


def medicion_de(resultados):
    """El rotulo de la medicion si todas las corridas son de la misma."""
    m = {r.get("spec", {}).get("medicion") for r in resultados}
    m.discard(None)
    return m.pop() if len(m) == 1 else None


def clave_corrida(spec) -> tuple:
    """Una corrida del plan: el grupo, la hora y la variante. Con el grupo,
    una misma hora que cae en dos grupos (m2) cuenta dos veces, como en el
    plan."""
    return (str(spec.get("grupo", "")), str(spec.get("caso", "")),
            str(spec.get("fecha", "")), str(spec.get("etq", "")))


def plan_de(resultados, horas_dir=None) -> dict:
    """N3: cuantas corridas tenia el plan y cuantas se hicieron.

    Los JSON de aqui en adelante traen `plan_total` y `plan_indice` en cada
    registro. Los de la noche lanzada antes de este arreglo no: para ellos el
    plan se DEDUCE de los ficheros de seleccion (`horas_<caso>.json`) y de las
    especificaciones del guion de la medicion, que son deterministas. Si se
    cambian los ficheros de seleccion o el guion despues de la noche, la
    deduccion deja de valer: por eso se dice de donde sale la cifra.

    Devuelve dict(total, hechas, fuente), con total None si no se pudo saber.
    """
    con_plan = [r for r in resultados if "plan_total" in r]
    if con_plan:
        total = max(int(r["plan_total"]) for r in con_plan)
        hechas = len({int(r["plan_indice"]) for r in con_plan})
        return dict(total=total, hechas=hechas,
                    fuente="plan_total guardado en el JSON")
    med = medicion_de(resultados)
    hechas_claves = {clave_corrida(r.get("spec", {})) for r in resultados}
    if med not in GUIONES or horas_dir is None:
        return dict(total=None, hechas=len(hechas_claves),
                    fuente="sin plan: el JSON no lo trae y no hay de donde "
                           "deducirlo")
    from corre_mediciones import carga_horas
    mod = importlib.import_module(GUIONES[med])
    if not callable(getattr(mod, "specs", None)):
        return dict(total=None, hechas=len(hechas_claves),
                    fuente=f"sin plan: {GUIONES[med]} no trae specs()")
    horas = carga_horas(Path(horas_dir))
    plan = {clave_corrida(sp) for sp in mod.specs(horas)}
    return dict(total=len(plan), hechas=len(hechas_claves & plan),
                fuente=f"deducido de {GUIONES[med]}.specs() y de los "
                       f"horas_<caso>.json de {horas_dir}")


def aviso_plan(resultados, horas_dir=None) -> tuple:
    """(texto, incompleta) del estado del plan, para encima de la tabla."""
    p = plan_de(resultados, horas_dir)
    if p["total"] is None:
        return (f"  AVISO: no se sabe si la medicion esta completa ({p['fuente']})",
                False)
    if p["hechas"] < p["total"]:
        raya = "=" * 70
        return (f"\n  {raya}\n  MEDICION INCOMPLETA: {p['hechas']} de "
                f"{p['total']} corridas del plan\n  ({p['fuente']}).\n  Lo que "
                f"sigue se lee sobre lo que se hizo; las horas que faltan no "
                f"estan\n  en ningun denominador.\n  {raya}", True)
    return (f"  plan completo: {p['hechas']} de {p['total']} corridas "
            f"({p['fuente']})", False)


def resume(resultados, horas_dir=None) -> str:
    med = medicion_de(resultados)
    texto_plan, _inc = aviso_plan(resultados, horas_dir)
    horas = None
    if horas_dir is not None:
        from corre_mediciones import carga_horas
        horas = carga_horas(Path(horas_dir))
    partes = [texto_plan,
              tabla(resultados, rotular=med not in SIN_ROTULO_GENERICO,
                    horas=horas)]
    if med in GUIONES:
        mod = importlib.import_module(GUIONES[med])
        juicio = getattr(mod, "veredicto", None)
        if callable(juicio):
            partes.append(juicio(resultados))
    return "\n".join(partes)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    # `--salida <fichero>` deja el mismo texto escrito, ademas de imprimirlo:
    # el registro del lanzador queda en modelo_base/logs y la entrega quiere el
    # veredicto dentro de SALIDAS_SERVIDOR.
    salida = None
    if "--salida" in argv:
        k = argv.index("--salida")
        if k + 1 >= len(argv):
            print("  --salida necesita un fichero")
            return 2
        salida = Path(argv[k + 1]).resolve()
        del argv[k:k + 2]
    # `--horas <carpeta>`: donde estan los horas_<caso>.json con que se deduce
    # el plan de un JSON que no lo guarda (N3). Por defecto, la carpeta del
    # primer JSON, que en la noche es la misma.
    horas_dir = None
    if "--horas" in argv:
        k = argv.index("--horas")
        if k + 1 >= len(argv):
            print("  --horas necesita una carpeta")
            return 2
        horas_dir = Path(argv[k + 1]).resolve()
        del argv[k:k + 2]
    if horas_dir is None and argv:
        horas_dir = Path(argv[0]).resolve().parent
    # Todas las rutas ya estan resueltas: al recalcular (NM2) se importa
    # `preparacion`, que trae el arnes, y el arnes se situa en la raiz del
    # repositorio; una ruta relativa dejaria de apuntar a su fichero.
    lineas = []

    def escribe(texto=""):
        lineas.append(str(texto))
        print(texto)

    resultados = []
    for f in argv:
        p = Path(f).resolve()
        if not p.is_file():
            print(f"  no esta: {p}")
            return 2
        resultados.extend(json.loads(p.read_text(encoding="utf-8")))
    fallas = [r for r in resultados if str(r.get("msg", "")).startswith("FALLA")]
    cortadas = [r for r in resultados if r.get("cortada")]
    sin_mercado = [r for r in resultados if r.get("msg") == "sin mercado"]
    med = medicion_de(resultados)
    escribe(f"  {med or 'medicion mixta o sin rotulo'}: {len(resultados)} "
            f"corridas leidas de {len(argv)} fichero(s)")
    if sin_mercado:
        escribe(f"  {len(sin_mercado)} sobre horas sin mercado, que no entran "
                f"en el veredicto:")
        for r in sin_mercado[:10]:
            escribe(f"    {r['spec']['caso']} {r['spec']['fecha']}: "
                    f"{'; '.join(r.get('avisos', []))}")
    if fallas:
        muertas = sum(1 for r in fallas if es_muerto(r))
        escribe(f"  {len(fallas)} con FALLA{texto_muertas(muertas)}:")
        for r in fallas[:10]:
            escribe(f"    {r['spec']['caso']} {r['spec']['fecha']} "
                    f"{r['spec']['etq']}: {r['msg']}")
    if cortadas:
        escribe(f"  {len(cortadas)} CORTADAS antes del ultimo punto de control "
                f"(se publican; una hora sin ninguna corrida en teq 160 cuenta "
                f"como «no llega»):")
        for r in cortadas[:20]:
            escribe(f"    {r['spec']['caso']} {r['spec']['fecha']} "
                    f"{r['spec']['etq']}: llego a teq "
                    f"{r.get('teq_alcanzado', 0):g} con {r.get('nfev', 0)} "
                    f"evaluaciones ({r['msg']})")
    _texto, incompleta = aviso_plan(resultados, horas_dir)
    escribe(resume(resultados, horas_dir))
    juzgables = [r for r in resultados if r.get("veredicto")]
    if salida is not None:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        print(f"  escrito {salida}")
    if not juzgables:
        # Un veredicto sin ninguna corrida juzgable no es un veredicto.
        print("  NINGUNA CORRIDA TIENE VEREDICTO: no hay nada que rotular")
        return 3
    if incompleta:
        # N3: el veredicto se escribio, pero sobre una medicion a la que le
        # faltan corridas; el lanzador lo anota como «incompleta».
        return CODIGO_INCOMPLETA
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
