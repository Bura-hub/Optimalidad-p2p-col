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
| **1** — Análisis del modelo de referencia | **1.0** — Inventario de elementos del sistema e insumos por escenario | `Documentos/Inventario_Act_1_0.md`; `data/base_case_data.py`; `data/xm_prices.py` | — | completado | Inventario formal de 5 escenarios, 6 agentes MTE y parámetros de la Tabla I canónica (Chacón et al., 2025) |
| **1** | **1.1** — Revisión y consolidación del modelo base | `core/ems_p2p.py`; `core/replicator_sellers.py`; `core/replicator_buyers.py`; `core/market_prep.py`; `tests/validate_base_model.py`; `tests/golden_test_sofia.py` | `graficas/fig11_convergencia_h*.png` | completado | Replicator Dynamics + Stackelberg implementados. Golden test verifica P_total dentro de atol = 0,15 kWh y pi_i ∈ [PGB, PGS] vs oráculo SLSQP (Bienestar6p.py). Tolerancia rtol = 5 % documentada en `tests/golden_test_sofia.py` |
| **1** | **1.2** — Inferencia de parámetros mediante revisión bibliográfica y datos reales | `Documentos/Revision_Bibliografica_Act_1_2.md`; `Documentos/references.bib`; `data/base_case_data.py`; `data/xm_prices.py` | Tablas 1.1–1.5 (en `Revision_Bibliografica_Act_1_2.md`) | completado | b_n = 225 COP/kWh (LCOE solar Pasto, IRENA [16]/UPME [17]); ε_p corto plazo −0,20 a −0,47 (LAC, [19][20]); λ_n = 100, θ_n = 0,5, η_i = 0,1 calibrados contra [5][22][25]. 12 fuentes DOI-verificadas (3 con autores pendientes de confirmación) |
| **2** — Modelado de escenarios regulatorios | **2.1** — Estructuración matemática de escenarios C1–C4 | `scenarios/scenario_c1_creg174.py`; `scenarios/scenario_c2_bilateral.py`; `scenarios/scenario_c3_spot.py`; `scenarios/scenario_c4_creg101072.py` | — | completado | C1: créditos 1:1 + excedentes a bolsa (CREG 174/2021 [3]). C2: PPA bilateral precio fijo. C3: exposición total precio bolsa horario. C4: distribución administrativa vía PDE (CREG 101 072/2025 [4]), modo `pde_only` por defecto |
| **2** | **2.2** — Algoritmos de cálculo de métricas | `scenarios/comparison_engine.py`; `core/settlement.py`; `analysis/optimality.py`; `analysis/fairness.py` | `graficas/fig5_comparacion_regulatoria.png`; `graficas/fig6_ganancia_por_agente.png` | completado | SC, SS, IE, Gini, RPE, GDR, **PoF** calculados con convención unificada de `net_benefit` en los 5 escenarios. PoF formal (Bertsimas, 2011 [15]) implementado en `analysis/fairness.py`: `compute_pof()`, `fairness_curve()`; integrado en `ComparisonResult.fairness` y hoja `PoF_Fairness` del Excel |
| **3** — Comparación cuantitativa de desempeño | **3.1** — Gestión y procesamiento de datos empíricos | `data/xm_data_loader.py`; `data/xm_prices.py`; `diagnostico_datos.py` | `graficas/fig1_perfiles.png` | completado | MTE: 5 instituciones (Udenar, Mariana, UCC, HUDN, Cesmag), 5 160 h (jul. 2025–ene. 2026), resolución 1 h, tz `America/Bogota`. Protocolo de limpieza y remuestreo documentado en `data/xm_data_loader.py` |
| **3** | **3.2** — Ejecución de simulaciones comparativas | `main_simulation.py`; `analysis/subperiod.py`; `analysis/p2p_breakdown.py`; `analysis/monthly_report.py` | `graficas/fig3_mercado_p2p.png`; `graficas/fig4_metricas_horarias.png`; `graficas/fig13_desglose_flujos.png`; `graficas/fig16_subperiod.png`; `graficas/fig12_comparacion_mensual.png` | completado | Horizonte completo **6 144 h** ejecutado con MedicionesMTE_v3 (Abr–Dic 2025, 256 días). Última corrida 2026-04-27, ~52 min. 1 031/6 144 h con mercado P2P activo (16,8 %); 3 657,7 kWh transados. Sub-períodos SP1–SP4 computados. Reporte mensual en `graficas/fig12_comparacion_mensual.png` |
| **3** | **3.3** — Descomposición del bienestar y comparación monetaria | `scenarios/comparison_engine.py`; `analysis/optimality.py`; `core/settlement.py`; `analysis/fairness.py` | `graficas/fig14_optimalidad_horaria.png`; `graficas/fig15_c1_vs_c4.png`; `graficas/fig20_price_of_fairness.png` | completado | Descomposición monetaria vs. intangibles implementada. RPE = 0,0321 (horizonte 6 144 h). **PoF formal (Bertsimas 2011)** implementado y calculado automáticamente en cada ejecución: `analysis/fairness.py`, visualizado en `fig20_price_of_fairness.png`. GDR y spread de ineficiencia estática C4 documentados en `outputs/REPORTE_AVANCES.md` |
| **4** — Sensibilidad y análisis de optimalidad | **4.1** — Análisis de sensibilidad mediante simulaciones | `analysis/global_sensitivity.py`; `analysis/sensitivity.py`; `analysis/sensitivity_2d.py`; `analysis/subperiod.py`; `scripts/sweep_pgb_pv.py` | `graficas/fig7_sensibilidad_pgb.png`; `graficas/fig8_sensibilidad_pv.png`; `graficas/fig9_factibilidad.png`; `graficas/fig10_sensibilidad_ppa.png`; `graficas/fig11_sensibilidad_pgs.png`; `graficas/fig16_subperiod.png`; `graficas/fig18_heatmap_pgb_pv.png`; `graficas/fig19_desercion_individual.png`; `graficas/fig21_robustez_c4_agente.png` | completado | Cobertura ortogonal de §VI.D: (i) **GSA Sobol-Saltelli** sobre el modelo de referencia (Chacón et al.): 7 parámetros, 3 outputs. **n_base = 128 ejecutado 2026-04-27** (2 048 evaluaciones, 1 367 válidas, modo preciso, 111 min). ST: `factor_PV` (0,66 ganancia / 0,82 SC), `factor_D` (0,44 ganancia), `PGB` (0,99 IE — dominante en equidad). Resultados en `outputs/resultados_gsa.xlsx`. Decisión: `_fast_mode` deprecado por cuelgues de LSODA en samples patológicos. (ii) **Barridos uni-paramétricos sobre MTE_v3**: SA-1/2/3/PPA sobre 6 144 h. (iii) **Sweep 2D PGB×PV** (`fig18_heatmap_pgb_pv.png`, `outputs/sensitivity_2d_pgb_pv.parquet`): mapa conjunto cobertura/precio. (iv) **Deserción individual** por agente (`fig19_desercion_individual.png`). (v) **Subperíodos** SP1–SP4. (vi) **Robustez C4 por agente** (`fig21`). Justificación metodológica en `Documentos/notas_modelo_tesis.md` §A.7. |
| **4** | **4.2** — Análisis cualitativo de optimalidad del equilibrio | `analysis/feasibility.py`; `analysis/optimality.py`; `tests/test_stackelberg_convergence.py`; `tests/statistical_tests.py` | `graficas/fig9_factibilidad.png`; `graficas/fig14_optimalidad_horaria.png`; `graficas/fig17_robustez_c4.png` | completado | Criterio de parada Stackelberg adaptativo validado. **Bootstrap re-ejecutado 2026-04-27** con n=10 000 sobre MTE_v3 (256 días, block_days=7): Δ̄ = 4 732 COP/día (P2P − C4), IC 95% [3 629, 5 751], p Wilcoxon < 0,001, **Cohen's d = 0,90** (efecto grande). Resultado más robusto que la corrida previa (n=500, 215 días). |

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
- **Referencias:** Confirmar autores de [22][24][26][27] en `Documentos/references.bib`.

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
