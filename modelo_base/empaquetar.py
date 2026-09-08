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
    "data/xm_prices.py",                 # H-50: el techo de escasez y su guarda
    "data/precios_bolsa_xm_api.csv",     # la serie de bolsa, que el techo acota
    "main_simulation.py",
    # La corrida canonica toca ademas la comparacion y la liquidacion
    "scenarios/comparison_engine.py",
]
SONDAS = [
    "reformateo/documento/scripts/estilo.py",
    "reformateo/documento/scripts/datos.py",
    "reformateo/documento/scripts/sonda/hilos.py",   # un hilo por proceso
    "reformateo/documento/scripts/sonda/paso_a_paso.py",
    "reformateo/documento/scripts/sonda/caso_publicado.py",
    "reformateo/documento/scripts/sonda/competencia_real.py",
    "reformateo/documento/scripts/sonda/eficiencia.py",
    "reformateo/documento/scripts/sonda/cotas_excedente.py",
    "reformateo/documento/scripts/sonda/error_centralizado.py",
    # La tanda del 2026-09-07
    "reformateo/documento/scripts/sonda/techo_regimen.py",           # H-45
    "reformateo/documento/scripts/sonda/escenario_comercializador.py",  # H-47
    "reformateo/documento/scripts/sonda/peso_virtual.py",            # H-46
    "reformateo/documento/scripts/sonda/participacion.py",           # C-151
    "reformateo/documento/scripts/sonda/banda_adaptativa.py",        # CAL-47
    # La tanda del 2026-09-08: la decision del piso
    "reformateo/documento/scripts/sonda/recoge.py",         # plazo POR TAREA
    "reformateo/documento/scripts/sonda/regimen_piso.py",   # H-52, 4 regimenes
    "reformateo/documento/scripts/sonda/tramo_residual.py", # H-53
    "reformateo/documento/scripts/sonda/compara_regimenes.py",   # C-155
]
COMPUERTAS = [
    "tests/gate_c138_bienestar_comprador.py",
    "tests/gate_cal47_solucionador.py",
    "tests/gate_cal46_paso_horario.py",
    "tests/gate_cal49_competencia.py",
    "tests/gate_python310.py",
    "tests/gate_h45_techo_por_comprador.py",
    "tests/gate_h46_peso_virtual.py",
    "tests/gate_c146_techo_en_el_juego.py",       # el techo llega al juego
    "tests/gate_c151_participacion_motor.py",     # la restriccion de participar
    "tests/gate_h55_bienestar_precio.py",         # el bienestar no arbitra
    "tests/gate_c156_plazo_por_tarea.py",         # el plazo por tarea corta
    "tests/golden_test_sofia.py",
]
LANZADOR = [
    "modelo_base/run_servidor.sh",
    "modelo_base/MONTAJE_SERVIDOR.md",
]


# El arbol de Windows tiene finales de linea CRLF, incluidos ficheros que
# nadie edito: asi los deja el checkout. El tar los llevaba tal cual a Linux,
# donde bash lee un retorno de carro pegado a la ultima opcion de `set`
# y responde «invalid option», con ese mismo retorno de carro comiendose el
# retorno de carro comiendose el propio mensaje de error. Paso el 2026-09-07
# y costo una parada en seco a mitad del montaje.
#
# El paquete se NORMALIZA a LF al armarlo. Es el sitio correcto: el arbol
# local se queda como esta y lo que viaja es siempre valido en el destino.
TEXTO = {".sh", ".py", ".md", ".csv", ".tex", ".txt", ".cfg", ".toml", ".yml"}

# Construidos con chr() a proposito: un literal con barra invertida
# no sobrevive a un heredoc del shell, que es como se rompio este
# fichero la primera vez.
CRLF = (chr(13) + chr(10)).encode()
LF = chr(10).encode()


def contenido(p: Path) -> bytes:
    """Los bytes que van al paquete, con LF si el fichero es de texto."""
    crudo = p.read_bytes()
    if p.suffix.lower() in TEXTO:
        return crudo.replace(CRLF, LF)
    return crudo


def sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(contenido(p))          # la huella es la de lo que VIAJA
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
    import io

    def mete(tar, ruta: Path, nombre: str) -> None:
        datos = contenido(ruta)
        info = tar.gettarinfo(str(ruta), arcname=nombre)
        info.size = len(datos)               # cambia al normalizar
        if nombre.endswith(".sh"):
            info.mode |= 0o111               # ejecutable, por si acaso
        tar.addfile(info, io.BytesIO(datos))

    with tarfile.open(destino, "w:gz") as tar:
        for f in todos:
            mete(tar, RAIZ / f, f)
        mete(tar, manifiesto, "modelo_base/MANIFIESTO.txt")

    mb = destino.stat().st_size / 1e6
    print(f"  paquete: {destino}")
    print(f"  {len(todos) + 1} ficheros · {mb:.2f} MB")
    print(f"  rama {rama} · commit {commit}")
    print()
    print("  En el servidor:")
    print("    tar xzf paquete_modelo_base_*.tar.gz -C /ruta/al/repo")
    print("    bash modelo_base/run_servidor.sh entorno")
    print("    bash modelo_base/run_servidor.sh compuertas")
    print("    bash modelo_base/run_servidor.sh decision 200   # H-52/H-53, LA QUE DECIDE")
    print("    bash modelo_base/run_servidor.sh tanda 200      # H-45, H-46, H-47")
    print("    bash modelo_base/run_servidor.sh canonica       # la corrida entera")
    print("    bash modelo_base/run_servidor.sh recoger")


if __name__ == "__main__":
    main()
