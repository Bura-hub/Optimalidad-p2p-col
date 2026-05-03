"""
scripts/ruflo_index_mte_profiles.py — A3 Knowledge Graph MTE en Ruflo
======================================================================
Brayan S. Lopez-Mendez · Udenar 2026 · Actividad 1.0

Indexa los 5 perfiles institucionales MTE como entradas semánticas en
el namespace Ruflo `mte_profiles`. Habilita queries naturales como
"¿cuál institución tiene mejor cobertura PV?" o "¿qué tipo de inversor
usa Cesmag?" recuperables vía `mcp__claude-flow__memory_search`.

Datos por agente:
  - Categoria tarifaria (oficial / comercial) + nivel de tension.
  - Cobertura solar G/D promedio sobre el horizonte MTE.
  - Inversor EMS (Fronius vs otros) y capacidad instalada.
  - Generacion / demanda promedio en kW.
  - Tipo de medidor (NET / GROSS / NET_PARTIAL).
  - π_gs efectivo del horizonte y notas regulatorias.

Uso:
  python scripts/ruflo_index_mte_profiles.py
  python scripts/ruflo_index_mte_profiles.py --dry-run    # solo imprime
  python scripts/ruflo_index_mte_profiles.py --t-start 2025-08-01 --t-end 2025-08-08

Salida: 5 entradas en namespace `mte_profiles` (idempotente, --upsert).
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer,
                                   encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer,
                                   encoding="utf-8", errors="replace")


def cargar_mte(t_start: str, t_end: str):
    """Carga MTE completo y devuelve subset alineado."""
    from data.xm_data_loader import MTEDataLoader, slice_horizon, AGENTS
    from data.cedenar_tariff import (
        INSTITUTION_PROFILE,
        community_effective_pi_gs,
    )
    mte_root = os.environ.get("MTE_ROOT", str(ROOT / "MedicionesMTE_v3"))
    loader = MTEDataLoader(root_path=mte_root)
    D_full, G_full, idx_full = loader.load(verbose=False)
    D, G, idx = slice_horizon(D_full, G_full, idx_full, t_start, t_end)
    return D, G, idx, list(AGENTS), INSTITUTION_PROFILE


# Notas estaticas (de xm_data_loader.py + INSTITUTION_PROFILE).
INVERTER_INFO = {
    "Udenar":  ("Fronius", "Bloque Sur - Medidor 1", "NET METER"),
    "Mariana": ("Fronius - Alvernia", "Medidor 1 - Alvernia", "NET PARTIAL"),
    "UCC":     ("Fronius - UCC", "Medidor 1 - UCC", "NET PARTIAL"),
    "HUDN":    ("Inversor 1 - HUDN", "Medidor 1 - HUDN", "GROSS METER"),
    "Cesmag":  ("Inverter 1 - Cesmag", "Medidor 1 - Cesmag", "GROSS METER"),
}


def calcular_perfil(name: str, n: int, D, G, profile, t_start, t_end) -> dict:
    """Compone el perfil de una institucion."""
    inv, meter, mode = INVERTER_INFO.get(name, ("?", "?", "?"))
    dem_total = float(D[n].sum())
    gen_total = float(G[n].sum())
    cobertura = gen_total / max(dem_total, 1e-9)
    return {
        "name": name,
        "categoria": profile.categoria,
        "nivel_tension": profile.nivel_tension,
        "propiedad": profile.propiedad,
        "inverter": inv,
        "meter": meter,
        "metering_mode": mode,
        "D_mean_kW": round(float(D[n].mean()), 2),
        "D_max_kW":  round(float(D[n].max()), 2),
        "D_total_kWh": round(dem_total, 1),
        "G_mean_kW": round(float(G[n].mean()), 2),
        "G_max_kW":  round(float(G[n].max()), 2),
        "G_total_kWh": round(gen_total, 1),
        "cobertura_PV_total": round(cobertura, 4),
        "horas_con_G_pos": int((G[n] > 0).sum()),
        "horas_total":     int(D.shape[1]),
        "horizonte": f"{t_start} a {t_end}",
    }


def perfil_a_texto_semantico(p: dict) -> str:
    """Convierte el perfil dict a una cadena en lenguaje natural densa."""
    return (
        f"Institucion MTE {p['name']}: tarifa {p['categoria']} "
        f"nivel tension NT{p['nivel_tension']} propiedad {p['propiedad']}. "
        f"Inversor {p['inverter']} medidor {p['meter']} modo "
        f"{p['metering_mode']}. Demanda media {p['D_mean_kW']} kW "
        f"max {p['D_max_kW']} kW total {p['D_total_kWh']} kWh. "
        f"Generacion solar media {p['G_mean_kW']} kW max {p['G_max_kW']} kW "
        f"total {p['G_total_kWh']} kWh. Cobertura PV "
        f"{p['cobertura_PV_total']*100:.1f}% horas con generacion positiva "
        f"{p['horas_con_G_pos']}/{p['horas_total']}. Horizonte {p['horizonte']}. "
        f"Actividad 1.0 1.1 1.2 2.1"
    )


def store_in_ruflo(key: str, value: str, namespace: str = "mte_profiles"
                    ) -> bool:
    """Almacena via npx claude-flow CLI (igual patron que seed_ruflo_adr)."""
    flat = value.replace("\n", " | ").replace('"', "'")
    cmd = (
        f'npx @claude-flow/cli@latest memory store '
        f'--key "{key}" --value "{flat}" --namespace "{namespace}" --upsert'
    )
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", shell=True,
    )
    out = proc.stdout + proc.stderr
    return proc.returncode == 0 and "Data stored successfully" in out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--t-start", default="2025-04-04")
    ap.add_argument("--t-end", default="2025-12-16")
    ap.add_argument("--dry-run", action="store_true",
                    help="No almacena en Ruflo; solo imprime los perfiles.")
    ap.add_argument("--namespace", default="mte_profiles")
    args = ap.parse_args()

    print(f"  [A3] Cargando MTE [{args.t_start} .. {args.t_end})...")
    D, G, idx, agents, profiles = cargar_mte(args.t_start, args.t_end)
    print(f"  [A3] D={D.shape}, G={G.shape}, agentes={agents}")

    perfiles = []
    for n, name in enumerate(agents):
        if name not in profiles:
            print(f"  [A3] {name}: sin INSTITUTION_PROFILE, skipped")
            continue
        p = calcular_perfil(name, n, D, G, profiles[name],
                             args.t_start, args.t_end)
        perfiles.append(p)
        print(f"  [A3] {name}: cobertura={p['cobertura_PV_total']*100:.1f}% "
              f"D={p['D_mean_kW']:.2f}kW G={p['G_mean_kW']:.2f}kW "
              f"({p['inverter']})")

    if args.dry_run:
        print()
        print("  [A3] dry-run, NO almacenado en Ruflo.")
        for p in perfiles:
            print()
            print(f"  ---- {p['name']} ----")
            print(perfil_a_texto_semantico(p))
        return 0

    print()
    print(f"  [A3] Almacenando {len(perfiles)} perfiles en namespace "
          f"'{args.namespace}'...")
    ok = 0
    for p in perfiles:
        text = perfil_a_texto_semantico(p)
        key = f"mte-profile-{p['name'].lower()}"
        if store_in_ruflo(key, text, namespace=args.namespace):
            print(f"        ✓ {key}")
            ok += 1
        else:
            print(f"        ✗ {key} (fallo CLI)")
    print()
    print(f"  [A3] Hecho: {ok}/{len(perfiles)} perfiles almacenados.")
    return 0 if ok == len(perfiles) else 1


if __name__ == "__main__":
    sys.exit(main())
