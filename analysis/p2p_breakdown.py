"""
p2p_breakdown.py  — §3.12 Desglose P2P hora a hora
----------------------------------------------------
Brayan S. Lopez-Mendez · Udenar 2026

Genera dos tablas exportables (CSV / hojas Excel) con el detalle completo
del mercado P2P hora a hora:

  Tabla 1 — Flujos de transacción (una fila por par vendedor-comprador-hora):
    hora · vendedor · comprador · kWh_transados · precio_COP_kWh
    valor_COP · prima_vendedor_COP · ahorro_comprador_COP

  Tabla 2 — Resumen horario (una fila por hora):
    hora · mercado_activo · kWh_total · precio_prom_pond_COP_kWh
    n_vendedores · n_compradores · vendedores · compradores
    SC · SS · IE · G_total_kW · D_total_kW

Uso desde código:
    from analysis.p2p_breakdown import export_p2p_hourly
    flows_df, summary_df = export_p2p_hourly(
        p2p_results, agent_names, pi_gs, pi_gb, out_dir="resultados/")

Uso desde main_simulation.py:
    Llamado automáticamente con --analysis o --breakdown.
"""

import os
import numpy as np

try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False


def export_p2p_hourly(
    p2p_results: list,
    agent_names: list,
    pi_gs: float,
    pi_gb: float,
    out_dir: str = ".",
    prefix: str = "p2p_breakdown",
    verbose: bool = True,
) -> tuple:
    """
    Construye las dos tablas del desglose P2P hora a hora y las exporta a CSV.

    Parámetros
    ----------
    p2p_results : list[HourlyResult]  — salida de EMSP2P.run()
    agent_names : list[str]           — nombres de los N agentes
    pi_gs       : float               — precio retail (COP/kWh)
    pi_gb       : float               — precio bolsa base (COP/kWh)
    out_dir     : str                 — directorio de salida
    prefix      : str                 — prefijo para los archivos CSV

    Retorna
    -------
    (flows_rows, summary_rows) : tupla de listas de dicts
        Si pandas está disponible, los escribe también en Excel de dos hojas.
    """
    flows_rows   = []
    summary_rows = []

    for r in p2p_results:
        hora = r.k

        # ── Resumen horario ─────────────────────────────────────────────────
        g_total = float(np.sum(np.maximum(r.G_klim_k, 0))) if r.G_klim_k is not None else 0.0
        d_total = float(np.sum(np.maximum(r.D_k,      0))) if r.D_k      is not None else 0.0

        if r.P_star is None or float(np.sum(r.P_star)) < 1e-6:
            summary_rows.append({
                "hora":                hora,
                "mercado_activo":      False,
                "kWh_total_p2p":       0.0,
                "precio_prom_pond":    None,
                "n_vendedores":        0,
                "n_compradores":       0,
                "vendedores":          "",
                "compradores":         "",
                "SC":                  r.SC,
                "SS":                  r.SS,
                "IE":                  r.IE,
                "G_total_kW":          g_total,
                "D_total_kW":          d_total,
            })
            continue

        P_star    = r.P_star      # (J, I)
        pi_star   = r.pi_star     # (I,)  precio pagado por cada comprador
        sellers   = r.seller_ids  # índices en agent_names
        buyers    = r.buyer_ids   # índices en agent_names

        kwh_total = float(np.sum(P_star))

        # Precio promedio ponderado por volumen
        if kwh_total > 1e-6:
            kwh_per_buyer = np.sum(P_star, axis=0)   # (I,)
            precio_prom   = float(np.dot(kwh_per_buyer, pi_star) / kwh_total)
        else:
            precio_prom = float(np.mean(pi_star)) if pi_star is not None else 0.0

        seller_names = [agent_names[j] for j in sellers if j < len(agent_names)]
        buyer_names  = [agent_names[i] for i in buyers  if i < len(agent_names)]

        summary_rows.append({
            "hora":                hora,
            "mercado_activo":      True,
            "kWh_total_p2p":       round(kwh_total, 4),
            "precio_prom_pond":    round(precio_prom, 2),
            "n_vendedores":        len(sellers),
            "n_compradores":       len(buyers),
            "vendedores":          ";".join(seller_names),
            "compradores":         ";".join(buyer_names),
            "SC":                  round(r.SC, 4),
            "SS":                  round(r.SS, 4),
            "IE":                  round(r.IE, 4),
            "G_total_kW":          round(g_total, 3),
            "D_total_kW":          round(d_total, 3),
        })

        # ── Flujos por par vendedor-comprador ───────────────────────────────
        for j_idx, j in enumerate(sellers):
            nombre_vendedor = agent_names[j] if j < len(agent_names) else f"A{j+1}"
            for i_idx, i in enumerate(buyers):
                nombre_comprador = agent_names[i] if i < len(agent_names) else f"A{i+1}"
                kwh_ij = float(P_star[j_idx, i_idx])
                if kwh_ij < 1e-6:
                    continue
                precio_i    = float(pi_star[i_idx])
                valor_cop   = kwh_ij * precio_i
                prima_j     = kwh_ij * max(0.0, precio_i - pi_gb)
                ahorro_i    = kwh_ij * max(0.0, pi_gs    - precio_i)
                flows_rows.append({
                    "hora":               hora,
                    "vendedor":           nombre_vendedor,
                    "comprador":          nombre_comprador,
                    "kWh_transados":      round(kwh_ij,   4),
                    "precio_COP_kWh":     round(precio_i, 2),
                    "valor_COP":          round(valor_cop, 2),
                    "prima_vendedor_COP": round(prima_j,  2),
                    "ahorro_comprador_COP": round(ahorro_i, 2),
                })

    # ── Exportar CSV ─────────────────────────────────────────────────────────
    os.makedirs(out_dir, exist_ok=True)
    flows_path   = os.path.join(out_dir, f"{prefix}_flujos.csv")
    summary_path = os.path.join(out_dir, f"{prefix}_resumen_horario.csv")

    _write_csv(flows_rows,   flows_path,   _FLOWS_COLS)
    _write_csv(summary_rows, summary_path, _SUMMARY_COLS)

    # ── Exportar Excel (dos hojas) si pandas disponible ──────────────────────
    excel_path = None
    if _HAS_PANDAS:
        import pandas as pd
        excel_path = os.path.join(out_dir, f"{prefix}.xlsx")
        df_flows   = pd.DataFrame(flows_rows,   columns=_FLOWS_COLS)
        df_summary = pd.DataFrame(summary_rows, columns=_SUMMARY_COLS)
        with pd.ExcelWriter(excel_path, engine="openpyxl") as xw:
            df_summary.to_excel(xw, sheet_name="Resumen_Horario", index=False)
            df_flows.to_excel(xw,   sheet_name="Flujos_Transaccion", index=False)

    if verbose:
        n_active = sum(1 for r in summary_rows if r["mercado_activo"])
        kwh_tot  = sum(r["kWh_total_p2p"] for r in summary_rows)
        n_flows  = len(flows_rows)
        print(f"\n  §3.12 Desglose P2P hora a hora:")
        print(f"    Horas con mercado activo: {n_active}/{len(summary_rows)}")
        print(f"    kWh totales transados:    {kwh_tot:.3f} kWh")
        print(f"    Pares vendedor-comprador: {n_flows} registros")
        print(f"    CSV flujos     → {flows_path}")
        print(f"    CSV resumen    → {summary_path}")
        if excel_path:
            print(f"    Excel (2 hojas)→ {excel_path}")

    return flows_rows, summary_rows


def print_p2p_sample(flows_rows: list, summary_rows: list,
                     n_hours: int = 5) -> None:
    """Imprime las primeras n_hours horas activas del mercado P2P."""
    active = [r for r in summary_rows if r["mercado_activo"]]
    if not active:
        print("  No hubo horas con mercado P2P activo.")
        return

    print(f"\n  Primeras {min(n_hours, len(active))} horas con mercado P2P activo:")
    print(f"  {'Hora':>5}  {'kWh':>7}  {'Precio':>8}  {'Vendedores':<20}  {'Compradores':<20}")
    print("  " + "─"*70)
    for row in active[:n_hours]:
        print(f"  {row['hora']:>5}  "
              f"{row['kWh_total_p2p']:>7.3f}  "
              f"{row['precio_prom_pond']:>8.2f}  "
              f"{row['vendedores']:<20}  "
              f"{row['compradores']:<20}")

    flows_h = {row["hora"]: [] for row in active[:n_hours]}
    for f in flows_rows:
        if f["hora"] in flows_h:
            flows_h[f["hora"]].append(f)

    print(f"\n  Detalle de transacciones:")
    print(f"  {'Hora':>5}  {'Vendedor':<12}  {'Comprador':<12}  "
          f"{'kWh':>7}  {'Precio':>8}  {'Prima V':>9}  {'Ahorro C':>9}")
    print("  " + "─"*78)
    for hora in sorted(flows_h):
        for f in flows_h[hora]:
            print(f"  {f['hora']:>5}  "
                  f"{f['vendedor']:<12}  "
                  f"{f['comprador']:<12}  "
                  f"{f['kWh_transados']:>7.3f}  "
                  f"{f['precio_COP_kWh']:>8.2f}  "
                  f"{f['prima_vendedor_COP']:>9.2f}  "
                  f"{f['ahorro_comprador_COP']:>9.2f}")


# ── Helpers ───────────────────────────────────────────────────────────────────

_FLOWS_COLS = [
    "hora", "vendedor", "comprador",
    "kWh_transados", "precio_COP_kWh", "valor_COP",
    "prima_vendedor_COP", "ahorro_comprador_COP",
]

_SUMMARY_COLS = [
    "hora", "mercado_activo", "kWh_total_p2p", "precio_prom_pond",
    "n_vendedores", "n_compradores", "vendedores", "compradores",
    "SC", "SS", "IE", "G_total_kW", "D_total_kW",
]


def _write_csv(rows: list, path: str, columns: list) -> None:
    """Escribe CSV sin dependencia de pandas."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(columns) + "\n")
        for row in rows:
            vals = []
            for col in columns:
                v = row.get(col, "")
                if v is None:
                    vals.append("")
                elif isinstance(v, bool):
                    vals.append(str(v))
                elif isinstance(v, float):
                    vals.append(f"{v:.4f}")
                else:
                    vals.append(str(v))
            f.write(",".join(vals) + "\n")
