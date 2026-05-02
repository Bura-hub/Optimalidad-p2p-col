# Spec — CAL-16: Descomposicion regulatoria del ahorro en C2

**Fecha:** 2026-05-02
**Autor:** Brayan S. Lopez-Mendez
**ADR vinculado:** [ADR-0016](../../adr/0016-cal16-c2-savings-decomposition.md)
**Plan vinculado:** `~/.claude/plans/usa-superpowers-brainstorm-y-las-prancy-crystal.md`
**Fase:** Validacion regulatoria (Actividades 3.1, 3.2, 3.3) y escritura
del manuscrito (Actividad 4.2).

## 1. Motivacion

CAL-13 (2026-05-01) alineo C2 legalmente al modelar la comunidad MTE
como usuario no-regulado agregado bajo Ley 143/1994 art. 41 + CREG
086/1996 + Decreto 388/2007. El ahorro del comprador quedo:

```
savings_cons = E_PPA × ((G + Cvm + COT) − pi_ppa)
```

**Problema:** la suma agregada `G + Cvm + COT` es una **cota superior
optimista** que mezcla tres componentes con respaldo regulatorio
heterogeneo. Adicionalmente no modela los **costos administrativos del
usuario no-regulado** en el MEM (FAZNI, contribucion 4 %, comision del
representante en bolsa), que son egresos reales al sistema externo.

CAL-16 elimina la opacidad descomponiendo el ahorro en cuatro
componentes regulatoriamente trazables y agregando los costos del
MEM como termino restado.

## 2. Formula completa CAL-16

```
                        ┌─ negociable Ley 143/1994 art. 41
                        │
savings_cons = E_PPA × [ (G − π_ppa)
                       + Cvm                       ◄── ahorro comercializacion
                       + α · COT                   ◄── cota tributaria
                       − MEM_costs ]               ◄── egresos no-regulado
                                          (FAZNI + 0.04·G + π_rep)

con α ∈ [0, 1], default α = 1.0
```

### Defensa normativa por componente

| Componente | Defensa | Norma | Comentario |
|---|---|---|---|
| `G − π_ppa` | 100 % | Ley 143/1994 art. 41 | G es el unico componente del CU "negociable libremente" en mercado mayorista. |
| `Cvm` | 100 % | CREG 086/1996 art. 1 mod. 039/2001 + CREG 156/2012 | El no-regulado no tiene comercializador minorista; lo sustituye un representante en MEM. |
| `α · COT` | parametrizado | CREG 101-028/2023 | COT es ambiguo: el regulado lo paga obligatoriamente, pero al no tener comercializador el no-regulado podria no pagarlo. Default α=1.0 mantiene cota CAL-13; α=0.0 cota conservadora. |
| `MEM_costs` (resta) | 100 % | Ley 1715/2014 art. 19 + Ley 1117/2006 art. 2 + Ley 2099/2021 art. 45 + CREG 156/2012 | Egresos reales al sistema externo del usuario no-regulado en el MEM. |

### MEM_costs descompuesto

```
MEM_costs = FAZNI + 0.04 · G + π_rep
          ≈ 1.90 + 0.04 · G + 2.00     [COP/kWh]
```

donde
- **FAZNI** (Fondo de Apoyo Financiero a la Energizacion de Zonas No
  Interconectadas, Ley 1715/2014 art. 19): valor anual publicado por
  UPME. Modelado como 1.90 COP/kWh referencial 2025-2026.
- **Contribucion 4 % al sector electrico** (Ley 1117/2006 art. 2
  prorrogada por Ley 2099/2021 art. 45): exigible al usuario
  no-residencial industrial/comercial. Aplica sobre el componente G
  efectivo.
- **π_rep** (comision del representante en MEM, CREG 156/2012): pacto
  privado en rango tipico ASOCODIS 2024 (1-3 COP/kWh). Modelado como
  2.00 COP/kWh referencial.

## 3. Mapeo norma ↔ codigo

| Norma | Componente | Archivo / linea | Test |
|---|---|---|---|
| Ley 143/1994 art. 41 | `G − π_ppa` | `scenarios/scenario_c2_bilateral.py` (linea con `savings_G += e * (g_v[i, k] - pi_ppa)`) | `test_run_c2_savings_descompuesto_es_suma_componentes` |
| CREG 086/1996 mod. 039/2001 | `Cvm` | `data/cedenar_tariff.cu_components_per_agent_hourly` (clave `Cvm`) | mismo test |
| CREG 119/2007 art. 11 | `Cvm` literalidad | columna `Cvm` del CSV | `test_reconciliacion_componentes_abr_2026_nt2_oficial` |
| CREG 101-028/2023 | `α · COT` | clave `COT` + parametro `cot_alpha` | mismo test |
| CREG 119/2007 arts. 9, 10, 12, 13 | T, D, PR, Rm (peajes) | `tolls_per_agent_hourly` (referencia, no se resta del ahorro por Filosofia A) | `test_tolls_per_agent_hourly_devuelve_NT_y_suma_correcta` |
| Ley 1715/2014 art. 19 | FAZNI | `mem_costs_per_agent_hourly` columna `fazni_cop_kwh` | `test_mem_costs_per_agent_hourly_fazni_y_4pct_y_rep` |
| Ley 1117/2006 + Ley 2099/2021 art. 45 | contribucion 4 % | `0.04 × Gm` en mismo helper | mismo test |
| CREG 156/2012 | comision representante | columna `comision_representante_cop_kwh` | mismo test |

## 4. Datos

### Fuente primaria: `data/tarifas_cedenar_mensual.csv`

Transcripcion de los 13 PDFs `data/cedenar_pdfs/tarifa_YYYY-MM.pdf`
(jul-2025 a abr-2026). Columnas:
`mes, categoria, nivel_tension, propiedad, Gm, Tm, Dnm, Cvm, PR, Rm,
COT, CU_aplicado, fuente`.

Reconciliacion exacta abr-2026 NT2 oficial (Udenar/HUDN):

| Componente | Valor (COP/kWh) | Norma |
|---|---:|---|
| Gm | 310.96 | CREG 119/2007 art. 6-8 |
| Tm | 55.95 | CREG 119/2007 art. 9 |
| Dnm | 165.37 | CREG 119/2007 art. 10 |
| Cvm | 176.41 | CREG 119/2007 art. 11 |
| PR | 21.09 | CREG 119/2007 art. 12 |
| Rm | 30.64 | CREG 119/2007 art. 13 |
| COT | 38.73 | CREG 101-028/2023 |
| CU_aplicado | 799.16 | suma |

### Fuente secundaria: `data/mem_costs_no_regulado.csv` (CAL-16, NUEVO)

Tabla mensual con valores referenciales 2025-2026:
`mes, fazni_cop_kwh, contrib_4pct_de, comision_representante_cop_kwh,
fuente`.

Default constante:
- FAZNI = 1.90 COP/kWh
- contrib_4pct_de = "Gm" (declarativo: helper aplica `0.04 × Gm`)
- comision_representante = 2.00 COP/kWh

Cita normativa explicita en columna `fuente` por fila.

## 5. API tecnica

### Nueva firma de `run_c2_bilateral`

```python
def run_c2_bilateral(
    D, G, pi_gs, pi_gb, pi_ppa,
    prosumer_ids, consumer_ids,
    # CAL-16 (descomposicion)
    g_component=None,    cvm_component=None, cot_component=None,
    mem_costs=None,      cot_alpha=1.0,
    # Compat CAL-13
    pi_G=None,
) -> dict
```

Logica:
1. Si `g_component is not None` → modo CAL-16 (descompuesto).
2. Si solo `pi_G is not None` → modo CAL-13 (agregado).
3. Si ninguno → modo BTM legacy pre-CAL-12.

### Output extendido

`per_agent[n]` ahora incluye:
- `savings_G`, `savings_Cvm`, `savings_COT`, `mem_costs`,
- `savings_ppa = savings_G + savings_Cvm + savings_COT - mem_costs`
  (descomposicion del antiguo `savings_cons`).

`aggregate` agrega los totales correspondientes.

`params` reporta medias por componente: `G_mean`, `Cvm_mean`,
`COT_mean`, `MEM_mean`.

## 6. Tests obligatorios

`tests/test_cal16_savings_decomposition.py` (>= 12 tests):

| # | Test | Garantiza |
|---|---|---|
| 1 | `test_tolls_per_agent_hourly_devuelve_NT_y_suma_correcta` | Helper peajes valor abr-2026 |
| 2 | `test_cu_components_per_agent_hourly_reconcilia_cu_aplicado` | Suma de componentes == CU |
| 3 | `test_mem_costs_per_agent_hourly_fazni_y_4pct_y_rep` | MEM = 1.90 + 0.04·G + 2.00 |
| 4 | `test_run_c2_savings_descompuesto_es_suma_componentes` | savings_ppa = G + Cvm + α·COT − MEM |
| 5 | `test_run_comparison_acepta_parametros_descompuestos` | comparison_engine acepta nuevos parametros |
| 6 | `test_main_simulation_construye_componentes_descompuestos` | main_simulation usa nuevos helpers + banner CAL-16 |
| 7 | `test_run_sensitivity_ppa_acepta_descomposicion_y_calcula_pi_upper` | SA-3 acepta nuevos parametros |
| 8 | `test_invarianza_bienestar_agregado_pi_ppa_CAL16` | Bienestar agregado invariante en π_ppa |
| 9 | `test_bienestar_decrece_lineal_en_mem_costs` | Bienestar lineal decreciente en MEM |
| 10 | `test_reconciliacion_componentes_abr_2026_nt2_oficial` | Valores PDF CEDENAR exactos |
| 11+ | Test no-regresion: 22 tests previos en `test_c2_bilateral.py` | Compat pre-CAL-16 |

## 7. Brechas residuales (out-of-scope CAL-16)

- **Valor exacto de FAZNI por año.** UPME publica resolucion anual; el
  CSV se puede actualizar sin tocar codigo. Brecha empirica menor.
- **Comision real del representante.** Pacto privado por contrato; no
  hay base de datos publica. Brecha estructural.
- **COT bajo no-regulado.** Sin norma que aclare definitivamente;
  `cot_alpha` lo parametriza para el lector.
- **Contribucion 20 % de solidaridad.** El no-regulado puede negociar
  exencion; fuera del modelo.

## 8. Verificacion end-to-end

1. `pytest tests/test_c2_bilateral.py -q` → 22/22
2. `pytest tests/test_cal16_savings_decomposition.py -q` → ≥ 12/12
3. `pytest tests/test_full_simulation_preflight.py -q` → 41/41
4. `pytest tests/ -q` → todo verde
5. `python main_simulation.py --data real` → banner `[CAL-16]` visible
6. `grep -r "CAL-16" scenarios/scenario_c2_bilateral.py main_simulation.py`
   con resultados.

## 9. Referencias

- Ley 143/1994 art. 41 — mercado mayorista, contratos bilaterales.
- Ley 1117/2006 art. 2 (prorrogada por Ley 2099/2021 art. 45).
- Ley 1715/2014 art. 19 — FAZNI.
- Ley 142/1994 art. 131 — solidaridad (out-of-scope).
- Ley 2099/2021 art. 45.
- Decreto 388/2007 — umbrales de no-regulado.
- CREG 086/1996 art. 1 mod. CREG 039/2001 — precio libre no-regulado.
- CREG 119/2007 — descomposicion CU.
- CREG 156/2012 — representante en MEM.
- CREG 174/2021 art. 23 num. 1.a — AGPE FNCER y no-regulados.
- CREG 101-028/2023 — COT.
