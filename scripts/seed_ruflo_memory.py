"""Sembrado inicial de memoria semantica Ruflo para la tesis P2P.

Almacena resumenes-puntero de los documentos clave del proyecto en el namespace
'tesis' del backend hibrido AgentDB/HNSW. La busqueda semantica recupera el
puntero (path + sinopsis) y Claude lee el archivo real cuando lo necesita.

Ejecucion: python scripts/seed_ruflo_memory.py
Idempotente: sobrescribe la entrada si ya existe la misma --key.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (key, path_relativo, sinopsis)
ENTRIES = [
    (
        "propuesta-tesis",
        "Documentos/PropuestaTesis.txt",
        "Propuesta formal de tesis MaIE Udenar 2026: titulo, objetivo general "
        "y especificos, actividades 1.0-4.2, alcance, limitaciones, "
        "cronograma. Documento maestro: cualquier ambiguedad regulatoria, "
        "metodologica o de scope se resuelve consultandolo. Asesores: "
        "Andres Pantoja, German Obando.",
    ),
    (
        "notas-modelo-tesis",
        "Documentos/notas_modelo_tesis.md",
        "Bitacora viva de decisiones de diseno: calibraciones CAL-1..CAL-8, "
        "fundamento de Stackelberg, dinamica del replicador, parametros "
        "Cedenar, pi_GS COP/CU como fallback, rationale de scenarios C1-C4. "
        "Cualquier decision de modelado nuevo se documenta aqui (no en "
        "REPORTE_AVANCES).",
    ),
    (
        "claude-md-rules",
        "CLAUDE.md",
        "Reglas inviolables de Claude Code en este repo: idioma espanol "
        "academico, unidades kW/kWh/COP/America-Bogota, no commitear "
        "MedicionesMTE/, commits atomicos en imperativo con referencia a "
        "actividad, ambiguedad regulatoria CREG -> preguntar al usuario, "
        "stack Python 3.11/SALib/pydataxm, freeze_support obligatorio en "
        "Windows.",
    ),
    (
        "readme-estado",
        "README.md",
        "Vision tecnica del repositorio: arquitectura core/scenarios/"
        "analysis/data, comandos clave de main_simulation.py (sintetico, "
        "real, --analysis, --full), modos de ejecucion, variables MTE_ROOT y "
        "XM_PRICES_CSV, formato de outputs.",
    ),
    (
        "reporte-avances",
        "outputs/REPORTE_AVANCES.md",
        "Reporte mas reciente de resultados experimentales: figuras 10-19 "
        "vigentes, calibracion CAL-8 aplicada, p2p_breakdown.xlsx con "
        "comentarios PGS_COP/CU como fallback, comparacion C1-C4 mensual y "
        "horaria. Estado real del proyecto al 2026-04-28.",
    ),
    (
        "joinfinal-matlab-base",
        "Documentos/copy/JoinFinal.m",
        "Algoritmo P2P original de Sofia Chacon et al. (2025) en MATLAB. "
        "Base de fidelidad: cualquier port a Python en core/ debe replicar "
        "la logica de Stackelberg + dinamica del replicador descritas aqui. "
        "Antes de modificar core/, releer este archivo.",
    ),
    (
        "datos-mte",
        "MedicionesMTE_v3/",
        "Datos empiricos no commiteables: 5 instituciones en Pasto Narino, "
        "ventana Jul2025-Ene2026, kW/kWh hora local. Cargado por "
        "data/mte_loader.py via MTE_ROOT. NO commitear ningun CSV de aqui. "
        "Generan p2p_breakdown.xlsx tras correr main_simulation.py --data real.",
    ),
    (
        "regulacion-creg",
        "Documentos/PropuestaTesis.txt#regulacion",
        "Marco regulatorio colombiano que da pie a los escenarios C1-C4: "
        "CREG 174 (autogeneracion a pequena escala), CREG 101 072 y "
        "CREG 101 066. Si una decision de scenario depende del texto de una "
        "resolucion CREG, NO asumir contenido: preguntar al usuario antes "
        "de codificar la regla.",
    ),
    (
        "trazabilidad-actividades",
        "Documentos/PropuestaTesis.txt#actividades",
        "Numeracion oficial de actividades de la propuesta: 1.0/1.1/1.2 "
        "(Objetivo 1: caracterizacion empirica), 2.1/2.2 (Objetivo 2: "
        "modelo P2P), 3.1/3.2/3.3 (Objetivo 3: validacion regulatoria), "
        "4.1/4.2 (Objetivo 4: optimalidad). Cualquier modulo nuevo de "
        "analysis/ o scenarios/ debe referenciar UNA de estas en su "
        "docstring; no inventar nuevas numeraciones.",
    ),
    (
        "instrumentacion-figuras",
        "graficas/",
        "Convencion: cada figura PNG (fig10..fig19) debe acompanarse de "
        "siblings .csv y .mat con los datos exactos para reexportar a "
        "MATLAB. Patron de naming: figXX_<nombre>__<columna>.csv. Si "
        "alguna grafica nueva se genera, su sibling exporter va en "
        "visualization/.",
    ),
]


def store_entry(key: str, value: str, namespace: str = "tesis") -> bool:
    """Llama a `npx ruflo memory store` para una entrada.

    Estrategia: valor en una unica linea (separador ' | ' en lugar de \\n)
    para evitar truncamiento por shell de Windows. shell=True es necesario
    porque npx es un .cmd shim.
    """
    flat = value.replace("\n", " | ").replace('"', "'")
    quoted_value = f'"{flat}"'
    cmd = (
        f'npx @claude-flow/cli@latest memory store '
        f'--key "{key}" --value {quoted_value} --namespace "{namespace}" --upsert'
    )
    print(f"[seed] storing {namespace}/{key} ({len(flat)} chars)...", flush=True)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    ok = proc.returncode == 0 and "Data stored successfully" in (proc.stdout + proc.stderr)
    if not ok:
        print(f"  FAIL ({proc.returncode}): {proc.stderr.strip()[:200]}")
    return ok


def main() -> int:
    print(f"[seed] root: {ROOT}")
    missing = [p for _, p, _ in ENTRIES if "#" not in p and not (ROOT / p).exists()]
    if missing:
        print(f"[seed] WARN paths missing (se sembraran como referencia): {missing}")

    ok = 0
    for key, path, synopsis in ENTRIES:
        # Construye un valor compacto: ruta + sinopsis (es lo que se vectoriza).
        value = f"path: {path}\nresumen: {synopsis}"
        if store_entry(key, value):
            ok += 1
    print(f"[seed] hecho: {ok}/{len(ENTRIES)} entradas en namespace 'tesis'")
    return 0 if ok == len(ENTRIES) else 1


if __name__ == "__main__":
    sys.exit(main())
