# 0020 — CAL-20: Sensibilidad de `cot_alpha` en C2 + sustento del default 1.0

- **Estado:** Accepted
- **Fecha de decision:** 2026-05-02
- **Actividad:** 3.1-3.3 (validacion regulatoria)
- **Archivos afectados:** `scripts/study_cot_alpha.py` (nuevo),
  `graficas/sensibilidad_cot_alpha.{csv,png,mat}`,
  `tests/test_cal20_cot_alpha.py`
- **Relacionado con:** [ADR-0016 CAL-16](0016-cal16-c2-savings-decomposition.md)
  (introduce `cot_alpha`),
  [ADR-0013 CAL-13](0013-cal13-c2-no-regulado.md)
- **Fuente:** plan
  `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 2.2.

## Contexto

CAL-16 (ADR-0016) introdujo el parametro `cot_alpha ∈ [0, 1]` (con
posibles extensiones a [0, 2] para sensibilidad) en
`scenarios/scenario_c2_bilateral.py`. Modela la fraccion del
**Cargo del Operador del Tariador (COT)** efectivamente "ahorrada"
por el usuario no-regulado al moverse al esquema PPA bilateral. El
default fijado fue `cot_alpha = 1.0` por consistencia con la cota
pesimista del modelo CAL-13.

La regla "todo bajo fuente fundamentada" del plan
`radiant-sleeping-eagle.md` (Sprint 2.2) exige sustentar el default
con un barrido empirico de sensibilidad y aclarar su impacto sobre
la metrica `net_benefit C2`.

## Marco regulatorio

| Norma | Aplicabilidad sobre COT |
|-------|------------------------|
| **Ley 143/1994 art. 41** | Usuario no-regulado puede contratar PPA bilateral; queda fuera del comercializador minorista. |
| **CREG 086/1996 art. 1** (mod. CREG 039/2001) | Usuario no-regulado: demanda >= 55 MWh/mes o potencia >= 100 kW (las 5 instituciones MTE califican). |
| **CREG 101-028/2023** | Introduce el cargo COT como obligacion del comercializador minorista al usuario regulado. |
| **CREG 174/2021 art. 25** | NO menciona COT en la liquidacion de excedentes; literalidad cita solo `Cvm,i,j` de CREG 119/2007. |

**Lectura conjunta:** un usuario que pasa al esquema PPA bilateral
(no-regulado) deja de tener comercializador minorista; por tanto,
**no paga COT**. Cuanto del COT que pagaba como regulado aparece
como "ahorro" depende de:

1. La fraccion del COT que su comercializador anterior efectivamente
   le facturaba (siempre 100 % en las facturas Cedenar revisadas).
2. La cota interpretativa del modelo:
   - `cot_alpha = 1.0`: cota legal/maxima (no paga nada de COT).
   - `cot_alpha = 0.5`: cota conservadora (incertidumbre 50/50).
   - `cot_alpha = 0.0`: cota minima (no se cuenta como ahorro).

## Auditoria ejecutada

`scripts/study_cot_alpha.py` corre `run_c2_bilateral` con
`cot_alpha in {0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0}` sobre
168 h MTE (2025-08-04 a 2025-08-11). Pre-requisito: dado que las 5
instituciones MTE son todas prosumidoras, `consumer_ids = []`
inhibe el flujo PPA. Para activar el flujo y observar la
sensibilidad se aplica un **split ilustrativo** por cobertura G/D
(top-3 prosumers, bottom-2 consumers).

| `cot_alpha` | net_benefit C2 [k$] | savings_COT [k$] | Δ vs α=1.0 [%] |
|------------:|--------------------:|-----------------:|---------------:|
| 0.00        | 782.1               | 0.0              | -1.16          |
| 0.25        | 784.4               | 2.3              | -0.87          |
| 0.50        | 786.7               | 4.6              | -0.58          |
| 0.75        | 789.0               | 6.9              | -0.29          |
| **1.00**    | **791.3**           | **9.2**          | **0.00**       |
| 1.25        | 793.6               | 11.5             | +0.29          |
| 1.50        | 795.9               | 13.8             | +0.58          |
| 2.00        | 800.5               | 18.4             | +1.16          |

(Periodo: 168 h, split ilustrativo prosumers=[Udenar, Mariana, Cesmag],
consumers=[UCC, HUDN].)

**Lecturas:**

1. **Linealidad perfecta confirmada**: `net_benefit C2(α) =
   baseline + α · savings_COT_unit`. Cada incremento `Δα = 0.25`
   produce `Δ net_benefit ≈ +0.29 %` en este split. La pendiente
   depende del split y de los componentes COT del periodo, pero la
   forma funcional es lineal por construccion (linea 201 de
   `scenario_c2_bilateral.py`).

2. **Inercia en MTE actual (5 prosumers, 0 consumers)**: cuando
   `consumer_ids = []` (configuracion real `--full`), el flujo PPA
   no se activa, `savings_COT = 0` y `cot_alpha` queda
   **completamente inerte**. La eleccion del default no afecta
   numericamente los reportes actuales (`resultados_comparacion.xlsx`,
   `REPORTE_AVANCES.md`).

3. **Magnitud bajo split ilustrativo**: con 3 prosumers + 2 consumers
   sobre 168 h, mover `α` de 0 a 1 cambia el net_benefit C2 en ~9.2
   k$, equivalente a 1.16 % del net_benefit total. Bajo, pero NO
   despreciable.

4. **Sustento del default `α = 1.0`**: regulatoriamente correcto
   bajo Ley 143/1994 + CREG 086/1996 + CREG 101-028/2023 — el
   usuario no-regulado NO tiene comercializador minorista, por
   tanto deja de pagar el COT en su totalidad.

## Decision

Mantener **`cot_alpha = 1.0`** como default global, ratificado por:

- **Marco legal**: usuario no-regulado no paga COT (CREG 086/1996
  art. 1; Ley 143/1994 art. 41).
- **Linealidad**: el parametro afecta `net_benefit C2` de forma
  lineal y predecible; cualquier sensibilidad alrededor del default
  se obtiene por interpolacion sin re-correr.
- **Inercia operativa**: en MTE actual `consumer_ids = []` deja
  inerte el parametro; el default no afecta reportes
  cuantitativos publicados.

Acciones derivadas (Accepted):

1. `scripts/study_cot_alpha.py` queda como herramienta reproducible
   para sensibilidad antes de defensa o ante cambios de
   configuracion (split prosumers/consumers).
2. Test de regresion `tests/test_cal20_cot_alpha.py`:
   - Verifica linealidad (`net_benefit(α=2) − net_benefit(α=0) =
     2 · (net_benefit(α=1) − net_benefit(α=0))`).
   - Verifica que `cot_alpha` es inerte cuando
     `consumer_ids = []`.
   - Verifica que `savings_COT` es proporcional a `cot_alpha`.
3. ADR-0016 conserva el contrato: el flujo en
   `scenario_c2_bilateral.py:201` usa `α · cot_v[i, k]` y NO
   cambia.

## Alternativas consideradas

1. **`cot_alpha = 0.5` (compromiso intermedio)**. Descartado: no
   tiene fundamento regulatorio. Se introduciria como cota
   "conservadora-prudente" sin base normativa; el plan exige
   "fuente fundamentada".
2. **`cot_alpha = 0.0` (cota minima)**. Descartado: equivale a
   asumir que el comercializador minorista sigue cobrando COT al
   no-regulado, lo cual contradice CREG 086/1996.
3. **Hacer `cot_alpha` parametrizable por agente
   (`cot_alpha_v: np.ndarray`)**. Descartado: complejiza la API
   sin beneficio empirico (los componentes COT varian poco entre
   instituciones del mismo nivel de tension).
4. **Eliminar el parametro y fijar el ahorro al 100 %**. Descartado:
   el parametro es util para sensibilidades en defensa; mantenerlo
   con default 1.0 cubre ambos usos.

## Consecuencias

**Positivas**

- Default `cot_alpha = 1.0` queda sustentado con barrido empirico,
  base regulatoria explicita y prueba de linealidad.
- Cualquier sensibilidad future (e.g. asesor pide explorar
  `α = 0.5`) se calcula por interpolacion lineal sin nueva
  corrida.
- La inercia en MTE actual queda documentada: el parametro NO
  afecta reportes publicados; defenderia critica academica que
  pidiera "modificar `cot_alpha` no impacto el modelo".
- Test de regresion previene drift silencioso.

**Negativas**

- El barrido se ejecuta sobre un split artificial (no la config
  MTE real); esto se documenta explicitamente como ilustrativo.
- Para configuraciones futuras con consumer_ids no vacio (e.g.
  comunidad MTE compra excedente externo), el parametro pasaria
  a ser sensible y requerira re-validacion empirica.

**Riesgos abiertos**

- Si CREG emite una resolucion futura que aclare la aplicabilidad
  de COT al no-regulado de forma contraria al supuesto actual, el
  default deberia revisarse. **Mitigacion:** ADR documenta la
  decision; cualquier cambio normativo se trataria como nuevo
  CAL-N.
- `pi_ppa` se computa como `mean(g_comp)` en el barrido; esa
  eleccion afecta absolutamente la magnitud de `savings_COT` pero
  no la linealidad. La sensibilidad sobre `pi_ppa` se cubre en
  CAL-21 (Sprint 3).

## Verificacion

```powershell
# Barrido completo (~5 s):
python scripts/study_cot_alpha.py

# Tests de regresion (~10 s):
python -m pytest tests/test_cal20_cot_alpha.py -v

# Suite global (sin regresiones):
python -m pytest tests/ -q --ignore=tests/test_full_simulation_preflight.py
```

Output esperado del barrido:

```
| cot_alpha | net_benefit C2 [k$] | delta vs alpha=1.0 [%] |
|----------:|--------------------:|-----------------------:|
| 0.00      | ~782                | -1.16                 |
| 1.00      | ~791 (referencia)   |  0.00                 |
| 2.00      | ~800                | +1.16                 |
```

(Linealidad: `delta_pct(0) = -delta_pct(2)`.)

## Referencias

- ADR-0013 (CAL-13) — C2 alineado con marco no-regulado.
- ADR-0016 (CAL-16) — descomposicion regulatoria del ahorro;
  introduce `cot_alpha`.
- `scenarios/scenario_c2_bilateral.py:201` — punto donde
  `cot_alpha` afecta `savings_COT`.
- Ley 143/1994 art. 41 — autoriza PPA bilateral.
- CREG 086/1996 (mod. CREG 039/2001) — define usuario no-regulado.
- CREG 101-028/2023 — introduce COT al usuario regulado.
- CREG 174/2021 art. 25 — literalidad: solo cita Cvm.
