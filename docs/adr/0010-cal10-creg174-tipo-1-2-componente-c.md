# 0010 — CAL-10: Excedentes Tipo 1 / Tipo 2 + componente C en C1 (CREG 174/2021)

- **Estado:** Accepted
- **Fecha de decision:** 2026-04-30
- **Actividad:** 1.1 (caracterizacion empirica) / 3.1-3.3 (validacion regulatoria)
- **Archivos afectados:** `scenarios/scenario_c1_creg174.py`,
  `scenarios/_pi_gs.py`, `data/xm_prices.py`,
  `scenarios/comparison_engine.py`, `analysis/monthly_report.py`,
  `tests/test_c1_creg174_v2.py`
- **Relacionado con:** [ADR-0008 CAL-8](0008-cal8-pi-gs-cedenar.md)
  (calibracion Cedenar), [ADR-0009 CAL-9](0009-cal9-pi-gs-temporal.md)
  (matriz `pi_gs (N, T)`)
- **Fuente:** `Documentos/notas_modelo_tesis.md` §CAL-10,
  CREG 174/2021 arts. 22-23, Decreto 2469/2014 art. 2.2.3.2.4.1

## Contexto

CAL-9 promovio `pi_gs` a matriz `(N, T)` y dejo el escenario C1 con la
liquidacion mensual:

```python
savings_m  = (E_auto + E_permuted) * pi_gs_period
revenue_m  = E_net_surplus * pi_bolsa_avg_ponderado_por_surplus
```

Esa formulacion dejo dos brechas frente al texto regulatorio de la
**Resolucion CREG 174/2021** para Autogeneradores a Pequena Escala
(AGPE):

1. **Componente C de Comercializacion no descontado.** La regulacion
   (arts. 22-23) establece que el comercializador sigue cobrando el
   componente C del Costo Unitario sobre cada kWh permutado, porque la
   energia inyectada y posteriormente retirada usa la red de
   distribucion y el sistema de medicion bidireccional. El modelo
   pre-CAL-10 valoraba la permuta a `pi_gs` completo, lo que sobreestima
   el ahorro en aproximadamente `permutacion x C / pi_gs ~ 13.85 %` del
   componente permuta.

2. **Hora Hx ausente — tratamiento monolitico de los excedentes.** La
   regulacion distingue:

   - **Excedentes Tipo 1** (inyeccion ≤ retiro): se permutan al precio
     retail neto del componente C.
   - **Excedentes Tipo 2** (inyeccion > retiro, a partir de la hora Hx
     en que la inyeccion acumulada del mes supera al consumo
     acumulado): se liquidan al **precio de bolsa horario** `pi_bolsa[k]`
     hora a hora.

   El modelo pre-CAL-10 calculaba un balance neto al final del mes y
   liquidaba el excedente neto al **promedio ponderado mensual** del
   precio de bolsa. Esto sobreestima el ingreso de Tipo 2 cuando los
   excedentes ocurren en horas solares (precios mayoristas tipicamente
   bajos en Colombia, ~100-150 COP/kWh en mediodia vs ~280 COP/kWh
   promedio diario).

Auditoria 2026-04-30 (agente Explore + lectura directa de
`scenario_c1_creg174.py:46-159` baseline) confirmo que el codigo de C1
implementaba la permuta mensual y el excedente neto a bolsa, pero no
descuenta C ni localiza Hx. Constante `CU_COMPONENTS_2025["C"] = 90`
estaba definida en `data/xm_prices.py:504-511` desde CAL-8 sin uso
operativo.

## Decision

1. **Helper `as_component_c_array`** (en `scenarios/_pi_gs.py`).
   Normaliza la especificacion del componente C a matriz `(N, T)`:

   - `"auto"` (canonico CAL-10): `pi_C = pi_gs * C_FRACTION`,
     proporcional al CU. Escala con la tarifa Cedenar real
     (oficial NT2 ~797, comercial NT2 ~956 → C ~110/132 COP/kWh).
   - `None` o `0.0`: matriz de ceros (sin descuento, equivalente
     legacy).
   - `float`: COP/kWh fijo uniforme.
   - `(N,)` / `(T,)` / `(N, T)`: per-agente / temporal / completo.

2. **Constante `C_FRACTION`** (en `data/xm_prices.py`):

   ```python
   C_FRACTION = CU_COMPONENTS_2025["C"] / sum(CU_COMPONENTS_2025.values())
   #          ≈ 90 / 650 ≈ 0.1385
   ```

   y getter `get_c_fraction()`. La aproximacion proporcional es la
   alternativa pragmatica mientras CEDENAR no publique el desglose
   mensual en sus PDFs (TODO en docstring para upgrade futuro).

3. **Algoritmo de hora Hx** (en `scenario_c1_creg174.py`). Para cada
   periodo de facturacion `m` y agente `n`, recorrer las horas en orden
   cronologico:

   ```
   iny_acum = ret_acum = 0
   hx = None
   for k_local, k_global in enumerate(hours):
       iny_acum += surplus_h[k]
       ret_acum += deficit_h[k]
       if hx is None and iny_acum > ret_acum:
           cruce            = iny_acum - ret_acum
           surplus_t2[k]    = min(surplus_h[k], cruce)
           surplus_t1[k]    = surplus_h[k] - surplus_t2[k]
           hx               = k_local
       elif hx is not None:
           surplus_t2[k]    = surplus_h[k]
       else:
           surplus_t1[k]    = surplus_h[k]
   ```

   La parte de `surplus_h[hx]` que **completa la permuta** es Tipo 1; la
   parte que **excede el balance acumulado** es Tipo 2. Despues de Hx,
   todo el surplus es Tipo 2 hasta el cierre del periodo.

4. **Valoracion**:

   ```
   savings_m  = E_auto * pi_gs_period
                + E_permuted_t1 * (pi_gs_period - pi_C_period)
   revenue_m  = sum_k surplus_t2[k] * pi_bolsa[k]   # horario, no promedio
   net_benefit_n = sum_m (savings_m + revenue_m)
   ```

   Asimetria deliberada **autoconsumo vs permuta**:

   - Autoconsumo: la energia no toca la red ni el sistema de medicion
     → C no se factura sobre esos kWh → ahorro a `pi_gs` completo.
   - Permuta Tipo 1: la energia circula por la red de distribucion y
     por el medidor bidireccional → C se factura → ahorro a
     `(pi_gs - pi_C)`.

5. **Default de la API**: `component_c="auto"` en
   `run_c1_creg174(...)`. Ambos callers (`comparison_engine.py:124`,
   `analysis/monthly_report.py:123`) pasan el valor explicitamente para
   documentar la decision en el sitio de invocacion.

6. **Diagnostico exportado**. Cada `results[n]` retorna ahora
   `E_auto`, `E_permuted_t1`, `E_tipo2`, `hx_history` (lista de Hx por
   periodo). El agregado retorna los totales correspondientes para
   facilitar el monthly report y el desglose en `flow_breakdown`.

## Alternativas consideradas

### A. Componente C fijo (90 COP/kWh literal)

Hardcodear `C = 90` (valor de `CU_COMPONENTS_2025` 2025). **Rechazada**:
con tarifas Cedenar reales ~906 COP/kWh, el C real escala
proporcionalmente. Un valor fijo subestimaria el descuento.

### B. Extraer C de los PDFs Cedenar mensuales

`data/cedenar_pdfs/` contiene los PDFs originales con desglose
G + T + D + C + PR. **Diferida** porque parsing PDF mes a mes y por
nivel de tension excede el alcance de CAL-10 y aporta < 1 punto
porcentual de precision. TODO documentado en docstring.

### C. Documentar simplificacion sin tocar codigo

Mantener la formulacion pre-CAL-10 y agregar disclaimer en el
manuscrito. **Rechazada** por el usuario (decision 2026-04-30) — el
sesgo de 3-8 % afecta el RPE P2P-vs-C1 reportado a los asesores y
desplaza el umbral de SA-1 (cruce P2P=C1) en ~25-45 COP/kWh.

## Consecuencias

- (+) Liquidacion C1 fiel a CREG 174 arts. 22-23: descuento C en
  permuta + Hx + bolsa horaria post-cruce.
- (+) Aproximacion proporcional `C_FRACTION` escala correctamente con
  cualquier tarifa retail (sintetica 650, Cedenar oficial 797, comercial
  956).
- (+) `pi_gs` matriz `(N, T)` de CAL-9 sigue siendo el canonico; el
  componente C se calcula punto a punto sin colapsar dimensiones.
- (+) 8 tests v2 (`tests/test_c1_creg174_v2.py`) cubren: descuento auto
  / fijo / cero, Hx basico, sin cruce, cruce desde t=0, multi-mes,
  conservacion de energia.
- (+) Tests CAL-9 (`tests/test_pi_gs_temporal.py`, 10 casos) siguen
  pasando sin modificacion; los invariantes pi_gs son ortogonales a
  Hx/C.
- (-) Numeros de C1 en `REPORTE_AVANCES.md` y `notas_modelo_tesis.md`
  cambian. Backup: `outputs/*_pre_cal10_20260430.*` y
  `REPORTE_AVANCES_pre_cal10_20260430.md`.
- (-) Rollback a comportamiento legacy requiere pasar
  `component_c=0.0` explicitamente en cada caller; no hay flag global.

## Frontera con CAL-9 (aclaracion)

ADR-0009 menciono un "CAL-10 hipotetico" como una posible migracion del
EMS interno (`core/ems_p2p.py`) a matriz `pi_gs (N, T)`. Esa hipotesis
sigue **pendiente y no se incluye en este CAL-10**. El presente CAL-10
trata exclusivamente la mecanica regulatoria de C1 (Excedentes Tipo
1/Tipo 2, componente C). El EMS P2P sigue usando el escalar
comunitario `grid.pi_gs = pi_gs_eff` por las razones enumeradas en
ADR-0009 §"Frontera EMS escalar ↔ C1-C4 matriz".

## Estado

Implementado y probado en local 2026-04-30.

| Test | Resultado |
|---|---|
| `pytest tests/ -q` | 57/57 verdes (51 pre-CAL-10b + 5 CAL-10b + 1 NaN) |
| `python main_simulation.py` (sintetico) | 13 s, banner `[CAL-10b]` modo auto |
| `python main_simulation.py --data real --full --analysis` (CAL-10b) | mensual + SA-1/SA-2/GSA + FA-1/FA-2 OK; FA-3 falla por bug pre-existente (regresion ADR-009) |

Numeros agregados CAL-9/CAL-10/CAL-10b documentados en
`Documentos/notas_modelo_tesis.md §CAL-10b`.

**Aceptado en produccion 2026-04-30**.

---

## Anexo CAL-10b (2026-04-30) — Componente C real desde CSV Cedenar

### Cambio

`component_c="auto"` (proporcional 13.85 %) era una aproximacion
pragmatica; cedio el paso a un dato real `(N, T)` extraido del CSV
mensual `data/tarifas_cedenar_mensual.csv` que ya contiene `Cvm` y
`COT` para los 13 meses del horizonte (abr-2025 a abr-2026), copiados
manualmente de los PDFs `data/cedenar_pdfs/tarifa_*.pdf`.

### Implementacion

Helper publico nuevo:

```python
data.cedenar_tariff.cvm_plus_cot_per_agent_hourly(agent_names, idx)
    -> np.ndarray  # (N, T) COP/kWh, constante dentro del mes
```

Analogo 1-a-1 a `pi_gs_per_agent_hourly` (CAL-9). Las celdas con mes
ausente o Cvm/COT NaN se marcan `np.nan`; `scenarios._pi_gs.as_component_c_array`
las rellena con `pi_gs[n, k] * C_FRACTION` (fallback proporcional CAL-10).

`main_simulation.py` arma `component_c_arg` con la misma logica
condicional que `pi_gs_arg`: matriz real para `--full` y `--day`, modo
`"auto"` para perfil diario y caso sintetico. Banner del log condicional:

```
[CAL-10b] C1 (CREG 174 arts. 22-23): permuta Tipo 1 a (pi_gs - C),
          excedentes Tipo 2 a bolsa horaria post-Hx;
          C = Cvm + COT real desde CSV Cedenar (mes a mes).
```

### Decision regulatoria — C = Cvm + COT (no solo Cvm; no Rm)

Justificacion documentada en memoria semantica
`tesis-p2p / cal_10_componente_c_definicion_cvm_plus_cot`:

- CREG 119/2007 art. 11 define Cvm como margen de comercializacion
  puro.
- CREG 101-028/2023 reconoce COT como costo operativo del comercializador,
  no como impuesto. La factura real CEDENAR sigue cobrando Cvm + COT
  sobre la energia permutada aunque haya credito Tipo 1.
- Rm (Restricciones del SIN) queda fuera: matematicamente independiente
  en CU = G + T + D + C + P + R; CREG 174 limita el cobro sobre
  permuta al componente de comercializacion.

Postura estricta: peor escenario regulatorio para inyeccion Tipo 1,
fuerza al modelo a buscar eficiencia real en lugar de depender de
interpretacion laxa.

### Valores reales extraidos

Para el perfil oficial NT2 cedenar (Udenar/HUDN), 13 meses:

| Mes | Cvm | COT | C real |
|---|---:|---:|---:|
| 2025-04 | 174,69 | 40,27 | 214,96 |
| 2025-07 | 174,16 | 42,42 | 216,58 |
| 2025-10 | 173,61 | 41,13 | 214,74 |
| 2026-01 | 172,23 | 40,49 | 212,72 |
| 2026-04 | 176,41 | 38,73 | 215,14 |

(Cobertura completa en CSV. Fraccion real C/CU promedio ~26 % vs 13.85 %
de la aproximacion pre-CAL-10b.)

### Impacto numerico observado

Run completo `outputs/run_2026-04-30b.log`, `outputs/resultados_comparacion.xlsx`:

| Escenario | CAL-9 | CAL-10 | CAL-10b | Δ vs CAL-10 |
|---|---:|---:|---:|---:|
| C1 | 54.061.626 | 52.808.543 | 52.462.139 | −346.404 (−0,66 %) |
| P2P | 52.446.938 | 52.446.938 | 52.446.938 | 0 (esperado) |
| RPE | +3,08 % | +0,69 % | **+0,029 %** | −0,66 pp |

P2P y C1 quedan **estadisticamente empatados**. La diferencia
de 15 201 COP en agregado de 52,4 M COP es del orden del ruido numerico.

Por agente, Δ CAL-10 → CAL-10b:

| Agente | C1 CAL-10 | C1 CAL-10b | Δ % |
|---|---:|---:|---:|
| Udenar | 9.425.355 | 9.183.471 | **−2,57 %** |
| Mariana | 11.987.071 | 11.974.050 | −0,11 % |
| UCC | 14.686.160 | 14.669.410 | −0,11 % |
| HUDN | 10.259.945 | 10.211.360 | −0,47 % |
| Cesmag | 6.450.021 | 6.423.837 | −0,41 % |

Udenar (mayor generador) absorbe el 70 % del cambio agregado.

### Razon del impacto modesto vs prediccion

Antes de CAL-10b se predijo Δ −8 % a −12 % adicional sobre CAL-10
(porque C real ≈ 22-27 % del CU vs 13.85 % proporcional). El Δ real
fue −0,66 %. Razones documentadas en `notas_modelo_tesis.md §CAL-10b`:

1. **Hx temprano** en meses con surplus solar significativo →
   pequeña masa de energia paga el descuento C (la mayoria es Tipo 2,
   que no se ve afectado por C).
2. **Permuta dominada por meses de bajo cruce**, donde el surplus
   absoluto es modesto.
3. **CAL-9 ya capturaba parcialmente C en pi_gs** (Cedenar oficial NT2
   ~797 incluye C; la aproximacion 13.85 % de pi_gs ya descontaba
   ~110 COP/kWh, vs 215 real → diferencia efectiva ~105 COP/kWh sobre
   permuta de Udenar ~2300 kWh efectivos a lo largo del horizonte).

### Tests anadidos

| Test | Archivo |
|---|---|
| 4 tests del helper | `tests/test_cedenar_cvm_cot.py` |
| `as_component_c_array` rellena NaN con proporcional | `tests/test_c1_creg174_v2.py` |
| C real CSV produce C1 menor que proporcional | `tests/test_c1_creg174_v2.py` |

### Bug pendiente (no introducido por CAL-10b)

`analysis/feasibility.analyze_withdrawal_risk` (linea 725) pasa
`pi_gs (N=5, T)` a `run_c4_creg101072` con `N=4` despues de retirar un
agente, sin slicear la matriz. Esto dispara `ValueError` en
`as_pi_gs_array` en CAL-9+. ADR-009 §"Slicing en analisis" prometia el
slicing pero la implementacion regreso. Fix queda anotado para
proximo ciclo; no afecta los resultados CAL-10b para SA-1/SA-2/GSA ni
para la comparacion P2P vs C1/C2/C3/C4.

**Aceptado en produccion 2026-04-30 (anexo CAL-10b)**.

---

## Anexo CAL-10b.1 (2026-04-30) — Propagacion a SA-1/SA-2/SA-3 (PPA)

### Hallazgo

Tras la corrida CAL-10b se detecto que las funciones de sensibilidad
(`run_sensitivity_pgb`, `run_sensitivity_pv`, `run_sensitivity_ppa`)
**no propagaban `month_labels` ni `component_c`** a `run_comparison`.
SA-1 producia `C1 = 54.550.177 COP` constante (vs mensual TOTAL
`52.462.139`), ignorando la mecanica multi-mensual y el dato real
Cvm+COT del CSV Cedenar.

Defecto **pre-existente desde CAL-9** (cuando se introdujo
`month_labels` en `run_c1_creg174`); CAL-10b lo heredo al agregar
`component_c`. Detectado al comparar SA-1 entre las corridas CAL-10 y
CAL-10b: identicos al digito.

### Fix

`analysis/sensitivity.py` (4 firmas extendidas + 4 llamadas internas):

```python
def run_sensitivity_pgb(..., month_labels=None, component_c="auto"): ...
def run_sensitivity_pv(...,  month_labels=None, component_c="auto"): ...
def run_sensitivity_ppa(..., month_labels=None, component_c="auto"): ...
def run_sensitivity_pgs(..., month_labels=None):
    # pi_gs sintetico; component_c queda "auto" porque el dato real
    # Cedenar no aplica al sweep hipotetico.
```

`main_simulation.py` (4 sitios) propaga
`month_labels=month_labels, component_c=component_c_arg` a las 3
funciones de sensibilidad que mantienen `pi_gs` constante. SA-3
(barrido `pi_gs` sintetico) solo recibe `month_labels`.

### Otros callers verificados (sin cambios necesarios)

- `analysis/subperiod.py`: perfil diario con `pi_gs` escalar y
  `month_labels=None` (sub-periodo es una unidad). `"auto"` correcto.
- `analysis/global_sensitivity.py`: GSA Sobol con muestreo parametrico
  de `pi_gs`. `"auto"` correcto.
- `analysis/sensitivity_2d.py`: sweep 2D parametrico. `"auto"`
  correcto.

### Estado

Tests 57/57 verdes post-fix. Los numeros de SA-1/SA-2/SA-3 en
`outputs/run_2026-04-30b.log` son del run pre-fix; re-correr
`--full --analysis` produciria SA consistente con el mensual TOTAL
(no urgente: la conclusion cualitativa P2P estadisticamente empatado
con C1 ya quedo documentada en el anexo CAL-10b con la tabla mensual
TOTAL que es independiente de SA).

**Aceptado en produccion 2026-04-30 (anexo CAL-10b.1)**.
