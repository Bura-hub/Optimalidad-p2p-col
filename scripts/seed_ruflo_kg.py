"""Sembrado del grafo de conocimiento Ruflo para la tesis P2P.

Extrae nodos (modulos Python en core/scenarios/analysis/data/visualization
+ documentos clave) y aristas (imports cruzados, referencias tesis) y los
almacena como entradas en namespace 'knowledge-graph' del backend Ruflo.

Convencion de keys:
- Nodo modulo:   kg-node-<paquete>-<modulo>     (ej: kg-node-core-ems_p2p)
- Nodo doc:      kg-doc-<slug>                  (ej: kg-doc-propuesta)
- Arista:        kg-edge-<src>--<rel>--<tgt>    (ej: kg-edge-scenarios-c4--imports--core-settlement)

Idempotente: re-ejecutar sobrescribe.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ["core", "scenarios", "analysis", "data", "visualization"]

# Documentos-tesis externos al codigo (nodos de contexto)
DOC_NODES = [
    ("kg-doc-propuesta", "doc", "Documentos/PropuestaTesis.txt",
     "Propuesta formal MaIE Udenar 2026: objetivos 1-4 y actividades 1.0-4.2"),
    ("kg-doc-notas-modelo", "doc", "Documentos/notas_modelo_tesis.md",
     "Bitacora de decisiones de modelado: CAL-1..CAL-8 y rationale Stackelberg/RD"),
    ("kg-doc-joinfinal", "doc", "Documentos/copy/JoinFinal.m",
     "Algoritmo MATLAB original Sofia Chacon et al. 2025 (modelo base de fidelidad)"),
    ("kg-doc-claude-md", "doc", "CLAUDE.md",
     "Reglas inviolables del repo: idioma espanol, unidades, MTE no-commit, trazabilidad"),
    ("kg-doc-readme", "doc", "README.md",
     "Vision tecnica: estructura de modulos y comandos main_simulation"),
    ("kg-doc-reporte", "doc", "outputs/REPORTE_AVANCES.md",
     "Resultados experimentales mas recientes (post-CAL-8 2026-04-28)"),
    ("kg-doc-creg-174", "regulacion", "Documentos/PropuestaTesis.txt#creg174",
     "CREG 174: autogeneracion a pequena escala. Base del escenario C1"),
    ("kg-doc-creg-101072", "regulacion", "Documentos/PropuestaTesis.txt#creg101072",
     "CREG 101 072: marco P2P. Base del escenario C4"),
    ("kg-doc-creg-101066", "regulacion", "Documentos/PropuestaTesis.txt#creg101066",
     "CREG 101 066: complementaria a C4"),
    ("kg-doc-mte", "datos", "MedicionesMTE_v3/",
     "Datos empiricos MTE: 5 instituciones Pasto, jul2025-ene2026 (no commitable)"),
]

# Aristas tesis -> codigo (mapeo conceptual, no detectable por imports)
SEMANTIC_EDGES = [
    # Regulacion -> escenario que la implementa
    ("kg-doc-creg-174", "implementa", "kg-node-scenarios-scenario_c1_creg174"),
    ("kg-doc-creg-101072", "implementa", "kg-node-scenarios-scenario_c4_creg101072"),
    ("kg-doc-creg-101066", "complementa", "kg-node-scenarios-scenario_c4_creg101072"),
    # Modelo MATLAB -> port Python
    ("kg-doc-joinfinal", "porta-a", "kg-node-core-ems_p2p"),
    ("kg-doc-joinfinal", "porta-a", "kg-node-core-replicator_sellers"),
    ("kg-doc-joinfinal", "porta-a", "kg-node-core-replicator_buyers"),
    # Datos crudos -> cargador
    ("kg-doc-mte", "cargado-por", "kg-node-data-xm_data_loader"),
    ("kg-doc-mte", "cargado-por", "kg-node-data-preprocessing"),
    # Propuesta -> actividades (manual: que modulo cumple que actividad)
    ("kg-doc-propuesta", "actividad-2.1", "kg-node-core-ems_p2p"),
    ("kg-doc-propuesta", "actividad-2.2", "kg-node-core-replicator_sellers"),
    ("kg-doc-propuesta", "actividad-3.1", "kg-node-scenarios-comparison_engine"),
    ("kg-doc-propuesta", "actividad-3.2", "kg-node-analysis-monthly_report"),
    ("kg-doc-propuesta", "actividad-3.3", "kg-node-analysis-p2p_breakdown"),
    ("kg-doc-propuesta", "actividad-4.1", "kg-node-analysis-optimality"),
    ("kg-doc-propuesta", "actividad-4.2", "kg-node-analysis-global_sensitivity"),
    ("kg-doc-propuesta", "actividad-1.0", "kg-node-data-base_case_data"),
    ("kg-doc-propuesta", "actividad-1.1", "kg-node-data-cedenar_tariff"),
    ("kg-doc-propuesta", "actividad-1.2", "kg-node-data-xm_prices"),
]

IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", re.MULTILINE)
DOCSTRING_RE = re.compile(r'"""(.+?)"""', re.DOTALL)


def slug(text: str) -> str:
    return text.replace("\\", "-").replace("/", "-").replace(".py", "").replace("_", "_")


def extract_module_meta(path: Path) -> dict:
    """Devuelve {name, package, docstring_short, classes, functions, imports}."""
    src = path.read_text(encoding="utf-8", errors="replace")
    pkg = path.parent.name
    name = path.stem

    # docstring del modulo (primer triple quote)
    m = DOCSTRING_RE.search(src)
    doc = (m.group(1).strip().split("\n")[0] if m else "").replace('"', "'")[:200]

    classes = re.findall(r"^class\s+(\w+)", src, flags=re.MULTILINE)
    functions = re.findall(r"^def\s+(\w+)", src, flags=re.MULTILINE)

    imports_local = set()
    for from_mod, plain_mod in IMPORT_RE.findall(src):
        mod = from_mod or plain_mod
        if not mod:
            continue
        head = mod.split(".")[0]
        # solo imports a paquetes locales del repo
        if head in PACKAGES and head != pkg:
            target = mod.replace(".", "-")
            imports_local.add(target)
        elif head in PACKAGES and head == pkg:
            # imports dentro del mismo paquete
            target = mod.replace(".", "-")
            imports_local.add(target)

    return {
        "name": name,
        "package": pkg,
        "doc": doc,
        "n_classes": len(classes),
        "n_functions": len(functions),
        "imports": sorted(imports_local),
    }


def store(key: str, value: str, namespace: str = "knowledge-graph") -> bool:
    flat = value.replace("\n", " | ").replace('"', "'")
    cmd = (
        f'npx @claude-flow/cli@latest memory store '
        f'--key "{key}" --value "{flat}" --namespace "{namespace}"'
    )
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", shell=True,
    )
    if proc.returncode != 0 or "Data stored successfully" not in (proc.stdout + proc.stderr):
        print(f"  FAIL {key}: {proc.stderr.strip()[:150]}")
        return False
    return True


def main() -> int:
    print(f"[kg] root: {ROOT}")
    nodes_ok = 0
    edges_ok = 0
    edges_total = 0
    nodes_total = 0

    # 1. Nodos modulo Python
    for pkg in PACKAGES:
        for path in sorted((ROOT / pkg).glob("*.py")):
            if path.stem == "__init__" and path.stat().st_size < 200:
                continue
            meta = extract_module_meta(path)
            key = f"kg-node-{meta['package']}-{meta['name']}"
            value = (
                f"type: module | package: {meta['package']} | name: {meta['name']} | "
                f"path: {pkg}/{meta['name']}.py | classes: {meta['n_classes']} | "
                f"functions: {meta['n_functions']} | imports: {','.join(meta['imports']) or 'stdlib'} | "
                f"doc: {meta['doc']}"
            )
            nodes_total += 1
            if store(key, value):
                nodes_ok += 1
            # 2. Aristas import locales
            for tgt in meta["imports"]:
                # tgt viene como "core-ems_p2p" o "scenarios-c4..."
                ekey = f"kg-edge-{meta['package']}-{meta['name']}--imports--{tgt}"
                evalue = (
                    f"type: edge | rel: imports | "
                    f"src: kg-node-{meta['package']}-{meta['name']} | "
                    f"tgt: kg-node-{tgt}"
                )
                edges_total += 1
                if store(ekey, evalue):
                    edges_ok += 1

    # 3. Nodos documento
    for key, kind, path, doc in DOC_NODES:
        value = f"type: {kind} | path: {path} | resumen: {doc}"
        nodes_total += 1
        if store(key, value):
            nodes_ok += 1

    # 4. Aristas semanticas tesis -> codigo
    for src_key, rel, tgt_key in SEMANTIC_EDGES:
        ekey = f"kg-edge-{src_key.replace('kg-', '')}--{rel}--{tgt_key.replace('kg-', '')}"
        evalue = f"type: edge | rel: {rel} | src: {src_key} | tgt: {tgt_key}"
        edges_total += 1
        if store(ekey, evalue):
            edges_ok += 1

    print(f"[kg] nodos: {nodes_ok}/{nodes_total}  aristas: {edges_ok}/{edges_total}")
    return 0 if (nodes_ok == nodes_total and edges_ok == edges_total) else 1


if __name__ == "__main__":
    sys.exit(main())
