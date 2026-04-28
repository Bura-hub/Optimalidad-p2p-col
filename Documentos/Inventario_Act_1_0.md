# Inventario de Elementos y Requisitos de Datos

**Actividad 1.0 — Análisis de Optimalidad y Validación Regulatoria de Mercados P2P en Colombia**
Autor: Brayan S. Lopez-Mendez — Maestría en Ingeniería Electrónica, Universidad de Nariño, 2026.
Asesores: M.Sc. Andrés Pantoja, M.Sc. Germán Obando.

---

## A. Elementos comunes del sistema (P2P y C1–C4)

Los elementos descritos a continuación son compartidos por todos los modelos
de comparación. Las variables de demanda y generación se obtienen de los datos
empíricos del proyecto MTE (Medición de Tecnologías de Energía); los precios
de bolsa provienen del operador de red XM Colombia.

| Elemento | Descripción | Fuente de datos | Unidad | Alcance temporal |
|---|---|---|---|---|
| Nodos de la comunidad | 5 instituciones: Udenar, Mariana, UCC, HUDN, Cesmag | `MedicionesMTE/` | — | Jul 2025 – Ene 2026 |
| Horizonte de simulación | 5.160 horas continuas (215 días) | `data/xm_data_loader.py` (T_START, T_END) | h | 2025-07-01 / 2026-02-01 |
| Resolución temporal | 1 h (resampleada de mediciones a 2 min) | `data/xm_data_loader.py`, `_aggregate()` | h | — |
| Demanda por nodo *D*~n~ | Potencia activa total de medidores eléctricos | `MedicionesMTE/<nodo>/electricMeter/*.csv`, columna `totalActivePower` | kW | Por hora |
| Generación FV por nodo *G*~n~ | Potencia CA de inversores | `MedicionesMTE/<nodo>/inverter/*.csv`, columna `acPower` (W → kW) | kW | Por hora (cero nocturno) |
| Precio de venta red al usuario *π*~gs~ | CU mensual Cedenar (CREG 119/2007 + COT 101-028/2023) per-agente | `data/cedenar_tariff.py`, `data/tarifas_cedenar_mensual.csv` | COP/kWh | Mensual, abr-2025 → abr-2026 |
| Valor *π*~gs~ adoptado (CAL-8) | 797 oficial NT2 (Udenar, HUDN) · 956 comercial NT2 (Mariana, UCC, Cesmag) · 906 comunitario ponderado por demanda | `Documentos/notas_modelo_tesis.md` §CAL-8 · `data/cedenar_pdfs/` (13 PDFs respaldatorios) | COP/kWh | — |
| Valor *π*~gs~ legacy (deprecado, fallback) | 650 COP/kWh — solo si un mes no está cargado en el CSV | `data/cedenar_tariff.py` `DEFAULT_PI_GS_FALLBACK` | COP/kWh | — |
| Precio de compra red (*π*~gb~, precio de bolsa) | Precio de bolsa nacional horario XM | `data/precios_bolsa_xm_api.csv` | COP/kWh | Por hora |
| Precio de bolsa promedio adoptado | 221 COP/kWh (media aritmética Jul 2025 – Ene 2026) | `data/xm_prices.py` | COP/kWh | — |
| Parámetro LCOE *b*~n~ | Costo marginal de generación FV (calibrado) | `data/xm_prices.py`, `get_b_for_real_data()` | COP/kWh | — |
| Valor *b*~n~ adoptado | 235,71 COP/kWh (igual para los 5 nodos, calibración empírica) | `data/xm_prices.py` | COP/kWh | — |
| Capacidad FV Udenar | kWp instalados (DC y AC) | **PENDIENTE VERIFICAR CON ADMIN MTE** | kWp | — |
| Capacidad FV Mariana | kWp instalados (DC y AC) | **PENDIENTE VERIFICAR CON ADMIN MTE** | kWp | — |
| Capacidad FV UCC | kWp instalados (DC y AC) | **PENDIENTE VERIFICAR CON ADMIN MTE** | kWp | — |
| Capacidad FV HUDN | kWp instalados (DC y AC) | **PENDIENTE VERIFICAR CON ADMIN MTE** | kWp | — |
| Capacidad FV Cesmag | kWp instalados (DC y AC) | **PENDIENTE VERIFICAR CON ADMIN MTE** | kWp | — |
| Zona horaria | America/Bogota (UTC-5, sin horario de verano) | `data/xm_data_loader.py`, `tz_localize()` | — | — |
| Indice temporal | DatetimeIndex tz-aware America/Bogota | `data/xm_data_loader.py`, `MTEDataLoader.load()` | — | — |

**Nota sobre limpieza de datos (Actividad 3.1):** se aplica el protocolo
estándar sobre demanda y generación: eliminación de valores negativos,
detección de valores atípicos (Q75 + 5×IQR), interpolación lineal para brechas
de hasta 3 h y relleno hacia adelante/atrás para brechas de hasta 24 h. Las
horas restantes se completan con cero (generación nocturna).

---

## B. Requisitos de datos por escenario

La siguiente tabla especifica los parámetros adicionales requeridos por cada
modelo de comparación, los supuestos adoptados cuando los datos no están
disponibles y la referencia normativa que rige cada mecanismo.

| Escenario | Parámetros específicos | Supuestos | Referencia normativa |
|---|---|---|---|
| **P2P** (mercado dinámico) | *D*(N×T), *G*~klim~(N×T), *π*~gs~, *π*~gb~, *π*~bolsa~(T); parámetros λ~n~, θ~n~, η~n~, α~n~ del replicador | λ = 100, θ = 0,5, η = 0,1, α~prosumidor~ = 0,20, α~consumidor~ = 0,10 (calibración empírica, `tests/calibration_study.py`) | Chacón et al. (2025) [5]; propuesta tesis §VI.A–B |
| **C1** (CREG 174/2021) | *D*(N×T), *G*~klim~(N×T), *π*~gs~, *π*~bolsa~(T), etiquetas de período de facturación (mes) | Período de facturación mensual; excedente neto a precio de bolsa promedio ponderado del mes | Resolución CREG 174 de 2021 |
| **C2** (contrato bilateral PPA) | *D*(N×T), *G*~klim~(N×T), *π*~gs~, *π*~gb~, *π*~ppa~ | *π*~ppa~ = punto medio [*π*~gb~, *π*~gs~] (supuesto de negociación equitativa); reparto proporcional a la demanda de cada consumidor | Contrato privado entre partes; no existe marco CREG específico |
| **C3** (exposición total a bolsa) | *D*(N×T), *G*~klim~(N×T), *π*~gs~, *π*~bolsa~(T) | Cada agente enfrenta el precio spot horario sin mecanismo de balance | XM — Reglamento de operación (mercado mayorista) |
| **C4** (CREG 101 072/2025 — AGRC) | *D*(N×T), *G*~klim~(N×T), *π*~gs~, *π*~bolsa~(T), PDE(N), *capacity*(N) (kW instalados) | PDE calculado proporcional a capacidad instalada; modo `pde_only` (Tabla I propuesta); capacidad total ≤ 100 kW; relación cap.~máx~/cap.~mín~ ≤ 10×; comercializador único de respaldo | Decreto 2236 de 2023; Resolución CREG 101 072 de 2025; Resolución CREG 101 066 de 2024 |

### Observaciones sobre datos faltantes

1. **Capacidad FV instalada** (`capacity` en C4): los ponderadores PDE se
   calculan de forma proporcional a la capacidad instalada de cada nodo. Al
   no disponerse de los kWp reales, se aproxima la capacidad con la
   generación pico horaria observada en `MedicionesMTE/`. Esta aproximación
   debe ser reemplazada por los valores de placa una vez se confirmen con el
   administrador del proyecto MTE. Los campos marcados
   **PENDIENTE VERIFICAR CON ADMIN MTE** en la Tabla A requieren esta
   información.

2. **Precio PPA** (C2): el contrato bilateral supone un precio fijo pactado al
   inicio del período. Al no existir un acuerdo contractual documentado para
   las 5 instituciones, se adopta el punto medio entre *π*~gb~ y *π*~gs~ como
   referencia neutral. El análisis de sensibilidad SA-PPA barre este parámetro
   en el rango [*π*~gb~, *π*~gs~] para cuantificar su influencia.

3. **Irradiancia solar**: los datos de las estaciones meteorológicas
   (`weatherstation/`) están disponibles para los 5 nodos pero no se utilizan
   directamente en el modelo base; se reservan para calibración del parámetro
   *b*~n~ y para análisis de generación potencial en Actividad 1.1.

---

*Documento generado el 2026-04-16. Actualizar cuando se obtengan datos
físicos de capacidad FV confirmados por el administrador MTE.*
