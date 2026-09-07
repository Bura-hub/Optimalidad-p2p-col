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

ACCION="${1:?falta la accion: entorno|compuertas|caso|competencia|eficiencia|todo|recoger}"

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

# Corre una sonda con su log fechado y avisa del codigo de salida. No usa
# tuberias: una tuberia retiene la salida y el log se queda vacio hasta el
# final, que es justo lo que no se quiere en una corrida larga.
corre() {
  local nombre="$1"; shift
  local log="$LOGS/${nombre}_$(marca).log"
  echo "  -> $nombre   (log: $log)"
  if "$PY" -W ignore "$@" > "$log" 2>&1; then
    echo "     ok"
  else
    echo "     FALLA (codigo $?); mira el log"
  fi
  tail -n 12 "$log" | sed 's/^/     /'
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
    echo "  Comprueba que MTE_ROOT apunta a MedicionesMTE/ antes de medir:"
    echo "    export MTE_ROOT=/ruta/a/MedicionesMTE"
    ;;

  compuertas)
    echo "Compuertas, antes de dar por buena ninguna medicion"
    for t in golden_test_sofia gate_cal47_solucionador \
             gate_c138_bienestar_comprador; do
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

  recoger)
    DEST="modelo_base/resultados_$(marca).tar.gz"
    tar czf "$DEST" "$SALIDAS" "$LOGS" 2>/dev/null || true
    echo "  resultados en $DEST"
    echo "  $(tar tzf "$DEST" | wc -l) ficheros"
    echo
    echo "  Traelo de vuelta y descomprimelo en la raiz del repositorio."
    ;;

  *)
    echo "accion desconocida: $ACCION"; exit 2 ;;
esac
