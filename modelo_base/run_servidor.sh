#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Mediciones del modelo base — lanzador del servidor
#
#   bash modelo_base/run_servidor.sh entorno            <- UNA vez, primero
#   bash modelo_base/run_servidor.sh compuertas         <- antes de medir
#   bash modelo_base/run_servidor.sh caso               <- barato, sin datos MTE
#   bash modelo_base/run_servidor.sh competencia M1 60
#   bash modelo_base/run_servidor.sh eficiencia  M1 60
#   bash modelo_base/run_servidor.sh todo        60
#
#   --- la tanda del 2026-09-07 -------------------------------------------
#   bash modelo_base/run_servidor.sh techo       200    <- H-45
#   bash modelo_base/run_servidor.sh escenario   200    <- H-47
#   bash modelo_base/run_servidor.sh pesovirtual 200    <- H-46
#   bash modelo_base/run_servidor.sh tanda       200    <- las tres seguidas
#   bash modelo_base/run_servidor.sh canonica           <- la corrida entera
#
#   --- la tanda del 2026-09-08: la decision del piso ---------------------
#   bash modelo_base/run_servidor.sh tramo              <- H-53, barato, sin juego
#   bash modelo_base/run_servidor.sh piso        200    <- H-52 + H-53, 4 regimenes
#   bash modelo_base/run_servidor.sh decision    200    <- compuertas + tramo + piso
#
#   bash modelo_base/run_servidor.sh recoger            <- arma el tar de vuelta
#
# El segundo argumento es la frontera (M1 o M3) y el tercero el tamano de la
# muestra en horas. `todo` toma solo el tamano y recorre las dos fronteras.
#
# Se situa solo en la raiz del repositorio: da igual desde donde se invoque.
#
# QUE DECIDE ESTO. La medicion que importa es `competencia`: dice si la forma
# publicada del termino de competencia, que es la unica que reproduce el caso
# del articulo, deja los precios pegados a las cotas con datos reales. Si los
# deja, no sirve, y habria que cambiar un defecto por otro. Ver ADR-0049.
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."          # raiz del repositorio

ACCION="${1:?falta la accion: entorno|compuertas|caso|competencia|eficiencia|todo|techo|escenario|pesovirtual|tanda|tramo|piso|decision|canonica|reparto|juntar|recoger}"

SONDA="reformateo/documento/scripts/sonda"
SALIDAS="$SONDA/salidas"
LOGS="modelo_base/logs"
mkdir -p "$SALIDAS" "$LOGS"

# Interprete: preferir el del entorno virtual si existe, luego python3.
if [[ -x .venv/bin/python ]]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  PY="python"
fi

marca() { date +%Y-%m-%d_%H%M; }

# Nucleos para las sondas paralelas: todos menos dos, para que la maquina
# siga respondiendo y quede holgura para el sistema de ficheros.
#
# DOS TRAMPAS, las dos medidas el 2026-09-07 en el servidor:
#
# 1. `nproc` OBEDECE a OMP_NUM_THREADS. Su manual lo dice: si esa variable
#    esta puesta, fija el minimo que devuelve. Como mas abajo se exporta a
#    uno, y la accion `tanda` vuelve a invocar este guion para cada sonda,
#    en la segunda invocacion `nproc` devolvia 1 y treinta procesos se
#    quedaban en uno. Por eso se cuenta con la variable limpiada para esa
#    llamada concreta.
# 2. Aun asi conviene heredar la cuenta en vez de rehacerla, para que las
#    invocaciones anidadas no puedan discrepar entre si.
if [[ -z "${NUCLEOS:-}" ]]; then
  NUCLEOS="$( { OMP_NUM_THREADS= OMP_THREAD_LIMIT= nproc 2>/dev/null                 || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 8; } )"
fi
if [[ -z "${PROCS:-}" ]]; then
  PROCS=$(( NUCLEOS > 2 ? NUCLEOS - 2 : 1 ))
fi
export NUCLEOS PROCS

# UN hilo por proceso. Las bibliotecas de algebra lineal abren por defecto
# tantos hilos como nucleos vean, y como el trabajo se reparte en tantos
# PROCESOS como nucleos, eso multiplica: con 32 nucleos serian 32 procesos
# por 32 hilos peleando por 32 nucleos. El sistema que se integra tiene del
# orden de treinta y siete estados, demasiado pequeno para que repartirlo
# entre hilos compense siquiera.
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

# Corre una sonda con su log fechado y avisa del codigo de salida. No usa
# tuberias: una tuberia retiene la salida y el log se queda vacio hasta el
# final, que es justo lo que no se quiere en una corrida larga.
corre() {
  local nombre="$1"; shift
  local log="$LOGS/${nombre}_$(marca).log"
  echo "  -> $nombre   (log: $log)"
  local codigo=0
  "$PY" -W ignore "$@" > "$log" 2>&1 || codigo=$?

  # Un codigo de salida cero no basta para dar una compuerta por buena. Si
  # pytest salta todas sus pruebas, porque falta el fichero de referencia,
  # sale con cero y no ha verificado nada. Eso tiene que verse.
  if [[ $codigo -ne 0 ]]; then
    echo "     FALLA (codigo $codigo); mira el log"
  elif grep -qE "^[0-9]+ skipped|= *[0-9]+ skipped" "$log" \
       && ! grep -qE "[0-9]+ passed" "$log"; then
    echo "     NO VERIFICA NADA: todas las pruebas saltaron."
    echo "     Suele faltar Documentos/copy/, que esta gitignorado."
  else
    echo "     ok"
  fi
  tail -n 12 "$log" | sed 's/^/     /'
  return 0
}

case "$ACCION" in

  entorno)
    echo "Montando el entorno"
    if [[ ! -d .venv ]]; then
      python3 -m venv .venv
    fi
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
    echo
    echo "  interprete: $(.venv/bin/python --version)"
    echo "  Comprueba MTE_ROOT antes de medir. La carpeta que el codigo busca"
    echo "  por defecto se llama MedicionesMTE_v3, no MedicionesMTE:"
    echo "    export MTE_ROOT=\$PWD/MedicionesMTE_v3"
    if [[ -d MedicionesMTE_v3 ]]; then
      echo "    -> encontrada aqui, con $(ls MedicionesMTE_v3 | wc -l) ficheros"
    elif [[ -n "${MTE_ROOT:-}" && -d "${MTE_ROOT}" ]]; then
      echo "    -> MTE_ROOT ya apunta a $MTE_ROOT"
    else
      echo "    -> NO la encuentro. Copiala antes de medir."
    fi
    ;;

  compuertas)
    echo "Compuertas, antes de dar por buena ninguna medicion"
    for t in gate_python310 golden_test_sofia gate_cal47_solucionador \
             gate_c138_bienestar_comprador gate_cal46_paso_horario \
             gate_cal49_competencia gate_h45_techo_por_comprador \
             gate_h46_peso_virtual gate_c146_techo_en_el_juego \
             gate_c151_participacion_motor gate_h55_bienestar_precio \
             gate_c156_plazo_por_tarea; do
      corre "$t" "tests/$t.py"
    done
    echo
    echo "  Si alguna falla, PARA. Las mediciones no valen."
    ;;

  caso)
    # No necesita los datos del MTE: el caso publicado trae los suyos.
    echo "El caso publicado, con las tres formas del termino de competencia"
    for forma in aggregate matlab matrix; do
      corre "caso_$forma" "$SONDA/caso_publicado.py" \
            --competencia "$forma" --beta6 100
    done
    ;;

  competencia)
    COB="${2:-M1}"; N="${3:-60}"
    echo "Las dos formas sobre datos reales · $COB · $N horas"
    corre "competencia_${COB}_n${N}" "$SONDA/competencia_real.py" \
          --cobertura "$(echo "$COB" | tr 'A-Z' 'a-z')" --muestra "$N"
    ;;

  eficiencia)
    COB="${2:-M1}"; N="${3:-60}"
    echo "Ahorro capturado frente al alcanzable · $COB · $N horas"
    corre "cotas_${COB}_n${N}" "$SONDA/cotas_excedente.py" \
          --cobertura "$(echo "$COB" | tr 'A-Z' 'a-z')" --muestra "$N"
    corre "eficiencia_${COB}_n${N}" "$SONDA/eficiencia.py" \
          --cobertura "$(echo "$COB" | tr 'A-Z' 'a-z')" --muestra "$N"
    ;;

  todo)
    N="${2:-60}"
    echo "=== Todo, con muestra de $N horas por frontera ==="
    echo
    bash "$0" compuertas
    echo
    bash "$0" caso
    for COB in M1 M3; do
      echo
      bash "$0" eficiencia  "$COB" "$N"
      echo
      bash "$0" competencia "$COB" "$N"
    done
    echo
    echo "=== Hecho. Ahora: bash modelo_base/run_servidor.sh recoger ==="
    ;;

  reparto)
    # Reparte una sonda entre N nucleos. Cada proceso toma una de cada N horas
    # de LA MISMA muestra, de modo que la union es exactamente la muestra
    # entera y no hay que reconciliar nada.
    QUE="${2:?falta la sonda: competencia|eficiencia}"
    COB="${3:-M1}"; N="${4:-60}"; PART="${5:-8}"
    cob=$(echo "$COB" | tr 'A-Z' 'a-z')
    case "$QUE" in
      competencia) GUION="$SONDA/competencia_real.py" ;;
      eficiencia)  GUION="$SONDA/eficiencia.py" ;;
      *) echo "sonda desconocida: $QUE"; exit 2 ;;
    esac
    echo "$QUE · $COB · $N horas repartidas entre $PART procesos"
    for k in $(seq 1 "$PART"); do
      log="$LOGS/${QUE}_${COB}_p${k}de${PART}_$(marca).log"
      nohup "$PY" -W ignore "$GUION" --cobertura "$cob" --muestra "$N" \
            --particion "$k/$PART" > "$log" 2>&1 &
      echo "  lanzado $k/$PART   pid $!   log $log"
    done
    echo
    echo "  Sigue el avance con:  tail -f $LOGS/${QUE}_${COB}_p1de${PART}_*.log"
    echo "  Cuando terminen:      bash $0 juntar"
    ;;

  juntar)
    # Une las tablas parciales en una sola por sonda y frontera.
    "$PY" - <<'PYFIN'
from pathlib import Path
import re, pandas as pd
sal = Path("reformateo/documento/scripts/sonda/salidas")
for base in ("competencia", "eficiencia"):
    for cob in ("m1", "m3"):
        trozos = sorted(sal.glob(f"{base}_{cob}_p*de*.csv"))
        if not trozos:
            continue
        d = pd.concat([pd.read_csv(t) for t in trozos], ignore_index=True)
        col = "k" if "k" in d.columns else d.columns[0]
        orden = [col] + ([ "forma" ] if "forma" in d.columns else [])
        d = d.sort_values(orden).reset_index(drop=True)
        destino = sal / f"{base}_{cob}.csv"
        d.to_csv(destino, index=False)
        print(f"  {destino.name}: {len(trozos)} trozos -> {len(d)} filas")
PYFIN
    echo "  hecho"
    ;;

  escenario)
    # H-47. Tres escenarios de comercializador sobre la misma muestra. NO es
    # el regimen del techo: aqui se sustituye el perfil tarifario entero, de
    # modo que el cambio viaja al piso, al limite economico de generacion, a
    # la clasificacion en papeles y a la liquidacion.
    #
    # LEER LOS DOS NUMEROS. El excedente del mercado y la factura pagada
    # ordenan los escenarios AL REVES: el de mayor excedente es el de peor
    # factura, porque la banda es el cargo de comercializar y el mercado solo
    # lo recupera sobre el lado corto. El bueno es el de menor factura.
    N="${2:-200}"
    echo "Escenario de comercializador · $N horas por frontera · H-47"
    echo "  $NUCLEOS nucleos · $PROCS procesos"
    corre "escenario_n${N}" "$SONDA/escenario_comercializador.py" \
          --muestra "$N" --procesos "$PROCS"
    ;;

  techo)
    # H-45. Cuatro regimenes del limite superior, sobre la misma muestra.
    N="${2:-200}"
    echo "Regimen del techo · $N horas por frontera · H-45"
    echo "  $NUCLEOS nucleos · $PROCS procesos"
    corre "techo_n${N}" "$SONDA/techo_regimen.py" \
          --muestra "$N" --procesos "$PROCS"
    ;;

  pesovirtual)
    # H-46. Las dos formas del peso del jugador virtual. Si el volumen y el
    # excedente no se mueven, la eleccion es de fidelidad al modelo base y no
    # de resultado, y entonces conviene adoptar la del fichero original.
    N="${2:-200}"
    echo "Peso del jugador virtual · $N horas por frontera · H-46"
    echo "  $NUCLEOS nucleos · $PROCS procesos"
    corre "pesovirtual_n${N}" "$SONDA/peso_virtual.py" \
          --muestra "$N" --procesos "$PROCS"
    ;;

  tramo)
    # H-53. Barato y sin resolver el juego: cuanto cambia el tramo de permuta
    # si se cuenta sobre el excedente RESIDUAL, es decir descontando lo que el
    # vendedor coloca DENTRO de la comunidad, que es como el articulo 23 de la
    # Resolucion CREG 101 072 cuenta los excedentes asignables.
    #
    # No hace falta punto fijo: por D-7 el volumen es el lado corto y no
    # depende del precio, de modo que lo colocado dentro se calcula sin jugar.
    #
    # Tarda minutos, no horas. Correr esto ANTES que `piso`.
    echo "Tramo sobre excedente residual, las dos fronteras, H-53"
    corre "tramo_residual" "$SONDA/tramo_residual.py"
    ;;

  piso)
    # H-52 + H-53. LA MEDICION QUE DECIDE. Cuatro regimenes del piso sobre la
    # misma muestra de horas, que la semilla fija:
    #
    #   tramo     la alternativa REAL de cada vendedor segun la CREG 174. Es
    #             lo que el modelo hace hoy.
    #   permuta   todos con el piso de permuta. Contrafactual, para medir.
    #   bolsa     todos con el piso de bolsa. Contrafactual, para medir.
    #   residual  el tramo contado sobre lo que de verdad cruza la frontera.
    #             Es la lectura del articulo 23, y la UNICA de las tres
    #             alternativas que corresponde a algo que la comunidad podria
    #             de verdad hacer.
    #
    # COMO SE LEE, y esto importa mas que la tabla:
    #
    #   FACTURA   manda. Esta en pesos y contiene lo que la red paga por el
    #             excedente exportado, que es lo unico que el regimen cambia.
    #             Se compara en PESOS, nunca en porcentaje por hora: en la
    #             frontera secundaria la base ronda el cero y cambia de signo.
    #   EQUIDAD   el indice de Chacon y el reparto entre las dos partes. Es la
    #             metrica con la que el autor del modelo juzga su propio
    #             trabajo, su Tabla VII, y se mueve con el piso.
    #   bienestar NO arbitra. H-55 lo demuestra: los terminos de pago se
    #             cancelan entre los dos lados y lo unico que le queda del
    #             precio es la penalizacion de competencia, de modo que
    #             prefiere el piso mas bajo POR CONSTRUCCION.
    #   excedente ENGAÑA. Crece cuando la alternativa empeora, no cuando la
    #             comunidad mejora. Ver H-47.
    N="${2:-200}"
    PT="${3:-6}"
    echo "Regimen del piso, $N horas por frontera, 4 regimenes, H-52 y H-53"
    echo "  $NUCLEOS nucleos, $PROCS procesos, plazo por tarea $PT min"
    corre "piso_n${N}" "$SONDA/regimen_piso.py" \
          --muestra "$N" --procesos "$PROCS" --plazo-tarea "$PT"
    echo
    echo "  Tabla emparejada:"
    corre "piso_comparado" "$SONDA/compara_regimenes.py" --muestra "$N"
    ;;

  decision)
    # Todo lo que hace falta para decidir el regimen del piso, en orden.
    N="${2:-200}"
    echo "=== La decision del piso, muestra de $N horas por frontera ==="
    echo
    bash "$0" compuertas
    echo
    bash "$0" tramo
    echo
    bash "$0" piso "$N"
    echo
    echo "=== Hecho. Ahora: bash modelo_base/run_servidor.sh recoger ==="
    ;;

  canonica)
    # La corrida canonica. Acumula CAL-44, CAL-45, CAL-47 y C-143, cada uno
    # de los cuales invalida el canon por su cuenta.
    #
    # Va por la via ALTERNADA a proposito. La acoplada cuesta unos 47 s por
    # hora de mercado y el horizonte son 5.160 horas por frontera: ni con
    # dieciseis nucleos es viable. Ver H-42 y CAL-48.
    #
    # ANTES DE LANZARLA, dos cosas que no se pueden dar por supuestas:
    #   1. las compuertas en verde, TODAS;
    #   2. que MTE_ROOT apunte a las mediciones.
    if [[ -z "${MTE_ROOT:-}" ]]; then
      echo "  MTE_ROOT no esta definido. Exportalo antes:"
      echo "    export MTE_ROOT=/ruta/a/MedicionesMTE"
      exit 2
    fi
    echo "Corrida canonica · las dos fronteras · via alternada"
    echo "  MTE_ROOT = $MTE_ROOT"
    for par in "M1:" "M3:--paper-meters"; do
      COB="${par%%:*}"; EXTRA="${par#*:}"
      DIR="SALIDAS_SERVIDOR/canonica_$(echo "$COB" | tr 'A-Z' 'a-z')"
      mkdir -p "$DIR"
      echo
      echo "  --- $COB  ->  $DIR"
      corre "canonica_${COB}" main_simulation.py \
            --data real --full --analysis --include-c5 --no-regulado \
            --metodo acoplado \
            ${EXTRA:+$EXTRA} --out-dir "$DIR"
    done
    echo
    echo "  Comprueba las dos compuertas del canon antes de citar nada."
    ;;

  tanda)
    # Las tres mediciones nuevas seguidas, que es lo que se subio a medir.
    N="${2:-200}"
    echo "=== Tanda de H-45, H-46 y H-47 · $N horas por frontera ==="
    echo "    $NUCLEOS nucleos · $PROCS procesos · 1 hilo cada uno"
    bash "$0" compuertas
    echo; bash "$0" techo       "$N"
    echo; bash "$0" escenario   "$N"
    echo; bash "$0" pesovirtual "$N"
    echo
    echo "=== Hecho. Ahora: bash modelo_base/run_servidor.sh recoger ==="
    ;;

  recoger)
    DEST="modelo_base/resultados_$(marca).tar.gz"
    VALID="reformateo/documento/validacion_horaria"
    tar czf "$DEST" "$SALIDAS" "$LOGS" \n        $([[ -d "$VALID" ]] && echo "$VALID") \n        $([[ -d SALIDAS_SERVIDOR ]] && echo SALIDAS_SERVIDOR) \n        2>/dev/null || true
    echo "  resultados en $DEST"
    echo "  $(tar tzf "$DEST" | wc -l) ficheros"
    echo
    echo "  Traelo de vuelta y descomprimelo en la raiz del repositorio."
    ;;

  *)
    echo "accion desconocida: $ACCION"; exit 2 ;;
esac
