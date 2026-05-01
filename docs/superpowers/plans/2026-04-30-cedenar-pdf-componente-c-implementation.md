# CAL-10b: Componente C real (Cvm + COT) desde CSV Cedenar — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar la aproximación proporcional `C_FRACTION ≈ 13.85 %` (CAL-10) por el componente real `Cvm + COT` extraído del CSV mensual `data/tarifas_cedenar_mensual.csv` para cada institución MTE, mes a mes.

**Architecture:** Nuevo helper `cvm_plus_cot_per_agent_hourly` análogo 1:1 a `pi_gs_per_agent_hourly` (CAL-9). El valor se construye como matriz `(N, T)` constante dentro de cada mes. La capa `as_component_c_array` (CAL-10) se extiende para rellenar NaN con fallback proporcional. Se propaga `component_c` por `run_comparison` y `compute_monthly_metrics`, y `main_simulation.py` arma `component_c_arg` igual que `pi_gs_arg`.

**Tech Stack:** Python 3.11+, pandas, numpy, pytest. Reusa: `data/cedenar_tariff.py`, `scenarios/_pi_gs.py`, `scenarios/scenario_c1_creg174.py`.

**Spec de referencia:** `docs/superpowers/specs/2026-04-30-cedenar-pdf-componente-c-design.md`

---

## File Structure

| Archivo | Responsabilidad | Tamaño esperado |
|---|---|---|
| `data/cedenar_tariff.py` | + `_lookup_cvm_plus_cot` (privado) y `cvm_plus_cot_per_agent_hourly` (público). Mismo patrón que `_lookup_pi_gs` y `pi_gs_per_agent_hourly`. | +80 líneas |
| `scenarios/_pi_gs.py` | Extender `as_component_c_array` para detectar NaN en arrays y rellenar con `pi_gs * C_FRACTION`. | +10 líneas |
| `scenarios/comparison_engine.py` | `run_comparison` acepta y propaga `component_c`. | +5 líneas |
| `analysis/monthly_report.py` | `compute_monthly_metrics` acepta y slicea `component_c_full` por mes. | +10 líneas |
| `main_simulation.py` | Construir `component_c_arg` y pasarlo a `run_comparison`. Banner actualizado. | +15 líneas |
| `tests/test_cedenar_cvm_cot.py` | Nuevo: 3 tests del helper. | ~80 líneas |
| `tests/test_c1_creg174_v2.py` | +2 tests integración (NT,) array y dato real > proporcional. | +30 líneas |
| `Documentos/notas_modelo_tesis.md` | Subsección "CAL-10b" con delta numérico post-corrida. | +30 líneas |
| `outputs/REPORTE_AVANCES.md` | Reescribir con números post-CAL-10b. | sustitución completa |
| `docs/adr/0010-cal10-creg174-tipo-1-2-componente-c.md` | Anexo "CAL-10b: refinamiento Cvm+COT real". | +30 líneas |

---

### Task 1: Helper `_lookup_cvm_plus_cot` (privado) en `data/cedenar_tariff.py`

**Files:**
- Modify: `data/cedenar_tariff.py` (insertar después de `_lookup_pi_gs`, ~línea 180)
- Test: `tests/test_cedenar_cvm_cot.py` (crear)

- [ ] **Step 1: Crear el archivo de tests con el primer test fallando**

Crear `tests/test_cedenar_cvm_cot.py`:

```python
"""
tests/test_cedenar_cvm_cot.py — CAL-10b
========================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Verifica el helper que extrae Cvm + COT real del CSV mensual Cedenar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from data.cedenar_tariff import (
    INSTITUTION_PROFILE,
    TariffProfile,
    _lookup_cvm_plus_cot,
    cvm_plus_cot_per_agent_hourly,
    load_monthly_tariffs,
)


def test_lookup_cvm_plus_cot_real_value_oficial_NT2_2025_04():
    """2025-04 oficial NT2 cedenar: Cvm=174.69, COT=40.27 → C=214.96 COP/kWh."""
    df = load_monthly_tariffs()
    profile = TariffProfile("oficial", 2, "cedenar")
    result = _lookup_cvm_plus_cot(df, "2025-04", profile)
    assert result == pytest.approx(214.96, rel=1e-4)
```

- [ ] **Step 2: Run test to verify it fails (function doesn't exist yet)**

Run: `python -m pytest tests/test_cedenar_cvm_cot.py::test_lookup_cvm_plus_cot_real_value_oficial_NT2_2025_04 -v`
Expected: FAIL with `ImportError: cannot import name '_lookup_cvm_plus_cot'`

- [ ] **Step 3: Implementar `_lookup_cvm_plus_cot` en `data/cedenar_tariff.py`**

Insertar después de la función `_lookup_pi_gs` (alrededor de línea 180):

```python
def _lookup_cvm_plus_cot(df: pd.DataFrame, mes_key: str,
                          profile: TariffProfile,
                          warned: set | None = None) -> float | None:
    """
    Devuelve (Cvm + COT) para (mes, categoria, NT, propiedad) en COP/kWh.

    Bajo CREG 174/2021 art. 22-23, este es el componente que el comercializador
    sigue cobrando aunque el AGPE permute energia (Excedentes Tipo 1).

    Si el mes no esta en el CSV, o si Cvm/COT son NaN, retorna None y emite
    warning una vez por mes ausente. El caller decide como rellenar
    (tipicamente vía as_component_c_array que rellena con pi_gs * C_FRACTION).

    Refs: CREG 119/2007 art. 11 (Cvm), CREG 101-028/2023 (COT).
    """
    key = (mes_key, profile.categoria, profile.nivel_tension, profile.propiedad)
    try:
        cvm = float(df.loc[key, "Cvm"])
        cot = float(df.loc[key, "COT"])
    except KeyError:
        if warned is None or mes_key not in warned:
            warnings.warn(
                f"[cedenar_tariff] Mes {mes_key} ausente en CSV para "
                f"{profile.categoria}/NT{profile.nivel_tension}/{profile.propiedad}; "
                f"componente C marcado como NaN (caller debe aplicar fallback).",
                stacklevel=3,
            )
            if warned is not None:
                warned.add(mes_key)
        return None

    if not (np.isfinite(cvm) and np.isfinite(cot)):
        if warned is None or mes_key not in warned:
            warnings.warn(
                f"[cedenar_tariff] Cvm o COT NaN para {mes_key} "
                f"{profile.categoria}/NT{profile.nivel_tension}; "
                f"componente C marcado como NaN.",
                stacklevel=3,
            )
            if warned is not None:
                warned.add(mes_key)
        return None

    return cvm + cot
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cedenar_cvm_cot.py::test_lookup_cvm_plus_cot_real_value_oficial_NT2_2025_04 -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data/cedenar_tariff.py tests/test_cedenar_cvm_cot.py
git commit -m "Act 1.0 — CAL-10b: agrega _lookup_cvm_plus_cot para componente C real CREG 119/2007 + COT"
```

---

### Task 2: Helper público `cvm_plus_cot_per_agent_hourly`

**Files:**
- Modify: `data/cedenar_tariff.py` (insertar después de `pi_gs_per_agent_hourly`, ~línea 316)
- Test: `tests/test_cedenar_cvm_cot.py` (extender)

- [ ] **Step 1: Agregar test de shape y consistencia mensual**

En `tests/test_cedenar_cvm_cot.py`, después del primer test:

```python
def test_cvm_plus_cot_per_agent_hourly_shape():
    """Devuelve matriz (N, T) con tipo float."""
    agents = ["Udenar", "Mariana"]
    idx = pd.date_range("2025-07-01", "2025-07-04", freq="1h",
                        inclusive="left", tz="America/Bogota")
    arr = cvm_plus_cot_per_agent_hourly(agents, idx)
    assert arr.shape == (2, 72)
    assert arr.dtype == np.float64


def test_cvm_plus_cot_constante_dentro_de_un_mes():
    """Todas las horas del mismo mes comparten el mismo valor C."""
    agents = ["Udenar"]
    idx = pd.date_range("2025-07-01", "2025-08-01", freq="1h",
                        inclusive="left", tz="America/Bogota")
    arr = cvm_plus_cot_per_agent_hourly(agents, idx)
    # Todas las horas de julio deben ser iguales
    assert np.allclose(arr[0, :], arr[0, 0])


def test_cvm_plus_cot_per_agent_hourly_lookup_distinto_por_categoria():
    """Oficial y comercial NT2 pueden tener COT distinto (cuando aplique)."""
    agents = ["Udenar", "Mariana"]   # oficial NT2 vs comercial NT2
    idx = pd.date_range("2026-04-01", "2026-04-02", freq="1h",
                        inclusive="left", tz="America/Bogota")
    arr = cvm_plus_cot_per_agent_hourly(agents, idx)
    # Ambos NT2: en 2026-04 Cvm = 176.41 y COT NT2 = 38.73
    # → ambos C ≈ 215.14 COP/kWh
    expected = 215.14
    assert arr[0, 0] == pytest.approx(expected, abs=0.05)
    assert arr[1, 0] == pytest.approx(expected, abs=0.05)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cedenar_cvm_cot.py -v`
Expected: 3 nuevos tests FAIL con `ImportError: cannot import name 'cvm_plus_cot_per_agent_hourly'`.

- [ ] **Step 3: Implementar `cvm_plus_cot_per_agent_hourly`**

Insertar después de `pi_gs_per_agent_hourly` en `data/cedenar_tariff.py`:

```python
def cvm_plus_cot_per_agent_hourly(agent_names: list[str],
                                    hour_index: pd.DatetimeIndex,
                                    csv_path: str | Path | None = None,
                                    ) -> np.ndarray:
    """
    Matriz (N, T) con (Cvm + COT) por (agente, hora), constante dentro del mes.

    Bajo CREG 174/2021 art. 22-23, este es el "peaje" de comercializacion que
    el comercializador sigue cobrando aunque el AGPE permute energia (Tipo 1).
    Reemplaza la aproximacion proporcional pi_gs * C_FRACTION (~13.85 %)
    introducida en CAL-10 por el dato real del CSV (~22-27 % del CU segun NT).

    La decision regulatoria de incluir Cvm + COT (no solo Cvm) esta documentada
    en docs/adr/0010-cal10-creg174-tipo-1-2-componente-c.md y en el ADR
    de CAL-10b.

    Si un mes esta ausente del CSV, esa celda queda como np.nan;
    scenarios._pi_gs.as_component_c_array detecta los NaN y rellena con
    pi_gs[n, k] * C_FRACTION (fallback proporcional CAL-10).

    Refs: CREG 119/2007 (formula CU), CREG 101-028/2023 (COT como costo
    operativo del comercializador).
    """
    df = load_monthly_tariffs(csv_path)
    N, T = len(agent_names), len(hour_index)
    out = np.full((N, T), np.nan, dtype=float)
    months = hour_index.to_period("M").astype(str).to_numpy()

    warned: set = set()
    for n, name in enumerate(agent_names):
        prof = INSTITUTION_PROFILE.get(name)
        if prof is None:
            warnings.warn(
                f"[cedenar_tariff] Sin perfil tarifario para '{name}'; "
                f"componente C marcado como NaN para todas sus horas.",
                stacklevel=2,
            )
            continue
        cache: dict[str, float | None] = {}
        for t in range(T):
            mes_key = months[t]
            if mes_key not in cache:
                cache[mes_key] = _lookup_cvm_plus_cot(df, mes_key, prof, warned)
            v = cache[mes_key]
            out[n, t] = v if v is not None else np.nan
    return out
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `python -m pytest tests/test_cedenar_cvm_cot.py -v`
Expected: 4/4 PASS.

- [ ] **Step 5: Commit**

```bash
git add data/cedenar_tariff.py tests/test_cedenar_cvm_cot.py
git commit -m "Act 1.0 — CAL-10b: agrega cvm_plus_cot_per_agent_hourly para componente C real (N,T)"
```

---

### Task 3: Extender `as_component_c_array` para rellenar NaN con fallback proporcional

**Files:**
- Modify: `scenarios/_pi_gs.py:as_component_c_array`
- Test: `tests/test_c1_creg174_v2.py` (extender)

- [ ] **Step 1: Agregar test que verifica el rellenado de NaN**

En `tests/test_c1_creg174_v2.py`, al final del archivo:

```python
def test_as_component_c_array_rellena_nan_con_proporcional():
    """Si component_c es matriz con NaN, se rellenan con pi_gs * C_FRACTION."""
    from scenarios._pi_gs import as_component_c_array, as_pi_gs_array
    from data.xm_prices import C_FRACTION

    N, T = 2, 4
    pi_gs = as_pi_gs_array(800.0, N, T)         # matriz constante 800
    c_in = np.array([
        [200.0, np.nan, 200.0, np.nan],
        [np.nan, 210.0, np.nan, 210.0],
    ])
    c_out = as_component_c_array(c_in, pi_gs, N, T)

    # Celdas con dato real intactas
    assert c_out[0, 0] == 200.0
    assert c_out[0, 2] == 200.0
    assert c_out[1, 1] == 210.0
    assert c_out[1, 3] == 210.0
    # Celdas NaN reemplazadas por 800 * C_FRACTION ≈ 110.77
    expected_fallback = 800.0 * C_FRACTION
    assert c_out[0, 1] == pytest.approx(expected_fallback, rel=1e-9)
    assert c_out[0, 3] == pytest.approx(expected_fallback, rel=1e-9)
    assert c_out[1, 0] == pytest.approx(expected_fallback, rel=1e-9)
    assert c_out[1, 2] == pytest.approx(expected_fallback, rel=1e-9)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_c1_creg174_v2.py::test_as_component_c_array_rellena_nan_con_proporcional -v`
Expected: FAIL — la versión actual no maneja NaN; o pasa NaN tal cual o falla en validación.

- [ ] **Step 3: Modificar `as_component_c_array`**

En `scenarios/_pi_gs.py`, dentro de la función `as_component_c_array`, **al final** (después del último `if N == T and arr.shape == (N,):` block, antes del `raise ValueError`):

Reemplazar el bloque que valida shape `(N, T)`:

```python
    if arr.shape == (N, T):
        return arr.astype(float, copy=False)
```

por:

```python
    if arr.shape == (N, T):
        out = arr.astype(float, copy=True)
        nan_mask = np.isnan(out)
        if nan_mask.any():
            from data.xm_prices import C_FRACTION
            out[nan_mask] = pi_gs_arr[nan_mask] * float(C_FRACTION)
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_c1_creg174_v2.py::test_as_component_c_array_rellena_nan_con_proporcional -v`
Expected: PASS.

- [ ] **Step 5: Run full v2 suite to ensure no regression**

Run: `python -m pytest tests/test_c1_creg174_v2.py -v`
Expected: 9/9 PASS (8 previos + 1 nuevo).

- [ ] **Step 6: Commit**

```bash
git add scenarios/_pi_gs.py tests/test_c1_creg174_v2.py
git commit -m "Act 1.0 — CAL-10b: as_component_c_array rellena NaN con fallback proporcional"
```

---

### Task 4: Wiring de `component_c` en `comparison_engine.run_comparison`

**Files:**
- Modify: `scenarios/comparison_engine.py:run_comparison` (firma + llamada a C1)

- [ ] **Step 1: Leer la firma actual de `run_comparison`**

Run: `grep -n "def run_comparison" scenarios/comparison_engine.py`

Localizar la lista de parámetros (~línea 60-90).

- [ ] **Step 2: Agregar parámetro `component_c` con default**

En `scenarios/comparison_engine.py`, en la firma de `run_comparison`, agregar después del último parámetro existente (típicamente `month_labels=None`):

```python
    component_c: Union[str, float, np.ndarray] = "auto",
```

- [ ] **Step 3: Propagar a la llamada de C1**

Localizar la llamada a `run_c1_creg174` (línea 124 aproximadamente). Cambiar:

```python
    c1 = run_c1_creg174(D, G_klim, pi_gs_v, pi_bolsa, prosumer_ids,
                        month_labels=month_labels,
                        component_c="auto")
```

a:

```python
    c1 = run_c1_creg174(D, G_klim, pi_gs_v, pi_bolsa, prosumer_ids,
                        month_labels=month_labels,
                        component_c=component_c)
```

- [ ] **Step 4: Verificar que tests CAL-9 + CAL-10 + CAL-10b siguen pasando**

Run: `python -m pytest tests/test_pi_gs_temporal.py tests/test_c1_creg174_v2.py tests/test_cedenar_cvm_cot.py -q`
Expected: todos verdes.

- [ ] **Step 5: Commit**

```bash
git add scenarios/comparison_engine.py
git commit -m "Act 1.0 — CAL-10b: comparison_engine acepta y propaga component_c"
```

---

### Task 5: Wiring en `analysis/monthly_report.compute_monthly_metrics`

**Files:**
- Modify: `analysis/monthly_report.py:compute_monthly_metrics` (firma + slicing por mes)

- [ ] **Step 1: Leer firma actual**

Run: `grep -n "def compute_monthly_metrics" analysis/monthly_report.py`

Identificar la lista de parámetros (típicamente recibe `pi_gs`, `pi_bolsa`, etc.).

- [ ] **Step 2: Agregar parámetro `component_c`**

En la firma de `compute_monthly_metrics`, agregar:

```python
    component_c: "str | float | np.ndarray" = "auto",
```

- [ ] **Step 3: Slicear por mes igual que `pi_gs`**

Antes de la llamada a `run_c1_creg174` (línea ~123), preparar el slice:

```python
    if isinstance(component_c, np.ndarray):
        cc_m = component_c[:, idx_arr]
    else:
        cc_m = component_c
```

- [ ] **Step 4: Propagar a la llamada**

Cambiar:

```python
    c1 = run_c1_creg174(
        D_m, G_klim_m, pi_gs_m, pb_m, prosumer_ids,
        month_labels=None,
        component_c="auto",
    )
```

a:

```python
    c1 = run_c1_creg174(
        D_m, G_klim_m, pi_gs_m, pb_m, prosumer_ids,
        month_labels=None,
        component_c=cc_m,
    )
```

- [ ] **Step 5: Verificar suite completa**

Run: `python -m pytest tests/ -q`
Expected: todos verdes (≥54/54).

- [ ] **Step 6: Commit**

```bash
git add analysis/monthly_report.py
git commit -m "Act 1.0 — CAL-10b: monthly_report acepta y slicea component_c por mes"
```

---

### Task 6: Wiring en `main_simulation.py`

**Files:**
- Modify: `main_simulation.py` (bloque pi_gs_arg ~líneas 232-240, llamada a `run_comparison` ~línea 241, banner ~línea 228)

- [ ] **Step 1: Importar la nueva función**

En `main_simulation.py`, junto a la importación existente `from data.cedenar_tariff import ... pi_gs_per_agent_hourly`, agregar `cvm_plus_cot_per_agent_hourly`:

```python
from data.cedenar_tariff import (
    INSTITUTION_PROFILE,
    effective_pi_gs_per_agent,
    pi_gs_per_agent_hourly,
    cvm_plus_cot_per_agent_hourly,
    print_tariff_summary,
)
```

(Ajusta la lista importada según los nombres ya importados; mantén el orden alfabético si lo lleva el archivo).

- [ ] **Step 2: Construir `component_c_arg` espejo de `pi_gs_arg`**

Después del bloque que arma `pi_gs_arg` (líneas 232-240), agregar:

```python
    # CAL-10b: componente C real desde tarifas_cedenar_mensual.csv (Cvm + COT).
    # Solo aplicable cuando el horizonte tiene timestamps reales (full / single_day).
    # Perfil diario y caso sintético usan "auto" (proporcional 13.85 % de pi_gs).
    if use_real_data and full_horizon:
        component_c_arg = cvm_plus_cot_per_agent_hourly(agent_names, index_full)
    elif use_real_data and single_day:
        component_c_arg = cvm_plus_cot_per_agent_hourly(agent_names, idx_day)
    else:
        component_c_arg = "auto"
```

- [ ] **Step 3: Pasar a `run_comparison`**

En la llamada a `run_comparison` (línea ~241), agregar el parámetro al final:

```python
    cr = run_comparison(
        D=D, G_klim=G_klim, G_raw=G,
        p2p_results=p2p_results,
        pi_gs=pi_gs_arg, pi_gb=grid_params["pi_gb"],
        pi_bolsa=pi_bolsa,
        prosumer_ids=prosumer_ids, consumer_ids=consumer_ids,
        pde=pde,
        pi_ppa=grid_params["pi_gb"] + 0.5*(grid_params["pi_gs"] - grid_params["pi_gb"]),
        capacity=cap,
        month_labels=month_labels,
        component_c=component_c_arg,
    )
```

- [ ] **Step 4: Actualizar el banner [CAL-10] a [CAL-10b]**

Reemplazar el bloque actual (insertado en CAL-10):

```python
    print("    [CAL-10] C1 (CREG 174 arts. 22-23): permuta Tipo 1 a "
          "(pi_gs - C), excedentes Tipo 2 a bolsa horaria post-Hx; "
          "C_FRACTION ≈ 13.85 % proporcional al CU.")
```

por:

```python
    if isinstance(component_c_arg, np.ndarray):
        c_source = "C = Cvm + COT real desde CSV Cedenar"
    else:
        c_source = "C ≈ 13.85 % proporcional al CU (modo auto)"
    print(f"    [CAL-10b] C1 (CREG 174 arts. 22-23): permuta Tipo 1 a "
          f"(pi_gs - C), excedentes Tipo 2 a bolsa horaria post-Hx; "
          f"{c_source}.")
```

- [ ] **Step 5: Verificar caso sintético end-to-end**

Run: `python main_simulation.py 2>&1 | head -40`
Expected: completa sin errores; banner muestra `[CAL-10b]` con `C ≈ 13.85 %` (modo auto sintético).

- [ ] **Step 6: Verificar perfil diario empírico**

Run: `python main_simulation.py --data real 2>&1 | grep -E "CAL-10b|Comunidad"`
Expected: banner muestra `[CAL-10b]` con `C ≈ 13.85 %` (perfil diario usa modo auto, no full_horizon).

- [ ] **Step 7: Commit**

```bash
git add main_simulation.py
git commit -m "Act 1.0 — CAL-10b: main_simulation arma component_c_arg y banner condicional"
```

---

### Task 7: Test de integración — C real produce C1 menor que aproximación proporcional

**Files:**
- Test: `tests/test_c1_creg174_v2.py` (extender con 1 test)

- [ ] **Step 1: Agregar test que compara dato real vs aproximación**

En `tests/test_c1_creg174_v2.py`, al final:

```python
def test_c1_real_csv_C_mayor_que_proporcional():
    """
    Con C real ≈ 22-27 % del CU (vs C_FRACTION ≈ 13.85 %), la permuta Tipo 1
    se descuenta más → savings_m baja → C1 cae respecto a 'auto'.

    Requiere CSV Cedenar real (data/tarifas_cedenar_mensual.csv).
    """
    from data.cedenar_tariff import cvm_plus_cot_per_agent_hourly

    N = 1
    idx = pd.date_range("2025-07-01", "2025-08-01", freq="1h",
                        inclusive="left", tz="America/Bogota")
    T = len(idx)
    D = np.full((N, T), 1.0)
    G = np.zeros((N, T))
    # Surplus solar moderado: 8 h/día con G > D
    for d in range(31):
        G[0, d*24+8 : d*24+16] = 1.5
    pi_bolsa = np.full(T, 250.0)

    # pi_gs real Cedenar: ~797 oficial NT2
    pi_gs_real = 797.0

    # 1) Modo auto (CAL-10): C = pi_gs * 0.1385 ≈ 110 COP/kWh
    res_auto = run_c1_creg174(D, G, pi_gs_real, pi_bolsa, [0],
                               component_c="auto")

    # 2) Modo CSV (CAL-10b): C real desde CSV ≈ 215 COP/kWh
    c_csv = cvm_plus_cot_per_agent_hourly(["Udenar"], idx)
    res_csv = run_c1_creg174(D, G, pi_gs_real, pi_bolsa, [0],
                              component_c=c_csv)

    # El dato real descuenta más → savings menor → net_benefit menor
    nb_auto = res_auto[0]["net_benefit"]
    nb_csv  = res_csv[0]["net_benefit"]
    assert nb_csv < nb_auto, (
        f"Esperado nb_csv ({nb_csv:.0f}) < nb_auto ({nb_auto:.0f}); "
        f"dato real Cedenar deberia descontar más que aproximación 13.85 %."
    )
```

- [ ] **Step 2: Run test**

Run: `python -m pytest tests/test_c1_creg174_v2.py::test_c1_real_csv_C_mayor_que_proporcional -v`
Expected: PASS.

- [ ] **Step 3: Run suite completa**

Run: `python -m pytest tests/ -q`
Expected: todos verdes.

- [ ] **Step 4: Commit**

```bash
git add tests/test_c1_creg174_v2.py
git commit -m "Act 1.0 — CAL-10b: test integración C real CSV > C aproximación proporcional"
```

---

### Task 8: Smoke test del wiring completo (sintético + perfil diario)

**Files:**
- (Solo verificación, sin cambios)

- [ ] **Step 1: Caso sintético**

Run: `python main_simulation.py 2>&1 | tail -30`
Expected: completa en ~15 s, banner `[CAL-10b]` con modo auto, sin errores.

- [ ] **Step 2: Perfil diario empírico**

Run: `python main_simulation.py --data real 2>&1 | tail -30`
Expected: completa en ~2 min, banner `[CAL-10b]` con modo auto, sin errores. Net benefits del orden de magnitud esperado (~50 M COP comunidad).

- [ ] **Step 3: Verificar que tests siguen verdes**

Run: `python -m pytest tests/ -q`
Expected: todos verdes (≥55/55).

- [ ] **Step 4: Commit (vacío si no hay cambios — saltar este step si no hay diff)**

```bash
git status   # verificar que no quedó código sin commitear
```

Si hay archivos sin commit, decidir si pertenecen a CAL-10b o a otro cambio. Si no, no commitear.

---

### Task 9: Run completo `--full --analysis` con dato real

**Files:**
- Output: `outputs/run_2026-04-30b.log`, `outputs/resultados_comparacion.xlsx`, `outputs/p2p_breakdown.xlsx`

- [ ] **Step 1: Respaldar outputs CAL-10**

```bash
cp outputs/resultados_comparacion.xlsx outputs/resultados_comparacion_pre_cal10b.xlsx
cp outputs/p2p_breakdown.xlsx outputs/p2p_breakdown_pre_cal10b.xlsx
cp outputs/REPORTE_AVANCES.md outputs/REPORTE_AVANCES_pre_cal10b.md
```

- [ ] **Step 2: Lanzar corrida en background**

```bash
python main_simulation.py --data real --full --analysis 2>&1 | tee outputs/run_2026-04-30b.log
```

Esperar ~52-70 min. Se puede usar el patrón de "/loop dynamic" o `ScheduleWakeup` para retomar al terminar.

- [ ] **Step 3: Validar fin exitoso**

Run: `tail -10 outputs/run_2026-04-30b.log | grep -v "Mercado P2P\|h/s\]"`
Expected: aparece "Reporte asesores → ...REPORTE_AVANCES.md" o equivalente.

Run: `ls -la outputs/resultados_comparacion.xlsx outputs/resultados_analisis.xlsx`
Expected: ambos timestamps reflejan la corrida actual.

- [ ] **Step 4: Verificar el banner [CAL-10b] con dato CSV**

Run: `grep "CAL-10b" outputs/run_2026-04-30b.log`
Expected: `[CAL-10b] ... C = Cvm + COT real desde CSV Cedenar.`

- [ ] **Step 5: Extraer diff numérico**

```bash
python -c "
import pandas as pd
post = pd.read_excel('outputs/resultados_comparacion.xlsx', sheet_name='Resumen')
print(post.to_string())
"
```

Comparar contra los números CAL-10 ya documentados (`outputs/REPORTE_AVANCES_pre_cal10b.md`):
- C1 esperado: caer otro ~8-12 % (aprox. 46-49 M COP)
- P2P esperado: invariante (52,446,938 COP)
- RPE esperado: pasar a negativo (P2P > C1 agregadamente)

- [ ] **Step 6: Sin commit en este step (es ejecución)**

Los archivos generados se commitearán en el step de docs.

---

### Task 10: Documentar delta numérico en `notas_modelo_tesis.md`

**Files:**
- Modify: `Documentos/notas_modelo_tesis.md` (extender §CAL-10 con subsección CAL-10b)

- [ ] **Step 1: Agregar subsección al final del bloque §CAL-10**

Justo antes de la línea final del bloque CAL-10 (ahora termina con "una corrida posterior dedicada cuando se incorpore la corrección adicional Cvm+COT real."), reemplazar esa última oración por:

```markdown
### §CAL-10b — Refinamiento: Cvm + COT real desde CSV Cedenar

**Fecha:** 2026-04-30  (mismo día que CAL-10)

#### Motivación

CAL-10 introdujo el descuento del componente C usando la aproximación
proporcional `C_FRACTION ≈ 13.85 %`. Inspección del PDF
`data/cedenar_pdfs/tarifa_2026-04.pdf` mostró que el valor real es
significativamente mayor (`Cvm = 176.41 + COT NT2 = 38.73 → C = 215.14
COP/kWh ≈ 26.9 % del CU oficial NT2 = 799.16`). Como el CSV
`data/tarifas_cedenar_mensual.csv` ya tiene Cvm y COT poblados para los
13 meses del horizonte, basta con un helper análogo a
`pi_gs_per_agent_hourly` para usar el dato real.

#### Decisión regulatoria: C = Cvm + COT (no solo Cvm)

CREG 174/2021 cita "componente C" textualmente; lectura semántica
estricta apuntaría a Cvm puro (CREG 119/2007 art. 11). Sin embargo, la
metodología tarifaria vigente (CREG 101-028/2023) reconoce el COT como
costo operativo del comercializador, no como impuesto aislado. En la
liquidación real CEDENAR el usuario sigue pagando Cvm + COT aunque haya
permuta. Adoptamos la postura estricta — peor escenario regulatorio
para Excedentes Tipo 1 — que fuerza al modelo a buscar eficiencia real.

Rm (Restricciones del SIN) queda fuera: matemáticamente independiente,
CREG 174 limita el cobro sobre permuta al componente de comercialización.

#### Impacto numérico (TODO: rellenar tras corrida)

| Escenario | CAL-10 (COP) | CAL-10b (COP) | Δ |
|---|---:|---:|---:|
| C1   | 52.808.543 | <RELLENAR>   | <RELLENAR> |
| P2P  | 52.446.938 | <RELLENAR>   | invariante esperado |
| RPE  | +0,69 %    | <RELLENAR>   | <RELLENAR> |

#### Tests

`tests/test_cedenar_cvm_cot.py` (4 tests del helper) +
`tests/test_c1_creg174_v2.py::test_c1_real_csv_C_mayor_que_proporcional`
(integración).
```

(Sustituir `<RELLENAR>` con los números reales de la corrida step Task 9.5).

- [ ] **Step 2: Rellenar valores numéricos reales tras la corrida**

Editar la tabla con los números obtenidos. Ejemplo (valores ilustrativos):

```markdown
| C1   | 52.808.543 | 48.500.000 | −4,3 M COP (−8,2 %) |
| P2P  | 52.446.938 | 52.446.938 | 0 (esperado) |
| RPE  | +0,69 %    | −7,5 %     | −8,2 pp (P2P domina) |
```

- [ ] **Step 3: Commit**

```bash
git add Documentos/notas_modelo_tesis.md
git commit -m "Act 1.0 — CAL-10b: documenta delta numérico Cvm+COT real en notas_modelo_tesis"
```

---

### Task 11: Actualizar `outputs/REPORTE_AVANCES.md`

**Files:**
- Modify: `outputs/REPORTE_AVANCES.md` (sustitución de números y banner CAL-10 → CAL-10b)

- [ ] **Step 1: Reemplazar el header**

Cambiar la línea:

```markdown
**Calibración vigente:** CAL-10 (CREG 174/2021 art. 22-23: Tipo 1/Tipo 2 + componente C)
```

por:

```markdown
**Calibración vigente:** CAL-10b (CREG 174/2021 art. 22-23: Tipo 1/Tipo 2 + Cvm+COT real desde CSV Cedenar)
```

- [ ] **Step 2: Actualizar la tabla principal "Resultados comparación regulatoria"**

Sustituir los valores de C1 con los obtenidos en Task 9. Ajustar RPE y la nota explicativa del orden P2P vs C1.

- [ ] **Step 3: Actualizar §3 (Cambio CAL-10 vs CAL-9) → renombrar a "Cambio CAL-10b vs CAL-10"**

Tabla con tres columnas: CAL-9 / CAL-10 / CAL-10b.

- [ ] **Step 4: Mover la sección "En progreso 🔄" sobre Cvm+COT real a "Completado ✅"**

```markdown
### Completado ✅
...
- **Cvm + COT real desde CSV Cedenar en componente C** (CAL-10b, 2026-04-30)
  - Helper `cvm_plus_cot_per_agent_hourly` análogo a `pi_gs_per_agent_hourly`
  - Decisión regulatoria documentada en ADR-0010 anexo
  - C1 cae adicional ~X % vs CAL-10
```

- [ ] **Step 5: Commit**

```bash
git add outputs/REPORTE_AVANCES.md
git commit -m "Act 1.0 — CAL-10b: actualiza REPORTE_AVANCES con números Cvm+COT reales"
```

---

### Task 12: Anexar CAL-10b al ADR-0010

**Files:**
- Modify: `docs/adr/0010-cal10-creg174-tipo-1-2-componente-c.md` (agregar sección "CAL-10b")

- [ ] **Step 1: Agregar sección antes de "## Estado"**

```markdown
## Anexo CAL-10b — Componente C real desde CSV Cedenar (2026-04-30)

### Cambio

`component_c="auto"` (proporcional 13.85 %) era una aproximación
pragmática; cedió el paso a un dato real `(N, T)` extraído del CSV
mensual `data/tarifas_cedenar_mensual.csv` que ya contiene `Cvm` y
`COT` para los 13 meses del horizonte (abr-2025 → abr-2026), copiados
manualmente de los PDFs Cedenar.

### Implementación

Helper público nuevo:

```python
data.cedenar_tariff.cvm_plus_cot_per_agent_hourly(agent_names, idx)
    -> np.ndarray  # (N, T) COP/kWh, constante dentro del mes
```

Análogo 1-a-1 a `pi_gs_per_agent_hourly` (CAL-9). Las celdas con mes
ausente se marcan NaN; `scenarios._pi_gs.as_component_c_array` las
rellena con `pi_gs[n,k] * C_FRACTION` (fallback proporcional CAL-10).

`main_simulation.py` arma `component_c_arg` con la misma lógica
condicional que `pi_gs_arg`: matriz real para `--full` y `--day`,
modo `"auto"` para perfil diario y caso sintético.

### Decisión regulatoria

C = Cvm + COT (no solo Cvm; no Rm). Justificación:

- CREG 119/2007 define Cvm como margen de comercialización puro.
- CREG 101-028/2023 reconoce COT como costo operativo del comercializador,
  no como impuesto. La factura real CEDENAR sigue cobrando Cvm + COT
  sobre la energía permutada.
- Rm (Restricciones del SIN) queda fuera: CREG 174 limita el cobro
  sobre permuta al componente de comercialización.

Postura estricta: peor escenario regulatorio para inyección Tipo 1,
fuerza al modelo a buscar eficiencia real (almacenamiento, gestión de
demanda) en lugar de depender de interpretación laxa.

### Impacto observado

(Ver tabla en `Documentos/notas_modelo_tesis.md §CAL-10b`.)

### Tests añadidos

| Test | Archivo |
|---|---|
| 4 tests del helper | `tests/test_cedenar_cvm_cot.py` |
| `as_component_c_array` rellena NaN | `tests/test_c1_creg174_v2.py` |
| C real CSV produce C1 menor que proporcional | `tests/test_c1_creg174_v2.py` |
```

- [ ] **Step 2: Actualizar la tabla "Estado" al final del ADR**

Agregar una fila más:

```markdown
| `python main_simulation.py --data real --full --analysis` (CAL-10b) | <duración>, sin errores |
```

- [ ] **Step 3: Commit**

```bash
git add docs/adr/0010-cal10-creg174-tipo-1-2-componente-c.md
git commit -m "Act 1.0 — CAL-10b: anexa decisión Cvm+COT real al ADR-0010"
```

---

### Task 13: Sembrar memoria Ruflo con CAL-10b

**Files:**
- (Solo runtime Ruflo, sin cambios en repo)

- [ ] **Step 1: Almacenar resumen en namespace `tesis-p2p`**

Usando el MCP tool `mcp__claude-flow__memory_store`:

- `namespace`: `tesis-p2p`
- `key`: `cal_10b_componente_c_real_csv`
- `tags`: `["CAL-10b", "CREG-174", "CREG-119-2007", "CREG-101-028-2023", "Cvm", "COT", "regulatorio"]`
- `value`: resumen de implementación, valores numéricos pre/post, archivos modificados, criterio regulatorio, fallback, tests.

- [ ] **Step 2: Verificar que se sembró**

Usando `mcp__claude-flow__memory_search` con query `"CAL-10b Cvm COT real CSV"`, debería retornar el registro con `hasEmbedding: true`.

---

### Task 14: Commit final atómico (squash opcional)

- [ ] **Step 1: Revisar log de commits**

```bash
git log --oneline -20
```

Confirmar que los 12 commits anteriores cubren el cambio CAL-10b.

- [ ] **Step 2: (Opcional) Squash interactivo en una sola entrada CAL-10b**

Si el equipo prefiere un solo commit por bloque CAL-N:

```bash
git rebase -i HEAD~12   # reordenar a un solo commit
```

Mensaje sugerido:

```
Act 1.0 — CAL-10b: componente C real (Cvm + COT) desde CSV Cedenar

- data/cedenar_tariff.py: + cvm_plus_cot_per_agent_hourly y _lookup_cvm_plus_cot
- scenarios/_pi_gs.py: as_component_c_array rellena NaN con pi_gs * C_FRACTION
- scenarios/comparison_engine.py + analysis/monthly_report.py: aceptan y propagan component_c
- main_simulation.py: component_c_arg condicional + banner [CAL-10b]
- tests/test_cedenar_cvm_cot.py + tests/test_c1_creg174_v2.py: 6 tests nuevos
- docs/adr/0010: anexo CAL-10b con decisión Cvm+COT
- Documentos/notas_modelo_tesis.md §CAL-10b: delta numérico
- outputs/REPORTE_AVANCES.md: reescrito con números CAL-10b

Decisión regulatoria: C = Cvm + COT (CREG 119/2007 + CREG 101-028/2023);
Rm fuera (CREG 174 limita cobro permuta al componente de comercialización).
```

(Si no se hace squash, los 12 commits atómicos también son aceptables siguiendo la convención del proyecto.)

- [ ] **Step 3: NO push** — el proyecto exige push manual del usuario.

---

## Verificación final (smoke + tests)

- [ ] `python -m pytest tests/ -q` → todos verdes (≥56/56).
- [ ] `python main_simulation.py` → ~15 s, banner `[CAL-10b]` modo auto.
- [ ] `python main_simulation.py --data real` → ~2 min, banner `[CAL-10b]` modo auto.
- [ ] `python main_simulation.py --data real --full --analysis` → ~52-70 min, banner `[CAL-10b]` con CSV real, RPE esperado negativo (P2P > C1 agregadamente).
- [ ] Documentos actualizados: `notas_modelo_tesis.md §CAL-10b`, `REPORTE_AVANCES.md`, ADR-0010 anexo.
- [ ] Memoria Ruflo: `cal_10b_componente_c_real_csv` recuperable vía `memory_search`.

---

## Notas de mantenimiento

**Cuando publique CEDENAR un nuevo mes** (p.ej. 2026-05):

1. Descargar PDF a `data/cedenar_pdfs/tarifa_2026-05.pdf`.
2. Extraer manualmente Cvm y COT por (categoría, NT, propiedad).
3. Agregar 10 filas a `data/tarifas_cedenar_mensual.csv`.
4. No requiere cambios en código — el helper detecta el nuevo mes automáticamente.

**Si CEDENAR cambia la metodología** (CREG actualiza la fórmula CU):

1. Revisar el ADR-0010 §"Decisión regulatoria".
2. Actualizar `_lookup_cvm_plus_cot` si los nombres de columna cambian.
3. Bumpear a CAL-10c o CAL-11 según magnitud del cambio.
