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
| **2** | **2.2** — Algoritmos de cálculo de métricas | `scenarios/comparison_engine.py`; `core/settlement.py`; `analysis/optimality.py` | `graficas/fig5_comparacion_regulatoria.png`; `graficas/fig6_ganancia_por_agente.png` | completado | SC, SS, IE, Gini, RPE, GDR calculados con convención unificada de `net_benefit` en los 5 escenarios. RPE ≠ PoF (Bertsimas, 2011 [15]); stub TODO documentado en `scenarios/comparison_engine.py` |
| **3** — Comparación cuantitativa de desempeño | **3.1** — Gestión y procesamiento de datos empíricos | `data/xm_data_loader.py`; `data/xm_prices.py`; `diagnostico_datos.py` | `graficas/fig1_perfiles.png` | completado | MTE: 5 instituciones (Udenar, Mariana, UCC, HUDN, Cesmag), 5 160 h (jul. 2025–ene. 2026), resolución 1 h, tz `America/Bogota`. Protocolo de limpieza y remuestreo documentado en `data/xm_data_loader.py` |
| **3** | **3.2** — Ejecución de simulaciones comparativas | `main_simulation.py`; `analysis/subperiod.py`; `analysis/p2p_breakdown.py`; `analysis/monthly_report.py` | `graficas/fig3_mercado_p2p.png`; `graficas/fig4_metricas_horarias.png`; `graficas/fig13_desglose_flujos.png`; `graficas/fig16_subperiod.png` | parcial — falta run `--full` 5 160 h (postergado) | Perfil diario promedio MTE disponible (modo `--data real`). Día de referencia 2025-08-06 ejecutado (`outputs/run_day_2025-08-06_1458.log`, 12 225 s). Sub-períodos SP1–SP4 (laborable/finde × Jul/Ene) computados. Run horizonte completo (`--data real --full`) postergado por decisión del usuario. Condición de cierre: lanzar `--full` cuando el equipo lo autorice |
| **3** | **3.3** — Descomposición del bienestar y comparación monetaria | `scenarios/comparison_engine.py`; `analysis/optimality.py`; `core/settlement.py` | `graficas/fig14_optimalidad_horaria.png`; `graficas/fig15_c1_vs_c4.png` | completado | Descomposición monetaria vs. intangibles implementada. RPE = (W_P2P − W_C4) / |W_P2P| = 0,3035 (perfil diario promedio). GDR y spread de ineficiencia estática C4 = 14,164 kWh/período documentados en `REPORTE_AVANCES.md` |
| **4** — Sensibilidad y análisis de optimalidad | **4.1** — Análisis de sensibilidad mediante simulaciones | `analysis/global_sensitivity.py`; `analysis/sensitivity.py` | `graficas/fig7_sensibilidad_pgb.png`; `graficas/fig8_sensibilidad_pv.png`; `graficas/fig10_sensibilidad_ppa.png`; `graficas/fig11_sensibilidad_pgs.png` | completado | SALib 1.5.2. GSA Sobol-Saltelli (7 parámetros, 3 outputs, n_base = 64, 1 024 evaluaciones) ejecutado el 2026-04-17; resultados en `resultados_gsa.xlsx`. Factores más influyentes: `factor_PV` (SC y ganancia), `PGB` (IE). IC amplios por n_base = 64; los índices S1 negativos son artefacto de varianza; ST cualitativamente interpretables. Barridos paramétricos SA-1 (PGB), SA-2 (PV), SA-3 (PGS) y SA-PPA completados en `analysis/sensitivity.py`. Para IC más estrechos (publicación) se requiere n_base ≥ 256 (~3–4 h) |
| **4** | **4.2** — Análisis cualitativo de optimalidad del equilibrio | `analysis/feasibility.py`; `analysis/optimality.py`; `tests/test_stackelberg_convergence.py`; `tests/statistical_tests.py` | `graficas/fig9_factibilidad.png`; `graficas/fig14_optimalidad_horaria.png`; `graficas/fig17_robustez_c4.png` | completado | Criterio de parada Stackelberg adaptativo (tol = 1e-3, min_iter = 2, max_iter = 10) implementado y validado. Bootstrap por bloques Kunsch (1989) + Wilcoxon pareado en `tests/statistical_tests.py`. Datos reales para bootstrap pendientes del run `--full` |

---

## Resumen de cumplimiento por objetivo

| Objetivo | Actividades completadas | Actividades parciales | Total actividades |
|---|---|---|---|
| **1** — Análisis del modelo de referencia | 3 (1.0, 1.1, 1.2) | 0 | 3 |
| **2** — Modelado de escenarios | 2 (2.1, 2.2) | 0 | 2 |
| **3** — Comparación cuantitativa | 2 (3.1, 3.3) | 1 (3.2) | 3 |
| **4** — Sensibilidad y optimalidad | 2 (4.1, 4.2) | 0 | 2 |
| **TOTAL** | **9 / 10 (90 %)** | **1 / 10 (10 %)** | **10** |

**Actividad parcial y condición de cierre:**

- **3.2:** Requiere `python main_simulation.py --data real --full --analysis` (~20–30 min) para
  generar resultados sobre las 5 160 h de la ventana MTE. Esta ejecución está **postergada**
  por decisión del usuario (2026-04-17). Resultado parcial disponible: perfil diario promedio
  en `REPORTE_AVANCES.md` y día de referencia 2025-08-06 en
  `outputs/run_day_2025-08-06_1458.log`.

---

## Archivos de referencia de este documento

| Archivo | Propósito |
|---|---|
| `Documentos/PropuestaTesis.txt` | Fuente autoritativa de las 10 actividades y sus alcances |
| `Documentos/Inventario_Act_1_0.md` | Evidencia de cumplimiento de Actividad 1.0 |
| `Documentos/Revision_Bibliografica_Act_1_2.md` | Evidencia de cumplimiento de Actividad 1.2 |
| `Documentos/references.bib` | Bibliografía consolidada (27 entradas, formato BibTeX IEEE) |
| `Documentos/notas_modelo_tesis.md` | Decisiones de diseño y justificaciones técnicas |
| `REPORTE_AVANCES.md` | Resultados numéricos de la última ejecución |
| `README.md` | Instrucciones de reproducibilidad |
