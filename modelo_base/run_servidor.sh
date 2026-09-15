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
#   bash modelo_base/run_servidor.sh decision   3000    <- TODAS las horas activas
#   PROCS=48 bash modelo_base/run_servidor.sh decision 3000   <- y con mas procesos
#
#   bash modelo_base/run_servidor.sh oficial            <- la corrida oficial, sept.
#
#   --- el subproyecto 2 (2026-09-14): Anexo 4, escalado, H-79 -------------
#   bash modelo_base/run_servidor.sh humo_linux         <- una vez, antes de E5/matriz
#   bash modelo_base/run_servidor.sh sonda79            <- D25, veredicto en E0 y E4
#   bash modelo_base/run_servidor.sh matriz             <- D18/D24/D27, las 13 corridas
#   DESDE=P1 bash modelo_base/run_servidor.sh matriz    <- retoma desde ese caso
#
#   bash modelo_base/run_servidor.sh recoger            <- arma el tar de vuelta
#   bash modelo_base/run_servidor.sh recoger matriz     <- y comprueba lo de matriz
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
#
# MODO EN SECO. Con SECO=1 en el entorno, `corre()` imprime la orden completa
# que correria (interprete, buffer y argumentos) y devuelve cero sin ejecutar
# nada. Es como se comprueban `compuertas`, `humo_linux`, `sonda79` y `matriz`
# sin gastar una sola hora de mercado:
#
#   SECO=1 bash modelo_base/run_servidor.sh matriz
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."          # raiz del repositorio

ACCION="${1:?falta la accion: entorno|compuertas|caso|competencia|eficiencia|todo|techo|escenario|pesovirtual|tanda|tramo|piso|decision|canonica|oficial|humo_linux|sonda79|matriz|reparto|juntar|recoger}"

# Ronda de arreglo 1 (2026-09-14): crea un directorio, o dice que lo haria.
# Misma idea que el modo en seco de corre(), mas abajo, pero para mkdir: con
# SECO=1 no toca el disco. Se define ANTES de la primera creacion de
# directorios (justo abajo) porque esas corren en todas las acciones, no
# solo dentro del case.
crea_dir() {
  if [[ "${SECO:-0}" == "1" ]]; then
    printf '  [SECO] mkdir -p'
    printf ' %q' "$@"
    printf '\n'
    return 0
  fi
  mkdir -p "$@"
}

# Arreglo final (2026-09-14): borra ficheros, o dice que lo haria. Misma regla
# que crea_dir() y corre(): con SECO=1 no se toca el disco.
borra() {
  if [[ "${SECO:-0}" == "1" ]]; then
    printf '  [SECO] rm -f'
    printf ' %q' "$@"
    printf '\n'
    return 0
  fi
  rm -f "$@"
}

SONDA="reformateo/documento/scripts/sonda"
SALIDAS="$SONDA/salidas"
LOGS="modelo_base/logs"
crea_dir "$SALIDAS" "$LOGS"

# Subproyecto 2 (D25): donde `sonda79` escribe los veredictos de H-79 y donde
# `matriz` los lee. Una variable de entorno permite apuntar a otro directorio
# en la comprobacion en seco, sin tocar el de la corrida real.
SONDA_DIR="${SONDA_DIR:-SALIDAS_SERVIDOR/sonda79}"

# Los trece casos de `matriz` (spec 4.11/4.12, D18): caso y sus opciones; E0
# no lleva ninguna. Viven aqui, fuera de la accion, porque `recoger` tambien
# los necesita para saber que almacenes esperar (arreglo final, 2026-09-14).
CASOS_MATRIZ=(
  "E0:"
  "E1:--factor-generacion 3"
  "E2:--factor-generacion 4"
  "E3:--factor-generacion 5.6"
  "E4:--factor-generacion 7"
  "E5:--factor-generacion 10"
  "P1:--factor-demanda 1/7"
  "P2:--factor-generacion 7 --factor-demanda 7"
  "K1:--factor-demanda 2"
  "I1:--escala-agente UCC:neto_cero"
  "N1:--neto-cero"
  "CV2:--factor-cv 2"
  "SINU:--excluir-agente Udenar"
)

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
else
  # El operador la fijo a mano: se respeta, y la accion oficial no la pisa.
  PROCS_PEDIDO=1
  export PROCS_PEDIDO
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

  # Subproyecto 2: modo en seco. Con SECO=1 no se ejecuta nada: se imprime la
  # orden completa (interprete, `-u -W ignore` y argumentos, cada uno citado
  # tal cual se pasaria) y se devuelve cero. Es lo unico que hace falta para
  # comprobar `compuertas`, `humo_linux`, `sonda79` y `matriz` sin gastar una
  # sola hora de mercado.
  if [[ "${SECO:-0}" == "1" ]]; then
    printf '  -> %s   [SECO] %s -u -W ignore' "$nombre" "$PY"
    printf ' %q' "$@"
    printf '\n'
    return 0
  fi

  local log="$LOGS/${nombre}_$(marca).log"
  echo "  -> $nombre   (log: $log)"
  local codigo=0
  # -u: sin bufer (regla principal de CLAUDE.md, H-80). Si se detiene una
  # corrida larga a mitad, el log ya tiene lo que alcanzo a escribir.
  "$PY" -u -W ignore "$@" > "$log" 2>&1 || codigo=$?

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

  # C-171: DEVUELVE EL CODIGO, no cero.
  #
  # Hasta hoy devolvia cero siempre, de modo que la parada en el primer fallo
  # de la corrida oficial **nunca podia dispararse**: se anuncio y no era
  # cierto. La corrida del 9 de septiembre siguio adelante con quince pasos
  # caidos y termino diciendo «completa».
  #
  # Solo PARA cuando quien llama lo pide, poniendo la variable de abajo. Las
  # tandas de sondas siguen queriendo lo contrario: que una sonda que falla no
  # se lleve por delante a las que faltan, porque cada una mide algo distinto y
  # se comparan al final.
  if [[ "${PARA_EN_FALLO:-0}" == "1" && $codigo -ne 0 ]]; then
    echo
    echo "  === DETENIDO EN $nombre ==="
    echo "  El log completo esta en $log"
    return "$codigo"
  fi
  return 0
}

case "$ACCION" in

  entorno)
    echo "Montando el entorno"
    # Ronda de arreglo 1: modo en seco tambien aqui. `python3 -m venv` y
    # `pip install` son escrituras reales fuera de corre(), y esta accion no
    # es de las cuatro del subproyecto 2, pero el principio es el mismo: con
    # SECO=1 no se toca el disco.
    if [[ "${SECO:-0}" == "1" ]]; then
      echo "  [SECO] python3 -m venv .venv   (si no existe)"
      echo "  [SECO] .venv/bin/pip install --upgrade pip"
      echo "  [SECO] .venv/bin/pip install -r requirements.txt"
    else
      if [[ ! -d .venv ]]; then
        python3 -m venv .venv
      fi
      .venv/bin/pip install --upgrade pip
      .venv/bin/pip install -r requirements.txt
    fi
    echo
    if [[ "${SECO:-0}" == "1" ]]; then
      echo "  [SECO] interprete: no se crea .venv en seco, no hay version que mostrar"
    else
      echo "  interprete: $(.venv/bin/python --version)"
    fi
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
             gate_c156_plazo_por_tarea gate_almacen gate_almacen_cruzado \
             gate_cal51_contrato gate_cal52_contrato_interno \
             gate_c164_autoconsumo_autosuficiencia; do
      corre "$t" "tests/$t.py"
    done
    # C-165 con 48 horas, no las 72 de su defecto: con 72 la hora rigida del
    # caso sintetico vence el plazo por hora (H-81, D24). El humo de Linux
    # SI la corre con sus 72 horas, a proposito, para ejercer ese vencimiento.
    corre "gate_c165_desglose_horario" "tests/gate_c165_desglose_horario.py" \
          --horas 48

    echo
    echo "  El motor nuevo del subproyecto 2 (Anexo 4, escalado, H-79)"
    for t in test_anexo4_tramo test_escalado_umbrales test_p2p_residual_art25 \
             test_c4_mensual_norma test_p2p_colectivo test_c5_101099 \
             test_mensual_suma_total test_coincidencia test_c3_costos_mem \
             test_plazo_por_hora test_analisis_ligero test_fa3_cumplimiento \
             test_analysis_numeral2 test_palancas_acoplado \
             test_oraculo_anexo4 test_presupuesto_acoplado test_piso_P; do
      corre "pytest_$t" -m pytest "tests/$t.py" -q
    done
    echo
    echo "  Si alguna falla, PARA. Las mediciones no valen."
    echo "  NUNCA tests/test_full_simulation_preflight.py sin su filtro:"
    echo "  pisa outputs/ y graficas/ de la raiz con una corrida de datos"
    echo "  reales (memoria de pytest, CLAUDE.md)."
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
      # Ronda de arreglo 1: `nohup ... &` con redireccion es una escritura
      # real fuera de corre() (y ademas queda en segundo plano). En seco solo
      # se imprime la orden, sin lanzar nada.
      if [[ "${SECO:-0}" == "1" ]]; then
        printf '  [SECO] nohup %s -W ignore %s --cobertura %s --muestra %s --particion %s/%s > %s 2>&1 &\n' \
               "$PY" "$GUION" "$cob" "$N" "$k" "$PART" "$log"
        continue
      fi
      nohup "$PY" -W ignore "$GUION" --cobertura "$cob" --muestra "$N" \
            --particion "$k/$PART" > "$log" 2>&1 &
      echo "  lanzado $k/$PART   pid $!   log $log"
    done
    echo
    echo "  Sigue el avance con:  tail -f $LOGS/${QUE}_${COB}_p1de${PART}_*.log"
    echo "  Cuando terminen:      bash $0 juntar"
    ;;

  juntar)
    # Ronda de arreglo 1: el heredoc de mas abajo corre Python directo, fuera
    # de corre(), y escribe CSV de verdad (to_csv). En seco solo se dice que
    # se uniria, sin tocar disco.
    if [[ "${SECO:-0}" == "1" ]]; then
      echo "  [SECO] $PY - <<PYFIN   (une competencia_*/eficiencia_* de m1 y m3 en sonda/salidas/)"
    else
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
    fi
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
    # EL PLAZO TOTAL HAY QUE PASARLO. La sonda lo tiene por omision en 45
    # minutos, que era razonable para una muestra de cuarenta horas y absurdo
    # para mil seiscientas tareas: cortaria la medicion por la mitad. Con el
    # plazo POR TAREA haciendo de guardia, el total puede ser generoso.
    N="${2:-200}"
    PT="${3:-6}"
    PTOT="${4:-1440}"
    echo "Regimen del piso, $N horas por frontera, 4 regimenes, H-52 y H-53"
    echo "  $NUCLEOS nucleos, $PROCS procesos"
    echo "  plazo por tarea $PT min · plazo total $PTOT min"
    corre "piso_n${N}" "$SONDA/regimen_piso.py" \
          --muestra "$N" --procesos "$PROCS" \
          --plazo-tarea "$PT" --plazo "$PTOT"
    echo
    echo "  Tabla emparejada:"
    corre "piso_comparado" "$SONDA/compara_regimenes.py" --muestra "$N"
    ;;

  decision)
    # Todo lo que hace falta para decidir el regimen del piso, en orden.
    #
    # PARA USAR LA MAQUINA ENTERA hay dos palancas, y la segunda importa mas:
    #
    #   PROCS=48 bash modelo_base/run_servidor.sh decision 200
    #     sube los procesos. Por omision son los nucleos menos dos.
    #
    #   bash modelo_base/run_servidor.sh decision 3000
    #     mide TODAS las horas activas en vez de una muestra. Son 1.126 en la
    #     frontera principal y 1.811 en la secundaria, es decir 2.937 horas y
    #     11.748 tareas, y con eso desaparece la cautela de que los resultados
    #     son de una muestra. Es lo que de verdad aprovecha un servidor.
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
    # Va por la via ACOPLADA, que desde CAL-48 es la canonica. La objecion de
    # que no era viable venia de ANTES de arreglar la tolerancia del
    # integrador (H-51) y ya no se sostiene: medido aqui, 13,9 s por hora de
    # mercado con 32 procesos, es decir unos 89 minutos las dos fronteras.
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
      crea_dir "$DIR"
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

  oficial)
    # LA CORRIDA OFICIAL DEL SUBPROYECTO 1 (9 de septiembre de 2026). Se deja
    # tal cual, sin tocar: para el subproyecto 2 la reemplaza la accion
    # `matriz`, de mas abajo, que agrega las palancas del acoplado (D35, D26)
    # y las trece corridas de la matriz de escalado (D18) en vez de las dos
    # fronteras M1/M3 (M3 esta retirada, D10).
    #
    # Es la que produce las cifras publicables y, sobre
    # todo, el ALMACEN del que sale cualquier figura de cualquier hora sin
    # volver a simular.
    #
    # AQUI NO SE ENSAYA. En la maquina de trabajo solo se hacen humos de
    # minuto y medio antes de empaquetar; esta accion existe para correrse en
    # el servidor y en ningun otro sitio.
    #
    # Encadena en orden y PARA en el primer fallo, que es lo que distingue una
    # corrida oficial de una tanda de pruebas:
    #
    #   1. las compuertas, todas;
    #   2. la corrida acoplada de las dos fronteras CON EL ALMACEN;
    #   3. la liquidacion por institucion y la equidad por periodo;
    #   4. las figuras del foro, los cuatro grupos;
    #   5. la recogida.
    #
    # Medido aqui: 13,9 s por hora de mercado con 32 procesos, de modo que las
    # dos fronteras del horizonte completo son unos 89 minutos.
    # La parada en el primer fallo, que hasta C-171 se anunciaba y no ocurria.
    set -e
    export PARA_EN_FALLO=1
    if [[ -z "${MTE_ROOT:-}" ]]; then
      echo "  MTE_ROOT no esta definido. Exportalo antes:"
      echo "    export MTE_ROOT=\$PWD/MedicionesMTE_v3"
      exit 2
    fi
    ALM="SALIDAS_SERVIDOR/almacen"
    FIGS="SALIDAS_SERVIDOR/figuras_foro"

    # TODA LA MAQUINA, y no la de las sondas.
    #
    # Para las sondas se reservan dos nucleos, para que el servidor siga
    # respondiendo mientras se mide. La corrida oficial es lo unico que corre y
    # es la que se quiere lo mas corta posible, de modo que toma TODOS los
    # nucleos utiles. Quien quiera dejar holgura la pide: PROCS=30 bash ...
    #
    # UTILES, y no los que la maquina declara. Dentro de un contenedor o con la
    # afinidad restringida los dos numeros difieren, y abrir mas procesos que
    # nucleos utiles no acelera: los hace pelearse.
    if [[ -z "${PROCS_PEDIDO:-}" ]]; then
      PROCS="$NUCLEOS"
      export PROCS
    fi
    UTILES="$("$PY" -c 'import os
try:
    print(len(os.sched_getaffinity(0)))
except AttributeError:
    print(os.cpu_count() or 8)' 2>/dev/null || echo "$NUCLEOS")"

    echo "=== CORRIDA OFICIAL ==="
    echo "    nucleos que la maquina declara : $NUCLEOS"
    echo "    nucleos UTILES (afinidad)      : $UTILES"
    echo "    procesos del mercado           : $PROCS"
    echo "    hilos de algebra por proceso   : $OMP_NUM_THREADS"
    if [[ "$UTILES" -lt "$NUCLEOS" ]]; then
      echo "    AVISO: la afinidad restringe la maquina. El mercado se ajusta"
      echo "           solo a $UTILES y lo dice al arrancar."
    fi
    echo "    MTE_ROOT = $MTE_ROOT"
    echo "    almacen  = $ALM"
    echo "    Para dejar holgura:  PROCS_PEDIDO=1 PROCS=30 bash $0 oficial"
    echo

    echo "--- 1/5 · compuertas"
    bash "$0" compuertas

    echo
    echo "--- 2/5 · la corrida acoplada de las dos fronteras, con almacen"
    for par in "M1:" "M3:--paper-meters"; do
      COB="${par%%:*}"; EXTRA="${par#*:}"
      DIR="SALIDAS_SERVIDOR/oficial_$(echo "$COB" | tr 'A-Z' 'a-z')"
      crea_dir "$DIR"
      echo
      echo "  --- $COB  ->  $DIR"
      corre "oficial_${COB}" main_simulation.py \
            --data real --full --analysis --include-c5 --no-regulado \
            --metodo acoplado --almacen "$ALM" \
            ${EXTRA:+$EXTRA} --out-dir "$DIR"
    done

    echo
    echo "--- 3/5 · la liquidacion por institucion y la equidad por periodo"
    for COB in m1 m3; do
      corre "liquidacion_${COB}" \
            reformateo/documento/scripts/liquidacion.py "$ALM" \
            --cobertura "$COB" --periodo mes
      for P in mes hora_del_dia dia_semana; do
        corre "equidad_${COB}_${P}" analysis/equidad_periodo.py "$ALM" \
              --cobertura "$COB" --periodo "$P"
      done
    done

    echo
    echo "--- 4/5 · las figuras del foro"
    crea_dir "$FIGS"
    for COB in m1 m3; do
      corre "foro_acd_${COB}" reformateo/documento/scripts/gen_foro.py \
            "$ALM" --cobertura "$COB" --figuras "$FIGS"
      corre "foro_b_${COB}" reformateo/documento/scripts/gen_foro_b.py \
            --cobertura "$COB" --figuras "$FIGS"
    done

    echo
    echo "--- 5/5 · la recogida"
    bash "$0" recoger oficial
    echo
    echo "=== CORRIDA OFICIAL COMPLETA ==="
    echo "  Comprueba las dos compuertas del canon antes de citar nada."
    ;;

  humo_linux)
    # NUEVA del subproyecto 2 (tarea 18). Se corre UNA vez en el servidor,
    # antes de E5 y antes de `matriz`: verifica el arranque del pool por
    # `fork` (que es el de Linux), un vencimiento real del plazo por hora, un
    # dia completo de E5, y (arreglo final) ese mismo dia con las dos
    # palancas del acoplado encendidas.
    echo "Humo de Linux, antes de E5 y de matriz (subproyecto 2)"

    echo
    echo "  1/4 · test_plazo_por_hora bajo el arranque de Linux"
    echo "  core/ems_p2p.py abre el pool con multiprocessing.get_context()"
    echo "  SIN argumento, es decir el metodo de la plataforma; en Linux ya"
    echo "  es 'fork', que es el que nunca se ha probado (el arreglo del hilo"
    echo "  del pool viejo, tarea 18). No hace falta forzarlo con ninguna"
    echo "  variable: basta con correr esto aqui, que ya es Linux."
    corre "pytest_test_plazo_por_hora" -m pytest \
          "tests/test_plazo_por_hora.py" -q

    echo
    echo "  2/4 · C-165 con sus 72 horas de defecto (no las 48 de la compuerta)"
    echo "  ejerce un vencimiento real del plazo por hora y la renovacion del"
    echo "  pool: la hora 56 del caso sintetico, H-81. Su resumen [D24] debe"
    echo "  verse en el registro de esta corrida."
    corre "gate_c165_desglose_horario_72h" "tests/gate_c165_desglose_horario.py"

    echo
    echo "  3/4 · un dia de E5 (factor de generacion 10)"
    DIR="SALIDAS_SERVIDOR/humo_linux_e5"
    crea_dir "$DIR"
    corre "humo_linux_e5" main_simulation.py \
          --data real --full --desde 2025-07-15 --hasta 2025-07-16 \
          --factor-generacion 10 --include-c5 --no-regulado \
          --metodo acoplado --analisis-ligero --plazo-hora 15 \
          --out-dir "$DIR"

    echo
    echo "  4/4 · el mismo dia de E5 con las dos palancas del acoplado"
    echo "  (--rtol-acoplado 1e-7 --horizonte-max-acoplado 0.4), para ver en su"
    echo "  registro las lineas [D24], [D37], [D26] y [D38] antes de las trece corridas."
    echo "  Es un humo: si sale con 3 (D38) se imprime, pero no detiene nada."
    DIR="SALIDAS_SERVIDOR/humo_linux_e5_palancas"
    crea_dir "$DIR"
    # Con PARA_EN_FALLO=0, corre() devuelve siempre cero: no hay codigo que
    # recoger aqui, y el propio corre() ya imprime «FALLA (codigo N)» si la
    # corrida no salio con cero. El humo no se detiene.
    PARA_EN_FALLO=0 corre "humo_linux_e5_palancas" main_simulation.py \
          --data real --full --desde 2025-07-15 --hasta 2025-07-16 \
          --factor-generacion 10 --include-c5 --no-regulado \
          --metodo acoplado --analisis-ligero --plazo-hora 15 \
          --rtol-acoplado 1e-7 --horizonte-max-acoplado 0.4 \
          --out-dir "$DIR"
    echo "     Si el paso 4 dijo FALLA (codigo 3), es D38: su linea [D38] dice por que."

    echo
    echo "  Si las cuatro pasan, sigue con:  bash $0 sonda79"
    ;;

  sonda79)
    # NUEVA del subproyecto 2 (D25). La sonda de H-79 en E0 y E4: si el
    # reparto o el excedente dependen del integrador, y con que palanca se
    # corrige antes de `matriz`. El codigo de salida 2 de la sonda es un
    # VEREDICTO, no un fallo: PARA_EN_FALLO no se pone aqui, de modo que
    # corre() siempre devuelve cero y esta accion sigue aunque salte un
    # criterio.
    echo "Sonda de H-79: depende el reparto del integrador, en E0 y E4 (D25)"
    crea_dir "$SONDA_DIR"
    FALTAN=()
    for par in "E0:1" "E4:7"; do
      CASO="${par%%:*}"; FACTOR="${par#*:}"
      echo
      echo "  --- $CASO (factor de generacion $FACTOR)"
      # Arreglo final: el veredicto viejo se borra ANTES de correr la sonda.
      # Si no, una sonda que falla sin escribir dejaria el JSON de la vez
      # anterior, la comprobacion de abajo lo daria por nuevo y `matriz`
      # fijaria las palancas con un veredicto que no es de este codigo.
      borra "$SONDA_DIR/veredicto_${CASO}.json"
      corre "sonda79_${CASO}" "$SONDA/reparto_vs_integrador.py" \
            --horas 20 --factor-generacion "$FACTOR" \
            --salida "$SONDA_DIR/sonda79_${CASO}.csv" \
            --veredicto-json "$SONDA_DIR/veredicto_${CASO}.json"
      # Ronda de arreglo 1: el codigo 2 de la sonda es un veredicto, no un
      # fallo, y no detiene esta accion. Pero si la sonda no llega a ESCRIBIR
      # el JSON (su codigo 1, sin datos; o cualquier otro fallo), `matriz` no
      # tendria de donde leer la palanca. En seco nunca se escribe nada
      # (corre() no ejecuta), de modo que esta comprobacion se salta.
      if [[ "${SECO:-0}" != "1" && ! -f "$SONDA_DIR/veredicto_${CASO}.json" ]]; then
        FALTAN+=("$CASO")
      fi
    done
    echo
    if [[ ${#FALTAN[@]} -gt 0 ]]; then
      echo "  FALTA el veredicto de: ${FALTAN[*]} (mira su log: sin datos u otro fallo)"
      echo "  Los que si quedaron estan en $SONDA_DIR/veredicto_<CASO>.json."
      exit 1
    fi
    echo "  Veredictos en $SONDA_DIR/veredicto_E0.json y .../veredicto_E4.json."
    echo "  Mira que palanca activo cada uno; despues:  bash $0 matriz"
    ;;

  matriz)
    # NUEVA del subproyecto 2 (D18, D24, D27). Reemplaza a `oficial` para
    # esta tanda: las trece corridas de la matriz de escalado, con el plazo
    # por hora (D24), el modo ligero (D27) y las palancas del acoplado que
    # decidio `sonda79` (D35, D26). Solo M1: M3 esta retirada (D10).
    set -e
    export PARA_EN_FALLO=1
    if [[ -z "${MTE_ROOT:-}" ]]; then
      echo "  MTE_ROOT no esta definido. Exportalo antes:"
      echo "    export MTE_ROOT=\$PWD/MedicionesMTE_v3"
      exit 2
    fi

    echo "=== MATRIZ DEL SUBPROYECTO 2 · las trece corridas ==="
    echo "    MTE_ROOT   = $MTE_ROOT"
    echo "    veredictos = $SONDA_DIR"
    echo

    echo "--- 1/6 · compuertas"
    bash "$0" compuertas

    echo
    echo "--- 2/6 · los veredictos de la sonda de H-79 y las palancas"
    V0="$SONDA_DIR/veredicto_E0.json"
    V4="$SONDA_DIR/veredicto_E4.json"
    FALTAN=()
    [[ -f "$V0" ]] || FALTAN+=("$V0")
    [[ -f "$V4" ]] || FALTAN+=("$V4")
    if [[ ${#FALTAN[@]} -gt 0 ]]; then
      echo "  Falta el veredicto de la sonda de H-79:"
      for f in "${FALTAN[@]}"; do
        echo "    $f"
      done
      echo "  Corre primero:  bash $0 sonda79"
      exit 2
    fi
    # Union de las palancas de los dos veredictos (resolucion del brief).
    PALANCAS="$("$PY" -c '
import json, sys
palancas = set()
for ruta in sys.argv[1:]:
    with open(ruta, encoding="utf-8") as f:
        v = json.load(f)
    palancas.update(v.get("palanca", []))
print(" ".join(sorted(palancas)))
' "$V0" "$V4")"
    PALANCAS_ARGS=""
    if [[ " $PALANCAS " == *" tolerancia "* ]]; then
      PALANCAS_ARGS="$PALANCAS_ARGS --rtol-acoplado 1e-7"
      echo "  palanca activada: tolerancia -> --rtol-acoplado 1e-7 (D35)"
    fi
    if [[ " $PALANCAS " == *" horizonte "* ]]; then
      PALANCAS_ARGS="$PALANCAS_ARGS --horizonte-max-acoplado 0.4"
      echo "  palanca activada: horizonte -> --horizonte-max-acoplado 0.4 (D26)"
    fi
    if [[ -z "$PALANCAS_ARGS" ]]; then
      echo "  ninguna palanca: los dos veredictos de la sonda salieron limpios"
    fi

    echo
    echo "--- 3/6 · las trece corridas completas"
    # Caso : opciones (spec 4.11/4.12, D18), definidos arriba en CASOS_MATRIZ
    # porque `recoger` tambien los usa.
    CASOS=("${CASOS_MATRIZ[@]}")
    SALTAR="${DESDE:-}"
    for par in "${CASOS[@]}"; do
      CASO="${par%%:*}"; EXTRA="${par#*:}"
      if [[ -n "$SALTAR" ]]; then
        if [[ "$CASO" == "$SALTAR" ]]; then
          SALTAR=""
        else
          echo "  ... salta $CASO (DESDE=$DESDE)"
          continue
        fi
      fi
      DIR="SALIDAS_SERVIDOR/matriz/$CASO"
      ALM="$DIR/almacen"
      crea_dir "$ALM"
      echo
      echo "  --- $CASO  ->  $DIR"
      # D38: la corrida sale con 3, DESPUES de escribir todo, si hubo alguna
      # hora con excepcion o si las vencidas mas las sin exito del integrador
      # pasan del 1 % (D44). PARA_EN_FALLO la detiene como a cualquier fallo;
      # aqui se dice que mirar y como seguir.
      corre "matriz_${CASO}" main_simulation.py \
            --data real --full --include-c5 --no-regulado \
            --metodo acoplado --analisis-ligero --plazo-hora 15 \
            --almacen "$ALM" \
            ${PALANCAS_ARGS:+$PALANCAS_ARGS} ${EXTRA:+$EXTRA} \
            --out-dir "$DIR" || {
        cod=$?
        echo
        if [[ $cod -eq 3 ]]; then
          echo "  $CASO salio con codigo 3 (D38): hubo alguna hora con excepcion,"
          echo "  o las horas vencidas por el plazo mas las sin exito del"
          echo "  integrador pasan del 1 % de las horas de mercado (D44). Sus"
          echo "  salidas estan escritas, pero la cadena no sigue con un caso asi."
        else
          echo "  $CASO salio con codigo $cod."
        fi
        echo "  Mira las lineas [D24], [D37], [C-190] y [D38] de su registro"
        echo "  ($LOGS/matriz_${CASO}_<fecha>.log) y retoma desde este caso con:"
        echo "    DESDE=$CASO bash $0 matriz"
        exit "$cod"
      }
    done

    echo
    echo "--- 4/6 · la liquidacion y la equidad de cada caso (cobertura m1)"
    for par in "${CASOS[@]}"; do
      CASO="${par%%:*}"
      ALM="SALIDAS_SERVIDOR/matriz/$CASO/almacen"
      corre "matriz_liquidacion_${CASO}" \
            reformateo/documento/scripts/liquidacion.py "$ALM" \
            --cobertura m1 --periodo mes
      for P in mes hora_del_dia dia_semana; do
        corre "matriz_equidad_${CASO}_${P}" analysis/equidad_periodo.py \
              "$ALM" --cobertura m1 --periodo "$P"
      done
    done

    echo
    echo "--- 5/6 · las figuras del foro, solo de E0"
    FIGS="SALIDAS_SERVIDOR/matriz/figuras_foro"
    crea_dir "$FIGS"
    corre "matriz_foro_acd_E0" reformateo/documento/scripts/gen_foro.py \
          "SALIDAS_SERVIDOR/matriz/E0/almacen" --cobertura m1 --figuras "$FIGS"
    corre "matriz_foro_b_E0" reformateo/documento/scripts/gen_foro_b.py \
          --cobertura m1 --figuras "$FIGS"

    echo
    echo "--- 6/6 · la recogida"
    bash "$0" recoger matriz
    echo
    echo "=== MATRIZ COMPLETA ==="
    echo "  Un caso que falla detiene la cadena (es la corrida oficial);"
    echo "  se retoma desde ese caso con:  DESDE=<caso> bash $0 matriz"
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
    # Se arma la lista ANTES, y se comprueba. La version anterior llevaba
    # una barra con ene literal donde debia ir una continuacion de linea, de
    # modo que tar recibia tres argumentos llamados «n» que no existen: con
    # el error escondido y el «|| true» al final, la recogida salia bien
    # aunque faltara una carpeta entera. Ver C-158.
    QUE=("$SALIDAS" "$LOGS")
    [[ -d "$VALID" ]] && QUE+=("$VALID")
    # SALIDAS_SERVIDOR ya contiene el almacen y las figuras del foro, porque la
    # corrida oficial los escribe dentro. No hay que nombrarlos aparte, pero si
    # comprobar que estan: un almacen ausente pasaria desapercibido hasta que
    # alguien intentara dibujar una figura de vuelta en casa, y para entonces
    # la maquina que lo produjo ya no tiene el dato.
    [[ -d SALIDAS_SERVIDOR ]] && QUE+=(SALIDAS_SERVIDOR)

    # Arreglo final: lo que se espera depende de la corrida que se recoge.
    # `oficial` escribe SALIDAS_SERVIDOR/almacen y .../figuras_foro; `matriz`
    # un almacen por caso en SALIDAS_SERVIDOR/matriz/<caso>/almacen y las
    # figuras de E0 en SALIDAS_SERVIDOR/matriz/figuras_foro. Cada una llama a
    # esta accion con su nombre; sin nombre se deduce: si hay
    # SALIDAS_SERVIDOR/matriz, la matriz. Van dentro de SALIDAS_SERVIDOR, que
    # entra entero en el tar; aqui se comprueba que existen antes, y que
    # quedaron en el tar despues.
    DE="${2:-}"
    if [[ -z "$DE" ]]; then
      if [[ -d SALIDAS_SERVIDOR/matriz ]]; then DE="matriz"; else DE="oficial"; fi
    fi
    ESPERADOS=()
    case "$DE" in
      matriz)
        for par in "${CASOS_MATRIZ[@]}"; do
          ESPERADOS+=("SALIDAS_SERVIDOR/matriz/${par%%:*}/almacen")
        done
        ESPERADOS+=("SALIDAS_SERVIDOR/matriz/figuras_foro")
        ;;
      oficial)
        ESPERADOS=(SALIDAS_SERVIDOR/almacen SALIDAS_SERVIDOR/figuras_foro)
        ;;
      *)
        echo "  recoger: corrida desconocida '$DE'; use matriz u oficial"
        exit 2
        ;;
    esac
    echo "  recogiendo la corrida: $DE"
    for esperado in "${ESPERADOS[@]}"; do
      if [[ -d "$esperado" ]]; then
        echo "    esta: $esperado"
      else
        echo "  AVISO: no esta $esperado"
      fi
    done
    echo "  recogiendo: ${QUE[*]}"
    for d in "${QUE[@]}"; do
      [[ -d "$d" ]] || { echo "  AVISO: falta $d"; }
    done

    # Subproyecto 2: modo en seco. `matriz` encadena esta accion como su
    # ultimo paso (6/6), y sin esta guarda una comprobacion con `SECO=1`
    # empaquetaba de verdad todo SALIDAS_SERVIDOR: se detecto armando esta
    # misma tarea, un tar.gz de 65 MB con 2827 ficheros reales.
    if [[ "${SECO:-0}" == "1" ]]; then
      echo "  [SECO] tar czf $DEST ${QUE[*]}"
      exit 0
    fi

    tar czf "$DEST" "${QUE[@]}"
    echo "  resultados en $DEST"
    LISTA="$(tar tzf "$DEST")"
    # Sin tuberias: con `set -o pipefail`, `grep -q` cierra la tuberia al
    # primer acierto, el que escribe muere por SIGPIPE (141) si la lista pasa
    # del bufer, y el `!` convertiria eso en un aviso falso (re-revision).
    echo "  $(wc -l <<<"$LISTA") ficheros"
    # Lo que estaba en disco tiene que haber llegado al tar.
    for esperado in "${ESPERADOS[@]}"; do
      [[ -d "$esperado" ]] || continue
      if ! grep -q "^${esperado}/" <<<"$LISTA"; then
        echo "  AVISO: $esperado esta en disco pero NO en el tar"
      fi
    done
    echo
    echo "  Traelo de vuelta y descomprimelo en la raiz del repositorio."
    ;;

  *)
    echo "accion desconocida: $ACCION"; exit 2 ;;
esac
