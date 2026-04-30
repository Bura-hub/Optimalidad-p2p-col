# 0001 — CAL-1: `stackelberg_iters = 2`

- **Estado:** Accepted (retroactivo)
- **Fecha de decision:** 2026-04
- **Actividad:** 2.1 (modelo P2P) / 4.1 (optimalidad)
- **Archivos afectados:** `core/ems_p2p.py`
- **Fuente:** `Documentos/notas_modelo_tesis.md` §7 CAL-1

## Contexto

El bucle externo de Stackelberg (alternancia `solve_sellers` ↔
`solve_buyers`) requiere un numero maximo de iteraciones. El modelo base
de Sofia Chacon (`JoinFinal.m`) no fija un valor explicito porque integra
ambos replicadores en un unico sistema ODE conjunto.

Se necesita un valor justificado para la implementacion Python con
alternancia secuencial.

## Decision

Fijar `stackelberg_iters = 2` por defecto en `core/ems_p2p.py`.

## Justificacion empirica

Barrido en {1, 2, 3, 5, 8, 10}: la asignacion de potencias `P_star`
converge en la **primera iteracion** (`Δ SC = 0.00000` exacto entre
iter=1 e iter=10). Solo el indice de equidad IE oscila ±0,02 sin
tendencia monotonica.

| iters | SC | SS | IE |
|---|---|---|---|
| 1 | 0.8692 | 0.8465 | −0.3785 |
| 2 | 0.8692 | 0.8465 | −0.3889 |
| 10 | 0.8692 | 0.8465 | −0.3718 |

## Consecuencias

- (+) Captura el ajuste marginal de precios sin costo computacional.
- (+) Justificacion citable: *"P\* converge en la primera iteracion
  Stackelberg (Δ SC = 0); la segunda se mantiene para capturar el ajuste
  marginal de precios."*
- (-) Si en el futuro se cambia el solver de cada subsistema, hay que
  re-validar con el mismo barrido.

## Estado

Justificado. No se requiere accion adicional.
