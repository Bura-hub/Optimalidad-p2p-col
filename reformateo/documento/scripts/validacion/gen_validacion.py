"""
Las figuras del aparato de validacion horaria.

Cinco del dia, con panel doble M1 y M3, y un mosaico por hora testigo y
frontera. La hora testigo va en mosaico y no en seis laminas sueltas porque
es UNA unidad narrativa: separarla obliga al lector a recomponerla.

TODA figura declara que la via acoplada NO es el metodo con el que se
produjeron las cifras publicadas, que salieron de la via alternada.

Uso:
    python gen_validacion.py --dia 2025-05-02
    python gen_validacion.py --dia 2025-05-02 --solo panorama
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[3]
SONDA = AQUI.parent / "sonda"
for _p in (RAIZ, SONDA, AQUI.parent, AQUI.parent.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(AQUI.parent))
import estilo as E  # noqa: E402
from validacion import dia as Dia, factura as Fac  # noqa: E402

SALIDA = AQUI.parent.parent / "validacion_horaria"
AVISO = ("Vía acoplada, que no es el método con el que se produjeron "
         "las cifras publicadas")


def _guarda(fig, nombre, datos, fuentes):
    """Guarda en la carpeta del aparato, con su tabla y su procedencia."""
    SALIDA.mkdir(parents=True, exist_ok=True)
    png = SALIDA / f"{nombre}.png"
    if png.exists():
        png.unlink()          # los ficheros sincronizados se bloquean
    fig.savefig(png, dpi=200, bbox_inches="tight", facecolor="white")
    if datos is not None:
        d = datos if isinstance(datos, pd.DataFrame) else pd.DataFrame(datos)
        d.to_csv(SALIDA / f"{nombre}.csv", index=False, encoding="utf-8-sig")
    (SALIDA / f"{nombre}.fuente.txt").write_text(
        f"Figura: {nombre}\nVía: acoplada (CAL-48), NO la del canon\n"
        "Artefactos leidos:\n" + "\n".join(f"  - {f}" for f in fuentes) + "\n",
        encoding="utf-8")
    plt.close(fig)
    print(f"  [figura] {png.name}")


def _pie(fig, texto=AVISO):
    fig.text(0.5, -0.005, texto, ha="center", va="top", fontsize=7.5,
             color=E.TINTA, style="italic")


# ══ v01 · el panorama del día ═══════════════════════════════════════════
def v01_panorama(dia_txt, datos):
    fig, axes = plt.subplots(3, 2, figsize=(E.ANCHO_COMPLETO, 6.2),
                             sharex="col")
    for col, cob in enumerate(("m1", "m3")):
        tabla = datos[cob]["tabla"]
        color = E.COBERTURAS[cob]
        act = tabla[tabla.resuelta]
        x = np.arange(len(tabla))
        xa = np.array([i for i, r in enumerate(tabla.itertuples())
                       if r.resuelta])

        axes[0, col].set_title(E.titulo_cobertura(cob, dos_lineas=True),
                               color=color, fontweight="bold", pad=8)
        # energía: lo que se ofrece, lo que se pide y lo que se mueve
        axes[0, col].bar(x, tabla.demanda, color=E.APAGADO, label="demanda neta")
        axes[0, col].bar(x, tabla.oferta, color=color, alpha=0.35,
                         label="oferta neta")
        axes[0, col].plot(xa, act.volumen, "o-", color=E.TINTA, ms=3, lw=1.2,
                          label="transado")
        axes[0, col].set_yscale("symlog", linthresh=1)
        if col == 0:
            axes[0, col].set_ylabel("Energía (kWh)")
            axes[0, col].legend(fontsize=7, frameon=False, loc="upper left")

        # precio dentro de su banda
        axes[1, col].plot(xa, act.precio, "D-", color=color, ms=4, lw=1.2)
        for i, r in zip(xa, act.itertuples()):
            axes[1, col].annotate(f"{int(r.pegados)}/{int(r.n_precios)}",
                                  (i, r.precio), fontsize=6, ha="center",
                                  va="bottom", color=E.TINTA)
        if col == 0:
            axes[1, col].set_ylabel("Precio medio (COP/kWh)")

        # reparto entre quien vende y quien compra
        axes[2, col].axhline(50, color=E.TINTA, lw=0.8, ls="--")
        axes[2, col].bar(xa, act.tajada_vendedor, color=E.VENDE, width=0.8)
        axes[2, col].bar(xa, 100 - act.tajada_vendedor,
                         bottom=act.tajada_vendedor, color=E.COMPRA, width=0.8)
        axes[2, col].set_ylim(0, 100)
        if col == 0:
            axes[2, col].set_ylabel("Reparto (%)")
        axes[2, col].set_xticks(x[::3])
        axes[2, col].set_xticklabels(tabla.hora[::3], rotation=45, fontsize=7)

    for ax in axes.ravel():
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle(f"El mercado hora a hora · {dia_txt}", fontweight="bold")
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    _pie(fig)
    tabla = pd.concat([datos[c]["tabla"].assign(frontera=c.upper())
                       for c in ("m1", "m3")])
    _guarda(fig, f"v01_panorama_{dia_txt}", tabla,
            [f"validacion_horaria/cache/horas_{c}_{dia_txt}.pkl"
             for c in ("m1", "m3")])


# ══ v02 · quién vende y quién compra ════════════════════════════════════
def v02_papeles(dia_txt, datos):
    fig, ax1, ax3 = E.figura_m1_m3(alto=3.0)
    filas = []
    for ax, cob in ((ax1, "m1"), (ax3, "m3")):
        horas = datos[cob]["horas"]
        tabla = datos[cob]["tabla"]
        ks = list(tabla.k)
        nombres = None
        for m, k in enumerate(ks):
            h = horas[k]
            if not h.resuelta:
                continue
            nombres = h.nombres
            for n in range(len(h.nombres)):
                if h.papel[n] == "vende":
                    c, y = E.VENDE, 1
                elif h.papel[n] == "compra":
                    c, y = E.COMPRA, -1
                else:
                    continue
                ax.barh(n, 0.8, left=m - 0.4, height=0.7, color=c)
                filas.append(dict(frontera=cob.upper(), k=k,
                                  institucion=h.nombres[n], papel=h.papel[n]))
        if nombres:
            ax.set_yticks(range(len(nombres)))
            ax.set_yticklabels([E.etiqueta_institucion(x) for x in nombres],
                               fontsize=8)
        ax.set_xticks(range(0, len(ks), 3))
        ax.set_xticklabels(tabla.hora[::3], rotation=45, fontsize=7)
        ax.grid(axis="x", alpha=0.2)
    ax1.set_xlabel("")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=E.VENDE, label="vende"),
                        Patch(color=E.COMPRA, label="compra")],
               loc="lower center", ncol=2, frameon=False,
               bbox_to_anchor=(0.5, -0.02), fontsize=8.5)
    fig.suptitle(f"Quién vende y quién compra, hora a hora · {dia_txt}",
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0.08, 1, 0.94))
    _pie(fig)
    _guarda(fig, f"v02_papeles_{dia_txt}", pd.DataFrame(filas),
            [f"validacion_horaria/cache/horas_{c}_{dia_txt}.pkl"
             for c in ("m1", "m3")])


# ══ v03 · la factura comparada ══════════════════════════════════════════
def v03_factura(dia_txt, datos):
    fig, ax1, ax3 = E.figura_m1_m3(alto=3.4)
    todo = []
    for ax, cob in ((ax1, "m1"), (ax3, "m3")):
        f = datos[cob]["factura"]
        todo.append(f.assign(frontera=cob.upper()))
        y = np.arange(len(f))
        ax.barh(y - 0.2, f.beneficio_vendedor, height=0.38, color=E.VENDE,
                label="gana como vendedora")
        ax.barh(y + 0.2, f.beneficio_comprador, height=0.38, color=E.COMPRA,
                label="gana como compradora")
        ax.axvline(0, color=E.TINTA, lw=0.8)
        ax.set_yticks(y)
        ax.set_yticklabels([E.etiqueta_institucion(n) for n in f.institucion],
                           fontsize=8)
        ax.grid(axis="x", alpha=0.25)
        ax.set_xlabel("Lo que deja de pagar (COP)")
    ax1.legend(fontsize=7.5, frameon=False, loc="lower right")
    fig.suptitle(f"Lo que cada institución gana con el mercado · {dia_txt}",
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    _pie(fig)
    _guarda(fig, f"v03_factura_{dia_txt}", pd.concat(todo),
            [f"validacion_horaria/factura_{c}_{dia_txt}.csv"
             for c in ("m1", "m3")])


# ══ v04 · el índice normalizado ═════════════════════════════════════════
def v04_ganancia(dia_txt, datos):
    fig, ax1, ax3 = E.figura_m1_m3(alto=2.9, compartir_y=True)
    todo = []
    for ax, cob in ((ax1, "m1"), (ax3, "m3")):
        f = datos[cob]["factura"].copy()
        f["pct"] = 100.0 * f.indice
        todo.append(f.assign(frontera=cob.upper()))
        y = np.arange(len(f))
        ax.barh(y, f.pct.fillna(0.0), color=E.COBERTURAS[cob], height=0.6)
        for n, (v, ok) in enumerate(zip(f.pct, f.indice.notna())):
            if not ok:
                ax.text(1, n, "no participa", fontsize=7, va="center",
                        color=E.TINTA)
        ax.set_yticks(y)
        ax.set_yticklabels([E.etiqueta_institucion(n) for n in f.institucion],
                           fontsize=8)
        ax.set_xlim(0, 100)
        ax.grid(axis="x", alpha=0.25)
        ax.set_xlabel("Del margen que tenía disponible (%)")
    fig.suptitle(f"Cuánto captura cada una de lo que podía capturar · {dia_txt}",
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    _pie(fig, "Normalizado por el rango admisible de cada agente. " + AVISO)
    _guarda(fig, f"v04_ganancia_{dia_txt}", pd.concat(todo),
            [f"validacion_horaria/factura_{c}_{dia_txt}.csv"
             for c in ("m1", "m3")])


# ══ v06 · el mosaico de una hora testigo ════════════════════════════════
def v06_hora(h, categoria, dia_txt):
    fig, axes = plt.subplots(2, 3, figsize=(E.ANCHO_COMPLETO, 5.4))
    color = E.COBERTURAS[h.cobertura]
    et = [E.etiqueta_institucion(n) for n in h.nombres]

    # (a) quién es quién
    ax = axes[0, 0]
    x = np.arange(len(h.nombres))
    ax.bar(x - 0.2, h.generacion, 0.38, color=E.VENDE, label="genera")
    ax.bar(x + 0.2, h.demanda, 0.38, color=E.COMPRA, label="consume")
    ax.plot(x, h.g_klim, "_", color=E.TINTA, ms=14, mew=2, label="límite econ.")
    ax.set_xticks(x); ax.set_xticklabels(et, rotation=45, fontsize=6.5, ha="right")
    ax.set_ylabel("kW"); ax.legend(fontsize=6, frameon=False)
    ax.set_title("a · quién es quién", fontsize=8.5, loc="left")

    # (b) la banda y el acuerdo
    ax = axes[0, 1]
    for q, i in enumerate(h.bids):
        ax.plot([q, q], [h.piso_h, h.techo_i[q]], color=E.APAGADO, lw=6,
                solid_capstyle="butt", zorder=1)
        ax.plot(q, h.pi[q], "D", color=color, ms=7, zorder=3)
    for m, j in enumerate(h.sids):
        ax.axhline(h.piso_j[m], color=E.VENDE, lw=0.9, ls=":",
                   label="piso de un vendedor" if m == 0 else None)
    ax.set_xticks(range(len(h.bids)))
    ax.set_xticklabels([et[i] for i in h.bids], rotation=45, fontsize=6.5,
                       ha="right")
    ax.set_ylabel("COP/kWh"); ax.legend(fontsize=6, frameon=False)
    ax.set_title("b · la banda y el acuerdo", fontsize=8.5, loc="left")

    # (c) los flujos por pareja
    ax = axes[0, 2]
    im = ax.imshow(h.P, cmap="Blues", aspect="auto")
    ax.set_xticks(range(h.I)); ax.set_yticks(range(h.J))
    ax.set_xticklabels([et[i] for i in h.bids], rotation=45, fontsize=6.5,
                       ha="right")
    ax.set_yticklabels([et[j] for j in h.sids], fontsize=6.5)
    for m in range(h.J):
        for q in range(h.I):
            if h.P[m, q] > 1e-3:
                ax.text(q, m, f"{h.P[m, q]:.2f}", ha="center", va="center",
                        fontsize=6,
                        color="white" if h.P[m, q] > h.P.max()*0.6 else E.TINTA)
    fig.colorbar(im, ax=ax, label="kWh", fraction=0.046)
    ax.set_title("c · flujos por pareja", fontsize=8.5, loc="left")

    # (d) la convergencia, con los multiplicadores
    ax = axes[1, 0]
    tr = h.tr
    if tr is not None and getattr(tr, "pi_t", None) is not None:
        for q in range(tr.pi_t.shape[0]):
            ax.plot(tr.t, tr.pi_t[q], lw=1.1, color=color, alpha=0.85)
        ax.axhline(h.piso_h, color=E.TINTA, lw=0.7, ls="--")
        ax.axhline(h.gs_esc, color=E.TINTA, lw=0.7, ls="--")
        if getattr(tr, "bet_filt_t", None) is not None:
            ax2 = ax.twinx()
            for q in range(tr.bet_filt_t.shape[0]):
                ax2.plot(tr.t, tr.bet_filt_t[q], lw=0.8, ls=":",
                         color=E.COMPRA, alpha=0.8)
            ax2.set_ylabel("multiplicador", fontsize=7, color=E.COMPRA)
            ax2.tick_params(labelsize=6)
    ax.set_xlabel("tiempo (s)", fontsize=7); ax.set_ylabel("COP/kWh")
    ax.set_title("d · cómo llegó el precio", fontsize=8.5, loc="left")

    # (e) dónde cae el mercado entre las cotas
    ax = axes[1, 1]
    ax.barh(0, h.mejor, color=E.APAGADO, height=0.5)
    ax.barh(0, h.peor, color="#DDDDDD", height=0.5)
    ax.plot(h.ciego, 0, "o", mfc="white", mec=E.TINTA, ms=8, mew=1.2,
            label="reparto ciego")
    ax.plot(h.excedente, 0, "D", color=color, ms=8, label="el mercado")
    ax.set_yticks([]); ax.set_xlabel("Excedente (COP)")
    ax.legend(fontsize=6.5, frameon=False, loc="lower right")
    ax.set_title(f"e · captura el {h.eficiencia:.1f} %", fontsize=8.5, loc="left")

    # (f) contra la normativa base
    ax = axes[1, 2]
    ancho = 0.38
    xs = np.arange(h.J)
    reg = np.array([h.piso_j[m] * h.P[m, :].sum() for m in range(h.J)])
    mod = np.array([float(np.sum(h.pi * h.P[m, :])) for m in range(h.J)])
    ax.bar(xs - 0.2, reg, ancho, color=E.APAGADO, label="normativa base")
    ax.bar(xs + 0.2, mod, ancho, color=E.VENDE, label="el mercado")
    ax.set_xticks(xs)
    ax.set_xticklabels([et[j] for j in h.sids], rotation=45, fontsize=6.5,
                       ha="right")
    ax.set_ylabel("Lo que cobra (COP)"); ax.legend(fontsize=6.5, frameon=False)
    ax.set_title("f · qué cobra el vendedor", fontsize=8.5, loc="left")

    for ax in axes.ravel():
        ax.grid(axis="y", alpha=0.2)
    fig.suptitle(f"{categoria.upper()} · {h.ts.strftime('%Y-%m-%d %H:%M')} · "
                 f"{h.cobertura.upper()} · {h.J} vendedores y {h.I} compradores",
                 fontweight="bold", fontsize=10)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    _pie(fig)

    det = [dict(vendedor=h.nombres[h.sids[m]], comprador=h.nombres[h.bids[q]],
                kwh=float(h.P[m, q]), precio=float(h.pi[q]))
           for m in range(h.J) for q in range(h.I) if h.P[m, q] > 1e-9]
    _guarda(fig, f"v06_hora_{h.k}_{h.cobertura}", pd.DataFrame(det),
            [f"validacion_horaria/cache/horas_{h.cobertura}_{dia_txt}.pkl"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dia", default="2025-05-02")
    ap.add_argument("--solo", default=None,
                    choices=["panorama", "papeles", "factura", "ganancia", "horas"])
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    E.aplicar_estilo()

    from paso_a_paso import carga
    datos = {}
    for cob in ("m1", "m3"):
        dat = carga(cob)
        tabla, horas = Dia.recorre(cob, args.dia, dat=dat)
        datos[cob] = dict(dat=dat, tabla=tabla, horas=horas,
                          testigos=Dia.testigos(tabla, horas),
                          factura=Fac.calcula(dat, horas))

    hacer = args.solo
    if hacer in (None, "panorama"):
        v01_panorama(args.dia, datos)
    if hacer in (None, "papeles"):
        v02_papeles(args.dia, datos)
    if hacer in (None, "factura"):
        v03_factura(args.dia, datos)
    if hacer in (None, "ganancia"):
        v04_ganancia(args.dia, datos)
    if hacer in (None, "horas"):
        for cob in ("m1", "m3"):
            for cat, k in datos[cob]["testigos"].items():
                if k is None:
                    print(f"  [salta] {cat} no se da en {cob.upper()}")
                    continue
                v06_hora(datos[cob]["horas"][k], cat, args.dia)


if __name__ == "__main__":
    main()
