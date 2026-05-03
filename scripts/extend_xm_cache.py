"""
extend_xm_cache.py — Extender cache pydataxm al horizonte MTE completo
========================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 2.1

CAL-17 Sprint 1.1b: el cache `data/precios_bolsa_xm_api.csv` cubria
jul-2025 a ene-2026 (5160 h). El simulation `--full` usa el horizonte
MTE abr-2025 a dic-2025 (6144 h). Faltan 2112 horas al inicio
(abr-2025 a jul-2025).

Este script:
  1. Lee el cache existente.
  2. Detecta el rango faltante hacia atras.
  3. Descarga via pydataxm los meses faltantes.
  4. Concatena y guarda el cache extendido.
  5. Verifica continuidad horaria (sin gaps).

Uso:
  python scripts/extend_xm_cache.py
  python scripts/extend_xm_cache.py --t-start 2025-04-04 --t-end 2026-02-01
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "precios_bolsa_xm_api.csv"


def cargar_cache_existente() -> pd.DataFrame:
    """Devuelve el cache actual con Fecha como datetime."""
    if not CACHE.exists():
        return pd.DataFrame(columns=["Fecha", "Hora", "Precio_COP_kWh"])
    df = pd.read_csv(CACHE)
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    df["Hora"] = pd.to_numeric(df["Hora"], errors="coerce").fillna(1).astype(int)
    df["Precio_COP_kWh"] = pd.to_numeric(df["Precio_COP_kWh"], errors="coerce")
    return df.dropna(subset=["Fecha", "Precio_COP_kWh"])


def descargar_rango_pydataxm(t_start: str, t_end: str) -> pd.DataFrame:
    """Descarga PrecBolsNaci en bloques de 28 dias y devuelve DataFrame
    Fecha/Hora/Precio_COP_kWh."""
    from pydataxm.pydataxm import ReadDB

    obj = ReadDB()
    dt_start = datetime.strptime(t_start, "%Y-%m-%d")
    dt_end = datetime.strptime(t_end, "%Y-%m-%d")

    rows = []
    current = dt_start
    while current < dt_end:
        block_end = min(current + timedelta(days=28), dt_end)
        s = current.strftime("%Y-%m-%d")
        e = block_end.strftime("%Y-%m-%d")
        print(f"    Bloque {s} a {e}...", end=" ", flush=True)
        try:
            df = obj.request_data("PrecBolsNaci", "Sistema", s, e)
            if df is None or df.empty:
                print("vacio")
                current = block_end
                continue
            for _, r in df.iterrows():
                fecha = pd.to_datetime(r["Date"])
                for h in range(1, 25):
                    val = r.get(f"Values_Hour{h:02d}", np.nan)
                    if pd.notna(val):
                        rows.append({
                            "Fecha": fecha.strftime("%Y-%m-%d"),
                            "Hora": h,
                            "Precio_COP_kWh": round(float(val), 2),
                        })
            print(f"OK ({len(df)} dias)")
        except Exception as exc:
            print(f"ERROR: {exc}")
        current = block_end

    return pd.DataFrame(rows)


def verificar_continuidad(df: pd.DataFrame, t_start: str, t_end: str) -> tuple[int, list]:
    """Verifica que df cubra cada hora desde t_start hasta t_end-1h sin gaps."""
    expected_idx = pd.date_range(t_start, t_end, freq="1h", inclusive="left")
    df_idx = pd.to_datetime(df["Fecha"]) + pd.to_timedelta(df["Hora"] - 1, unit="h")
    actual_set = set(df_idx)
    missing = [t for t in expected_idx if t not in actual_set]
    return len(expected_idx) - len(missing), missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t-start", default="2025-04-04",
                        help="Inicio del horizonte objetivo (YYYY-MM-DD)")
    parser.add_argument("--t-end", default="2026-02-01",
                        help="Fin del horizonte objetivo, exclusivo (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true",
                        help="No guardar cambios; solo reportar.")
    args = parser.parse_args()

    print(f"  [extend-xm] Horizonte objetivo: {args.t_start} a {args.t_end}")
    cache = cargar_cache_existente()
    if cache.empty:
        print("  [extend-xm] Cache vacio, descargando todo el rango.")
        existing_min, existing_max = None, None
    else:
        existing_min = cache["Fecha"].min().strftime("%Y-%m-%d")
        existing_max = (cache["Fecha"].max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        print(f"  [extend-xm] Cache existente: {existing_min} a {existing_max} "
              f"({len(cache)} filas)")

    # Identificar segmentos faltantes
    target_start = pd.Timestamp(args.t_start)
    target_end = pd.Timestamp(args.t_end)

    fragmentos_descarga = []
    if cache.empty:
        fragmentos_descarga.append((args.t_start, args.t_end))
    else:
        cache_min = cache["Fecha"].min()
        cache_max_excl = cache["Fecha"].max() + pd.Timedelta(days=1)
        if target_start < cache_min:
            fragmentos_descarga.append(
                (args.t_start, cache_min.strftime("%Y-%m-%d")))
        if target_end > cache_max_excl:
            fragmentos_descarga.append(
                (cache_max_excl.strftime("%Y-%m-%d"), args.t_end))

    if not fragmentos_descarga:
        print("  [extend-xm] Cache ya cubre el horizonte; nada que descargar.")
    else:
        print(f"  [extend-xm] Fragmentos a descargar: {fragmentos_descarga}")

    nuevas_filas = pd.DataFrame()
    for s, e in fragmentos_descarga:
        print(f"  [extend-xm] Descargando {s} a {e}...")
        chunk = descargar_rango_pydataxm(s, e)
        nuevas_filas = pd.concat([nuevas_filas, chunk], ignore_index=True)

    if not nuevas_filas.empty:
        nuevas_filas["Fecha"] = pd.to_datetime(nuevas_filas["Fecha"])
        if not cache.empty:
            combined = pd.concat([cache, nuevas_filas], ignore_index=True)
        else:
            combined = nuevas_filas
        combined = combined.drop_duplicates(subset=["Fecha", "Hora"]).sort_values(
            ["Fecha", "Hora"]).reset_index(drop=True)
    else:
        combined = cache.copy()

    n_horas, missing = verificar_continuidad(combined, args.t_start, args.t_end)
    expected = int((target_end - target_start).total_seconds() / 3600)
    print(f"  [extend-xm] Continuidad: {n_horas}/{expected} horas presentes")
    if missing:
        print(f"  [extend-xm] AVISO: {len(missing)} horas faltantes")
        if len(missing) <= 10:
            for m in missing:
                print(f"    {m}")

    if args.dry_run:
        print("  [extend-xm] DRY-RUN: no se sobrescribe el cache.")
        return 0

    # Guardar (formato Long: Fecha como YYYY-MM-DD, Hora 1..24)
    out = combined.copy()
    out["Fecha"] = pd.to_datetime(out["Fecha"]).dt.strftime("%Y-%m-%d")
    out.to_csv(CACHE, index=False, encoding="utf-8-sig")
    print(f"  [extend-xm] Cache guardado: {CACHE}  ({len(out)} filas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
