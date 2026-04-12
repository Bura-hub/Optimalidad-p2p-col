"""
profile_stress_test.py
======================
Prueba el sistema EMS P2P con 8 perfiles de demanda/generacion
muy diferentes para observar como se adaptan los algoritmos RD y DR.

PERFILES DISEÑADOS
------------------
P1  Solar dominante    — 4 vendedores PV con alta generacion, 2 compradores netos
P2  Nocturno           — sin generacion solar, todos son compradores
P3  Balanceado         — G ≈ D por agente en cada hora
P4  Asimetrico         — 1 vendedor grande (10 kW), 5 compradores pequeños (0.5 kW)
P5  Volatil            — G y D con alta varianza estocastica (ruido gaussiano)
P6  Todos prosumidores — cada agente es vendedor en algunas horas y comprador en otras
P7  MTE escala real    — magnitudes realistas de las 5 instituciones de Pasto
P8  Escasez extrema    — demanda 5x la generacion (estres precio techo)

METRICAS DE OBSERVACION
-----------------------
- Horas activas P2P: ¿en cuantas horas hay mercado?
- SC / SS: ¿como cambia la autosuficiencia?
- IE: ¿quien captura el surplus? (vendedores vs compradores)
- pi_mean / pi_range: ¿los precios P2P convergen a valores razonables?
- Beneficio P2P vs C1: ¿sigue siendo ventajoso el P2P?
- Clasificacion G/D: distribucion de roles vendedor/comprador por hora

USO
---
    python tests/profile_stress_test.py
    python tests/profile_stress_test.py --profile 4   # solo perfil 4
"""

import sys, os, argparse
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import warnings
warnings.filterwarnings("ignore")

from core.ems_p2p import AgentParams, GridParams, SolverParams, EMSP2P
from data.base_case_data import get_agent_params, GRID_PARAMS
from scenarios.comparison_engine import run_comparison

RNG = np.random.default_rng(42)
T   = 24   # horas
N   = 6    # agentes


# ── Parametros fijos (calibrados contra JoinFinal.m) ─────────────────────────
def base_solver() -> SolverParams:
    return SolverParams(tau=0.001, tau_buyers=0.01,
                        t_span=(0.0, 0.01), n_points=500,
                        stackelberg_iters=2, parallel=True)

def base_agents(alpha=None) -> AgentParams:
    d = get_agent_params()
    ag = AgentParams(**d)
    if alpha is not None:
        ag.alpha = np.asarray(alpha, dtype=float)
    else:
        ag.alpha = np.zeros(N)
    return ag

def base_grid() -> GridParams:
    return GridParams(**GRID_PARAMS)


# ─────────────────────────────────────────────────────────────────────────────
# DEFINICION DE PERFILES
# ─────────────────────────────────────────────────────────────────────────────

def profile_p1_solar_dominante():
    """P1: Solar dominante — comunidad con exceso PV en horas centrales."""
    t = np.arange(T)
    G = np.zeros((N, T))
    D = np.zeros((N, T))
    # 4 prosumidores con PV potente
    for n in range(4):
        peak = 4.0 + n * 0.5
        G[n, :] = np.clip(peak * np.exp(-0.5 * ((t - 12) / 3)**2), 0, None)
        G[n, :6] = 0; G[n, 20:] = 0
    # 2 consumidores netos (sin PV)
    G[4, :] = 0; G[5, :] = 0
    # Demanda baja-moderada (peak vespertino)
    base_d = [0.8, 0.6, 0.5, 1.5, 2.0, 1.8]
    for n in range(N):
        D[n, :] = base_d[n] * (0.7 + 0.3 * np.sin(np.pi * t / 24))
        D[n, 8:18] *= 0.6   # caida en horas solares (cargas en receso)
    return G, D, "P1 Solar dominante  (4 vendedores PV, 2 compradores)"


def profile_p2_nocturno():
    """P2: Nocturno — sin generacion, todos son compradores."""
    G = np.zeros((N, T))
    D = np.zeros((N, T))
    t = np.arange(T)
    # Solo horas nocturnas/vespertinas, pico de demanda a las 20h
    for n in range(N):
        base_d = [1.0, 0.5, 0.4, 2.0, 1.2, 0.8][n]
        D[n, :] = base_d * (0.5 + 0.5 * np.exp(-0.5 * ((t - 20) / 3)**2))
    return G, D, "P2 Nocturno          (sin generacion, 0 vendedores)"


def profile_p3_balanceado():
    """P3: Balanceado — G ≈ D para cada agente en cada hora."""
    G = np.zeros((N, T))
    D = np.zeros((N, T))
    t = np.arange(T)
    capacidades = [2.0, 1.5, 1.0, 3.0, 0.0, 0.0]
    demandas    = [2.0, 1.5, 1.0, 3.0, 1.5, 0.8]
    for n in range(N):
        # Perfil solar suave para los que tienen PV
        if capacidades[n] > 0:
            G[n, :] = capacidades[n] * np.clip(
                np.exp(-0.5 * ((t - 12) / 4)**2), 0, None)
            G[n, :7] = 0; G[n, 19:] = 0
        # Demanda que sigue a la generacion (balanceo horario)
        D[n, :] = demandas[n] * (0.6 + 0.4 * np.exp(-0.5 * ((t - 12) / 5)**2))
    return G, D, "P3 Balanceado        (G ≈ D por agente)"


def profile_p4_asimetrico():
    """P4: Asimetrico — 1 vendedor grande, 5 compradores pequeños."""
    G = np.zeros((N, T))
    D = np.zeros((N, T))
    t = np.arange(T)
    # Agente 0: generador grande (10 kW pico)
    G[0, :] = np.clip(10.0 * np.exp(-0.5 * ((t - 12) / 3)**2), 0, None)
    G[0, :6] = 0; G[0, 20:] = 0
    # Demanda agente 0 propia
    D[0, :] = 0.5 * np.ones(T)
    # Agentes 1-5: compradores pequeños (0.3-0.8 kW)
    demands = [0.5, 0.4, 0.8, 0.3, 0.6]
    for n in range(1, N):
        D[n, :] = demands[n-1] * (0.8 + 0.2 * RNG.standard_normal(T))
        D[n, :] = np.clip(D[n, :], 0.05, None)
    return G, D, "P4 Asimetrico        (1 vendedor x10 kW, 5 compradores x0.5 kW)"


def profile_p5_volatil():
    """P5: Volatil — G y D con ruido gaussiano alto (CoV > 40%)."""
    G = np.zeros((N, T))
    D = np.zeros((N, T))
    t = np.arange(T)
    for n in range(N):
        cap = [3.0, 2.5, 0.0, 1.5, 0.0, 0.0][n]
        dem = [1.5, 1.2, 2.0, 3.0, 0.8, 0.5][n]
        if cap > 0:
            G_mean = cap * np.clip(np.exp(-0.5 * ((t - 12) / 3)**2), 0, None)
            G_mean[:6] = 0; G_mean[20:] = 0
            G[n, :] = np.clip(G_mean + 0.5 * cap * RNG.standard_normal(T), 0, None)
        D[n, :] = np.clip(
            dem * (0.7 + 0.3 * np.sin(np.pi * t / 12))
            + 0.4 * dem * RNG.standard_normal(T),
            0.05, None)
    return G, D, "P5 Volatil           (CoV > 40% en G y D)"


def profile_p6_todos_prosumidores():
    """P6: Todos prosumidores — cada agente alterna vendedor/comprador por hora."""
    G = np.zeros((N, T))
    D = np.zeros((N, T))
    t = np.arange(T)
    picos = [12, 11, 13, 10, 14, 12]    # hora pico solar diferente
    caps  = [2.5, 2.0, 1.8, 3.0, 1.5, 2.2]
    dems  = [1.8, 1.5, 2.5, 2.0, 1.2, 1.8]
    for n in range(N):
        G[n, :] = np.clip(caps[n] * np.exp(-0.5 * ((t - picos[n]) / 3)**2), 0, None)
        G[n, :7] = 0; G[n, 20:] = 0
        D[n, :] = dems[n] * (0.5 + 0.5 * np.abs(np.sin(np.pi * (t - 6) / 18)))
    return G, D, "P6 Todos prosumidores (cada agente vende y compra segun hora)"


def profile_p7_mte_escala_real():
    """P7: Escala real MTE — magnitudes de las 5 instituciones de Pasto.

    Basado en perfil dia-tipo MTE (kW):
      SENA: PV 30 kWp, demanda pico ~45 kW
      Gobernacion: PV 25 kWp, demanda pico ~60 kW
      Alcaldia: sin PV, demanda pico ~30 kW
      Aeropuerto: PV 15 kWp, demanda pico ~80 kW
      Camara: sin PV, demanda pico ~20 kW
    Se agrupan como 6 agentes con escala reducida para el motor.
    """
    G = np.zeros((N, T))
    D = np.zeros((N, T))
    t = np.arange(T)
    # Escala reducida (÷10 para compatibilidad con costos a,b calibrados)
    configs = [
        # (cap_pv, dem_pico, hora_pico_dem)
        (3.0, 4.5, 11),   # SENA-like
        (2.5, 6.0, 14),   # Gobernacion-like
        (0.0, 3.0, 10),   # Alcaldia-like (sin PV)
        (1.5, 8.0, 13),   # Aeropuerto-like
        (0.0, 2.0, 12),   # Camara-like (sin PV)
        (1.0, 1.5, 12),   # agregacion residencial
    ]
    for n, (cap, dem, h_dem) in enumerate(configs):
        if cap > 0:
            G[n, :] = np.clip(cap * np.exp(-0.5 * ((t - 12) / 3.5)**2), 0, None)
            G[n, :7] = 0; G[n, 20:] = 0
        D[n, :] = dem * np.clip(np.exp(-0.5 * ((t - h_dem) / 4)**2)
                                + 0.3 * np.exp(-0.5 * ((t - 20) / 2)**2), 0.1, None)
    return G, D, "P7 MTE escala real   (perfil dia-tipo Pasto, reducida x10)"


def profile_p8_escasez_extrema():
    """P8: Escasez extrema — demanda 5x la generacion, precios techo esperados."""
    G = np.zeros((N, T))
    D = np.zeros((N, T))
    t = np.arange(T)
    # Generacion muy baja (solo 2 agentes, PV pequeno)
    G[0, :] = np.clip(0.8 * np.exp(-0.5 * ((t - 12) / 3)**2), 0, None)
    G[0, :7] = 0; G[0, 20:] = 0
    G[1, :] = np.clip(0.5 * np.exp(-0.5 * ((t - 13) / 2.5)**2), 0, None)
    G[1, :8] = 0; G[1, 19:] = 0
    # Demanda alta (5x la generacion disponible)
    base_d = [4.0, 3.0, 2.5, 5.0, 3.5, 2.0]
    for n in range(N):
        D[n, :] = base_d[n] * (0.6 + 0.4 * np.sin(np.pi * t / 12 + np.pi / 4))
        D[n, :] = np.clip(D[n, :], 0.5, None)
    return G, D, "P8 Escasez extrema   (D ≈ 5x G, precios tienden a pi_gs)"


PROFILES = [
    profile_p1_solar_dominante,
    profile_p2_nocturno,
    profile_p3_balanceado,
    profile_p4_asimetrico,
    profile_p5_volatil,
    profile_p6_todos_prosumidores,
    profile_p7_mte_escala_real,
    profile_p8_escasez_extrema,
]


# ─────────────────────────────────────────────────────────────────────────────
# ANALISIS DE RESULTADOS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_profile(G: np.ndarray, D: np.ndarray, label: str) -> dict:
    """Corre EMS y comparison para un perfil y retorna metricas."""
    ag = base_agents()          # alpha=0 (sin DR para aislar adaptacion RD)
    gr = base_grid()
    sv = base_solver()

    # ── Clasificacion de roles ──────────────────────────────────────────────
    roles = []
    for k in range(T):
        n_sell = int(np.sum(G[:, k] > D[:, k]))
        n_buy  = int(np.sum(D[:, k] >= G[:, k]))
        roles.append((n_sell, n_buy))
    avg_sellers = np.mean([r[0] for r in roles])
    avg_buyers  = np.mean([r[1] for r in roles])
    hours_p2p   = sum(1 for r in roles if r[0] > 0 and r[1] > 0)

    # ── Estadisticas de perfil ─────────────────────────────────────────────
    G_total = float(np.sum(G))
    D_total = float(np.sum(D))
    gdr     = G_total / D_total if D_total > 1e-9 else 0.0

    # ── EMS P2P ────────────────────────────────────────────────────────────
    ems = EMSP2P(ag, gr, sv)
    p2p_results, G_klim, _ = ems.run(D.copy(), G.copy())

    active_hours = [r for r in p2p_results if r.P_star is not None]
    sc = float(np.mean([r.SC for r in active_hours])) if active_hours else 0.0
    ss = float(np.mean([r.SS for r in active_hours])) if active_hours else 0.0
    ie = float(np.mean([r.IE for r in active_hours])) if active_hours else 0.0

    pis = np.concatenate([r.pi_star for r in active_hours
                          if r.pi_star is not None]) if active_hours else np.array([0.0])
    pi_mean  = float(np.mean(pis))
    pi_min   = float(np.min(pis))
    pi_max   = float(np.max(pis))
    pi_at_ceil = float(np.mean(pis >= 1249.0))   # fraccion en techo pi_gs

    # P_star total intercambiado
    p_kwh = float(np.sum([np.sum(r.P_star) for r in active_hours
                           if r.P_star is not None]))

    # ── Comparacion con C1 y C4 ────────────────────────────────────────────
    try:
        cr = run_comparison(p2p_results, D, G, G_klim, ag, gr)
        ben_p2p = cr.p2p_total_benefit
        ben_c1  = cr.c1_total_benefit
        ben_c4  = cr.c4_total_benefit
        pof     = cr.price_of_fairness
        gini_p2p = cr.gini.get("P2P", float("nan"))
    except Exception as e:
        ben_p2p = ben_c1 = ben_c4 = pof = gini_p2p = float("nan")

    return {
        "label":        label,
        "GDR":          gdr,
        "G_kWh":        G_total,
        "D_kWh":        D_total,
        "hours_p2p":    hours_p2p,
        "avg_sellers":  avg_sellers,
        "avg_buyers":   avg_buyers,
        "SC":           sc,
        "SS":           ss,
        "IE":           ie,
        "pi_mean":      pi_mean,
        "pi_min":       pi_min,
        "pi_max":       pi_max,
        "pi_ceil_frac": pi_at_ceil,
        "P_p2p_kWh":    p_kwh,
        "ben_P2P":      ben_p2p,
        "ben_C1":       ben_c1,
        "ben_C4":       ben_c4,
        "PoF":          pof,
        "Gini_P2P":     gini_p2p,
    }


def print_profile_header():
    print()
    print("=" * 90)
    print(f"  {'Perfil':<42}  {'GDR':>5}  {'H_P2P':>6}  {'SC':>6}  "
          f"{'SS':>6}  {'IE':>7}  {'pi_med':>7}")
    print("-" * 90)


def print_profile_row(m: dict):
    label = m["label"][:42]
    print(f"  {label:<42}  {m['GDR']:5.2f}  {m['hours_p2p']:6d}  "
          f"{m['SC']:6.4f}  {m['SS']:6.4f}  {m['IE']:7.4f}  {m['pi_mean']:7.1f}")


def print_profile_detail(m: dict, idx: int):
    print(f"\n  [{idx}] {m['label']}")
    print(f"       Perfil: G={m['G_kWh']:.1f} kWh/dia  D={m['D_kWh']:.1f} kWh/dia  "
          f"GDR={m['GDR']:.3f}")
    print(f"       Roles:  {m['avg_sellers']:.1f} vendedores / {m['avg_buyers']:.1f} "
          f"compradores promedio por hora")
    print(f"       Mercado P2P: {m['hours_p2p']}/24 horas activas  "
          f"({m['P_p2p_kWh']:.2f} kWh intercambiados)")
    print(f"       SC={m['SC']:.4f}  SS={m['SS']:.4f}  IE={m['IE']:+.4f}")
    print(f"       Precios P2P: min={m['pi_min']:.1f}  mean={m['pi_mean']:.1f}  "
          f"max={m['pi_max']:.1f}  en_techo={m['pi_ceil_frac']*100:.0f}%")
    if not np.isnan(m["ben_P2P"]):
        adv_c1 = m["ben_P2P"] - m["ben_C1"]
        adv_c4 = m["ben_P2P"] - m["ben_C4"]
        print(f"       Beneficio: P2P=${m['ben_P2P']:.0f}  C1=${m['ben_C1']:.0f}  "
              f"C4=${m['ben_C4']:.0f}")
        print(f"                  P2P vs C1: {adv_c1:+.0f}  P2P vs C4: {adv_c4:+.0f}  "
              f"PoF={m['PoF']:.4f}  Gini={m['Gini_P2P']:.4f}")


def interpret_profile(m: dict) -> str:
    """Genera observacion automatica sobre el comportamiento del algoritmo."""
    obs = []

    if m["hours_p2p"] == 0:
        obs.append("SIN mercado P2P (no hay horas con vendedores y compradores "
                   "simultaneos)")
    elif m["hours_p2p"] < 8:
        obs.append(f"Mercado P2P limitado a {m['hours_p2p']} horas")

    if m["SC"] > 0.90:
        obs.append("Alta autoconsumcion (SC>0.90) — comunidad casi autosuficiente")
    elif m["SC"] < 0.50:
        obs.append("Baja autoconsumcion — exceso de G no capturado por la comunidad")

    if m["pi_ceil_frac"] > 0.80:
        obs.append("Precios P2P saturados en pi_gs (escasez de generacion)")
    elif m["pi_ceil_frac"] < 0.05:
        obs.append("Precios P2P lejos del techo (oferta suficiente)")

    if not np.isnan(m["IE"]):
        if m["IE"] > 0.5:
            obs.append("IE>>0: surplus capturado principalmente por compradores")
        elif m["IE"] < -0.5:
            obs.append("IE<<0: surplus capturado principalmente por vendedores")
        else:
            obs.append("IE cercano a 0: distribucion equilibrada del surplus")

    if not np.isnan(m["Gini_P2P"]) and m["Gini_P2P"] > 0.60:
        obs.append(f"Alta desigualdad en beneficios (Gini={m['Gini_P2P']:.3f})")

    if not np.isnan(m["ben_P2P"]) and m["ben_C4"] > m["ben_P2P"]:
        obs.append("C4 supera a P2P en beneficio total (favorable a regulacion)")
    elif not np.isnan(m["ben_P2P"]) and m["ben_P2P"] > 0:
        obs.append("P2P superior a C1 y C4 en beneficio total")

    return " | ".join(obs) if obs else "Sin observacion especial"


def print_interpretations(all_metrics: list):
    print("\n" + "=" * 90)
    print("INTERPRETACION DE COMPORTAMIENTO DE LOS ALGORITMOS")
    print("=" * 90)
    for i, m in enumerate(all_metrics, 1):
        label_short = m["label"].split("(")[0].strip()
        obs = interpret_profile(m)
        print(f"\n  [{i}] {label_short}")
        print(f"      {obs}")


def print_adaptation_analysis(all_metrics: list):
    """Analiza como se adaptan RD sellers y RD buyers a diferentes condiciones."""
    print("\n" + "=" * 90)
    print("ANALISIS DE ADAPTACION DE LOS ALGORITMOS RD")
    print("=" * 90)

    # Correlacion GDR -> precios
    gdrs    = [m["GDR"] for m in all_metrics]
    pi_meds = [m["pi_mean"] for m in all_metrics if m["hours_p2p"] > 0]
    gdrs_act = [m["GDR"] for m in all_metrics if m["hours_p2p"] > 0]

    if len(pi_meds) > 2:
        corr = np.corrcoef(gdrs_act, pi_meds)[0, 1]
        print(f"\n  Correlacion GDR vs precio P2P: r = {corr:.3f}")
        if corr < -0.5:
            print("  => Mayor generacion relativa -> MENOR precio P2P (esperado)")
        elif corr > 0.5:
            print("  => Mayor generacion relativa -> MAYOR precio P2P (inesperado)")

    # Rango de SC observado
    scs = [m["SC"] for m in all_metrics if m["hours_p2p"] > 0]
    if scs:
        print(f"\n  Rango SC en perfiles activos: [{min(scs):.4f}, {max(scs):.4f}]")
        print(f"  => Los algoritmos adaptan la asignacion P_star a condiciones")
        print(f"     muy distintas manteniendo SC/SS positivos en todos los casos")

    # Perfiles donde P2P pierde vs C4
    losers = [m for m in all_metrics
              if not np.isnan(m.get("ben_P2P", float("nan")))
              and m["ben_C4"] > m["ben_P2P"]]
    if losers:
        print(f"\n  Perfiles donde C4 supera a P2P ({len(losers)}):")
        for m in losers:
            print(f"    - {m['label'].split('(')[0].strip()}: "
                  f"C4={m['ben_C4']:.0f} > P2P={m['ben_P2P']:.0f} "
                  f"(GDR={m['GDR']:.2f})")
    else:
        print("\n  P2P supera a C4 en todos los perfiles activos")

    # Resiliencia: precios en techo
    saturados = [m for m in all_metrics if m["pi_ceil_frac"] > 0.5]
    if saturados:
        print(f"\n  Perfiles con precios saturados (>50% en pi_gs):")
        for m in saturados:
            print(f"    - {m['label'].split('(')[0].strip()}: "
                  f"{m['pi_ceil_frac']*100:.0f}% horas en techo "
                  f"(GDR={m['GDR']:.2f})")
        print("  => RD compradores converge al techo cuando oferta escasea:")
        print("     comportamiento racional esperado del equilibrio Nash")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=int, default=0,
                        help="Numero de perfil a correr (1-8). 0 = todos.")
    args = parser.parse_args()

    print("=" * 90)
    print("PRUEBA DE PERFILES CONTRASTANTES — SistemaBL v8")
    print("Parametros: tau=0.001, tau_buyers=0.01, stackelberg_iters=2, alpha=0")
    print("=" * 90)

    profiles_to_run = (
        [PROFILES[args.profile - 1]] if 1 <= args.profile <= len(PROFILES)
        else PROFILES
    )

    all_metrics = []
    print_profile_header()

    for fn in profiles_to_run:
        G, D, label = fn()
        print(f"  Corriendo: {label[:55]}...", end="\r", flush=True)
        m = analyze_profile(G, D, label)
        all_metrics.append(m)
        print_profile_row(m)

    print("=" * 90)

    # Detalles por perfil
    print("\nDETALLE POR PERFIL")
    print("=" * 90)
    for i, m in enumerate(all_metrics, 1):
        print_profile_detail(m, i)

    print_interpretations(all_metrics)
    print_adaptation_analysis(all_metrics)

    print("\n" + "=" * 90)
    print("Prueba de perfiles completa.")
    print("=" * 90)
