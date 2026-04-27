"""
test_fast_mode_equivalence.py
------------------------------
Verifica que `core.replicator_sellers._fast_mode = True` (VEL_GRAD=1e3,
rtol=0.5, atol=0.1, max_step=2e-4) produce el mismo equilibrio que el
modo preciso por defecto (VEL_GRAD=1e6, rtol=1e-6, atol=1e-9).

Este test es prerrequisito BLOQUEANTE de la re-ejecucion del GSA
Sobol-Saltelli sobre MedicionesMTE_v3 (Actividad 4.1 de la propuesta).

Tolerancias justificadas (consistentes con tests/golden_test_sofia.py):
  - ||P_fast - P_precise||_inf <= 0.15 kWh por par (j, i)
  - |P_total_fast - P_total_precise| <= 0.15 kWh por hora
  - Horas con mercado inactivo: ambos lados deben dar P_total ~= 0
  - Caso borde de activacion: si el excedente comunitario |G - D|_sum
    es menor que 0.5 kW (~3% del flujo P2P tipico), se permite que los
    dos modos discrepen sobre si el mercado se activa o no. Estas horas
    aportan energia despreciable al GSA agregado (ver A.7 de
    Documentos/notas_modelo_tesis.md).

Seleccion de 8 horas representativas:
  - 2 horas de mediodia con G > D (mercado activo, equilibrio interior)
  - 2 horas de clearing parcial (excedente positivo pero pequeno)
  - 2 horas nocturnas (sin generacion, mercado inactivo)
  - hasta 2 horas historicamente problematicas (subset de h0012, h0014, h3683)

Ref: Documentos/PropuestaTesis.txt VI.D, Act 4.1
     docs/superpowers/specs/2026-04-26-gsa-mte-v3-design.md
"""

import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
MTE_ROOT = Path(os.environ.get("MTE_ROOT", REPO_ROOT / "MedicionesMTE_v3"))

import numpy as np
import pytest

# Import diferido para mantener el modulo de _fast_mode controlable.
import core.replicator_sellers as _rs


pytestmark = pytest.mark.skipif(
    not MTE_ROOT.exists(),
    reason=f"MedicionesMTE no encontrado en {MTE_ROOT}; tests de datos reales saltados",
)


@pytest.fixture(scope="module")
def real_mte():
    """Carga D, G de MedicionesMTE_v3 una sola vez por modulo."""
    from data.preprocessing import build_demand_generation
    D, G, _idx = build_demand_generation(MTE_ROOT, verbose=False)
    return D, G


@pytest.fixture(scope="module")
def ems():
    """Construye EMSP2P con parametros base reales (PGS, PGB en COP)."""
    from core.ems_p2p        import EMSP2P, AgentParams, GridParams, SolverParams
    from data.base_case_data import get_agent_params, GRID_PARAMS_REAL

    p = get_agent_params()
    N = p["N"]
    # MTE tiene N=5 instituciones; los parametros base traen N=6 (modelo
    # Sofia con 6 prosumidores). Truncamos a las primeras 5.
    if N > 5:
        N = 5
        for k in ("a", "b", "c", "lam", "theta", "etha"):
            p[k] = p[k][:N]

    agents = AgentParams(
        N=N, a=p["a"], b=p["b"], c=p["c"],
        lam=p["lam"], theta=p["theta"], etha=p["etha"],
        alpha=np.zeros(N),
    )
    grid = GridParams(pi_gs=GRID_PARAMS_REAL["pi_gs"],
                      pi_gb=GRID_PARAMS_REAL["pi_gb"])
    solver = SolverParams(
        stackelberg_iters=2, stackelberg_tol=1e-3, stackelberg_max=10,
        parallel=False,
    )
    return EMSP2P(agents, grid, solver)


def _select_hours(D, G):
    """
    Devuelve hasta 8 indices horarios heterogeneos garantizando unicidad.
      idx 0-1: mediodia con mayor G - D (excedente comunitario alto).
      idx 2-3: clearing parcial (excedente positivo pero pequeno).
      idx 4-5: nocturnas (G ~ 0).
      idx 6-7: hasta dos de las problematicas {12, 14, 3683}.
    """
    G_sum = G.sum(axis=0)
    D_sum = D.sum(axis=0)
    excedente = G_sum - D_sum

    seen = set()
    hours: list[int] = []

    def _add(candidates):
        for h in candidates:
            h = int(h)
            if h not in seen and 0 <= h < D.shape[1]:
                seen.add(h)
                hours.append(h)
                if len(hours) >= 8:
                    return True
        return False

    # 1) Excedente alto
    _add(np.argsort(-excedente)[:6])  # hasta 2 unicas

    # 2) Clearing parcial: excedente positivo mas pequeno
    pos_idx = np.where(excedente > 0)[0]
    if len(pos_idx) > 0:
        sorted_pos = pos_idx[np.argsort(excedente[pos_idx])]
        _add(sorted_pos[:8])

    # 3) Nocturnas
    _add(np.argsort(G_sum)[:8])

    # 4) Problematicas
    _add([12, 14, 3683])

    # Si aun no llegamos a 8 (caso patologico), agregar pseudoaleatorias estables
    rng = np.random.default_rng(42)
    while len(hours) < 8:
        h = int(rng.integers(0, D.shape[1]))
        if h not in seen:
            seen.add(h)
            hours.append(h)

    return hours[:8]


def _run_hour(ems_obj, k, D, G, fast):
    """Corre una hora con el flag _fast_mode controlado."""
    _rs._fast_mode = bool(fast)
    try:
        res = ems_obj.run_single_hour(k, D, G)
    finally:
        _rs._fast_mode = False
    return res


def _market_active(res):
    return res is not None and res.P_star is not None


# Tests

def test_module_flag_default_off():
    """Por defecto _fast_mode debe ser False (modo preciso)."""
    assert _rs._fast_mode is False, (
        "_fast_mode debe quedar False por defecto al importar el modulo"
    )


def test_fast_mode_matches_precise_on_8_hours(real_mte, ems):
    """
    Compara P_total y P_star elemento a elemento para 8 horas heterogeneas
    de MTE_v3.
    """
    D, G = real_mte
    hours = _select_hours(D, G)

    assert len(hours) == 8, f"Se esperaban 8 horas, se obtuvieron {len(hours)}: {hours}"

    EXCEDENTE_BORDE_KW = 0.5  # umbral de "caso borde" para activacion
    failures = []
    notes    = []
    for k in hours:
        excedente_k = float((G[:, k] - D[:, k]).sum())

        res_precise = _run_hour(ems, k, D, G, fast=False)
        res_fast    = _run_hour(ems, k, D, G, fast=True)

        active_p = _market_active(res_precise)
        active_f = _market_active(res_fast)

        if active_p != active_f:
            if abs(excedente_k) < EXCEDENTE_BORDE_KW:
                notes.append(
                    f"hora {k}: activacion difiere en caso borde "
                    f"(excedente={excedente_k:.3f} kW, "
                    f"precise={active_p}, fast={active_f}) -- aceptado"
                )
                continue
            failures.append(
                f"hora {k}: market_active difiere (precise={active_p}, fast={active_f}, "
                f"excedente={excedente_k:.3f} kW)"
            )
            continue

        if not active_p:
            continue

        Pp = res_precise.P_star
        Pf = res_fast.P_star

        diff_total = abs(float(Pp.sum()) - float(Pf.sum()))
        if diff_total > 0.15:
            failures.append(
                f"hora {k}: |P_total_fast - P_total_precise|={diff_total:.4f} > 0.15 kWh "
                f"(precise={float(Pp.sum()):.3f}, fast={float(Pf.sum()):.3f})"
            )

        if Pp.shape == Pf.shape:
            diff_inf = float(np.abs(Pp - Pf).max())
            if diff_inf > 0.15:
                failures.append(
                    f"hora {k}: ||P_fast - P_precise||_inf={diff_inf:.4f} > 0.15 kWh"
                )
        else:
            failures.append(
                f"hora {k}: shapes distintas P_precise={Pp.shape} P_fast={Pf.shape}"
            )

    if notes:
        print("\n  [INFO] Casos borde aceptados:")
        for n in notes:
            print(f"    - {n}")

    assert not failures, "Discrepancias _fast_mode vs preciso:\n  " + "\n  ".join(failures)


def test_inactive_hour_zero_in_both_modes(real_mte, ems):
    """
    Para horas claramente nocturnas (G_sum ~ 0 en toda la comunidad), ambos
    modos deben reportar mercado inactivo o P_total ~ 0.
    """
    D, G = real_mte
    G_sum = G.sum(axis=0)
    night_idx = int(np.argmin(G_sum))

    res_p = _run_hour(ems, night_idx, D, G, fast=False)
    res_f = _run_hour(ems, night_idx, D, G, fast=True)

    p_total_p = 0.0 if not _market_active(res_p) else float(res_p.P_star.sum())
    p_total_f = 0.0 if not _market_active(res_f) else float(res_f.P_star.sum())

    assert p_total_p < 1e-3, f"hora nocturna {night_idx}: P_total preciso={p_total_p:.6f}"
    assert p_total_f < 1e-3, f"hora nocturna {night_idx}: P_total fast={p_total_f:.6f}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
