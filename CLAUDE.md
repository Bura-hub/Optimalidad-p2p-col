# Tesis P2P — Brayan S. Lopez-Mendez · Udenar 2026

Instrucciones persistentes para Claude Code en este repositorio.
Cargado automáticamente al inicio de cada sesión.

---

## Proyecto

Tesis de maestría: **"Análisis de Optimalidad y Validación Regulatoria
de Mercados P2P en Colombia"**.

- Autor: Brayan S. Lopez-Mendez
- Asesores: Andrés Pantoja, Germán Obando
- Programa: Maestría en Ingeniería Electrónica, Universidad de Nariño
- Modelo base: Sofía Chacón et al. (2025) — `Documentos/copy/JoinFinal.m`

El repositorio valida un mercado P2P (teoría de juegos + dinámica de
replicador + relajación Lagrangiana) contra cuatro escenarios
regulatorios colombianos (C1–C4), usando datos empíricos del proyecto
**MTE — Medición de Tecnologías de Energía** (5 instituciones en Pasto,
Nariño; Jul 2025 – Ene 2026).

---

## Archivos de lectura obligatoria antes de actuar

| Qué buscas | Archivo |
|---|---|
| Objetivos, actividades, alcance de la tesis | `Documentos/PropuestaTesis.txt` |
| Algoritmo P2P original | `Documentos/copy/JoinFinal.m`, `Bienestar6p.py` |
| Estado actual del código | `README.md` |
| Últimos resultados reportados | `REPORTE_AVANCES.md` |
| Decisiones previas de diseño | `Documentos/notas_modelo_tesis.md` |

---

## Stack técnico

- **Python 3.11+** (pandas ≥2.0, numpy, scipy, tqdm, matplotlib, openpyxl)
- **SALib** para sensibilidad global Sobol/Saltelli (cuando se implemente)
- **pydataxm** para precios de bolsa XM Colombia
- Windows 10/11 con PowerShell. Usar `ProcessPoolExecutor` con
  `multiprocessing.freeze_support()` obligatorio.
- Entorno virtual: `.venv/` (no commitear).

---

## Comandos clave

```powershell
# Caso sintético (validación rápida, ~35 s)
python main_simulation.py

# Perfil diario promedio MTE (~2 min)
python main_simulation.py --data real

# Perfil diario + sensibilidad + factibilidad (~15 min)
python main_simulation.py --data real --analysis

# Horizonte completo 5160 h (~20-30 min)
python main_simulation.py --data real --full --analysis

# Tests
python -m pytest tests/ -q

# Diagnóstico de datos MTE
python diagnostico_datos.py
```

Variables de entorno soportadas:

- `MTE_ROOT` — ruta a la carpeta `MedicionesMTE/`
- `XM_PRICES_CSV` — ruta a CSV alternativo de precios XM

---

## Reglas críticas (inviolables)

1. **Idioma**: español académico formal en texto; inglés solo en
   identificadores de código si corresponde al estándar.
2. **Unidades**: kW, kWh, COP/kWh, hora local `America/Bogota`.
3. **No commitear**: `MedicionesMTE/`, `*.log`, `.venv/`, `__pycache__/`,
   `*.xlsx` generados automáticamente (salvo los ya versionados).
4. **No push a remoto** salvo petición explícita del usuario.
5. **No modificar** `.gitconfig` ni config global.
6. **Commits atómicos** en español imperativo, con referencia a la
   actividad de la propuesta cuando aplique
   (ej: `Act 1.0 — agrega documento de inventario formal`).
7. **Antes de cerrar una tarea**: correr `pytest tests/ -q` y el comando
   relevante de simulación.
8. **Ambigüedad regulatoria**: si no está claro qué dice la CREG 174,
   CREG 101 072 o CREG 101 066, **pregunta al usuario**; no asumas.
9. **Runs largos**: redirige stdout a `outputs/run_<fecha>.log` y
   respalda los `.xlsx` previos.

---

## Skills disponibles (`.claude/skills/`)

Se activan automáticamente según el contexto; su descripción está en
el frontmatter. No necesitas cargarlas manualmente.

- **`tesis-p2p-context`** — Convenciones del proyecto, reglas de
  fidelidad al modelo base, trazabilidad con la propuesta, anti-patrones.
  Se activa al editar `core/`, `scenarios/`, `analysis/`, `data/` o
  `Documentos/`.
- **`run-long-simulations`** — Protocolo para ejecuciones costosas
  (`--full`, Sobol, bootstrap): `block_until_ms`, redirección de logs,
  checkpoints, detección de cuelgue, paralelismo en Windows.
  Se activa cuando se lanzan runs que pueden durar más de 2 minutos.
- **`academic-writing-es`** — Estilo de redacción académica en español,
  formato IEEE, evitar anglicismos, estructura de inventario y revisión
  bibliográfica, checklist de entrega.
  Se activa al editar cualquier `Documentos/*.md` o el `REPORTE_AVANCES.md`.

Consulta el `SKILL.md` correspondiente cuando necesites el detalle
operativo de cada una.

---

## Estructura del repositorio

```
SistemaBL/
├── main_simulation.py          # Orquestador (4 modos de ejecución)
├── core/                       # Núcleo EMS: Stackelberg + RD
├── scenarios/                  # C1–C4 + motor de comparación
├── analysis/                   # Sensibilidad, factibilidad, optimalidad
├── data/                       # Cargadores MTE/XM + parámetros base
├── visualization/              # Generación de figuras
├── tests/                      # Validación y calibración
├── Documentos/                 # Propuesta, notas, PDF de referencia
│   └── copy/                   # Código MATLAB original de Sofía
├── MedicionesMTE/              # Datos empíricos (NO commitear)
├── graficas/                   # Figuras generadas
├── outputs/                    # Logs y checkpoints de runs
└── .claude/skills/             # Skills de contexto
```

---

## Trazabilidad con la propuesta

Cada módulo de `analysis/` y `scenarios/` debe referenciar la actividad
correspondiente en el docstring. Actividades válidas:

**1.0, 1.1, 1.2** (Objetivo 1) · **2.1, 2.2** (Objetivo 2) ·
**3.1, 3.2, 3.3** (Objetivo 3) · **4.1, 4.2** (Objetivo 4)

No inventes numeraciones adicionales.

---

## Cuando algo no está claro

1. Relee el archivo de propuesta (`Documentos/PropuestaTesis.txt`).
2. Si sigue sin estar claro, consulta `REPORTE_AVANCES.md` y
   `Documentos/notas_modelo_tesis.md`.
3. Si persiste la duda, **pregunta al usuario** antes de tomar una
   decisión que afecte la comparación con los asesores.
