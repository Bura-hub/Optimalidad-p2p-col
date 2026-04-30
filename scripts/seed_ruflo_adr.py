"""Sembrado de ADRs en memoria semantica Ruflo (namespace 'adr').

Almacena un resumen-puntero por ADR existente en docs/adr/. La busqueda
semantica recupera el slug y Claude lee el archivo .md cuando lo necesita.

Idempotente: re-ejecutar sobrescribe.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = ROOT / "docs" / "adr"

# Resumen sintetico por ADR (lo que se vectoriza para busqueda).
ADR_SUMMARIES = {
    "0001-cal1-stackelberg-iters": (
        "CAL-1 stackelberg_iters=2 convergencia juego Stackelberg P_star "
        "una iteracion delta SC cero segunda iteracion captura ajuste "
        "marginal precios actividad 2.1"
    ),
    "0002-cal2-etha": (
        "CAL-2 etha=0.1 coeficiente competencia compradores inerte rango "
        "0.01 a 5.0 discrepancia JoinFinal articulo sin impacto "
        "actividad 2.1"
    ),
    "0003-cal3-alpha-dr": (
        "CAL-3 alpha_p=0.20 alpha_c=0.10 demand response fraccion demanda "
        "flexible punto inflexion 72 porciento mejora maxima literatura DR "
        "Luthander Parra prosumidores actividad 2.1 4.1"
    ),
    "0004-cal4-tau-scaling": (
        "CAL-4 tau_buyers/tau_sellers=10 escalado ODE alternativa WI WJ "
        "JoinFinal modelo conjunto vs implementacion secuencial filtros "
        "paso bajo equilibrio IE -0.39 actividad 2.1"
    ),
    "0005-cal5-theta": (
        "CAL-5 theta=0.5 insensibilidad dinamica solo afecta reporting "
        "Wj_total Wi_total no afecta solve_sellers solve_buyers "
        "JoinFinal vs ConArtLatin actividad 2.1"
    ),
    "0006-cal6-bn-lcoe-solar": (
        "CAL-6 b_n LCOE solar 225 COP/kWh homogeneo modo real Cesmag 210 "
        "Fronius IRENA UPME doble calibracion sintetico vector unidades "
        "optimizacion vs real COP/kWh hallazgo D2 cerrado actividad 1.1 1.2"
    ),
    "0007-cal7-stackelberg-alternancia": (
        "CAL-7 alternancia Stackelberg secuencial vs ODE conjunta "
        "JoinFinal ode15s mismo punto fijo Nash invariante factorizacion "
        "operador contractivo paralelizacion ProcessPoolExecutor golden "
        "test SLSQP hallazgo A3 cerrado actividad 2.1"
    ),
    "0008-cal8-pi-gs-cedenar": (
        "CAL-8 pi_gs Cedenar tarifa mensual diferenciada vector per-agente "
        "799 oficial Udenar HUDN 959 comercial Mariana UCC Cesmag "
        "supersede 650 fallback CSV tarifas_cedenar_mensual desercion "
        "P2P AGPE C1 5/5 a 3/5 IR estables impacto +37% beneficio "
        "actividad 1.1 3.1 3.2 3.3 superseded parcialmente por ADR 0009"
    ),
    "0009-cal9-pi-gs-temporal": (
        "CAL-9 pi_gs matriz N x T mes a mes en C1 C2 C3 C4 cada hora "
        "liquida con CU del mes que la contiene CREG 174 y 101 072 "
        "liquidan mensualmente spread 766.80 a 816.98 oficial NT2 "
        "as_pi_gs_array helper canonico backward compatible "
        "supersede parcialmente CAL-8 fase 2 vector N para full y "
        "single_day perfil diario conserva CAL-8 promedio horizonte "
        "tests 43/43 actividad 1.1 3.1 3.2 3.3"
    ),
}


def store(key: str, value: str, namespace: str = "adr") -> bool:
    flat = value.replace("\n", " | ").replace('"', "'")
    cmd = (
        f'npx @claude-flow/cli@latest memory store '
        f'--key "{key}" --value "{flat}" --namespace "{namespace}" --upsert'
    )
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", shell=True,
    )
    return proc.returncode == 0 and "Data stored successfully" in (proc.stdout + proc.stderr)


def main() -> int:
    if not ADR_DIR.is_dir():
        print(f"[adr] ERROR: {ADR_DIR} no existe")
        return 1

    ok = 0
    for adr_path in sorted(ADR_DIR.glob("000*.md")):
        slug = adr_path.stem  # ej: 0001-cal1-stackelberg-iters
        # Extrae titulo H1 del archivo
        first_line = adr_path.read_text(encoding="utf-8").splitlines()[0]
        title = re.sub(r"^#+\s*", "", first_line).strip()

        summary = ADR_SUMMARIES.get(slug, "")
        value = (
            f"adr_id: {slug.split('-')[0]} | titulo: {title} | "
            f"path: docs/adr/{slug}.md | resumen: {summary}"
        )
        key = f"adr-{slug}"
        print(f"[adr] storing {key} ({len(value)} chars)...")
        if store(key, value):
            ok += 1
        else:
            print(f"  FAIL {key}")

    total = len(list(ADR_DIR.glob("000*.md")))
    print(f"[adr] hecho: {ok}/{total} ADRs sembrados en namespace 'adr'")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
