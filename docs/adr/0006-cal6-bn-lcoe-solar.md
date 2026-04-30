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
