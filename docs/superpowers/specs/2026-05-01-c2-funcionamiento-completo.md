# Funcionamiento completo del escenario C2 (PPA bilateral comunitario no-regulado)

- **Fecha:** 2026-05-01
- **Autor:** Brayan S. Lopez-Mendez
- **Estado:** Verificado y alineado con la ley colombiana post-CAL-13
- **Cubre:** ADR-0011, ADR-0012, ADR-0013
- **Memoria semántica:** `tesis-p2p / c2_funcionamiento_completo`

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
| `pi_G[n, k]` | Rango negociable + ahorro comercialización (G + Cvm + COT) | COP/kWh, `data/cedenar_tariff.g_plus_commercialization_per_agent_hourly` |
| `pi_gb` | Precio de venta de excedente a la red (escalar) | COP/kWh, `data.parameters.GRID_PARAMS["pi_gb"]` |
| `pi_ppa` | Precio del contrato bilateral pactado (escalar) | COP/kWh, default = `pi_gb + 0,5·(mean(pi_G) − pi_gb)` |
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

### 4.4 Liquidación del comprador (consumidor de la comunidad)

```
para cada i ∈ consumer_ids:
    savings_cons[i] += ppa_delivered[i] · (pi_G[i, k] − pi_ppa)
    residual_i = max(0, deficits[i] − ppa_delivered[i])
    grid_cost[i] += residual_i · pi_gs[i, k]
```

**Justificación**:
- El comprador no-regulado paga `pi_ppa` por la energía PPA y T+D+PR+Rm
  al OR/STN (peajes regulados, no contabilizados aquí por filosofía A,
  pero implícitamente reflejados en que el ahorro se calcula sobre
  `pi_G = G + Cvm + COT` y NO sobre el CU completo).
- El déficit residual (lo que el PPA no cubre) lo compra al CU
  regulado completo `pi_gs` (caso conservador: si el AGPE no genera
  suficiente, el resto va a tarifa minorista).

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
net_benefit[n] = savings_gen[n] + savings_cons[n] + grid_revenue[n]
```

**No** se resta `grid_cost`. Justificación: el costo de comprar a
red lo que el PPA no cubrió se incurriría igualmente sin contrato;
por tanto no se contabiliza como reducción del bienestar PPA.
Filosofía A es consistente con C1, C3, C4 y P2P (decisión asesor
WEEF, min 22-26).

## 5. Origen y validación de los datos

### 5.1 Tarifas CEDENAR (`pi_gs`)

- **Helper**: `data/cedenar_tariff.pi_gs_per_agent_hourly(agents, idx)`
- **Fuente**: CSV `data/tarifas_cedenar_mensual.csv`, transcrito desde
  los PDFs `data/cedenar_pdfs/tarifa_*.pdf` (CEDENAR mensuales)
- **Cobertura**: 13 meses (abr-2025 → abr-2026)
- **Diferenciación**: por (categoría tarifaria, nivel de tensión, propiedad)
- **ADR**: ADR-0008 (CAL-8) y ADR-0009 (CAL-9)

### 5.2 Rango negociable + ahorro comercialización (`pi_G`)

- **Helper**: `data/cedenar_tariff.g_plus_commercialization_per_agent_hourly(agents, idx)`
- **Fuente**: columnas `Gm + Cvm + COT` del mismo CSV
- **ADR**: ADR-0013 (CAL-13)

### 5.3 Precio de bolsa (`pi_gb`)

- **Origen**: `pydataxm` (API XM oficial) o sintético calibrado
- **ADR**: usado escalar fijo en C2 (no requiere precio horario)

### 5.4 Precio del contrato (`pi_ppa`)

- **Default**: `pi_gb + 0,5·(mean(pi_G) − pi_gb)` — punto medio del
  rango natural CAL-13
- **Sustento del factor `f = 0,5`**: postulado normativo de reparto
  simétrico (ADR-0011); el bienestar agregado es invariante en `f`
  por el teorema §3.8

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

### 6.2 Cálculo del precio default

Con `pi_gb = 195` COP/kWh:

```
pi_ppa_default = 195 + 0,5 · (526,10 − 195) = 360,55 COP/kWh
```

### 6.3 Ahorro comparativo de un consumidor por kWh PPA

| Modelo | Fórmula | Ahorro |
|---|---|---:|
| pre-CAL-12 (BTM legacy) | `(CU − pi_ppa)` | 438,61 COP/kWh ⚠️ sobreestima |
| CAL-12 (FoM regulado) | `(G − pi_ppa)` | −49,59 COP/kWh ⚠️ negativo (descarta π_ppa) |
| **CAL-13 (FoM no-regulado)** | `((G + Cvm + COT) − pi_ppa)` | **165,55 COP/kWh** ✅ |

El default `f = 0,5` produce un ahorro positivo bajo CAL-13, lo que
hace al contrato económicamente racional para el comprador
no-regulado.

### 6.4 Bienestar agregado esperado

Con horizonte 7 meses MTE (jul-2025 → ene-2026, 6 144 h, 5
instituciones, generación PV ~10 000 kWh agregados):

| Modelo | Bienestar agregado C2 estimado |
|---|---:|
| pre-CAL-12 (BTM legacy) | ≈ 51,4M COP (sobreestimado) |
| CAL-12 (FoM regulado) | ≈ 12-25M COP |
| **CAL-13 (FoM no-regulado)** | **≈ 25-35M COP (cota intermedia)** |
| P2P (referencia) | ≈ 52,4M COP (invariante) |

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
| Comisión del representante MEM | Asumida = 0 (representante = entidad comunitaria) | ADR-0013 §7 |
| Registro ASIC del PPA | Administrativo; no afecta KPIs | ADR-0013 §1 |
| `run_sensitivity_ppa` rango actualizado | TODO post-CAL-13, no urgente | ADR-0013 — Consecuencias |

## 11. Tests que blindan el funcionamiento (21/21 verdes)

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

Suite global: 79/79 verdes (1:52 min).

## 12. Verificación de alineación regulatoria

| Criterio | Estado |
|---|---|
| Habilitación legal completa (Capa 1) | ✅ |
| Estructura contractual MEM (Capa 2) | ✅ con simplificaciones administrativas declaradas |
| Cláusulas estándar tipo CLPE (Capa 3) | ⚠️ PaP físico (declarado out-of-scope T-o-P, CFD) |
| Residuo tarifario CREG 119/2007 (Capa 4) | ✅ correcto bajo CAL-13 |
| Conservación de energía | ✅ |
| Filosofía contable A | ✅ |
| Teorema de invarianza | ✅ |
| Compatibilidad con tests previos | ✅ |
| Documentación en código | ✅ docstring CAL-13 |
| Documentación normativa | ✅ ADR-0011/0012/0013 + spec auditoría + este spec |

**Conclusión: C2 está completamente alineado con la ley colombiana
post-CAL-13** dentro del alcance de la tesis. Las diferencias con el
PPA tipo UPME CLPE (T-o-P CFD vs PaP físico) están declaradas
explícitamente y pre-diseñadas como CAL-14a/b futuro si el asesor
las exige.

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
> El alcance del precio respeta CREG 119/2007: π_ppa solo desplaza
> el componente G del CU; el comprador no-regulado se ahorra
> adicionalmente Cvm + COT (margen del comercializador minorista,
> que no aplica al régimen no-regulado), pero sigue pagando T+D+PR+Rm
> al OR/STN como cargos regulados trasladables.
>
> El default π_ppa = π_gb + 0,5·((G + Cvm + COT) − π_gb) corresponde
> al postulado normativo de reparto simétrico del excedente entre
> generador y comprador. El teorema de invarianza demostrado en §3.8
> garantiza que el bienestar agregado de C2 no depende del valor
> específico de π_ppa, lo que hace robusta la comparación P2P-vs-C2 a
> esta elección.
>
> Brechas declaradas y verificables: (i) la constitución legal formal
> de la persona jurídica MTE como usuario no-regulado agregado se
> asume cumplida (verificable con admin MTE); (ii) la modalidad
> Take-or-Pay y la naturaleza financiera CFD del PPA tipo UPME CLPE
> no se modelan, dejándose como ejercicio de extensión futura."

## 14. Referencias

[1] B. S. Lopez-Mendez, *ADR-0011: Auditoría y formalización C2*,
`docs/adr/0011-cal11-c2-ppa-bilateral-modelo-formal.md`.

[2] B. S. Lopez-Mendez, *ADR-0012: Corrección Front-of-Meter*,
`docs/adr/0012-cal12-c2-fom-peajes.md`.

[3] B. S. Lopez-Mendez, *ADR-0013: Comunidad MTE como usuario
no-regulado agregado*, `docs/adr/0013-cal13-c2-no-regulado.md`.

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
