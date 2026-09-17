# Generadores de literales de las pruebas

Guiones que calcularon, una sola vez, los literales hexadecimales que dos pruebas guardan escritos. Las pruebas no los importan ni los ejecutan: sirven para saber de dónde salió cada cifra y para regenerarla si hace falta. `pytest` no los recoge (`python_files = test_*.py`).

| Guion | Qué produce | Prueba que lo usa | Lee |
|---|---|---|---|
| `genera_literales.py` | Entradas de las nueve horas de E0 de la primera entrega (huella de esas nueve, `54b02e7841762414`) | `tests/test_reposo_mercado.py` | almacenes de la matriz del 2026-09-15 |
| `literales_ronda1.py` | Entradas de las cinco horas de la ronda de arreglos (E4 133, 5631 y 5632; E0 4766 y 226), en `literales_ronda1.txt` | `tests/test_reposo_mercado.py` | los mismos almacenes |
| `verifica_huella.py` | Comprueba al bit los catorce literales contra los almacenes e imprime la huella vigente, `fe4488168ced426c` | `tests/test_reposo_mercado.py` | los mismos almacenes |
| `literales_base.py` | Resultado de una hora por las vías alternada y acoplada, con y sin pisos por vendedor, calculado con el código base (commit `a392cbd`) | `tests/test_reposo_motor.py` | la hora sintética de C-165 |

## Requisitos

- Los tres de la tarea 1 leen parquet: necesitan un Python con `pyarrow`, que el `.venv` de la máquina de trabajo no trae. Los almacenes están en `SALIDAS_SERVIDOR/entrega_matriz_2026-09-15/SALIDAS_SERVIDOR/matriz/`.
- `literales_base.py` necesita el código base aparte, extraído de solo lectura:

  ```
  git archive a392cbd core data | tar -x -C <carpeta>
  python -u tests/literales/literales_base.py <carpeta>
  ```

  Sus literales valen al bit en Windows con las versiones de numpy y scipy de `requirements-lock.txt` (H-84). En ese entorno la prueba corre y falla si no coinciden; fuera de él se salta con su motivo.

## Procedencia

- Los tres primeros son de la tarea 1 del reposo (2026-09-16 y 17).
- `literales_base.py` es de la tarea 2 (2026-09-17).

Se trajeron del borrador de la sesión sin cambiar su lógica: solo la raíz del repositorio pasa a calcularse desde el propio fichero.
