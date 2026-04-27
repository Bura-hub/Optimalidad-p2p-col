"""
statistical_tests.py
---------------------
Bootstrap por bloques (Kunsch 1989) para comparar beneficio neto P2P vs C4
sobre el horizonte completo (5160 h → 215 días).

Funciones principales:
    bootstrap_blocks(series_p2p, series_c4, block_days=7, n_bootstrap=1000, seed=42)
        Remuestrea bloques semanales preservando autocorrelación.
        Retorna dict con delta_mean, CI 95%, p-valor Wilcoxon, Cohen's d, n_eff.

    load_series_from_outputs(run_id=None)
        Carga series diarias desde:
          1. outputs/daily_series_{run_id}.csv  (si run_id especificado)
          2. outputs/daily_series_*.csv         (más reciente)
          3. Hoja "Series_diarias" de resultados_comparacion.xlsx
        Retorna (series_p2p, series_c4) como np.ndarray o (None, None).

    save_bootstrap_results(result, seed=42)
        Guarda outputs/bootstrap_{seed}.json y resultados_tests.xlsx.

    main()
        CLI con argparse; invocable como:
            python tests/statistical_tests.py [--run-id ID] [--n-bootstrap N]
                                              [--block-days B] [--seed S] [--out DIR]

Actividad 4.2 — Tests estadísticos rigor científico.
Ref: Documentos/PropuestaTesis.txt §VI.D
"""

import sys
import os
import json
import argparse
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd


# ── Rutas de proyecto ──────────────────────────────────────────────────────────

ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUTS_DIR = os.path.join(ROOT, "outputs")          # logs y checkpoints GSA
RESULTS_XL  = os.path.join(OUTPUTS_DIR, "resultados_comparacion.xlsx")  # salida base del EMS


# ── Bootstrap por bloques ──────────────────────────────────────────────────────

def bootstrap_blocks(
    series_p2p,
    series_c4,
    block_days: int = 7,
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> dict:
    """
    Bootstrap por bloques de Kunsch (1989) para series diarias de beneficio neto.

    La diferencia diaria delta = P2P[d] - C4[d] se remuestrea en bloques de
    `block_days` días consecutivos para preservar la autocorrelación semanal del
    mercado energético (ciclos día-laborable / fin-de-semana).

    Parámetros
    ----------
    series_p2p, series_c4 : array-like, shape (n_days,)
        Beneficio neto comunitario diario (COP) para cada escenario.
    block_days : int
        Longitud del bloque en días (default 7 = semana).
    n_bootstrap : int
        Número de remuestras bootstrap (default 1000).
    seed : int
        Semilla aleatoria para reproducibilidad.

    Retorna
    -------
    dict con:
        delta_mean       — diferencia media P2P - C4 en la serie original (COP/día)
        delta_std        — desviación estándar de delta_d
        ci_95_lower      — límite inferior IC 95% bootstrap (COP/día)
        ci_95_upper      — límite superior IC 95% bootstrap (COP/día)
        p_valor_wilcoxon — p-valor Wilcoxon pareado bilateral (scipy.stats)
        wilcoxon_stat    — estadístico W del test Wilcoxon
        cohens_d         — tamaño de efecto (delta_mean / delta_std)
        n_eff            — muestra efectiva ≈ n_days / block_days
        n_days           — longitud de la serie original
        n_bootstrap      — número de remuestras
        block_days       — longitud de bloque usada
        seed             — semilla usada
        interpretacion   — cadena con conclusión breve en español
    """
    from scipy.stats import wilcoxon

    series_p2p = np.asarray(series_p2p, dtype=float)
    series_c4  = np.asarray(series_c4,  dtype=float)

    if len(series_p2p) != len(series_c4):
        raise ValueError(
            f"series_p2p ({len(series_p2p)}) y series_c4 ({len(series_c4)}) "
            "deben tener la misma longitud."
        )

    n_days = len(series_p2p)
    delta  = series_p2p - series_c4

    if n_days < 2 * block_days:
        raise ValueError(
            f"Serie demasiado corta ({n_days} días) para block_days={block_days}. "
            "Usa block_days=1 o proporciona más datos."
        )

    # ── Bootstrap ─────────────────────────────────────────────────────────────
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n_days / block_days))

    # Índices iniciales válidos para bloques (wrap-around circular)
    start_indices = np.arange(n_days - block_days + 1)
    boot_means = np.empty(n_bootstrap)

    for b in range(n_bootstrap):
        starts = rng.choice(start_indices, size=n_blocks, replace=True)
        blocks = [delta[s : s + block_days] for s in starts]
        sample = np.concatenate(blocks)[:n_days]   # truncar al largo original
        boot_means[b] = sample.mean()

    ci_lower = float(np.percentile(boot_means, 2.5))
    ci_upper = float(np.percentile(boot_means, 97.5))

    # ── Test Wilcoxon pareado (sobre serie original, no bootstrap) ────────────
    if np.all(delta == 0):
        w_stat, p_val = 0.0, 1.0
    else:
        res_wx = wilcoxon(delta, alternative="two-sided", zero_method="wilcox")
        w_stat = float(res_wx.statistic)
        p_val  = float(res_wx.pvalue)

    # ── Cohen's d ─────────────────────────────────────────────────────────────
    delta_std = float(np.std(delta, ddof=1)) if n_days > 1 else 0.0
    cohens_d  = (float(np.mean(delta)) / delta_std) if delta_std > 1e-12 else 0.0

    # ── Muestra efectiva ──────────────────────────────────────────────────────
    n_eff = max(1, n_days // block_days)

    # ── Interpretación automática ─────────────────────────────────────────────
    p2p_mejor = float(np.mean(delta)) > 0
    sig       = p_val < 0.05
    dir_str   = "P2P > C4" if p2p_mejor else "C4 > P2P"
    sig_str   = f"diferencia estadísticamente significativa (p={p_val:.4f})" \
                if sig else f"diferencia NO significativa (p={p_val:.4f})"
    interpretacion = (
        f"{dir_str}: {sig_str}. IC 95% = [{ci_lower:,.0f}, {ci_upper:,.0f}] COP/día. "
        f"Cohen's d = {cohens_d:.2f} (n_eff={n_eff})."
    )

    return {
        "delta_mean":       float(np.mean(delta)),
        "delta_std":        delta_std,
        "ci_95_lower":      ci_lower,
        "ci_95_upper":      ci_upper,
        "p_valor_wilcoxon": p_val,
        "wilcoxon_stat":    w_stat,
        "cohens_d":         cohens_d,
        "n_eff":            n_eff,
        "n_days":           n_days,
        "n_bootstrap":      n_bootstrap,
        "block_days":       block_days,
        "seed":             seed,
        "interpretacion":   interpretacion,
    }


# ── Carga de series diarias ────────────────────────────────────────────────────

def load_series_from_outputs(run_id: str = None):
    """
    Busca series diarias de beneficio neto P2P y C4 en:
      1. outputs/daily_series_{run_id}.csv  — si run_id especificado
      2. outputs/daily_series_*.csv         — el más reciente por mtime
      3. Hoja "Series_diarias" de resultados_comparacion.xlsx

    Columnas esperadas: 'nb_p2p' y 'nb_c4' (COP/día, comunidad completa).

    Retorna
    -------
    (series_p2p, series_c4) : (np.ndarray, np.ndarray) o (None, None)
    """
    # Opción 1: CSV con run_id específico
    if run_id is not None:
        path = os.path.join(OUTPUTS_DIR, f"daily_series_{run_id}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            if "nb_p2p" in df.columns and "nb_c4" in df.columns:
                return df["nb_p2p"].to_numpy(), df["nb_c4"].to_numpy()

    # Opción 2: CSV más reciente en outputs/
    if os.path.isdir(OUTPUTS_DIR):
        import glob
        csvs = sorted(
            glob.glob(os.path.join(OUTPUTS_DIR, "daily_series_*.csv")),
            key=os.path.getmtime,
            reverse=True,
        )
        for csv_path in csvs:
            try:
                df = pd.read_csv(csv_path)
                if "nb_p2p" in df.columns and "nb_c4" in df.columns:
                    return df["nb_p2p"].to_numpy(), df["nb_c4"].to_numpy()
            except Exception:
                continue

    # Opción 3: hoja "Series_diarias" en resultados_comparacion.xlsx
    if os.path.exists(RESULTS_XL):
        try:
            xl = pd.ExcelFile(RESULTS_XL)
            if "Series_diarias" in xl.sheet_names:
                df = xl.parse("Series_diarias")
                if "nb_p2p" in df.columns and "nb_c4" in df.columns:
                    return df["nb_p2p"].to_numpy(), df["nb_c4"].to_numpy()
        except Exception:
            pass

    return None, None


# ── Guardar resultados ─────────────────────────────────────────────────────────

def save_bootstrap_results(result: dict, seed: int = 42, out_dir: str = None):
    """
    Guarda los resultados del bootstrap en:
      - outputs/bootstrap_{seed}.json
      - resultados_tests.xlsx (hoja "Bootstrap_P2P_vs_C4")

    Parámetros
    ----------
    result : dict
        Salida de bootstrap_blocks().
    seed : int
        Semilla usada (sufijo del nombre de archivo).
    out_dir : str, opcional
        Directorio de salida (default: outputs/).
    """
    if out_dir is None:
        out_dir = OUTPUTS_DIR
    os.makedirs(out_dir, exist_ok=True)

    # JSON
    json_path = os.path.join(out_dir, f"bootstrap_{seed}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Excel
    xl_path = os.path.join(OUTPUTS_DIR, "resultados_tests.xlsx")
    df = pd.DataFrame([result])
    with pd.ExcelWriter(xl_path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Bootstrap_P2P_vs_C4", index=False)

    return json_path, xl_path


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    """
    Carga series diarias desde outputs/, ejecuta bootstrap_blocks() e imprime
    el resultado. Guarda JSON y Excel en outputs/ y en la raíz del proyecto.

    Requiere haber corrido previamente:
        python main_simulation.py --data real --full
    para generar outputs/daily_series_<fecha>.csv con columnas nb_p2p y nb_c4.
    """
    parser = argparse.ArgumentParser(
        description="Bootstrap por bloques P2P vs C4 — Tesis Brayan López (Udenar 2026)"
    )
    parser.add_argument("--run-id",      default=None, help="ID del run (sufijo CSV)")
    parser.add_argument("--n-bootstrap", type=int, default=1000, metavar="N",
                        help="Número de remuestras bootstrap (default 1000)")
    parser.add_argument("--block-days",  type=int, default=7,  metavar="B",
                        help="Longitud de bloque en días (default 7)")
    parser.add_argument("--seed",        type=int, default=42, metavar="S",
                        help="Semilla aleatoria (default 42)")
    parser.add_argument("--out",         default=None, metavar="DIR",
                        help="Directorio de salida (default outputs/)")
    args = parser.parse_args()

    print("\nBootstrap por bloques — P2P vs C4")
    print("="*50)

    series_p2p, series_c4 = load_series_from_outputs(run_id=args.run_id)

    if series_p2p is None:
        print(
            "\n  [ERROR] No se encontraron series diarias.\n"
            "  Ejecuta primero:\n"
            "      python main_simulation.py --data real --full\n"
            "  para generar outputs/daily_series_<fecha>.csv"
        )
        sys.exit(1)

    print(f"  Series cargadas: {len(series_p2p)} días")
    print(f"  P2P  — media={np.mean(series_p2p):,.0f} COP/día, "
          f"std={np.std(series_p2p):,.0f}")
    print(f"  C4   — media={np.mean(series_c4):,.0f} COP/día, "
          f"std={np.std(series_c4):,.0f}")

    result = bootstrap_blocks(
        series_p2p, series_c4,
        block_days=args.block_days,
        n_bootstrap=args.n_bootstrap,
        seed=args.seed,
    )

    print(f"\n  Resultado bootstrap ({args.n_bootstrap} remuestras, "
          f"bloque={args.block_days}d, seed={args.seed}):")
    print(f"    delta_mean  = {result['delta_mean']:>12,.0f} COP/día")
    print(f"    IC 95%      = [{result['ci_95_lower']:>12,.0f}, "
          f"{result['ci_95_upper']:>12,.0f}]")
    print(f"    p_Wilcoxon  = {result['p_valor_wilcoxon']:.4f}")
    print(f"    Cohen's d   = {result['cohens_d']:.3f}")
    print(f"    n_eff       = {result['n_eff']}")
    print(f"\n  Interpretación: {result['interpretacion']}")

    j_path, xl_path = save_bootstrap_results(result, seed=args.seed, out_dir=args.out)
    print(f"\n  Guardado en: {j_path}")
    print(f"               {xl_path}")


if __name__ == "__main__":
    main()
