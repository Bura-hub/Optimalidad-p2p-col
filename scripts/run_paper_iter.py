"""
scripts/run_paper_iter.py — Orquestador del paper IEEE WEEF 2026 (CAL-25)
==========================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 4.1 + 4.2

Modo paper: aplica los ajustes acordados en la reunion del 2026-05-01
para generar los resultados que sustentan el paper IEEE WEEF 2026,
sin afectar el flujo de la tesis (`main_simulation.py`).

Ajustes aplicados (decisiones plan radiant-sleeping-eagle Sprint 6):

  A1: Homogeneizar todas las instituciones a perfil 'comercial'
      (en memoria, no toca `data/cedenar_tariff.py`).
  B : Solo simula C1, C4 y P2P. Renombra C4 -> "C2 (CREG 101 072)".
  G : Limita el horizonte a un mes especifico (default 2025-08).

Uso:
  python scripts/run_paper_iter.py
  python scripts/run_paper_iter.py --month 2025-08
  python scripts/run_paper_iter.py --month 2025-08 --pde excedentes
  python scripts/run_paper_iter.py --tag "submit"

Output:
  outputs/paper/resultados_paper_<tag>.xlsx
  outputs/paper/perfiles_<month>.png

Referencia: docs/adr/0025-cal25-modo-paper.md
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _wrap_stdout_utf8():
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                       encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer,
                                       encoding="utf-8", errors="replace")


# ─── A1 — Homogeneización en memoria ───────────────────────────────────────


def homogeneizar_a_comercial() -> dict:
    """
    Modifica `INSTITUTION_PROFILE` en memoria a perfil comercial uniforme.
    Devuelve el dict original para auditoria.

    CAL-25: aplica solo en el proceso del script paper. La tesis y otros
    procesos siguen viendo el dict pre-CAL-25 (oficial+comercial mix).
    """
    from data import cedenar_tariff
    from data.cedenar_tariff import TariffProfile

    original = dict(cedenar_tariff.INSTITUTION_PROFILE)
    profile_comercial = TariffProfile(
        categoria="comercial", nivel_tension=2, propiedad="cedenar",
    )
    cedenar_tariff.INSTITUTION_PROFILE = {
        name: profile_comercial for name in original
    }
    print(f"  [CAL-25/A1] INSTITUTION_PROFILE homogeneizado a 'comercial'")
    print(f"             ({len(original)} agentes; original conservado en RAM)")
    return original


# ─── G — Horizonte mensual ─────────────────────────────────────────────────


def horizonte_mensual(month: str) -> tuple[str, str]:
    """
    Convierte 'YYYY-MM' en (t_start, t_end) inclusive del mes especificado.
    El t_end es el primer dia del mes siguiente (exclusive).
    """
    ts = pd.Timestamp(f"{month}-01")
    te = (ts + pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d")
    return ts.strftime("%Y-%m-%d"), te


def cargar_mte_subset(t_start: str, t_end: str):
    """Carga MTE completo (M1 totalizador) y devuelve subset alineado al mes.

    Este es el flujo legacy (status quo de la tesis). Ver
    ``cargar_mte_paper`` para CAL-28.
    """
    from data.xm_data_loader import MTEDataLoader, slice_horizon, AGENTS

    mte_root = os.environ.get("MTE_ROOT", str(ROOT / "MedicionesMTE_v3"))
    loader = MTEDataLoader(root_path=mte_root)
    D_full, G_full, idx_full = loader.load(verbose=False)
    D, G, idx = slice_horizon(D_full, G_full, idx_full, t_start, t_end)
    return D, G, idx, list(AGENTS)


# ─── CAL-28 — Selección de medidor puntual ────────────────────────────────


def _read_meter_csvs(meter_dir: Path,
                      col_demand: str = "totalActivePower",
                      tz: str = "America/Bogota") -> pd.Series:
    """Lee todos los CSVs de un medidor y devuelve serie horaria (kW)
    localizada en la zona horaria del proyecto."""
    csvs = sorted(meter_dir.glob("*.csv"))
    if not csvs:
        raise FileNotFoundError(f"Sin CSVs en {meter_dir}")
    parts = []
    for csv in csvs:
        try:
            df = pd.read_csv(csv, low_memory=False)
        except Exception:
            continue
        if "date" not in df.columns or col_demand not in df.columns:
            continue
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df[col_demand] = pd.to_numeric(df[col_demand], errors="coerce")
        df = df.dropna(subset=["date", col_demand])
        parts.append(df.set_index("date")[col_demand])
    if not parts:
        raise ValueError(f"Sin datos válidos en {meter_dir}")
    s = pd.concat(parts).sort_index()
    # Localizar a tz del proyecto (las series CSV son tz-naive). Se asume
    # que las marcas de tiempo del datalogger son hora local Colombia.
    s.index = s.index.tz_localize(tz, ambiguous="NaT", nonexistent="NaT")
    s = s[s.index.notna()]
    # Resample 1h con media (kW promedio por hora)
    s_hourly = s.resample("1h").mean()
    return s_hourly


def cargar_mte_paper(t_start: str, t_end: str,
                      config_csv: Optional[Path] = None
                      ) -> tuple[np.ndarray, np.ndarray,
                                  pd.DatetimeIndex, list[str]]:
    """
    Carga MTE para el paper IEEE WEEF (CAL-28).

    Para cada institución, lee el medidor configurado en
    ``data/paper_meter_config.csv`` (default M3 sub-medidor o
    M1 escalado para Mariana).

    La generación G se carga via MTEDataLoader normal (los inversores
    son comunes; no se reemplazan).

    Devuelve (D, G, idx, agents) con la misma firma que ``cargar_mte_subset``.
    """
    from data.xm_data_loader import MTEDataLoader, slice_horizon, AGENTS

    if config_csv is None:
        config_csv = ROOT / "data" / "paper_meter_config.csv"
    if not config_csv.exists():
        raise FileNotFoundError(
            f"Falta {config_csv}. Necesario para CAL-28."
        )
    cfg = pd.read_csv(config_csv)
    if not {"institucion", "carpeta", "medidor_nombre",
            "factor_escala"} <= set(cfg.columns):
        raise ValueError(f"CSV inválido: {config_csv}")

    mte_root = Path(os.environ.get("MTE_ROOT",
                                     str(ROOT / "MedicionesMTE_v3")))

    # 1. Generación: viene de MTEDataLoader normal (inversores).
    loader = MTEDataLoader(root_path=str(mte_root))
    D_full, G_full, idx_full = loader.load(verbose=False)
    agents = list(AGENTS)

    # 2. Demanda: reemplazar por medidor configurado por institución.
    D_paper_full = np.zeros_like(D_full)
    cfg_by_inst = cfg.set_index("institucion").to_dict("index")

    print(f"  [CAL-28] Cargando medidores puntuales ({len(agents)} inst)...")
    for n, inst in enumerate(agents):
        if inst not in cfg_by_inst:
            print(f"    {inst}: sin config → usando M1 totalizador")
            D_paper_full[n, :] = D_full[n, :]
            continue
        cfg_inst = cfg_by_inst[inst]
        meter_dir = (mte_root / inst / cfg_inst["carpeta"]
                      / f"{cfg_inst['medidor_nombre']} - electricMeter")
        try:
            s = _read_meter_csvs(meter_dir)
            s = s.reindex(idx_full).interpolate(method="time", limit=6)
            s = s.fillna(0.0) * float(cfg_inst["factor_escala"])
            # Clip a no-negativo (evita ruido negativo)
            D_paper_full[n, :] = np.maximum(s.to_numpy(), 0.0)
            mean_kw = float(D_paper_full[n].mean())
            print(f"    {inst}: {cfg_inst['medidor_nombre']} "
                  f"× {cfg_inst['factor_escala']} → D̄={mean_kw:.2f} kW")
        except Exception as e:
            print(f"    {inst}: ERROR ({e}); fallback a M1 totalizador")
            D_paper_full[n, :] = D_full[n, :]

    # 3. Slice al horizonte solicitado (mes específico).
    D, G, idx = slice_horizon(D_paper_full, G_full, idx_full, t_start, t_end)
    return D, G, idx, agents


# ─── Setup parametros y series ─────────────────────────────────────────────


def setup_parametros(D, G, idx, agents):
    """Construye pi_gs, pi_bolsa, componentes G/Cvm/COT, mem y b_calibrado."""
    from data.xm_prices import get_pi_bolsa, get_b_for_real_data
    from data.cedenar_tariff import (
        pi_gs_per_agent_hourly,
        cu_components_per_agent_hourly,
        mem_costs_per_agent_hourly,
    )

    N, T = D.shape
    t_start = idx[0].strftime("%Y-%m-%d")
    t_end = (idx[-1] + pd.Timedelta(hours=1)).strftime("%Y-%m-%d")

    # Tarifas y componentes (post-A1: todas instituciones perfil comercial)
    pi_gs = pi_gs_per_agent_hourly(agents, idx)
    components = cu_components_per_agent_hourly(agents, idx)
    g_comp = components["G"]
    cvm = components["Cvm"]
    cot = components["COT"]
    mem = mem_costs_per_agent_hourly(agents, idx)

    # Precio bolsa con techo PES (CAL-14 default).
    pi_bolsa = get_pi_bolsa(T=T, t_start=t_start, t_end=t_end,
                              use_api=True, apply_ceiling=True)

    # b calibrado por institucion
    b_cal = get_b_for_real_data(N, agents)

    return {
        "pi_gs": pi_gs, "pi_bolsa": pi_bolsa,
        "g_comp": g_comp, "cvm": cvm, "cot": cot, "mem": mem,
        "b_cal": b_cal,
    }


# ─── Simulación P2P ─────────────────────────────────────────────────────────


def correr_p2p(D, G, agents, b_cal, pi_gs_eff: float, pi_gb: float):
    """Corre el EMS P2P con los parametros del paper."""
    from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams

    N = D.shape[0]
    agent_params = AgentParams(
        N=N,
        a=np.zeros(N), b=b_cal, c=np.full(N, 1.2),
        lam=np.full(N, 100.0),
        theta=np.full(N, 0.5),
        etha=np.full(N, 0.1),
        alpha=np.zeros(N),  # sin DR
    )
    grid = GridParams(pi_gs=pi_gs_eff, pi_gb=pi_gb)
    solver = SolverParams(
        tau=0.001, t_span=(0.0, 0.005), n_points=150,
        stackelberg_iters=2, stackelberg_tol=1e-3, stackelberg_max=10,
        parallel=True,
    )
    ems = EMSP2P(agent_params, grid, solver)
    p2p_results, G_klim, _ = ems.run(D, G)
    return p2p_results, G_klim


# ─── Simulación regulatorios ───────────────────────────────────────────────


def correr_c1(D, G_klim, pi_gs, pi_bolsa, prosumer_ids, idx):
    """C1 = CREG 174/2021. Mensual con Hx (CAL-10b)."""
    from scenarios.scenario_c1_creg174 import run_c1_creg174

    month_labels = np.array(
        [ts.year * 100 + ts.month for ts in idx], dtype=int,
    )
    return run_c1_creg174(
        D, G_klim, pi_gs, pi_bolsa, prosumer_ids,
        month_labels=month_labels,
        component_c="auto",
    )


def correr_c4(D, G_klim, pi_gs, pi_bolsa, pde, capacity, component_c="auto"):
    """C4 = CREG 101 072/2025. Heredando CREG 174 (CAL-15)."""
    from scenarios.scenario_c4_creg101072 import run_c4_creg101072

    return run_c4_creg101072(
        D=D, G=G_klim, pi_gs=pi_gs, pi_bolsa=pi_bolsa,
        pde=pde, capacity=capacity,
        component_c=component_c,
        mode="creg174_inheritance",
    )


# ─── Renaming + reporte ─────────────────────────────────────────────────────


# Nomenclatura del paper IEEE WEEF (alineada con abstract).
PAPER_RENAMING = {
    "C1": "C1 (CREG 174)",
    "C4": "C2 (CREG 101 072)",
    "P2P": "P2P (Stackelberg + RD)",
}


def _p2p_decomposed(p2p_results, D, G_klim, pi_gs, pi_gb, prosumer_ids):
    """
    Decompone net_benefit P2P en (autoconsumo, mercado) por agente.

    Replica la lógica de scenarios.comparison_engine._p2p_monetary_benefit
    pero retorna las dos componentes separadas (CAL-Sprint 6.4).

    autoconsumo[n]   = sum_t min(G_klim[n,t], D[n,t]) * pi_gs[n,t]
    mercado[n]       = vendedor_premium[n] + comprador_savings[n]
                       (todo lo que no es autoconsumo)
    """
    from scenarios._pi_gs import as_pi_gs_array

    N, T = D.shape
    pi_gs_v = as_pi_gs_array(pi_gs, N, T)

    autoconsumo_per_agent = np.zeros(N)
    mercado_per_agent = np.zeros(N)

    for k_local, r in enumerate(p2p_results):
        if r.P_star is None:
            continue
        # Autoconsumo: ocurre antes del juego, igual en todos los escenarios.
        for n in prosumer_ids:
            auto_kn = float(min(G_klim[n, k_local], D[n, k_local]))
            autoconsumo_per_agent[n] += auto_kn * float(pi_gs_v[n, k_local])

        # Mercado P2P: prima del vendedor + ahorro del comprador
        if r.pi_star is None:
            continue
        sids = r.seller_ids or []
        bids = r.buyer_ids or []
        if not sids or not bids:
            continue
        try:
            pi_st = np.asarray(r.pi_star, dtype=float)
            P = np.asarray(r.P_star, dtype=float)
        except Exception:
            continue
        if np.any(~np.isfinite(pi_st)) or np.any(~np.isfinite(P)):
            continue
        # Vendedor j ofrece sum_i P[j,i] al precio promedio de pi_star.
        for j_idx, j in enumerate(sids):
            sold = float(P[j_idx].sum())
            if sold > 1e-9:
                price_avg = float((pi_st * P[j_idx]).sum()) / sold
                premium = (price_avg - pi_gb) * sold
                mercado_per_agent[j] += premium
        # Comprador i recibe sum_j P[j,i] al precio P2P.
        for i_idx, i in enumerate(bids):
            bought = float(P[:, i_idx].sum())
            if bought > 1e-9:
                pi_buy = float(pi_st[i_idx])
                pi_gs_ki = float(pi_gs_v[i, k_local])
                savings = (pi_gs_ki - pi_buy) * bought
                mercado_per_agent[i] += savings

    return autoconsumo_per_agent, mercado_per_agent


def construir_resumen(p2p_results, c1_per_agent, c4_result,
                       agents: list[str], D, G_klim, pi_gs, pi_gb,
                       prosumer_ids) -> pd.DataFrame:
    """Construye DataFrame Resumen con renaming del paper.

    Sprint 6.4: separa Ahorro_autoconsumo (offset común) vs
    Venta_excedentes (diferenciador) por escenario, además del Total.

    P2P net_benefit usa la misma fórmula que C1/C4 vía decomposición
    explícita autoconsumo + mercado P2P.
    """
    N = len(agents)

    # P2P decompuesto
    p2p_auto, p2p_mercado = _p2p_decomposed(
        p2p_results, D, G_klim, pi_gs, pi_gb, prosumer_ids,
    )
    p2p_net_per_agent = p2p_auto + p2p_mercado
    p2p_net = float(np.sum(p2p_net_per_agent))
    p2p_auto_total = float(p2p_auto.sum())
    p2p_mercado_total = float(p2p_mercado.sum())
    active = [r for r in p2p_results
              if r.P_star is not None and np.sum(r.P_star) > 1e-4]
    p2p_kwh = sum(float(np.sum(r.P_star)) for r in active)

    # C1 decompuesto (savings = autoconsumo + Tipo 1; surplus_revenue = Tipo 2 bolsa)
    c1_auto = np.zeros(N); c1_mercado = np.zeros(N)
    for n in range(N):
        if n in c1_per_agent:
            d = c1_per_agent[n]
            # En C1, "savings" = E_auto*pi_gs + E_t1*(pi_gs-Cvm). El offset
            # "Ahorro autoconsumo" comparable es E_auto*pi_gs; el resto
            # (Tipo 1 + Tipo 2) es "Venta excedentes".
            E_auto = d.get("E_auto", 0.0)
            # Aproximamos el ahorro de autoconsumo como pi_gs * E_auto
            # usando el promedio comunitario del periodo. Más preciso seria
            # leer pi_gs[n] del periodo, pero al estar homogeneizado (CAL-25)
            # el promedio = el escalar comercial.
            pi_gs_avg = float(np.nanmean(pi_gs))
            ahorro_n = E_auto * pi_gs_avg
            c1_auto[n] = ahorro_n
            c1_mercado[n] = d["net_benefit"] - ahorro_n
    c1_net_per_agent = c1_auto + c1_mercado
    c1_total = float(c1_net_per_agent.sum())

    # C4 decompuesto: savings = autoconsumo; pde_credits = Tipo 1; surplus_revenue = Tipo 2
    c4_per_agent = c4_result["per_agent"]
    c4_auto = np.zeros(N); c4_mercado = np.zeros(N)
    for n in range(N):
        if n in c4_per_agent:
            d = c4_per_agent[n]
            # En C4 "savings" = autoconsumo*pi_gs (sin permuta), separado.
            c4_auto[n] = float(d.get("savings", 0.0))
            c4_mercado[n] = (float(d.get("pde_credits", 0.0))
                              + float(d.get("surplus_revenue", 0.0)))
    c4_net_per_agent = c4_auto + c4_mercado
    c4_total = float(c4_net_per_agent.sum())

    rows = [
        {
            "Escenario": PAPER_RENAMING["P2P"],
            "Ahorro_autoconsumo_COP": round(p2p_auto_total, 1),
            "Venta_excedentes_COP":   round(p2p_mercado_total, 1),
            "Total_COP":              round(p2p_net, 1),
            "kWh_P2P_total":          round(p2p_kwh, 3),
            "horas_activas":          len(active),
            "Mecanismo":              "Stackelberg leader-follower + Replicator Dynamics",
            "Fuente legal":           "—",
        },
        {
            "Escenario": PAPER_RENAMING["C1"],
            "Ahorro_autoconsumo_COP": round(float(c1_auto.sum()), 1),
            "Venta_excedentes_COP":   round(float(c1_mercado.sum()), 1),
            "Total_COP":              round(c1_total, 1),
            "kWh_P2P_total":          0.0,
            "horas_activas":          0,
            "Mecanismo":              "AGPE Tipo 1 / Tipo 2 + componente Cvm",
            "Fuente legal":           "CREG 174/2021 art. 22-25",
        },
        {
            "Escenario": PAPER_RENAMING["C4"],
            "Ahorro_autoconsumo_COP": round(float(c4_auto.sum()), 1),
            "Venta_excedentes_COP":   round(float(c4_mercado.sum()), 1),
            "Total_COP":              round(c4_total, 1),
            "kWh_P2P_total":          0.0,
            "horas_activas":          0,
            "Mecanismo":              "PDE comunitario + herencia CREG 174",
            "Fuente legal":           "Decreto 2236/2023 + CREG 101 072/2025",
        },
    ]
    # mantener compatibilidad: por_agente recibe scenarios_data como antes.
    return pd.DataFrame(rows), {
        PAPER_RENAMING["P2P"]: (p2p_net, p2p_net_per_agent),
        PAPER_RENAMING["C1"]:  (c1_total, c1_net_per_agent),
        PAPER_RENAMING["C4"]:  (c4_total, c4_net_per_agent),
    }, {
        # Decomposición separada para la figura barras apiladas
        PAPER_RENAMING["P2P"]: (p2p_auto_total, p2p_mercado_total),
        PAPER_RENAMING["C1"]:  (float(c1_auto.sum()), float(c1_mercado.sum())),
        PAPER_RENAMING["C4"]:  (float(c4_auto.sum()), float(c4_mercado.sum())),
    }


def construir_por_agente(agents, scenarios_data: dict) -> pd.DataFrame:
    """DataFrame con net_benefit per agente por escenario."""
    rows = []
    for n, name in enumerate(agents):
        row = {"Agente": name}
        for esc, (_total, per_agent) in scenarios_data.items():
            row[esc] = round(float(per_agent[n]), 1) if len(per_agent) > n else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


# ─── Export ─────────────────────────────────────────────────────────────────


def exportar(resumen: pd.DataFrame, por_agente: pd.DataFrame,
              D, G, idx, agents: list[str], out_dir: Path,
              tag: str, month: str,
              decomposition: dict | None = None) -> dict:
    """Genera xlsx + png de perfiles + figura barras apiladas (Sprint 6.4)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    xlsx_path = out_dir / f"resultados_paper_{tag}.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
        resumen.to_excel(w, sheet_name="Resumen", index=False)
        por_agente.to_excel(w, sheet_name="Por_agente", index=False)
    try:
        rel_xlsx = xlsx_path.relative_to(ROOT)
    except ValueError:
        rel_xlsx = xlsx_path
    print(f"  [paper] Excel  -> {rel_xlsx}")

    # Figura de perfiles del mes
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
        N, T = D.shape
        hours = np.arange(T)
        agg_D = D.sum(axis=0)
        agg_G = G.sum(axis=0)
        axes[0].plot(hours, agg_D, label="Demand (community)",
                      color="tab:red", lw=1)
        axes[0].plot(hours, agg_G, label="Generation (community)",
                      color="tab:green", lw=1)
        axes[0].set_ylabel("kW")
        axes[0].set_title(f"Community profiles ({month}, "
                           f"5 institutions homogenized to commercial)")
        axes[0].legend(loc="upper right", fontsize=9)
        axes[0].grid(alpha=0.3)

        for n, name in enumerate(agents):
            axes[1].plot(hours, G[n], label=name, lw=0.8)
        axes[1].set_xlabel("Hour")
        axes[1].set_ylabel("Generation per institution [kW]")
        axes[1].legend(loc="upper right", fontsize=8, ncol=5)
        axes[1].grid(alpha=0.3)

        fig.tight_layout()
        png_path = out_dir / f"perfiles_{month}.png"
        fig.savefig(png_path, dpi=130, bbox_inches="tight")
        plt.close(fig)
        try:
            rel_png = png_path.relative_to(ROOT)
        except ValueError:
            rel_png = png_path
        print(f"  [paper] Figura -> {rel_png}")
    except Exception as e:
        print(f"  [paper] Figura skipped ({e})")

    # Sprint 6.4: figura barras apiladas (offset común vs diferencial)
    if decomposition:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            scenarios = list(decomposition.keys())
            ahorro_vals  = [decomposition[s][0] / 1e6 for s in scenarios]
            venta_vals   = [decomposition[s][1] / 1e6 for s in scenarios]

            fig, ax = plt.subplots(figsize=(8, 5))
            x = np.arange(len(scenarios))
            width = 0.6
            b1 = ax.bar(x, ahorro_vals, width, label="Self-consumption savings (offset)",
                         color="tab:gray", alpha=0.85)
            b2 = ax.bar(x, venta_vals, width, bottom=ahorro_vals,
                         label="Surplus revenue (differentiator)",
                         color="tab:blue", alpha=0.85)
            for i, (a, v) in enumerate(zip(ahorro_vals, venta_vals)):
                ax.text(i, a / 2, f"{a:.2f}", ha="center", va="center",
                        fontsize=8, color="white")
                ax.text(i, a + v / 2, f"{v:.2f}", ha="center", va="center",
                        fontsize=8, color="white")
                ax.text(i, a + v + 0.05 * max(ahorro_vals + venta_vals),
                        f"Total {a+v:.2f}", ha="center", fontsize=9,
                        fontweight="bold")
            ax.set_xticks(x)
            ax.set_xticklabels([s.replace(" (", "\n(") for s in scenarios],
                                fontsize=9)
            ax.set_ylabel("Net benefit [million COP]")
            ax.set_title(f"Self-consumption (common offset) vs. surplus revenue\n"
                          f"({month}, IEEE WEEF paper)")
            ax.legend(loc="upper right", fontsize=9)
            ax.grid(axis="y", alpha=0.3)
            fig.tight_layout()
            stack_path = out_dir / f"fig_offset_vs_diferencial_{tag}.png"
            fig.savefig(stack_path, dpi=130, bbox_inches="tight")
            plt.close(fig)
            try:
                rel_stack = stack_path.relative_to(ROOT)
            except ValueError:
                rel_stack = stack_path
            print(f"  [paper] Figura barras apiladas -> {rel_stack}")
        except Exception as e:
            print(f"  [paper] Figura barras apiladas skipped ({e})")

    return {"xlsx": str(xlsx_path), "month": month, "tag": tag}


# ─── Sprint 6.5 — Barrido PV con detector de cruces de ranking ──────────────


def barrido_pv_paper(D, G, idx, agents, params, prosumer_ids, pi_gs_eff,
                      pi_gb, pde_method: str = "capacity",
                      factors: tuple = (1.0, 1.5, 2.0, 2.5, 3.0)) -> list:
    """Re-ejecuta P2P + C1 + C4 escalando la generación por cada factor.

    Devuelve lista de dicts compatible con
    :func:`analysis.sensitivity.ranking_table_pv`.
    """
    from scenarios.scenario_c4_creg101072 import (
        compute_pde_weights, compute_excedentes_acumulados,
    )

    sweep = []
    print(f"\n  [Sprint 6.5] Barrido PV factors={list(factors)} "
          f"({pde_method})")
    print(f"  {'factor':>7}  {'cob%':>5}  {'P2P [M]':>9}  {'C1 [M]':>9}  "
          f"{'C2 [M]':>9}  {'horas':>5}")
    print("  " + "─" * 60)

    for f in factors:
        G_scaled = G * float(f)
        cap_scaled = np.maximum(G_scaled.mean(axis=1), 0)
        if pde_method == "capacity":
            pde = compute_pde_weights(cap_scaled,
                                       method="capacity_proportional")
        else:
            ex = compute_excedentes_acumulados(G_scaled, D)
            pde = compute_pde_weights(ex, method="excedentes_proportional")

        p2p_res, G_klim = correr_p2p(D, G_scaled, agents, params["b_cal"],
                                       pi_gs_eff, pi_gb)
        c1_per_agent = correr_c1(D, G_klim, params["pi_gs"], params["pi_bolsa"],
                                  prosumer_ids, idx)
        c4_res = correr_c4(D, G_klim, params["pi_gs"], params["pi_bolsa"],
                            pde, cap_scaled, component_c="auto")

        _resumen, scenarios_data, _decomp = construir_resumen(
            p2p_res, c1_per_agent, c4_res, agents,
            D, G_klim, params["pi_gs"], pi_gb, prosumer_ids,
        )
        nb_dict = {esc: float(total) for esc, (total, _) in scenarios_data.items()}
        active = [r for r in p2p_res
                  if r.P_star is not None and np.sum(r.P_star) > 1e-4]
        kwh = sum(float(np.sum(r.P_star)) for r in active)
        cov = float(G_scaled.sum()) / max(float(D.sum()), 1e-9)

        sweep.append({
            "param_value": float(f),
            "coverage": cov,
            "net_benefit": nb_dict,
            "kwh_p2p": kwh,
            "horas_activas": len(active),
        })
        print(f"  {f:>7.2f}  {cov*100:>4.0f}%  "
              f"{nb_dict.get(PAPER_RENAMING['P2P'], 0)/1e6:>9.2f}  "
              f"{nb_dict.get(PAPER_RENAMING['C1'], 0)/1e6:>9.2f}  "
              f"{nb_dict.get(PAPER_RENAMING['C4'], 0)/1e6:>9.2f}  "
              f"{len(active):>5}")
    return sweep


def exportar_ranking_pv(sweep: list, scenarios: list, out_dir: Path,
                          tag: str, graficas_dir: Optional[Path] = None) -> dict:
    """Genera tabla de ranking PV + figura + siblings .csv/.mat (Sprint 6.5)."""
    from analysis.sensitivity import ranking_table_pv, plot_pv_ranking

    rank_df = ranking_table_pv(sweep, scenarios=scenarios, baseline_factor=1.0)

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"fig_pv_ranking_{tag}.csv"
    rank_df.to_csv(csv_path, index=False)
    png_path = out_dir / f"fig_pv_ranking_{tag}.png"
    plot_pv_ranking(rank_df, scenarios, png_path,
                     title="PV factor sweep — paper IEEE WEEF 2026")

    print(f"  [Sprint 6.5] CSV ranking -> {csv_path.relative_to(ROOT) if csv_path.is_relative_to(ROOT) else csv_path}")
    print(f"  [Sprint 6.5] Fig ranking -> {png_path.relative_to(ROOT) if png_path.is_relative_to(ROOT) else png_path}")

    info = {"csv": str(csv_path), "png": str(png_path)}

    if graficas_dir is not None:
        graficas_dir.mkdir(parents=True, exist_ok=True)
        rank_df.to_csv(graficas_dir / "fig_pv_ranking.csv", index=False)
        plot_pv_ranking(rank_df, scenarios, graficas_dir / "fig_pv_ranking.png",
                         title="PV factor sweep — paper IEEE WEEF 2026")
        try:
            from scipy.io import savemat
            mat_data = {
                "factor": rank_df["factor"].to_numpy(dtype=float),
            }
            for s in scenarios:
                # MATLAB no acepta espacios/paréntesis en nombres de campos.
                key = (s.replace(" ", "_").replace("(", "").replace(")", "")
                          .replace("+", "").replace("-", "_"))
                mat_data[f"NB_{key}"] = rank_df[f"NB_{s}"].to_numpy(dtype=float)
                mat_data[f"rank_{key}"] = rank_df[f"rank_{s}"].to_numpy(dtype=int)
            savemat(graficas_dir / "fig_pv_ranking.mat", mat_data)
        except Exception as e:
            print(f"  [Sprint 6.5] .mat skipped ({e})")
        info["graficas_csv"] = str(graficas_dir / "fig_pv_ranking.csv")
        info["graficas_png"] = str(graficas_dir / "fig_pv_ranking.png")

    return info


# ─── Main orquestador ──────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--month", default="2025-08",
                    help="Mes a simular (YYYY-MM, default 2025-08).")
    ap.add_argument("--tag", default="default",
                    help="Tag para nombrar outputs (default 'default').")
    ap.add_argument("--out-dir", default=str(ROOT / "outputs" / "paper"))
    ap.add_argument("--pde", choices=("capacity", "excedentes"),
                    default="capacity",
                    help="Metodo PDE para C4 (default capacity_proportional).")
    ap.add_argument("--keep-profile", action="store_true",
                    help="NO homogeneizar (debug). Por defecto se aplica A1.")
    ap.add_argument("--no-paper-meters", action="store_true",
                    help="NO usar selección CAL-28 (usar M1 totalizador). "
                         "Solo para comparación con baseline tesis.")
    ap.add_argument("--ranking-pv", action="store_true",
                    help="Sprint 6.5: barrido de factor PV {1,1.5,2,2.5,3} "
                         "con detector de cruces de ranking + figura.")
    ap.add_argument("--pv-factors", default="1.0,1.5,2.0,2.5,3.0",
                    help="Factores PV (CSV). Default '1.0,1.5,2.0,2.5,3.0'.")
    args = ap.parse_args()

    print()
    print("=" * 78)
    print(f" CAL-25 — Modo paper IEEE WEEF (mes={args.month}, "
          f"pde={args.pde}, tag={args.tag})")
    print("=" * 78)

    # A1 homogeneizacion
    if not args.keep_profile:
        homogeneizar_a_comercial()
    else:
        print("  [CAL-25/A1] homogeneizacion DESACTIVADA (--keep-profile)")

    # G horizonte mensual
    t_start, t_end = horizonte_mensual(args.month)
    print(f"  [CAL-25/G ] Horizonte: [{t_start} .. {t_end})")

    t0 = time.time()
    if args.no_paper_meters:
        print(f"  [CAL-28]  DESACTIVADO (--no-paper-meters): usando M1 totalizador")
        D, G, idx, agents = cargar_mte_subset(t_start, t_end)
    else:
        # CAL-28 por defecto: medidores puntuales para el paper
        D, G, idx, agents = cargar_mte_paper(t_start, t_end)
    print(f"  [paper] D={D.shape}, G={G.shape}, agentes={agents}")
    cobertura = G.sum() / max(D.sum(), 1e-9)
    print(f"  [paper] Cobertura PV agregada G/D = {cobertura*100:.1f} %")
    if D.shape[1] < 24:
        print(f"  [paper] ERROR: subset demasiado corto ({D.shape[1]}h)")
        return 1

    # Setup parametros (post-A1, todas comerciales)
    p = setup_parametros(D, G, idx, agents)
    pi_gs_eff = float(np.nanmean(p["pi_gs"]))
    pi_gb = float(np.nanmean(p["pi_bolsa"]))
    print(f"  [paper] pi_gs efectivo: {pi_gs_eff:.1f} COP/kWh "
          f"(homogeneo comercial)")
    print(f"  [paper] pi_bolsa medio: {pi_gb:.1f} COP/kWh")

    # B - solo C1, C4, P2P
    print(f"\n  [paper 1/3] EMS P2P...")
    p2p_results, G_klim = correr_p2p(D, G, agents, p["b_cal"],
                                       pi_gs_eff, pi_gb)
    print(f"             {time.time() - t0:.1f}s acumulado")

    print(f"\n  [paper 2/3] C1 (CREG 174)...")
    prosumer_ids = list(range(D.shape[0]))
    c1_per_agent = correr_c1(D, G_klim, p["pi_gs"], p["pi_bolsa"],
                              prosumer_ids, idx)

    print(f"\n  [paper 3/3] C2 = C4 (CREG 101 072)...")
    capacity = np.maximum(G.mean(axis=1), 0)
    from scenarios.scenario_c4_creg101072 import (
        compute_pde_weights, compute_excedentes_acumulados,
    )
    if args.pde == "capacity":
        pde = compute_pde_weights(capacity, method="capacity_proportional")
        print(f"  [paper] PDE: capacity_proportional (CREG 101 072 art. 5)")
    else:
        # CAL-26: excedentes_proportional (opt-in)
        excedentes = compute_excedentes_acumulados(G, D)
        pde = compute_pde_weights(excedentes,
                                    method="excedentes_proportional")
        print(f"  [paper] PDE: excedentes_proportional (CAL-26 opt-in)")
    print(f"          PDE = {[round(float(p), 4) for p in pde]}")
    c4_result = correr_c4(D, G_klim, p["pi_gs"], p["pi_bolsa"],
                            pde, capacity, component_c="auto")

    elapsed = time.time() - t0
    print(f"\n  [paper] Simulacion completada en {elapsed:.1f}s")

    # Resumen + por_agente + decomposición ahorro/venta
    resumen, scenarios_data, decomposition = construir_resumen(
        p2p_results, c1_per_agent, c4_result, agents,
        D, G_klim, p["pi_gs"], pi_gb, prosumer_ids,
    )
    por_agente = construir_por_agente(agents, scenarios_data)

    print()
    print("  Resumen del paper:")
    print(resumen.to_string(index=False))
    print()
    print("  Net benefit por agente:")
    print(por_agente.to_string(index=False))

    # Export
    out_dir = Path(args.out_dir)
    info = exportar(resumen, por_agente, D, G, idx, agents,
                     out_dir, args.tag, args.month,
                     decomposition=decomposition)

    # Sprint 6.5 — barrido de factor PV opcional
    if args.ranking_pv:
        try:
            factors = tuple(float(x) for x in args.pv_factors.split(",")
                            if x.strip())
        except Exception:
            print(f"  [Sprint 6.5] --pv-factors inválido: {args.pv_factors}")
            return 1
        sweep = barrido_pv_paper(
            D, G, idx, agents, p, prosumer_ids, pi_gs_eff, pi_gb,
            pde_method=args.pde, factors=factors,
        )
        graficas_dir = ROOT / "graficas"
        scenarios_paper = [PAPER_RENAMING["P2P"],
                            PAPER_RENAMING["C1"],
                            PAPER_RENAMING["C4"]]
        exportar_ranking_pv(sweep, scenarios_paper, out_dir, args.tag,
                              graficas_dir=graficas_dir)

    print(f"\n  [paper] Hecho. tag={info['tag']}")
    return 0


if __name__ == "__main__":
    _wrap_stdout_utf8()
    sys.exit(main())
