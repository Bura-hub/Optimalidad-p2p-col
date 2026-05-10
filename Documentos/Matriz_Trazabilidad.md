# Matriz de trazabilidad — Objetivo → Código → Evidencia

**Tesis:** Análisis de Optimalidad y Validación Regulatoria de Mercados P2P en Colombia  
**Autor:** Brayan S. Lopez-Mendez | **Asesores:** Andrés Pantoja · Germán Obando  
**Programa:** Maestría en Ingeniería Electrónica, Universidad de Nariño, 2026  
**Fecha:** abril de 2026  
**Rama:** tesis/fase-3-documentacion

---

## Instrucciones de lectura

La tabla vincula cada actividad de la propuesta de tesis (`Documentos/PropuestaTesis.txt`) con:
- los módulos de código que la implementan,
- las figuras y tablas que constituyen su evidencia,
- y el estado de avance actual.

**Estados permitidos:**
- `completado` — implementado, validado con pytest y/o ejecución exitosa.
- `parcial — <razón>` — implementado pero faltan datos o validaciones finales.
- `pendiente` — no iniciado.
- `diferido — <razón>` — fuera del alcance de esta entrega.

---

## Tabla principal

| Objetivo | Actividad | Módulo / archivo | Figura / tabla | Estado | Observaciones |
|---|---|---|---|---|---|
| **1** — Análisis del modelo de referencia | **1.0** — Inventario de elementos del sistema e insumos por escenario | `Documentos/Inventario_Act_1_0.md`; `data/base_case_data.py`; `data/xm_prices.py`; **`data/cedenar_tariff.py`**; **`data/tarifas_cedenar_mensual.csv`**; **`data/cedenar_pdfs/`** (13 PDFs) | — | completado | Inventario formal de 5 escenarios, 6 agentes MTE y parámetros de la Tabla I canónica (Chacón et al., 2025). **CAL-8 (2026-04-28):** calibración Cedenar mensual per-agente reemplaza el escalar 650; cobertura completa abr-2025 → abr-2026 con PDFs respaldatorios |
| **1** | **1.1** — Revisión y consolidación del modelo base | `core/ems_p2p.py`; `core/replicator_sellers.py`; `core/replicator_buyers.py`; `core/market_prep.py`; `tests/validate_base_model.py`; `tests/golden_test_sofia.py` | `graficas/fig22_convergencia_h0013.png`; `graficas/fig22_convergencia_h0683.png` | completado | Replicator Dynamics + Stackelberg implementados. Golden test verifica P_total dentro de atol = 0,15 kWh y pi_i ∈ [PGB, PGS] vs oráculo SLSQP (Bienestar6p.py). Tolerancia rtol = 5 % documentada en `tests/golden_test_sofia.py`. Convergencia ilustrada en fig22a (h0013 caso marginal con W_T positivo) y fig22b (h0683 alta energía con W_T negativo) — renombradas el 2026-04-27 desde fig11_convergencia_h\* tras auditoría visual (§A.8 de notas_modelo_tesis.md) |
| **1** | **1.2** — Inferencia de parámetros mediante revisión bibliográfica y datos reales | `Documentos/Revision_Bibliografica_Act_1_2.md`; `Documentos/references.bib`; `data/base_case_data.py`; `data/xm_prices.py` | Tablas 1.1–1.5 (en `Revision_Bibliografica_Act_1_2.md`) | completado | b_n = 225 COP/kWh (LCOE solar Pasto, IRENA [16]/UPME [17]); ε_p corto plazo −0,20 a −0,47 (LAC, [19][20]); λ_n = 100, θ_n = 0,5, η_i = 0,1 calibrados contra [5][22][25]. **27 fuentes DOI-verificadas vs CrossRef 2026-04-30** (Tier 1.1 deep-research Ruflo): 6 entradas marcadas previamente VERIFICAR fueron corregidas y renombradas (ver `bib_verificacion_2026-04-30.md` y header de `references.bib`) |
| **2** — Modelado de escenarios regulatorios | **2.1** — Estructuración matemática de escenarios C1–C4 | `scenarios/scenario_c1_creg174.py`; `scenarios/scenario_c2_bilateral.py`; `scenarios/scenario_c3_spot.py`; `scenarios/scenario_c4_creg101072.py` | — | completado | C1: créditos 1:1 + excedentes a bolsa (CREG 174/2021 [3]). C2: PPA bilateral precio fijo. C3: exposición total precio bolsa horario. C4: distribución administrativa vía PDE (CREG 101 072/2025 [4]), modo `pde_only` por defecto |
| **2** | **2.2** — Algoritmos de cálculo de métricas | `scenarios/comparison_engine.py`; `core/settlement.py`; `analysis/optimality.py`; `analysis/fairness.py` | `graficas/fig5_comparacion_regulatoria.png`; `graficas/fig6_ganancia_por_agente.png` | completado | SC, SS, IE, Gini, RPE, GDR, **PoF** calculados con convención unificada de `net_benefit` en los 5 escenarios. PoF formal (Bertsimas, 2011 [15]) implementado en `analysis/fairness.py`: `compute_pof()`, `fairness_curve()`; integrado en `ComparisonResult.fairness` y hoja `PoF_Fairness` del Excel |
| **3** — Comparación cuantitativa de desempeño | **3.1** — Gestión y procesamiento de datos empíricos | `data/xm_data_loader.py`; `data/xm_prices.py`; `diagnostico_datos.py` | `graficas/fig1_perfiles.png`; `graficas/fig23_perfiles_diarios.png` | completado | MTE: 5 instituciones (Udenar, Mariana, UCC, HUDN, Cesmag), 6 144 h (abr.–dic. 2025), resolución 1 h, tz `America/Bogota`. Protocolo de limpieza y remuestreo documentado en `data/xm_data_loader.py`. fig1 muestra serie horaria completa; fig23 (agregada el 2026-04-27) muestra perfil diario promedio sobre los 256 días — complementarias |
| **3** | **3.2** — Ejecución de simulaciones comparativas | `main_simulation.py`; `analysis/subperiod.py`; `analysis/p2p_breakdown.py`; `analysis/monthly_report.py` | `graficas/fig3_mercado_p2p.png`; `graficas/fig4_metricas_horarias.png`; `graficas/fig13_desglose_flujos.png`; `graficas/fig16_subperiod.png`; `graficas/fig12_comparacion_mensual.png` | completado | Horizonte completo **6 144 h** ejecutado con MedicionesMTE_v3 (Abr–Dic 2025, 256 días). **Última corrida post-CAL-8: 2026-04-28, 55,2 min** (calibración Cedenar mensual per-agente). 1 031/6 144 h con mercado P2P activo (16,8 %); 3 659,3 kWh transados. Resultados: P2P 52,43 MCOP / C1 54,04 / C4 50,29 / Σ ventaja P2P − C4 = 2,14 MCOP. Sub-períodos SP1–SP4 computados. Reporte mensual en `graficas/fig12_comparacion_mensual.png` |
| **3** | **3.3** — Descomposición del bienestar y comparación monetaria | `scenarios/comparison_engine.py`; `analysis/optimality.py`; `core/settlement.py`; `analysis/fairness.py` | `graficas/fig14_optimalidad_horaria.png`; `graficas/fig15_c1_vs_c4.png`; `graficas/fig20_price_of_fairness.png` | completado | Descomposición monetaria vs. intangibles implementada. **RPE = +0,0408** (horizonte 6 144 h, post-CAL-8 2026-04-28). **PoF = 0,0000** (eficiente y equitativo coinciden = C1, sin tensión). PS = 71,4 % a compradores / PSR = 28,6 % a vendedores. GDR = 1,000 (clearing perfecto). Spread C4 = 1 004,4 kWh. PoF formal (Bertsimas 2011) integrado en `analysis/fairness.py` y visualizado en `fig20_price_of_fairness.png` |
| **4** — Sensibilidad y análisis de optimalidad | **4.1** — Análisis de sensibilidad mediante simulaciones | `analysis/global_sensitivity.py`; `analysis/sensitivity.py`; `analysis/sensitivity_2d.py`; `analysis/subperiod.py`; `scripts/sweep_pgb_pv.py` | `graficas/fig7_sensibilidad_pgb.png`; `graficas/fig8_sensibilidad_pv.png`; `graficas/fig9_factibilidad.png`; `graficas/fig10_sensibilidad_ppa.png`; `graficas/fig11_sensibilidad_pgs.png`; `graficas/fig16_subperiod.png`; `graficas/fig18_heatmap_pgb_pv.png`; `graficas/fig19_desercion_individual.png`; `graficas/fig21_robustez_c4_agente.png` | completado | Cobertura ortogonal de §VI.D: (i) **GSA Sobol-Saltelli** sobre el modelo de referencia (Chacón et al.): 7 parámetros, 3 outputs. **n_base = 128 ejecutado 2026-04-27** (2 048 evaluaciones, 1 367 válidas, modo preciso, 111 min). ST: `factor_PV` (0,66 ganancia / 0,82 SC), `factor_D` (0,44 ganancia), `PGB` (0,99 IE — dominante en seller-buyer balance, NO equidad distributiva; ver §A.10). Resultados en `outputs/resultados_gsa.xlsx`. Decisión: `_fast_mode` deprecado por cuelgues de LSODA en samples patológicos. (ii) **Barridos uni-paramétricos sobre MTE_v3**: SA-1/2/3/PPA sobre 6 144 h. (iii) **Sweep 2D PGB×PV** (`fig18_heatmap_pgb_pv.png`, `outputs/sensitivity_2d_pgb_pv.parquet`): mapa conjunto cobertura/precio. (iv) **Deserción individual** por agente (`fig19_desercion_individual.png`). (v) **Subperíodos** SP1–SP4. (vi) **Robustez C4 por agente** (`fig21`). Justificación metodológica en `Documentos/notas_modelo_tesis.md` §A.7. |
| **4** | **4.2** — Análisis cualitativo de optimalidad del equilibrio | `analysis/feasibility.py`; `analysis/optimality.py`; `tests/test_stackelberg_convergence.py`; `tests/statistical_tests.py` | `graficas/fig9_factibilidad.png`; `graficas/fig14_optimalidad_horaria.png`; `graficas/fig17_robustez_c4.png` | completado | Criterio de parada Stackelberg adaptativo validado. **Hallazgo IR post-CAL-8 (2026-04-28):** condición de racionalidad individual ahora 3/5 estables (Mariana, UCC, Cesmag — comerciales) y **2/5 en deserción a C1 (Udenar y HUDN — oficiales)** con umbrales `π_gb^*` de 180 y 233 COP/kWh respectivamente. La heterogeneidad oficial/comercial real cambia la frontera relevante de C4 → C1. Bootstrap previo (n=10 000, MTE_v3 pre-CAL-8): d=0,90; pendiente re-ejecutar con la calibración Cedenar para fijar IC definitivos sobre el delta P2P − C4 actualizado. |

---

## Resumen de cumplimiento por objetivo

| Objetivo | Actividades completadas | Actividades parciales | Total actividades |
|---|---|---|---|
| **1** — Análisis del modelo de referencia | 3 (1.0, 1.1, 1.2) | 0 | 3 |
| **2** — Modelado de escenarios | 2 (2.1, 2.2) | 0 | 2 |
| **3** — Comparación cuantitativa | 3 (3.1, 3.2, 3.3) | 0 | 3 |
| **4** — Sensibilidad y optimalidad | 2 (4.1, 4.2) | 0 | 2 |
| **TOTAL** | **10 / 10 (100 %)** | **0 / 10 (0 %)** | **10** |

**Pendientes de datos y escritura (no bloquean cumplimiento de actividades):**

- **GSA sobre MTE_v3 (diferido — decisión metodológica del 2026-04-26):**
  El GSA Sobol-Saltelli opera por diseño sobre el modelo de referencia (Chacón
  et al., 24 h sintético escalado por `factor_PV` y `factor_D`), no sobre series
  horarias MTE. La cobertura de "datos históricos" exigida por la propuesta
  §VI.D se cumple por los barridos uni-paramétricos sobre MTE_v3
  (`analysis/sensitivity.py`) y el análisis de subperíodos
  (`analysis/subperiod.py`). Justificación completa en
  `Documentos/notas_modelo_tesis.md` §A.7. **Actualización 2026-04-27:** GSA
  re-ejecutado con `n_base = 128` (en lugar del n=64 original); IC más
  estrechos pero todavía cualitativos. Una eventual ejecución con
  `n_base ≥ 256` para IC publicables queda como mejora opcional sujeta a
  petición del comité. La infraestructura `_fast_mode` (commit `19e57cb`)
  fue **deprecada** tras evidenciarse cuelgues de LSODA en samples
  patológicos (~58% del espacio Saltelli); el GSA actual usa modo preciso
  con timeout-wrapper de 45 s (ver `Documentos/notas_modelo_tesis.md` §A.7).
- **LCOE real:** Verificar datasheets de inversores instalados en las 5 instituciones MTE.
- ~~**Referencias:** Confirmar autores de [22][24][26][27] en `Documentos/references.bib`.~~ **CERRADO 2026-04-30** vía auditoría CrossRef (Tier 1.1 Ruflo): 6 entradas corregidas, ver `Documentos/bib_verificacion_2026-04-30.md`.
- **Nivel de tensión real per institución:** confirmar contra factura mensual Cedenar el supuesto NT2 actual del mapeo CAL-8.

---

## Archivos de referencia de este documento

| Archivo | Propósito |
|---|---|
| `Documentos/PropuestaTesis.txt` | Fuente autoritativa de las 10 actividades y sus alcances |
| `Documentos/Inventario_Act_1_0.md` | Evidencia de cumplimiento de Actividad 1.0 |
| `Documentos/Revision_Bibliografica_Act_1_2.md` | Evidencia de cumplimiento de Actividad 1.2 |
| `Documentos/references.bib` | Bibliografía consolidada (27 entradas, formato BibTeX IEEE) |
| `Documentos/notas_modelo_tesis.md` | Decisiones de diseño y justificaciones técnicas |
| `outputs/REPORTE_AVANCES.md` | Resultados numéricos de la última ejecución |
| `README.md` | Instrucciones de reproducibilidad |
| `docs/adr/0001..0008-*.md` | Architecture Decision Records de calibraciones CAL-1..CAL-8 |
| `Documentos/bib_verificacion_2026-04-30.md` | Auditoría CrossRef 2026-04-30 con las 6 correcciones del .bib |
| `Documentos/borrador_cap4_resultados.md` | Borrador estructurado del Capítulo 4 (sintetizado por Tier 1.2 Ruflo) |

---

## Anexo — Architecture Decision Records (ADRs CAL-1..CAL-33)

Cada decisión de calibración tiene un ADR formal en `docs/adr/`. Mapeo
de qué módulo está gobernado por qué ADR:

| ADR | Decisión | Módulos afectados | Actividad propuesta |
|---|---|---|---|
| [0001](../docs/adr/0001-cal1-stackelberg-iters.md) | `stackelberg_iters = 2` | `core/ems_p2p.py` | 2.1 |
| [0002](../docs/adr/0002-cal2-etha.md) | `etha = 0.1` | `core/replicator_buyers.py`, `core/ems_p2p.py` | 2.1 |
| [0003](../docs/adr/0003-cal3-alpha-dr.md) | `alpha_p = 0.20`, `alpha_c = 0.10` | `core/dr_program.py`, `core/ems_p2p.py` | 2.1, 4.1 |
| [0004](../docs/adr/0004-cal4-tau-scaling.md) | `tau_buyers/tau_sellers = 10` | `core/replicator_sellers.py`, `core/replicator_buyers.py` | 2.1 |
| [0005](../docs/adr/0005-cal5-theta.md) | `theta = 0.5` (solo reporting) | `core/ems_p2p.py::seller_welfare`, `buyer_welfare` | 2.1 |
| [0006](../docs/adr/0006-cal6-bn-lcoe-solar.md) | `b_n = 225 COP/kWh` real / vector u.o. sintético | `data/xm_prices.py`, `data/base_case_data.py` | 1.1, 1.2, 2.1 |
| [0007](../docs/adr/0007-cal7-stackelberg-alternancia.md) | Alternancia secuencial vs ODE conjunta | `core/ems_p2p.py:230-244` | 2.1 |
| [0008](../docs/adr/0008-cal8-pi-gs-cedenar.md) | `pi_gs` Cedenar mensual diferenciada per-agente (vector `(N,)`) | `data/cedenar_tariff.py`, `scenarios/_pi_gs.py`, `scenarios/scenario_c{1,2,3,4}_*.py`, `scenarios/comparison_engine.py`, `analysis/monthly_report.py`, `analysis/p2p_breakdown.py` | 1.0, 3.1, 3.2, 3.3 |
| [0009](../docs/adr/0009-cal9-pi-gs-temporal.md) | `pi_gs` matriz `(N, T)` mes a mes — supersede parcial 0008 en `--full` y `--day` | `scenarios/_pi_gs.py` (`as_pi_gs_array`), `scenarios/scenario_c{1,2,3,4}_*.py`, `scenarios/comparison_engine.py`, `analysis/feasibility.py`, `analysis/monthly_report.py`, `main_simulation.py`, `tests/test_pi_gs_temporal.py` | 1.1, 3.1, 3.2, 3.3 |
| [0010](../docs/adr/0010-cal10-creg174-tipo-1-2-componente-c.md) | C1 implementa Tipo 1/Tipo 2 + componente C (Cvm,i,j literal CREG 174 art. 25) | `scenarios/scenario_c1_creg174.py`, `scenarios/_pi_gs.py` (`as_component_c_array`, `cvm_per_agent_hourly`), `data/cedenar_tariff.py`, `tests/test_c1_creg174.py` | 2.1, 3.1, 3.2, 3.3 |
| [0011](../docs/adr/0011-cal11-c2-ppa-bilateral-modelo-formal.md) | CAL-11: C2 PPA bilateral (modelo formal) | `scenarios/scenario_c2_bilateral.py`, `data/xm_prices.py` (CSV bolsa anual) | 2.1, 3.x |
| [0015](../docs/adr/0015-cal15-c4-creg101072-tipo-1-2-cvm.md) | CAL-15: C4 (CREG 101 072 / Decreto 2236/2023) hereda Tipo 1/2 + Cvm,i,j de CREG 174 art. 25 | `scenarios/scenario_c4_creg101072.py`, `scenarios/comparison_engine.py`, `analysis/monthly_report.py`, `analysis/feasibility.py`, `main_simulation.py`, `tests/test_c4_creg101072.py` | 1.1, 3.1, 3.2, 3.3 |
| [0012](../docs/adr/0012-cal12-c2-fom-peajes.md) | CAL-12: C2 Front-of-Meter — `pi_ppa` reemplaza solo G; T+D+Cvm+PR+Rm+COT siempre se pagan | `scenarios/scenario_c2_bilateral.py`, `data/cedenar_tariff.py` (`g_component_per_agent_hourly`) | 2.1, 3.x |
| [0013](../docs/adr/0013-cal13-c2-no-regulado.md) | CAL-13: C2 alineado con marco no-regulado (Ley 143/1994 + CREG 086/1996 + Decreto 388/2007) | `scenarios/scenario_c2_bilateral.py`, `data/mem_costs_no_regulado.csv` | 3.x |
| [0014](../docs/adr/0014-cal14-creg101066-pes-ceiling.md) | CAL-14: Techo CREG 101 066/2024 (PES) en `pi_bolsa` | `data/xm_prices.py`, `tests/test_creg101066_ceiling.py` | 2.1, 3.x |
| [0016](../docs/adr/0016-cal16-c2-savings-decomposition.md) | CAL-16: Descomposición regulatoria del ahorro en C2 | `scenarios/scenario_c2_bilateral.py`, `analysis/savings_decomposition.py`, `tests/test_cal16_savings_decomposition.py` | 3.3 |
| [0017](../docs/adr/0017-cal17-pydataxm-vs-pb-prom.md) | CAL-17: Auditoría `pydataxm` vs PB_PROM oficial XM (corrección horizonte) | `data/xm_prices.py`, `data/precios_bolsa_xm_api.csv`, `data/audit_xm_yearly_summary.csv` | 2.1, 3.1 |
| [0018](../docs/adr/0018-cal18-cedenar-fail-fast.md) | CAL-18: Cedenar verificada 100 % + fail-fast (sin fallback silencioso) | `data/cedenar_tariff.py`, `tests/test_cedenar_no_fallback.py` | 2.1, 3.1 |
| [0019](../docs/adr/0019-cal19-stackelberg-convergencia.md) | CAL-19: Convergencia empírica del juego Stackelberg (sustento `iters=2`) | `core/ems_p2p.py`, `analysis/stackelberg_convergence_real.py` | 2.1 |
| [0020](../docs/adr/0020-cal20-cot-alpha-sensibilidad.md) | CAL-20: Sensibilidad de `cot_alpha` en C2 (sustento default 1.0) | `scenarios/scenario_c2_bilateral.py`, `scripts/study_cot_alpha.py` | 3.x |
| [0021](../docs/adr/0021-cal21-c2-f-split-sensibilidad.md) | CAL-21: Sensibilidad del split factor `f` en C2 (sustento `f=0.5`) | `scenarios/scenario_c2_bilateral.py`, `analysis/c2_f_sensitivity.py` | 3.x |
| [0022](../docs/adr/0022-cal22-c2-mem-costs-validacion.md) | CAL-22: Validación trazable de `mem_costs_no_regulado.csv` (FAZNI, contribución 4 %, comisión representante) | `data/mem_costs_no_regulado.csv`, `data/mem_costs_audit.md`, `tests/test_cal22_mem_costs_schema.py` | 3.x |
| [0023](../docs/adr/0023-cal23-c2-cxc-cargo-confiabilidad.md) | CAL-23: CXC en C2 (parametrizable, default conservador `cxc_alpha=0.0`) | `scenarios/scenario_c2_bilateral.py`, `scenarios/_c2_cxc.py` | 3.x |
| [0024](../docs/adr/0024-cal24-swarm-validador-regulatorio.md) | CAL-24: Swarm validador regulatorio (3 agentes especializados CREG 174/101 072/101 066) | `scripts/swarm_regulatory_validator.py` | 3.x |
| [0025](../docs/adr/0025-cal25-modo-paper.md) | CAL-25: Modo paper IEEE WEEF (homogeneización `INSTITUTION_PROFILE` + filtrado escenarios C1+C4+P2P) | `scripts/run_paper_iter.py`, `tests/test_run_paper_iter.py` | 4.1, 4.2 |
| [0026](../docs/adr/0026-cal26-pde-excedentes-proportional.md) | CAL-26: PDE proporcional a excedentes (método opt-in; default `capacity_proportional`) | `scenarios/scenario_c4_creg101072.py` (`compute_pde_weights`), `tests/test_cal26_pde_excedentes.py` | 2.1, 3.x |
| [0027](../docs/adr/0027-cal27-c4-mensual-hx.md) | CAL-27: C4-mensual con cruce Hx (cierra TODO de CAL-15) | `scenarios/scenario_c4_creg101072.py` (`_run_c4_monthly_hx`), `tests/test_cal27_c4_monthly.py` | 4.1, 4.2, 3.x |
| [0028](../docs/adr/0028-cal28-medidor-puntual.md) | CAL-28: Selección medidor puntual por institución (paper) — sub-medidor M3 + Mariana M1×0.3 | `scripts/run_paper_iter.py`, `data/mte_meter_selection.py` | 4.1, 4.2 |
| [0029](../docs/adr/0029-cal29-p2p-revenue-canonica.md) | CAL-29: Fórmula canónica de `net_benefit` P2P en `_p2p_decomposed` (paper, audit Sprint 6.6-A) | `scripts/run_paper_iter.py` (`_p2p_decomposed`), `tests/test_cal29_p2p_canonical.py` | 4.1, 4.2 |
| [0030](../docs/adr/0030-cal30-engine-canonical.md) | CAL-30: Migración del engine a fórmula canónica P2P (Sprint 7) — supersede `_p2p_monetary_benefit` | `scenarios/comparison_engine.py` (`_p2p_monetary_benefit`), `analysis/monthly_report.py`, `main_simulation.py` | 4.1, 4.2 |
| [0031](../docs/adr/0031-cal31-renumeracion-art-creg-101072.md) | CAL-31: Re-numeración correcta artículos CREG (174 art. 25, 101 072 art. 19/20) + aclaratoria terminológica Tipo 1/2/Hx + tracking CREG 101-087/2025 | `scenarios/scenario_c1_creg174.py`, `scenarios/scenario_c2_bilateral.py`, `scenarios/scenario_c4_creg101072.py` (docstrings), `Documentos/audit_regulatorio_C1_C4.md` | 3.1, 3.2, 3.3 |
| [0032](../docs/adr/0032-cal32-c-coefficient-defense.md) | CAL-32: Defensa de `c_j = 1.2` uniforme (offset aditivo en H_j; no entra en gradiente ∂H/∂P, equilibrio invariante) | `scripts/run_paper_iter.py:259`, `outputs/paper/paper_weef.md` (Methods) | 2.1, 4.2 |
| [0033](../docs/adr/0033-cal33-lambda-homogeneity.md) | CAL-33: `λ_j = 100` uniforme bajo homogeneidad de tecnología FV + α=0 (analíticamente invariante en eq. 7 cuando D_j*=D_j fijo) | `scripts/run_paper_iter.py:260`, `outputs/paper/paper_weef.md` (Methods) | 2.1, 4.2 |

**Regla de oro:** cualquier modificación futura a un módulo listado
arriba debe acompañarse de una nueva ADR (0010+) que supersede a la
correspondiente, o de una nota explícita en la existente. La memoria
semántica Ruflo (`namespace adr`) recupera estos ADRs por búsqueda
contextual.

**ADR 0009 — Detalle del wiring por modo de ejecución (`main_simulation.py:213`):**

| Modo de `main_simulation.py` | `pi_gs_arg` | Forma | Razón |
|---|---|---|---|
| `--data real --full` | `pi_gs_per_agent_hourly(names, index_full)` | `(N, T_full)` | Cada hora liquida con el CU del mes que la contiene |
| `--data real --day YYYY-MM-DD` | `pi_gs_per_agent_hourly(names, idx_day)` | `(N, 24)` | Liquidación intra-día con CU del mes vigente |
| `--data real` (perfil diario default) | `pi_gs_per_agent` | `(N,)` CAL-8 | El perfil 24 h promedia el horizonte; sin variabilidad temporal |
| Sintético (sin `--data real`) | `grid_params["pi_gs"]` | `float` | Caso uniforme; barridos de sensibilidad |

`scenarios._pi_gs.as_pi_gs_array(pi_gs, N, T)` normaliza al contrato
canónico `(N, T)` con broadcast retro-compatible para los cuatro
casos. `as_pi_gs_vector(pi_gs, N)` se conserva como adaptador para
callers que aún consumen el vector CAL-8 (colapsa la matriz al
promedio temporal).

---

## Anexo — Diagrama de dependencias (Mermaid)

```mermaid
flowchart TB
    PROP[Propuesta de tesis]
    subgraph O1[Obj 1: Caracterizacion]
      A10[Act 1.0]
      A11[Act 1.1]
      A12[Act 1.2]
    end
    subgraph O2[Obj 2: Modelo P2P]
      A21[Act 2.1]
      A22[Act 2.2]
    end
    subgraph O3[Obj 3: Regulatorio]
      A31[Act 3.1]
      A32[Act 3.2]
      A33[Act 3.3]
    end
    subgraph O4[Obj 4: Optimalidad]
      A41[Act 4.1]
      A42[Act 4.2]
    end
    PROP --> O1 --> O2 --> O3 --> O4

    subgraph CODE[Codigo Python]
      D[data/]
      C[core/]
      S[scenarios/]
      AN[analysis/]
    end
    A10 --> D
    A11 --> D
    A12 --> D
    A21 --> C
    A22 --> C
    A31 --> S
    A32 --> AN
    A33 --> AN
    A41 --> AN
    A42 --> AN

    subgraph FIGS[graficas/ 23 figuras]
      F1[fig1, fig23 datos]
      F5[fig5, fig6 comparacion]
      F12[fig12, fig13 mensual+horario]
      F14[fig14, fig15 optimalidad]
      F7[fig7-fig11, fig18 sensibilidad]
      F17[fig17, fig21 robustez C4]
      F19[fig19 desercion IR]
      F20[fig20 PoF]
      F22[fig22 convergencia]
    end
    D --> F1
    S --> F5
    AN --> F12
    AN --> F14
    AN --> F7
    AN --> F17
    AN --> F19
    AN --> F20
    C --> F22

    subgraph ADRS[ADRs CAL-1..CAL-33]
      ADR_CORE[CAL-1..7 nucleo P2P:<br/>iters, etha, alpha DR,<br/>tau, theta, b_n LCOE, alternancia]
      ADR_TARIFFS[CAL-8/9/12 tarifas:<br/>Cedenar vector / matriz NxT,<br/>C2 Front-of-Meter peajes]
      ADR_REG_C1[CAL-10/14 C1 + bolsa:<br/>Tipo 1/2 + Cvm CREG 174 art. 25,<br/>techo PES CREG 101 066]
      ADR_REG_C2[CAL-11/13/16/20-23 C2:<br/>PPA bilateral, no-regulado,<br/>desc. ahorro, cot_alpha, f, mem_costs, CXC]
      ADR_REG_C4[CAL-15/26/27 C4:<br/>Tipo 1/2 + Cvm CREG 101 072,<br/>PDE excedentes, mensual Hx]
      ADR_DATA[CAL-17/18 datos:<br/>pydataxm vs PB_PROM,<br/>Cedenar fail-fast]
      ADR_SUSTENTO[CAL-19 convergencia<br/>Stackelberg empirica]
      ADR_TOOLING[CAL-24 swarm<br/>validador regulatorio]
      ADR_PAPER[CAL-25/28/29/30 paper + engine:<br/>modo paper, medidor puntual,<br/>net_benefit canonico P2P]
      ADR_AUDIT[CAL-31 audit regulatorio:<br/>renumeracion arts. + CREG 101-087/2025]
    end
    C --> ADR_CORE
    D --> ADR_TARIFFS
    S --> ADR_TARIFFS
    S --> ADR_REG_C1
    S --> ADR_REG_C2
    S --> ADR_REG_C4
    D --> ADR_DATA
    C --> ADR_SUSTENTO
    AN --> ADR_TOOLING
    S --> ADR_PAPER
    S --> ADR_AUDIT
```

---

## Anexo — Verificaciones automatizables

Comandos que un asesor o auditor puede ejecutar para validar la
trazabilidad sin revisar el código línea por línea:

| Pregunta del asesor | Comando | Resultado esperado |
|---|---|---|
| ¿Tiene cada actividad implementación de código? | `grep -rn "Activity\|Actividad" analysis/ scenarios/ data/ core/` | ≥ 10 hits etiquetados |
| ¿Tienen las figuras siblings .csv/.mat? | `ls graficas/fig*__*.csv \| wc -l` | 44 (.csv) |
| | `ls graficas/*.mat \| wc -l` | 16 (.mat) |
| ¿Pasan todos los tests? | `pytest tests/ -q` | 33/33 verde |
| ¿Está CAL-8 propagada en escenarios? | `grep -l "as_pi_gs_vector" scenarios/` | 5 archivos C1-C4 + comparison_engine |
| ¿Coinciden ADR y código (etha)? | `grep "etha\s*=\s*" core/replicator_buyers.py core/ems_p2p.py` | `0.1` (per ADR 0002) |
| ¿Coinciden ADR y código (stackelberg_iters)? | `grep "stackelberg_iters\s*=" core/ems_p2p.py` | `2` (per ADR 0001) |
| ¿Coinciden ADR y código (alpha_p)? | `grep "alpha_p\s*=" core/dr_program.py core/ems_p2p.py` | `0.20` (per ADR 0003) |
| ¿Tarifa Cedenar tiene cobertura completa? | `head -5 data/tarifas_cedenar_mensual.csv && wc -l data/tarifas_cedenar_mensual.csv` | 130 filas, abr-2025 → abr-2026 |
| ¿Última corrida `--full` está consolidada? | `grep "post-CAL-8" outputs/REPORTE_AVANCES.md` | hits con fecha 2026-04-28 |
| ¿Bib es válido vs CrossRef? | `grep -c VERIFICAR Documentos/references.bib` | 0 entradas activas (solo cabecera explicativa) |

## Anexo — Recuperación semántica vía Ruflo

La trazabilidad también vive en memoria semántica para búsqueda
contextual. 124 entradas distribuidas en namespaces:

```bash
# ¿Qué módulo implementa la actividad X?
npx @claude-flow/cli memory search --query "actividad 4.1 Price of Fairness"
# → adr-* + kg-node-analysis-fairness + kg-edge-doc-propuesta--actividad-4.1--*

# ¿Qué decisión gobierna un parámetro?
npx @claude-flow/cli memory search --query "alpha demand response prosumidores"
# → adr-0003-cal3-alpha-dr (score ~0.7)

# Recorrer impacto de un cambio
npx @claude-flow/cli memory list --namespace knowledge-graph | grep "kg-edge-.*core-ems_p2p"
```

**Re-sembrar al añadir nueva actividad/módulo/figura/ADR:**
```bash
python scripts/seed_ruflo_kg.py    # actualiza grafo
python scripts/seed_ruflo_adr.py   # si añadiste ADR 0009+
```

---

**Última actualización:** 2026-05-06 (post-Sprint 8 / CAL-33 follow-up — defensa parámetros c_j, λ_j + bug fix CAL-6).
Cambios respecto a 2026-04-30:

- Anexo ADR extendido a CAL-1..CAL-31 (22 ADRs nuevos: CAL-10/CAL-15/
  CAL-12/CAL-13/CAL-14/CAL-16..CAL-31).
- Diagrama Mermaid agrupa ADRs por dominio (núcleo P2P, tarifas,
  regulatorio C1/C2/C4, datos, sustento, tooling, paper, audit).
- Sprint 6 (paper IEEE WEEF 2026): CAL-25..CAL-29 documentados.
- Sprint 7 (engine canónico): CAL-30 — `_p2p_monetary_benefit`
  migrado a fórmula canónica con gate de seguridad ±0.5 % RPE.
- Sprint 8 (auditoría regulatoria integral C1-C4): CAL-31 — 5
  fixes documentales de numeración artículos CREG (verificada
  oficialmente vía `gestornormativo.creg.gov.co`); tracking
  CREG 101-087/2025; auditoría completa en
  `Documentos/audit_regulatorio_C1_C4.md`.

**Notas pendientes** (autor humano, fuera del alcance de las
actividades 1-4 ya completadas, ver §8 de
`Documentos/audit_regulatorio_C1_C4.md`):

- 🚨 Verificar y corregir cita "Ley 2099/2021 art. 45" (probablemente
  art. 48): aparece en `data/cedenar_tariff.py:714-715`,
  `tests/test_cal16_savings_decomposition.py:17`,
  `scenarios/comparison_engine.py:128`,
  `scripts/seed_ruflo_adr.py:226,515`.
- Confirmar con CEDENAR clasificación tarifaria de cada institución
  MTE (¿pagan contribución 4 % sobre G?).
- Ejecutar `python main_simulation.py --data real --full --analysis`
  (~30 min) para capturar RPE canónica horizonte completo post-CAL-30.
