"""
Compuerta de H-44: la aptitud del replicador y el bienestar que se reporta.

El bloque de precios mueve cada precio segun una aptitud. Esa aptitud **si
es un gradiente**, pero del bienestar tal como lo escribe el DOCUMENTO
EXTENSO del modelo base, no del de la version arbitrada, que es el que la
funcion `buyer_welfare` reporta.

    aptitud = grad(bienestar del documento extenso)
              - competencia            <- no es gradiente de nada
              + senal de restriccion   <- tampoco

De modo que **la dinamica del modelo base no deriva de su propio bienestar
publicado**. No es un defecto de esta traduccion: esta asi en el fichero
original. Aqui se fija esa relacion para que nadie «arregle» uno de los dos
lados y deje al documento afirmando algo falso.

Comprueba cuatro cosas:

  1. la aptitud coincide con el gradiente del termino de pago del documento
     extenso;
  2. NO coincide con el de la version arbitrada, que difiere en tres ordenes
     de magnitud;
  3. el termino de competencia aporta CERO al gradiente en las tres formas,
     porque en ninguna interviene el precio propio del comprador;
  4. la formula de la aptitud que esta compuerta usa sigue siendo la que el
     nucleo tiene escrita.

Uso:
    python tests/gate_h44_aptitud_gradiente.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

FUENTE = RAIZ / "core" / "replicator_buyers.py"
# La linea que el nucleo tiene escrita para la aptitud del pago.
APTITUD_ESPERADA = "pagos = -pi_gb * sum_Pji / (pi_real + 1.0)"


def caso(semilla=4, J=3, I=4):
    rng = np.random.default_rng(semilla)
    P = rng.uniform(0.3, 3.0, (J, I))
    return dict(P=P, q=P.sum(axis=0), pi=rng.uniform(250.0, 850.0, I),
                etha=rng.uniform(0.05, 0.5, I), pi_gb=200.0, I=I)


def competencia(d, forma):
    I, M = d["I"], np.ones((d["I"], d["I"])) - np.eye(d["I"])
    if forma == "aggregate":
        return d["etha"].mean() * d["q"]
    if forma == "matlab":
        return (M.T @ d["etha"]) * d["q"]
    return d["etha"] * (M @ (d["pi"] * d["q"]))


def gradiente(d, pago, forma, h=1e-6):
    """d W_i / d pi_i, numérico, para el término de pago que se le pase."""
    g = np.zeros(d["I"])
    for i in range(d["I"]):
        val = []
        for s in (+1, -1):
            pi = d["pi"].copy(); pi[i] += s * h
            dd = dict(d, pi=pi)
            val.append(pago(dd)[i] - competencia(dd, forma)[i])
        g[i] = (val[0] - val[1]) / (2 * h)
    return g


# los dos términos de pago que las fuentes escriben
PAGO_EXTENSO = lambda d: -d["pi_gb"] * d["q"] * np.log(np.abs(d["pi"]) + 1.0)
PAGO_ARBITRADO = lambda d: d["q"] / np.log(np.abs(d["pi"]) + 1.0)


def main() -> int:
    fallos = []
    d = caso()
    # la aptitud tal como la escribe el núcleo
    apt = -d["pi_gb"] * d["q"] / (d["pi"] + 1.0)
    print(f"  aptitud del replicador        "
          f"{np.array2string(apt, precision=4)}")

    # ---- 1 · es el gradiente del documento extenso ---------------------
    g_ext = gradiente(d, PAGO_EXTENSO, "aggregate")
    ok1 = np.allclose(g_ext, apt, rtol=1e-4)
    print(f"\n  1 · gradiente del documento extenso                "
          f"{'ok' if ok1 else 'FALLA'}")
    print(f"      {np.array2string(g_ext, precision=4)}")
    if not ok1:
        fallos.append("la aptitud dejó de ser el gradiente del documento extenso")

    # ---- 2 · NO es el de la versión arbitrada --------------------------
    g_arb = gradiente(d, PAGO_ARBITRADO, "matrix")
    razon = float(np.max(np.abs(apt)) / np.max(np.abs(g_arb)))
    ok2 = not np.allclose(g_arb, apt, rtol=1e-2)
    print(f"\n  2 · NO es el de la versión arbitrada               "
          f"{'ok' if ok2 else 'FALLA'}")
    print(f"      {np.array2string(g_arb, precision=6)}")
    print(f"      difieren por un factor de {razon:,.0f}"
          .replace(",", " "))
    if not ok2:
        fallos.append("la compuerta ya no distingue las dos definiciones")

    # ---- 3 · la competencia no entra en el gradiente -------------------
    grads = {f: gradiente(d, PAGO_EXTENSO, f)
             for f in ("aggregate", "matlab", "matrix")}
    iguales = all(np.allclose(grads["aggregate"], v) for v in grads.values())
    print(f"\n  3 · la competencia aporta cero al gradiente        "
          f"{'ok' if iguales else 'FALLA'}")
    print(f"      las tres formas dan el mismo gradiente, porque en ninguna")
    print(f"      interviene el precio propio del comprador")
    if not iguales:
        fallos.append("alguna forma de competencia sí entra en el gradiente")

    # ---- 4 · la fórmula sigue siendo la del núcleo ---------------------
    texto = FUENTE.read_text(encoding="utf-8", errors="replace")
    presente = APTITUD_ESPERADA in re.sub(r"[ \t]+", " ", texto)
    print(f"\n  4 · la fórmula es la que el núcleo tiene escrita   "
          f"{'ok' if presente else 'FALLA'}")
    if not presente:
        fallos.append(f"no encuentro «{APTITUD_ESPERADA}» en el núcleo; "
                      "si cambió, hay que rehacer esta compuerta y H-44")

    print()
    if fallos:
        for f in fallos:
            print(f"  FALLA: {f}")
        return 1
    print("  COMPUERTA H-44 EN VERDE")
    print("  La dinámica del modelo base NO deriva de su bienestar publicado.")
    print("  Es una propiedad del modelo de origen, no de esta traducción.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
