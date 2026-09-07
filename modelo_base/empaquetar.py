"""
Arma el paquete que se lleva al servidor.

El servidor clona el repositorio, pero **nada de esta tanda esta commiteado**,
de modo que hace falta llevarle los cambios a mano. Este script recoge
exactamente los ficheros que las mediciones necesitan y los mete en un
tar.gz, junto con un manifiesto que dice de que arbol salieron.

No toca git ni el indice: solo lee ficheros y escribe el archivo.

Uso:
    python modelo_base/empaquetar.py
    python modelo_base/empaquetar.py --salida /ruta/al/paquete.tar.gz
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Lo que el servidor necesita y no viene del repositorio. Se enumera a mano
# a proposito: un comodin acabaria metiendo mediciones viejas y cache.
NUCLEO = [
    "core/coupled_ode_convergence.py",   # las tres formas de competencia
    "core/replicator_buyers.py",         # idem, y la nota corregida
    "core/ems_p2p.py",                   # metodo y t_span acoplado
    "core/market_prep.py",               # techo vectorial
    "core/settlement.py",                # cotas vectoriales
    "core/opciones_externas.py",         # permuta y pisos
    "data/cedenar_tariff.py",            # dos comercializadores, no regulados
    "data/tarifas_asc_mensual.csv",      # tarifas de ASC
    "main_simulation.py",
]
SONDAS = [
    "reformateo/documento/scripts/estilo.py",
    "reformateo/documento/scripts/datos.py",
    "reformateo/documento/scripts/sonda/paso_a_paso.py",
    "reformateo/documento/scripts/sonda/caso_publicado.py",
    "reformateo/documento/scripts/sonda/competencia_real.py",
    "reformateo/documento/scripts/sonda/eficiencia.py",
    "reformateo/documento/scripts/sonda/cotas_excedente.py",
    "reformateo/documento/scripts/sonda/error_centralizado.py",
]
COMPUERTAS = [
    "tests/gate_c138_bienestar_comprador.py",
    "tests/gate_cal47_solucionador.py",
    "tests/gate_cal46_paso_horario.py",
    "tests/golden_test_sofia.py",
]
LANZADOR = [
    "modelo_base/run_servidor.sh",
    "modelo_base/MONTAJE_SERVIDOR.md",
]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()[:16]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=None)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    marca = datetime.now().strftime("%Y-%m-%d_%H%M")
    destino = Path(args.salida) if args.salida else (
        RAIZ / "modelo_base" / f"paquete_modelo_base_{marca}.tar.gz")

    todos = NUCLEO + SONDAS + COMPUERTAS + LANZADOR
    faltan = [f for f in todos if not (RAIZ / f).exists()]
    if faltan:
        print("  faltan ficheros, no se empaqueta:")
        for f in faltan:
            print(f"    {f}")
        raise SystemExit(1)

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                cwd=RAIZ, capture_output=True, text=True,
                                check=True).stdout.strip()
        rama = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                              cwd=RAIZ, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        commit, rama = "desconocido", "desconocida"

    lineas = [
        "Paquete de mediciones del modelo base",
        f"armado el {datetime.now():%Y-%m-%d %H:%M}",
        f"sobre la rama {rama}, commit {commit}",
        "",
        "ATENCION: estos ficheros NO estan commiteados. El commit de arriba",
        "es el del arbol del que salieron, no el que los contiene.",
        "",
        f"{'sha256':>16s}  {'bytes':>9s}  fichero",
    ]
    for f in todos:
        p = RAIZ / f
        lineas.append(f"{sha(p):>16s}  {p.stat().st_size:9d}  {f}")

    manifiesto = RAIZ / "modelo_base" / "MANIFIESTO.txt"
    manifiesto.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    destino.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destino, "w:gz") as tar:
        for f in todos:
            tar.add(RAIZ / f, arcname=f)
        tar.add(manifiesto, arcname="modelo_base/MANIFIESTO.txt")

    mb = destino.stat().st_size / 1e6
    print(f"  paquete: {destino}")
    print(f"  {len(todos) + 1} ficheros · {mb:.2f} MB")
    print(f"  rama {rama} · commit {commit}")
    print()
    print("  En el servidor:")
    print("    tar xzf paquete_modelo_base_*.tar.gz -C /ruta/al/repo")
    print("    bash modelo_base/run_servidor.sh entorno")
    print("    bash modelo_base/run_servidor.sh todo")


if __name__ == "__main__":
    main()
