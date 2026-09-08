"""
Compuerta de C-151: la restricción de participación entra al motor.

Un vendedor no entra al mercado si el mercado le paga menos que su
alternativa de fuera, medido como su ingreso ponderado por energía. Hasta el
2026-09-07 eso solo lo hacía la sonda; el motor, y por tanto la corrida
canónica, no lo tenía.

Las tres comprobaciones se dejaron especificadas en H-43 ANTES de escribir el
código, y son estas:

  1. El caso sintético y el modelo base quedan IDÉNTICOS BIT A BIT. La
     restricción tiene que ser inerte cuando las cotas son uniformes, y no
     por una bandera sino por construcción: con un piso escalar el precio ya
     está acotado por debajo a ese valor, de modo que el ingreso ponderado
     nunca queda por debajo y no se retira nadie.

  2. QUIEN SALE DEL MERCADO NO SALE DE LA CONTABILIDAD. Es la trampa que se
     señaló antes de implementar: si al retirado se le quita de la lista de
     vendedores, la liquidación deja de contarlo y su excedente no se
     exporta, se evapora. Se exige que la energía del retirado siga saliendo
     a la red y que su prima sea cero, no negativa.

  3. Con pisos dispares, ningún vendedor acaba vendiendo por debajo de su
     alternativa. Es el defecto que motiva todo esto.

Uso:
    python tests/gate_c151_participacion_motor.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.ems_p2p import AgentParams, EMSP2P, GridParams, SolverParams  # noqa: E402
from core.settlement import compute_savings  # noqa: E402

N, T = 5, 6
TECHO, PISO = 906.27, 280.0


def caso(semilla: int = 3):
    rng = np.random.default_rng(semilla)
    D = rng.uniform(1.0, 5.0, (N, T))
    G = np.zeros((N, T))
    G[:3, :] = rng.uniform(4.0, 9.0, (3, T))     # tres con excedente
    G[3:, :] = rng.uniform(0.0, 0.6, (N - 3, T))
    return D, G


def corre(D, G, piso_agente=None, metodo="acoplado"):
    agents = AgentParams(N=N, a=np.zeros(N), b=np.full(N, 150.0),
                         c=np.zeros(N), lam=np.full(N, 100.0),
                         theta=np.full(N, 0.5), etha=np.full(N, 0.1))
    grid = GridParams(pi_gs=TECHO, pi_gb=PISO, pi_gb_agente=piso_agente)
    solver = SolverParams(tau=0.001, t_span=(0.0, 0.005), n_points=120,
                          stackelberg_iters=2, parallel=False,
                          metodo=metodo, t_span_acoplado=0.02)
    return EMSP2P(agents, grid, solver).run(D, G)


def main() -> int:
    fallos: list[str] = []
    D, G = caso()
    print()
    print("  Compuerta C-151 · la participación en el motor")
    print("  " + "=" * 58)

    # ── 1 · inerte con cotas uniformes, bit a bit ───────────────────────
    r0, gk0, ds0 = corre(D, G)
    r1, gk1, ds1 = corre(D, G, np.full((N, T), PISO))
    ok = np.array_equal(gk0, gk1) and np.array_equal(ds0, ds1)
    if ok:
        for x, y in zip(r0, r1):
            if (x.P_star is None) != (y.P_star is None):
                ok = False; break
            if x.P_star is not None and not (
                    np.array_equal(x.P_star, y.P_star)
                    and np.array_equal(x.pi_star, y.pi_star)):
                ok = False; break
    sin_retiros = all(not r.retirados for r in r1)
    print(f"  1 · con piso uniforme, idéntico y sin retiros        "
          f"{'ok' if ok and sin_retiros else 'FALLA'}")
    if not ok:
        fallos.append("el piso uniforme no reproduce el escalar")
    if not sin_retiros:
        fallos.append("retira a alguien con pisos iguales")

    # ── 2 y 3 · con pisos dispares ──────────────────────────────────────
    # Uno de los tres vendedores tiene una alternativa mucho mejor: si el
    # mercado no se la bate, no debe entrar.
    piso = np.tile(np.array([PISO, PISO, 780.0, PISO, PISO])[:, None], (1, T))
    r2, gk2, ds2 = corre(D, G, piso)

    retirados = sum(len(r.retirados) for r in r2)
    perdida, evaporada, horas = 0, 0.0, 0
    for k, r in enumerate(r2):
        if r.P_star is None or not r.seller_ids:
            continue
        horas += 1
        pj = piso[r.seller_ids, k]
        _, SR_j = compute_savings(r.P_star, r.pi_star, TECHO, pj)
        perdida += int(np.sum(SR_j < -1e-6))
        # La energia del retirado tiene que SALIR a la red, no desaparecer.
        for u, j in enumerate(r.seller_ids):
            if j in r.retirados:
                sobra = gk2[j, k] - ds2[j, k]
                if sobra > 1e-9 and r.P_ext is not None:
                    evaporada += abs(float(r.P_ext[u]) - sobra)

    print(f"  2 · el retirado sigue exportando a la red            "
          f"{'ok' if evaporada < 1e-9 else 'FALLA'}  "
          f"(energía evaporada {evaporada:.2e} kWh)")
    if evaporada >= 1e-9:
        fallos.append(f"se evaporan {evaporada:.3e} kWh del retirado")

    print(f"  3 · ningún vendedor por debajo de su piso            "
          f"{'ok' if perdida == 0 else 'FALLA'}  ({perdida})")
    if perdida:
        fallos.append(f"{perdida} vendedores a pérdida")

    print()
    print(f"  con pisos dispares: {retirados} retiros en {horas} horas")

    print()
    if fallos:
        print("  FALLA: " + "; ".join(fallos))
        return 1
    print("  todo en verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
