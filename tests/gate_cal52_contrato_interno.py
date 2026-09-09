"""
Compuerta de CAL-52: el contrato interno, y las dos propiedades que lo sostienen.

QUE ESCENARIO ES. Los miembros de la comunidad intercambian **la misma energia**
que intercambiarian en el mercado entre pares, pero a un precio pactado de
antemano —el punto medio de la banda de cada pareja— en vez de a uno formado
por el juego. Es lo que un contrato de suministro hace: fijar el precio.

POR QUE ES LA COMPARACION QUE LE FALTABA. Aisla exactamente lo que aporta el
mecanismo dinamico. Mismos flujos, misma comunidad, misma energia: lo unico que
cambia es como se forma el precio. Si el contrato diera lo mismo, la dinamica de
replicador no estaria aportando nada, y eso hay que saberlo antes de que lo
pregunte un jurado.

LAS CINCO COSAS QUE ESTA COMPUERTA PRUEBA:

  1. EL REPARTO ES EXACTO A LA MITAD. El punto medio de la banda deja al
     comprador y al vendedor con la misma parte, luego el indice de reparto vale
     cero. No es un ajuste: sale de la aritmetica.
  2. LA IDENTIDAD DE H-33 SE CUMPLE AL DECIMAL. El excedente es el ancho de la
     banda por la energia transada, **cualquiera que sea el precio pactado**.
     Es la misma identidad que rige el mercado entre pares, y por eso los dos
     son comparables.
  3. EL PRECIO PACTADO CAE DENTRO DE LA BANDA de cada pareja, que es lo que lo
     hace aceptable para las dos partes: ninguna esta peor que yendo a la red.
     Y CUANDO NO PUEDE, no se firma. Nada garantiza que el techo del comprador
     este por encima del piso del vendedor: son dos agentes con dos tarifas.
     Con la banda invertida no hay precio que sirva, y esa energia se trata
     como la que el mercado no coloca. Esta compuerta lo fuerza a proposito,
     porque en los datos de hoy la banda se invierte en el 0,036 % y el 1,900 %
     de las parejas-hora pero **nunca en una con papeles compatibles** (H-64):
     sin forzarlo, la guarda nunca se ejercitaria.
  4. EL EXCEDENTE NO DEPENDE DEL PRECIO. Movido el reparto a un tercio o a dos
     tercios de la banda, el total no se mueve; solo cambia quien se lo lleva.
     Es la comprobacion directa de que este escenario mide **reparto**, no
     tamaño de la torta.
  5. NO SE INVENTA ENERGIA. La que el contrato liquida es exactamente la que el
     mercado asigno.

Uso:
    python tests/gate_cal52_contrato_interno.py
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402


def _caso(N=5, T=48, semilla=7):
    """Flujos sinteticos con la forma de los reales: pocas parejas por hora."""
    rng = np.random.default_rng(semilla)
    techo = rng.uniform(700.0, 950.0, (N, T))
    piso = techo - rng.uniform(120.0, 260.0, (N, T))
    flujos = []
    for k in range(T):
        nv = int(rng.integers(1, 3))
        nc = int(rng.integers(1, 4))
        ids = rng.permutation(N)
        sids, bids = list(ids[:nv]), list(ids[nv:nv + nc])
        if not bids:
            continue
        P = rng.uniform(0.0, 6.0, (len(sids), len(bids)))
        # Parejas casi nulas a proposito: no deben romper nada ni contarse.
        P[rng.random(P.shape) < 0.25] = 0.0
        flujos.append((k, sids, bids, P))
    return flujos, techo, piso, N


def main() -> int:
    from scenarios._c2_interno import contrato_interno

    flujos, techo, piso, N = _caso()
    r = contrato_interno(flujos, techo, piso, N)
    fallos = []

    # 1 · el reparto es exacto a la mitad
    ok1 = abs(r["equidad"]) <= 1e-12
    print(f"  1 · el reparto es exacto a la mitad   índice {r['equidad']:+.3e}"
          f"   {'ok' if ok1 else 'FALLA'}")
    if not ok1:
        fallos.append("el punto medio no reparte la banda a la mitad")

    # 2 · la identidad de H-33
    banda = 0.0
    for k, sids, bids, P in flujos:
        for a, j in enumerate(sids):
            for b, i in enumerate(bids):
                e = float(P[a, b])
                ancho = float(techo[i, k]) - float(piso[j, k])
                if e > 0.0 and ancho >= 0.0:      # solo lo que se firma
                    banda += ancho * e
    d2 = abs(r["excedente"] - banda)
    ok2 = d2 <= 1e-6 * max(1.0, abs(banda))
    print(f"  2 · el excedente es el ancho de la banda por la energía")
    print(f"      identidad {banda:16.6f} · medido {r['excedente']:16.6f} · "
          f"dif {d2:.3e}   {'ok' if ok2 else 'FALLA'}")
    if not ok2:
        fallos.append("la identidad de H-33 no se cumple en el contrato")

    # 3 · el precio pactado vive dentro de la banda, y la invertida no se firma
    dentro, invertidas, energia_rota = 0, 0, 0.0
    for k, sids, bids, P in flujos:
        for a, j in enumerate(sids):
            for b, i in enumerate(bids):
                e = float(P[a, b])
                if e <= 0.0:
                    continue
                te, pi_ = float(techo[i, k]), float(piso[j, k])
                if te < pi_:
                    invertidas += 1
                    energia_rota += e
                elif pi_ - 1e-9 <= 0.5 * (te + pi_) <= te + 1e-9:
                    dentro += 1
    ok3 = (invertidas > 0                       # el caso se ejercita de verdad
           and r["parejas_sin_firmar"] == invertidas
           and abs(float(np.sum(r["sin_firmar"])) - energia_rota) <= 1e-9
           and dentro > 0)
    print(f"  3 · el precio cae dentro de la banda en {dentro} parejas, y las "
          f"{invertidas} invertidas no se firman")
    print(f"      el contrato declara {r['parejas_sin_firmar']} sin firmar con "
          f"{float(np.sum(r['sin_firmar'])):.4f} kWh   {'ok' if ok3 else 'FALLA'}")
    if not ok3:
        fallos.append("la guarda de la banda invertida no se comporta")

    # 4 · el excedente no depende del precio, solo el reparto
    def _sesgado(f: float) -> dict:
        """El mismo contrato pactado a la fraccion f de la banda."""
        ing = np.zeros(N)
        aho = np.zeros(N)
        for k, sids, bids, P in flujos:
            for a, j in enumerate(sids):
                for b, i in enumerate(bids):
                    e = float(P[a, b])
                    if e <= 0.0:
                        continue
                    te, pi_ = float(techo[i, k]), float(piso[j, k])
                    if te < pi_:
                        continue
                    pr = pi_ + f * (te - pi_)
                    ing[j] += (pr - pi_) * e
                    aho[i] += (te - pr) * e
        t = float(np.sum(ing) + np.sum(aho))
        return dict(total=t, cuota_vendedor=float(np.sum(ing)) / t)

    a3, a23 = _sesgado(1.0 / 3.0), _sesgado(2.0 / 3.0)
    d4 = max(abs(a3["total"] - r["excedente"]), abs(a23["total"] - r["excedente"]))
    movio = abs(a3["cuota_vendedor"] - a23["cuota_vendedor"])
    ok4 = d4 <= 1e-6 * max(1.0, r["excedente"]) and movio > 0.2
    print(f"  4 · el excedente no depende del precio   dif {d4:.3e}; "
          f"la cuota del vendedor sí se mueve {movio*100:.1f} pp   "
          f"{'ok' if ok4 else 'FALLA'}")
    if not ok4:
        fallos.append("el excedente del contrato depende del precio pactado")

    # 5 · no se inventa energia
    asignada = sum(float(np.sum(np.maximum(P, 0.0))) for _, _, _, P in flujos)
    rota = float(np.sum(r["sin_firmar"]))
    d5 = abs(r["kwh"] + rota - asignada)
    ok5 = d5 <= 1e-9 * max(1.0, asignada)
    print(f"  5 · nada se pierde ni se inventa   {r['kwh']:,.4f} firmados + "
          f"{rota:,.4f} sin firmar = {asignada:,.4f} asignados   "
          f"{'ok' if ok5 else 'FALLA'}")
    if not ok5:
        fallos.append("la energía liquidada más la no firmada no es la asignada")

    print()
    if fallos:
        for x in fallos:
            print(f"  FALLA: {x}")
        return 1
    print("  CAL-52 EN VERDE. El contrato interno reparte la banda a la mitad,")
    print("  cumple la identidad de H-33 al decimal, y su excedente no depende")
    print("  del precio pactado. Es el patrón contra el que se mide si el")
    print("  mecanismo dinámico reparte mejor o peor que una regla fija.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
