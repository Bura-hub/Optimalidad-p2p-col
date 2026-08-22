#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# GSA sobre datos reales — lanzador del servidor
#
#   bash gsa_real/run_servidor.sh entorno                 <- UNA vez, primero
#   bash gsa_real/run_servidor.sh calibrar M1 full 128
#   bash gsa_real/run_servidor.sh correr   M1 full 128 1800
#   bash gsa_real/run_servidor.sh reanudar M1 full 128 1800
#   bash gsa_real/run_servidor.sh analizar M1 full 128
#
# El 5o argumento es SIEMPRE el timeout en segundos, y solo lo usan `correr` y
# `reanudar`. La SEMILLA se pasa por entorno y por defecto es 42:
#
#   SEMILLA=7 bash gsa_real/run_servidor.sh correr M1 full 128 1800
#
# Antes, `analizar` reinterpretaba ese 5o argumento como semilla: copiar el
# comando de `correr` y cambiarle la accion buscaba un fichero `_s1800`
# inexistente. Un mismo hueco no puede significar dos cosas.
#
# Se situa solo en la raiz del repositorio: da igual desde donde se invoque.
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."          # raiz del repositorio

ACCION="${1:?falta la accion: entorno|calibrar|correr|reanudar|analizar}"
COB="${2:-M1}"
HOR="${3:-full}"
NBASE="${4:-128}"
TIMEOUT="${5:-1800}"                             # solo para correr|reanudar
SEMILLA="${SEMILLA:-42}"

# Interprete: preferir el del entorno virtual si existe, luego python3.
if [[ -x .venv/bin/python ]]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "ERROR: no hay interprete de Python en el PATH"; exit 1
fi

export MTE_ROOT="${MTE_ROOT:-$PWD/MedicionesMTE_v3}"
# Sin esto, un caracter no-ASCII bajo locale C mata la evaluacion y la corrida
# entera devuelve NaN. Es la clase de fallo del incidente CAL-28b.
export PYTHONIOENCODING=utf-8
# El nucleo ya se paraleliza por procesos; dejar que BLAS abra hilos dentro de
# cada uno satura la maquina y ralentiza el conjunto.
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

mkdir -p gsa_real/salidas

if [[ ! -d "$MTE_ROOT" ]]; then
  echo "ERROR: no existe MTE_ROOT=$MTE_ROOT"
  echo "  export MTE_ROOT=/home/brayan_lopez/sistemabl/MedicionesMTE_v3"
  exit 1
fi
if [[ ! -f main_simulation.py ]]; then
  echo "ERROR: no parece la raiz del repositorio (falta main_simulation.py)"
  exit 1
fi

# Preflight. `py_compile` NO basta: solo mira sintaxis y deja pasar un
# ImportError, que es como se cuela un nombre que no existe en la stdlib. Se
# ejecuta `--help`, que resuelve todos los imports sin hacer trabajo.
for S in 1_calibrar 2_correr_gsa 3_analizar; do
  if ! "$PY" "gsa_real/${S}.py" --help >/dev/null 2>"/tmp/pre_${S}.err"; then
    echo "ERROR: gsa_real/${S}.py no arranca:"
    cat "/tmp/pre_${S}.err"
    exit 1
  fi
done
if ! "$PY" -c "import sys; sys.path.insert(0,'gsa_real'); import comun" ; then
  echo "ERROR: gsa_real/comun.py no importa. Abortado."
  exit 1
fi

TAG="${COB}_${HOR//:/-}"
# `nproc` de coreutils toma OMP_NUM_THREADS como TECHO de lo que reporta, y
# arriba lo hemos puesto a 1 para que BLAS no abra hilos dentro de cada proceso.
# Llamarlo tal cual devolvia 1 en una maquina de 32 nucleos, y la corrida se
# habria hecho con un solo worker: diez dias en vez de ocho horas, sin que nada
# pareciera roto. Se desactivan las dos variables SOLO para esta llamada, de
# modo que siga respetando la mascara de afinidad —que si es un limite real—
# pero no nuestro propio ajuste de BLAS.
NUCLEOS="$(env -u OMP_NUM_THREADS -u OMP_THREAD_LIMIT nproc)"
# Override por entorno: tras un POOL ROTO por OOM el consejo es bajarlo, y
# sin esto no habia forma de obedecerlo sin editar el guion.
#   WORKERS=6 bash gsa_real/run_servidor.sh reanudar M1 full 128 1800
WORKERS="${WORKERS:-$(( NUCLEOS > 2 ? NUCLEOS - 2 : 1 ))}"

# `--help` tampoco basta: no ejecuta el cuerpo de main(), donde vive todo lo que
# puede desajustarse entre modulos (firmas, desempaquetados, claves del cache).
#
# `--verificar` recorre ese camino ENTERO —carga, huellas, .meta.json, pool
# anidado con su timeout, escritura del punto de control, codigos de salida—
# sustituyendo unicamente la resolucion del EMS. Cuesta segundos.
#
# Es deliberado que NO reevalue el modelo: de eso se encarga el paso 1 con cinco
# sondas reales. Una version anterior de este preflight corria 7 evaluaciones
# reales secuenciales, que sobre `full` son cerca de DOS HORAS antes de arrancar.
if [[ "$ACCION" == "correr" || "$ACCION" == "reanudar" ]]; then
  echo "preflight: verificando la orquestacion (${COB}/${HOR})..."
  VTAG="${TAG}_n1_s999_VERIF"
  VLOG="gsa_real/salidas/verif_${TAG}.log"
  rm -f "gsa_real/salidas/muestras_${VTAG}."*
  if ! "$PY" -u gsa_real/2_correr_gsa.py \
        --cobertura "$COB" --horizonte "$HOR" --n-base 1 --semilla 999 \
        --timeout 300 --workers 2 --forzar --verificar > "$VLOG" 2>&1; then
    echo "ERROR: la verificacion FALLO. El camino real esta roto:"
    echo "---------------------------------------------------------------"
    tail -30 "$VLOG"
    exit 1
  fi
  N_VER="$(( $(wc -l < "gsa_real/salidas/muestras_${VTAG}.csv") - 1 ))"
  if [[ "$N_VER" -ne 7 ]]; then
    echo "ERROR: la verificacion escribio $N_VER filas y esperaba 7."
    tail -30 "$VLOG"; exit 1
  fi
  echo "preflight OK: 7/7 filas por el camino real (sin resolver el EMS)"
  rm -f "gsa_real/salidas/muestras_${VTAG}."* "$VLOG"
fi

echo "raiz     : $PWD"
echo "python   : $PY  ($("$PY" -c 'import sys; print(sys.version.split()[0])'))"
echo "MTE_ROOT : $MTE_ROOT"
echo "arranque : $("$PY" -c 'import multiprocessing as m; print(m.get_start_method())')"
echo "nucleos  : $NUCLEOS  (usando $WORKERS)"
echo "accion   : $ACCION  cobertura=$COB horizonte=$HOR n_base=$NBASE semilla=$SEMILLA"
echo

case "$ACCION" in
  entorno)
    # Comprobacion de que el servidor esta listo. Se corre UNA vez, antes de
    # todo lo demas: cada cosa que falla aqui cuesta segundos, y descubierta a
    # mitad de una corrida de 17 h cuesta la corrida.
    FALLOS=0
    echo "── dependencias de Python ─────────────────────────────────────────"
    for MOD in numpy pandas scipy SALib; do
      # SALib no expone __version__ en el paquete raiz: se pregunta al gestor.
      V="$("$PY" -c "
import importlib, importlib.metadata as md
importlib.import_module('$MOD')
try:    print(md.version('$MOD'))
except Exception: print(getattr(importlib.import_module('$MOD'),'__version__','?'))" 2>/dev/null)" \
        && echo "  OK    $MOD $V" \
        || { echo "  FALTA $MOD  ->  $PY -m pip install -r requirements.txt"; FALLOS=$((FALLOS+1)); }
    done

    echo "── modulos del proyecto (los 20 que carga una evaluacion) ─────────"
    if "$PY" - <<'PYEOF' 2>/tmp/gsa_ent.err
import sys; sys.path.insert(0, ".")
from core.ems_p2p import EMSP2P, AgentParams, GridParams, SolverParams
from scenarios import run_comparison
import core.replicator_sellers
from data.xm_data_loader import MTEDataLoader
from data.preprocessing import PAPER_METER_DEMAND_CONFIG
from data.xm_prices import get_pi_bolsa
from data.cedenar_tariff import community_effective_pi_gs, pi_gs_per_agent_hourly
PYEOF
    then echo "  OK    el cierre de imports esta completo"
    else echo "  ROTO  faltan modulos del repo:"; sed 's/^/        /' /tmp/gsa_ent.err | tail -6; FALLOS=$((FALLOS+1)); fi

    echo "── datos ──────────────────────────────────────────────────────────"
    N_CSV="$(find "$MTE_ROOT" -name '*.csv' 2>/dev/null | wc -l)"
    if [[ "$N_CSV" -gt 0 ]]; then
      echo "  OK    MTE_ROOT con $N_CSV CSV ($(du -sh "$MTE_ROOT" 2>/dev/null | cut -f1))"
      for INST in Udenar Mariana UCC HUDN Cesmag; do
        [[ -d "$MTE_ROOT/$INST" ]] || { echo "  FALTA $MTE_ROOT/$INST"; FALLOS=$((FALLOS+1)); }
      done
    else
      echo "  ROTO  MTE_ROOT sin CSV: $MTE_ROOT"; FALLOS=$((FALLOS+1))
    fi
    for F in data/tarifas_cedenar_mensual.csv data/precios_bolsa_xm_api.csv \
             data/precios_escasez_creg.csv data/mem_costs_no_regulado.csv; do
      [[ -f "$F" ]] && echo "  OK    $F" \
        || { echo "  FALTA $F (viene del repo: revisa el clon)"; FALLOS=$((FALLOS+1)); }
    done
    REF="validacion_convergencia/salidas/sensibilidad/sobol_intervalos.csv"
    if [[ -f "$REF" ]]; then echo "  OK    $REF"
    else
      # No es fatal —el analisis lo detecta y omite la comparacion— pero SIN
      # ella se pierde el contraste con el GSA sintetico, que es el motivo de
      # todo el ejercicio.
      echo "  AVISO $REF ausente: no habra comparacion con el sintetico."
    fi

    echo "── maquina ────────────────────────────────────────────────────────"
    echo "  nucleos    $NUCLEOS   (el lanzador usaria $WORKERS workers)"
    echo "  procesos   ~$(( 2 * WORKERS + 1 )) en el arbol; dimensiona por RAM"
    # `|| true` en las dos: son informativas, y con `set -e` + `pipefail` una
    # tuberia cuyo primer mandato no exista —`free` no esta en todas partes—
    # abortaba la verificacion entera justo antes de emitir el veredicto.
    { free -g 2>/dev/null | awk '/^Mem:/{printf "  RAM        %s GB total, %s GB disponible\n",$2,$7}'; } || true
    { df -h . 2>/dev/null | awk 'NR==2{printf "  disco      %s libre en %s\n",$4,$6}'; } || true
    echo "  arranque   $("$PY" -c 'import multiprocessing as m; print(m.get_start_method())')"

    echo
    if [[ "$FALLOS" -eq 0 ]]; then
      echo "ENTORNO LISTO. Siguiente:"
      echo "  bash gsa_real/run_servidor.sh calibrar $COB $HOR $NBASE"
    else
      echo "ENTORNO NO LISTO: $FALLOS problema(s) arriba. No lances nada todavia."
      exit 1
    fi
    ;;

  calibrar)
    "$PY" -u gsa_real/1_calibrar.py --cobertura "$COB" --horizonte "$HOR" \
        --n-base-objetivo "$NBASE" --workers "$WORKERS" \
        2>&1 | tee "gsa_real/salidas/calibrar_${TAG}.log"
    ;;

  correr|reanudar)
    LOG="gsa_real/salidas/run_gsa_${TAG}_n${NBASE}_s${SEMILLA}.log"
    LOCK="gsa_real/salidas/.lock_${TAG}_n${NBASE}_s${SEMILLA}"
    # Dos corridas simultaneas sobre el mismo CSV lo truncan y lo reescriben a
    # la vez: quedan indices duplicados y el CSV entero deja de ser analizable.
    if [[ -f "$LOCK" ]] && kill -0 "$(cat "$LOCK")" 2>/dev/null; then
      echo "ERROR: ya hay una corrida viva con este tag (PID $(cat "$LOCK"))."
      echo "  Si estas seguro de que murio: rm $LOCK"
      exit 1
    fi

    EXTRA=""
    [[ "$ACCION" == "reanudar" ]] && EXTRA="--reanudar" || true
    # Marca de inicio: la deteccion de abajo solo mira lo escrito DESPUES de
    # esta linea. Sin ella, al reanudar el `arrancando` de la tanda anterior
    # seguia en el log (se abre en modo append) y el lanzador daba por vivo un
    # proceso que acababa de morir.
    MARCA="=== lanzamiento $(date -u +%Y-%m-%dT%H:%M:%SZ) accion=$ACCION ==="
    echo "$MARCA" >> "$LOG"
    DESDE="$(wc -l < "$LOG")"
    nohup "$PY" -u gsa_real/2_correr_gsa.py \
        --cobertura "$COB" --horizonte "$HOR" --n-base "$NBASE" \
        --semilla "$SEMILLA" --timeout "$TIMEOUT" --workers "$WORKERS" $EXTRA \
        >> "$LOG" 2>&1 &
    PID=$!
    echo "$PID" > "$LOCK"
    # La carga del dataset tarda decenas de segundos: comprobar a los 5 s ve el
    # proceso vivo aunque vaya a morir leyendo. Se vigila hasta que imprima la
    # linea de arranque del bucle, o 180 s.
    ARRANCO=0
    for _ in $(seq 1 90); do
      sleep 2
      if tail -n "+$((DESDE + 1))" "$LOG" 2>/dev/null | grep -q "arrancando"; then
        ARRANCO=1; break
      fi
      if ! kill -0 "$PID" 2>/dev/null; then break; fi
    done
    if [[ "$ARRANCO" -ne 1 ]] && ! kill -0 "$PID" 2>/dev/null; then
      rm -f "$LOCK"
      echo "EL PROCESO MURIO AL ARRANCAR. Ultimas lineas del log:"
      echo "---------------------------------------------------------------"
      tail -30 "$LOG"
      exit 1
    fi
    if [[ "$ARRANCO" -ne 1 ]]; then
      echo "AVISO: a los 180 s aun no habia arrancado el bucle, pero el proceso"
      echo "       sigue vivo (PID $PID). Vigilar el log."
    fi
    echo "corriendo en segundo plano, PID $PID"
    echo "log: $LOG"
    echo
    echo "  seguir    : tail -f $LOG"
    echo "  progreso  : wc -l gsa_real/salidas/muestras_${TAG}_n${NBASE}_s${SEMILLA}.csv"
    echo "  recargas  : grep -c '\[xm_csv\]' gsa_real/salidas/workers/*.log  # deberia ser ~0"
    # Cada worker externo lanza a su vez un proceso hijo que es el que calcula
    # (asi se impone el timeout por muestra): el arbol tiene 2*WORKERS+1
    # procesos, no WORKERS. La CPU la consumen solo los nietos, pero la RAM la
    # ocupan los 2*WORKERS interpretes con numpy/scipy cargados.
    echo "  procesos  : ~$(( 2 * WORKERS + 1 )) en total ($WORKERS calculando)"
    # `kill $PID` deja vivos a los nietos, que siguen comiendo un nucleo cada uno.
    echo "  detener   : pkill -f 2_correr_gsa.py && rm -f $LOCK"
    echo "  huerfanos : pgrep -f 2_correr_gsa.py   # tras un OOM, revisar y matar"
    ;;

  analizar)
    "$PY" -u gsa_real/3_analizar.py \
        --muestras "muestras_${TAG}_n${NBASE}_s${SEMILLA}.csv" \
        2>&1 | tee "gsa_real/salidas/analizar_${TAG}_n${NBASE}_s${SEMILLA}.log"
    ;;

  *)
    echo "accion desconocida: $ACCION"; exit 1 ;;
esac
