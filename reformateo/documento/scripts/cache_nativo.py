"""
cache_nativo.py — Ventanas del dato a su resolución nativa de dos minutos.
==========================================================================
Casi todo el documento se dibuja a paso horario, que es al que negocia el
modelo. Tres figuras necesitan lo contrario: enseñar qué hay **dentro** de
una hora, porque lo que discuten es precisamente si la media horaria está
escondiendo algo.

El caché es minúsculo a propósito. No guarda el crudo entero, que son
1,7 GB y veintisiete equipos, sino las cuatro ventanas que esas figuras
dibujan, con las cuatro columnas que usan. Así el generador de figuras
corre en segundos y sin la carpeta de mediciones delante.

    python scripts/cache_nativo.py

Salida
------
``datos_cache/nativo.parquet`` con una fila por muestra y las columnas
``ventana``, ``instante``, ``P`` (lectura del medidor), ``G`` (inversor),
``D`` (demanda reconstruida, que es lo que el filtro juzga) y las tres
tensiones de fase.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import datos as D  # noqa: E402

MTE = D.RAIZ / "MedicionesMTE_v3"
DESTINO = D.CACHE / "nativo.parquet"

COLUMNAS = ["date", "totalActivePower",
            "voltagePhaseA", "voltagePhaseB", "voltagePhaseC"]
COL_INVERSOR = ["date", "acPower"]

# Las cuatro ventanas, con el porqué de cada una al lado.
VENTANAS = {
    # El caso más débil de las once horas que el umbral retira: solo 13 de
    # las 30 muestras superan el umbral por sí solas. Si ni siquiera este
    # parece una espiga, ninguno lo parece.
    "umbral_mariana": ("Mariana", "Medidor 1 - Alvernia - electricMeter",
                       "2025-04-24 07:00", "2025-04-24 11:00"),
    # El caso más fuerte: 29 de 30 muestras sobre el umbral, es decir, una
    # racha de 58 minutos seguidos.
    "umbral_cesmag": ("Cesmag", "Medidor 3 - Cesmag - electricMeter",
                      "2025-05-09 07:00", "2025-05-09 11:00"),
    # El hundimiento de tensión que el criterio distribucional no podía ver,
    # porque durante el fallo el medidor informa una potencia diminuta.
    "fallo_mariana": ("Mariana", "Medidor 1 - Alvernia - electricMeter",
                      "2025-08-28 18:00", "2025-08-29 15:00"),
    # El mismo suceso en un segundo medidor del edificio, que conserva la
    # tensión y pierde el sincronismo de frecuencia.
    "fallo_mariana_2": ("Mariana", "Medidor 2 - Alvernia - electricMeter",
                        "2025-08-28 18:00", "2025-08-29 15:00"),
}


# Lo que el umbral juzga NO es la lectura del medidor sino la demanda ya
# reconstruida, y en las instituciones de medidor neto parcial esas dos cosas
# difieren justo a las horas de sol. Para que la figura y el umbral miren el
# mismo objeto hay que sumar el inversor a su propia resolucion.
INVERSORES = {
    "umbral_mariana": ("Mariana", "Fronius - Alvernia - inverter"),
    "fallo_mariana": ("Mariana", "Fronius - Alvernia - inverter"),
}
# Como reconstruye el pipeline la demanda de cada institucion, para no
# reimplementarlo de memoria: `neto_parcial` suma el inversor y recorta en
# cero; `bruto` solo recorta.
TIPO = {"umbral_mariana": "neto_parcial", "umbral_cesmag": "bruto",
        "fallo_mariana": "neto_parcial", "fallo_mariana_2": "bruto"}


def _carpeta_medidor(institucion: str) -> Path:
    """La carpeta de medidores de una institución.

    En el árbol de CESMAG el nombre viene mal escrito desde el origen, de
    modo que se aceptan las dos grafías en vez de corregir los datos.
    """
    raiz = MTE / institucion
    for nombre in ("electricMeter", "eletricMeter"):
        if (raiz / nombre).is_dir():
            return raiz / nombre
    raise FileNotFoundError(f"sin carpeta de medidores en {raiz}")


def _leer_inversor(institucion: str, subcarpeta: str,
                   t0: str, t1: str) -> pd.Series:
    """La generacion del inversor en la ventana, en kW y a paso nativo."""
    carpeta = MTE / institucion / "inverter" / subcarpeta
    partes = []
    for p in sorted(carpeta.glob("*.csv")):
        df = pd.read_csv(p, low_memory=False, on_bad_lines="skip",
                         usecols=lambda c: c in COL_INVERSOR)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["acPower"] = pd.to_numeric(df["acPower"], errors="coerce")
        partes.append(df)
    df = pd.concat(partes, ignore_index=True)
    df = df[(df["date"] >= t0) & (df["date"] < t1)]
    s = df.groupby("date", sort=True)["acPower"].mean() / 1000.0
    return s.clip(lower=0)          # la potencia inyectada no es negativa


def _leer(path: Path) -> pd.DataFrame:
    for codigo in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            path.read_bytes().decode(codigo)
            break
        except Exception:  # noqa: BLE001
            codigo = "latin-1"
    df = pd.read_csv(path, encoding=codigo, low_memory=False,
                     on_bad_lines="skip",
                     usecols=lambda c: c in COLUMNAS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    for c in df.columns:
        if c != "date":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def construir() -> pd.DataFrame:
    filas = []
    for etiqueta, (inst, medidor, t0, t1) in VENTANAS.items():
        carpeta = _carpeta_medidor(inst) / medidor
        if not carpeta.is_dir():
            raise FileNotFoundError(f"sin subcarpeta {carpeta}")
        partes = [_leer(p) for p in sorted(carpeta.glob("*.csv"))]
        df = pd.concat(partes, ignore_index=True)
        df = df[(df["date"] >= t0) & (df["date"] < t1)]
        # P-17: los tramos se solapan en un instante y el pipeline los funde
        # promediando. La ventana nativa hace lo mismo para no discrepar.
        df = df.groupby("date", sort=True).mean()
        g = pd.Series(0.0, index=df.index)
        if etiqueta in INVERSORES:
            inv_inst, inv_sub = INVERSORES[etiqueta]
            g = _leer_inversor(inv_inst, inv_sub, t0, t1).reindex(
                df.index).interpolate(limit=2).fillna(0.0)
        # La demanda tal como la ve el filtro, con la misma cuenta que el
        # pipeline hace a paso horario.
        if TIPO[etiqueta] == "neto_parcial":
            d_recon = (df["totalActivePower"].fillna(0.0) + g).clip(lower=0)
        else:
            d_recon = df["totalActivePower"].clip(lower=0)

        sub = pd.DataFrame({
            "ventana": etiqueta,
            "instante": df.index,
            "P": df["totalActivePower"].values,
            "G": g.values,
            "D": d_recon.values,
            "VA": df["voltagePhaseA"].values,
            "VB": df["voltagePhaseB"].values,
            "VC": df["voltagePhaseC"].values,
        })
        filas.append(sub)
        print(f"  {etiqueta:18s} {inst:8s} {len(sub):5d} muestras  "
              f"{df.index.min()} .. {df.index.max()}"
              + ("  (+ inversor)" if etiqueta in INVERSORES else ""))
    return pd.concat(filas, ignore_index=True)


def cargar() -> pd.DataFrame:
    """Devuelve el caché, y lo construye si no existe."""
    if not DESTINO.exists():
        raise FileNotFoundError(
            f"falta {DESTINO}; corra primero  python scripts/cache_nativo.py")
    return pd.read_parquet(DESTINO)


def ventana(etiqueta: str) -> pd.DataFrame:
    d = cargar()
    return (d[d.ventana == etiqueta]
            .set_index("instante").drop(columns="ventana").sort_index())


if __name__ == "__main__":
    if not MTE.exists():
        raise SystemExit(f"no encuentro {MTE}")
    print("\nVentanas nativas de dos minutos")
    d = construir()
    D.CACHE.mkdir(parents=True, exist_ok=True)
    d.to_parquet(DESTINO, index=False)
    print(f"\n  [cache] {DESTINO.name}  ({len(d)} muestras, "
          f"{DESTINO.stat().st_size / 1024:.0f} kB)")
