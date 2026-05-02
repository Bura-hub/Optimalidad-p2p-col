# Auditoría de alineación regulatoria — Escenarios C1 y C2

- **Fecha:** 2026-05-01 · revisado 2026-05-02 con anexo CAL-16
- **Autor:** Brayan S. Lopez-Mendez
- **Etiqueta:** auditoría post-CAL-12 → ampliada a CAL-13 → refinada
  por CAL-16 (descomposición regulatoria del ahorro)
- **Relacionado:** ADR-0008/0009/0010/0011/0012
- **Memoria semántica:** `tesis-p2p / regulatory_alignment_c1_c2_2026_05`

## 1. Objetivo y nota metodológica

Verificar que los escenarios C1 (CREG 174/2021 — AGPE) y C2 (PPA
bilateral) implementados en el simulador están **completamente
alineados** con las resoluciones aplicables tras los ciclos de
calibración CAL-8 → CAL-12. Reporte sin cambios de código.

**Nota metodológica (corrección 2026-05-01)**: la primera versión
de este spec auditaba C2 contra **CREG 119/2007**, lo cual es
incorrecto. CREG 119/2007 define la **fórmula tarifaria del usuario
regulado**, no la naturaleza del PPA. El marco regulatorio correcto
para auditar un PPA bilateral en Colombia se desglosa en cuatro
capas (de mayor a menor prelación):

| Capa | Pregunta | Marco aplicable |
|---|---|---|
| 1. Habilitación legal | ¿Quién puede firmar PPAs y con quién? | **Ley 143/1994** arts. 41-43 (mercado mayorista); **CREG 086/1996** art. 1 mod. CREG 039/2001 (precio libre solo para usuarios no regulados); **CREG 174/2021** arts. 22-25 (régimen específico AGPE) |
| 2. Estructura contractual | ¿Cómo se registra y liquida un PPA? | **CREG 156/2012** (registro ASIC y CROM); **CREG 024/1995** (aspectos comerciales del MEM); **CREG 130/2019** y **131/1998** (contratos de usuarios no regulados) |
| 3. Cláusulas estándar | ¿Take-or-Pay vs PaP, indexación, plazo? | **MME 4-0590/2019** y **4-0678/2019** (subastas largo plazo); **minuta UPME CLPE-02-2019/CLPE-03-2021/2024** (contrato modelo) |
| 4. Residuo tarifario | ¿Qué peajes paga un usuario regulado que hipotéticamente firmara un PPA? | **CREG 119/2007** arts. 6-14 (descomposición CU = G + T + D + Cvm + PR + Rm + COT) |

CAL-12 corrigió el escenario en la capa 4 (peajes obligatorios al
usuario regulado bajo el residuo tarifario CREG 119). La auditoría
de capas 1-3 no requiere cambios de código adicionales pero **sí
exige declarar la naturaleza del modelo C2 con citas correctas**.

## 2. Capacidad instalada de la comunidad MTE — definición del régimen aplicable

| Institución | Capacidad PV nominal | Régimen CREG 174 |
|---|---|---|
| Udenar (Edif. Ciencias) | ~15 kWp | AGPE ≤ 100 kW |
| Mariana | < 100 kW (Fronius) | AGPE ≤ 100 kW |
| UCC | < 100 kW (Fronius) | AGPE ≤ 100 kW |
| HUDN | < 100 kW (Fronius) | AGPE ≤ 100 kW |
| Cesmag | < 100 kW (otro inversor) | AGPE ≤ 100 kW |

Fuente: `Documentos/notas_modelo_tesis.md:1349` (Udenar 15 kWp);
`data/xm_prices.py:79` ("Fronius capacidad ≤ 100 kW");
`analysis/feasibility.py:551`.

**Implicación regulatoria**: en la permuta Tipo 1 de CREG 174 art. 25,
los AGPE ≤ 100 kW **solo descuentan el componente Cvm**; T+D+PR+R
**NO** se descuentan. AGPE > 100 kW sí los descuentan. Como toda la
comunidad MTE es ≤ 100 kW, aplica el régimen de descuento solo Cvm
(implementado en CAL-10b.2).

## 3. Auditoría C1 — alineación con CREG 174/2021 art. 25

C1 implementa el régimen AGPE ≤ 100 kW. Tras CAL-10b.2:

| # | Cláusula CREG 174 | Implementación en C1 | Estado |
|---|---|---|---|
| 1 | Art. 25 — clasificación Tipo 1 (≤ importación, crédito) y Tipo 2 (> importación, bolsa) | `scenario_c1_creg174.py:182-197` — bucle `iny_acum vs ret_acum` con hora `Hx` | ✅ |
| 2 | Art. 25 — Tipo 2 valorada al **precio horario** de bolsa | Línea 218: `revenue_m = np.dot(surplus_t2, pb_h)` (no promedio) | ✅ Corregido en CAL-10b.1 |
| 3 | Art. 25 — Tipo 1 permutada a tarifa retail menos Comercialización | Línea 215: `savings_m = E_auto·pi_gs + E_t1·(pi_gs − pi_C)` | ✅ Corregido en CAL-10/10b/10b.2 |
| 4 | Componente C = **Cvm puro** (no Cvm+COT) por literalidad del art. 25 que cita CREG 119/2007 art. 11 | `data/cedenar_tariff.cvm_per_agent_hourly` | ✅ Corregido en CAL-10b.2 |
| 5 | Autoconsumo no atraviesa la red → **no se factura C** | Línea 215: autoconsumo a `pi_gs` completo | ✅ |
| 6 | Liquidación **mensual** (período de facturación) | `period_hours = month_labels` (CAL-9) | ✅ |
| 7 | AGPE ≤ 100 kW: **NO** se descuenta T+D+PR+R en la permuta Tipo 1 | C1 solo descuenta `pi_C` | ✅ |
| 8 | Asignación intramensual de horas Tipo 2 cuando inyección acumulada cruza retiro acumulado | Orden cronológico (horas posteriores al cruce `Hx`) | ✅ Defensible (CREG no especifica criterio) |
| 9 | Comercializador obligado a recibir excedentes para usuarios **regulados** | C1 entrega Tipo 1 al comercializador (descuento C) y Tipo 2 al ASIC (precio bolsa) | ✅ |
| 10 | Crédito de energía no acumulable entre meses | `month_labels` cierra cada mes | ✅ |
| 11 | Costo residual de red al CU completo | Línea 222: `grid_cost_m = max(0, E_deficit−E_surplus) × pi_gs_period` | ✅ |

**Conclusión C1**: alineado con CREG 174/2021 art. 25 para el régimen
AGPE ≤ 100 kW. **No se identifican brechas residuales**.

## 4. Auditoría C2 — alineación con el marco contractual del MEM

C2 modela un PPA bilateral entre los AGPE residenciales de la
comunidad MTE. Esta auditoría compara C2 contra el marco contractual
real del PPA en Colombia (capas 1-3 de §1) y contra el residuo
tarifario (capa 4).

### 4.1 Capa 1 — habilitación legal del PPA

| Norma | Mandato | C2 | Estado |
|---|---|---|---|
| **Ley 143/1994 art. 41** | Los contratos bilaterales son instrumento del MEM entre **generadores y comercializadores o usuarios no regulados** | C2 modela contrato AGPE residencial ↔ consumidor residencial regulado | ❌ **INCOMPATIBLE** con la habilitación legal |
| **CREG 086/1996 art. 1 mod. 039/2001** | Precio libre vía contrato bilateral **solo aplica a usuarios no regulados**; para regulados aplican mecanismos del comercializador | Las 5 instituciones MTE son usuarios regulados (oficial/comercial NT2) | ❌ **INCOMPATIBLE** |
| **CREG 174/2021 art. 23 num. 1.a** | Confirma para AGPE: precio libremente pactado solo si la energía se destina a usuarios **no regulados** | C2 destina energía a regulados | ❌ **INCOMPATIBLE** |
| **CREG 174/2021 art. 25** | AGPE ≤ 100 kW debe vender excedentes al **comercializador que atiende al usuario** (Tipo 1 permuta, Tipo 2 bolsa). No autoriza PPA bilateral con consumidor residencial. | C2 implementa el contrato bilateral igualmente | ❌ **INCOMPATIBLE** |

C2 es **contrafáctico por construcción**: bajo el marco regulatorio
colombiano vigente, los AGPE residenciales no pueden firmar PPAs
bilaterales con consumidores residenciales. Esta naturaleza ya está
declarada en ADR-0011 §2 y reforzada en ADR-0012 §1; aquí queda
documentada con las citas legales correctas (Ley 143/1994 +
CREG 086/1996 + CREG 174/2021), no con la cita errónea a CREG 119/2007.

### 4.2 Capa 2 — estructura contractual del MEM

| Norma | Mandato | C2 | Estado |
|---|---|---|---|
| **CREG 156/2012** | PPAs largo plazo se registran en ASIC; ASIC calcula CROM (capacidad operativa) | No modelado (administrativo) | N/A out-of-scope |
| **CREG 024/1995** | Liquidación a través del ASIC con resolución diaria-horaria | C2 liquida hora a hora pero sin paso por ASIC | ⚠️ Simplificación aceptable |
| **CREG 130/2019, 131/1998** | Contratos para usuarios no regulados | No aplica (comunidad regulada) | N/A |

### 4.3 Capa 3 — cláusulas estándar (modelo UPME CLPE)

El **contrato modelo CLPE** de UPME (CLPE-02-2019, CLPE-03-2021, 2024)
es la referencia industrial pública más cercana a un "PPA tipo" en
Colombia. Sus cláusulas características:

| Cláusula CLPE | Característica | C2 | Estado |
|---|---|---|---|
| Tipo de contrato | **Financiero (CFD)**: liquidación contra bolsa con compensación al precio pactado | C2 modela **físico**: entrega real al precio pactado | ⚠️ Diferencia estructural |
| Modalidad | **Pague lo contratado (Take-or-Pay)**: comprador paga el bloque pactado independiente del consumo | C2 modela **Pay-as-Produced** | ⚠️ Diferencia estructural |
| Plazo | **15 años** | Implícito = horizonte 7 meses MTE | ⚠️ Out-of-scope (ADR-0011) |
| Indexación | Anual por **IPP** | Escalar fijo | ⚠️ Out-of-scope (ADR-0011) |
| Garantías | Aval bancario 30% energía anualizada × precio | No modelado | N/A out-of-scope |
| Resolución de la curva | Hora por hora durante plazo de suministro | Hora por hora ✅ | ✅ |
| Marco habilitante | MME 4-0590/2019 mod. 4-0678/2019; Ley 143/1994 | No citado | ⚠️ El manuscrito debe citar este marco si referencia "PPA tipo subasta" |

**Implicación**: el "PPA modelo" colombiano público (UPME CLPE) es
**Take-or-Pay financiero a 15 años**, mientras C2 modela
**Pay-as-Produced físico sin plazo**. Las dos estructuras son
extremos opuestos del espectro PPA. C2 elige PaP físico porque es la
forma más simple de modelar el reparto del excedente comunitario; el
T-o-P CFD requiere bolsa horaria como referencia y compensación
financiera (queda como CAL-13a/b según ADR-0011 anexo CAL-11b).

### 4.4 Capa 4 — residuo tarifario (CAL-12)

Esta es la única capa cubierta por la corrección estructural CAL-12:
qué componentes del CU sigue facturando el comercializador al
**usuario regulado** que hipotéticamente firmara un PPA.

| Norma | Mandato | C2 (post-CAL-12) | Estado |
|---|---|---|---|
| CREG 119/2007 arts. 6-8 | G es el único componente "negociable" via mercado | `savings_cons = E_PPA · (G − pi_ppa)` con G desde CSV CEDENAR | ✅ Implementado en CAL-12 |
| CREG 119/2007 arts. 9-14 | T+D+Cvm+PR+Rm+COT son cargos regulados trasladables | C2 ya no los "regala" a la comunidad | ✅ Implementado en CAL-12 |
| Liquidación déficit consumidor regulado | Va al CU minorista (no spot) | Línea 82: `grid_cost += residual × pi_gs` | ✅ |

## 5. Síntesis ejecutiva

| Escenario | Régimen | Estado de alineación |
|---|---|---|
| **C1** | CREG 174/2021 art. 25 — AGPE ≤ 100 kW | ✅ **Plenamente alineado** tras CAL-10b.2; sin brechas residuales |
| **C2** | Capa 1 (Ley 143/1994 + CREG 086/1996 + CREG 174/2021) | ❌ **Contrafáctico**: ningún PPA bilateral AGPE residencial-consumidor regulado existe legalmente |
| C2 | Capa 2 (CREG 156/2012, 024/1995) | ⚠️ Simplificación administrativa aceptable (sin ASIC) |
| C2 | Capa 3 (cláusulas tipo UPME CLPE) | ⚠️ C2 = PaP físico vs CLPE = T-o-P CFD; estructuras diferentes; CAL-13a/b pre-diseñados |
| C2 | Capa 4 (residuo tarifario CREG 119/2007) | ✅ **Corregido en CAL-12** (FoM, savings sobre G) |

**Conclusión global**: C1 está plenamente alineado regulatoriamente.
C2 está **técnicamente correcto** para representar un PPA bilateral
**Pay-as-Produced físico contrafáctico** entre AGPE residenciales
hipotéticamente habilitados a contratar entre sí. Su naturaleza
contrafáctica viene de la **capa 1** (la regulación no permite el
contrato), no de la capa 4 (donde CAL-12 ya lo corrigió). La
estructura PaP físico vs T-o-P CFD del modelo CLPE es una decisión
de diseño documentada en ADR-0011 anexo CAL-11b.

## 6. Recomendaciones

1. **C1 cerrado regulatoriamente**. No abrir CAL adicional.
2. **C2 cerrado bajo su naturaleza contrafáctica declarada**. Si el
   manuscrito (cap. 4 §C2) referencia "el PPA típico colombiano",
   debe citar:
   - **Marco habilitante**: Ley 143/1994 art. 41; CREG 086/1996
     art. 1 mod. 039/2001; CREG 174/2021 arts. 22-25
   - **Estructura contractual**: CREG 156/2012; CREG 024/1995
   - **Cláusulas estándar tipo subasta**: minuta UPME CLPE-02-2019;
     MME 4-0590/2019 mod. 4-0678/2019
   - **Residuo tarifario**: CREG 119/2007 arts. 6-14 (CAL-12)
3. **NO citar CREG 119/2007 como fundamento del PPA**. CREG 119/2007
   es la **fórmula tarifaria del usuario regulado**, no el marco del
   PPA. Citarla así fue el error metodológico que motivó esta
   revisión.
4. **TODO menor**: extender `analysis/sensitivity.run_sensitivity_ppa`
   a rango `[π_gb, G]` (coherencia CAL-12). No urgente.
5. **Si el asesor exige T-o-P o CFD**: abrir CAL-13a (T-o-P PaP) o
   CAL-13b (T-o-P bloque ajustable, eventualmente CFD) según
   pre-diseño en ADR-0011 anexo CAL-11b.

## 7. Referencias

[1] Congreso de la República, *Ley 143 de 1994*. https://www.upme.gov.co/wp-content/uploads/2025/02/Ley_143_1994.pdf

[2] CREG, *Resolución 086 de 1996* mod. *Resolución 039 de 2001*
(precio libre usuarios no regulados).

[3] CREG, *Resolución 156 de 2012* (registro ASIC contratos largo
plazo, CROM). https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_0156_2012.htm

[4] CREG, *Resolución 174 de 2021* (AGPE FNCER). https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_0174_2021.htm

[5] CREG, *Resolución 119 de 2007* (fórmula tarifaria CU usuario
regulado). https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_0119_2007.htm

[6] CREG, *Resolución 024 de 1995* (aspectos comerciales del MEM).

[7] MinMinas, *Resolución MME 4-0590 de 2019* mod. *4-0678 de 2019*
(subastas largo plazo CLPE).

[8] UPME, *Contrato de Suministro de Energía a Largo Plazo V. 2.3*
(CLPE-02-2019). https://www1.upme.gov.co/PromocionSector/Subastas-largo-plazo/Documents/Subasta-CLPE-02-2019/Minuta_Subasta_MME.pdf

[9] CREG, *Resolución 102 072 de 2025* (Comunidades Energéticas).

[10] Solsta, *¿Cómo se remunera a los GD y AGPE? — CREG 174*. https://solsta.co/remuneracion-gd-y-agpe-creg-174-33/

[11] Norton Rose Fulbright, *Bankability of Colombian projects*,
oct. 2019. https://www.projectfinance.law/publications/2019/october/bankability-of-colombian-projects/

[12] B. S. Lopez-Mendez, ADR-0008 a ADR-0012, repositorio interno
`docs/adr/`.

[13] B. S. Lopez-Mendez, *ADR-0013: Comunidad MTE como usuario
no-regulado agregado*, `docs/adr/0013-cal13-c2-no-regulado.md`.

[14] B. S. Lopez-Mendez, *ADR-0016: Descomposición regulatoria del
ahorro en C2*, `docs/adr/0016-cal16-c2-savings-decomposition.md`.

[15] Congreso de la República, *Ley 1715 de 2014* art. 19 (FAZNI).

[16] Congreso de la República, *Ley 1117 de 2006* art. 2 prorrogada
por *Ley 2099 de 2021* art. 45 (contribución 4 % al sector eléctrico).

[17] CREG, *Resolución 101-028 de 2023* (COT — Costo Operativo
Tributario del comercializador minorista).

---

## Anexo CAL-16 (2026-05-02) — Veredicto regulatorio actualizado

Tras CAL-13 se identificó que la formulación agregada
`savings = E_PPA · ((G + Cvm + COT) − π_ppa)` era una **cota
superior optimista**: mezclaba tres componentes con respaldo
regulatorio heterogéneo y omitía los costos administrativos del
usuario no-regulado en el MEM. CAL-16 (ADR-0016) refina la
formulación a cuatro términos regulatoriamente trazables:

$$
\mathrm{savings}^{C2} \;=\; E_{PPA} \,\Bigl[\,
  \underbrace{(G - \pi_{ppa})}_{\text{Ley 143/1994 art. 41}}
  \;+\; \underbrace{Cvm}_{\text{CREG 086/1996 + 156/2012}}
  \;+\; \underbrace{\alpha\,COT}_{\text{CREG 101-028/2023, } \alpha\in[0,1]}
  \;-\; \underbrace{\mathrm{MEM}}_{\text{Ley 1715/2014 + 1117/2006 + 156/2012}}
\,\Bigr]
$$

con $\mathrm{MEM} = \mathrm{FAZNI} + 0{,}04\,G + \pi_{rep}$.

### Veredicto regulatorio C2 — actualizado

| Criterio | Estado pre-CAL-16 (CAL-13) | Estado post-CAL-16 |
|---|---|---|
| Habilitación legal contratos bilaterales no-regulados | ✅ | ✅ |
| AGPE FNCER vende a precio libre | ✅ | ✅ |
| Descomposición CU CREG 119/2007 | ⚠️ agregada (`pi_G = G+Cvm+COT`) | ✅ explícita por componente |
| Cvm como ahorro del no-regulado | ✅ implícito | ✅ explícito (CREG 086/1996) |
| COT como ahorro del no-regulado | ⚠️ asumido al 100 % | ✅ parametrizado `α∈[0,1]` |
| Costos del usuario no-regulado en MEM | ❌ no modelados | ✅ modelados (FAZNI + 4 % + rep) |
| Reconciliación con factura CEDENAR | ⚠️ implícita | ✅ test explícito |
| Trazabilidad regulatoria por componente | ⚠️ mezclada | ✅ por norma |
| Teorema de invarianza en `π_ppa` | ✅ verificado | ✅ preservado |
| Cota económica racional para PPA | `pi_G = G+Cvm+COT` | `pi_upper = G+Cvm+α·COT−MEM` (más estricta) |

**Veredicto C2 post-CAL-16**: completamente alineado con la ley
colombiana, con descomposición regulatoria explícita y costos del
MEM modelados. La cota es **regulatoriamente exacta** (no
aproximada). El KPI agregado de C2 cae 5–15 % vs CAL-13 por el costo
MEM. Esto **refuerza la conclusión P2P > C2** del manuscrito (la
diferencia es aún mayor bajo CAL-16). Detalle: [14] y spec
`docs/superpowers/specs/2026-05-02-cal16-c2-savings-decomposition.md`.

### Veredicto regulatorio C1 — sin cambios

C1 (CREG 174/2021 art. 25 con permuta a `pi_gs − Cvm`, Tipo 1/Tipo 2,
componente C real desde CAL-10b) no se ve afectado por CAL-16.
Mantiene su alineación post-CAL-10b.
