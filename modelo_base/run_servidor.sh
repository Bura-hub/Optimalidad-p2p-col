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
#   PROCS=8 bash modelo_base/run_servidor.sh decision 3000    <- con menos procesos (nunca mas de 16: el servidor es compartido)
#
#   bash modelo_base/run_servidor.sh oficial            <- la corrida oficial, sept.
#
#   --- el subproyecto 2 (2026-09-14): Anexo 4, escalado, H-79 -------------
#   bash modelo_base/run_servidor.sh humo_linux         <- una vez, antes de E5/matriz
#   bash modelo_base/run_servidor.sh sonda79            <- D25, veredicto en E0 y E4
#   bash modelo_base/run_servidor.sh matriz             <- D18/D24/D27, las 13 corridas
#   DESDE=P1 bash modelo_base/run_servidor.sh matriz    <- retoma desde ese caso
#
#   --- el arranque del acoplado (2026-09-15): H-85, D45 y D46 -------------
#   bash modelo_base/run_servidor.sh arranque           <- E0 y E4, una semana, los dos arranques
#
#   --- la convergencia del reparto (2026-09-16): H-86, D47 ----------------
#   bash modelo_base/run_servidor.sh convergencia       <- E0 y K1, una semana, tres criterios
#
#   --- el reposo del juego regularizado (2026-09-17): D48 a D69, M-F -----
#   bash modelo_base/run_servidor.sh matriz_reposo      <- las 13 corridas por reposo, cada una con su compuerta de salida
#   DESDE=P1 bash modelo_base/run_servidor.sh matriz_reposo   <- retoma desde ese caso
#   bash modelo_base/run_servidor.sh barrido_sigma      <- las 13 con sigma 0, 0,5 y 1 (despues de matriz_reposo)
#   SIGMAS="0.5 1" DESDE=P1 bash modelo_base/run_servidor.sh barrido_sigma   <- retoma
#
#   --- la validacion del reposo (2026-09-17): M-A a M-G -------------------
#   bash modelo_base/run_servidor.sh validacion_reposo  <- decide si cada regimen se publica como reposo verificado o como regla declarada
#   LENTAS=0 bash modelo_base/run_servidor.sh validacion_reposo   <- sin las dos horas lentas de la compuerta de la dinamica
#   TOPE_GLOBAL_S=86400 bash modelo_base/run_servidor.sh validacion_reposo   <- tope global de 24 h (defecto 12 h)
#   ETAPA2=1 TOPE_874=<s> TOPE_4766=<s> bash modelo_base/run_servidor.sh validacion_reposo   <- y con la compuerta entera
#
#   bash modelo_base/run_servidor.sh recoger            <- arma el tar de vuelta
#   bash modelo_base/run_servidor.sh recoger matriz     <- y comprueba lo de matriz
#   bash modelo_base/run_servidor.sh recoger arranque   <- y comprueba lo de arranque
#   bash modelo_base/run_servidor.sh recoger convergencia  <- y lo de convergencia
#   bash modelo_base/run_servidor.sh recoger matriz_reposo <- y lo de matriz_reposo
#   bash modelo_base/run_servidor.sh recoger barrido_sigma <- y lo del barrido
#   bash modelo_base/run_servidor.sh recoger validacion_reposo <- y lo de la validacion
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

# CONTENCION (incidente del 2026-09-18). EL SERVIDOR ES COMPARTIDO con la
# plataforma MTE en produccion: la web, los servicios de los puertos 3500 y
# 3600, PostgreSQL y la red de Fabric. La validacion del reposo, con 30
# procesos (nucleos - 2), la dejo sin CPU de 10:37 a 14:14: carga de hasta 417,
# la web y el SSH sin responder, y el patron «vuelve cada hora unos minutos»
# eran los huecos entre una medicion y la siguiente.
#
# Desde entonces TODA accion se vuelve a lanzar a si misma, antes de hacer nada,
# encerrada en la mitad alta de los nucleos (taskset, un tope duro: la mitad
# baja queda siempre para la plataforma), con la prioridad minima de CPU
# (nice 19) y de disco (ionice, clase ociosa). Los hijos lo heredan, y como
# NUCLEOS se cuenta despues con la afinidad ya puesta, los procesos del mercado
# se ajustan solos al tramo.
#
#   CONTENCION=0          la desactiva (solo con la plataforma parada o avisada)
#   NUCLEOS_TESIS=24-31   otro tramo de nucleos
#   MEMORIA_TESIS=16G     el tope duro de memoria del arbol (tarea 4f), con
#                         systemd-run --user --scope; corre_mediciones abre
#                         como mucho MEMORIA_TESIS / 1,5 GB procesos
#
# Si el operador ya la lanzo con la afinidad restringida, se respeta: solo se
# restringe cuando el proceso ve la maquina entera. Solo en Linux; en seco
# tambien se aplica, que es como se comprueba. Subir el nice no se deshace sin
# sudo; la afinidad la puede ensanchar el dueno: taskset -a -p -c 0-31 <pid>.
if [[ "${CONTENCION:-1}" == "1" && -z "${CONTENIDO:-}" \
      && "$(uname -s 2>/dev/null)" == "Linux" ]]; then
  export CONTENIDO=1
  # Y si alguna vez falta memoria, que el nucleo mate PRIMERO a la tesis y no a
  # PostgreSQL ni a la plataforma: subir el oom_score_adj propio no pide sudo,
  # se hereda por fork y exec, y corre_mediciones sobrevive a un trabajador
  # muerto. taskset limita la CPU, no la memoria; esto cubre ese hueco.
  { echo 500 > /proc/self/oom_score_adj; } 2>/dev/null || true
  _todos="$(nproc --all 2>/dev/null || echo 0)"
  _visibles="$(OMP_NUM_THREADS= OMP_THREAD_LIMIT= nproc 2>/dev/null || echo 0)"
  _previo=()
  # Tarea 4f: un TOPE DURO de memoria para todo el arbol. El relanzamiento del
  # 2026-09-18 (ec6ac35) se comio la RAM y arrastro a servicios de la
  # plataforma: oom_score_adj elige a quien mata el nucleo, pero no pone techo.
  # Con un scope de systemd de usuario (sin sudo) el arbol entero queda en un
  # cgroup con MemoryMax, sin swap, y si se pasa el nucleo mata DENTRO de el
  # (un trabajador, que corre_mediciones sobrevive), no a la plataforma. Se
  # comprueba antes con las mismas propiedades y una orden inocua; si no
  # funciona, se sigue sin el y se avisa. MEMORIA_TESIS cambia el tope (16G).
  #
  # Dos trampas del scope (revision de 4f), las dos capaces de matar la noche:
  #  - OOMPolicy: desde systemd 253 un scope que no es de sesion toma
  #    DefaultOOMPolicy=stop, y un solo trabajador muerto por MemoryMax para
  #    el scope ENTERO. Se pide OOMPolicy=continue; si ese systemd no conoce la
  #    propiedad (anterior a 253, donde los scopes no la aplican), se prueba
  #    sin ella antes de rendirse.
  #  - linger: el scope vive en el gestor de usuario, que logind para al
  #    cerrarse la ULTIMA sesion del usuario si no tiene linger. Con «nohup ...
  #    &» y salir de SSH, la noche moriria al desconectar. Sin linger, solo se
  #    acepta dentro de tmux o screen (la sesion sigue abierta); si no, se para
  #    aqui en voz alta (en seco solo se avisa). SIN_LINGER_OK=1 lo fuerza.
  _mem=(-p "MemoryMax=${MEMORIA_TESIS:-16G}" -p MemorySwapMax=0)
  _scope=()
  if command -v systemd-run >/dev/null 2>&1; then
    if systemd-run --user --scope -q "${_mem[@]}" -p OOMPolicy=continue \
         true >/dev/null 2>&1; then
      _scope=(systemd-run --user --scope -q "${_mem[@]}" -p OOMPolicy=continue)
    elif systemd-run --user --scope -q "${_mem[@]}" true >/dev/null 2>&1; then
      _scope=(systemd-run --user --scope -q "${_mem[@]}")
    fi
  fi
  if [[ ${#_scope[@]} -gt 0 ]]; then
    export MEMORIA_TESIS="${MEMORIA_TESIS:-16G}"
    _linger="$(loginctl show-user "$(id -un)" -p Linger --value 2>/dev/null \
               || echo desconocido)"
    if [[ "$_linger" != "yes" && -z "${TMUX:-}" && -z "${STY:-}" ]]; then
      echo "[contencion] AVISO: el usuario no tiene linger (Linger=$_linger) y" \
           "esto no corre dentro de tmux ni screen: el scope de memoria MORIRIA" \
           "al cerrar la sesion SSH. Lanzalo dentro de tmux (tmux new -s tesis)" \
           "y deja tmux vivo, o con SIN_LINGER_OK=1 si la sesion no se cierra." >&2
      if [[ "${SECO:-0}" != "1" && "${SIN_LINGER_OK:-0}" != "1" ]]; then
        exit 2
      fi
    fi
    _previo+=("${_scope[@]}")
  else
    echo "[contencion] AVISO: systemd-run --user --scope no funciona aqui: SIN" \
         "tope duro de memoria (quedan oom_score_adj y el tope por proceso de" \
         "corre_mediciones)" >&2
  fi
  if [[ "$_todos" -ge 4 && "$_visibles" -eq "$_todos" ]] \
      && command -v taskset >/dev/null 2>&1; then
    _previo+=(taskset -c "${NUCLEOS_TESIS:-$(( _todos / 2 ))-$(( _todos - 1 ))}")
  fi
  command -v nice >/dev/null 2>&1 && _previo+=(nice -n 19)
  command -v ionice >/dev/null 2>&1 && _previo+=(ionice -c 3 -t)
  if [[ ${#_previo[@]} -gt 0 ]]; then
    echo "[contencion] ${_previo[*]} (el servidor es compartido con la" \
         "plataforma MTE; CONTENCION=0 la quita)" >&2
    exec "${_previo[@]}" bash "${BASH_SOURCE[0]}" "$@"
  fi
fi

cd "$(dirname "${BASH_SOURCE[0]}")/.."          # raiz del repositorio

ACCION="${1:?falta la accion: entorno|compuertas|caso|competencia|eficiencia|todo|techo|escenario|pesovirtual|tanda|tramo|piso|decision|canonica|oficial|humo_linux|sonda79|matriz|arranque|convergencia|matriz_reposo|barrido_sigma|validacion_reposo|reparto|juntar|recoger}"

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

# H-85, D45 y D46 (2026-09-15): los dos casos de la accion `arranque`, cada
# uno corrido con los dos arranques del acoplado. Viven aqui por la misma
# razon que CASOS_MATRIZ: `recoger` los necesita para saber que esperar.
CASOS_ARRANQUE=(
  "E0:"
  "E4:--factor-generacion 7"
)
REGLAS_ARRANQUE=(iguales factible)

# H-86, D47 (2026-09-16): la campana de convergencia. Los dos casos, cada uno
# con las tres configuraciones del criterio de parada. Viven aqui por la misma
# razon que los de arriba: `recoger` los necesita para saber que esperar.
#
# K1 (--factor-demanda 2) es el caso de la matriz con MENOS horas estacionarias,
# el 33 %, frente al 68 % del conjunto: es donde el criterio de parada se ve
# mas, y por eso acompana a E0.
CASOS_CONVERGENCIA=(
  "E0:"
  "K1:--factor-demanda 2"
)
# «hoy» lleva el presupuesto y el plazo de la matriz (el presupuesto es la
# constante del motor, que no se pasa). Las dos del criterio nuevo aflojan los
# dos topes a proposito: la campana existe PARA VER EL COSTO, no para acotarlo,
# y una hora que hoy se corta por presupuesto es justo la que hay que medir.
CONFIGS_CONVERGENCIA=(
  "hoy:--criterio-estacionario precio --horizonte-max-acoplado 0.4 --plazo-hora 15"
  "reparto04:--criterio-estacionario precio_y_reparto --horizonte-max-acoplado 0.4 --plazo-hora 60 --presupuesto-eval-acoplado 100000000"
  "reparto20:--criterio-estacionario precio_y_reparto --horizonte-max-acoplado 2.0 --plazo-hora 60 --presupuesto-eval-acoplado 100000000"
)
# Las comparaciones de repartos que se hacen al final, «A:B» por caso.
PARES_CONVERGENCIA=("hoy:reparto20" "reparto04:reparto20")

# D48 a D69 (2026-09-17): donde escriben `matriz_reposo` y `barrido_sigma`, y
# las sigmas del barrido del presupuesto de precios (D50). Viven aqui por la
# misma razon que los de arriba: `recoger` los necesita para saber que esperar.
# La matriz vieja (acoplado, 15 de septiembre) sigue en SALIDAS_SERVIDOR/matriz
# y no se pisa (D57).
MATRIZ_REPOSO="SALIDAS_SERVIDOR/matriz_reposo"
MATRIZ_VIEJA="SALIDAS_SERVIDOR/matriz"
# SIGMAS acota el barrido; la sigma base, (I-1)/I, es la de `matriz_reposo`.
SIGMAS_BARRIDO="${SIGMAS:-0 0.5 1}"

# La etiqueta de una sigma en el nombre de la carpeta: 0 -> 0, 0.5 -> 05, 1 -> 1.
etiqueta_sigma() {
  printf '%s' "${1//./}"
}

# Fallar en voz alta si SIGMAS trae algo que no es una de las tres sigmas del
# barrido, escrita en su forma canonica. El motor rechaza lo que no es un
# numero en [0, 1], pero despues de cargar los datos; y una forma no canonica,
# como 1.0 o 0.50, daria otra carpeta (_sigma10, _sigma050) que `recoger` y la
# comparacion no buscan (revision de 4b, menor 2).
valida_sigmas() {
  local s
  for s in $SIGMAS_BARRIDO; do
    case "$s" in
      0|0.5|1) ;;
      *)
        echo "  SIGMAS: '$s' no vale; las sigmas del barrido se escriben 0, 0.5 o 1"
        exit 2
        ;;
    esac
  done
  return 0
}

# Fallar en voz alta, ANTES de las compuertas, si DESDE no es ninguno de los
# trece casos: si no, la cadena saltaria todos en silencio despues de gastar las
# compuertas.
valida_desde() {
  local par
  [[ -z "${DESDE:-}" ]] && return 0
  for par in "${CASOS_MATRIZ[@]}"; do
    [[ "${par%%:*}" == "$DESDE" ]] && return 0
  done
  echo "  DESDE=$DESDE no es ninguno de los trece casos de la matriz"
  exit 2
}

# Los casos de la matriz que tienen almacen de la matriz vieja, en VIEJOS. Solo
# lee el disco.
casos_con_matriz_vieja() {
  VIEJOS=()
  local par
  for par in "${CASOS_MATRIZ[@]}"; do
    if [[ -d "$MATRIZ_VIEJA/${par%%:*}/almacen" ]]; then
      VIEJOS+=("${par%%:*}")
    fi
  done
  return 0
}

# El registro mas reciente que corre() dejo con ese nombre. corre() le pone la
# fecha al nombre, de modo que `recoger` no puede esperar una ruta fija: la
# busca, y si no hay ninguno devuelve la ruta con «<fecha>», que no existe y
# sale como ausente.
ultimo_registro() {
  local hallados=()
  shopt -s nullglob
  hallados=("$LOGS/${1}_"[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]_[0-9][0-9][0-9][0-9].log)
  shopt -u nullglob
  if [[ ${#hallados[@]} -gt 0 ]]; then
    printf '%s' "${hallados[${#hallados[@]}-1]}"
  else
    printf '%s' "$LOGS/${1}_<fecha>.log"
  fi
}

# Interprete: preferir el del entorno virtual si existe, luego python3.
if [[ -x .venv/bin/python ]]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  PY="python"
fi

marca() { date +%Y-%m-%d_%H%M; }

# Nucleos para las sondas paralelas. Hasta el 2026-09-18 eran todos menos dos;
# desde entonces, como mucho la mitad (PROCS_MAX, mas abajo): el servidor es
# compartido con la plataforma MTE, que es produccion.
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
# PROCS_MAX (regla del servidor compartido, 2026-09-18): COMO MUCHO LA MITAD de
# los nucleos de la maquina (16 en bunnygirl), y nunca mas que los del tramo
# de la contencion. Antes era «todos menos dos», y con 30 procesos de ~1 GB la
# plataforma MTE, que es produccion, se quedo sin CPU ni memoria.
_todos_nucleos="$(nproc --all 2>/dev/null || echo "$NUCLEOS")"
PROCS_MAX=$(( _todos_nucleos / 2 > 0 ? _todos_nucleos / 2 : 1 ))
if [[ "$NUCLEOS" -lt "$PROCS_MAX" ]]; then
  PROCS_MAX="$NUCLEOS"
fi
if [[ -z "${PROCS:-}" ]]; then
  PROCS="$PROCS_MAX"
else
  # El operador la fijo a mano: se respeta por debajo del tope, y la accion
  # oficial no la pisa. Por encima, solo con CONTENCION=0 (plataforma avisada).
  PROCS_PEDIDO=1
  export PROCS_PEDIDO
  if [[ "$PROCS" -gt "$PROCS_MAX" && "${CONTENCION:-1}" != "0" ]]; then
    echo "[contencion] PROCS=$PROCS pedido; se baja a $PROCS_MAX, la mitad de" \
         "los nucleos (el servidor es compartido; CONTENCION=0 lo permite)" >&2
    PROCS="$PROCS_MAX"
  fi
fi
export NUCLEOS PROCS PROCS_MAX

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

# H-85 (2026-09-15): el codigo de salida de la ultima orden de corre(), para
# quien lo quiera imprimir aunque corre() devuelva cero (PARA_EN_FALLO=0).
# En seco vale «seco»: no se ejecuto nada.
CODIGO_CORRE=""

# Tarea 4d (esperador con tope): la orden que envuelve la siguiente llamada a
# corre(), por ejemplo `timeout --kill-after=300 18300`. Vacia por omision,
# de modo que las demas acciones corren exactamente como antes; quien la pone
# la vacia al volver.
ENVOLTURA=()

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
    printf '  -> %s   [SECO]' "$nombre"
    if [[ ${#ENVOLTURA[@]} -gt 0 ]]; then printf ' %q' "${ENVOLTURA[@]}"; fi
    printf ' %s -u -W ignore' "$PY"
    printf ' %q' "$@"
    printf '\n'
    CODIGO_CORRE="seco"
    return 0
  fi

  local log="$LOGS/${nombre}_$(marca).log"
  echo "  -> $nombre   (log: $log)"
  local codigo=0
  # -u: sin bufer (regla principal de CLAUDE.md, H-80). Si se detiene una
  # corrida larga a mitad, el log ya tiene lo que alcanzo a escribir.
  ${ENVOLTURA[@]+"${ENVOLTURA[@]}"} "$PY" -u -W ignore "$@" > "$log" 2>&1 \
    || codigo=$?
  CODIGO_CORRE="$codigo"

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
             test_oraculo_anexo4 test_presupuesto_acoplado test_piso_P \
             test_arranque_acoplado test_compara_arranque \
             test_criterio_reparto test_censo_convergencia \
             test_reposo_mercado test_reposo_motor \
             test_compuertas_matriz_reposo test_compara_matriz_reposo \
             test_dinamica_regularizada; do
      corre "pytest_$t" -m pytest "tests/$t.py" -q
    done
    # D49 / D50: la compuerta de la dinamica regularizada, SOLO sus dos horas
    # rapidas (853 y 2120): `-k "not lenta"`. Las dos lentas (874 y 4766)
    # cuestan horas y van aparte, con las ordenes del docstring de la
    # compuerta (revision final, menor 2).
    corre "pytest_gate_reposo_cero_dinamica" -m pytest \
          "tests/gate_reposo_cero_dinamica.py" -q -k "not lenta"
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
    #   PROCS=8 bash modelo_base/run_servidor.sh decision 200   (como mucho PROCS_MAX)
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

    # TODO EL TRAMO DE LA TESIS (2026-09-18), no toda la maquina.
    #
    # Antes la corrida oficial tomaba TODOS los nucleos utiles. El servidor es
    # compartido con la plataforma MTE, que es produccion, y desde el incidente
    # del 2026-09-18 la corrida oficial toma PROCS_MAX: como mucho la mitad de
    # los nucleos, los del tramo de la contencion. Quien quiera menos lo pide:
    # PROCS=8 bash ...
    #
    # UTILES, y no los que la maquina declara. Dentro de un contenedor o con la
    # afinidad restringida los dos numeros difieren, y abrir mas procesos que
    # nucleos utiles no acelera: los hace pelearse.
    if [[ -z "${PROCS_PEDIDO:-}" ]]; then
      PROCS="$PROCS_MAX"
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
    echo "    Para dejar mas holgura:  PROCS=8 bash $0 oficial   (como mucho $PROCS_MAX)"
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

  arranque)
    # H-85, D45 y D46 (2026-09-15). La matriz dejo nueve horas sin resolver
    # por el arranque del acoplado; el arranque factible es una opcion
    # apagada por defecto (--arranque-acoplado factible) y se mide aqui antes
    # de decidir si pasa a ser el defecto y se repite la matriz (D45). La
    # misma campana mide en cuantas horas el precio por comprador no queda
    # determinado (D46). Una semana, la del 5 al 11 de mayo de 2025, que
    # contiene la hora 753 de E4; E0 y E4, cada uno con los dos arranques.
    #
    # Las compuertas NO se repiten: ya pasaron con este codigo. Las corridas
    # NO se detienen por el codigo 3 de D38 (la semana de E4 con el arranque
    # de hoy lo dara, por la hora 753): PARA_EN_FALLO=0 y se imprime el
    # codigo de cada una.
    if [[ -z "${MTE_ROOT:-}" ]]; then
      echo "  MTE_ROOT no esta definido. Exportalo antes:"
      echo "    export MTE_ROOT=\$PWD/MedicionesMTE_v3"
      exit 2
    fi
    ARR="SALIDAS_SERVIDOR/arranque"

    echo "=== ARRANQUE DEL ACOPLADO (H-85; D45 y D46) ==="
    echo "    semana del 2025-05-05 al 2025-05-11 (contiene la hora 753 de E4)"
    echo "    MTE_ROOT = $MTE_ROOT"
    echo "    procesos del mercado = $PROCS"
    echo "    salidas  = $ARR"
    echo

    echo "--- 1/4 · la sintaxis del lanzador (las compuertas no se repiten)"
    if bash -n "$0"; then
      echo "     ok"
    else
      echo "     FALLA: el lanzador tiene un error de sintaxis"
      exit 2
    fi

    echo
    echo "--- 2/4 · las cuatro corridas de la semana"
    CODIGOS=()
    for par in "${CASOS_ARRANQUE[@]}"; do
      CASO="${par%%:*}"; EXTRA="${par#*:}"
      for REGLA in "${REGLAS_ARRANQUE[@]}"; do
        DIR="$ARR/${CASO}_${REGLA}"
        ALM="$DIR/almacen"
        crea_dir "$ALM"
        echo
        echo "  --- $CASO con el arranque $REGLA  ->  $DIR"
        PARA_EN_FALLO=0 corre "arranque_${CASO}_${REGLA}" main_simulation.py \
              --data real --full --desde 2025-05-05 --hasta 2025-05-12 \
              --include-c5 --no-regulado \
              --metodo acoplado --plazo-hora 15 \
              --horizonte-max-acoplado 0.4 \
              --arranque-acoplado "$REGLA" \
              --almacen "$ALM" \
              ${EXTRA:+$EXTRA} --out-dir "$DIR"
        echo "     codigo de salida de ${CASO} con ${REGLA}: $CODIGO_CORRE"
        CODIGOS+=("${CASO}_${REGLA}=${CODIGO_CORRE}")
      done
    done

    echo
    echo "--- 3/4 · la comparacion de los dos arranques, E0 y E4"
    for par in "${CASOS_ARRANQUE[@]}"; do
      CASO="${par%%:*}"
      PARA_EN_FALLO=0 corre "arranque_compara_${CASO}" \
            "$SONDA/compara_arranque.py" \
            "$ARR/${CASO}_iguales/almacen" "$ARR/${CASO}_factible/almacen" \
            --cobertura m1 --etiqueta "$CASO" --salida "$ARR"
      echo "     codigo de salida de la comparacion de ${CASO}: $CODIGO_CORRE"
      CODIGOS+=("compara_${CASO}=${CODIGO_CORRE}")
    done

    echo
    echo "--- 4/4 · la recogida"
    bash "$0" recoger arranque
    echo
    echo "=== ARRANQUE COMPLETO ==="
    echo "  codigos de salida: ${CODIGOS[*]}"
    echo "  El 3 de D38 en E4 con el arranque iguales es lo esperado (hora 753)."
    echo "  Mira en los registros arranque_compara_<caso>_<fecha>.log las horas"
    echo "  sin resolver de cada arranque, cuantas cambian y las de precio"
    echo "  indeterminado (D46)."
    ;;

  convergencia)
    # H-86, D47 (2026-09-16). El criterio de parada del acoplado mira EL
    # PRECIO, y en muchas horas el precio ya esta quieto mientras el reparto
    # entre compradores sigue moviendose entero: de las 15 541 horas de mercado
    # de la matriz, una de cada tres no llego siquiera al criterio (2 556 por
    # tope, 2 475 por presupuesto), y de las que llegaron, la hora 109 de E0
    # paro con residuo 0,0065 y su reparto lejos del punto final. Integrada a
    # 2,0 esa hora da todo el excedente a un solo comprador, mientras el
    # horizonte de produccion lo reparte casi por igual entre cuatro.
    #
    # Esta campana mide QUE CUESTA mirar tambien el reparto, para fijar el
    # horizonte de produccion con el costo medido delante. NO cambia ese
    # horizonte y NO repite la matriz: las dos cosas vienen despues, con estas
    # cifras.
    #
    # Una semana, la del 5 al 11 de mayo de 2025; dos casos, E0 y K1 (el de
    # menos horas estacionarias de la matriz, el 33 %); tres configuraciones,
    # la de hoy y el criterio nuevo a los horizontes 0,4 y 2,0. Todas con el
    # arranque factible, que es el defecto desde D45 y el barato.
    #
    # LAS COMPUERTAS SI HAY QUE CORRERLAS ANTES, al reves que en `arranque`.
    # Este paquete mueve el defecto del arranque del acoplado a "factible"
    # (D45) y edita `tests/gate_almacen_cruzado.py`, que es justo la que
    # compara el motor contra el camino independiente de la sonda: ninguna de
    # las dos cosas ha pasado todavia por una corrida de compuertas en el
    # servidor. Esta accion no las corre sola, para no encadenar una hora de
    # pruebas a una campana de una noche, pero lo avisa en su paso 1.
    #
    # Las corridas NO se detienen por el codigo 3 de D38 (una semana con horas
    # sin resolver lo dara): PARA_EN_FALLO=0 y se imprime el codigo de cada una.
    if [[ -z "${MTE_ROOT:-}" ]]; then
      echo "  MTE_ROOT no esta definido. Exportalo antes:"
      echo "    export MTE_ROOT=\$PWD/MedicionesMTE_v3"
      exit 2
    fi
    CONV="SALIDAS_SERVIDOR/convergencia"

    echo "=== LA CONVERGENCIA DEL REPARTO (H-86, D47) ==="
    echo "    semana del 2025-05-05 al 2025-05-11"
    echo "    MTE_ROOT = $MTE_ROOT"
    echo "    procesos del mercado = $PROCS"
    echo "    salidas  = $CONV"
    echo "    ESTO TARDA DEL ORDEN DE UNA NOCHE: la configuracion del"
    echo "    horizonte 2,0 integra hasta que el reparto se quieta, y en la"
    echo "    medicion de H-86 hubo horas de 3 609 (s) con 28,7 millones de"
    echo "    evaluaciones. Es a proposito: la campana existe para ver el"
    echo "    costo, no para acotarlo."
    echo

    echo "--- 1/5 · la sintaxis del lanzador"
    if bash -n "$0"; then
      echo "     ok"
    else
      echo "     FALLA: el lanzador tiene un error de sintaxis"
      exit 2
    fi
    echo
    echo "  AVISO: en ESTE paquete las compuertas SI hay que correrlas antes:"
    echo "      bash $0 compuertas"
    echo "  El defecto del arranque del acoplado se movio a «factible» (D45) y"
    echo "  tests/gate_almacen_cruzado.py se edito despues de la ultima corrida"
    echo "  de compuertas. Esa compuerta es la que compara el motor contra el"
    echo "  camino independiente de la sonda, es decir la que se enteraria si"
    echo "  los dos dejaran de arrancar igual. Una campana de una noche sobre"
    echo "  un motor sin compuertas no vale nada."

    echo
    echo "--- 2/5 · las seis corridas de la semana"
    CODIGOS=()
    for par in "${CASOS_CONVERGENCIA[@]}"; do
      CASO="${par%%:*}"; EXTRA="${par#*:}"
      for cfg in "${CONFIGS_CONVERGENCIA[@]}"; do
        NOMBRE="${cfg%%:*}"; OPTS="${cfg#*:}"
        DIR="$CONV/${CASO}_${NOMBRE}"
        ALM="$DIR/almacen"
        crea_dir "$ALM"
        echo
        echo "  --- $CASO con la configuracion $NOMBRE  ->  $DIR"
        PARA_EN_FALLO=0 corre "convergencia_${CASO}_${NOMBRE}" main_simulation.py \
              --data real --full --desde 2025-05-05 --hasta 2025-05-12 \
              --include-c5 --no-regulado \
              --metodo acoplado --arranque-acoplado factible \
              ${OPTS:+$OPTS} \
              --almacen "$ALM" \
              ${EXTRA:+$EXTRA} --out-dir "$DIR"
        echo "     codigo de salida de ${CASO} con ${NOMBRE}: $CODIGO_CORRE"
        CODIGOS+=("${CASO}_${NOMBRE}=${CODIGO_CORRE}")
      done
    done

    echo
    echo "--- 3/5 · los repartos, comparados dos a dos"
    # La herramienta es la de D46 (`compara_arranque.py`), que compara dos
    # almacenes de la misma ventana hora a hora. Aqui A y B no son dos
    # arranques sino dos criterios: A el primero del par, B el segundo, y las
    # diferencias siguen siendo B menos A.
    for par in "${CASOS_CONVERGENCIA[@]}"; do
      CASO="${par%%:*}"
      for pc in "${PARES_CONVERGENCIA[@]}"; do
        A="${pc%%:*}"; B="${pc#*:}"
        PARA_EN_FALLO=0 corre "convergencia_compara_${CASO}_${A}_vs_${B}" \
              "$SONDA/compara_arranque.py" \
              "$CONV/${CASO}_${A}/almacen" "$CONV/${CASO}_${B}/almacen" \
              --cobertura m1 --etiqueta "${CASO}_${A}_vs_${B}" \
              --etiqueta-a "$A" --etiqueta-b "$B" \
              --salida "$CONV"
        echo "     codigo de la comparacion ${CASO} ${A} vs ${B}: $CODIGO_CORRE"
        CODIGOS+=("compara_${CASO}_${A}_vs_${B}=${CODIGO_CORRE}")
      done
    done

    echo
    echo "--- 4/5 · el censo del costo"
    PARA_EN_FALLO=0 corre "convergencia_censo" \
          "$SONDA/censo_convergencia.py" "$CONV" \
          --cobertura m1 --salida "$CONV"
    echo "     codigo del censo: $CODIGO_CORRE"
    CODIGOS+=("censo=${CODIGO_CORRE}")

    echo
    echo "--- 5/5 · la recogida"
    bash "$0" recoger convergencia
    echo
    echo "=== CONVERGENCIA COMPLETA ==="
    echo "  codigos de salida: ${CODIGOS[*]}"
    echo "  Mira en convergencia_censo_<fecha>.log, por caso y configuracion,"
    echo "  cuantas horas pararon por cada motivo y cuantas quedaron con el"
    echo "  reparto todavia en marcha; en los registros de cada corrida, las"
    echo "  lineas [D26] y [D47] y los segundos del mercado; y en las"
    echo "  comparaciones, cuanto se mueve el reparto entre configuraciones."
    ;;

  matriz_reposo)
    # D48 a D69 (2026-09-17): la matriz de trece casos con el mercado de cada
    # hora resuelto en el reposo del juego regularizado, en forma cerrada
    # (CAL-53, ADR 0060; M-F de H-90). Es una copia de la estructura de
    # `matriz`, con estos cambios:
    #
    #   - escribe en SALIDAS_SERVIDOR/matriz_reposo/<caso>, sin pisar
    #     SALIDAS_SERVIDOR/matriz, que es la matriz vieja (acoplado, 15 de
    #     septiembre) y se queda para comparar (D57);
    #   - corre con `--metodo reposo`, el presupuesto `sigma` con la sigma base
    #     (I-1)/I (sin --sigma-nivel), la liquidacion `uniforme` y el despacho
    #     `piso`: los vendedores despachan por su piso, una caminata
    #     competitiva decide quien entra y el piso del juego es el del
    #     vendedor marginal (D63 a D65). Son los defectos, y van escritos
    #     igual, para que la orden del registro diga con que se corrio. Con el
    #     piso marginal la participacion es una guarda inerte (D67): un solo
    #     retiro hace salir la corrida con el codigo 3, y la compuerta de
    #     salida lo comprueba otra vez sobre el almacen (`cero_retiros`);
    #   - NO lee los veredictos de la sonda de H-79 ni pone las palancas del
    #     acoplado (tolerancia y horizonte): la via por reposo no integra;
    #   - NO pasa --plazo-hora. El motor no lo exige con `reposo`: la opcion
    #     tiene un defecto de 15 (min) que actua en cualquier via, como guardia
    #     del lazo paralelo (D24), y una hora por reposo tarda milisegundos;
    #   - detras de cada corrida va su COMPUERTA DE SALIDA
    #     (`compuertas_matriz_reposo.py`) sobre su almacen, por corre(), de
    #     modo que su fallo para la cadena como el de la corrida;
    #   - las figuras del foro de E0 van con `--grupo CDE`. El grupo A lee la
    #     tabla de trayectorias, que la via por reposo no escribe, y
    #     `gen_foro.py` se cae en su primera figura con FileNotFoundError
    #     (medido en la tarea 4b sobre un almacen por reposo); C, D y E salen.
    #     Las figuras no detienen la cadena (PARA_EN_FALLO=0): en la matriz
    #     vieja, una figura rota la detuvo antes de la recogida;
    #   - NO corre `gen_foro_b.py`: sus figuras vuelven a simular el modelo
    #     base con otros parametros, no leen el almacen ni dependen de la via,
    #     y ya salieron con la matriz vieja (unos 7 (min) que no aportan);
    #   - al final, la comparacion con la matriz vieja
    #     (`compara_matriz_reposo.py`) de los casos que la tengan; si no hay
    #     ninguno, avisa y sigue: se hace en casa, en segundos.
    #
    # Se conservan las compuertas, --include-c5 --no-regulado
    # --analisis-ligero, el almacen, las opciones de cada caso (CASOS_MATRIZ),
    # DESDE, el tratamiento del codigo 3 (D38) y la liquidacion y la equidad
    # por caso. Ninguna corrida usa --modo-presupuesto c136, que saldria con 3
    # por H-32 en unas 451 horas (medidas con D62; con el piso marginal la
    # cuenta puede cambiar).
    set -e
    export PARA_EN_FALLO=1
    if [[ -z "${MTE_ROOT:-}" ]]; then
      echo "  MTE_ROOT no esta definido. Exportalo antes:"
      echo "    export MTE_ROOT=\$PWD/MedicionesMTE_v3"
      exit 2
    fi
    valida_desde

    echo "=== MATRIZ CON EL REPOSO (D48 a D69) · las trece corridas ==="
    echo "    MTE_ROOT = $MTE_ROOT"
    echo "    procesos del mercado = $PROCS"
    echo "    salidas  = $MATRIZ_REPOSO   (la matriz vieja, $MATRIZ_VIEJA, no se toca)"
    echo

    echo "--- 1/6 · compuertas"
    bash "$0" compuertas

    echo
    echo "--- 2/6 · las trece corridas, cada una con su compuerta de salida"
    SALTAR="${DESDE:-}"
    for par in "${CASOS_MATRIZ[@]}"; do
      CASO="${par%%:*}"; EXTRA="${par#*:}"
      if [[ -n "$SALTAR" ]]; then
        if [[ "$CASO" == "$SALTAR" ]]; then
          SALTAR=""
        else
          echo "  ... salta $CASO (DESDE=$DESDE)"
          continue
        fi
      fi
      DIR="$MATRIZ_REPOSO/$CASO"
      ALM="$DIR/almacen"
      crea_dir "$ALM"
      echo
      echo "  --- $CASO  ->  $DIR"
      # D38: por reposo, la corrida sale con 3 si alguna hora termino con
      # excepcion del nucleo (C-190) o si la participacion retiro a algun
      # vendedor (D67); las horas vencidas por el plazo tambien cuentan,
      # aunque no deberia haber ninguna.
      corre "matriz_reposo_${CASO}" main_simulation.py \
            --data real --full --include-c5 --no-regulado \
            --metodo reposo --modo-presupuesto sigma \
            --regla-precio uniforme --despacho-vendedores piso \
            --analisis-ligero --almacen "$ALM" \
            ${EXTRA:+$EXTRA} --out-dir "$DIR" || {
        cod=$?
        echo
        if [[ $cod -eq 3 ]]; then
          echo "  $CASO salio con codigo 3 (D38): alguna hora termino con excepcion"
          echo "  del reposo (C-190), la participacion retiro a algun vendedor (D67:"
          echo "  con el piso marginal debe dar 0), o las vencidas por el plazo pasan"
          echo "  del 1 %. Sus salidas estan escritas, pero la cadena no sigue con un"
          echo "  caso asi."
        else
          echo "  $CASO salio con codigo $cod."
        fi
        echo "  Mira las lineas [C-190], [C-151], [D24], [D48] y [D38] de su registro"
        echo "  ($LOGS/matriz_reposo_${CASO}_<fecha>.log) y retoma desde este caso con:"
        echo "    DESDE=$CASO bash $0 matriz_reposo"
        exit "$cod"
      }
      corre "matriz_reposo_compuerta_${CASO}" \
            "$SONDA/compuertas_matriz_reposo.py" "$ALM" \
            --cobertura m1 --caso "$CASO" || {
        cod=$?
        echo
        echo "  La compuerta de salida de $CASO no paso (codigo $cod): alguna hora"
        echo "  no cumple una identidad del reposo (1), o el almacen no se pudo"
        echo "  comprobar (2). El almacen esta escrito; la lista de fallos va al"
        echo "  final de $LOGS/matriz_reposo_compuerta_${CASO}_<fecha>.log."
        echo "  Retoma desde este caso con:"
        echo "    DESDE=$CASO bash $0 matriz_reposo"
        exit "$cod"
      }
    done

    echo
    echo "--- 3/6 · la liquidacion y la equidad de cada caso (cobertura m1)"
    for par in "${CASOS_MATRIZ[@]}"; do
      CASO="${par%%:*}"
      ALM="$MATRIZ_REPOSO/$CASO/almacen"
      corre "matriz_reposo_liquidacion_${CASO}" \
            reformateo/documento/scripts/liquidacion.py "$ALM" \
            --cobertura m1 --periodo mes
      for P in mes hora_del_dia dia_semana; do
        corre "matriz_reposo_equidad_${CASO}_${P}" analysis/equidad_periodo.py \
              "$ALM" --cobertura m1 --periodo "$P"
      done
    done

    echo
    echo "--- 4/6 · las figuras del foro, solo de E0, grupos C, D y E"
    CODIGOS=()
    FIGS="$MATRIZ_REPOSO/figuras_foro"
    crea_dir "$FIGS"
    PARA_EN_FALLO=0 corre "matriz_reposo_foro_cde_E0" \
          reformateo/documento/scripts/gen_foro.py \
          "$MATRIZ_REPOSO/E0/almacen" --cobertura m1 --grupo CDE \
          --figuras "$FIGS"
    CODIGOS+=("foro_cde_E0=${CODIGO_CORRE}")

    echo
    echo "--- 5/6 · la comparacion con la matriz vieja"
    casos_con_matriz_vieja
    COMPARA=("$SONDA/compara_matriz_reposo.py" --vieja "$MATRIZ_VIEJA" \
             --nueva "$MATRIZ_REPOSO" --cobertura m1 \
             --salida "$MATRIZ_REPOSO/compara_matriz_reposo.csv")
    if [[ ${#VIEJOS[@]} -eq 0 ]]; then
      echo "  AVISO: no esta $MATRIZ_VIEJA/<caso>/almacen de ningun caso; la"
      echo "  comparacion no se hace aqui. Se hace en casa, en segundos, con la"
      echo "  matriz vieja de la entrega del 15 de septiembre. --nueva es la"
      echo "  carpeta $MATRIZ_REPOSO que sale del tar de esta recogida,"
      echo "  desempaquetado en su carpeta de entrega, por ejemplo:"
      echo "    python -u $SONDA/compara_matriz_reposo.py \\"
      echo "      --vieja SALIDAS_SERVIDOR/entrega_matriz_2026-09-15/SALIDAS_SERVIDOR/matriz \\"
      echo "      --nueva SALIDAS_SERVIDOR/entrega_<nombre>/SALIDAS_SERVIDOR/matriz_reposo \\"
      echo "      --salida SALIDAS_SERVIDOR/entrega_<nombre>/compara_matriz_reposo.csv"
      CODIGOS+=("compara=no se hizo")
      if [[ "${SECO:-0}" == "1" ]]; then
        echo "  [SECO] con la matriz vieja en el servidor, correria:"
        PARA_EN_FALLO=0 corre "matriz_reposo_compara" "${COMPARA[@]}" \
              --casos $(for par in "${CASOS_MATRIZ[@]}"; do printf '%s ' "${par%%:*}"; done)
      fi
    else
      if [[ ${#VIEJOS[@]} -lt ${#CASOS_MATRIZ[@]} ]]; then
        echo "  AVISO: solo hay matriz vieja de ${#VIEJOS[@]} casos; se comparan: ${VIEJOS[*]}"
      fi
      PARA_EN_FALLO=0 corre "matriz_reposo_compara" "${COMPARA[@]}" \
            --casos "${VIEJOS[@]}"
      CODIGOS+=("compara=${CODIGO_CORRE}")
    fi

    echo
    echo "--- 6/6 · la recogida"
    bash "$0" recoger matriz_reposo
    echo
    echo "=== MATRIZ CON EL REPOSO COMPLETA ==="
    echo "  codigos de salida: ${CODIGOS[*]}"
    echo "  Un caso o una compuerta de salida que falla detiene la cadena; se"
    echo "  retoma desde ese caso con:  DESDE=<caso> bash $0 matriz_reposo"
    echo "  Mira en cada matriz_reposo_<caso>_<fecha>.log las dos lineas [D48]"
    echo "  (M-H: la energia en horas de un solo comprador; los retiros de la via"
    echo "  por reposo, que deben ser 0 (D67); y la prima descompuesta en renta"
    echo "  inframarginal y parte del juego (D69)), en"
    echo "  cada matriz_reposo_compuerta_<caso>_<fecha>.log el resumen por regimen"
    echo "  y las identidades cero_retiros y prima_descompuesta,"
    echo "  y en matriz_reposo_compara_<fecha>.log los cambios de signo (M-F)."
    ;;

  barrido_sigma)
    # D50 (2026-09-17): el barrido del presupuesto de precios de la via por
    # reposo, S = suma de [piso + sigma·(techo - piso)], con sigma 0 (el
    # «Chacon fiel»: todos en el piso), 0,5 y 1 (todos en su techo). La sigma
    # base, (I-1)/I, es la de `matriz_reposo`. Va aparte para que el autor
    # tenga primero las cifras base: se corre DESPUES de `matriz_reposo`.
    #
    # Los trece casos por sigma, en SALIDAS_SERVIDOR/matriz_reposo/<caso>_sigma
    # <0|05|1>, con las mismas opciones que `matriz_reposo` mas --sigma-nivel,
    # y cada uno con su compuerta de salida. Recorre una sigma entera antes de
    # pasar a la siguiente. SIGMAS acota la lista (por defecto "0 0.5 1") y
    # DESDE salta hasta ese caso DE LA PRIMERA SIGMA de la lista; las
    # siguientes corren enteras. Para retomar en la segunda sigma, se la pone
    # primera:  SIGMAS="0.5 1" DESDE=P1 bash $0 barrido_sigma
    #
    # Las compuertas no se repiten: ya pasaron con este codigo en el paso 1 de
    # `matriz_reposo`. Por eso el barrido se lanza CON EL MISMO PAQUETE que
    # `matriz_reposo`, sin traer codigo nuevo entre las dos; si cambio algo,
    # antes van las compuertas. La liquidacion, la equidad, las figuras y la comparacion
    # no se hacen aqui; la comparacion del barrido se hace en casa con
    # `compara_matriz_reposo.py --sufijo-nueva _sigma<etiqueta>`.
    set -e
    export PARA_EN_FALLO=1
    if [[ -z "${MTE_ROOT:-}" ]]; then
      echo "  MTE_ROOT no esta definido. Exportalo antes:"
      echo "    export MTE_ROOT=\$PWD/MedicionesMTE_v3"
      exit 2
    fi
    valida_sigmas
    valida_desde
    # Sin comodines posibles: valida_sigmas ya comprobo que son numeros.
    SIGS=( $SIGMAS_BARRIDO )

    echo "=== BARRIDO DE SIGMA (D50) · trece casos por sigma ==="
    echo "    sigmas   = ${SIGS[*]}   (la base, (I-1)/I, es matriz_reposo)"
    echo "    MTE_ROOT = $MTE_ROOT"
    echo "    procesos del mercado = $PROCS"
    echo "    salidas  = $MATRIZ_REPOSO/<caso>_sigma<etiqueta>"
    echo

    echo "--- 1/3 · la sintaxis del lanzador (las compuertas ya pasaron en matriz_reposo)"
    if bash -n "$0"; then
      echo "     ok"
    else
      echo "     FALLA: el lanzador tiene un error de sintaxis"
      exit 2
    fi
    echo "  AVISO: se corre con el mismo paquete que matriz_reposo. Si entre las"
    echo "  dos llego codigo nuevo, antes:  bash $0 compuertas"

    echo
    echo "--- 2/3 · las corridas, cada una con su compuerta de salida"
    SALTAR="${DESDE:-}"
    for n in "${!SIGS[@]}"; do
      S="${SIGS[$n]}"
      ETQ="$(etiqueta_sigma "$S")"
      RESTO="${SIGS[*]:$n}"
      echo
      echo "  === sigma $S"
      for par in "${CASOS_MATRIZ[@]}"; do
        CASO="${par%%:*}"; EXTRA="${par#*:}"
        if [[ -n "$SALTAR" ]]; then
          if [[ "$CASO" == "$SALTAR" ]]; then
            SALTAR=""
          else
            echo "  ... salta $CASO (DESDE=$DESDE)"
            continue
          fi
        fi
        DIR="$MATRIZ_REPOSO/${CASO}_sigma${ETQ}"
        ALM="$DIR/almacen"
        crea_dir "$ALM"
        echo
        echo "  --- $CASO con sigma $S  ->  $DIR"
        corre "barrido_sigma${ETQ}_${CASO}" main_simulation.py \
              --data real --full --include-c5 --no-regulado \
              --metodo reposo --modo-presupuesto sigma --sigma-nivel "$S" \
              --regla-precio uniforme --despacho-vendedores piso \
              --analisis-ligero --almacen "$ALM" \
              ${EXTRA:+$EXTRA} --out-dir "$DIR" || {
          cod=$?
          echo
          if [[ $cod -eq 3 ]]; then
            echo "  $CASO con sigma $S salio con codigo 3 (D38): alguna hora termino"
            echo "  con excepcion del reposo (C-190), la participacion retiro a algun"
            echo "  vendedor (D67), o las vencidas por el plazo pasan del 1 %. Sus"
            echo "  salidas estan escritas."
          else
            echo "  $CASO con sigma $S salio con codigo $cod."
          fi
          echo "  Mira las lineas [C-190], [C-151], [D24], [D48] y [D38] de su registro y retoma con:"
          echo "    SIGMAS=\"$RESTO\" DESDE=$CASO bash $0 barrido_sigma"
          exit "$cod"
        }
        corre "barrido_compuerta_sigma${ETQ}_${CASO}" \
              "$SONDA/compuertas_matriz_reposo.py" "$ALM" \
              --cobertura m1 --caso "${CASO}_sigma${ETQ}" || {
          cod=$?
          echo
          echo "  La compuerta de salida de $CASO con sigma $S no paso (codigo $cod)."
          echo "  La lista de fallos va al final de su registro. Retoma con:"
          echo "    SIGMAS=\"$RESTO\" DESDE=$CASO bash $0 barrido_sigma"
          exit "$cod"
        }
      done
    done

    echo
    echo "--- 3/3 · la recogida"
    bash "$0" recoger barrido_sigma
    echo
    echo "=== BARRIDO DE SIGMA COMPLETO ==="
    echo "  La comparacion con la base se hace en casa y por sigma. Las dos raices"
    echo "  son la carpeta $MATRIZ_REPOSO que sale del tar, desempaquetado en"
    echo "  su carpeta de entrega, por ejemplo:"
    echo "    python -u $SONDA/compara_matriz_reposo.py \\"
    echo "      --vieja SALIDAS_SERVIDOR/entrega_<nombre>/SALIDAS_SERVIDOR/matriz_reposo \\"
    echo "      --nueva SALIDAS_SERVIDOR/entrega_<nombre>/SALIDAS_SERVIDOR/matriz_reposo \\"
    echo "      --sufijo-nueva _sigma05 --salida SALIDAS_SERVIDOR/entrega_<nombre>/compara_sigma05.csv"
    ;;

  validacion_reposo)
    # M-A a M-G (2026-09-17): la validacion del reposo contra la dinamica
    # regularizada. Decide COMO SE CUENTA cada regimen en la tesis (reposo
    # verificado o regla declarada); no cambia ninguna cifra de la matriz, que
    # ya corrio con su compuerta de salida.
    #
    # NO SE HACE CON EL MOTOR. En una hora rigida, llegar al reposo integrando
    # cuesta del orden de 1e9 evaluaciones del lado derecho. Se hace con el
    # ARNES ACELERADO de la sonda del consenso, en
    # reformateo/documento/scripts/sonda/consenso/, que multiplica por k los
    # bloques lentos sin mover los ceros del lado derecho. El motor no hace eso
    # ni debe hacerlo. El README de esa carpeta dice que mide cada guion, que
    # escribe y que cuesta.
    #
    # PARA_EN_FALLO=0 A PROPOSITO: una medicion que no converge ES UN RESULTADO
    # (ese regimen se publica como regla declarada), no un fallo que deba
    # llevarse por delante a las que faltan. La unica excepcion es el paso 1:
    # si el lado derecho del arnes no es el del motor, ninguna medicion de esta
    # noche significa nada y la accion se detiene con el codigo 3.
    export PARA_EN_FALLO=0
    if [[ -z "${MTE_ROOT:-}" ]]; then
      echo "  MTE_ROOT no esta definido. Exportalo antes:"
      echo "    export MTE_ROOT=\$PWD/MedicionesMTE_v3"
      exit 2
    fi

    CONS="$SONDA/consenso"
    VAL="SALIDAS_SERVIDOR/validacion_reposo"
    # De donde salen las horas de cada regimen. Por defecto, los almacenes que
    # dejo `matriz_reposo`; con ALMACENES se apunta a una entrega desempaquetada.
    ALMACENES="${ALMACENES:-$MATRIZ_REPOSO}"
    # Tope de pared por medicion (s). Dentro, cada corrida tiene ademas el suyo
    # (3 600 s), y si el tope total corta, el guion dice con que --desde se
    # retoma.
    TOPE_M="${TOPE_MEDICION:-14400}"
    # Las dos horas lentas de la compuerta de la dinamica: LENTAS=0 las salta.
    LENTAS="${LENTAS:-1}"
    # Menor 2 de la revision de 4c: un tope GLOBAL de pared para toda la
    # accion, porque los topes sumados pasan de una noche (unas 22 (h) en el
    # peor caso, y hasta 27 con las corridas en vuelo; la cuenta, en
    # MONTAJE_SERVIDOR.md). Cada medicion cara recibe como --tope-total lo
    # menor entre el suyo y lo que quede; si al empezar quedan menos de 10
    # (min), se SALTA y su nombre queda en CODIGOS. Lo que tarda segundos (el
    # arnes, M-D, el censo, los veredictos, la dorada y la recogida) corre
    # siempre.
    TOPE_GLOBAL="${TOPE_GLOBAL_S:-43200}"
    INICIO_GLOBAL="$(date +%s)"
    MARGEN_MINIMO=600
    queda() {
      local r=$(( TOPE_GLOBAL - ( $(date +%s) - INICIO_GLOBAL ) ))
      if (( r < 0 )); then r=0; fi
      printf '%s' "$r"
    }
    tope_de() {
      local r
      r="$(queda)"
      if (( r < $1 )); then printf '%s' "$r"; else printf '%s' "$1"; fi
    }
    hay_tiempo() {
      local r
      r="$(queda)"
      if (( r >= MARGEN_MINIMO )); then return 0; fi
      echo "  === TOPE GLOBAL: quedan $r s de $TOPE_GLOBAL; se SALTA $1 ==="
      return 1
    }
    SALTADAS=()
    # Tarea 4d (CLAUDE.md: un solo esperador por corrida, con tope, que cubra
    # el fallo). Cada corre_mediciones.py va envuelto en `timeout`, con su tope
    # total mas 3 900 (s): la hora de la ultima corrida en vuelo (3 600) y 300
    # de margen, y --kill-after=300 por si no atiende al SIGTERM. Un cuelgue
    # del gestor del pool queda asi acotado y sale con 124 (o 137), que el
    # cierre anota como fallo. Sin `timeout` (GNU) no se envuelve, y se dice.
    TIMEOUT_GNU=0
    if timeout --version >/dev/null 2>&1; then TIMEOUT_GNU=1; fi
    con_tope() {                     # $1 = el --tope-total de la medicion (s)
      ENVOLTURA=()
      if [[ "$TIMEOUT_GNU" == "1" ]]; then
        ENVOLTURA=(timeout --kill-after=300 "$(( $1 + 3900 ))")
      fi
    }
    # N3 de la re-revision de 4c: una medicion (o su veredicto) sale con 4
    # cuando el plan tenia corridas que no se llegaron a hacer. No es un fallo
    # del codigo, pero la medicion no esta completa: se anota «incompleta» y el
    # cierre dice INCOMPLETA (m3). `anota <etiqueta>` lo hace despues de corre().
    INCOMPLETAS=()
    anota() {
      if [[ "${CODIGO_CORRE}" == "4" ]]; then
        CODIGOS+=("$1=incompleta"); INCOMPLETAS+=("$1")
        echo "     (el codigo 4 es MEDICION INCOMPLETA: quedaron corridas del plan"
        echo "      sin hacer, por el tope; no es un fallo del codigo)"
      else
        CODIGOS+=("$1=${CODIGO_CORRE}")
      fi
    }
    # m1: los casos cuya seleccion de horas salio con 1 (descarto de mas o dejo
    # un grupo vacio). Las mediciones corren igual; el cierre lo repite.
    SELECCION_MAL=()
    # Tarea 4d: PASOS elige que pasos correr, para relanzar solo los que
    # fallaron (la noche del 2026-09-18: PASOS="3 4 5 7" son M-A, M-B, M-C y
    # M-E). Por defecto, todos. El 1 (el arnes frente al motor) corre SIEMPRE:
    # sin el nada de lo demas vale. El 2 (la muestra de horas) corre, caso por
    # caso, si falta su horas_<caso>.json aunque no se pida. La 10 (la recogida
    # y el cierre) tambien corre siempre. Lo que PASOS deja fuera sale en el
    # cierre como «no pedido», que no es un fallo ni un salto por el tope.
    PASOS_TODOS="1 2 3 4 5 6 7 8 9 10"
    PASOS="${PASOS:-$PASOS_TODOS}"
    PASOS="${PASOS//,/ }"
    for _p in $PASOS; do
      if ! [[ "$_p" =~ ^([1-9]|10)$ ]]; then
        echo "  PASOS=\"$PASOS\": \"$_p\" no es un paso (van del 1 al 10)"
        exit 2
      fi
    done
    export PASOS                     # la recogida (paso 10) lo lee tambien
    pedido() { [[ " $PASOS " == *" $1 "* ]]; }
    NO_PEDIDOS=()
    no_pedido() {                    # $1 = paso, $2 = etiqueta en CODIGOS
      echo "    no pedido (PASOS=\"$PASOS\"): no se corre"
      CODIGOS+=("$2=no_pedido"); NO_PEDIDOS+=("$1:$2")
    }
    crea_dir "$VAL"

    echo "=== VALIDACION DEL REPOSO (M-A a M-G) ==="
    echo "    MTE_ROOT  = $MTE_ROOT"
    echo "    procesos  = $PROCS   (corre_mediciones.py los baja si la memoria"
    echo "                no da ${MEMORIA_POR_PROCESO_GB:-1.5} GB a cada uno)"
    if [[ -n "${MEMORIA_TESIS:-}" ]]; then
      echo "    memoria   = tope duro de $MEMORIA_TESIS para todo el arbol"
      echo "                (MEMORIA_TESIS; como mucho $MEMORIA_TESIS / ${MEMORIA_POR_PROCESO_GB:-1.5} GB procesos)"
    else
      echo "    memoria   = SIN tope duro (MEMORIA_TESIS: lo pone la contencion"
      echo "                con systemd-run, solo en Linux)"
    fi
    echo "    almacenes = $ALMACENES   (de ahi salen las horas de cada regimen)"
    echo "    salidas   = $VAL"
    echo "    pasos     = $PASOS   (PASOS; el 1 y la recogida corren siempre,"
    echo "                el 2 si falta la muestra de algun caso)"
    echo "    tope por medicion = $TOPE_M s (M-A y M-B; M-C, M-E y M-G, 7200 s)"
    echo "    tope global = $TOPE_GLOBAL s (TOPE_GLOBAL_S; cada medicion recibe"
    echo "                  lo menor entre su tope y lo que quede)"
    if [[ "$TIMEOUT_GNU" == "1" ]]; then
      echo "    esperador = timeout, con el tope de cada medicion + 3900 s"
    else
      echo "    esperador = SIN timeout (no esta el de GNU): una medicion colgada"
      echo "                no se corta sola"
    fi
    echo
    CODIGOS=()

    echo "--- 1/10 · el lado derecho del arnes frente al del motor"
    echo "    Tiene que coincidir AL BIT en diez ramas: los defectos, el termino"
    echo "    entropico, el costo por la alternativa, el piso marginal y las tres"
    echo "    juntas; sobre el caso publicado, una hora sintetica de pisos"
    echo "    distintos y cuatro horas reales (la de E4 tiene dos vendedores)."
    echo "    Es lo que hace creible lo demas."
    corre "validacion_reposo_lado_derecho" "$CONS/arnes.py" \
          E0 "2025-05-09 13:00" E0 "2025-05-10 10:00" K1 "2025-05-11 08:00" \
          E4 "2025-05-07 07:00"
    CODIGOS+=("lado_derecho=${CODIGO_CORRE}")
    if [[ "${CODIGO_CORRE}" != "seco" && "${CODIGO_CORRE}" != "0" ]]; then
      echo
      echo "  === EL ARNES SE DESVIO DEL MOTOR, O NO SE PUDO COMPROBAR ==="
      echo "  El registro dice cual de las dos: DIFIERE (con el bloque del estado"
      echo "  y cuanto) o NO SE PUEDE COMPROBAR (una hora sin mercado, que no"
      echo "  tiene piso marginal). En los dos casos la comprobacion no esta"
      echo "  completa y ninguna medicion de esta noche se podria creer, de modo"
      echo "  que la accion para aqui. Mira"
      echo "  $LOGS/validacion_reposo_lado_derecho_<fecha>.log y corre:"
      echo "    python -m pytest tests/test_arnes_consenso.py -q"
      exit 3
    fi

    echo
    echo "--- 2/10 · la muestra de horas de cada regimen, comprobada"
    echo "    Cada hora escogida se vuelve a resolver con el arnes y se compara"
    echo "    con lo que el almacen guardo (regimen y piso del juego); la que no"
    echo "    coincide NO entra en la muestra."
    HORAS_VALIDACION=(
      "E0::10"
      "K1::10"
      "E4:compradores_cortos_con_cesmag:20"
      "E5:compradores_cortos_con_cesmag:10"
      "CV2:suma_no_cabe:37"
    )
    for par in "${HORAS_VALIDACION[@]}"; do
      CASO="${par%%:*}"; RESTO="${par#*:}"
      GRUPOS="${RESTO%%:*}"; NHORAS="${RESTO##*:}"
      ALM="$ALMACENES/$CASO/almacen"
      # Tarea 4d: sin el paso 2 en PASOS, la muestra que ya esta se usa tal
      # cual (la seleccion es determinista: semilla fija); la que falta se hace.
      if ! pedido 2 && [[ -f "$VAL/horas_${CASO}.json" ]]; then
        echo "    $CASO: se usa $VAL/horas_${CASO}.json, que ya esta (el paso 2"
        echo "    no se pidio)"
        CODIGOS+=("horas_$CASO=ya_estaba")
        continue
      fi
      if [[ ! -d "$ALM" && "${SECO:-0}" != "1" ]]; then
        echo "  AVISO: no esta $ALM; $CASO se queda sin muestra y las"
        echo "  mediciones que dependen de el correran con sus horas de respaldo"
        echo "  (M-A) o no correran (M-B, M-C)."
        CODIGOS+=("horas_$CASO=sin almacen")
        continue
      fi
      corre "validacion_reposo_horas_${CASO}" "$CONS/selecciona_horas.py" \
            --almacen "$ALM" --caso "$CASO" --cobertura m1 \
            --por-regimen "$NHORAS" --maximo 40 \
            ${GRUPOS:+--grupos "$GRUPOS"} \
            --salida "$VAL/horas_${CASO}.json"
      CODIGOS+=("horas_$CASO=${CODIGO_CORRE}")
      if [[ "${CODIGO_CORRE}" == "1" ]]; then SELECCION_MAL+=("$CASO"); fi
    done

    echo
    echo "--- 3/10 · M-A · la forma cerrada frente a la dinamica, por regimen"
    echo "    Diez horas de cada regimen, mu = 1, nivel sigma, piso del vendedor"
    echo "    marginal, con k = 100 y k = 1 000 hasta el tiempo equivalente 160"
    echo "    (1 % de E y 0,5 (COP/kWh)), y en los grupos libres tambien sin"
    echo "    acelerar (tolerancia estricta: 1e-3·E y 0,05). En teq 80 y 160, en"
    echo "    el 95 % de las horas, con cinco como minimo. 140 corridas; la que no"
    echo "    quepa en su tope se publica como cortada."
    if ! pedido 3; then
      no_pedido 3 m_a
    elif hay_tiempo "M-A"; then
      T_M="$(tope_de "$TOPE_M")"; con_tope "$T_M"
      corre "validacion_reposo_m_a" "$CONS/corre_mediciones.py" \
            --medicion medicion_regimenes --salida "$VAL/m_a_regimenes.json" \
            --procesos "$PROCS" --tope-total "$T_M" --horas "$VAL"
      ENVOLTURA=()
      anota "m_a"
      corre "validacion_reposo_m_a_veredicto" "$CONS/veredicto.py" \
            "$VAL/m_a_regimenes.json" --salida "$VAL/veredicto_m_a.txt"
      anota "m_a_veredicto"
    else
      CODIGOS+=("m_a=saltada"); SALTADAS+=("M-A")
    fi

    echo
    echo "--- 4/10 · M-B · con que regla reparte la dinamica entre vendedores"
    echo "    Veinte horas de E4 y diez de E5 con compradores cortos y Cesmag"
    echo "    vendiendo, con el costo del vendedor en su alternativa (su piso) y"
    echo "    en su costo nivelado, contra las tres reglas del nucleo."
    echo "    Aceptacion: |dP_ji| <= 1e-3·E (kWh) para la que gane. Decide D64."
    if ! pedido 4; then
      no_pedido 4 m_b
    elif hay_tiempo "M-B"; then
      T_M="$(tope_de "$TOPE_M")"; con_tope "$T_M"
      corre "validacion_reposo_m_b" "$CONS/corre_mediciones.py" \
            --medicion medicion_merito_vendedores --salida "$VAL/m_b_merito.json" \
            --procesos "$PROCS" --tope-total "$T_M" --horas "$VAL"
      ENVOLTURA=()
      anota "m_b"
      corre "validacion_reposo_m_b_veredicto" "$CONS/veredicto.py" \
            "$VAL/m_b_merito.json" --salida "$VAL/veredicto_m_b.txt"
      anota "m_b_veredicto"
    else
      CODIGOS+=("m_b=saltada"); SALTADAS+=("M-B")
    fi

    echo
    echo "--- 5/10 · M-C · la regla de «la suma no cabe», con los cuatro arranques"
    echo "    Las horas de ese regimen de E0 (28) y de CV2 (37), cada una desde"
    echo "    las dos ofertas (iguales y factible) por los dos arranques de"
    echo "    precios (sigma y medio): 260 corridas de las baratas."
    echo "    Aceptacion: el mismo reposo en los cuatro. Decide D53, que es el"
    echo "    rotulo de un regimen que pesa el 14 % de la energia."
    if ! pedido 5; then
      no_pedido 5 m_c
    elif hay_tiempo "M-C"; then
      T_M="$(tope_de "${TOPE_M_C:-7200}")"; con_tope "$T_M"
      corre "validacion_reposo_m_c" "$CONS/corre_mediciones.py" \
            --medicion medicion_suma_no_cabe --salida "$VAL/m_c_no_cabe.json" \
            --procesos "$PROCS" --tope-total "$T_M" --horas "$VAL"
      ENVOLTURA=()
      anota "m_c"
      corre "validacion_reposo_m_c_veredicto" "$CONS/veredicto.py" \
            "$VAL/m_c_no_cabe.json" --salida "$VAL/veredicto_m_c.txt"
      anota "m_c_veredicto"
    else
      CODIGOS+=("m_c=saltada"); SALTADAS+=("M-C")
    fi

    echo
    echo "--- 6/10 · M-D · la estabilidad del reposo (jacobiano en el reposo)"
    echo "    Segundos: no integra. Lee antes el residuo de cada hora, que dice"
    echo "    si ese punto es de reposo tambien para los multiplicadores."
    if ! pedido 6; then
      no_pedido 6 m_d
    else
      corre "validacion_reposo_m_d" "$CONS/medicion_estabilidad.py" \
            --horas "$VAL" --salida "$VAL/m_d_estabilidad.json" --por-regimen 10
      CODIGOS+=("m_d=${CODIGO_CORRE}")
    fi

    echo
    echo "--- 7/10 · M-E · sensibilidad a mu, y el censo de empates"
    if ! pedido 7; then
      no_pedido 7 m_e            # la sensibilidad a mu y el censo
    elif hay_tiempo "M-E (la sensibilidad a mu; el censo corre igual)"; then
      T_M="$(tope_de "${TOPE_M_E:-7200}")"; con_tope "$T_M"
      corre "validacion_reposo_m_e" "$CONS/corre_mediciones.py" \
            --medicion medicion_mu --salida "$VAL/m_e_mu.json" \
            --procesos "$PROCS" --tope-total "$T_M" --horas "$VAL"
      ENVOLTURA=()
      anota "m_e"
      corre "validacion_reposo_m_e_veredicto" "$CONS/veredicto.py" \
            "$VAL/m_e_mu.json" --salida "$VAL/veredicto_m_e.txt"
      anota "m_e_veredicto"
    else
      CODIGOS+=("m_e=saltada"); SALTADAS+=("M-E")
    fi
    for CASO in E0 K1; do
      if ! pedido 7; then break; fi
      ALM="$ALMACENES/$CASO/almacen"
      if [[ ! -d "$ALM" && "${SECO:-0}" != "1" ]]; then
        echo "  AVISO: no esta $ALM; el censo de empates de $CASO no se hace"
        continue
      fi
      corre "validacion_reposo_m_e_empates_${CASO}" "$CONS/medicion_mu.py" \
            --censo --almacen "$ALM" --caso "$CASO" --cobertura m1 --mu 1 \
            --salida "$VAL/m_e_empates_${CASO}.json"
      CODIGOS+=("m_e_empates_$CASO=${CODIGO_CORRE}")
    done

    echo
    echo "--- 8/10 · M-G · el caso publicado de Chacon"
    echo "    La prueba dorada va en las compuertas, sin cambio (7 de 7); aqui"
    echo "    van sus dos horas con el arnes, con las dos formas del jugador"
    echo "    virtual. Es la tabla de la comparacion con el articulo base."
    if ! pedido 8; then
      no_pedido 8 m_g            # M-G y la prueba dorada
    elif hay_tiempo "M-G (la dorada corre igual)"; then
      T_M="$(tope_de "${TOPE_M_G:-7200}")"; con_tope "$T_M"
      corre "validacion_reposo_m_g" "$CONS/corre_mediciones.py" \
            --medicion medicion_chacon --salida "$VAL/m_g_chacon.json" \
            --procesos "$PROCS" --tope-total "$T_M" --horas "$VAL"
      ENVOLTURA=()
      anota "m_g"
      corre "validacion_reposo_m_g_veredicto" "$CONS/veredicto.py" \
            "$VAL/m_g_chacon.json" --salida "$VAL/veredicto_m_g.txt"
      anota "m_g_veredicto"
    else
      CODIGOS+=("m_g=saltada"); SALTADAS+=("M-G")
    fi
    if pedido 8; then
      corre "validacion_reposo_m_g_dorada" -m pytest tests/golden_test_sofia.py \
            -q -rs -p no:cacheprovider
      CODIGOS+=("m_g_dorada=${CODIGO_CORRE}")
    fi

    echo
    echo "--- 9/10 · las dos horas lentas de la compuerta de la dinamica"
    if ! pedido 9; then
      no_pedido 9 horas_lentas
    elif [[ "$LENTAS" != "1" ]]; then
      echo "  LENTAS=$LENTAS: se saltan. Sus ordenes exactas estan en el"
      echo "  docstring de tests/gate_reposo_cero_dinamica.py."
    else
      echo "  Etapa 1, los cortes intermedios (t = 0,5 y t = 1 de las horas 874"
      echo "  y 4766). De ahi sale la estimacion de lo que costaria t = 5:"
      echo "  con p = ln(N(1)/N(0,5))/ln 2, son N(1)·5^p evaluaciones."
      for HORA in 874 4766; do
        for CORTE in "0.5:5000:t05" "1:10000:t1"; do
          H="${CORTE%%:*}"; RESTO="${CORTE#*:}"
          TOPE_H="${RESTO%%:*}"; ETQ="${RESTO##*:}"
          if ! hay_tiempo "la hora $HORA hasta t = $H"; then
            CODIGOS+=("gate_${HORA}_${ETQ}=saltada")
            SALTADAS+=("gate_${HORA}_${ETQ}")
            continue
          fi
          export HORIZONTE_COMPUERTA="$H"
          TOPE_COMPUERTA_S="$(tope_de "$TOPE_H")"
          export TOPE_COMPUERTA_S
          echo "    hora $HORA: HORIZONTE_COMPUERTA=$H TOPE_COMPUERTA_S=$TOPE_COMPUERTA_S"
          corre "validacion_reposo_gate_${HORA}_${ETQ}" -m pytest \
                tests/gate_reposo_cero_dinamica.py -k "lenta and $HORA" \
                -s -q -rs -p no:cacheprovider
          CODIGOS+=("gate_${HORA}_${ETQ}=${CODIGO_CORRE}")
          unset HORIZONTE_COMPUERTA TOPE_COMPUERTA_S
        done
      done
      if [[ "${ETAPA2:-0}" == "1" ]]; then
        echo "  Etapa 2, la compuerta completa (t = 5), con el tope que el"
        echo "  operador estimo de la etapa 1."
        for HORA in 874 4766; do
          VART="TOPE_$HORA"
          export TOPE_COMPUERTA_S="${!VART:-0}"
          if [[ "$TOPE_COMPUERTA_S" == "0" ]]; then
            echo "  $HORA: falta TOPE_$HORA (segundos, 1,4 veces lo estimado);"
            echo "  no se lanza."
            unset TOPE_COMPUERTA_S
            continue
          fi
          if ! hay_tiempo "la compuerta entera de la hora $HORA"; then
            CODIGOS+=("gate_${HORA}=saltada"); SALTADAS+=("gate_${HORA}")
            unset TOPE_COMPUERTA_S
            continue
          fi
          TOPE_COMPUERTA_S="$(tope_de "$TOPE_COMPUERTA_S")"
          export TOPE_COMPUERTA_S
          echo "    hora $HORA: compuerta entera, TOPE_COMPUERTA_S=$TOPE_COMPUERTA_S"
          corre "validacion_reposo_gate_${HORA}" -m pytest \
                tests/gate_reposo_cero_dinamica.py -k "lenta and $HORA" \
                -s -q -p no:cacheprovider
          CODIGOS+=("gate_${HORA}=${CODIGO_CORRE}")
          unset TOPE_COMPUERTA_S
        done
      else
        echo "  Etapa 2 (la compuerta entera, t = 5) NO se lanza sola: su tope"
        echo "  sale de lo que la etapa 1 midio. Cuando tengas la estimacion:"
        echo "    ETAPA2=1 TOPE_874=<s> TOPE_4766=<s> LENTAS=1 \\"
        echo "      bash $0 validacion_reposo"
        echo "  (o las dos ordenes sueltas del docstring de la compuerta, que"
        echo "  pueden correr a la vez)."
      fi
    fi

    echo
    echo "--- 10/10 · la recogida"
    bash "$0" recoger validacion_reposo
    echo
    # m3: con algo saltado o incompleto, la noche NO esta completa.
    # m-a de la re-revision 2: un paso que salio con un codigo de fallo (1, 2,
    # 3 o cualquier otro distinto de 0 y de 4) tampoco deja la noche completa.
    # «seco», «saltada», «incompleta» y 0 no son fallos; tampoco «no_pedido» ni
    # «ya_estaba» (tarea 4d: PASOS), que no son numeros.
    FALLOS=()
    for par in "${CODIGOS[@]}"; do
      valor="${par#*=}"
      if [[ "$valor" =~ ^[0-9]+$ && "$valor" != "0" && "$valor" != "4" ]]; then
        FALLOS+=("$par")
      fi
    done
    INCOMPLETA=0
    if [[ ${#SALTADAS[@]} -gt 0 || ${#INCOMPLETAS[@]} -gt 0 ]]; then
      INCOMPLETA=1
    fi
    # Con PASOS, el cierre habla solo de los pasos pedidos.
    ALCANCE=""
    if [[ ${#NO_PEDIDOS[@]} -gt 0 ]]; then
      ALCANCE=" EN LOS PASOS PEDIDOS (PASOS=\"$PASOS\")"
    fi
    if [[ ${#FALLOS[@]} -gt 0 && $INCOMPLETA -eq 1 ]]; then
      echo "=== VALIDACION DEL REPOSO CON FALLOS E INCOMPLETA${ALCANCE} ==="
    elif [[ ${#FALLOS[@]} -gt 0 ]]; then
      echo "=== VALIDACION DEL REPOSO CON FALLOS${ALCANCE} ==="
    elif [[ $INCOMPLETA -eq 1 ]]; then
      echo "=== VALIDACION DEL REPOSO INCOMPLETA${ALCANCE} ==="
    else
      echo "=== VALIDACION DEL REPOSO COMPLETA${ALCANCE} ==="
    fi
    echo "  codigos de salida: ${CODIGOS[*]}"
    if [[ ${#NO_PEDIDOS[@]} -gt 0 ]]; then
      echo "  no pedidos (PASOS=\"$PASOS\"): ${NO_PEDIDOS[*]}"
      echo "  No son fallos ni saltos por el tope: esta vez no se pidieron. Sus"
      echo "  resultados, si los hay, son los de la corrida que los pidio."
    fi
    if [[ ${#FALLOS[@]} -gt 0 ]]; then
      echo "  === CON FALLOS: ${FALLOS[*]} ==="
      echo "  (124 o 137 en una medicion: la corto su esperador con tope; el"
      echo "  gestor del pool se colgo o no atendio a su propio tope)"
      echo "  Mira el registro de cada uno en $LOGS/validacion_reposo_<paso>_<fecha>.log"
      echo "  antes de leer ningun veredicto que dependa de el."
    fi
    echo "  tiempo de pared: $(( $(date +%s) - INICIO_GLOBAL )) s de un tope global de $TOPE_GLOBAL s"
    if [[ ${#SALTADAS[@]} -gt 0 ]]; then
      echo "  === SALTADAS POR EL TOPE GLOBAL: ${SALTADAS[*]} ==="
      echo "  Se corren sueltas con las ordenes de MONTAJE_SERVIDOR.md (seccion"
      echo "  de la validacion del reposo), o otra noche con TOPE_GLOBAL_S mayor."
    fi
    if [[ ${#INCOMPLETAS[@]} -gt 0 ]]; then
      echo "  === INCOMPLETAS (quedaron corridas del plan sin hacer): ${INCOMPLETAS[*]} ==="
      echo "  Su registro dice con que --desde se retoman; veredicto.py acepta los"
      echo "  dos JSON juntos y avisa «MEDICION INCOMPLETA: N de M» mientras falten."
    fi
    if [[ ${#SELECCION_MAL[@]} -gt 0 ]]; then
      # m1: las mediciones corrieron igual con esa muestra; hay que saberlo.
      echo "  === AVISO: la seleccion de horas de ${SELECCION_MAL[*]} salio con 1 ==="
      echo "  Descarto mas del 30 % de las horas examinadas de algun grupo, o dejo"
      echo "  un grupo sin horas, y las mediciones corrieron igual con esa muestra."
      echo "  Mira $LOGS/validacion_reposo_horas_<caso>_<fecha>.log antes de leer"
      echo "  ningun veredicto de esos casos."
    fi
    echo "  Lee, en este orden:"
    echo "    1. $LOGS/validacion_reposo_lado_derecho_<fecha>.log: el arnes no"
    echo "       se desvio del motor (si no, nada de lo demas vale);"
    echo "    2. $VAL/veredicto_m_a.txt: que regimen queda como reposo"
    echo "       verificado y cual como regla declarada. Es la tabla que se"
    echo "       lleva a la tesis;"
    echo "    3. $VAL/veredicto_m_b.txt: que regla de despacho reproduce la"
    echo "       dinamica (D64);"
    echo "    4. $VAL/veredicto_m_c.txt: si los cuatro arranques dan el mismo"
    echo "       reposo en «la suma no cabe» (D53);"
    echo "    5. el registro de M-D: estabilidad, con su residuo por hora;"
    echo "    6. $VAL/veredicto_m_e.txt y m_e_empates_<caso>.json: si mu solo"
    echo "       cambia la velocidad, y cuanta energia esta en empate;"
    echo "    7. $VAL/veredicto_m_g.txt: el caso publicado, para el articulo."
    echo "  Una medicion que no converge no es un fallo: ese regimen se publica"
    echo "  como regla declarada, y eso es lo que decide esta noche."
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
      arranque)
        # H-85: el almacen de cada caso con cada arranque, y el CSV hora a
        # hora de la comparacion de cada caso (un fichero, no una carpeta).
        for par in "${CASOS_ARRANQUE[@]}"; do
          for REGLA in "${REGLAS_ARRANQUE[@]}"; do
            ESPERADOS+=("SALIDAS_SERVIDOR/arranque/${par%%:*}_${REGLA}/almacen")
          done
          ESPERADOS+=("SALIDAS_SERVIDOR/arranque/compara_arranque_${par%%:*}.csv")
        done
        ;;
      convergencia)
        # H-86: el almacen de cada caso con cada configuracion, los CSV hora a
        # hora de las comparaciones dos a dos, y el censo del costo.
        for par in "${CASOS_CONVERGENCIA[@]}"; do
          CASO="${par%%:*}"
          for cfg in "${CONFIGS_CONVERGENCIA[@]}"; do
            ESPERADOS+=("SALIDAS_SERVIDOR/convergencia/${CASO}_${cfg%%:*}/almacen")
          done
          for pc in "${PARES_CONVERGENCIA[@]}"; do
            ESPERADOS+=("SALIDAS_SERVIDOR/convergencia/compara_arranque_${CASO}_${pc%%:*}_vs_${pc#*:}.csv")
          done
        done
        ESPERADOS+=("SALIDAS_SERVIDOR/convergencia/censo_convergencia.csv")
        ;;
      matriz_reposo)
        # D48: el almacen de cada caso y el registro de su compuerta de salida
        # (el mas reciente: corre() le pone fecha al nombre), las figuras del
        # foro de E0 y, si habia matriz vieja con que comparar, el CSV de la
        # comparacion.
        for par in "${CASOS_MATRIZ[@]}"; do
          CASO="${par%%:*}"
          ESPERADOS+=("$MATRIZ_REPOSO/$CASO/almacen")
          ESPERADOS+=("$(ultimo_registro "matriz_reposo_compuerta_${CASO}")")
        done
        ESPERADOS+=("$MATRIZ_REPOSO/figuras_foro")
        casos_con_matriz_vieja
        if [[ ${#VIEJOS[@]} -gt 0 ]]; then
          ESPERADOS+=("$MATRIZ_REPOSO/compara_matriz_reposo.csv")
        else
          echo "  sin matriz vieja en $MATRIZ_VIEJA: la comparacion no se espera (se hace en casa)"
        fi
        ;;
      barrido_sigma)
        # D50: lo que exista de cada sigma y cada caso, con aviso de lo que
        # falte: el almacen y el registro de su compuerta de salida.
        valida_sigmas
        for S in $SIGMAS_BARRIDO; do
          ETQ="$(etiqueta_sigma "$S")"
          for par in "${CASOS_MATRIZ[@]}"; do
            CASO="${par%%:*}"
            ESPERADOS+=("$MATRIZ_REPOSO/${CASO}_sigma${ETQ}/almacen")
            ESPERADOS+=("$(ultimo_registro "barrido_compuerta_sigma${ETQ}_${CASO}")")
          done
        done
        ;;
      validacion_reposo)
        # M-A a M-G: el JSON de cada medicion y el veredicto de las que lo
        # tienen. La muestra de horas de cada caso se espera solo si su almacen
        # estaba (sin el, la medicion corre con sus horas de respaldo o no
        # corre), de modo que aqui se avisa de lo que falte pero no se aborta:
        # recoger lo que hay sirve tambien cuando algo no corrio.
        # Tarea 4d: con PASOS, solo se espera lo de los pasos pedidos (la
        # muestra de horas y el registro del arnes, siempre).
        _pasos=" ${PASOS:-1 2 3 4 5 6 7 8 9 10} "
        _pasos="${_pasos//,/ }"
        _pide() { [[ "$_pasos" == *" $1 "* ]]; }
        VR="SALIDAS_SERVIDOR/validacion_reposo"
        for CASO in E0 K1 E4 E5 CV2; do
          ESPERADOS+=("$VR/horas_${CASO}.json")
        done
        if _pide 3; then ESPERADOS+=("$VR/m_a_regimenes.json" "$VR/veredicto_m_a.txt"); fi
        if _pide 4; then ESPERADOS+=("$VR/m_b_merito.json" "$VR/veredicto_m_b.txt"); fi
        if _pide 5; then ESPERADOS+=("$VR/m_c_no_cabe.json" "$VR/veredicto_m_c.txt"); fi
        if _pide 6; then
          ESPERADOS+=("$VR/m_d_estabilidad.json")
          ESPERADOS+=("$(ultimo_registro "validacion_reposo_m_d")")
        fi
        if _pide 7; then
          ESPERADOS+=("$VR/m_e_mu.json" "$VR/veredicto_m_e.txt")
          for CASO in E0 K1; do
            ESPERADOS+=("$VR/m_e_empates_${CASO}.json")
          done
        fi
        if _pide 8; then ESPERADOS+=("$VR/m_g_chacon.json" "$VR/veredicto_m_g.txt"); fi
        ESPERADOS+=("$(ultimo_registro "validacion_reposo_lado_derecho")")
        if [[ "$_pasos" != " 1 2 3 4 5 6 7 8 9 10 " ]]; then
          echo "  PASOS=\"${PASOS}\": solo se espera lo de esos pasos"
        fi
        ;;
      *)
        echo "  recoger: corrida desconocida '$DE'; use matriz, oficial, arranque, convergencia, matriz_reposo, barrido_sigma o validacion_reposo"
        exit 2
        ;;
    esac
    echo "  recogiendo la corrida: $DE"
    # H-85: -e y no -d, porque `arranque` espera tambien ficheros (los CSV
    # de la comparacion); para las carpetas de `matriz` y `oficial` es lo
    # mismo.
    for esperado in "${ESPERADOS[@]}"; do
      if [[ -e "$esperado" ]]; then
        echo "    esta: $esperado"
      else
        echo "  AVISO: no esta $esperado"
      fi
    done
    # D48 (revision de 4b, menor 4): en `matriz_reposo` y `barrido_sigma`,
    # estar no basta. La carpeta de figuras la crea el lanzador ANTES de
    # dibujar, de modo que existe aunque la figura se caiga; y el registro de
    # una compuerta de salida existe aunque falle. Se avisa en voz alta, pero
    # no se aborta: recoger lo que hay sirve tambien cuando algo fallo.
    if [[ "$DE" == "matriz_reposo" || "$DE" == "barrido_sigma" ]]; then
      for esperado in "${ESPERADOS[@]}"; do
        if [[ -d "$esperado" && "$esperado" == */figuras_foro ]]; then
          shopt -s nullglob dotglob
          contenido=("$esperado"/*)
          shopt -u nullglob dotglob
          if [[ ${#contenido[@]} -eq 0 ]]; then
            echo "  === AVISO: $esperado esta VACIA: las figuras no salieron ==="
          fi
        fi
        if [[ -f "$esperado" && "$esperado" == */*compuerta_*.log ]]; then
          if ! grep -qE "^COMPUERTA MATRIZ REPOSO .* EN VERDE" "$esperado"; then
            echo "  === AVISO: la compuerta de salida NO termino EN VERDE: $esperado ==="
          fi
        fi
      done
    fi
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
    # Una carpeta aparece en la lista como «ruta/» y un fichero como «ruta»
    # a secas: se aceptan las dos formas (H-85, los CSV de `arranque`).
    # Los puntos de la ruta van como «[.]», para que no casen con cualquier
    # caracter en la expresion regular.
    for esperado in "${ESPERADOS[@]}"; do
      [[ -e "$esperado" ]] || continue
      if ! grep -qE "^${esperado//./[.]}(/|\$)" <<<"$LISTA"; then
        echo "  AVISO: $esperado esta en disco pero NO en el tar"
      fi
    done
    echo
    echo "  Traelo de vuelta y descomprimelo en la raiz del repositorio."
    ;;

  *)
    echo "accion desconocida: $ACCION"; exit 2 ;;
esac
