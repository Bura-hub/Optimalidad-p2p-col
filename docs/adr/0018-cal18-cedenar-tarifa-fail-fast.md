# 0018 — CAL-18: Cedenar verificada al 100 % + fail-fast (sin fallback silencioso)

- **Estado:** Accepted
- **Fecha de decision:** 2026-05-02
- **Actividad:** 2.1 (modelo P2P) — capa de datos
- **Archivos afectados:** `data/cedenar_tariff.py`,
  `tests/test_no_fallback_horizon.py` (nuevo)
- **Relacionado con:** [ADR-0008 CAL-8](0008-cal8-pi-gs-cedenar.md),
  [ADR-0009 CAL-9](0009-cal9-pi-gs-temporal.md),
  [ADR-0017 CAL-17](0017-cal17-pydataxm-vs-ptb-audit.md)
- **Fuente:** `docs/superpowers/specs/2026-05-02-cal18-cedenar-tarifa-fail-fast.md`,
  plan `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 1.2,
  Resolucion CREG 119/2007

## Contexto

ADR-0008 (CAL-8, abr-2025) introdujo el constante
`DEFAULT_PI_GS_FALLBACK = 650.0` en `data/cedenar_tariff.py` para tolerar
meses ausentes del CSV `tarifas_cedenar_mensual.csv` mientras se cargaban
los PDFs Cedenar progresivamente. ADR-0009 (CAL-9) elevo `pi_gs` a
matriz `(N, T)` mes a mes pero conservo el fallback como red de
seguridad para meses sin PDF.

A 2026-05-02 todos los PDFs del horizonte de la simulacion estan
cargados:

```
Cobertura Cedenar para horizonte real --full (abr-2025 a dic-2025):
  meses_horizonte: ['2025-04','2025-05','2025-06','2025-07','2025-08',
                    '2025-09','2025-10','2025-11','2025-12']
  meses_cargados:    9/9
  meses_faltantes:   []

Cobertura Cedenar para rango total CSV (abr-2025 a abr-2026):
  meses_cargados:   13/13
  meses_faltantes:   []
```

El fallback `pi_gs=650 COP/kWh` deja de activarse en condiciones de
produccion. Sin embargo, sigue presente como default silencioso, lo que
oculta drift potencial: un mes ausente en una expansion futura
produciria un escalar promedio 650 COP/kWh con `warnings.warn` (que en
CI suele ignorarse), introduciendo un sesgo invisible en `revenues =
surplus * pi_bolsa[k]` y en cualquier `savings = E_auto * pi_gs[n,k]`.

El plan
`C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 1.2
contemplaba escribir un parser PDF para reforzar la cobertura. Tras
verificar que ya esta al 100 %, la accion correcta es **eliminar el
fallback silencioso** y forzar errores explicitos para futuras
expansiones.

## Decision

**Fail-fast por defecto**: `DEFAULT_PI_GS_FALLBACK = None`.

1. La firma de las cuatro funciones publicas afectadas pasa de
   `fallback: float = DEFAULT_PI_GS_FALLBACK` a
   `fallback: float | None = DEFAULT_PI_GS_FALLBACK`:
   - `_lookup_pi_gs`
   - `effective_pi_gs`
   - `effective_pi_gs_per_agent`
   - `community_effective_pi_gs`
   - `pi_gs_per_agent_hourly`
2. Cuando el `fallback` resuelto es `None` y se necesita (mes ausente,
   institucion sin perfil, horizonte vacio), las funciones levantan
   `KeyError` o `ValueError` con mensaje detallado que:
   - cita ADR-0018,
   - indica como pasar `fallback=<valor>` literal para opt-in.
3. Se conserva `LEGACY_PI_GS_DIAGNOSTIC_FALLBACK = 650.0` exclusivamente
   para la CLI/diagnostico (`print_pi_gs_summary`), donde el modo
   informativo "muestrame todo" sigue siendo util.
4. Tests, sensibilidades, herramientas educativas o escenarios contra-
   factuales que requieran un fallback numerico **deben pasarlo de forma
   literal** (`fallback=650.0`). La suite actual no lo necesita
   (126/126 verdes sin cambios).

## Alternativas consideradas

1. **Conservar `DEFAULT_PI_GS_FALLBACK = 650.0` y solo agregar tests**.
   Descartado: deja la posibilidad de drift silencioso futuro. La regla
   del plan "todo bajo fuente fundamentada" pide eliminar el fallback,
   no solo cubrirlo con tests.

2. **Eliminar completamente el parametro `fallback`**. Descartado:
   sensibilidades y herramientas educativas se beneficiarian de poder
   pasarlo de forma explicita. Forzar la opt-in mantiene flexibilidad
   sin permitir el silencio por defecto.

3. **Escribir el parser PDF previsto en el plan**. Descartado: ya no es
   necesario. Cobertura al 100 %; el parser introduciria deuda
   tecnica sin beneficio inmediato.

4. **Reemplazar `KeyError` por `ValueError` o por una excepcion
   personalizada** (`MissingTariffMonthError`). Descartado por ahora:
   `KeyError` es semanticamente correcto (clave ausente en el indice
   pandas) y no introduce nuevos tipos de excepcion en la API publica.
   Re-evaluar si surgen necesidades de captura granular.

## Consecuencias

**Positivas**

- La cadena de datos del proyecto queda **fail-fast en produccion**: un
  mes ausente abortaria la simulacion en lugar de inyectar 650 COP/kWh
  silenciosamente.
- Mensaje de error accionable cita ADR-0018 y la opcion de opt-in
  explicito, facilitando el debugging futuro.
- La regla "todo bajo fuente fundamentada" del plan queda formalmente
  cerrada para Cedenar.
- Tests, sensibilidades y CLI siguen funcionando; el patron de
  opt-in literal hace **explicita** la presencia de fallback donde se
  use.

**Negativas**

- Codigo externo (no incluido en este repo) que importe
  `DEFAULT_PI_GS_FALLBACK` esperando un float fallara con `TypeError`
  al intentar `float(None)`. Mitigacion: hoy no hay imports externos
  documentados; la API publica del modulo se preserva.
- Una sensibilidad futura que use meses fuera del CSV debera pasar
  `fallback=<valor>` literal o ampliar el CSV. Esto es deseable
  (explicitud).

**Riesgos abiertos**

- Si el horizonte de la simulacion se extiende mas alla de abr-2026
  sin actualizar el CSV, el `--full` abortara con un mensaje claro.
  **Mitigacion:** documentado en el mensaje de error; ADR-0018 queda
  como referencia primaria.

## Verificacion

```powershell
# 1. Suite global sigue verde sin pasar fallback en ningun llamado:
python -m pytest tests/ -q --ignore=tests/test_full_simulation_preflight.py

# 2. Tests especificos CAL-18:
python -m pytest tests/test_no_fallback_horizon.py -v

# 3. Smoke test produccion: --full no cambia outputs:
python main_simulation.py --data real --full --analysis
```

Output esperado:

- 126 + 8 = 134 tests verdes.
- `--full --analysis` corre sin warning `[cedenar_tariff] Mes ... ausente`.
- KeyError documentado al pedir un mes fuera de cobertura.

## Referencias regulatorias y tecnicas

- **CREG 119/2007** — define la estructura del Costo Unitario (CU)
  utilizado por Cedenar; soporta el formato del CSV.
- **ADR-0008 (CAL-8)** — origen del fallback `650 COP/kWh`; este ADR
  lo supersede parcialmente al hacerlo opt-in.
- **ADR-0009 (CAL-9)** — eleva `pi_gs` a matriz mensual; este ADR
  cierra el ciclo eliminando el escalar de respaldo silencioso.
- **ADR-0017 (CAL-17)** — auditoria pydataxm; precedente metodologico
  de "fuente fundamentada" para `pi_bolsa`.
