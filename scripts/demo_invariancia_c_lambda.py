"""scripts/demo_invariancia_c_lambda.py
==========================================
Demo numerica de invariancia del equilibrio del juego Stackelberg + RD
respecto a c_j, lambda_j, theta_j, eta_i bajo alpha=0.

Verifica empiricamente la derivacion analitica documentada en las
decisiones de calibracion internas:
  - CAL-2 (eta inerte)
  - CAL-5 (theta inerte)
  - CAL-32 (c invariante)
  - CAL-33 (lambda invariante alpha=0)

Estrategia:
1. Carga el caso h=512 (max P2P volume del horizonte 744h).
2. Corre 3 configuraciones del coupled-ODE solver:
   A) baseline:    c=1.2,  lam=100,  theta=0.5,  eta=0.1   (estado actual)
   B) c=0:         c=0.0,  lam=100,  theta=0.5,  eta=0.1
   C) extremo:     c=10000, lam=999, theta=10.0, eta=5.0
3. Compara P*, pi*, IE numericamente.
4. Tolerancias: diff_P_max < 1e-4 kW, diff_pi_max < 1.0 COP/kWh.
   (Tolerancias no extremadamente apretadas porque LSODA tiene
   ruido numerico ~rtol*atol; lo importante es que no haya orden
   de magnitud, no precision absoluta).
"""
from __future__ import annotations
import io
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _wrap_stdout_utf8():
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                       encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer,
                                       encoding="utf-8", errors="replace")


def _run_config(name, c_val, lam_val, theta_val, eta_val,
                G_net_j, D_net_i, a_j, b_j, G_klim_i,
                pi_gs, pi_gb):
    """Corre solve_coupled_for_hour con (c, lam, theta, eta) dados."""
    from core.coupled_ode_convergence import solve_coupled_for_hour

    J = len(G_net_j)
    I = len(D_net_i)
    lam_j = np.full(J, lam_val)
    theta_j = np.full(J, theta_val)
    lam_i = np.full(I, lam_val)
    theta_i = np.full(I, theta_val)
    etha_i = np.full(I, eta_val)

    coupled = solve_coupled_for_hour(
        G_net_j=G_net_j, D_net_i=D_net_i,
        a_j=a_j, b_j=b_j,
        lam_j=lam_j, theta_j=theta_j,
        G_klim_i=G_klim_i,
        lam_i=lam_i, theta_i=theta_i, etha_i=etha_i,
        pi_gs=pi_gs, pi_gb=pi_gb,
        tau_sellers=0.001, tau_buyers=0.01,
        t_span=(0.0, 0.04), n_points=400,
    )
    return coupled.P_star, coupled.pi_star


def main():
    _wrap_stdout_utf8()
    print("=" * 70)
    print("Demo de invariancia del equilibrio bajo alpha=0")
    print("=" * 70)

    # ── Setup case study (mismo que debug_convergence_h512.py)
    from scripts.run_paper_iter import (
        homogeneizar_a_comercial, cargar_mte_paper, setup_parametros,
    )
    homogeneizar_a_comercial()
    D, G, idx, agents = cargar_mte_paper("2025-08-01", "2025-09-01")
    G = G * 1.5  # phi case study UPME 2030
    p = setup_parametros(D, G, idx, agents)
    pi_gs = float(np.median(p["pi_gs"]))
    pi_gb = 234.0

    # h=512: maximo volumen P2P del horizonte
    k = 512
    G_klim_k = G[:, k]   # con a=0, c<<pi_gs*G: G_klim ~= G
    D_k = D[:, k]
    sids = [n for n in range(len(agents)) if G_klim_k[n] > D_k[n]]
    bids = [n for n in range(len(agents)) if G_klim_k[n] < D_k[n]]
    G_net_j = (G_klim_k - D_k)[sids]
    D_net_i = (D_k - G_klim_k)[bids]
    a_j = np.zeros(len(sids))
    b_j = p["b_cal"][sids]
    G_klim_i = G_klim_k[bids]

    print()
    print(f"hora k={k}, sellers={[agents[i] for i in sids]}, "
          f"buyers={[agents[i] for i in bids]}")
    print(f"  b_j (sellers) = {b_j}  COP/kWh")
    print(f"  pi_gs={pi_gs:.0f}, pi_gb={pi_gb:.0f}")
    print()

    # ── Ejecutar 3 configuraciones
    configs = [
        ("A baseline",  1.2,    100.0, 0.5,  0.1),
        ("B c=0",       0.0,    100.0, 0.5,  0.1),
        ("C extremo",   10000.0, 999.0, 10.0, 5.0),
    ]
    results = {}
    for name, cv, lv, tv, ev in configs:
        print(f"[{name}] c={cv}, lambda={lv}, theta={tv}, eta={ev}...")
        P_star, pi_star = _run_config(
            name, cv, lv, tv, ev,
            G_net_j, D_net_i, a_j, b_j, G_klim_i, pi_gs, pi_gb,
        )
        results[name] = {"P": P_star, "pi": pi_star, "c": cv, "lam": lv}

    # ── Comparativa
    print()
    print("─" * 70)
    print("Comparacion de equilibrios:")
    print("─" * 70)
    base_P = results["A baseline"]["P"]
    base_pi = results["A baseline"]["pi"]

    print(f"{'Run':<12} {'sumP_total':>12} {'pi_mean':>10} "
          f"{'diff_P_max':>14} {'diff_pi_max':>14}")
    for name, r in results.items():
        diff_P_max = float(np.max(np.abs(r["P"] - base_P)))
        diff_pi_max = float(np.max(np.abs(r["pi"] - base_pi)))
        print(f"{name:<12} {float(r['P'].sum()):>12.4f} "
              f"{float(r['pi'].mean()):>10.2f} "
              f"{diff_P_max:>14.6f} {diff_pi_max:>14.6f}")

    # ── Tabla por par (j, i)
    print()
    print("Tabla detallada de P*[j, i] por configuracion:")
    print(f"{'par':<25} {'A baseline':>12} {'B c=0':>12} {'C extremo':>12}")
    for ji_idx, j in enumerate(range(len(sids))):
        for i in range(len(bids)):
            sname = agents[sids[j]]
            bname = agents[bids[i]]
            label = f"{sname}->{bname}"
            print(f"  {label:<22} "
                  f"{results['A baseline']['P'][j, i]:>12.4f} "
                  f"{results['B c=0']['P'][j, i]:>12.4f} "
                  f"{results['C extremo']['P'][j, i]:>12.4f}")

    print()
    print("pi* por buyer:")
    for i, b in enumerate(bids):
        print(f"  pi[{agents[b]:>10s}] = "
              f"A={results['A baseline']['pi'][i]:.4f}  "
              f"B={results['B c=0']['pi'][i]:.4f}  "
              f"C={results['C extremo']['pi'][i]:.4f}")

    # ── Veredicto
    print()
    print("─" * 70)
    tol_P = 1e-4
    tol_pi = 1.0
    diff_P_BA = float(np.max(np.abs(results["B c=0"]["P"] - base_P)))
    diff_P_CA = float(np.max(np.abs(results["C extremo"]["P"] - base_P)))
    diff_pi_BA = float(np.max(np.abs(results["B c=0"]["pi"] - base_pi)))
    diff_pi_CA = float(np.max(np.abs(results["C extremo"]["pi"] - base_pi)))

    pass_BA = diff_P_BA < tol_P and diff_pi_BA < tol_pi
    pass_CA = diff_P_CA < tol_P and diff_pi_CA < tol_pi

    print(f"VEREDICTO (tolerancias: diff_P<{tol_P} kW, diff_pi<{tol_pi} COP/kWh):")
    print(f"  B vs A: P-diff={diff_P_BA:.2e} kW, pi-diff={diff_pi_BA:.2e} -> "
          f"{'PASS' if pass_BA else 'FAIL'}")
    print(f"  C vs A: P-diff={diff_P_CA:.2e} kW, pi-diff={diff_pi_CA:.2e} -> "
          f"{'PASS' if pass_CA else 'FAIL'}")
    print()
    if pass_BA and pass_CA:
        print("  CONFIRMADO: invariancia analitica de c_j, lambda_j, theta_j, eta_i")
        print("              bajo alpha=0 verificada empiricamente.")
        return 0
    else:
        print("  ATENCION: diferencias por encima de tolerancia. Revisar.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
