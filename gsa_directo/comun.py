"""Lo que comparten todas las piezas del GSA directo (D73 a D79).

Actividad 4.1. El diseno esta en
`docs/superpowers/specs/2026-09-26-gsa-directo-design.md`; los valores de
este modulo (entradas, rangos, salidas, n) son los aprobados, tal cual.

- Seis entradas, todas incertidumbres y todas uniformes (D74).
- Catorce salidas de comunidad que entran al Sobol (D75), mas las que se
  guardan para comprobar identidades (C2, los conteos) y las brechas por
  institucion, que solo se publican con su probabilidad de inversion.
- Desde el 2026-10-02, nueve salidas mas AL FINAL, sin cambiar el
  significado de ninguna de D75: los niveles de C2 como PPA (`C2ppa`, CANON
  §14.22) y del P2P colectivo (`P2Pcom`, §14.23) y sus siete brechas, que
  tambien se guardan por institucion.
- Desde el 2026-10-04, cinco mas detras: el nivel de H1, el credito
  mutualizado (§14.26), y sus cuatro brechas; por institucion, ademas, H1
  con la compensacion contra C4 y contra C1.
- Los trece casos de la matriz, con la MISMA opcion que `CASOS_MATRIZ` de
  `modelo_base/run_servidor.sh` (una prueba lo comprueba), y el n de cada uno
  (D77): 2 048 en E0, E2 y E4; 512 en los demas. El Sobol corre en doce
  (`CASOS_SOBOL`): CV2 queda solo como contraste determinista.
- Saltelli de segundo orden: bloques de 2D + 2 = 14 filas por punto base,
  anidados con la misma semilla (los n' primeros bloques de la muestra de n
  son la muestra de n').
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shlex
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# ── Entradas (D74) ──────────────────────────────────────────────────────────
NOMBRES = ["f_cv", "f_bolsa", "f_tarifa", "f_peaje", "e_G", "e_D"]
SOPORTES = [[0.25, 2.0],     # descuento de comercializar sobre la permuta
            [0.75, 4.0],     # nivel de la bolsa (antes del techo PES)
            [0.90, 1.10],    # nivel del costo unitario (el techo)
            [0.85, 1.15],    # nivel de T+D+PR+R
            [0.95, 1.05],    # error de medida de la generacion
            [0.95, 1.05]]    # error de medida de la demanda
# Como se rotula cada entrada en TODAS las salidas (indices, S2, informe,
# deterministas). f_cv NO es el Cv de la tarifa: es el factor sobre el
# componente de comercializar que el art. 25 descuenta de la permuta para el
# piso del vendedor (y el mismo que usan C1, C4, el colectivo y los
# residuales, como `--factor-cv` de `main()`, D7); no toca `cvm_component` de
# C5 ni el techo.
ROTULOS = {
    "f_cv": "descuento de comercializar sobre la permuta (art. 25)",
    "f_bolsa": "nivel de la bolsa (antes del techo PES)",
    "f_tarifa": "nivel del costo unitario (el techo)",
    "f_peaje": "nivel de T+D+PR+R",
    "e_G": "error de medida de la generacion",
    "e_D": "error de medida de la demanda",
}
PROBLEMA = {"num_vars": len(NOMBRES), "names": list(NOMBRES),
            "bounds": [list(s) for s in SOPORTES]}
D_ENTRADAS = len(NOMBRES)
SEGUNDO_ORDEN = True
B = 2 * D_ENTRADAS + 2           # filas por bloque de Saltelli: 14
SEMILLA = 42
PUNTO_BASE = np.ones(D_ENTRADAS)

# ── Salidas (D75) ───────────────────────────────────────────────────────────
NIVELES = ("P2P", "P2P_colectivo", "C1", "C3", "C4", "C5")
CONTROLES = ("energia", "excedente")
REPARTO = ("parte_vendedor",)
# Brecha -> (minuendo, sustraendo). P2P - C1 es la identidad de H-70 (ancho
# de banda por energia): se declara antes de leerla como hallazgo.
BRECHAS = {
    "P2P_menos_C1": ("P2P", "C1"),
    "P2P_menos_C4": ("P2P", "C4"),
    "P2Pcol_menos_C1": ("P2P_colectivo", "C1"),
    "C4_menos_C1": ("C4", "C1"),
    "P2P_menos_C5": ("P2P", "C5"),
}
SALIDAS_D75 = NIVELES + CONTROLES + REPARTO + tuple(BRECHAS)  # las 14 de D75

# ── Los dos mecanismos nuevos (2026-10-02, CANON §14.22 y §14.23) ───────────
# Se AÑADEN al final, sin tocar el significado de ninguna salida de D75.
# Los nombres son los de las claves del canon y de `cifras.csv`:
#
# - `C2ppa`: el C2 de la propuesta medido como PPA (punto P, §14.22): cada
#   institucion vende TODO su excedente horario a PP constante = la media de
#   la serie de XM de contratos del mercado no regulado en el horizonte
#   (287,41 COP/kWh), sin credito; autoconsumo a la tarifa. NO es la columna
#   `C2` de arriba (el contrato interno de CAL-52, identidad con P2P).
# - `P2Pcom`: el «P2P colectivo» de la decision del autor del 2026-10-02 (el
#   P2P comunitario del punto PC, §14.23): el intercambio del mercado sin
#   cargos y fuera del fondo; el residual al autogenerador colectivo con el
#   PDE igual, en el caso del art. 20 sin la regla del 10 %. Se llama
#   `P2Pcom` y no `P2Pcol` porque `P2Pcol_menos_C1` ya es, desde D75, la
#   brecha del VIEJO mercado por el colectivo (`P2P_colectivo`), que se
#   conserva para comparar (las claves `*P2Pcol*` del canon siguen siendo el
#   viejo, §14.23).
NIVELES_NUEVOS = ("P2Pcom", "C2ppa")
BRECHAS_NUEVAS = {
    "P2Pcom_menos_C4": ("P2Pcom", "C4"),
    "P2Pcom_menos_C1": ("P2Pcom", "C1"),
    "P2Pcom_menos_P2P": ("P2Pcom", "P2P"),
    "C2ppa_menos_C1": ("C2ppa", "C1"),
    "C2ppa_menos_C4": ("C2ppa", "C4"),
    "C2ppa_menos_P2P": ("C2ppa", "P2P"),
    "P2Pcom_menos_C2ppa": ("P2Pcom", "C2ppa"),
}
ROTULOS_SALIDAS = {
    "P2P_colectivo": "mercado P2P por el colectivo (el viejo; v(0,0) de §14.21)",
    "P2Pcol_menos_C1": "viejo mercado por el colectivo - C1",
    "P2Pcom": "P2P colectivo (propuesta, punto PC, §14.23)",
    "C2ppa": "C2 como PPA a la media de XM (punto P, §14.22)",
}
# ── H1, el credito mutualizado (2026-10-04, CANON §14.26) ───────────────────
# Otra vez AL FINAL, sin tocar ninguna de las anteriores. `H1` es «H1 fondo»
# de `hibrido_por_planta.py`, la lectura exacta y la que se cita: sin
# intercambio, toda la inyeccion al fondo de C4, deducida por el numeral del
# art. 25 de la planta de origen y repartida por mes «primero lo propio».
# `H1comp` es H1 con la compensacion de quien cede credito: suma cero, de
# modo que en la comunidad es H1 y solo se guarda por institucion.
NIVELES_H1 = ("H1",)
BRECHAS_H1 = {
    "H1_menos_C4": ("H1", "C4"),
    "H1_menos_C1": ("H1", "C1"),
    "H1_menos_P2P": ("H1", "P2P"),
    "H1_menos_P2Pcom": ("H1", "P2Pcom"),
}
BRECHAS_H1_INSTITUCION = {
    **BRECHAS_H1,
    "H1comp_menos_C4": ("H1comp", "C4"),
    "H1comp_menos_C1": ("H1comp", "C1"),
}
ROTULOS_SALIDAS["H1"] = ("H1, credito mutualizado sin intercambio (punto H1, "
                         "§14.26)")
ROTULOS_SALIDAS["H1comp"] = "H1 con la compensacion de quien cede credito"
# El numeral 1 del art. 25 de la CREG 174, por capacidad instalada (§14.26).
UMBRAL_NUMERAL1_KW = 100.0
# Todas las brechas de comunidad, las de D75 primero y en su orden.
BRECHAS = {**BRECHAS, **BRECHAS_NUEVAS, **BRECHAS_H1}
NIVELES = NIVELES + NIVELES_NUEVOS + NIVELES_H1
SALIDAS = (SALIDAS_D75 + NIVELES_NUEVOS + tuple(BRECHAS_NUEVAS)  # 14 + 9
           + NIVELES_H1 + tuple(BRECHAS_H1))                     # + 5
# Se guardan y no entran al Sobol: C2 coincide con P2P en el agregado
# (CAL-52) y se comprueba como identidad; los conteos son las guardas.
IDENTIDADES = ("C2",)
CONTEOS = ("n_horas_mercado", "n_cuantal", "n_sin_ganancia", "retiros")
BRECHAS_INSTITUCION = {
    "P2P_menos_C1": ("P2P", "C1"),
    "P2P_menos_C4": ("P2P", "C4"),
    "P2P_menos_C5": ("P2P", "C5"),
    **BRECHAS_NUEVAS,
    **BRECHAS_H1_INSTITUCION,
}
# Lo que fija el P2P colectivo (§14.23): el umbral de la capacidad por
# usuario del art. 18 y el tope de la suma (1 MW) del art. 20, SIN la regla
# del 10 % del PDE.
UMBRAL_CINAC_KW = 100.0
LIMITE_COLECTIVO_KW = 1000.0
INSTITUCIONES = ["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]


def salidas_institucion(nombres) -> list:
    """Las brechas por institucion, `<brecha>__<institucion>`; 80 con las
    cinco y 64 en SINU (las 3 de D75, las 7 de C2ppa y P2Pcom y las 6 de
    H1)."""
    return [f"{b}__{n}" for n in nombres for b in BRECHAS_INSTITUCION]


def columnas_salida(nombres) -> list:
    return (list(SALIDAS) + list(IDENTIDADES) + list(CONTEOS)
            + salidas_institucion(nombres))


# ── Los trece casos (misma opcion que CASOS_MATRIZ del lanzador) ────────────
CASOS = {
    "E0": "",
    "E1": "--factor-generacion 3",
    "E2": "--factor-generacion 4",
    "E3": "--factor-generacion 5.6",
    "E4": "--factor-generacion 7",
    "E5": "--factor-generacion 10",
    "P1": "--factor-demanda 1/7",
    "P2": "--factor-generacion 7 --factor-demanda 7",
    "K1": "--factor-demanda 2",
    "I1": "--escala-agente UCC:neto_cero",
    "N1": "--neto-cero",
    "CV2": "--factor-cv 2",
    "SINU": "--excluir-agente Udenar",
}
# Orden de prioridad del apartado 5.4: los tres puntos de diseno primero; si
# el tiempo aprieta, los demas en este orden.
ORDEN_CASOS = ("E0", "E2", "E4", "E1", "E3", "E5", "P1", "P2", "K1", "I1",
               "N1", "CV2", "SINU")
# Los casos que corren el Sobol (ronda de arreglos de la tarea G, I-1). CV2
# NO: es E0 con el costo de comercializar x2, y el Sobol de E0 ya recorre
# f_cv en [0,25; 2]. Sobre CV2, f_cv volveria a multiplicar un cvm que ya
# viene x2 y sacaria el descuento del rango aprobado (D74): medido, 6 de 512
# bloques con el piso de Cesmag negativo, 1,17 %, que detiene el analisis.
# CV2 sigue en ORDEN_CASOS para la compuerta del punto base (y su contraste
# con E0 a f_cv = 2) y para las deterministas.
SOLO_DETERMINISTAS = ("CV2",)
CASOS_SOBOL = tuple(c for c in ORDEN_CASOS if c not in SOLO_DETERMINISTAS)
CASOS_DISENO = ("E0", "E2", "E4")
N_BASE_DISENO = 2048
N_BASE_RESTO = 512


def n_base_de(caso: str, n_diseno: int = N_BASE_DISENO,
              n_resto: int = N_BASE_RESTO) -> int:
    return int(n_diseno if caso in CASOS_DISENO else n_resto)


def opciones_caso(caso: str) -> dict:
    """La opcion del caso, leida como la lee `main_simulation.py`, en los
    argumentos de su `main()`."""
    if caso not in CASOS:
        raise ValueError(f"caso {caso!r} no es ninguno de los trece: "
                         f"{', '.join(CASOS)}")
    from data.escalado import lee_factor
    ap = argparse.ArgumentParser(prog=f"caso {caso}", add_help=False)
    ap.add_argument("--factor-generacion", default="1")
    ap.add_argument("--factor-demanda", default="1")
    ap.add_argument("--escala-agente", default=None)
    ap.add_argument("--neto-cero", action="store_true")
    ap.add_argument("--factor-cv", default="1")
    ap.add_argument("--excluir-agente", default=None)
    a = ap.parse_args(shlex.split(CASOS[caso]))
    return dict(factor_generacion=lee_factor(a.factor_generacion),
                factor_demanda=lee_factor(a.factor_demanda),
                escala_agente=a.escala_agente, neto_cero=bool(a.neto_cero),
                factor_cv=lee_factor(a.factor_cv),
                excluir_agente=a.excluir_agente)


def nombres_caso(caso: str) -> list:
    fuera = [n.strip() for n in (opciones_caso(caso)["excluir_agente"] or "")
             .split(",") if n.strip()]
    return [n for n in INSTITUCIONES if n not in fuera]


# ── Muestra ─────────────────────────────────────────────────────────────────
def muestra(n_base: int, semilla: int = SEMILLA) -> np.ndarray:
    """La muestra de Saltelli de segundo orden: n_base bloques de B filas."""
    from SALib.sample import sobol as sobol_sample
    X = sobol_sample.sample(PROBLEMA, int(n_base),
                            calc_second_order=SEGUNDO_ORDEN, seed=semilla)
    if X.shape != (int(n_base) * B, D_ENTRADAS):
        raise ValueError(f"muestra {X.shape}, se esperaba "
                         f"({int(n_base) * B}, {D_ENTRADAS})")
    return X


def es_potencia_de_dos(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


# ── Huellas y rutas ─────────────────────────────────────────────────────────
def huella_diseno(caso: str, n_base: int, semilla: int = SEMILLA) -> str:
    """Huella del diseno: si cambia una entrada, un rango, el caso, n o la
    semilla, dos corridas no pueden mezclarse bajo los mismos indices."""
    s = (f"{caso}|{CASOS.get(caso)}|{int(n_base)}|{int(semilla)}|"
         f"{SEGUNDO_ORDEN}|{'/'.join(NOMBRES)}|{SOPORTES}")
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def huella_datos(mte_root) -> str:
    """Huella del dato: el inventario de MTE_ROOT (ruta relativa y tamano de
    cada .csv/.xlsx, sin leerlos) y el contenido de los .py y .csv de `data/`
    (tarifas, bolsa, PES, contratos, cargadores). Si cambia, el `.npz` de la
    carga se rehace y `--reanudar` aborta en vez de mezclar poblaciones."""
    h = hashlib.sha256()
    raiz = Path(mte_root)
    h.update(str(raiz.name).encode())
    if not raiz.is_dir():
        raise FileNotFoundError(f"MTE_ROOT no es una carpeta: {raiz}")
    for p in sorted(raiz.rglob("*")):
        if p.is_file() and p.suffix.lower() in (".csv", ".xlsx", ".xls"):
            h.update(f"{p.relative_to(raiz).as_posix()}:{p.stat().st_size}|"
                     .encode())
    datos = RAIZ / "data"
    for p in sorted(list(datos.glob("*.py")) + list(datos.glob("*.csv"))):
        h.update(p.name.encode())
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()[:16]


def mte_root_defecto() -> str:
    return os.environ.get("MTE_ROOT", str(RAIZ / "MedicionesMTE_v3"))


def salidas_defecto() -> Path:
    return RAIZ / "SALIDAS_SERVIDOR" / "gsa_directo"


def nombre_muestras(caso: str, n_base: int, semilla: int = SEMILLA) -> str:
    return f"muestras_{caso}_n{int(n_base)}_s{int(semilla)}.csv"


def version_codigo() -> str:
    """El commit del arbol, para el `.meta.json`. Sin git, lo dice."""
    import subprocess
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ,
                           capture_output=True, text=True, timeout=10)
        sucio = subprocess.run(["git", "status", "--porcelain",
                                "--untracked-files=no"], cwd=RAIZ,
                               capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return r.stdout.strip() + ("+cambios" if sucio.stdout.strip()
                                       else "")
    except (OSError, subprocess.SubprocessError):
        pass
    return "sin git"


def rss_mb() -> float:
    """Memoria residente maxima de ESTE proceso (MB). En Linux por
    `resource`; en Windows por la API del sistema. Es una medida, no un
    resultado: donde no se puede medir devuelve NaN y el humo lo dice."""
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except ImportError:
        pass
    if sys.platform != "win32":
        return float("nan")
    import ctypes
    from ctypes import wintypes

    class _PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    c = _PMC()
    c.cb = ctypes.sizeof(_PMC)
    k32 = ctypes.WinDLL("kernel32")
    psapi = ctypes.WinDLL("psapi")
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.GetCurrentProcess.argtypes = []
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,
                                           ctypes.POINTER(_PMC),
                                           wintypes.DWORD]
    if psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c),
                                  c.cb):
        return c.PeakWorkingSetSize / (1024.0 * 1024.0)
    return float("nan")


def salida_utf8() -> None:
    """Como `main_simulation.py`: en Windows la consola y la redireccion a
    fichero salen en cp1252; se reconfigura en sitio a UTF-8."""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
