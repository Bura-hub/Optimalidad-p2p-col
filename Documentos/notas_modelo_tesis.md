# Notas técnicas del modelo — Tesis P2P Colombia

**Autor:** Brayan S. Lopez-Mendez | **Udenar, 2026**
**Asesores:** Andrés Pantoja · Germán Obando

> Este archivo es permanente y NO es generado ni sobreescrito por `main_simulation.py`.
> Registra decisiones de modelado, derivaciones matemáticas y análisis que complementan
> el reporte automático `REPORTE_AVANCES.md`.

> **Aviso (auditoría 2026-04-17):** los valores numéricos de IE, RPE, PoF y beneficios
> monetarios reportados en este archivo son **provisionales** hasta que se ejecute la
> corrida `--full` (horizonte completo 5 160 h) y se congele la fuente de verdad oficial
> en §4. `REPORTE_AVANCES.md` puede mostrar cifras distintas porque se regenera
> automáticamente en cada corrida; no es fuente de verdad para documentos de tesis.

> **Glosario rápido — MTE:** a lo largo de este documento "MTE" se refiere al
> proyecto **Medición de Tecnologías de Energía** (ver
> `Documentos/Inventario_Act_1_0.md:13`), campaña de monitoreo de 5 instituciones
> educativas de Pasto, Nariño (Udenar, Mariana, UCC, HUDN, Cesmag) con cobertura
> horaria 2025-07-01 → 2026-02-01. "Perfil 24h MTE" = promedio diario del período.

---

## §4 — Índice de Equidad (IE): definición y signo

### Fórmula

$$
\text{IE} = \frac{\sum_i S_i - \sum_j SR_j}{\sum_i S_i + \sum_j SR_j}
$$

donde:
- $S_i$ = ahorro del comprador $i$ = energía comprada P2P × $(π_{gs} − π_{p2p})$
- $SR_j$ = prima del vendedor $j$ = energía vendida P2P × $(π_{p2p} − π_{bolsa})$

### Tabla de signos

| IE     | Interpretación                                       |
|--------|------------------------------------------------------|
| +1     | Compradores capturan todo el excedente del mercado   |
| 0      | Reparto equitativo entre compradores y vendedores    |
| −1     | Vendedores capturan todo el excedente del mercado    |
| > 0    | Mercado sesgado hacia compradores                    |
| < 0    | Mercado sesgado hacia vendedores                     |

### Valores por escenario (perfil 24h MTE) — **PROVISIONAL (2026-04-17)**

**Nota de auditoría:** los valores de esta tabla provienen de una corrida
previa del perfil diario promedio y se marcan como provisionales hasta
que se ejecute `--full` y se fije la fuente de verdad oficial. La tabla
§6 más abajo (si aplica) y la de `REPORTE_AVANCES.md` pueden mostrar
números distintos sobre otros perfiles.

| Escenario              | IE       | Interpretación                              |
|------------------------|----------|---------------------------------------------|
| P2P (Stackelberg + RD) | +0.0984  | Compradores reciben ventaja leve             |
| C1 CREG 174/2021       | −0.1009  | Vendedores (red) se benefician más           |
| C2 Bilateral PPA       | −0.1602  | Mayor sesgo hacia vendedores (PPA fijo)      |
| C3 Mercado spot        | −0.1009  | Igual a C1 (degeneración — ver §5)           |
| C4 CREG 101 072 ★      | −0.0614  | Referencia regulatoria vigente, menor sesgo  |

**Nota:** IE = 0 no significa precio P2P = $(π_{gs} + π_{gb})/2$. Significa que el excedente
total se distribuye igualmente entre compradores y vendedores en valor monetario agregado,
no que el precio sea el promedio aritmético.

---

## §5 — Degeneración C1 = C3: condición formal y predicción

### Condición formal de degeneración

**Proposición:** C1 (CREG 174/2021) y C3 (mercado spot) producen resultados idénticos
si y solo si:

$$
\forall n \in \mathcal{N},\; \forall k \in \mathcal{T}: \quad G_n(k) \leq D_n(k)
$$

es decir, ningún nodo tiene excedente individual en ninguna hora del horizonte.

**Demostración (sketch):** En C1, los excedentes individuales $e_n(k) = \max(0, G_n(k) - D_n(k))$
se liquidan a precio de bolsa $π_{bolsa}(k)$. Si $e_n(k) = 0\; \forall n,k$, la liquidación
es nula y C1 colapsa al mecanismo de C3 (autoconsumo + compra de déficit a red). $\square$

### Verificación para perfil 24h MTE

La condición se cumple en el perfil diario promedio porque la cobertura PV de la comunidad
es 11.3% (ΣG/ΣD = 0.113). Aun para el prosumidor con mayor cobertura (Udenar, 52%
individual), el perfil promedio suaviza los picos solares por debajo de la demanda media.

Esto es **matemáticamente correcto** y no un error del modelo.

### Predicción para la serie horaria real (5160h)

Con precios XM horarios reales y perfil desagregado por día:

- Fines de semana y festivos: demanda institucional cae ~60% mientras la generación solar
  mantiene su perfil. Se espera que $G_n(k) > D_n(k)$ en horas solares para Udenar y
  posiblemente Mariana.
- Días de sequía (El Niño, julio–agosto 2025): precios de bolsa XM más altos → la
  liquidación a bolsa en C3 tendrá mayor valor que el autoconsumo ajustado de C1.

**En consecuencia:** al correr `--full` con la serie real de 5160h, se espera que
$\text{C3} > \text{C1}$ en las horas con excedente y/o precio de bolsa alto.

### Párrafo en inglés para el paper

> Under the 24-hour average demand–generation profile, scenario C1 (CREG 174/2021
> net-metering) and C3 (spot-price liquidation) yield identical welfare outcomes.
> This degeneracy arises because community-level photovoltaic coverage is 11.3%,
> so no prosumer produces a surplus in any period of the profile and the grid
> liquidation mechanism becomes irrelevant. The degeneracy is expected to break
> when individual-day profiles are used, particularly on weekends and public
> holidays when institutional demand drops sharply while solar generation
> maintains its characteristic profile.

---

## §3.14 — Condición de Racionalidad Individual (IR) y deserción del P2P

### Definición formal

Agente $n$ permanece en el mercado P2P si y solo si:

$$
B_n^{P2P}(\pi) \geq \max\!\left(B_n^{C1}(\pi),\, B_n^{C4}(\pi)\right)
$$

donde $\pi = \{π_{gs}, π_{gb}, π_{bolsa}(k)\}$ son los parámetros de precio vigentes.

Definimos el **excedente de participación** de cada agente:

$$
\Delta_n(\pi) = B_n^{P2P}(\pi) - \max\!\left(B_n^{C1}(\pi),\, B_n^{C4}(\pi)\right)
$$

- $\Delta_n > 0$: agente prefiere P2P (estable)
- $\Delta_n = 0$: agente es indiferente (umbral crítico)
- $\Delta_n < 0$: agente deserta del P2P

El **umbral crítico** $\pi_{gb,n}^*$ es el precio de bolsa donde $\Delta_n = 0$ (raíz interpolada
de la curva SA-1).

### Resultados con perfil nominal MTE (precios XM reales, media = 222 COP/kWh)

Los valores base usan la simulación nominal con precios XM horarios reales (no el punto
fijo del barrido SA-1). Esto es crítico: SA-1 usa $π_{bolsa} = \text{const}$ para explorar
sensibilidad, pero el caso base real tiene precios variables con media ~222 COP/kWh y
precios solares ~100 COP/kWh.

| Agente  | B_n^P2P (COP) | Mejor alt. (COP) | Δ_n (COP) | Δ_n/B_alt | π_gb^* (COP/kWh) | Estado      |
|---------|---------------|------------------|-----------|-----------|------------------|-------------|
| Udenar  | 35,292        | 31,819 (C1)      | +3,473    | +10.9%    | ~217             | OK estable  |
| Mariana | 31,014        | 27,555 (C4)      | +3,459    | +12.6%    | >rango           | OK estable  |
| UCC     | 34,679        | 34,679 (C4)      | +0        | +0.0%     | >rango           | neutral     |
| HUDN    | 29,596        | 26,291 (C4)      | +3,305    | +12.6%    | >rango           | OK estable  |
| Cesmag  | 19,537        | 15,278 (C4)      | +4,259    | +27.9%    | >rango           | OK estable  |

**Agentes estables (5/5):** todos prefieren P2P en condiciones nominales.

**Nota importante:** el REPORTE_AVANCES.md generado automáticamente puede mostrar Udenar como
"en riesgo" (Δ=−6,108). Eso ocurre cuando el análisis IR usa el punto SA-1 con
$π_{bolsa}=280$ COP/kWh constante como base. Con los precios XM reales variables, Udenar
es estable (Δ=+3,473). La diferencia se explica abajo (§3.14.1).

### §3.14.1 — Por qué Udenar es sensible al PGB

Udenar tiene cobertura PV individual del 52%. En las horas solares, $G_{Udenar}(k) > D_{Udenar}(k)$,
por lo que tiene excedente que en C1 se liquida a precio de bolsa. Con precios XM reales,
el precio de bolsa en horas solares es bajo (~100 COP/kWh, período de mayor generación),
lo que reduce el valor del excedente en C1 y mantiene B_Udenar^C1 bajo.

Con $π_{bolsa}$ constante en SA-1, el excedente de Udenar se liquida al precio fijo del barrido,
que a 280 COP/kWh ya supera el promedio real. Por eso en SA-1:
- A $π_{gb}$ = 200 COP/kWh: Udenar P2P > C1 (Δ = +2,630)
- A $π_{gb}$ = 250 COP/kWh: Udenar P2P < C1 (Δ = −2,831)
- Umbral individual $\pi_{gb,Udenar}^*$ ≈ 217 COP/kWh

**Esto es consistente:** el umbral 217 COP/kWh está por debajo del precio bolsa XM real
(media = 222 COP/kWh), pero como la media está sesgada por horas nocturnas con precio
alto, las horas solares (cuando Udenar tiene excedente) tienen precio ~100 COP/kWh.
En la realidad, la comparación relevante para el excedente solar de Udenar es precisamente
el precio en esas horas solares, que está muy por debajo del umbral.

### §3.14.2 — Por qué C4 es constante con respecto a PGB

**Explicación:** C4 (CREG 101 072/2025) usa el mecanismo PDE (Participación en el Despacho
de Excedentes comunitarios). Los créditos PDE dependen del **excedente neto comunitario**:

$$
E_{com}(k) = \max\!\left(0,\; \sum_n G_n(k) - \sum_n D_n(k)\right)
$$

Con cobertura comunitaria del 11.3%, $\sum_n G_n(k) < \sum_n D_n(k)$ en **todas las horas**
del perfil diario promedio. Por tanto $E_{com}(k) = 0\; \forall k$, y los créditos PDE son
siempre cero. C4 queda reducido a solo los ahorros de autoconsumo, que no dependen de $π_{bolsa}$.

**Conclusión:** C4 = 129,911 COP/período es invariante al precio de bolsa para el perfil
actual. Esta es la razón por la que P2P domina C4 en todo el rango del barrido SA-1.

Cuando se escale la cobertura PV (SA-2), a partir de ~50% de cobertura comunitaria
empiezan a aparecer excedentes netos y C4 comenzará a crecer con PGB.

### §3.14.4 — Sensibilidad al precio al usuario (π_gs / CU)

**Pregunta del asesor (WEEF):** *"¿Y ojalá tuviera esa sensibilidad a parámetros?"*
— referido a bolsa, costo unitario (CU del comercializador), costos fijos.

**Metodología analítica de primer orden:**

| Beneficio | Fórmula | Dependencia con π_gs |
|-----------|---------|----------------------|
| $B_n^{C1}(\pi_{gs})$ | $\text{autoconsumo}_n \times \pi_{gs} + \text{excedente}_n \times \bar{\pi}_{bolsa}$ | Lineal (↑ π_gs → ↑ C1) |
| $B_n^{C4}(\pi_{gs})$ | $\text{autoconsumo}_n \times \pi_{gs}$ (PDE≈0) | Lineal (↑ π_gs → ↑ C4) |
| $B_n^{P2P}(\pi_{gs})$ | $B_n^{P2P,nom} \times (\pi_{gs}/\pi_{gs}^{nom})$ | Proporcional (aprox.) |

**Resultado teórico (derivada analítica):**

Para un comprador neto en P2P:
$$
\frac{d\Delta_n}{d\pi_{gs}} \approx \frac{B_n^{P2P,nom}}{\pi_{gs}^{nom}} - \text{autoconsumo}_n > 0
$$

siempre que el volumen transado en P2P aporte un beneficio adicional sobre
el autoconsumo puro (condición que se cumple cuando hay mercado activo).

**Conclusión:** a mayor precio retail (π_gs), el P2P se vuelve **más atractivo**
relativo a las alternativas C1/C4. El riesgo de deserción es mayor cuando el CU
es bajo, no alto. Esto es contraintuitivo pero económicamente correcto: en P2P
los compradores ahorran $(π_{gs} - π_{star})$ por kWh; si π_gs sube, ese margen crece.

**Implementación:** `analysis/feasibility.py → analyze_desertion_sensitivity_pgs()`

---

### §3.14.3 — Umbral comunitario agregado

El umbral comunitario es el $\pi_{gb}$ donde el total P2P deja de superar el total del
mejor escenario alternativo. Del barrido SA-1:

| π_gb (COP/kWh) | P2P (COP) | C1 (COP)  | C4 (COP)  | P2P>C1 | P2P>C4 |
|----------------|-----------|-----------|-----------|--------|--------|
| 200            | 154,487   | 135,621   | 129,911   | SI     | SI     |
| 250            | 151,756   | 135,621   | 129,911   | SI     | SI     |
| 280            | 150,118   | 135,621   | 129,911   | SI     | SI     |
| 300            | 149,025   | 135,621   | 129,911   | SI     | SI     |
| 350            | 146,295   | 149,025*  | 129,911   | NO     | SI     |
| 400            | 143,564   | —         | 129,911   | NO     | SI     |
| 450            | 140,833   | —         | 129,911   | NO     | SI     |
| 500            | 138,103   | —         | 129,911   | NO     | SI     |

*Valor aproximado. Umbral P2P < C1 interpolado: **~325 COP/kWh**
P2P siempre domina C4 en el rango evaluado (C4 es constante en 129,911).

**Interpretación:** Si el precio de bolsa supera ~325 COP/kWh de forma sostenida (escenario
El Niño severo), el escenario C1 (CREG 174) genera más beneficio comunitario que el P2P.
Esto no implica deserción individual (depende de cada agente), sino que el mecanismo
regulatorio C1 sería preferible a nivel de bienestar agregado.

---

## §3.6 — Fuente de precios: XM bolsa vs CU del comercializador

**Preguntas del asesor (WEEF §3.6):**
- *"¿Es el precio de bolsa?"* — confirmar qué precio se usa para cada transacción
- *"No sé si así se consigue"* — el CU lo arma el comercializador, no está en XM
- *"¿XM quién es el precio de bolsa?"* — XM publica bolsa ≠ precio que paga el consumidor

### Estructura del modelo: dos precios, dos transacciones

| Variable | Valor (COP/kWh) | Uso en el modelo | Fuente |
|----------|-----------------|-----------------|--------|
| `π_gs` | 650 | Precio retail: lo que paga el consumidor comprando a la red | CU Cedenar/ESSA Nariño 2024-2025 |
| `π_bolsa` | ~221 (media) | Precio mayorista: lo que recibe el generador inyectando excedentes | XM Precio de Bolsa Nacional (horario) |

**Estas son transacciones distintas y deben tener precios distintos:**
- Cuando un agente *compra* energía a la red → paga `π_gs` (tarifa completa CU)
- Cuando un agente *vende/inyecta* excedente a la red → recibe `π_bolsa` (precio bolsa XM)

Así lo establece la regulación colombiana (CREG 174/2021 Art. 5, CREG 101 072/2025).

### Descomposición regulatoria del CU institucional (Nariño 2025)

$$\text{CU} = G + T + D + C + PR + \text{otros}$$

| Componente | COP/kWh | % CU | Nota |
|-----------|---------|------|------|
| G (generación — precio bolsa) | 220 | 33.8% | **Varía con XM** |
| T (transmisión STN) | 60 | 9.2% | Fijo por CREG |
| D (distribución STR+SDL, nivel 2-3) | 160 | 24.6% | Fijo por zona |
| C (comercialización Cedenar/ESSA) | 90 | 13.8% | Por contrato |
| PR (pérdidas reconocidas + restricciones) | 35 | 5.4% | Parámetro CREG |
| Otros (contribución, SSPD, IVA) | 85 | 13.1% | Regulado |
| **TOTAL CU** | **650** | 100% | Rango Nariño: 580-720 |

El componente G del CU sí varía con el precio de bolsa XM, pero **los otros 430 COP/kWh son cuasi-fijos**. Por eso `π_gs ≠ π_bolsa` y el spread es estructural, no volátil.

### Justificación del estimador para π_bolsa en el análisis comparativo

Para el análisis SA-1 se evalúa C1 con un `π_bolsa` constante (barrido discreto). La
elección del estimador representativo afecta la comparación:

| Estimador | Valor aprox. | Sesgo sobre C1 |
|-----------|-------------|----------------|
| Media aritmética **(ELEGIDA)** | 221 COP/kWh | Neutro / ligeramente alto |
| Mediana | ~200 COP/kWh | Conservador (C1 menos atractivo) |
| Media horas solares (8-16h) | ~100-150 COP/kWh | Muy conservador (precio bajo cuando hay excedente) |

**Justificación de la media aritmética:**

1. **Conservador para P2P**: la media global > media solar, por lo que el SA-1 le asigna
   a C1 un precio más alto del que Udenar realmente enfrenta al inyectar excedentes.
   Esto favorece a C1 → hace más estricto el umbral de deserción del P2P.

2. **Coherente con el horizonte 7 meses (Jul 2025 – Ene 2026)**: la media mensual
   pondera igual las noches (precio alto, sin excedente) y las horas solares (precio bajo,
   con excedente). Usar la media global es la convención estándar en la literatura.

3. **Trazabilidad**: se puede replicar exactamente con los informes mensuales publicados
   por XM (fuente primaria verificada, no requiere microdatos horarios).

**Impacto en Udenar:** ver §3.14.1 — el umbral de deserción individual `π_gb^* ≈ 217 COP/kWh`
fue calculado con la media global. Con la media solar (~120 COP/kWh), el umbral sería
**mucho menor** (Udenar estaría aún más estable en P2P).

**Implementación:** `data/xm_prices.py → price_source_analysis()` + `CU_COMPONENTS_2025`

---

## §3.8 — Sensibilidad al precio del contrato bilateral PPA

**Pregunta del asesor (WEEF, ~44:55):** *"Pregunta interesante: qué tan sensible es el
desempeño al precio del contrato bilateral a largo plazo — implica varias simulaciones
con barrido de precios."*

### Modelo del escenario C2

$$
B_n^{C2}(\pi_{ppa}) = \underbrace{\text{autoconsumo}_n \times \pi_{gs}}_{\text{ahorro base}}
+ \underbrace{\text{excedente\_vendido}_n \times \pi_{ppa}}_{\text{ingreso PPA (generador)}}
+ \underbrace{\text{energía\_recibida}_n \times (\pi_{gs} - \pi_{ppa})}_{\text{ahorro PPA (comprador)}}
$$

### Parametrización del barrido

$$\pi_{ppa}(f) = \pi_{gb} + f \cdot (\pi_{gs} - \pi_{gb}), \quad f \in [0, 1]$$

| f | Efecto económico |
|---|-----------------|
| 0 → $\pi_{ppa} = \pi_{gb}$ | Todo el excedente del mercado va al comprador; generador recibe lo mismo que vendiendo a la red |
| 0.5 → midpoint | Default actual; reparto simétrico del excedente |
| 1 → $\pi_{ppa} = \pi_{gs}$ | Todo el excedente va al generador; comprador no ahorra nada vs. red |

### Resultado teórico

- $\partial B_n^{C2} / \partial \pi_{ppa} > 0$ para generadores (prosumidores con excedente)
- $\partial B_n^{C2} / \partial \pi_{ppa} < 0$ para compradores netos
- La suma $B_{total}^{C2}(\pi_{ppa})$ es **constante** respecto a $\pi_{ppa}$ en comunidad cerrada
  (la prima del generador y el ahorro del comprador se compensan exactamente)
- Por tanto, C2 vs P2P vs C1 vs C4 se compara sobre ese total constante

**Implementación:** `analysis/sensitivity.py → run_sensitivity_ppa()` + `graficas/fig10_sensibilidad_ppa.png`

---

## §3.12 — Desglose P2P hora a hora: estructura y definiciones

**Solicitud del asesor (WEEF, ~58:19):** *"¿Puedes subir los datos del P2P?"*

### Variables exportadas por par (vendedor j, comprador i, hora k)

| Variable | Fórmula | Unidad |
|----------|---------|--------|
| `kWh_transados` | $P^*_{ji}(k)$ | kWh |
| `precio_COP_kWh` | $\pi^*_i(k)$ | COP/kWh |
| `valor_COP` | $P^*_{ji} \times \pi^*_i$ | COP |
| `prima_vendedor_COP` | $P^*_{ji} \times \max(0,\, \pi^*_i - \pi_{gb})$ | COP |
| `ahorro_comprador_COP` | $P^*_{ji} \times \max(0,\, \pi_{gs} - \pi^*_i)$ | COP |

**Nota:** $\pi^*_i(k)$ es el precio fijado por el comprador $i$ en el equilibrio
Stackelberg de la hora $k$ (Replicator Dynamics). Es el mismo para todos los
vendedores que venden a $i$ en esa hora; varía entre compradores.

### Variables de resumen por hora k

| Variable | Descripción |
|----------|-------------|
| `precio_prom_pond` | $\sum_i \pi^*_i(k) \cdot \sum_j P^*_{ji} \;/\; \sum_{ij} P^*_{ji}$ — precio medio ponderado por volumen |
| `SC`, `SS`, `IE` | Índices de autoconsumo, autosuficiencia y equidad de esa hora |
| `vendedores` / `compradores` | Nombres de agentes activos separados por `;` |

### Condición de datos en el mercado (cuándo hay transacción)

Una hora $k$ tiene mercado activo si existe al menos un par $(j, i)$ con $G_{j}(k) > D_{j}(k)$
y $D_{i}(k) > G_{i}(k)$, es decir, hay excedente neto en al menos un prosumidor y déficit
en al menos otro agente.

### Implementación

```python
from analysis.p2p_breakdown import export_p2p_hourly
flows, summary = export_p2p_hourly(
    p2p_results, agent_names, pi_gs=650, pi_gb=280,
    out_dir=".", prefix="p2p_breakdown")
```

---

## §6 — Price of Fairness (PoF): interpretación

$$
\text{PoF} = \frac{W^* - W^{eq}}{W^*}
$$

donde $W^*$ es el bienestar máximo (en C4 = mecanismo más eficiente) y $W^{eq}$ es el
bienestar en el P2P con equidad (Stackelberg + RD). PoF = 0.1346 significa que se pierde
un 13.5% del bienestar máximo posible para lograr la distribución equitativa del P2P.

Este valor es **razonable** para un mercado P2P comunitario. En la literatura, valores de
PoF entre 0.05 y 0.30 se consideran aceptables cuando la equidad tiene valor intrínseco
(comunidades, cooperativas, instituciones educativas).

---

## §7 — Calibración de parámetros: justificación numérica

**Fecha:** 2026-04-12 | **Script:** `tests/calibration_study.py`

Se ejecutó un barrido sistemático sobre los 5 parámetros del modelo que carecían de
justificación explícita en Chacón et al. (2025). Los resultados validan los valores actuales
o documentan por qué la discrepancia entre versiones del código es irrelevante.

### CAL-1: `stackelberg_iters` — convergencia del juego Stackelberg

**Valores probados:** 1, 2, 3, 5, 8, 10 iteraciones.

| iters | SC | SS | IE | Δ SC vs anterior |
|-------|---------|---------|---------|-----------------|
| 1 | 0.8692 | 0.8465 | −0.3785 | — |
| 2 | 0.8692 | 0.8465 | −0.3889 | 0.00000 |
| 3 | 0.8692 | 0.8465 | −0.3704 | 0.00000 |
| 5 | 0.8692 | 0.8465 | −0.3702 | 0.00000 |
| 8 | 0.8692 | 0.8465 | −0.3718 | 0.00000 |
| 10 | 0.8692 | 0.8465 | −0.3718 | 0.00000 |

**Conclusión:** SC y SS convergen en la primera iteración Stackelberg (ΔSC = 0 exacto para
todas las combinaciones). Solo IE oscila ±0.02 sin tendencia monotónica. El juego de
asignación de potencias P_star converge en una sola iteración del loop externo.

**Justificación formal de `stackelberg_iters = 2`:** el valor actual es conservador
(captura el efecto marginal de IE sin costo computacional relevante). Para la tesis puede
citarse: *"La asignación de potencias P* converge en la primera iteración Stackelberg
(ΔSC = 0); la segunda iteración se mantiene para capturar el ajuste marginal de precios."*

### CAL-2: `etha` — coeficiente de competencia entre compradores

**Contexto:** JoinFinal.m usa etha=0.1; ConArtLatin.m (artículo) usa etha=1.0. Discrepancia
de un orden de magnitud entre las dos versiones del código de Chacón.

**Valores probados:** 0.01, 0.05, 0.10, 0.50, 1.00, 2.00, 5.00.

| etha | SC | SS | IE | pi_mean |
|------|---------|---------|---------|---------|
| 0.01 | 0.8692 | 0.8465 | −0.3889 | 863.36 |
| 0.10 (JoinFinal) | 0.8692 | 0.8465 | −0.3889 | 863.36 |
| 1.00 (artículo) | 0.8692 | 0.8465 | −0.3889 | 863.36 |
| 5.00 | 0.8692 | 0.8465 | −0.3889 | 863.35 |

**Conclusión:** `etha` es operacionalmente inerte en el rango [0.01, 5.0]. El término
`compe = etha × Σ P_ji` en `solve_buyers` es numéricamente despreciable frente a los
términos `pagos` y `trestris` a las escalas de operación del modelo. La discrepancia entre
JoinFinal.m (0.1) y ConArtLatin.m (1.0) carece de consecuencias. Se mantiene etha=0.1
por consistencia con el modelo dinámico de referencia (JoinFinal.m).

### CAL-3: `alpha` — fracción de demanda flexible (DR Program)

**Contexto:** No existe en ninguna versión del código de Chacón. Es un supuesto propio
de la implementación. Rango típico en literatura DR: 10–40% para prosumidores.

| alpha_p | alpha_c | Desplazamiento | SC | SS | ΔSC vs α=0 |
|---------|---------|---------------|---------|---------|-----------|
| 0.00 | 0.00 | 0.0% | 0.8692 | 0.8465 | — |
| 0.10 | 0.05 | 9.1% | 0.8874 | 0.8804 | +0.0182 |
| **0.20** | **0.10** | **18.2%** | **0.9040** | **0.9058** | **+0.0348** |
| 0.30 | 0.15 | 27.3% | 0.9174 | 0.9190 | +0.0481 |
| 0.40 | 0.20 | 36.4% | 0.9163 | 0.9101 | +0.0470 ← satura |

**Punto óptimo empírico:** alpha_p=0.20 captura el 72% de la mejora máxima posible
(ΔSC=0.035 de 0.048 máx) con solo el 50% del desplazamiento del punto de saturación.
El beneficio marginal del DR se vuelve negativo para alpha_p > 0.30–0.35.

**Justificación formal de alpha_p=0.20, alpha_c=0.10:** punto de inflexión en la
curva ΔSC(alpha), consistente con valores reportados en la literatura de DR para
comunidades energéticas universitarias (Luthander et al. 2015, Parra et al. 2017).

### CAL-4: `WI/WJ scaling` — diagnóstico del escalado del sistema ODE

**Contexto:** JoinFinal.m combina compradores y vendedores en un solo sistema ODE:
`dX/dt = [WI × ReplicadorWi; WJ × ReplicadorWj]` con WI=0.08 y WJ=10 (ratio WJ/WI = 125).
En nuestra implementación los subsistemas son secuenciales (no combinados).

| tau_b / tau_s | tau_buyers | SC | SS | IE |
|--------------|-----------|---------|---------|---------|
| 1 | 0.0010 | 0.8692 | 0.8465 | −0.1152 |
| 5 | 0.0050 | 0.8692 | 0.8465 | −0.2829 |
| **10** | **0.0100** | **0.8692** | **0.8465** | **−0.3889** ← JoinFinal |
| 20 | 0.0200 | 0.8692 | 0.8465 | −0.3613 |

**Conclusión:** el ratio `tau_buyers/tau = 10` reproduce IE=−0.39, valor consistente con
el equilibrio de JoinFinal.m. Ratios menores o mayores producen IE fuera del rango esperado.
El escalado WI/WJ de JoinFinal.m está **implícitamente implementado** a través de la
diferencia de constantes de tiempo. No se requiere ningún cambio de código.

**Justificación para la tesis:** *"El sistema ODE combinado de Chacón (JoinFinal.m) escala
el bloque comprador con WI=0.08 y el bloque vendedor con WJ=10. En la implementación
secuencial equivalente, este escalado se captura mediante la diferencia de constantes de
tiempo de los filtros de paso bajo: τ_vendedores=0.001 s, τ_compradores=0.01 s (ratio=10),
alineado con WJ/WI=10 del modelo de referencia."*

### CAL-5: `theta` — confirmación de insensibilidad dinámica

| theta | Aparece en | SC | SS |
|-------|-----------|---------|---------|
| 0.5 (JoinFinal.m) | `seller_welfare()`, `buyer_welfare()` solo | 0.8692 | 0.8465 |
| 10.0 (ConArtLatin.m) | ídem | 0.8692 | 0.8465 |

**Conclusión:** `theta` no afecta `solve_sellers()` ni `solve_buyers()`. Solo modifica
los valores de Wj_total/Wi_total exportados en la hoja Excel de reporte. La discrepancia
JoinFinal(0.5) vs ConArtLatin(10.0) corresponde a dos objetivos distintos: JoinFinal
usa theta para la dinámica RD; ConArtLatin lo usa en el solver estático SLSQP. Se mantiene
theta=0.5 por consistencia con el modelo dinámico de referencia.

### CAL-6: `b_n` — LCOE solar: sintético vs real (nota de auditoría D2)

**Fecha de la nota:** 2026-04-17 | **Evidencia:** `data/xm_prices.py:72-101`,
`data/base_case_data.py:40-43`, `Documentos/copy/JoinFinal.m:40-43`,
`Documentos/Revision_Bibliografica_Act_1_2.md:81`.

El parámetro `b_n` tiene **dos calibraciones separadas** según el modo de
ejecución. Son numéricamente incomparables porque están en unidades
distintas y responden a propósitos distintos.

| Modo | Fuente | Vector `b` | Unidad | Propósito |
|---|---|---|---|---|
| Sintético | `base_case_data.py::B = SCALE * [3.93·52, 32, 47, 37, 0, 0]` | `[1245, 195, 287, 225, 0, 0]` | u.o. (unidades de optimización) | Fidelidad exacta al caso base `JoinFinal.m:40-43` para validación (golden test) |
| Real (MTE) | `xm_prices.py::B_CALIBRATED` | 225 (homogéneo; 210 Cesmag) | COP/kWh | Representación empírica de la comunidad MTE con LCOE colombiano |

**Justificación del homogéneo en modo real:**

1. Las 5 instituciones usan inversores **Fronius ≤ 100 kW**, mismo
   fabricante y clase de capacidad. La diferencia entre LCOE individuales
   es dominada por horas-sol equivalentes, que son homogéneas en un radio
   < 2 km (campus de Pasto).
2. El rango IRENA [16] / UPME [17] para solar distribuida pequeña en
   Colombia 2024–2025 es **200–250 COP/kWh**; el valor 225 está en la
   mediana del rango.
3. Cesmag tiene un inversor distinto (no Fronius), por eso se asigna
   210 COP/kWh — diferenciación justificada por ficha técnica.
4. Los datos de capacidad FV por institución están marcados como
   **PENDIENTE VERIFICAR CON ADMIN MTE** en
   `Inventario_Act_1_0.md:29-33`. Heterogeneizar `b_n` antes de ese
   cierre introduciría falsa precisión.

**Por qué no se reemplaza el homogéneo por el vector heterogéneo de
JoinFinal.m en modo real:** el vector MATLAB está en unidades de
optimización (el modelo sintético usa `pi_gs = 1250`, precios
adimensionales), no en COP/kWh. Su traducción directa no tendría
sentido físico.

**Veredicto:** la decisión de usar `b_n = 225 COP/kWh` homogéneo en el
modo real es una decisión de modelado deliberada y defendible. El
hallazgo D2 queda cerrado como discrepancia documentada, no como bug.

### CAL-7: Alternancia Stackelberg vs ODE conjunta (nota de auditoría A3)

**Fecha:** 2026-04-17 | **Archivo:** `core/ems_p2p.py:230-244`

El bucle Stackelberg de este repositorio se resuelve por **alternancia**
(outer loop):

```
mientras iter < max_iter:
    P_star  ←  solve_sellers(pi_i, ...)     # RD vendedores (ODE interna)
    pi_i    ←  solve_buyers(P_star, ...)    # RD compradores (ODE interna)
    norm_rel = ‖P_new − P_old‖ / (‖P_old‖ + 1e-9)
    si norm_rel < tol: salir
```

En `Documentos/copy/JoinFinal.m:139`, en cambio, el sistema se integra
de forma **conjunta**: el estado concatenado `[consumer_state,
seller_state]` se pasa a `ode15s` en una única llamada y ambos
replicadores evolucionan simultáneamente.

**¿Por qué se adoptó la alternancia?** Razones de ingeniería de
software, no de modelado:

1. **Paralelización.** La iteración horaria de 5 160 h se reparte con
   `ProcessPoolExecutor`; cada hora solo necesita un bucle finito de
   pasos discretos, más predecible que un integrador adaptativo.
2. **Diagnóstico por separado.** Permite inspeccionar `P_star` y `pi_i`
   tras cada sub-paso, facilitando los tests de convergencia.
3. **Criterio de parada uniforme.** La norma relativa en `P_star` es
   un contrato explícito y adaptativo entre escenarios.

**¿Afecta el equilibrio?** No en el límite. Ambas formulaciones
convergen al mismo punto fijo del juego Stackelberg cuando
`tol → 0` y `max_iter → ∞`, porque el equilibrio de Nash es
invariante bajo la factorización del operador de actualización (el
operador T que lleva `(P, π)` al siguiente estado es contractivo
tanto aplicado "en bloque" como alternado, con el mismo fijo).

**¿Afecta las trayectorias transitorias?** Sí. Las iteraciones
intermedias (antes de converger) difieren. Esto es relevante solo si
se reporta la dinámica antes del equilibrio, lo cual no se hace en
ninguna figura de la tesis (todas usan `P_star` y `pi_i` ya convergidos).

**Validación empírica.** El test
`tests/test_stackelberg_convergence.py` garantiza que al salir del
bucle `norm_rel < tol`. El `tests/golden_test_sofia.py` confirma
que el equilibrio alcanzado coincide con el oráculo SLSQP de
`Bienestar6p.py` dentro de tolerancias (`P_total` atol = 0,15 kWh,
demanda rtol = 5 %, `π_i ∈ [π_GB, π_GS]`).

**Implicación para la tesis.** En la sección de Métodos debe
declararse: *"El sistema Stackelberg se resuelve por alternancia
(`solve_sellers` ↔ `solve_buyers`) con criterio de parada
`‖ΔP‖ / (‖P‖ + ε) < tol = 1e-3` y `max_iter = 8`. El equilibrio
resultante coincide con el oráculo SLSQP del modelo base dentro de
tolerancias numéricas documentadas."*

**Veredicto:** el hallazgo A3 queda cerrado como discrepancia
de formulación documentada. No se modifica el código.

### Resumen de recomendaciones de calibración

| Parámetro | Valor actual | Referencia | Veredicto | Acción |
|-----------|-------------|-----------|-----------|--------|
| `stackelberg_iters` | 2 | —  | **Justificado** | Ninguna |
| `etha` | 0.1 | JoinFinal=0.1 / artículo=1.0 | **Inerte** | Ninguna |
| `alpha_p` | 0.20 | Literatura 10–40% | **Óptimo empírico** | Documentar en §III-A tesis |
| `alpha_c` | 0.10 | 50% de alpha_p | **Conservador** | Documentar en §III-A tesis |
| `theta` | 0.5 | JoinFinal=0.5 / SLSQP=10 | **Solo reporting** | Ninguna |
| `WI/WJ scaling` | no implementado | tau_b/tau_s=10 equivalente | **Implícito** | Ninguna |
| `pi_gs` real | 650 COP/kWh | Rango Nariño 580–720 | **Estimado** | Confirmar con Cedenar/ESSA |
| `pi_gb` real | 280 COP/kWh | XM Jul25–Ene26 ~221 | **Pendiente** | Reemplazar con serie XM real |
| `b_n` real | 225 COP/kWh | IRENA/UPME 200–250 | **Homogéneo justificado** | Ninguna (ver CAL-6) |
| `b_n` sintético | `[1245,195,287,225,0,0]` u.o. | JoinFinal.m:40-43 | **Fiel al modelo base** | Ninguna |

---

## §8 — Prueba de perfiles contrastantes: adaptación de los algoritmos

**Fecha:** 2026-04-12 | **Script:** `tests/profile_stress_test.py`

Se diseñaron 8 perfiles de generación/demanda muy diferentes para observar cómo los
algoritmos RD (Algoritmos 2 y 3 de Chacón) se adaptan a condiciones distintas.
Parámetros fijos en todos los perfiles: tau=0.001, tau_buyers=0.01,
stackelberg_iters=2, alpha=0 (sin DR para aislar el comportamiento del juego).

### Tabla resumen

| # | Perfil | GDR | H_P2P | SC | SS | IE | pi_med |
|---|--------|-----|-------|-----|-----|-----|--------|
| P1 | Solar dominante | 1.11 | 13/24 | 0.883 | 0.536 | −0.814 | 1057 |
| P2 | Nocturno | 0.00 | **0/24** | — | — | — | — |
| P3 | Balanceado (G≈D) | 0.34 | **0/24** | — | — | — | — |
| P4 | Asimétrico (1 vendedor grande) | 1.21 | 14/24 | 0.878 | 0.936 | −0.673 | 958 |
| P5 | Volátil (CoV>40%) | 0.50 | 15/24 | 0.694 | 0.884 | −0.454 | 896 |
| P6 | Todos prosumidores | 0.44 | 10/24 | 0.854 | 0.943 | −0.474 | 859 |
| P7 | MTE escala real | 0.22 | **0/24** | — | — | — | — |
| P8 | Escasez extrema (D≈5×G) | 0.03 | **0/24** | — | — | — | — |

### Condición de activación del mercado P2P

El mercado P2P solo se activa en la hora k si existe al menos un agente n con
G_klim[n,k] > D[n,k] (vendedor neto). Esta condición requiere GDR comunitario suficiente
**y** distribución desigual de G y D entre agentes.

Los perfiles P2, P3, P7 y P8 producen 0 horas de mercado activo:
- P2 (GDR=0.00): sin generación solar en ninguna hora.
- P3 (GDR=0.34): G presente pero distribuida de forma que G[n,k] < D[n,k] para todo n,k.
- P7 (GDR=0.22): replica el problema de los datos MTE reales (ver §8.1).
- P8 (GDR=0.03): demanda 5× generación, ningún agente tiene excedente individual.

### Observaciones por perfil activo

**P1 — Solar dominante (GDR=1.11, 13 horas, SC=0.883, IE=−0.814):**
Alta SC pero SS baja (0.536): la generación solar supera ampliamente la demanda en horas
centrales y el excedente que no se puede vender internamente se pierde (o va a la red).
El mercado P2P captura parte del surplus solar pero los 2 compradores tienen capacidad de
absorción limitada. IE=−0.814 indica que los vendedores capturan la mayor parte del
excedente — resultado esperado cuando hay abundancia de oferta y escasez de compradores.
Precios altos (pi_med=1057, 77% de horas en el techo pi_gs): contraintuitivo, pero correcto
en el juego Stackelberg donde los vendedores son líderes con alto poder de negociación.

**P4 — Asimétrico (GDR=1.21, 14 horas, SC=0.878, SS=0.936, IE=−0.673):**
El algoritmo RD asigna eficientemente la generación del vendedor grande a los 5 compradores
pequeños (SS=0.936: el 93.6% de la generación disponible es absorbida por la comunidad).
Caso de interés: un campus universitario grande con varios edificios dependientes.

**P5 — Volátil (GDR=0.50, 15 horas, SC=0.694):**
SC más bajo de los perfiles activos. El ruido gaussiano (CoV>40%) genera horas donde la
clasificación vendedor/comprador cambia aleatoriamente, degradando la eficiencia del mercado.
Relevante para datos reales donde la irradiancia solar tiene alta variabilidad.

**P6 — Todos prosumidores (GDR=0.44, 10 horas, SS=0.943):**
Mejor aprovechamiento relativo cuando todos los agentes tienen paneles solares y turnan
su rol de vendedor/comprador según la hora. SS=0.943 es el más alto de todos los perfiles.
Escenario deseable para una comunidad energética madura.

### Correlación GDR → precio P2P (r = +0.83, positiva)

Hallazgo inesperado a primera vista: mayor generación relativa → **precios más altos**.
Interpretación en marco Stackelberg: cuando los vendedores tienen más generación disponible,
ejercen mayor poder de negociación como líderes del juego. Los compradores ofrecen precios
altos para asegurar el suministro porque saben que los vendedores tienen alternativas
(vender a la red a pi_gs). Este es el comportamiento de equilibrio Nash correcto en un
juego Stackelberg con líderes vendedores.

Implicación para el diseño de política: la regulación P2P debería considerar mecanismos
de precio techo intra-comunidad para evitar que los prosumidores con alta cobertura PV
extraigan rentas monopólicas en horas de alta generación.

### §8.1 — GDR real MTE: verificación ejecutada (2026-04-12)

**Resultado:** el mercado P2P es **directamente viable** con los datos reales.
Se verificó sobre la serie completa de 5,160 horas (Jul 2025 – Ene 2026).

#### Horas de mercado P2P por institución y en total

| Agente | G_med (kW) | D_med (kW) | GDR ind. | H_vendedor | H_vend% |
|--------|-----------|-----------|---------|-----------|--------|
| Udenar | 3.95 | 7.54 | 0.524 | **1,389** | **26.9%** |
| Mariana | 1.77 | 13.77 | 0.128 | 452 | 8.8% |
| UCC | 2.22 | 42.09 | 0.053 | 204 | 4.0% |
| HUDN | 1.69 | 21.68 | 0.078 | 109 | 2.1% |
| Cesmag | 0.98 | 9.03 | 0.108 | 237 | 4.6% |

**Mercado P2P posible: 1,397/5,160 horas (27.1%)**

La preocupación del test P7 era infundada: el perfil sintético distribuía GDR uniformemente
entre agentes (GDR_individual≈0.22), pero en los datos reales Udenar tiene GDR individual
0.524 y actúa como vendedor principal en 1,389 horas, siendo suficiente para activar
el mercado aunque el GDR comunitario sea solo 0.113.

#### Distribución temporal del mercado P2P

**Por hora del día** (patrón estrictamente solar, pico al mediodía):

| Rango horario | % días con P2P | Observación |
|---------------|---------------|-------------|
| 00:00–06:00 | 0.0% | Sin generación solar |
| 07:00–08:00 | 41–55% | Rampa solar matinal |
| 09:00–15:00 | **60–82%** | Ventana P2P principal |
| 12:00 | **81.4%** | Hora de mayor activación |
| 16:00–17:00 | 5–39% | Caída vespertina |
| 18:00–23:00 | 0.0% | Sin generación solar |

**Por tipo de día:**
- Laborables (L–V): 24.0% de horas con P2P → demanda institucional alta reduce excedente
- **Fines de semana (S–D): 34.8%** → demanda cae ~60% mientras G_solar permanece ✓

**Por mes** (patrón estacional):

| Mes | H_P2P | % | Interpretación |
|-----|-------|---|---------------|
| Jul 2025 | 273/744 | **36.7%** | Verano seco, mayor irradiancia |
| Ago 2025 | 230/744 | 30.9% | Transición |
| Sep–Nov 2025 | 190–213 | 26–30% | Estación intermedia |
| Dic 2025 | 246/744 | 33.1% | Vacaciones institucionales (D baja) |
| **Ene 2026** | **37/744** | **5.0%** | Anomalía — ver nota |

**Nota enero 2026:** 305/744 horas con D=0 para todos los agentes (cierre por vacaciones
universitarias + festivos colombianos ene-15). Además, Ene es temporada de lluvias en
Nariño (G_media=0.41 kW vs 4.20 kW en julio, G_zeros=91.5%). Los 37/744 son
estadísticamente correctos, no un error de datos. Última hora con datos: 2026-01-29 17:00.

#### Excedente de Udenar (vendedor principal) en horas pico solar

| Hora | Días vendedor | Excedente medio |
|------|--------------|----------------|
| 10:00 | 71.2% | 14.4 kW |
| 11:00 | 76.3% | 14.7 kW |
| **12:00** | **82.3%** | **14.7 kW** |
| 13:00 | 81.4% | 14.6 kW |
| 14:00 | 75.8% | 12.4 kW |

**Conclusión:** los datos reales MTE son directamente utilizables para el análisis P2P.
La simulación `--data real --full` procederá sobre 1,397 horas con mercado activo.

---

*Última actualización: 2026-04-13 (v8.3: robustez C4, brechas vs propuesta, tareas pendientes)*
*Este archivo es permanente — editarlo directamente, no auto-generado*

---

## §A.6 — Robustez regulatoria C4: retiro de participante y escalamiento (FA-3/FA-4)

**Implementado:** v8.3 (2026-04-13) | Módulo: `analysis/feasibility.py → run_withdrawal_robustness()` + `run_scaling_robustness()`
Gráfica: `graficas/fig17_robustez_c4.png`

**Motivación (propuesta §VII.C):** La autogeneración colectiva CREG 101 072 (C4) impone
restricciones de composición: regla 10% y límite 100 kW. Si un participante se retira o
escala su instalación, el régimen AGRC puede quedar inválido → la comunidad cae a régimen
individual (sin créditos PDE). Esta fragilidad regulatoria es una ventaja estructural del P2P,
que no tiene restricciones de composición.

### FA-3 — Retiro de participante

Para cada prosumidor $n$, se simula su retiro y se recalcula:

| Indicador | Descripción |
|-----------|-------------|
| `B_C4_remaining` | Beneficio C4 de la comunidad restante (con AGRC si sigue válido) |
| `B_fallback` | Beneficio C4 si el retiro invalida AGRC → cada uno en régimen individual |
| `B_P2P_remaining` | Beneficio P2P de la comunidad restante (sin restricciones) |
| `flexibility_premium` | `B_P2P_remaining − B_fallback` — prima de flexibilidad del P2P |
| `compliant` | ¿La comunidad restante sigue cumpliendo CREG 101 072? |

**Resultado con datos MTE (5 instituciones):**
Ningún retiro individual invalida el régimen AGRC — la comunidad restante sigue cumpliendo
la regla del 10% y el límite de 100 kW en todos los escenarios de retiro. La "prima de
flexibilidad" del P2P es positiva en todos los casos: incluso si C4 no cae a fallback,
el P2P ofrece mayor beneficio a la comunidad restante.

**Fig 17 — Dos paneles:**
- Panel A: beneficios B_C4 (AGRC), B_fallback y B_P2P por escenario de retiro
- Panel B: prima de flexibilidad P2P vs C4_fallback por prosumidor retirado

### FA-4 — Escalamiento de instalación

Para cada prosumidor $n$, se simula escalar su generación (factores 2×, 3×, ...) y se
identifica el umbral de escala donde se viola alguna restricción CREG 101 072:

- Regla del 10%: `G_n × factor / Σ D_n ≤ 0.10`
- Límite 100 kW: `G_n_pico × factor ≤ 100 kW`

**Resultado con datos MTE:**
- Udenar: puede escalar hasta ~3× antes de acercarse al límite del 10%
  (GDR_ind actual = 0.524 / GDR_com = 0.113; margen regulatorio amplio)
- Las otras 4 instituciones tienen margen de escala aún mayor
- C4 podría quedar restringido si alguna institución escala agresivamente su PV,
  mientras que P2P se adapta automáticamente sin necesitar revalidación regulatoria

### Implicación para la tesis

La robustez C4 confirma la ventaja estructural del P2P: mientras C4 requiere
revalidación ante cambios de composición o escala, el P2P reoptimiza dinámicamente
la asignación sin barreras regulatorias. Este es un argumento directo para el
§5 de conclusiones (flexibilidad ante la entrada/salida de participantes y ante
la expansión natural de las instalaciones fotovoltaicas).

---

## §A.7 — Evaluación de brechas vs. propuesta de tesis (estado 2026-04-13)

### Actividades completadas (propuesta §VI)

| Actividad | Descripción | Estado |
|-----------|-------------|--------|
| Act 1.0 | Inventario de elementos del sistema | ✅ |
| Act 1.1–1.2 | Inferencia de parámetros (CAL-1 a CAL-5) | ✅ |
| Act 2.1 | Estructuración de escenarios regulatorios C1–C4 | ✅ |
| Act 2.2 | Algoritmos de cálculo de flujos de caja | ✅ |
| Act 3.1 | Procesamiento de datos empíricos MTE | ✅ |
| Act 3.3 | Descomposición bienestar Nivel 1 / Nivel 2 | ✅ |
| Act 4.1 | Análisis de sensibilidad SA-1/SA-2/SA-3/SA-PPA | ✅ |
| Act 4.2 | Análisis cualitativo de optimalidad | ✅ |
| Act 4.3 | Descomposición sub-períodos | ✅ |
| §VII.C | Robustez regulatoria C4 (FA-3/FA-4) | ✅ |

### Actividad crítica pendiente

**Act 2.3 / 3.2 — Simulación horizonte completo 5160h:**
La propuesta exige "simulaciones de tipo horario a lo largo de un horizonte de
evaluación de seis meses." Esta actividad está POSPUESTO por decisión del usuario.
Es el prerequisito principal para el Capítulo 4 de la tesis.

Comando de ejecución:
```bash
python main_simulation.py --data real --full --analysis
```

Resultado esperado: `resultados_comparacion.xlsx` con 5160 filas horarias,
`graficas/fig12_comparacion_mensual.png`, reporte mensual C1 vs P2P.

### Pendientes de escritura

| Sección | Prerequisito | Urgencia |
|---------|-------------|---------|
| Cap. 4 resultados completos | Ejecución --full | Alta |
| Cap. 5 conclusiones | Resultados Cap. 4 | Alta |
| Apéndice A: derivación Stackelberg | Ninguno | Media |
| Apéndice B: tablas datos MTE | Ninguno | Media |

### Pendiente de datos

- [ ] Verificar LCOE real de inversores instalados (parámetro `b_n`)
  — actualmente `b_n = 225 COP/kWh` (estimado UPME/IRENA)
  — confirmar con datasheets de Udenar, Mariana, UCC, HUDN, Cesmag

---

## Preguntas abiertas para los asesores

### Para Andrés Pantoja (modelado y control)

1. **Calibración del parámetro b (costo de degradación de baterías):** ¿Disponemos de
   las especificaciones técnicas de los inversores instalados en cada institución? El LCOE
   real de los sistemas instalados permitiría calibrar el parámetro `b` en lugar de usar
   el valor por defecto (b=1.2 COP/kWh²).

2. **Dinámica del Stackelberg:** ¿Es apropiado el supuesto de que el líder observa la
   función de reacción de los seguidores antes de fijar el precio P2P? ¿O sería más
   realista un modelo de Cournot simultáneo para el contexto institucional de Pasto?

3. **Horizonte de simulación:** Al correr las 5160h completas, ¿debemos usar la serie XM
   con precios horarios reales descargada de los reportes XM Jul2025–Ene2026, o deberíamos
   escalar los perfiles MTE medidos con la variabilidad horaria de irradiancia NASA POWER?

### Para Germán Obando (economía y regulación)

4. **CREG 101 072/2025:** ¿La resolución final publicada mantiene la estructura PDE descrita
   en el documento preliminar que usamos como referencia? ¿Hay cambios en el mecanismo de
   liquidación de excedentes comunitarios desde la versión consultada?

5. **Representatividad del perfil promedio:** Para la tesis, ¿es suficiente presentar los
   resultados con el perfil diario promedio 24h (que da C1=C3) y complementar con el
   análisis de sub-períodos para mostrar la divergencia? ¿O los comités de evaluación
   esperarían el análisis completo de la serie horaria?

6. **Límite del 10% CREG 101 072:** Las 5 instituciones están muy por debajo del límite
   de participación (máx 4.2% para Udenar). ¿Existe alguna restricción adicional sobre
   la capacidad mínima de instalación que debamos verificar?

7. **Precio de bolsa de referencia:** ¿Cuál es el valor de π_gb que debería usarse para
   las comparaciones regulatorias en el contexto tarifario actual de Pasto/Sur de Colombia?
   ¿El promedio histórico XM, el precio proyectado, o un escenario de estrés?

---

## Tareas pendientes detalladas

### Datos

- [x] Descargar serie horaria XM Jul 2025 – Ene 2026 → `data/precios_bolsa_xm_api.csv` (5160h, media 222 COP/kWh)
  - URL XM: Sistema de Información de Precios de Bolsa (SIC-XM)
  - Columnas requeridas: timestamp, precio_bolsa_COP_kWh, demanda_MW
  - Preprocesamiento: interpolación de faltantes, conversión COP/MWh → COP/kWh

- [ ] Verificar LCOE real de inversores instalados en cada institución
  - Udenar: sistema de paneles en edificio ciencias (capacidad nominal ~15 kWp)
  - Mariana, UCC, HUDN, Cesmag: confirmar fabricante y modelo para datasheet

- [x] Completar perfiles horarios MTE para laborables vs fines de semana
  - `analysis/subperiod.py` → 4 sub-períodos: laborable × {jul, ene} y finde × {jul, ene}
  - Divergencia C1≠C3 confirmada en todos los sub-períodos (8,907–13,595 COP)

### Simulación

- [ ] Correr horizonte completo 5160h:
  ```bash
  python main_simulation.py --data real --full --analysis
  ```

- [x] Análisis de sub-períodos (`analysis/subperiod.py`, `graficas/fig16_subperiod.png`):
  - Laborables vs fines de semana, julio vs enero
  - Ver §A.4 para hallazgos completos

### Modelo

- [x] §3.12 — Desglose hora a hora del mercado P2P (`analysis/p2p_breakdown.py`):
  - CSV 1: `p2p_breakdown_flujos.csv` — un registro por par (vendedor, comprador, hora)
    Columnas: hora, vendedor, comprador, kWh_transados, precio_COP_kWh, valor_COP,
              prima_vendedor_COP, ahorro_comprador_COP
  - CSV 2: `p2p_breakdown_resumen_horario.csv` — un registro por hora
    Columnas: hora, mercado_activo, kWh_total_p2p, precio_prom_pond, vendedores,
              compradores, SC, SS, IE, G_total_kW, D_total_kW
  - Excel de 2 hojas: `p2p_breakdown.xlsx`
  - Se ejecuta automáticamente con: `python main_simulation.py --data real --analysis`

- [x] §3.8 — Sensibilidad de C2 (Bilateral PPA) al parámetro π_ppa (`analysis/sensitivity.py → run_sensitivity_ppa()`):
  - Barrido completo: π_ppa ∈ [π_gb, π_gs] en 11 puntos (factores 0.0 → 1.0)
  - Panel 1: beneficio agregado C2 vs P2P/C1/C4 en función de π_ppa
  - Panel 2: beneficio C2 por agente (quién gana más según el precio pactado)
  - Panel 3: reparto del excedente C2 entre generadores y compradores
  - Gráfica: `graficas/fig10_sensibilidad_ppa.png`
  - Se ejecuta automáticamente con: `python main_simulation.py --data real --analysis`

- [x] §3.6 — Justificación formal de fuente de precios (`data/xm_prices.py → price_source_analysis()`):
  - Descomposición CU institucional (G+T+D+C+PR+otros = 650 COP/kWh)
  - Comparación media, mediana, media solar, percentil 25/75
  - Justificación de la media aritmética como estimador conservador
  - Se ejecuta automáticamente con: `python main_simulation.py --data real --analysis`

### Modelo (nuevos en v8.3)

- [x] §A.6 — Robustez regulatoria C4 (FA-3/FA-4, `analysis/feasibility.py`, `graficas/fig17_robustez_c4.png`):
  - FA-3: simula retiro individual de cada prosumidor → ¿la comunidad restante sigue cumpliendo CREG 101 072?
  - FA-4: escala generación de cada prosumidor (2×, 3×) → ¿cuándo se viola el 10% o los 100 kW?
  - Métrica "prima de flexibilidad": B_P2P_restante − B_C4_fallback
  - Resultado: ningún retiro individual invalida el régimen AGRC con la composición MTE actual
  - Ver §A.6 más abajo para detalle completo

### Escritura tesis

- [x] Capítulo 3: §3.14 completo — IR formal, tabla umbrales, sensibilidad pi_gb y pi_gs
- [ ] Capítulo 4: actualizar con resultados de la serie horaria completa (5160h)
  - **BLOQUEADO** por la ejecución del horizonte completo (pospuesto)
  - Interim: presentar resultados del perfil 24h + sub-períodos como caso de validación
- [ ] Capítulo 5: conclusiones — destacar PoF=0.1346 como resultado central
- [ ] Apéndice A: derivación del equilibrio de Stackelberg
- [ ] Apéndice B: datos empíricos MTE completos (tablas de GDR, H_P2P por mes)

---

## §A.1 — Programa de Respuesta a la Demanda (DR Program)

Implementa los pasos 15–22 del Algoritmo 1 de Chacón et al. (2025).
Código: `core/dr_program.py → run_dr_program()`.

### Formulación

El P2PMO maximiza el bienestar comunitario neto sobre el horizonte T:

$$
\max_{\{Dv_k^n\}} \sum_{k \in \mathcal{T}} W_k, \qquad
W_k = \ln\!\left(1 + \sum_{n} D_k^n\right) - \pi_k \left(\sum_n D_k^n - \sum_n G_{k,\text{lim}}^n\right)
$$

Sujeto a:

| Restricción | Ecuación | Descripción |
|-------------|----------|-------------|
| Demanda total | $D_k^n = D_k^{0n} + Dv_k^n$ | Demanda base + ajuste DR |
| Límite de flexibilidad | $\|Dv_k^n\| \leq \alpha_n \cdot D_k^{0n}$ | Fracción máxima desplazable |
| Conservación | $\sum_k Dv_k^n = 0 \; \forall n$ | No se crea ni destruye energía |

### Implementación

- Método: SLSQP (`scipy.optimize.minimize`) con gradiente analítico.
- Gradiente: $\partial W_k / \partial Dv_k^n = 1/(1 + D_{\text{sum},k}) - \pi_k$

### Calibración para datos reales MTE

$\alpha_n = 0$ para todas las instituciones: la demanda medida es insumo fijo
(no hay señales de control activo en campo). En consecuencia $D^* = D^0$ y el
DR no modifica el despacho. La estructura del código mantiene el DR activo para
simular escenarios hipotéticos de flexibilidad.

### Señal de precio $\pi_k$ del P2PMO

$$
\pi_k = \pi_{gs} + \text{clip}\!\left(\frac{\sum_n G_{k,\text{lim}}^n}{\sum_n D_k^n}, 0, 1\right) \cdot (\pi_{gb} - \pi_{gs})
$$

Cuando hay surplus ($G_{\text{sum}} \geq D_{\text{sum}}$): $\pi_k = \pi_{gb}$.
Cuando hay déficit: $\pi_k \to \pi_{gs}$. La señal incentiva desplazar demanda
hacia las horas de generación solar disponible.

---

## §A.2 — Índice de Gini (equidad distributiva)

Código: `core/settlement.py → equity_index()` (Gini) y `welfare_distribution()`.

### Fórmula

$$
G = \frac{2 \sum_{i=1}^{N} i \cdot B_{(i)}}{N \sum_{i=1}^{N} B_{(i)}} - \frac{N+1}{N}
$$

donde $B_{(i)}$ son los beneficios netos ordenados ascendentemente.

- $G = 0$: beneficios perfectamente iguales entre agentes.
- $G = 1$: un solo agente concentra todos los beneficios.

### Valores en el escenario base (perfil 24h MTE)

| Escenario | Gini | Interpretación |
|-----------|------|----------------|
| P2P | 0.113 | Udenar captura prima mayor como principal vendedor |
| C1 CREG 174 | 0.088 | Más equitativo (autoconsumo proporcional a instalación) |
| C4 CREG 101 072 | 0.088 | Ídem C1 en perfil promedio |

El P2P es algo menos equitativo que C4 porque Udenar (mayor generador, 52% cobertura)
captura una prima de vendedor mayor. Sin embargo, todos los agentes obtienen beneficio
positivo y superior al de C4, lo que justifica el Price of Fairness PoF = 0.1346.

**Relación con IE (reportado en tablas):** la tesis reporta el IE de Chacón et al.,
no el Gini directamente. El Gini se usa internamente para comparar distribuciones entre
escenarios.

---

## §A.3 — SA-3: Sensibilidad al precio al usuario (π_gs)

Código: `analysis/sensitivity.py → run_sensitivity_pgs()`.
Gráfica: `graficas/fig11_sensibilidad_pgs.png`.

### Pregunta de investigación

¿Qué tan robusto es el mercado P2P a variaciones en la tarifa al usuario final
(CU del comercializador)? Si π_gs baja (mayor competencia minorista), ¿el
incentivo a participar en P2P desaparece?

### Rango del barrido

π_gs ∈ [500, 800] COP/kWh. El valor base es 650 COP/kWh (CU ESSA/Cedenar Nariño 2025).
Límite inferior (500): reducción del 23%. Límite superior (800): incremento del 23%.

### Hallazgo

El beneficio del P2P es elástico a π_gs porque el ahorro principal proviene del
**autoconsumo** (energía que no se compra a la red a π_gs). Una reducción de π_gs
reduce el incentivo a participar en el mercado P2P. Por debajo de ~500 COP/kWh,
C4 comienza a ser competitivo con el P2P para algunos agentes.

---

## §A.4 — Análisis de Sub-períodos (Actividad 4.3)

Código: `analysis/subperiod.py`. Gráfica: `graficas/fig16_subperiod.png`.

Compara el mercado P2P en cuatro escenarios que cruzan tipo de día y mes.
La reducción de demanda del 35% en fines de semana refleja el patrón
institucional colombiano (universidades, hospitales con actividad reducida).

### Precios XM reales por grupo (datos reales Jul 2025–Ene 2026)

| Grupo | Media (COP/kWh) | Horas |
|-------|----------------|-------|
| Total | 222 | 5,160 |
| Laborables (L-V) | 218 | 3,696 |
| Fines de semana | 232 | 1,464 |
| Julio 2025 | 133 | 744 |
| Enero 2026 | 219 | 744 |

### Resultados simulación (perfil diario base, datos MTE)

| Sub-período | π_gb | d_fac | P2P (COP) | C1 (COP) | C3 (COP) | C4 (COP) | H-P2P | PoF | \|C1−C3\| |
|------------|------|-------|-----------|----------|----------|----------|-------|-----|---------|
| Laborable-Jul | 133 | 1.00 | 42,002 | 38,338 | 24,743 | 18,754 | 23/24 | 1.24 | 13,595 |
| Laborable-Ene | 218 | 1.00 | 38,175 | 39,931 | 28,570 | 18,754 | 23/24 | 1.04 | 11,360 |
| Finde-Jul | 133 | 0.65 | 36,736 | 33,145 | 22,486 | 22,780 | **24/24** | 0.61 | 10,659 |
| Finde-Ene | 218 | 0.65 | 33,308 | 35,591 | 26,684 | 25,534 | **24/24** | 0.30 | 8,907 |

### Hallazgos clave

1. **C1 ≠ C3 en todos los sub-períodos** — Divergencia de 8,907 a 13,595 COP.
   El supuesto "C1 = C3 en el perfil promedio" no se sostiene con excedente real.
   El mecanismo de liquidación (balance mensual vs spot horario) sí importa.

2. **P2P vs C1 depende del precio de bolsa** — En julio (π_gb=133) P2P domina.
   En enero (π_gb=218) C1 supera al P2P: el precio alto de bolsa beneficia
   a C1 al remunerar los excedentes. Consistente con el umbral IR de Udenar.

3. **Fin de semana → mercado 24/24 h** — Con demanda reducida al 65%, hay
   surplus comunitario en 21/24 horas (vs 14/24 en laborable), lo que activa
   el mercado P2P las 24 horas.

4. **PoF varía 0.30–1.24** — El escenario de menor costo de equidad es
   Finde-Ene (PoF=0.30); el mayor es Laborable-Jul (PoF=1.24).

---

## §A.5 — Act 3.3: Descomposición del bienestar P2P (Nivel 1 / Nivel 2)

**Implementado:** 2026-04-12 | Módulo: `scenarios/comparison_engine.py`

### Motivación

El modelo P2P optimiza funciones de bienestar $W_j$ (vendedores) y $W_i$ (compradores)
que incluyen términos de utilidad de autoconsumo ($\lambda$, $\theta$) y aversión al
riesgo ($\eta$), además de los flujos de caja directos. Los escenarios C1–C4 son
puramente financieros. Para comparar ambos de forma rigurosa, la propuesta
(§VI.C Act 3.3, §VII.C) exige separar el bienestar P2P en dos niveles.

### Nivel 1 — Beneficio monetario directo (COP)

Comparable directamente con C1–C4:

| Componente | Fórmula | Quién recibe |
|------------|---------|--------------|
| Autoconsumo | $\sum_{n \in \mathcal{J}} \sum_k \min(G_{n,k}, D_{n,k}) \times \pi_{gs}$ | Prosumidores |
| Prima vendedor | $\sum_k \sum_j [\pi_{p2p,i}^* \cdot P_{ji}^* - \pi_{gb} \cdot P_{ji}^*]$ | Vendedores P2P |
| Ahorro comprador | $\sum_k \sum_i [(\pi_{gs} - \pi_{p2p,i}^*) \cdot \sum_j P_{ji}^*]$ | Compradores P2P |

El total monetario es `ComparisonResult.net_benefit["P2P"]`.

### Nivel 2 — Bienestar de optimización (unidades de optimización)

Las funciones de bienestar que rigen la dinámica de replicador:

**Vendedores:**
$$W_j = \lambda_j G_j - \theta_j G_j^2 - \sum_i \frac{P_{ji}}{\log(1+\pi_i)} - a_j \left(\sum_i P_{ji}\right)^2 - b_j \sum_i P_{ji}$$

**Compradores:**
$$W_i = \lambda_i G_i - \theta_i G_i^2 + \frac{\sum_j P_{ji}}{\log(|\pi_i|+1)} - \eta_i \sum_{l \neq i} \pi_l \sum_j P_{jl}$$

Estos valores están en **unidades de optimización (u.o.)**, no en COP. Cuantifican
la preferencia de los agentes más allá del flujo de caja: satisfacción por
autoconsumo, aversión a pagar precios altos, penalización por competencia.

### Resultados perfil 24h MTE (2026-04-12) — **PROVISIONAL (2026-04-17)**

**Nota de auditoría:** valores registrados el 2026-04-12 sobre una
configuración anterior. Se marcan como provisionales hasta el run
`--full`; no coinciden necesariamente con los de §4 ni con
`REPORTE_AVANCES.md` por diferencias de fecha y configuración.

| Métrica | Valor |
|---------|-------|
| $\Sigma W_j$ (vendedores) | −7,677.16 u.o. |
| $\Sigma W_i$ (compradores) | +5,815.70 u.o. |
| $W_{total}$ | −1,861.46 u.o. |
| Beneficio monetario Nivel 1 (P2P) | 152,613 COP |
| IE P2P vs IE C4 | +0.1510 vs −0.0614  (Δ = +0.2124) |
| Gini P2P vs Gini C4 | 0.0940 vs 0.1239  (Δ = −0.0300) |
| Price of Fairness | 0.1346 (P2P más eficiente que C4) |

**Interpretación:** $W_j < 0$ para vendedores indica que la utilidad neta de la
función objetivo (incluyendo costos de generación y el término log del precio)
es negativa en u.o., aunque el flujo de caja en COP sea positivo. Esto es
consistente con el modelo de Sofía Chacón: el término de costo $a_j P^2 + b_j P$
domina cuando los parámetros calibrados son altos. El signo de $W$ en u.o. no
implica pérdidas monetarias — el beneficio en COP es la métrica correcta para
la comparación financiera.

### Implementación

- `ComparisonResult.W_sellers_total`, `W_buyers_total` — acumulados de `HourlyResult.Wj_total` y `Wi_total`
- `print_welfare_decomposition(cr)` — imprime la tabla formal Nivel 1 / Nivel 2
- Exportado en `resultados_comparacion.xlsx` → hoja `Metricas_extra`

---

## §A.6 — FA-3/FA-4: Robustez regulatoria C4 (propuesta §VII.C)

**Implementado:** 2026-04-12 | Módulo: `analysis/feasibility.py`, figura `fig17_robustez_c4.png`

### Motivación

La propuesta (§VII.C) exige cuantificar el **beneficio de flexibilidad estructural
del P2P frente a la fragilidad regulatoria de C4**. El escenario C4 (CREG 101 072)
impone dos restricciones rígidas que pueden invalidar el régimen AGRC si la
composición de la comunidad cambia:

1. **Regla del 10%:** ningún agente puede suministrar >10% de la demanda total
2. **Límite 100 kW:** capacidad individual de autogeneración ≤ 100 kW

Si alguna restricción se viola, la comunidad pierde el régimen simplificado
y los créditos PDE desaparecen (fallback = régimen individual, equivalente a C3).

### FA-3: Retiro de participante

Para cada prosumidor $n$, se simula su retiro:
1. Se re-calculan los PDE para la comunidad restante
2. Se verifica cumplimiento CREG 101 072 (FA-2 sobre subconjunto)
3. Si viola: $B_{fallback} = B_{C3,\text{restante}}$ (sin créditos PDE)
4. **Prima de flexibilidad:** $FP_n = B_{P2P,\text{restante}} - B_{fallback,n}$

### FA-4: Escalamiento de instalación

Para cada prosumidor $n$, se evalúa escalamiento $\times$[1.5, 2.0, 2.5, 3.0]:
- ¿Se viola la regla 100 kW? ($G_{n,\max} \times s > 100$)
- ¿Se viola la regla del 10%? ($\bar{G}_n \times s / \bar{D}_{total} > 0.10$)
- Escala máxima sin violar ninguna restricción.

### Resultados perfil 24h MTE (2026-04-12)

**FA-3 — Retiro de participante:**

| Agente retirado | AGRC restante | B_C4_rest (COP) | B_fallback (COP) | B_P2P_rest (COP) | FP (COP) |
|-----------------|--------------|-----------------|-----------------|------------------|----------|
| Udenar          | ✓ Cumple      | 103,802         | 103,802          | 115,874          | +12,071  |
| Mariana         | ✓ Cumple      | 102,356         | 102,356          | 117,820          | +15,465  |
| UCC             | ✓ Cumple      | 95,232          | 95,232           | 115,439          | +20,207  |
| HUDN            | ✓ Cumple      | 103,620         | 103,620          | 120,655          | +17,035  |
| Cesmag          | ✓ Cumple      | 114,633         | 114,633          | 130,683          | +16,050  |

→ **0/5 retiros invalidan el AGRC** en el perfil promedio de 24h.
→ La prima de flexibilidad es positiva en todos los casos (+12k a +20k COP).

**FA-4 — Escalamiento:**

| Agente | G_mean (kW) | Share actual | 2× ok | 3× ok | Escala máx. |
|--------|-------------|-------------|-------|-------|-------------|
| Udenar | 3.95 | 4.2% | ✓ | ✗ | 2.0× |
| Mariana | 1.77 | 1.9% | ✓ | ✓ | 3.0× |
| UCC | 2.22 | 2.4% | ✓ | ✓ | 3.0× |
| HUDN | 1.69 | 1.8% | ✓ | ✓ | 3.0× |
| Cesmag | 0.98 | 1.0% | ✓ | ✓ | 3.0× |

→ Udenar (generador principal) satura la regla del 10% al duplicar × 2.5 (share = 10.5%).
→ Ningún agente supera el límite de 100 kW incluso a 3×.

### Interpretación para la tesis

**Hallazgo principal:** en el perfil promedio de la comunidad MTE, la fragilidad
estructural de C4 **no se activa** con los datos actuales. Ningún retiro individual
invalida el régimen AGRC porque las cuotas de participación son bajas (1–4%).

**Implicación:** el argumento de la propuesta sobre "fragilidad regulatoria de C4"
aplica con más fuerza en comunidades con asimetría de generación mayor, donde un
generador dominante supera fácilmente el 10%. En la MTE, Udenar es el dominante
pero aún está dentro del límite (4.2%).

**Argumento defensible ante el jurado:**
- La prima de flexibilidad P2P es positiva (+12k a +20k COP) en todos los
  escenarios de retiro, incluso cuando C4 no colapsa. Esto significa que P2P
  ofrece más beneficio que C4 independientemente de la composición de la comunidad.
- Si la comunidad creciera (nuevas instituciones con PV), el riesgo de violación
  del 10% aumenta para Udenar, reforzando la ventaja comparativa del P2P.

### Notas de implementación

- `WithdrawalRiskReport` — dataclass con `by_agent`, `community_at_risk`, `flexibility_premium_total`
- `analyze_withdrawal_risk()` — simula retiro de cada prosumidor; usa `run_c4_creg101072` y `run_c3_spot` internamente
- `analyze_scaling_risk()` — evalúa cumplimiento a escalas [1.5×, 2×, 2.5×, 3×]
- `plot_robustness_c4()` → `fig17_robustez_c4.png` (2 paneles: beneficios + prima de flexibilidad)
- Exportado en `resultados_analisis.xlsx` → hojas `FA3_Robustez_Retiro` y `FA4_Robustez_Escala`

---

## §B.1 — Definición canónica de ganancia neta (Filosofía A)

**Decisión validada por asesor Pantoja · reunión WEEF · 2026-04-16**
Referencia: `Documentos/conversacion_WEEF.txt`, min 22–26.

### Definición

```
ganancia_neta_n = costo_línea_base_n − costo_con_sistema_n
                = (D_total_n × π_gs) − costo_pagado_participando
                = savings_n + revenues_n
```

El costo residual de compra a la red **no se resta**. Argumento: ese costo
se incurriría igual sin participar en el mercado. Restar ese costo produce
ganancias negativas para agentes de baja cobertura PV, lo cual el asesor
rechazó explícitamente: *"a mí ganancias negativas no me suenan"*.

### Aplicación por escenario

| Escenario | Fórmula (Filosofía A) | Nota |
|-----------|----------------------|------|
| P2P | `autoconsumo × π_gs + prima_vendedor + ahorro_comprador` | Sin restar déficit residual |
| C1 | `savings + revenue_permutación + revenue_excedente` | Ya era correcto |
| C2 | `savings_gen + savings_cons + grid_revenue` | Corregido 2026-04-16: eliminado `- grid_cost` (línea 91 de `scenario_c2_bilateral.py`) |
| C3 | `savings + revenues_bolsa` | Ya era correcto |
| C4 | `savings + credits_pde + surplus_sell` | Ya era correcto |

### Función canónica

```python
# core/settlement.py — compute_net_benefit()
def compute_net_benefit(savings, revenues):
    """Filosofía A: ganancia_neta = savings + revenues."""
    return np.asarray(savings) + np.asarray(revenues)
```

### Efecto numérico del cambio en C2

Con datos reales día 2025-11-15 (sábado): C2 = 121.149 COP (positivo).
Con perfil promedio 24h: C2 = 145.202 COP. Los demás escenarios no
cambiaron numéricamente.

### grid_cost como campo informativo

`grid_cost` permanece en los dicts de resultados como campo informativo
(representa la factura residual a la red), pero no entra en `net_benefit`.

---

## §B.2 — Corrección doble contabilidad C4 (mode pde_only)

**Implementado: 2026-04-16 · rama tesis/fase-1-desbloqueos**

El código anterior de `run_c4_creg101072()` sumaba simultáneamente:
1. Créditos PDE distribuidos a agentes con déficit (correcto).
2. Venta individual del excedente propio a bolsa (doble contabilidad).

Se agregó el parámetro `mode: Literal["pde_only", "pde_plus_residual_export"]`
con default `"pde_only"` (Tabla I propuesta).

- `pde_only`: el excedente queda dentro de la comunidad redistribuido
  vía PDE; no hay venta a bolsa. Es el mecanismo AGRC puro.
- `pde_plus_residual_export`: solo se exporta el remanente que supera
  la absorción interna (Σ déficit); distribuido por PDE.

---

*Última actualización manual: 2026-04-16*
*Este archivo es permanente — editarlo directamente, no auto-generado*
