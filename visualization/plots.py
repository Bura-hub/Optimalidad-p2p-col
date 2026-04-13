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

    fig = plt.figure(figsize=(13, 11))
    fig.suptitle("Fig 5 — Comparación regulatoria: cinco escenarios",
                 fontsize=12, fontweight="bold")
    gs5 = GridSpec(3, 2, figure=fig, hspace=0.42, wspace=0.32)

    # ── Fila 1: Ganancia neta  +  SC ─────────────────────────────────────
    ax = fig.add_subplot(gs5[0, 0])
    bars = ax.bar(xlabs, values, color=colors, alpha=0.85)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title(f"Ganancia neta ({currency}/período)")
    ax.set_ylabel(currency)
    rng = max(values) - min(values) if values else 1
    for bar, val in zip(bars, values):
        sign = 1 if val >= 0 else -1
        ax.text(bar.get_x() + bar.get_width() / 2,
                val + sign * rng * 0.02,
                f"{val/1e6:.2f}M" if abs(val) > 1e5 else f"{val:,.0f}",
                ha="center",
                va="bottom" if val >= 0 else "top",
                fontsize=8)

    ax = fig.add_subplot(gs5[0, 1])
    ax.bar(xlabs, sc_v, color=colors, alpha=0.85)
    ax.set_ylim(0, 1.1)
    ax.set_title("Self-consumption (SC)")
    ax.set_ylabel("SC")

    # ── Fila 2: SS  +  IE ────────────────────────────────────────────────
    ax = fig.add_subplot(gs5[1, 0])
    ax.bar(xlabs, ss_v, color=colors, alpha=0.85)
    ax.set_ylim(0, 1.1)
    ax.set_title("Self-sufficiency (SS)")
    ax.set_ylabel("SS")

    ax = fig.add_subplot(gs5[1, 1])
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

    # ── Fila 3: Distribución del excedente P2P — PS / PSR ────────────────
    # Solo aplica al escenario P2P. Muestra cómo se divide el surplus entre
    # compradores (PS) y vendedores (PSR).  Ref: Tabla VII Sofía Chacón (2025).
    ax_dist = fig.add_subplot(gs5[2, :])

    ps_val  = getattr(cr, "ps_p2p",  50.0)
    psr_val = getattr(cr, "psr_p2p", 50.0)

    # Barra apilada horizontal para P2P
    ax_dist.barh(["P2P"], [ps_val],  color="#378ADD", alpha=0.85,
                 label=f"PS  (compradores) = {ps_val:.1f}%")
    ax_dist.barh(["P2P"], [psr_val], left=[ps_val], color="#D85A30", alpha=0.85,
                 label=f"PSR (vendedores)  = {psr_val:.1f}%")

    # Línea de referencia 50/50
    ax_dist.axvline(50, color="black", lw=1.0, ls="--", alpha=0.5,
                    label="Reparto equitativo 50/50")

    # Etiquetas dentro de las barras
    if ps_val > 5:
        ax_dist.text(ps_val / 2, 0,
                     f"{ps_val:.1f}%", ha="center", va="center",
                     fontsize=10, fontweight="bold", color="white")
    if psr_val > 5:
        ax_dist.text(ps_val + psr_val / 2, 0,
                     f"{psr_val:.1f}%", ha="center", va="center",
                     fontsize=10, fontweight="bold", color="white")

    ax_dist.set_xlim(0, 100)
    ax_dist.set_xlabel("Porcentaje del excedente P2P (%)")
    ax_dist.set_title(
        "Distribución del excedente P2P entre roles  "
        f"(IE = {cr.equity_index.get('P2P', 0):.4f}  |  "
        f"PoF P2P vs C4 = {cr.price_of_fairness:.4f})"
        if cr.price_of_fairness is not None else
        "Distribución del excedente P2P entre roles"
    )
    ax_dist.legend(fontsize=9, loc="lower right")

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
    """Fig 7 — Sensibilidad al precio de bolsa PGB con contexto hidrológico colombiano."""
    pgb    = [r.param_value for r in sa_results]
    esc    = ["P2P", "C1", "C2", "C3", "C4"]
    colors = {e: COLORS_ESC[e] for e in esc}

    # ── Zonas hidrológicas colombianas (COP/kWh bolsa XM) ──────────────────
    # Referencia: histórico XM, informes CREG, El Niño 2023-2024
    _hydro_zones = [
        # (x_ini, x_fin, color, alpha, etiqueta)
        (100,  280, "#1D9E75", 0.08, "Hidrología\nfavorable"),
        (280,  350, "#F0C040", 0.10, "Sequía\nmoderada"),
        (350,  450, "#D85A30", 0.10, "El Niño\nsevero"),
        (450,  600, "#8B0000", 0.10, "Escasez\ncrítica"),
    ]
    _hydro_lines = [
        (280, "#888888", ":"),    # umbral sequía
        (350, "#D85A30", "--"),   # umbral El Niño
        (450, "#8B0000", "--"),   # umbral escasez
    ]

    def _add_hydro_context(ax, pgb_list, annotate=False):
        xmin, xmax = min(pgb_list), max(pgb_list)
        for x0, x1, c, a, lbl in _hydro_zones:
            x0c, x1c = max(x0, xmin - 10), min(x1, xmax + 10)
            if x0c < x1c:
                ax.axvspan(x0c, x1c, color=c, alpha=a, zorder=0)
        for xv, c, ls in _hydro_lines:
            if xmin <= xv <= xmax:
                ax.axvline(xv, color=c, linewidth=0.9, linestyle=ls,
                           alpha=0.75, zorder=1)
        if annotate:
            ymin_ax, ymax_ax = ax.get_ylim()
            y_text = ymin_ax + 0.97 * (ymax_ax - ymin_ax)
            for x0, x1, c, a, lbl in _hydro_zones:
                xc = (max(x0, xmin) + min(x1, xmax)) / 2
                if xmin < xc < xmax:
                    ax.text(xc, y_text, lbl, fontsize=6.5, ha="center",
                            va="top", color=c if c != "#F0C040" else "#897000",
                            style="italic",
                            bbox=dict(fc="white", ec="none", alpha=0.6, pad=1))

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(
        "Fig 7 — Análisis de sensibilidad: variación precio de bolsa XM (PGB)\n"
        "Contexto hidrológico colombiano: normal → sequía → El Niño → escasez",
        fontsize=11, fontweight="bold")

    # ── Panel 1: ganancia neta por escenario ────────────────────────────────
    ax = axes[0]
    for e in esc:
        vals = [r.net_benefit[e] for r in sa_results]
        ax.plot(pgb, vals, "o-", color=colors[e], linewidth=2,
                markersize=5, label=e, zorder=3)
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", zorder=2)
    ax.set_xlabel("PGB (COP/kWh)")
    ax.set_ylabel(f"Ganancia neta ({currency}/período)")
    ax.set_title("Ganancia neta vs precio de bolsa")
    ax.legend(fontsize=8, loc="upper left")
    _add_hydro_context(ax, pgb, annotate=True)

    # ── Panel 2: IE del P2P ──────────────────────────────────────────────────
    ax = axes[1]
    ie_vals = [r.ie_p2p for r in sa_results]
    ax.plot(pgb, ie_vals, "s-", color=COLORS_ESC["P2P"],
            linewidth=2, markersize=6, zorder=3)
    ax.axhline(0, color="black", linewidth=0.8, zorder=2)
    ax.fill_between(pgb, ie_vals, 0,
                    where=[v >= 0 for v in ie_vals],
                    alpha=0.20, color="#1D9E75", label="IE ≥ 0  (equitativo)", zorder=2)
    ax.fill_between(pgb, ie_vals, 0,
                    where=[v < 0 for v in ie_vals],
                    alpha=0.20, color="#D85A30", label="IE < 0  (inequitativo)", zorder=2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_xlabel("PGB (COP/kWh)")
    ax.set_ylabel("IE")
    ax.set_title("Índice de equidad P2P vs PGB")
    ax.legend(fontsize=8)
    _add_hydro_context(ax, pgb, annotate=False)

    # ── Panel 3: PoF ─────────────────────────────────────────────────────────
    ax = axes[2]
    pof_vals = [r.pof for r in sa_results]
    ax.plot(pgb, pof_vals, "^-", color="#7F77DD",
            linewidth=2, markersize=6, zorder=3)
    ax.axhline(1.0, color="gray", linewidth=0.8, linestyle="--",
               label="PoF=1 (sin pérdida de eficiencia)", zorder=2)
    ax.axhline(0.0, color="black", linewidth=0.5, zorder=2)
    ax.set_xlabel("PGB (COP/kWh)")
    ax.set_ylabel("PoF (P2P vs C4)")
    ax.set_title("Price of Fairness vs precio de bolsa")
    ax.legend(fontsize=8)
    _add_hydro_context(ax, pgb, annotate=False)

    # ── Leyenda compartida de zonas (patch manual) ───────────────────────────
    legend_patches = [
        mpatches.Patch(color="#1D9E75", alpha=0.35, label="Hidrología favorable"),
        mpatches.Patch(color="#F0C040", alpha=0.45, label="Sequía moderada (>280)"),
        mpatches.Patch(color="#D85A30", alpha=0.35, label="El Niño severo (>350)"),
        mpatches.Patch(color="#8B0000", alpha=0.35, label="Escasez crítica (>450)"),
    ]
    fig.legend(handles=legend_patches, loc="lower center", ncol=4,
               fontsize=8, framealpha=0.8,
               bbox_to_anchor=(0.5, -0.04))

    fig.tight_layout(rect=[0, 0.06, 1, 1])
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


def plot_sensitivity_ppa(sa_ppa_results: list, agent_names: list,
                         pi_gb: float, pi_gs: float,
                         out_dir: str, currency: str = "COP") -> str:
    """Fig 10 — Sensibilidad al precio del contrato bilateral (SA-3 §3.8)."""
    if not sa_ppa_results:
        return None

    factors  = [r["ppa_factor"] for r in sa_ppa_results]
    pi_ppas  = [r["pi_ppa"]     for r in sa_ppa_results]
    x_label  = f"pi_ppa (COP/kWh)   [pi_gb={pi_gb:.0f} ← → pi_gs={pi_gs:.0f}]"

    # ── extraer series ──────────────────────────────────────────────────────
    nb_p2p = [r["net_benefit"]["P2P"] for r in sa_ppa_results]
    nb_c1  = [r["net_benefit"]["C1"]  for r in sa_ppa_results]
    nb_c2  = [r["net_benefit"]["C2"]  for r in sa_ppa_results]
    nb_c4  = [r["net_benefit"]["C4"]  for r in sa_ppa_results]

    # Beneficio C2 por agente
    N = len(sa_ppa_results[0]["net_per_agent_c2"])
    agent_c2 = {
        (agent_names[n] if n < len(agent_names) else f"A{n+1}"):
        [r["net_per_agent_c2"][n] for r in sa_ppa_results]
        for n in range(N)
    }

    # Desglose gen vs consumidor
    surp_gen  = [r["surplus_gen_c2"]  for r in sa_ppa_results]
    sav_cons  = [r["saving_cons_c2"]  for r in sa_ppa_results]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle(
        "Fig 10 — SA-3: Sensibilidad al precio del contrato bilateral PPA (C2)",
        fontsize=12, fontweight="bold")

    # ── Panel 1: escenarios agregados ──────────────────────────────────────
    ax = axes[0]
    ax.plot(pi_ppas, nb_p2p, "o-", color=COLORS_ESC["P2P"],
            linewidth=2.5, markersize=5, label="P2P (referencia)")
    ax.plot(pi_ppas, nb_c2,  "s-", color=COLORS_ESC["C2"],
            linewidth=2.5, markersize=5, label="C2 Bilateral PPA")
    ax.plot(pi_ppas, nb_c1,  "--", color=COLORS_ESC["C1"],
            linewidth=1.5, alpha=0.7, label="C1 CREG 174")
    ax.plot(pi_ppas, nb_c4,  "--", color=COLORS_ESC["C4"],
            linewidth=1.5, alpha=0.7, label="C4 CREG 101 072")
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    # Punto base (factor=0.5)
    idx_base = min(range(len(factors)), key=lambda i: abs(factors[i] - 0.5))
    ax.axvline(pi_ppas[idx_base], color="gray", linewidth=1,
               linestyle=":", label=f"Base (f=0.5)")
    ax.set_xlabel(x_label)
    ax.set_ylabel(f"Beneficio neto ({currency}/período)")
    ax.set_title("Beneficio agregado vs pi_ppa")
    ax.legend(fontsize=8)

    # ── Panel 2: beneficio C2 por agente ───────────────────────────────────
    ax = axes[1]
    for idx_n, (name, vals) in enumerate(agent_c2.items()):
        ax.plot(pi_ppas, vals, "o-",
                color=COLORS_AGT[idx_n % len(COLORS_AGT)],
                linewidth=2, markersize=5, label=name)
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.axvline(pi_ppas[idx_base], color="gray", linewidth=1, linestyle=":")
    ax.set_xlabel(x_label)
    ax.set_ylabel(f"Beneficio neto ({currency}/período)")
    ax.set_title("C2: beneficio por agente vs pi_ppa")
    ax.legend(fontsize=8)

    # ── Panel 3: reparto excedente (gen vs consumidor) ─────────────────────
    ax = axes[2]
    ax.stackplot(pi_ppas, surp_gen, sav_cons,
                 labels=["Beneficio generadores (prima PPA)",
                         "Ahorro compradores (PPA < pi_gs)"],
                 colors=[COLORS_ESC["C1"], COLORS_ESC["C3"]],
                 alpha=0.75)
    ax.plot(pi_ppas, nb_c2, "k--", linewidth=1.5, label="C2 total")
    ax.axvline(pi_ppas[idx_base], color="gray", linewidth=1, linestyle=":")
    ax.set_xlabel(x_label)
    ax.set_ylabel(f"Valor ({currency}/período)")
    ax.set_title("Reparto del excedente C2:\ngeneradores vs compradores")
    ax.legend(fontsize=8)

    fig.tight_layout()
    path = os.path.join(out_dir, "fig10_sensibilidad_ppa.png")
    return _save(fig, path)


def plot_flow_breakdown(cr, out_dir: str, currency: str = "COP") -> str:
    """
    Fig 13 — Desglose de flujos por componente (Activity 3.2, Nivel 1).
    Barra apilada vertical: cada escenario muestra de dónde proviene su
    beneficio neto (autoconsumo, permutación, excedente, mercado P2P, etc.).
    """
    if not cr.flow_breakdown:
        return ""

    esc_order = ["P2P", "C1", "C3", "C4"]
    labels_esc = {
        "P2P": "P2P\n(Stackelberg+RD)",
        "C1":  "C1\nCREG 174",
        "C3":  "C3\nSpot",
        "C4":  "C4\nCREG 101 072",
    }
    # Colores por nombre de componente (consistentes entre escenarios)
    _COMP_COLORS = {
        "Autoconsumo":       "#1D9E75",
        "Permutación":       "#378ADD",
        "Excedente neto":    "#BA7517",
        "Excedente bolsa":   "#BA7517",
        "Prima vendedor":    "#534AB7",
        "Ahorro comprador":  "#7FBFFF",
        "Créditos PDE":      "#D4537E",
    }
    _DEFAULT_COLOR = "#AAAAAA"

    # Recopilar todos los componentes presentes en los escenarios elegidos
    all_comps = []
    for esc in esc_order:
        for comp in cr.flow_breakdown.get(esc, {}):
            if comp not in all_comps:
                all_comps.append(comp)

    x      = np.arange(len(esc_order))
    bar_w  = 0.52
    fig, axes = plt.subplots(1, 2, figsize=(14, 6),
                              gridspec_kw={"width_ratios": [2, 1]})
    fig.suptitle("Fig 13 — Desglose de flujos por componente  (Activity 3.2 — Nivel 1)",
                 fontsize=12, fontweight="bold")

    # ── Panel izquierdo: barras apiladas absolutas ────────────────────────
    ax = axes[0]
    bottoms = np.zeros(len(esc_order))

    for comp in all_comps:
        vals = []
        for esc in esc_order:
            vals.append(cr.flow_breakdown.get(esc, {}).get(comp, 0.0))
        vals = np.array(vals)
        color = _COMP_COLORS.get(comp, _DEFAULT_COLOR)
        bars  = ax.bar(x, vals, bar_w, bottom=bottoms,
                       label=comp, color=color, alpha=0.88)
        # Etiqueta dentro de la barra si es suficientemente alta
        for xi, (v, b) in enumerate(zip(vals, bottoms)):
            if v > max(sum(cr.flow_breakdown.get(esc, {}).values())
                       for esc in esc_order) * 0.05:
                ax.text(xi, b + v / 2,
                        f"{v/1e6:.2f}M" if abs(v) > 5e4 else f"{v:,.0f}",
                        ha="center", va="center", fontsize=7.5,
                        color="white", fontweight="bold")
        bottoms += vals

    ax.set_xticks(x)
    ax.set_xticklabels([labels_esc[e] for e in esc_order], fontsize=10)
    ax.set_ylabel(f"Beneficio neto ({currency})")
    ax.set_title("Composición absoluta del beneficio neto por escenario")
    ax.legend(title="Componente", fontsize=8, loc="upper right")
    ax.axhline(0, color="black", lw=0.8)

    # Anotación totales
    for xi, esc in enumerate(esc_order):
        total = sum(cr.flow_breakdown.get(esc, {}).values())
        ax.text(xi, total + bottoms.max() * 0.015,
                f"{total/1e6:.2f}M" if total > 5e4 else f"{total:,.0f}",
                ha="center", va="bottom", fontsize=8, fontweight="bold",
                color=COLORS_ESC.get(esc, "#333333"))

    # ── Panel derecho: barras apiladas normalizadas (%) ───────────────────
    ax2 = axes[1]
    bottoms2 = np.zeros(len(esc_order))

    for comp in all_comps:
        pcts = []
        for esc in esc_order:
            bd    = cr.flow_breakdown.get(esc, {})
            total = sum(bd.values())
            val   = bd.get(comp, 0.0)
            pcts.append(val / total * 100 if total > 1e-6 else 0.0)
        pcts  = np.array(pcts)
        color = _COMP_COLORS.get(comp, _DEFAULT_COLOR)
        ax2.bar(x, pcts, bar_w, bottom=bottoms2,
                label=comp, color=color, alpha=0.88)
        for xi, (p, b) in enumerate(zip(pcts, bottoms2)):
            if p > 6:
                ax2.text(xi, b + p / 2, f"{p:.0f}%",
                         ha="center", va="center", fontsize=7.5,
                         color="white", fontweight="bold")
        bottoms2 += pcts

    ax2.set_xticks(x)
    ax2.set_xticklabels([labels_esc[e] for e in esc_order], fontsize=10)
    ax2.set_ylim(0, 108)
    ax2.set_ylabel("Porcentaje del beneficio total (%)")
    ax2.set_title("Composición relativa (%)")
    ax2.axhline(100, color="black", lw=0.6, ls="--", alpha=0.4)

    fig.text(
        0.5, 0.01,
        "Autoconsumo = igual en todos los escenarios (min(G,D) × pi_gs).  "
        "La diferencia entre escenarios proviene del valor asignado a los excedentes.",
        ha="center", fontsize=8, style="italic", color="#555555",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    path = os.path.join(out_dir, "fig13_desglose_flujos.png")
    return _save(fig, path)


def plot_monthly_comparison(monthly: list, out_dir: str,
                            currency: str = "COP") -> str:
    """
    Fig 12 — Comparación mes a mes (modo --full, horizonte 6-8 meses).
    Cuatro paneles:
      A. Beneficio neto mensual por escenario (barras agrupadas)
      B. IE P2P mensual (línea + área de referencia)
      C. SC y SS mensual (P2P vs C4)
      D. Distribución PS/PSR mensual (barra apilada)
    """
    if not monthly:
        return ""

    labels  = [m["month_label"] for m in monthly]
    n_m     = len(labels)
    x       = np.arange(n_m)
    esc     = ["P2P", "C1", "C3", "C4"]
    colors  = {e: COLORS_ESC[e] for e in esc}
    w       = 0.20

    fig = plt.figure(figsize=(14, 12))
    fig.suptitle("Fig 12 — Comparación regulatoria mensual (horizonte completo)",
                 fontsize=12, fontweight="bold")
    gs12 = GridSpec(2, 2, figure=fig, hspace=0.42, wspace=0.32)

    # ── Panel A: Beneficio neto mensual ────────────────────────────────────
    ax_a = fig.add_subplot(gs12[0, :])   # fila 0, ambas columnas
    offsets = np.linspace(-(len(esc)-1)/2, (len(esc)-1)/2, len(esc)) * w
    for i, e in enumerate(esc):
        vals = [m["net_benefit"].get(e, 0) for m in monthly]
        bars = ax_a.bar(x + offsets[i], vals, w * 0.92,
                        label=e, color=colors[e], alpha=0.85)
        # Etiqueta en millones si supera 100k
        for bar, v in zip(bars, vals):
            if abs(v) > 1e5:
                ax_a.text(bar.get_x() + bar.get_width() / 2,
                          v + (max(max(m["net_benefit"].get(e2,0)
                                       for e2 in esc) for m in monthly) * 0.01),
                          f"{v/1e6:.1f}M",
                          ha="center", va="bottom", fontsize=6.5, rotation=90)

    ax_a.axhline(0, color="black", lw=0.8)
    ax_a.set_xticks(x); ax_a.set_xticklabels(labels)
    ax_a.set_ylabel(f"Beneficio neto ({currency})")
    ax_a.set_title(f"A — Beneficio neto mensual por escenario ({currency})")
    ax_a.legend(title="Escenario", ncol=len(esc), fontsize=9)

    # ── Panel B: IE P2P mensual ────────────────────────────────────────────
    ax_b = fig.add_subplot(gs12[1, 0])
    ie_vals = [m["ie_p2p"] for m in monthly]
    ax_b.plot(x, ie_vals, "o-", color=COLORS_ESC["P2P"], lw=2, markersize=7)
    ax_b.fill_between(x, ie_vals, alpha=0.15, color=COLORS_ESC["P2P"])
    ax_b.axhline(0,    color="black",   lw=0.8, ls="--", label="Neutro (IE=0)")
    ax_b.axhline(-0.2, color="#D85A30", lw=0.7, ls=":",
                 label="Umbral favorable vendedores")
    ax_b.set_ylim(-1.1, 1.1)
    ax_b.set_xticks(x); ax_b.set_xticklabels(labels, rotation=15, ha="right")
    ax_b.set_ylabel("IE  [−1, +1]")
    ax_b.set_title("B — Índice de equidad P2P mensual")
    ax_b.legend(fontsize=8)
    for xi, ie in zip(x, ie_vals):
        ax_b.annotate(f"{ie:.3f}", (xi, ie),
                      textcoords="offset points", xytext=(0, 7),
                      ha="center", fontsize=7.5)

    # ── Panel C: SC y SS mensual ───────────────────────────────────────────
    ax_c = fig.add_subplot(gs12[1, 1])
    sc_p2p = [m["sc"].get("P2P", 0) for m in monthly]
    ss_p2p = [m["ss"].get("P2P", 0) for m in monthly]
    sc_c4  = [m["sc"].get("C4",  0) for m in monthly]
    ss_c4  = [m["ss"].get("C4",  0) for m in monthly]

    ax_c.plot(x, sc_p2p, "o-",  color=COLORS_ESC["P2P"], lw=2,
              label="SC P2P", markersize=6)
    ax_c.plot(x, ss_p2p, "s--", color=COLORS_ESC["P2P"], lw=1.8,
              label="SS P2P", markersize=5, alpha=0.7)
    ax_c.plot(x, sc_c4,  "o-",  color=COLORS_ESC["C4"],  lw=1.5,
              label="SC C4",  markersize=5, alpha=0.7)
    ax_c.plot(x, ss_c4,  "s--", color=COLORS_ESC["C4"],  lw=1.2,
              label="SS C4",  markersize=4, alpha=0.5)

    ax_c.set_ylim(0, 1.05)
    ax_c.set_xticks(x); ax_c.set_xticklabels(labels, rotation=15, ha="right")
    ax_c.set_ylabel("[0, 1]")
    ax_c.set_title("C — SC y SS mensual: P2P vs C4")
    ax_c.legend(fontsize=8, ncol=2)

    fig.text(0.5, 0.01,
             "Nota: C1 usa balance mensual (permutación a pi_gs); "
             "C3 usa liquidación horaria a pi_bolsa; C4 distribuye via PDE estático.",
             ha="center", fontsize=8, style="italic", color="#555555")

    path = os.path.join(out_dir, "fig12_comparacion_mensual.png")
    return _save(fig, path)


def plot_convergence(conv_list: list, agent_names: list,
                     out_dir: str, currency: str = "COP") -> list:
    """
    Fig 11 — Convergencia del algoritmo RD + Stackelberg.
    Equivalente a Figs 9-11 del modelo base de Sofía Chacón.

    Por cada hora representativa genera una figura con 3 filas:
      Fila 1: Bienestar total W_j + W_i por iteración Stackelberg
      Fila 2: Evolución de precios π_i(t) — dinámica compradores
      Fila 3: Evolución de potencias P_ji(t) — dinámica vendedores

    Parámetros
    ----------
    conv_list : lista de ConvergenceData de ems_p2p.run_convergence()
    """
    os.makedirs(out_dir, exist_ok=True)
    saved = []

    for cd in conv_list:
        J = len(cd.seller_ids)
        I = len(cd.buyer_ids)
        n_iters = len(cd.welfare_iters)

        fig = plt.figure(figsize=(13, 10))
        fig.suptitle(
            f"Fig 11 — Convergencia RD + Stackelberg  |  Hora k={cd.hour}  "
            f"({'excedente' if float(np.sum(cd.G_net_j)) >= float(np.sum(cd.D_net_i)) else 'déficit'} comunitario)",
            fontsize=12, fontweight="bold",
        )
        gs_fig = GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

        # ── Fila 1: Bienestar por iteración Stackelberg ───────────────────
        ax_w = fig.add_subplot(gs_fig[0, :])
        iters = np.arange(1, n_iters + 1)
        Wj_arr = np.array([w[0] for w in cd.welfare_iters])
        Wi_arr = np.array([w[1] for w in cd.welfare_iters])
        W_total = Wj_arr + Wi_arr

        ax_w.plot(iters, Wj_arr,  "o--", color="#D85A30", lw=1.8,
                  label=r"$W_j$ (vendedores)", markersize=5)
        ax_w.plot(iters, Wi_arr,  "s--", color="#378ADD", lw=1.8,
                  label=r"$W_i$ (compradores)", markersize=5)
        ax_w.plot(iters, W_total, "D-",  color="#534AB7", lw=2.2,
                  label=r"$W = W_j + W_i$ (total)", markersize=6)
        ax_w.axhline(W_total[-1], color="#534AB7", lw=0.8, ls=":", alpha=0.6)
        ax_w.set_xlabel("Iteración Stackelberg")
        ax_w.set_ylabel(f"Bienestar ({currency})")
        ax_w.set_title("Convergencia del bienestar agregado por iteración Stackelberg")
        ax_w.set_xticks(iters)
        ax_w.legend(fontsize=8)

        # ── Fila 2: Evolución de precios π_i(t) ──────────────────────────
        ax_pi = fig.add_subplot(gs_fig[1, :])
        if cd.pi_traj.size > 0 and cd.t_buyers.size > 0:
            for i in range(I):
                buyer_name = (agent_names[cd.buyer_ids[i]]
                              if cd.buyer_ids[i] < len(agent_names)
                              else f"C{cd.buyer_ids[i]}")
                ax_pi.plot(cd.t_buyers, cd.pi_traj[i, :],
                           color=COLORS_AGT[i % len(COLORS_AGT)],
                           lw=1.8, label=f"$\\pi_{{{buyer_name}}}$")
            ax_pi.set_xlabel("Tiempo de integración $t$")
            ax_pi.set_ylabel(f"Precio ({currency}/kWh)")
            ax_pi.set_title("Dinámica de precios de compradores $\\pi_i(t)$ — última iteración")
            ax_pi.legend(fontsize=8, ncol=min(I, 3))
        else:
            ax_pi.text(0.5, 0.5, "Sin datos de trayectoria",
                       ha="center", va="center", transform=ax_pi.transAxes)

        # ── Fila 3: Evolución de potencias P_ji(t) ───────────────────────
        ax_pL = fig.add_subplot(gs_fig[2, 0])
        ax_pR = fig.add_subplot(gs_fig[2, 1])

        if cd.P_traj.size > 0 and cd.t_sellers.size > 0:
            pair_idx = 0
            for j in range(J):
                seller_name = (agent_names[cd.seller_ids[j]]
                               if cd.seller_ids[j] < len(agent_names)
                               else f"S{cd.seller_ids[j]}")
                for i in range(I):
                    buyer_name = (agent_names[cd.buyer_ids[i]]
                                  if cd.buyer_ids[i] < len(agent_names)
                                  else f"C{cd.buyer_ids[i]}")
                    ax_target = ax_pL if pair_idx < (J * I + 1) // 2 else ax_pR
                    ax_target.plot(
                        cd.t_sellers, cd.P_traj[j, i, :],
                        color=COLORS_AGT[pair_idx % len(COLORS_AGT)],
                        lw=1.6,
                        label=f"$P_{{{seller_name}→{buyer_name}}}$",
                    )
                    pair_idx += 1

            for ax_p, title in [(ax_pL, "Pares (1)"), (ax_pR, "Pares (2)")]:
                ax_p.set_xlabel("Tiempo de integración $t$")
                ax_p.set_ylabel("Potencia (kW)")
                ax_p.set_title(f"Dinámica de potencias $P_{{ji}}(t)$ — {title}")
                if ax_p.lines:
                    ax_p.legend(fontsize=7, ncol=1)
        else:
            ax_pL.text(0.5, 0.5, "Sin datos", ha="center", va="center",
                       transform=ax_pL.transAxes)

        # Anotaciones de valores finales
        P_final = cd.P_star_iters[-1]
        pi_final = cd.pi_star_iters[-1]
        info_lines = [
            f"Resultado final (iteración {n_iters}):",
            f"  Σ P_ji = {float(np.sum(P_final)):.3f} kW",
            f"  π_i ∈ [{float(pi_final.min()):.0f}, {float(pi_final.max()):.0f}] {currency}/kWh",
            f"  W_j = {cd.welfare_iters[-1][0]:.2f}   W_i = {cd.welfare_iters[-1][1]:.2f}",
            f"  Vendedores: {[agent_names[s] if s < len(agent_names) else s for s in cd.seller_ids]}",
            f"  Compradores: {[agent_names[b] if b < len(agent_names) else b for b in cd.buyer_ids]}",
        ]
        fig.text(0.01, 0.01, "\n".join(info_lines),
                 fontsize=7.5, family="monospace",
                 va="bottom", ha="left",
                 bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", alpha=0.8))

        path = os.path.join(out_dir, f"fig11_convergencia_h{cd.hour:04d}.png")
        saved.append(_save(fig, path))

    return saved


def plot_optimality(
    summary,           # OptimalitySummary
    out_dir: str,
    currency: str = "COP",
) -> str:
    """
    Fig 14 — Análisis de optimalidad P2P vs C4 hora a hora.

    Panel A (superior): timeline de categoría por hora (barras coloreadas)
    Panel B (medio)   : cumsum de Delta = B_P2P - B_C4 acumulado
    Panel C (inferior): GDR por hora activa + distribución categorial (pie)
    """
    hourly = summary.hourly_data
    if not hourly:
        return ""

    os.makedirs(out_dir, exist_ok=True)
    T = len(hourly)

    # ── Vectores ─────────────────────────────────────────────────────────────
    hours   = np.arange(T)
    deltas  = np.array([h.delta   for h in hourly])
    gdrs    = np.array([h.gdr     for h in hourly])
    cats    = [h.category for h in hourly]

    cat_colors = {
        "P2P_dom":  "#534AB7",   # violeta (P2P)
        "C4_dom":   "#D4537E",   # rosa   (C4)
        "neutral":  "#F0C040",   # amarillo (empate)
        "inactive": "#CCCCCC",   # gris (inactivo)
    }
    cat_labels = {
        "P2P_dom":  "P2P dominante",
        "C4_dom":   "C4 dominante",
        "neutral":  "Neutral",
        "inactive": "Inactivo",
    }

    color_arr = np.array([cat_colors[c] for c in cats])

    fig = plt.figure(figsize=(13, 10))
    gs  = GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35,
                   width_ratios=[3, 1])

    # ── Panel A: timeline de categorías ─────────────────────────────────────
    ax_a = fig.add_subplot(gs[0, :])
    bar_h = np.ones(T)
    for cat, clr in cat_colors.items():
        mask = np.array([c == cat for c in cats])
        if mask.any():
            ax_a.bar(hours[mask], bar_h[mask], color=clr, width=1.0,
                     label=cat_labels[cat], alpha=0.85)
    ax_a.set_xlim(0, T)
    ax_a.set_ylim(0, 1.2)
    ax_a.set_yticks([])
    ax_a.set_xlabel("Hora k")
    ax_a.set_title("A — Dominancia horaria: P2P vs C4", fontweight="bold")
    ax_a.legend(loc="upper right", ncol=4, fontsize=8)
    ax_a.axhline(1, color="#888", lw=0.4, ls="--")

    # ── Panel B: Delta acumulado ─────────────────────────────────────────────
    ax_b = fig.add_subplot(gs[1, :2])
    cumsum = np.cumsum(deltas)
    clr_line = "#534AB7" if cumsum[-1] >= 0 else "#D4537E"
    ax_b.plot(hours, cumsum / 1e3, color=clr_line, lw=1.5)
    ax_b.axhline(0, color="#555", lw=0.8, ls="--", alpha=0.7)
    ax_b.fill_between(hours, cumsum / 1e3, 0,
                      where=cumsum >= 0, color="#534AB7", alpha=0.15, label="P2P > C4")
    ax_b.fill_between(hours, cumsum / 1e3, 0,
                      where=cumsum < 0,  color="#D4537E", alpha=0.15, label="C4 > P2P")
    ax_b.set_xlabel("Hora k")
    ax_b.set_ylabel(f"ΔB acumulado (k{currency})")
    ax_b.set_title("B — Ventaja diferencial acumulada P2P − C4", fontweight="bold")
    ax_b.legend(fontsize=8)
    ax_b.set_xlim(0, T)

    # ── Panel C-izq: GDR por hora ────────────────────────────────────────────
    ax_cl = fig.add_subplot(gs[2, 0])
    active_mask = np.array([h.active for h in hourly])
    if active_mask.any():
        ax_cl.scatter(hours[active_mask], gdrs[active_mask],
                      s=4, c="#1D9E75", alpha=0.55, label="GDR hora activa")
        ax_cl.axhline(summary.gdr_mean, color="#1D9E75", lw=1.2, ls="--",
                      label=f"μ={summary.gdr_mean:.3f}")
    ax_cl.set_xlim(0, T)
    ax_cl.set_ylim(-0.05, 1.05)
    ax_cl.set_xlabel("Hora k")
    ax_cl.set_ylabel("GDR")
    ax_cl.set_title("C — Global Dispatch Ratio por hora", fontweight="bold")
    ax_cl.legend(fontsize=8)

    # ── Panel C-der: torta resumen ────────────────────────────────────────────
    ax_cr = fig.add_subplot(gs[2, 1])
    cat_order = ["P2P_dom", "C4_dom", "neutral", "inactive"]
    counts = [cats.count(c) for c in cat_order]
    nonzero_idx = [i for i, c in enumerate(counts) if c > 0]
    wedge_sizes  = [counts[i] for i in nonzero_idx]
    wedge_colors = [cat_colors[cat_order[i]] for i in nonzero_idx]
    wedge_labels = [f"{cat_labels[cat_order[i]]}\n{counts[i]}h" for i in nonzero_idx]
    ax_cr.pie(wedge_sizes, labels=wedge_labels, colors=wedge_colors,
              autopct="%1.0f%%", startangle=90,
              textprops={"fontsize": 7.5},
              wedgeprops={"edgecolor": "white", "linewidth": 0.8})
    ax_cr.set_title("D — Distribución categorial", fontweight="bold")

    # ── Anotación de resultados clave ─────────────────────────────────────────
    info = (f"B_P2P total = {summary.B_p2p_total/1e6:,.1f} M{currency}\n"
            f"B_C4  total = {summary.B_c4_total/1e6:,.1f} M{currency}\n"
            f"ΔTotal      = {summary.delta_total/1e3:,.0f} k{currency}\n"
            f"GDR medio   = {summary.gdr_mean:.3f}  (std {summary.gdr_std:.3f})\n"
            f"Umbral      = ±{summary.threshold_cop:,.0f} {currency}")
    fig.text(0.01, 0.01, info, fontsize=8, family="monospace",
             va="bottom", ha="left",
             bbox=dict(boxstyle="round,pad=0.4", fc="lightyellow", alpha=0.85))

    fig.suptitle("Fig 14 — Análisis de optimalidad horaria: P2P vs C4 (AGRC)\n"
                 "Clasificación por dominancia y eficiencia de clearing",
                 fontsize=11, fontweight="bold")

    path = os.path.join(out_dir, "fig14_optimalidad_horaria.png")
    return _save(fig, path)


def plot_sensitivity_pgs(sa_pgs_results: list, out_dir: str,
                         currency: str = "COP") -> str:
    """Fig 11 — SA-3: Sensibilidad al precio al usuario π_gs (tarifa retail).

    Panel superior : beneficio neto total  P2P vs C1 vs C4 en función de π_gs.
    Panel inferior : ventaja diferencial  ΔB = B_P2P − B_C4  e  IE_P2P.

    sa_pgs_results : lista de SensitivityResult (param_name='pi_gs').
    """
    if not sa_pgs_results:
        return ""

    pgs_vals  = [r.param_value      for r in sa_pgs_results]
    b_p2p     = [r.net_benefit["P2P"] for r in sa_pgs_results]
    b_c1      = [r.net_benefit["C1"]  for r in sa_pgs_results]
    b_c4      = [r.net_benefit["C4"]  for r in sa_pgs_results]
    delta_c4  = [p - c for p, c in zip(b_p2p, b_c4)]
    delta_c1  = [p - c for p, c in zip(b_p2p, b_c1)]
    ie_vals   = [r.ie_p2p            for r in sa_pgs_results]
    sc_vals   = [r.sc_p2p            for r in sa_pgs_results]
    ss_vals   = [r.ss_p2p            for r in sa_pgs_results]

    pi_gs_base = pgs_vals[len(pgs_vals) // 2]   # punto central del barrido

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle(
        f"Fig 11 — SA-3: Sensibilidad al precio al usuario π_gs\n"
        f"(π_gs base ≈ {pi_gs_base:.0f} {currency}/kWh — "
        f"re-ejecuta EMS completo en cada punto)",
        fontsize=11, fontweight="bold")

    clr = {"P2P": "#1f77b4", "C1": "#ff7f0e", "C4": "#2ca02c",
           "ΔC4": "#d62728", "ΔC1": "#9467bd"}

    # ── Panel A: beneficios absolutos ──────────────────────────────────────
    ax = axes[0, 0]
    ax.plot(pgs_vals, b_p2p, "o-", color=clr["P2P"], lw=2, label="P2P (Stackelberg+RD)")
    ax.plot(pgs_vals, b_c1,  "s--", color=clr["C1"], lw=1.5, label="C1 CREG 174/2021")
    ax.plot(pgs_vals, b_c4,  "^--", color=clr["C4"], lw=1.5, label="C4 CREG 101 072")
    ax.axvline(pi_gs_base, color="gray", lw=1, ls=":", alpha=0.7, label="π_gs base")
    ax.set_xlabel(f"π_gs ({currency}/kWh)"); ax.set_ylabel(f"Beneficio neto ({currency})")
    ax.set_title("A — Beneficio total por escenario")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    # ── Panel B: ventaja diferencial P2P vs C4 y vs C1 ────────────────────
    ax = axes[0, 1]
    ax.plot(pgs_vals, delta_c4, "o-", color=clr["ΔC4"], lw=2,
            label="P2P − C4 (ventaja vs regulación vigente)")
    ax.plot(pgs_vals, delta_c1, "s-", color=clr["ΔC1"], lw=1.5,
            label="P2P − C1 (ventaja vs CREG 174)")
    ax.axhline(0, color="black", lw=0.8, ls="--")
    ax.axvline(pi_gs_base, color="gray", lw=1, ls=":", alpha=0.7)
    ax.fill_between(pgs_vals, delta_c4, 0,
                    where=[d > 0 for d in delta_c4],
                    alpha=0.12, color=clr["ΔC4"], label="P2P superior a C4")
    ax.fill_between(pgs_vals, delta_c4, 0,
                    where=[d <= 0 for d in delta_c4],
                    alpha=0.12, color="red", label="C4 superior a P2P")
    ax.set_xlabel(f"π_gs ({currency}/kWh)"); ax.set_ylabel(f"Δ beneficio ({currency})")
    ax.set_title("B — Ventaja diferencial P2P")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{x:+,.0f}"))

    # ── Panel C: SC y SS ───────────────────────────────────────────────────
    ax = axes[1, 0]
    ax.plot(pgs_vals, sc_vals, "o-", color="#17becf", lw=2, label="SC (autoconsumo)")
    ax.plot(pgs_vals, ss_vals, "s-", color="#bcbd22", lw=2, label="SS (autosuficiencia)")
    ax.axvline(pi_gs_base, color="gray", lw=1, ls=":", alpha=0.7)
    ax.set_xlabel(f"π_gs ({currency}/kWh)"); ax.set_ylabel("Índice [0–1]")
    ax.set_title("C — SC y SS vs π_gs")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    ax.set_ylim(0, 1.05)

    # ── Panel D: IE y cuadro resumen ──────────────────────────────────────
    ax = axes[1, 1]
    colors_ie = ["#d62728" if ie < 0 else "#2ca02c" for ie in ie_vals]
    ax.bar(pgs_vals, ie_vals, color=colors_ie, alpha=0.7, width=(pgs_vals[-1]-pgs_vals[0])/(len(pgs_vals)*1.5))
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(pi_gs_base, color="gray", lw=1, ls=":", alpha=0.7)
    ax.set_xlabel(f"π_gs ({currency}/kWh)"); ax.set_ylabel("IE P2P")
    ax.set_title("D — Índice de Equidad vs π_gs\n(rojo: vendedores > compradores)")
    ax.grid(alpha=0.3, axis="y")
    ax.set_ylim(-1.05, 1.05)

    # Anotaciones de tendencia
    increasing = all(delta_c4[i] <= delta_c4[i+1] for i in range(len(delta_c4)-1))
    tend_label = "↑ creciente" if increasing else "no monótona"
    best_pgs   = pgs_vals[delta_c4.index(max(delta_c4))]
    axes[0, 1].annotate(
        f"Máx ventaja: π_gs={best_pgs:.0f}\nTendencia: {tend_label}",
        xy=(best_pgs, max(delta_c4)),
        xytext=(0.05, 0.85), textcoords="axes fraction",
        fontsize=8, color=clr["ΔC4"],
        arrowprops=dict(arrowstyle="->", color=clr["ΔC4"], lw=1),
    )

    fig.tight_layout()
    path = os.path.join(out_dir, "fig11_sensibilidad_pgs.png")
    return _save(fig, path)


def plot_c1_vs_c4(
    cr,
    agent_names: list,
    D: np.ndarray,
    G_klim: np.ndarray,
    pi_bolsa: np.ndarray,
    pde: np.ndarray,
    pi_gs: float,
    out_dir: str,
    currency: str = "COP",
) -> str:
    """
    Fig 15 — Comparación directa C1 (CREG 174 AGPE) vs C4 (CREG 101 072 AGRC).

    Panel A: beneficio neto por agente — barras enfrentadas C1 vs C4
    Panel B: diferencia horaria ΔB = B_C1_k - B_C4_k a lo largo del período
    Panel C: ΔB vs pi_bolsa horario (dispersión con regresión local)
    """
    N = cr.n_agents
    T = D.shape[1]
    names = (agent_names[:N] if len(agent_names) >= N
             else [f"A{n+1}" for n in range(N)])

    b_c1 = cr.net_benefit_per_agent.get("C1", np.zeros(N))
    b_c4 = cr.net_benefit_per_agent.get("C4", np.zeros(N))
    nb_c1 = cr.net_benefit.get("C1", 0.0)
    nb_c4 = cr.net_benefit.get("C4", 0.0)

    # ── Diferencia horaria C1 vs C4 (per-hour, lightweight) ─────────────────
    # C4 hora k: autoconsumo + crédito PDE efectivo + excedente propio
    # C1 hora k: autoconsumo solo (permutación se evalúa mensual/total)
    # Aproximación para la dispersión: C1_k = autoconsumo_k × pi_gs + balance
    # Usamos la diferencia de beneficio total dividida como proxy horario:
    # Delta_total / T como línea de referencia, y spread C4 como variación.
    D_pos = np.maximum(D, 0.0)
    G_pos = np.maximum(G_klim, 0.0)
    auto_k  = np.sum(np.minimum(G_pos, D_pos), axis=0)       # (T,)
    surp_k  = np.sum(np.maximum(G_pos - D_pos, 0.0), axis=0) # (T,)
    def_k   = np.sum(np.maximum(D_pos - G_pos, 0.0), axis=0) # (T,)
    comm_surp_k = np.maximum(np.sum(G_pos, axis=0) - np.sum(D_pos, axis=0), 0.0)
    credits_k   = np.sum(np.minimum(
        pde[:, None] * comm_surp_k[None, :],
        np.maximum(D_pos - G_pos, 0.0)
    ), axis=0)   # (T,) crédito PDE efectivo total

    # B_C4_k (aproximado a nivel comunitario)
    b_c4_k = auto_k * pi_gs + credits_k * pi_gs + surp_k * pi_bolsa

    # B_C1_k: asignamos el delta total mensual/uniforme como proxy per-hora
    # La lógica C1 acumula el mes — per-hora solo tiene el autoconsumo
    b_c1_k_proxy = auto_k * pi_gs + def_k * 0.0 + surp_k * pi_bolsa
    # Ajustamos con el factor de permutación promedio
    perm_total = nb_c1 - (float(np.sum(auto_k)) * pi_gs
                          + float(np.sum(surp_k * pi_bolsa)))
    perm_per_h = perm_total / max(T, 1)
    b_c1_k = b_c1_k_proxy + perm_per_h   # proxy horario corregido

    delta_k = b_c1_k - b_c4_k     # C1 − C4 por hora

    # ── Figura ───────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(15, 5))
    gs  = GridSpec(1, 3, figure=fig, wspace=0.35)

    # ── Panel A: beneficio por agente ────────────────────────────────────────
    ax_a = fig.add_subplot(gs[0])
    x = np.arange(N)
    w = 0.35
    bars_c1 = ax_a.bar(x - w/2, b_c1, w, label="C1 CREG 174/2021",
                       color=COLORS_ESC["C1"], alpha=0.85)
    bars_c4 = ax_a.bar(x + w/2, b_c4, w, label="C4 CREG 101 072/2025",
                       color=COLORS_ESC["C4"], alpha=0.85)
    ax_a.axhline(0, color="black", lw=0.8)
    ax_a.set_xticks(x); ax_a.set_xticklabels(names, rotation=15, ha="right")
    ax_a.set_ylabel(f"{currency}/período")
    ax_a.set_title("A — Beneficio neto por agente:\nC1 (AGPE) vs C4 (AGRC)",
                   fontweight="bold")
    ax_a.legend(fontsize=8)

    # Anotación delta total
    delta_total = nb_c1 - nb_c4
    sign  = "C1 > C4" if delta_total > 0 else "C4 > C1"
    color = COLORS_ESC["C1"] if delta_total > 0 else COLORS_ESC["C4"]
    ax_a.text(0.98, 0.97,
              f"Δ total = {delta_total:+,.0f} {currency}\n({sign})",
              transform=ax_a.transAxes, ha="right", va="top", fontsize=8,
              color=color,
              bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color, alpha=0.85))

    # ── Panel B: diferencia horaria ──────────────────────────────────────────
    ax_b = fig.add_subplot(gs[1])
    hours = np.arange(T)
    ax_b.bar(hours, delta_k, color=np.where(delta_k >= 0,
             COLORS_ESC["C1"], COLORS_ESC["C4"]),
             alpha=0.65, width=1.0)
    ax_b.axhline(0, color="black", lw=0.9, ls="--")
    ax_b.set_xlabel("Hora k")
    ax_b.set_ylabel(f"ΔB = B_C1 − B_C4  ({currency})")
    ax_b.set_title("B — Diferencia horaria C1 − C4\n(positivo = C1 mejor)",
                   fontweight="bold")
    # parches de leyenda
    ax_b.legend(handles=[
        mpatches.Patch(color=COLORS_ESC["C1"], alpha=0.7, label="C1 > C4"),
        mpatches.Patch(color=COLORS_ESC["C4"], alpha=0.7, label="C4 > C1"),
    ], fontsize=8)

    # ── Panel C: dispersión ΔB vs pi_bolsa ───────────────────────────────────
    ax_c = fig.add_subplot(gs[2])
    sc = ax_c.scatter(pi_bolsa, delta_k,
                      c=delta_k, cmap="RdYlGn",
                      vmin=-abs(delta_k).max(), vmax=abs(delta_k).max(),
                      s=20, alpha=0.65, edgecolors="none")
    ax_c.axhline(0, color="black", lw=0.9, ls="--")
    # Tendencia suavizada (ventana móvil sobre datos ordenados)
    sort_idx  = np.argsort(pi_bolsa)
    pb_sorted = pi_bolsa[sort_idx]
    dk_sorted = delta_k[sort_idx]
    win = max(3, len(pb_sorted) // 8)
    if len(pb_sorted) >= win:
        smooth = np.convolve(dk_sorted, np.ones(win)/win, mode="valid")
        x_sm   = pb_sorted[win//2: win//2 + len(smooth)]
        ax_c.plot(x_sm, smooth, color="#222222", lw=1.5, ls="-",
                  label=f"Media móvil (w={win})")
        ax_c.legend(fontsize=8)
    fig.colorbar(sc, ax=ax_c, shrink=0.8, label=f"ΔB ({currency})")
    ax_c.set_xlabel("pi_bolsa (COP/kWh)")
    ax_c.set_ylabel(f"ΔB = B_C1 − B_C4  ({currency})")
    ax_c.set_title("C — ΔB vs precio de bolsa\n(depende de hidrología)",
                   fontweight="bold")

    fig.suptitle(
        "Fig 15 — Comparación directa C1 (CREG 174/2021 AGPE) vs C4 (CREG 101 072/2025 AGRC)\n"
        "Diferencia por agente, por hora y en función del precio de bolsa",
        fontsize=10, fontweight="bold")

    path = os.path.join(out_dir, "fig15_c1_vs_c4.png")
    return _save(fig, path)


def plot_robustness_c4(
    wr_report,          # WithdrawalRiskReport
    agent_names: list,
    out_dir: str,
    currency: str = "COP",
) -> str:
    """
    Fig 17 — Robustez regulatoria C4 (FA-3 + FA-4).

    Panel A: Beneficio COP por escenario de retiro
        - B_C4_remaining (si AGRC se mantiene)
        - B_fallback     (si AGRC se invalida → régimen individual)
        - B_P2P_remaining (P2P sin el agente retirado)
    Panel B: Flexibility premium (B_P2P_remaining - B_fallback)
        Barras negativas → C4 fallback supera a P2P (raro)
        Barras positivas → P2P ofrece más que el fallback de C4

    Referencias: propuesta tesis §VII.C — Robustez ante riesgo regulatorio
    """
    ba = wr_report.by_agent
    if not ba:
        return ""

    names = list(ba.keys())
    B_c4r   = [ba[n]["B_C4_remaining"]      for n in names]
    B_fall  = [ba[n]["B_fallback"]           for n in names]
    B_p2pr  = [ba[n]["B_P2P_remaining"]      for n in names]
    FP      = [ba[n]["flexibility_premium"]  for n in names]
    compliant = [ba[n]["compliant"]          for n in names]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(
        "Fig 17 — Robustez regulatoria C4: impacto del retiro de participante",
        fontsize=11, fontweight="bold",
    )

    x   = np.arange(len(names))
    w   = 0.25
    fmt = lambda v: f"{v/1000:.1f}k" if abs(v) >= 1000 else f"{v:.0f}"

    # ── Panel A: beneficios bajo cada escenario de retiro ─────────────────
    b1 = ax1.bar(x - w, B_c4r,  width=w, label="C4 AGRC (restante)",
                 color="#2196F3", alpha=0.85)
    b2 = ax1.bar(x,     B_fall, width=w, label="C4 fallback (sin AGRC)",
                 color="#F44336", alpha=0.85)
    b3 = ax1.bar(x + w, B_p2pr, width=w, label="P2P (restante)",
                 color="#4CAF50", alpha=0.85)

    # Marcar violaciones
    for i, (ok, name) in enumerate(zip(compliant, names)):
        if not ok:
            ax1.annotate("⚠ AGRC\ninválido",
                         xy=(x[i], max(B_c4r[i], B_fall[i]) * 1.02),
                         ha="center", va="bottom", fontsize=7,
                         color="#F44336", fontweight="bold")

    ax1.set_xticks(x)
    ax1.set_xticklabels([f"Retiro\n{n}" for n in names], fontsize=8)
    ax1.set_ylabel(f"Beneficio comunidad restante ({currency})", fontsize=9)
    ax1.set_title("A — Beneficio por escenario de retiro", fontsize=10)
    ax1.legend(fontsize=8)
    ax1.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"{v/1000:.0f}k" if abs(v) >= 1000 else f"{v:.0f}"))
    ax1.grid(axis="y", alpha=0.3)

    # ── Panel B: flexibility premium ──────────────────────────────────────
    colors = ["#4CAF50" if f >= 0 else "#F44336" for f in FP]
    bars   = ax2.bar(x, FP, color=colors, alpha=0.85, edgecolor="white")

    for bar, val in zip(bars, FP):
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + (max(FP) - min(FP)) * 0.02,
                 f"{val:+,.0f}", ha="center", va="bottom", fontsize=8)

    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"Retiro\n{n}" for n in names], fontsize=8)
    ax2.set_ylabel(f"Prima de flexibilidad ({currency})\nB_P2P_rest − B_fallback",
                   fontsize=9)
    ax2.set_title("B — Prima de flexibilidad P2P vs C4 fallback", fontsize=10)
    ax2.grid(axis="y", alpha=0.3)

    # Anotación de resumen
    if wr_report.community_at_risk:
        ax2.text(0.5, 0.02,
                 f"⚠ {wr_report.n_risky_withdrawals}/{len(names)} retiros invalidan AGRC\n"
                 f"Prima total: {wr_report.flexibility_premium_total:+,.0f} {currency}",
                 transform=ax2.transAxes, ha="center", va="bottom",
                 fontsize=8, color="#F44336",
                 bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#F44336", alpha=0.8))
    else:
        ax2.text(0.5, 0.02,
                 "✓ Ningún retiro invalida el régimen AGRC",
                 transform=ax2.transAxes, ha="center", va="bottom",
                 fontsize=8, color="#4CAF50",
                 bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#4CAF50", alpha=0.8))

    fig.tight_layout()
    return _save(fig, os.path.join(out_dir, "fig17_robustez_c4.png"))


def generate_sensitivity_plots(sa_pgb, sa_pv, findings,
                                agent_names, out_dir, currency="COP",
                                fa_desertion=None, fa_creg=None,
                                p2p_results=None, pi_bolsa=None, D=None,
                                sa_ppa=None, pi_gb=None, pi_gs=None,
                                **kwargs):
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

    # Fig 10: sensibilidad PPA
    if sa_ppa and pi_gb is not None and pi_gs is not None:
        steps.append(("Fig 10 — Sensibilidad PPA",
                      lambda: plot_sensitivity_ppa(
                          sa_ppa, agent_names, pi_gb, pi_gs, out_dir, currency)))

    # Fig 11: sensibilidad π_gs  (SA-3)
    if "sa_pgs" in kwargs and kwargs["sa_pgs"]:
        sa_pgs = kwargs["sa_pgs"]
        steps.append(("Fig 11 — Sensibilidad π_gs (SA-3)",
                      lambda _sa=sa_pgs: plot_sensitivity_pgs(
                          _sa, out_dir, currency)))

    for label, fn in steps:
        try:
            p = fn()
            if p:
                paths.append(p)
                print(f"    ✓ {label}")
        except Exception as e:
            print(f"    ✗ {label}: {e}")

    return paths
