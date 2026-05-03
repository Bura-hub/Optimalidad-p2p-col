# Capitulo 5 — Discusion regulatoria (BORRADOR)

> **Aviso al autor:** este borrador fue sintetizado a partir de los
> ADRs 0001-0024 y `Documentos/notas_modelo_tesis.md` (§§CAL-9 a CAL-18).
> Cada seccion cita la resolucion CREG / ley aplicable y la
> implementacion en codigo. Los placeholders `[NARRATIVA]` indican
> los puntos donde el autor humano debe escribir interpretacion
> academica final con citas bibliograficas.
>
> **Sesion:** Sprint 5.4 del plan
> `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` · 2026-05-02
> **Destino esperado:** copiado/editado a `Documentos/FinalTesis/`
> (otro repositorio, no commitear desde SistemaBL).

---

## 5.1 Marco normativo colombiano del mercado electrico

### 5.1.1 Jerarquia normativa relevante

El analisis comparativo P2P vs escenarios regulatorios se asienta
sobre la siguiente cadena normativa:

| Nivel | Norma | Aplicabilidad sobre el modelo |
|-------|-------|------------------------------|
| Constitucion | Art. 365, 366 (servicios publicos) | Marco general |
| Ley | **Ley 142/1994** (servicios publicos domiciliarios) | Tarifas reguladas, regimen subsidios/contribuciones |
| Ley | **Ley 143/1994** art. 41 (sector electrico) | Autorizacion contratos bilaterales (PPA) |
| Ley | **Ley 1715/2014** art. 19 | Crea FAZNI (cargo MEM no-regulado) |
| Ley | **Ley 1117/2006** art. 2 (prorrogada Ley 2099/2021 art. 45) | Contribucion 4 % sobre Gm |
| Decreto | **Decreto 388/2007** | Reglamenta usuario no-regulado |
| Decreto | **Decreto 2236/2023** | Comunidades energeticas (autogeneracion colectiva) |
| Resolucion CREG | **CREG 086/1996** mod. **CREG 039/2001** | Define usuario no-regulado (>= 55 MWh/mes o >= 100 kW) |
| Resolucion CREG | **CREG 119/2007** | Estructura del CU (G + T + D + Cvm + PR + R) |
| Resolucion CREG | **CREG 156/2012** | Representante en MEM |
| Resolucion CREG | **CREG 174/2021** | Excedentes AGPE (Tipo 1 / Tipo 2 + Cvm) |
| Resolucion CREG | **CREG 101-028/2023** | Cargo COT (Operador Telematico) |
| Resolucion CREG | **CREG 101 066/2024** | Tope PES sobre PTB (precio bolsa) |
| Resolucion CREG | **CREG 101 072/2025** | Reglamenta Decreto 2236 (PDE, AGRC) |

### 5.1.2 Estructura del Costo Unitario CU (CREG 119/2007)

El CU que paga un usuario regulado se descompone en seis componentes
liquidados por cada kWh consumido:

```
CU = G + T + D + Cvm + PR + R
```

| Componente | Descripcion | Unico negociable via PPA |
|-----------|-------------|:---:|
| **G** (Generacion) | Costo energia mayorista | Si (Ley 143/1994 art. 41) |
| **T** (Transmision STN) | Peaje SIN | No |
| **D** (Distribucion OR) | Peaje SDL | No |
| **Cvm** (Comercializacion) | Margen comercializador | No (regulado) |
| **PR** (Perdidas) | Reconocidas tecnicamente | No |
| **R** (Restricciones) | Operacion segura | No |
| **COT** (Operador Telematico, post-CREG 101-028/2023) | Cargo telematico | Discutido |

[NARRATIVA — desarrollar como esta estructura subyace a la
distincion C1 vs C2 vs P2P. Citar texto literal CREG 119/2007 arts.
6-13.]

---

## 5.2 Analisis por escenario regulatorio

### 5.2.1 C1 — CREG 174/2021 (Autoconsumo individual AGPE)

**Marco:** CREG 174/2021 reglamenta los AGPE (Auto-Generadores a
Pequena Escala). El art. 22 distingue dos tipos de excedentes y el
art. 25 fija su valoracion:

- **Excedentes Tipo 1** (intercambio fisico mes a mes): el usuario
  recibe credito por la energia inyectada y descuenta el consumo
  posterior dentro del mes; el comercializador cobra solo el
  componente Cvm,i,j sobre la energia permutada.
- **Excedentes Tipo 2** (residual mensual): la energia que no se
  consumio queda como saldo y se liquida al precio de bolsa
  (PTB hora a hora).

**Implementacion en C1** (`scenarios/scenario_c1_creg174.py`,
ADR-0010 CAL-10):

```
savings_m = E_auto * pi_gs[m] + E_permutada_t1 * (pi_gs[m] - Cvm[m])
revenue_m = E_t2[k] * pi_bolsa[k]   (post hora Hx)
```

La hora `Hx` es el "cruce" mensual: el momento en que la inyeccion
acumulada excede el retiro acumulado y los excedentes posteriores
clasifican como Tipo 2.

**ADRs aplicables:**

- ADR-0010 (CAL-10) - implementacion Tipo 1/2 + componente C.
- ADR-0010 §"CAL-10b.2" - correccion de literalidad: solo Cvm,i,j
  puro (no Cvm + COT). El cargo COT introducido por CREG 101-028/2023
  no se descuenta en la permuta segun la letra del art. 25.

[NARRATIVA — discutir el balance entre proteccion al consumidor
regulado (Cvm cobrado al permutar) y el incentivo a la generacion
distribuida (no se cobra G).]

### 5.2.2 C2 — Ley 143/1994 art. 41 (PPA bilateral usuario no-regulado)

**Marco:** la Ley 143/1994 art. 41 autoriza contratos bilaterales
de suministro entre **usuarios no-regulados** y generadores. Para
calificar como no-regulado, el usuario debe superar el umbral de
**55 MWh/mes** o **100 kW** instalados (CREG 086/1996 art. 1, mod.
CREG 039/2001). Las cinco instituciones MTE califican.

**Particularidad clave:** el usuario no-regulado **no tiene
comercializador minorista**. En cambio, contrata un **representante
en el MEM** (CREG 156/2012) y participa directamente en el mercado
mayorista, asumiendo:

- Cargo FAZNI (Ley 1715/2014 art. 19): ~1,90 COP/kWh
- Contribucion 4 % sobre Gm (Ley 1117/2006 + Ley 2099/2021): ~12 COP/kWh
- Comision representante: ~2,00 COP/kWh

**Total MEM ~15,90 COP/kWh** (~3 % del componente G), validado en
ADR-0022 con trazabilidad celda-fuente en `data/mem_costs_audit.md`.

**Implementacion en C2** (`scenarios/scenario_c2_bilateral.py`,
ADR-0011, 0012, 0013, 0016):

```
savings_PPA = savings_G + savings_Cvm + alpha_COT * savings_COT
              + alpha_CXC * savings_CXC - mem_costs
```

donde:
- `savings_G = E_PPA * (G - pi_ppa)` (descuento componente G)
- `savings_Cvm = E_PPA * Cvm` (no paga comercializador minorista)
- `savings_COT = E_PPA * COT * cot_alpha` (cota legal `cot_alpha = 1`)
- `savings_CXC = E_PPA * CXC * cxc_alpha` (cota conservadora
  `cxc_alpha = 0`)
- `mem_costs = E_PPA * (FAZNI + 0.04 * G + pi_repr)`

**Ambiguedades regulatorias resueltas:**

| Componente | Cota | Justificacion | ADR |
|-----------|------|---------------|-----|
| `f` (split factor PPA) | 0,5 | Egalitaria por simetria; teorema invarianza demostrado | 0021 |
| `cot_alpha` | 1,0 | CREG 086/1996: usuario no-regulado no tiene comercializador minorista | 0020 |
| `cxc_alpha` | 0,0 | Practica industrial PPAs colombianos (CXC sigue cobrandose en peajes) | 0023 |

[NARRATIVA — discutir la legitimidad del esquema PPA bilateral como
alternativa a P2P para usuarios institucionales. Comparar con
literatura: Sorin et al. 2019, Tushar et al. 2020.]

### 5.2.3 C3 — CREG 101 066/2024 (Mercado spot con techo PES)

**Marco:** la CREG 101 066/2024, vigente desde **01-DIC-2024**,
establece que el **Precio de Transacciones en Bolsa (PTB)** no
puede exceder el **Precio de Escasez Superior (PES)** publicado
mensualmente por XM. Antes de esta resolucion, el PTB podia
exceder el PES en horas con activacion de Obligaciones de Energia
Firme (OEF).

**Distincion PB vs PTB** (relevante para el modelo):

- **PB** (Precio de Bolsa): precio marginal de oferta sin
  modificaciones. Es lo que devuelve la API `pydataxm.PrecBolsNaci`.
- **PTB** (Precio de Transacciones): precio efectivo tras
  activacion OEF, capado a PES. Es lo que se liquida realmente.

El cache `data/precios_bolsa_xm_api.csv` contiene PB; CAL-14
(ADR-0014) implementa `apply_creg101066_ceiling` que aproxima PTB
mediante `min(PB, PES_mes)`. Sobre 7 272 h cubiertas, 12 horas
fueron recortadas (0,23 % del horizonte) con delta acumulado de
3 676 COP/kWh.

**Auditoria CAL-17 (ADR-0017):** la metrica `PrecBolsNaci` fue
verificada contra los siete informes mensuales oficiales XM con
tolerancia 10 %; sesgo medio firmado de -1,81 % (no sistematico).
La diferencia residual se explica por la asimetria metodologica
**aritmetica vs ponderada por demanda** que XM publica.

**Implementacion en C3** (`scenarios/scenario_c3_spot.py`):

```
revenue[k] = surplus[k] * pi_bolsa[k]   (con apply_ceiling=True default)
```

[NARRATIVA — discutir la robustez del modelo: el techo PES protege
al modelo contra picos artificiales; la auditoria explicita
certifica que la metrica de pydataxm es defendible.]

### 5.2.4 C4 — Decreto 2236/2023 + CREG 101 072/2025 (Comunidades energeticas)

**Marco:** el Decreto 2236/2023 art. 4 establece que cada miembro
de un esquema AGRC (Auto-Generador y Auto-Consumidor de Energias
Renovables Colectivo) se liquida **bajo el regimen AGPE**
(CREG 174/2021). Por linealidad regulatoria, C4 hereda los
mecanismos Tipo 1 / Tipo 2 de C1.

**Particularidades CREG 101 072/2025 art. 5:**

- **PDE** (Porcentaje de Distribucion de Excedentes): credito
  intracomunitario asignado proporcionalmente a la capacidad
  instalada de cada miembro.
- **Permuta intracomunitaria** (Tipo 1): valorada a `pi_gs - Cvm,i,j`
  como en C1.
- **Excedente residual** (Tipo 2): liquidado al `pi_bolsa[k]`
  horario.
- **Limite individual:** ningun miembro puede tener > 10 % de
  capacidad sin restricciones; en MTE las cinco instituciones
  cumplen.

**Implementacion en C4** (`scenarios/scenario_c4_creg101072.py`,
ADR-0011 CAL-15):

```
inyeccion_total[k] = sum_n surplus[n,k]
credit[n,k] = pde[n] * inyeccion_total[k]
permuta_t1[n,k] = min(credit[n,k], deficit[n,k])
excedente_t2[n,k] = max(credit[n,k] - deficit[n,k], 0)

savings[n] = sum_k autoconsumo * pi_gs +
              sum_k permuta_t1 * (pi_gs - Cvm) +
              sum_k excedente_t2 * pi_bolsa
```

[NARRATIVA — discutir como la herencia formal de CREG 174 (reciente
en CAL-15, 2026-05-01) cambia significativamente las conclusiones:
C4 sube +4,03 % vs el calculo legacy `pde_only` que silenciaba la
exportacion Tipo 2 a bolsa. RPE P2P-vs-C4 cae de +0,03 a +0,004 —
diferencia marginal pero coherente con la teoria.]

---

## 5.3 P2P frente al marco regulatorio colombiano

### 5.3.1 Posicion regulatoria del P2P

El esquema P2P implementado en este trabajo (Stackelberg + dinamica
de replicador, basado en Chacon et al. 2025) **no esta explicitamente
contemplado en la regulacion colombiana vigente**. Sin embargo,
puede interpretarse como:

1. **Variante mas eficiente del esquema AGRC** (CREG 101 072/2025):
   reemplaza el PDE estatico (proporcional a capacidad) por una
   asignacion dinamica derivada del juego de mercado.
2. **Generalizacion del PPA bilateral** (Ley 143/1994 art. 41):
   N contratos bilaterales simultaneos resueltos por un
   coordinador de mercado.

[NARRATIVA — discutir las implicaciones legales: el modelo P2P es
admisible bajo el marco actual si se enmarca como un esquema AGRC
con PDE dinamico, sujeto a reglamentacion por la CREG.]

### 5.3.2 Comparacion cuantitativa

Sobre el horizonte abr-dic 2025 (6 144 h MTE, 5 instituciones):

| Escenario | Ganancia neta (MCOP) | Δ vs P2P [%] | Marco regulatorio dominante |
|-----------|---------------------:|------------:|----------------------------|
| **P2P** | **52,45** | — | Sin marco explicito; combinacion AGRC + bilateral |
| C1 | 52,47 | +0,03 | CREG 174/2021 art. 22-25 |
| C2 | 51,44 | -1,93 | Ley 143/1994 art. 41 + CREG 086/1996 |
| C3 | 50,77 | -3,20 | CREG 101 066/2024 (PTB con techo PES) |
| C4 | 52,22 | -0,43 | Decreto 2236/2023 + CREG 101 072/2025 |

**Lectura clave:** P2P **empata con C1** en bienestar agregado
(diferencia 0,03 %, dentro del ruido numerico) pero supera a C2,
C3 y C4 en distintos margenes. La distribucion intracomunitaria
varia (Gini P2P 0,162 vs C1 0,147), reflejando que el P2P
internaliza la negociacion de precios y deja una cola de
beneficiarios distinta.

### 5.3.3 Potencial regulatorio del P2P para Colombia

[NARRATIVA — desarrollar:
- ¿Que cambios normativos requeriria el P2P para ser legalmente
  vigente? (e.g. permitir PDE dinamico bajo CREG 101 072.)
- ¿Que entidades deberian ser comercializadores P2P? (CREG, XM,
  representantes MEM.)
- ¿Como interactua con la transicion energetica nacional 2050
  (Mision Crecimiento Verde)?]

---

## 5.4 Limitaciones del modelo respecto al marco regulatorio

### 5.4.1 Simplificaciones documentadas

| Limitacion | Documentada en | Mitigacion |
|-----------|---------------|------------|
| Aproximacion `min(PB, PES)` ignora composicion horaria del despacho OEF | ADR-0014 §"Negativas" | Cap PES es cota superior conservadora |
| `cot_alpha = 1,0` cota legal (no empirica) | ADR-0020 | Default 1,0 inerte si `consumer_ids = []` |
| `cxc_alpha = 0,0` cota conservadora (no empirica) | ADR-0023 | Parametrizable opt-in para sensibilidades |
| `f = 0,5` postulado normativo | ADR-0021 | Teorema invarianza protege metrica principal |
| Comision representante 2,00 COP/kWh referencial (no contractual) | ADR-0022 | Banda mercado [1,5; 3,0]; auditable |

### 5.4.2 Brechas regulatorias no cubiertas

[NARRATIVA — desarrollar:
- Tarifas dinamicas (Time-of-Use, real-time pricing): no modeladas;
  CREG 015/2018 las contempla pero el horizonte MTE no las usa.
- Beneficios tributarios Ley 1715/2014: no modelados (IVA, renta,
  retenciones); analisis comparativo P2P-vs-regulado es neutral
  a impuestos.
- Modalidad Take-or-Pay PPA: no modelada (CAL-11 spec § out-of-scope);
  requiere modelar curva de generacion solar pura nocturna como
  imposible -> contrato marca cero.
- Cargo CXC efectivo en C2: documentado como CAL-23 opt-in; default
  0,0 reproduce practica industrial.]

### 5.4.3 Ambiguedades regulatorias documentadas

[NARRATIVA — desarrollar:
- COT en C2: CREG 174 art. 25 no menciona COT explicitamente; CAL-20
  parametriza como `cot_alpha`.
- CXC en C2: CREG 101 072/2025 (autogen colectiva) no menciona CXC;
  CAL-23 parametriza como `cxc_alpha`.
- PB vs PTB efectivo: la metrica `PrecBolsNaci` es PB marginal, no
  PTB liquidado; CAL-14 + CAL-17 documentan la aproximacion via
  techo PES.]

---

## 5.5 Recomendaciones de politica publica

### 5.5.1 Para la CREG

[NARRATIVA — desarrollar:
1. Reglamentar PDE dinamico (no solo proporcional a capacidad) en
   esquemas AGRC, habilitando explicitamente mecanismos de mercado.
2. Aclarar la aplicabilidad del CXC a usuarios no-regulados bajo
   PPA bilateral.
3. Publicar PTB efectivo (post-OEF) directamente en pydataxm para
   eliminar la asimetria PB vs PTB.
4. Estandarizar reportes de comision representante MEM (ASOCODIS)
   para reducir la dispersion observada [1,5; 3,0] COP/kWh.]

### 5.5.2 Para el sector academico

[NARRATIVA — desarrollar:
1. Consolidar la literatura sobre P2P energetico colombiano: Salazar
   et al. 2024, Pardo et al. 2023.
2. Validar empiricamente el postulado `f = 0,5` con contratos PPA
   reales colombianos (CAL-21 mostro rango disperso [-3,08; +0,029]
   en 4 contratos publicos).]

### 5.5.3 Para los AGPE/AGRC

[NARRATIVA — desarrollar:
- Bajo el horizonte MTE actual, P2P aporta ganancia distributiva
  marginal vs C1 individual; C4 colectivo tambien es competitivo.
- La cobertura PV de la comunidad MTE (19 % agregada) limita el
  espacio de mejora; con cobertura 30-44 % (SA-2) la actividad P2P
  satura.]

---

## 5.6 Sintesis de la discusion

[NARRATIVA — desarrollar parrafos finales:
- Resumen de hallazgos en clave regulatoria (P2P es admisible bajo
  marco AGRC ampliado).
- Trazabilidad: cada decision del modelo se mapea a un ADR
  formalizado con fuente regulatoria explicita (24 ADRs CAL-1..24).
- Validador swarm CAL-24 reporta PASS 15/15 sobre el repo actual.
- Limitaciones documentadas como sensibilidades parametrizables
  (`f`, `cot_alpha`, `cxc_alpha`), permitiendo defender el modelo
  ante variantes interpretativas.]

---

## Anexos a este borrador

- **Tablas y figuras:** referencias cruzadas a `graficas/` y a
  `docs/adr/` para tablas regulatorias.
- **Apendice A (Lista de ADRs):** indice completo en
  `docs/adr/README.md` (24 ADRs).
- **Apendice B (Validador regulatorio):** `python
  scripts/swarm_regulatory_validator.py` (CAL-24).
- **Apendice C (Auditoria de datos):** `data/mem_costs_audit.md`,
  `data/audit_pydataxm_horizon.csv`.

---

**Verificaciones pendientes antes de copiar a `Documentos/FinalTesis/`:**

1. Citar autores correctos en las recomendaciones de politica publica.
2. Verificar que todas las leyes/decretos citados estan vigentes a
   la fecha de defensa (revisar gestornormativo.creg.gov.co).
3. Reescribir todos los `[NARRATIVA — ...]` con texto del autor
   y citas bibliograficas BibTeX.
4. Cruzar verificacion cuantitativa con §4.9 del capitulo 4
   (resultados deben coincidir).

---

## §5.7 — Discusión regulatoria: subset paper IEEE WEEF 2026

Esta sección extiende §5.2 con la lectura regulatoria del subset
paper (CAL-25..29). Las cifras y trazabilidad se documentan en
`borrador_cap4_resultados.md` §6.5.

### §5.7.1 Naturaleza del offset común

El paper confirma con sub-medidores (CAL-28, cobertura 96 %) la
hipótesis del asesor expresada en `Reunion0105.txt` líneas 414-462:
**el ahorro por autoconsumo (3.60 M COP en agosto-2025) es físicamente
idéntico en P2P, C1 y C2**. La energía que nunca atraviesa la frontera
del sitio del prosumidor no es objeto de regulación CREG: `pi_gs`
completo aplica como ahorro implícito.

Esta simetría no es trivial: en la simulación pre-CAL-29 el offset
P2P aparecía como 2.64 M COP (solo horas con mercado activo) — un
artefacto de implementación que ocultaba la equivalencia física. La
fórmula canónica de CAL-29 restaura la simetría y permite afirmar
sin ambigüedades que **los tres escenarios solo se diferencian en
qué pasa con el excedente**.

### §5.7.2 Diferenciador regulatorio: la valoración del excedente

Ya con el offset común aislado, las ventas de excedentes en
agosto-2025 se distribuyen así (M COP):

- **C1 (CREG 174)**: 1.35 M, vía Tipo 1 a `(pi_gs − Cvm) ≈ 600
  COP/kWh` y Tipo 2 a `pi_bolsa[k] ≈ 234`.
- **C2 (CREG 101 072)**: 0.98 M, mismo mecanismo Tipo 1/Tipo 2
  pero sobre el balance comunitario agregado vía PDE
  (`capacity_proportional`).
- **P2P**: 1.21 M, vía price discovery Stackelberg
  (`pi_star ∈ [pi_gb, pi_gs]`) sobre la fracción transada
  internamente (525.88 kWh, 12 % del excedente total) y `pi_bolsa[k]`
  sobre el residual (88 % del excedente).

C1 supera a P2P por 142 K COP debido a la diferencia entre
`pi_gs − Cvm` (Tipo 1) y `pi_star` para los kWh que crucen Hx en C1.
P2P supera a C2 porque el price discovery interno extrae un spread
que el PDE comunitario administrativo no puede capturar.

### §5.7.3 Phase transition: P2P óptimo a partir de PV factor ≥ 1.5

El barrido PV revela el aporte estructural del mercado P2P en
escenarios de mayor penetración solar:

- A 96 % cobertura (1.0×): P2P rank 2, marginalmente bajo C1.
- A ≥ 144 % cobertura (≥ 1.5×): **P2P se vuelve óptimo absoluto**,
  superando ambos esquemas regulatorios CREG.

La interpretación regulatoria es directa: cuando la comunidad alcanza
sobre-generación estructural, el mecanismo administrativo de
permuta-más-bolsa (compartido por C1 y C2) deja eficiencia sobre la
mesa. El P2P captura esa eficiencia vía price discovery dinámico.

Esto sugiere que la elección regulatoria de Colombia entre CREG 174
(individual) y CREG 101 072 (colectivo) no es ortogonal a la velocidad
de despliegue solar: ambos se vuelven sub-óptimos simultáneamente
cuando la comunidad supera 144 % cobertura. Bajo el plan UPME
2025-2039, este umbral es alcanzable en comunidades educativas
universitarias en horizonte 5-10 años.

### §5.7.4 Heterogeneidad por agente y adopción

A nivel agente individual (CAL-29 per-agent breakdown):

- **Udenar, HUDN, Cesmag** (3/5): prefieren P2P sobre C1 individualmente.
- **Mariana, UCC** (2/5): prefieren C1.

La heterogeneidad se explica por el perfil generación/demanda. UCC
tiene la cobertura más baja (alta demanda) y se beneficia más del
crédito Tipo 1 a `pi_gs − Cvm` que del trading P2P (donde es
predominantemente comprador). Cesmag, con perfil más equilibrado,
gana 246 K COP adicionales cuando puede vender a sus pares.

**Implicación de adopción**: una decisión regulatoria sobre P2P no
debería ignorar esta heterogeneidad. Comunidades con perfiles diversos
generan ganadores y perdedores entre mecanismos; un esquema mixto
(opcional) podría ser preferible a un mandato uniforme.

### §5.7.5 Limitaciones y trabajo futuro

La conclusión del paper se sostiene bajo:

1. Un mes (agosto-2025), 5 instituciones (N=5 pequeño).
2. Cobertura 96 % obtenida vía sub-medidores M3 (paper-only).
   El cap. 4 §6.4 mantiene el escenario tesis (cobertura 19 % con
   M1 totalizador) donde P2P-vs-C4 da `RPE = +0.43 %`, también
   favorable.
3. Sin demand response (`alpha=0`).
4. PV factor ≥ 1.5× ilustrativo, no realista para edificios
   comerciales actuales.

CAL-30 (Sprint 7 post-paper) migrará el engine de la tesis a la
fórmula canónica para re-evaluar capítulo 4 completo. El cambio
es esperable: invariante en signo (P2P sigue ganando RPE) pero
con magnitud actualizada en agregado.
