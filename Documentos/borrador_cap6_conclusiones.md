# Capitulo 6 — Conclusiones (BORRADOR)

> **Aviso al autor:** este borrador cierra la tesis sintetizando los
> hallazgos cuantitativos del capitulo 4 y la discusion regulatoria
> del capitulo 5. Los placeholders `[NARRATIVA]` indican los puntos
> donde el autor humano debe escribir interpretacion academica final.
>
> **Sesion:** Sprint 5.5 del plan
> `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` · 2026-05-02
> **Destino esperado:** copiado/editado a `Documentos/FinalTesis/`
> (otro repositorio, no commitear desde SistemaBL).

---

## 6.1 Sintesis de las contribuciones

### 6.1.1 Tres capas de contribucion

Esta tesis aporta al estado del arte del mercado P2P energetico
colombiano en tres capas complementarias:

| Capa | Contribucion | Evidencia |
|------|-------------|-----------|
| **Modelado** | Reproduccion del modelo Stackelberg + RD de Chacon et al. (2025) sobre datos empiricos colombianos | `core/ems_p2p.py` + golden test `tests/golden_test_sofia.py` |
| **Calibracion** | 24 decisiones formalizadas (CAL-1 a CAL-24) con sustento empirico reproducible | `docs/adr/0001-0024` |
| **Validacion regulatoria** | Mapeo coherente entre codigo, ADRs y resoluciones CREG; validador swarm automatico | `scripts/swarm_regulatory_validator.py` (CAL-24) |

[NARRATIVA — desarrollar como las tres capas se integran. La capa
de modelado importa el algoritmo, la capa de calibracion lo adapta
a Colombia con datos empiricos MTE, y la capa regulatoria certifica
que la implementacion respeta las normas vigentes.]

### 6.1.2 Trazabilidad academica

Cada parametro, dato, supuesto y decision esta documentado en un
ADR con fuente fundamentada:

- **Datos** (CAL-9, CAL-17, CAL-18, CAL-22): cobertura 100 % del
  horizonte simulacion; trazabilidad celda-fuente en CSVs Cedenar,
  XM y MEM.
- **Parametros del juego** (CAL-1, CAL-19): `stackelberg_iters = 2`
  con barrido empirico sobre 168 h MTE (Δ welfare < 0,02 % vs
  `iters = 10`).
- **Modelo regulatorio C2** (CAL-11..16, CAL-20, CAL-21, CAL-23):
  PPA bilateral con descomposicion explicita en G + Cvm + α·COT +
  α·CXC − MEM; cada componente parametrizable.
- **Modelo regulatorio C3** (CAL-14, CAL-17): techo PES con
  auditoria empirica vs PB_PROM oficial XM.
- **Modelo regulatorio C4** (CAL-15): herencia formal CREG 174 art. 25.

[NARRATIVA — discutir como esta trazabilidad permite la auditoria
externa por asesores, tribunales academicos y reguladores
potenciales.]

---

## 6.2 Hallazgos cuantitativos principales

### 6.2.1 Comparacion P2P vs escenarios regulatorios

Sobre el horizonte abr-dic 2025 (6 144 h, 5 instituciones MTE):

| Pregunta | Respuesta | Evidencia |
|----------|-----------|-----------|
| ¿P2P supera a C1 (AGPE individual)? | Empata: RPE = -0,03 % | §4.9.1 |
| ¿P2P supera a C2 (PPA bilateral)? | Si: RPE = +1,93 % | §4.9.1 |
| ¿P2P supera a C3 (mercado spot con techo)? | Si: RPE = +3,20 % | §4.9.1 |
| ¿P2P supera a C4 (autogen colectiva)? | Si: RPE = +0,43 % | §4.9.1 |
| ¿La distribucion intracomunitaria del P2P es equitativa? | Gini P2P = 0,162; intermedia entre C1 (0,147) y C4 (0,170) | §4.9.1 |
| ¿Cuanto kWh transo el mercado P2P? | 3 659,31 kWh en 1 031 / 6 144 horas activas | §4.9.5 |

[NARRATIVA — interpretar el hallazgo central: P2P aporta beneficio
distributivo marginal vs C1 (que es el baseline de referencia para
AGPE individual) y supera notoriamente a C2 y C3. Vs C4 colectivo,
P2P mantiene ventaja modesta pero estable.]

### 6.2.2 Estabilidad ante variaciones de parametros

Las sensibilidades formalizadas en CAL-19, CAL-20, CAL-21 y CAL-23
demuestran que las conclusiones son robustas:

- **`f` (PPA split factor):** `total_net_benefit C2` invariante
  (Δ < 1e-13 % entre `f = 0` y `f = 1`); solo cambia la distribucion
  Gini.
- **`cot_alpha` (peso COT):** linealidad confirmada; en MTE real
  (`consumer_ids = []`) es **inerte**.
- **`cxc_alpha` (peso CXC):** linealidad confirmada; default
  conservador 0,0 reproduce practica industrial.
- **`stackelberg_iters` (iteraciones del juego):** 2 iteraciones
  son optimo precision-tiempo (speedup 2,4× vs `iters = 10`,
  Δ welfare < 0,02 %).

[NARRATIVA — discutir que esta robustez parametric blindara el
modelo ante variantes interpretativas que asesores o tribunales
puedan plantear.]

### 6.2.3 Validacion regulatoria automatica

El validador swarm CAL-24 reporta veredicto **PASS** con 15/15
checks sobre el repositorio actual:

| Agente | Familia normativa | Veredicto |
|--------|-------------------|-----------|
| `CREG174Validator` | CREG 174/2021 | PASS (5/5) |
| `CREG101072Validator` | Decreto 2236/2023 + CREG 101 072/2025 | PASS (5/5) |
| `CREG101066Validator` | CREG 101 066/2024 | PASS (5/5) |

Este validador es ejecutable en cualquier momento
(`python scripts/swarm_regulatory_validator.py`) y detectaria drift
silencioso si una modificacion futura rompe la coherencia
codigo-ADR-resolucion.

---

## 6.3 Limitaciones reconocidas

### 6.3.1 Limitaciones de modelado

[NARRATIVA — desarrollar:
- Cobertura PV agregada del 19 % en MTE; con cobertura 30-44 % la
  actividad P2P satura (SA-2 §4.5.2).
- LCOE solar `b_n = 225 COP/kWh` homogeneo (CAL-6); pendiente
  heterogeneizar con fichas tecnicas reales de inversores.
- Horizonte abr-dic 2025 (~256 dias); estacionalidad anual completa
  no observada.
- Heredada de Chacon et al. 2025: parametros `tau`, `theta`, `etha`,
  `lam` no recalibrados a MTE (decision deliberada para preservar
  fidelidad al modelo base).]

### 6.3.2 Limitaciones regulatorias

[NARRATIVA — desarrollar:
- Aproximacion `min(PB, PES)` ignora composicion horaria del
  despacho OEF real.
- COT y CXC parametrizables como cotas regulatorias (no calibrados
  empiricamente con factura real).
- Comision representante MEM como mediana ASOCODIS [1,5; 3,0]
  COP/kWh; no contractualmente vinculada.
- Marco P2P no esta explicitamente reglamentado en Colombia;
  admisibilidad legal depende de su interpretacion como AGRC con
  PDE dinamico.]

### 6.3.3 Limitaciones del proceso de validacion

[NARRATIVA — desarrollar:
- Validador swarm CAL-24 modo `local` se basa en heuristicas
  (regex), no en parsing semantico de las resoluciones CREG. Modo
  `swarm` requiere MCP activo.
- Tests de integracion preflight no se ejecutan en CI default por
  costo computacional (~52 min).]

---

## 6.4 Trabajo futuro

### 6.4.1 Extensiones de modelado

[NARRATIVA — desarrollar:
1. **Replicar con horizonte completo 2026** cuando MTE entregue
   datos enero-diciembre.
2. **Calibrar `b_n` heterogeneo** con horas-sol equivalentes por
   institucion.
3. **Modelar deserción individual** completa (RPE por agente vs
   contrafactual sin P2P) para evaluar IR (Individual Rationality).
4. **Time-of-Use pricing** (CREG 015/2018) en C1, C3 y P2P.
5. **Tarifas con beneficios tributarios Ley 1715/2014** (IVA 0 %,
   renta deduccion).]

### 6.4.2 Extensiones regulatorias

[NARRATIVA — desarrollar:
1. **Auditoria empirica del split factor `f`** mediante PPAs
   colombianos publicados (UPME, ANDI, Corporacion Energia).
2. **CAL-25+: Cargo CXC efectivo** mediante convocatoria de
   reforma CREG sobre transparencia post-CREG 101 072.
3. **CAL-26+: PTB efectivo en pydataxm** si XM publica la metrica
   directamente.
4. **CAL-27+: PDE dinamico bajo CREG 101 072**, evaluando si el
   regulador habilitaria mecanismos de mercado que internalicen
   la negociacion de excedentes.]

### 6.4.3 Extensiones tecnicas

[NARRATIVA — desarrollar:
1. **DAA por escenario** (Dynamic Agentic Architecture, postergado
   a Ruflo v3 2026H2): cada C1-C4 como agente adaptativo con
   fitness propio.
2. **Bibliografia academica indexada** en Ruflo (extension de A2
   del plan); habilitaria citas correlacionadas semanticamente
   durante escritura.
3. **GSA Sobol-Saltelli** sobre los 4 parametros sensibilizados
   (`f`, `cot_alpha`, `cxc_alpha`, `stackelberg_iters`) para
   indices `S_T` cuantitativos.]

### 6.4.4 Replicabilidad y diseminacion

[NARRATIVA — desarrollar:
1. **Replicar metodologia** con otras comunidades colombianas para
   externalizar la generalidad del hallazgo "P2P empata C1 con
   ventaja distributiva".
2. **Publicacion academica** en revista indexada del area (e.g.
   Revista Iberoamericana de Sistemas Energeticos, Energy Research
   & Social Science).
3. **Open-source release** del repositorio SistemaBL post-defensa
   con licencia academica para uso por otros grupos UPME, IPSE.
4. **Compartir CAL-24 swarm validador** como contribucion
   metodologica en sub-comites tecnicos CREG.]

---

## 6.5 Cierre

### 6.5.1 La pregunta de investigacion revisitada

> "¿Es el mercado P2P energetico mas eficiente que los esquemas
> regulatorios colombianos vigentes para una comunidad academica?"

[NARRATIVA — desarrollar respuesta integrada. Hallazgo principal:
P2P empata con C1 en bienestar agregado (RPE = -0,03 %) pero supera
a C2, C3 y C4 en margenes que van de +0,43 % (C4) a +3,20 % (C3).
La eficiencia se complementa con una distribucion mas equitativa
intra-comunidad (Gini P2P 0,162 vs C4 0,170). Bajo el horizonte
MTE actual (cobertura PV 19 %), el P2P aporta ganancia
distributiva marginal vs C1 individual; en escenarios con mayor
cobertura PV (SA-2: 44 %) la actividad P2P se intensifica
significativamente.]

### 6.5.2 Aporte metodologico

[NARRATIVA — desarrollar: la metodologia ADR-driven (24 ADRs
formalizados con sustento empirico reproducible) constituye una
contribucion metodologica reusable por otras tesis del area.
Combinada con el validador swarm CAL-24 y el wrapper de telemetria
CAL-Sprint 5.1, el repositorio queda preparado para auditoria
academica y reglamentaria.]

### 6.5.3 Reflexion final

[NARRATIVA — desarrollar parrafos finales de cierre. Sugerir:
- Importancia de la trazabilidad regulatoria en la transicion
  energetica colombiana.
- El P2P como herramienta de empoderamiento comunitario sin
  comprometer el bienestar agregado.
- Llamado a la CREG para reglamentar mecanismos de mercado en
  comunidades energeticas (PDE dinamico).
- Reconocimiento al modelo base de Chacon et al. 2025 y al equipo
  MTE Udenar/Pasto por los datos empiricos.]

---

## 6.6 Productos de la tesis

### 6.6.1 Artefactos academicos

- **Manuscrito** capitulos 1-6 (este documento + caps. previos).
- **Codigo fuente** del repositorio SistemaBL (~17 000 LOC),
  con licencia academica.
- **24 ADRs** (`docs/adr/0001-0024`) formalizando cada decision.
- **24 entradas** sembradas en Ruflo namespace `adr` para
  busqueda semantica.
- **5 perfiles institucionales** sembrados en Ruflo namespace
  `mte_profiles` (CAL-Sprint 4.3).
- **Snapshot baseline** sembrado en Ruflo namespace `runs`
  (CAL-Sprint 4.4).

### 6.6.2 Artefactos tecnicos

- **EMS P2P core** (`core/ems_p2p.py`) con golden test contra
  modelo base MATLAB.
- **4 escenarios regulatorios** (`scenarios/scenario_c[1234]_*.py`)
  con coherencia validada por swarm CAL-24.
- **Capa de datos** (`data/`) con auditoria trazable
  (`mem_costs_audit.md`, `audit_pydataxm_horizon.csv`).
- **Suite de tests** (`tests/`, ~200 tests verdes) con cobertura
  por escenario, calibracion y herramientas Ruflo.
- **5 herramientas Ruflo quick win** (Sprint 4) + **2 inversiones**
  (Sprint 5).

### 6.6.3 Reproducibilidad

```powershell
# Reproducir el baseline de la tesis:
python main_simulation.py --data real --full --analysis

# Auditar coherencia regulatoria:
python scripts/swarm_regulatory_validator.py

# Snapshot post-run:
python scripts/ruflo_snapshot_run.py --tag "defensa-final"

# Suite de tests:
python -m pytest tests/ -q --ignore=tests/test_full_simulation_preflight.py
```

[NARRATIVA — cerrar con parrafo de gratitud y proyeccion futura.]

---

**Fin del borrador del Capitulo 6.**

Verificaciones pendientes antes de copiar a `Documentos/FinalTesis/`:

1. Reescribir todos los `[NARRATIVA — ...]` con texto del autor.
2. Verificar que las cifras coinciden con §4.9 del capitulo 4.
3. Verificar que las recomendaciones de §6.4.2 son coherentes con
   §5.5 del capitulo 5.
4. Agregar agradecimientos formales (asesores Pantoja/Obando, MTE
   Udenar, comunidad academica).
5. Anadir referencias BibTeX completas para todas las citas.
