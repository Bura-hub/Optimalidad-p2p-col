"""M-B reformulada: con que regla reparte la dinamica cuando sobran vendedores.

QUE DECIDE. D64: si el despacho entre vendedores va por el costo de su
alternativa (su piso, que es lo que dejan de cobrar por no venderle a la red) o
por su costo nivelado b_j, o si la dinamica no distingue y reparte por llenado.
Es la que decide si H-89 se cuenta con el costo de oportunidad o con el costo
de la energia.

COMO. Veinte horas de E4 y diez de E5 con compradores cortos y Cesmag entre los
vendedores (`selecciona_horas.py`, grupo `compradores_cortos_con_cesmag`), cada
una integrada dos veces: con el costo del vendedor en su piso
(`costo_vendedor="alternativa"`, que en el arnes es `b_vend="PISO"`) y con el
costo nivelado (`"lcoe"`, el b_j de los datos, que es el defecto). En cada
punto de control se mide la distancia al reposo de las TRES reglas de despacho
del nucleo: por piso (D64, la de produccion), por costo (el merito de D52) y
por llenado.

AQUI NO SE RECORTAN LOS VENDEDORES: lo que se mide es justamente a quien
despacha la dinamica, de modo que entran todos los que tienen excedente. Los
compradores con el techo bajo el piso del juego si salen, porque no pueden
comprar a ningun precio.

ACEPTACION: |dP_ji| <= 1e-3·E (kWh) para la regla que gane. Si gana la del piso,
D64 queda confirmada; si gana la del costo, hay que revisar si el multiplicador
de capacidad absorbe b_j; si gana el llenado, la dinamica no distingue y el
orden de merito es una decision del modelo, no un resultado.

COMO SE LEE. Cada costo del vendedor es una familia: el veredicto da, para
«costo alternativa» y para «costo lcoe» por separado, cuantas horas reproduce
cada una de las tres reglas (la columna `dP<=1e-3E`). Si la alternativa
reproduce la regla del piso y el costo nivelado la del costo, la dinamica
distingue las dos y D64 se decide por el costo que el modelo adopte. Antes de
la ronda de arreglos las dos familias se mezclaban en una sola cuenta y las
tres reglas salian en 0 % (critico 1 de la revision de 4c).

COSTO. Treinta horas por dos costos por dos aceleraciones son 120 corridas, de
1 a 10 (min) cada una, con tope de 3 600 (s).
"""
GRUPO = "compradores_cortos_con_cesmag"
CUANTAS = {"E4": 20, "E5": 10}
MU = 1.0
TOPE = 3600.0

MEDICION = "M-B"
QUE_DECIDE = "D64: el despacho entre vendedores va por piso, por costo o por llenado"

CORTES = {1000.0: [0, 2e-3, 5e-3, 1e-2, 2e-2, 4e-2, 8e-2, 0.16],
          100.0: [0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6]}
ACELERACIONES = (100.0, 1000.0)

# Las tres reglas del nucleo con que se compara el reparto entre vendedores.
REFERENCIAS = {"cerrada": dict(despacho_vendedores="piso"),
               "costo": dict(despacho_vendedores="costo"),
               "llenado": dict(despacho_vendedores="llenado")}

# Los dos costos del vendedor en la dinamica (D68): su alternativa o su costo
# nivelado. "PISO" lo resuelve `corre_mediciones.trabajo` con el piso de cada
# vendedor de esa hora.
COSTOS = {"alternativa": "PISO", "lcoe": "LCOE"}
# El rotulo de cada regla en el juicio ("cerrada" es la de produccion, D64).
NOMBRE_REGLA = {"cerrada": "piso (D64)", "costo": "costo (D52)",
                "llenado": "llenado"}
TOL_P_REL = 1e-3          # |dP_ji| <= 1e-3·E (kWh)
MIN_MUESTRA = 5           # el de preparacion.MIN_MUESTRA (medio 2)
UMBRAL = 0.95             # fraccion de las horas que discriminan (N1)
TEQ_JUICIO = (80.0, 160.0)


def specs(horas):
    fuera = []
    for caso, cuantas in CUANTAS.items():
        elegidas = horas.get(caso, {}).get(GRUPO, [])[:cuantas]
        for h in elegidas:
            for costo, b in COSTOS.items():
                for k in ACELERACIONES:
                    fuera.append(dict(
                        # Critico 1: cada costo es un MODELO distinto y se
                        # juzga aparte; sus dos aceleraciones, juntas.
                        medicion=MEDICION, familia=f"costo {costo}",
                        caso=caso, fecha=h["fecha"], grupo=GRUPO,
                        etq=f"costo {costo} k{k:g}",
                        var=dict(mu_ent=MU, k_lento=k, b_vend=b),
                        cortes=CORTES[k], tope=TOPE,
                        nivel="sigma", piso_juego="marginal",
                        recorta_vendedores=False,
                        referencias=REFERENCIAS))
    return fuera


def _dP(res, regla, teq):
    for f in res.get("filas", []):
        if abs(float(f["teq"]) - teq) < 1e-6:
            d = f["dist"].get(regla)
            return float(d["dP"]) if d else float("inf")
    return None


def reproduce(corridas, regla) -> object:
    """Si las corridas de una hora (una familia) reproducen esa regla.

    Se juzga con las que llegaron a teq 160: todas con max|dP_ji| <= 1e-3·E en
    teq 80 y 160. None si ninguna llego (la hora no se juzga)."""
    juzgadas = [c for c in corridas if _dP(c, regla, TEQ_JUICIO[-1]) is not None]
    if not juzgadas:
        return None
    E = max(float(juzgadas[0].get("E", 0.0)), 1e-12)
    return all(_dP(c, regla, t) is not None and _dP(c, regla, t) <= TOL_P_REL * E
               for c in juzgadas for t in TEQ_JUICIO)


def discrimina(corridas):
    """Si en esa hora la regla del piso y la del costo despachan distinto.

    Se lee de los repartos en forma cerrada que el JSON guarda para cada
    referencia (`cerrada["cerrada"]["P"]` y `cerrada["costo"]["P"]`): la hora
    discrimina si difieren en mas de 1e-3·E. Una hora que no discrimina no
    puede decidir D64, porque las dos reglas la reproducen a la vez (N1).
    None si el registro no trae las dos referencias.
    """
    for c in corridas:
        refs = c.get("cerrada") or {}
        pp = (refs.get("cerrada") or {}).get("P")
        pc = (refs.get("costo") or {}).get("P")
        if pp is None or pc is None:
            continue
        E = max(float(c.get("E", 0.0)), 1e-12)
        dif = max((abs(float(a) - float(b))
                   for fa, fb in zip(pp, pc) for a, b in zip(fa, fb)),
                  default=0.0)
        return dif > TOL_P_REL * E
    return None


def veredicto(resultados) -> str:
    """D64: que regla de despacho reproduce la dinamica con cada costo.

    N1 y N2 de la re-revision de 4c, sobre lo que el JSON ya guarda:
      - el denominador son TODAS las horas de la familia: una hora sin ninguna
        corrida en teq 160 cuenta como que no reproduce ninguna regla (N2);
      - D64 se decide sobre las horas que DISCRIMINAN (la regla del piso y la
        del costo a mas de 1e-3·E): una regla gana solo si reproduce el 95 % o
        mas de ellas, y hacen falta al menos cinco (N1). Antes ganaba la que
        mas horas tuviera, con cualquier fraccion (2 de 30 en el ejemplo de
        la re-revision);
      - se dice cuantas horas se apartaron (el recorte movio el reposo),
        cuantas no llegaron a teq 160 y cuantas discriminan.
    """
    horas, apartadas = {}, {}
    for res in resultados:
        sp = res.get("spec", {})
        if sp.get("medicion") != MEDICION:
            continue
        fam = sp.get("familia", sp.get("etq", ""))
        hora = (sp["caso"], sp["fecha"])
        if res.get("recorte_movio"):
            apartadas.setdefault(fam, set()).add(hora)
            continue
        horas.setdefault(fam, {}).setdefault(hora, []).append(res)
    lineas = ["", "  M-B - QUE REGLA REPRODUCE LA DINAMICA, POR COSTO DEL "
              "VENDEDOR (|dP_ji| <= 1e-3*E en teq 80 y 160)", ""]
    if not horas:
        return "\n".join(lineas + ["  ninguna corrida de M-B"])
    ganadoras = {}
    for fam in sorted(horas):
        from veredicto import es_falla
        hs = horas[fam]
        n = len(hs)
        # m-b de la re-revision 2: una hora cuyas corridas fallaron todas
        # sigue en el denominador, como «falla», igual que las que no llegan.
        fallidas = sum(1 for c in hs.values() if all(es_falla(x) for x in c))
        no_llegan = sum(1 for c in hs.values()
                        if reproduce(c, "cerrada") is None) - fallidas
        discr = [h for h, c in hs.items() if discrimina(c)]
        lineas.append(f"  {fam}: {n} horas; {len(apartadas.get(fam, ()))} "
                      f"apartadas (el recorte movio el reposo); {no_llegan} sin "
                      f"ninguna corrida en teq 160 y {fallidas} con todas sus "
                      f"corridas FALLIDAS (cuentan como que no reproducen); "
                      f"{len(discr)} discriminan entre el piso y el costo"
                      f"{' (de las fallidas no se sabe si discriminan: no '
                         'guardan su reposo cerrado)' if fallidas else ''}")
        lineas.append(f"    {'regla':<12s} {'todas':>12s} {'discriminan':>14s}")
        cuenta = {}
        for regla in REFERENCIAS:
            si_todas = sum(1 for c in hs.values() if reproduce(c, regla))
            si_discr = sum(1 for h in discr if reproduce(hs[h], regla))
            cuenta[regla] = si_discr
            pct = 100.0 * si_discr / len(discr) if discr else 0.0
            lineas.append(f"    {NOMBRE_REGLA[regla]:<12s} {si_todas:5d} de "
                          f"{n:<4d} {si_discr:5d} de {len(discr):<3d} "
                          f"({pct:3.0f} %)")
        # (la regla que gana o None, lo que se dice)
        if len(discr) < MIN_MUESTRA:
            ganadoras[fam] = (None, f"muestra insuficiente: solo {len(discr)} "
                                    f"horas discriminan (hacen falta "
                                    f"{MIN_MUESTRA})")
        else:
            llegan = [r for r, si in cuenta.items()
                      if si >= UMBRAL * len(discr)]
            if not llegan:
                ganadoras[fam] = (None, f"ninguna regla alcanza el "
                                        f"{100 * UMBRAL:.0f} % de las horas "
                                        f"que discriminan")
            elif len(llegan) > 1:
                ganadoras[fam] = (None, "empate entre " + " y ".join(
                    NOMBRE_REGLA[r] for r in llegan))
            else:
                ganadoras[fam] = (llegan[0],
                                  f"gana {NOMBRE_REGLA[llegan[0]]}")
        lineas.append("")
    for fam, (_r, texto) in sorted(ganadoras.items()):
        lineas.append(f"  con {fam}: {texto}")
    alt = ganadoras.get("costo alternativa", (None, ""))[0]
    lcoe = ganadoras.get("costo lcoe", (None, ""))[0]
    if alt == "cerrada" and lcoe == "costo":
        lineas.append("  => la dinamica DISTINGUE las dos reglas: con el costo "
                      "de la alternativa despacha por piso, y con el costo "
                      "nivelado por costo. D64 se decide por el costo que el "
                      "modelo adopte.")
    elif "llenado" in (alt, lcoe):
        lineas.append("  => la dinamica reparte por llenado con algun costo: el "
                      "orden de merito es una decision del modelo, no un "
                      "resultado.")
    elif alt is None or lcoe is None:
        lineas.append("  => D64 NO se puede decidir con esta medicion: ver "
                      "arriba por que.")
    return "\n".join(lineas)

