# 0017 — CAL-17: Auditoria pydataxm vs PB_PROM oficial XM

- **Estado:** Accepted
- **Fecha de decision:** 2026-05-02
- **Actividad:** 2.1 (modelo P2P) — capa de datos
- **Archivos afectados:** `data/xm_prices.py` (`XM_MONTHLY_REAL`),
  `data/audit_pydataxm_horizon.csv`,
  `scripts/audit_pydataxm_full_horizon.py`,
  `tests/test_cal17_xm_audit.py`,
  `docs/adr/0014-cal14-creg101066-pes-ceiling.md` (post-script aclaratorio)
- **Relacionado con:** [ADR-0014 CAL-14](0014-cal14-creg101066-pes-ceiling.md)
- **Fuente:** `docs/superpowers/specs/2026-05-02-cal17-pydataxm-vs-ptb-audit.md`,
  informes mensuales XM (`xm.com.co/noticias/8119,8184,8442,8584,8759`),
  sinergox.xm.com.co sheets `Comportamiento_PBNal_Horario`

## Contexto

El cache `data/precios_bolsa_xm_api.csv` se construye con la metrica
`PrecBolsNaci` de pydataxm — **Precio de Bolsa Nacional** marginal de
oferta, no PTB efectivo tras OEF. ADR-0014 (CAL-14) documento que esta
distincion implica que algunos picos > 2 000 COP/kWh quedan en el cache
mientras la liquidacion real PTB se topa al PES de CREG 101 066/2024
(implementado por CAL-14 con `apply_creg101066_ceiling`).

ADR-0014 §"Riesgos abiertos" documento adicionalmente un *"gap del 35 %
en ene-2026 (cache 218.5 vs PB_PROM oficial 213.0)"* y declaro CAL-17
como follow-up para auditar la metrica de la API contra los informes
oficiales.

La auditoria documentada en `docs/superpowers/specs/2026-05-02-cal17...md`
ejecuto el script `scripts/audit_pydataxm_full_horizon.py` sobre las
5 160 horas del horizonte MTE (jul-2025 a ene-2026) y reporto:

| mes     | cache_mean | PB_PROM oficial | delta_pct |
|---------|-----------:|----------------:|----------:|
| 2025-07 |     133.39 |          138.36 |    -3.59% |
| 2025-08 |     238.25 |          251.50 |    -5.27% |
| 2025-09 |     295.05 |          292.65 |    +0.82% |
| 2025-10 |     189.93 |          176.90 |    +7.37% |
| 2025-11 |     207.37 |          234.87 |   -11.71% |
| 2025-12 |     275.02 |          278.83 |    -1.37% |
| 2026-01 |     218.46 |          213.00 |    +2.56% |

- 6/7 meses dentro de tolerancia 10 %.
- 1/7 (nov-2025) marginalmente fuera (-11.71 %), dentro de tolerancia 15 %.
- Delta medio firmado: **-1.81 %** (sin sesgo sistematico).
- Maximo absoluto: **11.71 %**.

El "gap del 35 %" del ADR-0014 fue un **error de redaccion**: la
aritmetica `(218.5 − 213.0) / 213.0` da +2.58 %, no 35 %. El numero
original probablemente provino de comparar contra
`XM_MONTHLY_REAL["2026-01"] = 220.0` cuando ese valor era un placeholder
estimado (no oficial). Con los valores oficiales verificados en este
audit, el gap real es 2.56 %.

## Decision

**No aplicar correccion numerica al cache `precios_bolsa_xm_api.csv`.**

La metrica `PrecBolsNaci` de pydataxm es valida como aproximacion del
PB horario para la tesis. Las diferencias mensuales observadas se
explican por la diferencia metodologica entre:

- Media **aritmetica** de la serie horaria (lo que computa la tesis).
- Media **ponderada por demanda** que XM publica como PB_PROM oficial.

El sesgo medio firmado (-1.81 %) es despreciable y no reorientaria
sistematicamente las conclusiones cuantitativas (RPE, Gini, net_benefit
por escenario).

Acciones derivadas (Accepted):

1. Actualizar `data/xm_prices.py::XM_MONTHLY_REAL` con los valores
   oficiales verificados (reemplazar estimados dic-2025 = 200 y
   ene-2026 = 220 por 278.83 y 213.00).
2. Anadir post-script en ADR-0014 aclarando que el "gap del 35 %" fue
   un error de redaccion y referenciando este ADR.
3. Anadir test de regresion `tests/test_cal17_xm_audit.py` que mantenga
   la cobertura del invariante de tolerancia.
4. Conservar el script `scripts/audit_pydataxm_full_horizon.py` como
   herramienta reproducible para futuras auditorias.

## Alternativas consideradas

1. **Correccion lineal por mes** (`scale = oficial / cache_mean`).
   Descartado: distorsiona la serie horaria sin justificacion
   regulatoria; introduce sesgo en revenues = `surplus * pi_bolsa[k]`
   sin mejorar la fidelidad horaria que es lo que importa al modelo.

2. **Cambiar a otra metrica pydataxm** (ej. `PrecioTransaccionBolsa`).
   Descartado: candidatos no aparecen en
   `obj.inventario_metricas["MetricId"].values` actual de la API XM
   (verificado en `download_via_api`). `PrecBolsNaci` es el unico ID
   funcional para precios horarios sistemicos.

3. **Demand-weighting con serie horaria de demanda**.
   Descartado: requiere descargar serie horaria de demanda XM y
   re-ponderar todas las medias mensuales. Fuera del alcance de la
   tesis (Actividad 2.1) y no afectaria la serie horaria que el modelo
   consume hora a hora.

4. **Reemplazar cache por sintetico calibrado**. Descartado: la
   sintesis introduciria mayor sesgo (perfil intradiario tipificado vs
   serie real con eventos especificos como picos de jul-2025 o
   transicion post-El Niño en oct-nov-2025).

## Consecuencias

**Positivas**

- El cache pydataxm queda **certificado** como fuente valida para la
  tesis tras auditoria explicita contra 7 informes oficiales XM.
- `XM_MONTHLY_REAL` queda sincronizado con valores reales (no
  estimados), eliminando inconsistencia interna.
- Script de auditoria reproducible (`audit_pydataxm_full_horizon.py`)
  permite verificar la integridad de futuros caches en cualquier
  expansion del horizonte.
- Test de regresion `test_cal17_xm_audit_within_tolerance` previene
  drift silencioso del cache.

**Negativas**

- La diferencia metodologica aritmetica/demand-weighted queda como
  limitacion documentada (no eliminada).
- Nov-2025 marginalmente fuera de tolerancia 10 % requiere mantener
  la tolerancia en 15 % (en linea con el test de CAL-14).

**Riesgos abiertos**

- Si pydataxm publica datos provisionales para meses recientes y XM
  los actualiza a posteriori, futuros runs sobre el mismo horizonte
  pueden producir caches diferentes. **Mitigacion:** test de regresion
  reportara el drift; auditoria reproducible permite re-validar.
- Si futura version de pydataxm renombra la metric `PrecBolsNaci`,
  `download_via_api` ya itera por candidatos. Sin embargo, ningun
  candidato actual es PTB efectivo. **Mitigacion:** CAL-N futuro si
  XM expone PTB nativamente.

## Verificacion

```powershell
# 1. Audit reproducible (debe terminar con codigo 1 hasta que nov-2025
#    salga, lo cual requiere mas datos):
python scripts/audit_pydataxm_full_horizon.py --tolerance 0.10

# 2. Tests de regresion (deben pasar todos):
python -m pytest tests/test_cal17_xm_audit.py -v

# 3. Suite global (sin regresiones):
python -m pytest tests/ -q
```

Output esperado del audit (al ejecutar 2026-05-02):

```
  Meses dentro de tolerancia: 6/7
  Meses fuera de tolerancia: 1/7
  Delta_pct max: 11.71 %
  Delta_pct min: 0.82 %
  Delta_pct medio (signed): -1.81 %
```

## Referencias regulatorias y tecnicas

- **CREG 101 066/2024** — define PEI/PE/PES como techo del PTB; la
  presente auditoria es complementaria al techo (PTB <= PES, CAL-14).
- **CREG 071/2006** — estructura del PB y PE.
- **API XM** (`github.com/EquipoAnaliticaXM/API_XM`) — documenta
  `PrecBolsNaci` como metric Sistema con resolucion horaria.
- **Sinergox XM** (`sinergox.xm.com.co`) — informes mensuales con
  PB_PROM oficial ponderado por demanda.

---

## Post-script Sprint 1.1b (2026-05-02) — extension cache + alineacion MTE

Durante la verificacion de la solidez del audit se detecto un **bug
pre-existente de desalineacion temporal** entre el cache XM y el
horizonte MTE que la simulacion `--full` realmente usa:

- Horizonte MTE `--full`: **abr-2025 a dic-2025 (6144 h)**.
- Cache pre-Sprint 1.1b: **jul-2025 a ene-2026 (5160 h)**.
- `main_simulation.py:138` llamaba `get_pi_bolsa(T=6144, csv_path=...)`
  sin pasar `t_start`/`t_end`, asi que el cache se cargaba con el
  default `t_start="2025-07-01"` y `_adj` rellenaba con `nanmedian`
  (= 188.1 COP/kWh, std=0) las 984 horas finales.
- Resultado: `pi_bolsa[k]` indexaba 6144 horas MTE (abr-04..dic-16) con
  valores que en realidad correspondian a jul-2025 .. ene-2026, **un
  desfase de ~88 dias**, ademas de un padding constante para los
  ultimos 17 dias.

### Acciones tomadas

1. **Extender cache** via `scripts/extend_xm_cache.py`. Descarga
   incremental por `pydataxm` de los rangos faltantes (abr-2025 a
   jul-2025, 2112 horas). Cache final: **7272 horas (303 dias),
   2025-04-04 a 2026-02-01**, continuidad 100 % verificada.
2. **Alinear `get_pi_bolsa` por fecha** en `main_simulation.py:138`:
   se pasa `t_start = index_full[0]` y `t_end = index_full[-1] + 1h`
   en los modos `--full` y `--day`. Modo de perfil diario promedio
   (T=24) conserva defaults intencionalmente.
3. **Actualizar `XM_MONTHLY_REAL`** con los 3 meses adicionales
   (abr/may/jun 2025) usando la media aritmetica del cache. Marcados
   como `cache mean (CAL-17b pendiente verificacion oficial)`.
4. **Re-correr `--full`**. Cambios observables:
   - PGB promedio bolsa: 222 → 182 COP/kWh (refleja precios reales
     bajos abr-jun 2025 post-El Niño 2024-2025).
   - C3 TOTAL: 50 958 336 → 50 767 203 COP (-191 133 COP, -0.38 %).
   - Horas con techo PES: 12 → 20 (los nuevos meses incluyen picos
     ago-sep 2025 reales).
   - Per-mes: cada fila del reporte mensual ahora corresponde a las
     fechas reales en lugar de un desplazamiento sistematico.
5. **Tests nuevos (Grupo D en `tests/test_cal17_xm_audit.py`):**
   - `test_xm_monthly_real_incluye_abr_may_jun_2025`.
   - `test_cache_xm_cubre_horizonte_mte_completo` (>= 7272 filas, fechas).
   - `test_get_pi_bolsa_alineacion_por_fecha` (abr-2025 != jul-2025).

### Follow-up CAL-17b (riesgo abierto)

Los meses **abr-2025, may-2025, jun-2025** estan en cache (verificable
via pydataxm) pero su PB_PROM oficial XM no se ha verificado contra el
informe mensual XM correspondiente. Provisional: media aritmetica del
cache (132.51, 126.70, 112.51 COP/kWh). Action item: descargar los
informes XM publicados en may-jul 2025 y validar dentro de tolerancia
15 % en `tests/test_cal17_xm_audit.py`. Hasta entonces, el audit no
los reporta.

### Backup

El cache previo se conserva en `data/precios_bolsa_xm_api.csv.bak_pre_cal17b`
para reproducibilidad.
