"""
scripts/reporte_calidad_datos_por_medidor.py
--------------------------------------------
Reporte de calidad de datos POR MEDIDOR e inversor, desglosado POR MES.

Responde a la variable del Excel `Documentos/reuniones/Variables_MTE_Revisado.xlsx`
"Fallas en el sistema de informacion (% de desconexion o de integracion de datos)"
y a la propuesta del IP del MTE (Wilson Achicanoy) de reportar, por medidor/inversor,
el porcentaje de datos faltantes/imputados por mes y el "mejor periodo" de cobertura.

ES UN ANALISIS SOBRE LA DATA CRUDA: NO re-corre el modelo P2P, NO toca ninguna cifra
canonica (M1/M3, bootstrap, GSA). Solo agrega variables nuevas de calidad de datos.

Reutiliza los cargadores validados del pipeline de la tesis (data/preprocessing.py,
data/xm_data_loader.py). La cobertura horaria se calcula sobre el horizonte canonico
2025-04-04 -> 2025-12-16 (6144 h). "Faltante" = hora sin lectura cruda (la que el
pipeline imputa si el hueco es <=24h, o deja como hueco si es mayor).

Uso:
    python scripts/reporte_calidad_datos_por_medidor.py
    python scripts/reporte_calidad_datos_por_medidor.py --root "C:/ruta/a/MedicionesMTE_v3"

Salidas:
    outputs/calidad_datos_por_medidor.csv     (tabla larga: fuente x mes)
    outputs/calidad_datos_por_medidor_resumen.csv  (resumen por fuente)
    Documentos/reporte_calidad_datos_MTE.md   (reporte formateado, listo para entregar)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from data.preprocessing import _find_subdir, _read_single_meter  # noqa: E402
from data.xm_data_loader import COL_DEMAND, COL_GEN, T_START, T_END, AGENTS  # noqa: E402

GAP_IMPUTABLE_H = 24  # el pipeline interpola huecos <= 24 h; mayores = "hueco real"

# Ventana diurna para inversores: la generacion FV es diurna, asi que medir la
# cobertura sobre las 24 h confunde "noche sin sol" con "dato faltante" y vuelve
# incomparables los inversores (unos registran 0 de noche, otros no registran).
# Se mide la cobertura de generacion en la franja diurna [HORA_DIA_INI, HORA_DIA_FIN).
HORA_DIA_INI, HORA_DIA_FIN = 6, 18

# Patrones tolerantes al typo de la fuente ("eletricMeter" en Cesmag) y a las
# variantes de capitalizacion de las carpetas de inversores. "tricmeter" casa
# tanto "elecTRICMETER" como "eleTRICMETER" (typo Cesmag).
MEDIDOR_PAT = "tricmeter"
INVERSOR_PAT = ("inverter", "inversor")    # casa Inverters / inverter / Inverter


def _hourly_index() -> pd.DatetimeIndex:
    """Horizonte canonico horario (6144 h)."""
    return pd.date_range(T_START, T_END, freq="1h", inclusive="left")


def _enumerar_fuentes(root: Path) -> list[dict]:
    """Lista (institucion, tipo, nombre, carpeta) de cada medidor e inversor."""
    fuentes: list[dict] = []
    for agent in AGENTS:
        adir = root / agent
        if not adir.exists():
            print(f"  [WARN] institucion sin carpeta: {agent}")
            continue
        for parent in sorted(p for p in adir.iterdir() if p.is_dir()):
            name = parent.name.lower()
            if MEDIDOR_PAT in name:
                tipo, col, div = "medidor", COL_DEMAND, 1.0
            elif any(k in name for k in INVERSOR_PAT):
                tipo, col, div = "inversor", COL_GEN, 1000.0
            else:
                continue
            for sub in sorted(s for s in parent.iterdir() if s.is_dir()):
                if not any(sub.rglob("*.csv")):
                    continue
                fuentes.append(dict(institucion=agent, tipo=tipo,
                                    nombre=sub.name, carpeta=sub,
                                    col=col, div=div))
    return fuentes


def _clasificar_huecos(faltante: pd.Series) -> pd.Series:
    """Devuelve, para cada hora faltante, la longitud (h) de su racha de hueco.

    Para horas con dato devuelve 0. Permite distinguir imputables (<=24h) de
    huecos reales (>24h).

    Caveat (inversores): para inversores la serie llega filtrada a la franja
    diurna, de modo que las rachas se miden sobre el eje diurno concatenado y el
    umbral de 24h es aproximado. No afecta la cobertura % (cifra principal).
    """
    is_na = faltante.values
    n = len(is_na)
    run_len = np.zeros(n, dtype=int)
    i = 0
    while i < n:
        if is_na[i]:
            j = i
            while j < n and is_na[j]:
                j += 1
            run_len[i:j] = j - i
            i = j
        else:
            i += 1
    return pd.Series(run_len, index=faltante.index)


def _mejor_periodo(mensual: pd.DataFrame) -> str:
    """Etiqueta del rango de meses con cobertura >= 90 % mas larga."""
    buenos = mensual.index[mensual["cobertura_pct"] >= 90.0].tolist()
    if not buenos:
        if mensual.empty:
            return "n/d"
        top = mensual["cobertura_pct"].idxmax()
        return f"{top} (max {mensual.loc[top, 'cobertura_pct']:.0f}%)"
    # rango contiguo mas largo
    mejor_ini, mejor_fin, ini = buenos[0], buenos[0], buenos[0]
    prev = buenos[0]
    for m in buenos[1:]:
        if (pd.Period(m) - pd.Period(prev)).n == 1:
            prev = m
        else:
            if (pd.Period(prev) - pd.Period(ini)).n > (pd.Period(mejor_fin) - pd.Period(mejor_ini)).n:
                mejor_ini, mejor_fin = ini, prev
            ini, prev = m, m
    if (pd.Period(prev) - pd.Period(ini)).n > (pd.Period(mejor_fin) - pd.Period(mejor_ini)).n:
        mejor_ini, mejor_fin = ini, prev
    return mejor_ini if mejor_ini == mejor_fin else f"{mejor_ini}..{mejor_fin}"


def analizar_fuente(f: dict, idx: pd.DatetimeIndex) -> tuple[pd.DataFrame, dict]:
    """Calcula cobertura mensual y resumen de una fuente.

    Medidores: ventana 24 h (la demanda es 24 h). Inversores: ventana diurna
    (la generacion FV solo ocurre de dia; medir la noche falsearia la cobertura).
    """
    if f["tipo"] == "inversor":
        idx_use = idx[(idx.hour >= HORA_DIA_INI) & (idx.hour < HORA_DIA_FIN)]
        ventana = f"diurna {HORA_DIA_INI:02d}-{HORA_DIA_FIN:02d}h"
    else:
        idx_use = idx
        ventana = "24h"
    serie = _read_single_meter(f["carpeta"], f["col"], idx_use, divide_by=f["div"])
    faltante = serie.isna()
    run_len = _clasificar_huecos(faltante)
    hueco_real = faltante & (run_len > GAP_IMPUTABLE_H)
    imputable = faltante & (run_len <= GAP_IMPUTABLE_H)

    df = pd.DataFrame({
        "mes": idx_use.to_period("M").astype(str),
        "faltante": faltante.values,
        "hueco_real": hueco_real.values,
        "imputable": imputable.values,
    })
    g = df.groupby("mes")
    mensual = pd.DataFrame({
        "horas_totales": g.size(),
        "horas_faltantes": g["faltante"].sum(),
        "horas_imputables": g["imputable"].sum(),
        "horas_hueco_real": g["hueco_real"].sum(),
    })
    mensual["cobertura_pct"] = 100.0 * (1 - mensual["horas_faltantes"] / mensual["horas_totales"])
    mensual["faltante_pct"] = 100.0 - mensual["cobertura_pct"]
    mensual = mensual.round(2)

    tot_h = len(idx_use)
    falt = int(faltante.sum())
    resumen = dict(
        institucion=f["institucion"], tipo=f["tipo"], fuente=f["nombre"],
        ventana=ventana, horas_totales=tot_h, horas_faltantes=falt,
        horas_imputables=int(imputable.sum()), horas_hueco_real=int(hueco_real.sum()),
        cobertura_pct=round(100.0 * (1 - falt / tot_h), 2),
        faltante_pct=round(100.0 * falt / tot_h, 2),
        mayor_hueco_h=int(run_len.max()),
        mejor_periodo=_mejor_periodo(mensual),
    )
    return mensual, resumen


def escribir_markdown(largo: pd.DataFrame, resumen: pd.DataFrame,
                      root: Path, out_md: Path) -> None:
    L: list[str] = []
    L.append("# Reporte de calidad de datos MTE — por medidor e inversor\n")
    L.append("> **Qué es.** Porcentaje de datos faltantes/imputados por medidor e "
             "inversor, desglosado por mes, sobre el horizonte canónico "
             f"**{T_START} → {T_END} (6144 h)**. Responde a la variable "
             "«Fallas en el sistema de información (% de desconexión o de integración "
             "de datos)» del Excel `Variables_MTE_Revisado.xlsx` y a la propuesta del "
             "IP del MTE de reportar el mejor periodo de cobertura por fuente.\n")
    L.append("> **Método.** Se reusan los cargadores del pipeline de la tesis "
             "(`data/preprocessing.py`). «Faltante» = hora sin lectura cruda (que el "
             "pipeline imputa si la racha es ≤24 h, o deja como hueco si es mayor). "
             "Los **medidores** se evalúan sobre las 24 h; los **inversores**, sobre la "
             f"franja diurna **{HORA_DIA_INI:02d}–{HORA_DIA_FIN:02d} h** (la generación "
             "FV es diurna: medir la noche confundiría «sin sol» con «dato faltante»). "
             "Es un análisis sobre la data cruda: **no recalcula el modelo ni altera "
             "ninguna cifra canónica**.\n")
    L.append("> **Caveat.** Para inversores, la separación imputable (≤24 h) / hueco real "
             "(>24 h) se computa sobre el eje diurno concatenado, por lo que ese umbral de "
             "24 h es aproximado; la cifra principal reportada —la cobertura %— no se ve "
             "afectada por ello.\n")
    L.append(f"> **Fuente de datos.** `{root}`\n")

    # Resumen comunitario
    n_med = (resumen["tipo"] == "medidor").sum()
    n_inv = (resumen["tipo"] == "inversor").sum()
    cob_med = resumen.loc[resumen["tipo"] == "medidor", "cobertura_pct"].mean()
    cob_inv = resumen.loc[resumen["tipo"] == "inversor", "cobertura_pct"].mean()
    L.append("## Resumen ejecutivo\n")
    L.append(f"- Medidores analizados: **{n_med}** · inversores: **{n_inv}** "
             f"(total {len(resumen)} fuentes).")
    L.append(f"- Cobertura media — medidores (24 h): **{cob_med:.1f} %** · "
             f"inversores (franja diurna): **{cob_inv:.1f} %**.")
    L.append("- La baja cobertura residual se concentra en equipos de arranque tardío "
             "(p. ej. el «Inversor MTE - Udenar», operativo desde septiembre); el periodo "
             "sep–dic es el de mayor disponibilidad de generación, coincidiendo con la "
             "ventana que el IP del MTE usa en su análisis paralelo.\n")

    # Resumen por fuente
    L.append("## Resumen por fuente (horizonte completo)\n")
    L.append("| Institución | Tipo | Fuente | Cobertura % | Faltante % | "
             "Imputable h | Hueco real h | Mayor hueco h | Mejor periodo |")
    L.append("|---|---|---|---:|---:|---:|---:|---:|---|")
    for _, r in resumen.iterrows():
        L.append(f"| {r.institucion} | {r.tipo} | {r.fuente} | "
                 f"{r.cobertura_pct:.1f} | {r.faltante_pct:.1f} | "
                 f"{r.horas_imputables} | {r.horas_hueco_real} | "
                 f"{r.mayor_hueco_h} | {r.mejor_periodo} |")
    L.append("")

    # Detalle mensual por institución
    L.append("## Detalle mensual (cobertura %) por institución\n")
    meses = sorted(largo["mes"].unique())
    for inst in AGENTS:
        sub = largo[largo["institucion"] == inst]
        if sub.empty:
            continue
        L.append(f"### {inst}\n")
        L.append("| Fuente (tipo) | " + " | ".join(meses) + " |")
        L.append("|---|" + "|".join(["---:"] * len(meses)) + "|")
        for (nombre, tipo), g in sub.groupby(["fuente", "tipo"]):
            fila = g.set_index("mes")["cobertura_pct"]
            celdas = [f"{fila.get(m, float('nan')):.0f}" if m in fila.index else "—"
                      for m in meses]
            L.append(f"| {nombre} ({tipo}) | " + " | ".join(celdas) + " |")
        L.append("")

    L.append("## Lectura para la solicitud externa\n")
    L.append("- El **% de desconexión/integración de datos** por medidor/inversor y mes "
             "está en la tabla anterior y en `outputs/calidad_datos_por_medidor.csv`.")
    L.append("- El **mejor periodo** por fuente (columna homónima) permite reportar la "
             "ventana en que cada equipo operó con cobertura ≥90 %.")
    L.append("- Coherente con la **Declaración de honestidad metodológica** de la tesis "
             "(§4.4): cuantifica, ahora con granularidad por medidor, la intervención que "
             "el pipeline aplica a cada serie.\n")

    out_md.write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=os.environ.get(
        "MTE_ROOT", str(REPO / "MedicionesMTE_v3")))
    args = ap.parse_args()
    root = Path(args.root)
    if not root.exists():
        print(f"ERROR: no existe la raiz de datos: {root}")
        sys.exit(1)

    print(f"[reporte] raiz: {root}")
    idx = _hourly_index()
    print(f"[reporte] horizonte: {idx[0]} -> {idx[-1]}  ({len(idx)} h)")

    fuentes = _enumerar_fuentes(root)
    print(f"[reporte] fuentes encontradas: {len(fuentes)}")

    filas_largo: list[pd.DataFrame] = []
    resumenes: list[dict] = []
    for i, f in enumerate(fuentes, 1):
        print(f"  [{i:>2}/{len(fuentes)}] {f['institucion']:<8} {f['tipo']:<8} {f['nombre']}")
        try:
            mensual, resumen = analizar_fuente(f, idx)
        except Exception as e:  # pragma: no cover - robustez de IO
            print(f"      ERROR: {e}")
            continue
        mensual = mensual.reset_index()
        mensual.insert(0, "fuente", f["nombre"])
        mensual.insert(0, "tipo", f["tipo"])
        mensual.insert(0, "institucion", f["institucion"])
        filas_largo.append(mensual)
        resumenes.append(resumen)

    largo = pd.concat(filas_largo, ignore_index=True)
    resumen = pd.DataFrame(resumenes)

    out_csv = REPO / "outputs" / "calidad_datos_por_medidor.csv"
    out_res = REPO / "outputs" / "calidad_datos_por_medidor_resumen.csv"
    out_md = REPO / "Documentos" / "reporte_calidad_datos_MTE.md"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    largo.to_csv(out_csv, index=False, encoding="utf-8")
    resumen.to_csv(out_res, index=False, encoding="utf-8")
    escribir_markdown(largo, resumen, root, out_md)

    print(f"\n[reporte] cobertura media medidores: "
          f"{resumen.loc[resumen.tipo=='medidor','cobertura_pct'].mean():.1f}%  "
          f"inversores: {resumen.loc[resumen.tipo=='inversor','cobertura_pct'].mean():.1f}%")
    print(f"[reporte] CSV largo:   {out_csv}")
    print(f"[reporte] CSV resumen: {out_res}")
    print(f"[reporte] reporte MD:  {out_md}")


if __name__ == "__main__":
    main()
