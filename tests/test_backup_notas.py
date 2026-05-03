"""
tests/test_backup_notas.py — C4 Backup numerado de notas
==========================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Tests del backup wrapper. Usa tmp_path para no tocar el repo real.

Referencia: scripts/backup_notas_tesis.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.backup_notas_tesis import make_backup, list_backups


def test_backup_se_crea(tmp_path):
    src = tmp_path / "notas.md"
    src.write_text("# notas\nL1\nL2\n", encoding="utf-8")
    out = make_backup(src, tmp_path / ".bak")
    assert out is not None
    assert out.exists()
    assert out.read_text(encoding="utf-8") == "# notas\nL1\nL2\n"


def test_backup_no_existe_source(tmp_path):
    out = make_backup(tmp_path / "no_existe.md", tmp_path / ".bak")
    assert out is None


def test_backup_keep_prune(tmp_path):
    """`keep=N` mantiene solo los N mas recientes."""
    src = tmp_path / "notas.md"
    src.write_text("v1", encoding="utf-8")
    bak_dir = tmp_path / ".bak"
    # Crear 5 backups con sleeps minimos para timestamps distintos.
    for i in range(5):
        src.write_text(f"v{i}", encoding="utf-8")
        time.sleep(1.05)  # >1s para timestamp con resolucion de segundos
        make_backup(src, bak_dir, keep=3)
    backups = list_backups(bak_dir, stem="notas")
    assert len(backups) == 3, f"esperan 3 backups, hay {len(backups)}"


def test_list_backups_orden_decreciente(tmp_path):
    src = tmp_path / "notas.md"
    bak_dir = tmp_path / ".bak"
    src.write_text("v1", encoding="utf-8")
    make_backup(src, bak_dir)
    time.sleep(1.05)
    src.write_text("v2", encoding="utf-8")
    make_backup(src, bak_dir)
    bs = list_backups(bak_dir, stem="notas")
    assert len(bs) == 2
    assert bs[0].stat().st_mtime >= bs[1].stat().st_mtime
