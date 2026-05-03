# 0027 — CAL-27: C4-mensual con cruce Hx (cierra TODO de CAL-15)

- **Estado:** Accepted
- **Fecha de decisión:** 2026-05-03
- **Actividad:** 4.1 + 4.2 (escritura paper) + 3.1-3.3 (validación regulatoria)
- **Archivos afectados:** `scenarios/scenario_c4_creg101072.py`
  (función nueva `_run_c4_monthly_hx`, dispatcher actualizado),
  `tests/test_cal27_c4_monthly.py` (nuevo),
  `graficas/fig_c4_horario_vs_mensual.{csv,mat,png}` (nuevo).
  **NO toca** el default `creg174_inheritance` (peor caso CAL-15).
- **Relacionado con:** ADR-0010 (CAL-10), ADR-0011 (CAL-15).
- **Fuente:** plan
  `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 6.3;
  reunión asesores 2026-05-01 (`Reunion0105.txt` líneas 232-282).

## Contexto

ADR-0011 (CAL-15) implementó C4 (Decreto 2236/2023 + CREG 101 072/2025)
en modo `creg174_inheritance` con clasificación **hora a hora** de
excedentes:

```
permuta_t1[n,k] = min(credit[n,k], deficit_ind[n,k])  # por hora
excedente_t2[n,k] = max(credit[n,k] - deficit_ind[n,k], 0)
```

CAL-15 §"Simplificaciones documentadas" reconoció explícitamente:

> *"Algoritmo hora-a-hora: peor-caso para C4 (clasifica residual como
> Tipo 2 sin esperar mes); versión mensual con Hx sería ligeramente
> mejor. Diferida porque fortalece argumento P2P > C4."*

La reunión con asesores (2026-05-01, líneas 232-282) destacó que
CREG 174 (C1) liquida **mensualmente** mientras P2P y C4 (modo actual)
liquidan **horario**. Esta asimetría es relevante para el paper:
"vamos a tener las de perder con los autogeneradores a pequeña escala
porque esos picos en donde hay más generación... son muy pequeñitos".

Para el paper IEEE WEEF queremos:

1. Reportar C4 en su modo "peor caso" (`creg174_inheritance`) y en
   su modo "mejor caso" (`monthly_hx`) lado a lado.
2. Demostrar que el ranking P2P > C4 (o P2P ≈ C4) es robusto a la
   elección de granularidad temporal.
3. Cerrar el TODO documentado en CAL-15.

## Decisión

Implementar `_run_c4_monthly_hx` análogo a `_run_c4_creg174_inheritance`
pero con **agregación mensual + cruce Hx por agente** (heredado de C1).

Algoritmo:

```
Para cada mes m:
  Para cada agente n:
    inyeccion_acum_n_m = sum_{t in m} max(G[n,t] - D[n,t], 0)
    deficit_acum_n_m = sum_{t in m} max(D[n,t] - G[n,t], 0)

  total_iny_pool_m = sum_n inyeccion_acum_n_m

  Para cada agente n:
    credit_n_m = pde[n] * total_iny_pool_m       # crédito mensual del agente

    # Cruce Hx mensual (por agente, a nivel agregado del mes)
    permuta_t1_n_m = min(credit_n_m, deficit_acum_n_m)
    excedente_t2_n_m = max(credit_n_m - deficit_acum_n_m, 0)
    grid_buy_n_m = max(deficit_acum_n_m - credit_n_m, 0)

  # Valoración
  pi_gs_m_n = mean(pi_gs[n, t in m])
  pi_C_m_n = mean(pi_C[n, t in m])
  pi_bolsa_m_avg = mean(pi_bolsa[t in m])

  savings_m_n = sum_{t in m} autoconsumo[n,t] * pi_gs[n,t]
              + permuta_t1_n_m * (pi_gs_m_n - pi_C_m_n)
              + excedente_t2_n_m * pi_bolsa_m_avg
              - grid_buy_n_m * pi_gs_m_n  (no se resta, Filosofía A)

  net_benefit_n = sum_m savings_m_n
```

**Diferencias clave respecto a `creg174_inheritance` (CAL-15)**:

- En CAL-15, el cruce ocurre **hora a hora** y `excedente_t2` puede
  acumularse desde la primera hora con surplus.
- En CAL-27, el cruce ocurre **mensualmente sobre el agregado**:
  todo el surplus del mes va primero a saldar el déficit acumulado
  del agente; solo lo que queda (residual mensual) clasifica como
  Tipo 2.

**Hipótesis (a verificar empíricamente)**:
`total_net_benefit(monthly_hx) ≥ total_net_benefit(creg174_inheritance)`
para cualquier conjunto de datos, porque el modo mensual permite
saldar más permutas Tipo 1 (que valen más que Tipo 2 en regímenes
donde `pi_gs - Cvm > pi_bolsa`).

**Activación**:
- `mode="creg174_inheritance"` (default, sin cambios) — peor caso, lo
  reportado en la tesis y baseline post-CAL-23.
- `mode="monthly_hx"` (CAL-27 nuevo) — mejor caso, requiere
  `month_labels` para distinguir meses (igual que C1).

## Alternativas consideradas

1. **Cambiar el default global a `monthly_hx`**. Descartado: rompe
   baseline post-CAL-23 y oscurece el "peor caso" deliberadamente
   elegido en CAL-15 para fortalecer la comparación P2P > C4.
2. **Distribuir Tipo 2 mensual hora a hora y valorar horario**.
   Descartado por ahora: complejidad sin beneficio empírico claro.
   El promedio mensual de `pi_bolsa` es una aproximación razonable.
   Puede ser CAL-N futuro.
3. **Implementar Hx en cada mes a nivel comunitario** (no por
   agente). Descartado: no respeta la individualidad de la
   liquidación que la CREG hereda de art. 22.

## Consecuencias

**Positivas**

- Paper reporta C4 en sus dos modos, demostrando robustez del
  ranking respecto a granularidad temporal.
- TODO de CAL-15 cerrado formalmente.
- API extendida sin romper tests previos: `mode="creg174_inheritance"`
  default; `mode="monthly_hx"` opt-in.
- Tests comparativos verifican la hipótesis
  `monthly_hx ≥ creg174_inheritance`.

**Negativas**

- Nueva ruta de cálculo en `scenario_c4_creg101072.py` (~80 LOC).
  Mitigación: testeada exhaustivamente.
- Si `month_labels` no se pasa, el modo `monthly_hx` opera como
  período único (similar al modo perfil diario de C1). Comportamiento
  documentado.

**Riesgos abiertos**

- La valoración del Tipo 2 al **promedio mensual** de `pi_bolsa`
  puede subestimar/sobreestimar respecto a la valoración hora a hora.
  Mitigación: documentado; CAL-N futuro puede refinar si la
  diferencia es material (>5%).

## Verificación

```powershell
# Tests CAL-27:
python -m pytest tests/test_cal27_c4_monthly.py -v

# Smoke comparativo en run_paper_iter:
python scripts/run_paper_iter.py --month 2025-08 --c4-mode monthly_hx
python scripts/run_paper_iter.py --month 2025-08 --c4-mode creg174_inheritance

# Suite global (sin regresiones):
python -m pytest tests/test_c4_creg101072.py -q
```

Output esperado:
- `monthly_hx ≥ creg174_inheritance` en `total_net_benefit`.
- Diferencia típica 1-5% (peor caso vs mejor caso).

## Referencias

- ADR-0010 (CAL-10) — algoritmo Hx mensual original en C1.
- ADR-0011 (CAL-15) — implementación horaria de C4 (peor caso).
- `Reunion0105.txt` líneas 232-282 — discusión asesores
  granularidad temporal.
- `Documentos/notas_modelo_tesis.md §CAL-15` — TODO documentado.
- Plan: `radiant-sleeping-eagle.md` Sprint 6.3.
