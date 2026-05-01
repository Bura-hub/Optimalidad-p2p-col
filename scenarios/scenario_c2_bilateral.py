"""
scenario_c2_bilateral.py
------------------------
Escenario C2: Contratos bilaterales (Power Purchase Agreement — PPA).

Mecanismo: precio fijo pactado a largo plazo entre un AGPE prosumidor
y la **comunidad MTE constituida como usuario no-regulado agregado**
(CAL-13, 2026-05-01).

ALCANCE FORMAL CAL-13 (2026-05-01) — comunidad como usuario no-regulado
=======================================================================

Bajo Ley 143/1994 art. 41 + Decreto 388/2007 + CREG 086/1996 art. 1
mod. 039/2001, las 5 instituciones MTE constituidas como persona
jurídica común (asociación, cooperativa o comunidad energética con
demanda agregada ≥ 55 MWh/mes o potencia conectada ≥ 100 kW)
califican como **usuario no-regulado** y pueden firmar contratos
bilaterales a precio libre con AGPE FNCER miembros bajo CREG 174/2021
art. 23 num. 1.a.

Bajo Res. CREG 119/2007 (arts. 6-14) el Costo Unitario CU se descompone:

    CU = G + T + D + Cvm + PR + Rm + COT

- G es negociable vía contrato bilateral (arts. 6-8).
- T+D+PR+Rm son cargos regulados al OR/STN: cualquier usuario
  (regulado o no) los paga obligatoriamente.
- **Cvm + COT son margen del comercializador minorista**: un usuario
  no-regulado NO los paga (no tiene comercializador minorista; contrata
  directamente con el generador a través de un representante del MEM).

Por tanto, bajo CAL-13 el ahorro del comprador no-regulado vía PPA es:

    savings_cons = E_PPA × ((G + Cvm + COT) − pi_ppa)        [CAL-13]

donde (G + Cvm + COT) es el "rango negociable + ahorro de
comercialización". Esta es una cota intermedia entre:

    BTM legacy pre-CAL-12:  (CU − pi_ppa)                  [incorrecto]
    FoM regulado CAL-12:    (G − pi_ppa)                   [correcto si comprador queda regulado]
    FoM no-regulado CAL-13: ((G + Cvm + COT) − pi_ppa)    [correcto bajo Opción A]

Datos del rango negociable + comercialización (G + Cvm + COT):
    `data/cedenar_tariff.g_plus_commercialization_per_agent_hourly(
       agents, idx)` → matriz (N, T) constante dentro del mes,
    transcrita de los PDFs `data/cedenar_pdfs/tarifa_*.pdf`.

Ejemplo abr-2026 oficial NT2 (Udenar/HUDN):
    CU = 799,16 ; G = 310,96 ; Cvm + COT = 215,14
    G + Cvm + COT = 526,10 ; peajes T+D+PR+Rm = 273,06 COP/kWh

ALCANCE FORMAL CAL-11 (2026-04-30) — modalidad y sustento
=========================================================

  - Tipo: PPA físico Pay-as-Produced (escalar fijo en horizonte).
  - Sustento empírico: subastas UPME CLPE 02-2019, CLPE 03-2021, 2024;
    contratos bilaterales mayoristas XM 2023-2024
    (cf. `scripts/audit_xm_yearly_means.py`,
    `data/audit_xm_yearly_summary.csv`).
  - Sustento normativo del default `f=0,5`: postulado de reparto
    simétrico ENTRE `pi_gb` y (G + Cvm + COT) (CAL-13); el bienestar
    agregado es invariante en `f` (teorema notas §3.8).
  - Brechas declaradas out-of-scope: variante CFD/financiera, perfil
    Baseload, plazo contractual, precios diferenciados por agente.

NOTA — parámetro `pi_G` del módulo
==================================

El parámetro de entrada se llama `pi_G` por razones históricas
(CAL-12 introdujo el componente G). Bajo CAL-13 representa el
**rango negociable + ahorro de comercialización** (G + Cvm + COT
para no-regulado), no solo G. La firma se preserva por
compatibilidad con tests CAL-11/CAL-12 y `pi_G=None` cae al
comportamiento BTM legacy.

Ver:
  - docs/adr/0011-cal11-c2-ppa-bilateral-modelo-formal.md
  - docs/adr/0012-cal12-c2-fom-peajes.md
  - docs/adr/0013-cal13-c2-no-regulado.md
  - docs/superpowers/specs/2026-05-01-c1-c2-regulatory-alignment-audit.md
  - tests/test_c2_bilateral.py
"""

from typing import Union

import numpy as np

from ._pi_gs import as_pi_gs_array


def run_c2_bilateral(
    D: np.ndarray,             # (N, T) demanda [kWh]
    G: np.ndarray,             # (N, T) generación bruta [kWh]
    pi_gs: Union[float, np.ndarray],  # escalar, (N,) o (N, T) — CAL-9
    pi_gb: float,              # precio de venta excedente a red $/kWh
    pi_ppa: float,             # precio PPA pactado $/kWh
    prosumer_ids: list,        # índices de agentes con generación
    consumer_ids: list,        # índices de consumidores puros
    pi_G: Union[float, np.ndarray, None] = None,  # componente G — CAL-12
) -> dict:
    """
    Lógica:
      1. Cada prosumidor autoconsume primero (energía detrás del medidor:
         no toca la red → ahorra el CU completo `pi_gs`).
      2. El excedente se vende a precio `pi_ppa` a los consumidores del
         contrato. Reparto: proporcional a la demanda de cada consumidor.
      3. El consumidor regulado paga `pi_ppa` por la energía vía PPA y
         SIGUE pagando los peajes T+D+Cvm+PR+Rm+COT al OR/STN. Su ahorro
         real frente a comprar 100 % red es `(G − pi_ppa)` por kWh
         (CAL-12). Si `pi_ppa > G`, el comprador PIERDE dinero al
         contratar — ése es el filtro económico que descarta π_ppa
         arbitrarios.
      4. El déficit residual se cubre con red a `pi_gs[n, k]` (CU
         completo, peajes incluidos).
      5. Si queda excedente del prosumidor sin colocar vía PPA, va a
         red a `pi_gb`.

    Parámetro `pi_G`:
        Componente G (Generación) del CU, único negociable vía PPA.
        Acepta float, (N,), (T,) o (N, T). Si es None (legacy
        pre-CAL-12), se asume `pi_G == pi_gs` y la función reproduce el
        comportamiento BTM antiguo, conservado solo por compatibilidad
        con tests/análisis previos. PRODUCCIÓN (`main_simulation.py`)
        DEBE pasar la matriz real obtenida de
        `data.cedenar_tariff.g_component_per_agent_hourly`.

    Filosofía A (WEEF min 22-26):
        net_benefit = savings_autoconsumo + savings_ppa + grid_revenue
        (no se resta el grid_cost residual por la energía aún
        comprada a red; ese costo se incurriría igual sin PPA).

    Ref: CREG 119/2007 arts. 6-14; ADR-0011, ADR-0012.
    """
    N, T = D.shape
    pi_gs_v = as_pi_gs_array(pi_gs, N, T)                     # (N, T) CAL-9
    if pi_G is None:
        # Legacy pre-CAL-12: BTM puro (pi_G == pi_gs). Conservado solo
        # como compatibilidad para tests previos; producción debe pasar
        # la matriz real.
        pi_G_v = pi_gs_v
    else:
        pi_G_v = as_pi_gs_array(pi_G, N, T)                   # (N, T) CAL-12

    savings_gen  = np.zeros(N)    # ahorro autoconsumo + ingreso PPA
    savings_cons = np.zeros(N)    # ahorro PPA del comprador (sobre G)
    grid_cost    = np.zeros(N)    # costo energía aún comprada a red
    grid_revenue = np.zeros(N)    # ingresos por venta excedente a red

    for k in range(T):
        # Excedentes netos de prosumidores
        gen_surplus = np.maximum(G[:, k] - D[:, k], 0.0)
        # Déficit de todos los agentes (antes de contrato)
        deficits    = np.maximum(D[:, k] - G[:, k], 0.0)

        total_surplus = float(np.sum(gen_surplus[prosumer_ids]))

        # Autoconsumo: ahorro de cada prosumidor (energía detrás del
        # medidor → ahorra CU completo).
        for n in prosumer_ids:
            autoconsumo = min(G[n, k], D[n, k])
            savings_gen[n] += autoconsumo * pi_gs_v[n, k]

        # Distribución del excedente a consumidores (proporcional a demanda)
        dem_cons = np.array([D[i, k] for i in consumer_ids])
        total_dem_cons = float(np.sum(dem_cons))

        if total_dem_cons > 0 and total_surplus > 0:
            share = dem_cons / total_dem_cons
            ppa_delivered = np.minimum(share * total_surplus, dem_cons)

            for idx, i in enumerate(consumer_ids):
                # CAL-12: ahorro PPA solo sobre componente G del CU.
                # Los peajes T+D+Cvm+PR+Rm+COT se siguen pagando al
                # OR/STN sobre la energía recibida vía PPA (pero NO se
                # contabilizan aquí por filosofía A: solo se contabilizan
                # AHORROS o INGRESOS, no costos de la contraparte).
                savings_cons[i] += ppa_delivered[idx] * (pi_G_v[i, k] - pi_ppa)
                # Déficit residual → red a la tarifa CU completa
                # (peajes incluidos sobre la energía de red).
                residual = max(0.0, deficits[i] - ppa_delivered[idx])
                grid_cost[i] += residual * pi_gs_v[i, k]

            # Ingresos PPA del prosumidor
            for n in prosumer_ids:
                frac = gen_surplus[n] / total_surplus if total_surplus > 0 else 0.0
                ppa_sold = frac * float(np.sum(ppa_delivered))
                savings_gen[n] += ppa_sold * pi_ppa
                # Excedente que no se vendió por PPA → red a pi_gb
                grid_revenue[n] += max(0.0, gen_surplus[n] - ppa_sold) * pi_gb
        else:
            # Sin PPA posible: todo va a red
            for n in prosumer_ids:
                grid_revenue[n] += gen_surplus[n] * pi_gb
            for i in consumer_ids:
                grid_cost[i] += deficits[i] * pi_gs_v[i, k]

    net_benefit = savings_gen + savings_cons + grid_revenue

    results_per_agent = {
        n: {
            "savings_autoconsumo": float(savings_gen[n]),
            "savings_ppa":         float(savings_cons[n]),
            "grid_revenue":        float(grid_revenue[n]),
            "grid_cost":           float(grid_cost[n]),
            "net_benefit":         float(net_benefit[n]),
            "pi_ppa":              pi_ppa,
        }
        for n in range(N)
    }

    return {
        "per_agent": results_per_agent,
        "aggregate": {
            "total_net_benefit":     float(np.sum(net_benefit)),
            "total_savings_gen":     float(np.sum(savings_gen)),
            "total_savings_cons":    float(np.sum(savings_cons)),
            "total_grid_revenue":    float(np.sum(grid_revenue)),
            "total_grid_cost":       float(np.sum(grid_cost)),
        },
        "params": {"pi_ppa": pi_ppa,
                    "pi_gs": pi_gs_v.mean(axis=1).tolist(),
                    "pi_G":  pi_G_v.mean(axis=1).tolist(),
                    "pi_gb": pi_gb},
    }


def ppa_price_range(pi_gb: float, pi_upper: float,
                    factors: list = None) -> list:
    """
    Genera un rango de precios PPA para análisis de sensibilidad.

    CAL-12: el rango natural es ahora [pi_gb, G] (no [pi_gb, CU]),
    porque G es el componente único negociable vía PPA. Para retro-
    compatibilidad, esta función acepta cualquier valor superior
    `pi_upper` — ahí donde antes se pasaba `pi_gs`, en producción
    pos-CAL-12 se pasa `G_efectivo`.

    Por defecto: 25 %, 50 %, 75 % del rango [pi_gb, pi_upper].
    """
    if factors is None:
        factors = [0.25, 0.50, 0.75]
    return [pi_gb + f * (pi_upper - pi_gb) for f in factors]
