# GSA Sobol-Saltelli sobre MTE_v3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-ejecutar el GSA Sobol-Saltelli (n_base=64) sobre MedicionesMTE_v3 (6144 h) y actualizar la documentación, validando antes que el flag `_fast_mode` produce el mismo equilibrio que el modo preciso.

**Architecture:** Trabajo directo en `main`, sin worktree. Tres commits atómicos: (1) golden test `_fast_mode`, (2) ejecución GSA + actualización docs, (3) centralización de outputs/ y regeneración de figuras. Bloqueo TDD: si el golden test falla, no se ejecuta el GSA.

**Tech Stack:** Python 3.11+, pytest, SALib (Sobol-Saltelli), pandas, numpy, scipy.integrate.solve_ivp (LSODA), ProcessPoolExecutor (Windows + freeze_support).

**Spec:** `docs/superpowers/specs/2026-04-26-gsa-mte-v3-design.md` (commit `5b0b1aa`).

---

## File Structure

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `tests/test_fast_mode_equivalence.py` | Crear | Golden test que valida `_fast_mode` vs modo preciso en 8 horas representativas |
| `analysis/global_sensitivity.py` | Modificar (ya hecho, sin commitear) | Activación `_fast_mode` por worker + resume desde checkpoint + outputs/ |
| `core/replicator_sellers.py` | Modificar (ya hecho, sin commitear) | Flag `_fast_mode` + tolerancias condicionales |
| `main_simulation.py` | Modificar (ya hecho, sin commitear) | Redirección de Excel a `outputs/` |
| `tests/statistical_tests.py` | Modificar (ya hecho, sin commitear) | Cambio menor sin relación al GSA |
| `outputs/resultados_gsa.xlsx` | Generar | Evidencia GSA, commiteada |
| `Documentos/notas_modelo_tesis.md` | Modificar | § A.7 con tabla ST nueva |
| `README.md` | Modificar | Pendiente marcado |
| `Documentos/Matriz_Trazabilidad.md` | Modificar | Fila Act 4.1 + lista pendientes |
| `graficas/fig*.png` (8 archivos) | Modificar (ya regeneradas, sin commitear) | Figuras con datos v3 |

---

## Task 1: Golden test de equivalencia `_fast_mode`

**Files:**
- Create: `tests/test_fast_mode_equivalence.py`

- [ ] **Step 1: Verificar import del loader MTE y signaturas relevantes**

Leer `data/preprocessing.py:1-60` y `core/ems_p2p.py:1-100`. Confirmar:
- `from data.preprocessing import build_demand_generation` retorna `(D, G, idx_tz)` con `D, G` de shape `(5, 6144)`.
- `EMSP2P(agents, grid, solver).run_single_hour(k, D, G)` retorna un `HourlyResult` con campos `P_star`, `pi_star`, `seller_ids`, `buyer_ids` (P_star=None si mercado inactivo).
- `import core.replicator_sellers as _rs; _rs._fast_mode = True/False` controla el flag.

- [ ] **Step 2: Escribir el test**

Crear el archivo con este contenido exacto:

```python
"""
test_fast_mode_equivalence.py
------------------------------
Verifica que `core.replicator_sellers._fast_mode = True` (VEL_GRAD=1e3,
rtol=0.5, atol=0.1, max_step=2e-4) produce el mismo equilibrio que el
modo preciso por defecto (VEL_GRAD=1e6, rtol=1e-6, atol=1e-9).

Este test es prerrequisito BLOQUEANTE de la re-ejecución del GSA
Sobol-Saltelli sobre MedicionesMTE_v3 (Actividad 4.1 de la propuesta).

Tolerancias justificadas (consistentes con tests/golden_test_sofia.py):
  - ||P_fast - P_precise||_inf <= 0.10 kWh por par (j, i)
  - |P_total_fast - P_total_precise| <= 0.15 kWh por hora
  - Horas con mercado inactivo: ambos lados deben dar P_total ~= 0

Selección de 8 horas representativas:
  - 2 horas de mediodia con G > D (mercado activo, equilibrio interior)
  - 2 horas matinales/tarde con clearing parcial
  - 2 horas nocturnas (sin generacion, mercado inactivo)
  - 2 horas historicamente problematicas (subset de h0012, h0014, h3683)

Ref: Documentos/PropuestaTesis.txt §VI.D, Act 4.1
     docs/superpowers/specs/2026-04-26-gsa-mte-v3-design.md
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

# Import diferido para mantener el modulo de _fast_mode controlable.
import core.replicator_sellers as _rs


def _load_real_mte():
    """Carga D, G de MedicionesMTE_v3. Skip si no hay datos."""
    try:
        from data.preprocessing import build_demand_generation
    except ImportError as e:
        pytest.skip(f"data.preprocessing no disponible: {e}")
    try:
        D, G, _idx = build_demand_generation()
    except Exception as e:
        pytest.skip(f"No se pudieron cargar datos MTE_v3: {e}")
    return D, G


def _build_ems():
    """Construye EMSP2P con parametros base reales (PGS, PGB en COP)."""
    from core.ems_p2p        import EMSP2P, AgentParams, GridParams, SolverParams
    from data.base_case_data import get_agent_params, GRID_PARAMS_REAL

    p = get_agent_params()
    N = p["N"]
    agents = AgentParams(
        N=N, a=p["a"], b=p["b"], c=p["c"],
        lam=p["lam"], theta=p["theta"], etha=p["etha"],
        alpha=np.zeros(N),
    )
    grid = GridParams(pi_gs=GRID_PARAMS_REAL["pi_gs"],
                      pi_gb=GRID_PARAMS_REAL["pi_gb"])
    solver = SolverParams(
        stackelberg_iters=2, stackelberg_tol=1e-3, stackelberg_max=10,
        parallel=False,
    )
    return EMSP2P(agents, grid, solver)


def _select_hours(D, G):
    """
    Devuelve 8 indices horarios heterogeneos:
      idx 0-1: mediodia con G > D (mayor excedente comunitario).
      idx 2-3: clearing parcial (excedente positivo pero pequeno).
      idx 4-5: nocturnas (G ~ 0).
      idx 6-7: dos de las problematicas {12, 14, 3683}.
    """
    G_sum = G.sum(axis=0)   # (T,)
    D_sum = D.sum(axis=0)   # (T,)
    excedente = G_sum - D_sum

    # Mediodia con mayor excedente
    top2_excedente = np.argsort(-excedente)[:2].tolist()

    # Clearing parcial: excedente positivo pero pequeno (cuartil bajo dentro de positivos)
    pos_mask = excedente > 0
    pos_idx  = np.where(pos_mask)[0]
    if len(pos_idx) >= 2:
        sorted_pos = pos_idx[np.argsort(excedente[pos_idx])]
        n_quart = max(1, len(sorted_pos) // 4)
        clearing_parcial = sorted_pos[:n_quart][:2].tolist()
        if len(clearing_parcial) < 2:
            clearing_parcial = sorted_pos[:2].tolist()
    else:
        clearing_parcial = pos_idx[:2].tolist()

    # Nocturnas: G_sum minimo
    bottom2_G = np.argsort(G_sum)[:2].tolist()

    # Problematicas: subset de {12, 14, 3683} que esten dentro del rango
    T = D.shape[1]
    problematicas = [h for h in (12, 14, 3683) if h < T][:2]

    hours = list(dict.fromkeys(top2_excedente + clearing_parcial + bottom2_G + problematicas))
    return hours[:8]


def _run_hour(ems, k, D, G, fast):
    """Corre una hora con el flag _fast_mode controlado."""
    _rs._fast_mode = bool(fast)
    try:
        res = ems.run_single_hour(k, D, G)
    finally:
        _rs._fast_mode = False
    return res


def _market_active(res):
    return res is not None and res.P_star is not None


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_module_flag_default_off():
    """Por defecto _fast_mode debe ser False (modo preciso)."""
    assert _rs._fast_mode is False, (
        "_fast_mode debe quedar False por defecto al importar el modulo"
    )


def test_fast_mode_matches_precise_on_8_hours():
    """
    Compara P_total y P_star elemento a elemento para 8 horas heterogeneas
    de MTE_v3.
    """
    D, G = _load_real_mte()
    ems  = _build_ems()
    hours = _select_hours(D, G)

    assert len(hours) == 8, f"Se esperaban 8 horas, se obtuvieron {len(hours)}: {hours}"

    failures = []
    for k in hours:
        res_precise = _run_hour(ems, k, D, G, fast=False)
        res_fast    = _run_hour(ems, k, D, G, fast=True)

        active_p = _market_active(res_precise)
        active_f = _market_active(res_fast)

        # Sub-test 1: ambos deben coincidir en si el mercado se activo o no
        if active_p != active_f:
            failures.append(
                f"hora {k}: market_active difiere (precise={active_p}, fast={active_f})"
            )
            continue

        if not active_p:
            # Mercado inactivo en ambos: nada mas que verificar
            continue

        Pp = res_precise.P_star
        Pf = res_fast.P_star

        # Sub-test 2: P_total dentro de 0.15 kWh
        diff_total = abs(float(Pp.sum()) - float(Pf.sum()))
        if diff_total > 0.15:
            failures.append(
                f"hora {k}: |P_total_fast - P_total_precise|={diff_total:.4f} > 0.15 kWh "
                f"(precise={float(Pp.sum()):.3f}, fast={float(Pf.sum()):.3f})"
            )

        # Sub-test 3: cada P_ji dentro de 0.10 kWh
        if Pp.shape == Pf.shape:
            diff_inf = float(np.abs(Pp - Pf).max())
            if diff_inf > 0.10:
                failures.append(
                    f"hora {k}: ||P_fast - P_precise||_inf={diff_inf:.4f} > 0.10 kWh"
                )
        else:
            failures.append(
                f"hora {k}: shapes distintas P_precise={Pp.shape} P_fast={Pf.shape}"
            )

    assert not failures, "Discrepancias _fast_mode vs preciso:\n  " + "\n  ".join(failures)


def test_inactive_hour_zero_in_both_modes():
    """
    Para horas claramente nocturnas (G_sum ~ 0 en toda la comunidad), ambos
    modos deben reportar mercado inactivo o P_total ~ 0.
    """
    D, G = _load_real_mte()
    ems  = _build_ems()

    G_sum = G.sum(axis=0)
    night_idx = int(np.argmin(G_sum))

    res_p = _run_hour(ems, night_idx, D, G, fast=False)
    res_f = _run_hour(ems, night_idx, D, G, fast=True)

    p_total_p = 0.0 if not _market_active(res_p) else float(res_p.P_star.sum())
    p_total_f = 0.0 if not _market_active(res_f) else float(res_f.P_star.sum())

    assert p_total_p < 1e-3, f"hora nocturna {night_idx}: P_total preciso={p_total_p:.6f}"
    assert p_total_f < 1e-3, f"hora nocturna {night_idx}: P_total fast={p_total_f:.6f}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

- [ ] **Step 3: Ejecutar el test, esperar PASS**

Run:
```powershell
python -m pytest tests/test_fast_mode_equivalence.py -v
```

Expected: 3 tests PASS (`test_module_flag_default_off`, `test_fast_mode_matches_precise_on_8_hours`, `test_inactive_hour_zero_in_both_modes`).

Si falla `test_fast_mode_matches_precise_on_8_hours`: **STOP**. El `_fast_mode` no es equivalente. Diagnosticar antes de seguir.

- [ ] **Step 4: Verificar suite global no regresiona**

Run:
```powershell
python -m pytest tests/ -q
```

Expected: todos los tests pasan (los que ya pasaban + los 3 nuevos).

Si algo falla por los cambios sin commitear de `core/replicator_sellers.py`, diagnosticar antes de seguir.

- [ ] **Step 5: Commit 1 — Act 1.1 test fast_mode**

Run:
```powershell
git add tests/test_fast_mode_equivalence.py
git commit -m "Act 1.1 -- agrega golden test de equivalencia _fast_mode

Verifica que core.replicator_sellers._fast_mode produce el mismo
equilibrio que el modo preciso (P_total dentro de 0.15 kWh, P_ji
dentro de 0.10 kWh) en 8 horas representativas de MedicionesMTE_v3.

Prerrequisito bloqueante para la re-ejecucion del GSA Sobol-Saltelli
(Act 4.1)."
```

Expected: commit creado en `main`. Anotar SHA para reportar al final.

---

## Task 2: Snapshot previo y ejecución del GSA

**Files:**
- Read: `analysis/global_sensitivity.py` (modificado, sin commitear)
- Read: `core/replicator_sellers.py` (modificado, sin commitear)
- Generate: `outputs/resultados_gsa.xlsx`, `outputs/gsa_checkpoint_*.parquet`, `outputs/run_gsa_mte_v3_<timestamp>.log`

- [ ] **Step 1: Snapshot previo del GSA anterior si existe**

Run:
```powershell
python -c "import os, shutil; src=os.path.join('outputs','resultados_gsa.xlsx'); dst=os.path.join('outputs','resultados_gsa_prev.xlsx'); shutil.copy2(src,dst) if os.path.exists(src) else print('(no hay GSA previo, sin snapshot)')"
```

Expected: copia silenciosa o mensaje "no hay GSA previo".

- [ ] **Step 2: Generar timestamp y nombre de log**

Run:
```powershell
python -c "import datetime; print('outputs/run_gsa_mte_v3_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '.log')"
```

Expected: ruta tipo `outputs/run_gsa_mte_v3_20260426_213000.log`. Anotar como `<LOGFILE>`.

- [ ] **Step 3: Lanzar GSA en background**

Run:
```powershell
python main_simulation.py --data real --gsa --n-base 64 > <LOGFILE> 2>&1
```

(con `run_in_background=true` y captura del PID).

Expected: arranque sin error, log empieza a llenarse.

- [ ] **Step 4: Polling del progreso**

Polling cada ~60-90 s con `Monitor` o lectura del log:
- Línea esperada de arranque: `Modo paralelo: N workers, M muestras pendientes`.
- Avance: contador `done/M` debe crecer.
- Cancelar y diagnosticar si: traceback en log, exit code != 0, o > 35 min sin avance.

Expected: 1024 muestras evaluadas en 10–20 min con 7 workers.

- [ ] **Step 5: Verificar Excel generado**

Run:
```powershell
python -c "
import pandas as pd
xl = pd.ExcelFile('outputs/resultados_gsa.xlsx')
print('Sheets:', xl.sheet_names)
df_x = pd.read_excel('outputs/resultados_gsa.xlsx', sheet_name='Muestras_X')
print('Muestras_X shape:', df_x.shape)
print('NaN count:', df_x.isna().sum().sum())
print('NaN rows:', df_x.isna().any(axis=1).sum(), '/', len(df_x))
"
```

Expected:
- Sheets: incluye `S1`, `ST`, `S1_conf`, `ST_conf`, `Muestras_X`.
- `Muestras_X` shape: `(1024, ≥10)` (7 params + 3 outputs).
- NaN rows ≤ 51 (5 % de 1024). Si > 51 → diagnosticar antes de seguir.

- [ ] **Step 6: Inspeccionar ranking ST cualitativo**

Run:
```powershell
python -c "
import pandas as pd
df_st = pd.read_excel('outputs/resultados_gsa.xlsx', sheet_name='ST')
print(df_st.to_string())
"
```

Expected: tabla con `factor_PV` y `factor_D` con ST mayores en columna `ganancia`. `PGB` con ST mayor en `IE`. Anotar valores: serán insertados en Documentos/notas_modelo_tesis.md § A.7.

---

## Task 3: Actualizar Documentos/notas_modelo_tesis.md § A.7

**Files:**
- Modify: `Documentos/notas_modelo_tesis.md:873-918`

- [ ] **Step 1: Leer la sección actual**

Read: `Documentos/notas_modelo_tesis.md` líneas 856–920 para confirmar el estado actual antes de editar.

- [ ] **Step 2: Reemplazar la tabla y el comentario**

Editar `Documentos/notas_modelo_tesis.md` cambiando solo la sub-sección "Resultados GSA Sobol-Saltelli" (líneas ~873–895):

Old (a buscar literalmente):
```
### Resultados GSA Sobol-Saltelli (n_base = 64, 2026-04-17)

Ejecutado con `python main_simulation.py --gsa --n-base 64`.
7 parámetros: PGB, PGS, factor_PV, factor_D, alpha_mean, b_mean, pi_ppa.
3 outputs: ganancia neta, SC (auto-consumo), IE (inequidad).
```

New:
```
### Resultados GSA Sobol-Saltelli (n_base = 64, 2026-04-26, MedicionesMTE_v3)

Ejecutado con `python main_simulation.py --data real --gsa --n-base 64`
sobre el horizonte completo de MedicionesMTE_v3 (6 144 h, 256 días).
7 parámetros: PGB, PGS, factor_PV, factor_D, alpha_mean, b_mean, pi_ppa.
3 outputs: ganancia neta, SC (auto-consumo), IE (inequidad).
Run previo (2026-04-17) sobre datos anteriores conservado en
`outputs/resultados_gsa_prev.xlsx` para comparación.
```

Old tabla (a buscar literalmente):
```
**Índices ST cualitativos (totales; más robustos que S1 con n_base pequeño):**

| Parámetro | ST ganancia | ST SC | ST IE | Interpretación |
|-----------|-------------|-------|-------|----------------|
| factor_PV | 4,63 | 0,85 | 0,23 | dominante en ganancia y SC |
| factor_D  | 2,92 | 0,21 | 0,10 | segundo en ganancia |
| PGB       | 0,73 | ~0   | 2,94 | dominante en equidad |
| PGS       | 1,77 | ~0   | 0,19 | impacto en ganancia |
| alpha_mean| 0,06 | 0,02 | 0,02 | efecto DR pequeño |
| b_mean    | ~0   | 0    | 0,07 | sin efecto significativo |
| pi_ppa    | 0    | 0    | 0    | sin efecto (C2 desactivado) |
```

New: reemplazar **todas las celdas numéricas** de la tabla con los valores leídos de `outputs/resultados_gsa.xlsx` hoja `ST` (paso 6 de Task 2). Mantener el orden de filas y la columna "Interpretación" si el ranking cualitativo se mantiene; si cambia, actualizar la columna de interpretación coherentemente.

Añadir inmediatamente después de la tabla nueva:

```
**Comparación con run anterior (2026-04-17, datos previos a v3):**
- Ranking de ST en ganancia: <"se mantiene" | "cambia: detalle">
- Ranking de ST en IE: <"se mantiene" | "cambia: detalle">
- Si el ranking se mantiene: confirma robustez del análisis previo frente al
  cambio de horizonte 5 160 → 6 144 h y los perfiles ligeramente distintos.
- Si cambia: el cambio se debe a <interpretación a partir de los Δ observados>.
```

Resolver los `<...>` con los valores reales antes de guardar.

- [ ] **Step 3: Verificar la edición**

Run:
```powershell
python -c "
with open('Documentos/notas_modelo_tesis.md', encoding='utf-8') as f:
    txt = f.read()
assert '2026-04-26, MedicionesMTE_v3' in txt, 'fecha nueva no insertada'
assert 'Comparación con run anterior' in txt, 'sub-sección de comparación faltante'
print('OK: notas_modelo_tesis.md actualizado')
"
```

Expected: `OK: notas_modelo_tesis.md actualizado`.

---

## Task 4: Actualizar README.md y Matriz_Trazabilidad.md

**Files:**
- Modify: `README.md:248`
- Modify: `Documentos/Matriz_Trazabilidad.md:38, 55-57`

- [ ] **Step 1: Marcar pendiente en README.md**

Editar `README.md` línea ~248. Reemplazar:

Old:
```
- [ ] GSA Sobol sobre MTE_v3: `python main_simulation.py --data real --gsa --n-base 64`
```

New (reemplazar `<SHA_GSA>` con el SHA corto del commit que se hará en Task 6):
```
- [x] ~~GSA Sobol sobre MTE_v3~~ → ejecutado 2026-04-26 (commit `<SHA_GSA>`); resultados en `outputs/resultados_gsa.xlsx`
```

> Nota: dejar literalmente `<SHA_GSA>` como placeholder; se reemplazará tras crear el commit en Task 6 con `git commit --amend` o se enmienda la siguiente vez. Aceptable porque el commit que toca este archivo se hace inmediatamente después.

Alternativa (preferida): hacer este cambio dentro del Step 4 de Task 6, para que el SHA sea el del propio commit. Si se elige esta alternativa, **omitir este step y pasar directo al Step 2**.

- [ ] **Step 2: Actualizar Matriz_Trazabilidad.md fila Act 4.1**

Editar `Documentos/Matriz_Trazabilidad.md` línea ~38. Buscar el texto:

```
GSA Sobol-Saltelli (7 parámetros, 3 outputs, n_base = 64, 1 024 evaluaciones) ejecutado el 2026-04-17;
```

Reemplazar por:
```
GSA Sobol-Saltelli (7 parámetros, 3 outputs, n_base = 64, 1 024 evaluaciones) ejecutado el 2026-04-26 sobre MedicionesMTE_v3;
```

- [ ] **Step 3: Eliminar bullet de pendiente en Matriz_Trazabilidad.md**

Editar `Documentos/Matriz_Trazabilidad.md` líneas 55–57. Buscar:

```
- **GSA sobre MTE_v3:** El GSA Sobol (n_base=64) fue ejecutado el 2026-04-17 sobre datos
  anteriores. Pendiente re-ejecución sobre MedicionesMTE_v3 (6 144 h):
  `python main_simulation.py --data real --gsa --n-base 64` (~10-20 min).
```

Eliminarlo completamente (junto con la línea en blanco posterior si queda doble).

- [ ] **Step 4: Verificar las ediciones**

Run:
```powershell
python -c "
with open('README.md', encoding='utf-8') as f:
    r = f.read()
assert 'GSA Sobol sobre MTE_v3' in r and 'ejecutado 2026-04-26' in r, 'README no actualizado'
with open('Documentos/Matriz_Trazabilidad.md', encoding='utf-8') as f:
    m = f.read()
assert 'ejecutado el 2026-04-26 sobre MedicionesMTE_v3' in m, 'Matriz fila Act 4.1 no actualizada'
assert 'Pendiente re-ejecución sobre MedicionesMTE_v3' not in m, 'pendiente GSA no removido'
print('OK: README + Matriz actualizados')
"
```

Expected: `OK: README + Matriz actualizados`.

---

## Task 5: Commit 2 — Act 4.1 GSA + actualización docs

**Files:**
- Stage: `analysis/global_sensitivity.py`, `core/replicator_sellers.py`, `outputs/resultados_gsa.xlsx`, `Documentos/notas_modelo_tesis.md`, `README.md`, `Documentos/Matriz_Trazabilidad.md`

- [ ] **Step 1: Verificar staging exacto**

Run:
```powershell
git status
```

Expected: ver los 6 archivos arriba como modificados/añadidos. Si aparecen otros (p. ej. `main_simulation.py`, `tests/statistical_tests.py`, figuras), **NO** stagear todavía — esos van en el Commit 3.

- [ ] **Step 2: Stage selectivo**

Run:
```powershell
git add analysis/global_sensitivity.py core/replicator_sellers.py outputs/resultados_gsa.xlsx Documentos/notas_modelo_tesis.md README.md Documentos/Matriz_Trazabilidad.md
git status
```

Expected: solo los 6 archivos en staging. `main_simulation.py`, `tests/statistical_tests.py` y `graficas/*.png` siguen como `Modified` no staged.

- [ ] **Step 3: Crear commit 2**

Run:
```bash
git commit -m "Act 4.1 -- GSA Sobol-Saltelli sobre MTE_v3 (n_base=64)

Re-ejecuta el GSA Sobol-Saltelli sobre el horizonte completo de
MedicionesMTE_v3 (6 144 h, 256 dias). 7 parametros, 3 outputs,
1 024 evaluaciones, ~<TIEMPO_REAL> con _fast_mode activo.

Cambios:
- core/replicator_sellers.py: flag _fast_mode (VEL_GRAD reducido,
  tolerancias relajadas) activable por workers del GSA. Equivalencia
  con modo preciso validada en tests/test_fast_mode_equivalence.py.
- analysis/global_sensitivity.py: activacion _fast_mode por worker,
  resume desde checkpoint, salidas centralizadas en outputs/.
- outputs/resultados_gsa.xlsx: evidencia (sheets S1, ST, S1_conf,
  ST_conf, Muestras_X).
- Documentos/notas_modelo_tesis.md: tabla ST actualizada en A.7
  con datos v3 y comparacion con run anterior.
- README.md, Matriz_Trazabilidad.md: pendiente cerrado."
```

Reemplazar `<TIEMPO_REAL>` con el tiempo medido en el log (ej. "18 min").

Expected: commit creado en `main`. Anotar SHA como `<SHA_GSA>`.

- [ ] **Step 4: (Opcional) Amend para insertar SHA en README**

Si en Task 4 Step 1 se dejó `<SHA_GSA>` literal:

Run:
```powershell
git log -1 --format="%h"
```

Anotar SHA corto, sustituirlo en `README.md`, luego:

```powershell
git add README.md
git commit --amend --no-edit
```

Expected: commit amendado con el SHA correcto. Si se prefiere evitar `--amend`, hacer un commit pequeño "docs: registra SHA del run GSA" en su lugar.

---

## Task 6: Verificar pipeline base no roto

**Files:**
- Run: `main_simulation.py` (sin modificar todavía la centralización de outputs/)

- [ ] **Step 1: Backup de Excel actuales**

Run:
```powershell
python -c "
import os, shutil
for f in ('resultados_comparacion.xlsx','resultados_analisis.xlsx','p2p_breakdown.xlsx'):
    src = os.path.join('outputs', f)
    dst = os.path.join('outputs', f.replace('.xlsx','_prev.xlsx'))
    if os.path.exists(src):
        shutil.copy2(src, dst)
print('OK: backups creados')
"
```

Expected: `OK: backups creados`.

- [ ] **Step 2: Smoke run sintético**

Run:
```powershell
python main_simulation.py
```

Expected: completa en ~35 s sin tracebacks. Verifica que los cambios sin commitear de `main_simulation.py` (redirección a `outputs/`) no rompen el modo sintético.

- [ ] **Step 3: Smoke run real (perfil promedio)**

Run:
```powershell
python main_simulation.py --data real
```

Expected: completa en ~2 min. Excels caen en `outputs/`. Verifica integridad del cambio de redirección.

Si falla cualquiera: **STOP**. Diagnosticar antes de stagear el commit 3.

---

## Task 7: Commit 3 — Centralización outputs/ + figuras

**Files:**
- Stage: `main_simulation.py`, `tests/statistical_tests.py`, `graficas/fig*.png` (8 archivos)

- [ ] **Step 1: Verificar contenido pendiente**

Run:
```powershell
git status
```

Expected: solo `main_simulation.py`, `tests/statistical_tests.py` y las 8 figuras como modificados; nada más.

- [ ] **Step 2: Stage**

Run:
```powershell
git add main_simulation.py tests/statistical_tests.py graficas/fig13_desglose_flujos.png graficas/fig15_c1_vs_c4.png graficas/fig1_perfiles.png graficas/fig2_clasificacion.png graficas/fig3_mercado_p2p.png graficas/fig4_metricas_horarias.png graficas/fig5_comparacion_regulatoria.png graficas/fig6_ganancia_por_agente.png
git status
```

Expected: 10 archivos staged.

- [ ] **Step 3: Commit 3**

Run:
```bash
git commit -m "outputs: centraliza salidas de simulacion en outputs/

- main_simulation.py: redirige resultados_comparacion.xlsx,
  resultados_analisis.xlsx y p2p_breakdown.xlsx a outputs/.
- tests/statistical_tests.py: ajuste menor coherente con la
  ubicacion centralizada.
- graficas/fig*.png (8 figuras): regeneradas con datos de
  MedicionesMTE_v3 (6 144 h)."
```

Expected: commit creado. Anotar SHA.

---

## Task 8: Cierre y reporte

- [ ] **Step 1: Verificar repo limpio**

Run:
```powershell
git status
```

Expected: `working tree clean` excepto los archivos no relacionados con esta tarea (p. ej. `.gitignore` eliminado deliberadamente, `Documentos/FinalTesis/` que vive en otro repo según memoria de proyecto).

- [ ] **Step 2: Listar los tres commits creados**

Run:
```powershell
git log --oneline -5
```

Expected: tres commits nuevos en orden: (commit 3) → (commit 2 con SHA `<SHA_GSA>`) → (commit 1 test) → `5b0b1aa docs: agrega diseño Act 4.1` → ...

- [ ] **Step 3: Reportar al usuario**

Mensaje de cierre con:
- SHAs de los tres commits.
- Tiempo real de ejecución del GSA.
- ¿Ranking ST se mantuvo o cambió respecto al run anterior?
- Pendientes residuales fuera de alcance:
  * Verificar LCOE real de inversores instalados (`b_n`).
  * Confirmar autores de referencias [22][24][26][27].
  * Capítulos 4 y 5 del manuscrito.
  * Apéndices A y B.
  * GSA con n_base ≥ 256 si los asesores lo solicitan.
- Confirmar que **NO** se hizo push a remoto (regla #4).

---

## Self-Review Notes (interno)

- Spec coverage: ✅ las 4 fases del spec (validación, ejecución, docs, commits) están cubiertas en Tasks 1–7. Cierre en Task 8.
- Placeholders: `<LOGFILE>`, `<TIEMPO_REAL>`, `<SHA_GSA>` son placeholders dinámicos por diseño (se llenan en runtime). Marcados explícitamente como tales.
- Tipos consistentes: `_fast_mode` se usa con la misma sintaxis (`_rs._fast_mode = True/False`) en `_eval_sample` (código existente) y en `_run_hour` (test). `EMSP2P.run_single_hour(k, D, G)` consistente con `tests/golden_test_sofia.py`.
- Bloqueos: Task 1 bloquea Task 2 (test debe pasar antes del GSA). Task 5 bloquea Task 6 (commit 2 antes del smoke test, para que outputs no se mezcle). Task 6 bloquea Task 7.
