# Reporte de Avances — Tesis P2P Colombia

**Autor:** Brayan S. Lopez-Mendez | **Fecha:** 2026-04-13
**Asesores:** Andrés Pantoja · Germán Obando | **Udenar, 2026**

---

## 1. Estado del modelo

| Parámetro | Valor |
|-----------|-------|
| Datos | Empíricos MTE — perfil diario promedio (24h) |
| Agentes | 5 instituciones Pasto (MTE) |
| Horizonte | 24h (1 días) |
| Horas con mercado P2P | 7/24 (29.2%) |
| Energía P2P total | 54.6 kWh/período |
| Precios | PGS=650.0 · PGB=280.0 COP/kWh |

## 2. Datos empíricos MTE

| Institución | D̄ (kW) | Ḡ (kW) | Cobertura PV |
|-------------|---------|---------|-------------|
| Udenar | 7.5 | 3.9 | 52% |
| Mariana | 13.8 | 1.8 | 13% |
| UCC | 42.1 | 2.2 | 5% |
| HUDN | 21.7 | 1.7 | 8% |
| Cesmag | 9.0 | 1.0 | 11% |
| **Comunidad** | **94.1** | **10.6** | **11.3%** |

## 3. Resultados comparación regulatoria

| Escenario | Ganancia neta (COP) | SC | SS | IE |
|-----------|--------------------------|-----|-----|-----|
| P2P (Stackelberg + RD) | 150,118 | 0.113 | 1.000 | 0.1510 |
| C1 CREG 174/2021 | 165,410 | 0.088 | 0.785 | -0.2628 |
| C2 Bilateral PPA | 145,203 | 0.088 | 0.785 | -0.1602 |
| C3 Mercado spot | 135,621 | 0.088 | 0.785 | -0.1009 |
| C4 CREG 101 072 ★ | 129,911 | 0.088 | 0.785 | -0.0614 |

**Price of Fairness (P2P vs C4):** 0.1346
**Spread ineficiencia estática C4:** 20.341 kWh/período

### 3.1 Ventaja P2P vs C4 por institución

| Institución | P2P (COP) | C4 (COP) | Ventaja P2P (COP) |
|-------------|---------|---------|-----------------|
| Udenar | 34,244 | 26,108 | +8,136 ✓ P2P mejor |
| Mariana | 32,297 | 27,555 | +4,742 ✓ P2P mejor |
| UCC | 34,679 | 34,679 | +0 ✓ P2P mejor |
| HUDN | 29,463 | 26,291 | +3,172 ✓ P2P mejor |
| Cesmag | 19,435 | 15,278 | +4,157 ✓ P2P mejor |

### 3.2 Nota sobre C1 = C3

Con el perfil diario promedio de datos MTE, C1 (CREG 174) y C3 (Mercado spot)
producen resultados idénticos. Esto es **correcto matemáticamente**: cuando la
cobertura PV es 11% y G < D en el 100% de las horas, ningún nodo tiene excedente
para vender a bolsa, por lo que el mecanismo de liquidación es irrelevante.
La diferencia entre C1 y C3 aparecerá con precios de bolsa XM horarios reales
y en días con baja demanda institucional (fines de semana, festivos).

## 4. Métricas del mercado P2P

| Métrica | Valor | Interpretación |
|---------|-------|----------------|
| SC (P2P) | 0.113 | Fracción demanda cubierta internamente |
| SS (P2P) | 1.000 | Fracción generación usada en comunidad |
| IE (P2P) | 0.1510 | Distribución beneficio (0=equitativo) |
| IE (C4)  | -0.0614 | Referencia regulatoria vigente |
| PoF      | 0.1346 | Pérdida eficiencia por equidad P2P vs C4 |

## 5. Análisis de sensibilidad

### SA-1: Variación precio de bolsa PGB

| PGB (COP/kWh) | P2P (COP) | C4 (COP) | IE P2P | PoF |
|---------------|---------|---------|--------|-----|
| 200 | 154,487 | 129,911 | 0.151 | 0.159 |
| 250 | 151,756 | 129,911 | 0.151 | 0.144 |
| 280 | 150,118 | 129,911 | 0.151 | 0.135 |
| 300 | 149,025 | 129,911 | 0.151 | 0.128 |
| 350 | 146,295 | 129,911 | 0.151 | 0.112 |
| 400 | 143,564 | 129,911 | 0.151 | 0.095 |
| 450 | 140,833 | 129,911 | 0.151 | 0.078 |
| 500 | 138,103 | 129,911 | 0.151 | 0.059 |

### SA-2: Variación cobertura PV

| Factor PV | Cobertura (%) | P2P (COP) | C4 (COP) | Horas mercado | kWh P2P |
|-----------|--------------|---------|---------|--------------|---------|
| 1.00x | 11% | 150,118 | 129,911 | 7 | 54.6 |
| 1.78x | 20% | 259,892 | 215,334 | 9 | 120.4 |
| 2.93x | 33% | 402,744 | 350,317 | 10 | 223.8 |
| 4.44x | 50% | 505,781 | 566,074 | 10 | 245.3 |
| 6.66x | 75% | 594,954 | 812,629 | 9 | 195.2 |
| 8.88x | 100% | 647,717 | 989,478 | 8 | 136.9 |

## 6. Análisis de factibilidad

### FA-1: Condición de deserción del P2P

- Precio P2P nunca menor que bolsa: **Sí**
- Umbral crítico precio bolsa: **476 COP/kWh**

### FA-2: Cumplimiento CREG 101 072/2025

| Institución | Participación (%) | Cumple 10% | Cap. max (kW) | Cumple 100kW |
|-------------|------------------|-----------|--------------|-------------|
| Udenar | 4.20% | ✓ | 12.7 | ✓ |
| Mariana | 1.88% | ✓ | 5.8 | ✓ |
| UCC | 2.36% | ✓ | 7.0 | ✓ |
| HUDN | 1.79% | ✓ | 5.6 | ✓ |
| Cesmag | 1.04% | ✓ | 2.9 | ✓ |

**Score de robustez C4:** 1.00 (1=máxima robustez)

### FA-1b: Deserción — Condición de Racionalidad Individual (§3.14)

**Definición formal (Restricción IR):**
Agente n permanece en P2P sii `B_n^P2P(π) ≥ max(B_n^C1, B_n^C4)(π)`

Donde `Δ_n = B_n^P2P − max(B_n^C1, B_n^C4)` (>0 → agente prefiere P2P). 
Umbral crítico `π_gb^*_n`: precio de bolsa donde el agente es indiferente.

| Agente | B_P2P (COP) | B_alt (COP) | Δ_n (COP) | Δ_n/B_alt | π_gb^*_n | Estado |
|--------|---------|---------|---------|----------|---------|--------|
| Udenar | 34,244 | 61,607 | -27,363 | -44.4% | 180 | en riesgo |
| Mariana | 32,297 | 27,555 | +4,742 | +17.2% | >rango | estable |
| UCC | 34,679 | 34,679 | +0 | +0.0% | >rango | estable |
| HUDN | 29,463 | 26,291 | +3,172 | +12.1% | >rango | estable |
| Cesmag | 19,435 | 15,278 | +4,157 | +27.2% | >rango | estable |

**Agentes estables (4/5):** Mariana, UCC, HUDN, Cesmag
**Umbral comunitario (mediana individual):** >rango (>500.0) COP/kWh
**Umbral agregado P2P < max(C1,C4):** >rango (>500.0) COP/kWh

**Tabla Δ_n(pi_gb) — sensibilidad a precio de bolsa:**

| pi_gb | Udenar | Mariana | UCC | HUDN | Cesmag | Σ Δ |
|-------|--------|--------|--------|--------|--------|--------|
| 200 | -22,994 | +4,742 | +0 | +3,172 | +4,157 | -10,923 |
| 250 | -25,725 | +4,742 | +0 | +3,172 | +4,157 | -13,654 |
| 280 | -27,363 | +4,742 | +0 | +3,172 | +4,157 | -15,292 |
| 300 | -28,456 | +4,742 | +0 | +3,172 | +4,157 | -16,384 |
| 350 | -31,186 | +4,742 | +0 | +3,172 | +4,157 | -19,115 |
| 400 | -33,917 | +4,742 | +0 | +3,172 | +4,157 | -21,846 |
| 450 | -36,648 | +4,742 | +0 | +3,172 | +4,157 | -24,576 |
| 500 | -39,378 | +4,742 | +0 | +3,172 | +4,157 | -27,307 |

---

## 7. Pendiente

- [ ] Correr horizonte completo 5160h: `python main_simulation.py --data real --full --analysis`
- [x] Serie horaria XM Jul 2025-Ene 2026 disponible en `data/precios_bolsa_xm_api.csv` (5 160 h, descargada vía API pydataxm)
- [ ] Verificar LCOE real de inversores instalados en cada institución
- [ ] Análisis sub-período: laborables vs fines de semana, julio vs enero

## 8. Estructura del repositorio

```
SistemaBL/
├── main_simulation.py          # Orquestador principal (4 modos)
├── core/                       # EMS P2P: Stackelberg + RD
│   ├── ems_p2p.py
│   ├── replicator_sellers.py
│   ├── replicator_buyers.py
│   ├── settlement.py
│   ├── market_prep.py
│   └── dr_program.py
├── scenarios/                  # 4 escenarios regulatorios + motor
│   ├── comparison_engine.py
│   ├── scenario_c1_creg174.py
│   ├── scenario_c2_bilateral.py
│   ├── scenario_c3_spot.py
│   └── scenario_c4_creg101072.py
├── analysis/                   # Sensibilidad, factibilidad, optimalidad
│   ├── sensitivity.py
│   ├── feasibility.py
│   ├── p2p_breakdown.py
│   ├── optimality.py
│   ├── monthly_report.py
│   └── subperiod.py
├── data/                       # Parámetros base y precios XM
│   ├── base_case_data.py
│   ├── xm_prices.py
│   ├── xm_data_loader.py
│   └── precios_bolsa_xm_api.csv   # 5 160h Jul 2025–Ene 2026
├── visualization/
│   └── plots.py                # 17 figuras automáticas
├── graficas/                   # Figuras generadas (PNG)
├── resultados_comparacion.xlsx # Resultados 5 escenarios
├── resultados_analisis.xlsx    # SA-1/2/3, FA-1/2, IR individual
└── p2p_breakdown.xlsx          # Desglose flujos P2P hora a hora
```

**Ejecutar simulación:**
```bash
# Perfil diario promedio (rápido, ~2 min)
python main_simulation.py --data real --analysis

# Horizonte completo 5 160h (requiere MedicionesMTE/)
python main_simulation.py --data real --full --analysis
```

---
*Generado automáticamente por main_simulation.py · 2026-04-12 23:53*