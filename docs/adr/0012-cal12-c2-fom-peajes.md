# 0012 — CAL-12: Corrección Front-of-Meter del PPA en C2 (peajes T+D+C+PR+R)

- **Estado:** Accepted
- **Fecha de decisión:** 2026-05-01
- **Actividad:** 3.1–3.3 (validación regulatoria) / 4.2 (escritura del manuscrito)
- **Archivos afectados:** `scenarios/scenario_c2_bilateral.py`,
  `scenarios/comparison_engine.py`, `main_simulation.py`,
  `data/cedenar_tariff.py` (helper nuevo `g_component_per_agent_hourly`),
  `tests/test_c2_bilateral.py` (7 tests nuevos),
  `Documentos/notas_modelo_tesis.md` §3.8 (ampliación)
- **Relacionado con:** [ADR-0008 CAL-8](0008-cal8-pi-gs-cedenar.md),
  [ADR-0009 CAL-9](0009-cal9-pi-gs-temporal.md),
  [ADR-0010 CAL-10](0010-cal10-creg174-tipo-1-2-componente-c.md),
  [ADR-0011 CAL-11](0011-cal11-c2-ppa-bilateral-modelo-formal.md)
- **Memoria semántica:** `tesis-p2p / cal_12_c2_fom_peajes`
- **Fuente normativa:** Resolución CREG 119/2007 arts. 6-14
  (componentes G, T, D, C, PR, R del CU)
- **Fuente bibliográfica:** Norton Rose Fulbright (PPAs Colombia 2019),
  XM/ASIC manuales de liquidación, instrucción asesor 2026-05-01

## Contexto

CAL-11 (2026-04-30) formalizó C2 como PPA físico Pay-as-Produced y
documentó el sustento empírico del factor `f`. Sin embargo, **dejó
intocada la lógica del módulo**: el ahorro del consumidor seguía
calculándose como `ppa_kWh × (pi_gs − pi_ppa)`, asumiendo
implícitamente que `pi_ppa` reemplaza el **CU completo**.

Auditoría regulatoria 2026-05-01 (instrucción asesor + WebFetch
directo a `gestornormativo.creg.gov.co`):

> *"La Resolución CREG 119/2007 no contempla exenciones en peajes T+D
> para usuarios regulados con contratos bilaterales. Los artículos
> 9-10 establecen que estos son costos trasladables obligatorios al
> usuario regulado, independientemente de su origen energético
> contratado."*

Las búsquedas confirman cuatro dimensiones regulatorias del PPA
colombiano:

1. **Alcance**: el PPA solo cubre el componente **G** (Generación) del
   CU. Los peajes T+D+Cvm+PR+Rm+COT siguen siendo facturados por el
   OR/STN/comercializador al usuario regulado, sin importar la
   existencia del contrato (CREG 119/2007 arts. 6-14).
2. **Modalidad**: Take-or-Pay vs Pay-as-Produced; ASIC registra ambas
   (Norton Rose Fulbright 2019).
3. **Indexación**: anual por IPP/IPC en contratos largo plazo
   (irrelevante para horizonte 7 meses MTE).
4. **Liquidación horaria**: ASIC/XM evalúa contrato vs consumo real
   contra frontera comercial; déficit se cubre a precio spot
   (no-regulados) o al CU regulado (regulados).

**Hallazgo crítico**: el modelo C2 pre-CAL-12 sobrestima el ahorro del
comprador en `(CU − G) × E_PPA` por kWh recibido vía PPA. Para
abril-2026 oficial NT2 (`CU = 799,16`, `G = 310,96`) la diferencia es
**488,20 COP/kWh** sobre cada kWh PPA. Esto inflaba `total_net_benefit`
de C2 en ~75 % respecto al valor regulatoriamente correcto.

## Decisión

### 1. Separar G de los peajes en el modelo C2

El ahorro del comprador vía PPA se calcula sobre el componente G,
no sobre el CU completo:

```
savings_cons = E_PPA × (G − pi_ppa)            [CAL-12]
```

El comprador sigue pagando T+D+Cvm+PR+Rm+COT al OR/STN sobre toda
la energía recibida (incluida la PPA), pero **eso no se contabiliza
en savings_cons** por la filosofía A (`net_benefit = savings + revenues`,
sin costos de la red). El efecto neto es que el ahorro PPA se reduce
al spread (G − pi_ppa), que típicamente es **mucho menor** que (CU − pi_ppa).

### 2. Helper `g_component_per_agent_hourly`

Nuevo en `data/cedenar_tariff.py`, análogo a `pi_gs_per_agent_hourly`
(CAL-9) y `cvm_per_agent_hourly` (CAL-10b.2). Lee la columna `Gm` del
CSV `data/tarifas_cedenar_mensual.csv`, transcrita manualmente desde
los PDFs `data/cedenar_pdfs/tarifa_*.pdf` (CEDENAR mensuales).

Ejemplo abr-2026 oficial NT2: `G = 310,96 COP/kWh`. Las 130 filas del
CSV están completamente pobladas para los 13 meses del horizonte.

### 3. Refactor `run_c2_bilateral`

Nueva firma:

```python
def run_c2_bilateral(
    D, G_pv, pi_gs, pi_gb, pi_ppa,
    prosumer_ids, consumer_ids,
    pi_G=None,                                # CAL-12
) -> dict:
    pi_gs_v = as_pi_gs_array(pi_gs, N, T)
    pi_G_v  = pi_gs_v if pi_G is None else as_pi_gs_array(pi_G, N, T)
    ...
    savings_cons[i] += ppa_delivered[idx] * (pi_G_v[i, k] - pi_ppa)  # CAL-12
```

Cuando `pi_G is None` se reproduce el comportamiento BTM legacy
(pre-CAL-12), preservando la suite CAL-11 al 100 %. En producción
(`main_simulation.py --data real`) se pasa la matriz real.

### 4. Default de `pi_ppa` actualizado

Antes (pre-CAL-12):
```
pi_ppa_default = pi_gb + 0.5 × (pi_gs − pi_gb)        # rango [pi_gb, CU]
```

Después (CAL-12):
```
pi_ppa_default = pi_gb + 0.5 × (G_promedio − pi_gb)   # rango [pi_gb, G]
```

El factor `f = 0,5` se preserva como postulado simétrico de reparto
(ADR-0011 sigue vigente), pero ahora aplica al **rango natural
regulatorio** (donde el comprador todavía obtiene ahorro: π_ppa < G).

### 5. Propagación en `comparison_engine.run_comparison`

Nuevo parámetro `pi_G` propagado a `run_c2_bilateral`. Default en
`main_simulation.py`:

| Modo | Origen de `pi_G_arg` |
|---|---|
| `--data real --full` | `g_component_per_agent_hourly(agents, index_full)` |
| `--data real --day` | `g_component_per_agent_hourly(agents, idx_day)` |
| `--data real` (perfil diario) | `mean(pi_G_full, axis=1)` (vector N) |
| sintético | `mean(pi_bolsa)` (escalar — proxy del componente G) |

Banner de log nuevo:
```
[CAL-12] C2 (CREG 119/2007 arts. 6-8): savings_cons sobre G (no CU);
         G = matriz (N=5, T=6144) mes a mes desde Cedenar PDFs.
```

### 6. Brechas que se mantienen out-of-scope

ADR-0011 declaró las siguientes como cerradas; CAL-12 confirma:

- Variante CFD/financiera
- Perfil Baseload
- Plazo contractual con renegociación
- Precios PPA diferenciados por agente

Adicionalmente CAL-12 NO modela:

- **Liquidación spot del déficit Take-or-Pay**: el déficit residual
  sigue yendo al CU regulado (que es lo correcto para usuario
  regulado bajo Pay-as-Produced; sería distinto bajo T-o-P
  no-regulado).
- **Costos T+D+C+PR+R explícitos en el net_benefit**: por filosofía A,
  estos costos no se restan; simplemente el savings_cons se reduce al
  spread (G − π_ppa). El efecto numérico es idéntico a restar
  (CU − G) × E_PPA del savings legacy.

## Alternativas consideradas

### A. Documentación BTM sin cambio de código (rechazada)

Justificar el modelo legacy como BTM puro: la energía P2P fluye en
una microred local privada que no toca el SDL. **Rechazada por
incongruencia física**: las 5 instituciones MTE están geográficamente
dispersas en Pasto, conectadas individualmente al SDL de CEDENAR. No
hay microred privada, no hay BTM puro.

### B. Variante paralela `scenario_c2b_bilateral_fom.py` (rechazada)

Mantener el C2 actual (BTM hipotético) y agregar variante FoM como
escenario alternativo. **Rechazada por sobrecarga conceptual**: la
tesis ya tiene 5 escenarios (P2P, C1, C2, C3, C4); añadir un 6.º
diluye el mensaje. Mejor corregir C2 *in situ* con el modelo
regulatoriamente correcto.

### C. Tratar peajes como costo explícito en filosofía B

Cambiar a filosofía B: `net_benefit = savings + revenues − grid_cost`.
**Rechazada**: rompe la consistencia con C1, C3, C4 y P2P, que usan
filosofía A bajo CAL-9/CAL-10b.2. La equivalencia matemática
(savings sobre G es equivalente a savings sobre CU menos peajes
sobre E_PPA) hace el cambio innecesario.

## Consecuencias

- (+) **Modelo regulatoriamente correcto**: C2 ahora respeta CREG
  119/2007 sobre el alcance del PPA (solo G negociable).
- (+) **El factor `f` empírico colombiano negativo deja de ser
  anomalía** (CAL-11 §5.4): se convierte en consecuencia natural del
  hecho de que solo G se negocia. La tabla de PPAs reales colombianos
  cobra coherencia.
- (+) **Tests blindan el cambio**: 7 tests CAL-12 nuevos, 9 CAL-11
  preservados (legacy via `pi_G=None`). Suite total 74 tests verdes
  (vs 66 antes), sin regresión.
- (+) **Helper `g_component_per_agent_hourly`** queda disponible para
  otros análisis futuros (p.ej. estudios de elasticidad de PPA).
- (+) **Conclusión P2P-vs-C2 se refuerza**: los KPIs de C2 caen, P2P
  no cambia (P2P opera detrás del medidor en la dinámica Stackelberg
  + RD, sin necesidad de declarar BTM porque no usa peajes
  regulatorios en la liquidación).
- (−) **Los KPIs de C2 cambian** drásticamente: estimación previa
  -50 % a -75 % en `total_net_benefit` cuando se corre `--full`. Las
  figuras `fig5/fig6/fig13` y el Excel de salida cambiarán. **Es
  necesario re-correr `main_simulation.py --data real --full --analysis`**
  (~52 min) para regenerar todo.
- (−) **Los números reportados en `REPORTE_AVANCES.md` y manuscrito
  cap. 4** quedan obsoletos para C2; se debe actualizar tras la
  re-corrida.
- (−) **`run_sensitivity_ppa` (SA-3) sigue usando rango `[pi_gb, pi_gs]`
  como cota superior**. Para coherencia CAL-12 debería actualizarse
  a `[pi_gb, G]`. Queda anotado como TODO post-CAL-12 (no urgente:
  el barrido sigue siendo informativo, solo cambia la interpretación
  del `f` en cada punto).

## Estado

Accepted en producción 2026-05-01.

| Componente | Archivo | Estado |
|---|---|---|
| Helper componente G | `data/cedenar_tariff.g_component_per_agent_hourly` | Implementado |
| Refactor C2 | `scenarios/scenario_c2_bilateral.run_c2_bilateral` | Implementado (firma extendida con `pi_G`) |
| Propagación motor | `scenarios/comparison_engine.run_comparison` | Implementado |
| Wiring main | `main_simulation.py` | Implementado (modo real y sintético) |
| Tests CAL-12 | `tests/test_c2_bilateral.py` | 7 nuevos + 9 CAL-11 preservados, 16/16 verdes |
| Suite global | `tests/` | 74/74 verdes (4 min) |
| Smoke sintético | `python main_simulation.py` | OK (24 s) |
| ADR-0012 | Este documento | Escrito |
| Notas §3.8 ampliada | `Documentos/notas_modelo_tesis.md` | Pendiente |
| Memoria persistente | `MEMORY.md` + `project_cal12_c2_fom.md` | Pendiente |
| Indexación AgentDB | `python scripts/seed_ruflo_adr.py` | Pendiente cierre |
| Re-corrida `--full --analysis` | `outputs/` y `graficas/` | **Pendiente — usuario decide cuándo** |
