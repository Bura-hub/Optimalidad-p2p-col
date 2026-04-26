"""
fairness.py
-----------
Price of Fairness (PoF) según Bertsimas, Farias & Trichakis (2011).

Definición formal:
    PoF = (W_eff − W_fair) / W_eff

Donde:
  W_eff  = bienestar total bajo la asignación más eficiente (max Σ B_n)
  W_fair = bienestar total bajo la asignación más equitativa (min Gini)

Interpretación en el contexto P2P:
  - Si el escenario más eficiente (P2P) y el más equitativo (C4) son distintos,
    el PoF cuantifica el costo de eficiencia de imponer la distribución equitativa.
  - PoF → 0: el mecanismo justo casi no sacrifica eficiencia.
  - PoF → 1: el mecanismo justo pierde casi todo el beneficio eficiente.
  - PoF < 0: imposible (si el más equitativo fuera también el más eficiente,
              se redefine como PoF = 0 por convención).

Referencia:
  D. Bertsimas, V. F. Farias, and N. Trichakis, "The price of fairness,"
  Operations Research, vol. 59, no. 1, pp. 17-31, 2011.

Actividad 3.3 — Descomposición del bienestar y comparación monetaria.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field


@dataclass
class FairnessResult:
    pof:           float              # PoF global [0, 1]
    w_eff:         float              # COP — bienestar total del escenario eficiente
    w_fair:        float              # COP — bienestar total del escenario equitativo
    eff_scenario:  str                # escenario con mayor beneficio total
    fair_scenario: str                # escenario con menor Gini
    pof_per_agent: np.ndarray         # PoF individual (N,): (B_n^eff - B_n^fair) / |B_n^eff|
    gini_ranking:  list               # [(escenario, gini, beneficio_total), ...]


def compute_pof(
    net_benefit_per_agent: dict,
    gini: dict,
) -> FairnessResult:
    """
    Calcula el Price of Fairness (PoF) formal.

    Parámetros
    ----------
    net_benefit_per_agent : dict[str, np.ndarray]
        Beneficio neto por agente para cada escenario.
        Ej: {"P2P": array([...]), "C1": array([...]), "C4": array([...])}
    gini : dict[str, float]
        Índice de Gini por escenario (0=equitativo, 1=concentrado).

    Retorna
    -------
    FairnessResult con pof, w_eff, w_fair, escenarios y ranking.
    """
    if not net_benefit_per_agent or not gini:
        return FairnessResult(
            pof=0.0, w_eff=0.0, w_fair=0.0,
            eff_scenario="", fair_scenario="",
            pof_per_agent=np.array([]),
            gini_ranking=[],
        )

    # Intersección de escenarios presentes en ambos dicts
    common = [k for k in net_benefit_per_agent if k in gini]
    if not common:
        return FairnessResult(
            pof=0.0, w_eff=0.0, w_fair=0.0,
            eff_scenario="", fair_scenario="",
            pof_per_agent=np.array([]),
            gini_ranking=[],
        )

    totals = {k: float(np.sum(net_benefit_per_agent[k])) for k in common}

    # Escenario más eficiente: max beneficio total agregado
    eff_scenario = max(totals, key=totals.get)
    w_eff = totals[eff_scenario]

    # Escenario más equitativo: min coeficiente Gini
    fair_scenario = min(gini, key=lambda k: gini[k] if k in common else 1.0)
    w_fair = totals[fair_scenario]

    # PoF global (≥ 0 por definición; si el equitativo es más eficiente → 0)
    if abs(w_eff) > 1e-10:
        pof = max(0.0, (w_eff - w_fair) / abs(w_eff))
    else:
        pof = 0.0

    # PoF por agente: sacrificio individual de eficiencia
    b_eff  = net_benefit_per_agent[eff_scenario]
    b_fair = net_benefit_per_agent[fair_scenario]
    denom  = np.abs(b_eff)
    with np.errstate(invalid="ignore", divide="ignore"):
        pof_agent = np.where(denom > 1e-10,
                             np.maximum(0.0, (b_eff - b_fair) / denom),
                             0.0)

    # Ranking Gini ascendente (del más equitativo al más concentrado)
    gini_ranking = sorted(
        [(k, gini[k], totals[k]) for k in common],
        key=lambda x: x[1],
    )

    return FairnessResult(
        pof=pof,
        w_eff=w_eff,
        w_fair=w_fair,
        eff_scenario=eff_scenario,
        fair_scenario=fair_scenario,
        pof_per_agent=pof_agent,
        gini_ranking=gini_ranking,
    )


def fairness_curve(
    net_benefit_per_agent: dict,
    gini: dict,
) -> list:
    """
    Tabla PoF acumulada ordenada por equidad creciente.

    Para cada escenario (ordenado de mayor a menor Gini), calcula:
    - La pérdida de eficiencia si se adoptara ese escenario como "justo"
    - Cuánto sacrificio de beneficio total implicaría pasar al escenario siguiente

    Retorna
    -------
    list[dict] con columnas: escenario, gini, beneficio_total, pof_vs_eff,
                              delta_cop_vs_eff, delta_pct_vs_eff
    """
    if not net_benefit_per_agent or not gini:
        return []

    common = [k for k in net_benefit_per_agent if k in gini]
    totals = {k: float(np.sum(net_benefit_per_agent[k])) for k in common}
    w_eff  = max(totals.values())

    rows = []
    for k in sorted(common, key=lambda x: gini[x]):
        w_k    = totals[k]
        pof_k  = max(0.0, (w_eff - w_k) / abs(w_eff)) if abs(w_eff) > 1e-10 else 0.0
        delta  = w_eff - w_k
        rows.append({
            "escenario":      k,
            "gini":           gini[k],
            "beneficio_total": w_k,
            "pof_vs_eff":     pof_k,
            "delta_cop_vs_eff": delta,
            "delta_pct_vs_eff": delta / abs(w_eff) * 100 if abs(w_eff) > 1e-10 else 0.0,
        })
    return rows


def print_pof_report(fr: FairnessResult, currency: str = "COP") -> None:
    """Imprime el reporte de PoF en consola."""
    W = 70
    print("\n" + "=" * W)
    print("  PRICE OF FAIRNESS  [Bertsimas, Farias & Trichakis, 2011]")
    print("  PoF = (W_eff − W_fair) / W_eff")
    print("=" * W)
    if not fr.eff_scenario:
        print("  (sin datos suficientes)")
        print("=" * W)
        return

    print(f"\n  Escenario eficiente  ({fr.eff_scenario}):  "
          f"{fr.w_eff:>14,.0f} {currency}   [max beneficio total]")
    print(f"  Escenario equitativo ({fr.fair_scenario}):  "
          f"{fr.w_fair:>14,.0f} {currency}   [min Gini]")
    print(f"\n  PoF global:  {fr.pof:.4f}  "
          f"({fr.pof*100:.2f}% del beneficio eficiente se sacrifica por equidad)")

    print(f"\n  Ranking equidad (Gini ↑ = más concentrado):")
    print(f"  {'Escenario':<10} {'Gini':>8} {'Beneficio':>16} {'PoF vs eff':>12} {'Δ':>14}")
    print(f"  {'-'*64}")
    for esc, g, b in fr.gini_ranking:
        pof_k  = max(0.0, (fr.w_eff - b) / abs(fr.w_eff)) if abs(fr.w_eff) > 1e-10 else 0.0
        delta  = fr.w_eff - b
        marker = " ← eficiente" if esc == fr.eff_scenario else (
                 " ← equitativo" if esc == fr.fair_scenario else "")
        print(f"  {esc:<10} {g:>8.4f} {b:>16,.0f} {pof_k:>12.4f} "
              f"{delta:>+14,.0f}{marker}")

    if len(fr.pof_per_agent):
        print(f"\n  PoF por agente ({currency}):")
        for n, p in enumerate(fr.pof_per_agent):
            bar = "█" * int(p * 20)
            print(f"    Agente {n}: {p:.4f}  {bar}")

    print("=" * W)
