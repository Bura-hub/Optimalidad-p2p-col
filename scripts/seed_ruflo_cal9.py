"""Sembrado del namespace 'calibracion' con la decision CAL-9.

Almacena:
- cal9-decision: el ADR-009 en forma compacta (rule + why + how to apply)
- cal9-context-regulatorio: motivacion CREG 174 y CREG 101 072
- cal9-cu-mensual-oficial-nt2: tabla de CU mensual para referencia rapida
- cal9-cu-mensual-comercial-nt2: idem para comercial
- cal9-helper-as-pi-gs-array: contrato del helper extendido
- cal9-archivos-criticos: lista de archivos modificados
- cal9-tests: bateria de tests CAL-9 y baseline pre/post

Uso:
  python scripts/seed_ruflo_cal9.py

Idempotente.
"""
from __future__ import annotations

import subprocess
import sys

ENTRIES = [
    (
        "cal9-decision",
        "alta",
        "ADR-009 (CAL-9): pi_gs pasa de vector (N,) a matriz (N, T) en C1-C4 y "
        "en analisis. Each hour liquida con el CU del mes que la contiene. "
        "Why: Res. CREG 174/2021 y 101 072/2025 liquidan mensualmente; el "
        "spread CU oficial NT2 766.80-816.98 (~6,5%) borrado por el escalar "
        "no es regulatoriamente defensible. How to apply: usar "
        "data.cedenar_tariff.pi_gs_per_agent_hourly(names, idx) en "
        "main_simulation.py y propagar a run_comparison via pi_gs_arg. "
        "Ver docs/adr/0009-cal9-pi-gs-temporal.md."
    ),
    (
        "cal9-context-regulatorio",
        "alta",
        "Res. CREG 174/2021 (AGPE): liquidacion mensual con permutacion del "
        "excedente neto a precio bolsa promedio del periodo; el CU del mes "
        "valoriza creditos y permutacion. Res. CREG 101 072/2025 (AGRC): "
        "PDE distribuye creditos cada mes calendario. Por tanto pi_gs debe "
        "ser una funcion de tiempo, no un escalar de horizonte."
    ),
    (
        "cal9-cu-mensual-oficial-nt2",
        "alta",
        "CU oficial NT2 cedenar (COP/kWh) por mes en data/tarifas_cedenar_mensual.csv: "
        "2025-04 794.62 | 2025-05 777.17 | 2025-06 802.27 | 2025-07 814.91 | "
        "2025-08 816.98 | 2025-09 797.94 | 2025-10 790.07 | 2025-11 793.65 | "
        "2025-12 773.52 | 2026-01 766.80 | 2026-02 774.53 | 2026-03 795.15 | "
        "2026-04 799.16. Aplicada a Udenar y HUDN."
    ),
    (
        "cal9-cu-mensual-comercial-nt2",
        "alta",
        "CU comercial NT2 cedenar (COP/kWh) por mes (oficial * 1.20 contribucion 20% "
        "Ley 142/1994): 2025-04 953.55 | 2025-05 932.60 | 2025-06 962.73 | "
        "2025-07 977.89 | 2025-08 980.38 | 2025-09 957.53 | 2025-10 948.08 | "
        "2025-11 952.39 | 2025-12 928.22 | 2026-01 920.16 | 2026-02 929.43 | "
        "2026-03 954.18 | 2026-04 958.99. Aplicada a Mariana, UCC, Cesmag."
    ),
    (
        "cal9-helper-as-pi-gs-array",
        "alta",
        "scenarios._pi_gs.as_pi_gs_array(pi_gs, N, T) -> ndarray (N, T). "
        "Acepta float -> np.full, (N,) -> broadcast en t, (T,) -> broadcast en n, "
        "(N, T) -> as-is. Mantenemos as_pi_gs_vector(pi_gs, N) como adaptador "
        "retro-compatible que colapsa la matriz al promedio temporal."
    ),
    (
        "cal9-archivos-criticos",
        "alta",
        "CAL-9 modifica: scenarios/_pi_gs.py (helper), scenarios/scenario_c1..c4 "
        "(indexacion temporal), scenarios/comparison_engine.py (matriz N,T y "
        "_p2p_monetary_benefit por posicion), analysis/feasibility.py "
        "(slicing por mask), analysis/monthly_report.py (slicing por mes), "
        "main_simulation.py (wiring full/single_day). Crea: "
        "tests/test_pi_gs_temporal.py (10 casos), scripts/cal9_delta_report.py, "
        "docs/adr/0009-cal9-pi-gs-temporal.md."
    ),
    (
        "cal9-tests",
        "alta",
        "Tests post-CAL-9: 33 baseline + 10 CAL-9 = 43 verdes. Casos clave: "
        "test_c1_scalar_vs_constant_matrix (equivalencia), "
        "test_c1_matrix_per_month_differs_from_scalar (delta esperado), "
        "test_c1 split-sum equivale a matriz mes a mes. Smoke tests: "
        "sintetico 13s, --data real perfil diario 22s, --full ~52min "
        "(corriendo en background al cierre de sesion 2026-04-30)."
    ),
    (
        "cal9-pi-gs-arg-modes",
        "alta",
        "Wiring main_simulation.py:213 segun modo: --full -> "
        "pi_gs_per_agent_hourly(names, index_full) (N, T_full); --day -> "
        "pi_gs_per_agent_hourly(names, idx_day) (N, 24); perfil diario "
        "promedio -> pi_gs_per_agent (N,) CAL-8 (representa promedio "
        "del horizonte). Sintetico -> grid_params['pi_gs'] escalar."
    ),
    (
        "cal9-p2p-indexacion-posicion",
        "alta",
        "_p2p_monetary_benefit y _p2p_flow_breakdown indexan la matriz por "
        "posicion en la lista (enumerate), no por r.k. Esto permite reusar "
        "la funcion sobre slices arbitrarios siempre que el caller alinee "
        "(results, D) por construccion (run_comparison: full; "
        "_compute_daily_series: 24h slice)."
    ),
]


def store(key: str, evidence: str, summary: str,
          namespace: str = "calibracion") -> bool:
    flat = summary.replace("\n", " | ").replace('"', "'")
    value = f"evidence: {evidence} | {flat}"
    cmd = (
        f'npx @claude-flow/cli@latest memory store '
        f'--key "{key}" --value "{value}" --namespace "{namespace}"'
    )
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", shell=True,
    )
    ok = proc.returncode == 0 and "Data stored successfully" in (proc.stdout + proc.stderr)
    if not ok:
        print(f"  FAIL {key}: {proc.stderr.strip()[:200]}")
    return ok


def main() -> int:
    ok = 0
    for key, evidence, summary in ENTRIES:
        print(f"[cal9] storing {key}...")
        if store(key, evidence, summary):
            ok += 1
    print(f"[cal9] hecho: {ok}/{len(ENTRIES)} entradas en namespace 'calibracion'")
    return 0 if ok == len(ENTRIES) else 1


if __name__ == "__main__":
    sys.exit(main())
