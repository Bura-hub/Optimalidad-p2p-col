# Auditoría P2P decomposition vs C1/C2 (Sprint 6.6-A, 2026-05-02)

**Disparador (usuario):** *"Antes de continuar me parece importante definir y realizar
una auditoria a por qué ahora tenemos tanta diferencia y desbeneficio al mercado P2P,
¿estoy simulando mal? ¿hay algo que deba calibrar del Modelo P2P original que no esté
haciendo?"*

**Caso bajo escrutinio (agosto 2025, post-CAL-25..28, capacity_proportional):**

| Escenario          | Total [M COP] | Δ vs P2P |
|--------------------|---------------|----------|
| P2P                |          3.03 |        — |
| C1 (CREG 174)      |          4.95 |  +63 %   |
| C2 (CREG 101 072)  |          4.58 |  +51 %   |

## Fase A — Comparación de fórmulas (lectura del código)

### C1 — `scenario_c1_creg174.run_c1_creg174` (líneas 215-218, 235)

```
E_auto       = Σ_k min(G[n,k], D[n,k])
E_permuted_1 = Σ_k surplus_t1[n,k]        (Tipo 1, hasta hora Hx)
E_tipo2      = Σ_k surplus_t2[n,k]        (Tipo 2, post-Hx)

savings  = E_auto × pi_gs + E_permuted_1 × (pi_gs - pi_C)
revenue  = Σ_k surplus_t2[k] × pi_bolsa[k]
NET_C1   = savings + revenue                         ← TOTAL revenue del excedente
```

### C4 / C2-paper — `scenario_c4_creg101072._run_c4_creg174_inheritance` (líneas 41-46)

```
savings_auto = Σ_k autoconsumo[n,k] × pi_gs[n,k]
savings_t1   = Σ_k permuta_t1[n,k]  × (pi_gs[n,k] - pi_C[n,k])
revenue_t2   = Σ_k excedente_t2[n,k] × pi_bolsa[k]
NET_C2       = savings_auto + savings_t1 + revenue_t2 ← TOTAL revenue del excedente
```

### P2P — `comparison_engine._p2p_monetary_benefit` (líneas 444-510)

```
autoconsumo_n         = Σ_k min(G[n,k], D[n,k]) × pi_gs[n,k]
prima_vendedor_j      = Σ_k (pi_star[k] - pi_gb) × P_sold[j,k]    ← INCREMENTAL
ahorro_comprador_i    = Σ_k (pi_gs[i,k] - pi_star[k]) × P_bought[i,k] ← INCREMENTAL
NET_P2P               = autoconsumo + prima + ahorro              ← INCOMPLETO
```

## Hallazgo principal — H1 confirmada

**C1/C4** computan `net_benefit = ahorro_total - costo_post_solar` (relativo a baseline
"sin solar"). Captura la **revenue completa** del excedente: Tipo 1 vale
`E_t1 × (pi_gs - pi_C)` y Tipo 2 vale `E_t2 × pi_bolsa[k]`.

**P2P** computa `net_benefit = autoconsumo + ganancia_incremental_del_trade`.
La fórmula `(pi_star - pi_gb) × P_sold` representa la **prima sobre el contrafactual
"vender todo a bolsa"**. Tiene dos omisiones:

1. **El base revenue del trade**: `pi_gb × P_sold` (lo que el vendedor recibiría
   "vendiendo a bolsa"). Esto se cancela contra un baseline implícito que NO se
   añade al P2P final.
2. **El residual surplus**: cuando un prosumidor tiene más excedente del que
   transa en el mercado P2P, la formula NO contabiliza la venta a bolsa de
   ese residual. La función `_p2p_monetary_benefit` solo itera sobre
   `r.seller_ids`/`r.buyer_ids` con `r.P_star[idx, :]` (volumen transado).

### Manifestación numérica (caso 1 hora con G=10, D=2, surplus=8)

Suponer pi_gs=700, pi_gb=234, pi_C=100, pi_star_promedio=400. El P2P transa 5 kWh
de los 8 surplus; el residual 3 kWh sale a bolsa (asumido pi_bolsa=234 ≈ pi_gb).

| Concepto                     | C1 / C4 (Tipo 2 if hx=0) | P2P actual | P2P canónico (con residual) |
|------------------------------|--------------------------|------------|------------------------------|
| Autoconsumo                  | 2 × 700 = 1400            | 1400       | 1400                         |
| Surplus traded               | (Tipo 2) 5 × 234 = 1170   | (400-234) × 5 = 830 | 5 × 400 = 2000      |
| Surplus residual             | (Tipo 2) 3 × 234 = 702    | **0**      | 3 × 234 = 702                |
| **NET**                      | **3272**                  | **2230**   | **4102**                     |

P2P actual reporta **31 % menos** que la cifra canónica. La diferencia
corresponde exactamente a `(pi_gb × P_sold) + (pi_bolsa × P_residual)`.

### Por qué el bug no se observaba en la tesis (M1 totalizador)

Con cobertura ~19 % (M1 totalizador), el surplus residual es pequeño:
mayoría de horas son deficitarias y P2P solo trata pequeños excedentes
puntuales. La omisión `pi_bolsa × P_residual` es despreciable.

Con cobertura 96 % (CAL-28 sub-medidores), surplus residual es **dominante**:
la omisión equivale a cientos de miles de COP. **El bug solo es visible en
escenarios alta cobertura**, lo cual coincide con el síntoma reportado por
el usuario al activar CAL-28.

## Hipótesis secundarias (a verificar en Fase B)

| Hipótesis | Probabilidad post-Fase A |
|-----------|--------------------------|
| H1 — Asimetría de descomposición | **Confirmada** (lectura código) |
| H2 — Excedente residual al spot vs AGPE | Moderada (ver Fase B) |
| H3 — Convergencia Stackelberg con cob 96% | Baja (parámetro independiente) |
| H4 — Calibración `b` con sub-medidores | Moderada (D ~5× menor con CAL-28) |
| H5 — `pi_gs` escalar vs matriz en `correr_p2p` | Baja (homogéneo CAL-25) |
| H6 — Baselines distintos | Baja (todos contra "sin solar") |

## Fase B — Plan de diagnóstico

`scripts/audit_p2p_paper.py` debe imprimir, por escenario y por agente:

1. **Energía** [kWh]:
   - `E_auto`, `E_surplus_total`, `E_surplus_traded`, `E_surplus_residual`,
     `E_grid_export`, `E_grid_import`
2. **Monetario** [COP]:
   - `R_auto`, `R_surplus_traded`, `R_surplus_residual`,
     `R_total_canonical = R_auto + R_traded + R_residual`,
     `R_total_engine = comparison_engine.net_benefit[n]`,
     `delta = R_total_canonical - R_total_engine`
3. **Sweep iters** ∈ {2, 5, 10}:
   - Si `|net(iters=10) - net(iters=2)| / |net(iters=2)| > 1 %`, escalar default.
4. **Sanity check b**:
   - `b_cal[n] / D.mean(n)` debe estar en [0.5, 5].

## Fase C — Decisión sobre fix

Ya con H1 confirmada en lectura, el fix mínimo es **modificar `_p2p_monetary_benefit`
para incluir la revenue completa del trade y el residual**. Dos opciones:

**Opción A — Engine-level fix (toca tesis):**
```python
# En _p2p_monetary_benefit: cambiar
net[j] += income - baseline
# por
net[j] += income                                          # revenue del trade
# y añadir aparte el residual surplus revenue:
for n in prosumer_ids:
    for k in range(T):
        residual = max(G_klim[n, k] - D[n, k] - sum_traded_k[n, k], 0)
        net[n] += residual * pi_bolsa[k]
```

Validar 117/117 tests + RPE post-CAL-23 ± 0.5%. Si rompe, parar e informar.

**Opción B — Paper-level fix (solo `run_paper_iter._p2p_decomposed`):**

Reescribir la descomposición P2P del paper para sumar los términos faltantes
sin tocar el engine. La tesis sigue con la fórmula incremental (documentada en
docstring "Filosofía A").

**Recomendación:** Opción A. La fórmula actual de `_p2p_monetary_benefit` no
es "savings + revenues" como dice el docstring, es "savings + (revenues -
bolsa_baseline)". Documentar el cambio en `docs/adr/0029-cal29-p2p-revenue-completa.md`.

## Acciones después del fix

1. Re-ejecutar Sprint 6.5 (ranking PV) con el nuevo `_p2p_monetary_benefit`.
2. Actualizar tablas/figuras en `outputs/paper/`.
3. Si P2P recupera competitividad (ranking cambia): actualizar narrativa del paper.
4. Si P2P sigue debajo: documentar como hallazgo regulatorio defensible
   en CAL-29.

## Resultados empíricos Fase B (`scripts/audit_p2p_paper.py`, 2026-05-02)

**Output ejecutivo (agosto 2025, post-CAL-25..28):**

| Concepto | Valor |
|---|---|
| `delta` total observado | **958,255 COP** |
| `pi_bolsa_mean × E_surplus_total` predicho | **958,255 COP** |
| MATCH | < 1 % (exacto a redondeo) |

**H1 CONFIRMADA EMPÍRICAMENTE.** El delta exacto coincide con el faltante
predicho por análisis de fórmula.

**Comparación de NETs corregidos:**

| Escenario | Engine (actual) | Canónico (post-fix) |
|---|---|---|
| P2P | 3,989,374 | **4,947,629** |
| C1 (CREG 174) | 4,950,443 | 4,950,443 |
| C2 (CREG 101 072) | 4,577,608 | 4,577,608 |

**P2P canónico ≈ C1 (diferencia 2,814 COP, 0.1 %).** El "desbeneficio P2P"
del 38 % era un artefacto de la fórmula incremental. Con la fórmula
canónica, P2P y C1 son indistinguibles dentro del margen numérico.

### Segundo bug detectado (paper script)

Adicional a H1, se encontró un segundo bug en `run_paper_iter._p2p_decomposed`:

```python
for k_local, r in enumerate(p2p_results):
    if r.P_star is None:
        continue       # ← ESTE continue salta el autoconsumo en horas inactivas
    for n in prosumer_ids:
        auto_kn = ...
```

**Efecto:** las 523 horas (de 744 en agosto) sin mercado P2P activo no
contabilizan autoconsumo. Diferencia: ~961 K COP adicionales no contados.

**Total bugs paper:**
- Bug 1 (engine + paper): residual surplus omitido → -958 K COP
- Bug 2 (paper only): autoconsumo solo en horas activas → -961 K COP
- Total subreporte P2P en paper: **-1,919 K COP**, lo cual explica la cifra
  reportada 3.03M vs canónica 4.95M.

### Hallazgos secundarios

**H4 (calibración `b`):** ratio b/D.mean por agente: 73-234. Todos fuera
del rango [0.5, 5]. `b_cal=235.71` calibrado sobre M1 totalizador (D ~10×
más alto). Con CAL-28 sub-medidores, b está estructuralmente mal-calibrado.
**No afecta directamente la magnitud de net_benefit** (la calibración de b
afecta el equilibrio Stackelberg, no la formula post-equilibrio), pero sí
puede afectar dinámica de oferta y por tanto pi_star. Recalibración pendiente
(Sprint Phase C si hay tiempo).

**H3, H5, H6:** no se ejecutaron (H1 + bug-2 explican el 100 % del gap).

## Plan de fix consolidado (Fase C)

### Fix 1 — Engine `_p2p_monetary_benefit` (impacto tesis, riesgo alto)

Añadir el residual surplus revenue:
```python
# Después del loop sobre results, añadir loop sobre prosumer_ids:
for n in prosumer_ids:
    surplus_total_n = np.maximum(G_klim[n, :] - D[n, :], 0.0)
    # Restar lo que el agente vendió por P2P (P_sold_n[k] por hora)
    P_sold_n = np.zeros(T)
    for k_local, r in enumerate(results):
        if r.P_star is None or n not in (r.seller_ids or []):
            continue
        idx = r.seller_ids.index(n)
        P_sold_n[k_local] = float(r.P_star[idx, :].sum())
    residual_n = np.maximum(surplus_total_n - P_sold_n, 0.0)
    net[n] += float(np.dot(residual_n, pi_bolsa))  # residual a bolsa horaria
    # Y el income del trade ya no va como "income - baseline" sino como income completo:
    # (cambio en el loop seller arriba)
```

**Impacto esperado:** todos los net_benefit P2P aumentan en `pi_bolsa_mean ×
E_surplus_total / N_agentes`. RPE P2P-vs-C4 cambia significativamente
(sube ~10-30 % según dataset).

**Validación obligatoria (gate seguridad):**
1. `pytest tests/ -q` — 117/117 deben pasar.
2. `python main_simulation.py --data real` — RPE post-fix vs post-CAL-23
   debe ser DEFENSIBLE (puede cambiar, pero el cambio debe estar
   documentado en ADR-29 con rationale).
3. Tests específicos que comparan valores numéricos pueden requerir
   actualización (ya estaban probando los valores buggy).

### Fix 2 — Paper script `_p2p_decomposed` (impacto solo paper, riesgo bajo)

Mover el loop de autoconsumo FUERA del loop sobre `p2p_results`:
```python
# Autoconsumo: SIEMPRE (no depende de si hay mercado P2P en esa hora)
for n in prosumer_ids:
    for k in range(T):
        auto_kn = float(min(G_klim[n, k], D[n, k]))
        autoconsumo_per_agent[n] += auto_kn * float(pi_gs_v[n, k])

# Mercado P2P (premium + savings) y residual surplus:
for k_local, r in enumerate(p2p_results):
    if r.P_star is None:
        continue
    # ... (lógica actual de premium/savings)

# Residual surplus per agent (vendido a bolsa)
for n in prosumer_ids:
    # similar al engine fix
    mercado_per_agent[n] += residual_n.dot(pi_bolsa)
```

### ADR a redactar

`docs/adr/0029-cal29-p2p-revenue-completa.md`:
- Status: **Proposed** (cambia métricas reportadas en tesis)
- Decisión: cambiar `_p2p_monetary_benefit` para incluir revenue completo
  del trade + residual surplus al precio bolsa horario.
- Rationale: la fórmula previa era "incremental sobre baseline bolsa", no
  "savings + revenues" como decía el docstring. Asimétrica con C1/C4.
- Impacto: net_benefit P2P sube ~`pi_bolsa × surplus_total`. RPE re-medido.
- Test plan: nuevo `tests/test_cal29_p2p_canonical.py` valida la fórmula
  canónica sobre datos sintéticos donde la respuesta esperada es analítica.
