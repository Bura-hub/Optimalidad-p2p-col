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
| `b_n` (LCOE solar) | 225 COP/kWh (210 Cesmag) | IRENA/UPME | 0006 |
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

| Escenario | Ganancia neta (MCOP) | SC | SS | IE |
|---|---:|---:|---:|---:|
| **P2P (Stackelberg + RD)** | **52,43** | 0,188 | 0,981 | +0,3677 |
| C1 (CREG 174/2021, AGPE) | 54,04 | 0,176 | 0,921 | -0,0115 |
| C2 (Bilateral PPA) | 51,44 | 0,176 | 0,921 | +0,0292 |
| C3 (Mercado spot) | 50,96 | 0,176 | 0,921 | +0,0375 |
| C4 (CREG 101 072) ★ | 50,29 | 0,176 | 0,921 | +0,0517 |

**Notacion:** SC = autoconsumo (self-consumption), SS = autosuficiencia
(self-sufficiency), IE = indice de equidad (positivo = compradores
capturan excedente, negativo = vendedores).

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
de los indices. Discusion del por que IE_P2P > 0 (compradores
comerciales capturan 71,4 % del excedente por su mayor `pi_gs[i]`).]

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
- LCOE solar `b_n = 225 COP/kWh` homogeneo es supuesto (ADR 0006);
  pendiente de heterogeneizar con fichas tecnicas de inversores.
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
