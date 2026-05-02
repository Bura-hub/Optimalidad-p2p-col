# 0016 — CAL-16: Descomposicion regulatoria del ahorro en C2

- **Estado:** Accepted
- **Fecha de decision:** 2026-05-02
- **Actividad:** 3.1-3.3 (validacion regulatoria) / 4.2 (escritura del manuscrito)
- **Archivos afectados:** `data/cedenar_tariff.py`
  (helpers nuevos `tolls_per_agent_hourly`, `cu_components_per_agent_hourly`,
  `mem_costs_per_agent_hourly`),
  `data/mem_costs_no_regulado.csv` (NUEVO),
  `scenarios/scenario_c2_bilateral.py` (firma ampliada de `run_c2_bilateral`),
  `scenarios/comparison_engine.py` (propagacion de parametros descompuestos),
  `analysis/sensitivity.py` (cota refinada SA-3),
  `main_simulation.py` (wiring de los componentes descompuestos),
  `tests/test_cal16_savings_decomposition.py` (>=12 tests nuevos),
  `Documentos/notas_modelo_tesis.md` §3.8 (anexo CAL-16)
- **Relacionado con:** [ADR-0011 CAL-11](0011-cal11-c2-ppa-bilateral-modelo-formal.md)
  (modelo formal C2), [ADR-0012 CAL-12](0012-cal12-c2-fom-peajes.md)
  (Front-of-Meter), [ADR-0013 CAL-13](0013-cal13-c2-no-regulado.md)
  (comunidad MTE no-regulada agregada). **Supersede parcial** del agregado
  `pi_G = G + Cvm + COT` introducido por CAL-13: ahora se descompone en
  cuatro terminos con trazabilidad regulatoria por componente.
- **Memoria semantica:** `tesis-p2p / cal_16_c2_savings_decomposition`
- **Fuente normativa:**
  - **Ley 143/1994 art. 41** — mercado mayorista, contratos bilaterales:
    `G` es el unico componente "negociable libremente".
  - **CREG 086/1996 art. 1 mod. CREG 039/2001** — precio libre solo
    para usuarios no-regulados. El no-regulado se ahorra `Cvm` por
    sustitucion del comercializador minorista por representante en MEM.
  - **CREG 119/2007 arts. 6-14** — descomposicion CU = G + T + D + Cvm
    + PR + Rm; arts. 9, 10, 12, 13 fijan T, D, PR, Rm como cargos
    regulados al OR/STN obligatorios para todo usuario.
  - **CREG 156/2012** — figura del representante en MEM que sustituye
    al comercializador minorista para el usuario no-regulado.
  - **CREG 101-028/2023** — introduce COT (margen tributario del
    comercializador). Bajo CAL-16 se trata con un parametro `cot_alpha
    in [0, 1]` (default 1.0) para reflejar la incertidumbre normativa
    sobre si el no-regulado se ahorra COT integramente.
  - **Ley 1715/2014 art. 19** — FAZNI (Fondo de Apoyo Financiero para
    la Energizacion de las Zonas No Interconectadas), valor anual
    publicado por UPME. Modelado como 1.90 COP/kWh referencial.
  - **Ley 1117/2006 art. 2** prorrogada por **Ley 2099/2021 art. 45** —
    contribucion del 4 % al sector electrico. Modelada como
    `0.04 x G(t)`.
- **Fuente de codigo:** plan
  `C:\Users\burav\.claude\plans\usa-superpowers-brainstorm-y-las-prancy-crystal.md`
  (CAL-16, 2026-05-02).

## Contexto

CAL-13 (ADR-0013, 2026-05-01) alineo C2 legalmente al modelar la comunidad
MTE como usuario no-regulado agregado con ahorro:

```
savings_cons = E_PPA x ((G + Cvm + COT) - pi_ppa)
```

Esta formulacion es **una cota superior optimista**, porque:

1. **COT** (Costo Operativo Tributario, CREG 101-028/2023) es ambiguo
   regulatoriamente: el regulado lo paga obligatoriamente, pero el
   no-regulado podria no pagarlo (es margen del comercializador). La
   suma `G + Cvm + COT` postula que se ahorra integramente, sin
   modelar la incertidumbre.
2. **No descompone los componentes**: el sumando agregado oculta
   que `(G - pi_ppa)` es defendible al 100 % por Ley 143/1994 art. 41,
   `Cvm` es defendible al 100 % por CREG 086/1996, pero `COT` y los
   costos del MEM (FAZNI, 4 %, comision representante) merecen
   tratamiento separado.
3. **No modela los costos del usuario no-regulado en el MEM**: FAZNI
   (Ley 1715/2014 art. 19), contribucion 4 % al sector (Ley 1117/2006
   prorrogada por Ley 2099/2021 art. 45) y comision del representante
   en bolsa (CREG 156/2012). Estos son egresos al sistema externo, no
   transferencias entre miembros de la comunidad.

Auditoria 2026-05-02 con cuatro Explore agents y memoria Ruflo
confirmo:
- CSV `data/tarifas_cedenar_mensual.csv` tiene los **7 componentes
  oficiales literales del CU CEDENAR** (`Gm, Tm, Dnm, Cvm, PR, Rm,
  COT`) transcritos de los 13 PDFs `data/cedenar_pdfs/tarifa_*.pdf`,
  con valor abr-2026 NT2 oficial: G=310.96, T=55.95, D=165.37,
  Cvm=176.41, PR=21.09, R=30.64, COT=38.73, CU=799.16 COP/kWh.
- No existe helper que devuelva los peajes T+D+PR+Rm explicitamente
  ni el dict descompuesto de componentes.
- Los costos del MEM no-regulado no estan modelados.

## Decision

C2 calcula el ahorro del comprador no-regulado como **suma explicita
de cuatro componentes regulatorios trazables**:

```
savings_cons = E_PPA x [ (G - pi_ppa)               # negociable Ley 143/94
                       + Cvm                       # ahorro comercializacion CREG 086/96
                       + cot_alpha x COT           # cota tributaria CREG 101-028/23
                       - MEM_costs ]               # egresos no-regulado al MEM
```

donde
- `G`, `Cvm`, `COT` provienen literalmente del CSV CEDENAR
  (transcrito desde los PDFs oficiales).
- `cot_alpha in [0, 1]` parametriza la incertidumbre normativa sobre
  COT. Default `cot_alpha = 1.0` mantiene la cota CAL-13 como caso
  base; `cot_alpha = 0.0` devuelve la cota mas conservadora; barrido
  intermedio se ofrece como sensibilidad.
- `MEM_costs = FAZNI + 0.04 x G + pi_rep` se lee del CSV nuevo
  `data/mem_costs_no_regulado.csv` con citas normativas explicitas en
  la columna `fuente`. Default referencial 2025-2026: FAZNI=1.90,
  pi_rep=2.00 COP/kWh; contribucion 4 % es ley fija sobre `G`.

### API tecnica

Nueva firma de `run_c2_bilateral` (CAL-16):

```python
def run_c2_bilateral(
    ...,
    g_component,    cvm_component, cot_component,    # CREG 119/2007
    mem_costs,      cot_alpha=1.0,                   # CAL-16 nuevos
    pi_G=None,                                       # compat CAL-13
):
```

Si `g_component is not None`, modo CAL-16 (descompuesto). Si solo
`pi_G is not None`, modo CAL-13 (agregado, retro-compatible). Si
ninguno, modo BTM legacy pre-CAL-12.

### KPIs reportados

`per_agent` y `aggregate` ahora exponen:

- `savings_G`, `savings_Cvm`, `savings_COT`, `mem_costs`,
- `savings_ppa = savings_G + savings_Cvm + savings_COT - mem_costs`
  (lo mismo que `savings_cons` pre-CAL-16, descompuesto).

### Helpers nuevos

| Funcion | Devuelve | Norma |
|---|---|---|
| `tolls_per_agent_hourly` | (N, T) T+D+PR+Rm | CREG 119/2007 arts. 9, 10, 12, 13 |
| `cu_components_per_agent_hourly` | dict con G, T, D, Cvm, PR, R, COT, CU | CREG 119/2007 art. 2 |
| `mem_costs_per_agent_hourly` | (N, T) FAZNI + 0.04 G + pi_rep | Ley 1715/2014 + Ley 1117/2006 + CREG 156/2012 |

## Consecuencias

**Positivas:**
- Trazabilidad regulatoria componente-por-componente del ahorro.
- KPIs auditables: cada termino se puede comparar contra factura real.
- Test de reconciliacion `CU = G + T + D + Cvm + PR + R + COT`
  garantiza coherencia con los PDFs CEDENAR.
- Teorema de invarianza del bienestar agregado en `pi_ppa` se preserva.
- Bienestar es funcion lineal decreciente del costo total MEM
  (esperado: MEM es egreso real al sistema externo).

**Negativas / brechas:**
- KPI agregado de C2 cae 5-15 % vs CAL-13 (cota mas conservadora).
  Este es el numero **correcto regulatoriamente**; CAL-13 era
  optimista.
- Los valores referenciales de FAZNI=1.90 y comision representante=2.00
  son aproximaciones razonables 2025-2026. Si UPME publica FAZNI
  exacto por ano o si se obtiene comision real, se puede actualizar
  el CSV `data/mem_costs_no_regulado.csv` sin tocar el codigo.
- El cargo COT permanece como cota parametrizable (`cot_alpha`)
  porque no hay norma que aclare definitivamente si el no-regulado lo
  paga; default 1.0 mantiene cota CAL-13.

**Out-of-scope (declarado):**
- Modelar peajes T+D+PR+Rm como egreso del comprador (Filosofia A,
  consistente con C1).
- Recalibrar FAZNI por ano; se usara 1.90 COP/kWh como referencia.
- Negociar comision real del representante (pacto privado).
- Contribucion 20 % de solidaridad (Ley 142/1994).
- Take-or-Pay, Baseload, plazo, CFD financiero (CAL-11b out-of-scope).

## Alternativas rechazadas

- **Mantener CAL-13** (sumando agregado `pi_G = G+Cvm+COT`):
  rechazado por inexactitud normativa y por opacar los componentes.
- **Descomponer pero ignorar MEM_costs**: rechazado porque el modelo
  seria asimetrico (cuenta los ahorros pero ignora los costos
  reales del no-regulado).
- **Usar valores empiricos exactos por ano para FAZNI y comision
  representante**: rechazado de momento por costo de investigacion.
  El plan agendado lo deja como brecha futura.

## Plan de migracion / compatibilidad

- Tests CAL-11/12/13/13b siguen verdes con la firma vieja `pi_G=...`.
- Los modulos de `analysis/` (monthly_report, feasibility) consumen
  `per_agent` y `aggregate`; se mantienen retro-compatibles.
- `--full --analysis` regenera `outputs/` y `graficas/` con los
  nuevos campos descompuestos.

## Referencias

- Plan: `C:\Users\burav\.claude\plans\usa-superpowers-brainstorm-y-las-prancy-crystal.md`
- Spec: `docs/superpowers/specs/2026-05-02-cal16-c2-savings-decomposition.md`
- Datos: `data/tarifas_cedenar_mensual.csv`,
  `data/mem_costs_no_regulado.csv`, `data/cedenar_pdfs/tarifa_*.pdf`
- ADRs predecesores: 0011, 0012, 0013
- Tests: `tests/test_cal16_savings_decomposition.py`
