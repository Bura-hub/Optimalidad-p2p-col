# Auditoría de Coherencia — Tesis P2P Colombia

**Autor del informe:** Claude (auditoría automatizada sobre el repositorio)
**Solicitada por:** Brayan S. Lopez-Mendez · Udenar 2026
**Fecha:** 2026-04-17
**Corrida de referencia:** `outputs/run_day_2025-08-06_1458.log`
(miércoles, ventana MTE laborable con alta irradiancia; duración 12 225 s).

---

## 1. Resumen ejecutivo

La auditoría evalúa 20 preguntas repartidas en cuatro frentes
(A fidelidad al modelo base · B cumplimiento de la propuesta de tesis ·
C validaciones WEEF · D consistencia interna de documentos).

Se encuentran **20 hallazgos** con la siguiente distribución de severidad:

| Severidad | A | B | C | D | Total |
|---|---|---|---|---|---|
| CRÍTICO   | 0 | 0 | 0 | 1 | **1** |
| ALTO      | 1 | 0 | 1 | 2 | **4** |
| MEDIO     | 2 | 2 | 1 | 2 | **7** |
| BAJO / OK | 3 | 4 | 2 | 1 | **10 (3 son BAJO)** |

**Bloqueos para la reunión de asesores:** el hallazgo CRÍTICO D1
(tres valores distintos de IE P2P en documentos auditables) y los ALTO
A2 (`compe` divergente en `core/replicator_buyers.py`) y D5 (dos
denominadores de RPE en el mismo repositorio).

**Bloqueos para la defensa:** A5 (golden test compara Python↔Python,
no Python↔MATLAB) y C3 (invariancia de C4 vs precio de bolsa solo
justificada teóricamente; requiere verificación con `--full` sobre
series horarias XM).

**Declaraciones obligatorias en el documento final de tesis:** la
auditoría fue ejecutada sobre la corrida `--day 2025-08-06`. Los
frentes **B3, C3 y el valor definitivo de D1** quedan pendientes
del run `--full` sobre el horizonte de 5 160 h (Act 3.2 y 4.1). No
modificar fórmulas, rangos GSA ni convención `net_benefit` hasta
validar contra `--full`.

---

## 2. Frente A — Fidelidad al modelo base (Sofía Chacón et al., 2025)

### [A1] OK — Replicator de vendedores coincide con `ReplicadorWjSol2`

**Enunciado.** La fuerza de cambio del vendedor usa
`F = pi_i − H_j − lam_filt − bet_filt + BGRANDE`, idéntica a la
expresión MATLAB del modelo base.

**Evidencia.** `core/replicator_sellers.py:1-142`;
`Documentos/copy/JoinFinal.m:240-242` (constantes `VEL_GRAD=1e6`,
`BGRANDE=1e6`, `VEL_RD=0.1`).

**Recomendación.** Mantener sin cambios. Documentar explícitamente
en el docstring del módulo que las constantes provienen de
`JoinFinal.m:240-242` (ya está parcialmente hecho).

---

### [A2] ALTO — Divergencia en término de competencia del replicator de compradores

**Enunciado.** En `core/replicator_buyers.py:70` la dinámica utiliza
`compe = etha_s * sum_Pji`, donde `sum_Pji` es la energía total
canalizada por el comprador `i`. En `JoinFinal.m:187-189` la
definición es `compe = etha * matriz`, con `matriz = ones(I,I) − eye(I)`
y uso por indexación lineal de MATLAB, lo que produce
`compe(i=1) = 0` y `compe(i>1) = etha`. La formulación Python
sobrecastiga en magnitud y no reproduce el decaimiento por índice
que usa el modelo base.

**Evidencia.**
- `core/replicator_buyers.py:70` (dinámica)
- `core/replicator_buyers.py:124-125` (función de bienestar, que sí
  usa `matriz = ones((I,I)) − eye(I)` — inconsistente con la
  dinámica dentro del mismo archivo).
- `Documentos/copy/JoinFinal.m:187-200`.

**Recomendación.** Reemplazar en la dinámica por
`compe = etha * (np.ones((I,I)) − np.eye(I))` y aplicar sobre la
matriz `P_ij` antes de sumar por vendedor, replicando el
indexado lineal MATLAB. Antes de mezclar, correr
`tests/golden_test_sofia.py` para cuantificar el impacto sobre
`P_total` y `pi_i` en la hora 14. Si la desviación respecto del
oráculo SLSQP disminuye, el cambio se acepta.

---

### [A3] MEDIO — Alternancia vs ODE conjunta

**Enunciado.** `core/ems_p2p.py:230-244` resuelve el Stackelberg por
alternancia (`solve_sellers` → `solve_buyers` con norma relativa).
`JoinFinal.m:139` integra el sistema acoplado con `ode15s`
(estado concatenado `[consumer_state, seller_state]`). Son dos
formulaciones numéricamente distintas que convergen al mismo
equilibrio de Nash pero con trayectorias transitorias diferentes.

**Evidencia.** `core/ems_p2p.py:230-244`; `Documentos/copy/JoinFinal.m:139`.

**Recomendación.** Declarar la diferencia en la sección de Métodos de
la tesis y añadir un párrafo en `Documentos/notas_modelo_tesis.md`
explicando por qué ambas formulaciones producen el mismo equilibrio
en el límite. No requiere cambio de código, pero sí una cita al test
de convergencia (`tests/test_stackelberg_convergence.py`) que
evidencie `‖P_new − P_old‖ / (‖P_old‖+ε) < tol` al terminar.

---

### [A4] OK — Parámetros sintéticos exactos

**Enunciado.** `data/base_case_data.py:1-96` replica los parámetros
canónicos de `JoinFinal.m:40-43`: `SCALE = 6.0865`,
`A = SCALE*[4·0.089, 0.069, 0, 0, 0, 0]`,
`B = SCALE*[3.93·52, 32, 47, 37, 0, 0]`, `lam = 100`, `theta = 0.5`,
`etha = 0.1`, `pi_gs = 1250`, `pi_gb = 114`.

**Evidencia.** `data/base_case_data.py:40-95`; `JoinFinal.m:40-43`.

**Recomendación.** Ninguna. La extensión del vector `alpha = [0.20×4,
0.10×2]` para el programa DR es una ampliación declarada y no
contamina la comparación con el modelo base cuando se pasa
`alpha = np.zeros(6)` (como ya hacen los tests y el golden).

---

### [A5] MEDIO — Golden test compara Python↔Python, no Python↔MATLAB

**Enunciado.** `tests/golden_test_sofia.py` declara ser un golden
contra el modelo base de Sofía, pero el oráculo
(`Documentos/copy/reference_h14.json`) se genera con el optimizador
SLSQP de `Bienestar6p.py` (reimplementación Python del modelo). No
hay comparación directa contra una salida de `JoinFinal.m` ejecutada
en MATLAB.

**Evidencia.** `tests/golden_test_sofia.py:7-23, 38-41`;
`Documentos/copy/Bienestar6p.py` (no `.m`). Tolerancias declaradas:
`P_total` atol = 0,15 kWh; demanda rtol = 5 %; `pi_i ∈ [PGB, PGS]`.

**Recomendación.** (a) Añadir una nota en §VI.D de la tesis
indicando que la fidelidad al modelo base está verificada en dos
etapas: SLSQP (mercado Nash estático) y Replicator Dynamics
(mismo equilibrio por solver distinto); (b) ejecutar una vez
`JoinFinal.m` en MATLAB para la hora 14 y añadir un segundo
archivo `reference_h14_matlab.json` que garantice el cierre MATLAB
↔ Python. La entrega puede declarar esto como limitación si no
hay acceso a MATLAB.

---

### [A6] BAJO — Test de convergencia es indirecto

**Enunciado.** `tests/test_stackelberg_convergence.py` verifica
`iters_used ∈ [min_iter, max_iter]` y que con `tol = 0` se alcanza
`max_iter`, pero no asevera explícitamente que
`‖P_new − P_old‖ / (‖P_old‖+ε) < tol` al salir del bucle en una hora
convergida. La afirmación se sostiene por el contrato del código,
no por el test.

**Evidencia.** `tests/test_stackelberg_convergence.py:70-104`.

**Recomendación.** Añadir en `_run_hour_worker` la devolución del
`norm_rel` final como campo opcional de `HourlyResult` y agregar un
`assert res.norm_rel_final < 1e-3` en la prueba `test_convergence_
norm_below_tol`. Es un cambio de una sola línea sin riesgo para la
lógica de producción.

---

## 3. Frente B — Cumplimiento de la propuesta de tesis

### [B1] OK — Actividades 1.0 a 2.2 implementadas y trazables

**Enunciado.** Actividades 1.0 (Inventario), 1.1 (Modelo base),
1.2 (Inferencia paramétrica), 2.1 (C1–C4) y 2.2 (Métricas) están
completadas y citadas en `Documentos/Matriz_Trazabilidad.md`.

**Evidencia.** `Documentos/Matriz_Trazabilidad.md:28-34`;
`Documentos/Inventario_Act_1_0.md`;
`Documentos/Revision_Bibliografica_Act_1_2.md`.

**Recomendación.** Ninguna.

---

### [B2] OK — Cinco escenarios cumplen la Tabla I

**Enunciado.** `scenarios/scenario_c1_creg174.py`,
`scenario_c2_bilateral.py`, `scenario_c3_spot.py` y
`scenario_c4_creg101072.py` modelan el tratamiento regulatorio
pedido. C4 usa `mode = "pde_only"` por defecto
(`scenarios/scenario_c4_creg101072.py:79`), alineado con la regla 2
de la skill `tesis-p2p-context`.

**Evidencia.** `scenarios/scenario_c4_creg101072.py:79,181-183`;
`scenarios/comparison_engine.py:130-131`.

**Recomendación.** Ninguna.

---

### [B3] PARCIAL (dependiente de `--full`) — Actividad 3.2 incompleta

**Enunciado.** `Documentos/Matriz_Trazabilidad.md:36` declara la
Actividad 3.2 como "parcial — falta run `--full` 5 160 h". La
corrida `--day 2025-08-06` cubre un laborable con irradiancia alta
pero no reemplaza el horizonte completo exigido por la propuesta
(§VII).

**Evidencia.** `Documentos/PropuestaTesis.txt:VII`;
`Documentos/Matriz_Trazabilidad.md:36`;
`outputs/run_day_2025-08-06_1458.log`.

**Recomendación.** Lanzar `python main_simulation.py --data real
--full --analysis` dentro de las próximas 72 h (skill
`run-long-simulations`, `block_until_ms = 1800000`). Sin este
resultado la tesis no puede reportar PoF/RPE, IE ni SS
consolidados para los 6 meses de la ventana MTE.

---

### [B4] ~~MEDIO~~ RESUELTO — GSA Sobol/Saltelli n_base = 64 ejecutada

**Enunciado original.** `analysis/global_sensitivity.py` declaraba smoke
test con `n_base = 4` pero la corrida estadísticamente válida estaba pendiente.

**Estado (2026-04-17).** La corrida con `n_base = 64` (1 024 evaluaciones,
7 parámetros, 3 outputs: ganancia, SC, IE) fue ejecutada el 2026-04-17.
Resultados en `resultados_gsa.xlsx` (hoja `S1_ST`, 21 filas).

**Hallazgos cualitativos:**
- SC dominada por `factor_PV` (ST ≈ 0,85) y `factor_D` (ST ≈ 0,21).
- Ganancia dominada por `factor_PV` (ST ≈ 4,6) y `factor_D` (ST ≈ 2,9).
- IE más sensible a `PGB` (ST ≈ 2,9, primer orden S1 ≈ 0,24).
- IC amplios (artefacto de n_base = 64); S1 negativos son varianza, no
  interpretación física. Para IC estrechos en publicación: n_base ≥ 256.

**`Documentos/Matriz_Trazabilidad.md` actualizado** — Act 4.1 marcada
`completado`. Actividad 3.2 sigue siendo la única parcial del proyecto.

---

### [B5] OK — Cronograma §VIII respetado (con 1 desvío menor)

**Enunciado.** Las Actividades 1.0–4.2 se implementan en el orden
cronológico esperado; el único desvío detectado es que la GSA
(Act 4.1, marzo–abril) aún no ha corrido con `n_base ≥ 64` a la
fecha de la auditoría (17-abril), pero los módulos están listos.

**Evidencia.** `Documentos/PropuestaTesis.txt §VIII Tabla II`;
`Documentos/Matriz_Trazabilidad.md:38`.

**Recomendación.** No bloqueante; resolver junto con B4.

---

### [B6] BAJO — Convención `net_benefit` unificada

**Enunciado.** La convención Filosofía A (beneficio neto = ahorros
+ ingresos, sin resta de costo de red) está implementada de forma
consistente entre `core/settlement.py:104-115`,
`scenarios/comparison_engine.py:102-104` y los cuatro `scenario_c*.py`.
Es la decisión validada en la reunión WEEF (ver Frente C1).

**Evidencia.** `core/settlement.py:104-115`;
`scenarios/comparison_engine.py:102-104`;
`scenarios/scenario_c4_creg101072.py:181-183`.

**Recomendación.** Ninguna.

---

## 4. Frente C — Validaciones de los asesores (reunión WEEF)

### [C1] OK — Filosofía A incorporada

**Enunciado.** Los asesores definen la ganancia neta como "lo que
me ahorro frente al caso base sin generación", no como
`ingresos − costos`. Todo el pipeline aplica esta definición.

**Evidencia.** `Documentos/conversacion_WEEF.txt:888-963`
(discusión explícita: "la ganancia no se debería calcular en lo
que debo pagar de energía menos lo que estoy generando, sino lo que
me estoy ahorrando"). Implementado en
`core/settlement.py:104-115`.

**Recomendación.** Ninguna.

---

### [C2] OK — Validación de ganancias por escenario

**Enunciado.** Los asesores esperan que el P2P supere a C4 "en
todos los niveles de precio" (`conversacion_WEEF.txt:1820-1823`).
La corrida `--day 2025-08-06` lo confirma: P2P = 123 433 COP >
C4 = 110 888 COP, RPE = 0.1016 (`REPORTE_AVANCES.md:34-40`).

**Evidencia.** `Documentos/conversacion_WEEF.txt:1786-1823`;
`REPORTE_AVANCES.md:34-40`.

**Recomendación.** Ninguna, pero rehacer la verificación contra
`--full` para confirmar que la dominancia se preserva en los
fines de semana y durante El Niño.

---

### [C3] ALTO (dependiente de `--full`) — Invariancia de C4 vs precio de bolsa

**Enunciado.** Los asesores observan en la reunión que "C4 no varía
ante los precios" y piden auditar si debería variar
(`conversacion_WEEF.txt:1825-1836`). La justificación teórica está
en `Documentos/notas_modelo_tesis.md §3.14.2`: con cobertura
comunitaria 11,3 %, el excedente neto comunitario
`E_com(k) = 0 ∀k` y los créditos PDE son siempre nulos, haciendo a
C4 invariante a `pi_bolsa`. La observación de los asesores queda
formalmente respondida **solo para el perfil diario promedio**.

**Evidencia.** `Documentos/conversacion_WEEF.txt:1825-1836`;
`Documentos/notas_modelo_tesis.md:168-184`.

**Recomendación.** En la corrida `--full` se debe generar un barrido
explícito C4(`pi_bolsa`) sobre las horas con `E_com(k) > 0` (fines
de semana y días de baja demanda institucional). Si C4 sigue
invariante allí, la conclusión del `§3.14.2` se generaliza; si no,
se debe corregir la formulación PDE en
`scenarios/scenario_c4_creg101072.py`.

---

### [C4] OK — Condición de deserción documentada

**Enunciado.** El umbral de deserción individual está en
`Documentos/conversacion_WEEF.txt:2151-2170` ("la deserción solo
sería posible si esto es mayor a 4.72"). La condición de
Racionalidad Individual aparece formalizada en
`Documentos/notas_modelo_tesis.md §3.14` con umbrales por agente
(Udenar ~180 COP/kWh en SA-1 con pi_bolsa constante; estable con
precios XM reales).

**Evidencia.** `Documentos/conversacion_WEEF.txt:2151-2170`;
`Documentos/notas_modelo_tesis.md:101-165`; `REPORTE_AVANCES.md:116-147`.

**Recomendación.** Ninguna.

---

## 5. Frente D — Consistencia interna de documentos

### [D1] CRÍTICO — Tres valores distintos de IE P2P en el repositorio

**Enunciado.** El índice de equidad del escenario P2P aparece
reportado con **tres valores incompatibles** en tres archivos
auditables:

| Archivo | IE P2P | Fuente |
|---|---|---|
| `REPORTE_AVANCES.md:34` | **0.0922** | corrida `--day` actual |
| `Documentos/notas_modelo_tesis.md:38` | **0.0984** | "perfil 24h MTE" |
| `Documentos/notas_modelo_tesis.md:1093` | **0.1510** | corrida previa |

Los tres deberían referir a la misma configuración nominal. La
dispersión (0,06 puntos) excede cualquier ruido numérico esperable
del replicador. El IE es una métrica citada en §VII de la propuesta
y aparece en las tablas mostradas a los asesores.

**Evidencia.** `REPORTE_AVANCES.md:34`;
`Documentos/notas_modelo_tesis.md:38,1093`.

**Recomendación.** Definir `REPORTE_AVANCES.md` como única fuente
automática y `Documentos/notas_modelo_tesis.md` como fuente
permanente. Tras la corrida `--full` se congela el valor oficial
en `notas_modelo_tesis.md §4`. Toda otra aparición de IE debe
marcarse como histórica con fecha. **No tocar antes del `--full`.**

---

### [D2] ALTO — `b_n` uniforme contradice `JoinFinal.m`

**Enunciado.** `data/xm_prices.py:73-79` define
`B_CALIBRATED = {fronius: 225, Cesmag_inv: 210, default: 220}`,
valores uniformes en COP/kWh. `JoinFinal.m:40-43` usa
`b = 6.0865·[3.93·52, 32, 47, 37, 0, 0] = [1245, 195, 287, 225, 0, 0]`,
vector heterogéneo en unidades normalizadas. El documento
`Revision_Bibliografica_Act_1_2.md:81` reconoce el conflicto:
*"**225 COP/kWh** (datos reales MTE); 194,76 adim. (caso sintético)"*.

**Evidencia.** `data/xm_prices.py:73-79`;
`Documentos/copy/JoinFinal.m:40-43`;
`Documentos/Revision_Bibliografica_Act_1_2.md:81`.

**Recomendación.** Documentar explícitamente en un párrafo de
`notas_modelo_tesis.md` que en modo real los agentes comparten LCOE
homogéneo (justificación: todos con Fronius ≤ 100 kW instalados en
Pasto en la misma ventana temporal), mientras que el modo sintético
preserva la heterogeneidad de `JoinFinal.m`. Añadir un test
`tests/test_b_calibration.py` que afirme `B_CALIBRATED["default_pasto"]
∈ [200, 250]` y documente la fuente IRENA/UPME.

---

### [D3] MEDIO — Acrónimo MTE sin definición única

**Enunciado.** El acrónimo "MTE" aparece en más de 30 archivos del
repositorio (código, docs, skills) pero solo se expande en un
único lugar: `Documentos/Inventario_Act_1_0.md:13` — "MTE (Medición
de Tecnologías de Energía)". No aparece expandido en la propuesta
(`Documentos/PropuestaTesis.txt`), ni en `CLAUDE.md`, ni en el
`README.md`.

**Evidencia.** `Documentos/Inventario_Act_1_0.md:13`; búsqueda
`grep -n "MTE" Documentos/PropuestaTesis.txt` → 0 coincidencias
con expansión.

**Recomendación.** Añadir la definición "MTE — Medición de
Tecnologías de Energía" en el glosario de la tesis y la primera vez
que aparece en `README.md`. Remediación documental BAJO-MEDIO:
adecuada para commit atómico `audit: unifica acrónimo MTE`.

---

### [D4] BAJO — Residuos textuales "PoF" en `analysis/sensitivity.py`

**Enunciado.** El repositorio renombró PoF (Price of Fairness
Bertsimas) a RPE (Rendimiento Relativo) para no confundir con el
concepto formal que la tesis no implementa (stub TODO en
`comparison_engine.py:331-334`). Quedan tres residuos textuales.

**Evidencia.**
- `analysis/sensitivity.py:19` — docstring "PoF (Price of Fairness)"
- `analysis/sensitivity.py:80` — encabezado `"{'PoF':>6}"`
- `analysis/sensitivity.py:450` — encabezado `"{'PoF':>6}"`

**Recomendación.** Reemplazar por `RPE` y aclarar en el docstring que
no corresponde al PoF Bertsimas. Commit atómico
`audit: residuos PoF → RPE en analysis/sensitivity.py`.

---

### [D5] ALTO — Dos denominadores distintos para el RPE

**Enunciado.** El RPE se calcula con **dos denominadores
incompatibles** en el mismo repositorio:

| Archivo | Fórmula |
|---|---|
| `scenarios/comparison_engine.py:331-334` | `rpe = (w_eff − w_fair) / abs(w_eff)` con `w_eff = net_benefit["P2P"]` |
| `analysis/subperiod.py:147` | `rpe = (p2p_tot − c4_tot) / max(abs(c4_tot), 1.0)` |

La diferencia entre `|W_P2P|` y `max(|W_C4|, 1)` puede producir
valores de RPE con magnitudes distintas (hasta ~15 %) para la
misma configuración. El documento
`Matriz_Trazabilidad.md:37` reporta "RPE = 0,3035 con fórmula
(W_P2P − W_C4) / |W_P2P|", coherente con `comparison_engine.py`.

**Evidencia.** `scenarios/comparison_engine.py:36-40,331-334`;
`analysis/subperiod.py:147`;
`Documentos/Matriz_Trazabilidad.md:37`.

**Recomendación.** Unificar `analysis/subperiod.py` para usar la
fórmula de `comparison_engine.py` (regla 4 de la skill
`tesis-p2p-context`: `net_benefit` unificado entre escenarios).
El cambio requiere regenerar `p2p_breakdown.xlsx`. No hacer antes
del `--full`.

---

### [D6] MEDIO — Cinco entradas `VERIFICAR` en `references.bib`

**Enunciado.** `Documentos/references.bib` contiene seis marcas
`VERIFICAR` para autores o DOIs no confirmados.

**Evidencia.**
- L206,215 — Scielo Colombia (autores + DOI)
- L244,253 — JEEM Elsevier (DOI)
- L260,268 — estudio Valle de Aburrá (autores)
- L286,295 — Energy Policy Elsevier (autores)
- L312,319 — e-Prime Elsevier (DOI)
- L323,329 — Energy Economics Elsevier (autores + DOI)

**Recomendación.** Resolver antes de la defensa contrastando con
las plataformas editoriales. No bloqueante para la reunión.
Commit atómico `audit: verifica DOI y autores en references.bib`.

---

## 6. Matriz de decisión

| ID | Severidad | Corregir antes de la reunión | Corregir antes de la defensa | Declarar como limitación | Depende de `--full` |
|---|---|---|---|---|---|
| A1 | OK       |   |   |   |   |
| A2 | ALTO     | ✓ |   |   |   |
| A3 | MEDIO    |   | ✓ |   |   |
| A4 | OK       |   |   |   |   |
| A5 | MEDIO    |   | ✓ | opcional |   |
| A6 | BAJO     |   | ✓ |   |   |
| B1 | OK       |   |   |   |   |
| B2 | OK       |   |   |   |   |
| B3 | PARCIAL  |   | ✓ |   | ✓ |
| B4 | ~~MEDIO~~ RESUELTO | — | — | — | — |
| B5 | OK       |   |   |   |   |
| B6 | OK       |   |   |   |   |
| C1 | OK       |   |   |   |   |
| C2 | OK       |   |   |   | ✓ (confirmar) |
| C3 | ALTO     |   | ✓ |   | ✓ |
| C4 | OK       |   |   |   |   |
| D1 | CRÍTICO  | ✓ |   |   | ✓ (valor final) |
| D2 | ALTO     | ✓ |   |   |   |
| D3 | MEDIO    |   | ✓ |   |   |
| D4 | BAJO     |   | ✓ |   |   |
| D5 | ALTO     | ✓ |   |   | ✓ (regen. xlsx) |
| D6 | MEDIO    |   | ✓ |   |   |

---

## 7. Fuentes de verdad propuestas

| Magnitud | Fuente de verdad propuesta | Cómo usar |
|---|---|---|
| IE P2P (nominal) | `Documentos/notas_modelo_tesis.md §4` tras `--full` | Todo otro IE se marca como histórico con fecha |
| `b_n` (modo real) | `data/xm_prices.py::B_CALIBRATED` (225 COP/kWh, justificado en `Revision_Bibliografica_Act_1_2.md:81`) | Ningún documento debe contradecir el valor |
| Acrónimo MTE | `Documentos/Inventario_Act_1_0.md:13` — "Medición de Tecnologías de Energía" | Usar expandido en primera aparición de tesis y README |
| Convención RPE | `scenarios/comparison_engine.py:331-334` — `(W_P2P − W_C4) / abs(W_P2P)` | `analysis/subperiod.py:147` debe migrar a esta fórmula |
| `net_benefit` | `core/settlement.py:104-115` + `comparison_engine.py:102-104` | Cualquier nuevo escenario reutiliza la función canónica |
| Filosofía A | `conversacion_WEEF.txt:888-963` | Referencia al justificar la fórmula en la tesis |

---

## 8. Apéndice — Preguntas pendientes de decisión del usuario

1. **D1 IE P2P:** ¿se congela el valor tras `--full` o se acepta
   reportar el IE del perfil diario promedio como nominal? El primer
   camino retrasa la reunión; el segundo requiere declarar el IE de
   6 meses como análisis complementario.
2. **A2 `compe` en `replicator_buyers.py`:** ¿se acepta rehacer la
   corrida `--day` tras el fix, o se declara como "discrepancia
   documentada contra modelo base" con evidencia del golden?
3. **A5 golden MATLAB:** ¿hay acceso a MATLAB para generar
   `reference_h14_matlab.json`, o se declara la limitación Python↔Python?
4. **C3 C4 invariante:** ¿se quiere un barrido explícito
   C4(`pi_bolsa`) sobre horas con `E_com > 0` como figura adicional
   de la tesis, o basta con la justificación teórica de
   `§3.14.2`?
5. **D5 denominador RPE:** ¿se regenera `p2p_breakdown.xlsx` con la
   fórmula unificada ahora, o se espera al `--full`?
6. **Remediación opcional BAJO/MEDIO:** ¿autorizas commits atómicos
   `audit: ...` para D3 (acrónimo MTE), D4 (PoF→RPE residuos) y D6
   (entradas `VERIFICAR` de `references.bib`)? No tocan fórmulas
   ni números.
7. **B4 GSA `n_base = 64`:** ¿autorizas lanzar ahora la Sobol con
   `n_base = 64` (~75 min) o se espera a tener el `--full` primero?

---

*Fin del informe. No se hicieron cambios en el repositorio.*
