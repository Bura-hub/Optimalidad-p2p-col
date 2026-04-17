# Reporte de Avances — Tesis P2P Colombia

**Autor:** Brayan S. Lopez-Mendez | **Fecha:** 2026-04-16 22:32
**Asesores:** Andrés Pantoja · Germán Obando | **Udenar, 2026**

---

## 1. Estado del modelo

| Parámetro | Valor |
|-----------|-------|
| Datos | Empíricos MTE — perfil diario promedio (24h) |
| Agentes | 5 instituciones Pasto (MTE) |
| Horizonte | 24h (1 días) |
| Horas con mercado P2P | 8/24 (33.3%) |
| Energía P2P total | 88.5 kWh/período |
| Precios | PGS=650.0 · PGB=280.0 COP/kWh |

## 2. Datos empíricos MTE

| Institución | D̄ (kW) | Ḡ (kW) | Cobertura PV |
|-------------|---------|---------|-------------|
| Udenar | 6.0 | 3.8 | 63% |
| Mariana | 12.4 | 1.9 | 15% |
| UCC | 35.1 | 2.1 | 6% |
| HUDN | 27.6 | 1.5 | 5% |
| Cesmag | 7.9 | 0.6 | 8% |
| **Comunidad** | **88.9** | **9.9** | **11.1%** |

## 3. Resultados comparación regulatoria

| Escenario | Ganancia neta (COP) | SC | SS | IE |
|-----------|--------------------------|-----|-----|-----|
| P2P (Stackelberg + RD) | 129,111 | 0.111 | 1.000 | 0.3934 |
| C1 CREG 174/2021 | 153,881 | 0.069 | 0.626 | -0.2782 |
| C2 Bilateral PPA | 121,150 | 0.069 | 0.626 | -0.0832 |
| C3 Mercado spot | 105,633 | 0.069 | 0.626 | 0.0515 |
| C4 CREG 101 072 ★ | 96,380 | 0.069 | 0.626 | 0.1525 |

**Price of Fairness (P2P vs C4):** 0.2535
**Spread ineficiencia estática C4:** 32.595 kWh/período

### 3.1 Ventaja P2P vs C4 por institución

| Institución | P2P (COP) | C4 (COP) | Ventaja P2P (COP) |
|-------------|---------|---------|-----------------|
| Udenar | 11,710 | 2,805 | +8,905 ✓ P2P mejor |
| Mariana | 33,809 | 28,432 | +5,377 ✓ P2P mejor |
| UCC | 41,667 | 32,265 | +9,402 ✓ P2P mejor |
| HUDN | 27,636 | 23,272 | +4,363 ✓ P2P mejor |
| Cesmag | 14,289 | 9,606 | +4,683 ✓ P2P mejor |

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
| SC (P2P) | 0.111 | Fracción demanda cubierta internamente |
| SS (P2P) | 1.000 | Fracción generación usada en comunidad |
| IE (P2P) | 0.3934 | Distribución beneficio (0=equitativo) |
| IE (C4)  | 0.1525 | Referencia regulatoria vigente |
| PoF      | 0.2535 | Pérdida eficiencia por equidad P2P vs C4 |


---

## 7. Nota metodológica — definición de ganancia neta (Fase 1)

La ganancia neta se define como el ahorro respecto al costo de línea base
(comprar toda la demanda al comercializador convencional), siguiendo la
definición validada por los asesores en reunión WEEF
(`Documentos/conversacion_WEEF.txt`, min 22-26):

    ganancia_neta = costo_línea_base - costo_con_sistema
                  = savings + revenues

El costo residual de compra a la red no entra en el cálculo porque el
agente incurriría en él igual sin participar en el mercado. Esta
convención aplica a los cinco escenarios (P2P, C1, C2, C3, C4).

**Cambio respecto a versión anterior:** en C2 (contrato bilateral PPA) se
eliminó la resta del costo residual de red, lo que corrige valores negativos
que el asesor Pantoja rechazó explícitamente. El net_benefit de C2 sube con
esta corrección; los demás escenarios no cambian numéricamente.

## 8. Pendiente

- [ ] Correr horizonte completo 5160h: `python main_simulation.py --data real --full --analysis`
- [ ] Descargar serie horaria XM Jul 2025-Ene 2026 → `data/xm_precios_bolsa.csv`
- [ ] Verificar capacidad FV instalada (kWp DC/AC) con admin MTE — requerido para PDE real en C4
- [ ] Análisis sub-período: laborables vs fines de semana, julio vs enero

---
*Generado automáticamente por main_simulation.py · 2026-04-16 22:32*
*Nota metodológica Fase 1 agregada manualmente · 2026-04-16*