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
│   └── settlement.py           ← liquidación + métricas SS/SC unificadas (v3)
├── scenarios/
│   ├── scenario_c1_creg174.py       ← CREG 174/2021 créditos 1:1
│   ├── scenario_c2_bilateral.py     ← Bilateral PPA
│   ├── scenario_c3_spot.py          ← Mercado spot precio bolsa
│   ├── scenario_c4_creg101072.py    ← AGRC + PDE (escenario vigente)
│   └── comparison_engine.py         ← 5 escenarios, métricas Nivel 1 y 2
├── data/
│   ├── base_case_data.py       ← parámetros + GRID_PARAMS (sintético) + GRID_PARAMS_REAL (COP)
│   ├── xm_data_loader.py       ← cargador CSV MTE (pandas 3.x compatible)
│   └── xm_prices.py            ← precios XM reales/sintéticos + calibración parámetro b
├── analysis/
│   ├── sensitivity.py          ← SA-1 (PGB 200-500) + SA-2 (cobertura PV 11-100%)
│   └── feasibility.py          ← FA-1 (deserción) + FA-2 (CREG 101 072)
├── visualization/
│   └── plots.py                ← 8 figuras automáticas (P2P + sensibilidad)
├── tests/
│   └── validate_base_model.py
└── diagnostico_datos.py
```

---

## Comandos de ejecución

```powershell
# Modo 1 — Validación sintética (24h, ~35s)
python main_simulation.py

# Modo 2 — Perfil diario promedio MTE (24h, ~2 min)
python main_simulation.py --data real

# Modo 3 — Sensibilidad + factibilidad MTE (Objetivo 4, ~15 min)
python main_simulation.py --data real --analysis

# Modo 4 — Horizonte completo 5160h / 215 días (~20 min) [AL FINAL]
python main_simulation.py --data real --full

# Con rutas explícitas
$env:MTE_ROOT="C:\ruta\a\MedicionesMTE"
$env:XM_PRICES_CSV="C:\ruta\precios_bolsa_xm.csv"   # opcional
python main_simulation.py --data real --analysis
```

---

## Datos empíricos MTE — Instituciones

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

## Resultados — Perfil diario promedio

```
P2P (Stackelberg + RD)    $ -307,653   SC=0.083  SS=0.248  IE=-0.182
C1  CREG 174/2021         $-2,317,311  SC=0.088  SS=0.785  IE=+1.000
C2  Bilateral PPA         $  +256,054  SC=0.088  SS=0.785  IE=-1.000
C3  Mercado spot          $-2,317,311  SC=0.088  SS=0.785  IE=+1.000
C4  CREG 101 072 (AGRC)   $-2,323,537  SC=0.088  SS=0.785  IE=+1.000

P2P supera a C4 en los 5 nodos.
C1=C3: correcto — G < D en todas las horas con perfil promedio.
IE_P2P≈0: único mecanismo con distribución equitativa del beneficio.
```

---

## Archivos generados automáticamente

| Archivo | Contenido |
|---------|-----------|
| `resultados_comparacion.xlsx` | Resumen + por agente + P2P horario |
| `resultados_sensibilidad.xlsx` | SA-1 (PGB) + SA-2 (PV) + hallazgos |
| `resultados_factibilidad.xlsx` | FA-1 (deserción) + FA-2 (CREG) |
| `graficas/fig1_perfiles.png` | Perfiles D y G por nodo |
| `graficas/fig2_clasificacion.png` | Vendedor/comprador por hora |
| `graficas/fig3_mercado_p2p.png` | Energía y precios de equilibrio |
| `graficas/fig4_metricas_horarias.png` | SC, SS, IE, bienestar por hora |
| `graficas/fig5_comparacion_regulatoria.png` | Comparación 5 escenarios |
| `graficas/fig6_ganancia_por_agente.png` | Ganancia por institución |
| `graficas/fig7_sensibilidad_pgb.png` | SA-1: P2P vs PGB |
| `graficas/fig8_sensibilidad_pv.png` | SA-2: P2P vs cobertura |

---

## Módulos implementados (últimas versiones)

- **Punto 2** — Precios XM reales integrados (`data/xm_prices.py`): usa CSV si existe, sino sintético calibrado
- **Punto 3** — SS unificada (`scenarios/comparison_engine.py`): SS = (autoconsumo + P2P) / G_total
- **Punto 4** — Parámetro b calibrado (`data/xm_prices.py`): LCOE solar Pasto 2025 ≈ 210-225 COP/kWh
- **Punto 5** — Sensibilidad SA-1/SA-2 (`analysis/sensitivity.py`): barrido PGB y cobertura PV
- **Punto 6** — Factibilidad FA-1/FA-2 (`analysis/feasibility.py`): deserción y CREG 101 072

---

## Hallazgo C1 = C3 (perfil promedio)

Con la comunidad MTE, G < D en el 100% de horas del perfil promedio (cobertura PV = 11%). Sin excedente individual, vender a bolsa (C3) y tener créditos 1:1 (C1) producen idéntica ganancia neta. Los dos escenarios divergirán en el análisis --full con precios XM horarios reales, cuando días de baja demanda (fines de semana) puedan generar excedente puntual. Este es un hallazgo correcto y documentado.
