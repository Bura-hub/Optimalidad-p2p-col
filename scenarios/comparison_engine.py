"""
comparison_engine.py  (v2 — sin DR)
------------------------------------
Motor de comparación cuantitativa del Objetivo 3 de la tesis.

La demanda D es un insumo fijo (datos reales de la comunidad).
Todos los escenarios C1–C4 y el P2P operan sobre los mismos
perfiles D y G_klim, garantizando comparación equitativa.

Dos niveles de métricas (propuesta tesis):
  Nivel 1 — Monetario: ganancias económicas netas
  Nivel 2 — Bienestar: IE, Price of Fairness, SC, SS, autosuficiencia
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Union

from ._pi_gs import as_pi_gs_array, as_component_c_array
from core.opciones_externas import (deduccion_art25, precio_permuta_por_periodo,
                                    reparto_anexo4)
from .scenario_c1_creg174    import run_c1_creg174
from .scenario_c2_bilateral  import run_c2_bilateral
from .scenario_c3_spot       import run_c3_spot
from .scenario_c4_creg101072 import (
    run_c4_creg101072, compute_pde_weights, static_spread_c4_vs_p2p,
    pde_por_regla,
)
from core.settlement import gini_index, compute_net_benefit
from analysis.fairness import FairnessResult, compute_pof, print_pof_report


@dataclass
class ComparisonResult:
    net_benefit:           dict  = field(default_factory=dict)
    net_benefit_per_agent: dict  = field(default_factory=dict)
    equity_index:          dict  = field(default_factory=dict)
    gini:                  dict  = field(default_factory=dict)   # Índice de Gini por escenario
    self_sufficiency:      dict  = field(default_factory=dict)
    self_consumption:      dict  = field(default_factory=dict)
    rpe:                   Optional[float]      = None
    # RPE = (W_P2P - W_C4) / |W_P2P|: rendimiento relativo frente al escenario
    # colectivo regulatorio (C4). Positivo = P2P supera a C4; negativo = al revés.
    # RPE ≠ PoF de Bertsimas (2011). Ver fairness.py para el PoF formal.
    fairness:              Optional[FairnessResult] = None
    # PoF = (W_eff - W_fair) / W_eff — Bertsimas, Farias & Trichakis (2011).
    # W_eff = beneficio total del escenario más eficiente (max Σ B_n).
    # W_fair = beneficio total del escenario más equitativo (min Gini).
    static_spread_24h:     Optional[np.ndarray] = None
    hours:     int   = 24
    n_agents:  int   = 6
    pi_ppa:    float = 0.0
    pde:       Optional[np.ndarray] = None
    # Distribución del excedente P2P (solo aplica al escenario P2P)
    # PS  = (Σ S_i)  / (Σ S_i + Σ SR_j) × 100  → fracción capturada por compradores
    # PSR = (Σ SR_j) / (Σ S_i + Σ SR_j) × 100  → fracción capturada por vendedores
    # Ref: Tabla VII modelo base Sofía Chacón (2025)
    ps_p2p:    float = 50.0   # % excedente P2P hacia compradores
    psr_p2p:   float = 50.0   # % excedente P2P hacia vendedores
    # Desglose de flujos por componente (Activity 3.2 — Nivel 1)
    # {escenario: {componente: COP_total}}
    flow_breakdown: dict = field(default_factory=dict)
    # ── Descomposición del bienestar P2P (Act 3.3) ──────────────────────
    # Nivel 1: beneficio monetario directo (COP)  → net_benefit["P2P"]
    # Nivel 2: bienestar de optimización (u.o.)   → W_sellers + W_buyers
    #
    # W_j = lam_j×G_j - theta_j×G_j² - Σ_i P_ji/log(1+π_i) - a_j×ΣP² - b_j×ΣP
    # W_i = lam_i×G_i - theta_i×G_i² + Σ_j P_ji/log(|π_i|+1) - etha_i×compe
    #
    # Nota: W_j y W_i están en unidades de optimización (u.o.): son los valores
    # de las funciones objetivo que guían la dinámica de replicador, e incluyen
    # utilidad de autoconsumo (preferencias λ, θ) y aversión al riesgo (η).
    # NO son directamente comparables en COP, pero cuantifican los beneficios
    # intangibles del mecanismo P2P más allá de los flujos de caja.
    W_sellers_total: float = 0.0   # Σ_k W_j(k) sobre todas las horas activas
    W_buyers_total:  float = 0.0   # Σ_k W_i(k) sobre todas las horas activas
    # ── El detalle propio del contrato interno (CAL-52) ─────────────────
    #
    # POR QUE VIAJA APARTE Y NO EN LA COLUMNA DE EQUIDAD. El contrato reparte
    # la banda a la mitad, de modo que el ahorro del comprador y la prima del
    # vendedor son iguales y su indice de reparto vale **cero exacto**. Pero la
    # columna de equidad de la tabla mide otra cosa: agrega el beneficio de
    # cada agente, lo parte en dos grupos por su cobertura solar, y compara los
    # grupos. Escribir el cero del contrato en esa columna dejaria una celda
    # que no significa lo mismo que sus vecinas, que es justamente el defecto
    # que la ficha de los escenarios ya tiene anotado.
    #
    # De modo que la columna se queda uniforme y la propiedad del contrato se
    # reporta aqui, donde puede comprobarse sin contaminar la comparacion.
    contrato_c2: dict = field(default_factory=dict)
    # ── El desglose por hora y agente de cada mecanismo (C-165) ─────────
    #
    # {escenario: matriz (N, T)} con el beneficio anotado en la hora que lo
    # genera. Es lo que permite decir en QUE meses y en QUE horas cada
    # mecanismo reparte mejor, que hasta ahora solo existia agregado al
    # horizonte entero.
    #
    # Desde C-178 estan todos: el colectivo mensual anota su credito a la
    # tarifa media del mes y su exceso a la bolsa de su hora, igual que C1.
    #
    # La compuerta comprueba que cada matriz suma por filas EXACTAMENTE el
    # beneficio por agente que este mismo motor reporta.
    neto_horario: dict = field(default_factory=dict)
    # ── Contrafacticos del colectivo (spec 4.6, D5) ──────────────────────
    # El mismo colectivo mensual con otra regla de porcentaje, o en el caso
    # favorable del art. 20 como si hubiera 11 fronteras, y el mercado por la
    # via del colectivo en ese mismo caso (I-4). No son columnas de la
    # tabla: miden cuanto pesa cada supuesto. {nombre: {"total",
    # "por_agente", "caso_art20"}}.
    contrafacticos: dict = field(default_factory=dict)
    # ── El factor de coincidencia (D20) ─────────────────────────────────
    # {escenario: [0, 1]}: de lo que cada mecanismo acredita como si
    # sustituyera importacion, que fraccion coincidio en la hora con esa
    # importacion (analysis/coincidencia.py). C3 no acredita: NaN.
    coincidencia: dict = field(default_factory=dict)
    # El pico de importacion neta de la comunidad entre la suma de los picos
    # de cada miembro. Es de la comunidad, no del mecanismo.
    simultaneidad: Optional[float] = None


def run_comparison(
    D:            np.ndarray,       # (N, T) demanda real FIJA
    G_klim:       np.ndarray,       # (N, T) límite de generación (pre-calc.)
    G_raw:        np.ndarray,       # (N, T) generación bruta original
    p2p_results:  list,
    pi_gs:        Union[float, np.ndarray],  # escalar, (N,) o (N, T) — CAL-9
    pi_gb:        float,
    pi_bolsa:     np.ndarray,       # (T,) precio de bolsa horario
    prosumer_ids: list,
    consumer_ids: list,
    pde:          Optional[np.ndarray] = None,
    pi_ppa:       Optional[float]      = None,
    capacity:     Optional[np.ndarray] = None,
    month_labels: Optional[np.ndarray] = None,  # (T,) etiqueta de período (YYYYMM)
    component_c:  Union[str, float, np.ndarray] = "auto",  # CAL-10b
    tolls:        Union[float, np.ndarray, None] = None,   # CAL-41: T+D+PR+Rm de C4
    pi_G:         Union[float, np.ndarray, None] = None,   # CAL-13 (agregado)
    # CAL-16: descomposición regulatoria explícita del ahorro en C2
    g_component:   Union[float, np.ndarray, None] = None,
    cvm_component: Union[float, np.ndarray, None] = None,
    cot_component: Union[float, np.ndarray, None] = None,
    mem_costs:     Union[float, np.ndarray, None] = None,
    cot_alpha:     float = 1.0,
    # ── CAL-37 (ADR-0037): escenario C5 AGR (CREG 101 099/2026) ─────────
    # Default OFF: el paper no usa run_comparison, pero el OFF garantiza
    # que ningún caller existente cambie de comportamiento.
    include_c5:    bool = False,
    pi_escasez:    Optional[np.ndarray] = None,   # (T,) PES mensual→horario
    f_split_c5:    float = 0.5,
    # ── CAL-46 (ADR-0046): duración del paso en horas ───────────────────
    # D, G_klim y G_raw llevan potencia media del paso (kW) y los precios
    # COP/kWh, de modo que la energía del paso es potencia por `dt`. Antes de
    # CAL-46 el factor estaba implícito en 1 hora y no se escribía en ninguna
    # parte. El default 1.0 deja el camino horario idéntico bit a bit.
    dt:            float = 1.0,
    # CAL-51: precio pactado del contrato bilateral, (T,) o escalar.
    # Con None se conserva el comportamiento anterior bit a bit.
    pi_contrato:  Union[float, np.ndarray, None] = None,
    # CAL-52: el piso de cada vendedor, matriz (N, T). Lo necesita el
    # contrato interno para su punto medio. Con None, C2 se comporta como
    # antes.
    piso_agente:  Union[np.ndarray, None] = None,
    cobertura_contrato: float = 1.0,
    # C-179: precio del contrato de la autogeneracion remota, (T,), de la
    # serie de XM del mercado no regulado; y el CERE del art. 18, (T,).
    pi_contrato_c5: Union[float, np.ndarray, None] = None,
    cere_c5:        Union[float, np.ndarray, None] = None,
) -> ComparisonResult:
    """
    Todos los escenarios operan sobre D (real, fijo) y G_klim.

    `pi_gs` admite escalar (caso uniforme), vector `(N,)` per-agente
    (CAL-8) o matriz `(N, T)` mes a mes (CAL-9, calibración Cedenar
    temporal). Internamente se propaga como matriz `(N, T)` para que
    cada hora liquide con el CU vigente en su mes.

    `pi_G` (CAL-12 → CAL-13, ADR-0012/0013): rango negociable del CU
    para el contrato bilateral. Bajo CAL-12 representaba solo G (caso
    consumidor regulado). Bajo CAL-13 representa **G + Cvm + COT** (caso
    comunidad MTE como usuario no-regulado agregado bajo Ley 143/1994 +
    CREG 086/1996 + CREG 174/2021 art. 23 num. 2 lit. a). El parámetro mantiene
    su nombre histórico `pi_G` por compatibilidad. Acepta float, `(N,)`,
    `(T,)` o `(N, T)` — análogo a `pi_gs`. Si None y no se proveen los
    componentes descompuestos (CAL-16), C2 cae al comportamiento BTM
    legacy (`pi_G == pi_gs`).

    `g_component`, `cvm_component`, `cot_component`, `mem_costs`,
    `cot_alpha` (CAL-16, ADR-0016): descomposición regulatoria explícita
    del ahorro de C2. Cuando se proveen, C2 calcula

        savings_ppa = E_PPA × [(G − π_ppa) + Cvm + α·COT − MEM]

    donde:
      - `g_component`   → G   (Ley 143/1994 art. 41, único negociable)
      - `cvm_component` → Cvm (CREG 086/1996, ahorrado por no-regulado)
      - `cot_component` → COT (CREG 101-028/2023, peso α ∈ [0, 1])
      - `mem_costs`     → MEM = FAZNI + 0.04·G + π_rep
                         (Ley 1715/2014 + Ley 1117/2006 + Ley 2099/2021
                          + CREG 156/2012)
      - `cot_alpha` default 1.0 mantiene cota CAL-13; 0.0 cota más
        conservadora.

    En producción (`main_simulation.py --data real`) se construyen
    estos componentes con `data.cedenar_tariff.cu_components_per_agent_hourly`
    y `mem_costs_per_agent_hourly`. La modalidad CAL-16 tiene
    precedencia sobre `pi_G`. Si ninguno se provee, C2 cae al
    comportamiento BTM legacy.

    El default de `pi_ppa` (cuando es None) usa el rango negociable
    como cota superior. Bajo CAL-16, `pi_upper = G + Cvm + α·COT − MEM`
    (cota económicamente racional donde el comprador deja de ganar).
    """
    N, T = D.shape
    cr   = ComparisonResult(hours=T, n_agents=N)

    # Normalizar pi_gs a matriz (N, T) — CAL-9: tarifa temporal mes a mes.
    pi_gs_v = as_pi_gs_array(pi_gs, N, T)

    # C-177: lo que el comercializador cobra sobre cada kWh permutado, por
    # agente y hora, con el numeral del art. 25 que decide la capacidad
    # instalada. La usan el residual del mercado, el del contrato interno y
    # el mercado por la via del colectivo.
    tolls_v = (None if tolls is None
               else as_component_c_array(tolls, pi_gs_v, N, T,
                                         rellena_nan=False))
    ded_v = deduccion_art25(as_component_c_array(component_c, pi_gs_v, N, T),
                            tolls_v, capacity)

    # CAL-12: normalizar pi_G a matriz (N, T) o caer a BTM legacy.
    if pi_G is None:
        pi_G_v = pi_gs_v          # Comportamiento BTM legacy pre-CAL-12.
    else:
        pi_G_v = as_pi_gs_array(pi_G, N, T)

    # Valores por defecto
    if pde is None:
        # D5: la base es el reparto igual. Con placas identicas coincide con
        # la capacidad; la generacion media medida era lo que el rotulo viejo
        # llamaba capacidad (H-71).
        pde = compute_pde_weights(np.ones(N), method="equal")
    cr.pde = pde

    if pi_ppa is None:
        # CAL-12: rango natural del PPA es [pi_gb, G], no [pi_gb, CU].
        # Default f=0.5 = punto medio entre venta a red y componente G.
        pi_ppa = pi_gb + 0.5 * (float(np.mean(pi_G_v)) - pi_gb)
    cr.pi_ppa = pi_ppa

    # Todos los escenarios usan Filosofía A: net_benefit = savings + revenues.
    # No se resta la factura residual a la red (validado por asesor Pantoja,
    # Documentos/conversacion_WEEF.txt min 22-26).

    # ── C1 ──────────────────────────────────────────────────────────────
    # month_labels habilita el balance mensual real de CREG 174 (permutación).
    # Si None (perfil 24h o sintético), todo el horizonte es un único período.
    # component_c="auto" (CAL-10) descuenta proporcional 13.85 %; matriz (N, T)
    # de cvm_per_agent_hourly (CAL-10b.2) usa Cvm,i,j puro de CREG 119/2007
    # desde CSV Cedenar (literalidad CREG 174 art. 25, sin COT).
    # Excedentes a bolsa horaria post-cruce mensual (jerga industria: "Tipo 2"
    # post-"Hora Hx", aunque CREG no nombra esos términos formalmente).
    # Ver scenarios/scenario_c1_creg174.py y data/cedenar_tariff.py.
    c1 = run_c1_creg174(D, G_klim, pi_gs_v, pi_bolsa, prosumer_ids,
                        month_labels=month_labels,
                        component_c=component_c, dt=dt,
                        capacidad_kw=capacity, tolls=tolls)
    c1_net = np.array([c1[n]["net_benefit"] if n in c1 else 0.0
                       for n in range(N)])
    cr.net_benefit["C1"]           = float(np.sum(c1_net))
    cr.neto_horario["C1"] = c1.get("neto_horario")          # C-165
    cr.net_benefit_per_agent["C1"] = c1_net

    # ── C2 ──────────────────────────────────────────────────────────────
    # CAL-12 → CAL-13 → CAL-16 (ADR-0012/0013/0016).
    # Si se proporciona la descomposición explícita (g_component, etc.),
    # C2 calcula:  savings_ppa = savings_G + savings_Cvm + α·savings_COT
    #              − mem_costs   (CAL-16)
    # Si solo llega pi_G (modo CAL-13 agregado), se preserva el
    # comportamiento anterior. Si ninguno, modo BTM legacy pre-CAL-12.
    c2 = run_c2_bilateral(
        D, G_klim, pi_gs_v, pi_gb, pi_ppa,
        prosumer_ids, consumer_ids,
        # CAL-16
        g_component=g_component,
        cvm_component=cvm_component,
        cot_component=cot_component,
        mem_costs=mem_costs,
        cot_alpha=cot_alpha,
        # CAL-13 retro-compatibilidad
        pi_G=pi_G_v,
        # CAL-37: excedente no colocado a bolsa HORARIA (fix artefacto §7.5)
        pi_bolsa=pi_bolsa,
        # CAL-51: el precio pactado del contrato, articulo 23 numeral 2
        # literal a. Sin el, este escenario valoraba su excedente a la bolsa
        # y coincidia con C3 al ultimo digito.
        pi_contrato=pi_contrato,
        cobertura_contrato=cobertura_contrato,
        dt=dt,
    )
    # ── CAL-52: el contrato bilateral INTERNO ────────────────────────────
    #
    # Los mismos flujos que el mercado entre pares, pero a un precio PACTADO
    # en el punto medio de la banda de cada pareja en vez de negociado. Es lo
    # que un contrato de suministro hace: fijar el precio y quitar la
    # incertidumbre.
    #
    # Aisla exactamente lo que aporta el mecanismo dinamico. Por la identidad
    # de H-33 el excedente total no cambia, de modo que la comparacion mide
    # **si el juego reparte mejor o peor que una regla fija**. Y el punto
    # medio reparte la banda a la mitad, con lo que su indice de equidad es
    # cero exacto: es el patron perfectamente equitativo.
    if piso_agente is not None:
        from scenarios._c2_interno import contrato_interno
        flujos = [(r.k, r.seller_ids, r.buyer_ids, r.P_star)
                  for r in p2p_results
                  if r.P_star is not None and r.seller_ids and r.buyer_ids]
        ci = contrato_interno(flujos, pi_gs_v, piso_agente, N, dt=dt)
        # Mismo convenio que el mercado entre pares: autoconsumo a la tarifa
        # propia, y lo que no firma sigue el articulo 25 (D9), no la bolsa.
        # H-78: el vendedor cobra el precio por la energia que entrega, igual
        # que en el mercado entre pares; el comprador ahorra su techo menos
        # el precio. Antes solo se contaba la prima sobre el piso.
        c2_net = ci["cobro_vendedor"] + ci["ahorro_comprador"]
        # C-165: la matriz del contrato trae SOLO el excedente del acuerdo.
        # El autoconsumo y el residual del articulo 25 se le suman aqui,
        # igual que se le suman al total, o el desglose no cuadraria con lo
        # publicado.
        c2_horario = np.array(ci["cobro_horario"], dtype=float)
        for n in prosumer_ids:
            for k in range(T):
                auto = min(G_klim[n, k], D[n, k]) * pi_gs_v[n, k] * dt
                c2_net[n] += auto
                c2_horario[n, k] += auto
        # Lo firmado, por agente y hora, en UNA pasada. Lo que el contrato no
        # firma vuelve al residual del vendedor y a la importacion del
        # comprador (D9), y se liquida por el articulo 25 como el del mercado.
        vendido = np.zeros((N, T))
        comprado = np.zeros((N, T))
        for r in p2p_results:
            if r.P_star is None or not r.seller_ids:
                continue
            Pk = np.asarray(r.P_star, dtype=float)
            if np.isnan(Pk).any():
                continue
            for a_, j in enumerate(r.seller_ids):
                vendido[j, r.k] += float(Pk[a_, :].sum())
            for b_, i in enumerate(r.buyer_ids):
                comprado[i, r.k] += float(Pk[:, b_].sum())
        paso = max(dt, 1e-12)
        vendido = np.maximum(vendido - ci["sin_firmar"] / paso, 0.0)
        comprado = np.maximum(comprado - ci["sin_firmar_comprador"] / paso, 0.0)
        pb_v = (np.full(T, float(pi_gb)) if pi_bolsa is None
                else np.asarray(pi_bolsa, dtype=float).reshape(-1))
        resid = _residual_art25(G_klim, D, vendido, comprado, pi_gs_v, ded_v,
                                pb_v, month_labels, prosumer_ids) * dt
        c2_net += resid.sum(axis=1)
        c2_horario += resid
        cr.net_benefit["C2"]           = float(np.sum(c2_net))
        cr.net_benefit_per_agent["C2"] = c2_net
        cr.neto_horario["C2"] = c2_horario                   # C-165
        cr.contrato_c2 = dict(
            equidad=float(ci["equidad"]),      # cero exacto por construccion
            parejas_sin_firmar=int(ci["parejas_sin_firmar"]),
            precio_medio=float(ci["precio_medio"]),
            kwh=float(ci["kwh"]),
            excedente=float(ci["excedente"]),
            ingreso_vendedor=ci["ingreso_vendedor"],
            ahorro_comprador=ci["ahorro_comprador"],
            cobro_vendedor=ci["cobro_vendedor"],
            # D20: lo que no se firma, en las unidades de P_star (kW del
            # paso), para el factor de coincidencia.
            sin_firmar=ci["sin_firmar"] / paso,
            sin_firmar_comprador=ci["sin_firmar_comprador"] / paso,
        )
    else:
        c2_net = np.array([c2["per_agent"][n]["net_benefit"]
                           for n in range(N)])
    cr.net_benefit["C2"]           = float(np.sum(c2_net))
    cr.net_benefit_per_agent["C2"] = c2_net

    # ── C3 ──────────────────────────────────────────────────────────────
    c3 = run_c3_spot(D, G_klim, pi_gs_v, pi_bolsa, prosumer_ids,
                     consumer_ids, dt=dt, mem_costs=mem_costs)
    c3_net = np.array([c3["per_agent"][n]["net_benefit"] for n in range(N)])
    cr.net_benefit["C3"]           = float(np.sum(c3_net))
    cr.neto_horario["C3"] = c3.get("neto_horario")          # C-165
    cr.net_benefit_per_agent["C3"] = c3_net

    # ── C4: el colectivo MENSUAL, que es el que rige (D4, C-178) ─────────
    # Arts. 19 a 21 de la CREG 101 072 con el art. 25 de la CREG 174 por
    # remision; el caso del art. 20 lo resuelve el porcentaje y la capacidad
    # por usuario, y con el caso 2 la permuta paga T+D+Cv+PR+R (CAL-41). El
    # modo horario queda en el modulo como opcion no normativa y ya no se
    # invoca. Sin calendario, todo el horizonte es un periodo.
    c4 = run_c4_creg101072(D, G_klim, pi_gs_v, pi_bolsa, pde, capacity,
                           component_c=component_c, tolls=tolls,
                           mode="monthly_hx", month_labels=month_labels,
                           dt=dt)
    c4_net = np.array([c4["per_agent"][n]["net_benefit"] for n in range(N)])
    cr.net_benefit["C4"]           = float(np.sum(c4_net))
    cr.neto_horario["C4"]          = c4["neto_horario"]
    cr.net_benefit_per_agent["C4"] = c4_net
    # Alias de una version, para los consumidores que piden la clave vieja.
    cr.net_benefit["C4_mensual"]           = cr.net_benefit["C4"]
    cr.net_benefit_per_agent["C4_mensual"] = c4_net
    cr.neto_horario["C4_mensual"]          = c4["neto_horario"]

    # Los contrafacticos del colectivo (D5).
    _base_c4 = dict(component_c=component_c, tolls=tolls, mode="monthly_hx",
                    month_labels=month_labels, dt=dt)
    _igual = compute_pde_weights(np.ones(N), method="equal")
    # Con 11 fronteras iguales cada una tendria 1/11 < 10 %: caso 1, salvo
    # que alguna planta supere los 100 kW (art. 20 num. 2 ii).
    _caso_11 = (1 if capacity is None
                or float(np.max(capacity)) <= 100.0 else 2)
    _r = run_c4_creg101072(D, G_klim, pi_gs_v, pi_bolsa, _igual, capacity,
                           caso=_caso_11, **_base_c4)
    _pa = np.array([_r["per_agent"][n]["net_benefit"] for n in range(N)])
    cr.contrafacticos["C4_11_fronteras"] = dict(
        total=float(_pa.sum()), por_agente=_pa, caso_art20=_caso_11)
    for _regla in ("consumo", "aporte", "generacion"):
        _pm = pde_por_regla(_regla, G_klim, D, month_labels)
        _r = run_c4_creg101072(D, G_klim, pi_gs_v, pi_bolsa, _igual, capacity,
                               pde_mensual=_pm, **_base_c4)
        _pa = np.array([_r["per_agent"][n]["net_benefit"] for n in range(N)])
        cr.contrafacticos[f"C4_regla_{_regla}"] = dict(
            total=float(_pa.sum()), por_agente=_pa,
            caso_art20=int(_r["caso_art20"]))
    # I-4 (revision final): el mercado por la via del colectivo en el mismo
    # caso favorable de 11 fronteras (spec 4.10, paso 3, y tabla de 4.11).
    from .scenario_p2p_colectivo import run_p2p_colectivo as _pc11
    _r = _pc11(p2p_results, D, G_klim, pi_gs_v, pi_bolsa,
               month_labels=month_labels, component_c=component_c,
               tolls=tolls, capacity=capacity, caso=_caso_11, dt=dt)
    _pa = np.array([_r["per_agent"][n]["net_benefit"] for n in range(N)])
    cr.contrafacticos["P2P_colectivo_11_fronteras"] = dict(
        total=float(_pa.sum()), por_agente=_pa,
        caso_art20=int(_r["caso_art20"]))

    # ── C5 (CAL-37, ADR-0037): AGR CREG 101 099/2026 ────────────────────
    c5 = None
    c5_net = None
    if include_c5:
        from .scenario_c5_agr_creg101099 import run_c5_agr_creg101099
        c5 = run_c5_agr_creg101099(
            D, G_klim, pi_gs_v,
            pi_bolsa if pi_bolsa is not None else np.full(T, float(pi_gb)),
            g_component=g_component if g_component is not None else 0.0,
            cvm_component=cvm_component if cvm_component is not None else 0.0,
            cot_component=cot_component if cot_component is not None else 0.0,
            mem_costs=mem_costs if mem_costs is not None else 0.0,
            cot_alpha=cot_alpha, f_split=f_split_c5, pi_escasez=pi_escasez,
            prosumer_ids=prosumer_ids, dt=dt,
            pi_contrato=pi_contrato_c5, cere=cere_c5,
        )
        c5_net = np.array([c5["per_agent"][n]["net_benefit"]
                           for n in range(N)])
        cr.net_benefit["C5"]           = float(np.sum(c5_net))
        cr.neto_horario["C5"] = c5.get("neto_horario")          # C-165
        cr.net_benefit_per_agent["C5"] = c5_net

    # ── P2P ─────────────────────────────────────────────────────────────
    # C-177: el residual del mercado se liquida por el art. 25 sobre las
    # series residuales, igual que su piso (D2); ya no va a bolsa.
    p2p_net, p2p_horario = _p2p_monetary_benefit(
        p2p_results, D, G_klim, pi_gs_v, pi_gb, prosumer_ids,
        pi_bolsa=pi_bolsa, mode="canonical", dt=dt, devuelve_horario=True,
        month_labels=month_labels, deduccion=ded_v,
    )
    cr.net_benefit["P2P"]           = float(np.sum(p2p_net))
    cr.net_benefit_per_agent["P2P"] = p2p_net
    cr.neto_horario["P2P"]          = p2p_horario          # C-165

    # ── SC / SS ─────────────────────────────────────────────────────────
    # PUNTO 3 — SS unificada: misma definición para todos los escenarios.
    #
    # Definición única (comparable entre P2P y C1-C4):
    #   SC = (autoconsumo_local + energía_P2P_recibida) / D_total
    #   SS = (autoconsumo_local + energía_P2P_recibida) / G_total
    #
    # Para C1–C4: no hay mercado P2P → energía_P2P = 0
    #   SC_C1 = sum(min(G,D)) / sum(G)      ← C-164: contra la GENERACION
    #   SS_C1 = sum(min(G,D)) / sum(D)      ← C-164: contra la DEMANDA
    #
    # Para P2P: se suma el autoconsumo local más lo intercambiado en mercado
    #   SC_P2P = (sum_k [autoconsumo_k + P2P_k]) / G_total
    #   SS_P2P = (sum_k [autoconsumo_k + P2P_k]) / D_total
    #
    # Esto corrige la paradoja SS_P2P < SS_C1 que aparecía porque la versión
    # anterior solo contaba energía del mercado, ignorando el autoconsumo local.

    sc_base = _sc_index_static(G_klim, D)
    ss_base = _ss_index_static(G_klim, D)
    # CAL-42: C4_mensual comparte SC/SS con los demás escenarios sin mercado —
    # la energía física es la misma; lo que cambia es el período de neteo.
    for esc in (["C1", "C2", "C3", "C4"]
                + (["C4_mensual"] if "C4_mensual" in cr.net_benefit else [])
                + (["C5"] if include_c5 else [])):
        cr.self_consumption[esc] = sc_base
        cr.self_sufficiency[esc] = ss_base

    # Para P2P: SC/SS unificados incluyendo autoconsumo + mercado
    active = [r for r in p2p_results
              if r.P_star is not None and np.sum(r.P_star) > 1e-6]

    # Calcular SS/SC P2P sobre el período completo (no solo horas activas)
    T_total   = len(p2p_results)
    D_total   = float(np.sum(np.maximum(D, 0)))
    G_total   = float(np.sum(np.maximum(G_klim, 0)))

    energia_util_total = 0.0   # autoconsumo local + intercambio P2P
    for k, r in enumerate(p2p_results):
        # Autoconsumo local en esta hora (todos los nodos, independiente de si hay mercado)
        autoconsumo_k = float(np.sum(np.minimum(
            np.maximum(G_klim[:, k], 0),
            np.maximum(D[:, k], 0)
        )))
        # Energía adicional cubierta por el mercado P2P esta hora
        p2p_k = float(np.sum(r.P_star)) if r.P_star is not None else 0.0
        energia_util_total += autoconsumo_k + p2p_k

    # C-164: el autoconsumo se mide contra la generacion y la autosuficiencia
    # contra la demanda. Estaban al reves.
    cr.self_consumption["P2P"] = energia_util_total / G_total if G_total > 1e-10 else 0.0
    cr.self_sufficiency["P2P"] = energia_util_total / D_total if D_total > 1e-10 else 0.0

    # ── Equidad (IE) ─────────────────────────────────────────────────────
    #
    # P2P: fórmula del mercado hora a hora (settlement.py)
    #   IE = (ΣS_i − ΣSR_j) / (ΣS_i + ΣSR_j)
    #   S_i  = (pi_gs − pi_star) × P_comprado  ← ahorro comprador
    #   SR_j = (pi_star − pi_gb) × P_vendido   ← prima vendedor
    #   IE = +1 → compradores capturan todo el excedente del mercado
    #   IE = −1 → vendedores/generadores capturan todo
    #   IE =  0 → reparto exactamente igual
    #
    # C1–C4: cuando toda la comunidad son prosumidores (consumer_ids=[]),
    #   la fórmula prosumidor/consumidor colapsa siempre a −1.0 (artefacto).
    #   Fix: clasificar agentes por COBERTURA PV (ratio G/D promedio):
    #     "alta cobertura" = G/D por encima de la mediana → rol vendedor natural
    #     "baja cobertura" = G/D por debajo de la mediana → rol comprador natural
    #   IE = (beneficio_baja_cobertura − beneficio_alta_cobertura) / total
    #   IE = +1 → mecanismo redistribuye hacia quienes menos generan (equitativo)
    #   IE = −1 → mecanismo concentra beneficios en el mayor generador
    #   IE =  0 → distribución proporcional a capacidad instalada

    cr.equity_index["P2P"] = np.mean([r.IE for r in active]) if active else 0.0

    # ── PS / PSR agregados (distribución del excedente P2P) ──────────────
    # Ponderado por kWh transados en cada hora activa:
    #   PS_agg  = Σ_k (PS_k  × kWh_k) / Σ_k kWh_k
    #   PSR_agg = Σ_k (PSR_k × kWh_k) / Σ_k kWh_k
    # Esto es equivalente a calcular (Σ S_i) / (Σ S_i + Σ SR_j) global.
    if active:
        kwh_arr = np.array([float(np.sum(r.P_star)) for r in active])
        ps_arr  = np.array([r.PS  for r in active])
        psr_arr = np.array([r.PSR for r in active])
        total_kwh = float(np.sum(kwh_arr))
        if total_kwh > 1e-9:
            cr.ps_p2p  = float(np.dot(ps_arr,  kwh_arr) / total_kwh)
            cr.psr_p2p = float(np.dot(psr_arr, kwh_arr) / total_kwh)
        else:
            cr.ps_p2p = cr.psr_p2p = 50.0
    else:
        cr.ps_p2p = cr.psr_p2p = 50.0

    # CAL-42: la base mensual de C4 entra a equidad y Gini igual que las demás.
    # Sin esto, el Gini de C4 que reporta la tesis sería solo el de la cota
    # horaria, y la comparación de equidad quedaría descuadrada con la columna
    # de beneficio que sí se publica en base mensual.
    _c4m = ([("C4_mensual", cr.net_benefit_per_agent["C4_mensual"])]
            if "C4_mensual" in cr.net_benefit_per_agent else [])

    for esc, net in ([("C1", c1_net), ("C2", c2_net),
                      ("C3", c3_net), ("C4", c4_net)] + _c4m
                     + ([("C5", c5_net)] if include_c5 else [])):
        cr.equity_index[esc] = _indice_equidad_agregado(
            net, prosumer_ids, consumer_ids, G_raw, D)

    # ── Gini (Índice de desigualdad, propuesta §VI.C Nivel 2) ───────────────
    # Se calcula sobre beneficios netos por agente para todos los escenarios.
    # Gini=0: todos los agentes ganan lo mismo; Gini=1: máxima concentración.
    for esc, net in ([("P2P", p2p_net), ("C1", c1_net),
                      ("C2", c2_net), ("C3", c3_net), ("C4", c4_net)] + _c4m
                     + ([("C5", c5_net)] if include_c5 else [])):
        cr.gini[esc] = gini_index(net)

    # ── Desglose de flujos por componente (Activity 3.2 — Nivel 1) ──────────
    #
    # Para cada escenario, el beneficio neto se descompone en sus fuentes:
    #   Autoconsumo : energía solar consumida en sitio  → valorada a pi_gs
    #   Permutación : energía inyectada que compensa retiros del período (C1)
    #   Excedente   : energía neta exportada            → valorada a pi_bolsa
    #   Prima vend. : ganancia P2P del vendedor sobre pi_gb  (solo P2P)
    #   Ahorro comp.: ahorro del comprador respecto a pi_gs  (solo P2P)
    #   Créditos PDE: distribución administrativa de excedentes (C4)
    #
    # Autoconsumo es IDÉNTICO en todos los escenarios (no depende del mecanismo).
    # Lo que varía es el valor asignado a la energía que pasa por la red.

    # Autoconsumo total (prosumidores) — el kWh es idéntico en todos los
    # escenarios; el valor en COP refleja la tarifa temporal per-agente
    # (CAL-9: matriz N×T mes a mes).
    auto_kwh_hourly = np.minimum(
        np.maximum(G_klim, 0), np.maximum(D, 0),
    )                                              # (N, T) kWh
    auto_kwh_per_agent = auto_kwh_hourly.sum(axis=1)
    auto_kwh = float(np.sum(auto_kwh_per_agent[prosumer_ids]))
    auto_cop = float(np.sum(
        auto_kwh_hourly[prosumer_ids] * pi_gs_v[prosumer_ids]
    ))
    # CAL-46: de potencia a energía, en el autoconsumo que este motor calcula
    # por su cuenta y no le pide a ningún escenario.
    if dt != 1.0:
        auto_kwh_per_agent = auto_kwh_per_agent * dt
        auto_kwh *= dt
        auto_cop *= dt

    # C1 breakdown
    c1_savings_total = c1["aggregate"]["total_savings"]      # auto + permutación
    c1_permutacion   = max(0.0, c1_savings_total - auto_cop) # solo permutación
    c1_excedente     = c1["aggregate"]["total_surplus_revenue"]

    # C3 breakdown
    c3_auto_total    = c3["aggregate"]["total_savings"]
    c3_excedente     = c3["aggregate"]["total_revenues"]

    # C4 breakdown
    c4_auto_total    = c4["aggregate"]["total_savings"]
    c4_pde_credits   = c4["aggregate"]["total_pde_credits"]
    c4_excedente     = c4["aggregate"]["total_surplus_revenue"]

    # P2P breakdown: prima vendedor + ahorro comprador + autoconsumo propio
    p2p_prima, p2p_ahorro = _p2p_flow_breakdown(p2p_results, pi_gs_v, pi_gb,
                                                dt=dt)

    cr.flow_breakdown = {
        "P2P": {
            "Autoconsumo":      auto_cop,
            "Prima vendedor":   p2p_prima,
            "Ahorro comprador": p2p_ahorro,
        },
        "C1": {
            "Autoconsumo":    auto_cop,
            "Permutación":    c1_permutacion,
            "Excedente neto": c1_excedente,
        },
        # CAL-37: C2 cableado al desglose (gap detectado por el autor).
        "C2": {
            "Autoconsumo + ingreso PPA": c2["aggregate"]["total_savings_gen"],
            "Ahorro no-regulado (PPA)":  c2["aggregate"]["total_savings_ppa"],
            "Excedente bolsa":           c2["aggregate"]["total_grid_revenue"],
        },
        "C3": {
            "Autoconsumo":     c3_auto_total,
            "Excedente bolsa": c3_excedente,
        },
        "C4": {
            "Autoconsumo":   c4_auto_total,
            "Créditos PDE":  c4_pde_credits,
            "Excedente bolsa": c4_excedente,
        },
    }
    if include_c5 and c5 is not None:
        cr.flow_breakdown["C5"] = {
            "Autoconsumo":       c5["aggregate"]["total_autoconsumo"],
            "Compensación AGR":  c5["aggregate"]["total_compensacion"],
            "Excedente bolsa":   c5["aggregate"]["total_residual_bolsa"],
        }

    # ── Act 3.3: Bienestar de optimización (Nivel 2 — u.o.) ─────────────
    # Acumula los valores W_j y W_i calculados por el motor P2P hora a hora.
    # Estos incluyen utilidad de autoconsumo (λ, θ) y aversión al riesgo (η),
    # que no están capturados en el beneficio monetario de Nivel 1.
    # CAL-46: las utilidades del juego son por unidad de tiempo, de modo que
    # su acumulado sobre el horizonte lleva el mismo factor que el dinero.
    cr.W_sellers_total = float(sum(
        r.Wj_total for r in p2p_results if r.P_star is not None)) * dt
    cr.W_buyers_total = float(sum(
        r.Wi_total for r in p2p_results if r.P_star is not None)) * dt

    # ── RPE: Rendimiento Relativo P2P vs C4 ──────────────────────────────
    w_p2p = cr.net_benefit["P2P"]
    w_c4  = cr.net_benefit["C4"]
    cr.rpe = ((w_p2p - w_c4) / abs(w_p2p)
              if abs(w_p2p) > 1e-10 else 0.0)

    # ── PoF: Price of Fairness (Bertsimas 2011) ───────────────────────────
    cr.fairness = compute_pof(cr.net_benefit_per_agent, cr.gini)

    # ── Spread de ineficiencia estática C4 ───────────────────────────────
    cr.static_spread_24h = static_spread_c4_vs_p2p(D, G_klim, pde)

    # ── El mercado liquidado por la via del colectivo (D8) ───────────────
    # Va al final a proposito: es una columna nueva y no debe alterar la
    # equidad ni el precio de la equidad que ya se calcularon para las demas.
    from .scenario_p2p_colectivo import run_p2p_colectivo
    _pc = run_p2p_colectivo(p2p_results, D, G_klim, pi_gs_v, pi_bolsa,
                            month_labels=month_labels, component_c=component_c,
                            tolls=tolls, capacity=capacity, dt=dt)
    _pc_net = np.array([_pc["per_agent"][n]["net_benefit"] for n in range(N)])
    cr.net_benefit["P2P_colectivo"]           = float(_pc_net.sum())
    cr.net_benefit_per_agent["P2P_colectivo"] = _pc_net
    cr.neto_horario["P2P_colectivo"]          = _pc["neto_horario"]
    cr.self_consumption["P2P_colectivo"] = cr.self_consumption["P2P"]
    cr.self_sufficiency["P2P_colectivo"] = cr.self_sufficiency["P2P"]
    cr.gini["P2P_colectivo"] = gini_index(_pc_net)
    # Tarea 16: su indice de equidad, con la formula de los regulados. Sin
    # el, la tabla imprimia 0.0000 por el respaldo de una clave ausente.
    cr.equity_index["P2P_colectivo"] = _indice_equidad_agregado(
        _pc_net, prosumer_ids, consumer_ids, G_raw, D)

    # ── El factor de coincidencia (D20) ──────────────────────────────────
    from analysis.coincidencia import (coincidencia_por_mecanismo,
                                       simultaneidad_picos)
    _c2 = cr.contrato_c2 or {}
    cr.coincidencia = coincidencia_por_mecanismo(
        D, G_klim, p2p_results, month_labels=month_labels, pde=pde,
        pde_colectivo=_pc["pde_por_mes"],
        sin_firmar=_c2.get("sin_firmar"),
        sin_firmar_comprador=_c2.get("sin_firmar_comprador"),
        include_c5=include_c5)
    if "C4_mensual" in cr.net_benefit:
        cr.coincidencia["C4_mensual"] = cr.coincidencia["C4"]   # alias C-178
    cr.simultaneidad = simultaneidad_picos(D, G_klim)

    return cr


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _indice_equidad_agregado(net, prosumer_ids, consumer_ids, G_raw, D) -> float:
    """Indice de equidad agregado de un escenario sin mercado horario.

    Es la formula que run_comparison aplicaba en linea a C1-C5, en un solo
    sitio para que la columna del mercado por la via del colectivo use la
    misma (tarea 16).
    """
    net = np.asarray(net, dtype=float)
    if len(consumer_ids) > 0:
        # Comunidad mixta (prosumidores + consumidores puros): formula original
        s_gen  = float(np.sum(net[prosumer_ids]))
        s_cons = float(np.sum(net[consumer_ids]))
        total  = abs(s_gen) + abs(s_cons)
        return (s_cons - s_gen) / total if total > 1e-10 else 0.0
    # Comunidad 100 % prosumidores: clasificar por cobertura PV (G/D)
    g_mean = np.mean(G_raw, axis=1)
    d_mean = np.mean(D,     axis=1)
    gd_ratio = g_mean / np.maximum(d_mean, 1e-9)
    gd_median = np.median(gd_ratio)
    high_cov = [n for n in prosumer_ids if gd_ratio[n] >= gd_median]
    low_cov  = [n for n in prosumer_ids if gd_ratio[n] <  gd_median]
    s_alta = float(np.sum(net[high_cov])) if high_cov else 0.0
    s_baja = float(np.sum(net[low_cov]))  if low_cov  else 0.0
    total  = abs(s_alta) + abs(s_baja)
    return (s_baja - s_alta) / total if total > 1e-10 else 0.0


def _effective_buyer_prices(pi_star, buyer_ids, pi_gs_v, k_local):
    """CAL-35 (ADR-0035): precio efectivo por comprador en el settlement.

        pi_eff[i] = min(pi_star[i], pi_gs[i, k])

    El juego (Stackelberg+RD, fiel a Chacón ec. 8) acota pi_star con un
    techo ESCALAR comunitario; un comprador real nunca paga por encima de
    SU tarifa de red. El cap se aplica solo al contar dinero — el juego no
    se modifica. Garantías: (a) no-op con techos homogéneos (sintético
    1250 / paper 956) → resultados idénticos; (b) el total comunitario es
    invariante (vendedor+comprador = pi_gs[i]·kWh, el precio se cancela);
    (c) solo redistribuye vendedor→comprador cuando pi_star > pi_gs[i,k].
    """
    caps = np.array([float(pi_gs_v[i, k_local]) for i in buyer_ids])
    return np.minimum(np.asarray(pi_star, dtype=float), caps)


def _residual_art25(G_klim, D, vendido, comprado, pi_gs_v, deduccion,
                    pi_bolsa_v, month_labels, ids):
    """Dinero (N, T) del excedente que el mercado no coloca (D2, D3, C-177).

    Se liquida como el de un autogenerador, sobre las series RESIDUALES: la
    inyeccion menos lo vendido dentro, contra la importacion menos lo comprado
    dentro (lectura comercial). Credito hasta el cupo del mes, valorado a la
    tarifa media del periodo menos la deduccion del articulo 25, y exceso a la
    bolsa de cada hora desde el corte hx del Anexo 4. No multiplica por `dt`.
    """
    N, T = D.shape
    Gp = np.maximum(np.asarray(G_klim, dtype=float), 0.0)
    Dp = np.maximum(np.asarray(D, dtype=float), 0.0)
    iny = np.maximum(np.maximum(Gp - Dp, 0.0) - vendido, 0.0)
    ret = np.maximum(np.maximum(Dp - Gp, 0.0) - comprado, 0.0)
    credito, exceso, _ = reparto_anexo4(iny, ret, month_labels)
    precio = precio_permuta_por_periodo(pi_gs_v, deduccion, month_labels)
    valor = credito * precio + exceso * np.asarray(pi_bolsa_v)[None, :]
    fuera = np.ones(N, dtype=bool)
    fuera[list(ids)] = False
    valor[fuera, :] = 0.0
    return valor


def _p2p_monetary_benefit(results, D, G_klim, pi_gs, pi_gb,
                           prosumer_ids,
                           pi_bolsa: Optional[np.ndarray] = None,
                           mode: str = "canonical",
                           dt: float = 1.0,
                           devuelve_horario: bool = False,
                           month_labels=None,
                           deduccion=None):
    """
    Convierte resultados P2P a flujos monetarios netos por agente.

    Dos modos disponibles (CAL-30, ADR-0030):

    ``mode="canonical"`` (default desde CAL-30, simétrico con C1/C2/C3/C4):
        Vendedor:    π_star × P_vendido + π_bolsa[k] × residual    (revenue
                     COMPLETO: trade interno + residual exportado a la red)
        Comprador:   (π_gs[i, k] − π_star[i]) × P_comprado          (ahorro
                     vs comprar a la red)
        Autoconsumo: min(G, D) × π_gs[n, k]                         (todas
                     las horas, tarifa temporal CAL-9)

    ``mode="premium"`` (legacy, pre-CAL-30, mantenido para reproducibilidad):
        Vendedor:    (π_star − π_gb) × P_vendido    (prima incremental
                     sobre el contrafactual "vender todo a bolsa")
        Comprador:   (π_gs[i, k] − π_star[i]) × P_comprado    (igual)
        Autoconsumo: min(G, D) × π_gs[n, k]                    (igual)

    La diferencia es exactamente:
        canonical[n] − premium[n] = π_gb × P_vendido[n] + π_bolsa × residual[n]

    Cuando π_bolsa ≈ π_gb y residual = surplus_total − P_vendido, el extra
    canónico equivale a ``π_bolsa × surplus_total[n]`` por agente — lo que
    el prosumidor RECIBIRÍA del comercializador por exportar su surplus al
    spot, que en la fórmula premium se cancelaba contra un baseline implícito.

    Auditoría empírica (Sprint 6.6-A, 2026-05-02): la fórmula premium
    sub-reporta el net_benefit P2P en ``π_bolsa_mean × E_surplus_total``
    cuando la cobertura PV es alta. En el caso paper agosto-2025 con CAL-28
    sub-medidores (96 % cobertura) el sub-reporte fue 958 K COP de 4.95 M
    totales (≈ 19 %). En la tesis con M1 totalizador (19 % cobertura) el
    sub-reporte es estructuralmente más pequeño (E_surplus_total reducido).

    Ver ``Documentos/audit_p2p_decomposition.md`` y
    ``docs/adr/0029-cal29-p2p-revenue-canonica.md`` para el análisis
    completo.

    Parámetros
    ----------
    results : list[HourlyResult]
    D, G_klim : ndarray (N, T)
    pi_gs : float | ndarray (N,) | ndarray (N, T) — CAL-9
    pi_gb : float — precio de bolsa escalar (baseline modo premium / fallback)
    prosumer_ids : list[int] — índices de agentes con generación propia
    pi_bolsa : ndarray (T,) | None — precio bolsa horario para modo canonical.
        Si None, se usa π_gb escalar como aproximación.
    mode : "canonical" | "premium" — fórmula a aplicar (default canonical).
    dt : float — duración del paso en horas (CAL-46). Las cantidades del juego
        y las matrices son potencia media del paso (kW) y los precios COP/kWh,
        de modo que el dinero lleva el factor de duración. Todo lo que este
        cálculo acumula es lineal en la energía y por eso basta escalarlo al
        final. Con paso horario dt = 1.0 y no se ejecuta ninguna operación.
    month_labels, deduccion : con `deduccion` (N, T) el residual se liquida
        por el articulo 25 sobre las series residuales (D2, C-177), con el
        corte hx por periodo de `month_labels`. Con None se conserva el
        residual a bolsa horaria de CAL-30, que solo usan llamadores viejos.
    """
    N, T = D.shape
    pi_gs_v = as_pi_gs_array(pi_gs, N, T)
    net = np.zeros(N)
    # C-165: el mismo dinero, anotado en la hora que lo genera. Se llena en
    # paralelo con `net` y no lo sustituye: la compuerta comprueba que sus
    # filas suman exactamente el vector que este calculo ya devolvia.
    neto_horario = np.zeros((N, T))

    if mode not in ("canonical", "premium"):
        raise ValueError(
            f"mode={mode!r} no válido (esperado 'canonical' o 'premium')"
        )

    # Modo canonical: vector pi_bolsa horario (con fallback a pi_gb escalar).
    if mode == "canonical":
        if pi_bolsa is None:
            pi_bolsa_v = np.full(T, float(pi_gb))
        else:
            pi_bolsa_v = np.asarray(pi_bolsa, dtype=float).reshape(-1)
            if pi_bolsa_v.size != T:
                raise ValueError(
                    f"pi_bolsa size {pi_bolsa_v.size} != T={T}"
                )
        # Acumulador kWh vendidos por agente y hora (para residual surplus).
        P_sold_n_k = np.zeros((N, T))
        P_bought_n_k = np.zeros((N, T))

    # Indexación por POSICIÓN en la lista, no por r.k. El caller debe pasar
    # results alineado con D (mismas T columnas, mismo orden). Esto permite
    # usarlo tanto sobre el horizonte completo (run_comparison) como sobre
    # slices diarios (_compute_daily_series), sin tener que mapear r.k global
    # a un índice local mes a mes.
    for k_local, r in enumerate(results):
        if r.P_star is None:
            continue

        # Guard: si el ODE devolvió NaN (~0.2% de horas con G_net minúsculos +
        # VelGrad=1e6 generan inestabilidad numérica puntual) se salta la hora
        # como si no hubiera mercado. Un solo NaN contamina toda la agregación.
        if np.isnan(r.P_star).any() or (
                r.pi_star is not None and np.isnan(r.pi_star).any()):
            continue

        # CAL-35: precios efectivos por comprador para esta hora.
        pi_eff = (_effective_buyer_prices(r.pi_star, r.buyer_ids,
                                          pi_gs_v, k_local)
                  if r.pi_star is not None else None)

        # Vendedores
        for idx_j, j in enumerate(r.seller_ids):
            if pi_eff is not None:
                income = float(np.dot(pi_eff, r.P_star[idx_j, :]))
            else:
                income = float(np.sum(r.P_star[idx_j, :])) * pi_gb
            sold = float(np.sum(r.P_star[idx_j, :]))
            if mode == "canonical":
                # Revenue completo del trade
                net[j] += income
                neto_horario[j, k_local] += income
                P_sold_n_k[j, k_local] = sold
            else:
                # Premium: prima sobre venta a bolsa
                baseline = sold * pi_gb
                net[j] += income - baseline
                neto_horario[j, k_local] += income - baseline

        # Compradores: ahorro por pagar pi_star en vez de comprar todo a la
        # red. La tarifa de referencia es la del agente en la hora del mercado.
        # Idéntico en ambos modos.
        for idx_i, i in enumerate(r.buyer_ids):
            received = float(np.sum(r.P_star[:, idx_i]))
            if mode == "canonical":
                P_bought_n_k[i, k_local] += received
            pi_ref = float(pi_gs_v[i, k_local])
            if pi_eff is not None:
                paid = pi_eff[idx_i] * received
            else:
                paid = received * pi_ref
            net[i] += received * pi_ref - paid
            neto_horario[i, k_local] += received * pi_ref - paid

    # Autoconsumo propio de prosumidores a su pi_gs[n, k] (tarifa temporal).
    # Idéntico en ambos modos (todas las horas, no solo activas).
    for n in prosumer_ids:
        for k in range(T):
            auto = min(G_klim[n, k], D[n, k])
            net[n] += auto * pi_gs_v[n, k]
            neto_horario[n, k] += auto * pi_gs_v[n, k]

    # Residual del mercado (solo modo canonical).
    if mode == "canonical" and deduccion is not None:
        resid = _residual_art25(G_klim, D, P_sold_n_k, P_bought_n_k, pi_gs_v,
                                np.asarray(deduccion, dtype=float), pi_bolsa_v,
                                month_labels, prosumer_ids)
        net += resid.sum(axis=1)
        neto_horario += resid
    elif mode == "canonical":
        for n in prosumer_ids:
            for k in range(T):
                G_nk = max(float(G_klim[n, k]), 0.0)
                D_nk = max(float(D[n, k]), 0.0)
                surplus_total_nk = max(G_nk - D_nk, 0.0)
                residual_nk = max(surplus_total_nk - P_sold_n_k[n, k], 0.0)
                net[n] += residual_nk * float(pi_bolsa_v[k])
                neto_horario[n, k] += residual_nk * float(pi_bolsa_v[k])

    # CAL-46: de potencia a energía.
    if dt != 1.0:
        net = net * dt
        neto_horario = neto_horario * dt

    if devuelve_horario:
        return net, neto_horario
    return net


def _p2p_flow_breakdown(results, pi_gs, pi_gb: float,
                        dt: float = 1.0) -> tuple:
    """
    Descompone el beneficio P2P en prima de vendedor y ahorro de comprador.

      prima_vendedor  : Σ_k Σ_j max(0, ingreso_j - baseline_j)
      ahorro_comprador: Σ_k Σ_i max(0, pi_gs[i, k] × P_comprado - pagado)

    El autoconsumo propio se contabiliza por separado (igual kWh en todos
    los escenarios, valorado a la pi_gs temporal per-agente).

    Parámetros
    ----------
    results : list[HourlyResult]
    pi_gs   : float | ndarray (N,) | ndarray (N, T) — tarifa al usuario (CAL-9)
    pi_gb   : float — precio de bolsa, baseline de venta (COP/kWh)
    dt      : float — duración del paso en horas (CAL-46)
    """
    if not results:
        return 0.0, 0.0
    # N y T implícitos en buyer_ids/seller_ids y len(results).
    N_inferred = 0
    for r in results:
        if r.P_star is None:
            continue
        if r.buyer_ids:
            N_inferred = max(N_inferred, max(r.buyer_ids) + 1)
        if r.seller_ids:
            N_inferred = max(N_inferred, max(r.seller_ids) + 1)
    T_inferred = len(results)
    if N_inferred == 0:
        return 0.0, 0.0
    pi_gs_v = as_pi_gs_array(pi_gs, N_inferred, T_inferred)

    prima  = 0.0
    ahorro = 0.0
    for k_local, r in enumerate(results):
        if r.P_star is None:
            continue
        # CAL-35: precio efectivo por comprador (ver _effective_buyer_prices).
        pi_eff = (_effective_buyer_prices(r.pi_star, r.buyer_ids,
                                          pi_gs_v, k_local)
                  if r.pi_star is not None else None)
        for idx_j, j in enumerate(r.seller_ids):
            if pi_eff is not None:
                income = float(np.dot(pi_eff, r.P_star[idx_j, :]))
            else:
                income = float(np.sum(r.P_star[idx_j, :])) * pi_gb
            baseline = float(np.sum(r.P_star[idx_j, :])) * pi_gb
            prima += max(0.0, income - baseline)
        for idx_i, i in enumerate(r.buyer_ids):
            received = float(np.sum(r.P_star[:, idx_i]))
            pi_ref = float(pi_gs_v[i, k_local])
            paid     = (pi_eff[idx_i] * received if pi_eff is not None
                        else received * pi_ref)
            ahorro  += max(0.0, received * pi_ref - paid)
    # CAL-46: de potencia a energía.
    if dt != 1.0:
        prima *= dt
        ahorro *= dt
    return prima, ahorro


def print_welfare_decomposition(cr: "ComparisonResult") -> None:
    """
    Act 3.3 — Descomposición formal del bienestar P2P.

    Nivel 1 — Beneficio monetario directo (COP):
        Comparable directamente con C1–C4 (que son puramente financieros).
        Fuentes: autoconsumo, prima vendedor, ahorro comprador.

    Nivel 2 — Bienestar de optimización (u.o.) + métricas sociales:
        W_j y W_i guían la dinámica de replicador e incluyen utilidad de
        autoconsumo (λ, θ) y aversión al riesgo (η). No son COP, pero
        cuantifican el valor intangible del mecanismo dinámico.
        Métricas sociales: IE, Gini, SC, SS, PoF.

    Referencia: propuesta tesis §VI.C Act 3.3, §VII.C Niveles 1 y 2.
    """
    W = 70
    print("\n" + "=" * W)
    print("  Act 3.3 — DESCOMPOSICIÓN DEL BIENESTAR P2P")
    print("  (distingue beneficio monetario de intangibles del mecanismo dinámico)")
    print("=" * W)

    # ── Nivel 1: monetario ────────────────────────────────────────────────
    print("\n  NIVEL 1 — Beneficio monetario directo (COP)")
    print(f"  {'(comparable con C1–C4 que son puramente financieros)'}")
    print(f"  {'-' * 60}")
    bd = cr.flow_breakdown.get("P2P", {})
    if bd:
        total_mon = sum(bd.values())
        for comp, val in bd.items():
            pct = val / total_mon * 100 if total_mon > 1e-6 else 0.0
            print(f"    {comp:<26} {val:>14,.0f} COP  ({pct:5.1f}%)")
        print(f"    {'─' * 52}")
        print(f"    {'TOTAL monetario (Nivel 1)':<26} {total_mon:>14,.0f} COP  (100.0%)")
    else:
        print(f"    (no disponible — ejecutar con datos reales)")

    # ── Nivel 2: intangibles del mecanismo ───────────────────────────────
    print(f"\n  NIVEL 2 — Bienestar publicado, evaluado en el equilibrio")
    print(f"  {'(incluye: utilidad de autoconsumo λ/θ, aversión al riesgo η)'}")
    print(f"  {'-' * 60}")
    W_total = cr.W_sellers_total + cr.W_buyers_total
    print(f"    {'Bienestar vendedores  Σ W_j':<34} {cr.W_sellers_total:>12.4f} u.o.")
    print(f"    {'Bienestar compradores Σ W_i':<34} {cr.W_buyers_total:>12.4f} u.o.")
    print(f"    {'─' * 52}")
    print(f"    {'Suma, Wj + Wi':<34} {W_total:>12.4f} u.o.")
    # H-44: la nota anterior decia que estos valores «guian la dinamica de
    # replicador». Medido, es falso: la aptitud que mueve los precios es el
    # gradiente del bienestar del documento extenso, no de la ecuacion que
    # esta suma evalua, y las dos difieren por un factor de miles. Ademas la
    # suma es degenerada como objetivo (H-40): su optimo manda todos los
    # precios al piso. Decirlo aqui evita la unica lectura que hace dano.
    print(f"\n    Nota: u.o. = unidades de optimización, no son COP. Es la")
    print(f"    definición de bienestar de la versión arbitrada del modelo")
    print(f"    base, evaluada en el equilibrio. NO es lo que la dinámica")
    print(f"    maximiza ni una medida de calidad: su óptimo manda todos los")
    print(f"    precios al piso. Ver H-40 y H-44. La medida de calidad del")
    print(f"    trabajo es el ahorro capturado frente al alcanzable (H-39).")

    # ── Métricas sociales (componente intangible observable) ─────────────
    print(f"\n  NIVEL 2 — Métricas sociales del mecanismo P2P")
    print(f"  {'-' * 60}")
    ie   = cr.equity_index.get("P2P",   0.0)
    ie4  = cr.equity_index.get("C4",    0.0)
    gini = cr.gini.get("P2P",           0.0)
    gini4 = cr.gini.get("C4",           0.0)
    sc   = cr.self_consumption.get("P2P", 0.0)
    ss   = cr.self_sufficiency.get("P2P", 0.0)
    rpe  = cr.rpe or 0.0
    print(f"    IE  P2P = {ie:+.4f}   vs   IE  C4 = {ie4:+.4f}  "
          f"  Δ = {ie - ie4:+.4f}")
    print(f"    Gini P2P = {gini:.4f}   vs   Gini C4 = {gini4:.4f}  "
          f"  Δ = {gini - gini4:+.4f}")
    print(f"    SC  P2P = {sc:.4f}    SS  P2P = {ss:.4f}")
    print(f"    RPE (P2P vs C4): {rpe:.4f}  [Rendimiento relativo vs C4; RPE > 0: P2P supera C4]")

    if cr.fairness is not None and cr.fairness.eff_scenario:
        fr = cr.fairness
        print(f"    PoF (Bertsimas 2011): {fr.pof:.4f}  "
              f"[{fr.eff_scenario}→{fr.fair_scenario}: "
              f"−{(fr.w_eff-fr.w_fair):,.0f} COP por equidad]")

    print("=" * W)


def print_flow_breakdown(cr: "ComparisonResult", currency: str = "COP") -> None:
    """
    Imprime el desglose de flujos por componente para cada escenario.
    Activity 3.2 — Nivel 1: flujos de caja netos por fuente de valor.
    """
    if not cr.flow_breakdown:
        return

    print("\n" + "="*68)
    print("  DESGLOSE DE FLUJOS POR COMPONENTE  (Activity 3.2 — Nivel 1)")
    print("  (muestra cómo se genera el beneficio neto en cada escenario)")
    print("="*68)

    # CAL-37: orden canónico, pero solo se imprimen los presentes en el dict
    esc_order = ["P2P", "C1", "C2", "C3", "C4", "C5"]
    labels = {
        "P2P": "P2P (Stackelberg + RD)",
        "C1":  "C1  CREG 174 — AGPE",
        "C2":  ("C2  Contrato interno (precio pactado)" if cr.contrato_c2
                else "C2  Bilateral PPA (no regulado)"),
        "C3":  "C3  Mercado spot",
        "C4":  "C4  CREG 101 072 — AGRC",
        "C5":  "C5  CREG 101 099 — AGR",
    }
    col_w = 16

    for esc in esc_order:
        bd = cr.flow_breakdown.get(esc)
        if not bd:
            continue
        total = sum(bd.values())
        print(f"\n  {labels[esc]}")
        print(f"  {'Componente':<24} {'COP':>{col_w}} {'%':>7}")
        print(f"  {'-'*50}")
        for comp, val in bd.items():
            pct = val / total * 100 if total > 1e-6 else 0.0
            print(f"  {comp:<24} {val:>{col_w},.0f} {pct:>7.1f}%")
        print(f"  {'TOTAL':<24} {total:>{col_w},.0f} {'100.0%':>7}")

    print("="*68)
    # Nota interpretativa
    auto_p2p = cr.flow_breakdown.get("P2P", {}).get("Autoconsumo", 0)
    auto_c1  = cr.flow_breakdown.get("C1",  {}).get("Autoconsumo", 0)
    if auto_p2p > 0 and abs(auto_p2p - auto_c1) < 1.0:
        print("  Nota: el autoconsumo es idéntico en todos los escenarios —")
        print(f"        lo que varía es el valor asignado a los excedentes.")
    print("="*68)

    # ── Act 3.3: descomposición formal del bienestar ─────────────────────
    print_welfare_decomposition(cr)


def _sc_index_static(G_klim, D) -> float:
    """El autoconsumo sin mercado: min(G,D) / sum(G).

    C-164: esta funcion dividia por la demanda, que es la autosuficiencia. Los
    dos nombres estaban cruzados aqui y en el modulo de liquidacion.
    """
    used = float(np.sum(np.minimum(
        np.maximum(G_klim, 0), np.maximum(D, 0))))
    gen  = float(np.sum(np.maximum(G_klim, 0)))
    return used / gen if gen > 1e-10 else 0.0


def _ss_index_static(G_klim, D) -> float:
    """La autosuficiencia sin mercado: min(G,D) / sum(D). Ver C-164."""
    used  = float(np.sum(np.minimum(
        np.maximum(G_klim, 0), np.maximum(D, 0))))
    total = float(np.sum(np.maximum(D, 0)))
    return used / total if total > 1e-10 else 0.0


def print_comparison_report(cr: ComparisonResult) -> None:
    # CAL-37: C5 aparece si fue calculado (include_c5 en run_comparison)
    # CAL-42: y C4_mensual cuando hay calendario de facturación.
    scenarios = [e for e in ["P2P", "P2P_colectivo", "C1", "C2", "C3", "C4",
                              "C4_mensual", "C5"]
                 if e in cr.net_benefit]
    labels = {
        "P2P": "P2P (Stackelberg + RD)",
        "P2P_colectivo": "P2P  por la via del colectivo (dos niveles)",
        "C1":  "C1  Individual CREG 174/2021",
        # CAL-52: el rotulo dice el precio MEDIO PACTADO cuando el contrato es
        # el interno, que ya no tiene un precio unico: cada pareja contrata en
        # el punto medio de su propia banda. Con el contrato externo, el de
        # antes.
        "C2":  (f"C2  Contrato interno (${cr.contrato_c2['precio_medio']:.0f}"
                f"/kWh medio)" if cr.contrato_c2
                else f"C2  Bilateral PPA (${cr.pi_ppa:.0f}/kWh)"),
        "C3":  "C3  Spot (bolsa mayorista)",
        "C4":  "C4  Colectivo CREG 101 072 (mensual)",
        "C4_mensual": "C4m Colectivo CREG 101 072 (mensual)",
        "C5":  "C5  AGR CREG 101 099/2026",
    }
    print("\n" + "="*80)
    print("  COMPARACIÓN REGULATORIA  —  BENEFICIO ECONÓMICO DEL SISTEMA SOLAR")
    print("  (ahorro en factura + ingresos; no incluye compras residuales a red)")
    print("="*80)
    print(f"  {'Escenario':<32} {'Beneficio':>12}  {'SC':>6}  {'SS':>6}  "
          f"{'IE':>8}  {'Gini':>6}")
    print(f"  {'':32} {'COP/período':>12}  {'[0-1]':>6}  {'[0-1]':>6}  "
          f"{'[-1,+1]':>8}  {'[0-1]':>6}")
    print("-"*80)
    for esc in scenarios:
        nb   = cr.net_benefit.get(esc, 0.0)
        sc   = cr.self_consumption.get(esc, 0.0)
        ss   = cr.self_sufficiency.get(esc, 0.0)
        ie   = cr.equity_index.get(esc, 0.0)
        gini = cr.gini.get(esc, 0.0)
        print(f"  {labels[esc]:<32} ${nb:>11,.0f}  {sc:>6.3f}  "
              f"{ss:>6.3f}  {ie:>8.4f}  {gini:>6.4f}")
    print("="*80)
    print(f"  RPE (P2P vs C4):  {cr.rpe:.4f}")
    if cr.fairness is not None and cr.fairness.eff_scenario:
        fr = cr.fairness
        print(f"  PoF (Bertsimas 2011):  {fr.pof:.4f}  "
              f"[eficiente={fr.eff_scenario} {fr.w_eff:,.0f} COP; "
              f"equitativo={fr.fair_scenario} {fr.w_fair:,.0f} COP]")
    if cr.static_spread_24h is not None:
        print(f"  Spread inef. estática C4 total: "
              f"{np.sum(cr.static_spread_24h):.3f} kWh")
    print("-"*68)
    print(f"  Distribución del excedente P2P (ref. Tabla VII Sofía Chacón):")
    print(f"    PS  (compradores):  {cr.ps_p2p:6.2f}%  "
          f"← fracción del surplus P2P capturada por compradores")
    print(f"    PSR (vendedores):   {cr.psr_p2p:6.2f}%  "
          f"← fracción del surplus P2P capturada por vendedores")
    psr_gap = abs(cr.ps_p2p - cr.psr_p2p)
    dominant = "compradores" if cr.ps_p2p > cr.psr_p2p else "vendedores"
    print(f"    → Asimetría: {psr_gap:.2f} pp a favor de {dominant}  "
          f"(IE={cr.equity_index.get('P2P', 0):.4f})")
    # CAL-52: el patron contra el que se mide ese reparto. El contrato interno
    # liquida los MISMOS flujos al punto medio de la banda, de modo que su
    # reparto es 50/50 exacto. Puestos uno al lado del otro, la diferencia es
    # lo que el mecanismo dinamico le quita a un lado y le da al otro.
    if cr.contrato_c2:
        d = cr.contrato_c2
        print("-"*68)
        print("  Y el mismo reparto bajo contrato interno a precio pactado:")
        print(f"    reparto 50,00 % / 50,00 %  (índice {d['equidad']:+.2e}, "
              f"cero por construcción)")
        print(f"    precio medio pactado: {d['precio_medio']:,.2f} COP/kWh "
              f"sobre {d['kwh']:,.1f} kWh")
        print(f"    → el mercado desplaza {psr_gap/2:.2f} pp del excedente "
              f"hacia {dominant} frente al reparto a la mitad")
    # I-3 (revision final): los contrafacticos del colectivo (D5, D11), una
    # linea cada uno. Se calculaban en cada corrida y no llegaban a ninguna
    # salida.
    if cr.contrafacticos:
        print("-"*68)
        print("  Contrafacticos del colectivo (D5, D11):")
        for nombre, d in cr.contrafacticos.items():
            print(f"    {nombre:<28} ${d['total']:>13,.0f}  "
                  f"caso art. 20: {d['caso_art20']}")
    print("="*68)
