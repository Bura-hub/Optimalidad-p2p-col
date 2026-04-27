# Diseño — Re-ejecución de GSA Sobol-Saltelli sobre MedicionesMTE_v3

**Autor:** Brayan S. Lopez-Mendez
**Fecha:** 2026-04-26
**Actividad de la propuesta:** 4.1 (Análisis de sensibilidad mediante simulaciones)
**Modo de trabajo:** directo en `main`, sin worktree

---

## Contexto

El GSA Sobol-Saltelli (n_base = 64, 7 parámetros, 3 outputs, 1024 evaluaciones) se ejecutó por primera vez el 2026-04-17 sobre datos previos a `MedicionesMTE_v3`. Tras la migración a v3 (commit `cdb11e9`, horizonte de 6144 h, 256 días, Abr–Dic 2025), el GSA quedó pendiente de re-ejecución para que los índices de sensibilidad documentados en `Documentos/notas_modelo_tesis.md` § A.7 reflejen los datos efectivamente usados en el resto de la tesis.

El trabajo previo sin commitear ya prepara la re-ejecución:
- `core/replicator_sellers.py`: añade flag `_fast_mode` (`VEL_GRAD` 1e6 → 1e3, `rtol` 1e-6 → 0.5, `atol` 1e-9 → 0.1, `max_step` = 2e-4) con justificación documentada "mismo equilibrio, 1000× menos stiff".
- `analysis/global_sensitivity.py`: activa `_fast_mode` por worker, añade resume desde `outputs/gsa_checkpoint_*.parquet`, redirige salidas a `outputs/`.

Adicionalmente hay cambios no relacionados al GSA (redirección de `main_simulation.py` a `outputs/`, regeneración de 8 figuras, cambio menor en `tests/statistical_tests.py`) que se separarán en un commit propio.

## Objetivo

Reemplazar la tabla cualitativa de índices de sensibilidad de § A.7 con valores calculados sobre `MedicionesMTE_v3` (6144 h), manteniendo n_base = 64 (resultados cualitativos, no IC publicables). Eliminar el ítem "GSA sobre MTE_v3" de los pendientes en `README.md` y `Matriz_Trazabilidad.md`.

## No-objetivos

- **No** se busca n_base ≥ 256 (publicable). Se deja como pendiente futuro si los asesores lo solicitan.
- **No** se cambian los 7 parámetros, sus rangos, ni los 3 outputs.
- **No** se documenta cambio metodológico — solo actualización numérica con la misma metodología.
- **No** se aborda LCOE de inversores ni autores de referencias [22][24][26][27].

## Alcance

### Fase 1 — Validación de equivalencia `_fast_mode` (TDD)

Antes del GSA se valida que `_fast_mode=True` produce el mismo equilibrio que el modo preciso, para defender la elección frente a los asesores.

**Nuevo archivo:** `tests/test_fast_mode_equivalence.py`

**Diseño del test:**

1. Cargar datos `MedicionesMTE_v3` vía `MTEDataLoader`.
2. Seleccionar 8 horas representativas heterogéneas:
   - 2 horas de mediodía con G > D (mercado activo, equilibrio interior).
   - 2 horas matinales/tarde con clearing parcial.
   - 2 horas nocturnas (sin generación, mercado inactivo).
   - 2 horas históricamente problemáticas escogidas de {h0012, h0014, h3683} ya documentadas en `graficas/fig11_convergencia_h*.png`.
3. Para cada hora, ejecutar `core.replicator_sellers.solve_sellers()` dos veces:
   - Primero con `_fast_mode = False` (modo preciso, baseline).
   - Luego con `_fast_mode = True` (modo del GSA).
4. Aserciones por hora:
   - `||P_fast − P_precise||_∞ ≤ 0.10 kWh` (tolerancia absoluta por par vendedor-comprador).
   - `|P_total_fast − P_total_precise| ≤ 0.15 kWh` (consistente con la tolerancia de `tests/golden_test_sofia.py`).
   - Para horas con mercado inactivo, ambas configuraciones deben dar `P_total ≈ 0` (atol = 1e-3 kWh).

**Criterio de aceptación:** test verde. Si falla, **bloquea el GSA**: revisar parámetros antes de continuar.

**Costo estimado:** ~5–10 min de implementación + 3–5 min de ejecución.

### Fase 2 — Ejecución del GSA

**Comando:**

```powershell
python main_simulation.py --data real --gsa --n-base 64 > outputs/run_gsa_mte_v3_<timestamp>.log 2>&1
```

**Configuración (sin cambios sobre el código existente):**

- 7 parámetros: `PGB, PGS, factor_PV, factor_D, alpha_mean, b_mean, pi_ppa`.
- 3 outputs: `Y_ganancia, Y_sc, Y_ie`.
- Saltelli `N = n_base × (2D+2) = 64 × 16 = 1024` evaluaciones.
- `_fast_mode = True` activado por worker en `_eval_sample()`.
- Resume desde `outputs/gsa_checkpoint_*.parquet` si existe.

**Protocolo de ejecución (skill `run-long-simulations` del proyecto):**

1. Snapshot previo: `cp outputs/resultados_gsa.xlsx outputs/resultados_gsa_prev.xlsx` si existe.
2. Lanzar el comando en background, capturar PID.
3. Polling con `Monitor` sobre el log para detectar:
   - `"Modo paralelo: N workers"` (arranque correcto).
   - `done/M` (avance regular).
   - tracebacks o exit ≠ 0.
4. Salida esperada: `outputs/resultados_gsa.xlsx` (5 hojas: S1, ST, S1_conf, ST_conf, Muestras_X) + `outputs/gsa_checkpoint_*.parquet`.
5. Si el run cuelga > 35 min sin progreso → abortar y diagnosticar.

**Tiempo estimado:** 10–20 min con `_fast_mode` y 7 workers (8 cores − 1).

**Verificación post-ejecución:**

- 1024 muestras válidas (no NaN) en hoja `Muestras_X`.
- `ST_factor_PV > 0` y `ST_factor_D > 0` para output `ganancia` (sanity).
- `ST_PGB > 0` para output `IE` (sanity, dominante en equidad según GSA previo).
- Si > 5 % de muestras NaN → revisar workers fallidos antes de reportar.

### Fase 3 — Integración en documentación

**Archivos a actualizar tras GSA exitoso:**

| Archivo | Cambio | Línea aprox. |
|---|---|---|
| `Documentos/notas_modelo_tesis.md` § A.7 | Reemplazar tabla de índices ST cualitativos con valores nuevos sobre MTE_v3. Mantener nota sobre IC > S1 con n_base=64. Cambiar fecha "(2026-04-17)" por "(2026-04-26)". | 873–894 |
| `README.md` | Marcar pendiente: `- [x] GSA Sobol sobre MTE_v3 (commit <sha>)` | 248 |
| `Documentos/Matriz_Trazabilidad.md` | Actualizar fila Act 4.1 con SHA del nuevo commit GSA y eliminar el bullet "GSA sobre MTE_v3" de pendientes. | 38, 55–57 |
| `outputs/resultados_gsa.xlsx` | Generado automáticamente por el run; **commiteado como evidencia**. | — |

**Comparación contra GSA previo:**

- Reportar Δ del ranking de ST entre GSA anterior y GSA-MTE_v3 en una sub-tabla nueva en § A.7.
- Si el ranking se mantiene (`factor_PV > factor_D > PGS > PGB > ...`) → confirma robustez del análisis previo.
- Si el ranking cambia → discutir interpretación (cambio de horizonte 5160 → 6144 h, perfiles ligeramente distintos en v3).

### Fase 4 — Commits atómicos y verificación

**Tres commits en `main`:**

1. **`Act 1.1 — agrega golden test de equivalencia _fast_mode`**
   - `tests/test_fast_mode_equivalence.py` (nuevo).
   - Pre-commit: `pytest tests/test_fast_mode_equivalence.py -v` verde + `pytest tests/ -q` no regresiona.

2. **`Act 4.1 — GSA Sobol-Saltelli sobre MTE_v3 (n_base=64)`**
   - `analysis/global_sensitivity.py` (modo fast + checkpoint resume).
   - `core/replicator_sellers.py` (`_fast_mode` flag).
   - `outputs/resultados_gsa.xlsx` (evidencia).
   - `Documentos/notas_modelo_tesis.md` (§ A.7 actualizada).
   - `README.md` (pendiente marcado).
   - `Documentos/Matriz_Trazabilidad.md` (fila Act 4.1).
   - Pre-commit: 1024 muestras válidas + ranking ST coherente.

3. **`outputs: centraliza salidas en outputs/`**
   - `main_simulation.py` (3 redirecciones a `outputs/`).
   - `tests/statistical_tests.py` (cambio menor).
   - 8 figuras regeneradas en `graficas/`.
   - Pre-commit: `python main_simulation.py` (sintético) + `python main_simulation.py --data real` no rompen.

**Política de errores:** si una verificación previa al commit falla, detener, diagnosticar (skill `systematic-debugging`), no encadenar más commits.

### Cierre

- `git status` limpio.
- 3 commits con mensaje en español imperativo y trazabilidad a la actividad correspondiente (regla de proyecto #6).
- **No push** a remoto (regla de proyecto #4).
- Reportar al usuario: SHAs, tiempo real de GSA, cambio en ranking ST vs GSA previo, pendientes residuales fuera de alcance (LCOE, autores referencias).

## Tiempo total estimado

| Fase | Tiempo |
|---|---|
| 1 — Validación `_fast_mode` (TDD) | ~15 min |
| 2 — Ejecución GSA | ~20 min |
| 3 — Documentación | ~10 min |
| 4 — Cierre y verificación | ~10 min |
| **Total** | **~55 min** |

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| `_fast_mode` produce equilibrio distinto al modo preciso | Fase 1 (TDD) bloquea GSA si el test falla. |
| Workers fallan en multiprocessing (NaN en outputs) | Verificación post-GSA: si > 5 % NaN, diagnosticar antes de commitear. |
| Run cuelga (Windows + ProcessPoolExecutor) | Polling con Monitor; abortar a > 35 min sin progreso. |
| Ranking ST cambia de forma inesperada | Reportar como hallazgo en § A.7 con interpretación; no es bloqueante para la tesis. |
| Cambios sin commitear no relacionados al GSA confunden el commit | Tres commits atómicos separan responsabilidades. |

## Pendientes residuales fuera de alcance

- Verificar LCOE real de inversores instalados (parámetro `b_n`). Pregunta abierta a Andrés Pantoja.
- Confirmar autores de referencias [22][24][26][27] en `Documentos/references.bib`.
- Capítulos 4 (resultados completos) y 5 (conclusiones) del manuscrito de tesis.
- Apéndices A (derivación Stackelberg) y B (datos MTE).
- GSA con n_base ≥ 256 si los asesores lo solicitan para publicación.
