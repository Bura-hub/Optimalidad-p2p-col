# Ruflo Quick Wins — Sprint 4 del plan radiant-sleeping-eagle

Manual operativo de las 5 herramientas de Sprint 4 que extienden el
uso de Ruflo más allá de los ADRs (`scripts/seed_ruflo_adr.py`).

| Quick Win | Script | Test | Namespace Ruflo |
|-----------|--------|------|-----------------|
| F2 — consistencia CAL-N | [`scripts/check_cal_consistency.py`](../../scripts/check_cal_consistency.py) | `tests/test_check_cal_consistency.py` | n/a |
| F1 — duplicación escenarios | [`scripts/check_scenario_duplication.py`](../../scripts/check_scenario_duplication.py) | `tests/test_check_scenario_duplication.py` | n/a |
| A3 — KG MTE | [`scripts/ruflo_index_mte_profiles.py`](../../scripts/ruflo_index_mte_profiles.py) | `tests/test_mte_profiles_indexer.py` | `mte_profiles` |
| A4 — snapshot post-run | [`scripts/ruflo_snapshot_run.py`](../../scripts/ruflo_snapshot_run.py) | `tests/test_ruflo_snapshot_run.py` | `runs` |
| C4 — backup notas | [`scripts/backup_notas_tesis.py`](../../scripts/backup_notas_tesis.py) | `tests/test_backup_notas.py` | n/a |

---

## F2 — Detector de inconsistencias CAL-N

Verifica que cada `CAL-N` referenciado en el repositorio tenga un ADR
correspondiente y que ningún ADR coexista con duplicados de slug.

```powershell
# Reporte humano + JSON a stderr:
python scripts/check_cal_consistency.py

# CI / agentes (fail si hay issues):
python scripts/check_cal_consistency.py --strict --json-only
```

**Caso histórico que justifica F2:** durante Sprint 1.1 se detectó que
ADR-0014 referenciaba `CAL-15` y `notas_modelo_tesis.md` referenciaba
`CAL-16` para el mismo follow-up del audit pydataxm, mientras que
ambos números ya estaban ocupados por C4 y C2 respectivamente. F2
hubiera detectado el conflicto automáticamente.

---

## F1 — Detector de duplicación entre escenarios

Compara funciones top-level de `scenarios/scenario_c*.py` por
similitud de AST normalizado (variables renombradas, docstrings
removidos, literales sentinelizados).

```powershell
# Default threshold 0.85:
python scripts/check_scenario_duplication.py

# Más permisivo:
python scripts/check_scenario_duplication.py --threshold 0.5

# Custom glob:
python scripts/check_scenario_duplication.py --pattern "core/*.py"
```

**Estado actual:** los 4 escenarios principales (C1, C2, C3, C4) son
suficientemente distintos — no hay duplicación ≥ 0.85. La máxima
similaridad observada entre helpers fue 0.541 (`spot_sensitivity_analysis`
vs `compute_pde_weights`, falso positivo).

---

## A3 — Knowledge Graph MTE indexado

Indexa los 5 perfiles institucionales como entradas semánticas en
namespace `mte_profiles`. Habilita queries como "qué institución
tiene mejor cobertura PV" o "qué inversor usa Cesmag".

```powershell
# Ver perfiles sin almacenar:
python scripts/ruflo_index_mte_profiles.py --dry-run

# Almacenar (idempotente, --upsert):
python scripts/ruflo_index_mte_profiles.py
```

**Verificación HNSW** vía `mcp__claude-flow__memory_search`:

```python
search("Cesmag inversor", namespace="mte_profiles")
# -> mte-profile-cesmag (sim 0.34)

search("institucion con mayor cobertura solar PV", namespace="mte_profiles")
# -> top-3 instituciones (sim ~0.42)
```

---

## A4 — Snapshot post-run

Captura las métricas clave de `outputs/resultados_comparacion.xlsx`
tras un `--full` y las almacena en namespace `runs` para comparación
histórica entre corridas.

```powershell
# Tras un --full --analysis:
python main_simulation.py --data real --full --analysis

# Snapshot con tag:
python scripts/ruflo_snapshot_run.py --tag "post-CAL-23"

# Sin almacenar (preview):
python scripts/ruflo_snapshot_run.py --dry-run
```

**Snapshot baseline almacenado** (key `run-post-cal23-baseline`):

```
CALs activos: 23 (1-23)
net_benefit_P2P=52,446,938   net_benefit_C1=52,465,042
net_benefit_C2=51,437,446    net_benefit_C3=50,767,203
net_benefit_C4=52,219,945
RPE_P2P_vs_C1=-0.0003   RPE_P2P_vs_C4=+0.0043
IE_P2P=0.368   kWh_P2P=3,659.31   horas_p2p_activas=1,031/6,144
gini: P2P=0.162  C1=0.147  C2=0.155  C3=0.161  C4=0.170
```

Cualquier run futuro queda comparable semánticamente vs este baseline.

---

## C4 — Backup numerado de notas_modelo_tesis.md

Crea snapshots timestamp del archivo de notas en
`Documentos/.notas_backups/` (gitignored). Útil antes de pedirle a
Claude que reescriba secciones largas.

```powershell
# Backup nuevo:
python scripts/backup_notas_tesis.py

# Listar backups existentes:
python scripts/backup_notas_tesis.py --list

# Mantener solo 10 más recientes:
python scripts/backup_notas_tesis.py --keep 10
```

### Modo automatizado (hook claude-code) — pendiente de confirmación

Para automatizar el backup como pre-edit hook de Claude Code,
modificar `~/.claude/settings.json` con:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "if echo $CLAUDE_FILE_PATHS | grep -q 'notas_modelo_tesis.md'; then python scripts/backup_notas_tesis.py --keep 20; fi"
          }
        ]
      }
    ]
  }
}
```

**Aviso (CLAUDE.md regla #5):** instalar este hook modifica config
global de Claude Code y debe hacerse con consentimiento explícito
del usuario. Ejecutar manualmente `python scripts/backup_notas_tesis.py`
antes de sesiones grandes es una alternativa segura.

---

## Estadísticas de Sprint 4

| Métrica | Valor |
|---|---|
| Scripts nuevos | 5 |
| Tests nuevos | 32 (7 F2 + 8 F1 + 4 A3 + 9 A4 + 4 C4) |
| Líneas de código | ~1 400 |
| ADRs nuevos | 0 (Sprint 4 son herramientas, no decisiones) |
| Namespaces Ruflo nuevos | 2 (`mte_profiles`, `runs`) |
| Entradas semánticas almacenadas | 6 (5 perfiles MTE + 1 baseline run) |

## Referencias

- Plan: `C:\Users\burav\.claude\plans\radiant-sleeping-eagle.md` Sprint 4
- ADR-0017 (CAL-17) — caso histórico que motivó F2
- `Documentos/notas_modelo_tesis.md` — fuente protegida por C4
