"""
retiro_miembro.py — Robustez ante cambios de composicion: el retiro de cada
institucion, caso por caso, en el punto base (B2, H-106, 2026-09-27).
==========================================================================
La justificacion de la propuesta pregunta «si los mecanismos dinamicos
ofrecen mayor robustez que los esquemas administrativos ante cambios en la
composicion de las comunidades», y el resultado esperado «Robustez ante
riesgo regulatorio» promete cuantificar el beneficio de flexibilidad del P2P
frente a C4 ante la entrada o salida de participantes. Hasta aqui solo
existia una corrida sin un miembro (SINU, sin Udenar).

Para cada caso de la matriz salvo CV2 (contraste determinista de E0) y SINU
(ya excluye a Udenar) -- once casos -- y para cada institucion del caso, el
guion evalua en el punto base del GSA (los seis factores en 1, mu = 1) la
comunidad SIN esa institucion y la comunidad completa como referencia, con
`evaluador.prepara_caso(caso, datos, excluir_agente=<nombre>)`: la exclusion
se SUMA a la opcion del caso, como si `main()` recibiera la opcion del caso
mas `--excluir-agente <nombre>` (C-176), de modo que el escalado, la
capacidad, el reparto igual de C4 (1/4), las tarifas y las cotas cuelgan de
la comunidad que queda.

Un par no se evalua, y se declara: I1 sin UCC. La opcion de I1 escala a UCC
a neto cero; sin UCC el caso no esta definido (`main()` se detiene, como el
evaluador) y lo que queda es E0 sin UCC, que ya esta medido.

Compuerta de coherencia (se detiene sin escribir si falla):
    - la comunidad completa de cada caso reproduce al peso el canon de ese
      caso (hoja `Resumen`, `Por_agente`, energia, parte del vendedor, horas
      cuantales, con las comprobaciones de `gsa_directo/compuerta_punto_base`);
    - E0 sin Udenar reproduce al peso el canon de SINU.
Ademas se comprueba en cada retirada que C4 sigue en el caso 2 del art. 20
con cuatro fronteras y el reparto igual del 25 %.

Escribe en SALIDAS_SERVIDOR/retiro_miembro_2026-09-27/:

    comunidad.csv        por (caso, retirada): los siete mecanismos de la
                         comunidad que queda, las cinco brechas con su signo
                         y si cambia respecto de la comunidad completa, el
                         caso del art. 20 de C4, el reparto, la capacidad por
                         usuario del art. 18, la energia transada, y la
                         perdida de las que quedan en P2P y en C4
    quienes_quedan.csv   por (caso, retirada, institucion que se queda): su
                         beneficio con y sin la retirada en P2P, P2P
                         colectivo, C1, C4 y C5, la perdida que le causa la
                         salida (completa - sin; negativa es una ganancia),
                         la diferencia perdida P2P - perdida C4 (`mas_afectado`,
                         con signo) y la de sus valores absolutos
                         (`mas_estable`: en que mecanismo se mueve menos el
                         beneficio de quien se queda)
    compuerta.csv        las comprobaciones de la compuerta de coherencia
    procedencia.txt      commit, fecha, orden, dato, resultado

No escribe en `outputs/` ni en `graficas/`. Con `--procesos N` reparte las
evaluaciones (unas 65, de 4 a 12 s cada una) en N procesos, que leen la
carga del MTE de `--cache`; en serie tarda unos 8 minutos, con 4 unos 2.

    python -u reformateo/documento/scripts/retiro_miembro.py --cache <carpeta> --procesos 4

Actividad 2.2 (robustez comparada de los mecanismos).
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from gsa_directo import comun  # noqa: E402

COMPLETA = "ninguna"
CASOS_RETIRO = tuple(c for c in comun.ORDEN_CASOS if c not in ("CV2", "SINU"))
MECANISMOS = ("P2P", "P2P_colectivo", "C1", "C2", "C3", "C4", "C5")
BRECHAS = {                      # nombre -> (minuendo, sustraendo)
    "P2P_menos_C1": ("P2P", "C1"),
    "P2P_menos_C4": ("P2P", "C4"),
    "P2P_menos_C5": ("P2P", "C5"),
    "P2Pcol_menos_C4": ("P2P_colectivo", "C4"),
    "C4_menos_C1": ("C4", "C1"),
}
# Los mecanismos cuyo beneficio por institucion se sigue en quienes_quedan.
MEC_INST = ("P2P", "P2P_colectivo", "C1", "C4", "C5")
TOL_PESO = 0.5
MATRIZ_CANON = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
                / "SALIDAS_SERVIDOR" / "matriz_reposo")
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "retiro_miembro_2026-09-27"


def signo(v: float) -> str:
    """'+', '-' o '0' (dentro de medio peso)."""
    if not np.isfinite(v):
        raise ValueError(f"valor no finito: {v!r}")
    return "0" if abs(v) <= TOL_PESO else ("+" if v > 0 else "-")


def no_aplica(caso: str, nombre: str):
    """El motivo por el que el par (caso, retirada) no se evalua, o None.
    Es el caso de una opcion que escala a la institucion retirada (I1 sin
    UCC): sin ella el caso no esta definido."""
    from data.escalado import lee_escala_agente
    op = comun.opciones_caso(caso)
    if nombre in lee_escala_agente(op["escala_agente"]):
        return (f"la opcion de {caso} ({comun.CASOS[caso]}) escala a "
                f"{nombre}; sin {nombre} el caso no esta definido y lo que "
                f"queda es E0 sin {nombre}")
    return None


_DATOS = None          # la carga del MTE de cada proceso (inicializador)


def _inicia(mte_root, cache):
    """Inicializador de cada proceso: el regimen no regulado y la carga del
    MTE (desde la cache que el proceso principal ya dejo escrita)."""
    global _DATOS
    from gsa_directo import evaluador
    evaluador.inicia_proceso()
    _DATOS = evaluador.carga_mte(mte_root, cache)


def trabajo(caso: str, excluir, matriz: str, registros: str) -> dict:
    """Una evaluacion del caso sin `excluir` (None: la comunidad completa),
    con lo que el guion necesita, y la compuerta cuando toca (la comunidad
    completa frente a su canon; E0 sin Udenar frente a SINU)."""
    from gsa_directo import evaluador
    from gsa_directo import compuerta_punto_base as cpb
    t1 = time.time()
    ins = evaluador.prepara_caso(caso, _DATOS, excluir_agente=excluir)
    esperados = [n for n in comun.nombres_caso(caso) if n != excluir]
    if ins.excluido != excluir or list(ins.nombres) != esperados:
        raise RuntimeError(f"{caso} sin {excluir}: los insumos traen "
                           f"{ins.nombres} (excluido {ins.excluido!r}); se "
                           f"esperaba {esperados}")
    out, cr = evaluador.evalua_comparacion(ins, comun.PUNTO_BASE)
    seg = time.time() - t1
    pa = {e: np.asarray(v, dtype=float).copy()
          for e, v in cr.net_benefit_per_agent.items()}
    net = {e: float(v) for e, v in cr.net_benefit.items()}
    filas = []
    canon_de = (caso if excluir is None else
                "SINU" if (caso, excluir) == ("E0", "Udenar") else None)
    if canon_de is not None:
        etiqueta = caso if excluir is None else "E0 sin Udenar frente a SINU"
        canon = cpb.lee_canon(Path(matriz) / canon_de, ins.nombres,
                              Path(registros), canon_de, canon_fijo=True)
        filas = cpb.compara(etiqueta, out, pa, net, canon, ins.nombres)
    return dict(caso=caso, excluir=excluir, nombres=list(ins.nombres),
                out=dict(out), pa=pa, net=net, art20=art20(ins, cr),
                seg=seg, compuerta=filas)


def art20(ins, cr) -> tuple:
    """(caso del art. 20, reparto maximo, capacidad por usuario del art. 18)
    del C4 que liquido `run_comparison`: el reparto igual (`cr.pde`) y la
    capacidad de los insumos, con la misma funcion que `run_c4_creg101072`
    usa con `caso="auto"`."""
    from scenarios.scenario_c4_creg101072 import (
        capacidad_por_usuario_art18, resolve_caso_art20)
    pde = np.asarray(cr.pde, dtype=float)
    N = len(ins.nombres)
    if pde.shape != (N,) or not np.allclose(pde, 1.0 / N, rtol=0, atol=1e-12):
        raise RuntimeError(f"{ins.caso}: el reparto de C4 no es el igual "
                           f"1/{N}: {pde.tolist()}")
    return (int(resolve_caso_art20(pde, ins.cap)), float(pde.max()),
            capacidad_por_usuario_art18(ins.cap, N))


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True,
                       text=True, check=True)
    return r.stdout.rstrip("\n")


def main(argv=None) -> int:
    comun.salida_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--matriz", default=str(MATRIZ_CANON))
    ap.add_argument("--salida", default=str(SALIDA))
    ap.add_argument("--casos", nargs="+", default=list(CASOS_RETIRO))
    ap.add_argument("--mte-root", default=None)
    ap.add_argument("--cache", default=None,
                    help="carpeta de cache de la carga del MTE (opcional; "
                         "obligatoria con --procesos > 1)")
    ap.add_argument("--procesos", type=int, default=1,
                    help="procesos en paralelo (uno por evaluacion; defecto "
                         "1, en serie)")
    args = ap.parse_args(argv)

    from gsa_directo import evaluador
    from gsa_directo import compuerta_punto_base as cpb

    malos = [c for c in args.casos if c not in CASOS_RETIRO]
    if malos:
        raise SystemExit(f"casos fuera de los once del retiro: {malos}")
    if args.procesos < 1:
        raise SystemExit(f"--procesos {args.procesos}: al menos 1")
    matriz = Path(args.matriz)
    registros = cpb._registros_de(matriz, None)
    if registros is None:
        raise SystemExit(f"no se hallan los registros D71 junto a {matriz}")
    ajenos = [c for c in dict.fromkeys(list(args.casos) + ["SINU"])
              if cpb.huella_libro(matriz / c) != cpb.HUELLAS_CANON[c]]
    if ajenos:
        raise SystemExit(f"la matriz no es la del canon 2026-09 en {ajenos}")
    mte_root = args.mte_root or comun.mte_root_defecto()
    if not Path(mte_root).is_dir():
        raise SystemExit(f"MTE_ROOT no es una carpeta: {mte_root}")
    if args.procesos > 1 and not args.cache:
        raise SystemExit("con --procesos > 1 hace falta --cache: cada "
                         "proceso lee la carga del MTE de alli")
    salida = Path(args.salida)

    print("=" * 72)
    print("RETIRO DE CADA INSTITUCION (robustez ante cambios de composicion), "
          "punto base")
    print("=" * 72)
    print(f"  matriz     {matriz}")
    print(f"  registros  {registros}")
    print(f"  MTE_ROOT   {mte_root}")
    print(f"  procesos   {args.procesos}")
    t0 = time.time()
    evaluador.carga_mte(mte_root, args.cache)      # deja la cache escrita
    print(f"  carga del MTE en {time.time() - t0:.1f} s")

    # Los trabajos: la comunidad completa y cada retirada que aplica.
    trabajos, omitidos = [], []
    for caso in args.casos:
        trabajos.append((caso, None))
        for excl in comun.nombres_caso(caso):
            motivo = no_aplica(caso, excl)
            if motivo:
                omitidos.append((caso, excl, motivo))
                print(f"  {caso:<5} sin {excl:<8} NO APLICA: {motivo}")
            else:
                trabajos.append((caso, excl))
    print(f"  {len(trabajos)} evaluaciones")
    res = {}
    if args.procesos == 1:
        _inicia(mte_root, args.cache)
        for caso, excl in trabajos:
            r = trabajo(caso, excl, str(matriz), str(registros))
            res[(caso, excl)] = r
            print(f"  {caso:<5} {'sin ' + excl if excl else 'completa':<12} "
                  f"{r['seg']:5.1f} s")
    else:
        # Todas las evaluaciones se someten de una vez: son pocas (menos de
        # setenta) y cada resultado es pequeno; la ventana acotada de
        # CAL-43e es para las 6 144 horas del motor, no para esto.
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=args.procesos,
                                 initializer=_inicia,
                                 initargs=(mte_root, args.cache)) as pool:
            fut = {pool.submit(trabajo, c, e, str(matriz), str(registros)):
                   (c, e) for c, e in trabajos}
            for f in fut:
                c, e = fut[f]
                r = f.result()          # una excepcion del trabajo sube aqui
                res[(c, e)] = r
                print(f"  {c:<5} {'sin ' + e if e else 'completa':<12} "
                      f"{r['seg']:5.1f} s  ({time.time() - t0:6.1f} s)")

    com, quedan, comp = [], [], []
    for caso in args.casos:
        r0 = res[(caso, None)]
        comp.extend(r0["compuerta"])
        out0 = r0["out"]
        pa0 = {m: r0["pa"][m] for m in MEC_INST}
        idx0 = {n: i for i, n in enumerate(r0["nombres"])}
        base = {b: signo(float(out0[a]) - float(out0[c]))
                for b, (a, c) in BRECHAS.items()}
        base_inst = {n: signo(pa0["P2P"][i] - pa0["C4"][i])
                     for n, i in idx0.items()}
        print(f"\n  {caso:<5} completa  P2P {out0['P2P'] / 1e6:9.3f}  C4 "
              f"{out0['C4'] / 1e6:9.3f} MCOP  canon al peso: "
              f"{all(f[6] for f in r0['compuerta'])}")

        for excl in [None] + list(r0["nombres"]):
            if (caso, excl) not in res:
                continue                 # no aplica (declarado arriba)
            r = res[(caso, excl)]
            out, nombres, seg = r["out"], r["nombres"], r["seg"]
            if excl is not None and r["compuerta"]:
                comp.extend(r["compuerta"])
                print(f"        {caso} sin {excl} frente al canon: "
                      f"al peso: {all(f[6] for f in r['compuerta'])}")
            caso20, pde_max, cap_u = r["art20"]
            N = len(nombres)
            if excl is not None and (N != 4 or caso20 != 2
                                     or abs(pde_max - 0.25) > 1e-12):
                raise RuntimeError(f"{caso} sin {excl}: C4 en el caso "
                                   f"{caso20} con reparto {pde_max} y {N} "
                                   f"fronteras; se esperaba el caso 2, 25 %")
            energia = float(out["energia"])
            fila = dict(caso=caso, retirada=excl or COMPLETA,
                        n_instituciones=N)
            fila.update({m: float(out[m]) for m in MECANISMOS})
            for b, (a, c) in BRECHAS.items():
                v = float(out[a]) - float(out[c])
                s = signo(v)
                fila[b] = v
                fila[f"signo_{b}"] = s
                fila[f"cambia_{b}"] = bool(s != base[b])
            pa = {m: r["pa"][m] for m in MEC_INST}
            perd = {m: 0.0 for m in MEC_INST}
            for i, n in enumerate(nombres):
                i0 = idx0[n]
                fi = dict(caso=caso, retirada=excl or COMPLETA,
                          institucion=n)
                for m in MEC_INST:
                    con, sin = float(pa0[m][i0]), float(pa[m][i])
                    fi[f"{m}_completa"] = con
                    fi[f"{m}_sin"] = sin
                    fi[f"perdida_{m}"] = con - sin
                    fi[f"perdida_rel_{m}"] = ((con - sin) / abs(con)
                                              if abs(con) > TOL_PESO
                                              else float("nan"))
                    perd[m] += con - sin
                d = fi["perdida_P2P"] - fi["perdida_C4"]
                fi["perdida_P2P_menos_perdida_C4"] = d
                # Quien pierde mas con la salida (con signo: una perdida
                # negativa es una ganancia) y quien se mueve menos (en valor
                # absoluto: la estabilidad del beneficio de quien se queda).
                fi["mas_afectado"] = {"+": "P2P", "-": "C4",
                                      "0": "igual"}[signo(d)]
                a = abs(fi["perdida_P2P"]) - abs(fi["perdida_C4"])
                fi["abs_perdida_P2P_menos_abs_perdida_C4"] = a
                fi["mas_estable"] = {"+": "C4", "-": "P2P",
                                     "0": "igual"}[signo(a)]
                v = float(pa["P2P"][i] - pa["C4"][i])
                fi["P2P_menos_C4_sin"] = v
                fi["signo_P2P_menos_C4_sin"] = signo(v)
                fi["cambia_P2P_menos_C4"] = bool(signo(v) != base_inst[n])
                if excl is not None:
                    quedan.append(fi)
            fila.update({f"perdida_quedan_{m}": perd[m] for m in MEC_INST})
            fila["perdida_quedan_P2P_menos_C4"] = perd["P2P"] - perd["C4"]
            fila.update(
                caso_art20_C4=caso20, reparto_C4=pde_max,
                cap_por_usuario_art18_kW=cap_u, energia_kWh=energia,
                parte_vendedor_almacen=float(out["parte_vendedor"]),
                horas_cuantales=int(out["n_cuantal"]),
                horas_mercado=int(out["n_horas_mercado"]),
                seg=round(seg, 2))
            no_finitos = [k for k, v in fila.items()
                          if isinstance(v, float) and not np.isfinite(v)]
            if no_finitos:
                raise ValueError(f"{caso} sin {excl}: no finitos en "
                                 f"{no_finitos}")
            com.append(fila)
            if excl is not None:
                print(f"  {caso:<5} sin {excl:<8} P2P "
                      f"{out['P2P'] / 1e6:9.3f}  C4 {out['C4'] / 1e6:9.3f}  "
                      f"C1 {out['C1'] / 1e6:9.3f} MCOP  perdida de las que "
                      f"quedan P2P {perd['P2P'] / 1e6:7.3f}  C4 "
                      f"{perd['C4'] / 1e6:7.3f}  caso {caso20}  E "
                      f"{energia:9.1f} kWh")

    dc = pd.DataFrame(comp, columns=["caso", "comprobacion", "canon",
                                     "evaluado", "dif", "tol", "ok"])
    malas = dc[~dc["ok"]]
    if len(malas):
        for _, f in malas.iterrows():
            print(f"  COMPUERTA {f['caso']} DIFIERE {f['comprobacion']}: "
                  f"canon {f['canon']:,.6f}  evaluado {f['evaluado']:,.6f}")
        print("RETIRO DE MIEMBRO: la compuerta de coherencia NO reproduce el "
              "canon; se detiene sin escribir")
        return 1
    if not any(f[0] == "E0 sin Udenar frente a SINU" for f in comp) \
            and "E0" in args.casos:
        raise RuntimeError("no se comprobo E0 sin Udenar frente a SINU")

    dm = pd.DataFrame(com)
    dq = pd.DataFrame(quedan)
    num = dm.select_dtypes(include=[np.number])
    if not np.all(np.isfinite(num.to_numpy(dtype=float))):
        raise ValueError("comunidad: hay valores no finitos")
    num = dq.drop(columns=[c for c in dq.columns
                           if c.startswith("perdida_rel_")]) \
            .select_dtypes(include=[np.number])
    if not np.all(np.isfinite(num.to_numpy(dtype=float))):
        raise ValueError("quienes_quedan: hay valores no finitos")

    salida.mkdir(parents=True, exist_ok=True)
    dm.to_csv(salida / "comunidad.csv", index=False, float_format="%.6f")
    dq.to_csv(salida / "quienes_quedan.csv", index=False, float_format="%.6f")
    dc.to_csv(salida / "compuerta.csv", index=False, float_format="%.6f")

    ret = dm[dm["retirada"] != COMPLETA]
    cambian = int(ret[[f"cambia_{b}" for b in BRECHAS]].to_numpy().sum())
    n_p2p = int((dq["mas_afectado"] == "P2P").sum())
    n_c4 = int((dq["mas_afectado"] == "C4").sum())
    n_ig = int((dq["mas_afectado"] == "igual").sum())
    e_p2p = int((dq["mas_estable"] == "P2P").sum())
    e_c4 = int((dq["mas_estable"] == "C4").sum())
    e_ig = int((dq["mas_estable"] == "igual").sum())
    c1_max = float(dq["perdida_C1"].abs().max())
    # Control duro (revision B2-D): C1 es individual, de modo que la salida de
    # otra institucion no puede mover el beneficio de quien se queda.
    if c1_max > 1e-6:
        raise SystemExit(f"control fallido: la salida de un miembro mueve C1 "
                         f"de quien se queda en {c1_max:.6g} COP")
    orden = " ".join([Path(sys.executable).name, "-u",
                      "reformateo/documento/scripts/retiro_miembro.py"]
                     + (argv if argv is not None else sys.argv[1:]))
    sucio = git("status", "--short", "--", "scenarios", "analysis", "core",
                "gsa_directo", "data", "main_simulation.py")
    with open(salida / "procedencia.txt", "w", encoding="utf-8") as fh:
        fh.write("B2 / H-106: robustez ante el retiro de cada institucion "
                 "(punto base del GSA)\n")
        fh.write(f"fecha: {dt.datetime.now().isoformat(timespec='seconds')}\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("arbol de trabajo (codigo) con cambios sin commit:\n"
                 + (sucio or "(ninguno)") + "\n")
        fh.write(f"orden: {orden}\n")
        fh.write(f"MTE_ROOT: {mte_root}\n")
        fh.write(f"huella del dato: {comun.huella_datos(mte_root)}\n")
        fh.write(f"canon de comparacion: {matriz}\n")
        fh.write("punto: seis factores en 1, mu = 1 (evaluador del GSA "
                 "directo, prepara_caso(excluir_agente=...) y "
                 "evalua_comparacion)\n")
        fh.write(f"casos: {' '.join(args.casos)}\n")
        fh.write(f"retiradas evaluadas: {len(ret)}; no aplican: "
                 f"{len(omitidos)}\n")
        for c, n, m in omitidos:
            fh.write(f"  no aplica {c} sin {n}: {m}\n")
        fh.write(f"compuerta de coherencia: {len(dc)} comprobaciones, todas "
                 f"al peso (comunidad completa de cada caso frente a su "
                 f"canon; E0 sin Udenar frente a SINU)\n")
        fh.write("caso del art. 20 de C4 en cada retirada: 2, con cuatro "
                 "fronteras y el reparto igual del 25 % (comprobado)\n")
        fh.write(f"brechas de comunidad con signo distinto del de la "
                 f"comunidad completa: {cambian}\n")
        fh.write(f"pares (retirada, institucion que queda): {len(dq)}; la "
                 f"salida le cuesta mas en P2P que en C4 en {n_p2p}, mas en "
                 f"C4 en {n_c4}, igual al peso en {n_ig}; su beneficio se "
                 f"mueve menos (valor absoluto) en P2P en {e_p2p}, en C4 en "
                 f"{e_c4}, igual en {e_ig}\n")
        fh.write(f"control: perdida maxima en C1 (individual) de quien se "
                 f"queda: {c1_max:.6f} COP\n")
    print(f"\n  escrito en {salida}")
    print(f"  compuerta de coherencia: {len(dc)} comprobaciones, todas al peso")
    print(f"  retiradas: {len(ret)} evaluadas, {len(omitidos)} no aplican; "
          f"signos de brecha que cambian: {cambian}")
    print(f"  quien se queda pierde mas en P2P: {n_p2p}; en C4: {n_c4}; "
          f"igual: {n_ig}; |perdida C1| max {c1_max:.3g} COP")
    print(f"  se mueve menos en P2P: {e_p2p}; en C4: {e_c4}; igual: {e_ig}")
    print(f"RETIRO DE MIEMBRO: comunidad completa al peso con el canon en "
          f"{len(args.casos)} casos"
          + (" y E0 sin Udenar al peso con SINU" if "E0" in args.casos
             else ""))
    return 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    sys.exit(main())
