"""Auditoria del preprocesamiento MTE: medidor unico + inversor EMS.

Reporta por institucion:
  - D_net (cruda del medidor elegido)
  - D_bruta (post-reconstruccion para Udenar; igual a D_net.clip(0) para gross)
  - G_ems  (inversor unico expuesto al EMS)
  - G_recon (suma de inversores reconstructores; solo Udenar)

Bloque diagnostico para Udenar: horas con D_net<0, horas con D_bruta=0
tras la suma, y delta de energia kWh(D_bruta) - kWh(D_net) que debe
aproximarse a la integral de G_recon.
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from data.xm_data_loader import (
    _clean, T_START, T_END, AGENTS,
    METER_FOLDER, INVERTER_FOLDER, COL_DEMAND,
)
from data.preprocessing import (
    DEMAND_METER_CONFIG, EMS_INVERTER_CONFIG, RECONSTRUCTION_INVERTERS_CONFIG,
    _find_subdir, _read_single_meter, _read_single_inverter,
    _sum_inverter_reconstruction,
)


root = Path(os.environ.get("MTE_ROOT", "MedicionesMTE_v3"))
ts = os.environ.get("MTE_T_START", T_START)
te = os.environ.get("MTE_T_END", T_END)
idx = pd.date_range(ts, te, freq="1h", inclusive="left")
print(f"Auditando {root} | horizonte {ts} -> {te} ({len(idx)} h)")


def stats_block(label: str, raw: pd.Series, clean_kwh_only: bool = False):
    """Imprime una linea con estadisticos clave de una serie."""
    valid = raw.dropna()
    if len(valid) == 0:
        print(f"  {label:<22s}  (sin datos)")
        return
    q25 = float(valid.quantile(0.25))
    q75 = float(valid.quantile(0.75))
    p995 = float(valid.quantile(0.995))
    iqr = q75 - q25
    raw_kwh = float(valid.sum())
    raw_max = float(valid.max())
    raw_min = float(valid.min())
    n_neg = int((valid < 0).sum())
    if iqr > 0:
        umbral_iqr = q75 + 5 * iqr
    else:
        umbral_iqr = float("inf")
    umbral_p995 = p995 * 1.2 if np.isfinite(p995) else float("inf")
    umbral = max(umbral_iqr, umbral_p995)
    h_clip = int((valid > umbral).sum())
    kwh_clip = float(valid[valid > umbral].sum())

    cleaned = _clean(raw.copy(), label).clip(lower=0)
    cln_kwh = float(cleaned.sum())
    cln_max = float(cleaned.max())
    perd = 100.0 * (raw_kwh - cln_kwh) / max(abs(raw_kwh), 1e-9)

    print(
        f"  {label:<22s} "
        f"min={raw_min:>7.2f} max={raw_max:>7.2f} kWh={raw_kwh:>9.0f} "
        f"neg_h={n_neg:>4d} | "
        f"q25={q25:>5.2f} q75={q75:>5.2f} p995={p995:>5.2f} umbr={umbral:>6.2f} "
        f"clip_h={h_clip:>3d} | "
        f"cln_max={cln_max:>6.2f} cln_kWh={cln_kwh:>8.0f} perd={perd:>5.1f}%"
    )


print("=" * 110)
print("AUDITORIA DEL PREPROCESAMIENTO MTE (un medidor + un inversor EMS por institucion)")
print("=" * 110)

for n, agent in enumerate(AGENTS):
    adir = _find_subdir(root, agent)
    if adir is None:
        print(f"\n[{n}] {agent}: CARPETA NO ENCONTRADA")
        continue

    cfg_d = DEMAND_METER_CONFIG.get(agent, {})
    ems_sub = EMS_INVERTER_CONFIG.get(agent)
    recon_subs = RECONSTRUCTION_INVERTERS_CONFIG.get(agent, [])
    kind = cfg_d.get("kind", "gross")

    print(f"\n[{n}] {agent}  ({kind.upper()})")
    print(f"     Medidor demanda: {cfg_d.get('subfolder', '-')}")
    print(f"     Inversor EMS:    {ems_sub or '-'}")
    if recon_subs:
        print(f"     Inversores reconstruccion ({len(recon_subs)}): "
              f"{', '.join(recon_subs)}")
    print()

    meter_root = _find_subdir(adir, METER_FOLDER[agent])
    mdir = _find_subdir(meter_root, cfg_d.get("subfolder", "")) if meter_root else None

    inv_root = _find_subdir(adir, INVERTER_FOLDER[agent])
    ems_dir = _find_subdir(inv_root, ems_sub) if inv_root and ems_sub else None

    # Crudas
    D_net = _read_single_meter(mdir, COL_DEMAND, idx, divide_by=1.0) if mdir is not None else pd.Series(np.nan, index=idx)
    G_ems = _read_single_inverter(ems_dir, idx) if ems_dir is not None else pd.Series(0.0, index=idx)
    G_recon = _sum_inverter_reconstruction(adir, recon_subs, idx) if recon_subs else None

    # Demanda bruta segun semantica
    G_recon_filled = (G_recon if G_recon is not None else pd.Series(0.0, index=idx)).fillna(0.0)
    if kind in ("net", "net_partial"):
        D_bruta = (D_net.fillna(0.0) + G_recon_filled).clip(lower=0.0)
    else:
        D_bruta = D_net.clip(lower=0.0)

    stats_block("D_net (raw)", D_net)
    stats_block("D_bruta (input EMS)", D_bruta)
    stats_block("G_ems  (input EMS)", G_ems)
    if G_recon is not None:
        n_inv = len(recon_subs)
        stats_block(f"G_recon (suma {n_inv}inv)", G_recon)

    # Diagnostico para net y net_partial
    if kind in ("net", "net_partial"):
        D_net_filled = D_net.fillna(0.0)
        n_dnet_neg = int((D_net < 0).sum())
        n_dbruta_zero_clip = int(((D_net_filled + G_recon_filled) < 0).sum())
        delta_kwh = float(D_bruta.sum() - D_net_filled.clip(lower=0).sum())
        gr_total = float(G_recon_filled.sum()) if G_recon is not None else 0.0
        print(f"\n     Diagnostico {agent} ({kind}):")
        print(f"       horas D_net < 0:                        {n_dnet_neg}")
        print(f"       horas D_bruta clipeadas a 0 tras suma:  {n_dbruta_zero_clip}")
        print(f"       delta kWh(D_bruta) - kWh(max(D_net,0)): {delta_kwh:>10.0f}")
        print(f"       integral G_recon (kWh):                  {gr_total:>10.0f}")
        ratio = delta_kwh / gr_total if gr_total > 0 else float("nan")
        print(f"       ratio delta/G_recon:                     {ratio:>10.3f}")

print()
print("=" * 110)
print("Convenciones:")
print("  raw_*:   serie cruda tras resample horario, antes de _clean")
print("  cln_*:   lo que recibe el EMS tras _clean (outliers + gaps + fillna)")
print("  perd%:   energia perdida por el pipeline respecto a la cruda")
print("  net          (Udenar)        D_bruta = max(0, D_net + Fronius1 + Fronius2 + InversorMTE)")
print("  net_partial  (Mariana, UCC)   D_bruta = max(0, D_net + Inversor)")
print("  gross        (HUDN, Cesmag)   D_bruta = max(0, D_net)")
print("=" * 110)
