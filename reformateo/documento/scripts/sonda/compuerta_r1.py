"""
compuerta_r1.py — compuerta de salida de las corridas de la revision r1 del
articulo (AE-5 y AE-4; acciones `matriz_esquina` y `matriz_corte` de
`modelo_base/run_servidor.sh`).

Actividad 3.3. No sustituye a `compuertas_matriz_reposo.py`, que no se toca:

- si el almacen tiene ALGUNA hora resuelta, delega en ella tal cual (misma
  orden, mismo codigo de salida, misma linea final);
- si NO tiene ninguna, aquella no puede comprobar nada y sale con 2. Es lo
  que pasa, por diseno, en la esquina «solo el 1» de E0, K1, CV2 y SINU
  (`diseno_mediciones_completas.md`, 1.3): con lo intercambiado pagando
  kappa·Cv + Theta y nadie agotando su credito, ningun par gana y nadie
  transa. Entonces esta compuerta comprueba lo que si tiene que valer, y
  distingue «no hubo mercado porque ningun par gana» de «la corrida no
  resolvio nada»:

  estado     toda hora es «sin mercado esa hora» (ninguna vencida por el plazo,
             con excepcion, sin exito del integrador ni «sin resolver»), sin
             retirados, y toda hora con vendedor y comprador trae el regimen
             `sin_ganancia` del reposo; las demas, ninguno;
  banda      en esas horas, recalculado del almacen, ningun par gana: la
             tarifa del comprador menos su cargo (`cargo_comprador.npy`, cero
             si no lo hay) no pasa del piso de ningun vendedor;
  energia    nada vendido ni comprado dentro y ningun flujo;
  valor      sin intercambio, el mercado de la esquina vale lo que C1 al peso
             (1 COP), en la comunidad y en cada institucion, en la hoja Resumen
             y en Por_agente del libro de la corrida (la regla de liquidacion
             del mercado P2P sobre flujos nulos es la de C1). El valor de las
             esquinas sin el supuesto 1 (el colectivo, columna P2P_colectivo)
             se informa, no se compara: sin intercambio es C4 con el PDE de la
             exportacion propia.

Linea final en verde: «COMPUERTA SIN MERCADO <caso> EN VERDE». Codigos: 0
verde, 1 alguna identidad falla, 2 no se puede comprobar (faltan tablas o el
libro). Uso, como la otra:
    python -u compuerta_r1.py <almacen> --cobertura m1 --caso E0
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
AQUI = Path(__file__).resolve().parent

MOTIVO_SIN_MERCADO = "sin mercado esa hora"
REGIMEN_SIN_GANANCIA = "sin_ganancia"
TOL_COP = 1.0          # «al peso», la tolerancia del canon para C1 (§14.21)
TOL_BANDA = 1e-6       # COP/kWh


def _compuerta_de_siempre():
    spec = importlib.util.spec_from_file_location(
        "compuertas_matriz_reposo", AQUI / "compuertas_matriz_reposo.py")
    mod = importlib.util.module_from_spec(spec)
    # las dataclasses del modulo necesitan encontrarse en sys.modules
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _texto(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip()


def sin_mercado(almacen: Path, cobertura: str, caso: str) -> int:
    from core.almacen import lee
    malas = []

    def exige(ok, msg):
        print(("  BIEN  " if ok else "  MAL   ") + msg)
        if not ok:
            malas.append(msg)

    try:
        h = lee(str(almacen), cobertura, "horas")
        a = lee(str(almacen), cobertura, "agentes")
    except FileNotFoundError as e:
        print(f"COMPUERTA SIN MERCADO {caso}: NO SE PUEDE COMPROBAR: {e}")
        return 2
    try:
        fl = lee(str(almacen), cobertura, "flujos")
    except FileNotFoundError:
        fl = pd.DataFrame()
    libro = almacen.parent / "outputs" / "resultados_comparacion.xlsx"
    if not libro.is_file():
        print(f"COMPUERTA SIN MERCADO {caso}: NO SE PUEDE COMPROBAR: no esta {libro}")
        return 2
    n = len(h)
    print("=" * 78)
    print(f"  COMPUERTA SIN MERCADO - caso {caso} ({n} horas, ninguna resuelta)")
    print("=" * 78)

    # estado: por que no hay mercado
    motivo = _texto(h["motivo"])
    otros = motivo[motivo != MOTIVO_SIN_MERCADO]
    exige(otros.empty,
          f"estado: las {n} horas son «{MOTIVO_SIN_MERCADO}»"
          + ("" if otros.empty else f"; {len(otros)} con otro motivo, p. ej. "
             f"«{otros.iloc[0]}» (hora {int(h.loc[otros.index[0], 'hora'])})"))
    papel = _texto(a["papel"])
    raros = papel[~papel.isin(["vendedor", "comprador", "inactivo"])]
    exige(raros.empty, "estado: ningun agente «sin resolver» ni «retirado»"
          + ("" if raros.empty else f"; hay {raros.value_counts().to_dict()}"))
    lados = (a.assign(v=papel.eq("vendedor"), c=papel.eq("comprador"))
             .groupby("hora")[["v", "c"]].any())
    ambos = lados.index[lados.v & lados.c]
    reg = _texto(h.set_index("hora")["regimen"]) if "regimen" in h else \
        pd.Series("", index=h.hora)
    con = reg.reindex(ambos)
    exige(len(ambos) > 0 and bool((con == REGIMEN_SIN_GANANCIA).all()),
          f"estado: las {len(ambos)} horas con vendedor y comprador traen el "
          f"regimen «{REGIMEN_SIN_GANANCIA}»"
          + ("" if (con == REGIMEN_SIN_GANANCIA).all() else
             f"; {int((con != REGIMEN_SIN_GANANCIA).sum())} no"))
    resto = reg.drop(index=ambos, errors="ignore")
    exige(bool((resto == "").all()),
          f"estado: las {len(resto)} horas sin los dos lados no traen regimen")

    # banda: recalculada del almacen
    ags = list(dict.fromkeys(a.agente))
    T = int(a.hora.max()) + 1
    techo = a.pivot(index="agente", columns="hora", values="techo").loc[ags].to_numpy(float)
    piso = a.pivot(index="agente", columns="hora", values="piso").loc[ags].to_numpy(float)
    vend = (a.pivot(index="agente", columns="hora", values="papel").loc[ags] == "vendedor").to_numpy()
    comp = (a.pivot(index="agente", columns="hora", values="papel").loc[ags] == "comprador").to_numpy()
    f_cargo = almacen / "cargo_comprador.npy"
    cargo = np.load(f_cargo) if f_cargo.is_file() else np.zeros_like(techo)
    exige(cargo.shape == techo.shape and np.isfinite(cargo).all(),
          f"banda: el cargo del comprador ({'cargo_comprador.npy' if f_cargo.is_file() else 'sin fichero: cero'}) "
          f"tiene forma {cargo.shape}")
    peor = -np.inf
    for k in ambos:
        k = int(k)
        mejor = (np.max((techo[:, k] - cargo[:, k])[comp[:, k]])
                 - np.min(piso[vend[:, k], k]))
        peor = max(peor, mejor)
    exige(peor <= TOL_BANDA,
          f"banda: en ninguna de esas horas gana ningun par; la mayor banda "
          f"(techo neto del comprador - piso del vendedor) es {peor:.4f} COP/kWh")

    # energia
    v = float(a["vende_p2p"].astype(float).abs().sum())
    q = float(a["compra_p2p"].astype(float).abs().sum())
    exige(v == 0.0 and q == 0.0 and len(fl) == 0,
          f"energia: vendido {v:.6f} kWh, comprado {q:.6f} kWh, {len(fl)} flujos")

    # valor: el mercado sin intercambio es C1 al peso
    res = pd.read_excel(libro, "Resumen").set_index("Escenario")["Ganancia_neta_COP"]
    pa = pd.read_excel(libro, "Por_agente")
    exige(np.isfinite(res.to_numpy(dtype=float)).all() and {"P2P", "C1"} <= set(res.index),
          "valor: la hoja Resumen tiene P2P y C1 finitos")
    d = abs(float(res["P2P"]) - float(res["C1"]))
    exige(d <= TOL_COP, f"valor: la comunidad vale C1 al peso: P2P {float(res['P2P']):,.2f}, "
          f"C1 {float(res['C1']):,.2f} COP (dif {d:.4f})")
    da = (pa["P2P"].astype(float) - pa["C1"].astype(float)).abs()
    exige(bool((da <= TOL_COP).all()),
          f"valor: cada institucion vale C1 al peso (mayor dif {float(da.max()):.4f} COP)")
    if "P2P_colectivo" in res.index:
        print(f"  INFO  sin intercambio, el colectivo con el PDE propio (P2P_colectivo) "
              f"vale {float(res['P2P_colectivo']):,.2f} COP y C4 {float(res.get('C4', np.nan)):,.2f}")

    if malas:
        print(f"COMPUERTA SIN MERCADO {caso} CON {len(malas)} FALLOS")
        return 1
    print(f"COMPUERTA SIN MERCADO {caso} EN VERDE")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("almacen")
    ap.add_argument("--cobertura", default="m1")
    ap.add_argument("--caso", default=None)
    args = ap.parse_args(argv)
    if (hasattr(sys.stdout, "reconfigure")
            and str(getattr(sys.stdout, "encoding", "")).lower() != "utf-8"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    alm = Path(args.almacen)
    caso = args.caso or (alm.parent.name if alm.name == "almacen" else alm.name)
    from core.almacen import lee
    try:
        h = lee(str(alm), args.cobertura, "horas")
    except FileNotFoundError as e:
        print(f"COMPUERTA SIN MERCADO {caso}: NO SE PUEDE COMPROBAR: {e}")
        return 2
    if bool(h["resuelta"].eq(True).any()):
        argv2 = [str(alm), "--cobertura", args.cobertura, "--caso", caso]
        return _compuerta_de_siempre().main(argv2)
    return sin_mercado(alm, args.cobertura, caso)


if __name__ == "__main__":
    sys.exit(main())
