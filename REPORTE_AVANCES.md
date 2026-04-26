# Reporte de Avances — Tesis P2P Colombia

**Autor:** Brayan S. Lopez-Mendez | **Fecha:** 2026-04-26 12:27
**Asesores:** Andrés Pantoja · Germán Obando | **Udenar, 2026**

---

## 1. Estado del modelo

| Parámetro | Valor |
|-----------|-------|
| Datos | Sintéticos (validación) |
| Agentes | 6 instituciones Pasto (MTE) |
| Horizonte | 24h (1 días) |
| Horas con mercado P2P | 24/24 (100.0%) |
| Energía P2P total | 44.5 kWh/período |
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
| P2P (Stackelberg + RD) | 149,166 | 0.903 | 0.935 | -0.1983 |
| C1 CREG 174/2021 | 139,838 | 0.578 | 0.598 | -1.0000 |
| C2 Bilateral PPA | 116,457 | 0.578 | 0.598 | -0.8992 |
| C3 Mercado spot | 104,717 | 0.578 | 0.598 | -1.0000 |
| C4 CREG 101 072 ★ | 103,896 | 0.578 | 0.598 | -1.0000 |

**RPE (P2P vs C4):** 0.3035
**Spread ineficiencia estática C4:** 14.164 kWh/período

### 3.1 Ventaja P2P vs C4 por institución

| Institución | P2P ($) | C4 ($) | Ventaja P2P ($) |
|-------------|---------|---------|-----------------|
| A1 | 69,558 | 62,180 | +7,378 ✓ P2P mejor |
| A2 | 19,172 | 14,072 | +5,100 ✓ P2P mejor |
| A3 | 10,632 | 9,201 | +1,431 ✓ P2P mejor |
| A4 | 46,461 | 18,443 | +28,018 ✓ P2P mejor |
| A5 | 1,665 | 0 | +1,665 ✓ P2P mejor |
| A6 | 1,679 | 0 | +1,679 ✓ P2P mejor |

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
| SC (P2P) | 0.903 | Fracción demanda cubierta internamente |
| SS (P2P) | 0.935 | Fracción generación usada en comunidad |
| IE (P2P) | -0.1983 | Distribución beneficio (0=equitativo) |
| IE (C4)  | -1.0000 | Referencia regulatoria vigente |
| RPE      | 0.3035 | Rendimiento relativo P2P vs C4 (RPE ≠ PoF Bertsimas 2011) |


---

## 7. Pendiente

- [ ] Correr horizonte completo 5160h: `python main_simulation.py --data real --full --analysis`
- [ ] Descargar serie horaria XM Jul 2025-Ene 2026 → `data/xm_precios_bolsa.csv`
- [ ] Verificar LCOE real de inversores instalados en cada institución
- [ ] Análisis sub-período: laborables vs fines de semana, julio vs enero

---
*Generado automáticamente por main_simulation.py · 2026-04-26 12:27*