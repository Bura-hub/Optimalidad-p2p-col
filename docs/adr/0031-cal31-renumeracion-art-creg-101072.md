# 0031 — CAL-31: Re-numeración de artículos CREG y aclaratorias terminológicas

- **Estado:** Accepted
- **Fecha de decisión:** 2026-05-03
- **Actividad:** 3.1 + 3.2 + 3.3 (validación regulatoria)
- **Archivos afectados:**
  - `scenarios/scenario_c1_creg174.py` (3 docstrings)
  - `scenarios/scenario_c2_bilateral.py` (1 docstring)
  - `scenarios/scenario_c4_creg101072.py` (5 docstrings)
  - `Documentos/audit_regulatorio_C1_C4.md` (NUEVO, ~12 páginas)
- **Relacionado con:** ADR-0010 (CAL-10 C1), ADR-0011 (CAL-15 C4),
  ADR-0014 (CAL-14 PES), ADR-0024 (CAL-24 swarm validador).
- **Fuente:** Sprint 8 (`radiant-sleeping-eagle.md` §7) — auditoría
  regulatoria integral C1-C4 solicitada por usuario 2026-05-03.

## Contexto

Tras Sprint 7 (CAL-30 engine canónico), el usuario solicitó auditar la
**implementación regulatoria** de los 4 escenarios contra el texto
oficial de las resoluciones colombianas, con foco en parámetros
hardcoded y vigencia 2025-2026.

La auditoría (`Documentos/audit_regulatorio_C1_C4.md`) incluyó:

- Fase A: WebFetch a gestornormativo.creg.gov.co, secretariasenado,
  funcionpublica para 9 fuentes oficiales (CREG 174/2021, 101 072/2025,
  101 066/2024, 119/2007, 086/1996; Decreto 2236/2023, 388/2007; Ley
  143/1994, 1715/2014).
- Fase B: mapeo cláusula↔código por escenario.
- Fase C: cross-check 8 parámetros hardcoded vs fuentes externas.
- Fase D: análisis de gaps y severidad.

## Hallazgos

**Lógica matemática**: ✓ correcta en los 4 escenarios. Cero gaps críticos.

**Parámetros**: ✓ 8/8 verificados, ninguno con magnitud incorrecta.

**Documentación**: ⚠ 5 referencias a artículos con numeración incorrecta
(comparado con texto oficial verificado vía WebFetch):

### G-01..G-04 — Numeración incorrecta de artículos

| ID | Escenario | Cita actual | Correcto | Lugares |
|---|---|---|---|---|
| G-01 | C4 | CREG 101 072 art. 5 (PDE) | **art. 19** (PDE) | 4 |
| G-02 | C4 | CREG 101 072 art. 3 (≤100 kW) | **art. 20 caso 1** | 1 |
| G-03 | C1 | CREG 174 art. 22-23 (Tipo 1/2) | **art. 25** (créditos + valoración horaria) | 3 |
| G-04 | C2 | CREG 086/1996 art. 1 mod. 039/2001 | art. **3** mod. CREG 039/2001 art. 1 | 1 |

### G-05 — Modificación regulatoria 2025 NO trackeada

**CREG 101-087/2025** modifica vía DOS artículos distintos (corrección
follow-up 2026-05-03 tras búsqueda en sitios alternativos):
- **Art. 13** modifica CREG 101 072/2025 art. 20 (caso 4 amplía a fuentes
  no-FNCER).
- **Art. 6** modifica CREG 174/2021 art. 24 ("Tratamiento de Excedentes
  de los AGPE en el ASIC y el LAC"); reescribe completamente con reglas
  diferenciadas para comercializadores integrados/no integrados con OR.

**Impacto en MTE**: NULO numéricamente.
- Caso 4 no-FNCER no aplica (todas las plantas MTE son solar/FNCER).
- Cambios en art. 24 afectan CÓMO se liquidan los excedentes en ASIC/LAC,
  NO la formación del precio de bolsa horario. El tope sigue en el
  parágrafo 1° del art. 23 (CREG 174). El `pi_bolsa_horario` (PB_PROM XM)
  que usamos NO se ve afectado por art. 24.

### G-06 — Terminología "Tipo 1/Tipo 2/Hx" no es literal CREG 174

CREG 174/2021 art. 25 habla de:
- *"crédito de energía"* (excedentes ≤ importación)
- *"valoración horaria de la energía que exceda"* (residual)

Las denominaciones "Tipo 1", "Tipo 2", "hora cruce Hx" son construcciones
**didácticas del sector** (operadores como EDEQ, Solsta), no cita literal.

## Decisión

Aplicar **fixes documentales** (5 docstrings) corrigiendo la numeración
de artículos a la verificada oficialmente, y añadir notas terminológicas
para distinguir construcciones internas vs cita literal CREG.

**No se modifica lógica matemática.** Los 310 tests de la suite siguen
verdes idénticamente. CAL-24 validador swarm sigue PASS 15/15.

### Cambios aplicados

**`scenarios/scenario_c1_creg174.py`:**
- Docstring línea 88: `"CREG 174 art. 22-23"` → `"derivada de CREG 174 art. 25"`
- + Nota terminológica: Tipo 1/Tipo 2/Hx son didácticos, no literales.
- Comentario línea ~125: `"art. 22"` → `"art. 25 (créditos de energía)"`
- Comentario línea ~213: `"CREG 174 art. 22-23"` → `"CREG 174 art. 25"`

**`scenarios/scenario_c2_bilateral.py`:**
- Docstring línea 13: `"CREG 086/1996 art. 1 mod. 039/2001"` →
  `"CREG 086/1996 (art. 3 modificado por CREG 039/2001 art. 1)"`

**`scenarios/scenario_c4_creg101072.py`:**
- Docstring marco regulatorio: `"art. 5"` → `"art. 19 (PDE) + art. 20 caso 1"`
- Sección "Referencia regulatoria": expandida con (a) numeración correcta,
  (b) tracking CREG 101-087/2025, (c) nota PES referencial mensual.
- 4 ocurrencias `"CREG 101 072 art. 5"` → `"CREG 101 072 art. 19"` (replace_all).

## Consecuencias

**Positivas:**
- **Defensibilidad académica**: cita oficial verificada con URLs de
  gestornormativo.creg.gov.co.
- **Tracking regulatorio**: CREG 101-087/2025 ahora documentada.
- **Aclaratoria terminológica**: futuros lectores no confundirán
  "Tipo 1" como cita literal CREG.

**Negativas:**
- Ninguna. Los cambios son no-functional.

**Pendientes** (se documentan en §7 del audit, no parte de CAL-31):
1. Verificar umbral usuario no-regulado vigente 2025-2026 (Concepto
   CREG 14534/2025).
2. Verificar prórroga contribución 4% (Ley 2099/2021 art. 45).
3. Lectura literal CREG 101 028/2023 mod CREG 119/2007 (no afecta cálculo
   actual pero aclara contexto).

## Validación

- **pytest tests/ -q**: 310/310 verdes (sin cambios de lógica → tests
  invariantes).
- **CAL-24 swarm validador**: PASS 15/15 post-fix.
- **main_simulation.py --data real**: RPE delta = 0 (cambios solo doc).

## Test plan

No se añaden tests nuevos. Los cambios son docstring-only y los tests
existentes verifican funcionalmente la implementación. La defensibilidad
se documenta en `Documentos/audit_regulatorio_C1_C4.md`.

## Referencias

- **`Documentos/audit_regulatorio_C1_C4.md`** — auditoría completa con
  los 9 hallazgos, mapeo por escenario, parámetros sensibles, y
  pendientes para autor humano.
- CREG 174/2021: https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_0174_2021.htm
- CREG 101 072/2025: https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_101-72_2025.htm
- CREG 101-087/2025: https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_101-87_2025.htm
- CREG 101 066/2024: https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_101-66_2024.htm
- Plan: `radiant-sleeping-eagle.md` §7 Sprint 8.
