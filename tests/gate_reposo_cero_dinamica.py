"""
Compuerta: la dinamica regularizada se QUEDA en el reposo en forma cerrada
(D48, D49, D50). 2026-09-17; rondas de arreglos 1 y 2 de la tarea 3.

QUE HACE. Integra la via acoplada (`solve_coupled_for_hour`) con la
exploracion entropica del vendedor, mu = 1 (COP/kWh), y los precios en el
presupuesto sigma (`nivel="sigma"`, el jugador virtual en su techo), DESDE el
reposo cerrado del nucleo (`resuelve_reposo` con sus defectos: presupuesto
sigma, liquidacion uniforme, despacho por merito), durante Dt = 5 unidades de
tiempo. Es la compuerta 2 de la sec. 6 de
`.superpowers/sdd/2026-09-16-sonda-equilibrio/fable-report.md`, y valida que
el reposo cerrado es un punto de reposo de la dinamica regularizada. NO es la
validacion del servidor por regimen (M-A): esa usa el arnes acelerado de la
medicion de consenso.

COMO SE CORRE. Directa, como las demas compuertas del lanzador:

    python tests/gate_reposo_cero_dinamica.py

corre pytest sobre si misma con `-k "not lenta"` (las dos horas rapidas) y
sale con su codigo: 0 si pasan, distinto de 0 si alguna falla o no se recoge
ninguna. Directa exige t = 5: con `HORIZONTE_COMPUERTA` no vacia se niega a
correr y sale con 2, porque un horizonte parcial nunca aprueba y la compuerta
saldria con 0 sin haber aprobado nada. Tambien por pytest:

    .venv/Scripts/python.exe -u -m pytest tests/gate_reposo_cero_dinamica.py \
        -k "not lenta" -s -q -p no:cacheprovider

`pytest tests/` no la recoge (`python_files = test_*.py`). LAS LENTAS NO SE
CORREN EN LOCAL, ni con tope: todo lo pesado va al servidor (regla del autor).

EL ARRANQUE. `estado_inicial` lleva la oferta por pareja P del reposo, sin el
recorte a 1e-10 (sus ceros se leen con ese piso, D40), y los precios del
reposo (`pi_reposo`, el pago segun puja); el jugador virtual arranca en su
techo (`nivel="sigma"`), de modo que la suma de precios que conserva la
dinamica es el presupuesto S del reposo. Los multiplicadores y los filtros
arrancan como siempre. Eso basta en las horas NO rigidas: en el reposo, el
reparto arranca quieto o casi (max |dP/dt| = 0 en la 853 y 3,0e-4 (kWh por
unidad de tiempo) en la 2120), y el transitorio medido no pasa de 2,2e-6 (kWh)
en la 853 ni de 3e-10 (kWh) en la 2120. En las rigidas NO: max |dP/dt| = 86,3
en la 874 y 32,7 en la 4766 (kWh por unidad de tiempo), porque sus
multiplicadores de demanda arrancan lejos de su valor; alli no se ha medido si
darlos cambia el resultado. Las cuatro cifras son de la revision de la tarea 3
y las fija `tests/test_dinamica_regularizada.py`.

LAS HORAS, con los literales y la huella de `tests/test_reposo_mercado.py`
(`_entradas`, que comprueba la huella antes de devolverlos), en numeracion de
la matriz de E0:
  - 853 (2025-05-09 13:00), todos interiores;
  - 874 (2025-05-10 10:00), topados que reciben (LENTA);
  - 2120 (2025-07-01 08:00), tres excluidos y todo a Cesmag;
  - 4766 (2025-10-19 14:00), compradores cortos, SOLO INFORMATIVA (LENTA): el
    despacho por merito frente al de la dinamica es lo que mide M-B, de modo
    que su resultado se imprime y no se afirma.

ACEPTACION, fijada de antemano (la del encargo): en TODOS los puntos de
control (cada 0,1 desde t = 0 hasta t = 5, el final incluido),
max |P_ji(t) - P_ji del reposo| <= 1e-4·E (kWh), con E el volumen de la hora,
y max |pi_i(t) - pi_i del reposo| <= 0,05 (COP/kWh); ademas, el integrador
termina con exito en t = 5. P y pi son los de la trayectoria (P recortada a
cero y pi a su banda, como la publica `CoupledTrajectory`).
rtol = atol = 1e-6 (H-51).

DOS VARIABLES DE ENTORNO, para el servidor:
  - `TOPE_COMPUERTA_S`: tope de tiempo de pared por hora, en segundos; si se
    pasa, la prueba falla en voz alta con lo que llevaba. 0 o ausente: sin
    tope.
  - `HORIZONTE_COMPUERTA`: un horizonte PARCIAL, en (0, 5] y multiplo de 0,1
    (por ejemplo 0,5, 1 o 2), para ver como crece el costo de las horas lentas
    antes de comprometer la noche. SOLO por `python -m pytest`: la ejecucion
    directa la rechaza (sale con 2). Con el, los puntos de control siguen cada
    0,1 hasta ese horizonte; una hora fuera de la aceptacion falla igual, y
    una dentro sale como SALTADA, nunca como aprobada, porque la compuerta
    exige t = 5. Un valor fuera de rango o que no es multiplo de 0,1 falla al
    importar. Ausente o vacia: 5.

COSTO medido en la maquina de trabajo (Windows, Python 3.13.7, numpy 2.4.4,
scipy 1.17.1), el 2026-09-17, antes de la regla de no correr lo pesado en
local:
  - 853: 2 159 evaluaciones (63 jacobianas), 0,3 (s);
  - 2120: 2 729 evaluaciones (86 jacobianas), 0,4 (s);
  - 874: con un tope de 270 (s) llego a t = 0,243 con 1 804 000
    evaluaciones, y alli seguia en el reposo (|dP| = 2,5e-5 (kWh), |dpi| =
    1,1e-4 (COP/kWh)); el costo por unidad de tiempo crecia (5,9e6
    evaluaciones por unidad hasta t = 0,145 y 9,7e6 despues), porque el
    multiplicador de demanda de cada topado crece sin tope, a unas 10 veces su
    filtro por unidad de tiempo, y con el la rigidez del modo rapido del tope;
  - 4766: con un tope de 480 (s) llego a t = 0,203 con 3 664 000
    evaluaciones (|dP| = 5,4e-8 (kWh), |dpi| = 0 en el ultimo estado
    evaluado). Con compradores cortos la suma de P queda clavada en la
    demanda, el filtro de cada comprador vale unos 1 000 y su multiplicador
    crece a 1e4 por unidad de tiempo: mas rigida que la 874.

ESTIMACION, CON SU RIESGO. Con esos dos cortes por hora, las evaluaciones
acumuladas crecen como t^1,44: hasta t = 5 serian unas 1,4e8 en la 874 y unas
3,7e8 en la 4766; a 60 (us) por evaluacion (la cifra del servidor de la sonda
del consenso; en la maquina de trabajo, unos 130), unas 2,5 (h) y 6 (h). Pero
eso extrapola unas 20 veces un ajuste de dos puntos. Si el crecimiento es
cuadratico, la 874 pasa de 12 (h) (7,6e8 evaluaciones) y la 4766 de 35 (h)
(2,2e9). Por eso en el servidor van primero los cortes intermedios.

EN EL SERVIDOR, con el entorno de `requirements-lock.txt` (H-84), cada orden
un proceso de un nucleo con su registro, sin canalizar la salida y con un solo
esperador con tope (`timeout`), que cubre el fallo. Pueden correr a la vez.

Etapa 1, los cortes intermedios (t = 0,5 y t = 1 de las dos horas):

    cd ~/bslopez/sistemabl
    PYTHONUNBUFFERED=1 HORIZONTE_COMPUERTA=0.5 TOPE_COMPUERTA_S=5000 \
        timeout 90m .venv/bin/python -u -m pytest \
        tests/gate_reposo_cero_dinamica.py -k "lenta and 874" -s -q -rs \
        -p no:cacheprovider \
        > outputs/run_$(date +%F)_gate_reposo_cero_874_t0.5.log 2>&1
    PYTHONUNBUFFERED=1 HORIZONTE_COMPUERTA=1 TOPE_COMPUERTA_S=10000 \
        timeout 3h .venv/bin/python -u -m pytest \
        tests/gate_reposo_cero_dinamica.py -k "lenta and 874" -s -q -rs \
        -p no:cacheprovider \
        > outputs/run_$(date +%F)_gate_reposo_cero_874_t1.log 2>&1

y las mismas dos con `-k "lenta and 4766"` y `_4766_` en el nombre del
registro. Cada registro dice las evaluaciones N y los segundos de su horizonte.
Con p = ln(N(1)/N(0,5))/ln 2, lo de t = 5 se estima en N(1)·5^p evaluaciones
y en esa cifra por los segundos por evaluacion de t = 1. Si cabe en la noche:

Etapa 2, la compuerta completa, con `TOPE_COMPUERTA_S` en unas 1,4 veces lo
estimado, justo por debajo del `timeout`, que queda en 1,5 veces: asi el tope
de la prueba llega antes y el registro dice hasta donde llego y con que costo,
y el `timeout` solo cubre el fallo (si no cabe, `HORIZONTE_COMPUERTA=2`
primero):

    PYTHONUNBUFFERED=1 TOPE_COMPUERTA_S=<1,4 veces lo estimado, en s> \
        timeout <1,5 veces lo estimado> .venv/bin/python -u -m pytest \
        tests/gate_reposo_cero_dinamica.py -k "lenta and 874" -s -q \
        -p no:cacheprovider \
        > outputs/run_$(date +%F)_gate_reposo_cero_874.log 2>&1

y la misma con la 4766.

SIN DATOS REALES: solo literales.
"""
from __future__ import annotations

import contextlib
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import solve_ivp as _solve_ivp_real

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import core.coupled_ode_convergence as ccc  # noqa: E402
from core.coupled_ode_convergence import solve_coupled_for_hour  # noqa: E402
from core.reposo_mercado import resuelve_reposo  # noqa: E402
from test_reposo_mercado import _entradas  # noqa: E402

MU = 1.0               # (COP/kWh), D49
DT = 5.0               # unidades de tiempo de la compuerta
PASO_CONTROL = 0.1     # un punto de control cada 0,1
TOL_P_REL = 1e-4       # |dP| <= 1e-4·E (kWh)
TOL_PI = 0.05          # |dpi| <= 0,05 (COP/kWh)
# Tope de tiempo de pared por hora, en segundos; 0 (defecto) sin tope. Si se
# pasa, la prueba falla en voz alta con lo que costo hasta ahi.
TOPE_S = float(os.environ.get("TOPE_COMPUERTA_S", "0") or 0)


MENSAJE_DIRECTA = (
    "gate_reposo_cero_dinamica: la compuerta ejecutada directa exige t = 5 y "
    "no admite HORIZONTE_COMPUERTA={valor!r}. El horizonte parcial es solo "
    "para medir las horas lentas en el servidor, lanzadas con "
    "`python -m pytest tests/gate_reposo_cero_dinamica.py -k \"lenta and "
    "874\"` (o 4766). Quite la variable del entorno para correr la compuerta.")


def _niega_horizonte_parcial_en_directa() -> None:
    """Ronda de arreglos 2: ejecutada directa, la compuerta no corre con
    `HORIZONTE_COMPUERTA` no vacia. Con ella las dos horas rapidas saldrian
    SALTADAS y la compuerta con 0, sin haber aprobado nada. Sale con 2 y lo
    dice. Va antes de leer el horizonte, para que tambien un valor invalido
    salga asi."""
    valor = os.environ.get("HORIZONTE_COMPUERTA", "")
    if valor.strip():
        print(MENSAJE_DIRECTA.format(valor=valor), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    _niega_horizonte_parcial_en_directa()


def _horizonte() -> tuple:
    """(horizonte, puntos de control) de la integracion: DT, o el parcial de
    `HORIZONTE_COMPUERTA`, en (0, DT] y multiplo de PASO_CONTROL (con
    tolerancia de redondeo), de modo que haya un punto de control cada 0,1
    exacto. Un valor que no lo cumple falla al importar, en voz alta, antes de
    integrar nada."""
    texto = os.environ.get("HORIZONTE_COMPUERTA", "").strip()
    h = DT
    if texto:
        try:
            h = float(texto)
        except ValueError:
            raise ValueError(f"HORIZONTE_COMPUERTA={texto!r} no es un "
                             f"numero") from None
        if not (math.isfinite(h) and 0.0 < h <= DT):
            raise ValueError(f"HORIZONTE_COMPUERTA={texto!r} tiene que estar "
                             f"en (0, {DT:g}]")
    pasos = int(round(h / PASO_CONTROL))
    if pasos < 1 or abs(h - pasos * PASO_CONTROL) > 1e-9:
        raise ValueError(f"HORIZONTE_COMPUERTA={texto!r} tiene que ser "
                         f"multiplo de {PASO_CONTROL:g}, para que haya un "
                         f"punto de control cada {PASO_CONTROL:g}")
    return h, pasos + 1


HORIZONTE, N_PUNTOS = _horizonte()
PARCIAL = HORIZONTE < DT


class _Tope(Exception):
    """El tiempo de pared de la hora paso de TOPE_COMPUERTA_S."""


@contextlib.contextmanager
def _integrador_con_tope(cuenta: dict):
    """Envuelve el integrador del modulo para contar evaluaciones, guardar una
    copia del ultimo estado evaluado y cortar por tiempo de pared si hay tope.
    Sin tope la integracion es la misma: la envoltura solo cuenta y copia."""
    t0 = time.perf_counter()

    def envuelto(fun, t_span, y0, **kw):
        def f(t, y):
            cuenta["nfev"] += 1
            if t >= cuenta["t"]:
                # Copia: el integrador puede reutilizar el vector que pasa.
                cuenta["t"], cuenta["y"] = t, np.array(y, dtype=float,
                                                       copy=True)
            if (TOPE_S > 0 and cuenta["nfev"] % 2000 == 0
                    and time.perf_counter() - t0 > TOPE_S):
                raise _Tope()
            return fun(t, y)
        return _solve_ivp_real(f, t_span, y0, **kw)

    original = ccc.solve_ivp
    ccc.solve_ivp = envuelto
    try:
        yield
    finally:
        ccc.solve_ivp = original


def _llamada(k):
    """(reposo, argumentos de `solve_coupled_for_hour`) de la hora k: el
    reposo del nucleo y la integracion regularizada que arranca de el. La usa
    tambien `tests/test_dinamica_regularizada.py` para medir dP/dt en el
    arranque con la misma llamada."""
    s, d, b, techo, piso_j = _entradas(k)
    rep = resuelve_reposo(s, d, b, techo, piso_j)
    J, I = s.size, d.size
    kw = dict(
        G_net_j=s, D_net_i=d, a_j=np.zeros(J), b_j=b,
        lam_j=np.full(J, 100.0), theta_j=np.full(J, 0.5),
        G_klim_i=np.zeros(I), lam_i=np.full(I, 100.0),
        theta_i=np.full(I, 0.5), etha_i=np.full(I, 0.1),
        # El piso del juego es el del reposo (D62); en estas horas es tambien
        # el menor de los vendedores, el que recibe el motor.
        pi_gs=techo, pi_gb=rep.piso, tau_sellers=0.001, tau_buyers=0.01,
        t_span=(0.0, HORIZONTE), n_points=N_PUNTOS, rtol=1e-6, atol=1e-6,
        buyer_competition="aggregate", peso_virtual="barrera",
        mu_entropia=MU, nivel="sigma",
        estado_inicial=dict(P=rep.P, pi=rep.pi_reposo))
    return rep, kw


def _desde_el_reposo(k):
    """Resuelve el reposo de la hora k con el nucleo e integra la dinamica
    regularizada desde el. Devuelve (reposo, trayectoria, segundos)."""
    rep, kw = _llamada(k)
    J, I = len(kw["G_net_j"]), len(kw["D_net_i"])
    cuenta = dict(nfev=0, t=0.0, y=None)
    t0 = time.perf_counter()
    corte = None
    try:
        with _integrador_con_tope(cuenta):
            tr = solve_coupled_for_hour(**kw)
    except _Tope:
        seg = time.perf_counter() - t0
        y = cuenta["y"]
        i0 = I + 1 + 2 * J
        P = np.clip(y[i0:i0 + J * I].reshape(J, I), 0.0, None)
        pi = np.clip(y[:I], rep.piso, kw["pi_gs"])
        corte = (f"hora {k}: paso el tope de {TOPE_S:.0f} (s) en t = "
                 f"{cuenta['t']:.4g}, con {cuenta['nfev']} evaluaciones y "
                 f"{seg:.0f} (s); en el ultimo estado evaluado |dP| = "
                 f"{np.abs(P - rep.P).max():.3e} (kWh) y |dpi| = "
                 f"{np.abs(pi - rep.pi_reposo).max():.3e} (COP/kWh)")
    if corte is not None:
        # Fuera del `except`, para que el fallo diga solo el costo.
        pytest.fail(corte, pytrace=False)
    return rep, tr, time.perf_counter() - t0


def _mide(k, rep, tr, seg):
    """Las distancias al reposo en cada punto de control, y el informe."""
    dP = np.abs(tr.P_t - rep.P[:, :, None]).max(axis=(0, 1))
    dpi = np.abs(tr.pi_t - rep.pi_reposo[:, None]).max(axis=0)
    if PARCIAL:
        print(f"\n    HORIZONTE PARCIAL t = {HORIZONTE:g}: no es la "
              f"aceptacion de la compuerta, que exige t = {DT:g}")
    print(f"\n    hora {k} ({rep.regimen}): exito {tr.success}, t final "
          f"{tr.t[-1]:g}; {tr.nfev} evaluaciones, {tr.njev} jacobianas, "
          f"{seg:.1f} (s)")
    print(f"    E = {rep.E:.4f} (kWh); tolerancias {TOL_P_REL * rep.E:.2e} "
          f"(kWh) y {TOL_PI} (COP/kWh)")
    print(f"    |dP| maximo {dP.max():.3e} (kWh) en t = "
          f"{tr.t[dP.argmax()]:.1f}, final {dP[-1]:.3e}")
    print(f"    |dpi| maximo {dpi.max():.3e} (COP/kWh) en t = "
          f"{tr.t[dpi.argmax()]:.1f}, final {dpi[-1]:.3e}")
    return dP, dpi


def _si_es_parcial_se_salta(k, tr, seg):
    """Con horizonte parcial, la hora que llego dentro de la aceptacion sale
    SALTADA con su costo, nunca aprobada."""
    if PARCIAL:
        pytest.skip(f"hora {k}: horizonte parcial t = {HORIZONTE:g}, dentro "
                    f"de lo medido hasta ahi; {tr.nfev} evaluaciones, "
                    f"{seg:.0f} (s). La compuerta exige t = {DT:g}")


def _acepta(k, regimen):
    rep, tr, seg = _desde_el_reposo(k)
    assert rep.regimen == regimen, (k, rep.regimen)
    dP, dpi = _mide(k, rep, tr, seg)
    assert tr.success, tr.message
    assert tr.t[-1] == HORIZONTE and tr.t.size == N_PUNTOS
    assert np.all(np.isfinite(tr.P_t)) and np.all(np.isfinite(tr.pi_t))
    assert dP.max() <= TOL_P_REL * rep.E, (dP.max(), TOL_P_REL * rep.E)
    assert dpi.max() <= TOL_PI, dpi.max()
    _si_es_parcial_se_salta(k, tr, seg)


# ─── las horas ─────────────────────────────────────────────────────────────


def test_853_todos_interiores_se_queda_en_el_reposo():
    _acepta(853, "interiores")


def test_2120_excluidos_se_queda_en_el_reposo():
    _acepta(2120, "excluidos")


def test_lenta_874_topados_se_queda_en_el_reposo():
    _acepta(874, "topados")


def test_lenta_informativa_4766_compradores_cortos():
    """Solo informa: se afirma que la integracion termina con valores
    finitos, no donde queda. El despacho por merito del reposo frente al de
    la dinamica es lo que mide M-B (H-89)."""
    rep, tr, seg = _desde_el_reposo(4766)
    assert rep.regimen == "compradores_cortos"
    dP, dpi = _mide(4766, rep, tr, seg)
    assert tr.success, tr.message
    assert np.all(np.isfinite(tr.P_t)) and np.all(np.isfinite(tr.pi_t))
    s, d, b, techo, piso_j = _entradas(4766)
    llenado = resuelve_reposo(s, d, b, techo, piso_j,
                              despacho_vendedores="llenado")
    vende = tr.P_t[:, :, -1].sum(axis=1)
    print(f"    INFORMATIVO, sin afirmar. Vende cada vendedor al final: "
          f"{np.array2string(vende, precision=6)} (kWh); por merito "
          f"{np.array2string(rep.s_despachado, precision=6)}; por llenado "
          f"{np.array2string(llenado.s_despachado, precision=6)}")
    print(f"    distancia al merito {np.abs(vende - rep.s_despachado).max():.3e}"
          f" (kWh), al llenado "
          f"{np.abs(vende - llenado.s_despachado).max():.3e} (kWh); "
          f"dentro de la aceptacion de las otras horas: "
          f"{dP.max() <= TOL_P_REL * rep.E and dpi.max() <= TOL_PI}")
    _si_es_parcial_se_salta(4766, tr, seg)


if __name__ == "__main__":
    # Importante 1 de la revision de la tarea 3: ejecutada directa, como corre
    # las compuertas `modelo_base/run_servidor.sh`, la compuerta corre pytest
    # sobre si misma con las dos horas rapidas y sale con SU codigo. Sin esto,
    # `python tests/gate_reposo_cero_dinamica.py` salia con 0 sin ejecutar
    # nada. Las lentas no se corren asi: van por pytest con `-k lenta`, en el
    # servidor. Ronda 2: con `HORIZONTE_COMPUERTA` no vacia ya salio con 2
    # (`_niega_horizonte_parcial_en_directa`, al principio del modulo).
    sys.exit(int(pytest.main([__file__, "-k", "not lenta", "-s", "-q",
                              "-p", "no:cacheprovider"])))
