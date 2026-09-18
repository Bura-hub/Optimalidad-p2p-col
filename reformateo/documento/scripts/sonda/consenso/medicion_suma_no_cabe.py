"""M-C: la regla del regimen «la suma no cabe sobre el piso», con cuatro arranques.

QUE DECIDE. D53: si la regla de saturacion por aptitud (paso 5 del nucleo) es
EL reposo de ese regimen o solo una regla declarada. Es el unico regimen cuya
regla se derivo sin un reposo interior que la respalde, y ademas es el que
reparte energia de forma desigual: el vendedor sirve primero a los techos altos
y a los demas no les queda.

COMO. Las horas de ese regimen de los almacenes de E0 (unas veintiocho) y de
CV2 (unas treinta y siete), cada una integrada desde CUATRO arranques
distintos: la oferta repartida a partes iguales (como JoinFinal.m) o en
proporcion al lado corto (el arranque factible, D45), cruzados con los precios
en el presupuesto sigma (D50) o en el punto medio de la banda. Si los cuatro
terminan en el mismo sitio, el reposo no depende de por donde se entre.

POR QUE LAS DOS: veintiocho horas son una muestra pobre para decidir el rotulo
de un regimen que pesa el 14 % de la energia. CV2 es el mismo mercado con el
componente de comercializar por dos: el comercializador descuenta el doble
sobre lo permutado, de modo que el piso de quien esta en permuta BAJA y la
banda se ensancha, y sus horas de este regimen son un contraste y no una
repeticion. El arnes las carga desde que `paso_a_paso.carga` acepta
`factor_cv` (D7), que en el piso hace lo mismo que `main_simulation.py
--factor-cv 2` (en produccion el factor entra ademas en la liquidacion de los
escenarios, que el mercado de la hora no ve; ver el docstring de la carga).

LA TOLERANCIA ES LA DECLARADA, no la que el corredor deduce de k (medio 3 de
la revision de 4c): 1e-3·E en reparto y 0,5 (COP/kWh) en precio, en las cuatro
corridas. Si con ella alguna hora no valida, eso es un resultado.

LOS DOS ARRANQUES DE PRECIOS NO SON EL MISMO MODELO (grave de la re-revision 3
de 4c; decision del controlador). La dinamica CONSERVA la suma de los precios,
y esa suma la fija el arranque (H-90): con precios en el punto medio la suma es
otra que con el presupuesto sigma, y el reposo al que se llega es otro. Que
«medio» y «sigma» acaben en sitios distintos no es multiplicidad: es la
dependencia del presupuesto, ya conocida. Antes se comparaban los cuatro
arranques como un mismo modelo, y una hora interior sintetica con los cuatro
quietos (sigma en 727,81 x 3, igual que la forma cerrada; medio en 707,81 x 3)
salia «SITIOS DISTINTOS, D53 DECLARADA».

EL JUICIO, en tres partes (`veredicto(resultados)`):

  1. MULTIPLICIDAD, solo DENTRO de cada arranque de precios: sus dos ofertas
     (iguales frente a factible), sobre el estado final de las que llegaron
     quietas a teq 160 (`entre_arranques`). Si discrepan, la hora tiene varios
     reposos y se suma la energia afectada. SOLO esto puede hacer que D53 salga
     declarada por multiplicidad. El resultado se da por arranque de precios
     (sigma y medio por separado), y la hora cuenta en el «MISMO sitio» solo si
     se comparo EL PAR SIGMA (re-revision 4 de 4c, medio): el par sigma es la
     prueba de unicidad de la regla, y una hora con una oferta sigma cortada,
     fallida o todavia en movimiento no puede sumar como «MISMO sitio» por el
     par medio, que es otro modelo.
  2. LOS ARRANQUES SIGMA FRENTE A LA FORMA CERRADA: si la regla del paso 5 es
     el reposo al que llega la dinamica. La hora cuenta «dentro» solo si LAS
     DOS ofertas sigma llegaron a teq 160 y estan dentro en teq 80 y 160
     (re-revision 4): si una se corto, la hora es «no llega», y si una fallo,
     «falla», aunque la otra este dentro; esas horas con una sola oferta sigma
     en teq 160 se cuentan aparte. El denominador son TODAS las horas, con las
     que no llegan y las que fallaron dentro (N2 y m-b). Con el 95 % o mas
     dentro (y cinco horas como minimo), la regla es el reposo verificado; si
     no, regla declarada.
  3. «MEDIO» FRENTE A SIGMA, solo informativo: la dependencia del presupuesto
     (H-90), con la diferencia de la suma de los precios y cuantas horas cambian
     de regimen, es decir cambian el conjunto de compradores sin energia (como
     la 2120 del consenso, que con precios medios pasaba a «cabe» y repartia por
     llenado). No cuenta contra D53.

La tabla generica de `veredicto.py` NO rotula M-C: los arranques «medio» se
compararian con la forma cerrada de sigma, que no es su reposo, y el rotulo
seria «regla declarada» por construccion.

COSTO. Este regimen es de los baratos: en la hora 2120 de E0 la dinamica llegaba
a la esquina hacia t = 20 con unas 64 000 evaluaciones (sec. 3 del informe del
consenso). Con k = 100 hasta teq 160 es del orden de un minuto por corrida;
sesenta y cinco horas por cuatro arranques son 260 corridas.
"""
import numpy as np

GRUPO = "suma_no_cabe"
# Cuantas horas de cada caso, con el reparto que pide el plan de medicion.
CUANTAS = {"E0": 28, "CV2": 37}
MU = 1.0
TOPE = 1800.0

MEDICION = "M-C"
QUE_DECIDE = "D53: la regla de saturacion es el reposo, o es regla declarada"

CORTES = [0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6]     # teq 0 a 160 con k = 100
K = 100.0
TEQ_FINAL = 160.0

# Los cuatro arranques: oferta x precios. Comparten la familia solo como
# etiqueta de la noche: los dos arranques de precios NO son el mismo modelo
# (conservan sumas de precios distintas, H-90), y la multiplicidad se juzga
# solo entre las dos ofertas de cada uno (ver el docstring).
ARRANQUES = (("iguales", "sigma"), ("factible", "sigma"),
             ("iguales", "medio"), ("factible", "medio"))
FAMILIA = "V3a cuatro arranques"
# Las dos ofertas de cada arranque de precios: el PAR que prueba la unicidad.
OFERTAS = tuple(dict.fromkeys(oferta for oferta, _nivel in ARRANQUES))
# Los dos arranques de precios, en el orden en que se informan.
NIVELES = tuple(dict.fromkeys(nivel for _oferta, nivel in ARRANQUES))

# La tolerancia que el plan fija para M-C (medio 3).
TOLERANCIA = dict(tol_q_rel=1e-3, tol_p=0.5, clase="declarada M-C",
                  motivo="la del plan para M-C: 1e-3*E y 0,5 (COP/kWh)")


def specs(horas):
    fuera = []
    for caso, cuantas in CUANTAS.items():
        for h in horas.get(caso, {}).get(GRUPO, [])[:cuantas]:
            for oferta, nivel in ARRANQUES:
                fuera.append(dict(
                    medicion=MEDICION, familia=FAMILIA,
                    caso=caso, fecha=h["fecha"], grupo=GRUPO,
                    etq=f"oferta {oferta} + precios {nivel}",
                    var=dict(mu_ent=MU, k_lento=K, arranque=oferta),
                    cortes=CORTES, tope=TOPE, tolerancia=TOLERANCIA,
                    nivel=nivel, piso_juego="marginal"))
    return fuera


def entre_arranques(corridas, tol=TOLERANCIA) -> dict:
    """Unas corridas de UNA hora comparadas entre si, sobre su estado final.

    El juicio la llama con las dos ofertas de UN arranque de precios (ver el
    docstring del modulo): comparar arranques de precios distintos no mide
    multiplicidad, sino la dependencia del presupuesto.

    Solo entran las que LLEGARON: a teq 160 y con el estado final QUIETO
    (`veredicto.esta_quieta`; N5 y NM1). Una corrida cortada antes, o que en
    teq 160 todavia se mueve, no dice donde se queda: compararla con las demas
    haria pasar una convergencia lenta por multiplicidad. Devuelve cuantas se
    compararon y de que ofertas (`ofertas`), cuantas no llegaron (y por que),
    la mayor diferencia de reparto y de precio entre dos de las que llegaron, y
    si hay multiplicidad.
    """
    from veredicto import esta_quieta
    en_160 = [c for c in corridas
              if c.get("filas") and not c.get("cortada")
              and abs(float(c["filas"][-1]["teq"]) - TEQ_FINAL) < 1e-6]
    llegaron = [c for c in en_160 if esta_quieta(c)]
    E = max(float(corridas[0].get("E", 0.0)), 1e-12) if corridas else 1e-12
    dq = dp = 0.0
    for a in range(len(llegaron)):
        for b in range(a + 1, len(llegaron)):
            fa, fb = llegaron[a]["filas"][-1], llegaron[b]["filas"][-1]
            dq = max(dq, float(np.max(np.abs(np.asarray(fa["q"], float)
                                             - np.asarray(fb["q"], float)))))
            dp = max(dp, float(np.max(np.abs(np.asarray(fa["p"], float)
                                             - np.asarray(fb["p"], float)))))
    multiple = bool(len(llegaron) >= 2
                    and (dq > tol["tol_q_rel"] * E or dp > tol["tol_p"]))
    return dict(comparados=len(llegaron),
                ofertas=frozenset(oferta_de(c) for c in llegaron),
                cortados=len(corridas) - len(en_160),
                moviendose=len(en_160) - len(llegaron),
                dq=dq, dp=dp, E=E, multiple=multiple)


def nivel_de(res) -> str:
    """El arranque de precios de una corrida ("sigma" o "medio")."""
    return str(res.get("spec", {}).get("nivel", "sigma"))


def oferta_de(res) -> str:
    """El arranque de la oferta de una corrida ("iguales" o "factible"); el
    del nucleo, "iguales", si el registro no lo trae."""
    return str(res.get("spec", {}).get("var", {}).get("arranque", "iguales"))


def par_de(corridas) -> dict:
    """Parte 1: el PAR de ofertas de un arranque de precios en una hora.

    `estado`: «distinto» si las que llegaron quietas discrepan (multiplicidad);
    «mismo» si llegaron quietas LAS DOS ofertas (`OFERTAS`) y coinciden; si
    no, «incompleto», el par no se comparo. Con el juicio de `entre_arranques`
    sobre las vivas, cuantas fallaron y que ofertas faltan en el registro."""
    from veredicto import es_falla
    vivas = [c for c in corridas if not es_falla(c)]
    j = entre_arranques(vivas)
    if j["multiple"]:
        estado = "distinto"
    elif set(OFERTAS) <= j["ofertas"]:
        estado = "mismo"
    else:
        estado = "incompleto"
    return dict(estado=estado, juicio=j, fallan=len(corridas) - len(vivas),
                faltan=sorted(set(OFERTAS) - {oferta_de(c) for c in corridas}))


def _llego(res) -> bool:
    """A teq 160 y quieta: la condicion de `entre_arranques`, para una sola."""
    from veredicto import esta_quieta
    return bool(res.get("filas") and not res.get("cortada")
                and abs(float(res["filas"][-1]["teq"]) - TEQ_FINAL) < 1e-6
                and esta_quieta(res))


def sin_energia(res, tol=TOLERANCIA) -> frozenset:
    """Los compradores que acaban sin energia (q <= 1e-3·E): el que cambie
    este conjunto entre dos arranques es que la hora cambio de regimen."""
    E = max(float(res.get("E", 0.0)), 1e-12)
    q = res["filas"][-1]["q"]
    return frozenset(i for i, x in enumerate(q)
                     if float(x) <= tol["tol_q_rel"] * E)


def contra_la_forma_cerrada(corridas) -> dict:
    """Parte 2: las DOS ofertas sigma de una hora frente a la regla del paso 5.

    Cada oferta de `OFERTAS` se juzga con sus corridas sigma y los indicadores
    RECALCULADOS (NM2): «juzgada» si alguna llego a teq 160, con `dentro`
    (dentro en teq 80 y 160) y `llega` (el criterio de consenso); «no llega»
    si ninguna llego; «falla» si fallaron todas; «falta» si no hay ninguna en
    el registro.

    La hora (re-revision 4 de 4c, medio): «juzgada» solo si LAS DOS ofertas lo
    estan, con `dentro` y `llega` si lo estan las dos. Si no, «falla» si alguna
    oferta fallo y «no llega» en otro caso: una hora con una sola oferta en
    teq 160 NO se da por verificada, porque el par es la prueba de unicidad.
    `una_sola` dice si llego una sola oferta a teq 160, y `una_sola_dentro` si
    esa estaba dentro (se informan aparte).
    """
    from veredicto import es_falla, rejuzga
    por_oferta = {}
    for c in corridas:
        if nivel_de(c) == "sigma":
            por_oferta.setdefault(oferta_de(c), []).append(c)
    ofertas = {}
    for of in OFERTAS:
        cs = por_oferta.get(of, [])
        vivas = [c for c in cs if not es_falla(c)]
        juzgados = [j for j in (rejuzga(c, "cerrada") for c in vivas)
                    if j["hay160"]]
        if juzgados:
            ofertas[of] = dict(
                estado="juzgada",
                dentro=all(j["dentro80"] and j["dentro160"] for j in juzgados),
                llega=all(j["llega"] for j in juzgados))
        elif vivas:
            ofertas[of] = dict(estado="no llega")
        elif cs:
            ofertas[of] = dict(estado="falla")
        else:
            ofertas[of] = dict(estado="falta")
    juzgadas = [o for o in ofertas.values() if o["estado"] == "juzgada"]
    fuera = dict(ofertas=ofertas, una_sola=len(juzgadas) == 1,
                 una_sola_dentro=(len(juzgadas) == 1 and juzgadas[0]["dentro"]))
    if len(juzgadas) == len(OFERTAS):
        fuera.update(estado="juzgada",
                     dentro=all(o["dentro"] for o in juzgadas),
                     llega=all(o["llega"] for o in juzgadas))
    elif any(o["estado"] == "falla" for o in ofertas.values()):
        fuera.update(estado="falla")
    else:
        fuera.update(estado="no llega")
    return fuera


def dependencia_presupuesto(corridas) -> dict:
    """Parte 3: «medio» frente a sigma, sobre las corridas que llegaron.

    Devuelve la diferencia de la suma de los precios (medio menos sigma) y si
    cambia el conjunto de compradores sin energia (cambio de regimen). None si
    no llego ninguna corrida de alguno de los dos arranques."""
    sig = [c for c in corridas if nivel_de(c) == "sigma" and _llego(c)]
    med = [c for c in corridas if nivel_de(c) == "medio" and _llego(c)]
    if not sig or not med:
        return None
    s, m = sig[0], med[0]
    suma = (float(np.sum(m["filas"][-1]["p"]))
            - float(np.sum(s["filas"][-1]["p"])))
    return dict(dif_suma=suma, cambia=sin_energia(m) != sin_energia(s),
                E=max(float(s.get("E", 0.0)), 1e-12))


def veredicto(resultados) -> str:
    """D53 en tres partes: multiplicidad dentro de cada arranque de precios,
    los arranques sigma frente a la forma cerrada, y «medio» frente a sigma
    como dependencia del presupuesto (ver el docstring del modulo)."""
    from veredicto import es_falla, es_muerto, rotulo, texto_muertas
    horas = {}
    for res in resultados:
        sp = res.get("spec", {})
        if sp.get("medicion") != MEDICION:
            continue
        if res.get("recorte_movio"):
            continue
        if not res.get("filas") and not es_falla(res):
            continue                        # sin mercado: no es de la muestra
        horas.setdefault((sp["caso"], sp["fecha"]), []).append(res)
    lineas = ["", "  M-C - LA REGLA DE «LA SUMA NO CABE» (D53)", ""]
    if not horas:
        return "\n".join(lineas + ["  ninguna hora con corridas utiles"])
    n = len(horas)
    fallidas = [h for h, c in horas.items() if all(es_falla(x) for x in c)]
    # Tarea 4d: de las fallidas, cuantas por trabajador muerto (la maquina).
    fallidas_muertas = sum(1 for h in fallidas
                           if all(es_muerto(x) for x in horas[h]))

    # ── 1. multiplicidad, dentro de cada arranque de precios ──────────────
    # Re-revision 4 (medio): el resultado se da por arranque de precios, y la
    # hora cuenta en el MISMO sitio solo si se comparo el par sigma.
    E_total = E_multiple = 0.0
    multiples, sin_comparar, igual = [], [], []
    por_arranque = {nv: dict(mismo=0, distinto=0, incompleto=0)
                    for nv in NIVELES}
    for (caso, fecha), corridas in sorted(horas.items()):
        por_nivel = {nv: [] for nv in NIVELES}
        for c in corridas:
            por_nivel.setdefault(nivel_de(c), []).append(c)
        pares = {nv: par_de(cs) for nv, cs in por_nivel.items()}
        for nv, par in pares.items():
            por_arranque.setdefault(nv, dict(mismo=0, distinto=0,
                                             incompleto=0))[par["estado"]] += 1
        if (caso, fecha) in fallidas:
            continue
        vivas = [c for c in corridas if not es_falla(c)]
        E_total += max(float(vivas[0].get("E", 0.0)), 0.0)
        distintos = {nv: par["juicio"] for nv, par in pares.items()
                     if par["estado"] == "distinto"}
        if distintos:
            E_multiple += max(r["E"] for r in distintos.values())
            multiples.append((caso, fecha, distintos))
        elif pares["sigma"]["estado"] == "mismo":
            igual.append((caso, fecha))
        else:
            sin_comparar.append((caso, fecha, pares))
    solo_medio = [h for h in sin_comparar
                  if h[2].get("medio", {}).get("estado") == "mismo"]
    lineas.append("  1. MULTIPLICIDAD, dentro de cada arranque de precios (las "
                  "dos ofertas, iguales frente a factible):")
    lineas.append(f"     {n} horas: {len(igual)} con el par sigma en el MISMO "
                  f"sitio; {len(multiples)} en SITIOS DISTINTOS (varios "
                  f"reposos) en algun arranque de precios; {len(sin_comparar)} "
                  f"SIN EL PAR SIGMA COMPARADO (alguna de sus dos ofertas sigma "
                  f"no llego quieta a teq 160, fallo o no se corrio); "
                  f"{len(fallidas)} FALLARON en todas sus corridas"
                  f"{texto_muertas(fallidas_muertas)}")
    lineas.append(f"     por arranque de precios (cada linea cuenta las {n} "
                  f"horas):")
    for nv, cuenta in por_arranque.items():
        lineas.append(f"       precios {nv}: {cuenta['mismo']} con el par en el "
                      f"MISMO sitio, {cuenta['distinto']} en SITIOS DISTINTOS y "
                      f"{cuenta['incompleto']} sin el par comparado")
    if solo_medio:
        lineas.append(f"     {len(solo_medio)} horas sin el par sigma comparado "
                      f"tienen el par medio en el mismo sitio: NO cuentan como "
                      f"MISMO sitio (el par medio es otro modelo, H-90)")
    frac = E_multiple / E_total if E_total > 0 else 0.0
    lineas.append(f"     energia afectada por la multiplicidad: "
                  f"{E_multiple:.4f} de {E_total:.4f} (kWh) de la muestra = "
                  f"{100 * frac:.2f} %")
    for caso, fecha, rs in multiples[:20]:
        for nv, r in sorted(rs.items()):
            lineas.append(f"       VARIOS REPOSOS {caso} {fecha} (precios {nv}): "
                          f"max|dq| = {r['dq']:.3e} (kWh, E = {r['E']:.4f}), "
                          f"max|dp| = {r['dp']:.3f} (COP/kWh)")
    for caso, fecha, pares in sin_comparar[:10]:
        detalle = "; ".join(
            f"{nv}: {par['juicio']['comparados']} quietas en teq 160, "
            f"{par['juicio']['cortados']} cortadas, "
            f"{par['juicio']['moviendose']} en movimiento y {par['fallan']} "
            f"fallidas" + (f", falta {' y '.join(par['faltan'])}"
                           if par["faltan"] else "")
            for nv, par in pares.items())
        lineas.append(f"       sin el par sigma {caso} {fecha} ({detalle})")
    for caso, fecha in fallidas[:10]:
        lineas.append(f"       fallaron {caso} {fecha}: su energia no entra en "
                      f"la cuenta")

    # ── 2. las dos ofertas sigma frente a la forma cerrada ─────────────────
    # Re-revision 4 (medio): la hora cuenta dentro solo con LAS DOS ofertas.
    estados = {h: contra_la_forma_cerrada(c) for h, c in horas.items()}
    juzgadas = [e for e in estados.values() if e["estado"] == "juzgada"]
    dentro = sum(1 for e in juzgadas if e["dentro"])
    llegan = sum(1 for e in juzgadas if e["llega"])
    no_llegan = sum(1 for e in estados.values() if e["estado"] == "no llega")
    fallan = sum(1 for e in estados.values() if e["estado"] == "falla")
    # Tarea 4d: las «falla» cuyas ofertas sigma fallidas murieron todas por el
    # trabajador (la maquina, no el modelo).
    fallan_muertas = sum(
        1 for h, e in estados.items() if e["estado"] == "falla"
        and all(es_muerto(c) for c in horas[h]
                if nivel_de(c) == "sigma" and es_falla(c)))
    una_sola = [h for h, e in sorted(estados.items()) if e["una_sola"]]
    una_dentro = sum(1 for h in una_sola if estados[h]["una_sola_dentro"])
    rot = rotulo(dentro, n)
    lineas += ["", "  2. LOS ARRANQUES SIGMA FRENTE A LA FORMA CERRADA (la regla "
                   "del paso 5):",
               f"     {n} horas (el denominador): {dentro} dentro en teq 80 y "
               f"160 con LAS DOS ofertas sigma, {llegan} que cumplen el criterio "
               f"de consenso, {no_llegan} que no llegan a teq 160 y {fallan} que "
               f"fallaron{texto_muertas(fallan_muertas)} (basta con que no "
               f"llegue o falle una de las dos ofertas sigma) -> {rot}",
               f"     {len(una_sola)} horas con UNA SOLA oferta sigma en teq 160 "
               f"(la otra cortada, fallida o sin correr): cuentan como \"no "
               f"llega\" o \"falla\", no como dentro; {una_dentro} de ellas con "
               f"esa oferta dentro"]
    for caso, fecha in una_sola[:10]:
        of = estados[(caso, fecha)]["ofertas"]
        detalle = ", ".join(f"{o}: {x['estado']}" for o, x in of.items())
        lineas.append(f"       una sola oferta sigma {caso} {fecha} ({detalle})")

    # ── 3. «medio» frente a sigma: dependencia del presupuesto ────────────
    deps = [(h, dependencia_presupuesto(c)) for h, c in sorted(horas.items())]
    deps = [(h, d) for h, d in deps if d is not None]
    lineas += ["", "  3. «MEDIO» FRENTE A SIGMA: DEPENDENCIA DEL PRESUPUESTO "
                   "(H-90), informativa, no cuenta contra D53:"]
    if deps:
        difs = [d["dif_suma"] for _h, d in deps]
        cambian = [h for h, d in deps if d["cambia"]]
        lineas.append(f"     {len(deps)} horas con los dos arranques quietos: la "
                      f"suma de los precios cambia en {np.mean(difs):+.2f} "
                      f"(COP/kWh) de media (de {min(difs):+.2f} a "
                      f"{max(difs):+.2f}); {len(cambian)} horas CAMBIAN DE "
                      f"REGIMEN (cambia el conjunto de compradores sin energia)")
        for caso, fecha in cambian[:10]:
            lineas.append(f"       cambia de regimen {caso} {fecha}")
    else:
        lineas.append("     ninguna hora con los dos arranques quietos")

    # ── la conclusion ──────────────────────────────────────────────────────
    if multiples:
        lineas.append("  => D53: la regla del paso 5 se publica como DECLARADA "
                      "por multiplicidad, con esa energia afectada")
    elif rot.startswith("reposo verificado"):
        lineas.append("  => D53: la regla del paso 5 es el reposo al que llega la "
                      "dinamica (reposo verificado)")
    else:
        # Re-revision final de 4c (menor 1): si ninguna hora juzgada queda
        # fuera, el rotulo cae por las que no llegan o fallan, y eso es «no se
        # pudo verificar», no «la dinamica va a otro sitio».
        fuera = len(juzgadas) - dentro
        if fuera == 0:
            motivo = (f"no se pudo verificar: {no_llegan} horas no llegan y "
                      f"{fallan} fallan, y ninguna juzgada queda fuera")
        else:
            motivo = (f"la dinamica con sigma no la alcanza en {fuera} horas "
                      f"juzgadas; ademas {no_llegan} no llegan y {fallan} "
                      f"fallan")
        lineas.append(f"  => D53: la regla del paso 5 se publica como DECLARADA: "
                      f"{motivo} ({rot})")
    return "\n".join(lineas)
