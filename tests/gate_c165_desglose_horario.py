"""
Compuerta de C-165: el desglose por hora suma exactamente el total publicado.

QUE FALTABA. El beneficio de cada mecanismo solo existia **agregado al
horizonte entero**. De modo que no habia con que contestar en que meses y en
que horas un mecanismo reparte mejor que otro, que es media pregunta del
capitulo de equidad y toda la de la discusion de precios.

COMO SE HIZO, y por que asi. Cada escenario anota su dinero **en la hora que
lo genera**, con los mismos vectores con los que ya calculaba el total, antes
de sumarlos. No hay una segunda implementacion que pueda derivar de la primera:
hay una sola cuenta que ademas guarda el paso intermedio.

Y ESTA COMPUERTA LO FUERZA. Para cada mecanismo comprueba que la matriz suma
por filas **exactamente** el beneficio por agente que el motor reporta. Si
alguien toca una de las dos cuentas y no la otra, se entera aqui.

LA QUE FALTA A PROPOSITO. La segunda granularidad del colectivo valora contra
promedios MENSUALES. Repartir su dinero entre las horas del mes seria inventar
una precision que la liquidacion no tiene, de modo que no tiene desglose
horario y la compuerta comprueba que **no lo finge**.

Uso:
    python tests/gate_c165_desglose_horario.py
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402

TOL = 1e-7


def _caso(N=5, T=72, semilla=19):
    """Comunidad sintetica con mercado activo y las dos cotas por agente."""
    rng = np.random.default_rng(semilla)
    D = rng.uniform(3.0, 14.0, (N, T))
    G = np.zeros((N, T))
    for k in range(T):
        h = k % 24
        if 6 <= h <= 18:
            G[:, k] = rng.uniform(0.0, 20.0, N) * np.sin(np.pi * (h - 6) / 12)
    return D, G


def main() -> int:
    from core.ems_p2p import AgentParams, EMSP2P, GridParams, SolverParams
    from scenarios.comparison_engine import run_comparison

    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--horas', type=int, default=72)
    args = ap.parse_args()

    D, G = _caso(T=args.horas)
    N, T = D.shape
    pi_gs = np.full((N, T), 780.0) + np.arange(N)[:, None] * 12.0
    piso = np.full((N, T), 300.0) + np.arange(N)[:, None] * 7.0
    pi_bolsa = np.full(T, 190.0)
    pde = np.full(N, 1.0 / N)

    ems = EMSP2P(
        agents=AgentParams(N=N, a=np.zeros(N), b=np.full(N, 225.0),
                           c=np.zeros(N), lam=np.full(N, 100.0),
                           theta=np.full(N, 0.5), etha=np.full(N, 0.1)),
        grid=GridParams(pi_gs=float(np.max(pi_gs)), pi_gb=float(np.min(piso)),
                        pi_gs_agente=pi_gs, pi_gb_agente=piso),
        solver=SolverParams(tau=0.001, tau_buyers=0.01, t_span=(0.0, 0.005),
                            n_points=120, stackelberg_iters=2, parallel=True,
                            metodo="acoplado", t_span_acoplado=0.05,
                            buyer_competition="aggregate"),
    )
    resultados, G_klim, _ = ems.run(D, G)

    cr = run_comparison(
        D=D, G_klim=G_klim, G_raw=G, p2p_results=resultados,
        pi_gs=pi_gs, pi_gb=float(np.min(piso)), pi_bolsa=pi_bolsa,
        prosumer_ids=list(range(N)), consumer_ids=[], pde=pde,
        piso_agente=piso, pi_contrato=None, component_c=0.0,
    )

    fallos = []
    print(f"  comunidad de {N} agentes sobre {T} horas\n")
    for esc in ("P2P", "C1", "C2", "C3", "C4"):
        m = cr.neto_horario.get(esc)
        objetivo = np.asarray(cr.net_benefit_per_agent[esc], dtype=float)
        if m is None:
            print(f"  {esc:<4}· sin desglose horario   FALLA")
            fallos.append(f"{esc} no devuelve desglose horario")
            continue
        m = np.asarray(m, dtype=float)
        if m.shape != (N, T):
            print(f"  {esc:<4}· forma {m.shape}, se esperaba {(N, T)}   FALLA")
            fallos.append(f"{esc} devuelve una matriz de forma equivocada")
            continue
        suma = m.sum(axis=1)
        d = float(np.max(np.abs(suma - objetivo)))
        esc_rel = d / max(float(np.max(np.abs(objetivo))), 1e-12)
        ok = esc_rel <= TOL
        print(f"  {esc:<4}· la matriz suma el total por agente   "
              f"dif rel {esc_rel:.2e}   {'ok' if ok else 'FALLA'}")
        if not ok:
            fallos.append(f"el desglose de {esc} no suma su propio total")

    # La granularidad mensual del colectivo NO finge tener desglose horario.
    if "C4_mensual" in cr.net_benefit:
        ok_m = cr.neto_horario.get("C4_mensual") is None
        print(f"\n  la granularidad mensual del colectivo no finge desglose "
              f"horario   {'ok' if ok_m else 'FALLA'}")
        if not ok_m:
            fallos.append("la rama mensual inventó un desglose horario")

    # Y una comprobacion de sentido: agregando por mes de 720 horas, la suma
    # de los meses vuelve a dar el total. Es la operacion que el capitulo de
    # equidad va a hacer, y conviene que este probada.
    m = np.asarray(cr.neto_horario["P2P"], dtype=float)
    trozos = [m[:, i:i + 24].sum(axis=1) for i in range(0, T, 24)]
    d = float(np.max(np.abs(np.sum(trozos, axis=0)
                            - np.asarray(cr.net_benefit_per_agent["P2P"]))))
    ok = d <= 1e-6 * max(float(np.max(np.abs(m))), 1.0)
    print(f"  agregando por días y volviendo a sumar, el total se conserva   "
          f"dif {d:.3e}   {'ok' if ok else 'FALLA'}")
    if not ok:
        fallos.append("la agregación por período pierde dinero")

    print()
    if fallos:
        for x in fallos:
            print(f"  FALLA: {x}")
        return 1
    print("  C-165 EN VERDE. Cada mecanismo anota su dinero en la hora que lo")
    print("  genera, y esa anotación suma exactamente el total que el motor")
    print("  publica. De ahí salen las métricas por mes y por hora sin volver")
    print("  a simular, y la tabla de escenarios del almacén.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
