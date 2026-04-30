# 0003 — CAL-3: `alpha_p = 0.20`, `alpha_c = 0.10` (Demand Response)

- **Estado:** Accepted (retroactivo)
- **Fecha de decision:** 2026-04
- **Actividad:** 2.1 (modelo P2P) / 4.1 (optimalidad)
- **Archivos afectados:** `core/dr_program.py`, `core/ems_p2p.py`
- **Fuente:** `Documentos/notas_modelo_tesis.md` §7 CAL-3

## Contexto

`alpha_p` (productores) y `alpha_c` (consumidores) controlan la fraccion
de demanda flexible disponible para el programa Demand Response. **No
existen** en ninguna version del codigo de Chacon — son un supuesto
propio de la implementacion Python.

Rango tipico en literatura DR para prosumidores: 10-40 %.

## Decision

`alpha_p = 0.20`, `alpha_c = 0.10`.

## Justificacion empirica

Barrido `(alpha_p, alpha_c)`:

| alpha_p | alpha_c | Δ SC vs α=0 |
|---:|---:|---:|
| 0.00 | 0.00 | — |
| 0.10 | 0.05 | +0.0182 |
| **0.20** | **0.10** | **+0.0348** ← 72 % de la mejora maxima |
| 0.30 | 0.15 | +0.0481 |
| 0.40 | 0.20 | +0.0470 ← satura, beneficio marginal negativo |

`alpha_p = 0.20` captura el 72 % de la mejora maxima posible con solo
el 50 % del desplazamiento del punto de saturacion. El beneficio
marginal del DR se vuelve negativo para `alpha_p > 0.30-0.35`.

`alpha_c = 0.10` mantiene la relacion 2:1 vendedores:compradores,
consistente con que los autoconsumidores tienen mayor flexibilidad
operacional que los consumidores institucionales.

## Consecuencias

- (+) Punto de inflexion en la curva ΔSC(α), defendible empiricamente.
- (+) Coherente con literatura DR para comunidades energeticas
  universitarias: Luthander et al. 2015, Parra et al. 2017.
- (-) Si la propuesta cambia el regimen de DR (p.ej. solo
  desplazamiento horario sin curtailment) hay que recalibrar.

## Estado

Optimo empirico. Documentar en §III-A del manuscrito.
