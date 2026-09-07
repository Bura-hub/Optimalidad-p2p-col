"""
El paso a paso de una hora: la normativa base frente al mercado entre pares.

Enseña, para una hora concreta y con las cotas medidas de CAL-47:

  1. Quien genera y quien consume, y de ahi quien vende y quien compra.
  2. **Que hace la normativa base** con el excedente de cada vendedor: la
     Resolucion CREG 174 lo parte en dos tramos, permuta mientras la
     inyeccion acumulada del mes no supere el retiro, y mercado mayorista a
     partir de ahi. Cada tramo se paga a un precio distinto.
  3. **La banda de cada agente**: su piso, que es lo que la red le paga si
     no negocia, y su techo, que es lo que su comercializador le cobra. No
     son iguales para todos: cuatro instituciones compran a ASC y el CESMAG
     a CEDENAR.
  4. **La negociacion**: la trayectoria del precio hasta el acuerdo, y donde
     cae respecto de las cotas.
  5. **El reparto**: cuanto se lleva cada parte frente a su alternativa.

Se resuelve con el solucionador ACOPLADO, que es el del modelo base, porque
el lazo alternado deja el precio pegado a una cota en el 72 % de los casos y
eso no es un acuerdo negociado.

Primero verifica con numeros. Solo dibuja si se le pide, y conviene mirar
los numeros antes.

Uso:
    python paso_a_paso.py --hora 3000
    python paso_a_paso.py --hora 3000 --dibuja
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
DOC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(DOC / "scripts"))

AGENTES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]


def carga(cobertura: str):
    """Series, tarifas por agente, bolsa y estado de permuta."""
    from core.opciones_externas import piso_por_vendedor, tramo_permuta
    from data.cedenar_tariff import (INSTITUTION_PROFILE,
                                     aplicar_regimen_no_regulado,
                                     cu_components_per_agent_hourly,
                                     pi_gs_per_agent_hourly)
    from data.preprocessing import PAPER_METER_DEMAND_CONFIG
    from data.xm_data_loader import MTEDataLoader

    aplicar_regimen_no_regulado(True)          # CAL-47
    cfg = PAPER_METER_DEMAND_CONFIG if cobertura == "m3" else None
    loader = MTEDataLoader(os.environ.get("MTE_ROOT",
                                          str(RAIZ / "MedicionesMTE_v3")),
                           demand_config=cfg)
    D, G, idx = loader.load(verbose=False)
    N = D.shape[0]
    nombres = AGENTES[:N]

    techo = pi_gs_per_agent_hourly(nombres, idx)          # (N, T)
    comp = cu_components_per_agent_hourly(nombres, idx)
    cvm = comp["Cvm"]
    peaje = comp["T"] + comp["D"] + comp["PR"] + comp["R"]

    b = pd.read_csv(RAIZ / "data" / "precios_bolsa_xm_api.csv")
    b["ts"] = pd.to_datetime(b["Fecha"]) + pd.to_timedelta(b["Hora"] - 1, "h")
    llaves = pd.DatetimeIndex(idx)
    if llaves.tz is not None:
        llaves = llaves.tz_localize(None)
    bolsa = b.set_index("ts")["Precio_COP_kWh"].reindex(llaves).to_numpy(float)

    mes = pd.Series(idx).dt.strftime("%Y-%m").to_numpy()
    perm = tramo_permuta(G, D, mes)
    piso = piso_por_vendedor(techo, cvm, bolsa, perm)

    com = {n: INSTITUTION_PROFILE[n].comercializador for n in nombres}
    return dict(D=D, G=G, idx=idx, nombres=nombres, techo=techo, cvm=cvm,
                peaje=peaje, bolsa=bolsa, perm=perm, piso=piso, com=com)


def carga_base():
    """El caso sintetico de Chacon, con la misma forma de datos.

    Sirve de contraste: si la maquinaria produce un acuerdo interior sobre
    los datos del modelo base, el diagnostico no depende de nuestras cotas
    medidas ni de nuestro dato.

    Dos diferencias que hay que declarar. El modelo base **no tiene la
    Resolucion CREG 174**, de modo que no hay tramos de permuta y de bolsa:
    su piso es una constante unica para todos. Y **no hay comercializadores
    distintos**, de modo que las cotas son las mismas para las seis
    instituciones.
    """
    from core.dr_program import compute_price_signal, run_dr_program
    from core.ems_p2p import GridParams
    from core.market_prep import compute_generation_limit
    from data.base_case_data import (get_agent_params, get_demand_profiles,
                                     get_generation_profiles)

    G = get_generation_profiles()
    D = get_demand_profiles()
    N, T = D.shape
    gr = GridParams()
    p = get_agent_params()

    # El modelo base corre con PROGRAMA DE RESPUESTA A LA DEMANDA activo,
    # 20 % de flexibilidad en los prosumidores y 10 % en los consumidores.
    # Sin el, la demanda de cada hora no es la que el articulo publica en su
    # tabla del caso de estudio, y la comparacion no seria de lo mismo. Con
    # dato real esta desactivado, porque la demanda medida es un insumo fijo.
    G_klim = np.column_stack([
        compute_generation_limit(G[:, k], p["a"], p["b"], p["c"], gr.pi_gs)
        for k in range(T)])
    pi_k = compute_price_signal(D, G_klim, gr.pi_gs, gr.pi_gb)
    D = run_dr_program(D, G_klim, pi_k, p["alpha"])
    nombres = [f"Agente {n + 1}" for n in range(N)]
    idx = pd.date_range("2025-01-01", periods=T, freq="1h")
    return dict(D=D, G=G, idx=idx, nombres=nombres,
                techo=np.full((N, T), gr.pi_gs),
                cvm=np.zeros((N, T)), peaje=np.zeros((N, T)),
                bolsa=np.full(T, gr.pi_gb),
                perm=np.zeros((N, T), dtype=bool),
                piso=np.full((N, T), gr.pi_gb),
                com={n: "modelo base" for n in nombres},
                modo="base")


def resuelve(dat: dict, k: int):
    """Resuelve la hora por la via del modelo base, con las cotas medidas."""
    from core.coupled_ode_convergence import solve_coupled_for_hour
    from core.market_prep import classify_agents, compute_generation_limit
    from data.xm_prices import get_b_for_real_data

    D, G = dat["D"], dat["G"]
    N = D.shape[0]
    a = np.zeros(N); c = np.zeros(N)
    if dat.get("modo") == "base":
        from data.base_case_data import get_agent_params
        p = get_agent_params()
        a, b, c = p["a"].copy(), p["b"].copy(), p["c"].copy()
        lam, theta, etha = p["lam"], p["theta"], p["etha"]
    else:
        b = get_b_for_real_data(N, dat["nombres"])
        lam = np.full(N, 100.0); theta = np.full(N, 0.5); etha = np.full(N, 0.1)

    # El limite economico usa el techo de cada agente
    g_klim = compute_generation_limit(G[:, k], a, b, c, dat["techo"][:, k])
    _, sids, bids = classify_agents(g_klim, D[:, k])
    if not sids or not bids:
        return None

    G_net = np.array([g_klim[j] - D[j, k] for j in sids])
    D_net = np.array([D[i, k] - g_klim[i] for i in bids])

    # El techo lo pone cada COMPRADOR; el piso, el vendedor mas barato de la
    # hora, porque por debajo de el no vende nadie. Los vendedores con piso
    # mas alto solo participan si el precio los cubre: esa es la restriccion
    # de participacion, que se comprueba al final.
    techo_i = dat["techo"][bids, k]
    piso_j = dat["piso"][sids, k]
    piso_h = float(np.min(piso_j))

    # RESTRICCION DE PARTICIPACION. El modelo forma un precio por comprador,
    # no por pareja, de modo que el piso de cada vendedor no puede acotar ese
    # precio directamente. Lo que si puede es decidir quien entra: un vendedor
    # cuyo piso supere el precio que se le ofrece no habria vendido.
    #
    # Se itera: se resuelve con los vendedores activos, se retira a los que no
    # cubran su alternativa, y se vuelve a resolver. Con cinco agentes son a lo
    # sumo cinco vueltas. Sin esto la primera medicion sobre dato real daba a
    # Mariana una prima negativa, porque el piso agregado tomaba el del CESMAG,
    # que compra a otro comercializador y por eso tiene una alternativa peor.
    activos = list(range(len(sids)))
    retirados = []
    for _ in range(len(sids) + 1):
        if not activos:
            return None
        sa = [sids[a] for a in activos]
        Gn = G_net[activos]
        piso_a = piso_j[activos]
        piso_h = float(np.min(piso_a))
        tr = solve_coupled_for_hour(
            G_net_j=Gn, D_net_i=D_net, a_j=a[sa], b_j=b[sa],
            lam_j=lam[sa], theta_j=theta[sa], G_klim_i=g_klim[bids],
            lam_i=lam[bids], theta_i=theta[bids], etha_i=etha[bids],
            pi_gs=float(np.max(techo_i)), pi_gb=piso_h,
            tau_sellers=0.001, tau_buyers=0.01,
            t_span=(0.0, 0.05), n_points=500)
        pi = np.clip(tr.pi_star, piso_h, techo_i)
        P = np.asarray(tr.P_star, float)
        # Un vendedor sobra si TODA su venta va por debajo de su alternativa
        fuera = []
        for u, a_idx in enumerate(activos):
            vendido = P[u, :]
            if vendido.sum() <= 1e-9:
                continue
            mejor = float(np.max(pi[vendido > 1e-9]))
            if mejor < piso_j[a_idx] - 1e-9:
                fuera.append(a_idx)
        if not fuera:
            break
        retirados.extend(fuera)
        activos = [x for x in activos if x not in fuera]

    sids_f = [sids[a] for a in activos]
    return dict(k=k, sids=sids_f, bids=bids, g_klim=g_klim,
                G_net=G_net[activos], D_net=D_net, techo_i=techo_i,
                piso_j=piso_j[activos], piso_h=piso_h, pi=pi, P=P, tr=tr,
                retirados=[sids[a] for a in retirados])


def informa(dat: dict, r: dict) -> bool:
    """Imprime el paso a paso. Devuelve si todo cuadro."""
    k = r["k"]
    nom = dat["nombres"]
    ts = pd.DatetimeIndex(dat["idx"])[k]
    ok = True

    print(f"\nHORA {k} · {ts:%Y-%m-%d %H:%M} ({['lun','mar','mie','jue',
          'vie','sab','dom'][ts.dayofweek]})")
    print("=" * 78)

    print("\n1 · Quien es quien esa hora")
    print(f"  {'institucion':11s} {'gen kW':>8s} {'dem kW':>8s} "
          f"{'papel':>10s} {'neto kW':>9s} {'comercializador':>16s}")
    for n in range(len(nom)):
        gen, dem = dat["G"][n, k], dat["D"][n, k]
        papel = ("vende" if n in r["sids"] else
                 "compra" if n in r["bids"] else "ni uno")
        print(f"  {nom[n]:11s} {gen:8.3f} {dem:8.3f} {papel:>10s} "
              f"{gen - dem:9.3f} {dat['com'][nom[n]]:>16s}")

    print("\n2 · Que hace la normativa base con el excedente de cada vendedor")
    print(f"  {'vendedor':11s} {'excedente':>10s} {'tramo':>10s} "
          f"{'se paga a':>10s} {'vale':>10s}")
    for a, j in enumerate(r["sids"]):
        exc = r["G_net"][a]
        tramo = ("cota unica" if dat.get("modo") == "base"
                 else "permuta" if dat["perm"][j, k] else "bolsa")
        p = dat["piso"][j, k]
        print(f"  {nom[j]:11s} {exc:10.3f} {tramo:>10s} {p:10.2f} "
              f"{exc * p:10.0f}")

    print("\n3 · La banda de cada comprador")
    print(f"  {'comprador':11s} {'deficit':>9s} {'piso':>9s} {'techo':>9s} "
          f"{'ancho':>9s} {'acordado':>10s} {'posicion':>10s}")
    for i, b in enumerate(r["bids"]):
        techo = r["techo_i"][i]
        ancho = techo - r["piso_h"]
        pos = (r["pi"][i] - r["piso_h"]) / ancho if ancho > 1e-9 else 0.0
        marca = ("EN EL PISO" if pos < 1e-6 else
                 "EN EL TECHO" if pos > 1 - 1e-6 else f"{100*pos:.0f} % ")
        if pos < 1e-6 or pos > 1 - 1e-6:
            ok = False
        print(f"  {nom[b]:11s} {r['D_net'][i]:9.3f} {r['piso_h']:9.2f} "
              f"{techo:9.2f} {ancho:9.2f} {r['pi'][i]:10.2f} {marca:>10s}")

    print("\n4 · Los flujos y su reparto")
    print(f"  {'vendedor':11s} {'comprador':11s} {'kWh':>8s} {'precio':>9s} "
          f"{'prima vend':>11s} {'ahorro comp':>12s}")
    tot_pv = tot_ac = 0.0
    for a, j in enumerate(r["sids"]):
        for i, b in enumerate(r["bids"]):
            q = float(r["P"][a, i])
            if q <= 1e-9:
                continue
            p = r["pi"][i]
            pv = (p - dat["piso"][j, k]) * q
            ac = (r["techo_i"][i] - p) * q
            tot_pv += pv; tot_ac += ac
            if pv < -1e-6:
                print("      AVISO: prima negativa, el vendedor no habria "
                      "aceptado (restriccion de participacion)")
                ok = False
            print(f"  {nom[j]:11s} {nom[b]:11s} {q:8.3f} {p:9.2f} "
                  f"{pv:11.1f} {ac:12.1f}")
    tot = tot_pv + tot_ac
    if tot > 0:
        print(f"  {'':23s} excedente {tot:10.1f} COP · reparto "
              f"{100*tot_pv/tot:.1f} vendedor / {100*tot_ac/tot:.1f} comprador")

    print("\n5 · Como llego el precio hasta ahi")
    traj = r["tr"].pi_t
    n = traj.shape[1]
    cola = max(1, n // 10)
    mov = float(np.max(np.abs(traj[:, -1] - traj[:, -cola])))
    rec = float(np.max(np.abs(traj.max(axis=1) - traj.min(axis=1))))
    print(f"  arranque {traj[:, 0].mean():8.2f} · final "
          f"{traj[:, -1].mean():8.2f} · recorrido {rec:8.2f}")
    print(f"  movimiento en el ultimo decimo: {mov:.4f} "
          f"({100*mov/rec if rec > 1e-12 else 0:.2f} % del recorrido)")
    print(f"  integrador: {'exito' if getattr(r['tr'], 'success', True) else 'FALLO'}")
    if not getattr(r["tr"], "success", True):
        ok = False

    print("\n" + ("  TODO CUADRA: precios interiores y participacion respetada"
                  if ok else
                  "  HAY AVISOS: revisar antes de dibujar"))
    return ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hora", type=int, default=None)
    ap.add_argument("--cobertura", default="m1", choices=["m1", "m3"])
    ap.add_argument("--dibuja", action="store_true")
    ap.add_argument("--base", action="store_true",
                    help="corre sobre el caso sintetico de Chacon en vez de "
                         "sobre el dato real, como contraste")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    dat = carga_base() if args.base else carga(args.cobertura)
    D, G = dat["D"], dat["G"]

    if args.hora is None:
        # Una hora con varios de cada lado, para que haya negociacion
        exc = np.maximum(G - D, 0.0) > 1e-9
        det = np.maximum(D - G, 0.0) > 1e-9
        cand = np.flatnonzero((exc.sum(axis=0) >= 2) & (det.sum(axis=0) >= 3))
        if len(cand) == 0:
            raise SystemExit("sin horas con varios de cada lado")
        args.hora = int(cand[len(cand) // 2])
        print(f"  hora elegida automaticamente: {args.hora} "
              f"(de {len(cand)} con al menos 2 vendedores y 3 compradores)")

    r = resuelve(dat, args.hora)
    if r is None:
        raise SystemExit(f"la hora {args.hora} no tiene mercado")
    ok = informa(dat, r)

    if args.dibuja:
        if not ok:
            print("\n  No se dibuja: primero hay que resolver los avisos.")
            return
        print("\n  (el dibujo se genera en el paso siguiente)")


if __name__ == "__main__":
    main()
