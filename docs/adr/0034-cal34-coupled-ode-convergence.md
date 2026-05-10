# ADR-0034 — CAL-34: Coupled ODE convergence solver

**Estado:** Accepted
**Fecha:** 2026-05-04
**Contexto:** Act 4.1 / 4.2 — paper IEEE WEEF + tesis

## Contexto

Antes de CAL-34 la funcion `EMSP2P.run_convergence()` usaba un esquema
**alternating Stackelberg discreto**: 8 iteraciones outer alternando
(sellers replicator dynamics) con (buyers price update). El resultado
visual era una secuencia de saltos discretos en `(W, pi, P)` por
iteracion, no una trayectoria continua.

Esto contrasta con la formulacion del modelo base (Chacon 2025,
`JoinFinal.m:139`) donde el sistema se integra como un ODE acoplado
unificado, y las figuras 10a / 11a del paper de Chacon muestran
`W(t)` como curva continua sobre `t in [0, t_end]`.

## Decision

Se introduce `core/coupled_ode_convergence.py` con la funcion
`solve_coupled_ode(...)` que integra el sistema acoplado (sellers RD +
buyers price update) sobre `t in [0, 0.005]s` con 400 puntos via
`scipy.integrate.solve_ivp`.

`EMSP2P.run_convergence(use_coupled_ode=True)` (default tras 2026-05-04
para uso en figuras del paper) expone los campos:

- `ConvergenceData.coupled_t` — eje temporal (n_pts,)
- `ConvergenceData.coupled_W_t`, `coupled_Wj_t`, `coupled_Wi_t` — welfare
- `ConvergenceData.coupled_pi_t` — (I, n_pts) precios buyer
- `ConvergenceData.coupled_P_t` — (J, I, n_pts) flujos de potencia

Cuando `use_coupled_ode=False` (legacy) los campos coupled_* son `None`
y se usa el flujo discreto Stackelberg pre-existente.

## Consecuencias

- **No-breaking:** el solver principal `EMSP2P.run()` no cambia. Solo
  `run_convergence(...)` expone la nueva opcion para figuras.
- **Paper:** `fig_paper_convergence_h0512` ahora muestra `W(t)` como
  curva continua matching Chacon Fig 10a/11a.
- **Tesis:** las figuras de convergencia heredan automaticamente el
  cambio cuando se regeneren con `--full --analysis`.

## Verificacion

`scripts/regen_convergence_paper.py` corre el solver coupled-ODE para
hora h=512 (max P2P volume) y produce el PNG con trayectorias continuas.
Los valores finales `W_inf, pi_inf, P_inf` coinciden con el equilibrio
del solver discreto a precision numerica (~1e-3).

## Trazabilidad

- Modulo: `core/coupled_ode_convergence.py`
- Integracion: `core/ems_p2p.py:run_convergence(use_coupled_ode=...)`
- Figura: `outputs/paper/fig_paper_convergence_h0512.png`
- Generador: `scripts/regen_convergence_paper.py`
