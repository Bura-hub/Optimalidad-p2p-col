# Snapshot reproducible — Memoria semántica Tesis P2P

**Generado:** 2026-04-30 vía Tier 2.3 Ruflo
**Autor:** Brayan S. Lopez-Mendez | Udenar 2026
**Asesores:** Andrés Pantoja, Germán Obando

Este directorio contiene un snapshot portable del contexto semántico
del proyecto P2P. Permite que un asesor (o auditor externo) reproduzca
el "estado mental" del agente sin acceso al código fuente Python.

## Contenido

| Archivo | Tamaño | Descripción |
|---|---|---|
| `tesis_p2p_memoria_2026-04-30.json` | 28 KB | Snapshot completo: 124 entradas en 5 namespaces (texto plano, sin embeddings) |

**Namespaces incluidos:**

| Namespace | Entradas | Contenido |
|---|---:|---|
| `tesis` | 10 | Punteros a documentos maestros (PropuestaTesis, notas_modelo, CLAUDE.md, README, REPORTE_AVANCES, JoinFinal.m, MTE, regulación CREG, trazabilidad, figuras) |
| `knowledge-graph` | 100 | 32 módulos Python + 9 docs/regulación/ADR (incluye ADR 0009) + 59 aristas (imports cruzados + mapeo actividad → módulo + supersede + gobierna) |
| `adr` | 9 | Architecture Decision Records CAL-1..CAL-9 (calibraciones del modelo, incluye CAL-9 pi_gs matriz N×T) |
| `horizons` | 8 | Hitos de cierre de tesis (manuscrito + revisiones asesores + defensa) |
| `bibliografia` | 8 | Auditoría CrossRef 2026-04-30 con 6 correcciones de DOIs/autores |
| `calibracion` | 9 | Detalle CAL-9 (decisión, contexto regulatorio CREG, CU mensual oficial/comercial NT2, helper as_pi_gs_array, archivos críticos, tests, wiring por modo, indexación por posición) |

## Cómo usar el snapshot

### Opción A — Lectura directa (recomendada para asesor)

El JSON es legible. Cualquier editor de texto / `jq` / VS Code lo abre.
No requiere instalación de Ruflo.

```bash
# Inventario rápido
jq '.metadata' tesis_p2p_memoria_2026-04-30.json

# Listar las decisiones CAL-1..CAL-8
jq '.entries.adr | keys' tesis_p2p_memoria_2026-04-30.json

# Buscar por palabra clave
jq -r '.entries | to_entries[] | .value | to_entries[] | select(.value | test("Cedenar"; "i")) | "\(.key): \(.value)"' tesis_p2p_memoria_2026-04-30.json
```

### Opción B — Importar a Ruflo en otra máquina

Requiere Claude Code + `@claude-flow/cli` instalado.

```bash
# 1. Clonar el repo del proyecto en la máquina destino
git clone <repo> SistemaBL && cd SistemaBL

# 2. Inicializar runtime Ruflo
npx @claude-flow/cli@latest init --skip-claude --force --with-embeddings
npx @claude-flow/cli@latest memory init

# 3. Re-sembrar desde los scripts (idempotentes — no requieren el JSON)
python scripts/seed_ruflo_memory.py
python scripts/seed_ruflo_kg.py
python scripts/seed_ruflo_adr.py
python scripts/seed_ruflo_horizon.py
python scripts/seed_ruflo_bibliografia.py

# 4. Re-sembrar también el namespace calibracion (CAL-9):
python scripts/seed_ruflo_cal9.py

# 5. Verificar
npx @claude-flow/cli memory stats
# Total Entries esperado: ~144 (10 tesis + 100 kg + 9 adr + 8 horizons + 8 biblio + 9 calibracion)
```

**Nota:** los scripts de re-sembrado son la fuente de verdad portable.
El JSON snapshot es para auditoría humana, no para re-importación
binaria a Ruflo (la API `memory_import` requiere un formato distinto).

## Verificación de integridad

El snapshot debe contener:

```bash
$ jq '.metadata.total_entries' tesis_p2p_memoria_2026-04-30.json
144

$ jq '.entries | to_entries | map({namespace: .key, count: (.value | length)})' \
    tesis_p2p_memoria_2026-04-30.json
# [
#   { "namespace": "tesis", "count": 10 },
#   { "namespace": "knowledge-graph", "count": 100 },
#   { "namespace": "adr", "count": 9 },
#   { "namespace": "horizons", "count": 8 },
#   { "namespace": "bibliografia", "count": 8 },
#   { "namespace": "calibracion", "count": 9 }
# ]
```

## Documentos relacionados (no incluidos en el snapshot — están en el repo)

Para validar las afirmaciones del snapshot contra los documentos
fuente, el asesor necesita acceso a estos archivos del repositorio:

| Archivo | Propósito |
|---|---|
| `Documentos/PropuestaTesis.txt` | Fuente autoritativa de las 10 actividades |
| `Documentos/notas_modelo_tesis.md` | Decisiones de modelado y CAL-1..CAL-8 |
| `Documentos/Matriz_Trazabilidad.md` | Mapping actividad → módulo → figura → ADR |
| `Documentos/bib_verificacion_2026-04-30.md` | Detalle de las 6 correcciones bibliográficas |
| `Documentos/borrador_cap4_resultados.md` | Borrador estructurado del Capítulo 4 |
| `Documentos/references.bib` | Bibliografía corregida post-CrossRef |
| `outputs/REPORTE_AVANCES.md` | Resultados numéricos `--full --analysis` post-CAL-8 |
| `docs/adr/0001..0008-*.md` | Versión humana de los 8 ADRs |
| `core/`, `scenarios/`, `analysis/`, `data/` | Código Python verificable contra los ADRs |

## Re-generar el snapshot

```bash
python scripts/export_ruflo_memory.py
# Output: Documentos/exports/tesis_p2p_memoria_<fecha>.json
```

El script consume la CLI `npx @claude-flow/cli memory list/retrieve
--format json` y serializa todos los namespaces. No requiere el daemon
ni MCP tools (que pueden no estar disponibles en sesiones sin
inicializar).

---

**Privacidad:** este snapshot NO incluye datos empíricos MTE
(`MedicionesMTE_v3/` está bajo licencia restringida), tampoco PDFs de
tarifas Cedenar, ni el código fuente Python. Solo metadatos del
proyecto y resúmenes-puntero a archivos en disco. Es seguro
distribuirlo a cualquier asesor o auditor.
