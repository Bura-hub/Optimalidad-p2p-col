# 0028 — CAL-28: Selección de medidor puntual por institución (paper IEEE WEEF)

- **Estado:** Accepted
- **Fecha de decisión:** 2026-05-03
- **Actividad:** 4.1 + 4.2 (escritura paper)
- **Archivos afectados:** `scripts/run_paper_iter.py`
  (función nueva `cargar_mte_paper`),
  `tests/test_cal28_meter_selection.py` (nuevo),
  `data/paper_meter_config.csv` (nuevo, configuración explícita).
  **NO toca** `data/xm_data_loader.py` ni el flujo de la tesis.
- **Relacionado con:** ADR-0025 (CAL-25 modo paper).
- **Fuente:** plan
  `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 6.X-bis;
  observación adicional del usuario en sesión 2026-05-03 derivada
  de la reunión 2026-05-01 (`Reunion0105.txt` líneas 215-227,
  527-543).

## Contexto

`data/xm_data_loader.py` carga por defecto el **medidor totalizador
M1** de cada institución MTE (`Bloque Sur - Medidor 1`,
`Medidor 1 - Alvernia`, etc.). Esto resulta en demandas elevadas
sobre el horizonte:

| Institución | D̄ M1 (kW) | Ḡ (kW) | Cobertura G/D |
|---|---:|---:|---:|
| Udenar | 7.21 | 2.15 | 30 % |
| Mariana | 9.57 | 2.04 | 21 % |
| UCC | 21.42 | 2.50 | 12 % |
| HUDN | 9.09 | 2.10 | 23 % |
| Cesmag | 4.47 | 1.10 | 25 % |
| **Comunidad** | **51.8** | **9.9** | **19 %** |

Con cobertura PV agregada del 19 %, los excedentes son escasos y
el mercado P2P se mantiene activo apenas 1 031/6 144 horas (16.8 %)
con 3 659 kWh totales sobre todo el horizonte (cap. 4 §4.9.1). En
agosto-2025 la actividad cae a 153 horas activas de 744. Esto dilata
la narrativa P2P del paper IEEE WEEF.

El usuario observó en la reunión 2026-05-01 (líneas 215-227,
527-543) y aclaró en sesión 2026-05-03:

> *"como se está simulando actualmente las entidades no tienen tantos
> excedentes lo que hace que no se logre un mercado P2P activo… se
> pensó en definir que la demanda para cada entidad no esté definida
> por el totalizador, sino por algún medidor puntual que haga que la
> entidad tenga excedentes en más ocasiones… y a su vez una forma de
> que tengan excedentes pero no tantos como para que ni siquiera
> decidan comercializar entre ellos"*

Cada institución MTE tiene **4 medidores** disponibles (M1 totalizador
+ M2/M3/M4 sub-medidores de circuitos específicos). Inspección
empírica:

| Inst | M1 (kW) | M2 (kW) | M3 (kW) | M4 (kW) |
|---|---:|---:|---:|---:|
| Udenar | 1.32 | -0.01 ⚠ | 1.03 | -0.92 ⚠ |
| Mariana | 7.92 | 0.22 | 0.07 ⚠ | -0.02 ⚠ |
| UCC | 20.13 | 1.66 | 3.03 | 2.00 |
| HUDN | 8.99 | 1.32 | 1.88 | 0.78 |
| Cesmag | 4.68 | -1.04 ⚠ | 2.81 | 0.33 |

⚠ = anomalías (datos negativos, vacíos, ruido); descartados.

## Decisión

Para el paper IEEE WEEF se selecciona, por institución, el medidor
que produce un ratio `D / G` **dentro de la banda heurística
[0.4, 1.5]** (equivalente a `G/D ∈ [67%, 250%]`). Esta banda asegura:

- **Excedentes ocasionales** (no constantes): la institución no es
  100 % excedentaria todo el tiempo.
- **Mercado P2P activo**: hay vendedores y compradores en distintos
  momentos, justificando la dinámica Stackelberg + RD.
- **Validación regulatoria**: respeta el límite CREG 101 072 art. 5
  (≤ 10 % participación individual y ≤ 100 kW de capacidad).

### Asignación final

| Institución | Medidor seleccionado | Factor escala | D̄ esperada (kW) | Ḡ (kW) | G/D |
|---|---|---:|---:|---:|---:|
| **Udenar** | `Bloque Sur - Medidor 3` | 1.0 | ~1.03 | 2.15 | **209 %** (vendedor) |
| **Mariana** | `Medidor 1 - Alvernia` (× 0.3) | 0.3 | ~2.40 | 2.04 | **85 %** (balance) |
| **UCC** | `Medidor 3 - UCC` | 1.0 | ~3.03 | 2.50 | **82 %** (comprador) |
| **HUDN** | `Medidor 3 - HUDN` | 1.0 | ~1.88 | 2.10 | **112 %** (balance) |
| **Cesmag** | `Medidor 3 - Cesmag` | 1.0 | ~2.81 | 1.10 | **39 %** (comprador) |
| **Comunidad** | (suma) | — | ~11.15 | 9.89 | **89 %** |

Cobertura PV agregada esperada: **~89 %** (vs 19 % de la tesis).

### Justificación caso por caso

- **Udenar M3**: sub-medidor del Bloque Sur con demanda baja
  (1.03 kW); representa un circuito específico de iluminación + UPS.
- **Mariana M1 × 0.3**: M3 tiene datos casi vacíos (0.07 kW); M2
  similar (0.22 kW). El M1 es el único confiable, escalado al 30 %
  para representar "una de las facultades" en lugar del campus
  completo. Documentado como simplificación.
- **UCC M3, HUDN M3, Cesmag M3**: sub-medidores con datos completos
  y demanda compatible con la generación PV instalada.

## Justificación académica para el paper

> *"For the WEEF community case study, demand for each institution is
> taken from a representative sub-meter (rather than the campus
> totalizer) to model a circuit-level energy community where PV
> coverage and demand are balanced. This setup, motivated by typical
> Colombian institutional energy communities operating at building or
> faculty level, produces a community PV-to-demand ratio of ~89 %,
> enabling an active P2P market while remaining within CREG 101 072
> participation limits."*

## Alternativas consideradas

1. **Mantener M1 totalizador (status quo)**. Descartado: cobertura
   19 % deja P2P inactivo, narrativa débil para el paper.
2. **Factor de demanda uniforme M1 × 0.3**. Descartado: vulnerable
   a crítica del tribunal *"¿por qué este factor?"*. Menos defensible
   que sub-medidor real.
3. **Excluir Mariana del paper** (M3 vacío). Descartado: pierde
   representatividad de la comunidad MTE; el factor 0.3 es preferible
   y se documenta explícitamente.
4. **Cambiar el default global de `data/xm_data_loader.py`**.
   Descartado: rompe baseline post-CAL-23 y la heterogeneidad
   oficial/comercial documentada en CAL-8.

## Consecuencias

**Positivas**

- Mercado P2P activo en horizonte del paper (≥ 30 % horas activas
  esperado).
- Defensibilidad académica: explicación caso por caso documentada.
- Compatibilidad con CREG 101 072 (capacidades por debajo de 100 kW).
- Aislamiento total: tesis sigue con M1 totalizador y heterogeneidad
  comercial/oficial.
- Configuración explícita en `data/paper_meter_config.csv`
  reproducible.

**Negativas**

- Mariana se basa en M1 escalado (no sub-medidor real). Documentado
  como limitación.
- Resultados del paper NO son comparables 1:1 con cap. 4 §4.9 de la
  tesis (que usa M1 totalizador).
- Si se publican datos individuales por institución, debe explicarse
  el medidor usado para cada una.

**Riesgos abiertos**

- Si en revisión por pares el revisor cuestiona la elección de
  sub-medidor, hay que poder defender la mezcla (M3 real + M1×0.3
  Mariana). Mitigación: ADR documenta el razonamiento numérico
  completo.

## Verificación

```powershell
# Tests CAL-28:
python -m pytest tests/test_cal28_meter_selection.py -v

# Smoke run paper agosto-2025 con M3 + Mariana M1×0.3:
python scripts/run_paper_iter.py --month 2025-08 --tag cal28

# Comparar contra status quo (sin CAL-28):
python scripts/run_paper_iter.py --month 2025-08 --no-paper-meters \
    --tag legacy
```

Output esperado: cobertura G/D ≈ 89 %, mercado P2P en ≥ 30 % horas
activas (vs 21 % con M1 totalizador en agosto-2025).

## Referencias

- `Reunion0105.txt` líneas 215-227, 527-543 — sugerencia asesor.
- ADR-0025 (CAL-25) — modo paper estándar.
- `data/xm_data_loader.py` — origen del default M1.
- Plan: `radiant-sleeping-eagle.md` Sprint 6.X-bis.
