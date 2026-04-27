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
│   ├── base_case_data.py       ← parámetros + GRID_PARAMS (sintético) + GRID_PARAMS_REAL (COP)
│   ├── xm_data_loader.py       ← cargador CSV MTE (pandas 3.x compatible)
│   └── xm_prices.py            ← precios XM reales/sintéticos + calibración parámetro b
├── analysis/
│   ├── sensitivity.py          ← SA-1 (PGB) + SA-2 (PV) + SA-3 (π_gs) + SA-PPA + umbrales
│   ├── global_sensitivity.py   ← GSA Saltelli/Sobol (SALib, 7 params, 3 outputs, --gsa)
│   ├── feasibility.py          ← FA-1 (deserción horaria + IR individual) + FA-2 (CREG 101 072)
│   ├── p2p_breakdown.py        ← §3.12 Desglose P2P hora a hora → CSV + Excel
│   ├── monthly_report.py       ← Reporte mes a mes para horizonte completo (--full)
│   ├── subperiod.py            ← SP1–SP4: laborable/fin-semana × julio/enero (Act. 3.2)
│   └── optimality.py           ← Dominancia P2P vs C4 por hora, GDR (Act. 4.2)
├── visualization/
│   └── plots.py                ← 15 figuras automáticas
├── tests/
│   ├── validate_base_model.py
│   ├── calibration_study.py              ← estudio de calibración de parámetro b
│   ├── profile_stress_test.py            ← stress test perfiles extremos
│   ├── golden_test_sofia.py              ← golden test RD vs SLSQP (Bienestar6p.py)
│   ├── test_stackelberg_convergence.py   ← criterio de parada Stackelberg adaptativo
│   └── statistical_tests.py             ← bootstrap bloques Kunsch + Wilcoxon P2P vs C4
└── diagnostico_datos.py
```

---

## Comandos de ejecución

```powershell
# Modo 1 — Validación sintética (24h, ~35s)
python main_simulation.py

# Modo 2 — Perfil diario promedio MTE (24h, ~1 min con LSODA adaptativo)
python main_simulation.py --data real

# Modo 3 — Perfil diario + sensibilidad y factibilidad (~5 min)
python main_simulation.py --data real --analysis

# Modo 4 — Horizonte completo 5160h / 215 días (~45 min)
python main_simulation.py --data real --full

# Modo 5 — Horizonte completo + todos los análisis (~100 min, corrida definitiva)
python main_simulation.py --data real --full --analysis

# Con rutas explícitas
$env:MTE_ROOT="C:\ruta\a\MedicionesMTE"
$env:XM_PRICES_CSV="C:\ruta\precios_bolsa_xm.csv"   # opcional
python main_simulation.py --data real --analysis

# Modo 6 — Análisis de sensibilidad global Saltelli (GSA, ~75 min con 8 workers)
python main_simulation.py --gsa --n-base 64

# GSA smoke test ultrarrápido (verificación ~5 min)
python main_simulation.py --gsa --n-base 4

# Tests estadísticos bootstrap (requiere outputs/daily_series_*.csv del run --full)
python tests/statistical_tests.py --n-bootstrap 1000 --block-days 7
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
python outputs/data_quality_audit.py     # 27 fuentes raw
python outputs/audit_clean.py            # post-preprocesamiento
python outputs/plot_coverage_gantt.py    # graficas/data_coverage_gantt.png
```

---

## Parámetros clave

| Parámetro | Datos sintéticos | Datos reales MTE | Justificación |
|-----------|-----------------|-----------------|---------------|
| PGS | 1250 (adim.) | **650 COP/kWh** | Tarifa usuario regulada |
| PGB | 114 (adim.) | **280 COP/kWh** | Precio bolsa promedio XM |
| b_n | 194.76 (adim.) | **~225 COP/kWh** | LCOE solar Pasto, Fronius |

---

## Archivos generados automáticamente

### Excel / CSV

| Archivo | Contenido |
|---------|-----------|
| `resultados_comparacion.xlsx` | Resumen + por agente + P2P horario + métricas extra |
| `resultados_analisis.xlsx` | SA-1 (PGB) + SA-2 (PV) + FA-1 + FA-2 + IR individual |
| `p2p_breakdown.xlsx` | Desglose P2P hora a hora (flujos + resumen horario) |
| `p2p_breakdown_flujos.csv` | Flujos de transacción por par vendedor-comprador-hora |
| `p2p_breakdown_resumen_horario.csv` | Resumen horario: kWh, precio, SC, SS, IE |

### Figuras (graficas/)

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
| `fig11_convergencia_h*.png` | Convergencia RD+Stackelberg (horas diagnóstico: h0012, h0014, h0015, h0019, h3683) |
| `fig11_sensibilidad_pgs.png` | SA-3: sensibilidad al precio regulado PGS (conflicto de numeración con fig11 de convergencia) |
| `fig12_comparacion_mensual.png` | Comparación mensual (solo --full) |
| `fig13_desglose_flujos.png` | Desglose flujos por componente (Act. 3.2) |
| `fig14_optimalidad_horaria.png` | Dominancia P2P vs C4 por hora (Act. 4.2) |
| `fig15_c1_vs_c4.png` | Comparación directa C1 vs C4 |
| `fig16_subperiod.png` | Sub-períodos SP1–SP4: laborable/fin-semana × jul./ene. (Act. 3.2) |
| `fig17_robustez_c4.png` | Robustez de C4 ante variación de participantes (Act. 4.2) |

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

## Resultados del horizonte completo (5160 h)

Primera corrida limpia `--data real --full --analysis` (commit `83d4815`, ~100 min, 215 días, jul. 2025–ene. 2026):

| Escenario | Ganancia neta (MCOP) | Observación |
|-----------|----------------------|-------------|
| P2P       | **28.12** | 1387/5160 h con mercado activo (26.9%); 16 870 kWh transados |
| C1 (CREG 174 créditos 1:1) | 35.56 | Mejor régimen regulado cuando hay días con excedente puntual |
| C3 (spot XM) | 25.95 | Divergencia confirmada vs C1 con precios horarios reales |
| C4 (CREG 101 072 AGPE+PDE) | 22.26 | Régimen vigente, baseline de comparación |

**Métricas agregadas**: IE P2P = +0.5038 · Gini P2P = 0.1716 · **RPE P2P vs C4 = +0.2084**.

**Subperiodos (Act. 3.2)**: RPE entre +0.2202 y +0.2722 (Laborable/Fin-semana × Jul./Ene.), sin inversión de signo.

**Sensibilidad horizonte completo**: SA-1 PGB → RPE de +0.2447 a +0.0881 (siempre positivo). SA-2 factor PV → ventaja P2P-C4 no monótona, máximo en factor 4.44×.

**Inferencia estadística (Act. 4.1)**: bootstrap diario de bloques (215 días, n=1000) → **p < 0.001**, Cohen d = 0.67 para P2P vs C4.

---

## Divergencia C1 vs C3 confirmada en `--full`

Con el perfil diario promedio (cobertura PV = 11%, G < D en el 100% de las horas), C1 y C3 producían ganancia neta idéntica. La predicción del README anterior —que divergirían con precios XM horarios reales sobre las 5160 h— quedó confirmada: **C1 = 35.56 MCOP** vs **C3 = 25.95 MCOP** (brecha ≈ 9.6 MCOP, 37%). Los días de baja demanda generan excedente puntual que C1 acredita 1:1 mientras C3 lo liquida al precio horario XM.

---

## Pendiente

- [x] ~~Run horizonte completo 5 160 h~~ → **6 144 h** con MedicionesMTE_v3 (commit `cdb11e9`, ~56 min, exit 0)
- [x] ~~Bootstrap con datos reales~~ → p<0.001, Cohen d = 0.67
- [x] ~~Price of Fairness (PoF)~~ → `analysis/fairness.py` (commit `36084b4`, Act 3.3)
- [x] ~~GSA Sobol n_base 64~~ → ejecutado 2026-04-17 sobre el modelo de referencia (Chacón et al., 24h sintético escalado por `factor_PV`/`factor_D`). Cobertura de "datos históricos" de la propuesta §VI.D vía SA-1/2/3/PPA + subperíodos sobre MTE_v3 (ortogonalidad metodológica documentada en `Documentos/notas_modelo_tesis.md` §A.7)
- [ ] (diferido) GSA Sobol con `n_base ≥ 256` para IC publicables — solo si el comité lo solicita; infraestructura `_fast_mode` lista (commit `19e57cb`)
- [ ] Verificar LCOE real de inversores instalados en cada institución MTE
- [ ] Confirmar autores referencias [22][24][26][27] en `Documentos/references.bib`
