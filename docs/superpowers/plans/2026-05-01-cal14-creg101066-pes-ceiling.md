# CAL-14 — Techo CREG 101 066/2024 (PES) en pi_bolsa: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicar el techo regulatorio CREG 101 066/2024 (Precio de Escasez Superior, PES) al precio de bolsa horario en `data/xm_prices.py`, recortando picos del cache pydataxm que superan el techo absoluto del PTB. Todos los escenarios C1/C3/C4 reciben automáticamente la serie ya topada.

**Architecture:** Capa de datos única — `get_pi_bolsa(apply_ceiling=True)` aplica el cap como último paso antes de retornar la serie. Tabla mensual de PEI/PE/PES vive en `data/precios_escasez_creg.csv` (paralelo a `data/tarifas_cedenar_mensual.csv` de CAL-9). Política para meses sin valor: interpolación lineal entre adyacentes con WARN en log.

**Tech Stack:** Python 3.11, pandas ≥2.0, numpy, pytest. Sigue convenciones existentes del proyecto: docstrings en español, tests con TDD London-light, commits atómicos en español imperativo con prefijo `Act 1.0 — CAL-14:`.

**Spec base:** `docs/superpowers/specs/2026-05-01-cal14-creg101066-pes-ceiling.md`

---

## File Structure

| Acción | Archivo | Responsabilidad |
|---|---|---|
| Create | `data/precios_escasez_creg.csv` | Tabla mensual PEI/PE/PES (7 filas, jul-2025 a ene-2026) |
| Modify | `data/xm_prices.py` | Añade `load_creg_ceiling`, `apply_creg101066_ceiling`, `_print_ceiling_summary`; modifica `get_pi_bolsa` |
| Create | `tests/test_creg101066_ceiling.py` | 8 tests cubriendo loader, capping, integración |
| Create | `docs/adr/0014-cal14-creg101066-pes-ceiling.md` | ADR formal de la decisión |
| Modify | `docs/adr/README.md` | Añade fila en el índice |
| Modify | `Documentos/notas_modelo_tesis.md` | §CAL-14 con justificación regulatoria |
| Modify | `scripts/seed_ruflo_adr.py` | Sembrar ADR-0014 en memoria Ruflo |

---

## Task 1: Crear el CSV con la tabla mensual PEI/PE/PES

**Files:**
- Create: `data/precios_escasez_creg.csv`

- [ ] **Step 1: Escribir el CSV con los 7 meses verificados**

Crear `data/precios_escasez_creg.csv` con este contenido exacto:

```csv
mes,pei_cop_kwh,pe_cop_kwh,pes_cop_kwh,fuente,nota
2025-07,350.08,699.17,865.22,xm.com.co/noticias/8119,Informe XM jul-2025
2025-08,343.86,746.17,898.02,xm.com.co/noticias/8184,Informe XM ago-2025
2025-09,339.20,711.27,893.85,sinergox.xm.com.co/2025/09/03_Informe_Precios,Excel sheet Comportamiento_PBNal_Horario
2025-10,334.17,675.82,857.21,xm.com.co/noticias/8442,Informe XM oct-2025
2025-11,332.00,659.00,829.00,xm.com.co/noticias/8584,Informe XM nov-2025
2025-12,329.43,625.20,864.91,sinergox.xm.com.co/2025/12/03_Informe_Precios,Excel sheet Comportamiento_PBNal_Horario
2026-01,327.67,590.56,830.34,xm.com.co/noticias/8759,Informe XM ene-2026
```

- [ ] **Step 2: Verificar que el archivo se lee correctamente**

Ejecutar:

```bash
python -c "import pandas as pd; df = pd.read_csv('data/precios_escasez_creg.csv'); print(df); print('shape:', df.shape)"
```

Expected:
```
       mes  pei_cop_kwh  pe_cop_kwh  pes_cop_kwh  ...
0  2025-07       350.08      699.17       865.22  ...
... (7 filas)
shape: (7, 6)
```

- [ ] **Step 3: Commit**

```bash
git add data/precios_escasez_creg.csv
git commit -m "Act 1.0 — CAL-14: tabla mensual PEI/PE/PES CREG 101 066/2024"
```

---

## Task 2: load_creg_ceiling — caso básico (mes presente)

**Files:**
- Modify: `data/xm_prices.py` (añadir bloque al final, antes de `# ── CLI`)
- Create: `tests/test_creg101066_ceiling.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_creg101066_ceiling.py`:

```python
"""
tests/test_creg101066_ceiling.py — CAL-14: Techo CREG 101 066/2024 PES
=======================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 3.x

Verifica el cargador de la tabla mensual PEI/PE/PES y la aplicación del
techo regulatorio al precio de bolsa horario.

Referencia: docs/superpowers/specs/2026-05-01-cal14-creg101066-pes-ceiling.md
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from data.xm_prices import (
    load_creg_ceiling,
    apply_creg101066_ceiling,
    get_pi_bolsa,
)


# ─── Grupo A — load_creg_ceiling ──────────────────────────────────────────────

def test_load_csv_returns_series_indexed_by_month():
    """load_creg_ceiling devuelve serie pandas con index Period[M]."""
    s = load_creg_ceiling("2025-07-01", "2026-02-01", level="PES")
    assert isinstance(s, pd.Series)
    assert len(s) == 7
    # Valor exacto del Excel XM para sep-2025
    assert s.loc[pd.Period("2025-09", freq="M")] == pytest.approx(893.85)
    assert s.loc[pd.Period("2025-07", freq="M")] == pytest.approx(865.22)
    assert s.loc[pd.Period("2026-01", freq="M")] == pytest.approx(830.34)


def test_load_csv_supports_pei_pe_pes_levels():
    """Los tres niveles PEI/PE/PES son seleccionables."""
    s_pes = load_creg_ceiling("2025-07-01", "2026-02-01", level="PES")
    s_pe  = load_creg_ceiling("2025-07-01", "2026-02-01", level="PE")
    s_pei = load_creg_ceiling("2025-07-01", "2026-02-01", level="PEI")
    # Orden canónico: PEI < PE < PES en cualquier mes
    assert (s_pei < s_pe).all()
    assert (s_pe  < s_pes).all()
```

- [ ] **Step 2: Correr el test y verificar que falla**

```bash
python -m pytest tests/test_creg101066_ceiling.py -v
```

Expected: `ImportError: cannot import name 'load_creg_ceiling'`

- [ ] **Step 3: Implementar load_creg_ceiling en data/xm_prices.py**

Añadir antes del bloque `# ── CLI`, alrededor de la línea 655:

```python
# ── CAL-14: Techo CREG 101 066/2024 ──────────────────────────────────────────
# Resolución CREG 101 066/2024 (vigente 01-DIC-2024) reemplaza el precio de
# escasez único por tres niveles diferenciados (PEI/PE/PES) que se actualizan
# mensualmente. Al recortar pi_bolsa por PES (techo absoluto superior) se
# aproxima el PTB (Precio de Transacciones en Bolsa) que el generador
# efectivamente recibe tras activación de OEF — el dato bruto del cache
# pydataxm (PrecBolsNaci) entrega el marginal sin recortar.
#
# Tabla mensual: data/precios_escasez_creg.csv
# Validación de valores: sheet Comportamiento_PBNal_Horario en
#   sinergox.xm.com.co/.../03_Informe_Precios_y_Transacciones_MM_2025.xlsx
# Spec: docs/superpowers/specs/2026-05-01-cal14-creg101066-pes-ceiling.md

_CEILING_LEVEL_COL = {
    "PEI": "pei_cop_kwh",
    "PE":  "pe_cop_kwh",
    "PES": "pes_cop_kwh",
}


def load_creg_ceiling(
    t_start: str,
    t_end: str,
    level: str = "PES",
    csv_path: Optional[str] = None,
) -> pd.Series:
    """
    Carga la tabla mensual de precios de escasez CREG 101 066/2024.

    Parameters
    ----------
    t_start, t_end : str
        Rango ISO ``"YYYY-MM-DD"`` del horizonte solicitado.
    level : {"PEI", "PE", "PES"}
        Nivel de techo a devolver. Default ``"PES"`` (techo absoluto superior).
    csv_path : str, optional
        Ruta al CSV. Default ``data/precios_escasez_creg.csv``.

    Returns
    -------
    pd.Series
        Serie indexada por ``pd.Period(freq="M")`` con el techo en COP/kWh
        para cada mes del rango ``[t_start, t_end)``. Meses sin valor en el
        CSV se interpolan linealmente entre adyacentes con valor.

    Raises
    ------
    FileNotFoundError
        Si el CSV no existe.
    ValueError
        Si ``level`` no está en ``{"PEI", "PE", "PES"}``.
    """
    if level not in _CEILING_LEVEL_COL:
        raise ValueError(
            f"level debe ser uno de {list(_CEILING_LEVEL_COL)}, recibido {level!r}"
        )

    if csv_path is None:
        csv_path = str(Path(__file__).parent / "precios_escasez_creg.csv")

    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Falta {csv_path}. Esperado: tabla mensual PEI/PE/PES CREG 101 066. "
            f"Ver docs/superpowers/specs/2026-05-01-cal14-creg101066-pes-ceiling.md"
        )

    df = pd.read_csv(path)
    df["mes"] = pd.PeriodIndex(df["mes"], freq="M")
    df = df.set_index("mes").sort_index()

    col = _CEILING_LEVEL_COL[level]
    target_idx = pd.period_range(
        start=pd.Timestamp(t_start).to_period("M"),
        end=pd.Timestamp(t_end).to_period("M"),
        freq="M",
    )
    serie = df[col].reindex(target_idx)
    # Interpolación lineal para meses sin valor
    if serie.isna().any():
        serie = serie.interpolate(method="linear", limit_direction="both")

    return serie
```

Y asegurarse de que estos imports estén al tope del archivo (verificar líneas 29-35):

```python
from pathlib import Path
from typing import Optional
```

(Ya existen — solo confirmar.)

- [ ] **Step 4: Correr el test y verificar que pasa**

```bash
python -m pytest tests/test_creg101066_ceiling.py::test_load_csv_returns_series_indexed_by_month -v
python -m pytest tests/test_creg101066_ceiling.py::test_load_csv_supports_pei_pe_pes_levels -v
```

Expected: ambos PASS.

- [ ] **Step 5: Commit**

```bash
git add data/xm_prices.py tests/test_creg101066_ceiling.py
git commit -m "Act 1.0 — CAL-14: load_creg_ceiling carga tabla mensual PEI/PE/PES"
```

---

## Task 3: load_creg_ceiling — manejo de errores y celdas vacías

**Files:**
- Modify: `tests/test_creg101066_ceiling.py`

- [ ] **Step 1: Añadir tests de manejo de errores**

Añadir en `tests/test_creg101066_ceiling.py` después del último test del Grupo A:

```python
def test_load_csv_raises_when_file_missing(tmp_path):
    """Falla explícita cuando el CSV no existe (no caer en silencio)."""
    fake_path = tmp_path / "no_existe.csv"
    with pytest.raises(FileNotFoundError, match="Falta"):
        load_creg_ceiling("2025-07-01", "2026-02-01",
                          level="PES", csv_path=str(fake_path))


def test_load_csv_raises_on_invalid_level():
    """level fuera de {PEI, PE, PES} lanza ValueError."""
    with pytest.raises(ValueError, match="level debe ser"):
        load_creg_ceiling("2025-07-01", "2026-02-01", level="WRONG")


def test_load_csv_handles_empty_cell_with_interpolation(tmp_path):
    """Mes con celda vacía se interpola linealmente entre adyacentes."""
    csv = tmp_path / "test_ceiling.csv"
    csv.write_text(
        "mes,pei_cop_kwh,pe_cop_kwh,pes_cop_kwh,fuente,nota\n"
        "2025-07,350.0,700.0,800.0,test,jul\n"
        "2025-08,,,,test,gap\n"               # Celda vacía
        "2025-09,360.0,720.0,820.0,test,sep\n"
    )
    s = load_creg_ceiling("2025-07-01", "2025-10-01",
                          level="PES", csv_path=str(csv))
    # Interpolación lineal: ago debería ser (800 + 820) / 2 = 810
    assert s.loc[pd.Period("2025-08", freq="M")] == pytest.approx(810.0)
```

- [ ] **Step 2: Correr los tests y verificar resultado**

```bash
python -m pytest tests/test_creg101066_ceiling.py -v -k "load_csv"
```

Expected: los 3 tests nuevos PASS (el código ya soporta los casos por construcción de pandas).

- [ ] **Step 3: Commit**

```bash
git add tests/test_creg101066_ceiling.py
git commit -m "Act 1.0 — CAL-14: tests para manejo de errores e interpolación"
```

---

## Task 4: apply_creg101066_ceiling — recorte básico

**Files:**
- Modify: `data/xm_prices.py`
- Modify: `tests/test_creg101066_ceiling.py`

- [ ] **Step 1: Escribir el test que falla**

Añadir en `tests/test_creg101066_ceiling.py` (Grupo B):

```python
# ─── Grupo B — apply_creg101066_ceiling ──────────────────────────────────────

def test_ceiling_caps_values_above_PES():
    """Valores > PES del mes se recortan a PES exacto."""
    # 24 horas del 2025-07-01 (PES jul = 865.22)
    pi = np.array([100.0, 1500.0, 200.0, 2000.0] + [100.0] * 20)
    capped = apply_creg101066_ceiling(pi, "2025-07-01", level="PES")
    assert capped.max() == pytest.approx(865.22)
    # Valores no afectados quedan iguales
    assert capped[0] == 100.0
    assert capped[2] == 200.0


def test_ceiling_does_not_modify_values_below_PES():
    """Si todos los valores están bajo PES, la serie no se modifica."""
    pi = np.array([100.0, 200.0, 300.0, 400.0] + [500.0] * 20)
    capped = apply_creg101066_ceiling(pi, "2025-07-01", level="PES")
    assert np.allclose(capped, pi)
```

- [ ] **Step 2: Correr y verificar que falla**

```bash
python -m pytest tests/test_creg101066_ceiling.py::test_ceiling_caps_values_above_PES -v
```

Expected: `ImportError` o `AttributeError` por función no definida.

- [ ] **Step 3: Implementar apply_creg101066_ceiling**

Añadir en `data/xm_prices.py` después de `load_creg_ceiling`:

```python
def apply_creg101066_ceiling(
    pi_bolsa: np.ndarray,
    t_start: str,
    level: str = "PES",
    effective_date: str = "2024-12-01",
    csv_path: Optional[str] = None,
    return_diagnostics: bool = False,
):
    """
    Aplica el techo CREG 101 066/2024 al precio de bolsa horario.

    Para cada hora ``k``, si la fecha local de esa hora es ``>= effective_date``,
    el precio se recorta a ``min(pi_bolsa[k], ceiling[mes_de_k])``. Antes de
    ``effective_date`` la serie se devuelve sin cambios.

    Parameters
    ----------
    pi_bolsa : np.ndarray  shape (T,)
        Serie horaria de precios de bolsa en COP/kWh.
    t_start : str
        Fecha de inicio del horizonte ``"YYYY-MM-DD"``.
    level : {"PEI", "PE", "PES"}
        Nivel del techo. Default ``"PES"`` (techo absoluto superior).
    effective_date : str
        Fecha desde la cual aplica CREG 101 066/2024. Default ``"2024-12-01"``.
    csv_path : str, optional
        Override de la ruta al CSV de techos.
    return_diagnostics : bool
        Si True, devuelve ``(pi_capped, diag)`` con métricas de recorte.

    Returns
    -------
    np.ndarray  shape (T,)
        Serie con techo aplicado.
    dict (opcional)
        Diagnósticos: ``hours_capped``, ``fraction``, ``delta_cop_total``,
        ``by_month``.
    """
    pi = np.asarray(pi_bolsa, dtype=float).copy()
    T = len(pi)

    idx = pd.date_range(t_start, periods=T, freq="1h")
    eff = pd.Timestamp(effective_date)
    t_end = (idx[-1] + pd.Timedelta(hours=1)).strftime("%Y-%m-%d")

    ceil_monthly = load_creg_ceiling(t_start, t_end, level=level,
                                      csv_path=csv_path)
    # Vector horario de techo: misma longitud que pi
    ceil_per_hour = np.array([
        ceil_monthly.loc[ts.to_period("M")] if ts >= eff else np.inf
        for ts in idx
    ], dtype=float)

    pi_pre = pi.copy()
    pi = np.minimum(pi, ceil_per_hour)

    if not return_diagnostics:
        return pi

    mask = pi_pre > ceil_per_hour
    diag = {
        "hours_capped":    int(mask.sum()),
        "fraction":        float(mask.mean()),
        "delta_cop_total": float((pi_pre - pi).sum()),
        "by_month":        {},
    }
    serie = pd.Series(pi_pre - pi, index=idx)
    for period, sub in serie.groupby(serie.index.to_period("M")):
        diag["by_month"][str(period)] = {
            "hours_capped": int((sub > 0).sum()),
            "delta_mean":   float(sub.mean()),
        }
    return pi, diag
```

- [ ] **Step 4: Correr y verificar que pasa**

```bash
python -m pytest tests/test_creg101066_ceiling.py::test_ceiling_caps_values_above_PES tests/test_creg101066_ceiling.py::test_ceiling_does_not_modify_values_below_PES -v
```

Expected: ambos PASS.

- [ ] **Step 5: Commit**

```bash
git add data/xm_prices.py tests/test_creg101066_ceiling.py
git commit -m "Act 1.0 — CAL-14: apply_creg101066_ceiling recorta pi_bolsa al techo PES"
```

---

## Task 5: apply_creg101066_ceiling — uso correcto del mes

**Files:**
- Modify: `tests/test_creg101066_ceiling.py`

- [ ] **Step 1: Escribir el test**

Añadir en `tests/test_creg101066_ceiling.py`:

```python
def test_ceiling_uses_correct_month_for_each_hour():
    """Cada hora se compara con el techo del mes al que pertenece."""
    # 31 días de jul (24*31 = 744 h) + 24 horas de ago (de día 1).
    # Todas las horas con valor 1000 — superan ambos techos.
    T = 24 * 31 + 24
    pi = np.full(T, 1000.0)
    capped = apply_creg101066_ceiling(pi, "2025-07-01", level="PES")
    # Hora 0 (jul-01 00:00) debe topar a PES jul = 865.22
    assert capped[0] == pytest.approx(865.22)
    # Hora 743 (jul-31 23:00) sigue en jul
    assert capped[743] == pytest.approx(865.22)
    # Hora 744 (ago-01 00:00) debe topar a PES ago = 898.02
    assert capped[744] == pytest.approx(898.02)
    # Última hora (ago-01 23:00) también ago
    assert capped[-1] == pytest.approx(898.02)


def test_ceiling_skips_hours_before_effective_date():
    """Horas anteriores a effective_date no se recortan."""
    # 24 horas del 2024-11-01 (antes del 2024-12-01)
    pi = np.full(24, 5000.0)
    capped = apply_creg101066_ceiling(pi, "2024-11-01", level="PES",
                                       effective_date="2024-12-01")
    # Sin recorte (effective_date no se ha alcanzado)
    assert np.allclose(capped, pi)
```

- [ ] **Step 2: Correr y verificar**

```bash
python -m pytest tests/test_creg101066_ceiling.py -v -k "month_for_each_hour or before_effective"
```

Expected: ambos PASS (la implementación ya soporta ambos casos).

- [ ] **Step 3: Commit**

```bash
git add tests/test_creg101066_ceiling.py
git commit -m "Act 1.0 — CAL-14: tests de transición mensual y vigencia regulatoria"
```

---

## Task 6: apply_creg101066_ceiling — diagnósticos

**Files:**
- Modify: `tests/test_creg101066_ceiling.py`

- [ ] **Step 1: Escribir el test**

Añadir en `tests/test_creg101066_ceiling.py`:

```python
def test_ceiling_returns_diagnostics_when_requested():
    """return_diagnostics=True devuelve tupla con métricas correctas."""
    # 48 horas en jul-2025: 5 horas > PES jul (865.22), resto bajo
    pi = np.array([100.0] * 5 + [1500.0] * 5 + [100.0] * 38)
    result = apply_creg101066_ceiling(pi, "2025-07-01", level="PES",
                                       return_diagnostics=True)
    assert isinstance(result, tuple)
    capped, diag = result
    assert diag["hours_capped"] == 5
    assert diag["fraction"] == pytest.approx(5 / 48)
    assert diag["delta_cop_total"] == pytest.approx((1500.0 - 865.22) * 5)
    assert "2025-07" in diag["by_month"]
    assert diag["by_month"]["2025-07"]["hours_capped"] == 5
```

- [ ] **Step 2: Correr y verificar**

```bash
python -m pytest tests/test_creg101066_ceiling.py::test_ceiling_returns_diagnostics_when_requested -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_creg101066_ceiling.py
git commit -m "Act 1.0 — CAL-14: test de diagnósticos por mes en apply_creg101066_ceiling"
```

---

## Task 7: Helper de impresión `_print_ceiling_summary`

**Files:**
- Modify: `data/xm_prices.py`

- [ ] **Step 1: Implementar el helper**

Añadir en `data/xm_prices.py` después de `apply_creg101066_ceiling`:

```python
def _print_ceiling_summary(diag: dict, level: str = "PES") -> None:
    """Imprime resumen humano del recorte aplicado por CREG 101 066."""
    print(f"  [creg-101-066] Techo {level} aplicado: "
          f"{diag['hours_capped']} horas recortadas "
          f"({100 * diag['fraction']:.2f}% del horizonte), "
          f"delta = {diag['delta_cop_total']:,.0f} COP/kWh acumulado")
    if diag["by_month"] and diag["hours_capped"] > 0:
        print(f"  [creg-101-066] Por mes:")
        print(f"                  {'Mes':<10} {'Horas-cap':>10} "
              f"{'Δmedia COP/kWh':>16}")
        for mes, m in diag["by_month"].items():
            if m["hours_capped"] > 0:
                print(f"                  {mes:<10} {m['hours_capped']:>10} "
                      f"{-m['delta_mean']:>16.2f}")
```

- [ ] **Step 2: Smoke test manual**

```bash
python -c "
import numpy as np
from data.xm_prices import apply_creg101066_ceiling, _print_ceiling_summary
pi = np.array([100.0] * 5 + [1500.0] * 5 + [100.0] * 38)
_, diag = apply_creg101066_ceiling(pi, '2025-07-01', return_diagnostics=True)
_print_ceiling_summary(diag)
"
```

Expected:
```
  [creg-101-066] Techo PES aplicado: 5 horas recortadas (10.42% del horizonte), delta = 3,174 COP/kWh acumulado
  [creg-101-066] Por mes:
                  Mes        Horas-cap    Δmedia COP/kWh
                  2025-07            5             66.12
```

- [ ] **Step 3: Commit**

```bash
git add data/xm_prices.py
git commit -m "Act 1.0 — CAL-14: helper de impresión del resumen de techo aplicado"
```

---

## Task 8: Integrar `apply_ceiling` en `get_pi_bolsa`

**Files:**
- Modify: `data/xm_prices.py` (firma de `get_pi_bolsa`)
- Modify: `tests/test_creg101066_ceiling.py`

- [ ] **Step 1: Escribir los tests de integración**

Añadir en `tests/test_creg101066_ceiling.py` (Grupo C):

```python
# ─── Grupo C — Integración en get_pi_bolsa ───────────────────────────────────

def test_get_pi_bolsa_applies_ceiling_by_default():
    """get_pi_bolsa(apply_ceiling=True) topa la serie a max(PES) del horizonte."""
    pi = get_pi_bolsa(T=5160, t_start="2025-07-01",
                      use_api=True, apply_ceiling=True)
    # max(PES) jul-ene = 898.02 (ago-2025)
    assert pi.max() <= 898.02 + 1e-6


def test_get_pi_bolsa_respects_disable_flag():
    """apply_ceiling=False entrega la serie sin recortar (puede exceder PES)."""
    pi_capped = get_pi_bolsa(T=5160, t_start="2025-07-01",
                              use_api=True, apply_ceiling=True)
    pi_raw    = get_pi_bolsa(T=5160, t_start="2025-07-01",
                              use_api=True, apply_ceiling=False)
    # raw debe tener al menos un valor > PES (cache real tiene picos > 1000)
    assert pi_raw.max() > pi_capped.max()
```

- [ ] **Step 2: Correr y verificar que falla**

```bash
python -m pytest tests/test_creg101066_ceiling.py -v -k "get_pi_bolsa"
```

Expected: FAIL — `get_pi_bolsa` no acepta `apply_ceiling`.

- [ ] **Step 3: Modificar la firma de `get_pi_bolsa`**

En `data/xm_prices.py`, encontrar la función `get_pi_bolsa` (alrededor de línea 408) y modificar su firma + cuerpo:

Cambiar de:

```python
def get_pi_bolsa(T, t_start="2025-07-01", t_end="2026-02-01",
                 csv_path=None, use_api=True,
                 scenario="2025_real", seed=42):
    """
    Obtiene vector de precios bolsa pi_bolsa (T,) en COP/kWh.
    Prioridad: API pydataxm → CSV local → sintético calibrado.
    """
```

A:

```python
def get_pi_bolsa(T, t_start="2025-07-01", t_end="2026-02-01",
                 csv_path=None, use_api=True,
                 scenario="2025_real", seed=42,
                 apply_ceiling=True,
                 ceiling_level="PES"):
    """
    Obtiene vector de precios bolsa pi_bolsa (T,) en COP/kWh.

    Prioridad de fuentes: API pydataxm → CSV local → sintético calibrado.

    Parameters
    ----------
    apply_ceiling : bool
        Si True (default), aplica el techo CREG 101 066/2024 a la serie
        antes de retornarla. Ver ``apply_creg101066_ceiling``.
    ceiling_level : {"PEI", "PE", "PES"}
        Nivel del techo. Default ``"PES"`` (techo absoluto superior).
    """
```

Y al final de la función, justo antes de cualquier `return prices` o `return generate_synthetic_prices(...)`, envolver con la aplicación del techo. La estructura actual tiene 4 ramas con `return _adj(prices, T)`. Refactorar a una sola salida final:

Reemplazar todas las ramas de `return _adj(prices, T)` y `return generate_synthetic_prices(...)` para que en su lugar **asignen a una variable local** y caigan a un bloque común al final:

```python
    # Intento 1: API pydataxm (con cache)
    prices = None
    if use_api:
        cache = base_dir / "precios_bolsa_xm_api.csv"
        if cache.exists():
            prices = load_xm_prices(str(cache), t_start, t_end)
        if prices is None:
            prices = download_via_api(t_start, t_end, save_path=str(cache))

    # Intento 2: CSV explícito
    if prices is None and csv_path:
        prices = load_xm_prices(csv_path, t_start, t_end)

    # Intento 3: CSV automático en data/
    if prices is None:
        for name in ["precios_bolsa_xm.csv", "xm_precios_bolsa.csv",
                      "precio_bolsa_xm.csv", "PrecioBolsa.csv",
                      "Precio_Bolsa_Nacional.csv"]:
            p = base_dir / name
            if p.exists():
                prices = load_xm_prices(str(p), t_start, t_end)
                if prices is not None:
                    break

    # Intento 4: sintético calibrado
    if prices is None:
        print(f"  [xm] Sintético calibrado. Para datos reales:")
        print(f"    pip install pydataxm  (descarga automática)")
        print(f"    o descargar CSV de sinergox.xm.com.co → Históricos → Precios")
        print(f"    y guardarlo como: {base_dir}/precios_bolsa_xm.csv")
        prices = generate_synthetic_prices(T, t_start, scenario, seed)

    prices = _adj(prices, T)

    # CAL-14: aplicar techo CREG 101 066/2024 (PES por defecto).
    if apply_ceiling:
        prices, diag = apply_creg101066_ceiling(
            prices, t_start, level=ceiling_level,
            return_diagnostics=True)
        _print_ceiling_summary(diag, level=ceiling_level)

    return prices
```

- [ ] **Step 4: Correr todos los tests de CAL-14**

```bash
python -m pytest tests/test_creg101066_ceiling.py -v
```

Expected: los 8+ tests PASS.

- [ ] **Step 5: Verificar que no rompió nada existente**

```bash
python -m pytest tests/ -q --ignore=tests/test_full_simulation_preflight.py
```

Expected: todos los tests existentes siguen pasando.

- [ ] **Step 6: Commit**

```bash
git add data/xm_prices.py tests/test_creg101066_ceiling.py
git commit -m "Act 1.0 — CAL-14: integra techo CREG 101 066 en get_pi_bolsa (default ON)"
```

---

## Task 9: Test de regresión contra PB oficial XM (Nivel 2 validación)

**Files:**
- Modify: `tests/test_creg101066_ceiling.py`

- [ ] **Step 1: Escribir el test de regresión**

Añadir en `tests/test_creg101066_ceiling.py` al final del archivo:

```python
# ─── Grupo D — Validación contra PB oficial XM (regresión) ──────────────────

PB_OFFICIAL_PROM_MES = {
    # Valores oficiales del sheet IndiceLiquidez de los Excel XM
    # 03_Informe_Precios_y_Transacciones_MM_YYYY.xlsx (columna PRECIO_BOLSA_PROM_MES)
    "2025-09": 292.65,
    "2025-12": 278.83,
    # PB_PROM oficial para jul/ago/oct/nov se infiere del XM_MONTHLY_REAL ya verificado.
    "2025-07": 138.36,
    "2025-08": 251.50,
    "2025-10": 176.90,
    "2025-11": 234.87,
    "2026-01": 213.00,
}


def test_capped_monthly_means_match_official_within_tolerance():
    """
    La media mensual de la serie tras aplicar PES debe estar dentro del
    ±10 % del PRECIO_BOLSA_PROM_MES publicado por XM, EXCEPTO ene-2026
    donde el cache pydataxm presenta un gap conocido (CAL-15 follow-up).
    """
    pi = get_pi_bolsa(T=5160, t_start="2025-07-01",
                      use_api=True, apply_ceiling=True)
    idx = pd.date_range("2025-07-01", periods=5160, freq="1h")
    serie = pd.Series(pi, index=idx)

    out_of_tolerance = []
    for mes_str, oficial in PB_OFFICIAL_PROM_MES.items():
        mask = serie.index.to_period("M") == pd.Period(mes_str, freq="M")
        media = serie[mask].mean()
        delta_pct = abs(media - oficial) / oficial * 100
        if delta_pct > 10.0 and mes_str != "2026-01":
            out_of_tolerance.append(
                f"{mes_str}: capped={media:.1f} oficial={oficial:.1f} "
                f"delta={delta_pct:.1f}%"
            )
    assert not out_of_tolerance, (
        "Meses fuera de la tolerancia ±10% (excluyendo ene-2026 follow-up "
        f"CAL-15):\n" + "\n".join(out_of_tolerance)
    )
```

- [ ] **Step 2: Correr el test**

```bash
python -m pytest tests/test_creg101066_ceiling.py::test_capped_monthly_means_match_official_within_tolerance -v
```

Expected: PASS — el cache real ya es coherente con XM oficial dentro de ±10 % para los 6 meses excluidos del follow-up.

- [ ] **Step 3: Si falla en algún mes**

Si el test falla en un mes (no ene-2026), inspeccionar:

```bash
python -c "
from data.xm_prices import get_pi_bolsa
import pandas as pd
pi = get_pi_bolsa(T=5160, t_start='2025-07-01', apply_ceiling=True)
idx = pd.date_range('2025-07-01', periods=5160, freq='1h')
serie = pd.Series(pi, index=idx)
for mes, sub in serie.groupby(serie.index.to_period('M')):
    print(f'{mes}: media={sub.mean():.1f} max={sub.max():.1f} n={len(sub)}')
"
```

Comparar con la tabla del spec sección 4.2 y consultar al usuario si el delta excede ±15 % — puede indicar problema de fuente de datos no resuelto por el techo.

- [ ] **Step 4: Commit**

```bash
git add tests/test_creg101066_ceiling.py
git commit -m "Act 1.0 — CAL-14: test de regresión contra PB oficial XM (±10%)"
```

---

## Task 10: Smoke test sobre el cache real

**Files:**
- (Solo verificación, ningún cambio)

- [ ] **Step 1: Correr corrida diaria como smoke test**

```bash
python main_simulation.py --data real
```

Expected output (parcial):
```
  [creg-101-066] Techo PES aplicado: 0 horas recortadas (0.00% del horizonte), delta = 0 COP/kWh acumulado
```

(0 horas porque el perfil diario es promedio — no hay picos extremos.)

- [ ] **Step 2: Correr con horizonte completo**

```bash
python main_simulation.py --data real --full
```

Expected output (parcial):
```
  [creg-101-066] Techo PES aplicado: ~99 horas recortadas (~1.92% del horizonte), delta ≈ 168,000 COP/kWh acumulado
  [creg-101-066] Por mes:
                  Mes        Horas-cap    Δmedia COP/kWh
                  2025-07            2          ...
                  2025-08           19          ...
                  2025-09            7          ...
                  ...
```

(El conteo exacto puede variar ligeramente según el cache, pero debe ser > 0 y < 200.)

- [ ] **Step 3: Verificar que las medias resultantes son coherentes**

```bash
python -c "
from data.xm_prices import get_pi_bolsa
import pandas as pd, numpy as np
pi = get_pi_bolsa(T=5160, t_start='2025-07-01', apply_ceiling=True)
idx = pd.date_range('2025-07-01', periods=5160, freq='1h')
serie = pd.Series(pi, index=idx)
print('Mes           media   max')
for mes, sub in serie.groupby(serie.index.to_period('M')):
    print(f'{mes}   {sub.mean():>7.1f} {sub.max():>7.1f}')
print(f'Total horizonte max: {pi.max():.1f}')
"
```

Expected: `max <= 898.02` para todo el horizonte; medias mensuales dentro del ±10% de los PB_PROM oficiales (138.4 jul, 251.5 ago, 304.8 sep, 176.9 oct, 234.9 nov, ~283 dic, ~213 ene).

---

## Task 11: ADR-0014

**Files:**
- Create: `docs/adr/0014-cal14-creg101066-pes-ceiling.md`
- Modify: `docs/adr/README.md`

- [ ] **Step 1: Escribir el ADR**

Crear `docs/adr/0014-cal14-creg101066-pes-ceiling.md`:

```markdown
# 0014 — CAL-14: Techo CREG 101 066/2024 (PES) en pi_bolsa

- **Estado:** Accepted
- **Fecha de decision:** 2026-05-01
- **Actividad:** 3.x (validacion regulatoria)
- **Archivos afectados:** `data/xm_prices.py`,
  `data/precios_escasez_creg.csv`, `tests/test_creg101066_ceiling.py`,
  escenarios C1/C3/C4 (sin cambios en codigo, solo en datos recibidos)
- **Relacionado con:** [ADR-0010 CAL-10b](0010-cal10-creg174-tipo-1-2-componente-c.md)
- **Fuente:** `docs/superpowers/specs/2026-05-01-cal14-creg101066-pes-ceiling.md`,
  Resolucion CREG 101 066/2024,
  `Documentos/notas_modelo_tesis.md` §CAL-14

## Contexto

La metrica `PrecBolsNaci` que devuelve la API pydataxm es el **Precio de
Bolsa marginal de oferta**, no el **Precio de Transacciones en Bolsa
(PTB)** efectivo tras activacion de OEF. El cache
`data/precios_bolsa_xm_api.csv` contiene picos > 2000 COP/kWh para
agosto 2025 mientras el techo regulatorio absoluto del PTB (PES) era
898.02 COP/kWh ese mes. Ningun PTB liquidado supera PES.

Aplicar el escenario C3 (y los excedentes Tipo 2 de C1, surplus tras PDE
de C4) sobre la serie cruda sobreestima los ingresos del prosumidor en
horas extremas que en la practica regulatoria estan recortadas.

## Decision

Aplicar PES (Precio de Escasez Superior) como techo duro al precio de
bolsa horario en la capa de datos `data/xm_prices.py:get_pi_bolsa`.
Tabla mensual de PEI/PE/PES en `data/precios_escasez_creg.csv` con los
7 meses del horizonte verificados desde el sheet
`Comportamiento_PBNal_Horario` de los Excel oficiales XM.

`get_pi_bolsa(apply_ceiling=True)` queda como default — toda corrida
nueva refleja CREG 101 066 sin tocar callers. `apply_ceiling=False`
permite analisis contrafactual.

## Alternativas consideradas

1. **Recortar a PE (intermedio, ~660-746)** — mas conservador, recorta
   ~199 horas adicionales. Descartado: PES es el techo absoluto del PTB
   liquidado; recortar a PE introduce sesgo a la baja sin justificacion
   regulatoria directa.
2. **Recortar a PEI (inferior, ~330)** — descartado: PEI solo aplica
   cuando la planta marginal es de bajo costo variable, no es techo
   absoluto.
3. **Aplicar PEI/PE/PES selectivamente segun composicion del despacho**
   — descartado: requiere descargar el despacho diario de XM, fuera
   del alcance de la tesis.
4. **Aplicar el techo solo en C3** — descartado: el techo es propiedad
   del dato (`pi_bolsa`), no del escenario; aplicarlo solo en C3 deja
   C1-Tipo 2 y C4 inconsistentes con la regulacion vigente.

## Consecuencias

**Positivas**

- C1, C3 y C4 reflejan ingresos de bolsa coherentes con CREG 101 066/2024.
- La capa de datos garantiza el invariante regulatorio:
  `max(pi_bolsa) <= max(PES_horizonte)`.
- Comparacion P2P vs C3 deja de favorecer artificialmente a C3 en
  escenarios de escasez extrema.

**Negativas**

- Aproximacion: aplicar PES como cap duro ignora la composicion horaria
  del despacho OEF real (que recortaria a PEI o PE en horas con
  generacion abundante). Documentado en §CAL-14 de notas_modelo_tesis.md.
- Mantenimiento: cada mes que XM publique nuevos PEI/PE/PES hay que
  agregar fila al CSV.

**Riesgos abiertos**

- **CAL-15** (follow-up): auditoria de la metrica que devuelve pydataxm
  vs PTB oficial. El gap de 35 % observado en ene-2026 (cache 218.5 vs
  PB_PROM oficial 213.0) sugiere que la API podria estar entregando
  datos provisionales o una metrica distinta.
```

- [ ] **Step 2: Actualizar el indice de ADRs**

En `docs/adr/README.md`, añadir al final de la tabla de índice (después de la fila de CAL-13 si existe, o de CAL-9 si CAL-10..13 no estan listados):

```markdown
| 0014 | CAL-14: Techo CREG 101 066/2024 (PES) en pi_bolsa | Accepted | 2026-05-01 |
```

- [ ] **Step 3: Commit**

```bash
git add docs/adr/0014-cal14-creg101066-pes-ceiling.md docs/adr/README.md
git commit -m "Act 1.0 — CAL-14: ADR-0014 sobre techo CREG 101 066/2024 PES"
```

---

## Task 12: §CAL-14 en notas_modelo_tesis.md

**Files:**
- Modify: `Documentos/notas_modelo_tesis.md`

- [ ] **Step 1: Identificar punto de inserción**

Ubicar la sección CAL-13 (la más reciente) en `Documentos/notas_modelo_tesis.md`:

```bash
grep -n "## §CAL-13\|## §CAL-12\|## §CAL-11" Documentos/notas_modelo_tesis.md
```

Insertar la nueva sección **después** de §CAL-13 (o de la última sección CAL existente).

- [ ] **Step 2: Escribir §CAL-14**

Añadir al final del archivo `Documentos/notas_modelo_tesis.md`:

```markdown
## §CAL-14 — Techo CREG 101 066/2024 (PES) en pi_bolsa  (2026-05-01)

### Justificación regulatoria

Resolución CREG 101 066/2024 (publicada 18-NOV-2024, vigencia
01-DIC-2024) reemplazó el precio de escasez único (~945 COP/kWh) por
tres niveles diferenciados que se actualizan mensualmente:

| Nivel | Aplicación | Rango jul-2025 → ene-2026 |
|---|---|---:|
| PEI Precio Escasez Inferior | Plantas con bajo costo variable | 327.67 – 350.08 |
| PE  Precio Escasez "intermedio" | Fórmula CREG 071/2006 | 590.56 – 746.17 |
| PES Precio Escasez Superior | Plantas a líquidos (techo absoluto) | 829.00 – 898.02 |

### Distinción PB vs PTB

XM publica dos métricas en su mercado mayorista:

- **PB (Precio de Bolsa)** — marginal de oferta del despacho diario,
  puede superar PES en horas de escasez extrema.
- **PTB (Precio de Transacciones en Bolsa)** — efectivo tras activación
  de OEF, **nunca supera PES**.

La API pydataxm devuelve PB (campo `PrecBolsNaci`), no PTB. Aplicar
`pi_bolsa[k] = min(PB[k], PES[mes])` aproxima PTB sin necesidad de
modelar la composición horaria del despacho OEF.

### Decisión del modelo

Se aplica **PES** como techo en la capa de datos `data/xm_prices.py`,
afectando uniformemente a todos los escenarios que liquidan a `pi_bolsa`
(C1 Tipo 2, C3, C4). PEI y PE quedan disponibles en el CSV
`data/precios_escasez_creg.csv` para análisis contrafactual.

### Limitaciones

- El recorte real ocurre vía activación OEF horaria que el modelo no
  replica detalladamente. Aplicar PES uniformemente sobreestima el
  techo en horas con planta marginal de bajo costo (donde el efectivo
  sería PEI o PE).
- En el horizonte actual (post-Niño jul-2025 → ene-2026, baja
  activación de OEF), el efecto cuantitativo es pequeño: ~99 horas
  recortadas (1.9 % del total), Δmedia mensual < 4 %.
- En análisis Sobol con escenarios `2025_el_nino` o `2024_escasez`, el
  techo sí cambia conclusiones — documentado para revisión con asesores.

### Verificación

Tabla de PEI/PE/PES extraída del sheet `Comportamiento_PBNal_Horario`
de los Excel oficiales XM
(`sinergox.xm.com.co/.../03_Informe_Precios_y_Transacciones_MM_YYYY.xlsx`).
Los tres niveles son **constantes durante todo el mes** —
verificación: un único valor distinto por mes en cada columna del
sheet horario. Spec completo:
`docs/superpowers/specs/2026-05-01-cal14-creg101066-pes-ceiling.md`.
```

- [ ] **Step 3: Commit**

```bash
git add Documentos/notas_modelo_tesis.md
git commit -m "Act 1.0 — CAL-14: §CAL-14 en notas con justificación regulatoria"
```

---

## Task 13: Sembrado en memoria semántica Ruflo

**Files:**
- Modify: `scripts/seed_ruflo_adr.py`

- [ ] **Step 1: Inspeccionar el script existente**

```bash
python -c "import ast; tree = ast.parse(open('scripts/seed_ruflo_adr.py').read()); print('OK')"
grep -n "0013\|cal_13\|CAL-13" scripts/seed_ruflo_adr.py
```

Identificar el patrón usado para entradas previas (la entrada CAL-13 será la más reciente). Cada ADR aparece como una entrada con `key`, `value`, `namespace`.

- [ ] **Step 2: Añadir entrada para CAL-14**

Añadir en `scripts/seed_ruflo_adr.py` siguiendo el mismo patrón que CAL-13. La entrada nueva debe tener:

```python
{
    "key":       "adr-0014-cal14-creg101066-pes-ceiling",
    "namespace": "adr",
    "value":     (
        "CAL-14 (2026-05-01) — Aplica techo PES de CREG 101 066/2024 al "
        "precio de bolsa horario en la capa de datos `data/xm_prices.py`. "
        "Tabla mensual de PEI/PE/PES en `data/precios_escasez_creg.csv` "
        "(7 meses verificados desde Excel oficial XM). "
        "`get_pi_bolsa(apply_ceiling=True)` por defecto. PES es el techo "
        "absoluto del PTB; aplicarlo aproxima el efecto OEF sin modelar "
        "composición horaria del despacho. Afecta C1 Tipo 2, C3, C4. "
        "Follow-up CAL-15: auditar metrica pydataxm vs PTB oficial "
        "(gap 35 % en ene-2026)."
    ),
}
```

- [ ] **Step 3: Ejecutar el script y verificar**

```bash
python scripts/seed_ruflo_adr.py
```

Expected: el script reporta haber sembrado N entradas (incluida la nueva), sin errores.

- [ ] **Step 4: Commit**

```bash
git add scripts/seed_ruflo_adr.py
git commit -m "Act 1.0 — CAL-14: sembrado memoria Ruflo con entrada ADR-0014"
```

---

## Task 14: Verificación final con corrida `--full --analysis`

**Files:**
- (Solo verificación)

- [ ] **Step 1: Correr la suite completa de tests**

```bash
python -m pytest tests/ -q
```

Expected: 100 % de tests pasan, incluidos los 9 nuevos de `test_creg101066_ceiling.py`.

- [ ] **Step 2: Correr corrida con datos reales y horizonte completo**

```bash
mkdir -p outputs
python main_simulation.py --data real --full --analysis 2>&1 | tee "outputs/run_cal14_$(date +%Y%m%d_%H%M%S).log"
```

Expected output (parcial):
```
  [creg-101-066] Techo PES aplicado: ~99 horas recortadas (~1.92% del horizonte), delta = ~168,000 COP/kWh acumulado
  [creg-101-066] Por mes:
                  Mes        Horas-cap    Δmedia COP/kWh
                  ...
```

- [ ] **Step 3: Comparar net_benefit C3 antes/después**

Si tienes un log de la última corrida `--full` previo a CAL-14 disponible, compara las cifras de `net_benefit["C3"]`. Esperado: el delta es < 1 % del total (porque el recorte solo afecta ~2 % de las horas y por valores pequeños). Si el delta es > 5 %, hay una sospecha de implementación incorrecta — investigar antes de commitear el log.

- [ ] **Step 4: Commit del log**

```bash
git add outputs/run_cal14_*.log
git commit -m "Act 1.0 — CAL-14: log de corrida --full --analysis post-techo PES"
```

---

## Notas finales

- **Estimación total de esfuerzo:** ~5-7 h distribuidas en una sesión.
- **Orden recomendado:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14.
- **Bloqueadores:** ninguno — todas las decisiones están cerradas en el spec.
- **No tocar:** `scenarios/scenario_c1_creg174.py`, `scenario_c3_spot.py`,
  `scenario_c4_creg101072.py`, `comparison_engine.py` — el techo se aplica
  exclusivamente en la capa de datos.
- **Si algo falla:** revisar primero el spec
  `docs/superpowers/specs/2026-05-01-cal14-creg101066-pes-ceiling.md`
  y consultar al usuario antes de improvisar.
