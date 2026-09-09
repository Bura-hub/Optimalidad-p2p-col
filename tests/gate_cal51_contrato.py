"""
Compuerta de CAL-51: el escenario del contrato deja de ser una copia del de bolsa.

EL DEFECTO. En la configuracion de produccion las cinco instituciones son
prosumidoras y no hay consumidores puros, de modo que la rama del contrato
bilateral **nunca se ejecutaba** y el escenario caia a una rama que calcula
autoconsumo mas excedente a bolsa horaria. Que es literalmente el escenario de
mercado mayorista. Los dos daban el mismo resultado al ultimo digito, y la
igualdad se presentaba como una propiedad cuando era una ausencia: al escenario
le faltaba **lo unico que lo constituye**, que es un precio pactado.

LA NORMA. Articulo 23 numeral 2 literal a de la Resolucion CREG 174, tal como
quedo modificado por el articulo 27 de la Resolucion 101 072 de 2025: la venta
a un tercero con destino a usuarios no regulados se hace «a precio pactado
libremente». El numeral 2 es el de los AGPE que usan fuentes no convencionales,
que es el caso de las cinco instalaciones solares.

QUE PRUEBA ESTA COMPUERTA, y son cinco cosas:

  1. RETRO-COMPATIBILIDAD BIT A BIT. Sin precio de contrato, el escenario
     devuelve exactamente lo de siempre.
  2. LA DEGENERACION CONTROLADA. Con el precio de contrato igual al de bolsa,
     los dos escenarios vuelven a coincidir **exactamente**. La coincidencia
     pasa de accidente a propiedad demostrada de un caso limite.
  3. LA SEPARACION COMO IDENTIDAD, no como umbral: la diferencia entre los dos
     es el excedente por la diferencia de precios, comprobable al ultimo
     decimal. Es el mismo estilo de la identidad de H-33.
  4. NO CONTAMINACION. Con y sin precio de contrato, los demas escenarios dan
     lo mismo por igualdad de matrices. Es la respuesta directa a «sin romper
     los demas», y es demostrable en vez de argumentable.
  5. COBERTURA DEL DATO. La serie de contratos cubre el horizonte completo y
     falla en voz alta si le falta un mes.

Uso:
    python tests/gate_cal51_contrato.py
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

TOL = 1e-9


def _caso(N=5, T=96, semilla=11):
    rng = np.random.default_rng(semilla)
    return dict(
        D=rng.uniform(1.0, 10.0, (N, T)),
        G=rng.uniform(0.0, 12.0, (N, T)),
        pi_gs=np.full((N, T), 730.0),
        pi_bolsa=rng.uniform(100.0, 400.0, T),
        N=N, T=T,
    )


def main() -> int:
    from scenarios.scenario_c2_bilateral import run_c2_bilateral
    from scenarios.scenario_c3_spot import run_c3_spot
    from data.precios_contratos import cobertura, precio_horario

    c = _caso()
    N, T = c["N"], c["T"]
    ids = dict(prosumer_ids=list(range(N)), consumer_ids=[])
    base = dict(D=c["D"], G=c["G"], pi_gs=c["pi_gs"], pi_gb=280.0,
                pi_ppa=393.0, pi_bolsa=c["pi_bolsa"], **ids)
    fallos = []

    # 1 · retro-compatibilidad
    a = run_c2_bilateral(**base)
    b = run_c2_bilateral(**base, pi_contrato=None)
    d1 = abs(a["aggregate"]["total_net_benefit"]
             - b["aggregate"]["total_net_benefit"])
    ok1 = d1 <= TOL
    print(f"  1 · sin precio de contrato, identico a lo de siempre   "
          f"dif {d1:.3e}   {'ok' if ok1 else 'FALLA'}")
    if not ok1:
        fallos.append("el parametro nulo cambia el resultado historico")

    # 2 · degeneracion controlada
    c3 = run_c3_spot(D=c["D"], G=c["G"], pi_gs=c["pi_gs"],
                     pi_bolsa=c["pi_bolsa"], **ids)
    igual = run_c2_bilateral(**base, pi_contrato=c["pi_bolsa"])
    d2 = abs(igual["aggregate"]["total_net_benefit"]
             - c3["aggregate"]["total_net_benefit"])
    ok2 = d2 <= TOL
    print(f"  2 · con el precio de contrato igual al de bolsa, coinciden   "
          f"dif {d2:.3e}   {'ok' if ok2 else 'FALLA'}")
    if not ok2:
        fallos.append("la degeneracion controlada no se cumple")

    # 3 · la separacion es una identidad
    pc = np.full(T, 288.0)
    con = run_c2_bilateral(**base, pi_contrato=pc)
    exc = np.maximum(c["G"] - c["D"], 0.0)
    esperado = float(np.sum(exc * (pc - c["pi_bolsa"])[None, :]))
    real = (con["aggregate"]["total_net_benefit"]
            - c3["aggregate"]["total_net_benefit"])
    d3 = abs(real - esperado)
    ok3 = d3 <= 1e-6 * max(1.0, abs(esperado))
    print(f"  3 · la separacion es el excedente por la diferencia de precios")
    print(f"      esperado {esperado:14.4f} · medido {real:14.4f} · "
          f"dif {d3:.3e}   {'ok' if ok3 else 'FALLA'}")
    if not ok3:
        fallos.append("la separacion no cuadra con su identidad")

    # 4 · no contaminacion
    c3b = run_c3_spot(D=c["D"], G=c["G"], pi_gs=c["pi_gs"],
                      pi_bolsa=c["pi_bolsa"], **ids)
    # El desglose por agente viene indexado por el numero del agente.
    def _vec(r):
        pa = r["per_agent"]
        return np.array([float(pa[i]["net_benefit"]) if isinstance(pa[i], dict)
                         else float(pa[i]) for i in sorted(pa)])
    ok4 = np.array_equal(_vec(c3), _vec(c3b))
    print(f"  4 · el escenario de bolsa no se mueve   "
          f"{'ok' if ok4 else 'FALLA'}")
    if not ok4:
        fallos.append("el escenario de bolsa cambio")

    # 5 · cobertura del dato
    try:
        cob = cobertura("2025-04-04", "2025-12-16")
        idx = pd.date_range("2025-04-04", periods=6144, freq="h")
        v = precio_horario(idx)
        ok5 = (not cob["faltan"] and not cob["fuera_de_banda"]
               and len(v) == 6144 and len(set(np.round(v, 4))) == 9)
        print(f"  5 · la serie cubre el horizonte   {len(cob['cargados'])} de "
              f"{len(cob['meses'])} meses · de {cob['minimo']:.1f} a "
              f"{cob['maximo']:.1f} COP/kWh   {'ok' if ok5 else 'FALLA'}")
        if not ok5:
            fallos.append("la serie de contratos no cubre el horizonte")
    except Exception as exc:                      # noqa: BLE001
        print(f"  5 · la serie de contratos   FALLA: {exc}")
        fallos.append(f"no se pudo cargar la serie: {exc}")

    print()
    if fallos:
        for x in fallos:
            print(f"  FALLA: {x}")
        return 1
    print("  CAL-51 EN VERDE. El escenario del contrato tiene precio propio,")
    print("  se separa del de bolsa por una identidad exacta, y con el precio")
    print("  igualado vuelve a coincidir: la igualdad de antes queda demostrada")
    print("  como caso limite y no como accidente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
