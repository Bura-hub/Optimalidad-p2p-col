# CAL-14 — Aplicar techo CREG 101 066/2024 (PES) al precio de bolsa horario

- **Fecha:** 2026-05-01
- **Autor:** Brayan S. Lopez-Mendez
- **Etiqueta:** CAL-14
- **Relacionado:** ADR-0010 (CAL-10b), ADR-0013 (CAL-13), `data/xm_prices.py`,
  `data/precios_bolsa_xm_api.csv`, escenarios C1 / C3 / C4
- **Memoria semántica:** `tesis-p2p / cal_14_creg101066_pes_techo_pi_bolsa`

## Contexto

El modelo actual liquida excedentes a precio de bolsa horario (`pi_bolsa[k]`)
en tres rutas:

- C1 — excedentes Tipo 2 post-Hx (CREG 174/2021)
- C3 — todos los excedentes (mercado spot)
- C4 — surplus tras créditos PDE (CREG 101 072/2025)

El precio se carga en `data/xm_prices.py:get_pi_bolsa()` con prioridad
API pydataxm (cache `data/precios_bolsa_xm_api.csv`) → CSV manual →
sintético calibrado.

**Auditoría 2026-05-01** detectó que la métrica `PrecBolsNaci` que
devuelve pydataxm es el **Precio de Bolsa marginal de oferta**, no el
**Precio de Transacciones en Bolsa (PTB)** efectivo tras activación de
Obligaciones de Energía Firme (OEF). Verificación contra el sheet
`Comportamiento_PBNal_Horario` del Excel oficial XM 03_Informe_Precios:

| Mes | PB max cache (pydataxm) | PB max XM Excel | PES vigente |
|---|---:|---:|---:|
| 2025-09 | 1 229 | 1 186.26 | 893.85 |
| 2025-12 | 795 | 465.21 | 864.91 |

PB excede sistemáticamente PES (techo regulatorio absoluto) → el dato
liquidado real (PTB) está topado por el mecanismo OEF, pero la API entrega
el marginal sin recortar. C1, C3 y C4 actualmente sobreestiman ingresos
por bolsa en horas extremas que en la práctica regulatoria estarían
recortadas.

**Resolución CREG 101 066/2024** (publicada 18-NOV-2024, vigente
01-DIC-2024) reemplazó el precio de escasez único (~945 COP/kWh) por
tres niveles diferenciados que se actualizan mensualmente:

| Nivel | Aplica a | Rango jul-2025 → ene-2026 |
|---|---|---:|
| **PEI** Precio Escasez Inferior | Plantas con bajo costo variable: hidro, solar, eólica, carbón eficiente | 327.67 – 350.08 |
| **PE**  Precio Escasez "intermedio" CREG 071/2006 | Fórmula CREG 071/2006 actualizada | 590.56 – 746.17 |
| **PES** Precio Escasez Superior | Plantas a combustibles líquidos (techo absoluto) | 829.00 – 898.02 |

El precio liquidado real (PTB) nunca supera PES. Aplicar PES como cap
duro al precio de bolsa entregado por pydataxm es la aproximación más
fiel al PTB sin necesidad de modelar la composición horaria del despacho
OEF. Decisión locked-in en sección "Decisiones cerradas".

## Decisiones cerradas

1. **Alcance (pregunta 1)**: opción **A** — fiel a CREG 101 066/2024.
   C3 reporta lo que el generador efectivamente recibe en bolsa hoy.
2. **Capa donde aplicar el techo (pregunta 2)**: opción **A2** — en la
   fuente de datos `data/xm_prices.py:get_pi_bolsa()`. Una sola
   intervención afecta a C1, C3, C4 y cualquier escenario futuro que
   pida `pi_bolsa`.
3. **Nivel del techo (pregunta 3)**: **PES** (absoluto superior). PE y
   PEI quedan disponibles como columnas en el CSV para análisis futuros
   sin recargar datos.
4. **Persistencia de la tabla mensual (pregunta 4)**: opción **P2** —
   CSV externo `data/precios_escasez_creg.csv`, paralelo a
   `data/tarifas_cedenar_mensual.csv` (CAL-8/9).

## Diseño

### 1. Capa de datos

#### 1.1 Nuevo CSV `data/precios_escasez_creg.csv`

```csv
mes,pei_cop_kwh,pe_cop_kwh,pes_cop_kwh,fuente,nota
2025-07,350.08,699.17,865.22,xm.com.co/noticias/8119,Informe XM jul-2025
2025-08,343.86,746.17,898.02,xm.com.co/noticias/8184,Informe XM ago-2025
2025-09,339.20,711.27,893.85,sinergox.xm.com.co/2025/09/03_Informe_Precios,Excel sheet Comportamiento_PBNal_Horario
2025-10,334.17,675.82,857.21,xm.com.co/noticias/8442,Informe XM oct-2025
2025-11,332.00,659.00,829.00,xm.com.co/noticias/8584,Informe XM nov-2025
2025-12,329.43,625.20,864.91,sinergox.xm.com.co/2025/12/03_Informe_Precios,Excel sheet Comportamiento_PBNal_Horario
2026-01,327.67,590.56,830.34,xm.com.co/noticias/8759,Informe XM ene-2026
```

Los 7 meses del horizonte de la tesis quedan completos sin
interpolación. Verificación cruzada de los valores se realizó contra el
sheet `Comportamiento_PBNal_Horario` de los Excel `03_Informe_Precios_y
_Transacciones_MM_2025.xlsx` (las columnas "Precio de Escasez 071",
"Precio de Escasez Superior" y "Precio de Escasez Inferior" son
constantes durante todo el mes — un valor único por mes).

#### 1.2 Nueva función `load_creg_ceiling()`

```python
def load_creg_ceiling(
    t_start: str,           # "2025-07-01"
    t_end:   str,           # "2026-02-01"
    level:   str = "PES",   # "PEI" | "PE" | "PES"
    csv_path: Optional[str] = None,
) -> pd.Series:
    """
    Devuelve serie mensual indexada por Period('M') con el valor del
    nivel elegido en COP/kWh.

    Política para celdas vacías:
      - Interpolación lineal entre meses adyacentes con valor.
      - Forward/backward fill si solo hay un lado disponible.
      - Mes fuera del rango del CSV: WARN en log + valor del mes más
        cercano.

    Lanza FileNotFoundError si el CSV no existe (no falla en silencio).
    """
```

Ubicación: nuevo bloque en `data/xm_prices.py`, después del bloque
`§3.6 Análisis de fuente de precios`, antes del CLI.

### 2. Lógica de aplicación

#### 2.1 Nueva función `apply_creg101066_ceiling()`

```python
def apply_creg101066_ceiling(
    pi_bolsa: np.ndarray,            # (T,) precios horarios COP/kWh
    t_start:  str,                   # "2025-07-01"
    level:    str = "PES",
    effective_date: str = "2024-12-01",  # vigencia CREG 101 066/2024
    csv_path: Optional[str] = None,
    return_diagnostics: bool = False,
) -> Union[np.ndarray, Tuple[np.ndarray, dict]]:
    """
    Aplica el techo regulatorio CREG 101 066/2024 a la serie de precios
    de bolsa horarios.

    Para cada hora k:
        h_date = t_start + k horas
        if h_date >= effective_date:
            ceiling = ceiling_table[h_date.year-month]
            pi_bolsa[k] = min(pi_bolsa[k], ceiling)

    Implementación: vector mensual expandido a horas, np.minimum una vez.

    Si return_diagnostics=True devuelve (pi_capped, diag) con:
        diag['hours_capped']    : número de horas recortadas
        diag['fraction']        : fracción del horizonte recortada
        diag['delta_cop_total'] : suma de (pi_raw - pi_capped) en COP/kWh
        diag['by_month']        : dict mes → {capped, mean_pre, mean_post}
    """
```

#### 2.2 Integración en `get_pi_bolsa()`

Modificar la firma actual para añadir dos parámetros opt-in:

```python
def get_pi_bolsa(T, t_start="2025-07-01", t_end="2026-02-01",
                 csv_path=None, use_api=True,
                 scenario="2025_real", seed=42,
                 apply_ceiling=True,           # nuevo
                 ceiling_level="PES"):         # nuevo
    ...
    # (lógica actual: API → CSV → sintético → return _adj(prices, T))
    prices = ...

    if apply_ceiling:
        prices, diag = apply_creg101066_ceiling(
            prices, t_start, level=ceiling_level,
            return_diagnostics=True)
        _print_ceiling_summary(diag)
    return prices
```

Default `apply_ceiling=True` para que toda corrida nueva refleje
CREG 101 066 sin necesidad de tocar callers. Pasar `False` permite
análisis contrafactual ("qué pasaría sin la regulación") sin reabrir
código.

#### 2.3 Diagnóstico en consola

`_print_ceiling_summary(diag)` imprime al final del header de
inicialización del modelo:

```
  [creg-101-066] Techo PES aplicado: 99 horas recortadas (1.92% del horizonte),
                  delta = 168,234 COP/kWh acumulado
  [creg-101-066] Por mes:
                  Mes      Horas-cap   Δmedia COP/kWh
                  2025-07      2          -0.4
                  2025-08     19          -3.9
                  2025-09      7          -1.6
                  2025-10      0           0.0
                  2025-11      4          -0.7
                  2025-12      0           0.0
                  2026-01      0           0.0
```

### 3. Sin cambios en escenarios

`scenarios/scenario_c1_creg174.py`, `scenario_c3_spot.py` y
`scenario_c4_creg101072.py` reciben `pi_bolsa` exactamente como hoy.
La capa de datos garantiza que cumple `pi_bolsa <= max(PES_horizonte)`.

### 4. Validación

#### 4.1 Invariante regulatorio (test estricto)

```python
assert pi_capped.max() <= max_PES_horizonte + 1e-6
```

#### 4.2 Coherencia con PB oficial XM (test de regresión)

Para los meses con valor oficial conocido, la media de la serie capada
debe estar dentro del ±10 % del PRECIO_BOLSA_PROM_MES publicado por XM:

```python
PB_OFFICIAL_PROM_MES = {
    "2025-09": 292.65,   # del sheet IndiceLiquidez del Excel XM
    "2025-12": 278.83,
}
for mes, oficial in PB_OFFICIAL_PROM_MES.items():
    delta_pct = abs(pi_capped[mes].mean() - oficial) / oficial * 100
    assert delta_pct < 10.0
```

El gap de 35 % observado en `2026-01` queda registrado como
**follow-up CAL-17** (auditoría de la métrica que devuelve pydataxm
vs PTB oficial). No bloquea CAL-14.

### 5. Plan de testing — `tests/test_creg101066_ceiling.py`

Siete tests organizados en tres grupos:

**Grupo A — Cargador del CSV (3 tests)**
- `test_load_csv_returns_series_indexed_by_month`
- `test_load_csv_raises_when_file_missing`
- `test_load_csv_handles_empty_cell_with_interpolation`

**Grupo B — Aplicación del techo (3 tests)**
- `test_ceiling_caps_values_above_PES`
- `test_ceiling_does_not_modify_values_below_PES`
- `test_ceiling_uses_correct_month_for_each_hour`

**Grupo C — Integración (1 test)**
- `test_get_pi_bolsa_applies_ceiling_by_default`
- `test_get_pi_bolsa_respects_disable_flag`

Todos los tests deterministas. El de regresión usa el cache real ya
versionado y los valores oficiales XM de los meses verificados.

### 6. Documentación

- **ADR-0014** `docs/adr/0014-cal14-creg101066-pes-ceiling.md` con la
  decisión formal, contexto regulatorio, alternativas evaluadas y
  consecuencias.
- **§CAL-14** en `Documentos/notas_modelo_tesis.md`: justificación del
  estimador (PES vs PE vs PEI), distinción PB vs PTB, impacto cuantitativo
  esperado por escenario, limitaciones del modelo simplificado vs
  composición OEF horaria real.
- **Memoria semántica Ruflo** con resumen para futuras sesiones:
  `cal_14_creg101066_pes_techo_pi_bolsa`.
- **Comentario en bloque** en `data/xm_prices.py` antes de las nuevas
  funciones, citando el sheet exacto del Excel XM y el rango de meses
  cubierto.

## Fuera de alcance

- **Composición horaria de OEF**: aplicar PEI/PE/PES selectivamente según
  qué tipo de planta está en el margen cada hora. Requeriría descargar
  el despacho diario de XM. PES como aproximación es suficiente para la
  tesis.
- **Auditoría de pydataxm vs PTB oficial**: el gap de 35 % observado en
  ene-2026 entre el cache (218.5) y el PB_PROM oficial (213.0 → calculado
  sobre 7 días) sugiere que la API puede estar entregando datos
  provisionales. Investigación → **CAL-17** (CAL-15 ya asignado a C4 y
  CAL-16 a descomposición regulatoria del ahorro en C2).
- **Datos pre-CREG 101 066/2024**: no se aplica techo a horas anteriores
  a `effective_date=2024-12-01`. Fuera del horizonte de la tesis.

## Riesgos

1. **Distribución del recorte**: aplicar `min(PB, PES)` modifica solo
   los picos. La media mensual prácticamente no cambia (1-4 %). El
   efecto cuantitativo es pequeño en el horizonte actual (post-Niño)
   pero sustancial en escenarios futuros con `2025_el_nino` o
   `2024_escasez` del análisis Sobol — donde sí podría modificar
   conclusiones.
2. **Defensa académica**: si los asesores objetan que PES no es un cap
   duro sino una activación OEF, la respuesta es: "PES es el techo
   regulatorio absoluto del PTB; los valores de PTB publicados por XM
   nunca lo superan; aplicarlo como cap del PB es la aproximación más
   simple y conservadora para la simulación, dejando explícito en
   §CAL-14 que el mecanismo real opera vía activación OEF horaria que
   el modelo no replica detalladamente".
3. **Mantenimiento del CSV**: cada mes que XM publique nuevos PEI/PE/PES
   hay que añadir una fila. La lectura tolera celdas vacías por
   interpolación pero el CSV debe extenderse. Solución de bajo costo:
   correr un script `scripts/update_creg_ceiling.py` que descargue el
   Excel del mes desde Sinergox y escriba la fila.

## Criterios de aceptación

1. `data/precios_escasez_creg.csv` versionado con los 7 meses del horizonte.
2. `data/xm_prices.py` exporta `load_creg_ceiling` y
   `apply_creg101066_ceiling`.
3. `get_pi_bolsa(apply_ceiling=True)` (default) entrega serie con
   `max(pi_bolsa) <= 898.02 + 1e-6` para el horizonte jul-2025 → ene-2026.
4. `pytest tests/test_creg101066_ceiling.py -q` pasa los 7+ tests.
5. Una corrida `python main_simulation.py --data real --full` imprime
   el bloque `[creg-101-066]` con conteo de horas recortadas.
6. ADR-0014 aceptado y vinculado en `docs/adr/README.md`.
7. §CAL-14 escrito en `Documentos/notas_modelo_tesis.md`.

## Estimación de esfuerzo

- CSV de 7 filas: 5 min.
- `load_creg_ceiling` y `apply_creg101066_ceiling`: ~80 LOC, 1-2 h.
- Integración en `get_pi_bolsa`: ~15 LOC, 30 min.
- 7+ tests: ~120 LOC, 1-2 h.
- ADR + notas + memoria semántica: 1 h.
- Validación con corrida `--full` y revisión del log: 1 h.

**Total: ~5-7 h** distribuidas en una sesión de implementación.
