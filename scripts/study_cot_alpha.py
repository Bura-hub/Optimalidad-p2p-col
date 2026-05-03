"""
scripts/study_cot_alpha.py — CAL-20 Sensibilidad cot_alpha en C2 (PPA bilateral)
================================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 3.1-3.3

Sustento empirico del default `cot_alpha=1.0` introducido en CAL-16
(ADR-0016) para C2 (PPA bilateral, usuario no-regulado).

Contexto regulatorio:
  - CREG 101-028/2023 introduce COT (Cargo Operador Telematico) como
    cargo del comercializador minorista al usuario regulado.
  - Ley 143/1994 / CREG 086/1996: usuario no-regulado no tiene
    comercializador minorista, por tanto **no paga COT**.
  - cot_alpha modela la fraccion de COT efectivamente "ahorrada"
    por el usuario no-regulado al moverse al esquema PPA bilateral:
       cot_alpha = 1.0 -> ahorra 100% del COT (cota pesimista)
       cot_alpha = 0.5 -> ahorra 50% (interpretacion conservadora)
       cot_alpha = 0.0 -> no ahorra COT (lower bound)

Salidas:
  graficas/sensibilidad_cot_alpha.csv  -- tabla alpha vs net_benefit C2
  graficas/sensibilidad_cot_alpha.png  -- plot de sensibilidad
  graficas/sensibilidad_cot_alpha.mat  -- reproducibilidad MATLAB

Referencia: docs/adr/0020-cal20-cot-alpha-sensibilidad.md
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
    """Carga MTE + tarifas Cedenar + componentes regulatorios."""
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


def correr_barrido(alphas: list[float], D, G, pi_gs, g_comp, cvm, cot, mem,
                    prosumer_ids: list[int] | None = None,
                    consumer_ids: list[int] | None = None):
    """Corre run_c2_bilateral para cada alpha y devuelve DataFrame.

    Nota CAL-20: en MTE las 5 instituciones son todas prosumidoras
    (todas tienen solar). En esa configuracion `consumer_ids = []`
    deshabilita el flujo PPA y `cot_alpha` queda inerte. Para
    observar la sensibilidad se permite un split artificial (3
    prosumers + 2 consumers segun cobertura G/D promedio) que
    activa el flujo PPA. La eleccion del split se documenta en
    ADR-0020 como ilustrativa, no como configuracion real.
    """
    from scenarios.scenario_c2_bilateral import run_c2_bilateral

    N = D.shape[0]
    if prosumer_ids is None or consumer_ids is None:
        # Split por cobertura G/D promedio: top-3 prosumidores,
        # bottom-2 consumidores. Los IDs reales dependen del orden
        # de AGENTS pero el patron es estable.
        cov = G.sum(axis=1) / np.maximum(D.sum(axis=1), 1e-9)
        order = np.argsort(-cov)  # descendente
        prosumer_ids = sorted(order[:3].tolist())
        consumer_ids = sorted(order[3:].tolist())
        print(f"  [cal-20] Split ilustrativo: prosumers={prosumer_ids}, "
              f"consumers={consumer_ids}")

    # pi_ppa razonable: media de g_comp (componente G) del periodo.
    pi_ppa = float(np.nanmean(g_comp))
    pi_gb = 280.0  # baseline conservador (PGB_COP de CAL-6)

    rows = []
    for alpha in alphas:
        result = run_c2_bilateral(
            D=D, G=G,
            pi_gs=pi_gs, pi_gb=pi_gb, pi_ppa=pi_ppa,
            prosumer_ids=prosumer_ids,
            consumer_ids=consumer_ids,
            g_component=g_comp,
            cvm_component=cvm,
            cot_component=cot,
            mem_costs=mem,
            cot_alpha=alpha,
        )
        agg = result["aggregate"]
        rows.append({
            "cot_alpha": alpha,
            "total_net_benefit": agg["total_net_benefit"],
            "total_savings_G": agg["total_savings_G"],
            "total_savings_Cvm": agg["total_savings_Cvm"],
            "total_savings_COT": agg["total_savings_COT"],
            "total_mem_costs": agg["total_mem_costs"],
            "total_savings_ppa": agg["total_savings_ppa"],
            "total_grid_cost": agg["total_grid_cost"],
        })
    df = pd.DataFrame(rows).set_index("cot_alpha").sort_index()

    # Linealidad esperada: net_benefit(alpha) = baseline + alpha * savings_COT_unit
    # Reportamos el delta absoluto y porcentual vs alpha=1.0 (default).
    if 1.0 in df.index:
        ref = df.loc[1.0, "total_net_benefit"]
        df["delta_vs_alpha1_abs"] = df["total_net_benefit"] - ref
        df["delta_vs_alpha1_pct"] = (
            df["delta_vs_alpha1_abs"] / max(abs(ref), 1e-9) * 100
        )
    return df


def _save_outputs(df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "sensibilidad_cot_alpha.csv"
    df.to_csv(csv_path)
    print(f"  [cal-20] CSV  -> {csv_path}")

    try:
        from scipy.io import savemat
        mat_data = {col: df[col].to_numpy() for col in df.columns}
        mat_data["cot_alpha"] = df.index.to_numpy(dtype=float)
        savemat(str(out_dir / "sensibilidad_cot_alpha.mat"), mat_data)
        print(f"  [cal-20] MAT  -> {out_dir / 'sensibilidad_cot_alpha.mat'}")
    except Exception as e:
        print(f"  [cal-20] MAT skipped ({e})")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

        ax = axes[0]
        nb_kcop = df["total_net_benefit"] / 1e3
        ax.plot(df.index, nb_kcop, "o-", color="tab:blue",
                label="net_benefit C2 [k$]")
        ax.axvline(1.0, color="gray", lw=0.8, ls="--",
                   label="default cot_alpha=1.0")
        ax.set_xlabel("cot_alpha")
        ax.set_ylabel("Beneficio neto C2 total [k$]")
        ax.set_title("Sensibilidad de C2 a cot_alpha")
        ax.grid(alpha=0.3)
        ax.legend(loc="best", fontsize=8)

        ax = axes[1]
        cot_only = df["total_savings_COT"] / 1e3
        ax.plot(df.index, cot_only, "s-", color="tab:red",
                label="savings_COT [k$]")
        if "delta_vs_alpha1_pct" in df.columns:
            ax2 = ax.twinx()
            ax2.plot(df.index, df["delta_vs_alpha1_pct"], "^--",
                     color="tab:green",
                     label="delta net_benefit vs alpha=1 [%]")
            ax2.axhline(0, color="black", lw=0.5, ls=":")
            ax2.set_ylabel("delta net_benefit [%]", color="tab:green")
        ax.set_xlabel("cot_alpha")
        ax.set_ylabel("savings_COT [k$]", color="tab:red")
        ax.set_title("Linealidad de cot_alpha")
        ax.grid(alpha=0.3)
        ax.legend(loc="lower right", fontsize=8)

        fig.suptitle("CAL-20 - sensibilidad cot_alpha en C2 (PPA bilateral)")
        fig.tight_layout()
        png_path = out_dir / "sensibilidad_cot_alpha.png"
        fig.savefig(png_path, dpi=130, bbox_inches="tight")
        plt.close(fig)
        print(f"  [cal-20] PNG  -> {png_path}")
    except Exception as e:
        print(f"  [cal-20] PNG skipped ({e})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--t-start", default="2025-08-04",
                    help="Fecha inicio (YYYY-MM-DD), default 2025-08-04.")
    ap.add_argument("--t-end", default="2025-08-11",
                    help="Fecha fin (YYYY-MM-DD), default 2025-08-11.")
    ap.add_argument("--alphas", default="0.0,0.25,0.5,0.75,1.0,1.25,1.5,2.0",
                    help="Lista de cot_alpha separada por comas.")
    ap.add_argument("--out-dir", default=str(ROOT / "graficas"))
    args = ap.parse_args()

    alphas = [float(x) for x in args.alphas.split(",")]
    print(f"  [cal-20] Subset: [{args.t_start} .. {args.t_end})")
    print(f"  [cal-20] alphas: {alphas}")

    D, G, pi_gs, g_comp, cvm, cot, mem, agents = cargar_subset(
        args.t_start, args.t_end,
    )
    print(f"  [cal-20] D={D.shape}, G={G.shape}, agentes={agents}")
    print(f"  [cal-20] pi_gs medio: {np.nanmean(pi_gs):.1f} COP/kWh, "
          f"G medio: {np.nanmean(g_comp):.1f}, "
          f"Cvm medio: {np.nanmean(cvm):.1f}, "
          f"COT medio: {np.nanmean(cot):.1f}, "
          f"MEM medio: {np.nanmean(mem):.1f}")

    df = correr_barrido(alphas, D, G, pi_gs, g_comp, cvm, cot, mem)
    print()
    print(df.to_string())

    out_dir = Path(args.out_dir)
    _save_outputs(df, out_dir)
    print()
    print("  [cal-20] hecho.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
