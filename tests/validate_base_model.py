"""
validate_base_model.py  (v3 — sin DR)
--------------------------------------
Valida que el pipeline sin DR funcione correctamente.
"""

import sys, os, warnings, time
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np

from core.market_prep       import prepare_hour, compute_generation_limit
from core.replicator_sellers import solve_sellers
from core.replicator_buyers  import solve_buyers
from core.ems_p2p            import EMSP2P, AgentParams, GridParams, SolverParams
from scenarios               import run_comparison, print_comparison_report
from data.base_case_data     import (
    get_generation_profiles, get_demand_profiles,
    get_agent_params, get_pde_weights,
    GRID_PARAMS, PGS, PGB,
)


def sep(t): print(f"\n{'='*60}\n{t}\n{'='*60}")


def test1_glim():
    sep("TEST 1: G_klim — solo agente 1 restringido (hora 14)")
    G = get_generation_profiles()
    p = get_agent_params()
    prep = prepare_hour(G[:, 13], get_demand_profiles()[:, 13],
                        p["a"], p["b"], p["c"], PGS)
    for n in range(6):
        tag = "★ LIMITADO" if prep["G_klim"][n] < G[n, 13] - 1e-4 else "  libre"
        print(f"  A{n+1}: G={G[n,13]:.3f}  G_lim={prep['G_klim'][n]:.3f}  {tag}")
    assert prep["G_klim"][0] < G[0, 13] - 1e-4
    print("  Vendedores:", [s+1 for s in prep["seller_ids"]])
    print("  Compradores:", [b+1 for b in prep["buyer_ids"]])
    print("✓ PASADO")


def test2_no_dr():
    sep("TEST 2: Confirmar que NO hay DR — D no se modifica")
    D = get_demand_profiles()
    G = get_generation_profiles()
    p = get_agent_params()
    k = 13
    prep = prepare_hour(G[:, k], D[:, k], p["a"], p["b"], p["c"], PGS)
    assert np.allclose(prep["D"], D[:, k]), "D debe ser idéntica a la entrada"
    print("  D entrada == D en prep_hour: TRUE")
    print("  El pipeline usa D real sin ninguna modificación.")
    print("✓ PASADO")


def test3_sellers_hour14():
    sep("TEST 3: RD vendedores — hora 14")
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


def test4_buyers_hour14():
    sep("TEST 4: RD compradores — precios en [Pgb, Pgs]")
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
    assert np.all(pi >= PGB - 1) and np.all(pi <= PGS + 1)
    print("✓ PASADO")


def test5_full_ems_24h():
    sep("TEST 5: EMS completo 24h (sin DR, paralelo)")
    G = get_generation_profiles()
    D = get_demand_profiles()
    p = get_agent_params()
    t0 = time.time()
    agents = AgentParams(**p); grid = GridParams(**GRID_PARAMS)
    solver = SolverParams(tau=0.001, t_span=(0, 0.005),
                          n_points=150, stackelberg_iters=2, parallel=True)
    ems = EMSP2P(agents, grid, solver)
    results, G_klim = ems.run(D, G)
    dt = time.time() - t0
    active = [r for r in results if r.P_star is not None
              and np.sum(r.P_star) > 1e-4]
    print(f"  Tiempo: {dt:.1f}s")
    print(f"  Horas con mercado: {len(active)}/24")
    print(f"  SC prom: {np.mean([r.SC for r in active]):.3f}")
    print(f"  SS prom: {np.mean([r.SS for r in active]):.3f}")
    print(f"  IE prom: {np.mean([r.IE for r in active]):.4f}")
    print(f"  PS: {np.mean([r.PS for r in active]):.1f}%  "
          f"PSR: {np.mean([r.PSR for r in active]):.1f}%")
    print("✓ PASADO")


def test6_comparison():
    sep("TEST 6: Comparación P2P vs C1–C4")
    G = get_generation_profiles()
    D = get_demand_profiles()
    p = get_agent_params()
    agents = AgentParams(**p); grid = GridParams(**GRID_PARAMS)
    solver = SolverParams(tau=0.001, t_span=(0, 0.005),
                          n_points=150, stackelberg_iters=2, parallel=True)
    ems = EMSP2P(agents, grid, solver)
    results, G_klim = ems.run(D, G)

    cr = run_comparison(
        D=D, G_klim=G_klim, G_raw=G,
        p2p_results=results,
        pi_gs=PGS, pi_gb=PGB,
        pi_bolsa=np.full(24, PGB),
        prosumer_ids=[0,1,2,3], consumer_ids=[4,5],
        pde=get_pde_weights(),
        capacity=np.array([3.0, 4.0, 3.0, 2.0, 0.0, 0.0]),
    )
    print_comparison_report(cr)
    print("✓ PASADO")


if __name__ == "__main__":
    print("\n" + "#"*60)
    print("  VALIDACIÓN — Pipeline sin DR (Brayan Lopez, 2026)")
    print("#"*60)
    for test in [test1_glim, test2_no_dr, test3_sellers_hour14,
                 test4_buyers_hour14, test5_full_ems_24h, test6_comparison]:
        try:
            test()
        except Exception as e:
            import traceback
            print(f"\n✗ {test.__name__}: {e}")
            traceback.print_exc()
    print("\n" + "="*60)
    print("  Validación completada.")
    print("="*60)
