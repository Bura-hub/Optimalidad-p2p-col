"""
calibration_study.py
====================
Estudio de calibración de parámetros sin justificación formal.

PARÁMETROS BAJO ESTUDIO
-----------------------
1. stackelberg_iters  (actualmente=2)
   - JoinFinal.m: ODE combinada (sin loop Stackelberg explícito)
   - ConArtLatin.m: 10 iteraciones
   - Pregunta: ¿cuántas iteraciones bastan para convergencia?

2. etha (actualmente=0.1)
   - JoinFinal.m: 0.1  |  ConArtLatin.m: 1.0
   - Afecta: dinámica de compradores (compe = etha * sum_Pji)
   - Pregunta: ¿cómo afecta etha a los precios P2P y a SC/SS?

3. WI / WJ scaling (actualmente: no implementados)
   - JoinFinal.m: WI=0.08 (bloque comprador), WJ=10 (bloque vendedor)
   - Son factores de escala del sistema ODE combinado
   - Pregunta: ¿impactan la convergencia si los bloques son separados?

4. alpha (actualmente=[0.20, 0.20, 0.20, 0.20, 0.10, 0.10])
   - No existe en Chacón (suposición del modelo)
   - Pregunta: ¿qué rango de alpha maximiza SC/SS sin perjudicar costos?

CRITERIOS DE CALIBRACIÓN
------------------------
- Convergencia P_star: ||P_star(i+1) - P_star(i)||_F / ||P_star(i)||_F < ε
- Precio válido: pi_star ∈ [pi_gb, pi_gs], sin valores extremos constantes
- SC/SS estable: variación < 5% entre iteraciones consecutivas
- IE razonable: IE ∈ (-1, 0) para condiciones favorables a vendedores

USO
---
    python tests/calibration_study.py
"""

import sys, os
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import warnings
warnings.filterwarnings("ignore")

from data.base_case_data import (
    get_agent_params, get_generation_profiles, get_demand_profiles, GRID_PARAMS
)
from core.ems_p2p import AgentParams, GridParams, SolverParams, EMSP2P

# ── Perfil de referencia (24h, sintético) ────────────────────────────────────
G_BASE = get_generation_profiles()
D_BASE = get_demand_profiles()
ap_dict = get_agent_params()

def make_agents(**overrides) -> AgentParams:
    d = ap_dict.copy()
    d.update(overrides)
    return AgentParams(**d)

def make_grid() -> GridParams:
    return GridParams(**GRID_PARAMS)

def make_solver(**overrides) -> SolverParams:
    base = dict(tau=0.001, tau_buyers=0.01, t_span=(0.0, 0.01),
                n_points=500, stackelberg_iters=2, parallel=True)
    base.update(overrides)
    return SolverParams(**base)

def run_ems(agents, grid, solver):
    """Ejecuta EMS y retorna (results, G_klim, D_star)."""
    ems = EMSP2P(agents, grid, solver)
    return ems.run(D_BASE.copy(), G_BASE.copy())

def metrics_summary(results):
    """Calcula métricas promedio sobre el horizonte."""
    hours = [r for r in results if r.P_star is not None]
    if not hours:
        return {"SC": 0, "SS": 0, "IE": 0, "pi_mean": 0, "pi_spread": 0,
                "hours_active": 0}
    sc  = np.mean([r.SC for r in hours])
    ss  = np.mean([r.SS for r in hours])
    ie  = np.mean([r.IE for r in hours])
    pis = [r.pi_star for r in hours if r.pi_star is not None]
    pi_all = np.concatenate(pis) if pis else np.array([0])
    return {
        "SC": sc, "SS": ss, "IE": ie,
        "pi_mean": float(np.mean(pi_all)),
        "pi_spread": float(np.std(pi_all)),
        "hours_active": len(hours),
    }

SEP = "=" * 65


# ─────────────────────────────────────────────────────────────────────────────
# CAL-1: stackelberg_iters
# ─────────────────────────────────────────────────────────────────────────────
def calibrate_stackelberg_iters():
    print(f"\n{SEP}")
    print("CAL-1: stackelberg_iters — convergencia del juego Stackelberg")
    print(f"{SEP}")
    print(f"{'iters':>6}  {'SC':>6}  {'SS':>6}  {'IE':>7}  {'pi_mean':>8}  "
          f"{'pi_spread':>9}  {'horas':>5}")
    print("-" * 65)

    results_by_iters = {}
    for iters in [1, 2, 3, 5, 8, 10]:
        ag = make_agents()
        ag.alpha = np.zeros(6)           # sin DR para aislar el efecto
        gr = make_grid()
        sv = make_solver(stackelberg_iters=iters)
        res, _, _ = run_ems(ag, gr, sv)
        m = metrics_summary(res)
        results_by_iters[iters] = m
        print(f"  {iters:4d}  {m['SC']:6.4f}  {m['SS']:6.4f}  {m['IE']:7.4f}  "
              f"{m['pi_mean']:8.2f}  {m['pi_spread']:9.2f}  {m['hours_active']:5d}")

    # Analizar convergencia relativa entre iteraciones consecutivas
    print()
    vals = list(results_by_iters.items())
    print("  Delta SC entre iteraciones consecutivas:")
    for i in range(1, len(vals)):
        prev_n, prev_m = vals[i-1]
        curr_n, curr_m = vals[i]
        d_sc = abs(curr_m["SC"] - prev_m["SC"])
        d_ie = abs(curr_m["IE"] - prev_m["IE"])
        print(f"    {prev_n}→{curr_n}: ΔSC={d_sc:.5f}  ΔIE={d_ie:.5f}"
              + ("  ← converge" if d_sc < 0.001 and d_ie < 0.01 else ""))

    # Recomendación
    base_sc = results_by_iters[2]["SC"]
    for n, m in results_by_iters.items():
        if abs(m["SC"] - base_sc) < 0.005:
            print(f"\n  Recomendacion: stackelberg_iters >= {n} suficiente "
                  f"(ΔSC < 0.5% vs base)")
            break

    return results_by_iters


# ─────────────────────────────────────────────────────────────────────────────
# CAL-2: etha — coeficiente de competencia de compradores
# ─────────────────────────────────────────────────────────────────────────────
def calibrate_etha():
    print(f"\n{SEP}")
    print("CAL-2: etha — coeficiente de competencia entre compradores")
    print("  JoinFinal.m=0.1  |  ConArtLatin.m=1.0  |  actual=0.1")
    print(f"{SEP}")
    print(f"{'etha':>8}  {'SC':>6}  {'SS':>6}  {'IE':>7}  {'pi_mean':>8}  {'pi_spread':>9}")
    print("-" * 65)

    best = {"etha": None, "score": -np.inf}
    for etha_val in [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]:
        ag = make_agents(etha=etha_val * np.ones(6))
        ag.alpha = np.zeros(6)
        gr = make_grid()
        sv = make_solver(stackelberg_iters=2)
        res, _, _ = run_ems(ag, gr, sv)
        m = metrics_summary(res)
        score = m["SC"] + m["SS"] - abs(m["IE"])    # heurística
        marker = " ← articulo" if abs(etha_val - 1.0) < 0.01 else (
                 " ← JoinFinal" if abs(etha_val - 0.1) < 0.01 else "")
        print(f"  {etha_val:6.3f}  {m['SC']:6.4f}  {m['SS']:6.4f}  {m['IE']:7.4f}  "
              f"{m['pi_mean']:8.2f}  {m['pi_spread']:9.2f}{marker}")
        if score > best["score"]:
            best = {"etha": etha_val, "score": score}

    print(f"\n  Mejor etha (SC+SS-|IE|): {best['etha']}")
    print("  Nota: etha afecta la funcion compe en solve_buyers (dinamica real)")

    return best


# ─────────────────────────────────────────────────────────────────────────────
# CAL-3: alpha — fraccion de demanda flexible (DR Program)
# ─────────────────────────────────────────────────────────────────────────────
def calibrate_alpha():
    print(f"\n{SEP}")
    print("CAL-3: alpha — fraccion de demanda flexible (DR Program)")
    print("  Rango tipico literatura: 0.10-0.40 para prosumidores")
    print(f"{SEP}")
    print(f"{'alpha_p':>8}  {'alpha_c':>8}  {'SC_d':>7}  {'SS_d':>7}  "
          f"{'shift%':>7}  {'ΔSC_DR':>7}")
    print("-" * 68)

    for alpha_p in [0.0, 0.10, 0.20, 0.30, 0.40]:
        for alpha_c in ([0.0] if alpha_p == 0.0 else [alpha_p * 0.5]):
            ag = make_agents()
            ag.alpha = np.array([alpha_p]*4 + [alpha_c]*2)
            gr = make_grid()
            sv = make_solver(stackelberg_iters=2)

            # Sin DR (alpha=0)
            ag_nodr = make_agents()
            ag_nodr.alpha = np.zeros(6)
            res_nodr, _, _ = run_ems(ag_nodr, gr, sv)
            m_nodr = metrics_summary(res_nodr)

            # Con DR
            res, G_klim, D_star = run_ems(ag, gr, sv)
            m = metrics_summary(res)

            # Porcentaje de desplazamiento
            shift_pct = float(np.sum(np.abs(D_star - D_BASE))) / max(
                float(np.sum(D_BASE)), 1e-9) * 100.0
            dsc = m["SC"] - m_nodr["SC"]

            print(f"  {alpha_p:6.2f}   {alpha_c:6.2f}   {m['SC']:7.4f}  "
                  f"{m['SS']:7.4f}  {shift_pct:7.2f}  {dsc:+7.4f}")

    print(f"\n  Nota: alpha=0 para datos reales MTE (demanda no gestionable)")
    print(f"  Recomendacion tesis: alpha_p=0.20, alpha_c=0.10 "
          f"(supuesto conservador)")


# ─────────────────────────────────────────────────────────────────────────────
# CAL-4: WI/WJ scaling factors (diagnostico)
# ─────────────────────────────────────────────────────────────────────────────
def diagnose_wi_wj_scaling():
    print(f"\n{SEP}")
    print("CAL-4: WI/WJ scaling — diagnostico (JoinFinal.m: WI=0.08, WJ=10)")
    print(f"{SEP}")
    print("  En JoinFinal.m los subsistemas estan combinados en una ODE con:")
    print("    dX/dt = [WI * ReplicadorWiSol2; WJ * ReplicadorWjSol2]")
    print("    WI=0.08, WJ=10 => razon WJ/WI = 125")
    print()
    print("  En nuestro codigo los subsistemas son SECUENCIALES (no combinados).")
    print("  El tau diferencial (tau_buyers=0.01 vs tau=0.001, ratio=10)")
    print("  es el equivalente funcional a este escalado.")
    print()

    # Comparar tau_buyers = tau vs tau_buyers = 10*tau
    results = {}
    for tau_b_factor in [1.0, 5.0, 10.0, 20.0]:
        tau_s = 0.001
        tau_b = tau_s * tau_b_factor
        ag = make_agents()
        ag.alpha = np.zeros(6)
        gr = make_grid()
        sv = make_solver(tau=tau_s, tau_buyers=tau_b, stackelberg_iters=2)
        res, _, _ = run_ems(ag, gr, sv)
        m = metrics_summary(res)
        results[tau_b_factor] = m
        marker = " ← JoinFinal" if abs(tau_b_factor - 10.0) < 0.1 else ""
        print(f"  tau_b/tau_s={tau_b_factor:4.1f}  tau_b={tau_b:.4f}  "
              f"SC={m['SC']:.4f}  SS={m['SS']:.4f}  IE={m['IE']:+.4f}{marker}")

    print()
    print("  Conclusion: tau_buyers=0.01 (ratio=10) alinea con WJ/WI equivalente.")
    print("  El escalado WI/WJ de JoinFinal.m es implicito en la diferencia de tau.")


# ─────────────────────────────────────────────────────────────────────────────
# CAL-5: theta — solo reporting, pero documentar inconsistencia
# ─────────────────────────────────────────────────────────────────────────────
def calibrate_theta():
    print(f"\n{SEP}")
    print("CAL-5: theta — impacto en Wj/Wi (solo reporting, no dinamica RD)")
    print("  JoinFinal.m=0.5  |  ConArtLatin.m=10.0  |  actual=0.5")
    print(f"{SEP}")
    print("  theta aparece SOLO en seller_welfare() y buyer_welfare() (Excel).")
    print("  NO afecta solve_sellers() ni solve_buyers() -> no cambia SC/SS/IE.")
    print()

    for theta_val in [0.5, 1.0, 5.0, 10.0]:
        ag = make_agents(theta=theta_val * np.ones(6))
        ag.alpha = np.zeros(6)
        gr = make_grid()
        sv = make_solver(stackelberg_iters=2)
        res, _, _ = run_ems(ag, gr, sv)
        m = metrics_summary(res)
        marker = " ← articulo" if abs(theta_val - 10.0) < 0.1 else (
                 " ← JoinFinal" if abs(theta_val - 0.5) < 0.1 else "")
        print(f"  theta={theta_val:5.1f}  SC={m['SC']:.4f}  SS={m['SS']:.4f}"
              + marker)

    print()
    print("  Recomendacion: usar theta=0.5 (JoinFinal.m) para consistencia")
    print("  con el modelo dinamico. Theta=10 es del solver estatico SLSQP.")


# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN FINAL DE RECOMENDACIONES
# ─────────────────────────────────────────────────────────────────────────────
def print_summary():
    print(f"\n{'=' * 65}")
    print("RESUMEN DE RECOMENDACIONES DE CALIBRACION")
    print(f"{'=' * 65}")
    rows = [
        ("stackelberg_iters", "2 actual", "ver CAL-1",
         "Aumentar si ΔSC > 0.5% entre iter 2 y 3"),
        ("etha", "0.1 actual", "0.1 (JoinFinal) / 1.0 (articulo)",
         "Usar 0.1 para replicar JoinFinal.m"),
        ("alpha_prosumidor", "0.20", "0.10-0.40 literatura",
         "Analisis de sensibilidad SA-alpha ya implementado"),
        ("alpha_consumidor", "0.10", "0.05-0.20",
         "Conservador: 50% de alpha_prosumidor"),
        ("theta", "0.5", "solo reporting",
         "No afecta dinamica. Mantener 0.5"),
        ("WI/WJ scaling", "no impl.", "implicito en tau_buyers",
         "tau_buyers=0.01 = equivalente funcional"),
        ("pi_gs_real", "650 COP/kWh", "580-720 COP/kWh",
         "Obtener de contratos Cedenar/ESSA"),
        ("pi_gb_real", "280 COP/kWh", "250-320 COP/kWh",
         "Reemplazar con serie XM cuando disponible"),
    ]
    print(f"  {'Parametro':<22} {'Valor':<10} {'Referencia':<28} Accion")
    print(f"  {'-'*22} {'-'*10} {'-'*28} {'-'*25}")
    for name, val, ref, action in rows:
        print(f"  {name:<22} {val:<10} {ref:<28} {action}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 65)
    print("ESTUDIO DE CALIBRACION — SistemaBL v8")
    print("Perfil: datos sinteticos 24h (base Chacon et al. 2025)")
    print("=" * 65)

    calibrate_stackelberg_iters()
    calibrate_etha()
    calibrate_alpha()
    diagnose_wi_wj_scaling()
    calibrate_theta()
    print_summary()

    print(f"\n{'=' * 65}")
    print("Calibracion completa.")
    print(f"{'=' * 65}")
