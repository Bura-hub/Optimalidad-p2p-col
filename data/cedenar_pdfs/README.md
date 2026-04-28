# PDFs de tarifa Cedenar (mensuales)

Repositorio local de los PDFs oficiales del **Costo Unitario de Prestación
del Servicio de Energía Eléctrica** publicados por Cedenar S.A. E.S.P.,
calculados según la Res. CREG 119/2007 con COT por Res. CREG 101-028/2023.

Fuente: <https://scl.cedenar.com.co/Out/Tarifas/Tarifas.aspx>
(la página solo expone los últimos cuatro meses; los meses anteriores
deben solicitarse directamente a la empresa).

## Convención de nombres

`tarifa_YYYY-MM.pdf`

donde `YYYY-MM` es el **mes de aplicación** declarado en la portada del
PDF (no el mes de descarga). Ejemplos:

- `tarifa_2025-07.pdf` — vigente para consumos desde jul-2025.
- `tarifa_2026-04.pdf` — vigente desde el 21 de abril de 2026.

Si Cedenar publica un único PDF para varias fechas dentro del mes
(p. ej. ajustes intramensuales), conserva los dos archivos:

- `tarifa_2026-04a.pdf`, `tarifa_2026-04b.pdf`.

En la columna `fuente` del CSV se anota el archivo que respaldó cada fila.

## Cómo agregar un mes

1. Descargar el PDF desde la página de Cedenar (paginar para meses
   anteriores).
2. Guardarlo aquí siguiendo la convención de nombres.
3. Abrir `data/tarifas_cedenar_mensual.csv` y rellenar las filas del mes
   correspondiente (mínimo `(oficial, 2, cedenar)` y `(comercial, 2,
   cedenar)`; también NT1 y NT3 si aplica a alguna institución).
4. Actualizar la columna `fuente` con el nombre del PDF.
5. Verificar:
   ```
   python data/cedenar_tariff.py --t-start <inicio> --t-end <fin>
   ```
   El resumen debe mostrar el mes recién agregado en "Meses cargados en CSV".

## Estado actual

| Mes | PDF en carpeta | Filas en CSV |
|---|---|---|
| 2025-04 | `tarifa_2025-04.pdf` (pub. 21-abr-2025) | 10 filas |
| 2025-05 | `tarifa_2025-05.pdf` (pub. 21-may-2025) | 10 filas |
| 2025-06 | `tarifa_2025-06.pdf` (pub. 21-jun-2025) | 10 filas |
| 2025-07 | `tarifa_2025-07.pdf` (pub. 21-jul-2025) | 10 filas |
| 2025-08 | `tarifa_2025-08.pdf` (pub. 17-ago-2025) | 10 filas |
| 2025-09 | `tarifa_2025-09.pdf` (pub. 21-sep-2025) | 10 filas |
| 2025-10 | `tarifa_2025-10.pdf` (pub. 21-oct-2025) | 10 filas |
| 2025-11 | `tarifa_2025-11.pdf` (pub. 21-nov-2025) | 10 filas |
| 2025-12 | `tarifa_2025-12.pdf` (pub. 21-dic-2025) | 10 filas |
| 2026-01 | `tarifa_2026-01.pdf` (pub. 21-ene-2026) | 10 filas |
| 2026-02 | `tarifa_2026-02.pdf` (pub. 21-feb-2026) | 10 filas |
| 2026-03 | `tarifa_2026-03.pdf` (pub. 21-mar-2026) | 10 filas |
| 2026-04 | `tarifa_2026-04.pdf` (pub. 21-abr-2026) | 10 filas |

> Cobertura completa: 13 PDFs (abr-2025 → abr-2026) y 130 filas en el
> CSV. Trazabilidad cerrada para todo el horizonte de simulación
> MTE (2025-04-04 → 2025-12-16).

## Verificación rápida

```
python data/cedenar_tariff.py --t-start 2025-07-01 --t-end 2026-02-01
```

Debe reportar "Meses cargados en CSV: 7" y mostrar `pi_gs efectiva` en
~ 794 COP/kWh para oficial NT2 y ~ 953 COP/kWh para comercial NT2.
