"""
plot_price_curves_equilibrio.py — Curvas de equilibrio de precios π_i(t)
=========================================================================
Réplica de las figuras de convergencia de precios del modelo original
(Chacón et al. 2025, Figs. 9-11 / JoinFinal.m): trayectorias continuas del
solver ACOPLADO (CAL-34, réplica de ode15s en JoinFinal.m:139) para tres
horas representativas — escasez (π→π_gs), interior (negociación visible) y
exceso (π bajo). Las cotas [π_gb, π_gs] van como líneas de referencia y el
endpoint de la alternancia de producción como marcador (CAL-7/CAL-38: deben
coincidir en marginales; en π se aprecia la "coordenada lenta", Capa 9).

Uso:
    python scripts/plot_price_curves_equilibrio.py            # SYN (caso original)
    python scripts/plot_price_curves_equilibrio.py --dataset COB-M1   # real (server)

Salida: outputs/fig_curvas_precio_equilibrio_<ds>.png/.pdf (+ CSV sibling).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))), "scripts"))
from smoke_common import (   # noqa: E402
    ROOT, load_dataset, make_solver, run_ems_cached, active_hours,
    setup_stdout_utf8,
)

import numpy as np                                          # noqa: E402


def _select_hours(results, gr):
    """(escasez, interior, exceso) entre las horas activas."""
    act = active_hours(results)
    band = gr.pi_gs - gr.pi_gb

    def deficit(k):
        r = results[k]
        return sum(r.D_k[i] - r.G_klim_k[i] for i in r.buyer_ids)

    def surplus(k):
        r = results[k]
        return sum(r.G_klim_k[j] - r.D_k[j] for j in r.seller_ids)

    def interiority(k):
        pi = results[k].pi_star
        return float(np.max(np.minimum(pi - gr.pi_gb, gr.pi_gs - pi))) / band

    h_esc = max(act, key=lambda k: deficit(k) - surplus(k))
    h_int = max(act, key=interiority)
    h_exc = max(act, key=lambda k: surplus(k) - deficit(k))
    return list(dict.fromkeys([h_esc, h_int, h_exc]))


def main():
    setup_stdout_utf8()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="SYN")
    args = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from core.coupled_ode_convergence import solve_coupled_for_hour

    ds = load_dataset(args.dataset)
    gr, ag = ds["grid"], ds["agents"]
    results, _, _ = run_ems_cached(ds, make_solver())
    hours = _select_hours(results, gr)
    labels = ["escasez", "interior", "exceso"][:len(hours)]
    print(f"  horas seleccionadas ({args.dataset}): "
          f"{dict(zip(labels, hours))}")

    fig, axes = plt.subplots(1, len(hours), figsize=(4.2 * len(hours), 3.4),
                             sharey=True)
    axes = np.atleast_1d(axes)
    rows = []
    for ax, k, lab in zip(axes, hours, labels):
        r = results[k]
        G_net = np.array([r.G_klim_k[j] - r.D_k[j] for j in r.seller_ids])
        D_net = np.array([r.D_k[i] - r.G_klim_k[i] for i in r.buyer_ids])
        cpl = solve_coupled_for_hour(
            G_net_j=G_net, D_net_i=D_net,
            a_j=ag.a[r.seller_ids], b_j=ag.b[r.seller_ids],
            lam_j=ag.lam[r.seller_ids], theta_j=ag.theta[r.seller_ids],
            G_klim_i=r.G_klim_k[r.buyer_ids],
            lam_i=ag.lam[r.buyer_ids], theta_i=ag.theta[r.buyer_ids],
            etha_i=ag.etha[r.buyer_ids],
            pi_gs=gr.pi_gs, pi_gb=gr.pi_gb,
            tau_sellers=0.001, tau_buyers=0.01,
            t_span=(0.0, 0.04), n_points=400, method="LSODA")
        for i_idx, i in enumerate(r.buyer_ids):
            name = ds["names"][i] if i < len(ds["names"]) else f"A{i+1}"
            ax.plot(cpl.t, np.clip(cpl.pi_t[i_idx], gr.pi_gb, gr.pi_gs),
                    lw=1.4, label=name)
            ax.plot(cpl.t[-1], float(r.pi_star[i_idx]), "kx", ms=6)
            for t_, p_ in zip(cpl.t, cpl.pi_t[i_idx]):
                rows.append((lab, k, name, float(t_), float(p_)))
        ax.axhline(gr.pi_gs, color="gray", ls="--", lw=0.8)
        ax.axhline(gr.pi_gb, color="gray", ls="--", lw=0.8)
        ax.set_title(f"h{k} ({lab})", fontsize=10)
        ax.set_xlabel("Tiempo [s]")
        ax.legend(fontsize=7)
    axes[0].set_ylabel(r"$\pi_i(t)$ [COP/kWh]")
    fig.suptitle("Convergencia del precio de equilibrio — solver acoplado "
                 "(réplica JoinFinal.m); × = endpoint alternancia",
                 fontsize=10)
    fig.tight_layout()

    base = os.path.join(ROOT, "outputs",
                        f"fig_curvas_precio_equilibrio_{args.dataset}")
    fig.savefig(base + ".png", dpi=200)
    fig.savefig(base + ".pdf")
    import csv
    with open(base + ".csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["regimen", "hora", "comprador", "t_s", "pi_cop_kwh"])
        w.writerows(rows)
    print(f"  → {base}.png/.pdf/.csv")


if __name__ == "__main__":
    main()
