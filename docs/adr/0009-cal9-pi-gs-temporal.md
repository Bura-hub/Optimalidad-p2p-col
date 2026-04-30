# 0009 — CAL-9: Tarifa pi_gs temporal mes a mes (matriz N×T)

- **Estado:** Accepted
- **Fecha de decision:** 2026-04-30
- **Actividad:** 1.1 (caracterizacion empirica) / 3.1-3.3 (validacion regulatoria)
- **Archivos afectados:** `scenarios/_pi_gs.py`,
  `scenarios/scenario_c{1,2,3,4}_*.py`, `scenarios/comparison_engine.py`,
  `analysis/feasibility.py`, `analysis/monthly_report.py`,
  `main_simulation.py`, `tests/test_pi_gs_temporal.py`
- **Supersedes parcialmente:** la Fase 2 de
  [ADR-0008 CAL-8](0008-cal8-pi-gs-cedenar.md) (contrato `pi_gs : (N,)`)
- **Fuente:** `Documentos/notas_modelo_tesis.md` §CAL-9

## Contexto

CAL-8 introdujo la calibracion Cedenar mensual diferenciada por
institucion, pero los escenarios C1-C4 consumian `pi_gs` como vector
escalar `(N,)`: cada agente liquidaba todo el horizonte con el
**promedio horario-ponderado** del CU mensual del CSV
`data/tarifas_cedenar_mensual.csv` (~792 oficial NT2, ~950 comercial
NT2 sobre `2025-07 → 2026-02`).

Ese colapso introduce sesgos regulatorios:

- La Res. CREG 174/2021 liquida creditos y excedentes con resolucion
  **mensual**: cada mes calendario tiene su propio CU.
- La Res. CREG 101 072/2025 distribuye PDE tambien **mensualmente**.

El CU oficial NT2 del CSV varia entre 766,80 y 816,98 COP/kWh
(spread ~6,5 % intraanual). Liquidar `--full` con un escalar borra
esa variabilidad y debilita la fidelidad regulatoria del comparativo
P2P vs C1/C4 ante los asesores.

La funcion `data.cedenar_tariff.pi_gs_per_agent_hourly(agents, idx)`
(introducida en CAL-8 como API publica) ya devuelve la matriz
`(N, T)` constante dentro del mes, pero ningun consumidor la usaba.

## Decision

1. **Promover `pi_gs` al contrato canonico `(N, T)`** en escenarios C1-C4
   y modulos de analisis (`comparison_engine`, `monthly_report`,
   `feasibility.analyze_withdrawal_risk`, `_compute_daily_series`).

2. **Helper extendido** `scenarios._pi_gs.as_pi_gs_array(pi_gs, N, T)`:

   - `float`            → `np.full((N, T), v)`
   - `(N,)`            → broadcast a `(N, T)`
   - `(T,)`            → broadcast a `(N, T)`
   - `(N, T)`          → as-is con validacion

   Mantiene `as_pi_gs_vector(pi_gs, N)` como fallback retro-compatible:
   acepta matriz y la colapsa al promedio temporal por agente.

3. **Wiring en `main_simulation.py`** segun el modo:

   - `--data real --full`: `pi_gs_arg = pi_gs_per_agent_hourly(names, index_full)`
   - `--data real --day YYYY-MM-DD`: `pi_gs_per_agent_hourly(names, idx_day)`
   - `--data real` (perfil diario promedio 24h): vector `(N,)` CAL-8
     porque ese modo representa el promedio del horizonte
   - sintetico: escalar `grid_params["pi_gs"]`

4. **Indexacion temporal en escenarios**:

   - C1 (CREG 174): `pi_gs_period = pi_gs_v[n, hours].mean()`
     dentro del bucle de periodos. Compatible con
     `month_labels = year×100 + month` ya existente.
   - C2 (PPA), C3 (spot), C4 (AGRC): `pi_gs_v[n, k]` dentro del bucle
     horario para autoconsumo, creditos PDE, deficit residual.

5. **Slicing en analisis**:

   - `monthly_report` slicea la matriz al mes: `pi_gs_m = pi_gs_v[:, idx_arr]`.
   - `analyze_withdrawal_risk` slicea por agentes restantes:
     `pi_gs_r = pi_gs[mask, :]`.
   - `_compute_daily_series` slicea al dia: `pi_gs_d = pi_gs_full[:, sl]`.

6. **`_p2p_monetary_benefit` y `_p2p_flow_breakdown` indexan por
   POSICION** en la lista de resultados (`enumerate`), no por `r.k`.
   Esto permite reusar la funcion sobre slices arbitrarios siempre que
   el caller alinee `(results, D)` por construccion.

## Justificacion

El refactor es de baja friccion (~15 lineas en 2 archivos core), no
introduce dependencias nuevas y preserva backward compatibility:
todo callsite que pase escalar o vector `(N,)` sigue funcionando via
broadcast en `as_pi_gs_array`.

La fidelidad mes a mes se exige porque el modelo regulatorio CREG
liquida mensualmente, y porque CAL-8 ya carga el dato fino del CSV;
no usar la variabilidad disponible es decision arbitraria.

## Impacto observado

Validacion sobre horizonte completo MTE (`--full --analysis`,
2026-04-30, 61,4 min, 6144 h, log
`outputs/run_cal9_20260430_1656.log`, comparado contra
`outputs/pre_cal9_resultados.xlsx`):

### Beneficio neto agregado por escenario

| Escenario | CAL-8 (COP) | CAL-9 (COP) | Δ COP | Δ % |
|---|---:|---:|---:|---:|
| C1   | 54.042.168 | 54.061.626 | +19.458 | **+0,036 %** |
| C2   | 51.440.813 | 51.437.446 | −3.367  | −0,007 % |
| C3   | 50.961.703 | 50.958.336 | −3.367  | −0,007 % |
| C4   | 50.290.134 | 50.288.076 | −2.059  | −0,004 % |
| P2P  | 52.430.924 | 52.446.938 | +16.014 | **+0,031 %** |

### Beneficio neto P2P por agente

| Agente | CAL-8 (COP) | CAL-9 (COP) | Δ COP | Δ % |
|---|---:|---:|---:|---:|
| Udenar  | 8.136.217  | 8.117.765  | −18.453 | **−0,227 %** |
| Mariana | 12.188.801 | 12.198.377 | +9.576  | +0,079 % |
| UCC     | 15.208.492 | 15.219.747 | +11.255 | +0,074 % |
| HUDN    | 10.255.874 | 10.263.249 | +7.375  | +0,072 % |
| Cesmag  | 6.641.540  | 6.647.801  | +6.261  | +0,094 % |

### Lectura

- En **agregado** la calibracion CAL-8 escalar era una buena
  aproximacion al promedio del horizonte (delta < 0,04 %): mover de
  promedio horario-ponderado a matriz mes a mes preserva el orden
  de magnitud del bienestar comunitario.
- La **redistribucion intra-comunidad** si es relevante: Udenar
  (mayor generador, oficial NT2 cuyo CU baja en dic-ene) pierde
  beneficio P2P relativo, mientras los compradores comerciales
  (Mariana / UCC / Cesmag, CU oficial * 1,20) y HUDN ganan
  proporcionalmente. Mismo patron en C2/C3/C4: Udenar −0,21 a
  −0,24 %, los demas +0,03 a +0,06 %.
- C1 (CREG 174) es el escenario con la **ganancia agregada mas
  positiva** post-CAL-9 (+0,036 %), consistente con el balance
  mensual de creditos: cada mes liquida con su CU real, y los meses
  con CU bajo (dic-2025: 773.52, ene-2026: 766.80) generan menos
  permutacion penalizada.
- La estructura cualitativa de IR/IE/Gini se mantiene casi identica
  (IE C4 cambia +0,0004; Gini sin cambios significativos), por lo
  que las conclusiones pre-CAL-9 sobre desercion (3/5 estables) y
  RPE P2P-vs-C4 siguen validas.

Reporte detallado: `outputs/cal9_delta_report.md`.

## Consecuencias

- (+) Liquidacion regulatoriamente fiel: cada hora hereda el CU del
  mes que la contiene, alineado con CREG 174 / CREG 101 072.
- (+) Cobertura tarifaria 13/13 meses sigue al 100 %; el CSV no
  cambia.
- (+) Tests CAL-9 (`tests/test_pi_gs_temporal.py`, 10 casos) cubren:
  shapes del helper, equivalencia escalar↔matriz constante, delta
  esperado mes a mes para C1 y C4.
- (-) `as_pi_gs_vector` queda en uso solo como adaptador para callers
  que aun esperan vector (`p2p_breakdown.export_p2p_hourly`); estos
  reciben el promedio temporal sin perder semantica.
- (Pendiente) Documentar el delta numerico cuantitativo en
  `Documentos/notas_modelo_tesis.md §CAL-9` una vez termine la corrida
  `--full --analysis`.

## Frontera EMS escalar ↔ C1-C4 matriz (decision de diseno)

El motor P2P interno (`core/ems_p2p.py`, replicator dynamics,
`compute_savings`, `residual_settlement`, `IE` horario) **conserva el
escalar** `grid.pi_gs = pi_gs_eff` (~906 COP/kWh, comunitario ponderado
por demanda). La matriz `(N, T)` solo entra al comparativo regulatorio
(C1-C4, `monthly_report`, `_p2p_monetary_benefit`,
`analyze_withdrawal_risk`).

**Razones (detalladas en notas_modelo_tesis.md §CAL-9.5):**

1. **Mecanismo P2P uniforme**: el solver resuelve un unico `pi_star[k]`
   por hora; pasar a matriz introduciria discriminacion implicita por
   categoria tarifaria (HUDN bidearia hasta 797, comerciales hasta 956),
   convirtiendo el P2P en un PPA segmentado — algo distinto a la
   propuesta de tesis.
2. **Fidelidad al modelo base** (Chacon et al. 2025): el juego se define
   con `pi_gs` escalar adimensional. La tesis valida ese modelo, no lo
   reemplaza.
3. **Outside option comunitario**: `pi_gs_eff` representa "lo que paga
   la comunidad como agregado si no hay P2P", referencia conceptual
   correcta para una negociacion uniforme.
4. **La heterogeneidad se sintetiza despues**: una vez resuelto
   `pi_star[k]`, `_p2p_monetary_benefit` valoriza `received * pi_gs[i,
   k_local] - paid` con la matriz, capturando el flujo de caja real
   per-agente. No hay perdida de fidelidad regulatoria.

**Implicaciones para el reporte**:

- `IE` horario (`HourlyResult.IE`, calculado en `ems_p2p.py:294`):
  Nivel 2 (bienestar del mercado, u.o.), usa escalar — correcto.
- `Gini`, `RPE`, `net_benefit` por agente, `flow_breakdown`
  (calculados en `comparison_engine`): Nivel 1 (cash, COP), usan
  matriz — correcto.

**Migracion a matriz en EMS (CAL-10 hipotetico)** solo se justificaria
si la propuesta cambiara para modelar un P2P segmentado por categoria
tarifaria. Hoy esa hipotesis no esta en la propuesta.

## Estado

Implementado, probado y validado en local 2026-04-30.

| Test | Resultado |
|---|---|
| `pytest tests/ -q` | 43/43 verdes (33 baseline + 10 CAL-9) |
| `python main_simulation.py` (sintetico) | 13 s |
| `python main_simulation.py --data real` (perfil diario) | 22 s |
| `python main_simulation.py --data real --full --analysis` | **61,4 min**, sin errores |
| `scripts/cal9_delta_report.py` | delta agregado < 0,04 % en todos los escenarios |

**Aceptado en produccion 2026-04-30**.
