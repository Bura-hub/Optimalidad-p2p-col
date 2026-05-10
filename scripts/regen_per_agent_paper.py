"""scripts/regen_per_agent_paper.py
Regen rapido de fig_paper_per_agent_benefit desde el CSV existente.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from visualization.paper_figures.thesis_adapted_en import fig_paper_per_agent_benefit

    csv = ROOT / "outputs" / "paper" / "fig_paper_per_agent_benefit.csv"
    df = pd.read_csv(csv)
    agents = df["agent"].tolist()

    # Reconstruir scenarios_data: (total_COP, per_agent_COP_array)
    # La funcion divide por 1e3 internamente para mostrar en kCOP, asi que
    # multiplicamos por 1e3 los valores del CSV (que estan en kCOP).
    scenarios_data = {}
    for col in df.columns[1:]:  # skip "agent"
        per_agent_kCOP = df[col].to_numpy()
        per_agent_COP = per_agent_kCOP * 1e3
        total_COP = float(per_agent_COP.sum())
        scenarios_data[col] = (total_COP, per_agent_COP)

    out = ROOT / "outputs" / "paper" / "fig_paper_per_agent_benefit"
    saved = fig_paper_per_agent_benefit(scenarios_data, agents, out)
    print(f"[OK] regen -> {saved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
