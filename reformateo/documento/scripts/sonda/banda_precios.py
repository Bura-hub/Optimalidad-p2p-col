"""
Sonda de la banda de precios — CAL-47.

Mide qué pasa cuando las dos cotas del juego dejan de ser constantes
escritas a mano y pasan a ser las opciones de fuera realmente medidas:

    techo  = costo unitario mensual del comercializador, nivel de tensión 2,
             clase exenta de contribución, común a las cinco instituciones
    piso   = precio de bolsa de esa hora, la misma serie que ya usan los
             cuatro escenarios regulados y el residual del propio P2P

Tres configuraciones sobre el mismo mes y los mismos datos:

    A  canon      techo 906,27 · piso 280        constantes, lo de hoy
    B  solo piso  techo 906,27 · piso bolsa[k]   aísla el efecto del piso
    C  banda      techo CU[mes] · piso bolsa[k]  la propuesta completa

La configuración A **tiene que reproducir el canon dígito a dígito**. Si no
lo hace, nada de lo que diga B o C es creíble y la sonda se detiene.

La sonda NO toca el modelo. Replica el empaquetado por hora que hace el
motor y le pasa a cada hora sus propias cotas, de modo que el árbol queda
igual que antes de correrla.

Uso:
    python banda_precios.py --mes 2025-09
    python banda_precios.py --mes 2025-09 --cobertura m3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))

from core.ems_p2p import AgentParams, SolverParams, _run_hour_worker  # noqa: E402
from core.market_prep import classify_agents, compute_generation_limit  # noqa: E402
from data.base_case_data import GRID_PARAMS_REAL  # noqa: E402
from data.xm_prices import get_b_for_real_data  # noqa: E402
from data.cedenar_tariff import community_effective_pi_gs  # noqa: E402

SALIDAS = Path(__file__).parent / "salidas"


# ── Cotas ────────────────────────────────────────────────────────────────────
def _fila_tarifa(mes: str):
    t = pd.read_csv(RAIZ / "data" / "tarifas_cedenar_mensual.csv", comment="#")
    f = t[(t.nivel_tension == 2) & (t.categoria == "oficial")
          & (t.propiedad == "cedenar") & (t.mes == mes)]
    if f.empty:
        raise SystemExit(f"sin tarifa para {mes} en el CSV de Cedenar")
    return f.iloc[0]


def piso_permuta(mes: str) -> float:
    """Lo que el vendedor obtiene de la red si NO negocia con un vecino.

    Mientras su inyeccion acumulada del mes no supere su retiro, el
    excedente se liquida como permuta y vale la tarifa menos el componente
    de comercializacion. Medido sobre el horizonte, entre el 62 y el 100 %
    del excedente de cada institucion cae en ese tramo, de modo que esta
    es la alternativa que gobierna y no el precio de bolsa.

    De aqui sale que **el ancho de la banda es exactamente el componente de
    comercializacion**: el comprador paga la tarifa y el vendedor recibe la
    tarifa menos ese cargo.
    """
    r = _fila_tarifa(mes)
    return float(r.CU_aplicado) - float(r.Cvm)


def techo_mensual(mes: str) -> float:
    """Costo unitario del mes, nivel de tensión 2, clase exenta.

    Se lee la fila «oficial», que es la que no lleva la contribución de
    solidaridad. Las cinco instituciones comparten techo: sin acceso a los
    contratos bilaterales no hay fuente que dé una generación distinta por
    entidad, de modo que diferenciarlas sería inventar el dato.
    """
    return float(_fila_tarifa(mes).CU_aplicado)


def piso_horario(idx: pd.DatetimeIndex) -> np.ndarray:
    """Serie de bolsa alineada a las horas del tramo."""
    b = pd.read_csv(RAIZ / "data" / "precios_bolsa_xm_api.csv")
    b["ts"] = pd.to_datetime(b["Fecha"]) + pd.to_timedelta(b["Hora"] - 1, "h")
    serie = b.set_index("ts")["Precio_COP_kWh"]
    llaves = pd.DatetimeIndex(idx)
    if llaves.tz is not None:            # el cargador entrega hora local
        llaves = llaves.tz_localize(None)
    s = serie.reindex(llaves)
    if s.isna().any():
        raise SystemExit(f"faltan {int(s.isna().sum())} horas de bolsa "
                         f"entre {llaves[0]} y {llaves[-1]}")
    return s.to_numpy(float)


# ── Corrida por hora con cotas propias ───────────────────────────────────────
def corre(D, G, agentes, pi_gs_k, pi_gb_k, sv: SolverParams):
    """Replica el empaquetado del motor, hora a hora, con cotas por hora.

    Devuelve la lista de resultados y el número de horas que no abrieron
    por banda invertida, es decir aquellas en que la bolsa iguala o supera
    al costo unitario y ninguna transacción beneficia a las dos partes.
    """
    N, T = D.shape
    res, cerradas = [], 0

    for k in range(T):
        gs, gb = float(pi_gs_k[k]), float(pi_gb_k[k])

        if gb >= gs:
            cerradas += 1
            res.append(None)
            continue

        g_klim = compute_generation_limit(
            G[:, k], agentes.a, agentes.b, agentes.c, gs)
        _, sids, bids = classify_agents(g_klim, D[:, k])

        res.append(_run_hour_worker((
            k, g_klim.copy(), D[:, k].copy(), G[:, k].copy(), sids, bids,
            agentes.a, agentes.b, agentes.lam, agentes.theta, agentes.etha,
            gs, gb,
            sv.tau, sv.tau_buyers, sv.t_span, sv.n_points,
            sv.stackelberg_iters, sv.stackelberg_tol, sv.stackelberg_max,
            sv.ode_method, sv.buyer_competition)))

    return res, cerradas


# ── Lectura de una corrida ───────────────────────────────────────────────────
def mide(res, pi_gs_k, pi_gb_k, nombres):
    """Resume una corrida: volumen, precio, reparto y prima por institución."""
    filas = []
    for r in res:
        if r is None or r.P_star is None:
            continue
        for a, i in enumerate(r.buyer_ids):
            for b, j in enumerate(r.seller_ids):
                q = float(r.P_star[b, a])
                if q <= 1e-9:
                    continue
                p = float(r.pi_star[a])
                filas.append({
                    "hora": r.k, "vendedor": nombres[j], "comprador": nombres[i],
                    "kWh": q, "precio": p,
                    "prima_vendedor": (p - pi_gb_k[r.k]) * q,
                    "ahorro_comprador": (pi_gs_k[r.k] - p) * q,
                    "en_piso": abs(p - pi_gb_k[r.k]) < 1e-6,
                    "en_techo": abs(p - pi_gs_k[r.k]) < 1e-6,
                })
    return pd.DataFrame(filas)


def informe(nombre, f, cerradas, T):
    if f.empty:
        print(f"  {nombre:14s} sin transacciones")
        return
    pv, ac = f.prima_vendedor.sum(), f.ahorro_comprador.sum()
    print(f"  {nombre:14s} {len(f):5d} flujos · {f.kWh.sum():9.1f} kWh · "
          f"precio mediano {f.precio.median():7.2f}")
    print(f"  {'':14s} en el piso {100*f.en_piso.mean():5.1f} % · "
          f"en el techo {100*f.en_techo.mean():5.1f} % · "
          f"interior {100*(1-f.en_piso.mean()-f.en_techo.mean()):5.1f} %")
    print(f"  {'':14s} excedente {pv+ac:12,.0f} COP · reparto "
          f"{100*pv/(pv+ac):4.1f} vendedor / {100*ac/(pv+ac):4.1f} comprador"
          f"{f' · {cerradas} de {T} horas cerradas' if cerradas else ''}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mes", default="2025-09")
    ap.add_argument("--cobertura", default="m1", choices=["m1", "m3"])
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    SALIDAS.mkdir(exist_ok=True)

    from data.xm_data_loader import MTEDataLoader, slice_horizon

    print(f"Sonda de la banda · {args.mes} · cobertura {args.cobertura.upper()}")
    print("=" * 74)

    import os
    raiz_mte = os.environ.get("MTE_ROOT", str(RAIZ / "MedicionesMTE_v3"))
    cfg = None
    if args.cobertura == "m3":
        from data.preprocessing import PAPER_METER_DEMAND_CONFIG
        cfg = PAPER_METER_DEMAND_CONFIG
    loader = MTEDataLoader(raiz_mte, demand_config=cfg)
    D_full, G_full, idx_full = loader.load(verbose=False)
    ini = pd.Timestamp(args.mes + "-01")
    fin = ini + pd.offsets.MonthBegin(1)
    D, G, idx = slice_horizon(D_full, G_full, idx_full,
                             ini.strftime("%Y-%m-%d"), fin.strftime("%Y-%m-%d"))
    N, T = D.shape
    nombres = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"][:N]
    print(f"  {T} horas · {N} instituciones\n")

    # Mismos parametros que la corrida canonica: main_simulation.py
    agentes = AgentParams(
        N=N, a=np.zeros(N), b=get_b_for_real_data(N, nombres), c=np.zeros(N),
        lam=np.full(N, 100.0), theta=np.full(N, 0.5), etha=np.full(N, 0.1))
    sv = SolverParams(tau=0.001, t_span=(0.0, 0.005),
                      n_points=150, stackelberg_iters=2, parallel=True)

    gs_canon = community_effective_pi_gs(
        nombres, idx_full[0], idx_full[-1] + pd.Timedelta(hours=1),
        weights=D_full.mean(axis=1))
    gb_canon = float(GRID_PARAMS_REAL["pi_gb"])
    gs_nuevo = techo_mensual(args.mes)
    gb_nuevo = piso_horario(idx)

    print(f"  techo de hoy {gs_canon:7.2f} · techo del mes {gs_nuevo:7.2f}")
    print(f"  piso de hoy  {gb_canon:7.2f} · piso medido: mediana "
          f"{np.median(gb_nuevo):6.2f}, media {gb_nuevo.mean():6.2f}, "
          f"máximo {gb_nuevo.max():7.2f}")
    print(f"  horas con la banda invertida: "
          f"{int((gb_nuevo >= gs_nuevo).sum())} de {T}\n")

    gb_permuta = piso_permuta(args.mes)
    print(f"  piso de permuta {gb_permuta:7.2f} · el ancho de esa banda es el "
          f"cargo de comercializar, {gs_nuevo - gb_permuta:6.2f}")
    print()

    uno = np.ones(T)
    configs = [
        ("A · canon",     uno * gs_canon,  uno * gb_canon),
        ("B · solo piso", uno * gs_canon,  gb_nuevo),
        ("C · bolsa",     uno * gs_nuevo,  gb_nuevo),
        ("D · permuta",   uno * gs_nuevo,  uno * gb_permuta),
    ]

    guardadas = {}
    for nombre, gs_k, gb_k in configs:
        res, cerradas = corre(D, G, agentes, gs_k, gb_k, sv)
        f = mide(res, gs_k, gb_k, nombres)
        informe(nombre, f, cerradas, T)
        print()
        guardadas[nombre] = f
        f.to_csv(SALIDAS / f"banda_{args.cobertura}_{args.mes}_"
                           f"{nombre.split()[0]}.csv", index=False)

    # Comprobación obligatoria: A debe reproducir el canon
    ref = pd.read_csv(RAIZ / "SALIDAS_SERVIDOR" / "entrega_canonica_2026-08"
                      / f"canonica_{args.cobertura}" / "outputs"
                      / "p2p_breakdown_flujos.csv")
    h0 = int((ini - pd.Timestamp("2025-04-04")).total_seconds() // 3600)
    ref = ref[(ref.hora >= h0) & (ref.hora < h0 + T)]
    a = guardadas["A · canon"]
    print("Comprobación contra el canon, mismo tramo")
    print(f"  canon {len(ref):5d} flujos · {ref.kWh_transados.sum():9.1f} kWh")
    print(f"  sonda {len(a):5d} flujos · {a.kWh.sum():9.1f} kWh")
    if len(ref) == len(a):
        d = np.abs(np.sort(ref.kWh_transados.values) - np.sort(a.kWh.values)).max()
        print(f"  máxima diferencia en kWh: {d:.2e}"
              f"  {'REPRODUCE' if d < 1e-6 else 'NO REPRODUCE'}")
    else:
        print("  NO REPRODUCE: distinto número de flujos")


if __name__ == "__main__":
    main()
