"""
subperiod.py — Análisis de sub-períodos (Actividad 3.2)
--------------------------------------------------------
Brayan S. Lopez-Mendez · Udenar 2026

Compara el mercado P2P en cuatro escenarios representativos:

  SP1  Laborable × Julio   → demanda plena   + π_gb=133 COP/kWh
  SP2  Laborable × Enero   → demanda plena   + π_gb=218 COP/kWh
  SP3  Fin-semana × Julio  → demanda × 0.65  + π_gb=133 COP/kWh
  SP4  Fin-semana × Enero  → demanda × 0.65  + π_gb=218 COP/kWh

La reducción de demanda del 35% en fines de semana refleja el patrón
observado en instituciones públicas colombianas (universidades, hospitales)
con actividad reducida sábado-domingo.

El valor informativo principal es la divergencia C1 ≠ C3: cuando hay
excedente (más probable en fines de semana), C1 (CREG 174 — balance
mensual) y C3 (spot horario) producen resultados distintos.

Uso desde main_simulation.py:
    from analysis.subperiod import run_subperiod_analysis
    results = run_subperiod_analysis(D, G, agents, grid, solver, ...)

Uso standalone (datos sintéticos):
    python analysis/subperiod.py
"""

from __future__ import annotations

import os, sys
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

# ── Parámetros de sub-período ─────────────────────────────────────────────────

WEEKEND_FACTOR = 0.65   # demanda fin de semana / demanda laborable
# Rango reportado en Colombia: 60-70%. Se usa el punto medio (65%).
# Fuente: patrones XM 2023 y mediciones institucionales Pasto.

# Precios de bolsa reales promedio por sub-período (COP/kWh)
PI_GB_JULIO  = 133.0   # julio-2025 (mes más bajo del período)
PI_GB_ENERO  = 218.0   # enero-2026 (mes más alto del período)

SUB_PERIODS = {
    "Laborable-Jul": {"demand_factor": 1.00, "pi_gb": PI_GB_JULIO},
    "Laborable-Ene": {"demand_factor": 1.00, "pi_gb": PI_GB_ENERO},
    "Finde-Jul":     {"demand_factor": WEEKEND_FACTOR, "pi_gb": PI_GB_JULIO},
    "Finde-Ene":     {"demand_factor": WEEKEND_FACTOR, "pi_gb": PI_GB_ENERO},
}


@dataclass
class SubperiodResult:
    label:        str
    demand_factor: float
    pi_gb:        float
    net_p2p:      float        # ganancia neta P2P total [COP]
    net_c1:       float        # ganancia neta C1 [COP]
    net_c3:       float        # ganancia neta C3 [COP]
    net_c4:       float        # ganancia neta C4 [COP]
    net_p2p_agent: list        # por agente [COP]
    net_c4_agent:  list        # por agente [COP]
    rpe:          float        # (W_P2P - W_C4) / |W_P2P|; ver ComparisonResult.rpe
    ie_p2p:       float        # índice de equidad P2P
    market_hours: int          # horas con mercado activo
    kwh_p2p:      float        # kWh intercambiados en P2P
    c1_c3_spread: float        # |net_c1 - net_c3| divergencia C1 vs C3 [COP]
    sc:           float        # self-consumption ratio
    ss:           float        # self-sufficiency ratio


# ── Función principal ─────────────────────────────────────────────────────────

def run_subperiod_analysis(
    D:            np.ndarray,     # (N, 24) perfil diario base
    G:            np.ndarray,     # (N, 24) generación diaria base
    agents,                       # AgentParams (ya configurado)
    grid,                         # GridParams base
    solver,                       # SolverParams
    pde:          np.ndarray,     # (N,) pesos C4
    prosumer_ids: list,
    consumer_ids: list,
    pi_gs:        float,
    capacity:     np.ndarray,
    agent_names:  list,
    currency:     str = "COP",
    verbose:      bool = True,
) -> list[SubperiodResult]:
    """
    Ejecuta la simulación completa (EMS P2P + escenarios C1-C4) para
    cada uno de los 4 sub-períodos y retorna lista de SubperiodResult.
    """
    from core.ems_p2p import EMSP2P
    from scenarios import run_comparison

    results = []

    for label, params in SUB_PERIODS.items():
        df = params["demand_factor"]
        pgb = params["pi_gb"]

        D_sp = D * df           # escalar demanda
        G_sp = G.copy()         # generación no cambia

        # Ajustar grid params con el pi_gb del sub-período
        import copy
        grid_sp = copy.copy(grid)
        grid_sp.pi_gb = pgb

        if verbose:
            surplus_h = int(np.sum(G_sp.sum(axis=0) > D_sp.sum(axis=0)))
            print(f"\n  [{label}]  d_factor={df:.2f}  pi_gb={pgb:.0f}"
                  f"  horas_surplus={surplus_h}/24")

        # EMS P2P
        ems = EMSP2P(agents, grid_sp, solver)
        p2p_results_sp, G_klim_sp, _ = ems.run(D_sp, G_sp)

        active = [r for r in p2p_results_sp
                  if r.P_star is not None and np.sum(r.P_star) > 1e-4]
        kwh = sum(float(np.sum(r.P_star)) for r in active)

        # Escenarios C1-C4
        pi_bolsa_sp = np.full(D_sp.shape[1], pgb)
        cr = run_comparison(
            D=D_sp, G_klim=G_klim_sp, G_raw=G_sp,
            p2p_results=p2p_results_sp,
            pi_gs=pi_gs, pi_gb=pgb,
            pi_bolsa=pi_bolsa_sp,
            prosumer_ids=prosumer_ids,
            consumer_ids=consumer_ids,
            pde=pde,
            pi_ppa=pgb + 0.5 * (pi_gs - pgb),
            capacity=capacity,
            month_labels=None,
        )

        nb = cr.net_benefit
        nba = cr.net_benefit_per_agent
        p2p_tot = float(nb.get("P2P", 0))
        c4_tot  = float(nb.get("C4",  0))
        c1_tot  = float(nb.get("C1",  0))
        c3_tot  = float(nb.get("C3",  0))
        # RPE canónico: (W_P2P - W_C4) / |W_P2P|  (ver comparison_engine.py:331-334
        # y Matriz_Trazabilidad.md:37). max(|W_P2P|, 1.0) evita división por cero
        # en sub-períodos sin mercado P2P activo. Hallazgo de auditoría D5 (2026-04-17):
        # esta fórmula antes era (p2p - c4) / max(|c4|, 1.0), inconsistente con la
        # canónica; los .xlsx generados antes del run --full contienen valores stale.
        rpe = (p2p_tot - c4_tot) / max(abs(p2p_tot), 1.0)

        res = SubperiodResult(
            label=label,
            demand_factor=df,
            pi_gb=pgb,
            net_p2p=p2p_tot,
            net_c1=c1_tot,
            net_c3=c3_tot,
            net_c4=c4_tot,
            net_p2p_agent=list(nba.get("P2P", [])),
            net_c4_agent=list(nba.get("C4",  [])),
            rpe=rpe,
            ie_p2p=float(cr.gini.get("P2P", 0)),
            market_hours=len(active),
            kwh_p2p=kwh,
            c1_c3_spread=abs(c1_tot - c3_tot),
            sc=float(cr.self_consumption.get("P2P", 0)),
            ss=float(cr.self_sufficiency.get("P2P", 0)),
        )
        results.append(res)

        if verbose:
            print(f"    P2P={p2p_tot:,.0f}  C1={c1_tot:,.0f}  "
                  f"C3={c3_tot:,.0f}  C4={c4_tot:,.0f}  {currency}")
            print(f"    Horas P2P={len(active)}/24  kWh={kwh:.1f}  "
                  f"RPE={rpe:.4f}  C1≠C3={abs(c1_tot - c3_tot):,.0f}")

    return results


# ── Tabla resumen ─────────────────────────────────────────────────────────────

def print_subperiod_table(results: list[SubperiodResult], currency: str = "COP") -> None:
    print("\n" + "="*75)
    print("  ANÁLISIS DE SUB-PERÍODOS")
    print("="*75)
    print(f"  {'Sub-período':<18} {'π_gb':>6} {'d_fac':>6} "
          f"{'P2P':>10} {'C1':>10} {'C3':>10} {'C4':>10} "
          f"{'H-P2P':>6} {'RPE':>7} {'C1≠C3':>8}")
    print("  " + "-"*75)
    for r in results:
        print(f"  {r.label:<18} {r.pi_gb:>6.0f} {r.demand_factor:>6.2f} "
              f"{r.net_p2p:>10,.0f} {r.net_c1:>10,.0f} {r.net_c3:>10,.0f} "
              f"{r.net_c4:>10,.0f} {r.market_hours:>6} {r.rpe:>7.4f} "
              f"{r.c1_c3_spread:>8,.0f}")
    print("="*75)

    # Hallazgos clave
    base = next((r for r in results if r.label == "Laborable-Jul"), None)
    finde = next((r for r in results if r.label == "Finde-Ene"), None)
    if base and finde:
        delta_h = finde.market_hours - base.market_hours
        delta_c1c3 = finde.c1_c3_spread
        print(f"\n  Hallazgos:")
        print(f"  • Horas P2P Finde-Ene vs Laborable-Jul: {delta_h:+d} "
              f"({base.market_hours}→{finde.market_hours})")
        print(f"  • Divergencia C1 vs C3 en Finde-Ene: {delta_c1c3:,.0f} {currency}/período")
        if delta_c1c3 > 0:
            print(f"    → Fin de semana genera excedente: C1 y C3 dejan de ser idénticos")
        print(f"  • RPE varía entre "
              f"{min(r.rpe for r in results):.4f} (Jul) y "
              f"{max(r.rpe for r in results):.4f} (Ene)")


# ── Figura ────────────────────────────────────────────────────────────────────

def plot_subperiod(
    results: list[SubperiodResult],
    out_dir: str,
    currency: str = "COP",
) -> Optional[str]:
    """
    Genera fig16_subperiod.png con 4 paneles:
      A) Precio de bolsa XM por mes (serie real Jul-Ene)
      B) Horas de mercado P2P activo por sub-período
      C) Ganancia neta P2P vs C4 por sub-período
      D) Divergencia C1 vs C3 (kWh excedente en fin de semana)
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        print("  matplotlib no disponible — se omite fig16")
        return None

    MESES = ["Jul\n2025", "Ago\n2025", "Sep\n2025", "Oct\n2025",
             "Nov\n2025", "Dic\n2025", "Ene\n2026"]
    PRECIOS_REALES = [133, 238, 295, 190, 207, 275, 218]

    labels = [r.label for r in results]
    x = np.arange(len(results))
    COLOR_P2P = "#2196F3"
    COLOR_C4  = "#FF5722"
    COLOR_C1  = "#4CAF50"
    COLOR_C3  = "#9C27B0"
    COLOR_BAR = "#78909C"
    FINDE_COLOR = "#E3F2FD"

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle("Análisis de Sub-períodos: Laborable vs Fin de Semana × Julio vs Enero",
                 fontsize=13, fontweight="bold")

    # ── Panel A: Precios XM mensuales ─────────────────────────────────────────
    ax = axes[0, 0]
    bar_colors = ["#B0BEC5"] * 7
    bar_colors[0] = "#EF9A9A"   # Julio  — resaltado (π_gb bajo)
    bar_colors[6] = "#A5D6A7"   # Enero  — resaltado (π_gb alto)
    bars = ax.bar(range(7), PRECIOS_REALES, color=bar_colors, edgecolor="white",
                  linewidth=0.5)
    for i, (v, c) in enumerate(zip(PRECIOS_REALES, bar_colors)):
        ax.text(i, v + 4, f"{v}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    ax.set_xticks(range(7))
    ax.set_xticklabels(MESES, fontsize=8.5)
    ax.set_ylabel("COP/kWh", fontsize=9)
    ax.set_title("A. Precio de bolsa XM real (Jul 2025 – Ene 2026)", fontsize=10)
    ax.set_ylim(0, 360)
    ax.axhline(np.mean(PRECIOS_REALES), color="gray", linestyle="--",
               linewidth=1, alpha=0.7, label=f"Media={np.mean(PRECIOS_REALES):.0f}")
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    # Fondo suave para los meses resaltados
    ax.annotate("π_gb usado\nen análisis", xy=(0, 133), xytext=(1.5, 80),
                arrowprops=dict(arrowstyle="->", color="#E53935"), fontsize=7.5,
                color="#E53935")
    ax.annotate("", xy=(6, 218), xytext=(4.5, 80),
                arrowprops=dict(arrowstyle="->", color="#388E3C"))

    # ── Panel B: Horas mercado P2P ────────────────────────────────────────────
    ax = axes[0, 1]
    hours = [r.market_hours for r in results]
    bar_cols = [FINDE_COLOR if "Finde" in r.label else "#CFD8DC" for r in results]
    bars2 = ax.bar(x, hours, color=bar_cols, edgecolor="#78909C", linewidth=0.8)
    # Separar laborable de finde con colores de texto
    for i, (rect, h) in enumerate(zip(bars2, hours)):
        ax.text(rect.get_x() + rect.get_width()/2, h + 0.1, f"{h}h",
                ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([l.replace("Laborable", "Lab").replace("Finde", "Fin") for l in labels], fontsize=10, rotation=0, ha="center")
    ax.set_ylabel("Horas / 24h", fontsize=9)
    ax.set_title("B. Horas con mercado P2P activo", fontsize=10)
    ax.set_ylim(0, 24)
    ax.spines[["top", "right"]].set_visible(False)
    lab_patch = mpatches.Patch(color="#CFD8DC", label="Laborable")
    fin_patch = mpatches.Patch(color=FINDE_COLOR, label="Fin de semana")
    ax.legend(handles=[lab_patch, fin_patch], fontsize=8)

    # ── Panel C: Ganancia neta P2P vs C4 ─────────────────────────────────────
    ax = axes[1, 0]
    w = 0.35
    net_p2p = [r.net_p2p / 1000 for r in results]   # en k COP
    net_c4  = [r.net_c4  / 1000 for r in results]
    b1 = ax.bar(x - w/2, net_p2p, w, label="P2P", color=COLOR_P2P, alpha=0.85)
    b2 = ax.bar(x + w/2, net_c4,  w, label="C4-Colectivo", color=COLOR_C4, alpha=0.85)
    for rect, v in zip(b1, net_p2p):
        ax.text(rect.get_x() + rect.get_width()/2, v + 0.5,
                f"{v:.0f}", ha="center", va="bottom", fontsize=7.5)
    for rect, v in zip(b2, net_c4):
        ax.text(rect.get_x() + rect.get_width()/2, v + 0.5,
                f"{v:.0f}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels([l.replace("Laborable", "Lab").replace("Finde", "Fin") for l in labels], fontsize=10, rotation=0, ha="center")
    ax.set_ylabel(f"Ganancia neta (k {currency}/período)", fontsize=9)
    ax.set_title("C. Ganancia neta: P2P vs C4-Colectivo", fontsize=10)
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)

    # ── Panel D: Divergencia C1 vs C3 ────────────────────────────────────────
    ax = axes[1, 1]
    c1_vals = [r.net_c1 / 1000 for r in results]
    c3_vals = [r.net_c3 / 1000 for r in results]
    spread  = [r.c1_c3_spread / 1000 for r in results]
    w2 = 0.3
    ax.bar(x - w2, c1_vals, w2, label="C1 (CREG 174)", color=COLOR_C1, alpha=0.85)
    ax.bar(x,      c3_vals, w2, label="C3 (Spot)",      color=COLOR_C3, alpha=0.85)
    ax.bar(x + w2, spread,  w2, label="|C1−C3|",        color="#FF9800", alpha=0.9,
           edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels([l.replace("Laborable", "Lab").replace("Finde", "Fin") for l in labels], fontsize=10, rotation=0, ha="center")
    ax.set_ylabel(f"Ganancia neta (k {currency}/período)", fontsize=9)
    ax.set_title("D. Divergencia C1 vs C3: balance mensual vs spot", fontsize=10)
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    # Anotar si la divergencia es > 0
    for i, (r, s) in enumerate(zip(results, spread)):
        if s > 0.1:
            ax.text(i + w2, s + 0.3, f"Δ={r.c1_c3_spread:.0f}",
                    ha="center", va="bottom", fontsize=7, color="#E65100")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = os.path.join(out_dir, "fig16_subperiod.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"    ✓ Fig 16 — Análisis sub-períodos guardado en {out_path}")
    return out_path


# ── Estadísticas de precios XM por sub-período ────────────────────────────────

def xm_price_subperiod_stats(csv_path: Optional[str] = None) -> dict:
    """
    Carga precios XM reales y calcula estadísticas por tipo de día y mes.

    Fuente: data/precios_bolsa_xm_api.csv (descargado vía pydataxm).
    Retorna dict con claves 'todos', 'laborable', 'finde', 'julio', 'enero';
    cada valor es {'media': float, 'n': int [, 'std': float]}.
    Retorna {} si el CSV no existe o falla la lectura.
    """
    if csv_path is None:
        base = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base, "..", "data", "precios_bolsa_xm_api.csv")

    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        df["Fecha"] = pd.to_datetime(df["Fecha"])
        df["dow"]   = df["Fecha"].dt.dayofweek   # 0=Lun, 6=Dom
        df["mes"]   = df["Fecha"].dt.month
        p = df["Precio_COP_kWh"]

        return {
            "todos":      {"media": p.mean(),   "std": p.std(),   "n": len(p)},
            "laborable":  {"media": p[df["dow"] < 5].mean(),  "n": int((df["dow"] < 5).sum())},
            "finde":      {"media": p[df["dow"] >= 5].mean(), "n": int((df["dow"] >= 5).sum())},
            "julio":      {"media": p[df["mes"] == 7].mean(), "n": int((df["mes"] == 7).sum())},
            "enero":      {"media": p[df["mes"] == 1].mean(), "n": int((df["mes"] == 1).sum())},
        }
    except Exception as e:
        print(f"  [subperiod] XM stats error: {e}")
        return {}


# ── CLI standalone ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Ejecución standalone con datos del perfil diario (base_case_data).
    Útil para prueba rápida sin tener las mediciones MTE completas.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    import warnings
    warnings.filterwarnings("ignore")

    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("\n" + "="*65)
    print("  SUB-PERIOD ANALYSIS — Brayan S. Lopez-Mendez (Udenar 2026)")
    print("="*65)

    # Estadísticas XM reales
    stats = xm_price_subperiod_stats()
    if stats:
        print("\n  Precios XM reales por sub-período (COP/kWh):")
        for k, v in stats.items():
            print(f"    {k:<12}: media={v['media']:.1f}  n={v['n']}h")

    # Cargar datos base
    from data.base_case_data import (
        get_generation_profiles, get_demand_profiles, get_agent_params,
        get_pde_weights, GRID_PARAMS_REAL,
    )
    from core.ems_p2p import AgentParams, GridParams, SolverParams, EMSP2P

    G = get_generation_profiles()
    D = get_demand_profiles()
    p = get_agent_params()
    pde = get_pde_weights()
    N = D.shape[0]

    grid_base = GridParams(**GRID_PARAMS_REAL)
    agents = AgentParams(
        N=N, a=np.zeros(N), b=np.array(p["b"]), c=np.full(N, 1.2),
        lam=np.full(N, 100.0), theta=np.full(N, 0.5), etha=np.full(N, 0.1),
    )
    solver = SolverParams(tau=0.001, t_span=(0.0, 0.005),
                          n_points=150, stackelberg_iters=2, parallel=True)

    agent_names = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"][:N]
    cap = np.zeros(N)

    print("\n  Corriendo simulaciones por sub-período...")
    results = run_subperiod_analysis(
        D=D, G=G,
        agents=agents, grid=grid_base, solver=solver,
        pde=pde, prosumer_ids=list(range(N)), consumer_ids=[],
        pi_gs=grid_base.pi_gs, capacity=cap,
        agent_names=agent_names, currency="COP", verbose=True,
    )

    print_subperiod_table(results, currency="COP")

    out_dir = os.path.join(os.path.dirname(__file__), "..", "graficas")
    os.makedirs(out_dir, exist_ok=True)
    plot_subperiod(results, out_dir=out_dir, currency="COP")
