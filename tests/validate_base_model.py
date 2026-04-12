"""
validate_base_model.py  (v4 — con DR, parámetros Chacón)
----------------------------------------------------------
Valida el pipeline completo contra el modelo base publicado en:
  Chacón et al. (2025) "Energy management system in communities with
  P2P markets using game theory and optimization models", MaIE-Udenar.

Tests:
  TEST 1: G_klim — agente 1 restringido (parámetros base)
  TEST 2: DR program — desplazamiento de demanda con alpha>0
  TEST 3: DR program — alpha=0 devuelve D sin cambios
  TEST 4: RD vendedores — hora 14, P_star >= 0
  TEST 5: RD compradores — precios en [pi_gb, pi_gs]
  TEST 6: EMS completo 24h (con DR activo, datos sintéticos)
  TEST 7: Comparación P2P vs C1–C4 (incluye Gini)
  TEST 8: Validación parámetros Chacón Tabla I — G_klim esperados
"""

import sys, os, warnings, time
warnings.filterwarnings("ignore")
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np

from core.market_prep        import prepare_hour, compute_generation_limit
from core.replicator_sellers import solve_sellers
from core.replicator_buyers  import solve_buyers
from core.ems_p2p            import EMSP2P, AgentParams, GridParams, SolverParams
from core.dr_program         import run_dr_program, compute_price_signal
from core.settlement         import gini_index
from scenarios               import run_comparison, print_comparison_report
from data.base_case_data     import (
    get_generation_profiles, get_demand_profiles,
    get_agent_params, get_pde_weights,
    GRID_PARAMS, PGS, PGB,
)


def sep(t): print(f"\n{'='*65}\n{t}\n{'='*65}")


# ─── TEST 1: G_klim ────────────────────────────────────────────────────────────

def test1_glim():
    sep("TEST 1: G_klim — agente 1 restringido en hora 14")
    G = get_generation_profiles()
    p = get_agent_params()
    prep = prepare_hour(G[:, 13], get_demand_profiles()[:, 13],
                        p["a"], p["b"], p["c"], PGS)
    for n in range(6):
        tag = "★ LIMITADO" if prep["G_klim"][n] < G[n, 13] - 1e-4 else "  libre"
        print(f"  A{n+1}: G={G[n,13]:.3f}  G_lim={prep['G_klim'][n]:.3f}  {tag}")
    assert prep["G_klim"][0] < G[0, 13] - 1e-4, "A1 debe estar restringido"
    print("  Vendedores:", [s+1 for s in prep["seller_ids"]])
    print("  Compradores:", [b+1 for b in prep["buyer_ids"]])
    print("✓ PASADO")


# ─── TEST 2: DR program activo (alpha > 0) ─────────────────────────────────────

def test2_dr_active():
    sep("TEST 2: DR program — desplazamiento de demanda con alpha > 0")
    D = get_demand_profiles()
    G = get_generation_profiles()
    p = get_agent_params()

    # Obtener G_klim para todo el horizonte
    N, T = D.shape
    G_klim = np.zeros((N, T))
    for k in range(T):
        G_klim[:, k] = compute_generation_limit(
            G[:, k], p["a"], p["b"], p["c"], PGS)

    pi_k   = compute_price_signal(D, G_klim, PGS, PGB)
    alpha  = p["alpha"]   # [0.20, 0.20, 0.20, 0.20, 0.10, 0.10]
    D_star = run_dr_program(D, G_klim, pi_k, alpha, verbose=True)

    # Verificar conservación por agente: Σ_k Dv_k^n = 0
    Dv = D_star - D
    for n in range(N):
        shift_n = float(np.sum(Dv[n, :]))
        assert abs(shift_n) < 1e-4, f"Agente {n+1}: conservación violada (Σ Dv = {shift_n:.6f})"
        max_shift = alpha[n] * float(np.max(D[n, :]))
        for k in range(T):
            assert abs(Dv[n, k]) <= alpha[n] * D[n, k] + 1e-6, \
                f"Agente {n+1} hora {k}: shift excede alpha*D"

    shift_total = float(np.sum(np.abs(Dv)))
    print(f"  Demanda total desplazada: {shift_total:.4f} kWh")
    print(f"  Conservación por agente: ✓ (Σ_k Dv_k^n ≈ 0 para todo n)")
    print(f"  Límites de flexibilidad: ✓")
    assert shift_total > 1e-6, "Con alpha>0 debería haber desplazamiento"
    print("✓ PASADO")


# ─── TEST 3: DR program inactivo (alpha = 0) ───────────────────────────────────

def test3_dr_inactive():
    sep("TEST 3: DR program — alpha=0 devuelve D sin cambios")
    D = get_demand_profiles()
    G = get_generation_profiles()
    p = get_agent_params()

    N, T = D.shape
    G_klim = np.zeros((N, T))
    for k in range(T):
        G_klim[:, k] = compute_generation_limit(
            G[:, k], p["a"], p["b"], p["c"], PGS)

    pi_k   = compute_price_signal(D, G_klim, PGS, PGB)
    alpha0 = np.zeros(N)
    D_star = run_dr_program(D, G_klim, pi_k, alpha0)

    assert np.allclose(D_star, D, atol=1e-10), \
        "Con alpha=0, D_star debe ser idéntica a D"
    print("  alpha=0: D_star == D_base  ✓")
    print("  Equivalente a datos reales donde D es insumo fijo observado.")
    print("✓ PASADO")


# ─── TEST 4: RD vendedores ─────────────────────────────────────────────────────

def test4_sellers_hour14():
    sep("TEST 4: RD vendedores — hora 14, P_star >= 0")
    G = get_generation_profiles()
    D = get_demand_profiles()
    p = get_agent_params()
    prep = prepare_hour(G[:, 13], D[:, 13], p["a"], p["b"], p["c"], PGS)
    sids = prep["seller_ids"]; bids = prep["buyer_ids"]
    G_net_j = prep["G_net"][sids]; D_net_i = prep["D_net"][bids]
    a_j = p["a"][sids]; b_j = p["b"][sids]
    P = solve_sellers(np.full(len(bids), PGB), G_net_j, D_net_i, a_j, b_j,
                      tau=0.001, t_span=(0, 0.005), n_points=150)
    print(f"  P_star (J×I):\n{np.round(P, 4)}")
    assert np.all(P >= -1e-6), "P_star debe ser >= 0"
    print("✓ PASADO")


# ─── TEST 5: RD compradores ────────────────────────────────────────────────────

def test5_buyers_hour14():
    sep("TEST 5: RD compradores — precios en [pi_gb, pi_gs]")
    G = get_generation_profiles()
    D = get_demand_profiles()
    p = get_agent_params()
    prep = prepare_hour(G[:, 13], D[:, 13], p["a"], p["b"], p["c"], PGS)
    sids = prep["seller_ids"]; bids = prep["buyer_ids"]
    G_net_j = prep["G_net"][sids]; D_net_i = prep["D_net"][bids]
    a_j = p["a"][sids]; b_j = p["b"][sids]
    P = solve_sellers(np.full(len(bids), PGB), G_net_j, D_net_i, a_j, b_j,
                      tau=0.001, t_span=(0, 0.005), n_points=150)
    pi = solve_buyers(P, a_j, b_j, p["etha"][bids],
                      pi_gs=PGS, pi_gb=PGB,
                      tau=0.001, t_span=(0, 0.005), n_points=150)
    print(f"  pi_star: {np.round(pi, 2)}")
    assert np.all(pi >= PGB - 1) and np.all(pi <= PGS + 1), \
        f"Precios fuera de rango [{PGB}, {PGS}]"
    print("✓ PASADO")


# ─── TEST 6: EMS completo con DR ───────────────────────────────────────────────

def test6_full_ems_with_dr():
    sep("TEST 6: EMS completo 24h CON DR (alpha > 0)")
    G = get_generation_profiles()
    D = get_demand_profiles()
    p = get_agent_params()

    t0 = time.time()
    agents = AgentParams(**p)   # incluye alpha=[0.20, 0.20, 0.20, 0.20, 0.10, 0.10]
    grid   = GridParams(**GRID_PARAMS)
    solver = SolverParams(tau=0.001, t_span=(0, 0.005),
                          n_points=150, stackelberg_iters=2, parallel=True)
    ems = EMSP2P(agents, grid, solver)
    results, G_klim, D_star = ems.run(D, G, verbose_dr=True)
    dt = time.time() - t0

    active = [r for r in results if r.P_star is not None
              and np.sum(r.P_star) > 1e-4]

    # Verificar que DR cambió la demanda
    dr_shifted = not np.allclose(D_star, D, atol=1e-6)
    print(f"  Tiempo: {dt:.1f}s")
    print(f"  DR desplazó demanda: {'Sí' if dr_shifted else 'No (alpha=0)'}")
    print(f"  Horas con mercado P2P: {len(active)}/24")
    print(f"  SC prom:  {np.mean([r.SC for r in active]):.3f}")
    print(f"  SS prom:  {np.mean([r.SS for r in active]):.3f}")
    print(f"  IE prom:  {np.mean([r.IE for r in active]):.4f}")
    print(f"  PS:  {np.mean([r.PS for r in active]):.1f}%  "
          f"PSR: {np.mean([r.PSR for r in active]):.1f}%")
    print("✓ PASADO")


# ─── TEST 7: Comparación con Gini ─────────────────────────────────────────────

def test7_comparison_with_gini():
    sep("TEST 7: Comparación P2P vs C1–C4 con Gini")
    G = get_generation_profiles()
    D = get_demand_profiles()
    p = get_agent_params()
    agents = AgentParams(**p)
    grid   = GridParams(**GRID_PARAMS)
    solver = SolverParams(tau=0.001, t_span=(0, 0.005),
                          n_points=150, stackelberg_iters=2, parallel=True)
    ems = EMSP2P(agents, grid, solver)
    results, G_klim, D_star = ems.run(D, G)

    cr = run_comparison(
        D=D_star, G_klim=G_klim, G_raw=G,
        p2p_results=results,
        pi_gs=PGS, pi_gb=PGB,
        pi_bolsa=np.full(24, PGB),
        prosumer_ids=[0,1,2,3], consumer_ids=[4,5],
        pde=get_pde_weights(),
        capacity=np.array([3.0, 4.0, 3.0, 2.0, 0.0, 0.0]),
    )
    print_comparison_report(cr)

    # Verificar que Gini fue calculado para todos los escenarios
    assert len(cr.gini) == 5, f"Gini debe existir para 5 escenarios, hay {len(cr.gini)}"
    for esc in ["P2P", "C1", "C2", "C3", "C4"]:
        g = cr.gini[esc]
        assert 0.0 <= g <= 1.0, f"Gini {esc} fuera de [0,1]: {g}"
        print(f"  Gini {esc}: {g:.4f}  ✓")
    print("✓ PASADO")


# ─── TEST 8: Validación parámetros Chacón Tabla I ─────────────────────────────

def test8_chacon_params_validation():
    """
    Valida el cálculo de G_klim con los parámetros EXACTOS de la Tabla I
    del artículo de Chacón et al. (2025).

    Tabla I: Cost parameters for the EC
      Agent 1: a=2.166, b=1243.80, c=4.5   (no renovable, mayor costo)
      Agent 2: a=0.420, b=194.76,  c=1.2   (microgrid solar+viento)
      Agent 3: a=0.000, b=286.06,  c=3.5   (solo viento)
      Agent 4: a=0.000, b=225.20,  c=10.2  (solo PV)

    Comportamiento esperado (Chacón §IV-A):
      - Agente 1 es el único limitado por G_klim (mayor costo de generación).
      - Agentes 2-4 (a=0 o bajo): G_klim = G (sin restricción).
    """
    sep("TEST 8: Parámetros exactos Chacón Tabla I — comportamiento G_klim")

    # ── Parámetros exactos de la Tabla I de Chacón et al. (2025) ────────────
    # (El código usa c=0 en vez de c>0, lo que cambia ligeramente el umbral)
    a_ch = np.array([2.166, 0.420, 0.000, 0.000])
    b_ch = np.array([1243.80, 194.76, 286.06, 225.20])
    c_ch_paper = np.array([4.5, 1.2, 3.5, 10.2])   # Tabla I del paper
    c_ch_code  = np.zeros(4)                          # usado en base_case_data.py

    pi_gs_base = 1250.0   # PGS del código (no 1500)

    print("  Parámetros Tabla I Chacón et al. (2025):")
    print(f"  {'Agente':<6} {'a_n':>8} {'b_n':>10} {'c_paper':>9} {'c_code':>7}")
    for n in range(4):
        print(f"  A{n+1:<5} {a_ch[n]:>8.3f} {b_ch[n]:>10.2f} "
              f"{c_ch_paper[n]:>9.2f} {c_ch_code[n]:>7.2f}")

    # ── Test A: con c=0 (código) y pi_gs=1250, agente 1 DEBE estar restringido ─
    # Discriminante: (b - pi_gs)² - 4ac = (1243.80 - 1250)² - 0 = 38.44 > 0
    # Raíz: ≈ 2.84 kW → para G=4 > raíz → G_klim = raíz < G
    G_test = np.array([4.0, 3.0, 2.5, 1.5])
    G_klim_code = compute_generation_limit(G_test, a_ch, b_ch, c_ch_code, pi_gs_base)

    print(f"\n  [c=0 (código), pi_gs={pi_gs_base:.0f}]")
    print(f"  {'Agente':<10} {'G_bruta':>10} {'G_klim':>10} {'Estado':>15} "
          f"{'Costo@G':>12} {'pi_gs*G':>10}")
    for n in range(4):
        gn = G_test[n]
        costo = a_ch[n]*gn**2 + b_ch[n]*gn + c_ch_code[n]
        pi_g  = pi_gs_base * gn
        limitado = "★ LIMITADO" if G_klim_code[n] < gn - 1e-4 else "  libre"
        print(f"  A{n+1:<9} {gn:>10.3f} {G_klim_code[n]:>10.3f} {limitado:>15} "
              f"{costo:>12.2f} {pi_g:>10.2f}")

    assert G_klim_code[0] < G_test[0] - 1e-4, \
        "Agente 1 (c=0, pi_gs=1250): debe estar restringido (costo≥ingreso)"
    print("  Agente 1 restringido (c=0, pi_gs=1250): ✓")

    # ── Test B: con c exacto del paper y pi_gs=1250, agente 1 SIEMPRE restringido ─
    # disc = (1243.80 - 1250)² - 4×2.166×4.5 = 38.44 - 38.99 = -0.55 < 0
    # → G_klim = 0 para toda G
    G_klim_paper = compute_generation_limit(G_test, a_ch, b_ch, c_ch_paper, pi_gs_base)
    print(f"\n  [c=paper (c_1=4.5), pi_gs={pi_gs_base:.0f}]")
    print(f"  A1: disc=(1243.80-1250)²-4×2.166×4.5 = {(1243.80-1250)**2 - 4*2.166*4.5:.3f} < 0")
    print(f"  → G_klim[0] = {G_klim_paper[0]:.4f} (siempre 0 cuando disc<0)")
    assert G_klim_paper[0] == 0.0, "Con parámetros exactos del paper, G_klim[0]=0"
    print("  Agente 1 con c=4.5: G_klim=0 (costo siempre > ingreso): ✓")

    # ── Nota de documentación ─────────────────────────────────────────────────
    print("\n  NOTA: El código usa c=0 (simplificación) en lugar de c=4.5 del paper.")
    print("        Ambas versiones restringen correctamente el agente 1 de mayor costo.")
    print("        Diferencia: c=0 → G_klim=2.84 kW; c=4.5 → G_klim=0 kW a pi_gs=1250.")

    # Test adicional: índice de Gini
    beneficios = np.array([100.0, 80.0, 60.0, 40.0, 0.0, 0.0])
    g = gini_index(beneficios)
    print(f"\n  Gini test [100,80,60,40,0,0]: {g:.4f}  (esperado ≈ 0.30-0.40)")
    assert 0.0 < g < 1.0, "Gini fuera de rango"

    # Verificar caso equitativo
    g_eq = gini_index(np.array([50.0, 50.0, 50.0, 50.0]))
    print(f"  Gini equitativo [50,50,50,50]: {g_eq:.4f}  (esperado = 0.0)")
    assert g_eq < 1e-10, "Distribución equitativa debe tener Gini=0"

    print("✓ PASADO")


# ─── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "#"*65)
    print("  VALIDACIÓN — Pipeline EMS P2P con DR (Brayan Lopez, 2026)")
    print("  Referencia: Chacón et al. (2025), MaIE-Udenar")
    print("#"*65)

    tests = [
        test1_glim,
        test2_dr_active,
        test3_dr_inactive,
        test4_sellers_hour14,
        test5_buyers_hour14,
        test6_full_ems_with_dr,
        test7_comparison_with_gini,
        test8_chacon_params_validation,
    ]

    passed, failed = 0, []
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            import traceback
            print(f"\n✗ {test.__name__}: {e}")
            traceback.print_exc()
            failed.append(test.__name__)

    print("\n" + "="*65)
    print(f"  Resultado: {passed}/{len(tests)} tests pasados")
    if failed:
        print(f"  Fallidos: {', '.join(failed)}")
    else:
        print("  Todos los tests pasados ✓")
    print("="*65)
