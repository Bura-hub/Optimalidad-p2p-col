"""
optimality.py  — Análisis de optimalidad del mercado P2P frente al colectivo
------------------------------------------------------------------------------
Brayan S. Lopez-Mendez · Udenar 2026

Actividad 4.2: dominancia del mecanismo P2P frente al colectivo de la CREG
101 072 (C4), mes a mes, en el horizonte y, como descripción, hora a hora.

D72 (2026-09-26, H-94, C-202)
=============================
1. **Los beneficios son los de la liquidación.** B_P2P y B_C4 de cada agente
   en cada hora son las matrices (N, T) que liquida el motor,
   ``cr.neto_horario["P2P"]`` y ``cr.neto_horario["C4"]`` (C-165). Este
   módulo ya no reconstruye ningún beneficio: la reconstrucción anterior
   valoraba la energía con una tarifa escalar, contaba al vendedor solo su
   prima sobre la bolsa nominal, contaba dos veces el autoconsumo del
   vendedor y llevaba a bolsa el excedente que la liquidación valora por el
   art. 25 con el cupo mensual. Su suma no coincidía con la hoja ``Resumen``
   en ninguno de los trece casos del canon (H-94). El análisis comprueba que
   su horizonte es el liquidado (``referencia_liquidacion``) y, si no, lanza
   ``ValueError``; omitir la comprobación exige ``sin_referencia=True``.

2. **El resultado principal es mes a mes y en el horizonte.** Con el cupo
   mensual (C-175), el dinero de una hora depende del resto de su mes: el
   corte hx del Anexo 4 decide qué parte del excedente se acredita a tarifa y
   qué parte va a bolsa. El mes es la unidad en que la liquidación se cierra.
   ``analyze_monthly_dominance`` da, por institución y en la comunidad,
   P2P − C4 de cada mes, quién domina cada mes, cuántos meses domina cada uno
   y el total del horizonte.

3. **La clasificación hora a hora es DESCRIPTIVA.** Reparte entre las horas
   el dinero de un mes que se decide mensualmente, de modo que depende de la
   convención con que el motor anota el crédito del corte hx en cada hora
   (``ADVERTENCIA_HORARIA``). Se informa aparte, con las horas con mercado y
   las horas sin mercado separadas: sin mercado, P2P y C4 NO son iguales,
   porque el mercado mueve el corte del mes.

Clasificación descriptiva de cada hora (con mercado):
  "P2P_dom"   : Delta_k >  umbral
  "C4_dom"    : Delta_k < −umbral
  "neutral"   : |Delta_k| ≤ umbral
  "inactive"  : no hubo mercado P2P (P_star None o ≈ 0); su Delta se informa
                aparte y no se clasifica
El umbral por defecto es el 5 % de la media de |B_P2P_k| en las horas con
mercado, con un mínimo de 1 COP.

GDR_k = Σ P_ji / min(Σ G_net_j, Σ D_net_i): eficiencia de despacho del
mercado en la hora (1 = coloca todo el lado corto).

Conjuntos de horas: ``B_p2p_total``, ``B_c4_total`` y ``delta_horizonte``
suman TODAS las horas; ``B_p2p_activas``, ``B_c4_activas`` y ``delta_total``
solo las que tuvieron mercado; ``delta_inactivas`` las demás. Nunca se
mezcla un conjunto con otro (tarea R, punto 1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

# Tolerancia con la liquidación, en COP: el total del horizonte debe ser el
# liquidado «al peso». Es también la banda en la que un mes cuenta como
# empate: por debajo de un peso el signo no es un resultado.
TOL_COP = 1.0

COMUNIDAD = "Comunidad"

ADVERTENCIA_HORARIA = (
    "La clasificación hora a hora es DESCRIPTIVA (D72): con el cupo mensual "
    "(C-175), el crédito del art. 25 se decide por mes con el corte hx del "
    "Anexo 4, y el reparto de ese dinero entre las horas es la convención "
    "con que el motor lo anota. El resultado se lee mes a mes y en el "
    "horizonte.")


# ── Clases de resultados ────────────────────────────────────────────────────

@dataclass
class HourlyOptimality:
    k:            int
    B_p2p:        float    # beneficio P2P liquidado en la hora k  [COP]
    B_c4:         float    # beneficio C4 liquidado en la hora k   [COP]
    delta:        float    # B_p2p - B_c4                           [COP]
    gdr:          float    # Global Dispatch Ratio  ∈ [0,1]
    category:     str      # "P2P_dom" | "C4_dom" | "neutral" | "inactive"
    kwh_p2p:      float    # kWh transados en P2P
    active:       bool     # True si hubo mercado activo
    mes:          str = "" # periodo de facturacion de la hora


@dataclass
class MonthlyDominance:
    """P2P frente a C4 por mes, por institución y en la comunidad (D72).

    ``B_p2p`` y ``B_c4`` son (A, M): una fila por institución, en el orden de
    ``agentes``, y la última fila es la comunidad. ``meses`` va en el orden
    en que aparece cada mes en el horizonte.
    """
    meses:    list
    agentes:  list
    B_p2p:    np.ndarray
    B_c4:     np.ndarray

    @property
    def delta(self) -> np.ndarray:
        return self.B_p2p - self.B_c4

    @property
    def domina(self) -> np.ndarray:
        """(A, M) de «P2P», «C4» o «empate» (|Delta| ≤ TOL_COP)."""
        d = self.delta
        out = np.full(d.shape, "empate", dtype=object)
        out[d > TOL_COP] = "P2P"
        out[d < -TOL_COP] = "C4"
        return out

    def fila(self, agente: str) -> int:
        return self.agentes.index(agente)

    def cuenta(self, agente: str = COMUNIDAD) -> dict:
        dom = list(self.domina[self.fila(agente)])
        return {"P2P": dom.count("P2P"), "C4": dom.count("C4"),
                "empate": dom.count("empate")}

    def total(self, agente: str = COMUNIDAD) -> tuple:
        """(B_P2P, B_C4, Delta) del horizonte para un agente o la comunidad."""
        i = self.fila(agente)
        p, c = float(self.B_p2p[i].sum()), float(self.B_c4[i].sum())
        return p, c, p - c

    def tabla(self):
        """Formato largo: agente, mes, B_P2P, B_C4, Delta y quién domina."""
        import pandas as pd
        dom = self.domina
        filas = []
        for i, a in enumerate(self.agentes):
            for m, mes in enumerate(self.meses):
                filas.append({"agente": a, "mes": mes,
                              "B_P2P_COP": float(self.B_p2p[i, m]),
                              "B_C4_COP": float(self.B_c4[i, m]),
                              "delta_COP": float(self.delta[i, m]),
                              "domina": dom[i, m]})
        return pd.DataFrame(filas)

    def resumen(self):
        """Por agente: meses que domina cada uno y el total del horizonte."""
        import pandas as pd
        filas = []
        for a in self.agentes:
            c = self.cuenta(a)
            p, q, d = self.total(a)
            filas.append({"agente": a, "meses": len(self.meses),
                          "meses_P2P": c["P2P"], "meses_C4": c["C4"],
                          "meses_empate": c["empate"],
                          "B_P2P_COP": p, "B_C4_COP": q, "delta_COP": d,
                          "veredicto_horizonte": _veredicto(d)})
        return pd.DataFrame(filas)


@dataclass
class OptimalitySummary:
    # Resultado principal (D72): mes a mes y en el horizonte
    mensual:        Optional[MonthlyDominance] = None

    # Conteos de horas por categoría (descriptivo)
    n_p2p_dom:      int   = 0
    n_c4_dom:       int   = 0
    n_neutral:      int   = 0
    n_inactive:     int   = 0
    n_active:       int   = 0
    T_total:        int   = 0

    # Estadísticas de delta (solo horas activas)
    delta_mean:     float = 0.0
    delta_std:      float = 0.0
    delta_total:    float = 0.0    # Σ (B_P2P - B_C4) en horas ACTIVAS [COP]
    delta_pct:      float = 0.0    # % de horas activas con P2P dominante

    # Estadísticas GDR (solo horas activas)
    gdr_mean:       float = 0.0
    gdr_std:        float = 0.0
    gdr_min:        float = 0.0
    gdr_max:        float = 0.0

    # Beneficios acumulados en TODAS las horas del horizonte
    B_p2p_total:    float = 0.0
    B_c4_total:     float = 0.0
    delta_horizonte: float = 0.0   # B_p2p_total - B_c4_total [COP]
    # Los mismos beneficios, solo en las horas ACTIVAS (delta_total es su
    # diferencia) y la diferencia en las horas sin mercado
    B_p2p_activas:  float = 0.0
    B_c4_activas:   float = 0.0
    delta_inactivas: float = 0.0
    kwh_p2p_total:  float = 0.0

    # Umbral usado en la clasificación descriptiva
    threshold_cop:  float = 0.0
    hourly_data:    list  = field(default_factory=list)   # list[HourlyOptimality]


# ── Validación de las entradas ─────────────────────────────────────────────

def _matriz_liquidada(x, nombre: str, forma: Optional[tuple] = None
                      ) -> np.ndarray:
    if x is None:
        raise ValueError(
            f"{nombre} es obligatorio (D72): el analisis de optimalidad usa "
            f"el beneficio horario que liquida el motor, cr.neto_horario")
    m = np.asarray(x, dtype=float)
    if m.ndim != 2:
        raise ValueError(f"{nombre} debe ser (N, T); llega con forma "
                         f"{m.shape}")
    if forma is not None and m.shape != forma:
        raise ValueError(f"{nombre} tiene forma {m.shape} y la otra matriz "
                         f"{forma}: no son el mismo horizonte")
    malas = np.argwhere(~np.isfinite(m))
    if malas.size:
        raise ValueError(
            f"{nombre}: {len(malas)} valor(es) no finito(s), el primero en "
            f"(agente {malas[0][0]}, hora {malas[0][1]}). Una suma con NaN no "
            f"clasifica nada")
    return m


def _etiqueta_mes(x) -> str:
    """YYYYMM entero (el del motor) → «YYYY-MM»; lo demás, como texto."""
    if isinstance(x, (int, np.integer)) and 100000 <= int(x) <= 999912:
        return f"{int(x) // 100:04d}-{int(x) % 100:02d}"
    return str(x)


def _etiquetas(month_labels, T: int) -> list:
    """El periodo de cada hora como texto; None es un solo periodo."""
    if month_labels is None:
        return ["horizonte"] * T
    crudas = list(np.asarray(month_labels).reshape(-1))
    if len(crudas) != T:
        raise ValueError(f"month_labels tiene {len(crudas)} etiquetas "
                         f"para T={T}")
    return [_etiqueta_mes(x) for x in crudas]


def _finito(x, rotulo: str) -> np.ndarray:
    a = np.asarray(x, dtype=float)
    if not np.all(np.isfinite(a)):
        raise ValueError(f"referencia_liquidacion[{rotulo!r}] no es finita: "
                         f"{x}")
    return a


def _comprueba_liquidacion(P: np.ndarray, C: np.ndarray,
                           referencia: Optional[dict],
                           sin_referencia: bool) -> None:
    """El horizonte de cada escenario es el liquidado, al peso (D72).

    La omision tiene que pedirse: sin `referencia_liquidacion` hace falta
    `sin_referencia=True`, y entonces se imprime un AVISO. Con la referencia,
    "P2P" y "C4" son obligatorios; "P2P_por_agente" y "C4_por_agente", si
    vienen, se comprueban agente por agente.
    """
    if referencia is None:
        if not sin_referencia:
            raise ValueError(
                "analyze_hourly_dominance: falta referencia_liquidacion "
                "(D72, M-1). Pasa {'P2P': cr.net_benefit['P2P'], 'C4': "
                "cr.net_benefit['C4']} o, si de verdad no hay liquidacion "
                "con que comparar, sin_referencia=True")
        print("    AVISO [D72]: optimalidad SIN comprobar contra la "
              "liquidacion (sin_referencia=True)")
        return
    if sin_referencia:
        raise ValueError("referencia_liquidacion y sin_referencia=True a la "
                         "vez: elige uno")
    propios = {"P2P": P, "C4": C}
    for esc, M in propios.items():
        if referencia.get(esc) is None:
            raise ValueError(
                f"referencia_liquidacion no trae {esc!r}: la comprobacion "
                f"contra la liquidacion no se salta en silencio (M-1)")
        ref = float(_finito(referencia[esc], esc))
        propio = float(M.sum())
        if abs(propio - ref) > TOL_COP:
            raise ValueError(
                f"optimalidad (D72): el B_{esc} del horizonte "
                f"({propio:,.2f} COP) no es el de la liquidacion "
                f"({ref:,.2f} COP); diferencia {propio - ref:+,.2f} COP. El "
                f"beneficio horario tiene que ser cr.neto_horario[{esc!r}]")
        clave = f"{esc}_por_agente"
        if referencia.get(clave) is None:
            continue
        por = _finito(referencia[clave], clave).reshape(-1)
        if por.size != M.shape[0]:
            raise ValueError(f"referencia_liquidacion[{clave!r}] trae "
                             f"{por.size} agentes y el horario {M.shape[0]}")
        dif = M.sum(axis=1) - por
        malo = int(np.argmax(np.abs(dif)))
        if abs(dif[malo]) > TOL_COP:
            raise ValueError(
                f"optimalidad (D72): el B_{esc} del agente {malo} "
                f"({M[malo].sum():,.2f} COP) no es el liquidado "
                f"({por[malo]:,.2f} COP)")


# ── Análisis mensual (resultado principal) ─────────────────────────────────

def analyze_monthly_dominance(
    p2p_horario: np.ndarray,
    c4_horario:  np.ndarray,
    month_labels: Optional[Sequence] = None,
    agent_names: Optional[Sequence[str]] = None,
) -> MonthlyDominance:
    """P2P − C4 de cada mes, por institución y en la comunidad (D72).

    Parameters
    ----------
    p2p_horario, c4_horario : (N, T)
        El dinero que liquida el motor por agente y hora,
        ``cr.neto_horario["P2P"]`` y ``cr.neto_horario["C4"]``.
    month_labels : (T,), optional
        El período de facturación de cada hora (YYYYMM del motor o texto).
        Con None, todo el horizonte es un solo período, «horizonte».
    agent_names : list, optional
        Nombres de las N instituciones; con None, «A1» … «AN».
    """
    P = _matriz_liquidada(p2p_horario, "p2p_horario")
    C = _matriz_liquidada(c4_horario, "c4_horario", P.shape)
    N, T = P.shape
    nombres = (list(agent_names) if agent_names is not None
               else [f"A{n + 1}" for n in range(N)])
    if len(nombres) != N:
        raise ValueError(f"agent_names tiene {len(nombres)} nombres para "
                         f"{N} agentes")
    if COMUNIDAD in nombres:
        raise ValueError(f"{COMUNIDAD!r} esta reservado para la fila de la "
                         f"comunidad")
    etiquetas = _etiquetas(month_labels, T)
    meses = list(dict.fromkeys(etiquetas))
    col = np.array([meses.index(e) for e in etiquetas])
    M = len(meses)
    Bp = np.zeros((N + 1, M))
    Bc = np.zeros((N + 1, M))
    for m in range(M):
        sel = col == m
        Bp[:N, m] = P[:, sel].sum(axis=1)
        Bc[:N, m] = C[:, sel].sum(axis=1)
    Bp[N] = Bp[:N].sum(axis=0)
    Bc[N] = Bc[:N].sum(axis=0)
    return MonthlyDominance(meses=meses, agentes=nombres + [COMUNIDAD],
                            B_p2p=Bp, B_c4=Bc)


# ── Análisis completo ───────────────────────────────────────────────────────

def analyze_hourly_dominance(
    p2p_horario:  np.ndarray,        # (N, T) cr.neto_horario["P2P"]
    c4_horario:   np.ndarray,        # (N, T) cr.neto_horario["C4"]
    p2p_results:  list,              # lista de HourlyResult, len = T
    D:            np.ndarray,        # (N, T) demanda [kWh], para el GDR
    G_klim:       np.ndarray,        # (N, T) generación limitada, para el GDR
    month_labels: Optional[Sequence] = None,
    agent_names:  Optional[Sequence[str]] = None,
    threshold_cop: Optional[float] = None,
    referencia_liquidacion: Optional[dict] = None,
    sin_referencia: bool = False,
) -> OptimalitySummary:
    """
    Dominancia P2P frente a C4: mes a mes, en el horizonte y hora a hora.

    Parameters
    ----------
    p2p_horario, c4_horario : (N, T)
        El beneficio liquidado por agente y hora (D72). Obligatorios.
    p2p_results : list
        Resultados del mercado, uno por hora: deciden qué horas tuvieron
        mercado, los kWh transados y el GDR. No entran en el dinero.
    month_labels, agent_names :
        Ver ``analyze_monthly_dominance``.
    threshold_cop : float, optional
        Umbral de la clasificación descriptiva; con None, el 5 % de la media
        de |B_P2P_k| en las horas con mercado (mínimo 1 COP).
    referencia_liquidacion : dict
        ``{"P2P": cr.net_benefit["P2P"], "C4": cr.net_benefit["C4"]}``, y
        opcionalmente ``"P2P_por_agente"`` y ``"C4_por_agente"`` con
        ``cr.net_benefit_per_agent``. Si el horizonte de este análisis se
        aparta más de ``TOL_COP`` del liquidado, lanza ``ValueError``.
        Obligatoria salvo con ``sin_referencia=True``.
    sin_referencia : bool
        Pide de forma explícita no comprobar contra la liquidación; se
        imprime un AVISO (M-1). Nunca se omite en silencio.
    """
    P = _matriz_liquidada(p2p_horario, "p2p_horario")
    C = _matriz_liquidada(c4_horario, "c4_horario", P.shape)
    N, T = P.shape
    if len(p2p_results) != T:
        raise ValueError(f"p2p_results tiene {len(p2p_results)} horas y el "
                         f"beneficio horario {T}")
    D = np.asarray(D, dtype=float)
    G_klim = np.asarray(G_klim, dtype=float)
    if D.shape != (N, T) or G_klim.shape != (N, T):
        raise ValueError(f"D {D.shape} y G_klim {G_klim.shape} deben ser "
                         f"{(N, T)}")

    _comprueba_liquidacion(P, C, referencia_liquidacion, sin_referencia)
    mensual = analyze_monthly_dominance(P, C, month_labels, agent_names)

    B_p2p_k = P.sum(axis=0)
    B_c4_k = C.sum(axis=0)
    etiquetas = _etiquetas(month_labels, T)
    hourly = []
    for k, res in enumerate(p2p_results):
        P_star = getattr(res, "P_star", None)
        active = (P_star is not None and float(np.sum(P_star)) > 1e-6)
        kwh_p2p, gdr = 0.0, 0.0
        if active:
            kwh_p2p = float(np.sum(P_star))
            G_net_j = np.array([max(float(G_klim[j, k]) - float(D[j, k]), 0.0)
                                for j in res.seller_ids])
            D_net_i = np.array([max(float(D[i, k]) - float(G_klim[i, k]), 0.0)
                                for i in res.buyer_ids])
            potential = min(float(np.sum(G_net_j)), float(np.sum(D_net_i)))
            gdr = (kwh_p2p / potential) if potential > 1e-9 else 0.0
            gdr = float(np.clip(gdr, 0.0, 1.0))
        hourly.append(HourlyOptimality(
            k=k, B_p2p=float(B_p2p_k[k]), B_c4=float(B_c4_k[k]),
            delta=float(B_p2p_k[k] - B_c4_k[k]), gdr=gdr,
            category="inactive", kwh_p2p=kwh_p2p, active=active,
            mes=etiquetas[k]))

    # ── Umbral adaptativo ────────────────────────────────────────────────────
    active_hrs = [h for h in hourly if h.active]
    if threshold_cop is None:
        if active_hrs:
            avg_b = np.mean([abs(h.B_p2p) for h in active_hrs])
            threshold_cop = max(avg_b * 0.05, 1.0)
        else:
            threshold_cop = 1.0

    # ── Clasificación descriptiva ─────────────────────────────────────────────
    for h in hourly:
        if not h.active:
            h.category = "inactive"
        elif h.delta > threshold_cop:
            h.category = "P2P_dom"
        elif h.delta < -threshold_cop:
            h.category = "C4_dom"
        else:
            h.category = "neutral"

    # ── Resumen agregado ──────────────────────────────────────────────────────
    cats = [h.category for h in hourly]
    deltas_active = [h.delta for h in active_hrs]
    gdrs_active   = [h.gdr   for h in active_hrs]

    summary = OptimalitySummary(
        mensual    = mensual,
        n_p2p_dom  = cats.count("P2P_dom"),
        n_c4_dom   = cats.count("C4_dom"),
        n_neutral  = cats.count("neutral"),
        n_inactive = cats.count("inactive"),
        n_active   = len(active_hrs),
        T_total    = len(hourly),
        delta_mean   = float(np.mean(deltas_active))  if deltas_active else 0.0,
        delta_std    = float(np.std(deltas_active))   if deltas_active else 0.0,
        delta_total  = float(np.sum(deltas_active))   if deltas_active else 0.0,
        delta_pct    = (cats.count("P2P_dom") / max(len(active_hrs), 1)) * 100.0,
        gdr_mean     = float(np.mean(gdrs_active))    if gdrs_active else 0.0,
        gdr_std      = float(np.std(gdrs_active))     if gdrs_active else 0.0,
        gdr_min      = float(np.min(gdrs_active))     if gdrs_active else 0.0,
        gdr_max      = float(np.max(gdrs_active))     if gdrs_active else 0.0,
        B_p2p_total  = float(np.sum(B_p2p_k)),
        B_c4_total   = float(np.sum(B_c4_k)),
        delta_horizonte = float(np.sum(B_p2p_k - B_c4_k)),
        B_p2p_activas = float(np.sum([h.B_p2p for h in active_hrs])),
        B_c4_activas  = float(np.sum([h.B_c4  for h in active_hrs])),
        delta_inactivas = float(np.sum([h.delta for h in hourly
                                        if not h.active])),
        kwh_p2p_total= float(np.sum([h.kwh_p2p for h in hourly])),
        threshold_cop= threshold_cop,
        hourly_data  = hourly,
    )
    _comprueba_conjuntos(summary)
    return summary


def _comprueba_conjuntos(s: OptimalitySummary) -> None:
    """Cada diferencia es la de los totales de SU conjunto de horas.

    Falla en voz alta si no: un total de un conjunto con la diferencia de
    otro es lo que hacía decir «P2P superior» en E4 con B_P2P por debajo de
    B_C4 (tarea R). Comprueba también que el mensual y el horario suman lo
    mismo.
    """
    pares = [
        ("horizonte", s.B_p2p_total - s.B_c4_total, s.delta_horizonte),
        ("horas activas", s.B_p2p_activas - s.B_c4_activas, s.delta_total),
        ("activas + sin mercado", s.delta_horizonte,
         s.delta_total + s.delta_inactivas),
    ]
    if s.mensual is not None:
        p, c, d = s.mensual.total(COMUNIDAD)
        pares += [("mensual, P2P", s.B_p2p_total, p),
                  ("mensual, C4", s.B_c4_total, c),
                  ("mensual, Delta", s.delta_horizonte, d)]
    for rotulo, esperado, guardado in pares:
        tol = 1e-6 * max(1.0, abs(esperado))
        if abs(esperado - guardado) > tol:
            raise ValueError(
                f"optimalidad ({rotulo}): {guardado:,.2f} no es "
                f"{esperado:,.2f}")


def _veredicto(delta: float) -> str:
    """Quién gana por el signo de la diferencia; |Delta| ≤ TOL_COP es empate."""
    if delta > TOL_COP:
        return "P2P superior"
    if delta < -TOL_COP:
        return "C4 superior"
    return "empate"


# ── Tablas para exportar ──────────────────────────────────────────────────────

def tabla_horaria(summary: OptimalitySummary):
    """Una fila por hora: su dinero, su mercado y su categoria descriptiva."""
    import pandas as pd
    return pd.DataFrame([{
        "hora": h.k, "mes": h.mes, "mercado": h.active,
        "kwh_p2p": h.kwh_p2p, "B_P2P_COP": h.B_p2p, "B_C4_COP": h.B_c4,
        "delta_COP": h.delta, "categoria_descriptiva": h.category,
        "gdr": h.gdr} for h in summary.hourly_data])


def exporta_optimalidad(summary: OptimalitySummary, carpeta: str,
                        prefijo: str = "optimalidad") -> list:
    """Escribe el mensual, su resumen y el horario en CSV (D72).

    ``<prefijo>_mensual.csv`` (agente x mes), ``<prefijo>_resumen.csv`` (por
    agente, con el horizonte) y ``<prefijo>_horaria.csv`` (descriptiva).
    """
    import os
    if summary.mensual is None:
        raise ValueError("exporta_optimalidad: el resumen no trae el mensual")
    os.makedirs(carpeta, exist_ok=True)
    rutas = []
    for nombre, df in (("mensual", summary.mensual.tabla()),
                       ("resumen", summary.mensual.resumen()),
                       ("horaria", tabla_horaria(summary))):
        ruta = os.path.join(carpeta, f"{prefijo}_{nombre}.csv")
        df.to_csv(ruta, index=False, encoding="utf-8")
        rutas.append(ruta)
    return rutas


# ── Impresión consola ──────────────────────────────────────────────────────────

def print_optimality_report(
    summary: OptimalitySummary,
    agent_names: Optional[list] = None,
    currency: str = "COP",
) -> None:
    """Imprime el análisis: primero el mes, después el horizonte y la hora."""
    s = summary
    T = s.T_total
    A = max(s.n_active, 1)
    mm = s.mensual

    print("\n" + "="*72)
    print("  ANÁLISIS DE OPTIMALIDAD — P2P vs C4 (D72: beneficio liquidado)")
    print("="*72)

    if mm is not None:
        print(f"  1. Mes a mes (resultado principal), comunidad:")
        print(f"    {'Mes':<10} {'B_P2P':>14} {'B_C4':>14} {'Delta':>13}  Domina")
        i = mm.fila(COMUNIDAD)
        for m, mes in enumerate(mm.meses):
            print(f"    {mes:<10} {mm.B_p2p[i, m]:>14,.0f} "
                  f"{mm.B_c4[i, m]:>14,.0f} {mm.delta[i, m]:>13,.0f}  "
                  f"{mm.domina[i, m]}")
        c = mm.cuenta(COMUNIDAD)
        print(f"    Meses: P2P domina {c['P2P']}, C4 domina {c['C4']}, "
              f"empate {c['empate']} (de {len(mm.meses)})")
        print(f"  Por institución ({currency}, horizonte):")
        print(f"    {'Agente':<10} {'P2P/C4/emp.':>11} {'Delta':>14}  Veredicto")
        for a in mm.agentes:
            c = mm.cuenta(a)
            d = mm.total(a)[2]
            print(f"    {a:<10} {c['P2P']:>3}/{c['C4']}/{c['empate']:<5}"
                  f" {d:>14,.0f}  {_veredicto(d)}")
        print()

    print(f"  2. Horizonte ({T} h):")
    print(f"    B_P2P : {s.B_p2p_total:>14,.0f} {currency}")
    print(f"    B_C4  : {s.B_c4_total:>14,.0f} {currency}")
    print(f"    Delta : {s.delta_horizonte:>14,.0f} {currency}  "
          f"({_veredicto(s.delta_horizonte)})")
    print()

    print("  3. Hora a hora (DESCRIPTIVO):")
    print(f"    {ADVERTENCIA_HORARIA}")
    print(f"    Horas con mercado: {s.n_active} de {T} "
          f"({100*s.n_active/max(T, 1):.1f}%); umbral neutral "
          f"±{s.threshold_cop:,.0f} {currency}")
    print(f"      P2P dominante : {s.n_p2p_dom:>5} h  ({100*s.n_p2p_dom/A:5.1f}%)")
    print(f"      C4  dominante : {s.n_c4_dom:>5} h  ({100*s.n_c4_dom/A:5.1f}%)")
    print(f"      Neutral       : {s.n_neutral:>5} h  ({100*s.n_neutral/A:5.1f}%)")
    print(f"      Delta en horas con mercado : {s.delta_total:>14,.0f} "
          f"{currency}  (media {s.delta_mean:,.0f}, desv. {s.delta_std:,.0f} "
          f"{currency}/h)")
    print(f"      Delta en horas sin mercado ({s.n_inactive} h): "
          f"{s.delta_inactivas:>14,.0f} {currency}")
    if (s.delta_total > TOL_COP and s.delta_horizonte < -TOL_COP) or \
            (s.delta_total < -TOL_COP and s.delta_horizonte > TOL_COP):
        print(f"      AVISO: las horas con mercado y el horizonte dan "
              f"veredictos contrarios; el signo lo ponen las {s.n_inactive} "
              f"horas sin mercado")
    print(f"      GDR medio {s.gdr_mean:.3f} (mín. {s.gdr_min:.3f}, "
          f"máx. {s.gdr_max:.3f})")
    print("="*72)
