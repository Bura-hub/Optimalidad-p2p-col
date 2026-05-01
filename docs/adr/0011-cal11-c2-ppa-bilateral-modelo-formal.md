# 0011 — CAL-11: Formalización del modelo C2 (Contrato Bilateral PPA)

- **Estado:** Accepted
- **Fecha de decisión:** 2026-04-30
- **Actividad:** 3.1–3.3 (validación regulatoria y comparación con
  alternativas) / 4.2 (escritura del manuscrito)
- **Archivos afectados:** `scenarios/scenario_c2_bilateral.py`,
  `analysis/sensitivity.py` (run_sensitivity_ppa — reporte Gini),
  `tests/test_c2_bilateral.py` (nuevo),
  `Documentos/notas_modelo_tesis.md` §3.8,
  `docs/superpowers/specs/2026-04-30-c2-ppa-bilateral-audit.md`,
  `scripts/audit_xm_yearly_means.py`
- **Relacionado con:** [ADR-0006 CAL-6](0006-cal6-bn-lcoe-solar.md)
  (calibración LCOE), [ADR-0008 CAL-8](0008-cal8-pi-gs-cedenar.md)
  (tarifa CEDENAR mensual), [ADR-0009 CAL-9](0009-cal9-pi-gs-temporal.md)
  (matriz `pi_gs (N, T)`), [ADR-0010 CAL-10](0010-cal10-creg174-tipo-1-2-componente-c.md)
  (CREG 174 Tipo 1/2 + componente C)
- **Memoria semántica:** `tesis-p2p / cal_11_c2_ppa_bilateral_audit`
- **Fuente normativa:** Resolución CREG 174/2021,
  Resolución CREG 101 072/2025 (Comunidades Energéticas), subastas
  UPME CLPE-02-2019, CLPE-03-2021, subasta solar 2024
- **Fuente bibliográfica:** ver spec asociado §9 (referencias 1-17)

## Contexto

CAL-9 y CAL-10 formalizaron rigurosamente los escenarios C1 (CREG 174)
y la tarifa minorista `pi_gs (N, T)` con datos reales CEDENAR. El
escenario C2 (Contrato Bilateral PPA) **quedaba sin formalización
equivalente**:

1. El docstring del módulo `scenarios/scenario_c2_bilateral.py` no citaba
   ningún marco regulatorio ni paper.
2. El precio del contrato `pi_ppa` se calcula en
   `main_simulation.py:269` como `pi_gb + 0,5·(pi_gs − pi_gb)`. El
   factor `f = 0,5` no tenía sustento empírico documentado.
3. No existían tests unitarios para C2 (sí para C1, C4).
4. No estaba declarado el alcance del modelo (físico vs financiero,
   Pay-as-Produced vs Baseload, plazo).

Auditoría 2026-04-30 (spec
`docs/superpowers/specs/2026-04-30-c2-ppa-bilateral-audit.md`):

- C2 se modela como **PPA físico Pay-as-Produced** con **precio fijo
  constante** en todo el horizonte y para todos los agentes
  (`pi_ppa: float`). Sin variante CFD, sin perfil Baseload, sin plazo.
- `pi_gs` proviene del CSV CEDENAR mensual (sustento real, ADR-008/009);
  `pi_gb` proviene de `pydataxm` o sintético calibrado contra promedios
  XM reales (sustento real); `pi_ppa` es la única variable de C2 sin
  sustento empírico.
- Datos reales descargados con `pydataxm` para 2019, 2021, 2023, 2024
  (spec §5.3): media de bolsa anual osciló entre 139,33 (2021) y 682,48
  (2024) COP/kWh. PPAs reales adjudicados (UPME 2019/2021/2024,
  bilaterales mayoristas 2023/2024): rango 75–321 COP/kWh.
- Cálculo de `f` empírico (spec §5.4) para los siete casos colombianos
  documentados: rango `[−3,08, +0,029]`, ningún caso cerca de
  `f = +0,5`.

## Decisión

### 1. Naturaleza del modelo C2

C2 modela un **PPA bilateral comunitario hipotético** entre las cinco
instituciones MTE en Pasto. Las características operativas se fijan así:

| Atributo | Valor decidido |
|---|---|
| Tipo | Físico (entrega real) |
| Perfil de volumen | Pay-as-Produced (toda la generación PV residual se ofrece) |
| Reparto entre consumidores | Proporcional a la demanda instantánea |
| Plazo | Implícito = horizonte completo (sin renegociación) |
| Precio | `pi_ppa` escalar fijo, parametrizado como `pi_gb + f·(pi_gs − pi_gb)` |
| Default `f` | `0,5` (postulado normativo de reparto simétrico) |
| Liquidación con red | Déficit residual a `pi_gs[n, k]` (sin descuento componente C; C2 no es CREG 174); excedente no vendido a `pi_gb` |

### 2. Justificación del `f = 0,5`

El factor `f = 0,5` no es una observación empírica; los PPAs
colombianos reales muestran `f ∈ [−3,08, +0,029]` (spec §5.4). Se
adopta como **postulado normativo de reparto simétrico** en el contexto
comunitario sin intermediario:

- C2 no representa un PPA mayorista ni un AGPE bajo CREG 174 (que
  obliga a vender excedentes a precio de bolsa horario).
- C2 representa un acuerdo hipotético "vecino-a-vecino" donde el
  spread `pi_gs − pi_gb` queda **íntegro dentro de la comunidad** y
  el factor `f` parametriza cómo se reparte ese spread entre
  generador (mayor `f` → más al generador) y consumidor (menor `f`
  → más al consumidor).
- `f = 0,5` divide simétricamente: el generador captura la mitad
  del spread vía precio mayor que `pi_gb`; el consumidor captura la
  otra mitad vía precio menor que `pi_gs`.

### 3. Teorema de invarianza del bienestar agregado

`Documentos/notas_modelo_tesis.md` §3.8 demuestra que en comunidad
cerrada (excedente vendido = energía recibida):

```
Σ_n B_n^{C2}(pi_ppa) = constante respecto a pi_ppa
```

Por tanto el factor `f` afecta la **distribución** del beneficio entre
prosumidores y consumidores, pero no la **eficiencia agregada** de C2.
La comparación P2P-vs-C2 a nivel agregado es **robusta a la elección
de `f`**.

### 4. Reporte obligatorio del coeficiente de Gini

Como el bienestar agregado es invariante en `f`, la **única dimensión
informativa** del barrido SA-3 (`f ∈ {0,25, 0,50, 0,75}`) es la
distribución intra-comunidad. Se exige:

- En toda presentación de C2 se reporta `Gini_C2(f)` para
  `f ∈ {0,25, 0,50, 0,75}` además del `net_benefit_total`.
- `analysis/sensitivity.run_sensitivity_ppa` se extiende para incluir
  el cálculo de Gini por valor de `f` y exportarlo en el resumen
  Excel `outputs/resultados_comparacion.xlsx` y en la figura
  `graficas/fig10_sensibilidad_ppa.png`.
- Un test unitario (`tests/test_c2_bilateral.py::test_invarianza_bienestar_agregado`)
  verifica que `Σ B_n^{C2}` es constante en `f` hasta tolerancia
  numérica `1e-6` relativa.
- Un segundo test
  (`tests/test_c2_bilateral.py::test_gini_no_invariante`)
  verifica que `Gini_C2(0,25) ≠ Gini_C2(0,50) ≠ Gini_C2(0,75)`
  para una mini-comunidad sintética (3 prosumidores + 3 consumidores
  con perfiles asimétricos).

### 5. Citas obligatorias en el código

- `scenarios/scenario_c2_bilateral.py` (docstring del módulo):
  añadir 3 líneas con cita "Ver ADR-0011 (CAL-11) y
  `docs/superpowers/specs/2026-04-30-c2-ppa-bilateral-audit.md`.
  Sustento empírico: subastas UPME CLPE 02-2019, CLPE 03-2021, 2024;
  contratos bilaterales mayoristas XM 2023-2024."
- `Documentos/notas_modelo_tesis.md` §3.8: añadir párrafo final
  citando la tabla 5.4 del spec y declarando que `f = 0,5` es un
  postulado normativo, no un valor empírico.

### 6. Reporte en el manuscrito

En el capítulo 4 (§C2) se debe incluir:

- Declaración explícita de la naturaleza contrafáctica de C2
  ("PPA bilateral comunitario hipotético, no un mecanismo legal
  disponible para AGPE residenciales bajo CREG 174").
- Tabla resumida del spec §5.4 (PPAs colombianos reales y `f` empírico).
- Resultado SA-3 con Gini (sensibilidad redistributiva).

## Brechas declaradas como cerradas (out-of-scope)

Las siguientes dimensiones **no se implementan** en el alcance de la
tesis y se documentan como decisiones explícitas:

| Brecha | Decisión | Razón |
|---|---|---|
| Variante CFD/financiera | **Cerrada (out-of-scope)** | C2 representa un PPA físico comunitario; un CFD requeriría modelar liquidación contra bolsa hora a hora y compensación financiera, lo que desplaza el foco regulatorio del trabajo y duplica análisis con C3 (mercado spot) |
| Perfil Baseload | **Cerrada (out-of-scope)** | La comunidad MTE es solar-pura; no hay generación firme 24/7 para suscribir Baseload |
| Plazo contractual | **Cerrada (out-of-scope)** | El horizonte del proyecto MTE es 7 meses; modelar plazos de 5–20 años requiere proyectar inflación, degradación PV y cláusulas de renegociación, ajenas al objetivo de comparar mecanismos |
| Precios diferenciados por agente (`pi_ppa[n, k]`) | **Cerrada (out-of-scope)** | El ejercicio comunitario es simétrico por construcción; diferenciar por agente abriría una discusión de equidad bilateral que no agrega evidencia para la tesis |
| Cláusula de incumplimiento (off-take) | **Cerrada (out-of-scope)** | C2 es un modelo de bienestar puro, no un contrato legal completo |
| Calibración con PPAs colombianos reales | **No se calibra** | El `f` empírico colombiano es estructuralmente distinto (mayorista con intermediario) al modelado (comunitario sin intermediario); usar `f` empírico mayorista en C2 introduciría sesgo de contexto |

## Alternativas consideradas

### A. Cambiar el default `f` por uno empírico (`f ≈ 0,03` por UPME 2021)

Reemplazar `f = 0,5` por `f = 0` (o `f` cercano a 0) basándose en el
caso UPME 2021 donde `P_PPA ≈ P_bolsa`. **Rechazada**: este valor solo
aplica al contexto mayorista colombiano con bolsa baja; no traslada
información útil al ejercicio comunitario, además de borrar el sentido
del PPA (si `f = 0` el generador queda indiferente entre PPA y red).
La propiedad "punto medio" preserva el rol del contrato como vehículo
de reparto del spread `pi_gs − pi_gb`.

### B. Hacer `f` parámetro de entrada sin default

Eliminar el default y exigir que el usuario lo especifique. **Rechazada**:
añade fricción operativa sin valor analítico; el teorema de invarianza
asegura que el agregado no depende del valor.

### C. Implementar variante CFD (PPA financiero)

Crear `scenario_c2b_bilateral_cfd.py` con liquidación contra bolsa
horaria. **Rechazada para esta tesis**: la conclusión P2P-vs-C2 a
nivel agregado no cambiaría (teorema de invarianza se generaliza al
caso CFD bajo precio promedio igual al caso físico) y la complejidad
adicional no aporta a la pregunta de investigación.

### D. Documentar simplificación en manuscrito sin cambios

Mantener la formulación actual sin docstrings, sin tests, sin spec.
**Rechazada por el usuario** (decisión 2026-04-30): el sustento del
factor `f` es la pregunta más cuestionable que pueden formular los
asesores y debe quedar formalmente documentada en ADR + spec + tests.

## Consecuencias

- (+) C2 queda **plenamente documentado** con sustento empírico
  (subastas UPME 2019/2021/2024 y contratos bilaterales mayoristas
  XM 2023/2024) y sustento normativo (postulado de reparto simétrico
  comunitario).
- (+) Tests unitarios (`tests/test_c2_bilateral.py`, ver ADR-0011
  Fase D del spec) blindan: balance de energía, invarianza del
  agregado, no-invarianza del Gini, rango `[pi_gb, pi_gs]`,
  compatibilidad `pi_gs (N, T)`.
- (+) `run_sensitivity_ppa` reporta Gini para `f ∈ {0,25, 0,50, 0,75}`,
  haciendo explícita la sensibilidad redistributiva.
- (+) Brechas declaradas (CFD, Baseload, plazo, precios por agente)
  quedan cerradas formalmente; cualquier extensión futura abriría un
  CAL nuevo.
- (+) Script `scripts/audit_xm_yearly_means.py` queda como herramienta
  reproducible para volver a descargar promedios anuales de bolsa
  desde la API XM.
- (−) El número agregado de C2 **no cambia** respecto a CAL-9/CAL-10b
  (la lógica del módulo no se toca, solo el docstring). Cualquier
  re-corrida produce los mismos KPIs.
- (−) La asimetría con C1 (que sí cita CREG 174) y C4 (que cita CREG
  101 072) se mitiga pero no se elimina: C2 sigue siendo un escenario
  contrafáctico sin amparo regulatorio directo, y eso debe quedar
  declarado en el manuscrito.

## Estado

Accepted en producción 2026-04-30. Implementación incremental:

| Componente | Archivo | Estado |
|---|---|---|
| Spec auditoría | `docs/superpowers/specs/2026-04-30-c2-ppa-bilateral-audit.md` | Escrito 2026-04-30 |
| ADR-0011 | `docs/adr/0011-cal11-c2-ppa-bilateral-modelo-formal.md` | Este documento |
| Script descarga XM | `scripts/audit_xm_yearly_means.py` | Implementado y ejecutado 2026-04-30 |
| Datos crudos XM 2019/2021/2023/2024 | `data/precios_bolsa_xm_audit_<año>.csv` | Cacheados |
| Resumen anual XM | `data/audit_xm_yearly_summary.csv` | Generado |
| Tests unitarios C2 | `tests/test_c2_bilateral.py` | 9 tests verdes 2026-04-30 |
| Reporte Gini en SA-3 | `analysis/sensitivity.py` | Pendiente — TODO post-CAL-11 |
| Citas en docstring | `scenarios/scenario_c2_bilateral.py` | Aplicadas 2026-04-30 |
| Párrafo §3.8 notas | `Documentos/notas_modelo_tesis.md` | Aplicado 2026-04-30 |
| Indexación AgentDB | `python scripts/seed_ruflo_adr.py` | Sembrado 2026-04-30 |

---

## Anexo CAL-11b (2026-05-01) — Justificación detallada de Take-or-Pay como out-of-scope

Pregunta del asesor (2026-05-01): *"¿Por qué no implementar la
modalidad Take-or-Pay?"*

La declaración pre-CAL-11 ("Baseload no modelado: la comunidad MTE es
solar pura, no hay generación firme 24/7") era **incompleta**. T-o-P
no es exactamente Baseload — son dimensiones ortogonales:

- **Pay-as-Produced vs Take-or-Pay**: define **quién asume el riesgo
  de volumen**.
- **Baseload vs solar/PaP**: define **el perfil temporal del bloque
  energético**.

T-o-P solar (sin Baseload) es perfectamente concebible: el generador
se compromete a entregar `Q_block(k)` kWh por hora `k` (típicamente
modulado por curva PV esperada) y, si la planta no produce, **compra
el déficit a `pi_bolsa[k]`** y lo entrega al cliente al precio
pactado `pi_ppa`.

### Razones (ordenadas) para mantener T-o-P out-of-scope en este trabajo

1. **Incongruencia con el recurso de la comunidad MTE.** Las 5
   instituciones son 100 % solares **sin almacenamiento ni respaldo**.
   En horas nocturnas, T-o-P obligaría al generador comunitario a
   comprar el bloque completo a spot y revenderlo a `pi_ppa`, lo que
   convierte el PPA solar en un **PPA back-to-back**: la comunidad
   no aporta valor energético, solo financiero. El resultado
   esperado (sin sorpresa) es que T-o-P comunitario solar puro es
   **financieramente inviable**: el generador siempre pierde dinero
   en horas nocturnas si `pi_ppa < pi_bolsa[k]`, condición que el
   spread regulatorio típicamente cumple.

2. **Choque con la estructura del modelo base (Sofía Chacón 2025).**
   El equilibrio Stackelberg + Replicator Dynamics se resuelve hora
   a hora con generación PV limitada `G_klim` fija. T-o-P agrega un
   compromiso intertemporal (bloque firme) que no encaja en la
   dinámica marginal del juego. Modelar T-o-P riguroso requiere un
   nivel adicional de optimización: elegir el bloque comprometido
   `Q_block` minimizando expectativa del costo total bajo
   restricción de producción esperada y aversión al riesgo.

3. **El asesor (WEEF, ~44:55) pidió sensibilidad a `pi_ppa` (factor
   `f`), no a estructuras contractuales alternativas.** Toda la
   conversación WEEF se centró en SA-3 y el reparto del excedente
   entre prosumidor y consumidor.

4. **Scope-creep de la tesis aprobada.** La propuesta tiene 4
   escenarios regulatorios (C1-C4); agregar T-o-P como variante
   sería un 5.º escenario o convertir C2 en una familia paramétrica,
   ambas opciones desbordan el plan.

### Razones para sí implementarlo (consideradas y descartadas)

- (a) **Completitud académica**: la definición canónica del PPA
  incluye ambas modalidades. Un revisor riguroso podría exigirlo.
  → Mitigado documentando explícitamente en este anexo y en el
  manuscrito (cap. 4 §C2) que C2 modela exclusivamente PaP, citando
  CAL-11.
- (b) **Cuantificación del riesgo de volumen**: comparar PaP vs T-o-P
  mostraría cuánto vale para el comprador transferir el riesgo al
  generador. → Resultado esperado bajo MTE solar puro: T-o-P es
  inviable; el ejercicio aporta poco al objetivo de tesis (validar
  P2P frente a alternativas regulatorias).
- (c) **Plumbing trivial**: el precio `pi_bolsa[k]` ya pasa al motor;
  ~80 líneas adicionales bastarían. → Cierto, pero la complejidad
  conceptual (modelar el riesgo, justificar `Q_block`, defender ante
  asesores) es mayor que la complejidad de código.

### Decisión

**T-o-P queda out-of-scope** para esta tesis. Si el asesor o un
revisor lo exige, se abre un **CAL-13 dedicado** con dos sub-opciones
ya pre-diseñadas:

- **CAL-13a "T-o-P realista"**: el generador comunitario, cuando el
  sol no produce, compra el déficit a `pi_bolsa[k]` y lo entrega al
  cliente a `pi_ppa`. Reporta cuánto pierde el generador en horas
  nocturnas → muestra que T-o-P comunitario solar puro es
  **financieramente inviable** (resultado de tesis nuevo).
- **CAL-13b "T-o-P sintético con bloque ajustable"**: parametriza
  `Q_block` como fracción de `mean(G_pv)`. Para `Q_block ≪ G_pv` el
  T-o-P se acerca a PaP; para `Q_block > G_pv` el generador pierde
  dinero. Resultado: curva continua de viabilidad.

Ambas son ejercicios de ~2-3 horas + ADR + tests; ninguna es bloqueante
para la entrega de tesis bajo el plan actual.

**Aceptado en producción 2026-05-01 (anexo CAL-11b)**.
