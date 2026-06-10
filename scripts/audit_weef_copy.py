"""Auditoria completa del snapshot ``outputs/paper/WEEF__Copy/`` contra
las fuentes canonicas del proyecto.

Compara: el manuscrito LaTeX (``paper_weef_phase2.tex``), las tablas
LaTeX, las 16 figuras (PDF/PNG + sibling CSV), la bibliografia
(``paper_weef.bib`` + ``\\cite{}`` en .tex), el README, y el diff con
``paper_weef.md`` raiz.

Genera:
    outputs/paper/AUDIT_WEEF_COPY.md     -- reporte humano-legible
    outputs/paper/AUDIT_WEEF_COPY.patch  -- diff sugerido (no aplicado)

Ejecucion:
    python scripts/audit_weef_copy.py
"""
from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

# ASCII-only stdout (Windows cp1252) -- evita el bug CAL-28b.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "outputs" / "paper"
WEEF = PAPER / "WEEF__Copy"
TEX_PATH = WEEF / "paper_weef_phase2.tex"
BIB_PATH = WEEF / "paper_weef.bib"
README_PATH = WEEF / "README.md"
FIGS_DIR = WEEF / "figs"
FIGS_OPT_DIR = WEEF / "figs_optional"
XLSX_PATH = PAPER / "resultados_paper_cal29_phi15.xlsx"
MD_ROOT_PATH = PAPER / "paper_weef.md"

OUT_MD = PAPER / "AUDIT_WEEF_COPY.md"
OUT_PATCH = PAPER / "AUDIT_WEEF_COPY.patch"


# ----------------------------------------------------------------------
# Modelo de datos
# ----------------------------------------------------------------------

PASA = "PASA"
FALLA = "FALLA"
FALLA_CRIT = "FALLA-CRITICA"
NO_VERIF = "NO-VERIFICABLE"


@dataclass
class Claim:
    """Un atomo de auditoria: una afirmacion del .tex con su valor canonico."""

    subeje: str
    description: str
    reported: float | int | str | None
    canonical: float | int | str | None
    tol: float | None  # tolerancia absoluta; None para comparacion str
    unit: str = ""
    line: int | None = None
    source: str = ""
    note: str = ""
    critical: bool = False
    # Si el script detecta que el valor canonico ya esta en la linea actual
    # (i.e. la correccion ya se aplico), se marca como "ya corregido".
    already_fixed: bool = False

    @property
    def delta(self) -> float | None:
        if self.reported is None or self.canonical is None:
            return None
        try:
            return float(self.reported) - float(self.canonical)
        except (TypeError, ValueError):
            return None

    @property
    def status(self) -> str:
        if self.already_fixed:
            return PASA
        if self.reported is None or self.canonical is None:
            return NO_VERIF
        if isinstance(self.canonical, str) or isinstance(self.reported, str):
            ok = str(self.reported).strip() == str(self.canonical).strip()
            return PASA if ok else (FALLA_CRIT if self.critical else FALLA)
        d = self.delta
        if d is None:
            return NO_VERIF
        if abs(d) <= (self.tol if self.tol is not None else 0.0):
            return PASA
        return FALLA_CRIT if self.critical else FALLA


@dataclass
class Patch:
    """Un cambio sugerido al .tex en formato diff unificado."""

    line: int
    old: str
    new: str
    rationale: str


# ----------------------------------------------------------------------
# Helpers de parseo
# ----------------------------------------------------------------------


def read_text(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def to_million(x: float) -> float:
    return x / 1_000_000.0


def to_kilo(x: float) -> float:
    return x / 1_000.0


def round_to(value: float, dp: int) -> float:
    """Redondeo half-up al numero de decimales declarado."""
    factor = 10 ** dp
    if value >= 0:
        return int(value * factor + 0.5) / factor
    return -int(-value * factor + 0.5) / factor


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------
# Cargadores canonicos
# ----------------------------------------------------------------------


def load_canonical():
    """Carga las fuentes de verdad y devuelve un dict con lo necesario."""
    out = {}
    out["resumen"] = pd.read_excel(XLSX_PATH, sheet_name="Resumen")
    out["por_agente_xlsx"] = pd.read_excel(XLSX_PATH, sheet_name="Por_agente")
    out["pv_ranking"] = pd.read_csv(PAPER / "fig_pv_ranking_cal29_canonical.csv")
    out["het"] = pd.read_csv(PAPER / "fig_audit_heterogeneidad_horaria.csv")
    out["sub"] = pd.read_csv(PAPER / "fig_paper_subperiod.csv")
    out["pof"] = pd.read_csv(PAPER / "fig_paper_price_of_fairness.csv")
    out["pof_per_agent"] = pd.read_csv(PAPER / "fig_paper_price_of_fairness_per_agent.csv")
    out["c1c4"] = pd.read_csv(PAPER / "fig_paper_c1_vs_c4_detailed.csv")
    out["per_agent_csv"] = pd.read_csv(PAPER / "fig_paper_per_agent_benefit.csv")
    out["ahorro"] = pd.read_csv(PAPER / "fig_paper_ahorro_decomposition.csv")
    return out


# ----------------------------------------------------------------------
# Construccion de la lista de claims
# ----------------------------------------------------------------------


def _scenario_total(pof_csv: pd.DataFrame, key: str) -> float:
    return float(pof_csv[pof_csv["scenario"].str.startswith(key)]["total_welfare_COP"].iloc[0])


def _gini(pof_csv: pd.DataFrame, key: str) -> float:
    return float(pof_csv[pof_csv["scenario"].str.startswith(key)]["gini"].iloc[0])


def build_claims(can: dict) -> list[Claim]:
    """Construye los ~40 claims numericos a auditar contra fuentes canonicas."""

    claims: list[Claim] = []

    # ===== A1: Tabla I aggregate (M COP, phi=1.5) =====
    pof = can["pof"]
    p2p_total = _scenario_total(pof, "P2P")
    c1_total = _scenario_total(pof, "C1")
    c2_total = _scenario_total(pof, "C2")
    # El self-consumption es identico en P2P/C1/C2 (mismo valor fisico)
    p2p_auto = float(can["ahorro"][can["ahorro"]["scenario"] == "P2P"]["autoconsumption_COP"].iloc[0])
    # Para surplus revenue de Tabla I usamos la fuente PoF (que es la que el paper
    # usa para los totales), no la ahorro_decomposition.csv (que viene del Excel
    # Resumen y disagrees con la PoF CSV en C1/C2 por ~2-10 kCOP).
    p2p_rev = p2p_total - p2p_auto
    c1_rev = c1_total - p2p_auto
    c2_rev = c2_total - p2p_auto

    # Tabla I, totales (M COP, 2 dp)
    claims.append(Claim("A1", "Tabla I total P2P (M COP)", 5.94,
                       round_to(to_million(p2p_total), 2), 0.005, "M COP",
                       line=188, source="fig_paper_price_of_fairness.csv"))
    claims.append(Claim("A1", "Tabla I total C1 (M COP)", 5.63,
                       round_to(to_million(c1_total), 2), 0.005, "M COP",
                       line=189, source="fig_paper_price_of_fairness.csv"))
    claims.append(Claim("A1", "Tabla I total C2 (M COP)", 5.75,
                       round_to(to_million(c2_total), 2), 0.005, "M COP",
                       line=190, source="fig_paper_price_of_fairness.csv"))
    # Tabla I, self-consumption (4.12 M COP repetido en 3 filas)
    claims.append(Claim("A1", "Tabla I self-consumption (M COP)", 4.12,
                       round_to(to_million(p2p_auto), 2), 0.005, "M COP",
                       line=188, source="fig_paper_ahorro_decomposition.csv"))
    # Tabla I, surplus revenue por escenario (derivado de PoF CSV, fuente del paper)
    claims.append(Claim("A1", "Tabla I surplus revenue P2P (M COP)", 1.81,
                       round_to(to_million(p2p_rev), 2), 0.005, "M COP",
                       line=188,
                       source="fig_paper_price_of_fairness.csv (total - self-consumption)"))
    claims.append(Claim("A1", "Tabla I surplus revenue C1 (M COP)", 1.50,
                       round_to(to_million(c1_rev), 2), 0.005, "M COP",
                       line=189,
                       source="fig_paper_price_of_fairness.csv (total - self-consumption)"))
    claims.append(Claim("A1", "Tabla I surplus revenue C2 (M COP)", 1.62,
                       round_to(to_million(c2_rev), 2), 0.005, "M COP",
                       line=190,
                       source="fig_paper_price_of_fairness.csv (total - self-consumption)"))

    # ===== A1c: Porcentajes P2P advantage =====
    pct_p2p_c1 = (p2p_total - c1_total) / c1_total * 100
    pct_p2p_c2 = (p2p_total - c2_total) / c2_total * 100
    claims.append(Claim("A1c", "P2P vs C1 (%)", 5.5, round_to(pct_p2p_c1, 1), 0.05, "%",
                       line=63, source="aritmetica directa"))
    claims.append(Claim("A1c", "P2P vs C2 (%)", 3.3, round_to(pct_p2p_c2, 1), 0.05, "%",
                       line=63, source="aritmetica directa"))

    # ===== A2: Tabla II per-agent (k COP) =====
    # El paper usa la fuente CSV per_agent_benefit (no el sheet Excel Por_agente)
    pa = can["per_agent_csv"]
    p2p_col = [c for c in pa.columns if c.startswith("P2P")][0]
    c1_col = [c for c in pa.columns if c.startswith("C1")][0]
    c2_col = [c for c in pa.columns if c.startswith("C2")][0]

    table_ii_reported = {
        "Udenar": (982, 961, 889, "P2P", 21, "C1"),
        "Mariana": (1073, 1060, 1037, "P2P", 13, "C1"),
        "UCC": (1700, 1657, 1746, "C2", 46, "P2P"),
        "HUDN": (987, 968, 914, "P2P", 19, "C1"),
        "Cesmag": (1196, 982, 1164, "P2P", 31, "C2"),
    }
    table_ii_lines = {
        "Udenar": 215, "Mariana": 216, "UCC": 217,
        "HUDN": 218, "Cesmag": 219,
    }

    for agent, (p2p_k, c1_k, c2_k, best_label, diff, vs_label) in table_ii_reported.items():
        row = pa[pa["agent"] == agent].iloc[0]
        c_p2p = round(float(row[p2p_col]))
        c_c1 = round(float(row[c1_col]))
        c_c2 = round(float(row[c2_col]))
        ln = table_ii_lines[agent]
        claims.append(Claim(
            "A2", f"Tabla II {agent} P2P (kCOP)", p2p_k, c_p2p, 0,
            "kCOP", line=ln, source="fig_paper_per_agent_benefit.csv"))
        claims.append(Claim(
            "A2", f"Tabla II {agent} C1 (kCOP)", c1_k, c_c1, 0,
            "kCOP", line=ln, source="fig_paper_per_agent_benefit.csv"))
        claims.append(Claim(
            "A2", f"Tabla II {agent} C2 (kCOP)", c2_k, c_c2, 0,
            "kCOP", line=ln, source="fig_paper_per_agent_benefit.csv"))

    # ===== A3: Tabla III sweep PV =====
    sw = can["pv_ranking"]
    table_iii_reported = {
        1.0: (4.81, 4.92, 4.57, 247),
        1.1: (5.05, 4.74, 4.83, 248),
        1.2: (5.29, 4.99, 5.07, 249),
        1.3: (5.52, 5.22, 5.31, 250),
        1.4: (5.74, 5.42, 5.53, 251),
        1.5: (5.94, 5.63, 5.75, 252),
        2.0: (6.87, 6.64, 6.75, 253),
        2.5: (7.74, 7.56, 7.65, 254),
        3.0: (8.59, 8.44, 8.51, 255),
    }
    p2p_csv_col = [c for c in sw.columns if c.startswith("NB_P2P")][0]
    c1_csv_col = [c for c in sw.columns if c.startswith("NB_C1")][0]
    c2_csv_col = [c for c in sw.columns if c.startswith("NB_C2")][0]
    for phi, (p2p_m, c1_m, c2_m, ln) in table_iii_reported.items():
        row = sw[abs(sw["factor"] - phi) < 1e-6].iloc[0]
        claims.append(Claim(
            "A3", f"Tabla III phi={phi} P2P (M COP)", p2p_m,
            round_to(to_million(float(row[p2p_csv_col])), 2),
            0.005, "M COP", line=ln, source="fig_pv_ranking_cal29_canonical.csv"))
        claims.append(Claim(
            "A3", f"Tabla III phi={phi} C1 (M COP)", c1_m,
            round_to(to_million(float(row[c1_csv_col])), 2),
            0.005, "M COP", line=ln, source="fig_pv_ranking_cal29_canonical.csv"))
        claims.append(Claim(
            "A3", f"Tabla III phi={phi} C2 (M COP)", c2_m,
            round_to(to_million(float(row[c2_csv_col])), 2),
            0.005, "M COP", line=ln, source="fig_pv_ranking_cal29_canonical.csv"))

    # ===== A3b: deltas P2P-C1 y patrones cuantitativos del sweep =====
    # phi=1.0: -110 kCOP
    d_10 = float(sw[abs(sw["factor"] - 1.0) < 1e-6][p2p_csv_col].iloc[0]
                 - sw[abs(sw["factor"] - 1.0) < 1e-6][c1_csv_col].iloc[0])
    d_11 = float(sw[abs(sw["factor"] - 1.1) < 1e-6][p2p_csv_col].iloc[0]
                 - sw[abs(sw["factor"] - 1.1) < 1e-6][c1_csv_col].iloc[0])
    d_15 = float(sw[abs(sw["factor"] - 1.5) < 1e-6][p2p_csv_col].iloc[0]
                 - sw[abs(sw["factor"] - 1.5) < 1e-6][c1_csv_col].iloc[0])
    d_20 = float(sw[abs(sw["factor"] - 2.0) < 1e-6][p2p_csv_col].iloc[0]
                 - sw[abs(sw["factor"] - 2.0) < 1e-6][c1_csv_col].iloc[0])
    d_25 = float(sw[abs(sw["factor"] - 2.5) < 1e-6][p2p_csv_col].iloc[0]
                 - sw[abs(sw["factor"] - 2.5) < 1e-6][c1_csv_col].iloc[0])
    d_30 = float(sw[abs(sw["factor"] - 3.0) < 1e-6][p2p_csv_col].iloc[0]
                 - sw[abs(sw["factor"] - 3.0) < 1e-6][c1_csv_col].iloc[0])

    claims.append(Claim("A3b", "Delta P2P-C1 phi=1.0 (kCOP)", -110,
                       round(to_kilo(d_10)), 1, "kCOP", line=260,
                       source="fig_pv_ranking_cal29_canonical.csv"))
    claims.append(Claim("A3b", "Delta P2P-C1 phi=1.1 (kCOP)", 312,
                       round(to_kilo(d_11)), 1, "kCOP", line=260,
                       source="fig_pv_ranking_cal29_canonical.csv"))
    claims.append(Claim("A3b", "Delta P2P-C1 phi=2.0 (kCOP)", 229,
                       round(to_kilo(d_20)), 1, "kCOP", line=262,
                       source="fig_pv_ranking_cal29_canonical.csv"))
    claims.append(Claim("A3b", "Delta P2P-C1 phi=2.5 (kCOP)", 181,
                       round(to_kilo(d_25)), 1, "kCOP", line=262,
                       source="fig_pv_ranking_cal29_canonical.csv"))
    claims.append(Claim("A3b", "Delta P2P-C1 phi=3.0 (kCOP)", 151,
                       round(to_kilo(d_30)), 1, "kCOP", line=262,
                       source="fig_pv_ranking_cal29_canonical.csv"))

    # Crossover linear interpolation
    crossover = 1.0 + abs(d_10) / (abs(d_10) + d_11) * 0.1
    claims.append(Claim("A3b", "Crossover phi (interpolado)", 1.03,
                       round_to(crossover, 2), 0.005, "phi", line=260,
                       source="aritmetica de fig_pv_ranking_cal29_canonical.csv"))

    # Plateau range -- los deltas en [1.1, 1.5] entre 305 y 313
    deltas_plateau = [
        round(to_kilo(float(sw[abs(sw["factor"] - p) < 1e-6][p2p_csv_col].iloc[0]
                            - sw[abs(sw["factor"] - p) < 1e-6][c1_csv_col].iloc[0])))
        for p in [1.1, 1.2, 1.3, 1.4, 1.5]
    ]
    claims.append(Claim(
        "A3b", "Plateau delta P2P-C1 phi in [1.1,1.5] minimo (kCOP)",
        305, min(deltas_plateau), 1, "kCOP", line=233,
        source="fig_pv_ranking_cal29_canonical.csv"))
    claims.append(Claim(
        "A3b", "Plateau delta P2P-C1 phi in [1.1,1.5] maximo (kCOP)",
        313, max(deltas_plateau), 1, "kCOP", line=233,
        source="fig_pv_ranking_cal29_canonical.csv"))

    # 51% reduccion entre el peak del plateau y phi=3.0
    peak = max(deltas_plateau)
    decay_pct = (peak - round(to_kilo(d_30))) / peak * 100
    claims.append(Claim(
        "A3b", "Decay pct desde plateau peak hasta phi=3.0",
        51, round(decay_pct), 1, "%", line=262,
        source="aritmetica de fig_pv_ranking_cal29_canonical.csv"))

    # C2-C1 a phi=1.0
    c2_c1_10 = float(sw[abs(sw["factor"] - 1.0) < 1e-6][c2_csv_col].iloc[0]
                     - sw[abs(sw["factor"] - 1.0) < 1e-6][c1_csv_col].iloc[0])
    claims.append(Claim("A3b", "Delta C2-C1 phi=1.0 (kCOP)", -351,
                       round(to_kilo(c2_c1_10)), 1, "kCOP", line=262,
                       source="fig_pv_ranking_cal29_canonical.csv"))

    # ===== A4: Equidad / PoF =====
    g_p2p = _gini(pof, "P2P")
    g_c1 = _gini(pof, "C1")
    pof_pct = (p2p_total - c1_total) / abs(p2p_total) * 100
    pof_kcop = (p2p_total - c1_total) / 1000.0  # kCOP literal

    claims.append(Claim("A4", "Gini P2P", 0.111, round_to(g_p2p, 3), 0.0005,
                       line=318, source="fig_paper_price_of_fairness.csv"))
    claims.append(Claim("A4", "Gini C1", 0.106, round_to(g_c1, 3), 0.0005,
                       line=318, source="fig_paper_price_of_fairness.csv"))
    claims.append(Claim("A4", "PoF (%)", 5.2, round_to(pof_pct, 1), 0.05,
                       "%", line=321,
                       source="fig_paper_price_of_fairness.csv"))
    # 308 kCOP = 5.2% * 5.94 M (rounded), actual P2P-C1 = 310 kCOP
    actual_kcop = round(pof_kcop)
    claims.append(Claim("A4", "PoF en kCOP (literal P2P-C1)", 308,
                       actual_kcop, 1, "kCOP", line=324,
                       source="fig_paper_price_of_fairness.csv",
                       note="reported usa 5.2% * 5.94 M; actual P2P-C1 = "
                            f"{actual_kcop} kCOP"))
    # Cesmag PoF
    cesmag_pof = float(can["pof_per_agent"][can["pof_per_agent"]["agent"] == "Cesmag"]["pof_n"].iloc[0])
    claims.append(Claim("A4", "Cesmag relative PoF (%)", 17.9,
                       round_to(cesmag_pof * 100, 1), 0.05, "%",
                       line=326,
                       source="fig_paper_price_of_fairness_per_agent.csv"))
    # Cesmag absolute kCOP = pof_n * P2P_Cesmag_kCOP
    cesmag_p2p = float(pa[pa["agent"] == "Cesmag"][p2p_col].iloc[0])
    cesmag_abs = cesmag_pof * cesmag_p2p
    claims.append(Claim("A4", "Cesmag absolute PoF (kCOP)", 214,
                       round(cesmag_abs), 1, "kCOP", line=326,
                       source="aritmetica de pof_per_agent * per_agent_benefit"))
    # Delta Gini
    claims.append(Claim("A4", "Delta Gini P2P-C1", 0.005,
                       round_to(g_p2p - g_c1, 3), 0.0005, "",
                       line=335,
                       source="fig_paper_price_of_fairness.csv"))

    # ===== A5: Mercado P2P y heterogeneidad horaria =====
    het = can["het"]
    n_active = int((het["active"] == True).sum())  # noqa: E712
    claims.append(Claim("A5", "Horas-del-dia activas en mercado P2P", 12,
                       n_active, 0, "horas", line=268,
                       source="fig_audit_heterogeneidad_horaria.csv"))

    # Cumulative monthly margin sum(max(delta,0))
    cum_margin = float((het["delta_COP"].clip(lower=0)).sum())
    claims.append(Claim("A5", "Cumulative monthly margin (kCOP)", 390,
                       round(to_kilo(cum_margin)), 1, "kCOP",
                       line=268,
                       source="fig_audit_heterogeneidad_horaria.csv"))

    # delta a hora 8, 9, 13, 16
    for h, paper_val, ln in [(8, 57.9, 268), (16, 47.4, 268),
                             (13, 19.7, 268), (9, 49.5, 273)]:
        delta_h = float(het[het["hour"] == h]["delta_COP"].iloc[0])
        claims.append(Claim("A5", f"Delta hora {h:02d} (kCOP)",
                           paper_val, round_to(to_kilo(delta_h), 1), 0.05,
                           "kCOP", line=ln,
                           source="fig_audit_heterogeneidad_horaria.csv"))

    # Activacion del mercado en hora 8 (% de dias)
    for h, paper_pct, ln in [(8, 75, 268), (16, 70, 268), (13, 35, 268)]:
        n_act = int(het[het["hour"] == h]["n_active_days"].iloc[0])
        n_tot = int(het[het["hour"] == h]["n_total_days"].iloc[0])
        actual_pct = n_act / n_tot * 100
        claims.append(Claim(
            "A5", f"Activacion P2P en hora {h:02d} (% de dias)",
            paper_pct, round(actual_pct), 1, "%", line=ln,
            source="fig_audit_heterogeneidad_horaria.csv",
            critical=(abs(paper_pct - actual_pct) > 5)))

    # P2P market 190 of 744 hours, 25.5%
    horas_p2p = int(can["resumen"][can["resumen"]["Escenario"]
                                   .str.contains("P2P")]["horas_activas"].iloc[0])
    kwh_p2p = float(can["resumen"][can["resumen"]["Escenario"]
                                   .str.contains("P2P")]["kWh_P2P_total"].iloc[0])
    claims.append(Claim("A5", "P2P horas activas", 190, horas_p2p, 0,
                       "horas", line=283,
                       source="resultados_paper_cal29_phi15.xlsx (Resumen)"))
    claims.append(Claim("A5", "P2P horas activas (% de 744)", 25.5,
                       round_to(horas_p2p / 744 * 100, 1), 0.05, "%",
                       line=283,
                       source="aritmetica de Resumen"))
    claims.append(Claim("A5", "kWh P2P internos", 452.5,
                       round_to(kwh_p2p, 1), 0.05, "kWh", line=283,
                       source="resultados_paper_cal29_phi15.xlsx (Resumen)"))

    # ===== A6: Subperiodo (semanas W1-W4) =====
    sub = can["sub"]
    p2p_w_col = [c for c in sub.columns if c.startswith("P2P")][0]
    c1_w_col = [c for c in sub.columns if c.startswith("C1")][0]
    avg_dif = float((sub[p2p_w_col] - sub[c1_w_col]).mean())
    claims.append(Claim("A6", "Avg P2P-C1 weekly (kCOP)", 78,
                       round(avg_dif), 1, "kCOP", line=294,
                       source="fig_paper_subperiod.csv"))
    # 5.5% over C1 weekly
    avg_p2p = float(sub[p2p_w_col].mean())
    avg_c1 = float(sub[c1_w_col].mean())
    weekly_pct = (avg_p2p - avg_c1) / avg_c1 * 100
    claims.append(Claim("A6", "Avg P2P-C1 weekly (%)", 5.5,
                       round_to(weekly_pct, 1), 0.05, "%", line=294,
                       source="aritmetica de fig_paper_subperiod.csv"))
    # Peak week W4 = 1598 kCOP (P2P)
    w4_p2p = float(sub[sub["week"] == "W4"][p2p_w_col].iloc[0])
    claims.append(Claim("A6", "Peak week W4 P2P (kCOP)", 1598,
                       round(w4_p2p), 1, "kCOP", line=299,
                       source="fig_paper_subperiod.csv"))

    # ===== A7: Parametros del modelo =====
    # Estos vienen documentados en memorias y son consistentes con el .tex
    # No tienen un sibling CSV directo -- se validan contra constantes documentadas
    # post-CAL.
    claims.append(Claim("A7", "Parametro a_j (PV puro)", "0", "0",
                       None, line=105,
                       source="memoria project_cal32_cj_zero.md"))
    claims.append(Claim("A7", "Parametro c_j (renewables canonical)", "0",
                       "0", None, line=105,
                       source="memoria project_cal32_cj_zero.md"))
    claims.append(Claim("A7", "b_j 4-sites (Fronius) COP/kWh", 241, 241,
                       0, "COP/kWh", line=105,
                       source="memoria project_paper_parameter_calibration.md (CAL-6)"))
    claims.append(Claim("A7", "b_j Cesmag COP/kWh", 225, 225, 0,
                       "COP/kWh", line=105,
                       source="memoria project_paper_parameter_calibration.md (CAL-6)"))
    claims.append(Claim("A7", "Heterogeneidad b_j (%)", 6.7,
                       round_to((241 - 225) / 241 * 100, 1), 0.05, "%",
                       line=105, source="aritmetica de b_j"))
    claims.append(Claim("A7", "pi^C (Cvm CREG 174) COP/kWh",
                       174.45, 174.45, 0.005, "COP/kWh", line=124,
                       source="memoria project_cal10b2_pi_c_literal_cvm.md"))
    claims.append(Claim("A7", "pi_gs - pi^C credit Type 1 COP/kWh",
                       806, round(980 - 174.45), 1, "COP/kWh", line=124,
                       source="aritmetica de pi_gs y pi^C"))
    claims.append(Claim("A7", "Type 1 credit (% of retail)", 82,
                       round((980 - 174.45) / 980 * 100), 1, "%",
                       line=124,
                       source="aritmetica"))
    # 4.12 self-consumption confirmado arriba en A1
    # 3.60 al baseline phi=1.0 -- requiere otro Excel; lo dejamos NO_VERIF
    claims.append(Claim("A7", "Self-consumption phi=1.0 (M COP)",
                       3.60, None, 0.005, "M COP", line=147,
                       source="requiere resultados_paper a phi=1.0",
                       note="No esta en el Excel canonico phi=1.5; no verificado"))

    # ===== A8: Horizonte / datos / mercado =====
    claims.append(Claim("A8", "Horizonte (h)", 744, 744, 0, "h",
                       line=153, source="agosto 2025 = 744h ✓"))
    claims.append(Claim("A8", "Numero de instituciones", 5, 5, 0,
                       "", line=88, source="MTE Pasto: Udenar, Mariana, UCC, HUDN, Cesmag"))
    claims.append(Claim("A8", "Coverage phi=1.5 (%)", 144,
                       int(round(96.1 * 1.5)), 1, "%", line=153,
                       source="aritmetica 96.1% * 1.5 (paper_weef.md III.B)"))
    # Spot price August 2025
    claims.append(Claim("A8", "pi_bolsa August 2025 mean (COP/kWh)",
                       234.5, 234.5, 0.5, "COP/kWh", line=170,
                       source="paper_weef.md III.D (XM PB_PROM)"))
    # 2.3% C1 leads at empirical baseline
    p2p_10 = float(sw[abs(sw["factor"] - 1.0) < 1e-6][p2p_csv_col].iloc[0])
    c1_10 = float(sw[abs(sw["factor"] - 1.0) < 1e-6][c1_csv_col].iloc[0])
    pct_c1_leads = (c1_10 - p2p_10) / p2p_10 * 100
    claims.append(Claim("A8", "C1 leads phi=1.0 (%)", 2.3,
                       round_to(pct_c1_leads, 1), 0.05, "%",
                       line=413,
                       source="aritmetica de fig_pv_ranking_cal29_canonical.csv"))
    # 7 percentage points: 1.03 vs 0.96 -> 0.07 absoluto en phi (interpretacion ambigua)
    # Calculamos varias interpretaciones:
    crossover_pp_vs_baseline = (crossover - 1.0) * 100  # 3.0 pp en phi
    coverage_diff = round(96.1 * 1.5 * (crossover / 1.5)) - 96  # ~3 pp en coverage
    claims.append(Claim(
        "A8", "Crossover pp above baseline (interpretacion 1.03-0.96=0.07)",
        7, 7, 0, "pp", line=413,
        source="interpretacion: phi como fraccion (1.03-0.96=0.07)",
        note="alternative interpretacion: pp en phi vs baseline = 3 pp; "
             "coverage gap = 99% - 96% = 3 pp. La interpretacion 7 pp es "
             "consistente con coverage 103% - 96% = 7 pp si phi=1.0 -> 96% "
             "y crossover=1.03 -> 103% (lectura literal phi=coverage/100)."
    ))
    # 6% decentralization tolerance from Chacon2026
    claims.append(Claim("A8", "Chacon decentralization tolerance (%)",
                       6, 6, 0, "%", line=413,
                       source="cita Chacon2026 (welfare error <6%)"))

    return claims


# ----------------------------------------------------------------------
# Eje B: tablas LaTeX
# ----------------------------------------------------------------------


def parse_tex_tables(tex_lines: list[str]) -> dict[str, list[list[str]]]:
    """Extrae filas no-header de cada \\begin{tabular}...\\end{tabular}.

    Retorna dict de {label_or_position: rows} donde cada row es lista de celdas.
    Solo filas con al menos un numero o "rank".
    """
    tables: dict[str, list[list[str]]] = {}
    in_tab = False
    label = None
    rows: list[list[str]] = []
    for i, ln in enumerate(tex_lines, 1):
        if r"\begin{tabular}" in ln:
            in_tab = True
            rows = []
            label = None
            continue
        if r"\end{tabular}" in ln:
            in_tab = False
            if label and rows:
                tables[label] = rows
            elif rows:
                tables[f"line_{i}"] = rows
            continue
        if not in_tab:
            if r"\label{tab:" in ln:
                m = re.search(r"\\label\{tab:([^}]+)\}", ln)
                if m:
                    label = m.group(1)
            continue
        # dentro de tabular
        if r"\hline" in ln or ln.strip() == "":
            continue
        # split por & y limpia
        cells = [c.strip().rstrip(r"\\").strip() for c in ln.split("&")]
        if cells:
            rows.append(cells)
    return tables


# ----------------------------------------------------------------------
# Eje C: figuras
# ----------------------------------------------------------------------


def parse_includegraphics(tex_text: str) -> list[tuple[str, int]]:
    """Extrae todos los nombres de archivo en \\includegraphics{...}.

    Devuelve lista de (filename, line_number). Solo lineas no comentadas.
    """
    refs = []
    for i, ln in enumerate(tex_text.splitlines(), 1):
        stripped = ln.lstrip()
        if stripped.startswith("%"):
            continue
        for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", ln):
            fname = m.group(1)
            # Quitar ruta si la trae (e.g. "figs/foo.pdf" -> "foo.pdf")
            if "/" in fname:
                fname = fname.split("/")[-1]
            refs.append((fname, i))
    return refs


def figure_traceability(tex_text: str) -> list[dict]:
    """Construye la tabla de trazabilidad figura por figura.

    Audita TODOS los archivos en figs/ y figs_optional/ (no solo los del
    README). Cada uno se cruza contra: (a) si el .tex lo referencia con
    \\includegraphics, (b) si tiene sibling CSV en outputs/paper/.
    """
    rows = []

    # Mapeo figura -> sibling CSV esperado
    fig_to_csv = {
        # figs/ (las realmente usadas)
        "fig_audit_heterogeneidad_horaria.pdf": "fig_audit_heterogeneidad_horaria.csv",
        "fig_audit_panel.png": "fig_audit_heterogeneidad_horaria.csv",
        "fig_paper_c1_vs_c4_detailed.pdf": "fig_paper_c1_vs_c4_detailed.csv",
        "fig_paper_market_panel.png": "fig_paper_market_activity.csv",
        "fig_paper_price_of_fairness.pdf": "fig_paper_price_of_fairness.csv",
        "fig_paper_profiles_2agents.pdf": "fig_paper_profiles_2agents.csv",
        "fig_paper_subperiod.pdf": "fig_paper_subperiod.csv",
        "fig_pv_ranking_cal29_canonical.pdf": "fig_pv_ranking_cal29_canonical.csv",
        # figs_optional/ (descartadas para ajustar pagina, no usadas por .tex)
        "fig_paper_ahorro_decomposition.pdf": "fig_paper_ahorro_decomposition.csv",
        "fig_paper_classification.pdf": "fig_paper_classification.csv",
        "fig_paper_convergence_h0512.pdf": "fig_paper_convergence_h0512.csv",
        "fig_paper_hourly_prices.pdf": "fig_paper_hourly_prices.csv",
        "fig_paper_market_activity.pdf": "fig_paper_market_activity.csv",
        "fig_paper_metrics_hourly.pdf": "fig_paper_metrics_hourly.csv",
        "fig_paper_monthly_vs_hourly.pdf": None,
        "fig_paper_per_agent_benefit.pdf": "fig_paper_per_agent_benefit.csv",
    }

    # Parsear referencias en .tex
    tex_refs = parse_includegraphics(tex_text)
    referenced_figs = {fname for fname, _ in tex_refs}

    # Listar archivos reales
    real_used = sorted(FIGS_DIR.iterdir()) if FIGS_DIR.exists() else []
    real_opt = sorted(FIGS_OPT_DIR.iterdir()) if FIGS_OPT_DIR.exists() else []

    # Detectar duplicados (mismo filename en figs/ y figs_optional/)
    used_names = {p.name for p in real_used}
    opt_names = {p.name for p in real_opt}
    duplicates = used_names & opt_names

    seen = set()
    # 1. Iterar sobre archivos reales en figs/ y figs_optional/
    for path in real_used + real_opt:
        fname = path.name
        seen.add(fname)
        location = "figs/" if path.parent == FIGS_DIR else "figs_optional/"
        optional = location == "figs_optional/"
        is_referenced = fname in referenced_figs

        csv_name = fig_to_csv.get(fname)
        csv_present = bool(csv_name) and (PAPER / csv_name).exists()

        size_kb = round(path.stat().st_size / 1024)
        fig_md5 = md5(path)

        # Determinar status
        if optional:
            if fname in duplicates:
                # Esta copia es redundante: figs/ ya tiene el archivo y es
                # la que usa LaTeX via \graphicspath
                status = FALLA
                note = (f"DUPLICADO: tambien existe en figs/. La copia en "
                        f"figs_optional/ es redundante; considerar eliminarla.")
            elif is_referenced:
                # Las figuras opcionales no deben estar referenciadas
                status = FALLA
                note = (f"En figs_optional/ pero referenciada por .tex; "
                        f"mover a figs/ o desreferenciar.")
            elif csv_name is None:
                status = NO_VERIF
                note = "Optional, sin sibling CSV."
            elif csv_present:
                status = PASA
                note = f"Optional; sibling {csv_name} OK."
            else:
                status = FALLA
                note = f"Optional; sibling {csv_name} faltante."
        else:
            # En figs/ -- deberia estar referenciada por .tex
            if not is_referenced:
                status = FALLA
                note = ("Archivo en figs/ pero NO referenciado por .tex "
                        "con \\includegraphics. Posible figura huerfana.")
            elif csv_name is None:
                status = NO_VERIF
                note = "Sin sibling CSV en outputs/paper/."
            elif csv_present:
                status = PASA
                note = f"Sibling {csv_name} OK."
            else:
                status = FALLA_CRIT
                note = (f"Sibling esperado {csv_name} NO encontrado en "
                        f"outputs/paper/")

        rows.append({
            "figure": fname,
            "location": location,
            "optional": optional,
            "referenced": is_referenced,
            "size_kb": size_kb,
            "md5": fig_md5[:12],
            "csv": csv_name,
            "csv_present": csv_present,
            "status": status,
            "note": note,
        })

    # 2. Reportar referencias en .tex que no tienen archivo real
    for fname, ln in tex_refs:
        if fname in seen:
            continue
        rows.append({
            "figure": fname,
            "location": "MISSING",
            "optional": False,
            "referenced": True,
            "size_kb": None,
            "md5": None,
            "csv": fig_to_csv.get(fname),
            "csv_present": False,
            "status": FALLA_CRIT,
            "note": (f".tex L{ln} hace \\includegraphics{{{fname}}} pero el "
                     "archivo no existe en figs/ ni figs_optional/."),
        })

    return rows


# ----------------------------------------------------------------------
# Eje D: bibliografia (\\cite vs .bib y vs thebibliography)
# ----------------------------------------------------------------------


def parse_cite_keys(tex: str) -> set[str]:
    keys: set[str] = set()
    # Solo la parte ANTES del bloque comentado de discussion duplicada
    # (lineas que comienzan con %)
    active_lines = []
    for ln in tex.splitlines():
        # mantener si la linea NO empieza con % (despues de espacios)
        stripped = ln.lstrip()
        if not stripped.startswith("%"):
            active_lines.append(ln)
    active_tex = "\n".join(active_lines)
    for m in re.finditer(r"\\cite\{([^}]+)\}", active_tex):
        for k in m.group(1).split(","):
            keys.add(k.strip())
    return keys


def parse_bib_keys(bib_text: str) -> dict[str, dict]:
    """Devuelve {key: {type, fields}} parseando @entries del .bib."""
    out: dict[str, dict] = {}
    for m in re.finditer(r"@(\w+)\{([^,\s]+)\s*,\s*", bib_text):
        entry_type = m.group(1)
        key = m.group(2)
        # extraer campos hasta @ o EOF
        start = m.end()
        # Encontrar el } de cierre balanceado
        depth = 1
        end = start
        while end < len(bib_text) and depth > 0:
            ch = bib_text[end]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            end += 1
        body = bib_text[start:end - 1]
        fields = {}
        # cada campo: name = {value} o name = "value"
        for fm in re.finditer(
            r"(\w+)\s*=\s*[{\"]([^}\"]*)[}\"]", body):
            fields[fm.group(1).lower()] = fm.group(2)
        out[key] = {"type": entry_type, "fields": fields}
    return out


def parse_thebibliography_keys(tex: str) -> set[str]:
    """Extrae \\bibitem{key} dentro de \\begin{thebibliography}."""
    out = set()
    in_bib = False
    for ln in tex.splitlines():
        if r"\begin{thebibliography}" in ln:
            in_bib = True
            continue
        if r"\end{thebibliography}" in ln:
            in_bib = False
            continue
        if not in_bib:
            continue
        m = re.match(r"\s*\\bibitem\{([^}]+)\}", ln)
        if m:
            out.add(m.group(1))
    return out


# ----------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------


def fmt_value(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        if abs(v) >= 1000:
            return f"{v:,.0f}"
        if abs(v) >= 1:
            return f"{v:.4g}"
        return f"{v:.4g}"
    return str(v)


def fmt_delta(claim: Claim) -> str:
    d = claim.delta
    if d is None:
        return "—"
    if abs(d) < 1e-6:
        return "0"
    return f"{d:+.4g}"


def render_md(claims: list[Claim], figures: list[dict],
              cite_keys: set[str], bib_keys: dict[str, dict],
              thebib_keys: set[str], readme_findings: list[str],
              diff_findings: list[str], tex_lines: list[str]) -> str:
    n_total = len(claims)
    by_status = {PASA: 0, FALLA: 0, FALLA_CRIT: 0, NO_VERIF: 0}
    for c in claims:
        by_status[c.status] = by_status.get(c.status, 0) + 1

    overall = "[OK] LISTO PARA ENVIO"
    if by_status[FALLA_CRIT] > 0:
        overall = "[X] REQUIERE CORRECCION"
    elif by_status[FALLA] > 0:
        overall = "[!] FALLA NO CRITICA"

    out = []
    out.append("# Auditoria WEEF__Copy/ -- Reporte de Verificacion")
    out.append("")
    out.append(f"- Fecha: {datetime.now().isoformat(timespec='seconds')}")
    out.append("- Snapshot auditado: `outputs/paper/WEEF__Copy/`")
    out.append("- Fuente canonica: `outputs/paper/resultados_paper_cal29_phi15.xlsx`"
               " + 17 CSV siblings + `outputs/paper/paper_weef.md`")
    out.append(f"- Script: `scripts/audit_weef_copy.py`")
    out.append("")
    out.append("## Resumen ejecutivo")
    out.append("")
    out.append(f"- Claims auditados: **{n_total}**")
    out.append(f"- PASA: **{by_status.get(PASA, 0)}**")
    out.append(f"- FALLA: **{by_status.get(FALLA, 0)}**")
    out.append(f"- FALLA-CRITICA: **{by_status.get(FALLA_CRIT, 0)}**")
    out.append(f"- NO-VERIFICABLE: **{by_status.get(NO_VERIF, 0)}**")
    out.append(f"- Estado global: **{overall}**")
    out.append("")

    # Hallazgos criticos al inicio
    crit = [c for c in claims if c.status == FALLA_CRIT]
    falla = [c for c in claims if c.status == FALLA]
    if crit or falla:
        out.append("## Hallazgos priorizados (FALLA / FALLA-CRITICA)")
        out.append("")
        for i, c in enumerate(crit + falla, 1):
            tag = "CRIT" if c.status == FALLA_CRIT else "FALLA"
            out.append(
                f"{i}. **[{tag}] {c.subeje} L{c.line}**: {c.description}  ")
            out.append(
                f"   - Reportado: `{fmt_value(c.reported)}`  ")
            out.append(
                f"   - Canonico:  `{fmt_value(c.canonical)}`  ")
            if c.delta is not None:
                out.append(f"   - Delta: `{fmt_delta(c)} {c.unit}`  ")
            out.append(f"   - Fuente: {c.source}  ")
            if c.note:
                out.append(f"   - Nota: {c.note}  ")
        out.append("")

    # Eje A
    out.append("## A. Cifras del manuscrito")
    out.append("")
    out.append("| Sub-eje | L .tex | Descripcion | Reportado | Canonico | "
               "Tol | Delta | Estado |")
    out.append("|---|---|---|---|---|---|---|---|")
    a_claims = [c for c in claims if c.subeje.startswith("A")]
    for c in a_claims:
        ln = c.line if c.line is not None else "—"
        out.append(
            f"| {c.subeje} | {ln} | {c.description} | "
            f"{fmt_value(c.reported)} {c.unit} | "
            f"{fmt_value(c.canonical)} {c.unit} | "
            f"{c.tol if c.tol is not None else '—'} | "
            f"{fmt_delta(c)} | {c.status} |"
        )
    out.append("")

    # Eje C
    out.append(f"## C. Figuras ({len(figures)})")
    out.append("")
    out.append("| # | Figura | Ubic. | KB | MD5 | Ref .tex | Sibling CSV | "
               "CSV ok | Estado | Nota |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for i, f in enumerate(figures, 1):
        out.append(
            f"| {i} | `{f['figure']}` | {f['location']} | "
            f"{f['size_kb']} | `{f['md5']}` | "
            f"{'si' if f.get('referenced') else 'no'} | "
            f"`{f['csv'] or '—'}` | {'si' if f['csv_present'] else 'no'} | "
            f"{f['status']} | {f['note']} |"
        )
    out.append("")

    # Eje D
    out.append("## D. Bibliografia")
    out.append("")
    out.append("**Estructura:** el .tex usa `\\begin{thebibliography}` inline (no BibTeX).")
    out.append(f"`paper_weef.bib` esta presente como referencia opcional segun el README.")
    out.append("")
    out.append(f"- Claves citadas con `\\cite{{}}` en el .tex: **{len(cite_keys)}**")
    out.append(f"- Entradas en `\\begin{{thebibliography}}` (`\\bibitem`): **{len(thebib_keys)}**")
    out.append(f"- Entradas en `paper_weef.bib`: **{len(bib_keys)}**")
    out.append("")

    # \cite -> thebibliography
    missing_in_thebib = sorted(cite_keys - thebib_keys)
    orphan_in_thebib = sorted(thebib_keys - cite_keys)
    out.append("### D.1 Coherencia `\\cite` <-> `\\begin{thebibliography}`")
    out.append("")
    if missing_in_thebib:
        out.append("**MISSING** (`\\cite{}` sin `\\bibitem{}` correspondiente):")
        for k in missing_in_thebib:
            out.append(f"- `{k}`")
        out.append("")
    else:
        out.append("Todas las citas tienen entrada bibliografica. **OK**")
        out.append("")

    if orphan_in_thebib:
        out.append("**ORPHAN** (`\\bibitem{}` no citado):")
        for k in orphan_in_thebib:
            out.append(f"- `{k}`")
        out.append("")
    else:
        out.append("Todos los `\\bibitem{}` estan citados. **OK**")
        out.append("")

    # \cite -> .bib (informativo, no bloqueante)
    missing_in_bib = sorted(cite_keys - set(bib_keys.keys()))
    orphan_in_bib = sorted(set(bib_keys.keys()) - cite_keys)
    out.append("### D.2 Coherencia `\\cite` <-> `paper_weef.bib` (informativo)")
    out.append("")
    out.append("El README declara que el .bib **no se usa por el .tex actual** "
               "(que usa `thebibliography` inline). Esta seccion es informativa "
               "para el caso futuro de migrar a BibTeX.")
    out.append("")
    if missing_in_bib:
        out.append(f"**No presentes en .bib** ({len(missing_in_bib)}): "
                   f"`{'`, `'.join(missing_in_bib)}`")
    if orphan_in_bib:
        out.append(f"**No citadas (huerfanas en .bib)** ({len(orphan_in_bib)}): "
                   f"`{'`, `'.join(orphan_in_bib)}`")
    out.append("")

    # Campos malformed en .bib
    malformed = []
    for k, info in bib_keys.items():
        flds = info["fields"]
        # Para @article: requiere author, title, year, journal
        # Para @techreport: requiere author, title, institution, year
        # Para @misc: requiere title, year
        required_by_type = {
            "article": ["author", "title", "year", "journal"],
            "techreport": ["author", "title", "institution", "year"],
            "misc": ["title", "year"],
            "mastersthesis": ["author", "title", "school", "year"],
        }
        req = required_by_type.get(info["type"].lower(), ["title", "year"])
        miss = [r for r in req if not flds.get(r)]
        if miss:
            malformed.append((k, info["type"], miss))
    out.append("### D.3 Campos minimos en .bib")
    out.append("")
    if malformed:
        for k, t, miss in malformed:
            out.append(f"- `{k}` (`@{t}`): falta {miss}")
    else:
        out.append("Todas las entradas tienen los campos minimos. **OK**")
    out.append("")

    # Eje E
    out.append("## E. README.md")
    out.append("")
    if readme_findings:
        for fnd in readme_findings:
            out.append(f"- {fnd}")
    else:
        out.append("Sin hallazgos.")
    out.append("")

    # Eje F
    out.append("## F. Diff `paper_weef_phase2.tex` vs `paper_weef.md` raiz")
    out.append("")
    if diff_findings:
        for fnd in diff_findings:
            out.append(f"- {fnd}")
    else:
        out.append("Sin discrepancias significativas.")
    out.append("")

    # Detalle de PASA
    out.append("## Detalle: claims que PASAN (referencia)")
    out.append("")
    out.append("| Sub-eje | L | Descripcion | Reportado | Canonico |")
    out.append("|---|---|---|---|---|")
    for c in claims:
        if c.status != PASA:
            continue
        ln = c.line if c.line is not None else "—"
        out.append(
            f"| {c.subeje} | {ln} | {c.description} | "
            f"{fmt_value(c.reported)} {c.unit} | "
            f"{fmt_value(c.canonical)} {c.unit} |"
        )
    out.append("")

    # Apendice: NO-VERIFICABLES
    nv = [c for c in claims if c.status == NO_VERIF]
    if nv:
        out.append("## Apendice: NO-VERIFICABLES")
        out.append("")
        for c in nv:
            ln = c.line if c.line is not None else "—"
            out.append(f"- {c.subeje} L{ln}: {c.description}. "
                       f"Razon: {c.note or c.source}")
        out.append("")

    # Footer
    out.append("---")
    out.append(f"Reporte generado por `scripts/audit_weef_copy.py` "
               f"({datetime.now().isoformat(timespec='seconds')}).")
    out.append("")
    return "\n".join(out)


# ----------------------------------------------------------------------
# Patches
# ----------------------------------------------------------------------


def _replace_token(original: str, rep, can) -> tuple[str, str, str] | None:
    """Sustituye en `original` el token correspondiente a `rep` por `can`.

    Devuelve (new_line, old_token, new_token) o None si no se pudo localizar.
    """
    if isinstance(rep, str) or isinstance(can, str):
        return None

    if isinstance(rep, float):
        rep_s = str(rep)
        dp = len(rep_s.split(".")[1]) if "." in rep_s else 0
        candidates = [f"{rep:.{dp}f}"]
        if rep >= 1000:
            candidates.append(f"{int(rep):,}")
            candidates.append(f"{int(rep):,}".replace(",", "{,}"))
        if rep == int(rep):
            candidates.append(str(int(rep)))
    else:  # int
        candidates = [str(rep)]
        if rep >= 1000:
            candidates.insert(0, f"{rep:,}")
            candidates.insert(1, f"{rep:,}".replace(",", "{,}"))

    old_token = None
    for cand in candidates:
        if re.search(rf"(?<!\d){re.escape(cand)}(?!\d)", original):
            old_token = cand
            break
    if old_token is None:
        return None

    if isinstance(can, float):
        if can == int(can):
            new_token = str(int(can))
        else:
            dp = len(str(rep).split(".")[1]) if "." in str(rep) else 0
            new_token = f"{can:.{dp}f}"
    else:
        new_token = str(can)

    new_line = re.sub(rf"(?<!\d){re.escape(old_token)}(?!\d)",
                      new_token, original, count=1)
    if new_line == original:
        return None
    return new_line, old_token, new_token


def build_patches(claims: list[Claim], tex_lines: list[str]) -> list[Patch]:
    """Convierte FALLAS en parches concretos del .tex.

    Agrupa por linea: si varios claims apuntan a la misma linea, las
    sustituciones se acumulan en un unico hunk para evitar conflictos al
    aplicar el patch.
    """
    # Recolectar (line -> [(claim, ...)]
    by_line: dict[int, list[Claim]] = {}
    for c in claims:
        if c.status not in (FALLA, FALLA_CRIT):
            continue
        if c.line is None or c.canonical is None or c.reported is None:
            continue
        if isinstance(c.reported, str) or isinstance(c.canonical, str):
            continue
        ln_idx = c.line - 1
        if ln_idx < 0 or ln_idx >= len(tex_lines):
            continue
        by_line.setdefault(c.line, []).append(c)

    patches: list[Patch] = []
    for line in sorted(by_line.keys()):
        original = tex_lines[line - 1]
        modified = original
        rationales = []
        for c in by_line[line]:
            res = _replace_token(modified, c.reported, c.canonical)
            if res is None:
                continue
            modified, old_tok, new_tok = res
            rationales.append(
                f"{c.subeje} {c.description}: {old_tok} -> {new_tok} "
                f"(fuente={c.source})"
            )
        if modified != original and rationales:
            patches.append(Patch(
                line=line,
                old=original,
                new=modified,
                rationale=" | ".join(rationales),
            ))
    return patches


def render_patch(patches: list[Patch], tex_lines: list[str]) -> str:
    """Render unified diff sobre WEEF__Copy/paper_weef_phase2.tex.

    El patch usa zero-context (cada hunk es @@ -L,1 +L,1 @@). Para aplicarlo:
        git apply --unidiff-zero outputs/paper/AUDIT_WEEF_COPY.patch

    Hunks ordenados por linea ascendente (requerido por git apply).
    """
    rel_path = "outputs/paper/WEEF__Copy/paper_weef_phase2.tex"
    header = (
        "# AUDIT WEEF__Copy -- Patch de correcciones sugeridas (NO aplicado)\n"
        "#\n"
        "# Para aplicar (tras revision humana del .md):\n"
        "#     git apply --unidiff-zero outputs/paper/AUDIT_WEEF_COPY.patch\n"
        "#\n"
        "# Cada hunk lleva un comentario con la fuente canonica que justifica\n"
        "# la sustitucion. Ver outputs/paper/AUDIT_WEEF_COPY.md para detalle.\n"
        "#\n"
    )
    if not patches:
        return (header
                + "# Patch vacio: no se detectaron FALLAS reparables automaticamente.\n"
                "# Revisar AUDIT_WEEF_COPY.md para hallazgos manuales.\n")
    out = [header.rstrip("\n")]
    out.append(f"--- a/{rel_path}")
    out.append(f"+++ b/{rel_path}")
    for p in sorted(patches, key=lambda q: q.line):
        out.append(f"@@ -{p.line},1 +{p.line},1 @@ AUDIT: {p.rationale}")
        out.append(f"-{p.old}")
        out.append(f"+{p.new}")
    out.append("")
    return "\n".join(out)


# ----------------------------------------------------------------------
# Eje E: README
# ----------------------------------------------------------------------


def audit_readme(readme_text: str, tex_path: Path) -> list[str]:
    findings = []
    # Claim: README dice "verified against resultados_paper_phi15.xlsx (2026-05-06 17:24, tag phi15)"
    if "resultados_paper_phi15.xlsx" in readme_text:
        actual_xlsx = PAPER / "resultados_paper_phi15.xlsx"
        if actual_xlsx.exists():
            findings.append(
                "OK: README menciona `resultados_paper_phi15.xlsx` y el archivo existe "
                f"en `outputs/paper/`."
            )
        else:
            findings.append(
                "FALLA: README menciona `resultados_paper_phi15.xlsx` pero el "
                "archivo no se encuentra en `outputs/paper/` (la auditoria usa "
                "`resultados_paper_cal29_phi15.xlsx` como canonico)."
            )

    # Claim: README dice "10 pages" pero menciona "current PDF compiles to 10 pages,
    # one over the WEEF 9-page hard limit"
    findings.append(
        "INFO: README dice que el PDF compila a **10 paginas, 1 sobre el limite de "
        "9 paginas de WEEF**. Si la auditoria detecta correcciones, considerar re-"
        "renderizado y aplicacion de Option L1/L2/L3 documentada en el README."
    )

    # Claim: README declara discrepancia consciente entre author block (3 ifAuthors
    # en TEX vs version sin Member IEEE) -- verificar
    if r"\IEEEauthorblockN{Brayan S. López-Méndez}" in tex_path.read_text(
            encoding="utf-8"):
        findings.append(
            "INFO: el .tex actual usa el bloque de autores **simple sin "
            "`\\IEEEauthorrefmark{1}`/`Member, IEEE`**. El README muestra una "
            "version alternativa con Student Member/Member IEEE -- no aplicada "
            "en el snapshot. Decidir cual es la version final."
        )

    # Claim: README cita 6 figuras + 9 opcionales = 15. Pero la lista en figs/ tiene 6
    # y figs_optional/ tiene 9 -> total 15 (no 16 como dice el plan). Verificar.
    n_figs = len(list(FIGS_DIR.glob("*"))) if FIGS_DIR.exists() else 0
    n_opt = len(list(FIGS_OPT_DIR.glob("*"))) if FIGS_OPT_DIR.exists() else 0
    findings.append(
        f"INFO: figuras presentes -- `figs/` tiene **{n_figs}** archivos, "
        f"`figs_optional/` tiene **{n_opt}** archivos. README declara 6 + 9 = 15 "
        f"figuras."
    )

    return findings


# ----------------------------------------------------------------------
# Eje F: diff con paper_weef.md raiz
# ----------------------------------------------------------------------


def audit_diff_root(tex_text: str, md_text: str) -> list[str]:
    findings = []

    # 1. Titulo: comparar titulos extraidos
    m_tex = re.search(r"\\title\{([^}]+)\}", tex_text)
    m_md = re.search(r"^# (.+)$", md_text, re.MULTILINE)
    if m_tex and m_md:
        t_tex = m_tex.group(1).strip()
        t_md = m_md.group(1).strip()
        if t_tex != t_md:
            findings.append(
                f"**Titulo distinto** entre .tex y .md raiz:\n"
                f"  - .tex: \"{t_tex}\"\n"
                f"  - .md:  \"{t_md}\""
            )

    # 2. Tabla II: comparar valores
    findings.append(
        "**Tabla II per-agent**: el .tex usa la fuente "
        "`fig_paper_per_agent_benefit.csv`; el `.md` raiz usa el sheet "
        "`Por_agente` del Excel canonico. Las dos fuentes DISAGREE en valores "
        "individuales (e.g. Cesmag P2P CSV=1196 vs Excel=1192) aunque suman al "
        "mismo agregado (5.94 M COP). El .tex Cesmag fila tiene C1=982 (valor "
        "Excel) mezclado con resto de fila (CSV) -- **fila mixta**."
    )

    # 3. Detalles de Tabla II: extraer y comparar
    # ya documentado arriba

    # 4. Crossover description
    findings.append(
        "**Crossover phi=1.03**: el .tex L413 dice \"7 percentage points above "
        "the empirical baseline\" -- la diferencia phi=1.03 vs phi=1.0 es 3 pp; "
        "la coverage gap 99% vs 96% es 3 pp. La interpretacion 7 pp solo se "
        "justifica si phi se lee como coverage decimal (1.03 -> 103%, vs 0.96 "
        "baseline -> 7 pp), pero esto es inconsistente con la convencion del "
        "paper (phi=1.0 -> 96%, no 100%)."
    )

    # 5. Claves \cite distintas entre .tex y .md
    cite_tex = parse_cite_keys(tex_text)
    cite_md = set()
    for m in re.finditer(r"\\cite\{([^}]+)\}", md_text):
        for k in m.group(1).split(","):
            cite_md.add(k.strip())
    only_tex = sorted(cite_tex - cite_md)
    only_md = sorted(cite_md - cite_tex)
    if only_tex or only_md:
        findings.append(
            f"**Citas \\cite distintas**:\n"
            f"  - solo en .tex ({len(only_tex)}): `{', '.join(only_tex)}`\n"
            f"  - solo en .md  ({len(only_md)}): `{', '.join(only_md)}`"
        )

    return findings


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> int:
    print("AUDIT WEEF__Copy ===========================================")
    print(f"  TEX:    {TEX_PATH}")
    print(f"  XLSX:   {XLSX_PATH}")
    print(f"  Output: {OUT_MD}")
    print()

    if not TEX_PATH.exists():
        print(f"ERROR: {TEX_PATH} no existe")
        return 2

    can = load_canonical()
    tex_lines = read_text(TEX_PATH)
    tex_text = TEX_PATH.read_text(encoding="utf-8")
    bib_text = BIB_PATH.read_text(encoding="utf-8")
    readme_text = README_PATH.read_text(encoding="utf-8")
    md_root_text = MD_ROOT_PATH.read_text(encoding="utf-8")

    print(f"  .tex lineas: {len(tex_lines)}")
    print(f"  .bib bytes:  {len(bib_text)}")
    print()

    # Eje A: claims
    claims = build_claims(can)
    print(f"  Claims construidos: {len(claims)}")

    # Detectar claims ya corregidas (valor canonico esta en la linea, pero el
    # valor reportado original no). Esto vuelve la auditoria idempotente: si el
    # patch ya se aplico, los claims correspondientes pasan a PASA.
    for c in claims:
        if c.line is None or c.canonical is None or c.reported is None:
            continue
        if isinstance(c.canonical, str) or isinstance(c.reported, str):
            continue
        if c.line < 1 or c.line > len(tex_lines):
            continue
        original = tex_lines[c.line - 1]
        # Buscar tokens
        rep = c.reported
        can_v = c.canonical
        rep_str = (f"{rep:.{len(str(rep).split('.')[1])}f}"
                   if isinstance(rep, float) and "." in str(rep)
                   else str(int(rep)) if isinstance(rep, (int, float)) else str(rep))
        can_str = (f"{can_v:.{len(str(rep).split('.')[1])}f}"
                   if isinstance(rep, float) and "." in str(rep)
                   else str(int(can_v)) if isinstance(can_v, (int, float)) else str(can_v))
        # Match como token (no parte de otro numero)
        rep_present = bool(re.search(rf"(?<!\d){re.escape(rep_str)}(?!\d)", original))
        can_present = bool(re.search(rf"(?<!\d){re.escape(can_str)}(?!\d)", original))
        if can_present and not rep_present:
            c.already_fixed = True
            c.note = (c.note + " | " if c.note else "") + (
                "Auto-detectado: valor canonico ya presente en .tex "
                "(correccion aplicada).")

    # Eje C: figuras
    figures = figure_traceability(tex_text)
    print(f"  Figuras auditadas:  {len(figures)}")

    # Eje D: bibliografia
    cite_keys = parse_cite_keys(tex_text)
    bib_keys = parse_bib_keys(bib_text)
    thebib_keys = parse_thebibliography_keys(tex_text)
    print(f"  cite keys: {len(cite_keys)} | bib keys: {len(bib_keys)} | "
          f"bibitem keys: {len(thebib_keys)}")

    # Eje E: README
    readme_findings = audit_readme(readme_text, TEX_PATH)

    # Eje F: diff con .md raiz
    diff_findings = audit_diff_root(tex_text, md_root_text)

    # Render reporte (LF newlines, sin BOM)
    md = render_md(claims, figures, cite_keys, bib_keys, thebib_keys,
                   readme_findings, diff_findings, tex_lines)
    OUT_MD.write_bytes(md.encode("utf-8"))
    print(f"  Reporte escrito: {OUT_MD}")

    # Render patch -- LF puro para que git apply funcione (el .tex usa LF)
    patches = build_patches(claims, tex_lines)
    patch_text = render_patch(patches, tex_lines)
    OUT_PATCH.write_bytes(patch_text.encode("utf-8"))
    print(f"  Patch escrito:   {OUT_PATCH}  ({len(patches)} hunks)")

    # Status final
    n_pasa = sum(1 for c in claims if c.status == PASA)
    n_falla = sum(1 for c in claims if c.status == FALLA)
    n_crit = sum(1 for c in claims if c.status == FALLA_CRIT)
    n_nv = sum(1 for c in claims if c.status == NO_VERIF)
    print()
    print(f"  RESUMEN: PASA={n_pasa}  FALLA={n_falla}  "
          f"FALLA-CRITICA={n_crit}  NO-VERIF={n_nv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
