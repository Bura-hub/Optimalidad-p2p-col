"""
Cuanto del excedente alcanzable captura el mecanismo.

Es la medida de calidad que al proyecto le faltaba y que la pregunta por el
objetivo de Chacon destapo.

POR QUE NO SIRVE LA SUMA DE BIENESTARES
---------------------------------------
Medido: el bienestar total, tal como esta implementado, **se maximiza sin
transar nada**, y cae monotonamente conforme el mercado opera. La razon es
que los dos terminos de pago se cancelan exactamente, porque son
transferencias internas, y lo que queda son costos de generacion y un
termino de rivalidad entre compradores, ambos crecientes con lo transado.

Le falta la pieza que importa: **la utilidad del comprador por la energia
que recibe**. Lo unico que hay, `lam*G - theta*G^2`, es la utilidad de su
PROPIA generacion, no de la comprada.

De modo que un centralizado que maximice esa suma cierra el mercado, y no
puede servir de referencia.

CUAL ES EL OBJETIVO CORRECTO
----------------------------
Lo que un planificador de una comunidad energetica maximiza es **lo que la
comunidad deja de pagarle a la red**. Por cada kWh que va del vendedor j al
comprador i, la comunidad se ahorra:

    (lo que i le pagaria a su comercializador) - (lo que la red le pagaria
     a j por inyectarlo)  =  techo_i - piso_j

El costo de generar **no entra**: el panel genera igual, se venda al vecino
o se exporte, de modo que en el momento de decidir a quien vender ese costo
esta hundido. Lo que si gobierna es el limite economico de generacion, que
se calcula antes y aqui se toma como dado.

El optimo centralizado es entonces un **problema de transporte lineal**:

    max  sum_ji (techo_i - piso_j) * P_ji
    s.a. sum_i P_ji <= G_net_j     (lo que cada vendedor tiene)
         sum_j P_ji <= D_net_i     (lo que cada comprador necesita)
         P_ji >= 0

que encaja con lo ya sabido: el reparto es lineal y su valor optimo unico.

LA METRICA, Y POR QUE SE PARTE EN DOS
-------------------------------------
Eficiencia = excedente logrado / excedente maximo alcanzable. Pero ese
cociente mezcla dos preguntas distintas, y conviene separarlas:

  volumen  = cuanta energia se movio, contra la que se podia mover
  emparej. = cuanto vale en promedio cada kWh movido, contra lo que valdria
             si estuviera bien emparejado

y su producto es la eficiencia total. La distincion importa porque **si
todos los compradores tienen el mismo techo y todos los vendedores el mismo
piso, el emparejamiento no decide nada**: cada kWh vale igual venga de donde
venga, y la eficiencia se reduce al volumen. Eso es exactamente lo que pasa
en el caso base del articulo, y es la razon de que alli el 100 % sea barato.

En la comunidad real la banda **no** es uniforme, porque hay dos
comercializadores, y entonces el emparejamiento si decide. La sonda marca
cada hora con el rotulo que corresponde para que el numero no se lea de mas.

Uso:
    python eficiencia.py --muestra 40
    python eficiencia.py --muestra 12 --base
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

from core.replicator_buyers import solve_buyers  # noqa: E402
from core.replicator_sellers import solve_sellers  # noqa: E402


def optimo_centralizado(G_net, D_net, techo_i, piso_j):
    """El reparto que maximiza lo que la comunidad deja de pagarle a la red."""
    J, I = len(G_net), len(D_net)
    # linprog minimiza, de modo que el objetivo va con signo cambiado
    c = -np.array([[techo_i[i] - piso_j[j] for i in range(I)]
                   for j in range(J)]).ravel()
    A, b = [], []
    for j in range(J):                       # capacidad del vendedor
        fila = np.zeros(J * I); fila[j * I:(j + 1) * I] = 1.0
        A.append(fila); b.append(G_net[j])
    for i in range(I):                       # necesidad del comprador
        fila = np.zeros(J * I); fila[i::I] = 1.0
        A.append(fila); b.append(D_net[i])
    r = linprog(c, A_ub=np.array(A), b_ub=np.array(b),
                bounds=[(0, None)] * (J * I), method="highs")
    if not r.success:
        return None
    P = r.x.reshape(J, I)
    return dict(P=P, excedente=float(-r.fun), volumen=float(P.sum()))


def excedente(P, techo_i, piso_j):
    """Lo que la comunidad deja de pagarle a la red con este reparto."""
    J, I = P.shape
    return float(sum((techo_i[i] - piso_j[j]) * P[j, i]
                     for j in range(J) for i in range(I)))


def descompone(P, cen, techo_i, piso_j):
    """Parte la eficiencia en volumen y emparejamiento.

    El excedente logrado es (volumen) x (valor medio del kWh movido). El
    optimo tiene los dos suyos, de modo que el cociente se factoriza y cada
    factor responde a una pregunta separada.
    """
    exc, vol = excedente(P, techo_i, piso_j), float(P.sum())
    vol_op, exc_op = cen["volumen"], cen["excedente"]
    ef = 100.0 * exc / exc_op
    ef_vol = 100.0 * vol / vol_op if vol_op > 1e-12 else np.nan
    # valor medio por kWh de cada reparto; su cociente es el emparejamiento
    ef_emp = ef / ef_vol * 100.0 if ef_vol and ef_vol > 1e-12 else np.nan
    return exc, vol, ef, ef_vol, ef_emp


def excede(P, G_net, D_net, tol=1e-6):
    """Cuanto se pasa el reparto de lo que hay y de lo que se necesita."""
    return float(max(np.max(P.sum(axis=1) - G_net), np.max(P.sum(axis=0) - D_net),
                     0.0)) if P.size else 0.0


def resuelve(dat, k):
    from core.coupled_ode_convergence import solve_coupled_for_hour
    from core.market_prep import classify_agents, compute_generation_limit

    D, G = dat["D"], dat["G"]
    N = D.shape[0]
    if dat.get("modo") == "base":
        from data.base_case_data import get_agent_params
        p = get_agent_params()
        a, b, c = p["a"].copy(), p["b"].copy(), p["c"].copy()
        lam, theta, etha = p["lam"], p["theta"], p["etha"]
    else:
        from data.xm_prices import get_b_for_real_data
        a = np.zeros(N); c = np.zeros(N)
        b = get_b_for_real_data(N, dat["nombres"])
        lam = np.full(N, 100.0); theta = np.full(N, 0.5); etha = np.full(N, 0.1)

    g_klim = compute_generation_limit(G[:, k], a, b, c, dat["techo"][:, k])
    _, sids, bids = classify_agents(g_klim, D[:, k])
    if not sids or not bids:
        return None
    G_net = np.array([g_klim[j] - D[j, k] for j in sids])
    D_net = np.array([D[i, k] - g_klim[i] for i in bids])
    techo_i = dat["techo"][bids, k]
    piso_j = dat["piso"][sids, k]
    piso_h = float(np.min(piso_j))
    gs_esc = float(np.max(techo_i))
    # C-147: el techo de CADA comprador, no el mayor de la hora.
    # Pasar el maximo y recortar despues es el defecto de H-45:
    # deja a los del techo bajo pagando exactamente el suyo, con
    # ahorro cero por construccion. `gs_esc` queda solo de guarda.


    cen = optimo_centralizado(G_net, D_net, techo_i, piso_j)
    if cen is None or cen["excedente"] <= 1e-9:
        return None

    tr = solve_coupled_for_hour(
        G_net_j=G_net, D_net_i=D_net, a_j=a[sids], b_j=b[sids],
        lam_j=lam[sids], theta_j=theta[sids], G_klim_i=g_klim[bids],
        lam_i=lam[bids], theta_i=theta[bids], etha_i=etha[bids],
        pi_gs=techo_i, pi_gb=piso_h, tau_sellers=0.001, tau_buyers=0.01,
        t_span=(0.0, 0.05), n_points=500)
    P_aco = np.asarray(tr.P_star, float)

    J, I = len(sids), len(bids)
    P = (np.tile(D_net / J, (J, 1)) if np.sum(G_net) >= np.sum(D_net)
         else np.tile(G_net / I, (I, 1)).T)
    P = np.clip(P, 1e-10, None)
    pi = np.full(I, piso_h)
    for _ in range(2):
        P = solve_sellers(pi, G_net, D_net, a[sids], b[sids], tau=0.001,
                          t_span=(0.0, 0.005), n_points=150, method="LSODA")
        pi = np.clip(solve_buyers(P, a[sids], b[sids], etha[bids],
                                  pi_gs=techo_i, pi_gb=piso_h, tau=0.01,
                                  t_span=(0.0, 0.005), n_points=150),
                     piso_h, techo_i)

    # Si todos los techos y todos los pisos son iguales, cada kWh vale lo
    # mismo venga de donde venga y el emparejamiento no decide nada.
    uniforme = bool(np.ptp(techo_i) < 1e-9 and np.ptp(piso_j) < 1e-9)

    _, v_a, ef_a, efv_a, efe_a = descompone(P_aco, cen, techo_i, piso_j)
    _, v_l, ef_l, efv_l, efe_l = descompone(P, cen, techo_i, piso_j)
    return dict(
        k=k, J=J, I=I, uniforme=uniforme,
        max_exc=cen["excedente"], vol_cen=cen["volumen"],
        ef_aco=ef_a, efvol_aco=efv_a, efemp_aco=efe_a, vol_aco=v_a,
        ef_alt=ef_l, efvol_alt=efv_l, efemp_alt=efe_l, vol_alt=v_l,
        exceso_aco=excede(P_aco, G_net, D_net),
        exceso_alt=excede(P, G_net, D_net))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=40)
    ap.add_argument("--cobertura", default="m1", choices=["m1", "m3"])
    ap.add_argument("--base", action="store_true")
    ap.add_argument("--particion", default=None,
                    help="k/n: este proceso toma una de cada n horas, "
                         "empezando por la k. Sirve para repartir la muestra "
                         "entre varios núcleos; la unión de las particiones "
                         "es exactamente la muestra entera.")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    from paso_a_paso import carga, carga_base
    dat = carga_base() if args.base else carga(args.cobertura)
    D, G = dat["D"], dat["G"]
    vende = (np.maximum(G - D, 0.0) > 1e-9).any(axis=0)
    compra = (np.maximum(D - G, 0.0) > 1e-9).any(axis=0)
    cand = np.flatnonzero(vende & compra)
    rng = np.random.default_rng(42)
    sel = np.sort(rng.choice(cand, size=min(args.muestra, len(cand)),
                             replace=False))
    marca = ""
    if args.particion:
        k_p, n_p = (int(x) for x in args.particion.split("/"))
        if not (1 <= k_p <= n_p):
            raise SystemExit(f"partición {args.particion} fuera de rango")
        sel = sel[k_p - 1::n_p]
        marca = f"_p{k_p}de{n_p}"

    etiqueta = "caso base de Chacón" if args.base else args.cobertura.upper()
    print(f"Eficiencia frente al reparto óptimo · {etiqueta} · "
          f"{len(sel)} horas de {len(cand)}", flush=True)
    print("  100 % es capturar todo el excedente alcanzable; se parte en "
          "volumen × emparejamiento", flush=True)
    print("  la marca «u» dice que la banda es uniforme esa hora, y entonces "
          "el emparejamiento no decide", flush=True)
    print("=" * 86, flush=True)
    print(f"  {'hora':>6s} {'J':>2s} {'I':>2s} {'':>1s} {'máx COP':>10s} "
          f"{'aco tot':>8s} {'vol':>7s} {'emp':>7s} "
          f"{'alt tot':>9s} {'vol':>7s} {'emp':>7s}", flush=True)

    sal = Path(__file__).parent / "salidas"
    sal.mkdir(exist_ok=True)
    suf = "base" if args.base else args.cobertura
    import pandas as pd

    filas = []
    for k in sel:
        r = resuelve(dat, int(k))
        if r is None:
            continue
        filas.append(r)
        print(f"  {r['k']:6d} {r['J']:2d} {r['I']:2d} "
              f"{'u' if r['uniforme'] else ' ':>1s} {r['max_exc']:10.1f} "
              f"{r['ef_aco']:6.1f} % {r['efvol_aco']:5.1f} % "
              f"{r['efemp_aco']:5.1f} % "
              f"{r['ef_alt']:7.1f} % {r['efvol_alt']:5.1f} % "
              f"{r['efemp_alt']:5.1f} %", flush=True)
        # se guarda en cada paso, para que un corte no pierda lo hecho
        pd.DataFrame(filas).to_csv(sal / f"eficiencia_{suf}{marca}.csv", index=False)

    if not filas:
        print("  ninguna hora con excedente alcanzable")
        return

    def resume(nombre, clave):
        v = np.array([f[clave] for f in filas], float)
        tot = sum(f["max_exc"] for f in filas)
        pon = sum(f[clave] * f["max_exc"] for f in filas) / tot
        return (f"  {nombre:>22s}: media {np.nanmean(v):6.1f} % · mediana "
                f"{np.nanmedian(v):6.1f} % · mínimo {np.nanmin(v):6.1f} % · "
                f"ponderada por excedente {pon:6.1f} %")

    n_u = sum(f["uniforme"] for f in filas)
    print("\n  " + "-" * 82)
    for nom, cl in (("acoplado total", "ef_aco"), ("acoplado volumen", "efvol_aco"),
                    ("acoplado emparej.", "efemp_aco"),
                    ("alternado total", "ef_alt"), ("alternado volumen", "efvol_alt"),
                    ("alternado emparej.", "efemp_alt")):
        print(resume(nom, cl))
    print(f"\n  banda uniforme en {n_u} de {len(filas)} horas; ahí el "
          f"emparejamiento es 100 % por construcción")
    ex = max(max(f["exceso_aco"] for f in filas),
             max(f["exceso_alt"] for f in filas))
    print(f"  mayor incumplimiento de una restricción: {ex:.2e} kWh")
    print(f"\n  detalle en salidas/eficiencia_{suf}{marca}.csv")


if __name__ == "__main__":
    main()
