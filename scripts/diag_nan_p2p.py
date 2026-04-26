"""Diagnóstico: localiza la fuente del NaN en net_benefit['P2P']
en el análisis de subperíodos sobre 5160 h."""
import sys, os, warnings
warnings.filterwarnings("ignore")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
from core.ems_p2p import AgentParams, GridParams, SolverParams, EMSP2P
from data.xm_data_loader import MTEDataLoader
from data.base_case_data import GRID_PARAMS_REAL
from data.xm_prices import get_b_for_real_data
from scenarios.scenario_c4_creg101072 import compute_pde_weights
from analysis.subperiod import SUB_PERIODS
import copy

def main():
    import multiprocessing; multiprocessing.freeze_support()
    mte_root = os.environ.get("MTE_ROOT", os.path.join(ROOT, "MedicionesMTE_v3"))
    loader = MTEDataLoader(mte_root)
    D, G, idx = loader.load(verbose=False)
    N, T = D.shape
    print(f"D shape: {D.shape}, G shape: {G.shape}")
    print(f"NaN en D? {np.isnan(D).any()} · NaN en G? {np.isnan(G).any()}")
    print(f"Min/Max D: {np.nanmin(D):.3f}/{np.nanmax(D):.3f}")
    print(f"Min/Max G: {np.nanmin(G):.3f}/{np.nanmax(G):.3f}")

    names = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"][:N]
    agents = AgentParams(N=N, a=np.zeros(N), b=get_b_for_real_data(N, names),
                         c=np.full(N,1.2), lam=np.full(N,100.0),
                         theta=np.full(N,0.5), etha=np.full(N,0.1),
                         alpha=np.zeros(N))
    grid = GridParams(**GRID_PARAMS_REAL)
    solver = SolverParams(stackelberg_iters=2, parallel=True)

    # Reproducir primer subperíodo: Laborable-Jul (d_factor=1.00, pi_gb=133)
    label = "Laborable-Jul"
    params = SUB_PERIODS[label]
    df, pgb = params["demand_factor"], params["pi_gb"]
    D_sp = D * df; G_sp = G.copy()
    grid_sp = copy.copy(grid); grid_sp.pi_gb = pgb

    print(f"\n[{label}] d_factor={df}, pi_gb={pgb}")
    print(f"NaN en D_sp? {np.isnan(D_sp).any()} · NaN en G_sp? {np.isnan(G_sp).any()}")

    # Correr EMS
    print("Corriendo EMS...")
    ems = EMSP2P(agents, grid_sp, solver)
    results, G_klim, _ = ems.run(D_sp, G_sp)

    # Chequear NaN en resultados horarios
    nan_P = sum(1 for r in results if r.P_star is not None and np.isnan(r.P_star).any())
    nan_pi = sum(1 for r in results if r.pi_star is not None and np.isnan(r.pi_star).any())
    active = [r for r in results if r.P_star is not None and np.sum(r.P_star) > 1e-4]
    print(f"Horas con P_star NaN: {nan_P}/{len(results)}")
    print(f"Horas con pi_star NaN: {nan_pi}/{len(results)}")
    print(f"Horas activas: {len(active)}/{len(results)}")

    # Encontrar primera hora con NaN
    for r in results:
        if r.P_star is not None and np.isnan(r.P_star).any():
            print(f"\n  Primera hora con NaN en P_star: k={r.k}")
            print(f"    P_star shape: {r.P_star.shape}")
            print(f"    P_star: {r.P_star}")
            print(f"    pi_star: {r.pi_star}")
            print(f"    seller_ids: {r.seller_ids}, buyer_ids: {r.buyer_ids}")
            print(f"    G_klim_k: {r.G_klim_k}")
            print(f"    D_k: {r.D_k}")
            break
        if r.pi_star is not None and np.isnan(r.pi_star).any():
            print(f"\n  Primera hora con NaN en pi_star: k={r.k}")
            print(f"    pi_star: {r.pi_star}")
            print(f"    P_star: {r.P_star}")
            print(f"    seller_ids: {r.seller_ids}, buyer_ids: {r.buyer_ids}")
            break

    # Si no hay NaN horario, el problema es acumulación
    if nan_P == 0 and nan_pi == 0:
        # Replicar _p2p_monetary_benefit paso a paso
        print("\nSin NaN horario. Probando acumulación...")
        pi_gs = GRID_PARAMS_REAL["pi_gs"]
        net = np.zeros(N)
        for r in results:
            if r.P_star is None:
                continue
            for idx_j, j in enumerate(r.seller_ids):
                income = float(np.dot(r.pi_star, r.P_star[idx_j, :])) if r.pi_star is not None else 0
                baseline = float(np.sum(r.P_star[idx_j, :])) * pgb
                delta = income - baseline
                if np.isnan(delta) or np.isinf(delta):
                    print(f"  Vendedor j={j} k={r.k}: income={income} baseline={baseline} Δ={delta}")
                    print(f"    pi_star={r.pi_star} P_star[j,:]={r.P_star[idx_j,:]}")
                    return
                net[j] += delta
            for idx_i, i in enumerate(r.buyer_ids):
                received = float(np.sum(r.P_star[:, idx_i]))
                paid = r.pi_star[idx_i] * received if r.pi_star is not None else received * pi_gs
                delta = received * pi_gs - paid
                if np.isnan(delta) or np.isinf(delta):
                    print(f"  Comprador i={i} k={r.k}: received={received} paid={paid} Δ={delta}")
                    print(f"    pi_star[i]={r.pi_star[idx_i]}")
                    return
                net[i] += delta
        print(f"  Después de mercado: net={net}")

        prosumer_ids = [n for n in range(N) if np.maximum(G.mean(axis=1),0)[n] > 1e-6]
        for n in prosumer_ids:
            for k in range(T):
                auto = min(G_klim[n, k], D_sp[n, k])
                if np.isnan(auto):
                    print(f"  Autoconsumo n={n} k={k}: G_klim={G_klim[n,k]} D={D_sp[n,k]}")
                    return
                net[n] += auto * pi_gs
        print(f"  Final net por agente: {net}")
        print(f"  Suma: {np.sum(net)}")

if __name__ == "__main__":
    main()
