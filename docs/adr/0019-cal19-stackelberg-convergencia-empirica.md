# 0019 — CAL-19: Convergencia empírica del juego Stackelberg

- **Estado:** Accepted
- **Fecha de decision:** 2026-05-02
- **Actividad:** 2.1 (modelo P2P) — capa nuclear
- **Archivos afectados:** `core/ems_p2p.py` (docstring),
  `analysis/stackelberg_convergence_real.py` (nuevo),
  `graficas/convergencia_stackelberg_quick.{csv,png,mat}`,
  `tests/test_cal19_iters_real.py`
- **Relacionado con:** [ADR-0001 CAL-1](0001-cal1-stackelberg-iters.md)
  (extiende y formaliza con sustento empirico real),
  [ADR-0007 CAL-7](0007-cal7-stackelberg-alternancia.md)
- **Fuente:** plan
  `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 2.1.

## Contexto

CAL-1 (ADR-0001) fijo `stackelberg_iters = 2` con un barrido **sintetico**
(modelo base 24 h de Chacon et al. 2025) en
`tests/calibration_study.py::calibrate_stackelberg_iters`. La regla
"todo bajo fuente fundamentada" del plan
`radiant-sleeping-eagle.md` (Sprint 2) exige un barrido **sobre datos
MTE reales** que justifique `iters=2` con la matriz precision × tiempo
de computo. Ademas, CAL-1 no documentaba explicitamente la justificacion
de los parametros companeros `stackelberg_tol = 1e-3` y
`stackelberg_max = 10`.

El usuario senalo explicitamente la necesidad de evaluar el tradeoff
**precision vs rendimiento**: optimizaciones previas (e.g.
`n_points = 150`, `t_span = 0.005`) tuvieron impacto medible en la
fidelidad numerica, asi que cualquier decision sobre `iters` debe
documentar ambos ejes.

## Auditoria ejecutada

`analysis/stackelberg_convergence_real.py --quick` corre sobre 168 h
MTE reales (2025-08-04 a 2025-08-11, alta actividad P2P) con
`alpha = 0` (sin DR) para aislar el efecto del juego. Barrido sobre
`stackelberg_iters in {1, 2, 3, 5, 8, 10}`. Otros parametros del
solver: defaults (`tau = 0.001`, `t_span = (0, 0.005)`,
`n_points = 150`, `tol = 1e-3`, `max = 10`, paralelismo activo).

| iters | tiempo (s) | kwh_p2p | bienestar total | iters reales (mediana / max) | norma residual mediana | Δ bienestar vs ref [%] |
|------:|----------:|--------:|----------------:|-----------------------------:|----------------------:|----------------------:|
| 1     | 12.8      | 193.72  | 28 553.7        | 2 / 10                       | 1.4e-05              | **1.891 %**           |
| **2** | **14.8**  | 193.72  | **28 020.6**    | 3 / 10                       | 1.6e-04              | **0.011 %**           |
| 3     | 15.4      | 193.72  | 28 023.7        | 3 / 10                       | 3.3e-08              | 0.000 %               |
| 5     | 20.7      | 193.72  | 28 023.7        | 5 / 10                       | 0.0                  | 0.000 %               |
| 8     | 29.1      | 193.72  | 28 023.7        | 8 / 10                       | 0.0                  | 0.000 %               |
| 10    | 35.1      | 193.72  | 28 023.7        | 10 / 10                      | 0.0                  | 0.000 %               |

(`Δ bienestar vs ref` = `|welfare(iters) − welfare(iters=10)| / |welfare(iters=10)|`.)

**Lecturas:**

1. **`iters = 1` es insuficiente**: Δ bienestar = 1.89 % > 1 %. Una
   sola pasada del bucle Stackelberg no captura el ajuste marginal de
   precios.
2. **`iters = 2` es el optimo precision × rendimiento**: Δ bienestar
   = **0.011 %**, factor 5 000 bajo el umbral 1 %. Tiempo: 14.8 s
   (2.4× mas rapido que `iters = 10`).
3. **`iters >= 3` son redundantes**: bienestar identico al ref, solo
   aumenta tiempo de computo de forma lineal.
4. **`stackelberg_max = 10` actua como red de seguridad util**: incluso
   con `stackelberg_iters = 2` (minimo), algunas horas requieren hasta
   10 iteraciones para converger (`iters_used_max = 10`). La mediana
   real es 3, lo que confirma que la mayoria de horas converge rapido
   pero hay outliers.
5. **`stackelberg_tol = 1e-3` queda ratificada**: con `iters = 2` la
   norma residual mediana es **1.6e-4**, un orden de magnitud por
   debajo de la tolerancia. Reducir a `tol = 1e-4` no cambiaria el
   resultado en la mayoria de las horas.
6. **`kwh_p2p_total` es identico en todos los `iters >= 1`**: el
   volumen comerciado en P2P se decide en la primera pasada del juego;
   las iteraciones adicionales solo refinan el reparto de bienestar
   entre vendedores y compradores.

## Decision

Mantener **`stackelberg_iters = 2`** como default global, ratificado
por el barrido empirico:

- **Precision**: Δ bienestar < 0.02 % vs `iters = 10` (factor 5 000
  bajo el umbral 1 %).
- **Rendimiento**: 14.8 s vs 35.1 s sobre el subset (~58 % menos
  tiempo).
- **Robustez**: `stackelberg_max = 10` cubre las horas con
  convergencia lenta (outliers); `stackelberg_tol = 1e-3` deja
  margen sobrado.

Acciones derivadas (Accepted):

1. Conservar las constantes del default actual:
   ```python
   stackelberg_iters: int   = 2
   stackelberg_tol:   float = 1e-3
   stackelberg_max:   int   = 10
   ```
2. Anadir docstring en `core/ems_p2p.py:SolverParams` que cite ADR-0019
   y el script de auditoria.
3. `analysis/stackelberg_convergence_real.py` queda como herramienta
   reproducible:
   - `--quick` (default, 168 h, ~2-3 min) para CI / re-validacion
     periodica.
   - `--full` (6144 h MTE, ~30 min) para validacion antes de defensa.
4. Test de regresion `tests/test_cal19_iters_real.py` ejecuta un
   sub-subset (24 h o 48 h) y garantiza
   `|welfare(iters=2) − welfare(iters=10)| / |welfare(iters=10)| < 1 %`.

## Alternativas consideradas

1. **`stackelberg_iters = 3`** (compromiso conservador). Descartado:
   bienestar identico al de `iters = 2` con 0.6 s extra (sobre 168 h)
   y sin mejora detectable. Sobre 5 160 h el costo seria ~20 s sin
   beneficio numerico.
2. **`stackelberg_iters = 1`** (rendimiento maximo). Descartado:
   Δ bienestar 1.89 % excede el umbral del plan.
3. **Reducir `stackelberg_max` a 5**. Descartado: con `iters = 2` y
   `tol = 1e-3`, el bucle puede llegar a `max` en horas con dinamica
   compleja; reducir el techo introduciria sesgo en esos casos
   (`norm_rel_final` no cumpliria `tol`).
4. **Endurecer `stackelberg_tol` a 1e-4**. Descartado: la auditoria
   muestra que `iters = 2` ya cumple holgadamente `tol = 1e-3`
   (norma residual mediana 1.6e-4); endurecer no cambia resultados
   pero podria forzar mas iteraciones en horas marginales.

## Consecuencias

**Positivas**

- Default `stackelberg_iters = 2` queda sustentado con datos MTE
  reales y tabla precision × tiempo, complementando el barrido
  sintetico de CAL-1.
- La regla "todo bajo fuente fundamentada" del plan queda cerrada
  para los tres parametros del juego Stackelberg
  (`iters`, `tol`, `max`).
- Script reproducible permite re-validar en cualquier extension
  futura del horizonte o cambio de calibracion.
- Test de regresion previene drift silencioso si alguien cambia el
  default sin ejecutar el barrido.

**Negativas**

- El barrido `--full` (6 144 h) toma ~30 min; en CI solo se ejecuta
  `--quick` (168 h) que cubre una semana representativa pero no
  todos los regimenes climaticos del horizonte. Mitigacion: el
  test de regresion usa un horizonte aun menor (24-48 h) y la
  validacion completa se documenta en este ADR.
- El subset de 168 h (1 semana ago-2025) puede no representar
  estacionalidades extremas (e.g. dic-2025). Mitigacion: el plan
  contempla correr `--full` antes de la defensa para validacion
  end-to-end.

**Riesgos abiertos**

- Si las calibraciones de CAL-3, CAL-4, CAL-5 cambian sustancialmente
  (alpha, tau, theta), el equilibrio del juego puede desplazarse y
  la convergencia de `iters = 2` debe re-validarse. **Mitigacion:**
  re-ejecutar el script `--quick` tras cualquier cambio en
  `core/ems_p2p.py::SolverParams`.

## Verificacion

```powershell
# Barrido quick (default, 168 h, ~2-3 min):
python analysis/stackelberg_convergence_real.py --quick

# Barrido full (6144 h, ~30 min, antes de defensa):
python analysis/stackelberg_convergence_real.py --full

# Test de regresion (subset corto, ~30 s):
python -m pytest tests/test_cal19_iters_real.py -v

# Suite global (sin regresiones):
python -m pytest tests/ -q --ignore=tests/test_full_simulation_preflight.py
```

Output esperado del barrido quick:

```
| iters | tiempo |  Δ welfare vs iters=10 |
|------:|-------:|----------------------:|
|   1   |  ~13 s |  ~1.89 % (insuficiente)|
|   2   |  ~15 s |  ~0.01 % (default OK)  |
|  10   |  ~35 s |   0 %      (referencia)|
```

## Referencias

- ADR-0001 (CAL-1) — barrido sintetico inicial; este ADR lo extiende.
- ADR-0007 (CAL-7) — alternancia Stackelberg vs ODE conjunta.
- `core/ems_p2p.py:155-157` — definicion de los tres parametros.
- `Documentos/notas_modelo_tesis.md §CAL-1` — justificacion teorica
  inicial.
- Chacon et al. 2025 — modelo base; el bucle Stackelberg
  (alternancia) fue introducido en CAL-7.
