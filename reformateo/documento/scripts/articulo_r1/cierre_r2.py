"""
cierre_r2.py — Corre las mediciones completas de AE-5 y AE-4 y el tope del
precio único, y junta `cifras.csv`, `GUIONES.csv` y `procedencia.txt`
(CANON §14.41)
===============================================================================
Corre m2r, m10, m1r, m9, m11 y m12, cada una en su proceso y en primer plano; si una falla, se
detiene. Antes deja en `logs/canon_antes.log` la salida de
`verificar_canon_2026-09.py`, que tiene que terminar en INTACTO. Sin fecha en
ningún fichero: con el mismo árbol, dos corridas dan los mismos ficheros.

    PYTHONUNBUFFERED=1 .venv/Scripts/python.exe -u reformateo/documento/scripts/articulo_r1/cierre_r2.py
"""
from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy

for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[4]
AQUI = Path(__file__).resolve().parent
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "articulo_r1_resuelta_2026-11-21"
ORDEN = [("m2r", "m2r_factorial_resuelto.py"), ("m10", "m10_un_comercializador.py"), ("m1r", "m1r_corte_secuencial.py"),
         ("m9", "m9_tope_precio.py"), ("m11", "m11_trm_banrep.py"), ("m12", "m12_miembros_c4.py")]
# los guiones de esta medicion y los modulos del proyecto que liquidan
GUIONES = ["reformateo/documento/scripts/articulo_r1/ar1_comun.py",
           "reformateo/documento/scripts/articulo_r1/ar2_comun.py",
           "reformateo/documento/scripts/articulo_r1/m2r_factorial_resuelto.py",
           "reformateo/documento/scripts/articulo_r1/m1r_corte_secuencial.py",
           "reformateo/documento/scripts/articulo_r1/m9_tope_precio.py",
           "reformateo/documento/scripts/articulo_r1/m10_un_comercializador.py",
           "reformateo/documento/scripts/articulo_r1/m11_trm_banrep.py",
           "reformateo/documento/scripts/articulo_r1/m12_miembros_c4.py",
           "reformateo/documento/scripts/articulo_r1/cierre_r2.py",
           "reformateo/documento/scripts/sonda/compuerta_r1.py", "reformateo/documento/scripts/sonda/especificacion_r1.py",
           "scenarios/esquinas_supuestos.py", "analysis/shapley_factorial.py",
           "core/corte_secuencial.py", "core/opciones_externas.py"]


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.rstrip("\n")


def main() -> int:
    (SALIDA / "logs").mkdir(parents=True, exist_ok=True)
    v = subprocess.run([sys.executable, "-u", str(RAIZ / "Documentos/canon_2026-09/verificar_canon_2026-09.py")],
                       cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    (SALIDA / "logs" / "canon_antes.log").write_text("\n".join(
        x for x in v.stdout.splitlines() if x.strip()).rstrip() + "\n", encoding="utf-8", newline="\n")
    if v.returncode != 0 or not v.stdout.rstrip().endswith("CANON 2026-09 INTACTO"):
        raise SystemExit("[ar2:cierre] el canon no está intacto antes de medir")
    for nom, guion in ORDEN:
        print(f"[ar2:cierre] corre {guion}", flush=True)
        r = subprocess.run([sys.executable, "-u", str(AQUI / guion)], cwd=RAIZ, capture_output=True, text=True,
                           encoding="utf-8", timeout=3600)
        if r.returncode != 0:
            print(r.stdout[-3000:])
            print(r.stderr[-3000:])
            raise SystemExit(f"[ar2:cierre] {guion} terminó con código {r.returncode}")
    # M1 de la auditoría: la compuerta de la especificación (compuerta_r1.py
    # --canon) sobre las 81 corridas; un cargo o un piso mal puestos fallan.
    canon = RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19" / "SALIDAS_SERVIDOR" / "matriz_reposo"
    gate = RAIZ / "reformateo" / "documento" / "scripts" / "sonda" / "compuerta_r1.py"
    corridas = [("esquina", e, c) for e in ("p2p", "solo1", "solo2", "ninguno") for c in
                ("E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1", "CV2", "SINU")]
    corridas += [("corte", v, c) for v in ("iterado", "secuencial_saldo") for c in
                 ("E1", "E2", "E3", "E4", "E5", "P1", "I1", "N1")]
    corridas += [("corte", "secuencial_pronostico", c) for c in
                 ("E1", "E2", "E3", "E4", "E5", "P1", "I1", "N1", "E0", "P2", "K1", "CV2", "SINU")]
    # el retome de B1 y B2 (e1a0e40): solo1 con el punto fijo de su corte y el
    # iterado del corte con los dos estados del ciclo (24 corridas)
    retome = []
    for base in ("matriz_esquina_solo1_iterado", "matriz_corte_iterado_b2"):
        for d in sorted((RAIZ / "SALIDAS_SERVIDOR" / base).iterdir()):
            if d.is_dir():
                retome.append(("retome", base, d.name))
    esp = []
    for tipo, v, c in corridas + retome:
        if tipo == "retome":
            alm = RAIZ / "SALIDAS_SERVIDOR" / v / c / "almacen"
            c = c.split("_")[0]
        else:
            alm = RAIZ / "SALIDAS_SERVIDOR" / f"matriz_{tipo}_{v}" / c / "almacen"
        r = subprocess.run([sys.executable, "-u", str(gate), str(alm), "--cobertura", "m1", "--caso", c,
                            "--canon", str(canon)], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=1200)
        ult = [x.strip() for x in r.stdout.splitlines() if x.strip()]
        fallos = [x.strip() for x in r.stdout.splitlines() if x.strip().startswith("MAL")]
        esp.append(f"{tipo} {v} {c}: codigo {r.returncode}; {ult[-1] if ult else '(sin salida)'}"
                   + ("; " + "; ".join(fallos) if fallos else ""))
        if r.returncode != 0 or not ult or not ult[-1].endswith("EN VERDE"):
            (SALIDA / "logs" / "especificacion_81.log").write_text("\n".join(esp) + "\n", encoding="utf-8", newline="\n")
            raise SystemExit(f"[ar2:cierre] la compuerta de la especificación falla en {tipo} {v} {c}")
    (SALIDA / "logs" / "especificacion_81.log").write_text(
        "\n".join(esp) + f"\nretome: {len(retome)} de {len(retome)} corridas EN VERDE\n"
        f"{len(corridas)} de {len(corridas)} corridas EN VERDE\n", encoding="utf-8", newline="\n")
    print(f"[ar2:cierre] especificación: {len(corridas)} corridas y {len(retome)} del retome en verde", flush=True)
    partes, n_comp, lineas, leidos, insumos = [], 0, [], [], []
    for nom, guion in ORDEN:
        p = SALIDA / f"cifras_{nom}.csv"
        c = pd.read_csv(p, dtype=str, keep_default_na=False)
        if list(c.columns) != ["clave", "valor", "unidad", "fuente"] or len(c) == 0:
            raise SystemExit(f"[ar2:cierre] {p.name} sin cifras o con otra cabecera")
        partes.append(c)
        log = (SALIDA / "logs" / f"{nom}.log").read_text(encoding="utf-8").splitlines()
        comp = [x.split("  OK  ", 1)[1] for x in log if "  OK  " in x]
        fin = [x for x in log if x.endswith(" cifras") and " compuertas, " in x]
        if not fin or f"{len(comp)} compuertas, {len(c)} cifras" not in fin[-1]:
            raise SystemExit(f"[ar2:cierre] el registro de {nom} no cuadra con sus cifras y compuertas")
        n_comp += len(comp)
        lineas.append(f"{nom} ({guion}): {len(comp)} compuertas, {len(c)} cifras")
        lineas += [f"  - {x}" for x in comp]
        modo = None
        for x in log:
            if "artefactos leídos con huella" in x:
                modo = leidos
            elif "insumos sin huella" in x:
                modo = insumos
            elif x.startswith("[ar1:"):
                modo = None
            elif modo is not None and x.startswith("  "):
                if x.strip() not in modo:
                    modo.append(x.strip())
    cif = pd.concat(partes, ignore_index=True)
    if cif.clave.duplicated().any():
        raise SystemExit(f"[ar2:cierre] claves repetidas: {list(cif.clave[cif.clave.duplicated()])[:5]}")
    cif.to_csv(SALIDA / "cifras.csv", index=False, lineterminator="\n")
    for nom, _ in ORDEN:
        (SALIDA / f"cifras_{nom}.csv").unlink()
    with open(SALIDA / "GUIONES.csv", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("ruta,bytes,sha256\n")
        for g in GUIONES:
            d = (RAIZ / g).read_bytes()
            fh.write(f"{g},{len(d)},{hashlib.sha256(d).hexdigest()}\n")
    with open(SALIDA / "procedencia.txt", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("articulo_r1_resuelta: AE-5 y AE-4 con el mercado resuelto y el tope del precio único, CANON §14.41\n")
        fh.write(f"git rev-parse HEAD: {git('rev-parse', 'HEAD')}\n")
        fh.write("cambios sin commit en los guiones y módulos de GUIONES.csv:\n")
        fh.write((git("status", "--porcelain", "--", *GUIONES) or "(ninguno)") + "\n")
        fh.write(f"python {platform.python_version()}, numpy {np.__version__}, scipy {scipy.__version__}, pandas {pd.__version__}\n")
        fh.write("orden: python -u reformateo/documento/scripts/articulo_r1/cierre_r2.py\n")
        fh.write("corridas: las 81 del servidor del 2026-11-21 (revision_r1_resuelta; commits 57fbb55 y abf83ab, mismo núcleo), "
                 "en SALIDAS_SERVIDOR/matriz_esquina_<esquina>/ y matriz_corte_<variante>/\n")
        fh.write("no simula: no importa el motor ni resuelve el mercado; liquida con scenarios/esquinas_supuestos.py, "
                 "core/opciones_externas.reparto_anexo4 y core/corte_secuencial.liquida_fifo\n")
        fh.write(f"compuertas: {n_comp}\n")
        fh.write(f"cifras: {len(cif)}\n")
        fh.write("\n".join(lineas) + "\n")
        fh.write(f"artefactos leídos con huella: {len(leidos)}\n")
        fh.write("\n".join(f"  {x}" for x in sorted(leidos)) + "\n")
        fh.write(f"ficheros de las corridas y de data/ leídos, con su tamaño y su sha256: {len(insumos)}\n")
        fh.write("\n".join(f"  {x}" for x in sorted(insumos)) + "\n")
    print(f"[ar2:cierre] {n_comp} compuertas, {len(cif)} cifras, {len(GUIONES)} guiones y módulos, {len(leidos)} artefactos "
          f"con huella, {len(insumos)} ficheros de las corridas y de data/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
