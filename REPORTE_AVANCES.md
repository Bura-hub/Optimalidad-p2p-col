# Reporte de Avances — Tesis P2P Colombia

**Autor:** Brayan S. Lopez-Mendez | **Fecha:** 2026-04-17 11:37
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

## 5. Análisis de sensibilidad global (Act. 4.1)

El módulo `analysis/global_sensitivity.py` implementa el análisis de sensibilidad
global de Saltelli mediante el método de Sobol (SALib 1.5.2). Siete parámetros de
entrada: PGB [114–500], PGS [500–750], factor_PV [0,5–2,0], factor_D [0,7–1,5],
alpha_mean [0,0–0,25], b_mean [150–400] COP/kWh, pi_ppa [200–900] COP/kWh.
Tres outputs evaluados: ganancia neta P2P, SC comunitario, IE de equidad.

**Estado:** smoke test n_base = 4 exitoso. Para índices Sobol fiables: `python main_simulation.py --gsa --n-base 64` (~75 min, 8 workers).

---

## 6. Tests estadísticos P2P vs C4 (Act. 4.2)

Bootstrap por bloques Kunsch (1989) implementado en `tests/statistical_tests.py`.
Remuestreo circular semanal (block_days = 7); IC 95 %, Wilcoxon pareado bilateral,
Cohen's d, n_eff. Resultados estadísticos definitivos pendientes del run `--full`.

---

## 7. Modos del escenario C4 (CREG 101 072/2025)

`scenarios/scenario_c4_creg101072.py` implementa dos modos:
- `pde_only` (**default**): distribución administrativa vía PDE.
- `pde_plus_residual_export`: extensión con exportación de excedentes a bolsa.

---

## 8. Golden test vs modelo base (Chacón et al., 2025)

`tests/golden_test_sofia.py` verifica que Replicator Dynamics reproduce el equilibrio
SLSQP de `Documentos/copy/Bienestar6p.py` (hora 14, commit 5a15d24):
P_total dentro de atol = 0,15 kWh; pi_i ∈ [PGB, PGS]; no excede G_net_j; aprobado.

---

## 9. Pendiente

- [ ] Run horizonte completo 5 160 h: `python main_simulation.py --data real --full --analysis`
- [ ] GSA Sobol n_base ≥ 64 (solicitar OK): `python main_simulation.py --gsa --n-base 64`
- [ ] Descargar serie horaria XM jul. 2025–ene. 2026 → `data/xm_precios_bolsa.csv`
- [ ] Bootstrap con datos reales: `python tests/statistical_tests.py`
- [ ] Verificar LCOE real de inversores instalados en cada institución MTE
- [ ] Confirmar autores referencias [22][24][26][27] en `Documentos/references.bib`

---

## Trazabilidad

| Campo | Valor |
|---|---|
| Fecha | 2026-04-17 |
| Commit (Fase 3) | `c36ff3b` — docs: actualiza README.md |
| Commit (última simulación) | `5a15d24` — Act 3.2 — actualiza resultados |
| Python | 3.13.7 |
| pandas | 2.3.3 |
| Comando §1–§4 | `python main_simulation.py` (caso sintético) |

*Secciones §1–§4 generadas automáticamente por `main_simulation.py · 2026-04-17 11:37`.
Secciones §5–§9 mantenidas manualmente — no se sobrescriben al re-ejecutar.*