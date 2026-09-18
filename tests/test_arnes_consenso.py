"""El arnes de la validacion del reposo no se desvio del motor.

QUE COMPRUEBA, que es lo que hace creible las mediciones M-A a M-G:

  1. con k = 1 y las opciones apagadas, el lado derecho de
     `reformateo/documento/scripts/sonda/consenso/arnes.py` coincide AL BIT con
     el que `core/coupled_ode_convergence.py` evalua, en las cuatro
     combinaciones de peso del jugador virtual y de arranque de la oferta;
  2. con mu > 0, el termino entropico del arnes es el del motor (D49);
  3. el arranque de precios del presupuesto sigma que usan las mediciones es el
     mismo `nivel="sigma"` del motor (D50);
  4. el criterio de consenso hace lo que dice: dos puntos de control seguidos
     dentro de la tolerancia, y con las derivadas pequenas;
  5. la aceleracion k escala lo que tiene que escalar (los compradores y el
     replicador del vendedor) y nada mas (los multiplicadores y sus filtros);
  6. los literales del caso publicado de Chacon son los mismos que ya estaban
     en `tests/test_reposo_mercado.py`;
  7. el cargador de la sonda es aditivo al bit con el factor del cargo de
     comercializar (caso CV2).

Y, desde la ronda de arreglos de la revision de 4c:

  8. la comprobacion perturba de forma aditiva por bloque y ejerce los ocho
     bloques del estado, tambien los filtros, que valen cero en X0 (grave 1);
  9. las dos ramas nuevas del motor, el costo por la alternativa y el piso
     marginal, coinciden al bit, y la comprobacion detecta cuando no (grave 3);
 10. M-D clasifica bien los valores propios: una direccion de signos alternos
     y suma cero es inestable, no neutra (grave 2, el caso de la revision);
 11. el veredicto cuenta por familia: M-B distingue las dos reglas cuando la
     alternativa reproduce el piso y el costo nivelado el costo (critico 1);
     M-G se juzga contra su tabla (critico 1b); las cortadas no hunden su hora
     y M-A tiene su brazo sin acelerar (critico 2);
 12. los medios: medicion sin corridas sale con 3 (1), muestra minima (2),
     tolerancia declarada (3), los cuatro arranques entre si (4), las horas
     con recorte que movio el reposo se apartan (5), y el umbral de descarte
     de la seleccion (6).

RAPIDA Y SIN DATOS REALES: todo se hace sobre el caso publicado de Chacon, que
son literales, una hora sintetica y registros escritos a mano. No carga MTE ni
escribe nada fuera de `tmp_path`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
CONSENSO = RAIZ / "reformateo" / "documento" / "scripts" / "sonda" / "consenso"
for _p in (RAIZ, CONSENSO, Path(__file__).resolve().parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# `arnes` se situa en la raiz del repositorio al importarse (lo necesita el
# cargador de horas reales). Aqui se deshace, para no cambiarle el directorio a
# las demas pruebas de la sesion.
_CWD = os.getcwd()
import arnes as A                                   # noqa: E402
import preparacion as PR                            # noqa: E402
import caso_publicado_chacon as CH                  # noqa: E402
os.chdir(_CWD)

HORAS = ("22", "14")
PESOS = ("barrera", "precio")
ARRANQUES = ("factible", "iguales")


@pytest.fixture(scope="module")
def horas():
    return {h: A.hora_de("CHACON", h) for h in HORAS}


# ── 1. el lado derecho, al bit ─────────────────────────────────────────────
@pytest.mark.parametrize("hora", HORAS)
@pytest.mark.parametrize("peso", PESOS)
@pytest.mark.parametrize("arranque", ARRANQUES)
def test_lado_derecho_identico_al_motor(horas, hora, peso, arranque):
    r = A.comprueba_contra_el_motor(horas[hora], peso=peso, arranque=arranque)
    assert r["dif_X0"] == 0.0, f"el estado inicial difiere: {r}"
    # Grave 1: los ocho bloques del estado, tambien los dos filtros que
    # arrancan en cero, tienen que haberse ejercido.
    assert set(r["bloques_ejercidos"]) == {n for n, _ in A.bloques(1, 1)}, \
        f"bloques sin ejercer: {r['bloques_ejercidos']}"
    assert r["identico"], (
        f"el lado derecho del arnes NO es el del motor en {hora}:00 con peso "
        f"{peso} y arranque {arranque}: |dif| = {r['dif_abs']:.3e}, relativa "
        f"{r['dif_rel']:.3e}, en los bloques {r['bloques']}")


# ── 2. el termino entropico (D49) ──────────────────────────────────────────
@pytest.mark.parametrize("hora", HORAS)
@pytest.mark.parametrize("mu", (0.3, 1.0, 3.0))
def test_termino_entropico_identico_al_motor(horas, hora, mu):
    r = A.comprueba_contra_el_motor(horas[hora], mu_ent=mu,
                                    opciones_motor=dict(mu_entropia=mu))
    assert r["identico"], (
        f"el termino entropico del arnes no es el del motor con mu = {mu}: "
        f"|dif| = {r['dif_abs']:.3e} en {r['bloques']}")


def test_el_entropico_cambia_algo(horas):
    """Si apagarlo y encenderlo diera lo mismo, la prueba anterior no diria nada."""
    e = horas["22"]
    f0, X0, _ix = A.construye(e)
    f1, _X1, _ = A.construye(e, mu_ent=1.0)
    rng = np.random.default_rng(3)
    X = X0 * (1 + 0.05 * rng.standard_normal(X0.size))
    assert np.max(np.abs(f0(0.0, X) - f1(0.0, X))) > 0.0


# ── 3. el arranque de precios del presupuesto sigma (D50) ──────────────────
@pytest.mark.parametrize("hora", HORAS)
def test_precios_sigma_son_los_del_motor(horas, hora):
    e = horas[hora]
    I = len(e["dn"])
    _f, y0 = A.captura_motor(e, nivel="sigma")
    pi0 = PR.precios_sigma(e["techo"], e["piso"])
    assert np.array_equal(y0[:I], pi0), (
        f"el arranque sigma del arnes no es el del motor: {y0[:I]} frente a "
        f"{pi0}")
    assert y0[I] == pytest.approx(float(np.max(e["techo"])))
    # Y con ese arranque, la X0 del arnes es la del motor, al bit.
    _f2, X0, _ix = A.construye(e, precios0=np.append(pi0, y0[I]))
    assert np.array_equal(X0, y0)


# ── 4. el criterio de consenso ─────────────────────────────────────────────
def _fila(t, dq, dp, dq_dt=0.0, dp_dt=0.0, nombre="cerrada"):
    return dict(t=t, teq=t, dq_dt=dq_dt, dp_dt=dp_dt,
                dist={nombre: dict(dq=dq, dp=dp, dP=dq, dsj=dq)})


def test_criterio_de_consenso_pide_dos_puntos_seguidos():
    tol = dict(tol_q_rel=1e-3, tol_p=0.05)
    E = 10.0        # la tolerancia de reparto es 1e-2 (kWh)
    # Uno dentro y el siguiente fuera: no llega.
    filas = [_fila(0, 1.0, 10.0), _fila(1, 1e-3, 1e-3), _fila(2, 1.0, 10.0)]
    assert not PR.criterio_consenso(filas, "cerrada", E, tol)["llega"]
    # Dos seguidos dentro: llega, y en el primero de los dos.
    filas = [_fila(0, 1.0, 10.0), _fila(1, 1e-3, 1e-3), _fila(2, 1e-3, 1e-3)]
    r = PR.criterio_consenso(filas, "cerrada", E, tol)
    assert r["llega"] and r["t"] == 1
    # Dentro pero moviendose: no llega.
    filas = [_fila(0, 1e-3, 1e-3, dq_dt=1.0), _fila(1, 1e-3, 1e-3, dq_dt=1.0),
             _fila(2, 1e-3, 1e-3, dq_dt=1.0)]
    assert not PR.criterio_consenso(filas, "cerrada", E, tol)["llega"]
    # El precio fuera por poco tambien es fuera.
    filas = [_fila(0, 1e-3, 0.06), _fila(1, 1e-3, 0.06)]
    assert not PR.criterio_consenso(filas, "cerrada", E, tol)["llega"]
    # El reparto se compara contra 1e-3·E, no contra 1e-3.
    filas = [_fila(0, 5e-3, 0.0), _fila(1, 5e-3, 0.0)]
    assert PR.criterio_consenso(filas, "cerrada", E, tol)["llega"]
    assert not PR.criterio_consenso(filas, "cerrada", 1.0, tol)["llega"]


def test_la_tolerancia_se_afloja_con_aceleracion_o_con_topados():
    estricta = PR.tolerancias("interiores", 1.0)
    assert estricta["clase"] == "estricta"
    assert estricta["tol_q_rel"] == PR.TOL_Q_REL_ESTRICTA
    for caso in (("interiores", 100.0), ("topados", 1.0), ("mixto", 1000.0),
                 ("compradores_cortos", 1.0)):
        t = PR.tolerancias(*caso)
        assert t["clase"] == "floja" and t["tol_p"] == PR.TOL_P_FLOJA, caso


# ── 5. la aceleracion escala lo que tiene que escalar ──────────────────────
@pytest.mark.parametrize("k", (100.0, 1000.0))
def test_la_aceleracion_escala_solo_su_parte(horas, k):
    e = horas["22"]
    I, J = len(e["dn"]), len(e["gn"])
    f1, X0, _ix = A.construye(e, mu_ent=1.0)
    fk, Xk, _ = A.construye(e, mu_ent=1.0, k_lento=k)
    assert np.array_equal(X0, Xk), "la aceleracion no toca el estado inicial"
    rng = np.random.default_rng(7)
    for _ in range(5):
        X = X0 * (1 + 0.05 * rng.standard_normal(X0.size))
        a = np.asarray(f1(0.0, X), float)
        b = np.asarray(fk(0.0, X), float)
        for nombre, sl in A.bloques(I, J, X0.size):
            if nombre in ("precios", "gamma", "filtro_gamma", "P"):
                assert np.allclose(b[sl], k * a[sl], rtol=1e-12, atol=0.0), \
                    f"el bloque {nombre} no escalo por k = {k}"
            else:
                assert np.array_equal(b[sl], a[sl]), \
                    f"el bloque {nombre} cambio con k = {k} y no debia"


def test_la_aceleracion_no_mueve_los_ceros(horas):
    """Lo que justifica acelerar: el reposo es el mismo."""
    e = horas["22"]
    f1, X0, ix = A.construye(e, mu_ent=1.0)
    fk, _Xk, _ = A.construye(e, mu_ent=1.0, k_lento=1000.0)
    rng = np.random.default_rng(11)
    for _ in range(5):
        X = X0 * (1 + 0.05 * rng.standard_normal(X0.size))
        a = np.asarray(f1(0.0, X), float)
        b = np.asarray(fk(0.0, X), float)
        assert np.array_equal(a == 0.0, b == 0.0)


# ── 6. los literales del caso publicado ────────────────────────────────────
def test_los_literales_de_chacon_son_los_del_nucleo():
    from test_reposo_mercado import GLIM_22, DOPT_22, B_CHACON
    assert np.array_equal(CH.CASO22["Glim"], GLIM_22)
    assert np.array_equal(CH.CASO22["Dopt"], DOPT_22)
    assert np.array_equal(CH.B_ALL, B_CHACON)


# ── 7. el factor del cargo de comercializar (D7, caso CV2) ────────────────
# `paso_a_paso.carga` acepta `factor_cv` para que el arnes pueda reproducir el
# caso CV2 de la matriz, que M-C necesita. Lo que hay que comprobar es que el
# anadido es ADITIVO: sin el factor, la carga tiene que ser identica al bit a
# la de siempre. Se hace con un cargador falso, de modo que la prueba sigue
# siendo rapida y sin datos reales: las tarifas y la bolsa salen de los CSV del
# repositorio, y lo unico que se finge son las series de demanda y generacion.
IDX_FALSO = ("2025-05-05", 72)     # 72 horas dentro del rango de la bolsa


@pytest.fixture
def cargador_falso(monkeypatch, tmp_path):
    """Demanda y generacion sinteticas, con el calendario real."""
    import pandas as pd
    import data.xm_data_loader as xdl
    from data.cedenar_tariff import INSTITUTION_PROFILE

    inicio, T = IDX_FALSO
    idx = pd.date_range(inicio, periods=T, freq="h")
    N = 5
    t = np.arange(T)
    sol = np.clip(np.sin((t % 24 - 6) * np.pi / 12), 0, None)
    G = np.outer(np.array([9.0, 1.2, 0.8, 2.0, 0.0]), sol)
    D = np.outer(np.array([3.0, 1.0, 0.9, 2.5, 1.4]),
                 1.0 + 0.3 * np.cos(t * np.pi / 12))
    monkeypatch.setenv("MTE_ROOT", str(tmp_path))
    monkeypatch.setattr(xdl.MTEDataLoader, "load",
                        lambda self, *a, **k: (D.copy(), G.copy(), idx))
    # `carga` fija el regimen tarifario global; se devuelve como estaba para no
    # cambiarselo a las demas pruebas de la sesion.
    antes = dict(INSTITUTION_PROFILE)
    yield
    INSTITUTION_PROFILE.clear()
    INSTITUTION_PROFILE.update(antes)


def test_sin_factor_cv_la_carga_es_identica_al_bit(cargador_falso):
    import paso_a_paso as PP
    base = PP.carga("m1")
    for otro in (PP.carga("m1", factor_cv=1.0), PP.carga("m1", factor_cv=None)):
        assert set(base) == set(otro)
        for k in ("D", "G", "techo", "cvm", "peaje", "bolsa", "perm", "piso"):
            assert np.array_equal(base[k], otro[k], equal_nan=True), \
                f"el defecto de factor_cv movio {k}"


def test_el_factor_cv_solo_mueve_el_piso_por_el_cv(cargador_falso):
    import paso_a_paso as PP
    from core.opciones_externas import deduccion_art25, piso_por_vendedor
    from data.capacidad_instalada import capacidad_instalada

    base = PP.carga("m1")
    dos = PP.carga("m1", factor_cv=2.0)
    # Lo que NO se mueve: las series, el techo, el peaje, la bolsa y el tramo.
    for k in ("D", "G", "techo", "peaje", "bolsa", "perm"):
        assert np.array_equal(base[k], dos[k], equal_nan=True), \
            f"factor_cv movio {k} y no debia"
    # Lo que si: el Cv, exactamente por dos.
    assert np.allclose(dos["cvm"], 2.0 * base["cvm"], rtol=0, atol=0,
                       equal_nan=True)
    # Y el piso, exactamente el que sale de ese Cv por la misma receta.
    esperado = piso_por_vendedor(
        base["techo"],
        deduccion_art25(2.0 * base["cvm"], base["peaje"],
                        capacidad_instalada(base["nombres"], None)),
        base["bolsa"], base["perm"])
    assert np.array_equal(dos["piso"], esperado, equal_nan=True)
    # El piso de permuta baja (se deduce mas Cv) y el de bolsa no se mueve.
    perm = base["perm"]
    assert np.all(dos["piso"][perm] <= base["piso"][perm] + 1e-12)
    assert np.array_equal(dos["piso"][~perm], base["piso"][~perm],
                          equal_nan=True)


def test_un_factor_cv_absurdo_falla_en_voz_alta(cargador_falso):
    import paso_a_paso as PP
    for malo in (0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            PP.carga("m1", factor_cv=malo)


def test_el_arnes_carga_cv2_con_el_factor(cargador_falso):
    """CV2 en el arnes es la carga con el Cv por dos, y E0 la de siempre."""
    A._CACHE.clear()
    try:
        e0, _ = A.carga("E0")
        cv2, _ = A.carga("CV2")
        assert np.array_equal(e0["D"], cv2["D"])
        assert np.array_equal(e0["G"], cv2["G"])
        assert np.array_equal(e0["techo"], cv2["techo"])
        assert np.allclose(cv2["cvm"], 2.0 * e0["cvm"], rtol=0, atol=0,
                           equal_nan=True)
        assert not np.array_equal(e0["piso"], cv2["piso"])
    finally:
        A._CACHE.clear()


def test_un_agente_sin_papel_se_avisa_y_no_cambia_el_resultado(capsys):
    """Menor 4 de la revision: Glim = Dopt = 0 da 0/0 y el agente sale del
    mercado, como en JoinFinal.m; ahora se dice cual y por que."""
    glim = np.array([2.0, 0.0, 0.5, 0.0, 0.0, 0.0])
    dopt = np.array([1.0, 0.0, 1.5, 0.4, 0.3, 0.2])
    c = CH.prepara(glim, dopt)
    assert list(c["vendedores"]) == [0]
    assert list(c["compradores"]) == [2, 3, 4, 5]
    assert [s["agente"] for s in c["sin_papel"]] == ["ag2"]
    err = capsys.readouterr().err
    assert "ag2 queda FUERA" in err and "Glim = 0 y Dopt = 0" in err
    # En las dos horas publicadas no ocurre.
    for base in (CH.CASO14, CH.CASO22):
        assert CH.prepara(base["Glim"], base["Dopt"])["sin_papel"] == []


def test_el_caso_de_chacon_clasifica_como_el_nucleo(horas):
    """Un vendedor con 1,381 (kWh) y cinco compradores, a las 22:00.

    El vendedor es el agente 4 (1,760 de generacion y 0,379 de demanda) y los
    otros cinco compran; es la clasificacion de JoinFinal.m y la que
    `tests/test_reposo_mercado.py` usa para el mismo caso.
    """
    e = horas["22"]
    assert e["vend"] == ["ag4"]
    assert e["comp"] == ["ag1", "ag2", "ag3", "ag5", "ag6"]
    assert np.allclose(e["gn"], [1.381], rtol=0, atol=1e-12)
    assert np.allclose(e["dn"], [0.577, 0.525, 0.534, 0.262, 0.208],
                       rtol=0, atol=1e-12)
    assert e["piso"] == 114.0 and np.all(e["techo"] == 1250.0)


# ═══════════════ ronda de arreglos de la revision de 4c ═══════════════════
import corre_mediciones as CM                        # noqa: E402
import veredicto as V                                # noqa: E402
import medicion_regimenes as MA                      # noqa: E402
import medicion_merito_vendedores as MB              # noqa: E402
import medicion_suma_no_cabe as MC                   # noqa: E402
import medicion_estabilidad as MD                    # noqa: E402
import medicion_mu as ME                             # noqa: E402
import medicion_chacon as MG                         # noqa: E402
import selecciona_horas as SH                        # noqa: E402
os.chdir(_CWD)

TODOS_LOS_BLOQUES = {n for n, _ in A.bloques(1, 1)}


# ── grave 1: la perturbacion ejerce los filtros ────────────────────────────
def test_la_perturbacion_es_aditiva_y_mueve_los_bloques_nulos(horas):
    e = horas["22"]
    _f, X0, ix = A.construye(e)
    tramos = A.bloques(ix["I"], ix["J"], X0.size)
    nulos = [n for n, sl in tramos if np.all(X0[sl] == 0.0)]
    assert set(nulos) == {"filtro_lam", "filtro_bet"}, \
        "el arranque tiene que traer los dos filtros en cero"
    X = A.perturba(X0, tramos, np.random.default_rng(0), 0.05)
    for n, sl in tramos:
        assert np.any(X[sl] != X0[sl]), f"la perturbacion no movio {n}"
    cargado = A.estado_cargado(X0, ix["I"], ix["J"], np.random.default_rng(0))
    for n, sl in tramos:
        if n in ("filtro_lam", "filtro_bet"):
            assert np.all(cargado[sl] >= 1e3), f"{n} no quedo cargado"


# ── grave 3: las dos ramas nuevas del motor ────────────────────────────────
@pytest.mark.parametrize("caso,fecha", [("CHACON", "22"), ("CHACON", "14"),
                                        ("SINTETICA", "pisos")])
def test_todas_las_ramas_identicas_al_motor(caso, fecha):
    e = A.hora_de(caso, fecha)
    for rotulo, kw in A.ramas(e):
        r = A.comprueba_contra_el_motor(e, **kw)
        assert r["identico"], (f"{caso} {fecha} {rotulo}: |dif| = "
                               f"{r['dif_abs']:.3e} en {r['bloques']}")
        assert set(r["bloques_ejercidos"]) == TODOS_LOS_BLOQUES


def test_la_hora_sintetica_ejerce_el_piso_marginal():
    """Si el piso marginal fuera el minimo, la rama no probaria nada."""
    e = A.caso_pisos_distintos()
    assert A.piso_marginal(e) == 690.0 and e["piso"] == 600.0


def test_la_comprobacion_detecta_ramas_cruzadas():
    """Que no sea vacia: el arnes con el piso minimo frente al motor con el
    marginal, o con b_j frente a la alternativa, tiene que DIFERIR."""
    e = A.caso_pisos_distintos()
    r = A.comprueba_contra_el_motor(
        e, opciones_motor=dict(piso_juego="marginal", piso_j=e["piso_j"]))
    assert not r["identico"] and "precios" in r["bloques"]
    r = A.comprueba_contra_el_motor(
        e, opciones_motor=dict(costo_vendedor="alternativa",
                               piso_j=e["piso_j"]))
    assert not r["identico"] and "P" in r["bloques"]


# ── grave 2: M-D y el vector propio con signo ──────────────────────────────
I_MD, J_MD = 5, 2
N_MD = (I_MD + 1) + J_MD * I_MD            # 16


def _alternos(desde, hasta):
    u = np.zeros(N_MD)
    u[desde:hasta] = [(-1.0) ** k for k in range(hasta - desde)]
    return u


def _jac_con(u, lam):
    """-1 en todo, salvo lam en la direccion u."""
    u = u / np.linalg.norm(u)
    return -np.eye(N_MD) + (lam + 1.0) * np.outer(u, u)


def _regla_vieja_neutra(u) -> bool:
    """La regla de antes: abs del vector y maximo sobre las dos direcciones."""
    neutras = MD.direcciones_neutras(I_MD, J_MD)
    v = np.abs(u) / np.linalg.norm(np.abs(u))
    return float(np.max(np.abs(neutras @ v))) >= MD.TOL_ALINEADO


@pytest.mark.parametrize("bloque", ["reparto", "precios"])
def test_md_signos_alternos_de_suma_cero_es_inestable(bloque):
    """El caso de la revision: I = 5, J = 2, una direccion de signos alternos
    y suma cero dentro de un bloque. Es ortogonal a lo conservado y crece, de
    modo que es INESTABLE. La regla vieja la daba por neutra."""
    u = (_alternos(I_MD + 1, N_MD) if bloque == "reparto"
         else _alternos(0, I_MD + 1))
    assert abs(u[:I_MD + 1].sum()) < 1e-12 and abs(u[I_MD + 1:].sum()) < 1e-12
    assert _regla_vieja_neutra(u), "la prueba tiene que apuntar al defecto"
    c = MD.clasifica_valores_propios(_jac_con(u, 1.0), I_MD, J_MD)
    assert len(c["inestables"]) == 1
    assert c["inestables"][0]["alineacion"] < 1e-9


def test_md_lo_conservado_no_cuenta_como_inestable():
    neutras = MD.direcciones_neutras(I_MD, J_MD)
    for u in neutras:
        c = MD.clasifica_valores_propios(_jac_con(u, 1.0), I_MD, J_MD)
        assert c["inestables"] == []


def test_md_par_conjugado_ortogonal_es_inestable():
    a = _alternos(0, I_MD + 1)
    b = _alternos(I_MD + 1, N_MD)
    rng = np.random.default_rng(3)
    Q, _ = np.linalg.qr(np.column_stack([a, b, rng.standard_normal(
        (N_MD, N_MD - 2))]))
    D = -np.eye(N_MD)
    D[:2, :2] = [[0.5, -2.0], [2.0, 0.5]]      # 0,5 +- 2i
    c = MD.clasifica_valores_propios(Q @ D @ Q.T, I_MD, J_MD)
    assert len(c["inestables"]) == 1           # el par, contado una vez
    assert c["inestables"][0]["re"] == pytest.approx(0.5)
    c = MD.clasifica_valores_propios(-np.eye(N_MD), I_MD, J_MD)
    assert c["inestables"] == []


# ── registros sinteticos con la forma que escribe corre_mediciones ─────────
def _registro(medicion, familia, caso, fecha, k, regimen, E, dist,
              teqs=(0.0, 80.0, 160.0), tol=None, recorte_movio=False,
              final=None, refs=None, var=None, quieta=True, grupo="g"):
    """Una corrida sintetica con la forma que escribe la noche (sin
    `plan_total`, como los JSON lanzados antes de la re-revision). `dist` es
    {referencia: dict(dq, dp, dP, dsj)}, igual en todos los puntos de control
    salvo el primero, que va lejos. `refs` son los repartos cerrados de cada
    referencia ({ref: dict(P=...)}), `var` se anade a los ganchos, y con
    `quieta=False` el estado final todavia se mueve."""
    tol = tol or dict(tol_q_rel=1e-2, tol_p=0.5, clase="floja",
                      motivo="prueba")
    final = final or dict(p=[700.0], q=[1.0], ppond=700.0, parte=0.5)
    lejos = {r: dict(dq=9.0, dp=99.0, dP=9.0, dsj=9.0) for r in dist}
    filas = [dict(t=t / k, teq=t,
                  dq_dt=(1.0 if n == 0 else (0.0 if quieta else 0.5)),
                  dp_dt=0.0, nfev=100 * (n + 1), seg=float(n), **final,
                  dist=(lejos if n == 0 else {r: dict(d) for r, d in
                                              dist.items()}))
             for n, t in enumerate(teqs)]
    ver = {r: dict(consenso=PR.criterio_consenso(filas, r, E, tol),
                   teq80=PR.en_teq(filas, r, E, tol, 80.0),
                   teq160=PR.en_teq(filas, r, E, tol, 160.0),
                   final=PR.dentro(filas[-1], r, E, tol)) for r in dist}
    cortada = abs(teqs[-1] - 160.0) > 1e-9
    v = dict(k_lento=k)
    v.update(var or {})
    return dict(spec=dict(medicion=medicion, familia=familia, caso=caso,
                          fecha=fecha, etq=f"{familia} k{k:g}", grupo=grupo,
                          var=v),
                msg=("ok" if not cortada else "tope 3600 s en [..]"),
                cortada=cortada, teq_alcanzado=teqs[-1], nfev=filas[-1]["nfev"],
                recorte_movio=recorte_movio, regimen=regimen, E=E,
                tolerancia=tol, filas=filas, veredicto=ver, seg=1.0,
                cerrada=(refs or {}))


# Los repartos cerrados de las tres reglas en una hora de M-B: el piso y el
# costo despachan a vendedores distintos (la hora DISCRIMINA), o igual.
REFS_DISCRIMINA = {"cerrada": dict(P=[[1.0, 0.0], [0.0, 1.0]]),
                   "costo": dict(P=[[0.0, 1.0], [1.0, 0.0]]),
                   "llenado": dict(P=[[0.5, 0.5], [0.5, 0.5]])}
REFS_IGUALES = {"cerrada": dict(P=[[1.0, 0.0], [0.0, 1.0]]),
                "costo": dict(P=[[1.0, 0.0], [0.0, 1.0]]),
                "llenado": dict(P=[[0.5, 0.5], [0.5, 0.5]])}


def registros_mb(n_horas=6, E=2.0, refs=REFS_DISCRIMINA):
    """M-B cuando la alternativa reproduce la regla del piso y el costo
    nivelado la del costo. Del lado de los compradores las tres reglas dan lo
    mismo (compradores cortos: cada uno recibe su deficit); lo que cambia es el
    reparto entre vendedores, dP."""
    bien = dict(dq=1e-6, dp=1e-3, dP=1e-5, dsj=1e-5)
    mal = dict(dq=1e-6, dp=1e-3, dP=0.3, dsj=0.3)
    fuera = []
    for h in range(n_horas):
        fecha = f"2025-05-{h + 1:02d} 12:00"
        for k in (100.0, 1000.0):
            fuera.append(_registro("M-B", "costo alternativa", "E4", fecha, k,
                                   "compradores_cortos", E,
                                   dict(cerrada=bien, costo=mal, llenado=mal),
                                   refs=refs))
            fuera.append(_registro("M-B", "costo lcoe", "E4", fecha, k,
                                   "compradores_cortos", E,
                                   dict(cerrada=mal, costo=bien, llenado=mal),
                                   refs=refs))
    return fuera


def _veredicto_viejo_dP(resultados, regla):
    """La clave de antes: la hora sin mirar la variante, todas dentro."""
    horas = {}
    for r in resultados:
        horas.setdefault((r["spec"]["caso"], r["spec"]["fecha"]), []).append(r)
    return sum(all(c["filas"][-1]["dist"][regla]["dP"] <= 1e-3 * c["E"]
                   for c in corridas) for corridas in horas.values())


# ── critico 1: la familia en la clave; M-B distingue las dos reglas ───────
def test_mb_distingue_las_dos_reglas():
    res = registros_mb()
    # Antes: las tres reglas en cero, D64 indecidible.
    assert all(_veredicto_viejo_dP(res, r) == 0
               for r in ("cerrada", "costo", "llenado"))
    texto = MB.veredicto(res)
    assert "con costo alternativa: gana piso (D64)" in texto
    assert "con costo lcoe: gana costo (D52)" in texto
    assert "DISTINGUE" in texto
    # El rotulo generico (por q y p) no sale en M-B: diria «reposo verificado»
    # tambien para la regla que pierde, porque con compradores cortos las tres
    # reglas dan el mismo q.
    completo = V.resume(res)
    assert "reposo verificado" not in completo
    assert "(ver el juicio propio)" in completo
    # Y la tabla generica cuenta cada familia aparte.
    grupos, _ = V.agrupa(res)
    for (reg, ref, fam), horas_g in grupos.items():
        cuentas = [V.cuenta_hora(c, ref) for c in horas_g.values()]
        esperado = ((fam == "costo alternativa" and ref == "cerrada")
                    or (fam == "costo lcoe" and ref == "costo"))
        assert sum(c["con_dP"] for c in cuentas) == (6 if esperado else 0), \
            (fam, ref)


def test_ma_las_dos_aceleraciones_son_una_familia():
    """En M-A una hora pasa si pasan sus dos aceleraciones, no una sola."""
    bien = dict(dq=1e-5, dp=0.01, dP=1e-5, dsj=1e-5)
    mal = dict(dq=0.5, dp=5.0, dP=0.5, dsj=0.5)
    res = [_registro("M-A", "V3a acelerada", "E0", "2025-05-09 13:00", 100.0,
                     "interiores", 1.0, dict(cerrada=bien)),
           _registro("M-A", "V3a acelerada", "E0", "2025-05-09 13:00", 1000.0,
                     "interiores", 1.0, dict(cerrada=mal))]
    grupos, _ = V.agrupa(res)
    (clave, horas_g), = grupos.items()
    c = V.cuenta_hora(next(iter(horas_g.values())), "cerrada")
    assert c["juzgada"] and not c["dentro"] and c["alguna"]


# ── critico 2: el brazo sin acelerar y las cortadas ────────────────────────
def test_ma_tiene_brazo_sin_acelerar_en_los_grupos_libres():
    horas_f = {"E0": {g: [dict(fecha="2025-05-09 13:00")] * 12
                      for g in MA.GRUPOS}}
    sp = MA.specs(horas_f)
    k1 = [s for s in sp if s["var"]["k_lento"] == 1.0]
    assert {s["grupo"] for s in k1} == set(MA.GRUPOS_LIBRES)
    assert all(s["familia"] == MA.SIN_ACELERAR and s["cortes"][-1] == 160
               and s["tope"] == 3600.0 for s in k1)
    assert len(sp) == 6 * 10 * 2 + 2 * 10
    # Con k = 1 y compradores libres, la tolerancia es la estricta del plan.
    assert PR.tolerancias("interiores", 1.0)["clase"] == "estricta"
    assert PR.tolerancias("suma_no_cabe", 1.0)["clase"] == "estricta"


def test_una_corrida_cortada_no_hunde_su_hora():
    bien = dict(dq=1e-5, dp=0.01, dP=1e-5, dsj=1e-5)
    res = [_registro("M-A", "V3a acelerada", "E0", "h", 100.0, "interiores",
                     1.0, dict(cerrada=bien)),
           _registro("M-A", "V3a acelerada", "E0", "h", 1000.0, "interiores",
                     1.0, dict(cerrada=bien), teqs=(0.0, 20.0, 40.0))]
    grupos, _ = V.agrupa(res)
    c = V.cuenta_hora(next(iter(next(iter(grupos.values())).values())),
                      "cerrada")
    assert c["juzgada"] and c["dentro"] and c["cortadas"] == 1
    # Y si todas se cortan, la hora no se juzga (ni dentro ni fuera).
    solo = [res[1]]
    grupos, _ = V.agrupa(solo)
    c = V.cuenta_hora(next(iter(next(iter(grupos.values())).values())),
                      "cerrada")
    assert not c["juzgada"] and c["cortadas"] == 1


# ── critico 1b: M-G contra su tabla ────────────────────────────────────────
def test_mg_se_juzga_contra_la_tabla_publicada():
    reposo = dict(p=[833.3333, 833.3333, 833.3333, 1250.0, 1250.0],
                  q=[0.303667, 0.303667, 0.303667, 0.262, 0.208],
                  ppond=975.14, parte=0.758)
    camino = dict(p=[947.6, 947.6, 947.6, 1037.0, 1120.0],
                  q=[0.30, 0.30, 0.30, 0.26, 0.21], ppond=990.0, parte=0.772)
    d = dict(dq=0.0, dp=0.0, dP=0.0, dsj=0.0)
    res = [_registro("M-G", MG.BARRERA, "CHACON", "22", 100.0, "topados",
                     1.381, dict(cerrada=d), final=reposo),
           _registro("M-G", MG.BARRERA, "CHACON", "22", 1.0, "topados",
                     1.381, dict(cerrada=d), teqs=(0.0, 20.0, 40.0),
                     final=camino)]
    texto = MG.veredicto(res)
    assert "brazo k = 1: llego a teq 40" in texto      # se publica, no falla
    assert "CUMPLE  precios 833,3 x 3 y 1 250 x 2" in texto
    assert "CUMPLE  reparto [0,3037 x 3; 0,262; 0,208]" in texto
    assert "CUMPLE  parte del vendedor 0,758" in texto
    # El 0,77 del plan era el transitorio a t = 0,3: ya no esta en la
    # aceptacion (decision del controlador, 2026-09-18).
    assert "0,77 " not in texto and "0,77)" not in texto
    assert all(abs(v - 0.77) > 1e-9 for _t, m, v, _tol, _f
               in MG.ESPERADO[("22", MG.BARRERA)] if m == "parte")
    assert "con el brazo k = 100" in texto
    # En M-G la tabla generica no rotula.
    assert "(ver el juicio propio)" in V.tabla(res, rotular=False)
    assert "M-G CONTRA LA TABLA" in V.resume(res)


@pytest.mark.parametrize("final,lectura", [
    (dict(p=[114.0] * 5, q=[0.3] * 5, ppond=114.2, parte=0.0005), "(b)"),
    (dict(p=[114.0, 380.3, 114.0, 114.0, 114.0], q=[0.3] * 5, ppond=225.4,
          parte=0.0985), "(a)"),
    (dict(p=[600.0] * 5, q=[0.3] * 5, ppond=600.0, parte=0.43), "(c)"),
])
def test_mg_el_brazo_de_precio_dice_su_lectura(final, lectura):
    d = dict(dq=0.0, dp=0.0, dP=0.0, dsj=0.0)
    res = [_registro("M-G", MG.PRECIO, "CHACON", "22", 100.0, "topados",
                     1.381, dict(cerrada=d), final=final)]
    texto = MG.veredicto(res)
    assert f"=> se cumple la lectura {lectura}" in texto or (
        lectura == "(c)" and "=> (c) no se cumple ninguna" in texto)


def test_mg_corre_en_la_configuracion_del_codigo_de_la_autora():
    """La de la sonda del consenso y la de H-88: competencia `matlab` y oferta
    a partes iguales, en los dos brazos, con nivel c136 y el Algoritmo 3."""
    for sp in MG.specs({}):
        assert sp["var"]["comp"] == "matlab"
        assert sp["var"]["arranque"] == "iguales"
        assert sp["nivel"] == "c136"
        assert sp["cerrada"]["modo_presupuesto"] == "algoritmo3"


def test_mg_la_tabla_de_las_14_es_la_forma_cerrada():
    e = A.hora_de("CHACON", "14")
    r = PR.resuelve(e, modo_presupuesto="algoritmo3", pi_gs=1250.0)
    tabla = dict((m, v) for _t, m, v, _tol, _f in MG.ESPERADO[("14",
                                                                MG.BARRERA)])
    assert np.allclose(r.pi_reposo, tabla["p"], atol=0.5)
    assert np.allclose(r.q, tabla["q"], atol=1e-3)
    assert abs(r.parte_vendedor - tabla["parte"]) <= 0.005


# ── medio 1: una medicion sin corridas no sale con 0 ───────────────────────
def test_una_medicion_sin_corridas_sale_con_3(tmp_path, capsys):
    vacia = tmp_path / "sin_horas"
    vacia.mkdir()
    cod = CM.main(["--medicion", "medicion_suma_no_cabe", "--salida",
                   str(tmp_path / "m_c.json"), "--horas", str(vacia)])
    assert cod == 3
    assert "CERO CORRIDAS" in capsys.readouterr().out
    assert not (tmp_path / "m_c.json").exists()
    assert MD.main(["--horas", str(vacia), "--salida",
                    str(tmp_path / "m_d.json")]) == 3


# ── medio 2: muestra minima y el n siempre ─────────────────────────────────
def test_rotulo_con_muestra_minima():
    assert V.MIN_MUESTRA == PR.MIN_MUESTRA == MB.MIN_MUESTRA == 5
    assert V.rotulo(4, 4) == "muestra insuficiente (n = 4)"
    assert V.rotulo(5, 5) == "reposo verificado (n = 5)"
    assert V.rotulo(9, 10) == "regla declarada (90 %, n = 10)"


# ── medio 3: la tolerancia declarada ───────────────────────────────────────
def test_mc_y_me_usan_la_tolerancia_que_declaran():
    horas_f = {"E0": {"suma_no_cabe": [dict(fecha="f")] * 3},
               "CV2": {"suma_no_cabe": [dict(fecha="g")] * 3}}
    for sp in MC.specs(horas_f):
        assert sp["tolerancia"] is MC.TOLERANCIA
    horas_f = {"E0": {g: [dict(fecha="f")] * 3 for g in ME.GRUPOS}}
    for sp in ME.specs(horas_f):
        assert sp["tolerancia"] is ME.TOLERANCIA
    t = PR.tolerancias("interiores", 100.0, declarada=MC.TOLERANCIA)
    assert (t["tol_q_rel"], t["tol_p"]) == (1e-3, 0.5)
    assert t["clase"] == "declarada M-C"
    with pytest.raises(ValueError):
        PR.tolerancias("interiores", 1.0, declarada=dict(tol_p=0.5))


# ── medio 4: los cuatro arranques entre si y la energia afectada ───────────
def _arranque(fecha, E, q, p, cortada=False, nivel="sigma", oferta="iguales",
              dist=None):
    """Un arranque de M-C: su arranque de precios va en `spec.nivel` y el de
    la oferta en `spec.var.arranque`, como en la noche."""
    d = dist or dict(dq=0.0, dp=0.0, dP=0.0, dsj=0.0)
    r = _registro("M-C", MC.FAMILIA, "E0", fecha, 100.0, "suma_no_cabe", E,
                  dict(cerrada=d),
                  teqs=((0.0, 80.0, 160.0) if not cortada else (0.0, 20.0)),
                  final=dict(p=p, q=q, ppond=700.0, parte=0.4),
                  var=dict(arranque=oferta))
    r["spec"]["nivel"] = nivel
    r["spec"]["etq"] = f"oferta {oferta} + precios {nivel}"
    return r


def _cuatro(fecha, E, sigma, medio, sigma_f=None, medio_f=None):
    """Los cuatro arranques de una hora: (q, p) final de cada arranque de
    precios con la oferta iguales, y con la factible si se da otro."""
    return [_arranque(fecha, E, *sigma, nivel="sigma", oferta="iguales"),
            _arranque(fecha, E, *(sigma_f or sigma), nivel="sigma",
                      oferta="factible"),
            _arranque(fecha, E, *medio, nivel="medio", oferta="iguales"),
            _arranque(fecha, E, *(medio_f or medio), nivel="medio",
                      oferta="factible")]


def test_mc_multiplicidad_dentro_de_un_arranque_y_energia():
    a = ([1.0, 1.0], [700.0, 710.0])
    b = ([1.5, 0.5], [700.0, 710.0])
    # `entre_arranques` compara lo que se le da.
    iguales = [_arranque("A", 2.0, *a) for _ in range(4)]
    assert not MC.entre_arranques(iguales)["multiple"]
    r = MC.entre_arranques(iguales[:1] + [_arranque("A", 2.0, *b)])
    assert r["multiple"] and r["dq"] == pytest.approx(0.5)
    # La hora A tiene las dos ofertas de sigma en sitios distintos; la B no.
    res = (_cuatro("A", 2.0, a, a, sigma_f=b)
           + _cuatro("B", 3.0, ([1.0, 2.0], [690.0, 695.0]),
                     ([1.0, 2.0], [690.0, 695.0])))
    texto = MC.veredicto(res)
    assert "1 en SITIOS DISTINTOS (varios reposos)" in texto
    assert "VARIOS REPOSOS E0 A (precios sigma)" in texto
    assert "2.0000 de 5.0000 (kWh) de la muestra = 40.00 %" in texto
    assert "DECLARADA por multiplicidad" in texto
    # Un arranque cortado antes de teq 160 no entra en la comparacion.
    r = MC.entre_arranques(iguales[:3] + [_arranque("A", 2.0, [9.0, 9.0],
                                                    [1.0, 1.0], cortada=True)])
    assert r["comparados"] == 3 and not r["multiple"]


# ── medio 5: la hora con recorte que movio el reposo se aparta ─────────────
def test_la_hora_con_recorte_movido_no_cuenta():
    bien = dict(dq=1e-5, dp=0.01, dP=1e-5, dsj=1e-5)
    res = [_registro("M-A", "V3a acelerada", "E0", "h", 100.0, "interiores",
                     1.0, dict(cerrada=bien), recorte_movio=True)]
    grupos, apartadas = V.agrupa(res)
    assert grupos == {} and len(apartadas) == 1
    assert "APARTADAS" in V.tabla(res)


# ── medio 6: el umbral de descarte de la seleccion ─────────────────────────
@pytest.mark.parametrize("descartes,excesivo", [(3, False), (4, True)])
def test_seleccion_falla_si_descarta_demasiado(descartes, excesivo):
    malas = set(range(descartes))

    def comprueba(h):
        if h in malas:
            return None, "otro regimen", f"la hora {h} no casa"
        return dict(hora=h), "", ""
    x = SH.examina_grupo("interiores", list(range(10)), 40, comprueba)
    assert x["examinadas"] == 10 and x["descartadas"] == descartes
    assert x["excesivo"] is excesivo
    assert x["motivos"] == ({"otro regimen": descartes} if descartes else {})


# ═══════════════ re-revision de 4c: la capa del veredicto ════════════════
# Todo se lee de JSON con la forma que escribe la noche lanzada ANTES de este
# arreglo (sin `plan_total`), que es sobre los que se volvera a correr
# `veredicto.py`.

# ── N1: M-B exige el 95 % de las horas que discriminan, y cinco de ellas ──
def _mb_horas(n_horas, n_piso, refs=REFS_DISCRIMINA, E=2.0, cortadas=0):
    """n_horas de «costo alternativa»; en n_piso reproduce la regla del piso,
    en el resto ninguna; las `cortadas` ultimas no llegan a teq 160."""
    bien = dict(dq=1e-6, dp=1e-3, dP=1e-5, dsj=1e-5)
    mal = dict(dq=1e-6, dp=1e-3, dP=0.3, dsj=0.3)
    fuera = []
    for h in range(n_horas):
        piso = bien if h < n_piso else mal
        teqs = ((0.0, 20.0, 40.0) if h >= n_horas - cortadas
                else (0.0, 80.0, 160.0))
        for k in (100.0, 1000.0):
            fuera.append(_registro(
                "M-B", "costo alternativa", "E4", f"h{h:02d}", k,
                "compradores_cortos", E,
                dict(cerrada=piso, costo=mal, llenado=mal), refs=refs,
                teqs=teqs))
    return fuera


def test_n1_mb_no_gana_con_2_de_30():
    """El ejemplo de la re-revision: la regla del piso reproduce 2 de 30 horas.
    Antes ganaba (era la que mas tenia); ahora no llega al 95 %."""
    texto = MB.veredicto(_mb_horas(30, 2))
    assert "ninguna regla alcanza el 95 %" in texto
    assert "gana" not in texto
    assert "30 discriminan" in texto
    assert "D64 NO se puede decidir" in texto


def test_n1_mb_pocas_horas_que_discriminan():
    """30 horas, pero solo 3 donde el piso y el costo despachan distinto: las
    otras 27 las reproducen las dos reglas a la vez y no deciden nada."""
    res = (_mb_horas(3, 3)
           + [r for r in _mb_horas(30, 30, refs=REFS_IGUALES)
              if r["spec"]["fecha"] >= "h03"])
    texto = MB.veredicto(res)
    assert "3 discriminan" in texto
    assert "muestra insuficiente: solo 3 horas discriminan" in texto


def test_n1_mb_gana_con_el_95_y_dice_lo_apartado_y_lo_cortado():
    res = _mb_horas(20, 20, cortadas=1)
    res[0]["recorte_movio"] = True                 # una corrida apartada
    res[1]["recorte_movio"] = True
    texto = MB.veredicto(res)
    # 19 horas (una apartada), 1 sin corrida en teq 160: 18 de 19 = 94,7 %.
    assert "1 apartadas" in texto and "1 sin ninguna corrida en teq 160" in texto
    assert "ninguna regla alcanza el 95 %" in texto
    texto = MB.veredicto(_mb_horas(20, 20))
    assert "con costo alternativa: gana piso (D64)" in texto


# ── N2: el denominador son las horas del regimen ───────────────────────────
def test_n2_las_horas_cortadas_cuentan_como_no_llega():
    """El ejemplo de la re-revision: 10 horas, 5 dentro y 5 cortadas. Antes
    salia «verificado (n = 5)»; ahora es regla declarada con n = 10."""
    bien = dict(dq=1e-5, dp=0.01, dP=1e-5, dsj=1e-5)
    res = []
    for h in range(10):
        teqs = (0.0, 80.0, 160.0) if h < 5 else (0.0, 20.0, 40.0)
        res.append(_registro("M-A", "V3a acelerada", "E0", f"h{h}", 100.0,
                             "interiores", 1.0, dict(cerrada=bien),
                             teqs=teqs))
    texto = V.tabla(res)
    assert "regla declarada (50 %, n = 10)" in texto
    assert "reposo verificado" not in texto


def test_n2_tambien_en_mb():
    texto = MB.veredicto(_mb_horas(10, 10, cortadas=5))
    assert "5 de 10" in texto            # la regla del piso: 5 de 10 horas
    assert "ninguna regla alcanza el 95 %" in texto


# ── N3: la medicion incompleta ─────────────────────────────────────────────
def test_n3_codigo_propio_y_faltantes():
    assert CM.CODIGO_INCOMPLETA == V.CODIGO_INCOMPLETA == 4
    assert CM.faltantes(8, {0, 1, 2}) == [3, 4, 5, 6, 7]
    assert CM.faltantes(8, set(range(8))) == []
    assert CM.faltantes(8, {5, 6, 7}, desde=5) == []


def _mg_hechos(indices, con_plan=False):
    d = dict(dq=0.0, dp=0.0, dP=0.0, dsj=0.0)
    fuera = []
    specs = MG.specs({})
    for n in indices:
        sp = specs[n]
        r = _registro("M-G", sp["familia"], sp["caso"], sp["fecha"],
                      sp["var"]["k_lento"], "topados", 1.381, dict(cerrada=d),
                      grupo=sp["grupo"])
        r["spec"]["etq"] = sp["etq"]
        if con_plan:
            r["plan_total"], r["plan_indice"] = len(specs), n
        fuera.append(r)
    return fuera


def test_n3_deduce_el_plan_de_una_noche_sin_plan_total(tmp_path):
    """La noche lanzada antes del arreglo no guarda `plan_total`: el plan se
    deduce del guion y de los ficheros de seleccion."""
    res = _mg_hechos([0, 1, 2])
    p = V.plan_de(res, tmp_path)
    assert (p["total"], p["hechas"]) == (8, 3) and "deducido" in p["fuente"]
    texto, incompleta = V.aviso_plan(res, tmp_path)
    assert incompleta and "MEDICION INCOMPLETA: 3 de 8" in texto
    assert "MEDICION INCOMPLETA: 3 de 8" in V.resume(res, tmp_path)
    # Completa: sin aviso.
    assert V.aviso_plan(_mg_hechos(range(8)), tmp_path)[1] is False


def test_n3_con_plan_total_guardado():
    res = _mg_hechos([0, 3, 5], con_plan=True)
    p = V.plan_de(res)
    assert (p["total"], p["hechas"]) == (8, 3) and "guardado" in p["fuente"]


def test_n3_el_plan_de_ma_sale_de_la_seleccion(tmp_path):
    """Para M-A el plan depende de la muestra: se lee de horas_<caso>.json."""
    import json as _json
    por_regimen = {g: [dict(fecha=f"2025-05-09 {h:02d}:00") for h in range(12)]
                   for g in MA.GRUPOS}
    (tmp_path / "horas_E0.json").write_text(_json.dumps(
        dict(caso="E0", por_regimen=por_regimen)), encoding="utf-8")
    plan = MA.specs({"E0": por_regimen})
    d = dict(dq=0.0, dp=0.0, dP=0.0, dsj=0.0)
    res = []
    for sp in plan[:7]:
        r = _registro("M-A", sp["familia"], sp["caso"], sp["fecha"],
                      sp["var"]["k_lento"], "interiores", 1.0,
                      dict(cerrada=d), grupo=sp["grupo"])
        r["spec"]["etq"] = sp["etq"]
        res.append(r)
    p = V.plan_de(res, tmp_path)
    assert (p["total"], p["hechas"]) == (len(plan), 7)


def test_n3_veredicto_sale_con_4_si_falta_algo(tmp_path):
    import json as _json
    f = tmp_path / "m_g_chacon.json"
    f.write_text(_json.dumps(_mg_hechos([0, 1, 2])), encoding="utf-8")
    assert V.main([str(f), "--salida", str(tmp_path / "v.txt")]) == 4
    assert "MEDICION INCOMPLETA: 3 de 8" in (tmp_path / "v.txt").read_text(
        encoding="utf-8")
    f.write_text(_json.dumps(_mg_hechos(range(8))), encoding="utf-8")
    assert V.main([str(f)]) == 0


# ── N4: M-E compara los tres mu de cada hora ───────────────────────────────
def _me(fecha, finales, quietos=(True, True, True)):
    d = dict(dq=0.0, dp=0.0, dP=0.0, dsj=0.0)
    fuera = []
    for mu, final, quieta in zip(ME.MUS, finales, quietos):
        fuera.append(_registro(
            "M-E", f"mu {mu:g}", "E0", fecha, 1000.0, "interiores", 2.0,
            dict(cerrada=d), var=dict(mu_ent=mu), quieta=quieta,
            final=dict(p=final[1], q=final[0], ppond=700.0, parte=0.5)))
    return fuera


def test_n4_me_compara_los_mu_entre_si():
    igual = ([1.0, 1.0], [700.0, 710.0])
    otro = ([1.5, 0.5], [700.0, 710.0])
    res = []
    for h in range(5):                           # cinco horas que coinciden
        res += _me(f"c{h}", [igual] * 3)
    res += _me("mueve", [igual, igual, otro])    # mu = 3 va a otro sitio
    res += _me("sin", [igual, igual, igual], quietos=(True, False, False))
    texto = ME.veredicto(res)
    assert "en 5 los mu que llegaron coinciden" in texto
    assert "en 1 el reposo CAMBIA con mu" in texto
    assert "MU MUEVE EL REPOSO E0 mueve" in texto
    assert "1 no se pueden comparar" in texto
    # Y la tabla generica de M-E no rotula (cada mu tiene n = 2 por grupo).
    assert "(ver el juicio propio)" in V.resume(res)


def test_n4_me_mu_solo_velocidad_con_cinco_horas():
    igual = ([1.0, 1.0], [700.0, 710.0])
    res = []
    for h in range(5):
        res += _me(f"c{h}", [igual] * 3)
    assert "mu solo cambia la velocidad" in ME.veredicto(res)


# ── N5: M-C y M-G solo con estados quietos ─────────────────────────────────
def test_n5_mc_moverse_no_es_multiplicidad():
    """Una oferta que en teq 160 todavia se mueve no cuenta: si el par sigma
    llego al mismo sitio, la hora esta en el MISMO sitio aunque el par medio no
    se comparara; si el par sigma no se comparo, la hora no se da por
    comparada (re-revision 4)."""
    a = ([1.0, 1.0], [700.0, 710.0])
    res = _cuatro("A", 2.0, a, a, medio_f=([1.9, 0.1], [700.0, 710.0]))
    for f in res[3]["filas"]:                  # medio + factible, lenta
        f["dq_dt"] = 0.5
    r = MC.entre_arranques(res[2:])
    assert not r["multiple"] and r["comparados"] == 1 and r["moviendose"] == 1
    texto = MC.veredicto(res)
    assert "1 con el par sigma en el MISMO sitio" in texto
    assert "precios medio: 0 con el par en el MISMO sitio, 0 en SITIOS "            "DISTINTOS y 1 sin el par comparado" in texto
    for c in (res[1], res[3]):                 # las dos factibles, lentas
        for f in c["filas"]:
            f["dq_dt"] = 0.5
    texto = MC.veredicto(res)
    assert "1 SIN EL PAR SIGMA COMPARADO" in texto
    assert "VARIOS REPOSOS" not in texto


def test_n5_mg_un_transitorio_no_se_lee_contra_la_tabla():
    reposo = dict(p=[833.3333, 833.3333, 833.3333, 1250.0, 1250.0],
                  q=[0.303667, 0.303667, 0.303667, 0.262, 0.208],
                  ppond=975.14, parte=0.758)
    d = dict(dq=0.0, dp=0.0, dP=0.0, dsj=0.0)
    res = [_registro("M-G", MG.BARRERA, "CHACON", "22", 100.0, "topados",
                     1.381, dict(cerrada=d), final=reposo, quieta=False)]
    texto = MG.veredicto(res)
    assert "todavia EN MOVIMIENTO" in texto
    assert "NO LLEGO" in texto and "CUMPLE" not in texto
    # El brazo de precio se juzga con lo que lee su tabla (re-revision 4): su
    # transitorio es de precios, no de reparto.
    res = [_registro("M-G", MG.PRECIO, "CHACON", "22", 100.0, "topados",
                     1.381, dict(cerrada=d), quieta=False,
                     final=dict(p=[114.0] * 5, q=[0.3] * 5, ppond=114.0,
                                parte=0.0))]
    for f in res[0]["filas"][1:]:
        f["dp_dt"] = 0.5
    assert "sin lectura: el brazo de precio no llego" in MG.veredicto(res)


# ═══════════════ re-revision 2 de 4c: NM1, NM2 y m-b ═════════════════════
_D0 = dict(dq=0.0, dp=0.0, dP=0.0, dsj=0.0)


def _lento(fecha="h", q80=(0.92, 1.08), q160=(1.0, 1.0), E=2.0,
           dq_dt=9e-4, medicion="M-C"):
    """Una corrida con las derivadas JUSTO BAJO 1e-3 en sus ultimos puntos,
    pero cuyo reparto todavia se mueve entre teq 80 y teq 160: el transitorio
    lento de la re-revision 2."""
    r = _registro(medicion, MC.FAMILIA, "E0", fecha, 100.0, "suma_no_cabe", E,
                  dict(cerrada=_D0),
                  final=dict(p=[700.0, 710.0], q=list(q160), ppond=700.0,
                             parte=0.4))
    r["filas"][1]["q"] = list(q80)
    for f in r["filas"][1:]:
        f["dq_dt"] = dq_dt
    return r


# ── NM1: la quietud compara el estado entre teq 80 y teq 160 ───────────────
def test_nm1_un_transitorio_lento_ya_no_esta_quieto():
    lento = _lento()
    assert all(f["dq_dt"] < 1e-3 for f in lento["filas"][-2:])
    quieta, motivo = V.quietud(lento)
    assert not quieta and "entre teq 80 y 160" in motivo
    # El mismo estado sin moverse entre 80 y 160 si esta quieto.
    assert V.esta_quieta(_lento(q80=(1.0, 1.0)))
    # Sin punto en teq 80 (el brazo k = 1 de M-G llega a teq 40): no se sabe.
    corto = _registro("M-G", MG.BARRERA, "CHACON", "22", 1.0, "topados", 1.381,
                      dict(cerrada=_D0), teqs=(0.0, 20.0, 40.0))
    quieta, motivo = V.quietud(corto)
    assert not quieta and "teq 80 y 160" in motivo


def test_nm1_en_mc_un_transitorio_lento_no_es_multiplicidad():
    """Tres arranques quietos en el mismo sitio y uno lento que acaba en otro:
    antes contaba como «varios reposos»; ahora no llego."""
    iguales = [_lento(q80=(1.0, 1.0)) for _ in range(3)]
    lento = _lento(q80=(1.3, 0.7), q160=(1.2, 0.8))
    r = MC.entre_arranques(iguales + [lento])
    assert not r["multiple"] and r["comparados"] == 3 and r["moviendose"] == 1


def test_nm1_en_me_un_mu_lento_no_mueve_el_reposo():
    igual = ([1.0, 1.0], [700.0, 710.0])
    res = _me("h", [igual] * 3)
    lento = res[2]                             # mu = 3, en otro sitio y lento
    lento["filas"][-1]["q"] = [1.2, 0.8]
    lento["filas"][1]["q"] = [1.3, 0.7]
    for f in lento["filas"][1:]:
        f["dq_dt"] = 9e-4
    texto = ME.veredicto(res)
    assert "MU MUEVE EL REPOSO" not in texto
    assert "(1 de las que coinciden lo hacen con solo dos mu" in texto


# ── NM2: al releer se recalcula con la tolerancia de hoy ───────────────────
def _guardado_con_tolerancia_floja(dq=0.1, E=2.0):
    """Una corrida de M-A cuyos indicadores se calcularon al correr con una
    tolerancia de reparto de 1e-1·E (dentro), y cuya distancia guardada es
    dq = 0,05·E: con la de hoy (1e-2·E, floja) queda fuera."""
    dist = dict(dq=dq, dp=0.01, dP=dq, dsj=dq)
    return _registro("M-A", "V3a acelerada", "E0", "h", 100.0, "interiores", E,
                     dict(cerrada=dist),
                     tol=dict(tol_q_rel=1e-1, tol_p=0.5, clase="de la noche",
                              motivo="prueba"))


def test_nm2_cambiar_la_tolerancia_cambia_el_veredicto_al_releer(monkeypatch):
    r = _guardado_con_tolerancia_floja()
    # Al correr, dentro.
    assert r["veredicto"]["cerrada"]["teq160"]["dentro"] is True
    # Al releer con la tolerancia de hoy (floja, 1e-2·E), fuera.
    c = V.cuenta_hora([r], "cerrada")
    assert c["juzgada"] and c["dentro"] is False and c["guardados"] == 0
    assert c["clases"] == ["floja"]
    # Si la tolerancia de hoy cambia, el veredicto releido cambia con ella.
    monkeypatch.setattr(PR, "TOL_Q_REL_FLOJA", 1e-1)
    assert V.cuenta_hora([r], "cerrada")["dentro"] is True


def test_nm2_sin_regimen_usa_el_indicador_guardado_y_lo_dice():
    r = _guardado_con_tolerancia_floja()
    del r["regimen"]
    j = V.rejuzga(r, "cerrada")
    assert j["fuente"].startswith("guardado") and j["dentro160"] is True
    assert "AVISO: en 1 juicios de corrida no se pudo recalcular" in V.tabla([r])


def test_nm2_el_criterio_de_consenso_tambien_se_recalcula(monkeypatch):
    bien = dict(dq=1e-5, dp=0.01, dP=1e-5, dsj=1e-5)
    r = _registro("M-A", "V3a acelerada", "E0", "h", 100.0, "interiores", 1.0,
                  dict(cerrada=bien))
    assert V.rejuzga(r, "cerrada")["llega"] is True
    # Un criterio de hoy mas exigente (ninguna derivada queda bajo cero) se
    # recoge al releer. Se cambia la funcion y no la constante, porque la
    # constante entra como argumento por defecto al definirse.
    original = PR.criterio_consenso
    monkeypatch.setattr(PR, "criterio_consenso",
                        lambda filas, nombre, E, tol: original(
                            filas, nombre, E, tol, tol_derivada=0.0))
    assert V.rejuzga(r, "cerrada")["llega"] is False


# ── m-b: una hora cuyas corridas fallaron todas cuenta como «falla» ────────
def _falla(medicion, familia, fecha, caso="E0", grupo="interiores", k=100.0,
           referencias=None):
    return dict(spec=dict(medicion=medicion, familia=familia, caso=caso,
                          fecha=fecha, grupo=grupo, etq=f"{familia} k{k:g}",
                          var=dict(k_lento=k), referencias=referencias or {}),
                msg="FALLA RuntimeError: prueba", filas=[], veredicto={},
                cerrada={}, seg=0.0)


def test_mb_una_hora_toda_fallida_cuenta_en_el_denominador():
    bien = dict(dq=1e-5, dp=0.01, dP=1e-5, dsj=1e-5)
    res = [_registro("M-A", "V3a acelerada", "E0", f"b{h}", 100.0,
                     "interiores", 1.0, dict(cerrada=bien), grupo="interiores")
           for h in range(5)]
    res += [_falla("M-A", "V3a acelerada", f"f{h}") for h in range(5)]
    horas = {"E0": {"interiores": [dict(fecha=f"f{h}", regimen="interiores")
                                   for h in range(5)]}}
    texto = V.tabla(res, horas=horas)
    # Antes: las fallidas salian y el rotulo era «verificado (n = 5)».
    assert "regla declarada (50 %, n = 10)" in texto
    assert "reposo verificado" not in texto
    grupos, _ = V.agrupa(res, horas)
    (clave, hs), = grupos.items()
    assert clave[0] == "interiores"
    assert sum(V.cuenta_hora(c, "cerrada")["falla"] for c in hs.values()) == 5
    # Sin la seleccion no se sabe su regimen: salen aparte, como «?».
    grupos, _ = V.agrupa(res)
    assert {k[0] for k in grupos} == {"interiores", "?"}


def test_mb_las_fallidas_tambien_en_los_juicios_propios():
    iguales = _cuatro("A", 2.0, ([1.0, 1.0], [700.0, 710.0]),
                      ([1.0, 1.0], [700.0, 710.0]))
    fallida = [_falla("M-C", MC.FAMILIA, "Z", grupo="suma_no_cabe")
               for _ in range(4)]
    texto = MC.veredicto(iguales + fallida)
    assert "2 horas" in texto and "1 FALLARON en todas sus corridas" in texto
    assert "1 que fallaron" in texto          # tambien frente a la forma cerrada
    mb = _mb_horas(6, 6) + [_falla("M-B", "costo alternativa", "zz", caso="E4")]
    texto = MB.veredicto(mb)
    assert "7 horas" in texto and "1 con todas sus corridas FALLIDAS" in texto
    me = _me("h", [([1.0, 1.0], [700.0, 710.0])] * 3)
    me += [_falla("M-E", f"mu {mu:g}", "rota") for mu in ME.MUS]
    assert "1 FALLARON en todos sus mu" in ME.veredicto(me)
    mg = [_falla("M-G", MG.BARRERA, "22", caso="CHACON", grupo="chacon")]
    assert "NO LLEGO: fallaron todos sus brazos" in MG.veredicto(mg)


# ═══════════════ re-revision 3 de 4c: M-C por arranque de precios, M-G ═════
def test_rr3_mc_dos_presupuestos_no_son_multiplicidad():
    """Los dos arranques de precios quietos en sitios distintos, con sus dos
    ofertas de acuerdo dentro de cada uno: NO es multiplicidad; sale como
    dependencia del presupuesto (H-90), con la diferencia de la suma y el
    cambio de regimen (el comprador 2 recibe energia con precios medios)."""
    sigma = ([1.0, 0.0], [700.0, 710.0])       # comprador 2 sin energia
    medio = ([0.6, 0.4], [690.0, 695.0])       # «cabe»: los dos reciben
    res = []
    for h in range(5):
        res += _cuatro(f"h{h}", 1.0, sigma, medio)
    texto = MC.veredicto(res)
    assert "5 con el par sigma en el MISMO sitio; 0 en SITIOS DISTINTOS" in texto
    assert "precios sigma: 5 con el par en el MISMO sitio" in texto
    assert "precios medio: 5 con el par en el MISMO sitio" in texto
    assert "DECLARADA por multiplicidad" not in texto
    assert "DEPENDENCIA DEL PRESUPUESTO" in texto
    assert "-25.00 (COP/kWh) de media" in texto
    assert "5 horas CAMBIAN DE REGIMEN" in texto
    # Y los sigma estan en la forma cerrada: la regla es el reposo.
    assert "reposo verificado (n = 5)" in texto
    assert "D53: la regla del paso 5 es el reposo al que llega" in texto
    # La tabla generica no rotula M-C.
    assert "(ver el juicio propio)" in V.resume(res)


def test_rr3_mc_ofertas_distintas_en_un_arranque_si_es_multiplicidad():
    a = ([1.0, 0.0], [700.0, 710.0])
    b = ([0.7, 0.3], [700.0, 710.0])
    res = _cuatro("h", 1.0, a, a, medio_f=b)   # dentro de «medio», discrepan
    texto = MC.veredicto(res)
    assert "1 en SITIOS DISTINTOS" in texto
    assert "VARIOS REPOSOS E0 h (precios medio)" in texto
    assert "D53: la regla del paso 5 se publica como DECLARADA por " \
           "multiplicidad" in texto


def test_rr3_mc_sigma_frente_a_la_forma_cerrada_con_todas_las_horas():
    """El denominador son todas las horas: 5 dentro, 1 que no llega (sus
    sigma cortadas) y 1 que fallo entera dan 5 de 7."""
    a = ([1.0, 0.0], [700.0, 710.0])
    res = []
    for h in range(5):
        res += _cuatro(f"h{h}", 1.0, a, a)
    corta = _cuatro("corta", 1.0, a, a)
    for c in corta[:2]:
        c.update(_arranque("corta", 1.0, *a, cortada=True))
    res += corta
    res += [_falla("M-C", MC.FAMILIA, "rota", grupo="suma_no_cabe")]
    texto = MC.veredicto(res)
    assert "7 horas (el denominador): 5 dentro" in texto
    assert "1 que no llegan a teq 160 y 1 que fallaron" in texto
    assert "regla declarada (71 %, n = 7)" in texto


def _brazo_k1(final, q20=None):
    """El brazo k = 1 de M-G tal como lo escribe la noche: sus cortes acaban
    en teq 40 POR DISEÑO y termino con «ok»."""
    r = _registro("M-G", MG.BARRERA, "CHACON", "22", 1.0, "topados", 1.381,
                  dict(cerrada=_D0), teqs=(0.0, 20.0, 40.0), final=final)
    r["spec"]["cortes"] = list(MG.CORTES[1.0])
    r["cortada"], r["msg"] = False, "ok"
    if q20 is not None:
        r["filas"][1]["q"] = list(q20)
    return r


_REPOSO_22 = dict(p=[833.3333, 833.3333, 833.3333, 1250.0, 1250.0],
                  q=[0.303667, 0.303667, 0.303667, 0.262, 0.208],
                  ppond=975.14, parte=0.758)


def test_rr3_mg_el_brazo_k1_quieto_en_20_y_40_se_lee():
    r = _brazo_k1(_REPOSO_22)
    quieta, motivo = V.quietud(r, MG.tolerancia_quietud("22", MG.BARRERA))
    assert quieta and "entre teq 20 y 40" in motivo
    texto = MG.veredicto([r])
    assert "CUMPLE  precios 833,3 x 3 y 1 250 x 2" in texto
    assert "con el brazo k = 1" in texto and "NO LLEGO" not in texto
    # En M-A, M-C y M-E nada cambia: sus cortes llegan a 160 y se usan 80 y 160.
    assert V.teq_final_del_plan(r) == 40.0
    lento = _lento()
    lento["spec"]["cortes"] = list(MC.CORTES)
    assert V.teq_final_del_plan(lento) == pytest.approx(160.0)
    assert "entre teq 80 y 160" in V.quietud(lento)[1]


def test_rr3_mg_un_reparto_que_deriva_0_01_no_esta_quieto():
    """Con la tolerancia de la tabla (+-1e-3 (kWh)) un reparto que todavia se
    mueve 0,01 (kWh) no esta quieto. Con la floja de M-A (1e-2·E = 0,0138
    (kWh) aqui) si lo habria estado: es el menor de la re-revision 3."""
    deriva = [x + 0.01 for x in _REPOSO_22["q"]]
    r = _registro("M-G", MG.BARRERA, "CHACON", "22", 100.0, "topados", 1.381,
                  dict(cerrada=_D0), final=_REPOSO_22)
    r["filas"][1]["q"] = deriva                   # teq 80
    assert V.quietud(r)[0] is True                # con la floja de M-A
    tol = MG.tolerancia_quietud("22", MG.BARRERA)
    assert tol["magnitudes"] == {"p": 0.5, "q": 1e-3, "parte": 0.005}
    quieta, motivo = V.quietud(r, tol)
    assert not quieta and "EN MOVIMIENTO entre teq 80 y 160" in motivo
    assert "NO LLEGO" in MG.veredicto([r])
    # El brazo k = 1 con la misma deriva entre 20 y 40, tampoco.
    k1 = _brazo_k1(_REPOSO_22, q20=deriva)
    assert not V.quietud(k1, tol)[0]


# ═══════════════ re-revision 4 de 4c: el par sigma y M-G por magnitudes ════
def _sigma_cortada(fecha, E=1.2):
    """La oferta «factible + sigma» cortada por el tope en teq 5, lejos de la
    regla 0,4 x 3, como en la sintetica con techos distintos de la
    re-revision 4."""
    r = _registro("M-C", MC.FAMILIA, "E0", fecha, 100.0, "suma_no_cabe", E,
                  dict(cerrada=_D0), teqs=(0.0, 2.0, 5.0),
                  final=dict(p=[700.0, 705.0, 710.0], q=[0.065, 0.536, 0.600],
                             ppond=700.0, parte=0.4),
                  var=dict(arranque="factible"))
    r["spec"]["nivel"] = "sigma"
    r["spec"]["etq"] = "oferta factible + precios sigma"
    return r


def test_rr4_mc_una_oferta_sigma_cortada_no_verifica_la_hora():
    """Cinco horas con la oferta iguales + sigma dentro y la factible + sigma
    cortada en teq 5: antes salian «reposo verificado (n = 5)» con una sola
    oferta, y «MISMO sitio» por el par medio. Ahora no llegan."""
    regla = ([0.4, 0.4, 0.4], [700.0, 705.0, 710.0])
    res = []
    for h in range(5):
        cuatro = _cuatro(f"h{h}", 1.2, regla, regla)
        cuatro[1] = _sigma_cortada(f"h{h}")
        res += cuatro
    est = MC.contra_la_forma_cerrada([c for c in res if c["spec"]["fecha"]
                                      == "h0"])
    assert est["estado"] == "no llega" and est["una_sola"]
    assert est["una_sola_dentro"]
    assert est["ofertas"]["factible"]["estado"] == "no llega"
    texto = MC.veredicto(res)
    # Parte 2: ninguna hora dentro; las cinco, con una sola oferta.
    assert "5 horas (el denominador): 0 dentro" in texto
    assert "5 que no llegan a teq 160 y 0 que fallaron" in texto
    assert "5 horas con UNA SOLA oferta sigma en teq 160" in texto
    assert "5 de ellas con esa oferta dentro" in texto
    assert "reposo verificado" not in texto
    assert "regla declarada (0 %, n = 5)" in texto
    # Re-revision final (menor 1): ninguna juzgada queda fuera, de modo que
    # no es que la dinamica vaya a otro sitio, sino que no se pudo verificar.
    assert "D53: la regla del paso 5 se publica como DECLARADA: no se pudo " \
           "verificar: 5 horas no llegan y 0 fallan" in texto
    assert "no la alcanza" not in texto
    # Parte 1: el par medio coincide, pero la hora no suma como MISMO sitio.
    assert "0 con el par sigma en el MISMO sitio" in texto
    assert "5 SIN EL PAR SIGMA COMPARADO" in texto
    assert "precios sigma: 0 con el par en el MISMO sitio, 0 en SITIOS " \
           "DISTINTOS y 5 sin el par comparado" in texto
    assert "precios medio: 5 con el par en el MISMO sitio" in texto
    assert "5 horas sin el par sigma comparado tienen el par medio en el " \
           "mismo sitio: NO cuentan como MISMO sitio" in texto
    assert "VARIOS REPOSOS" not in texto
    # Si la oferta en vez de cortarse falla, la hora es «falla».
    rota = _cuatro("r", 1.2, regla, regla)
    rota[1] = _falla("M-C", MC.FAMILIA, "r", grupo="suma_no_cabe")
    rota[1]["spec"].update(nivel="sigma")
    rota[1]["spec"]["var"]["arranque"] = "factible"
    est = MC.contra_la_forma_cerrada(rota)
    assert est["estado"] == "falla" and est["una_sola"]
    texto = MC.veredicto(rota)
    assert "1 horas (el denominador): 0 dentro" in texto
    assert "0 que no llegan a teq 160 y 1 que fallaron" in texto
    # Y si la oferta ni se corrio, tampoco hay par.
    est = MC.contra_la_forma_cerrada([c for i, c in enumerate(rota) if i != 1])
    assert est["estado"] == "no llega"
    assert est["ofertas"]["factible"]["estado"] == "falta"


def test_rr4_mc_las_dos_ofertas_sigma_dentro_verifican_como_hoy():
    regla = ([0.4, 0.4, 0.4], [700.0, 705.0, 710.0])
    res = []
    for h in range(5):
        res += _cuatro(f"h{h}", 1.2, regla, regla)
    est = MC.contra_la_forma_cerrada(res[:4])
    assert est["estado"] == "juzgada" and est["dentro"] and not est["una_sola"]
    texto = MC.veredicto(res)
    assert "5 horas (el denominador): 5 dentro en teq 80 y 160 con LAS DOS " \
           "ofertas sigma" in texto
    assert "0 horas con UNA SOLA oferta sigma" in texto
    assert "reposo verificado (n = 5)" in texto
    assert "5 con el par sigma en el MISMO sitio" in texto
    assert "D53: la regla del paso 5 es el reposo al que llega" in texto


# El reparto que todavia converge como 1/t con c = 0,25: entre teq 80 y 160 se
# mueve 0,25/80 - 0,25/160 = 1,5625e-3 (kWh), y su derivada en teq 160 es
# 0,25/160^2 = 9,8e-6, bajo 1e-3.
_C_LENTO = 0.25


def _q_lento(q_inf, teq):
    """q_inf mas c/teq en el primer comprador y menos en el segundo (la
    energia se conserva)."""
    q = list(q_inf)
    q[0] += _C_LENTO / teq
    q[1] -= _C_LENTO / teq
    return q


def _con_reparto_lento(r, q_inf):
    for f in r["filas"][1:]:
        f["q"] = _q_lento(q_inf, f["teq"])
        f["dq_dt"] = _C_LENTO / f["teq"] ** 2
    return r


def test_rr4_mg_brazo_de_precio_en_el_piso_con_reparto_lento_se_lee_b():
    q_inf = [0.2762] * 5
    r = _registro("M-G", MG.PRECIO, "CHACON", "22", 100.0, "topados", 1.381,
                  dict(cerrada=_D0),
                  final=dict(p=[114.0] * 5, q=q_inf, ppond=114.0, parte=0.0))
    _con_reparto_lento(r, q_inf)
    f80, f160 = r["filas"][1], r["filas"][2]
    assert max(abs(a - b) for a, b in zip(f80["q"], f160["q"])) \
        == pytest.approx(1.5625e-3)
    assert f160["dq_dt"] < 1e-3
    tol = MG.tolerancia_quietud("22", MG.PRECIO)
    # Re-revision final (menor 2): (b) lee tambien cada precio, con +-1.
    assert tol["magnitudes"] == {"ppond": 1.0, "parte": 0.002, "p": 1.0}
    quieta, motivo = V.quietud(r, tol)
    assert quieta and "entre teq 80 y 160" in motivo
    # Con la tolerancia de la ronda 4 (+-1e-3 (kWh) en el reparto) no lo estaba.
    assert not V.quietud(r, dict(tol_q_abs=1e-3, tol_p=1.0))[0]
    texto = MG.veredicto([r])
    assert "=> se cumple la lectura (b)" in texto and "NO LLEGO" not in texto
    # Pero si el nivel ponderado todavia se mueve mas de 1 (COP/kWh), no.
    r["filas"][1]["ppond"] = 116.0
    quieta, motivo = V.quietud(r, tol)
    assert not quieta and "EN MOVIMIENTO entre teq 80 y 160" in motivo
    assert "sin lectura: el brazo de precio no llego" in MG.veredicto([r])


def test_rr4_mg_brazo_de_barrera_con_el_mismo_reparto_lento_no_esta_quieto():
    r = _registro("M-G", MG.BARRERA, "CHACON", "22", 100.0, "topados", 1.381,
                  dict(cerrada=_D0), final=_REPOSO_22)
    _con_reparto_lento(r, _REPOSO_22["q"])
    tol = MG.tolerancia_quietud("22", MG.BARRERA)
    quieta, motivo = V.quietud(r, tol)
    assert not quieta and "EN MOVIMIENTO entre teq 80 y 160" in motivo
    assert "|dq| = 1.56e-03 (kWh)" in motivo
    texto = MG.veredicto([r])
    assert "NO LLEGO" in texto and "CUMPLE" not in texto
    # Sin tolerancia por magnitudes (M-A, M-C, M-E) todo sigue como antes.
    assert V.quietud(r, dict(tol_q_abs=1e-3, tol_p=0.5))[0] is False
    assert V.quietud(r, dict(tol_q_abs=2e-3, tol_p=0.5))[0] is True


def test_rrf_mg_b_exige_todos_los_precios_en_el_piso():
    """Re-revision final de 4c (menor 2): el nivel y la parte van ponderados por
    energia. Un comprador quieto en 300 (COP/kWh) que recibe 0,001 (kWh) deja
    el nivel en 114,135 y la parte en 1,2e-4, dentro de sus tolerancias; la
    fila de cada precio impide que eso se lea como «todos en el piso»."""
    r = _registro("M-G", MG.PRECIO, "CHACON", "22", 100.0, "topados", 1.381,
                  dict(cerrada=_D0),
                  final=dict(p=[300.0] + [114.0] * 4, q=[0.2762] * 5,
                             ppond=114.135, parte=1.2e-4))
    juicio = MG.juzga_fila(r["filas"][-1], MG.ESPERADO[("22", MG.PRECIO)])
    por_texto = {j["texto"]: j["cumple"] for j in juicio}
    assert por_texto["(b) todos en el piso: nivel 114"]
    assert por_texto["(b) todos en el piso: parte 0"]
    assert not por_texto["(b) todos en el piso: cada precio en 114"]
    assert "lectura (b)" not in MG.lectura(juicio)
