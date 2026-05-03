# 0022 — CAL-22: Validación trazable de `data/mem_costs_no_regulado.csv`

- **Estado:** Accepted
- **Fecha de decisión:** 2026-05-02
- **Actividad:** 3.1-3.3 (validación regulatoria)
- **Archivos afectados:** `data/mem_costs_no_regulado.csv` (sin
  cambios; auditado), `data/mem_costs_audit.md` (nuevo),
  `tests/test_cal22_mem_costs.py` (nuevo).
- **Relacionado con:** [ADR-0016 CAL-16](0016-cal16-c2-savings-decomposition.md)
  (introduce el CSV).
- **Fuente:** plan
  `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 3.2.

## Contexto

ADR-0016 (CAL-16) introdujo `data/mem_costs_no_regulado.csv` con
tres componentes que el usuario no-regulado paga al MEM al moverse
del régimen regulado al esquema PPA bilateral (Ley 143/1994 art. 41
+ CREG 086/1996):

- **FAZNI** (Ley 1715/2014 art. 19): cargo fijo COP/kWh.
- **Contribución 4 %** sobre Gm (Ley 1117/2006 + Ley 2099/2021).
- **Comisión del representante en MEM** (CREG 156/2012): pacto
  bilateral en COP/kWh.

El CSV vigente tiene 13 filas (abr-2025 a abr-2026) con valores
constantes (FAZNI=1.90, contrib=`Gm` lit., comisión=2.00). La regla
"todo bajo fuente fundamentada" del plan
`radiant-sleeping-eagle.md` Sprint 3.2 exige una **trazabilidad
celda-fuente formal** para cada componente.

## Decisión

Aceptar los valores actuales del CSV como **referenciales
defendibles** para el horizonte 2025-2026, con la trazabilidad
documentada en
[`data/mem_costs_audit.md`](../../data/mem_costs_audit.md):

| Componente | Valor | Fuente legal | Justificación numérica |
|------------|------:|--------------|------------------------|
| FAZNI      | 1.90 COP/kWh | Ley 1715/2014 art. 19 + MinMinas Resolución 4 0067/2024 | Valor publicado UPME para vigencia 2025; constante anual. |
| Contribución 4 % | 0.04 · Gm | Ley 1117/2006 art. 2 (prorrogada Ley 2099/2021 art. 45) | Tasa fija normativa; aplicada sobre G del mes (`tarifas_cedenar_mensual.csv`). |
| Comisión representante | 2.00 COP/kWh | CREG 156/2012 + ASOCODIS 2024 (mediana mercado) | Mediana del rango típico [1.5, 3.0] COP/kWh para usuarios de ~50-200 MWh/mes; bilateral. |

**Total estimado** con `Gm ≈ 300 COP/kWh` (mediana horizonte):
**~15.90 COP/kWh** (~3 % del G, ~5 % del CU completo). Material
pero no dominante.

Acciones derivadas (Accepted):

1. Crear `data/mem_costs_audit.md` con trazabilidad celda-fuente
   por cada componente, cobertura por mes y riesgos abiertos.
2. Test `tests/test_cal22_mem_costs.py`:
   - **Schema**: 13 filas, 4 columnas, sin NaN, tipos correctos.
   - **Cobertura**: meses abr-2025 a abr-2026 sin gaps.
   - **Rangos**: FAZNI ∈ [1.0, 3.0]; comisión ∈ [0.5, 5.0]; contrib
     literal `"Gm"` o `"0.04*Gm"`.
   - **Coherencia**: el helper `mem_costs_per_agent_hourly` produce
     valores en rango razonable (~10-20 COP/kWh con G real).
3. Cualquier modificación futura del CSV debe re-ejecutar
   `mem_costs_audit.md` y este test.

## Alternativas consideradas

1. **Calibración empírica de la comisión representante** mediante
   contratos reales con representantes MEM. Descartado: requiere
   negociación bilateral fuera del alcance académico de la tesis;
   el rango [1.5, 3.0] de ASOCODIS es referencia defensible.
2. **Modelado FAZNI variable mes a mes** según resoluciones
   trimestrales UPME. Descartado: el cargo es **anual** por
   construcción legal; modelarlo mensual introduce ruido sin
   beneficio.
3. **Eliminar el CSV y hardcodear los valores** en el código.
   Descartado: el CSV permite actualizar cuando UPME publique
   nuevos valores sin tocar código (ya CAL-16 lo eligió por esa
   razón).

## Consecuencias

**Positivas**

- Cada celda del CSV tiene fuente legal explícita y trazabilidad
  numérica documentada.
- Test de regresión previene drift silencioso (cambios accidentales
  en valores).
- Plan radiant-sleeping-eagle Sprint 3.2 cierra el item "validación
  MEM costs" formalmente.
- Cobertura 13/13 meses (rango total CSV) y 9/9 meses (horizonte
  `--full`) confirmadas.

**Negativas**

- La comisión representante (2.00 COP/kWh) es estimación de mercado;
  si el proyecto contrata un representante real con tarifa distinta,
  el CSV debe actualizarse. Documentado como riesgo abierto en el
  audit.
- FAZNI puede revisarse anualmente; el audit indica el procedimiento
  de actualización.

**Riesgos abiertos**

- Ver `data/mem_costs_audit.md §"Riesgos abiertos"` para detalles.
- En particular: si UPME publica nuevo FAZNI o si la Ley 2099/2021
  expira sin prórroga, los valores actuales requerirían revisión.

## Verificación

```powershell
# Test de regresión (~1 s):
python -m pytest tests/test_cal22_mem_costs.py -v

# Suite global (sin regresiones):
python -m pytest tests/ -q --ignore=tests/test_full_simulation_preflight.py
```

## Referencias

- ADR-0016 (CAL-16) — origen del CSV.
- `data/mem_costs_audit.md` — auditoría detallada celda-fuente.
- `data/cedenar_tariff.py::mem_costs_per_agent_hourly` — helper que
  consume el CSV y produce la matriz `(N, T)`.
- Ley 1715/2014 art. 19 — FAZNI.
- Ley 1117/2006 art. 2 + Ley 2099/2021 art. 45 — Contribución 4 %.
- CREG 156/2012 — Representante en MEM.
- ASOCODIS 2024 — rangos de comisión típica para usuarios
  no-regulados.
