"""Lee los JSON de una medicion y dice que se publica como reposo verificado
y que como regla declarada.

    python -u reformateo/documento/scripts/sonda/consenso/veredicto.py \\
        SALIDAS_SERVIDOR/validacion_reposo/m_a_regimenes.json \\
        --salida SALIDAS_SERVIDOR/validacion_reposo/veredicto_m_a.txt

Acepta varios JSON (por ejemplo el de una corrida y el de su retomada).

LA CLAVE (critico 1 de la revision de 4c). Se cuenta por (regimen, referencia,
FAMILIA). La familia es el MODELO que se prueba, y la pone cada guion de
medicion: las dos aceleraciones de M-A, o los cuatro arranques de M-C, son el
mismo modelo y van juntos; los dos costos del vendedor de M-B, las dos formas
del jugador virtual de M-G o los tres mu de M-E son modelos distintos y se
cuentan aparte. Antes se agrupaba por hora sin mirar la variante, y en M-B las
tres reglas salian en 0 % porque se exigia que un mismo reparto casara con dos
modelos que van a sitios distintos a proposito.

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
reproduce cada costo), M-C (los cuatro arranques entre si y la energia
afectada) y M-G (la tabla publicada; en M-G la tabla generica no rotula).

Nada de esto decide por si mismo: deja la tabla con la que el autor rotula cada
regimen en la tesis.
"""
import importlib
import json
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
# «muestra insuficiente» sin que eso sea el resultado.
SIN_ROTULO_GENERICO = ("M-B", "M-E", "M-G")


def esta_quieta(res, tol=TOL_DERIVADA) -> bool:
    """N5: el estado final de una corrida esta QUIETO si en sus dos ultimos
    puntos de control las derivadas del reparto y de los precios, por unidad
    de tiempo equivalente, valen menos de `tol`. Es la parte del criterio de
    consenso que no mira la forma cerrada, y se lee de lo que el JSON guarda
    (`dq_dt`, `dp_dt`). Sin dos puntos, no se sabe: False."""
    filas = res.get("filas") or []
    if len(filas) < 2:
        return False
    return all(float(f["dq_dt"]) < tol and float(f["dp_dt"]) < tol
               for f in filas[-2:])


def _hora(res) -> tuple:
    sp = res["spec"]
    return (sp["caso"], sp["fecha"])


def familia(res) -> str:
    sp = res["spec"]
    return str(sp.get("familia", sp.get("etq", "")))


def agrupa(resultados) -> tuple:
    """({(regimen, referencia, familia): {hora: [corridas]}}, [apartadas])."""
    fuera, apartadas = {}, []
    for res in resultados:
        if not res.get("veredicto"):
            continue
        if res.get("recorte_movio"):
            apartadas.append(res)
            continue
        reg = res.get("regimen", "?")
        for nombre in res["veredicto"]:
            fuera.setdefault((reg, nombre, familia(res)), {}).setdefault(
                _hora(res), []).append(res)
    return fuera, apartadas


def punto(res, teq):
    """La fila del punto de control de ese tiempo equivalente, o None."""
    for f in res.get("filas", []):
        if abs(float(f["teq"]) - teq) < 1e-6:
            return f
    return None


def juzgable(res, nombre) -> bool:
    """Una corrida se juzga si llego al punto de control de teq 160."""
    return bool(res["veredicto"][nombre]["teq160"]["hay"])


def cuenta_hora(corridas, nombre) -> dict:
    """Lo que una hora aporta a su fila del veredicto, dentro de su familia."""
    juzgadas = [c for c in corridas if juzgable(c, nombre)]
    cortadas = len(corridas) - len(juzgadas)
    if not juzgadas:
        return dict(juzgada=False, cortadas=cortadas)
    v = [c["veredicto"][nombre] for c in juzgadas]
    ok = [x["teq80"]["dentro"] and x["teq160"]["dentro"] for x in v]
    E = max(float(juzgadas[0].get("E", 0.0)), 1e-12)
    dP = []
    peor_dq = peor_dp = 0.0
    for c in juzgadas:
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
    clases = sorted({str(c.get("tolerancia", {}).get("clase", "?"))
                     for c in juzgadas})
    return dict(juzgada=True, cortadas=cortadas, dentro=all(ok),
                alguna=any(ok), llega=all(x["consenso"]["llega"] for x in v),
                con_dP=all(x <= TOL_P_REL * E for x in dP),
                peor_dq=peor_dq, peor_dp=peor_dp, clases=clases)


def rotulo(dentro: int, n: int) -> str:
    if n < MIN_MUESTRA:
        return f"muestra insuficiente (n = {n})"
    frac = dentro / n
    if frac >= UMBRAL:
        return f"reposo verificado (n = {n})"
    return f"regla declarada ({100 * frac:.0f} %, n = {n})"


def tabla(resultados, rotular=True) -> str:
    grupos, apartadas = agrupa(resultados)
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
                  f"{'horas':>5s} {'juzg':>4s} {'nolleg':>6s} {'cort':>4s} "
                  f"{'llegan':>6s} {'80y160':>6s} {'alguna':>6s} "
                  f"{'dP<=1e-3E':>9s} {'peor dq':>9s} {'peor dp':>8s} "
                  f"tolerancia  rotulo")
    for (reg, nombre, fam), horas in sorted(grupos.items()):
        cuentas = [cuenta_hora(c, nombre) for c in horas.values()]
        juzg = [c for c in cuentas if c["juzgada"]]
        # N2: el denominador son TODAS las horas del grupo. Una hora sin
        # ninguna corrida en teq 160 cuenta como «no llega», no sale de la
        # cuenta.
        n = len(horas)
        no_llegan = n - len(juzg)
        cortadas = sum(c["cortadas"] for c in cuentas)
        dentro = sum(c["dentro"] for c in juzg)
        alguna = sum(c["alguna"] for c in juzg)
        llegan = sum(c["llega"] for c in juzg)
        con_dP = sum(c["con_dP"] for c in juzg)
        peor_dq = max((c["peor_dq"] for c in juzg), default=float("nan"))
        peor_dp = max((c["peor_dp"] for c in juzg), default=float("nan"))
        clases = ",".join(sorted({k for c in juzg for k in c["clases"]})) or "-"
        rot = rotulo(dentro, n) if rotular else "(ver el juicio propio)"
        lineas.append(f"  {reg:<19s} {nombre:<11s} {fam:<22s} {n:5d} "
                      f"{len(juzg):4d} {no_llegan:6d} {cortadas:4d} "
                      f"{llegan:6d} {dentro:6d} {alguna:6d} {con_dP:9d} "
                      f"{peor_dq:9.2e} {peor_dp:8.2e} {clases:<11s} {rot}")
    lineas += ["",
               "  horas = horas del grupo, que son el DENOMINADOR del rotulo; "
               "juzg = las que tienen alguna corrida en teq 160; nolleg = las "
               "que no, y cuentan como «no llega»; cort = corridas que no "
               "llegaron a teq 160 (cortadas por su tope, o con cortes que "
               "terminan antes, como el brazo k = 1 de M-G)",
               "  llegan = todas las juzgadas cumplen el criterio de consenso "
               "(dos puntos seguidos dentro y derivadas bajo 1e-3)",
               "  80y160 = todas las juzgadas dentro de su tolerancia en teq 80 "
               "y 160; alguna = al menos una",
               "  dP<=1e-3E = todas las juzgadas con max|dP_ji| <= 1e-3*E en "
               "teq 160 (la aceptacion de M-B)",
               "  peor dq y peor dp: en kWh y COP/kWh, en los puntos de juicio "
               "(teq 80 y 160)", ""]
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
    partes = [texto_plan,
              tabla(resultados, rotular=med not in SIN_ROTULO_GENERICO)]
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
        salida = Path(argv[k + 1])
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
        horas_dir = Path(argv[k + 1])
        del argv[k:k + 2]
    if horas_dir is None and argv:
        horas_dir = Path(argv[0]).resolve().parent
    lineas = []

    def escribe(texto=""):
        lineas.append(str(texto))
        print(texto)

    resultados = []
    for f in argv:
        p = Path(f)
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
        escribe(f"  {len(fallas)} con FALLA:")
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
