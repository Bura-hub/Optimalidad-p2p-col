"""Lo que comparten las mediciones: la hora preparada, el reposo en forma
cerrada con que se compara y el criterio de consenso.

QUE HACE. Para cada hora, deja del mismo lado dos cosas que hay que comparar:

  1. el REPOSO EN FORMA CERRADA, `core.reposo_mercado.resuelve_reposo` con las
     opciones de produccion (presupuesto sigma, liquidacion uniforme, despacho
     por piso con la caminata competitiva, D63 a D65);
  2. la DINAMICA REGULARIZADA del arnes, arrancada en el mismo sitio en que
     arranca la via acoplada con `nivel="sigma"` y con el piso del juego en el
     del vendedor marginal (D63).

Para que la comparacion sea de lo mismo, la hora se RECORTA a quienes estan en
el juego: los vendedores que despachan y los compradores que no quedaron fuera
por tener el techo bajo el piso del juego (`excluidos_bajo_piso`). Los
compradores del regimen «no cabe» (`excluidos`) se QUEDAN: estan en el juego,
en su techo y sin energia, y es justo lo que la dinamica tiene que reproducir.
El recorte se comprueba: el reposo de la hora recortada tiene que ser el de la
hora entera restringido, y la diferencia se guarda (`dif_recorte`).

SIN ESCRITURAS. Solo lee. Lo que escribe es el guion que lo llama.
"""
import numpy as np

import arnes as A                                          # noqa: E402
from core.reposo_mercado import resuelve_reposo, presupuesto_precios  # noqa: E402,E501

# ── Tolerancias de aceptacion (sec. 11 de fable-report.md, M-A) ────────────
# Con compradores libres y sin acelerar.
TOL_Q_REL_ESTRICTA = 1e-3      # veces E (kWh)
TOL_P_ESTRICTA = 0.05          # (COP/kWh)
# Con topados o con aceleracion, porque la aceleracion solo es exacta con
# libres (ver el encabezado de `arnes.py`).
TOL_Q_REL_FLOJA = 1e-2         # 1 % de E (kWh)
TOL_P_FLOJA = 0.5              # (COP/kWh)
# El criterio de consenso pide ademas derivadas pequenas, por unidad de tiempo
# EQUIVALENTE (es decir, divididas por la aceleracion k).
TOL_DERIVADA = 1e-3
# Por debajo de este numero de horas juzgadas un grupo no se rotula: sale
# «muestra insuficiente», nunca «reposo verificado» (medio 2 de la revision de
# 4c, decision del controlador).
MIN_MUESTRA = 5
# Cuanto puede mover el recorte el reparto del reposo antes de que la hora deje
# de contar (kWh, relativo a max(1, E)): la hora recortada tiene que dar el
# mismo reposo que la entera restringida, y si no, la comparacion no es de lo
# mismo (medio 5).
TOL_RECORTE_REL = 1e-9

# Los regimenes en que la aceleracion no es exacta, aunque k sea 1: hay un
# multiplicador que crece sin tope y la hora es rigida.
REGIMENES_RIGIDOS = ("topados", "mixto", "compradores_cortos")
SIN_MERCADO = ("sin_mercado", "sin_ganancia")

# Las opciones de produccion del reposo (matriz_reposo, D50, D51, D64).
CERRADA_PRODUCCION = dict(modo_presupuesto="sigma", regla_precio="uniforme",
                          despacho_vendedores="piso")


def sigma_base(n_compradores: int) -> float:
    """sigma_I = (I-1)/I, la del presupuesto de precios de produccion (D50)."""
    return (n_compradores - 1) / n_compradores


def precios_sigma(techo, piso: float, sigma=None) -> np.ndarray:
    """Los precios con que arranca `nivel="sigma"` de la via acoplada (D50).

    Cada comprador abre en piso + sigma_I·(techo_i - piso). Sale del nucleo,
    aplicado a un comprador a la vez con la sigma de la hora, igual que
    `core.coupled_ode_convergence._precios_sigma`, para no repetir la formula.
    """
    techo = np.asarray(techo, float)
    I = techo.size
    sg = sigma_base(I) if sigma is None else float(sigma)
    pi0 = np.array([presupuesto_precios(techo[i:i + 1], float(piso),
                                        modo="sigma", sigma=sg)
                    for i in range(I)])
    S = presupuesto_precios(techo, float(piso), modo="sigma", sigma=sg)
    if abs(float(np.sum(pi0)) - S) > 1e-9 * max(1.0, abs(S)):
        raise AssertionError(f"el arranque sigma suma {np.sum(pi0)!r} y el "
                             f"presupuesto del nucleo es {S!r}")
    return pi0


def resuelve(e, **opciones):
    """El reposo en forma cerrada de una hora del arnes."""
    op = dict(CERRADA_PRODUCCION)
    op.update(opciones)
    return resuelve_reposo(e["gn"], e["dn"], e["b"], e["techo"], e["piso_j"],
                           **op)


def _sub(e, sel_j, sel_i, piso: float) -> dict:
    """La hora con solo los agentes que estan en el juego, y el piso dado."""
    sel_j = np.asarray(sel_j, int)
    sel_i = np.asarray(sel_i, int)
    return dict(s=[e["s"][j] for j in sel_j], bb=[e["bb"][i] for i in sel_i],
                vend=[e["vend"][j] for j in sel_j],
                comp=[e["comp"][i] for i in sel_i],
                gn=np.asarray(e["gn"], float)[sel_j],
                dn=np.asarray(e["dn"], float)[sel_i],
                a=np.asarray(e["a"], float)[sel_j],
                b=np.asarray(e["b"], float)[sel_j],
                gk=np.asarray(e["gk"], float)[sel_i],
                techo=np.asarray(e["techo"], float)[sel_i],
                piso_j=np.asarray(e["piso_j"], float)[sel_j],
                piso=float(piso), fecha=e["fecha"])


def _cerrada_a_dict(r) -> dict:
    return dict(q=np.asarray(r.q, float), p=np.asarray(r.pi_reposo, float),
                P=np.asarray(r.P, float),
                sj=np.asarray(r.s_despachado, float), E=float(r.E),
                regimen=str(r.regimen), piso=float(r.piso), S=float(r.S),
                ell=(None if r.ell is None else float(r.ell)),
                p_u=float(r.p_u), n_soluciones=int(r.n_soluciones),
                excluidos=tuple(int(k) for k in r.excluidos),
                parte_vendedor=float(r.parte_vendedor))


def prepara(spec) -> dict:
    """La hora lista para integrar, y contra que se compara.

    Claves de `spec` que se leen aqui:
      caso, fecha          la hora (`arnes.hora_de`);
      cerrada              opciones del reposo de referencia (por defecto las
                           de produccion);
      referencias          dict nombre -> opciones del reposo, para comparar
                           varias reglas en la misma corrida (M-B);
      piso_juego           "marginal" (D63, defecto) o "minimo" (la regla
                           anterior, D62);
      nivel                "sigma" (D50, defecto), "c136" (el arranque de
                           siempre), o "medio" / "alto" / "bajo";
      sigma                la sigma del nivel y del presupuesto; None = la base;
      recorta_vendedores   True (defecto) deja solo a los que despachan;
      recorta_compradores  True (defecto) saca a los de `excluidos_bajo_piso`.

    Devuelve dict(e, precios0, referencias, base, avisos, sin_mercado).
    """
    e0 = A.hora_de(spec["caso"], spec["fecha"])
    avisos = []
    op_base = dict(spec.get("cerrada", {}))
    if spec.get("sigma") is not None:
        op_base.setdefault("sigma", float(spec["sigma"]))
    r0 = resuelve(e0, **op_base)
    if r0.regimen in SIN_MERCADO or r0.E <= 0.0:
        return dict(e=None, sin_mercado=True, base=_cerrada_a_dict(r0),
                    precios0=None, referencias={}, avisos=[
                        f"la hora no tiene mercado (regimen {r0.regimen})"])

    # Quien esta en el juego.
    J = len(e0["gn"])
    I = len(e0["dn"])
    if spec.get("recorta_vendedores", True):
        sel_j = np.where(np.asarray(r0.s_despachado, float) > 1e-12)[0]
    else:
        sel_j = np.where(np.asarray(e0["gn"], float) > 0.0)[0]
    fuera_i = set(int(k) for k in r0.excluidos_bajo_piso)
    if spec.get("recorta_compradores", True):
        sel_i = np.array([i for i in range(I)
                          if np.asarray(e0["dn"], float)[i] > 0.0
                          and i not in fuera_i], int)
    else:
        sel_i = np.where(np.asarray(e0["dn"], float) > 0.0)[0]
    if sel_j.size == 0 or sel_i.size == 0:
        return dict(e=None, sin_mercado=True, base=_cerrada_a_dict(r0),
                    precios0=None, referencias={}, avisos=[
                        "no queda ningun vendedor o ningun comprador en el juego"])
    if sel_j.size < J or sel_i.size < I:
        avisos.append(f"recorte: {J - sel_j.size} vendedores y "
                      f"{I - sel_i.size} compradores fuera del juego")

    # El piso del juego.
    modo_piso = spec.get("piso_juego", "marginal")
    if modo_piso == "marginal":
        piso = float(r0.piso)
    elif modo_piso == "minimo":
        piso = float(np.min(np.asarray(e0["piso_j"], float)[sel_j]))
    else:
        raise ValueError(f"piso_juego={modo_piso!r}; use 'marginal' o 'minimo'")

    e = _sub(e0, sel_j, sel_i, piso)

    # El reposo de la hora recortada, que es el que se compara, y la
    # comprobacion de que el recorte no lo movio.
    referencias = {}
    recorte_movio = False
    nombres = dict(spec.get("referencias", {})) or {"cerrada": {}}
    for nombre, extra in nombres.items():
        op = dict(op_base)
        op.update(extra)
        # El nucleo rechaza `sigma` fuera del modo sigma y `pi_gs` fuera del
        # modo algoritmo3, y una referencia puede cambiar el modo: se quitan
        # las que dejaron de aplicar, en vez de dejar que falle.
        if op.get("modo_presupuesto", "sigma") != "sigma":
            op.pop("sigma", None)
        if op.get("modo_presupuesto", "sigma") != "algoritmo3":
            op.pop("pi_gs", None)
        r = resuelve(e, **op)
        d = _cerrada_a_dict(r)
        d["opciones"] = op
        if nombre == "cerrada" or not spec.get("referencias"):
            P_ent = np.asarray(r0.P, float)[np.ix_(sel_j, sel_i)]
            d["dif_recorte"] = float(np.max(np.abs(d["P"] - P_ent))) \
                if P_ent.shape == d["P"].shape else float("inf")
            if d["dif_recorte"] > TOL_RECORTE_REL * max(1.0, float(r0.E)):
                recorte_movio = True
                avisos.append(f"el recorte movio el reposo: "
                              f"|dP| = {d['dif_recorte']:.3e} (kWh); la hora "
                              f"NO cuenta en el veredicto")
            if abs(d["piso"] - piso) > 1e-6 and modo_piso == "marginal":
                recorte_movio = True
                avisos.append(f"el piso del juego de la hora recortada es "
                              f"{d['piso']:.4f} y el de la entera {piso:.4f} "
                              f"(COP/kWh); la hora NO cuenta en el veredicto")
        referencias[nombre] = d

    # Los precios con que arranca la dinamica.
    nivel = spec.get("nivel", "sigma")
    if nivel == "sigma":
        pi0 = precios_sigma(e["techo"], piso, spec.get("sigma"))
        precios0 = np.append(pi0, float(np.max(e["techo"])))
    elif nivel == "c136":
        precios0 = None
    elif nivel in ("medio", "alto", "bajo"):
        precios0 = nivel
    else:
        raise ValueError(f"nivel={nivel!r}; use 'sigma', 'c136', 'medio', "
                         f"'alto' o 'bajo'")

    return dict(e=e, precios0=precios0, referencias=referencias,
                base=_cerrada_a_dict(r0), avisos=avisos, sin_mercado=False,
                sel_j=[int(k) for k in sel_j], sel_i=[int(k) for k in sel_i],
                piso_juego=piso, modo_piso=modo_piso,
                recorte_movio=recorte_movio)


def tolerancias(regimen: str, k: float, estricta_si_libre=True,
                declarada=None):
    """Que tolerancia le toca a esta hora, y por que.

    Con `declarada` (un dict con tol_q_rel y tol_p, y opcionalmente motivo),
    esa y ninguna otra: es la que la medicion fija en su plan, y si con ella
    alguna hora no valida, eso es un resultado (medio 3 de la revision de 4c).
    Sin ella, la de M-A: estricta (1e-3·E y 0,05 (COP/kWh)) solo sin
    aceleracion y sin topados; floja (1 % de E y 0,5) en cuanto hay
    aceleracion o la hora es rigida.
    """
    if declarada is not None:
        tol = dict(declarada)
        for clave in ("tol_q_rel", "tol_p"):
            v = tol.get(clave)
            if v is None or not np.isfinite(float(v)) or float(v) <= 0.0:
                raise ValueError(f"tolerancia declarada sin {clave} valido: "
                                 f"{declarada!r}")
            tol[clave] = float(v)
        tol.setdefault("clase", "declarada")
        tol.setdefault("motivo", "la que fija la medicion")
        return tol
    rigida = regimen in REGIMENES_RIGIDOS
    if estricta_si_libre and float(k) == 1.0 and not rigida:
        return dict(tol_q_rel=TOL_Q_REL_ESTRICTA, tol_p=TOL_P_ESTRICTA,
                    clase="estricta",
                    motivo="sin acelerar y con compradores libres")
    motivo = []
    if float(k) != 1.0:
        motivo.append(f"acelerada k = {k:g}")
    if rigida:
        motivo.append(f"regimen {regimen}")
    return dict(tol_q_rel=TOL_Q_REL_FLOJA, tol_p=TOL_P_FLOJA, clase="floja",
                motivo=" y ".join(motivo) or "por defecto")


def distancias(r_din, cerrada) -> dict:
    """Lo que separa un punto de control del reposo en forma cerrada."""
    q = np.asarray(r_din["q"], float)
    p = np.asarray(r_din["p"], float)
    P = np.asarray(r_din["P"], float)
    sj = P.sum(axis=1)
    return dict(dq=float(np.max(np.abs(q - cerrada["q"]))),
                dp=float(np.max(np.abs(p - cerrada["p"]))),
                dP=float(np.max(np.abs(P - cerrada["P"]))),
                dsj=float(np.max(np.abs(sj - cerrada["sj"]))))


def dentro(fila, nombre: str, E: float, tol) -> bool:
    """Cierto si ese punto de control esta dentro de la tolerancia."""
    d = fila["dist"].get(nombre)
    if d is None:
        return False
    return (d["dq"] <= tol["tol_q_rel"] * max(E, 1e-12)
            and d["dp"] <= tol["tol_p"])


def criterio_consenso(filas, nombre: str, E: float, tol,
                      tol_derivada: float = TOL_DERIVADA) -> dict:
    """El criterio fijado antes de medir (consenso-report.md, sec. «Metodo»).

    La hora llega al reposo en t si en t Y en el punto de control siguiente
    esta dentro de la tolerancia de reparto y de precio, y ademas las derivadas
    del reparto y de los precios, por unidad de tiempo EQUIVALENTE, valen menos
    de `tol_derivada`. Devuelve el primer t que lo cumple.
    """
    for k in range(len(filas) - 1):
        a, b = filas[k], filas[k + 1]
        if not (dentro(a, nombre, E, tol) and dentro(b, nombre, E, tol)):
            continue
        if max(a["dq_dt"], b["dq_dt"]) >= tol_derivada:
            continue
        if max(a["dp_dt"], b["dp_dt"]) >= tol_derivada:
            continue
        return dict(llega=True, t=a["t"], teq=a["teq"], punto=k)
    return dict(llega=False, t=None, teq=None, punto=None)


def en_teq(filas, nombre: str, E: float, tol, teq: float) -> dict:
    """Si el punto de control de ese tiempo equivalente esta dentro."""
    for f in filas:
        if abs(f["teq"] - teq) < 1e-9:
            d = f["dist"].get(nombre, {})
            return dict(hay=True, dentro=dentro(f, nombre, E, tol),
                        dq=d.get("dq"), dp=d.get("dp"))
    return dict(hay=False, dentro=False, dq=None, dp=None)
