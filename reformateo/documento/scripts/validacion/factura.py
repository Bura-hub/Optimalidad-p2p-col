"""
La factura comparada por institucion.

Es lo que se pidio en la reunion preparatoria del foro y lo que no existia:

    «¿no has hecho un ejercicio practico de resultado?… este usuario saldria
     liquidado asi con el modelo. Con lo regulatorio al usuario le estan
     cobrando 900 pesos, pero los excedentes se los estan pagando a 200.
     Mientras que en el optimo… me la estan cobrando no a 900, sino a 300.»

    «Asi sea que tuvieras los resultados PARA UNA ENTIDAD, ¿como hacer esa
     verificacion?»

COMO SE CALCULA, y por que asi.

Bajo la NORMATIVA BASE cada institucion compra a la red lo que le falta, al
costo unitario de su comercializador, que es su techo; y le pagan lo que le
sobra al piso que le corresponde esa hora, que es la permuta mientras su
excedente no supere su consumo del mes, y la bolsa despues.

Bajo el MODELO lo unico que cambia es el precio de la energia que si
encuentra pareja dentro de la comunidad: en vez de comprarla al techo la
compra al precio acordado, y en vez de venderla al piso la vende a ese mismo
precio. Lo que no encuentra pareja sigue liquidandose igual que antes.

De ahi que el beneficio de un comprador sea el techo menos el precio, por la
energia que compro dentro; y el de un vendedor, el precio menos su piso, por
la que coloco dentro. Que es exactamente lo que calcula la liquidacion del
nucleo, de modo que este modulo no reimplementa esa cuenta: la agrega.

EL INDICE DE GANANCIA se normaliza por el rango admisible de cada agente,
siguiendo la tesis de Medina, porque comparar en pesos a instituciones de
tamaños muy distintos no dice nada. Las dos cotas salen de la banda REAL de
cada hora.

Uso:
    python factura.py --dia 2025-05-02 --cobertura m1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[3]
SONDA = AQUI.parent / "sonda"
for _p in (RAIZ, SONDA, AQUI.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def calcula(dat: dict, horas: dict) -> pd.DataFrame:
    """La factura de cada institucion sobre las horas que se le pasen."""
    nombres = list(dat["nombres"])
    N = len(nombres)
    z = lambda: np.zeros(N)          # noqa: E731

    kwh_vende_p2p, kwh_compra_p2p = z(), z()
    kwh_vende_red, kwh_compra_red = z(), z()
    reg_cobro, reg_pago = z(), z()
    mod_cobro, mod_pago = z(), z()
    ben_vendedor, ben_comprador = z(), z()
    rango_min, rango_max = z(), z()

    for k, h in sorted(horas.items()):
        if not h.resuelta:
            continue
        techo = dat["techo"][:, k]
        piso = dat["piso"][:, k]

        # ── quien compra dentro de la comunidad ─────────────────────────
        for q, i in enumerate(h.bids):
            dentro = float(h.P[:, q].sum())
            fuera = float(h.compra_red[i])
            kwh_compra_p2p[i] += dentro
            kwh_compra_red[i] += fuera
            # con la normativa base compraria TODO al techo
            reg_cobro[i] += techo[i] * (dentro + fuera)
            # con el modelo, lo de dentro al precio acordado
            mod_cobro[i] += float(h.pi[q]) * dentro + techo[i] * fuera
            ben_comprador[i] += (techo[i] - float(h.pi[q])) * dentro
            # rango admisible: peor, comprarlo todo a la red, cero ahorro;
            # mejor, comprarlo todo al piso mas bajo de esa hora
            rango_max[i] += (techo[i] - h.piso_h) * dentro

        # ── quien vende dentro de la comunidad ──────────────────────────
        for m, j in enumerate(h.sids):
            dentro = float(h.P[m, :].sum())
            fuera = float(h.vende_red[j])
            kwh_vende_p2p[j] += dentro
            kwh_vende_red[j] += fuera
            # con la normativa base lo colocaria TODO a su piso
            reg_pago[j] += piso[j] * (dentro + fuera)
            precio_medio = (float(np.sum(h.pi * h.P[m, :])) / dentro
                            if dentro > 1e-12 else 0.0)
            mod_pago[j] += precio_medio * dentro + piso[j] * fuera
            ben_vendedor[j] += (precio_medio - piso[j]) * dentro
            # rango admisible: peor, exportarlo todo a su piso; mejor,
            # colocarlo al techo mas alto de esa hora
            rango_max[j] += (h.gs_esc - piso[j]) * dentro

        # ── los que la participacion retiro exportan todo ───────────────
        for j in h.retirados:
            fuera = float(h.vende_red[j])
            kwh_vende_red[j] += fuera
            reg_pago[j] += piso[j] * fuera
            mod_pago[j] += piso[j] * fuera

    reg_neto = reg_cobro - reg_pago          # lo que paga, neto
    mod_neto = mod_cobro - mod_pago
    beneficio = reg_neto - mod_neto          # lo que deja de pagar

    with np.errstate(divide="ignore", invalid="ignore"):
        indice = np.where(rango_max - rango_min > 1e-9,
                          (beneficio - rango_min) / (rango_max - rango_min),
                          np.nan)

    return pd.DataFrame(dict(
        institucion=nombres,
        kwh_vende_p2p=kwh_vende_p2p, kwh_compra_p2p=kwh_compra_p2p,
        kwh_vende_red=kwh_vende_red, kwh_compra_red=kwh_compra_red,
        reg_cobro=reg_cobro, reg_pago=reg_pago, reg_neto=reg_neto,
        mod_cobro=mod_cobro, mod_pago=mod_pago, mod_neto=mod_neto,
        beneficio=beneficio,
        beneficio_vendedor=ben_vendedor, beneficio_comprador=ben_comprador,
        rango_min=rango_min, rango_max=rango_max, indice=indice))


def _n(x, dec=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def informa(f: pd.DataFrame, cobertura: str, fecha: str) -> None:
    print(f"\nLa factura del día {fecha} · frontera {cobertura.upper()}")
    print("  qué le liquida la normativa base y qué le liquidaría el mercado")
    print("=" * 96)
    print(f"  {'institución':<11s} {'vende':>8s} {'compra':>8s} "
          f"{'paga reg.':>11s} {'paga modelo':>12s} {'beneficio':>11s} "
          f"{'vendedor':>10s} {'comprador':>10s} {'índice':>8s}")
    for _, r in f.iterrows():
        print(f"  {r.institucion:<11s} {_n(r.kwh_vende_p2p,2):>8s} "
              f"{_n(r.kwh_compra_p2p,2):>8s} {_n(r.reg_neto,0):>11s} "
              f"{_n(r.mod_neto,0):>12s} {_n(r.beneficio,0):>11s} "
              f"{_n(r.beneficio_vendedor,0):>10s} "
              f"{_n(r.beneficio_comprador,0):>10s} "
              f"{_n(100*r.indice,1):>7s} %")
    print("  " + "-" * 92)
    print(f"  {'comunidad':<11s} {_n(f.kwh_vende_p2p.sum(),2):>8s} "
          f"{_n(f.kwh_compra_p2p.sum(),2):>8s} {_n(f.reg_neto.sum(),0):>11s} "
          f"{_n(f.mod_neto.sum(),0):>12s} {_n(f.beneficio.sum(),0):>11s} "
          f"{_n(f.beneficio_vendedor.sum(),0):>10s} "
          f"{_n(f.beneficio_comprador.sum(),0):>10s}")

    gana_v = int((f.beneficio_vendedor > 1e-6).sum())
    gana_c = int((f.beneficio_comprador > 1e-6).sum())
    pierde = f[f.beneficio < -1e-6]
    print(f"\n  Se benefician como vendedoras {gana_v} y como compradoras "
          f"{gana_c}, de {len(f)}.")
    if len(pierde):
        print(f"  ATENCIÓN: {len(pierde)} salen PERDIENDO con el modelo: "
              f"{', '.join(pierde.institucion)}. Eso contradice lo que la")
        print("  reunión predice y hay que registrarlo como hallazgo, no "
              "maquillarlo.")
    else:
        print("  Ninguna sale perdiendo, que es lo que la reunión predecía.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dia", default="2025-05-02")
    ap.add_argument("--cobertura", default="m1", choices=["m1", "m3"])
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    from paso_a_paso import carga
    from validacion import dia as Dia
    dat = carga(args.cobertura)
    _, horas = Dia.recorre(args.cobertura, args.dia, dat=dat)
    f = calcula(dat, horas)
    informa(f, args.cobertura, args.dia)

    sal = AQUI.parent.parent / "validacion_horaria"
    sal.mkdir(parents=True, exist_ok=True)
    destino = sal / f"factura_{args.cobertura}_{args.dia}.csv"
    f.to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"\n  detalle en {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
