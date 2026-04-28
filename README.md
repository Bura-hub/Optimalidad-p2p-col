# Tesis: Análisis de Optimalidad y Validación Regulatoria de Mercados P2P en Colombia

**Autor:** Brayan S. Lopez-Mendez  
**Asesores:** M.Sc. Andrés Pantoja — M.Sc. Germán Obando  
**Programa:** Maestría en Ingeniería Electrónica — Universidad de Nariño, 2026  
**Modelo base:** Sofía Chacón Chamorro (Chacón et al., 2025) — JoinFinal.m / Bienestar6p.py

---

## Estructura del proyecto

```
tesis_p2p/
├── main_simulation.py          ← punto de entrada único
├── core/
│   ├── ems_p2p.py              ← motor EMS paralelo + barra progreso
│   ├── market_prep.py          ← G_klim + clasificación GDR
│   ├── replicator_sellers.py   ← Algoritmo 2: RD vendedores
│   ├── replicator_buyers.py    ← Algoritmo 3: RD compradores
│   ├── settlement.py           ← liquidación + métricas SS/SC/Gini unificadas
│   └── dr_program.py           ← DR program (alpha=0 en datos reales, sin DR)
├── scenarios/
│   ├── scenario_c1_creg174.py       ← CREG 174/2021 créditos 1:1 (balance mensual real)
│   ├── scenario_c2_bilateral.py     ← Bilateral PPA
│   ├── scenario_c3_spot.py          ← Mercado spot precio bolsa
│   ├── scenario_c4_creg101072.py    ← AGRC + PDE (escenario vigente)
│   └── comparison_engine.py         ← 5 escenarios, Nivel 1 y 2 + Gini + desglose flujos
├── data/
│   ├── base_case_data.py       ← parámetros + GRID_PARAMS (sintético) + GRID_PARAMS_REAL (COP, fallback)
│   ├── xm_data_loader.py       ← cargador CSV MTE (pandas 3.x compatible)
│   ├── xm_prices.py            ← precios XM reales/sintéticos + calibración parámetro b
│   ├── cedenar_tariff.py       ← CAL-8: tarifa CU mensual Cedenar per-agente (oficial/comercial)
│   ├── tarifas_cedenar_mensual.csv  ← 130 filas, abr-2025 → abr-2026
│   └── cedenar_pdfs/           ← 13 PDFs oficiales respaldatorios
├── analysis/
│   ├── sensitivity.py          ← SA-1 (PGB) + SA-2 (PV) + SA-3 (π_gs) + SA-PPA + umbrales
│   ├── sensitivity_2d.py       ← Sweep bivariado PGB×PV (Act 4.1, parquet persistido)
│   ├── global_sensitivity.py   ← GSA Saltelli/Sobol (SALib, 7 params, 3 outputs, --gsa)
│   ├── feasibility.py          ← FA-1 (deserción horaria + IR individual) + FA-2 (CREG 101 072)
│   ├── fairness.py             ← Price of Fairness formal (Bertsimas et al., 2011)
│   ├── p2p_breakdown.py        ← §3.12 Desglose P2P hora a hora → CSV + Excel
│   ├── monthly_report.py       ← Reporte mes a mes para horizonte completo (--full)
│   ├── subperiod.py            ← SP1–SP4: laborable/fin-semana × julio/enero (Act. 3.2)
│   └── optimality.py           ← Dominancia P2P vs C4 por hora, GDR (Act. 4.2)
├── visualization/
│   ├── plots.py                ← 21 figuras automáticas (fig1–fig21)
│   └── matlab_export.py        ← Helper de exportación MATLAB (.csv UTF-8 BOM + .mat siblings)
├── scripts/
│   ├── sweep_pgb_pv.py              ← CLI sweep 2D PGB×PV → outputs/sensitivity_2d_pgb_pv.parquet
│   ├── probe_gsa_samples.py         ← Diagnóstico de samples Saltelli (timeout configurable)
│   ├── data_quality_audit.py        ← Auditoría 27 fuentes raw MTE
│   ├── audit_clean.py               ← Auditoría post-preprocesamiento
│   └── plot_coverage_gantt.py       ← Gráfico cobertura temporal por institución
├── tests/
│   ├── validate_base_model.py
│   ├── calibration_study.py              ← estudio de calibración de parámetro b
│   ├── profile_stress_test.py            ← stress test perfiles extremos
│   ├── golden_test_sofia.py              ← golden test RD vs SLSQP (Bienestar6p.py)
│   ├── test_stackelberg_convergence.py   ← criterio de parada Stackelberg adaptativo
│   ├── test_fast_mode_equivalence.py     ← validación 8 horas (NO toda Saltelli; ver A.7)
│   ├── test_matlab_export.py             ← 8 tests del helper MATLAB
│   └── statistical_tests.py             ← bootstrap bloques Kunsch + Wilcoxon P2P vs C4
└── diagnostico_datos.py
```

**Total tests pytest:** 33 verdes (`python -m pytest tests/ -q`).

---

## Comandos de ejecución

```powershell
# Modo 1 — Validación sintética (24h, ~35s)
python main_simulation.py

# Modo 2 — Perfil diario promedio MTE (24h, ~1 min con LSODA adaptativo)
python main_simulation.py --data real

# Modo 3 — Perfil diario + sensibilidad y factibilidad (~5 min)
python main_simulation.py --data real --analysis

# Modo 4 — Horizonte completo 6144h / 256 días (~52 min, medido 2026-04-27)
python main_simulation.py --data real --full

# Modo 5 — Horizonte completo + todos los análisis (~100 min, corrida definitiva)
python main_simulation.py --data real --full --analysis

# Con rutas explícitas
$env:MTE_ROOT="C:\ruta\a\MedicionesMTE"
$env:XM_PRICES_CSV="C:\ruta\precios_bolsa_xm.csv"   # opcional
python main_simulation.py --data real --analysis

# Modo 6 — Análisis de sensibilidad global Saltelli (GSA Sobol)
# n_base=128 → 2048 evaluaciones, ~111 min con 11 workers (corrida actual)
python main_simulation.py --gsa --n-base 128

# n_base=64 → 1024 evaluaciones, ~75 min (válida para resultados cualitativos)
python main_simulation.py --gsa --n-base 64

# GSA smoke test ultrarrápido (verificación ~5 min)
python main_simulation.py --gsa --n-base 4

# Modo 7 — Sweep bivariado PGB×PV (~7 min, grid 20×20 serial)
# Importante: workers=1 obligatorio en Windows (deadlock conocido del ProcessPoolExecutor)
python scripts/sweep_pgb_pv.py --grid 20 --workers 1

# Tests estadísticos bootstrap (requiere outputs/daily_series_*.csv del run --full)
python tests/statistical_tests.py --n-bootstrap 10000 --block-days 7
```

---

## Datos empíricos MTE — Instituciones

**MTE** = Medición de Tecnologías de Energía (proyecto de monitoreo de
5 instituciones en Pasto, Nariño; ver `Documentos/Inventario_Act_1_0.md:13`).

### Pipeline de datos (`data/preprocessing.py`)

Cada vez que `main_simulation.py` se ejecuta con `--data real`, el preprocesamiento corre primero (≈ 5–10 s sobre `MedicionesMTE_v3`):

1. **Eje horario canónico** Abr 4 → Dic 16 2025 (6 144 h).
2. **Por cada institución**:
   - Lee **un medidor de demanda específico** (definido en `DEMAND_METER_CONFIG`), concatenando los CSVs particionados temporalmente (v3 = 3 archivos por medidor: Ene-Jun, Jun-Ene, Ene-Abr).
   - Lee **un inversor EMS específico** (`EMS_INVERTER_CONFIG`), W→kW, `clip(0)`.
   - Resuelve no-negatividad según el tipo del medidor:
     - **`net`** (Udenar): `D = max(0, D_net + Σ_3-inversores)` para revertir el netting agresivo del totalizador.
     - **`net_partial`** (Mariana, UCC): `D = max(0, D_net + 1-inversor)` para corregir las pocas horas con D < 0.
     - **`gross`** (HUDN, Cesmag): `D = max(0, D_raw)`, sólo clip defensivo.
   - Aplica `_clean()`: outliers `> max(Q75+5·IQR, P99.5×1.2)` → NaN; interpolación ≤ 3 h, ffill/bfill ≤ 24 h, `fillna(0)`.
3. **Apila** en arrays `(5, 6144)` float64.
4. **Sanity check**: `(D ≥ 0).all()` y `(G ≥ 0).all()` (RuntimeError si fallan).
5. **Localiza tz** `America/Bogota`.

Configuración por institución (sobreescribible vía kwargs a `MTEDataLoader`):

| Institución (n) | D̄ (kW) | Ḡ (kW) | Cobertura PV | Tipo | Inversor EMS | Rol |
|---|---|---|---|---|---|---|
| Udenar (n=0)    | 7.21    | 2.15    | 30 %         | net          | Fronius Inverter 1 | Comprador / vendedor mediodía |
| Mariana (n=1)   | 9.57    | 2.04    | 21 %         | net_partial  | Fronius - Alvernia | Comprador / vendedor mediodía |
| UCC (n=2)       | 21.42   | 2.50    | 12 %         | net_partial  | Fronius - UCC      | Comprador firme |
| HUDN (n=3)      | 9.09    | 2.10    | 23 %         | gross        | Inversor 1 - HUDN  | Comprador |
| Cesmag (n=4)    | 4.47    | 1.10    | 25 %         | gross        | Inverter 1 - Cesmag| Comprador |

Período: **2025-04-04 → 2025-12-16 · 6 144 h · 256 días** (horizonte sólido común sobre `MedicionesMTE_v3`).

Detalle completo de decisiones, verificación empírica del net metering en Udenar y trazabilidad con la auditoría: ver `Documentos/notas_modelo_tesis.md` § 3.1.

Auditorías regenerables:

```powershell
python scripts/data_quality_audit.py     # 27 fuentes raw
python scripts/audit_clean.py            # post-preprocesamiento
python scripts/plot_coverage_gantt.py    # graficas/data_coverage_gantt.png
```

---

## Parámetros clave

| Parámetro | Datos sintéticos | Datos reales MTE | Justificación |
|-----------|-----------------|-----------------|---------------|
| PGS (oficial NT2) | 1250 (adim.) | **~797 COP/kWh** (Udenar, HUDN) | Cedenar mensual oficial 2025-26 (CAL-8) |
| PGS (comercial NT2) | —            | **~956 COP/kWh** (Mariana, UCC, Cesmag) | Cedenar mensual comercial 2025-26 (CAL-8) |
| PGS comunitario ponderado | —     | **~906 COP/kWh** (promedio por demanda) | Drop-in escalar para análisis de sensibilidad |
| PGS legacy (deprecado, fallback) | — | 650 COP/kWh | Punto medio histórico Cedenar/ESSA pre-CAL-8 |
| PGB | 114 (adim.) | **280 COP/kWh** | Precio bolsa promedio XM |
| b_n | 194.76 (adim.) | **~225 COP/kWh** | LCOE solar Pasto, Fronius |

> **CAL-8** (`Documentos/notas_modelo_tesis.md` §CAL-8): la tarifa real
> Cedenar se carga desde `data/tarifas_cedenar_mensual.csv` y se propaga
> per-agente a los escenarios C1-C4. Los escenarios aceptan
> `pi_gs : float | np.ndarray (N,)` vía
> `scenarios._pi_gs.as_pi_gs_vector`. Cobertura del CSV: 13 meses
> (abr-2025 → abr-2026), respaldados por PDFs en `data/cedenar_pdfs/`.

---

## Archivos generados automáticamente

### Excel / CSV (en `outputs/`)

| Archivo | Contenido |
|---------|-----------|
| `resultados_comparacion.xlsx` | Resumen + por agente + P2P horario + métricas extra |
| `resultados_analisis.xlsx` | SA-1 (PGB) + SA-2 (PV) + FA-1 + FA-2 + IR individual |
| `resultados_gsa.xlsx` | GSA Sobol-Saltelli: S1, ST + S2 + Muestras_X (post `--gsa`) |
| `resultados_tests.xlsx` | Bootstrap + Wilcoxon (post `tests/statistical_tests.py`) |
| `p2p_breakdown.xlsx` | Desglose P2P hora a hora (flujos + resumen horario) |
| `p2p_breakdown_flujos.csv` | Flujos de transacción por par vendedor-comprador-hora |
| `p2p_breakdown_resumen_horario.csv` | Resumen horario: kWh, precio, SC, SS, IE |
| `sensitivity_2d_pgb_pv.parquet` | Sweep bivariado PGB×PV (post `scripts/sweep_pgb_pv.py`) |
| `daily_series_*.csv` | Series diarias B_P2P, B_C4 (entrada del bootstrap) |
| `bootstrap_42.json` | Resultados bootstrap detallados |
| `REPORTE_AVANCES.md` | Reporte automático para asesores (post `--full`) |

### Reproducibilidad MATLAB

Cada figura genera dos siblings junto al `.png`:
- `fig*.csv` (UTF-8 con BOM, headers en español, lectura directa con `readtable`)
- `fig*.mat` (scipy.io.savemat v5, struct con datos + metadata `activity_ref`/`units`/`fig_id`)

Validado: 16 archivos `.mat` y 44 archivos `.csv` se cargan sin error con `scipy.io.loadmat` y `pandas.read_csv`.

### Figuras (graficas/) — 21 figs principales con siblings .csv/.mat

| Figura | Contenido |
|--------|-----------|
| `fig1_perfiles.png` | Perfiles D y G por nodo |
| `fig2_clasificacion.png` | Vendedor/comprador por hora |
| `fig3_mercado_p2p.png` | Energía y precios de equilibrio |
| `fig4_metricas_horarias.png` | SC, SS, IE, bienestar por hora |
| `fig5_comparacion_regulatoria.png` | Comparación 5 escenarios |
| `fig6_ganancia_por_agente.png` | Ganancia por institución |
| `fig7_sensibilidad_pgb.png` | SA-1: P2P vs PGB |
| `fig8_sensibilidad_pv.png` | SA-2: P2P vs cobertura PV |
| `fig9_factibilidad.png` | FA-1 + FA-2 CREG 101 072 |
| `fig10_sensibilidad_ppa.png` | SA-PPA: sensibilidad precio bilateral |
| `fig11_sensibilidad_pgs.png` | SA-3: sensibilidad al precio regulado PGS al usuario |
| `fig12_comparacion_mensual.png` | Comparación mensual (solo --full) |
| `fig13_desglose_flujos.png` | Desglose flujos por componente (Act. 3.2) |
| `fig14_optimalidad_horaria.png` | Dominancia P2P vs C4 por hora (Act. 4.2) |
| `fig15_c1_vs_c4.png` | Comparación directa C1 vs C4 |
| `fig16_subperiod.png` | Sub-períodos SP1–SP4: laborable/fin-semana × jul./ene. (Act. 3.2) |
| `fig17_robustez_c4.png` | Robustez de C4 ante retiro de participantes (Act. 4.2) |
| **`fig18_heatmap_pgb_pv.png`** | Mapa bivariado PGB×cobertura PV (5 paneles: ganancia P2P/C4, RPE, IE, kWh) — requiere `scripts/sweep_pgb_pv.py` previo |
| **`fig19_desercion_individual.png`** | Curvas Δ_n(π_gb) por institución — racionalidad individual frente al mejor sustituto regulatorio |
| **`fig20_price_of_fairness.png`** | Price of Fairness formal (Bertsimas 2011): W_eff vs W_fair, ranking por agente y Gini |
| **`fig21_robustez_c4_agente.png`** | FA-3/FA-4 desagregado: regla 10% y límite 100 kW por institución |
| **`fig22_convergencia_h*.png`** | Convergencia RD+Stackelberg en horas diagnóstico: h0013 (caso marginal) y h0683 (alta energía con W_T negativo). Renombradas el 2026-04-27 desde fig11_convergencia (Act 1.1) |
| **`fig23_perfiles_diarios.png`** | Perfil diario promedio (5 instituciones + comunidad agregada). Complementa fig1 (serie horaria completa) con vista del patrón típico solar (Act 3.1) |

---

## Módulos implementados

- **Punto 2** — Precios XM reales integrados (`data/xm_prices.py`): usa CSV si existe, sino sintético calibrado
- **Punto 3** — SS/SC unificadas (`scenarios/comparison_engine.py`): misma definición para P2P y C1–C4 (autoconsumo + intercambio P2P)
- **Punto 4** — Parámetro b calibrado (`data/xm_prices.py`): LCOE solar Pasto 2025 ≈ 210-225 COP/kWh
- **Punto 5** — Sensibilidad SA-1/SA-2/SA-3/SA-PPA (`analysis/sensitivity.py`): barrido PGB, cobertura PV, precio al usuario, precio PPA
- **Punto 6** — Factibilidad FA-1/FA-2 + IR individual (`analysis/feasibility.py`): deserción horaria, racionalidad individual por agente, CREG 101 072
- **Activity 3.2** — Desglose de flujos por componente (`scenarios/comparison_engine.py` + `analysis/p2p_breakdown.py`)
- **Activity 4.2** — Optimalidad horaria P2P vs C4 + GDR (`analysis/optimality.py`)
- **Índice Gini** — distribución del beneficio por escenario (`core/settlement.py`)
- **Price of Fairness (PoF)** — Act 3.3: `analysis/fairness.py` implementa `compute_pof()` y `fairness_curve()` según Bertsimas, Farias & Trichakis (2011); integrado en `ComparisonResult` y exportado en hoja `PoF_Fairness` del Excel
- **Balance mensual C1** — permutación mensual real para horizonte --full (`scenarios/scenario_c1_creg174.py`)
- **Reporte mensual** — desglose mes a mes para horizonte --full (`analysis/monthly_report.py`)
- **DR program** — integrado (`core/dr_program.py`), inactivo con datos reales (alpha=0)
- **Optimización EMS** — `core/ems_p2p.py` usa LSODA adaptativo (stiff-aware, análogo a `ode15s` de `JoinFinal.m`) con `n_points=300`; speedup ~15× sobre RK45+500pts (961s → 64s en `--data real`). Guard NaN en `_run_hour_worker` descarta horas inestables (0.21% con `G_net` mínimo + VelGrad=1e6)

---

## Métricas de Nivel 2 (propuesta tesis)

| Métrica | Descripción | Rango |
|---------|-------------|-------|
| SC | Self-Consumption: fracción de D cubierta localmente | [0, 1] |
| SS | Self-Sufficiency: fracción de G usada en comunidad | [0, 1] |
| IE | Equity Index: distribución del beneficio entre roles | [-1, +1] |
| Gini | Índice de Gini por escenario (concentración del beneficio) | [0, 1] |
| RPE | Rendimiento Relativo de Equidad P2P vs C4: (W_P2P−W_C4)/|W_P2P| | (−∞, 1] |
| PoF | Price of Fairness [Bertsimas 2011]: (W_eff−W_fair)/W_eff; eficiente=max Σ B_n, equitativo=min Gini | [0, 1] |
| GDR | Global Dispatch Ratio: eficiencia de clearing del mercado | [0, 1] |
| PS / PSR | Fracción del excedente P2P capturada por compradores / vendedores | [0%, 100%] |

---

## Resultados del horizonte completo (6 144 h, MTE_v3)

Última corrida `--data real --full --analysis` (2026-04-28, 55.2 min, 256
días, abril–diciembre 2025) **con calibración Cedenar CAL-8 per-agente**
(`pi_gs[i]` mensual diferenciado por categoría tarifaria):

| Escenario | Ganancia neta (MCOP) | Observación |
|-----------|----------------------|-------------|
| C1 (CREG 174 créditos 1:1) | **54.04** | Mejor régimen regulado bajo créditos plenos (referencia) |
| **P2P (Stackelberg + RD)** | **52.43** | 1 031/6 144 h con mercado activo (16,8 %); 3 659,3 kWh transados |
| C2 (Bilateral PPA, π_ppa = 593) | 51.44 | Punto medio (π_gb + π̄_gs)/2 |
| C3 (spot XM) | 50.96 | |
| C4 (CREG 101 072 AGRC+PDE) | **50.29** | **Régimen vigente, baseline de comparación** |

**Métricas agregadas**: SC P2P = 0.188 · SS P2P = 0.981 · IE P2P = +0.3677 · **RPE P2P vs C4 = +0.0408** · PoF = 0.0000 (eficiente = equitativo = C1) · Spread C4 = 1 004,4 kWh.

**Ventaja P2P por institución frente a C4** (todas positivas, racionalidad individual cumplida):
- Udenar: **+548 973 COP** · Mariana: **+313 185 COP** · UCC: **+638 232 COP** · HUDN: **+271 069 COP** · Cesmag: **+369 330 COP** (Σ = +2,14 MCOP).

**Comparativa pre vs post CAL-8** (mismas series MTE, mismo horizonte;
sólo cambia la calibración de `pi_gs`):

| Escenario | Pre-CAL-8 (650 escalar) | Post-CAL-8 (vector per-agente) | Δ |
|---|---:|---:|---:|
| P2P | 37,78 MCOP | **52,43 MCOP** | +38,8 % |
| C1  | 39,56 MCOP | 54,04 MCOP | +36,6 % |
| C4  | 36,56 MCOP | 50,29 MCOP | +37,6 % |
| RPE (P2P vs C4) | +0,0321 | **+0,0408** | +27 % en magnitud |
| Σ ventaja P2P sobre C4 | 1,21 MCOP | **2,14 MCOP** | +77 % |
| IE P2P | +0,4063 | +0,3677 | −0,04 (vendedores capturan algo más) |

La jerarquía cualitativa **C1 ≥ P2P > C2 ≥ C3 > C4** se conserva. La activación de la heterogeneidad oficial/comercial **amplifica la prima de flexibilidad del P2P** sobre C4 en términos absolutos (Σ ventaja casi se duplica) sin invertir signos.

**Sub-períodos (Act. 3.2)**: P2P supera a C4 en los cuatro sub-períodos (Laborable/Finde × Jul/Ene) sin inversión de signo.

**Sensibilidad uni-paramétrica**: SA-1 PGB → RPE estrictamente positivo en `[200, 500]` COP/kWh. SA-2 factor PV → ventaja P2P-C4 con máximo no lineal alrededor del factor `4.4×` (cobertura ~50%).

**Sensibilidad bivariada (Act. 4.1, fig18)**: zona favorable al P2P localizada en cobertura intermedia (100-130%) y precio de bolsa bajo (~200 COP/kWh).

**Sensibilidad global Sobol-Saltelli (Act. 4.1, n_base = 128, ejecutado 2026-04-27, ~111 min)**:
- `factor_PV` domina en eficiencia: ST = 0.66 (ganancia), 0.82 (SC).
- `PGB` domina en equidad: ST = 0.99 (IE).
- 1 367/2 048 muestras válidas (66.7%); ST acotados en [0,1] tras eliminar artefactos del muestreo n=64 previo.
- Decisión 2026-04-27: `_fast_mode` deprecado por cuelgues en LSODA con samples patológicos (~58% del espacio Saltelli). El GSA opera en modo preciso con timeout-wrapper de 45 s por evaluación.

**Inferencia estadística (Act. 4.2, bootstrap n = 10 000, ejecutado 2026-04-27)**:
- $\bar{\Delta}$ (P2P − C4) = **4 732 COP/día**
- IC 95% (bootstrap por bloques, block_days = 7) = `[3 629, 5 751]` COP/día
- $p$-valor Wilcoxon < 0.001
- Cohen's $d$ = **0.90** (efecto grande)
- $n_\text{eff}$ = 36 bloques sobre 256 días MTE_v3

---

## Decisión metodológica: `_fast_mode` deprecado

El flag `_fast_mode` en `core/replicator_sellers.py` (commit `a5f2dc4`, introducido el 2026-04-26) reducía `VEL_GRAD` de 1e6 a 1e3 y relajaba tolerancias del solver ODE para acelerar el GSA ~10×. **Nunca completó un GSA exitosamente**: ~58% de los samples Saltelli disparan ciclos infinitos del Newton iterativo de LSODA, atascando los workers. El test `tests/test_fast_mode_equivalence.py` valida solo 8 horas representativas y por eso pasa verde, pero no cubre la distribución completa del muestreo Saltelli.

Tras la investigación del 2026-04-27 (utilidad de diagnóstico `scripts/probe_gsa_samples.py`), se desactivó `_fast_mode` en `analysis/global_sensitivity.py:_eval_sample` y se añadió un wrapper con timeout de 45 s en `_worker` como defensa adicional (samples patológicos se marcan NaN y se filtran del estimador Sobol). Trazabilidad completa en `Documentos/notas_modelo_tesis.md` §A.7.

---

## Estado de actividades (propuesta de tesis)

Las 10 actividades 1.0 → 4.2 están **completas y validadas con datos empíricos MTE_v3**. Trazabilidad detallada por actividad en `Documentos/Matriz_Trazabilidad.md`.

### Hitos completados

- [x] **Modelo base** consolidado y validado contra `JoinFinal.m` (Act 1.1)
- [x] **5 escenarios regulatorios** C1/C2/C3/C4 + P2P implementados (Act 2.1, 2.2)
- [x] **Datos empíricos MTE_v3** integrados — 6 144 h, 256 días, abril–diciembre 2025 (Act 3.1)
- [x] **Run horizonte completo** ~52 min, última corrida 2026-04-27 (Act 3.2)
- [x] **Descomposición de bienestar** + Price of Fairness formal (Bertsimas 2011) en `analysis/fairness.py` (Act 3.3)
- [x] **Sensibilidad uni-paramétrica** SA-1/2/3/PPA (Act 4.1)
- [x] **Sensibilidad global Sobol-Saltelli** n_base = 128, 1 367/2 048 válidas, ST publicables (Act 4.1)
- [x] **Sweep bivariado PGB×PV** + fig18 heatmap (Act 4.1)
- [x] **Análisis de subperíodos** SP1–SP4 laborable/finde × jul/ene (Act 3.2)
- [x] **Optimalidad P2P vs C4 hora a hora** + GDR (Act 4.2)
- [x] **Bootstrap** n = 10 000 sobre 256 días MTE_v3 → Cohen's d = 0.90 (Act 4.2)
- [x] **Reproducibilidad MATLAB** — `visualization/matlab_export.py` + 16 .mat + 44 .csv
- [x] **CAL-8: tarifa Cedenar mensual per-agente** (Fase 1 + Fase 2,
  2026-04-27). 13 PDFs (abr-2025 → abr-2026), 130 filas en CSV.
  Escenarios C1-C4 + `comparison_engine` + `monthly_report` +
  `p2p_breakdown` aceptan `pi_gs : float | ndarray (N,)`.
  Heterogeneidad oficial vs comercial capturada per-agente en todos
  los caminos de cálculo.

### Pendiente (no bloqueante)

- [ ] (diferido) GSA Sobol con `n_base ≥ 256` para IC más estrechos — solo si el comité lo solicita
- [ ] Verificar LCOE real de inversores instalados en cada institución MTE
- [ ] Confirmar autores de referencias `[22][24][26][27]` en `Documentos/references.bib`
- [ ] Manuscrito Capítulos 4 (resultados) y 5 (conclusiones) — vive en `Documentos/FinalTesis/` (otro repositorio)
