"""Recalcula la huella de los literales de tests/test_reposo_mercado.py desde
los almacenes (receta de cada hora) y compara al bit. Solo lee.

Es el que fija la huella vigente, fe4488168ced426c, sobre las catorce horas
(las nueve de `genera_literales.py` y las cinco de `literales_ronda1.py`).
Traido al repositorio sin cambiar su logica; solo la raiz pasa a calcularse
desde este fichero. Ver README.md."""
import hashlib
import sys
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tests"))
from data.xm_prices import get_b_for_real_data  # noqa: E402
import test_reposo_mercado as t  # noqa: E402

base = RAIZ / "SALIDAS_SERVIDOR/entrega_matriz_2026-09-15/SALIDAS_SERVIDOR/matriz"
NOMBRES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
bmap = dict(zip(NOMBRES, get_b_for_real_data(5, NOMBRES)))
PRIMERA = {853, 874, 2120, 3804, 3086, 877, 12, 58, 540}
cache = {}
m = hashlib.sha256()
for clave, h in t.HORAS.items():
    caso, k = ("E0", clave) if isinstance(clave, int) else clave.split("-")
    k = int(k)
    if caso not in cache:
        cache[caso] = pd.read_parquet(base / caso / "almacen/m1/agentes")
    ag = cache[caso][cache[caso]["hora"] == k]
    papeles = ("vendedor",) if clave in PRIMERA else ("vendedor", "retirado")
    ven = ag[ag["papel"].isin(papeles) & (ag["sobrante"] > 0)]
    com = ag[(ag["papel"] == "comprador") & (ag["faltante"] > 0)]
    arr = dict(s=ven["sobrante"].to_numpy(np.float64), d=com["faltante"].to_numpy(np.float64),
               b=np.array([bmap[n] for n in ven["agente"]], dtype=np.float64),
               techo=com["techo"].to_numpy(np.float64), piso_j=ven["piso"].to_numpy(np.float64))
    for campo in t.CAMPOS:
        lit = t._hex(h[campo])
        assert np.array_equal(lit, arr[campo]), (clave, campo)
        m.update(np.ascontiguousarray(arr[campo], dtype=np.float64).tobytes())
    assert h["vendedores"] == ven["agente"].tolist() and h["compradores"] == com["agente"].tolist(), clave
print("literales identicos al almacen; huella", m.hexdigest()[:16])
