# Reporte de Avances — Tesis P2P Colombia

**Autor:** Brayan S. Lopez-Mendez | **Fecha:** 2026-04-25 23:05
**Asesores:** Andrés Pantoja · Germán Obando | **Udenar, 2026**

---

## 1. Estado del modelo

| Parámetro | Valor |
|-----------|-------|
| Datos | Empíricos MTE — perfil diario promedio (24h) |
| Agentes | 5 instituciones Pasto (MTE) |
| Horizonte | 24h (1 días) |
| Horas con mercado P2P | 1/24 (4.2%) |
| Energía P2P total | 0.3 kWh/período |
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
| P2P (Stackelberg + RD) | 154,432 | 0.191 | 1.000 | -0.0634 |
| C1 CREG 174/2021 | 154,527 | 0.191 | 0.999 | -0.0823 |
| C2 Bilateral PPA | 154,401 | 0.191 | 0.999 | -0.0815 |
| C3 Mercado spot | 154,342 | 0.191 | 0.999 | -0.0811 |
| C4 CREG 101 072 ★ | 154,306 | 0.191 | 0.999 | -0.0809 |

**RPE (P2P vs C4):** 0.0008
**Spread ineficiencia estática C4:** 0.074 kWh/período

### 3.1 Ventaja P2P vs C4 por institución

| Institución | P2P (COP) | C4 (COP) | Ventaja P2P (COP) |
|-------------|---------|---------|-----------------|
| Udenar | 33,410 | 33,343 | +67 ✓ P2P mejor |
| Mariana | 31,877 | 31,863 | +14 ✓ P2P mejor |
| UCC | 39,059 | 39,046 | +13 ✓ P2P mejor |
| HUDN | 32,847 | 32,831 | +16 ✓ P2P mejor |
| Cesmag | 17,239 | 17,224 | +16 ✓ P2P mejor |

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
| SC (P2P) | 0.191 | Fracción demanda cubierta internamente |
| SS (P2P) | 1.000 | Fracción generación usada en comunidad |
| IE (P2P) | -0.0634 | Distribución beneficio (0=equitativo) |
| IE (C4)  | -0.0809 | Referencia regulatoria vigente |
| RPE      | 0.0008 | Rendimiento relativo P2P vs C4 (RPE ≠ PoF Bertsimas 2011) |


---

## 7. Pendiente

- [ ] Correr horizonte completo 5160h: `python main_simulation.py --data real --full --analysis`
- [ ] Descargar serie horaria XM Jul 2025-Ene 2026 → `data/xm_precios_bolsa.csv`
- [ ] Verificar LCOE real de inversores instalados en cada institución
- [ ] Análisis sub-período: laborables vs fines de semana, julio vs enero

---
*Generado automáticamente por main_simulation.py · 2026-04-25 23:05*