"""
fig_barrido_respuesta.py — Figura del barrido de cargos de red en E0 para la
respuesta a los revisores (envío 11297 a IEEE Latin America Transactions,
comentario J-2; CANON §14.40, punto 3)
===============================================================================
Actividades 4.1 y 4.2 de la propuesta. No simula ni toca `core/`: lee
`m3_cargos.csv` y `m3_umbrales.csv` de `SALIDAS_SERVIDOR/articulo_r1_2026-11-21/`
después de comprobar su tamaño y su sha256 contra
`Documentos/canon_2026-09/HUELLAS.csv` (grupo e1/AR1), y dibuja la ventaja del
mercado P2P sobre C4 y sobre C1 en E0 frente a la fracción de los cargos de
red que paga lo intercambiado, con los intercambios fijos y con salida, y las
marcas del 23 % (la ventaja sobre C1 se anula con los intercambios fijos) y
del 52 % (desde ahí ningún par gana al transar).

Con los intercambios fijos la cuenta es lineal en la fracción (§14.40). Con
salida solo se calcularon cinco fracciones (0, 25, 50, 75 y 100 %); los
segmentos entre ellas solo unen los puntos.

Falla en voz alta: ninguna huella distinta, ningún valor no finito, y las
cifras que cita la respuesta se comprueban antes de dibujar.

Uso:  python reformateo/documento/scripts/articulo_r1/fig_barrido_respuesta.py
Salida: Documentos/articulo_latam/v2_es/revision_r1/respuesta/fig_barrido_E0.{pdf,png}
"""
from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parents[4]
HUELLAS = RAIZ / "Documentos" / "canon_2026-09" / "HUELLAS.csv"
SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
GRUPO = "e1/AR1"
F_CARGOS = "articulo_r1_2026-11-21/m3_cargos.csv"
F_UMBRALES = "articulo_r1_2026-11-21/m3_umbrales.csv"
DESTINO = RAIZ / "Documentos" / "articulo_latam" / "v2_es" / "revision_r1" / "respuesta"
M = 1e6

AZUL, NARANJA = "#2a78d6", "#eb6834"   # sobre C4 y sobre C1
TINTA, TINTA2, REJILLA = "#0b0b0b", "#52514e", "#e4e3df"


def exige(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[fig_barrido] COMPUERTA FALLIDA: {msg}")


def lee(ruta: str) -> pd.DataFrame:
    h = pd.read_csv(HUELLAS)
    f = h[(h.grupo == GRUPO) & (h.ruta == ruta)]
    exige(len(f) == 1, f"{ruta}: {len(f)} filas en HUELLAS.csv")
    p = SALIDAS / ruta
    datos = p.read_bytes()
    exige(len(datos) == int(f.iloc[0].bytes), f"{ruta}: tamaño distinto de la huella")
    sha = hashlib.sha256(datos).hexdigest()
    exige(sha == f.iloc[0].sha256, f"{ruta}: sha256 distinto de la huella")
    print(f"[fig_barrido] huella OK {ruta} {sha[:12]}…")
    return pd.read_csv(p)


def main() -> int:
    c = lee(F_CARGOS)
    u = lee(F_UMBRALES)
    e0 = c[c.caso == "E0"].sort_values("f")
    um = u[u.caso == "E0"].iloc[0]
    cols = ["P2P_fijos_menos_C4", "P2P_fijos_menos_C1", "P2P_salida_menos_C4", "P2P_salida_menos_C1"]
    exige(len(e0) == 5 and list(e0.f) == [0.0, 0.25, 0.5, 0.75, 1.0], "E0: fracciones inesperadas")
    exige(all(math.isfinite(x) for x in e0[cols].to_numpy().ravel()), "valores no finitos")
    f23, f52 = float(um.f_cambio_P2P_C1_fijos), float(um.f_sin_intercambio_salida)
    salida_c4 = float(um.minimo_P2P_salida_menos_C4) / M
    # Las cifras que cita la respuesta (CANON §14.40, punto 3)
    exige(round(f23 * 100) == 23, f"f de cambio con flujos fijos {f23}")
    exige(round(f52 * 100) == 52, f"f sin intercambio con salida {f52}")
    exige(round(salida_c4, 2) == 1.71, f"mínimo con salida {salida_c4}")
    exige(round(e0.P2P_fijos_menos_C4.iloc[0] / M, 2) == 2.01, "P2P − C4 en f = 0")
    exige(round(e0.P2P_fijos_menos_C1.iloc[0] / M, 2) == 0.30, "P2P − C1 en f = 0")
    exige((e0.P2P_salida_menos_C1 >= -1e-6).all(), "con salida, P2P − C1 negativo")

    x = e0.f.to_numpy() * 100
    plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                         "font.size": 9, "axes.edgecolor": TINTA2, "axes.labelcolor": TINTA,
                         "xtick.color": TINTA2, "ytick.color": TINTA2})
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    ax.axhline(0, color=TINTA2, lw=0.8)
    for xm, txt in ((f23 * 100, "23 %"), (f52 * 100, "52 %")):
        ax.axvline(xm, color=TINTA2, lw=0.8, ls=":")
        ax.text(xm + 1, 2.12, txt, color=TINTA2, fontsize=8.5, va="bottom")
    ax.plot(x, e0.P2P_fijos_menos_C4 / M, color=AZUL, lw=2, label="over collective (C4), trades fixed")
    ax.plot(x, e0.P2P_salida_menos_C4 / M, color=AZUL, lw=1.2, ls="--", marker="o", ms=4,
            label="over collective (C4), with exit")
    ax.plot(x, e0.P2P_fijos_menos_C1 / M, color=NARANJA, lw=2, label="over individual (C1), trades fixed")
    ax.plot(x, e0.P2P_salida_menos_C1 / M, color=NARANJA, lw=1.2, ls="--", marker="s", ms=4,
            label="over individual (C1), with exit")
    ax.text(101, salida_c4, "1.71", color=TINTA2, fontsize=8.5, va="center")
    ax.set_xlim(0, 100)
    ax.set_ylim(-1.15, 2.35)
    ax.set_xlabel("Share of the buyer's network charges paid by traded energy (%)")
    ax.set_ylabel("Market's advantage (MCOP)")
    ax.grid(axis="y", color=REJILLA, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=8.5, frameon=False, ncol=2)
    fig.tight_layout()
    DESTINO.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(DESTINO / f"fig_barrido_E0.{ext}", dpi=300, metadata={"Creator": None} if ext == "png" else None)
    print(f"[fig_barrido] escrito {DESTINO / 'fig_barrido_E0.pdf'} y .png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
