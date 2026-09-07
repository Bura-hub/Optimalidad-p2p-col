"""
La medida de calidad del modelo base, aplicada a nuestra adaptacion.

Chacon valida su metodo contra un **optimo centralizado** que maximiza la
suma de los bienestares de compradores y vendedores, resuelto con punto
interior, y publica el error normalizado de esa comparacion: **0,316 % de
media**, por debajo del 6 % en el peor caso.

Nuestro proyecto **nunca habia hecho esa comprobacion**. El oraculo que hay
en el repositorio no sirve para esto: es un lazo de Stackelberg estatico con
optimizador dentro, no un centralizado.

Esta sonda construye el centralizado que falta y mide contra el las dos vias
del proyecto, la alternada y la acoplada, con las mismas dos cantidades que
usa el articulo, leidas de su propio texto:

    ahorro del comprador   S_i  = pi_gs * sum_j P_ji - pi_i * sum_j P_ji
    prima del vendedor     SR_j = sum_i pi_i * P_ji - pi_gb * sum_i P_ji

El error normalizado de cada hora es la suma de las diferencias absolutas
contra el centralizado, dividida por el total del centralizado.

QUE MIDE DE VERDAD ESTA METRICA
-------------------------------
Conviene decirlo, porque no es obvio. La suma de las dos cantidades es el
ancho de la banda por la energia transada, que es la identidad H-33. Y el
volumen esta fijado por las restricciones. De modo que **el total es el
mismo para todos los metodos**, y el error no mide eficiencia economica:
mide **cuanto se parece el reparto** entre vendedores y compradores, y su
distribucion entre agentes, al que produce el centralizado.

LA RESTRICCION QUE FALTABA
--------------------------
Un primer intento devolvio un centralizado que **no transaba nada**, y de
ahi que la metrica saliera indefinida. La razon parecia de fondo: la suma de
bienestares es decreciente en lo transado, porque los dos pagos se cancelan
exactamente y lo que queda son costos.

El algebra es correcta pero **no es vinculante**, y el error estaba en la
sonda, no en el modelo. El modelo base NO deja elegir cuanto transar: fija
el volumen al lado corto con una restriccion de IGUALDAD. La primera version
de esta sonda usaba desigualdades en los dos lados, y por eso el optimizador
podia cerrar el mercado. Ver H-39.

Uso:
    python error_centralizado.py --muestra 20
    python error_centralizado.py --muestra 20 --base
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

from core.replicator_buyers import buyer_welfare, solve_buyers  # noqa: E402
from core.replicator_sellers import seller_welfare, solve_sellers  # noqa: E402


def centralizado(G_net, D_net, a_j, b_j, lam_j, theta_j, G_klim_i,
                 lam_i, theta_i, etha_i, pi_gs, pi_gb, semillas=3):
    """Maximiza la suma de bienestares sobre P y pi a la vez.

    Es la referencia teorica del articulo: un unico problema, sin juego ni
    alternancia. Se resuelve con programacion cuadratica secuencial desde
    varias semillas, porque el objetivo no es concavo y una sola salida
    podria quedarse en un optimo local.
    """
    J, I = len(G_net), len(D_net)
    gs = np.broadcast_to(np.asarray(pi_gs, float), (I,))

    def desarma(x):
        return x[:J * I].reshape(J, I), x[J * I:]

    def objetivo(x):
        P, pi = desarma(x)
        return -(seller_welfare(P, G_net, a_j, b_j, lam_j, theta_j, pi)
                 + buyer_welfare(pi, P, G_klim_i, lam_i, theta_i, etha_i))

    restr = [
        {"type": "ineq", "fun": lambda x, j=j: G_net[j] - desarma(x)[0][j].sum()}
        for j in range(J)
    ] + [
        {"type": "ineq", "fun": lambda x, i=i: D_net[i] - desarma(x)[0][:, i].sum()}
        for i in range(I)
    ]

    # La restriccion que faltaba, y que lo cambia todo. El modelo base NO
    # deja elegir cuanto transar: fija el volumen al lado corto con una
    # IGUALDAD (`Restris3` y `Restris4` de Bienestar6p.py, ecuaciones 11 y
    # 13). Si sobra oferta, cada comprador recibe exactamente su deficit; si
    # falta, se coloca toda la generacion.
    #
    # Sin ella el centralizado elige no transar, porque la suma de
    # bienestares es decreciente en lo transado. Con ella ese hecho deja de
    # ser vinculante: el volumen no esta en el conjunto de decision, y lo
    # unico que se optimiza es el emparejamiento y los precios.
    if float(np.sum(D_net)) <= float(np.sum(G_net)):
        restr += [{"type": "eq",
                   "fun": lambda x, i=i: desarma(x)[0][:, i].sum() - D_net[i]}
                  for i in range(I)]
    else:
        restr += [{"type": "eq",
                   "fun": lambda x: desarma(x)[0].sum() - float(np.sum(G_net))}]
    lim = [(0.0, None)] * (J * I) + [(float(pi_gb), float(gs[i]))
                                     for i in range(I)]

    corto = min(float(np.sum(G_net)), float(np.sum(D_net)))
    mejor, mejor_v = None, np.inf
    rng = np.random.default_rng(42)
    for s in range(semillas):
        # el arranque respeta la igualdad de volumen desde el principio; solo
        # se aleatoriza el reparto DENTRO de esa igualdad, y los precios
        P0 = (np.tile(D_net / J, (J, 1)) if np.sum(G_net) >= np.sum(D_net)
              else np.tile(G_net / I, (I, 1)).T)
        if s > 0:
            peso = rng.uniform(0.3, 1.0, (J, I))
            if np.sum(G_net) >= np.sum(D_net):    # cada columna suma D_net[i]
                P0 = peso / peso.sum(axis=0, keepdims=True) * D_net
            else:                                 # cada fila suma G_net[j]
                P0 = peso / peso.sum(axis=1, keepdims=True) * G_net[:, None]
        P0 = np.clip(P0, 1e-10, None)
        pi0 = (np.full(I, pi_gb) if s == 0 else
               rng.uniform(pi_gb, gs, size=I))
        x0 = np.concatenate([P0.ravel(), pi0])
        try:
            r = minimize(objetivo, x0, method="SLSQP", bounds=lim,
                         constraints=restr,
                         options={"maxiter": 600, "ftol": 1e-9})
        except Exception:
            continue
        if r.success and r.fun < mejor_v:
            mejor_v, mejor = r.fun, r.x
    if mejor is None:
        return None
    P, pi = desarma(mejor)
    return dict(P=P, pi=np.clip(pi, pi_gb, gs), W=-mejor_v, corto=corto)


def cantidades(P, pi, pi_gs, pi_gb):
    """Las dos cantidades con que el articulo mide el error."""
    I = len(pi)
    gs = np.broadcast_to(np.asarray(pi_gs, float), (I,))
    S_i = np.array([(gs[i] - pi[i]) * float(P[:, i].sum()) for i in range(I)])
    SR_j = np.array([float(np.sum((pi - pi_gb) * P[j, :]))
                     for j in range(P.shape[0])])
    return S_i, SR_j


def error(ref, cand) -> float:
    """Error normalizado contra la referencia, en tanto por ciento."""
    (Sr, Rr), (Sc, Rc) = ref, cand
    den = float(np.abs(Sr).sum() + np.abs(Rr).sum())
    if den < 1e-12:
        return np.nan
    num = float(np.abs(Sc - Sr).sum() + np.abs(Rc - Rr).sum())
    return 100.0 * num / den


def resuelve_vias(dat, k, sv_alt=None):
    """Las tres vias sobre la misma hora: centralizado, acoplado, alternado."""
    from core.coupled_ode_convergence import solve_coupled_for_hour
    from core.market_prep import classify_agents, compute_generation_limit
    from paso_a_paso import resuelve as _resuelve_aco

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
    piso_h = float(np.min(dat["piso"][sids, k]))
    gs_esc = float(np.max(techo_i))

    cen = centralizado(G_net, D_net, a[sids], b[sids], lam[sids],
                       theta[sids], g_klim[bids], lam[bids], theta[bids],
                       etha[bids], techo_i, piso_h)
    if cen is None:
        return None

    tr = solve_coupled_for_hour(
        G_net_j=G_net, D_net_i=D_net, a_j=a[sids], b_j=b[sids],
        lam_j=lam[sids], theta_j=theta[sids], G_klim_i=g_klim[bids],
        lam_i=lam[bids], theta_i=theta[bids], etha_i=etha[bids],
        pi_gs=gs_esc, pi_gb=piso_h, tau_sellers=0.001, tau_buyers=0.01,
        t_span=(0.0, 0.05), n_points=500)
    aco = dict(P=np.asarray(tr.P_star, float),
               pi=np.clip(tr.pi_star, piso_h, techo_i))

    J, I = len(sids), len(bids)
    P = (np.tile(D_net / J, (J, 1)) if np.sum(G_net) >= np.sum(D_net)
         else np.tile(G_net / I, (I, 1)).T)
    P = np.clip(P, 1e-10, None)
    pi = np.full(I, piso_h)
    for _ in range(2):
        P = solve_sellers(pi, G_net, D_net, a[sids], b[sids], tau=0.001,
                          t_span=(0.0, 0.005), n_points=150, method="LSODA")
        pi = np.clip(solve_buyers(P, a[sids], b[sids], etha[bids],
                                  pi_gs=gs_esc, pi_gb=piso_h, tau=0.01,
                                  t_span=(0.0, 0.005), n_points=150),
                     piso_h, techo_i)
    alt = dict(P=P, pi=pi)

    ref = cantidades(cen["P"], cen["pi"], techo_i, piso_h)
    return dict(
        k=k, I=I, J=J,
        err_aco=error(ref, cantidades(aco["P"], aco["pi"], techo_i, piso_h)),
        err_alt=error(ref, cantidades(alt["P"], alt["pi"], techo_i, piso_h)),
        vol_cen=float(cen["P"].sum()), vol_aco=float(aco["P"].sum()),
        vol_alt=float(alt["P"].sum()), corto=cen["corto"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=20)
    ap.add_argument("--cobertura", default="m1", choices=["m1", "m3"])
    ap.add_argument("--base", action="store_true")
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

    etiqueta = "caso base de Chacón" if args.base else args.cobertura.upper()
    print(f"Error contra el óptimo centralizado · {etiqueta} · "
          f"{len(sel)} horas", flush=True)
    print(f"  La referencia del artículo es 0,316 % de media y 6 % máximo",
          flush=True)
    print("=" * 70, flush=True)
    print(f"  {'hora':>6s} {'J':>2s} {'I':>2s} {'err acoplado':>13s} "
          f"{'err alternado':>14s}", flush=True)

    filas = []
    for k in sel:
        r = resuelve_vias(dat, int(k))
        if r is None:
            continue
        filas.append(r)
        print(f"  {r['k']:6d} {r['J']:2d} {r['I']:2d} {r['err_aco']:12.3f} % "
              f"{r['err_alt']:13.3f} %", flush=True)

    if not filas:
        print("  ninguna hora resuelta")
        return
    ea = np.array([f["err_aco"] for f in filas], float)
    el = np.array([f["err_alt"] for f in filas], float)
    print("\n  " + "-" * 66)
    print(f"  {'acoplado ':>14s}: media {np.nanmean(ea):7.3f} % · "
          f"mediana {np.nanmedian(ea):7.3f} % · máximo {np.nanmax(ea):7.3f} %")
    print(f"  {'alternado':>14s}: media {np.nanmean(el):7.3f} % · "
          f"mediana {np.nanmedian(el):7.3f} % · máximo {np.nanmax(el):7.3f} %")
    print(f"  {'Chacón (RD)':>14s}: media   0,316 % · máximo por debajo del 6 %")


if __name__ == "__main__":
    main()
