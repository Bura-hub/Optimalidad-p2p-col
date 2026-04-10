# Reporte de Avances — Tesis P2P Colombia

**Autor:** Brayan S. Lopez-Mendez | **Fecha:** 2026-04-10 06:24
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
| P2P (Stackelberg + RD) | -172,034 | 0.113 | 1.000 | 0.1006 |
| C1 CREG 174/2021 | -1,190,254 | 0.088 | 0.785 | 1.0000 |
| C2 Bilateral PPA | 145,203 | 0.088 | 0.785 | -1.0000 |
| C3 Mercado spot | -1,190,254 | 0.088 | 0.785 | 1.0000 |
| C4 CREG 101 072 ★ | -1,208,239 | 0.088 | 0.785 | 1.0000 |

**Price of Fairness (P2P vs C4):** 6.0233
**Spread ineficiencia estática C4:** 20.341 kWh/período

### 3.1 Ventaja P2P vs C4 por institución

| Institución | P2P (COP) | C4 (COP) | Ventaja P2P (COP) |
|-------------|---------|---------|-----------------|
| Udenar | 35,280 | -65,363 | +100,643 ✓ P2P mejor |
| Mariana | 2,130 | -159,727 | +161,857 ✓ P2P mejor |
| UCC | -196,637 | -587,183 | +390,546 ✓ P2P mejor |
| HUDN | -6,430 | -285,592 | +279,161 ✓ P2P mejor |
| Cesmag | -6,377 | -110,374 | +103,997 ✓ P2P mejor |

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
| IE (P2P) | 0.1006 | Distribución beneficio (0=equitativo) |
| IE (C4)  | 1.0000 | Referencia regulatoria vigente |
| PoF      | 6.0233 | Pérdida eficiencia por equidad P2P vs C4 |


---

## 7. Pendiente

- [ ] Correr horizonte completo 5160h: `python main_simulation.py --data real --full --analysis`
- [ ] Descargar serie horaria XM Jul 2025-Ene 2026 → `data/xm_precios_bolsa.csv`
- [ ] Verificar LCOE real de inversores instalados en cada institución
- [ ] Análisis sub-período: laborables vs fines de semana, julio vs enero

---
*Generado automáticamente por main_simulation.py · 2026-04-10 06:24*