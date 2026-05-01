# Auditoría del escenario C2 (Contrato Bilateral PPA)

- **Fecha:** 2026-04-30
- **Autor:** Brayan S. Lopez-Mendez
- **Etiqueta:** CAL-11 (auditoría y formalización del modelo C2)
- **Relacionado:** ADR-006 (CAL-6 LCOE solar `b_n`), ADR-008 (CAL-8 tarifa Cedenar mensual), ADR-009 (CAL-9 `pi_gs (N, T)`), ADR-010 (CAL-10 CREG 174 Tipo 1/2 + componente C)
- **Memoria semántica:** `tesis-p2p / cal_11_c2_ppa_bilateral_audit`
- **Activa:** se debe leer junto con `Documentos/notas_modelo_tesis.md` §3.8

## 1. Contexto y motivación

El asesor cuestionó si el escenario **C2** del simulador realmente modela un *Power Purchase Agreement* (PPA) bilateral según la práctica comercial estándar, y si los precios usados tienen **sustento empírico** o son supuestos arbitrarios.

Un PPA bilateral, en su forma canónica, descansa sobre cinco elementos
(adaptación de la nota conceptual aportada por el asesor y de la entrada
"Power Purchase Agreement" en Wikipedia, así como del marco regulatorio
CREG 174/2021 y CREG 101 072/2025):

1. **Precio fijo** pactado entre generador y consumidor.
2. **Volumen y perfil**: *Pay-as-Produced* (toda la generación renovable
   cuando esté disponible) o *Baseload* (bloque firme 24/7).
3. **Plazo largo**, típicamente 5 a 20 años, condición de bancabilidad.
4. **Físico** (entrega real de energía a través de la red o detrás del
   medidor) versus **financiero / Contract for Difference (CFD)**, donde
   ambas partes liquidan a precio de bolsa y compensan la diferencia
   contra el precio pactado.
5. **Motivación**: certidumbre financiera tanto para el generador
   (bancabilidad del proyecto) como para el consumidor (cobertura ante
   volatilidad de la bolsa).

Esta auditoría reporta el estado del módulo
`scenarios/scenario_c2_bilateral.py`, contrasta cada elemento con la
implementación, audita el sustento de cada precio que C2 utiliza, y
documenta las brechas con respecto a PPAs reales firmados en Colombia.
La auditoría **no modifica la lógica del escenario**; sus salidas son
el ADR-0011 y los tests unitarios derivados.

## 2. Modelo actual de C2 — descripción precisa

Implementación en `scenarios/scenario_c2_bilateral.py:25-125`.

### 2.1 Algoritmo

Para cada hora `k ∈ [0, T)`:

1. **Autoconsumo local**: cada prosumidor `n ∈ prosumer_ids` valora
   `min(G[n,k], D[n,k])` a su tarifa minorista
   `pi_gs[n, k]` (matriz `(N, T)` post-CAL-9).
2. **Excedente agregado** del lado generador:
   `total_surplus = Σ_n max(G[n,k] − D[n,k], 0)` para
   `n ∈ prosumer_ids`.
3. **Distribución a consumidores** proporcional a la demanda
   instantánea `D[i, k]` para `i ∈ consumer_ids`:
   `share_i = D[i, k] / Σ_i D[i, k]`,
   `ppa_delivered_i = min(share_i · total_surplus, D[i, k])`.
4. **Liquidación**:
   - El consumidor `i` paga `pi_ppa` por `ppa_delivered_i` y, en
     consecuencia, ahorra `(pi_gs[i, k] − pi_ppa)` por kWh
     respecto al CU regulado.
   - El déficit residual `D[i, k] − ppa_delivered_i` se cubre con red
     a tarifa `pi_gs[i, k]` (sin descuento del componente C: el modelo
     C2 no aplica la lógica CAL-10 porque no es CREG 174).
   - El prosumidor `n` recibe `pi_ppa` por la fracción del excedente
     vendida vía PPA.
   - Cualquier excedente no absorbido por el contrato se vende a la
     red a precio `pi_gb` (precio de venta a bolsa, parametrizado como
     escalar fijo en el motor).

### 2.2 Filosofía contable (Filosofía A — WEEF Min 22-26)

```
net_benefit_n = savings_autoconsumo_n
              + savings_ppa_n               # solo consumidores
              + grid_revenue_n              # solo prosumidores con excedente no vendido
```

**No** se resta `grid_cost` residual. Justificación: el costo de
comprar a red el déficit que el PPA no cubrió se incurriría
igualmente sin contrato, por lo que tratarlo como "costo evitado"
inflaría artificialmente el net_benefit del consumidor sin contraparte
real (decisión documentada en ADR-0006/CAL-6 y consistente con la
filosofía aplicada en P2P, C1, C3, C4).

### 2.3 Parametrización del precio

```python
# main_simulation.py:269
pi_ppa = pi_gb + 0.5 * (pi_gs − pi_gb)        # default

# analysis/sensitivity.py + scenarios/scenario_c2_bilateral.ppa_price_range
# Análisis de sensibilidad SA-3:
factors = [0.25, 0.50, 0.75]
pi_ppa_range = [pi_gb + f * (pi_gs − pi_gb) for f in factors]
```

`pi_ppa` es un **escalar fijo en todo el horizonte y para todos los
agentes**. No depende del tiempo, no depende del agente, no depende
del precio de bolsa horario.

## 3. Inventario de precios — sustento

| Variable | Valor típico (abr-2026) | Origen | Sustento | ADR aplicable |
|---|---|---|---|---|
| `pi_gs` oficial NT2 | 799,16 COP/kWh | `data/cedenar_tariff.py` ← `data/tarifas_cedenar_mensual.csv` ← PDFs CEDENAR mensuales | **SUSTENTADO**: Resoluciones CREG 119/2007 y 101-028/2023, factura CEDENAR real | ADR-008, ADR-009 |
| `pi_gs` comercial NT2 | 958,99 COP/kWh | Idem | **SUSTENTADO** | ADR-008, ADR-009 |
| `pi_gb` precio bolsa | 200–250 COP/kWh promedio | `data/xm_prices.py` ← pydataxm / Sinergox / sintético calibrado | **SUSTENTADO** (datos reales jul-2025 a feb-2026) o **DERIVADO** (sintético calibrado contra promedios mensuales reales) | — |
| `b` LCOE solar | 225 COP/kWh (Fronius), 210 (Cesmag) | `data/parameters.py` | **SUSTENTADO**: rangos IRENA y UPME 200–250 COP/kWh para PV utility-scale Colombia | ADR-006 |
| `pi_ppa` | 553 COP/kWh (caso base, f=0,5) | `main_simulation.py:269` | **SUPUESTO**: factor `f=0,5` es elección de diseño, no observación empírica | (este documento → ADR-0011) |

El valor `pi_ppa = 553` corresponde al cálculo
`200 + 0,5·(906 − 200) = 553` con `pi_gs` comunitario ponderado
≈ 906 COP/kWh y `pi_gb` ≈ 200 COP/kWh.

## 4. Comparación con la teoría PPA bilateral

| Elemento canónico | Implementación en C2 | Estado |
|---|---|---|
| **Precio fijo** | `pi_ppa` escalar único en todo el horizonte | ✅ |
| Precio "menor que tarifa, mayor que bolsa promedio" | `f=0,5` ⇒ punto medio entre `pi_gb` y `pi_gs` | ✅ propiedad cumplida; ⚠️ valor del factor sin sustento empírico |
| **Volumen y perfil** | Pay-as-Produced (toda la generación PV se ofrece al contrato) | ⚠️ Baseload no modelado |
| **Plazo** | Implícito = horizonte completo (6 144 h ≈ 7 meses) | ❌ ausente como variable |
| **Físico vs financiero** | Físico puro: entrega real de energía al precio pactado | ⚠️ variante CFD no modelada |
| **Motivación financiera** | Eliminar volatilidad de bolsa para el comprador y dar ingreso estable al generador | ✅ reflejada en filosofía contable |
| **Reparto del excedente** | Proporcional a la demanda instantánea de cada consumidor | ✅ es una elección de diseño explícita |
| **Marco regulatorio** | El docstring no cita CREG, decreto ni paper | ❌ se corrige en ADR-0011 |

## 5. Sustento empírico del factor `f` — PPAs reales en Colombia

Definición operativa del factor empírico:

$$
f_{\text{emp}} = \frac{P_{\text{PPA,obs}} − P_{\text{bolsa,prom}}}{P_{\text{tarifa,obs}} − P_{\text{bolsa,prom}}}
$$

Si `P_PPA < P_bolsa_prom`, `f_emp < 0`. Si `P_PPA > P_tarifa`, `f_emp > 1`.
Bajo el modelo actual el rango "natural" se asume en `[0, 1]`.

### 5.1 Subastas UPME de Largo Plazo (CLPE)

| Subasta | Año | Precio adjudicado promedio | Plazo | Capacidad |
|---|---|---|---|---|
| CLPE 02-2019 | 2019 | **95,65 COP/kWh** (≈ 0,028 USD/kWh) | 15 años | 1 298 MW (5 eólicos + 3 solares) |
| CLPE 03-2021 | 2021 | **155,8 COP/kWh** (≈ 0,036 EUR/kWh) | 15 años | 796,3 MW (11 proyectos) |
| Subasta 2024 | 2024 | **≈ 75 COP/kWh** (0,0182 USD/kWh) | 15 años | 4,4 GW solar |

Fuentes: comunicado UPME 05-2019 [3]; pv-magazine [4]; energiaestrategica [5];
Solarpack-Ecoener [6]; pv-magazine 2024 [7]; subastas 02-2019 / 03-2021
en portal UPME [1, 2].

### 5.2 Contratos bilaterales del mercado mayorista

Reportes XM y Portafolio (Superservicios):

| Año | Mercado regulado | Mercado no regulado | Volumen anual |
|---|---:|---:|---:|
| 2023 | 284,25 COP/kWh | 277,43 COP/kWh | 94 311 GWh [8] |
| Sept 2024 | 320,82 COP/kWh (+11,7 % a/a) | 310,61 COP/kWh (+8,8 % a/a) | mismo orden [9] |

### 5.3 Precio de bolsa de referencia (XM)

Promedios anuales descargados directamente desde la API XM (`pydataxm.ReadDB`,
métrica `PrecBolsNaci`) usando `scripts/audit_xm_yearly_means.py`.
Cobertura completa horaria (8 760 ó 8 784 datos por año):

| Año | Media | Mediana | p25 | p75 | p90 | min | max |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2019 | **225,71** | 214,58 | 144,90 | 298,93 | 357,49 | 69,95 | 910,47 |
| 2021 | **139,33** | 101,53 | 91,65 | 161,69 | 240,15 | 81,76 | 566,47 |
| 2023 | **564,20** | 504,32 | 310,94 | 791,67 | 1 051,98 | 100,59 | 1 595,69 |
| 2024 | **682,48** | 591,01 | 371,05 | 832,11 | 1 090,26 | 95,85 | 2 675,65 |

Fuente complementaria: BMCBEC reporta cierre 2023 en 572,47 COP/kWh [10],
diferencia ≈ 1,5 % con la media simple horaria reportada arriba (debido a
ponderación por demanda vs ponderación uniforme).

Para el horizonte del proyecto MTE (jul-2025 a feb-2026) el rango es
138–305 COP/kWh (post-Niño 2023-2024) [12], evidenciando la fuerte
volatilidad interanual. CSV crudo de cada año en
`data/precios_bolsa_xm_audit_<año>.csv` (cache reproducible).

### 5.4 Cálculo del factor empírico `f_emp`

Bolsa anual descargada via `pydataxm` (§5.3). Tarifa `P_tarifa` (CU NT2)
usa el promedio CEDENAR del año aproximado (2019–2021 ≈ 700, 2023–2024
≈ 800, abr-2026 ≈ 906 COP/kWh).

| Caso | `P_PPA` | `P_bolsa,prom` (real) | `P_tarifa` (CU NT2) | `f_emp` |
|---|---:|---:|---:|---:|
| UPME 2019 (15 a) | 95,65 | 225,71 | 700 | **−0,274** |
| UPME 2021 (15 a) | 155,80 | 139,33 | 700 | **+0,029** |
| UPME 2024 solar (15 a) | 76,44 | 682,48 | 950 | **−2,267** |
| Bilateral mayorista regulado 2023 | 284,25 | 564,20 | 750 | **−1,507** |
| Bilateral mayorista no regulado 2023 | 277,43 | 564,20 | 750 | **−1,544** |
| Bilateral mayorista regulado sep-2024 | 320,82 | 682,48 | 800 | **−3,078** |
| **Default modelo C2 (CAL-9 / CAL-10b)** | **553** | 200 | 906 | **+0,500** |

**Hallazgo crítico**: el `f` empírico de los PPAs colombianos
documentados es **negativo en seis de siete casos** (rango −3,08 a −0,27)
y muy cercano a cero (+0,029) en el séptimo. Ningún caso real se
acerca al default del modelo `f = +0,5`.

**Caso atípico — UPME 2021 con f ≈ 0**: el precio adjudicado
(155,8 COP/kWh) coincidió casi exactamente con el promedio anual de bolsa
(139,3 COP/kWh) porque 2021 fue un año hidrológicamente favorable
(post-pandemia, embalses llenos), lo que comprimió la bolsa. Es la
excepción que confirma la regla: cuando la bolsa baja al nivel del
LCOE solar (~150 COP/kWh), el PPA y la bolsa convergen, pero el spread
PPA-tarifa sigue siendo grande y queda en su totalidad para el
comercializador, no para el generador ni el consumidor final.

### 5.5 Interpretación — por qué `f_emp < 0` en los datos colombianos

La condición `P_PPA < P_bolsa,prom` (es decir `f_emp < 0`) es estructural
del mercado mayorista colombiano por al menos cinco razones:

1. **Subastas de cargo por confiabilidad y CLPE** licitan
   *generación firme renovable* a 15 años, donde el precio se reduce
   por la certidumbre que el contrato aporta para la bancabilidad
   (NPV del flujo descontado de un IPP cubierto a 15 años justifica
   precios menores que la bolsa esperada).
2. **Bolsa colombiana volátil al alza** por exposición hidrológica
   (Fenómeno de El Niño 2023–2024 elevó la bolsa por encima de
   1 000 COP/kWh en varios meses).
3. **El comprador del PPA** (comercializador) **revende** la energía
   a tarifa al usuario regulado y captura el spread; no transfiere el
   ahorro de comprar barato al usuario final.
4. **Marco CREG 174/2021** obliga a los AGPE pequeños (hasta 0,1 MW)
   a vender excedentes al **precio de bolsa horario**, no permite
   firmar PPAs bilaterales con consumidores residenciales
   individuales.
5. **CREG 101 072/2025** (Comunidades Energéticas) habilita
   autogeneración colectiva (AC) y generación distribuida colectiva
   (GDC) con liquidación bidireccional horaria, pero los excedentes
   netos siguen valuándose contra bolsa, no contra un PPA pactado.

### 5.6 Por qué `f = 0,5` puede defenderse en el contexto comunitario de la tesis

El proyecto MTE no replica el mercado mayorista colombiano.
Lo que C2 modela es un **PPA hipotético comunitario sin intermediario**,
firmado entre cinco prosumidores institucionales en Pasto. En ese contexto:

- No hay banco financiando 15 años → el precio no necesita cubrir
  bancabilidad bajo presión de un IPP.
- No hay comercializador capturando spread → el ahorro tarifa-bolsa
  queda íntegro dentro de la comunidad.
- El espacio natural de pactado es `[pi_gb, pi_gs]`, no `[0, pi_bolsa]`.
- El factor `f` parametriza el **reparto** del excedente entre los
  dos extremos; `f = 0,5` es el postulado normativo de **equidad**:
  cada parte se queda con la mitad del spread.

Por tanto, la elección `f = 0,5` es **defendible como postulado normativo
de reparto simétrico**, no como observación empírica. Esta posición debe
quedar explícita en el ADR-0011 y en el manuscrito (capítulo 4, §C2).

## 6. Teorema de invarianza del bienestar agregado

`Documentos/notas_modelo_tesis.md` §3.8 establece:

$$
B_n^{C2}(\pi_{ppa}) =
\underbrace{\text{autoconsumo}_n \cdot \pi_{gs}}_{\text{ahorro base}}
+ \underbrace{\text{excedente vendido}_n \cdot \pi_{ppa}}_{\text{ingreso PPA}}
+ \underbrace{\text{energía recibida}_n \cdot (\pi_{gs} − \pi_{ppa})}_{\text{ahorro PPA}}
$$

En **comunidad cerrada** (excedente vendido = energía recibida), la
suma `Σ_n B_n^{C2}` es **constante** respecto a `pi_ppa`: la prima
adicional al generador y la pérdida de ahorro del comprador se
compensan exactamente. Por consiguiente, el factor `f` afecta la
**redistribución** del excedente entre tipos de agente, pero no
afecta la eficiencia agregada de C2.

Implicación operativa: la comparación P2P-vs-C2 a nivel agregado es
**robusta a la elección de `f`**. La discusión sobre `f` solo
condiciona la equidad (Gini, índice de equidad por agente).

Este teorema **debe ser un test unitario obligatorio** (ver Fase D).

## 7. Brechas conocidas y no implementadas

Las siguientes dimensiones del PPA canónico **se documentan como
brechas** y se dejan fuera del alcance de la tesis. La justificación es
que la tesis evalúa el **mecanismo P2P frente a alternativas
regulatorias colombianas existentes** (C1 = CREG 174, C4 = CREG 101 072,
y los regímenes individual/spot), y el rol de C2 es un escenario
contrafáctico de referencia, no una propuesta operativa.

| Brecha | Implicación | Trabajo futuro |
|---|---|---|
| **Variante CFD / financiera** | C2 actual es físico puro; un PPA financiero liquidaría a `pi_bolsa[k]` y compensaría la diferencia con `pi_ppa` | Rama `scenario_c2_bilateral_cfd.py` para tesis posterior |
| **Perfil Baseload** | Solo Pay-as-Produced está modelado; un PPA Baseload obligaría al generador a entregar un bloque firme 24/7 contraste a la curva PV | Requiere modelar fuente firme (no aplica a comunidad solar pura) |
| **Plazo contractual** | No hay variable de duración ni cláusulas de escalada/renegociación | Requiere extender el horizonte a años, integrar inflación y degradación PV |
| **Precios diferenciados por agente** | `pi_ppa` es escalar; un PPA real podría diferenciar por riesgo de crédito o por curva de carga | Podría modelarse como `pi_ppa[n, k]`, queda como CAL futuro |
| **Cláusula de incumplimiento (off-take)** | C2 asume entrega y pago perfectos; no modela impago ni interrupciones | Fuera del alcance de un modelo de bienestar puro |
| **Alineación con CREG 102 072 / 174** | C2 *no* representa un mecanismo legal disponible para AGPE residenciales; es contrafáctico | Documentar explícitamente en ADR-0011 §Consecuencias |

## 8. Recomendaciones

1. **Adoptar ADR-0011 (CAL-11)** que formalice el modelo C2 con su
   sustento empírico (este documento) y declare las brechas como
   decisiones de alcance.
2. **Añadir tests unitarios** (Fase D) que blinden:
   - balance de energía (Pay-as-Produced),
   - el teorema de invarianza,
   - el rango `[pi_gb, pi_gs]` del precio,
   - compatibilidad con `pi_gs (N, T)` post-CAL-9.
3. **Actualizar el docstring** de `scenarios/scenario_c2_bilateral.py`
   con cita a ADR-0011 y a este spec; añadir una línea "Sustento
   empírico: ver ADR-0011 §5".
4. **Añadir párrafo de sustento** al final de `notas_modelo_tesis.md`
   §3.8 que cite la tabla 5.4 (factor empírico colombiano) y declare
   que `f = 0,5` es un postulado normativo de reparto simétrico, no
   un valor observado.
5. **Reportar en el manuscrito (capítulo 4, §C2)** la naturaleza
   contrafáctica de C2 y la sensibilidad SA-3 ya implementada como
   evidencia de robustez de la comparación P2P-vs-C2.
6. **No cambiar el default `f = 0,5`** — el teorema de invarianza
   asegura que el agregado es invariante; cambiar el default
   afectaría la presentación de resultados sin valor analítico
   añadido.

## 9. Referencias

[1] Unidad de Planeación Minero-Energética (UPME), *Subasta CLPE No. 02-2019*. https://www1.upme.gov.co/PromocionSector/Subastas-largo-plazo/Paginas/Subasta-CLPE-No-02-2019.aspx (consultado 2026-04-30).

[2] UPME, *Subasta CLPE No. 03-2021*. https://www1.upme.gov.co/PromocionSector/Subastas-largo-plazo/Paginas/Subasta-CLPE-03-2021.aspx (consultado 2026-04-30).

[3] UPME, *Comunicado de Prensa 05-2019: Día histórico para las energías renovables en Colombia*. https://www1.upme.gov.co/SalaPrensa/ComunicadosPrensa/Comunicado_05_2019.pdf

[4] *La subasta de Colombia termina con precio promedio final de $0,027/kWh*, pv magazine Latin America, oct. 2019. https://www.pv-magazine-latam.com/2019/10/23/la-subasta-de-colombia-termina-con-precio-promedio-final-de-0027-kwh/

[5] *El listado de los adjudicatarios de la subasta de renovables en Colombia*, Energía Estratégica, oct. 2019.

[6] *Solarpack y Ecoener, adjudicatarios de la subasta de Colombia, cuyo precio medio es de 0,03560 €/kWh*, pv magazine España, oct. 2021.

[7] *Colombia assigns 4.4 GW of solar for $0.0182/kWh in latest energy auction*, pv magazine, feb. 2024.

[8] Superservicios, *Boletín de seguimiento y monitoreo de los mercados mayoristas de energía y gas*, marzo–mayo 2023. https://www.superservicios.gov.co/

[9] *En septiembre aumentaron los precios de los contratos bilaterales*, Portafolio, oct. 2024. https://www.portafolio.co/energia/

[10] BMCBEC, *Precio de energía en bolsa de Colombia cerró 2023 en $572,47/kWh*. https://www.bmcbec.com.co/

[11] XM, *Comunicados sobre las variables del mercado de energía*, abril, agosto, diciembre 2024. https://www.xm.com.co/

[12] Brayan S. Lopez-Mendez, datos del proyecto MTE — Medición de Tecnologías de Energía, 5 instituciones, Pasto, jul. 2025 – feb. 2026.

[13] Comisión de Regulación de Energía y Gas (CREG), *Resolución 174 de 2021*. Gestor Normativo CREG. https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_0174_2021.htm

[14] CREG, *Resolución 101 072 de 2025 (Comunidades Energéticas)*.

[15] *Power Purchase Agreement*, Wikipedia. https://en.wikipedia.org/wiki/Power_purchase_agreement

[16] B. S. Lopez-Mendez, *notas_modelo_tesis.md* §3.8 — Sensibilidad al precio del contrato bilateral PPA. Repositorio interno SistemaBL.

[17] B. S. Lopez-Mendez, ADR-0006 / ADR-0008 / ADR-0009 / ADR-0010, repositorio interno `docs/adr/`.

---

**Cierre.** Este spec es la base evidencial del ADR-0011 (CAL-11). Todas
las afirmaciones cuantitativas son trazables a las referencias
numeradas o al código fuente identificado por línea. Las brechas
documentadas en §7 reflejan decisiones explícitas de alcance, no
omisiones.
