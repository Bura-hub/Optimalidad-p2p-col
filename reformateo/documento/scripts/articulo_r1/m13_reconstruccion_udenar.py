"""
m13_reconstruccion_udenar.py — La reconstrucción de la generación de Udenar:
solape, factor de escala y correlación (CANON §14.42; comentario C-4)
===============================================================================
Actividades 1.0 y 4.2. Revisión r1 del artículo (envío 11297). CAL-44: el
inversor del proyecto en Udenar entra en servicio el 2025-09-03; las horas
anteriores del horizonte se reconstruyen con la curva de un inversor de
referencia del mismo sitio (`EMS_INVERTER_BACKFILL_CONFIG`), escalada por la
razón de energías de las horas en que registran los dos
(`data/preprocessing._read_ems_generation`). Esa razón y la correlación del
solape solo estaban en comentarios del código; aquí se miden.

No simula. Lee las dos series de inversor con las funciones de
`data/preprocessing.py` (las mismas que usa el modelo), reconstruye la serie
como el modelo y la contrasta con la generación de Udenar del almacén canónico
de E0 (`atribucion_supuestos.carga`, con huella).

Compuertas:
  T1  las dos series cubren el horizonte de 6 144 h; hay solape (≥ 24 h) y la
      energía de referencia en él es positiva
  T2  las horas reconstruidas son el 77,1 % del horizonte y las previas a la
      primera lectura del designado son 3 666, las dos cifras de §14.17; las
      que tampoco tienen lectura de referencia entran en cero, como en el modelo,
      y se cuentan
  T3  la serie reconstruida aquí es, hora a hora, la generación de Udenar del
      almacén canónico de E0 (diferencia ≤ 1e-6 kWh)
  T4  la energía reconstruida es el 59,3 % de la de Udenar en el horizonte
      (§14.17, redondeado a una décima)

Escribe en `SALIDAS_SERVIDOR/articulo_r1_reconstruccion_2026-11-25/`:
`m13_solape_horario.csv` (las horas del solape, con las dos series),
`m13_solape_diario.csv`, `cifras_m13.csv` y `logs/m13.log`.

    PYTHONUNBUFFERED=1 python -u reformateo/documento/scripts/articulo_r1/m13_reconstruccion_udenar.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import ar1_comun as A1

A1.SALIDA = A1.SALIDAS / "articulo_r1_reconstruccion_2026-11-25"
AS, Medicion, RAIZ = A1.AS, A1.Medicion, A1.RAIZ

import data.preprocessing as P  # noqa: E402

AGENTE = "Udenar"
N_PREVIAS = 3666                  # CANON §14.40, punto 2: las horas previas al 2025-09-03
FRAC_HORAS = 0.771                # CANON §14.17: el 77,1 % de las horas
FRAC_ENERGIA = 0.593              # CANON §14.17: el 59,3 % de la energía de Udenar
FUENTE = ("data/preprocessing.py: _read_single_inverter sobre MedicionesMTE_v3, inversor designado "
          f"{P.EMS_INVERTER_CONFIG[AGENTE]!r} y de referencia {P.EMS_INVERTER_BACKFILL_CONFIG[AGENTE]!r}")


def main() -> int:
    med = Medicion("m13", "la reconstrucción de la generación de Udenar: solape, factor y correlación")
    root = RAIZ / "MedicionesMTE_v3"
    med.exige(root.is_dir(), "falta MedicionesMTE_v3 en la raíz del repositorio")
    idx = pd.date_range("2025-04-04", "2025-12-16", freq="1h", inclusive="left")
    med.exige(len(idx) == 6144, "el horizonte no tiene 6 144 horas")
    adir = P._find_subdir(root, AGENTE)
    inv = P._find_subdir(adir, P.INVERTER_FOLDER[AGENTE]) if adir is not None else None
    med.exige(inv is not None, "no se encuentra la carpeta de inversores de Udenar")
    d_dis = P._find_subdir(inv, P.EMS_INVERTER_CONFIG[AGENTE])
    d_ref = P._find_subdir(inv, P.EMS_INVERTER_BACKFILL_CONFIG[AGENTE])
    med.exige(d_dis is not None and d_ref is not None, "falta el inversor designado o el de referencia")
    print("[ar1:m13] leyendo las dos series de inversor (lento)", flush=True)
    g = P._read_single_inverter(d_dis, idx)
    r = P._read_single_inverter(d_ref, idx)
    s = g.notna() & r.notna()
    e_ref = float(r[s].sum())
    med.exige(len(g) == len(r) == 6144 and int(s.sum()) >= 24 and e_ref > 0.0, "solape insuficiente")
    med.ok(f"T1: las dos series cubren las 6 144 h; solape de {int(s.sum())} h con energía de referencia positiva")

    falta = g.isna()
    primera = g.first_valid_index()
    previas = falta & (g.index < primera)
    despues = falta & (g.index > primera)
    med.exige(round(int(falta.sum()) / 6144, 3) == FRAC_HORAS and int(previas.sum()) == N_PREVIAS,
              f"horas reconstruidas {int(falta.sum())} y previas {int(previas.sum())}")
    sin_nada = falta & r.isna()
    med.ok(f"T2: {int(falta.sum())} horas reconstruidas, el {100 * falta.sum() / 6144:.1f} % (§14.17), "
           f"{N_PREVIAS} de ellas antes de la primera lectura del designado ({primera}); {int(sin_nada.sum())} sin ninguna lectura, en cero")

    k = float(g[s].sum()) / e_ref
    rec = g.copy()
    rec[falta] = k * r[falta]
    rec = rec.fillna(0.0)
    TT, cap = AS.tarifas(), AS.capacidades()
    e0 = AS.carga("E0", TT, cap)
    n = e0["ags"].index(AGENTE)
    dif = float(np.abs(e0["G"][n] - rec.to_numpy()).max())
    med.exige(dif <= 1e-6, f"la serie reconstruida difiere de la del almacén de E0 en {dif} kWh")
    med.ok(f"T3: la serie reconstruida es la generación de Udenar del almacén de E0 (máx. |dif| {dif:.2e} kWh)")

    frac = float(rec[falta].sum() / rec.sum())
    med.exige(round(frac, 3) == FRAC_ENERGIA, f"energía reconstruida {frac:.4f}, no {FRAC_ENERGIA}")
    med.ok(f"T4: la energía reconstruida es el {100 * frac:.1f} % de la de Udenar (§14.17)")

    gs, rs = g[s].astype(float), r[s].astype(float)
    r_hor = float(np.corrcoef(gs, rs)[0, 1])
    luz = (gs > 0) | (rs > 0)
    r_luz = float(np.corrcoef(gs[luz], rs[luz])[0, 1])
    dia = pd.DataFrame({"designado_kWh": gs, "referencia_kWh": rs}).groupby(gs.index.normalize()).agg(["sum", "count"])
    dia.columns = ["designado_kWh", "n_designado", "referencia_kWh", "n_referencia"]
    completos = dia[dia.n_designado >= 8]   # las mismas horas en los dos: solo el solape
    r_dia = float(np.corrcoef(completos.designado_kWh, completos.referencia_kWh)[0, 1])
    err_dia = (k * completos.referencia_kWh - completos.designado_kWh).abs() / completos.designado_kWh
    pend = np.polyfit(rs, gs, 1)
    med.di(f"  solape {int(s.sum())} h, del {gs.index.min()} al {gs.index.max()}; factor {k:.4f}")
    med.di(f"  r horaria {r_hor:.4f}; r en horas con generación ({int(luz.sum())} h) {r_luz:.4f}; "
           f"r diaria ({len(completos)} días completos) {r_dia:.4f}; error diario de k·ref: mediana "
           f"{100 * err_dia.median():.2f} %, máximo {100 * err_dia.max():.2f} %")

    med.tabla(pd.DataFrame({"hora": gs.index.strftime("%Y-%m-%d %H:%M"), "designado_kWh": gs.to_numpy(),
                            "referencia_kWh": rs.to_numpy()}), "m13_solape_horario.csv")
    out_dia = completos.reset_index().rename(columns={"index": "dia"})
    out_dia.iloc[:, 0] = pd.to_datetime(out_dia.iloc[:, 0]).dt.strftime("%Y-%m-%d")
    med.tabla(out_dia, "m13_solape_diario.csv")

    med.pon("m13__horas_solape", int(s.sum()), "h", FUENTE + "; horas con lectura de los dos inversores")
    med.pon("m13__primera_hora_designado", str(g.first_valid_index()), "hora local", FUENTE)
    med.pon("m13__horas_reconstruidas", int(falta.sum()), "h", FUENTE)
    med.pon("m13__horas_sin_ninguna_lectura", int(sin_nada.sum()), "h", FUENTE + "; entran con generación cero")
    med.pon("m13__horas_sin_ninguna_lectura_previas", int((sin_nada & previas).sum()), "h", FUENTE)
    med.pon("m13__horas_reconstruidas_previas", int(previas.sum()), "h", FUENTE + "; antes de la primera lectura")
    med.pon("m13__horas_reconstruidas_despues", int(despues.sum()), "h", FUENTE + "; después, sin lectura del designado")
    med.pon("m13__energia_reconstruida_previas_frac", float(rec[previas].sum() / rec.sum()), "1",
            "energía reconstruida antes de la primera lectura / energía de Udenar")
    med.pon("m13__energia_reconstruida_despues_kWh", float(rec[despues].sum()), "kWh",
            "energía reconstruida en las horas sin lectura del designado tras su primera lectura")
    med.pon("m13__factor_escala", k, "1", "energía del designado / energía de referencia en el solape")
    med.pon("m13__r_horaria", r_hor, "1", "correlación de Pearson de las dos series horarias en el solape")
    med.pon("m13__horas_con_generacion", int(luz.sum()), "h", "horas del solape con generación en alguno")
    med.pon("m13__r_horaria_con_generacion", r_luz, "1", "Pearson en las horas del solape con generación")
    med.pon("m13__dias_completos", len(completos), "días", "días con al menos 8 horas de solape (el designado no reporta de noche)")
    med.pon("m13__r_diaria", r_dia, "1", "Pearson de la energía diaria sobre las horas del solape, en esos días")
    med.pon("m13__err_diario_mediana", float(err_dia.median()), "1", "|k·ref − designado| / designado por día")
    med.pon("m13__err_diario_max", float(err_dia.max()), "1", "máximo del mismo error en esos días")
    med.pon("m13__pendiente_mco", float(pend[0]), "1", "pendiente de designado sobre referencia por MCO, horaria")
    med.pon("m13__energia_reconstruida_frac", frac, "1", "energía reconstruida / energía de Udenar en el horizonte")
    med.pon("m13__energia_udenar_kWh", float(rec.sum()), "kWh", "generación de Udenar en el horizonte (= almacén E0)")
    med.pon("m13__max_dif_almacen_E0", dif, "kWh", "máx. |reconstruida − G de Udenar en el almacén de E0|")
    med.cierra()
    return 0


if __name__ == "__main__":
    sys.exit(main())
