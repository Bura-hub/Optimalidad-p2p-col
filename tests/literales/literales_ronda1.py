"""Ronda de arreglos 1: literales de las horas nuevas y lo que da el nucleo.
Horas: E4 133 (riesgo 5), 5631 y 5632 (D61); E0 4766 (compradores cortos con
Cesmag vendiendo) y 226 (un comprador). Receta nueva: vendedores = papel
«vendedor» o «retirado» con sobrante > 0. Solo lee los almacenes; escribe los
literales en `literales_ronda1.txt`, junto a este fichero.

Tarea 1 del reposo, ronda de arreglos (2026-09-17). Traido al repositorio sin
cambiar su logica; solo la raiz pasa a calcularse desde este fichero. Ver
README.md."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from data.xm_prices import get_b_for_real_data  # noqa: E402
from core.reposo_mercado import resuelve_reposo  # noqa: E402

base = RAIZ / "SALIDAS_SERVIDOR/entrega_matriz_2026-09-15/SALIDAS_SERVIDOR/matriz"
NOMBRES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
bmap = dict(zip(NOMBRES, get_b_for_real_data(5, NOMBRES)))
np.set_printoptions(precision=4, suppress=True, linewidth=220)
HORAS = [("E4", 133), ("E4", 5631), ("E4", 5632), ("E0", 4766), ("E0", 226)]
cache = {}
lineas = []
for caso, k in HORAS:
    if caso not in cache:
        cache[caso] = pd.read_parquet(base / caso / "almacen/m1/agentes")
    a = cache[caso]
    ag = a[a["hora"] == k]
    ven = ag[ag["papel"].isin(("vendedor", "retirado")) & (ag["sobrante"] > 0)]
    com = ag[(ag["papel"] == "comprador") & (ag["faltante"] > 0)]
    s = ven["sobrante"].to_numpy(np.float64); d = com["faltante"].to_numpy(np.float64)
    b = np.array([bmap[n] for n in ven["agente"]], dtype=np.float64)
    t = com["techo"].to_numpy(np.float64); p = ven["piso"].to_numpy(np.float64)
    fecha = str(ag["fecha"].iloc[0])[:16]
    print(f"\n=== {caso} {k} {fecha} vend {list(zip(ven['agente'], ven['papel']))} s {s} b {b} piso {p}")
    print(f"    comp {com['agente'].tolist()} d {d} techo {t}")
    for kw in ({}, {"despacho_vendedores": "llenado"}, {"regla_precio": "puja"}):
        r = resuelve_reposo(s, d, b, t, p, **kw)
        print(f"  {kw}: {r.regimen} n {r.n_soluciones} piso {r.piso:.4f} S {r.S:.4f} ell {r.ell} q {r.q} "
              f"desp {r.s_despachado} pujas {r.pi_reposo} p_u {r.p_u:.4f} p_liq {r.p_liquidado} "
              f"parte {r.parte_vendedor:.4f} excl {r.excluidos} merito {r.orden_merito} E {r.E:.4f} sigma {r.sigma}")
    hx = lambda v: "[" + ", ".join(f'"{float(x).hex()}"' for x in v) + "]"
    lineas.append(f"    # {caso}, {fecha}; vendedores {list(zip(ven['agente'], ven['papel']))}; compradores {com['agente'].tolist()}")
    lineas.append(f"    \"{caso}-{k}\": dict(")
    lineas.append(f"        vendedores={ven['agente'].tolist()!r}, compradores={com['agente'].tolist()!r},")
    for nombre, v in (("s", s), ("d", d), ("b", b), ("techo", t), ("piso_j", p)):
        lineas.append(f"        {nombre}={hx(v)},")
    lineas.append("    ),")
(Path(__file__).parent / "literales_ronda1.txt").write_text("\n".join(lineas), encoding="utf-8")
