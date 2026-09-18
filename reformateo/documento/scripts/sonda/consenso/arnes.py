"""Arnes de la sonda del consenso: la dinamica del juego, acelerada, para
validar el reposo calculado en forma cerrada (mediciones M-A a M-G).

QUE ES
------
Una COPIA del lado derecho de `core/coupled_ode_convergence.py` (`_rhs`) con
ganchos para las variantes del juego que se midieron el 2026-09-16, mas el
cargador de horas reales (`carga`, `entradas`, `hora_de`), el integrador por
tramos con tope (`integra_tramos`) y el resumen de cada punto de control
(`resumen`). No sustituye al motor ni escribe nada: solo lee el repositorio.

DE DONDE VIENE
--------------
De la sonda del consenso del 2026-09-16, cuyo informe es
`.superpowers/sdd/2026-09-16-sonda-equilibrio/consenso-report.md`. Alli vivia
fuera del arbol, en el borrador de la sesion, con la raiz del repositorio
escrita a mano. Aqui esta con la misma logica, la raiz calculada desde el
propio fichero y sin ninguna ruta del borrador ni del usuario.

POR QUE EXISTE, Y POR QUE ESTO NO VA EN EL MOTOR
------------------------------------------------
La validacion del reposo (M-A a M-G) necesita integrar la dinamica
regularizada HASTA EL REPOSO, y en las horas rigidas eso no cabe: con topados
o con varios vendedores, el multiplicador de capacidad crece sin tope y el
modo rapido que impone endurece el sistema, de modo que llegar a t = 20 cuesta
del orden de 1e9 evaluaciones del lado derecho (consenso-report.md, sec. 1
punto 5 y sec. 3). El arnes mete un recurso numerico que el motor no tiene:

    ACELERACION k (`k_lento`): multiplica por k el bloque de los compradores
    (precios, gamma y su filtro) y el replicador del vendedor, y deja los
    multiplicadores y sus filtros como estan.

Los CEROS del lado derecho no cambian con k: el reposo es el mismo, y lo unico
que cambia es el tiempo en que se llega. Por eso todo resultado acelerado se
rotula con su k y con su «teq» (tiempo equivalente sin acelerar, t·k). La
equivalencia se midio: en las horas 109 de E0, 152 de K1 y 85 de E0 la
trayectoria acelerada es la misma con el tiempo reescalado (diferencias menores
que 1e-6 (kWh)); en la 130 solo se parece (hasta 0,04 (kWh) en teq 5); y en la
hora 36, de energia casi nula, la salida de la esquina cambia. Es decir, la
aceleracion es EXACTA con compradores libres y APROXIMADA con topados, y por
eso la tolerancia de aceptacion se afloja en esas horas (1 % de E y 0,5
(COP/kWh), en vez de 1e-3·E y 0,05).

El motor no hace esto ni debe hacerlo: la via de produccion resuelve el
mercado en forma cerrada (`core/reposo_mercado.py`, D48) y la via acoplada
reproduce `Documentos/copy/JoinFinal.m` al bit con sus defectos. Un factor de
velocidad metido ahi seria un apartamiento del modelo base sin necesidad. Aqui
es legitimo porque lo que se mide es A DONDE LLEGA la dinamica, no cuanto
tarda.

QUE LO HACE CREIBLE
-------------------
`comprueba_contra_el_motor(e, ...)`: el lado derecho de `construye` tiene que
coincidir AL BIT con el que el motor evalua (`captura_motor`, que atrapa el
`_rhs` real de `solve_coupled_for_hour`), en las diez ramas de `ramas(e)`: los
cuatro defectos (peso del jugador virtual por arranque de la oferta), el
termino entropico (D49), el costo del vendedor por su alternativa y el piso del
vendedor marginal (D68, las dos ramas que sostienen M-B y el ancla de M-A),
las tres juntas, y las dos configuraciones de M-G (el codigo de la autora:
competencia `matlab` y oferta a partes iguales, con los dos pesos). Los
estados se perturban de forma ADITIVA y por bloque, desde el arranque y desde
un estado con los filtros de los multiplicadores cargados
(`perturba`, `estado_cargado`), de modo que se ejercen los ocho bloques del
estado; la version anterior perturbaba multiplicando y nunca probaba los
filtros, que valen cero en el arranque (grave 1 de la revision de 4c). Si no
coincide, dice en que bloque difiere y cuanto. Se corre solo:

    python -u reformateo/documento/scripts/sonda/consenso/arnes.py
    python -u .../arnes.py E0 "2025-05-09 13:00" K1 "2025-05-11 08:00"

Siempre sobre el caso publicado de Chacon y sobre una hora sintetica de pisos
distintos (`caso_pisos_distintos`, la que ejerce de verdad el piso marginal),
que no necesitan datos reales; los argumentos anaden horas reales. Lo mismo, y
el criterio de consenso, la aceleracion y el veredicto, esta en
`tests/test_arnes_consenso.py`.

QUE TRAE
--------
- carga(caso): E0, K1 (demanda x2), E4 (generacion x7), E5 (x10) y CV2 (el
  cargo de comercializar x2), con la receta de `paso_a_paso.carga`.
- entradas(dat, K): vendedores, compradores, excedentes, deficits, techo por
  comprador, piso por vendedor y piso de la hora.
- captura_motor(e, **op): el lado derecho EXACTO del motor (capturado).
- construye(e, **variante): COPIA del lado derecho del motor con ganchos de
  variante; con la variante vacia coincide con el del motor (se comprueba).
- integra_tramos(rhs, X0, cortes, tope_s): LSODA rtol = atol = 1e-6 (H-51).
- resumen(e, X): precios, reparto por comprador, ponderado, parte del
  vendedor, suma de precios, virtual.
- caso_chacon(hora): el caso publicado (Tablas II y IV), sin datos reales.
- comprueba_contra_el_motor, ramas, perturba, estado_cargado, piso_marginal y
  caso_pisos_distintos: la comprobacion contra el motor (arriba).
"""
import os
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
# La raiz del repositorio, desde el propio fichero:
# reformateo/documento/scripts/sonda/consenso/arnes.py -> cinco niveles arriba.
AQUI = Path(__file__).resolve().parent
R = AQUI.parents[4]
os.environ.setdefault("MTE_ROOT", str(R / "MedicionesMTE_v3"))
for _p in (R, AQUI.parent, AQUI):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
os.chdir(R)

import numpy as np                                            # noqa: E402
import pandas as pd                                           # noqa: E402
from scipy.integrate import solve_ivp as _solve_ivp_real      # noqa: E402
import core.coupled_ode_convergence as cco                    # noqa: E402
from core.market_prep import classify_agents, compute_generation_limit  # noqa: E402,E501
from data.xm_prices import get_b_for_real_data                # noqa: E402
from core.replicator_sellers import VEL_GRAD, BGRANDE, VEL_RD  # noqa: E402
from core.replicator_buyers import VEL_WI, VEL_GPC             # noqa: E402


def clave(x):
    t = pd.Timestamp(x)
    return (t.tz_localize(None) if t.tzinfo is not None else t).strftime(
        "%Y-%m-%d %H:%M")


_CACHE = {}


def carga(caso):
    if caso in _CACHE:
        return _CACHE[caso]
    from paso_a_paso import carga as _carga
    import data.xm_data_loader as xdl
    if caso == "E0":
        dat = _carga("m1", factor_generacion=1.0)
    elif caso == "E4":
        dat = _carga("m1", factor_generacion=7.0)
    elif caso == "E5":
        # Los dos casos de la matriz que esta tarea anade al cargador de la
        # sonda (CASOS_MATRIZ de run_servidor.sh). E5 es E4 con el factor de la
        # generacion en 10, y M-B pide diez de sus horas.
        dat = _carga("m1", factor_generacion=10.0)
    elif caso == "CV2":
        # CV2 es el componente de comercializar por dos (--factor-cv 2): se
        # descuenta el doble sobre lo permutado, de modo que el piso de quien
        # esta en permuta BAJA y la banda se ensancha. M-C pide sus 37 horas
        # del regimen «la suma no cabe», mas de la mitad de esa muestra.
        dat = _carga("m1", factor_generacion=1.0, factor_cv=2.0)
    elif caso == "K1":
        orig = xdl.MTEDataLoader.load

        def load2(self, *a, **k):
            D, G, idx = orig(self, *a, **k)
            return np.asarray(D, dtype=float) * 2.0, G, idx
        xdl.MTEDataLoader.load = load2
        try:
            dat = _carga("m1", factor_generacion=1.0)
        finally:
            xdl.MTEDataLoader.load = orig
    else:
        raise ValueError(caso)
    mapa = {clave(x): k for k, x in enumerate(dat["idx"])}
    _CACHE[caso] = (dat, mapa)
    return dat, mapa


def entradas(dat, K):
    D, G = dat["D"], dat["G"]
    N = D.shape[0]
    a = np.zeros(N)
    c = np.zeros(N)
    b = get_b_for_real_data(N, dat["nombres"])
    g = compute_generation_limit(G[:, K], a, b, c, dat["techo"][:, K])
    _, s, bb = classify_agents(g, D[:, K])
    s, bb = list(s), list(bb)
    nom = list(dat["nombres"])
    return dict(s=s, bb=bb, vend=[nom[j] for j in s], comp=[nom[i] for i in bb],
                gn=np.array([g[j] - D[j, K] for j in s], dtype=float),
                dn=np.array([D[i, K] - g[i] for i in bb], dtype=float),
                a=a[s], b=np.asarray(b, dtype=float)[s],
                gk=np.asarray(g, dtype=float)[bb],
                techo=np.asarray(dat["techo"][bb, K], dtype=float),
                piso_j=np.asarray(dat["piso"][s, K], dtype=float),
                piso=float(np.min(dat["piso"][s, K])),
                fecha=str(dat["idx"][K]))


def hora_de(caso, fecha):
    dat, mapa = carga(caso)
    return entradas(dat, mapa[fecha])


# ------------------------------------------------------------------ motor
def captura_motor(e, peso="barrera", comp="aggregate", arranque="factible",
                  **opciones):
    """El lado derecho REAL del motor para esta hora, y su estado inicial.

    Reemplaza `solve_ivp` por uno que se queda con la funcion y con y0 y no
    integra nada. `opciones` se pasa tal cual a `solve_coupled_for_hour`: es
    por donde entran las opciones que el motor gano DESPUES de esta sonda
    (`mu_entropia` y `nivel`, D49 y D50), para poder comparar tambien esas
    ramas. Sin `opciones`, lo capturado son los defectos del motor.
    """
    cap = {}

    def falso(fun, t_span, y0, **kw):
        cap["fun"], cap["y0"] = fun, np.array(y0, dtype=float)
        return _solve_ivp_real(fun, (0.0, 1e-12), y0, method="LSODA",
                               rtol=1e-6, atol=1e-6)
    I, J = len(e["dn"]), len(e["gn"])
    cco.solve_ivp = falso
    try:
        cco.solve_coupled_for_hour(
            G_net_j=e["gn"], D_net_i=e["dn"], a_j=e["a"], b_j=e["b"],
            lam_j=np.full(J, 100.0), theta_j=np.full(J, 0.5), G_klim_i=e["gk"],
            lam_i=np.full(I, 100.0), theta_i=np.full(I, 0.5),
            etha_i=np.full(I, 0.1), pi_gs=e["techo"], pi_gb=e["piso"],
            tau_sellers=0.001, tau_buyers=0.01, t_span=(0.0, 1e-12),
            n_points=2, rtol=1e-6, atol=1e-6, buyer_competition=comp,
            peso_virtual=peso, arranque=arranque, **opciones)
    finally:
        cco.solve_ivp = _solve_ivp_real
    if "fun" not in cap:
        # La hora sin mercado vuelve antes de integrar (tambien «sin_ganancia»
        # con el piso marginal): no hay lado derecho que capturar.
        raise ValueError("el motor no integro esta hora (sin mercado): no hay "
                         "lado derecho que comparar")
    return cap["fun"], cap["y0"]


# ------------------------------------------------------------------ variante
def construye(e, peso="barrera", comp="aggregate", arranque="factible",
              eps_v=0.0,          # V2: peso del virtual = barrera + eps_v  (o eps_v solo con peso="cte")
              mu_ent=0.0,         # V3a: exploracion entropica del vendedor
              mu_mut=0.0,         # V3b: mutacion del vendedor hacia el reparto proporcional al lado corto
              mu_pi=0.0,          # V3c: regularizacion cuadratica del precio del comprador
              tau_f=0.0,          # V3d: filtro de primer orden sobre la aptitud del comprador
              rho_def=0.0,        # V4b: termino de deficit sin cubrir en la aptitud del comprador
              b_vend=None,        # V4a: costo del vendedor (ec. 16), p. ej. el piso
              precios0=None,      # arranque de precios: None = el del motor; "medio"; array (I+1)
              escala_c=0.08, escala_v=10.0,
              k_lento=1.0):       # aceleracion numerica: bloque de compradores y replicador del vendedor por k (mismo reposo)
    """Copia del lado derecho de core/coupled_ode_convergence.py (_rhs) con
    ganchos. Con los valores por defecto coincide con el motor."""
    G_net_j = np.asarray(e["gn"], float)
    D_net_i = np.asarray(e["dn"], float)
    a_j = np.asarray(e["a"], float)
    b_j = np.asarray(e["b"] if b_vend is None else np.broadcast_to(
        np.asarray(b_vend, float), (len(G_net_j),)), float)
    etha_i = np.full(len(D_net_i), 0.1)
    pi_gb = float(e["piso"])
    J, I = len(G_net_j), len(D_net_i)
    simplex = min(G_net_j.sum(), D_net_i.sum())
    gs_i = np.asarray(e["techo"], float).copy()
    pi_gs_all = np.append(gs_i, gs_i.max())
    n_pi_all = I + 1
    i_gam = n_pi_all
    i_y = i_gam + J
    i_P = i_y + J
    i_lam = i_P + J * I
    i_bet = i_lam + J
    i_lamf = i_bet + I
    i_betf = i_lamf + J
    n_base = i_betf + I
    n_tot = n_base + (I + 1 if tau_f > 0 else 0)

    simple = float(np.sum(gs_i))
    ci = simple / n_pi_all
    ci_i = np.where((pi_gb < ci) & (ci < gs_i), ci,
                    pi_gb + (gs_i - pi_gb) * I / n_pi_all)
    ci_v = (ci if pi_gb < ci < gs_i.max()
            else pi_gb + (gs_i.max() - pi_gb) * I / n_pi_all)
    pi0 = np.append(ci_i, ci_v)
    if isinstance(precios0, str) and precios0 == "medio":
        pi0 = np.append(0.5 * (gs_i + pi_gb), 0.5 * (gs_i.max() + pi_gb))
    elif isinstance(precios0, str) and precios0 == "alto":   # 90 % de la banda
        pi0 = np.append(pi_gb + 0.9 * (gs_i - pi_gb), pi_gb + 0.9 * (gs_i.max() - pi_gb))
    elif isinstance(precios0, str) and precios0 == "bajo":   # 10 % de la banda
        pi0 = np.append(pi_gb + 0.1 * (gs_i - pi_gb), pi_gb + 0.1 * (gs_i.max() - pi_gb))
    elif precios0 is not None and not isinstance(precios0, str):
        pi0 = np.asarray(precios0, float)
    P0 = cco._arranque_P0(G_net_j, D_net_i, arranque)
    X0 = np.concatenate([pi0, 0.1 * np.ones(J), np.ones(J), P0.ravel(),
                         0.1 * np.ones(J), 0.1 * np.ones(I), np.zeros(J), np.zeros(I)])
    if tau_f > 0:
        X0 = np.concatenate([X0, np.zeros(I + 1)])
    etha_s = float(np.mean(etha_i))
    matriz = np.ones((I, I)) - np.eye(I)
    etha_fila = matriz.T @ etha_i
    # objetivo de la mutacion: reparto proporcional al lado corto (el factible)
    P_obj = np.outer(G_net_j, D_net_i) / max(G_net_j.sum(), D_net_i.sum())
    P_obj = P_obj * simplex / P_obj.sum()
    cont = [0]

    def rhs(t, X):
        cont[0] += 1
        pi_all = X[:n_pi_all]
        gamma = X[i_gam:i_y]
        y_filt = X[i_y:i_P]
        P = np.maximum(X[i_P:i_lam].reshape(J, I), 1e-10)
        lam_ub = X[i_lam:i_bet]
        bet_ub = X[i_bet:i_lamf]
        lam_filt = X[i_lamf:i_betf]
        bet_filt = X[i_betf:n_base]
        pi_real = pi_all[:I]
        pi_p = pi_all[I]
        sumP_i = P.sum(axis=0)
        sumP_j = P.sum(axis=1)
        pagos = -pi_gb * sumP_i / (pi_real + 1.0)
        trestris = (y_filt[:, None] * P).sum(axis=0)
        if comp == "aggregate":
            compe = etha_s * sumP_i
        elif comp == "matlab":
            compe = etha_fila * sumP_i
        else:
            compe = etha_i * (matriz @ (pi_real * sumP_i))
        dwi_real = pagos - compe + trestris
        if rho_def:
            dwi_real = dwi_real + rho_def * np.clip(D_net_i - sumP_i, 0, None) / D_net_i
        dwi_all = np.append(dwi_real, simple - pi_p)
        if tau_f > 0:
            fit = X[n_base:]          # aptitud filtrada
        else:
            fit = dwi_all
        pi_hat = (pi_gs_all - pi_all) * (-pi_gb + pi_all)
        if peso == "precio":
            pi_hat = np.concatenate((pi_hat[:I], pi_all[I:I + 1]))
        elif peso == "cte":
            pi_hat = np.concatenate((pi_hat[:I], [eps_v]))
        elif eps_v:
            pi_hat = pi_hat.copy()
            pi_hat[I] = pi_hat[I] + eps_v
        pi_hat = np.clip(pi_hat, 1e-12, None)
        if mu_pi:
            # aptitud regularizada: f_k - mu_pi * pi_k (solo compradores reales)
            fit = fit.copy()
            fit[:I] = fit[:I] - mu_pi * pi_real
        sum_ph = float(np.sum(pi_hat))
        F_bar_b = float(np.dot(pi_hat, fit)) / sum_ph if sum_ph > 1e-14 else 0.0
        d_pi_all = pi_hat * VEL_WI * (fit - F_bar_b)
        at_low = (pi_all[:I] <= pi_gb + 1e-9) & (d_pi_all[:I] < 0)
        at_high = (pi_all[:I] >= gs_i - 1e-9) & (d_pi_all[:I] > 0)
        d_pi_all[:I] = np.where(at_low | at_high, 0.0, d_pi_all[:I])

        re = (P * pi_real[None, :]).sum(axis=1)
        Hj = a_j * sumP_j ** 2 + b_j * sumP_j
        raw_gamma = VEL_GPC * gamma * (Hj - re) + 1000.0
        d_gamma = raw_gamma
        d_y = (raw_gamma - y_filt) / 0.01

        Hm = 2.0 * a_j * sumP_j + b_j
        F = (pi_real[None, :] - Hm[:, None] - lam_filt[:, None]
             - bet_filt[None, :] + BGRANDE)
        F_bar_s = float(np.sum(P * F)) / simplex
        dP = P * VEL_RD * (F - F_bar_s)
        Glam = VEL_GRAD * lam_ub * (sumP_j - G_net_j) + 1000.0
        Gbet = VEL_GRAD * bet_ub * (sumP_i - D_net_i) + 1000.0
        d_lamf = (Glam - lam_filt) / 0.001
        d_betf = (Gbet - bet_filt) / 0.001
        dP_eff = escala_v * dP.ravel()
        if mu_ent:
            lnP = np.log(P)
            m = float(np.sum(P * lnP)) / float(np.sum(P))
            dP_eff = dP_eff - mu_ent * (P * (lnP - m)).ravel()
        if mu_mut:
            # replicador-mutador que conserva la suma: hacia P_obj escalado a la suma actual
            dP_eff = dP_eff + mu_mut * (P_obj * (P.sum() / simplex) - P).ravel()
        if k_lento != 1.0:
            dP_eff = k_lento * dP_eff
        kc = k_lento * escala_c
        out = [kc * d_pi_all, kc * d_gamma, kc * d_y, dP_eff,
               escala_v * Glam, escala_v * Gbet, escala_v * d_lamf, escala_v * d_betf]
        if tau_f > 0:
            out.append((dwi_all - X[n_base:]) / tau_f)
        return np.concatenate(out)

    rhs.cont = cont
    ix = dict(pi=slice(0, n_pi_all), P=slice(i_P, i_lam), I=I, J=J, n_base=n_base)
    return rhs, X0, ix


# ------------------------------------------------------------------ integracion
class _Tope(Exception):
    pass


def integra_tramos(rhs, X0, cortes, tope_s=300.0, method="LSODA"):
    t_ini = time.perf_counter()
    nf = [0]

    def f(t, Y):
        nf[0] += 1
        if nf[0] % 2000 == 0 and time.perf_counter() - t_ini > tope_s:
            raise _Tope()
        return rhs(t, Y)
    X = np.array(X0, float)
    out = [(cortes[0], X.copy(), 0, 0.0)]
    msg = "ok"
    for ta, tb in zip(cortes[:-1], cortes[1:]):
        try:
            sol = _solve_ivp_real(f, (ta, tb), X, method=method, rtol=1e-6, atol=1e-6)
        except _Tope:
            msg = f"tope {tope_s:.0f} s en [{ta}; {tb}]"
            break
        except Exception as exc:                       # noqa: BLE001
            msg = f"excepcion {type(exc).__name__}: {exc} en [{ta}; {tb}]"
            break
        if not sol.success:
            msg = f"sin exito en [{ta}; {tb}]: {sol.message}"
            break
        if not np.all(np.isfinite(sol.y[:, -1])):
            msg = f"no finito en [{ta}; {tb}]"
            break
        X = sol.y[:, -1].copy()
        out.append((tb, X.copy(), nf[0], time.perf_counter() - t_ini))
    return out, msg


def resumen(e, X):
    I, J = len(e["dn"]), len(e["gn"])
    pi = X[:I + 1]
    P = np.clip(X[I + 1 + 2 * J:I + 1 + 2 * J + J * I].reshape(J, I), 0, None)
    p = np.clip(pi[:I], e["piso"], e["techo"])
    q = P.sum(axis=0)
    E = q.sum()
    S = float(np.sum((e["techo"][None, :] - p[None, :]) * P))
    SR = float(np.sum((p[None, :] - e["piso_j"][:, None]) * P))
    return dict(p=p, pv=float(pi[I]), q=q, P=P, E=E,
                parte=SR / (S + SR) if (S + SR) > 0 else np.nan,
                ppond=float((p * q).sum() / E) if E > 0 else np.nan,
                suma=float(p.sum()), S=S, SR=SR)


def llenado(D, E):
    """Llenado por niveles: min(D_i, L) con suma E."""
    D = np.asarray(D, float)
    if E >= D.sum():
        return D.copy(), np.inf
    orden = np.sort(D)
    resto, n = E, len(D)
    for k, d in enumerate(orden):
        L = resto / (n - k)
        if d >= L:
            return np.minimum(D, L), L
        resto -= d
    return D.copy(), orden[-1]


def fmt(v, nd=4):
    return "[" + " ".join(f"{x:.{nd}f}" for x in np.atleast_1d(v)) + "]"


def informe(e, out, msg, etiqueta, cada=1, ref=None):
    print(f"--- {etiqueta} [{msg}]", flush=True)
    for k, (t, X, nf, s) in enumerate(out):
        if k % cada and k != len(out) - 1:
            continue
        r = resumen(e, X)
        extra = ""
        if ref is not None:
            extra = f" |q-ref|={np.max(np.abs(r['q'] - ref)):.2e}"
        print(f"  t={t:<8g} p={fmt(r['p'], 2)} pv={r['pv']:.2f} q={fmt(r['q'])} "
              f"ppond={r['ppond']:.2f} suma={r['suma']:.3f} parteV={r['parte']:.4f}"
              f"{extra} nfev={nf} {s:.1f}s", flush=True)
    return resumen(e, out[-1][1])


# ------------------------------------------------------------------ caso de Chacon
def caso_chacon(hora="22"):
    """Caso publicado (Tablas II y IV) tras la clasificacion de JoinFinal.m,
    con los literales de `caso_publicado_chacon.py` (que en el borrador de la
    sonda estaban en `scratchpad/revision_chacon/literal.py`)."""
    import caso_publicado_chacon as lit
    base = lit.CASO22 if hora == "22" else lit.CASO14
    c = lit.prepara(base["Glim"], base["Dopt"])
    I = len(c["Di"])
    return dict(s=list(c["vendedores"]), bb=list(c["compradores"]),
                vend=[f"ag{k+1}" for k in c["vendedores"]], comp=[f"ag{k+1}" for k in c["compradores"]],
                gn=c["Gj"].astype(float), dn=c["Di"].astype(float), a=c["a"].astype(float),
                b=c["b"].astype(float), gk=np.zeros(I), techo=np.full(I, 1250.0),
                piso_j=np.full(len(c["Gj"]), 114.0), piso=114.0, fecha=f"Chacon {hora}:00")


_hora_de_real = hora_de


def hora_de(caso, fecha):          # noqa: F811
    if caso == "CHACON":
        return caso_chacon(fecha)
    if caso == "SINTETICA":
        return caso_pisos_distintos()
    return _hora_de_real(caso, fecha)


# ------------------------------------------------- comprobacion contra el motor
def bloques(I, J, n_tot=None):
    """Los tramos del estado, con su nombre, para decir DONDE difiere."""
    n_pi = I + 1
    i_gam = n_pi
    i_y = i_gam + J
    i_P = i_y + J
    i_lam = i_P + J * I
    i_bet = i_lam + J
    i_lamf = i_bet + I
    i_betf = i_lamf + J
    n_base = i_betf + I
    tramos = [("precios", slice(0, n_pi)), ("gamma", slice(i_gam, i_y)),
              ("filtro_gamma", slice(i_y, i_P)), ("P", slice(i_P, i_lam)),
              ("lam", slice(i_lam, i_bet)), ("bet", slice(i_bet, i_lamf)),
              ("filtro_lam", slice(i_lamf, i_betf)),
              ("filtro_bet", slice(i_betf, n_base))]
    if n_tot is not None and n_tot > n_base:
        tramos.append(("aptitud_filtrada", slice(n_base, n_tot)))
    return tramos


def perturba(X, tramos, rng, escala):
    """Un estado vecino de X, con perturbacion ADITIVA y escala POR BLOQUE.

    La perturbacion era multiplicativa, X·(1 + e·ruido), y eso deja en cero lo
    que vale cero: los dos filtros de los multiplicadores arrancan en cero, de
    modo que nunca se probaban, y son justo los que mandan en las horas rigidas
    (grave 1 de la revision de 4c). Ahora cada bloque se mueve con una amplitud
    de `escala` veces su mayor valor absoluto, y como minimo `escala`: un bloque
    nulo tambien se mueve.
    """
    Y = np.array(X, dtype=float, copy=True)
    for _nombre, sl in tramos:
        base = Y[sl]
        if base.size == 0:
            continue
        amp = escala * max(float(np.max(np.abs(base))), 1.0)
        Y[sl] = base + amp * rng.standard_normal(base.size)
    return Y


def estado_cargado(X0, I, J, rng):
    """X0 con los multiplicadores y sus filtros en valores de hora rigida.

    Los multiplicadores arrancan en 0,1 y sus filtros en 0; en una hora rigida
    el filtro de cada comprador vale del orden de 1 000 y su multiplicador
    crece hasta 1e4 (docstring de `tests/gate_reposo_cero_dinamica.py`). Este
    estado los pone en ese rango, para que la comprobacion ejerza tambien los
    terminos que alli dominan.
    """
    X = np.array(X0, dtype=float, copy=True)
    for nombre, sl in bloques(I, J, X0.size):
        m = sl.stop - sl.start
        if nombre in ("lam", "bet"):
            X[sl] = 1e2 * (1.0 + 99.0 * rng.random(m))
        elif nombre in ("filtro_lam", "filtro_bet"):
            X[sl] = 1e3 * (1.0 + 9.0 * rng.random(m))
    return X


def piso_marginal(e) -> float:
    """El piso del vendedor marginal de la hora (D63), el mismo p* que el motor
    toma del nucleo con `piso_juego="marginal"` (`despacho_competitivo` con la
    regla de produccion, "piso")."""
    from core.reposo_mercado import despacho_competitivo
    desp = despacho_competitivo(np.asarray(e["gn"], float),
                                np.asarray(e["dn"], float),
                                np.asarray(e["techo"], float),
                                np.asarray(e["piso_j"], float), "piso",
                                b=np.asarray(e["b"], float))
    if desp.causa:
        raise ValueError(f"la hora no tiene mercado ({desp.causa!r}): no hay "
                         f"piso marginal que comparar")
    return float(desp.piso)


def comprueba_contra_el_motor(e, n=20, semilla=1, escala=0.05,
                              opciones_motor=None, e_arnes=None, **variante):
    """El lado derecho de `construye` frente al que el motor evalua, al bit.

    Con `variante` vacia (k = 1 y las opciones apagadas) el resultado tiene que
    ser identico: misma X0 y misma salida en cada estado probado. Si no lo es,
    el diccionario dice en que bloques del estado difiere y cuanto, en absoluto
    y en relativo. `opciones_motor` son las opciones que se le pasan al motor
    para capturar la MISMA rama (por ejemplo `dict(mu_entropia=1.0)` frente a
    `mu_ent=1.0` en la variante). `e_arnes` es la hora con que se construye el
    arnes cuando no es la misma que recibe el motor: con el piso marginal, el
    motor recibe el piso minimo y calcula p* el mismo, y el arnes recibe p*.

    LOS ESTADOS PROBADOS: `n` vecinos del arranque y `n` vecinos de un estado
    con los multiplicadores y sus filtros cargados (`estado_cargado`), mas ese
    estado tal cual, siempre con perturbacion aditiva por bloque (`perturba`).
    `bloques_ejercidos` dice que bloques tuvieron valores no nulos en algun
    estado probado: tienen que estar los ocho.

    Devuelve dict(identico, dif_X0, dif_abs, dif_rel, bloques,
    bloques_ejercidos, n, evaluaciones).
    """
    op = dict(opciones_motor or {})
    comunes = {k: variante[k] for k in ("peso", "comp", "arranque")
               if k in variante}
    motor = dict(comunes)
    motor.update(op)
    fm, X0m = captura_motor(e, **motor)
    fv, X0v, ix = construye(e if e_arnes is None else e_arnes, **variante)
    I, J = ix["I"], ix["J"]
    tramos = bloques(I, J, X0v.size)
    rng = np.random.default_rng(semilla)
    dif_X0 = float(np.max(np.abs(X0m - X0v))) if X0m.size == X0v.size else np.inf
    dif_abs = 0.0
    dif_rel = 0.0
    donde = {}
    ejercidos = set()
    identico = (X0m.size == X0v.size) and bool(np.array_equal(X0m, X0v))
    cargado = estado_cargado(X0m, I, J, rng)
    estados = ([perturba(X0m, tramos, rng, escala) for _ in range(n)]
               + [cargado]
               + [perturba(cargado, tramos, rng, escala) for _ in range(n)])
    for X in estados:
        for nombre, sl in tramos:
            if np.any(X[sl] != 0.0):
                ejercidos.add(nombre)
        a = np.asarray(fm(0.0, X), float)
        b = np.asarray(fv(0.0, X), float)
        if a.size != b.size:
            return dict(identico=False, dif_X0=dif_X0, dif_abs=np.inf,
                        dif_rel=np.inf, bloques={"tamano": float(a.size - b.size)},
                        bloques_ejercidos=sorted(ejercidos), n=len(estados),
                        evaluaciones=int(fv.cont[0]))
        if not np.array_equal(a, b):
            identico = False
        d = np.abs(a - b)
        dif_abs = max(dif_abs, float(np.max(d)))
        dif_rel = max(dif_rel, float(np.max(d) / (np.max(np.abs(a)) + 1e-300)))
        for nombre, sl in tramos:
            peor = float(np.max(d[sl])) if d[sl].size else 0.0
            if peor > 0.0:
                donde[nombre] = max(donde.get(nombre, 0.0), peor)
    return dict(identico=identico, dif_X0=dif_X0, dif_abs=dif_abs,
                dif_rel=dif_rel, bloques=donde,
                bloques_ejercidos=sorted(ejercidos), n=len(estados),
                evaluaciones=int(fv.cont[0]))


def ramas(e):
    """Las comparaciones que hacen creible la validacion, para una hora.

    Cada una es (rotulo, kwargs de `comprueba_contra_el_motor`). Las cuatro
    primeras son los defectos (peso del jugador virtual por arranque de la
    oferta); despues, las ramas que sostienen las mediciones: el termino
    entropico (D49, todas), el costo del vendedor por su alternativa (D68, M-B),
    el piso del vendedor marginal (D63 y D68, el ancla de M-A), las tres juntas
    y las dos configuraciones de M-G (competencia `matlab`, oferta a partes
    iguales y mu = 1, con los dos pesos del jugador virtual).
    """
    fuera = []
    for peso in ("barrera", "precio"):
        for arr in ("factible", "iguales"):
            fuera.append((f"{peso:8s} {arr:8s}", dict(peso=peso, arranque=arr)))
    piso_j = np.asarray(e["piso_j"], float)
    fuera.append(("entropico mu=1   ", dict(
        mu_ent=1.0, opciones_motor=dict(mu_entropia=1.0))))
    fuera.append(("costo alternativa", dict(
        b_vend=piso_j,
        opciones_motor=dict(costo_vendedor="alternativa", piso_j=piso_j))))
    p_m = piso_marginal(e)
    fuera.append(("piso marginal    ", dict(
        e_arnes=dict(e, piso=p_m),
        opciones_motor=dict(piso_juego="marginal", piso_j=piso_j))))
    fuera.append(("las tres juntas  ", dict(
        e_arnes=dict(e, piso=p_m), b_vend=piso_j, mu_ent=1.0,
        opciones_motor=dict(mu_entropia=1.0, costo_vendedor="alternativa",
                            piso_juego="marginal", piso_j=piso_j))))
    # Las dos configuraciones de M-G: el codigo de la autora (competencia
    # `matlab`, oferta a partes iguales) con la exploracion entropica, con los
    # dos pesos del jugador virtual.
    for peso in ("barrera", "precio"):
        fuera.append((f"autora {peso:8s}", dict(
            peso=peso, comp="matlab", arranque="iguales", mu_ent=1.0,
            opciones_motor=dict(mu_entropia=1.0))))
    return fuera


def caso_pisos_distintos():
    """Una hora sintetica con dos vendedores de pisos distintos (600 y 690
    (COP/kWh)) y vendedores cortos, de modo que despachan los dos y el piso
    marginal (690) NO es el minimo (600). En las horas del caso publicado todos
    los pisos son 114, y alli la rama del piso marginal coincide con la del
    minimo por construccion: esta hora es la que la ejerce de verdad."""
    return dict(s=[0, 1], bb=[0, 1, 2], vend=["v1", "v2"],
                comp=["c1", "c2", "c3"],
                gn=np.array([1.0, 0.8]), dn=np.array([0.7, 0.9, 0.6]),
                a=np.zeros(2), b=np.array([150.0, 200.0]), gk=np.zeros(3),
                techo=np.array([730.0, 745.0, 800.0]),
                piso_j=np.array([600.0, 690.0]), piso=600.0,
                fecha="sintetica, pisos 600 y 690")


def _main(argv):
    """Dice en voz alta si el arnes se desvio del motor.

    Siempre sobre el caso publicado de Chacon (22:00 y 14:00) y sobre la hora
    sintetica de pisos distintos, que no necesitan datos reales; con
    argumentos, ademas sobre esas horas reales, en pares de caso y fecha (por
    ejemplo: E0 "2025-05-09 13:00"). En cada hora, las diez ramas de `ramas`.
    Sale con 1 si alguna difiere o no ejerce los ocho bloques del estado.
    """
    horas = [("CHACON", "22"), ("CHACON", "14"), ("SINTETICA", "pisos")]
    if argv:
        if len(argv) % 2:
            print("  los argumentos van en pares de caso y fecha, por "
                  "ejemplo: E0 \"2025-05-09 13:00\"", flush=True)
            return 2
        for k in range(0, len(argv), 2):
            horas.append((argv[k], argv[k + 1]))
    print("Lado derecho del arnes frente al del motor, al bit", flush=True)
    print("  (perturbacion aditiva por bloque, desde el arranque y desde un "
          "estado con los filtros cargados)", flush=True)
    malas = 0
    todos = {n for n, _ in bloques(1, 1)}
    for caso, fecha in horas:
        e = hora_de(caso, fecha)
        try:
            lista = ramas(e)
        except ValueError as exc:
            # Una hora sin mercado no tiene piso marginal: se dice y se sigue
            # con las demas, pero cuenta como comprobacion que falta.
            print(f"  {caso} {fecha}: NO SE PUEDE COMPROBAR: {exc}", flush=True)
            malas += 1
            continue
        for rotulo, kw in lista:
            r = comprueba_contra_el_motor(e, **kw)
            faltan = sorted(todos - set(r["bloques_ejercidos"]))
            ok = r["identico"] and not faltan
            if not ok:
                malas += 1
            print(f"  {caso} {fecha} {rotulo} "
                  f"{'IDENTICO' if r['identico'] else 'DIFIERE'} "
                  f"|X0|={r['dif_X0']:.1e} |dif|={r['dif_abs']:.1e} "
                  f"rel={r['dif_rel']:.1e} estados={r['n']}"
                  f"{' SIN EJERCER ' + str(faltan) if faltan else ''} "
                  f"{r['bloques'] or ''}", flush=True)
    if malas:
        print(f"  EL ARNES SE DESVIO DEL MOTOR, o no se pudo comprobar, en "
              f"{malas} casos", flush=True)
        return 1
    print("  el arnes no se desvio del motor en ninguna rama", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
