"""
diagnostico_datos.py
--------------------
Corre este script ANTES de main_simulation.py para diagnosticar
exactamente qué ve el cargador en los CSV reales.

Uso:
    python diagnostico_datos.py
    python diagnostico_datos.py --root "C:/ruta/a/MedicionesMTE"
"""

import sys, os, argparse
from pathlib import Path
import pandas as pd
import numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "MedicionesMTE"))
    args = ap.parse_args()
    root = Path(args.root)

    print(f"\n{'='*65}")
    print(f"  DIAGNÓSTICO DE DATOS MTE")
    print(f"  Raíz: {root}")
    print(f"{'='*65}\n")

    if not root.exists():
        print(f"  ERROR: La carpeta no existe: {root}")
        sys.exit(1)

    # ── Listar estructura ──────────────────────────────────────────────
    print("Estructura encontrada:")
    for item in sorted(root.iterdir()):
        if item.is_dir():
            print(f"  /{item.name}/")
            for sub in sorted(item.iterdir()):
                if sub.is_dir():
                    csvs = list(sub.rglob("*.csv"))
                    print(f"    /{sub.name}/  ({len(csvs)} CSV)")

    print()

    # ── Inspeccionar un CSV de cada tipo ──────────────────────────────
    tipos = {
        "electricMeter":  ("electricMeter", "eletricMeter", "Medidor"),
        "inverter":       ("inverter", "Inverter", "Inverters", "inversor", "Inversor"),
        "weatherStation": ("weatherstation", "weatherStation"),
    }

    muestras_revisadas = set()

    for inst in sorted(root.iterdir()):
        if not inst.is_dir():
            continue
        print(f"\n{'─'*55}")
        print(f"  INSTITUCIÓN: {inst.name}")
        print(f"{'─'*55}")

        for tipo_label, keywords in tipos.items():
            # Buscar carpeta que coincida
            carpeta = None
            for sub in inst.iterdir():
                if sub.is_dir() and any(k.lower() in sub.name.lower() for k in keywords):
                    carpeta = sub
                    break

            if carpeta is None:
                print(f"  [{tipo_label}] NO ENCONTRADA")
                continue

            csvs = list(carpeta.rglob("*.csv"))
            print(f"\n  [{tipo_label}] → {carpeta.name}/ ({len(csvs)} archivos)")

            if not csvs:
                print("    Sin CSV")
                continue

            # Leer el primero que no hayamos visto
            csv_path = csvs[0]
            key = str(csv_path)
            if key in muestras_revisadas:
                csv_path = csvs[-1] if len(csvs) > 1 else csvs[0]
            muestras_revisadas.add(str(csv_path))

            print(f"    Archivo: {csv_path.name}")

            try:
                # Detectar separador y encoding
                raw = csv_path.read_bytes()
                encoding = "utf-8"
                for enc in ["utf-8", "latin-1", "cp1252", "utf-8-sig"]:
                    try:
                        raw.decode(enc)
                        encoding = enc
                        break
                    except Exception:
                        pass

                # Leer con pandas
                df = pd.read_csv(csv_path, encoding=encoding,
                                 nrows=5, low_memory=False)

                print(f"    Filas muestra: {len(df)}  Columnas: {len(df.columns)}")
                print(f"    Columnas ({len(df.columns)}):")
                for col in df.columns[:10]:
                    val = df[col].iloc[0] if len(df) > 0 else "?"
                    print(f"      '{col}' → {repr(val)}")
                if len(df.columns) > 10:
                    print(f"      ... (+{len(df.columns)-10} más)")

                # Buscar columna de fecha
                date_cols = [c for c in df.columns
                             if "date" in c.lower() or "time" in c.lower()
                             or "fecha" in c.lower()]
                if date_cols:
                    print(f"    Columna fecha detectada: {date_cols}")
                    sample_date = df[date_cols[0]].iloc[0]
                    print(f"    Ejemplo fecha: {repr(sample_date)}")

                # Buscar columna de potencia
                power_cols = [c for c in df.columns
                              if any(k in c.lower() for k in
                                     ["power", "potencia", "acpower", "active",
                                      "watt", "kw", "energia"])]
                if power_cols:
                    print(f"    Columnas de potencia detectadas: {power_cols}")
                    for pc in power_cols[:3]:
                        val = df[pc].iloc[0] if len(df) > 0 else "?"
                        print(f"      {pc} → {repr(val)}")

                # Leer TODO el archivo y ver rango temporal
                df_full = pd.read_csv(csv_path, encoding=encoding,
                                      low_memory=False)
                print(f"    Filas totales: {len(df_full)}")
                if date_cols:
                    dates = pd.to_datetime(df_full[date_cols[0]], errors="coerce")
                    valid = dates.dropna()
                    if len(valid):
                        print(f"    Rango fechas: {valid.min()} → {valid.max()}")
                    else:
                        print(f"    No se pudo parsear fecha")

            except Exception as e:
                print(f"    ERROR leyendo: {e}")

    print(f"\n{'='*65}")
    print("  FIN DEL DIAGNÓSTICO")
    print("  Comparte esta salida para corregir el cargador.")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
