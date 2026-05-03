"""
tests/test_check_cal_consistency.py — F2 detector CAL-N
=========================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Tests del detector de inconsistencias CAL-N. Usa fixtures sintéticas
en `tmp_path` para no depender del estado real del repo.

Referencia: scripts/check_cal_consistency.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_cal_consistency.py"


def _build_fake_repo(tmp_path: Path,
                     readme_extra: str = "",
                     adr_filenames: list[str] | None = None,
                     code_files: dict[str, str] | None = None
                     ) -> Path:
    """Construye un repo sintético con docs/adr/* y archivos de código."""
    repo = tmp_path / "repo"
    adr_dir = repo / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    readme = adr_dir / "README.md"
    readme.write_text(
        "# Architecture Decision Records — Test\n\n"
        "## Indice\n\n"
        "| ID | Titulo | Estado | Fecha decision |\n"
        "|---|---|---|---|\n"
        "| 0001 | CAL-1: Iters Stackelberg | Accepted | 2026-04 |\n"
        "| 0002 | CAL-2: etha competencia | Accepted | 2026-04 |\n"
        + readme_extra,
        encoding="utf-8",
    )
    for fname in (adr_filenames or ["0001-cal1-iters.md",
                                     "0002-cal2-etha.md"]):
        (adr_dir / fname).write_text(
            f"# {fname}\nADR de prueba\n", encoding="utf-8",
        )
    for relpath, content in (code_files or {}).items():
        target = repo / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return repo


def _run_script(repo: Path, strict: bool = False) -> tuple[int, dict]:
    """Invoca el script y devuelve (exit_code, json_issues)."""
    args = [sys.executable, str(SCRIPT), "--root", str(repo),
             "--json-only"]
    if strict:
        args.append("--strict")
    res = subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8")
    if res.returncode > 1:
        raise RuntimeError(f"Script crash: {res.stderr}")
    issues = json.loads(res.stdout) if res.stdout.strip() else {}
    return res.returncode, issues


# ─── A — sin issues: repo bien formado ──────────────────────────────────────


def test_repo_limpio_sin_issues(tmp_path):
    repo = _build_fake_repo(
        tmp_path,
        code_files={"core/foo.py": "# referencia CAL-1\nimport os\n"},
    )
    code, issues = _run_script(repo)
    assert code == 0
    assert issues["summary"]["huerfanos_count"] == 0
    assert issues["summary"]["conflictos_count"] == 0
    assert issues["summary"]["no_en_readme_count"] == 0


# ─── B — huérfanos detectados ───────────────────────────────────────────────


def test_detecta_cal_huerfano(tmp_path):
    """CAL-99 citado en código pero sin ADR debe aparecer como huérfano."""
    repo = _build_fake_repo(
        tmp_path,
        code_files={"core/foo.py": "# CAL-99 fantasma\n"},
    )
    code, issues = _run_script(repo, strict=True)
    assert code == 1, "strict debe fallar con huerfanos"
    huer = [h["cal"] for h in issues["huerfanos"]]
    assert 99 in huer, f"CAL-99 deberia estar como huerfano: {issues}"


def test_huerfano_reporta_archivo_y_linea(tmp_path):
    repo = _build_fake_repo(
        tmp_path,
        code_files={
            "scripts/bar.py": "# linea 1\n# linea 2 referencia CAL-77\n",
        },
    )
    _, issues = _run_script(repo)
    huer = {h["cal"]: h["refs"] for h in issues["huerfanos"]}
    assert 77 in huer
    refs = huer[77]
    assert any(r["file"].endswith("bar.py") and r["line"] == 2
                for r in refs)


# ─── C — conflictos de slug ─────────────────────────────────────────────────


def test_detecta_conflictos_slug(tmp_path):
    """Mismo CAL-N en dos archivos ADR → conflicto."""
    repo = _build_fake_repo(
        tmp_path,
        adr_filenames=["0001-cal1-original.md",
                        "0099-cal1-duplicado.md"],
        code_files={"core/foo.py": "CAL-1 referencia\n"},
    )
    _, issues = _run_script(repo)
    assert issues["summary"]["conflictos_count"] >= 1
    assert "1" in issues["conflictos_slug"] or 1 in [
        int(k) for k in issues["conflictos_slug"]
    ]


# ─── D — ADRs sin entrada en README ─────────────────────────────────────────


def test_adr_sin_entrada_en_readme_se_reporta(tmp_path):
    """Un ADR file con CAL-9 pero sin fila en tabla → no_en_readme."""
    repo = _build_fake_repo(
        tmp_path,
        adr_filenames=["0001-cal1-iters.md", "0002-cal2-etha.md",
                        "0099-cal9-fantasma.md"],
        code_files={"foo.py": "CAL-9\n"},
    )
    _, issues = _run_script(repo, strict=True)
    assert 9 in issues["no_en_readme"]


# ─── E — strict mode ────────────────────────────────────────────────────────


def test_strict_mode_exit_code(tmp_path):
    """strict=True debe devolver 1 si hay huerfanos."""
    repo = _build_fake_repo(
        tmp_path,
        code_files={"foo.py": "CAL-99 huerfano\n"},
    )
    code_normal, _ = _run_script(repo, strict=False)
    assert code_normal == 0  # sin strict, retorna 0 incluso con issues
    code_strict, _ = _run_script(repo, strict=True)
    assert code_strict == 1


# ─── F — repo real (smoke) ──────────────────────────────────────────────────


def test_repo_real_corre_sin_crash():
    """Smoke: el detector corre sobre el repo real sin crashear."""
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--json-only"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
    )
    assert res.returncode in (0, 1), (
        f"Script crash en repo real: {res.stderr}"
    )
    issues = json.loads(res.stdout)
    assert "summary" in issues
    assert issues["summary"]["total_known_in_table"] >= 20
