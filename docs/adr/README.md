# Architecture Decision Records — Tesis P2P

Registro de decisiones de modelado y calibracion de la tesis. Formato
MADR simplificado, idioma espanol academico.

Numeracion correlativa, sin reusar IDs incluso si una ADR se supersede.
Estado posibles: `Proposed | Accepted | Superseded | Deprecated`.

## Indice

| ID | Titulo | Estado | Fecha decision |
|---|---|---|---|
| 0001 | CAL-1: Iteraciones del juego Stackelberg (`stackelberg_iters=2`) | Accepted | 2026-04 |
| 0002 | CAL-2: Coeficiente de competencia entre compradores (`etha=0.1`) | Accepted | 2026-04 |
| 0003 | CAL-3: Fraccion de demanda flexible (`alpha_p=0.20`, `alpha_c=0.10`) | Accepted | 2026-04 |
| 0004 | CAL-4: Escalado del sistema ODE (`tau_buyers/tau_sellers=10`) | Accepted | 2026-04 |
| 0005 | CAL-5: Insensibilidad dinamica de `theta` | Accepted | 2026-04 |
| 0006 | CAL-6: LCOE solar `b_n` sintetico vs real (homogeneo 225 COP/kWh) | Accepted | 2026-04-17 |
| 0007 | CAL-7: Alternancia Stackelberg vs ODE conjunta | Accepted | 2026-04-17 |
| 0008 | CAL-8: Tarifa Cedenar mensual diferenciada (vector per-agente) | Accepted (parcial Superseded por 0009) | 2026-04-27 |
| 0009 | CAL-9: Tarifa pi_gs temporal mes a mes (matriz N×T) | Accepted | 2026-04-30 |
| 0010 | CAL-10: Excedentes Tipo 1 / Tipo 2 + componente C en C1 | Accepted | 2026-04-30 |
| 0011 | CAL-11: C2 PPA bilateral (modelo formal) | Accepted | 2026-04-30 |
| 0012 | CAL-12: C2 Front-of-Meter + peajes T+D+Cvm+PR+Rm+COT | Accepted | 2026-05-01 |
| 0013 | CAL-13: C2 alineado con marco no-regulado (Ley 143/1994) | Accepted (parcial Superseded por 0016) | 2026-05-01 |
| 0014 | CAL-14: Techo CREG 101 066/2024 (PES) en pi_bolsa | Accepted | 2026-05-01 |
| 0016 | CAL-16: Descomposición regulatoria del ahorro en C2 | Accepted | 2026-05-02 |
| 0017 | CAL-17: Auditoría pydataxm vs PB_PROM oficial XM | Accepted | 2026-05-02 |

> **Nota numeración:** CAL-15 / ADR `0011-cal15-c4-creg101072-tipo-1-2-cvm.md`
> está reservado para el trabajo en C4 (Decreto 2236/2023 + CREG
> 101072/2025) — no commiteado a la fecha. La numeración de IDs ADR
> es secuencial, los slugs `cal-NN` no necesariamente lo son. Por eso
> CAL-15 (C4) y CAL-16 (C2) coexisten en archivos `0011-cal15-...md` y
> `0016-cal16-...md` respectivamente.

## Conexion con la propuesta

Estas ADRs cubren las decisiones de calibracion enmarcadas en las
actividades **2.1** (modelo P2P) y **3.x** (validacion regulatoria) de
la propuesta de tesis. Toda decision posterior que afecte el nucleo
`core/`, los escenarios `scenarios/` o el procesamiento de datos `data/`
debe agregarse aqui antes de implementarse.

## Como agregar una nueva ADR

1. Asignar el siguiente ID secuencial (0009, 0010, ...).
2. Copiar la estructura de cualquier ADR existente.
3. Llenar **Contexto** (que problema), **Decision** (que se eligio),
   **Consecuencias** (positivas, negativas, riesgos abiertos).
4. Si supersede una ADR previa, marcar la anterior como `Superseded`
   apuntando al nuevo ID.
5. Sembrar en memoria Ruflo:
   ```bash
   npx @claude-flow/cli memory store \
     --key "adr-NNNN-slug" \
     --value "<contenido sintetico>" \
     --namespace adr
   ```
