# 0029 — CAL-29: Fórmula canónica de net_benefit P2P en modo paper

- **Estado:** Accepted (paper-only; engine pendiente de CAL-30)
- **Fecha de decisión:** 2026-05-03
- **Actividad:** 4.1 + 4.2 (escritura paper)
- **Archivos afectados:** `scripts/run_paper_iter.py::_p2p_decomposed`
  (reescrito, dos bugs corregidos), `tests/test_cal29_p2p_canonical.py`
  (nuevo).
  **NO toca** `scenarios/comparison_engine.py::_p2p_monetary_benefit`
  (decisión consciente: el engine reescribe en CAL-30 con validación
  completa de tesis).
- **Relacionado con:** ADR-0025 (CAL-25 modo paper), Sprint 6.6-A audit.
- **Fuente:** auditoría documentada en
  `Documentos/audit_p2p_decomposition.md` y diagnóstico empírico
  `scripts/audit_p2p_paper.py`.

## Contexto

Tras activar CAL-25..28 (modo paper + sub-medidores M3 al 96 %
cobertura), el reporte de Sprint 6.4 mostró un gap inesperado:

```
P2P                  3.03M COP
C1 (CREG 174)        4.95M COP   (+63 %)
C2 (CREG 101 072)    4.58M COP   (+51 %)
```

El usuario solicitó una auditoría: *"¿estoy simulando mal? ¿hay algo
que deba calibrar del Modelo P2P original que no esté haciendo?"*. La
auditoría (Sprint 6.6-A, Fases A y B) descubrió **dos bugs en la
descomposición del paper**, no un fallo del modelo.

### Bug 1 — Asimetría de fórmula entre P2P y C1/C4

`comparison_engine._p2p_monetary_benefit` (y `_p2p_decomposed` del
script paper, que la replicaba) computa la prima del vendedor como:

```python
net[j] += income - baseline = (pi_star - pi_gb) × P_sold
```

Esta fórmula es **incremental sobre el contrafactual "vender todo a
bolsa al precio pi_gb"**. Omite:

1. **El revenue base del trade**: `pi_gb × P_sold`, que se cancela
   contra un baseline implícito.
2. **El residual surplus**: cuando el prosumidor tiene más excedente
   del que transa internamente, la función no contabiliza la venta a
   bolsa de ese residual.

Mientras tanto C1/C4 reportan **revenue total**:

```
NET_C1 = E_auto × pi_gs
       + E_t1 × (pi_gs - pi_C)
       + E_t2 × pi_bolsa[k]
```

Las dos métricas no son comparables aritméticamente.

**Verificación empírica (`scripts/audit_p2p_paper.py`, agosto 2025):**

```
delta total observado          = 958,255 COP
pi_bolsa_mean × E_surplus_total = 234.5 × 4085.6 = 958,255 COP
→ MATCH < 1 %, H1 confirmada.
```

### Bug 2 — Autoconsumo solo en horas con mercado

Adicionalmente, `_p2p_decomposed` calculaba el autoconsumo dentro del
loop sobre `p2p_results` con `if r.P_star is None: continue`. Las 523
horas (de 744) sin mercado P2P activo no contabilizaban autoconsumo.

Diferencia: ~961 K COP adicionales no contados.

**Total subreporte P2P en paper:** 1.92 M COP, lo cual explica el gap
3.03 M (buggy) vs 4.95 M (canónico) reportado por `audit_p2p_paper.py`.

## Decisión

Reescribir `scripts/run_paper_iter.py::_p2p_decomposed` con la **fórmula
canónica** simétrica con C1/C4:

```python
# Bug 2 fix — autoconsumo SIEMPRE (fuera del loop p2p_results):
for n in prosumer_ids:
    for k in range(T):
        autoconsumo[n] += min(G_klim[n,k], D[n,k]) × pi_gs[n,k]

# Mercado P2P (revenue completo + savings comprador):
for hora con r.P_star válido:
    for vendedor j:
        income_j = Σ pi_star[k] × P_sold[j,k]    ← revenue COMPLETO
        mercado[j] += income_j
    for comprador i:
        savings_i = (pi_gs - pi_star) × P_bought[i,k]
        mercado[i] += savings_i

# Bug 1 fix — residual surplus exportado a bolsa horaria:
for n in prosumer_ids:
    for k in range(T):
        residual_nk = max(G_klim[n,k] - D[n,k] - P_sold[n,k], 0)
        mercado[n] += residual_nk × pi_bolsa[k]
```

Resultado post-fix (agosto 2025, mismo dataset):

| Escenario | Pre-CAL-29 | Post-CAL-29 |
|---|---:|---:|
| P2P | 3.03 M | **4.81 M** |
| C1 (CREG 174) | 4.95 M | 4.95 M |
| C2 (CREG 101 072) | 4.58 M | 4.58 M |

**Narrativa nueva (defensible para el paper):** P2P está entre C1 y C2,
queda 2.9 % bajo C1 y 5.0 % sobre C2. A nivel agente: 3 de 5
instituciones (Udenar, HUDN, Cesmag) prefieren P2P sobre C1.

## Alcance limitado a paper

`comparison_engine._p2p_monetary_benefit` **NO se modifica en CAL-29**.
Razones:

1. La función es usada por toda la tesis (117/117 tests verdes
   asumen la fórmula incremental).
2. Cambiarla impactaría las métricas RPE en cap. 4 y 5 del manuscrito.
3. La auditoría regulatoria (CAL-7, CAL-9, CAL-10, CAL-13, CAL-15)
   y los hallazgos de cap. 5 se basan en los valores incrementales.

El fix engine queda planificado en **CAL-30** (Sprint 7 post-paper):
introducir un parámetro `mode={"premium", "canonical"}` con default
`"premium"` y migrar la tesis a `"canonical"` con validación completa
de tests + RPE.

## Consecuencias

**Positivas:**

- El paper reporta una narrativa **defendible y simétrica** entre P2P
  y los escenarios regulatorios.
- La descomposición **autoconsumo (offset común) vs venta excedentes
  (diferenciador)** ahora es real: el offset común es idéntico (3.6 M
  COP) en los 3 escenarios, validando la hipótesis del asesor (líneas
  414-462 de `Reunion0105.txt`).
- El test `test_c1_y_c2_tienen_autoconsumo_identico` ahora puede
  extenderse para incluir P2P (era falso pre-CAL-29).

**Negativas:**

- Dualidad temporal entre paper (canonical) y tesis (premium). Se
  documenta explícitamente en `Documentos/notas_modelo_tesis.md`
  §CAL-29 y se cita el plan CAL-30 para el fix engine.
- Tablas y figuras de Sprint 6.5 (ranking PV) deben re-ejecutarse con
  la nueva descomposición. Acción: ya re-ejecutado el smoke baseline;
  la tabla `outputs/paper/fig_pv_ranking_*.csv` debe regenerarse.

## Test plan

Nuevo `tests/test_cal29_p2p_canonical.py` (~4 tests):

1. **`test_autoconsumo_p2p_igual_a_c1_c2`**: tras la corrida del paper,
   los 3 escenarios reportan idéntico `Ahorro_autoconsumo_COP`.
2. **`test_autoconsumo_p2p_cuenta_horas_sin_mercado`**: en escenario
   sintético sin trades, P2P autoconsumo = total física = idéntico al
   no-P2P.
3. **`test_decomposed_canonica_incluye_residual`**: con surplus que
   excede el trade, el `mercado` incluye un componente
   `~ pi_bolsa × residual`.
4. **`test_canonica_match_audit_h1`**: replica el caso agosto-2025 y
   verifica que `delta = pi_bolsa_mean × E_surplus_total` (invariante
   H1 del audit).

## Referencias

- `Documentos/audit_p2p_decomposition.md` — auditoría completa.
- `scripts/audit_p2p_paper.py` — diagnóstico empírico reproducible.
- `scenarios/comparison_engine.py::_p2p_monetary_benefit` (líneas 444-510)
  — fórmula premium (no modificada).
- `scenarios/scenario_c1_creg174.py::run_c1_creg174` (líneas 215-218,
  235) — fórmula canónica de referencia.
- Plan `radiant-sleeping-eagle.md` §6.6.5 (Sprint 6.6-A audit).
