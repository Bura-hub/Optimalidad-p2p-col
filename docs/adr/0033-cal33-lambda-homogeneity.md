# 0033 — CAL-33: lambda_j homogeneity defense

- **Estado:** Accepted
- **Fecha de decision:** 2026-05-06
- **Actividad:** 2.1 (modelo P2P) / 4.2 (paper IEEE WEEF 2026)
- **Archivos afectados:** `scripts/run_paper_iter.py:260`,
  `outputs/paper/paper_weef.md` (defensa metodologica)
- **Fuente:** plan
  `C:\Users\burav\.claude\plans\con-ruflo-puedes-orquestar-twinkly-leaf.md`
  Sprint 2026-05-06 (parameter calibration audit)
- **Relacionado con:** CAL-2 (etha homogeneo), CAL-5 (theta homogeneo),
  CAL-6 (b_j heterogeneo via inversor), CAL-32 (c_j homogeneo)

## Contexto

Modelo base Chacon 2025 (eq. 7, p. 4): la utilidad de auto-consumo
del seller j es

```
U_j(D_j*) = lambda_j · D_j* − (theta_j / 2) · (D_j*)^2
```

donde `lambda_j` y `theta_j` son "preference factors that may depend
on the consumption pattern, need or type of DER" (Chacon p. 4).

El codigo MATLAB original `Bienestar6p.py:28` y `JoinFinal.m:26`
ambos usan `lambda = [100, 100, 100, 100, 100, 100]` homogeneo. CAL-5
(2026-04) ya documenta que `theta_j = 0.5` homogeneo es operativamente
inerte (afecta solo reporting, no equilibrio).

`lambda_j = 100` no estaba documentada en ningun ADR. Se hereda de
`Bienestar6p.py:28` sin recalibracion para el caso MTE.

## Decision

**Mantener `lambda_j = 100` uniforme para los 5 agentes**, con
justificacion explicita basada en homogeneidad de tecnologia FV.

## Justificacion sustantiva

`lambda_j` representa la "preferencia por auto-consumo" del seller j —
cuanto valora cada unidad de energia que retiene en lugar de exportar.
Para una comunidad 100% PV grid-tied (sin almacenamiento, sin DR
activo), esta preferencia depende fundamentalmente de:

1. **Tipo de DER** — todos los 5 sitios tienen sistemas FV grid-tied.
   Mismo perfil de generacion intermitente (curva diaria solar).
2. **Tecnologia del inversor** — 4 de 5 sitios usan Fronius (mismo
   fabricante, misma clase ≤ 100 kW); Cesmag tiene inversor distinto
   pero misma topologia grid-tied (sin baterias).
3. **Patron de consumo institucional** — las 5 instituciones son
   educativas/comerciales en Pasto, con perfil diurno similar
   (oficinas/aulas operando 6:00-22:00). CAL-25 homogeneizo todas a
   perfil "comercial".
4. **Necesidades de auto-suficiencia energetica** — sin DR, todas las
   instituciones tienen la misma flexibilidad operativa cero (la
   demanda no se puede desplazar entre horas).

Bajo estos supuestos, no hay razon estructural para asignar diferentes
preferencias `lambda_j` por institucion. La heterogeneidad legitima
estaria en `b_j` (LCOE, capturada en CAL-6) y eventualmente en
capacidad instalada `G_klim` (capturada en los datos MTE).

## Justificacion matematica (sensibilidad operativa)

A diferencia de `theta_j` (que solo afecta reporting per CAL-5),
`lambda_j` SI entra en la utilidad efectiva del seller:

```
W_j = U_j(D_j*) + R_j - H_j
    = lambda_j · D_j* - (theta_j / 2) · (D_j*)^2 + sum_i pi_i P_ji - H_j
```

Sin embargo, en nuestro modelo `D_j*` (demanda flexible optimizada
por DR) **es invariante en lambda_j** porque DR esta deshabilitado
(`alpha = np.zeros(N)` en `run_paper_iter.py:263`). Sin DR, `D_j* = D_j`
fijo desde los datos MTE, independiente de lambda. Por tanto:

- `dW_j / d_lambda = D_j*` (constante respecto al equilibrio)
- El equilibrio P* y pi* del juego Stackelberg + RD **no depende de
  lambda_j** mientras DR este apagado.
- Solo cambia el offset de bienestar reportado (similar al caso CAL-5
  para theta).

Cuando se active DR (futuro trabajo), `D_j*` SI dependera de lambda_j
y la decision deberia revisarse.

## Verificacion empirica

Sin verificacion empirica directa para `lambda_j` (a diferencia de
CAL-2 / CAL-5 que tienen barridos documentados), pero el argumento
matematico arriba es suficiente: bajo `alpha = 0` la sensibilidad a
lambda es analiticamente nula en el equilibrio.

## Decision para el paper

Anadir nota en Section II.D Methods:

> The self-consumption utility parameters `lambda_j = 100` and
> `theta_j = 0.5` are taken from the base model (Chacon et al., 2025
> [21]; Bienestar6p.py reference implementation) and held uniform
> across the five institutions. This is justified by homogeneity in
> DER technology (all 5 sites grid-tied PV without storage), inverter
> brand (Fronius for 4 of 5), location (radius < 2 km in Pasto with
> uniform irradiance ~4.5 kWh/m^2/day), and operational profile
> (educational / commercial agents homogenized to "comercial"
> tariff per CAL-25). Sensitivity analysis (CAL-2, CAL-5) confirms
> that `theta_j` and the buyer competition parameter `eta_i` are
> empirically inert across four orders of magnitude. Under our
> case-study assumption alpha = 0 (no demand response), the
> equilibrium is also analytically invariant in `lambda_j` (eq. 7
> contributes only an additive offset to W_j when D_j* = D_j is fixed).

## Consecuencias

- (+) Defensa metodologica explicita ante reviewers.
- (+) Cero cambio de codigo; cero regeneracion.
- (=) `lambda_j = 100` permanece como esta.
- (-) Si trabajo futuro activa DR (alpha > 0), revisar la decision.

## Estado

Defensa documentada. CAL-33 cierra el gap de justificacion para
lambda_j bajo alpha = 0.

## Referencias

- Chacon et al. (2025) Modelo_Base_Sofía_Chacon.pdf, eq. 7, p. 4
- Chacon et al. (2024) TecnoLógicas 27(60), ref [21]
- `Documentos/copy/JoinFinal.m:26` (lambda inicial)
- `Documentos/copy/Bienestar6p.py:28` (lambda = [100]*6)
- ADR-0002 (CAL-2: etha)
- ADR-0005 (CAL-5: theta)
- ADR-0006 (CAL-6: b_j)
- ADR-0032 (CAL-32: c_j)
