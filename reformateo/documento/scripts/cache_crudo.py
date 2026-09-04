"""
cache_crudo.py — Instantáneas intermedias del preprocesamiento.
================================================================
El capítulo 3 del documento muestra qué le pasa al dato en cada etapa
del pipeline. Para dibujarlo hace falta algo que el proyecto no guarda:
los estados **intermedios**. ``build_demand_generation()`` entrega el
resultado final —matrices limpias y no negativas— y descarta por el
camino justo lo que aquí interesa: la demanda tal como salió del
medidor, la generación que se le sumó para revertir el neteo, los
valores que la limpieza marcó como atípicos y los huecos que rellenó.

Este script vuelve a recorrer el pipeline **usando las mismas funciones
del proyecto** (``_read_single_meter``, ``_read_ems_generation``,
``_sum_inverter_reconstruction``, ``_clean``), pero conservando cada
estado intermedio. Al reusar las funciones originales en lugar de
reimplementarlas, el caché es fiel por construcción: si el pipeline
cambia, el caché cambia con él.

Salida
------
``datos_cache/preproceso_{m1,m3}.npz`` con, por institución:

    D_raw      demanda del medidor, sin tratar (puede ser negativa)
    G_recon    suma de los inversores usados para revertir el neteo
    D_recon    demanda ya reconstruida y no negativa
    D_limpia   demanda tras _clean (la que ve el modelo)
    G_ems      inversor EMS, crudo
    G_limpia   generación tras _clean (la que ve el modelo)
    mask_out   horas que _clean marcó como atípicas
    mask_imp   horas que _clean rellenó (estaban vacías y salieron con valor)

Se ejecuta una sola vez; después las figuras leen el .npz.

    python scripts/cache_crudo.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from data.preprocessing import (                       # noqa: E402
    DEMAND_METER_CONFIG,
    EMS_INVERTER_BACKFILL_CONFIG,
    EMS_INVERTER_CONFIG,
    PAPER_METER_DEMAND_CONFIG,
    RECONSTRUCTION_INVERTERS_CONFIG,
    _find_subdir,
    _read_ems_generation,
    _read_single_meter,
    _sum_inverter_reconstruction,
)
from data.xm_data_loader import (                      # noqa: E402
    AGENTS,
    COL_DEMAND,
    INVERTER_FOLDER,
    METER_FOLDER,
    T_END,
    T_START,
)

CACHE = Path(__file__).resolve().parent.parent / "datos_cache"


def raiz_mte() -> Path:
    """Ubica MedicionesMTE, respetando la variable de entorno del proyecto."""
    env = os.environ.get("MTE_ROOT")
    if env and Path(env).exists():
        return Path(env)
    for nombre in ("MedicionesMTE_v3", "MedicionesMTE"):
        p = RAIZ / nombre
        if p.exists():
            return p
    raise FileNotFoundError(
        "No se encuentra MedicionesMTE. Definir MTE_ROOT o colocarla en la raíz.")


def limpiar_instrumentado(s: pd.Series):
    """
    Réplica instrumentada de ``xm_data_loader._clean``.

    Devuelve (serie_limpia, mask_outliers, mask_imputados). La lógica y
    los umbrales son exactamente los del original —umbral robusto
    ``max(Q75 + 5·IQR, P99,5 × 1,2)``, interpolación temporal de hasta
    3 h, relleno hacia adelante y atrás de hasta 24 h, y ceros para el
    resto—; lo único que se añade es el registro de qué horas tocó.

    Al final se comprueba que la serie coincide con la del pipeline
    original, de modo que la instrumentación no pueda desviarse en
    silencio.
    """
    s = s.copy()
    faltantes_iniciales = s.isna()

    q25, q75 = s.quantile(0.25), s.quantile(0.75)
    p995 = s.quantile(0.995)
    iqr = q75 - q25
    umbral_iqr = q75 + 5 * iqr if iqr > 0 else np.inf
    umbral_p995 = p995 * 1.2 if np.isfinite(p995) else np.inf
    umbral = max(umbral_iqr, umbral_p995)

    mask_out = pd.Series(False, index=s.index)
    if np.isfinite(umbral) and umbral > 0:
        mask_out = s > umbral
        s[mask_out] = np.nan

    # Todo lo que está vacío justo antes del relleno y sale con valor
    # después, fue imputado: los huecos originales más los atípicos.
    vacios_antes = s.isna()
    s = s.interpolate(method="time", limit=3)
    s = s.ffill(limit=24).bfill(limit=24)
    s = s.fillna(0.0)
    mask_imp = vacios_antes & s.notna()

    return s, mask_out.fillna(False), mask_imp, float(umbral), faltantes_iniciales


def construir(cobertura: str, verbose: bool = True) -> Path:
    """Recorre el pipeline guardando cada estado intermedio."""
    root = raiz_mte()
    idx = pd.date_range(T_START, T_END, freq="1h", inclusive="left")
    d_cfg = DEMAND_METER_CONFIG if cobertura == "m1" else PAPER_METER_DEMAND_CONFIG

    print(f"\n[{cobertura.upper()}] raíz={root.name}  horizonte={T_START}..{T_END} "
          f"({len(idx)} h)")

    salida: dict[str, np.ndarray] = {}
    resumen = []

    for agente in AGENTS:
        adir = _find_subdir(root, agente)
        cfg = d_cfg.get(agente, {})
        tipo = cfg.get("kind", "gross")

        # ── 1. Demanda cruda, tal como la entrega el medidor ─────────
        meter_root = _find_subdir(adir, METER_FOLDER[agente])
        mdir = _find_subdir(meter_root, cfg["subfolder"]) if meter_root else None
        D_raw = (_read_single_meter(mdir, COL_DEMAND, idx, divide_by=1.0)
                 if mdir is not None else pd.Series(np.nan, index=idx))
        if float(cfg.get("scale", 1.0)) != 1.0:
            D_raw = D_raw * float(cfg["scale"])

        # ── 2. Inversor EMS (la generación que ve el modelo) ─────────
        # CAL-44: se llama al mismo lector del pipeline en vez de repetir
        # su lógica aquí, para que la caché no vuelva a desviarse. Incluye
        # la extensión del inversor designado desde el de referencia.
        inv_root = _find_subdir(adir, INVERTER_FOLDER[agente])
        G_ems = (_read_ems_generation(
                     inv_root, EMS_INVERTER_CONFIG[agente],
                     EMS_INVERTER_BACKFILL_CONFIG.get(agente), idx,
                     etiqueta=agente, verbose=False)
                 if inv_root is not None else pd.Series(0.0, index=idx))

        # ── 3. Reconstrucción net->bruta, solo donde aplica ──────────
        if tipo in ("net", "net_partial"):
            G_recon = _sum_inverter_reconstruction(
                adir, RECONSTRUCTION_INVERTERS_CONFIG.get(agente, []), idx
            ).fillna(0.0)
            D_recon = (D_raw.fillna(0.0) + G_recon).clip(lower=0.0)
        else:
            G_recon = pd.Series(0.0, index=idx)
            D_recon = D_raw.clip(lower=0.0)

        # ── 4. Limpieza, con registro de lo que tocó ─────────────────
        D_limpia, out_d, imp_d, umbral_d, falt_d = limpiar_instrumentado(D_recon)
        G_limpia, out_g, imp_g, umbral_g, falt_g = limpiar_instrumentado(G_ems)

        for clave, serie in (
            (f"{agente}__D_raw", D_raw), (f"{agente}__G_recon", G_recon),
            (f"{agente}__D_recon", D_recon), (f"{agente}__D_limpia", D_limpia),
            (f"{agente}__G_ems", G_ems), (f"{agente}__G_limpia", G_limpia),
            (f"{agente}__mask_out_D", out_d), (f"{agente}__mask_imp_D", imp_d),
            (f"{agente}__mask_out_G", out_g), (f"{agente}__mask_imp_G", imp_g),
        ):
            salida[clave] = serie.values

        n_neg = int((D_raw < 0).sum())
        fila = {
            "institucion": agente,
            "tipo_medidor": tipo,
            "medidor": cfg.get("subfolder", "-"),
            "horas_negativas": n_neg,
            "pct_negativas": 100.0 * n_neg / len(idx),
            "min_D_raw_kW": float(D_raw.min()) if D_raw.notna().any() else np.nan,
            "horas_reconstruidas": int((G_recon > 0).sum()),
            "umbral_outlier_D_kW": umbral_d,
            "outliers_D": int(out_d.sum()),
            "faltantes_D": int(falt_d.sum()),
            "imputadas_D": int(imp_d.sum()),
            "pct_imputadas_D": 100.0 * int(imp_d.sum()) / len(idx),
            "outliers_G": int(out_g.sum()),
            "imputadas_G": int(imp_g.sum()),
            "D_media_kW": float(D_limpia.mean()),
            "G_media_kW": float(G_limpia.mean()),
        }
        resumen.append(fila)
        if verbose:
            print(f"  {agente:8s} [{tipo:11s}] D<0: {n_neg:4d} h "
                  f"({fila['pct_negativas']:4.1f} %)  min={fila['min_D_raw_kW']:7.2f} kW"
                  f"  outliers: {fila['outliers_D']:3d}  imputadas: {fila['imputadas_D']:4d}")

    salida["__horas"] = idx.values.astype("datetime64[ns]")
    CACHE.mkdir(parents=True, exist_ok=True)
    destino = CACHE / f"preproceso_{cobertura}.npz"
    np.savez_compressed(destino, **salida)

    df = pd.DataFrame(resumen)
    df.to_csv(CACHE / f"preproceso_{cobertura}_resumen.csv",
              index=False, encoding="utf-8-sig")
    print(f"  -> {destino.name}  ({destino.stat().st_size / 1e6:.1f} MB)")
    return destino


def verificar_contra_pipeline(cobertura: str) -> bool:
    """
    Comprueba que las series del caché coinciden con las que produce
    ``build_demand_generation()``.

    Es la garantía de que la instrumentación no se desvió del pipeline
    real. Si esto falla, las figuras del capítulo 3 estarían contando
    algo que el modelo no vio.
    """
    from data.preprocessing import build_demand_generation

    d_cfg = DEMAND_METER_CONFIG if cobertura == "m1" else PAPER_METER_DEMAND_CONFIG
    D, G, _ = build_demand_generation(raiz_mte(), demand_config=d_cfg, verbose=False)
    z = np.load(CACHE / f"preproceso_{cobertura}.npz", allow_pickle=True)

    ok = True
    for n, agente in enumerate(AGENTS):
        dd = np.abs(z[f"{agente}__D_limpia"] - D[n]).max()
        dg = np.abs(z[f"{agente}__G_limpia"] - G[n]).max()
        bien = dd < 1e-9 and dg < 1e-9
        ok &= bien
        print(f"  {agente:8s} max|dif| D={dd:.2e}  G={dg:.2e}  "
              f"{'OK' if bien else 'DISCREPA'}")
    return ok


if __name__ == "__main__":
    for cob in ("m1", "m3"):
        construir(cob)
    print("\n=== Verificación contra el pipeline del proyecto ===")
    todo = True
    for cob in ("m1", "m3"):
        print(f"[{cob.upper()}]")
        todo &= verificar_contra_pipeline(cob)
    print("\nCACHÉ FIEL AL PIPELINE" if todo else "\nDISCREPANCIA — revisar")
    raise SystemExit(0 if todo else 1)
