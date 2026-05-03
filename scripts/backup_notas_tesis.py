"""
scripts/backup_notas_tesis.py — C4 Backup numerado de notas_modelo_tesis.md
==============================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Crea un backup timestamp de `Documentos/notas_modelo_tesis.md` para
preservar el historial sin depender de git (útil cuando una sesión
de Claude reescribe el archivo extensivamente y se quiere conservar
el estado intermedio).

Variantes:

  python scripts/backup_notas_tesis.py
    -> crea Documentos/.notas_backups/notas_modelo_tesis_YYYYMMDD-HHMMSS.md

  python scripts/backup_notas_tesis.py --keep 10
    -> mantiene solo los últimos 10 backups (default 20).

Uso recomendado: invocar manualmente antes de pedirle a Claude que
reescriba secciones largas. Para automatizar como hook pre-edit del
harness Claude Code, ver `docs/tooling/ruflo_quickwins.md` §C4.
"""
from __future__ import annotations

import argparse
import io
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTAS = ROOT / "Documentos" / "notas_modelo_tesis.md"
BACKUP_DIR = ROOT / "Documentos" / ".notas_backups"

def _wrap_stdout_utf8():
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                       encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer,
                                       encoding="utf-8", errors="replace")


def make_backup(source: Path = NOTAS,
                 backup_dir: Path = BACKUP_DIR,
                 keep: int = 20) -> Path | None:
    """
    Copia `source` a `backup_dir/<stem>_<timestamp>.md`. Mantiene solo
    los `keep` mas recientes. Devuelve la ruta del backup creado.
    """
    if not source.exists():
        print(f"  [C4] No existe {source}; nada que respaldar.")
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_dir / f"{source.stem}_{ts}{source.suffix}"
    shutil.copy2(source, target)

    # Limpieza: mantener solo `keep` mas recientes.
    backups = sorted(
        backup_dir.glob(f"{source.stem}_*{source.suffix}"),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    pruned = []
    for old in backups[keep:]:
        try:
            old.unlink()
            pruned.append(old.name)
        except OSError:
            pass

    try:
        rel = target.relative_to(ROOT)
    except ValueError:
        rel = target  # tests con tmp_path
    print(f"  [C4] Backup -> {rel} "
          f"({target.stat().st_size} bytes)")
    if pruned:
        print(f"  [C4] Pruned {len(pruned)} backups antiguos "
              f"(keep={keep}): {', '.join(pruned[:3])}"
              + (" ..." if len(pruned) > 3 else ""))
    return target


def list_backups(backup_dir: Path = BACKUP_DIR,
                  stem: str = "notas_modelo_tesis",
                  suffix: str = ".md") -> list[Path]:
    """Lista los backups existentes ordenados por fecha (mas reciente primero)."""
    if not backup_dir.is_dir():
        return []
    return sorted(
        backup_dir.glob(f"{stem}_*{suffix}"),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keep", type=int, default=20,
                    help="Numero maximo de backups a conservar (default 20).")
    ap.add_argument("--list", action="store_true",
                    help="Solo lista backups existentes; no crea uno nuevo.")
    args = ap.parse_args()

    if args.list:
        bs = list_backups()
        if not bs:
            print(f"  [C4] No hay backups en {BACKUP_DIR}.")
            return 0
        print(f"  [C4] Backups existentes ({len(bs)}):")
        for b in bs:
            ts = datetime.fromtimestamp(b.stat().st_mtime)
            try:
                rel = b.relative_to(ROOT)
            except ValueError:
                rel = b
            print(f"        {rel}  "
                  f"({b.stat().st_size} bytes, {ts:%Y-%m-%d %H:%M:%S})")
        return 0

    target = make_backup(NOTAS, BACKUP_DIR, keep=args.keep)
    return 0 if target else 1


if __name__ == "__main__":
    _wrap_stdout_utf8()
    sys.exit(main())
