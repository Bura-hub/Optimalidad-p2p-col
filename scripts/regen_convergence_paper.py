"""
scripts/regen_convergence_paper.py
==================================
Regenera fig_paper_convergence_h0512 (panel a continuo via coupled-ODE),
sin re-correr todo el pipeline de scripts/run_paper_iter.py.

Reusa la misma logica de carga de datos + parametros del paper, corre
EMSP2P.run() (~30-60 s para 744h) para obtener p2p_results, y llama a
run_convergence con use_coupled_ode=True (default tras 2026-05-04).

Uso:
  python scripts/regen_convergence_paper.py
  python scripts/regen_convergence_paper.py --month 2025-08

Genera en outputs/paper/:
  fig_paper_convergence_h{HHHH}.png/pdf/csv  (1 o 2 horas representativas)

Requiere: MTE_ROOT, data/paper_meter_config.csv (CAL-28), .venv activo.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _wrap_stdout_utf8():
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                       encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer,
                                       encoding="utf-8", errors="replace")


def _phi_factor() -> float:
    return float(os.environ.get("PV_SCALE", 1.5))


def main():
    _wrap_stdout_utf8()

    parser = argparse.ArgumentParser()
    parser.add_argument("--month", default="2025-08",
                        help="Mes en formato YYYY-MM (default: 2025-08)")
    parser.add_argument("--max-hours", type=int, default=2,
                        help="Numero de horas representativas (default: 2)")
    parser.add_argument("--n-iters", type=int, default=8,
                        help="Iteraciones Stackelberg en run_convergence")
    args = parser.parse_args()

    # Reutilizar A1 + setup del paper para no duplicar config
    from scripts.run_paper_iter import (
        homogeneizar_a_comercial,
        cargar_mte_paper, setup_parametros, correr_p2p,
    )
    from visualization.paper_figures.thesis_adapted_en import (
        fig_paper_convergence,
    )

    # ── A1: homogeneizar perfiles a comercial ───────────────────
    print("[1/5] CAL-25/A1: homogeneizando perfiles institucionales...")
    homogeneizar_a_comercial()

    # ── G: cargar mes especifico (default Aug 2025 → 744 h) ─────
    yyyy, mm = args.month.split("-")
    t_start = f"{yyyy}-{mm}-01"
    t_end_month = int(mm) + 1
    t_end_yyyy = int(yyyy)
    if t_end_month > 12:
        t_end_month = 1
        t_end_yyyy += 1
    t_end = f"{t_end_yyyy:04d}-{t_end_month:02d}-01"

    print(f"[2/5] Cargando MTE [{t_start} → {t_end}) (CAL-28 medidores)...")
    D, G, idx, agents = cargar_mte_paper(t_start, t_end)
    N, T = D.shape
    print(f"        D.shape = ({N}, {T})  agents = {agents}")

    # ── phi=1.5 case study (UPME 2030) ──────────────────────────
    phi = _phi_factor()
    G = G * phi
    print(f"[3/5] phi={phi} aplicado a G (case study UPME 2030)")

    # ── Parametros + correr EMS P2P ─────────────────────────────
    print("[4/5] Setup parametros + corriendo EMSP2P.run()...")
    p = setup_parametros(D, G, idx, agents)
    pi_gs_eff = float(np.median(p["pi_gs"]))
    pi_gb = 234.0  # piso bolsa (matching paper convention)

    t0 = time.time()
    p2p_results, G_klim, ems = correr_p2p(D, G, agents, p["b_cal"],
                                            pi_gs_eff, pi_gb)
    print(f"        run() terminado en {time.time()-t0:.1f} s")

    # ── run_convergence con coupled-ODE ─────────────────────────
    print(f"[5/5] run_convergence (n_iters={args.n_iters}, "
          f"max_hours={args.max_hours}, coupled-ODE=ON)...")
    t0 = time.time()
    conv_data = ems.run_convergence(
        D=D, G=G, G_klim=G_klim,
        p2p_results=p2p_results,
        n_iters_conv=args.n_iters,
        max_hours=args.max_hours,
        use_coupled_ode=True,
    )
    print(f"        run_convergence terminado en {time.time()-t0:.1f} s")

    if not conv_data:
        print("[ERROR] No hay horas representativas — abort")
        return 1

    for cd in conv_data:
        n_t = cd.coupled_t.shape[0] if cd.coupled_t is not None else 0
        print(f"  hora k={cd.hour}: J={len(cd.seller_ids)} I={len(cd.buyer_ids)} "
              f"coupled_t={n_t} pts")

    out_prefix = ROOT / "outputs" / "paper" / "fig_paper_convergence"
    saved = fig_paper_convergence(conv_data, agents, out_prefix)
    print()
    print("Generados:")
    for path in saved:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
