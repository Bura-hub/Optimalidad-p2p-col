"""
El corte del piso calculado con lo que se sabe en cada hora (AE-4).

Actividades 2.2 y 3.3. Revision r1 del articulo (envio 11297), comentario
AE-4 del editor asociado: «a temporally consistent settlement procedure that
updates credit balances as actual transactions occur». Diseno en
`Documentos/articulo_latam/v2_es/revision_r1/diseno_mediciones_completas.md`,
seccion 2; decisiones del autor del 2026-11-21 en `decisiones.md`.

QUE CAMBIA Y QUE NO. La liquidacion del mercado ya es la de la norma: el
Anexo 4 de la CREG 101 072 al cierre del mes sobre los residuales que resolvio
el mercado. Lo unico que usa informacion que en tiempo real no se tiene es el
CORTE QUE ENTRA EN EL PISO del vendedor (`opciones_externas.piso_residual`),
que se calcula antes del mercado con las series aproximadas y la importacion
TOTAL del mes (CANON §14.27). Este modulo lo sustituye por tres variantes:

  iterado               punto fijo: el corte con los residuales que resolvio
                        el mercado en la iteracion anterior (conserva la
                        prevision del mes, quita la aproximacion del residual);
  secuencial_pronostico en la hora k, con el saldo REAL hasta k-1 y la
                        importacion del mes extrapolada en linea recta
                        (`prevision_corte.py`, CANON §14.27);
  secuencial_saldo      en la hora k, con el saldo conocido: es permuta solo lo
                        que cubre importacion ya registrada.

EL SALDO. Por miembro y mes, en orden FIFO (`SaldoFIFO`): lo inyectado cubre
primero la importacion pendiente; lo que sobra es exceso provisional, en cola;
lo importado cubre primero el exceso provisional MAS ANTIGUO. Al cierre, lo que
queda en la cola es exceso y va a la bolsa de su hora. Con FIFO eso es el
Anexo 4 (CANON §14.40, punto 7; `test_corte_secuencial.py`).

LA PARALELIZACION. El piso de la hora k depende de lo que el mercado transo
en las horas anteriores del mismo mes, de modo que dentro del mes las horas
son una cadena. El saldo se reinicia cada mes (C-175): cada mes es una cadena
independiente y se resuelve en un proceso aparte. `EMSP2P.run` no se toca: la
cadena llama a `EMSP2P.run_single_hour`, que honra las mismas cotas.

Nada de esto actua por defecto: `main_simulation.py --corte-piso mes` (el
defecto) no importa este modulo.
"""
from __future__ import annotations

import copy
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor, TimeoutError as _Vencido
from typing import Optional

import numpy as np

from core.opciones_externas import (piso_por_vendedor, reparto_anexo4,
                                    residual_proporcional)

REGLAS_SECUENCIALES = ("fija", "secuencial_pronostico", "secuencial_saldo")
CORTES = ("mes", "iterado", "secuencial_pronostico", "secuencial_saldo")


# ── El saldo FIFO ──────────────────────────────────────────────────────────

class SaldoFIFO:
    """El saldo de credito de N miembros en un mes, en orden FIFO.

    `pendiente[n]`: importacion registrada que ninguna inyeccion cubre aun.
    `cola[n]`: exceso provisional, pares [hora, kWh] en orden de llegada.
    Nunca hay a la vez importacion pendiente y exceso provisional.
    """

    def __init__(self, N: int):
        self.N = N
        self.pendiente = np.zeros(N)
        self.cola = [deque() for _ in range(N)]
        self.inyectado = np.zeros(N)
        self.importado = np.zeros(N)

    def actualiza(self, k: int, sr: np.ndarray, dr: np.ndarray) -> None:
        """Anota la inyeccion `sr` y la importacion `dr` residuales (N,) de la
        hora k, en ese orden para cada miembro (en una hora un miembro inyecta
        o importa; si llegaran las dos, primero la inyeccion)."""
        for n in range(self.N):
            s = float(sr[n])
            d = float(dr[n])
            if s < 0.0 or d < 0.0 or not (np.isfinite(s) and np.isfinite(d)):
                raise ValueError(f"saldo: residual negativo o no finito en la "
                                 f"hora {k}, miembro {n}")
            self.inyectado[n] += s
            self.importado[n] += d
            if s > 0.0:
                c = min(s, self.pendiente[n])
                self.pendiente[n] -= c
                if s - c > 0.0:
                    self.cola[n].append([k, s - c])
            if d > 0.0:
                q = self.cola[n]
                while d > 0.0 and q:
                    u = min(q[0][1], d)
                    q[0][1] -= u
                    d -= u
                    if q[0][1] <= 0.0:
                        q.popleft()
                self.pendiente[n] += d

    def exceso_provisional(self) -> np.ndarray:
        return np.array([sum(e for _, e in q) for q in self.cola])

    def cierra(self, T: int) -> np.ndarray:
        """(N, T) el exceso al cierre del mes, en la hora de cada inyeccion."""
        exc = np.zeros((self.N, T))
        for n, q in enumerate(self.cola):
            for h, e in q:
                exc[n, h] += e
        return exc


def liquida_fifo(sr: np.ndarray, dr: np.ndarray,
                 etiqueta_mes: Optional[np.ndarray] = None):
    """La liquidacion FIFO entera de unas series residuales (N, T). Devuelve
    (credito, exceso) como `reparto_anexo4`."""
    sr = np.asarray(sr, dtype=float)
    dr = np.asarray(dr, dtype=float)
    N, T = sr.shape
    etiquetas = (np.zeros(T, dtype=int) if etiqueta_mes is None
                 else np.asarray(etiqueta_mes))
    exceso = np.zeros((N, T))
    for mes in np.unique(etiquetas):
        idx = np.flatnonzero(etiquetas == mes)
        saldo = SaldoFIFO(N)
        for k in idx:
            saldo.actualiza(int(k), sr[:, k], dr[:, k])
        exceso += saldo.cierra(T)
    return sr - exceso, exceso


# ── La marca de permuta en la hora k ────────────────────────────────────────

def marca_permuta(regla: str, saldo: SaldoFIFO, sr_k: np.ndarray,
                  dr_k: np.ndarray, h_k: int, H_m: int) -> np.ndarray:
    """(N,) True si el residual de la hora k de cada miembro se da por credito
    al fijar su piso. `sr_k`, `dr_k`: los residuales aproximados de la hora
    (`residual_proporcional`); `saldo`: el estado real hasta k-1; `h_k`: horas
    transcurridas del mes con k incluida; `H_m`: horas del mes. La hora que
    cruza el cupo ya va a la bolsa, como en `reparto_anexo4`."""
    I = saldo.inyectado + np.asarray(sr_k, float)
    R = saldo.importado + np.asarray(dr_k, float)
    if regla == "secuencial_pronostico":
        R_hat = np.maximum(R, R * (float(H_m) / float(h_k)))
        return I <= R_hat
    if regla == "secuencial_saldo":
        return I <= R
    raise ValueError(f"regla {regla!r}; se esperaba secuencial_pronostico o "
                     f"secuencial_saldo")


# ── La cadena de un mes ─────────────────────────────────────────────────────

def _flujos_hora(r, N: int):
    """(vendido, comprado) (N,) de un resultado horario."""
    v = np.zeros(N)
    q = np.zeros(N)
    if r.P_star is not None and r.seller_ids and r.buyer_ids:
        P = np.asarray(r.P_star, dtype=float)
        if P.size and np.isfinite(P).all():
            for a, j in enumerate(r.seller_ids):
                v[j] = float(P[a, :].sum())
            for b, i in enumerate(r.buyer_ids):
                q[i] = float(P[:, b].sum())
    return v, q


def _cadena_mes(args):
    """Resuelve las horas de un mes en orden. Es la tarea de cada proceso."""
    (ems, D, G, horas, cu, ded, bolsa, iny_r, ret_r, regla, piso_base,
     trayectorias) = args
    N, T = D.shape
    ems = copy.copy(ems)
    ems.grid = copy.copy(ems.grid)
    piso = np.array(piso_base, dtype=float, copy=True)
    ems.grid.pi_gb_agente = piso
    exc = np.maximum(G - D, 0.0)
    dfc = np.maximum(D - G, 0.0)
    saldo = SaldoFIFO(N)
    H_m = len(horas)
    resultados, marcas = [], np.ones((N, len(horas)), dtype=bool)
    t0 = time.perf_counter()
    for pos, k in enumerate(horas):
        if regla != "fija":
            m = marca_permuta(regla, saldo, iny_r[:, k], ret_r[:, k],
                              pos + 1, H_m)
            marcas[:, pos] = m
            piso[:, k] = np.where(m, cu[:, k] - ded[:, k], bolsa[k])
        r = ems.run_single_hour(int(k), D, G,
                                devuelve_trayectoria=trayectorias)
        v, q = _flujos_hora(r, N)
        saldo.actualiza(int(k), np.maximum(exc[:, k] - v, 0.0),
                        np.maximum(dfc[:, k] - q, 0.0))
        resultados.append(r)
    return (list(horas), resultados, piso[:, horas], marcas,
            time.perf_counter() - t0)


def resuelve_secuencial(ems, D, G, cu, ded, bolsa, etiqueta_mes,
                        regla: str = "secuencial_pronostico",
                        procesos: Optional[int] = None,
                        plazo_hora_s: Optional[float] = None,
                        piso_base: Optional[np.ndarray] = None):
    """El mercado con el corte del piso fijado hora a hora con el saldo real.

    ems: un `EMSP2P` armado como el de la corrida (sin DR: alpha = 0).
    D, G (N, T); cu, ded (N, T): tarifa y deduccion del art. 25 del vendedor;
    bolsa (T,); etiqueta_mes (T,).
    regla: una de REGLAS_SECUENCIALES. ``fija`` no actualiza nada y usa
        `piso_base` (o el de la rejilla): solo sirve para comprobar que la
        cadena es el motor (`test_corte_secuencial.py`).
    procesos: cuantos meses a la vez (None: tantos como meses; 0 o 1: en este
        proceso). plazo_hora_s: tope por hora; el de un mes es ese tope por
        sus horas, y si se pasa la corrida falla en voz alta (D24, H-50).

    Devuelve (resultados (lista de HourlyResult, por hora), piso (N, T)
    usado, marcas (N, T) de permuta, segundos por mes)."""
    if regla not in REGLAS_SECUENCIALES:
        raise ValueError(f"regla {regla!r}; se esperaba una de "
                         f"{REGLAS_SECUENCIALES}")
    alpha = getattr(ems.agents, "alpha", None)
    if alpha is not None and np.any(np.asarray(alpha) > 1e-12):
        raise ValueError("el corte secuencial no admite el programa DR "
                         "(alpha > 0): la cadena usa la demanda medida")
    D = np.asarray(D, dtype=float)
    G = np.asarray(G, dtype=float)
    N, T = D.shape
    cu = np.asarray(cu, dtype=float)
    ded = np.asarray(ded, dtype=float)
    bolsa = np.asarray(bolsa, dtype=float).reshape(-1)
    if piso_base is None:
        piso_base = ems.grid.pi_gb_agente
    if piso_base is None:
        raise ValueError("el corte secuencial necesita el piso por vendedor "
                         "(corrida con calendario)")
    piso_base = np.asarray(piso_base, dtype=float)
    for nombre, x in (("cu", cu), ("ded", ded), ("piso_base", piso_base)):
        if x.shape != (N, T) or not np.isfinite(x).all():
            raise ValueError(f"{nombre} no valido para el corte secuencial")
    iny_r, ret_r = residual_proporcional(G, D)
    etiquetas = np.asarray(etiqueta_mes)
    meses = [np.flatnonzero(etiquetas == m) for m in
             sorted(np.unique(etiquetas), key=lambda m: np.flatnonzero(
                 etiquetas == m)[0])]
    tray = bool(getattr(ems.solver, "guarda_trayectorias", False))
    tareas = [(ems, D, G, h, cu, ded, bolsa, iny_r, ret_r, regla, piso_base,
               tray) for h in meses]
    salidas = []
    if procesos is not None and procesos <= 1:
        salidas = [_cadena_mes(t) for t in tareas]
    else:
        n = min(len(tareas), procesos or len(tareas))
        with ProcessPoolExecutor(max_workers=n) as ex:
            futuros = [ex.submit(_cadena_mes, t) for t in tareas]
            for f, h in zip(futuros, meses):
                tope = None if not plazo_hora_s else plazo_hora_s * len(h)
                try:
                    salidas.append(f.result(timeout=tope))
                except _Vencido:
                    for p in list(getattr(ex, "_processes", {}).values()):
                        p.kill()
                    raise RuntimeError(
                        f"el corte secuencial: un mes de {len(h)} horas paso "
                        f"su tope de {tope:.0f} s (D24); la corrida no sigue")
    resultados = [None] * T
    piso = np.array(piso_base, dtype=float, copy=True)
    marcas = np.ones((N, T), dtype=bool)
    segundos = []
    for horas, res, piso_h, marca_h, seg in salidas:
        for k, r in zip(horas, res):
            resultados[k] = r
        piso[:, horas] = piso_h
        marcas[:, horas] = marca_h
        segundos.append(seg)
    if any(r is None for r in resultados):
        raise RuntimeError("el corte secuencial dejo horas sin resultado")
    return resultados, piso, marcas, segundos


# ── La variante iterada ─────────────────────────────────────────────────────

def residuales_de(resultados, D, G):
    """(sr, dr) (N, T) los residuales que dejo el mercado."""
    D = np.asarray(D, dtype=float)
    G = np.asarray(G, dtype=float)
    N, T = D.shape
    v = np.zeros((N, T))
    q = np.zeros((N, T))
    for r in resultados:
        vk, qk = _flujos_hora(r, N)
        v[:, r.k] = vk
        q[:, r.k] = qk
    return (np.maximum(np.maximum(G - D, 0.0) - v, 0.0),
            np.maximum(np.maximum(D - G, 0.0) - q, 0.0))


def resuelve_iterado(ems, D, G, cu, ded, bolsa, etiqueta_mes, en_permuta0,
                     max_iter: int = 8, resultados0=None):
    """Punto fijo del corte: resuelve, recalcula el corte con los residuales
    que resolvio (`reparto_anexo4`), rehace el piso y repite hasta que la marca
    no cambie en ninguna hora-vendedor, o `max_iter` veces. Si la marca vuelve
    a un estado ya visto, para y lo dice (ciclo).

    `en_permuta0` es la marca con que se armo el piso de la rejilla (la del
    canon, `piso_residual`). La iteracion i compara la marca que dan los
    residuales resueltos con la que se uso para resolverlos.

    Devuelve (resultados, G_klim, D_star, piso (N, T), historial), con el
    historial una lista de dicts por iteracion: horas-vendedor que cambian de
    marca, si hubo ciclo y si convergio."""
    D = np.asarray(D, dtype=float)
    G = np.asarray(G, dtype=float)
    cu = np.asarray(cu, dtype=float)
    ded = np.asarray(ded, dtype=float)
    bolsa = np.asarray(bolsa, dtype=float).reshape(-1)
    vende = np.maximum(G - D, 0.0) > 1e-9
    ems = copy.copy(ems)
    ems.grid = copy.copy(ems.grid)
    piso = np.array(ems.grid.pi_gb_agente, dtype=float, copy=True)
    if resultados0 is None:
        resultados, G_klim, D_star = ems.run(D, G)
    else:
        resultados, G_klim, D_star = resultados0
    marca = np.asarray(en_permuta0, dtype=bool)
    vistas = [np.packbits(marca & vende).tobytes()]
    historial = []
    for it in range(1, max_iter + 1):
        sr, dr = residuales_de(resultados, D, G)
        nueva = reparto_anexo4(sr, dr, etiqueta_mes)[2]
        cambian = int(np.sum((nueva != marca) & vende))
        clave = np.packbits(nueva & vende).tobytes()
        ciclo = cambian > 0 and clave in vistas
        historial.append(dict(iteracion=it, cambian=cambian, ciclo=ciclo,
                              convergio=cambian == 0))
        if cambian == 0 or ciclo:
            break
        vistas.append(clave)
        marca = nueva
        piso = piso_por_vendedor(cu, ded, bolsa, marca)
        ems.grid.pi_gb_agente = piso
        resultados, G_klim, D_star = ems.run(D, G)
    return resultados, G_klim, D_star, piso, historial
