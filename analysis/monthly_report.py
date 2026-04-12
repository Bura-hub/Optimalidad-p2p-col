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
from typing import Optional

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
    pi_gs:        float,
    pi_gb:        float,
    pi_bolsa:     np.ndarray,        # (T,)
    prosumer_ids: list,
    consumer_ids: list,
    month_labels: np.ndarray,        # (T,) enteros YYYYMM
    pde:          np.ndarray,        # (N,)
    capacity:     Optional[np.ndarray] = None,
) -> list[dict]:
    """
    Calcula métricas de comparación mes a mes.
    Retorna lista de dicts ordenada cronológicamente.
    """
    from scenarios.scenario_c1_creg174    import run_c1_creg174
    from scenarios.scenario_c3_spot       import run_c3_spot
    from scenarios.scenario_c4_creg101072 import run_c4_creg101072

    N, T = D.shape

    # ── Agrupar índices por mes ───────────────────────────────────────────
    month_to_idx: dict[int, list[int]] = defaultdict(list)
    for k, m in enumerate(month_labels):
        month_to_idx[int(m)].append(k)

    monthly = []

    for yyyymm in sorted(month_to_idx):
        idx = month_to_idx[yyyymm]
        idx_arr = np.array(idx, dtype=int)
        T_m = len(idx)

        D_m      = D[:, idx_arr]           # (N, T_m)
        G_klim_m = G_klim[:, idx_arr]      # (N, T_m)
        G_raw_m  = G_raw[:, idx_arr]       # (N, T_m)
        pb_m     = pi_bolsa[idx_arr]       # (T_m,)
        res_m    = [p2p_results[k] for k in idx]  # HourlyResult para el mes

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
        net_p2p = _p2p_benefit_month(active_m, D_m, G_klim_m, pi_gs, pi_gb,
                                      prosumer_ids, idx)

        # SC / SS P2P: autoconsumo local + P2P transado
        D_total_m = float(np.sum(np.maximum(D_m, 0)))
        G_total_m = float(np.sum(np.maximum(G_klim_m, 0)))
        auto_m    = float(np.sum(np.minimum(
            np.maximum(G_klim_m, 0), np.maximum(D_m, 0))))
        sc_p2p = (auto_m + kwh_m) / D_total_m if D_total_m > 1e-10 else 0.0
        ss_p2p = (auto_m + kwh_m) / G_total_m if G_total_m > 1e-10 else 0.0

        # ── C1 (CREG 174): balance mensual — todo el mes = un período ─────
        c1 = run_c1_creg174(
            D_m, G_klim_m, pi_gs, pb_m, prosumer_ids,
            month_labels=None,   # mes completo = un único período de facturación
        )
        net_c1 = sum(c1[n]["net_benefit"] for n in prosumer_ids)

        # ── C3 (spot): liquidación horaria ───────────────────────────────
        c3 = run_c3_spot(D_m, G_klim_m, pi_gs, pb_m, prosumer_ids, consumer_ids)
        net_c3 = c3["aggregate"]["total_net_benefit"]

        # ── C4 (AGRC): distribución PDE ──────────────────────────────────
        try:
            c4 = run_c4_creg101072(D_m, G_klim_m, pi_gs, pb_m, pde, capacity)
            net_c4 = c4["aggregate"]["total_net_benefit"]
        except ValueError:
            # Si la capacidad supera el límite del régimen, reportar sin error
            c4 = run_c4_creg101072(D_m, G_klim_m, pi_gs, pb_m, pde, capacity=None)
            net_c4 = c4["aggregate"]["total_net_benefit"]

        # SC/SS regulatorios (sin mercado P2P): min(G,D)/sum(D|G)
        sc_reg = auto_m / D_total_m if D_total_m > 1e-10 else 0.0
        ss_reg = auto_m / G_total_m if G_total_m > 1e-10 else 0.0

        monthly.append({
            "month":        yyyymm,
            "month_label":  _month_label(yyyymm),
            "T_month":      T_m,
            "net_benefit": {
                "P2P": net_p2p,
                "C1":  net_c1,
                "C3":  net_c3,
                "C4":  net_c4,
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
    pi_gs:        float,
    pi_gb:        float,
    prosumer_ids: list,
    global_idx:   list,
) -> float:
    """
    Beneficio monetario neto P2P para el mes: misma lógica que
    comparison_engine._p2p_monetary_benefit(), pero sobre un slice mensual.
    """
    N = D_m.shape[0]
    net = np.zeros(N)

    # Mapear índice global → posición local en el slice
    global_to_local = {g: l for l, g in enumerate(global_idx)}

    for r in active_results:
        if r.P_star is None:
            continue
        k_local = global_to_local.get(r.k)
        if k_local is None:
            continue

        # Vendedores
        for idx_j, j in enumerate(r.seller_ids):
            if r.pi_star is not None:
                income = float(np.dot(r.pi_star, r.P_star[idx_j, :]))
            else:
                income = float(np.sum(r.P_star[idx_j, :])) * pi_gb
            baseline = float(np.sum(r.P_star[idx_j, :])) * pi_gb
            net[j] += income - baseline

        # Compradores
        for idx_i, i in enumerate(r.buyer_ids):
            received = float(np.sum(r.P_star[:, idx_i]))
            paid = (r.pi_star[idx_i] * received if r.pi_star is not None
                    else received * pi_gs)
            net[i] += received * pi_gs - paid

    # Autoconsumo propio de prosumidores
    T_m = D_m.shape[1]
    for n in prosumer_ids:
        for t in range(T_m):
            net[n] += min(max(G_klim_m[n, t], 0.0), max(D_m[n, t], 0.0)) * pi_gs

    return float(np.sum(net))


def print_monthly_table(monthly: list[dict], currency: str = "COP") -> None:
    """Imprime la tabla resumen mensual en consola."""
    esc = ["P2P", "C1", "C3", "C4"]
    col_w = 14

    header = f"  {'Mes':<10}" + "".join(f"{e:>{col_w}}" for e in esc)
    header += f"  {'IE_P2P':>8}  {'PS%':>6}  {'PSR%':>6}  {'kWh_P2P':>9}"
    print("\n" + "="*len(header))
    print(f"  BENEFICIO NETO MENSUAL ({currency})  —  P2P vs C1 / C3 / C4")
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
