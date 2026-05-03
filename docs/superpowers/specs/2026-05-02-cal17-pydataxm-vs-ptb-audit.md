# CAL-17 — Auditoria pydataxm vs PTB oficial XM

- **Fecha de inicio:** 2026-05-02
- **Actividad:** 2.1 (modelo P2P) — capa de datos
- **ADR objetivo:** [`docs/adr/0017-cal17-pydataxm-vs-ptb-audit.md`](../../adr/0017-cal17-pydataxm-vs-ptb-audit.md)
- **Origen del trabajo:** follow-up explicito declarado en
  [ADR-0014 §"Riesgos abiertos"](../../adr/0014-cal14-creg101066-pes-ceiling.md)

## Contexto

El cache horario `data/precios_bolsa_xm_api.csv` se construye a partir de
`pydataxm.ReadDB().request_data("PrecBolsNaci", "Sistema", ...)`. La
metrica `PrecBolsNaci` corresponde al **Precio de Bolsa Nacional** (PB),
no al **Precio de Transacciones en Bolsa** (PTB) post-OEF.

ADR-0014 documento un "gap del 35 %" en ene-2026 entre el cache y el
PB_PROM oficial. La auditoria de esta spec verifica ese numero y decide
la politica de correccion.

## Hipotesis a falsar

H0: El cache `precios_bolsa_xm_api.csv` reproduce el PB_PROM oficial XM
con una desviacion < 10 % en cada uno de los 7 meses del horizonte
(jul-2025 a ene-2026). De ser asi, no se requiere correccion numerica
del cache.

H1: La media aritmetica mensual del cache difiere del PB_PROM oficial
(media ponderada por demanda) en una fraccion explicada por la
diferencia metodologica (sin error sistematico de la metric API).

## Metodologia

1. Cargar el cache horario (5160 h, sin techo PES) via `get_pi_bolsa`.
2. Computar la media aritmetica mensual.
3. Comparar contra `PB_OFFICIAL_PROM_MES` extraido de informes mensuales
   XM en `xm.com.co/noticias/...` y sheet `Precios` de
   `03_Informe_Precios_y_Transacciones_MM_YYYY.xlsx` en
   `sinergox.xm.com.co`.
4. Calcular delta absoluto y porcentual mes a mes.
5. Reportar meses fuera de tolerancia (default 10 %).

## Hallazgos (ejecutado 2026-05-02)

Output del script `scripts/audit_pydataxm_full_horizon.py`:

| mes     | cache_mean | oficial | delta_abs | delta_pct | fuera_tol |
|---------|-----------:|--------:|----------:|----------:|:---------:|
| 2025-07 |     133.39 |  138.36 |     -4.97 |     3.59% |    No     |
| 2025-08 |     238.25 |  251.50 |    -13.25 |     5.27% |    No     |
| 2025-09 |     295.05 |  292.65 |     +2.40 |     0.82% |    No     |
| 2025-10 |     189.93 |  176.90 |    +13.03 |     7.37% |    No     |
| 2025-11 |     207.37 |  234.87 |    -27.50 |    11.71% |  **Si**   |
| 2025-12 |     275.02 |  278.83 |     -3.81 |     1.37% |    No     |
| 2026-01 |     218.46 |  213.00 |     +5.46 |     2.56% |    No     |

- **6/7 meses** dentro de tolerancia 10 %.
- **1/7** (nov-2025) marginalmente fuera (-11.71 %).
- Delta medio firmado: **-1.81 %** (sin sesgo sistematico).
- Maxima desviacion: **11.71 %**, no 35 %.

## Reconciliacion del "gap del 35 %" del ADR-0014

ADR-0014 lineas 91-95 afirma: *"gap de 35 % observado en ene-2026 (cache
218.5 vs PB_PROM oficial 213.0)"*. La aritmetica `(218.5-213.0)/213.0`
da **+2.58 %**, no 35 %. El numero original es un **error de redaccion**.

Origen probable del error: comparar el cache con `XM_MONTHLY_REAL["2026-01"] = 220.0`
(estimado provisional) durante la auditoria preliminar de CAL-14, sin
notar que ese valor era un placeholder no derivado del informe oficial.
La metrica real de pydataxm `PrecBolsNaci` esta dentro de tolerancia.

## Decision (resumida — ver ADR-0017 para forma completa)

**No aplicar correccion numerica al cache `precios_bolsa_xm_api.csv`.**

Justificaciones:

1. La diferencia entre media aritmetica del cache y media ponderada por
   demanda del informe XM es **metodologica**, no una falla de la API.
2. El sesgo medio (-1.81 %) es despreciable y no reorientaria
   sistematicamente las conclusiones de la tesis.
3. El unico mes fuera de tolerancia 10 % (nov-2025) sigue dentro del
   limite 15 % del test de regresion existente
   (`test_capped_monthly_means_match_official_within_tolerance`).
4. Aplicar una correccion lineal (`scale = oficial / cache_mean`)
   distorsionaria la serie horaria sin justificacion regulatoria.

Acciones derivadas:

a. Actualizar `data/xm_prices.py::XM_MONTHLY_REAL` con los valores
   **oficiales verificados** (reemplazar estimados dic-2025 = 200 y
   ene-2026 = 220 por 278.83 y 213.00 respectivamente).
b. Corregir la afirmacion del "35 % gap" en ADR-0014 con un post-script
   `> Nota CAL-17 (2026-05-02):` aclarando que el numero original fue
   un error y referenciando este ADR.
c. Anadir test de regresion `test_cal17_xm_audit_within_tolerance` que
   asegure que el cache se mantiene dentro de tolerancia 15 % vs PB_PROM
   oficial en cualquier corrida futura.

## Plan de implementacion

| Paso | Accion | Archivo |
|------|--------|---------|
| 1 | Crear ADR-0017 (Accepted) | `docs/adr/0017-cal17-pydataxm-vs-ptb-audit.md` |
| 2 | Actualizar `XM_MONTHLY_REAL` con valores oficiales | `data/xm_prices.py:39-49` |
| 3 | Anadir post-script CAL-17 al ADR-0014 | `docs/adr/0014-cal14-creg101066-pes-ceiling.md` |
| 4 | Test de regresion CAL-17 | `tests/test_cal17_xm_audit.py` |
| 5 | Documentar en `Documentos/notas_modelo_tesis.md` §CAL-17 | (Sprint 1.3) |
| 6 | Sembrado Ruflo entrada `0017-cal17-pydataxm-vs-ptb-audit` | `scripts/seed_ruflo_adr.py` (Sprint 1.3) |
| 7 | Actualizar indice `docs/adr/README.md` con fila ADR-0017 | `docs/adr/README.md` |

## Out-of-scope

- Implementar `min(PB, PTB)` para aproximar el efecto OEF: ya cubierto
  por CAL-14 (techo PES).
- Cambiar la metric `PrecBolsNaci` por otra: candidatos
  `PrecioTransaccionBolsa` no aparecen en `inventario_metricas` actual
  de pydataxm (verificado en download_via_api).
- Ajuste por demanda horaria real: requiere descargar serie horaria de
  demanda XM, fuera del alcance de esta auditoria.

## Tests

`tests/test_cal17_xm_audit.py`:

1. `test_audit_script_runs_without_errors` — el script termina con
   exit_code in {0, 1} (1 si hay meses fuera tolerancia, esperado).
2. `test_cache_within_15pct_of_official_per_month` — invariante de
   tolerancia 15 % en cualquier corrida (incluido nov-2025).
3. `test_signed_mean_delta_under_5pct` — sin sesgo sistematico
   (|mean(delta_pct_signed)| < 5 %).
4. `test_xm_monthly_real_matches_audit_official` — `XM_MONTHLY_REAL`
   queda sincronizado con `PB_OFFICIAL_PROM_MES` del script de auditoria.

## Riesgos

- Si la API XM cambia de metrica o devuelve datos provisionales para
  meses recientes (e.g., ene-2026), el invariante de 15 % podria romper.
  Mitigacion: el test detecta y reporta el delta, no oculta la
  divergencia. CAL-N futuro auditaria si es persistente.

## Referencias

- ADR-0014 (CAL-14): techo CREG 101 066/2024.
- Informes mensuales XM: `xm.com.co/noticias/{8119,8184,8442,8584,8759}`
- Sinergox sheets: `sinergox.xm.com.co/2025/{09,12}/03_Informe_Precios_y_Transacciones_*.xlsx`
- pydataxm: `github.com/EquipoAnaliticaXM/API_XM`
