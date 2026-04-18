# Reporte de Avances — Tesis P2P Colombia

**Autor:** Brayan S. Lopez-Mendez | **Fecha:** 2026-04-17 18:22
**Asesores:** Andrés Pantoja · Germán Obando | **Udenar, 2026**

---

## 1. Estado del modelo

| Parámetro | Valor |
|-----------|-------|
| Datos | Empíricos MTE — perfil diario promedio (24h) |
| Agentes | 5 instituciones Pasto (MTE) |
| Horizonte | 24h (1 días) |
| Horas con mercado P2P | 3/24 (12.5%) |
| Energía P2P total | 33.9 kWh/período |
| Precios | PGS=650.0 · PGB=280.0 COP/kWh |

## 2. Datos empíricos MTE

| Institución | D̄ (kW) | Ḡ (kW) | Cobertura PV |
|-------------|---------|---------|-------------|
| Udenar | 14.4 | 3.0 | 21% |
| Mariana | 17.9 | 1.5 | 8% |
| UCC | 78.2 | 1.7 | 2% |
| HUDN | 27.7 | 1.5 | 5% |
| Cesmag | 15.7 | 0.8 | 5% |
| **Comunidad** | **153.9** | **8.5** | **5.5%** |

## 3. Resultados comparación regulatoria

| Escenario | Ganancia neta (COP) | SC | SS | IE |
|-----------|--------------------------|-----|-----|-----|
| P2P (Stackelberg + RD) | 123,433 | 0.055 | 1.000 | 0.0922 |
| C1 CREG 174/2021 | 132,926 | 0.046 | 0.834 | -0.3993 |
| C2 Bilateral PPA | 120,381 | 0.046 | 0.834 | -0.3367 |
| C3 Mercado spot | 114,432 | 0.046 | 0.834 | -0.3022 |
| C4 CREG 101 072 ★ | 110,888 | 0.046 | 0.834 | -0.2799 |

**RPE (P2P vs C4):** 0.1016
**Spread ineficiencia estática C4:** 12.628 kWh/período

### 3.1 Ventaja P2P vs C4 por institución

| Institución | P2P (COP) | C4 (COP) | Ventaja P2P (COP) |
|-------------|---------|---------|-----------------|
| Udenar | 30,201 | 24,508 | +5,694 ✓ P2P mejor |
| Mariana | 26,919 | 23,493 | +3,425 ✓ P2P mejor |
| UCC | 27,098 | 27,098 | +0 ✓ P2P mejor |
| HUDN | 26,389 | 22,963 | +3,425 ✓ P2P mejor |
| Cesmag | 12,825 | 12,825 | +0 ✓ P2P mejor |

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
| SC (P2P) | 0.055 | Fracción demanda cubierta internamente |
| SS (P2P) | 1.000 | Fracción generación usada en comunidad |
| IE (P2P) | 0.0922 | Distribución beneficio (0=equitativo) |
| IE (C4)  | -0.2799 | Referencia regulatoria vigente |
| RPE      | 0.1016 | Rendimiento relativo P2P vs C4 (RPE ≠ PoF Bertsimas 2011) |

## 5. Análisis de sensibilidad

### SA-1: Variación precio de bolsa PGB

| PGB (COP/kWh) | P2P (COP) | C4 (COP) | IE P2P | RPE |
|---------------|---------|---------|--------|-----|
| 200 | 126,145 | 110,888 | 0.092 | 0.121 |
| 250 | 124,450 | 110,888 | 0.092 | 0.109 |
| 280 | 123,433 | 110,888 | 0.092 | 0.102 |
| 300 | 122,755 | 110,888 | 0.092 | 0.097 |
| 350 | 121,060 | 110,888 | 0.092 | 0.084 |
| 400 | 119,364 | 110,888 | 0.092 | 0.071 |
| 450 | 117,669 | 110,888 | 0.092 | 0.058 |
| 500 | 115,974 | 110,888 | 0.092 | 0.044 |

### SA-2: Variación cobertura PV

| Factor PV | Cobertura (%) | P2P (COP) | C4 (COP) | Horas mercado | kWh P2P |
|-----------|--------------|---------|---------|--------------|---------|
| 1.99x | 22% | 244,541 | 218,692 | 4 | 69.9 |
| 3.61x | 41% | 434,964 | 375,207 | 5 | 161.5 |
| 5.96x | 67% | 659,195 | 566,029 | 7 | 293.4 |
| 9.03x | 102% | 862,370 | 776,661 | 7 | 365.7 |
| 10.00x | 113% | 915,194 | 832,840 | 8 | 386.1 |

## 6. Análisis de factibilidad

### FA-1: Condición de deserción del P2P

- Precio P2P nunca menor que bolsa: **Sí**
- Umbral crítico precio bolsa: **448 COP/kWh**

### FA-2: Cumplimiento CREG 101 072/2025

| Institución | Participación (%) | Cumple 10% | Cap. max (kW) | Cumple 100kW |
|-------------|------------------|-----------|--------------|-------------|
| Udenar | 1.94% | ✓ | 14.0 | ✓ |
| Mariana | 0.98% | ✓ | 6.9 | ✓ |
| UCC | 1.13% | ✓ | 7.6 | ✓ |
| HUDN | 0.96% | ✓ | 6.6 | ✓ |
| Cesmag | 0.53% | ✓ | 2.8 | ✓ |

**Score de robustez C4:** 1.00 (1=máxima robustez)

### FA-1b: Deserción — Condición de Racionalidad Individual (§3.14)

**Definición formal (Restricción IR):**
Agente n permanece en P2P sii `B_n^P2P(π) ≥ max(B_n^C1, B_n^C4)(π)`

Donde `Δ_n = B_n^P2P − max(B_n^C1, B_n^C4)` (>0 → agente prefiere P2P). 
Umbral crítico `π_gb^*_n`: precio de bolsa donde el agente es indiferente.

| Agente | B_P2P (COP) | B_alt (COP) | Δ_n (COP) | Δ_n/B_alt | π_gb^*_n | Estado |
|--------|---------|---------|---------|----------|---------|--------|
| Udenar | 30,201 | 46,546 | -16,344 | -35.1% | 180 | en riesgo |
| Mariana | 26,919 | 23,493 | +3,425 | +14.6% | >rango | estable |
| UCC | 27,098 | 27,098 | +0 | +0.0% | >rango | estable |
| HUDN | 26,389 | 22,963 | +3,425 | +14.9% | >rango | estable |
| Cesmag | 12,825 | 12,825 | +0 | +0.0% | >rango | estable |

**Agentes estables (4/5):** Mariana, UCC, HUDN, Cesmag
**Umbral comunitario (mediana individual):** >rango (>500.0) COP/kWh
**Umbral agregado P2P < max(C1,C4):** >rango (>500.0) COP/kWh

**Tabla Δ_n(pi_gb) — sensibilidad a precio de bolsa:**

| pi_gb | Udenar | Mariana | UCC | HUDN | Cesmag | Σ Δ |
|-------|--------|--------|--------|--------|--------|--------|
| 200 | -13,632 | +3,425 | +0 | +3,425 | +0 | -6,781 |
| 250 | -15,327 | +3,425 | +0 | +3,425 | +0 | -8,476 |
| 280 | -16,344 | +3,425 | +0 | +3,425 | +0 | -9,493 |
| 300 | -17,022 | +3,425 | +0 | +3,425 | +0 | -10,171 |
| 350 | -18,718 | +3,425 | +0 | +3,425 | +0 | -11,867 |
| 400 | -20,413 | +3,425 | +0 | +3,425 | +0 | -13,562 |
| 450 | -22,108 | +3,425 | +0 | +3,425 | +0 | -15,257 |
| 500 | -23,803 | +3,425 | +0 | +3,425 | +0 | -16,952 |

---

## 7. Ejecuciones completadas (adicionales al perfil promedio)

| Run | Fecha | Archivo de log | Descripción |
|-----|-------|----------------|-------------|
| Día de referencia | 2026-04-17 | `outputs/run_day_2025-08-06_1458.log` | Miércoles laborable, irradiancia alta. Sub-períodos SP1–SP4 (Laborable/Finde × Jul/Ene). RPE = 0.1581 (Laborable-Jul). |
| GSA Sobol n_base=64 | 2026-04-17 | `resultados_gsa.xlsx` | 7 parámetros, 3 outputs (ganancia, SC, IE), 1 024 evaluaciones. Factor dominante SC: `factor_PV`; IE: `PGB`. IC amplios; orden cualitativo interpretable. |
| Bootstrap P2P vs C4 | 2026-04-17 | `resultados_tests.xlsx` | n=500 bloques, block_days=7, seed=42. Δ̄ = 7 489 COP/día, IC 95 % = [6 051, 8 963], p-Wilcoxon = 0.000, Cohen's d = 0.67 (n_eff = 30). |

## 8. Pendiente

- [ ] **Horizonte completo 5 160 h (postergado):** `python main_simulation.py --data real --full --analysis`. Condición de cierre para Actividad 3.2 y valor definitivo de IE, RPE y métricas mensuales. Ver `Documentos/Matriz_Trazabilidad.md`.
- [ ] Verificar LCOE real de inversores instalados en cada institución (parámetro `b_n`).
- [ ] GSA n_base ≥ 256 (~3–4 h) para IC estrechos en S1/ST (opcional para publicación).
- [ ] Bootstrap sobre serie de 5 160 h (depende del run `--full`).

---
*Sección §1–§6 generada automáticamente por main_simulation.py · 2026-04-17 18:22*
*Secciones §7–§8 actualizadas manualmente · 2026-04-17*