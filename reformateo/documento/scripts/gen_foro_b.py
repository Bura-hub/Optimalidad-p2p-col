"""
Grupo B: lo que el modelo base hacía y este trabajo no reproducía.

POR QUÉ VIVE APARTE. Las demás figuras del foro leen del almacén y no vuelven a
simular. Estas dos **no pueden**: exigen correr el modelo con parámetros que la
corrida oficial no usa. Separarlas es lo que permite que la regla de aquel
guion siga siendo cierta sin excepciones, en vez de tener una regla con una nota
al pie.

SON DOS HUECOS, y conviene llenarlos porque sostienen el método:

  B1 · CON FILTRO Y SIN ÉL. Es la figura 3 del modelo base. La autora muestra
       que el sistema **sin filtrar oscila de forma permanente alrededor del
       óptimo** en vez de converger, y que el filtro es lo que lo estabiliza.
       Los parámetros del filtro existen en esta traducción desde el primer día
       y **nadie los había puesto a prueba**.

       QUÉ ES EL FILTRO, con precisión: un paso bajo de primer orden sobre los
       multiplicadores de las dos restricciones del vendedor. Lo que entra en
       su dinámica no es el multiplicador crudo sino su versión suavizada. De
       ahí que la constante de tiempo tendiendo a cero **sea** el sistema sin
       filtrar: la suavizada persigue a la cruda instantáneamente.

  B2 · EL BARRIDO DEL TÉRMINO DE RIVALIDAD. Es su figura 12. El término mide
       cuánto le molesta a un comprador que otros compren, y es el único
       parámetro del modelo que representa competencia entre los del mismo
       lado. La pregunta es qué le hace al precio y a la asignación.

LO QUE NO SE HACE AQUÍ, y se declara: no se cambia ningún valor de producción.
Las dos figuras miden, y lo que midan va al registro.

Uso:
    python gen_foro_b.py --cobertura m1
    python gen_foro_b.py --cobertura m1 --hora 4741
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
SONDA = AQUI / "sonda"
for _p in (RAIZ, AQUI, SONDA):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import estilo as E  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

# Las cuatro constantes que se contrastan. La de produccion es la primera; las
# demas son fracciones de ella, y la ultima es el sistema practicamente sin
# filtrar.
TAUS = (0.001, 1e-4, 1e-5, 1e-6)


def _hora_activa(dat: dict) -> int:
    """Una hora con mercado de verdad: al menos dos de cada lado."""
    D, G = dat["D"], dat["G"]
    exc = np.maximum(G - D, 0.0)
    dfc = np.maximum(D - G, 0.0)
    act = [k for k in range(D.shape[1])
           if (exc[:, k] > 1e-9).sum() >= 2 and (dfc[:, k] > 1e-9).sum() >= 2]
    if not act:
        raise ValueError("no hay ninguna hora con dos vendedores y dos "
                         "compradores en esta frontera")
    return int(np.median(act))


def b1_filtro(cobertura: str, k: int | None = None):
    """El sistema con filtro y sin él, sobre la misma hora.

    Si la afirmación del modelo base se sostiene, al aflojar la constante de
    tiempo del filtro la trayectoria del precio debe dejar de asentarse y
    empezar a oscilar.

    MEDIDO, Y SALE AL REVÉS. Sobre la hora 2363 de la primera frontera, con la
    constante de producción la trayectoria **no ha terminado de asentarse** al
    final del horizonte —su último tercio recorre 53,29 (COP/kWh)— mientras que
    con el filtro mil veces más rápido se asienta casi de inmediato y su último
    tercio recorre 0,0002. El precio final pasa de 137,45 a 112,87.

    De modo que en este caso el filtro **no estabiliza: retarda**, y la figura
    3 del modelo base no se reproduce. Se registra como H-65, y con dos
    cautelas: es UNA hora, y la vía de producción itera además el criterio de
    participación por encima de esta integración. La medición amplia va al
    servidor.
    """
    from paso_a_paso import carga, resuelve

    dat = carga(cobertura)
    if k is None:
        k = _hora_activa(dat)

    filas, curvas = [], []
    for tau in TAUS:
        r = resuelve(dat, k, multiplicadores=True,
                     solucionador=dict(tau_sellers=tau, tau_buyers=10 * tau))
        if r is None:
            continue
        tr = r.get("tr")
        if tr is None or not hasattr(tr, "t"):
            continue
        pi = np.asarray(getattr(tr, "pi_t", []), float)
        if pi.size == 0:
            continue
        # Se dibuja el precio del PRIMER comprador: la pregunta es si la
        # trayectoria se asienta o no, y para eso una serie basta. Dibujar las
        # cuatro convertiria la figura en una maraña donde no se ve nada.
        #
        # La orientacion de la matriz se DEDUCE del numero de pasos y no se
        # supone: el solucionador la devuelve con los compradores en las filas
        # y confundir los ejes da una serie de tres puntos que matplotlib
        # rechaza, que es como se detecto.
        t = np.asarray(tr.t, float)
        if pi.ndim == 2:
            serie = pi[0, :] if pi.shape[1] == t.size else pi[:, 0]
        else:
            serie = pi
        curvas.append((tau, t, serie))
        # La medida de si oscila: la amplitud de lo que queda en el ULTIMO
        # tercio de la integracion, cuando ya deberia estar asentado.
        cola = serie[int(len(serie) * 2 / 3):]
        filas.append(dict(tau=tau, amplitud_cola=float(cola.max() - cola.min()),
                          precio_final=float(serie[-1])))

    if not curvas:
        print("  [omitida] el solucionador no devolvió trayectorias de precio")
        return None

    fig, ax = E.figura(alto=3.6)
    colores = [E.DESPUES, "#5B8FA8", E.ALERTA, "#7B3F00"]
    for (tau, t, y), c in zip(curvas, colores):
        rot = ("con filtro (producción)" if tau == TAUS[0]
               else f"filtro {int(TAUS[0] / tau)} veces más rápido")
        ax.plot(t, y, linewidth=2.0, color=c, label=rot)
    ax.set_xlabel("Tiempo de integración")
    ax.set_ylabel("Precio del primer comprador (COP/kWh)")
    ax.set_title("El filtro no estabiliza en esta hora: retarda", pad=8)
    ax.legend(loc="best", fontsize=8, frameon=False)
    E.eje_espanol(ax, "y", "miles", 0)

    d = pd.DataFrame(filas)
    base = d.loc[d["tau"] == TAUS[0]].iloc[0]
    # El contraste es con la constante MAS RAPIDA, no con la de mayor
    # amplitud: la de mayor amplitud resulto ser la de produccion, de modo que
    # el pie se comparaba consigo mismo y anunciaba dos veces la misma cifra.
    rapido = d.loc[d["tau"].idxmin()]
    fig.text(0.01, 0.005,
             f"Nota. Hora {k} de la frontera {cobertura.upper()}. El filtro es "
             f"un paso bajo sobre los multiplicadores del vendedor, de modo "
             f"que acortar su constante de tiempo equivale a quitarlo. La "
             f"amplitud del último tercio de la trayectoria vale "
             f"{E.fmt_miles(base['amplitud_cola'], 3)} con la constante de "
             f"producción y {E.fmt_miles(rapido['amplitud_cola'], 4)} "
             f"(COP/kWh) con el filtro mil veces más rápido, y el precio final "
             f"pasa de {E.fmt_miles(base['precio_final'], 2)} a "
             f"{E.fmt_miles(rapido['precio_final'], 2)}. Es decir, en esta "
             f"hora el filtro no estabiliza: retarda. La figura 3 del modelo "
             f"base, donde el sistema sin filtrar oscila de forma permanente, "
             f"no se reproduce aquí.",
             fontsize=6.6, color=E.NEUTRO, ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.215, 1, 1))
    return E.guardar(fig, f"foro_b1_filtro_{cobertura}", datos=d,
                     procedencia=[f"mediciones MTE, frontera {cobertura}, "
                                  f"hora {k}; núcleo del modelo"])


def _una_rivalidad(dat: dict, k: int, v: float):
    """Un punto del barrido, en su propio proceso.

    RECIBE EL DATO YA CARGADO, y no la frontera. Cargarlo dentro costaba mas
    que resolver la hora: en Windows cada proceso hijo arranca de cero y
    reimporta el modulo entero, de modo que el plazo se consumia leyendo
    mediciones en vez de integrando. Con el dato hecho, el plazo mide lo que
    debe medir.

    Vive fuera de la funcion que lo llama porque el proceso hijo tiene que
    poder encontrarla por nombre.
    """
    import numpy as _np
    from paso_a_paso import resuelve as _resuelve

    r = _resuelve(dat, k, params=dict(etha=v))
    if r is None:
        return None
    pi = _np.asarray(r["pi"], float)
    P = _np.asarray(r["P"], float)
    return dict(rivalidad=v,
                precio_medio=float(_np.mean(pi)),
                precio_minimo=float(_np.min(pi)),
                precio_maximo=float(_np.max(pi)),
                energia_kwh=float(_np.sum(P)),
                retirados=len(r.get("retirados", [])))


def _envuelve(cola, dat: dict, k: int, v: float) -> None:
    """Corre un punto del barrido y deja el resultado en la cola.

    El hijo tiene que poder morir sin llevarse al padre, de modo que cualquier
    fallo suyo se convierte en «no resolvio» y no en una traza que nadie ve.
    """
    try:
        cola.put(_una_rivalidad(dat, k, v))
    except Exception:                              # noqa: BLE001
        cola.put(None)


def b2_rivalidad(cobertura: str, k: int | None = None,
                 valores=(0.0, 0.05, 0.1, 0.2, 0.4, 0.8),
                 plazo: float = 240.0):
    """El barrido del término de rivalidad entre compradores.

    Mide qué le hace al precio acordado y a la energía asignada. El valor de
    producción es 0,1 y viene del modelo base sin justificación medida, de modo
    que saber cuánto mueve el resultado es parte de poder defenderlo.
    """
    from paso_a_paso import carga, resuelve

    dat = carga(cobertura)
    if k is None:
        k = _hora_activa(dat)

    # CADA VALOR CON SU PLAZO, y es la lección de C-156 aplicada aquí. El
    # primer intento de este barrido se quedó quince minutos en un valor sin
    # decir cuál: el integrador se vuelve rígido para ciertos coeficientes,
    # igual que se vuelve al aflojar el filtro. Un barrido que se cuelga en un
    # punto no mide nada y además esconde CUÁL fue el punto.
    #
    # El valor que no resuelve dentro del plazo **se anota como tal** y el
    # barrido sigue. Un hueco declarado en la figura es un resultado; un
    # barrido que nunca termina, no.
    # UN PROCESO POR VALOR, y se termina si se pasa del plazo.
    #
    # El primer intento uso un ejecutor con un solo obrero, y no sirve: un
    # ejecutor NO PUEDE CANCELAR una tarea que ya esta corriendo. El plazo
    # vencia, la tarea seguia ocupando al unico obrero, el siguiente valor
    # quedaba en cola detras de ella y al cerrar el ejecutor la espera era
    # infinita. El plazo estaba escrito pero no mordia.
    #
    # Un proceso propio por valor si se puede terminar, y es la unica forma de
    # que un barrido con un punto rigido termine.
    import multiprocessing as mp

    filas = []
    for v in valores:
        cola = mp.Queue()
        pr = mp.Process(target=_envuelve, args=(cola, dat, k, float(v)))
        pr.start()
        pr.join(plazo)
        if pr.is_alive():
            pr.terminate()
            pr.join(5)
            print(f"  rivalidad {v}: no resuelve en {plazo:.0f} s")
            filas.append(dict(rivalidad=v, precio_medio=np.nan,
                              precio_minimo=np.nan, precio_maximo=np.nan,
                              energia_kwh=np.nan, retirados=-1,
                              resuelta=False))
            continue
        r = cola.get() if not cola.empty() else None
        if r is None:
            print(f"  rivalidad {v}: esa hora no abre mercado")
            continue
        r["resuelta"] = True
        filas.append(r)
        print(f"  rivalidad {v}: precio {r['precio_medio']:.2f}, "
              f"energía {r['energia_kwh']:.3f} kWh")

    d = pd.DataFrame(filas)
    if d.empty or not d["resuelta"].any():
        print("  [omitida] ningún valor del barrido resolvió")
        return None
    # Solo se DIBUJA lo que resolvió; lo que no, queda en la tabla de datos y
    # se cuenta en el pie.
    sin = int((~d["resuelta"]).sum())
    d_ok = d[d["resuelta"]].reset_index(drop=True)

    fig, ax = E.figura(alto=3.2)
    ax2 = ax.twinx()
    ax.plot(d_ok["rivalidad"], d_ok["precio_medio"], marker="o", markersize=5,
            linewidth=2.2, color=E.DESPUES, label="precio acordado")
    ax.fill_between(d_ok["rivalidad"], d_ok["precio_minimo"],
                    d_ok["precio_maximo"],
                    color=E.DESPUES, alpha=0.14, linewidth=0)
    ax2.plot(d_ok["rivalidad"], d_ok["energia_kwh"], marker="s", markersize=4.5,
             linewidth=2.0, color=E.ALERTA, linestyle="--",
             label="energía asignada")
    ax.axvline(0.1, color=E.NEUTRO, linewidth=1.0, linestyle=":")
    ax.annotate("valor de producción", xy=(0.1, ax.get_ylim()[0]), fontsize=7,
                color=E.NEUTRO, ha="left", va="bottom", rotation=90,
                xytext=(3, 4), textcoords="offset points")
    ax.set_xlabel("Coeficiente de rivalidad entre compradores")
    ax.set_ylabel("Precio (COP/kWh)")
    ax2.set_ylabel("Energía asignada (kWh)", color=E.ALERTA)
    ax2.tick_params(axis="y", colors=E.ALERTA)
    # EL EJE DERECHO NO SE DEJA AUTOESCALAR, y es la diferencia entre una
    # figura honesta y una enganosa. Con la serie plana, el escalado
    # automatico abre un rango de 10^-11 alrededor del valor y saca un factor
    # comun en la esquina: la linea recta aparece con estructura y el lector
    # ve variacion donde no la hay. Se ancla un rango con sentido fisico.
    e0 = float(d_ok["energia_kwh"].mean())
    margen = max(0.05 * abs(e0), 0.5)
    ax2.set_ylim(e0 - margen, e0 + margen)
    ax2.ticklabel_format(axis="y", useOffset=False, style="plain")
    # Y el titulo dice el RESULTADO, no la pregunta. La figura contesta que no
    # mueve nada, y un titulo interrogativo obligaria a leer el pie para
    # saberlo.
    plano = (rp_prev := float(d_ok["precio_medio"].max()
                              - d_ok["precio_medio"].min())) <= 1e-6
    ax.set_title("La rivalidad entre compradores no mueve el resultado"
                 if plano else
                 "Cuánto mueve la rivalidad entre compradores", pad=8)
    E.eje_espanol(ax, "y", "miles", 0)

    rp = (d_ok["precio_medio"].max() - d_ok["precio_medio"].min())
    re = (d_ok["energia_kwh"].max() - d_ok["energia_kwh"].min())
    veredicto = (
        f"Sobre el barrido completo el precio acordado NO se mueve —recorre "
        f"{E.fmt_miles(rp, 2)} (COP/kWh)— y la energía asignada tampoco, con "
        f"{E.fmt_miles(re, 3)} (kWh). Es la misma conclusión de H-62 medida "
        f"sobre el parámetro que el modelo base barre en su figura 12."
        if rp <= 1e-6 and re <= 1e-6 else
        f"El precio acordado recorre {E.fmt_miles(rp, 2)} (COP/kWh) y la "
        f"energía asignada {E.fmt_miles(re, 3)} (kWh).")
    hueco = ("" if sin == 0 else
             f" Quedan {sin} valores fuera: el integrador no resuelve en "
             f"{plazo:.0f} s para ese coeficiente, y así consta en la tabla "
             f"de datos.")
    fig.text(0.01, 0.005,
             f"Nota. Hora {k} de la frontera {cobertura.upper()}, sobre "
             f"{len(d_ok)} de {len(d)} valores del barrido. {veredicto} La "
             f"banda azul es el intervalo entre el precio del comprador más "
             f"barato y el del más caro, y no una incertidumbre: mide la "
             f"dispersión ENTRE compradores, no el efecto del barrido. El eje "
             f"de la derecha lleva un rango fijo a propósito, porque el "
             f"automático abriría una escala de milmillonésimas y haría "
             f"parecer que hay variación.{hueco}",
             fontsize=6.6, color=E.NEUTRO, ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.245, 1, 1))
    return E.guardar(fig, f"foro_b2_rivalidad_{cobertura}", datos=d,
                     procedencia=[f"mediciones MTE, frontera {cobertura}, "
                                  f"hora {k}; núcleo del modelo"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cobertura", default="m1")
    ap.add_argument("--hora", type=int, default=None)
    ap.add_argument("--figuras", default=None)
    a = ap.parse_args()
    if a.figuras:
        E.DIR_FIGURAS = Path(a.figuras)
        E.DIR_FIGURAS.mkdir(parents=True, exist_ok=True)

    print("\nGrupo B · lo que el modelo base hacía y no reproducíamos")
    b1_filtro(a.cobertura, a.hora)
    b2_rivalidad(a.cobertura, a.hora)
    print(f"\nen {E.DIR_FIGURAS}")


if __name__ == "__main__":
    import multiprocessing as _mp

    _mp.freeze_support()          # obligatorio en Windows
    main()
