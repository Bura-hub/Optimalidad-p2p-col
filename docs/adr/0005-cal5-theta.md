# 0005 — CAL-5: `theta = 0.5` (insensibilidad dinamica)

- **Estado:** Accepted (retroactivo)
- **Fecha de decision:** 2026-04
- **Actividad:** 2.1 (modelo P2P)
- **Archivos afectados:** `core/ems_p2p.py` (solo en `seller_welfare`,
  `buyer_welfare` para reporting)
- **Fuente:** `Documentos/notas_modelo_tesis.md` §7 CAL-5

## Contexto

Discrepancia entre versiones del codigo de Chacon:

- `JoinFinal.m` (dinamica RD): `theta = 0.5`
- `ConArtLatin.m` (solver estatico SLSQP): `theta = 10.0`

Ambas versiones usan `theta` con proposito distinto:

- En `JoinFinal.m`: parametro de la dinamica del replicador.
- En `ConArtLatin.m`: parametro del solver estatico de bienestar.

## Decision

Mantener `theta = 0.5` por consistencia con el modelo dinamico de
referencia (`JoinFinal.m`).

## Justificacion empirica

| theta | SC | SS |
|---:|---:|---:|
| 0.5 (JoinFinal) | 0.8692 | 0.8465 |
| 10.0 (ConArtLatin) | 0.8692 | 0.8465 |

`theta` **no afecta** `solve_sellers()` ni `solve_buyers()`. Solo
modifica los valores `Wj_total` y `Wi_total` que se exportan a la
hoja Excel de reporte. El equilibrio del juego es identico para ambos
valores.

## Consecuencias

- (+) Consistencia narrativa con la dinamica RD de Chacon.
- (=) Cualquier valor produce el mismo equilibrio de mercado.
- (-) Los numeros de "bienestar total" reportados dependen de la
  eleccion; documentar esto en la seccion de Metodos.

## Estado

Solo afecta reporting. Decision por consistencia.
