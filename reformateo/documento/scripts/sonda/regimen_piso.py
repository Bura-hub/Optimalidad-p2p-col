"""
Sonda del régimen del piso (H-52).

La pregunta la planteó el autor: si el mercado entre pares de una comunidad
energética tiene que regirse por el tramo de la Resolución CREG 174, que
manda al vendedor a bolsa en cuanto su inyección acumulada supera su retiro
del mes, o si puede negociar siempre con el piso de permuta. Y si bajar al
piso de bolsa resultara más beneficioso, si convendría hacerlo.

LO QUE DICE LA NORMA, y es lo primero porque acota la pregunta. El precio
interno **no está regulado**: la Resolución CREG 101 072 establece que «el
precio de venta es pactado libremente» para quien atiende usuarios no
regulados, y las cinco lo son desde CAL-47; y el porcentaje de distribución
de excedentes del colectivo lo **acuerdan sus integrantes**. De modo que los
tres regímenes son admisibles y la pregunta es cuál conviene, no cuál se
permite.

LO QUE HAY QUE TENER CLARO ANTES DE LEER. El piso NO es un precio que se
elija: es lo que la red le pagaría al vendedor si no negociara. Forzar
permuta a quien ya pasó a bolsa modela a un vendedor que rechaza dinero que
aceptaría. Los dos regímenes forzados existen para MEDIR el efecto.

Y EL PRECIO INTERNO NO MUEVE EL AGREGADO. En una venta dentro de la
comunidad el comprador paga y el vendedor cobra lo mismo: es una
transferencia entre miembros y se cancela. Lo único que mueve la posición
agregada es cuánta energía se mueve dentro en vez de cruzar la frontera, y
los precios a los que cruza lo que sobra, que los fija la red. Es la
identidad de H-33 leída por el otro lado.

De ahí que el canal por el que el piso SÍ puede importar sea otro: un piso
más bajo retira menos vendedores, y más participación es más volumen.

EL CUARTO RÉGIMEN, `residual`, viene de H-53: el tramo se acumula sobre lo
que de verdad cruza la frontera, es decir el excedente menos lo colocado
dentro de la comunidad, que es como el artículo 23 de la Resolución CREG
101 072 cuenta los excedentes asignables. No hace falta punto fijo, porque
por D-7 el volumen es el lado corto y no depende del precio.

EL BIENESTAR NO ARBITRA, y esto está probado en H-55: los términos de pago
del vendedor y del comprador se cancelan al sumar los dos lados, de modo que
la única dependencia del precio que le queda al bienestar es la penalización
de competencia, que es negativa y proporcional al precio. **Prefiere el piso
más bajo por construcción.** Se informa porque es la función del modelo base,
no porque decida. Quien decide es la factura, que sí está en pesos.

LAS CUATRO MÉTRICAS, y se informan por separado a propósito, porque la
jornada del 2026-09-07 enseñó que se contradicen:

  bienestar   W de vendedores más W de compradores, que es la función que el
              modelo base maximiza. Es la métrica del autor del modelo.
  factura     lo que la comunidad paga de verdad, con mercado y sin él.
  volumen     y los vendedores retirados, que es el canal de arriba.
  excedente   la banda por la energía. ENGAÑA: crece cuando la alternativa
              empeora, no cuando la comunidad mejora. Ver H-47.

Uso:
    python reformateo/documento/scripts/sonda/regimen_piso.py --muestra 40
"""
from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[3]
for _p in (RAIZ, AQUI):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import hilos  # noqa: E402,F401   un hilo por proceso, y ANTES que numpy

import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402

from recoge import recoge  # noqa: E402

REGIMENES = ("tramo", "permuta", "bolsa", "residual")
SALIDA = AQUI.parents[1] / "validacion_horaria"

_DAT: dict = {}


def _datos(cobertura: str, regimen: str):
    from paso_a_paso import carga
    llave = (cobertura, regimen)
    if llave not in _DAT:
        _DAT[llave] = carga(cobertura, piso=regimen)
    return _DAT[llave]


def _una(args):
    """Resuelve UNA hora bajo UN régimen del piso."""
    cobertura, k, regimen = args
    from core.settlement import compute_savings
    from paso_a_paso import resuelve

    dat = _datos(cobertura, regimen)
    try:
        r = resuelve(dat, int(k))
    except Exception:
        r = None
    if r is None:
        return [dict(cobertura=cobertura, hora=int(k), regimen=regimen,
                     resuelta=False)]

    P = np.asarray(r["P"], float)
    pi = np.asarray(r["pi"], float)
    # C-160: el integrador puede devolver una solucion NO FINITA sin lanzar
    # excepcion. Su aviso lo dice, «too much accuracy requested ... tolsf =
    # NaN», pero va a la salida de errores y la sonda no lo mira. Una fila asi
    # se anotaba como RESUELTA con metricas no numericas, y las sumas de
    # pandas descartan esos valores en silencio: el regimen afectado saldria
    # con menos horas dentro de su suma que los demas, sesgado y sin aviso.
    # Es la misma familia de H-50. Una hora que no resuelve es un dato.
    if not (np.all(np.isfinite(P)) and np.all(np.isfinite(pi))):
        return [dict(cobertura=cobertura, hora=int(k), regimen=regimen,
                     resuelta=False, motivo="solucion no finita")]
    techo_i, piso_j = r["techo_i"], r["piso_j"]
    S_i, SR_j = compute_savings(P, pi, techo_i, piso_j)

    # La factura sin mercado se calcula sobre TODOS los vendedores, incluidos
    # los retirados: quien sale del mercado no sale de la contabilidad. Es el
    # error que la auditoria encontro en la sonda del escenario.
    G_net, D_net = r["G_net"], r["D_net"]
    sin = float(np.sum(D_net * techo_i) - np.sum(G_net * piso_j))
    exc = float(S_i.sum() + SR_j.sum())

    # Las metricas con las que el AUTOR DEL MODELO juzgaria esta pregunta.
    # Su articulo evalua con el indice de equidad global y el reparto del
    # bienestar entre los dos lados, no con una factura:
    #
    #   IE = (suma del ahorro de compradores - suma del ingreso de
    #        vendedores) / (suma de los dos)
    #
    # Cerca de cero es equitativo; hacia -1 favorece al vendedor y hacia +1
    # al comprador. En su Tabla VII el metodo centralizado da -0,8913 con un
    # 94,56 % para el vendedor, y ese es el argumento del articulo.
    #
    # Importa AQUI porque los dos sumandos son el ahorro contra el techo y el
    # ingreso contra el PISO, de modo que el indice se mueve con el regimen:
    # bajar el piso ensancha el margen del vendedor sobre su alternativa y
    # empuja el indice hacia su lado.
    ahorro_c = float(S_i.sum())
    ingreso_v = float(SR_j.sum())
    tot = ahorro_c + ingreso_v
    ie = (ahorro_c - ingreso_v) / tot if abs(tot) > 1e-12 else np.nan
    ps = 100.0 * ahorro_c / tot if abs(tot) > 1e-12 else np.nan

    tr = r["tr"]
    return [dict(
        cobertura=cobertura, hora=int(k), regimen=regimen, resuelta=True,
        J=len(r["sids"]), I=len(r["bids"]), retirados=len(r["retirados"]),
        volumen=float(P.sum()),
        # la funcion objetivo del modelo base
        bienestar=float(tr.W_t[-1]) if getattr(tr, "W_t", None) is not None
        else np.nan,
        bienestar_vendedor=float(tr.Wj_t[-1]) if getattr(tr, "Wj_t", None)
        is not None else np.nan,
        bienestar_comprador=float(tr.Wi_t[-1]) if getattr(tr, "Wi_t", None)
        is not None else np.nan,
        excedente=exc, factura_sin=sin, factura_con=sin - exc,
        ahorro_comprador=ahorro_c, ingreso_vendedor=ingreso_v,
        equidad=ie, reparto_comprador=ps,
        reparto_vendedor=(100.0 - ps) if np.isfinite(ps) else np.nan,
        piso_medio=float(np.mean(piso_j)),
        precio_medio=float(np.average(pi, weights=np.maximum(P.sum(axis=0),
                                                             1e-12))),
    )]


def horas_activas(cobertura: str) -> np.ndarray:
    from core.market_prep import classify_agents, compute_generation_limit
    from data.xm_prices import get_b_for_real_data

    dat = _datos(cobertura, "tramo")
    D, G = dat["D"], dat["G"]
    N, T = D.shape
    a = np.zeros(N); c = np.zeros(N)
    b = get_b_for_real_data(N, dat["nombres"])
    return np.array([k for k in range(T)
                     if all(classify_agents(
                         compute_generation_limit(
                             G[:, k], a, b, c, dat["techo"][:, k]),
                         D[:, k])[1:])], dtype=int)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=40)
    # Un regimen ya medido no se repite: la muestra la fija la semilla, de
    # modo que correr uno suelto da EXACTAMENTE las mismas horas y la
    # comparacion sigue emparejada contra la corrida anterior.
    ap.add_argument("--regimenes", default=",".join(REGIMENES),
                    help="lista separada por comas")
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--plazo", type=float, default=45.0,
                    help="plazo TOTAL en minutos")
    # El que de verdad manda: corta cuando pasan N minutos sin que termine
    # NINGUNA tarea. Sin el, tres horas atascadas cuestan media hora de
    # procesos ociosos. Ver la cabecera de recoge.py.
    ap.add_argument("--plazo-tarea", type=float, default=6.0,
                    dest="plazo_tarea",
                    help="minutos sin que termine ninguna tarea")
    ap.add_argument("--procesos", type=int,
                    default=max(1, (os.cpu_count() or 4) - 2))
    args = ap.parse_args()
    regimenes = tuple(g.strip() for g in args.regimenes.split(",") if g.strip())
    for g in regimenes:
        if g not in REGIMENES:
            raise SystemExit(f"regimen {g!r} desconocido; hay {REGIMENES}")

    rng = np.random.default_rng(args.semilla)
    horas = []
    for cob in ("m1", "m3"):
        act = horas_activas(cob)
        n = min(args.muestra, len(act))
        horas += [(cob, int(k)) for k in rng.choice(act, size=n, replace=False)]

    tareas = [(cob, k, g) for cob, k in horas for g in regimenes]
    print(f"  {len(horas)} horas · {len(regimenes)} regímenes = "
          f"{len(tareas)} tareas · {args.procesos} procesos", flush=True)

    # Los tres juegos de datos, armados antes de abrir los procesos.
    for g in regimenes:
        for cob in sorted({c for c, _ in horas}):
            _datos(cob, g)
    print(f"  datos en memoria: {len(_DAT)} juegos", flush=True)

    SALIDA.mkdir(parents=True, exist_ok=True)
    etiqueta = ("" if len(regimenes) == len(REGIMENES)
                else "_" + "_".join(regimenes))
    csv = SALIDA / f"regimen_piso_muestra{args.muestra}{etiqueta}.csv"
    d = recoge(_una, tareas, args.procesos, csv, plazo_min=args.plazo,
               plazo_tarea_min=args.plazo_tarea,
               describe=lambda t: f"{t[0]} hora {t[1]} piso {t[2]}")

    ok = d[d.resuelta.fillna(False)]
    print(flush=True)
    print(f"  Régimen del piso · muestra{args.muestra}", flush=True)
    print("  " + "=" * 92, flush=True)
    for cob in ("m1", "m3"):
        s = ok[ok.cobertura == cob]
        if s.empty:
            continue
        print(flush=True)
        print(f"  frontera {cob.upper()}", flush=True)
        print(f"  {'regimen':>9s} {'horas':>6s} {'piso medio':>11s} "
              f"{'BIENESTAR':>13s} {'FACTURA con':>13s} {'volumen':>9s} "
              f"{'retir':>6s} {'excedente':>12s} {'EQUIDAD':>9s} "
              f"{'% compr':>8s}", flush=True)
        for g in regimenes:
            t = s[s.regimen == g]
            if t.empty:
                continue
            # El indice y el reparto se agregan sobre las SUMAS del
            # periodo, no promediando indices por hora: son cocientes, y la
            # media de cocientes no es el cociente de las sumas.
            ac, iv = t.ahorro_comprador.sum(), t.ingreso_vendedor.sum()
            tt = ac + iv
            ie_g = (ac - iv) / tt if abs(tt) > 1e-12 else float("nan")
            ps_g = 100.0 * ac / tt if abs(tt) > 1e-12 else float("nan")
            print(f"  {g:>9s} {len(t):6d} {t.piso_medio.mean():11.1f} "
                  f"{t.bienestar.sum():13.1f} {t.factura_con.sum():13.1f} "
                  f"{t.volumen.sum():9.2f} {int(t.retirados.sum()):6d} "
                  f"{t.excedente.sum():12.1f} {ie_g:9.4f} {ps_g:7.2f}%",
                  flush=True)

        # C-155: la comparacion va en PESOS y sobre horas emparejadas, no en
        # porcentaje por hora. En la frontera secundaria la factura ronda el
        # cero y cambia de signo, de modo que el cociente daba valores como
        # -231,60 % sin contenido. Ademas solo cuentan las horas con TODOS
        # los regimenes resueltos, para que las sumas sean comparables.
        if "tramo" not in regimenes:
            continue
        p = s.pivot(index="hora", columns="regimen",
                    values=["factura_con", "volumen"]).dropna()
        if p.empty:
            continue
        print(f"    emparejadas sobre {len(p)} horas con todos los "
              f"regimenes resueltos", flush=True)
        for g in regimenes:
            if g == "tramo":
                continue
            df = p["factura_con"][g] - p["factura_con"]["tramo"]
            dv = p["volumen"][g] - p["volumen"]["tramo"]
            mueve = int((df.abs() > 1e-6).sum())
            med = float(df[df.abs() > 1e-6].median()) if mueve else 0.0
            print(f"    {g:>8s} frente a tramo: factura {df.sum():+12.1f} "
                  f"(COP) . volumen {dv.sum():+8.3f} (kWh) . cambia en "
                  f"{mueve} de {len(p)} horas, mediana {med:+.1f} (COP)",
                  flush=True)
    print(flush=True)
    print(f"  csv: {csv}", flush=True)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
