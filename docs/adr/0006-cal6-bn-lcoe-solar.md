# 0006 — CAL-6: LCOE solar `b_n` sintetico vs real

- **Estado:** Accepted
- **Fecha de decision:** 2026-04-17
- **Actividad:** 1.1 / 1.2 (caracterizacion empirica) / 2.1 (modelo)
- **Archivos afectados:** `data/xm_prices.py` (modo real),
  `data/base_case_data.py` (modo sintetico)
- **Hallazgo de auditoria:** D2 (cerrado como discrepancia documentada)
- **Fuente:** `Documentos/notas_modelo_tesis.md` §7 CAL-6

## Contexto

Existe una **doble calibracion** de `b_n` (LCOE solar) segun el modo de
ejecucion. El hallazgo D2 de la auditoria encontro la discrepancia y
preguntaba si era un bug. Resolucion: no es bug, son unidades distintas.

| Modo | Fuente | Vector `b` | Unidad | Proposito |
|---|---|---|---|---|
| Sintetico | `base_case_data.py::B = SCALE × [3.93·52, 32, 47, 37, 0, 0]` | `[1245, 195, 287, 225, 0, 0]` | u.o. | Fidelidad exacta a `JoinFinal.m:40-43` (golden test) |
| Real (MTE) | `xm_prices.py::B_CALIBRATED` | 225 (homogeneo, 210 Cesmag) | COP/kWh | LCOE colombiano empirico |

## Decision

**Mantener la doble calibracion.** Modo sintetico: vector heterogeneo
fiel al MATLAB para validacion. Modo real: `b_n = 225 COP/kWh` homogeneo
(210 para Cesmag).

## Justificacion del homogeneo en modo real

1. Las 5 instituciones usan inversores **Fronius ≤ 100 kW**, mismo
   fabricante y clase. La diferencia entre LCOE individuales esta
   dominada por horas-sol equivalentes, **homogeneas en un radio < 2 km**.
2. El rango IRENA / UPME para solar distribuida pequena en Colombia
   2024-2025 es **200-250 COP/kWh**; 225 esta en la mediana.
3. Cesmag tiene un inversor distinto (no Fronius) → 210 COP/kWh
   diferenciado por ficha tecnica.
4. Los datos de capacidad FV por institucion estan marcados
   **PENDIENTE VERIFICAR CON ADMIN MTE** en
   `Inventario_Act_1_0.md:29-33`. Heterogeneizar antes de ese cierre
   introduciria falsa precision.

## Por que NO se reemplaza el homogeneo por el vector heterogeneo de JoinFinal en modo real

El vector MATLAB esta en **unidades de optimizacion** (el modelo
sintetico usa `pi_gs = 1250` adimensional), no en COP/kWh. Su traduccion
directa **no tendria sentido fisico** en el modo real.

## Consecuencias

- (+) El golden test contra `Bienestar6p.py` sigue siendo exacto en
  modo sintetico.
- (+) El modo real usa una calibracion empirica defendible para Colombia.
- (-) Cualquier nueva figura debe declarar explicitamente en que modo se
  genero (sintetico vs real).
- (Pendiente) Cuando MTE confirme las fichas tecnicas, se podra
  heterogeneizar por horas-sol equivalente reales.

## Estado

Hallazgo D2 cerrado como discrepancia documentada (no bug). Decision
defendible.

## Apendice — Bug fix 2026-05-06 (case-mismatch en lookup)

Durante la auditoria de parametros para el paper IEEE WEEF 2026 se
descubrio que la implementacion de `calibrate_b_parameters`
(`data/xm_prices.py:519-520`) tenia un bug de case-mismatch:

```python
# Codigo buggy (antes del fix):
b = [B_CALIBRATED.get(f"{n.lower()}_fronius",
     B_CALIBRATED["default_pasto"]) * adj for n in agent_names]
```

Para `agent_names = ['Udenar', 'Mariana', 'UCC', 'HUDN', 'Cesmag']`,
la expresion `n.lower()` produce las claves `'udenar_fronius'`, etc.
Pero las claves reales de `B_CALIBRATED` estan capitalizadas
(`'Udenar_fronius'`, `'Cesmag_inv'`, etc.). Las 5 busquedas fallaban y
caian al fallback `default_pasto = 220`. **La intencion de CAL-6
(Cesmag=210 por inversor distinto) nunca se ejecutaba**: los 5 agentes
obtenian `b = 220 × adj ≈ 235.7` uniforme.

### Sintoma observable

En `scripts/debug_convergence_h512.py` el equilibrio P_ji resulto
*perfectamente* simetrico (P0 = P_final dentro de 0.04% de variacion),
porque costos identicos producen asignacion uniforme P*[j,i] = D_i/J,
que coincide con la condicion inicial P0 de JoinFinal.m. La figura de
convergencia `fig_paper_convergence_h0512` panel (c) Power flows
mostraba lineas planas en lugar del transitorio visible en Chacon
Fig. 3a.

### Fix aplicado

Reemplazado el lookup por un dict explicito `INVERTER_BY_AGENT` que
matchea las claves reales:

```python
INVERTER_BY_AGENT = {
    "Udenar":  "Udenar_fronius",
    "Mariana": "Mariana_fronius",
    "UCC":     "UCC_fronius",
    "HUDN":    "HUDN_fronius",
    "Cesmag":  "Cesmag_inv",
}
b = [B_CALIBRATED.get(INVERTER_BY_AGENT.get(n, "default_pasto"),
                        B_CALIBRATED["default_pasto"]) * adj
     for n in agent_names]
```

Resultado del sanity check:

| Agente  | b (COP/kWh) |
|---|---:|
| Udenar  | 241.07 |
| Mariana | 241.07 |
| UCC     | 241.07 |
| HUDN    | 241.07 |
| Cesmag  | 225.00 |

Heterogeneidad Cesmag vs resto: 6.67%, exactamente lo que CAL-6
documentaba como intencion.

### Impacto en resultados anteriores

Las 16 figuras del paper y las Tablas I-III usaban implicitamente el
b uniforme. Como CAL-6 ya defendia b homogeneo `=225` mediana, el
delta numerico en Tabla III (welfare totales) es < 1% per CAL-2 /
CAL-5 inertia. La unica figura que se beneficia visualmente del fix
es `fig_paper_convergence_h0512` panel (c), que ahora muestra
transitorio P_ji genuino al perderse la simetria perfecta.

Verificado por `scripts/debug_convergence_h512.py` post-fix.

---

**Implementacion final 2026-05-10:** el fix queda confirmado en
`data/xm_prices.py:520+` con el dict `INVERTER_BY_AGENT`. Tambien
incluye un fix CAL-28b en `download_via_api` que evitaba que un
`UnicodeEncodeError` (caracteres no-ASCII en print bajo stdout cp1252)
fuera silenciosamente atrapado por `except Exception`.
