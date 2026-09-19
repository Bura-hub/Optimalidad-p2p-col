"""
El nucleo del reposo en forma cerrada (`core/reposo_mercado.py`; D48 a D55,
D61 y D63 a D69; especificacion en `fable-report.md` sec. 5.1). 2026-09-16, con
la ronda de arreglos de la revision de la tarea 1 (2026-09-17) y la tarea 5a
(2026-09-17): el piso del juego es el del vendedor marginal (D63), los
vendedores despachan por su piso (D64) y una caminata competitiva decide quien
entra (D65). Los valores esperados de las pruebas nuevas son los de
`.superpowers/sdd/2026-09-16-reposo/fable-retiro-report.md` (sec. 6 y 7).

QUE CAMBIO CON D63 EN LAS HORAS REALES. Con `despacho_vendedores="piso"` (el
defecto) las once horas 853, 874, 2120, 3804, 3086, 877, 12, 58, 540, 226 y 4766
dan lo mismo AL BIT que con el nucleo de antes y el merito (comprobado en los
cuatro pares de presupuesto sigma o c136 y liquidacion uniforme o puja): tienen
un solo vendedor, pisos iguales, o (4766) el vendedor de piso menor es tambien
el de costo menor y cubre la demanda. Con "costo" tambien son identicas, E4-133
incluida (despacha solo Cesmag y el maximo y el minimo de un vendedor son el
mismo). Cambian por la regla, y se reescribieron:
  - E4-133 con "piso": vende Udenar, el de piso menor, a 147,46; antes vendia
    Cesmag a 330,15 por tener el b menor (H-89);
  - E0-4766 y E4-133 con "llenado": despachan todos, y el piso del juego pasa
    del minimo al maximo de sus pisos (677,28 y 415,10), con la parte del
    vendedor positiva (antes -0,262 y -0,441, que corregia la participacion).
Las pruebas de D62 (`test_d62_*`) se reescribieron con la regla nueva, y las de
merito por costo pasan a pedir `despacho_vendedores="costo"` de forma
explicita.

SIN DATOS REALES. Las entradas de las horas reales son literales hexadecimales
(`float.fromhex`), identicos al bit en cualquier maquina. Se sacaron una sola
vez de los almacenes de la matriz del 2026-09-15 (en
`SALIDAS_SERVIDOR/entrega_matriz_2026-09-15/SALIDAS_SERVIDOR/matriz/`, la
tabla `<caso>/almacen/m1/agentes`): compradores, papel «comprador» con
faltante > 0; `piso_j` de cada vendedor; `b` de `data/xm_prices.py`
(`get_b_for_real_data`, 241,07 salvo Cesmag, 225).
Dos recetas para los vendedores:
  - las nueve horas de E0 de la primera entrega (853, 874, 2120, 3804, 3086,
    877, 12, 58 y 540): papel «vendedor» con sobrante > 0, es decir, el
    conjunto que quedo DESPUES del retiro de la corrida vieja (solo la 58
    tenia retirados);
  - las horas de la ronda de arreglos (E0 4766 y 226; E4 133, 5631 y 5632):
    papel «vendedor» o «retirado» con sobrante > 0, es decir, CON los
    retirados, que es lo que recibira el motor antes de su participacion.
Las claves enteras son horas de E0; las de texto llevan el caso. Su huella
SHA-256 (s, d, b, techo, piso_j de cada hora, en float64 y en el orden de
HORAS) se comprueba antes de usarlos.
Los guiones que los generaron estan en el repositorio, en `tests/literales/`
(ver su README.md): `genera_literales.py` (las nueve horas de E0),
`literales_ronda1.py` (las cinco de la ronda de arreglos) y
`verifica_huella.py`, que los compara al bit con los almacenes y da la huella
vigente.

Las horas 3086 y 877 son del regimen «la suma no cabe sobre el piso». Se
prueban con la regla del paso 5 de la sec. 5.1, que conserva la suma de precios
y reproduce los promedios de la dinamica de
`scratchpad/evaluador2/valida_reposo_E0.log` (horas 540 y 3086, abajo). Los
esperados que traia el encargo para esas dos horas salian de un segundo lazo
del prototipo y se retiraron (decision del controlador tras la revision).

LA RAMA CUANTAL (D71, tarea Q, 2026-09-19). En las horas fragiles el nucleo
publica el reposo con mu = 1 (regimen «cuantal»); de los literales, solo la
hora 12 con el presupuesto sigma. Las aserciones de antes de la hora 12 se
conservan sin cambiar un caracter con `mu_cuantal=0.0`, y las nuevas son los
esperados de la sec. 6 de `.superpowers/sdd/2026-09-16-reposo/
diseno-rama-cuantal.md`. `test_identidades` y las horas al azar comprueban que
en toda hora no fragil los campos de antes son identicos al bit con la rama
encendida y apagada, y las identidades de la sec. 4 en las fragiles.

Grupos:
  - la huella de los literales;
  - las horas reales de E0 y la evidencia de la dinamica;
  - horas reales de compradores cortos (despacho por piso, por costo y por
    llenado), de un comprador, sin ganancia (D61) y del piso marginal (D63);
  - sinteticos: sigma = 0, un comprador, bandas iguales, b distintos con
    vendedores cortos y con compradores cortos, multiplicidad anotada, D61
    parcial, D63, H-32 con «c136», guardas de `_comprueba`;
  - la regla del piso marginal (D63 a D69) con los ejemplos de Fable: S1, S2,
    cruce de cotas, empate de volumen, continuidad, el lazo que oscila con
    "costo", las guardas nuevas de `_comprueba` y el teorema de cobertura en
    2 000 horas sinteticas;
  - identidades sobre todas las horas y variantes;
  - entradas invalidas, sin mercado, presupuesto, cotas;
  - el caso de Chacon 22:00 con el Algoritmo 3.
"""
from __future__ import annotations

import dataclasses
import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import core.reposo_mercado as RM  # noqa: E402
from core.reposo_mercado import (  # noqa: E402
    DESPACHOS_VENDEDORES, MU_CUANTAL, REGIMENES, TOL_FRAGIL_REL,
    DespachoHora, ReposoHora, captura, cotas_optimalidad,
    despacho_competitivo, ingreso_por_vendedor, presupuesto_precios,
    resuelve_reposo)

TOL_P = 0.01      # precios (COP/kWh)
TOL_Q = 1e-3      # energias (kWh)
TOL_PARTE = 1e-3  # parte del vendedor, dada con tres decimales


# ─── las horas reales de E0, al bit ────────────────────────────────────────

HORAS = {
    # 2025-05-09 13:00; vende Udenar; compran Mariana, UCC, HUDN, Cesmag
    853: dict(
        vendedores=["Udenar"], compradores=["Mariana", "UCC", "HUDN", "Cesmag"],
        s=["0x1.3583a60000000p+0"],
        d=["0x1.e278f80000000p+2", "0x1.a7f9720000000p+4",
           "0x1.6ca94e0000000p+2", "0x1.169ad40000000p+3"],
        b=["0x1.e224924924924p+7"],
        techo=["0x1.6d903a0000000p+9", "0x1.6d903a0000000p+9",
               "0x1.6d903a0000000p+9", "0x1.8495c20000000p+9"],
        piso_j=["0x1.5a58b40000000p+9"]),
    # 2025-05-10 10:00; vende Udenar; compran Mariana, UCC, HUDN, Cesmag
    874: dict(
        vendedores=["Udenar"], compradores=["Mariana", "UCC", "HUDN", "Cesmag"],
        s=["0x1.0c55860000000p+3"],
        d=["0x1.7bb75e0000000p-1", "0x1.2ed1fc0000000p+4",
           "0x1.5ed5d00000000p+2", "0x1.88fa220000000p+0"],
        b=["0x1.e224924924924p+7"],
        techo=["0x1.6d903a0000000p+9", "0x1.6d903a0000000p+9",
               "0x1.6d903a0000000p+9", "0x1.8495c20000000p+9"],
        piso_j=["0x1.5a58b40000000p+9"]),
    # 2025-07-01 08:00; vende Udenar; compran Mariana, UCC, HUDN, Cesmag
    2120: dict(
        vendedores=["Udenar"], compradores=["Mariana", "UCC", "HUDN", "Cesmag"],
        s=["0x1.3178920000000p+1"],
        d=["0x1.415e9e0000000p+2", "0x1.1935ee0000000p+4",
           "0x1.e5cac00000000p+2", "0x1.3a39120000000p+1"],
        b=["0x1.e224924924924p+7"],
        techo=["0x1.5fd0860000000p+9", "0x1.5fd0860000000p+9",
               "0x1.5fd0860000000p+9", "0x1.97747a0000000p+9"],
        piso_j=["0x1.4d014e0000000p+9"]),
    # 2025-09-09 12:00; vende HUDN; compran Udenar, Mariana, UCC, Cesmag
    3804: dict(
        vendedores=["HUDN"], compradores=["Udenar", "Mariana", "UCC", "Cesmag"],
        s=["0x1.3719880000000p+2"],
        d=["0x1.c2124c0000000p+2", "0x1.be6bdc0000000p+2",
           "0x1.3b7ee80000000p+5", "0x1.9d30be0000000p+2"],
        b=["0x1.e224924924924p+7"],
        techo=["0x1.6391420000000p+9", "0x1.6391420000000p+9",
               "0x1.6391420000000p+9", "0x1.8ef8520000000p+9"],
        piso_j=["0x1.50b3920000000p+9"]),
    # 2025-08-10 14:00; vende Udenar; compran Mariana, UCC, HUDN, Cesmag
    3086: dict(
        vendedores=["Udenar"], compradores=["Mariana", "UCC", "HUDN", "Cesmag"],
        s=["0x1.39d6780000000p+3"],
        d=["0x1.3b7e900000000p-1", "0x1.55f0700000000p+3",
           "0x1.d1fd000000000p-1", "0x1.acd58a0000000p-1"],
        b=["0x1.e224924924924p+7"],
        techo=["0x1.6b74ca0000000p+9", "0x1.6b74ca0000000p+9",
               "0x1.6b74ca0000000p+9", "0x1.987d700000000p+9"],
        piso_j=["0x1.582ee00000000p+9"]),
    # 2025-05-10 13:00; venden Udenar y Mariana; compran UCC, HUDN, Cesmag
    877: dict(
        vendedores=["Udenar", "Mariana"], compradores=["UCC", "HUDN", "Cesmag"],
        s=["0x1.f9f6ce0000000p+2", "0x1.37ca7a0000000p-1"],
        d=["0x1.adf1880000000p+2", "0x1.c0bbde0000000p+0",
           "0x1.bcfaac0000000p+0"],
        b=["0x1.e224924924924p+7", "0x1.e224924924924p+7"],
        techo=["0x1.6d903a0000000p+9", "0x1.6d903a0000000p+9",
               "0x1.8495c20000000p+9"],
        piso_j=["0x1.5a58b40000000p+9", "0x1.5a58b40000000p+9"]),
    # 2025-04-04 12:00; venden Udenar y HUDN; compran Mariana, UCC, Cesmag
    12: dict(
        vendedores=["Udenar", "HUDN"], compradores=["Mariana", "UCC", "Cesmag"],
        s=["0x1.420e040000000p+2", "0x1.b32a760000000p+0"],
        d=["0x1.e35b9e0000000p+1", "0x1.36c5fa0000000p+5",
           "0x1.08c5280000000p+3"],
        b=["0x1.e224924924924p+7", "0x1.e224924924924p+7"],
        techo=["0x1.6f26800000000p+9", "0x1.6f26800000000p+9",
               "0x1.8d4f5c0000000p+9"],
        piso_j=["0x1.5bd72e0000000p+9", "0x1.5bd72e0000000p+9"]),
    # 2025-04-06 10:00; vende Cesmag; compran UCC y HUDN. Literales POSTERIORES
    # al retiro de la corrida vieja: Udenar y Mariana estaban retirados y no
    # entran (receta de la primera entrega).
    58: dict(
        vendedores=["Cesmag"], compradores=["UCC", "HUDN"],
        s=["0x1.9226800000000p+0"],
        d=["0x1.6b8f800000000p+3", "0x1.b9675c0000000p+0"],
        b=["0x1.c200000000000p+7"],
        techo=["0x1.6f26800000000p+9", "0x1.6f26800000000p+9"],
        piso_j=["0x1.35f70a0000000p+9"]),
    # 2025-04-26 12:00; vende Udenar; compran Mariana, UCC, HUDN, Cesmag.
    # No es del encargo: es la evidencia de la dinamica para el paso 5.
    540: dict(
        vendedores=["Udenar"], compradores=["Mariana", "UCC", "HUDN", "Cesmag"],
        s=["0x1.eb6f560000000p+2"],
        d=["0x1.21da0c0000000p+0", "0x1.565daa0000000p+3",
           "0x1.0abc240000000p+1", "0x1.9182aa0000000p-2"],
        b=["0x1.e224924924924p+7"],
        techo=["0x1.6f26800000000p+9", "0x1.6f26800000000p+9",
               "0x1.6f26800000000p+9", "0x1.8d4f5c0000000p+9"],
        piso_j=["0x1.5bd72e0000000p+9"]),
    # 2025-10-19 14:00; venden Udenar (retirado), HUDN (retirado) y Cesmag;
    # compran Mariana y UCC. Compradores cortos con Cesmag vendiendo.
    4766: dict(
        vendedores=["Udenar", "HUDN", "Cesmag"], compradores=["Mariana", "UCC"],
        s=["0x1.c6c6840000000p+1", "0x1.1ff7440000000p+0",
           "0x1.0f6a5c0000000p+2"],
        d=["0x1.bfe5ca0000000p-2", "0x1.48f7f20000000p+0"],
        b=["0x1.e224924924924p+7", "0x1.e224924924924p+7",
           "0x1.c200000000000p+7"],
        techo=["0x1.65cf600000000p+9", "0x1.65cf600000000p+9"],
        piso_j=["0x1.52a4320000000p+9", "0x1.52a4320000000p+9",
                "0x1.343ae20000000p+9"]),
    # 2025-04-13 10:00; venden Udenar, Mariana, UCC y HUDN; compra Cesmag.
    226: dict(
        vendedores=["Udenar", "Mariana", "UCC", "HUDN"], compradores=["Cesmag"],
        s=["0x1.4761760000000p+3", "0x1.2571bc0000000p+0",
           "0x1.5236e20000000p+1", "0x1.0f16420000000p+2"],
        d=["0x1.17c61c0000000p+1"],
        b=["0x1.e224924924924p+7", "0x1.e224924924924p+7",
           "0x1.e224924924924p+7", "0x1.e224924924924p+7"],
        techo=["0x1.8d4f5c0000000p+9"],
        piso_j=["0x1.5bd72e0000000p+9", "0x1.5bd72e0000000p+9",
                "0x1.5bd72e0000000p+9", "0x1.5bd72e0000000p+9"]),
    # E4, 2025-04-09 13:00; venden Udenar, Mariana (retirado), HUDN (retirado)
    # y Cesmag (retirado); compra UCC. El riesgo 5 de la revision.
    "E4-133": dict(
        vendedores=["Udenar", "Mariana", "HUDN", "Cesmag"], compradores=["UCC"],
        s=["0x1.9569e00000000p+4", "0x1.78323e0000000p+1",
           "0x1.1624cc0000000p+5", "0x1.b38b200000000p+2"],
        d=["0x1.0c50d40000000p+2"],
        b=["0x1.e224924924924p+7", "0x1.e224924924924p+7",
           "0x1.e224924924924p+7", "0x1.c200000000000p+7"],
        techo=["0x1.6f26800000000p+9"],
        piso_j=["0x1.26eb860000000p+7", "0x1.9f19e20000000p+8",
                "0x1.9f19e20000000p+8", "0x1.4a26660000000p+8"]),
    # E4, 2025-11-24 15:00; venden Mariana, HUDN y Cesmag; compran Udenar y UCC.
    "E4-5631": dict(
        vendedores=["Mariana", "HUDN", "Cesmag"], compradores=["Udenar", "UCC"],
        s=["0x1.778c380000000p+1", "0x1.d170180000000p+1",
           "0x1.0084b60000000p+3"],
        d=["0x1.d490ba0000000p+0", "0x1.b77bf80000000p+4"],
        b=["0x1.e224924924924p+7", "0x1.e224924924924p+7",
           "0x1.c200000000000p+7"],
        techo=["0x1.680f1a0000000p+9", "0x1.680f1a0000000p+9"],
        piso_j=["0x1.8bae140000000p+9", "0x1.8bae140000000p+9",
                "0x1.8bae140000000p+9"]),
    # E4, 2025-11-24 16:00; venden Mariana y Cesmag; compran Udenar, UCC, HUDN.
    "E4-5632": dict(
        vendedores=["Mariana", "Cesmag"], compradores=["Udenar", "UCC", "HUDN"],
        s=["0x1.9e46ba0000000p+1", "0x1.467d100000000p+3"],
        d=["0x1.9583c20000000p+3", "0x1.1e623c0000000p+5",
           "0x1.ddfea20000000p+0"],
        b=["0x1.e224924924924p+7", "0x1.c200000000000p+7"],
        techo=["0x1.680f1a0000000p+9", "0x1.680f1a0000000p+9",
               "0x1.680f1a0000000p+9"],
        piso_j=["0x1.8bae140000000p+9", "0x1.8bae140000000p+9"]),
}
HUELLA = "fe4488168ced426c"
CAMPOS = ("s", "d", "b", "techo", "piso_j")


def _hex(v):
    return np.array([float.fromhex(x) for x in v], dtype=float)


def _huella():
    m = hashlib.sha256()
    for h in HORAS.values():
        for campo in CAMPOS:
            m.update(np.ascontiguousarray(_hex(h[campo]),
                                          dtype=np.float64).tobytes())
    return m.hexdigest()[:16]


def _entradas(k):
    """(s, d, b, techo, piso_j) de la hora k. Comprueba la huella antes, para
    que una prueba suelta (`-k 3086`) no use literales sin comprobar."""
    assert _huella() == HUELLA, \
        "los literales de las horas no son los de la huella"
    h = HORAS[k]
    return tuple(_hex(h[c]) for c in CAMPOS)


def _resuelve(k, **kw):
    return resuelve_reposo(*_entradas(k), **kw)


def _cerca(x, y, tol):
    return np.all(np.abs(np.asarray(x, float) - np.asarray(y, float)) <= tol)


# ─── la huella ─────────────────────────────────────────────────────────────


def test_la_huella_de_los_literales_es_la_extraida():
    assert _huella() == HUELLA
    for h in HORAS.values():
        assert len(h["s"]) == len(h["b"]) == len(h["piso_j"]) == \
            len(h["vendedores"])
        assert len(h["d"]) == len(h["techo"]) == len(h["compradores"])


# ─── las horas de E0 de la primera entrega ────────────────────────────────


def test_853_cuatro_compradores_interiores():
    r = _resuelve(853)
    assert r.regimen == "interiores" and r.n_soluciones == 1
    assert _cerca(r.q, [0.30225] * 4, TOL_Q)
    assert abs(r.S - 2920.61) <= TOL_P
    assert abs(r.ell - 730.15) <= TOL_P and abs(r.p_u - 730.15) <= TOL_P
    assert abs(r.parte_vendedor - 0.750) <= TOL_PARTE
    # Un solo vendedor: es el marginal, sin renta; toda la prima es del juego
    # (D69), y la hora es identica con las tres opciones de despacho.
    assert r.piso_marginal == r.piso and r.vendedores_no_despachados == ()
    assert r.renta_inframarginal == 0.0
    prima = r.ingreso_vendedores.sum() - r.piso * r.s_despachado.sum()
    assert r.parte_juego == pytest.approx(prima, rel=1e-12)
    for despacho in ("costo", "llenado"):
        otra = _resuelve(853, despacho_vendedores=despacho)
        assert np.array_equal(otra.P, r.P) and otra.p_u == r.p_u
    # El invariante guardado en la matriz (H-87): la suma de los arranques
    # de C-136 menos el techo mayor.
    assert abs(_resuelve(853, modo_presupuesto="c136").S - 2913.70) <= TOL_P


def test_874_topados_que_reciben():
    r = _resuelve(874)
    assert r.regimen == "topados" and r.n_soluciones == 1
    assert _cerca(r.q, [0.742, 3.054, 3.054, 1.535], TOL_Q)
    assert _cerca(r.pi_reposo, [731.13, 706.15, 706.15, 777.17], TOL_P)
    assert abs(r.p_u - 721.36) <= TOL_P
    assert abs(r.parte_vendedor - 0.612) <= TOL_PARTE
    rc = _resuelve(874, modo_presupuesto="c136")
    assert _cerca(rc.pi_reposo[[1, 2]], [702.70, 702.70], TOL_P)
    assert _cerca(rc.q, r.q, 1e-12)


def test_2120_tres_excluidos_y_todo_a_cesmag():
    r = _resuelve(2120)
    assert r.regimen == "excluidos" and r.n_soluciones == 1
    assert r.excluidos == (0, 1, 2) and r.excluidos_bajo_piso == ()
    assert np.all(r.q[:3] == 0.0) and abs(r.q[3] - 2.386) <= TOL_Q
    assert abs(r.pi_reposo[3] - 749.47) <= TOL_P
    assert abs(r.p_u - 749.47) <= TOL_P
    assert abs(r.parte_vendedor - 0.561) <= TOL_PARTE


def test_3804_solo_cesmag():
    r = _resuelve(3804)
    assert r.regimen == "excluidos" and r.excluidos == (0, 1, 2)
    assert np.all(r.q[:3] == 0.0) and abs(r.q[3] - 4.861) <= TOL_Q
    assert abs(r.pi_reposo[3] - 738.51) <= TOL_P
    assert abs(r.p_u - 738.51) <= TOL_P
    assert abs(r.parte_vendedor - 0.523) <= TOL_PARTE


def test_3086_la_suma_no_cabe_reparto_y_regimen_del_encargo():
    r = _resuelve(3086)
    assert r.regimen == "suma_no_cabe" and r.n_soluciones == 1
    assert _cerca(r.q, [0.616, 7.444, 0.910, 0.838], TOL_Q)


def test_3086_la_suma_no_cabe_precios_de_la_regla_del_paso_5():
    """Lo que da el nucleo con la regla del paso 5. Orden de aptitud (lo que
    recibe, creciente): Mariana 0,616, Cesmag 0,838, HUDN 0,910, UCC 7,444.
    Mariana y Cesmag caben en su techo; HUDN no cabe y queda interior con el
    resto de S; UCC, en el piso. La suma de los precios es S."""
    s, d, b, techo, piso_j = _entradas(3086)
    r = _resuelve(3086)
    piso = float(piso_j[0])
    hudn = r.S - techo[0] - techo[3] - piso
    assert _cerca(r.pi_reposo, [techo[0], piso, hudn, techo[3]], 1e-9)
    assert abs(r.pi_reposo.sum() - r.S) <= 1e-9
    assert r.ell == pytest.approx(hudn, abs=1e-9)
    assert _cerca(r.pi_reposo, [726.91, 688.37, 704.40, 816.98], TOL_P)
    assert abs(r.p_u - 703.26) <= TOL_P
    assert abs(r.parte_vendedor - 0.322) <= TOL_PARTE


def test_877_dos_vendedores_reparto_y_regimen_del_encargo():
    r = _resuelve(877)
    assert r.regimen == "suma_no_cabe" and r.n_soluciones == 1
    assert _cerca(r.q, [5.024, 1.753, 1.738], TOL_Q)
    # Rango uno: cada vendedor reparte en proporcion a lo que recibe cada uno.
    s = _entradas(877)[0]
    assert np.allclose(r.P, np.outer(s, r.q) / r.E, rtol=0, atol=1e-12)


def test_877_la_suma_no_cabe_precios_de_la_regla_del_paso_5():
    """Orden de aptitud: Cesmag 1,738, HUDN 1,753, UCC 5,024. Cesmag cabe en
    su techo; HUDN no cabe y queda interior; UCC, en el piso."""
    s, d, b, techo, piso_j = _entradas(877)
    r = _resuelve(877)
    piso = float(piso_j.min())
    hudn = r.S - techo[2] - piso
    assert _cerca(r.pi_reposo, [piso, hudn, techo[2]], 1e-9)
    assert _cerca(r.pi_reposo, [692.69, 715.78, 777.17], TOL_P)
    assert abs(r.p_u - 714.69) <= TOL_P
    assert abs(r.parte_vendedor - 0.460) <= TOL_PARTE


def test_12_dos_vendedores_mariana_y_ucc_excluidos():
    # D71: la forma cerrada de la hora 12, con la rama cuantal apagada. Las
    # aserciones de antes de D71, sin cambiar un caracter.
    r = _resuelve(12, mu_cuantal=0.0)
    assert r.regimen == "excluidos" and r.excluidos == (0, 1)
    assert np.all(r.q[:2] == 0.0) and abs(r.q[2] - 6.732) <= TOL_Q
    assert abs(r.pi_reposo[2] - 735.89) <= TOL_P
    assert abs(r.parte_vendedor - 0.406) <= TOL_PARTE
    assert _cerca(r.s_despachado, _entradas(12)[0], 1e-12)
    assert r.regimen_cerrado == "excluidos" and r.apartamiento == 0.0
    assert r.mu_cuantal == 0.0


def test_12_es_fragil_y_el_nucleo_publica_el_reposo_cuantal():
    """D71 (sec. 6.1 del diseno de la rama cuantal). La hora 12 de E0 es la
    fragil de los literales: Cesmag, interior, queda a 1,59 (COP/kWh) sobre el
    techo de Mariana y UCC, que en la forma cerrada no reciben nada. Con
    mu = 1 el nucleo publica el reposo cuantal: los mismos precios, S, ell y
    despacho, y el reparto por la respuesta cuantal."""
    s, d, b, techo, piso_j = _entradas(12)
    r = _resuelve(12)
    cerrado = _resuelve(12, mu_cuantal=0.0)
    assert r.regimen == "cuantal" and r.regimen_cerrado == "excluidos"
    assert r.excluidos == () and r.n_soluciones == 1 and r.mu_cuantal == 1.0
    assert r.apartamiento == pytest.approx(0.289056, abs=1e-4)
    assert _cerca(r.q, [0.97295922, 0.97295922, 4.78605365], 1e-6)
    assert _cerca(r.P, [[0.72728070, 0.72728070, 3.57754404],
                        [0.24567852, 0.24567852, 1.20850961]], 1e-6)
    # Los precios, S, ell y lo despachado, AL BIT los de la forma cerrada.
    assert np.array_equal(r.pi_reposo, cerrado.pi_reposo)
    assert _cerca(r.pi_reposo, [734.30078125, 734.30078125, 735.8939006],
                  1e-6)
    assert r.ell == cerrado.ell and r.S == cerrado.S
    assert r.p_u == pytest.approx(735.893901, abs=1e-6)
    assert np.array_equal(r.s_despachado, s)
    assert abs(float(r.q.sum()) - r.E) <= 1e-12 * r.E
    # El dinero: el ingreso casi no cambia; el excedente y la captura bajan y
    # la parte del vendedor sube.
    assert r.ingreso_vendedores.sum() == pytest.approx(4950.917, abs=1e-3)
    assert r.excedente == pytest.approx(548.678, abs=1e-3)
    assert r.parte_vendedor == pytest.approx(0.487739, abs=1e-6)
    assert r.renta_inframarginal == 0.0
    assert r.parte_juego == pytest.approx(267.611, abs=1e-3)
    medio = r.ingreso_vendedores / r.s_despachado
    assert medio == pytest.approx([735.4334, 735.4334], abs=1e-4)
    assert medio[0] == pytest.approx(medio[1], rel=1e-15)
    assert np.all(medio >= 695.68)
    optimo, peor = cotas_optimalidad(s, d, techo, piso_j, r.E)
    assert optimo == pytest.approx(666.054, abs=1e-3)
    assert peor == pytest.approx(259.987, abs=1e-3)
    assert captura(r.excedente, optimo) == pytest.approx(0.823774, abs=1e-6)
    # La condicion del reposo: pi_i - ln q_i, la misma para los tres.
    v = r.pi_reposo - np.log(r.q)
    assert float(v.max() - v.min()) <= 1e-9


@pytest.mark.parametrize("mu, parte", [(0.25, 0.0034), (0.5, 0.0763),
                                       (1.0, 0.2891), (2.0, 0.4742),
                                       (4.0, 0.5732)])
def test_12_el_reparto_cuantal_depende_de_mu(mu, parte):
    """D71, sec. 8.1 del diseno: la parte de E que sale del comprador interior
    en la hora 12 depende de mu, que no tiene ancla empirica. Con mu -> 0 se
    recupera la forma cerrada (con 0,1 ya no es fragil)."""
    r = _resuelve(12, mu_cuantal=mu)
    assert r.regimen == "cuantal" and r.mu_cuantal == mu
    assert r.apartamiento == pytest.approx(parte, abs=1e-4)
    # En la forma cerrada Cesmag recibe todo E: lo que sale de el es el
    # apartamiento.
    assert (r.E - r.q[2]) / r.E == pytest.approx(r.apartamiento, rel=1e-9)
    casi = _resuelve(12, mu_cuantal=0.1)
    assert casi.regimen == "excluidos" and casi.apartamiento < 1e-6


def test_58_un_vendedor_dos_compradores_parte_un_medio_exacta():
    # Sus literales son el conjunto posterior al retiro de la corrida vieja
    # (Udenar y Mariana retirados, fuera); con los retirados seria otra hora.
    r = _resuelve(58)
    assert r.regimen == "interiores"
    assert _cerca(r.q, [0.785, 0.785], TOL_Q)
    assert abs(r.p_u - 677.12) <= TOL_P
    assert r.sigma == 0.5
    assert abs(r.parte_vendedor - 0.5) <= 1e-12


# ─── la dinamica respalda la regla del paso 5 ─────────────────────────────
# Promedios temporales del acoplado (arranque de hoy, es decir presupuesto
# C-136) en `scratchpad/evaluador2/valida_reposo_E0.log`, redondeados a dos
# decimales. En la 540 la dinamica llega; en la 3086 oscila y el promedio
# queda a 1,4 (COP/kWh) del reposo. El segundo lazo del prototipo pone a HUDN
# en su techo (734,30 y 726,91), a 24 y 35 (COP/kWh) de la dinamica.


@pytest.mark.parametrize("k, q_din, z_din, tol_z", [
    (540, [1.132, 4.07, 2.084, 0.392], [734.30, 695.68, 710.17, 794.62], 0.02),
    (3086, [0.616, 7.444, 0.91, 0.838], [726.84, 688.37, 692.25, 815.69], 1.5),
])
def test_paso_5_reproduce_el_promedio_de_la_dinamica(k, q_din, z_din, tol_z):
    r = _resuelve(k, modo_presupuesto="c136")
    assert r.regimen == "suma_no_cabe"
    assert _cerca(r.q, q_din, 2e-3)
    assert _cerca(r.pi_reposo, z_din, tol_z)
    assert abs(r.pi_reposo.sum() - sum(z_din)) <= 0.05


# ─── compradores cortos, un comprador, D61 y D63 en horas reales ──────────


def test_e0_4766_compradores_cortos_piso_costo_y_llenado():
    """Compradores cortos con Cesmag vendiendo (b = 225, piso 616,46) y dos
    retirados de la corrida vieja (b = 241,07, piso 677,28). Por piso y por
    costo despacha solo Cesmag, el de piso menor y costo menor, que cubre los
    1,72 (kWh): el piso marginal es el suyo y la hora es la de siempre (Fable,
    sec. 6, E5). Por llenado despachan los tres a partes iguales, y el piso del
    juego es el maximo de sus pisos, 677,28 (D63; Fable lo predijo en la sec.
    7): suben el presupuesto y los precios, y la parte del vendedor, que antes
    salia -0,262, pasa a ser positiva."""
    d = _entradas(4766)[1]
    r = _resuelve(4766)
    rc = _resuelve(4766, despacho_vendedores="costo")
    rl = _resuelve(4766, despacho_vendedores="llenado")
    for x in (r, rc, rl):
        assert x.regimen == "compradores_cortos" and x.n_soluciones == 1
        assert _cerca(x.q, d, 0.0)
        assert x.orden_merito == (2, 0, 1)
    # Por piso, la caminata cierra en 616,46 (volumen 1,72 en los dos
    # niveles): Udenar y HUDN, de piso 677,28, no despachan por la
    # competencia. Por costo no hay caminata y la lista queda vacia.
    assert r.vendedores_no_despachados == (0, 1)
    assert rc.vendedores_no_despachados == rl.vendedores_no_despachados == ()
    for x in (r, rc):
        assert abs(x.piso - 616.46) <= TOL_P and abs(x.S - 1332.08) <= TOL_P
        # Dos compradores de banda igual y sigma = 1/2: el de menor deficit
        # (Mariana) en su techo y UCC en el piso.
        assert _cerca(x.pi_reposo, [715.62, 616.46], TOL_P)
        assert abs(x.p_u - 641.64) <= TOL_P
        assert _cerca(x.p_liquidado, [641.64, 641.64], TOL_P)
        assert _cerca(x.s_despachado, [0.0, 0.0, 1.7224], 1e-4)
        assert abs(x.parte_vendedor - 0.254) <= TOL_PARTE
        # Un solo despachado, el marginal: sin renta, toda la prima es del
        # juego, (641,64 - 616,46)·1,7224.
        assert x.renta_inframarginal == 0.0
        assert abs(x.parte_juego - (x.p_u - x.piso) * x.E) <= 1e-9
    assert np.array_equal(r.P, rc.P) and r.p_u == rc.p_u
    # Por llenado: el piso marginal es el maximo de los tres.
    piso_j = _entradas(4766)[4]
    assert rl.piso == float(piso_j.max())
    assert abs(rl.piso - 677.28) <= TOL_P and abs(rl.S - 1392.90) <= TOL_P
    assert _cerca(rl.pi_reposo, [715.62, 677.28], TOL_P)
    assert abs(rl.p_u - 687.02) <= TOL_P
    assert _cerca(rl.s_despachado, [0.5741, 0.5741, 0.5741], 1e-4)
    assert abs(rl.parte_vendedor - 0.512) <= TOL_PARTE
    # La renta es la de Cesmag, (677,28 - 616,46)·0,5741.
    assert abs(rl.renta_inframarginal - 34.92) <= 0.01
    assert abs(rl.parte_juego - 16.77) <= 0.01


def test_e0_226_un_comprador_paga_el_piso():
    # Cuatro vendedores de igual piso y de igual b: las tres opciones reparten
    # igual, por niveles.
    for despacho in DESPACHOS_VENDEDORES:
        r = _resuelve(226, despacho_vendedores=despacho)
        assert r.regimen == "un_comprador" and r.n_soluciones == 1
        assert abs(r.q[0] - 2.1857) <= TOL_Q
        assert _cerca(r.s_despachado, [0.5464] * 4, 1e-4)
        assert abs(r.piso - 695.68) <= TOL_P
        assert r.p_u == pytest.approx(r.piso, abs=1e-9)
        assert r.piso == r.pi_reposo[0] == r.S
        assert r.parte_vendedor == 0.0 and r.sigma == 0.0
        assert r.renta_inframarginal == 0.0
        assert r.vendedores_no_despachados == ()


@pytest.mark.parametrize("k, techo, energia_posible", [
    ("E4-5631", 720.12, 14.586), ("E4-5632", 720.12, 13.439)])
def test_e4_sin_ganancia_es_sin_mercado_con_su_causa(k, techo, energia_posible):
    """D61: el piso de todos los vendedores (791,36) supera el techo de todos
    los compradores activos (720,12). No es un error: sin mercado, con la
    causa anotada para contar su energia. Con la caminata (D65) es su volumen
    maximo 0, y sigue igual con las tres opciones."""
    s, d, b, t, piso_j = _entradas(k)
    for kw in ({}, {"despacho_vendedores": "costo"},
               {"despacho_vendedores": "llenado"},
               {"modo_presupuesto": "c136"}):
        r = _resuelve(k, **kw)
        assert r.regimen == "sin_ganancia" and r.n_soluciones == 0
        assert r.E == 0.0 and not np.any(r.P) and not np.any(r.q)
        assert abs(r.piso - 791.36) <= TOL_P and r.piso_marginal == r.piso
        assert _cerca(r.pi_reposo, [techo] * d.size, TOL_P)
        assert np.array_equal(r.p_liquidado, t) and r.excluidos == ()
        assert r.vendedores_excluidos == tuple(range(s.size))
        assert r.orden_merito == r.excluidos_bajo_piso == ()
        assert r.vendedores_no_despachados == ()
        assert r.renta_inframarginal == r.parte_juego == 0.0
        dh = despacho_competitivo(s, d, t, piso_j,
                                  kw.get("despacho_vendedores", "piso"), b=b)
        assert dh.causa == "sin_ganancia" and dh.E == 0.0
    assert abs(min(s.sum(), d.sum()) - energia_posible) <= TOL_Q


def test_e4_133_el_piso_es_el_del_vendedor_marginal():
    """Un comprador (UCC, 4,19 (kWh), techo 734,31) y cuatro vendedores con los
    retirados de la corrida vieja: Udenar 25,34 (kWh) a 147,46; Mariana 2,94 y
    HUDN 34,77 a 415,10; Cesmag 6,81 a 330,15 (Fable, sec. 6, E4).

    Por piso (D64 y D65): la caminata da el mismo volumen, 4,19, en los tres
    niveles, y se queda con el menor: vende solo Udenar, a su piso, 147,46,
    con parte 0 y sin renta; los otros tres quedan no despachados.
    Por costo: vende Cesmag (b = 225) a 330,15, lo de siempre.
    Por llenado: despachan los cuatro y el piso del juego es el maximo, 415,10
    (antes, con el minimo, 147,46 y parte -0,441)."""
    s, d, b, techo, piso_j = _entradas("E4-133")
    r = _resuelve("E4-133")
    assert r.regimen == "un_comprador"
    assert _cerca(r.s_despachado, [4.1924, 0.0, 0.0, 0.0], 1e-4)
    assert abs(r.piso - 147.46) <= TOL_P and r.piso == float(piso_j[0])
    assert r.p_u == pytest.approx(r.piso, abs=1e-9)
    assert abs(r.parte_vendedor) <= 1e-12
    assert r.orden_merito == (0, 3, 1, 2)
    assert r.vendedores_no_despachados == (1, 2, 3)
    assert r.vendedores_excluidos == () and r.excluidos_bajo_piso == ()
    assert r.renta_inframarginal == 0.0 and abs(r.parte_juego) <= 1e-9

    rc = _resuelve("E4-133", despacho_vendedores="costo")
    assert rc.regimen == "un_comprador"
    assert _cerca(rc.s_despachado, [0.0, 0.0, 0.0, 4.1924], 1e-4)
    assert abs(rc.piso - 330.15) <= TOL_P
    assert rc.p_u == pytest.approx(rc.piso, abs=1e-9)
    assert abs(rc.parte_vendedor) <= 1e-12
    assert rc.orden_merito == (3, 0, 1, 2)
    assert rc.vendedores_no_despachados == ()

    rl = _resuelve("E4-133", despacho_vendedores="llenado")
    assert _cerca(rl.s_despachado, [1.0481] * 4, 1e-4)
    assert abs(rl.piso - 415.10) <= TOL_P and rl.piso == float(piso_j.max())
    assert rl.p_u == pytest.approx(rl.piso, abs=1e-9)
    assert abs(rl.parte_vendedor - 0.2164) <= TOL_PARTE
    # Un comprador: la prima es toda renta de los inframarginales (D66).
    assert abs(rl.parte_juego) <= 1e-9
    assert rl.renta_inframarginal == pytest.approx(
        float(np.dot(rl.piso - piso_j, rl.s_despachado)), rel=1e-12)


# ─── sinteticos ────────────────────────────────────────────────────────────

GRANDES = [10.0, 20.0, 30.0]   # deficits que el vendedor no llena (kWh)


def test_sigma_cero_da_todos_en_el_piso_y_parte_cero():
    r = resuelve_reposo([3.0], GRANDES, [241.0], [730.0, 730.0, 780.0],
                        [690.0], sigma=0.0)
    assert np.all(r.pi_reposo == 690.0) and r.p_u == 690.0
    assert np.all(r.p_liquidado == 690.0)
    assert r.parte_vendedor == 0.0


@pytest.mark.parametrize("kw", [
    {}, {"sigma": 1.0}, {"modo_presupuesto": "c136"},
    {"modo_presupuesto": "algoritmo3", "pi_gs": 730.0},
])
def test_un_comprador_paga_el_piso_en_todos_los_modos(kw):
    # D54: vendedores cortos y compradores cortos.
    r = resuelve_reposo([2.0], [5.0], [241.0], [730.0], [690.0], **kw)
    assert r.regimen == "un_comprador"
    assert r.pi_reposo[0] == 690.0 and r.p_u == 690.0 and r.q[0] == 2.0
    rc = resuelve_reposo([2.0, 3.0], [1.5], [241.0, 225.0], [730.0],
                         [690.0, 680.0], **kw)
    assert rc.regimen == "un_comprador" and rc.p_u == 680.0
    assert _cerca(rc.s_despachado, [0.0, 1.5], 1e-12)


@pytest.mark.parametrize("I, parte", [(2, 0.5), (4, 0.75)])
def test_bandas_iguales_parte_del_vendedor_es_i_menos_uno_sobre_i(I, parte):
    r = resuelve_reposo([3.0], [10.0 + k for k in range(I)], [241.0],
                        [730.0] * I, [690.0])
    assert r.regimen == "interiores"
    assert abs(r.parte_vendedor - parte) <= 1e-12
    assert _cerca(r.pi_reposo, [690.0 + parte * 40.0] * I, 1e-9)


def test_vendedores_cortos_el_reparto_por_comprador_no_depende_de_b():
    base = dict(s=[2.0, 1.0], d=[5.0, 0.5, 4.0], techo=[730.0, 730.0, 780.0],
                piso_j=[690.0, 695.0])
    for despacho in DESPACHOS_VENDEDORES:
        rs = [resuelve_reposo(base["s"], base["d"], b, base["techo"],
                              base["piso_j"], despacho_vendedores=despacho)
              for b in ([200.0, 260.0], [260.0, 200.0], [241.0, 241.0])]
        for r in rs[1:]:
            assert np.array_equal(r.q, rs[0].q)
            assert np.array_equal(r.P, rs[0].P)
            assert np.array_equal(r.pi_reposo, rs[0].pi_reposo)
        assert _cerca(rs[0].s_despachado, base["s"], 0.0)
        # Vendedores cortos: despachan los dos y el marginal es el de 695.
        assert all(r.piso == 695.0 for r in rs)
        if despacho == "piso":
            assert all(r.orden_merito == (0, 1) for r in rs)
        else:
            assert rs[0].orden_merito == (0, 1)
            assert rs[1].orden_merito == (1, 0)


def test_compradores_cortos_costo_despacha_primero_al_de_b_menor():
    kw = dict(s=[5.0, 5.0], d=[2.0, 4.0], b=[241.07, 225.0],
              techo=[730.0, 780.0], piso_j=[690.0, 690.0])
    r = resuelve_reposo(**kw, despacho_vendedores="costo")
    assert r.regimen == "compradores_cortos"
    assert _cerca(r.q, [2.0, 4.0], 0.0)
    assert _cerca(r.s_despachado, [1.0, 5.0], 1e-12)
    assert r.orden_merito == (1, 0)
    rl = resuelve_reposo(**kw, despacho_vendedores="llenado")
    assert _cerca(rl.s_despachado, [3.0, 3.0], 1e-12)
    assert _cerca(rl.pi_reposo, r.pi_reposo, 0.0)
    # Por piso, con pisos iguales, un solo nivel: llenado entre los dos, y el
    # orden por piso es el de los indices.
    rp = resuelve_reposo(**kw)
    assert _cerca(rp.s_despachado, [3.0, 3.0], 1e-12)
    assert rp.orden_merito == (0, 1)
    assert _cerca(rp.pi_reposo, r.pi_reposo, 0.0)


def test_compradores_cortos_llenado_entre_vendedores_de_igual_b():
    # Por costo, Cesmag (b = 225) vende todo; los dos de b = 241 reparten el
    # resto por niveles (el de 1 (kWh) se agota).
    kw = dict(s=[4.0, 1.0, 5.0], d=[3.0, 4.0], b=[241.0, 241.0, 225.0],
              techo=[730.0, 780.0], piso_j=[690.0, 690.0, 690.0])
    r = resuelve_reposo(**kw, despacho_vendedores="costo")
    assert _cerca(r.s_despachado, [1.0, 1.0, 5.0], 1e-12)
    assert r.orden_merito == (2, 0, 1)
    rl = resuelve_reposo(**kw, despacho_vendedores="llenado")
    assert _cerca(rl.s_despachado, [3.0, 1.0, 3.0], 1e-12)
    # Por piso, los tres en el mismo nivel: llenado, como "llenado".
    rp = resuelve_reposo(**kw)
    assert np.array_equal(rp.s_despachado, rl.s_despachado)
    for x in (r, rl, rp):
        assert np.allclose(x.P.sum(axis=1), x.s_despachado, atol=1e-12)
        assert np.allclose(x.P.sum(axis=0), [3.0, 4.0], atol=1e-12)


def test_varios_reposos_del_paso_3_se_anotan_y_se_elige_el_llenado_amplio():
    # Dos compradores identicos y llenos: su precio comun, o uno en el techo
    # y el otro interior. Tres reposos; se elige el de mas interiores.
    r = resuelve_reposo([4.72], [2.0, 2.0, 0.9], [241.0],
                        [818.6, 818.6, 728.4], [690.0], sigma=0.9)
    assert r.n_soluciones == 3
    assert r.regimen == "topados"
    assert r.pi_reposo[0] == r.pi_reposo[1]


def test_compradores_cortos_con_empate_se_anotan_las_soluciones():
    r = resuelve_reposo([30.0], [0.3, 0.9, 7.0, 7.0], [241.0],
                        [774.5, 774.5, 818.6, 774.5], [690.0], sigma=0.5)
    assert r.regimen == "compradores_cortos" and r.n_soluciones == 3
    # Empate en deficit: sube primero el de techo mas alto.
    assert _cerca(r.pi_reposo, [774.5, 774.5, 712.05, 690.0], 1e-9)


def test_la_regla_del_paso_5_sin_reposo_se_publica_como_declarada():
    # Ningun estado cumple las condiciones de reposo: la regla se aplica igual
    # y n_soluciones = 0 lo anota (D53, regla declarada).
    r = resuelve_reposo([0.66], [16.5, 0.24, 0.23], [241.0],
                        [676.0, 717.0, 732.0], [620.0])
    assert r.regimen == "suma_no_cabe" and r.n_soluciones == 0
    assert _cerca(r.pi_reposo, [620.0, r.S - 732.0 - 620.0, 732.0], 1e-9)


def test_una_regla_que_no_cae_en_ningun_reposo_existente_falla(monkeypatch):
    # La guarda de _regla_entre_estados: con reposos en la hora, una regla que
    # publicara otro estado es un fallo mudo en potencia y debe lanzar.
    import core.reposo_mercado as rm

    def regla_equivocada(q_orden, techo, piso, S, tol_q):
        z = np.full(techo.size, piso)
        z[0] = S - piso * (techo.size - 1)
        return z, 0, float(z[0])

    kw = dict(s=[5.0, 5.0], d=[2.0, 4.0], b=[241.07, 225.0],
              techo=[730.0, 780.0], piso_j=[690.0, 690.0])
    assert resuelve_reposo(**kw).n_soluciones == 1
    monkeypatch.setattr(rm, "_regla_saturacion", regla_equivocada)
    with pytest.raises(ValueError, match="reposos de la hora"):
        resuelve_reposo(**kw)


def test_d61_sin_ganancia_no_lanza_y_anota_la_causa():
    # El piso del vendedor activo (710) supera el techo del unico comprador
    # activo; el vendedor inactivo (600) no cuenta.
    r = resuelve_reposo([2.0, 0.0], [5.0], [241.0, 225.0], [700.0],
                        [710.0, 600.0])
    assert r.regimen == "sin_ganancia" and r.E == 0.0 and r.piso == 710.0
    assert r.vendedores_excluidos == (0,) and r.orden_merito == ()
    assert r.excluidos == r.excluidos_bajo_piso == ()
    # Un comprador sin deficit con techo alto no cuenta.
    r2 = resuelve_reposo([2.0], [5.0, 0.0], [241.0], [700.0, 900.0], [710.0])
    assert r2.regimen == "sin_ganancia"


def test_d61_parcial_el_comprador_bajo_el_piso_sale_de_la_hora():
    r = resuelve_reposo(**{**VALIDA, "techo": [680.0, 780.0]})
    assert r.regimen == "un_comprador" and r.excluidos_bajo_piso == (0,)
    assert r.excluidos == ()
    assert r.q[0] == 0.0 and r.q[1] == 2.0
    assert r.p_u == 690.0 and r.S == 690.0
    assert r.pi_reposo[0] == 680.0 and r.p_liquidado[0] == 680.0
    # Con tres: sale el de techo bajo, y S y sigma son los de los otros dos.
    r3 = resuelve_reposo([3.0], [5.0, 4.0, 6.0], [241.0],
                         [700.0, 760.0, 780.0], [710.0])
    assert r3.regimen == "interiores" and r3.excluidos_bajo_piso == (0,)
    assert r3.excluidos == ()
    assert r3.q[0] == 0.0 and _cerca(r3.q[1:], [1.5, 1.5], 1e-12)
    assert r3.S == pytest.approx(presupuesto_precios([760.0, 780.0], 710.0))
    assert r3.sigma == 0.5
    assert r3.pi_reposo[1:].sum() == pytest.approx(r3.S)
    # Un comprador sin deficit con el techo muy bajo no cuenta ni lanza.
    r0 = resuelve_reposo([2.0], [0.0, 5.0], [241.0], [100.0, 730.0], [690.0])
    assert r0.regimen == "un_comprador"
    assert r0.excluidos == r0.excluidos_bajo_piso == ()


def test_d63_el_piso_es_el_del_vendedor_marginal_en_las_tres_opciones():
    """Sustituye a la prueba de D62. Dos vendedores, pisos 600 y 690, con 5 y
    10 (kWh); dos compradores con 2 y 4 (kWh). Por piso, la caminata da 5 al
    nivel 600 y 6 al nivel 690: despacha 5 el de 600 y 1 el de 690, el
    marginal, y el piso del juego es 690. Por costo despacha solo el segundo
    (b = 225): 690. Por llenado, los dos a 3 (kWh): el maximo, 690 (con D62
    era el minimo, 600, y el de 690 quedaba bajo su piso). En las tres, los
    mismos precios y nadie bajo su piso."""
    kw = dict(s=[5.0, 10.0], d=[2.0, 4.0], b=[241.0, 225.0],
              techo=[730.0, 780.0], piso_j=[600.0, 690.0])
    r = resuelve_reposo(**kw)
    assert _cerca(r.s_despachado, [5.0, 1.0], 1e-12) and r.piso == 690.0
    assert r.renta_inframarginal == pytest.approx(90.0 * 5.0)
    rc = resuelve_reposo(**kw, despacho_vendedores="costo")
    assert _cerca(rc.s_despachado, [0.0, 6.0], 1e-12) and rc.piso == 690.0
    assert rc.renta_inframarginal == 0.0
    rl = resuelve_reposo(**kw, despacho_vendedores="llenado")
    assert _cerca(rl.s_despachado, [3.0, 3.0], 1e-12) and rl.piso == 690.0
    for x in (r, rc, rl):
        assert _cerca(x.pi_reposo, [730.0, 715.0], 1e-9)
        assert x.parte_vendedor >= 0.0
        medio = x.ingreso_vendedores / np.where(x.s_despachado > 0,
                                                x.s_despachado, 1.0)
        assert np.all(medio[x.s_despachado > 0]
                      >= np.array(kw["piso_j"])[x.s_despachado > 0] - 1e-9)


def test_oferta_de_los_que_despachan_igual_a_la_demanda():
    """Por costo despacha solo el primero y su oferta iguala la demanda. La
    hora sigue en compradores cortos (la rama la decide la oferta de todos los
    que pueden vender) y da lo mismo que pasar solo a ese vendedor, que cae en
    la rama de vendedores cortos con sum s = sum d.

    Por piso (D65), el mismo empate lo resuelve la caminata: al nivel 600 la
    oferta ya iguala la demanda, 6 (kWh), y el menor nivel que maximiza es ese;
    pueden vender solo los de piso <= 600 y la hora es de vendedores cortos,
    identica a la del vendedor solo, con el otro no despachado."""
    kw = dict(d=[2.0, 4.0], techo=[730.0, 780.0])
    r = resuelve_reposo(s=[6.0, 5.0], b=[225.0, 241.0], piso_j=[690.0, 600.0],
                        despacho_vendedores="costo", **kw)
    assert r.regimen == "compradores_cortos"
    assert _cerca(r.s_despachado, [6.0, 0.0], 0.0) and r.piso == 690.0
    solo = resuelve_reposo(s=[6.0], b=[225.0], piso_j=[690.0], **kw)
    assert solo.regimen == "topados"
    for campo in ("q", "pi_reposo", "p_liquidado"):
        assert _cerca(getattr(r, campo), getattr(solo, campo), 1e-9), campo
    assert r.piso == solo.piso and r.S == pytest.approx(solo.S)
    assert r.p_u == pytest.approx(solo.p_u)
    assert r.n_soluciones == solo.n_soluciones == 1

    rp = resuelve_reposo(s=[5.0, 6.0], b=[241.0, 225.0], piso_j=[690.0, 600.0],
                         **kw)
    solo_p = resuelve_reposo(s=[6.0], b=[225.0], piso_j=[600.0], **kw)
    assert rp.regimen == solo_p.regimen == "topados"
    assert rp.vendedores_no_despachados == (0,)
    assert _cerca(rp.s_despachado, [0.0, 6.0], 0.0) and rp.piso == 600.0
    for campo in ("q", "pi_reposo", "p_liquidado"):
        assert np.array_equal(getattr(rp, campo), getattr(solo_p, campo)), \
            campo


def test_d61_el_vendedor_sin_ganancia_posible_no_entra_al_merito():
    # El de b menor tiene el piso (750) sobre el techo de todos (720): queda
    # fuera antes del orden de merito, y vende el de piso 600. Con las tres
    # opciones da lo mismo, y la hora no es «sin_ganancia». Es D61, no la
    # competencia: va a `vendedores_excluidos`, no a los no despachados.
    kw = dict(s=[10.0, 10.0], d=[2.0], b=[225.0, 241.0], techo=[720.0],
              piso_j=[750.0, 600.0])
    for despacho in DESPACHOS_VENDEDORES:
        r = resuelve_reposo(**kw, despacho_vendedores=despacho)
        assert r.regimen == "un_comprador" and r.piso == 600.0
        assert r.vendedores_excluidos == (0,) and r.orden_merito == (1,)
        assert r.vendedores_no_despachados == ()
        assert _cerca(r.s_despachado, [0.0, 2.0], 0.0)
        assert not np.any(r.P[0]) and r.p_u == pytest.approx(600.0)


def test_d61_el_vendedor_sin_ganancia_no_cuenta_para_decidir_la_rama():
    # Con los dos vendedores la oferta (13) pasa la demanda (6), pero el de
    # piso 750 no puede vender a nadie (techos 720 y 730): la oferta que cuenta
    # es 3, la hora es de vendedores cortos y el de piso 600 vende todo.
    r = resuelve_reposo([10.0, 3.0], [2.0, 4.0], [225.0, 241.0],
                        [720.0, 730.0], [750.0, 600.0])
    assert r.regimen != "compradores_cortos"
    assert r.vendedores_excluidos == (0,) and r.E == 3.0
    assert _cerca(r.s_despachado, [0.0, 3.0], 0.0) and r.piso == 600.0
    assert r.q.sum() == pytest.approx(3.0)
    # Sin el excluido, la hora es la misma.
    solo = resuelve_reposo([3.0], [2.0, 4.0], [241.0], [720.0, 730.0], [600.0])
    for campo in ("q", "pi_reposo", "p_liquidado"):
        assert _cerca(getattr(r, campo), getattr(solo, campo), 0.0), campo
    assert r.regimen == solo.regimen and r.p_u == solo.p_u
    # Un vendedor con piso igual al techo mayor si puede vender.
    r2 = resuelve_reposo([10.0, 3.0], [2.0, 4.0], [225.0, 241.0],
                         [720.0, 730.0], [730.0, 600.0])
    assert r2.vendedores_excluidos == ()


def test_c136_con_dos_compradores_es_h32_y_lanza():
    # Arranque comun 500 dentro de las dos bandas: S = 1 500 - 800 = 700, el
    # techo menor, bajo 2·piso = 800.
    assert presupuesto_precios([700.0, 800.0], 400.0, modo="c136") == \
        pytest.approx(700.0)
    with pytest.raises(ValueError, match="H-32"):
        resuelve_reposo([1.0], [5.0, 5.0], [241.0], [700.0, 800.0], [400.0],
                        modo_presupuesto="c136")


def test_comprueba_falla_si_la_liquidacion_no_conserva_el_ingreso(monkeypatch):
    import core.reposo_mercado as rm
    original = rm._precio_uniforme
    monkeypatch.setattr(rm, "_precio_uniforme",
                        lambda *args: original(*args) + 0.5)
    with pytest.raises(ValueError, match="no conserva el ingreso"):
        _resuelve(853)


def test_comprueba_falla_si_los_precios_no_suman_el_presupuesto(monkeypatch):
    import core.reposo_mercado as rm
    original = rm._elige_paso3

    def corrido(estados):
        h = original(estados)
        return {**h, "z": h["z"] - 1.0}

    monkeypatch.setattr(rm, "_elige_paso3", corrido)
    with pytest.raises(ValueError, match="no el presupuesto"):
        _resuelve(853)


def test_regla_puja_liquida_al_precio_del_reposo():
    ru = _resuelve(874)
    rp = _resuelve(874, regla_precio="puja")
    assert np.array_equal(rp.p_liquidado, rp.pi_reposo)
    assert rp.p_u == ru.p_u
    assert rp.regla_precio == "puja" and ru.regla_precio == "uniforme"
    assert abs(rp.ingreso_vendedores.sum() - ru.ingreso_vendedores.sum()) <= \
        1e-9 * ru.ingreso_vendedores.sum()


# ─── el piso del vendedor marginal (D63 a D69), los ejemplos de Fable ─────


def test_s1_un_comprador_y_tres_vendedores_cortos():
    """Fable, sec. 6, E1: d = 10 (kWh) con techo 734; s = (3; 4; 2) con pisos
    (150; 330; 415). Vendedores cortos: despachan los tres, el marginal es el
    de 415 y el comprador unico paga 415 (D66). Con D62 pagaba 150, y la
    participacion retiraba a los otros dos: E = 3 en vez de 9."""
    r = resuelve_reposo([3.0, 4.0, 2.0], [10.0], [225.0, 241.0, 241.0],
                        734.0, [150.0, 330.0, 415.0])
    assert r.regimen == "un_comprador"
    assert r.piso == r.piso_marginal == 415.0 and r.p_u == 415.0
    assert r.E == 9.0 and r.vendedores_no_despachados == ()
    assert _cerca(r.s_despachado, [3.0, 4.0, 2.0], 0.0)
    assert _cerca(r.ingreso_vendedores, [1245.0, 1660.0, 830.0], 1e-9)
    assert r.renta_inframarginal == pytest.approx(1135.0, abs=1e-9)
    assert r.parte_juego == pytest.approx(0.0, abs=1e-9)
    assert abs(r.parte_vendedor - 0.2833) <= 1e-4
    assert r.excedente == pytest.approx(4006.0)
    # La misma hora por la funcion publica del paso 1.
    dh = despacho_competitivo([3.0, 4.0, 2.0], [10.0], 734.0,
                              [150.0, 330.0, 415.0])
    assert isinstance(dh, DespachoHora) and dh.causa == ""
    assert dh.piso == 415.0 and dh.E == 9.0 and dh.dentro == (0,)
    assert dh.pueden_vender == (0, 1, 2)
    assert np.array_equal(dh.s_despachado, r.s_despachado)


def test_s2_dos_compradores_vendedor_en_bolsa_y_en_permuta():
    """Fable, sec. 6, E2: s = (2; 2), pisos (350; 693); d = (3; 3), techos
    (731; 777). Vendedores cortos, E = 4, sigma = 1/2: S = 2·693 + 1/2·(38 +
    84) = 1 447, los dos interiores a 723,5. Con D62 el de permuta cobraba 552
    y se retiraba."""
    r = resuelve_reposo([2.0, 2.0], [3.0, 3.0], [225.0, 241.0], [731.0, 777.0],
                        [350.0, 693.0])
    assert r.regimen == "interiores" and r.n_soluciones == 1
    assert r.piso == 693.0 and r.S == pytest.approx(1447.0)
    assert r.ell == pytest.approx(723.5) and r.p_u == pytest.approx(723.5)
    assert _cerca(r.q, [2.0, 2.0], 1e-12)
    assert abs(r.parte_vendedor - 0.8688) <= 1e-4
    assert r.excedente == pytest.approx(930.0)
    # Prima 808 = renta 686 (el de bolsa, 343·2) + parte del juego 122.
    assert r.renta_inframarginal == pytest.approx(686.0)
    assert r.parte_juego == pytest.approx(122.0)


def test_cruce_de_cotas_el_comprador_de_techo_bajo_queda_fuera():
    """Fable, sec. 7, prueba 5: s (1; 1), pisos (300; 700), d (1,5; 1),
    techos (800; 650). Al nivel 300 el volumen es 1; al nivel 700, min(2;
    1,5) = 1,5: p* = 700 y el comprador de techo 650 sale (D61 parcial). Queda
    un comprador, que paga 700; despachan 1 el de 300 y 0,5 el de 700."""
    r = resuelve_reposo([1.0, 1.0], [1.5, 1.0], [225.0, 241.0], [800.0, 650.0],
                        [300.0, 700.0])
    assert r.piso == 700.0 and r.E == 1.5
    assert r.excluidos_bajo_piso == (1,) and r.regimen == "un_comprador"
    assert r.p_u == 700.0 and r.p_liquidado[0] == 700.0
    assert _cerca(r.s_despachado, [1.0, 0.5], 1e-12)
    assert r.q[1] == 0.0 and r.pi_reposo[1] == 650.0
    # Prima 1 050 - (300 + 350) = 400 sobre un excedente de 500 + 50.
    assert abs(r.parte_vendedor - 400.0 / 550.0) <= 1e-12
    assert abs(r.parte_vendedor - 0.727) <= TOL_PARTE


def test_empate_de_volumen_gana_el_nivel_menor():
    """Fable, sec. 7, prueba 6: s (1; 1), pisos (300; 700), d (1), techo 800.
    Los dos niveles dan volumen 1; p* es el menor, 300, y vende solo el
    primero. El segundo no despacha, por la competencia, no por D61."""
    r = resuelve_reposo([1.0, 1.0], [1.0], [241.0, 225.0], 800.0,
                        [300.0, 700.0])
    assert r.piso == 300.0 and r.E == 1.0 and r.p_u == 300.0
    assert _cerca(r.s_despachado, [1.0, 0.0], 0.0)
    assert r.vendedores_no_despachados == (1,)
    assert r.vendedores_excluidos == ()
    assert r.orden_merito == (0, 1)
    # Con costo, el de b menor es el de 700, y el piso sube a 700.
    rc = resuelve_reposo([1.0, 1.0], [1.0], [241.0, 225.0], 800.0,
                         [300.0, 700.0], despacho_vendedores="costo")
    assert rc.piso == 700.0 and _cerca(rc.s_despachado, [0.0, 1.0], 0.0)


def test_continuidad_de_un_comprador_a_dos():
    """Fable, sec. 7, prueba 7: s (1), d (10; eps), techos (730; 730), piso
    690. El comprador pequeno queda en su techo y recibe eps; el grande, en el
    piso con 1 - eps; p_u = 690 + 40·eps, que tiende a 690 (el precio de un
    comprador) cuando eps tiende a 0."""
    eps = 1e-3
    r = resuelve_reposo([1.0], [10.0, eps], [241.0], [730.0, 730.0], [690.0])
    assert _cerca(r.pi_reposo, [690.0, 730.0], 1e-9)
    assert _cerca(r.q, [1.0 - eps, eps], 1e-12)
    assert r.p_u == pytest.approx(690.0 + 40.0 * eps, abs=1e-9)
    assert abs(r.p_u - 690.04) <= 1e-9
    uno = resuelve_reposo([1.0], [10.0], [241.0], [730.0], [690.0])
    assert uno.p_u == 690.0


def test_con_costo_el_lazo_que_oscila_falla_en_voz_alta():
    """D63 con "costo": el lazo de exclusion ya no es monotono. A (b = 200,
    piso 300, 2 (kWh)) y B (b = 225, piso 700, 10 (kWh)); X (techo 800, 1
    (kWh)) e Y (techo 650, 5 (kWh)). Con los dos dentro despachan A y B y el
    piso maximo es 700: Y sale. Sin Y despacha solo A y el piso es 300: Y
    vuelve. Oscila, y lanza. Por piso la caminata no tiene lazo: p* = 300,
    vende A y compran los dos."""
    kw = dict(s=[2.0, 10.0], d=[1.0, 5.0], b=[200.0, 225.0],
              techo=[800.0, 650.0], piso_j=[300.0, 700.0])
    with pytest.raises(ValueError, match="oscila"):
        resuelve_reposo(**kw, despacho_vendedores="costo")
    with pytest.raises(ValueError, match="oscila"):
        despacho_competitivo(kw["s"], kw["d"], kw["techo"], kw["piso_j"],
                             "costo", b=kw["b"])
    r = resuelve_reposo(**kw)
    assert r.piso == 300.0 and r.E == 2.0
    assert r.excluidos_bajo_piso == () and r.vendedores_no_despachados == (1,)
    # Con llenado despachan los dos siempre: el piso es 700 y Y sale sin
    # oscilar.
    rl = resuelve_reposo(**kw, despacho_vendedores="llenado")
    assert rl.piso == 700.0 and rl.excluidos_bajo_piso == (1,)


def test_despacho_competitivo_rechaza_lo_invalido():
    with pytest.raises(ValueError, match="despacho"):
        despacho_competitivo([1.0], [1.0], 800.0, 300.0, "merito")
    with pytest.raises(ValueError, match="exige b"):
        despacho_competitivo([1.0], [1.0], 800.0, 300.0, "costo")
    with pytest.raises(ValueError):
        despacho_competitivo([1.0, 2.0], [1.0], 800.0, [300.0], "piso")
    assert despacho_competitivo([0.0], [1.0], 800.0, 300.0).causa == \
        "sin_mercado"


def _paso1_con_piso(monkeypatch, piso):
    """Sustituye el paso 1 por uno que devuelve el mismo despacho con otro
    piso del juego, para ejercer las dos guardas de `_comprueba`."""
    import dataclasses

    import core.reposo_mercado as rm
    original = rm._paso1

    def cambiado(*a, **kw):
        return dataclasses.replace(original(*a, **kw), piso=piso)

    monkeypatch.setattr(rm, "_paso1", cambiado)


S2 = dict(s=[2.0, 2.0], d=[3.0, 3.0], b=[225.0, 241.0],
          techo=[731.0, 777.0], piso_j=[350.0, 693.0])


def test_comprueba_falla_si_el_piso_queda_bajo_el_del_marginal(monkeypatch):
    # S2 con el piso del juego en el minimo (la regla de D62): el vendedor de
    # 693 despacha y cobraria bajo su piso.
    _paso1_con_piso(monkeypatch, 350.0)
    with pytest.raises(ValueError, match="queda bajo el mayor piso de los "
                                         "que despachan 693"):
        resuelve_reposo(**S2)


def test_comprueba_falla_si_el_piso_no_es_de_ningun_vendedor(monkeypatch):
    # Un piso del juego de 700, que cubre a los dos despachados pero no es el
    # piso de ninguno: el piso del juego es el de UN vendedor, el marginal.
    _paso1_con_piso(monkeypatch, 700.0)
    with pytest.raises(ValueError, match="no es el piso de ningun vendedor "
                                         "que puede vender"):
        resuelve_reposo(**S2)
    # Con el piso de verdad, la hora resuelve.
    monkeypatch.undo()
    assert resuelve_reposo(**S2).piso == 693.0


def test_dos_vendedores_de_polvo_en_niveles_distintos_no_tumban_la_hora():
    """Revision de la tarea 5a, importante 1. Reproductor exacto: s = (1,0;
    1e-9; 1e-12) (kWh) con pisos (616,46; 650; 693) y un comprador de 10
    (kWh) con techo 700. La caminata cierra en 650, porque el nivel de 616,46
    se queda 1e-9 por debajo del maximo, pero el filtro de polvo de
    `_despachan` mide sobre otra base y no cuenta al vendedor de 1e-9: con la
    igualdad como guarda, la hora moria con un ValueError falso y la matriz se
    habria detenido. Ahora resuelve, y queda coherente."""
    s = [1.0, 1e-9, 1e-12]
    piso_j = [616.46, 650.0, 693.0]
    r = resuelve_reposo(s, [10.0], [225.0, 241.0, 241.0], 700.0, piso_j)
    assert r.regimen == "un_comprador"
    assert r.piso == r.piso_marginal == 650.0
    assert r.p_u == 650.0 and r.pi_reposo[0] == 650.0
    # El de 693 no despacha; los otros dos venden todo lo que tienen.
    assert r.vendedores_no_despachados == (2,)
    assert _cerca(r.s_despachado, [1.0, 1e-9, 0.0], 0.0)
    assert r.E == pytest.approx(1.0 + 1e-9, rel=1e-15)
    assert abs(float(r.q[0]) - r.E) <= 1e-15
    assert abs(float(r.P.sum()) - r.E) <= 1e-12
    # Cobertura: los dos que venden cobran 650, por encima de sus pisos.
    for j in (0, 1):
        assert r.ingreso_vendedores[j] / r.s_despachado[j] >= piso_j[j] - 1e-6
    # La renta es la del de 616,46, (650 - 616,46)·1,0.
    assert r.renta_inframarginal == pytest.approx(33.54, abs=1e-6)
    assert abs(r.parte_juego) <= 1e-6
    # El paso 1 publico dice lo mismo.
    dh = despacho_competitivo(s, [10.0], 700.0, piso_j)
    assert dh.piso == 650.0 and dh.pueden_vender == (0, 1)
    assert dh.vendedores_no_despachados == (2,)


def test_un_vendedor_marginal_minusculo_si_sube_el_piso_de_la_hora():
    """Revision de la tarea 5a, importante 2. La tolerancia del nivel es una
    guarda de redondeo, no un filtro de vendedores pequenos: con 10 (kWh) en
    el nivel de 616,46 y 1e-7 (kWh) en el de 693, el piso del juego es 693, un
    12 % mas de precio por una diezmillonesima de la energia. Es la subasta de
    precio uniforme, y es el riesgo 2 de Fable: se mide en M-J, no se corrige
    aqui. Se prueba para que el dia que cambie se vea."""
    s = [10.0, 1e-7]
    r = resuelve_reposo(s, [20.0], [225.0, 241.0], 700.0, [616.46, 693.0])
    assert r.piso == 693.0 and r.p_u == 693.0
    assert r.vendedores_no_despachados == ()
    assert r.renta_inframarginal == pytest.approx((693.0 - 616.46) * 10.0)
    # Por debajo de 1e-9 relativo si lo absorbe la guarda de redondeo.
    polvo = resuelve_reposo([10.0, 1e-9], [20.0], [225.0, 241.0], 700.0,
                            [616.46, 693.0])
    assert polvo.piso == 616.46
    assert polvo.vendedores_no_despachados == (1,)
    # Lo que se pierde con la guarda es esa oferta, 1e-9 (kWh) de 10.
    assert polvo.E == pytest.approx(10.0, rel=1e-15)


def test_comprueba_falla_si_un_despachado_cobra_bajo_su_piso(monkeypatch):
    # S2 con sigma = 0: los dos compradores pagan el piso marginal, 693, y el
    # vendedor de 693 cobra justo su piso. Si su ingreso baja 1 (COP) sobre
    # 2 (kWh), cobra 692,5 de media: el teorema de cobertura lo detecta. La
    # descomposicion de la prima sigue cuadrando, porque sale del mismo
    # ingreso.
    import core.reposo_mercado as rm
    real = rm.ingreso_por_vendedor

    def ingreso_bajo(P, p):
        x = real(P, p)
        x[1] -= 1.0
        return x

    kw = dict(s=[2.0, 2.0], d=[3.0, 3.0], b=[225.0, 241.0],
              techo=[731.0, 777.0], piso_j=[350.0, 693.0], sigma=0.0)
    r = resuelve_reposo(**kw)
    assert r.p_u == 693.0 and r.ingreso_vendedores[1] / 2.0 == 693.0
    monkeypatch.setattr(rm, "ingreso_por_vendedor", ingreso_bajo)
    with pytest.raises(ValueError, match="vendedor 1 cobra de media "
                                         "692.5.*bajo su piso 693"):
        resuelve_reposo(**kw)


def test_comprueba_falla_si_la_prima_no_se_descompone(monkeypatch):
    import core.reposo_mercado as rm
    original = rm.ReposoHora

    def corre_la_renta(**kw):
        kw["renta_inframarginal"] = kw["renta_inframarginal"] + 1.0
        return original(**kw)

    monkeypatch.setattr(rm, "ReposoHora", corre_la_renta)
    with pytest.raises(ValueError, match="D69"):
        resuelve_reposo([2.0, 2.0], [3.0, 3.0], [225.0, 241.0],
                        [731.0, 777.0], [350.0, 693.0])


@pytest.mark.parametrize("despacho", DESPACHOS_VENDEDORES)
def test_teorema_de_cobertura_en_horas_al_azar(despacho):
    """Fable, sec. 7, prueba 8 (D63, D67): en 2 000 horas sinteticas con pisos
    y techos al azar, ningun vendedor despachado cobra de media bajo su piso,
    la prima se descompone en renta y parte del juego, la parte del vendedor no
    es negativa y el piso del juego es el mayor piso de los que despachan. Con
    "costo" el lazo puede oscilar y lanzar en voz alta (se cuenta aparte).

    D71 (revision de la tarea Q, I-1). La mitad de los b se sortea en [220,
    230] (COP/kWh), a menos de los 7 que hacen fragil una hora con mu = 1:
    con los b de antes, a 16 o mas, «costo» nunca tenia una hora fragil del
    lado vendedor y la prueba no podia ver que la rama la tumbaba con un D63.
    Con «costo» la rama lanza el ValueError propio de D71 cuando despacharia
    a un vendedor sobre el piso del juego, y la forma cerrada resuelve esa
    hora (se cuenta aparte)."""
    rng = np.random.default_rng(20260917)
    con_mercado = oscilan = varios_pisos = sin_rama = 0
    fragiles = {"compradores": 0, "vendedores": 0}
    for _ in range(2000):
        J, I = int(rng.integers(1, 5)), int(rng.integers(1, 5))
        s = rng.uniform(0.0, 10.0, J) * (rng.random(J) > 0.15)
        d = rng.uniform(0.0, 10.0, I) * (rng.random(I) > 0.15)
        techo = rng.uniform(600.0, 1250.0, I)
        piso_j = rng.choice([150.0, 330.0, 415.0, 616.46, 677.28, 693.0,
                             rng.uniform(100.0, 1200.0)], J)
        b = np.where(rng.random(J) < 0.5,
                     rng.choice([200.0, 225.0, 241.07], J),
                     rng.uniform(220.0, 230.0, J))
        kw = dict(despacho_vendedores=despacho,
                  regla_precio=str(rng.choice(["uniforme", "puja"])),
                  sigma=rng.choice([None, 0.0, 0.5, 1.0]))
        try:
            r = resuelve_reposo(s, d, b, techo, piso_j, **kw)
        except ValueError as e:
            assert despacho == "costo", (despacho, e)
            if "D71 con despacho 'costo'" in str(e):
                assert "mu_cuantal=0.0" in str(e)
                cerrada = resuelve_reposo(s, d, b, techo, piso_j, **kw,
                                          mu_cuantal=0.0)
                assert cerrada.regimen in ("compradores_cortos",
                                           "un_comprador")
                sin_rama += 1
                continue
            assert "oscila" in str(e), (despacho, e)
            with pytest.raises(ValueError, match="oscila"):
                resuelve_reposo(s, d, b, techo, piso_j, **kw, mu_cuantal=0.0)
            oscilan += 1
            continue
        # D71: la forma cerrada de la misma hora. En las horas no fragiles,
        # todo al bit; en las fragiles, las identidades de la sec. 4.
        r0 = resuelve_reposo(s, d, b, techo, piso_j, **kw, mu_cuantal=0.0)
        if r.regimen == "cuantal":
            _identidades_cuantales(r, r0, s, d, techo, piso_j, b=b)
            lado = ("compradores" if np.array_equal(r.s_despachado,
                                                    r0.s_despachado)
                    else "vendedores")
            fragiles[lado] += 1
        else:
            _identicos_al_bit(r, r0)
            assert r.regimen_cerrado == r.regimen
            assert r.apartamiento <= TOL_FRAGIL_REL
        if r.regimen in ("sin_mercado", "sin_ganancia"):
            assert r.renta_inframarginal == r.parte_juego == 0.0
            continue
        con_mercado += 1
        desp = r.s_despachado > TOL_Q * 1e-6
        varios_pisos += len(set(piso_j[desp])) > 1
        medio = r.ingreso_vendedores[desp] / r.s_despachado[desp]
        assert np.all(medio >= piso_j[desp] * (1.0 - 1e-9)), (s, d, piso_j)
        if r.regimen == "cuantal" and despacho == "costo":
            # Con «costo» el despacho cuantal puede dejar en polvo al
            # vendedor que fijaba el piso en la forma cerrada: el piso del
            # juego queda sobre los despachados, que es la desigualdad de D63.
            assert r.piso >= float(piso_j[desp].max())
        else:
            assert r.piso == float(piso_j[desp].max())
        prima = float(r.ingreso_vendedores.sum()
                      - np.dot(piso_j, r.s_despachado))
        assert abs(r.renta_inframarginal + r.parte_juego - prima) <= \
            1e-9 * max(1.0, float(r.ingreso_vendedores.sum()))
        assert r.renta_inframarginal >= -1e-9 and r.parte_juego >= -1e-6
        assert r.parte_vendedor >= -1e-12
        opt, peor = cotas_optimalidad(s, d, techo, piso_j, r.E)
        assert r.excedente <= opt + 1e-6
        # D71: la cota del peor, relativa.
        assert r.excedente >= peor - 1e-9 * max(1.0, abs(peor))
    assert con_mercado > 1000 and varios_pisos > 300
    if despacho != "costo":
        assert oscilan == 0 and sin_rama == 0
    # D71: con techos al azar aparecen horas fragiles del lado comprador. Del
    # lado vendedor: con «llenado» ninguna, porque la respuesta cuantal es el
    # llenado mismo; con «costo», con los b cercanos, unas que resuelven y
    # otras que la rama rechaza con su propio ValueError; con «piso», las que
    # den los pisos del sorteo, casi nunca a menos de 7 (COP/kWh) entre si
    # (ese lado lo cubre `test_la_rama_cuantal_del_lado_vendedor_en_horas_al_
    # azar`).
    assert fragiles["compradores"] > 0, fragiles
    if despacho == "llenado":
        assert fragiles["vendedores"] == 0, fragiles
    if despacho == "costo":
        assert fragiles["vendedores"] > 0 and sin_rama > 0, (fragiles,
                                                             sin_rama)


def test_la_rama_cuantal_del_lado_vendedor_en_horas_al_azar():
    """D71: compradores cortos con los pisos de los vendedores a pocos
    (COP/kWh) entre si, al azar. Las fragiles del lado vendedor cumplen las
    identidades de la sec. 4 (cobertura, piso marginal, D69, la condicion
    del reposo con la clave del piso) y las demas son la forma cerrada al
    bit."""
    rng = np.random.default_rng(20260919)
    fragiles = otras = 0
    for _ in range(1500):
        J, I = int(rng.integers(2, 5)), int(rng.integers(1, 4))
        s = rng.uniform(1.0, 8.0, J)
        d = rng.uniform(0.2, 1.0, I) * s.sum() / I * 0.8
        piso_j = 690.0 + rng.uniform(0.0, 12.0, J)
        techo = rng.uniform(720.0, 800.0, I)
        b = np.full(J, 241.07)
        r = resuelve_reposo(s, d, b, techo, piso_j)
        r0 = resuelve_reposo(s, d, b, techo, piso_j, mu_cuantal=0.0)
        if r.regimen != "cuantal":
            _identicos_al_bit(r, r0)
            otras += 1
            continue
        fragiles += 1
        _identidades_cuantales(r, r0, s, d, techo, piso_j)
        assert np.array_equal(r.q, r0.q)
        assert r.regimen_cerrado in ("compradores_cortos", "un_comprador")
        desp = r.s_despachado > 1e-9 * r.s_despachado.sum()
        medio = r.ingreso_vendedores[desp] / r.s_despachado[desp]
        assert np.all(medio >= piso_j[desp] * (1.0 - 1e-9))
        assert r.piso >= float(piso_j[desp].max()) - 1e-9
        prima = float(r.ingreso_vendedores.sum()
                      - np.dot(piso_j, r.s_despachado))
        assert abs(r.renta_inframarginal + r.parte_juego - prima) <= \
            1e-9 * max(1.0, float(r.ingreso_vendedores.sum()))
        opt, peor = cotas_optimalidad(s, d, techo, piso_j, r.E)
        assert peor - 1e-9 * max(1.0, abs(peor)) <= r.excedente <= opt + 1e-9
    assert fragiles > 100 and otras > 100, (fragiles, otras)


# ─── identidades ───────────────────────────────────────────────────────────

SINTETICOS = [
    dict(s=[2.0, 1.0], d=[5.0, 0.5, 4.0], b=[241.0, 225.0],
         techo=[730.0, 760.0, 780.0], piso_j=[690.0, 650.0]),
    dict(s=[4.0, 1.0, 5.0], d=[3.0, 4.0], b=[241.0, 241.0, 225.0],
         techo=[730.0, 780.0], piso_j=[690.0, 680.0, 620.0]),
    dict(s=[0.66], d=[16.5, 0.24, 0.23], b=[241.0],
         techo=[676.0, 717.0, 732.0], piso_j=[620.0]),
    dict(s=[3.0, 0.0], d=[0.0, 10.0, 0.4], b=[241.0, 225.0],
         techo=[700.0, 730.0, 780.0], piso_j=[690.0, 600.0]),
    # D61 parcial y el piso del vendedor marginal (D63).
    dict(s=[3.0], d=[5.0, 4.0, 6.0], b=[241.0],
         techo=[700.0, 760.0, 780.0], piso_j=[710.0]),
    dict(s=[5.0, 10.0], d=[2.0, 4.0], b=[241.0, 225.0],
         techo=[730.0, 780.0], piso_j=[600.0, 690.0]),
]


def _casos():
    for k in HORAS:
        yield f"hora{k}", _entradas(k)
    for n, c in enumerate(SINTETICOS):
        yield f"sintetico{n}", tuple(np.asarray(c[x], float) for x in CAMPOS)


# D71: los campos de antes de la rama cuantal, que en las horas no fragiles
# son identicos al bit con la rama encendida y apagada.
CAMPOS_ANTES_DE_D71 = tuple(
    f.name for f in dataclasses.fields(ReposoHora)
    if f.name not in ("regimen_cerrado", "apartamiento", "mu_cuantal"))


def _identicos_al_bit(a, b, nombre=""):
    for campo in CAMPOS_ANTES_DE_D71:
        x, y = getattr(a, campo), getattr(b, campo)
        if isinstance(x, np.ndarray):
            assert isinstance(y, np.ndarray) and x.dtype == y.dtype, \
                (nombre, campo)
            assert np.array_equal(x, y), (nombre, campo)
        else:
            assert type(x) is type(y) and x == y, (nombre, campo)


def _identidades_cuantales(r, cerrado, s, d, techo, piso_j, nombre="",
                           b=None):
    """D71, sec. 4 del diseno: lo que cumple una hora «cuantal». La condicion
    del reposo del lado vendedor usa la clave del despacho: el piso con
    "piso", b_j con "costo" (si se da `b`) y una comun con "llenado".
    `cerrado` es la misma hora con `mu_cuantal=0.0`."""
    assert r.regimen == "cuantal" and r.regimen_cerrado == cerrado.regimen
    assert r.apartamiento > TOL_FRAGIL_REL and r.mu_cuantal > 0.0
    for campo in ("piso", "S", "E", "excluidos_bajo_piso",
                  "vendedores_excluidos", "vendedores_no_despachados",
                  "orden_merito"):
        assert getattr(r, campo) == getattr(cerrado, campo), (nombre, campo)
    assert abs(float(r.q.sum()) - r.E) <= 1e-12 * max(1.0, r.E), nombre
    assert abs(float(r.s_despachado.sum()) - r.E) <= 1e-12 * max(1.0, r.E)
    mu = r.mu_cuantal
    juego = (d > 0) & (techo >= r.piso)
    libres = juego & (r.q < d * (1 - 1e-9))
    if libres.sum() > 1:
        v = r.pi_reposo[libres] - mu * np.log(r.q[libres])
        assert float(v.max() - v.min()) <= 1e-9 * max(
            1.0, float(np.abs(r.pi_reposo).max())), nombre
    fuera = list(r.vendedores_excluidos) + list(r.vendedores_no_despachados)
    pueden = (s > 0) & ~np.isin(np.arange(s.size), fuera)
    libres_v = pueden & (r.s_despachado < s * (1 - 1e-9))
    clave = {"piso": piso_j, "costo": b,
             "llenado": np.zeros(s.size)}[r.despacho_vendedores]
    if libres_v.sum() > 1 and clave is not None:
        w = -clave[libres_v] - mu * np.log(r.s_despachado[libres_v])
        assert float(w.max() - w.min()) <= 1e-9 * max(
            1.0, float(np.abs(clave).max())), nombre


@pytest.mark.parametrize("modo", ["sigma", "c136"])
@pytest.mark.parametrize("regla", ["uniforme", "puja"])
@pytest.mark.parametrize("despacho", DESPACHOS_VENDEDORES)
def test_identidades(modo, regla, despacho):
    for nombre, (s, d, b, techo, piso_j) in _casos():
        r = resuelve_reposo(s, d, b, techo, piso_j, modo_presupuesto=modo,
                            regla_precio=regla, despacho_vendedores=despacho)
        # D71: la forma cerrada, con la rama apagada. De las 14 literales y
        # los sinteticos, solo la hora 12 con el presupuesto sigma es fragil;
        # en todas las demas, todo al bit.
        r0 = resuelve_reposo(s, d, b, techo, piso_j, modo_presupuesto=modo,
                             regla_precio=regla, despacho_vendedores=despacho,
                             mu_cuantal=0.0)
        assert r0.mu_cuantal == 0.0 and r0.apartamiento == 0.0, nombre
        assert r0.regimen_cerrado == r0.regimen, nombre
        fragil = nombre == "hora12" and modo == "sigma"
        assert (r.regimen == "cuantal") is fragil, nombre
        if fragil:
            _identidades_cuantales(r, r0, s, d, techo, piso_j, nombre)
        else:
            _identicos_al_bit(r, r0, nombre)
            assert r.regimen_cerrado == r.regimen, nombre
            # Con las opciones de produccion el apartamiento de una hora no
            # fragil es ruido de la biseccion (medido: hasta 3,9e-12). Con
            # "costo" la clave es b_j y dos b a 16 (COP/kWh) dejan 1e-7; con
            # "c136" la 3804 queda a unos 13 (COP/kWh) y deja 1,8e-6: son
            # apartamientos de verdad, bajo el umbral.
            if modo == "sigma" and despacho != "costo":
                assert 0.0 <= r.apartamiento <= 3e-11, (nombre,
                                                        r.apartamiento)
            assert 0.0 <= r.apartamiento <= TOL_FRAGIL_REL, nombre
        assert isinstance(r, ReposoHora) and r.regimen in REGIMENES, nombre
        for campo in ("P", "q", "s_despachado", "pi_reposo", "p_liquidado",
                      "ingreso_vendedores"):
            assert np.all(np.isfinite(getattr(r, campo))), (nombre, campo)
        if r.regimen in ("sin_mercado", "sin_ganancia"):
            assert r.E == 0.0 and not np.any(r.P), nombre
            assert np.array_equal(r.pi_reposo, techo), nombre
            continue
        # En el juego: con deficit y el techo sobre el piso (D61 parcial).
        juego = (d > 0) & (techo >= r.piso)
        assert abs(r.pi_reposo[juego].sum() - r.S) <= 1e-6, nombre
        assert np.allclose(r.P.sum(axis=1), r.s_despachado, rtol=0,
                           atol=1e-12), nombre
        exc = float(np.sum((techo[None, :] - piso_j[:, None]) * r.P))
        assert abs(r.excedente - exc) <= 1e-6, nombre
        assert np.all(r.P >= 0.0), nombre
        assert np.all(r.P.sum(axis=1) <= s + 1e-12), nombre
        assert np.allclose(r.P.sum(axis=0), r.q, rtol=0, atol=1e-12), nombre
        assert abs(r.q.sum() - r.E) <= 1e-12 * max(1.0, r.E), nombre
        # La oferta que cuenta: sin los de D61 ni los no despachados (D65).
        fuera = list(r.vendedores_excluidos) + list(r.vendedores_no_despachados)
        puede = (s > 0) & ~np.isin(np.arange(s.size), fuera)
        assert r.E == pytest.approx(min(s[puede].sum(), d[juego].sum()),
                                    abs=1e-12)
        # D63: el piso es el del marginal y todo despachado queda cubierto;
        # D69: la prima se descompone.
        desp = r.s_despachado > 0.0
        assert r.piso == r.piso_marginal == float(piso_j[desp].max()), nombre
        assert np.all(r.ingreso_vendedores[desp] / r.s_despachado[desp]
                      >= piso_j[desp] * (1.0 - 1e-9)), nombre
        prima = float(r.ingreso_vendedores.sum()
                      - np.dot(piso_j, r.s_despachado))
        assert abs(r.renta_inframarginal + r.parte_juego - prima) <= 1e-9 * \
            max(1.0, float(r.ingreso_vendedores.sum())), nombre
        assert r.parte_vendedor >= 0.0, nombre
        if despacho != "piso":
            assert r.vendedores_no_despachados == (), nombre
        assert np.all(r.p_liquidado[juego] >= r.piso - 1e-9), nombre
        assert np.all(r.p_liquidado <= techo + 1e-9), nombre
        ingreso = float(np.dot(r.p_liquidado, r.q))
        reposo = float(np.dot(r.pi_reposo, r.q))
        assert abs(ingreso - reposo) <= 1e-9 * abs(reposo), nombre
        assert abs(r.ingreso_vendedores.sum() - ingreso) <= 1e-9 * abs(reposo)
        opt, peor = cotas_optimalidad(s, d, techo, piso_j, r.E)
        # D71: la cota del peor, relativa (sec. 4 del diseno): con el
        # despacho cuantal del lado vendedor el excedente puede ser el peor a
        # 1e-11 relativo.
        assert opt + 1e-9 >= r.excedente, nombre
        assert r.excedente >= peor - 1e-9 * max(1.0, abs(peor)), nombre
        assert 0.0 <= captura(r.excedente, opt) <= 1.0 + 1e-12, nombre


# ─── la rama cuantal (D71, tarea Q) ────────────────────────────────────────


@pytest.mark.parametrize("mu", [-1.0, float("nan"), float("inf"), True,
                                "1.0", None, 1e-7, 1e-10, 1e-12])
def test_mu_cuantal_invalido_lanza(mu):
    with pytest.raises(ValueError, match="mu_cuantal"):
        resuelve_reposo(**VALIDA, mu_cuantal=mu)


def test_mu_cuantal_tiene_un_piso_salvo_el_cero():
    """Revision de la tarea Q, M-1: con mu por debajo de 1e-6 la biseccion no
    resuelve la exponencial y la respuesta fallaba en voz alta hasta en horas
    no frageles (la 2120 con 1e-10). Se rechaza al validar, con la pista de
    usar 0; con 1e-6 las literales resuelven y la hora 12 ya no es fragil."""
    assert RM.MU_CUANTAL_MIN == 1e-6
    with pytest.raises(ValueError, match="use 0 para apagar la rama"):
        _resuelve(2120, mu_cuantal=1e-10)
    for k in HORAS:
        r = _resuelve(k, mu_cuantal=1e-6)
        assert r.regimen != "cuantal" and r.mu_cuantal == 1e-6, k
    assert _resuelve(2120, mu_cuantal=0.0).regimen == "excluidos"


def test_con_costo_la_rama_no_despacha_sobre_el_piso_del_juego():
    """Revision de la tarea Q, I-1. Con «costo» pueden vender todos los que
    tienen ganancia posible, pero el piso del juego es el mayor de los que
    despacha la forma cerrada por b_j. Aqui la cerrada despacha solo al de
    b = 225 (piso 600), y la respuesta cuantal con la clave b_j (el otro esta
    a 2 (COP/kWh)) le daria 0,596 (kWh) al de piso 695,68, sobre el piso del
    juego: sin la guarda, D63 lanzaba con otro nombre. La rama no esta
    definida para esa combinacion; la forma cerrada resuelve la hora."""
    kw = dict(s=[5.5, 4.0], d=[2.0, 3.0], b=[225.0, 227.0],
              techo=[734.30, 794.62], piso_j=[600.0, 695.68],
              despacho_vendedores="costo")
    with pytest.raises(ValueError, match="D71 con despacho 'costo'") as e:
        resuelve_reposo(**kw)
    assert "piso 695.680000" in str(e.value)
    assert "sobre el piso del juego 600.000000" in str(e.value)
    assert "mu_cuantal=0.0" in str(e.value) and "D63" not in str(e.value)
    r = resuelve_reposo(**kw, mu_cuantal=0.0)
    assert r.regimen == "compradores_cortos" and r.piso == 600.0
    assert _cerca(r.s_despachado, [5.0, 0.0], 0.0)
    # Con «piso» la misma hora no tiene ese problema: pueden vender solo los
    # de piso <= p*.
    r = resuelve_reposo(**{**kw, "despacho_vendedores": "piso"})
    assert r.regimen != "cuantal" or r.piso >= 695.68


def test_mu_cuantal_admite_enteros_y_numpy():
    base = _resuelve(12)
    for mu in (1, np.float64(1.0), np.int64(1)):
        r = _resuelve(12, mu_cuantal=mu)
        assert r.mu_cuantal == 1.0 and np.array_equal(r.P, base.P)
    assert MU_CUANTAL == 1.0 and TOL_FRAGIL_REL == 1e-3


def test_la_respuesta_cuantal_con_precios_iguales_es_el_llenado():
    q = RM._respuesta_cuantal(4.0, np.array([1.0, 5.0]),
                              np.array([700.0, 700.0]), 1.0)
    assert np.allclose(q, [1.0, 3.0], rtol=0, atol=1e-12)
    # Tres iguales sin tope: exactamente lo mismo, sin desempate por indice.
    q = RM._respuesta_cuantal(3.0, np.array([5.0, 5.0, 5.0]),
                              np.full(3, 735.0), 1.0)
    assert q[0] == q[1] == q[2] and abs(float(q.sum()) - 3.0) <= 4e-16
    # Si la energia cubre las capacidades, las capacidades, sin iterar.
    cap = np.array([1.0, 2.0])
    assert np.array_equal(RM._respuesta_cuantal(3.0, cap,
                                                np.array([0.0, 9.0]), 1.0),
                          cap)
    assert RM._respuesta_cuantal(3.0, np.array([]), np.array([]),
                                 1.0).size == 0


def test_la_respuesta_cuantal_reparte_el_resto_y_suma_e_a_un_ulp():
    """Sin el reparto del resto la suma queda a 1e-11 relativo de E, y el
    residuo de la dinamica en el punto cuantal seria 6e-5 en vez de 1e-10
    (sec. 3.1 del diseno)."""
    E, cap = 6.731972098350525, np.array([3.78, 38.8, 8.27])
    z = np.array([734.30078125, 734.30078125, 735.8939005534])
    q = RM._respuesta_cuantal(E, cap, z, 1.0)
    assert abs(float(q.sum()) - E) <= 2 * np.spacing(E)
    assert np.all(q <= cap) and np.all(q > 0)
    # Con pesos exp(dz/mu): el de precio mayor recibe e^1,59 veces mas.
    assert q[2] / q[0] == pytest.approx(np.exp(z[2] - z[0]), rel=1e-12)
    # Con topes: el topado recibe su capacidad y el resto se reparte.
    q = RM._respuesta_cuantal(10.0, np.array([1.0, 20.0, 20.0]),
                              np.array([800.0, 700.0, 700.0]), 1.0)
    assert q[0] == 1.0 and q[1] == q[2] == pytest.approx(4.5, abs=1e-12)


def test_la_respuesta_cuantal_falla_en_voz_alta(monkeypatch):
    # Una exponencial que no sale finita no pasa en silencio.
    with pytest.raises(ValueError, match="D71"):
        RM._respuesta_cuantal(1.0, np.array([2.0, 2.0]),
                              np.array([700.0, np.nan]), 1.0)


def test_estados_reposo_con_el_servicio_de_siempre_es_el_de_antes():
    # `sirve` por defecto es `_sirve`: la enumeracion de la forma cerrada.
    s, d, b, techo, piso_j = _entradas(12)
    r = _resuelve(12, mu_cuantal=0.0)
    uno = RM._estados_reposo(r.E, d, techo, r.piso, r.S, q_fijo=None)
    dos = RM._estados_reposo(r.E, d, techo, r.piso, r.S, q_fijo=None,
                             sirve=RM._sirve)
    assert len(uno) == len(dos) == 1
    assert np.array_equal(uno[0]["q"], dos[0]["q"])
    assert np.array_equal(uno[0]["z"], dos[0]["z"])


# Los sinteticos del diseno (sec. 6.3), con la tarifa de abril de 2025: techo
# de ASC 734,30, de Cesmag 794,62, piso de permuta 695,68 (techo - Cv).
TA, TC, PA = 734.30, 794.62, 734.30 - 38.62


@pytest.mark.parametrize("caso, regimen, apartamiento, q_cuantal", [
    # k = 3 de ASC en su techo, Cesmag interior a 6,62 (COP/kWh).
    (([5.0], [8.0, 9.0, 7.0, 6.0], [241.07], [TA, TA, TA, TC], [PA]),
     "excluidos", 0.003984, [0.00664, 0.00664, 0.00664, 4.98008]),
    # topados: Cesmag con 0,86·E, topado en la cerrada y no en la cuantal.
    (([6.0], [8.0, 9.0, 5.16], [241.07], [TA, TA, TC], [PA]),
     "topados", 0.149012, [0.86704, 0.86704, 4.26593]),
])
def test_los_sinteticos_fragiles_del_lado_comprador(caso, regimen,
                                                    apartamiento, q_cuantal):
    s, d, b, techo, piso_j = (np.asarray(x, float) for x in caso)
    r = resuelve_reposo(s, d, b, techo, piso_j)
    r0 = resuelve_reposo(s, d, b, techo, piso_j, mu_cuantal=0.0)
    assert r.regimen == "cuantal" and r.regimen_cerrado == regimen
    assert r.apartamiento == pytest.approx(apartamiento, abs=1e-6)
    assert _cerca(r.q, q_cuantal, 1e-5)
    assert np.array_equal(r.pi_reposo, r0.pi_reposo) and r.n_soluciones == 1
    _identidades_cuantales(r, r0, s, d, techo, piso_j)
    # Con Cesmag topada tambien en la cuantal (0,5·E), no es fragil.
    if regimen == "topados":
        r = resuelve_reposo(s, [8.0, 9.0, 3.0], b, techo, piso_j)
        assert r.regimen == "topados" and r.apartamiento < 1e-10


def test_el_sintetico_fragil_del_lado_vendedor():
    """Compradores cortos con dos vendedores de pisos a 2 (COP/kWh): la forma
    cerrada despacha primero el de piso menor; la cuantal, s~_j proporcional a
    exp(-piso_j/mu). Los compradores reciben lo mismo."""
    s, d = np.array([4.5, 4.0]), np.array([2.0, 3.0])
    b, techo = np.array([241.07, 241.07]), np.array([TA, TC])
    piso_j = np.array([PA - 2.0, PA])
    r = resuelve_reposo(s, d, b, techo, piso_j)
    r0 = resuelve_reposo(s, d, b, techo, piso_j, mu_cuantal=0.0)
    assert r0.regimen == "compradores_cortos"
    assert _cerca(r0.s_despachado, [4.5, 0.5], 1e-12)
    assert r.regimen == "cuantal" and r.regimen_cerrado == "compradores_cortos"
    assert r.apartamiento == pytest.approx(0.019203, abs=1e-6)
    assert _cerca(r.s_despachado, [4.40399, 0.59601], 1e-5)
    assert np.array_equal(r.q, r0.q) and np.array_equal(r.pi_reposo,
                                                        r0.pi_reposo)
    assert r.s_despachado[0] / r.s_despachado[1] == pytest.approx(
        np.exp(2.0), rel=1e-12)
    _identidades_cuantales(r, r0, s, d, techo, piso_j)
    # Los dos cobran lo mismo (rango uno), sobre su piso; el de piso bajo,
    # con renta.
    medio = r.ingreso_vendedores / r.s_despachado
    assert medio[0] == pytest.approx(medio[1], rel=1e-12)
    assert np.all(medio >= piso_j) and r.renta_inframarginal > 0.0


def test_la_clave_del_lado_vendedor_es_la_del_despacho():
    """La rama cuantal regulariza el despacho de cada opcion (D71): la forma
    cerrada sigue siendo su limite mu -> 0. Con "llenado" la respuesta
    cuantal es el llenado mismo y nunca es fragil; con "costo" la clave es
    b_j, de modo que dos vendedores de b iguales y pisos a 2 (COP/kWh) no son
    fragiles, y con b a 2 (COP/kWh) si."""
    s, d = np.array([4.5, 4.0]), np.array([2.0, 3.0])
    techo, piso_j = np.array([TA, TC]), np.array([PA - 2.0, PA])
    igual_b = np.array([241.07, 241.07])
    for despacho in ("llenado", "costo"):
        r = resuelve_reposo(s, d, igual_b, techo, piso_j,
                            despacho_vendedores=despacho)
        r0 = resuelve_reposo(s, d, igual_b, techo, piso_j,
                             despacho_vendedores=despacho, mu_cuantal=0.0)
        assert r.regimen == "compradores_cortos" and r.apartamiento < 1e-12
        _identicos_al_bit(r, r0, despacho)
    # Por costo, b a 2 (COP/kWh), y los dos con el mismo piso: fragil.
    r = resuelve_reposo(s, d, [239.07, 241.07], techo, [PA, PA],
                        despacho_vendedores="costo")
    assert r.regimen == "cuantal" and r.apartamiento == pytest.approx(
        0.019203, abs=1e-6)
    assert r.s_despachado[0] / r.s_despachado[1] == pytest.approx(
        np.exp(2.0), rel=1e-12)


def test_con_un_comprador_solo_el_lado_vendedor_puede_ser_fragil():
    s, piso_j = np.array([4.5, 4.0]), np.array([PA - 2.0, PA])
    r = resuelve_reposo(s, [5.0], [241.07, 241.07], [TC], piso_j)
    assert r.regimen == "cuantal" and r.regimen_cerrado == "un_comprador"
    assert r.q[0] == 5.0 and r.pi_reposo[0] == r.piso == PA
    assert r.s_despachado.sum() == pytest.approx(5.0, abs=1e-12)
    # Con vendedores cortos, un comprador recibe E en las dos formas.
    r = resuelve_reposo([3.0], [5.0], [241.07], [TC], [PA])
    assert r.regimen == "un_comprador" and r.apartamiento < 1e-12


def test_sin_mercado_los_campos_de_la_rama_son_neutros():
    for mu in (1.0, 0.0):
        r = resuelve_reposo([0.0], [5.0], [241.0], [730.0], [690.0],
                            mu_cuantal=mu)
        assert r.regimen == r.regimen_cerrado == "sin_mercado"
        assert r.apartamiento == 0.0 and r.mu_cuantal == mu
        r = resuelve_reposo([2.0], [5.0], [241.0], [700.0], [710.0],
                            mu_cuantal=mu)
        assert r.regimen == r.regimen_cerrado == "sin_ganancia"


def test_comprueba_falla_si_la_hora_cuantal_no_es_el_reposo(monkeypatch):
    """Las identidades nuevas de `_comprueba` (D71): una respuesta cuantal
    corrida (la condicion del reposo, pi - mu ln q, deja de ser la misma) o
    una hora con el apartamiento sobre el umbral que no se publica «cuantal»
    fallan en voz alta."""
    original = RM._respuesta_cuantal

    def torcida(E, cap, z, mu):
        x = original(E, cap, z, mu)
        if x.size == 3 and not np.array_equal(x, cap):
            x = x * np.array([1.001, 0.999, 1.0])
            x *= E / x.sum()
        return x

    monkeypatch.setattr(RM, "_respuesta_cuantal", torcida)
    with pytest.raises(ValueError, match="pi - mu·ln q"):
        _resuelve(12)
    monkeypatch.undo()
    import dataclasses as dc
    r = _resuelve(12)
    s, d, b, techo, piso_j = _entradas(12)
    otra = dc.replace(r, regimen="excluidos")
    with pytest.raises(ValueError, match="tendria que ser «cuantal»"):
        RM._comprueba_cuantal(otra, s, d, np.arange(3), (0, 1), piso_j)
    otra = dc.replace(r, apartamiento=5e-4)
    with pytest.raises(ValueError, match="tendria que pasar"):
        RM._comprueba_cuantal(otra, s, d, np.arange(3), (0, 1), piso_j)
    otra = dc.replace(r, regimen_cerrado="cuantal")
    with pytest.raises(ValueError, match="ser de mercado"):
        RM._comprueba_cuantal(otra, s, d, np.arange(3), (0, 1), piso_j)
    otra = dc.replace(r, q=r.q * 1.01)
    with pytest.raises(ValueError, match="suma"):
        RM._comprueba_cuantal(otra, s, d, np.arange(3), (0, 1), piso_j)
    cerrado = _resuelve(12, mu_cuantal=0.0)
    otra = dc.replace(cerrado, apartamiento=0.2)
    with pytest.raises(ValueError, match="rama cuantal apagada"):
        RM._comprueba_cuantal(otra, s, d, np.arange(3), (0, 1), piso_j)


# ─── entradas invalidas y sin mercado ──────────────────────────────────────

VALIDA = dict(s=[2.0], d=[5.0, 4.0], b=[241.0], techo=[730.0, 780.0],
              piso_j=[690.0])


@pytest.mark.parametrize("cambio", [
    {"s": [np.nan]}, {"d": [5.0, np.inf]}, {"b": [np.nan]},
    {"techo": [730.0, np.inf]}, {"piso_j": [np.nan]},
    {"s": [-1.0]}, {"d": [5.0, -0.1]},
    {"b": [241.0, 225.0]}, {"techo": [730.0]}, {"piso_j": [690.0, 690.0]},
    {"d": [[5.0, 4.0]]},
])
def test_entradas_invalidas_lanzan(cambio):
    with pytest.raises(ValueError):
        resuelve_reposo(**{**VALIDA, **cambio})


@pytest.mark.parametrize("kw", [
    {"modo_presupuesto": "otro"}, {"regla_precio": "otra"},
    {"despacho_vendedores": "otro"},
    # El nucleo no admite el alias "merito" (lo traducen el motor y la linea
    # de ordenes, con aviso): sus opciones son las de D64.
    {"despacho_vendedores": "merito"},
    {"sigma": 1.5}, {"sigma": -0.1},
    {"sigma": 0.5, "modo_presupuesto": "c136"},
    {"pi_gs": 780.0},
    {"modo_presupuesto": "algoritmo3"},                   # sin pi_gs
    {"modo_presupuesto": "algoritmo3", "pi_gs": 780.0},   # techo no escalar
])
def test_opciones_invalidas_lanzan(kw):
    with pytest.raises(ValueError):
        resuelve_reposo(**VALIDA, **kw)


def test_algoritmo3_con_el_precio_comun_bajo_el_piso_lanza():
    # H-32: (I-1)/I·pi_gs = 365 < piso 690.
    with pytest.raises(ValueError, match="H-32"):
        resuelve_reposo([2.0], [5.0, 4.0], [241.0], 730.0, [690.0],
                        modo_presupuesto="algoritmo3", pi_gs=730.0)


@pytest.mark.parametrize("s, d, b, techo, piso_j", [
    ([0.0, 0.0], [5.0], [241.0, 225.0], [730.0], [690.0, 690.0]),
    ([2.0], [0.0, 0.0], [241.0], [730.0, 780.0], [690.0]),
    ([], [5.0], [], [730.0], []),
    ([2.0], [], [241.0], [], [690.0]),
])
def test_sin_mercado_no_lanza_energia_en_cero_y_precios_en_el_techo(
        s, d, b, techo, piso_j):
    r = resuelve_reposo(s, d, b, techo, piso_j)
    assert r.regimen == "sin_mercado" and r.n_soluciones == 0
    assert r.P.shape == (len(s), len(d)) and not np.any(r.P)
    assert not np.any(r.q) and not np.any(r.s_despachado)
    assert r.E == 0.0 and r.excedente == 0.0 and r.parte_vendedor == 0.0
    assert r.ell is None and r.vendedores_excluidos == ()
    assert r.excluidos == r.excluidos_bajo_piso == r.orden_merito == ()
    assert r.vendedores_no_despachados == ()
    assert r.renta_inframarginal == r.parte_juego == 0.0
    assert r.piso_marginal == r.piso
    # La convencion de precios de un comprador fuera del juego: su techo.
    assert np.array_equal(r.pi_reposo, np.asarray(techo, float))
    assert np.array_equal(r.p_liquidado, np.asarray(techo, float))
    activos = sum(x > 0 for x in d)
    assert r.sigma == ((activos - 1) / activos if activos else None)


# ─── presupuesto, cotas e ingreso ──────────────────────────────────────────


def test_presupuesto_sigma():
    techo = [730.0, 730.0, 790.0]
    assert presupuesto_precios(techo, 690.0) == pytest.approx(
        3 * 690.0 + 2 / 3 * 180.0)
    assert presupuesto_precios(techo, 690.0, sigma=0.0) == 3 * 690.0
    assert presupuesto_precios(techo, 690.0, sigma=1.0) == pytest.approx(2250.0)
    assert presupuesto_precios([730.0], 690.0) == 690.0


def test_presupuesto_c136_con_el_interruptor_por_jugador():
    # Banda ancha y techo escalar: el arranque comun cae dentro de todas las
    # bandas y S = (I-1)·pi_gs, como el Algoritmo 3.
    assert presupuesto_precios([1250.0] * 5, 114.0, modo="c136") == \
        pytest.approx(5000.0)
    # Mixto: arranque comun 575 fuera de la banda del primero (100 a 300),
    # que arranca en 100 + 200·3/4 = 250; los otros dos y el virtual en 575.
    assert presupuesto_precios([300.0, 1000.0, 1000.0], 100.0, modo="c136") \
        == pytest.approx(250.0 + 3 * 575.0 - 1000.0)


def test_cotas_de_optimalidad_a_mano():
    s, d = [2.0, 1.0], [5.0, 0.5, 4.0]
    techo, piso_j = [730.0, 760.0, 780.0], [690.0, 650.0]
    opt, peor = cotas_optimalidad(s, d, techo, piso_j, 3.0)
    # Optimo: 3 (kWh) al techo 780; despacho 650 y luego 690.
    assert opt == pytest.approx(3 * 780.0 - (650.0 + 2 * 690.0))
    # Peor: 3 al techo 730; despacho 690 y luego 650.
    assert peor == pytest.approx(3 * 730.0 - (2 * 690.0 + 650.0))
    r = resuelve_reposo(s, d, [241.0, 225.0], techo, piso_j)
    assert opt >= r.excedente >= peor
    with pytest.raises(ValueError):
        cotas_optimalidad(s, d, techo, piso_j, 3.5)


def test_captura_con_optimo_nulo_y_casos_sin_sentido():
    assert captura(0.0, 0.0) == 1.0
    assert captura(50.0, 100.0) == 0.5
    with pytest.raises(ValueError):
        captura(101.0, 100.0)
    with pytest.raises(ValueError):
        captura(-1.0, 0.0)
    with pytest.raises(ValueError):
        captura(-1.0, 100.0)


def test_ingreso_por_vendedor():
    P = np.array([[1.0, 2.0], [0.5, 0.0]])
    assert _cerca(ingreso_por_vendedor(P, [700.0, 710.0]),
                  [700.0 + 1420.0, 350.0], 1e-12)
    with pytest.raises(ValueError):
        ingreso_por_vendedor(P, [700.0])
    with pytest.raises(ValueError):
        ingreso_por_vendedor(P, [700.0, np.nan])


# ─── el caso de Chacon, 22:00 ──────────────────────────────────────────────
# Tabla IV del documento extenso (la de `scratchpad/revision_chacon/literal.py`)
# con la clasificacion de `Documentos/copy/JoinFinal.m` (lineas 50 a 59):
# comprador si Glim/Dopt <= 1, con deficit Dopt - Glim; vendedor si >= 1, con
# excedente Glim - Dopt. Banda escalar 114 a 1 250; b = 6,0865·[3,93·52, 32,
# 47, 37, 0, 0] (JoinFinal.m, `data/base_case_data.py`).

GLIM_22 = np.array([2.844, 0.770, 0.0, 1.760, 0.0, 0.0])
DOPT_22 = np.array([3.421, 1.295, 0.534, 0.379, 0.262, 0.208])
B_CHACON = 6.0865 * np.array([3.93 * 52, 32.0, 47.0, 37.0, 0.0, 0.0])


def _chacon_22():
    razon = GLIM_22 / DOPT_22
    compra, vende = razon <= 1, razon >= 1
    return (GLIM_22[vende] - DOPT_22[vende], DOPT_22[compra] - GLIM_22[compra],
            B_CHACON[vende])


def test_chacon_22_con_el_algoritmo_3():
    """La prediccion derivada de la sintesis (sec. 11, M-G): con la ec. 24 y
    el Algoritmo 3, S = (I-1)·pi_gs = 5 000; los dos compradores de menor
    deficit (0,262 y 0,208) quedan en su techo y reciben todo, y los otros tres
    comparten 833,33 y el resto por igual. El nucleo la reproduce. Es una
    prediccion derivada, no medida: la integracion hasta el consenso es M-G."""
    s, d, b = _chacon_22()
    assert _cerca(s, [1.381], 1e-12)
    assert _cerca(d, [0.577, 0.525, 0.534, 0.262, 0.208], 1e-12)
    r = resuelve_reposo(s, d, b, 1250.0, 114.0,
                        modo_presupuesto="algoritmo3", pi_gs=1250.0)
    assert r.S == pytest.approx(5000.0)
    assert r.regimen == "topados" and r.n_soluciones == 1
    assert _cerca(r.pi_reposo, [833.33, 833.33, 833.33, 1250.0, 1250.0], TOL_P)
    assert _cerca(r.q, [0.3037, 0.3037, 0.3037, 0.262, 0.208], 1e-3)
    # Lo que da el nucleo en la liquidacion (no hay prediccion previa):
    # p_u = ingreso/E, parte = (ingreso - 114·E)/(1 136·E).
    assert abs(r.p_u - 975.14) <= TOL_P
    assert abs(r.parte_vendedor - 0.758) <= TOL_PARTE
    # El presupuesto de hoy (C-136) coincide con el Algoritmo 3 en su banda.
    rc = resuelve_reposo(s, d, b, 1250.0, 114.0, modo_presupuesto="c136")
    assert rc.S == pytest.approx(5000.0)
    assert np.allclose(rc.pi_reposo, r.pi_reposo, rtol=0, atol=1e-9)
