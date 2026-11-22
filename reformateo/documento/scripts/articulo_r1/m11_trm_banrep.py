"""
m11_trm_banrep.py — La TRM media del horizonte contrastada con la serie del
Banco de la República (CANON §14.41, punto 5)
===============================================================================
Actividad 4.2. Revisión r1 del artículo: la TRM media del horizonte (M8,
`trm__media_horizonte` del grupo e1/AR1, 4 019,25 COP/USD) sale de la serie de
datos.gov.co (conjunto mcec-87by, Superintendencia Financiera). Aquí se
contrasta con la serie del Banco de la República, de su servicio SDMX:

    https://totoro.banrep.gov.co/sdmx/rest/data/BANREP.CIE,DF_TRM,1.0/all
        ?startPeriod=2025-03-25&endPeriod=2025-12-31
    cabecera Accept: application/vnd.sdmx.data+csv

La copia guardada está en `insumos/trm_banrep_sdmx_DF_TRM.csv` de la carpeta
de salida, con su tamaño y su sha256 fijados abajo (descarga del 2026-11-22,
idéntica byte a byte a la del 2026-11-21 de `comprobaciones_r4.md`). Con
`--descarga` el guion la vuelve a bajar y exige la misma huella; sin ella, solo
lee la copia. No se usa ninguna tasa de memoria.

LA REGLA. La de M8: la tasa vigente cada día calendario del 2025-04-04 al
2025-12-15 (256 días), cada día con una sola tasa, y la media simple. La serie
del Banco ya trae un valor por día calendario, fines de semana y festivos
incluidos, así que no hay que rellenar nada.

Compuertas:
  T1  la copia es la de la huella; una sola serie diaria COP por USD, con
      estado A, fechas sin repetir
  T2  la serie cubre los 256 días del horizonte, cada uno una vez, con tasas
      finitas y positivas
  T3  la comparación día a día con `m8_trm_diaria.csv` (e1/AR1) cubre los 256
      días; se cuentan los días distintos y la mayor diferencia
  T4  la media de M8 recalculada de `m8_trm_diaria.csv` es `trm__media_horizonte`
"""
from __future__ import annotations

import hashlib
import sys
import urllib.request

import numpy as np
import pandas as pd

import ar2_comun as R

A1, AS = R.A1, R.AS
REL = "SALIDAS_SERVIDOR/articulo_r1_resuelta_2026-11-21/insumos/trm_banrep_sdmx_DF_TRM.csv"
URL = ("https://totoro.banrep.gov.co/sdmx/rest/data/BANREP.CIE,DF_TRM,1.0/all"
       "?startPeriod=2025-03-25&endPeriod=2025-12-31")
ACCEPT = "application/vnd.sdmx.data+csv"
BR_BYTES = 41757
BR_SHA256 = "612341ad5213d63d2ef8ac42b543b7fa1c5d8eebd2e0b34dd0d6e7ddd8ea8e1b"
D0, D1 = "2025-04-04", "2025-12-15"
F_M8 = "articulo_r1_2026-11-21/m8_trm_diaria.csv"
F_AR1 = "articulo_r1_2026-11-21/cifras.csv"
FUENTE = ("Banco de la República, servicio SDMX, flujo BANREP.CIE DF_TRM 1.0 (TRM diaria COP/USD), "
          "copia insumos/trm_banrep_sdmx_DF_TRM.csv")


def descarga(p) -> None:
    req = urllib.request.Request(URL, headers={"Accept": ACCEPT, "User-Agent": "python-urllib"})
    with urllib.request.urlopen(req, timeout=60) as r:
        datos = r.read()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(datos)


def main() -> int:
    med = R.Medicion("m11", "la TRM media del horizonte frente a la serie del Banco de la República")
    p = A1.RAIZ / REL
    if "--descarga" in sys.argv:
        descarga(p)
        med.di(f"  descargada {URL}")
    if not p.is_file():
        raise SystemExit(f"[ar1:m11] falta la copia de la serie del Banco de la República en {REL}. "
                         "Corra el guion con --descarga.")
    datos = p.read_bytes()
    med.exige(len(datos) == BR_BYTES and hashlib.sha256(datos).hexdigest() == BR_SHA256,
              "la serie del Banco de la República no es la de la huella (tamaño o sha256 distintos)")
    med.insumos.append((REL, len(datos), BR_SHA256))
    t = pd.read_csv(p, dtype=str, keep_default_na=False)
    med.exige({"DATAFLOW", "FREQ", "CURRENCY", "CURRENCY_DENOM", "TIME_PERIOD", "OBS_VALUE", "OBS_STATUS"} <= set(t.columns),
              "columnas inesperadas en la serie SDMX")
    med.exige(bool((t.DATAFLOW == "BANREP.CIE:DF_TRM(1.0)").all() and (t.FREQ == "D").all()
                   and (t.CURRENCY == "COP").all() and (t.CURRENCY_DENOM == "USD").all()
                   and (t.OBS_STATUS == "A").all()),
              "la serie no es una sola serie diaria COP por USD con estado A")
    fechas = pd.to_datetime(t.TIME_PERIOD, format="%Y-%m-%d")
    med.exige(not fechas.duplicated().any(), "fechas repetidas en la serie SDMX")
    med.ok(f"T1: la copia es la de la huella ({BR_BYTES} bytes, sha256 {BR_SHA256[:12]}…), {len(t)} filas de una sola "
           "serie diaria COP/USD con estado A, sin fechas repetidas")
    s = pd.Series(pd.to_numeric(t.OBS_VALUE).to_numpy(dtype=float), index=fechas)
    dias = pd.date_range(D0, D1, freq="D")
    med.exige(len(dias) == 256 and dias.isin(s.index).all(), "la serie no cubre los 256 días del horizonte")
    v = s.reindex(dias)
    med.exige(bool(np.isfinite(v).all() and (v > 0).all()), "tasas no finitas o no positivas en el horizonte")
    med.ok("T2: la serie cubre los 256 días calendario del 2025-04-04 al 2025-12-15, cada uno con una sola tasa")
    m8 = pd.read_csv(AS.lee(F_M8, "e1/AR1"), parse_dates=["fecha"]).set_index("fecha").trm_COP_USD
    med.exige(len(m8) == 256 and m8.index.equals(dias), "m8_trm_diaria.csv no tiene los 256 días del horizonte")
    dif = (v - m8).abs()
    n_dist = int((dif > 0.005).sum())
    med.ok(f"T3: comparación día a día con m8_trm_diaria.csv en los 256 días: {n_dist} días distintos, "
           f"mayor diferencia {dif.max():.4f} COP/USD")
    ar1 = pd.read_csv(AS.lee(F_AR1, "e1/AR1")).set_index("clave").valor
    media_m8 = float(m8.mean())
    med.exige(abs(media_m8 - float(ar1["trm__media_horizonte"])) <= 1e-9,
              "la media de m8_trm_diaria.csv no es trm__media_horizonte")
    med.ok("T4: la media de m8_trm_diaria.csv es trm__media_horizonte (e1/AR1)")
    media = float(v.mean())
    med.di(f"  TRM media, Banco de la República: {media:.4f}; M8 (datos.gov.co): {media_m8:.4f} COP/USD; "
           f"días distintos {n_dist} de 256")
    T = pd.DataFrame({"fecha": dias.strftime("%Y-%m-%d"), "trm_banrep_COP_USD": v.to_numpy(),
                      "trm_m8_COP_USD": m8.to_numpy(), "dif_COP_USD": (v - m8).to_numpy()})
    med.tabla(T, "m11_trm_banrep_diaria.csv")
    med.pon("trmbr__media_horizonte", media, "COP/USD", FUENTE + "; media de los 256 días del horizonte")
    med.pon("trmbr__media_menos_m8", media - media_m8, "COP/USD", "trmbr__media_horizonte − trm__media_horizonte (e1/AR1)")
    med.pon("trmbr__dias", len(dias), "días", FUENTE)
    med.pon("trmbr__dias_distintos", n_dist, "días", "días con |Banco − M8| > 0,005 COP/USD, de m11_trm_banrep_diaria.csv")
    med.pon("trmbr__max_dif_diaria", float(dif.max()), "COP/USD", "máximo de |Banco − M8| en los 256 días")
    med.pon("trmbr__min", float(v.min()), "COP/USD", FUENTE)
    med.pon("trmbr__max", float(v.max()), "COP/USD", FUENTE)
    med.pon("trmbr__filas_serie", len(t), "filas", FUENTE + "; del 2025-03-25 al 2025-12-31")
    med.cierra()
    return 0


if __name__ == "__main__":
    sys.exit(main())
