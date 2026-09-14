"""
tests/test_oraculo_anexo4.py -- oraculo del Anexo 4 de la CREG 101 072
(subproyecto 2, paso 1; brief en
.superpowers/sdd/2026-09-14-oraculo-anexo4/brief.md).

Compuerta de tres niveles, de menor a mayor dependencia de datos:

  1. `liquida_mes` a mano, sobre meses de juguete de seis horas, con el
     resultado calculado en el comentario: un caso sin hx, uno con hx a
     mitad de hora y uno con empate exacto.
  2. `liquida_mes` contra el motor (`run_c1_creg174`) sobre datos sinteticos
     de pocas horas y dos meses (sin datos reales), con los dos numerales
     del articulo 25.
  3. La comparacion completa (`compara`) contra datos reales (m1, factor 1),
     que se salta si `MedicionesMTE_v3` no esta disponible en esta maquina.

El oraculo (`liquida_mes`) esta escrito desde el texto de la norma, sin
llamar a `reparto_anexo4`, `deduccion_art25` ni `tramo_permuta`; estas
pruebas si pueden llamar al motor (`run_c1_creg174`), porque lo que se
verifica es que el oraculo REPRODUCE lo que el motor liquida, no al reves.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reformateo" / "documento" / "scripts" / "sonda"))

from oraculo_anexo4 import (  # noqa: E402
    LIMITE_NUMERAL_1_KW, UMBRAL_DINERO_COP, UMBRAL_ENERGIA_KWH, compara,
    liquida_mes,
)


# ─── 1 · liquida_mes a mano ─────────────────────────────────────────────────


def test_liquida_mes_sin_hx():
    # G = [6,0,6,0,6,0]  D = [5,5,5,5,5,5]
    # exp = [1,0,1,0,1,0]  imp = [0,5,0,5,0,5]  -> Imp = 15
    # acumulado de exp: 1,1,2,2,3,3 -- nunca alcanza 15 (Imp): todo credito.
    # auto = min(G,D) = [5,0,5,0,5,0] -> auto = 15; credito = 3 (= exp
    # total); exceso = 0; hx = None.
    G_h = np.array([6.0, 0.0, 6.0, 0.0, 6.0, 0.0])
    D_h = np.array([5.0, 5.0, 5.0, 5.0, 5.0, 5.0])
    cu_h = np.full(6, 800.0)
    ded_h = np.full(6, 50.0)
    bolsa_h = np.array([90.0, 95.0, 100.0, 105.0, 110.0, 115.0])
    r = liquida_mes(G_h, D_h, cu_h, ded_h, bolsa_h)
    assert r["auto"] == pytest.approx(15.0)
    assert r["credito"] == pytest.approx(3.0)
    assert r["exceso"] == pytest.approx(0.0)
    assert r["hx"] is None
    # dinero_auto = 15 * 800 = 12000
    # dinero_credito = 3 * (800 - 50) = 2250
    # dinero_exceso = 0 (no hay exceso, el precio de bolsa no cuenta)
    assert r["dinero_auto"] == pytest.approx(12000.0)
    assert r["dinero_credito"] == pytest.approx(2250.0)
    assert r["dinero_exceso"] == pytest.approx(0.0)
    assert r["dinero_total"] == pytest.approx(14250.0)


def test_liquida_mes_hx_a_mitad_de_hora():
    # G = [2,2,3,4,0,0]  D = [0,0,0,0,5,0]
    # exp = [2,2,3,4,0,0]  imp = [0,0,0,0,5,0]  -> Imp = 5
    # acumulado: 2,4,7,11,11,11 -- cruza en h=2 (7 >= 5): de los 3 kWh de
    # esa hora, 2 (= 7-5) son exceso y 1 es credito; desde h=3 toda la
    # exportacion es exceso. credito = 2+2+1 = 5 (= Imp); exceso = 2+4 = 6;
    # auto = 0 (G y D nunca son positivos en la misma hora); hx = 2.
    G_h = np.array([2.0, 2.0, 3.0, 4.0, 0.0, 0.0])
    D_h = np.array([0.0, 0.0, 0.0, 0.0, 5.0, 0.0])
    cu_h = np.full(6, 800.0)
    ded_h = np.full(6, 50.0)
    bolsa_h = np.array([100.0, 110.0, 120.0, 130.0, 140.0, 150.0])
    r = liquida_mes(G_h, D_h, cu_h, ded_h, bolsa_h)
    assert r["auto"] == pytest.approx(0.0)
    assert r["credito"] == pytest.approx(5.0)
    assert r["exceso"] == pytest.approx(6.0)
    assert r["hx"] == 2
    # dinero_credito = 5 * (800 - 50) = 3750
    # dinero_exceso = 2*120 (hora 2, parte que excede) + 4*130 (hora 3) =
    #               = 240 + 520 = 760
    assert r["dinero_auto"] == pytest.approx(0.0)
    assert r["dinero_credito"] == pytest.approx(3750.0)
    assert r["dinero_exceso"] == pytest.approx(760.0)
    assert r["dinero_total"] == pytest.approx(4510.0)


def test_liquida_mes_empate_exacto():
    # G = [3,0,2,0,0,0]  D = [0,5,0,0,0,0]
    # exp = [3,0,2,0,0,0]  imp = [0,5,0,0,0,0]  -> Imp = 5
    # acumulado: 3,3,5,5,5,5 -- IGUALA en h=2 (5 >= 5); el exceso de esa
    # hora es 5-5 = 0 (empate exacto: la norma dice "iguala o sobrepasa",
    # de modo que h=2 SI es la hora de corte, aunque no reparta exceso).
    # Desde h=3 toda exportacion seria exceso, pero ya no hay mas. credito
    # = 3+0+2 = 5 (= Imp); exceso = 0; auto = 0; hx = 2.
    G_h = np.array([3.0, 0.0, 2.0, 0.0, 0.0, 0.0])
    D_h = np.array([0.0, 5.0, 0.0, 0.0, 0.0, 0.0])
    cu_h = np.full(6, 800.0)
    ded_h = np.full(6, 50.0)
    bolsa_h = np.array([200.0, 210.0, 220.0, 230.0, 240.0, 250.0])
    r = liquida_mes(G_h, D_h, cu_h, ded_h, bolsa_h)
    assert r["auto"] == pytest.approx(0.0)
    assert r["credito"] == pytest.approx(5.0)
    assert r["exceso"] == pytest.approx(0.0)
    assert r["hx"] == 2
    assert r["dinero_auto"] == pytest.approx(0.0)
    assert r["dinero_credito"] == pytest.approx(3750.0)
    assert r["dinero_exceso"] == pytest.approx(0.0)
    assert r["dinero_total"] == pytest.approx(3750.0)


# ─── 2 · liquida_mes contra el motor, con datos sinteticos ─────────────────


def test_liquida_mes_reproduce_al_motor_sintetico():
    """Tres agentes, dos meses de ocho horas, los dos numerales del art. 25.

    El agente 1 tiene una capacidad de 150 kW (numeral 2: se descuenta
    Cv + T+D+PR+R); los agentes 0 y 2, 50 y 17,55 kW (numeral 1: solo Cv).
    Se compara el dinero TOTAL de cada agente sobre los dos meses (la suma
    de `liquida_mes` por mes) contra `neto_horario` del motor.
    """
    from scenarios.scenario_c1_creg174 import run_c1_creg174

    rng = np.random.default_rng(2026)
    N, T = 3, 16
    G = rng.uniform(0.0, 8.0, (N, T))
    D = rng.uniform(0.0, 5.0, (N, T))
    cu = rng.uniform(700.0, 900.0, (N, T))       # techo (CU)
    cvm = rng.uniform(30.0, 60.0, (N, T))        # componente Cv
    peaje = rng.uniform(200.0, 400.0, (N, T))    # T+D+PR+R
    bolsa = rng.uniform(100.0, 400.0, T)
    etiquetas = np.array([202501] * 8 + [202502] * 8)
    capacidad_kw = np.array([50.0, 150.0, 17.55])

    resultado = run_c1_creg174(
        D, G, cu, bolsa, list(range(N)), month_labels=etiquetas,
        component_c=cvm, capacidad_kw=capacidad_kw, tolls=peaje)
    neto_horario = resultado["neto_horario"]

    meses = sorted(set(etiquetas.tolist()))
    for n in range(N):
        numeral = 1 if capacidad_kw[n] <= LIMITE_NUMERAL_1_KW else 2
        ded_n = cvm[n, :] if numeral == 1 else cvm[n, :] + peaje[n, :]
        oraculo_total = 0.0
        for mes in meses:
            horas = np.flatnonzero(etiquetas == mes)
            r = liquida_mes(G[n, horas], D[n, horas], cu[n, horas],
                            ded_n[horas], bolsa[horas])
            oraculo_total += r["dinero_total"]
        motor_total = float(np.sum(neto_horario[n, :]))
        assert oraculo_total == pytest.approx(motor_total,
                                              abs=UMBRAL_DINERO_COP), (
            f"agente {n} (numeral {numeral}): oraculo={oraculo_total:.4f} "
            f"motor={motor_total:.4f}")


# ─── 3 · comparacion completa con datos reales ─────────────────────────────


def test_compara_datos_reales_base():
    mte_root = Path(os.environ.get("MTE_ROOT", str(ROOT / "MedicionesMTE_v3")))
    if not mte_root.is_dir():
        pytest.skip("MedicionesMTE_v3 no disponible")

    r = compara(1.0)
    assert r["numeral"] == 1
    assert len(r["df"]) > 0
    assert r["dif_dinero_max"] <= UMBRAL_DINERO_COP, (
        f"diferencia de dinero {r['dif_dinero_max']:.4f} (COP) por encima "
        f"del umbral {UMBRAL_DINERO_COP:g}")
    assert r["dif_energia_max"] <= UMBRAL_ENERGIA_KWH, (
        f"diferencia de energia {r['dif_energia_max']:.9f} (kWh) por "
        f"encima del umbral {UMBRAL_ENERGIA_KWH:g}")


def test_compara_datos_reales_factor_7():
    """El numeral 2 y el tramo del exceso, con datos reales (arreglo final).

    Con la generacion por siete cada planta pasa de 100 (kW) (122,85), de
    modo que la deduccion es la del numeral 2 (Cv + T + D + PR + R), y la
    exportacion del mes alcanza la importacion en la mayoria de los meses:
    hay hora de corte y tramo del exceso a bolsa. El caso de la base (factor
    1) no ejerce ni lo uno ni lo otro. Se salta igual que el de la base si
    faltan las mediciones.
    """
    mte_root = Path(os.environ.get("MTE_ROOT", str(ROOT / "MedicionesMTE_v3")))
    if not mte_root.is_dir():
        pytest.skip("MedicionesMTE_v3 no disponible")

    r = compara(7.0)
    assert r["numeral"] == 2
    assert len(r["df"]) > 0
    # El tramo del exceso se ejerce de verdad: meses con hora de corte y
    # energia del exceso, en la MISMA hora en el oraculo y en el motor.
    assert r["con_corte_oraculo"] > 0
    assert r["con_corte_oraculo"] == r["con_corte_motor"]
    assert r["hx_distinta"] == 0
    assert float(r["df"].exceso_kwh.sum()) > 0.0
    assert r["dif_dinero_max"] <= UMBRAL_DINERO_COP, (
        f"diferencia de dinero {r['dif_dinero_max']:.4f} (COP) por encima "
        f"del umbral {UMBRAL_DINERO_COP:g}")
    assert r["dif_energia_max"] <= UMBRAL_ENERGIA_KWH, (
        f"diferencia de energia {r['dif_energia_max']:.9f} (kWh) por "
        f"encima del umbral {UMBRAL_ENERGIA_KWH:g}")
