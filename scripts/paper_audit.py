"""One-shot audit script (read-only).

Verifies that paper_weef.md citations, labels, and refs match the PNG
inventory in outputs/paper/.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
paper = (ROOT / "outputs" / "paper" / "paper_weef.md").read_text(encoding="utf-8")

inc = re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", paper)
labels = re.findall(r"\\label\{(fig:[^}]+)\}", paper)
refs = re.findall(r"\\ref\{(fig:[^}]+)\}", paper)

png_dir = ROOT / "outputs" / "paper"
png_files = sorted(p.name for p in png_dir.glob("*.png"))

print(f"paper_weef.md  includegraphics: {len(inc)}")
print(f"paper_weef.md  labels         : {len(labels)}")
print(f"paper_weef.md  refs in body   : {len(refs)}")
print(f"outputs/paper  PNG files      : {len(png_files)}")
print()

missing = [g for g in inc if not (png_dir / g).exists()]
unused = [p for p in png_files if p not in inc]
unresolved = sorted(set(refs) - set(labels))
orphan_labels = [l for l in labels if l not in refs]

print(f"CITED but MISSING : {missing}")
print(f"ON DISK uncited   : {unused}")
print(f"REFS w/o LABEL    : {unresolved}")
print(f"LABELS never REFD : {orphan_labels}")
print()

# Per-figure size check (IEEE 300dpi expects PNG > 50 kB, PDF > 5 kB)
print("File sizes (cited figures only):")
print(f"  {'figure':45s}  {'PNG kB':>7s}  {'PDF kB':>7s}")
for png in inc:
    p = png_dir / png
    pdf = p.with_suffix(".pdf")
    pkb = p.stat().st_size // 1024 if p.exists() else 0
    dkb = pdf.stat().st_size // 1024 if pdf.exists() else 0
    flag_p = "" if pkb >= 50 else " <<"
    flag_d = "" if dkb >= 5 else " <<"
    print(f"  {png:45s}  {pkb:7d}{flag_p}  {dkb:7d}{flag_d}")
