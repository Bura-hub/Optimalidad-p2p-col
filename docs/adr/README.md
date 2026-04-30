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
| 0008 | CAL-8: Tarifa Cedenar mensual diferenciada (vector per-agente) | Accepted | 2026-04-27 |

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
