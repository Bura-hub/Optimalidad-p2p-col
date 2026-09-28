"""Energía y excedente del mercado por régimen del reposo, en los 13 casos.

Actividad 1.1 (verificación del núcleo). Punto C1 de la preparación antes de
redactar (2026-09-27).

La validación dinámica del 2026-09-19 (M-A) juzgó 22 horas: donde la dinámica
llegó al reposo, llegó al de la forma cerrada en 20. Llegó en los regímenes
«interiores», «topados», «suma_no_cabe» y «un_comprador»; en
«compradores_cortos» y «excluidos» no llegó en ninguna hora, de modo que ahí
la forma cerrada es una regla declarada (junto con D64, el despacho de
vendedores, y D53, la saturación cuando la suma no cabe). Este guion mide qué
parte de la energía transada y del excedente del mercado cae en cada grupo,
leyendo los almacenes de la matriz canónica sin volver a simular.

- Régimen publicado: columna `regimen` de la tabla `horas` (incluye «cuantal»,
  D71); régimen de la forma cerrada: `regimen_cerrado` (sin la rama cuantal).
- Energía: `volumen` de `horas` (kWh).
- Excedente del mercado: suma por hora de `ahorro_comprador + prima_vendedor`
  de la tabla `flujos` (COP), es decir, la banda repartida.

Salida en SALIDAS_SERVIDOR/energia_por_regimen_2026-09-27/:
  por_regimen_13casos.csv   caso, columna, régimen, horas, kWh, COP y sus %
  por_grupo_13casos.csv     lo mismo agrupado en «alcanzado por la dinámica»,
                            «regla declarada» y «cuantal»
  procedencia.txt

Uso:
    .venv/Scripts/python.exe reformateo/documento/scripts/energia_por_regimen.py
"""
from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
MATRIZ = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_matriz_reposo_2026-09-19"
          / "SALIDAS_SERVIDOR" / "matriz_reposo")
SALIDA = RAIZ / "SALIDAS_SERVIDOR" / "energia_por_regimen_2026-09-27"
CASOS = ["E0", "E1", "E2", "E3", "E4", "E5", "P1", "P2", "K1", "I1", "N1",
         "CV2", "SINU"]

# M-A (2026-09-19): regímenes a los que la dinámica llegó y en los que la forma
# cerrada se confirmó (20 de 22 horas juzgadas), y los que nunca alcanzó.
ALCANZADOS = {"interiores", "topados", "suma_no_cabe", "un_comprador"}
DECLARADOS = {"compradores_cortos", "excluidos"}
CUANTAL = {"cuantal"}
# Horas clasificadas sin intercambio: no aportan energía ni excedente, y se
# comprueba que así sea.
SIN_MERCADO = {"sin_mercado", "sin_ganancia"}          # D61


def grupo(regimen: str) -> str:
    if regimen in ALCANZADOS:
        return "alcanzado por la dinámica"
    if regimen in DECLARADOS:
        return "regla declarada"
    if regimen in CUANTAL:
        return "cuantal (D71)"
    if regimen in SIN_MERCADO:
        return "sin mercado"
    raise ValueError(f"régimen desconocido: {regimen!r}")


def lee_caso(caso: str) -> pd.DataFrame:
    alm = MATRIZ / caso / "almacen" / "m1"
    if not alm.is_dir():
        raise FileNotFoundError(f"no está el almacén de {caso}: {alm}")
    h = pd.read_parquet(alm / "horas")
    f = pd.read_parquet(alm / "flujos")
    # Revisión C1-C8: sin rellenar antes de comprobar. Las horas sin mercado
    # (régimen nulo) pueden no traer volumen; las que tienen régimen, sí.
    con_intercambio = h["regimen"].notna() & ~h["regimen"].isin(SIN_MERCADO)
    if not np.isfinite(h.loc[con_intercambio, "volumen"].to_numpy()).all():
        raise ValueError(f"{caso}: volumen no finito en horas con intercambio")
    # Las horas «sin_mercado» y «sin_ganancia» no traen volumen por
    # construcción (no hubo intercambio): se anotan como cero, explícitamente.
    sin_int = h["regimen"].isin(SIN_MERCADO)
    h.loc[sin_int, "volumen"] = h.loc[sin_int, "volumen"].fillna(0.0)
    exc = (f["ahorro_comprador"] + f["prima_vendedor"]).groupby(f["hora"]).sum()
    if not np.isfinite(exc.to_numpy()).all():
        raise ValueError(f"{caso}: excedente no finito en los flujos")
    h = h[h["regimen"].notna()].copy()           # solo horas con mercado
    h["excedente"] = h["hora"].map(exc).fillna(0.0)
    sm = h[h["regimen"].isin(SIN_MERCADO)]
    if len(sm) and (sm["volumen"].abs().max() > 1e-9
                    or sm["excedente"].abs().max() > 1e-6):
        raise ValueError(f"{caso}: horas «sin_mercado» con energía o "
                         f"excedente distinto de cero")
    sin_flujo = set(exc.index) - set(h["hora"])
    if sin_flujo:
        raise ValueError(f"{caso}: {len(sin_flujo)} horas con flujos y sin "
                         f"régimen en la tabla horas")
    return h


def resume(h: pd.DataFrame, caso: str, col: str) -> pd.DataFrame:
    g = h.groupby(h[col]).agg(horas=("hora", "size"), kwh=("volumen", "sum"),
                              cop=("excedente", "sum")).reset_index()
    g = g.rename(columns={col: "regimen"})
    g.insert(0, "columna", col)
    g.insert(0, "caso", caso)
    for c in ("horas", "kwh", "cop"):
        tot = g[c].sum()
        g[f"{c}_pct"] = 100.0 * g[c] / tot if tot > 0 else 0.0
    return g


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    filas = []
    for caso in CASOS:
        h = lee_caso(caso)
        filas.append(resume(h, caso, "regimen"))
        filas.append(resume(h, caso, "regimen_cerrado"))
        print(f"  {caso:5} {len(h):5d} horas con mercado · "
              f"{h['volumen'].sum():12.2f} kWh · {h['excedente'].sum():14.0f} COP")
    por = pd.concat(filas, ignore_index=True)
    por.to_csv(SALIDA / "por_regimen_13casos.csv", index=False)

    pub = por[por["columna"] == "regimen"].copy()
    pub["grupo"] = pub["regimen"].map(grupo)
    gr = pub.groupby(["caso", "grupo"], sort=False)[
        ["horas", "kwh", "cop", "horas_pct", "kwh_pct", "cop_pct"]].sum()
    gr = gr.reset_index()
    gr.to_csv(SALIDA / "por_grupo_13casos.csv", index=False)

    try:
        cabeza = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ,
                                capture_output=True, text=True,
                                check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as e:
        raise RuntimeError(f"no se pudo leer el HEAD de git: {e}") from e
    (SALIDA / "procedencia.txt").write_text(
        f"guion: reformateo/documento/scripts/energia_por_regimen.py\n"
        f"codigo: {cabeza}\nfecha: {dt.datetime.now().isoformat(timespec='seconds')}\n"
        f"fuente: {MATRIZ.relative_to(RAIZ).as_posix()} (canon 2026-09)\n"
        f"alcanzados (M-A): {sorted(ALCANZADOS)}\n"
        f"regla declarada: {sorted(DECLARADOS)}\n", encoding="utf-8")

    piv = gr.pivot(index="caso", columns="grupo", values="kwh_pct").reindex(CASOS)
    print("\n  % de la energía transada por grupo")
    print(piv.round(2).to_string())
    piv2 = gr.pivot(index="caso", columns="grupo", values="cop_pct").reindex(CASOS)
    print("\n  % del excedente del mercado por grupo")
    print(piv2.round(2).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
