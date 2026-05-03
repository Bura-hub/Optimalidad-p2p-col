# CAL-15 — C4 (CREG 101 072 / Decreto 2236) hereda Tipo 1 / Tipo 2 + Cvm de CREG 174

- **Fecha:** 2026-05-01
- **Autor:** Brayan S. Lopez-Mendez
- **Etiqueta:** CAL-15
- **Relacionado:** ADR-0010 (CAL-10b.2 — Cvm puro en C1), ADR-0009 (CAL-9 — pi_gs (N,T)), ADR-0014 (CAL-14 — techo PES, en flight)
- **Memoria semántica:** `tesis-p2p / cal_15_c4_tipo_1_2_cvm`

## Contexto

CAL-9 promovió `pi_gs` a matriz `(N, T)` y CAL-10b.2 fijó la decisión
regulatoria de descontar **únicamente `Cvm,i,j`** (no COT, no Rm) en la
permuta Tipo 1 del escenario C1, por literalidad de la CREG 174/2021
art. 25. C4 (AGRC bajo Decreto 2236/2023 + CREG 101 072/2025) quedó al
margen de esa corrección y conserva tres brechas regulatorias:

1. **Componente Cvm no descontado en créditos PDE.** El art. 4 del
   Decreto 2236/2023 establece que cada miembro AGRC se liquida bajo el
   marco de "Generador Distribuido y AGPE" — es decir, hereda CREG 174.
   La CREG 101 072/2025 no introduce un régimen de costo distinto: la
   energía del crédito PDE que sustituye un retiro de red atraviesa la
   misma frontera comercial y el mismo medidor bidireccional que la
   permuta CREG 174. Por linealidad regulatoria (art. 25 CREG 174) el
   comercializador retiene `Cvm,i,j` sobre esa permuta administrativa.
   Pre-CAL-15 valoraba créditos PDE a `pi_gs` completo
   (`scenario_c4_creg101072.py:166`), igual que C1 pre-CAL-10.

2. **Tratamiento monolítico de excedentes — sin distinción Tipo 1 / Tipo 2.**
   El modelo actual:

   ```python
   community_surplus = max(0, total_gen - total_dem)
   credits_k          = pde * community_surplus
   ```

   captura sólo el **neto comunitario hora a hora**. Cuando hay
   inyección y retiro simultáneos (un miembro genera mientras otro
   demanda), el neto puede ser cero aunque haya intercambio real a
   través de la frontera comunitaria. La permuta intracomunitaria
   (Tipo 1) y la exportación residual (Tipo 2) coexisten en cada hora;
   sólo el primer rubro es elegible al régimen de permuta CREG 174,
   sólo el segundo se valora a `pi_bolsa[k]` horario.

3. **Modo `pde_only` por defecto silencia la venta a bolsa.** El
   `comparison_engine.py:182` invoca C4 con `mode="pde_only"`, lo que
   deja `surplus_sell = 0` aunque exista exportación residual. El
   escenario AGRC pierde la mecánica completa que el usuario describe
   como rival a vencer del P2P (vender excedente barato + comprar
   déficit caro en la misma hora). El modo `pde_plus_residual_export`
   ya implementado nunca se ejecuta.

## Decisión regulatoria

**C4 hereda CREG 174/2021 art. 25** (vía Decreto 2236/2023 art. 4 y
CREG 101 072/2025 art. 5). El componente que se descuenta es
**`Cvm,i,j`** puro, sin COT, alineado con la corrección de literalidad
ya aplicada a C1 en CAL-10b.2.

Reglas operativas:

1. **Permuta intracomunitaria (Tipo 1 hora a hora)**:
   energía del crédito PDE que efectivamente compensa un retiro del
   miembro receptor → valorada a `(pi_gs[n,k] - Cvm[n,k])`.

2. **Exportación residual (Tipo 2 hora a hora)**:
   energía del crédito PDE que **excede** el retiro del miembro receptor
   → valorada a `pi_bolsa[k]` horario.

3. **Compra residual a la red**:
   déficit del miembro que **excede** su crédito PDE → comprada a
   `pi_gs[n,k]`. No produce ahorro (es factura ordinaria); se contabiliza
   en `grid_cost` como diagnóstico, no se resta del beneficio neto
   (Filosofía A WEEF, igual que C1-C3).

4. **Autoconsumo individual previo**: la energía que cada miembro
   consume de sus propios paneles antes de inyectar al pool comunitario
   se valora a `pi_gs[n,k]` completo (no toca red ni medidor
   bidireccional). Asimetría idéntica a C1 (CAL-10).

## Algoritmo (hora a hora)

Sustituye la lógica `community_surplus = max(0, total_gen - total_dem)`
por el flujo de inyecciones individuales:

```python
for k in range(T):
    autoconsumo[n,k]  = min(G[n,k], D[n,k])      # local, a pi_gs
    surplus_ind[n,k]  = max(G[n,k] - D[n,k], 0)  # inyectado al pool
    deficit_ind[n,k]  = max(D[n,k] - G[n,k], 0)  # retiro de la red

    inyeccion_total[k] = sum(surplus_ind[:,k])   # va a la frontera com.

    # PDE distribuye administrativamente la inyección (no la neta)
    credit[n,k] = pde[n] * inyeccion_total[k]

    permuta_t1[n,k] = min(credit[n,k], deficit_ind[n,k])      # Tipo 1
    excedente_t2[n,k] = max(credit[n,k] - deficit_ind[n,k], 0) # Tipo 2
    grid_buy[n,k]     = max(deficit_ind[n,k] - credit[n,k], 0) # red

# Valoración (CAL-10b.2 inheritance)
savings_auto[n]   = sum_k autoconsumo[n,k]   * pi_gs[n,k]
savings_t1[n]     = sum_k permuta_t1[n,k]    * (pi_gs[n,k] - Cvm[n,k])
revenue_t2[n]     = sum_k excedente_t2[n,k]  * pi_bolsa[k]
grid_cost[n]      = sum_k grid_buy[n,k]      * pi_gs[n,k]   # diagnóstico

net_benefit[n] = savings_auto[n] + savings_t1[n] + revenue_t2[n]
```

**Conservación**: por construcción
`sum_n credit[n,k] = inyeccion_total[k]` y
`sum_n (permuta_t1[n,k] + excedente_t2[n,k]) = inyeccion_total[k]`.
La energía que sale de la frontera comunitaria nunca se duplica ni se
pierde.

**Inheritance del helper Cvm**: `component_c="auto"` reusa el contrato
de C1 (`scenarios/_pi_gs.as_component_c_array`):
- modo `"auto"` → `pi_C = pi_gs × C_FRACTION` (proporcional 13.85 %),
  fallback cuando no hay calendario mensual.
- matriz `(N, T)` → `cvm_per_agent_hourly(...)` desde
  `data/tarifas_cedenar_mensual.csv` (CAL-10b.2), con relleno de NaN al
  proporcional. Mismo helper que ya consume C1.
- `None` o `0.0` → comportamiento legacy pre-CAL-15 (sin descuento).

## Cambios concretos

### `scenarios/scenario_c4_creg101072.py`

- Firma extendida:
  ```python
  def run_c4_creg101072(D, G, pi_gs, pi_bolsa, pde,
                         capacity=None, max_capacity_kw=100.0,
                         component_c="auto",        # ← nuevo, contrato C1
                         mode="creg174_inheritance" # ← reemplaza pde_only
                         ): ...
  ```
- `mode="creg174_inheritance"` (default): nuevo algoritmo Tipo 1 / Tipo 2.
- `mode="pde_only"`: legacy, emite `DeprecationWarning` con apuntador a CAL-15.
- `mode="pde_plus_residual_export"`: legacy v2, mismo warning.
- Retorna por agente: `savings`, `pde_credits` (= `savings_t1`),
  `surplus_revenue` (= `revenue_t2`), `grid_cost`, `net_benefit`,
  `pde_weight`, más diagnóstico horario `inyeccion_total`,
  `permuta_t1`, `excedente_t2`.

### `scenarios/comparison_engine.py:181-183`

- Eliminar `mode="pde_only"`; pasar `component_c=component_c`
  (parámetro nuevo de `run_comparison`, default `"auto"`).

### `analysis/monthly_report.py:143-148`

- Pasar `component_c=cc_m` con la misma lógica de slicing que C1
  (líneas 126-129 ya implementan el slice).

### `main_simulation.py:840`

- Slice diario en sub-período: pasar `component_c="auto"` (sin
  calendario mensual asociado al slice). Eliminar `mode="pde_only"`.

### `analysis/feasibility.py:740`

- FA-3 retiro de participante: aplicar el mismo slicing condicional de
  CAL-9 al `component_c` (igual que CAL-10b.2 ya hizo para C1 — bug
  pendiente documentado en ADR-0010 anexo CAL-10b.2 §"Bug pendiente").
  CAL-15 cierra ese bug también.

## Tests nuevos (`tests/test_c4_creg101072.py`)

1. **Descuento Cvm en permuta**: con `component_c=200` constante y un
   caso donde `permuta_t1` es no nulo, verificar que
   `savings_t1 = E_permuta × (pi_gs − 200)`.
2. **Tipo 2 a pi_bolsa horario**: una hora con surplus comunitario sin
   demanda interna → `revenue_t2 = pde × surplus × pi_bolsa[k]` (no
   `pi_bolsa.mean()`).
3. **Conservación**: `sum_n (permuta_t1 + excedente_t2 + grid_buy_no_cubierto)
   = inyeccion_total + sum_n deficit_ind` por hora.
4. **Ejemplo del usuario** (descalce horario): A en viaje (D=0), B con
   carga pesada (D=10, G=0), planta comunitaria genera 10 kWh, PDE 50/50
   → A vende 5 a `pi_bolsa`, B compra 5 a `pi_gs` y permuta 5 a
   `(pi_gs − Cvm)`.
5. **Modo legacy `pde_only` emite DeprecationWarning** y produce
   `surplus_revenue = 0` (regression).
6. **Validación PDE inválido**: `validate_pde([0.4, 0.4])` lanza
   `ValueError`.
7. **Slicing en feasibility**: matriz `component_c (N, T)` con
   `mask = [m for m in range(N) if m != n]` se reduce correctamente.

## Alternativas consideradas

### A. Mantener `mode="pde_only"` como default y documentar el sesgo

Rechazada: contradice la directiva del usuario "hazlo según determine
la ley". El sesgo es estructural (afecta la magnitud de C4 y por ende
RPE P2P-vs-C4) y no se puede aislar como nota al pie.

### B. Cvm + COT (postura conservadora pre-CAL-10b.2)

Rechazada: ya corregida en C1 (CAL-10b.2) por verificación de literalidad
del art. 25. Aplicar Cvm+COT a C4 reintroduce la inconsistencia.

### C. Hx por miembro (algoritmo mensual, simétrico a C1)

Diferida a CAL-16 (eventual). El algoritmo hora-a-hora es **estricto
peor-caso para C4**: clasifica todo crédito PDE no compensado como
Tipo 2 (precio bolsa) sin esperar a que se acumule durante el mes.
La versión mensual con Hx daría un C4 ligeramente mejor (más Tipo 1).
Para la tesis esto **fortalece** el argumento P2P > C4: la cota inferior
de C4 ya muestra ineficiencia. Documentado en consecuencias.

## Consecuencias

- (+) C4 fiel a Decreto 2236/2023 + CREG 101 072/2025 + CREG 174/2021
  art. 25; literalidad consistente con C1 (CAL-10b.2).
- (+) Captura cuantitativamente la ineficiencia del PDE estático que el
  usuario describe (Sec. "rival a vencer"): la comunidad simultáneamente
  vende a `pi_bolsa` y compra a `pi_gs` cuando el descalce horario es
  alto.
- (+) Sin nuevas dependencias: reusa `cvm_per_agent_hourly` y
  `as_component_c_array` ya consolidados en CAL-10b.2.
- (+) Cierra bug pendiente documentado en ADR-0010 anexo CAL-10b.2
  §"Bug pendiente" sobre slicing en `analysis/feasibility.py`.
- (−) Beneficio neto de C4 cambia (esperado: caída de 1-3 % vs CAL-10b.2
  por descuento Cvm en permuta intracomunitaria; subida marginal por
  exportación Tipo 2 ahora contabilizada). Backup `outputs/*_pre_cal15_*`
  antes de re-correr `--full`.
- (−) Cambio en flow_breakdown: aparece "Excedente bolsa" no nulo en C4
  (antes era 0 por `pde_only`). REPORTE_AVANCES.md y figuras
  fig5_comparacion_regulatoria, fig6_ganancia_por_agente,
  fig13_desglose_flujos requieren regeneración.

## Estado

Pendiente de implementación.

| Validación | Pendiente |
|---|---|
| `pytest tests/ -q` permanece verde + 7 tests CAL-15 nuevos | ⏳ |
| `python main_simulation.py` (sintético) corre sin error | ⏳ |
| Δ C4 vs CAL-10b.2 documentado tras `--full --analysis` | ⏳ |
