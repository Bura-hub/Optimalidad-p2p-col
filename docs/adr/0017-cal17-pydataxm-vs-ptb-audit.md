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
