"""
audit_xm_yearly_means.py
========================
Script ad-hoc para CAL-11 (auditoría C2 / PPA bilateral).

Descarga el precio de bolsa XM (mismo endpoint que data/xm_prices.py
usa en producción, pydataxm.ReadDB) para los años 2019, 2021, 2023 y
2024 y reporta media, mediana, p25, p75, min y max.

Salida:
  - stdout: tabla resumen
  - data/precios_bolsa_xm_audit_<YEAR>.csv: serie horaria por año

Uso:
  (.venv) python scripts/audit_xm_yearly_means.py [years...]
  (.venv) python scripts/audit_xm_yearly_means.py 2019 2021 2023 2024

(El script funciona en consola Windows cp1252.)

Si pydataxm no está disponible o la API falla para un año, la entrada
se reporta como "N/A" y el script continúa con los siguientes años.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.xm_prices import download_via_api  # noqa: E402


def stats_for_year(year: int):
    t_start = f"{year}-01-01"
    t_end   = f"{year + 1}-01-01"
    save_path = ROOT / "data" / f"precios_bolsa_xm_audit_{year}.csv"
    print(f"\n[{year}] {t_start} -> {t_end}", flush=True)
    prices = download_via_api(t_start=t_start, t_end=t_end,
                              save_path=str(save_path))
    if prices is None:
        print(f"  [{year}] FALLO: sin datos.")
        return None

    arr = np.asarray(prices, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        print(f"  [{year}] FALLO: array vacío.")
        return None

    return {
        "year":   year,
        "n":      int(arr.size),
        "mean":   float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p25":    float(np.percentile(arr, 25)),
        "p75":    float(np.percentile(arr, 75)),
        "p90":    float(np.percentile(arr, 90)),
        "min":    float(np.min(arr)),
        "max":    float(np.max(arr)),
    }


def main():
    years = [int(a) for a in sys.argv[1:]] or [2019, 2021, 2023, 2024]
    rows = []
    for y in years:
        s = stats_for_year(y)
        if s is not None:
            rows.append(s)

    if not rows:
        print("\nNINGUN AÑO RESULTÓ. Revisa pydataxm / red.")
        sys.exit(1)

    df = pd.DataFrame(rows).set_index("year")
    print("\n" + "=" * 78)
    print("Resumen — Precio de bolsa XM (COP/kWh, horario ponderado uniforme)")
    print("=" * 78)
    with pd.option_context("display.float_format", "{:>9.2f}".format):
        print(df[["n", "mean", "median", "p25", "p75", "p90", "min", "max"]])

    out_csv = ROOT / "data" / "audit_xm_yearly_summary.csv"
    df.to_csv(out_csv)
    print(f"\nResumen escrito en {out_csv}")


if __name__ == "__main__":
    main()
