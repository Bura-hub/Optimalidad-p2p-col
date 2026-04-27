"""
matlab_export.py
----------------
Helper centralizado para exportar los datos numéricos de cada figura a archivos
CSV y .mat siblings del PNG generado, de modo que las gráficas sean reproducibles
en MATLAB sin re-ejecutar la simulación.

Convenciones
~~~~~~~~~~~~
- Los archivos se nombran como el PNG pero con extensión `.csv` y `.mat`.
- Los CSV se escriben en UTF-8-BOM con headers en español.
- Los .mat usan scipy.io.savemat formato v5; las claves no-ASCII se sanitizan.
- Los timestamps se exportan en hora local America/Bogota.
- NaN se preservan en CSV ('nan' literal) y en .mat (np.nan).

Tipos de figura soportados
~~~~~~~~~~~~~~~~~~~~~~~~~~
- Series 1D (todas del mismo largo): un único CSV con N columnas.
- Series 1D heterogéneas: CSV por serie con sufijo, todas en un único .mat.
- Matriz 2D (heatmap): CSV en formato matriz + .mat con array nativo.
- DataFrame: se exporta tal cual con `to_csv(..., index=True)`.

Actividad de propuesta: complementa entregables 1.1, 2.1, 3.3, 4.1, 4.2.

Uso
~~~
    from visualization.matlab_export import export_figure_data
    export_figure_data(
        fig_id="fig07",
        data={"pgb": pgb_arr, "ganancia_p2p": gp_arr, "ganancia_c4": gc_arr},
        fig_path="graficas/fig7_sensibilidad_pgb.png",
        metadata={"activity_ref": "Act 4.1", "units": "COP/kWh, COP"},
    )
"""

from __future__ import annotations

import os
import re
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Tuple

import numpy as np
import pandas as pd
import scipy.io as sio


_TZ = "America/Bogota"


def _sanitize_key(key: str) -> str:
    """Sanitiza una clave para que sea aceptable como nombre de variable MATLAB."""
    s = re.sub(r"[^A-Za-z0-9_]", "_", str(key))
    if not s or not s[0].isalpha():
        s = "v_" + s
    return s[:31]  # MATLAB limita nombres a 63 chars; uso 31 por seguridad


def _to_serializable(arr: Any) -> Any:
    """Convierte un objeto a algo que numpy/scipy pueda serializar."""
    if arr is None:
        return np.array([])
    if isinstance(arr, (list, tuple)):
        return np.asarray(arr)
    if isinstance(arr, pd.DatetimeIndex):
        try:
            arr = arr.tz_convert(_TZ) if arr.tz is not None else arr.tz_localize(_TZ)
        except Exception:
            pass
        return np.array([str(x) for x in arr])
    if isinstance(arr, pd.Series):
        return arr.to_numpy()
    if isinstance(arr, pd.DataFrame):
        return arr  # se maneja por separado
    if isinstance(arr, np.ndarray):
        return arr
    if np.isscalar(arr):
        return np.asarray(arr)
    return np.asarray(arr)


def _bogota_timestamp() -> str:
    """Timestamp ISO en hora local Bogotá."""
    try:
        return pd.Timestamp.now(tz=_TZ).isoformat()
    except Exception:
        return datetime.now().isoformat()


def _build_csv_dataframe(data: Mapping[str, Any]) -> pd.DataFrame | None:
    """
    Construye un DataFrame plano si todas las series son 1D y comparten longitud.
    Retorna None si la heterogeneidad de shapes obliga a CSVs separados.
    """
    series = {}
    common_len = None
    for k, v in data.items():
        v_arr = _to_serializable(v)
        if isinstance(v_arr, pd.DataFrame):
            return None
        v_arr = np.asarray(v_arr)
        if v_arr.ndim > 1:
            return None
        if v_arr.ndim == 0:
            v_arr = v_arr.reshape(1)
        if common_len is None:
            common_len = len(v_arr)
        elif len(v_arr) != common_len:
            return None
        series[k] = v_arr
    if not series:
        return None
    return pd.DataFrame(series)


def _write_csv_per_series(data: Mapping[str, Any], base_path: Path) -> list[Path]:
    """Escribe un CSV por serie cuando los shapes son heterogéneos."""
    out_paths: list[Path] = []
    for k, v in data.items():
        path = base_path.with_name(f"{base_path.stem}__{_sanitize_key(k)}.csv")
        v_arr = _to_serializable(v)
        if isinstance(v_arr, pd.DataFrame):
            v_arr.to_csv(path, index=True, encoding="utf-8-sig")
        else:
            v_arr = np.asarray(v_arr)
            if v_arr.ndim <= 1:
                pd.DataFrame({k: v_arr}).to_csv(path, index=False, encoding="utf-8-sig")
            else:
                pd.DataFrame(v_arr).to_csv(path, index=False, header=False, encoding="utf-8-sig")
        out_paths.append(path)
    return out_paths


def _build_mat_dict(data: Mapping[str, Any], metadata: dict | None) -> dict:
    """Construye el dict que recibe scipy.io.savemat."""
    mat: dict = {}
    for k, v in data.items():
        key = _sanitize_key(k)
        v_arr = _to_serializable(v)
        if isinstance(v_arr, pd.DataFrame):
            mat[key] = {
                "values":  v_arr.to_numpy(),
                "columns": np.array(list(v_arr.columns), dtype=object),
                "index":   np.array([str(x) for x in v_arr.index], dtype=object),
            }
        else:
            mat[key] = np.asarray(v_arr)

    meta = {
        "fig_id":            metadata.get("fig_id", "") if metadata else "",
        "timestamp_bogota":  _bogota_timestamp(),
        "units":             metadata.get("units", "") if metadata else "",
        "activity_ref":      metadata.get("activity_ref", "") if metadata else "",
        "description":       metadata.get("description", "") if metadata else "",
    }
    mat["metadata"] = meta
    return mat


def export_figure_data(
    fig_id: str,
    data: Mapping[str, Any],
    fig_path: str | Path,
    metadata: dict | None = None,
) -> Tuple[Path, Path]:
    """
    Escribe `<fig_path>.csv` y `<fig_path>.mat` con los datos numéricos de una figura.

    Parámetros
    ----------
    fig_id : str
        Identificador corto de la figura ("fig07"). Se usa en metadatos.
    data : dict
        Mapping clave→array/serie/DataFrame. Las claves son los nombres de columna
        en el CSV y los nombres de variable en el .mat.
    fig_path : str | Path
        Ruta absoluta o relativa del PNG. Los archivos sibling se escriben con la
        misma ruta cambiando la extensión.
    metadata : dict, opcional
        Llaves comunes: 'units', 'activity_ref' (e.g. 'Act 4.1'), 'description'.

    Retorna
    -------
    (csv_path, mat_path) : tuple[Path, Path]
        Si el CSV principal no se pudo construir como tabla plana, el primer
        elemento apunta al primer archivo CSV escrito por serie.
    """
    fig_path = Path(fig_path)
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    if not data:
        warnings.warn(f"export_figure_data({fig_id}): data dict vacío; nada que exportar.")
        return fig_path.with_suffix(".csv"), fig_path.with_suffix(".mat")

    csv_path = fig_path.with_suffix(".csv")
    mat_path = fig_path.with_suffix(".mat")

    df_flat = _build_csv_dataframe(data)
    if df_flat is not None:
        df_flat.to_csv(csv_path, index=False, encoding="utf-8-sig")
        primary_csv = csv_path
    else:
        per_series = _write_csv_per_series(data, csv_path)
        primary_csv = per_series[0] if per_series else csv_path

    meta_full = dict(metadata or {})
    meta_full.setdefault("fig_id", fig_id)
    mat_dict = _build_mat_dict(data, meta_full)
    sio.savemat(str(mat_path), mat_dict, do_compression=True, format="5")

    return primary_csv, mat_path


def safe_export(
    fig_id: str,
    data: Mapping[str, Any],
    fig_path: str | Path,
    metadata: dict | None = None,
) -> Tuple[Path | None, Path | None]:
    """
    Wrapper que captura excepciones para que un fallo de exportación nunca rompa
    la generación de figuras.
    """
    try:
        return export_figure_data(fig_id, data, fig_path, metadata)
    except Exception as exc:  # noqa: BLE001
        warnings.warn(f"export_figure_data({fig_id}) falló: {exc}")
        return None, None
