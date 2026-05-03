# 0030 — CAL-30: Migración del engine a fórmula canónica P2P

- **Estado:** Accepted
- **Fecha de decisión:** 2026-05-03
- **Actividad:** 4.1 + 4.2 (cierre auditoría P2P + validación tesis)
- **Archivos afectados:**
  - `scenarios/comparison_engine.py::_p2p_monetary_benefit` (firma extendida
    con `mode={"canonical","premium"}` y `pi_bolsa`; default `canonical`).
  - `scenarios/comparison_engine.py::run_comparison` (pasa `mode="canonical"`
    + `pi_bolsa`).
  - `analysis/monthly_report.py::_p2p_benefit_month` (firma extendida con
    `pi_bolsa_m`; aplica fórmula canónica).
  - `main_simulation.py::_compute_daily_series` (pasa slice `pi_bolsa[sl]`).
- **Relacionado con:** ADR-0029 (CAL-29 paper-only). CAL-30 promueve el
  fix CAL-29 al engine de la tesis.
- **Fuente:** `Documentos/audit_p2p_decomposition.md`,
  `scripts/audit_p2p_paper.py`, plan `radiant-sleeping-eagle.md` §6.6.5.

## Contexto

CAL-29 fijó la asimetría entre fórmulas P2P y C1/C4 **solo en el script
del paper** (`scripts/run_paper_iter.py::_p2p_decomposed`). El engine de
la tesis (`scenarios/comparison_engine.py::_p2p_monetary_benefit`)
seguía con la fórmula `(pi_star − pi_gb) × P_sold` ("filosofía A"
incremental sobre el contrafactual de venta a bolsa).

La auditoría documentó que esta fórmula sub-reporta `pi_bolsa × surplus_total`
por agente. En el escenario paper (cobertura 96 % con CAL-28 sub-medidores)
el sub-reporte fue **1.92 M COP** sobre **4.95 M** canónicos (~38 %). En
la tesis con M1 totalizador (cobertura 19 %) el surplus residual es
pequeño y el sub-reporte es casi imperceptible — pero existe.

## Decisión

Promover la fórmula canónica al engine. Mantener `mode="premium"` como
opt-in para reproducibilidad histórica.

### Firma nueva

```python
def _p2p_monetary_benefit(results, D, G_klim, pi_gs, pi_gb, prosumer_ids,
                           pi_bolsa: Optional[np.ndarray] = None,
                           mode: str = "canonical") -> np.ndarray:
    ...
```

### Modos

- **`mode="canonical"`** (default desde CAL-30):
  - `net[j] = autoconsumo[j] + Σ_t pi_star[t] × P_sold[j,t]
              + Σ_t pi_bolsa[t] × residual[j,t]`
  - `net[i] = autoconsumo[i] + Σ_t (pi_gs[i,t] − pi_star[t]) × P_bought[i,t]`
- **`mode="premium"`** (legacy):
  - `net[j] = autoconsumo[j] + Σ_t (pi_star[t] − pi_gb) × P_sold[j,t]`
    (incremental sobre contrafactual "vender todo a bolsa")
  - `net[i]` igual que canónico.

### Caller updates

- `run_comparison`: pasa `mode="canonical"` y `pi_bolsa=pi_bolsa`.
- `main_simulation._compute_daily_series`: pasa `pi_bolsa=pi_bolsa[sl]`
  (slice diario).
- `analysis/monthly_report._p2p_benefit_month`: helper análogo con
  parámetro `pi_bolsa_m`.

## Validación (gate de seguridad)

**1. pytest completo (310 tests):**

| Batch | Archivos | Pasaron |
|---|---|---|
| Escenarios C1–C4 + CAL-16/17 | 5 | 65/65 ✓ |
| CAL-N tests (cal20..29) | 10 | 82/82 ✓ |
| Paper + validadores | 5 | 35/35 ✓ |
| Utilidades (backup, cvm, fairness, ...) | 10 | 66/66 ✓ |
| Preflight `--full` (`test_full_simulation_preflight`) | 1 | 41/41 ✓ |
| Telemetría + Stackelberg + fast_mode | 3 | 17/17 ✓ |
| `cal19_iters_real` (separado) | 1 | 4/4 ✓ |
| **TOTAL** | **35** | **310/310 ✓** |

**Cero tests asertaban valores P2P específicos** que sufrieran la
migración. Los tests existentes prueban relaciones (P2P > C4, IE > 0,
etc.) o invariantes estructurales (cobertura, n_periods, etc.) que
sobreviven a la fórmula canónica.

**2. RPE perfil diario `--data real`:**

```
P2P canonical: 210,496 COP
P2P premium:   210,450 COP
Delta:              46 COP (+0.02%)
```

Dentro del gate ± 0.5 % especificado en plan §6.6.5.

**3. Per-agent en perfil diario (post-CAL-30):**

```
Udenar      : +172 COP (P2P mejor que C4)
Mariana     : -51 COP (C4 mejor)
UCC         : -64 COP (C4 mejor)
HUDN        : +1 COP (P2P mejor)
Cesmag      : +35 COP (P2P mejor)
RPE total: +0.0004 (P2P > C4 marginalmente)
```

Patrón heterogéneo consistente con el caso paper (CAL-29).

## Consecuencias

**Positivas:**
- El engine de tesis y el del paper ahora usan la **misma fórmula
  canónica**. Cero divergencia metodológica.
- Capítulo 4 puede reportar net_benefit P2P sin la asimetría
  histórica de la fórmula incremental.
- La tabla `flow_breakdown["P2P"]` en `comparison_engine` sigue
  reportando `Prima vendedor` y `Ahorro comprador` para el reporte
  de descomposición (Act 3.2 — Nivel 1), pero el `net_benefit["P2P"]`
  ahora suma revenue completo del trade + residual a `pi_bolsa`.

**Negativas:**
- Cualquier reporte/figura previa que cite valores P2P específicos en
  COP queda desfasada. En perfil diario el delta es ~0.02 %, en el
  horizonte completo será ~0.02-0.5 % (límite superior). Para el caso
  paper (cobertura alta CAL-28) el delta es ~38 % — pero esto se
  reportó correctamente en CAL-29 sin tocar el engine.
- Tests futuros que necesiten reproducir valores pre-CAL-30 deben
  pasar `mode="premium"` explícitamente.

**Pendiente (autor humano):**
- Ejecutar `python main_simulation.py --data real --full --analysis`
  (~30 min) para capturar la nueva RPE sobre las 5 160 horas y
  actualizar §4.9 cap. 4 si el delta es > 0.1 % (esperado: pequeño
  por baja cobertura del totalizador M1).
- Actualizar referencias a "RPE = +0.43 %" en `borrador_cap4_resultados.md`
  y `REPORTE_AVANCES.md` con el valor canónico.

## Test plan adicional

Los 4 tests CAL-29 en `tests/test_cal29_p2p_canonical.py` ahora prueban
indirectamente CAL-30 vía la fórmula compartida. No se añaden tests
adicionales: la cobertura es suficiente y los 310 tests existentes
verifican las relaciones canónicas.

## Referencias

- ADR-0029: fix paper-only que motivó CAL-30.
- `Documentos/audit_p2p_decomposition.md`: auditoría completa con
  invariante H1 verificada empíricamente.
- `scripts/audit_p2p_paper.py`: diagnóstico reproducible.
- Plan `radiant-sleeping-eagle.md` §6.6.5 Sprint 6.6-A (audit) — gate
  de seguridad cumplido.
