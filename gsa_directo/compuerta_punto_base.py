"""Compuerta del punto base del GSA directo (apartado 6.1 del diseno, D73).

Actividad 4.1.

Para cada uno de los trece casos evalua el modelo con los seis factores en 1
y lo compara con el canon (la matriz por reposo del 2026-09-19):

    beneficio de los ocho escenarios   hoja Resumen, Ganancia_neta_COP   al peso (*)
    beneficio por institucion          hoja Por_agente                   al peso (*)
    energia transada                   suma de kWh_transados del CSV     0,01 (kWh)
                                       de flujos, y la del almacen
    parte del vendedor                 almacen (prima contra el piso)    5e-4 (float32)
    horas cuantales                    almacen y registro de la          exactas
                                       compuerta de salida (D71)
    retiros de la via por reposo       0 (D67)                           exactos

(*) La tolerancia del beneficio es la menor entre 1e-6 relativa (la del
diseno) y medio peso: con 1e-6 sola, sobre 46 MCOP pasarian 46 (COP) de
diferencia, y el criterio es «al peso». Medido el 2026-09-26 en los trece
casos: 4,3e-16 relativa como maximo.

y el contraste determinista del apartado 5.3: E0 con f_cv = 2 y el resto en
1 frente al caso CV2 del canon.

Dos guardas de la ronda de arreglos de la tarea G:

- `--matriz` es OBLIGATORIA y, antes de evaluar, el libro de cada caso se
  compara con la huella del canon 2026-09 (M-8): una `matriz_reposo`
  reescrita despues no pasa por canon;
- una comprobacion sin dato de referencia (el registro D71 que no se halla,
  una columna de Por_agente) cuenta como diferencia, salvo
  `--permite-omitir`, que la deja pasar con aviso (M-7);
- (ronda 2, m-3) el registro D71 es el de la matriz canonica del 19 de
  septiembre, por nombre y huella (REGISTROS_CANON), no el ultimo por
  nombre; con `--sin-huella-canon`, el unico de esa fecha.

Imprime `COMPUERTA GSA PUNTO BASE EN VERDE` y sale con 0, o lista las
diferencias y sale con 1 (2 si el canon no se puede leer o no es el canon). Corre ANTES de la
corrida del servidor y la detiene si falla: es la prueba de que el evaluador
no derivo de `main()`.

    python -u gsa_directo/compuerta_punto_base.py --matriz SALIDAS_SERVIDOR/matriz_reposo
    python -u gsa_directo/compuerta_punto_base.py \
        --matriz SALIDAS_SERVIDOR/entrega_matriz_reposo_2026-09-19/SALIDAS_SERVIDOR/matriz_reposo \
        --sin-escribir --cache <carpeta temporal>
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from gsa_directo import comun  # noqa: E402

ESCENARIOS = ("P2P", "P2P_colectivo", "C1", "C2", "C3", "C4", "C4_mensual",
              "C5")
TOL_REL = 1e-6
TOL_PESO = 0.5
TOL_KWH = 0.01
TOL_PARTE = 5e-4
PATRON_CUANTAL = re.compile(r"Horas «cuantal» \(D71\):\s*(\d+)")
SIN_REFERENCIA = " (SIN REFERENCIA)"
# sha256 del libro `outputs/resultados_comparacion.xlsx` de cada caso de la
# matriz canonica del 2026-09-19, copiadas de
# `Documentos/canon_2026-09/HUELLAS.csv` (que no viaja al servidor: Documentos/
# esta fuera de git). La compuerta compara contra el CANON, no contra
# cualquier `matriz_reposo` que haya en disco: si esa carpeta se reescribio
# despues con otro codigo, el evaluador y la matriz nueva coincidirian entre
# si y la compuerta saldria en verde sin serlo (ronda de arreglos de la
# tarea G, M-8). `--sin-huella-canon` lo omite, y lo dice.
HUELLAS_CANON = {
    "E0": "08c47e920932ffa4474eb423da1440fb0e8bce9dfd57f76e044d1177b3bae528",
    "E1": "3aeffd80a2827bf923b1cfea6fc53faa6f14321b2aa7fde992b2e6644b930604",
    "E2": "4416f9987cddd2d8b688263a35ad567e4186a47ad82f34cc83d3b86445d80d22",
    "E3": "e167cf5c67b549cff77cbac4e1e7e43ddd94454fd00b9faf5cac65f8e282ffd6",
    "E4": "a7be204d0057e9a95ad6f1d13afa3500a713522ba7cca17e83d98d4fdcf291ab",
    "E5": "c2b5670b5a0ccfe496d82fd9a524b56022dcf322205e399c2d1381b38263a645",
    "P1": "6bfbad25dbbf846b0d1077d0582d6ee3b240220f06ff691825963c5a2578c63e",
    "P2": "8a21e0b675d512a211dc0b2b643d9a134b4f6663fe74cf5d2b9ca2e77af206dd",
    "K1": "8999c29e31d9e106ab52abbec76b06c4e857214d58192ec5aca716fe4556f306",
    "I1": "6a71443ce6ed4f7cd169c27025679c2e40dcece73034a4cb0883e30e766d9c0f",
    "N1": "878229170c1db74258ed48e9da1280bee5a42287dad8208aeb90d36dc2c8f7cc",
    "CV2": "4ebfd938c04a96f3924a00be07e6874db99f01bd3a2c08a74fbc42604b88c88c",
    "SINU": "ec868669801708cd3812629123bc4bdab037eded74eb74155b9a141cf63facca",
}


# El registro de la compuerta de salida de cada caso en la matriz canonica
# del 19 de septiembre: nombre y sha256, de `Documentos/canon_2026-09/
# HUELLAS.csv` (grupo «registro»). La compuerta toma ESE registro, no el
# ultimo por nombre: si despues se relanzo algo en el servidor, un registro
# posterior no es el del canon (ronda 2 de la tarea G, m-3). Un registro con
# el nombre del canon y otra huella se trata como ausente (SIN REFERENCIA).
FECHA_CANON = "2026-09-19"
REGISTROS_CANON = {
    "CV2": ("matriz_reposo_compuerta_CV2_2026-09-19_1733.log",
            "251fb7af3d66313dff39c3d74a997a67b36bba1374969801031fc4fc96e5b0cb"),
    "E0": ("matriz_reposo_compuerta_E0_2026-09-19_1721.log",
           "44c157f4660ef2a7711f00642c39037c7eb308ccb7d499f5f3bfe69d40a74c48"),
    "E1": ("matriz_reposo_compuerta_E1_2026-09-19_1722.log",
           "0290506fbf96b77a356332a8efaa9297eec23dba84acc1f57beb29ca12143016"),
    "E2": ("matriz_reposo_compuerta_E2_2026-09-19_1724.log",
           "bef44a1dcb088bc6e8352ed461cc355f4d196ae95b1f221775fee13dc6ae1686"),
    "E3": ("matriz_reposo_compuerta_E3_2026-09-19_1725.log",
           "24ccae795eaaa03a59bd452ef3ea00365dc511d6dfd24a535eb095ad6ab3f85f"),
    "E4": ("matriz_reposo_compuerta_E4_2026-09-19_1726.log",
           "a89ad0d86fb0c89bba68b25c4f9f2c5dfed4d2cee6e9f14639952efa1a7770e4"),
    "E5": ("matriz_reposo_compuerta_E5_2026-09-19_1727.log",
           "a8c3af138eea2a291012722832175abe39b22cb56bd11ccca3e432025b06bb4e"),
    "I1": ("matriz_reposo_compuerta_I1_2026-09-19_1731.log",
           "1df7c1e50ab0d4cec0213f99063a40860110de401eb0fbfe1f6a486d893cc319"),
    "K1": ("matriz_reposo_compuerta_K1_2026-09-19_1730.log",
           "871053f20de453a8e1a38e628601deb80859523f3fa61127e46cda1605e76285"),
    "N1": ("matriz_reposo_compuerta_N1_2026-09-19_1732.log",
           "46a33799fe0980cbfa95c64e2311a41935028eb5c3930e3569343c35fe44bf8f"),
    "P1": ("matriz_reposo_compuerta_P1_2026-09-19_1728.log",
           "f32955a77711c3712fab053ffc93d043df7231c7741cf6d53853c66c31334bb5"),
    "P2": ("matriz_reposo_compuerta_P2_2026-09-19_1729.log",
           "23d6b55e2c9ecdc88ebee2f2160ed7b0c5f7630dc54b7b7a637d97e37053c8e7"),
    "SINU": ("matriz_reposo_compuerta_SINU_2026-09-19_1734.log",
             "c27862431541c98fd83a6465dd27af5e816437eb250ef74289a661285cc3ce6e"),
}


def elige_registro(registros, caso: str, canon_fijo: bool = True):
    """(ruta, nota) del registro D71 del caso.

    Con `canon_fijo`, el del canon por nombre y huella (REGISTROS_CANON); si
    el caso no esta alli (canones sinteticos) o sin `canon_fijo`, el unico de
    la fecha del canon, y si hay varios de esa fecha, ninguno (ambiguo).
    Nunca «el ultimo por nombre»."""
    import hashlib
    if registros is None:
        return None, "sin carpeta de registros"
    carpeta = Path(registros)
    if canon_fijo and caso in REGISTROS_CANON:
        nombre, sha = REGISTROS_CANON[caso]
        ruta = carpeta / nombre
        if not ruta.exists():
            return None, f"no esta {nombre}"
        if hashlib.sha256(ruta.read_bytes()).hexdigest() != sha:
            return None, f"{nombre} no tiene la huella del canon"
        return ruta, ""
    hallados = sorted(carpeta.glob(
        f"matriz_reposo_compuerta_{caso}_{FECHA_CANON}_*.log"))
    if len(hallados) == 1:
        return hallados[0], ""
    if not hallados:
        return None, f"ningun registro de {caso} del {FECHA_CANON}"
    return None, (f"{len(hallados)} registros de {caso} del {FECHA_CANON}: "
                  f"ambiguo")


def huella_libro(dir_caso: Path) -> str:
    import hashlib
    libro = dir_caso / "outputs" / "resultados_comparacion.xlsx"
    return hashlib.sha256(libro.read_bytes()).hexdigest()


class CanonIlegible(Exception):
    pass


# ── Lectura del canon ───────────────────────────────────────────────────────
def lee_canon(dir_caso: Path, nombres: list, registros=None,
              caso: str = "", canon_fijo: bool = False) -> dict:
    """Las cifras canonicas de un caso."""
    from core.almacen import lee
    libro = dir_caso / "outputs" / "resultados_comparacion.xlsx"
    flujos_csv = dir_caso / "outputs" / "p2p_breakdown_flujos.csv"
    alm = dir_caso / "almacen"
    for p in (libro, flujos_csv, alm):
        if not p.exists():
            raise CanonIlegible(f"no esta {p}")
    res = pd.read_excel(libro, sheet_name="Resumen")
    resumen = {str(e): float(v) for e, v in
               zip(res["Escenario"], res["Ganancia_neta_COP"])}
    pa = pd.read_excel(libro, sheet_name="Por_agente")
    if len(pa) != len(nombres):
        raise CanonIlegible(f"Por_agente trae {len(pa)} filas y el caso tiene "
                            f"{len(nombres)} instituciones")
    # Un escenario que falte en Por_agente queda como None: `compara` lo
    # cuenta como comprobacion SIN REFERENCIA, no lo salta en silencio.
    por_agente = {e: (pa[e].to_numpy(dtype=float) if e in pa.columns
                      else None) for e in ESCENARIOS}
    energia_csv = float(pd.read_csv(flujos_csv)["kWh_transados"].sum())
    fl = lee(alm, "m1", "flujos")
    prima = float(fl["prima_vendedor"].astype(float).sum())
    ahorro = float(fl["ahorro_comprador"].astype(float).sum())
    hs = lee(alm, "m1", "horas")
    cuantal_alm = int((hs["regimen"].astype(str) == "cuantal").sum()) \
        if "regimen" in hs.columns else None
    cuantal_reg = None
    ruta_reg, nota_reg = elige_registro(registros, caso, canon_fijo)
    if ruta_reg is not None:
        m = PATRON_CUANTAL.search(ruta_reg.read_text(encoding="utf-8",
                                                     errors="replace"))
        if m:
            cuantal_reg = int(m.group(1))
        else:
            nota_reg = f"{ruta_reg.name} no trae la linea de horas cuantal"
    return dict(resumen=resumen, por_agente=por_agente,
                energia_csv=energia_csv,
                energia_alm=float(fl["kwh"].astype(float).sum()),
                parte=prima / (prima + ahorro) if prima + ahorro > 0
                else float("nan"),
                cuantal_alm=cuantal_alm, cuantal_reg=cuantal_reg,
                registro=str(ruta_reg) if ruta_reg else None,
                nota_registro=nota_reg)


# ── Comparacion ─────────────────────────────────────────────────────────────
def compara(etiqueta: str, out: dict, por_agente: dict, net: dict,
            canon: dict, nombres: list, permite_omitir: bool = False) -> list:
    """Lista de (etiqueta, que, canon, evaluado, diferencia, tolerancia, ok).

    Una comprobacion cuyo dato de referencia falta (el registro D71 que no
    se hallo, una columna de Por_agente, el regimen del almacen) NO se salta
    en silencio (ronda de arreglos de la tarea G, M-7): entra con el rotulo
    «(SIN REFERENCIA)» y cuenta como diferencia, salvo que se pida
    expresamente `permite_omitir`, y entonces pasa pero se avisa."""
    filas = []

    def anota(que, c, v, tol, relativa=False):
        if c is None:
            filas.append((etiqueta, que + SIN_REFERENCIA, float("nan"),
                          float(v), float("nan"), 0.0, bool(permite_omitir)))
            return
        dif = abs(float(v) - float(c))
        lim = (min(tol * max(abs(float(c)), 1.0), TOL_PESO) if relativa
               else tol)
        filas.append((etiqueta, que, float(c), float(v), dif, lim,
                      bool(np.isfinite(dif) and dif <= lim)))

    for e in ESCENARIOS:
        if e not in canon["resumen"]:
            filas.append((etiqueta, f"Resumen {e}", float("nan"),
                          net.get(e, float("nan")), float("nan"), 0.0, False))
            continue
        anota(f"Resumen {e}", canon["resumen"][e], net[e], TOL_REL, True)
    for e, col in canon["por_agente"].items():
        if col is None:
            anota(f"Por_agente {e}", None, float("nan"), 0.0)
            continue
        for n, nombre in enumerate(nombres):
            anota(f"Por_agente {e} {nombre}", col[n], por_agente[e][n],
                  TOL_REL, True)
    anota("energia (CSV de flujos)", canon["energia_csv"], out["energia"],
          TOL_KWH)
    anota("energia (almacen)", canon["energia_alm"], out["energia"], TOL_KWH)
    anota("parte del vendedor (almacen)", canon["parte"],
          out["parte_vendedor"], TOL_PARTE)
    anota("horas cuantales (almacen)", canon["cuantal_alm"], out["n_cuantal"],
          0.0)
    anota("horas cuantales (registro D71)", canon["cuantal_reg"],
          out["n_cuantal"], 0.0)
    anota("retiros (D67)", 0.0, out["retiros"], 0.0)
    return filas


def _registros_de(matriz: Path, dado):
    if dado:
        return Path(dado)
    for cand in (matriz.parent.parent / "modelo_base" / "logs",
                 comun.RAIZ / "modelo_base" / "logs"):
        if cand.is_dir() and any(cand.glob("matriz_reposo_compuerta_*.log")):
            return cand
    return None


def ejecuta(argv=None) -> int:
    comun.salida_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--matriz", required=True,
                    help="la matriz por reposo del canon, EXPLICITA (M-8): en "
                         "el servidor, la del 19 de septiembre; se comprueba "
                         "contra las huellas del canon")
    ap.add_argument("--sin-huella-canon", action="store_true",
                    help="no comprueba que los libros sean los del canon "
                         "(solo para canones sinteticos o nuevos)")
    ap.add_argument("--permite-omitir", action="store_true",
                    help="una comprobacion sin dato de referencia pasa con "
                         "aviso en vez de contar como diferencia (M-7)")
    ap.add_argument("--registros", default=None,
                    help="carpeta de los registros de las compuertas de "
                         "salida de la matriz (se busca sola)")
    ap.add_argument("--casos", nargs="+", default=list(comun.ORDEN_CASOS))
    ap.add_argument("--sin-contraste", action="store_true",
                    help="no evalua E0 con f_cv = 2 frente a CV2")
    ap.add_argument("--salida", default=str(comun.salidas_defecto() / "base"
                                            / "punto_base.csv"))
    ap.add_argument("--sin-escribir", action="store_true",
                    help="no escribe punto_base.csv (ni cache si no se da)")
    ap.add_argument("--mte-root", default=None)
    ap.add_argument("--cache", default=None)
    args = ap.parse_args(argv)

    from gsa_directo import evaluador

    matriz = Path(args.matriz)
    if not matriz.is_absolute():
        matriz = comun.RAIZ / matriz
    registros = _registros_de(matriz, args.registros)
    cache = (Path(args.cache) if args.cache else
             None if args.sin_escribir else comun.salidas_defecto() / "cache")
    malos = [c for c in args.casos if c not in comun.CASOS]
    if malos:
        print(f"  casos desconocidos: {malos}")
        return 2
    print("=" * 70)
    print("COMPUERTA GSA PUNTO BASE (apartado 6.1): el evaluador con los seis "
          "factores en 1 frente al canon")
    print("=" * 70)
    print(f"  matriz     {matriz}")
    print(f"  registros  {registros or 'NO HALLADOS: la comprobacion del registro D71 queda sin referencia y cuenta como diferencia (salvo --permite-omitir)'}")
    if args.sin_huella_canon:
        print("  huellas    NO se comprueban (--sin-huella-canon): la matriz "
              "podria no ser la del canon")
    else:
        ajenos = []
        for c in dict.fromkeys(list(args.casos) + (
                [] if args.sin_contraste or "E0" not in args.casos
                else ["CV2"])):
            try:
                h = huella_libro(matriz / c)
            except OSError as exc:
                print(f"\n  CANON ILEGIBLE en {c}: {exc}")
                return 2
            if h != HUELLAS_CANON.get(c):
                ajenos.append(c)
        if ajenos:
            print(f"\n  LA MATRIZ NO ES LA DEL CANON: el libro "
                  f"resultados_comparacion.xlsx de {' '.join(ajenos)} no tiene "
                  f"la huella del canon 2026-09 (Documentos/canon_2026-09/"
                  f"HUELLAS.csv). Apunta --matriz a la entrega del 19 de "
                  f"septiembre, o usa --sin-huella-canon si es a proposito.")
            return 2
        print("  huellas    los libros de los casos son los del canon 2026-09")
    print(f"  casos      {' '.join(args.casos)}")

    t0 = time.time()
    datos = evaluador.carga_mte(args.mte_root, cache)
    print(f"  carga del MTE en {time.time() - t0:.1f} s")

    todas, filas_salida, tiempos = [], [], {}
    trabajos = [(c, c, comun.PUNTO_BASE) for c in args.casos]
    if not args.sin_contraste and "E0" in args.casos:
        x = comun.PUNTO_BASE.copy()
        x[comun.NOMBRES.index("f_cv")] = 2.0
        trabajos.append(("E0 con f_cv = 2 frente a CV2", "CV2", x))
    ins_cache = {}
    for etiqueta, caso_canon, x in trabajos:
        caso_ins = etiqueta.split()[0]
        if caso_ins not in ins_cache:
            ins_cache[caso_ins] = evaluador.prepara_caso(caso_ins, datos)
        ins = ins_cache[caso_ins]
        try:
            canon = lee_canon(matriz / caso_canon, ins.nombres, registros,
                              caso_canon,
                              canon_fijo=not args.sin_huella_canon)
        except (CanonIlegible, FileNotFoundError, KeyError, ValueError) as exc:
            print(f"\n  CANON ILEGIBLE en {caso_canon}: {exc}")
            return 2
        t1 = time.time()
        try:
            out, pa, net = evaluador.evalua_detalle(ins, x)
        except ValueError as exc:
            print(f"\n  {etiqueta}: la evaluacion FALLA: {exc}")
            todas.append((etiqueta, "evaluacion", float("nan"), float("nan"),
                          float("nan"), 0.0, False))
            continue
        seg = time.time() - t1
        tiempos[etiqueta] = seg
        filas = compara(etiqueta, out, pa, net, canon, ins.nombres,
                        permite_omitir=args.permite_omitir)
        todas.extend(filas)
        malas = [f for f in filas if not f[6]]
        ben = [f for f in filas if f[1].startswith(("Resumen", "Por_agente"))
               and not f[1].endswith(SIN_REFERENCIA)]
        dmax = max((f[4] / max(abs(f[2]), 1.0) for f in ben), default=0.0)
        e = next(f for f in filas if f[1].startswith("energia (CSV"))
        p = next(f for f in filas if f[1].startswith("parte"))
        print(f"\n  {etiqueta:<30} {seg:5.2f} s  beneficio: dif. rel. max "
              f"{dmax:.1e}  energia {e[4]:.4f} kWh  parte {p[4]:.1e}  "
              f"cuantales {out['n_cuantal']:.0f}  retiros "
              f"{out['retiros']:.0f}  -> {'al peso' if not malas else 'DIFIERE'}")
        for f in malas:
            print(f"      DIFIERE {f[1]}: canon {f[2]:,.6f}  evaluado "
                  f"{f[3]:,.6f}  |dif| {f[4]:.3g} > {f[5]:.3g}")
        for f in filas:
            if f[6] and f[1].endswith(SIN_REFERENCIA):
                print(f"      AVISO {f[1]}: omitida por --permite-omitir")
        if canon.get("nota_registro"):
            print(f"      registro D71: {canon['nota_registro']}")
        if etiqueta == caso_canon:
            filas_salida.append(dict(caso=caso_canon, seg=round(seg, 3), **out))

    print()
    if tiempos:
        v = np.array(list(tiempos.values()))
        print(f"  tiempo por evaluacion (6 144 h, un proceso): mediana "
              f"{np.median(v):.2f} s, de {v.min():.2f} a {v.max():.2f} s")
    if not args.sin_escribir and filas_salida:
        destino = Path(args.salida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        campos = ["caso", "seg"] + sorted(
            {k for f in filas_salida for k in f} - {"caso", "seg"},
            key=lambda k: (k not in comun.SALIDAS, k))
        with open(destino, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=campos)
            w.writeheader()
            for f in filas_salida:
                w.writerow({k: (repr(v) if isinstance(v, float) else v)
                            for k, v in f.items()})
        print(f"  escrito {destino}")
    malas = [f for f in todas if not f[6]]
    omitidas = [f for f in todas if f[1].endswith(SIN_REFERENCIA)]
    if omitidas:
        print(f"  {len(omitidas)} comprobaciones SIN REFERENCIA"
              + (" (omitidas con aviso, --permite-omitir)" if
                 args.permite_omitir else " (cuentan como diferencias)")
              + f": {sorted({f[1] for f in omitidas})}")
    if malas:
        print(f"COMPUERTA GSA PUNTO BASE EN ROJO: {len(malas)} diferencias en "
              f"{len({f[0] for f in malas})} casos")
        return 1
    hechas = len(todas) - len(omitidas)
    print(f"COMPUERTA GSA PUNTO BASE EN VERDE: {hechas} comprobaciones "
          f"en {len(tiempos)} evaluaciones, todas al peso"
          + (f"; {len(omitidas)} OMITIDAS sin referencia" if omitidas
             else ""))
    return 0


if __name__ == "__main__":
    sys.exit(ejecuta())
