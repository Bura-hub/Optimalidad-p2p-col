"""scripts/regen_subperiod_paper.py
Regen fig_paper_subperiod usando state pickle del case study real.

Si existe outputs/paper/_subperiod_state.pkl (de scripts/debug_subperiod_v2.py),
usa los p2p_results reales -> P2P weekly = suma horaria real (NO atribucion).
Si no existe, cae a fallback CSV-based con PV-weighted attribution.

Para regenerar el state pickle (cuando cambien parametros):
  python scripts/debug_subperiod_v2.py
"""
from __future__ import annotations
import sys
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WEEKLY_PV_RATIOS = np.array([0.22037, 0.26298, 0.24842, 0.26823])


def _from_pickle(state_path: Path):
    """Usa state pickled (con p2p_results reales)."""
    with open(state_path, "rb") as f:
        state = pickle.load(f)
    return (state["scenarios_data"], state["agents"],
            state["p2p_results"], state["G_klim"])


def _from_csv():
    """Fallback: CSV-based con weights hardcoded."""
    csv = ROOT / "outputs" / "paper" / "fig_paper_per_agent_benefit.csv"
    df = pd.read_csv(csv)
    agents = df["agent"].tolist()
    n_weeks = 4
    week_size = 168
    T = n_weeks * week_size

    scenarios_data = {}
    for col in df.columns[1:]:
        per_agent_kCOP = df[col].to_numpy()
        per_agent_COP = per_agent_kCOP * 1e3
        total_COP = float(per_agent_COP.sum())
        scenarios_data[col] = (total_COP, per_agent_COP)

    G_klim = np.zeros(T)
    for w in range(n_weeks):
        G_klim[w * week_size:(w + 1) * week_size] = WEEKLY_PV_RATIOS[w] / week_size
    p2p_results = [None] * T
    return scenarios_data, agents, p2p_results, G_klim


def main() -> int:
    from visualization.paper_figures.thesis_adapted_en import fig_paper_subperiod

    state_path = ROOT / "outputs" / "paper" / "_subperiod_state.pkl"
    if state_path.exists():
        print(f"[regen] Using state pickle: {state_path.name}")
        scenarios_data, agents, p2p_results, G_klim = _from_pickle(state_path)
    else:
        print("[regen] No state pickle; CSV fallback (PV-weighted)")
        print("  Run scripts/debug_subperiod_v2.py to generate state with real p2p_results")
        scenarios_data, agents, p2p_results, G_klim = _from_csv()

    out = ROOT / "outputs" / "paper" / "fig_paper_subperiod"
    saved = fig_paper_subperiod(scenarios_data, agents, p2p_results,
                                  G_klim, out)
    print(f"[OK] regen -> {saved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
