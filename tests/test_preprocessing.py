"""
Actividad 3.1 - Tests del modulo data/preprocessing.py.

Verifica el contrato del refactor:
  1. Demanda y generacion no-negativas por construccion.
  2. Shape y orden de agentes invariantes.
  3. Reconstruccion net->bruta de Udenar usa los 3 inversores;
     EMS solo expone Inversor MTE (las dos capas son distintas).
  4. Para los gross (Mariana, UCC, HUDN, Cesmag) la demanda corresponde
     al medidor unico declarado.
  5. Smoke test del wrapper MTEDataLoader.

Requiere MedicionesMTE/ presente bajo la raiz del repo.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
MTE_ROOT = Path(os.environ.get("MTE_ROOT", REPO_ROOT / "MedicionesMTE_v3"))


pytestmark = pytest.mark.skipif(
    not MTE_ROOT.exists(),
    reason=f"MedicionesMTE no encontrado en {MTE_ROOT}; tests de datos reales saltados",
)


@pytest.fixture(scope="module")
def loaded():
    from data.preprocessing import build_demand_generation
    D, G, idx = build_demand_generation(MTE_ROOT, verbose=False)
    return D, G, idx


def test_demand_non_negative(loaded):
    D, G, _ = loaded
    assert (D >= 0).all(), "La demanda debe ser no-negativa por construccion"
    assert (G >= 0).all(), "La generacion debe ser no-negativa"


def test_shape_invariant(loaded):
    D, G, idx = loaded
    # Horizonte sólido común Abr 4 → Dic 16, 2025 sobre v3 (ver § 3.1)
    assert D.shape == (5, 6144), f"D shape esperado (5, 6144), obtenido {D.shape}"
    assert G.shape == (5, 6144), f"G shape esperado (5, 6144), obtenido {G.shape}"
    assert str(idx.tz) == "America/Bogota"
    assert D.dtype == np.float64
    assert G.dtype == np.float64


def test_agent_order(loaded):
    from data.xm_data_loader import AGENTS
    assert AGENTS == ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]
    D, G, _ = loaded
    assert D.shape[0] == len(AGENTS)


def test_udenar_net_reconstruction_increases_demand(loaded):
    """
    Para Udenar, la suma de los inversores de reconstruccion debe haber
    aumentado la demanda total respecto al raw del medidor neto
    (que tiene ~1146 horas con valor < 0).
    """
    from data.preprocessing import (
        DEMAND_METER_CONFIG, _find_subdir, _read_single_meter,
    )
    from data.xm_data_loader import (
        AGENTS, METER_FOLDER, COL_DEMAND, T_START, T_END,
    )

    idx = pd.date_range(T_START, T_END, freq="1h", inclusive="left")
    udenar_dir = _find_subdir(MTE_ROOT, "Udenar")
    meter_root = _find_subdir(udenar_dir, METER_FOLDER["Udenar"])
    sub = DEMAND_METER_CONFIG["Udenar"]["subfolder"]
    mdir = _find_subdir(meter_root, sub)
    D_net = _read_single_meter(mdir, COL_DEMAND, idx, divide_by=1.0).fillna(0.0)

    # max(D_net, 0): lo que veriamos si simplemente clipeasemos sin reconstruir
    kwh_clipped = float(D_net.clip(lower=0).sum())

    D, _, _ = loaded
    udenar_idx = AGENTS.index("Udenar")
    kwh_udenar = float(D[udenar_idx].sum())

    assert kwh_udenar > kwh_clipped, (
        f"D_bruta(Udenar)={kwh_udenar:.0f} kWh debe ser mayor que "
        f"max(D_net,0)={kwh_clipped:.0f} kWh por la reconstruccion"
    )


def test_udenar_ems_inverter_distinct_from_reconstruction(loaded):
    """
    G[Udenar] expone solo Inversor MTE; G_recon suma 3 inversores.
    Por construccion, integral G_recon >= integral G[Udenar].
    """
    from data.preprocessing import (
        RECONSTRUCTION_INVERTERS_CONFIG, _find_subdir,
        _sum_inverter_reconstruction,
    )
    from data.xm_data_loader import AGENTS, T_START, T_END

    idx = pd.date_range(T_START, T_END, freq="1h", inclusive="left")
    udenar_dir = _find_subdir(MTE_ROOT, "Udenar")
    G_recon = _sum_inverter_reconstruction(
        udenar_dir, RECONSTRUCTION_INVERTERS_CONFIG["Udenar"], idx,
    ).fillna(0.0)

    _, G, _ = loaded
    udenar_idx = AGENTS.index("Udenar")
    g_ems_total = float(G[udenar_idx].sum())
    g_recon_total = float(G_recon.sum())

    assert g_recon_total > g_ems_total, (
        f"G_recon total ({g_recon_total:.0f} kWh) debe ser mayor que "
        f"G_ems Udenar ({g_ems_total:.0f} kWh) — son capas distintas"
    )
    # Deberian ser ratios razonables: G_recon ~= 3x G_ems si los 3 inv producen similar
    ratio = g_recon_total / max(g_ems_total, 1.0)
    assert 1.5 < ratio < 6.0, (
        f"Ratio G_recon/G_ems = {ratio:.2f} fuera de rango razonable"
    )


def test_mariana_ucc_net_partial_reconstruction(loaded):
    """
    Mariana y UCC son net_partial: tienen pocas horas con D<0
    (160 h y 119 h respectivamente sobre el horizonte completo). Tras la
    reconstruccion, la demanda total debe ser >= max(D_net, 0) y
    aproximadamente <= D_net + G_inv en la ventana del inversor.
    """
    from data.preprocessing import (
        DEMAND_METER_CONFIG, _find_subdir, _read_single_meter,
    )
    from data.xm_data_loader import (
        AGENTS, METER_FOLDER, COL_DEMAND, T_START, T_END,
    )

    idx = pd.date_range(T_START, T_END, freq="1h", inclusive="left")

    for agent in ("Mariana", "UCC"):
        a_dir = _find_subdir(MTE_ROOT, agent)
        meter_root = _find_subdir(a_dir, METER_FOLDER[agent])
        sub = DEMAND_METER_CONFIG[agent]["subfolder"]
        mdir = _find_subdir(meter_root, sub)
        D_net = _read_single_meter(mdir, COL_DEMAND, idx, divide_by=1.0).fillna(0.0)
        kwh_clipped = float(D_net.clip(lower=0).sum())

        D, _, _ = loaded
        ai = AGENTS.index(agent)
        kwh_recon = float(D[ai].sum())

        assert kwh_recon >= kwh_clipped, (
            f"{agent}: D_recon={kwh_recon:.0f} debe ser >= max(D_net,0)={kwh_clipped:.0f}"
        )
        # Ademas el tipo declarado debe ser net_partial
        assert DEMAND_METER_CONFIG[agent]["kind"] == "net_partial", (
            f"{agent} no esta marcado como net_partial"
        )


def test_hudn_cesmag_gross_passthrough(loaded):
    """
    Para HUDN y Cesmag (gross) D_max debe ser cercano al maximo del CSV
    crudo (no hay reconstruccion).
    """
    from data.preprocessing import (
        DEMAND_METER_CONFIG, _find_subdir, _read_single_meter,
    )
    from data.xm_data_loader import (
        AGENTS, METER_FOLDER, COL_DEMAND, T_START, T_END,
    )

    idx = pd.date_range(T_START, T_END, freq="1h", inclusive="left")

    for agent in ("HUDN", "Cesmag"):
        a_dir = _find_subdir(MTE_ROOT, agent)
        meter_root = _find_subdir(a_dir, METER_FOLDER[agent])
        sub = DEMAND_METER_CONFIG[agent]["subfolder"]
        mdir = _find_subdir(meter_root, sub)
        D_raw = _read_single_meter(mdir, COL_DEMAND, idx, divide_by=1.0).clip(lower=0)
        raw_max = float(D_raw.max())

        D, _, _ = loaded
        ai = AGENTS.index(agent)
        cleaned_max = float(D[ai].max())

        assert 0.5 * raw_max <= cleaned_max <= 1.05 * raw_max, (
            f"D_max({agent})={cleaned_max:.2f} fuera de rango vs raw_max={raw_max:.2f}"
        )


def test_loader_smoke():
    from data.xm_data_loader import MTEDataLoader
    D, G, idx = MTEDataLoader(str(MTE_ROOT)).load(verbose=False)
    assert D.shape == G.shape == (5, 6144)
    assert (D >= 0).all() and (G >= 0).all()
    assert isinstance(idx, pd.DatetimeIndex)
