# Reporte de Avances — Tesis P2P Colombia

**Autor:** Brayan S. Lopez-Mendez | **Fecha:** 2026-04-12 01:31
**Asesores:** Andrés Pantoja · Germán Obando | **Udenar, 2026**

---

## 1. Estado del modelo

| Parámetro | Valor |
|-----------|-------|
| Datos | Sintéticos (validación) |
| Agentes | 6 instituciones Pasto (MTE) |
| Horizonte | 24h (1 días) |
| Horas con mercado P2P | 24/24 (100.0%) |
| Energía P2P total | 36.6 kWh/período |
| Precios | PGS=1250.0 · PGB=114.0 $/kWh |

## 2. Datos empíricos MTE

| Institución | D̄ (kW) | Ḡ (kW) | Cobertura PV |
|-------------|---------|---------|-------------|
| A1 | 2.3 | 2.8 | 121% |
| A2 | 0.7 | 1.3 | 191% |
| A3 | 0.5 | 0.6 | 129% |
| A4 | 1.8 | 1.1 | 63% |
| A5 | 0.3 | 0.0 | 0% |
| A6 | 0.2 | 0.0 | 0% |
| **Comunidad** | **5.7** | **5.8** | **102.4%** |

## 3. Resultados comparación regulatoria

| Escenario | Ganancia neta ($) | SC | SS | IE |
|-----------|--------------------------|-----|-----|-----|
| P2P (Stackelberg + RD) | 138,809 | 0.837 | 0.867 | -0.1898 |
| C1 CREG 174/2021 | 139,838 | 0.569 | 0.589 | -1.0000 |
| C2 Bilateral PPA | 112,691 | 0.569 | 0.589 | -0.9328 |
| C3 Mercado spot | 103,387 | 0.569 | 0.589 | -1.0000 |
| C4 CREG 101 072 ★ | 108,745 | 0.569 | 0.589 | -1.0000 |

**Price of Fairness (P2P vs C4):** 0.2166
**Spread ineficiencia estática C4:** 14.465 kWh/período

### 3.1 Ventaja P2P vs C4 por institución

| Institución | P2P ($) | C4 ($) | Ventaja P2P ($) |
|-------------|---------|---------|-----------------|
| A1 | 66,489 | 62,457 | +4,032 ✓ P2P mejor |
| A2 | 19,810 | 16,175 | +3,635 ✓ P2P mejor |
| A3 | 12,172 | 9,289 | +2,883 ✓ P2P mejor |
| A4 | 35,699 | 20,824 | +14,874 ✓ P2P mejor |
| A5 | 2,569 | 0 | +2,569 ✓ P2P mejor |
| A6 | 2,070 | 0 | +2,070 ✓ P2P mejor |

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
| SC (P2P) | 0.837 | Fracción demanda cubierta internamente |
| SS (P2P) | 0.867 | Fracción generación usada en comunidad |
| IE (P2P) | -0.1898 | Distribución beneficio (0=equitativo) |
| IE (C4)  | -1.0000 | Referencia regulatoria vigente |
| PoF      | 0.2166 | Pérdida eficiencia por equidad P2P vs C4 |

## 5. Análisis de sensibilidad

### SA-1: Variación precio de bolsa PGB

| PGB (COP/kWh) | P2P ($) | C4 ($) | IE P2P | PoF |
|---------------|---------|---------|--------|-----|
| 200 | 135,659 | 112,453 | -0.190 | 0.171 |
| 250 | 133,828 | 114,609 | -0.190 | 0.144 |
| 280 | 132,729 | 115,903 | -0.190 | 0.127 |
| 300 | 131,997 | 116,765 | -0.190 | 0.115 |
| 350 | 130,166 | 118,921 | -0.190 | 0.086 |
| 400 | 128,334 | 121,077 | -0.190 | 0.057 |
| 450 | 126,503 | 123,233 | -0.190 | 0.026 |
| 500 | 124,672 | 125,389 | -0.190 | -0.006 |

### SA-2: Variación cobertura PV

| Factor PV | Cobertura (%) | P2P ($) | C4 ($) | Horas mercado | kWh P2P |
|-----------|--------------|---------|---------|--------------|---------|
| 1.00x | 11% | 138,809 | 108,745 | 24 | 36.6 |

## 6. Análisis de factibilidad

### FA-1: Condición de deserción del P2P

- Precio P2P nunca menor que bolsa: **Sí**
- Umbral crítico precio bolsa: **1250 COP/kWh**

### FA-2: Cumplimiento CREG 101 072/2025

| Institución | Participación (%) | Cumple 10% | Cap. max (kW) | Cumple 100kW |
|-------------|------------------|-----------|--------------|-------------|
| A1 | 48.32% | ✗ | 4.0 | ✓ |
| A2 | 23.46% | ✗ | 4.0 | ✓ |
| A3 | 11.26% | ✗ | 2.5 | ✓ |
| A4 | 19.36% | ✗ | 1.5 | ✓ |
| A5 | 0.00% | ✓ | 0.0 | ✓ |
| A6 | 0.00% | ✓ | 0.0 | ✓ |

**Score de robustez C4:** 0.50 (1=máxima robustez)

### FA-1b: Deserción — Condición de Racionalidad Individual (§3.14)

**Definición formal (Restricción IR):**
Agente n permanece en P2P sii `B_n^P2P(π) ≥ max(B_n^C1, B_n^C4)(π)`

Donde `Δ_n = B_n^P2P − max(B_n^C1, B_n^C4)` (>0 → agente prefiere P2P). 
Umbral crítico `π_gb^*_n`: precio de bolsa donde el agente es indiferente.

| Agente | B_P2P ($) | B_alt ($) | Δ_n ($) | Δ_n/B_alt | π_gb^*_n | Estado |
|--------|---------|---------|---------|----------|---------|--------|
| A1 | 66,489 | 68,766 | -2,277 | -3.3% | 180 | en riesgo |
| A2 | 19,810 | 22,738 | -2,928 | -12.9% | 180 | en riesgo |
| A3 | 12,172 | 15,273 | -3,100 | -20.3% | 180 | en riesgo |
| A4 | 35,699 | 33,062 | +2,637 | +8.0% | 449 | estable |
| A5 | 2,569 | 0 | +2,569 | +0.0% | >rango | estable |
| A6 | 2,070 | 0 | +2,070 | +0.0% | >rango | estable |

**Agentes estables (3/6):** A4, A5, A6
**Umbral comunitario (mediana individual):** 315 COP/kWh
**Umbral agregado P2P < max(C1,C4):** >rango (>500.0) COP/kWh

**Tabla Δ_n(pi_gb) — sensibilidad a precio de bolsa:**

| pi_gb | A1 | A2 | A3 | A4 | A5 | A6 | Σ Δ |
|-------|--------|--------|--------|--------|--------|--------|--------|
| 200 | -2,970 | -5,574 | -4,141 | +1,960 | +2,569 | +2,070 | -6,085 |
| 250 | -3,373 | -7,112 | -4,746 | +1,567 | +2,569 | +2,070 | -9,024 |
| 280 | -3,615 | -8,035 | -5,109 | +1,331 | +2,569 | +2,070 | -10,788 |
| 300 | -3,776 | -8,650 | -5,351 | +1,174 | +2,569 | +2,070 | -11,964 |
| 350 | -4,178 | -10,188 | -5,956 | +781 | +2,569 | +2,070 | -14,903 |
| 400 | -4,581 | -11,727 | -6,561 | +387 | +2,569 | +2,070 | -17,842 |
| 450 | -4,984 | -13,265 | -7,166 | -6 | +2,569 | +2,070 | -20,782 |
| 500 | -5,387 | -14,803 | -7,771 | -399 | +2,569 | +2,070 | -23,721 |

---

## 7. Pendiente

- [ ] Correr horizonte completo 5160h: `python main_simulation.py --data real --full --analysis`
- [ ] Descargar serie horaria XM Jul 2025-Ene 2026 → `data/xm_precios_bolsa.csv`
- [ ] Verificar LCOE real de inversores instalados en cada institución
- [ ] Análisis sub-período: laborables vs fines de semana, julio vs enero

---
*Generado automáticamente por main_simulation.py · 2026-04-12 01:31*