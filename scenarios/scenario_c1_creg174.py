"""
scenario_c1_creg174.py
----------------------
Escenario C1: Autogeneración a Pequeña Escala (AGPE)
Resolución CREG 174 de 2021 — balance por período de facturación

Mecanismo (alineado con el art. 25 de la CREG 174 — renumeración CAL-31,
residuo "arts. 22-23" corregido 2026-06-11 — y Decreto 2469/2014):
  1. Autoconsumo directo hora a hora  → ahorro = pi_gs
                                          (la energía nunca pasó por la
                                          red; no se factura C sobre esos
                                          kWh).
  2. Inyección a la red dentro del mes → crédito de energía hasta igualar la
     importación del MES ENTERO (art. 25, texto del art. 28 de la CREG 101 072;
     C-175). Cada kWh permutado vale (pi_gs − deducción): el componente de
     comercializar si la planta tiene hasta 100 kW, y T+D+Cv+PR+R entre 100 kW
     y 1 MW (numerales 1 y 2 del art. 25).
  3. La inyección posterior al corte hx del Anexo 4 de la CREG 101 072 (la hora
     en que la inyección acumulada alcanza la importación total del mes) se
     liquida a la bolsa de cada hora, que es la regla transitoria vigente
     mientras el MCm no aplique (parágrafo del art. 25; Conceptos CREG 3018 y
     3023 de 2026).

Diferencia estructural con C3:
  C1 (este módulo):  liquidación en el período de facturación (mes).
     La permuta (Tipo 1) se valora a (pi_gs − pi_C); solo el excedente
     post-cruce (Tipo 2) llega a bolsa horaria.
  C3 (scenario_c3_spot): liquidación hora a hora.
     Cada kWh excedente de cada hora → bolsa(h).
     El agente asume volatilidad spot completa.

Cuando pi_bolsa < (pi_gs − pi_C) (caso habitual en Colombia), C1 sigue
siendo favorable porque la permuta Tipo 1 se valora a la tarifa retail
neta de Comercialización en vez de a precio mayorista. El autoconsumo
captura el spread completo pi_gs.

Histórico:
  Pre-CAL-10 (≤ 2026-04-29): el escenario valoraba auto + permuta a pi_gs
    completo y el excedente neto mensual al promedio ponderado de bolsa.
    Esa formulación sobreestimaba el beneficio de C1 en 3-8% al ignorar
    el componente C de Comercialización y la mecánica de "hora Hx".
    Para reproducirla en tests/regresión: pasar component_c=0.0.

Parámetros nuevos en CAL-10
---------------------------
component_c : "auto" | None | float | (N,) | (N, T)
    Componente de Comercialización (COP/kWh) que el comercializador sigue
    cobrando aunque el AGPE permute energía. "auto" usa la fracción
    proporcional al CU (≈ 13.85% del pi_gs); 0.0 reproduce el comportamiento
    legacy pre-CAL-10. Ver scenarios/_pi_gs.py:as_component_c_array.

month_labels : array (T,) de enteros con etiqueta del período de facturación
               (p.ej. año×100+mes: 202507, 202508, …).
               Si None, todo el horizonte se trata como un único período
               (equivalente al modo perfil-diario de 24 h).

Referencia regulatoria:
    CREG 174 de 2021 - Artículo 5  (pequeña escala ≤ 1 MW)
    CREG 174 de 2021 - Art. 25, numerales 1 y 2; CREG 101 072 de 2025 - Anexo 4 (corte hx)
    Decreto MinEnergía 2469 de 2014 - art. 2.2.3.2.4.1
    CREG 119 de 2007 - estructura del Costo Unitario (CU = G+T+D+C+PR+otros)

Actividad 2.2.
"""

from __future__ import annotations

import numpy as np
from collections import defaultdict
from typing import Optional, Union

from ._pi_gs import as_pi_gs_array, as_component_c_array
from core.opciones_externas import deduccion_art25, reparto_anexo4


def run_c1_creg174(
    D:            np.ndarray,                # (N, T) demanda base [kWh]
    G:            np.ndarray,                # (N, T) generación bruta [kWh]
    pi_gs:        Union[float, np.ndarray],  # escalar, (N,) o (N, T) — CAL-9
    pi_bolsa:     np.ndarray,                # (T,) precio de bolsa horario $/kWh
    agent_ids:    list,                      # índices de agentes autogeneradores
    month_labels: Optional[np.ndarray] = None,  # (T,) etiqueta de período (ej. YYYYMM)
    component_c:  Union[str, float, np.ndarray, None] = "auto",  # CAL-10
    dt:           float = 1.0,               # CAL-46: duración del paso en horas
    capacidad_kw: Optional[np.ndarray] = None,  # (N,) kW; decide el numeral
    tolls:        Union[float, np.ndarray, None] = None,  # T+D+PR+R (num. 2)
) -> dict:
    """
    Simula el esquema CREG 174 con balance por período de facturación,
    descuento de componente C y separación Excedentes Tipo 1 / Tipo 2.

    Para cada agente n y cada período de facturación m, hora local k del mes:

        surplus_h[k] = max(G[n,k] - D[n,k], 0)   ← inyectado a la red
        deficit_h[k] = max(D[n,k] - G[n,k], 0)   ← retirado de la red
        auto_h[k]    = min(G[n,k], D[n,k])       ← autoconsumo directo

    Clasificación al cierre del período (CREG 174 art. 25, texto del art. 28
    de la CREG 101 072 de 2025; corrección C-175):
    -- NOTA TERMINOLÓGICA (CAL-31, 2026-05-03): "Tipo 1", "Tipo 2" y
       "hora Hx" son denominaciones DIDÁCTICAS del sector (EDEQ, Solsta,
       etc.), NO cita literal de CREG 174/2021. El art. 25 habla de
       "crédito de energía" (excedentes ≤ importación) y "valoración
       horaria del residual" (excedentes > importación). El algoritmo
       implementa esa mecánica con etiquetas internas.

        credito, exceso = reparto_anexo4(surplus_h, deficit_h)   # Anexo 4
        # hx: primera hora del mes en que la inyección acumulada alcanza la
        # importación TOTAL del mes; la inyección de esa hora se parte.

    Liquidación del período:

        E_auto       = Σ_k auto_h[k]
        E_permuted_1 = Σ_k surplus_tipo1[k]            (Tipo 1)
        savings_m    = E_auto × pi_gs_period
                       + E_permuted_1 × (pi_gs_period − pi_C_period)
        revenue_m    = Σ_k surplus_tipo2[k] × pi_bolsa[k]   (Tipo 2, horario)

        net_benefit_n = Σ_m (savings_m + revenue_m)

    Justificación de la asimetría auto / permuta:
        - Autoconsumo: la energía no atraviesa la red, no entra al sistema
          de medición ni a la facturación de la comercializadora; por lo
          tanto C no aplica.
        - Permuta Tipo 1: la energía sí circula por la red distribución y
          por el sistema de medición bidireccional, lo que justifica que
          el comercializador siga cobrando C bajo CREG 174 art. 25
          (créditos de energía).

    Notas
    -----
    - Si la inyección acumulada del mes no alcanza la importación del mes,
      hx = None y todo el surplus se permuta como Tipo 1.
    - Si la inyección supera al retiro desde la primera hora, hx=0 y
      surplus_tipo1 puede ser 0 para todo el mes.
    - El costo residual de red (energía aún comprada cuando deficit > surplus)
      mantiene la convención original: cobrado a pi_gs_period.
    """
    N, T = D.shape
    pi_gs_v = as_pi_gs_array(pi_gs, N, T)              # (N, T) — CAL-9
    pi_C_v  = as_component_c_array(component_c, pi_gs_v, N, T)  # (N, T) — CAL-10

    # Numeral del art. 25 por capacidad instalada (spec 4.11): hasta 100 kW
    # se cobra Cv; entre 100 kW y 1 MW, T+D+Cv+PR+R.
    tolls_v = (None if tolls is None
               else as_component_c_array(tolls, pi_gs_v, N, T,
                                         rellena_nan=False))
    pi_C_v = deduccion_art25(pi_C_v, tolls_v, capacidad_kw)

    # ── Construir índice de períodos ─────────────────────────────────────────
    if month_labels is None:
        # Período único (modo perfil diario 24h o sintético)
        period_hours: dict[int, list[int]] = {0: list(range(T))}
    else:
        period_hours = defaultdict(list)
        for k, m in enumerate(month_labels):
            period_hours[int(m)].append(k)

    results: dict = {}
    total_savings         = 0.0
    total_surplus_revenue = 0.0
    total_grid_cost       = 0.0
    total_e_permuted_t1   = 0.0
    total_e_tipo2         = 0.0
    total_e_auto          = 0.0

    # C-165: el desglose por hora y agente del beneficio, para poder decir en
    # QUE meses y en QUE horas cada mecanismo reparte mejor. Se llena con los
    # mismos vectores con los que ya se calcula el total, antes de sumarlos, de
    # modo que no puede derivar: la compuerta comprueba que cada fila suma
    # exactamente el total que este mismo modulo reporta.
    neto_horario = np.zeros_like(np.asarray(D, dtype=float))

    for n in agent_ids:
        savings_n     = 0.0
        surplus_n     = 0.0
        grid_cost_n   = 0.0
        e_permuted_n  = 0.0
        e_tipo2_n     = 0.0
        e_auto_n      = 0.0
        hx_history_n  = []   # registro de hx por período (debugging/monthly)

        for _m, hours in period_hours.items():
            # ── Vectores del período ─────────────────────────────────────
            G_h = np.maximum(G[n, hours], 0.0)  # generación  (≥0)
            D_h = np.maximum(D[n, hours], 0.0)  # demanda     (≥0)
            pb_h = pi_bolsa[hours]               # precios bolsa del período

            # ── Flujos horarios ──────────────────────────────────────────
            auto_h     = np.minimum(G_h, D_h)   # autoconsumo directo (kWh)
            surplus_h  = G_h - auto_h            # inyectado a la red  (≥0)
            deficit_h  = D_h - auto_h            # retirado de la red  (≥0)

            # ── Corte hx del Anexo 4 (C-175, C-177) ─────────────────────
            credito, exceso, _ = reparto_anexo4(surplus_h[None, :],
                                                deficit_h[None, :])
            surplus_t1, surplus_t2 = credito[0], exceso[0]
            con_exceso = np.flatnonzero(surplus_t2 > 0.0)
            hx = int(con_exceso[0]) if con_exceso.size else None
            hx_history_n.append(hx)

            # ── Totales del período ──────────────────────────────────────
            E_auto       = float(np.sum(auto_h))
            E_surplus    = float(np.sum(surplus_h))
            E_deficit    = float(np.sum(deficit_h))
            E_permuted_1 = float(np.sum(surplus_t1))
            E_tipo2      = float(np.sum(surplus_t2))

            # ── Valoración ───────────────────────────────────────────────
            # Autoconsumo: pi_gs completo (no toca la red → C no aplica).
            # Permuta Tipo 1: (pi_gs - pi_C) (sí toca la red, C se factura).
            # CREG 174 art. 25 (créditos + valoración horaria),
            # Decreto 2469/2014 art. 2.2.3.2.4.1.
            pi_gs_period = float(pi_gs_v[n, hours].mean())
            pi_C_period  = float(pi_C_v[n, hours].mean())
            pi_eff_t1    = pi_gs_period - pi_C_period
            savings_m    = E_auto * pi_gs_period + E_permuted_1 * pi_eff_t1

            # Excedente Tipo 2 → bolsa horaria (no promedio).
            revenue_m = float(np.dot(surplus_t2, pb_h))

            # Costo residual de red (déficit no cubierto por surplus mensual).
            # Bajo CREG 174 esta energía se factura completa al pi_gs (incluye C).
            grid_cost_m = max(0.0, E_deficit - E_surplus) * pi_gs_period

            # C-165: el mismo dinero, repartido a la hora que lo genera.
            neto_horario[n, hours] = (auto_h * pi_gs_period
                                      + surplus_t1 * pi_eff_t1
                                      + surplus_t2 * pb_h)

            savings_n     += savings_m
            surplus_n     += revenue_m
            grid_cost_n   += grid_cost_m
            e_permuted_n  += E_permuted_1
            e_tipo2_n     += E_tipo2
            e_auto_n      += E_auto

        # CAL-46: de potencia a energía. Las matrices llevan potencia media
        # del paso (kW) y los precios COP/kWh, de modo que tanto el dinero
        # como las energías de diagnóstico se multiplican por la duración.
        # La búsqueda de la hora de cruce es homogénea y no se toca.
        if dt != 1.0:
            neto_horario[n, :] *= dt
            savings_n *= dt
            surplus_n *= dt
            grid_cost_n *= dt
            e_auto_n *= dt
            e_permuted_n *= dt
            e_tipo2_n *= dt

        results[n] = {
            "savings":         savings_n,
            "surplus_revenue": surplus_n,
            "grid_cost":       grid_cost_n,
            "net_benefit":     savings_n + surplus_n,
            # Métricas CAL-10 para diagnóstico / monthly_report
            "E_auto":          e_auto_n,
            "E_permuted_t1":   e_permuted_n,
            "E_tipo2":         e_tipo2_n,
            "hx_history":      hx_history_n,
        }

        total_savings         += savings_n
        total_surplus_revenue += surplus_n
        total_grid_cost       += grid_cost_n
        total_e_permuted_t1   += e_permuted_n
        total_e_tipo2         += e_tipo2_n
        total_e_auto          += e_auto_n

    results["aggregate"] = {
        "total_savings":         total_savings,
        "total_surplus_revenue": total_surplus_revenue,
        "total_grid_cost":       total_grid_cost,
        "total_net_benefit":     total_savings + total_surplus_revenue,
        # CAL-10
        "total_E_auto":          total_e_auto,
        "total_E_permuted_t1":   total_e_permuted_t1,
        "total_E_tipo2":         total_e_tipo2,
    }
    # C-165: matriz (N, T) del beneficio a la hora que lo genera. Su suma por
    # filas es el beneficio neto por agente, al ultimo digito.
    results["neto_horario"] = neto_horario

    return results


def net_economic_gain_c1(results: dict, agent_ids: list) -> np.ndarray:
    """Extrae ganancia económica neta por agente como vector."""
    return np.array([results[n]["net_benefit"] for n in agent_ids])
