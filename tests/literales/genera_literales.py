"""Genera los literales hexadecimales de las horas reales para
tests/test_reposo_mercado.py y su huella SHA-256. Solo lee el almacen.

Tarea 1 del reposo (2026-09-16): las nueve horas de E0 de la primera entrega
(853, 874, 2120, 3804, 3086, 877, 12, 58 y 540), con la huella de esas nueve,
54b02e7841762414. Traido al repositorio sin cambiar su logica; solo la raiz
pasa a calcularse desde este fichero. Ver README.md."""
import hashlib
import sys
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from data.xm_prices import get_b_for_real_data  # noqa: E402

B = sorted((RAIZ / "SALIDAS_SERVIDOR/entrega_matriz_2026-09-15").glob(
    "**/matriz/E0/almacen/m1"))[0]
print("# almacen:", B.relative_to(RAIZ))
a = pd.read_parquet(B / "agentes")
NOMBRES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
bmap = dict(zip(NOMBRES, get_b_for_real_data(5, NOMBRES)))
HORAS = [853, 874, 2120, 3804, 3086, 877, 12, 58, 540]
m = hashlib.sha256()
lineas = ["HORAS = {"]
for k in HORAS:
    ag = a[a["hora"] == k]
    ven = ag[(ag["papel"] == "vendedor") & (ag["sobrante"] > 0)]
    com = ag[(ag["papel"] == "comprador") & (ag["faltante"] > 0)]
    fecha = str(ag["fecha"].iloc[0])[:16]
    s = ven["sobrante"].to_numpy(np.float64)
    d = com["faltante"].to_numpy(np.float64)
    b = np.array([bmap[n] for n in ven["agente"]], dtype=np.float64)
    t = com["techo"].to_numpy(np.float64)
    p = ven["piso"].to_numpy(np.float64)
    for v in (s, d, b, t, p):
        m.update(np.ascontiguousarray(v, dtype=np.float64).tobytes())
    hx = lambda v: "[" + ", ".join(f'"{float(x).hex()}"' for x in v) + "]"
    lineas.append(f"    # {fecha}; vendedores {ven['agente'].tolist()}, compradores {com['agente'].tolist()}")
    lineas.append(f"    {k}: dict(")
    lineas.append(f"        vendedores={ven['agente'].tolist()!r}, compradores={com['agente'].tolist()!r},")
    lineas.append(f"        s={hx(s)},")
    lineas.append(f"        d={hx(d)},")
    lineas.append(f"        b={hx(b)},")
    lineas.append(f"        techo={hx(t)},")
    lineas.append(f"        piso_j={hx(p)}),")
    print(f"# {k}: s {s} d {d} b {b} techo {t} piso {p}")
lineas.append("}")
print("\n".join(lineas))
print(f'HUELLA = "{m.hexdigest()[:16]}"')
