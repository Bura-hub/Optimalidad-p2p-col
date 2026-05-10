"""scripts/regen_pof_paper.py
Regen rapido de fig_paper_price_of_fairness desde el CSV per_agent existente.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from visualization.paper_figures.thesis_adapted_en import fig_paper_price_of_fairness

    csv = ROOT / "outputs" / "paper" / "fig_paper_per_agent_benefit.csv"
    df = pd.read_csv(csv)
    agents = df["agent"].tolist()

    # Reconstruir scenarios_data: (total_COP, per_agent_COP_array)
    scenarios_data = {}
    for col in df.columns[1:]:  # skip "agent"
        per_agent_kCOP = df[col].to_numpy()
        per_agent_COP = per_agent_kCOP * 1e3
        total_COP = float(per_agent_COP.sum())
        scenarios_data[col] = (total_COP, per_agent_COP)

    out = ROOT / "outputs" / "paper" / "fig_paper_price_of_fairness"
    saved = fig_paper_price_of_fairness(scenarios_data, agents, out)
    print(f"[OK] regen -> {saved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
