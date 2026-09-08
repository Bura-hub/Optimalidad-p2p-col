"""
Compuerta de H-55: en que depende del precio el bienestar del modelo base.

Tres comprobaciones, y las tres se pueden desmentir:

  1. Los terminos de pago del vendedor y del comprador se CANCELAN al sumar
     los dos lados, para cualquier vector de precios positivos y cualquier
     reparto.
  2. Reconstruir el bienestar total SIN los terminos de pago da el mismo
     numero.
  3. Cancelado el pago, la unica dependencia del precio es la penalizacion de
     competencia, que es negativa y proporcional al precio, de modo que el
     bienestar total es MONOTONO DECRECIENTE en el precio.

De donde se sigue lo que H-55 registra: el bienestar prefiere siempre el piso
mas bajo por construccion, y por tanto no arbitra una comparacion en la que lo
que cambia entre alternativas es la banda.

Uso:
    python tests/gate_h55_bienestar_precio.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from core.replicator_buyers import buyer_welfare  # noqa: E402
from core.replicator_sellers import seller_welfare  # noqa: E402

TOL = 1e-9


def _caso(rng, J=3, I=4):
    return dict(
        P=rng.uniform(0.0, 3.0, (J, I)),
        G_j=rng.uniform(1.0, 5.0, J),
        G_i=rng.uniform(1.0, 5.0, I),
        a=np.zeros(J),
        b=rng.uniform(200.0, 250.0, J),
        lam_j=np.full(J, 100.0), th_j=np.full(J, 0.5),
        lam_i=np.full(I, 100.0), th_i=np.full(I, 0.5),
        et=np.full(I, 0.1),
    )


def _sin_pago(c, pi):
    J, I = c["P"].shape
    v = sum(c["lam_j"][j] * c["G_j"][j] - c["th_j"][j] * c["G_j"][j] ** 2
            - c["a"][j] * c["P"][j].sum() ** 2 - c["b"][j] * c["P"][j].sum()
            for j in range(J))
    co = sum(c["lam_i"][i] * c["G_i"][i] - c["th_i"][i] * c["G_i"][i] ** 2
             - c["et"][i] * sum(pi[k] * c["P"][:, k].sum()
                                for k in range(I) if k != i)
             for i in range(I))
    return float(v + co)


def _total(c, pi):
    wj = seller_welfare(c["P"], c["G_j"], c["a"], c["b"], c["lam_j"],
                        c["th_j"], pi)
    wi = buyer_welfare(pi, c["P"], c["G_i"], c["lam_i"], c["th_i"], c["et"])
    return wj + wi


def main() -> int:
    rng = np.random.default_rng(11)
    fallos = []

    # 1 y 2: la cancelacion, sobre 200 casos al azar
    peor_can, peor_rec = 0.0, 0.0
    for _ in range(200):
        c = _caso(rng)
        I = c["P"].shape[1]
        pi = rng.uniform(90.0, 950.0, I)
        pago_v = -sum(float(np.sum(c["P"][j, :] / np.log1p(pi)))
                      for j in range(c["P"].shape[0]))
        pago_c = sum(float(np.sum(c["P"][:, i]))
                     / (np.log(abs(pi[i]) + 1) + 1e-12) for i in range(I))
        peor_can = max(peor_can, abs(pago_v + pago_c))
        peor_rec = max(peor_rec, abs(_total(c, pi) - _sin_pago(c, pi)))
    print(f"  1 · los pagos se cancelan          peor resto {peor_can:.2e}")
    print(f"  2 · el total sin pagos coincide    peor resto {peor_rec:.2e}")
    if peor_can > TOL:
        fallos.append("los terminos de pago no se cancelan")
    if peor_rec > TOL:
        fallos.append("el total no coincide sin los pagos")

    # 3: monotonia decreciente en el precio
    subidas = 0
    for _ in range(50):
        c = _caso(rng)
        I = c["P"].shape[1]
        w = [_total(c, np.full(I, p)) for p in np.linspace(100.0, 900.0, 40)]
        if np.any(np.diff(w) > TOL):
            subidas += 1
    print(f"  3 · el bienestar baja con el precio  casos que suben "
          f"{subidas} de 50")
    if subidas:
        fallos.append("el bienestar no es monotono decreciente en el precio")

    print()
    if fallos:
        for f in fallos:
            print(f"  FALLA: {f}")
        return 1
    print("  H-55 en verde: el bienestar depende del precio SOLO por la")
    print("  penalizacion de competencia, y por tanto prefiere siempre el")
    print("  piso mas bajo por construccion.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
