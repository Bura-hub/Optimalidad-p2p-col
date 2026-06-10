"""
generate_reference_oracle.py — Oráculo SLSQP multi-hora para el smoke C1 (ADR-0038)
====================================================================================
Extiende el oráculo estático de `Documentos/copy/generate_reference_h14.py`
(Bienestar6p.py, Chacón et al. 2025) de la hora 14 a:

  (a) TODAS las horas activas del caso sintético 24h
      → Documentos/copy/reference_syn24.json
  (b) una muestra estratificada de horas activas del horizonte real MTE
      → Documentos/copy/reference_real_sample.json

Para (b), nota de escala (plan 2026-06-10 §2a): la formulación log-precio
no es invariante de escala. Los precios reales del juego (π_gs_eff≈906,
π_gb=280) están en el MISMO orden que el caso sintético (1250/114), así que
el default corre SIN normalizar; `--normalize` divide precios por π_gb como
alternativa si SLSQP no converge. Degradación aprobada: si falla >25 % de
la muestra, el JSON se marca `"degraded": true` y el smoke C1-real reporta
INFO en vez de HARD.

Uso:
    python scripts/generate_reference_oracle.py            # sintético
    python scripts/generate_reference_oracle.py --real     # + muestra real (COB-M1)
    python scripts/generate_reference_oracle.py --real --paper-meters   # COB-M3
    python scripts/generate_reference_oracle.py --real --normalize

Salida: JSONs arriba + resumen en stdout. Exit 0 siempre que el sintético
genere ≥1 hora (el real puede degradar sin fallar).
"""
import sys, os, json, argparse, warnings
import importlib.util
warnings.filterwarnings("ignore")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")

import numpy as np

from core.market_prep import compute_generation_limit, classify_agents
from data.base_case_data import (
    get_generation_profiles, get_demand_profiles, get_agent_params,
    PGS, PGB, PGB_COP,
)

# ── Importar el módulo del oráculo h14 (carpeta sin __init__, nombre 'copy') ─
_oracle_path = os.path.join(ROOT, "Documentos", "copy",
                            "generate_reference_h14.py")
_spec = importlib.util.spec_from_file_location("oracle_h14", _oracle_path)
oracle_h14 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oracle_h14)

VOLUME_MIN_KWH = 0.01    # umbral de hora "activa" (consistente con smoke C5)


def _solve_hour_oracle(Gj, Di, Gi, a_j, b_j, theta_j, lamda_j,
                       theta_i, lamda_i, etha_i, pgs, pgb,
                       max_outer=10, verbose=False):
    """Loop Stackelberg estático del oráculo (idéntico a generate() de h14).

    Retorna (ref: dict, ok: bool). ok=False si scipy no produjo una solución
    factible (errores de cierre > 1% del volumen).
    """
    J, I = len(Gj), len(Di)
    pii = np.full(I, pgb)
    Pij = (np.tile(Di / J, (J, 1)) if np.sum(Gj) >= np.sum(Di)
           else np.tile(Gj / I, (I, 1)).T)
    Pij = np.clip(Pij, 1e-10, None)

    W_prev = -np.inf
    W_total = np.nan
    try:
        for it in range(max_outer):
            Pij_new, Wj = oracle_h14._solve_sellers(
                pii, Gj, Di, a_j, b_j, theta_j, lamda_j, J, I, pgs, pgb)
            pii_new, Wi = oracle_h14._solve_buyers(
                Pij_new, Gi, etha_i, lamda_i, theta_i, J, I, pgs, pgb,
                a_j, b_j)
            W_total = Wj + Wi
            Pij = Pij_new
            pii = np.clip(pii_new, pgb, pgs)
            if W_total >= W_prev and it >= 2:
                break
            W_prev = W_total
    except Exception as exc:                                # noqa: BLE001
        return {"error": str(exc)}, False

    if not (np.isfinite(Pij).all() and np.isfinite(pii).all()
            and np.isfinite(W_total)):
        return {"error": "NaN/Inf en la solución"}, False

    # Factibilidad: cierre del lado corto dentro del 1% del volumen
    volume = float(min(np.sum(Gj), np.sum(Di)))
    closure_err = abs(float(Pij.sum()) - volume)
    ok = closure_err <= max(0.01 * volume, 1e-6)

    ref = {
        "G_net_j": Gj.tolist(), "D_net_i": Di.tolist(),
        "P_ij": Pij.tolist(), "pi_i": pii.tolist(),
        "P_total": float(Pij.sum()), "pi_mean": float(pii.mean()),
        "W_total": float(W_total), "closure_err": closure_err,
        "volume_short_side": volume,
    }
    return ref, ok


def generate_synthetic(verbose=True):
    G = get_generation_profiles()
    D = get_demand_profiles()
    p = get_agent_params()
    T = G.shape[1]

    hours, skipped = {}, []
    for k in range(T):
        G_klim = compute_generation_limit(G[:, k], p["a"], p["b"], p["c"], PGS)
        _, sids, bids = classify_agents(G_klim, D[:, k])
        if not sids or not bids:
            skipped.append(k)
            continue
        Gj = np.array([G_klim[j] - D[j, k] for j in sids])
        Di = np.array([D[i, k] - G_klim[i] for i in bids])
        if min(float(np.sum(Gj)), float(np.sum(Di))) < VOLUME_MIN_KWH:
            skipped.append(k)
            continue
        ref, ok = _solve_hour_oracle(
            Gj, Di, G_klim[bids],
            p["a"][sids], p["b"][sids], p["theta"][sids], p["lam"][sids],
            p["theta"][bids], p["lam"][bids], p["etha"][bids],
            float(PGS), float(PGB))
        ref.update({"seller_ids": [int(s) for s in sids],
                    "buyer_ids": [int(b) for b in bids],
                    "ok": ok})
        hours[str(k)] = ref
        if verbose:
            tag = "OK " if ok else "FAIL"
            print(f"  syn h{k:02d} [{tag}] J={len(sids)} I={len(bids)} "
                  f"P_total={ref.get('P_total', float('nan')):.4f} "
                  f"pi_mean={ref.get('pi_mean', float('nan')):.1f}")

    n_ok = sum(1 for r in hours.values() if r.get("ok"))
    out = {"meta": {"case": "synthetic_24h", "pgs": float(PGS),
                    "pgb": float(PGB), "n_active": len(hours),
                    "n_ok": n_ok, "skipped_hours": skipped},
           "hours": hours}
    path = os.path.join(ROOT, "Documentos", "copy", "reference_syn24.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"\n  Sintético: {n_ok}/{len(hours)} horas activas OK → {path}")
    return out


def generate_real_sample(paper_meters=False, n_sample=24, normalize=False,
                         seed=42, verbose=True):
    import pandas as pd
    from data.xm_data_loader import MTEDataLoader
    from data.cedenar_tariff import community_effective_pi_gs
    from data.xm_prices import get_b_for_real_data

    cob = "COB-M3" if paper_meters else "COB-M1"
    mte_root = os.environ.get("MTE_ROOT",
                              os.path.join(ROOT, "MedicionesMTE_v3"))
    demand_cfg = None
    if paper_meters:
        from data.preprocessing import PAPER_METER_DEMAND_CONFIG
        demand_cfg = PAPER_METER_DEMAND_CONFIG
    loader = MTEDataLoader(mte_root, demand_config=demand_cfg)
    D, G, index_full = loader.load(verbose=False)
    N, T = D.shape
    names = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"][:N]

    pi_gs_eff = community_effective_pi_gs(
        names, index_full[0], index_full[-1] + pd.Timedelta(hours=1),
        weights=D.mean(axis=1))
    pgb = float(PGB_COP)
    b_cal = get_b_for_real_data(N, names)
    a = np.zeros(N); c = np.zeros(N)
    lam = np.full(N, 100.0); theta = np.full(N, 0.5); etha = np.full(N, 0.1)

    # Horas activas con su volumen del lado corto
    actives = []
    for k in range(T):
        G_klim = compute_generation_limit(G[:, k], a, b_cal, c, pi_gs_eff)
        _, sids, bids = classify_agents(G_klim, D[:, k])
        if not sids or not bids:
            continue
        Gj = np.array([G_klim[j] - D[j, k] for j in sids])
        Di = np.array([D[i, k] - G_klim[i] for i in bids])
        vol = min(float(np.sum(Gj)), float(np.sum(Di)))
        if vol >= VOLUME_MIN_KWH:
            actives.append((k, vol))
    if not actives:
        print(f"  [real {cob}] sin horas activas — nada que generar")
        return None

    # Muestra estratificada por volumen: terciles bajo/medio/alto
    actives.sort(key=lambda x: x[1])
    n3 = max(1, n_sample // 3)
    terc = np.array_split(np.array(actives, dtype=object), 3)
    rng = np.random.default_rng(seed)
    sample = []
    for t_arr in terc:
        idx = rng.choice(len(t_arr), size=min(n3, len(t_arr)), replace=False)
        sample.extend(int(t_arr[i][0]) for i in idx)
    sample = sorted(set(sample))

    scale = pgb if normalize else 1.0
    pgs_o, pgb_o = float(pi_gs_eff) / scale, pgb / scale

    hours, n_fail = {}, 0
    for k in sample:
        G_klim = compute_generation_limit(G[:, k], a, b_cal, c, pi_gs_eff)
        _, sids, bids = classify_agents(G_klim, D[:, k])
        Gj = np.array([G_klim[j] - D[j, k] for j in sids])
        Di = np.array([D[i, k] - G_klim[i] for i in bids])
        ref, ok = _solve_hour_oracle(
            Gj, Di, G_klim[bids],
            a[sids], b_cal[sids] / scale, theta[sids], lam[sids],
            theta[bids], lam[bids], etha[bids],
            pgs_o, pgb_o)
        ref.update({"seller_ids": [int(s) for s in sids],
                    "buyer_ids": [int(b) for b in bids], "ok": ok})
        hours[str(k)] = ref
        n_fail += 0 if ok else 1
        if verbose:
            tag = "OK " if ok else "FAIL"
            print(f"  real h{k:05d} [{tag}] J={len(sids)} I={len(bids)} "
                  f"P_total={ref.get('P_total', float('nan')):.4f}")

    degraded = n_fail > 0.25 * len(hours)
    out = {"meta": {"case": f"real_{cob}", "pgs": pgs_o, "pgb": pgb_o,
                    "normalized": bool(normalize), "scale": scale,
                    "n_sample": len(hours), "n_fail": n_fail,
                    "degraded": bool(degraded), "seed": seed},
           "hours": hours}
    path = os.path.join(ROOT, "Documentos", "copy",
                        "reference_real_sample.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    status = "DEGRADADO → C1-real será INFO" if degraded else "OK"
    print(f"\n  Real {cob}: {len(hours) - n_fail}/{len(hours)} OK "
          f"[{status}] → {path}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--real", action="store_true",
                    help="genera también la muestra real")
    ap.add_argument("--paper-meters", action="store_true",
                    help="cobertura COB-M3 para la muestra real")
    ap.add_argument("--normalize", action="store_true",
                    help="normaliza precios por pi_gb en el oráculo real")
    ap.add_argument("--n-sample", type=int, default=24)
    args = ap.parse_args()

    print("=== Oráculo SLSQP multi-hora (ADR-0038, smoke C1) ===")
    syn = generate_synthetic()
    if args.real:
        generate_real_sample(paper_meters=args.paper_meters,
                             n_sample=args.n_sample,
                             normalize=args.normalize)
    return 0 if syn["meta"]["n_ok"] >= 1 else 1


if __name__ == "__main__":
    sys.exit(main())
