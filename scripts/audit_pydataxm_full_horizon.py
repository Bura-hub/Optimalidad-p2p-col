"""
audit_pydataxm_full_horizon.py — CAL-17 Auditoria pydataxm vs PB_PROM oficial XM
================================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 2.1

Compara la media aritmetica mensual de la serie horaria del cache pydataxm
contra el Precio de Bolsa Nacional Promedio Mensual (PB_PROM) publicado en
los informes oficiales mensuales de XM.

Origen de la sospecha:
  ADR-0014 documento un gap del 35 % en ene-2026 entre cache y oficial. Esta
  auditoria comprueba ese numero, lo reconcilia con los informes oficiales
  XM (xm.com.co/noticias y sinergox.xm.com.co), y propone politica de
  correccion (si aplica) en la capa data/xm_prices.py.

Salida:
  data/audit_pydataxm_horizon.csv  — tabla mes/cache_mean/oficial/delta
  Consola: resumen ejecutivo + meses fuera de tolerancia configurada.

Uso:
  python scripts/audit_pydataxm_full_horizon.py
  python scripts/audit_pydataxm_full_horizon.py --tolerance 0.10
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.xm_prices import get_pi_bolsa  # noqa: E402

# PB_PROM oficial XM por mes (COP/kWh).
# Fuentes: informes mensuales XM publicados en xm.com.co/noticias/ y
# sheet "Precios" del Excel 03_Informe_Precios_y_Transacciones_MM_YYYY.xlsx
# en sinergox.xm.com.co. Verificados manualmente en CAL-14.
PB_OFFICIAL_PROM_MES = {
    "2025-07": (138.36, "xm.com.co/noticias/8119"),
    "2025-08": (251.50, "xm.com.co/noticias/8184"),
    "2025-09": (292.65, "sinergox.xm.com.co/2025/09/03_Informe_Precios"),
    "2025-10": (176.90, "xm.com.co/noticias/8442"),
    "2025-11": (234.87, "xm.com.co/noticias/8584"),
    "2025-12": (278.83, "sinergox.xm.com.co/2025/12/03_Informe_Precios"),
    "2026-01": (213.00, "xm.com.co/noticias/8759"),
}

T_HORIZONTE = 7272  # abr-2025 a ene-2026 (303 dias) — extendido en Sprint 1.1b
T_START = "2025-04-04"  # alineado con horizonte MTE, ver ADR-0017 post-script


def cargar_cache(apply_ceiling: bool = False) -> pd.Series:
    """Lee el cache horario y devuelve serie indexada por timestamp."""
    pi = get_pi_bolsa(
        T=T_HORIZONTE,
        t_start=T_START,
        use_api=True,
        apply_ceiling=apply_ceiling,
    )
    idx = pd.date_range(T_START, periods=T_HORIZONTE, freq="1h")
    return pd.Series(pi, index=idx, name="pi_bolsa")


def auditar_mensual(serie: pd.Series, tolerance_pct: float = 0.10) -> pd.DataFrame:
    """
    Audita media aritmetica mensual del cache vs PB_PROM oficial.
    Devuelve DataFrame con columnas:
      mes / cache_mean / oficial / delta_abs / delta_pct / fuente / fuera_tolerancia
    """
    rows = []
    for mes_str, (oficial, fuente) in PB_OFFICIAL_PROM_MES.items():
        mask = serie.index.to_period("M") == pd.Period(mes_str, freq="M")
        sub = serie[mask]
        if sub.empty:
            continue
        cache_mean = float(sub.mean())
        delta_abs = cache_mean - oficial
        delta_pct = abs(delta_abs) / oficial
        rows.append({
            "mes": mes_str,
            "n_horas": int(mask.sum()),
            "cache_mean": round(cache_mean, 2),
            "oficial": oficial,
            "delta_abs": round(delta_abs, 2),
            "delta_pct": round(delta_pct * 100, 2),
            "fuera_tolerancia": delta_pct > tolerance_pct,
            "fuente": fuente,
        })
    return pd.DataFrame(rows)


def resumen_ejecutivo(df: pd.DataFrame, tolerance_pct: float) -> None:
    """Imprime resumen formateado a consola."""
    print()
    print("=" * 78)
    print(f"CAL-17 Auditoria pydataxm vs PB_PROM oficial XM")
    print(f"Horizonte: {T_START} a 2026-02-01 ({T_HORIZONTE} h, 10 meses)")
    print(f"Solo se auditan meses con PB_PROM oficial verificado:")
    print(f"  {', '.join(sorted(PB_OFFICIAL_PROM_MES.keys()))}")
    print(f"Meses en cache pero sin oficial verificado (CAL-17b pendiente):")
    print(f"  2025-04, 2025-05, 2025-06")
    print(f"Tolerancia: {tolerance_pct*100:.0f} %")
    print("=" * 78)

    print()
    print(df[["mes", "cache_mean", "oficial", "delta_abs", "delta_pct",
             "fuera_tolerancia"]].to_string(index=False))

    n_ok = (~df["fuera_tolerancia"]).sum()
    n_fuera = df["fuera_tolerancia"].sum()
    print()
    print(f"  Meses dentro de tolerancia: {n_ok}/{len(df)}")
    print(f"  Meses fuera de tolerancia: {n_fuera}/{len(df)}")
    print(f"  Delta_pct max: {df['delta_pct'].max():.2f} %")
    print(f"  Delta_pct min: {df['delta_pct'].min():.2f} %")
    print(f"  Delta_pct medio (signed): "
          f"{(df['cache_mean'].sum()-df['oficial'].sum())/df['oficial'].sum()*100:+.2f} %")

    if n_fuera > 0:
        print()
        print("  Meses fuera de tolerancia:")
        for _, row in df[df["fuera_tolerancia"]].iterrows():
            print(f"    {row['mes']}: cache={row['cache_mean']:.1f}  "
                  f"oficial={row['oficial']:.1f}  delta={row['delta_pct']:+.2f} %  "
                  f"({row['fuente']})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tolerance", type=float, default=0.10,
        help="Tolerancia (fraccion) entre cache_mean y PB_PROM oficial (default 0.10 = 10%%)",
    )
    parser.add_argument(
        "--output", type=str,
        default=str(ROOT / "data" / "audit_pydataxm_horizon.csv"),
        help="Ruta del CSV con resultados detallados",
    )
    parser.add_argument(
        "--apply-ceiling", action="store_true",
        help="Auditar serie con techo PES aplicado (CAL-14, default sin techo)",
    )
    args = parser.parse_args()

    print(f"  [cal-17] Cargando cache (apply_ceiling={args.apply_ceiling})...")
    serie = cargar_cache(apply_ceiling=args.apply_ceiling)
    print(f"  [cal-17] {len(serie)} horas, "
          f"media global={serie.mean():.1f} COP/kWh")

    df = auditar_mensual(serie, tolerance_pct=args.tolerance)
    resumen_ejecutivo(df, args.tolerance)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print()
    print(f"  [cal-17] Reporte guardado en: {out_path}")
    print()
    return 0 if not df["fuera_tolerancia"].any() else 1


if __name__ == "__main__":
    sys.exit(main())
