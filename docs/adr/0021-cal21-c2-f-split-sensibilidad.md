# 0021 — CAL-21: Sensibilidad del split factor `f` en C2 (sustento `f = 0.5`)

- **Estado:** Accepted
- **Fecha de decision:** 2026-05-02
- **Actividad:** 3.1-3.3 (validacion regulatoria)
- **Archivos afectados:** `scripts/study_f_split.py` (nuevo),
  `graficas/sensibilidad_f.{csv,png,mat}`,
  `tests/test_cal21_f_sensibilidad.py`,
  `main_simulation.py` (constante `F_PPA_DEFAULT` + ADR-0021).
- **Relacionado con:** [ADR-0011 CAL-11](0011-cal11-c2-ppa-bilateral-modelo-formal.md)
  (introduce `f`),
  [ADR-0016 CAL-16](0016-cal16-c2-savings-decomposition.md),
  [ADR-0020 CAL-20](0020-cal20-cot-alpha-sensibilidad.md)
- **Fuente:** plan
  `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 3.1.

## Contexto

ADR-0011 (CAL-11) postulo `f = 0.5` como factor de reparto del spread
del precio PPA: `pi_ppa = pi_gb + f * (pi_upper - pi_gb)`. La spec
auditada PPAs colombianos reales y observo que `f` empirico cae en
`[-3.08, +0.029]` — ningun contrato real esta cerca de 0.5. La
eleccion `0.5` se introdujo como **postulado normativo** de simetria
egalitaria, sin barrido empirico de sensibilidad.

CAL-16 (ADR-0016) demostro un **teorema de invarianza** (notas §3.8):
para una **comunidad cerrada** (todos los excedentes del prosumidor
los compran consumidores de la misma comunidad) el `total_net_benefit`
es invariante en `f`. Lo que cambia es la **distribucion** entre
prosumidor y consumidor (medible via Gini).

La regla "todo bajo fuente fundamentada" del plan
`radiant-sleeping-eagle.md` exige verificar empiricamente:

  H1. `total_net_benefit C2` es invariante en `f` (corolario CAL-11/16).
  H2. `Gini(net_benefit)` NO es invariante en `f` (justifica SA-3).
  H3. `f = 0.5` produce el split egalitario (50/50 del spread).

## Auditoria ejecutada

`scripts/study_f_split.py` corre `run_c2_bilateral` con
`f in {0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0}` sobre 168 h MTE
(2025-08-04 a 2025-08-11). Como en CAL-20, MTE real tiene
`consumer_ids = []` y `f` queda inerte; se aplica el split
ilustrativo (top-3 cobertura prosumers + bottom-2 consumers).

Parametros: `pi_gb = 280`, `pi_upper = 513.2 = G + Cvm + 1*COT - MEM`,
spread = 233.2 COP/kWh.

| `f` | pi_ppa | net_benefit total | savings_gen | savings_ppa | nb prosumer mean | nb consumer mean | Gini |
|----:|-------:|------------------:|------------:|------------:|-----------------:|-----------------:|-----:|
| 0.00 | 280.0 | 791 289 | 740 397 | 50 891     | 246 799 | 25 446 | 0.436 |
| 0.10 | 303.3 | 791 289 | 745 486 | 45 802     | 248 495 | 22 901 | 0.442 |
| 0.25 | 338.3 | 791 289 | 753 120 | 38 169     | 251 040 | 19 084 | 0.451 |
| **0.50** | **396.6** | **791 289** | **765 843** | **25 446** | **255 281** | **12 723** | **0.466** |
| 0.75 | 454.9 | 791 289 | 778 566 | 12 723     | 259 522 | 6 361  | 0.480 |
| 0.90 | 489.9 | 791 289 | 786 200 | 5 089      | 262 067 | 2 545  | 0.489 |
| 1.00 | 513.2 | 791 289 | 791 289 | ~0         | 263 763 | ~0     | 0.495 |

(168 h, split ilustrativo prosumers=[Udenar, Mariana, Cesmag],
consumers=[UCC, HUDN].)

**Resultados (las tres hipotesis ratificadas):**

1. **H1 ratificada (teorema de invarianza)**: `total_net_benefit
   = 791 289` COP para los 7 valores de `f`; `Δ vs f = 0.5` es
   `1.5e-14 %` (precision numerica del float). Confirma el teorema
   §3.8 sobre datos reales MTE (no solo en demostracion algebraica).

2. **H2 ratificada (Gini no invariante)**: Gini sube monotonicamente
   de 0.436 (f=0) a 0.495 (f=1), un rango de 0.059 puntos. Justifica
   explicitamente el reporte SA-3 por `f` (CAL-11) en la tesis.

3. **H3 ratificada (egalitaridad)**: con `f = 0.5`, `nb prosumer mean
   = 255 281` y `nb consumer mean = 12 723`. La distribucion del
   **incremento marginal del spread** entre prosumidor y consumidor
   es exactamente lineal y simetrica respecto a `f = 0.5` (cada
   `Δf = 0.1` mueve `~Δ 1 700` del consumer al prosumer y viceversa).

4. **Trade-off interno explicito**: a medida que `f` crece, `savings_gen`
   (autoconsumo del prosumidor) absorbe progresivamente lo que era
   `savings_ppa`; la suma se conserva. Eso es lo que produce la
   invarianza H1.

## Decision

Mantener **`f = 0.5`** como default global, ratificado por:

- **Teorema de invarianza** (CAL-11/16, §3.8) — la metrica principal de
  comparacion (`total_net_benefit C2`) no depende de `f`.
- **Egalitaridad** — `f = 0.5` es el unico valor con simetria
  perfecta entre prosumidor y consumidor en el reparto del spread
  marginal.
- **Estabilidad de Gini** alrededor del default — el Gini en `f = 0.5`
  es 0.466, exactamente la mediana del intervalo `[0.436, 0.495]`
  observado.
- **Defensibilidad academica** — al ser un postulado normativo
  declarado y demostrado invariante para la metrica principal, no
  es una libertad oculta sino una eleccion explicita y justificada.

Acciones derivadas (Accepted):

1. `scripts/study_f_split.py` queda como herramienta reproducible.
2. Test de regresion `tests/test_cal21_f_sensibilidad.py`:
   - Verifica invarianza (`total_net_benefit(f=0) ==
     total_net_benefit(f=1)` con tolerancia 1e-9 %).
   - Verifica Gini monotono creciente en `f`.
   - Verifica simetria: `nb_prosumer_mean(0.5) - nb_consumer_mean(0.5)`
     es la mediana del rango `[0,1]`.
   - Verifica que con `consumer_ids = []`, `f` es inerte (caso MTE
     real).
3. `main_simulation.py:370,380`: extraer `f` a constante con nombre
   `F_PPA_DEFAULT = 0.5` y comentario que cite ADR-0021.

## Alternativas consideradas

1. **`f` derivado de PPAs colombianos auditados**. Descartado: la
   spec CAL-11 audita 4 contratos publicos (UPME, ANDI) con `f
   in [-3.08, +0.029]` y comportamientos no representativos del caso
   MTE (PPAs corporativos vs comunidad academica). El intervalo es
   demasiado disperso para sustentar un default empirico.
2. **`f = 0.0` (toda la utilidad al consumidor)**. Descartado: rompe
   el incentivo del prosumidor a ofertar; en el limite `f = 0`,
   `pi_ppa = pi_gb` y el prosumidor no gana nada por participar
   (vs solo vender excedente a la red).
3. **`f = 1.0` (toda al prosumidor)**. Descartado: rompe el
   incentivo del consumidor a comprar; en el limite `nb consumer
   = 0` y el contrato no se firmaria.
4. **Hacer `f` parametro por agente** (`f_n`). Descartado:
   complejidad innecesaria sin evidencia de heterogeneidad
   relevante; SA-3 ya cubre el rango.

## Consecuencias

**Positivas**

- Default `f = 0.5` queda sustentado por tres argumentos
  cuantitativos independientes (invarianza, simetria, estabilidad
  Gini).
- Cualquier discusion futura sobre el split puede referirse a CAL-21
  con tabla concreta y plot de sensibilidad.
- El teorema de invarianza queda demostrado tambien numericamente,
  no solo algebraicamente (notas §3.8).
- Test de regresion previene drift silencioso.

**Negativas**

- En MTE real (`consumer_ids = []`) el parametro es inerte; el
  default 0.5 no afecta los reportes actuales. Esto se documenta
  explicitamente como en CAL-20.
- Para configuraciones futuras donde la comunidad tenga
  consumidores externos, la robustez del agregado sigue valida pero
  el Gini cambia; el reporte SA-3 (CAL-11) cubre ese caso.

**Riesgos abiertos**

- En comunidades **abiertas** (consumidores fuera de la comunidad),
  el teorema de invarianza puede no aplicar exactamente; CAL-11
  reservo este caso a la spec out-of-scope. Si se modela esa
  apertura, deberia auditar empiricamente la sensibilidad de
  `total_net_benefit`. **Mitigacion:** documentado en CAL-11
  spec; CAL-N futuro si se modela.

## Verificacion

```powershell
# Barrido completo (~5 s):
python scripts/study_f_split.py

# Tests de regresion (~5 s):
python -m pytest tests/test_cal21_f_sensibilidad.py -v

# Suite global (sin regresiones):
python -m pytest tests/ -q --ignore=tests/test_full_simulation_preflight.py
```

Output esperado del barrido:

```
| f    | total_net_benefit | Gini  | delta_nb_vs_f05_pct |
|------|------------------:|------:|--------------------:|
| 0.0  | 791 289           | 0.436 | ~1e-14 %            |
| 0.5  | 791 289           | 0.466 | 0                   |
| 1.0  | 791 289           | 0.495 | ~1e-14 %            |
```

## Referencias

- ADR-0011 (CAL-11) — formalizacion del modelo PPA y `f` postulado.
- ADR-0016 (CAL-16) — descomposicion regulatoria; introduce
  `pi_upper = G + Cvm + alpha*COT - MEM`.
- `Documentos/notas_modelo_tesis.md §3.8` — teorema de invarianza.
- `tests/test_c2_bilateral.py::test_invarianza_bienestar_agregado_comunidad_cerrada`
  y `::test_gini_no_invariante_a_f` — sustento algebraico previo.
- `main_simulation.py:370,380` — punto donde se aplica `f = 0.5`.
