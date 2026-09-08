"""
Sonda del tramo de permuta sobre el excedente residual (H-53).

LA PREGUNTA. El tramo de la Resolucion CREG 174 manda al vendedor a bolsa en
cuanto su inyeccion acumulada del mes supera su retiro acumulado. Nuestro
codigo lo evalua sobre el excedente BRUTO, como si todo cruzara la frontera.
Pero la energia que un vendedor coloca DENTRO de la comunidad no se la
entrego al comercializador, de modo que no deberia agotar su permuta. La
Resolucion CREG 101 072 lo dice para el colectivo: sus articulos 21 a 23
cuentan los dos tramos sobre los excedentes ASIGNABLES a cada usuario tras
el reparto.

POR QUE NO HACE FALTA UN PUNTO FIJO, que era la sospecha. Por D-7 el volumen
transado en una hora es el lado corto, el minimo entre oferta y demanda
netas, y no depende del precio. De modo que cuanto coloca la comunidad
dentro se sabe SIN jugar la partida: se reparte el lado corto entre los
vendedores en proporcion a su excedente. Queda un lazo de segundo orden, el
de la restriccion de participacion, que vale del orden del 0,5 % del volumen.

LAS TRES LECTURAS, y no son dos:

  bruto     todo el excedente cuenta como inyectado. Es lo que hay hoy.
  residual  solo cuenta lo que de verdad cruzo el medidor. Es lo que la
            norma liquida.
  amenaza   la posicion acumulada es la residual, es decir la real, y con
            ella se pregunta que le pagarian por el kWh de esta hora si no
            lo vendiera dentro. Es el punto de amenaza correcto del juego, y
            coincide con la contabilidad de la norma salvo en la hora en
            curso. Es lo que esta sonda estima.

LO QUE SALE, y desmiente la suposicion de que la lectura residual siempre
favorece a la comunidad: en la frontera principal ningun vendedor llega a
pisar la bolsa, y el ancho de la banda cae un 80 %; en la secundaria el
cruce llega ANTES, no despues, porque alli el mercado interno agota el
deficit mucho antes que el excedente y el retiro de la red tambien encoge.

Y hay que leerlo con H-47 en la mano: un ancho de banda menor NO es una
comunidad peor. Es una alternativa externa mejor, es decir menos que
arreglar.

Uso:
    python reformateo/documento/scripts/sonda/tramo_residual.py
"""
from __future__ import annotations

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[3]
for _p in (RAIZ, AQUI, AQUI.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402


def tramo_sobre(iny: np.ndarray, ret: np.ndarray,
                etiqueta_mes: np.ndarray) -> np.ndarray:
    """El tramo de la CREG 174 sobre las series que se le den.

    Igual que `core.opciones_externas.tramo_permuta`, pero recibe inyeccion
    y retiro en vez de deducirlos de la generacion y la demanda. Asi la
    misma mecanica sirve para el excedente bruto y para el residual.
    """
    N, T = iny.shape
    en = np.ones((N, T), dtype=bool)
    for mes in np.unique(etiqueta_mes):
        sel = etiqueta_mes == mes
        idx = np.flatnonzero(sel)
        for n in range(N):
            cruza = np.cumsum(iny[n, sel]) > np.cumsum(ret[n, sel])
            if cruza.any():
                en[n, idx[int(np.argmax(cruza)):]] = False
    return en


def residual(G: np.ndarray, D: np.ndarray):
    """Inyeccion y retiro que quedan tras colocar el lado corto dentro.

    El reparto entre vendedores es PROPORCIONAL a su excedente. Es una
    aproximacion del reparto verdadero, que solo existe despues de jugar la
    partida; el agregado, en cambio, es exacto por D-7.
    """
    exc = np.maximum(G - D, 0.0)
    dfc = np.maximum(D - G, 0.0)
    oferta, demanda = exc.sum(axis=0), dfc.sum(axis=0)
    corto = np.minimum(oferta, demanda)
    with np.errstate(invalid="ignore", divide="ignore"):
        fv = np.where(oferta > 1e-9, corto / oferta, 0.0)
        fc = np.where(demanda > 1e-9, corto / demanda, 0.0)
    return exc * (1.0 - fv)[None, :], dfc * (1.0 - fc)[None, :], exc


SALIDA = AQUI.parents[1] / "validacion_horaria"


def main() -> int:
    from paso_a_paso import carga
    from core.opciones_externas import piso_por_vendedor

    filas = []
    for cob in ("m1", "m3"):
        d = carga(cob)
        G, D = d["G"], d["D"]
        mes = pd.Series(pd.DatetimeIndex(d["idx"])
                        ).dt.strftime("%Y-%m").to_numpy()
        iny_r, ret_r, exc = residual(G, D)
        bruto = tramo_sobre(exc, np.maximum(D - G, 0.0), mes)
        resid = tramo_sobre(iny_r, ret_r, mes)
        vende = exc > 1e-9
        pb = piso_por_vendedor(d["techo"], d["cvm"], d["bolsa"], bruto)
        pr = piso_por_vendedor(d["techo"], d["cvm"], d["bolsa"], resid)
        e = exc[vende]
        nv = int(vende.sum())

        print(f"\n  frontera {cob.upper()} · {nv} horas-vendedor", flush=True)
        print("  " + "-" * 62, flush=True)
        cam = int((vende & (bruto != resid)).sum())
        for nom, t, p in (("bruto", bruto, pb), ("residual", resid, pr)):
            n_b = int((vende & ~t).sum())
            piso = float(np.average(p[vende], weights=e))
            ancho = float(np.average(d["techo"][vende] - p[vende], weights=e))
            print(f"  {nom:>9s}  en bolsa {n_b:6d} ({100*n_b/nv:5.1f} %) · "
                  f"piso {piso:7.1f} · ancho {ancho:7.1f} (COP/kWh)",
                  flush=True)
            filas.append(dict(
                cobertura=cob, lectura=nom, horas_vendedor=nv,
                en_bolsa=n_b, pct_en_bolsa=round(100 * n_b / nv, 4),
                piso_medio_ponderado=round(piso, 4),
                ancho_medio_ponderado=round(ancho, 4),
                cambian_de_tramo=cam,
                pct_cambian=round(100 * cam / nv, 4),
                invertidas=int(((d["techo"][vende] - p[vende]) <= 0).sum())))
        print(f"  {'':>9s}  cambian de tramo {cam:6d} ({100*cam/nv:5.1f} %)",
              flush=True)

    SALIDA.mkdir(parents=True, exist_ok=True)
    csv = SALIDA / "tramo_residual.csv"
    pd.DataFrame(filas).to_csv(csv, index=False, encoding="utf-8")
    nota = (
        "Generado por reformateo/documento/scripts/sonda/tramo_residual.py",
        "Horizonte completo de las dos coberturas. El reparto de lo colocado",
        "dentro es proporcional al excedente; el agregado por hora es exacto",
        "por D-7, el lado corto. Ver H-53.",
    )
    (SALIDA / "tramo_residual.fuente.txt").write_text(
        chr(10).join(nota) + chr(10), encoding="utf-8")
    print(chr(10) + f"  csv: {csv}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
