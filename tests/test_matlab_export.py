"""
Tests del helper visualization/matlab_export.py.

Verifica que cada figura genera un CSV y un .mat sibling reproducibles.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.io as sio
import pytest

from visualization.matlab_export import export_figure_data, safe_export


def test_export_simple_1d_arrays(tmp_path):
    fig_path = tmp_path / "figXX_test.png"
    csv_p, mat_p = export_figure_data(
        "figXX",
        {"hora": np.arange(24), "demanda_kW": np.linspace(1, 5, 24)},
        fig_path,
        metadata={"activity_ref": "Act 1.1", "units": "h, kW"},
    )

    assert csv_p.exists() and csv_p.suffix == ".csv"
    assert mat_p.exists() and mat_p.suffix == ".mat"

    df = pd.read_csv(csv_p)
    assert list(df.columns) == ["hora", "demanda_kW"]
    assert len(df) == 24
    assert df["demanda_kW"].iloc[-1] == pytest.approx(5.0)

    mat = sio.loadmat(mat_p)
    assert "hora" in mat and "demanda_kW" in mat
    assert mat["hora"].size == 24


def test_export_handles_nan(tmp_path):
    fig_path = tmp_path / "fig_nan.png"
    arr = np.array([1.0, np.nan, 3.0, np.nan, 5.0])
    csv_p, mat_p = export_figure_data("fig_nan", {"valor": arr}, fig_path)

    df = pd.read_csv(csv_p)
    assert df["valor"].isna().sum() == 2

    mat = sio.loadmat(mat_p)
    arr_mat = mat["valor"].ravel()
    assert np.isnan(arr_mat[1]) and np.isnan(arr_mat[3])


def test_export_heterogeneous_shapes_writes_per_series(tmp_path):
    fig_path = tmp_path / "fig_het.png"
    csv_p, mat_p = export_figure_data(
        "fig_het",
        {
            "vector_24": np.arange(24, dtype=float),
            "vector_5":  np.arange(5, dtype=float),
            "matriz_2d": np.eye(3),
        },
        fig_path,
    )

    # Los CSVs por serie comparten prefijo con el PNG
    siblings = list(tmp_path.glob("fig_het__*.csv"))
    assert len(siblings) == 3

    mat = sio.loadmat(mat_p)
    assert "vector_24" in mat and "vector_5" in mat and "matriz_2d" in mat
    assert mat["matriz_2d"].shape == (3, 3)


def test_export_dataframe_preserves_columns(tmp_path):
    fig_path = tmp_path / "fig_df.png"
    df = pd.DataFrame(
        {"P2P": [100, 200, 300], "C4": [80, 150, 250]},
        index=pd.Index(["Udenar", "Mariana", "UCC"], name="agente"),
    )
    csv_p, mat_p = export_figure_data("fig_df", {"ganancia": df}, fig_path)

    siblings = list(tmp_path.glob("fig_df__*.csv"))
    assert len(siblings) == 1
    df_back = pd.read_csv(siblings[0], index_col=0)
    assert list(df_back.columns) == ["P2P", "C4"]
    assert df_back.loc["Mariana", "C4"] == 150


def test_metadata_included_in_mat(tmp_path):
    fig_path = tmp_path / "fig_meta.png"
    _, mat_p = export_figure_data(
        "fig_meta",
        {"x": np.arange(3)},
        fig_path,
        metadata={"activity_ref": "Act 4.2", "units": "h", "description": "test"},
    )
    mat = sio.loadmat(mat_p)
    assert "metadata" in mat
    meta_struct = mat["metadata"]
    # scipy guarda dicts como struct arrays con dtype.names
    names = meta_struct.dtype.names
    assert names is not None
    assert "fig_id" in names
    assert "activity_ref" in names


def test_safe_export_swallows_exceptions(tmp_path, monkeypatch):
    """safe_export() nunca debe propagar excepciones."""
    fig_path = tmp_path / "fig_safe.png"

    # Forzar fallo: data con tipo no serializable y shapes heterogéneos
    class _Bad:
        pass

    csv_p, mat_p = safe_export("fig_safe", {"bad": _Bad()}, fig_path)
    # Permitido que falle silencioso; lo crítico es que no propague
    assert (csv_p is None) or csv_p.suffix == ".csv"


def test_sanitize_keys_with_special_chars(tmp_path):
    """Claves con espacios / acentos / símbolos deben sanitizarse para MATLAB."""
    fig_path = tmp_path / "fig_keys.png"
    _, mat_p = export_figure_data(
        "fig_keys",
        {"π_gb*ⁿ": np.arange(5), "Δ_ganancia (COP)": np.arange(5)},
        fig_path,
    )
    mat = sio.loadmat(mat_p)
    keys = [k for k in mat.keys() if not k.startswith("__")]
    # Las claves deben ser identificadores MATLAB válidos: solo [A-Za-z0-9_]
    import re
    for k in keys:
        assert re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", k), f"clave inválida: {k}"


def test_csv_uses_utf8_bom(tmp_path):
    """El CSV debe abrirse correctamente en Excel y MATLAB readtable."""
    fig_path = tmp_path / "fig_utf8.png"
    csv_p, _ = export_figure_data(
        "fig_utf8",
        {"institución": np.array(["Udenar", "Mariana", "UCC"]),
         "energía_kWh": np.array([100.0, 200.0, 300.0])},
        fig_path,
    )
    raw = csv_p.read_bytes()
    # UTF-8 BOM = EF BB BF
    assert raw[:3] == b"\xef\xbb\xbf"
