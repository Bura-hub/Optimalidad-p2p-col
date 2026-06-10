"""
monthly_report.py  — Reporte mes a mes para el horizonte completo
-----------------------------------------------------------------
Brayan S. Lopez-Mendez · Udenar 2026

Usado únicamente con --full (horizonte 5160 h, ~7 meses Jul 2025–Feb 2026).
Para el modo perfil diario (24 h) no aplica: month_labels es None.

Lógica:
  - P2P: métricas agregadas desde los HourlyResult ya calculados (sin re-simular).
  - C1 : run_c1_creg174 sobre el slice del mes (una sola period = todo el mes).
  - C3 : run_c3_spot sobre el slice.
  - C4 : run_c4_creg101072 sobre el slice.

Retorna lista de dicts (uno por mes) con las claves:
  month           : int   YYYYMM
  month_label     : str   "Jul 2025"
  T_month         : int   horas en el mes
  net_benefit     : dict  {escenario: COP}
  ie_p2p          : float media de IE en horas activas
  ps_p2p          : float % excedente capturado por compradores (pond. por kWh)
  psr_p2p         : float % excedente capturado por vendedores
  sc              : dict  {escenario: [0,1]}
  ss              : dict  {escenario: [0,1]}
  market_hours    : int   horas con mercado P2P activo
  kwh_p2p         : float kWh totales transados en P2P
"""

from __future__ import annotations

import numpy as np
from collections import defaultdict
from typing import Optional, Union

from scenarios._pi_gs import as_pi_gs_array

_MONTHS_ES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}


def _month_label(yyyymm: int) -> str:
    y, m = divmod(yyyymm, 100)
    return f"{_MONTHS_ES.get(m, str(m))} {y}"


def compute_monthly_metrics(
    D:            np.ndarray,        # (N, T)
    G_klim:       np.ndarray,        # (N, T)
    G_raw:        np.ndarray,        # (N, T)
    p2p_results:  list,              # lista de HourlyResult, len = T
    pi_gs:        Union[float, np.ndarray],  # escalar, (N,) o (N, T) — CAL-9
    pi_gb:        float,
    pi_bolsa:     np.ndarray,        # (T,)
    prosumer_ids: list,
    consumer_ids: list,
    month_labels: np.ndarray,        # (T,) enteros YYYYMM
    pde:          np.ndarray,        # (N,)
    capacity:     Optional[np.ndarray] = None,
    component_c:  "str | float | np.ndarray" = "auto",   # CAL-10b
    # ── CAL-37 (ADR-0037): C2 y C5 en el reporte mensual ────────────────
    pi_ppa:        Optional[float] = None,        # si no es None → C2 mensual
    g_component:   Optional[np.ndarray] = None,   # CAL-16 (N, T)
    cvm_component: Optional[np.ndarray] = None,
    cot_component: Optional[np.ndarray] = None,
    mem_costs:     Optional[np.ndarray] = None,
    cot_alpha:     float = 1.0,
    include_c5:    bool = False,
    pi_escasez:    Optional[np.ndarray] = None,   # (T,) PES→horario
    f_split_c5:    float = 0.5,
) -> list[dict]:
    """
    Calcula métricas de comparación mes a mes.
    Retorna lista de dicts ordenada cronológicamente.
    """
    from scenarios.scenario_c1_creg174    import run_c1_creg174
    from scenarios.scenario_c3_spot       import run_c3_spot
    from scenarios.scenario_c4_creg101072 import run_c4_creg101072

    N, T = D.shape
    pi_gs_v = as_pi_gs_array(pi_gs, N, T)   # (N, T) — CAL-9

    # ── Agrupar índices por mes ───────────────────────────────────────────
    month_to_idx: dict[int, list[int]] = defaultdict(list)
    for k, m in enumerate(month_labels):
        month_to_idx[int(m)].append(k)

    monthly = []

    for yyyymm in sorted(month_to_idx):
        idx = month_to_idx[yyyymm]
        idx_arr = np.array(idx, dtype=int)
        T_m = len(idx)

        D_m       = D[:, idx_arr]           # (N, T_m)
        G_klim_m  = G_klim[:, idx_arr]      # (N, T_m)
        G_raw_m   = G_raw[:, idx_arr]       # (N, T_m)
        pb_m      = pi_bolsa[idx_arr]       # (T_m,)
        pi_gs_m   = pi_gs_v[:, idx_arr]     # (N, T_m) — tarifa del mes (CAL-9)
        res_m     = [p2p_results[k] for k in idx]  # HourlyResult para el mes

        # ── P2P: agregar desde HourlyResult ya calculados ─────────────────
        active_m = [r for r in res_m
                    if r.P_star is not None and float(np.sum(r.P_star)) > 1e-6]
        kwh_m    = sum(float(np.sum(r.P_star)) for r in active_m)

        ie_m   = float(np.mean([r.IE  for r in active_m])) if active_m else 0.0
        ps_m   = 50.0
        psr_m  = 50.0
        if active_m:
            kwh_arr  = np.array([float(np.sum(r.P_star)) for r in active_m])
            ps_arr   = np.array([r.PS  for r in active_m])
            psr_arr  = np.array([r.PSR for r in active_m])
            tot_kwh  = float(np.sum(kwh_arr))
            if tot_kwh > 1e-9:
                ps_m  = float(np.dot(ps_arr,  kwh_arr) / tot_kwh)
                psr_m = float(np.dot(psr_arr, kwh_arr) / tot_kwh)

        # Beneficio monetario P2P — misma lógica que comparison_engine
        # CAL-30: pasa pb_m (slice mensual de pi_bolsa) para residual surplus.
        net_p2p = _p2p_benefit_month(active_m, D_m, G_klim_m, pi_gs_m, pi_gb,
                                      prosumer_ids, idx,
                                      pi_bolsa_m=pb_m)

        # SC / SS P2P: autoconsumo local + P2P transado
        D_total_m = float(np.sum(np.maximum(D_m, 0)))
        G_total_m = float(np.sum(np.maximum(G_klim_m, 0)))
        auto_m    = float(np.sum(np.minimum(
            np.maximum(G_klim_m, 0), np.maximum(D_m, 0))))
        sc_p2p = (auto_m + kwh_m) / D_total_m if D_total_m > 1e-10 else 0.0
        ss_p2p = (auto_m + kwh_m) / G_total_m if G_total_m > 1e-10 else 0.0

        # ── C1 (CREG 174): balance mensual — todo el mes = un período ─────
        # CAL-10b: si component_c es matriz (N, T), slicear al mes; si es
        # string ("auto") o escalar, usar tal cual.
        if isinstance(component_c, np.ndarray):
            cc_m = component_c[:, idx_arr]
        else:
            cc_m = component_c
        c1 = run_c1_creg174(
            D_m, G_klim_m, pi_gs_m, pb_m, prosumer_ids,
            month_labels=None,   # mes completo = un único período de facturación
            component_c=cc_m,
        )
        net_c1 = sum(c1[n]["net_benefit"] for n in prosumer_ids)

        # ── C3 (spot): liquidación horaria ───────────────────────────────
        c3 = run_c3_spot(D_m, G_klim_m, pi_gs_m, pb_m, prosumer_ids, consumer_ids)
        net_c3 = c3["aggregate"]["total_net_benefit"]

        # ── C4 (AGRC): distribución PDE ──────────────────────────────────
        # CAL-15: hereda Cvm,i,j de CREG 174 art. 25 (mismo cc_m que C1).
        try:
            c4 = run_c4_creg101072(
                D_m, G_klim_m, pi_gs_m, pb_m, pde, capacity,
                component_c=cc_m,
            )
            net_c4 = c4["aggregate"]["total_net_benefit"]
        except ValueError:
            # Si la capacidad supera el límite del régimen, reportar sin error
            c4 = run_c4_creg101072(
                D_m, G_klim_m, pi_gs_m, pb_m, pde, capacity=None,
                component_c=cc_m,
            )
            net_c4 = c4["aggregate"]["total_net_benefit"]

        # SC/SS regulatorios (sin mercado P2P): min(G,D)/sum(D|G)
        sc_reg = auto_m / D_total_m if D_total_m > 1e-10 else 0.0
        ss_reg = auto_m / G_total_m if G_total_m > 1e-10 else 0.0

        # ── C2 y C5 mensuales (CAL-37) ────────────────────────────────────
        def _sl(x):
            """Slice mensual de matrices (N, T); passthrough para el resto."""
            return (x[:, idx_arr]
                    if isinstance(x, np.ndarray) and x.ndim == 2 else x)

        nb_extra = {}
        if pi_ppa is not None:
            from scenarios.scenario_c2_bilateral import run_c2_bilateral
            c2 = run_c2_bilateral(
                D_m, G_klim_m, pi_gs_m, pi_gb, pi_ppa,
                prosumer_ids, consumer_ids,
                g_component=_sl(g_component),
                cvm_component=_sl(cvm_component),
                cot_component=_sl(cot_component),
                mem_costs=_sl(mem_costs),
                cot_alpha=cot_alpha,
                pi_bolsa=pb_m,            # CAL-37: bolsa horaria del mes
            )
            nb_extra["C2"] = c2["aggregate"]["total_net_benefit"]
        if include_c5:
            from scenarios.scenario_c5_agr_creg101099 import (
                run_c5_agr_creg101099)
            c5 = run_c5_agr_creg101099(
                D_m, G_klim_m, pi_gs_m, pb_m,
                g_component=_sl(g_component) if g_component is not None else 0.0,
                cvm_component=_sl(cvm_component) if cvm_component is not None else 0.0,
                cot_component=_sl(cot_component) if cot_component is not None else 0.0,
                mem_costs=_sl(mem_costs) if mem_costs is not None else 0.0,
                cot_alpha=cot_alpha, f_split=f_split_c5,
                pi_escasez=(pi_escasez[idx_arr]
                            if pi_escasez is not None else None),
            )
            nb_extra["C5"] = c5["aggregate"]["total_net_benefit"]

        monthly.append({
            "month":        yyyymm,
            "month_label":  _month_label(yyyymm),
            "T_month":      T_m,
            "net_benefit": {
                "P2P": net_p2p,
                "C1":  net_c1,
                "C3":  net_c3,
                "C4":  net_c4,
                **nb_extra,
            },
            "ie_p2p":      ie_m,
            "ps_p2p":      ps_m,
            "psr_p2p":     psr_m,
            "sc":  {"P2P": sc_p2p, "C1": sc_reg, "C3": sc_reg, "C4": sc_reg},
            "ss":  {"P2P": ss_p2p, "C1": ss_reg, "C3": ss_reg, "C4": ss_reg},
            "market_hours": len(active_m),
            "kwh_p2p":      kwh_m,
        })

    return monthly


def _p2p_benefit_month(
    active_results: list,
    D_m:          np.ndarray,
    G_klim_m:     np.ndarray,
    pi_gs:        Union[float, np.ndarray],
    pi_gb:        float,
    prosumer_ids: list,
    global_idx:   list,
    pi_bolsa_m:   Optional[np.ndarray] = None,
) -> float:
    """
    Beneficio monetario neto P2P para el mes: misma lógica que
    comparison_engine._p2p_monetary_benefit() en modo canónico (CAL-30).
    pi_gs admite escalar, vector (N,) o matriz (N, T_m) — CAL-9.

    CAL-30: añade revenue completo del trade + residual surplus a
    ``pi_bolsa_m[k]`` horario. Si pi_bolsa_m es None, usa pi_gb escalar
    como aproximación (compatibilidad con callers pre-CAL-30).
    """
    N, T_m = D_m.shape
    pi_gs_v = as_pi_gs_array(pi_gs, N, T_m)   # (N, T_m)
    net = np.zeros(N)

    if pi_bolsa_m is None:
        pi_bolsa_v = np.full(T_m, float(pi_gb))
    else:
        pi_bolsa_v = np.asarray(pi_bolsa_m, dtype=float).reshape(-1)
        if pi_bolsa_v.size != T_m:
            raise ValueError(
                f"pi_bolsa_m size {pi_bolsa_v.size} != T_m={T_m}"
            )

    # Acumulador kWh vendidos por agente y hora local del mes (residual).
    P_sold_n_k = np.zeros((N, T_m))

    # Mapear índice global → posición local en el slice
    global_to_local = {g: l for l, g in enumerate(global_idx)}

    for r in active_results:
        if r.P_star is None:
            continue
        k_local = global_to_local.get(r.k)
        if k_local is None:
            continue

        # Vendedores: revenue completo (CAL-30 canonical)
        for idx_j, j in enumerate(r.seller_ids):
            if r.pi_star is not None:
                income = float(np.dot(r.pi_star, r.P_star[idx_j, :]))
            else:
                income = float(np.sum(r.P_star[idx_j, :])) * pi_gb
            sold = float(np.sum(r.P_star[idx_j, :]))
            net[j] += income           # revenue completo
            P_sold_n_k[j, k_local] = sold

        # Compradores: cada uno a su pi_gs[i, k_local] del mes
        for idx_i, i in enumerate(r.buyer_ids):
            received = float(np.sum(r.P_star[:, idx_i]))
            pi_ref = float(pi_gs_v[i, k_local])
            paid = (r.pi_star[idx_i] * received if r.pi_star is not None
                    else received * pi_ref)
            net[i] += received * pi_ref - paid

    # Autoconsumo propio de prosumidores a pi_gs[n, t] del mes
    for n in prosumer_ids:
        for t in range(T_m):
            net[n] += min(max(G_klim_m[n, t], 0.0),
                           max(D_m[n, t], 0.0)) * pi_gs_v[n, t]

    # Residual surplus exportado a la red (CAL-30 canonical)
    for n in prosumer_ids:
        for t in range(T_m):
            G_nt = max(float(G_klim_m[n, t]), 0.0)
            D_nt = max(float(D_m[n, t]), 0.0)
            surplus_total_nt = max(G_nt - D_nt, 0.0)
            residual_nt = max(surplus_total_nt - P_sold_n_k[n, t], 0.0)
            net[n] += residual_nt * float(pi_bolsa_v[t])

    return float(np.sum(net))


def print_monthly_table(monthly: list[dict], currency: str = "COP") -> None:
    """Imprime la tabla resumen mensual en consola."""
    # CAL-37: columnas dinámicas según escenarios presentes (C2/C5 opcionales)
    canon = ["P2P", "C1", "C2", "C3", "C4", "C5"]
    presentes = monthly[0]["net_benefit"].keys() if monthly else []
    esc = [e for e in canon if e in presentes]
    col_w = 14

    header = f"  {'Mes':<10}" + "".join(f"{e:>{col_w}}" for e in esc)
    header += f"  {'IE_P2P':>8}  {'PS%':>6}  {'PSR%':>6}  {'kWh_P2P':>9}"
    print("\n" + "="*len(header))
    print(f"  BENEFICIO NETO MENSUAL ({currency})  —  "
          f"P2P vs {' / '.join(esc[1:])}")
    print("="*len(header))
    print(header)
    print("-"*len(header))

    for m in monthly:
        row = f"  {m['month_label']:<10}"
        for e in esc:
            v = m["net_benefit"].get(e, 0.0)
            row += f"{v:>{col_w},.0f}"
        row += (f"  {m['ie_p2p']:>8.4f}"
                f"  {m['ps_p2p']:>6.1f}"
                f"  {m['psr_p2p']:>6.1f}"
                f"  {m['kwh_p2p']:>9.2f}")
        print(row)

    # Totales
    print("-"*len(header))
    total_row = f"  {'TOTAL':<10}"
    for e in esc:
        t = sum(m["net_benefit"].get(e, 0.0) for m in monthly)
        total_row += f"{t:>{col_w},.0f}"
    avg_ie  = float(np.mean([m["ie_p2p"]  for m in monthly]))
    avg_ps  = float(np.mean([m["ps_p2p"]  for m in monthly]))
    avg_psr = float(np.mean([m["psr_p2p"] for m in monthly]))
    tot_kwh = sum(m["kwh_p2p"] for m in monthly)
    total_row += (f"  {avg_ie:>8.4f}"
                  f"  {avg_ps:>6.1f}"
                  f"  {avg_psr:>6.1f}"
                  f"  {tot_kwh:>9.2f}")
    print(total_row)
    print("="*len(header))
