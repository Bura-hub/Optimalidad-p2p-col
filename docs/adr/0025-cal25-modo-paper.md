# 0025 — CAL-25: Modo paper IEEE WEEF (homogeneización + filtrado de escenarios)

- **Estado:** Accepted
- **Fecha de decision:** 2026-05-02
- **Actividad:** 4.1 + 4.2 (escritura paper)
- **Archivos afectados:** `scripts/run_paper_iter.py` (nuevo),
  `tests/test_run_paper_iter.py` (nuevo),
  `outputs/paper/` (gitignored salvo el xlsx final).
  **NO toca** `main_simulation.py` ni `data/cedenar_tariff.py`.
- **Relacionado con:** ADR-0008 (CAL-8), ADR-0009 (CAL-9),
  ADR-0011 (CAL-15).
- **Fuente:** plan
  `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 6.1;
  reunión asesores 2026-05-01 (`Reunion0105.txt` líneas 63-144).

## Contexto

El abstract aceptado para WEEF 2026
(`WEEF2026_Propuesta_BrayanLopez.docx`) define:

- **Dos benchmarks regulatorios**: C1 (CREG 174/2021, AGPE individual)
  y "C2" (CREG 101 072/2025, comunidad energética).
- **No menciona**: PPA bilateral (C2 interno del repo) ni mercado spot
  (C3 interno).
- **Resultados sobre perfiles diarios promedio** ("average daily
  profiles"), no horizonte completo.

La reunión con asesores (2026-05-01) identifico además que la
heterogeneidad tarifaria oficial vs comercial introducida por CAL-8
(`pi_gs[Udenar,HUDN] = 797 oficial` vs `pi_gs[Mariana,UCC,Cesmag] = 956
comercial`) genera **deserción individual** en P2P: 2/5 instituciones
(Udenar, HUDN) prefieren C1 sobre P2P porque su `pi_gs` bajo
"abarata" la permuta CREG 174 (ver §4.6.3 del borrador cap 4).

Esto se debe a que el solver Stackelberg + RD del P2P
(`core/replicator_buyers.py:108`) usa `pi_gs` como **escalar único**
en la dinámica de réplica:

```
pi_hat = (pi_gs - pi_all) * (-pi_gb + pi_all)
```

Tarifas heterogéneas rompen la ventana común de admisibilidad
`[pi_gb, pi_gs]` y producen multi-equilibrios (compradores oficiales
"caros" y comerciales "baratos" simultáneamente).

Para el paper IEEE WEEF, dos cambios son convenientes:

1. **Homogeneizar** todas las instituciones a perfil `comercial`
   (956 COP/kWh) → ventana P2P uniforme → narrativa limpia.
2. **Filtrar escenarios**: solo C1 + C4 + P2P (los del abstract);
   C4 se renombra a "C2 (CREG 101 072)" para consistencia con el
   abstract.

La **tesis completa mantiene** la heterogeneidad oficial/comercial
(es un hallazgo legítimo). El cambio aplica **solo al script
`run_paper_iter.py`** que genera los outputs del paper.

## Decisión

Crear **`scripts/run_paper_iter.py`** orquestador del paper como
script standalone aislado. Aplica en memoria:

1. **A1 — Homogeneización**: redefine
   `data.cedenar_tariff.INSTITUTION_PROFILE` antes de cargar el resto,
   sustituyendo el perfil de Udenar y HUDN por
   `TariffProfile("comercial", 2, "cedenar")`.
2. **B — Filtrado**: solo simula C1, C4 y P2P (no C2 PPA ni C3 Spot).
3. **B-rename**: en outputs/figuras/Excel, renombra
   `"C4"` a `"C2 (CREG 101 072)"` y `"C1"` se mantiene como
   `"C1 (CREG 174)"`.
4. **G — Mes específico**: parámetro `--month YYYY-MM`
   (default `2025-08`); filtra el horizonte MTE al mes seleccionado.

**Garantías**:

- **No toca `main_simulation.py`**: el flujo `--full --analysis`
  produce los mismos resultados post-CAL-23.
- **No toca `data/cedenar_tariff.py`**: la tesis sigue con
  heterogeneidad oficial/comercial.
- **Patron de "modo paper"**: precedente para futuras adaptaciones
  paper-vs-tesis sin invadir el código nuclear.

## Alternativas consideradas

1. **Flag `--paper-mode` en `main_simulation.py`** (opción i del
   plan). Descartado: invade un archivo gobernado por múltiples
   ADRs (CAL-8, CAL-9, ...) y dispararía pre-commit hook anti-drift
   en cada cambio del modo paper.
2. **Postproceso del xlsx existente** (opción iii del plan).
   Descartado: requiere correr `--full` cada vez (~52 min) en lugar
   de solo el mes de agosto (~30 s).
3. **Cambiar el default de `INSTITUTION_PROFILE` a comercial uniforme**.
   Descartado: rompe la tesis y el baseline post-CAL-23.

## Consecuencias

**Positivas**

- Script standalone aislado: se puede iterar libremente pre-deadline
  10-may-2026 sin riesgo para el resto del repo.
- Reusa todas las funciones existentes (`run_c1_creg174`,
  `run_c4_creg101072`, `EMSP2P`, etc.) sin modificarlas.
- Patrón "modo paper" replicable para futuras versiones (revistas,
  conferencias adicionales).
- Output dedicado en `outputs/paper/` con nomenclatura del abstract.

**Negativas**

- Duplicación parcial de orquestación (carga MTE + setup ems): el
  script repite ~50 líneas de `main_simulation.py`. Aceptable como
  costo de aislamiento.
- A1 modifica `INSTITUTION_PROFILE` en memoria; debe ejecutarse antes
  de cualquier import de `cedenar_tariff` que cachee el dict.

**Riesgos abiertos**

- Si `INSTITUTION_PROFILE` se cachea durante imports, A1 podría no
  surtir efecto. **Mitigación:** el script importa
  `cedenar_tariff` y modifica el atributo del módulo; las funciones
  helper leen `INSTITUTION_PROFILE` por nombre cada vez (verificado
  en `cedenar_tariff.py:286-298`).
- Si en el futuro alguien crea otro modo paper (e.g. para una
  revista), debe seguir este patrón aislado.

## Verificación

```powershell
# Modo paper sobre agosto 2025:
python scripts/run_paper_iter.py --month 2025-08

# Verifica que tesis no se afecta:
python main_simulation.py --data real --full --analysis  # mismo baseline

# Tests:
python -m pytest tests/test_run_paper_iter.py -v
```

Output esperado:

```
outputs/paper/resultados_paper.xlsx
  - Hoja 'Resumen': 3 escenarios (C1, C2 (CREG 101 072), P2P)
  - Hoja 'Por_agente': perfiles homogeneizados
outputs/paper/perfiles_agosto_2025.png
```

## Referencias

- ADR-0008 (CAL-8) — origen de heterogeneidad oficial/comercial.
- ADR-0011 (CAL-15) — implementación C4 = `creg174_inheritance`.
- `Reunion0105.txt` — discusión asesores 2026-05-01.
- `WEEF2026_Propuesta_BrayanLopez.docx` — abstract aceptado.
- Plan: `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 6.1.
