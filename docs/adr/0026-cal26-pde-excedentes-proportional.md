# 0026 — CAL-26: PDE proporcional a excedentes (método opt-in)

- **Estado:** Accepted
- **Fecha de decision:** 2026-05-03
- **Actividad:** 4.1 + 4.2 (escritura paper) + 3.1-3.3 (validación regulatoria)
- **Archivos afectados:** `scenarios/scenario_c4_creg101072.py`
  (extender `compute_pde_weights`),
  `tests/test_cal26_pde_excedentes.py` (nuevo),
  `scripts/run_paper_iter.py` (uso del método nuevo).
  **NO toca** el default actual `capacity_proportional` (CAL-15 intacto).
- **Relacionado con:** ADR-0011 (CAL-15) — implementación PDE estática.
- **Fuente:** plan
  `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 6.2;
  reunión asesores 2026-05-01 (`Reunion0105.txt` líneas 354-379).

## Contexto

ADR-0011 (CAL-15) implementó `compute_pde_weights` con dos métodos:

- `capacity_proportional` (default): `PDE_n = cap_n / Σ cap_m`
- `equal`: `PDE_n = 1/N`

Ambos son **estáticos** y se calculan a partir de la capacidad
instalada, no de la generación efectiva. El abstract WEEF y la
reunión con asesores (2026-05-01) sugirieron **probar también
el método proporcional a la energía excedente** efectivamente
generada por cada agente.

Cita literal asesor (líneas 358-378):

> *"se puede trabajar con porcentaje de distribución equitativo, me
> parece, pues, no sé, **o** de acuerdo **o** proporcional a la
> cantidad de energía excedente… no equitativo, no coger toda la
> plata que sobró… sino proporcional a cuánto en el mes vendió
> cada uno… eso es más justo para quienes claramente vendieron más"*

### Marco regulatorio

| Norma | Aplicabilidad |
|---|---|
| **CREG 101 072/2025 art. 5** | Cita `capacity_proportional` y `equal` como referencia. Permite "ponderadores acordados entre miembros". |
| **Decreto 2236/2023 art. 4** | AGRC heredan régimen AGPE. No prescribe método PDE específico. |

`excedentes_proportional` cae en "ponderadores acordados entre
miembros" — admisible pero no listado. Esta es la razón por la cual
**se mantiene `capacity_proportional` como default global** (alineado
con la letra de la CREG) y `excedentes_proportional` queda **opt-in**
para análisis de robustez.

## Decisión

Extender `compute_pde_weights` con un nuevo método
`method="excedentes_proportional"` que recibe los excedentes
acumulados `(N,)` por agente:

```
PDE_n^(exc) = exc_n / Σ_m exc_m
```

Donde `exc_n = Σ_t max(G_n(t) − D_n(t), 0)` es el excedente bruto
agregado del agente sobre la ventana de tiempo (mes, horizonte).

**Helper nuevo** `compute_excedentes_acumulados(G, D) -> np.ndarray`
que computa el vector `(N,)` a partir de las matrices `(N, T)`.

**Default**: sin cambios. `compute_pde_weights(capacity)` con
`method="capacity_proportional"` sigue siendo el camino estándar.

**Uso opt-in**:
```python
from scenarios.scenario_c4_creg101072 import (
    compute_pde_weights, compute_excedentes_acumulados,
)
exc = compute_excedentes_acumulados(G, D)  # (N,)
pde = compute_pde_weights(exc, method="excedentes_proportional")
```

`scripts/run_paper_iter.py` activa este método con
`--pde excedentes`. El paper reporta **ambos lado a lado**
(C2-cap, C2-exc) para demostrar robustez del análisis.

## Alternativas consideradas

1. **Cambiar el default global a `excedentes_proportional`**.
   Descartado: rompe baseline post-CAL-23 y contradice CREG 101 072
   art. 5 que cita `capacity` explícitamente.
2. **Función nueva separada `compute_pde_weights_from_excedentes`**.
   Descartado: duplica firmas; `compute_pde_weights(metric, method=...)`
   ya soporta polimorfismo de la métrica.
3. **PDE temporal mes a mes** (en lugar de estático). Descartado: el
   paper se limita a un mes (decisión G), no hay diferencia.
   La tesis puede explorar PDE temporal como CAL-N futuro.

## Consecuencias

**Positivas**

- Default sin cambios (`capacity_proportional`): tesis y baseline
  post-CAL-23 intactos.
- Paper reporta ambos métodos lado a lado → robustez explícita.
- Patrón coherente con ADRs previos opt-in (`cot_alpha` CAL-20,
  `cxc_alpha` CAL-23).
- API minimalmente extendida: 1 método nuevo, 1 helper nuevo.
- Coherente con CREG 101 072 art. 5 ("acordados entre miembros").

**Negativas**

- API ahora acepta dos significados para el primer argumento de
  `compute_pde_weights`: capacidad (kW) o excedentes (kWh). El
  usuario debe pasar la métrica correcta según `method`.
  **Mitigación**: docstring explícito; helper dedicado.

**Riesgos abiertos**

- Posibilidad de "gaming": en una comunidad real, una institución
  podría reducir su demanda artificialmente para aumentar excedentes
  y subir su PDE. **Mitigación**: documentado como limitación; el
  método se usa solo en análisis académico, no en contrato real.
- Si el paper muestra que `excedentes_proportional` cambia el ranking
  P2P vs C2, abre discusión regulatoria adicional. **Mitigación**:
  el paper lo presenta como sensibilidad de robustez, no como
  recomendación de cambiar el default.

## Verificación

```powershell
# Tests unitarios:
python -m pytest tests/test_cal26_pde_excedentes.py -v

# Smoke con paper en agosto:
python scripts/run_paper_iter.py --month 2025-08 --pde excedentes \
    --tag pde_exc

# Comparar contra capacity:
python scripts/run_paper_iter.py --month 2025-08 --pde capacity \
    --tag pde_cap
```

Output esperado: dos xlsx, mismo formato, valores distintos en
C2 (CREG 101 072) según el método PDE.

## Referencias

- ADR-0011 (CAL-15) — implementación PDE estática original.
- CREG 101 072/2025 art. 5 — define `capacity` y `equal` como
  referencias; permite "acordados entre miembros".
- `Reunion0105.txt` líneas 354-380 — sugerencia textual asesor.
- Plan: `radiant-sleeping-eagle.md` Sprint 6.2.
