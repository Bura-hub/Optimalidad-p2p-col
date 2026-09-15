"""
El piso de P en el solucionador acoplado (H-84; D40, D41, D42). 2026-09-14.

La hora 4184 de la frontera M1 con la generacion por siete explotaba segun el
ultimo decimal de la entrada: la oferta P de los vendedores al comprador 0
cruzaba el cero dentro de la dinamica del acoplado y, con P negativa, el
replicador se alimentaba a si mismo hasta desbordar. La corrida que
sobrevivia liquidaba energia inflada, porque el recorte a cero de la salida
borraba la P negativa. D40 lee P con un piso de 1e-10 dentro del lado
derecho; D41 corta la integracion al primer valor no finito del lado derecho
y devuelve una trayectoria con `success=False`, que el motor trata como
integrador sin exito (D37); D42 deja la via alternada como esta.

SIN DATOS REALES. Las entradas de la hora son literales hexadecimales
(`float.fromhex`), identicos al bit en cualquier maquina. Se sacaron una vez
con `paso_a_paso.carga("m1", factor_generacion=7)` y la receta de los
guiones de diagnostico de H-84, y su huella SHA-256 (G_net, D_net, a, b,
G_klim, techo y piso, en float64) es la que dio la hora en la maquina de
trabajo y en el servidor.

Tres grupos de pruebas:
  - rapida, la que decide: con un horizonte corto que cubre el evento de
    t = 1,06e-4, la base y cuatro perturbaciones de un ulp terminan todas, sin
    valores no finitos y con el mismo precio. Sin el piso no pasa.
  - lenta (unos 3 a 4 (min)): la base al horizonte de produccion llega al
    equilibrio medido en H-84, y ningun comprador recibe mas que su deficit.
  - D41: un lado derecho no finito en la evaluacion k corta en esa misma
    evaluacion, y la hora sigue el camino de D37 por `_run_hour_worker`.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest
import scipy.integrate

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import core.coupled_ode_convergence as ccc  # noqa: E402
from core.coupled_ode_convergence import solve_coupled_for_hour  # noqa: E402
from core.ems_p2p import SolverParams, _run_hour_worker  # noqa: E402
from core.market_prep import classify_agents, compute_generation_limit  # noqa: E402
from gate_c165_desglose_horario import _caso  # noqa: E402


# ─── la hora 4184 con la generacion por siete, al bit ──────────────────────


def _hex(v):
    return np.array([float.fromhex(x) for x in v], dtype=float)


# Excedente neto de cada vendedor y deficit neto de cada comprador (kWh).
GN = _hex(["0x1.4c82ef7abe53dp+4", "0x1.44a6921735ee0p+1"])
DN = _hex(["0x1.f3078263ab500p-4", "0x1.346a7ef9db22ep+3",
           "0x1.3d1807a557849p+5"])
# Coeficientes de costo de los vendedores y generacion limite de los
# compradores (kWh).
A = _hex(["0x0.0p+0", "0x0.0p+0"])
B = _hex(["0x1.e224924924924p+7", "0x1.c200000000000p+7"])
GK = _hex(["0x1.37c82869f32a8p+4", "0x1.1600aec33e1f6p+4",
           "0x1.1c43728d2ceb6p+4"])
# Techo de cada comprador y piso de la hora (COP/kWh).
TECHO = _hex(["0x1.639141205bc02p+9"] * 3)
PISO = float.fromhex("0x1.fc28f5c28f5c3p+7")
HUELLA = "678c7a72873ca47b"

T_CORTO = 0.002        # cubre el evento de H-84, t = 1,06e-4
T_PRODUCCION = 0.05


def _huella(gn, dn, a, b, gk, techo, piso):
    m = hashlib.sha256()
    for v in (gn, dn, a, b, gk, techo):
        m.update(np.ascontiguousarray(v, dtype=np.float64).tobytes())
    m.update(np.float64(piso).tobytes())
    return m.hexdigest()[:16]


def _resuelve(gn=GN, dn=DN, t_fin=T_PRODUCCION, **kw):
    """La receta de H-84: los parametros de produccion del acoplado. La
    tolerancia absoluta queda en su defecto de 1e-6 (H-51)."""
    J, I = len(gn), len(dn)
    return solve_coupled_for_hour(
        G_net_j=gn, D_net_i=dn, a_j=A, b_j=B,
        lam_j=np.full(J, 100.0), theta_j=np.full(J, 0.5),
        G_klim_i=GK, lam_i=np.full(I, 100.0), theta_i=np.full(I, 0.5),
        etha_i=np.full(I, 0.1), pi_gs=TECHO, pi_gb=PISO,
        tau_sellers=0.001, tau_buyers=0.01, t_span=(0.0, t_fin),
        n_points=150, rtol=1e-6, buyer_competition="aggregate", **kw)


def _variantes():
    """La base y las cuatro perturbaciones de un ulp: G_net[0] y D_net[0],
    arriba y abajo."""
    out = [("base", GN, DN)]
    for clave, sentido, nombre in (("gn", np.inf, "G_net[0]+1ulp"),
                                   ("gn", -np.inf, "G_net[0]-1ulp"),
                                   ("dn", np.inf, "D_net[0]+1ulp"),
                                   ("dn", -np.inf, "D_net[0]-1ulp")):
        gn, dn = GN.copy(), DN.copy()
        v = gn if clave == "gn" else dn
        v[0] = np.nextafter(v[0], sentido)
        out.append((nombre, gn, dn))
    return out


NOMBRES = [n for n, _, _ in _variantes()]


def _finita(tr):
    return all(np.all(np.isfinite(np.asarray(getattr(tr, c), dtype=float)))
               for c in ("pi_t", "P_t", "pi_star", "P_star", "W_t"))


def test_los_literales_son_la_hora_4184_al_bit():
    assert _huella(GN, DN, A, B, GK, TECHO, PISO) == HUELLA
    for _, gn, dn in _variantes()[1:]:
        assert _huella(gn, dn, A, B, GK, TECHO, PISO) != HUELLA


# ─── rapida: un ulp ya no decide el resultado ──────────────────────────────


@pytest.fixture(scope="module")
def cortas():
    return {nombre: _resuelve(gn, dn, t_fin=T_CORTO)
            for nombre, gn, dn in _variantes()}


@pytest.mark.parametrize("nombre", NOMBRES)
def test_rapida_cada_variante_termina_sin_valores_no_finitos(cortas, nombre):
    tr = cortas[nombre]
    assert tr.success, f"{nombre}: {tr.message}"
    assert _finita(tr), f"{nombre}: valores no finitos en la trayectoria"
    assert tr.t[-1] == T_CORTO, f"{nombre}: no llego al horizonte"


# Tolerancia relativa del precio final entre la base y las perturbaciones de
# un ulp: 1e-6, la tolerancia relativa del integrador. Una perturbacion de un
# ulp en un sistema bien condicionado mueve el resultado del orden de lo que
# el integrador deja pasar, no mas; medido en la maquina de trabajo, la mayor
# diferencia es de 3,0e-9 (unas trescientas veces por debajo), sobre precios
# del orden de 500 (COP/kWh). Lo que esta prueba separa es otra cosa: sin el
# piso, las variantes que explotan no llegan al horizonte o terminan en NaN.
TOL_PRECIO_REL = 1e-6


def test_rapida_las_cinco_terminan_con_el_mismo_precio(cortas):
    # Una perturbacion de un ulp en un sistema bien condicionado mueve el
    # resultado lo que mueve la tolerancia del integrador, no mas.
    base = np.asarray(cortas["base"].pi_star, dtype=float)
    peor = 0.0
    for nombre in NOMBRES[1:]:
        pi = np.asarray(cortas[nombre].pi_star, dtype=float)
        rel = float(np.max(np.abs(pi - base) / np.abs(base)))
        peor = max(peor, rel)
        print(f"    {nombre:14s} precio final {np.array2string(pi, precision=6)}"
              f"   dif. relativa {rel:.3e}")
    print(f"    mayor diferencia relativa frente a la base: {peor:.3e}")
    for nombre in NOMBRES[1:]:
        np.testing.assert_allclose(cortas[nombre].pi_star, base,
                                   rtol=TOL_PRECIO_REL, atol=0.0,
                                   err_msg=nombre)


# ─── lenta: el equilibrio al horizonte de produccion ───────────────────────


def test_lenta_equilibrio_de_la_hora_4184_al_horizonte_de_produccion():
    # Unos 200 (s) en la maquina de trabajo. Las cifras son las de H-84
    # (`outputs/run_2026-09-14_experimento_proyeccion.log`): las once
    # corridas con el piso dieron este precio y este reparto.
    tr = _resuelve(t_fin=T_PRODUCCION)
    assert tr.success, tr.message
    assert _finita(tr)
    assert tr.pi_star == pytest.approx([711.134, 456.569, 254.566], abs=1e-3)
    recibe = np.asarray(tr.P_star, dtype=float).sum(axis=0)
    print(f"    precio {np.array2string(tr.pi_star, precision=4)}"
          f"   recibe {np.array2string(recibe, precision=6)} (kWh)"
          f"   deficit {np.array2string(DN, precision=6)} (kWh)"
          f"   evaluaciones {tr.nfev}")
    assert recibe == pytest.approx([0.1218, 9.638, 13.5585], abs=1e-3)
    # Sin el piso, el comprador 0 recibia 0,2319 frente a su deficit de
    # 0,1218 (kWh): la P negativa que el recorte de la salida borraba.
    assert np.all(recibe <= DN + 1e-6), (recibe, DN)


# ─── D41: el corte al primer valor no finito ───────────────────────────────


def _envenena(monkeypatch, k, como="salida", en_resolucion=1):
    """Sustituye `solve_ivp` en el modulo del acoplado por el de scipy con
    una envoltura que, en la resolucion numero `en_resolucion` y en su
    evaluacion numero `k`, le pasa al lado derecho VERDADERO un estado que lo
    hace no finito:

      como="estado": un NaN en el estado;
      como="salida": un estado FINITO con el precio del comprador 0 en -1,
                     que anula el denominador de sus pagos (pi + 1), de
                     modo que es la salida la que sale no finita.

    Devuelve el registro: cuantas resoluciones y cuantas evaluaciones hizo
    cada una."""
    real = scipy.integrate.solve_ivp
    reg = {"resoluciones": 0, "evaluaciones": []}

    def envuelta(fun, t_span, y0, **kw):
        reg["resoluciones"] += 1
        esta = reg["resoluciones"]
        reg["evaluaciones"].append(0)

        def f(t, X):
            reg["evaluaciones"][-1] += 1
            if esta == en_resolucion and reg["evaluaciones"][-1] == k:
                X = np.array(X, dtype=float, copy=True)
                X[0] = np.nan if como == "estado" else -1.0
            return fun(t, X)

        return real(f, t_span, y0, **kw)

    monkeypatch.setattr(ccc, "solve_ivp", envuelta)
    return reg


@pytest.mark.parametrize("como", ["estado", "salida"])
@pytest.mark.parametrize("k", [1, 7, 50])
def test_d41_corta_en_la_evaluacion_k_con_formas_coherentes(monkeypatch, k,
                                                             como):
    reg = _envenena(monkeypatch, k, como)
    with np.errstate(all="ignore"):
        tr = _resuelve(t_fin=T_CORTO, devuelve_multiplicadores=True)
    # Vuelve en seguida: ni una evaluacion despues de la k.
    assert reg["evaluaciones"] == [k]
    assert tr.success is False
    assert tr.message.startswith("lado derecho no finito en t=")
    assert f"{como} de la evaluacion {k}" in tr.message
    assert tr.nfev == k
    assert tr.njev == 0
    # Las formas de siempre, con un solo punto: el inicial.
    J, I = len(GN), len(DN)
    assert tr.t.shape == (1,) and tr.t[0] == 0.0
    assert tr.pi_t.shape == (I, 1)
    assert tr.P_t.shape == (J, I, 1)
    for c in ("Wj_t", "Wi_t", "W_t"):
        assert getattr(tr, c).shape == (1,)
    assert tr.pi_star.shape == (I,)
    assert tr.P_star.shape == (J, I)
    assert tr.lam_t.shape == (J, 1) and tr.lam_filt_t.shape == (J, 1)
    assert tr.bet_t.shape == (I, 1) and tr.bet_filt_t.shape == (I, 1)


def test_d41_un_corte_no_contamina_la_resolucion_siguiente(monkeypatch):
    # El corte sale del integrador por una excepcion a mitad de paso. La
    # resolucion siguiente en el mismo proceso (un trabajador del pool
    # resuelve muchas horas) tiene que dar lo mismo que antes del corte.
    antes = _resuelve(t_fin=2e-5)
    _envenena(monkeypatch, 50)
    with np.errstate(all="ignore"):
        assert not _resuelve(t_fin=T_CORTO).success
    monkeypatch.undo()
    despues = _resuelve(t_fin=2e-5)
    assert antes.success and despues.success
    assert antes.nfev == despues.nfev
    assert np.array_equal(antes.pi_t, despues.pi_t)
    assert np.array_equal(antes.P_t, despues.P_t)


# ─── D41 por el motor: el camino de D37 ────────────────────────────────────

PGS, PGB = 1250.0, 114.0
T_ACO = 0.002          # horizonte de la primera vuelta, corto para que corra


def _hora():
    """La primera hora del caso sintetico de C-165 con vendedores y
    compradores a la vez, la misma de `test_presupuesto_acoplado.py`."""
    D, G = _caso(T=24)
    N = D.shape[0]
    a = np.zeros(N); b = np.full(N, 225.0); c = np.zeros(N)
    lam = np.full(N, 100.0); theta = np.full(N, 0.5); etha = np.full(N, 0.1)
    for k in range(D.shape[1]):
        g_klim = compute_generation_limit(G[:, k], a, b, c, PGS)
        _, sids, bids = classify_agents(g_klim, D[:, k])
        if sids and bids:
            return dict(k=k, g_klim=g_klim, d_k=D[:, k].copy(),
                        g_k=G[:, k].copy(), sids=sids, bids=bids, a=a, b=b,
                        lam=lam, theta=theta, etha=etha)
    raise RuntimeError("ninguna hora del caso sintetico de C-165 tiene "
                       "vendedores y compradores a la vez")


def _args(h, horizonte_max):
    """La tupla de 29 campos de `_run_hour_worker`, via acoplada."""
    sv = SolverParams()
    return (h["k"], h["g_klim"], h["d_k"], h["g_k"], h["sids"], h["bids"],
            h["a"], h["b"], h["lam"], h["theta"], h["etha"],
            PGS, PGB, sv.tau, sv.tau_buyers, sv.t_span, sv.n_points,
            sv.stackelberg_iters, sv.stackelberg_tol, sv.stackelberg_max,
            sv.ode_method, sv.buyer_competition,
            "acoplado", T_ACO, None, False,
            1e-6, horizonte_max, None)


def test_d41_primera_vuelta_cortada_con_la_parada_apagada_deja_la_hora_sin_mercado(
        monkeypatch):
    reg = _envenena(monkeypatch, 20)
    with np.errstate(all="ignore"):
        res = _run_hour_worker(_args(_hora(), None))
    assert reg["evaluaciones"] == [20]
    assert res.P_star is None
    assert res.motivo == f"integrador sin exito al horizonte {T_ACO:g}"
    assert res.parada_acoplado == "una_vuelta"
    assert res.horizonte_usado == 0.0


def test_d41_primera_vuelta_cortada_con_la_parada_activa_deja_la_hora_sin_mercado(
        monkeypatch):
    reg = _envenena(monkeypatch, 20)
    with np.errstate(all="ignore"):
        res = _run_hour_worker(_args(_hora(), 4 * T_ACO))
    assert reg["resoluciones"] == 1 and reg["evaluaciones"] == [20]
    assert res.P_star is None
    assert res.motivo == f"integrador sin exito al horizonte {T_ACO:g}"
    assert res.parada_acoplado == "fallo_vuelta"
    assert res.horizonte_usado == 0.0


def test_d41_segunda_vuelta_cortada_conserva_la_primera(monkeypatch):
    h = _hora()
    sv = SolverParams()
    sids, bids = h["sids"], h["bids"]
    directo = solve_coupled_for_hour(
        G_net_j=np.array([h["g_klim"][j] - h["d_k"][j] for j in sids]),
        D_net_i=np.array([h["d_k"][i] - h["g_klim"][i] for i in bids]),
        a_j=h["a"][sids], b_j=h["b"][sids], lam_j=h["lam"][sids],
        theta_j=h["theta"][sids], G_klim_i=h["g_klim"][bids],
        lam_i=h["lam"][bids], theta_i=h["theta"][bids],
        etha_i=h["etha"][bids], pi_gs=PGS, pi_gb=PGB, tau_sellers=sv.tau,
        tau_buyers=sv.tau_buyers, t_span=(0.0, T_ACO),
        n_points=sv.n_points, rtol=1e-6,
        buyer_competition=sv.buyer_competition)
    assert directo.success

    reg = _envenena(monkeypatch, 20, en_resolucion=2)
    with np.errstate(all="ignore"):
        res = _run_hour_worker(_args(h, 2 * T_ACO))
    # La primera vuelta no es estacionaria y dobla; la segunda se corta en su
    # evaluacion 20 y la hora se queda con la primera, identica.
    assert reg["resoluciones"] == 2 and reg["evaluaciones"][1] == 20
    assert res.parada_acoplado == "fallo_vuelta"
    assert res.motivo == ""
    assert res.horizonte_usado == T_ACO
    assert np.array_equal(res.P_star, np.asarray(directo.P_star, dtype=float))
    assert np.array_equal(res.pi_star,
                          np.clip(np.asarray(directo.pi_star, dtype=float),
                                  PGB, PGS))
