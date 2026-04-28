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

### Valores por escenario (horizonte completo MTE_v3) — **OFICIAL (2026-04-28)**

Fuente de verdad: corrida `--data real --full --analysis` del 2026-04-28,
55,2 min, 6 144 h, 256 días, calibración Cedenar mensual per-agente
(CAL-8). Reemplaza la tabla provisional anterior (perfil 24 h, 2026-04-17).

| Escenario              | IE        | Beneficio (MCOP) | Interpretación                                                          |
|------------------------|----------:|----------------:|--------------------------------------------------------------------------|
| C1 CREG 174/2021 ★ eficiente | −0,0115 | 54,04 | Permutación 1:1 captura todo el valor a `pi_gs[n]`; reparto casi neutral |
| **P2P (Stackelberg + RD)** | **+0,3677** | **52,43** | Compradores comerciales (Mariana, UCC, Cesmag) capturan 71,4 % del excedente del mercado |
| C2 Bilateral PPA       | +0,0292   | 51,44 | Reparto cuasi neutral; PPA = 593 COP/kWh contractual            |
| C3 Mercado spot        | +0,0375   | 50,96 | Casi indistinguible de C2 a nivel agregado                       |
| C4 CREG 101 072 ★ vigente | +0,0517 | 50,29 | PDE estático; baseline regulatorio                          |

`PoF (Bertsimas 2011) = 0,0000` (eficiente y equitativo coinciden = C1 →
no hay tensión eficiencia–equidad sobre este horizonte). `RPE P2P vs C4
= +0,0408`. `Spread C4 = 1 004,4 kWh` (energía mal asignada por el PDE
estático, captada por el P2P dinámico).

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

### Verificación con la serie horaria real (6144h, --full post-CAL-8)

Con precios XM horarios reales y perfil desagregado por día:

- Fines de semana y festivos: demanda institucional cae ~60% mientras la generación solar
  mantiene su perfil. $G_n(k) > D_n(k)$ se observa en horas solares para Udenar y
  ocasionalmente otras instituciones (verificado en sub-períodos Finde-Jul/Finde-Ene).
- Días de sequía (El Niño, julio–agosto 2025): precios de bolsa XM más altos → la
  liquidación a bolsa en C3 tiene mayor valor que el autoconsumo ajustado de C1.

**Resultado verificado:** al correr `--full` con la serie real de 6 144 h y la
calibración Cedenar mensual per-agente (CAL-8), $\text{C3} \ne \text{C1}$ en
todos los sub-períodos con $|B^{C1} - B^{C3}|$ entre 3,3 y 7,4 MCOP, confirmando
la predicción.

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

### Resultados con horizonte completo MTE_v3 (post-CAL-8, 2026-04-28)

Fuente de verdad: corrida `--full --analysis` del 2026-04-28 con
calibración Cedenar mensual per-agente (oficial 797 / comercial 956
COP/kWh). Reemplaza el resultado provisional con perfil 24 h del
2026-04-17 (donde 5/5 eran estables) tras incorporar la heterogeneidad
tarifaria oficial vs comercial sobre las 6 144 horas reales.

| Agente  | Categoría | B_n^P2P | B_n^max(C1,C4) | Δ_n        | Δ_n / B_alt | π_gb^* | Estado          |
|---------|-----------|--------:|---------------:|-----------:|------------:|-------:|------------------|
| Udenar  | oficial   | 8,136 k | **10,536 k (C1)** | **−2,400 k** | −22,8 %    | 180    | **deserción**     |
| Mariana | comercial | 12,189 k | 12,003 k (C1)    | +186 k       | +1,5 %     | >rango | OK estable       |
| UCC     | comercial | 15,208 k | 14,709 k (C1)    | +500 k       | +3,4 %     | >rango | OK estable       |
| HUDN    | oficial   | 10,256 k | **10,306 k (C1)** | **−50 k**    | −0,5 %     | 233    | **deserción**     |
| Cesmag  | comercial | 6,642 k  | 6,488 k (C1)     | +153 k       | +2,4 %     | >rango | OK estable       |

**Hallazgo central post-CAL-8:** **3/5 estables (Mariana, UCC, Cesmag —
todas comerciales) y 2/5 en riesgo de deserción a C1 (Udenar y HUDN —
ambas oficiales).** Esto invierte el resultado pre-CAL-8 (5/5 estables
con perfil 24 h y `pi_gs = 650` uniforme).

**Interpretación:** la asimetría oficial (797) vs comercial (956) en
`pi_gs` favorece estructuralmente el mecanismo C1 (créditos 1:1 a
`pi_gs[n]`) sobre el P2P para los agentes con tarifa oficial. La
intuición: cada kWh permutado en C1 vale `pi_gs[n]` directamente,
mientras que en P2P un vendedor oficial obtiene una prima
`(pi_star − pi_gb)` que es menor que su `pi_gs[n]`. Para los
agentes comerciales, su mayor `pi_gs[n]` les permite extraer más
ahorro en P2P como compradores `(pi_gs[i] − pi_star[i])`, lo que
mantiene su Δ_n positivo.

**Implicación para el diseño regulatorio del P2P:** los umbrales
críticos `π_gb^*` para Udenar (180 COP/kWh) y HUDN (233 COP/kWh)
están dentro del rango histórico de bolsa XM 2025 (media 222 COP/kWh,
rango [80, 400]). El P2P necesita un **mecanismo compensatorio**
para los agentes oficiales — subsidio cruzado, ajuste del precio
Stackelberg, o exclusión voluntaria de la permutación C1 — sin el
cual la viabilidad institucional del mercado depende de que las
universidades públicas y hospitales públicos absorban una pérdida
relativa frente a la regulación vigente.

**Nota:** la condición pre-CAL-8 documentada (5/5 estables) era
artefacto del escalar uniforme 650 COP/kWh, que aplanaba la asimetría
real entre régimenes tarifarios. La simulación con tarifa real es
métricamente más severa pero refleja el mercado tal como existe.

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

### CAL-8: `pi_gs` — tarifa Cedenar mensual diferenciada por institución

**Fecha:** 2026-04-27 | **Archivos:** `data/cedenar_tariff.py`,
`data/tarifas_cedenar_mensual.csv`.

Hasta el cierre de auditoría D2 (CAL-6), el modelo usaba un escalar
`pi_gs = 650 COP/kWh` justificado como "punto medio conservador del rango
580-720 COP/kWh reportado por contratos Cedenar/ESSA Nariño". La revisión
del PDF oficial de Cedenar
(`https://scl.cedenar.com.co/Out/Tarifas/Tarifas.aspx`, archivo
`tarifa_210.pdf`, vigente desde 21-abr-2026) muestra que ese escalar
**subestima la tarifa real entre 18 % y 47 %** según la categoría
tarifaria y el nivel de tensión de cada institución.

#### Hallazgo

Tarifa CU 101-028/23 (con COT) para abril-2026, no residencial, NT2:

| Categoría tarifaria | NT2 (COP/kWh) | Aplica a |
|---|---:|---|
| Oficial / Especial | **799,16** | Udenar, HUDN (universidad pública, hospital público) |
| Comercial / Industrial | **958,99** | Mariana, UCC, Cesmag (universidades privadas) |

El escalar 650 no corresponde a ninguna categoría real: coincide
aproximadamente con NT3 sin COT (685,54) o con un promedio histórico
2024–2025, pero **ya está por debajo de la tarifa vigente**.

#### Decisión

1. **Sustituir el escalar por una serie mensual diferenciada** por
   `(categoría tarifaria, nivel de tensión, propiedad del activo)`.
   Convención CSV: `data/tarifas_cedenar_mensual.csv`, una fila por
   `(mes, categoria, nivel_tension, propiedad)`.

2. **Mapeo institucional provisional** (el nivel de tensión real
   debe confirmarse contra factura mensual de cada campus):

   | Institución | Régimen jurídico | Categoría | NT asumido |
   |---|---|---|---|
   | Udenar | Universidad pública | Oficial/Especial | 2 |
   | HUDN | Hospital público | Oficial/Especial | 2 |
   | Mariana | Universidad privada | Comercial | 2 |
   | UCC | Universidad privada | Comercial | 2 |
   | Cesmag | Universidad privada | Comercial | 2 |

3. **Integración (Fase 1, en producción desde 2026-04-27).**
   `main_simulation.py` con `--data real` ya consume el CSV Cedenar:
   - Calcula `pi_gs` comunitario ponderado por la demanda media de
     cada agente sobre el horizonte real de los datos MTE
     (`community_effective_pi_gs` con `weights=D_full.mean(axis=1)`).
   - Imprime la tabla per-agente y la cobertura `meses_cargados /
     meses_horizonte`. Si faltan PDFs para algún mes, lo declara
     explícitamente (`AVISO: ... fallback 650 COP/kWh aplicado en: ...`).
   - El contrato escalar `pi_gs : float` de los escenarios C1-C4 se
     conserva sin cambios; el escalar entregado ya refleja la
     calibración real Cedenar.
4. **Fase 2 (en producción desde 2026-04-27).** Los escenarios C1-C4,
   `comparison_engine`, `analysis/monthly_report` y
   `analysis/p2p_breakdown` aceptan ahora `pi_gs : float | np.ndarray (N,)`.
   El helper compartido `scenarios._pi_gs.as_pi_gs_vector(pi_gs, N)`
   normaliza la entrada a vector `(N,)` al inicio de cada función,
   permitiendo que los análisis de sensibilidad (que varían `pi_gs`
   como escalar) sigan funcionando sin cambios mientras la calibración
   real propaga la heterogeneidad oficial/comercial hasta el detalle
   per-agente:

   - Autoconsumo: cada institución valoriza su `min(G_n, D_n)` a su
     `pi_gs[n]` real (oficial 797 vs comercial 956).
   - Permutación C1, créditos PDE C4, déficit residual: idem.
   - Ahorro comprador P2P: `(pi_gs[i] − pi_star[i]) × P_comprado`,
     captura que UCC (comercial) se ahorra más por kWh comprado en P2P
     que Udenar (oficial).

5. **Fallback explícito.** Si una fecha del horizonte cae fuera de los
   meses cargados, el módulo emite un `UserWarning` único por mes y
   usa el fallback `DEFAULT_PI_GS_FALLBACK = 650 COP/kWh`. Esto
   preserva la reproducibilidad del valor anterior mientras el CSV
   se completa. El log de `main_simulation.py --data real` declara
   explícitamente cualquier mes que cayó al fallback.

#### Estado del CSV

A la fecha de esta nota están cargados **trece meses** (abr-2025 a
abr-2026) con sus PDFs respaldatorios en `data/cedenar_pdfs/` y
130 filas en `data/tarifas_cedenar_mensual.csv`. La cobertura es
total para el horizonte de datos MTE (2025-04-04 → 2025-12-16):
no se invoca el fallback. El `pi_gs` comunitario ponderado por la
demanda media de cada institución resulta en **906 COP/kWh**
(oficial NT2 = 797, comercial NT2 = 956), un **+39 %** sobre el
escalar legacy de 650 COP/kWh.

#### Impacto observado en resultados

Validación sobre el horizonte completo MTE_v3 (corrida `--full
--analysis` 2026-04-28, 55,2 min, 6 144 h):

| Métrica | Pre-CAL-8 (650 escalar) | Post-CAL-8 (vector per-agente) | Δ |
|---|---:|---:|---:|
| Beneficio P2P    | 37,78 MCOP | **52,43 MCOP** | +38,8 % |
| Beneficio C1     | 39,56 MCOP | **54,04 MCOP** | +36,6 % |
| Beneficio C4     | 36,56 MCOP | **50,29 MCOP** | +37,6 % |
| RPE P2P vs C4    | +0,0321    | **+0,0408**    | +27 % en magnitud |
| Σ ventaja P2P − C4 | 1,21 MCOP | **2,14 MCOP** | +77 % |
| IE P2P           | +0,4063    | +0,3677        | −0,04 (vendedores capturan algo más) |
| Agentes IR-estables | 5/5     | **3/5** (Udenar y HUDN desertan a C1) | hallazgo nuevo |

Validación adicional sobre el perfil 24 h (sanity check rápido):
P2P = 211 046 COP, IE = +0,209. Todos los signos coherentes con la
corrida `--full`.

Cifras observadas:

1. **Bienestar absoluto** de los cinco escenarios sube ~37 % por la
   recalibración. El delta vs comunitario uniforme refleja la
   heterogeneidad: tres comerciales (Mariana, UCC, Cesmag — tarifa
   956) vs dos oficiales (Udenar, HUDN — tarifa 797).
2. **Brecha C1 ↔ C3 se amplía**: la permutación 1:1 a `pi_gs[n]` vale
   más, mientras la liquidación a bolsa permanece anclada en ≈ 280
   COP/kWh. C1 emerge como el escenario dominante en eficiencia
   monetaria (`PoF = 0,0000`).
3. **Jerarquía P2P > C4 se mantiene** en las cinco instituciones, y
   la ventaja absoluta agregada **casi se duplica** (1,21 → 2,14 MCOP).
   Sin embargo, la **frontera relevante para IR es ahora C1**, no C4:
   ver §3.14 sobre la deserción de Udenar y HUDN al régimen AGPE.
4. **IE P2P sigue siendo positivo** (+0,3677): los compradores
   comerciales (Mariana, UCC, Cesmag) capturan 71,4 % del excedente
   P2P agregado por su mayor `pi_gs[i]`. Los vendedores capturan el
   28,6 % restante.

#### Veredicto

`pi_gs = 650 COP/kWh` queda **deprecado como valor escalar único**.
Se conserva solo como `DEFAULT_PI_GS_FALLBACK` para los meses sin
PDF Cedenar disponible (hoy ninguno, cobertura es total).
La fila correspondiente en la tabla resumen se actualiza abajo.

### Resumen de recomendaciones de calibración

| Parámetro | Valor actual | Referencia | Veredicto | Acción |
|-----------|-------------|-----------|-----------|--------|
| `stackelberg_iters` | 2 | —  | **Justificado** | Ninguna |
| `etha` | 0.1 | JoinFinal=0.1 / artículo=1.0 | **Inerte** | Ninguna |
| `alpha_p` | 0.20 | Literatura 10–40% | **Óptimo empírico** | Documentar en §III-A tesis |
| `alpha_c` | 0.10 | 50% de alpha_p | **Conservador** | Documentar en §III-A tesis |
| `theta` | 0.5 | JoinFinal=0.5 / SLSQP=10 | **Solo reporting** | Ninguna |
| `WI/WJ scaling` | no implementado | tau_b/tau_s=10 equivalente | **Implícito** | Ninguna |
| `pi_gs` real | 650 COP/kWh (fallback) | Cedenar abr-2026: 799 oficial / 959 comercial NT2 | **Deprecado como escalar** | Cargar serie mensual en `tarifas_cedenar_mensual.csv` (CAL-8) |
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

### Resultados GSA Sobol-Saltelli (n_base = 64, 2026-04-17)

Ejecutado con `python main_simulation.py --gsa --n-base 64`.
7 parámetros: PGB, PGS, factor_PV, factor_D, alpha_mean, b_mean, pi_ppa.
3 outputs: ganancia neta, SC (auto-consumo), IE (inequidad).

**Alcance metodológico — sobre qué corre el GSA (auditoría 2026-04-26).**
El GSA Sobol-Saltelli opera sobre el **modelo de referencia** (Chacón
et al., 2025) con perfiles sintéticos de 24 h y 6 agentes. Los
parámetros `factor_PV` y `factor_D` escalan multiplicativamente esos
perfiles base; `factor_PV = 1.0` corresponde al perfil sintético sin
escalar, no al perfil promedio MTE. El flag `--data real` se ignora
en modo `--gsa`: `analysis/global_sensitivity.py:_eval_sample` usa
`get_generation_profiles()` y `get_demand_profiles()` de
`data/base_case_data.py` (perfiles del modelo Sofía), no
`MTEDataLoader`.

**Cobertura de la propuesta (§VI.D, §VII.D).** La Actividad 4.1 pide
(a) índices de sensibilidad global y (b) evaluación bajo condiciones
históricas reales en distintas semanas o días. Esta tesis cubre ambas
componentes con métodos ortogonales:

- **Sobol-Saltelli sobre el modelo de referencia** (esta sección):
  proporciona los índices de sensibilidad global y captura
  *interacciones* entre parámetros — información que los barridos
  uni-paramétricos no entregan.
- **Barridos uni-paramétricos sobre MTE_v3** (`analysis/sensitivity.py`,
  SA-1 PGB, SA-2 factor_PV, SA-3 PGS, SA-PPA): operan sobre el
  horizonte completo de 6 144 h; cuantifican la sensibilidad relativa
  bajo condiciones empíricas reales.
- **Análisis de subperíodos** (`analysis/subperiod.py`, SP1–SP4):
  desagrega laborable/finsemana × Jul/Ene; complementa la cobertura
  de "distintas semanas o días" exigida por la propuesta.

La combinación de los tres mecanismos satisface la Actividad 4.1; el
GSA Sobol no se ejecuta sobre MTE por dos razones declaradas:
(i) el costo computacional de Saltelli sobre 6 144 h × 1 024
evaluaciones es prohibitivo y (ii) los barridos uni-paramétricos sobre
MTE ya cubren la dimensión de "datos históricos". La cancelación del
intento de re-ejecutar el GSA sobre MTE_v3 (run del 2026-04-26 abortado
tras 5 min) está documentada en
`docs/superpowers/specs/2026-04-26-gsa-mte-v3-design.md` y su plan
asociado.

**Índices ST cualitativos (totales; más robustos que S1 con n_base pequeño):**

| Parámetro | ST ganancia | ST SC | ST IE | Interpretación |
|-----------|-------------|-------|-------|----------------|
| factor_PV | 4,63 | 0,85 | 0,23 | dominante en ganancia y SC |
| factor_D  | 2,92 | 0,21 | 0,10 | segundo en ganancia |
| PGB       | 0,73 | ~0   | 2,94 | dominante en equidad |
| PGS       | 1,77 | ~0   | 0,19 | impacto en ganancia |
| alpha_mean| 0,06 | 0,02 | 0,02 | efecto DR pequeño |
| b_mean    | ~0   | 0    | 0,07 | sin efecto significativo |
| pi_ppa    | 0    | 0    | 0    | sin efecto (C2 desactivado) |

**Nota:** S1 negativos y ST > 1 son artefacto de n_base = 64 (IC > media).
El orden cualitativo es estable: `factor_PV` y `factor_D` gobiernan
el bienestar global; `PGB` es el parámetro más crítico para la equidad.
Para IC publicables (S1_conf < S1): ejecutar con n_base ≥ 256.

**Infraestructura `_fast_mode` (commit `19e57cb` y siguientes) — DEPRECADA EFECTIVAMENTE.**
`core/replicator_sellers.py` expone un flag `_fast_mode` que reduce
`VEL_GRAD` de 1e6 a 1e3 y relaja las tolerancias del solver ODE
(`rtol=0.5`, `atol=0.1`, `max_step=2e-4`). El test
`tests/test_fast_mode_equivalence.py` valida equivalencia en 8 horas
representativas (||P||_∞ ≤ 0,15 kWh) pero la re-ejecución del GSA con
`_fast_mode=True` el 2026-04-27 reveló que **ciertos samples Saltelli
disparan ciclos infinitos del Newton iterativo de LSODA** (probabilidad
empírica ~58% del espacio de parámetros). La validación de 8 horas no
muestrea esos casos patológicos. **Decisión 2026-04-27:** desactivar
`_fast_mode` en `_eval_sample` (línea 105). El GSA opera en modo preciso
con timeout-wrapper de 45 s por evaluación (samples patológicos se marcan
NaN y se filtran del estimador Sobol).

### Resultados GSA Sobol-Saltelli (n_base = 128, 2026-04-27)

Re-ejecución con `python main_simulation.py --gsa --n-base 128`
(2048 evaluaciones; 11 workers; 111 min). Modo preciso, timeout-wrapper
45 s, bounds originales `factor_PV ∈ [0.5, 2.0]`. **1367/2048 muestras
válidas (66.7%)** — el resto NaN por timeout en samples patológicos.

| Parámetro | ST ganancia | ST SC | ST IE | Interpretación |
|-----------|-------------|-------|-------|----------------|
| factor_PV | 0,66 | 0,82 | 0,41 | dominante en ganancia y SC |
| factor_D  | 0,44 | 0,37 | 0,26 | segundo en ganancia |
| PGB       | 0,08 | 0,11 | **0,99** | dominante en equidad |
| PGS       | 0,22 | 0,07 | 0,25 | impacto en ganancia |
| alpha_mean| 0,12 | 0,10 | 0,15 | efecto DR pequeño |
| b_mean    | 0,02 | 0,07 | 0,33 | secundario en equidad |
| pi_ppa    | 0,01 | 0,04 | 0,05 | sin efecto (C2 desactivado) |

**Mejora vs n=64:** todos los ST < 1 (era artefacto en n=64), IC más
estrechos. Ranking idéntico al GSA previo: `factor_PV` y `factor_D`
gobiernan ganancia/SC; `PGB` gobierna equidad. Confirma robustez de
los hallazgos del 2026-04-17.

### Resultados Bootstrap P2P vs C4 (n=500, 2026-04-17)

Ejecutado con `tests/statistical_tests.py`, datos: 215 días MTE, block_days=7, seed=42.

| Métrica | Valor |
|---------|-------|
| Δ̄ (P2P − C4) | 7 489 COP/día |
| IC 95 % (bootstrap) | [6 051, 8 963] COP/día |
| p-valor Wilcoxon | 0,000 |
| Cohen's d | 0,67 (efecto medio-alto) |
| n_eff (bloques) | 30 |

**Conclusión:** P2P supera a C4 con diferencia estadísticamente significativa
(p = 0). El intervalo de confianza no incluye 0. Cohen's d = 0,67 indica
efecto práctico medio-alto. Resultado sobre 215 días, perfil promedio diario;
pendiente replicación sobre serie horaria completa 5 160 h.

### Resultados Bootstrap P2P vs C4 (n=10 000, MTE_v3 6 144 h, 2026-04-27)

Re-ejecutado con `tests/statistical_tests.py --n-bootstrap 10000`
sobre series diarias del run `--data real --full` (256 días MTE_v3,
block_days=7, seed=42).

| Métrica | Valor |
|---------|-------|
| Δ̄ (P2P − C4) | 4 732 COP/día |
| IC 95 % (bootstrap) | [3 629, 5 751] COP/día |
| p-valor Wilcoxon | 0,000 |
| Cohen's d | **0,90** (efecto grande) |
| n_eff (bloques) | 36 |

**Cambio vs run de abril-17 (n=500, 215 días):** Δ̄ baja de 7 489 a
4 732 COP/día porque la muestra incluye más meses con menor diferencia
(MTE_v3 cubre Abr–Dic vs Jul–Dic anterior). El IC 95% sigue sin incluir
0; Cohen's d aumenta a 0,90 (efecto grande) por la reducción de varianza
con n=10 000. Resultado más robusto y publicable.

### Cierre del ciclo 2026-04-27

Ejecución completa del sistema (extremo a extremo, ~3,5 h):
- Validación pytest: 33/33 tests verdes (incluye 8 nuevos de `matlab_export`).
- Run `--data real --full --analysis`: 51,7 min, REPORTE_AVANCES.md actualizado.
- GSA Sobol n_base=128: 111 min, índices ST publicables (66,7% válidas).
- Bootstrap n=10 000 sobre MTE_v3: IC 95% [3 629, 5 751] COP/día, p<0,001.
- 4 figuras nuevas: fig18 (heatmap PGB×PV), fig19 (deserción individual),
  fig20 (Price of Fairness), fig21 (robustez C4 por agente).
- Helper `visualization/matlab_export.py`: 16 .mat + 44 .csv generados,
  todos validados con `scipy.io.loadmat` y `pandas.read_csv`.

**Siguiente:** redactar Capítulo 4 con datos del run; revisar con asesores.

### ~~Actividad crítica pendiente~~ → COMPLETADA

**Act 3.2 — Simulación horizonte completo 6 144 h:**
Ejecutada con MedicionesMTE_v3 (Abr–Dic 2025, 256 días), commit `cdb11e9`, ~56 min.
RPE = 0,0321 · 1 031/6 144 h con mercado activo · 3 657,7 kWh P2P transados.
`graficas/fig12_comparacion_mensual.png` generada. Ver `REPORTE_AVANCES.md` para métricas completas.

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

3. **Horizonte de simulación:** Al correr las 6 144 h completas (MTE Abr–Dic 2025),
   ¿debemos usar la serie XM con precios horarios reales descargada de los reportes
   XM Jul2025–Ene2026, o deberíamos escalar los perfiles MTE medidos con la variabilidad
   horaria de irradiancia NASA POWER?

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

- [x] ~~Correr horizonte completo 5160h~~ → **6 144 h** con MedicionesMTE_v3, commit `cdb11e9`

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
  - Descomposición CU institucional (G+T+D+Cv+PR+R+COT) — la calibración real
    en producción es la tarifa Cedenar mensual per-agente (CAL-8): oficial NT2
    797, comercial NT2 956, comunitario ponderado 906 COP/kWh. La función
    `price_source_analysis()` reporta la descomposición ilustrativa contra el
    escalar legacy de 650 COP/kWh (deprecado).
  - Comparación media, mediana, media solar, percentil 25/75 del precio de bolsa.
  - Justificación de la media aritmética como estimador conservador.
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
- [ ] Capítulo 4: actualizar con resultados de la serie horaria completa (6 144 h, MTE_v3)
  - Resultados disponibles: `REPORTE_AVANCES.md`, `resultados_comparacion.xlsx`
- [ ] Capítulo 5: conclusiones — destacar PoF formal (Bertsimas 2011) como resultado central
  - PoF implementado en `analysis/fairness.py`; valor concreto disponible tras cada ejecución
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

π_gs ∈ [500, 1100] COP/kWh. El valor base bajo CAL-8 es 906 COP/kWh
(promedio comunitario Cedenar ponderado por demanda; oficial NT2 797 /
comercial NT2 956). El barrido SA-3 cubre desde 500 (~ 45 % por debajo del
base, escenario hipotético de competencia minorista intensa) hasta 1100
(~ 21 % por encima del base, techo de proyección). El antiguo escalar
650 COP/kWh queda como fallback para meses sin PDF Cedenar (hoy ninguno).

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

## §3.1 — Preprocesamiento MTE: selección de medidor, inversor y manejo de net metering

**Implementado: 2026-04-25 · módulo nuevo `data/preprocessing.py`**

### Motivación

La versión anterior del cargador (`data/xm_data_loader.py`, función `_aggregate`) sumaba **todos** los CSV encontrados vía `rglob("*.csv")` en las carpetas de medidores e inversores por institución. Esto producía dos problemas físicamente incorrectos:

1. **Mezcla de señales heterogéneas.** Cada institución tiene cuatro medidores con propósitos distintos (totalizador principal, ramales internos, medidores de inyección de solar). Al sumarlos se obtenía una "demanda" que no correspondía a ningún punto de medición físico — incluyendo en algunos casos medidores de inyección con valores negativos (Udenar Med 4 "Inyección PJ", Cesmag Med 3 "Bloque-A").

2. **Demanda artificialmente baja al mediodía en Udenar** por *net metering* del totalizador Bloque Sur Med 1: el medidor registra `consumo - solar_inyectada`, no consumo bruto. La rutina `_clean()` trataba los valores negativos como NaN, ocultando el problema en lugar de resolverlo.

### Decisión: selección puntual por institución

Se eligió **un medidor único** por institución para representar la demanda y **un inversor único** para la generación expuesta al EMS. Las cinco gráficas de referencia están en `Documentos/otros/comparacion_4med_<institucion>.png`.

| Institución | Medidor de demanda (subcarpeta exacta) | Tipo | Inversor EMS | Inversores de reconstrucción |
|---|---|---|---|---|
| Udenar | `Bloque Sur - Medidor 1 - electricMeter` | **net** | `Fronius Inverter 1 - inverter` | Fronius 1 + Fronius 2 + Inversor MTE (suma) |
| Mariana | `Medidor 1 - Alvernia - electricMeter` | **net_partial** | `Fronius - Alvernia - inverter` | Fronius - Alvernia (mismo) |
| UCC | `Medidor 1 - UCC - electricMeter` (totalizador gabinete ppal) | **net_partial** | `Fronius - UCC - inverter` | Fronius - UCC (mismo) |
| HUDN | `Medidor 1 - HUDN - electricMeter` | gross | `Inversor 1 - HUDN - inverter` | — |
| Cesmag | `Medidor 1 - Cesmag - electricMeter` | gross | `Inverter 1 - Cesmag - inverter` | — |

**Tipos:** `net` (netting agresivo, Udenar 989 h con D<0), `net_partial` (Mariana 149 h, UCC 55 h con D<0; reconstrucción a través del único inversor), `gross` (limpio, sólo `clip(lower=0)` defensivo).

**Horizonte de simulación:** `2025-04-04 → 2025-12-16` (6 144 h, 256 días) sobre `MedicionesMTE_v3`. Ver § sobre auditoría más abajo.

Justificación visual:
- **Udenar**: Med 1 muestra valle pronunciado al mediodía (consistente con net metering, ver verificación empírica abajo).
- **Cesmag**: Med 1 (Bloque-B) tiene perfil académico característico 3–7 kW con pico ~13 h, sin signos de netting.
- **HUDN**: Med 1 es plano 8–10 kW las 24 h (carga hospitalaria estable, sin influencia solar).
- **Mariana / Alvernia**: Med 1 (Totalizador principal) plano 7–10 kW; Med 2–4 son ramales <1 kW que no representan el edificio.
- **UCC**: se eligió **Med 1 (Totalizador gabinete principal)** que mide el edificio completo (rango 9–68 kW, pico ~30 kW al mediodía). Cobertura PV ~14 % → comprador firme. Es la lectura físicamente representativa del nodo UCC. Decisión revisada el 2026-04-25 (originalmente se había propuesto Med 2 / piso 1 para diversificar la comunidad, pero se priorizó la fidelidad del modelo a la realidad del edificio).

### Pipeline detallado del preprocesamiento

El módulo `data/preprocessing.py` ejecuta el siguiente flujo cada vez que se llama `MTEDataLoader.load()` (vía `main_simulation.py` o cualquier script consumidor). Es determinístico y dura 5–10 s sobre `MedicionesMTE_v3` con horizonte Abr-Dic (6 144 h).

#### Paso 0 — Construcción del eje temporal canónico

```python
idx = pd.date_range(T_START="2025-04-04", T_END="2025-12-16",
                    freq="1h", inclusive="left")  # → 6 144 horas
```

Todo el resto del pipeline reindexa al `idx` para garantizar shape uniforme (5 instituciones × 6 144 horas).

#### Paso 1 — Por cada institución (5 iteraciones, orden fijo)

Orden: `["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]`. Por institución:

**1.a — Localizar carpetas** (tolerante a mayúsculas vía `_find_subdir`):

```
<root>/<agent>/<METER_FOLDER[agent]>/<DEMAND_METER_CONFIG[agent]['subfolder']>
<root>/<agent>/<INVERTER_FOLDER[agent]>/<EMS_INVERTER_CONFIG[agent]>
```

**1.b — Lectura del medidor de demanda** (`_read_single_meter`, líneas 117-142):

1. Itera todos los CSVs de la subcarpeta vía `rglob("*.csv")` (en v3 hay 3 archivos por medidor: Ene-Jun, Jun-Ene, Ene-Abr).
2. Por cada CSV: `pandas.read_csv` → parse columna `date` → set como índice → `to_numeric` sobre `totalActivePower` → si hay timestamps duplicados, los promedia (`groupby(s.index).mean()`).
3. Concatena las series con `pd.concat(parts, axis=1).sum(axis=1, min_count=1)` (suma con `NaN` donde ningún CSV tiene datos).
4. Filtra a la ventana `[idx[0], idx[-1]]`.
5. Resample a 1h (media de las muestras de cada hora).
6. Reindexa al `idx` canónico (NaN donde no hay datos en esa hora).

Devuelve serie en kW, **sin clipping de negativos** (la decisión de cómo tratar negativos depende del tipo declarado).

**1.c — Lectura del inversor EMS** (`_read_single_inverter`, líneas 145-152):

Mismo flujo, columna `acPower`, divide por 1 000 (W→kW), `clip(lower=0)` defensivo (la potencia AC inyectada nunca puede ser negativa físicamente).

**1.d — Resolución de no-negatividad según tipo declarado** en `DEMAND_METER_CONFIG[agent]['kind']`:

| Tipo | Instituciones | Operación |
|---|---|---|
| `net` | Udenar | `G_recon = ΣG_inv (Fronius1+Fronius2+InversorMTE)`<br>`D_bruta = max(0, D_net + G_recon)` |
| `net_partial` | Mariana, UCC | `G_recon = G del único inversor`<br>`D_bruta = max(0, D_net + G_recon)` |
| `gross` | HUDN, Cesmag | `D_bruta = max(0, D_raw)` (sólo clip defensivo) |

Justificación de las tres ramas:
- **`net`**: el totalizador físico nettea solar (visible en gráfica como dip al mediodía e incluso valores negativos exportadores). Reconstruir con la suma de TODOS los inversores es la única forma físicamente correcta de recuperar la demanda bruta.
- **`net_partial`**: pequeña fracción de horas con D < 0 (~3 % en Mariana, ~2 % en UCC). El medidor no es net agresivo, pero hay episodios. La reconstrucción con el inversor único corrige esos episodios sin alterar el resto (verificado: ratio reconstrucción/G_inv ≈ 0.99).
- **`gross`**: medidores limpios, sin valores negativos ni dip al mediodía. Sólo aplica `clip(0)` defensivo por si hay glitches puntuales del sensor (en HUDN/Cesmag = 0 horas truncadas).

El pipeline registra y reporta `n_horas_reconstruidas`, `n_horas_passthrough` y `n_horas_clipeadas_a_0`.

**1.e — `_clean()`** (en `data/xm_data_loader.py:134-166`):

Aplicado tanto a `D_bruta` como a `G_ems`. La rutina **ya no toca negativos** (se resolvieron aguas arriba); se enfoca en outliers y gaps:

1. **Detección de outliers** con umbral híbrido robusto a distribuciones bimodales:
   ```
   umbral = max( Q75 + 5·IQR ,  P99.5 × 1.2 )
   ```
   El piso `P99.5 × 1.2` evita cortar picos académicos legítimos cuando la carga base es plana (IQR pequeño, p. ej. Cesmag: IQR ≈ 1.2 kW, picos de ~15 kW). Valores > umbral → NaN.
2. **Imputación de gaps cortos**:
   - `interpolate(method="time", limit=3)` → interpolación lineal hasta 3 h consecutivas (típico: una o dos lecturas perdidas).
   - `ffill(limit=24).bfill(limit=24)` → propaga última lectura conocida hasta 24 h (cubre el corte de mediados de Dic, ~3 días).
   - `fillna(0.0)` → ceros para lo restante (horas largas sin datos: noche para G; sólo aparece si una falla cubre > 24 h, que en el horizonte sólido no debería pasar).

#### Paso 2 — Apilado y validación

```python
D = np.array(D_list, dtype=float)   # shape (5, 6144)
G = np.array(G_list, dtype=float)   # shape (5, 6144)

# Sanity check del contrato (línea 309-318)
if (D < 0).any(): raise RuntimeError("BUG: D negativa")
if (G < 0).any(): raise RuntimeError("BUG: G negativa")
```

#### Paso 3 — Localización de zona horaria

```python
idx_tz = idx.tz_localize("America/Bogota",
                         nonexistent="shift_forward",
                         ambiguous="infer")
```

`shift_forward` para los saltos DST inexistentes (no aplica en Colombia, pero es robusto), `infer` para los ambiguos.

#### Paso 4 — Retorno

`return (D, G, idx_tz)` con:
- `D.shape == (5, 6144)`, dtype `float64`, kW
- `(D >= 0).all()` y `(G >= 0).all()` garantizados
- Orden de filas: `["Udenar", "Mariana", "UCC", "HUDN", "Cesmag"]`

Esto es exactamente lo que el EMS y los escenarios C1-C4 reciben downstream.

#### Cuándo se ejecuta

| Comando | Llamadas a `load()` |
|---|---|
| `python main_simulation.py --data real` | 1 (perfil promedio 24 h) |
| `python main_simulation.py --day YYYY-MM-DD` | 1 (slice de 24 h) |
| `python main_simulation.py --data real --full` | 1 (las 6 144 horas) |
| `python main_simulation.py --data real --full --analysis` | 1 + análisis posterior |
| `python outputs/audit_clean.py` | 0 (lee crudo, no usa el loader) |
| `python outputs/data_quality_audit.py` | 0 (igual) |
| Tests `pytest tests/test_preprocessing.py` | 1 (fixture cacheada con `scope="module"`) |

No se cachea entre ejecuciones porque el costo es bajo (5–10 s) y la determinismo se preferible al riesgo de "datos pegados". Si en el futuro algún flujo (Sobol, bootstrap masivo) requiere muchas re-cargas, el patrón es cargar una vez y pasar `D, G, idx` por argumento.

### Auditoría exhaustiva de calidad de datos (2026-04-25)

Se ejecutó una auditoría sistemática sobre las 27 fuentes (5 instituciones × 4 medidores + 7 inversores) con `outputs/data_quality_audit.py`. Salidas archivadas en:

- `outputs/data_quality_report.txt` — reporte texto regenerable
- `outputs/data_quality_metrics.csv` — tabla maestra de métricas por CSV
- `graficas/data_coverage_gantt.png` — Gantt visual de cobertura

**Hallazgos estructurales:**

1. **Horizonte sólido común Abr 4 → Dic 16 2025 (256 días).** Sobre `MedicionesMTE_v3` (que extiende los datos a Ene 2025 → Abr 2026), el cuello de botella temprano es el inversor de HUDN que arranca el 4-Abr-2025; el cuello de botella tardío sigue siendo Dic 16 2025 (HUDN y Fronius Udenar simultáneamente). Más allá del 22-Dic 2025 HUDN tiene gap de 5 semanas hasta el 27-Ene 2026 — para evitar imputación masiva, `T_END = 2025-12-16`. Esto da +88 días vs el horizonte previo (v2, Jul-Dic).
2. **Gap global mediados de Diciembre (~14-16-Dic):** todos los CSV tienen una franja faltante simultánea. Sugiere caída de servidor / mantenimiento de la red MTE. _clean() lo cubre con interpolación ≤ 24 h.
3. **Sensores frozen detectados (4):** Udenar Med 2 (4442 h), Mariana Med 4 (4351 h), Cesmag Med 2 (4443 h), UCC Med 4 (178 h). Son ramales nunca instrumentados o averiados; no son alternativas viables de medición.
4. **Net metering parcial en Mariana y UCC:** 149 h y 55 h respectivamente con D<0 sobre el horizonte recortado (3-Sep no aplica). Tratamiento como `net_partial` reconstruye con el único inversor disponible y elimina los negativos sin perder energía contabilizada (ratio delta/G_recon ≈ 0.99).
5. **Udenar inversor EMS migrado a Fronius Inverter 1** (cobertura Jul-Dic) en lugar de Inversor MTE (cobertura Sep-Ene). Razón: con T_END = Dic 17 el horizonte de Inversor MTE se reduce a Sep-Dic y deja Jul-Ago sin generación EMS visible. Fronius 1 cubre el período completo del horizonte recortado. La reconstrucción `D_bruta` sigue usando los tres inversores sumados.

**Comandos de auditoría:**

```powershell
python outputs/data_quality_audit.py        # reporte texto + CSV
python outputs/plot_coverage_gantt.py       # figura Gantt
python outputs/audit_clean.py               # diagnóstico post-preprocesamiento
```

### Verificación empírica del net metering en Udenar

Se ejecutó una comparación directa Bloque Sur Med 1 ∩ Inversor MTE sobre el período de overlap (2025-09-03 → 2026-01-29):

- **710 h con valor negativo** en el período de verificación (≈20% del horizonte de overlap, mínimo −34.6 kW). Sobre el horizonte completo Jul 2025 → Feb 2026 son **1146 h** negativas.
- Perfil hora-a-hora promedio: D_net cae a **−10 kW al mediodía** y sube a **+11 kW a las 17 h**. No es un patrón de carga real; es netting agresivo.
- Reconstrucción `D_net + Inversor MTE` al mediodía aún quedaba en **−3.5 kW**, demostrando que los **tres inversores físicos de Udenar** (Fronius 1 + Fronius 2 + Inversor MTE) inyectaban simultáneamente y el totalizador descontaba los tres.

### Estrategia de dos capas

Para satisfacer la regla "un solo inversor expuesto al EMS" sin sacrificar la corrección física de la demanda bruta, el módulo `data/preprocessing.py` separa dos configuraciones:

- **`EMS_INVERTER_CONFIG`**: cuál inversor el modelo expone como `G[agent]`. Una sola subcarpeta por institución.
- **`RECONSTRUCTION_INVERTERS_CONFIG`**: para los net meters, qué inversores **sumar** internamente para revertir el netting y recuperar la demanda bruta. Es bookkeeping físico — no entra al EMS.

Pipeline para Udenar:
1. Lee `D_net` desde Bloque Sur Med 1.
2. Lee `G_recon = Fronius1 + Fronius2 + Inversor MTE` (rellenando con 0 donde alguno no tiene cobertura — Fronius 1+2 cubren Jul–Dic, Inversor MTE cubre Sep–Ene).
3. `D_bruta = max(0, D_net + G_recon)`.
4. `G[Udenar] = Inversor MTE` (un solo inversor expuesto al EMS).

Pipeline para los gross (Mariana, UCC, HUDN, Cesmag):
1. Lee `D_raw` del medidor único declarado.
2. `D = max(0, D_raw)` con conteo y log de horas truncadas (deberían ser raras; si son muchas, bandera roja).
3. `G[agent] = inversor único declarado`.

La rutina `_clean()` (outliers + interpolación + ffill/bfill) se aplica al final, sin el paso `s[s<0]=NaN` que ya no es necesario.

### Limitaciones documentadas

- **Udenar 2026-01-30 → 2026-02-01** (3 días): ningún inversor de Udenar tiene cobertura en esa ventana. La reconstrucción queda passthrough; el efecto sobre la simulación es despreciable (3 días de 215).
- **Udenar Jul–Ago 2025 — generación EMS aparente cero**: durante ese período Inversor MTE no estaba operativo (sí lo estaban Fronius 1+2). Al exponer solo Inversor MTE como `G[Udenar]`, el EMS no ve la generación física que existió. Es decisión deliberada por la regla "un solo inversor"; la reconstrucción de la demanda bruta sí usa Fronius 1+2 (capa interna), por lo que el efecto sobre `D[Udenar]` queda corregido.
- **UCC ~119 h con D < 0** (mín −8.2 kW): el totalizador principal tiene 119 horas con valores negativos pequeños probablemente por instrumentación o netting parcial de algún ramal interno. Se truncan a 0; bandera amarilla pendiente de revisión con el equipo MTE.
- **Mariana ~160 h con D < 0**: el medidor "gross" de Alvernia tiene 160 horas con valores negativos pequeños (mín −2.4 kW), probablemente instrumentación. Se truncan a 0 con log; bandera amarilla pendiente de revisión con el equipo MTE.

### Cómo reproducir / auditar

```powershell
# Auditoría completa por institución × señal
python outputs/audit_clean.py

# Tests del contrato (no-negatividad, shape, reconstrucción, EMS distinto)
python -m pytest tests/test_preprocessing.py -v

# Smoke completo
python main_simulation.py --data real
```

La auditoría imprime, por institución:
- `D_net (raw)`: medidor crudo (en Udenar incluye los valores negativos).
- `D_bruta (input EMS)`: tras reconstrucción/clip — lo que recibe el EMS.
- `G_ems  (input EMS)`: inversor único expuesto al EMS.
- `G_recon (suma 3inv)`: solo Udenar — fuente de verdad de la inyección que el net meter descontó.

Bloque diagnóstico Udenar: número de horas D_net<0, horas clipeadas a 0 tras la suma, delta de energía kWh(D_bruta) − kWh(max(D_net,0)) y razón delta/G_recon (no es 1.0 porque la mayor parte de la generación cancelaba consumo > 0 sin cruzar a exportación).

### Archivos tocados

- **Nuevo**: `data/preprocessing.py` (núcleo del refactor; expone `build_demand_generation`, `DEMAND_METER_CONFIG`, `EMS_INVERTER_CONFIG`, `RECONSTRUCTION_INVERTERS_CONFIG`).
- **Modificado**: `data/xm_data_loader.py` (`_clean()` ya no trata negativos como NaN; `MTEDataLoader.load()` ahora delega en `build_demand_generation`; `_aggregate` queda como legacy).
- **Reescrito**: `outputs/audit_clean.py` (audita selección puntual + bloque diagnóstico Udenar).
- **Nuevo**: `tests/test_preprocessing.py` (7 tests del contrato).

---

*Última actualización manual: 2026-04-25 — sección §3.1 agregada; UCC revisado a Med 1 (totalizador completo); auditoría exhaustiva 27 fuentes; **migración a `MedicionesMTE_v3`** (16 meses de datos) con horizonte sólido Abr 4 → Dic 16 (6144 h, 256 días, +52 % vs Jul-Dic); Mariana y UCC migrados a `net_partial`; Udenar EMS migrado a Fronius 1; loader soporta CSVs particionados (3 archivos por medidor)*
*Este archivo es permanente — editarlo directamente, no auto-generado*

---

## §A.8 — Auditoría visual de figuras (2026-04-27)

Tras el ciclo end-to-end del 2026-04-27 se realizó una auditoría visual de las
24 figuras PNG generadas usando 6 sub-agentes Claude (Explore) en paralelo.
Cada agente revisó 4 figuras contra tres criterios: legibilidad visual, valor
narrativo y trazabilidad con la propuesta de tesis. La consolidación de
hallazgos se discutió con el usuario en 11 rondas y produjo el plan de
auditoría implementado a continuación.

### Resultados consolidados (23 figuras finales)

| Acción | Figuras |
|---|---|
| **KEEP sin cambios** (11) | fig1, fig4, fig5, fig7, fig9, fig12, fig13, fig15, fig17, fig20, fig21 |
| **Regenerada** (1) | **fig3** — heatmap día×hora (256×24) + boxplot precios + indicador horas activas. Reemplaza el scatter ilegible de 1 031 puntos etiquetados. |
| **Renombradas** (2) | **fig11_convergencia_h\*** → **fig22_convergencia_h\*** (h0013, h0683). Libera el prefijo `fig11` para `fig11_sensibilidad_pgs` (SA-3). |
| **Nueva** (1) | **fig23_perfiles_diarios** — porta `fig_perfiles_DG_actualizados.png` (huérfano sin código) al pipeline `plots.py` con sibling .csv/.mat. |
| **Eliminada** (1) | `fig_perfiles_DG_actualizados.png` — reemplazada por fig23 con trazabilidad correcta. |
| **IMPROVE** (6) | fig6 (panel doble: absoluto + ventaja P2P−C4 por agente), fig10 (corrección título "SA-3"→"SA-PPA"), fig14 (definición operacional de dominancia ±966 COP/h), fig16 (etiquetas X horizontales, abreviadas Lab-/Fin-), fig18 (etiqueta "perfil sintético 24 h" + anotación gráfica de RPE máximo), fig19 (panel doble absoluto + normalizado %B_alt — resuelve aplastamiento por curva Udenar). |
| **Fix global** | `plt.rcParams`: titlesize 11→13, labelsize 10→12, ticks heredados→11. Mejora legibilidad en las 23 figuras simultáneamente. |

### Lección sobre confiabilidad de los sub-agentes

Tres alucinaciones numéricas detectadas durante la auditoría que **no** son
problemas reales de las figuras:

1. **Agente sobre fig15**: citó "Udenar C1 = 85.5 MCOP vs C4 = 62.5 MCOP" cuando
   los valores reales del CSV son **8.59 MCOP y 6.19 MCOP** (factor 10× off, decimal corrido).
2. **Agente sobre fig17**: reportó "3/5 agentes AGRC compliant" cuando el CSV muestra
   **5/5 compliant** (`AGRC_compliant=True` en todas las filas).
3. **Agente sobre fig19**: citó "+3 473 COP de Udenar" como evidencia de incongruencia
   con el CSV. El número **no existe en el reporte actual**; fue alucinado.

**Conclusión metodológica:** los sub-agentes Claude inspeccionando imágenes
son confiables para **detectar problemas visuales** (legibilidad, paneles
densos, conflictos de naming, redundancias) pero **NO** para verificar
precisión numérica. De 6 agentes, 3 introdujeron al menos un dato incorrecto
(50 % tasa de error en cifras específicas). Toda decisión que dependa de un
valor numérico citado por un agente debe **cruzarse manualmente con el CSV/.mat**
antes de actuar.

### Tiempos reales del ciclo (2026-04-27, post-auditoría)

| Etapa | Tiempo |
|---|---|
| Backup defensivo | 1 min |
| Edición de código (rcParams + 7 funciones) | ~2 h |
| Run `--data real --full --analysis` | 48.7 min |
| Validación pytest 33/33 | 1 min 52 s |
| Smoke loadmat/read_csv (17 .mat + 52 .csv) | 1 s |

### Inventario final de figuras (`graficas/`)

24 PNGs activos con sus siblings:
- fig1–fig10 (10 figs principales)
- fig11_sensibilidad_pgs (SA-3 retoma el slot fig11)
- fig12–fig17 (6 figs principales)
- fig18 (sweep 2D PGB×PV) — depende de `outputs/sensitivity_2d_pgb_pv.parquet`
- fig19 (deserción individual, panel doble)
- fig20 (Price of Fairness Bertsimas 2011)
- fig21 (robustez C4 por agente)
- **fig22_convergencia_h0013, fig22_convergencia_h0683** (renombradas)
- **fig23_perfiles_diarios** (nueva, Act 3.1)

Plus 17 archivos .mat (uno por figura con datos persistidos) y 52 archivos
.csv (siblings por serie cuando los shapes son heterogéneos).

