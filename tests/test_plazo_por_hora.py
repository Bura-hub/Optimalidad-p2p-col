"""D24: una hora que pasa del plazo se anota como no resuelta y la corrida
sigue; sin plazo, se espera a todas; y el plazo no corre mientras la hora
espera en cola.

Ronda de corrección 1 de la tarea 18: la renovación del pool a mitad de
ventana no pierde ni repite horas; sin horas vencidas, el lazo paralelo da
exactamente lo mismo que la rama secuencial; `run_convergence` no elige una
hora vencida; y la tabla de agentes no rotula «inactivo» a quien tenía papel
en una hora vencida."""
import multiprocessing
import time
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np

from core.ems_p2p import _horas_representativas, _resuelve_con_plazo


@dataclass
class _R:
    k: int
    motivo: str = ""


def _trabajo(j):
    k, dormir = j
    time.sleep(dormir)
    return _R(k=k)


def _vencida(j):
    return _R(k=j[0], motivo="plazo")


class _Barra:
    """Barra de pega: solo cuenta sus `update`."""

    def __init__(self):
        self.n = 0

    def update(self, n=1):
        self.n += n


def test_la_hora_atascada_vence_y_las_demas_terminan():
    jobs = [(0, 0.1), (1, 60.0), (2, 0.1), (3, 0.1)]
    t0 = time.time()
    rmap, vencidas = _resuelve_con_plazo(_trabajo, jobs, procesos=2,
                                         plazo_s=3.0, hace_vencida=_vencida,
                                         latido=0.5)
    assert vencidas == [1]
    assert rmap[1].motivo == "plazo"
    assert all(rmap[k].motivo == "" for k in (0, 2, 3))
    assert time.time() - t0 < 30          # no espera a la hora atascada


def test_sin_plazo_espera_a_todas():
    jobs = [(0, 0.1), (1, 0.5)]
    rmap, vencidas = _resuelve_con_plazo(_trabajo, jobs, procesos=2,
                                         plazo_s=None, hace_vencida=_vencida,
                                         latido=0.2)
    assert vencidas == [] and sorted(rmap) == [0, 1]


def test_la_cola_no_consume_el_plazo():
    # Un solo trabajador y cuatro horas de 1,5 s: la cuarta espera 4,5 s en
    # cola. Con plazo de 3 s medido desde que corre, ninguna vence.
    jobs = [(k, 1.5) for k in range(4)]
    rmap, vencidas = _resuelve_con_plazo(_trabajo, jobs, procesos=1,
                                         plazo_s=3.0, hace_vencida=_vencida,
                                         latido=0.2)
    assert vencidas == [] and sorted(rmap) == [0, 1, 2, 3]


def test_la_renovacion_a_mitad_de_ventana_no_pierde_ni_repite_horas():
    # Ochenta horas de 0,2 s con dos trabajadores; la hora 2 duerme 60 s.
    # La ventana de CAL-43e somete 64 de golpe, de modo que cuando la hora 2
    # vence (unos 1,8 s despues de empezar) el pool viejo tiene una hora
    # sana en vuelo, decenas sometidas en cola y otras aun sin someter. Las
    # tres clases tienen que llegar al pool nuevo sin perderse ni repetirse,
    # y la barra tiene que contar cada hora una sola vez.
    atascada = 2
    jobs = [(k, 60.0 if k == atascada else 0.2) for k in range(80)]
    barra = _Barra()
    t0 = time.time()
    rmap, vencidas = _resuelve_con_plazo(_trabajo, jobs, procesos=2,
                                         plazo_s=1.5, hace_vencida=_vencida,
                                         latido=0.1, bar=barra)
    assert sorted(rmap) == list(range(80))
    assert barra.n == 80
    assert vencidas == [atascada]
    assert rmap[atascada].motivo == "plazo"
    assert all(rmap[k].motivo == "" for k in range(80) if k != atascada)
    assert time.time() - t0 < 60          # no espera al trabajador de 60 s
    # Y al volver no queda ningun trabajador vivo, tampoco el atascado.
    assert multiprocessing.active_children() == []


def test_el_lazo_paralelo_da_lo_mismo_que_el_secuencial():
    # El caso sintetico y el SolverParams de la compuerta C-165, con doce
    # horas: dentro de las primeras 40 no hay horas rigidas, y el plazo de
    # 900 s no puede saltar. Lo que se prueba es el lazo, no el integrador.
    #
    # POR LA VIA ALTERNADA, no la acoplada de la compuerta. Con la acoplada,
    # la rama secuencial de estas doce horas llevaba mas de 280 (s) de CPU en
    # el proceso principal sin terminar (medido el 2026-09-13), y la prueba
    # tiene que tardar segundos. El lazo no depende de la via: somete el
    # mismo trabajo y recoge el mismo resultado por las dos.
    from core.ems_p2p import AgentParams, EMSP2P, GridParams, SolverParams
    from gate_c165_desglose_horario import _caso

    D, G = _caso(T=12)
    N, T = D.shape
    pi_gs = np.full((N, T), 780.0) + np.arange(N)[:, None] * 12.0
    piso = np.full((N, T), 300.0) + np.arange(N)[:, None] * 7.0

    def _corre(paralelo):
        ems = EMSP2P(
            agents=AgentParams(N=N, a=np.zeros(N), b=np.full(N, 225.0),
                               c=np.zeros(N), lam=np.full(N, 100.0),
                               theta=np.full(N, 0.5), etha=np.full(N, 0.1)),
            grid=GridParams(pi_gs=float(np.max(pi_gs)),
                            pi_gb=float(np.min(piso)),
                            pi_gs_agente=pi_gs, pi_gb_agente=piso),
            solver=SolverParams(tau=0.001, tau_buyers=0.01,
                                t_span=(0.0, 0.005), n_points=120,
                                stackelberg_iters=2, parallel=paralelo,
                                metodo="alternado", t_span_acoplado=0.05,
                                buyer_competition="aggregate",
                                procesos=2, plazo_hora_s=900.0),
        )
        resultados, _, _ = ems.run(D, G)
        return resultados

    par = _corre(True)
    sec = _corre(False)
    assert len(par) == len(sec) == T
    con_mercado = 0
    for k in range(T):
        a, b = par[k], sec[k]
        assert a.k == b.k == k
        assert a.motivo == "" and b.motivo == "", f"hora {k} con motivo"
        assert (a.P_star is None) == (b.P_star is None), f"hora {k}"
        assert (a.pi_star is None) == (b.pi_star is None), f"hora {k}"
        if a.P_star is not None:
            con_mercado += 1
            assert np.array_equal(a.P_star, b.P_star), f"P_star, hora {k}"
        if a.pi_star is not None:
            assert np.array_equal(a.pi_star, b.pi_star), f"pi_star, hora {k}"
        assert list(a.seller_ids) == list(b.seller_ids), f"hora {k}"
        assert list(a.buyer_ids) == list(b.buyer_ids), f"hora {k}"
    assert con_mercado >= 1               # si no, la prueba no probaria nada


def test_run_convergence_no_elige_una_hora_vencida():
    # Dos agentes y cuatro horas. La hora 1 tiene el mayor volumen P2P; la
    # hora 2 el mayor deficit (18 kWh), pero vencio el plazo; la 3 le sigue
    # (10 kWh). `run_convergence` resuelve sin plazo en el proceso principal:
    # si eligiera la hora 2 colgaria la corrida justo en la hora perdida.
    D = np.array([[1.0, 1.0, 9.0, 5.0], [1.0, 1.0, 9.0, 5.0]])
    G = np.zeros((2, 4))
    G[:, 1] = [3.0, 0.0]
    res = [SimpleNamespace(k=0, P_star=None, motivo=""),
           SimpleNamespace(k=1, P_star=np.array([[1.0]]), motivo=""),
           SimpleNamespace(k=2, P_star=None,
                           motivo="vencio el plazo por hora de 15 min"),
           SimpleNamespace(k=3, P_star=None, motivo="")]
    assert _horas_representativas(res, D, G, max_hours=2) == [1, 3]
    assert _horas_representativas(res, D, G, max_hours=1) == [1]
    # Sin la hora vencida, la eleccion es la de antes.
    res[2] = SimpleNamespace(k=2, P_star=None, motivo="")
    assert _horas_representativas(res, D, G, max_hours=2) == [1, 2]
    # Y si la unica hora con mercado vencio, no hay nada que dibujar.
    res[1] = SimpleNamespace(k=1, P_star=None, motivo="vencio")
    assert _horas_representativas(res, D, G, max_hours=2) == []


def test_la_hora_vencida_no_rotula_inactivo_a_quien_tenia_papel(tmp_path,
                                                               monkeypatch):
    from core.almacen import Almacen

    # La prueba lee el bufer y no vuelca nada, de modo que no necesita motor
    # de parquet. La comprobacion de C-171 se anula solo aqui: el entorno
    # local no trae pyarrow, y esta prueba no es la que debe detectarlo.
    monkeypatch.setattr("core.almacen._comprueba_motor",
                        lambda comprimir="zstd": None)
    alm = Almacen(tmp_path, cobertura="m1", inicio="2025-04-04")
    nombres = ["A", "B", "C"]
    D = np.array([2.0, 5.0, 3.0])
    G = np.array([6.0, 1.0, 3.0])          # A sobra, B falta, C a la par
    te, pi_ = np.full(3, 800.0), np.full(3, 300.0)

    alm.anota_agentes(0, nombres, D, G, te, pi_,
                      motivo="vencio el plazo por hora de 15 min")
    filas = {f["agente"]: f for f in alm._buf["agentes"] if f["hora"] == 0}
    assert {n: f["papel"] for n, f in filas.items()} == {
        "A": "sin resolver", "B": "sin resolver", "C": "inactivo"}
    # Sin mercado resuelto, todo el sobrante y el faltante cruzan la red.
    assert filas["A"]["vende_red"] == 4.0 and filas["A"]["vende_p2p"] == 0.0
    assert filas["B"]["compra_red"] == 4.0 and filas["B"]["compra_p2p"] == 0.0

    # Sin motivo, lo de siempre.
    alm.anota_agentes(1, nombres, D, G, te, pi_, sids=[0], bids=[1])
    filas = {f["agente"]: f for f in alm._buf["agentes"] if f["hora"] == 1}
    assert {n: f["papel"] for n, f in filas.items()} == {
        "A": "vendedor", "B": "comprador", "C": "inactivo"}
