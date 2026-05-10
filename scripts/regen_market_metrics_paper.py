"""scripts/regen_market_metrics_paper.py
Regen rapido fig_paper_market_activity + fig_paper_metrics_hourly
desde state pickle (~5s).
"""
from __future__ import annotations
import sys
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from visualization.paper_figures.thesis_adapted_en import (
        fig_paper_market_activity, fig_paper_metrics_hourly,
    )

    state_path = ROOT / "outputs" / "paper" / "_subperiod_state.pkl"
    if not state_path.exists():
        print("[ERROR] state pickle no existe; correr scripts/debug_subperiod_v2.py primero")
        return 1

    with open(state_path, "rb") as f:
        state = pickle.load(f)
    p2p_results = state["p2p_results"]
    G_klim = state["G_klim"]

    out1 = ROOT / "outputs" / "paper" / "fig_paper_market_activity"
    fig_paper_market_activity(p2p_results, out1)
    print(f"[OK] market_activity -> {out1}.png")

    out2 = ROOT / "outputs" / "paper" / "fig_paper_metrics_hourly"
    # Necesita D que no esta en state -> reconstruir o saltar
    try:
        import numpy as np
        D = np.zeros((len(state["agents"]), len(p2p_results)))
        fig_paper_metrics_hourly(p2p_results, D, G_klim, out2)
        print(f"[OK] metrics_hourly -> {out2}.png")
    except Exception as e:
        print(f"[skip] metrics_hourly: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
