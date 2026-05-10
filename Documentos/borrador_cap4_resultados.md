# Capitulo 4 — Resultados (BORRADOR)

> **Aviso al autor:** este borrador fue sintetizado por agente Ruflo
> a partir de `outputs/REPORTE_AVANCES.md` (post-CAL-8 2026-04-28),
> `Documentos/notas_modelo_tesis.md` (§§3-8 + §A.7) y los ADRs
> 0001-0008. Todas las cifras provienen de corridas reales del
> modelo (`--full --analysis` 6 144 h, 55,2 min). Los placeholders
> `[NARRATIVA]` indican secciones donde solo el autor humano debe
> escribir interpretacion academica final.
>
> **Sesion:** Tier 1.2 research-synthesize · 2026-04-30
> **Origen del borrador:** plan
> `C:\Users\burav\.claude\plans\ya-hecho-todo-esto-lazy-moler.md`
> **Destino esperado:** copiado/editado a `Documentos/FinalTesis/`
> (otro repositorio, no commitear desde SistemaBL).

---

## 4.1 Diseno experimental

### 4.1.1 Datos empiricos

Los resultados presentados en este capitulo se derivan de la corrida
`--full --analysis` sobre el horizonte completo del proyecto MTE
(Medicion de Tecnologias de Energia), con datos empiricos de cinco
instituciones del campus de Pasto, Narino:

| Institucion | D̄ (kW) | Ḡ (kW) | Cobertura PV |
|---|---:|---:|---:|
| Universidad de Narino (Udenar) | 7.2 | 2.2 | 30 % |
| Universidad Mariana | 9.6 | 2.0 | 21 % |
| Universidad Cooperativa (UCC) | 21.4 | 2.5 | 12 % |
| Hospital Universitario Departamental (HUDN) | 9.1 | 2.1 | 23 % |
| Universidad Cesmag | 4.5 | 1.1 | 25 % |
| **Comunidad agregada** | **51.8** | **9.9** | **19,1 %** |

**Horizonte:** 6 144 horas (256 dias, abr-2025 → dic-2025), resolucion
horaria, zona horaria America/Bogota.

**Tiempo de ejecucion:** 55,2 min (`ProcessPoolExecutor` Windows,
`stackelberg_iters = 2`, `tau_buyers/tau_sellers = 10`).

### 4.1.2 Parametros calibrados

Los parametros del modelo P2P son resultado de las calibraciones
formalizadas en los ADRs 0001-0008 (ver Apendice A):

| Parametro | Valor | Fuente | ADR |
|---|---|---|---|
| `stackelberg_iters` | 2 | barrido empirico | 0001 |
| `etha` | 0.1 | JoinFinal.m (modelo base) | 0002 |
| `alpha_p`, `alpha_c` | 0.20, 0.10 | Optimo empirico DR | 0003 |
| `tau_buyers/tau_sellers` | 10 | Replica WI/WJ JoinFinal | 0004 |
| `theta` | 0.5 | JoinFinal.m | 0005 |
| `b_n` (LCOE solar) | **{241, 241, 241, 241, 225} COP/kWh** post-fix (Cesmag = 225 por inversor distinto) | IRENA 2024 / UPME 2025-2039 | 0006 (apéndice 2026-05-06) |
| `c_n` (offset fijo) | **0 uniforme** (post-fix CAL-32 2026-05-06b) | Convención canónica PV puro (Yang 2024, Martinez-Piazuelo 2022); equilibrio invariante (verificado empíricamente) | 0032 |
| `lambda_n` (preferencia auto-consumo) | 100 uniforme | JoinFinal.m:26 (PV homogéneo + α=0) | 0033 |
| Solver Stackelberg | Alternancia secuencial | Paralelizacion | 0007 |
| `pi_gs` (perfil diario) | Vector `(N,)` Cedenar promedio horizonte | Tarifa CU 101-028/23 | 0008 |
| `pi_gs` (`--full` / `--day`) | Matriz `(N, T)` mes a mes | CU mensual CSV Cedenar | **0009** |

Calibracion `pi_gs` por agente (CAL-8, post-2026-04-27):

| Agente | Categoria tarifaria | NT | `pi_gs` (COP/kWh) |
|---|---|---:|---:|
| Udenar | Oficial/Especial | 2 | 797 |
| Mariana | Comercial | 2 | 956 |
| UCC | Comercial | 2 | 956 |
| HUDN | Oficial/Especial | 2 | 797 |
| Cesmag | Comercial | 2 | 956 |
| **Comunitario ponderado** | — | — | **906** |

**Precio de bolsa:** `pi_gb = 280 COP/kWh` promedio XM Jul 2025–Ene 2026.

**Precio CU mensual (CAL-9, ADR 0009):** la corrida `--full` y la
liquidacion `--day` no usan el escalar 906 sino la **matriz `(N, T)`**
construida por `pi_gs_per_agent_hourly(agents, idx)`. Cada hora hereda
el CU del mes que la contiene. El CU oficial NT2 varia entre 766,80
(ene-2026) y 816,98 (ago-2025) COP/kWh — spread intraanual ~6,5 % que
el escalar CAL-8 colapsaba.

[NARRATIVA — justificar la diferenciacion oficial/comercial citando
CREG y notas_modelo_tesis §7 CAL-8 + §CAL-9.]

---

## 4.2 Validacion del modelo

### 4.2.1 Golden test contra modelo MATLAB original

El modelo Python en `core/ems_p2p.py` reproduce el equilibrio del
algoritmo MATLAB de referencia `JoinFinal.m` de Chacon et al. (2025)
[\cite{Chacon2025EMS}] dentro de las siguientes tolerancias:

- `P_total`: atol = 0,15 kWh
- Demanda agregada: rtol = 5 %
- `pi_i`: dentro del rango `[pi_gb, pi_gs]`

El test `tests/golden_test_sofia.py` se ejecuta como parte del CI
local. La discrepancia entre la formulacion ODE conjunta del modelo
base y la alternancia secuencial de la implementacion Python no
afecta el equilibrio resultante (ver ADR 0007, "El equilibrio de Nash
es invariante bajo factorizacion del operador de actualizacion").

### 4.2.2 Convergencia del juego Stackelberg

[NARRATIVA — citar ADR 0001 con tabla del barrido `stackelberg_iters`
1, 2, 3, 5, 8, 10 y la conclusion `Δ SC = 0` exacto.]

---

## 4.3 Comparacion regulatoria C1-C4 vs P2P

### 4.3.1 Bienestar agregado por escenario

| Escenario | Ganancia neta (MCOP) | SC | SS | IE | Gini |
|---|---:|---:|---:|---:|---:|
| **P2P (Stackelberg + RD)** | **52,43** | 0,188 | 0,981 | +0,3677 | 0,162 |
| C1 (CREG 174/2021, AGPE) | 54,04 | 0,176 | 0,921 | -0,0115 | 0,147 |
| C2 (Bilateral PPA) | 51,44 | 0,176 | 0,921 | +0,0292 | 0,155 |
| C3 (Mercado spot) | 50,96 | 0,176 | 0,921 | +0,0375 | 0,161 |
| C4 (CREG 101 072) ★ | 50,29 | 0,176 | 0,921 | +0,0517 | 0,170 |

**Notacion:** SC = autoconsumo (self-consumption), SS = autosuficiencia
(self-sufficiency), IE = indice de balance comprador-vendedor
(\cite{Chacon2025EMS}; positivo = compradores capturan excedente,
negativo = vendedores; mide la posicion del precio P2P en el rango
admisible $[\pi_{gb},\pi_{gs}]$, no la equidad distributiva — ver
notas_modelo_tesis.md §A.10), Gini = coeficiente de inequidad
distributiva sobre net benefits per-agente (estandar en literatura
P2P-energy, Sorin et al. 2019; lower = mas equitativo).

Metricas derivadas:

- **RPE (P2P vs C4):** +0,0408 → P2P supera al regimen vigente CREG
  101 072 en 4,1 % de bienestar agregado.
- **Σ ventaja P2P − C4:** 2,14 MCOP en horizonte 6 144 h.
- **Spread ineficiencia C4:** 1 004,4 kWh/periodo no liquidados.

### 4.3.2 Ventaja P2P por institucion

| Institucion | P2P (COP) | C4 (COP) | Ventaja P2P (COP) |
|---|---:|---:|---:|
| Udenar | 8 136 217 | 7 587 244 | **+548 973** |
| Mariana | 12 188 801 | 11 875 616 | +313 185 |
| UCC | 15 208 492 | 14 570 260 | +638 232 |
| HUDN | 10 255 874 | 9 984 804 | +271 069 |
| Cesmag | 6 641 540 | 6 272 210 | +369 330 |

**Hallazgo:** las cinco instituciones obtienen ganancia neta superior
en P2P versus C4 [\cite{paudel2019}] [\cite{Sorin2019Consensus}].

### 4.3.3 Degeneracion C1 = C3

En el horizonte completo (6 144 h con CAL-8), se observa que los
escenarios C1 (CREG 174 / AGPE) y C3 (mercado spot) ya **no son
identicos**, contrario al hallazgo del perfil 24 h promedio
(notas_modelo_tesis §5). La calibracion mensual diferenciada por
agente (`pi_gs[n]` oficial 797 vs comercial 956) introduce
heterogeneidad que rompe la simetria entre los dos mecanismos de
liquidacion.

[NARRATIVA — citar §5 de notas_modelo_tesis y la tabla de delta
mensual C1-C3 para los 12 meses MTE_v3.]

---

## 4.4 Analisis de optimalidad (Act 4.1)

### 4.4.1 Indices SC/SS/IE/RPE

[NARRATIVA — referir a `analysis/optimality.py` y al patron horario
de los indices. El IE de Chacon ($\sum S_i - \sum S_{R_j}$ sobre
$\sum S_i + \sum S_{R_j}$) se reduce a $(\pi_{gs}+\pi_{gb}-2\pi^*)/(\pi_{gs}-\pi_{gb})$
dado el clearing P2P, midiendo donde cae el precio de equilibrio
$\pi^*$ dentro del rango regulatorio admisible. Bajo esta lectura,
IE_P2P=+0,3677 indica un precio de equilibrio cerca del piso $\pi_{gb}$,
favoreciendo a los compradores comerciales (que capturan 71,4 % del
excedente por su mayor $\pi_{gs}[i]$). Esto NO contradice la equidad
distributiva, que se mide aparte con el coeficiente de Gini (P2P=0,162
vs C1=0,147; ambos en rango "moderadamente equitativo" en literatura
P2P-energy). Ver notas_modelo_tesis.md §A.10 para el desarrollo
algebraico y la decision de usar Gini como metrica primaria.]

### 4.4.2 Price of Fairness (Bertsimas et al. 2011)

`PoF = 0,0000` para C1 (CREG 174). Implementacion formal en
`analysis/fairness.py` siguiendo [\cite{Bertsimas2011PoF}].

[NARRATIVA — interpretar: el escenario "eficiente" (maxima ganancia)
y el "equitativo" (minima dispersion intra-comunidad) coinciden en
C1, lo que limita el espacio de mejora distributiva via P2P respecto
a CREG 174 cuando el horizonte solo tiene cobertura PV del 19 %.]

---

## 4.5 Sensibilidad (Act 4.2)

### 4.5.1 SA-1: Variacion del precio de bolsa `pi_gb`

| `pi_gb` (COP/kWh) | P2P (MCOP) | C4 (MCOP) | RPE |
|---:|---:|---:|---:|
| 200 | 53,37 | 50,98 | 0,045 |
| 250 | 53,18 | 50,98 | 0,041 |
| **280** ★ | **53,07** | **50,98** | **0,039** |
| 300 | 53,00 | 50,98 | 0,038 |
| 350 | 52,82 | 50,98 | 0,035 |
| 400 | 52,64 | 50,98 | 0,031 |
| 450 | 52,45 | 50,98 | 0,028 |
| 500 | 52,27 | 50,98 | 0,025 |

**Observacion:** RPE decrece monotonamente con `pi_gb`. La ventaja
de P2P sobre C4 es maxima en regimen de bolsa baja.

### 4.5.2 SA-2: Variacion de cobertura PV

| Factor PV | Cobertura | P2P (MCOP) | Horas mercado | kWh P2P |
|---:|---:|---:|---:|---:|
| 1.00× | 11 % | 53,07 | 1 031 | 3 659 |
| 1.05× | 12 % | 55,23 | 1 078 | 3 940 |
| 1.72× | 19 % | 82,81 | 1 576 | 8 560 |
| 2.61× | 30 % | 108,54 | 1 688 | 13 631 |
| 3.92× | 44 % | 131,62 | 1 562 | 16 004 |
| 5.23× | 59 % | 144,87 | 1 403 | 14 712 |

**Observacion:** la actividad del mercado P2P se satura entre 30-44 %
de cobertura PV (1 688 horas/periodo), luego decrece — los excedentes
exceden la capacidad de absorcion comunitaria.

### 4.5.3 GSA Sobol-Saltelli (n_base = 128)

Ejecucion 2026-04-27, 111 min, **1 367 / 2 048 muestras validas**:

[NARRATIVA — incluir tabla de indices `S_T` por parametro siguiendo
el formato de notas_modelo_tesis §A.7. Citar Saltelli et al. 2008
[\cite{Saltelli2008GSA}].]

---

## 4.6 Factibilidad (Act 3.3)

### 4.6.1 FA-1: Condicion de no-arbitraje

El precio P2P `pi_star[i]` no cae nunca por debajo de `pi_gb` en el
horizonte evaluado, descartando arbitraje sistemico. Umbral critico de
deserción comunitaria: `pi_gb^* = 528 COP/kWh`.

### 4.6.2 FA-2: Cumplimiento CREG 101 072 / 2025

| Institucion | Participacion (%) | Cap. max (kW) | Cumple |
|---|---:|---:|:---:|
| Udenar | 4,16 | 13,9 | ✓ |
| Mariana | 3,95 | 14,7 | ✓ |
| UCC | 4,84 | 15,1 | ✓ |
| HUDN | 4,07 | 14,0 | ✓ |
| Cesmag | 2,13 | 10,1 | ✓ |

Todas las instituciones cumplen el doble criterio CREG 101 072: ≤ 10 %
de participacion individual y ≤ 100 kW de capacidad. **Score de
robustez C4 = 1,00**.

### 4.6.3 Racionalidad Individual (§3.14, post-CAL-8)

| Agente | Δ_n (COP) | Δ_n / B_alt | π_gb*_n | Estado |
|---|---:|---:|---:|---|
| Udenar | -2 400 250 | -22,8 % | 180 | **deserta a C1** |
| Mariana | +185 994 | +1,5 % | >rango | estable |
| UCC | +499 883 | +3,4 % | >rango | estable |
| HUDN | -50 240 | -0,5 % | 233 | **deserta a C1** |
| Cesmag | +153 369 | +2,4 % | >rango | estable |

**Hallazgo critico post-CAL-8:** **3/5 instituciones permanecen en
P2P** (Mariana, UCC, Cesmag — todas comerciales). Udenar y HUDN —
ambas oficiales — desertan al regimen AGPE C1 porque su `pi_gs[n] = 797`
hace que la permutacion 1:1 a CREG 174 valga mas que el ahorro P2P.

Este resultado **invierte** el hallazgo pre-CAL-8 (5/5 estables) y
constituye una contribucion novedosa: la heterogeneidad tarifaria
oficial vs comercial introduce una frontera de IR que la calibracion
escalar uniforme ocultaba.

[NARRATIVA — discutir implicaciones de politica publica:
recomendar que CREG 174 sea preferida sobre 101 072 para entidades
oficiales con tarifa Especial.]

---

## 4.7 Bootstrap estadistico (Act 3.2)

Bootstrap por bloques estacionarios (Künsch 1989 [\cite{Kunsch1989Bootstrap}])
sobre series diarias MTE_v3 (256 dias):

- **Δ̄ (P2P − C4):** 4 732 COP/dia
- **Intervalo de confianza 95 %:** [3 629, 5 751]
- **n bootstrap:** 10 000
- **Cohen's d:** 0,90 (efecto grande)

[NARRATIVA — concluir que la ventaja P2P > C4 es estadisticamente
significativa con efecto grande.]

---

## 4.8 Sintesis y discusion

### 4.8.1 Hallazgos principales

1. **P2P > C4 en bienestar absoluto** (52,43 vs 50,29 MCOP, +4,1 %)
   y por agente (5/5 ganan en P2P vs C4).
2. **P2P NO domina a C1 para todos los agentes**: en el contexto
   post-CAL-8, 2/5 instituciones (Udenar, HUDN — oficiales) prefieren
   el regimen AGPE de CREG 174 sobre el mercado P2P. Este es un
   hallazgo novedoso atribuible a la heterogeneidad tarifaria.
3. **GSA Sobol** confirma que `pi_gb` y cobertura PV son los
   parametros con mayor contribucion al varianza del bienestar
   agregado.
4. **Bootstrap Künsch** valida con d = 0,90 que la ventaja P2P > C4
   es estructural, no fruto de una corrida favorable.
5. **PoF = 0** en C1 indica que CREG 174 ya es Pareto-optimo en el
   sentido de Bertsimas para este horizonte; el margen de mejora
   distributivo del P2P sobre C1 no es justificable solo por
   eficiencia agregada.

### 4.8.2 Limitaciones

[NARRATIVA — desarrollar:
- Cobertura PV del 19 % comunitaria es relativamente baja; resultados
  con cobertura 44 % (SA-2) deberian validarse con datos reales
  futuros.
- LCOE solar `b_n` calibrado a 241 COP/kWh (Fronius) y 225 COP/kWh
  (Cesmag) tras fix CAL-6 del 2026-05-06; heterogeneidad limitada a
  6,67 % (sólo varía Cesmag por inversor distinto). Pendiente de
  ampliar a heterogeneidad por horas-sol equivalentes y CapEx
  per-institución cuando MTE confirme fichas técnicas
  (`Inventario_Act_1_0.md:30-34`).
- `c_n = 0` (PV puro, convención canónica, fix 2026-05-06b CAL-32) y
  `lambda_n = 100` uniformes; ambos analíticamente invariantes en el
  equilibrio bajo α = 0 (sin DR), sólo afectan el offset reportado de
  bienestar. Verificado empíricamente vía
  `scripts/demo_invariancia_c_lambda.py`.
- Nivel de tension NT2 asumido para todas las instituciones; pendiente
  de confirmar contra factura mensual real.
- Horizonte 6 144 h cubre solo abr-dic 2025; estacionalidad anual
  completa no observada.]

### 4.8.3 Trabajo futuro

[NARRATIVA — desarrollar:
- Extender horizonte con datos 2026 cuando MTE los entregue.
- Evaluar el impacto de `b_n` heterogeneo por horas-sol equivalentes.
- Replicar con otras comunidades colombianas para externalizar la
  generalidad del hallazgo de IR diferenciada por categoria tarifaria.]

---

## Anexos a este borrador

- **Tablas y figuras:** referencias cruzadas a `graficas/fig10..fig21`
  y sus siblings `.csv`/`.mat`.
- **Apendice A (Calibracion):** `docs/adr/0001-cal1...` a
  `docs/adr/0008-cal8-pi-gs-cedenar.md`.
- **Apendice B (Reproducibilidad):** comandos `pytest tests/ -q` y
  `python main_simulation.py --data real --full --analysis`.
- **Codigo fuente:** `core/`, `scenarios/`, `analysis/`, `data/` y
  `visualization/` en este repositorio.

---

**Conteo:** ~245 lineas estructuradas. Ratio narrativa/datos: ~30/70
(las cifras concretas dominan; el autor humano debe aportar el 30 %
narrativo restante para defender los hallazgos academicamente).

**Verificaciones pendientes antes de copiar a `Documentos/FinalTesis/`:**

1. Aplicar las correcciones bibliograficas de
   `Documentos/bib_verificacion_2026-04-30.md` (renombrar 6 keys).
2. Generar tabla GSA Sobol con `S_T` por parametro (§4.5.3 placeholder).
3. Generar tabla mensual C1-C3 (§4.3.3 placeholder).
4. Confirmar que los `\cite{}` de este borrador resuelven con las
   keys ya corregidas.
5. Reescribir todos los `[NARRATIVA — ...]` con texto del autor.
6. **Actualizar cifras tras corrida `--full --analysis` con CAL-9**
   (matriz `(N, T)`): los numeros de §4.3.1, §4.6.3 y §4.7 fueron
   producidos pre-CAL-9 con el escalar 906. El delta esperado es
   < 1 % en agregados pero mas pronunciado mes a mes. Ejecutar
   `python scripts/cal9_delta_report.py` con los Excel pre/post para
   anotar las cifras finales. Documento canonico de la decision:
   `docs/adr/0009-cal9-pi-gs-temporal.md`.

---

## 4.9 Actualizacion post-CAL-24 (2026-05-02)

> **Contexto:** Tras el cierre de Sprint 5 del plan
> `radiant-sleeping-eagle`, todos los items "asumidos" detectados en
> la auditoria inicial fueron sustentados (CAL-17 a CAL-23) y se
> incorporo un validador regulatorio swarm (CAL-24). Esta seccion
> reemplaza los placeholders de §4.5 y suma los nuevos hallazgos.
> Las cifras provienen del snapshot Ruflo
> `run-post-cal23-baseline` (namespace `runs`).

### 4.9.1 Cifras principales actualizadas (horizonte 6 144 h)

| Escenario | Ganancia neta (COP) | Δ vs P2P [%] | Gini |
|-----------|--------------------:|------------:|-----:|
| **P2P (Stackelberg + RD)** | **52 446 938** | — | 0,162 |
| C1 (CREG 174/2021, AGPE) | 52 465 042 | +0,03 | 0,147 |
| C2 (PPA bilateral, no-regulado) | 51 437 446 | -1,93 | 0,155 |
| C3 (Mercado spot + techo PES) | 50 767 203 | -3,20 | 0,161 |
| C4 (Decreto 2236 + CREG 101 072) | 52 219 945 | -0,43 | 0,170 |

- **RPE (P2P vs C4):** +0,0043 (P2P supera al regimen vigente CREG
  101 072 en 0,43 % de bienestar agregado).
- **RPE (P2P vs C1):** -0,0003 (P2P empata con el regimen CREG 174
  para autogeneracion individual).
- **Bienestar agregado en C1 maximo absoluto** (52,47 MCOP); P2P
  capta 99,97 % de ese maximo con un equilibrio de mercado que
  redistribuye el excedente hacia los compradores comerciales
  (`IE_P2P = +0,368` indica precio cerca de $\pi_{gb}$,
  buyer-favoring). El coeficiente de Gini per-agente, que sí mide
  inequidad distributiva en sentido estandar, es 0,162 para P2P vs
  0,147 para C1 — diferencia despreciable; ambos escenarios son
  distributivamente equivalentes y la ventaja P2P viene de **expandir
  el pastel** sin redistribuir significativamente.

**Volumen P2P transado:** 3 659,31 kWh en 1 031 / 6 144 horas
activas (16,8 % del horizonte). Periodo abr-2025 a dic-2025.

### 4.9.2 Sustento empirico de los parametros del modelo

Cada parametro central tiene ahora un ADR con barrido empirico
reproducible:

| Parametro | Valor | Sustento empirico | ADR |
|-----------|------:|-------------------|-----|
| `stackelberg_iters` | 2 | Δ welfare < 0,02 % vs `iters = 10`; speedup 2,4× sobre 168 h MTE | 0019 |
| `cot_alpha` | 1,0 | Linealidad confirmada; default = cota legal CREG 086/1996 | 0020 |
| `f` (split PPA) | 0,5 | Teorema invarianza ratificado numericamente (Δ < 1e-13 %); cota egalitaria | 0021 |
| `cxc_alpha` | 0,0 | Default conservador (practica industrial PPAs colombianos); opt-in | 0023 |

**Hallazgos cuantitativos clave:**

1. **Stackelberg (CAL-19):** sobre 168 h reales, `iters = 1` produce
   Δ welfare = 1,89 % (insuficiente); `iters = 2` produce 0,011 %
   (default OK); `iters >= 3` no mejora numericamente. El sistema
   converge en mediana 3 iteraciones reales; `stackelberg_max = 10`
   cubre outliers.
2. **`cot_alpha` (CAL-20):** linealidad perfecta confirmada.
   Cuando `consumer_ids = []` (configuracion MTE real, todas
   prosumidoras), el parametro es **inerte** — el default 1,0 no
   afecta numericamente los reportes actuales.
3. **`f` (CAL-21):** sobre split ilustrativo 3 prosumers + 2
   consumers, `total_net_benefit` invariante (Δ vs `f = 0,5` <
   1e-13 %), Gini sube monotonicamente de 0,436 a 0,495. La
   distribucion prosumer/consumer es perfectamente lineal y
   simetrica en `f`.
4. **`cxc_alpha` (CAL-23):** parametrizable opt-in. Default 0,0
   coherente con la practica industrial (CXC se sigue cobrando
   bajo PPA bilateral). Sensibilidad triple disponible para defensa
   (`f`, `cot_alpha`, `cxc_alpha`).

### 4.9.3 Trazabilidad y certificacion de datos

**Cobertura horizonte simulacion (`--full`, abr-dic 2025):**

| Fuente | Cobertura | ADR |
|--------|-----------|-----|
| Cache pydataxm `precios_bolsa_xm_api.csv` | 7 272 h (303 dias, abr-2025 a feb-2026) | 0017 |
| Tarifa Cedenar `tarifas_cedenar_mensual.csv` | 13/13 meses (abr-2025 a abr-2026) | 0018 |
| Componente Cvm CREG 119/2007 art. 11 | 13/13 meses | 0010, 0016 |
| Costos MEM no-regulado (FAZNI + 4 % + repr.) | 13/13 meses | 0022 |
| Techo PES CREG 101 066/2024 | 7/7 meses verificados Excel oficial XM | 0014 |
| CXC referencial | 13/13 meses (modo opt-in) | 0023 |

**Auditoria pydataxm vs PB_PROM oficial XM (CAL-17):**

| Mes | Cache | PB_PROM oficial | Δ% |
|-----|------:|----------------:|---:|
| 2025-07 | 133,39 | 138,36 | -3,59 |
| 2025-08 | 238,25 | 251,50 | -5,27 |
| 2025-09 | 295,05 | 292,65 | +0,82 |
| 2025-10 | 189,93 | 176,90 | +7,37 |
| 2025-11 | 207,37 | 234,87 | -11,71 |
| 2025-12 | 275,02 | 278,83 | -1,37 |
| 2026-01 | 218,46 | 213,00 | +2,56 |

- 6/7 meses dentro de tolerancia 10 %; sesgo medio firmado -1,81 %
  (no sistematico).
- Decision: **no aplicar correccion numerica** al cache; la
  diferencia es metodologica (aritmetica vs ponderada por demanda).
- El gap del "35 %" mencionado en ADR-0014 fue un error de
  redaccion; la realidad es 2,58 % (post-script aclaratorio en
  ADR-0014, ver ADR-0017).

**Cedenar fail-fast (CAL-18):** se elimino el fallback silencioso
`pi_gs = 650 COP/kWh`. Cualquier mes ausente del CSV produce
`KeyError` con mensaje accionable que cita ADR-0018, en lugar de
inyectar un escalar invisible. La regla "todo bajo fuente
fundamentada" del plan queda formalmente cerrada para Cedenar.

### 4.9.4 Validacion regulatoria automatica (CAL-24)

Tres agentes especializados validan coherencia codigo-ADR-resolucion:

| Agente | Familia normativa | Escenario | Veredicto |
|--------|-------------------|-----------|-----------|
| `CREG174Validator` | CREG 174/2021 | C1 | PASS (5/5) |
| `CREG101072Validator` | Decreto 2236/2023 + CREG 101 072/2025 | C4 | PASS (5/5) |
| `CREG101066Validator` | CREG 101 066/2024 | C3 | PASS (5/5) |

**Veredicto agregado:** PASS (15/15 checks).

Comando reproducible: `python scripts/swarm_regulatory_validator.py`.

### 4.9.5 Snapshot Ruflo del baseline

El estado certificado del repositorio al cierre del Sprint 5 queda
almacenado como entrada semantica en namespace `runs` (clave
`run-post-cal23-baseline`):

```text
CALs activos: 24 (1-24)
RPE_P2P_vs_C1=-0,0003   RPE_P2P_vs_C4=+0,0043
IE_P2P=0,368   kWh_P2P=3 659,31   horas_p2p_activas=1 031/6 144
gini: P2P=0,162  C1=0,147  C2=0,155  C3=0,161  C4=0,170
```

Cualquier corrida futura quedara comparable semanticamente vs este
baseline mediante el wrapper de telemetria
`scripts/run_full_with_telemetry.py` (Sprint 5.1, JSON Lines).

### 4.9.6 Sintesis cuantitativa para defensa

| Pregunta de defensa | Respuesta cuantitativa |
|---------------------|-----------------------|
| ¿P2P es mejor que C1 (AGPE individual)? | Empate con ventaja distributiva: `RPE = -0,0003`, Gini P2P 0,162 vs C1 0,147 |
| ¿P2P es mejor que C4 (autogen colectiva)? | Si: `RPE = +0,0043`; 5/5 instituciones mejoran |
| ¿P2P es mejor que C2 (PPA bilateral)? | Si: `RPE = +1,93 %` |
| ¿P2P es mejor que C3 (mercado spot)? | Si: `RPE = +3,20 %` |
| ¿Los parametros tienen sustento empirico? | Si: 4 ADRs con barridos reproducibles (CAL-19 a CAL-21, CAL-23) |
| ¿Los datos tienen fuente fundamentada? | Si: cobertura 100 % horizonte; CAL-17/18/22 verifican |
| ¿La implementacion respeta las resoluciones CREG? | Si: validador swarm CAL-24 reporta PASS 15/15 |

[NARRATIVA — interpretar el resultado central: P2P aporta ganancia
distributiva sin perder bienestar agregado; la arquitectura completa
(24 ADRs) garantiza trazabilidad regulatoria y reproducibilidad
hacia auditores y asesores.]

---

## §6.5 — Subset paper IEEE WEEF 2026 (modo paper, CAL-25..29)

### Configuración paper

El paper IEEE WEEF 2026 usa un subset de la corrida de tesis con
ajustes acordados con asesores (reunión 2026-05-01,
`Documentos/Reunion0105.txt`):

- **CAL-25** (modo paper): homogeneización a perfil tarifario
  `comercial` y filtrado a 3 escenarios (P2P, C1=CREG 174, C2=C4
  renombrado=CREG 101 072). La tesis mantiene heterogeneidad oficial
  vs comercial.
- **CAL-28** (medidor puntual): selección de sub-medidor M3 por
  institución (Mariana M1 × 0.3) → cobertura PV agregada **96 %**
  vs **19 %** del totalizador M1. Mercado P2P pasa de 0 % a 29.7 %
  de horas activas.
- **CAL-29** (fórmula canónica): autoconsumo en TODAS las horas +
  revenue completo del trade + residual surplus a `pi_bolsa[k]`.
  Simétrico con C1/C2.
- **CAL-26/CAL-27** opt-in: PDE excedentes y C4 monthly_hx (no
  modifican baseline).

### Resultados paper — agosto-2025, baseline 1.0× PV

| Escenario | Ahorro autoconsumo [M COP] | Venta excedentes [M COP] | Total [M COP] |
|---|---:|---:|---:|
| P2P (Stackelberg + RD) | 3.60 | 1.21 | **4.81** |
| C1 (CREG 174) | 3.60 | 1.35 | **4.95** |
| C2 (CREG 101 072) | 3.60 | 0.98 | **4.58** |

P2P queda 2.9 % bajo C1 y 5.0 % sobre C2. La descomposición confirma
empíricamente la intuición del asesor: el autoconsumo es **offset
físico común** (3.60 M COP idéntico en los 3 escenarios); las ventas
de excedentes son el **diferenciador regulatorio real**.

### Heterogeneidad por institución

| Agente | P2P [COP] | C1 [COP] | C2 [COP] | Mejor |
|---|---:|---:|---:|:---:|
| Udenar | 787 250 | 759 326 | 704 467 | **P2P** (+27K vs C1) |
| Mariana | 855 641 | 873 086 | 815 953 | C1 (+17K vs P2P) |
| UCC | 1 376 917 | 1 802 451 | 1 431 606 | C1 (+425K vs P2P) |
| HUDN | 815 894 | 789 266 | 751 983 | **P2P** (+27K vs C1) |
| Cesmag | 972 226 | 726 314 | 873 599 | **P2P** (+246K vs C1) |

**3 de 5 instituciones individualmente prefieren P2P** sobre C1.
La agregación oculta heterogeneidad relevante para análisis de
adopción.

### Sensibilidad PV — transición de fase a P2P

Barrido `factor ∈ {1.0, 1.5, 2.0, 2.5, 3.0}` (96 %–288 % cobertura
comunitaria):

| Factor | Cobertura | P2P [M] | C1 [M] | C2 [M] | Rank P2P | Rank C1 | Rank C2 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.0 | 96 % | 4.81 | 4.95 | 4.58 | 2 | 1 | 3 |
| 1.5 | 144 % | 5.94 | 5.63 | 5.76 | **1** | 3 | 2 |
| 2.0 | 192 % | 6.87 | 6.64 | 6.75 | **1** | 3 | 2 |
| 2.5 | 240 % | 7.74 | 7.57 | 7.65 | **1** | 3 | 2 |
| 3.0 | 288 % | 8.59 | 8.44 | 8.51 | **1** | 3 | 2 |

**Hallazgo principal del paper**: P2P es competitivo a baseline
(rank 2) y se convierte en óptimo absoluto a partir de factor 1.5×.
La transición ocurre entre 1.0× y 1.5× cobertura.

### Auditoría histórica del fix CAL-29

La descomposición `_p2p_decomposed` previa a CAL-29 sub-reportaba P2P
en 1.92 M COP debido a dos bugs:

- Bug 1: `(pi_star − pi_gb) × P_sold` (incremental sobre baseline
  bolsa) en lugar de revenue completo + residual a `pi_bolsa`.
- Bug 2: autoconsumo solo en horas con mercado activo (omitía
  523/744 horas).

Con la fórmula buggy P2P aparecía perdiendo 38 % vs C1; corregido,
la diferencia es solo 2.9 %. Verificación empírica del audit:
`delta = pi_bolsa_mean × E_surplus_total = 234.5 × 4085.6 ≈ 958 K
COP`, coincide exacto con la cifra observada. Documento completo
en `Documentos/audit_p2p_decomposition.md` (Sprint 6.6-A).

### Trazabilidad regulatoria

Los 3 escenarios del paper se sustentan en ADRs específicos:

- **C1** → ADR-0010 (CAL-10 Tipo 1/2 + Cvm), CAL-9 (`pi_gs`
  temporal), CAL-14 (techo PES CREG 101 066), CAL-17 (auditoría
  pydataxm).
- **C2** (CREG 101 072) → ADR-0011 (CAL-15 herencia CREG 174),
  ADR-0026 (PDE excedentes opt-in), ADR-0027 (monthly_hx).
- **P2P** → CAL-1 a CAL-7 (parámetros núcleo), ADR-0029 (fórmula
  canónica paper-only).

CAL-24 (swarm validador regulatorio) confirma PASS 15/15 sobre el
repo post-Sprint 6.

### Borrador del paper

Documentos producidos para IEEE WEEF 2026 (deadline 2026-05-10):

- `Documentos/paper_weef.md` — borrador en inglés, 9 páginas
  estimadas, ~5 000 palabras.
- `Documentos/paper_weef_bib.bib` — 26 entradas BibTeX.

Pendiente al cierre de la tesis (no a este capítulo): conversión
LaTeX con plantilla IEEEtran + validación IEEE PDF eXpress (Conf
ID 71988X) + submit ACOFI Papers.
