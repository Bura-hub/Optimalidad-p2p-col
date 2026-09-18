"""M-G: el caso publicado de Chacon, con la dinamica regularizada.

QUE DECIDE. Es la tabla con que se presenta H-87 y H-88 a los asesores y al
arbitro: que da el modelo del articulo, con su propia ecuacion, en sus dos
horas publicadas, y en que se parece o no a sus Tablas II y IV. De aqui sale la
frase honesta de la comparacion con el articulo base.

COMO, dos formas del jugador virtual, las dos con la exploracion entropica del
vendedor (mu = 1), y las dos EN LA CONFIGURACION DEL CODIGO DE LA AUTORA: la
competencia `matlab` (la linea activa de JoinFinal.m:189) y el arranque de la
oferta a partes iguales. Es la configuracion con que la sonda del consenso
corrio este caso (`scratchpad/consenso/s6_chacon.py`) y con la que H-88
reproduce sus tablas «al centesimo». Con los defectos del arnes (`aggregate` y
`factible`) un resultado distinto no se podria leer: no se sabria si viene del
reposo o de la configuracion. El reposo de la barrera no depende de la forma
de la competencia (D60), de modo que ese brazo no pierde nada.

  - «barrera + V3a», que es la forma de esta traduccion (el jugador virtual
    lleva el peso de barrera). Prediccion derivada, que es lo que hay que
    confirmar o desmentir: 22:00 con precios 833,3 (COP/kWh) en tres
    compradores y 1 250 en dos, reparto [0,3037 x 3; 0,262; 0,208] (kWh) y
    parte del vendedor 0,758. El nucleo ya la reproduce en
    `tests/test_reposo_mercado.py::test_chacon_22_con_el_algoritmo_3`; lo que
    falta es que la DINAMICA llegue ahi.
  - «precio + V3a» (V1+ent), que es la forma del fichero original: el jugador
    virtual entra con su propio precio. Hay dos predicciones y la medicion dice
    cual se cumple (ver «LAS DOS LECTURAS DEL BRAZO DE PRECIO», abajo).

LA PARTE DEL VENDEDOR A LAS 22:00 SE CITA 0,758, LA DEL NUCLEO (decision del
controlador, 2026-09-18). El plan (sec. 11) escribio 0,77, pero esa cifra es
el valor TRANSITORIO que la sonda del consenso leyo a t = 0,3 (0,772), con los
precios todavia en camino (947,6 x 3; 1 037; 1 120), no el reposo. En el
reposo, con 833,3 x 3 y 1 250 x 2, la parte es 0,758, y
`tests/test_reposo_mercado.py` la fija. **No se vuelve a poner 0,77 en la
aceptacion.**

LAS DOS LECTURAS DEL BRAZO DE PRECIO, escritas antes de medir para que el
resultado se pueda interpretar sin volver a preguntar:

  (a) Se cumple la del plan: nivel ponderado 225 +- 1 (COP/kWh) y parte
      0,098 +- 0,002 EN EL REPOSO. Es el costo del vendedor: en este caso
      b = 225,20 (COP/kWh) esta por encima del piso (114), la ec. 16 muerde y
      el precio medio cubre justo ese costo; la parte es
      (b - piso)/(techo - piso) = 0,098. Es lo que H-88 mide con el codigo de
      la autora. Lectura: la exploracion entropica no mueve ese nivel, y la
      Tabla IV es el reposo de su modelo en su caso. Con nuestras tarifas, donde
      b (unos 241) queda bajo el piso (unos 693), el mismo mecanismo deja todo
      en el piso (H-88, «Sobre nuestros datos»).
  (b) Se cumple la del piso: nivel 114 y parte 0 en el reposo. Entonces 225 y
      0,098 describen un TRANSITORIO (su codigo integra hasta t = 0,01 y la
      sonda los leyo a t = 0,1 y 0,15) o las tablas del codigo de la autora, no
      el reposo. Asi se escribira en la tesis, y casa con H-88 en que sus
      tablas salen de su codigo y no de un reposo del juego. MATIZ que hay que
      llevar a H-88 si sale (b): H-88 presenta el nivel 225 como el costo b que
      la ec. 16 hace cubrir en su caso; (b) diria que eso vale a su horizonte y
      no en el reposo de la dinamica regularizada.
  (c) Ninguna de las dos: se publica lo que de, con su trayectoria, y la lectura
      queda abierta.

EL ARRANQUE DE PRECIOS ES EL DE SIEMPRE (`nivel="c136"`), NO EL PRESUPUESTO
SIGMA, Y ES DELIBERADO. En la banda del modelo base (114 a 1 250) el arranque
de C-136 cae dentro de la banda y su invariante es el presupuesto del Algoritmo
3, S = (I-1)·1 250 = 5 000, que es contra el que estan escritas las
predicciones de la sec. 11 del plan y las tablas publicadas. Con el arranque
sigma el presupuesto seria 5·[114 + 0,8·1 136] = 5 114, y entonces los precios
del reposo no serian los 833,3 y 1 250 con que se compara el articulo: la
medicion dejaria de responder la pregunta que se le hace. Por eso el reposo de
referencia se calcula con `modo_presupuesto="algoritmo3"`. **Cambiarlo a sigma
para «unificarlo» con M-A rompe la comparacion con el articulo base.** La
segunda referencia, con sigma = 0, es «todos en el piso», que es adonde lleva la
forma del fichero original.

LA PRUEBA DORADA NO ESTA AQUI: la corre el lanzador como una compuerta mas
(`tests/golden_test_sofia.py`), sin cambio, 7 de 7.

SIN DATOS REALES: el caso publicado son literales
(`caso_publicado_chacon.py`).

COMO SE JUZGA (critico 1b de la revision de 4c). NO con los puntos de teq ni
con el criterio de consenso de M-A: contra la TABLA (`ESPERADO`), variante por
variante y hora por hora, sobre el estado final de cada brazo (k = 1 hasta teq
40 y k = 100 hasta teq 160). Se lee el brazo que llego mas lejos ESTANDO
QUIETO (`veredicto.quietud`): con las derivadas bajo 1e-3 en sus dos ultimos
puntos (N5 de la re-revision) y sin moverse mas que la tolerancia entre dos
puntos de control (NM1 de la re-revision 2). Los dos puntos son teq 80 y 160
para el brazo k = 100, y para el brazo k = 1, que termina en teq 40 POR
DISEÑO, sus dos ultimos, teq 20 y 40 (re-revision 3): asi el brazo sin
acelerar tambien se puede leer, que es el contraste que importa en «topados»,
donde la aceleracion solo es aproximada. La tolerancia de esa quietud es la de
la TABLA, no la floja de M-A (re-revision 3, menor), y se aplica SOLO a las
magnitudes que la tabla lee (`tolerancia_quietud`, re-revision 4, menor): el
brazo de barrera, con q (+-1e-3 (kWh)), p (+-0,5 (COP/kWh)) y la parte del
vendedor; el de precio, con el nivel ponderado y la parte, sin mirar el
reparto, que con la exploracion entropica puede seguir convergiendo como 1/t
con los precios ya quietos en el piso. Un estado que todavia se mueve es un
transitorio, y si ningun brazo esta quieto la tabla no se lee y se dice «no
llego». Los dos brazos se publican con su alcance, su costo y el motivo de su
quietud. `veredicto(resultados)` hace esto, y `veredicto.py` lo llama solo
cuando el JSON es de M-G.

LA TABLA, con su procedencia:
  - 22:00, barrera + V3a: precios 833,3 x 3 y 1 250 x 2, +-0,5 (COP/kWh), y
    reparto [0,3037 x 3; 0,262; 0,208], +-1e-3 (kWh), de la sec. 11 del plan;
    parte del vendedor 0,758 +-0,005, la del nucleo (ver arriba por que no
    0,77).
  - 14:00, barrera + V3a: la sec. 11 dice «lo que de la forma cerrada
    (calcularlo antes y fijarlo)». Calculado con el nucleo el 2026-09-18
    (`preparacion.resuelve` con el Algoritmo 3 y techo 1 250): regimen
    compradores cortos, precios [1 250; 114; 1 136; 1 250] y reparto [0,021;
    2,843; 0,259; 0,114], parte 0,1137.
  - 22:00, precio + V3a (V1+ent): las dos predicciones de las dos lecturas,
    (a) nivel 225 +- 1 y parte 0,098 +- 0,002 y (b) nivel 114 +- 1 y parte
    0 +- 0,002.
  - 14:00, precio + V3a: sin prediccion publicada; solo la lectura (b).

COSTO. La sonda del consenso no llego al reposo en este caso, y por eso esta
medicion existe: a t = 0,3 los precios seguian moviendose. Con k = 100 hasta
teq 160 deberia caber; el tope es de 3 600 (s) por corrida y son ocho corridas.
"""
import math

import numpy as np

MEDICION = "M-G"
QUE_DECIDE = "que da el modelo del articulo en sus dos horas publicadas"

# La tabla contra la que se juzga, por (hora, familia). Cada fila: nombre,
# magnitud del estado final, valor, tolerancia y procedencia. Las magnitudes
# son "p" (precio de cada comprador, en el orden de `e["comp"]`), "q" (lo que
# recibe cada comprador), "ppond" (precio ponderado por energia) y "parte"
# (parte del vendedor en el excedente).
BARRERA = "barrera + V3a"
PRECIO = "precio + V3a (V1+ent)"
ESPERADO = {
    ("22", BARRERA): [
        ("precios 833,3 x 3 y 1 250 x 2", "p",
         [833.333, 833.333, 833.333, 1250.0, 1250.0], 0.5, "plan, sec. 11"),
        ("reparto [0,3037 x 3; 0,262; 0,208]", "q",
         [0.3037, 0.3037, 0.3037, 0.262, 0.208], 1e-3, "plan, sec. 11"),
        # NO 0,77: era el transitorio de la sonda a t = 0,3 (ver el docstring).
        ("parte del vendedor 0,758", "parte", 0.758, 0.005,
         "nucleo (test_reposo_mercado.py)"),
    ],
    ("14", BARRERA): [
        ("precios [1 250; 114; 1 136; 1 250]", "p",
         [1250.0, 114.0, 1136.0, 1250.0], 0.5, "nucleo, fijado el 2026-09-18"),
        ("reparto [0,021; 2,843; 0,259; 0,114]", "q",
         [0.021, 2.843, 0.259, 0.114], 1e-3, "nucleo, fijado el 2026-09-18"),
        ("parte del vendedor 0,1137", "parte", 0.1137, 0.005,
         "nucleo, fijado el 2026-09-18"),
    ],
    ("22", PRECIO): [
        ("(a) nivel ponderado 225", "ppond", 225.0, 1.0,
         "plan, sec. 11; H-88, el costo b"),
        ("(a) parte del vendedor 0,098", "parte", 0.098, 0.002,
         "plan, sec. 11; H-88, (b - piso)/(techo - piso)"),
        ("(b) todos en el piso: nivel 114", "ppond", 114.0, 1.0,
         "lectura del transitorio"),
        ("(b) todos en el piso: parte 0", "parte", 0.0, 0.002,
         "lectura del transitorio"),
        # Re-revision final de 4c (menor 2): el nivel y la parte van
        # ponderados por energia, y un comprador quieto en 300 que recibe
        # 0,001 (kWh) los dejaba en 114,135 y 1,2e-4. «Todos» se lee literal.
        ("(b) todos en el piso: cada precio en 114", "p", [114.0] * 5, 1.0,
         "lectura del transitorio"),
    ],
    ("14", PRECIO): [
        ("(b) todos en el piso: nivel 114", "ppond", 114.0, 1.0,
         "lectura del transitorio"),
        ("(b) todos en el piso: parte 0", "parte", 0.0, 0.002,
         "lectura del transitorio"),
        ("(b) todos en el piso: cada precio en 114", "p", [114.0] * 4, 1.0,
         "lectura del transitorio"),
    ],
}
# Que lectura dice la tabla, segun que filas del brazo de precio se cumplan.
LECTURAS = {
    "(a)": "(a) el nivel es el costo del vendedor y la Tabla IV es el reposo "
           "de su modelo en su caso",
    "(b)": "(b) todos en el piso: 225 y 0,098 eran un transitorio o las tablas "
           "del codigo de la autora, no el reposo (casa con H-88; ver el matiz "
           "del docstring)",
}

HORAS = ("22", "14")
ACELERACIONES = (1.0, 100.0)
CORTES = {1.0: [0, 0.05, 0.1, 0.3, 1, 2, 5, 10, 20, 40],
          100.0: [0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6]}
MU = 1.0
TOPE = 3600.0

# El reposo de referencia: el presupuesto del Algoritmo 3 con el techo del
# modelo base, y «todos en el piso» (sigma = 0), que es la lectura (b) del
# brazo de precio.
REFERENCIAS = {"cerrada": dict(modo_presupuesto="algoritmo3", pi_gs=1250.0),
               "piso_todos": dict(modo_presupuesto="sigma", sigma=0.0)}

# La configuracion del codigo de la autora (ver el docstring): competencia
# `matlab` y oferta arrancando a partes iguales, en los dos brazos.
CODIGO_AUTORA = dict(comp="matlab", arranque="iguales")
VARIANTES = ((BARRERA, dict(CODIGO_AUTORA)),
             (PRECIO, dict(CODIGO_AUTORA, peso="precio")))


def specs(horas=None):
    fuera = []
    for hora in HORAS:
        for etq, extra in VARIANTES:
            for k in ACELERACIONES:
                var = dict(mu_ent=MU, k_lento=k)
                var.update(extra)
                fuera.append(dict(
                    medicion=MEDICION, familia=etq,
                    caso="CHACON", fecha=hora, grupo="chacon",
                    etq=f"{etq} k{k:g}", var=var,
                    cortes=CORTES[k], tope=TOPE,
                    nivel="c136", piso_juego="marginal",
                    cerrada=dict(modo_presupuesto="algoritmo3", pi_gs=1250.0),
                    referencias=REFERENCIAS))
    return fuera


def tolerancia_quietud(hora, familia) -> dict:
    """La tolerancia con que se juzga si un brazo de M-G esta quieto: la de SU
    TABLA (menor de la re-revision 3 de 4c), no la floja de M-A, que con
    k = 100 daba 1e-2·E = 0,014 (kWh) mientras la tabla exige +-1e-3 (kWh).

    Y SOLO CON LAS MAGNITUDES QUE LEE SU TABLA (menor de la re-revision 4): el
    brazo de barrera, con q, p y la parte del vendedor; el de precio, con el
    nivel ponderado y la parte, sin mirar el reparto. Con la exploracion
    entropica y compradores topados el reparto converge como 1/t: con c = 0,25
    se mueve 1,56e-3 (kWh) entre teq 80 y 160 aunque los precios esten ya
    quietos en el piso y la lectura (b) se cumpla exactamente, y exigirle
    +-1e-3 (kWh) al reparto dejaba ese brazo «sin lectura».

    Devuelve {"magnitudes": {magnitud: tolerancia}} para `veredicto.quietud`:
    la tolerancia de cada magnitud es la menor de las filas de la tabla que la
    leen. Una hora y variante sin tabla (no la hay hoy) se juzga con la del
    plan para M-G: 1e-3 (kWh) en reparto y 0,5 (COP/kWh) en precio."""
    tabla = ESPERADO.get((hora, familia), [])
    magnitudes = {}
    for _t, m, _v, tol, _f in tabla:
        magnitudes[m] = min(float(tol), magnitudes.get(m, math.inf))
    if not magnitudes:
        magnitudes = {"q": 1e-3, "p": 0.5}
    return dict(magnitudes=magnitudes,
                clase="la de la tabla de M-G, en lo que lee la tabla")


def _valor(fila, magnitud):
    return np.asarray(fila[magnitud], dtype=float)


def juzga_fila(fila, filas_tabla) -> list:
    """Cada linea de la tabla frente al estado final de un brazo."""
    fuera = []
    for texto, magnitud, valor, tol, fuente in filas_tabla:
        obtenido = _valor(fila, magnitud)
        esperado = np.asarray(valor, dtype=float)
        if obtenido.shape != esperado.shape:
            fuera.append(dict(texto=texto, fuente=fuente, cumple=False,
                              dif=float("inf"), obtenido=obtenido.tolist()))
            continue
        dif = float(np.max(np.abs(obtenido - esperado)))
        fuera.append(dict(texto=texto, fuente=fuente, cumple=bool(dif <= tol),
                          dif=dif, tol=tol, obtenido=obtenido.tolist()))
    return fuera


def veredicto(resultados) -> str:
    """M-G contra su tabla, por hora y variante, con el alcance de cada brazo."""
    from veredicto import es_falla, quietud
    lineas = ["", "  M-G CONTRA LA TABLA (por variante; se lee el brazo que "
              "llego mas lejos ESTANDO QUIETO)", ""]
    grupos = {}
    for res in resultados:
        sp = res.get("spec", {})
        if sp.get("medicion") != MEDICION:
            continue
        if not res.get("filas") and not es_falla(res):
            continue
        grupos.setdefault((sp["fecha"], sp.get("familia", sp["etq"])),
                          []).append(res)
    if not grupos:
        return "\n".join(lineas + ["  ninguna corrida de M-G con puntos de "
                                   "control: no hay nada que juzgar"])
    for (hora, familia), brazos in sorted(grupos.items()):
        tabla = ESPERADO.get((hora, familia), [])
        lineas.append(f"  {hora}:00 - {familia}")
        # m-b de la re-revision 2: un brazo fallido se dice, no desaparece.
        for res in [b for b in brazos if es_falla(b)]:
            k = res["spec"].get("var", {}).get("k_lento", 1.0)
            lineas.append(f"    brazo k = {k:g}: FALLA ({res.get('msg', '?')})")
        brazos = sorted([b for b in brazos if not es_falla(b)],
                        key=lambda r: -float(r.get("teq_alcanzado", 0.0)))
        tol_quieta = tolerancia_quietud(hora, familia)
        for res in brazos:
            k = res["spec"].get("var", {}).get("k_lento", 1.0)
            f = res["filas"][-1]
            _q, motivo = quietud(res, tol_quieta)
            lineas.append(
                f"    brazo k = {k:g}: llego a teq {res.get('teq_alcanzado', 0):g}"
                f" ({res.get('msg', '?')}), {res.get('nfev', 0)} evaluaciones, "
                f"{res.get('seg', 0.0):.0f} (s), {motivo} "
                f"(|dq/dt| = {f['dq_dt']:.1e}, |dp/dt| = {f['dp_dt']:.1e}); "
                f"precios {np.round(f['p'], 2).tolist()}, reparto "
                f"{np.round(f['q'], 4).tolist()}, nivel {f['ppond']:.2f}, "
                f"parte {f['parte']:.4f}")
        if not brazos:
            lineas.append("    NO LLEGO: fallaron todos sus brazos")
            if familia == PRECIO:
                lineas.append("    => sin lectura: el brazo de precio fallo")
            lineas.append("")
            continue
        if not tabla:
            lineas.append("    (sin tabla para esta hora y variante)")
            lineas.append("")
            continue
        # N5: solo se lee contra la tabla un estado QUIETO. El brazo que llego
        # mas lejos sin estar quieto describe un transitorio, y leerlo contra
        # la tabla confundiria «no llego» con «llego a otro sitio».
        quietos = [r for r in brazos if quietud(r, tol_quieta)[0]]
        if not quietos:
            lineas.append("    NO LLEGO: ningun brazo esta quieto al final; su "
                          "estado es un transitorio y no se lee contra la tabla")
            if familia == PRECIO:
                lineas.append("    => sin lectura: el brazo de precio no llego "
                              "al reposo")
            lineas.append("")
            continue
        mejor = quietos[0]
        juicio = juzga_fila(mejor["filas"][-1], tabla)
        k = mejor["spec"].get("var", {}).get("k_lento", 1.0)
        for j in juicio:
            lineas.append(f"    {'CUMPLE ' if j['cumple'] else 'NO     '} "
                          f"{j['texto']} (|dif| = {j['dif']:.3g}, tol "
                          f"{j.get('tol', float('nan')):g}; {j['fuente']}) "
                          f"con el brazo k = {k:g}")
        if familia == PRECIO:
            lineas.append(f"    => {lectura(juicio)}")
        lineas.append("")
    return "\n".join(lineas)


def lectura(juicio) -> str:
    """Que lectura del brazo de precio dice la tabla (ver el docstring)."""
    for clave in ("(a)", "(b)"):
        filas = [j for j in juicio if j["texto"].startswith(clave)]
        if filas and all(j["cumple"] for j in filas):
            return f"se cumple la lectura {LECTURAS[clave]}"
    return ("(c) no se cumple ninguna de las dos lecturas: se publica lo que "
            "dio, con su trayectoria, y la lectura queda abierta")
