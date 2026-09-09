"""
Cuales de los parametros heredados mueven el resultado, RESOLVIENDO (H-62).

LA PREGUNTA. `PARAMETROS.md` afirma que de los parametros libres del modelo
base ninguno gobierna el resultado: que la preferencia y la saciedad no entran
en la dinamica, que la competencia es inerte, y que solo el costo lineal manda.
Esa afirmacion se apoyaba en leer las firmas de las rutinas y en barridos
antiguos. **Leer una firma no es una prueba.**

Aqui se comprueba resolviendo: para cada parametro se vuelve a jugar la partida
con valores muy distintos y se mide cuanto se mueven el precio, el reparto, el
volumen y el bienestar.

QUE SE MIDE, y las cuatro columnas dicen cosas distintas:

  precio     el vector de equilibrio. Es lo primero que se movería.
  volumen    la energia transada. Por D-7 es el lado corto y deberia ser
             insensible a casi todo.
  reparto    la matriz completa, par por par. Puede moverse aunque el volumen
             no lo haga, que es la indeterminacion ya documentada.
  bienestar  el CUASILINEAL, es decir el excedente: ahorro del comprador
             contra su techo mas prima del vendedor contra su piso. Es el bien
             planteado segun H-61, y el que la tesis reporta.

COMO SE LEE. Una diferencia relativa por debajo de la tolerancia del
integrador, 1e-6, es ruido numerico y significa **sin efecto**. Una diferencia
grande significa que el parametro manda y hay que justificarlo.

Uso:
    python reformateo/documento/scripts/sonda/parametros_efecto.py
    python reformateo/documento/scripts/sonda/parametros_efecto.py --horas 6
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[3]
for _p in (RAIZ, AQUI):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

SALIDA = AQUI.parents[1] / "validacion_horaria"
NL = chr(10)

# Los barridos. Deliberadamente amplios: si un parametro importa, con estos
# rangos tiene que notarse.
BARRIDOS = {
    "lam":   (100.0, [1.0, 10000.0]),
    "theta": (0.5, [0.01, 2500.0]),
    "etha":  (0.1, [0.0, 50.0]),
    "c":     (0.0, [1.0, 1000.0]),
    "a":     (0.0, [0.01, 10.0]),
    "b":     (None, [0.5, 2.0]),   # multiplicadores del costo medido
}


def _metricas(r, dat, k):
    """Precio, volumen, reparto y el bienestar CUASILINEAL de una hora."""
    from core.settlement import bienestar_cuasilineal, compute_savings
    P = np.asarray(r["P"], float)
    pi = np.asarray(r["pi"], float)
    S_i, SR_j = compute_savings(P, pi, r["techo_i"], r["piso_j"])
    return dict(pi=pi, P=P, vol=float(P.sum()),
                W=bienestar_cuasilineal(S_i, SR_j))


def _dif(base, otro):
    """Diferencias relativas, con el maximo del vector como referencia."""
    def rel(x, y):
        x, y = np.atleast_1d(x), np.atleast_1d(y)
        if x.shape != y.shape:
            return float("inf")          # cambio el numero de participantes
        d = float(np.max(np.abs(x - y)))
        e = max(float(np.max(np.abs(x))), 1e-12)
        return d / e
    return dict(
        d_pi=rel(base["pi"], otro["pi"]),
        d_P=rel(base["P"], otro["P"]),
        d_vol=abs(otro["vol"] - base["vol"]) / max(base["vol"], 1e-12),
        d_W=abs(otro["W"] - base["W"]) / max(abs(base["W"]), 1e-12),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horas", type=int, default=4)
    ap.add_argument("--cobertura", default="m1")
    ap.add_argument("--semilla", type=int, default=7)
    args = ap.parse_args()

    from paso_a_paso import carga, resuelve

    dat = carga(args.cobertura)
    exc = np.maximum(dat["G"] - dat["D"], 0.0)
    dfc = np.maximum(dat["D"] - dat["G"], 0.0)
    act = [k for k in range(dat["D"].shape[1])
           if (exc[:, k] > 1e-9).sum() >= 2 and (dfc[:, k] > 1e-9).sum() >= 3]
    rng = np.random.default_rng(args.semilla)
    horas = [int(k) for k in rng.choice(act, size=min(args.horas, len(act)),
                                        replace=False)]
    print(f"  {args.cobertura.upper()} · horas {horas}", flush=True)

    # Reanudacion: lo ya medido no se repite. Con medio minuto por partida,
    # repetir es caro y no aporta nada.
    hecho = set()
    filas = []
    prev = SALIDA / "parametros_efecto.csv"
    if prev.exists():
        d0 = pd.read_csv(prev)
        filas = d0.to_dict("records")
        hecho = {(r["hora"], r["parametro"], str(r["valor"])) for r in filas}
        print(f"  reanudando: {len(hecho)} combinaciones ya medidas",
              flush=True)

    for k in horas:
        r0 = resuelve(dat, k)
        if r0 is None:
            continue
        base = _metricas(r0, dat, k)
        print(NL + f"  hora {k}   volumen {base['vol']:.4f} kWh · "
              f"bienestar {base['W']:.1f} (COP)", flush=True)
        print(f"  {'parametro':>10s} {'valor':>10s} {'d precio':>11s} "
              f"{'d reparto':>11s} {'d volumen':>11s} {'d bienestar':>12s} "
              f"{'veredicto':>12s}", flush=True)
        for nom, (defecto, valores) in BARRIDOS.items():
            for v in valores:
                if nom == "b":
                    # el costo lineal se mide por institucion: se escala
                    from data.xm_prices import get_b_for_real_data
                    b0 = get_b_for_real_data(len(dat["nombres"]),
                                             dat["nombres"])
                    pv = {"b": float(np.mean(b0) * v)}
                    etiqueta = f"x{v:g}"
                else:
                    pv = {nom: v}
                    etiqueta = f"{v:g}"
                if (k, nom, etiqueta) in hecho:
                    continue
                try:
                    r1 = resuelve(dat, k, params=pv)
                except Exception as e:            # noqa: BLE001
                    print(f"  {nom:>10s} {etiqueta:>10s}   falla: {e}",
                          flush=True)
                    continue
                if r1 is None:
                    print(f"  {nom:>10s} {etiqueta:>10s}   la hora deja de "
                          f"tener mercado", flush=True)
                    filas.append(dict(cobertura=args.cobertura, hora=k,
                                      parametro=nom, valor=etiqueta,
                                      sin_mercado=True))
                    continue
                d = _dif(base, _metricas(r1, dat, k))
                mueve = max(d["d_pi"], d["d_P"], d["d_vol"], d["d_W"])
                ver = "sin efecto" if mueve < 1e-6 else (
                    "marginal" if mueve < 1e-3 else "MUEVE")
                print(f"  {nom:>10s} {etiqueta:>10s} {d['d_pi']:11.2e} "
                      f"{d['d_P']:11.2e} {d['d_vol']:11.2e} "
                      f"{d['d_W']:12.2e} {ver:>12s}", flush=True)
                filas.append(dict(cobertura=args.cobertura, hora=k,
                                  parametro=nom, valor=etiqueta,
                                  sin_mercado=False, **d, veredicto=ver))
                # ESCRITURA INCREMENTAL. Cada resolucion cuesta medio minuto y
                # el proceso puede morir por plazo: lo hecho no se pierde. Es
                # la misma leccion que `recoge.py`.
                SALIDA.mkdir(parents=True, exist_ok=True)
                pd.DataFrame(filas).to_csv(SALIDA / "parametros_efecto.csv",
                                           index=False, encoding="utf-8")

    d = pd.DataFrame(filas)
    if not d.empty and "veredicto" in d.columns:
        print(NL + "  " + "=" * 62, flush=True)
        print("  VEREDICTO POR PARAMETRO, sobre todas las horas y valores",
              flush=True)
        print("  " + "=" * 62, flush=True)
        print(f"  {'parametro':>10s} {'casos':>6s} {'peor d precio':>14s} "
              f"{'peor d volumen':>15s} {'peor d bienestar':>17s} "
              f"{'veredicto':>12s}", flush=True)
        for nom in BARRIDOS:
            t = d[(d.parametro == nom) & (~d.sin_mercado.fillna(False))]
            if t.empty:
                continue
            peor = max(t.d_pi.max(), t.d_P.max(), t.d_vol.max(), t.d_W.max())
            ver = "sin efecto" if peor < 1e-6 else (
                "marginal" if peor < 1e-3 else "MUEVE")
            print(f"  {nom:>10s} {len(t):6d} {t.d_pi.max():14.2e} "
                  f"{t.d_vol.max():15.2e} {t.d_W.max():17.2e} {ver:>12s}",
                  flush=True)

    SALIDA.mkdir(parents=True, exist_ok=True)
    csv = SALIDA / "parametros_efecto.csv"
    d.to_csv(csv, index=False, encoding="utf-8")
    nota = (
        "Generado por reformateo/documento/scripts/sonda/parametros_efecto.py",
        "Vuelve a RESOLVER la hora con cada parametro sustituido y mide",
        "cuanto se mueven precio, reparto, volumen y el bienestar",
        "cuasilineal. Por debajo de 1e-6, la tolerancia del integrador, es",
        "ruido numerico. Ver H-62 y PARAMETROS.md.",
    )
    (SALIDA / "parametros_efecto.fuente.txt").write_text(
        NL.join(nota) + NL, encoding="utf-8")
    print(NL + f"  csv: {csv}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
