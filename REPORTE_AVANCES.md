# Reporte de Avances — Tesis P2P Colombia

**Autor:** Brayan S. Lopez-Mendez | **Fecha:** 2026-04-17 10:55
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

**Nota:** Esta sección se actualiza automáticamente con cada ejecución de
`main_simulation.py`. Los resultados anteriores corresponden a la validación
sintética del caso base. Los números del horizonte completo (5 160 h reales)
están **pendientes** de la ejecución `--data real --full --analysis`.

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
| A1 | 69,558 | 62,180 | +7,378 |
| A2 | 19,172 | 14,072 | +5,100 |
| A3 | 10,632 | 9,201 | +1,431 |
| A4 | 46,461 | 18,443 | +28,018 |
| A5 | 1,665 | 0 | +1,665 |
| A6 | 1,679 | 0 | +1,679 |

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
| RPE      | 0.3035 | Rendimiento relativo P2P vs C4 |

**RPE** = (W_P2P − W_C4) / |W_P2P|: positivo indica que P2P supera a C4.
RPE ≠ PoF de Bertsimas (2011); ver `Documentos/notas_modelo_tesis.md §6`.

---

## 5. Análisis de sensibilidad global (Act 4.1)

El módulo `analysis/global_sensitivity.py` implementa el análisis de sensibilidad
global de Saltelli mediante el método de Sobol (SALib 1.5.2).

**Parámetros de entrada (7):**

| Parámetro | Rango | Interpretación |
|---|---|---|
| PGB | [114, 500] COP/kWh | Precio bolsa nominal → precio de escasez CREG 101 066 |
| PGS | [500, 750] COP/kWh | Tarifa usuario subsidiada → tarifa media Colombia |
| factor_PV | [0.5, 2.0] | Factor de escala sobre generación solar (lluvia/sequía) |
| factor_D | [0.7, 1.5] | Factor de escala sobre demanda (vacaciones/pico) |
| alpha_mean | [0.0, 0.25] | Media del parámetro de respuesta a la demanda (alpha) |
| b_mean | [150, 400] COP/kWh | LCOE lineal de generación (b_n); no confundir con pi_bolsa |
| pi_ppa | [200, 900] COP/kWh | Precio bilateral PPA (escenario C2) |

**Outputs evaluados (3):** ganancia neta P2P, SC comunitario, IE de equidad.

**Estado:** smoke test con n_base = 4 (56 evaluaciones) exitoso. Para índices
Sobol estadísticamente fiables se requiere n_base ≥ 64 (~1 024 evaluaciones,
~75 min con 8 workers). Ejecutar:

```powershell
python main_simulation.py --gsa --n-base 64
```

Los resultados se guardan en `outputs/gsa_checkpoint_<ts>.parquet` (cada 100
muestras) y en `resultados_gsa.xlsx` (hojas S1_ST, S2, Muestras_X).

---

## 6. Tests estadísticos P2P vs C4 (Act 4.2)

El módulo `tests/statistical_tests.py` implementa el bootstrap por bloques de
Kunsch (1989) para comparar las series diarias de beneficio neto P2P y C4.

**Metodología:**
- Remuestreo circular de bloques semanales (block_days = 7) para preservar
  la autocorrelación del ciclo laborable/fin de semana.
- Diferencia diaria delta_d = B_P2P[d] − B_C4[d].
- Intervalo de confianza al 95 % (IC 95 %) por percentiles bootstrap.
- Prueba de Wilcoxon pareada bilateral (scipy.stats).
- Tamaño de efecto Cohen's d y muestra efectiva n_eff ≈ n_días / 7.

**Estado:** módulo implementado y probado con datos sintéticos. Los resultados
estadísticos definitivos requieren las series diarias del run `--full` (5 160 h).
Cuando esas series existan en `outputs/daily_series_<ts>.csv`, ejecutar:

```powershell
python tests/statistical_tests.py [--n-bootstrap 1000] [--block-days 7]
```

Los resultados se guardan en `outputs/bootstrap_42.json` y
`resultados_tests.xlsx` (hoja Bootstrap_P2P_vs_C4).

---

## 7. Modos del escenario C4 (CREG 101 072/2025)

El módulo `scenarios/scenario_c4_creg101072.py` implementa dos modos de
liquidación para el escenario C4:

| Modo | Parámetro | Descripción |
|---|---|---|
| `pde_only` | `mode="pde_only"` | **Default.** Distribución administrativa vía PDE (Porcentaje de Distribución de Excedentes). No incluye exportación individual a bolsa |
| `pde_plus_residual_export` | `mode="pde_plus_residual_export"` | Extensión: distribuye excedentes vía PDE y, adicionalmente, exporta excedentes no distribuidos a precio de bolsa |

El modo `pde_only` es el comportamiento regulatorio vigente según CREG
101 072/2025 para comunidades energéticas con un único punto de conexión
y distribución administrativa. El modo `pde_plus_residual_export` es una
extensión hipotética para análisis de sensibilidad regulatoria.

---

## 8. Golden test vs modelo base (Sofía Chacón et al., 2025)

El archivo `tests/golden_test_sofia.py` verifica que el núcleo Python (Replicator
Dynamics) reproduce el equilibrio Nash calculado por el optimizador estático SLSQP
de `Documentos/copy/Bienestar6p.py` (modelo base de referencia [5]).

**Oráculo:** `Documentos/copy/reference_h14.json` (hora 14, t=13, parámetros
JoinFinal.m: theta=0.5, etha=0.1, PGS=1 250, PGB=114, datos sintéticos).

**Resultados del golden test (última ejecución, commit 5a15d24):**

| Prueba | Criterio | Resultado |
|---|---|---|
| Mercado activo en hora 14 | P_star ≠ None, pi_star ≠ None | aprobada |
| P_total (kWh transados) | \|P_EMS − P_SLSQP\| ≤ 0.15 kWh | aprobada |
| Vaciado de demanda por comprador | err_rel_max ≤ 5 % | aprobada |
| Precios pi_i en rango | pi_i ∈ [PGB, PGS] | aprobada |
| No exceder G_net_j por vendedor | max_viol ≤ 1e-3 kW | aprobada |

**Justificación de las tolerancias:** SLSQP (Bienestar6p.py) usa utilidad
log-precio (−P_ji / log(1 + |π_i|)); RD usa fitness lineal (π_i − H_j). Las
formulaciones son distintas pero convergen al mismo equilibrio Nash de vaciado
de mercado. La tolerancia atol = 0,15 kWh absorbe diferencias de método; la
comparación se hace sobre métricas de clearing, no sobre P_ij componente a
componente (SLSQP concentra en un vendedor, RD distribuye).

---

## 9. Pendiente

- [ ] Run horizonte completo 5 160 h: `python main_simulation.py --data real --full --analysis`
- [ ] GSA Sobol n_base ≥ 64: `python main_simulation.py --gsa --n-base 64` (solicitar OK al usuario antes)
- [ ] Descargar serie horaria XM jul. 2025–ene. 2026 → `data/xm_precios_bolsa.csv`
- [ ] Verificar LCOE real de inversores instalados en cada institución MTE
- [ ] Confirmar autores de referencias [22], [24], [26], [27] en `Documentos/references.bib`
- [ ] Ejecutar bootstrap con datos reales: `python tests/statistical_tests.py`

---

## Trazabilidad

| Campo | Valor |
|---|---|
| Fecha | 2026-04-17 |
| Commit (Fase 3) | `0450a7a` — docs: crea matriz de trazabilidad |
| Commit (última simulación) | `5a15d24` — Act 3.2 — actualiza resultados |
| Python | 3.13.7 |
| pandas | 2.3.3 |
| Comando §1–§4 | `python main_simulation.py` (caso sintético) |
| Comando §5 | `python main_simulation.py --gsa --n-base 4` (smoke test) |
| Documento completo | `Documentos/Matriz_Trazabilidad.md` |

*Secciones §1–§4 generadas automáticamente por `main_simulation.py`.
Secciones §5–§9 mantenidas manualmente — no se sobrescriben al re-ejecutar.*
