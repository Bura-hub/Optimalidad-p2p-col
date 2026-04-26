# Reporte de Avances — Tesis P2P Colombia

**Autor:** Brayan S. Lopez-Mendez | **Fecha:** 2026-04-26 02:37
**Asesores:** Andrés Pantoja · Germán Obando | **Udenar, 2026**

---

## 1. Estado del modelo

| Parámetro | Valor |
|-----------|-------|
| Datos | Empíricos MTE — 5160h completas |
| Agentes | 5 instituciones Pasto (MTE) |
| Horizonte | 6144h (256 días) |
| Horas con mercado P2P | 1031/6144 (16.8%) |
| Energía P2P total | 3657.7 kWh/período |
| Precios | PGS=650.0 · PGB=280.0 COP/kWh |

## 2. Datos empíricos MTE

| Institución | D̄ (kW) | Ḡ (kW) | Cobertura PV |
|-------------|---------|---------|-------------|
| Udenar | 7.2 | 2.2 | 30% |
| Mariana | 9.6 | 2.0 | 21% |
| UCC | 21.4 | 2.5 | 12% |
| HUDN | 9.1 | 2.1 | 23% |
| Cesmag | 4.5 | 1.1 | 25% |
| **Comunidad** | **51.8** | **9.9** | **19.1%** |

## 3. Resultados comparación regulatoria

| Escenario | Ganancia neta (COP) | SC | SS | IE |
|-----------|--------------------------|-----|-----|-----|
| P2P (Stackelberg + RD) | 37,776,156 | 0.188 | 0.981 | 0.4063 |
| C1 CREG 174/2021 | 39,559,013 | 0.176 | 0.921 | -0.0823 |
| C2 Bilateral PPA | 37,773,788 | 0.176 | 0.921 | -0.0458 |
| C3 Mercado spot | 37,294,678 | 0.176 | 0.921 | -0.0354 |
| C4 CREG 101 072 ★ | 36,564,671 | 0.176 | 0.921 | -0.0170 |

**RPE (P2P vs C4):** 0.0321
**Spread ineficiencia estática C4:** 1004.436 kWh/período

### 3.1 Ventaja P2P vs C4 por institución

| Institución | P2P (COP) | C4 (COP) | Ventaja P2P (COP) |
|-------------|---------|---------|-----------------|
| Udenar | 6,451,279 | 6,187,405 | +263,874 ✓ P2P mejor |
| Mariana | 8,252,661 | 8,070,465 | +182,196 ✓ P2P mejor |
| UCC | 10,278,482 | 9,901,698 | +376,783 ✓ P2P mejor |
| HUDN | 8,347,133 | 8,142,617 | +204,516 ✓ P2P mejor |
| Cesmag | 4,446,601 | 4,262,486 | +184,115 ✓ P2P mejor |

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
| SC (P2P) | 0.188 | Fracción demanda cubierta internamente |
| SS (P2P) | 0.981 | Fracción generación usada en comunidad |
| IE (P2P) | 0.4063 | Distribución beneficio (0=equitativo) |
| IE (C4)  | -0.0170 | Referencia regulatoria vigente |
| RPE      | 0.0321 | Rendimiento relativo P2P vs C4 (RPE ≠ PoF Bertsimas 2011) |

## 5. Análisis de sensibilidad

### SA-1: Variación precio de bolsa PGB

| PGB (COP/kWh) | P2P (COP) | C4 (COP) | IE P2P | RPE |
|---------------|---------|---------|--------|-----|
| 200 | 38,068,773 | 36,564,671 | 0.406 | 0.040 |
| 250 | 37,885,888 | 36,564,671 | 0.406 | 0.035 |
| 280 | 37,776,156 | 36,564,671 | 0.406 | 0.032 |
| 300 | 37,703,002 | 36,564,671 | 0.406 | 0.030 |
| 350 | 37,520,117 | 36,564,671 | 0.406 | 0.025 |
| 400 | 37,337,232 | 36,564,671 | 0.406 | 0.021 |
| 450 | 37,154,347 | 36,564,671 | 0.406 | 0.016 |
| 500 | 36,971,462 | 36,564,671 | 0.406 | 0.011 |

### SA-2: Variación cobertura PV

| Factor PV | Cobertura (%) | P2P (COP) | C4 (COP) | Horas mercado | kWh P2P |
|-----------|--------------|---------|---------|--------------|---------|
| 1.00x | 11% | 37,776,156 | 36,564,671 | 1031 | 3657.7 |
| 1.05x | 12% | 39,304,084 | 38,010,375 | 1081 | 3957.8 |
| 1.72x | 19% | 58,718,330 | 56,219,193 | 1576 | 8560.7 |
| 2.61x | 30% | 76,757,827 | 73,050,863 | 1685 | 13593.3 |
| 3.92x | 44% | 93,130,832 | 89,784,014 | 1563 | 15987.5 |
| 5.23x | 59% | 102,737,122 | 100,254,244 | 1402 | 14708.6 |

## 6. Análisis de factibilidad

### FA-1: Condición de deserción del P2P

- Precio P2P nunca menor que bolsa: **No**
- Umbral crítico precio bolsa: **414 COP/kWh**

### FA-2: Cumplimiento CREG 101 072/2025

| Institución | Participación (%) | Cumple 10% | Cap. max (kW) | Cumple 100kW |
|-------------|------------------|-----------|--------------|-------------|
| Udenar | 4.16% | ✓ | 13.9 | ✓ |
| Mariana | 3.95% | ✓ | 14.7 | ✓ |
| UCC | 4.84% | ✓ | 15.1 | ✓ |
| HUDN | 4.07% | ✓ | 14.0 | ✓ |
| Cesmag | 2.13% | ✓ | 10.1 | ✓ |

**Score de robustez C4:** 1.00 (1=máxima robustez)

### FA-1b: Deserción — Condición de Racionalidad Individual (§3.14)

**Definición formal (Restricción IR):**
Agente n permanece en P2P sii `B_n^P2P(π) ≥ max(B_n^C1, B_n^C4)(π)`

Donde `Δ_n = B_n^P2P − max(B_n^C1, B_n^C4)` (>0 → agente prefiere P2P). 
Umbral crítico `π_gb^*_n`: precio de bolsa donde el agente es indiferente.

| Agente | B_P2P (COP) | B_alt (COP) | Δ_n (COP) | Δ_n/B_alt | π_gb^*_n | Estado |
|--------|---------|---------|---------|----------|---------|--------|
| Udenar | 6,451,279 | 8,592,498 | -2,141,219 | -24.9% | 180 | en riesgo |
| Mariana | 8,252,661 | 8,156,901 | +95,759 | +1.2% | >rango | estable |
| UCC | 10,278,482 | 9,995,718 | +282,764 | +2.8% | >rango | estable |
| HUDN | 8,347,133 | 8,404,645 | -57,512 | -0.7% | 180 | en riesgo |
| Cesmag | 4,446,601 | 4,409,250 | +37,352 | +0.8% | 408 | estable |

**Agentes estables (3/5):** Mariana, UCC, Cesmag
**Umbral comunitario (mediana individual):** 408 COP/kWh
**Umbral agregado P2P < max(C1,C4):** >rango (>500.0) COP/kWh

**Tabla Δ_n(pi_gb) — sensibilidad a precio de bolsa:**

| pi_gb | Udenar | Mariana | UCC | HUDN | Cesmag | Σ Δ |
|-------|--------|--------|--------|--------|--------|--------|
| 200 | -1,917,764 | +105,954 | +288,254 | -27,475 | +60,790 | -1,490,240 |
| 250 | -2,057,423 | +99,582 | +284,822 | -46,248 | +46,141 | -1,673,125 |
| 280 | -2,141,219 | +95,759 | +282,764 | -57,512 | +37,352 | -1,782,856 |
| 300 | -2,197,083 | +93,211 | +281,391 | -65,021 | +31,492 | -1,856,010 |
| 350 | -2,336,743 | +86,839 | +277,960 | -83,795 | +16,843 | -2,038,896 |
| 400 | -2,476,403 | +80,467 | +274,528 | -102,568 | +2,194 | -2,221,781 |
| 450 | -2,616,062 | +74,096 | +271,097 | -121,341 | -12,455 | -2,404,666 |
| 500 | -2,755,722 | +67,724 | +267,666 | -140,114 | -27,104 | -2,587,551 |

---

## 7. Pendiente

- [ ] Correr horizonte completo 5160h: `python main_simulation.py --data real --full --analysis`
- [ ] Descargar serie horaria XM Jul 2025-Ene 2026 → `data/xm_precios_bolsa.csv`
- [ ] Verificar LCOE real de inversores instalados en cada institución
- [ ] Análisis sub-período: laborables vs fines de semana, julio vs enero

---
*Generado automáticamente por main_simulation.py · 2026-04-26 02:37*