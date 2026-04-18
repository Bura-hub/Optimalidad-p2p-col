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

# Modo 2 — Perfil diario promedio MTE (24h, ~2 min)
python main_simulation.py --data real

# Modo 3 — Perfil diario + sensibilidad y factibilidad (~15 min)
python main_simulation.py --data real --analysis

# Modo 4 — Horizonte completo 5160h / 215 días (~20 min)
python main_simulation.py --data real --full

# Modo 5 — Horizonte completo + todos los análisis
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


| Institución | D̄ (kW) | Ḡ (kW) | Cobertura PV | Rol |
|-------------|---------|---------|-------------|-----|
| Udenar (n=0)| 7.5 | 3.9 | 52% | **Vendedor** (único) |
| Mariana (n=1)| 13.8 | 1.8 | 13% | Comprador |
| UCC (n=2) | 42.1 | 2.2 | 5% | Comprador |
| HUDN (n=3) | 21.7 | 1.7 | 8% | Comprador |
| Cesmag (n=4)| 9.0 | 1.0 | 11% | Comprador |

Período: 2025-07-01 → 2026-01-31 · 5160h · 215 días

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
| `fig11_convergencia_h*.png` | Convergencia RD+Stackelberg (por hora) |
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
- **Balance mensual C1** — permutación mensual real para horizonte --full (`scenarios/scenario_c1_creg174.py`)
- **Reporte mensual** — desglose mes a mes para horizonte --full (`analysis/monthly_report.py`)
- **DR program** — integrado (`core/dr_program.py`), inactivo con datos reales (alpha=0)

---

## Métricas de Nivel 2 (propuesta tesis)

| Métrica | Descripción | Rango |
|---------|-------------|-------|
| SC | Self-Consumption: fracción de D cubierta localmente | [0, 1] |
| SS | Self-Sufficiency: fracción de G usada en comunidad | [0, 1] |
| IE | Equity Index: distribución del beneficio entre roles | [-1, +1] |
| Gini | Índice de Gini por escenario (concentración del beneficio) | [0, 1] |
| RPE | Rendimiento Relativo de Equidad P2P vs C4: (W_P2P−W_C4)/|W_P2P|; RPE ≠ PoF Bertsimas (2011) | (−∞, 1] |
| GDR | Global Dispatch Ratio: eficiencia de clearing del mercado | [0, 1] |
| PS / PSR | Fracción del excedente P2P capturada por compradores / vendedores | [0%, 100%] |

---

## Hallazgo C1 = C3 (perfil promedio)

Con la comunidad MTE, G < D en el 100% de horas del perfil promedio (cobertura PV = 11%). Sin excedente individual, vender a bolsa (C3) y tener créditos 1:1 (C1) producen idéntica ganancia neta. Los dos escenarios divergirán en el análisis `--full` con precios XM horarios reales, cuando días de baja demanda (fines de semana) puedan generar excedente puntual.

---

## Pendiente

- [ ] Run horizonte completo 5 160 h: `python main_simulation.py --data real --full --analysis`
- [ ] GSA Sobol n_base ≥ 64 (solicitar OK): `python main_simulation.py --gsa --n-base 64`
- [ ] Descargar serie horaria XM jul. 2025–ene. 2026 → `data/xm_precios_bolsa.csv`
- [ ] Bootstrap con datos reales: `python tests/statistical_tests.py` (requiere run --full)
- [ ] Verificar LCOE real de inversores instalados en cada institución MTE
- [ ] Confirmar autores referencias [22][24][26][27] en `Documentos/references.bib`
