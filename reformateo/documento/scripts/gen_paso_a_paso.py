"""
Las tres figuras del paso a paso de una hora (CAL-47 y CAL-48).

Enseñan, sobre una hora concreta, qué hace la normativa base con el
excedente de cada institución y qué hace en su lugar el mercado entre
pares, con las cotas medidas y el solucionador acoplado.

  f6_10  el estado de la hora: quién genera, quién consume, quién vende
  f6_11  la banda de cada agente y dónde cae el acuerdo
  f6_12  la trayectoria del precio y el reparto que resulta

Las tres se generan solo si la sonda `sonda/paso_a_paso.py` da por buena la
hora, es decir si el precio queda dentro de la banda y ningún vendedor
queda por debajo de su alternativa.

Uso:
    python gen_paso_a_paso.py
    python gen_paso_a_paso.py --hora 2342
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI / "sonda"))

import estilo as E  # noqa: E402
from paso_a_paso import carga, resuelve  # noqa: E402

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado",
        "domingo"]


def _n(x, dec=2):
    """Número con coma decimal y signo menos tipográfico."""
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def f610_estado(dat, r, ts):
    """Quién genera, quién consume y quién acaba vendiendo."""
    nom = dat["nombres"]
    k = r["k"]
    gen = dat["G"][:, k]
    dem = dat["D"][:, k]
    y = np.arange(len(nom))

    fig, ax = E.figura(alto=3.1)
    ax.barh(y + 0.19, gen, height=0.34, color=E.NEUTRO,
            edgecolor="black", linewidth=0.5, label="Generación")
    ax.barh(y - 0.19, dem, height=0.34, color="white", hatch="////",
            edgecolor="black", linewidth=0.5, label="Demanda")

    for n in range(len(nom)):
        neto = gen[n] - dem[n]
        papel = ("vende" if n in r["sids"] else
                 "compra" if n in r["bids"] else "sin papel")
        ax.text(max(gen[n], dem[n]) + 0.5, y[n],
                f"{papel}  {_n(neto)} kW", va="center", fontsize=7.5)

    ax.set_yticks(y)
    ax.set_yticklabels([E.etiqueta_corta(x) for x in nom])
    ax.invert_yaxis()
    ax.set_xlabel("Potencia media de la hora (kW)")
    ax.set_xlim(0, max(gen.max(), dem.max()) * 1.42)
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    ax.grid(axis="x", alpha=0.3)

    datos = pd.DataFrame({"institucion": nom, "generacion_kW": gen,
                          "demanda_kW": dem, "neto_kW": gen - dem})
    return fig, datos


def f611_banda(dat, r, ts):
    """La banda de cada agente y el precio en que se cierra el acuerdo."""
    nom = dat["nombres"]
    k = r["k"]
    fig, ax = E.figura(alto=3.4)

    filas = []
    etiquetas = []
    pos = 0
    techo_max = float(np.max(r["techo_i"]))

    # Cada VENDEDOR: su margen va desde su propia alternativa hasta el techo
    # mas alto que algun comprador le puede pagar. Se ve de un vistazo que
    # Mariana tiene menos sitio que el CESMAG, y por que: compran a
    # comercializadores distintos y por eso su permuta les paga distinto.
    for a, j in enumerate(r["sids"]):
        piso = dat["piso"][j, k]
        tramo = "permuta" if dat["perm"][j, k] else "bolsa"
        ax.plot([piso, techo_max], [pos, pos], color=E.NEUTRO, lw=6,
                solid_capstyle="butt", alpha=0.30)
        ax.plot([piso, piso], [pos - 0.28, pos + 0.28], color="black", lw=2.4)
        ax.annotate(f"{_n(piso)}", (piso, pos), fontsize=7.5,
                    xytext=(0, 11), textcoords="offset points", ha="center")
        cobra = float(np.max(r["pi"][r["P"][a, :] > 1e-9]))             if (r["P"][a, :] > 1e-9).any() else np.nan
        if np.isfinite(cobra):
            ax.plot([cobra], [pos], marker="o", ms=7, color="black", zorder=5)
        etiquetas.append(f"{E.etiqueta_corta(nom[j])} vende ({tramo})")
        filas.append(dict(agente=nom[j], papel="vende", cota=piso,
                          tipo=f"piso ({tramo})", acordado=cobra))
        pos += 1

    # Cada COMPRADOR: desde el piso vigente de la hora hasta su propio techo.
    for i, b in enumerate(r["bids"]):
        techo = r["techo_i"][i]
        ax.plot([r["piso_h"], techo], [pos, pos], color=E.NEUTRO, lw=6,
                solid_capstyle="butt", alpha=0.30)
        ax.plot([techo, techo], [pos - 0.28, pos + 0.28], color="black", lw=2.4)
        ax.annotate(f"{_n(techo)}", (techo, pos), fontsize=7.5,
                    xytext=(0, 11), textcoords="offset points", ha="center")
        ax.plot([r["pi"][i]], [pos], marker="o", ms=7, color="black", zorder=5)
        etiquetas.append(f"{E.etiqueta_corta(nom[b])} compra")
        filas.append(dict(agente=nom[b], papel="compra", cota=techo,
                          tipo="techo", acordado=r["pi"][i]))
        pos += 1

    ax.set_yticks(range(pos))
    ax.set_yticklabels(etiquetas)
    ax.invert_yaxis()
    ax.set_xlabel("Precio (COP/kWh)")
    ax.grid(axis="x", alpha=0.3)
    ax.margins(x=0.14)
    ax.set_ylim(pos - 0.4, -0.9)
    ax.annotate("el acuerdo", (r["pi"][0], -0.55), fontsize=8.5,
                ha="center", va="center")
    ax.plot([r["pi"][0], r["pi"][0]], [-0.35, pos - 0.55], color="black",
            lw=0.7, ls="--", alpha=0.55, zorder=1)
    return fig, pd.DataFrame(filas)


def f612_trayectoria(dat, r, ts):
    """Cómo llega el precio al acuerdo, y cómo se reparte lo que crea."""
    nom = dat["nombres"]
    k = r["k"]
    import matplotlib.pyplot as plt
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(E.ANCHO_COMPLETO, 4.1),
        gridspec_kw={"height_ratios": [3.0, 1.0], "hspace": 0.55})

    t = r["tr"].t
    traj = r["tr"].pi_t
    # Las tres trayectorias se superponen: los compradores convergen al
    # mismo precio y difieren en la cuarta cifra decimal. Dibujar tres
    # lineas de colores y una leyenda de tres prometeria una distincion que
    # no existe ni sobrevive impresa, de modo que se dibuja una sola y se
    # declara la dispersion, que es la magnitud informativa.
    for i in range(traj.shape[0]):
        ax1.plot(t, traj[i], lw=1.4, color="black")
    disp = float(np.max(traj[:, -1]) - np.min(traj[:, -1]))
    techo_max = float(np.max(r["techo_i"]))
    ax1.axhline(r["piso_h"], color=E.NEUTRO, lw=1.1, ls=":")
    ax1.axhline(techo_max, color=E.NEUTRO, lw=1.1, ls=":")
    # Las cotas se rotulan a la IZQUIERDA, que es donde queda hueco: a la
    # derecha vive el acuerdo y abajo la nota, y ahi se estorbaban.
    ax1.annotate(f"techo {_n(techo_max)}", (t[0], techo_max), fontsize=7.5,
                 xytext=(4, -12), textcoords="offset points", ha="left")
    ax1.annotate(f"piso {_n(r['piso_h'])}", (t[0], r["piso_h"]),
                 fontsize=7.5, xytext=(4, 7), textcoords="offset points",
                 ha="left")
    ax1.annotate(f"acuerdo {_n(float(traj[0, -1]))}",
                 (t[-1], float(traj[0, -1])), fontsize=8,
                 xytext=(-4, 9), textcoords="offset points", ha="right")
    ax1.text(0.98, 0.06, f"las {traj.shape[0]} trayectorias se superponen; "
             f"difieren en {_n(disp, 4)} COP/kWh",
             transform=ax1.transAxes, ha="right", fontsize=7.5,
             style="italic")
    ax1.set_xlabel("Tiempo de la negociación")
    ax1.set_ylabel("Precio (COP/kWh)")
    ax1.grid(alpha=0.3)

    pv = ac = 0.0
    detalle = []
    for a, j in enumerate(r["sids"]):
        for i, b in enumerate(r["bids"]):
            q = float(r["P"][a, i])
            if q <= 1e-9:
                continue
            p = r["pi"][i]
            v = (p - dat["piso"][j, k]) * q
            c = (r["techo_i"][i] - p) * q
            pv += v; ac += c
            detalle.append(dict(vendedor=nom[j], comprador=nom[b],
                                kWh=q, precio=p, prima_vendedor=v,
                                ahorro_comprador=c))
    tot = pv + ac
    ax2.barh([0], [100 * pv / tot], color=E.NEUTRO, edgecolor="black",
             linewidth=0.5, height=0.5)
    ax2.barh([0], [100 * ac / tot], left=[100 * pv / tot], color="white",
             hatch="////", edgecolor="black", linewidth=0.5, height=0.5)
    ax2.text(100 * pv / tot / 2, 0, f"vendedor\n{_n(100*pv/tot, 1)} %",
             ha="center", va="center", fontsize=8)
    # Texto negro sobre rayado negro no se lee: va sobre fondo blanco. El
    # rayado se queda, que es lo que hace la distincion sobrevivir en gris.
    ax2.text(100 * pv / tot + 100 * ac / tot / 2, 0,
             f"comprador\n{_n(100*ac/tot, 1)} %", ha="center", va="center",
             fontsize=8,
             bbox=dict(boxstyle="round,pad=0.28", facecolor="white",
                       edgecolor="none"))
    ax2.set_xlim(0, 100)
    ax2.set_yticks([])
    ax2.set_xlabel(f"Reparto del excedente de la hora "
                   f"({_n(tot, 1)} COP)")
    return fig, pd.DataFrame(detalle)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hora", type=int, default=2342)
    ap.add_argument("--cobertura", default="m1", choices=["m1", "m3"])
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    E.aplicar_estilo()
    dat = carga(args.cobertura)
    r = resuelve(dat, args.hora)
    if r is None:
        raise SystemExit(f"la hora {args.hora} no tiene mercado")

    ts = pd.DatetimeIndex(dat["idx"])[args.hora]
    proc = ["MedicionesMTE_v3 vía data/preprocessing.py",
            "data/tarifas_asc_mensual.csv y data/tarifas_cedenar_mensual.csv",
            "data/precios_bolsa_xm_api.csv",
            "core/coupled_ode_convergence.py (CAL-48, horizonte 0,05)"]

    # En esta maquina sobrescribir un PNG existente falla con «argumento
    # invalido», que es un bloqueo del sistema de ficheros y no del codigo.
    # Se retira el archivo antes de escribirlo.
    for viejo in ("f6_10_estado_hora", "f6_11_banda_acuerdo",
                  "f6_12_trayectoria_reparto"):
        for ext in (".png", ".csv", ".fuente.txt"):
            f = E.DIR_FIGURAS / f"{viejo}{ext}"
            if f.exists():
                try:
                    f.unlink()
                except OSError:
                    pass

    for nombre, fn in [("f6_10_estado_hora", f610_estado),
                       ("f6_11_banda_acuerdo", f611_banda),
                       ("f6_12_trayectoria_reparto", f612_trayectoria)]:
        fig, datos = fn(dat, r, ts)
        ruta = E.guardar(fig, nombre, datos=datos, procedencia=proc)
        print(f"  {ruta.name}  ({len(datos)} filas de rastro)")

    print(f"\n  Hora {args.hora}: {ts:%Y-%m-%d %H:%M}, {DIAS[ts.dayofweek]}.")
    print(f"  Acuerdo en {_n(r['pi'][0])} COP/kWh, al "
          f"{_n(100*(r['pi'][0]-r['piso_h'])/(r['techo_i'][0]-r['piso_h']), 0)} % "
          f"de la banda.")


if __name__ == "__main__":
    main()
