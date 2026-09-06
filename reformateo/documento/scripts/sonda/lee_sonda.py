# -*- coding: utf-8 -*-
"""Lee las cuatro corridas de la sonda CAL-46 y arma su tabla.

Ninguna cifra derivada se escribe a mano: todas salen de los registros que
dejo la corrida. Uso:

    python lee_sonda.py <carpeta de la sonda>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

BRAZOS = {"m1_h": ("M1", 1.0), "m1_q": ("M1", 0.25),
          "m3_h": ("M3", 1.0), "m3_q": ("M3", 0.25)}

# Cada mecanismo, con el trozo de linea por el que se le reconoce.
MECANISMOS = [
    ("P2P", r"^  P2P \(Stackelberg"),
    ("C1", r"^  C1  Individual"),
    ("C2", r"^  C2  Bilateral"),
    ("C3", r"^  C3  Spot"),
    ("C4", r"^  C4  Colectivo"),
    ("C4_mensual", r"^  C4m Colectivo"),
    ("C5", r"^  C5  AGR"),
]
CIFRA = r"\$\s*([\d,]+)\s+([\d.]+)\s+([\d.]+)\s+(-?[\d.]+)\s+([\d.]+)"
PARTES = [("Autoconsumo", r"Autoconsumo\s+([\d,]+) COP"),
          ("Prima vendedor", r"Prima vendedor\s+([\d,]+) COP"),
          ("Ahorro comprador", r"Ahorro comprador\s+([\d,]+) COP")]


def num(s: str) -> float:
    return float(s.replace(",", ""))


def lee(log: Path) -> dict:
    t = log.read_text(encoding="utf-8", errors="replace")
    d = {"mecanismos": {}, "partes": {}}
    for nombre, patron in MECANISMOS:
        m = re.search(patron + r".*?" + CIFRA, t, re.M)
        if m:
            d["mecanismos"][nombre] = dict(
                cop=num(m.group(1)), sc=float(m.group(2)),
                ss=float(m.group(3)), ie=float(m.group(4)),
                gini=float(m.group(5)))
    for nombre, patron in PARTES:
        m = re.search(patron, t)
        if m:
            d["partes"][nombre] = num(m.group(1))
    m = re.search(r"RPE \(P2P vs C4\):\s+(-?[\d.]+)", t)
    d["rpe"] = float(m.group(1)) if m else None
    m = re.search(r"Ventana .*?: (\d+) pasos", t)
    d["pasos"] = int(m.group(1)) if m else None
    return d


def main(base: Path) -> int:
    datos = {k: lee(base / f"{k}.log") for k in BRAZOS}

    filas = []
    for frontera in ("M1", "M3"):
        h = datos[f"{frontera.lower()}_h"]
        q = datos[f"{frontera.lower()}_q"]
        for nombre, _ in MECANISMOS:
            if nombre not in h["mecanismos"] or nombre not in q["mecanismos"]:
                continue
            a, b = h["mecanismos"][nombre], q["mecanismos"][nombre]
            filas.append(dict(
                frontera=frontera, mecanismo=nombre,
                cop_hora=a["cop"], cop_cuarto=b["cop"],
                dif_pct=100.0 * (b["cop"] / a["cop"] - 1.0),
                sc_hora=a["sc"], sc_cuarto=b["sc"],
                ss_hora=a["ss"], ss_cuarto=b["ss"],
                ie_hora=a["ie"], ie_cuarto=b["ie"],
                gini_hora=a["gini"], gini_cuarto=b["gini"]))
    tabla = pd.DataFrame(filas)

    partes = []
    for frontera in ("M1", "M3"):
        h = datos[f"{frontera.lower()}_h"]["partes"]
        q = datos[f"{frontera.lower()}_q"]["partes"]
        for nombre in h:
            partes.append(dict(frontera=frontera, componente=nombre,
                               cop_hora=h[nombre], cop_cuarto=q[nombre],
                               dif_pct=100.0 * (q[nombre] / h[nombre] - 1.0)))
    desglose = pd.DataFrame(partes)

    pd.set_option("display.width", 200)
    print("\n=== Beneficio por mecanismo, julio de 2025 ===")
    print(tabla[["frontera", "mecanismo", "cop_hora", "cop_cuarto",
                 "dif_pct"]].round(2).to_string(index=False))
    print("\n=== El P2P por dentro: quien sube y quien baja ===")
    print(desglose.round(2).to_string(index=False))
    print("\n=== Rendimiento relativo del P2P frente al colectivo ===")
    for frontera in ("M1", "M3"):
        a = datos[f"{frontera.lower()}_h"]["rpe"]
        b = datos[f"{frontera.lower()}_q"]["rpe"]
        print(f"  {frontera}: {a:.4f} -> {b:.4f}   "
              f"({100 * (b / a - 1):+.1f} %)")

    print("\n=== El orden, paso a paso ===")
    for frontera in ("M1", "M3"):
        for etq, paso in (("hora", "cop_hora"), ("cuarto", "cop_cuarto")):
            s = tabla[tabla.frontera == frontera].sort_values(
                paso, ascending=False)
            print(f"  {frontera} a {etq:6s}: "
                  + " > ".join(s.mecanismo.tolist()))

    salida = Path(__file__).resolve().parent / "salidas"
    salida.mkdir(exist_ok=True)
    tabla.to_csv(salida / "sonda_mecanismos.csv", index=False,
                 encoding="utf-8-sig")
    desglose.to_csv(salida / "sonda_desglose_p2p.csv", index=False,
                    encoding="utf-8-sig")
    print(f"\nescritas en {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
