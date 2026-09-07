"""
El lector unico de una hora del mercado.

El proyecto tiene siete resolvedores por hora repartidos entre las sondas
—paso a paso, eficiencia, cotas del excedente, competencia, banda de
precios, coste del acoplado y arranque de banda— y todos repiten la misma
preparacion: limite economico de generacion, clasificacion en papeles,
cantidades netas, techo y piso. Este modulo la hace UNA vez y devuelve todo
lo que se sabe de la hora.

No reimplementa nada. Compone:

    paso_a_paso.resuelve      el juego resuelto por la via acoplada, con la
                              restriccion de participacion iterada
    eficiencia                el optimo centralizado y la eficiencia partida
                              en volumen y emparejamiento
    cotas_excedente           el peor reparto del mismo volumen y el ciego
    core.settlement           el ahorro del comprador y la prima del vendedor
    core.opciones_externas    el tramo de permuta de cada vendedor

CONTRATO: `lee` no imprime y no dibuja. Devuelve datos. Todo lo que imprime
o dibuja vive en `dia.py`, `factura.py` y `gen_validacion.py`.

AVISO sobre la via: se resuelve por la via ACOPLADA, que es la del modelo
base y la que produce precios interiores, pero **no es el metodo con el que
se produjeron las cifras publicadas**, que salieron de la via alternada.
Quien dibuje a partir de esto tiene que declararlo.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[3]
SONDA = AQUI.parent / "sonda"
for _p in (RAIZ, SONDA):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from core.settlement import compute_savings  # noqa: E402

PEGADO = 0.01   # a menos del uno por ciento de la banda, el precio esta pegado


@dataclass
class Hora:
    """Todo lo que se sabe de una hora del mercado.

    Los campos van agrupados como en la especificacion: agentes, banda,
    mercado, convergencia, cotas, reparto, red y avisos.
    """
    # ── identidad ──────────────────────────────────────────────────────
    k: int
    cobertura: str
    ts: object = None
    resuelta: bool = False
    motivo: str = ""

    # ── agentes ────────────────────────────────────────────────────────
    nombres: list = field(default_factory=list)
    papel: list = field(default_factory=list)      # "vende" | "compra" | "-"
    g_klim: Optional[np.ndarray] = None            # limite economico (N,)
    demanda: Optional[np.ndarray] = None           # (N,)
    generacion: Optional[np.ndarray] = None        # (N,)
    neto: Optional[np.ndarray] = None              # g_klim - demanda (N,)
    comercializador: dict = field(default_factory=dict)

    # ── banda ──────────────────────────────────────────────────────────
    techo_n: Optional[np.ndarray] = None           # techo de CADA agente (N,)
    piso_n: Optional[np.ndarray] = None            # piso de CADA agente (N,)
    techo_i: Optional[np.ndarray] = None           # de los compradores (I,)
    piso_j: Optional[np.ndarray] = None            # de los vendedores (J,)
    piso_h: float = 0.0                            # el menor de los pisos
    gs_esc: float = 0.0                            # el mayor de los techos
    en_permuta: Optional[np.ndarray] = None        # (N,) bool

    # ── mercado ────────────────────────────────────────────────────────
    sids: list = field(default_factory=list)
    bids: list = field(default_factory=list)
    G_net: Optional[np.ndarray] = None
    D_net: Optional[np.ndarray] = None
    P: Optional[np.ndarray] = None                 # (J, I)
    pi: Optional[np.ndarray] = None                # (I,)
    volumen: float = 0.0

    # ── convergencia ───────────────────────────────────────────────────
    tr: object = None                              # CoupledTrajectory
    cola: float = float("nan")                     # movimiento del ultimo decimo
    segundos: float = 0.0

    # ── cotas y eficiencia ─────────────────────────────────────────────
    mejor: float = 0.0
    peor: float = 0.0
    ciego: float = 0.0
    excedente: float = 0.0
    eficiencia: float = float("nan")
    ef_volumen: float = float("nan")
    ef_emparejamiento: float = float("nan")

    # ── reparto ────────────────────────────────────────────────────────
    S_i: Optional[np.ndarray] = None               # ahorro por comprador
    SR_j: Optional[np.ndarray] = None              # prima por vendedor
    tajada_vendedor: float = float("nan")          # en tanto por ciento

    # ── red ────────────────────────────────────────────────────────────
    compra_red: Optional[np.ndarray] = None        # (N,) kWh que faltan
    vende_red: Optional[np.ndarray] = None         # (N,) kWh que sobran

    # ── avisos ─────────────────────────────────────────────────────────
    retirados: list = field(default_factory=list)  # vendedores que no entran
    bajo_piso: list = field(default_factory=list)  # vendedores por debajo
    pegados: int = 0
    n_precios: int = 0

    @property
    def J(self) -> int:
        return len(self.sids)

    @property
    def I(self) -> int:
        return len(self.bids)

    @property
    def uniforme(self) -> bool:
        """Si la banda es uniforme, el emparejamiento no decide nada."""
        if self.techo_i is None or self.piso_j is None or not self.J:
            return True
        return bool(np.ptp(self.techo_i) < 1e-9 and np.ptp(self.piso_j) < 1e-9)


def lee(dat: dict, k: int, cobertura: str = "m1") -> Hora:
    """Todo lo que se sabe de la hora `k`, en un solo objeto.

    Si la hora no tiene mercado —falta un vendedor o un comprador, o la
    banda esta vacia— devuelve una `Hora` con `resuelta=False` y el motivo,
    en vez de reventar. Recorrer un dia entero exige que las horas muertas
    tengan respuesta.
    """
    import pandas as pd
    from paso_a_paso import resuelve

    N = dat["D"].shape[0]
    idx = pd.DatetimeIndex(dat["idx"])
    h = Hora(k=int(k), cobertura=cobertura, ts=idx[k],
             nombres=list(dat["nombres"]),
             demanda=dat["D"][:, k].copy(),
             generacion=dat["G"][:, k].copy(),
             techo_n=dat["techo"][:, k].copy(),
             piso_n=dat["piso"][:, k].copy(),
             en_permuta=dat["perm"][:, k].copy(),
             comercializador=dict(dat["com"]))

    t0 = time.time()
    try:
        # se piden los multiplicadores: son los que dicen que restriccion
        # esta mordiendo, y sin ellos la figura de convergencia enseña el
        # precio deteniendose sin poder decir por que se detiene ahi
        r = resuelve(dat, int(k), multiplicadores=True)
    except Exception as e:                      # el integrador puede reventar
        h.motivo = f"el solucionador falló: {type(e).__name__}"
        h.segundos = time.time() - t0
        return h
    h.segundos = time.time() - t0
    if r is None:
        h.motivo = "sin mercado esa hora"
        return h

    h.sids, h.bids = list(r["sids"]), list(r["bids"])
    h.g_klim = r["g_klim"]
    h.neto = r["g_klim"] - dat["D"][:, k]
    h.papel = ["vende" if n in h.sids else "compra" if n in h.bids else "-"
               for n in range(N)]
    h.G_net, h.D_net = r["G_net"], r["D_net"]
    h.techo_i, h.piso_j = r["techo_i"], r["piso_j"]
    h.piso_h = float(r["piso_h"])
    h.gs_esc = float(np.max(r["techo_i"])) if len(r["techo_i"]) else 0.0
    h.P, h.pi = np.asarray(r["P"], float), np.asarray(r["pi"], float)
    h.tr = r["tr"]
    h.retirados = list(r["retirados"])
    h.volumen = float(h.P.sum())

    if not h.sids or not h.bids:
        h.motivo = "sin vendedores o sin compradores tras la participación"
        return h

    # ── el precio dentro de su banda ────────────────────────────────────
    ancho = np.maximum(h.techo_i - h.piso_h, 1e-12)
    pos = (h.pi - h.piso_h) / ancho
    h.n_precios = len(h.pi)
    h.pegados = int(np.sum((pos <= PEGADO) | (pos >= 1.0 - PEGADO)))

    # ── vendedores por debajo de su propio piso (H-43) ──────────────────
    for m, j in enumerate(h.sids):
        vendido = h.P[m, :]
        if vendido.sum() <= 1e-9:
            continue
        if float(np.max(h.pi[vendido > 1e-9])) < h.piso_j[m] - 1e-9:
            h.bajo_piso.append(j)

    # ── cotas y eficiencia ──────────────────────────────────────────────
    c = _cotas(h.G_net, h.D_net, h.techo_i, h.piso_j, h.P)
    if c is not None:
        for campo, valor in c.items():
            if campo != "volumen":
                setattr(h, campo, valor)

    # ── reparto entre quien vende y quien compra ────────────────────────
    h.S_i, h.SR_j = compute_savings(h.P, h.pi, h.techo_i, h.piso_j)
    tot = float(h.S_i.sum() + h.SR_j.sum())
    h.tajada_vendedor = 100.0 * float(h.SR_j.sum()) / tot if abs(tot) > 1e-9 else float("nan")

    # ── lo que queda con la red ─────────────────────────────────────────
    h.compra_red = np.zeros(N)
    h.vende_red = np.zeros(N)
    for q, i in enumerate(h.bids):
        h.compra_red[i] = max(float(h.D_net[q] - h.P[:, q].sum()), 0.0)
    for m, j in enumerate(h.sids):
        h.vende_red[j] = max(float(h.G_net[m] - h.P[m, :].sum()), 0.0)
    for j in h.retirados:                       # no entraron: exportan todo
        h.vende_red[j] = max(float(h.g_klim[j] - dat["D"][j, k]), 0.0)

    # ── la cola de la trayectoria, que dice si se detuvo ────────────────
    if h.tr is not None and getattr(h.tr, "pi_t", None) is not None:
        pit = np.asarray(h.tr.pi_t, float)
        if pit.shape[1] > 10:
            corte = int(pit.shape[1] * 0.9)
            h.cola = float(np.max(np.abs(pit[:, -1] - pit[:, corte])))

    h.resuelta = True
    return h


# ── composicion de las piezas ya validadas ──────────────────────────────
def _cotas(G_net, D_net, techo_i, piso_j, P):
    """Optimo, peor reparto y reparto ciego del mismo volumen."""
    from cotas_excedente import peor_reparto, reparto_ciego
    from eficiencia import descompone, excedente, optimo_centralizado

    cen = optimo_centralizado(G_net, D_net, techo_i, piso_j)
    if cen is None or cen["excedente"] <= 1e-9:
        return None
    peor = peor_reparto(G_net, D_net, techo_i, piso_j, cen["volumen"])
    ciego = excedente(reparto_ciego(G_net, D_net), techo_i, piso_j)
    exc, vol, ef, ef_vol, ef_emp = descompone(P, cen, techo_i, piso_j)
    return dict(mejor=cen["excedente"], peor=peor if peor is not None else 0.0,
                ciego=ciego, excedente=exc, volumen=vol,
                eficiencia=ef, ef_volumen=ef_vol, ef_emparejamiento=ef_emp)
