"""Escoge las horas de cada regimen sobre las que se valida el reposo.

QUE HACE. Lee el almacen de un caso de la matriz por reposo, agrupa sus horas
por regimen, muestrea unas cuantas de cada uno con una semilla fija y escribe
un JSON con la fecha de cada una. Las mediciones M-A, M-C y M-E leen ese JSON,
de modo que la muestra queda escrita y se puede repetir.

    python -u reformateo/documento/scripts/sonda/consenso/selecciona_horas.py \\
        --almacen SALIDAS_SERVIDOR/matriz_reposo/E0/almacen --caso E0 \\
        --por-regimen 10 --maximo 40 \\
        --salida SALIDAS_SERVIDOR/validacion_reposo/horas_E0.json

LOS GRUPOS. Ademas de los regimenes del nucleo (`core.reposo_mercado.REGIMENES`),
arma tres grupos que las mediciones piden por su nombre y que no son un regimen:

    dos_vendedores                 dos o mas vendedores y compradores largos
    compradores_cortos_con_cesmag  compradores cortos con Cesmag vendiendo (M-B)
    compradores_cortos_sin_cesmag  compradores cortos sin Cesmag vendiendo (M-A)

LA COMPROBACION, que es media razon de que esto exista. De cada hora escogida
vuelve a resolver el reposo con las entradas del arnes y lo compara con lo que
el almacen guardo: mismo regimen y mismo piso del juego. Si no coincide, la
hora NO entra en la muestra y queda anotada en los avisos: significa que el
arnes y la corrida no estan viendo la misma hora, y medir sobre ella no diria
nada. Si un grupo se queda sin horas, sale con codigo 1.

EL UMBRAL DE DESCARTE (medio 6 de la revision de 4c). Unas pocas horas
descartadas son ruido; muchas son un sintoma: el arnes y la corrida no cargan
la misma serie (otro MTE_ROOT, otro factor, otra version del cargador). Si en
un grupo se descarta MAS DEL 30 % de las horas examinadas, sale con codigo 1 y
dice por que, con los motivos contados. El JSON guarda por grupo cuantas se
examinaron y cuantas se descartaron.

SOLO ESCRIBE SU JSON.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import numpy as np                                   # noqa: E402
import arnes as A                                    # noqa: E402
import preparacion as PR                             # noqa: E402
from core.almacen import lee                         # noqa: E402
from core.reposo_mercado import REGIMENES            # noqa: E402

SIN_MERCADO = ("sin_mercado", "sin_ganancia")
TOL_PISO = 1e-3          # (COP/kWh); el almacen guarda en precision sencilla
DESCARTE_MAXIMO = 0.30   # fraccion de horas examinadas que puede descartarse
GRUPOS_EXTRA = ("dos_vendedores", "compradores_cortos_con_cesmag",
                "compradores_cortos_sin_cesmag")


def examina_grupo(g, muestra, maximo, comprueba) -> dict:
    """Recorre la muestra de un grupo hasta juntar `maximo` horas buenas.

    `comprueba(h)` devuelve (hora buena o None, motivo, texto). Cuenta las
    examinadas y las descartadas por motivo, y marca `excesivo` si se descarto
    mas de DESCARTE_MAXIMO de las examinadas (medio 6).
    """
    buenas, motivos, avisos = [], {}, []
    examinadas = 0
    for h in muestra:
        if len(buenas) >= maximo:
            break
        examinadas += 1
        buena, motivo, texto = comprueba(h)
        if buena is None:
            motivos[motivo] = motivos.get(motivo, 0) + 1
            avisos.append(f"{g}: {texto}")
            continue
        buenas.append(buena)
    descartadas = examinadas - len(buenas)
    return dict(buenas=buenas, examinadas=examinadas, descartadas=descartadas,
                motivos=motivos, avisos=avisos,
                excesivo=bool(examinadas
                              and descartadas / examinadas > DESCARTE_MAXIMO))


def vendedores_por_hora(agentes) -> dict:
    """{hora: [nombres de los vendedores]}, del almacen."""
    v = agentes[agentes["papel"] == "vendedor"]
    fuera = {}
    for h, nombre in zip(v["hora"].to_numpy(), v["agente"].to_numpy()):
        fuera.setdefault(int(h), []).append(str(nombre))
    return fuera


def compradores_por_hora(agentes) -> dict:
    c = agentes[agentes["papel"] == "comprador"]
    fuera = {}
    for h, nombre in zip(c["hora"].to_numpy(), c["agente"].to_numpy()):
        fuera.setdefault(int(h), []).append(str(nombre))
    return fuera


def agrupa(horas, vend, comp) -> dict:
    """{grupo: [hora]} con los regimenes del nucleo y los tres grupos extra."""
    grupos = {}
    for fila in horas.itertuples():
        if not bool(getattr(fila, "resuelta", False)):
            continue
        reg = str(getattr(fila, "regimen", "") or "")
        if not reg or reg in SIN_MERCADO:
            continue
        h = int(fila.hora)
        grupos.setdefault(reg, []).append(h)
        vs = vend.get(h, [])
        if reg == "compradores_cortos":
            clave = ("compradores_cortos_con_cesmag"
                     if any("esmag" in x for x in vs)
                     else "compradores_cortos_sin_cesmag")
            grupos.setdefault(clave, []).append(h)
        elif len(vs) >= 2:
            grupos.setdefault("dos_vendedores", []).append(h)
    return grupos


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--almacen", required=True)
    ap.add_argument("--caso", required=True,
                    help="el caso tal como lo carga el arnes: E0, E4, E5 o K1")
    ap.add_argument("--cobertura", default="m1")
    ap.add_argument("--por-regimen", type=int, default=10,
                    help="cuantas horas pide como minimo la medicion que mas "
                         "pide de este caso; la muestra se toma al menos asi "
                         "de ancha")
    ap.add_argument("--maximo", type=int, default=40,
                    help="cuantas horas comprobadas se guardan por grupo, "
                         "como mucho")
    ap.add_argument("--grupos", default="",
                    help="lista separada por comas; vacio = todos")
    ap.add_argument("--semilla", type=int, default=1)
    ap.add_argument("--salida", required=True)
    args = ap.parse_args(argv)

    alm = Path(args.almacen)
    horas = lee(alm, args.cobertura, "horas")
    agentes = lee(alm, args.cobertura, "agentes")
    vend = vendedores_por_hora(agentes)
    comp = compradores_por_hora(agentes)
    grupos = agrupa(horas, vend, comp)
    pedidos = ([g.strip() for g in args.grupos.split(",") if g.strip()]
               or [g for g in list(REGIMENES) + list(GRUPOS_EXTRA)
                   if g in grupos])
    print(f"  almacen {alm} - caso {args.caso} - {len(horas)} horas", flush=True)
    for g in sorted(grupos):
        print(f"    {g:<32s} {len(grupos[g]):6d} horas", flush=True)

    dat, _mapa = A.carga(args.caso)
    idx = list(dat["idx"])
    avisos = []
    if grupos and max(max(v) for v in grupos.values()) >= len(idx):
        avisos.append(f"el almacen llega a la hora "
                      f"{max(max(v) for v in grupos.values())} y el arnes solo "
                      f"carga {len(idx)}: no son la misma serie")

    piso_alm = {int(h): float(p) for h, p in
                zip(horas["hora"].to_numpy(), horas["piso_juego"].to_numpy())}
    reg_alm = {int(h): str(r or "") for h, r in
               zip(horas["hora"].to_numpy(), horas["regimen"].to_numpy())}

    rng = np.random.default_rng(args.semilla)
    por_regimen = {}
    examen = {}
    vacios = []
    excesivos = []
    for g in pedidos:
        candidatas = sorted(set(grupos.get(g, [])))
        if not candidatas:
            vacios.append(g)
            continue
        # Se muestrea lo mas ancho de los dos topes, porque comprobar descarta
        # horas y el grupo no puede quedarse corto por eso.
        ancho = min(len(candidatas), max(args.por_regimen, args.maximo))
        muestra = sorted(rng.choice(np.array(candidatas), size=ancho,
                                    replace=False).tolist())
        def comprueba(h, g=g):
            """(hora buena o None, motivo del descarte, texto del aviso)."""
            if h >= len(idx):
                return (None, "fuera de la serie del arnes",
                        f"la hora {h} no esta en la serie del arnes")
            fecha = A.clave(idx[h])
            try:
                e = A.hora_de(args.caso, fecha)
                r = PR.resuelve(e)
            except Exception as exc:                        # noqa: BLE001
                return (None, f"el arnes no la resuelve ({type(exc).__name__})",
                        f"la hora {h} ({fecha}) no se pudo resolver con el "
                        f"arnes: {type(exc).__name__}: {exc}")
            mismo = (r.regimen == reg_alm.get(h, ""))
            dif_piso = abs(float(r.piso) - piso_alm.get(h, float("nan")))
            if not mismo or not (dif_piso <= TOL_PISO):
                return (None,
                        "otro regimen" if not mismo else "otro piso del juego",
                        f"la hora {h} ({fecha}) no coincide con el almacen: "
                        f"regimen {r.regimen} frente a {reg_alm.get(h, '')}, "
                        f"piso {float(r.piso):.4f} frente a "
                        f"{piso_alm.get(h, float('nan')):.4f}")
            return (dict(hora=h, fecha=fecha, regimen=r.regimen, grupo=g,
                         E=float(r.E), piso=float(r.piso), S=float(r.S),
                         n_soluciones=int(r.n_soluciones),
                         vendedores=vend.get(h, []),
                         compradores=comp.get(h, []),
                         J=len(e["gn"]), I=len(e["dn"])), "", "")

        x = examina_grupo(g, muestra, args.maximo, comprueba)
        avisos.extend(x["avisos"])
        buenas = x["buenas"]
        if not buenas:
            vacios.append(g)
        por_regimen[g] = buenas
        examen[g] = dict(examinadas=x["examinadas"],
                         descartadas=x["descartadas"], motivos=x["motivos"])
        if x["excesivo"]:
            excesivos.append((g, x["examinadas"], x["descartadas"],
                              x["motivos"]))
        print(f"    {g:<32s} -> {len(buenas)} comprobadas de "
              f"{x['examinadas']} examinadas ({x['descartadas']} descartadas)",
              flush=True)

    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(dict(
        caso=args.caso, almacen=str(alm), cobertura=args.cobertura,
        semilla=args.semilla, por_regimen_pedido=args.por_regimen,
        maximo=args.maximo, generado=datetime.now().isoformat(timespec="seconds"),
        por_regimen=por_regimen, examen=examen, avisos=avisos), indent=1),
        encoding="utf-8")
    print(f"  escrito {salida}", flush=True)
    for a in avisos:
        print(f"  AVISO: {a}", flush=True)
    codigo = 0
    if excesivos:
        print(f"  === DEMASIADAS HORAS DESCARTADAS (mas del "
              f"{100 * DESCARTE_MAXIMO:.0f} % de las examinadas) ===", flush=True)
        for g, ex, de, mot in excesivos:
            detalle = "; ".join(f"{m}: {c}" for m, c in sorted(mot.items()))
            print(f"    {g}: {de} de {ex} ({100 * de / ex:.0f} %) - {detalle}",
                  flush=True)
        print("  El arnes y la corrida no parecen ver la misma serie (MTE_ROOT, "
              "el factor del caso o la version del cargador). La muestra queda "
              "escrita, pero medir sobre ella no diria nada hasta aclararlo.",
              flush=True)
        codigo = 1
    if vacios:
        print(f"  SIN HORAS: {', '.join(vacios)}", flush=True)
        codigo = 1
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
