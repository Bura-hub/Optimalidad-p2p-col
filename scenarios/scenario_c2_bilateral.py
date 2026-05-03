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
    # CAL-16: descomposición regulatoria explícita del ahorro
    g_component:   Union[float, np.ndarray, None] = None,  # G CREG 119
    cvm_component: Union[float, np.ndarray, None] = None,  # Cvm CREG 119
    cot_component: Union[float, np.ndarray, None] = None,  # COT CREG 101-028
    mem_costs:     Union[float, np.ndarray, None] = None,  # FAZNI+4%+rep
    cot_alpha:     float = 1.0,                            # peso COT [0,1]
    # CAL-23 (ADR-0023): CXC opt-in. Default 0.0 = cota conservadora
    # (usuario sigue pagando CXC bajo PPA, interpretacion industrial).
    cxc_component: Union[float, np.ndarray, None] = None,  # CXC CREG 071/2006
    cxc_alpha:     float = 0.0,                            # peso CXC [0,1]
    # Compatibilidad pre-CAL-16: si solo se pasa pi_G se trata como G+Cvm+COT
    pi_G: Union[float, np.ndarray, None] = None,
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

    # ── CAL-16: selección de modo según parámetros recibidos ─────────────
    # Modo CAL-16 (descompuesto): se proporciona g_component → se usan
    #     los cuatro componentes regulatorios (G, Cvm, α·COT, MEM).
    # Modo CAL-13 (agregado, retro-compatible): solo pi_G → se trata como
    #     "G + Cvm + COT" agregado en savings_G; Cvm, COT, MEM = 0.
    # Modo BTM legacy (pre-CAL-12): ningún parámetro → pi_G = pi_gs.
    use_decomp = g_component is not None
    if use_decomp:
        g_v   = as_pi_gs_array(g_component, N, T)
        cvm_v = (as_pi_gs_array(cvm_component, N, T)
                 if cvm_component is not None else np.zeros((N, T)))
        cot_v = (as_pi_gs_array(cot_component, N, T)
                 if cot_component is not None else np.zeros((N, T)))
        mem_v = (as_pi_gs_array(mem_costs, N, T)
                 if mem_costs is not None else np.zeros((N, T)))
    elif pi_G is not None:
        g_v   = as_pi_gs_array(pi_G, N, T)                     # CAL-13
        cvm_v = np.zeros((N, T))
        cot_v = np.zeros((N, T))
        mem_v = np.zeros((N, T))
    else:
        g_v   = pi_gs_v                                        # legacy BTM
        cvm_v = np.zeros((N, T))
        cot_v = np.zeros((N, T))
        mem_v = np.zeros((N, T))

    # CAL-23: CXC opt-in (default cero si no se pasa).
    cxc_v = (as_pi_gs_array(cxc_component, N, T)
             if cxc_component is not None else np.zeros((N, T)))

    savings_gen   = np.zeros(N)    # autoconsumo + ingreso PPA del prosumidor
    savings_G     = np.zeros(N)    # ahorro componente G (Ley 143/1994)
    savings_Cvm   = np.zeros(N)    # ahorro Cvm (CREG 086/1996)
    savings_COT   = np.zeros(N)    # ahorro α·COT (CREG 101-028/2023)
    savings_CXC   = np.zeros(N)    # ahorro α·CXC (CAL-23, opt-in)
    mem_costs_arr = np.zeros(N)    # egresos MEM no-regulado (FAZNI+4%+rep)
    grid_cost     = np.zeros(N)    # costo energía aún comprada a red
    grid_revenue  = np.zeros(N)    # ingresos por venta excedente a red

    for k in range(T):
        gen_surplus = np.maximum(G[:, k] - D[:, k], 0.0)
        deficits    = np.maximum(D[:, k] - G[:, k], 0.0)
        total_surplus = float(np.sum(gen_surplus[prosumer_ids]))

        # Autoconsumo: ahorra CU completo (BTM)
        for n in prosumer_ids:
            autoconsumo = min(G[n, k], D[n, k])
            savings_gen[n] += autoconsumo * pi_gs_v[n, k]

        # Distribución PPA proporcional a la demanda
        dem_cons = np.array([D[i, k] for i in consumer_ids])
        total_dem_cons = float(np.sum(dem_cons))

        if total_dem_cons > 0 and total_surplus > 0:
            share = dem_cons / total_dem_cons
            ppa_delivered = np.minimum(share * total_surplus, dem_cons)

            for idx, i in enumerate(consumer_ids):
                e = ppa_delivered[idx]
                # CAL-16: ahorro descompuesto por componente regulatorio
                savings_G[i]     += e * (g_v[i, k] - pi_ppa)
                savings_Cvm[i]   += e *  cvm_v[i, k]
                savings_COT[i]   += e *  cot_v[i, k] * cot_alpha
                # CAL-23: CXC parametrizable (default 0.0 = cota conservadora)
                savings_CXC[i]   += e *  cxc_v[i, k] * cxc_alpha
                mem_costs_arr[i] += e *  mem_v[i, k]
                # Déficit residual → red al CU completo
                residual = max(0.0, deficits[i] - e)
                grid_cost[i] += residual * pi_gs_v[i, k]

            # Ingresos PPA del prosumidor
            for n in prosumer_ids:
                frac = (gen_surplus[n] / total_surplus
                        if total_surplus > 0 else 0.0)
                ppa_sold = frac * float(np.sum(ppa_delivered))
                savings_gen[n]  += ppa_sold * pi_ppa
                grid_revenue[n] += max(0.0,
                                        gen_surplus[n] - ppa_sold) * pi_gb
        else:
            for n in prosumer_ids:
                grid_revenue[n] += gen_surplus[n] * pi_gb
            for i in consumer_ids:
                grid_cost[i] += deficits[i] * pi_gs_v[i, k]

    # CAL-16: savings_ppa es la suma neta descompuesta. CAL-23 agrega CXC.
    savings_ppa = (savings_G + savings_Cvm + savings_COT + savings_CXC
                    - mem_costs_arr)
    net_benefit = savings_gen + savings_ppa + grid_revenue

    results_per_agent = {
        n: {
            "savings_autoconsumo": float(savings_gen[n]),
            "savings_G":           float(savings_G[n]),
            "savings_Cvm":         float(savings_Cvm[n]),
            "savings_COT":         float(savings_COT[n]),
            "savings_CXC":         float(savings_CXC[n]),
            "mem_costs":           float(mem_costs_arr[n]),
            "savings_ppa":         float(savings_ppa[n]),
            # Compatibilidad: savings_cons era el agregado pre-CAL-16
            "savings_cons":        float(savings_ppa[n]),
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
            "total_net_benefit":  float(np.sum(net_benefit)),
            "total_savings_gen":  float(np.sum(savings_gen)),
            "total_savings_G":    float(np.sum(savings_G)),
            "total_savings_Cvm":  float(np.sum(savings_Cvm)),
            "total_savings_COT":  float(np.sum(savings_COT)),
            "total_savings_CXC":  float(np.sum(savings_CXC)),
            "total_mem_costs":    float(np.sum(mem_costs_arr)),
            "total_savings_ppa":  float(np.sum(savings_ppa)),
            # Compat
            "total_savings_cons": float(np.sum(savings_ppa)),
            "total_grid_revenue": float(np.sum(grid_revenue)),
            "total_grid_cost":    float(np.sum(grid_cost)),
        },
        "params": {
            "pi_ppa":     pi_ppa,
            "pi_gb":      pi_gb,
            "cot_alpha":  cot_alpha,
            "cxc_alpha":  cxc_alpha,
            "pi_gs":      pi_gs_v.mean(axis=1).tolist(),
            "G_mean":     g_v.mean(axis=1).tolist(),
            "Cvm_mean":   cvm_v.mean(axis=1).tolist(),
            "COT_mean":   cot_v.mean(axis=1).tolist(),
            "MEM_mean":   mem_v.mean(axis=1).tolist(),
            # Compat: pi_G era el agregado CAL-13 (G+Cvm+COT)
            "pi_G":       (g_v + cvm_v + cot_v).mean(axis=1).tolist(),
        },
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
