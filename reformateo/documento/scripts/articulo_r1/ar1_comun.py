"""
ar1_comun.py — Piezas comunes de las mediciones de la revisión r1 del artículo
(envío 11297 a IEEE Latin America Transactions, 2026-11-21; CANON §14.40)
===============================================================================
Actividades 3.3, 4.1 y 4.2 de la propuesta. Ningún guion de esta carpeta simula
el mercado ni toca `core/`, `scenarios/` ni `analysis/`: leen artefactos con
huella en `Documentos/canon_2026-09/HUELLAS.csv` (se comprueba tamaño y sha256
de cada uno antes de leerlo, con `atribucion_supuestos.lee`) y calculan sobre
ellos. Los insumos de `data/` sin huella en el canon se registran con su sha256.

Cada guion escribe en `SALIDAS_SERVIDOR/articulo_r1_2026-11-21/` sus tablas,
`cifras_<medicion>.csv` (clave, valor, unidad, fuente) y `logs/<medicion>.log`.
`cierre.py` junta `cifras.csv`, `GUIONES.csv` y `procedencia.txt`.

Falla en voz alta: ningún `except` que trague y ningún valor no finito.
"""
from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[4]
AQUI = Path(__file__).resolve().parent
ARTICULO = RAIZ / "reformateo" / "documento" / "scripts" / "articulo"
for _p in (str(RAIZ), str(ARTICULO), str(AQUI)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import atribucion_supuestos as AS  # noqa: E402
import c2_ppa as CP  # noqa: E402

SALIDAS = RAIZ / "SALIDAS_SERVIDOR"
SALIDA = SALIDAS / "articulo_r1_2026-11-21"
CASOS = AS.CASOS
CINCO = ["E0", "E3", "E4", "I1", "SINU"]          # los cinco casos del artículo
M = 1e6
F_CIFRAS = "cifras_articulo_2026-09-30/cifras.csv"
F_ATR = "atribucion_supuestos_2026-09-30/atribucion_13casos.csv"
F_PC = "p2p_comunitario_2026-10-02/p2p_comunitario_13casos.csv"


class Medicion:
    """Registro, compuertas y cifras de una medición."""

    def __init__(self, nombre: str, titulo: str):
        self.nombre, self.titulo = nombre, titulo
        self.lineas: list[str] = []
        self.compuertas: list[str] = []
        self.cifras: list[dict] = []
        self.insumos: list[tuple[str, int, str]] = []
        self.tablas: list[str] = []
        (SALIDA / "logs").mkdir(parents=True, exist_ok=True)
        self.di(f"{nombre}: {titulo}")

    def di(self, msg: str) -> None:
        linea = f"[ar1:{self.nombre}] {msg}"
        print(linea)
        self.lineas.append(linea)

    def exige(self, cond: bool, msg: str) -> None:
        if not cond:
            raise SystemExit(f"[ar1:{self.nombre}] COMPUERTA FALLIDA: {msg}")

    def ok(self, msg: str) -> None:
        self.compuertas.append(msg)
        self.di(f"  OK  {msg}")

    def pon(self, clave: str, valor, unidad: str, fuente: str) -> None:
        if isinstance(valor, (float, np.floating)):
            self.exige(math.isfinite(float(valor)), f"cifra no finita: {clave}")
            valor = float(valor)
        elif isinstance(valor, (int, np.integer)):
            valor = int(valor)
        self.exige(all(c["clave"] != clave for c in self.cifras), f"clave repetida: {clave}")
        self.cifras.append(dict(clave=clave, valor=valor, unidad=unidad, fuente=fuente))

    def insumo(self, rel: str) -> Path:
        """Un fichero sin huella en el canon: se registra su tamaño y su sha256."""
        p = RAIZ / rel
        self.exige(p.is_file(), f"no existe el insumo {rel}")
        datos = p.read_bytes()
        self.insumos.append((rel, len(datos), hashlib.sha256(datos).hexdigest()))
        return p

    def tabla(self, df: pd.DataFrame, nombre: str, **kw) -> None:
        num = df.select_dtypes(include=[np.number]).to_numpy(dtype=float)
        self.exige(bool(np.isfinite(num[~np.isnan(num)]).all()), f"{nombre}: valores infinitos")
        df.to_csv(SALIDA / nombre, index=kw.pop("index", False), lineterminator="\n", **kw)
        self.tablas.append(nombre)
        self.di(f"  escrito {nombre} ({len(df)} filas)")

    def cierra(self) -> None:
        leidos = list(dict.fromkeys(AS.LEIDOS + CP.LEIDOS))
        ins = list(dict.fromkeys(self.insumos + [tuple(x) for x in CP.INSUMOS]))
        self.di(f"artefactos leídos con huella: {len(leidos)}")
        H = AS._H.set_index(["grupo", "ruta"]).sha256
        for g, r in leidos:
            self.lineas.append(f"  {g} {r} {H[(g, r)]}")
        self.di(f"insumos sin huella en el canon, con su sha256: {len(ins)}")
        for rel, n, h in ins:
            self.lineas.append(f"  {rel} {n} {h}")
        self.di(f"tablas: {', '.join(self.tablas)}")
        self.di(f"{len(self.compuertas)} compuertas, {len(self.cifras)} cifras")
        pd.DataFrame(self.cifras, columns=["clave", "valor", "unidad", "fuente"]).to_csv(
            SALIDA / f"cifras_{self.nombre}.csv", index=False, lineterminator="\n")
        (SALIDA / "logs" / f"{self.nombre}.log").write_text("\n".join(self.lineas) + "\n", encoding="utf-8",
                                                            newline="\n")


def cifras_articulo() -> pd.Series:
    """Las cifras del artículo (grupo e1/L), clave → valor."""
    c = pd.read_csv(AS.lee(F_CIFRAS, "e1/L"))
    return c.set_index("clave").valor


def atribucion() -> pd.DataFrame:
    return pd.read_csv(AS.lee(F_ATR, "e1/S")).set_index("caso")


def p2pcom() -> pd.DataFrame:
    return pd.read_csv(AS.lee(F_PC, "e1/PC"), keep_default_na=False, na_values=[""])


def casos_cargados(med: Medicion, casos=None) -> tuple[dict, np.ndarray]:
    """Los almacenes de los casos (como `atribucion_supuestos.carga`) y la
    bolsa horaria con su tope (la caché, comprobada contra la reconstruida del
    canon por `c2_ppa.bolsa`)."""
    TT = AS.tarifas()
    cap = AS.capacidades()
    DAT = {c: AS.carga(c, TT, cap) for c in (casos or CASOS)}
    idx, _ = CP.horizonte()
    pb = CP.bolsa(idx)
    med.ok(f"almacenes de {len(DAT)} casos cargados con sus compuertas (flujos = agentes, vendido = comprado por hora) "
           "y bolsa de la caché igual a la reconstruida del canon")
    return DAT, pb
