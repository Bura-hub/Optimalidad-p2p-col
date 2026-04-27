# Reorganización del repositorio — plan de implementación

> **Para agentic workers:** SKILL OBLIGATORIO: usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para ejecutar tarea por tarea. Los steps usan checkbox (`- [ ]`) para tracking.

**Goal:** Reducir fricción operativa del repositorio SistemaBL antes de la fase de escritura del manuscrito: invertir reglas de `.gitignore`, trackear `CLAUDE.md` y `Documentos/PropuestaTesis.txt`, mover `REPORTE_AVANCES.md` a `outputs/`, corregir rutas obsoletas en `README.md`, eliminar el archivo huérfano `superpowers_sistemaBL.md`.

**Architecture:** Cuatro commits atómicos en `main` (per Approach B del spec — sin worktree, sin renames de carpetas). Cambios afectan únicamente: `.gitignore`, `CLAUDE.md` (track), `Documentos/PropuestaTesis.txt` (track), `main_simulation.py` (1 línea más una invocación a `os.makedirs`), `Documentos/INDICE_ARCHIVOS.md`, `Documentos/Matriz_Trazabilidad.md`, `README.md`. Verificación basada en `pytest tests/ -q` + corrida de `python main_simulation.py`.

**Tech Stack:** git, Python 3.13.7, pytest 9.0.2 (corre con `--capture=no` por bug conocido del entorno).

**Spec base:** `docs/superpowers/specs/2026-04-26-repo-reorg-design.md`.

---

## Task 0: Pre-paso — eliminar archivo huérfano

**Files:**
- Delete (working tree only): `superpowers_sistemaBL.md`

- [ ] **Step 1: Confirmar que el archivo está untracked**

Run:
```bash
git ls-files --error-unmatch superpowers_sistemaBL.md
```
Expected: error `did not match any file(s) known to git` y exit code 1. Esto confirma que nunca estuvo en git.

- [ ] **Step 2: Eliminar el archivo del working tree**

Run:
```bash
rm superpowers_sistemaBL.md
```

- [ ] **Step 3: Confirmar que ya no aparece en `git status`**

Run:
```bash
git status --short | grep superpowers_sistemaBL || echo "OK: no aparece"
```
Expected: `OK: no aparece`.

> No hay commit en este task — el archivo nunca estuvo en git.

---

## Task 1: Commit 1 — `.gitignore` inversion + defensivos

**Files:**
- Modify: `.gitignore` (reemplazo completo)

- [ ] **Step 1: Reemplazar `.gitignore` con la nueva configuración**

Reemplazar TODO el contenido de `.gitignore` por:

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

- [ ] **Step 2: Verificar que el cambio no remueve archivos tracked por accidente**

Run:
```bash
git status --short
```
Expected output incluye:
- ` M .gitignore` (modificación esperada)
- `?? CLAUDE.md` (ahora destracked-able; antes ignorado)
- `?? Documentos/PropuestaTesis.txt` (ahora destracked-able; antes ignorado)
- Auto-regenerados ya conocidos en `outputs/`, `graficas/`, `REPORTE_AVANCES.md`

NO debe haber líneas con `D ` para archivos previamente tracked. Si las hay, **detener** y revisar antes de avanzar.

- [ ] **Step 3: Stage y commit**

Run:
```bash
git add .gitignore
git commit -m "chore(gitignore): invierte regla Documentos y agrega defensivos"
```

- [ ] **Step 4: Verificar el commit**

Run:
```bash
git log --oneline -1
```
Expected: el último commit es el recién creado, hash nuevo, mensaje exacto.

---

## Task 2: Commit 2 — Trackear `CLAUDE.md` y `Documentos/PropuestaTesis.txt`

**Files:**
- Track: `CLAUDE.md` (raíz)
- Track: `Documentos/PropuestaTesis.txt`

- [ ] **Step 1: Stage los dos archivos**

Run:
```bash
git add CLAUDE.md Documentos/PropuestaTesis.txt
```

- [ ] **Step 2: Verificar que ambos aparecen como nuevos archivos**

Run:
```bash
git status --short
```
Expected incluye:
- `A  CLAUDE.md`
- `A  Documentos/PropuestaTesis.txt`

- [ ] **Step 3: Commit**

Run:
```bash
git commit -m "chore: traquea CLAUDE.md y PropuestaTesis.txt como project context"
```

- [ ] **Step 4: Verificar tracking efectivo**

Run:
```bash
git ls-files | grep -E "^(CLAUDE.md|Documentos/PropuestaTesis.txt)$"
```
Expected: ambas líneas presentes en la salida.

---

## Task 3: Commit 3 — Mover `REPORTE_AVANCES.md` a `outputs/` y ajustar referencias

**Files:**
- Modify: `main_simulation.py` (línea 1026 y siguiente)
- Delete from tracking: `REPORTE_AVANCES.md` (raíz)
- Modify: `Documentos/INDICE_ARCHIVOS.md`
- Modify: `Documentos/Matriz_Trazabilidad.md`

- [ ] **Step 1: Editar `main_simulation.py:1026` para escribir a `outputs/`**

Cambio en `main_simulation.py` (la línea exacta hoy es la 1026):

```python
# Antes (1 línea):
    path = os.path.join(base_dir, "REPORTE_AVANCES.md")

# Después (2 líneas):
    os.makedirs(os.path.join(base_dir, "outputs"), exist_ok=True)
    path = os.path.join(base_dir, "outputs", "REPORTE_AVANCES.md")
```

`base_dir` ya es la raíz del proyecto (definido en `main_simulation.py:240`). El `os.makedirs(..., exist_ok=True)` hace la función auto-suficiente y es idempotente.

- [ ] **Step 2: Eliminar `REPORTE_AVANCES.md` tracked desde raíz**

Run:
```bash
git rm REPORTE_AVANCES.md
```
Expected: `rm 'REPORTE_AVANCES.md'`. El archivo desaparece del working tree y queda staged como `D `.

- [ ] **Step 3: Localizar y editar la línea de `Documentos/INDICE_ARCHIVOS.md` que referencia el path**

Buscar la línea exacta:
```bash
grep -n "REPORTE_AVANCES" Documentos/INDICE_ARCHIVOS.md
```
Expected: la línea ~21 menciona `` `REPORTE_AVANCES.md` `` en la columna de path.

Editar esa línea cambiando el path a `outputs/REPORTE_AVANCES.md`:

```diff
- | `REPORTE_AVANCES.md` | Reporte de avance para asesores. ...
+ | `outputs/REPORTE_AVANCES.md` | Reporte de avance para asesores. ...
```

- [ ] **Step 4: Editar la línea correspondiente en `Documentos/Matriz_Trazabilidad.md`**

Buscar la línea exacta:
```bash
grep -n "REPORTE_AVANCES" Documentos/Matriz_Trazabilidad.md
```
Expected: la línea ~80 menciona `` `REPORTE_AVANCES.md` `` en una tabla de archivos.

Editar esa línea cambiando el path a `outputs/REPORTE_AVANCES.md`:

```diff
- | `REPORTE_AVANCES.md` | Resultados numéricos de la última ejecución |
+ | `outputs/REPORTE_AVANCES.md` | Resultados numéricos de la última ejecución |
```

- [ ] **Step 5: Correr la simulación sintética para regenerar el reporte en la nueva ubicación**

Run:
```bash
python main_simulation.py > outputs/sim_postreorg.log 2>&1
echo "EXIT=$?"
```
Expected: `EXIT=0`. La última línea del log debe contener `Reporte asesores → .../outputs/REPORTE_AVANCES.md`.

- [ ] **Step 6: Verificar que el archivo está en `outputs/` y NO en raíz**

Run:
```bash
ls outputs/REPORTE_AVANCES.md
ls REPORTE_AVANCES.md 2>&1 | grep -q "No such file" && echo "OK: no en raíz"
```
Expected:
- Primera línea muestra `outputs/REPORTE_AVANCES.md`.
- Segunda línea muestra `OK: no en raíz`.

- [ ] **Step 7: Correr el test suite completo**

Run:
```bash
python -m pytest tests/ -q --capture=no > outputs/pytest_postreorg.log 2>&1
echo "EXIT=$?"
```
Expected: `EXIT=0`. Para confirmar el conteo:
```bash
grep -c "PASSED" outputs/pytest_postreorg.log
```
Expected: `25`.

- [ ] **Step 8: Stage y commit**

Run:
```bash
git add main_simulation.py Documentos/INDICE_ARCHIVOS.md Documentos/Matriz_Trazabilidad.md
git commit -m "outputs: mueve REPORTE_AVANCES.md a outputs/ y ajusta referencias"
```

`REPORTE_AVANCES.md` ya está staged como deleted (Step 2). Quedará incluido en el mismo commit.

- [ ] **Step 9: Verificar el commit**

Run:
```bash
git show --stat HEAD
```
Expected en la salida:
- `main_simulation.py | 3 ++-` (o similar: 1 inserción de la línea makedirs + cambio del path).
- `REPORTE_AVANCES.md | XX ----` (delete completo del archivo).
- `Documentos/INDICE_ARCHIVOS.md | 2 +-`.
- `Documentos/Matriz_Trazabilidad.md | 2 +-`.

---

## Task 4: Commit 4 — Corregir rutas de scripts en `README.md`

**Files:**
- Modify: `README.md` (3 líneas en el bloque de auditorías regenerables)

- [ ] **Step 1: Localizar el bloque de auditorías**

Run:
```bash
grep -n "outputs/audit_clean\|outputs/data_quality\|outputs/plot_coverage" README.md
```
Expected: 3 líneas, aproximadamente líneas 128–130 del README.

- [ ] **Step 2: Reemplazar las 3 ocurrencias en `README.md`**

Cambios exactos:

```diff
- python outputs/data_quality_audit.py     # 27 fuentes raw
- python outputs/audit_clean.py            # post-preprocesamiento
- python outputs/plot_coverage_gantt.py    # graficas/data_coverage_gantt.png
+ python scripts/data_quality_audit.py     # 27 fuentes raw
+ python scripts/audit_clean.py            # post-preprocesamiento
+ python scripts/plot_coverage_gantt.py    # graficas/data_coverage_gantt.png
```

- [ ] **Step 3: Verificar que ya no quedan referencias al patrón antiguo**

Run:
```bash
grep -E "outputs/(audit_clean|data_quality|plot_coverage)" README.md || echo "OK: 0 matches"
```
Expected: `OK: 0 matches`.

- [ ] **Step 4: Verificar que las nuevas referencias existen**

Run:
```bash
grep -cE "scripts/(audit_clean|data_quality|plot_coverage)" README.md
```
Expected: `3`.

- [ ] **Step 5: Stage y commit**

Run:
```bash
git add README.md
git commit -m "docs(README): corrige rutas de scripts auditoría"
```

---

## Task 5: Verificación final + housekeeping de memoria

- [ ] **Step 1: Test suite end-to-end**

Run:
```bash
python -m pytest tests/ -q --capture=no > outputs/pytest_final.log 2>&1
echo "EXIT=$?"
grep -c "PASSED" outputs/pytest_final.log
```
Expected: `EXIT=0` y conteo `25`.

- [ ] **Step 2: Simulación sintética end-to-end**

Run:
```bash
python main_simulation.py > outputs/sim_final.log 2>&1
echo "EXIT=$?"
ls outputs/REPORTE_AVANCES.md
```
Expected: `EXIT=0`, archivo `outputs/REPORTE_AVANCES.md` existe (recién regenerado).

- [ ] **Step 3: Estado de git limpio**

Run:
```bash
git status --short
```
Expected: solo modificaciones en `outputs/` (gitignored, así que no deberían aparecer) y posiblemente `graficas/*.png` regenerados. Nada en raíz, nada en `Documentos/` (excepto los auto-generados ya conocidos).

- [ ] **Step 4: Historial de commits**

Run:
```bash
git log --oneline -6
```
Expected: en orden cronológico inverso, los últimos 4 commits son los del reorg, mensajes en español imperativo:
1. `docs(README): corrige rutas de scripts auditoría`
2. `outputs: mueve REPORTE_AVANCES.md a outputs/ y ajusta referencias`
3. `chore: traquea CLAUDE.md y PropuestaTesis.txt como project context`
4. `chore(gitignore): invierte regla Documentos y agrega defensivos`
5. `docs: actualiza horizonte 5160h → 6144h tras migración a MTE_v3` (commit `089caae` previo)

- [ ] **Step 5: Limpiar memoria obsoleta `project_gitignorefake.md`**

El archivo `C:\Users\burav\.claude\projects\C--Users-burav-Documentos-MaIE---UDENAR-Proyectos-SistemaBL\memory\project_gitignorefake.md` describe una situación que ya no aplica (el `.gitignore` está activo y `.gitignorefake` no existe).

Acciones:
1. Borrar el archivo `project_gitignorefake.md`.
2. Editar `MEMORY.md` y borrar la línea correspondiente del índice.

```bash
rm "C:/Users/burav/.claude/projects/C--Users-burav-Documentos-MaIE---UDENAR-Proyectos-SistemaBL/memory/project_gitignorefake.md"
```

Después editar `MEMORY.md` quitando la línea:
```diff
- - [project_gitignorefake.md](project_gitignorefake.md) — `.gitignorefake` es `.gitignore` renombrado deliberadamente para acceso temporal completo; no borrar
```

- [ ] **Step 6: Confirmar que el spec marca la implementación como completa**

Editar `docs/superpowers/specs/2026-04-26-repo-reorg-design.md` línea 8 para apuntar al plan ya creado:

```diff
- **Plan asociado:** pendiente — `docs/superpowers/plans/2026-04-26-repo-reorg-implementation.md`
+ **Plan asociado:** `docs/superpowers/plans/2026-04-26-repo-reorg-implementation.md` (implementado)
```

> Sin commit por este último ajuste menor — opcional. Si se quiere committear: `git add docs/superpowers/specs/2026-04-26-repo-reorg-design.md && git commit -m "docs(spec): marca reorg como implementada"`.

---

## Resumen de criterios de éxito

Al finalizar las 6 tasks, el repositorio debe satisfacer:

1. **`pytest tests/ -q --capture=no` retorna exit 0 con 25 tests PASSED.**
2. **`python main_simulation.py` (sintético) retorna exit 0 y genera `outputs/REPORTE_AVANCES.md`.**
3. **`git status --short` no muestra `M REPORTE_AVANCES.md` en raíz** (porque ya no existe ahí; el de `outputs/` está gitignored).
4. **`CLAUDE.md` y `Documentos/PropuestaTesis.txt` aparecen en `git ls-files`.**
5. **`grep "outputs/audit_clean" README.md` retorna 0 matches.**
6. **`git log --oneline -5` muestra los 4 commits del reorg + el commit previo `089caae`.**
7. **El archivo `superpowers_sistemaBL.md` ya no existe en el working tree.**
8. **La memoria `project_gitignorefake.md` está borrada del filesystem y del índice `MEMORY.md`.**

Si cualquiera de estos no se cumple, **no marcar el plan como completo** y revisar el step que falló.
