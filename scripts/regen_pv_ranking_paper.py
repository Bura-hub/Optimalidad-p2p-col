"""scripts/regen_pv_ranking_paper.py
Regen rapido fig_pv_ranking_cal29_canonical desde CSV existente (~3s).
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from analysis.sensitivity import plot_pv_ranking

    csv = ROOT / "outputs" / "paper" / "fig_pv_ranking_cal29_canonical.csv"
    df = pd.read_csv(csv)
    scenarios = [
        "P2P (Stackelberg + RD)",
        "C1 (CREG 174)",
        "C2 (CREG 101 072)",
    ]

    out = ROOT / "outputs" / "paper" / "fig_pv_ranking_cal29_canonical.png"
    saved = plot_pv_ranking(df, scenarios, out,
                              title="PV factor sweep — paper IEEE WEEF 2026",
                              baseline_factor=1.0)
    print(f"[OK] regen -> {saved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
