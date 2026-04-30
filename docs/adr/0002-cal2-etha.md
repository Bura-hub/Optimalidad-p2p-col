# 0002 — CAL-2: `etha = 0.1`

- **Estado:** Accepted (retroactivo)
- **Fecha de decision:** 2026-04
- **Actividad:** 2.1 (modelo P2P)
- **Archivos afectados:** `core/replicator_buyers.py`, `core/ems_p2p.py`
- **Fuente:** `Documentos/notas_modelo_tesis.md` §7 CAL-2

## Contexto

Existe discrepancia entre las dos versiones del codigo de Chacon:

- `JoinFinal.m` (modelo base de fidelidad) usa `etha = 0.1`.
- `ConArtLatin.m` (codigo del articulo publicado) usa `etha = 1.0`.

`etha` controla el termino de competencia `compe = etha · Σ P_ji`
en `solve_buyers()`. Diferencia de un orden de magnitud entre las
dos referencias.

## Decision

Mantener `etha = 0.1` por consistencia con `JoinFinal.m` (modelo base
del que parte la tesis).

## Justificacion empirica

Barrido en {0.01, 0.05, 0.10, 0.50, 1.00, 2.00, 5.00}:

| etha | SC | SS | IE | pi_mean |
|---|---|---|---|---|
| 0.01 | 0.8692 | 0.8465 | −0.3889 | 863.36 |
| 0.10 | 0.8692 | 0.8465 | −0.3889 | 863.36 |
| 1.00 | 0.8692 | 0.8465 | −0.3889 | 863.36 |
| 5.00 | 0.8692 | 0.8465 | −0.3889 | 863.35 |

`etha` es **operacionalmente inerte** en [0.01, 5.0]. El termino
`compe` es numericamente despreciable frente a `pagos` y `trestris`
en las escalas del modelo.

## Consecuencias

- (+) La discrepancia JoinFinal vs articulo carece de impacto.
- (+) No se requiere defender el valor frente a los asesores.
- (=) Cualquier valor en el rango produce el mismo equilibrio.

## Estado

Inerte. Decision por consistencia, no por sensibilidad.
