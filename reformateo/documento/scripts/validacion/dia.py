"""
El panorama de un dia y la eleccion de las horas testigo.

Recorre las 24 horas con el lector unico y produce dos cosas: la tabla del
dia, con una fila por hora, y la seleccion de tres o cuatro horas testigo
para desarrollar a fondo.

POR QUE HORAS TESTIGO Y NO LAS 24. Un dia son 24 horas por cinco agentes,
con papel, limites, flujos por pareja, precios, convergencia y reparto.
Ensenarlo entero serian dos docenas de laminas que nadie lee. El modelo base
resuelve esto igual: elige dos horas, una de excedente y otra de deficit, y
las explica a fondo.

EL CRITERIO SE DECLARA, y las categorias que no se dan ese dia SE DICEN, en
vez de sustituirlas por otra hora. Asi es como se cuelan los ejemplos
escogidos a conveniencia.

    central      la de mayor volumen transado
    deficit      la de mayor racionamiento, con demanda neta sobre la oferta
    excedente    la de mayor sobrante, con oferta neta sobre la demanda
    patologica   la que deja mas vendedores por debajo de su piso (H-43)

Ninguna hora ocupa dos categorias: se asignan en ese orden y la que se toma
sale del reparto.

AVISO: se resuelve por la via ACOPLADA, que no es el metodo con el que se
produjeron las cifras publicadas.

Uso:
    python dia.py --dia 2025-05-02 --cobertura m1
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

from validacion import hora as H  # noqa: E402

CATEGORIAS = ("central", "deficit", "excedente", "patologica")


def _ruta_cache(cobertura: str, fecha: str) -> Path:
    d = AQUI.parent.parent / "validacion_horaria" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"horas_{cobertura}_{fecha}.pkl"


def recorre(cobertura: str, fecha: str, dat=None, presupuesto_s: float = 180.0,
            rehacer: bool = False):
    """Las 24 horas de `fecha`, leidas una a una.

    Resolver un dia por la via acoplada cuesta minutos, y los tres modulos
    que lo consumen —panorama, factura y figuras— lo necesitan igual. Por eso
    el resultado se guarda: se calcula UNA vez por dia y frontera. Con
    `rehacer=True` se ignora lo guardado.

    `presupuesto_s` no interrumpe el integrador —no hay forma limpia de
    hacerlo desde aqui— pero se usa para avisar de las horas caras, que la
    via acoplada las tiene.
    """
    import pickle
    from paso_a_paso import carga

    cache = _ruta_cache(cobertura, fecha)
    if cache.exists() and not rehacer:
        with open(cache, "rb") as fh:
            guardado = pickle.load(fh)
        print(f"  [caché] {cache.name}, {len(guardado['horas'])} horas")
        return guardado["tabla"], guardado["horas"]

    if dat is None:
        dat = carga(cobertura)

    idx = pd.DatetimeIndex(dat["idx"])
    dia = pd.Timestamp(fecha).date()
    ks = [int(i) for i in np.flatnonzero(idx.date == dia)]
    if not ks:
        raise SystemExit(f"la fecha {fecha} no está en el horizonte")

    horas, filas = {}, []
    for k in ks:
        h = H.lee(dat, k, cobertura=cobertura)
        horas[k] = h
        filas.append(dict(
            k=k, hora=idx[k].strftime("%H:%M"),
            resuelta=h.resuelta, motivo=h.motivo,
            J=h.J, I=h.I,
            oferta=float(h.G_net.sum()) if h.G_net is not None else 0.0,
            demanda=float(h.D_net.sum()) if h.D_net is not None else 0.0,
            volumen=h.volumen,
            precio=float(np.mean(h.pi)) if h.pi is not None and len(h.pi) else np.nan,
            excedente=h.excedente, mejor=h.mejor, peor=h.peor, ciego=h.ciego,
            eficiencia=h.eficiencia, tajada_vendedor=h.tajada_vendedor,
            pegados=h.pegados, n_precios=h.n_precios,
            bajo_piso=len(h.bajo_piso), retirados=len(h.retirados),
            uniforme=h.uniforme, segundos=h.segundos))

    tabla = pd.DataFrame(filas)
    with open(cache, "wb") as fh:
        pickle.dump(dict(tabla=tabla, horas=horas), fh)
    return tabla, horas


def testigos(tabla: pd.DataFrame, horas: dict) -> dict:
    """Las horas testigo, por criterio declarado y sin repetir."""
    libres = set(int(k) for k in tabla[tabla.resuelta].k)
    fuera = {}

    def toma(nombre, candidatas, clave):
        cand = [k for k in candidatas if k in libres]
        fuera[nombre] = max(cand, key=clave) if cand else None
        if fuera[nombre] is not None:
            libres.discard(fuera[nombre])

    toma("central", list(libres), lambda k: horas[k].volumen)
    toma("deficit",
         [k for k in libres
          if float(horas[k].D_net.sum()) > float(horas[k].G_net.sum())],
         lambda k: float(horas[k].D_net.sum() - horas[k].G_net.sum()))
    toma("excedente",
         [k for k in libres
          if float(horas[k].G_net.sum()) > float(horas[k].D_net.sum())],
         lambda k: float(horas[k].G_net.sum() - horas[k].D_net.sum()))
    # La señal de la hora patológica es RETIRADOS, no `bajo_piso`. El paso a
    # paso ya aplica la restricción de participación, de modo que después de
    # aplicarla no queda por construcción ningún vendedor bajo su piso: usar
    # `bajo_piso` como criterio no puede disparar nunca. Lo que sí queda
    # registrado es a quién hubo que retirar para conseguirlo (H-43).
    toma("patologica",
         [k for k in libres if horas[k].retirados or horas[k].bajo_piso],
         lambda k: len(horas[k].retirados) + len(horas[k].bajo_piso))
    return fuera


def _n(x, dec=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def informa(tabla, horas, elegidas, cobertura, fecha) -> None:
    print(f"\nEl día {fecha} en la frontera {cobertura.upper()}")
    print("  resuelto por la vía acoplada, que NO es el método de las "
          "cifras publicadas")
    print("=" * 92)
    print(f"  {'hora':>5s} {'J':>2s} {'I':>2s} {'oferta':>8s} {'demanda':>8s} "
          f"{'volumen':>8s} {'precio':>8s} {'excedente':>10s} {'vend %':>7s} "
          f"{'pegados':>8s} {'s':>6s}")
    for _, r in tabla.iterrows():
        if not r.resuelta:
            print(f"  {r.hora:>5s}  ·  ·  {r.motivo}")
            continue
        print(f"  {r.hora:>5s} {int(r.J):2d} {int(r.I):2d} {_n(r.oferta):>8s} "
              f"{_n(r.demanda):>8s} {_n(r.volumen):>8s} {_n(r.precio,1):>8s} "
              f"{_n(r.excedente,0):>10s} {_n(r.tajada_vendedor,1):>7s} "
              f"{int(r.pegados):3d}/{int(r.n_precios):<4d} {_n(r.segundos,1):>6s}")

    act = tabla[tabla.resuelta]
    print("\n  " + "-" * 88)
    print(f"  {len(act)} horas con mercado de {len(tabla)} · "
          f"volumen {_n(act.volumen.sum())} kWh · "
          f"excedente {_n(act.excedente.sum(), 0)} COP")
    caras = act[act.segundos > 120]
    if len(caras):
        print(f"  {len(caras)} horas costaron más de dos minutos; la peor "
              f"{_n(act.segundos.max(), 0)} s")

    print("\n  Horas testigo, por criterio declarado")
    for nombre in CATEGORIAS:
        k = elegidas.get(nombre)
        if k is None:
            print(f"    {nombre:>11s}: NO SE DA ese día")
            continue
        h = horas[k]
        print(f"    {nombre:>11s}: hora {h.ts.strftime('%H:%M')} (k={k}) · "
              f"{h.J} vendedores, {h.I} compradores · "
              f"{_n(h.volumen)} kWh · {_n(h.excedente, 0)} COP"
              + (f" · {len(h.bajo_piso)} bajo su piso" if h.bajo_piso else ""))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dia", default="2025-05-02")
    ap.add_argument("--cobertura", default="m1", choices=["m1", "m3"])
    ap.add_argument("--presupuesto", type=float, default=180.0)
    ap.add_argument("--rehacer", action="store_true",
                    help="ignora lo guardado y vuelve a resolver el día")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tabla, horas = recorre(args.cobertura, args.dia,
                           presupuesto_s=args.presupuesto,
                           rehacer=args.rehacer)
    elegidas = testigos(tabla, horas)
    informa(tabla, horas, elegidas, args.cobertura, args.dia)

    sal = AQUI.parent.parent / "validacion_horaria"
    sal.mkdir(parents=True, exist_ok=True)
    destino = sal / f"tabla_{args.cobertura}_{args.dia}.csv"
    tabla.to_csv(destino, index=False, encoding="utf-8-sig")
    print(f"\n  tabla en {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
