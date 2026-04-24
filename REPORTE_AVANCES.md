# Reporte de Avances — Tesis P2P Colombia

**Autor:** Brayan S. Lopez-Mendez | **Fecha:** 2026-04-23 19:21
**Asesores:** Andrés Pantoja · Germán Obando | **Udenar, 2026**

---

## 1. Estado del modelo

| Parámetro | Valor |
|-----------|-------|
| Datos | Empíricos MTE — 5160h completas |
| Agentes | 5 instituciones Pasto (MTE) |
| Horizonte | 5160h (215 días) |
| Horas con mercado P2P | 1387/5160 (26.9%) |
| Energía P2P total | 16869.8 kWh/período |
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
| P2P (Stackelberg + RD) | 28,120,523 | 0.104 | 0.924 | 0.5038 |
| C1 CREG 174/2021 | 35,563,088 | 0.069 | 0.615 | -0.2628 |
| C2 Bilateral PPA | 27,773,510 | 0.069 | 0.615 | -0.1036 |
| C3 Mercado spot | 25,946,467 | 0.069 | 0.615 | -0.0465 |
| C4 CREG 101 072 ★ | 22,259,344 | 0.069 | 0.615 | 0.0918 |

**RPE (P2P vs C4):** 0.2084
**Spread ineficiencia estática C4:** 6732.007 kWh/período

### 3.1 Ventaja P2P vs C4 por institución

| Institución | P2P (COP) | C4 (COP) | Ventaja P2P (COP) |
|-------------|---------|---------|-----------------|
| Udenar | 3,800,803 | 2,613,250 | +1,187,553 ✓ P2P mejor |
| Mariana | 5,250,423 | 4,535,551 | +714,872 ✓ P2P mejor |
| UCC | 8,331,716 | 6,624,661 | +1,707,055 ✓ P2P mejor |
| HUDN | 6,870,693 | 5,526,201 | +1,344,491 ✓ P2P mejor |
| Cesmag | 3,866,888 | 2,959,680 | +907,209 ✓ P2P mejor |

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
| SC (P2P) | 0.104 | Fracción demanda cubierta internamente |
| SS (P2P) | 0.924 | Fracción generación usada en comunidad |
| IE (P2P) | 0.5038 | Distribución beneficio (0=equitativo) |
| IE (C4)  | 0.0918 | Referencia regulatoria vigente |
| RPE      | 0.2084 | Rendimiento relativo P2P vs C4 (RPE ≠ PoF Bertsimas 2011) |

## 5. Análisis de sensibilidad

### SA-1: Variación precio de bolsa PGB

| PGB (COP/kWh) | P2P (COP) | C4 (COP) | IE P2P | RPE |
|---------------|---------|---------|--------|-----|
| 200 | 29,470,108 | 22,259,344 | 0.504 | 0.245 |
| 250 | 28,626,617 | 22,259,344 | 0.504 | 0.222 |
| 280 | 28,120,523 | 22,259,344 | 0.504 | 0.208 |
| 300 | 27,783,127 | 22,259,344 | 0.504 | 0.199 |
| 350 | 26,939,636 | 22,259,344 | 0.504 | 0.174 |
| 400 | 26,096,146 | 22,259,344 | 0.504 | 0.147 |
| 450 | 25,252,655 | 22,259,344 | 0.504 | 0.119 |
| 500 | 24,409,165 | 22,259,344 | 0.504 | 0.088 |

### SA-2: Variación cobertura PV

| Factor PV | Cobertura (%) | P2P (COP) | C4 (COP) | Horas mercado | kWh P2P |
|-----------|--------------|---------|---------|--------------|---------|
| 1.00x | 11% | 28,120,523 | 22,259,344 | 1387 | 16869.8 |
| 1.78x | 20% | 45,870,181 | 37,288,152 | 1491 | 26828.8 |
| 2.93x | 33% | 66,899,116 | 56,020,876 | 1545 | 36530.2 |
| 4.44x | 50% | 87,210,054 | 75,513,532 | 1495 | 43507.1 |
| 6.66x | 75% | 106,819,515 | 96,920,588 | 1378 | 45018.2 |
| 8.88x | 100% | 119,904,386 | 112,142,866 | 1251 | 42987.1 |

## 6. Análisis de factibilidad

### FA-1: Condición de deserción del P2P

- Precio P2P nunca menor que bolsa: **No**
- Umbral crítico precio bolsa: **363 COP/kWh**

### FA-2: Cumplimiento CREG 101 072/2025

| Institución | Participación (%) | Cumple 10% | Cap. max (kW) | Cumple 100kW |
|-------------|------------------|-----------|--------------|-------------|
| Udenar | 4.20% | ✓ | 32.2 | ✓ |
| Mariana | 1.88% | ✓ | 14.6 | ✓ |
| UCC | 2.36% | ✓ | 15.1 | ✓ |
| HUDN | 1.79% | ✓ | 13.8 | ✓ |
| Cesmag | 1.04% | ✓ | 8.1 | ✓ |

**Score de robustez C4:** 1.00 (1=máxima robustez)

### FA-1b: Deserción — Condición de Racionalidad Individual (§3.14)

**Definición formal (Restricción IR):**
Agente n permanece en P2P sii `B_n^P2P(π) ≥ max(B_n^C1, B_n^C4)(π)`

Donde `Δ_n = B_n^P2P − max(B_n^C1, B_n^C4)` (>0 → agente prefiere P2P). 
Umbral crítico `π_gb^*_n`: precio de bolsa donde el agente es indiferente.

| Agente | B_P2P (COP) | B_alt (COP) | Δ_n (COP) | Δ_n/B_alt | π_gb^*_n | Estado |
|--------|---------|---------|---------|----------|---------|--------|
| Udenar | 3,800,803 | 13,245,552 | -9,444,749 | -71.3% | 180 | en riesgo |
| Mariana | 5,250,423 | 5,924,324 | -673,902 | -11.4% | 180 | en riesgo |
| UCC | 8,331,716 | 7,455,886 | +875,830 | +11.7% | >rango | estable |
| HUDN | 6,870,693 | 5,652,570 | +1,218,123 | +21.5% | >rango | estable |
| Cesmag | 3,866,888 | 3,284,757 | +582,132 | +17.7% | >rango | estable |

**Agentes estables (3/5):** UCC, HUDN, Cesmag
**Umbral comunitario (mediana individual):** >rango (>500.0) COP/kWh
**Umbral agregado P2P < max(C1,C4):** >rango (>500.0) COP/kWh

**Tabla Δ_n(pi_gb) — sensibilidad a precio de bolsa:**

| pi_gb | Udenar | Mariana | UCC | HUDN | Cesmag | Σ Δ |
|-------|--------|--------|--------|--------|--------|--------|
| 200 | -8,350,761 | -537,660 | +917,393 | +1,243,027 | +635,020 | -6,092,980 |
| 250 | -9,034,503 | -622,811 | +891,417 | +1,227,462 | +601,965 | -6,936,471 |
| 280 | -9,444,749 | -673,902 | +875,830 | +1,218,123 | +582,132 | -7,442,565 |
| 300 | -9,718,246 | -707,962 | +865,440 | +1,211,897 | +568,910 | -7,779,961 |
| 350 | -10,401,988 | -793,113 | +839,463 | +1,196,332 | +535,854 | -8,623,452 |
| 400 | -11,085,730 | -878,264 | +813,486 | +1,180,767 | +502,799 | -9,466,942 |
| 450 | -11,769,473 | -963,415 | +787,509 | +1,165,202 | +469,744 | -10,310,433 |
| 500 | -12,453,215 | -1,048,566 | +761,532 | +1,149,637 | +436,688 | -11,153,923 |

---

## 7. Pendiente

- [ ] Correr horizonte completo 5160h: `python main_simulation.py --data real --full --analysis`
- [ ] Descargar serie horaria XM Jul 2025-Ene 2026 → `data/xm_precios_bolsa.csv`
- [ ] Verificar LCOE real de inversores instalados en cada institución
- [ ] Análisis sub-período: laborables vs fines de semana, julio vs enero

---
*Generado automáticamente por main_simulation.py · 2026-04-23 19:21*