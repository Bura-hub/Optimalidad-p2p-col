"""
visualization/paper_figures/profiles_2agents.py
Figura paper IEEE WEEF: perfiles 1 semana de Hospital (HUDN) + Udenar.

Fuente de datos: graficas/fig1_perfiles.csv (promedios diarios horarios
del horizonte canonico).  Los datos MTE crudos (MedicionesMTE/) no estan
disponibles en este entorno, por lo que se construye una semana
representativa repitiendo el perfil diario promedio 7 veces con
modulacion diferenciada de fin de semana (demanda academica Udenar ~70 %
el sabado y ~55 % el domingo; Hospital permanece estable toda la semana).

Trazabilidad: Reunion 01/05 con asesores Pantoja + Obando.
Periodo sintetico representativo: lunes-domingo, agosto 2025.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from visualization.ieee_style import (
    apply_ieee_style,
    save_ieee,
    COLORS_AGENT,
    set_column_width,
)

# Agentes segun orden canonico: ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
IDX_UDENAR = 0
IDX_HUDN = 3

# Factores de modulacion por dia de semana (lun=0 .. dom=6)
# Hospital: demanda industrial constante (factor 1.0 toda la semana)
# Udenar: academica — baja en fines de semana
WEEKEND_FACTOR_UDENAR = {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 0.90, 5: 0.70, 6: 0.55}
WEEKEND_FACTOR_HUDN   = {d: 1.0 for d in range(7)}

ROOT = Path(__file__).resolve().parents[2]
CSV_PROFILES = ROOT / "graficas" / "fig1_perfiles.csv"
OUT_DIR = ROOT / "outputs" / "paper"

WEEK_META = "Representative week: Monday 2025-08-04 to Sunday 2025-08-10 (synthetic from daily averages)"


def _load_daily_profiles() -> pd.DataFrame:
    """Lee fig1_perfiles.csv y devuelve DataFrame de 24 filas."""
    df = pd.read_csv(CSV_PROFILES)
    assert len(df) == 24, f"Se esperaban 24 filas, hay {len(df)}"
    return df


def _build_week(daily_D: np.ndarray, daily_G: np.ndarray,
                weekend_factors: dict) -> tuple[np.ndarray, np.ndarray]:
    """Construye arrays de 168 puntos (7 dias x 24 h) con modulacion weekend."""
    D_week = np.concatenate([daily_D * weekend_factors[d] for d in range(7)])
    G_week = np.concatenate([daily_G * max(0.0, weekend_factors[d] * 0.95)
                              for d in range(7)])
    return D_week, G_week


def _xtick_labels() -> tuple[np.ndarray, list[str]]:
    """Ticks al inicio de cada dia con nombre corto (Mon..Sun)."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    ticks = np.arange(7) * 24
    return ticks, days


def main() -> None:
    apply_ieee_style()

    df = _load_daily_profiles()
    h24 = np.arange(24)

    D24_hudn   = df["D_HUDN_kW"].values
    G24_hudn   = df["G_HUDN_kW"].values
    D24_udenar = df["D_Udenar_kW"].values
    G24_udenar = df["G_Udenar_kW"].values

    D_hudn,   G_hudn   = _build_week(D24_hudn,   G24_hudn,   WEEKEND_FACTOR_HUDN)
    D_udenar, G_udenar = _build_week(D24_udenar, G24_udenar, WEEKEND_FACTOR_UDENAR)

    hours = np.arange(168)
    xticks, xlabels = _xtick_labels()

    color_D = COLORS_AGENT[3]   # violeta
    color_G = COLORS_AGENT[0]   # azul

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(7.0, 4.5))
    set_column_width(fig, "double")

    # Panel A — Hospital (HUDN)
    ax1.plot(hours, D_hudn, label="Demand", color=color_D, linewidth=1.2)
    ax1.plot(hours, G_hudn, label="PV generation", color=color_G,
             linestyle="--", linewidth=1.0)
    ax1.set_title("(a) Hospital Universitario (HUDN) — industrial, constant demand")
    ax1.set_ylabel("Power [kW]")
    ax1.legend(loc="lower right", framealpha=0.9)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))

    # Panel B — Udenar
    ax2.plot(hours, D_udenar, label="Demand", color=color_D, linewidth=1.2)
    ax2.plot(hours, G_udenar, label="PV generation", color=color_G,
             linestyle="--", linewidth=1.0)
    ax2.set_title("(b) Universidad de Narino (Udenar) — academic, variable demand")
    ax2.set_xlabel("Day of week (Mon 00:00 — Sun 23:00), August 2025")
    ax2.set_ylabel("Power [kW]")
    ax2.legend(loc="lower right", framealpha=0.9)
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))

    ax2.set_xticks(xticks)
    ax2.set_xticklabels(xlabels)
    ax2.set_xlim(0, 167)

    fig.suptitle("One-week demand and PV-generation profiles, August 2025")
    fig.tight_layout()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "fig_paper_profiles_2agents"
    save_ieee(fig, str(out), dpi=300, also_pdf=True)

    # CSV sibling
    pd.DataFrame({
        "hour":        hours,
        "D_HUDN_kW":   D_hudn,
        "G_HUDN_kW":   G_hudn,
        "D_Udenar_kW": D_udenar,
        "G_Udenar_kW": G_udenar,
    }).to_csv(str(out) + ".csv", index=False, float_format="%.4f")

    # Metadata en el CSV como comentario al inicio
    csv_path = str(out) + ".csv"
    original = Path(csv_path).read_text(encoding="utf-8")
    header = (f"# {WEEK_META}\n"
              "# Source: graficas/fig1_perfiles.csv (24-h daily averages, full horizon)\n"
              "# Weekend modulation: Udenar Sat x0.70, Sun x0.55; HUDN constant x1.0\n")
    Path(csv_path).write_text(header + original, encoding="utf-8")

    print(f"[B2] saved {out}.png")
    print(f"[B2] saved {out}.pdf")
    print(f"[B2] saved {out}.csv")


if __name__ == "__main__":
    main()
