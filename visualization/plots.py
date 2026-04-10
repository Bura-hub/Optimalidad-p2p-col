"""
plots.py
--------
Gráficas del proceso completo del modelo P2P para la tesis.
Produce 6 figuras que documentan todo el pipeline:

  Fig 1 — Perfiles D, G, G_klim por nodo
  Fig 2 — Clasificación vendedor/comprador hora a hora
  Fig 3 — Flujos del mercado P2P: energía y precios
  Fig 4 — Métricas horarias SC, SS, IE, bienestar
  Fig 5 — Comparación regulatoria: cuatro métricas × cinco escenarios
  Fig 6 — Ganancia neta por agente y escenario
"""

import os
import warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore")

AGENTS_REAL = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
COLORS_AGT  = ["#378ADD", "#1D9E75", "#D85A30", "#7F77DD", "#BA7517", "#D4537E"]
COLORS_ESC  = {"P2P": "#534AB7", "C1": "#1D9E75", "C2": "#BA7517",
                "C3": "#D85A30", "C4": "#D4537E"}

plt.rcParams.update({
    "font.family":    "DejaVu Sans",
    "font.size":      10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "legend.fontsize": 9,
    "figure.facecolor": "white",
    "axes.facecolor":   "white",
    "axes.grid":   True,
    "grid.alpha":  0.3,
    "grid.linewidth": 0.5,
})


def _save(fig, path: str, dpi: int = 150) -> str:
    fig.savefig(path, dpi=dpi, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    return path


# ── Fig 1 ─────────────────────────────────────────────────────────────────────

def plot_profiles(D, G, G_klim, agent_names, out_dir):
    N, T = D.shape
    hours = np.arange(T)
    fig, axes = plt.subplots(N, 1, figsize=(11, 2.6*N), sharex=True)
    if N == 1:
        axes = [axes]
    fig.suptitle("Fig 1 — Perfiles de demanda y generación por nodo",
                 fontsize=12, fontweight="bold", y=1.01)

    for n, ax in enumerate(axes):
        name = agent_names[n] if n < len(agent_names) else f"A{n+1}"
        ax.fill_between(hours, D[n], alpha=0.20, color="#378ADD")
        ax.plot(hours, D[n], color="#378ADD", linewidth=1.5, label="Demanda D")
        ax.plot(hours, G[n], color="#1D9E75", linewidth=1.5,
                linestyle="--", label="Generación G")
        ax.plot(hours, G_klim[n], color="#D85A30", linewidth=2.0,
                linestyle=":", label="G_klim (límite mercado)")
        ax.fill_between(hours, G_klim[n], alpha=0.18, color="#1D9E75")

        surplus = G_klim[n] > D[n]
        if surplus.any():
            ax.fill_between(hours, D[n], G_klim[n], where=surplus,
                            alpha=0.30, color="#1D9E75", label="Excedente P2P")

        cob = G[n].sum() / max(D[n].sum(), 1) * 100
        ax.set_ylabel("kW")
        ax.set_title(f"Nodo {n}: {name}  "
                     f"(D̄={D[n].mean():.1f} kW  "
                     f"Ḡ={G[n].mean():.1f} kW  "
                     f"cobertura PV={cob:.0f}%)")
        ax.legend(loc="upper right", ncol=4, fontsize=8)

    axes[-1].set_xlabel("Hora del perfil")
    axes[-1].set_xticks(hours[::max(1, T//12)])
    fig.tight_layout()
    return _save(fig, os.path.join(out_dir, "fig1_perfiles.png"))


# ── Fig 2 ─────────────────────────────────────────────────────────────────────

def plot_classification(p2p_results, agent_names, out_dir):
    T = len(p2p_results)
    N = len(agent_names)
    hours = np.arange(T)

    roles = np.zeros((N, T))
    for r in p2p_results:
        for j in r.seller_ids:
            roles[j, r.k] = 1
        for i in r.buyer_ids:
            roles[i, r.k] = -1

    fig, ax = plt.subplots(figsize=(12, 3.5))
    fig.suptitle("Fig 2 — Clasificación vendedor / comprador por hora",
                 fontsize=12, fontweight="bold")

    cmap = matplotlib.colors.ListedColormap(["#378ADD", "#F1EFE8", "#1D9E75"])
    norm = matplotlib.colors.BoundaryNorm([-1.5, -0.5, 0.5, 1.5], cmap.N)
    ax.imshow(roles, aspect="auto", cmap=cmap, norm=norm,
              extent=[-0.5, T-0.5, N-0.5, -0.5])

    ax.set_yticks(range(N))
    ax.set_yticklabels(agent_names)
    ax.set_xlabel("Hora del perfil")
    ax.set_xticks(hours[::max(1, T//12)])

    market_hours = [r.k for r in p2p_results
                    if r.P_star is not None and np.sum(r.P_star) > 1e-4]
    for h in market_hours:
        ax.axvline(h, color="#D85A30", alpha=0.45, linewidth=1.8)

    patches = [
        mpatches.Patch(color="#1D9E75", label="Vendedor (G_klim > D)"),
        mpatches.Patch(color="#F1EFE8", label="Neutro"),
        mpatches.Patch(color="#378ADD", label="Comprador (G_klim < D)"),
    ]
    ax.legend(handles=patches, loc="upper right", fontsize=9)
    ax.set_title(f"Horas con mercado P2P activo: {len(market_hours)}/{T}  "
                 f"(líneas naranjas)")
    fig.tight_layout()
    return _save(fig, os.path.join(out_dir, "fig2_clasificacion.png"))


# ── Fig 3 ─────────────────────────────────────────────────────────────────────

def plot_market_flows(p2p_results, agent_names, out_dir):
    T = len(p2p_results)
    hours = np.arange(T)

    kwh = np.array([float(np.sum(r.P_star)) if r.P_star is not None else 0.0
                    for r in p2p_results])

    avg_price = np.full(T, np.nan)
    for r in p2p_results:
        if r.pi_star is not None and r.P_star is not None:
            total = float(np.sum(r.P_star))
            if total > 1e-6:
                w = np.sum(r.P_star, axis=0) / total
                avg_price[r.k] = float(np.dot(w, r.pi_star))

    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    fig.suptitle("Fig 3 — Flujos del mercado P2P: energía y precios",
                 fontsize=12, fontweight="bold")

    ax = axes[0]
    bars = ax.bar(hours, kwh, color="#534AB7", alpha=0.80, width=0.7)
    for bar in bars:
        h = bar.get_height()
        if h > 0.05:
            ax.text(bar.get_x()+bar.get_width()/2, h+0.005*kwh.max(),
                    f"{h:.1f}", ha="center", va="bottom", fontsize=7)
    ax.set_ylabel("kWh")
    ax.set_title(f"Energía intercambiada en el mercado P2P  "
                 f"(total={kwh.sum():.1f} kWh)")

    ax = axes[1]
    valid = ~np.isnan(avg_price)
    if valid.any():
        ax.plot(hours[valid], avg_price[valid], "o-",
                color="#D85A30", linewidth=1.8, markersize=6,
                label="Precio promedio ponderado")
        ax.legend(fontsize=9)
    ax.set_ylabel("Precio (COP/kWh)")
    ax.set_xlabel("Hora del perfil")
    ax.set_title("Precios de equilibrio — juego de Stackelberg")
    axes[-1].set_xticks(hours[::max(1, T//12)])
    fig.tight_layout()
    return _save(fig, os.path.join(out_dir, "fig3_mercado_p2p.png"))


# ── Fig 4 ─────────────────────────────────────────────────────────────────────

def plot_metrics_hourly(p2p_results, out_dir):
    T = len(p2p_results)
    hours = np.arange(T)
    SC = np.array([r.SC for r in p2p_results])
    SS = np.array([r.SS for r in p2p_results])
    IE = np.array([r.IE for r in p2p_results])
    Wj = np.array([r.Wj_total for r in p2p_results])
    Wi = np.array([r.Wi_total for r in p2p_results])

    fig = plt.figure(figsize=(12, 9))
    fig.suptitle("Fig 4 — Métricas horarias del mercado P2P",
                 fontsize=12, fontweight="bold")
    gs = GridSpec(3, 2, figure=fig, hspace=0.50, wspace=0.32)

    for ax_pos, data, color, title, ylabel in [
        (gs[0, 0], SC, "#1D9E75", "Self-consumption (SC)", "SC"),
        (gs[0, 1], SS, "#378ADD", "Self-sufficiency (SS)", "SS"),
    ]:
        ax = fig.add_subplot(ax_pos)
        ax.bar(hours, data, color=color, alpha=0.80)
        ax.axhline(data.mean(), color=color, linewidth=1.5, linestyle="--",
                   label=f"Media={data.mean():.3f}")
        ax.set_ylim(0, 1.05)
        ax.set_title(title); ax.set_ylabel(ylabel)
        ax.legend(fontsize=8)
        ax.set_xticks(hours[::max(1, T//12)])

    ax = fig.add_subplot(gs[1, :])
    ie_colors = ["#1D9E75" if v >= -0.2 else "#D85A30" for v in IE]
    ax.bar(hours, IE, color=ie_colors, alpha=0.80)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axhline(IE.mean(), color="#534AB7", linewidth=1.5, linestyle="--",
               label=f"Media={IE.mean():.3f}")
    ax.set_ylim(-1.15, 1.15)
    ax.set_title("Índice de equidad (IE)  "
                 "[−1=favorece vendedores  0=equitativo  +1=favorece compradores]")
    ax.set_ylabel("IE"); ax.legend(fontsize=8)
    ax.set_xticks(hours[::max(1, T//12)])

    ax = fig.add_subplot(gs[2, :])
    ax.bar(hours, Wj, label="Wj (vendedores)", color="#1D9E75", alpha=0.75)
    ax.bar(hours, Wi, bottom=Wj, label="Wi (compradores)", color="#378ADD", alpha=0.75)
    ax.set_title("Bienestar total Wj + Wi por hora")
    ax.set_ylabel("Bienestar"); ax.legend(fontsize=8)
    ax.set_xlabel("Hora del perfil")
    ax.set_xticks(hours[::max(1, T//12)])

    return _save(fig, os.path.join(out_dir, "fig4_metricas_horarias.png"))


# ── Fig 5 ─────────────────────────────────────────────────────────────────────

def plot_regulatory_comparison(cr, out_dir, currency="COP"):
    esc = ["P2P", "C1", "C2", "C3", "C4"]
    labels_short = {
        "P2P": "P2P\n(Stackelberg+RD)",
        "C1":  "C1\nCREG 174/2021",
        "C2":  "C2\nBilateral PPA",
        "C3":  "C3\nMercado spot",
        "C4":  "C4\nCREG 101 072",
    }
    values = [cr.net_benefit.get(e, 0) for e in esc]
    sc_v   = [cr.self_consumption.get(e, 0) for e in esc]
    ss_v   = [cr.self_sufficiency.get(e, 0) for e in esc]
    ie_v   = [cr.equity_index.get(e, 0) for e in esc]
    colors = [COLORS_ESC[e] for e in esc]
    xlabs  = [labels_short[e] for e in esc]

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    fig.suptitle("Fig 5 — Comparación regulatoria: cinco escenarios",
                 fontsize=12, fontweight="bold")

    # Ganancia neta
    ax = axes[0, 0]
    bars = ax.bar(xlabs, values, color=colors, alpha=0.85)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title(f"Ganancia neta ({currency}/período)")
    ax.set_ylabel(currency)
    rng = max(values) - min(values) if values else 1
    for bar, val in zip(bars, values):
        sign = 1 if val >= 0 else -1
        ax.text(bar.get_x()+bar.get_width()/2,
                val + sign * rng * 0.02,
                f"{val/1e6:.2f}M" if abs(val) > 1e5 else f"{val:,.0f}",
                ha="center",
                va="bottom" if val >= 0 else "top",
                fontsize=8)

    # SC
    ax = axes[0, 1]
    ax.bar(xlabs, sc_v, color=colors, alpha=0.85)
    ax.set_ylim(0, 1.1)
    ax.set_title("Self-consumption (SC)")
    ax.set_ylabel("SC")

    # SS
    ax = axes[1, 0]
    ax.bar(xlabs, ss_v, color=colors, alpha=0.85)
    ax.set_ylim(0, 1.1)
    ax.set_title("Self-sufficiency (SS)")
    ax.set_ylabel("SS")

    # IE
    ax = axes[1, 1]
    ie_c = ["#1D9E75" if v >= -0.2 else "#D85A30" for v in ie_v]
    ax.bar(xlabs, ie_v, color=ie_c, alpha=0.85)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylim(-1.2, 1.2)
    ax.set_title("Índice de equidad (IE)")
    ax.set_ylabel("IE  [−1 a +1]")
    if cr.price_of_fairness is not None:
        ax.text(0.98, 0.05,
                f"PoF(P2P vs C4) = {cr.price_of_fairness:.3f}",
                transform=ax.transAxes, ha="right", fontsize=8,
                color="#534AB7",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="#534AB7", alpha=0.8))

    fig.tight_layout()
    return _save(fig, os.path.join(out_dir, "fig5_comparacion_regulatoria.png"))


# ── Fig 6 ─────────────────────────────────────────────────────────────────────

def plot_per_agent(cr, agent_names, out_dir, currency="COP"):
    esc   = ["P2P", "C1", "C2", "C3", "C4"]
    N     = cr.n_agents
    x     = np.arange(N)
    w     = 0.15
    names = (agent_names[:N] if len(agent_names) >= N
             else [f"A{i+1}" for i in range(N)])

    fig, ax = plt.subplots(figsize=(13, 5))
    fig.suptitle("Fig 6 — Ganancia neta por agente y escenario",
                 fontsize=12, fontweight="bold")

    for idx, e in enumerate(esc):
        vals = [cr.net_benefit_per_agent[e][n] for n in range(N)]
        ax.bar(x + (idx-2)*w, vals, w, label=e,
               color=COLORS_ESC[e], alpha=0.82)

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel(f"{currency}/período")
    ax.set_title(f"Ganancia neta por institución ({currency})")
    ax.legend(title="Escenario", ncol=5, fontsize=9)

    if cr.static_spread_24h is not None:
        total_spread = float(np.sum(cr.static_spread_24h))
        ax.text(0.01, 0.97,
                f"Spread inef. estática C4: {total_spread:.2f} kWh/período",
                transform=ax.transAxes, va="top", fontsize=8,
                color="#D4537E",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="#D4537E", alpha=0.8))

    fig.tight_layout()
    return _save(fig, os.path.join(out_dir, "fig6_ganancia_por_agente.png"))


# ── Función principal ─────────────────────────────────────────────────────────

def generate_all_plots(D, G, G_klim, p2p_results, cr,
                       agent_names, out_dir, currency="COP"):
    """
    Genera las 6 figuras y las guarda en out_dir.
    Retorna lista de rutas de archivos generados.
    """
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    print(f"\n  Generando gráficas → {out_dir}")

    steps = [
        ("Fig 1 — Perfiles D, G, G_klim",
         lambda: plot_profiles(D, G, G_klim, agent_names, out_dir)),
        ("Fig 2 — Clasificación vendedor/comprador",
         lambda: plot_classification(p2p_results, agent_names, out_dir)),
        ("Fig 3 — Flujos mercado P2P",
         lambda: plot_market_flows(p2p_results, agent_names, out_dir)),
        ("Fig 4 — Métricas horarias SC/SS/IE",
         lambda: plot_metrics_hourly(p2p_results, out_dir)),
        ("Fig 5 — Comparación regulatoria",
         lambda: plot_regulatory_comparison(cr, out_dir, currency)),
        ("Fig 6 — Ganancia por agente",
         lambda: plot_per_agent(cr, agent_names, out_dir, currency)),
    ]

    for label, fn in steps:
        try:
            path = fn()
            paths.append(path)
            print(f"    ✓ {label}")
        except Exception as e:
            print(f"    ✗ {label}: {e}")

    print(f"  {len(paths)}/6 gráficas listas.")
    return paths


# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICAS DE SENSIBILIDAD Y FACTIBILIDAD (puntos 5 y 6)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_sensitivity_pgb(sa_results, out_dir, currency="COP"):
    """Fig 7 — Sensibilidad al precio de bolsa PGB."""
    from analysis.sensitivity import SensitivityResult
    pgb    = [r.param_value for r in sa_results]
    esc    = ["P2P", "C1", "C2", "C3", "C4"]
    colors = {e: COLORS_ESC[e] for e in esc}

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Fig 7 — Análisis de sensibilidad: variación precio de bolsa XM (PGB)",
                 fontsize=12, fontweight="bold")

    # Panel 1: ganancia neta por escenario
    ax = axes[0]
    for e in esc:
        vals = [r.net_benefit[e] for r in sa_results]
        ax.plot(pgb, vals, "o-", color=colors[e], linewidth=2,
                markersize=5, label=e)
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xlabel("PGB (COP/kWh)")
    ax.set_ylabel(f"Ganancia neta ({currency}/período)")
    ax.set_title("Ganancia neta vs precio de bolsa")
    ax.legend(fontsize=8)

    # Marcar punto base
    base_idx = min(range(len(pgb)), key=lambda i: abs(pgb[i] - 280))
    for e in esc:
        ax.axvline(pgb[base_idx], color="gray", linewidth=0.8,
                   linestyle=":", alpha=0.6)

    # Panel 2: IE del P2P
    ax = axes[1]
    ie_vals = [r.ie_p2p for r in sa_results]
    ax.plot(pgb, ie_vals, "s-", color=COLORS_ESC["P2P"],
            linewidth=2, markersize=6)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.fill_between(pgb, ie_vals, 0,
                    where=[v >= 0 for v in ie_vals],
                    alpha=0.15, color="#1D9E75", label="IE ≥ 0")
    ax.fill_between(pgb, ie_vals, 0,
                    where=[v < 0 for v in ie_vals],
                    alpha=0.15, color="#D85A30", label="IE < 0")
    ax.set_ylim(-1.2, 1.2)
    ax.set_xlabel("PGB (COP/kWh)")
    ax.set_ylabel("IE")
    ax.set_title("Índice de equidad P2P vs PGB")
    ax.legend(fontsize=8)

    # Panel 3: PoF
    ax = axes[2]
    pof_vals = [r.pof for r in sa_results]
    ax.plot(pgb, pof_vals, "^-", color="#7F77DD",
            linewidth=2, markersize=6)
    ax.axhline(1.0, color="gray", linewidth=0.8, linestyle="--",
               label="PoF=1 (sin pérdida)")
    ax.set_xlabel("PGB (COP/kWh)")
    ax.set_ylabel("PoF (P2P vs C4)")
    ax.set_title("Price of Fairness vs precio de bolsa")
    ax.legend(fontsize=8)

    # Marcar escenarios relevantes
    for ax in axes:
        ax.axvline(280, color="#888", linewidth=0.8, linestyle=":",
                   label="Base 280")
        ax.axvline(420, color="#D85A30", linewidth=0.8, linestyle=":",
                   label="El Niño 420")

    fig.tight_layout()
    return _save(fig, os.path.join(out_dir, "fig7_sensibilidad_pgb.png"))


def plot_sensitivity_pv(sa_pv_results, D, out_dir, agent_names=None):
    """Fig 8 — Sensibilidad a la cobertura PV."""
    if not sa_pv_results:
        return None

    factors  = [r.param_value for r in sa_pv_results]
    base_cov = 0.113  # cobertura actual MTE
    cov_pct  = [f * base_cov * 100 for f in factors]

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    fig.suptitle("Fig 8 — Análisis de sensibilidad: cobertura PV",
                 fontsize=12, fontweight="bold")

    # Panel 1: ganancia neta P2P y C4
    ax = axes[0, 0]
    p2p_vals = [r.net_benefit["P2P"] for r in sa_pv_results]
    c4_vals  = [r.net_benefit["C4"]  for r in sa_pv_results]
    ax.plot(cov_pct, p2p_vals, "o-", color=COLORS_ESC["P2P"],
            linewidth=2, label="P2P")
    ax.plot(cov_pct, c4_vals, "s-", color=COLORS_ESC["C4"],
            linewidth=2, label="C4")
    ax.axhline(0, color="black", linewidth=0.8)
    # Marcar cruce P2P=C4
    for i in range(len(sa_pv_results)-1):
        if (p2p_vals[i] < c4_vals[i]) != (p2p_vals[i+1] < c4_vals[i+1]):
            xc = (cov_pct[i] + cov_pct[i+1]) / 2
            ax.axvline(xc, color="#534AB7", linewidth=1.5,
                       linestyle="--", alpha=0.7, label=f"Cruce ~{xc:.0f}%")
    ax.axvline(11.3, color="gray", linewidth=0.8, linestyle=":",
               label="Actual 11.3%")
    ax.set_xlabel("Cobertura PV (%)")
    ax.set_ylabel("COP/período")
    ax.set_title("P2P vs C4 según cobertura solar")
    ax.legend(fontsize=8)

    # Panel 2: horas de mercado activo
    ax = axes[0, 1]
    market_h = [r.market_hours for r in sa_pv_results]
    ax.bar(cov_pct, market_h, color="#534AB7", alpha=0.75,
           width=max(cov_pct)/len(cov_pct)*0.7)
    ax.set_xlabel("Cobertura PV (%)")
    ax.set_ylabel("Horas con mercado P2P activo")
    ax.set_title("Horas de mercado activo vs cobertura")
    ax.axhline(24, color="gray", linewidth=0.8, linestyle="--",
               label="Máximo 24h")
    ax.legend(fontsize=8)

    # Panel 3: kWh intercambiados
    ax = axes[1, 0]
    kwh = [r.kwh_p2p for r in sa_pv_results]
    ax.plot(cov_pct, kwh, "o-", color="#1D9E75", linewidth=2, markersize=6)
    ax.set_xlabel("Cobertura PV (%)")
    ax.set_ylabel("kWh P2P intercambiados")
    ax.set_title("Volumen del mercado P2P")

    # Panel 4: IE y SS
    ax = axes[1, 1]
    ie_v = [r.ie_p2p for r in sa_pv_results]
    ss_v = [r.ss_p2p for r in sa_pv_results]
    ax2  = ax.twinx()
    ax.plot(cov_pct, ie_v, "o-", color="#D85A30", linewidth=2,
            markersize=5, label="IE (izq)")
    ax2.plot(cov_pct, ss_v, "s--", color="#378ADD", linewidth=2,
             markersize=5, label="SS (der)")
    ax.set_xlabel("Cobertura PV (%)")
    ax.set_ylabel("IE  [−1 a +1]")
    ax2.set_ylabel("SS")
    ax.set_title("Equidad y autosuficiencia vs cobertura")
    ax.axhline(0, color="black", linewidth=0.5)
    lines1, _ = ax.get_legend_handles_labels()
    lines2, _ = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, ["IE", "SS"], fontsize=8)

    fig.tight_layout()
    return _save(fig, os.path.join(out_dir, "fig8_sensibilidad_pv.png"))


def plot_feasibility(fa_desertion, fa_creg, p2p_results,
                     pi_bolsa, agent_names, out_dir):
    """Fig 9 — Análisis de factibilidad: deserción y cumplimiento CREG."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Fig 9 — Análisis de factibilidad",
                 fontsize=12, fontweight="bold")

    T = len(p2p_results)
    hours = np.arange(T)

    # Panel 1: precio P2P vs precio bolsa
    ax = axes[0]
    avg_p = fa_desertion.avg_p2p_price_by_hour
    valid = ~np.isnan(avg_p)
    if valid.any():
        ax.plot(hours[valid], avg_p[valid], "o-",
                color="#534AB7", linewidth=2, markersize=6,
                label="Precio P2P (equilibrio)")
    ax.plot(hours, pi_bolsa[:T], "s--",
            color="#D85A30", linewidth=1.5, markersize=4,
            label="Precio bolsa (pi_bolsa)")
    ax.fill_between(hours,
                    np.where(valid, avg_p, np.nan),
                    pi_bolsa[:T],
                    where=valid & (avg_p >= pi_bolsa[:T]),
                    alpha=0.20, color="#1D9E75",
                    label="P2P ≥ bolsa (no deserción)")
    ax.fill_between(hours,
                    np.where(valid, avg_p, np.nan),
                    pi_bolsa[:T],
                    where=valid & (avg_p < pi_bolsa[:T]),
                    alpha=0.20, color="#D85A30",
                    label="P2P < bolsa (riesgo deserción)")
    crit = fa_desertion.critical_pgb_threshold
    if crit:
        ax.axhline(crit, color="#7F77DD", linewidth=1.5, linestyle=":",
                   label=f"Umbral {crit:.0f} COP/kWh")
    ax.set_xlabel("Hora del perfil")
    ax.set_ylabel("COP/kWh")
    ax.set_title("FA-1: Condición de deserción\n"
                 + ("Sin riesgo en perfil actual"
                    if fa_desertion.condition_never_met
                    else "⚠ Riesgo en algunas horas"))
    ax.legend(fontsize=8)

    # Panel 2: participación por agente en C4 (regla 10%)
    ax = axes[1]
    names = list(fa_creg.max_supply_share_by_agent.keys())
    shares = [fa_creg.max_supply_share_by_agent[n] for n in names]
    bar_colors = ["#D85A30" if n in fa_creg.rule_10pct_violations
                  else "#1D9E75" for n in names]
    ax.barh(names, shares, color=bar_colors, alpha=0.80)
    ax.axvline(10, color="red", linewidth=1.5, linestyle="--",
               label="Límite 10% CREG 101 072")
    ax.set_xlabel("Participación media (% demanda comunidad)")
    ax.set_title("FA-2: Regla del 10%\n"
                 + ("✓ Todos cumplen" if fa_creg.rule_10pct_satisfied
                    else "✗ Violaciones detectadas"))
    ax.legend(fontsize=8)

    # Panel 3: capacidad máxima vs límite 100 kW
    ax = axes[2]
    cap_names = list(fa_creg.max_capacity_by_agent.keys())
    caps = [fa_creg.max_capacity_by_agent[n] for n in cap_names]
    bar_colors2 = ["#D85A30" if n in fa_creg.rule_100kw_violations
                   else "#1D9E75" for n in cap_names]
    ax.barh(cap_names, caps, color=bar_colors2, alpha=0.80)
    ax.axvline(100, color="red", linewidth=1.5, linestyle="--",
               label="Límite 100 kW CREG 101 072")
    ax.set_xlabel("Capacidad pico observada (kW)")
    ax.set_title("FA-2: Límite 100 kW\n"
                 + ("✓ Todos cumplen" if fa_creg.rule_100kw_satisfied
                    else "✗ Violaciones detectadas"))
    ax.legend(fontsize=8)

    fig.tight_layout()
    return _save(fig, os.path.join(out_dir, "fig9_factibilidad.png"))


def generate_sensitivity_plots(sa_pgb, sa_pv, findings,
                                agent_names, out_dir, currency="COP",
                                # parámetros opcionales para compatibilidad hacia atrás
                                fa_desertion=None, fa_creg=None,
                                p2p_results=None, pi_bolsa=None, D=None):
    """Genera las figuras 7 y 8 del análisis de sensibilidad.
    Firma compatible con la llamada desde main_simulation (findings como dict).
    """
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    print(f"\n  Gráficas de sensibilidad → {out_dir}")

    steps = [
        ("Fig 7 — Sensibilidad PGB",
         lambda: plot_sensitivity_pgb(sa_pgb, out_dir, currency)),
        ("Fig 8 — Sensibilidad cobertura PV",
         lambda: plot_sensitivity_pv(sa_pv, D, out_dir, agent_names)),
    ]
    # Fig 9 solo si se pasan los objetos de factibilidad
    if fa_desertion is not None and fa_creg is not None and p2p_results is not None:
        steps.append(("Fig 9 — Factibilidad",
                      lambda: plot_feasibility(fa_desertion, fa_creg, p2p_results,
                                               pi_bolsa, agent_names, out_dir)))

    for label, fn in steps:
        try:
            p = fn()
            if p:
                paths.append(p)
                print(f"    ✓ {label}")
        except Exception as e:
            print(f"    ✗ {label}: {e}")

    return paths
