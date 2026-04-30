# 0008 — CAL-8: Tarifa Cedenar mensual diferenciada por institucion

- **Estado:** Accepted
- **Fecha de decision:** 2026-04-27
- **Actividad:** 1.1 (caracterizacion empirica) / 3.1-3.3 (validacion regulatoria)
- **Archivos afectados:** `data/cedenar_tariff.py`,
  `data/tarifas_cedenar_mensual.csv`, `scenarios/_pi_gs.py`,
  `scenarios/scenario_c{1,2,3,4}_*.py`, `scenarios/comparison_engine.py`,
  `analysis/monthly_report.py`, `analysis/p2p_breakdown.py`,
  `main_simulation.py`
- **Supersedes parcialmente:** la nota de CAL-6 sobre el escalar
  `pi_gs = 650 COP/kWh`
- **Fuente:** `Documentos/notas_modelo_tesis.md` §7 CAL-8

## Contexto

Hasta el cierre de auditoria D2, el modelo usaba un escalar
`pi_gs = 650 COP/kWh` justificado como "punto medio conservador del
rango 580-720 reportado por contratos Cedenar/ESSA Narino".

La revision del PDF oficial Cedenar (`tarifa_210.pdf`, vigente desde
21-abr-2026, ya disponible en `data/cedenar_pdfs/`) muestra que ese
escalar **subestima la tarifa real entre 18 % y 47 %** segun la
categoria tarifaria y el nivel de tension de cada institucion.

Tarifa CU 101-028/23 (con COT) abril-2026, no residencial NT2:

| Categoria | NT2 (COP/kWh) | Aplica a |
|---|---:|---|
| Oficial / Especial | **799** | Udenar, HUDN |
| Comercial / Industrial | **959** | Mariana, UCC, Cesmag |

## Decision

1. **Sustituir el escalar por una serie mensual diferenciada** por
   `(categoria, nivel_tension, propiedad)`. Convencion CSV:
   `data/tarifas_cedenar_mensual.csv`, una fila por
   `(mes, categoria, nivel_tension, propiedad)`.

2. **Mapeo institucional provisional** (NT real pendiente factura):
   - Udenar, HUDN → Oficial/Especial NT2
   - Mariana, UCC, Cesmag → Comercial NT2

3. **Fase 1 (en produccion 2026-04-27)**: `main_simulation.py --data real`
   ya consume el CSV. Calcula `pi_gs` comunitario ponderado por demanda
   media de cada agente. Imprime tabla per-agente y cobertura
   `meses_cargados / meses_horizonte`. El contrato escalar
   `pi_gs : float` de los escenarios C1-C4 se conserva.

4. **Fase 2 (en produccion 2026-04-27)**: los escenarios C1-C4,
   `comparison_engine`, `monthly_report` y `p2p_breakdown` aceptan
   `pi_gs : float | np.ndarray (N,)`. El helper
   `scenarios._pi_gs.as_pi_gs_vector(pi_gs, N)` normaliza al inicio.
   Esto permite que la sensibilidad (que varia `pi_gs` como escalar)
   siga funcionando, mientras la calibracion real propaga heterogeneidad
   per-agente:
   - Autoconsumo: cada institucion valoriza `min(G_n, D_n)` a su
     `pi_gs[n]` real (797 oficial vs 956 comercial).
   - Permutacion C1, creditos PDE C4, deficit residual: idem.
   - Ahorro comprador P2P: `(pi_gs[i] − pi_star[i]) × P_comprado`.

5. **Fallback explicito**: si una fecha cae fuera de los meses cargados,
   `UserWarning` por mes y `DEFAULT_PI_GS_FALLBACK = 650 COP/kWh`. El
   log de `--data real` declara explicitamente cualquier mes en fallback.
   **Cobertura actual: 13/13 meses (abr-2025 → abr-2026), no se invoca
   fallback.**

## Justificacion

El escalar 650 COP/kWh quedo **factualmente desactualizado** vs la
tarifa Cedenar vigente. Cualquier resultado de bienestar comparativo
contra los contrafactuales C1-C4 estaba escalado por un factor erroneo
de aproximadamente +37 %.

## Impacto observado

Validacion sobre horizonte completo MTE_v3 (`--full --analysis`
2026-04-28, 55,2 min, 6 144 h):

| Metrica | Pre-CAL-8 (650) | Post-CAL-8 (vector) | Δ |
|---|---:|---:|---:|
| Beneficio P2P | 37,78 MCOP | **52,43 MCOP** | +38,8 % |
| Beneficio C1 | 39,56 MCOP | **54,04 MCOP** | +36,6 % |
| Beneficio C4 | 36,56 MCOP | **50,29 MCOP** | +37,6 % |
| RPE P2P vs C4 | +0,0321 | **+0,0408** | +27 % |
| Σ ventaja P2P − C4 | 1,21 MCOP | **2,14 MCOP** | +77 % |
| IE P2P | +0,4063 | +0,3677 | −0,04 |
| Agentes IR-estables | 5/5 | **3/5** | hallazgo nuevo |

`pi_gs` comunitario ponderado por demanda: **906 COP/kWh** (+39 %
sobre el legacy 650).

## Consecuencias

- (+) Calibracion empirica defendible con PDFs oficiales Cedenar.
- (+) Heterogeneidad oficial/comercial captura efectos reales en IE
  (vendedores capturan +28,6 % del excedente, compradores comerciales
  +71,4 %).
- (+) Reproducibilidad: 13 meses de PDFs en `data/cedenar_pdfs/`,
  130 filas en CSV.
- (-) **Hallazgo nuevo**: con la tarifa real, **Udenar y HUDN desertan
  del P2P al regimen AGPE C1** (3/5 estables, antes 5/5). Esto invierte
  el resultado pre-CAL-8 y reorganiza la frontera de IR. Ver §3.14 de
  notas_modelo_tesis.md.
- (-) `pi_gs = 650` queda **deprecado como valor escalar unico**. Se
  conserva solo como `DEFAULT_PI_GS_FALLBACK`.
- (Pendiente) Confirmar el nivel de tension real de cada campus contra
  factura mensual.

## Estado

En produccion desde 2026-04-27. Calibracion oficial usada en todas las
figuras post-CAL-8.
