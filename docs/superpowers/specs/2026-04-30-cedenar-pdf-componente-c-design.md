# Reemplazar la aproximación proporcional del componente C por el dato real (Cvm + COT) del CSV Cedenar

- **Fecha:** 2026-04-30
- **Autor:** Brayan S. Lopez-Mendez
- **Etiqueta:** CAL-10b (refinamiento de CAL-10)
- **Relacionado:** ADR-010 (CAL-10), ADR-009 (CAL-9), ADR-008 (CAL-8)
- **Memoria semántica:** `tesis-p2p / cal_10_componente_c_definicion_cvm_plus_cot`

## Contexto

CAL-10 (2026-04-30) introdujo el descuento del componente C de
Comercialización en la permuta Tipo 1 del escenario C1 (CREG 174/2021
arts. 22-23). La implementación actual usa una aproximación
proporcional:

```python
C_FRACTION = CU_COMPONENTS_2025["C"] / sum(CU_COMPONENTS_2025.values())
#          = 90 / 650 ≈ 0.1385
pi_C = pi_gs * C_FRACTION
```

Inspección directa del PDF `data/cedenar_pdfs/tarifa_2026-04.pdf`
muestra que los valores reales son significativamente más altos:

| Nivel Tensión | Cvm (COP/kWh) | COT (COP/kWh) | C_total | C/CU |
|---|---:|---:|---:|---:|
| NT1 | 176,41 | 38,65 | 215,06 | 24 % aprox. |
| NT2 oficial (799,16) | 176,41 | 38,73 | 215,14 | **26,9 %** |
| NT2 comercial (958,99) | 176,41 | 38,73 | 215,14 | 22,4 % |
| NT3 oficial (707,33) | 176,41 | 21,79 | 198,20 | 28,0 % |

La fracción real es **casi el doble** de la aproximación 13,85 %.
Mantener la aproximación introduce un sesgo sistemático: subestima el
"peaje" de comercialización y sobreestima la rentabilidad del AGPE en
~ 8-12 % adicional sobre lo ya corregido en CAL-10.

**Hallazgo crítico:** el CSV `data/tarifas_cedenar_mensual.csv` ya
contiene las columnas `Cvm` y `COT` pobladas para los 13 meses del
horizonte (abr-2025 → abr-2026), extraídas manualmente de los PDFs. El
loader `load_monthly_tariffs` en `data/cedenar_tariff.py` ya las lee
como columnas opcionales. **No hay que parsear PDFs** — los datos
están listos para consumir.

## Decisión regulatoria locked-in

El componente C operativo en CAL-10b se define como **Cvm + COT**
(no solo Cvm puro, no incluyendo Rm), por las siguientes razones
documentadas en memoria semántica:

1. CREG 174/2021 cita textualmente "componente C". La lectura semántica
   estricta apuntaría a Cvm puro (margen de comercialización CREG
   119/2007 art. 11), pero las metodologías tarifarias vigentes (CREG
   101-028/2023) reconocen que el comercializador no puede absorber
   las obligaciones tributarias derivadas de la prestación del
   servicio.
2. El COT (Costo Operativo Tributario) **no es un impuesto aislado**:
   es un costo operativo que el regulador permite integrar en la
   estructura de costos de atención al usuario. En la liquidación real
   de la factura CEDENAR el usuario sigue pagando Cvm + COT aunque
   haya permuta de Tipo 1.
3. Asumir solo Cvm subestimaría el "peaje" e inflaría artificialmente
   la rentabilidad del AGPE.
4. Rm (Restricciones del SIN) queda fuera: es matemáticamente
   independiente en `CU = G + T + D + C + P + R`; CREG 174 limita el
   cobro sobre permuta al componente de comercialización, no a
   restricciones.

La postura **Cvm + COT** representa el peor escenario regulatorio
posible para la inyección de excedentes Tipo 1, lo que fuerza al
modelo a buscar eficiencia real (almacenamiento, gestión de demanda)
en lugar de depender de interpretación laxa de la norma.

## Diseño

### 1. API y flujo de datos

#### 1.1 Nueva función pública en `data/cedenar_tariff.py`

```python
def cvm_plus_cot_per_agent_hourly(
    agent_names: list[str],
    idx: pd.DatetimeIndex,
    csv_path: str | Path | None = None,
    fallback_fraction: float | None = None,
) -> np.ndarray:
    """
    Devuelve matriz (N, T) en COP/kWh con (Cvm + COT) por (agente, hora),
    derivada del CSV mensual Cedenar y del INSTITUTION_PROFILE.

    Cada hora hereda Cvm + COT del mes calendario que la contiene,
    indexado por (categoria, nivel_tension, propiedad) del agente.
    """
```

Análoga 1-a-1 al patrón `pi_gs_per_agent_hourly` de CAL-9 (misma firma,
mismo manejo de `idx`, mismo `INSTITUTION_PROFILE`). Internamente
reutiliza `load_monthly_tariffs` y un helper privado nuevo
`_lookup_cvm_plus_cot`.

#### 1.2 Helper privado

```python
def _lookup_cvm_plus_cot(
    df: pd.DataFrame,
    mes_key: str,
    profile: TariffProfile,
    warned: set[str] | None = None,
) -> float | None:
    """
    Devuelve Cvm + COT para (mes, profile). Si falta el dato (mes
    ausente del CSV o NaN en alguna celda), warning una vez por mes
    y retorna None — el caller decide si caer a fallback proporcional
    o cero.
    """
```

#### 1.3 Wiring en `main_simulation.py`

Espejo del bloque CAL-9 actual en `main_simulation.py:232-240`:

```python
# CAL-10b: componente C real desde tarifas_cedenar_mensual.csv
if use_real_data:
    if full_horizon:
        component_c_arg = cvm_plus_cot_per_agent_hourly(agent_names, index_full)
    elif single_day:
        component_c_arg = cvm_plus_cot_per_agent_hourly(agent_names, idx_day)
    else:
        component_c_arg = "auto"   # perfil diario: aprox. proporcional 13.85 %
else:
    component_c_arg = "auto"        # sintético: 13.85 % de pi_gs sintético
```

Banner informativo actualizado en el log:

```python
print("    [CAL-10b] C1 (CREG 174 arts. 22-23): permuta Tipo 1 a "
      "(pi_gs - C), C = Cvm + COT real desde CSV Cedenar; "
      "excedentes Tipo 2 a bolsa horaria post-Hx.")
```

#### 1.4 Propagación a `comparison_engine` y `monthly_report`

`comparison_engine.run_comparison` agrega parámetro:

```python
component_c: Union[str, float, np.ndarray] = "auto"
```

Default `"auto"` para backward compat con tests sintéticos. Lo pasa a
`run_c1_creg174(..., component_c=component_c)`.

`analysis/monthly_report.compute_monthly_metrics` agrega el mismo
parámetro y lo slicea por mes igual que `pi_gs`:

```python
if isinstance(component_c, np.ndarray):
    cc_m = component_c[:, idx_arr]
else:
    cc_m = component_c
c1 = run_c1_creg174(..., component_c=cc_m)
```

### 2. Comportamiento ante datos faltantes

Patrón coherente con `_lookup_pi_gs` de CAL-8/9: **warning + fallback
proporcional**, con responsabilidad dividida entre dos capas.

#### Capa 1 — Helper `cvm_plus_cot_per_agent_hourly`

Se ocupa **solo del lookup en el CSV**. Si `_lookup_cvm_plus_cot`
retorna `None` para algún mes (mes ausente, Cvm o COT NaN), la celda
se marca con `np.nan`:

```python
out[n, hour_idx] = np.nan if c_real is None else c_real
```

El warning se emite una vez por mes ausente, indicando que el caller
debe completar la matriz.

#### Capa 2 — Helper existente `as_component_c_array`

Ya recibe `pi_gs_arr` como parámetro (CAL-10). Se extiende para
detectar NaN en la matriz pasada y rellenarlos proporcionalmente:

```python
arr = np.asarray(component_c, dtype=float)
nan_mask = np.isnan(arr)
if nan_mask.any():
    arr = arr.copy()
    arr[nan_mask] = pi_gs_arr[nan_mask] * C_FRACTION
return arr
```

Así el flujo queda simétrico al de pi_gs: la matriz puede mezclar
celdas con dato real y celdas con fallback proporcional, sin que el
helper de lookup necesite conocer pi_gs.

En la práctica el CSV cubre los 13 meses del horizonte simulado, así
que este path no se ejercita en runs operativos — está solo por
robustez.

### 3. Cobertura de tests

#### 3.1 Helper aislado — `tests/test_cedenar_cvm_cot.py` (nuevo)

```python
test_cvm_plus_cot_per_agent_hourly_shape
test_cvm_plus_cot_per_agent_hourly_lookup_aligns_with_csv
    # 2026-04 oficial NT2 cedenar → 174.69 + 40.27 = 214.96
    # 2026-04 comercial NT2 cedenar → 174.69 + 40.27 = 214.96
test_cvm_plus_cot_constante_dentro_de_un_mes
```

#### 3.2 Integración con C1 — extiende `tests/test_c1_creg174_v2.py`

```python
test_c1_acepta_array_NT_como_component_c
test_c1_csv_C_mayor_que_proporcional
    # Con C real ≈ 22 % del CU, savings cae más que con C_FRACTION=0.1385
```

#### 3.3 End-to-end — sin tests nuevos

Los smoke tests existentes (`python main_simulation.py`,
`--data real`, `--full --analysis`) verifican el wiring sin
asercones numéricas — se documenta en `REPORTE_AVANCES.md` el delta
observado.

### 4. Archivos a modificar

| Archivo | Cambio |
|---|---|
| `data/cedenar_tariff.py` | Agregar `_lookup_cvm_plus_cot`, `cvm_plus_cot_per_agent`, `cvm_plus_cot_per_agent_hourly`. ~80 líneas. |
| `main_simulation.py` | Bloque `component_c_arg` (~10 líneas) + banner actualizado. Pasar al `run_comparison`. |
| `scenarios/comparison_engine.py` | Aceptar `component_c` y propagar a `run_c1_creg174`. ~5 líneas. |
| `analysis/monthly_report.py` | Aceptar `component_c_full` y slicear por mes. ~10 líneas. |
| `tests/test_cedenar_cvm_cot.py` | Nuevo, 3 tests. ~80 líneas. |
| `tests/test_c1_creg174_v2.py` | +2 tests. |
| `Documentos/notas_modelo_tesis.md` | Actualizar §CAL-10 con el delta numérico post-CAL-10b. |
| `outputs/REPORTE_AVANCES.md` | Reemplazar números post-CAL-10 con post-CAL-10b. |
| `docs/adr/0010-cal10-creg174-tipo-1-2-componente-c.md` | Anexo "CAL-10b: refinamiento Cvm+COT real" o ADR nuevo 0011. |

### 5. Verificación

```powershell
# Nuevos tests
python -m pytest tests/test_cedenar_cvm_cot.py tests/test_c1_creg174_v2.py -v

# Suite completa
python -m pytest tests/ -q

# Smoke sintético
python main_simulation.py

# Real --full + diff
python main_simulation.py --data real --full --analysis 2>&1 | tee outputs/run_2026-04-30b.log
```

**Criterio de aceptación**:
- Todos los tests verdes (≥53/53 con los 2 nuevos).
- Caso sintético sin errores en ~15 s (sin cambios numéricos: usa
  `component_c="auto"` por default).
- Run `--full` muestra C1 < CAL-10 (aprox. otro −8 a −12 %), RPE
  posiblemente negativo (P2P agregadamente mejor que C1).
- Banner `[CAL-10b]` visible al inicio del bloque [3/5].

### 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| El CSV tiene Cvm para todos los meses pero no para todas las combinaciones (categoría, NT, propiedad) | Test de cobertura: para cada institución MTE, verificar que las 13 filas necesarias existen al cargar. |
| Subestimación de C en NT3 (COT 21.79) vs NT2 (COT 38.73) | No aplicable hoy: las 5 instituciones MTE son NT2. Documentado en INSTITUTION_PROFILE. |
| Cambio numérico cualitativo: P2P pasa de inferior a superior agregadamente vs C1 | Documentación honesta en notas_modelo_tesis.md y REPORTE_AVANCES.md. La interpretación regulatoria sigue siendo defendible (CREG 174 estricto). |
| Tests CAL-9 (test_pi_gs_temporal.py) podrían romper si pasan `component_c="auto"` y la matriz incluye Cvm+COT real | No aplica: esos tests usan datos sintéticos sin CSV; `"auto"` se mantiene como aproximación proporcional cuando no hay matriz real. |

### 7. Alcance explícitamente fuera

- Parsing automático de PDFs Cedenar — el CSV manual ya cubre el horizonte; YAGNI.
- Modificar el algoritmo de Hx, la asimetría auto/permuta o la valoración Tipo 2 — esos son CAL-10 ya estable.
- Cambiar el EMS interno (`core/ems_p2p.py`) — sigue usando escalar comunitario por las razones documentadas en ADR-009.

## Próximos pasos

Después de aprobación de este spec → invocar `superpowers:writing-plans` para producir el plan de implementación paso a paso.
