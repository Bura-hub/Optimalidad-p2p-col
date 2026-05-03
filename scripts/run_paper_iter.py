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


def construir_resumen(p2p_results, c1_per_agent, c4_result,
                       agents: list[str], D, G_klim, pi_gs, pi_gb,
                       prosumer_ids) -> pd.DataFrame:
    """Construye DataFrame Resumen con renaming del paper.

    P2P net_benefit usa la misma fórmula que C1/C4
    (autoconsumo + welfare del juego) vía
    `_p2p_monetary_benefit` para que las cifras sean comparables.
    """
    from scenarios.comparison_engine import _p2p_monetary_benefit

    N = len(agents)

    # P2P agregado: autoconsumo + welfare del juego, comparable con C1/C4
    p2p_net_per_agent = _p2p_monetary_benefit(
        p2p_results, D, G_klim, pi_gs, pi_gb, prosumer_ids,
    )
    p2p_net = float(np.sum(p2p_net_per_agent))
    active = [r for r in p2p_results
              if r.P_star is not None and np.sum(r.P_star) > 1e-4]
    p2p_kwh = sum(float(np.sum(r.P_star)) for r in active)

    # C1 agregado
    c1_net_per_agent = np.array([
        c1_per_agent[n]["net_benefit"] if n in c1_per_agent else 0.0
        for n in range(N)
    ])
    c1_total = float(np.sum(c1_net_per_agent))

    # C4 agregado (renombrado a C2 paper)
    c4_per_agent = c4_result["per_agent"]
    c4_net_per_agent = np.array([
        c4_per_agent[n]["net_benefit"] if n in c4_per_agent else 0.0
        for n in range(N)
    ])
    c4_total = float(np.sum(c4_net_per_agent))

    rows = [
        {
            "Escenario": PAPER_RENAMING["P2P"],
            "net_benefit_total_COP": round(p2p_net, 1),
            "kWh_P2P_total": round(p2p_kwh, 3),
            "horas_activas": len(active),
            "Mecanismo": "Stackelberg leader-follower + Replicator Dynamics",
            "Fuente legal": "—",
        },
        {
            "Escenario": PAPER_RENAMING["C1"],
            "net_benefit_total_COP": round(c1_total, 1),
            "kWh_P2P_total": 0.0,
            "horas_activas": 0,
            "Mecanismo": "AGPE Tipo 1 / Tipo 2 + componente Cvm",
            "Fuente legal": "CREG 174/2021 art. 22-25",
        },
        {
            "Escenario": PAPER_RENAMING["C4"],
            "net_benefit_total_COP": round(c4_total, 1),
            "kWh_P2P_total": 0.0,
            "horas_activas": 0,
            "Mecanismo": "PDE comunitario + herencia CREG 174",
            "Fuente legal": "Decreto 2236/2023 + CREG 101 072/2025",
        },
    ]
    return pd.DataFrame(rows), {
        PAPER_RENAMING["P2P"]: (p2p_net, p2p_net_per_agent),
        PAPER_RENAMING["C1"]:  (c1_total, c1_net_per_agent),
        PAPER_RENAMING["C4"]:  (c4_total, c4_net_per_agent),
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
              tag: str, month: str) -> dict:
    """Genera xlsx + png de perfiles."""
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

    return {"xlsx": str(xlsx_path), "month": month, "tag": tag}


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

    # Resumen + por_agente
    resumen, scenarios_data = construir_resumen(
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
                     out_dir, args.tag, args.month)
    print(f"\n  [paper] Hecho. tag={info['tag']}")
    return 0


if __name__ == "__main__":
    _wrap_stdout_utf8()
    sys.exit(main())
