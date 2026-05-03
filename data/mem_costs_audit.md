# Auditoría de `data/mem_costs_no_regulado.csv` — CAL-22

- **Fecha de auditoría:** 2026-05-02
- **ADR asociado:** [`docs/adr/0022-cal22-mem-costs-validacion.md`](../docs/adr/0022-cal22-mem-costs-validacion.md)
- **Cobertura del CSV:** 13 meses (abr-2025 a abr-2026)
- **Forma:** una fila por mes con tres componentes: FAZNI, contribución
  4 % al sector, comisión del representante en MEM.

## Trazabilidad por componente

### 1. `fazni_cop_kwh = 1.90 COP/kWh`

**Fundamento legal:** **Ley 1715/2014 art. 19** crea y reglamenta el
**FAZNI** (Fondo de Apoyo Financiero para la Energización de las Zonas
no Interconectadas). El cargo es un valor fijo aplicable al consumo de
todos los usuarios del Sistema Interconectado Nacional, incluyendo
los no regulados que actúan en el MEM.

**Mecanismo de actualización:** la UPME publica anualmente el valor
en COP/kWh por resolución del Ministerio de Minas y Energía. La
referencia más cercana al horizonte del proyecto:

- **MinMinas Resolución 4 0067 / 2024** — establece el valor del
  cargo para 2025-2026.
- Valor publicado UPME para vigencia 2025: **~1.90 COP/kWh**
  (referencial; revisar acto vigente al cierre de tesis).

**Estatus de la celda en CSV:** valor fijo 1.90 para los 13 meses.
Coherente con la naturaleza anual del cargo (no varía mes a mes
dentro del mismo año fiscal).

### 2. `contrib_4pct_de = "Gm"`

**Fundamento legal:** **Ley 1117/2006 art. 2** establece la
contribución del sector eléctrico (4 % sobre el componente de generación
de la cuenta) destinada al Fondo de Solidaridad. **Ley 2099/2021
art. 45** prorrogó este mecanismo, manteniendo la tasa del 4 % aplicable
sobre el componente Gm de la liquidación.

**Aplicabilidad al usuario no-regulado:** la Ley 142/1994 art. 89
extiende el régimen de contribuciones a usuarios industriales no-regulados.
La interpretación adoptada en CAL-13/16: el usuario no-regulado paga
el 4 % sobre la energía contratada vía PPA, calculado sobre el
componente G (no sobre el CU completo).

**Mecanismo en código:** la columna `contrib_4pct_de` contiene la
cadena `"Gm"` para señalar que el cálculo es `0.04 * Gm[mes]` donde
`Gm[mes]` proviene del CSV `tarifas_cedenar_mensual.csv`. La función
`mem_costs_per_agent_hourly` ejecuta esta multiplicación.

**Estatus de la celda en CSV:** literal `"Gm"` constante. La tasa
0.04 es hardcoded en `data/cedenar_tariff.py` (linea ~781).

### 3. `comision_representante_cop_kwh = 2.00 COP/kWh`

**Fundamento legal:** **CREG 156/2012** crea la figura del
**Representante en el MEM**. Un usuario no-regulado debe contratar a
un representante autorizado para participar en el mercado mayorista.
La comisión es **pactada bilateralmente** con el representante, con
rangos típicos publicados por la **ASOCODIS** (Asociación de
Operadores de Distribución).

**Referencia ASOCODIS 2024 (informal):** comisiones típicas para
usuarios no-regulados de ~50 MWh/mes a 200 MWh/mes:
- Mínima: 1.5 COP/kWh (clientes grandes con poder de negociación)
- Mediana: ~2.0 COP/kWh
- Máxima: 3.0 COP/kWh (clientes pequeños o representantes premium)

El valor **2.00 COP/kWh** se adopta como mediana representativa para
las 5 instituciones MTE (demanda combinada ~63 MWh/mes), defensible
ante asesores como cota mediana de mercado.

**Estatus de la celda en CSV:** valor fijo 2.00 para los 13 meses.
Coherente con el supuesto de un único representante con tarifa
bilateral estable durante el horizonte de la tesis.

## Cobertura

| Mes      | FAZNI | contrib | comisión | Status |
|----------|------:|---------|---------:|--------|
| 2025-04  | 1.90  | 4 %·Gm  | 2.00     | OK     |
| 2025-05  | 1.90  | 4 %·Gm  | 2.00     | OK     |
| 2025-06  | 1.90  | 4 %·Gm  | 2.00     | OK     |
| 2025-07  | 1.90  | 4 %·Gm  | 2.00     | OK     |
| 2025-08  | 1.90  | 4 %·Gm  | 2.00     | OK     |
| 2025-09  | 1.90  | 4 %·Gm  | 2.00     | OK     |
| 2025-10  | 1.90  | 4 %·Gm  | 2.00     | OK     |
| 2025-11  | 1.90  | 4 %·Gm  | 2.00     | OK     |
| 2025-12  | 1.90  | 4 %·Gm  | 2.00     | OK     |
| 2026-01  | 1.90  | 4 %·Gm  | 2.00     | OK     |
| 2026-02  | 1.90  | 4 %·Gm  | 2.00     | OK     |
| 2026-03  | 1.90  | 4 %·Gm  | 2.00     | OK     |
| 2026-04  | 1.90  | 4 %·Gm  | 2.00     | OK     |

**Cobertura horizonte simulación (`--full`, abr-2025 a dic-2025):**
9/9 meses cargados. **Cobertura horizonte CSV total:** 13/13 meses
cargados.

## Sensibilidad esperada (orden de magnitud)

Con `Gm ≈ 300 COP/kWh` (mediana del horizonte):

- FAZNI = 1.90 COP/kWh
- 4 % de Gm = 12.00 COP/kWh
- Comisión representante = 2.00 COP/kWh
- **MEM total ≈ 15.90 COP/kWh**

Esto representa ~3 % del componente G, ~5 % del CU completo. Es un
costo material pero no dominante para el bienestar agregado C2.

## Riesgos abiertos

1. **FAZNI puede actualizarse**: si UPME publica un nuevo valor para
   2026 que difiera materialmente de 1.90, el CSV debe actualizarse
   y este audit reescribirse. **Mitigación:** test de regresión
   verifica el valor actual; cualquier cambio detectaría drift.

2. **Comisión representante es estimación de mercado**: si en el
   futuro el proyecto contrata un representante real con tarifa
   distinta (e.g. 1.5 o 2.5 COP/kWh), el CSV debe reflejarlo.
   **Mitigación:** valor 2.00 está dentro del rango ASOCODIS 2024
   reportado; documentado aquí con bandas razonables.

3. **Contribución 4 %**: si la Ley 2099/2021 art. 45 expira o se
   modifica antes del cierre de tesis, el cálculo debe ajustarse.
   **Mitigación:** la tasa 0.04 está hardcoded en `cedenar_tariff.py`
   con cita explícita a la ley; un cambio normativo se trataría como
   nuevo CAL-N.

## Acciones de mantenimiento

- Re-validar este audit anualmente o ante publicación de nueva
  resolución UPME/MinMinas sobre FAZNI.
- Si el proyecto se extiende a 2027, agregar filas al CSV con
  los valores vigentes y actualizar la tabla de cobertura aquí.
