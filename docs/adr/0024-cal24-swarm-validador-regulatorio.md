# 0024 — CAL-24: Swarm validador regulatorio (3 agentes especializados)

- **Estado:** Accepted
- **Fecha de decisión:** 2026-05-02
- **Actividad:** 1.0 + 4.1 + 4.2 (validación regulatoria + cierre defensa)
- **Archivos afectados:**
  `scripts/swarm_regulatory_validator.py` (nuevo, modo `local` + `swarm`),
  `tests/test_swarm_regulatory_validator.py` (nuevo).
- **Relacionado con:** ADR-0010 (CAL-10 C1), ADR-0011 (CAL-15 C4),
  ADR-0014 (CAL-14 C3), ADR-0016 (CAL-16 C2), ADR-0017..0023 (calibraciones).
- **Fuente:** plan
  `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 5.2.

## Contexto

Tras 23 ADRs (CAL-1..CAL-23), el repositorio tiene una densa cadena
de decisiones regulatorias entre código (`scenarios/`), ADRs
(`docs/adr/`) y resoluciones CREG (citadas pero no parseadas
automáticamente). Sin un mecanismo de validación cruzada periódica,
es posible que:

1. Un cambio en el código rompa la literalidad de una resolución
   sin que el ADR correspondiente se actualice.
2. Un ADR `Accepted` no tenga implementación verificable en código.
3. Una resolución CREG sea modificada por una nueva (e.g. CREG
   101 072 modifica CREG 174 art. 25) y el modelo continúe usando
   la versión antigua.

El plan radiant-sleeping-eagle Sprint 5.2 propone un **swarm de 3
agentes especializados** que validan coherencia regulatoria por
familia normativa.

## Decisión

Implementar `scripts/swarm_regulatory_validator.py` con **dos modos
de ejecución**:

### Modo `local` (default, determinístico, rápido)

Validación heurística estática sin MCP. Tres agentes lógicos
(funciones independientes) validan checks por escenario:

| Agente | Familia CREG | Escenario | Checks |
|--------|--------------|-----------|--------|
| `CREG174Validator` | CREG 174/2021 | C1 | Excedentes Tipo 1/2 implementados; Cvm,i,j puro (CAL-10b.2); ADR-0010 Accepted; tests verdes. |
| `CREG101072Validator` | Decreto 2236/2023 + CREG 101 072/2025 | C4 | PDE estático aplicado; Tipo 1 a `pi_gs - Cvm`, Tipo 2 a `pi_bolsa`; ADR-0011 (CAL-15) Accepted; tests `test_c4_creg101072.py`. |
| `CREG101066Validator` | CREG 101 066/2024 | C3 | Techo PES aplicado por defecto; CSV `precios_escasez_creg.csv` cargado; `apply_creg101066_ceiling` definido; ADR-0014 Accepted. |

Cada agente devuelve `{"agent": ..., "verdict": "PASS"|"PARCIAL"|"FAIL",
"checks": [{"name": ..., "result": True|False, "detail": ...}, ...]}`.

Aggregator combina los 3 veredictos:
- **PASS** si los 3 son PASS.
- **PARCIAL** si al menos uno es PARCIAL (algunos checks fallan,
  pero el ADR cubre).
- **FAIL** si al menos uno es FAIL (check crítico violado).

### Modo `swarm` (opt-in, vía MCP claude-flow)

Para defensas o auditorías profundas, invocar `swarm_regulatory_validator.py
--mode swarm` lanza un swarm real con 3 agentes especializados
(`researcher` + `code-analyzer` + `reviewer`) usando
`mcp__claude-flow__swarm_init` + `agent_spawn`. Cada agente recibe
contexto: archivo de escenario, ADRs aplicables, resolución cita.

Esta capacidad requiere:
- MCP `claude-flow` activo en la sesión.
- Internet/API para los agentes especializados.
- ~30-60 s por agente.

**Graceful degradation**: si MCP no responde, cae al modo `local`
con warning explícito. Tests se ejecutan solo sobre el modo `local`
(determinístico).

## Alternativas consideradas

1. **Pre-commit hook que valide automáticamente**. Descartado: muy
   lento para CI; el modo `local` es suficiente como herramienta
   periódica.
2. **Implementar como agente único en lugar de 3**. Descartado:
   especialización por familia CREG produce diagnósticos más
   precisos y permite paralelización futura.
3. **Validación contra texto de la resolución CREG (NLP)**.
   Descartado: requiere parsear los PDFs de la CREG, fuera del
   alcance académico de la tesis.

## Consecuencias

**Positivas**

- Cierre formal del plan radiant-sleeping-eagle Sprint 5.2.
- Herramienta reproducible para validar coherencia regulatoria
  pre-defensa (`python scripts/swarm_regulatory_validator.py`).
- Modo `swarm` opcional para auditorías profundas con asesores.
- Test de regresión previene drift silencioso de cualquiera de los
  3 escenarios.

**Negativas**

- El modo `local` se basa en heurísticas (regex, presencia de
  archivos); no garantiza validación semántica completa de la
  literalidad CREG.
- El modo `swarm` requiere MCP activo; no es reproducible
  determinísticamente para CI.

**Riesgos abiertos**

- Si una resolución CREG futura modifica los componentes esperados
  (e.g. nuevo cargo o cambio en Cvm), las heurísticas del modo
  `local` deben actualizarse. Mitigación: el script reporta los
  patrones que verifica, facilitando su mantenimiento.

## Verificación

```powershell
# Modo local (determinístico, ~1 s):
python scripts/swarm_regulatory_validator.py

# Modo swarm (MCP real, opcional):
python scripts/swarm_regulatory_validator.py --mode swarm

# Tests:
python -m pytest tests/test_swarm_regulatory_validator.py -v
```

Output esperado (modo `local` sobre el repo actual):

```
================================================================
 CAL-24 — Validador regulatorio swarm (modo local)
================================================================
  CREG174Validator      PASS (5/5 checks)
  CREG101072Validator   PASS (5/5 checks)
  CREG101066Validator   PASS (5/5 checks)

  Veredicto agregado:   PASS
```

## Referencias

- ADR-0010 (CAL-10) — Excedentes Tipo 1/2 + Cvm en C1.
- ADR-0011 (CAL-15) — C4 hereda CREG 174.
- ADR-0014 (CAL-14) — Techo PES en C3.
- ADR-0016 (CAL-16) — Descomposición regulatoria del ahorro.
- Plan: `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 5.2.
