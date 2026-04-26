"""
Genera una figura limpia con los perfiles promedio diarios de demanda y
generacion por institucion, usando los datos post-refactor de
preprocesamiento (Actividad 3.1 - data/preprocessing.py).

Salida: graficas/fig_perfiles_DG_actualizados.png
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np

from data.xm_data_loader import AGENTS, daily_profiles
from data.preprocessing import build_demand_generation


def main():
    repo = Path(__file__).resolve().parents[1]
    mte_root = os.environ.get("MTE_ROOT", str(repo / "MedicionesMTE_v3"))
    t_start = os.environ.get("MTE_T_START")  # None -> usa default de xm_data_loader
    t_end = os.environ.get("MTE_T_END")
    print(f"Cargando: {mte_root}  horizonte={t_start or 'default'} -> {t_end or 'default'}")
    D, G, idx = build_demand_generation(
        mte_root, t_start=t_start, t_end=t_end, verbose=False,
    )

    Da, Ga = daily_profiles(D, G, idx)
    hours = np.arange(24)

    fig, axes = plt.subplots(3, 2, figsize=(11, 10), sharex=True)
    axes = axes.flatten()
    fig.suptitle(
        "Perfiles promedio diarios D y G - datos MTE post-refactor (Actividad 3.1)",
        fontsize=12, fontweight="bold",
    )

    color_d = "#378ADD"
    color_g = "#D85A30"

    for n, agent in enumerate(AGENTS):
        ax = axes[n]
        d_mean = float(Da[n].mean())
        g_mean = float(Ga[n].mean())
        cobertura = 100.0 * g_mean / max(d_mean, 1e-6)

        ax.fill_between(hours, Da[n], alpha=0.18, color=color_d)
        ax.plot(hours, Da[n], color=color_d, linewidth=2.0,
                marker="o", markersize=3, label="Demanda D")
        ax.fill_between(hours, Ga[n], alpha=0.18, color=color_g)
        ax.plot(hours, Ga[n], color=color_g, linewidth=2.0,
                linestyle="--", marker="s", markersize=3,
                label="Generacion G")

        ax.set_title(
            f"{agent}  (D={d_mean:.2f} kW  G={g_mean:.2f} kW  "
            f"cobertura {cobertura:.0f}%)",
            fontsize=10,
        )
        ax.set_ylabel("kW")
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 23)
        ax.set_xticks(np.arange(0, 24, 3))
        if n == 0:
            ax.legend(loc="upper left", fontsize=9)

    # Sexto panel: comunidad total
    ax = axes[5]
    D_tot = Da.sum(axis=0)
    G_tot = Ga.sum(axis=0)
    ax.fill_between(hours, D_tot, alpha=0.18, color=color_d)
    ax.plot(hours, D_tot, color=color_d, linewidth=2.0,
            marker="o", markersize=3, label="Demanda comunidad")
    ax.fill_between(hours, G_tot, alpha=0.18, color=color_g)
    ax.plot(hours, G_tot, color=color_g, linewidth=2.0,
            linestyle="--", marker="s", markersize=3,
            label="Generacion comunidad")
    cob_tot = 100.0 * G_tot.mean() / max(D_tot.mean(), 1e-6)
    ax.set_title(
        f"Comunidad total  (D={D_tot.mean():.2f} kW  "
        f"G={G_tot.mean():.2f} kW  cobertura {cob_tot:.0f}%)",
        fontsize=10,
    )
    ax.set_ylabel("kW")
    ax.set_xlabel("Hora del dia")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 23)
    ax.set_xticks(np.arange(0, 24, 3))
    ax.legend(loc="upper left", fontsize=9)

    axes[4].set_xlabel("Hora del dia")

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    out = repo / "graficas" / "fig_perfiles_DG_actualizados.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"OK -> {out}")


if __name__ == "__main__":
    main()
