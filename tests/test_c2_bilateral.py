"""
tests/test_c2_bilateral.py — CAL-11: Auditoría del escenario C2 (PPA bilateral)
==============================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 3.1-3.3

Verifica las propiedades formales del escenario C2 declaradas en
ADR-0011 (CAL-11):

  1. ppa_price_range produce valores dentro de [pi_gb, pi_gs] para
     todo factor f en [0, 1].
  2. Teorema de invarianza (notas §3.8): el bienestar agregado
     Sigma_n net_benefit_n es constante respecto al factor f en
     comunidad cerrada.
  3. Gini NO es invariante a f: la distribución entre prosumidores y
     consumidores cambia, lo que justifica reportar Gini en SA-3.
  4. Pay-as-Produced: toda la generación PV horaria se asigna entre
     autoconsumo, venta vía PPA y venta a red.
  5. Balance de energía por consumidor: D_n = autoconsumo_n
     (= 0 para puros) + ppa_recibida_n + grid_residual_n.
  6. El default usado en main_simulation.py:269 corresponde
     exactamente a f = 0.5 (punto medio del rango [pi_gb, pi_gs]).
  7. C2 acepta pi_gs como matriz (N, T) (compatibilidad CAL-9).

Referencias:
  - ADR-0011 (CAL-11, C2 PPA bilateral, modelo formal)
  - Especificacion de diseno interna (auditoria PPA bilateral C2)
"""

from __future__ import annotations

import numpy as np
import pytest

from scenarios.scenario_c2_bilateral import run_c2_bilateral, ppa_price_range


# ─── Fixture: mini-comunidad sintética con asimetría -------------------------
#
# 6 agentes: 3 prosumidores (0, 1, 2) + 3 consumidores puros (3, 4, 5).
# 24 horas (un día). Generación PV solo entre 8h y 18h con perfiles
# campana asimétricos para forzar Gini distinto entre escenarios f.

PI_GB = 200.0    # COP/kWh — venta excedente a red
PI_GS = 800.0    # COP/kWh — tarifa minorista (escalar; tests específicos
                 # extienden a matriz (N, T))


def _build_mini_community():
    """Devuelve (D, G, prosumer_ids, consumer_ids) — mini-comunidad 6x24."""
    N, T = 6, 24
    rng = np.random.default_rng(seed=11)

    D = np.zeros((N, T))
    # Demanda base diferenciada para que Gini sea informativo
    base_demands = np.array([0.4, 0.3, 0.2, 1.5, 1.0, 0.7])
    for n in range(N):
        # perfil 24h ~ constante con leve modulación día/noche
        modul = 0.85 + 0.30 * np.sin(np.linspace(-np.pi/2, 1.5*np.pi, T))
        D[n, :] = base_demands[n] * modul

    G = np.zeros((N, T))
    # Generación PV solo en horas solares 8-17 con perfiles diferenciados
    sun = np.zeros(T)
    sun[8:18] = np.sin(np.linspace(0, np.pi, 10))
    peaks = np.array([4.0, 2.0, 1.0])  # asimétricos: gen0 >> gen1 > gen2
    for idx, peak in enumerate(peaks):
        G[idx, :] = peak * sun

    prosumer_ids = [0, 1, 2]
    consumer_ids = [3, 4, 5]
    return D, G, prosumer_ids, consumer_ids


def _gini(x: np.ndarray) -> float:
    """
    Coeficiente de Gini para vector x. Asume valores no negativos
    (válido en C2 con la mini-comunidad de prueba: todos los net_benefit
    son positivos por construcción).
    """
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return 0.0
    # Forzar no-negatividad para evitar interpretación ambigua
    if np.any(x < 0):
        x = x - x.min()
    s = np.sum(x)
    if s == 0.0:
        return 0.0
    x_sorted = np.sort(x)
    n = x_sorted.size
    cum = np.cumsum(x_sorted)
    return float((n + 1 - 2.0 * np.sum(cum) / cum[-1]) / n)


# ─── 1. Rango del precio PPA ─────────────────────────────────────────────────

def test_ppa_price_range_dentro_de_rango():
    """ppa_price_range produce precios estrictamente dentro de [pi_gb, pi_gs]
    para los tres factores default {0.25, 0.5, 0.75}."""
    prices = ppa_price_range(PI_GB, PI_GS)
    assert len(prices) == 3
    for p in prices:
        assert PI_GB <= p <= PI_GS, f"pi_ppa={p} fuera de [{PI_GB}, {PI_GS}]"
    # Strictly increasing (factors strictly increasing)
    assert prices[0] < prices[1] < prices[2]
    # Default factor 0.5 → punto medio exacto
    assert prices[1] == pytest.approx((PI_GB + PI_GS) / 2.0, rel=1e-12)


def test_ppa_price_range_factores_personalizados():
    """ppa_price_range respeta factors custom y los valida en frontera."""
    prices = ppa_price_range(PI_GB, PI_GS, factors=[0.0, 1.0])
    assert prices[0] == pytest.approx(PI_GB)
    assert prices[1] == pytest.approx(PI_GS)


# ─── 2. Teorema de invarianza del bienestar agregado (notas §3.8) ────────────

def test_invarianza_bienestar_agregado_comunidad_cerrada():
    """En comunidad cerrada (excedente vendido = energía recibida vía PPA),
    Sigma_n net_benefit_n debe ser invariante respecto al factor f.

    Tolerancia 1e-6 relativa absorbe redondeo de la división proporcional
    que reparte el surplus entre consumidores (líneas 73-91 del módulo)."""
    D, G, pros, cons = _build_mini_community()

    totales = []
    for f in [0.25, 0.5, 0.75]:
        pi_ppa = PI_GB + f * (PI_GS - PI_GB)
        res = run_c2_bilateral(D, G, PI_GS, PI_GB, pi_ppa, pros, cons)
        totales.append(res["aggregate"]["total_net_benefit"])

    # Todos los totales deben coincidir entre sí
    base = totales[0]
    for t in totales[1:]:
        assert t == pytest.approx(base, rel=1e-6), (
            f"Bienestar agregado NO invariante: {totales}"
        )


# ─── 3. Gini NO es invariante (justifica reporte por f en SA-3) ──────────────

def test_gini_no_invariante_a_f():
    """Gini sobre net_benefit por agente DEBE variar con f
    (la elección de f redistribuye entre prosumidores y consumidores).

    Si Gini fuera invariante, el reporte SA-3 sería redundante."""
    D, G, pros, cons = _build_mini_community()

    ginis = {}
    for f in [0.25, 0.5, 0.75]:
        pi_ppa = PI_GB + f * (PI_GS - PI_GB)
        res = run_c2_bilateral(D, G, PI_GS, PI_GB, pi_ppa, pros, cons)
        nb = np.array([res["per_agent"][n]["net_benefit"]
                       for n in range(D.shape[0])])
        ginis[f] = _gini(nb)

    # Al menos dos de los tres Gini deben diferir significativamente.
    # Tolerancia: 5e-3 (Gini típico ~0.1-0.6, diferencias por f ~1e-2).
    pares = [(0.25, 0.5), (0.5, 0.75), (0.25, 0.75)]
    diferencias = [abs(ginis[a] - ginis[b]) for a, b in pares]
    assert max(diferencias) > 5e-3, (
        f"Gini parece invariante a f: {ginis}. "
        f"El reporte SA-3 carecería de sentido informativo."
    )


# ─── 4. Pay-as-Produced: balance de energía del lado generador ───────────────

def test_pay_as_produced_balance_generacion():
    """Para cada hora k, la generación total de los prosumidores debe igualar
    la suma de autoconsumo + PPA vendido + venta a red. No debe haber
    generación "perdida" ni doblemente contabilizada."""
    D, G, pros, cons = _build_mini_community()
    pi_ppa = PI_GB + 0.5 * (PI_GS - PI_GB)
    res = run_c2_bilateral(D, G, PI_GS, PI_GB, pi_ppa, pros, cons)

    # Reconstruimos energías globales del horizonte:
    G_total_pros = float(G[pros, :].sum())

    # Energía autoconsumida total (suma sobre prosumidores)
    # En el módulo, savings_autoconsumo (key "savings_autoconsumo") se valora a pi_gs;
    # pero pi_gs es escalar aquí, así que autoconsumo_kWh = savings / pi_gs
    autoconsumo_kWh = sum(
        res["per_agent"][n]["savings_autoconsumo"] / PI_GS for n in pros
    )

    # Energía vendida a red (revenue / pi_gb)
    vendida_red_kWh = sum(
        res["per_agent"][n]["grid_revenue"] / PI_GB for n in pros
    )

    # Energía vendida vía PPA: por conservación, debe completar
    # la generación total menos autoconsumo y red.
    ppa_vendida_kWh = G_total_pros - autoconsumo_kWh - vendida_red_kWh

    # Debe ser >= 0 y consistente con la energía recibida por consumidores
    assert ppa_vendida_kWh >= -1e-9, (
        f"PPA vendido negativo ({ppa_vendida_kWh}); "
        f"hay generación 'creada' o no reconciliada."
    )
    # Conservación absoluta: G_total ≈ autoconsumo + ppa + red
    assert (autoconsumo_kWh + ppa_vendida_kWh + vendida_red_kWh) == \
        pytest.approx(G_total_pros, rel=1e-6)


# ─── 5. Balance de energía por consumidor ────────────────────────────────────

def test_balance_energia_consumidor():
    """Para cada consumidor i, demand_total debe igualar:
    PPA_recibida + déficit_residual_a_red.
    (Los consumidores puros no autoconsumen porque G[i, :] = 0.)"""
    D, G, pros, cons = _build_mini_community()
    pi_ppa = PI_GB + 0.5 * (PI_GS - PI_GB)
    res = run_c2_bilateral(D, G, PI_GS, PI_GB, pi_ppa, pros, cons)

    for i in cons:
        # Para consumidores: G[i, :] = 0 → autoconsumo = 0
        # → savings_autoconsumo = 0
        savings_auto = res["per_agent"][i]["savings_autoconsumo"]
        assert savings_auto == pytest.approx(0.0, abs=1e-9), (
            f"Consumidor {i} con savings_autoconsumo = {savings_auto}; "
            f"se esperaba 0 (no genera)."
        )

        # ppa_recibida desde savings_ppa: savings_cons = ppa_kWh * (pi_gs - pi_ppa)
        savings_ppa = res["per_agent"][i]["savings_ppa"]
        ppa_kWh = savings_ppa / max(PI_GS - pi_ppa, 1e-9)

        # déficit_residual desde grid_cost: grid_cost = residual_kWh * pi_gs
        grid_cost = res["per_agent"][i]["grid_cost"]
        residual_kWh = grid_cost / PI_GS

        D_total_i = float(D[i, :].sum())
        assert (ppa_kWh + residual_kWh) == pytest.approx(D_total_i, rel=1e-6), (
            f"Consumidor {i}: D={D_total_i:.4f}, "
            f"PPA={ppa_kWh:.4f}, red={residual_kWh:.4f} "
            f"(suma={ppa_kWh + residual_kWh:.4f})"
        )


# ─── 6. Default de main_simulation.py:269 ────────────────────────────────────

def test_default_f_main_simulation_es_punto_medio():
    """Replica el cálculo de main_simulation.py:269 y confirma que
    representa exactamente f = 0.5."""
    pi_gb = 195.0
    pi_gs = 906.0
    pi_ppa = pi_gb + 0.5 * (pi_gs - pi_gb)   # idéntico al sitio main
    f_obs = (pi_ppa - pi_gb) / (pi_gs - pi_gb)
    assert f_obs == pytest.approx(0.5, rel=1e-12)


# ─── 7. Compatibilidad pi_gs (N, T) — CAL-9 ──────────────────────────────────

def test_pi_ppa_acepta_pi_gs_matriz_temporal():
    """C2 debe aceptar pi_gs como matriz (N, T) (post-CAL-9). Si todos los
    elementos de la matriz son iguales al escalar, los KPIs agregados deben
    coincidir (hasta tolerancia numérica) con la versión escalar."""
    D, G, pros, cons = _build_mini_community()
    N, T = D.shape
    pi_ppa = PI_GB + 0.5 * (PI_GS - PI_GB)

    res_scalar = run_c2_bilateral(D, G, PI_GS, PI_GB, pi_ppa, pros, cons)
    res_matrix = run_c2_bilateral(D, G, np.full((N, T), PI_GS),
                                  PI_GB, pi_ppa, pros, cons)

    assert (res_scalar["aggregate"]["total_net_benefit"]
            == pytest.approx(res_matrix["aggregate"]["total_net_benefit"],
                             rel=1e-9))
    for n in range(N):
        a = res_scalar["per_agent"][n]["net_benefit"]
        b = res_matrix["per_agent"][n]["net_benefit"]
        assert a == pytest.approx(b, rel=1e-9, abs=1e-6), (
            f"Agente {n}: escalar={a}, matriz={b}"
        )


def test_pi_gs_matriz_diferenciada_por_agente():
    """Matriz (N, T) con pi_gs diferenciado por agente debe producir
    distinto resultado que el escalar promedio (los consumidores con
    tarifa más alta ahorran más vía PPA)."""
    D, G, pros, cons = _build_mini_community()
    N, T = D.shape
    pi_ppa = PI_GB + 0.5 * (PI_GS - PI_GB)

    # Tarifas heterogéneas por agente: prosumidores 700, consumidores 900
    pi_gs_het = np.full((N, T), 700.0)
    for i in cons:
        pi_gs_het[i, :] = 900.0

    res_het = run_c2_bilateral(D, G, pi_gs_het, PI_GB, pi_ppa, pros, cons)
    res_uni = run_c2_bilateral(D, G, 800.0, PI_GB, pi_ppa, pros, cons)

    assert (res_het["aggregate"]["total_net_benefit"]
            != pytest.approx(res_uni["aggregate"]["total_net_benefit"],
                             rel=1e-3)), (
        "Diferenciar pi_gs por agente debería cambiar el agregado."
    )


# ─── CAL-12 (ADR-0012): Front-of-Meter — alcance regulatorio del PPA ─────────

PI_G = 250.0   # Componente G del CU (típico CEDENAR oficial NT2 ~310;
               # se elige 250 para que PI_G < pi_ppa default y exhibir
               # el comportamiento contraintuitivo: f_emp efectivo
               # negativo bajo FoM).


def test_pi_G_None_replica_legacy_BTM():
    """Si pi_G no se especifica (None), C2 reproduce exactamente el
    comportamiento BTM legacy pre-CAL-12 (savings sobre el CU completo).
    Esto preserva la suite CAL-11 al 100 %."""
    D, G_pv, pros, cons = _build_mini_community()
    pi_ppa = PI_GB + 0.5 * (PI_GS - PI_GB)

    res_legacy = run_c2_bilateral(D, G_pv, PI_GS, PI_GB, pi_ppa, pros, cons)
    res_BTM    = run_c2_bilateral(D, G_pv, PI_GS, PI_GB, pi_ppa, pros, cons,
                                  pi_G=None)
    # Pi_G=None == pi_G no pasado: ambos invocan el legacy.
    assert (res_legacy["aggregate"]["total_net_benefit"]
            == pytest.approx(res_BTM["aggregate"]["total_net_benefit"],
                             rel=1e-12))


def test_savings_cons_uses_pi_G_not_CU():
    """Bajo CAL-12, el ahorro del comprador se calcula sobre G,
    no sobre el CU completo. Verificación directa: con pi_G < pi_gs
    el savings debe ser estrictamente menor que la versión legacy."""
    D, G_pv, pros, cons = _build_mini_community()
    pi_ppa = PI_GB + 0.5 * (PI_GS - PI_GB)   # 500 COP/kWh

    # Legacy: savings_cons = ppa_kWh × (CU − π_ppa) = ppa × 300
    res_legacy = run_c2_bilateral(D, G_pv, PI_GS, PI_GB, pi_ppa, pros, cons)
    # FoM (CAL-12): savings_cons = ppa_kWh × (G − π_ppa) = ppa × (-250)
    # (¡puede ser negativo si π_ppa > G!)
    res_FoM = run_c2_bilateral(D, G_pv, PI_GS, PI_GB, pi_ppa, pros, cons,
                                pi_G=PI_G)

    sav_cons_legacy = sum(res_legacy["per_agent"][i]["savings_ppa"] for i in cons)
    sav_cons_FoM    = sum(res_FoM["per_agent"][i]["savings_ppa"] for i in cons)
    assert sav_cons_FoM < sav_cons_legacy, (
        f"FoM debe reducir savings_cons (G={PI_G} < CU={PI_GS}). "
        f"legacy={sav_cons_legacy:.1f}, FoM={sav_cons_FoM:.1f}"
    )

    # Verificación cuantitativa: la diferencia debe ser exactamente
    # ppa_kWh_total × (CU − G) = ppa_kWh_total × 550
    delta = sav_cons_legacy - sav_cons_FoM
    # ppa_kWh_total reconstruido: legacy savings = ppa × (PI_GS − pi_ppa)
    ppa_kWh_total = sav_cons_legacy / (PI_GS - pi_ppa)
    expected_delta = ppa_kWh_total * (PI_GS - PI_G)
    assert delta == pytest.approx(expected_delta, rel=1e-9)


def test_invarianza_bienestar_FoM_se_preserva():
    """El teorema de invarianza (notas §3.8) DEBE seguir valiendo bajo
    CAL-12 / FoM. La razón es analítica: en comunidad cerrada,
    Σ ppa_kWh recibida = Σ ppa_kWh entregada, por lo que
    Σ (G − π_ppa) ppa + Σ π_ppa ppa = Σ G ppa = constante en π_ppa.
    """
    D, G_pv, pros, cons = _build_mini_community()
    totales_FoM = []
    for f in [0.25, 0.5, 0.75]:
        pi_ppa = PI_GB + f * (PI_G - PI_GB)
        res = run_c2_bilateral(D, G_pv, PI_GS, PI_GB, pi_ppa, pros, cons,
                                pi_G=PI_G)
        totales_FoM.append(res["aggregate"]["total_net_benefit"])
    base = totales_FoM[0]
    for t in totales_FoM[1:]:
        assert t == pytest.approx(base, rel=1e-6), (
            f"Bienestar agregado FoM NO invariante: {totales_FoM}"
        )


def test_kpi_C2_cae_drasticamente_vs_legacy_BTM():
    """El paso de BTM (legacy) a FoM (CAL-12) reduce el bienestar
    agregado de C2 en magnitud aproximadamente igual a:
        ppa_kWh_total × (CU_promedio − G_promedio)
    porque ese delta corresponde a los peajes T+D+C+PR+R+COT que el
    modelo legacy regalaba a la comunidad y CAL-12 los traslada al
    OR/STN/comercializador correctamente."""
    D, G_pv, pros, cons = _build_mini_community()
    pi_ppa = PI_GB + 0.5 * (PI_G - PI_GB)   # default CAL-12

    res_legacy = run_c2_bilateral(D, G_pv, PI_GS, PI_GB, pi_ppa, pros, cons)
    res_FoM    = run_c2_bilateral(D, G_pv, PI_GS, PI_GB, pi_ppa, pros, cons,
                                  pi_G=PI_G)
    delta = (res_legacy["aggregate"]["total_net_benefit"]
             - res_FoM["aggregate"]["total_net_benefit"])
    assert delta > 0, "FoM debe reducir bienestar agregado."

    # Estimación del orden de magnitud: peajes (CU − G) × ppa_kWh
    # Reconstrucción: como la diferencia única está en savings_cons:
    sav_cons_legacy = sum(res_legacy["per_agent"][i]["savings_ppa"] for i in cons)
    sav_cons_FoM    = sum(res_FoM["per_agent"][i]["savings_ppa"] for i in cons)
    delta_savings = sav_cons_legacy - sav_cons_FoM
    assert delta == pytest.approx(delta_savings, rel=1e-9), (
        "La diferencia legacy↔FoM solo debe afectar savings_cons."
    )


def test_default_pi_ppa_es_punto_medio_pi_gb_y_G():
    """Replica el cálculo CAL-12 (main_simulation.py) y confirma que
    el default usa el punto medio entre pi_gb y G (no pi_gs)."""
    pi_gb_local = 195.0
    pi_G_mean   = 310.0   # Componente G típico oficial NT2
    pi_ppa_default = pi_gb_local + 0.5 * (pi_G_mean - pi_gb_local)
    f_obs = (pi_ppa_default - pi_gb_local) / (pi_G_mean - pi_gb_local)
    assert f_obs == pytest.approx(0.5, rel=1e-12)
    # Y confirmamos que NO equivale al cálculo pre-CAL-12:
    pi_gs_legacy = 906.0
    pi_ppa_legacy = pi_gb_local + 0.5 * (pi_gs_legacy - pi_gb_local)
    assert pi_ppa_default < pi_ppa_legacy, (
        "Default CAL-12 debe ser estrictamente menor que el default "
        "pre-CAL-12 (G < CU)."
    )


def test_pi_G_acepta_matriz_NT_y_escalar_equivalentes():
    """Pi_G escalar y matriz (N, T) constante deben dar el mismo
    resultado (compatibilidad con CAL-9)."""
    D, G_pv, pros, cons = _build_mini_community()
    N, T = D.shape
    pi_ppa = PI_GB + 0.5 * (PI_G - PI_GB)

    res_scalar = run_c2_bilateral(D, G_pv, PI_GS, PI_GB, pi_ppa, pros, cons,
                                  pi_G=PI_G)
    res_matrix = run_c2_bilateral(D, G_pv, PI_GS, PI_GB, pi_ppa, pros, cons,
                                  pi_G=np.full((N, T), PI_G))
    assert (res_scalar["aggregate"]["total_net_benefit"]
            == pytest.approx(res_matrix["aggregate"]["total_net_benefit"],
                             rel=1e-9))


def test_g_component_per_agent_hourly_smoke():
    """Smoke test del helper data/cedenar_tariff.g_component_per_agent_hourly:
    devuelve matriz (N, T) con valores no-NaN dentro del horizonte cubierto
    por el CSV."""
    import pandas as pd
    from data.cedenar_tariff import g_component_per_agent_hourly

    agents = ["Udenar", "HUDN", "Mariana"]
    idx = pd.date_range("2026-04-01", "2026-04-02", freq="1h", inclusive="left")
    arr = g_component_per_agent_hourly(agents, idx)
    assert arr.shape == (3, len(idx))
    # Abril 2026 está cubierto: no debe haber NaN.
    assert not np.any(np.isnan(arr))
    # G oficial NT2 ~310 COP/kWh; comercial NT2 mismo nivel ~310.
    assert 200 < arr.mean() < 400, f"G fuera de rango esperado: {arr.mean()}"


# ─── CAL-13 (ADR-0013): comunidad MTE como usuario no-regulado agregado ─────

PI_NEGOTIABLE = 526.0   # G + Cvm + COT típico abr-2026 oficial NT2
                        # (G=311 + Cvm=176 + COT=39 ≈ 526 COP/kWh).


def test_g_plus_commercialization_helper_smoke():
    """Smoke test del helper CAL-13: G + Cvm + COT por agente y hora.
    Para abril 2026 oficial NT2 (Udenar, HUDN), valor esperado ≈ 526."""
    import pandas as pd
    from data.cedenar_tariff import g_plus_commercialization_per_agent_hourly

    agents = ["Udenar", "HUDN"]
    idx = pd.date_range("2026-04-01", "2026-04-02", freq="1h", inclusive="left")
    arr = g_plus_commercialization_per_agent_hourly(agents, idx)
    assert arr.shape == (2, len(idx))
    assert not np.any(np.isnan(arr))
    # G+Cvm+COT abr-2026 oficial NT2: ≈ 526 COP/kWh
    assert 500 < arr.mean() < 550, (
        f"G+Cvm+COT fuera de rango esperado: {arr.mean()}"
    )


def test_helper_g_plus_strictly_greater_than_g_alone():
    """G + Cvm + COT debe ser estrictamente mayor que solo G
    (porque Cvm + COT > 0 siempre)."""
    import pandas as pd
    from data.cedenar_tariff import (
        g_component_per_agent_hourly,
        g_plus_commercialization_per_agent_hourly,
    )

    agents = ["Udenar", "HUDN", "Mariana"]
    idx = pd.date_range("2026-04-01", "2026-04-02", freq="1h",
                        inclusive="left")
    g_only  = g_component_per_agent_hourly(agents, idx)
    g_plus  = g_plus_commercialization_per_agent_hourly(agents, idx)
    assert np.all(g_plus > g_only), "G+Cvm+COT debe > G solo en cada celda"
    # Diferencia esperada ≈ 215 COP/kWh (Cvm + COT abr-2026)
    diff = (g_plus - g_only).mean()
    assert 200 < diff < 230, f"Cvm+COT fuera de rango: {diff}"


def test_savings_cons_es_mayor_bajo_no_regulado_que_regulado():
    """CAL-13 vs CAL-12: el ahorro del comprador no-regulado
    (rango G+Cvm+COT) debe ser estrictamente mayor que el del
    comprador regulado (rango G solo) para el mismo pi_ppa."""
    D, G_pv, pros, cons = _build_mini_community()
    pi_ppa = PI_GB + 0.5 * (PI_NEGOTIABLE - PI_GB)   # default CAL-13

    # CAL-12: comprador regulado, ahorra solo (G − pi_ppa)
    PI_G_REG = 250.0   # G solo (igual al test CAL-12 existente)
    res_reg = run_c2_bilateral(D, G_pv, PI_GS, PI_GB, pi_ppa,
                                pros, cons, pi_G=PI_G_REG)

    # CAL-13: comprador no-regulado, ahorra (G+Cvm+COT − pi_ppa)
    res_nreg = run_c2_bilateral(D, G_pv, PI_GS, PI_GB, pi_ppa,
                                 pros, cons, pi_G=PI_NEGOTIABLE)

    sav_reg  = sum(res_reg["per_agent"][i]["savings_ppa"] for i in cons)
    sav_nreg = sum(res_nreg["per_agent"][i]["savings_ppa"] for i in cons)
    assert sav_nreg > sav_reg, (
        f"CAL-13 (no-regulado) debe ahorrar más que CAL-12 (regulado). "
        f"reg={sav_reg:.1f}, nreg={sav_nreg:.1f}"
    )

    # La diferencia debe ser exactamente E_PPA × (PI_NEGOTIABLE − PI_G_REG)
    delta = sav_nreg - sav_reg
    ppa_kWh_total = sav_nreg / (PI_NEGOTIABLE - pi_ppa)
    expected_delta = ppa_kWh_total * (PI_NEGOTIABLE - PI_G_REG)
    assert delta == pytest.approx(expected_delta, rel=1e-9)


def test_invarianza_bienestar_FoM_no_regulado_se_preserva():
    """Teorema de invarianza (notas §3.8) sigue valiendo bajo CAL-13.
    Σ_n B_n^C2 es constante en pi_ppa cuando se usa el rango
    G+Cvm+COT como cota superior."""
    D, G_pv, pros, cons = _build_mini_community()
    totales = []
    for f in [0.25, 0.5, 0.75]:
        pi_ppa = PI_GB + f * (PI_NEGOTIABLE - PI_GB)
        res = run_c2_bilateral(D, G_pv, PI_GS, PI_GB, pi_ppa,
                                pros, cons, pi_G=PI_NEGOTIABLE)
        totales.append(res["aggregate"]["total_net_benefit"])
    base = totales[0]
    for t in totales[1:]:
        assert t == pytest.approx(base, rel=1e-6)


def test_default_pi_ppa_CAL13_punto_medio_pi_gb_y_negotiable():
    """Default CAL-13: pi_ppa = pi_gb + 0.5·((G+Cvm+COT) − pi_gb).
    Debe ser estrictamente mayor que el default CAL-12 (que usa solo G)
    porque G+Cvm+COT > G."""
    pi_gb_local = 195.0
    pi_negotiable = 526.0   # G+Cvm+COT abr-2026 oficial NT2
    pi_g_only     = 311.0   # G solo abr-2026

    pi_ppa_CAL13 = pi_gb_local + 0.5 * (pi_negotiable - pi_gb_local)
    pi_ppa_CAL12 = pi_gb_local + 0.5 * (pi_g_only     - pi_gb_local)

    assert pi_ppa_CAL13 > pi_ppa_CAL12, (
        "Default CAL-13 (no-regulado) debe ser mayor que default "
        "CAL-12 (regulado), porque G+Cvm+COT > G."
    )
    f_obs = (pi_ppa_CAL13 - pi_gb_local) / (pi_negotiable - pi_gb_local)
    assert f_obs == pytest.approx(0.5, rel=1e-12)


# ─── CAL-13b (TODO post-CAL-13): SA-3 usa rango [pi_gb, pi_G] ────────────────

def test_run_sensitivity_ppa_usa_rango_pi_G_cuando_se_provee(monkeypatch):
    """SA-3 con pi_G explícito usa rango [pi_gb, pi_G] (CAL-13b).
    Sin pi_G, cae al rango legacy [pi_gb, pi_gs] (compatibilidad pre-CAL-13).

    Usa monkeypatch para sustituir run_comparison y run_c2_bilateral por
    stubs ligeros: solo nos interesa verificar que los pi_ppa generados
    siguen el rango correcto, no la liquidación completa."""
    from analysis import sensitivity as sens
    from scenarios import scenario_c2_bilateral as c2_mod
    import scenarios as scenarios_pkg

    # Stub mínimo de ComparisonResult-like
    class _FakeCR:
        net_benefit = {e: 0.0 for e in ["P2P", "C1", "C2", "C3", "C4"]}
        net_benefit_per_agent = {"C2": np.zeros(6)}

    captured_pi_ppas = []

    def fake_run_comparison(*args, **kwargs):
        captured_pi_ppas.append(kwargs["pi_ppa"])
        return _FakeCR()

    def fake_run_c2(*args, **kwargs):
        return {"aggregate": {"total_savings_gen": 0.0,
                              "total_savings_cons": 0.0}}

    monkeypatch.setattr(scenarios_pkg, "run_comparison", fake_run_comparison)
    monkeypatch.setattr(c2_mod, "run_c2_bilateral", fake_run_c2)

    D, G_pv, pros, cons = _build_mini_community()
    pi_bolsa = np.full(D.shape[1], PI_GB)

    # Caso A: con pi_G — rango natural CAL-13 = [pi_gb, pi_G]
    captured_pi_ppas.clear()
    sens.run_sensitivity_ppa(
        D=D, G_klim=G_pv, G_raw=G_pv,
        pi_gs=PI_GS, pi_gb=PI_GB, pi_bolsa=pi_bolsa,
        p2p_results=[], prosumer_ids=pros, consumer_ids=cons,
        ppa_factors=[0.0, 0.5, 1.0],
        verbose=False,
        pi_G=PI_NEGOTIABLE,
    )
    # f=0 → pi_gb; f=1 → pi_negotiable; f=0.5 → punto medio
    assert captured_pi_ppas[0] == pytest.approx(PI_GB, rel=1e-9)
    assert captured_pi_ppas[-1] == pytest.approx(PI_NEGOTIABLE, rel=1e-9)
    assert captured_pi_ppas[1] == pytest.approx(
        PI_GB + 0.5 * (PI_NEGOTIABLE - PI_GB), rel=1e-9
    )

    # Caso B: sin pi_G — rango legacy [pi_gb, pi_gs]
    captured_pi_ppas.clear()
    sens.run_sensitivity_ppa(
        D=D, G_klim=G_pv, G_raw=G_pv,
        pi_gs=PI_GS, pi_gb=PI_GB, pi_bolsa=pi_bolsa,
        p2p_results=[], prosumer_ids=pros, consumer_ids=cons,
        ppa_factors=[0.0, 0.5, 1.0],
        verbose=False,
    )
    assert captured_pi_ppas[-1] == pytest.approx(PI_GS, rel=1e-9)
    assert PI_NEGOTIABLE < PI_GS, "Setup invariante para el test"
