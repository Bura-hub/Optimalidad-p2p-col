# Reorganización del repositorio SistemaBL — diseño

**Fecha:** 2026-04-26
**Autor:** Brayan S. Lopez-Mendez (con Claude Code)
**Skill base:** `superpowers:brainstorming`
**Plan asociado:** pendiente — `docs/superpowers/plans/2026-04-26-repo-reorg-implementation.md`

---

## 1. Contexto y motivación

El repositorio se encuentra en estado funcionalmente completo respecto a
la propuesta (Actividades 1.0 a 4.2 finalizadas, ver
`Documentos/notas_modelo_tesis.md` §A.7). Antes de la fase intensiva de
escritura del manuscrito (capítulos 4 y 5, en `Documentos/FinalTesis/`,
otro repositorio) se requiere reducir la fricción operativa del repo:

- `REPORTE_AVANCES.md` está versionado pero `main_simulation.py` lo
  reescribe en cada corrida, produciendo un diff "modified" permanente
  que ensucia `git status`.
- `.gitignore` mezcla entradas obsoletas (`history_chat/`,
  `MedicionesMTE_v2.zip`) con una whitelist frágil sobre `Documentos/*`
  que exige edición manual cada vez que se agrega un documento académico.
- `CLAUDE.md` está ignorado pese a que su contenido es project-context
  (no personal); su exclusión deja al lector inicial sin punto de
  entrada claro.
- `superpowers_sistemaBL.md` es un análisis huérfano en raíz, untracked,
  generado en una sesión previa.
- El `README.md` aún apunta a rutas antiguas (`outputs/audit_clean.py`)
  cuando los scripts viven en `scripts/`.

## 2. Alcance

Se adopta una intervención **media** (B): correcciones de configuración
y movimientos puntuales de archivos, sin renames de carpetas ni
restructuración profunda.

**Fuera de alcance** (decisiones tomadas explícitamente):
- No se renombra ninguna carpeta existente (`tests/`, `Documentos/copy/`,
  etc.).
- No se trackea `Documentos/copy/` (código MATLAB/Python de Sofía Chacón;
  decisión C2: tratamiento conservador por derechos de autor).
- No se separan tests pytest de scripts auxiliares dentro de `tests/`.
- No se modifican `graficas/` ni la política de versionado de figuras.

## 3. Decisiones del brainstorm

| # | Pregunta | Decisión |
|---|---|---|
| 1 | Nivel de intervención | **B**: medium reorg |
| 2 | `REPORTE_AVANCES.md` | **(i)** mover a `outputs/REPORTE_AVANCES.md` |
| 3 | `CLAUDE.md` | **(a)** trackear en raíz |
| 4a | `Documentos/*` ignore | **(β)** invertir a ignore-list explícita |
| 4b | `Documentos/copy/` | **(C2)** mantener ignorado (IP de terceros) |
| 5 | Estrategia de commits | **B**: secuencia atómica, 4 commits |

## 4. Cambios de configuración

### 4.1 Nuevo `.gitignore`

```gitignore
# === Python ===
__pycache__/
*.pyc
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/

# === Editores y SO ===
.vscode/
.idea/
.DS_Store
Thumbs.db

# === Claude Code y agentes ===
.claude/
.worktrees/

# === Datos crudos MTE (licencia restringida, no redistribuir) ===
MedicionesMTE/
MedicionesMTE_v3/

# === Documentos: trackeo por defecto, ignoro lo no apto ===
Documentos/FinalTesis/
Documentos/copy/
Documentos/*.pdf
Documentos/conversacion_*.txt
Documentos/informe_*.md
Documentos/p2p_explicacion.txt

# === Resultados y artefactos de corrida ===
*.xlsx
*.log
outputs/
p2p_breakdown_flujos.csv
p2p_breakdown_resumen_horario.csv
```

### 4.2 Diff conceptual

**Removido del actual:**
- `history_chat/` — directorio inexistente.
- `MedicionesMTE_v2.zip` — archivo inexistente.
- `CLAUDE.md` — pasa a tracked.
- `Documentos/*` blanket + 6 entradas `!whitelist` — reemplazadas por inversion.

**Agregado:**
- Defaults Python: `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`,
  `*.egg-info/`.
- Defaults editor/SO: `.vscode/`, `.idea/`, `.DS_Store`, `Thumbs.db`.
- Defensa adicional: `*.log`.
- Inversion explícita de `Documentos/`: `FinalTesis/`, `copy/`,
  `*.pdf`, `conversacion_*.txt`, `informe_*.md`, `p2p_explicacion.txt`.

**Efecto neto en tracking:** sólo `Documentos/PropuestaTesis.txt` se
vuelve elegible para `git add`. Todos los demás archivos en `Documentos/`
están cubiertos por reglas explícitas o ya estaban en la whitelist
anterior.

## 5. Cambios de código

### 5.1 `main_simulation.py:1026`

```python
# Antes:
path = os.path.join(base_dir, "REPORTE_AVANCES.md")

# Después:
os.makedirs(os.path.join(base_dir, "outputs"), exist_ok=True)
path = os.path.join(base_dir, "outputs", "REPORTE_AVANCES.md")
```

`base_dir` ya es la raíz del proyecto (definido en `main_simulation.py:240`).
La invocación `os.makedirs(..., exist_ok=True)` hace la función
auto-suficiente: no asume que upstream haya creado `outputs/`.

### 5.2 `README.md` — bloque de auditorías

```diff
- python outputs/data_quality_audit.py     # 27 fuentes raw
- python outputs/audit_clean.py            # post-preprocesamiento
- python outputs/plot_coverage_gantt.py    # graficas/data_coverage_gantt.png
+ python scripts/data_quality_audit.py     # 27 fuentes raw
+ python scripts/audit_clean.py            # post-preprocesamiento
+ python scripts/plot_coverage_gantt.py    # graficas/data_coverage_gantt.png
```

### 5.3 Documentos índice

- `Documentos/INDICE_ARCHIVOS.md` (línea ~21): actualizar
  `REPORTE_AVANCES.md` → `outputs/REPORTE_AVANCES.md` en la columna de
  ruta.
- `Documentos/Matriz_Trazabilidad.md` (línea ~80): mismo ajuste de ruta
  en la tabla de archivos.

Las tres referencias restantes en `Documentos/notas_modelo_tesis.md`
son textuales/conversacionales y no requieren actualización.

## 6. Plan de commits

**Pre-paso (no commit):** `rm superpowers_sistemaBL.md` — el archivo es
untracked; sale del working tree sin afectar git.

| # | Mensaje | Archivos | Verificación |
|---|---|---|---|
| 1 | `chore(gitignore): invierte regla Documentos y agrega defensivos` | `.gitignore` | `git status` muestra 2 nuevos `??`: `CLAUDE.md`, `Documentos/PropuestaTesis.txt`. Ningún `D` no esperado. |
| 2 | `chore: traquea CLAUDE.md y PropuestaTesis.txt como project context` | `CLAUDE.md`, `Documentos/PropuestaTesis.txt` | `git ls-files` los incluye; working tree limpio salvo auto-regenerados. |
| 3 | `outputs: mueve REPORTE_AVANCES.md a outputs/ y ajusta referencias` | `main_simulation.py`, `git rm REPORTE_AVANCES.md`, `Documentos/INDICE_ARCHIVOS.md`, `Documentos/Matriz_Trazabilidad.md` | `python main_simulation.py` exit 0, `outputs/REPORTE_AVANCES.md` existe, raíz no lo tiene; `pytest tests/ -q --capture=no` 25/25. |
| 4 | `docs(README): corrige rutas de scripts auditoría` | `README.md` | `grep "outputs/audit_clean\|outputs/data_quality\|outputs/plot_coverage" README.md` no devuelve líneas. |

**Restricciones de los commits** (CLAUDE.md §6):
- Idioma: español, imperativo.
- Atómicos: una preocupación conceptual por commit.
- Sin push a remoto (CLAUDE.md §4).
- Sin `--no-verify` ni bypass de hooks.

## 7. Verificación final

Después de los 4 commits, ejecutar en orden:

```bash
pytest tests/ -q --capture=no    # esperado: 25 passed, exit 0
python main_simulation.py         # esperado: exit 0, ~12 s
ls outputs/REPORTE_AVANCES.md     # esperado: existe
ls REPORTE_AVANCES.md             # esperado: no existe
git status --short                # esperado: solo auto-regenerados (graficas/, outputs/)
git log --oneline -5              # esperado: 4 commits del reorg + commit 089caae previo
```

## 8. Riesgos y mitigación

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Algún test lee `REPORTE_AVANCES.md` desde raíz | Baja (grep confirmó: ninguno) | El paso 3 corre `pytest` después del cambio. |
| `CLAUDE.md` contiene info que el usuario no quería pública | Muy baja (usuario revisó) | Decisión explícita en el brainstorm. |
| `Documentos/PropuestaTesis.txt` se trackea pero el usuario lo prefería privado | Muy baja (CLAUDE.md lo cita como "lectura obligatoria") | Si surge, `git rm --cached Documentos/PropuestaTesis.txt` y agregar a `.gitignore`. |
| El nuevo `.gitignore` atrapa archivos que el usuario quería trackeados | Baja | Inspección de `git status` después del commit 1 antes de avanzar. |
| Las rutas actualizadas en `INDICE_ARCHIVOS.md` rompen un script externo | Muy baja (no se conocen consumidores externos) | Reversible con un commit que restaure. |

## 9. Plan de rollback

Cada commit es revertible aislado. Para deshacer todo:

```bash
git revert <hash-commit-4> <hash-commit-3> <hash-commit-2> <hash-commit-1>
```

Para deshacer solo el movimiento de `REPORTE_AVANCES.md`:

```bash
git revert <hash-commit-3>
```

## 10. Tareas posteriores (fuera de este spec)

- Actualizar memoria de Claude: borrar o marcar obsoleta
  `project_gitignorefake.md`.
- Si en algún momento el comité solicita IC publicables, ejecutar GSA
  Sobol con `n_base ≥ 256` (skill `run-long-simulations`); ortogonal a
  esta reorg.
- Manuscrito (Cap. 4, Cap. 5, Apéndices A/B) — vive en
  `Documentos/FinalTesis/`, otro repositorio; usar `academic-writing-es`
  en sesión separada.
