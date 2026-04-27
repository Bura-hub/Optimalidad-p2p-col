"""
global_sensitivity.py
----------------------
Análisis de sensibilidad global Sobol/Saltelli (SALib) sobre el EMS P2P.

Evalúa cómo 7 parámetros de entrada afectan 3 indicadores de desempeño:
    - ganancia_neta_p2p   : beneficio neto comunitario total P2P (u.o. o COP)
    - sc_comunidad        : autoconsumo promedio comunidad P2P (fracción)
    - ie_p2p              : índice de equidad P2P (fracción)

Parámetros y rangos (ajustables en PARAM_BOUNDS):
    PGB        [114, 500]   COP/kWh — precio de bolsa (CREG 101 066)
    PGS        [500, 750]   COP/kWh — tarifa al usuario
    factor_PV  [0.5, 2.0]  — escalado de perfiles de generación solar
    factor_D   [0.7, 1.5]  — escalado de perfiles de demanda
    alpha_mean [0.0, 0.25]  — flexibilidad DR media (sin DR → DR realista)
    b_mean     [150, 400]   COP/kWh — coeficiente lineal del costo de generación
                            NOTA: b_n es el LCOE lineal en C(P)=a*P²+b*P+c,
                            NO el precio de bolsa (pi_bolsa).
    pi_ppa     [200, 900]   COP/kWh — precio PPA bilateral (C2)

Uso:
    from analysis.global_sensitivity import run_sobol_analysis, compute_indices, save_results
    Y_dict   = run_sobol_analysis(n_base=64, seed=42)
    idx_dict = compute_indices(Y_dict, Y_dict["problem"])
    save_results(idx_dict)

    # Desde línea de comando (smoke test):
    python analysis/global_sensitivity.py --n-base 4

Actividad 4.1 — Análisis de sensibilidad global.
Ref: Documentos/PropuestaTesis.txt §VI.D
"""

import sys
import os
import glob
import time
import warnings
import logging
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Rangos de parámetros (ajustables antes de la corrida final) ───────────────
#
# Revisar con los asesores antes de usar n_base >= 256.
# Los rangos representan incertidumbre regulatoria y de recursos Colombia 2025.

PARAM_BOUNDS = {
    "PGB":        {"bounds": [114.0,  500.0], "dists": "unif",
                   "desc":   "Precio de bolsa (COP/kWh); CREG 101 066: 114–500"},
    "PGS":        {"bounds": [500.0,  750.0], "dists": "unif",
                   "desc":   "Tarifa al usuario (COP/kWh); subsidio→tarifa media"},
    "factor_PV":  {"bounds": [0.5,    2.0],   "dists": "unif",
                   "desc":   "Factor de escala generación solar; nublado→óptimo"},
    "factor_D":   {"bounds": [0.7,    1.5],   "dists": "unif",
                   "desc":   "Factor de escala demanda; vacaciones→pico"},
    "alpha_mean": {"bounds": [0.0,    0.25],  "dists": "unif",
                   "desc":   "Flexibilidad DR media; sin DR→realista (~30% max)"},
    "b_mean":     {"bounds": [150.0,  400.0], "dists": "unif",
                   "desc":   "Coef. lineal costo generación b_n (COP/kWh); "
                             "es el LCOE lineal en C(P)=a*P²+b*P+c, NO pi_bolsa"},
    "pi_ppa":     {"bounds": [200.0,  900.0], "dists": "unif",
                   "desc":   "Precio PPA bilateral (COP/kWh); pi_gb→cercano pi_gs"},
}

_PARAM_NAMES  = list(PARAM_BOUNDS.keys())
_PARAM_BOUNDS = [PARAM_BOUNDS[k]["bounds"] for k in _PARAM_NAMES]
_N_PARAMS     = len(_PARAM_NAMES)


# ── Construcción del problema SALib ───────────────────────────────────────────

def _build_problem():
    return {
        "num_vars": _N_PARAMS,
        "names":    _PARAM_NAMES,
        "bounds":   _PARAM_BOUNDS,
    }


# ── Evaluación de un punto del espacio paramétrico ───────────────────────────

def _eval_sample(params: np.ndarray) -> tuple:
    """
    Evalúa el EMS P2P para un vector de parámetros de longitud 7.

    Retorna (ganancia_neta_p2p, sc_comunidad, ie_p2p) o (nan, nan, nan) si falla.
    """
    # Suprimir stdout/stderr para evitar UnicodeEncodeError en subprocess hijos
    # de Windows (cp1252) cuando tqdm escribe caracteres Unicode (█░).
    import os, sys
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

    from core.ems_p2p       import EMSP2P, AgentParams, GridParams, SolverParams
    from scenarios          import run_comparison
    from data.base_case_data import (
        get_generation_profiles, get_demand_profiles, get_agent_params,
    )
    from core.market_prep   import compute_generation_limit

    # _fast_mode DESACTIVADO: el GSA del 2026-04-17 (n_base=64) corrió
    # exitosamente en modo preciso. El intento del 2026-04-26 con
    # _fast_mode=True fue abortado por cuelgues en samples patológicos del
    # solver LSODA. test_fast_mode_equivalence.py valida 8 horas representativas
    # pero NO toda la distribución Saltelli — algunos samples disparan ciclos
    # del Newton iterativo de LSODA cuando rtol=0.5 + max_step=2e-4 son
    # incompatibles con dinámicas no-stiff de baja amplitud.
    import core.replicator_sellers as _rs
    _rs._fast_mode = False

    (pgb, pgs, f_pv, f_d, alpha_mean, b_mean, pi_ppa) = params

    try:
        G_base = get_generation_profiles() * f_pv    # (N, 24)
        D_base = get_demand_profiles()     * f_d     # (N, 24)
        p      = get_agent_params()
        N      = p["N"]

        # Reemplazar b con b_mean uniforme (mantiene heterogeneidad a_n)
        b_new = np.full(N, b_mean)

        agents = AgentParams(
            N=N,
            a=p["a"], b=b_new, c=p["c"],
            lam=p["lam"], theta=p["theta"], etha=p["etha"],
            alpha=np.full(N, alpha_mean),
        )
        grid   = GridParams(pi_gs=pgs, pi_gb=pgb)
        solver = SolverParams(
            stackelberg_iters=2, stackelberg_tol=5e-3, stackelberg_max=4,
            parallel=False,
        )

        ems = EMSP2P(agents, grid, solver)
        results, G_klim, D_star = ems.run(D_base, G_base)

        # Clasificar prosumidores/consumidores (mayoría de horas)
        sell_cnt = np.zeros(N, dtype=int)
        buy_cnt  = np.zeros(N, dtype=int)
        for r in results:
            for j in r.seller_ids:
                sell_cnt[j] += 1
            for i in r.buyer_ids:
                buy_cnt[i] += 1
        prosumer_ids = [n for n in range(N) if sell_cnt[n] > 0]
        consumer_ids = [n for n in range(N) if buy_cnt[n] > 0 and sell_cnt[n] == 0]
        if not prosumer_ids:
            prosumer_ids = list(range(N))

        pi_bolsa = np.full(D_star.shape[1], pgb)

        cr = run_comparison(
            D=D_star, G_klim=G_klim, G_raw=G_base,
            p2p_results=results,
            pi_gs=pgs, pi_gb=pgb,
            pi_bolsa=pi_bolsa,
            prosumer_ids=prosumer_ids,
            consumer_ids=consumer_ids,
            pi_ppa=pi_ppa,
        )

        ganancia = float(cr.net_benefit.get("P2P", 0.0))
        sc       = float(cr.self_consumption.get("P2P", 0.0))
        ie       = float(cr.equity_index.get("P2P", 0.0))
        return ganancia, sc, ie

    except Exception as exc:
        logger.warning("GSA sample failed: %s", exc)
        return float("nan"), float("nan"), float("nan")


# ── Worker para ProcessPoolExecutor ──────────────────────────────────────────

# Timeout por evaluación. Algunos samples (~20%) entran en zonas patológicas
# donde solve_ivp/LSODA del replicator se atora indefinidamente (combinaciones
# específicas de PGB+PGS+factor_PV+b_mean producen un equilibrio Nash inestable
# cerca del simplex frontier). Sin timeout, esos samples bloquean a su worker
# para siempre. 45s es ~10× la duración normal (~5s); samples que excedan se
# marcan NaN y se filtran en el análisis Sobol (los samples NaN no afectan la
# convergencia del estimador siempre que la fracción válida sea >70%).
_EVAL_TIMEOUT_S = 45


def _worker(args):
    """Wrapper top-level para ProcessPoolExecutor (pickle-safe en Windows).

    Ejecuta _eval_sample en un subproceso aislado con timeout. Si excede
    _EVAL_TIMEOUT_S, mata el subproceso y retorna NaN.
    """
    from concurrent.futures import ProcessPoolExecutor
    from concurrent.futures import TimeoutError as _FT
    idx, params = args
    with ProcessPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(_eval_sample, params)
        try:
            return idx, fut.result(timeout=_EVAL_TIMEOUT_S)
        except _FT:
            for p in ex._processes.values():
                try:
                    p.kill()
                except Exception:
                    pass
            return idx, (float("nan"), float("nan"), float("nan"))


# ── Análisis Sobol/Saltelli ───────────────────────────────────────────────────

def run_sobol_analysis(
    n_base:          int  = 64,
    params_override: dict = None,
    seed:            int  = 42,
    checkpoint_every: int = 100,
    parallel:        bool = True,
) -> dict:
    """
    Ejecuta el análisis de sensibilidad global Sobol/Saltelli.

    Parámetros
    ----------
    n_base : int
        Tamaño base de la muestra Saltelli.
        Evaluaciones totales = n_base * (2 * N_params + 2) = n_base * 16.
        Default 64 → 1024 evaluaciones (~75 min con 8 workers en datos sintéticos).
        ADVERTENCIA: usar n_base >= 256 solo con aprobación de los asesores
        (→ 4096 evaluaciones, ~5 h).
    params_override : dict, opcional
        Diccionario {nombre: [lb, ub]} para sobrescribir rangos de PARAM_BOUNDS.
    seed : int
        Semilla Saltelli.
    checkpoint_every : int
        Guardar checkpoint en outputs/ cada N evaluaciones.
    parallel : bool
        Usar ProcessPoolExecutor (requiere freeze_support en Windows).

    Retorna
    -------
    dict con:
        problem  — dict SALib
        X        — matriz de muestras (M, N_params)
        Y_ganancia, Y_sc, Y_ie — vectores de salida (M,)
        n_eval   — número de evaluaciones completadas
        elapsed  — tiempo total en segundos
    """
    from SALib.sample.sobol import sample as sobol_sample
    from multiprocessing import cpu_count, freeze_support
    from concurrent.futures import ProcessPoolExecutor, as_completed

    problem = _build_problem()
    if params_override:
        for name, bounds in params_override.items():
            if name in problem["names"]:
                idx = problem["names"].index(name)
                problem["bounds"][idx] = bounds

    if n_base >= 256:
        print(
            f"\n  ADVERTENCIA: n_base={n_base} → "
            f"{n_base*(2*_N_PARAMS+2)} evaluaciones (~5 h). "
            "Asegúrate de tener aprobación de los asesores."
        )

    X = sobol_sample(problem, N=n_base, calc_second_order=True,
                     seed=seed, skip_values=0)
    M = len(X)
    print(f"\n  GSA Saltelli: {M} evaluaciones, {_N_PARAMS} parámetros, seed={seed}")

    Y_ganancia = np.full(M, np.nan)
    Y_sc       = np.full(M, np.nan)
    Y_ie       = np.full(M, np.nan)

    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs"),
                exist_ok=True)
    outputs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")

    t0 = time.time()

    # Resume desde el checkpoint más reciente si existe
    already_done = set()
    cp_files = sorted(
        glob.glob(os.path.join(outputs_dir, "gsa_checkpoint_*.parquet")) +
        glob.glob(os.path.join(outputs_dir, "gsa_checkpoint_*.csv"))
    )
    if cp_files:
        latest_cp = cp_files[-1]
        try:
            if latest_cp.endswith(".parquet"):
                cp_df = pd.read_parquet(latest_cp)
            else:
                cp_df = pd.read_csv(latest_cp)
            valid_mask = ~np.isnan(cp_df["Y_ganancia"].values)
            if valid_mask.sum() > 0:
                n_cp = len(cp_df)
                Y_ganancia[:n_cp] = cp_df["Y_ganancia"].values
                Y_sc[:n_cp]       = cp_df["Y_sc"].values
                Y_ie[:n_cp]       = cp_df["Y_ie"].values
                already_done = {i for i in range(n_cp) if valid_mask[i]}
                print(f"  Resume desde checkpoint: {os.path.basename(latest_cp)} "
                      f"({len(already_done)} muestras recuperadas de {M})")
        except Exception as e:
            print(f"  Checkpoint no legible ({e}), arrancando desde cero.")

    jobs = [(i, X[i]) for i in range(M) if i not in already_done]

    def _save_checkpoint(step):
        """Persiste el estado parcial de Y_* en outputs/ para recuperación ante fallos."""
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        cp_path = os.path.join(outputs_dir, f"gsa_checkpoint_{ts}.parquet")
        df = pd.DataFrame({
            **{_PARAM_NAMES[j]: X[:, j] for j in range(_N_PARAMS)},
            "Y_ganancia": Y_ganancia,
            "Y_sc":       Y_sc,
            "Y_ie":       Y_ie,
        })
        try:
            df.to_parquet(cp_path, index=False)
            print(f"    Checkpoint guardado: {os.path.basename(cp_path)} ({step}/{M})")
        except ImportError:
            df.to_csv(cp_path.replace(".parquet", ".csv"), index=False)

    if parallel:
        freeze_support()
        n_workers = max(1, cpu_count() - 1)
        print(f"  Modo paralelo: {n_workers} workers, {len(jobs)} muestras pendientes")
        done = len(already_done)
        with ProcessPoolExecutor(max_workers=n_workers) as ex:
            futs = {ex.submit(_worker, j): j[0] for j in jobs}
            for f in as_completed(futs):
                i, (g, sc, ie) = f.result()
                Y_ganancia[i] = g
                Y_sc[i]       = sc
                Y_ie[i]       = ie
                done += 1
                if done % checkpoint_every == 0:
                    _save_checkpoint(done)
                if done % max(1, M // 50) == 0:
                    elapsed = time.time() - t0
                    eta     = elapsed / done * (M - done)
                    print(f"    {done}/{M} ({100*done/M:.0f}%)  "
                          f"elapsed={elapsed:.0f}s  ETA={eta:.0f}s",
                          flush=True)
    else:
        for i, params in [(j[0], j[1]) for j in jobs]:
            g, sc, ie = _eval_sample(params)
            Y_ganancia[i] = g
            Y_sc[i]       = sc
            Y_ie[i]       = ie
            if (i + 1) % checkpoint_every == 0:
                _save_checkpoint(i + 1)
            if (i + 1) % max(1, M // 10) == 0:
                elapsed = time.time() - t0
                eta     = elapsed / (i + 1) * (M - i - 1)
                print(f"    {i+1}/{M} ({100*(i+1)/M:.0f}%)  "
                      f"elapsed={elapsed:.0f}s  ETA={eta:.0f}s")

    elapsed = time.time() - t0
    n_valid = int(np.sum(~np.isnan(Y_ganancia)))
    print(f"  Completado: {n_valid}/{M} válidas en {elapsed:.0f}s")

    return {
        "problem":    problem,
        "X":          X,
        "Y_ganancia": Y_ganancia,
        "Y_sc":       Y_sc,
        "Y_ie":       Y_ie,
        "n_eval":     M,
        "n_valid":    n_valid,
        "elapsed":    elapsed,
        "seed":       seed,
        "n_base":     n_base,
    }


# ── Cálculo de índices Sobol ──────────────────────────────────────────────────

def compute_indices(Y_dict: dict) -> dict:
    """
    Calcula índices Sobol S1, ST y S2 para cada output.

    Parámetros
    ----------
    Y_dict : dict
        Salida de run_sobol_analysis().

    Retorna
    -------
    dict con claves "ganancia", "sc", "ie"; cada valor es el dict de SALib.analyze.
    """
    from SALib.analyze.sobol import analyze as sobol_analyze

    problem = Y_dict["problem"]
    results = {}

    for label, Y in [("ganancia", Y_dict["Y_ganancia"]),
                     ("sc",       Y_dict["Y_sc"]),
                     ("ie",       Y_dict["Y_ie"])]:
        mask   = ~np.isnan(Y)
        n_good = mask.sum()
        if n_good < len(Y) * 0.5:
            print(f"  [AVISO] {label}: solo {n_good}/{len(Y)} muestras válidas; "
                  "índices pueden ser poco fiables.")

        Y_clean = Y.copy()
        Y_clean[~mask] = np.nanmean(Y)   # imputación simple por la media

        Si = sobol_analyze(
            problem, Y_clean,
            calc_second_order=True,
            print_to_console=False,
        )
        results[label] = Si

    return results


# ── Guardar resultados ────────────────────────────────────────────────────────

def save_results(indices_dict: dict, Y_dict: dict = None,
                 path: str = None) -> str:
    """
    Guarda índices Sobol en Excel (dos hojas: S1_ST y S2).

    Parámetros
    ----------
    indices_dict : dict
        Salida de compute_indices().
    Y_dict : dict, opcional
        Salida de run_sobol_analysis(); añade hoja "Muestras_X" si se provee.
    path : str, opcional
        Ruta de salida (default: outputs/resultados_gsa.xlsx).

    Retorna
    -------
    str — ruta del archivo guardado.
    """
    if path is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        outputs_dir = os.path.join(root, "outputs")
        os.makedirs(outputs_dir, exist_ok=True)
        path = os.path.join(outputs_dir, "resultados_gsa.xlsx")

    with pd.ExcelWriter(path, engine="openpyxl") as w:
        # Hoja S1 / ST
        rows_s1st = []
        for output, Si in indices_dict.items():
            for j, name in enumerate(_PARAM_NAMES):
                rows_s1st.append({
                    "Output":    output,
                    "Parametro": name,
                    "S1":        float(Si["S1"][j]),
                    "S1_conf":   float(Si["S1_conf"][j]),
                    "ST":        float(Si["ST"][j]),
                    "ST_conf":   float(Si["ST_conf"][j]),
                })
        pd.DataFrame(rows_s1st).to_excel(w, sheet_name="S1_ST", index=False)

        # Hoja S2 (interacciones de segundo orden)
        rows_s2 = []
        for output, Si in indices_dict.items():
            if "S2" in Si and Si["S2"] is not None:
                S2     = Si["S2"]
                S2conf = Si["S2_conf"]
                for j1 in range(_N_PARAMS):
                    for j2 in range(j1 + 1, _N_PARAMS):
                        rows_s2.append({
                            "Output":   output,
                            "Param_1":  _PARAM_NAMES[j1],
                            "Param_2":  _PARAM_NAMES[j2],
                            "S2":       float(S2[j1, j2]),
                            "S2_conf":  float(S2conf[j1, j2]),
                        })
        if rows_s2:
            pd.DataFrame(rows_s2).to_excel(w, sheet_name="S2", index=False)

        # Hoja de muestras (opcional, para reproducibilidad)
        if Y_dict is not None:
            df_x = pd.DataFrame(Y_dict["X"], columns=_PARAM_NAMES)
            df_x["Y_ganancia"] = Y_dict["Y_ganancia"]
            df_x["Y_sc"]       = Y_dict["Y_sc"]
            df_x["Y_ie"]       = Y_dict["Y_ie"]
            df_x.to_excel(w, sheet_name="Muestras_X", index=False)

    return path


# ── CLI mínima ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="GSA Saltelli — Tesis Brayan López (Udenar 2026)"
    )
    parser.add_argument("--n-base",   type=int, default=64,    metavar="N")
    parser.add_argument("--seed",     type=int, default=42,    metavar="S")
    parser.add_argument("--no-parallel", action="store_true")
    parser.add_argument("--out",      default=None,            metavar="PATH")
    args = parser.parse_args()

    if args.n_base >= 256:
        ans = input(
            f"n_base={args.n_base} genera {args.n_base*(2*_N_PARAMS+2)} evaluaciones "
            "(~5 h). Confirmar [s/N]: "
        )
        if ans.strip().lower() != "s":
            print("Cancelado.")
            sys.exit(0)

    Y_dict   = run_sobol_analysis(
        n_base=args.n_base, seed=args.seed, parallel=not args.no_parallel
    )
    idx_dict = compute_indices(Y_dict)
    out_path = save_results(idx_dict, Y_dict=Y_dict, path=args.out)

    print(f"\nResultados guardados en: {out_path}")

    # Resumen S1/ST en consola
    print("\n  Índices S1 (primer orden) — top-3 por output:")
    for output, Si in idx_dict.items():
        order  = np.argsort(Si["ST"])[::-1]
        top3   = [(PARAM_BOUNDS[_PARAM_NAMES[j]]["bounds"], _PARAM_NAMES[j],
                   Si["S1"][j], Si["ST"][j])
                  for j in order[:3]]
        print(f"    {output}:")
        for _, name, s1, st in top3:
            print(f"      {name:<12}  S1={s1:.3f}  ST={st:.3f}")
