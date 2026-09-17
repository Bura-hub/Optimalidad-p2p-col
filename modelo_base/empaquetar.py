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
    # La serie de contratos de XM que usa C5 (precios_contratos.py). El
    # .gitignore excluye los .xlsx, asi que no llega con el clon: sin ella
    # toda corrida con --include-c5 falla al arrancar (humo de Linux,
    # 2026-09-14).
    "data/XM_Energía y Precios transados en contratos con destino a "
    "Mercado Regulado y No Regulado.xlsx",
    "main_simulation.py",
    # La corrida canonica toca ademas la comparacion y la liquidacion
    "scenarios/comparison_engine.py",
    # El motor nuevo del subproyecto 2 (Anexo 4 de la CREG 101 072, escalado
    # D10-D12, H-79). Sin estos, `matriz` y las pruebas de mas abajo fallan
    # con ImportError en un arbol recien clonado.
    "data/escalado.py",                        # D10-D12: escala la comunidad
    "data/capacidad_instalada.py",             # el numeral del art. 25
    "data/base_case_data.py",                  # parametros del caso sintetico
    "data/preprocessing.py",                   # PAPER_METER_DEMAND_CONFIG
    "data/xm_data_loader.py",                  # MTEDataLoader; lo usa paso_a_paso.carga
    "analysis/coincidencia.py",                # factor de coincidencia
    "analysis/feasibility.py",                 # FA-3: riesgo de desercion
    "scenarios/scenario_c1_creg174.py",        # C1: Anexo 4, permuta y excedente
    "scenarios/scenario_c3_spot.py",           # C3
    "scenarios/scenario_c4_creg101072.py",     # C4 mensual y P2P_colectivo
    "scenarios/scenario_c5_agr_creg101099.py", # C5, Resolucion 101 099
    "scenarios/scenario_p2p_colectivo.py",     # el reparto en dos niveles
    # Los pasos 4 y 5 de `matriz` (y de `oficial`): equidad por periodo de
    # cada caso. Estaban en la rama pero no en el paquete de respaldo.
    "analysis/equidad_periodo.py",
    # D48 a D62 (2026-09-17): el nucleo del reposo en forma cerrada, que el
    # motor importa, y el almacen, que gana la columna `precio_reposo` en los
    # flujos (tarea 2). Sin el almacen nuevo, `main_simulation.py` llama a
    # `anota_flujos` con un argumento que el viejo no conoce y la corrida
    # por reposo muere al anotar la primera hora.
    "core/reposo_mercado.py",
    "core/almacen.py",
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
    # El subproyecto 2 (2026-09-14): D25, la sonda de H-79 y el oraculo
    "reformateo/documento/scripts/sonda/reparto_vs_integrador.py",
    "reformateo/documento/scripts/sonda/oraculo_anexo4.py",  # lo importa el test
    # H-85 (2026-09-15): la comparacion de los dos arranques del acoplado,
    # D45 y D46. La corre la accion `arranque` y la importa su prueba.
    "reformateo/documento/scripts/sonda/compara_arranque.py",
    # H-86 (2026-09-16): el resumen del costo del criterio sobre el reparto,
    # D47. Lo corre la accion `convergencia`, al final de la campana.
    "reformateo/documento/scripts/sonda/censo_convergencia.py",
    # D48 (2026-09-17): la compuerta de salida de cada caso de
    # `matriz_reposo` y `barrido_sigma`, y la comparacion con la matriz vieja
    # (M-F). Las corre el lanzador y las importan sus pruebas.
    "reformateo/documento/scripts/sonda/compuertas_matriz_reposo.py",
    "reformateo/documento/scripts/sonda/compara_matriz_reposo.py",
    # Los pasos 4 y 5 de `matriz` (y de `oficial`): la liquidacion por
    # institucion y las figuras del foro de E0.
    "reformateo/documento/scripts/liquidacion.py",
    "reformateo/documento/scripts/gen_foro.py",     # importa liquidacion
    "reformateo/documento/scripts/gen_foro_b.py",   # importa paso_a_paso
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
    # Ronda de arreglo 1 (2026-09-14): estas cinco ya las usaba `compuertas`
    # antes de esta tarea y faltaban aqui.
    "tests/gate_almacen.py",
    "tests/gate_almacen_cruzado.py",
    "tests/gate_cal51_contrato.py",
    "tests/gate_cal52_contrato_interno.py",
    "tests/gate_c164_autoconsumo_autosuficiencia.py",
    # El subproyecto 2: el motor nuevo (Anexo 4, escalado, H-79). C-165 con
    # --horas: 48 en `compuertas`, 72 (su defecto) en `humo_linux`.
    "tests/gate_c165_desglose_horario.py",
    "tests/test_anexo4_tramo.py",
    "tests/test_escalado_umbrales.py",
    "tests/test_p2p_residual_art25.py",
    "tests/test_c4_mensual_norma.py",
    "tests/test_p2p_colectivo.py",
    "tests/test_c5_101099.py",
    "tests/test_mensual_suma_total.py",
    "tests/test_coincidencia.py",
    "tests/test_c3_costos_mem.py",
    "tests/test_plazo_por_hora.py",
    "tests/test_analisis_ligero.py",
    "tests/test_fa3_cumplimiento.py",
    "tests/test_analysis_numeral2.py",
    "tests/test_palancas_acoplado.py",     # importa tests/gate_c165_desglose_horario
    "tests/test_oraculo_anexo4.py",        # importa la sonda oraculo_anexo4
    "tests/test_presupuesto_acoplado.py",  # D36-D38; importa main_simulation
    "tests/test_piso_P.py",                # H-84, D40-D42; importa la C-165
    "tests/test_arranque_acoplado.py",     # H-85, D45; importa la C-165
    "tests/test_compara_arranque.py",      # H-85, D46; importa la sonda
    "tests/test_criterio_reparto.py",      # H-86, D47; importa la C-165
    "tests/test_censo_convergencia.py",    # H-86, D47; importa la sonda
    "tests/test_reposo_mercado.py",        # D48-D69, C-197: el nucleo
    "tests/test_reposo_motor.py",          # D48: la via por reposo en el motor
    "tests/test_compuertas_matriz_reposo.py",  # D48: la compuerta de salida
    "tests/test_compara_matriz_reposo.py",     # M-F: la comparacion
    # D49 / D50: la dinamica regularizada y su compuerta. `compuertas` la
    # corre con -k "not lenta" (las dos horas rapidas); las dos lentas van
    # aparte, con las ordenes del docstring de la compuerta (revision final,
    # menor 2). La prueba importa la compuerta, de modo que las dos viajan.
    "tests/test_dinamica_regularizada.py",
    "tests/gate_reposo_cero_dinamica.py",
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
    print("    bash modelo_base/run_servidor.sh humo_linux     # antes de E5 y de la matriz")
    print("    bash modelo_base/run_servidor.sh sonda79        # D25: escribe los veredictos")
    print("    bash modelo_base/run_servidor.sh matriz         # las 13 corridas, recoge al final")
    print("    bash modelo_base/run_servidor.sh arranque       # H-85: los dos arranques, E0 y E4")
    print("    bash modelo_base/run_servidor.sh convergencia   # H-86/D47: el costo del criterio del reparto")
    print("    bash modelo_base/run_servidor.sh matriz_reposo  # D48: las 13 corridas por reposo, con su compuerta de salida")
    print("    bash modelo_base/run_servidor.sh barrido_sigma  # D50: las 13 con sigma 0, 0,5 y 1, despues")
    print("  (antes de nada, SECO=1 bash modelo_base/run_servidor.sh matriz imprime")
    print("   las ordenes sin ejecutar ninguna)")


if __name__ == "__main__":
    main()
