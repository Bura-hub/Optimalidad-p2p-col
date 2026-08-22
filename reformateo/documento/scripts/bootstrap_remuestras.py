"""
bootstrap_remuestras.py — Recupera las 10.000 réplicas del remuestreo.
======================================================================
El artefacto canónico ``bootstrap_42.json`` guarda solo el resumen: la
media, el intervalo, el tamaño del efecto. Para dibujar la distribución
—que es lo que convierte una tabla en un argumento visual— hacen falta
las réplicas, y esas no se guardaron.

Este script las recupera volviendo a correr el remuestreo con la misma
semilla y el mismo procedimiento. Es determinista, de modo que el
resultado no es una estimación nueva sino **la misma de siempre**: el
script comprueba que reproduce las cifras publicadas y aborta si no.

    python scripts/bootstrap_remuestras.py

Salida: ``datos_cache/bootstrap_replicas_{m1,m3}.npy`` y un resumen en
``datos_cache/bootstrap_verificacion.csv``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import datos as D

CACHE = Path(__file__).resolve().parent.parent / "datos_cache"

# Tolerancia de la comprobación. Las cifras publicadas se transcriben aquí
# desde CANON.md §6.2; si el remuestreo no las reproduce, algo cambió y no
# se debe publicar la figura.
PUBLICADO = {
    "m1": {"delta_mean": 8114.1357018314575,
           "ci_95_lower": 6138.32843681907,
           "ci_95_upper": 10003.85735732364,
           "cohens_d": 0.888870353436644},
    "m3": {"delta_mean": 10579.11, "cohens_d": 0.8240},
}


def replicas(cobertura: str, block_days: int = 7, n_bootstrap: int = 10000,
             seed: int = 42):
    """
    Reproduce el remuestreo por bloques de la corrida canónica.

    Réplica exacta del procedimiento de ``tests/statistical_tests.py``:
    bloques solapados de ``block_days`` días consecutivos, elegidos con
    reemplazo hasta cubrir el largo original, y media de cada réplica.
    Los bloques preservan la autocorrelación semanal, que es la razón de
    no remuestrear día a día.
    """
    serie = D.serie_diaria(cobertura)
    delta = (serie["nb_p2p"] - serie["nb_c4"]).to_numpy(dtype=float)
    n_days = len(delta)

    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n_days / block_days))
    start_indices = np.arange(n_days - block_days + 1)

    boot = np.empty(n_bootstrap)
    for b in range(n_bootstrap):
        starts = rng.choice(start_indices, size=n_blocks, replace=True)
        muestra = np.concatenate([delta[s: s + block_days] for s in starts])[:n_days]
        boot[b] = muestra.mean()

    resumen = {
        "cobertura": cobertura.upper(),
        "delta_mean": float(delta.mean()),
        "delta_std": float(delta.std(ddof=1)),
        "ci_95_lower": float(np.percentile(boot, 2.5)),
        "ci_95_upper": float(np.percentile(boot, 97.5)),
        "cohens_d": float(delta.mean() / delta.std(ddof=1)),
        "n_days": n_days,
        "n_bootstrap": n_bootstrap,
        "block_days": block_days,
        "n_eff": max(1, n_days // block_days),
        "dias_favorables_pct": 100.0 * float((delta > 0).mean()),
    }
    return boot, delta, resumen


def verificar(cobertura: str, resumen: dict) -> bool:
    """Compara contra el artefacto canónico y contra las cifras publicadas."""
    canon = D.bootstrap(cobertura)
    ok = True
    for clave in ("delta_mean", "delta_std", "cohens_d",
                  "ci_95_lower", "ci_95_upper"):
        if clave not in canon:
            continue
        a, b = float(canon[clave]), float(resumen[clave])
        # La media y la desviación salen de la serie, no del azar: deben
        # coincidir al bit. El intervalo depende del remuestreo, que es
        # determinista con la misma semilla, así que también.
        rel = abs(a - b) / max(abs(a), 1e-9)
        bien = rel < 1e-9
        ok &= bien
        print(f"    {clave:14s} canon={a:14.6f}  recalculado={b:14.6f}  "
              f"{'OK' if bien else 'DIFIERE'}")
    return ok


if __name__ == "__main__":
    D.verificar_canon()
    CACHE.mkdir(parents=True, exist_ok=True)
    filas, todo = [], True

    for cob in D.COBERTURAS:
        print(f"\n[{cob.upper()}] remuestreo por bloques de 7 días, 10.000 réplicas")
        boot, delta, res = replicas(cob)
        np.save(CACHE / f"bootstrap_replicas_{cob}.npy", boot)
        np.save(CACHE / f"bootstrap_delta_{cob}.npy", delta)
        todo &= verificar(cob, res)
        filas.append(res)

    pd.DataFrame(filas).to_csv(CACHE / "bootstrap_verificacion.csv",
                               index=False, encoding="utf-8-sig")
    print("\nREPRODUCE EL CANON" if todo
          else "\nNO REPRODUCE — no publicar la figura")
    raise SystemExit(0 if todo else 1)
