"""
smoke_common.py — Infraestructura compartida de la campaña de smokes (ADR-0038)
================================================================================
Datasets, cache de corridas EMS, CheckResult y reporte consolidado.

Datasets soportados (claves de `load_dataset`):
  "SYN"      — sintético 24h del modelo base (réplica exacta de main_simulation)
  "COB-M1"   — horizonte real completo, demanda totalizador (cobertura ~19%)
  "COB-M3"   — horizonte real completo, sub-medidores del paper (~91%)
  "ago-2025" / "oct-2025" — slices mensuales de COB-M1 (para barridos)

Cada corrida EMS pesada se cachea en outputs/smoke_cache/<hash>.pkl con clave
= (dataset, campos de SolverParams, override de grid). Todos los smokes que
comparten configuración reusan la MISMA corrida.

Convención de veredictos: PASS / WARN / FAIL / INFO / SKIP.
El reporte consolidado vive en outputs/smoke_campaign_report.md y su fuente
de verdad acumulada en outputs/smoke_campaign_results.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import sys
import time
import warnings
from dataclasses import dataclass, asdict, field, fields, replace
from typing import Optional

warnings.filterwarnings("ignore")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np

from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams

CACHE_DIR   = os.path.join(ROOT, "outputs", "smoke_cache")
REPORT_MD   = os.path.join(ROOT, "outputs", "smoke_campaign_report.md")
RESULTS_JSON = os.path.join(ROOT, "outputs", "smoke_campaign_results.json")

VOLUME_MIN_KWH = 0.01    # umbral de "hora con energía material" (C5, fixtures)

AGENT_NAMES_REAL = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]

# SolverParams de producción de la tesis (= main_simulation.py:252, CAL-34)
PROD_SOLVER = dict(tau=0.001, t_span=(0.0, 0.005), n_points=150,
                   stackelberg_iters=2, parallel=True)


# ─────────────────────────────────────────────────────────────────────────────
# Resultado de un check
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    id:        str            # p.ej. "R1"
    eje:       str            # reparto | equivalencia | precios | solver
    datos:     str            # SYN | COB-M1 | COB-M3 | FIX | ago-2025 ...
    metric:    str
    value:     str            # formateado (puede ser "3.1e-13" o "0/4773")
    threshold: str
    verdict:   str            # PASS | WARN | FAIL | INFO | SKIP
    tier:      int
    seconds:   float = 0.0
    detail:    str   = ""

    def row(self) -> str:
        return (f"| {self.id} | {self.eje} | {self.datos} | {self.metric} | "
                f"{self.value} | {self.threshold} | {self.verdict} | "
                f"{self.tier} | {self.seconds:.0f} |")


# ─────────────────────────────────────────────────────────────────────────────
# Datasets
# ─────────────────────────────────────────────────────────────────────────────

def load_dataset(name: str) -> dict:
    """Carga un dataset replicando exactamente la preparación de
    main_simulation.py. Retorna dict con:
      D, G (N,T) · agents (AgentParams) · grid (GridParams) · names ·
      pi_gs_matrix (N,T) · pi_bolsa (T,) · month_labels (T,)|None · index|None
    """
    if name == "SYN":
        return _load_synthetic()
    if name in ("COB-M1", "COB-M3"):
        return _load_real(paper_meters=(name == "COB-M3"))
    if name in ("ago-2025", "oct-2025"):
        full = _load_real(paper_meters=False)
        ym = 202508 if name == "ago-2025" else 202510
        mask = full["month_labels"] == ym
        if not mask.any():
            raise ValueError(f"{name}: sin horas con etiqueta {ym}")
        sl = {**full, "name": name,
              "D": full["D"][:, mask], "G": full["G"][:, mask],
              "pi_gs_matrix": full["pi_gs_matrix"][:, mask],
              "pi_bolsa": full["pi_bolsa"][mask],
              "month_labels": full["month_labels"][mask],
              "index": full["index"][mask]}
        return sl
    raise ValueError(f"dataset desconocido: {name!r}")


def _load_synthetic() -> dict:
    from data.base_case_data import (
        get_generation_profiles, get_demand_profiles, get_agent_params,
        GRID_PARAMS,
    )
    G = get_generation_profiles()
    D = get_demand_profiles()
    p = get_agent_params()
    agents = AgentParams(**p)
    grid = GridParams(**GRID_PARAMS)
    N, T = D.shape
    pi_gs_matrix = np.full((N, T), float(grid.pi_gs))
    pi_bolsa = np.full(T, float(grid.pi_gb))
    return dict(name="SYN", D=D, G=G, agents=agents, grid=grid,
                names=[f"A{i+1}" for i in range(N)],
                pi_gs_matrix=pi_gs_matrix, pi_bolsa=pi_bolsa,
                month_labels=None, index=None,
                prosumer_ids=[0, 1, 2, 3], consumer_ids=[4, 5])


def _load_real(paper_meters: bool) -> dict:
    import pandas as pd
    from data.xm_data_loader import MTEDataLoader
    from data.cedenar_tariff import (
        community_effective_pi_gs, pi_gs_per_agent_hourly,
    )
    from data.xm_prices import get_pi_bolsa, get_b_for_real_data
    from data.base_case_data import GRID_PARAMS_REAL

    mte_root = os.environ.get("MTE_ROOT",
                              os.path.join(ROOT, "MedicionesMTE_v3"))
    demand_cfg = None
    if paper_meters:
        from data.preprocessing import PAPER_METER_DEMAND_CONFIG
        demand_cfg = PAPER_METER_DEMAND_CONFIG
    loader = MTEDataLoader(mte_root, demand_config=demand_cfg)
    D, G, index_full = loader.load(verbose=False)
    N, T = D.shape
    names = AGENT_NAMES_REAL[:N]

    pi_gs_eff = community_effective_pi_gs(
        names, index_full[0], index_full[-1] + pd.Timedelta(hours=1),
        weights=D.mean(axis=1))
    grid = GridParams(**{**GRID_PARAMS_REAL, "pi_gs": pi_gs_eff})

    b_cal = get_b_for_real_data(N, names)
    agents = AgentParams(N=N, a=np.zeros(N), b=b_cal, c=np.zeros(N),
                         lam=np.full(N, 100.0), theta=np.full(N, 0.5),
                         etha=np.full(N, 0.1))

    pi_gs_matrix = pi_gs_per_agent_hourly(names, index_full)
    xm_csv = os.path.join(ROOT, "data", "xm_precios_bolsa.csv")
    pi_bolsa = get_pi_bolsa(
        T,
        t_start=index_full[0].strftime("%Y-%m-%d"),
        t_end=(index_full[-1] + pd.Timedelta(hours=1)).strftime("%Y-%m-%d"),
        csv_path=xm_csv if os.path.exists(xm_csv) else None,
        scenario="2025_normal")
    month_labels = np.array([ts.year * 100 + ts.month for ts in index_full],
                            dtype=int)
    return dict(name="COB-M3" if paper_meters else "COB-M1",
                D=D, G=G, agents=agents, grid=grid, names=names,
                pi_gs_matrix=pi_gs_matrix, pi_bolsa=pi_bolsa,
                month_labels=month_labels, index=index_full,
                prosumer_ids=list(range(N)), consumer_ids=[])


# ─────────────────────────────────────────────────────────────────────────────
# Cache de corridas EMS
# ─────────────────────────────────────────────────────────────────────────────

def make_solver(**overrides) -> SolverParams:
    """SolverParams de producción de la tesis con overrides."""
    return SolverParams(**{**PROD_SOLVER, **overrides})


def _solver_signature(sv: SolverParams) -> str:
    return json.dumps({f.name: str(getattr(sv, f.name))
                       for f in fields(sv)}, sort_keys=True)


def run_ems_cached(ds: dict, sv: Optional[SolverParams] = None,
                   grid_override: Optional[GridParams] = None,
                   verbose: bool = True):
    """Corre EMSP2P.run con cache en disco. Retorna (results, G_klim, D_star)."""
    sv = sv or make_solver()
    grid = grid_override or ds["grid"]
    key_src = "|".join([
        ds["name"], str(ds["D"].shape), f"{float(np.sum(ds['D'])):.6f}",
        f"{float(np.sum(ds['G'])):.6f}",
        f"pi_gs={grid.pi_gs:.6f}", f"pi_gb={grid.pi_gb:.6f}",
        _solver_signature(sv),
    ])
    key = hashlib.md5(key_src.encode()).hexdigest()[:16]
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"ems_{ds['name']}_{key}.pkl")
    if os.path.exists(path):
        if verbose:
            print(f"    [cache hit] {os.path.basename(path)}")
        with open(path, "rb") as f:
            return pickle.load(f)
    t0 = time.time()
    ems = EMSP2P(ds["agents"], grid, sv)
    results, G_klim, D_star = ems.run(ds["D"], ds["G"])
    payload = (results, G_klim, D_star)
    with open(path, "wb") as f:
        pickle.dump(payload, f)
    if verbose:
        print(f"    [cache store] {os.path.basename(path)} "
              f"({time.time()-t0:.0f}s)")
    return payload


def active_hours(results) -> list:
    """Índices locales con mercado P2P activo (P_star válido y volumen>0)."""
    out = []
    for k_local, r in enumerate(results):
        if r.P_star is None:
            continue
        if np.isnan(r.P_star).any():
            continue
        if float(np.sum(r.P_star)) > 1e-9:
            out.append(k_local)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Reporte consolidado
# ─────────────────────────────────────────────────────────────────────────────

def save_results(rows: list, tier: int) -> None:
    """Acumula CheckResults en el JSON (reemplaza entradas mismo id+datos)
    y regenera el MD consolidado."""
    data = {}
    if os.path.exists(RESULTS_JSON):
        with open(RESULTS_JSON, encoding="utf-8") as f:
            data = json.load(f)
    for r in rows:
        data[f"{r.id}::{r.datos}"] = asdict(r)
    os.makedirs(os.path.dirname(RESULTS_JSON), exist_ok=True)
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    _write_md(data)


def _write_md(data: dict) -> None:
    rows = [CheckResult(**v) for v in data.values()]
    rows.sort(key=lambda r: (r.eje, r.id, r.datos))
    counts = {}
    for r in rows:
        counts[r.verdict] = counts.get(r.verdict, 0) + 1
    lines = [
        "# Campaña de smokes — modelo P2P (ADR-0038)",
        "",
        f"Actualizado: {time.strftime('%Y-%m-%d %H:%M')}",
        "",
        "Resumen: " + " | ".join(f"{v} {k}" for k, v in sorted(counts.items())),
        "",
        "| ID | Eje | Datos | Métrica | Valor | Umbral | Veredicto | Tier | t(s) |",
        "|----|-----|-------|---------|-------|--------|-----------|------|------|",
    ]
    lines += [r.row() for r in rows]
    details = [r for r in rows if r.detail]
    if details:
        lines += ["", "## Detalles"]
        for r in details:
            lines += [f"### {r.id} ({r.datos})", r.detail, ""]
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def hard_failures(rows: list) -> list:
    return [r for r in rows if r.verdict == "FAIL"]


def setup_stdout_utf8() -> None:
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace")
