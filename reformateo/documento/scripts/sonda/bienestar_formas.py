"""
Las dos formas del bienestar, enfrentadas sobre horas ya resueltas (H-58).

LA PREGUNTA. Las ecuaciones publicadas del modelo base y las tres
implementaciones de su autora no coinciden en la funcion de bienestar. La
diferencia cae justo en la pieza que decide si transar sube el bienestar o lo
baja, de modo que hay que medir cual describe un mercado que tenga sentido.

LAS DOS FORMAS, tal como se leen en cada fuente:

  codigo    la de su MATLAB y su Python, que es la que traducimos.
            vendedor:  lam*G_neto - theta*G_neto^2 - sum_i P/ln(1+pi_i)
                                    - a*(sumP)^2 - b*sumP
            comprador: lam*G_lim - theta*G_lim^2 + sum_j P/ln(|pi_i|+1)
                                    - eta*competencia

  articulo  la de las ecuaciones (6), (7) y (14) del PDF.
            vendedor:  lam*D_auto - (theta/2)*D_auto^2 + sum_i P*pi_i
                                    - a*(sumP)^2 - b*sumP - c
            comprador: lam*G_lim - (theta/2)*G_lim^2
                                    + pi_gb*sum_j P*ln(1/(pi_i+1))
                                    - beta*competencia

TRES DIFERENCIAS EN EL VENDEDOR y tres en el comprador. Ver H-58.

QUE SE MIDE, y no hace falta resolver de nuevo. Se toma una hora ya resuelta,
con su precio y su reparto, y se evalua el bienestar escalando lo transado por
un factor de cero a uno. Si el bienestar baja al subir el factor, esa forma
describe un mercado que conviene cerrar.

  W(0)      lo que vale no transar nada
  W(P*)     lo que vale el reparto de equilibrio
  argmax    donde esta el maximo dentro del recorrido

DOS ESCALAS, y es la clave. El caso publicado usa precios del orden de la
unidad; el nuestro, de cientos. El logaritmo NO es invariante de escala, de
modo que una forma puede comportarse bien en una escala y mal en la otra.

Uso:
    python reformateo/documento/scripts/sonda/bienestar_formas.py
    python reformateo/documento/scripts/sonda/bienestar_formas.py --horas 12
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[3]
for _p in (RAIZ, AQUI):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

SALIDA = AQUI.parents[1] / "validacion_horaria"
NL = chr(10)


# --------------------------------------------------------------------------
# Las dos formas. Se escriben aparte del nucleo a proposito: esta sonda mide,
# no cambia el modelo.
# --------------------------------------------------------------------------
def w_codigo(P, pi, dat):
    """La forma de su MATLAB y su Python, que es la que traducimos."""
    lam_j, th_j, a, b = dat["lam_j"], dat["th_j"], dat["a"], dat["b"]
    lam_i, th_i, et = dat["lam_i"], dat["th_i"], dat["et"]
    G_neto, G_lim = dat["G_neto"], dat["G_lim"]
    ln_pi = np.maximum(np.log1p(np.abs(pi)), 1e-12)

    wj = 0.0
    for j in range(P.shape[0]):
        sp = float(P[j, :].sum())
        wj += (lam_j[j] * G_neto[j] - th_j[j] * G_neto[j] ** 2
               - float(np.sum(P[j, :] / ln_pi))
               - a[j] * sp ** 2 - b[j] * sp)

    I = len(pi)
    m = np.ones((I, I)) - np.eye(I)
    compe = [sum(m[i][k] * pi[k] * float(P[:, k].sum()) for k in range(I))
             for i in range(I)]
    wi = 0.0
    for i in range(I):
        wi += (lam_i[i] * G_lim[i] - th_i[i] * G_lim[i] ** 2
               + float(P[:, i].sum()) / ln_pi[i] - compe[i] * et[i])
    return wj, wi


def w_articulo(P, pi, dat):
    """La forma de las ecuaciones (6), (7) y (14) del PDF."""
    lam_j, th_j, a, b, c = dat["lam_j"], dat["th_j"], dat["a"], dat["b"], dat["c"]
    lam_i, th_i, be = dat["lam_i"], dat["th_i"], dat["be"]
    D_auto, G_lim, pi_gb = dat["D_auto"], dat["G_lim"], dat["pi_gb"]

    wj = 0.0
    for j in range(P.shape[0]):
        sp = float(P[j, :].sum())
        wj += (lam_j[j] * D_auto[j] - 0.5 * th_j[j] * D_auto[j] ** 2
               + float(np.sum(P[j, :] * pi))
               - a[j] * sp ** 2 - b[j] * sp - c[j])

    I = len(pi)
    m = np.ones((I, I)) - np.eye(I)
    compe = [sum(m[i][k] * pi[k] * float(P[:, k].sum()) for k in range(I))
             for i in range(I)]
    wi = 0.0
    for i in range(I):
        wi += (lam_i[i] * G_lim[i] - 0.5 * th_i[i] * G_lim[i] ** 2
               + pi_gb * float(P[:, i].sum()) * np.log(1.0 / (pi[i] + 1.0))
               - compe[i] * be[i])
    return wj, wi


def w_completo(P, pi, dat):
    """La del articulo, con la pieza que le falta a las dos.

    En el modelo base la utilidad del comprador se evalua sobre SU PROPIA
    generacion, y el articulo lo dice expresamente: para un consumidor puro
    vale cero. De modo que comprar energia no le reporta utilidad a nadie, y
    transar solo puede anadir costos.

    Aqui la utilidad del comprador se evalua sobre la energia que de verdad
    consume, es decir la propia MAS la comprada. Es la formulacion estandar de
    la literatura que el propio articulo cita, y la unica de las tres en que
    el mercado puede mejorar el bienestar por una razon economica y no por una
    casualidad de escala.
    """
    lam_j, th_j, a, b, c = dat["lam_j"], dat["th_j"], dat["a"], dat["b"], dat["c"]
    lam_i, th_i, be = dat["lam_i"], dat["th_i"], dat["be"]
    D_auto, G_lim, pi_gb = dat["D_auto"], dat["G_lim"], dat["pi_gb"]

    wj = 0.0
    for j in range(P.shape[0]):
        sp = float(P[j, :].sum())
        wj += (lam_j[j] * D_auto[j] - 0.5 * th_j[j] * D_auto[j] ** 2
               + float(np.sum(P[j, :] * pi))
               - a[j] * sp ** 2 - b[j] * sp - c[j])

    I = len(pi)
    m = np.ones((I, I)) - np.eye(I)
    compe = [sum(m[i][k] * pi[k] * float(P[:, k].sum()) for k in range(I))
             for i in range(I)]
    wi = 0.0
    for i in range(I):
        consumo = G_lim[i] + float(P[:, i].sum())      # <- la pieza que falta
        wi += (lam_i[i] * consumo - 0.5 * th_i[i] * consumo ** 2
               + pi_gb * float(P[:, i].sum()) * np.log(1.0 / (pi[i] + 1.0))
               - compe[i] * be[i])
    return wj, wi


FORMAS = {"codigo": w_codigo, "articulo": w_articulo, "completo": w_completo}


def barre_escala(P, pi, dat, escalas=(1.0, 0.5, 0.1, 0.05, 0.01, 0.001)):
    """La prueba decisiva: la misma hora con el precio dividido por un factor.

    El logaritmo NO es invariante de escala, de modo que el signo del efecto de
    transar puede depender de las UNIDADES en que se midan los precios. La
    Tabla V del articulo reporta precios de 0,1 a 0,6 mientras su codigo usa de
    114 a 1.250: son las mismas cifras divididas por mil.

    Aqui se escala el precio y se vuelve a evaluar, SIN resolver de nuevo. El
    reparto se deja fijo a proposito: la pregunta es sobre la forma funcional,
    no sobre el equilibrio.
    """
    out = []
    for s in escalas:
        d = dict(dat)
        d["pi_gb"] = dat["pi_gb"] * s
        # el costo lineal del vendedor es un precio y escala con ellos
        d["b"] = np.asarray(dat["b"], float) * s
        d["lam_j"] = np.asarray(dat["lam_j"], float) * s
        d["lam_i"] = np.asarray(dat["lam_i"], float) * s
        d["th_j"] = np.asarray(dat["th_j"], float) * s
        d["th_i"] = np.asarray(dat["th_i"], float) * s
        fila = dict(escala=s, precio=float((pi * s).mean()))
        for nombre, f in FORMAS.items():
            wj0, wi0 = f(P * 0.0, pi * s, d)
            wj1, wi1 = f(P, pi * s, d)
            fila[nombre] = (wj1 + wi1) - (wj0 + wi0)
        out.append(fila)
    return out


def barre(P, pi, dat, n=41):
    """Escala lo transado de cero a uno y devuelve el bienestar en cada punto."""
    alfas = np.linspace(0.0, 1.0, n)
    out = {}
    for nombre, f in FORMAS.items():
        w = []
        for al in alfas:
            wj, wi = f(P * al, pi, dat)
            w.append(wj + wi)
        out[nombre] = np.asarray(w)
    return alfas, out


def _params(J, I):
    """Los del modelo, tal como los fija el orquestador con datos reales."""
    return dict(
        lam_j=np.full(J, 100.0), th_j=np.full(J, 0.5),
        a=np.zeros(J), b=np.full(J, 241.0), c=np.zeros(J),
        lam_i=np.full(I, 100.0), th_i=np.full(I, 0.5),
        et=np.full(I, 0.1), be=np.full(I, 0.1),
    )


def informa(etiqueta, alfas, w, escala):
    print(NL + f"  {etiqueta}   (precio medio {escala:.3f})", flush=True)
    print(f"  {'forma':>9s} {'W(0)':>14s} {'W(P*)':>14s} {'dif':>14s} "
          f"{'maximo en':>10s} {'sube al transar':>16s}", flush=True)
    fila = {}
    for nombre in FORMAS:
        v = w[nombre]
        k = int(np.argmax(v))
        sube = v[-1] > v[0] + 1e-9
        print(f"  {nombre:>9s} {v[0]:14.4f} {v[-1]:14.4f} {v[-1]-v[0]:+14.4f} "
              f"{alfas[k]:10.2f} {('si' if sube else 'NO'):>16s}", flush=True)
        fila[nombre] = dict(w0=float(v[0]), w1=float(v[-1]),
                            dif=float(v[-1] - v[0]), argmax=float(alfas[k]),
                            sube=bool(sube))
    return fila


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horas", type=int, default=8,
                    help="cuantas horas reales se miran")
    ap.add_argument("--cobertura", default="m1")
    args = ap.parse_args()

    from paso_a_paso import carga, carga_base, resuelve

    filas = []

    # 1 · el caso publicado, en su propia escala de precios
    print("=" * 78, flush=True)
    print("  1 · EL CASO PUBLICADO, en la escala de precios del articulo",
          flush=True)
    print("=" * 78, flush=True)
    base = carga_base()
    hechas = 0
    for k in range(base["D"].shape[1]):
        r = resuelve(base, k)
        if r is None:
            continue
        P, pi = np.asarray(r["P"], float), np.asarray(r["pi"], float)
        if P.sum() <= 1e-9 or not np.all(np.isfinite(pi)):
            continue
        J, I = P.shape
        d = _params(J, I)
        d.update(G_neto=r["G_net"], G_lim=r["g_klim"][r["bids"]],
                 D_auto=np.minimum(base["G"][r["sids"], k],
                                   base["D"][r["sids"], k]),
                 pi_gb=float(r["piso_h"]))
        print(f"{NL}  --- la prueba de la escala, hora {k} del caso publicado",
              flush=True)
        print(f"  {'escala':>8s} {'precio medio':>13s} "
              f"{'dif codigo':>14s} {'dif articulo':>14s}", flush=True)
        for e in barre_escala(P, pi, d):
            print(f"  {e['escala']:8.3f} {e['precio']:13.3f} "
                  f"{e['codigo']:+14.4f} {e['articulo']:+14.4f}", flush=True)
            filas.append(dict(caso="escala_publicado", hora=k,
                              forma="ambas", escala=e["escala"],
                              precio_medio=e["precio"],
                              dif_codigo=e["codigo"],
                              dif_articulo=e["articulo"]))
        alfas, w = barre(P, pi, d)
        f = informa(f"caso publicado, hora {k}", alfas, w, float(pi.mean()))
        for nom, v in f.items():
            filas.append(dict(caso="publicado", hora=k, forma=nom,
                              precio_medio=float(pi.mean()), **v))
        hechas += 1
        if hechas >= 3:
            break

    # 2 · el dato real, en pesos por kilovatio hora
    print(NL + "=" * 78, flush=True)
    print(f"  2 · EL DATO REAL ({args.cobertura.upper()}), en COP/kWh",
          flush=True)
    print("=" * 78, flush=True)
    dat = carga(args.cobertura)
    exc = np.maximum(dat["G"] - dat["D"], 0.0)
    dfc = np.maximum(dat["D"] - dat["G"], 0.0)
    act = [k for k in range(dat["D"].shape[1])
           if (exc[:, k] > 1e-9).sum() >= 2 and (dfc[:, k] > 1e-9).sum() >= 3]
    rng = np.random.default_rng(7)
    hechas = 0
    for k in rng.permutation(act):
        r = resuelve(dat, int(k))
        if r is None:
            continue
        P, pi = np.asarray(r["P"], float), np.asarray(r["pi"], float)
        if P.sum() <= 1e-9 or not np.all(np.isfinite(pi)):
            continue
        J, I = P.shape
        d = _params(J, I)
        d.update(G_neto=r["G_net"], G_lim=r["g_klim"][r["bids"]],
                 D_auto=np.minimum(dat["G"][r["sids"], int(k)],
                                   dat["D"][r["sids"], int(k)]),
                 pi_gb=float(r["piso_h"]))
        if hechas == 0:
            print(f"{NL}  --- la prueba de la escala, hora {int(k)} real",
                  flush=True)
            print(f"  {'escala':>8s} {'precio medio':>13s} "
                  f"{'dif codigo':>14s} {'dif articulo':>14s}", flush=True)
            for e in barre_escala(P, pi, d):
                print(f"  {e['escala']:8.3f} {e['precio']:13.3f} "
                      f"{e['codigo']:+14.4f} {e['articulo']:+14.4f}",
                      flush=True)
                filas.append(dict(caso="escala_real", hora=int(k),
                                  forma="ambas", escala=e["escala"],
                                  precio_medio=e["precio"],
                                  dif_codigo=e["codigo"],
                                  dif_articulo=e["articulo"]))
        alfas, w = barre(P, pi, d)
        f = informa(f"{args.cobertura} hora {int(k)}", alfas, w,
                    float(pi.mean()))
        for nom, v in f.items():
            filas.append(dict(caso=args.cobertura, hora=int(k), forma=nom,
                              precio_medio=float(pi.mean()), **v))
        hechas += 1
        if hechas >= args.horas:
            break

    d = pd.DataFrame(filas)
    print(NL + "=" * 78, flush=True)
    print("  RESUMEN · en cuantas horas sube el bienestar al transar",
          flush=True)
    print("=" * 78, flush=True)
    for caso in d.caso.unique():
        t = d[d.caso == caso]
        print(f"  {caso:>10s}  " + "  ".join(
            f"{nom}: {int(t[t.forma == nom].sube.sum())} de "
            f"{len(t[t.forma == nom])}" for nom in FORMAS), flush=True)

    SALIDA.mkdir(parents=True, exist_ok=True)
    csv = SALIDA / "bienestar_formas.csv"
    d.to_csv(csv, index=False, encoding="utf-8")
    nota = (
        "Generado por reformateo/documento/scripts/sonda/bienestar_formas.py",
        "Evalua las dos formas del bienestar sobre horas YA RESUELTAS,",
        "escalando lo transado de cero a uno. No resuelve de nuevo el juego.",
        "Ver H-58.",
    )
    (SALIDA / "bienestar_formas.fuente.txt").write_text(
        NL.join(nota) + NL, encoding="utf-8")
    print(NL + f"  csv: {csv}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
