# 0032 — CAL-32: c_j fixed-cost coefficient defense

- **Estado:** Accepted
- **Fecha de decision:** 2026-05-06
- **Actividad:** 2.1 (modelo P2P) / 4.2 (paper IEEE WEEF 2026)
- **Archivos afectados:** `scripts/run_paper_iter.py:259`,
  `outputs/paper/paper_weef.md` (defensa metodologica)
- **Fuente:** plan
  `C:\Users\burav\.claude\plans\con-ruflo-puedes-orquestar-twinkly-leaf.md`
  Sprint 2026-05-06 (parameter calibration audit)

## Contexto

Modelo base Chacon 2025 (eq. 16, p. 4): la funcion de costo de
generacion del seller j es

```
H_j(P) = a_j (sum_i P_ji)^2 + b_j (sum_i P_ji) + c_j
```

donde:
- `a_j`: curvatura cuadratica del costo (typicamente 0 para PV puro)
- `b_j`: coeficiente lineal (LCOE solar, COP/kWh)
- `c_j`: costo fijo aditivo

Chacon Tabla I (p. 9) reporta `c = {4.5, 1.2, 3.5, 10.2}` heterogeneo
para 4 prosumers, "adapted from [40]" (Yang et al. 2024,
*Renewable Energy* 228:120669).

Nuestro codigo actual fija `c_j = 1.2` uniforme para los 5 agentes
MTE (`scripts/run_paper_iter.py:259`: `c=np.full(N, 1.2)`). Esta
asignacion **no estaba documentada en ningun ADR** previo y aparenta
ser un default heuristico (valor 1.2 = mediana de la distribucion
{1.2, 3.5, 4.5, 10.2} de Chacon Tabla I).

## Decision

**Mantener `c_j = 1.2` uniforme y documentar formalmente que c_j
no afecta el equilibrio del juego.** Anadir nota en el paper Methods.

## Justificacion matematica

La dinamica del Replicator Dynamics para sellers (eq. 19 Chacon, p. 6)
se construye a partir del gradiente de la funcion de Lagrange:

```
F_Pji = - dL_Wj / dPji = - dWj / dPji - lam_j d(constraint G)/dPji - ...
```

donde W_j = U_j + R_j - H_j (eq. 6). El gradiente de H_j respecto a
P_ji es:

```
dH_j / dP_ji = 2 a_j (sum_k P_jk) + b_j     (no depende de c_j)
```

**c_j es una constante aditiva** que aparece en la utilidad absoluta
W_j(P) pero no en su gradiente. La RD evoluciona segun (F_Pji - F_bar)
y c_j cancela en la diferencia. Por tanto:

- **El equilibrio P\* es invariante en c_j**.
- **El precio de equilibrio pi\* es invariante en c_j** (depende de F = pi - H' - lam_filt - bet_filt + B; H' no depende de c).
- Solo cambia el valor numerico absoluto de W_j (offset) — no el ranking, no el delta.

Verificacion empirica: barrido `c_j ∈ {0, 1.2, 5, 10}` en
`scripts/calibrate_168h.py` produce identicos {SC, SS, IE, π*, P*}
hasta precision numerica.

## Justificacion sustantiva (paper Methods)

Para una comunidad 100% PV con inversores grid-tied, el costo fijo
c_j corresponde al O&M anual amortizado por unidad de tiempo. Bajo
los siguientes supuestos:

1. Mismo fabricante de inversor (Fronius para 4 de 5; Cesmag con
   inversor distinto pero misma clase ≤ 100 kW) → tasa O&M
   homogenea ~1-2% CapEx/ano (estandar IRENA 2024).
2. Capacidad instalada similar (kWp en orden de magnitud uniforme,
   pendiente verificar con admin MTE — `Inventario_Act_1_0.md:30-34`)
3. Misma latitud, misma irradiancia local (radio < 2 km en Pasto)

El valor `c_j = 1.2` representa el costo operativo marginal homogeneo
para los 5 sitios. **La invariancia matematica del equilibrio respecto
a c_j hace que esta eleccion sea inocua**: aunque tuvieramos c
heterogeneo per-institucion, el equilibrio P\*, π\*, IE, PoF
seguirian iguales.

## Decision para el paper

**Omitir c_j del analisis del equilibrio en Section II.D**. Anadir
nota:

> The fixed-cost coefficient `c_j` is omitted from the equilibrium
> analysis since it acts as an additive constant in `H_j` and
> consequently does not enter the gradient `∂H/∂P` that drives the
> replicator dynamics (eq. 19). It would only affect the absolute
> magnitude of welfare totals reported in Section IV, not the
> equilibrium allocation `P*`, prices `π*`, or the equity / efficiency
> indices.

## Consecuencias

- (+) Defensa metodologica explicita ante reviewers.
- (+) Cero cambio de codigo; cero regeneracion.
- (=) `c_j = 1.2` permanece como esta.
- (-) Si MTE confirma datos de O&M reales por institucion en el
  futuro, podemos heterogeneizar c_j sin afectar resultados anteriores.

## Estado

Defensa documentada. CAL-32 cierra el gap de justificacion para c_j.

## Apendice 2026-05-06b — Decision final c_j = 0

Tras la auditoria metodologica detallada del 2026-05-06b se profundizo
la justificacion y se cambio el valor por uno fisicamente justificable.

### Demo empirica de invariancia

`scripts/demo_invariancia_c_lambda.py` corrio 3 configuraciones en
hora h=512 (max P2P volume del paper):

| Run | c_j | lambda_j | theta_j | eta_i | sumP* (kW) | pi_mean | diff_P_max |
|---|---|---|---|---|---|---|---|
| A | 1.2 | 100 | 0.5 | 0.1 | 10.5202 | 490.19 | (baseline) |
| B | 0.0 | 100 | 0.5 | 0.1 | 10.5202 | 490.19 | **0.00 kW** |
| C | 10000 | 999 | 10 | 5 | 10.5202 | 490.19 | **2.35e-08 kW** |

**Confirmado:** invariancia analitica de c_j, lambda_j, theta_j,
eta_i bajo alpha=0 verificada empiricamente. El cambio numerico es
ruido LSODA (8 ordenes de magnitud por debajo de la escala fisica).

### Justificacion fisica de c_j = 0

CapEx tipico de un PV grid-tied 5 kWp: ~5e6 COP, vida util 25 anos.
Amortizacion por hora: 5e6 / (8760 x 25) ~ 22 COP/hora. Esto NO se
mapea a c_n del modelo (unidades de optimizacion adimensionales,
mismo orden de magnitud que pi_gs=1250).

Yang 2024 [40] y Martinez-Piazuelo 2022 [16] usan c=0 para
renovables como convencion canonica. `Bienestar6p.py:46` (modo
sintetico MATLAB) ya usa `C=zeros(6)`. Heredar c=1.2 en modo real
era un copy-paste de la fila "agente 2 turbina" de Chacon Tabla I,
no aplicable a PV puro.

### Cambio aplicado

`c_j = 1.2 → c_j = 0` en 11 archivos:

- `scripts/run_paper_iter.py:259`
- `main_simulation.py:233-238` (rama --data real)
- `analysis/audit/robustez_sweep.py:114`
- `analysis/audit/equidad_sweep.py:201`
- `analysis/subperiod.py:427`
- `analysis/stackelberg_convergence_real.py:78`
- `scripts/audit_p2p_paper.py:326`
- `scripts/calibrate_168h.py:47`
- `scripts/run_heterogeneidad_paper.py:62`
- `scripts/run_phi_sweep_hourly.py:57`
- `scripts/run_subperiod_only.py:51`

Excepto: `scripts/investigate_phi_dip{,_deep}.py` mantienen el
patron condicional original por ser scripts de investigacion
puntuales (no producen resultados oficiales).

### Impacto numerico

**Cero cambio** en P*, pi*, IE, PoF, RPE, SC, SS por la invariancia
analitica + verificada empiricamente. Solo cambia el offset
absoluto de W_j reportado por `seller_welfare`. Las 16 figuras del
paper IEEE WEEF y las Tablas I-III no cambian numericamente. El
`fig_paper_convergence_h0512` regenerado post-fix tiene P*, pi*
identicos al pre-fix (`scripts/debug_convergence_h512.py` lo
confirma).
