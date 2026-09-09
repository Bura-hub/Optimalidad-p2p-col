"""
main_simulation.py  — Tesis Brayan López, Udenar 2026

Implementa el EMS completo de Chacón et al. (2025):
  Algoritmo 1: G_klim + DR program (D* = D cuando alpha=0 para datos reales)
  Algoritmos 2-3: RD + Stackelberg (vendedores y compradores)

Modos:
  python main_simulation.py                              # datos sintéticos (24h)
  python main_simulation.py --data real                  # datos MTE, perfil diario promedio (24h)
  python main_simulation.py --day YYYY-MM-DD             # datos MTE, un día real específico (24h)
  python main_simulation.py --day YYYY-MM-DD --analysis  # día específico + sensibilidad/factibilidad
  python main_simulation.py --data real --full           # datos MTE, 6144h completas
  python main_simulation.py --data real --analysis       # perfil diario + sensibilidad y factibilidad
  python main_simulation.py --data real --analysis --full  # todo, horizonte completo
  python main_simulation.py --gsa [--n-base N]           # análisis de sensibilidad global Sobol/Saltelli

Notas:
  --day implica --data real y horizonte de 24h (no requiere --data real explícito).
  En los modos de 24h (sintético, perfil diario o --day) NO se genera reporte
  mensual ni series diarias para bootstrap (requieren T>=48h con --full).
"""
import sys, os, time, argparse, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows: forzar UTF-8 en stdout para soportar caracteres Unicode (█, etc.)
# CAL-39: reconfigure() EN SITIO en vez de reemplazar sys.stdout — el
# reemplazo dejaba huérfano al wrapper original y su buffer compartido se
# cerraba por GC, matando a quien conservara la referencia vieja (pytest:
# "I/O operation on closed file"; descubierto 2026-06-10 al correr tests/
# entero de una sola pasada).
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import numpy as np
import pandas as pd

from core.ems_p2p  import EMSP2P, AgentParams, GridParams, SolverParams
from scenarios     import (run_comparison, print_comparison_report,
                           print_flow_breakdown, print_welfare_decomposition)
from data.base_case_data import (
    get_generation_profiles, get_demand_profiles,
    get_agent_params, get_pde_weights,
    GRID_PARAMS, GRID_PARAMS_REAL, PGS, PGB, PGS_COP, PGB_COP,
)
from data.xm_prices import get_pi_bolsa, get_b_for_real_data
from data.cedenar_tariff import (
    community_effective_pi_gs, cvm_per_agent_hourly,
    effective_pi_gs_per_agent, pi_gs_per_agent_hourly,
    g_component_per_agent_hourly,                     # CAL-12 (ADR-0012)
    g_plus_commercialization_per_agent_hourly,        # CAL-13 (ADR-0013)
    cu_components_per_agent_hourly,                   # CAL-16 (ADR-0016)
    mem_costs_per_agent_hourly,                       # CAL-16 (ADR-0016)
    tariff_coverage, INSTITUTION_PROFILE,
)


def _procesos_pedidos(args):
    """Cuantos procesos se piden: la bandera manda, el entorno respalda.

    C-169. El lanzador del servidor calcula su cuenta de nucleos con cuidado
    —esquivando una trampa por la que `nproc` obedece a la variable de hilos y
    devolvia uno— y la exporta. Sin esta lectura esa cuenta **no llegaba al
    mercado**, y el ejecutor abria los procesos por su cuenta con un numero que
    no respeta la afinidad.

    Con None, el motor toma todos los nucleos utiles.
    """
    import os as _os

    if getattr(args, "procesos", None):
        return int(args.procesos)
    v = _os.environ.get("PROCS", "").strip()
    if v.isdigit() and int(v) > 0:
        print(f"    [C-169] procesos tomados del entorno: {v}")
        return int(v)
    return None


def main(use_real_data=False, full_horizon=False, run_analysis=False,
         single_day: str = None, paper_meters: bool = False,
         include_c5: bool = False, out_dir: str = None,
         paso: float = 1.0, desde: str = None, hasta: str = None,
         metodo: str = "alternado", t_span_acoplado: float = 0.05,
         almacen: str = None,
         procesos: int = None,
         exencion_contribucion: bool = False,
         buyer_competition: str = "aggregate"):
    t_total_start = time.time()
    print("\n" + "█"*65)
    print("  TESIS: Validación Regulatoria de Mercados P2P en Colombia")
    print("  Brayan S. Lopez-Mendez — Udenar, 2026  [SIN DR]")
    print("█"*65)

    # ── 1. Cargar datos ──────────────────────────────────────────────────
    if use_real_data:
        from data.xm_data_loader import (
            MTEDataLoader, validate_load, print_validation_report,
            daily_profiles,
        )
        mte_root = os.environ.get(
            "MTE_ROOT",
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "MedicionesMTE_v3"),
        )
        print(f"\n[1/5] Cargando datos empíricos MTE...")
        demand_cfg = None
        if paper_meters:
            # CAL-36 (ADR-0036): escenario M3 sub-medidores (cobertura ~89%),
            # mismos medidores del paper CAL-28, pipeline de limpieza de tesis.
            from data.preprocessing import PAPER_METER_DEMAND_CONFIG
            demand_cfg = PAPER_METER_DEMAND_CONFIG
            print("    [CAL-36] Escenario M3 sub-medidores (paper meters): "
                  "demanda = circuito PV, no campus completo")
        loader = MTEDataLoader(mte_root, demand_config=demand_cfg)
        D_full, G_full, index_full = loader.load(verbose=True, paso=paso)
        # CAL-46: ventana acotada de la sonda. Recorta antes que nada mas para
        # que la tarifa, la bolsa y las etiquetas de mes salgan del mismo
        # horizonte que las series.
        if desde or hasta:
            from data.xm_data_loader import slice_horizon
            _d = desde or index_full[0].strftime("%Y-%m-%d")
            _h = hasta or (index_full[-1] + pd.Timedelta(hours=paso)
                           ).strftime("%Y-%m-%d")
            D_full, G_full, index_full = slice_horizon(
                D_full, G_full, index_full, _d, _h)
            print(f"    [CAL-46] Ventana {_d} -> {_h}: "
                  f"{D_full.shape[1]} pasos de {paso * 60:.0f} min")
        print_validation_report(validate_load(D_full, G_full, index_full))

        # CAL-47: la clase tarifaria se decide ANTES de armar nada, porque
        # de ella cuelgan el escalar comunitario y la matriz de liquidacion.
        if exencion_contribucion:
            from data.cedenar_tariff import aplicar_regimen_no_regulado
            aplicar_regimen_no_regulado(True)
            print("    [CAL-47] Las cinco como usuarios NO REGULADOS: la tabla "
                  "publicada es referencia, no su tarifa, y se lee la fila sin "
                  "contribucion; comparten costo unitario y por tanto techo")

        from scenarios.scenario_c4_creg101072 import compute_pde_weights
        pde = compute_pde_weights(np.maximum(G_full.mean(axis=1), 0))
        cap = np.maximum(G_full.mean(axis=1), 0)
        N   = D_full.shape[0]

        agent_names = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"][:N]
        currency    = "COP"

        # ── pi_gs Cedenar (CAL-9): matriz (N, T) mes a mes en C1-C4 ──────
        # El escalar `pi_gs_eff` y el vector `pi_gs_per_agent` se conservan
        # SOLO como diagnóstico informativo (resumen comunicacional del
        # promedio del horizonte) y para análisis auxiliares con escalar
        # (sensibilidad SA-3, sub-períodos, plot_c1_vs_c4). Lo que entra al
        # settlement de C1-C4 es `pi_gs_arg` (línea ~213 abajo): matriz
        # `(N, T)` vía `pi_gs_per_agent_hourly`. Ver §CAL-9 y ADR-0009.
        t_start_cal = index_full[0]
        t_end_cal   = index_full[-1] + pd.Timedelta(hours=1)
        demand_weights = D_full.mean(axis=1)
        pi_gs_eff = community_effective_pi_gs(
            agent_names, t_start_cal, t_end_cal, weights=demand_weights,
        )
        pi_gs_per_agent = effective_pi_gs_per_agent(
            agent_names, t_start_cal, t_end_cal,
        )
        grid_params = {**GRID_PARAMS_REAL, "pi_gs": pi_gs_eff}

        # Parámetro b calibrado por institución (Actividad 1.2)
        b_cal = get_b_for_real_data(N, agent_names)

        if single_day:
            from data.xm_data_loader import slice_horizon
            day_start = single_day
            day_end   = (pd.Timestamp(single_day) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            D, G, idx_day = slice_horizon(D_full, G_full, index_full,
                                          day_start, day_end)
            T = D.shape[1]
            month_labels = None   # período único para C1
            dow = pd.Timestamp(single_day).day_name()
            print(f"\n    Modo: DÍA ESPECÍFICO  {single_day} ({dow})  N={N}  T={T}h")
        elif full_horizon:
            D, G = D_full, G_full
            T    = D.shape[1]
            # Etiquetas de período de facturación (YYYYMM) para C1 (CREG 174)
            month_labels = np.array([ts.year * 100 + ts.month
                                     for ts in index_full], dtype=int)
            print(f"\n    Modo: COMPLETO  N={N}  T={T} pasos "
                  f"({T * paso / 24:.0f} días, paso {paso * 60:.0f} min)")
            n_periods = len(set(month_labels))
            print(f"    Períodos de facturación C1: {n_periods} meses")
        else:
            D, G = daily_profiles(D_full, G_full, index_full)
            T    = 24
            month_labels = None   # perfil promedio → un único período
            print(f"\n    Modo: PERFIL DIARIO PROMEDIO  N={N}  T=24h")
            print(f"    Basado en {D_full.shape[1]} horas reales")
            print(f"    Para horizonte completo: --full")

        # Precios de bolsa: real si hay CSV, sintético si no.
        # CAL-17 Sprint 1.1b (2026-05-02): se pasa t_start/t_end derivados
        # del index MTE para alinear pi_bolsa por fecha con D y G en los
        # modos --full y --day. Antes el cache se cargaba con default
        # t_start=2025-07-01 y los 6144 valores indexados [0..T-1] quedaban
        # desplazados ~88 dias respecto al horizonte MTE (abr-2025 a
        # dic-2025). Ver ADR-0017 post-script Sprint 1.1b.
        xm_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "data", "xm_precios_bolsa.csv")
        if full_horizon:
            t_start_xm = index_full[0].strftime("%Y-%m-%d")
            t_end_xm = (index_full[-1]
                        + pd.Timedelta(hours=paso)).strftime("%Y-%m-%d")
            pi_bolsa = get_pi_bolsa(
                T,
                t_start=t_start_xm,
                t_end=t_end_xm,
                csv_path=xm_csv if os.path.exists(xm_csv) else None,
                scenario="2025_normal",
                dt=paso,          # CAL-46
            )
        elif single_day:
            t_start_xm = idx_day[0].strftime("%Y-%m-%d")
            t_end_xm = (idx_day[-1] + pd.Timedelta(hours=1)).strftime("%Y-%m-%d")
            pi_bolsa = get_pi_bolsa(
                T,
                t_start=t_start_xm,
                t_end=t_end_xm,
                csv_path=xm_csv if os.path.exists(xm_csv) else None,
                scenario="2025_normal",
            )
        else:
            # Modo perfil diario promedio (T=24): mantiene defaults para no
            # forzar alineacion fecha-a-fecha de un perfil agregado.
            pi_bolsa = get_pi_bolsa(
                T,
                csv_path=xm_csv if os.path.exists(xm_csv) else None,
                scenario="2025_normal",
            )
        cov = tariff_coverage(t_start_cal, t_end_cal)
        if cov["meses_faltantes"]:
            print(f"    AVISO: {len(cov['meses_faltantes'])} mes(es) sin "
                  f"PDF Cedenar, fallback {650:.0f} COP/kWh aplicado en: "
                  f"{', '.join(cov['meses_faltantes'])}")
        print(f"    PGS Cedenar — comunitario (informativo, NO entra al "
              f"settlement): {pi_gs_eff:.0f} COP/kWh  [legacy={PGS_COP:.0f}]")
        # CAL-9: lo que liquida es la matriz (N, T) mes a mes. Imprimimos
        # el rango por agente para evidenciar la variabilidad temporal.
        if full_horizon or single_day:
            idx_for_diag = index_full if full_horizon else idx_day
            tariff_matrix_diag = pi_gs_per_agent_hourly(agent_names, idx_for_diag)
            mode_tag = "matriz mes a mes (N×T)"
        else:
            # Perfil diario promedio: representa el promedio del horizonte → usar vector CAL-8
            tariff_matrix_diag = np.broadcast_to(
                pi_gs_per_agent[:, None], (N, T),
            )
            mode_tag = "vector CAL-8 (perfil diario, sin variabilidad mensual)"
        print(f"    PGS al settlement → {mode_tag}  "
              f"cobertura {len(cov['meses_cargados'])}/{len(cov['meses_horizonte'])} meses")
        print(f"      {'Institución':<10} {'Categoría':<10} {'NT':<4} "
              f"{'min':>5} {'max':>5} {'media':>6}  COP/kWh")
        for n, name in enumerate(agent_names):
            prof = INSTITUTION_PROFILE.get(name)
            cat  = prof.categoria if prof else "(sin perfil)"
            nt   = f"NT{prof.nivel_tension}" if prof else "—"
            row  = tariff_matrix_diag[n]
            print(f"      {name:<10} {cat:<10} {nt:<4} "
                  f"{row.min():>5.0f} {row.max():>5.0f} {row.mean():>6.0f}")
        # H-50: una serie de bolsa no numerica atraviesa la corrida entera sin
        # que nada falle y produce una tabla comparativa de valores no
        # numericos con codigo de salida cero. Paso el 2026-09-07 en modo dia,
        # porque el techo de la CREG 101 066 no tenia fila para ese mes y el
        # minimo lo propagaba. Se comprueba aqui, que es donde se sabe.
        _b = np.asarray(pi_bolsa, dtype=float)
        if not np.all(np.isfinite(_b)):
            raise ValueError(
                f"La serie de bolsa tiene {int(np.sum(~np.isfinite(_b)))} de "
                f"{_b.size} valores no numericos. Seguir produciria una tabla "
                f"de resultados no numericos con codigo de salida cero, que es "
                f"lo que hay que evitar. Ver H-50.")
        print(f"    PGB={pi_bolsa.mean():.0f} COP/kWh (promedio bolsa)")
        print(f"    b calibrado: {b_cal.round(0)}")

        prosumer_ids = list(range(N))
        consumer_ids = []

    else:
        print("\n[1/5] Datos sintéticos de validación (modelo base Sofía)...")
        G, D  = get_generation_profiles(), get_demand_profiles()
        p     = get_agent_params()
        pde   = get_pde_weights()
        T     = 24
        N, _  = D.shape
        grid_params  = GRID_PARAMS
        currency     = "$"
        agent_names  = [f"A{i+1}" for i in range(N)]
        b_cal        = np.array(p["b"])
        pi_bolsa     = np.full(T, PGB)
        pi_gs_per_agent = None    # sin Cedenar en modo sintético
        pi_gs_eff       = None    # sin escalar comunitario en modo sintético
        prosumer_ids = [0, 1, 2, 3]
        consumer_ids = [4, 5]
        cap          = np.array([3., 4., 3., 2., 0., 0.])
        month_labels = None   # período único (24h sintéticas)
        print(f"    N={N}  T={T}h  |  PGS={PGS} · PGB={PGB} (modelo base)")

    # ── 2. EMS P2P ───────────────────────────────────────────────────────
    print("\n[2/5] EMS P2P (RD + Stackelberg)...")
    t0   = time.time()

    # ── El techo por agente, que ahora entra AL JUEGO ─────────────────────
    # C-146 / H-45. Se arma aqui, antes del EMS, porque hasta el 2026-09-07
    # solo se construia mas abajo para los escenarios y la liquidacion: el
    # juego recibia un unico escalar comunitario. Esa asimetria dejaba a los
    # compradores del techo mas bajo pagando exactamente su techo, con ahorro
    # cero por construccion, en 109 de 200 horas de la frontera principal.
    #
    # Mas abajo se REUTILIZA en vez de recalcularse.
    if use_real_data:
        if full_horizon:
            pi_gs_arg = pi_gs_per_agent_hourly(agent_names, index_full)
        elif single_day:
            pi_gs_arg = pi_gs_per_agent_hourly(agent_names, idx_day)
        else:
            pi_gs_arg = pi_gs_per_agent           # (N,) — perfil diario
    else:
        pi_gs_arg = grid_params["pi_gs"]

    # ── Y el piso por vendedor, que tampoco llegaba ───────────────────────
    # H-49 / C-148. CAL-47 sustituyo las dos cotas escritas a mano por cotas
    # medidas. El techo llego, primero a la liquidacion y con C-146 al juego.
    # El piso NO: en la corrida valia 280 COP/kWh constante para los cinco
    # agentes y las 5.160 horas, que es justo la constante que CAL-47 venia a
    # sustituir. Nadie lo construia fuera de las sondas.
    #
    # Por la identidad de H-33, el excedente del mercado es el ancho de la
    # banda por la energia transada, de modo que con el techo corregido y el
    # piso no, la corrida canonica habria sobrestimado el excedente doce
    # veces en la frontera principal.
    #
    # El perfil diario promedio NO lo lleva, y con razon: el tramo de permuta
    # depende del mes y ese modo no tiene calendario. Ahi el piso sigue
    # siendo el escalar, y hay que declararlo donde se publique.
    pi_gb_agente = None
    if use_real_data:
        idx_piso = index_full if full_horizon else (idx_day if single_day
                                                    else None)
        if idx_piso is not None:
            from core.opciones_externas import (piso_por_vendedor,
                                                tramo_permuta)
            cvm_m = cvm_per_agent_hourly(agent_names, idx_piso)
            mes_m = pd.Series(idx_piso).dt.strftime("%Y-%m").to_numpy()
            # H-53: se evalua sobre el excedente BRUTO, es decir como si todo
            # el excedente cruzara la frontera. La energia que el vendedor
            # coloca DENTRO de la comunidad no deberia agotar su permuta, de
            # modo que esta cuenta manda a bolsa antes de tiempo. Queda
            # declarado como simplificacion y va como consulta al asesor.
            en_permuta_m = tramo_permuta(G, D, mes_m)
            pi_gb_agente = piso_por_vendedor(
                np.asarray(pi_gs_arg, dtype=float), cvm_m,
                np.asarray(pi_bolsa, dtype=float), en_permuta_m)

    grid = GridParams(**grid_params,
                      pi_gs_agente=pi_gs_arg if use_real_data else None,
                      pi_gb_agente=pi_gb_agente)
    if use_real_data:
        _t = np.atleast_2d(np.asarray(pi_gs_arg, dtype=float))
        print(f"    [C-146] El juego usa el techo de cada agente: "
              f"{np.min(_t):.1f} a {np.max(_t):.1f} COP/kWh entre agentes")
        if pi_gb_agente is None:
            print(f"    [H-49] El piso sigue siendo el escalar "
                  f"{grid_params['pi_gb']:.1f}: el perfil diario no tiene "
                  f"calendario y el tramo de permuta depende del mes")
        else:
            # C-153: el rango se mide sobre las horas en que el agente es
            # VENDEDOR de verdad, no sobre la matriz entera. Fuera de esas
            # horas la matriz guarda un valor latente que no es el piso de
            # nadie. Sobre el horizonte de la frontera principal la matriz
            # entera va de 97,9 a 898,0 COP/kWh, con el maximo por encima de
            # todos los techos, porque recoge el precio de bolsa de horas
            # nocturnas sin excedente; las horas-vendedor van de 103,7 a
            # 714,1, que son los dos tramos de verdad.
            _p = np.asarray(pi_gb_agente, dtype=float)
            _vende = np.maximum(G - D, 0.0) > 1e-9
            if _vende.any():
                _pv = _p[_vende]
                print(f"    [C-148] El juego usa el piso medido de cada "
                      f"vendedor: {np.min(_pv):.1f} a {np.max(_pv):.1f} "
                      f"COP/kWh en las {int(_vende.sum())} horas-vendedor "
                      f"(antes: {grid_params['pi_gb']:.1f} constante)")
            else:
                print(f"    [C-148] Ninguna hora con vendedor; el piso "
                      f"medido no llega a actuar")
            # H-53: el tramo se calcula sobre el excedente BRUTO, como si
            # todo cruzara la frontera. La energia colocada dentro de la
            # comunidad no deberia agotar la permuta. Es una simplificacion
            # declarada, no una decision cerrada: va como consulta al asesor.
            _en_b = int(np.sum(_vende & ~en_permuta_m))
            print(f"    [H-53] El tramo se evalua sobre el excedente bruto; "
                  f"{_en_b} horas-vendedor caen en bolsa por esa cuenta")

    # CAL-32 (apendice 2026-05-06b): c_j=0 para PV puro en modo --data real.
    # Equilibrio invariante en c_j (verificado por scripts/demo_invariancia_c_lambda.py).
    # Modo sintetico mantiene C=zeros(6) de Bienestar6p.py (golden test).
    agents = AgentParams(
        N=N, a=np.zeros(N) if use_real_data else np.array(p["a"]),
        b=b_cal if use_real_data else np.array(p["b"]),
        c=np.zeros(N) if use_real_data else np.array(p["c"]),
        lam=np.full(N, 100.0), theta=np.full(N, 0.5), etha=np.full(N, 0.1),
    ) if use_real_data else AgentParams(**p)

    solver = SolverParams(tau=0.001, t_span=(0.0, 0.005),
                          n_points=150, stackelberg_iters=2, parallel=True,
                          metodo=metodo, t_span_acoplado=t_span_acoplado,
                          buyer_competition=buyer_competition,   # CAL-49
                          # C-161: con almacen, cada hora conserva su
                          # trayectoria con multiplicadores en vez de tirarla.
                          guarda_trayectorias=bool(almacen),
                          # C-169: cuantos procesos abre el mercado. Con None
                          # se toman todos los nucleos UTILES, que no son los
                          # que la maquina declara sino los que la afinidad
                          # permite. La variable del entorno la pone el
                          # lanzador del servidor.
                          procesos=procesos)
    if metodo == "acoplado":
        print(f"    [CAL-48] Mercado resuelto ACOPLADO (horizonte "
              f"{t_span_acoplado}), como JoinFinal.m; no por alternancia")
    ems    = EMSP2P(agents, grid, solver)
    p2p_results, G_klim, D_star = ems.run(D, G)

    # ── El almacen de la corrida (C-161) ─────────────────────────────────
    # Todo lo que hasta hoy se tiraba: los retirados por hora, el piso y el
    # techo de cada agente, el estado del integrador, los pares de energia
    # casi nula que el desglose descarta, y la trayectoria entera de cada
    # hora con sus multiplicadores. Sin esto, ninguna figura de convergencia
    # puede dibujarse sin volver a simular.
    alm = None
    if almacen:
        from core.almacen import Almacen
        if metodo != "acoplado":
            print(f"    [C-161] AVISO: el almacen guarda trayectorias y la "
                  f"via alternada no las produce; solo se llenaran las "
                  f"tablas de horas y flujos")
        idx_alm = (index_full if full_horizon
                   else idx_day if single_day else None)
        alm = Almacen(almacen,
                      cobertura=("m3" if paper_meters else "m1"),
                      inicio=(str(idx_alm[0].date()) if idx_alm is not None
                              else "2025-04-04"),
                      paso_horas=float(paso))
        te_m = (None if not use_real_data
                else np.atleast_2d(np.asarray(pi_gs_arg, dtype=float)))
        _piso_m = (None if pi_gb_agente is None
                   else np.asarray(pi_gb_agente, dtype=float))
        for r in p2p_results:
            k = int(r.k)
            # C-166: la tabla de agentes se llena SIEMPRE, tambien en las
            # horas sin mercado. Una institucion que esa hora no transo sigue
            # comprandole a la red, y la liquidacion tiene que verlo.
            if te_m is not None and _piso_m is not None:
                _te_k = (te_m[:, k] if te_m.shape[0] > 1
                         else np.full(len(agent_names), float(te_m[0, k])))
                _P = (np.asarray(r.P_star, dtype=float)
                      if r.P_star is not None else None)
                _cp = np.zeros(len(agent_names))
                _vp = np.zeros(len(agent_names))
                if _P is not None and r.seller_ids and r.buyer_ids:
                    for _a, _j in enumerate(r.seller_ids):
                        _vp[_j] = float(_P[_a, :].sum())
                    for _b, _i in enumerate(r.buyer_ids):
                        _cp[_i] = float(_P[:, _b].sum())
                alm.anota_agentes(
                    k, agent_names, D[:, k], G_klim[:, k], _te_k,
                    _piso_m[:, k], sids=r.seller_ids or (),
                    bids=r.buyer_ids or (),
                    retirados=getattr(r, "retirados", ()) or (),
                    compra_p2p=_cp, vende_p2p=_vp)
            if not r.seller_ids or not r.buyer_ids:
                alm.sin_resolver(k, "sin mercado esa hora")
                continue
            P = np.asarray(r.P_star, dtype=float)
            pi = np.asarray(r.pi_star, dtype=float)
            alm.anota_hora(
                k, resuelta=True, vendedores=len(r.seller_ids),
                compradores=len(r.buyer_ids), retirados=len(r.retirados),
                volumen=float(np.sum(P)),
                precio_medio=float(np.mean(pi)) if pi.size else float("nan"),
                iteraciones=int(r.iters_used),
                residuo=float(r.norm_rel_final),
                W_vendedor=float(r.Wj_total), W_comprador=float(r.Wi_total),
                SC=float(r.SC), SS=float(r.SS), equidad=float(r.IE),
                reparto_comprador=float(r.PS),
                reparto_vendedor=float(r.PSR))
            alm.anota_flujos(
                k, P, pi, r.seller_ids, r.buyer_ids, agent_names,
                techo_i=(None if te_m is None or te_m.shape[0] == 1
                         else te_m[r.buyer_ids, k]),
                piso_j=(None if pi_gb_agente is None
                        else np.asarray(pi_gb_agente,
                                        dtype=float)[r.seller_ids, k]))
            if getattr(r, "tr", None) is not None:
                alm.anota_trayectoria(k, r.tr, r.seller_ids, r.buyer_ids,
                                      agent_names)
        # C-165: el almacen NO se cierra aqui. Le falta la cuarta tabla, la de
        # los escenarios regulatorios, y esa se llena mas abajo porque la
        # comparacion todavia no ha corrido. Cerrarlo aqui era la razon por la
        # que esa tabla llevaba dias declarada y vacia.

    # C-151: la restriccion de participacion tiene que VERSE. Retira
    # vendedores y con ellos su energia, y una corrida que lo hiciera en
    # silencio seria justo el tipo de cambio invisible que este proyecto
    # lleva un dia entero persiguiendo.
    _ret = sum(len(getattr(r, "retirados", []) or []) for r in p2p_results)
    if _ret:
        _hr = sum(1 for r in p2p_results if getattr(r, "retirados", None))
        _act = sum(1 for r in p2p_results if r.P_star is not None)
        print(f"    [C-151] Participacion: {_ret} retiros de vendedor en "
              f"{_hr} de {_act} horas con mercado. Un vendedor se retira "
              f"cuando el mercado le paga menos que su alternativa de red "
              f"por el conjunto de lo que coloca")
    elif getattr(grid, "pi_gb_agente", None) is not None:
        print(f"    [C-151] Participacion: ningun retiro; el mercado bate la "
              f"alternativa de red de todos los vendedores en todas las horas")

    # Reportar impacto del DR (solo si hay flexibilidad activa)
    dr_active = np.any(agents.alpha > 1e-9)
    if dr_active:
        from core.dr_program import dr_impact_report
        dr_rep = dr_impact_report(D, D_star, G_klim, agent_names)
        print(f"    DR activo: {dr_rep['shift_total_kwh']:.3f} kWh desplazados "
              f"({dr_rep['shift_pct']:.2f}% demanda)  "
              f"SC: {dr_rep['sc_before']:.3f}→{dr_rep['sc_after']:.3f}  "
              f"SS: {dr_rep['ss_before']:.3f}→{dr_rep['ss_after']:.3f}")
        # Usar D_star para los escenarios comparativos
        D = D_star
    t_p2p = time.time() - t0

    active = [r for r in p2p_results
              if r.P_star is not None and np.sum(r.P_star) > 1e-4]
    kwh    = sum(float(np.sum(r.P_star)) for r in active)
    print(f"    {t_p2p:.1f}s | horas mercado: {len(active)}/{T} | {kwh:.2f} kWh P2P")

    # ── 3. Escenarios C1–C4 ──────────────────────────────────────────────
    print("\n[3/5] Escenarios regulatorios C1–C4...")
    # CAL-9: con datos reales pi_gs es una matriz (N, T) mes a mes (CU
    # Cedenar temporal). Modos single_day y full_horizon llevan la
    # variabilidad mensual real; perfil diario usa el vector (N,) del CAL-8
    # porque representa el promedio del horizonte (sin variabilidad mensual).
    #
    # C-146: `pi_gs_arg` YA SE ARMO arriba, antes del EMS, porque desde el
    # 2026-09-07 el juego tambien lo necesita y no solo la liquidacion. Aqui
    # solo se reutiliza; recalcularlo daria lo mismo y costaria de mas.

    # CAL-10b.2: componente C = Cvm,i,j puro de CREG 119/2007 (literalidad
    # CREG 174 art. 25), leído desde tarifas_cedenar_mensual.csv.
    # Solo aplicable cuando el horizonte tiene timestamps reales (full /
    # single_day). Perfil diario y caso sintético usan "auto" (proporcional
    # ≈ 13.85 % de pi_gs) porque no hay calendario mensual asociado.
    if use_real_data and full_horizon:
        component_c_arg = cvm_per_agent_hourly(agent_names, index_full)
    elif use_real_data and single_day:
        component_c_arg = cvm_per_agent_hourly(agent_names, idx_day)
    else:
        component_c_arg = "auto"

    if isinstance(component_c_arg, np.ndarray):
        c_source = "C = Cvm,i,j real desde CSV Cedenar (CREG 119/2007 art. 11)"
    else:
        c_source = "C ≈ 13.85 % proporcional al CU (modo auto)"
    print(f"    [CAL-10b.2] C1 (CREG 174/2021 art. 25): permuta a "
          f"(pi_gs - Cvm), excedentes a bolsa horaria post-cruce mensual; "
          f"{c_source}.")

    # CAL-13 (ADR-0013): rango negociable + ahorro de comercialización
    # = G + Cvm + COT, para C2 (PPA bilateral con comunidad como usuario
    # no-regulado agregado bajo Ley 143/1994 + CREG 086/1996 + CREG 174/2021
    # art. 23 num. 2 lit. a; el numeral 2 es el de FNCER, que es el caso de las
    # cinco). El usuario no-regulado se ahorra Cvm + COT
    # (margen del comercializador minorista) además de poder negociar G.
    # Origen: columnas Gm + Cvm + COT del CSV Cedenar (PDFs CEDENAR).
    if use_real_data and full_horizon:
        pi_G_arg = g_plus_commercialization_per_agent_hourly(
            agent_names, index_full)
    elif use_real_data and single_day:
        pi_G_arg = g_plus_commercialization_per_agent_hourly(
            agent_names, idx_day)
    elif use_real_data:
        # Perfil diario: vector (N,) promedio horizonte (mismo patrón que pi_gs).
        # G+Cvm+COT constantes dentro del mes → promedio por agente.
        pi_G_full = g_plus_commercialization_per_agent_hourly(
            agent_names, index_full)
        pi_G_arg  = pi_G_full.mean(axis=1)
    else:
        # Caso sintético: G+Cvm+COT aproximado como pi_bolsa·1.5 (proxy).
        # No hay CSV mensual asociado al caso sintético.
        pi_G_arg = float(np.mean(pi_bolsa)) * 1.5

    if isinstance(pi_G_arg, np.ndarray):
        if pi_G_arg.ndim == 2:
            pi_G_msg = (f"matriz (N={pi_G_arg.shape[0]}, T={pi_G_arg.shape[1]}) "
                        f"mes a mes desde Cedenar PDFs")
        else:
            pi_G_msg = f"vector (N={pi_G_arg.shape[0]}) promedio horizonte"
    else:
        pi_G_msg = f"escalar {pi_G_arg:.1f} COP/kWh (proxy 1.5·pi_bolsa)"
    print(f"    [CAL-13] C2 (Ley 143/1994 art. 41 + CREG 086/1996 + "
          f"CREG 174/2021 art. 23 num. 2 lit. a): comunidad MTE como usuario "
          f"no-regulado agregado; savings_cons sobre (G+Cvm+COT); "
          f"rango negociable = {pi_G_msg}.")

    # ── CAL-16 (ADR-0016): descomposición regulatoria del ahorro en C2 ──
    # En lugar del agregado pi_G = G+Cvm+COT, C2 ahora calcula:
    #   savings = E_PPA × [(G − π_ppa) + Cvm + α·COT − MEM_costs]
    # con α=1.0 default y MEM_costs = FAZNI + 0.04·G + π_rep.
    # Origen: cu_components_per_agent_hourly + mem_costs_per_agent_hourly.
    # Si los datos reales no están disponibles (caso sintético) se cae al
    # modo CAL-13 agregado (pi_G_arg).
    if use_real_data and full_horizon:
        cu_comps = cu_components_per_agent_hourly(agent_names, index_full)
        mem_arg  = mem_costs_per_agent_hourly(agent_names, index_full)
    elif use_real_data and single_day:
        cu_comps = cu_components_per_agent_hourly(agent_names, idx_day)
        mem_arg  = mem_costs_per_agent_hourly(agent_names, idx_day)
    elif use_real_data:
        cu_comps_full = cu_components_per_agent_hourly(agent_names, index_full)
        mem_full      = mem_costs_per_agent_hourly(agent_names, index_full)
        # Perfil diario: promedio por agente (constante dentro del mes).
        # nanmean para robustez ante meses fuera del CSV (caen al fallback).
        cu_comps = {k: np.nanmean(v, axis=1) for k, v in cu_comps_full.items()}
        mem_arg  = np.nanmean(mem_full, axis=1)
    else:
        cu_comps = None
        mem_arg  = None

    if cu_comps is not None:
        g_arg, cvm_arg, cot_arg = cu_comps["G"], cu_comps["Cvm"], cu_comps["COT"]
        # CAL-41 (ADR-0041): peajes regulados T+D+PR+Rm. Los cobra el art. 25
        # num. 2 de la CREG 174 sobre la permuta cuando el AC cae en el Caso 2
        # del art. 20 de la 101 072 — que es lo que ocurre con cinco fronteras,
        # porque el PDE suma 100 % y ninguno puede quedar bajo el 10 %.
        # Se arman desde el MISMO `cu_comps` que el resto de la descomposición,
        # de modo que comparten origen, recorte temporal y fallback.
        tolls_arg = (cu_comps["T"] + cu_comps["D"]
                     + cu_comps["PR"] + cu_comps["R"])
        cot_alpha_default = 1.0
        g_mean   = float(np.nanmean(g_arg))
        cvm_mean = float(np.nanmean(cvm_arg))
        cot_mean = float(np.nanmean(cot_arg))
        mem_mean = float(np.nanmean(mem_arg))
        pi_upper = g_mean + cvm_mean + cot_alpha_default * cot_mean - mem_mean
        print(f"    [CAL-16] C2 descompuesto: savings = G + Cvm + α·COT − MEM | "
              f"G≈{g_mean:.1f} Cvm≈{cvm_mean:.1f} α·COT≈{cot_mean:.1f} "
              f"(α=1.0) MEM≈{mem_mean:.1f} → pi_upper≈{pi_upper:.1f} COP/kWh.")
        # CAL-21 (ADR-0021): f=0.5 como postulado egalitario; teorema de
        # invarianza demostrado empiricamente (Δ total_net_benefit < 1e-13 %).
        F_PPA_DEFAULT = 0.5
        pi_ppa_default = grid_params["pi_gb"] + F_PPA_DEFAULT * (
            pi_upper - grid_params["pi_gb"]
        )
    else:
        # Sin datos reales → se queda con el default CAL-13 agregado
        g_arg = cvm_arg = cot_arg = None
        # CAL-41: sin tarifas reales no hay peajes que descontar. C4 emitirá
        # su propio aviso si el Caso 2 aplica y los peajes faltan.
        tolls_arg = None
        cot_alpha_default = 1.0
        pi_G_mean_default = (float(np.mean(pi_G_arg))
                             if isinstance(pi_G_arg, np.ndarray)
                             else float(pi_G_arg))
        # CAL-21 (ADR-0021): mismo default f=0.5 en modo agregado.
        F_PPA_DEFAULT = 0.5
        pi_ppa_default = grid_params["pi_gb"] + F_PPA_DEFAULT * (
            pi_G_mean_default - grid_params["pi_gb"]
        )
        print(f"    [CAL-16] C2 modo agregado CAL-13 (caso sintético): "
              f"pi_G≈{pi_G_mean_default:.1f} COP/kWh.")

    # ── CAL-37 (ADR-0037): PES horario para el diagnóstico LBC de C5 ────
    pi_escasez_arr = None
    if include_c5 and isinstance(month_labels, np.ndarray):
        try:
            import pandas as _pd
            _pes_df = _pd.read_csv(os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "data", "precios_escasez_creg.csv"))
            _pes_map = {int(str(m).replace("-", "")): float(v)
                        for m, v in zip(_pes_df["mes"],
                                        _pes_df["pes_cop_kwh"])}
            pi_escasez_arr = np.array(
                [_pes_map.get(int(m), np.inf) for m in month_labels])
            _n_pes = int(np.isfinite(pi_escasez_arr).sum())
            print(f"    [CAL-37] C5 AGR activo: PES cargado para "
                  f"{_n_pes}/{len(pi_escasez_arr)} horas (LBC diagnóstico)")
        except Exception as _e:                          # noqa: BLE001
            print(f"    [CAL-37] PES no cargado ({_e}) → LBC sin trigger")

    # ── CAL-51: el precio pactado del contrato bilateral ─────────────────
    # Articulo 23 numeral 2 literal a de la Resolucion CREG 174: la venta a un
    # tercero con destino a usuarios no regulados se hace «a precio pactado
    # libremente». Sin ese precio, el escenario del contrato valoraba su
    # excedente a la bolsa horaria y coincidia con el de mercado mayorista al
    # ultimo digito. El precio lo publica XM y el fichero ya estaba en el
    # repositorio sin que nada lo leyera.
    # RETIRADO como definicion de C2 por decision del autor el 2026-09-08:
    # C2 pasa a ser el contrato INTERNO de CAL-52. La venta a un tercero del
    # literal a queda medida y registrada en H-63, con el hallazgo de que a
    # precio de mercado domina a la bolsa en las dos dimensiones a la vez, lo
    # que vuelve trivial esa comparacion. Se conserva alcanzable para el dia
    # que el asesor resuelva la consulta.
    pi_contrato_arg = None
    if False and use_real_data:
        idx_c = (index_full if full_horizon else
                 idx_day if single_day else None)
        if idx_c is not None:
            from data.precios_contratos import cobertura as _cob_contrato
            from data.precios_contratos import precio_horario as _pc_h
            pi_contrato_arg = _pc_h(idx_c)
            _c = _cob_contrato(str(idx_c[0].date()), str(idx_c[-1].date()))
            print(f"    [CAL-51] C2 coloca su excedente bajo contrato: "
                  f"{np.mean(pi_contrato_arg):.1f} COP/kWh de media, serie "
                  f"mensual de XM, {len(_c['cargados'])}/{len(_c['meses'])} "
                  f"meses (art. 23 num. 2 lit. a)")
        else:
            print(f"    [CAL-51] El perfil diario promedio no lleva contrato: "
                  f"su precio es mensual y ese modo no tiene calendario")

    cr = run_comparison(
        D=D, G_klim=G_klim, G_raw=G,
        p2p_results=p2p_results,
        pi_gs=pi_gs_arg, pi_gb=grid_params["pi_gb"],
        pi_bolsa=pi_bolsa,
        prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
        pde=pde,
        pi_ppa=pi_ppa_default,
        # CAL-52: C2 pasa a ser el contrato bilateral INTERNO, es decir los
        # mismos flujos del mercado a precio pactado en el punto medio de la
        # banda. Necesita el piso de cada vendedor.
        piso_agente=pi_gb_agente,
        pi_contrato=None,                               # CAL-51, ver H-63
        capacity=cap,
        month_labels=month_labels,
        component_c=component_c_arg,
        tolls=tolls_arg,                                # CAL-41 (art. 20 num. 2)
        pi_G=pi_G_arg,                                  # CAL-13 (compat)
        # CAL-16: descomposición explícita
        g_component=g_arg,
        cvm_component=cvm_arg,
        cot_component=cot_arg,
        mem_costs=mem_arg,
        cot_alpha=cot_alpha_default,
        # CAL-37: escenario C5 AGR (CREG 101 099/2026)
        include_c5=include_c5,
        pi_escasez=pi_escasez_arr,
        # CAL-46: duracion del paso. Con 1.0 no se ejecuta ninguna operacion
        # nueva y el camino horario queda identico bit a bit (compuerta en
        # tests/gate_cal46_paso_horario.py).
        dt=paso,
    )

    # ── La cuarta tabla del almacen: los escenarios (C-165) ──────────────
    #
    # Estaba declarada desde el primer dia y nadie la llenaba, porque el
    # desglose por hora de cada mecanismo no existia: el beneficio solo se
    # conocia agregado al horizonte entero. Con C-165 cada escenario anota su
    # dinero en la hora que lo genera, y esa anotacion suma exactamente el
    # total publicado (compuerta en tests/gate_c165_desglose_horario.py).
    #
    # De aqui salen las metricas por mes y por hora sin volver a simular, que
    # es lo que el capitulo de equidad necesita para poder decir EN QUE MESES
    # un mecanismo reparte mejor que otro.
    if alm is not None:
        _falta = []
        for _esc in ("P2P", "C1", "C2", "C3", "C4", "C4_mensual", "C5"):
            if _esc not in cr.net_benefit:
                continue
            _m = cr.neto_horario.get(_esc)
            if _m is None:
                _falta.append(_esc)
                continue
            _m = np.asarray(_m, dtype=float)
            for _k in range(_m.shape[1]):
                alm.anota_escenarios(_k, {_esc: _m[:, _k]}, agent_names)
        if _falta:
            # La granularidad mensual del colectivo no tiene desglose horario
            # a proposito: su dinero se valora contra promedios del mes.
            print(f"    [C-165] sin desglose horario, por diseno: "
                  f"{', '.join(_falta)}")
        partes = alm.cierra()
        print(f"    [C-161] almacen en {almacen}: " +
              " · ".join(f"{t} {n} partes" for t, n in partes.items()))

    # ── 4. Reporte ───────────────────────────────────────────────────────
    print("\n[4/5] Reporte:")
    print_comparison_report(cr)

    print_flow_breakdown(cr, currency=currency)

    # Nota: en la propuesta de tesis, el escenario "Individual" = C1 (CREG 174),
    # y los escenarios "C1"→"C3" de la propuesta corresponden a C2→C4 del código.
    # Los encabezados ya reflejan esto: "C1 Individual", "C4 Colectivo", etc.
    esc = [e for e in ["P2P", "C1", "C2", "C3", "C4", "C4_mensual", "C5"]
           if e in cr.net_benefit]                       # CAL-37: C5 opcional
    esc_labels = {                                       # CAL-42: C4_mensual
        "P2P": "P2P", "C1": "C1-Indiv", "C2": "C2-Bilat",
        "C3": "C3-Spot", "C4": "C4-Colect", "C4_mensual": "C4-Colect-mes",
        "C5": "C5-AGR",
    }
    print(f"\n  Ganancia neta por agente ({currency}/período):")
    print(f"  {'Institución':<12}" + "".join(f"{esc_labels[e]:>14}" for e in esc))
    print("  " + "─"*82)
    for n in range(N):
        name = agent_names[n] if n < len(agent_names) else f"A{n+1}"
        print(f"  {name:<12}" +
              "".join(f"{cr.net_benefit_per_agent[e][n]:>14,.0f}" for e in esc))

    print(f"\n  Gini por escenario (0=equitativo, 1=concentrado):")
    print(f"  " + "  ".join(f"{esc_labels[e]}: {cr.gini.get(e, 0):.4f}" for e in esc))

    print(f"\n  Ventaja P2P vs C4 (Colectivo CREG 101 072):")
    for n in range(N):
        name  = agent_names[n] if n < len(agent_names) else f"A{n+1}"
        delta = (cr.net_benefit_per_agent["P2P"][n]
                 - cr.net_benefit_per_agent["C4"][n])
        print(f"    {name:<12}: {'+'if delta>=0 else ''}{delta:>12,.0f} {currency}  "
              f"({'P2P mejor' if delta > 0 else 'C4 mejor'})")

    # ── 4b. Reporte mensual (solo modo --full con datos reales) ─────────────
    monthly_data = []
    if use_real_data and full_horizon and month_labels is not None:
        print("\n  Reporte mensual (horizonte completo)...")
        from analysis.monthly_report import compute_monthly_metrics, print_monthly_table
        monthly_data = compute_monthly_metrics(
            D=D, G_klim=G_klim, G_raw=G,
            p2p_results=p2p_results,
            pi_gs=pi_gs_arg,
            pi_gb=grid_params["pi_gb"],
            pi_bolsa=pi_bolsa,
            prosumer_ids=prosumer_ids,
            consumer_ids=consumer_ids,
            month_labels=month_labels,
            pde=pde,
            capacity=cap,
            component_c=component_c_arg,
            tolls=tolls_arg,                            # CAL-41
            # CAL-37: C2 y C5 en la tabla mensual
            pi_ppa=pi_ppa_default,
            g_component=g_arg,
            cvm_component=cvm_arg,
            cot_component=cot_arg,
            mem_costs=mem_arg,
            cot_alpha=cot_alpha_default,
            include_c5=include_c5,
            pi_escasez=pi_escasez_arr,
        )
        print_monthly_table(monthly_data, currency=currency)

    # ── 5. Exportar base ─────────────────────────────────────────────────
    print("\n[5/5] Exportando resultados y gráficas...")
    # CAL-43 (A5): destino de `outputs/` y `graficas/`. Por defecto la raiz
    # del repositorio, como siempre; con --out-dir, una carpeta aparte. Sin
    # esto, cualquier corrida de validacion PISA las figuras y los .xlsx del
    # arbol de trabajo, y la version anterior no es recuperable si no estaba
    # commiteada.
    base_dir  = (os.path.abspath(out_dir) if out_dir
                 else os.path.dirname(os.path.abspath(__file__)))
    if out_dir:
        os.makedirs(base_dir, exist_ok=True)
        print(f"    [CAL-43] salidas redirigidas a {base_dir}")

    # Series diarias (solo modo --full con datos reales, T ≥ 48h)
    daily_series = None
    if use_real_data and full_horizon and D.shape[1] >= 48:
        import datetime as _dt
        print("    Calculando series diarias para bootstrap estadístico...")
        daily_series = _compute_daily_series(
            D=D, G_klim=G_klim, p2p_results=p2p_results,
            pi_gs=pi_gs_arg, pi_gb=grid_params["pi_gb"],
            pi_bolsa=pi_bolsa, pde=pde, cap=cap,
            prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
            component_c=component_c_arg, tolls=tolls_arg,   # CAL-41
        )
        os.makedirs(os.path.join(base_dir, "outputs"), exist_ok=True)
        ts_str = _dt.datetime.now().strftime("%Y%m%d_%H%M")
        csv_path = os.path.join(base_dir, "outputs", f"daily_series_{ts_str}.csv")
        daily_series.to_csv(csv_path)
        print(f"    Series diarias ({len(daily_series)} días) → {csv_path}")

    excel_path = _export_base(cr, p2p_results, G_klim, D, base_dir, currency,
                               daily_series=daily_series)
    print(f"    Excel → {excel_path}")

    from analysis.p2p_breakdown import export_p2p_hourly, print_p2p_sample
    outputs_dir = os.path.join(base_dir, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    flows_rows, summary_rows = export_p2p_hourly(
        p2p_results=p2p_results,
        agent_names=agent_names,
        pi_gs=pi_gs_arg,
        pi_gb=grid_params["pi_gb"],
        out_dir=outputs_dir,
        prefix="p2p_breakdown",
        verbose=True,
    )
    print_p2p_sample(flows_rows, summary_rows, n_hours=2)

    from visualization.plots import (generate_all_plots, plot_monthly_comparison,
                                     plot_flow_breakdown, plot_c1_vs_c4,
                                     plot_fig23_perfiles_diarios)
    plots_dir = os.path.join(base_dir, "graficas")
    generate_all_plots(D=D, G=G, G_klim=G_klim, p2p_results=p2p_results,
                       cr=cr, agent_names=agent_names,
                       out_dir=plots_dir, currency=currency)

    # Fig 23 — perfiles diarios promedio (solo tiene sentido con horizonte ≥1 día)
    if use_real_data and D.shape[1] >= 24:
        p = plot_fig23_perfiles_diarios(D, G, agent_names, out_dir=plots_dir)
        if p:
            print(f"    ✓ Fig 23 — Perfiles diarios promedio")

    p = plot_flow_breakdown(cr, out_dir=plots_dir, currency=currency)
    if p:
        print(f"    ✓ Fig 13 — Desglose de flujos por componente")

    if monthly_data:
        p = plot_monthly_comparison(monthly_data, out_dir=plots_dir, currency=currency)
        if p:
            print(f"    ✓ Fig 12 — Comparación mensual")

    p = plot_c1_vs_c4(
        cr=cr, agent_names=agent_names,
        D=D, G_klim=G_klim, pi_bolsa=pi_bolsa,
        pde=pde, pi_gs=grid_params["pi_gs"],
        out_dir=plots_dir, currency=currency,
    )
    if p:
        print(f"    ✓ Fig 15 — Comparación directa C1 vs C4")

    # ── 6. Análisis de sensibilidad y factibilidad (--analysis) ──────────
    sa_pgb, sa_pv, sa_ppa = [], [], []
    fa_des, fa_creg_rep, fa_ir = None, None, None

    if run_analysis:
        print("\n" + "="*65)
        print("  ANÁLISIS DE SENSIBILIDAD Y FACTIBILIDAD")
        print("="*65)

        from analysis.sensitivity import (
            run_sensitivity_pgb, run_sensitivity_pv,
            run_sensitivity_ppa, run_sensitivity_pgs,
            find_dominance_threshold)
        from analysis.feasibility import (
            analyze_desertion, analyze_desertion_individual_rationality,
            analyze_creg_101072_compliance)
        from visualization.plots import generate_sensitivity_plots

        # SA-1: variación PGB. CAL-39 (aprobado por el autor): rango
        # extendido a [150..500] — la serie XM real está en 182-235 y el
        # rango histórico [200..500] arrancaba por encima de la realidad.
        # El valor NOMINAL PGB=280 no cambia (gated a asesores, Anexo A).
        pgb_range = np.array([150, 200, 250, 280, 300, 350, 400, 450, 500])
        sa_pgb = run_sensitivity_pgb(
            D=D, G=G, G_klim=G_klim, agents=agents, grid_base=grid,
            solver=solver, p2p_results_base=p2p_results,
            pi_gb_range=pgb_range, pde=pde,
            prosumer_ids=prosumer_ids, verbose=True,
            month_labels=month_labels,                  # CAL-9 fix
            component_c=component_c_arg,                 # CAL-10b fix
            tolls=tolls_arg,                            # CAL-41
            include_c5=include_c5,                      # CAL-39
            g_component=g_arg, cvm_component=cvm_arg,
            cot_component=cot_arg, mem_costs=mem_arg,
            cot_alpha=cot_alpha_default,
        )

        # SA-2: variación cobertura PV
        print(f"\n  SA-2: Ejecutando barrido de cobertura PV...")
        # C-172: los objetivos por DEBAJO de la cobertura actual se descartan,
        # no se recortan.
        #
        # La version anterior los recortaba a factor uno exacto. Como la
        # comunidad ya tiene cerca del 20 % de cobertura, el objetivo del 11 %
        # caia por debajo y se convertia en un factor 1,0000, mientras que el
        # del 20 % daba 1,0025: dos puntos casi identicos que la funcion de
        # duplicados no junta porque difieren en el tercer decimal.
        #
        # El barrido anunciaba seis niveles de cobertura y entregaba cinco, con
        # dos filas que la pantalla redondea al mismo «1.00  20%» y que nadie
        # puede distinguir leyendo la tabla. Y costaba una resolucion completa
        # del horizonte, es decir unos doce minutos por frontera, en recalcular
        # un punto que ya se tenia.
        #
        # Descartar es ademas lo que la intencion pedia: el barrido existe para
        # ver que pasa si la comunidad instala MAS solar, y reducirla por
        # debajo de lo que ya tiene no es una pregunta de este estudio.
        base_cov = float(G.mean() / max(D.mean(), 1e-6))
        targets  = [0.11, 0.20, 0.33, 0.50, 0.75, 1.00]
        # El estado ACTUAL entra siempre, porque es la referencia contra la que
        # se lee el barrido; los objetivos por encima entran cada uno una vez.
        _brutos = [t / max(base_cov, 0.01) for t in targets]
        _arriba = [f for f in _brutos if f >= 1.005]
        pv_factors = np.unique(np.round(np.clip([1.0] + _arriba, 1.0, 10.0), 3))
        _fuera = len(targets) - len(_arriba)
        if _fuera:
            print(f"    [C-172] {_fuera} objetivo(s) de cobertura quedan por "
                  f"debajo del {base_cov*100:.1f} % que la comunidad ya tiene; "
                  f"se descartan en vez de repetir el punto de referencia")
        sa_pv = run_sensitivity_pv(
            D=D, G_base=G, agents=agents, grid=grid, solver=solver,
            pv_factors=pv_factors, pde=pde,
            prosumer_ids=prosumer_ids, verbose=True,
            month_labels=month_labels,                  # CAL-9 fix
            component_c=component_c_arg,                 # CAL-10b fix
            tolls=tolls_arg,                            # CAL-41
            include_c5=include_c5,                      # CAL-39
            g_component=g_arg, cvm_component=cvm_arg,
            cot_component=cot_arg, mem_costs=mem_arg,
            cot_alpha=cot_alpha_default,
        )

        # SA-3: variación precio al usuario π_gs (Actividad 4.1 propuesta)
        print(f"\n  SA-3: Ejecutando barrido de precio al usuario (π_gs)...")
        sa_pgs = run_sensitivity_pgs(
            D=D, G=G, agents=agents, grid_base=grid, solver=solver,
            pde=pde, prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
            verbose=True,
            month_labels=month_labels,                  # CAL-9 fix
            # No pasamos component_c: pgs varía sintéticamente y el dato
            # real Cvm,i,j (CAL-10b.2) no aplica a un sweep hipotético del CU.
        )

        # Umbrales de dominancia
        thresholds = find_dominance_threshold(sa_pgb, sa_pv)
        print(f"\n  Umbrales de dominancia P2P:")
        print(f"    P2P siempre > C4: {thresholds.get('p2p_always_beats_c4')}")
        t_c4 = thresholds.get("pgb_threshold_vs_C4")
        t_c1 = thresholds.get("pgb_threshold_vs_C1")
        if isinstance(t_c4, float):
            print(f"    PGB umbral P2P = C4: {t_c4:.0f} COP/kWh")
        else:
            print(f"    PGB umbral P2P = C4: {t_c4}")
        if isinstance(t_c1, float):
            print(f"    PGB umbral P2P = C1: {t_c1:.0f} COP/kWh  ← deserción posible aquí")
        else:
            print(f"    PGB umbral P2P = C1: {t_c1}")
        if thresholds.get("pv_threshold_vs_C4"):
            print(f"    Factor PV umbral vs C4: {thresholds['pv_threshold_vs_C4']:.2f}x")

        # FA-1: deserción horaria (precio P2P vs precio bolsa)
        fa_des = analyze_desertion(
            p2p_results=p2p_results, pi_bolsa=pi_bolsa,
            agent_names=agent_names, prosumer_ids=prosumer_ids, verbose=True,
        )

        # FA-1b: Condición de Racionalidad Individual por agente (§3.14)
        # Pasamos los beneficios reales del caso nominal (XM variable) para
        # que la evaluación base use precios correctos, no el SA-1 constante.
        pi_gb_nom = grid_params["pi_gb"]
        fa_ir = analyze_desertion_individual_rationality(
            sa_pgb_results=sa_pgb,
            agent_names=agent_names,
            pi_gb_nominal=pi_gb_nom,
            base_net_p2p=cr.net_benefit_per_agent.get("P2P"),
            base_net_c1=cr.net_benefit_per_agent.get("C1"),
            base_net_c4=cr.net_benefit_per_agent.get("C4"),
            verbose=True,
        )

        # §3.6: Análisis de fuente y calibración de precios
        from data.xm_prices import price_source_analysis
        price_source_analysis(
            pi_bolsa=pi_bolsa,
            pi_gs=grid_params["pi_gs"],
            verbose=True,
        )

        # SA-3: sensibilidad precio bilateral PPA (§3.8)
        print(f"\n  SA-3: Sensibilidad al precio PPA (pi_ppa)...")
        sa_ppa = run_sensitivity_ppa(
            D=D, G_klim=G_klim, G_raw=G,
            pi_gs=grid_params["pi_gs"], pi_gb=grid_params["pi_gb"],
            pi_bolsa=pi_bolsa,
            p2p_results=p2p_results,
            prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
            pde=pde,
            capacity=cap if 'cap' in dir() else None,
            verbose=True,
            month_labels=month_labels,                  # CAL-9
            component_c=component_c_arg,                 # CAL-10b
            tolls=tolls_arg,                            # CAL-41
            pi_G=pi_G_arg,                                # CAL-13b
            # CAL-16: descomposición explícita
            g_component=g_arg,
            cvm_component=cvm_arg,
            cot_component=cot_arg,
            mem_costs=mem_arg,
            cot_alpha=cot_alpha_default,
        )

        # §3.12: Desglose P2P hora a hora (exportado en bloque 5, muestra ampliada)
        print(f"\n  §3.12 Desglose P2P hora a hora (muestra ampliada):")
        print_p2p_sample(flows_rows, summary_rows, n_hours=5)

        # FA-2: cumplimiento CREG 101 072
        fa_creg_rep = analyze_creg_101072_compliance(
            D=D, G=G, agent_names=agent_names,
            prosumer_ids=prosumer_ids, verbose=True,
        )

        # FA-3: Robustez — retiro de participante
        # FA-4: Robustez — escalamiento de instalación
        from analysis.feasibility import (analyze_withdrawal_risk,
                                          analyze_scaling_risk)
        print(f"\n  FA-3/FA-4: Robustez regulatoria C4...")
        cap_arr = np.array([float(G[n].max()) for n in range(D.shape[0])])
        wr_report = analyze_withdrawal_risk(
            D=D, G=G, G_klim=G_klim,
            pi_gs=pi_gs_arg,            # CAL-9: matriz (N, T) mes a mes en --full
            pi_gb=grid_params["pi_gb"],
            pi_bolsa=pi_bolsa,
            pde=pde,
            prosumer_ids=prosumer_ids,
            agent_names=agent_names,
            net_benefit_p2p=cr.net_benefit_per_agent["P2P"],
            net_benefit_c4_full=cr.net_benefit_per_agent["C4"],
            capacity=cap_arr,
            component_c=component_c_arg,  # CAL-15: hereda Cvm a C4
            tolls=tolls_arg,              # CAL-41: y los peajes si aplica Caso 2
            verbose=True,
        )
        sc_risk = analyze_scaling_risk(
            G=G, prosumer_ids=prosumer_ids, agent_names=agent_names,
            D=D, verbose=True,
        )

        # ── Convergencia RD + Stackelberg (Objetivo 2 / Validación) ──────
        print(f"\n  Convergencia RD+Stackelberg (horas representativas)...")
        from visualization.plots import plot_convergence
        conv_data = ems.run_convergence(
            D=D, G=G, G_klim=G_klim,
            p2p_results=p2p_results,
            n_iters_conv=8,
            max_hours=2,
        )
        if conv_data:
            conv_paths = plot_convergence(
                conv_list=conv_data,
                agent_names=agent_names,
                out_dir=plots_dir,
                currency=currency,
            )
            for p in conv_paths:
                print(f"    ✓ {os.path.basename(p)}")
        else:
            print("    (sin horas activas para análisis de convergencia)")

        # Activity 4.2: Análisis cualitativo de optimalidad P2P vs C4
        print(f"\n  Activity 4.2: Análisis de optimalidad P2P vs C4 hora a hora...")
        from analysis.optimality import analyze_hourly_dominance, print_optimality_report
        from visualization.plots import plot_optimality
        opt_summary = analyze_hourly_dominance(
            D=D, G_klim=G_klim,
            p2p_results=p2p_results,
            pde=pde,
            pi_gs=grid_params["pi_gs"],
            pi_gb=grid_params["pi_gb"],
            pi_bolsa=pi_bolsa,
            prosumer_ids=prosumer_ids,
            consumer_ids=consumer_ids,
        )
        print_optimality_report(opt_summary, agent_names=agent_names, currency=currency)
        p = plot_optimality(opt_summary, out_dir=plots_dir, currency=currency)
        if p:
            print(f"    ✓ Fig 14 — Análisis de optimalidad P2P vs C4")

        # Actividad 4.3: Análisis de sub-períodos (laborable/finde × jul/ene)
        print(f"\n  Actividad 4.3: Análisis de sub-períodos...")
        from analysis.subperiod import (run_subperiod_analysis,
                                        print_subperiod_table, plot_subperiod)
        sp_results = run_subperiod_analysis(
            D=D, G=G,
            agents=agents, grid=grid, solver=solver,
            pde=pde, prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
            pi_gs=grid_params["pi_gs"], capacity=cap,
            agent_names=agent_names, currency=currency, verbose=True,
        )
        print_subperiod_table(sp_results, currency=currency)
        p = plot_subperiod(sp_results, out_dir=plots_dir, currency=currency)
        if p:
            print(f"    ✓ Fig 16 — Análisis de sub-períodos")

        # Fig 17 — Robustez C4
        from visualization.plots import plot_robustness_c4
        p17 = plot_robustness_c4(wr_report, agent_names,
                                  out_dir=plots_dir, currency=currency)
        if p17:
            print(f"    ✓ Fig 17 — Robustez regulatoria C4")

        # Fig 18 — Heatmap 2D PGB×PV (solo si existe el parquet del barrido)
        sweep2d_path = os.path.join(base_dir, "outputs", "sensitivity_2d_pgb_pv.parquet")
        if os.path.exists(sweep2d_path):
            from analysis.sensitivity_2d import from_parquet
            from visualization.plots     import plot_fig18_heatmap_pgb_pv
            try:
                sweep2d = from_parquet(sweep2d_path)
                p18 = plot_fig18_heatmap_pgb_pv(sweep2d, out_dir=plots_dir,
                                                currency=currency)
                if p18:
                    print(f"    ✓ Fig 18 — Heatmap 2D PGB×PV")
            except Exception as e:
                print(f"    ✗ Fig 18: {e}")
        else:
            print(f"    (Fig 18 requiere: python scripts/sweep_pgb_pv.py)")

        # Fig 19 — Curva π_gb*ⁿ por agente (FA-1 individual)
        from visualization.plots import plot_fig19_desercion_individual
        try:
            p19 = plot_fig19_desercion_individual(
                fa_ir, agent_names, pi_gb_nominal=grid_params["pi_gb"],
                out_dir=plots_dir, currency=currency)
            if p19:
                print(f"    ✓ Fig 19 — Deserción individual por agente")
        except Exception as e:
            print(f"    ✗ Fig 19: {e}")

        # Fig 20 — Price of Fairness P2P vs C4
        from analysis.fairness   import compute_pof
        from visualization.plots import plot_fig20_price_of_fairness
        try:
            fr = compute_pof(
                net_benefit_per_agent=cr.net_benefit_per_agent,
                gini=cr.gini,
            )
            p20 = plot_fig20_price_of_fairness(fr, out_dir=plots_dir,
                                               currency=currency)
            if p20:
                print(f"    ✓ Fig 20 — Price of Fairness (PoF) P2P vs C4")
        except Exception as e:
            print(f"    ✗ Fig 20: {e}")

        # Fig 21 — Robustez C4 detallada por agente
        from visualization.plots import plot_fig21_robustez_c4_agente
        try:
            p21 = plot_fig21_robustez_c4_agente(fa_creg_rep, agent_names,
                                                out_dir=plots_dir,
                                                currency=currency)
            if p21:
                print(f"    ✓ Fig 21 — Robustez C4 detallada por agente")
        except Exception as e:
            print(f"    ✗ Fig 21: {e}")

        # Gráficas 7-9
        generate_sensitivity_plots(
            sa_pgb=sa_pgb, sa_pv=sa_pv,
            findings=thresholds,
            fa_desertion=fa_des, fa_creg=fa_creg_rep,
            p2p_results=p2p_results, pi_bolsa=pi_bolsa,
            D=D, agent_names=agent_names,
            out_dir=plots_dir, currency=currency,
            sa_ppa=sa_ppa,
            pi_gb=grid_params["pi_gb"],
            pi_gs=grid_params["pi_gs"],
            sa_pgs=sa_pgs,
        )

        # Exportar análisis a Excel
        _export_analysis(sa_pgb, sa_pv, fa_des, fa_creg_rep,
                          thresholds, base_dir, agent_names, fa_ir=fa_ir,
                          wr_report=wr_report, sc_risk=sc_risk)

    # ── Reporte de avances para asesores ─────────────────────────────────
    _generate_progress_report(
        cr=cr, p2p_results=p2p_results, G_klim=G_klim, D=D, G=G,
        agent_names=agent_names, currency=currency,
        use_real_data=use_real_data, full_horizon=full_horizon,
        sa_pgb=sa_pgb, sa_pv=sa_pv,
        fa_des=fa_des, fa_creg=fa_creg_rep, fa_ir=fa_ir,
        base_dir=base_dir,
        pi_gs_per_agent=pi_gs_per_agent,
        pi_gs_eff=pi_gs_eff if use_real_data else None,
    )

    t_total = time.time() - t_total_start
    print(f"\n✓ Completado en {t_total:.1f}s.")
    return cr, p2p_results


# ── Exportar Excel base ───────────────────────────────────────────────────────

def _export_base(cr, p2p_results, G_klim, D, base_dir, currency, daily_series=None):
    outputs_dir = os.path.join(base_dir, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    path = os.path.join(outputs_dir, "resultados_comparacion.xlsx")
    # CAL-39: lista dinámica — C5 entra al Excel cuando está presente
    # (antes el hardcode C1-C4 lo omitía de resultados_comparacion.xlsx).
    # CAL-42: C4_mensual entra igual, para que la base que el artículo publica
    # como principal salga de la corrida y no de un recálculo externo.
    esc  = [e for e in ["P2P", "C1", "C2", "C3", "C4", "C4_mensual", "C5"]
            if e in cr.net_benefit]
    N, T = G_klim.shape
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        # CAL-39 (D8): hoja Diagnostico — timestamp, modo y procedencia,
        # para detectar Excel stale entre corridas parciales y --full.
        try:
            import subprocess as _sp
            # CAL-43: el hash se resuelve contra la RAÍZ DEL REPOSITORIO, no
            # contra `base_dir` (que es el directorio de SALIDA y puede estar
            # fuera del árbol de git). Ese era el motivo de que la hoja
            # Diagnostico de las corridas canónicas trajera git_hash vacío y de
            # que la tesis tuviera que declarar la salvaguarda como incumplida.
            _repo = os.path.dirname(os.path.abspath(__file__))
            # CAL-43d: `-c safe.directory=<repo>`. En el servidor el repo es de
            # otro uid y el proceso corre como root, de modo que git aborta con
            # «detected dubious ownership», sale con 128 y `git_hash` quedaba en
            # "n/a" — el mismo campo vacío que CAL-43/A3 creía haber cerrado.
            # A3 atacaba el `cwd`; esta es la otra mitad de la causa.
            #
            # Se resuelve AQUI y no con `git config --global` a proposito: la
            # config global del servidor es su entorno, no nuestro, y cambiarla
            # altera la procedencia de lo que se entrega. `-c` afecta solo a
            # esta invocacion.
            _git = _sp.run(["git", "-c", "safe.directory=%s" % _repo,
                            "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, cwd=_repo,
                           timeout=5).stdout.strip() or "n/a"
        except Exception:                                  # noqa: BLE001
            _git = "n/a"
        # CAL-43: PROCEDENCIA DE LOS DATOS, en el artefacto y no solo en el log.
        # `get_pi_bolsa` sustituye la serie real por una SINTETICA cuando no
        # encuentra fuente, y hasta ahora el único rastro era una línea de
        # stdout: una corrida entera podía salir de precios inventados sin que
        # el .xlsx lo dijera. Es la misma clase de fallo que CAL-28b.
        try:
            from data import xm_prices as _xmp
            _fuente_bolsa = _xmp.ULTIMA_FUENTE or "desconocida"
        except Exception:                                  # noqa: BLE001
            _fuente_bolsa = "desconocida"
        pd.DataFrame([{
            "generado": pd.Timestamp.now().isoformat(timespec="seconds"),
            "n_horas": T, "n_agentes": N,
            "escenarios": ",".join(esc),
            "git_hash": _git,
            "fuente_bolsa": _fuente_bolsa,
            "mte_root": os.environ.get("MTE_ROOT", "(default del repo)"),
            "comando": " ".join(sys.argv),
        }]).to_excel(w, sheet_name="Diagnostico", index=False)
        pd.DataFrame({
            "Escenario": esc,
            f"Ganancia_neta_{currency}": [cr.net_benefit[e] for e in esc],
            "SC": [cr.self_consumption.get(e, 0) for e in esc],
            "SS": [cr.self_sufficiency.get(e, 0) for e in esc],
            "IE": [cr.equity_index.get(e, 0) for e in esc],
        }).to_excel(w, sheet_name="Resumen", index=False)
        pd.DataFrame([{"Agente": f"A{n+1}",
                        **{e: cr.net_benefit_per_agent[e][n] for e in esc}}
                       for n in range(cr.n_agents)]
                     ).to_excel(w, sheet_name="Por_agente", index=False)
        pd.DataFrame([{
            "Hora": r.k+1,
            "kWh_P2P": float(np.sum(r.P_star)) if r.P_star is not None else 0,
            "SC": r.SC, "SS": r.SS, "IE": r.IE,
            "PS_%": r.PS, "PSR_%": r.PSR,
            "Wj": r.Wj_total, "Wi": r.Wi_total,
        } for r in p2p_results]).to_excel(w, sheet_name="P2P_horario", index=False)
        fr = cr.fairness
        pd.DataFrame([{
            "RPE_P2P_vs_C4":         cr.rpe,
            "PoF_Bertsimas2011":      fr.pof if fr is not None else None,
            "PoF_W_eff_COP":          fr.w_eff if fr is not None else None,
            "PoF_W_fair_COP":         fr.w_fair if fr is not None else None,
            "PoF_escenario_eficiente": fr.eff_scenario if fr is not None else None,
            "PoF_escenario_equitativo": fr.fair_scenario if fr is not None else None,
            "Spread_C4_kWh":         float(np.sum(cr.static_spread_24h))
                                      if cr.static_spread_24h is not None else 0,
            # Act 3.3 — Bienestar de optimización (u.o.)
            "W_sellers_total_uo":    cr.W_sellers_total,
            "W_buyers_total_uo":     cr.W_buyers_total,
            "W_total_uo":            cr.W_sellers_total + cr.W_buyers_total,
            "Nota_W":                "u.o.=unidades optimizacion; no son COP",
        }]).to_excel(w, sheet_name="Metricas_extra", index=False)
        # Hoja PoF_Fairness — tabla curva de equidad ordenada por Gini
        if fr is not None and fr.gini_ranking:
            from analysis.fairness import fairness_curve
            curve = fairness_curve(cr.net_benefit_per_agent, cr.gini)
            pd.DataFrame(curve).to_excel(w, sheet_name="PoF_Fairness", index=False)
        if daily_series is not None and not daily_series.empty:
            daily_series.to_excel(w, sheet_name="Series_diarias", index=True)
    return path


# ── Series diarias para bootstrap estadístico ─────────────────────────────────

def _compute_daily_series(
    D, G_klim, p2p_results,
    pi_gs, pi_gb, pi_bolsa, pde, cap, prosumer_ids, consumer_ids,
    component_c="auto", tolls=None,          # CAL-41
):
    """
    Agrega beneficio neto comunitario por día para P2P y C4.
    Llama solo a las funciones de liquidación (NO re-corre el EMS).

    Retorna DataFrame(n_days, 2) con columnas ['nb_p2p', 'nb_c4'] en COP/día.
    Actividad 4.2 — soporte para bootstrap por bloques.
    """
    from scenarios.comparison_engine import _p2p_monetary_benefit
    from scenarios.scenario_c4_creg101072 import run_c4_creg101072
    from scenarios._pi_gs import as_pi_gs_array

    T      = D.shape[1]
    N      = D.shape[0]
    n_days = T // 24

    # CAL-9: normalizar pi_gs a matriz (N, T) y slicear por día. Cada día
    # liquida con la tarifa Cedenar del mes que contiene esas 24 horas.
    pi_gs_full = as_pi_gs_array(pi_gs, N, T)

    rows = []
    for d in range(n_days):
        sl = slice(d * 24, (d + 1) * 24)
        D_d = D[:, sl]
        G_d = G_klim[:, sl]
        pi_gs_d = pi_gs_full[:, sl]   # (N, 24) — tarifa del día

        nb_p2p = _p2p_monetary_benefit(
            p2p_results[d * 24 : (d + 1) * 24],
            D_d, G_d, pi_gs_d, pi_gb, prosumer_ids,
            pi_bolsa=pi_bolsa[sl],   # CAL-30: residual surplus horario
        ).sum()

        # CAL-41: el slice diario se liquida con la MISMA deducción que la
        # tabla agregada. Antes usaba component_c="auto" (proporcional
        # 13,85 %) porque el slice no lleva calendario mensual; pero la
        # matriz Cvm sí es recortable por índice horario, y usar el fallback
        # dejaba la suma de la serie 0,22 % por encima del total de la
        # comparación — desfase que contaminaba el bootstrap.
        cc_d = (component_c[:, sl]
                if isinstance(component_c, np.ndarray) and component_c.ndim == 2
                else component_c)
        tl_d = (tolls[:, sl]
                if isinstance(tolls, np.ndarray) and tolls.ndim == 2
                else tolls)
        # CAL-43: el bootstrap liquida C4 en base HORARIA a proposito, y no
        # en la mensual de CAL-42. La razon es metodologica, no un olvido:
        # la serie es DIARIA y un dia no es un periodo de facturacion, de
        # modo que no hay permuta mensual que cruzar dentro del bloque.
        # Consecuencia util: el bootstrap de esta corrida es directamente
        # comparable con el que publica el articulo, que tambien se
        # remuestrea contra el C4 Caso 2 horario (CANON.md §3.2).
        c4 = run_c4_creg101072(
            D_d, G_d, pi_gs_d, pi_bolsa[sl], pde, cap,
            component_c=cc_d, tolls=tl_d,
        )
        nb_c4 = sum(c4["per_agent"][n]["net_benefit"] for n in range(N))

        rows.append({"dia": d, "nb_p2p": float(nb_p2p), "nb_c4": float(nb_c4)})

    return pd.DataFrame(rows).set_index("dia")


# ── Exportar análisis de sensibilidad a Excel ─────────────────────────────────

def _export_analysis(sa_pgb, sa_pv, fa_des, fa_creg, thresholds, base_dir, agent_names,
                     fa_ir=None, wr_report=None, sc_risk=None):
    outputs_dir = os.path.join(base_dir, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    path = os.path.join(outputs_dir, "resultados_analisis.xlsx")
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        if sa_pgb:
            rows = []
            for r in sa_pgb:
                row = {"PGB_COP_kWh": r.param_value,
                       "IE_P2P": r.ie_p2p, "RPE": r.rpe,
                       "Horas_mercado": r.market_hours, "kWh_P2P": r.kwh_p2p}
                # CAL-43: lo que el barrido TRAIGA, no una lista fija. El
                # hardcode dejaba fuera del Excel el C4_mensual que el
                # propio barrido ya calcula, y con el la base que publica
                # el articulo habria seguido viniendo de fuera.
                row.update({f"Net_{e}": v
                            for e, v in r.net_benefit.items()})
                rows.append(row)
            pd.DataFrame(rows).to_excel(w, sheet_name="SA1_PGB", index=False)

        if sa_pv:
            rows = []
            for r in sa_pv:
                row = {"PV_factor": r.param_value,
                       "Cobertura_pct": r.param_value * 0.113 * 100,
                       "IE_P2P": r.ie_p2p, "SS_P2P": r.ss_p2p,
                       "Horas_mercado": r.market_hours, "kWh_P2P": r.kwh_p2p}
                row.update({f"Net_{e}": v            # CAL-43
                            for e, v in r.net_benefit.items()})
                rows.append(row)
            pd.DataFrame(rows).to_excel(w, sheet_name="SA2_PV", index=False)

        if fa_creg:
            rows = []
            for name in agent_names:
                rows.append({
                    "Agente": name,
                    "Participacion_pct": fa_creg.max_supply_share_by_agent.get(name, 0),
                    "Cumple_10pct": name not in fa_creg.rule_10pct_violations,
                    "Capacidad_max_kW": fa_creg.max_capacity_by_agent.get(name, 0),
                    "Cumple_100kW": name not in fa_creg.rule_100kw_violations,
                })
            rows.append({"Agente": "COMUNIDAD",
                          "Robustez_C4": fa_creg.robustness_score})
            pd.DataFrame(rows).to_excel(w, sheet_name="FA_CREG101072", index=False)

        pd.DataFrame([thresholds]).to_excel(w, sheet_name="Umbrales", index=False)

        # §3.14 — Racionalidad Individual
        if fa_ir:
            rows_ir = []
            for name in agent_names:
                rows_ir.append({
                    "Agente":         name,
                    "B_P2P_COP":      fa_ir.benefit_p2p.get(name, 0),
                    "B_C4_COP":       fa_ir.benefit_c4.get(name, 0),
                    "Delta_n_COP":    fa_ir.surplus_vs_c4.get(name, 0),
                    "Delta_n_rel":    fa_ir.surplus_rel.get(name, 0),
                    "pi_gb_critico":  fa_ir.critical_pgb.get(name, 0),
                    "Estado":         ("estable" if name in fa_ir.stable_agents
                                       else "en_riesgo"),
                })
            pd.DataFrame(rows_ir).to_excel(
                w, sheet_name="FA_DesercionIR", index=False)

            # Tabla de sensibilidad Δ_n(pi_gb)
            rows_sens = []
            for pgb_v, row_d in sorted(fa_ir.pgb_vs_surplus.items()):
                row = {"pi_gb": pgb_v}
                for name in agent_names:
                    row[f"delta_{name}"] = row_d.get(name, 0)
                row["delta_total"] = sum(row_d.values())
                rows_sens.append(row)
            pd.DataFrame(rows_sens).to_excel(
                w, sheet_name="DesercionIR_Sensibilidad", index=False)

        # FA-3: Robustez — retiro de participante
        if wr_report is not None and wr_report.by_agent:
            rows_wr = []
            for name, d in wr_report.by_agent.items():
                rows_wr.append({
                    "Agente_retirado":      name,
                    "AGRC_restante_cumple": d["compliant"],
                    "B_C4_full_COP":        d["B_C4_full"],
                    "B_C4_remaining_COP":   d["B_C4_remaining"],
                    "B_fallback_COP":       d["B_fallback"],
                    "B_P2P_remaining_COP":  d["B_P2P_remaining"],
                    "loss_C4_COP":          d["loss_C4"],
                    "flexibility_premium_COP": d["flexibility_premium"],
                    "reglas_violadas":      ",".join(d["violated_rules"]) or "—",
                })
            pd.DataFrame(rows_wr).to_excel(
                w, sheet_name="FA3_Robustez_Retiro", index=False)

        # FA-4: Robustez — escalamiento
        if sc_risk is not None:
            rows_sc = []
            for name, d in sc_risk.items():
                rows_sc.append({
                    "Agente":         name,
                    "G_mean_kW":      d["g_mean_kw"],
                    "G_max_kW":       d["g_max_kw"],
                    "Share_actual_%": d["share_pct"],
                    "2x_cumple":      d["2x_ok"],
                    "3x_cumple":      d["3x_ok"],
                    "Escala_max_ok":  d["max_ok_scale"],
                })
            pd.DataFrame(rows_sc).to_excel(
                w, sheet_name="FA4_Robustez_Escala", index=False)

    print(f"    Excel análisis → {path}")
    return path


# ── Reporte de avances para asesores (Markdown) ───────────────────────────────

def _generate_progress_report(cr, p2p_results, G_klim, D, G,
                               agent_names, currency, use_real_data,
                               full_horizon, sa_pgb, sa_pv,
                               fa_des, fa_creg, base_dir, fa_ir=None,
                               pi_gs_per_agent=None, pi_gs_eff=None):
    """
    Genera un reporte Markdown con los resultados actuales para presentar
    a los asesores Andrés Pantoja y Germán Obando.
    """
    from datetime import datetime
    now   = datetime.now().strftime("%Y-%m-%d %H:%M")
    N, T  = G_klim.shape
    esc   = [e for e in ["P2P", "C1", "C2", "C3", "C4", "C4_mensual",   # CAL-43
                         "C5"] if e in cr.net_benefit]

    active = [r for r in p2p_results
              if r.P_star is not None and np.sum(r.P_star) > 1e-4]
    kwh_p2p = sum(float(np.sum(r.P_star)) for r in active)

    data_mode = ("Empíricos MTE — " + ("6144h completas" if full_horizon
                  else "perfil diario promedio (24h)")) if use_real_data else "Sintéticos (validación)"

    lines = [
        "# Reporte de Avances — Tesis P2P Colombia",
        "",
        f"**Autor:** Brayan S. Lopez-Mendez | **Fecha:** {now}",
        f"**Asesores:** Andrés Pantoja · Germán Obando | **Udenar, 2026**",
        "",
        "---",
        "",
        "## 1. Estado del modelo",
        "",
        f"| Parámetro | Valor |",
        f"|-----------|-------|",
        f"| Datos | {data_mode} |",
        f"| Agentes | {N} instituciones Pasto (MTE) |",
        f"| Horizonte | {T}h ({T//24} días) |",
        f"| Horas con mercado P2P | {len(active)}/{T} ({len(active)/T*100:.1f}%) |",
        f"| Energía P2P total | {kwh_p2p:.1f} kWh/período |",
    ]
    if use_real_data and pi_gs_per_agent is not None:
        # CAL-9: tarifa Cedenar mensual con matriz (N, T) en C1-C4 (--full/--day),
        # vector (N,) en perfil diario.
        per_agent_str = " · ".join(
            f"{n}={int(round(v))}"
            for n, v in zip(agent_names, pi_gs_per_agent)
        )
        eff_val = (f"{pi_gs_eff:.0f}" if pi_gs_eff is not None
                   else f"{float(np.mean(pi_gs_per_agent)):.0f}")
        regimen = ("matriz N×T mes a mes (CAL-9)" if full_horizon
                    else "vector (N,) — perfil diario CAL-8")
        lines.append(
            f"| π_gs en C1–C4 (régimen) | {regimen} |"
        )
        lines.append(
            f"| π_gs por agente (promedio horizonte) | "
            f"{per_agent_str} {currency}/kWh |"
        )
        lines.append(
            f"| π_gs comunitario informativo | {eff_val} {currency}/kWh "
            f"(legacy escalar PGS_COP={PGS_COP:.0f} deprecado) |"
        )
        lines.append(
            f"| π_gb (precio bolsa promedio) | "
            f"{(PGB_COP if use_real_data else PGB):.0f} {currency}/kWh |"
        )
    else:
        lines.append(
            f"| Precios | PGS={PGS_COP if use_real_data else PGS} · "
            f"PGB={PGB_COP if use_real_data else PGB} {currency}/kWh |"
        )
    lines += [
        "",
        "## 2. Datos empíricos MTE",
        "",
        "| Institución | D̄ (kW) | Ḡ (kW) | Cobertura PV |",
        "|-------------|---------|---------|-------------|",
    ]

    for n in range(N):
        name = agent_names[n]
        d_m  = float(D[n].mean())
        g_m  = float(G[n].mean())
        cov  = g_m / max(d_m, 1e-6) * 100
        lines.append(f"| {name} | {d_m:.1f} | {g_m:.1f} | {cov:.0f}% |")

    d_tot = float(D.sum())
    g_tot = float(G.sum())
    lines += [
        f"| **Comunidad** | **{D.mean(axis=1).sum():.1f}** | **{G.mean(axis=1).sum():.1f}** | **{g_tot/max(d_tot,1)*100:.1f}%** |",
        "",
        "## 3. Resultados comparación regulatoria",
        "",
        f"| Escenario | Ganancia neta ({currency}) | SC | SS | IE |",
        "|-----------|--------------------------|-----|-----|-----|",
    ]

    # CAL-43d: este es el SEGUNDO diccionario de etiquetas del fichero (el otro
    # está en `main`, ~línea 475). Al añadir C4_mensual solo se actualizó aquél,
    # y este reventó con `KeyError: 'C4_mensual'` — en el servidor, el
    # 2026-08-08, DESPUÉS de escribir los dos Excel y todas las figuras. Habría
    # reventado igual con C5, presente desde CAL-37.
    #
    # Dos cambios, no uno: se completan las etiquetas Y se pasa a `.get` con
    # respaldo. El subíndice desnudo convierte «falta una etiqueta» —cosmético—
    # en «se cae la corrida entera», que es un cambio de gravedad que ningún
    # informe de progreso justifica.
    esc_labels = {
        "P2P": "P2P (Stackelberg + RD)",
        "C1": "C1 CREG 174/2021",
        "C2": "C2 Contrato interno",
        "C3": "C3 Mercado spot",
        "C4": "C4 CREG 101 072 ★ (horario)",
        "C4_mensual": "C4 CREG 101 072 ★ (mensual)",
        "C5": "C5 AGR CREG 101 099/2026",
    }
    for e in esc:
        nb = cr.net_benefit.get(e, 0)
        sc = cr.self_consumption.get(e, 0)
        ss = cr.self_sufficiency.get(e, 0)
        ie = cr.equity_index.get(e, 0)
        lines.append(f"| {esc_labels.get(e, e)} | {nb:,.0f} | {sc:.3f} "
                     f"| {ss:.3f} | {ie:.4f} |")

    rpe = cr.rpe or 0
    spread = float(np.sum(cr.static_spread_24h)) if cr.static_spread_24h is not None else 0
    lines += [
        "",
        f"**RPE (P2P vs C4):** {rpe:.4f}",
        f"**Spread ineficiencia estática C4:** {spread:.3f} kWh/período",
        "",
        "### 3.1 Ventaja P2P vs C4 por institución",
        "",
        f"| Institución | P2P ({currency}) | C4 ({currency}) | Ventaja P2P ({currency}) |",
        "|-------------|---------|---------|-----------------|",
    ]

    for n in range(N):
        name  = agent_names[n]
        p2p_n = cr.net_benefit_per_agent["P2P"][n]
        c4_n  = cr.net_benefit_per_agent["C4"][n]
        delta = p2p_n - c4_n
        sign  = "+" if delta >= 0 else ""
        win   = "✓ P2P mejor" if delta > 0 else "✗ C4 mejor"
        lines.append(f"| {name} | {p2p_n:,.0f} | {c4_n:,.0f} | {sign}{delta:,.0f} {win} |")

    lines += [
        "",
        "### 3.2 Nota sobre C1 = C3",
        "",
        "Con el perfil diario promedio de datos MTE, C1 (CREG 174) y C3 (Mercado spot)",
        "producen resultados idénticos. Esto es **correcto matemáticamente**: cuando la",
        "cobertura PV es 11% y G < D en el 100% de las horas, ningún nodo tiene excedente",
        "para vender a bolsa, por lo que el mecanismo de liquidación es irrelevante.",
        "La diferencia entre C1 y C3 aparecerá con precios de bolsa XM horarios reales",
        "y en días con baja demanda institucional (fines de semana, festivos).",
        "",
        "## 4. Métricas del mercado P2P",
        "",
        "| Métrica | Valor | Interpretación |",
        "|---------|-------|----------------|",
    ]

    sc_p2p = cr.self_consumption.get("P2P", 0)
    ss_p2p = cr.self_sufficiency.get("P2P", 0)
    ie_p2p = cr.equity_index.get("P2P", 0)
    ie_c4  = cr.equity_index.get("C4", 0)
    lines += [
        f"| SC (P2P) | {sc_p2p:.3f} | Fracción demanda cubierta internamente |",
        f"| SS (P2P) | {ss_p2p:.3f} | Fracción generación usada en comunidad |",
        f"| IE (P2P) | {ie_p2p:.4f} | Distribución beneficio (0=equitativo) |",
        f"| IE (C4)  | {ie_c4:.4f} | Referencia regulatoria vigente |",
        f"| RPE      | {rpe:.4f} | Rendimiento relativo P2P vs C4 |",
    ]
    if cr.fairness is not None and cr.fairness.eff_scenario:
        fr = cr.fairness
        lines.append(
            f"| PoF      | {fr.pof:.4f} | Price of Fairness [Bertsimas 2011]: "
            f"eficiente={fr.eff_scenario}, equitativo={fr.fair_scenario} |"
        )
    lines.append("")

    # Sensibilidad si disponible
    if sa_pgb:
        lines += [
            "## 5. Análisis de sensibilidad",
            "",
            "### SA-1: Variación precio de bolsa PGB",
            "",
            f"| PGB (COP/kWh) | P2P ({currency}) | C4 ({currency}) | IE P2P | RPE |",
            "|---------------|---------|---------|--------|-----|",
        ]
        for r in sa_pgb:
            lines.append(
                f"| {r.param_value:.0f} | {r.net_benefit['P2P']:,.0f} | "
                f"{r.net_benefit['C4']:,.0f} | {r.ie_p2p:.3f} | {r.rpe:.3f} |")

    if sa_pv:
        lines += [
            "",
            "### SA-2: Variación cobertura PV",
            "",
            f"| Factor PV | Cobertura (%) | P2P ({currency}) | C4 ({currency}) | Horas mercado | kWh P2P |",
            "|-----------|--------------|---------|---------|--------------|---------|",
        ]
        for r in sa_pv:
            cov = r.param_value * 0.113 * 100
            lines.append(
                f"| {r.param_value:.2f}x | {cov:.0f}% | "
                f"{r.net_benefit['P2P']:,.0f} | {r.net_benefit['C4']:,.0f} | "
                f"{r.market_hours} | {r.kwh_p2p:.1f} |")

    # Factibilidad si disponible
    if fa_des and fa_creg:
        lines += [
            "",
            "## 6. Análisis de factibilidad",
            "",
            "### FA-1: Condición de deserción del P2P",
            "",
            f"- Precio P2P nunca menor que bolsa: **{'Sí' if fa_des.condition_never_met else 'No'}**",
            f"- Umbral crítico precio bolsa: **{fa_des.critical_pgb_threshold:.0f} COP/kWh**",
            "",
            "### FA-2: Cumplimiento CREG 101 072/2025",
            "",
            f"| Institución | Participación (%) | Cumple 10% | Cap. max (kW) | Cumple 100kW |",
            "|-------------|------------------|-----------|--------------|-------------|",
        ]
        for name in agent_names:
            sh  = fa_creg.max_supply_share_by_agent.get(name, 0)
            cap = fa_creg.max_capacity_by_agent.get(name, 0)
            c10 = "✓" if name not in fa_creg.rule_10pct_violations else "✗"
            c100= "✓" if name not in fa_creg.rule_100kw_violations  else "✗"
            lines.append(f"| {name} | {sh:.2f}% | {c10} | {cap:.1f} | {c100} |")
        lines += [
            "",
            f"**Score de robustez C4:** {fa_creg.robustness_score:.2f} (1=máxima robustez)",
        ]

    # §3.14 — Racionalidad Individual
    if fa_ir:
        lines += [
            "",
            "### FA-1b: Deserción — Condición de Racionalidad Individual (§3.14)",
            "",
            "**Definición formal (Restricción IR):**",
            "Agente n permanece en P2P sii `B_n^P2P(π) ≥ max(B_n^C1, B_n^C4)(π)`",
            "",
            "Donde `Δ_n = B_n^P2P − max(B_n^C1, B_n^C4)` (>0 → agente prefiere P2P). ",
            "Umbral crítico `π_gb^*_n`: precio de bolsa donde el agente es indiferente.",
            "",
            f"| Agente | B_P2P ({currency}) | B_alt ({currency}) | Δ_n ({currency}) | Δ_n/B_alt | π_gb^*_n | Estado |",
            "|--------|---------|---------|---------|----------|---------|--------|",
        ]
        for name in agent_names:
            b_p2p = fa_ir.benefit_p2p.get(name, 0)
            b_c4  = fa_ir.benefit_c4.get(name, 0)
            delta = fa_ir.surplus_vs_c4.get(name, 0)
            rel   = fa_ir.surplus_rel.get(name, 0)
            thr   = fa_ir.critical_pgb.get(name, 0)
            estado = "estable" if name in fa_ir.stable_agents else "en riesgo"
            pgb_arr = sorted(fa_ir.pgb_vs_surplus.keys())
            thr_str = f">rango" if pgb_arr and thr > max(pgb_arr) * 1.05 else f"{thr:.0f}"
            sign = "+" if delta >= 0 else ""
            lines.append(
                f"| {name} | {b_p2p:,.0f} | {b_c4:,.0f} | "
                f"{sign}{delta:,.0f} | {rel:+.1%} | {thr_str} | {estado} |")

        comm_thr = fa_ir.community_critical_pgb
        agg_thr  = fa_ir.community_agg_critical_pgb
        pgb_arr  = sorted(fa_ir.pgb_vs_surplus.keys())
        comm_str = (f"{comm_thr:.0f}" if pgb_arr and comm_thr < max(pgb_arr) * 1.05
                    else f">rango (>{max(pgb_arr) if pgb_arr else '?'})")
        agg_str  = (f"{agg_thr:.0f}" if pgb_arr and agg_thr < max(pgb_arr) * 1.05
                    else f">rango (>{max(pgb_arr) if pgb_arr else '?'})")
        lines += [
            "",
            f"**Agentes estables ({len(fa_ir.stable_agents)}/{len(agent_names)}):** "
            f"{', '.join(fa_ir.stable_agents) or 'ninguno'}",
            f"**Umbral comunitario (mediana individual):** {comm_str} COP/kWh",
            f"**Umbral agregado P2P < max(C1,C4):** {agg_str} COP/kWh",
            "",
            "**Tabla Δ_n(pi_gb) — sensibilidad a precio de bolsa:**",
            "",
        ]
        # Header de la tabla sensibilidad
        hdr = "| pi_gb |" + "".join(f" {n} |" for n in agent_names) + " Σ Δ |"
        sep = "|-------|" + "".join("--------|" for _ in agent_names) + "--------|"
        lines += [hdr, sep]
        for pgb_v in sorted(fa_ir.pgb_vs_surplus.keys()):
            row_d = fa_ir.pgb_vs_surplus[pgb_v]
            total = sum(row_d.values())
            sign_t = "+" if total >= 0 else ""
            row = f"| {pgb_v:.0f} |"
            for name in agent_names:
                d = row_d.get(name, 0)
                sign_d = "+" if d >= 0 else ""
                row += f" {sign_d}{d:,.0f} |"
            row += f" {sign_t}{total:,.0f} |"
            lines.append(row)

    lines += [
        "",
        "---",
        "",
        "## 7. Estado de implementación",
        "",
        "### Completado ✅",
        "- Horizonte completo 6144h (MedicionesMTE_v3, 256 días, Abr–Dic 2025)",
        "- Precios XM horarios con patrón intradiario calibrado (`data/xm_prices.py`)",
        "- Análisis sub-períodos laborable/finde × julio/enero (`analysis/subperiod.py`)",
        "- Sensibilidad SA-1/2/3/3b (`analysis/sensitivity.py`)",
        "- Análisis de optimalidad P2P vs C4 hora a hora (`analysis/optimality.py`)",
        "- Factibilidad FA-1/2/3/4 (`analysis/feasibility.py`)",
        "- Bootstrap Kunsch + Wilcoxon (`tests/statistical_tests.py`) — "
        "corrida canónica 2026-06-11 (seed 42): Δ(P2P−C4) significativo en "
        "ambas coberturas (M1 d=0.84, M3 d=0.72)",
        "- GSA Sobol/Saltelli COMPLETADO (n_base=128, 1999/2048 válidas, "
        "2026-06-11): factor_PV domina ganancia/SC; PGB domina IE",
        "- Escenario C5/AGR (CREG 101 099) en comparación, PoF y SA-1/2 "
        "(CAL-37/39)",
        "- **Price of Fairness formal** (`analysis/fairness.py`) — Act 3.3",
        "",
        "### Pendiente 🔲",
        "- Decisiones con asesores: S1-S9 + PGB nominal + NT2 "
        "(`Documentos/preguntas_asesores_S1-S9.md`)",
        "- Verificar LCOE real de inversores (dato de campo, no de código)",
        "",
        "---",
        f"*Generado automáticamente por main_simulation.py · {now}*",
    ]

    os.makedirs(os.path.join(base_dir, "outputs"), exist_ok=True)
    path = os.path.join(base_dir, "outputs", "REPORTE_AVANCES.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"    Reporte asesores → {path}")
    return path


# ── Punto de entrada ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    # CRÍTICO en Windows: freeze_support evita que ProcessPoolExecutor
    # re-ejecute este script en cada worker (produce banner duplicado).
    import multiprocessing
    multiprocessing.freeze_support()

    ap = argparse.ArgumentParser(
        description="Simulación P2P — Tesis Brayan López, Udenar 2026")
    ap.add_argument("--data", choices=["synthetic", "real"], default="synthetic")
    ap.add_argument("--full", action="store_true",
                    help="Horizonte completo 6144h")
    ap.add_argument("--analysis", action="store_true",
                    help="Análisis de sensibilidad y factibilidad")
    ap.add_argument("--day", type=str, default=None,
                    help="Día específico YYYY-MM-DD (implica --data real, 24h)")
    ap.add_argument("--gsa", action="store_true",
                    help="Ejecutar análisis de sensibilidad global Sobol/Saltelli")
    ap.add_argument("--n-base", type=int, default=64, metavar="N",
                    help="Tamaño base muestra Saltelli (default 64 → 1024 eval.)")
    ap.add_argument("--paper-meters", action="store_true",
                    help="CAL-36: escenario M3 sub-medidores (demanda = circuito "
                         "PV, cobertura ~89%%; mismos medidores del paper CAL-28)")
    ap.add_argument("--out-dir", type=str, default=None, metavar="DIR",
                    help="CAL-43: carpeta destino de outputs/ y graficas/ "
                         "(por defecto, la raiz del repositorio)")
    ap.add_argument("--paso", type=float, default=1.0, metavar="H",
                    help="CAL-46: duracion del paso en horas. 1.0 (defecto) "
                         "es el eje canonico; 0.25 corre la sonda de quince "
                         "minutos. Ver docs/adr/0046-cal46-sonda-quince-"
                         "minutos.md")
    ap.add_argument("--desde", type=str, default=None, metavar="YYYY-MM-DD",
                    help="CAL-46: inicio de la ventana acotada")
    ap.add_argument("--hasta", type=str, default=None, metavar="YYYY-MM-DD",
                    help="CAL-46: fin de la ventana acotada, excluido")
    ap.add_argument("--almacen", default=None, metavar="CARPETA",
                    help="C-161: vuelca la corrida al almacen, con las "
                         "trayectorias de cada hora y sus multiplicadores, "
                         "para poder dibujar cualquier hora sin volver a "
                         "simular. Requiere --metodo acoplado para las "
                         "trayectorias")
    ap.add_argument("--procesos", type=int, default=None, metavar="N",
                    help="C-169: cuantos procesos abre el mercado. Sin la "
                         "bandera se usan TODOS los nucleos utiles, que son "
                         "los que la afinidad permite y no los que la maquina "
                         "declara. Tambien se lee de la variable de entorno "
                         "del lanzador del servidor.")
    ap.add_argument("--metodo", choices=["alternado", "acoplado"],
                    default="alternado",
                    help="CAL-48: 'acoplado' integra precios y cantidades "
                         "juntos como el modelo base; 'alternado' (defecto) "
                         "es el comportamiento historico")
    ap.add_argument("--permitir-alternado", dest="permitir_alternado",
                    action="store_true",
                    help="CAL-48: permite el horizonte completo por la via "
                         "alternada. Solo para comparar las dos vias; el "
                         "canon va acoplado y hay que declararlo si se usa")
    ap.add_argument("--t-span-acoplado", type=float, default=0.05,
                    metavar="T",
                    help="CAL-48: horizonte del solucionador acoplado")
    ap.add_argument("--competencia", dest="buyer_competition",
                    choices=["aggregate", "matlab", "matrix"],
                    default="aggregate",
                    help="CAL-49: forma del termino de competencia del "
                         "comprador. 'aggregate' (defecto) es la decision "
                         "del 2026-09-06; 'matlab' es la linea activa del "
                         "modelo base; 'matrix' es la ecuacion (11) de la "
                         "version arbitrada")
    ap.add_argument("--no-regulado", dest="exencion_contribucion",
                    action="store_true",
                    help="CAL-47: trata a las cinco como usuarios no regulados. "
                         "La tabla publicada pasa a ser referencia y se lee su "
                         "fila sin la contribucion de solidaridad")
    ap.add_argument("--include-c5", action="store_true",
                    help="CAL-37/39: añade el escenario C5 AGR (CREG 101 099) "
                         "a la comparación, al PoF y a los barridos SA-1/SA-2 "
                         "(FA-2 de la 101 072 no aplica a C5; SA-3 tampoco — "
                         "su pgs sintético no define la tasa no-regulada)")
    args = ap.parse_args()

    # ── CAL-39: validación de combinaciones de flags (antes, combinaciones
    # inválidas se ignoraban en silencio: --gsa descartaba --full/--analysis/
    # --include-c5/--paper-meters sin avisar; --day pisaba --full) ──────────
    if args.gsa and (args.full or args.analysis or args.include_c5
                     or args.paper_meters or args.day):
        ap.error("--gsa corre el modelo de referencia sintético y es "
                 "incompatible con --full/--analysis/--include-c5/"
                 "--paper-meters/--day")
    if args.day and args.full:
        ap.error("--day y --full son mutuamente exclusivos")

    # CAL-48, activado el 2026-09-07: la corrida canonica va ACOPLADA.
    #
    # El lazo alternado no resuelve el modelo base y deja el precio pegado a
    # una cota en el 72 % de los casos, frente al 1,2 % del acoplado (H-38).
    # Todo lo que el documento mide sale de la via acoplada, de modo que un
    # canon alternado reportaria un objeto distinto del que el documento
    # describe.
    #
    # Se exige explicito en vez de cambiar el defecto, para que ninguna
    # corrida antigua cambie de comportamiento en silencio. Y se puede
    # forzar, porque comparar las dos vias sobre el horizonte es una medicion
    # legitima; lo que no es legitimo es hacerlo sin querer.
    if args.full and args.metodo == "alternado" and not args.permitir_alternado:
        ap.error(
            "La corrida de horizonte completo va por la via ACOPLADA desde "
            "CAL-48. Anada --metodo acoplado.\n"
            "  Por que: el lazo alternado deja el precio pegado a una cota en "
            "el 72 % de los casos y no resuelve el modelo base (H-38), y todo "
            "lo que el documento mide sale de la via acoplada.\n"
            "  Si de verdad quiere el horizonte alternado, para comparar las "
            "dos vias, anada --permitir-alternado y declarelo donde publique.")

    if args.gsa:
        from analysis.global_sensitivity import (
            run_sobol_analysis, compute_indices, save_results)
        import multiprocessing
        multiprocessing.freeze_support()
        # CAL-39: el prompt interactivo solo con TTY — bajo nohup/tee el
        # stdin está cerrado e input() reventaba el GSA en el server.
        if args.n_base >= 256 and sys.stdin is not None and sys.stdin.isatty():
            ans = input(
                f"--n-base={args.n_base} genera "
                f"{args.n_base*(2*7+2)} evaluaciones (~5 h). "
                "Confirmar [s/N]: "
            )
            if ans.strip().lower() != "s":
                print("Cancelado.")
                sys.exit(0)
        elif args.n_base >= 256:
            print(f"[gsa] no-TTY: continuando con --n-base={args.n_base} "
                  f"({args.n_base*(2*7+2)} evaluaciones) sin confirmación")
        Y_dict   = run_sobol_analysis(n_base=args.n_base, seed=42, parallel=True)
        idx_dict = compute_indices(Y_dict)
        out_path = save_results(idx_dict, Y_dict=Y_dict)
        print(f"\nGSA completado. Resultados en: {out_path}")
    elif args.day:
        main(use_real_data=True, full_horizon=False, run_analysis=args.analysis,
             single_day=args.day, paper_meters=args.paper_meters,
             include_c5=args.include_c5, out_dir=args.out_dir,
             metodo=args.metodo, t_span_acoplado=args.t_span_acoplado,
             almacen=args.almacen,
             procesos=_procesos_pedidos(args),
             buyer_competition=args.buyer_competition,
             exencion_contribucion=args.exencion_contribucion)
    else:
        main(use_real_data=(args.data == "real"),
             full_horizon=args.full,
             run_analysis=args.analysis,
             paper_meters=args.paper_meters,
             include_c5=args.include_c5, out_dir=args.out_dir,
             paso=args.paso, desde=args.desde, hasta=args.hasta,
             metodo=args.metodo, t_span_acoplado=args.t_span_acoplado,
             almacen=args.almacen,
             procesos=_procesos_pedidos(args),
             buyer_competition=args.buyer_competition,
             exencion_contribucion=args.exencion_contribucion)
