# 0023 — CAL-23: CXC en C2 (parametrizable, default conservador)

- **Estado:** Accepted
- **Fecha de decisión:** 2026-05-02
- **Actividad:** 3.1-3.3 (validación regulatoria)
- **Archivos afectados:** `scenarios/scenario_c2_bilateral.py`
  (parámetros `cxc_component`, `cxc_alpha`),
  `scenarios/_c2_cxc.py` (nuevo, helper opt-in),
  `data/cxc_costs.csv` (nuevo, valor referencial 10.0 COP/kWh),
  `tests/test_cal23_cxc.py` (nuevo).
- **Relacionado con:** [ADR-0016 CAL-16](0016-cal16-c2-savings-decomposition.md),
  [ADR-0020 CAL-20](0020-cal20-cot-alpha-sensibilidad.md)
  (patrón análogo: parámetro alpha opt-in).
- **Fuente:** plan
  `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 3.3.

## Contexto

El **Cargo por Confiabilidad (CXC)** financia la disponibilidad firme
del sistema eléctrico colombiano (CREG 071/2006 modificada por CREG
099/2007). Tres normas concurrentes generan ambigüedad sobre su
aplicabilidad al usuario no-regulado en esquema PPA bilateral:

| Norma | Alcance del CXC |
|-------|-----------------|
| **Decreto 2236/2023** (autogeneración colectiva) | No menciona CXC. |
| **CREG 071/2006** | Define CXC como cargo del despacho universal. |
| **CREG 086/1996** (mod. CREG 039/2001) | Permite contrato bilateral, no exime explícitamente del CXC. |

**Práctica industrial colombiana** (PPAs corporativos auditados): el
CXC se sigue cobrando al usuario aunque firme PPA — está incorporado
en los peajes regulados, no en el componente G negociable.

La pregunta abierta: ¿el modelo C2 debe descontar el CXC del costo
del usuario no-regulado (asumir que el PPA lo exime) o conservarlo
(coherente con la práctica industrial)?

Consulta usuario realizada (2026-05-02): elección **"Parametrizable
(`cxc_alpha`)"**. ADR queda Accepted con interpretación neutra —
parámetro opt-in con default conservador.

## Decisión

Implementar CXC como **componente opt-in parametrizable**, análogo a
`cot_alpha` (CAL-20) pero con default opuesto (`cxc_alpha = 0.0` vs
`cot_alpha = 1.0`):

1. Nuevos parámetros en `run_c2_bilateral`:
   - `cxc_component: np.ndarray | None = None` (matriz `(N, T)`).
   - `cxc_alpha: float = 0.0` (peso CXC ∈ [0, 1]).
2. Cuando `cxc_component is not None` y `cxc_alpha > 0`:
   `savings_CXC[i] += e * cxc_v[i, k] * cxc_alpha` por cada
   consumidor. La línea es exactamente análoga a `savings_COT`.
3. `savings_ppa = savings_G + savings_Cvm + savings_COT +
   savings_CXC - mem_costs`.
4. **Default `cxc_alpha = 0.0`**: cota conservadora. Coherente con
   la práctica industrial (CXC se sigue pagando) y con el principio
   de "sin sorpresas": activar el descuento es decisión consciente
   del modelador.

CSV `data/cxc_costs.csv`: valor referencial **10.0 COP/kWh** mensual
constante (mediana del rango ASOCODIS 2024 [5, 15] COP/kWh para CXC
liquidado). Cobertura 13/13 meses (abr-2025 a abr-2026).

Helper `scenarios/_c2_cxc.py::cxc_per_agent_hourly` carga el CSV y
produce la matriz `(N, T)`. **No** se integra al flujo principal de
`main_simulation.py` — sólo se invoca desde sensibilidades o
escenarios derivados.

## Alternativas consideradas

1. **Default `cxc_alpha = 1.0`** (descontar siempre, cota legal
   maximalista). Descartado por consulta usuario: contradice la
   práctica industrial; introduciría sesgo a favor de C2 sin
   justificación normativa firme.
2. **NO incluir CXC en el modelo** (mantener CAL-16 sin cambios).
   Descartado: cierra la puerta a sensibilidades futuras y deja un
   gap regulatorio documentado abierto.
3. **Hardcodear CXC al pi_upper** (igual que peajes T+D+PR+R).
   Descartado: el CXC tiene una interpretación discutida que
   merece ser explícita y parametrizable, no enterrada en el techo.
4. **Diferir CAL-23 a trabajo futuro**. Descartado por consulta
   usuario: el patrón parametrizable cierra el item con bajo
   riesgo (default 0.0 no afecta reportes actuales).

## Consecuencias

**Positivas**

- El CXC queda como **gap regulatorio cerrado y parametrizable** —
  cualquier discusión futura con asesores se resuelve cambiando
  `cxc_alpha`.
- Default `cxc_alpha = 0.0` no afecta los reportes actuales
  (`net_benefit C2` igual que pre-CAL-23).
- Patrón consistente con CAL-20 (`cot_alpha`): facilita
  interpretación regulatoria por componente.
- Sensibilidad triplicada disponible: `f`, `cot_alpha`, `cxc_alpha`,
  cubriendo toda la incertidumbre regulatoria de C2.

**Negativas**

- Aumenta la superficie de parámetros del modelo (11 → 12 efectivos).
  Mitigación: defaults seguros (`cxc_alpha = 0.0`).
- Valor CXC = 10 COP/kWh es referencial; sensibilidad real depende
  del contrato del representante MEM. Documentado en CSV `nota`.
- Introduce un nuevo CSV mensual que requiere mantenimiento si la
  CREG actualiza la fórmula CXC. Mitigación: 13 filas constantes;
  trivial actualizar.

**Riesgos abiertos**

- Si en el futuro el proyecto contrata un representante MEM con
  estructura de CXC distinta, el CSV debe actualizarse. **Mitigación:**
  documentado en `data/cxc_costs.csv::nota`.
- La práctica industrial puede cambiar tras nuevas resoluciones CREG
  sobre autogeneración colectiva (post-Decreto 2236/2023). Si así
  sucede, re-evaluar el default `cxc_alpha = 0.0`. **Mitigación:**
  ADR queda como punto de referencia; cualquier cambio regulatorio
  se trataría como nuevo CAL-N.

## Verificación

```powershell
# Tests de regresión (~5 s):
python -m pytest tests/test_cal23_cxc.py -v

# Suite global (sin regresiones):
python -m pytest tests/ -q --ignore=tests/test_full_simulation_preflight.py
```

**Invariantes verificados:**

- Default sin pasar `cxc_component`: `savings_CXC = 0` exacto;
  el flujo de C2 actual no cambia.
- Linealidad: `savings_CXC(α=2) = 2 · savings_CXC(α=1)`.
- Inercia con `consumer_ids = []`: `cxc_alpha` es inerte (igual que
  `cot_alpha`).
- Schema CSV: 13 filas, 3 columnas, valores en banda razonable.

## Referencias

- ADR-0016 (CAL-16) — descomposición regulatoria del ahorro;
  patrón replicado.
- ADR-0020 (CAL-20) — `cot_alpha` análogo (default opuesto 1.0).
- CREG 071/2006 (mod. CREG 099/2007) — define CXC.
- Decreto 2236/2023 — autogeneración colectiva sin mención CXC.
- CREG 086/1996 (mod. CREG 039/2001) — usuario no-regulado.
- ASOCODIS 2024 — rangos típicos CXC liquidado [5, 15] COP/kWh.
- Consulta usuario 2026-05-02: opción "Parametrizable (cxc_alpha)".
