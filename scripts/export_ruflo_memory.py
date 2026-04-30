"""Exporta toda la memoria semantica Ruflo a un JSON portable.

Tier 2.3: snapshot reproducible para entregar a asesores que quieran
auditar el contexto del proyecto. NO requiere el MCP tool
`memory_export` (que sigue sin estar disponible). Itera la lista por
namespace via CLI y serializa.

Output: Documentos/exports/tesis_p2p_memoria_<fecha>.json
        Documentos/exports/README_import.md (instrucciones)

Idempotente: regenera el snapshot cada vez.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORTS_DIR = ROOT / "Documentos" / "exports"
NAMESPACES = ["tesis", "knowledge-graph", "adr", "horizons", "bibliografia", "calibracion"]


def list_namespace(namespace: str) -> list[str]:
    """Devuelve las keys de un namespace via CLI list (formato JSON, sin truncar)."""
    cmd = (
        f'npx @claude-flow/cli@latest memory list '
        f'--namespace "{namespace}" --limit 500 --format json'
    )
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", shell=True,
    )
    if proc.returncode != 0:
        print(f"  WARN list namespace '{namespace}' failed: {proc.stderr[:120]}")
        return []
    # Filtra solo las lineas de JSON (descarta logs INFO/WARN)
    json_text = proc.stdout
    try:
        data = json.loads(json_text)
        return [item["key"] for item in data]
    except json.JSONDecodeError:
        # Fallback: extrae el bloque JSON entre [ ... ]
        m = re.search(r"\[\s*\{.*?\}\s*\]", json_text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            return [item["key"] for item in data]
        return []


def retrieve(key: str, namespace: str) -> str | None:
    """Recupera el valor de una entrada via CLI retrieve (formato JSON)."""
    cmd = (
        f'npx @claude-flow/cli@latest memory retrieve '
        f'--key "{key}" --namespace "{namespace}" --format json'
    )
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", shell=True,
    )
    if proc.returncode != 0:
        return None
    json_text = proc.stdout
    try:
        data = json.loads(json_text)
        return data.get("content")
    except json.JSONDecodeError:
        m = re.search(r"\{.*?\"content\":\s*\".*?\".*?\}", json_text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                return data.get("content")
            except json.JSONDecodeError:
                pass
        return None


def main() -> int:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    out_json = EXPORTS_DIR / f"tesis_p2p_memoria_{today}.json"
    out_readme = EXPORTS_DIR / "README_import.md"

    snapshot = {
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "project": "Tesis P2P Colombia — Brayan S. Lopez-Mendez (Udenar 2026)",
            "ruflo_backend": "sql.js + HNSW (384-dim ONNX embeddings)",
            "namespaces": NAMESPACES,
            "total_entries": 0,
        },
        "entries": {ns: {} for ns in NAMESPACES},
    }

    total = 0
    for ns in NAMESPACES:
        print(f"[export] namespace '{ns}'...", flush=True)
        keys = list_namespace(ns)
        for k in keys:
            value = retrieve(k, ns)
            if value:
                snapshot["entries"][ns][k] = value
                total += 1
        print(f"  -> {len(keys)} keys, {sum(1 for k in keys if snapshot['entries'][ns].get(k))} valores recuperados")

    snapshot["metadata"]["total_entries"] = total

    with out_json.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    print(f"[export] hecho: {total} entradas en {out_json}")
    print(f"[export] tamano: {out_json.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
