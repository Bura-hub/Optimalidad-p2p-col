"""Sembrado del namespace 'bibliografia' tras auditoria CrossRef 2026-04-30.

Almacena cada correccion como entrada de busqueda semantica:
- bib-fix-<old_key>: que cambia (autor, DOI, journal)
- bib-audit-summary: resumen ejecutivo de la auditoria

Uso:
  python scripts/seed_ruflo_bibliografia.py

Idempotente.
"""
from __future__ import annotations

import subprocess
import sys

# Cada entrada: (key, evidence_grade, summary)
# evidence_grade: alta | media | baja
ENTRIES = [
    (
        "bib-audit-summary",
        "alta",
        "Auditoria CrossRef 2026-04-30 sobre 6 entradas VERIFICAR del .bib. "
        "Hallazgo: 5/6 con DOI INCORRECTO, 1/6 con autores incorrectos pero "
        "DOI correcto. Causa probable: estimacion de DOIs por PII con offset "
        "sistematico (23-119 unidades). Ver Documentos/bib_verificacion_2026-04-30.md"
    ),
    (
        "bib-fix-BernalTorres2020Solar",
        "alta",
        "BernalTorres2020Solar -> Castano2020Solar. Autores reales: "
        "Castano-Gomez M., Garcia-Rendon J.J. Journal: Lecturas de Economia "
        "(no Cuadernos). DOI correcto: 10.17533/udea.le.n93a338727 "
        "(no 10.15446/cuad.econ.v39n80.79498)."
    ),
    (
        "bib-fix-Tietjen2021Retail",
        "alta",
        "Tietjen2021Retail -> McRae2021Retail. Autores reales: "
        "McRae S.D., Wolak F.A. (no Tietjen, Lessmann, Pahle). DOI correcto: "
        "10.1016/j.jeem.2021.102541 (no .102513, off by 28)."
    ),
    (
        "bib-fix-Colombia2022P2P",
        "alta",
        "Colombia2022P2P -> Cardenas2022P2P. Autores reales: "
        "Cardenas-Alvarez J.P., Espana J.M., Ortega S. DOI correcto: "
        "10.1016/j.erss.2022.102737 (no .102714, off by 23). "
        "Estudio con 1101 usuarios Valle de Aburra Medellin."
    ),
    (
        "bib-fix-Sopha2020Prosumer",
        "alta",
        "Sopha2020Prosumer -> Hahnel2020Prosumer. DOI correcto, autores "
        "incorrectos. Reales: Hahnel U.J.J., Herberz M., Pena-Bello A., "
        "Parra D., Brosch T. (no Sopha, Klockner, Hertwich). Mismo grupo "
        "que PenaBello2022Prosumer (Nature Energy)."
    ),
    (
        "bib-fix-Guerrero2023RiskMicrogrid",
        "alta",
        "Guerrero2023RiskMicrogrid -> Herding2024RiskMicrogrid. Autores "
        "reales: Herding R., Ross E., Jones W.R., Endler E., Charitopoulos "
        "V.M., Papageorgiou L.G. Journal: Advances in Applied Energy (no "
        "e-Prime). DOI correcto: 10.1016/j.adapen.2024.100180 "
        "(no 10.1016/j.prime.2024.100439). El DOI viejo apunta a paper "
        "sobre transistores GNR, no microgrids."
    ),
    (
        "bib-fix-Tavakoli2023RiskAversion",
        "alta",
        "Tavakoli2023RiskAversion -> Mobius2023RiskAversion. Autores "
        "reales: Mobius T., Riepin I., Musgens F., van der Weijde A.H. "
        "(no Tavakoli). DOI correcto: 10.1016/j.eneco.2023.106767 "
        "(no .106886, off by 119). El DOI viejo apunta a 'Social media "
        "and energy justice', no risk aversion."
    ),
    (
        "bib-pattern-pii-doi-estimation-fail",
        "alta",
        "Patron observado: estimar DOIs por extension de codigo PII "
        "(p.ej. PII S0095069621001017 -> 10.1016/j.jeem.2021.102513) tiene "
        "offset sistematico de hasta 119 unidades. NUNCA usar este metodo. "
        "Resolver siempre via CrossRef API o sitio editorial. "
        "Recomendacion para futuras adiciones: curl api.crossref.org/works/{DOI}."
    ),
]


def store(key: str, evidence: str, summary: str, namespace: str = "bibliografia") -> bool:
    flat = summary.replace("\n", " | ").replace('"', "'")
    value = f"evidence: {evidence} | {flat}"
    cmd = (
        f'npx @claude-flow/cli@latest memory store '
        f'--key "{key}" --value "{value}" --namespace "{namespace}" --upsert'
    )
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", shell=True,
    )
    ok = proc.returncode == 0 and "Data stored successfully" in (proc.stdout + proc.stderr)
    if not ok:
        print(f"  FAIL {key}: {proc.stderr.strip()[:150]}")
    return ok


def main() -> int:
    ok = 0
    for key, evidence, summary in ENTRIES:
        print(f"[bib] storing {key}...")
        if store(key, evidence, summary):
            ok += 1
    print(f"[bib] hecho: {ok}/{len(ENTRIES)} entradas en namespace 'bibliografia'")
    return 0 if ok == len(ENTRIES) else 1


if __name__ == "__main__":
    sys.exit(main())
