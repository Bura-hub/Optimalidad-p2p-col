# 0014 — CAL-14: Techo CREG 101 066/2024 (PES) en pi_bolsa

- **Estado:** Accepted
- **Fecha de decision:** 2026-05-01
- **Actividad:** 3.x (validacion regulatoria)
- **Archivos afectados:** `data/xm_prices.py`,
  `data/precios_escasez_creg.csv`, `tests/test_creg101066_ceiling.py`,
  escenarios C1/C3/C4 (sin cambios en codigo, solo en datos recibidos)
- **Relacionado con:** [ADR-0010 CAL-10b](0010-cal10-creg174-tipo-1-2-componente-c.md),
  [ADR-0013 CAL-13](0013-cal13-c2-no-regulado.md)
- **Fuente:** `docs/superpowers/specs/2026-05-01-cal14-creg101066-pes-ceiling.md`,
  Resolucion CREG 101 066/2024,
  `Documentos/notas_modelo_tesis.md` §CAL-14

## Contexto

La metrica `PrecBolsNaci` que devuelve la API pydataxm es el **Precio de
Bolsa marginal de oferta**, no el **Precio de Transacciones en Bolsa
(PTB)** efectivo tras activacion de OEF. El cache
`data/precios_bolsa_xm_api.csv` contiene picos > 2000 COP/kWh para
agosto 2025 mientras el techo regulatorio absoluto del PTB (PES) era
898.02 COP/kWh ese mes. Ningun PTB liquidado supera PES.

Aplicar el escenario C3 (y los excedentes Tipo 2 de C1, surplus tras PDE
de C4) sobre la serie cruda sobreestima los ingresos del prosumidor en
horas extremas que en la practica regulatoria estan recortadas.

Verificacion cruzada del cache contra el sheet
`Comportamiento_PBNal_Horario` del Excel oficial XM
03_Informe_Precios_y_Transacciones (jul-2025 a ene-2026): PB del cache
excede sistematicamente PES en ~99 horas del horizonte (1.9% del total),
con max 2 224 COP/kWh en agosto 2025 vs PES = 898.02.

## Decision

Aplicar **PES** (Precio de Escasez Superior) como techo duro al precio
de bolsa horario en la capa de datos `data/xm_prices.py:get_pi_bolsa`.
Tabla mensual de PEI/PE/PES en `data/precios_escasez_creg.csv` con los
7 meses del horizonte verificados desde el sheet
`Comportamiento_PBNal_Horario` de los Excel oficiales XM.

`get_pi_bolsa(apply_ceiling=True)` queda como default — toda corrida
nueva refleja CREG 101 066 sin tocar callers. `apply_ceiling=False`
permite analisis contrafactual.

Nuevas funciones publicas:

- `load_creg_ceiling(t_start, t_end, level)` — carga la serie mensual.
- `apply_creg101066_ceiling(pi_bolsa, t_start, level, ...)` — aplica el
  techo hora a hora respetando vigencia regulatoria.
- `_print_ceiling_summary(diag)` — diagnostico humano por consola.

## Alternativas consideradas

1. **Recortar a PE (intermedio, ~660-746)** — mas conservador, recorta
   ~199 horas adicionales. Descartado: PES es el techo absoluto del PTB
   liquidado; recortar a PE introduce sesgo a la baja sin justificacion
   regulatoria directa.
2. **Recortar a PEI (inferior, ~330)** — descartado: PEI solo aplica
   cuando la planta marginal es de bajo costo variable, no es techo
   absoluto.
3. **Aplicar PEI/PE/PES selectivamente segun composicion del despacho**
   — descartado: requiere descargar el despacho diario de XM, fuera
   del alcance de la tesis.
4. **Aplicar el techo solo en C3** — descartado: el techo es propiedad
   del dato (`pi_bolsa`), no del escenario; aplicarlo solo en C3 deja
   C1-Tipo 2 y C4 inconsistentes con la regulacion vigente.

## Consecuencias

**Positivas**

- C1, C3 y C4 reflejan ingresos de bolsa coherentes con CREG 101 066/2024.
- La capa de datos garantiza el invariante regulatorio:
  `max(pi_bolsa) <= max(PES_horizonte)`.
- Comparacion P2P vs C3 deja de favorecer artificialmente a C3 en
  escenarios de escasez extrema.
- PEI y PE quedan disponibles en el CSV para analisis contrafactual sin
  modificar codigo.

**Negativas**

- Aproximacion: aplicar PES como cap duro ignora la composicion horaria
  del despacho OEF real (que recortaria a PEI o PE en horas con
  generacion abundante). Documentado en §CAL-14 de notas_modelo_tesis.md.
- Mantenimiento: cada mes que XM publique nuevos PEI/PE/PES hay que
  agregar fila al CSV.

**Riesgos abiertos**

- **CAL-17** (follow-up): auditoria de la metrica que devuelve pydataxm
  vs PTB oficial. El gap de 35 % observado en ene-2026 (cache 218.5 vs
  PB_PROM oficial 213.0) sugiere que la API podria estar entregando
  datos provisionales o una metrica distinta. CAL-15 ya esta asignado
  a C4 (CREG 101 072 / Decreto 2236) y CAL-16 a la descomposicion
  regulatoria del ahorro en C2; CAL-17 es el siguiente ID secuencial.

> **Nota CAL-17 (2026-05-02):** la auditoria efectuada en
> [ADR-0017](0017-cal17-pydataxm-vs-ptb-audit.md) demostro que el "gap
> del 35 %" enunciado arriba fue un **error de redaccion**: la
> aritmetica `(218.5 − 213.0) / 213.0` da +2.58 %, dentro de tolerancia
> 10 %. Las desviaciones reales del cache vs PB_PROM oficial son
> ≤ 11.71 % en todos los 7 meses del horizonte, con sesgo medio
> firmado de -1.81 % (no sistematico). Se decidio **no aplicar
> correccion** al cache; ver ADR-0017 para forma completa.
