# CAL-18 — Cedenar verificada al 100 % + fail-fast (sin fallback silencioso)

- **Fecha de inicio:** 2026-05-02
- **Actividad:** 2.1 (modelo P2P) — capa de datos
- **ADR objetivo:** [`docs/adr/0018-cal18-cedenar-tarifa-fail-fast.md`](../../adr/0018-cal18-cedenar-tarifa-fail-fast.md)
- **Origen del trabajo:** plan
  `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 1.2,
  reformulado tras verificar cobertura Cedenar al 100 % en el horizonte
  actual.

## Contexto

El plan original de Sprint 1.2 contemplaba escribir un parser PDF para
descargar las facturas Cedenar de jul-ago 2025 y eliminar el fallback
`pi_gs=650 COP/kWh`. Verificacion del estado real del CSV
`data/tarifas_cedenar_mensual.csv` mostro que **el fallback ya no se
activa en el horizonte real de la simulacion**:

```
Cobertura Cedenar para horizonte real --full (abr-2025 a dic-2025):
  meses_horizonte:  9 meses (2025-04 a 2025-12)
  meses_cargados:   9/9
  meses_faltantes:  []
```

El parser PDF deja de ser necesario; el riesgo academico de "33 % de
horizonte con fallback" identificado en la auditoria inicial ya no
existe (sucesivos commits CAL-9..CAL-13 cargaron PDFs faltantes).

Sin embargo, el constante `DEFAULT_PI_GS_FALLBACK = 650.0` sigue vivo
en el codigo. Si en el futuro alguien:

- extiende el horizonte mas alla de abr-2026, o
- olvida cargar un PDF nuevo cuando publica Cedenar, o
- prueba un escenario contra-factual con un mes ficticio,

obtendria silenciosamente un escalar 650 COP/kWh con un `warnings.warn`
que tipicamente se ignora en CI o se mezcla con otros mensajes. Eso
introduciria un sesgo invisible.

## Decision

Cambiar el modulo `data/cedenar_tariff.py` a **fail-fast** por defecto:

1. `DEFAULT_PI_GS_FALLBACK: float | None = None` (antes `650.0`).
2. Todas las funciones que aceptan `fallback` lo tipan como
   `float | None` y, cuando el valor efectivo es `None` y un mes esta
   ausente o un agente sin perfil, **levantan `KeyError`** con un
   mensaje detallado que cita ADR-0018 y la opcion de opt-in literal.
3. Se conserva `LEGACY_PI_GS_DIAGNOSTIC_FALLBACK = 650.0` exclusivamente
   para la salida CLI/diagnostica (`cedenar_tariff.py` cuando se ejecuta
   directamente o desde `print_pi_gs_summary`), donde el comportamiento
   informativo de "muestrame todo aunque haya gaps" sigue siendo util.
4. Cualquier test, sensibilidad o herramienta que **realmente** necesite
   un fallback numerico debe pasar `fallback=<float>` de forma literal.

Esta decision es coherente con la regla "todo bajo fuente fundamentada"
del plan: si Cedenar no tiene un mes, el codigo lo dice de forma
explicita en lugar de inventar un valor.

## Hipotesis a falsar

H0: Tras el cambio, la suite completa de tests sigue verde sin pasar
`fallback` explicitamente porque el horizonte real esta 100 % cubierto.

H1: Cualquier extension futura del horizonte fuera de la cobertura
Cedenar produce un `KeyError` con mensaje accionable que cita ADR-0018.

## Plan de implementacion

| Paso | Accion | Archivo |
|------|--------|---------|
| 1 | Cambiar `DEFAULT_PI_GS_FALLBACK` a `None` + `LEGACY_*` constante | `data/cedenar_tariff.py:67` |
| 2 | Actualizar firmas de 4 funciones publicas a `float \| None` | `data/cedenar_tariff.py` (4 funcs) |
| 3 | `_lookup_pi_gs`: raise KeyError cuando fallback is None | `data/cedenar_tariff.py:159` |
| 4 | `effective_pi_gs`: raise ValueError si horizonte vacio y fallback None | `data/cedenar_tariff.py:238` |
| 5 | `effective_pi_gs_per_agent`: raise si agente sin perfil y fallback None | `data/cedenar_tariff.py:269` |
| 6 | `pi_gs_per_agent_hourly`: misma proteccion | `data/cedenar_tariff.py:337` |
| 7 | CLI `print_pi_gs_summary`: usa LEGACY constante explicito | `data/cedenar_tariff.py:940-976` |
| 8 | Crear ADR-0018 (Accepted) | `docs/adr/0018-cal18-cedenar-tarifa-fail-fast.md` |
| 9 | Test de regresion `test_no_fallback_horizon.py` | `tests/` |
| 10 | Actualizar `docs/adr/README.md` | indice |
| 11 | Sembrado Ruflo (Sprint 1.3) | `scripts/seed_ruflo_adr.py` |

## Tests requeridos

`tests/test_no_fallback_horizon.py`:

1. `test_default_fallback_is_none` — invariante: `DEFAULT_PI_GS_FALLBACK is None`.
2. `test_legacy_diagnostic_fallback_preserved` — `LEGACY_PI_GS_DIAGNOSTIC_FALLBACK == 650.0`.
3. `test_lookup_raises_when_month_missing_default` — mes fuera de cobertura sin fallback explicito → KeyError.
4. `test_lookup_uses_fallback_when_explicit` — fallback=600 → emite warning, retorna 600.
5. `test_effective_pi_gs_full_horizon_works` — abr-2025 a dic-2025 sin fallback → no raise.
6. `test_effective_pi_gs_outside_horizon_raises` — ene-2025 (fuera de cobertura) → KeyError.
7. `test_pi_gs_per_agent_hourly_full_horizon_works` — matriz NxT sin fallback → no raise.
8. `test_keyerror_mentions_adr_0018` — mensaje del KeyError cita ADR-0018 (rastreabilidad).

## Out-of-scope

- Parser PDF Cedenar (no necesario; cobertura 100 %).
- Extension del horizonte simulacion (gobernada por `xm_data_loader.T_*`).
- Modificacion del CSV `tarifas_cedenar_mensual.csv` (intacto).
- Carga de meses ene/feb/mar 2025 (estarian fuera del MTE solido comun).

## Riesgos

- Tests/scripts externos que dependian del fallback silencioso fallaran
  con KeyError. **Mitigacion:** mensaje del error indica explicitamente
  como pasar `fallback=<valor>`. La suite actual (126 tests) pasa sin
  modificaciones, lo que indica que ningun test productivo depende del
  fallback silencioso.
- CLI diagnostica sigue funcionando porque pasa el literal
  `LEGACY_PI_GS_DIAGNOSTIC_FALLBACK = 650.0`. Si alguien importa el
  modulo con un mes faltante y no usa la CLI, vera la nueva exception.

## Referencias

- Plan: `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 1.2.
- ADR-0009 (CAL-9): tarifa pi_gs temporal mes a mes (matriz N x T).
- ADR-0008 (CAL-8): origen del fallback 650 (parcial Superseded).
- Resolucion CREG 119/2007 — estructura del CU.
