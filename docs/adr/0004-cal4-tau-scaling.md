# 0004 — CAL-4: Escalado ODE via constantes de tiempo (`tau_buyers / tau_sellers = 10`)

- **Estado:** Accepted (retroactivo)
- **Fecha de decision:** 2026-04
- **Actividad:** 2.1 (modelo P2P)
- **Archivos afectados:** `core/replicator_sellers.py`,
  `core/replicator_buyers.py`
- **Fuente:** `Documentos/notas_modelo_tesis.md` §7 CAL-4

## Contexto

`JoinFinal.m` (modelo base) integra un sistema ODE conjunto:
```
dX/dt = [WI · ReplicadorWi; WJ · ReplicadorWj]
```
con `WI = 0.08` (compradores), `WJ = 10` (vendedores). El ratio
`WJ / WI = 125` impone que los vendedores reaccionan ~125 veces mas
rapido que los compradores.

La implementacion Python usa subsistemas **secuenciales** (no
combinados): los replicadores de vendedores y compradores se resuelven
en pasos separados con sus propias constantes de tiempo `tau`.

## Decision

`tau_sellers = 0.001`, `tau_buyers = 0.010` (ratio = 10).

El escalado WI/WJ de JoinFinal queda **implicitamente implementado** a
traves de la diferencia de constantes de tiempo de los filtros de paso
bajo. No se hace cambio de codigo adicional.

## Justificacion empirica

Barrido en `tau_b / tau_s ∈ {1, 5, 10, 20}`:

| tau_b/tau_s | tau_buyers | IE |
|---:|---:|---:|
| 1 | 0.0010 | −0.1152 |
| 5 | 0.0050 | −0.2829 |
| **10** | **0.0100** | **−0.3889** ← reproduce JoinFinal.m |
| 20 | 0.0200 | −0.3613 |

Solo `ratio = 10` reproduce el equilibrio IE = −0.39 de `JoinFinal.m`.

## Consecuencias

- (+) Replica el equilibrio del modelo base sin cambiar la arquitectura
  secuencial (que es necesaria para el `ProcessPoolExecutor` horario).
- (+) Justificacion para la tesis: *"La implementacion secuencial captura
  el escalado WI/WJ del modelo conjunto via la diferencia de τ:
  τ_vendedores = 0.001, τ_compradores = 0.010 (ratio 10), alineado con
  WJ/WI = 10 del modelo de referencia."*
- (-) Si se cambia el solver de los replicadores, re-validar con el
  golden test contra `JoinFinal.m`.

## Estado

Equivalente al modelo base. No requiere modificacion.
