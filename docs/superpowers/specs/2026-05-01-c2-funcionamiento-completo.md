# Funcionamiento completo del escenario C2 (PPA bilateral comunitario no-regulado)

- **Fecha:** 2026-05-01 (CAL-13) · revisado 2026-05-02 (CAL-16)
- **Autor:** Brayan S. Lopez-Mendez
- **Estado:** Verificado y alineado con la ley colombiana post-CAL-16
  (descomposición regulatoria explícita del ahorro)
- **Cubre:** ADR-0011, ADR-0012, ADR-0013, **ADR-0016**
- **Memoria semántica:** `tesis-p2p / c2_funcionamiento_completo`,
  `tesis-p2p / project_cal16_c2_savings_decomposition`

## 1. Resumen ejecutivo

C2 modela un **contrato bilateral PPA físico, modalidad Pay-as-Produced,
de precio fijo**, firmado entre prosumidores AGPE FNCER ≤ 100 kW
(cada institución MTE) y la comunidad MTE constituida como
**usuario no-regulado agregado**. Es el único de los cuatro
escenarios regulatorios (C1, C2, C3, C4) que requiere un acuerdo
contractual privado entre las partes; los demás operan bajo
liquidaciones puramente regulatorias.

Función principal: `scenarios/scenario_c2_bilateral.run_c2_bilateral`.

## 2. Marco legal completo

| Capa | Norma | Mandato aplicado |
|---|---|---|
| **Habilitación** | Ley 143/1994 art. 41 | Los contratos bilaterales del MEM se firman entre generadores ↔ comercializadores ↔ usuarios no-regulados |
| | CREG 086/1996 art. 1 mod. CREG 039/2001 | Precio libremente pactado solo entre las partes habilitadas (no-regulados) |
| | CREG 174/2021 art. 23 num. 1.a | El AGPE FNCER puede vender excedentes a precio libre **si la energía se destina a usuarios no-regulados** |
| | Decreto 388/2007 | Umbral de no-regulado: demanda ≥ 55 MWh/mes o potencia conectada ≥ 100 kW |
| **Estructura** | CREG 156/2012 | Registro ASIC y cálculo de capacidad operativa (CROM) |
| | CREG 024/1995 | Reglas comerciales del MEM |
| **Residuo tarifario** | CREG 119/2007 arts. 6-14 | Descomposición CU = G + T + D + Cvm + PR + Rm + COT; G negociable; T+D+PR+Rm trasladables a cualquier usuario; Cvm + COT aplicables solo a usuarios regulados |

**Supuesto explícito del modelo (verificable empíricamente)**: las 5
instituciones MTE (Udenar, HUDN, Mariana, UCC, Cesmag) constituyen
una persona jurídica común (asociación, cooperativa o comunidad
energética) cuya demanda agregada cumple los umbrales del Decreto
388/2007. La validación con admin MTE confirmaría el supuesto sin
afectar el código del simulador.

## 3. Definiciones operativas

| Símbolo | Significado | Origen / unidad |
|---|---|---|
| `D[n, k]` | Demanda del agente `n` en hora `k` | kWh, datos MTE |
| `G[n, k]` | Generación PV bruta del agente `n` en hora `k` | kWh, datos MTE |
| `pi_gs[n, k]` | CU regulado completo (CEDENAR mensual) | COP/kWh, `data/cedenar_tariff.pi_gs_per_agent_hourly` |
| `g_component[n, k]` | Componente G del CU (Generación, único negociable) | COP/kWh, `data/cedenar_tariff.cu_components_per_agent_hourly["G"]` (CAL-16) |
| `cvm_component[n, k]` | Componente Cvm del CU (Comercialización Variable) | COP/kWh, `cu_components_per_agent_hourly["Cvm"]` (CAL-16) |
| `cot_component[n, k]` | Componente COT del CU (Costo Operativo Tributario) | COP/kWh, `cu_components_per_agent_hourly["COT"]` (CAL-16) |
| `mem_costs[n, k]` | Egresos del usuario no-regulado en el MEM | COP/kWh, `data/cedenar_tariff.mem_costs_per_agent_hourly` (CAL-16) |
| `cot_alpha` | Peso del COT en el ahorro (∈ [0, 1]) | adimensional, default 1.0 (CAL-16) |
| `pi_G[n, k]` | (compat CAL-13) agregado G + Cvm + COT | COP/kWh, `g_plus_commercialization_per_agent_hourly` |
| `pi_gb` | Precio de venta de excedente a la red (escalar) | COP/kWh, `data.parameters.GRID_PARAMS["pi_gb"]` |
| `pi_ppa` | Precio del contrato bilateral pactado (escalar) | COP/kWh, default = `pi_gb + 0,5·(pi_upper − pi_gb)` con `pi_upper = G+Cvm+α·COT−MEM` (CAL-16) |
| `prosumer_ids` | Índices de agentes con generación PV | lista |
| `consumer_ids` | Índices de consumidores puros | lista |

## 4. Mecánica del algoritmo (paso a paso)

Para cada hora `k ∈ [0, T)`:

### 4.1 Flujos físicos previos

```
gen_surplus[n] = max(G[n, k] − D[n, k], 0)        para n ∈ prosumer_ids
deficits[i]    = max(D[i, k] − G[i, k], 0)        para todo i
total_surplus  = Σ_{n ∈ prosumer_ids} gen_surplus[n]
```

### 4.2 Autoconsumo de cada prosumidor

```
para cada n ∈ prosumer_ids:
    autoconsumo = min(G[n, k], D[n, k])
    savings_gen[n] += autoconsumo · pi_gs[n, k]
```

**Justificación**: la energía autoconsumida no atraviesa la red, no
entra en el sistema de medición ni en la facturación de ningún
comercializador. El AGPE individual sigue siendo (al margen del PPA)
un usuario regulado individual; al autoconsumir, ahorra el CU
completo `pi_gs`.

### 4.3 Distribución del excedente vía PPA

Si `total_surplus > 0` y la demanda de los consumidores
`total_dem_cons = Σ_{i ∈ consumer_ids} D[i, k] > 0`:

```
share[i]         = D[i, k] / total_dem_cons
ppa_delivered[i] = min(share[i] · total_surplus, D[i, k])
```

Es decir, el excedente agregado se reparte entre consumidores
**proporcional a la demanda instantánea**, sin exceder lo que cada
consumidor demanda en esa hora.

### 4.4 Liquidación del comprador (consumidor de la comunidad) — CAL-16

Bajo CAL-16 (descomposición regulatoria explícita), el ahorro del
comprador no-regulado se desagrega en cuatro componentes trazables:

```
para cada i ∈ consumer_ids:
    e = ppa_delivered[i]
    savings_G[i]     += e · (g_component[i, k]   − pi_ppa)   # Ley 143/1994 art. 41
    savings_Cvm[i]   += e ·  cvm_component[i, k]              # CREG 086/1996
    savings_COT[i]   += e ·  cot_component[i, k] · cot_alpha  # CREG 101-028/2023
    mem_costs_arr[i] += e ·  mem_costs[i, k]                  # FAZNI+4%+rep
    residual_i = max(0, deficits[i] − e)
    grid_cost[i] += residual_i · pi_gs[i, k]
```

El ahorro total agregado del comprador es:

```
savings_ppa[i] = savings_G[i] + savings_Cvm[i] + savings_COT[i] − mem_costs_arr[i]
```

**Justificación normativa (defensa por componente)**:

- `savings_G = E_PPA · (G − π_ppa)` — Ley 143/1994 art. 41: G es el
  único componente del CU "negociable libremente" en el mercado mayorista.
- `savings_Cvm = E_PPA · Cvm` — CREG 086/1996 art. 1 mod. 039/2001 +
  CREG 156/2012: el no-regulado no tiene comercializador minorista; lo
  sustituye un representante en el MEM. Por eso se ahorra `Cvm` íntegro.
- `savings_COT = α · E_PPA · COT` — CREG 101-028/2023: COT es ambiguo
  (el regulado lo paga obligatoriamente; el no-regulado podría no
  pagarlo). El factor `α ∈ [0, 1]` parametriza esa incertidumbre;
  default `α = 1.0` mantiene la cota CAL-13, `α = 0.0` la cota más
  conservadora.
- `mem_costs = E_PPA · (FAZNI + 0.04·G + π_rep)` — Egresos reales del
  no-regulado al sistema externo: FAZNI ≈ 1.90 COP/kWh
  (Ley 1715/2014 art. 19), contribución 4 % al sector
  (Ley 1117/2006 art. 2 + Ley 2099/2021 art. 45), comisión del
  representante ≈ 2.00 COP/kWh (CREG 156/2012; pacto privado
  referencia ASOCODIS 2024).
- El déficit residual (lo que el PPA no cubre) se compra al CU
  regulado completo `pi_gs`. Los peajes T+D+PR+Rm sobre la energía
  recibida vía PPA no se contabilizan aquí (Filosofía A: solo
  ahorros e ingresos).

**Compatibilidad pre-CAL-16**:
- Si solo se pasa `pi_G` (modo CAL-13 agregado), `savings_G` recibe el
  agregado y `Cvm/COT/MEM = 0` — comportamiento legacy preservado.
- Si no se pasa nada, `pi_G = pi_gs` (BTM legacy pre-CAL-12).

### 4.5 Liquidación del vendedor (prosumidor con excedente)

```
para cada n ∈ prosumer_ids:
    frac          = gen_surplus[n] / total_surplus     (si total_surplus > 0)
    ppa_sold      = frac · Σ ppa_delivered[i]
    savings_gen[n] += ppa_sold · pi_ppa
    grid_revenue[n] += max(0, gen_surplus[n] − ppa_sold) · pi_gb
```

El prosumidor cobra `pi_ppa` por la energía vendida vía PPA y `pi_gb`
por el excedente que no se colocó en el contrato (vendido a la red
del comercializador).

### 4.6 Caso degenerado (sin PPA posible)

Si `total_surplus == 0` o `total_dem_cons == 0`:
- Cada prosumidor con surplus lo vende a `pi_gb`.
- Cada consumidor con déficit lo compra a `pi_gs`.

### 4.7 Bienestar neto por agente (Filosofía A)

```
savings_ppa[n] = savings_G[n] + savings_Cvm[n] + savings_COT[n] − mem_costs[n]
net_benefit[n] = savings_gen[n] + savings_ppa[n] + grid_revenue[n]
```

donde `savings_gen[n]` es el ahorro por autoconsumo más el ingreso
PPA del prosumidor; `savings_ppa[n]` es la descomposición CAL-16 del
ahorro del comprador no-regulado; `grid_revenue[n]` son los ingresos
del prosumidor por excedente vendido a la red.

**No** se resta `grid_cost`. Justificación: el costo de comprar a
red lo que el PPA no cubrió se incurriría igualmente sin contrato;
por tanto no se contabiliza como reducción del bienestar PPA.
Filosofía A es consistente con C1, C3, C4 y P2P (decisión asesor
WEEF, min 22-26).

> **Nota CAL-16**: el campo `savings_cons` en el `dict` devuelto se
> conserva por compatibilidad con módulos previos (`analysis/`,
> tests legacy) y es alias de `savings_ppa`.

## 5. Origen y validación de los datos

### 5.1 Tarifas CEDENAR (`pi_gs`)

- **Helper**: `data/cedenar_tariff.pi_gs_per_agent_hourly(agents, idx)`
- **Fuente**: CSV `data/tarifas_cedenar_mensual.csv`, transcrito desde
  los PDFs `data/cedenar_pdfs/tarifa_*.pdf` (CEDENAR mensuales)
- **Cobertura**: 13 meses (abr-2025 → abr-2026)
- **Diferenciación**: por (categoría tarifaria, nivel de tensión, propiedad)
- **ADR**: ADR-0008 (CAL-8) y ADR-0009 (CAL-9)

### 5.2 Componentes del CU descompuestos (CAL-16)

- **Helper**: `data/cedenar_tariff.cu_components_per_agent_hourly(agents, idx)`
- **Devuelve**: dict con claves `'G', 'T', 'D', 'Cvm', 'PR', 'R', 'COT', 'CU'`,
  cada una matriz `(N, T)` constante dentro del mes.
- **Fuente**: columnas `Gm, Tm, Dnm, Cvm, PR, Rm, COT, CU_aplicado`
  del CSV CEDENAR (transcritos del PDF mensual).
- **ADR**: ADR-0016 (CAL-16). Reemplaza el agregado `pi_G = G+Cvm+COT`
  por descomposición individual.

### 5.3 Costos del MEM no-regulado (CAL-16)

- **Helper**: `data/cedenar_tariff.mem_costs_per_agent_hourly(agents, idx)`
- **Fórmula**: `MEM(t) = FAZNI + 0.04 · G(t) + π_rep`
- **Fuente**: CSV nuevo `data/mem_costs_no_regulado.csv` (13 meses
  abr-2025 → abr-2026) con citas normativas en columna `fuente`:
  - `fazni_cop_kwh = 1.90` — Ley 1715/2014 art. 19
  - `contrib_4pct_de = "Gm"` (declarativo: `0.04 × G(t)`) —
    Ley 1117/2006 art. 2 + Ley 2099/2021 art. 45
  - `comision_representante_cop_kwh = 2.00` — CREG 156/2012,
    referencia ASOCODIS 2024
- **ADR**: ADR-0016 (CAL-16)

### 5.4 Peajes regulados T+D+PR+Rm (auditoría)

- **Helper**: `data/cedenar_tariff.tolls_per_agent_hourly(agents, idx)`
- **Devuelve**: matriz `(N, T)` con `Tm + Dnm + PR + Rm`.
- **Uso**: auditoría de reconciliación `CU = G + Cvm + COT + (T+D+PR+Rm)`.
  No entra en el cálculo de savings (Filosofía A).
- **ADR**: ADR-0016 (CAL-16); cargos por CREG 119/2007 arts. 9, 10, 12, 13.

### 5.5 Compatibilidad: `pi_G` (CAL-13 agregado)

- **Helper**: `data/cedenar_tariff.g_plus_commercialization_per_agent_hourly(agents, idx)`
- **Devuelve**: matriz `(N, T)` con `G + Cvm + COT`.
- **Estado**: preservado para compatibilidad pre-CAL-16. El motor C2
  aún acepta `pi_G` como atajo, pero la firma CAL-16 (descompuesta) es
  la canónica.
- **ADR**: ADR-0013 (CAL-13)

### 5.6 Precio de bolsa (`pi_gb`)

- **Origen**: `pydataxm` (API XM oficial) o sintético calibrado
- **ADR**: usado escalar fijo en C2 (no requiere precio horario)

### 5.7 Precio del contrato (`pi_ppa`)

- **Default CAL-16**: `pi_gb + 0,5·(pi_upper − pi_gb)` con
  `pi_upper = G + Cvm + α·COT − MEM`. Es la cota económicamente
  racional: si `pi_ppa > pi_upper` el comprador pierde dinero.
- **Sustento del factor `f = 0,5`**: postulado normativo de reparto
  simétrico (ADR-0011); el bienestar agregado es invariante en `f`
  por el teorema §3.8 (verificado bajo CAL-16 por
  `test_invarianza_bienestar_agregado_pi_ppa_CAL16`).

## 6. Ejemplo numérico — abril 2026, oficial NT2 (Udenar/HUDN)

### 6.1 Tarifas vigentes

| Componente | COP/kWh | % del CU |
|---|---:|---:|
| G | 310,96 | 39 % |
| T | 55,95 | 7 % |
| D | 165,37 | 21 % |
| Cvm | 176,41 | 22 % |
| PR | 21,09 | 3 % |
| Rm | 30,64 | 4 % |
| COT | 38,73 | 5 % |
| **CU = pi_gs** | **799,16** | 100 % |
| **G + Cvm + COT = pi_G (CAL-13)** | **526,10** | 65,8 % |
| Peajes T+D+PR+Rm | 273,06 | 34,2 % |

### 6.2 Costos del MEM no-regulado (CAL-16)

| Componente | Valor (COP/kWh) | Norma |
|---|---:|---|
| FAZNI | 1,90 | Ley 1715/2014 art. 19 |
| Contribución 4 % sobre G | 12,44 (= 0,04 × 310,96) | Ley 1117/2006 + Ley 2099/2021 art. 45 |
| Comisión representante MEM | 2,00 | CREG 156/2012 (ASOCODIS 2024) |
| **MEM total** | **16,34** | — |

### 6.3 Cálculo del precio default

Con `pi_gb = 195` COP/kWh y `α = 1.0`:

```
pi_upper       = G + Cvm + α·COT − MEM
              = 310,96 + 176,41 + 1,0·38,73 − 16,34
              = 509,76 COP/kWh
pi_ppa_default = 195 + 0,5 · (509,76 − 195) = 352,38 COP/kWh
```

### 6.4 Ahorro comparativo de un consumidor por kWh PPA

| Modelo | Fórmula | Ahorro |
|---|---|---:|
| pre-CAL-12 (BTM legacy) | `(CU − pi_ppa)` | ≈ 446,78 COP/kWh ⚠️ sobreestima |
| CAL-12 (FoM regulado) | `(G − pi_ppa)` | −41,42 COP/kWh ⚠️ negativo |
| CAL-13 (FoM no-regulado, agregado) | `((G+Cvm+COT) − pi_ppa)` | 173,72 COP/kWh ⚠️ cota optimista |
| **CAL-16 (descompuesto)** | `(G−pi_ppa) + Cvm + α·COT − MEM` | **157,38 COP/kWh** ✅ regulatoriamente exacto |

Bajo CAL-16, el default `f = 0,5` produce un ahorro positivo
descompuesto: `−41,42 + 176,41 + 38,73 − 16,34 = 157,38` COP/kWh,
trazable componente por componente a su norma.

### 6.5 Bienestar agregado esperado

Con horizonte 7 meses MTE (jul-2025 → ene-2026, 6 144 h, 5
instituciones, generación PV ~10 000 kWh agregados):

| Modelo | Bienestar agregado C2 estimado |
|---|---:|
| pre-CAL-12 (BTM legacy) | ≈ 51,4M COP (sobreestimado) |
| CAL-12 (FoM regulado) | ≈ 12-25M COP |
| CAL-13 (FoM no-regulado, cota optimista) | ≈ 25-35M COP |
| **CAL-16 (descompuesto, exacto)** | **≈ 22-32M COP** (cae 5-15 % vs CAL-13 por costos MEM) |
| P2P (referencia) | ≈ 52,4M COP (invariante) |

La conclusión P2P > C2 se mantiene reforzada: incluso bajo la cota
más conservadora (CAL-16) el P2P supera ampliamente a C2.

## 7. Garantías analíticas

### 7.1 Teorema de invarianza del bienestar agregado

En comunidad cerrada (`Σ ppa_delivered = Σ ppa_sold`):

$$
\sum_n B_n^{C2}(\pi_{ppa}) = \sum E_{PPA} \cdot pi_G + \text{(términos sin } \pi_{ppa}\text{)} = \text{constante}
$$

**Demostración**:

$$
\sum_i E_{PPA,i}(pi_G − pi_{ppa}) + \sum_n E_{PPA,n} \cdot pi_{ppa}
= \sum E_{PPA} \cdot pi_G − \sum E_{PPA} \cdot pi_{ppa} + \sum E_{PPA} \cdot pi_{ppa}
= \sum E_{PPA} \cdot pi_G
$$

independiente de `pi_ppa`. Verificado por
`tests/test_c2_bilateral.test_invarianza_bienestar_FoM_no_regulado_se_preserva`.

### 7.2 Conservación de energía (Pay-as-Produced)

Para cada `k`:

$$
G[n, k] = \text{autoconsumo}[n, k] + \text{ppa\_sold}[n, k] + \text{grid\_revenue\_kWh}[n, k]
$$

Verificado por `test_pay_as_produced_balance_generacion`.

### 7.3 Balance de demanda del consumidor

Para cada `i ∈ consumer_ids`, cada `k`:

$$
D[i, k] = \text{ppa\_delivered}[i, k] + \text{grid\_residual}[i, k]
$$

Verificado por `test_balance_energia_consumidor`.

### 7.4 Sensibilidad redistributiva (Gini varía con `f`)

Aunque el bienestar **agregado** es invariante en `f`, la
distribución intra-comunidad sí varía. El coeficiente de Gini de
`net_benefit[n]` cambia con `f`. Verificado por
`test_gini_no_invariante_a_f`.

## 8. Casos extremos y robustez

| Caso | Comportamiento | Test |
|---|---|---|
| `f = 0` ⇒ `pi_ppa = pi_gb` | Generador indiferente entre PPA y bolsa; comprador captura todo el spread | `test_invarianza_bienestar_FoM_no_regulado_se_preserva` con factores extremos |
| `f = 1` ⇒ `pi_ppa = pi_G` | Comprador indiferente; generador captura todo el spread | Idem |
| `pi_ppa > pi_G` | Comprador pierde dinero (ahorro negativo) — filtro económico | Implícito |
| Sin generación (todo `G = 0`) | `total_surplus = 0`, todos los consumidores compran a `pi_gs` | `else` branch línea 190-195 |
| Sin demanda en consumidores | `total_dem_cons = 0`, todo el surplus va a bolsa a `pi_gb` | Idem |
| `pi_gs` matriz `(N, T)` heterogénea | Cada agente liquida con su CU mensual | `test_pi_gs_matriz_diferenciada_por_agente` |
| `pi_G` escalar vs matriz `(N, T)` constante | Resultados idénticos (helper acepta ambas formas) | `test_pi_G_acepta_matriz_NT_y_escalar_equivalentes` |
| `pi_G = None` | Cae al comportamiento BTM legacy pre-CAL-12 (compatibilidad) | `test_pi_G_None_replica_legacy_BTM` |

## 9. Decisiones de modelado (caveats explícitos)

### 9.1 Autoconsumo se valora a `pi_gs` (no a `pi_ppa + peajes`)

**Decisión**: el autoconsumo del prosumidor se valora al CU regulado
completo `pi_gs`, **no** al costo efectivo bajo régimen no-regulado
`(pi_ppa + peajes)`.

**Justificación**: el AGPE individual sigue siendo, al margen del PPA,
un usuario regulado individual con su propia cuenta. La interpretación
del modelo es: cada AGPE es regulado para su propia demanda; solo el
flujo de excedentes vía PPA cae bajo el régimen no-regulado de la
comunidad. Esta interpretación es **simple, conservadora, y
coherente con el modelo base** [Chacón 2025] que trata cada agente
como persona regulada individual.

**Implicación**: el `savings_autoconsumo` calculado sobreestima el
ahorro real bajo régimen no-regulado en
`(pi_gs − (pi_ppa + peajes_T+D+PR+Rm)) = (pi_G − pi_ppa)` por kWh.
Este efecto es **conservador para la conclusión P2P > C2**: si se
ajustase, los KPIs de C2 caerían adicionalmente, reforzando aún más
la dominancia del P2P.

### 9.2 Filosofía A (no se resta `grid_cost`)

Decisión histórica del proyecto, validada por asesor Pantoja en
WEEF (`Documentos/conversacion_WEEF.txt` min 22-26). Consistente
con C1, C3, C4 y P2P. Un cambio a Filosofía B requeriría redefinir
todos los escenarios.

### 9.3 Reparto proporcional a demanda instantánea

El excedente se reparte entre los consumidores en proporción a su
demanda en la hora `k`. Alternativas posibles (descartadas por
simplicidad y por mantener simetría con el modelo base):

- Por capacidad PV instalada (estilo PDE de C4, CREG 101 072)
- Por turnos (round-robin)
- Subasta interna intracomunitaria (no aplica: C2 es PPA estático,
  no dinámico)

## 10. Brechas declaradas como out-of-scope (no son problemas)

| Brecha | Razón | ADR |
|---|---|---|
| Variante CFD/financiera | Estructura opuesta al PaP físico; cambia naturaleza de C2 | ADR-0011 §7 |
| Modalidad Take-or-Pay | Recurso solar puro no permite Baseload comprometido | ADR-0011 anexo CAL-11b |
| Indexación temporal `pi_ppa(t)` | Horizonte 7 meses; IPC ≈ 2 % despreciable | ADR-0011 §7 |
| Plazo contractual largo (5-20 años) | Horizonte fijo MTE | ADR-0011 §7 |
| Precios PPA diferenciados por agente | Simplicidad y simetría comunitaria | ADR-0011 §7 |
| Constitución legal formal de la persona jurídica MTE | Verificable empíricamente con admin MTE | ADR-0013 §7 |
| Registro ASIC del PPA | Administrativo; no afecta KPIs | ADR-0013 §1 |
| Valor exacto de FAZNI por año | UPME publica anual; CSV `mem_costs_no_regulado.csv` actualizable | ADR-0016 §Consecuencias |
| Comisión real del representante MEM | Pacto privado; valor referencial 2.00 COP/kWh ASOCODIS 2024 | ADR-0016 §Consecuencias |
| Contribución 20 % de solidaridad (Ley 142/1994 art. 131) | El no-regulado puede negociar exención | ADR-0016 §Consecuencias |
| ~~`run_sensitivity_ppa` rango actualizado~~ | ~~TODO post-CAL-13~~ → **resuelto en CAL-13b y refinado en CAL-16** (cota `pi_upper = G+Cvm+α·COT−MEM`) | ADR-0016 |

## 11. Tests que blindan el funcionamiento (22 + 12 verdes)

| # | Test | Verifica |
|---|---|---|
| 1 | `test_ppa_price_range_dentro_de_rango` | Precios default ∈ [pi_gb, pi_upper] |
| 2 | `test_ppa_price_range_factores_personalizados` | Frontera para `factors=[0,1]` |
| 3 | `test_invarianza_bienestar_agregado_comunidad_cerrada` | Σ B constante en `f` (BTM legacy) |
| 4 | `test_gini_no_invariante_a_f` | Gini varía con `f` (sentido informativo de SA-3) |
| 5 | `test_pay_as_produced_balance_generacion` | Conservación de energía generación |
| 6 | `test_balance_energia_consumidor` | Conservación demanda consumidor |
| 7 | `test_default_f_main_simulation_es_punto_medio` | Default reproducible |
| 8 | `test_pi_ppa_acepta_pi_gs_matriz_temporal` | Compatibilidad CAL-9 |
| 9 | `test_pi_gs_matriz_diferenciada_por_agente` | Heterogeneidad por agente |
| 10 | `test_pi_G_None_replica_legacy_BTM` | Backward compat CAL-11 |
| 11 | `test_savings_cons_uses_pi_G_not_CU` | Cambio CAL-12 (G no CU) |
| 12 | `test_invarianza_bienestar_FoM_se_preserva` | Teorema bajo CAL-12 |
| 13 | `test_kpi_C2_cae_drasticamente_vs_legacy_BTM` | Magnitud del cambio CAL-12 |
| 14 | `test_default_pi_ppa_es_punto_medio_pi_gb_y_G` | Default CAL-12 |
| 15 | `test_pi_G_acepta_matriz_NT_y_escalar_equivalentes` | Robustez de tipos |
| 16 | `test_g_component_per_agent_hourly_smoke` | Helper CAL-12 |
| 17 | `test_g_plus_commercialization_helper_smoke` | Helper CAL-13 |
| 18 | `test_helper_g_plus_strictly_greater_than_g_alone` | G+Cvm+COT > G |
| 19 | `test_savings_cons_es_mayor_bajo_no_regulado_que_regulado` | CAL-13 > CAL-12 |
| 20 | `test_invarianza_bienestar_FoM_no_regulado_se_preserva` | Teorema bajo CAL-13 |
| 21 | `test_default_pi_ppa_CAL13_punto_medio_pi_gb_y_negotiable` | Default CAL-13 |
| 22 | `test_run_sensitivity_ppa_usa_rango_pi_G_cuando_se_provee` | SA-3 acepta `pi_G` (CAL-13b) |

### 11.1 Tests CAL-16 — descomposición regulatoria (12/12)

`tests/test_cal16_savings_decomposition.py`:

| # | Test | Verifica |
|---|---|---|
| 1 | `test_tolls_per_agent_hourly_devuelve_NT_y_suma_correcta` | Helper peajes T+D+PR+R = 273,05 abr-2026 |
| 2 | `test_cu_components_per_agent_hourly_reconcilia_cu_oficial` | Σ componentes = CU (oficial); ratio 1.20 (comercial) |
| 3 | `test_mem_costs_per_agent_hourly_fazni_y_4pct_y_rep` | MEM = FAZNI+0.04·G+rep ≈ 16,34 |
| 4 | `test_run_c2_savings_descompuesto_es_suma_componentes` | Descomposición exacta vs cálculo manual |
| 5 | `test_run_c2_compat_pi_G_legacy_no_descompone` | Compat CAL-13: `pi_G=...` sigue funcionando |
| 6 | `test_run_comparison_acepta_parametros_descompuestos` | comparison_engine acepta nuevos params |
| 7 | `test_run_sensitivity_ppa_acepta_descomposicion_y_calcula_pi_upper` | SA-3 acepta nuevos params |
| 8 | `test_invarianza_bienestar_agregado_pi_ppa_CAL16` | Teorema §3.8 preservado bajo CAL-16 |
| 9 | `test_bienestar_decrece_lineal_en_mem_costs` | MEM es egreso externo → bienestar lineal |
| 10 | `test_invarianza_bienestar_agregado_cot_alpha` | α actúa linealmente sobre savings_COT |
| 11 | `test_reconciliacion_componentes_abr_2026_nt2_oficial` | G=310.96, T=55.95, D=165.37, Cvm=176.41, PR=21.09, R=30.64, COT=38.73, CU=799.16 |
| 12 | `test_reconciliacion_componentes_abr_2026_nt2_comercial` | CU=958.99 = 1.20 × 799.16 (Ley 142/1994) |

Suite global: todos los tests verdes (incluye 41 preflight `--full --analysis`).

## 12. Verificación de alineación regulatoria

| Criterio | Estado |
|---|---|
| Habilitación legal completa (Capa 1) | ✅ |
| Estructura contractual MEM (Capa 2) | ✅ con simplificaciones administrativas declaradas |
| Cláusulas estándar tipo CLPE (Capa 3) | ⚠️ PaP físico (declarado out-of-scope T-o-P, CFD) |
| Residuo tarifario CREG 119/2007 descompuesto por componente | ✅ exacto bajo CAL-16 |
| Costos del MEM no-regulado (FAZNI + 4 % + representante) | ✅ modelados (CAL-16) |
| Reconciliación con factura CEDENAR | ✅ (test reconciliación abr-2026) |
| Conservación de energía | ✅ |
| Filosofía contable A | ✅ |
| Teorema de invarianza en `pi_ppa` | ✅ preservado bajo CAL-16 |
| Linealidad del bienestar en MEM | ✅ verificada |
| Compatibilidad con tests previos | ✅ (firma `pi_G` preservada) |
| Documentación en código | ✅ docstring CAL-16 |
| Documentación normativa | ✅ ADR-0011/0012/0013/0016 + spec auditoría + este spec |

**Conclusión: C2 está completamente alineado con la ley colombiana
post-CAL-16** dentro del alcance de la tesis, con descomposición
regulatoria explícita por componente (Ley 143/1994, CREG 086/1996,
CREG 119/2007, CREG 156/2012, CREG 101-028/2023, Ley 1715/2014,
Ley 1117/2006, Ley 2099/2021). Las diferencias con el PPA tipo UPME
CLPE (T-o-P CFD vs PaP físico) están declaradas explícitamente y
pre-diseñadas como CAL-14a/b futuro si el asesor las exige.

## 13. Cómo se debe declarar en el manuscrito

En el cap. 4 §C2 debe aparecer:

> "El escenario C2 modela un contrato bilateral PPA físico, modalidad
> Pay-as-Produced, de precio fijo, firmado entre prosumidores AGPE
> FNCER ≤ 100 kW (cada institución MTE) y la comunidad MTE
> constituida como persona jurídica común calificada como usuario
> no-regulado agregado bajo Decreto 388/2007.
>
> Habilitación legal: Ley 143/1994 art. 41 (mercado mayorista,
> contratos bilaterales); CREG 086/1996 art. 1 mod. CREG 039/2001
> (precio libre para usuarios no-regulados); CREG 174/2021 art. 23
> num. 1.a (AGPE FNCER puede vender a precio libre si la energía se
> destina a usuarios no-regulados).
>
> El ahorro del comprador no-regulado se descompone explícitamente
> en cuatro términos regulatoriamente trazables (CAL-16):
>
> $$\mathrm{savings}^{C2} = E_{PPA}\bigl[(G - \pi_{ppa}) + Cvm + \alpha\,COT - \mathrm{MEM}\bigr]$$
>
> donde $G - \pi_{ppa}$ es el rango negociable bajo Ley 143/1994 art. 41;
> $Cvm$ se ahorra al 100 % por sustitución del comercializador minorista
> por representante en MEM (CREG 086/1996 + CREG 156/2012); $\alpha\,COT$
> es la cota tributaria parametrizable (CREG 101-028/2023, default
> $\alpha=1{,}0$); $\mathrm{MEM} = \mathrm{FAZNI} + 0{,}04\,G + \pi_{rep}$
> son los egresos del usuario no-regulado en el MEM
> (Ley 1715/2014 art. 19; Ley 1117/2006 + Ley 2099/2021 art. 45;
> CREG 156/2012). Los peajes $T+D+PR+Rm$ los paga el comprador al
> OR/STN como cargos regulados trasladables (CREG 119/2007 arts. 9,
> 10, 12, 13).
>
> El default $\pi_{ppa} = \pi_{gb} + 0{,}5\,(\pi_{upper} - \pi_{gb})$
> con $\pi_{upper} = G + Cvm + \alpha\,COT - \mathrm{MEM}$
> corresponde al postulado normativo de reparto simétrico entre
> generador y comprador. El teorema de invarianza demostrado en §3.8
> (verificado bajo CAL-16) garantiza que el bienestar agregado de C2
> no depende del valor específico de $\pi_{ppa}$.
>
> Brechas declaradas y verificables: (i) la constitución legal formal
> de la persona jurídica MTE como usuario no-regulado agregado se
> asume cumplida (verificable con admin MTE); (ii) la modalidad
> Take-or-Pay y la naturaleza financiera CFD del PPA tipo UPME CLPE
> no se modelan, dejándose como ejercicio de extensión futura;
> (iii) el valor exacto anual de FAZNI y la comisión real del
> representante MEM son referenciales 2025-2026, actualizables vía
> CSV `data/mem_costs_no_regulado.csv` sin tocar código."

## 14. Referencias

[1] B. S. Lopez-Mendez, *ADR-0011: Auditoría y formalización C2*,
`docs/adr/0011-cal11-c2-ppa-bilateral-modelo-formal.md`.

[2] B. S. Lopez-Mendez, *ADR-0012: Corrección Front-of-Meter*,
`docs/adr/0012-cal12-c2-fom-peajes.md`.

[3] B. S. Lopez-Mendez, *ADR-0013: Comunidad MTE como usuario
no-regulado agregado*, `docs/adr/0013-cal13-c2-no-regulado.md`.

[3b] B. S. Lopez-Mendez, *ADR-0016: Descomposición regulatoria del
ahorro en C2*, `docs/adr/0016-cal16-c2-savings-decomposition.md`.

[3c] B. S. Lopez-Mendez, *Spec CAL-16*,
`docs/superpowers/specs/2026-05-02-cal16-c2-savings-decomposition.md`.

[4] B. S. Lopez-Mendez, *Auditoría de alineación regulatoria C1 y
C2*, `docs/superpowers/specs/2026-05-01-c1-c2-regulatory-alignment-audit.md`.

[5] Congreso de la República, *Ley 143 de 1994*. https://www.upme.gov.co/wp-content/uploads/2025/02/Ley_143_1994.pdf

[6] CREG, *Resolución 086 de 1996* mod. *Resolución 039 de 2001*.

[7] CREG, *Resolución 174 de 2021*. https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_0174_2021.htm

[8] CREG, *Resolución 119 de 2007*. https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_0119_2007.htm

[9] MinMinas, *Decreto 388 de 2007* (umbrales de usuario no-regulado).

[10] CREG, *Resolución 156 de 2012* (registro ASIC).

[11] B. S. Lopez-Mendez, *notas_modelo_tesis.md* §3.8.

[12] S. Chacón et al., *Modelo P2P EMS basado en Stackelberg + RD*, 2025.
