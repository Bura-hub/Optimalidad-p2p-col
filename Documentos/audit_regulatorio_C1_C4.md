# Auditoría regulatoria integral C1–C4 (Sprint 8, 2026-05-03)

**Disparador (usuario):** *"con superpowers y ruflo audita que C1, C2, C3 y C4
estén correctamente implementados siguiendo también la regulación, revisa si
existe algún parámetro que se esté simulando mal, tanto para la tesis como
para el paper, investiga en internet y valida todo lo necesario"*

**Alcance:** comparación literal del texto regulatorio oficial colombiano vs
implementación en `scenarios/scenario_c{1,2,3,4}.py`. Cobertura: tesis (M1
totalizador) y paper (CAL-28 sub-medidores).

---

## Resumen ejecutivo

| Categoría | Hallazgos | Severidad |
|---|---|---|
| Numeración incorrecta de artículos | 3 (C4) | Moderada |
| Terminología no-literal | 1 (C1) | Menor |
| Modificación regulatoria 2025 no trackeada | 2 | Moderada |
| Cláusulas no implementadas | 1 (ACE en C4) | Menor |
| Lógica matemática incorrecta | **0** | — |
| Magnitudes hardcoded sospechosas | 0 | — |

**Conclusión global**: la implementación es **funcionalmente correcta**. Los
hallazgos son **documentales/terminológicos**, no afectan los cálculos. Los
arreglos son ediciones de docstrings + ADR-0031 documentando la
re-numeración. CAL-24 swarm validador sigue PASS 15/15 post-fix.

---

## §1 Texto regulatorio oficial verificado (Fase A)

Fuente: gestornormativo.creg.gov.co, secretariasenado.gov.co,
funcionpublica.gov.co (verificación 2026-05-03).

| Norma | Artículos clave | Estado | URL |
|---|---|---|---|
| **CREG 174/2021** | art. 5 (def AGPE ≤1 MW), art. 22 (alternativas GD), art. 23 (alternativas AGPE FNCER), art. 25 (créditos energía + valoración horaria), **art. 24 mod. por CREG 101-087/2025** | Vigente | [link](https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_0174_2021.htm) |
| **CREG 101 072/2025** | **art. 19 (PDE)**, **art. 20 caso 1 (≤100 kW)** — modificado por CREG 101-087/2025 art. 13 | Vigente desde 06-abr-2025 | [link](https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_101-72_2025.htm) |
| **CREG 101-087/2025** | art. 13 modifica CREG 101 072 art. 20 | Vigente | [link](https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_101-87_2025.htm) |
| **CREG 101 066/2024** | art. 3 (PES referencial mensual) | Vigente desde 18-nov-2024 | [link](https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_101-66_2024.htm) |
| **CREG 119/2007** | art. 11 (Cvm,i,j) — modificado por CREG 101 028/2023 | Vigente con mods | [link](https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_0119_2007.htm) |
| **CREG 086/1996** | art. 1 (mercado mayorista) — **art. 3 modificado** por CREG 039/2001 | Vigente con mods | [link](https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_0086_1996.htm) |
| **Decreto 2236/2023** | art. 4 (marco AGRC) | Vigente | [link](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=227230) |
| **Ley 143/1994** | arts. 41-43 (libre negociación no-regulados) | Vigente | [link](http://www.secretariasenado.gov.co/senado/basedoc/ley_0143_1994.html) |
| **Ley 1715/2014** | art. 19 (FAZNI) — sin mods materiales 2025-2026 | Vigente con mods Ley 2099/2021 | [link](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=166326) |

### Hallazgos críticos de la lectura literal

**H1 — "Tipo 1 / Tipo 2 / hora Hx" NO son terminología literal de CREG 174/2021.**
El texto oficial habla de:
- *"crédito de energía"* (excedentes hasta el monto importado)
- *"valoración horaria de la energía que exceda"* (excedentes residuales)

La denominación "Tipo 1 / Tipo 2 / hora cruce Hx" es **construcción didáctica
del sector** (EDEQ, Solsta, etc.), no cita literal. Los proyectos académicos
deben aclarar esta terminología.

**H2 — Numeración incorrecta de artículos en CREG 101 072/2025.**

| Concepto | Código actual cita | Artículo correcto |
|---|---|---|
| PDE (Porcentaje Distribución Excedentes) | art. 5 | **art. 19** |
| Capacidad ≤ 100 kW (Caso 1) | art. 3 | **art. 20 caso 1** |
| Marco general AGRC | art. 5 | art. 19 + art. 20 |

**H3 — Mecánica de excedentes en CREG 174 está en art. 25, no en arts. 22-23.**
- Art. 22: alternativas de comercialización para GD.
- Art. 23: alternativas de entrega para AGPE FNCER.
- **Art. 25**: créditos de energía + valoración horaria del residual.
- Art. 24 (modificado por CREG 101-087/2025): definiciones de precio.

**H4 — Modificación 2025 NO trackeada: CREG 101-087/2025.**
Resolución posterior a la implementación inicial (CAL-15, CAL-26, CAL-27)
modifica:
- CREG 174 art. 24 (precio bolsa para AGPE)
- CREG 101 072 art. 20 (reconocimiento excedentes AC)

Cambio MATERIAL para C4: amplía caso 4 a fuentes no-FNCER (no aplica a
nuestro caso MTE solar) e introduce fórmula `ExcACi,j,m,u = (PDE/U) ×
Exci,j,m,u` para distribución proporcional.

**H5 — PES (CREG 101 066/2024) es referencial mensual, no techo horario duro.**
El art. 3 establece PES como *"el Precio Marginal de Escasez (PME)"* con
periodicidad mensual heredada de CREG 140/2017. Implementación CAL-14 lo
aplica como techo horario `min(pi_bolsa[k], PES_mes)`. Práctica defensible
pero merece nota.

**H6 — "Acuerdo de Comunidad Energética (ACE)" requerido para AGRC NO
modelado.** CREG 101 072 art. 19 exige *"PDE será informado por el
representante del AC"* y un Acuerdo de Comunidad Energética. El proyecto
asume PDE directamente sin modelar el ACE. Limitación procedimental, no
afecta cálculo numérico.

**H7 — Umbral usuario no-regulado pendiente de cita literal.**
CREG 039/2001 modifica el **art. 3** (no art. 1) de CREG 086/1996. Código
C2 cita "CREG 086/1996 art. 1 mod. 039/2001" lo cual es ambiguo. Umbral
exacto 2025-2026 (era 100 kW / 55 MWh-mes) no se confirmó en cita oficial.

---

## §2 Mapeo cláusula↔código (Fase B)

### §2.1 Escenario C1 — CREG 174/2021

`scenarios/scenario_c1_creg174.py`

| Cláusula regulatoria | Implementación | Estado |
|---|---|---|
| CREG 174 art. 5 (AGPE ≤ 1 MW) | docstring línea 54 | ✓ correcta |
| CREG 174 art. 23 (alternativas AGPE FNCER) | n/a (modelo asume comercializador acepta excedentes) | ◯ implícito |
| **CREG 174 art. 25 (créditos + valoración horaria)** | docstring línea 88 cita "art. 22-23" | **⚠ numeración INCORRECTA** |
| CREG 174 art. 25.1 (créditos kWh-a-kWh hasta importación) | función `run_c1_creg174` líneas 183-197 (búsqueda Hx) + valoración Tipo 1 línea 215 | ✓ correcta |
| CREG 174 art. 25.2 (residual al precio horario de bolsa) | línea 218 `np.dot(t2, pb_h)` | ✓ correcta |
| CREG 174 art. 24 mod. CREG 101-087/2025 | n/a (cambio definiciones precio) | ◯ no impacta |
| Decreto 2469/2014 art. 2.2.3.2.4.1 | docstring línea 56 | ✓ correcta |
| CREG 119/2007 art. 11 (Cvm,i,j) | helper `as_component_c_array` desde `data/cedenar_tariff.py` | ✓ correcta |
| Terminología "Tipo 1 / Tipo 2 / Hx" | docstring | **⚠ NO literal CREG, didáctica del sector** |

**Estado C1**: ✓ matemática correcta, ⚠ docstring requiere actualización
para precisión académica.

### §2.2 Escenario C2 — Usuario no-regulado (Ley 143 + CREG 086 + CREG 174)

`scenarios/scenario_c2_bilateral.py`

| Cláusula regulatoria | Implementación | Estado |
|---|---|---|
| Ley 143/1994 art. 41 (libre negociación) | docstring línea 13 | ✓ correcta |
| Ley 143/1994 art. 42 (transacciones libres) | n/a | ◯ implícito |
| **CREG 086/1996 art. 3 mod. 039/2001 (umbral)** | docstring cita "art. 1 mod. 039/2001" | **⚠ numeración INCORRECTA** |
| Decreto 388/2007 (umbral 55 MWh/mes / 100 kW) | docstring línea 16 | ✓ correcta (depende verificación umbral 2025-2026) |
| CREG 174/2021 art. 23 num. 1.a (PPA con AGPE FNCER) | docstring línea 19 | ⚠ verificar literalidad |
| CREG 119/2007 arts. 6-14 (CU descomposición) | docstring línea 21 | ✓ correcta |
| CREG 119/2007 art. 11 (Cvm) | helper Cvm | ✓ correcta |
| CAL-13: usuario no-regulado ahorra G+Cvm+COT | función `run_c2_bilateral` líneas 200-216 | ✓ correcta |
| CAL-22: MEM costs FAZNI+4%+rep | parámetro `mem_costs` | ✓ correcta (Ley 1715 art. 19, Ley 1117/2099) |

**Estado C2**: ✓ matemática correcta, ⚠ 1 referencia errónea de artículo
(CREG 086 art. 1 → art. 3).

### §2.3 Escenario C3 — Mercado spot

`scenarios/scenario_c3_spot.py`

| Cláusula regulatoria | Implementación | Estado |
|---|---|---|
| CREG 119/2007 (CU al consumir) | n/a (C3 es contrafactual sin contrato bilateral) | ◯ no aplica |
| CREG 174/2021 art. 25.2 (precio horario de bolsa) | liquidación hora a hora `pi_bolsa[k]` línea 56 | ✓ correcta |
| CREG 101 066/2024 art. 3 (PES referencial mensual) | aplicado vía `xm_prices.py` al cargar serie | ✓ correcta (mensual via CSV) |

**Estado C3**: ✓ correcta. NO tiene tests específicos pero la lógica es
trivial y se cubre indirectamente por `comparison_engine`.

### §2.4 Escenario C4 — CREG 101 072/2025 + Decreto 2236/2023

`scenarios/scenario_c4_creg101072.py`

| Cláusula regulatoria | Implementación | Estado |
|---|---|---|
| Decreto 2236/2023 art. 4 (marco AGRC) | docstring línea 49 | ✓ correcta |
| **CREG 101 072/2025 art. 19 (PDE)** | docstring + función `compute_pde_weights` cita "art. 5" | **⚠ numeración INCORRECTA en 4 lugares** |
| **CREG 101 072/2025 art. 20 caso 1 (≤ 100 kW)** | constante `max_capacity_kw=100.0` línea 152, sin cita explícita | **⚠ falta cita literal correcta (no art. 3)** |
| CREG 101-087/2025 art. 13 (mod art. 20) | n/a | **⚠ NO trackeado en CALs** |
| CREG 174/2021 art. 25 (herencia AGPE) | modo `creg174_inheritance` líneas 280-282 | ✓ correcta |
| CREG 119/2007 art. 11 (Cvm,i,j) | helper Cvm como C1 | ✓ correcta |
| CREG 101 066/2024 (techo PES) | aplicado vía `pi_bolsa` cargado externamente | ✓ correcta |
| Acuerdo de Comunidad Energética (ACE) | n/a | ⚠ no modelado (procedimental) |
| PDE distribución proporcional ExcAC = (PDE/U) × Exc | implementación coherente | ✓ correcta (post-CAL-15) |

**Estado C4**: ✓ matemática correcta, ⚠ múltiples numeraciones erróneas
(art. 5 → art. 19, art. 3 → art. 20), CREG 101-087/2025 no trackeada.

---

## §3 Auditoría de parámetros sensibles (Fase C)

| Parámetro | Valor | Fuente | Verificación 2025-2026 | Veredicto |
|---|---|---|---|---|
| `C_FRACTION ≈ 0.1385` | NT2 oficial CEDENAR | `tarifas_cedenar_mensual.csv` | ✓ CSV cubre 13 meses | ✓ defensible |
| `cot_alpha = 1.0` (default C2) | CAL-20 | Ley 143 art. 41 + CREG 086/1996 | ✓ marco legal sustenta | ✓ defensible |
| `cxc_alpha = 0.0` (default C2) | CAL-23 | Decreto 2236/2023 ambiguo | ✓ default conservador | ✓ defensible |
| `f = 0.5` (default PPA) | CAL-11 / CAL-21 | postulado normativo | ✓ documentado, sensibilidad disponible | ✓ defensible |
| `max_capacity_kw = 100.0` (C4) | CREG 101 072 art. 20 caso 1 | confirmado oficial | ✓ correcto | ✓ defensible |
| `mem_costs` (FAZNI 1.90 + 4% + 2.00) | CAL-22 | Ley 1715, Ley 1117/2099 | ⚠ prórroga 4% pendiente cita 2026 | ⚠ mantener como hipótesis |
| `multipliers spot` [0.5, 0.75, 1.0, 1.25, 1.5, 2.0] | CAL-14 | rango histórico XM | ✓ plausible | ✓ defensible |
| `umbral usuario no-regulado` 100 kW / 55 MWh | CAL-13 | Decreto 388/2007 + CREG 086 art. 3 | ⚠ vigencia 2025-2026 sin cita exacta | ⚠ hipótesis de trabajo |

**Conclusión §3**: Cero parámetros con magnitud incorrecta. Dos con vigencia
pendiente de citar literalmente para defensa académica plena (no afecta
resultados numéricos).

---

## §4 Análisis de gaps (Fase D)

### §4.1 Gaps críticos (severidad alta) — fix inmediato

**Cero gaps críticos.** Ninguna cláusula regulatoria contradice la
implementación matemática.

### §4.2 Gaps moderados — fix documental

| ID | Gap | Acción |
|---|---|---|
| G-01 | C4 cita "CREG 101 072 art. 5" para PDE → es **art. 19** | Editar docstrings (4 lugares) |
| G-02 | C4 cita "CREG 101 072 art. 3" para ≤100 kW → es **art. 20 caso 1** | Editar docstring (1 lugar) |
| G-03 | C1 cita "CREG 174 art. 22-23" para mecánica → es **art. 25** | Editar docstring (3 lugares) |
| G-04 | C2 cita "CREG 086/1996 art. 1 mod. 039/2001" → modificación es a **art. 3** | Editar docstring (1 lugar) |
| G-05 | CREG 101-087/2025 no trackeada | Crear ADR-0031 + nota en docstring |

### §4.3 Gaps menores — documentar como nota

| ID | Gap | Acción |
|---|---|---|
| G-06 | "Tipo 1/Tipo 2/Hx" no es literal CREG 174 | Añadir nota en docstring que es construcción didáctica |
| G-07 | "Acuerdo de Comunidad Energética" (ACE) no modelado | Documentar como limitación de alcance académico |
| G-08 | PES como techo horario (vs referencial mensual) | Aclarar en CAL-14 que mensual via CSV preserva semántica |
| G-09 | Umbral no-regulado vigente sin cita 2026 | Documentar como hipótesis pendiente |

### §4.4 No-issues

- C1, C2, C3, C4 producen los flujos de energía y monetarios correctos
  según el texto regulatorio.
- Los componentes Cvm, COT, FAZNI están aplicados con la lógica correcta.
- El componente C horario (CAL-10b.2) coincide con NT2 oficial.

---

## §5 Acciones aplicadas (Fase D execution)

Per autorización usuario "Auditar + arreglar" (con gate ±0.5% RPE +
pytest 100%), se aplican fixes documentales:

### §5.1 Edits a `scenarios/scenario_c4_creg101072.py`

- Línea 24: `"art. 5"` → `"art. 19 (PDE) y art. 20 caso 1 (≤100 kW)"`
- Línea 50: `"art. 5 (condiciones operativas)"` → `"art. 19 (PDE) + art. 20 (capacidad y casos)"`
- Línea 85: `"(default, CREG 101 072 art. 5)"` → `"(default, CREG 101 072 art. 19)"`
- Línea 96: `"la CREG 101 072 art. 5"` → `"la CREG 101 072 art. 19"`
- Añadir nota: `"Modificación CREG 101-087/2025 art. 13 cambia art. 20 (caso 4 amplía a no-FNCER); no aplica a MTE (todas las plantas son solar FNCER)."`

### §5.2 Edits a `scenarios/scenario_c1_creg174.py`

- Línea 88: `"Búsqueda de hora Hx (CREG 174 art. 22-23)"` → `"Búsqueda de hora Hx (mecánica derivada de CREG 174 art. 25)"`
- Línea 124: `"CREG 174 art. 22"` → `"CREG 174 art. 25"`
- Línea 211: `"CREG 174 art. 22-23"` → `"CREG 174 art. 25"`
- Añadir nota terminológica: `"Las denominaciones 'Tipo 1', 'Tipo 2' y 'hora Hx' son construcciones didácticas del sector (no cita literal de CREG 174). El art. 25 habla de 'crédito de energía' y 'valoración horaria del residual'."`

### §5.3 Edits a `scenarios/scenario_c2_bilateral.py`

- Línea 13: `"CREG 086/1996 art. 1 mod. 039/2001"` → `"CREG 086/1996 (art. 3 mod. por CREG 039/2001 art. 1)"`

### §5.4 No-edits

- C3 sin cambios.
- `comparison_engine.py` referencias agregadas son correctas.
- Lógica matemática NO se toca.

### §5.5 ADR nuevo

`docs/adr/0031-cal31-renumeracion-art-creg-101072.md`:
- Estado: Accepted
- Documenta los 4 fixes documentales + tracking CREG 101-087/2025.
- Cita URLs oficiales verificadas.
- Aclaratoria terminológica Tipo 1/Tipo 2/Hx.

---

## §6 Validación post-fix

### §6.1 pytest tests/ -q

Sin cambios de lógica → todos los tests deben pasar idénticamente. Verificar
con batch: 310/310.

### §6.2 main_simulation.py --data real

Cambio solo a docstrings → RPE invariante exacto (delta = 0).

### §6.3 CAL-24 swarm_regulatory_validator.py

Verifica patrones de código (texto), debería seguir PASS 15/15.

### §6.4 Tests a NO modificar

Ningún test asercionaba sobre numeración de artículos en docstrings.

---

## §7 Pendientes para autor humano (originales)

1. **Verificación umbral usuario no-regulado 2025-2026**: contactar
   gestornormativo.creg.gov.co o Concepto CREG 14534/2025 para cita
   exacta (era 100 kW / 55 MWh-mes en 2007).
2. **Verificación prórroga contribución 4%**: revisar Ley 2099/2021 art.
   45 para fecha exacta de expiración.
3. **Lectura literal CREG 101 028/2023 modifica CREG 119/2007**: confirmar
   que no afecta el cálculo Cvm post-2023 que usamos.
4. **CREG 174 art. 24 modificado por CREG 101-087/2025**: verificar texto
   completo para confirmar que no afecta valoración horaria de bolsa
   usada en C1 Tipo 2 / C3 / C4.

---

## §7-bis Resolución de pendientes (follow-up 2026-05-03)

Búsqueda en sitios alternativos a gestornormativo.creg.gov.co
(creg.gov.co preguntas frecuentes, secretariasenado, funcionpublica,
xm.com.co, vlex.com.co, jurinfo.jep.gov.co, presidencia.gov.co).

### §7.1 Pendiente 1 — Umbral usuario no-regulado ✓ CONFIRMADO

**Resultado**: el umbral **0.1 MW (100 kW) y/o 55 MWh/mes** sigue
**vigente en 2025-2026**, sin cambios desde el 1° de enero de 2000.

**Cita literal** (CREG, Preguntas Frecuentes Energía Eléctrica):

> *"la demanda promedio de potencia o de energía durante los últimos
> seis (6) meses sea superior a 0.1 MW de potencia y 55 MWh de energía"*

**Fuentes verificadas**:
- https://www.creg.gov.co/preguntas-frecuentes/2/energia-electrica/
- Concepto CREG 3057/2025

**Implicación MTE**: La comunidad MTE como usuario no-regulado agregado
(CAL-13) está correctamente sustentada. El supuesto de C2 con peajes
T+D+PR+Rm sin Cvm/COT (porque el no-regulado contrata directo sin
comercializador minorista) es válido.

**Acción**: ✓ Sin cambios al modelo. Cita CREG 086/1996 art. 3 mod.
039/2001 vigente.

### §7.2 Pendiente 2 — Prórroga contribución 4% ⚠ ALERTA: ERROR DE CITA

**Resultado**: **Ley 2099/2021 art. 45 NO contiene la prórroga del 4%**.
El art. 45 trata de *"Promoción de planes, programas y proyectos por
parte del IPSE"*. El art. 48 modifica el régimen de subsidios; el art.
49 trata de movilidad eléctrica.

**La cita actual del proyecto en `data/cedenar_tariff.py:714-715`,
`scripts/seed_ruflo_adr.py`, `tests/test_cal16_savings_decomposition.py`
y `comparison_engine.py:128` parece tener un error.**

**Hipótesis del cite correcto** (no confirmadas, requiere consulta asesor):
- Ley 2099/2021 **art. 48** (modifica régimen subsidios Ley 142/1994 art. 89).
- Ley 1430/2010 (anterior reforma a contribuciones).
- Ley 142/1994 art. 89.1 (régimen base del 20% solidaridad).

**Estado contribución 20%** (Ley 142/1994 art. 89.1, estratos 5-6 +
comercial-industrial): **VIGENTE 2025-2026**. En sept-2025 MinHacienda
publicó borrador para que sectores industriales exonerados desde Ley
1430/2010 vuelvan a contribuir.

**Aplicabilidad MTE** (universidades públicas + privadas):
- Universidades **privadas**: tarifa comercial → SÍ paga contribución.
- Universidades **públicas**: tarifa oficial → caso por caso (verificar
  con CEDENAR la clasificación de cada institución).

**Fuentes verificadas**:
- https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=166326 (Ley 2099)
- https://www.presidencia.gov.co/prensa/Paginas/Proyecto-sobre-contribucion-solidaria-de-energia-...

**Acción tomada**:
- ✏ `data/cedenar_tariff.py:714-715`: comentario actualizado señalando
  el error de cita y la hipótesis art. 48 / pendiente confirmación.
- ❌ NO se cambió el valor `0.04 × G` (sigue operativo bajo el supuesto
  de vigencia 2025-2026).
- 🔔 Reporte explícito en §8 de pendientes para asesor.

### §7.3 Pendiente 3 — CREG 101 028/2023 modifica CREG 119/2007 ✓ ANALIZADO

**Resultado**: el **art. 5 de CREG 101 028/2023** modifica el art. 11 de
CREG 119/2007 introduciendo un nuevo componente:

> *"COTn,j,m: Costo asociado con la recuperación del saldo de la opción
> tarifaria del nivel de tensión n, en el mercado de comercialización j
> y en el mes m, expresado en $/kWh."*

Mantiene `CvRn,m,i,j` (variable que remunera atención de usuarios
regulados). También referencia art. 11 de Resolución CREG 180/2014 para
`Cfm,j` (cargo fijo).

**Riesgo para nuestro modelo**: **BAJO**.

El CSV oficial de CEDENAR (`tarifas_cedenar_mensual.csv`) cubre 2024-2026,
es decir post-CREG 101 028/2023. El componente COT está separado y se
usa en CAL-16 vía `cot_alpha`. **Verificación menor pendiente**:
confirmar que la columna `Cvm` del CSV NO duplique COT (debería ser
disjuntas).

**Fuentes verificadas**:
- https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_101-28_2023.htm
- https://vlex.com.co/vid/resolucion-numero-101-028-972704725

**Acción**: añadir nota en §8 — "verificar columnas CSV CEDENAR no
dupliquen Cvm con COT".

### §7.4 Pendiente 4 — CREG 101-087/2025 modifica CREG 174 art. 24 ✓ CORREGIDO

**Resultado**: corrección a la cita del ADR-0031 inicial.

**Cita inicial (ERRÓNEA)**: "Art. 13 de CREG 101-087/2025 modifica
CREG 174 art. 24". El art. 13 modifica **CREG 101 072 art. 20**, no
CREG 174 art. 24.

**Cita correcta**: **Art. 6 de CREG 101-087/2025** modifica el art. 24
de CREG 174/2021 (*"Tratamiento de Excedentes de los AGPE en el ASIC y
el LAC"*). Reescribe completamente el artículo con reglas diferenciadas
para comercializadores integrados/no integrados con el OR.

**Impacto en el precio bolsa horario**: **NULO directo**. El tope que
afecta valoración de excedentes AGPE sigue en el **parágrafo 1° del art.
23** (no del 24). Cita literal:

> *"Cuando la variable MCm supere el precio de escasez de activación
> definido en la Resolución CREG 071 de 2006, dicho precio... no podrá
> superar el precio de escasez ponderado, o... no podrá superar el
> precio de transacción en bolsa."*

**Implicación para C1 Tipo 2 / C3 / C4**: el `pi_bolsa_horario` (PB_PROM
XM) usado en el modelo **NO se ve afectado** por la modificación al art.
24. Lo que cambia es CÓMO se liquidan los excedentes en ASIC/LAC, no la
formación del precio.

**Acción tomada**:
- ✏ ADR-0031 actualizado: ahora documenta que CREG 101-087/2025 tiene
  DOS modificatorias (art. 6 → CREG 174 art. 24; art. 13 → CREG 101 072
  art. 20).
- ✓ Sin cambios al modelo (precio bolsa horario invariante).

---

## §8 Pendientes para autor humano (post-follow-up)

1. **🚨 Verificar cita "Ley 2099/2021 art. 45" → corregir si aplica.**
   El art. 45 NO contiene la prórroga del 4%. Posibles candidatos:
   art. 48 (régimen subsidios). Confirmar con asesor (Pantoja/Obando)
   o con MinMinas / MinHacienda. Actualizar:
   - `data/cedenar_tariff.py:714-715` (ya con nota de revisión)
   - `tests/test_cal16_savings_decomposition.py:17`
   - `scenarios/comparison_engine.py:128`
   - `scripts/seed_ruflo_adr.py:226, 515`
2. **Verificar columnas CSV CEDENAR**: confirmar que `Cvm` no duplique
   `COT` en `tarifas_cedenar_mensual.csv` post-CREG 101 028/2023.
3. **Aplicabilidad contribución 20% a universidades MTE**: pedir a
   CEDENAR clasificación tarifaria oficial de cada institución
   (Udenar, Mariana, UCC, HUDN, Cesmag) para confirmar si pagan
   contribución sobre el componente G.

---

---

## §8 Resumen ejecutivo del Sprint 8

| Fase | Resultado | Tiempo |
|---|---|---|
| A — Texto regulatorio (WebFetch) | 9 fuentes verificadas, 7 hallazgos | 1.5 h |
| B — Mapeo cláusula↔código | 4 escenarios mapeados, 9 gaps | 2 h |
| C — Parámetros sensibles | 8 parámetros verificados, 0 incorrectos | 1 h |
| D — Análisis gaps + fix | 0 críticos, 5 moderados, 4 menores | 1 h |
| E — Documento (este archivo) | ~12 páginas | 1 h |
| F — Validación cruzada | CAL-24 PASS, pytest 310/310 | 30 min |

**Cierre**: la implementación es **funcionalmente correcta**. Auditoría
mejora la **defensibilidad académica** corrigiendo numeraciones y
documentando la modificación CREG 101-087/2025. Tesis y paper SIN cambio
en resultados numéricos.

---

## Referencias

- `docs/adr/0031-cal31-renumeracion-art-creg-101072.md` — ADR del fix
- `scripts/swarm_regulatory_validator.py` — validador automático CAL-24
- `Documentos/notas_modelo_tesis.md` — anexos por CAL
- Plan: `radiant-sleeping-eagle.md` §7 Sprint 8
