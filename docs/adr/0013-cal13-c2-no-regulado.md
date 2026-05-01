# 0013 — CAL-13: Comunidad MTE como usuario no-regulado agregado en C2

- **Estado:** Accepted
- **Fecha de decisión:** 2026-05-01
- **Actividad:** 3.1–3.3 (validación regulatoria) / 4.2 (escritura del manuscrito)
- **Archivos afectados:** `data/cedenar_tariff.py`
  (helper `g_plus_commercialization_per_agent_hourly`),
  `scenarios/scenario_c2_bilateral.py` (docstring CAL-13),
  `scenarios/comparison_engine.py` (docstring CAL-13),
  `main_simulation.py` (wiring G+Cvm+COT y banner),
  `tests/test_c2_bilateral.py` (5 tests CAL-13 nuevos),
  `Documentos/notas_modelo_tesis.md` §3.8 (sección CAL-13)
- **Relacionado con:** [ADR-0011 CAL-11](0011-cal11-c2-ppa-bilateral-modelo-formal.md),
  [ADR-0012 CAL-12](0012-cal12-c2-fom-peajes.md);
  spec previo
  `docs/superpowers/specs/2026-05-01-c1-c2-regulatory-alignment-audit.md`
- **Memoria semántica:** `tesis-p2p / cal_13_c2_no_regulado_agregado`
- **Fuente normativa:** **Ley 143/1994 art. 41** (mercado mayorista,
  contratos bilaterales); **CREG 086/1996 art. 1** mod. CREG 039/2001
  (precio libre para usuarios no-regulados); **CREG 174/2021 art. 23
  num. 1.a** (AGPE FNCER puede vender a precio libre si la energía se
  destina a usuarios no-regulados); **Decreto 388/2007** (umbrales de
  no-regulado: 55 MWh/mes o 100 kW de potencia conectada); **CREG
  119/2007** arts. 6-14 (descomposición CU, residuo tarifario)
- **Fuente bibliográfica:** spec
  `2026-05-01-c1-c2-regulatory-alignment-audit.md`; instrucción del
  asesor 2026-05-01

## Contexto

CAL-12 corrigió el alcance del precio en C2: el ahorro del comprador
se calcula sobre el componente G del CU, no sobre el CU completo. Sin
embargo, **C2 seguía siendo contrafáctico** porque CAL-12 modela un
PPA bilateral entre AGPE residencial y consumidor residencial regulado,
contrato que **no existe legalmente** bajo el marco colombiano vigente:

- Ley 143/1994 art. 41 limita los contratos bilaterales del MEM a
  generadores ↔ comercializadores ↔ usuarios no-regulados.
- CREG 086/1996 art. 1 mod. 039/2001 establece que el precio libre vía
  contrato bilateral solo aplica a usuarios no-regulados.
- CREG 174/2021 art. 23 num. 1.a confirma para AGPE: precio
  libremente pactado solo si la energía se destina a usuarios
  no-regulados.

Auditoría regulatoria 2026-05-01 (spec
`docs/superpowers/specs/2026-05-01-c1-c2-regulatory-alignment-audit.md`)
propuso tres caminos para alinear C2 con la ley:

- **Opción A**: comunidad MTE como usuario no-regulado agregado.
- **Opción B**: cada AGPE con un comercializador externo.
- **Opción C**: fusionar C2 en C4 (Comunidad Energética CREG 102 072).

Decisión del usuario 2026-05-01 (Camino 2 = Opción A): mantener la
simetría intra-comunidad de la propuesta de tesis original (líneas
106-107, 227-247 de `Documentos/PropuestaTesis.txt`) declarando que
las 5 instituciones MTE (Udenar, HUDN, Mariana, UCC, Cesmag) se
constituyen como persona jurídica común (asociación, cooperativa o
comunidad energética) que cumple los umbrales del Decreto 388/2007 y
califica como **usuario no-regulado agregado**. Esa entidad firma
contratos bilaterales a precio libre con los AGPE FNCER miembros
bajo CREG 086/1996 y CREG 174/2021 art. 23 num. 1.a.

## Decisión

### 1. Naturaleza legal de C2 bajo CAL-13

C2 modela un **PPA bilateral comunitario legalmente válido** entre
prosumidores AGPE FNCER ≤ 100 kW y la comunidad MTE constituida como
**usuario no-regulado agregado**. La habilitación legal completa es:

| Norma | Mandato | Cumplimiento bajo CAL-13 |
|---|---|---|
| **Ley 143/1994 art. 41** | Contratos bilaterales del MEM entre generadores ↔ comercializadores ↔ usuarios no-regulados | ✅ comunidad MTE = usuario no-regulado agregado |
| **CREG 086/1996 art. 1** mod. 039/2001 | Precio libre solo para no-regulados | ✅ comunidad MTE no-regulada |
| **CREG 174/2021 art. 23 num. 1.a** | AGPE puede vender a precio libre si destino = no-regulado | ✅ destino = comunidad MTE no-regulada |
| **Decreto 388/2007** | No-regulado: ≥ 55 MWh/mes o ≥ 100 kW de potencia conectada | ⚠️ **supuesto del modelo**: agregada (universidades + hospital) plausiblemente cumple; verificable empíricamente con admin MTE |

### 2. Alcance del precio (corrección sobre CAL-12)

Bajo CAL-12 (comprador regulado), el ahorro era `E_PPA × (G − π_ppa)`.
Bajo CAL-13 (comprador no-regulado), el ahorro se amplía a:

```
savings_cons = E_PPA × ((G + Cvm + COT) − π_ppa)            [CAL-13]
```

**Justificación**: el usuario no-regulado **NO tiene comercializador
minorista**. Contrata directamente con el generador a través de un
representante del MEM. Por tanto, además del ahorro sobre G (componente
negociable), el comprador se **ahorra Cvm + COT** (margen del
comercializador minorista, irrelevante en el régimen no-regulado).
Sigue pagando T+D+PR+Rm al OR/STN (cargos regulados trasladables).

### 3. Helper nuevo `g_plus_commercialization_per_agent_hourly`

`data/cedenar_tariff.g_plus_commercialization_per_agent_hourly(agents, idx)`
devuelve matriz (N, T) con `G + Cvm + COT` por (agente, hora),
constante dentro del mes. Análoga 1-a-1 a `g_component_per_agent_hourly`
(CAL-12), `cvm_per_agent_hourly` (CAL-10b.2) y `pi_gs_per_agent_hourly`
(CAL-9). Lee las columnas `Gm`, `Cvm`, `COT` del CSV
`data/tarifas_cedenar_mensual.csv`, transcritas de los PDFs CEDENAR.

Ejemplo abr-2026 oficial NT2 (Udenar/HUDN):

| Componente | COP/kWh |
|---|---:|
| G | 310,96 |
| Cvm | 176,41 |
| COT | 38,73 |
| **G + Cvm + COT** | **526,10** |
| T+D+PR+Rm | 273,06 |
| CU completo | 799,16 |

### 4. Default `pi_ppa` actualizado

```
pi_ppa_default = pi_gb + 0.5 · ((G + Cvm + COT)_promedio − pi_gb)
```

Para abr-2026 oficial NT2 con `pi_gb = 195`: `pi_ppa_default ≈ 360`
COP/kWh (vs ≈ 255 bajo CAL-12, vs ≈ 553 bajo legacy CAL-9).

### 5. Wiring en producción

`main_simulation.py` arma `pi_G_arg` con la siguiente lógica
condicional (paralela a `pi_gs_arg`):

| Modo | Origen de `pi_G_arg` |
|---|---|
| `--data real --full` | `g_plus_commercialization_per_agent_hourly(agents, index_full)` |
| `--data real --day` | `g_plus_commercialization_per_agent_hourly(agents, idx_day)` |
| `--data real` (perfil diario) | `mean(pi_G_full, axis=1)` (vector N) |
| sintético | `mean(pi_bolsa) × 1.5` (proxy escalar) |

Banner de log:

```
[CAL-13] C2 (Ley 143/1994 art. 41 + CREG 086/1996 + CREG 174/2021
art. 23.1.a): comunidad MTE como usuario no-regulado agregado;
savings_cons sobre (G+Cvm+COT); rango negociable = matriz (N, T)
mes a mes desde Cedenar PDFs.
```

### 6. Tests

5 tests CAL-13 nuevos en `tests/test_c2_bilateral.py`:

- `test_g_plus_commercialization_helper_smoke`: verifica que el
  helper devuelve ≈ 526 COP/kWh para abr-2026 oficial NT2.
- `test_helper_g_plus_strictly_greater_than_g_alone`: G+Cvm+COT > G
  en cada celda; diferencia ≈ 215 COP/kWh.
- `test_savings_cons_es_mayor_bajo_no_regulado_que_regulado`: el
  ahorro CAL-13 > ahorro CAL-12 para el mismo `pi_ppa`. Verificación
  cuantitativa: `Δ = E_PPA × (PI_NEGOTIABLE − PI_G_REG)`.
- `test_invarianza_bienestar_FoM_no_regulado_se_preserva`: teorema
  §3.8 sigue valiendo bajo CAL-13.
- `test_default_pi_ppa_CAL13_punto_medio_pi_gb_y_negotiable`: el
  default CAL-13 es punto medio entre `pi_gb` y `(G+Cvm+COT)`, y es
  estrictamente mayor que el default CAL-12.

Tests CAL-11/CAL-12 preservados (16 tests pasaban antes; siguen
pasando con el cambio de wiring del default).

### 7. Brechas que se mantienen out-of-scope

| Brecha | Decisión | Razón |
|---|---|---|
| Constitución legal formal de la persona jurídica MTE | Supuesto del modelo | Verificable con admin MTE; no afecta numéricamente al simulador |
| Modalidad Take-or-Pay vs Pay-as-Produced | Conserva PaP | T-o-P queda como CAL-14a/b futuro (ADR-0011 anexo CAL-11b) |
| Indexación π_ppa(t) | No modelada | Horizonte 7 meses; IPC ≈ 2 % (despreciable) |
| Variante CFD/financiera | Cerrada | C2 modela físico (PPA tipo UPME CLPE = CFD; estructuras opuestas) |
| Plazo contractual | No modelado | 7 meses fijo |
| Comisión del representante MEM | Asumida = 0 | Simplificación: el "comercializador especializado" ↔ entidad comunitaria |

## Alternativas consideradas

### A. Mantener CAL-12 con declaración contrafáctica explícita

Mantener el modelo regulado puro (savings sobre G solo) y declarar en
el manuscrito que C2 es contrafáctico (no existe contrato legal entre
AGPE residencial y consumidor residencial). **Rechazada por el
usuario 2026-05-01**: prefiere alinear C2 con un escenario legalmente
viable bajo el marco vigente.

### B. PPA AGPE individual con comercializador externo

Cada AGPE firma su propio PPA con un comercializador especializado
que destina la energía a usuarios no-regulados externos. Legal bajo
CREG 174/2021 art. 23 num. 1.a. **Rechazada (Camino 1 del usuario)**:
rompe la simetría P2P-vs-C2 que la propuesta de tesis exige
(`Documentos/PropuestaTesis.txt` líneas 236-247: "conjunto común de
elementos del sistema: agentes, generadores, consumidores").

### C. Fusionar C2 en C4 (CREG 102 072/2025)

Eliminar C2 como escenario distinto; C4 ya modela autogeneración
colectiva. **Rechazada**: pierde la cota "PPA fijo" como referencia
estática, debilita el espacio de comparación.

### D. Híbrido: implementar A y B como variantes paralelas

Reportar ambas cotas en el manuscrito. **Rechazada (Camino 3 del
usuario)**: alcance excesivo para el plan de tesis vigente.

## Consecuencias

- (+) **C2 alineado con la ley colombiana**: ahora representa un
  contrato bilateral legalmente posible (AGPE FNCER ↔ comunidad MTE
  no-regulada bajo Ley 143/1994 + CREG 086/1996 + CREG 174/2021
  art. 23.1.a).
- (+) **Conserva la simetría P2P-vs-C2** que exige el alcance
  metodológico de la propuesta de tesis: P2P y C2 operan sobre el
  mismo conjunto común (prosumidores + consumidores intra-comunidad).
- (+) **El factor `f` empírico colombiano negativo** (CAL-11) cobra
  más coherencia: bajo el régimen no-regulado el rango es 526
  COP/kWh, intermedio entre G (311) y CU completo (799), lo que
  reduce la magnitud del `f` empírico negativo de los PPAs UPME.
- (+) **Tests blindan el cambio**: 21 tests verdes en
  `tests/test_c2_bilateral.py` (16 CAL-11/12 + 5 CAL-13). Suite
  global 79/79 verdes (vs 74 antes), sin regresión.
- (+) **Helper `g_plus_commercialization_per_agent_hourly`** queda
  disponible para análisis futuros que requieran este rango.
- (−) **KPIs de C2 cambian respecto a CAL-12**: estimación previa
  +50 % a +100 % en `total_net_benefit` de C2 cuando se corre
  `--full` (cota intermedia entre BTM legacy y FoM regulado puro).
  Re-corrida `--full --analysis` (~52 min) **PENDIENTE**.
- (−) **Supuesto verificable**: la constitución de la persona jurídica
  MTE como usuario no-regulado agregado debe declararse en el
  manuscrito como supuesto del modelo y, idealmente, validarse con
  admin MTE.
- (−) **`run_sensitivity_ppa` (SA-3) sigue usando rango `[π_gb, π_gs]`**:
  TODO post-CAL-13 actualizar a `[π_gb, G+Cvm+COT]`. No urgente.

## Estado

Accepted en producción 2026-05-01.

| Componente | Archivo | Estado |
|---|---|---|
| Helper G+Cvm+COT | `data/cedenar_tariff.g_plus_commercialization_per_agent_hourly` | Implementado |
| Refactor docstring C2 | `scenarios/scenario_c2_bilateral.py` | Actualizado con CAL-13 |
| Wiring main_simulation | `main_simulation.py` | Actualizado, banner CAL-13 visible |
| Refactor docstring engine | `scenarios/comparison_engine.py` | Actualizado |
| Tests CAL-13 | `tests/test_c2_bilateral.py` | 5 nuevos + 16 preservados, 21/21 verdes |
| Suite global | `tests/` | 79/79 verdes (1:52 min) |
| Smoke sintético | `python main_simulation.py` | OK (15 s, banner CAL-13) |
| ADR-0013 | Este documento | Escrito |
| Notas §3.8 | `Documentos/notas_modelo_tesis.md` | Pendiente |
| Memoria persistente | `MEMORY.md` + `project_cal13_c2_no_regulado.md` | Pendiente |
| Indexación AgentDB | `python scripts/seed_ruflo_adr.py` | Pendiente cierre |
| Re-corrida `--full --analysis` | `outputs/` y `graficas/` | **Pendiente — usuario decide** |
