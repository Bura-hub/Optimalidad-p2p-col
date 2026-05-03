"""
scripts/study_f_split.py — CAL-21 Sensibilidad de `f` (split factor PPA) en C2
================================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 3.1-3.3

Sustento empirico del default `f = 0.5` (postulado normativo CAL-11)
con datos MTE reales mas split ilustrativo (3 prosumers + 2 consumers).

Definicion: pi_ppa = pi_gb + f * (pi_upper - pi_gb), donde
  - pi_gb     = piso regulatorio (precio bolsa, sin PPA es lo que se cobra
                por excedente).
  - pi_upper  = techo regulatorio (G + Cvm + alpha*COT - MEM, CAL-16).
  - f in [0,1] = fraccion del spread que beneficia al prosumidor.

Hipotesis verificables (corolario del teorema de invarianza, notas §3.8):
  H1: total_net_benefit C2 es INVARIANTE en f (comunidad cerrada).
  H2: Gini de net_benefit NO es invariante en f (justifica SA-3).
  H3: f = 0.5 produce el split egalitario (50/50 del spread).

Salidas:
  graficas/sensibilidad_f.csv   -- tabla f vs net_benefit / Gini
  graficas/sensibilidad_f.png   -- plot 2 paneles
  graficas/sensibilidad_f.mat   -- reproducibilidad MATLAB

Referencia: docs/adr/0021-cal21-c2-f-split-sensibilidad.md
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                   encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer,
                                   encoding="utf-8", errors="replace")


def cargar_subset(t_start: str, t_end: str):
    """Carga MTE + componentes regulatorios."""
    import os
    from data.xm_data_loader import MTEDataLoader, slice_horizon, AGENTS
    from data.cedenar_tariff import (
        pi_gs_per_agent_hourly,
        cu_components_per_agent_hourly,
        mem_costs_per_agent_hourly,
    )
    mte_root = os.environ.get("MTE_ROOT", str(ROOT / "MedicionesMTE_v3"))
    loader = MTEDataLoader(root_path=mte_root)
    D_full, G_full, idx_full = loader.load(verbose=False)
    D, G, idx = slice_horizon(D_full, G_full, idx_full, t_start, t_end)
    agents = list(AGENTS)
    pi_gs = pi_gs_per_agent_hourly(agents, idx)
    components = cu_components_per_agent_hourly(agents, idx)
    g_comp = components["G"]
    cvm = components["Cvm"]
    cot = components["COT"]
    mem = mem_costs_per_agent_hourly(agents, idx)
    return D, G, pi_gs, g_comp, cvm, cot, mem, agents


def _gini(values: np.ndarray) -> float:
    """Indice de Gini sobre `values >= 0`. Devuelve [0, 1]."""
    v = np.asarray(values, dtype=float).flatten()
    if v.size == 0 or np.all(v == 0):
        return 0.0
    if np.any(v < 0):
        v = v - v.min()  # shift para tolerar valores negativos
    v_sorted = np.sort(v)
    n = v_sorted.size
    cum = np.cumsum(v_sorted)
    return float((2 * np.sum((np.arange(1, n + 1)) * v_sorted) - (n + 1) * cum[-1])
                  / (n * cum[-1]))


def correr_barrido(fs: list[float], D, G, pi_gs, g_comp, cvm, cot, mem,
                    prosumer_ids: list[int] | None = None,
                    consumer_ids: list[int] | None = None,
                    cot_alpha: float = 1.0):
    """Corre run_c2_bilateral para cada f y devuelve DataFrame.

    Nota CAL-21 (igual que CAL-20): MTE real tiene consumer_ids vacio
    (todas prosumidoras). Sin consumidores, el flujo PPA no se activa
    y `f` queda inerte. Para observar la sensibilidad usamos un split
    ilustrativo (top-3 cobertura prosumers + bottom-2 consumers).
    """
    from scenarios.scenario_c2_bilateral import run_c2_bilateral

    N = D.shape[0]
    if prosumer_ids is None or consumer_ids is None:
        cov = G.sum(axis=1) / np.maximum(D.sum(axis=1), 1e-9)
        order = np.argsort(-cov)
        prosumer_ids = sorted(order[:3].tolist())
        consumer_ids = sorted(order[3:].tolist())
        print(f"  [cal-21] Split ilustrativo: prosumers={prosumer_ids}, "
              f"consumers={consumer_ids}")

    pi_gb = 280.0  # baseline conservador (PGB_COP de CAL-6)
    g_mean = float(np.nanmean(g_comp))
    cvm_mean = float(np.nanmean(cvm))
    cot_mean = float(np.nanmean(cot))
    mem_mean = float(np.nanmean(mem))
    pi_upper = g_mean + cvm_mean + cot_alpha * cot_mean - mem_mean
    print(f"  [cal-21] pi_gb={pi_gb:.1f}, pi_upper={pi_upper:.1f} "
          f"(G+Cvm+alpha*COT-MEM, alpha={cot_alpha})")
    print(f"  [cal-21] Spread = pi_upper - pi_gb = "
          f"{pi_upper - pi_gb:.1f} COP/kWh")

    rows = []
    for f in fs:
        pi_ppa = pi_gb + f * (pi_upper - pi_gb)
        result = run_c2_bilateral(
            D=D, G=G,
            pi_gs=pi_gs, pi_gb=pi_gb, pi_ppa=pi_ppa,
            prosumer_ids=prosumer_ids,
            consumer_ids=consumer_ids,
            g_component=g_comp,
            cvm_component=cvm,
            cot_component=cot,
            mem_costs=mem,
            cot_alpha=cot_alpha,
        )
        agg = result["aggregate"]
        per_agent = result["per_agent"]
        nb_per_agent = np.array([per_agent[n]["net_benefit"]
                                  for n in range(N)])
        rows.append({
            "f": f,
            "pi_ppa": pi_ppa,
            "total_net_benefit": agg["total_net_benefit"],
            "total_savings_gen": agg["total_savings_gen"],
            "total_savings_ppa": agg["total_savings_ppa"],
            "total_grid_revenue": agg["total_grid_revenue"],
            "gini_net_benefit": _gini(nb_per_agent),
            "nb_prosumer_mean": float(
                np.mean([per_agent[n]["net_benefit"]
                         for n in prosumer_ids])),
            "nb_consumer_mean": float(
                np.mean([per_agent[n]["net_benefit"]
                         for n in consumer_ids])
                if consumer_ids else 0.0),
        })
    df = pd.DataFrame(rows).set_index("f").sort_index()

    if 0.5 in df.index:
        ref_nb = df.loc[0.5, "total_net_benefit"]
        df["delta_nb_vs_f05_pct"] = (
            (df["total_net_benefit"] - ref_nb).abs()
            / max(abs(ref_nb), 1e-9) * 100
        )
    return df


def _save_outputs(df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "sensibilidad_f.csv"
    df.to_csv(csv_path)
    print(f"  [cal-21] CSV  -> {csv_path}")

    try:
        from scipy.io import savemat
        mat_data = {col: df[col].to_numpy() for col in df.columns}
        mat_data["f"] = df.index.to_numpy(dtype=float)
        savemat(str(out_dir / "sensibilidad_f.mat"), mat_data)
        print(f"  [cal-21] MAT  -> {out_dir / 'sensibilidad_f.mat'}")
    except Exception as e:
        print(f"  [cal-21] MAT skipped ({e})")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

        ax = axes[0]
        ax.plot(df.index, df["total_net_benefit"] / 1e3, "o-",
                color="tab:blue", label="total net_benefit [k$]")
        ax.plot(df.index, df["nb_prosumer_mean"] / 1e3, "s--",
                color="tab:orange", label="prosumer mean [k$]")
        ax.plot(df.index, df["nb_consumer_mean"] / 1e3, "^--",
                color="tab:green", label="consumer mean [k$]")
        ax.axvline(0.5, color="gray", lw=0.8, ls=":", label="default f=0.5")
        ax.set_xlabel("f (split factor)")
        ax.set_ylabel("Beneficio neto [k$]")
        ax.set_title("Invarianza agregado / variacion individual")
        ax.legend(loc="best", fontsize=8)
        ax.grid(alpha=0.3)

        ax = axes[1]
        ax.plot(df.index, df["gini_net_benefit"], "o-",
                color="tab:red", label="Gini(net_benefit)")
        ax.axvline(0.5, color="gray", lw=0.8, ls=":")
        ax.set_xlabel("f (split factor)")
        ax.set_ylabel("Indice de Gini")
        ax.set_title("Gini NO invariante en f (justifica SA-3)")
        ax.grid(alpha=0.3)
        ax.legend(loc="best", fontsize=8)

        fig.suptitle("CAL-21 - sensibilidad de f en C2 (PPA bilateral)")
        fig.tight_layout()
        png_path = out_dir / "sensibilidad_f.png"
        fig.savefig(png_path, dpi=130, bbox_inches="tight")
        plt.close(fig)
        print(f"  [cal-21] PNG  -> {png_path}")
    except Exception as e:
        print(f"  [cal-21] PNG skipped ({e})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--t-start", default="2025-08-04")
    ap.add_argument("--t-end", default="2025-08-11")
    ap.add_argument("--fs", default="0.0,0.1,0.25,0.5,0.75,0.9,1.0")
    ap.add_argument("--out-dir", default=str(ROOT / "graficas"))
    args = ap.parse_args()

    fs = [float(x) for x in args.fs.split(",")]
    print(f"  [cal-21] Subset: [{args.t_start} .. {args.t_end})")
    print(f"  [cal-21] f a barrer: {fs}")

    D, G, pi_gs, g_comp, cvm, cot, mem, agents = cargar_subset(
        args.t_start, args.t_end,
    )
    print(f"  [cal-21] D={D.shape}, agentes={agents}")

    df = correr_barrido(fs, D, G, pi_gs, g_comp, cvm, cot, mem)
    print()
    print(df.to_string())

    out_dir = Path(args.out_dir)
    _save_outputs(df, out_dir)
    print()
    print("  [cal-21] hecho.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
