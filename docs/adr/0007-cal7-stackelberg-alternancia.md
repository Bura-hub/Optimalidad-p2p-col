# 0007 — CAL-7: Alternancia Stackelberg en lugar de ODE conjunta

- **Estado:** Accepted
- **Fecha de decision:** 2026-04-17
- **Actividad:** 2.1 (modelo P2P)
- **Archivos afectados:** `core/ems_p2p.py:230-244`
- **Hallazgo de auditoria:** A3 (cerrado como discrepancia documentada)
- **Fuente:** `Documentos/notas_modelo_tesis.md` §7 CAL-7

## Contexto

`JoinFinal.m:139` (modelo base) integra el sistema **conjunto**:
```
[consumer_state, seller_state] → ode15s
```
ambos replicadores evolucionan simultaneamente en una sola llamada al
integrador.

La implementacion Python usa **alternancia secuencial**:
```python
while iter < max_iter:
    P_star = solve_sellers(pi_i, ...)   # RD vendedores (ODE interna)
    pi_i   = solve_buyers(P_star, ...)  # RD compradores (ODE interna)
    norm_rel = ‖P_new − P_old‖ / (‖P_old‖ + 1e-9)
    if norm_rel < tol:
        break
```

Esto es una **discrepancia de formulacion** vs el modelo base. La
auditoria A3 pregunto si afecta los resultados.

## Decision

**Mantener la alternancia.** Razones de ingenieria de software:

1. **Paralelizacion**: la iteracion horaria de 5 160 h se reparte con
   `ProcessPoolExecutor`. Cada hora necesita un bucle finito predecible,
   no un integrador adaptativo.
2. **Diagnostico**: permite inspeccionar `P_star` y `pi_i` por separado
   tras cada sub-paso (tests de convergencia mas finos).
3. **Criterio de parada uniforme**: norma relativa en `P_star` como
   contrato explicito y adaptativo entre escenarios.

## Justificacion teorica de equivalencia

Ambas formulaciones convergen al **mismo punto fijo del juego
Stackelberg** cuando `tol → 0`, `max_iter → ∞`, porque el equilibrio
de Nash es invariante bajo factorizacion del operador de actualizacion:
el operador `T : (P, π) → siguiente estado` es contractivo tanto
aplicado en bloque como alternado, con el mismo punto fijo.

**Trayectorias transitorias** (antes de converger) si difieren entre
las dos formulaciones, pero **ninguna figura de la tesis reporta
dinamicas transitorias** — todas usan `P_star` y `pi_i` ya convergidos.

## Validacion empirica

- `tests/test_stackelberg_convergence.py` garantiza que al salir del
  bucle `norm_rel < tol = 1e-3`.
- `tests/golden_test_sofia.py` confirma que el equilibrio coincide con
  el oraculo SLSQP de `Bienestar6p.py`:
  - `P_total` atol = 0.15 kWh
  - demanda rtol = 5 %
  - `π_i ∈ [π_GB, π_GS]`

## Consecuencias

- (+) Habilita paralelismo masivo (necesario para `--full` 5 160 h).
- (+) Mismo equilibrio que el modelo base dentro de tolerancias.
- (+) Texto para Metodos: *"El sistema Stackelberg se resuelve por
  alternancia (`solve_sellers ↔ solve_buyers`) con criterio de parada
  `‖ΔP‖/(‖P‖+ε) < tol = 1e-3` y `max_iter = 8`."*
- (-) Cualquier futura figura de **dinamica transitoria** requeriria
  reformular a ODE conjunta — pero ese caso no esta en el alcance.

## Estado

Hallazgo A3 cerrado. No se modifica el codigo.
